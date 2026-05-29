# Grafana Alloy Configuration

Alloy sits between your log files and Loki. It tails `.log` files, optionally processes each line, and pushes the result to Loki so Grafana can query it.

## What We Have Now

### File Discovery — `local.file_match`

Tells Alloy which files to watch. The pattern `**/*.log` picks up every `.log` file recursively under `/logs/`.

```
local.file_match "logs" {
    path_targets = [
        {"__path__" = "/logs/**/*.log"},
    ]
}
```

Every discovered file gets a `__path__` attribute that downstream components use as a label.

---

### Log Tailing + Processing — `loki.source.file`

Tails the discovered files and applies processing stages before forwarding.

```
loki.source.file "scrape" {
    targets    = local.file_match.logs.targets
    forward_to = [loki.write.loki.receiver]
}
```

**Component label extraction** (what we added):

```
loki.source.file "scrape" {
    targets    = local.file_match.logs.targets
    forward_to = [loki.write.loki.receiver]

    stage.regex {
        expression = "/(?P<component>[^/]+)/[^/]+\\.log$"
        source     = "filename"
    }

    stage.labels {
        values = {
            component = "component",
        }
    }
}
```

This extracts the directory name from the file path as a `component` label. For example `consumer`, `producer`, or `rabbitmq`.

In Grafana Explorer you can then filter by:

```
{component="consumer"}
{component="producer"}
{component="rabbitmq"}
```

instead of the full file path.

---

### Forwarding to Loki — `loki.write`

Pushes all received log entries to a Loki instance.

```
loki.write "loki" {
    endpoint {
        url = "http://loki:3100/loki/api/v1/push"
    }
}
```

You can add multiple endpoints (e.g. dev Loki and prod Loki) by repeating the `endpoint` block or using separate `loki.write` components.

---

## What Else Can Be Added

### Processing Stages

Stages run on every log line and can parse, filter, or transform it.

| Stage | What it does | Example use |
|-------|-------------|-------------|
| `stage.drop` | Drop lines that match a condition | Silence noisy debug logs |
| `stage.multiline` | Merge lines that belong together (e.g. stack traces) | Capture full Go/Python panic trace as one entry |
| `stage.json` | Parse JSON log lines into structured labels | Extract `level`, `service` from `{"level":"error","msg":"..."}` |
| `stage.logfmt` | Parse logfmt lines into labels | Extract fields from `level=error msg="oops"` |
| `stage.regex` | Extract values via regex (already used above) | Pull out status codes, durations |
| `stage.timestamp` | Override the log timestamp with a value from the line | Use the app's own timestamp instead of file mtime |
| `stage.template` | Transform content with Go templates | Add prefix, reformat message |
| `stage.output` | Forward only a specific portion of the log line | Send just the message without metadata to Loki |
| `stage.static_labels` | Add constant labels | `{"app": "my-project"}` |

Example — parse Go consumer JSON logs and promote `level` to a label:

```
stage.json {
    expressions = {
        level     = "level",
    }
    source = "line"
}

stage.labels {
    values = {
        level = "level",
    }
}
```

---

### Metrics from Logs

Generate Prometheus-style metrics from log patterns using `loki.process` + `prometheus` components.

```
loki.process "metrics" {
    forward_to = [loki.write.loki.receiver]

    stage.metrics {
        counter {
            name        = "log_errors_total"
            description = "Total error log lines"
            prefix      = "app"
            match_all   = true
            action      = "inc"

            stage.match {
                selector = `{component="consumer"} |= "error"`
            }
        }
    }
}
```

This creates a `app_log_errors_total` metric you can scrape with Prometheus.

---

### Multiple Loki Outputs

Send different component logs to different Loki tenants or instances.

```
loki.write "prod" {
    endpoint {
        url        = "http://prod-loki:3100/loki/api/v1/push"
        tenant_id  = "production"
    }
}

loki.write "dev" {
    endpoint {
        url        = "http://dev-loki:3100/loki/api/v1/push"
        tenant_id  = "development"
    }
}
```

Route logs based on component:

```
loki.source.file "scrape" {
    ...
    forward_to = [loki.process.route.receiver]
}

loki.process "route" {
    stage.static_labels {
        values = { "env" = "production" }
    }

    forward_to = [loki.write.prod.receiver]

    stage.match {
        selector = `{component="consumer"}`
        forward_to = [loki.write.dev.receiver]
    }
}
```

---

### Auto-discovery — `discovery.docker`

Instead of mounting log files manually, Alloy can discover running containers and tail their stdout/stderr directly.

```
discovery.docker "containers" {
    host = "unix:///var/run/docker.sock"
}

docker.source "logs" {
    host       = "unix:///var/run/docker.sock"
    targets    = discovery.docker.containers.targets
    forward_to = [loki.write.loki.receiver]
}
```

This replaces `local.file_match` + `loki.source.file` entirely — no volume mounts needed.

---

### Prometheus Metrics Scraping

Alloy can also act as a Prometheus scraper for your app metrics endpoints.

```
prometheus.scrape "app" {
    targets = [
        {"__address__" = "producer:25001", "job" = "producer"},
        {"__address__" = "consumer:2112",  "job" = "consumer"},
    ]
    forward_to = [prometheus.remote_write.mimir.receiver]
}

prometheus.remote_write "mimir" {
    endpoint {
        url = "http://mimir:9009/api/v1/push"
    }
}
```

---

### Tempo Tracing — `otelcol.receiver.otlp`

Receive OpenTelemetry traces and forward to Tempo.

```
otelcol.receiver.otlp "traces" {
    grpc {
        endpoint = "0.0.0.0:4317"
    }

    output {
        traces = [otelcol.exporter.otlp.tempo.input]
    }
}

otelcol.exporter.otlp "tempo" {
    client {
        endpoint = "tempo:4317"
    }
}
```

---

### Relabeling — `loki.relabel`

Modify, drop, or rename labels before they reach the output.

```
loki.relabel "cleanup" {
    forward_to = [loki.write.loki.receiver]

    rule {
        action       = "replace"
        target_label = "filename"
        replacement  = "/logs/... (trimmed)"
    }

    rule {
        action        = "drop"
        regex         = "healthcheck"
        source_labels = ["__path__"]
    }
}
```

---

## Order of Processing

When multiple stages are defined, they run in this order:

1. `stage.drop`
2. `stage.multiline`
3. `stage.json` / `stage.logfmt` / `stage.regex` / `stage.template`
4. `stage.labels` / `stage.static_labels`
5. `stage.timestamp`
6. `stage.output`
7. `stage.metrics`
8. `stage.match` (routing)

---

## Tips

- **Label cardinality** — avoid unique values per log line (e.g. request IDs) as labels. Use them in the log content instead.
- **Stage order matters** — a `stage.regex` must come before `stage.labels` if you want to use the capture group as a label.
- **Test with `--dry-run`** — Alloy does not have a built-in dry-run mode, but you can inspect processed logs by adding a `stage.logfmt` or `stage.json` to see parsed output.
- **Alloy UI** — open `http://localhost:12345` to see component health, pipeline status, and debug info.
