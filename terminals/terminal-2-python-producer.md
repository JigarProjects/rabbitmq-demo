# Terminal 2 — Python Producer (REST → RabbitMQ)

This terminal runs a Flask API that accepts JSON events via POST and publishes them to RabbitMQ.

Make sure **Terminal 1 (RabbitMQ)** is already running before starting this one.

---

## 1. Install Python (if not installed)

**macOS (Homebrew):**
```bash
brew install python@3.13
```

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

**Verify:**
```bash
python3 --version
```

---

## 2. Clone the repo & go to the producer directory

```bash
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/python-producer
```

---

## 3. Create & activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

---

## 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

Installs `flask` (web framework) and `pika` (RabbitMQ client).

---

## 5. Run the producer

First make sure the log directory exists so Alloy can pick up the logs later:

```bash
mkdir -p ../logs/producer
```

Then start the server with `LOG_DIR` pointing to that directory:

```bash
LOG_DIR=../logs/producer OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14317 OTEL_SERVICE_NAME=python-producer python app.py
```

The server starts on `http://0.0.0.0:25001`.

---

## 6. Send a test event (from another terminal)

```bash
curl -X POST http://localhost:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice", "timestamp": "2026-05-18T12:00:00Z"}'
```

Expected response: `{"status": "published"}` (HTTP 201)

You should see the event appear in **Terminal 3 (Go Consumer)**.

---

## Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|---|---|
| `RABBITMQ_HOST` | `localhost` | RabbitMQ server address |
| `RABBITMQ_QUEUE` | `events` | Queue name |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASS` | `guest` | RabbitMQ password |
| `LOG_DIR` | `/app/logs` | Directory for log output (`producer.log`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:14317` | OTLP gRPC endpoint for trace export |
| `OTEL_SERVICE_NAME` | `python-producer` | Service name displayed in traces |

Set them before running, e.g.:
```bash
export RABBITMQ_HOST=192.168.1.50
LOG_DIR=../logs/producer OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14317 python app.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pika.exceptions.AMQPConnectionError` | RabbitMQ is not running — go back to Terminal 1 |
| Port 25001 in use | Kill the other process: `lsof -ti :25001 | xargs kill` |
| `pip: command not found` | Make sure the virtual environment is activated (`source .venv/bin/activate`) |

---

## Docker (alternative to local Python)

If you prefer to run the producer in a container instead of a local Python process:

### Build the image

```bash
docker build -t python-producer python-producer/
```

### Option A — Foreground (logs visible in terminal)

```bash
# Create the log directory first
mkdir -p logs/producer

docker run --rm \
  -p 25001:25001 \
  -e RABBITMQ_HOST=host.docker.internal \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:14317 \
  -e OTEL_SERVICE_NAME=python-producer \
  -v ./logs/producer:/app/logs \
  --name python-producer \
  python-producer
```

The container prints logs directly to this terminal. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
# Create the log directory first
mkdir -p logs/producer

docker run -d \
  -p 25001:25001 \
  -e RABBITMQ_HOST=host.docker.internal \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:14317 \
  -v ./logs/producer:/app/logs \
  --name python-producer \
  python-producer
```

**View logs live (background mode):**
```bash
docker logs -f python-producer
```

**Stop the container:**
```bash
docker stop python-producer
```
