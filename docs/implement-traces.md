# Implementing Distributed Tracing

## Overview

Traces let you follow a single request as it flows through the entire pipeline:

```
HTTP POST /ingest  ──→  RabbitMQ  ──→  Go Consumer
     │                     │               │
     ├─ span: /ingest      ├─ span: enqueue ├─ span: process
     │   trace_id=abc      │   trace_id=abc │   trace_id=abc
     └─ logs with          └─ logs with     └─ logs with
        trace_id=abc          trace_id=abc      trace_id=abc
```

The central concept is a **trace ID** — a 16-byte (128-bit) random identifier that is
generated at the entry point (the HTTP request) and propagated through every downstream
service via message headers. Every span and log line emitted during the request's lifecycle
carries this trace ID, letting you query "show me everything that happened for this one
request" in Grafana.

---

## 1. Core Concept: Correlation ID / Trace ID

A **trace ID** is just a correlation ID with a standardised format. OpenTelemetry defines:

| Field | Size | Format |
|-------|------|--------|
| `trace_id` | 16 bytes | hex-encoded (32 hex chars), e.g. `0af7651916cd43dd8448eb211c80319c` |
| `span_id` | 8 bytes | hex-encoded (16 hex chars), e.g. `b7ad6b7169203331` |
| `trace_flags` | 1 byte | bitmask; `01` = sampled |

**For RabbitMQ / AMQP**, trace context is propagated as message headers using the
[OpenTelemetry HTTP/HTTPs propagation format](https://www.w3.org/TR/trace-context/):

| Header | Example |
|--------|---------|
| `traceparent` | `00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01` |
| `tracestate` | (vendor-specific, optional) |

> **Note for AMQP:** RabbitMQ headers exchange already supports arbitrary `headers`
> as a table. We piggyback `traceparent` on the AMQP `BasicProperties.Headers` map.

---

## 2. OpenTelemetry SDK Setup

### Python Producer

**Add to `python-producer/requirements.txt`:**

```
opentelemetry-distro==0.52b0
opentelemetry-instrumentation-flask==0.52b0
opentelemetry-exporter-otlp-proto-grpc==1.31.0
```

**Instrument in `app.py`:**

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")))
)
trace.set_tracer_provider(provider)
set_global_textmap(TraceContextTextMapPropagator())

FlaskInstrumentor().instrument_app(app)
```

**Inject trace context into AMQP headers when publishing:**

```python
from opentelemetry import trace
from opentelemetry.propagate import inject

@app.route("/ingest", methods=["POST"])
def ingest():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rabbitmq_publish") as span:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        # Prepare AMQP headers with trace context
        headers = {}
        inject(headers)  # writes traceparent/tracestate into the dict

        connection, channel = get_rabbitmq_channel()
        try:
            channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(data),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers=headers,
                ),
            )
            span.set_attribute("messaging.destination", RABBITMQ_QUEUE)
            span.set_attribute("messaging.message_id", str(uuid.uuid4()))
            logging.info("Published event [trace_id=%s]", span.get_span_context().trace_id)
            return jsonify({"status": "published"}), 201
        finally:
            connection.close()
```

### Go Consumer

**Add to `go-consumer/main.go` imports and initialisation:**

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/propagation"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
    "go.opentelemetry.io/otel/trace"
)

func initTracerProvider() (*sdktrace.TracerProvider, error) {
    ctx := context.Background()
    exporter, err := otlptracegrpc.New(ctx, otlptracegrpc.WithEndpoint(
        envOr("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
    ), otlptracegrpc.WithInsecure())
    if err != nil {
        return nil, err
    }
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceNameKey.String("go-consumer"),
        )),
    )
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.TraceContext{})
    return tp, nil
}
```

**Extract trace context from AMQP headers when consuming:**

```go
import "go.opentelemetry.io/otel/propagation"

// Inside the consume loop:

var headers map[string]interface{}
if d.Headers != nil {
    headers = d.Headers
} else {
    headers = make(map[string]interface{})
}

// Extract trace context from AMQP headers
ctx := otel.GetTextMapPropagator().Extract(context.Background(), propagation.MapCarrier(headers))

tracer := otel.Tracer("go-consumer")
_, span := tracer.Start(ctx, "rabbitmq_consume",
    trace.WithAttributes(
        attribute.String("messaging.destination", queue),
        attribute.String("messaging.message_id", d.MessageId),
    ),
)

var payload any
if err := json.Unmarshal(d.Body, &payload); err != nil {
    log.Printf("Received raw: %s", d.Body)
} else {
    log.Printf("Received: %+v", payload)
}

span.End()
```

**Add to `go.mod`:**

```
go.opentelemetry.io/otel v1.31.0
go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.31.0
go.opentelemetry.io/otel/sdk v1.31.0
go.opentelemetry.io/otel/trace v1.31.0
go.opentelemetry.io/otel/attribute v1.31.0
go.opentelemetry.io/otel/propagation v1.31.0
go.opentelemetry.io/otel/semconv v1.26.0
```

---

