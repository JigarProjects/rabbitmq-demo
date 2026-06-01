# Terminal 8 — Tempo (Trace Storage)

This terminal runs Tempo so the producer and consumer can export traces to it and Grafana can query them.

Make sure **Terminal 5 (Alloy)** is up — Alloy receives OTLP traces from the producer and consumer and forwards them to Tempo.

---

## 1. Start Tempo

```bash
# Run from the grafana/ directory
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/grafana
```

### Option A — Foreground (logs visible in terminal)

```bash
docker run --rm \
  --name tempo \
  --network grafana-net \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 3200:3200 \
  -v ./tempo/tempo.yml:/etc/tempo/tempo.yml:ro \
  grafana/tempo:latest \
  -config.file=/etc/tempo/tempo.yml
```

Tempo's own logs appear here. Press `Ctrl+C` to stop.

### Option B — Background (frees up terminal)

```bash
docker run -d \
  --name tempo \
  --network grafana-net \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 3200:3200 \
  -v ./tempo/tempo.yml:/etc/tempo/tempo.yml:ro \
  grafana/tempo:latest \
  -config.file=/etc/tempo/tempo.yml
```

**Verify:**
```bash
curl -s http://localhost:3200/ready
# Should print "ready"
```

**View logs live:**
```bash
docker logs -f tempo
```

---

## 2. Check it's ready to receive traces

```bash
# Tempo API — list recent traces (may be empty until apps send data)
curl -s http://localhost:3200/api/search
```

You should get an empty result `{}` or `{"traces":[]}` — that's fine. Once Terminal 2 and Terminal 3 are running and sending events, traces will appear here.

---

## 3. Explore in Grafana

1. Open http://localhost:3000
2. Go to **Explore** (☰ menu → Explore)
3. Select the **Tempo** data source
4. Search by trace ID or service name once traces are flowing

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port 4317/4318/3200 already in use | `lsof -i :4317` to find the process, then stop it |
| `network grafana-net not found` | Run `docker network create grafana-net` first |
| Container already exists | `docker rm -f tempo` then re-run the `docker run` command |
| `config.file` not found | Make sure `tempo/tempo.yml` exists and you're running from `grafana/` |
| No traces visible | Make sure Terminal 2 (producer) and Terminal 3 (consumer) are running and receiving events |
