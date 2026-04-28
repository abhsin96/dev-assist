# Observability runbook

Every request through DevHub carries a single `trace_id` (a UUID) that links:

| System | Where to look | How `trace_id` appears |
|---|---|---|
| **structlog** (API logs) | stdout / log aggregator | `"trace_id": "<uuid>"` field on every line |
| **Sentry** (errors) | sentry.io → Issues | Custom tag `trace_id` on the event |
| **LangSmith** (agent runs) | smith.langchain.com | Metadata key `trace_id` on the run |

---

## 1. Find a request end-to-end

### Step 1 — Get the trace_id

**From the browser:**
Open DevTools → Network, pick any API call, look for the `X-Request-Id` response header. That value is the `trace_id`.

**From a Sentry alert:**
Open the event → *Additional Data* → `trace_id` tag.

**From a user report:**
Ask them to open DevTools → Console and run:
```js
// assuming the app stores the last trace_id
localStorage.getItem('last_trace_id')
```

---

### Step 2 — Find it in API logs

```bash
# Local dev
docker compose -f infra/docker/docker-compose.yml logs api | grep '<trace_id>'

# Production (adjust to your log aggregator)
# Datadog: @trace_id:<uuid>
# Grafana Loki: {app="devhub-api"} |= "<uuid>"
```

Every log line for that request will include `trace_id`, `run_id` (when an agent is running), and `user_id`.

---

### Step 3 — Find it in Sentry

1. Go to **Issues** → search `trace_id:<uuid>`.
2. Or open **Performance** → paste the trace_id in the search bar.

---

### Step 4 — Find it in LangSmith

1. Open [smith.langchain.com](https://smith.langchain.com) → your project (`devhub-ai`).
2. Filter runs by metadata: `trace_id = <uuid>`.
3. The run shows the full agent graph, tool calls, token counts, and latency.

---

## 2. Correlate a Sentry error to an agent run

1. Copy `trace_id` from the Sentry event tag.
2. In LangSmith, search `trace_id = <value>` → open the run.
3. The run's `state.errors` list shows the structured error that surfaced.

---

## 3. Silence a noisy structlog logger

```python
import logging
logging.getLogger("noisy.library").setLevel(logging.ERROR)
```

Or set `LOG_LEVEL=WARNING` in `.env` to raise the global floor.

---

## 4. Enable OTLP export (optional)

Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` in `.env` to send spans to a local Tempo / Jaeger instance. The API will auto-detect the env var and activate the OTLP exporter.

---

## 5. Redacted fields

The following request headers are **never** logged:

- `Authorization`
- `Cookie`
- `X-Api-Key`
- `X-Auth-Token`
- `Set-Cookie`

Sentry is configured with `send_default_pii=False`.
