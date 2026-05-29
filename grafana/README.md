# Grafana Observability Stack

Full observability for the RabbitMQ ingest demo — logs, metrics, and traces.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  RabbitMQ    │     │  Producer    │     │  Consumer    │
│  (broker)    │     │  (Flask)     │     │  (Go)        │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       │               logs/producer/        logs/consumer/
       │                    │                     │
       └────────────────────┼─────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Grafana Alloy │  ← reads log files
                    │  (collector)   │
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼─────┐ ┌────▼────┐ ┌──────▼──────┐
       │   Loki     │ │Prometheus│ │   Tempo     │
       │  (logs)    │ │(metrics) │ │ (traces)    │
       └──────┬─────┘ └────┬────┘ └──────┬───────┘
              │             │             │
              └─────────────┼─────────────┘
                            │
                    ┌───────▼────────┐
                    │    Grafana     │
                    │  (dashboard)   │
                    └────────────────┘
```

## Components

| Component | Status | Purpose |
|-----------|--------|---------|
| **Grafana Alloy** | ✅ Running | Log collector — reads `./logs/**/*.log` and forwards to Loki |
| **Loki** | ✅ Running | Log storage & query engine |
| **Grafana** | ✅ Running | Visualisation & dashboards |
| **Prometheus** | 📅 Later | Metrics collection & alerts |
| **Tempo** | 📅 Later | Distributed tracing |

## Quick Start

> **Prefer running components individually?** See the `terminals/` directory for step-by-step instructions for each service.

```bash
# Start the Grafana stack (Alloy + Loki + Grafana)
docker compose -f grafana/docker-compose.yml up -d

# Open Grafana at http://localhost:3000 (anonymous Admin)
```

## Per-service log files

| Service | Log path |
|---------|----------|
| Python Producer | `logs/producer/producer.log` |
| Go Consumer | `logs/consumer/consumer.log` |
| RabbitMQ | `logs/rabbitmq/rabbitmq.log` |

## Future

- **Prometheus** — scrape metrics from the producer and consumer
- **Tempo** — receive traces from the producer and consumer
- **Unified dashboards** — combine logs, metrics, and traces in single views
