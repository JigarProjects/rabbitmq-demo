# Terminal 1 — RabbitMQ (Message Broker)

This terminal starts RabbitMQ so the producer and consumer can connect to it.

---

## 1. Install Docker (if not installed)

**macOS:**
```bash
brew install --cask docker
open /Applications/Docker.app
# wait for the whale icon to appear in menu bar
```

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y docker.io
sudo systemctl enable --now docker
```

**Verify:**
```bash
docker --version
```

---

## 2. Start RabbitMQ

Choose **one** of the following:

### Option A — Foreground (logs visible in terminal)

```bash
# Create the log directory first
mkdir -p logs/rabbitmq

docker run --rm \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_LOGS=/var/log/rabbitmq/rabbitmq.log \
  -v ./logs/rabbitmq:/var/log/rabbitmq \
  rabbitmq:4-management
```

The container prints logs directly to this terminal. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
# Create the log directory first
mkdir -p logs/rabbitmq

docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_LOGS=/var/log/rabbitmq/rabbitmq.log \
  -v ./logs/rabbitmq:/var/log/rabbitmq \
  rabbitmq:4-management
```

- **AMQP port** (`5672`) — producer & consumer connect here.
- **Management UI** (`15672`) — open `http://localhost:15672` in a browser (guest/guest) to inspect queues.

**Verify it's running:**
```bash
docker logs rabbitmq --tail 5
```

**View logs live (background mode):**
```bash
docker logs -f rabbitmq
```

---

## 3. Keep running

RabbitMQ must stay running for the next two terminals to work.

- **Foreground mode** — the container is already running in this terminal; logs are visible live.
- **Background mode** — check logs at any time with `docker logs rabbitmq` or live-tail with `docker logs -f rabbitmq`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 5672 already in use | `lsof -i :5672` to find the process, then stop it |
| Docker daemon not running | Open Docker Desktop or run `sudo systemctl start docker` |
| Container already exists | `docker rm -f rabbitmq` then re-run the `docker run` command |
