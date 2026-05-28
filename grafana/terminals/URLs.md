# Service URLs

| Service | URL | Credentials | Terminal |
|---|---|---|---|
| **RabbitMQ Management UI** | http://localhost:15672 | `guest` / `guest` | 1 |
| **Producer API** (Flask) | http://localhost:25001 | — | 2 |
| **Loki** (HTTP API) | http://localhost:3100 | — | 4 |
| **Alloy** (UI / health) | http://localhost:12345 | — | 5 |
| **Grafana** (dashboards) | http://localhost:3000 | anonymous (Admin) | 6 |

## Quick checks

```bash
# RabbitMQ management
open http://localhost:15672

# Producer health
curl -s http://localhost:25001/ingest -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Loki readiness
curl -s http://localhost:3100/ready

# Alloy health
curl -s http://localhost:12345/-/health

# Grafana
open http://localhost:3000
```
