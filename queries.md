# Example Grafana Queries

Example queries for each signal in the RabbitMQ Ingest demo.

---

## Loki (Logs)

Loki requires **every query to start with a label selector** `{...}` — this is how its
inverted index works. You cannot query without one. The broadest selector is:

```logql
{filename=~".+"}
```

But applying a line filter for `trace_id` is far more useful:

| What | Query |
|------|-------|
| All logs for a trace | `{filename=~"/logs/(producer\|consumer)/.+"} \|= "trace_id=512dd0ee0e660e8f51e4483b6e7e7f31"` |
| Errors (last 15m) | `{filename=~"/logs/.+"} \|= "error"` |
| Logs per second by service | `sum by (filename) (rate({filename=~"/logs/(rabbitmq\|producer\|consumer)/.+"}[1m]))` |

**Tip:** Grafana's `derivedFields` (Loki datasource) and `traceToLogs` (Tempo datasource)
let you click between logs and traces without writing label selectors yourself —
configured in the datasource YAML files under `grafana/datasources/`.

---

## Tempo (Traces)

TraceQL queries. Open in Grafana **Explore > Tempo** or the **Traces** panel on the
overview dashboard.

| What | Query |
|------|-------|
| All recent traces | `{}` |
| Producer traces only | `{.service.name = "python-producer"}` |
| Consumer traces only | `{.service.name = "go-consumer"}` |
| Cross-service trace (producer → consumer) | `{.service.name = "python-producer" \|\| .service.name = "go-consumer"}` |
| Slow traces (> 100ms) | `{} \| duration > 100ms` |
| Traces with an error | `{ .status = error }` |
| Events by a specific trace_id | Use the **Trace ID** search field in Explore > Tempo with the full 32-hex ID |

---

## Mimir (Metrics)

PromQL queries against the Mimir datasource.

| What | Query |
|------|-------|
| Are all services up? | `up{job=~"rabbitmq\|producer\|consumer"}` |
| Queue depth (ready) | `rabbitmq_queue_messages_ready` |
| HTTP request rate (producer) | `sum(rate(flask_http_request_total{job="producer"}[1m]))` |
| Error rate (5xx) | `sum(rate(flask_http_request_total{job="producer",status=~"5.."}[1m])) or vector(0)` |
| p99 latency | `histogram_quantile(0.99, sum(rate(flask_http_request_duration_seconds_bucket{job="producer"}[1m])) by (le))` |
| Go goroutine count | `go_goroutines{job="consumer"}` |

---

## Cross-signal correlation

The most powerful Grafana workflow is linking signals without typing queries:

1. **Log → Trace** — click a highlighted `trace_id` value in any Loki log line to
   jump to the full trace in Tempo (requires `derivedFields` on the Loki datasource).
2. **Trace → Logs** — click a span in Tempo and open the **Logs** tab to see related
   Loki entries for that trace (requires `traceToLogs` on the Tempo datasource).

Both are configured in `grafana/datasources/`. See
[`grafana/README.md`](grafana/README.md) for datasource setup details.
