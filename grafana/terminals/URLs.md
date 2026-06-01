# Service URLs

| Service | URL | Credentials | Terminal |
|---|---|---|---|
| **RabbitMQ Management UI** | http://localhost:15672 | `guest` / `guest` | 1 |
| **RabbitMQ Prometheus** | http://localhost:15692/metrics | — | 1 |
| **Producer API** (Flask) | http://localhost:25001 | — | 2 |
| **Loki** (HTTP API) | http://localhost:3100 | — | 4 |
| **Alloy** (UI / health) | http://localhost:12345 | — | 5 |
| **Grafana** (dashboards) | http://localhost:3000 | anonymous (Admin) | 6 |
| **Mimir** (API) | http://localhost:9009 | — | 7 |
| **Tempo** (OTLP gRPC) | `localhost:4317` | — | 8 |
| **Tempo** (OTLP HTTP) | `localhost:4318` | — | 8 |
| **Tempo** (API / search) | http://localhost:3200 | — | 8 |

## Quick checks

```bash
# RabbitMQ management
open http://localhost:15672

# RabbitMQ Prometheus metrics
curl -s http://localhost:15692/metrics | head -5

# Producer health
curl -s http://localhost:25001/ingest -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Producer Prometheus metrics
curl -s http://localhost:25001/metrics | head -5

# Consumer Prometheus metrics
curl -s http://localhost:2112/metrics | head -5

# Loki readiness
curl -s http://localhost:3100/ready

# Alloy health
curl -s http://localhost:12345/-/health

# Mimir readiness
curl -s http://localhost:9009/ready

# Tempo readiness
curl -s http://localhost:3200/ready

# Grafana
open http://localhost:3000
```
