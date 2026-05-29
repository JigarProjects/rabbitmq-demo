package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/prometheus/client_golang/prometheus/promhttp"
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
			var payload any
			if err := json.Unmarshal(d.Body, &payload); err != nil {
				log.Printf("Received raw: %s", d.Body)
			} else {
				log.Printf("Received: %+v", payload)
			}
		case <-sig:
			log.Println("Shutting down ...")
			return
		}
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
