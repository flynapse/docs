# 01 — Backend telemetry inventory + adversarial verification of the 2026-09-04 audit

Research deliverable for the observability/telemetry rebuild. Written 2026-09-05, READ-ONLY pass over
`/home/aditya/Code` (worktrees `copilot-mro-s41/`, `copilot-mro-s44h/` excluded). Every claim carries a
`path:line`. Where I could not find something I say "not found" rather than guessing.

Scope split: **Part 1** re-verifies the audit (`docs/plans/observability-rebuild-audit.md`) as a
skeptic — CONFIRMED / PARTIAL / REFUTED with quoted evidence, plus new gaps G18+. **Part 2** is the
backend ground-truth inventory (metrics, traces, logs, LLM paths, dependency instrumentation,
background work, config).

---

# PART 1 — Verification of the audit

## 1.1 Audit §2 "What actually works today"

| # | Audit claim | Verdict | Evidence |
|---|---|---|---|
| 2.1 | Structured request logging binds `request_id, tenant_id, user_id, session_id, method, path, user_agent, client_ip` via `logger.contextualize`, `logging.py:59-68` | **CONFIRMED** | `api/flynapse_api/middleware/logging.py:59` `with logger.contextualize(` … `:68` `client_ip=client_ip,`. All eight fields present, `:59-68` exact. |
| 2.2 | `request_id`/`session_id` minted in `request_id.py:36-66` | **CONFIRMED** | `api/flynapse_api/middleware/request_id.py:40` `request_id = str(uuid.uuid4())`; `:48` `session_id = _minted_session_id()`; reserved-namespace guard `:49-59`. |
| 2.3 | loguru → custom OTLP sink `logging_config.py:132-238` → collector → Loki OTLP; no promtail/fluent-bit/vector | **CONFIRMED** | `utils/utils/logging_config.py:132` `def _setup_otel_integration(`; sink `:179 def otel_sink(message)`; `:233 logger.add(otel_sink, level=log_level, format="{message}")`. Collector logs pipeline → `otlphttp/logs: endpoint: http://loki:3100/otlp` (`copilot-mro/deployment/observability-local/otel-collector-config.yaml:58-59`). No promtail/fluentbit/vector file found anywhere. |
| 2.4 | Trace correlation injected only inside that sink (`:209-211`) | **CONFIRMED** | `logging_config.py:209-211` `if span_context.is_valid: log_record.otelTraceID = …` / `otelSpanID`. |
| 2.5 | HTTP metrics `http_requests_total`, `http_request_duration_seconds`, `active_sessions`, `active_users` from `observability.py:105-162` | **PARTIAL** | Names CONFIRMED (`api/flynapse_api/middleware/observability.py:106,118,130,135`). Line range is wrong: the success path is `:105-136`, the error path is a *second* pair at `:150-171`. Also — the error path records **only** `http_request_duration_seconds` + `http_requests_total`, never the two gauges, and hardcodes `status_code="500"` for **every** exception. |
| 2.6 | LLM metrics `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request`, `embedding_*` from `utils/llm.py:351-1193` | **CONFIRMED** (range slightly off) | `utils/utils/llm.py:350,358` (requests/duration), `:350-364` token counters inside `_record_token_metrics`, `:799`, `:1179-1193`, `:1299-1304`. Emit sites actually span `:350-1304`, not `:351-1193`. |
| 2.7 | Document-hub metrics — "~14 counters + 1 histogram, `operations.py:20-42`" | **PARTIAL / undercounted** | The file declares **20 name constants** at `copilot-mro/copilot_mro/app/services/document_hub/operations.py:20-48` (audit stops at `:42`, missing `DOCUMENT_HUB_ATTEMPT_VECTOR_CLEANUP_TOTAL:42` and `DOCUMENT_HUB_QUERY_EMBEDDING_FALLBACK_TOTAL:46-48`). **14 are emitted, 6 are dead** (see G7 row below). Only 1 is emitted as a histogram (`processing.py:554-560`). |
| 2.8 | "A handful of spans" — server span, `chat.enhanced_chat[_stream]`, `rag.pipeline.execute`, `db.chat.save_block`, `agent_sdk.run_query`, `agent_sdk.tool.<name>` | **PARTIAL — the span list is right, its attribute inventory is badly incomplete** | Span names CONFIRMED: `observability.py:64-76`, `chat_management.py:1106,1115,1230,1425,1434,1617`, `orchestrator.py:2607-2616`, `loop_observability.py:233`. **Missed**: the root span also carries `sdk.answer_found`, `sdk.judge_passed`, `sdk.confidence_probability`, `sdk.numeric_fidelity`, `sdk.figures_were_fed` (`orchestrator.py:3209-3218`) and **span events** `sdk.synthesis_judged` (one per synthesis scope, `orchestrator.py:3224-3242`). |
| 2.8b | Path of `loop_observability.py` given as `copilot-mro/.../agent_claude/loop_observability.py` | **REFUTED (path wrong)** | The file is `copilot-mro/copilot_mro/app/services/agent_shared/loop_observability.py`. There is no `agent_claude/loop_observability.py`. Same wrong path is repeated in G6. |
| 2.9 | Two durable Postgres LLM ledgers `llm_usage` / `llm_model_calls`; NULL cost = "not measured" | **CONFIRMED** | See Part 2 §4. |
| 2.10 | Product analytics API `GET /analytics/chat-quality`, raw LogQL against Loki `:832-880`, 300 s cache, 60 req/min per tenant | **CONFIRMED** | `core/core/resources/analytics/analytics_endpoints.py:43`; `chat_quality_service.py:832 async def _query_loki(`; cache TTL default 300 (`core/core/config.py:74-76`), rate limit 60/60 s (`core/core/config.py:77-82`). |

### §2 items the audit omits entirely (all verified, all live)
- **`chat_block_save_failures_total`** counter — `copilot-mro/copilot_mro/app/api/chat_management.py:363`.
- **`memory_search_latency_ms`** histogram — `copilot-mro/copilot_mro/app/services/memory/memory_index.py:555`.
- **`memory_get_latency_ms`** histogram — `copilot-mro/copilot_mro/app/services/memory/memory_db.py:836`.
So the real emitted-metric surface is **HTTP 4 + LLM/embedding ~8 + doc-hub 14 + 3 orphans = ~29 series families**, not the audit's implied ~20.


---

## 1.2 Gaps G1–G17

