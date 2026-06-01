# RabbitMQ Ingest Pipeline — Grafana Observability Demo

A demo showcasing Grafana's observability stack (Alloy, Loki, Mimir, Tempo, Grafana) with a simple event pipeline.

```
Python Producer (REST API)
        │  POST /ingest
        ▼
     RabbitMQ  (message broker)
        │  AMQP
        ▼
  Go Consumer  (poll & print)
```

- **Producer:** Python (Flask) — accepts JSON events via HTTP and publishes to RabbitMQ
- **Consumer:** Go — polls RabbitMQ every 30s, drains all available messages
- **Broker:** RabbitMQ — message queue between the two

---

## How observability is collected

| Signal | Method | Destination |
|---|---|---|
| **Logs** | Written to `logs/` files, scraped by Alloy | Loki |
| **Metrics** | Prometheus `/metrics` endpoint on each service, scraped by Alloy | Mimir |
| **Traces** | OpenTelemetry SDK exports via OTLP to Alloy | Tempo |

All three signals flow through **Grafana Alloy** (the single OTel ingress) before reaching their respective backends. All are visualized in **Grafana**.

### Tracing detail

The producer creates a span per HTTP request and injects the W3C `traceparent` into AMQP message headers. The consumer extracts it on receive and creates a child span, forming a single distributed trace across both services.

---

## Two ways to run

### Path A — Docker Compose (all services automated)

```bash
docker compose up -d                              # rabbitmq, producer, consumer
cd grafana && docker compose up -d                # alloy, loki, mimir, tempo, grafana
```

Everything starts in the background with default configs. The `docker-compose.yml` files set the required env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`, etc.) automatically.

### Path B — Terminal by terminal (local dev, step by step)

Each component runs as a local process, giving you full visibility into its output. The [`terminals/`](terminals/) docs walk through each one:

1. [`terminal-1-rabbitmq.md`](terminals/terminal-1-rabbitmq.md) — Start RabbitMQ
2. [`grafana/README.md`](grafana/README.md) — Start the Grafana stack (Alloy, Loki, Mimir, Tempo, Grafana)
3. [`terminal-2-python-producer.md`](terminals/terminal-2-python-producer.md) — Run the Flask producer
4. [`terminal-3-go-consumer.md`](terminals/terminal-3-go-consumer.md) — Run the Go consumer
5. [`terminal-4-tester.md`](terminals/terminal-4-tester.md) — Send test events

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `RABBITMQ_HOST` | `localhost` | RabbitMQ server address |
| `RABBITMQ_QUEUE` | `events` | Queue name |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASS` | `guest` | RabbitMQ password |
| `LOG_DIR` | `/app/logs` | Directory for application logs |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:14317` | Alloy OTLP endpoint for traces |
| `OTEL_SERVICE_NAME` | varies | Service name shown in traces |

---

## Docs

**Pipeline**
- [`docker-compose.yml`](docker-compose.yml) — RabbitMQ, producer, consumer (Compose path)
- [`terminals/terminal-1-rabbitmq.md`](terminals/terminal-1-rabbitmq.md) — Run RabbitMQ manually
- [`terminals/terminal-2-python-producer.md`](terminals/terminal-2-python-producer.md) — Run the producer manually
- [`terminals/terminal-3-go-consumer.md`](terminals/terminal-3-go-consumer.md) — Run the consumer manually
- [`terminals/terminal-4-tester.md`](terminals/terminal-4-tester.md) — Generate test traffic

**Grafana stack**
- [`grafana/docker-compose.yml`](grafana/docker-compose.yml) — Alloy, Loki, Mimir, Tempo, Grafana (Compose path)
- [`grafana/README.md`](grafana/README.md) — Full stack setup (both paths)
- [`grafana/terminals/terminal-4-loki.md`](grafana/terminals/terminal-4-loki.md) — Run Loki manually
- [`grafana/terminals/terminal-5-alloy.md`](grafana/terminals/terminal-5-alloy.md) — Run Alloy manually
- [`grafana/terminals/terminal-6-grafana.md`](grafana/terminals/terminal-6-grafana.md) — Run Grafana manually
- [`grafana/terminals/terminal-7-mimir.md`](grafana/terminals/terminal-7-mimir.md) — Run Mimir manually
- [`grafana/terminals/terminal-8-tempo.md`](grafana/terminals/terminal-8-tempo.md) — Run Tempo manually

**Reference**
- [`URLs.md`](URLs.md) — All service URLs & quick health checks
- [`docs/implement-traces.md`](docs/implement-traces.md) — Tracing architecture & code walkthrough