## 3. Tempo — Trace Storage Backend

Add Tempo to `grafana/docker-compose.yml`:

```yaml
tempo:
  image: grafana/tempo:latest
  container_name: grafana-tempo
  restart: unless-stopped
  command: ["-config.file=/etc/tempo/tempo.yml"]
  ports:
    - "4317:4317"   # OTLP gRPC
    - "4318:4318"   # OTLP HTTP
  volumes:
    - ./tempo/tempo.yml:/etc/tempo/tempo.yml:ro
```

Create `grafana/tempo/tempo.yml`:

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"

storage:
  trace:
    backend: local
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/blocks
```

**Register the Tempo datasource** in `grafana/datasources/` by adding `tempo.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Tempo
    type: tempo
    uid: tempo
    url: http://tempo:3200
    access: proxy
    editable: true
```

---

## 4. Alloy — OTLP Receiver

Add an OTLP receiver to `grafana/alloy/config.alloy` so Alloy can forward traces to Tempo:

```alloy
// ─── Traces ────────────────────────────────────────────────────────────────────

// Receive OTLP traces from the producer and consumer
otelcol.receiver.otlp "default" {
    grpc {
        endpoint = "0.0.0.0:14317"
    }
    http {
        endpoint = "0.0.0.0:14318"
    }

    output {
        traces = [otelcol.processor.batch.default.input]
    }
}

// Batch before forwarding
otelcol.processor.batch "default" {
    output {
        traces = [otelcol.exporter.otlp.tempo.input]
    }
}

// Forward to Tempo
otelcol.exporter.otlp "tempo" {
    client {
        endpoint = "tempo:4317"
        tls {
            insecure = true
        }
    }
}
```

**Expose OTLP ports** from the Alloy container:

```yaml
ports:
  - "14317:14317"   # OTLP gRPC
  - "14318:14318"   # OTLP HTTP
```

---

## 5. Correlating Logs with Traces

The real power comes from joining logs and traces. Every log line should include the
current `trace_id` and `span_id`.

### Python — structured JSON logging with trace context

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.dev.JSONRenderer(),
    ],
)

# In the ingest endpoint:
span = trace.get_current_span()
ctx = span.get_span_context()
log = structlog.get_logger().bind(
    trace_id=format(ctx.trace_id, "032x"),
    span_id=format(ctx.span_id, "016x"),
)
log.info("event_published", event=json.dumps(data))
```

### Go — structured logging with trace context

```go
slog.Info("message received",
    "trace_id", span.SpanContext().TraceID().String(),
    "span_id", span.SpanContext().SpanID().String(),
    "payload", fmt.Sprintf("%+v", payload),
)
```

### Alloy — parse trace_id from log lines for Loki

```alloy
loki.source.file "scrape" {
    targets    = local.file_match.logs.targets
    forward_to = [loki.process.extract_trace_id.receiver]
}

loki.process "extract_trace_id" {
    forward_to = [loki.write.loki.receiver]

    stage.json {
        expressions = { "trace_id" = "" }
    }

    stage.labels {
        values = { "trace_id" = "" }
    }
}
```

This lets you click a trace ID in a log line in Grafana and jump directly to the
trace in Tempo.

---

## 6. End-to-End Flow Summary

```
┌────────────────────────────────────────────────────────────────────┐
│  HTTP POST /ingest                                                 │
│    │                                                               │
│    ├─ FlaskInstrumentor creates root span (SERVER)                 │
│    │   trace_id = 0af7...319c                                      │
│    │                                                               │
│    ├─ inject() writes traceparent into AMQP headers                │
│    │   headers["traceparent"] = "00-0af7...319c-b7ad...3331-01"    │
│    │                                                               │
│    ├─ Publisher creates child span "rabbitmq_publish"              │
│    │   trace_id = 0af7...319c (inherited)                          │
│    │   span_id  = beef...cafe (new)                                │
│    │                                                               │
│    └─ Log line: trace_id context attached via structlog            │
│       {"event":"page_view","trace_id":"0af7...319c",...}           │
│                                                                    │
│                                │                                    │
│                          RabbitMQ                                   │
│                          headers[traceparent] forwarded             │
│                                │                                    │
│  Go Consumer                                                        │
│    │                                                               │
│    ├─ Extract() reads traceparent from AMQP headers                │
│    │   restores trace_id = 0af7...319c                             │
│    │                                                               │
│    ├─ Creates child span "rabbitmq_consume"                        │
│    │   trace_id = 0af7...319c (inherited)                          │
│    │   span_id  = dead...code (new)                                │
│    │                                                               │
│    └─ Log line: trace_id in structured log                         │
│       {"msg":"message received","trace_id":"0af7...319c",...}      │
│                                                                    │
│         │                                                          │
│         ▼                                                          │
│  OTLP Exporter ──→ Alloy (otelcol.receiver.otlp) ──→ Tempo        │
│  Log on disk  ──→ Alloy (loki.source.file)      ──→ Loki          │
│                                                                    │
│  In Grafana: Explore → Tempo → search trace_id                    │
│  Or: click trace_id in a Loki log line → "View trace"             │
└────────────────────────────────────────────────────────────────────┘
```

