# Observability / Telemetry Stack — Current-State Audit (2026-09-04)

Workspace-wide audit backing the observability rebuild. Facts only; design decisions live in the
design doc. Every claim carries a file reference.

## 1. Topology

| Repo | Role | Telemetry posture |
|---|---|---|
| `api/` | FastAPI **gateway** (`flynapse_api`); mounts `core`, `copilot-mro`, `shift-optimizer` as sub-apps | The only place OTel is initialised per-request. Owns logging / request-id / observability middleware. |
| `copilot-mro/` | RAG + agent service (also standalone) | Emits spans + some metrics; owns the LLM spend ledgers and `debug_dumps` |
| `core/` | Identity/RBAC/automations/comments + **frontend log ingest** + **Loki-backed product analytics API** | loguru only; zero OTel |
| `utils/` | Shared lib — **the entire OTel implementation lives here** | `utils/observability/{tracing,metrics}.py`, `utils/logging_config.py`, `utils/llm.py` |
| `dashboard/` | Next.js 15 product frontend (Amplify SSR) | ~1,650 LOC telemetry layer, **delivery disabled** |
| `shift-optimizer/` | loguru only | zero OTel, zero metrics |
| `telegram-bot/` | stdlib logging + hand-rolled in-process counters | never exported |
| `llm-platform/` | generates a `prometheus-scrape.yml` artifact for vLLM `/metrics` | no app telemetry |
| `lambdas/` | loguru to stdout | zero OTel |
| `website/` | Next.js 14 (Vercel) | Vercel Analytics + Speed Insights — **the only live frontend telemetry in the estate** |
| `iac/` | Terraform | no CloudWatch log groups, no X-Ray, no ADOT |

## 2. What actually works today

- **Structured request logging** — `api/flynapse_api/middleware/logging.py:59-68` binds
  `request_id, tenant_id, user_id, session_id, method, path, user_agent, client_ip` via
  `logger.contextualize`. `request_id`/`session_id` minted in `middleware/request_id.py:36-66`.
- **Log shipping** — loguru → custom OTLP sink (`utils/utils/logging_config.py:132-238`) → otel-collector
  → Loki OTLP. No promtail/fluent-bit/vector anywhere. Trace correlation injected only inside that sink
  (`logging_config.py:209-211` sets `otelTraceID`/`otelSpanID`).
- **HTTP metrics** — `http_requests_total`, `http_request_duration_seconds`, `active_sessions`,
  `active_users` from `api/flynapse_api/middleware/observability.py:105-162`.
- **LLM metrics (direct calls only)** — `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`,
  `llm_tokens_per_request`, `embedding_*` from `utils/utils/llm.py:351-1193`.
- **Document-hub metrics** — ~14 counters + 1 histogram, `copilot-mro/.../document_hub/operations.py:20-42`.
- **A handful of spans** — server span (`observability.py:64-76`), `chat.enhanced_chat[_stream]`,
  `rag.pipeline.execute`, `db.chat.save_block`, `agent_sdk.run_query` + backdated
  `agent_sdk.tool.<name>` children (`agent_claude/loop_observability.py:208-242`).
- **Two durable Postgres LLM ledgers** — the real cost system, complete and RLS-protected:
  - `llm_usage` (one row per turn) — `copilot-mro/.../postgres_table_definitions_modules/llm_usage.py:73-191`.
    `total_cost_usd`, `cost_complete`, token breakdown incl. cache read/write, `cache_hit_rate`,
    `is_error`, `loop_error`. NULL cost = "not measured", never zero.
  - `llm_model_calls` (one row per governed model attempt) — `.../llm_model_calls.py:66-200`.
    `provider/model/deployment/region`, `cost_source`, `cost_estimated`, `usage_estimated`,
    `latency_seconds`, `outcome`, `graph_node`, `attempt`.
  - Plus `automation_runs.cost_usd` (core) and `improvement_runs.llm_spend`.
- **Product analytics API** — `core/core/resources/analytics/analytics_endpoints.py:43`
  `GET /analytics/chat-quality`, served by `services/chat_quality_service.py` (894 LOC) which runs
  raw LogQL against Loki (`:832-880`) and aggregates in Python. 300 s cache, 60 req/min per tenant.

## 3. Gaps and defects

