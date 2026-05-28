# Terminal 4 — Loki (Log Storage)

This terminal runs Loki so Alloy can forward logs to it and Grafana can query them.

Make sure **Terminal 1 (RabbitMQ)** is running first so logs exist to tail.

---

## 1. Create a shared Docker network

All three Grafana services (Loki, Alloy, Grafana) need to be on the same network so they can find each other by container name.

```bash
docker network create grafana-net
```

---

## 2. Start Loki

Choose **one** of the following:

### Option A — Foreground (logs visible in terminal)

```bash
# Run from the grafana/ directory
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/grafana

docker run --rm \
  --name loki \
  --network grafana-net \
  -p 3100:3100 \
  grafana/loki:latest
```

The container prints Loki's own startup logs here. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
docker run -d \
  --name loki \
  --network grafana-net \
  -p 3100:3100 \
  grafana/loki:latest
```

**Verify:**
```bash
curl -s http://localhost:3100/ready
# Should print "ready"
```

**View logs live:**
```bash
docker logs -f loki
```

---

## 3. Keep running

Loki must stay running for **Terminal 5 (Alloy)** and **Terminal 6 (Grafana)** to work.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 3100 already in use | `lsof -i :3100` to find the process, then stop it |
| `network grafana-net not found` | Run `docker network create grafana-net` first |
| Container already exists | `docker rm -f loki` then re-run the `docker run` command |