| Gap | Verdict | Evidence / correction |
|---|---|---|
| **G1** Frontend telemetry collected then discarded | **CONFIRMED** | `dashboard/lib/logging/logger.ts:233-243` public `fetch` commented out (`:233 //const publicResponse = await fetch(publicUrl, {`), `:257-266` authenticated `fetchWithAuth` commented out, both preceded by `// NOTE when restoring this call: the throw must stay a 'LogDeliveryError'`. Prod console stripped: `dashboard/next.config.mjs:22` `removeConsole: process.env.NODE_ENV === 'production'`. |
| **G2** Browser OTel exports to localhost in production | **PARTIAL — the mechanism is worse than stated, not better** | The in-code fallback is a *relative* path, not localhost: `dashboard/lib/observability/otel.ts:37` `const otlpUrl = (runtime as any).OTEL_EXPORTER_OTLP_ENDPOINT \|\| '/otlp/v1/traces';`. The localhost default enters through `dashboard/lib/runtime-config.ts:90-93` `OTEL_EXPORTER_OTLP_ENDPOINT: readEnv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4318/v1/traces')` — which is `getServerRuntimeConfig()`, so *whichever* value wins, the browser posts either to the user's own localhost or to a path with no route behind it (`grep rewrites dashboard/next.config.mjs` → no match). `propagateTraceHeaderCorsUrls: [/.*/]` confirmed at `otel.ts:60` and `:71`; failures swallowed at `:86-90`. Net effect identical to the audit's claim; the causal chain in the audit is one hop off. |
| **G3** Prometheus client entirely decorative | **CONFIRMED** | `copilot-mro/copilot_mro/app/main.py:239-245` `return Response(content=generate_latest(), …)`; gateway `api/flynapse_api/main.py:372-379`. Workspace-wide search for `from prometheus_client import` returns exactly two hits: that endpoint and the synthetic load generator `copilot-mro/deployment/observability-local/test-observability.py:27`. `prometheus.yml:9-18` scrapes only `localhost:9090` and `otel-collector:9464` — the app endpoint is not a target. |
| **G4** Zero auto-instrumentation | **CONFIRMED** | `api/pyproject.toml:26-27` and `copilot-mro/pyproject.toml:81-82` declare `opentelemetry-instrumentation-fastapi` / `-logging`. Workspace-wide search for `Instrumentor` or `.instrument()` → **zero hits**. `core/pyproject.toml`, `shift-optimizer/pyproject.toml`, `telegram-bot/pyproject.toml` declare no `opentelemetry` dependency at all. |
| **G5** No trace-context propagation outbound | **CONFIRMED (backend)**, with a frontend caveat the audit missed | `utils/utils/observability/tracing.py:171-180` `ctx = extract(parent_headers or {})` — inbound only. Search for `propagate.inject` across all Python repos → **zero hits**. Caveat: the dashboard *does* hand-roll a W3C header — `dashboard/lib/api/utils.ts:52` `// --- Simple W3C traceparent generator (propagation only) ---`, `:81 function buildTraceparent(traceId?: string)`. So the backend server span *can* receive a parent, from a generator that shares no state with the browser OTel SDK. |
| **G6** Tempo receives spans nobody looks at | **CONFIRMED, and worse** | Tempo datasource wired with `serviceMap`+`spanMetrics` → prometheus (`grafana/provisioning/datasources/datasources.yml:21-32`); generator remote-writes to Prometheus (`tempo.yaml:21-33`, `overrides.defaults.metrics_generator.processors: [service-graphs, span-metrics]` `:40-43`). Zero dashboard JSON references Tempo. **Additionally**: `tempo.yaml:17-19` `compactor.compaction.block_retention: 1h` — traces are discarded after **one hour**, so even ad-hoc trace lookup is impossible past the current hour. Span-attribute path corrected: `agent_shared/loop_observability.py:109-136` (not `agent_claude/`). |
| **G7** Dashboards query metrics never emitted | **CONFIRMED for the effect; the provenance claim is REFUTED** | All seven dead targets verified as zero-emitter (workspace-wide search): `pipeline_step_duration_seconds`, `Completed pipeline step`, `LlamaIndexService returned chunks`, `rag_retrieval_score`, `agent_validation_failures_total`, `Tool Routing Decision` (only hit is the query itself, `chat_quality_service.py:68`). **REFUTED**: the audit says the names "come from the synthetic load generator `test-observability.py:99-122`" — that generator emits `rag_requests_total`, `rag_request_duration_seconds`, `rag_active_sessions`, **`rag_pipeline_steps_total`**, `rag_token_usage` (`test-observability.py:100,104,110,116,122`). None of those five names appears in any dashboard, and none of the dashboards' dead names appears in the generator. The dead names came from somewhere else (deleted code, most likely). **Doc-hub row corrected**: 6 constants are dead, not 3 — `DOCUMENT_HUB_QNA_TOTAL`, `_QNA_LATENCY_SECONDS`, `_QNA_SELECTED_DOCUMENTS`, `_QNA_RETRIEVAL_HITS`, `_QNA_NO_EVIDENCE_TOTAL`, `_QNA_CITATIONS` (`operations.py:28-33`) all have zero non-declaration references. |
| **G8** LLM cost invisible to every dashboard | **PARTIAL — right conclusion, wrong reason** | "A path the Claude Agent SDK loop never traverses" is true only of the **SDK loop's own model turns**. Every other model call in a turn *does* traverse `utils/llm.py` and *does* emit `llm_requests_total`/`llm_tokens_total`: `call_bedrock_messages` (`utils/utils/llm.py:691`) funnels through `recorded_llm_call` (`:724`), and the streaming synthesis path is explicitly metered by `accumulate_bedrock_cost` (`:754`, counter at `:799`). The real defect is sharper: **there is no `llm_cost_usd` metric at all.** The only USD *metric* anywhere is `embedding_cost_usd` (`utils/utils/llm.py:1189-1191`) — and no dashboard reads it either. Confirmed: no Grafana Postgres datasource (`datasources.yml` has only Prometheus/Loki/Tempo), and the only consumer of the ledgers is `api/flynapse_api/automations/executor.py`. |
| **G9** `RuntimeTelemetry` is dead code | **CONFIRMED** | `copilot-mro/copilot_mro/app/services/agent_shared/telemetry.py:18-131` defines 15 instruments + the `agent.turn` span (`:56`). Workspace-wide references: the class definition, its own `__all__` (`:134`), and `copilot-mro/tests/unit/agent_shared/test_telemetry.py:18,21,29`. Nothing else. (Count correction: the audit says 17 instruments; the real count is **12 counters** (`:23,28,29,30,31,32,33,34,37,42,43,44`) + **3 histograms** (`:24,38,45`) = **15 instruments**, plus the `agent.turn` span.) |
| **G10** Tenant filtering happens after the Loki fetch | **CONFIRMED** | `core/.../chat_quality_service.py:841-847` `"limit": settings.analytics_loki_query_limit, "direction": "forward"`; default 5000 (`core/core/config.py:83-85`). None of the nine `LOGQL_*` constants (`chat_quality_service.py:59-96`) carries a tenant selector — every one is `{service_name="copilots"}` plus a line filter. Truncation warning at `:888-891`. |
| **G11** Loki is a hard runtime dependency of a product feature | **CONFIRMED** | `core/core/config.py:73` `loki_base_url: str = Field(default="http://localhost:3100", alias="LOKI_BASE_URL")`; `chat_quality_service.py:850-856` issues a bare `client.get(url, params=params)` with **no auth header and no `X-Scope-OrgID`**; any failure → `raise RuntimeError("Failed to query Loki")`. |
| **G12** Service-label fragmentation | **CONFIRMED, with one nuance** | `api/Dockerfile:88` `ENV OTEL_SERVICE_NAME="copilots"`; `api/flynapse_api/main.py:7` `setup_logging(settings.otel_service_name, settings.otel_env)`; standalone default `copilot-mro/copilot_mro/app/config.py:953` `default="mro-copilot-rag"`; worker `api/flynapse_api/automations/worker.py:111` `SERVICE_NAME = "automation-worker"`. Nuance: `worker.py:469` `setup_logging(os.getenv("OTEL_SERVICE_NAME") or SERVICE_NAME, …)` — so if the worker inherits a stack-wide `OTEL_SERVICE_NAME=copilots` it *is* visible; the invisibility is conditional on the deployment, not unconditional. `utils/utils/config.py:106` adds a **third** default (`flynapse-utils`). |
| **G13** `OTEL_ENABLED` is a half-switch | **CONFIRMED** | `utils/utils/logging_config.py:119` `if otel_enabled:` is the only read. `get_tracing_service` (`tracing.py:230-240`) and `get_metrics_service` (`metrics.py:488-508`) never consult it; both unconditionally construct a provider pointed at `settings.otel_endpoint`. Default is `True` anyway (`utils/utils/config.py:107`). |
| **G14** Config split-brain | **CONFIRMED** | `utils/utils/observability/tracing.py:93` `from ..config import settings`; `metrics.py:131` same; `logging_config.py:243` `from .config import settings`. All three read **`utils.config.Settings`**, whose `otel_endpoint` alias is `OTEL_ENDPOINT` (`utils/utils/config.py:103-105`). The per-repo `otel_*` settings only supply the *arguments* (name/env/version). |
| **G15** Logs are not JSON on stdout | **CONFIRMED** | `utils/utils/logging_config.py:89-90` `"{time:YYYY-MM-DD HH:mm:ss} \| {level: <8} \| " "{name}:{function}:{line} - {message} \| {extra}"`. `{extra}` renders as a Python dict repr. The two **file** sinks (`:101-116`) use the same unparseable format. |
| **G16** Prompt/completion capture is filesystem-only and dev-gated | **CONFIRMED as stated, but materially incomplete — see G18** | `copilot-mro/copilot_mro/app/services/_debug_dump.py:195-218` `dump_debug`, `:199 if not _debug_enabled(): return`, `:207-213` nests under `debug_dumps/<agent>/<group…>/`, `:25 _RETENTION_SECONDS = 3 * 24 * 60 * 60`. No Langfuse/LangSmith/Phoenix/OpenLLMetry/Arize dependency anywhere; `api/tests/unit/infra/test_no_langsmith_integration.py` exists. **But** raw user prompts *are* shipped off-box on the log path — G18. |
| **G17a** Collector debug verbosity | **CONFIRMED** | `otel-collector-config.yaml:74-76` `service.telemetry.logs.level: debug`; `:61-63` `debug: verbosity: detailed`; `debug` is an exporter on **all four** pipelines (`:82,88,94,100`). |
| **G17b** Grafana `admin/admin`; EC2 ports open | **CONFIRMED, with two corrections** | `observe-docker-compose.yml:64-65` `GF_SECURITY_ADMIN_USER=admin` / `…PASSWORD=admin`. Correction 1: that same file binds Grafana to loopback (`:62 "127.0.0.1:3000:3000"`), so on the local stack the admin/admin is not internet-reachable. Correction 2: `iac/ec2.tf:96` opens far more than 3000/9090/3100/3200 — `for_each = [22, 8080, 50051, 7777, 3000, 9090, 3100, 3200, 4317, 4318, 9464, 13133, 1777, 14250, 14268, 8000, 9443]`, i.e. **the OTLP receivers, the collector's zpages/pprof (`1777`, `13133`) and the Prometheus exporter (`9464`) too**, to `var.allowed_ssh_ip` (`iac/variables.tf:372-375`, **no default — operator-supplied**) and again to the App Runner + Lambda security groups (`ec2.tf:107-115`). `pprof` on `1777` is a remote heap/CPU-profile door. |
| **G17c** Collector `prometheus` exporter name normalization | **REFUTED for every metric actually emitted** | Full reasoning in §1.3 below. Short version: names round-trip **unchanged**; there is no `http_requests_total_total`. |
| **G17d** README documents a Jaeger endpoint that doesn't exist | **CONFIRMED (and broader)** | `copilot-mro/deployment/observability-local/README.md` mentions Jaeger at lines **9, 23, 44, 84, 86, 142, 176** — not just `:6,22`. No `jaeger` service in any compose file. |
| **G17e** No alerting, no SLOs | **CONFIRMED** | `prometheus.yml:5-7` `rule_files:` fully commented out; no `alertmanager` service in any compose file; no `aws_cloudwatch_metric_alarm` / `aws_sns_topic` alert resource in `iac/`; no Grafana `alerting/` provisioning directory. |

---

## 1.3 G17c decided — what the Prometheus series are actually named

The audit flags this as "needs verification against a live collector". It can be decided from the
config plus the exporter's documented defaults; no live collector needed.

**Inputs.**
1. Exporter config is `prometheus: endpoint: "0.0.0.0:9464"` and nothing else
   (`otel-collector-config.yaml:46-49`). So every other field takes its default:
   `add_metric_suffixes: true`, `resource_to_telemetry_conversion.enabled: false`,
   `metric_expiration: 5m`, `namespace: ""`, `enable_open_metrics: false`.
2. Image is `otel/opentelemetry-collector:latest` (`observe-docker-compose.yml:6`) — the core
   distribution, which contains `prometheusexporter`.
3. **Every metric in this estate is auto-registered with the default unit `"1"`.** There is not a
   single `register_metrics` / `register_counter` / `register_histogram` call site anywhere in the
   workspace (verified by workspace-wide search). All emission goes through
   `increment_counter` / `record_histogram` / `set_gauge`, whose auto-registration branches pass only
   a name and a generated description: `utils/utils/observability/metrics.py:366`
   `self.register_counter(name, f"Counter metric: {name}")`, `:391` `self.register_histogram(name, …)`,
   `:416` `self.register_up_down_counter(name, …)` — and `register_*` default `unit: str = "1"`
   (`:179, :199, :219`).

**The translation rules** (`pkg/translator/prometheus`, used by `prometheusexporter` when
`add_metric_suffixes` is true):
- The name is tokenised on non-alphanumerics; a unit suffix is appended **only if** the OTel unit maps
  to a non-empty Prometheus unit **and** that token is not already present in the name.
- The OTel→Prom unit map sends `"1" → ""` (empty). An empty mapped unit appends nothing.
- `_total` is appended for **monotonic sums only**, and the implementation removes any existing
  `total` token before appending it — so an already-`_total` name is idempotent.
- `_ratio` is appended only when unit is `"1"` **and** the instrument is an OTel *Gauge*.

**Consequences for the metrics this estate emits:**