### G1 — Frontend telemetry is collected then discarded (CRITICAL)
`dashboard/lib/logging/logger.ts` — both delivery calls in `flush()` are commented out
(`:233-243` public, `:257-266` authenticated), commit `5c9b1c8`, 2026-02-19. The disable is
**deliberate and documented**: `NOTE when restoring this call: the throw must stay a
LogDeliveryError` — a plain `Error` is classified transient by `isRetryableLogFailure`, and a
permanently-rejected batch is re-queued to the FRONT forever, wedging every later log. Shipping was
switched off instead of fixing the classification.

Consequences:
- Zero frontend error visibility in production (`next.config.mjs:22` `removeConsole` in prod, so no
  console either). `ErrorBoundary.tsx:88` tells users "Our team has been notified" — false.
- All 21 panels of `frontend-perf-dashboard.json` are dark.
- Product settings panel **Most Accessed Documents** returns empty for every tenant, every time range
  (`chat_quality_service.py:69` selects `page_view`, emitted only by `page-tracking.ts:62`).
- Web Vitals, long tasks, memory, navigation timing, dwell, bounce, interaction rate: all lost.

### G2 — Browser OTel exports to localhost in production
`dashboard/lib/observability/otel.ts:37` falls back to `runtime-config.ts:90-93`
`http://localhost:4318/v1/traces`. `OTEL_EXPORTER_OTLP_ENDPOINT` is **not** in the `amplify.yml`
env allowlist, there is no `/otlp` route or rewrite in the Next app, and the collector lives on a
private IP (`iac/apprunner.tf:42`, `iac/lambda.tf:109`). Every browser span dies; failures swallowed
at `otel.ts:85-91`. `propagateTraceHeaderCorsUrls: [/.*/]` injects `traceparent` on every request
regardless.

### G3 — Prometheus client is entirely decorative
`copilot-mro/copilot_mro/app/main.py:239-245` serves `/metrics` via `generate_latest()`, gateway
redirects to it (`api/flynapse_api/main.py:372-379`) behind an `X-Metrics-Token` gate. **No `Counter`,
`Gauge`, `Histogram` or `CollectorRegistry` is constructed anywhere in the workspace.** The endpoint
serves default `python_gc_*` / `process_*` collectors only. `prometheus.yml` doesn't even scrape it.

### G4 — Zero auto-instrumentation
`opentelemetry-instrumentation-fastapi` and `-instrumentation-logging` are declared in
`api/pyproject.toml:26-27` and `copilot-mro/pyproject.toml:81-82` but **never imported**. There are no
httpx / psycopg / sqlalchemy / boto3 / redis instrumentors at all. Outbound HTTP, Postgres, Weaviate,
Redis and Bedrock calls produce **no spans**. Traces are a handful of hand-rolled spans with nothing
underneath them.

### G5 — No trace context propagation outbound
`utils/utils/observability/tracing.py:171-180` extracts W3C headers inbound. There is **no
`propagate.inject` call anywhere**. Every cross-process hop (automations worker, lambdas,
telegram-bot → api) starts a new disconnected trace.

### G6 — Tempo receives spans that nobody looks at
Tempo is deployed in 4 compose files with `span-metrics` + `service-graphs` remote-writing to
Prometheus and is wired as a Grafana datasource — and **not one dashboard panel queries it**. The span
attributes carrying every dollar (`sdk.total_cost_usd`, `sdk.combined_cost_usd`, set at
`loop_observability.py:109-136`) are exported and viewed by nobody.

### G7 — Dashboards query metrics that were never emitted
| Query target | Panels affected | Reality |
|---|---|---|
| `pipeline_steps_total`, `pipeline_step_duration_seconds` | 9 in `chat-metrics-dashboard.json` | zero emitters; names come from the synthetic load generator `deployment/observability-local/test-observability.py:99-122` |
| Loki `"Completed pipeline step"` | 4 | never logged |
| Loki `"LlamaIndexService returned chunks"` | 1 | never logged |
| `rag_retrieval_score` | 1 | never emitted |
| `agent_validation_failures_total` | 1 | never emitted |
| Loki `"Tool Routing Decision"` | **product** panel `router_intent_distribution` (`chat_quality_service.py:66-69`) | string exists only inside the query — this panel is served to tenant admins and always returns empty |
| `DOCUMENT_HUB_QNA_TOTAL/_LATENCY_SECONDS/_NO_EVIDENCE_TOTAL` | declared `operations.py:28-32` | zero call sites |

