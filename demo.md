# Demo: End-to-End Tracing Walkthrough

Follow along from your terminal to Grafana. Each step builds on the last.

---

## Overview

Think of a package delivery with a tracking number.

- The **tracking number** (`trace_id`) is one identifier that follows the package
  from pickup to delivery. You use it to look up everything that happened.
- At each stop (warehouse scan, truck load, delivery), a **scan event** (`span_id`)
  is recorded. Each scan has its own ID, but they all share the same tracking
  number.

In this demo:

```
Tracking number (trace_id) = deadbeefdeadbeefdeadbeefdeadbe01
             │
  ┌──────────▼──────────┐
  │ Scan at pickup      │  scan_id (span_id) = b7ad6b7169203331
  │ Producer receives   │
  │ HTTP POST           │
  └──────────┬──────────┘
             │ package forwarded via RabbitMQ
  ┌──────────▼──────────┐
  │ Scan at delivery    │  scan_id (span_id) = deadcodedeadcode (auto-generated)
  │ Consumer processes  │
  │ the message         │
  └─────────────────────┘
```

Both the producer and consumer write the tracking number (`trace_id`) into their
log files, and both send their scan events (spans) to Grafana's tracing backend
(Tempo). In Grafana you can see the full timeline of a request — from HTTP POST
to consumer processing — all connected by the `trace_id`.

```
curl ──→ Python Producer (Flask) ──→ RabbitMQ ──→ Go Consumer
           │  OTLP                       │            │
           ▼                             ▼            ▼
        Alloy ──→ Tempo (traces)     Logs ──→ Loki (logs)
           │                                       │
           ▼                                       ▼
        Grafana (Explore + dashboard)
```

> **Key point:** The `trace_id` stays the same across services. The `span_id`
> changes at each step — every service generates its own span ID. The `SPAN_ID`
> you set in the setup below is only for the producer's span; the consumer's
> span ID is created automatically.

---

## Prerequisites

- The full stack is running (see [`README.md`](README.md))
- Grafana is open at `http://localhost:3000`
- The **RabbitMQ Ingest — Overview** dashboard loads without errors

---

## Setup: one-time env vars

Set these once in your terminal — they stay the same for the whole demo:

```bash
export MACHINE_IP=localhost
export TRACE_ID_PREFIX="deadbeefdeadbeefdeadbeefdeadbe"
export SPAN_ID="b7ad6b7169203331"
```

| Variable | Value | Why |
|----------|-------|-----|
| `MACHINE_IP` | `localhost` | Address of the machine running the producer. Change to the actual IP if not local. |
| `TRACE_ID_PREFIX` | `deadbeefdeadbeefdeadbeefdeadbe` | First 30 hex chars of the trace ID. Append `01`, `02` … to make a full 32-char trace ID per request. |
| `SPAN_ID` | `b7ad6b7169203331` | Static 16-char span ID for the parent span. Keeps things predictable. |

---

## Scenario A: Request with a trace ID (you control it)

Send an event with a known `trace_id` injected via the `traceparent` header:

```bash
curl -X POST http://${MACHINE_IP}:25001/ingest \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-${TRACE_ID_PREFIX}01-${SPAN_ID}-01" \
  -d '{"event": "page_view", "user": "alice"}'
```

**What happened?**

1. FlaskInstrumentor received the incoming `traceparent` header and used it as the
   root span context — no new trace_id was generated.
2. The producer logged `[trace_id=deadbeefdeadbeefdeadbeefdeadbe01]` and published
   the message to RabbitMQ.
3. The Go consumer pulled the message, extracted the same `traceparent` from AMQP
   headers, created a child span, and logged the same trace_id.

### Verify in Grafana

#### 1. Logs (Loki)

Open **Explore > Loki** and run:

```logql
{filename=~"/logs/(producer|consumer)/.+"} |= "trace_id=deadbeefdeadbeefdeadbeefdeadbe01"
```

You should see **two log lines** — one from the producer (`Published event …`) and one
from the consumer (`Received …`), both with the same trace_id. This proves the trace_id
propagated across the message broker.

If **derivedFields** is configured on the Loki datasource, the trace_id value is
clickable — clicking it opens the trace in Tempo.

#### 2. Traces (Tempo)

Open **Explore > Tempo**, paste the trace_id into the **Trace ID** search field:

```
deadbeefdeadbeefdeadbeefdeadbe01
```

You should see a waterfall with two spans:
- `POST /ingest` (producer, root span)
- `rabbitmq_consume` (consumer, child span)

If **traceToLogs** is configured on the Tempo datasource, clicking either span
reveals a **Logs** tab showing the related Loki entries.

---

## Scenario B: Request without a trace ID (server generates one)

Send a plain request — no `traceparent` header:

```bash
curl -X POST http://${MACHINE_IP}:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "signup", "user": "bob"}'
```

This time the FlaskInstrumentor generated a **brand-new** trace_id on the server.
We don't know what it is yet.

### Find the generated trace_id

In **Explore > Loki**, query the producer's recent logs:

```logql
{filename=~"/logs/producer/.+"} |= "Published event"
```

Copy the 32-char hex value from the `[trace_id=...]` in the result (e.g.,
`0af7651916cd43dd8448eb211c80319c`).

### Verify

1. **Loki** — use the same trace_id to see both producer & consumer logs:
   ```
   {filename=~"/logs/(producer|consumer)/.+"} |= "trace_id=0af7651916cd43dd8448eb211c80319c"
   ```

2. **Tempo** — paste the trace_id into Explore > Tempo to see the full trace.

---

## Send multiple events (demo sequencing)

Increment the last two hex digits to create unique, traceable events:

```bash
# Event 01
curl -X POST http://${MACHINE_IP}:25001/ingest \
  -H "traceparent: 00-${TRACE_ID_PREFIX}01-${SPAN_ID}-01" \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice"}'

# Event 02
curl -X POST http://${MACHINE_IP}:25001/ingest \
  -H "traceparent: 00-${TRACE_ID_PREFIX}02-${SPAN_ID}-01" \
  -H "Content-Type: application/json" \
  -d '{"event": "signup", "user": "bob"}'

# Event 03
curl -X POST http://${MACHINE_IP}:25001/ingest \
  -H "traceparent: 00-${TRACE_ID_PREFIX}03-${SPAN_ID}-01" \
  -H "Content-Type: application/json" \
  -d '{"event": "purchase", "user": "charlie"}'
```

Query all three at once:

```logql
{filename=~"/logs/(producer|consumer)/.+"} |= "trace_id=deadbeefdeadbeefdeadbeefdeadbe"
```

---

## Cross-signal correlation (the magic)

Grafana's real power is linking signals without typing queries:

| Direction | How | What to click |
|-----------|-----|---------------|
| **Log → Trace** | `derivedFields` on the Loki datasource | Click a highlighted `trace_id` in any log line → opens the trace in Tempo |
| **Trace → Logs** | `traceToLogs` on the Tempo datasource | Click a span in a waterfall → open the **Logs** tab → shows related Loki entries |

These are configured in `grafana/datasources/loki.yml` and
`grafana/datasources/tempo.yml`.

---

## Reference

| What | Where |
|------|-------|
| Example queries | [`queries.md`](queries.md) |
| Tracing architecture | [`docs/implement-traces.md`](docs/implement-traces.md) |
| Dashboard | [`grafana/dashboards/overview.json`](grafana/dashboards/overview.json) |
