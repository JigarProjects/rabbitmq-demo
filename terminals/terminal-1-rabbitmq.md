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

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:4-management
```

- **AMQP port** (`5672`) — producer & consumer connect here.
- **Management UI** (`15672`) — open `http://localhost:15672` in a browser (guest/guest) to inspect queues.

**Verify it's running:**
```bash
docker logs rabbitmq --tail 5
```

---

## 3. Keep running

Leave this terminal open — RabbitMQ must stay running for the next two terminals to work.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 5672 already in use | `lsof -i :5672` to find the process, then stop it |
| Docker daemon not running | Open Docker Desktop or run `sudo systemctl start docker` |
| Container already exists | `docker rm -f rabbitmq` then re-run the `docker run` command |
