# Metrics Collection

Alloy scrapes Prometheus endpoints from each service and forwards metrics to Mimir, which Grafana queries.

```
metrics endpoints ──> Alloy ──> Mimir (storage) ──> Grafana
```

---

## Services and Endpoints

Each service exposes a `/metrics` endpoint with framework-level auto-instrumentation — no custom metric code required.

| Service | Port | Endpoint | Library |
|---------|------|----------|---------|
| Python producer | `25001` | `/metrics` | `prometheus_flask_exporter` |
| Go consumer | `2112` | `/metrics` | `promhttp` (Go client_golang) |
| RabbitMQ | `15692` | `/metrics` | Built-in Prometheus plugin |

---

## Scrape Config (Alloy)

```alloy
prometheus.scrape "default" {
    scrape_interval = "15s"

    targets = [
        {"__address__" = "host.docker.internal:15692", "job" = "rabbitmq"},
        {"__address__" = "host.docker.internal:25001", "job" = "producer"},
        {"__address__" = "host.docker.internal:2112",  "job" = "consumer"},
    ]

    forward_to = [prometheus.remote_write.mimir.receiver]
}
```

`host.docker.internal` is used because each service runs in its own container outside the `grafana-net` network.

---

## Remote Write (Alloy → Mimir)

```alloy
prometheus.remote_write "mimir" {
    endpoint {
        url = "http://mimir:9009/api/v1/push"
    }
}
```

Mimir accepts remote writes by default — no extra flags needed.

---

## What Each Service Exposes

### Python Producer

Auto-instrumented by `prometheus_flask_exporter`:

- `flask_http_request_total` — request count by method, status, path
- `flask_http_request_duration_seconds` — latency histogram
- `flask_http_request_exceptions_total` — exception count

### Go Consumer

Exposed by `promhttp` with default Go metrics:

- `go_goroutines` — number of goroutines
- `go_memstats_alloc_bytes` — memory allocation
- `go_gc_duration_seconds` — GC pause durations
- `process_cpu_seconds_total` — CPU usage
- `process_resident_memory_bytes` — RSS memory

### RabbitMQ

Built-in Prometheus plugin exposes:

- `rabbitmq_queue_messages_ready` — messages ready to deliver
- `rabbitmq_queue_messages_unacked` — messages delivered but not acked
- `rabbitmq_queue_messages_total` — total messages in queue
- `rabbitmq_connections_total` — connection count
- `rabbitmq_channels_total` — channel count

---

## Useful Queries

```promql
# Target health
up

# Request rate (producer)
rate(flask_http_request_total[1m])

# Error rate (producer)
rate(flask_http_request_exceptions_total[1m])

# Consumer memory
go_memstats_alloc_bytes

# Consumer goroutines
go_goroutines

# RabbitMQ queue depth
rabbitmq_queue_messages_ready{queue="events"}

# RabbitMQ connections
rabbitmq_connections_total
```

---

## What Else Can Be Added

### Metrics from Logs (Loki → Metrics)

Generate Prometheus metrics from log content without instrumenting the app:

```alloy
loki.process "metrics" {
    forward_to = [loki.write.loki.receiver]

    stage.metrics {
        counter {
            name        = "log_errors_total"
            description = "Total error log lines"
            prefix      = "app"
            match_all   = true
            action      = "inc"

            stage.match {
                selector = `{component="consumer"} |= "error"`
            }
        }
    }
}
```

This creates `app_log_errors_total` — a counter incremented every time a log line containing "error" appears.

### Multiple Backends

Forward to multiple remote-write targets:

```alloy
prometheus.remote_write "multi" {
    endpoint {
        url = "http://mimir:9009/api/v1/push"
    }
    endpoint {
        url = "http://victoria-metrics:8428/api/v1/push"
    }
}
```

### Service-Level Metrics (app code)

For more domain-specific metrics (e.g. published events count, consume latency), each app can register custom counters/histograms using the same Prometheus client libraries already imported.
