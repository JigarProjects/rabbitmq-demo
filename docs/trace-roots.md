# Why the consumer never appears as a root span

This is expected — it's how distributed tracing works.

```
HTTP POST /ingest  →  Flask span (ROOT, "POST /ingest")
                               │
                          inject traceparent
                          into AMQP headers
                               │
                    ┌──────────┴──────────┐
                    │     RabbitMQ        │
                    └──────────┬──────────┘
                               │
                          extract traceparent
                          from AMQP headers
                               │
                    consumer span (CHILD, "rabbitmq_consume")
```

- The **producer** receives the HTTP request first → creates the **root span**
- The **consumer** polls RabbitMQ, finds the `traceparent` header → creates a **child span** attached to the same trace
- Both spans share the same `trace_id` but have different `span_id` values

In the Tempo API response, traces appear with `"rootServiceName":"python-producer"` and the consumer spans appear as child spans under `"spanSets"`. Some early traces may show `"rootServiceName":"<root span not yet received>"` — this means the consumer span arrived at Tempo before the producer span. Once the producer span is ingested, the root service name resolves.

## Service Graph

The "Service Graph" panel in Grafana is separate from individual trace queries. It requires Tempo's `metrics_generator` to be enabled, which is not currently configured. When enabled, it produces Prometheus-style metrics from traces, and Grafana visualises the service-to-service edges from those metrics.

---

## See also

- [`queries.md`](../queries.md) — example Tempo TraceQL queries
- [`docs/implement-traces.md`](implement-traces.md) — how tracing works end-to-end
