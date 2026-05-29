# Grafana Datasources

Files in this folder are automatically provisioned into Grafana.

Grafana container mounts this directory to `/etc/grafana/provisioning/datasources/` and reads every `*.yml` file on startup to auto-configure data sources.

Current datasources:

| File | Name | Type | URL |
|------|------|------|-----|
| `loki.yml` | Loki | loki | http://loki:3100 |
| `mimir.yml` | Mimir | prometheus | http://mimir:9009/prometheus |

To add a new datasource, create a new `.yml` file here and restart Grafana.
