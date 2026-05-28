# Terminal 6 — Grafana (Dashboard)

This terminal runs Grafana so you can visualise logs collected by Loki.

Make sure **Terminal 4 (Loki)** is running — Grafana connects to Loki as its data source.

---

## 1. Start Grafana

```bash
# Run from the grafana/ directory
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/grafana
```

### Option A — Foreground (logs visible in terminal)

```bash
docker run --rm \
  --name grafana \
  --network grafana-net \
  -p 3000:3000 \
  -v ./datasources:/etc/grafana/provisioning/datasources \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  grafana/grafana:latest
```

Grafana's own logs appear here. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
docker run -d \
  --name grafana \
  --network grafana-net \
  -p 3000:3000 \
  -v ./datasources:/etc/grafana/provisioning/datasources \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  grafana/grafana:latest
```

**View logs live:**
```bash
docker logs -f grafana
```

---

## 2. Open Grafana

Open http://localhost:3000 in your browser.

- **Anonymous login** is enabled — you should get straight in as Admin.
- The **Loki** data source is already provisioned (from `./datasources/loki.yml`).

---

## 3. Explore logs

1. Go to **Explore** (☰ menu → Explore).
2. Select the **Loki** data source.
3. Click **"Log browser"** then **"Find labels"** → select a `filename` to see logs from a specific service.
4. Click **"Run query"** to fetch logs.

Example LogQL queries:

```logql
# All logs
{filename="/logs/consumer/consumer.log"}

# Producer logs
{filename="/logs/producer/producer.log"}

# Filter by log level
{filename="/logs/consumer/consumer.log"} |= "error"
```

---

## 4. Keep running

Keep Grafana open in the browser while you send test requests from **Terminal 2**. The logs should appear in Explore within a few seconds (Alloy tails the files and pushes to Loki continuously).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 3000 already in use | `lsof -i :3000` to find the process, then stop it |
| `dial tcp: lookup loki` | Loki is not running — go back to Terminal 4 |
| Data source not showing in Explore | Check the datasource file: `ls -l ./datasources/loki.yml` |
| Container already exists | `docker rm -f grafana` then re-run the `docker run` command |
