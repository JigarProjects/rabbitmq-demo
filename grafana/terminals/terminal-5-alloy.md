# Terminal 5 — Grafana Alloy (Log Collector)

This terminal runs Alloy, which tails the `./logs/**/*.log` files and forwards them to Loki.

Make sure **Terminal 1 (RabbitMQ)**, **Terminal 2 (Producer)** and **Terminal 3 (Consumer)** are running so there are log files to tail. Also make sure **Terminal 4 (Loki)** is running — Alloy needs the Loki endpoint.

---

## 1. Start Alloy

```bash
# Run from the grafana/ directory
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/grafana
```

### Option A — Foreground (logs visible in terminal)

```bash
docker run --rm \
  --name alloy \
  --network grafana-net \
  -p 12345:12345 \
  -v ./alloy/config.alloy:/etc/alloy/config.alloy:ro \
  -v ../logs:/logs:ro \
  grafana/alloy:latest \
  run /etc/alloy/config.alloy \
  --server.http.listen-addr=0.0.0.0:12345
```

Alloy prints its own logs here. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
docker run -d \
  --name alloy \
  --network grafana-net \
  -p 12345:12345 \
  -v ./alloy/config.alloy:/etc/alloy/config.alloy:ro \
  -v ../logs:/logs:ro \
  grafana/alloy:latest \
  run /etc/alloy/config.alloy \
  --server.http.listen-addr=0.0.0.0:12345
```

**View logs live:**
```bash
docker logs -f alloy
```

---

## 2. Verify it's forwarding logs

Send a test event from **Terminal 2**:

```bash
curl -X POST http://localhost:25001/ingest \
  -H "Content-Type: application/json" \
  -d '{"event": "page_view", "user": "alice", "timestamp": "2026-05-18T12:00:00Z"}'
```

Then check the Alloy logs:

```bash
docker logs alloy --tail 5
```

You should see Alloy picking up the log file changes.

You can also query Loki directly:

```bash
curl -s "http://localhost:3100/loki/api/v1/label/filename/values"
# Shows all log files being collected: /logs/producer/producer.log, /logs/consumer/consumer.log, /logs/rabbitmq/rabbitmq.log
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `dial tcp: lookup loki` | Loki is not running — go back to Terminal 4 |
| `no such file or directory` for config | Make sure you're in the `grafana/` directory |
| Port 12345 already in use | `lsof -i :12345` to find the process, then stop it |
| Container already exists | `docker rm -f alloy` then re-run the `docker run` command |
