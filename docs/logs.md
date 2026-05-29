# Logs Collection

Alloy tails log files from disk and forwards them to Loki, which Grafana queries for visualization.

```
log files ──> Alloy ──> Loki (storage) ──> Grafana
```

---

## File Discovery — `local.file_match`

Tells Alloy which files to watch. The pattern `**/*.log` picks up every `.log` file recursively under `/logs/`.

```alloy
local.file_match "logs" {
    path_targets = [
        {"__path__" = "/logs/**/*.log"},
    ]
}
```

Every discovered file gets a `__path__` attribute used as a label downstream.

---

## Log Tailing + Processing — `loki.source.file`

Tails the discovered files and applies processing stages before forwarding.

```alloy
loki.source.file "scrape" {
    targets    = local.file_match.logs.targets
    forward_to = [loki.write.loki.receiver]
}
```

### Component Label Extraction

A regex stage extracts the directory name from the file path as a `component` label.

```alloy
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

This produces labels like `component="consumer"`, `component="producer"`, `component="rabbitmq"`.

In Grafana Explorer filter by:

```
{component="consumer"}
{component="producer"}
{component="rabbitmq"}
```

---

## Forwarding to Loki — `loki.write`

Pushes all received log entries to Loki.

```alloy
loki.write "loki" {
    endpoint {
        url = "http://loki:3100/loki/api/v1/push"
    }
}
```

---

## Source Log Files

| Service | File path | Written by |
|---------|-----------|------------|
| Python producer | `logs/producer/producer.log` | Python `logging` module |
| Go consumer | `logs/consumer/consumer.log` | Go `log` package |
| RabbitMQ | `logs/rabbitmq/rabbitmq.log` | RabbitMQ built-in logging |

---

## Processing Stages

Stages run on every log line and can parse, filter, or transform it.

| Stage | What it does | Example use |
|-------|-------------|-------------|
| `stage.drop` | Drop lines matching a condition | Silence noisy debug logs |
| `stage.multiline` | Merge lines that belong together (e.g. stack traces) | Capture full Go/Python panic trace as one entry |
| `stage.json` | Parse JSON log lines into structured labels | Extract `level`, `service` from `{"level":"error","msg":"..."}` |
| `stage.logfmt` | Parse logfmt lines into labels | Extract fields from `level=error msg="oops"` |
| `stage.regex` | Extract values via regex | Pull out status codes, durations |
| `stage.timestamp` | Override the log timestamp | Use the app's own timestamp instead of file mtime |
| `stage.template` | Transform content with Go templates | Add prefix, reformat message |
| `stage.output` | Forward only a specific portion | Send just the message without metadata |
| `stage.static_labels` | Add constant labels | `{"app": "my-project"}` |

Example — parse JSON logs and promote `level` to a label:

```alloy
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

## Processing Order

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

## Auto-discovery (alternative)

Instead of mounting log files, Alloy can discover running Docker containers and tail their stdout/stderr directly.

```alloy
discovery.docker "containers" {
    host = "unix:///var/run/docker.sock"
}

docker.source "logs" {
    host       = "unix:///var/run/docker.sock"
    targets    = discovery.docker.containers.targets
    forward_to = [loki.write.loki.receiver]
}
```

This replaces `local.file_match` + `loki.source.file` — no volume mounts needed.

---

## Tips

- **Label cardinality** — avoid unique values per log line (e.g. request IDs) as labels. Use them in the log content instead.
- **Stage order matters** — a `stage.regex` must come before `stage.labels` if you want to use the capture group as a label.
- **Alloy UI** — open `http://localhost:12345` to see component health and pipeline status.
