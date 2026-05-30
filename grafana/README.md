# Grafana Observability Stack (LGTM)

Full observability for the RabbitMQ ingest demo — logs (Loki), metrics (Mimir), and traces (Tempo).

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  RabbitMQ    │     │  Producer    │     │  Consumer    │
│  (broker)    │     │  (Flask)     │     │  (Go)        │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       │  logs/rabbitmq/    │  logs/producer/     │  logs/consumer/
       │  :15692/metrics    │  :25001/metrics     │  :2112/metrics
       │                    │                     │
       └────────────────────┼─────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Grafana Alloy │  ← reads logs + scrapes metrics
                    │  (collector)   │
                    └───────┬────────┘
                            │
               ┌────────────┼────────────┐
               │            │            │
        ┌──────▼─────┐ ┌───▼────┐ ┌────▼──────┐
        │   Loki     │ │ Mimir  │ │   Tempo   │
        │  (logs)    │ │(metrics)│ │ (traces)  │
        └──────┬─────┘ └───┬────┘ └────┬──────┘
               │            │            │
               └────────────┼────────────┘
                            │
                    ┌───────▼────────┐
                    │    Grafana     │
                    │  (dashboard)   │
                    └────────────────┘
```

## Components

| Component | Status | Purpose |
|-----------|--------|---------|
| **Grafana Alloy** | ✅ Running | Collector — tails log files & scrapes metrics endpoints, forwards to Loki & Mimir |
| **Loki** | ✅ Running | Log storage & query engine |
| **Mimir** | ✅ Running | Metrics storage (Prometheus-compatible) |
| **Grafana** | ✅ Running | Visualisation & dashboards |
| **Tempo** | 📅 Later | Distributed tracing |

## Quick Start

> **Prefer running components individually?** See the `terminals/` directory for step-by-step instructions for each service.

```bash
# Start the Grafana stack (Alloy + Loki + Mimir + Grafana)
docker compose -f grafana/docker-compose.yml up -d

# Open Grafana at http://localhost:3000 (anonymous Admin)
```

## Per-service log files

| Service | Log path |
|---------|----------|
| Python Producer | `logs/producer/producer.log` |
| Go Consumer | `logs/consumer/consumer.log` |
| RabbitMQ | `logs/rabbitmq/rabbitmq.log` |

## Metrics endpoints

| Service | Port | Endpoint |
|---------|------|----------|
| Python Producer | `25001` | `/metrics` (prometheus_flask_exporter) |
| Go Consumer | `2112` | `/metrics` (promhttp) |
| RabbitMQ | `15692` | `/metrics` (built-in) |

Alloy scrapes these every 15s and forwards to Mimir.

## Future

- **Tempo** — receive traces from the producer and consumer
- **Unified dashboards** — combine logs, metrics, and traces in single views
