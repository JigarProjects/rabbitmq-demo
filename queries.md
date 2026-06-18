# Example Grafana Queries

Each signal has its own datasource. Open the right **Explore** view and paste the query.

---

## Loki (Logs)

Go to **Explore > Loki** in Grafana, select the **Loki** datasource, and paste these:

| Query | What it does |
|-------|-------------|
| `{service_name=~".+"}` | All logs across all services |
| `{service_name=~".+"} \|= "trace_id=512dd0ee0e660e8f51e4483b6e7e7f31"` | Logs for a specific trace |
| `{filename=~"/logs/(producer\|consumer)/.+"} \|= "trace_id=512dd0ee0e660e8f51e4483b6e7e7f31"` | Logs for a trace (narrower — excludes rabbitmq) |
| `{filename=~"/logs/.+"} \|= "error"` | Errors across all services (last 15m) |
| `sum by (filename) (rate({filename=~"/logs/(rabbitmq\|producer\|consumer)/.+"}[1m]))` | Logs per second by service |

Every Loki query must start with a label selector `{...}` — it's how the inverted index works.

---

## Tempo (Traces)

Go to **Explore > Tempo** in Grafana, select the **Tempo** datasource, and paste these:

| Query | What it does |
|-------|-------------|
| `{}` | All recent traces |
| `{.service.name = "python-producer"}` | Producer traces only |
| `{.service.name = "go-consumer"}` | Consumer traces only |
| `{.service.name = "python-producer" \|\| .service.name = "go-consumer"}` | Cross-service trace (producer → consumer) |
| `{} \| duration > 100ms` | Slow traces (> 100ms) |
| `{ .status = error }` | Traces with an error |

To find a trace by ID, use the **Trace ID** search field in Explore > Tempo with the full 32-hex ID.

---

## Mimir (Metrics)

Go to **Explore > Mimir** (or **Explore > Prometheus**) in Grafana, select the **Mimir** datasource, and paste these:

| Query | What it does |
|-------|-------------|
| `up` | Target health — all services up? |
| `rabbitmq_queue_messages_ready` | Queue depth (ready) |
| `rate(flask_http_request_total{job="producer"}[1m])` | HTTP request rate (producer) |
| `rate(flask_http_request_exceptions_total{job="producer"}[1m]) or vector(0)` | Error rate (5xx) |
| `histogram_quantile(0.99, sum(rate(flask_http_request_duration_seconds_bucket{job="producer"}[1m])) by (le))` | p99 latency |
| `go_goroutines{job="consumer"}` | Go goroutine count |

---

## Cross-signal correlation

Link logs, traces, and metrics without typing queries:

1. **Log → Trace** — click a highlighted `trace_id` value in any Loki log line to jump to the full trace in Tempo.
2. **Trace → Logs** — click a span in Tempo and open the **Logs** tab to see related Loki entries for that trace.

Both are configured in `grafana/datasources/`. See [`grafana/README.md`](grafana/README.md) for details.

---

## See also

- [`docs/log_format.md`](docs/log_format.md) — why log format matters for trace correlation
- [`docs/implement-traces.md`](docs/implement-traces.md) — how tracing works end-to-end
- [`docs/logs.md`](docs/logs.md) — how logs are collected via Alloy
- [`docs/metrics.md`](docs/metrics.md) — how metrics are scraped and stored
- [`docs/trace-roots.md`](docs/trace-roots.md) — why the consumer never appears as root
- [`docs/troubleshoot.md`](docs/troubleshoot.md) — common issues
- [`docs/scenario.md`](docs/scenario.md) — how this compares to production