`chat-metrics-dashboard.json` is **11 of 21 panels dead**.

### G8 — LLM cost is invisible to every dashboard
`llm-metrics-dashboard.json` reads `llm_*` OTel metrics from `utils/utils/llm.py`, a path the Claude
Agent SDK loop **never traverses** — so the largest share of spend is missing from those series. There
is no USD panel anywhere, no Grafana Postgres datasource, and no frontend surface reading `llm_usage`
or `llm_model_calls`. The complete, indexed, durable cost record has no consumer except the
automation budget gate (`api/flynapse_api/automations/executor.py:378-460`).

### G9 — `RuntimeTelemetry` is dead code
`copilot-mro/.../agent_shared/telemetry.py:23-48` defines 17 OTel instruments (`agent.turn.calls`,
`agent.model.{input,output,reasoning,cache_read,cache_write}_tokens`, `agent.model.cost_usd`,
`agent.tool.calls`, `agent.subagent.*`, span `agent.turn`). Referenced **only** by
`tests/unit/agent_shared/test_telemetry.py`. `services/lang_agent/runtime_factory.py` never
constructs it. This is the agent-observability layer, already written, entirely unwired.

### G10 — Tenant filtering happens after the Loki fetch
`chat_quality_service.py:841-847` queries with `limit: 5000`, `direction: "forward"` and **no
tenant selector in the LogQL**; `:434-437` and `:646-648` drop non-matching rows in Python. On a busy
multi-tenant deployment the limit is exhausted by other tenants' logs before reaching the caller's,
silently returning empty or partial panels. The code knows — `:876-880` logs *"Loki query hit limit;
results may be truncated"* — a warning the UI never surfaces.

### G11 — Loki is a hard runtime dependency of a product feature
The customer-facing settings dashboard cannot render without a reachable Loki
(`core/core/config.py:73`, default `http://localhost:3100`, queried anonymously with no auth header).
A log-aggregation outage becomes a product outage, and the observability backend can never be swapped
without breaking the product.

### G12 — Service-label fragmentation
Dashboards and the product analytics API hardcode `{service_name="copilots"}`. That label is correct
only because `api/Dockerfile:88` sets `OTEL_SERVICE_NAME=copilots` and the gateway calls
`setup_logging` (`main.py:7`) before importing `copilot_mro`. A standalone `copilot-mro` logs as
`mro-copilot-rag` (`config.py:953`) and the automations worker as `automation-worker`
(`worker.py:109`) — **both invisible to every dashboard and to the product analytics API**.

### G13 — `OTEL_ENABLED` is a half-switch
`utils/utils/logging_config.py:119` gates only the log pipeline. `get_tracing_service()` and
`get_metrics_service()` never consult it, so `OTEL_ENABLED=false` still builds a TracerProvider and
MeterProvider pointed at `OTEL_ENDPOINT`.

### G14 — Config split-brain
`setup_logging`, `tracing.py:93` and `metrics.py:131` read the endpoint from **`utils.config`**, not
from the calling service's settings. The per-repo `otel_*` settings supply only service
name/env/version. Setting `OTEL_ENDPOINT` on `api` alone does not move the exporters.

### G15 — Logs are not JSON on stdout
`logging_config.py:89-90` — `"{time} | {level} | {name}:{function}:{line} - {message} | {extra}"`,
where `{extra}` is a Python dict repr. Structure exists **only** on the OTLP path. Any cloud-native
log collector that reads stdout (CloudWatch agent, Fluent Bit sidecar, Azure Monitor) gets
unparseable text.