---

## 7. Environment Variables

| Variable | Default | Services |
|----------|---------|----------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://alloy:14317` | producer, consumer |
| `OTEL_SERVICE_NAME` | `python-producer` / `go-consumer` | producer, consumer |
| `OTEL_RESOURCE_ATTRIBUTES` | `service.version=1.0` | producer, consumer |

OTel SDKs respect these by default when the `OTEL_EXPORTER_OTLP_*` env vars are set.
If using the OTLP exporter directly in code (as shown above), you can read the env
var explicitly and pass it as the endpoint.

---

## 8. Operational Considerations

### Push vs Pull

Tempo is **push-based**. The app's OTel SDK pushes spans to the collector (Alloy), which pushes to Tempo. Traces are ephemeral and high-cardinality — you can't poll for them like metrics.

### Export Frequency

The OTel SDK's `BatchSpanProcessor` controls how often spans are shipped:

| Setting | Default | Behaviour |
|---------|---------|-----------|
| `max_export_batch_size` | 512 spans | Export when buffer fills up |
| `scheduled_delay` | 5s | Export at most every 5 seconds |
| `max_queue_size` | 2048 spans | Drops oldest if queue overflows |

So spans are pushed roughly **every 5 seconds** (or sooner if 512 spans accumulate). Within Tempo, incoming spans are written to the WAL immediately, then flushed to storage blocks in ~30s intervals.

### Retention

In our `tempo.yml`:

```yaml
backend_scheduler:
  provider:
    work:
      compaction:
        block_retention: 24h
```

Traces older than 24 hours are automatically deleted. For a demo this is fine; in production you'd set this to weeks or months, and use object storage (S3/GCS) instead of local disk.

### Sampling — The Risk of Missing Errors

By default, **every span** reaches Tempo. At low volume that's fine. But as volume grows you face a choice:

| Approach | Storage cost | Error visibility |
|----------|-------------|------------------|
| No sampling | Unlimited — keep everything | 100% of errors visible |
| Head-based sampling (decide at entry) | Bounded | ❌ May drop the one error in the sampled-out set |
| Tail-based sampling (decide after complete trace) | Bounded | ✅ All errors kept, sample successful traces |

**Head-based sampling** is risky — if you decide "keep 1 in 10 traces" at the HTTP entry point, an error that happens 1 in 100 requests will be visible only 10% of the time. You miss 9 out of 10 errors.

**Tail-based sampling** fixes this: Alloy waits until the trace completes, checks if any span has an error status, and keeps it unconditionally. Successful traces are sampled at a configurable rate.

Example Alloy tail-sampling config:

```alloy
otelcol.processor.tail_sampling "default" {
    decision_wait = 30s
    policies {
        name = "errors"
        type = "status_code"
        status_code {
            status_codes = ["ERROR"]
        }
    }
    policies {
        name = "successful"
        type = "probabilistic"
        probabilistic {
            sampling_percentage = 10
        }
    }
    output {
        traces = [otelcol.exporter.otlp.tempo.input]
    }
}
```

With this: every error trace is kept, only 10% of successful traces are stored. **You never miss errors**, and storage stays bounded.

### Pipeline: Where Sampling Fits

```
App → OTel SDK (BatchSpanProcessor, ~5s) → Alloy (tail_sampling, 30s window) → Tempo (retention, 24h+)
```

---

## 9. Verification

```bash
# Send a test event
curl -X POST http://localhost:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice"}'

# Check trace in Tempo
curl http://localhost:3200/api/search\?q\=\{\}

# Query traces by service
curl http://localhost:3200/api/search\?q\=\{service.name="python-producer"\}

# Grafana: Explore → Tempo → search by trace_id
# Grafana: Explore → Loki → filter by trace_id label
```

---

## Summary of Changes

| Area | Changes |
|------|---------|
| `python-producer/requirements.txt` | Add `opentelemetry-distro`, `opentelemetry-instrumentation-flask`, `opentelemetry-exporter-otlp-proto-grpc` |
| `python-producer/app.py` | OTel initialisation, `FlaskInstrumentor`, inject trace context into AMQP headers |
| `go-consumer/go.mod` | Add `go.opentelemetry.io/otel`, `otlptracegrpc`, SDK packages |
| `go-consumer/main.go` | `initTracerProvider()`, extract trace context from AMQP headers, create consumer spans |
| `grafana/docker-compose.yml` | Add `tempo` service |
| `grafana/tempo/tempo.yml` | OTLP gRPC/HTTP receivers, local storage config |
| `grafana/alloy/config.alloy` | Add `otelcol.receiver.otlp` → `otelcol.processor.batch` → `otelcol.exporter.otlp` pipeline |
| `grafana/datasources/tempo.yml` | Tempo datasource for Grafana |
| Logging | Structured JSON logging with `trace_id` / `span_id`; Alloy `loki.process` stage to extract `trace_id` as a label |
