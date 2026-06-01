# Terminal 4 — Test Event Generator

This terminal runs a script that continuously sends random events to the Python Producer, simulating real traffic.

Make sure **Terminal 1 (RabbitMQ)**, **Terminal 2 (Python Producer)**, and **Terminal 3 (Go Consumer)** are all running before starting this one.

---

## 1. Navigate to the test directory

```bash
cd ~/JR_2025/Projects/may_observability/rabbitmq-ingest/test
```

---

## 2. Run the tester

### Default — 1 event per second, unlimited

```bash
python send_events.py
```

### Custom rate and count

```bash
python send_events.py --rate 2 --count 20
```

Sends 2 events per second, stops after 20 events.

### Very slow — 1 event every 10 seconds

```bash
python send_events.py --rate 0.1
```

### Custom endpoint

```bash
python send_events.py --url http://localhost:25001/ingest
```

---

## Options

| Flag | Default | Description |
|---|---|---|
| `--url` | `http://localhost:25001/ingest` | Producer endpoint URL |
| `--rate` | `1` | Events per second (float) |
| `--users` | `5` | Number of distinct simulated user IDs |
| `--count` | `0` | Total events to send (`0` = unlimited) |

---

## Event types

Events alternate randomly among: `page_view`, `click`, `purchase`, `login`, `logout`, `signup`, `error`, `search`.

---

## Verify traces in Grafana

While the tester is running, open Grafana at [http://localhost:3000](http://localhost:3000) and use the **Explore** tab with the Tempo datasource to search for traces by service name (`python-producer` or `go-consumer`).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` | Producer is not running — go back to Terminal 2 |
| No consumer traces in Tempo | Wait up to 30s for the next consumer poll cycle |