### G16 — Prompt/completion capture is filesystem-only and dev-gated
`copilot-mro/copilot_mro/app/services/_debug_dump.py:195-217` writes to
`<repo>/debug_dumps/<agent>/<chat_id>/<block_id>/...`, gated on `settings.debug` (default `False`),
3-day retention. Not queryable, not shipped, absent in production. There is no LLM trace/eval store —
no Langfuse/LangSmith/Phoenix/OpenLLMetry/Arize (`api/tests/unit/infra/test_no_langsmith_integration.py`
actively asserts LangSmith's absence).

### G17 — Operational and security hygiene
- `otel-collector-config.yaml` runs `service.telemetry.logs.level: debug` and a `debug` exporter with
  `verbosity: detailed` on **every** pipeline — full payload dumps in collector stdout.
- Grafana is `admin/admin` (`observe-docker-compose.yml`); `iac/ec2.tf:96-110` opens 3000/9090/3100/3200
  on the shared Weaviate host.
- Collector `prometheus` exporter name normalization (unit + `_total` suffixes) may mean the real
  series are `http_requests_total_total` etc. — dashboard queries assume un-normalized spellings.
  Needs verification against a live collector.
- `observability-local/README.md:6,22` documents a Jaeger endpoint that does not exist.
- No alerting anywhere: no Alertmanager rules, no Grafana alert rules, no CloudWatch alarms.
- No SLOs, no error-budget definitions.

## 4. Grafana dashboard inventory

`copilot-mro/deployment/observability-local/grafana/dashboards/` — 8 provisioned JSONs, zero Tempo panels.

| Dashboard | Panels | Verdict |
|---|---|---|
| `backend-metrics-dashboard.json` | 5 | LIVE |
| `chat-metrics-dashboard.json` | 21 | **11 dead** (G7) |
| `llm-metrics-dashboard.json` | 6 | 5 live but SDK-loop-blind (G8); no USD panel |
| `frontend-perf-dashboard.json` | 21 | **all dark** (G1) |
| `document-viewer-metrics-dashboard.json` | 4 | PromQL panels live; `Top 10 Pages by Distinct Users` dead (G1) |
| `chat-quality-dashboard.json` | 5 | LIVE — the original the product settings page was ported from. `New Chats Created`, `Last 10 Chat Messages`, `Last 10 Chats` were never ported. |
| `comments-service-dashboard.json` | — | LIVE |
| `authorization-metrics-dashboard.json` | 4 | all filtered on `path=~".*/test-cookie"` — titled "Authorization", keyed on one legacy cookie-probe path |

## 5. Product settings dashboard inventory

Route `/settings/department/dashboard`, page
`dashboard/app/(dashboard)/settings/department/dashboard/page.tsx` (631 LOC),
`DepartmentChatQualityPage`. Recharts via a dynamic import of `features/chat/ChartCard`.
Tabbed — one panel renders at a time, one request per panel. Time ranges `1h/1d/1w/1m`, default `1h`.
Authz: `RouteGuard` on `VIEW_DASHBOARD` + backend `is_tenant_admin` (`analytics_endpoints.py:31-41`).

| # | Panel | Chart | Status |
|---|---|---|---|
| 1 | Top 10 Users by Message Count | bar | live |
| 2 | Active Users Over Time | line | live |
| 3 | Message Volume Over Time | line | live (duplicate LogQL of #1, cached separately) |
| 4 | LLM Token Consumption | line ×3 series | live; `estimated_cost`, `distinct_messages`, `total_llm_calls` returned but **never rendered** |
| 5 | Chat Time Duration Histogram | bar | live |
| 6 | Query Type Distribution | pie | **DEAD** (G7 — `Tool Routing Decision`) |
| 7 | Most Accessed Documents | bar | **DEAD** (G1 — `page_view`) |
| 8 | Feedback Received Over Time | line ×3 | live |
| 9 | Top 10 Users by Comment Count | bar | live |
| 10 | Comments Created Over Time | line | live (duplicate LogQL of #9) |

Only one filter exists in the whole surface: `model_name` on panel #4. No auto-refresh, no manual
refresh. Every failure — 429, Loki timeout, Loki down — collapses to
`'Failed to load chat quality data.'` (`page.tsx:381`).

## 6. Deployment reality

- **Local/POC/demo**: otel-collector + Prometheus + Loki + Tempo + Grafana in
  `observability-local/observe-docker-compose.yml`, and again inside `deployment/docker-compose.yml`,
  `deployment/poc/docker-compose.yml`, `deployment/demo/docker-compose.yml`.
- **AWS today** (`iac/`): a single `t2.large` `aws_instance.weaviate_observability` running Weaviate
  **and** the whole observability stack (`ec2.tf:2-36`). App Runner and Lambda point
  `OTEL_ENDPOINT` at its private IP.
- **`docs/production-architecture.md`** describes an ECS-on-EC2 stack with a dedicated observability
  instance pool and a shared 500 GB gp3 volume. Nothing in `iac/` implements it. The doc is also stale:
  it assumes DynamoDB (retired for Postgres) and Azure OpenAI (Bedrock is in use).
