package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

func main() {
	host := envOr("RABBITMQ_HOST", "localhost")
	queue := envOr("RABBITMQ_QUEUE", "events")
	user := envOr("RABBITMQ_USER", "guest")
	pass := envOr("RABBITMQ_PASS", "guest")

	logDir := envOr("LOG_DIR", "/app/logs")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		log.Printf("Failed to create log directory %s: %v", logDir, err)
	}
	logFile, err := os.OpenFile(filepath.Join(logDir, "consumer.log"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		log.Printf("Failed to open log file: %v — falling back to stdout only", err)
	} else {
		log.SetOutput(io.MultiWriter(os.Stdout, logFile))
		defer logFile.Close()
	}

	tp, err := initTracerProvider()
	if err != nil {
		log.Fatalf("Failed to init tracer provider: %v", err)
	}
	defer func() { _ = tp.Shutdown(context.Background()) }()

	conn, err := amqp.Dial(fmt.Sprintf("amqp://%s:%s@%s:5672/", user, pass, host))
	if err != nil {
		log.Fatalf("Failed to connect to RabbitMQ: %v", err)
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		log.Fatalf("Failed to open channel: %v", err)
	}
	defer ch.Close()

	q, err := ch.QueueDeclare(queue, true, false, false, false, nil)
	if err != nil {
		log.Fatalf("Failed to declare queue: %v", err)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	log.Printf("Polling queue %q every minute ...", q.Name)

	go func() {
		mux := http.NewServeMux()
		mux.Handle("/metrics", promhttp.Handler())
		addr := ":2112"
		log.Printf("Metrics HTTP server listening on %s", addr)
		if err := http.ListenAndServe(addr, mux); err != nil {
			log.Printf("Metrics HTTP server stopped: %v", err)
		}
	}()

	tracer := otel.Tracer("go-consumer")

	for {
		select {
		case <-ticker.C:
			d, ok, err := ch.Get(q.Name, true)
			if err != nil {
				log.Printf("Error getting message: %v", err)
				continue
			}
			if !ok {
				continue
			}

			headers := make(map[string]string)
			for k, v := range d.Headers {
				if s, ok := v.(string); ok {
					headers[k] = s
				}
			}

			ctx := otel.GetTextMapPropagator().Extract(context.Background(), propagation.MapCarrier(headers))

			_, span := tracer.Start(ctx, "rabbitmq_consume",
				trace.WithAttributes(
					attribute.String("messaging.destination", queue),
					attribute.String("messaging.message_id", d.MessageId),
				),
			)

			var payload any
			if err := json.Unmarshal(d.Body, &payload); err != nil {
				log.Printf("Received raw: %s", d.Body)
			} else {
				sc := span.SpanContext()
				log.Printf("Received [trace_id=%s]: %+v", sc.TraceID().String(), payload)
			}

			span.End()
		case <-sig:
			log.Println("Shutting down ...")
			return
		}
	}
}

func initTracerProvider() (*sdktrace.TracerProvider, error) {
	ctx := context.Background()
	endpoint := trimScheme(envOr("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:14317"))

	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(endpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(envOr("OTEL_SERVICE_NAME", "go-consumer")),
		)),
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return tp, nil
}

func trimScheme(endpoint string) string {
	endpoint = strings.TrimPrefix(endpoint, "http://")
	endpoint = strings.TrimPrefix(endpoint, "https://")
	return endpoint
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
