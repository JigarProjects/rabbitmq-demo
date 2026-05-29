# RabbitMQ Ingest Pipeline

Two services that communicate via RabbitMQ:

- **python-producer/** – REST API that accepts JSON via POST and publishes to a RabbitMQ queue.
- **go-consumer/** – CLI consumer that reads messages from the same queue and prints them.

---

## 1. RabbitMQ Installation

### macOS (Homebrew)

```bash
brew install rabbitmq
brew services start rabbitmq
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y rabbitmq-server
sudo systemctl enable --now rabbitmq-server
```

### Docker (any OS)

```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4-management
```

- **AMQP port:** `5672`
- **Management UI:** `http://localhost:15672` (guest/guest)

---

## 2. Python Producer (REST → RabbitMQ)

### Install dependencies

```bash
cd python-producer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

The server starts on `http://0.0.0.0:25001`.

### Send data

```bash
curl -X POST http://localhost:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice", "timestamp": "2026-05-18T12:00:00Z"}'
```

### Environment variables

| Variable         | Default   | Description            |
|------------------|-----------|------------------------|
| `RABBITMQ_HOST`  | localhost | RabbitMQ server host   |
| `RABBITMQ_QUEUE` | events    | Queue name             |
| `RABBITMQ_USER`  | guest     | RabbitMQ username      |
| `RABBITMQ_PASS`  | guest     | RabbitMQ password      |
| `LOG_DIR`        | /app/logs | Directory for `producer.log` |

---

## 3. Go Consumer (RabbitMQ → stdout)

### Install dependencies

```bash
cd go-consumer
go mod tidy
```

### Build & run

```bash
go run main.go
```

The consumer will print every message it receives from the queue.

### Environment variables

Same as the Python producer – both must point to the same RabbitMQ instance and queue name.

| Variable   | Default   | Description            |
|------------|-----------|------------------------|
| `LOG_DIR`  | /app/logs | Directory for `consumer.log` |

---

## Architecture

```
Machine A                    Network               Machine B
┌──────────────┐     POST     ┌──────────┐    AMQP    ┌──────────────┐
│  Python REST │ ─────────→ │ RabbitMQ │ ────────→ │  Go Consumer  │
│  (producer)  │  :25001    │  :5672   │           │  (consumer)   │
└──────────────┘             └──────────┘           └──────────────┘
                                  │
                          logs/rabbitmq/rabbitmq.log
```

Set `RABBITMQ_HOST` to the RabbitMQ machine's IP/hostname on both the producer and consumer.

---

## Observability stack

See `grafana/README.md` for the full observability setup (Loki + Alloy + Grafana) or `terminals/` for step-by-step instructions to run each component individually.
