# Log Format — Lessons Learned

## The problem

Old log format used brackets around key=value pairs:

```
[trace_id=179593dbf2dd2465096b0226e792df1c span_id=eb5b6bbcbf872562]: map[...]
```

This caused two issues:

1. **Logfmt parser** sees `[trace_id` (with bracket) as the key name. Grafana Drilldown UI displays it as `_trace_id` — inconsistent naming.
2. **No space** between `span_id=<value>` and `]:` — logfmt captures `<value>]:` as the span_id value (includes `]` and `:`).

Tempo's "Logs for this span" sends `trace_id=<value>` as a filter, but Drilldown stores the field as `_trace_id`. Mismatch → no results.

## The fix

Removed brackets and added spaces:

```
trace_id=%s span_id=%s : %s
```

```
trace_id=179593dbf2dd2465096b0226e792df1c span_id=eb5b6bbcbf872562 : map[...]
```

- Logfmt now parses clean `trace_id` and `span_id` — no brackets, no garbage characters.
- `tracesToLogs` uses a raw LogQL line filter (`|=`) instead of field filter, so it doesn't depend on field naming conventions.

## Lesson

Keep log formats simple. Brackets around key=value pairs seem harmless visually but break structured parsing. Use space-delimited `key=value` format for logfmt-compatible logs.