| Emitted OTel name | Instrument (as built here) | Unit | Prometheus series |
|---|---|---|---|
| `http_requests_total` | Counter (monotonic Sum) | `1` | `http_requests_total` — the existing `total` token is removed then re-appended. **No `_total_total`.** |
| `http_request_duration_seconds` | Histogram | `1` | `http_request_duration_seconds` (+`_bucket`/`_sum`/`_count`). Unit `1`→empty, so no second `_seconds`. |
| `active_sessions`, `active_users` | **UpDownCounter** (`set_gauge` → `register_up_down_counter`, `metrics.py:416`) | `1` | `active_sessions`, `active_users`. Non-monotonic Sum ⇒ no `_total`; not a Gauge ⇒ no `_ratio`. |
| `llm_requests_total`, `llm_tokens_total`, `embedding_*_total` | Counter | `1` | unchanged |
| `llm_request_duration`, `llm_tokens_per_request`, `embedding_cost_usd`, `memory_*_latency_ms` | Histogram | `1` | unchanged — **no `_seconds` appended**, so the dashboard's `llm_request_duration_bucket` is correct |
| `document_hub_*_total`, `document_hub_processing_duration_seconds` | Counter / Histogram | `1` | unchanged |

**Verdict: G17c is REFUTED.** Dashboard PromQL spellings match what the collector exposes. The reason
is slightly accidental — it holds *because* nobody ever passed a real unit. The moment someone
registers a metric properly (unit `s`, `By`, `USD`) the names shift under the dashboards.

**Two real normalization traps the audit did not name** (they bite the moment the dead code is wired up):
- `RuntimeTelemetry`'s dotted names become `agent_turn_calls_total`, `agent_model_input_tokens_total`,
  `agent_tool_calls_total`, … (dots → underscores, `_total` appended to every counter).
- `RuntimeTelemetry`'s `agent.model.cost_usd` is declared `unit="USD"`
  (`agent_shared/telemetry.py:37`). `USD` is not in the unit map, so it is appended verbatim and
  case-sensitively: the series becomes **`agent_model_cost_usd_USD_total`**. `agent.turn.duration_seconds`
  with `unit="s"` (`:24-27`) is safe — `seconds` is already a token — as is `agent.model.latency_seconds`.

**A third, separately checkable consequence of the same defaults (NEW — see G21):** with
`resource_to_telemetry_conversion` disabled, resource attributes are *not* promoted to labels. The
exporter emits only `job` (from `service.name`) and `instance` (from `service.instance.id`, which this
estate never sets). So **`service_name` is not a label on any Prometheus series**, and Prometheus
scrapes with `honor_labels` unset, meaning the exporter's own `job="copilots"` is renamed
`exported_job` and replaced by `job="otel-collector"` (`prometheus.yml:16-18`). Any future PromQL that
tries to split by service will silently return nothing. Today no PromQL panel filters on
`service_name` (only the LogQL panels do), so nothing is broken *yet*.

---

## 1.4 New gaps the audit missed — G18+

### G18 — Raw user prompts and answers ARE shipped off-box, in production, on the log path (CRITICAL)
G16 states prompt capture is "filesystem-only and dev-gated". That is true of `debug_dumps`, but the
**log** pipeline carries user content unconditionally, at INFO, to Loki:
- `copilot-mro/copilot_mro/app/api/chat_management.py:987-991` —
  `logger.info("Enhanced chat request received", chat_id=…, query=request.message, department=…)`.
  `query=request.message` is the user's full chat message. Same statement again on the streaming route,
  `:1303-1308`.
- `copilot-mro/copilot_mro/app/services/memory/memory_index.py:469-476` and `:559-566` —
  `logger.info("Memory search requested" / "Memory search completed", …, query=query, …)`.
Every one of these lands as an OTLP log attribute (`logging_config.py:214-224` copies every `extra`
key onto the record) with 3-day-plus Loki retention and Grafana `admin/admin` in front of it. This is
the single largest correction to the audit: there **is** an LLM-content store in production; it is
Loki, and nobody designed it as one.

### G19 — `set_gauge` is not a gauge; `active_sessions` / `active_users` are monotonic garbage
`utils/utils/observability/metrics.py:402-428`: `set_gauge` auto-registers an **UpDownCounter** and
then calls `.add(value, attributes)` — `:426` `self.metrics[name].add(value, attributes)`, with the
in-code admission at `:423-425` *"For gauge-like behavior, we'll use the current value … This is a
simplified approach."* The middleware calls it with a literal `1` on **every request**
(`api/flynapse_api/middleware/observability.py:129-136`), and nothing ever subtracts. So
`active_sessions{session_id=…}` and `active_users{user_id=…}` are per-request counters, never
concurrency gauges. `backend-metrics-dashboard.json` does not query them, so the wrongness is
currently invisible — which is worse, not better.

### G20 — Unbounded metric label cardinality: `session_id`, `user_id`, `path`, `item_count`
- `observability.py:108-113` and `:119-124` attach `user_id`, `session_id` **and the raw
  `request.url.path`** to both `http_requests_total` and `http_request_duration_seconds`. The path is
  un-templated, so every `/chats/{chat_id}`-shaped URL mints a new series. Combined with `session_id`
  (a fresh UUID per request when the client sends no `X-Session-ID` —
  `middleware/request_id.py:46-48`) this is per-request cardinality on a **histogram**.
- `copilot-mro/copilot_mro/app/services/memory/memory_db.py:836-841` labels `memory_get_latency_ms`
  with `item_count=len(memory_ids)` — a numeric value as a label.
This is the reason a self-hosted Prometheus on the shared `t2.large` will fall over first, and it is
also the thing that makes any managed backend (CloudWatch/New Relic) expensive on day one.

