# Terminal 3 — Go Consumer (RabbitMQ → stdout)

This terminal runs a Go program that listens for messages on a RabbitMQ queue and prints them.

Make sure **Terminal 1 (RabbitMQ)** is already running before starting this one.

---

## 1. Install Go (if not installed)

**macOS (Homebrew):**
```bash
brew install go@1.22
```

**Ubuntu / Debian:**
```bash
# Download & install Go 1.22+
wget https://go.dev/dl/go1.22.5.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.22.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

**Verify:**
```bash
go version
# Should show go 1.22.x
```

---

## 2. Clone the repo & go to the consumer directory

```bash
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/go-consumer
```

---

## 3. Download Go dependencies

```bash
go mod tidy
```

Downloads `github.com/rabbitmq/amqp091-go` (Go RabbitMQ client).

---

## 4. Run the consumer

```bash
go run main.go
```

You should see:
```
Waiting for messages on queue "events" ...
```

The consumer will print every message it receives.

---

## 5. Verify end-to-end

Send a POST request from **Terminal 2** or another shell:

```bash
curl -X POST http://localhost:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice", "timestamp": "2026-05-18T12:00:00Z"}'
```

In **this** terminal you should see:
```
Received: map[event:page_view timestamp:2026-05-18T12:00:00Z user:alice]
```

---

## Environment variables (optional)

Same as the producer — both must point to the **same** RabbitMQ instance and queue.

| Variable | Default | Purpose |
|---|---|---|
| `RABBITMQ_HOST` | `localhost` | RabbitMQ server address |
| `RABBITMQ_QUEUE` | `events` | Queue name |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASS` | `guest` | RabbitMQ password |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `dial tcp: connect: connection refused` | RabbitMQ is not running — go back to Terminal 1 |
| `go: go.mod file not found` | You're in the wrong directory — `cd go-consumer` |
| Module download fails | Check internet connection, or set `GOPROXY=https://proxy.golang.org,direct` |
