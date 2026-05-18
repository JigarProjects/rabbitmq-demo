package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	amqp "github.com/rabbitmq/amqp091-go"
)

func main() {
	host := envOr("RABBITMQ_HOST", "localhost")
	queue := envOr("RABBITMQ_QUEUE", "events")
	user := envOr("RABBITMQ_USER", "guest")
	pass := envOr("RABBITMQ_PASS", "guest")

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

	msgs, err := ch.Consume(q.Name, "", true, false, false, false, nil)
	if err != nil {
		log.Fatalf("Failed to register consumer: %v", err)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	log.Printf("Waiting for messages on queue %q ...", q.Name)

	for {
		select {
		case d := <-msgs:
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
