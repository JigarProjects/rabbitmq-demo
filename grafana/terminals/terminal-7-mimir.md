# Terminal 7 — Mimir (Metrics Storage)

This terminal runs Mimir so Alloy can forward scraped metrics to it and Grafana can query them.

Make sure **Terminal 5 (Alloy)** is running — Mimir needs Alloy to be pushing metrics.

---

## 1. Start Mimir

```bash
# Run from the grafana/ directory
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/grafana
```

### Option A — Foreground (logs visible in terminal)

```bash
docker run --rm \
  --name mimir \
  --network grafana-net \
  -p 9009:9009 \
  -v ./mimir/mimir.yml:/etc/mimir/mimir.yml:ro \
  grafana/mimir:latest \
  --config.file=/etc/mimir/mimir.yml
```

Mimir's own logs appear here. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
docker run -d \
  --name mimir \
  --network grafana-net \
  -p 9009:9009 \
  -v ./mimir/mimir.yml:/etc/mimir/mimir.yml:ro \
  grafana/mimir:latest \
  --config.file=/etc/mimir/mimir.yml
```

**Verify:**
```bash
curl -s http://localhost:9009/ready
# Should print "Ready"
```

**View logs live:**
```bash
docker logs -f mimir
```

---

## 2. Check metrics are arriving

```bash
curl -s 'http://localhost:9009/prometheus/api/v1/query?query=up'
```

You should see three targets (rabbitmq, producer, consumer).

---

## 3. Explore in Grafana

1. Open http://localhost:3000
2. Go to **Explore** (☰ menu → Explore)
3. Select the **Mimir** data source
4. Query `up`, `flask_http_request_total`, `go_goroutines`, etc.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 9009 already in use | `lsof -i :9009` to find the process, then stop it |
| `network grafana-net not found` | Run `docker network create grafana-net` first |
| Container already exists | `docker rm -f mimir` then re-run the `docker run` command |
| No metrics arriving | Make sure Alloy (Terminal 5) is running and config points to `mimir:9009` |

---

## Useful queries

```promql
# Target health
up

# Request rate (producer)
rate(flask_http_request_total[1m])

# Go runtime metrics (consumer)
go_goroutines
go_memstats_alloc_bytes

# RabbitMQ metrics
rabbitmq_queue_messages_ready
rabbitmq_queue_messages_unacked
```
