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

All three signals flow through **Grafana Alloy** before reaching their respective backends. All are visualized in **Grafana** with a pre-provisioned [dashboard](grafana/dashboards/overview.json) and [alert rules](grafana/alerting/rules.yml).

The producer creates a span per HTTP request and injects the W3C `traceparent` into AMQP message headers. The consumer extracts it on receive and creates a child span, forming a single distributed trace across both services.

---

## Three ways to run

### Path A — Single script (recommended)

Starts all 8 containers individually with `docker run -d`, no compose:

```bash
python scripts/start_all.py                                    # start everything
python scripts/start_all.py --status                           # check container status
python scripts/start_all.py --stop                             # stop all containers
```

All containers join a shared `grafana-net` bridge network and resolve each other by name. Logs go to `/home/ubuntu/logs/` (override with `--logs-home`).

Then generate traffic:

```bash
python test/continuous_traffic.py                              # burst of 1–5 events every 60s
```

Open http://localhost:3000 — the **RabbitMQ Ingest — Overview** dashboard is already provisioned with live panels for logs, metrics, and traces. Alert rules in the **Demo Alerts** folder evaluate automatically.

### Path B — Docker Compose

```bash
docker compose up -d                                           # rabbitmq, producer, consumer
cd grafana && docker compose up -d                             # alloy, loki, mimir, tempo, grafana
```

### Path C — Terminal by terminal

Each component runs as a local process. The [`terminals/`](terminals/) docs walk through each one:

1. [`terminal-1-rabbitmq.md`](terminals/terminal-1-rabbitmq.md) — Start RabbitMQ
2. [`grafana/README.md`](grafana/README.md) — Start the Grafana stack
3. [`terminal-2-python-producer.md`](terminals/terminal-2-python-producer.md) — Run the Flask producer
4. [`terminal-3-go-consumer.md`](terminals/terminal-3-go-consumer.md) — Run the Go consumer
5. [`terminal-4-tester.md`](terminals/terminal-4-tester.md) — Send test events

---

## Docs

| What | Where |
|------|-------|
| Startup script | [`scripts/start_all.py`](scripts/start_all.py) |
| Traffic generator | [`test/continuous_traffic.py`](test/continuous_traffic.py) / [`test/send_events.py`](test/send_events.py) |
| Pre-provisioned dashboard | [`grafana/dashboards/overview.json`](grafana/dashboards/overview.json) |
| Pre-provisioned alert rules | [`grafana/alerting/rules.yml`](grafana/alerting/rules.yml) |
| Alloy config | [`grafana/alloy/config.alloy`](grafana/alloy/config.alloy) |
| Service URLs & health checks | [`URLs.md`](URLs.md) |
| Tracing architecture | [`docs/implement-traces.md`](docs/implement-traces.md) |
| Terminal guides | [`terminals/`](terminals/) |