### G21 — `service_name` does not exist as a Prometheus label (see §1.3)
Consequence of the default `resource_to_telemetry_conversion: false`. Metrics from the gateway, a
standalone copilot-mro and the automations worker are **indistinguishable** in Prometheus today. The
log pipeline *does* carry `service_name` (Loki's OTLP path promotes `service.name`), which is why the
audit only saw the fragmentation on the log side.

### G22 — stdlib `logging` is never bridged into loguru, so whole subsystems never reach Loki
No `InterceptHandler`, no `logging.basicConfig` in any service entrypoint (workspace-wide search;
`basicConfig` appears only in `copilot-mro/scripts/**`). Every module that uses
`logging.getLogger(__name__)` writes to the root stdlib logger, which has no handler wired to the OTLP
sink. That silently excludes: the entire **data-discovery / SAD** subsystem
(`copilot-mro/.../data_discovery/service.py:87`, `agent/sad_runner.py:27`, `agent/provider.py:63`,
`agent/analysis_provider.py:72`, `agent/context_provider.py:58`, `agent/template_provider.py:58`), the
entire **improvement loop** (`services/improvement/{runner,distiller,clustering,collect_explicit,
collect_implicit,detect_telemetry,scheduler}.py`), the **workout** tools
(`agent_shared/tools/workout/{resolve_workout,workout_gate}.py:24,39`), `agent_shared/loop_controls.py:415`,
`agent_claude/pretool_hooks.py:158`, and both `telegram-bot` modules
(`telegram_bot/{digest,screening}.py:84,54`). It also excludes **uvicorn access logs, botocore, httpx
and asyncpg** warnings entirely.

### G23 — `setup_loguru` silently no-ops if any handler already exists
`utils/utils/logging_config.py:69-75`: `if not has_loguru_handlers(): logger.remove() else: … return
logger`, and `has_loguru_handlers()` (`:35-42`) is `len(logger._core.handlers) > 1`. So if **any**
import adds a second loguru handler before `setup_logging` runs, the whole configuration — stdout
format, file sinks **and the OTLP sink** — is skipped, and the only signal is one warning line
(`:72-74`). G12's note that the gateway works "because `main.py:7` runs before importing
`copilot_mro`" is really an instance of this: the pipeline's existence depends on import order.

### G24 — Log timestamps on the OTLP path are fabricated and the bump is not thread-safe
`utils/utils/logging_config.py:14-24` keeps a module-global `_last_ts_ns` and forces each record's
timestamp to be at least 1000 ns after the previous one; `:186-206` then **overwrites**
`log_record.created` with `time.time()` at *sink* time (not event time) plus that bump. Two
consequences: (a) the timestamp in Loki is the sink's clock, not the log call's, and under load the
forced monotonic skew accumulates; (b) `_last_ts_ns` is mutated without a lock from every thread
(`asyncio.to_thread` pipeline workers, the executor, the automations loop), so it is a plain data race.

### G25 — Blocking file sinks on the request path
`utils/utils/logging_config.py:101-116` unconditionally adds two **synchronous, non-`enqueue`d** file
sinks (`logs/error.log` 10 MB×30 d, `logs/app.log` 50 MB×7 d) and `:97-98` `log_path.mkdir` creates the
directory. In App Runner / Lambda these write to ephemeral container disk that nothing reads, and every
`logger.info` on the async event loop performs a blocking write plus a rotation size check. There is no
setting to turn them off — `log_dir` (`utils/utils/config.py:111`) only moves them.

### G26 — The LangGraph runtime emits no spans and no metrics at all
`copilot-mro/copilot_mro/app/services/lang_agent/` contains **zero** calls to `get_tracing_service`,
`get_metrics_service` or `RuntimeTelemetry` (workspace-wide search for span/metric entry points
returns hits only in `api/`, `chat_management.py`, `orchestrator.py`, `memory_*`, `document_hub`).
G9 says `runtime_factory.py` "never constructs" `RuntimeTelemetry`; the stronger fact is that the
whole second runtime is telemetry-dark — a turn served by the `lang` runtime produces no
`agent_sdk.run_query`-equivalent span, no tool spans, and no cost attributes anywhere in the trace.

### G27 — The metrics/tracing services are process-global singletons keyed on nothing
`metrics.py:485-508` and `tracing.py:227-240` cache a single instance in a module global; the
`name/env/version` arguments of **every call after the first are discarded**. Two live consequences:
(a) `document_hub/operations.py:69-75` calls `get_metrics_service()` with **no arguments**, so if a
doc-hub emission happens to be first, the whole process's meter is named `copilots`/`dev`/`1.0.0`
(`metrics.py:488-489` defaults); (b) `metrics.set_meter_provider` / `trace.set_tracer_provider`
(`metrics.py:170`, `tracing.py:108`) are global one-shot setters — a second provider would be refused
with a warning, so the first caller permanently owns the resource attributes for the process.

### G28 — Health checks: one real aggregate probe, three liveness stubs, no readiness anywhere
- **Real**: `copilot-mro/copilot_mro/app/api/health_check.py:42` (`@router.get("/")`, router prefix
  `/health`, mounted at `copilot-mro/copilot_mro/app/main.py:199`) probes Postgres, Redis/ElastiCache,
  S3, Weaviate and Azure OpenAI and returns a per-dependency verdict. It is **anonymous by design**
  (the docstring says so) and it does **not** probe the OTLP endpoint, Bedrock, or the Claude Agent SDK.
- **Stubs**: `api/flynapse_api/main.py:362-364` → `{"status": "healthy", "service": "flynapse-api"}`;
  `core/core/fastapi_app.py:233-241`; `shift-optimizer/shift_optimizer/app/api/health.py:13-16`.
- **Odd**: `copilot-mro/copilot_mro/app/main.py:228-236` defines a *second*, stub `{prefix}/health`
  that differs from the real aggregate route only by a trailing slash, and it leaks
  `"debug": settings.debug` to an unauthenticated caller.
- No `/ready`, `/readyz`, `/livez` or `/healthz` route exists in any repo, so App Runner cannot
  distinguish "process is up" from "process can serve".

### G29 — `LOKI_BASE_URL` is never set in `iac/`, so the customer-facing settings dashboard is dead in AWS (CRITICAL)
`core/core/config.py:73` defaults `loki_base_url` to `http://localhost:3100`. The only place that
variable appears anywhere outside that default is `core/core/.env.example:17` (which also says
`localhost:3100`). `iac/apprunner.tf:39-72` enumerates **every** runtime environment variable the API
service gets — `LOKI_BASE_URL` is not among them, and there is no `runtime_environment_secrets` block
on the resource. So in the deployed AWS environment `chat_quality_service._query_loki`
(`:835-856`) issues its request to `http://localhost:3100` **inside the App Runner container**, where
nothing is listening. The audit records two dead panels (#6 Query Type, #7 Most Accessed Documents);
the real state is that **all ten panels fail in AWS**, every one collapsing to
`'Failed to load chat quality data.'` (`page.tsx:419`). This subsumes and outranks G10 and G11 —
whatever a redesign does about tenant filtering, the feature does not currently work in production at
all. (Verifiable without a deploy: grep `iac/` for `LOKI`.)

### G30 — `METRICS_SCRAPE_TOKEN` is unset in production, on a publicly accessible service
`api/flynapse_api/auth/metrics_scrape.py:31-34` documents the gate as *"A no-op while
`METRICS_SCRAPE_TOKEN` is unset, which is the dev default"*. The variable appears in exactly one place
in the estate — `api/.env.example:81 METRICS_SCRAPE_TOKEN=` (empty) — and is **not** set in
`iac/apprunner.tf`, on a service whose `network_configuration.ingress_configuration` is
`is_publicly_accessible = true` (`apprunner.tf:88-90`). So the dev default is the production
configuration. The exposure today is small (the endpoint serves only default `python_gc_*`/`process_*`
collectors — G3) but it becomes a real leak the moment G3 is fixed and the tenant-labelled series
appear behind it.

### G31 — The observability box publishes Loki, Prometheus and the OTLP receivers unauthenticated on a public subnet
`iac/ec2.tf:5` puts `aws_instance.weaviate_observability` in `aws_subnet.public[0]`. The demo compose
that the user-data script starts (`iac/demo_ec2_setup.sh:93` over
`copilot-mro/deployment/demo/docker-compose.yml`) publishes Loki `3100:3100` (`:48`), Prometheus
`9090:9090` (`:35`), Tempo `3200:3200` (`:87`) and the collector's OTLP/zpages/pprof ports on **all
interfaces** — only Grafana is loopback-bound (`:61`). Loki's HTTP API has no authentication and no
`X-Scope-OrgID` enforcement — `loki-config.yaml:4` `auth_enabled: false` — so anyone the security group admits
(`ec2.tf:96-115`: `var.allowed_ssh_ip` **and** the App Runner + Lambda SGs) can read every tenant's
logs — which, per G18, include user prompt text. Grafana's `admin/admin` is the second key to the same
door via SSH port-forward. `auth_enabled: false` also means Loki has **no tenant separation of its
own** (everything lands in the single `fake` tenant), which is the structural reason G10's filtering
has to happen in Python.

Compounding it: `loki-config.yaml` declares no `compactor` block and no `limits_config.retention_period`,
so Loki's retention is **unlimited** — bounded only by the 30 GB root volume (`ec2.tf:11-13`) it shares
with Weaviate, Prometheus and Tempo. Combined with G18 that means user prompt text accumulates
indefinitely on an unauthenticated store until the disk fills, at which point Weaviate loses its
volume too.

### G32 — Nine parser/ingest entrypoints each mint their own `service_name`
`services/parsers/*.py` `__main__` blocks call `setup_logging(name="crew-manual-parser" | "amos-parser" |
"ifim-parser" | "mel-parser" | "tn-parser" | "ftd-parser" | "amos-post-processing" |
"amos-metadata-backfill" | "pdf-service", env="development")`
(`crew_manual_parser.py:1485`, `amos_parser.py:4585`, `ifim_parser.py:2569`, `mel_parser.py:1492`,
`tn_parser.py:1932`, `ftd_parser.py:1962`, `amos_post_processing.py:2828`,
`amos_metadata_backfill.py:251`, `s3_pdf_processor.py:692`). Each is a distinct `service_name` stream
label in Loki and a distinct `job` in Prometheus, all hardcoded `env="development"`, and none appears
in any dashboard or in the analytics service's `{service_name="copilots"}` selector. G12 names three
service identities; the real count is **at least thirteen**.

### G33 — Correction to the audit's topology table: `telegram-bot`'s "hand-rolled in-process counters" do not exist
The audit's §1 row reads *"stdlib logging + hand-rolled in-process counters — never exported"*. The
counters in `telegram-bot` are **durable product quota counters in Postgres**, written with
single-statement conditional `UPDATE … RETURNING` / `INSERT … ON CONFLICT` (`telegram_bot/state.py:17-38,
447-455, 489, 524`), not telemetry. The correct statement is: telegram-bot has **no telemetry at all** —
`logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)` (`telegram_bot/app.py:461`) to stdout, no
loguru, no `setup_logging`, no OTel dependency in `telegram-bot/pyproject.toml`.

### G34 — `shift-optimizer` and `core` never configure logging; they inherit the gateway's
Neither repo calls `setup_logging` / `setup_loguru` anywhere (the only call sites in the estate are
`api/flynapse_api/main.py:7`, `api/.../automations/worker.py:469`,
`copilot-mro/copilot_mro/app/main.py:13`, `copilot-mro/copilot_mro/app/core/__init__.py:10`, and the
nine parser `__main__` blocks). Both use `loguru` (`shift-optimizer/.../db/postgres.py:17`,
`.../services/run_executor.py:74`; `core` throughout), so mounted inside the gateway their logs ship
correctly — and run standalone they fall back to loguru's default stderr handler with **no OTLP sink
and no file sinks**. The audit's "loguru only; zero OTel" is right about the code and wrong about the
runtime: in the deployed topology these two *are* on the OTLP path, under the gateway's service name.

---

# PART 2 — Backend telemetry inventory (ground truth)

## 2.1 Metrics

### 2.1.0 The mechanism, in one paragraph
There is exactly one metrics implementation: `utils/utils/observability/metrics.py`, exposed as
`get_metrics_service(name, env, version)` (`:488`). It builds an OTel SDK `MeterProvider` with a
`PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=settings.otel_endpoint), 5000 ms)`
(`:156-170`), i.e. **OTLP/gRPC push every 5 s**, never a Prometheus pull. `register_metrics` /
`register_counter` / `register_histogram` / `register_up_down_counter` exist (`:179-337`) but **have
zero call sites in the whole workspace** — every metric in the estate is *lazily auto-registered on
first emit* with the default unit `"1"` and a generated description (`:360-366, :385-391, :409-416`).
So the audit's "registered vs emitted" distinction collapses: nothing is registered ahead of time; the
only meaningful categories are **emitted** and **named-but-never-emitted**.

Attributes: `_get_attributes` (`:339-350`) puts `tenant_id` first and then every keyword argument,
**dropping `None` values only** (so `"unknown"` strings survive and become label values).

### 2.1.1 Emitted metrics — complete list

| Metric | Instrument | Unit | Labels / attributes | Emit site(s) |
|---|---|---|---|---|
| `http_requests_total` | Counter | 1 | `tenant_id, user_id, session_id, method, path, status_code, status` | `api/flynapse_api/middleware/observability.py:117-126` (status=success), `:162-171` (status=error, status_code hardcoded `"500"`) |
| `http_request_duration_seconds` | Histogram | 1 (**not `s`**) | `tenant_id, user_id, session_id, method, path, status_code` | `observability.py:105-114`, `:150-159` |
| `active_sessions` | UpDownCounter (see G19) | 1 | `tenant_id, session_id` | `observability.py:129-131` |
| `active_users` | UpDownCounter (see G19) | 1 | `tenant_id, user_id` | `observability.py:134-136` |
| `llm_requests_total` | Counter | 1 | `tenant_id, model, department, status` | `utils/utils/llm.py:393-399` (success), `:444-450` (error), `:799-806` (streaming/`accumulate_bedrock_cost`) |
| `llm_request_duration` | Histogram | 1 | `tenant_id, model, department` | `utils/utils/llm.py:400-406`, `:451-457` |
| `llm_tokens_total` | Counter | 1 | `tenant_id, model, department, token_type` ∈ {input, output, total} | `utils/utils/llm.py:350-357` (`_record_token_metrics`, reached from `recorded_llm_call` `:409` and `accumulate_bedrock_cost` `:818`) |
| `llm_tokens_per_request` | Histogram | 1 | same as above | `utils/utils/llm.py:358-365` |
| `embedding_requests_total` | Counter | 1 | `tenant_id, model, status` (always `"success"`) | `utils/utils/llm.py:1179-1181` |
| `embedding_tokens_total` | Counter | 1 | `tenant_id, model` | `utils/utils/llm.py:1183-1185` |
| `embedding_cost_usd` | **Histogram** (the only USD metric in the estate) | 1 | `tenant_id, model` | `utils/utils/llm.py:1189-1191` |
| `embedding_request_duration` | Histogram | 1 | `tenant_id, model` | `utils/utils/llm.py:1193-1198` |
| `embedding_cache_hits_total` | Counter | 1 | `tenant_id, model` | `utils/utils/llm.py:1299-1301` |
| `embedding_cache_tokens_avoided_total` | Counter | 1 | `tenant_id, model` | `utils/utils/llm.py:1304-1308` |
| `chat_block_save_failures_total` | Counter | 1 | `tenant_id, department, error_kind, field` | `copilot-mro/copilot_mro/app/api/chat_management.py:363-368` |
| `memory_search_latency_ms` | Histogram | 1 | `tenant_id, search_type` | `copilot-mro/.../services/memory/memory_index.py:555-560` |
| `memory_get_latency_ms` | Histogram | 1 | `tenant_id, item_count` (**numeric label — G20**) | `copilot-mro/.../services/memory/memory_db.py:836-841` |
| `document_hub_upload_total` | Counter | 1 | `tenant_id, document_type, file_kind, sharing_scope, status, source_scope` | `document_hub/service.py:1053-1061` |
| `document_hub_retry_total` | Counter | 1 | `tenant_id, document_type, file_kind, status` | `document_hub/service.py:912-918` |
| `document_hub_delete_total` | Counter | 1 | `tenant_id, document_type, file_kind, source_scope` | `document_hub/service.py:856-862` |
| `document_hub_share_total` | Counter | 1 | `tenant_id, sharing_scope` | `document_hub/service.py:818-822` |
| `document_hub_processing_total` | Counter | 1 | `tenant_id, status, failure_code, file_kind, document_type, parser_route` | `document_hub/processing.py:549-553` |
| `document_hub_processing_duration_seconds` | Histogram | 1 | same labels as above | `document_hub/processing.py:554-560` |
| `document_hub_parser_failure_total` | Counter | 1 | `tenant_id, document_type, file_kind, failure_code, parser_route` | `document_hub/processing.py:425-432` |
| `document_hub_index_upsert_total` | Counter (value = `indexed_count`) | 1 | `tenant_id, document_type, file_kind, parser_route` | `document_hub/processing.py:259-266` |
| `document_hub_attempt_vector_cleanup_total` | Counter | 1 | `tenant_id, status, file_kind` | `document_hub/processing.py:521-526`, `:528-533` |
| `document_hub_cleanup_total` | Counter | 1 | `tenant_id, status, source_scope` | `document_hub/cleanup.py:406-411`, `:439-444` |
| `document_hub_cleanup_vectors` | Counter (value = vectors deleted) | 1 | `tenant_id, source_scope` | `document_hub/cleanup.py:412-417` |
| `document_hub_cleanup_objects` | Counter (value = objects deleted) | 1 | `tenant_id, source_scope` | `document_hub/cleanup.py:418-423` |
| `document_hub_notification_total` | Counter | 1 | `tenant_id, notification_type, outcome` | `document_hub/notifications.py:109-114`, `:124-129` |
| `document_hub_query_embedding_fallback_total` | Counter | 1 | `tenant_id` | `document_hub/indexing.py:755-758` |

**Total: 30 emitted metrics.** All are pushed OTLP/gRPC to `settings.otel_endpoint`
(`utils.config`, default `http://localhost:4317`).

### 2.1.2 Named but never emitted

| Name | Declared at | Status |
|---|---|---|
| `document_hub_qna_total` | `document_hub/operations.py:28` | zero call sites |
| `document_hub_qna_latency_seconds` | `:29` | zero call sites |
| `document_hub_qna_selected_documents` | `:30` | zero call sites |
| `document_hub_qna_retrieval_hits` | `:31` | zero call sites |
| `document_hub_qna_no_evidence_total` | `:32` | zero call sites |
| `document_hub_qna_citations` | `:33` | zero call sites |
| `agent.turn.calls`, `agent.turn.duration_seconds`, `agent.model.calls`, `agent.model.{input,output,reasoning,cache_read,cache_write,tool_search_overhead}_tokens`, `agent.model.cost_usd`, `agent.model.latency_seconds`, `agent.tool.calls`, `agent.tool.attempts`, `agent.subagent.calls`, `agent.subagent.duration_seconds` | `agent_shared/telemetry.py:23-48` | class never constructed outside tests (G9) |
| `rag_requests_total`, `rag_request_duration_seconds`, `rag_active_sessions`, `rag_pipeline_steps_total`, `rag_token_usage` | `deployment/observability-local/test-observability.py:100-122` | synthetic load generator only; nothing queries them |

### 2.1.3 Queried but never emitted (dashboard-side dead ends)
`pipeline_steps_total`, `pipeline_step_duration_seconds`, `rag_retrieval_score`,
`agent_validation_failures_total` — zero emitters anywhere. Plus the LogQL string filters
`Completed pipeline step`, `LlamaIndexService returned chunks`, `Tool Routing Decision`, and
`page_view` (frontend-only, and the frontend does not ship — G1).

---

## 2.2 Traces

### 2.2.1 Every span created in the estate

| Span name | Kind | Parent | Attributes set | Created at |
|---|---|---|---|---|
| `{METHOD} {path}` | SERVER | W3C-extracted from inbound headers (`tracing.py:174`), else root | `http.method, http.url, http.target, request_id, tenant_id, user_id, session_id` | `api/flynapse_api/middleware/observability.py:64-76` |
| `chat.enhanced_chat` | INTERNAL | ambient (server span) | `tenant_id, user_id, department, chat_id` | `copilot-mro/.../api/chat_management.py:1106-1114` |
| `chat.enhanced_chat_stream` | INTERNAL | ambient — inherited through `asyncio.create_task` (`chat_management.py:1673`), so it **does** parent to the server span | same four | `chat_management.py:1425-1433` |
| `rag.pipeline.execute` | INTERNAL | the `chat.*` span | `has_existing_chat` | `chat_management.py:1115-1118` and `:1434-1437` |
| `db.chat.save_block` | INTERNAL | ambient | `chat_id, block_id` | `chat_management.py:1230-1233` (sync path); `:1617-1620` (streaming background save, inside `asyncio.create_task`, `:1650`) |
| `agent_sdk.run_query` | INTERNAL | ambient (`rag.pipeline.execute`) | `sdk.has_history, sdk.has_memory, sdk.model, sdk.department, sdk.max_turns, sdk.max_budget_usd, tenant_id, user_id, chat_id` at open (`loop_observability.py:45-71`); then at close `sdk.{num_turns,input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens,synthesis_input_tokens,synthesis_output_tokens,direct_metered_input_tokens,direct_metered_output_tokens,direct_metered_cached_tokens,direct_unpriced_calls,embedding_tokens,embedding_calls,embedding_cache_hits,embedding_cache_tokens_avoided,embedding_cache_hits_unmeasured}`, `sdk.cache_hit_rate`, `sdk.{total,direct,embedding,combined}_cost_usd`, `sdk.direct_metered_duration_s`, `sdk.subtype`, `sdk.is_error`, `sdk.loop_error` (`loop_observability.py:74-136`), plus `sdk.answer_found`, `sdk.judge_passed`, `sdk.confidence_probability`, `sdk.numeric_fidelity`, `sdk.figures_were_fed` (`orchestrator.py:3209-3218`) | `orchestrator.py:2607-2617` |
| span **event** `sdk.synthesis_judged` | — | on `agent_sdk.run_query` | `scope_index, scope_id, superseded, passed, relevance, confidence_probability, answer_found` — one per synthesis scope | `orchestrator.py:3224-3242` |
| `agent_sdk.tool.<short_name>` | INTERNAL, **backdated** | ambient at emit time (still inside the root `with`) | `tool.name, tool.is_error, tool.duration_ms` + `tenant_id, user_id, chat_id` | `agent_shared/loop_observability.py:233-238`, called from `orchestrator.py:3243` |
| `agent.turn` | INTERNAL | — | `agent.runtime, agent.department` | `agent_shared/telemetry.py:56-62` — **never reached** (G9) |

That is the **complete** span inventory. There are no spans for: retrieval, Weaviate queries,
Postgres queries, Bedrock calls, S3, Redis, the automations worker, lambdas, telegram-bot,
shift-optimizer, core, document-hub, data-discovery/SAD, or the improvement loop.

### 2.2.2 Root span creation and context propagation

- **Root span**: only `api/flynapse_api/middleware/observability.py:64-76`, via
  `TracingService.as_current_server_span` → `tracer.start_as_current_span(name, context=extract(headers), kind=SERVER)`
  (`utils/utils/observability/tracing.py:174-180`). The span name is
  `f"{request.method} {request.url.path}"` — **the raw path, un-templated**, so span names are
  per-resource-id (a Tempo/Jaeger service-graph and span-metrics cardinality problem identical to G20).
- The trace id is echoed to the client as `X-Trace-Id` (`observability.py:88-91`).
- **Inbound extraction only.** No `propagate.inject` anywhere (G5), so no outbound HTTP, no queue
  message and no cross-process hop carries `traceparent`.
- **asyncio tasks — propagation HOLDS.** `asyncio.create_task` copies the current `contextvars`
  context, so `run_pipeline` (`chat_management.py:1673`) and `_save_chat_block_in_background`
  (`:1650`) inherit the server span.
- **Thread pools — propagation HOLDS, by luck of using `asyncio.to_thread`.** `chat_management.py:1488`
  `pipeline_result = await asyncio.to_thread(_run_pipeline_sync)`, and `_run_pipeline_sync`
  (`:1442-1448`) calls `asyncio.run(pipeline.execute(...))` — a *new event loop inside the worker
  thread*. `asyncio.to_thread` runs the callable through `contextvars.copy_context().run(...)`, and
  `asyncio.run`'s Task copies the thread's current context, so the OTel span survives both hops. A
  future refactor to `loop.run_in_executor(pool, fn)` or a bare `threading.Thread` would silently
  detach every pipeline span from its request.
- **Automations worker — no propagation, because there is no span to propagate.** The worker
  (`api/flynapse_api/automations/worker.py`) and the executor
  (`api/flynapse_api/automations/executor.py`) create **no spans at all** (no `get_tracing_service`
  import in either file) and never call `logger.contextualize`. A scheduled turn therefore produces an
  `agent_sdk.run_query` span with **no parent**, and its logs carry no `tenant_id`/`user_id`/`request_id`
  binding — only whatever each individual `logger.info` passes explicitly.
- **Sampling**: no sampler is configured (`tracing.py:107` `TracerProvider(resource=resource)`), so the
  SDK default applies — `parentbased_always_on` unless `OTEL_TRACES_SAMPLER` is set in the environment.
  Nothing in the repo sets it. 100 % of spans are exported.
- **Tempo retains blocks for 1 h** (`tempo.yaml:19`).

---

## 2.3 Logs

### 2.3.1 Configuration
`utils/utils/logging_config.py` is the only logging configuration in the estate.
`setup_logging(name, env)` (`:241-260`) reads **`utils.config.Settings`** (`:243`) — `log_level`,
`log_dir`, `log_colors`, `otel_enabled`, `otel_endpoint`, `app_version` — and passes the caller's
`name` as `otel_service_name`. It then calls `setup_loguru` (`:45`), which installs:

| Sink | Format | Level | Rotation / retention | Line |
|---|---|---|---|---|
| `sys.stdout` | `"{time:YYYY-MM-DD HH:mm:ss} \| {level: <8} \| {name}:{function}:{line} - {message} \| {extra}"` (colourised variant above it) | `log_level` | — | `:82-94` |
| `logs/error.log` | same, uncoloured | ERROR | 10 MB / 30 days | `:101-107` |
| `logs/app.log` | same | `log_level` | 50 MB / 7 days | `:110-116` |
| `otel_sink` (OTLP/gRPC log exporter) | `"{message}"` | `log_level` | — | `:179-233`, **only when `otel_enabled`** (`:119`) |

`setup_loguru` returns early without configuring anything if loguru already has >1 handler
(`:69-75`, `has_loguru_handlers` `:27-42`) — see G23.

### 2.3.2 OTLP record shape
`otel_sink` (`:179-230`) builds a stdlib `logging.LogRecord` and hands it to
`opentelemetry.sdk._logs.LoggingHandler`. Field mapping:

| OTLP field | Source |
|---|---|
| body | `message.record["message"]` (`:196`) — the rendered message, **without** `{extra}` |
| severity | `message.record["level"].no` (`:194`) |
| timestamp | **fabricated**: `time.time()` at sink time, forced ≥ previous +1000 ns (`:186-206`) — see G24 |
| `code.filepath` / `code.lineno` / `code.function` | `pathname`, `lineno` (`:195,197`), `funcName` (`:213`) |
| `logger name` | `message.record["name"]` (`:192`) |
| `otelTraceID` / `otelSpanID` | set as record attributes when a span is current (`:209-211`) |
| **every `extra` key** | `setattr(log_record, key, str(value))` (`:214-224`) — **all values stringified**, so numeric log fields arrive at Loki as strings |
| exception | `message.record["exception"]` → `exc_info` (`:198`) |

The collector's log pipeline sends these to `http://loki:3100/otlp`
(`otel-collector-config.yaml:58-59, :97-100`); Loki's OTLP endpoint promotes the resource attribute
`service.name` to the stream label **`service_name`**, which is what every LogQL query in the estate
selects on.

### 2.3.3 Bound context (`logger.contextualize`)

| Where | Fields bound |
|---|---|
| `api/flynapse_api/middleware/logging.py:59-68` | `request_id, tenant_id, user_id, session_id, method, path, user_agent, client_ip` — the only *middleware*-level binding; covers every HTTP request through the gateway |
| `copilot-mro/.../api/chat_management.py:1101-1103` and `:1420-1422` | adds `chat_id, department, block_id` for the duration of the pipeline call |

Nowhere else. Notably **not** bound: the automations executor/worker, the improvement loop, the
document-hub processing path, the data-discovery/SAD runner, lambdas, telegram-bot.

### 2.3.4 The log lines the product analytics service depends on

`core/core/resources/analytics/services/chat_quality_service.py:59-96` defines nine LogQL constants.
Their emitters:

| LogQL constant (line) | Grepped message | Emitting statement | `extra` fields the query reads |
|---|---|---|---|
| `LOGQL_TOP_USERS` (`:59`) / `LOGQL_ACTIVE_USERS` (`:89`) | `^Enhanced chat request received$` | `copilot-mro/.../api/chat_management.py:987-991` `logger.info("Enhanced chat request received", chat_id=…, query=request.message, department=request.department)` and the identical statement at `:1303-1308` | `user_id`, `tenant_id` (from the middleware `contextualize`), `department` (explicit) |
| `LOGQL_FEEDBACK_RECEIVED` (`:63`) | `^Response feedback saved successfully$` | `copilot-mro/copilot_mro/app/api/user_feedback.py:264` | `feedback_type`, `department`, `tenant_id` |
| `LOGQL_ROUTER_INTENT` (`:67`) | `^Tool Routing Decision$` | **no emitter anywhere** — dead panel (G7) | `intent`, `tenant_id` |
| `LOGQL_MOST_ACCESSED_PAGES` (`:71`) | `page_view` inside a JSON `data` blob | frontend only (`dashboard/lib/logging/page-tracking.ts`), and frontend delivery is disabled — dead panel (G1) | `pageId`, `user_id`, `tenant_id` |
| `LOGQL_CHAT_TIME_DURATION_HISTOGRAM` (`:78`) | `Chat response generated successfully` | `chat_management.py:1244-1248` and `:1651-1655` — `logger.info("Chat response generated successfully", block_id=block_id, execution_time=pipeline_result.execution_time)` | `execution_time`, plus the middleware's `path` |
| `LOGQL_COMMENTS_CREATED` (`:84`) | `^Successfully created comment$` | `core/core/resources/comments/comments_endpoints.py:312` | `user_id`, `department`, `tenant_id` |
| `LOGQL_LLM_TOKENS` (`:93`) | `LLM request completed` | `utils/utils/llm.py:412-431` — `logger.info("LLM request completed", chat_id=…, tenant_id=…, model=…, duration=…, department=…, prompt_tokens=…, completion_tokens=…, total_tokens=…, cached_tokens=…, reasoning_tokens=…, reasoning_effort=…)` | `total_tokens`, `prompt_tokens`, `completion_tokens`, `request_id`, `tenant_id`, `model` |

**Important consequence of the last row**: the product settings dashboard's "LLM Token Consumption"
panel is fed by `recorded_llm_call` only. The **Claude Agent SDK loop's own tokens never appear**
(the SDK reports usage on its `ResultMessage`, which is booked to `llm_usage`, not logged with that
message). The panel therefore reports direct-Bedrock/Azure tokens only — the minority of the spend.
`"Chat created successfully"` (`copilot-mro/copilot_mro/app/db/chat_history/chats.py:159`) and
`"Successfully toggled thumbs up for comment"` (`core/.../comments_endpoints.py:442`) are used by the
Grafana `chat-quality-dashboard.json` but were never ported to the product page.

### 2.3.5 Other structured log families worth knowing about
- `"Document Hub audit event"` — `document_hub/operations.py:123-132`, with
  `event_type="document_hub_audit", action, tenant_id, user_id, document_hub_document_id, outcome` +
  arbitrary extras. This is a genuine audit stream that nothing consumes.
- `"LLM streaming request metered"` (`utils/utils/llm.py:833-840`) and `"Embedding request metered"`
  (`:1205-1212`) — the only written record of spend on paths that produce no ledger row.
- `llm_usage: turn booked / FAILED / REFUSED` (`agent_shared/usage_ledger.py:311,322,330,336`) and
  `llm_model_calls: attempt booked / FAILED / REFUSED` (`agent_shared/model_call_ledger.py:167,175,183`)
  — the ledger's own reliability signal, log-only.
- `"%s_usage status=%s in=%s out=%s cache_read=%s cost_usd=%s"` — the SAD runner's cost line
  (`data_discovery/agent/sad_runner.py:412-420`), emitted through **stdlib `logging`**, therefore never
  reaching Loki (G22).

---

## 2.4 LLM call paths — what is captured, and where it lands

Legend for the sinks: **U** = `llm_usage` row (per turn), **MC** = `llm_model_calls` row (per model
attempt), **M** = OTel metrics, **S** = span attributes, **L** = log line, **D** = `debug_dumps` file.

| Path | Entry point | Provider / SDK | U | MC | M | S | L | D | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **Claude Agent SDK loop** (main + subagents) | `copilot-mro/.../agent_claude/orchestrator.py:2607` (`run_query`) | `claude-agent-sdk 0.2.128` → Bedrock | ✅ `record_turn_usage` at `orchestrator.py:3094`; failure salvage at `:2618` (`book_turn_on_failure`) | ❌ — `agent_pipeline.py:55-58`: "sees the five lifecycle calls ONLY — the SDK loop bills itself" | ❌ **no metric at all** | ✅ `agent_sdk.run_query` + `agent_sdk.tool.*` | ❌ (no per-call log) | ✅ when `DEBUG=true` | The biggest spender is invisible to Prometheus and to the product analytics panel |
| **Lifecycle / governed model calls, Claude runtime** | `agent_pipeline.py:70-96` (`build_claude_model_runtime_factory`) | LangChain clients → Bedrock/Azure/DeepSeek | folded into the turn's `direct_cost_usd` via `accumulator_fold_sink()` (`agent_pipeline.py:88`) | ✅ `durable_model_call_sink(...)` (`:89`) | via `utils/llm.py` where the call goes through `call_bedrock_messages` | ❌ | ✅ `llm_model_calls: attempt booked` | — | |
| **LangGraph runtime** (`AGENT_RUNTIME=lang`) | `agent_pipeline.py:230-385` | LangChain/LangGraph | ❌ **no `llm_usage` row** — `record_turn_usage` has exactly one caller, `orchestrator.py:3094` | ✅ `durable_model_call_sink` (`agent_pipeline.py:377-379`) | ❌ | ❌ **no spans** (`services/lang_agent/` contains zero tracing/metrics references) | ✅ ledger lines | `lang_agent/debug_dump.py` | Selected by `AGENT_RUNTIME` (`config.py:1064`, default `"claude"`); `agent_pipeline.py:453-459` validates the value |
| **Direct Bedrock messages** (grounding judge, synthesis judge, workout gate, PDF-OCR vision, text model, document classification, improvement distiller/clustering/collect_implicit) | `utils/utils/llm.py:691` `call_bedrock_messages` → `recorded_llm_call` `:724` | `anthropic[bedrock] 0.109.2` | folded into `direct_cost_usd` on the bound accumulator | ✅ when routed through the governed factory | ✅ `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request` | ❌ | ✅ `"LLM request completed"` / `"LLM request failed"` (`:412`, `:456`) | ✅ | Cost via `compute_bedrock_cost` (`:637`); `_note_unpriced_call` (`:269`) flags anything unpriceable |
| **Streaming direct-Bedrock synthesis** (`cited_synthesis`, `cross_source_synthesis`, `legacy_amos_synthesis`) | `utils/utils/llm.py:754` `accumulate_bedrock_cost` | `anthropic[bedrock]` streaming | folded | — | ✅ `llm_requests_total` (`:799`) + token metrics (`:818`) | ❌ | ✅ `"LLM streaming request metered"` (`:833`) | ✅ | Never traverses `recorded_llm_call` (documented at `legacy_amos_synthesis.py:348-349`) |
| **Azure OpenAI chat / stream** | `utils/utils/llm.py:1397` `call_openai_chat`, `:1461` `call_openai_chat_stream` | `openai 2.54.0` (Azure) | folded | — | ✅ (through `recorded_llm_call`) | ❌ | ✅ | ✅ | Pricing `compute_azure_openai_cost` (`:1096`) |
| **Azure audio transcription (STT)** | `utils/utils/llm.py:1585` `call_openai_audio_transcription`, used by `agent_shared/tools/media/transcribe_audio.py:50` | `openai` | folded into `direct_metered_*` | — | ✅ | ❌ | ✅ | — | |
| **Embeddings** | `utils/utils/embedding_service.py:154 generate_embedding`, `:224 generate_embeddings_batch`, `:476 health_check` → `utils/utils/llm.py:1216 accumulate_embedding_usage`, `:1262 note_embedding_cache_hits` | Azure OpenAI | `embedding_*` columns on the turn row | — | ✅ `embedding_requests_total`, `embedding_tokens_total`, `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`, `embedding_cache_tokens_avoided_total` | ❌ | ✅ `"Embedding request metered"` (`:1205`) | — | The metric fires on **every** call, bound turn or not — the only record of ingest-time embedding spend (`llm.py:1164-1168`) |
| **Image transcription (parsers)** | `copilot-mro/.../services/parsers/image_transcription.py:400` → `call_bedrock_messages` | Bedrock | only if a turn is bound (ingest is not) | — | ✅ | ❌ | ✅ | — | |
| **Data-discovery / SAD runner** | `copilot-mro/.../data_discovery/agent/sad_runner.py:303-426` | `claude-agent-sdk` (separate loop) | ❌ | ❌ | ❌ | ❌ | ⚠️ stdlib `logging` only (`sad_runner.py:27,412`) — **never reaches Loki** | — | `record_usage` (`:383-426`) captures `total_cost_usd`, in/out/cache tokens and hands them to a caller-supplied `usage_sink` (`runtime.py:311`, `provider.py:615`, `analysis_provider.py:471`, `context_provider.py:381`, `template_provider.py:256`); the `data_discovery` tables carry only `estimated_tokens` (`postgres_table_definitions_modules/data_discovery.py:669`), no cost column |
| **Automations executor** | `api/flynapse_api/automations/executor.py` | delegates to the copilot-mro pipeline in-process | ✅ (the pipeline's own row, `origin="automation"`, `session_id = f"automation:{run_id}"` `:1091-1092`) | ✅ | ✅ (whatever the pipeline emits) | ⚠️ the `agent_sdk.run_query` span is **parentless** — the executor opens no span | ✅ but with **no `contextualize` binding** | — | Also writes `automation_runs.cost_usd` — the de-dup discriminator is `llm_usage.origin` (`llm_usage.py:63-68`) |
| **Improvement loop** | `copilot-mro/.../services/improvement/{runner,distiller,clustering,collect_implicit}.py` → `call_bedrock_messages` | Bedrock | ❌ (no turn) | possibly, if governed | ✅ | ❌ | ⚠️ stdlib `logging` (`runner.py:51` etc.) — invisible to Loki | — | Cost aggregated into `improvement_runs.llm_spend` (`postgres_table_definitions_modules/improvement.py:75`, written at `db/improvement/runs.py:29,80`) |
| **telegram-bot** | `telegram-bot/telegram_bot/*` | calls the api over HTTP (`httpx`) | n/a (books on the api side) | n/a | ❌ | ❌ | ⚠️ stdlib `logging.basicConfig` (`app.py:461`) to stdout | — | No OTel dependency in `pyproject.toml`; product quota counters live in Postgres (`state.py`), they are **not** telemetry counters |
| **lambdas** (`cognito-lambdas`) | `lambdas/cognito-lambdas/app.py` | no LLM | — | — | ❌ | ❌ | loguru with a hand-rolled `print` sink (`app.py:24-25`) — never calls `setup_logging`, so no OTLP | — | Only telemetry is CloudWatch's capture of stdout |
| **llm-platform** | `llm-platform/llm_platform/` | offline model host manifests | — | — | — | — | — | — | Emits a `prometheus-scrape.yml` **artifact** for the vLLM/Ollama container (`profiles.py:224 prometheus_scrape_text`, `:381`); no application telemetry of its own |
| **shift-optimizer** | `shift-optimizer/shift_optimizer/app/**` | no LLM (solver) | — | — | ❌ | ❌ | loguru, but **never calls `setup_logging`** — mounted in the gateway it inherits the configured sinks; run standalone it has loguru's default stderr handler and ships nothing | — | |

### 2.4.1 Prompt / completion content capture
- **`debug_dumps`** — `copilot-mro/copilot_mro/app/services/_debug_dump.py:195` `dump_debug(agent, stage, content)`,
  no-op unless `settings.debug` (`:199`), writes plain text under
  `<repo>/debug_dumps/<agent>/<chat_id>/<block_id>/<agent>_<stage>_<ts>.txt` (`:207-213`), 3-day
  retention (`:25`), swept at most hourly (`:181-192`). Never shipped, never queryable.
- **`lang_agent/debug_dump.py`** — the LangGraph runtime's equivalent.
- **Loki (unintended)** — the user's message text is logged at INFO on every chat turn
  (`chat_management.py:989` `query=request.message`; also `:1306`) and every memory search
  (`memory_index.py:473`, `:563`). See G18.
- There is **no LLM trace/eval store**: no Langfuse, LangSmith, Phoenix, OpenLLMetry, Arize or
  Traceloop dependency in any `pyproject.toml`; `api/tests/unit/infra/test_no_langsmith_integration.py`
  actively asserts LangSmith's absence.

---

## 2.5 Dependency instrumentation

**No OTel instrumentor is applied anywhere.** Workspace-wide search for `Instrumentor` and
`.instrument()` returns zero hits, and no `opentelemetry-instrumentation-*` package beyond
`-fastapi` / `-logging` is even declared. Every row below therefore produces **no spans, no metrics
and no automatic error attribution**.

| Dependency | Client library actually used | Where | OTel instrumentor available upstream | Applied? |
|---|---|---|---|---|
| Postgres (shared) | **`psycopg2` (v2, sync)**, `ThreadedConnectionPool` | `utils/utils/postgres_service.py:39-42, :234` | `opentelemetry-instrumentation-psycopg2` | ❌ |
| Postgres (core) | `psycopg2` | `core/core/db/constraints.py:34`, `core/pyproject.toml:39` | same | ❌ |
| Postgres (telegram-bot) | **`psycopg` v3** + `psycopg-pool` | `telegram-bot/telegram_bot/db.py:72-73` | `opentelemetry-instrumentation-psycopg` | ❌ |
| SQLAlchemy | **not used anywhere** | — | — | n/a |
| asyncpg | **not used anywhere** — all Postgres access is synchronous, off the event loop via `asyncio.to_thread` | — | — | n/a |
| Redis | `redis` + `hiredis`, imported defensively | `utils/utils/cache_service.py:12-19` | `opentelemetry-instrumentation-redis` | ❌ |
| Weaviate | `weaviate-client` v4 (`WeaviateClient`) | `utils/utils/weaviate_service.py:12`, `copilot-mro/.../llama_index/llama_index_initialization.py:14-15` | none official | ❌ |
| S3 / SES / KMS / Bedrock control | `boto3` | `utils/utils/s3_service.py:15,130`, `utils/utils/email_service.py:49` | `opentelemetry-instrumentation-botocore` | ❌ |
| Bedrock model calls | `anthropic[bedrock]` → `AnthropicBedrock` | `agent_shared/tools/synthesis/_judge.py:37-39`, `agent_shared/tools/workout/workout_gate.py:237`, `utils/utils/llm.py` | `opentelemetry-instrumentation-botocore` (bedrock spans) — does not cover the `anthropic` SDK | ❌ |
| Claude Agent SDK | `claude-agent-sdk 0.2.128` | `agent_claude/orchestrator.py` | none | ❌ (hand-rolled spans only) |
| LangChain / LangGraph | `langchain 1.3.18`, `langgraph 1.2.11`, `langchain-{openai,aws,deepseek}` | `services/lang_agent/` | LangSmith / OpenLLMetry callbacks | ❌ (and LangSmith is asserted absent) |
| Outbound HTTP (async) | `httpx.AsyncClient` | `core/.../chat_quality_service.py:850`, `core/.../turnstile.py:54`, `copilot-mro/.../notam_service.py:39`, `.../weather_service.py:226,240` | `opentelemetry-instrumentation-httpx` | ❌ |
| Outbound HTTP (sync) | `httpx.Client`, `requests` | `copilot-mro/.../scrapers/faa_ad_fetcher.py:257,349,397`; `requests` declared in `api/pyproject.toml:18`, `core/pyproject.toml:34` | `-httpx`, `-requests` | ❌ |
| aiohttp | not used | — | — | n/a |
| FastAPI / Starlette | `opentelemetry-instrumentation-fastapi` **declared but never imported** | `api/pyproject.toml:26`, `copilot-mro/pyproject.toml:81` | — | ❌ |

### Health / readiness endpoints per service

| Service | Route | What it checks |
|---|---|---|
| `api` gateway | `GET {api_prefix}/health` (`api/flynapse_api/main.py:361-364`) | nothing — static `{"status":"healthy","service":"flynapse-api"}` |
| `api` gateway | `GET /metrics` (`main.py:372-379`) | 307 redirect to the mro `/metrics`, gated by `X-Metrics-Token` (`auth/metrics_scrape.py:28-61`), **open when `METRICS_SCRAPE_TOKEN` is unset — the dev default** (`:31-34`) |
| `copilot-mro` | `GET {prefix}/health/` (`api/health_check.py:42`, mounted `main.py:199`) | Postgres, Redis/ElastiCache, S3, Weaviate, Azure OpenAI — real dependency probes, anonymous |
| `copilot-mro` | `GET {prefix}/health` (`main.py:228-236`) | static, and leaks `settings.debug` |
| `copilot-mro` | `GET {prefix}/metrics` (`main.py:239-245`) | `prometheus_client.generate_latest()` — default `python_gc_*`/`process_*` collectors only |
| `core` | `GET {prefix}/health` (`core/core/fastapi_app.py:232-241`) | static |
| `shift-optimizer` | `GET /health` (`shift_optimizer/app/api/health.py:12-16`) | static + package version |
| automations worker | **none** — it is not an HTTP server | — |
| collector (local stack) | `:13133` health_check, `:1777` pprof, `:55679` zpages (`otel-collector-config.yaml:65-71`) | |

No `/ready`, `/readyz`, `/livez` or `/healthz` route exists anywhere.

---

## 2.6 Background work

| Worker | Entry point | Service name in logs | Spans | Metrics | Log context |
|---|---|---|---|---|---|
| **Automations worker** (standalone process) | `api/flynapse_api/automations/worker.py:main()` `:471`, loop task `TASK_NAME="automation-scheduler"` (`:107`) | `os.getenv("OTEL_SERVICE_NAME") or "automation-worker"` (`:469`, `SERVICE_NAME` at `:111`) | ❌ none — no `get_tracing_service` import | ❌ none | ❌ no `logger.contextualize` anywhere in `api/flynapse_api/automations/` |
| **Automations executor** (in-process, also runs embedded in the gateway) | `api/flynapse_api/automations/executor.py` | inherits the host process's | ❌ (the pipeline's `agent_sdk.run_query` becomes a **root** span) | inherits the pipeline's | mints `session_id = f"automation:{run_id}"` (`:1091-1092`) which is the ledger's `origin` discriminator (`request_id.py:10-25`, `llm_usage.py:63-68`), but binds nothing to loguru |
| **Improvement loop scheduler** | `copilot-mro/.../services/improvement/scheduler.py`, `runner.py` | inherits | ❌ | ❌ | ⚠️ stdlib `logging` — invisible to Loki (G22) |
| **Document-hub processing** | `document_hub/processing.py` — rides the automations substrate (`operations.py:7-10`) | inherits | ❌ | ✅ the `document_hub_*` families | ❌ |
| **Thread pools** | `asyncio.to_thread` throughout (`chat_management.py:788, 823, 1488, 1623`); telegram-bot's default executor is `min(32, cpu_count()+4)` (`telegram-bot/telegram_bot/app.py:204`) | — | context **is** carried by `to_thread` (see §2.2.2) | — | loguru's `contextualize` is a contextvar, so it is carried too |
| **Lambdas** (`cognito-lambdas`) | `lambdas/cognito-lambdas/app.py` | none — never calls `setup_logging`; installs its own sink `logger.add(lambda msg: print(msg, end=""), …)` (`:24-25`) | ❌ | ❌ | ❌ |
| **`llm-platform` certification runs** | `llm_platform/certify.py` (console script) | n/a | ❌ | ❌ | writes JSON reports to `docs/certification/` |
| **Parser / ingest scripts** | `services/parsers/*.py` `__main__` blocks call `setup_logging(name="…-parser", env="development")` (`crew_manual_parser.py:1485`, `amos_parser.py:4585`, `ifim_parser.py:2569`, `mel_parser.py:1492`, `tn_parser.py:1932`, `ftd_parser.py:1962`, `amos_post_processing.py:2828`, `amos_metadata_backfill.py:251`, `s3_pdf_processor.py:692`) | **one service name per parser** — nine more `service_name` values that no dashboard knows about (extends G12) | ❌ | embedding metrics only | ❌ |

---

## 2.7 Configuration — every telemetry knob

### 2.7.1 Settings fields

| Env var | Default | Declared in | Read by |
|---|---|---|---|
| `OTEL_ENDPOINT` | `http://localhost:4317` | `utils/utils/config.py:103-105`; **also** `api/flynapse_api/config/config.py:94-96` and `copilot-mro/copilot_mro/app/config.py:950-952` | **Only `utils.config`'s copy has any effect** — `tracing.py:93,95`, `metrics.py:131,133`, `logging_config.py:243,256`. The per-repo copies are read by nothing (G14). |
| `OTEL_SERVICE_NAME` | `flynapse-utils` (utils) / `copilots` (api) / `mro-copilot-rag` (copilot-mro) | `utils/utils/config.py:106`, `api/.../config.py:97`, `copilot-mro/.../config.py:953` | Passed as the `name` argument to `setup_logging` / `get_tracing_service` / `get_metrics_service`. Overridden in the image: `api/Dockerfile:88 ENV OTEL_SERVICE_NAME="copilots"`. Worker override at `worker.py:469`. |
| `OTEL_ENV` | `development` | `api/.../config.py:98`, `copilot-mro/.../config.py:954` | `deployment.environment` resource attribute. **Not declared in `utils/config.py`** — `setup_logging(name, env)` takes it as an argument. |
| `OTEL_VERSION` | `1.0.0` | `api/.../config.py:99`, `copilot-mro/.../config.py:955` | `service.version` resource attribute (tracing/metrics only). |
| `OTEL_ENABLED` | `True` | `utils/utils/config.py:107`, `api/.../config.py:100`, `copilot-mro/.../config.py:956` | **Only** `logging_config.py:119` (G13). |
| `LOG_LEVEL` | `INFO` | `utils/utils/config.py:110`, `api/.../config.py:103`, `copilot-mro/.../config.py:959` | `setup_loguru` — all four sinks. `api/Dockerfile:37 ARG LOG_LEVEL=INFO` → `:67 ENV LOG_LEVEL="${LOG_LEVEL}"`. |
| `LOG_DIR` | `logs` | `utils/utils/config.py:111`, `api/.../config.py:104`, `copilot-mro/.../config.py:960` | The two file sinks. `api/Dockerfile:69 ENV LOG_DIR="/tmp/logs"`. |
| `LOG_COLORS` | `True` | `utils/utils/config.py:112` **only** | `setup_loguru`. Also honours `NO_COLOR` (`logging_config.py:78-79`). Note: `True` by default means **ANSI escapes on stdout in production** unless `NO_COLOR` is set. |
| `DEBUG` | `False` | `utils/utils/config.py:59`, `api/.../config.py:65`, `core/core/config.py:66`, `copilot-mro/.../config.py:68` | Gates `debug_dumps` (`_debug_dump.py:54,199`); also leaked by the copilot-mro stub health route. |
| `METRICS_SCRAPE_TOKEN` | `None` | `api/flynapse_api/config/config.py:189-191` | `auth/metrics_scrape.py:51` — **unset ⇒ the `/metrics` route is open** (`:31-34`). |
| `LOKI_BASE_URL` | `http://localhost:3100` | `core/core/config.py:73` | `chat_quality_service.py:835` — the product analytics dashboard. |
| `ANALYTICS_CACHE_TTL_SECONDS` | `300` | `core/core/config.py:74-76` | analytics response cache |
| `ANALYTICS_RATE_LIMIT_WINDOW_SECONDS` | `60` | `core/core/config.py:77-79` | |
| `ANALYTICS_RATE_LIMIT_MAX_REQUESTS` | `60` | `core/core/config.py:80-82` | |
| `ANALYTICS_LOKI_QUERY_LIMIT` | `5000` | `core/core/config.py:83-85` | `chat_quality_service.py:845, 888` |
| `ANALYTICS_LOKI_TIMEOUT_SECONDS` | `10` | `core/core/config.py:86-88` | `chat_quality_service.py:849` |
| `AGENT_RUNTIME` | `claude` | `copilot-mro/copilot_mro/app/config.py:1064` | Selects the runtime (`agent_pipeline.py:453-459`); `lang` disables the span + `llm_usage` path entirely (G26) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` (frontend) | `http://localhost:4318/v1/traces` | `dashboard/lib/runtime-config.ts:90-93` | `dashboard/lib/observability/otel.ts:37`. **Not in the Amplify env allowlist** (`dashboard/amplify.yml:10`). |
| `OTEL_CORS_ORIGIN_1` / `_2` | `http://localhost:3001` / `https://demo.app.flynapse.ai` | `observe-docker-compose.yml:19-20` | the collector's OTLP/HTTP CORS allow-list |

`shift-optimizer`, `telegram-bot`, `lambdas` and `llm-platform` declare **no** telemetry settings.
`core` declares no `OTEL_*` at all — it inherits whatever the gateway configured.

### 2.7.2 What `iac/` actually sets

| Resource | Telemetry env |
|---|---|
| `aws_apprunner_service.api` (`iac/apprunner.tf:31-79`) | `OTEL_ENDPOINT = "http://<weaviate_observability private ip>:4317"` (`:42`) — **and nothing else**. No `OTEL_ENABLED`, `OTEL_ENV`, `OTEL_VERSION`, `LOG_LEVEL`, `METRICS_SCRAPE_TOKEN`, `LOKI_BASE_URL`. |
| `aws_lambda_function` (`iac/lambda.tf:109`) | `OTEL_ENDPOINT` set to the same private IP — but the lambda never initialises OTel (§2.6), so the variable is inert. |
| `aws_instance.weaviate_observability` (`iac/ec2.tf:2-36`) | `t2.large`, **public subnet** (`:5`), 30 GB gp3 root, `user_data` = `iac/demo_ec2_setup.sh`, which clones the repo and runs `docker-compose up -d` on `deployment/demo/docker-compose.yml` (`demo_ec2_setup.sh:93`) — collector + Prometheus + Loki + Tempo + Grafana + Weaviate + weaviate-ui on **one** box. Persistence under `/opt/persistent-data/observability-data/{prometheus,loki,grafana,tempo}` (`:43-46`). |
| Amplify (`dashboard/amplify.yml:10`) | allow-lists `ENV, APP_VERSION, API_BASE_URL, API_PREFIX, MRO_PREFIX, CORE_PREFIX, COGNITO_*, COMPANY` and any `NEXT_PUBLIC_*` — no OTel variable can reach the build. |
| CloudWatch | no `aws_cloudwatch_log_group`, no `aws_cloudwatch_metric_alarm`, no X-Ray, no ADOT resource in `iac/`. |

---

## 2.8 Verdict index (quick reference)

| Audit item | Verdict |
|---|---|
| §2.1–2.4, 2.9, 2.10 | CONFIRMED |
| §2.5 (HTTP metric line range), §2.6 (LLM metric line range), §2.7 (doc-hub count), §2.8 (span attributes) | PARTIAL |
| §2.8b (`loop_observability.py` path) | REFUTED — file is under `agent_shared/`, not `agent_claude/` |
| G1, G3, G4, G5, G6, G9, G10, G11, G12, G13, G14, G15, G16, G17a, G17d, G17e | CONFIRMED |
| G2 (causal chain), G7 (provenance + dead-count), G8 (reason), G17b (two corrections) | PARTIAL |
| G17c (`_total_total` normalization worry) | **REFUTED** — see §1.3 |
| New: G18 (prompt text in Loki), G19 (`set_gauge` is not a gauge), G20 (label cardinality), G21 (no `service_name` label in Prometheus), G22 (stdlib logging never bridged), G23 (`setup_loguru` silent no-op), G24 (fabricated, racy timestamps), G25 (blocking file sinks), G26 (LangGraph runtime is telemetry-dark), G27 (singleton services), G28 (health/readiness), G29 (`LOKI_BASE_URL` unset in AWS), G30 (`METRICS_SCRAPE_TOKEN` unset), G31 (unauthenticated Loki on a public subnet, unlimited retention), G32 (13+ service identities), G33 (telegram-bot correction), G34 (core/shift-optimizer inherit the gateway) | — |

**Severity ordering for the redesign** (my judgement, not the audit's):
1. **G29** — the flagship product observability feature does not work in the deployed environment.
2. **G18 + G31** — user prompt text on an unauthenticated, unlimited-retention log store.
3. **G20 + G19 + G21** — the metric layer's shape is wrong (cardinality, instrument kinds, labels),
   so "just point it at CloudWatch/New Relic" would be expensive and still unqueryable.
4. **G4 + G5** — with no auto-instrumentation and no outbound propagation, traces can never be more
   than the eight hand-rolled spans; every latency question is currently unanswerable.
5. **G8/G9/G26** — the cost data exists and is good (`llm_usage` / `llm_model_calls`); it simply has
   no metric, no dashboard and no reader, and one of the two runtimes writes neither.
