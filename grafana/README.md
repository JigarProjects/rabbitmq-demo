# Grafana Observability Stack (LGTM + Alloy)

Full observability for the RabbitMQ ingest demo — logs (Loki), metrics (Mimir), and traces (Tempo), all visualized in Grafana.

The stack runs independently from the pipeline services (RabbitMQ, producer, consumer). They communicate over the network.

---

## Architecture

```
RabbitMQ    Producer (Python)    Consumer (Go)
   │             │                   │
   │  :15692     │  :25001           │  :2112
   │  /metrics   │  /metrics         │  /metrics
   │  logs/      │  logs/            │  logs/
   └─────────────┼───────────────────┘
                 │
         ┌───────▼────────┐
         │  Grafana Alloy │  ← reads logs + scrapes metrics + receives OTLP traces
         │  (collector)   │
         └───────┬────────┘
                 │
      ┌──────────┼──────────┐
      │          │          │
 ┌────▼────┐ ┌──▼───┐ ┌───▼─────┐
 │  Loki   │ │ Mimir │ │  Tempo  │
 │ (logs)  │ │(metrics)│ │(traces) │
 └────┬────┘ └──┬───┘ └───┬─────┘
      │         │         │
      └─────────┼─────────┘
                │
          ┌─────▼──────┐
          │   Grafana   │
          │ (dashboards)│
          └────────────┘
```

---

## Two ways to run

### Path A — Docker Compose (all at once)

```bash
cd grafana && docker compose up -d
```

Starts Alloy, Loki, Mimir, Tempo, and Grafana. All default configs are in this directory.

### Path B — Terminal by terminal (manual Docker runs)

Each service runs individually via `docker run`. See the [`terminals/`](terminals/) docs:

| Terminal | Component | Ports |
|---|---|---|
| [`terminal-4-loki.md`](terminals/terminal-4-loki.md) | Loki | `3100` |
| [`terminal-5-alloy.md`](terminals/terminal-5-alloy.md) | Alloy | `12345`, `14317` (OTLP gRPC), `14318` (OTLP HTTP) |
| [`terminal-6-grafana.md`](terminals/terminal-6-grafana.md) | Grafana | `3000` |
| [`terminal-7-mimir.md`](terminals/terminal-7-mimir.md) | Mimir | `9009` |
| [`terminal-8-tempo.md`](terminals/terminal-8-tempo.md) | Tempo | `4317` (OTLP gRPC), `4318` (OTLP HTTP), `3200` |

For all service URLs and quick checks, see [`../URLs.md`](../URLs.md).

---

## What gets collected

| Signal | Source | How | Backend |
|---|---|---|---|
| **Logs** | `logs/` files (producer, consumer, rabbitmq) | Alloy tails `logs/**/*.log` | Loki |
| **Metrics** | Prometheus `/metrics` on each service | Alloy scrapes every 15s | Mimir |
| **Traces** | OTel SDK in producer & consumer | Apps send OTLP to Alloy port 14317/14318, Alloy forwards to Tempo | Tempo |

All three signals are queryable from Grafana at `http://localhost:3000`.

---

## Per-service log files

| Service | Log path | Format |
|---|---|---|
| Python Producer | `logs/producer/producer.log` | Plain text (includes `trace_id`) |
| Go Consumer | `logs/consumer/consumer.log` | Plain text (includes `trace_id`) |
| RabbitMQ | `logs/rabbitmq/rabbitmq.log` | RabbitMQ startup logs |

## Metrics endpoints

| Service | Port | Endpoint |
|---|---|---|
| Python Producer | `25001` | `/metrics` (prometheus_flask_exporter) |
| Go Consumer | `2112` | `/metrics` (promhttp) |
| RabbitMQ | `15692` | `/metrics` (built-in) |

---

## Grafana datasources

Provisioned automatically on startup via [`datasources/`](datasources/):

- **Loki** — log queries (LogQL)
- **Mimir** — metric queries (PromQL)
- **Tempo** — trace queries (trace ID lookup, search)

No manual setup required.
