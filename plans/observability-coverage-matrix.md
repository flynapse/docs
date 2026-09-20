# R.3 — Estate-wide signal coverage matrix

**Date:** 2026-09-20. **Task:** Task R / Phase G.1, half R.3. **Mode:** read-only audit. No code, plan or repo was changed.

## Scope

Every operational boundary in the four merged trees plus the three satellites, recorded against three columns: does it emit a **span**, a **metric**, a **trace-correlated structured log**.

### Trees read, with HEAD

| Tree | Path | HEAD | Branch |
|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `9812f44028ce14551dadce199722c10c14dcb035` | `obs-merge` |
| utils | `/home/aditya/Code/utils-obsm` | `e6b464e82dff615afa465dc828adfc21b81fbe34` | `obs-merge` |
| core | `/home/aditya/Code/core-obsm` | `d7f7b5469a803e07e9fbbafa56d7ec1496febd4d` | `obs-merge` |
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `ea0ac559ac2d379cd9c1f3292fd8df090cc75ffd` | `obs-merge` |
| flynapse-otel (shared pkg, read for mechanism) | `/home/aditya/Code/flynapse-otel` | `1cafda2231e0d1f7c2a1db24274ffa3bac3c0a67` | `main` |
| telegram-bot | `/home/aditya/Code/telegram-bot` | `3102fcc400273353835d311b2a91e1ef1307d28c` | `main` |
| shift-optimizer | `/home/aditya/Code/shift-optimizer` | `1ba897e8168d79ee0fba4611af9d272630b7c290` | `main` |
| dashboard | `/home/aditya/Code/dashboard` | `4a2898bd6559294926a8e5c67dbe82218fa562b8` | `agent_sdk` |

**`dashboard-obsm` was NOT read.** It is mid-merge under another agent right now. Every dashboard row below describes the **pre-merge** `dashboard` tree; **the merged dashboard state is unresolved and nothing here should be read as describing it.**

### R.4 deferral

G.1 has two halves. **This document is R.3 only — the coverage matrix.** **R.4 (orphan analysis over dashboards and alerts) was deliberately not attempted**, because two fix executors are editing dashboards, alerts, runbooks and cloud alarms concurrently; an orphan analysis run today would describe a state that will not exist tomorrow. Things noticed in passing that R.4 will want are listed in the appendix and nothing more was done with them.

Application code is not being edited by anyone right now, which is what makes R.3 runnable.

---

## Mechanism this audit relies on (read before judging the third column)

**Bootstrap.** `flynapse_otel.bootstrap.bootstrap()` (`flynapse-otel/flynapse_otel/bootstrap.py:115`) configures the three SDK providers from `OTEL_*` env and applies the client instrumentors the *caller declares*. `utils.observability.bootstrap` (`utils-obsm/utils/observability/bootstrap.py:45`) is a thin wrapper that bakes in six names for every api-side process:

```
psycopg2, httpx, requests, urllib3, redis, threading
```

Deliberately **not** declared: `botocore` (would double the `gen_ai.*` families) and `fastapi`/`asgi` (the gateway wires its own mount-aware ASGI middleware). Source: `utils-obsm/utils/observability/bootstrap.py:33-42`.

**Log correlation — the mechanism I judged the third column against.** `utils.observability.log_bridge.install()` (`utils-obsm/utils/observability/log_bridge.py:194`) installs exactly two loguru sinks:

1. a JSON stdout sink that reads `trace.get_current_span().get_span_context()` **at emit time** and writes `trace_id` / `span_id` onto the line only when that context is valid (`log_bridge.py:130-137`);
2. an OTLP sink built on the OTel SDK `LoggingHandler`, which attaches the ambient trace context the same way (`log_bridge.py:141-197`).

`utils.observability.intercept.install()` (`utils-obsm/utils/observability/intercept.py:70`) routes stdlib `logging` into loguru so non-loguru subsystems reach the same two sinks.

Both are installed by `utils.logging_config.setup_logging()` (`utils-obsm/utils/logging_config.py:47`), which is also what calls `bootstrap()`.

**Therefore a log line is trace-correlated if and only if both hold:**
(a) `setup_logging()` ran in that process, and
(b) the line is emitted while a recording span is current.

A line emitted in a process that only called `bootstrap()` (not `setup_logging()`) reaches loguru's *default stderr sink*, not the OTLP pipeline, and carries no `trace_id`. A line emitted outside any span carries no `trace_id` even with the sinks installed. I applied that test literally; where a row says "yes" it means I traced a live span enclosing the log site, not merely that a log call exists.

**Auto-instrumentor consequences I verified in the installed packages** (`/home/aditya/Code/api/.venv/lib/python3.11/site-packages`, `opentelemetry-*` 1.44.0 / 0.65b0):

| Instrumentor | Span | Metric |
|---|---|---|
| `psycopg2` (via `dbapi`) | yes | yes — `db.client.operation.duration` (`instrumentation/dbapi/__init__.py:522,886`) |
| `httpx` | yes | yes — `http.client.request.duration` (`instrumentation/httpx/__init__.py:784,792`) |
| `urllib3` | yes | yes — duration + request/response size (`instrumentation/urllib3/__init__.py:330-365`) |
| `requests` | yes | yes — duration (`instrumentation/requests/__init__.py:584,593`) |
| `redis` | yes | **no metric** — the redis instrumentor creates no instruments at all (grep for `create_histogram`/`meter` in `instrumentation/redis/__init__.py` returns nothing) |
| `threading` | context propagation only | no |

**The botocore nuance, verified rather than assumed.** No `botocore` instrumentor is declared anywhere in the estate. But `botocore.httpsession` calls `conn.urlopen(...)` (`botocore/httpsession.py:509`) on a `urllib3.HTTPConnectionPool`, and the urllib3 instrumentor patches exactly `urllib3.connectionpool.HTTPConnectionPool.urlopen` (`instrumentation/urllib3/__init__.py:434,552`). **So every boto3 call — S3, Bedrock, SES, Cognito, DynamoDB — does get a CLIENT span and an `http.client.request.duration` sample, as an HTTP call.** What it does *not* get is AWS semantics: no `rpc.system`/`rpc.service`/`aws.*`, no `gen_ai.*`. Rows below say "urllib3 (HTTP-shaped only)" where that is the whole of the coverage.

**The Weaviate nuance.** `weaviate-client` 4.17.0 uses `httpx` for REST (`weaviate/connect/v4.py:198,204`) — auto-instrumented — but **gRPC** for the search path (`weaviate/collections/grpc/query.py`, `weaviate.proto.v1`). No gRPC instrumentor is declared anywhere in the estate, so searches have no auto span; only the one hand-written `weaviate.hybrid_search` span covers any search.

---

## Gap table

`file:line` is the instrumentation site when one exists, otherwise the boundary's own definition site. All paths are repo-relative.

### A. HTTP routes and mounted sub-apps

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Gateway HTTP request (every route, all methods) — the mount-aware ASGI middleware | api | `flynapse_api/main.py:352` → `flynapse_api/telemetry/http_server.py:269,313` | **yes** — one SERVER span, `http.route` composed **through** the mounts (`resolve_route`, `http_server.py:81`) | **yes** — `http.server.request.duration` (+ old-semconv `http.server.duration`) and `http.server.active_requests`, both re-timed to the final response send (`http_server.py:155,173`) | **yes** — `LoggingContextMiddleware` binds `request_id`/`tenant_id`/`user_id`/`session_id`/`method`/`path` (`flynapse_api/middleware/logging.py:66`) inside the span | — |
| Request identity onto the server span | api | `flynapse_api/telemetry/request_identity.py:74`, called from `middleware/logging.py:78` | yes (attributes on the existing span) | n/a | yes | skips `"unknown"` placeholders, so an anonymous request carries no identity attrs by design |
| Gateway auth rejections (401/403 refused **before** routing) | api | `flynapse_api/middleware/telemetry.py:34,85` | yes (carries the SERVER span — D1 puts OTel outside auth) | **yes** — `auth.rejections` counter | yes | route-level 403s deliberately not counted |
| `X-Trace-Id` response header | api | `flynapse_api/middleware/telemetry.py:41` | n/a | n/a | n/a | — |
| Gateway own routers: `/api/v1/health`, `/api/v1/`, `/api/v1/test-cookie`, auth router | api | `flynapse_api/main.py:443,459,469,476` | yes (gateway span) | yes | yes | — |
| Health probes `/health/live`, `/health/ready` | api | `flynapse_api/routers/health.py:52,91`; excluded at `telemetry/http_server.py:56` | **no — excluded by design** | **no — excluded** | **no** — the readiness aggregate's log lines run outside any span | intentional exclusion; the consequence is that a failing readiness probe leaves an uncorrelated log line and no signal |
| Mounted sub-app `/api/v1/mro/**` (copilot-mro) | api + copilot-mro | mount `flynapse_api/main.py:398`; app `copilot_mro/app/main.py:288` | yes (gateway span, full mounted route) | yes | yes | — |
| Mounted sub-app `/api/v1/core/**` (core) | api + core | mount `flynapse_api/main.py:424`; app `core/fastapi_app.py:118` | yes (gateway span) | yes | yes | core contributes nothing of its own (see §F) |
| Mounted sub-app `/api/v1/optimizer/**` (shift-optimizer) | api + shift-optimizer | mount `flynapse_api/main.py:411` | yes (gateway span) | yes | yes | — |
| Mounted sub-apps' own `/v1/health` routes | api | excluded at `telemetry/http_server.py:58` | **no — excluded** | **no — excluded** | n/a | intentional |
| Browser OTLP ingest: `POST …/logging/ingest/v1/{logs,traces}` | core | `core/resources/logging/logging_endpoints.py:325,331`; excluded at `api-obsm/flynapse_api/telemetry/http_server.py:64` | **no — excluded from the gateway span** | **no — excluded, and no counter of its own** | **no** — rate-limit warnings (`:105`), forward failures (`:249,258,271`), "endpoint unset" (`:204`) and client-abandon (`:284`) all emit **outside any span** | **the telemetry front door has no signal of its own.** Volume, rejection rate, collector 5xx rate and drop-on-unset are visible only as uncorrelated log lines |
| Browser OTLP ingest: `POST …/logging/public/ingest/v1/{logs,traces}` (anonymous) | core | `core/resources/logging/logging_endpoints.py:337,343` | **no — excluded** | **no** | **no** | same; this is also the unauthenticated surface, so its 429/413 rate is the one an operator would most want |
| Ingest → collector forward (outbound `httpx.AsyncClient`) | core | `core/resources/logging/logging_endpoints.py:178-185` | **yes** — httpx auto-instrumentor CLIENT span, but it is a **trace ROOT** (parent span excluded) | yes — `http.client.request.duration` | no (the forward's own log lines sit outside the excluded route's span) | the client span is orphaned from any request trace, by construction of the exclusion |
| Product-events ingest `POST …/analytics/events` | core | `core/resources/analytics/events_endpoints.py:67` | **yes** — *not* in the exclusion list, so it carries the gateway SERVER span | **yes** — gateway request metrics | **yes** — refusal/abandon logs (`:98,165`) emit inside the span | asymmetry worth recording: the product-analytics front door is traced, the OTLP telemetry front door is not |
| Telemetry ingest health `GET …/logging/health` | core | `core/resources/logging/logging_endpoints.py:350` | yes (gateway span) | yes | yes | — |
| Every other core route (users, tenants, roles, departments, comments, documents, pdf pages, invitations, notifications, automations, analytics panels, channel provisioning, authz, operators) | core | `core/fastapi_app.py:160-193` | yes — **inherited from the gateway only** | yes — inherited | yes | **core creates zero spans and zero metrics of its own** (§F) |
| Copilot-mro routes (chat management, chat files, document hub, data discovery, memory, AD review, flight-ops brief, improvement, llm observability, mro documents, user feedback) | copilot-mro | `copilot_mro/app/main.py:31-41` | yes (gateway span) | yes | yes | — |
| `POST /chats/rag` (non-streaming chat turn) | copilot-mro | `copilot_mro/app/api/chat_management.py:1212` (`chat.enhanced_chat`), `:1222` (`rag.pipeline.execute`) | **yes** — two nested INTERNAL spans under the gateway SERVER span | see §D for the agent metrics | yes | — |
| `POST /chats/rag/stream` (SSE turn) | copilot-mro | `copilot_mro/app/api/chat_management.py:1576` (`chat.enhanced_chat_stream`), `:1586` (`rag.pipeline.execute`) | yes | see §D | yes | the SSE byte-pump phase itself is not separately spanned |
| Chat block save, request path | copilot-mro | `copilot_mro/app/api/chat_management.py:1332` (`db.chat.save_block`) | yes | **yes** — `chat_block_save_failures_total` counter on the failure path (`:379`, legacy shim) | yes | failures counted, successes not |
| Chat block save, background task (client disconnected) | copilot-mro | `copilot_mro/app/api/chat_management.py:1734` (`db.chat.save_block`) | yes | yes (same counter) | yes | **separate row from the one above by design:** this one runs as its own task, so its span is a trace root unless contextvars carried the parent; the two entry paths are instrumented by the same span name but reached differently |
| Standalone copilot-mro app (`uvicorn copilot_mro.app.main:app`, not mounted) | copilot-mro | `copilot_mro/app/main.py:12` | **no HTTP span** — no ASGI instrumentation is applied in this runtime; `instrument_gateway` lives in `api` | **no HTTP request metric** | yes (sinks installed by `setup_logging` at `:12`) | **second runtime, instrumented differently:** every copilot-mro route served standalone loses its SERVER span and its `http.server.*` metrics entirely. The per-turn spans (`chat.enhanced_chat` etc.) survive but become trace roots |
| Standalone core app (`python core/fastapi_app.py`) | core | `core/fastapi_app.py:148` | **no** | **no** | **no — `setup_logging()` is never called anywhere in `core`**, so neither sink is installed and loguru falls back to its default stderr sink | **second runtime, wholly dark.** Verified: no `setup_logging` call site exists in `core-obsm/core/` (grep across the package) |

### B. Background jobs and schedulers

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Automation **run** (the unit of scheduled work) | api | `flynapse_api/telemetry/run_span.py:26`, entered at `flynapse_api/automations/executor.py:953` | **yes** — `automation.run`, INTERNAL, new trace root per run, with `tenant.id`/`enduser.id`/`automation.*` | **no metric** — there is no run counter, no duration histogram, no active-runs gauge | **yes** — `logger.contextualize` binds the same identity for the whole run (`run_span.py:48`) | no metrics at all for the scheduled-work path |
| Automation **scheduler tick** (`run_tick` / `scheduler_loop`) | api | `flynapse_api/automations/loop.py:2869,3363` | **no** | **no** | **no** — every tick line (claims, skips, contention, reaping, retry sweeps) is emitted with no span current | **the clock itself is uninstrumented.** `run_span.py:8-10` states this explicitly: "the scheduler is not instrumented until Stream L's phase". Tick latency, due-scan size, claim contention and skip reasons are log-only and uncorrelated |
| Scheduler start / stop (embedded mode) | api | `flynapse_api/automations/loop.py:3469,3517`; called from `main.py:204,241` | no | no | start: **no** (runs in the lifespan, outside any span); stop: **no** | — |
| **One-shot run execution** (document-hub process/cleanup, data-discovery job, AD materialize, announcements) | api | `flynapse_api/automations/one_shot.py:148` | **no span at this layer** | **no** | **no** — `execute_one_shot_run`'s own lines (start, timeout, failure, completion) emit outside any span | the handler *bodies* are spanned (next four rows), but those spans become **trace roots** with no parent and no link, so queue-wait, attempt number and timeout-kill are invisible from the trace |
| Document Hub processing (one-shot body) | copilot-mro | `copilot_mro/app/services/document_hub/processing.py:137` (`document_hub.process`) | yes | no | yes (inside its own span) | root span, no parent/link to the enqueue or the tick |
| Document Hub cleanup sweep (one-shot body) | copilot-mro | `copilot_mro/app/services/document_hub/cleanup.py:213` (`document_hub.cleanup`) | yes | no | yes | same |
| Data Discovery job (one-shot body) | copilot-mro | `copilot_mro/app/services/data_discovery/runner.py:142` (`data_discovery.job.run`) | yes | no | yes | same |
| AD materialize / announcements (one-shot bodies) | api | `flynapse_api/automations/ad_materialize.py:299`, `announcements.py` | **no** | **no** | **no** | these two one-shot kinds have no span anywhere on their path |
| Automations **worker process** (separate runtime) | api | entry `flynapse_api/automations/worker.py:478`; logging at `:469` | run spans yes (same `automation.run`); tick no | no | yes for runs, no for ticks | **`main()` never calls `shutdown_telemetry`.** It closes the Postgres pool (`:391`) but the three providers are left to the SDK's own atexit hooks — three sequential unbounded flushes, the exact failure mode `api-obsm/flynapse_api/main.py:302-312` exists to prevent in the gateway |
| Improvement timer loop (tick) | copilot-mro | `copilot_mro/app/services/improvement/scheduler.py:323` | **no** | **no** | **no** — "timer started"/"stopped"/"off" lines emit outside any span | the loop is uninstrumented; only the run inside it is spanned |
| Improvement **run** | copilot-mro | `copilot_mro/app/services/improvement/runner.py:460` (`improvement.run`) | yes | **no** | yes | no metric |
| Improvement **stage** | copilot-mro | `copilot_mro/app/services/improvement/runner.py:507` (`improvement.stage`) | yes | no | yes | — |
| Improvement timer start/stop | copilot-mro | `copilot_mro/app/services/improvement/scheduler.py:334,378` | no | no | no | — |
| Background S3 PUT for chat uploads (off the request path) | copilot-mro | `copilot_mro/app/services/chat_file_service.py:905`, task created at `:123` | **no span of its own**; the boto3 call inside gets a urllib3 CLIENT span | no | partly — the task inherits the request's contextvars, so lines land under a span that has usually already **ended** | no span for the retry loop, so a PUT that retried three times and failed is only a log line |
| LLM content-capture background tasks | copilot-mro | `copilot_mro/app/services/agent_shared/llm_content_capture_tasks.py:33` | no | no | inherits context | — |
| Parser CLI entrypoints (AMOS, MEL, TN, FTD, IFIM, crew manual, AMOS metadata backfill, S3 PDF) | copilot-mro | `parsers/amos_parser.py:4659`, `mel_parser.py:1541`, `tn_parser.py:1974`, `ftd_parser.py:2003`, `ifim_parser.py:2604`, `crew_manual_parser.py:1546`, `amos_metadata_backfill.py:272`, `s3_pdf_processor.py:927` | **yes** — one `ingest.parse` span per process, `parser.kind` attribute, `operation.outcome` | **no** | **yes** — `setup_logging` is called first in each (`…:1973` etc.), so the sinks are installed and every parser line sits inside the span | no metric; no explicit telemetry shutdown, so the final flush is the SDK's unbounded atexit |
| Data Discovery CLI (`stage`, `reset-local-schema`) | copilot-mro | `copilot_mro/app/services/data_discovery/cli.py:140` | **no span** | **no** | **no** — it calls `bootstrap("data-discovery-job")` (`:39,140`), **not** `setup_logging`, so the loguru sinks are never installed; its lines go to loguru's default stderr and carry no `trace_id`, and none reach the OTLP logs pipeline | the one process in the estate that bootstraps the SDK without bootstrapping its logs |
| Lambda handler (S3 PDF processor) | copilot-mro | `lambda_functions/s3_pdf_processor_lambda.py:23` | **no** | **no** | **no** — imports `loguru` directly and never calls `setup_logging`; no bootstrap on its import chain (`copilot_mro/app/__init__.py` is empty; `services/__init__.py` is empty) | **third runtime for the same parsing work, wholly uninstrumented** — the CLI path of the same processor has `ingest.parse`, the Lambda path has nothing |

### C. External clients

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Postgres — tuple cursors | utils | instrumentor declared `utils/observability/bootstrap.py:35` | **yes** — psycopg2 auto-instrumentor CLIENT span | **yes** — `db.client.operation.duration` | yes when inside a span | — |
| Postgres — dict cursors (`RealDictCursor`) | utils | `utils/postgres_service.py:126,373,400,450,478` | **yes** — the traced dict-cursor factory restores the span the per-cursor `cursor_factory=` would otherwise bypass | yes | yes | falls back to an **untraced** cursor with one warning if the instrumentor is absent (`postgres_service.py:150`) |
| Postgres — connection pool acquisition | utils | `utils/postgres_service.py` (`_ensure_pool`) | **no** | **no** | no | pool exhaustion / wait time is invisible |
| Redis (cache, auth cache, rate-limit windows) | utils | instrumentor declared `utils/observability/bootstrap.py:38`; client `utils/cache_service.py:16,141` | **yes** — redis auto-instrumentor CLIENT span | **no — the redis instrumentor emits no metrics at all** (verified in the installed package) | yes | no cache hit/miss counter anywhere; hit rate is `get_cache_stats()` only (`api-obsm/flynapse_api/middleware/cache.py:289`) |
| Weaviate — hybrid search | utils | `utils/weaviate_service.py:1011` (`weaviate.hybrid_search`) | **yes** — hand-written CLIENT span with `db.system`, `server.address`, `tenant.id`, `search.result_count` | **no** | yes | — |
| Weaviate — `bm25_search`, `vector_search` | utils | `utils/weaviate_service.py:1198,1296` | **no** | **no** | no | **two of the three search modes are unspanned.** They go over gRPC, which no declared instrumentor covers, so there is no auto fallback either |
| Weaviate — object CRUD (`get_object_by_id`, `get_vector`, `query_objects`, `list_all_objects`, `list_all_uids`, `update_object_property`, `delete_object_by_id`, `delete_objects_by_property`, `delete_collection`, schema ops) | utils | `utils/weaviate_service.py:405,455,496,537,573,626,654,712,836,878,1763,1942` | **no explicit span**; REST ops ride httpx so they get an httpx CLIENT span | httpx duration only | yes | twelve-plus operations with HTTP-shaped coverage and no `db.*` semantics |
| Weaviate health check | utils | `utils/weaviate_service.py:910` | no explicit span (httpx only) | no | yes | — |
| S3 — `download_pdf` | utils | `utils/s3_service.py:226` (`s3.download`) | **yes** — hand-written CLIENT span, `rpc.system=aws-api`, `rpc.service=S3`, `server.address` | **no** | yes | — |
| S3 — every other operation (`upload_file`, `upload_json`, `download_json`, `upload_text`, `list_pdfs`, `list_files`, `delete_files_by_keyword`, `check_file_exists`, `download_folder`, `upload_folder`, `put_objects_parallel`, bucket ops, `health_check`) | utils | `utils/s3_service.py:309,350,377,413,438,474,566,769,910,1058,1177,1223` | **no explicit span** — only the urllib3 CLIENT span under botocore (HTTP-shaped only) | urllib3 `http.client.request.duration` only | yes | **one S3 method of ~sixteen is spanned.** The rest are indistinguishable from any other outbound HTTPS in the trace — no `rpc.*`, no bucket, no key |
| Bedrock / LLM — governed agent path | copilot-mro | `copilot_mro/app/services/agent_shared/telemetry.py:1498,1721` (`invoke_agent <runtime>`) | **yes** — with `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.conversation.id` | **yes** — `gen_ai.client.operation.duration`, `gen_ai.client.token.usage`, `agent.model.calls`, `agent.model.cost_usd`, `agent.model.unpriced_calls` (`telemetry.py:1411-1435`) | yes | the underlying boto3 HTTP call also produces a separate urllib3 span inside it |
| Bedrock / LLM — legacy `recorded_llm_call` path | utils | `utils/llm.py:367` (metering), `:786` (streaming accumulate) | **no span** — only the urllib3 span under boto3 | **yes, legacy-shaped** — `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request` via the compat shim (`utils/observability/metrics.py:57`) | yes | **two metric vocabularies for the same boundary.** Sole non-test caller found: `copilot-mro-obsm/copilot_mro/app/services/agent_claude/cited_synthesis.py` |
| Embeddings (Azure OpenAI) | utils | `utils/llm.py:1180-1196`, `:1300-1305`; service `utils/embedding_service.py` | **no span** | **yes, legacy-shaped** — `embedding_requests_total`, `embedding_tokens_total`, `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`, `embedding_cache_tokens_avoided_total` | yes | metered but never spanned; only the httpx/urllib3 span underneath |
| Agent tool execution | copilot-mro | `copilot_mro/app/services/agent_shared/telemetry.py:1881,1889` (`execute_tool <name>`); backdated variant `agent_shared/loop_observability.py:248` (`agent_sdk.tool.<short>`) | yes | **yes** — `agent.tool.calls`, `agent.tool.attempts` | yes | — |
| Agent subagent calls | copilot-mro | `copilot_mro/app/services/agent_shared/telemetry.py:1447,1452` | yes | **yes** — `agent.subagent.calls`, `agent.subagent.duration_seconds` | yes | — |
| Agent turn (the whole turn) | copilot-mro | `copilot_mro/app/services/agent_shared/telemetry.py:1401,1406` | yes (the `invoke_agent` root) | **yes** — `agent.turn.calls`, `agent.turn.duration_seconds` | yes | — |
| Memory — item fetch | copilot-mro | `copilot_mro/app/services/memory/memory_db.py:67` (`memory.items.get_by_ids`) | yes | **yes** — `memory_get_latency_ms` (legacy shim, `:880`) | yes | — |
| Memory — search | copilot-mro | `copilot_mro/app/services/memory/memory_index.py:96` (span name from the decorated operation) | yes | **yes** — `memory_search_latency_ms` (legacy shim, `:636`) | yes | — |
| Cognito (token validation, JWKS, session revoke) | api | `flynapse_api/auth/jwks.py:36` (`requests.get`); `flynapse_api/auth/auth.py`; `flynapse_api/routers/auth.py` | **yes** — `requests`/`urllib3` auto CLIENT span, inside the gateway request span (D1 puts OTel outside auth) | yes — `http.client.request.duration` | yes | HTTP-shaped only; no auth-specific span, no JWKS cache hit/miss metric |
| SES email | utils | `utils/email_service.py:49` | **no explicit span** — urllib3 under boto3 | urllib3 duration only | yes | — |
| SMTP email | utils | `utils/smtp_email_service.py:174` (`smtplib.SMTP`) | **no — `smtplib` is instrumented by nothing in this estate** | **no** | yes (the surrounding log lines) | **a fully dark network boundary.** There is no smtplib instrumentor in the declared set or the catalogue |
| DynamoDB | utils | `utils/dynamodb_service.py` | no explicit span — urllib3 under boto3 | urllib3 duration only | yes | DynamoDB is retired per the consolidation; the module still exists |
| Weaviate boot-check probe | copilot-mro | `copilot_mro/app/services/weaviate_boot_check.py` | inherits the startup span when run from copilot-mro's lifespan; **no span** when run from the gateway lifespan | no | gateway path: **no** | see §E |

### D. Queues

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| The durable job queue is a **Postgres table** (`automation_runs`), not a broker | — | — | — | — | — | **No message broker exists in this estate.** Verified: no SQS client, no Celery, no kombu, no RQ, no pika, no kafka in `api`, `utils`, `core` or `copilot-mro` |
| Enqueue (producer): `enqueue_one_shot_run` | core | `core/resources/automations/services/automation_store.py:931` | **no producer span** | **no** | inherits the caller's span when enqueued from a request (Document Hub upload, Data Discovery), **none** when enqueued from the gateway lifespan | — |
| Enqueue seam install (Document Hub) | copilot-mro | `copilot_mro/app/services/document_hub/job_enqueue.py:139` | no | no | no (lifespan) | — |
| Enqueue seam install (Data Discovery) | copilot-mro | `copilot_mro/app/services/data_discovery/job_enqueue.py` | no | no | no (lifespan) | — |
| Dequeue (consumer): claim + `execute_one_shot_run` | api | `flynapse_api/automations/one_shot.py:148` | **no** | **no** | **no** | **the queue has no producer span, no consumer span and no link between them.** `flynapse_api/telemetry/run_span.py:8-10` records the equivalent decision for the scheduled path: span kind is INTERNAL not CONSUMER, and "No `Link` to a scheduling span yet". Queue depth, queue wait and claim contention have no signal of any kind |

### E. Startup and shutdown

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Gateway startup (RLS check, Weaviate partition check, RBAC seed, flag check, two enqueuer installs, scheduler start, improvement timer start) | api | `flynapse_api/main.py:78-223` | **no span anywhere in the hook** | **no** | **no** — every line, including the two `logger.error` paths for a failed RBAC seed and a failed scheduler start, emits outside any span | **the gateway's entire boot sequence is untraced.** Contrast the mounted app below, which spans the same class of work |
| Gateway shutdown (scheduler stop, timer stop, save drain, capture drain, upload drain, telemetry flush) | api | `flynapse_api/main.py:226-315` | **no span** | **no** | **no** | the "Draining…" / "outlived its bound" lines the bounded shutdown exists to produce (`:298`) are uncorrelated; the flush itself is correct and bounded (`:312`, `shutdown_budget.py:75`) |
| copilot-mro standalone startup | copilot-mro | `copilot_mro/app/main.py:102` (`mro.lifecycle.startup`) | **yes** — INTERNAL, `lifecycle.phase`, `operation.outcome`, `lifecycle.degraded_components`, `lifecycle.failed_component` | **no** | **yes** | **never runs under the gateway** — Starlette gives a mounted sub-app no lifespan, which is exactly why `main.py:78-223` re-declares the same steps untraced |
| copilot-mro standalone shutdown | copilot-mro | `copilot_mro/app/main.py:235` (`mro.lifecycle.shutdown`) | yes | no | yes | same: dead code in the served deployment; **and it never calls `shutdown_telemetry`**, unlike the gateway's hook |
| core standalone startup (RLS check + RBAC seed) | core | `core/fastapi_app.py:96` | **no** | **no** | **no** (no sinks installed — §A last row) | — |
| Automations worker startup | api | `flynapse_api/automations/worker.py:414` | **no** | **no** | yes (sinks installed at `:469`, but no span is current) | — |
| Automations worker shutdown | api | `flynapse_api/automations/worker.py:478` (`finally: _close_database()`) | no | no | no | **no `shutdown_telemetry` call** (see §B) |
| Telemetry bootstrap itself | utils / flynapse-otel | `utils/logging_config.py:59-80` | n/a | n/a | one "Telemetry configured" INFO line after the sinks exist | bootstrap's own degradations (missing / failing instrumentor) are stdlib WARNINGs (`flynapse_otel/bootstrap.py:324,334`) — visible, but **no counter**, so a silently-missing instrumentor in production is log-only |
| Telemetry shutdown | flynapse-otel | `flynapse_otel/bootstrap.py:251` | n/a | n/a | WARNING on failure / timeout (`:294,305`) | no metric for a timed-out flush |

### F. Repos that contribute nothing of their own

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| **All of `core`'s application code** | core | `core-obsm/core/**` | **no — zero `start_as_current_span` / `start_span` call sites in the whole package** | **no — zero `registry.*` instruments, zero `get_meter`/`create_*` call sites in the whole package** | **yes when mounted** (the gateway's sinks + span), **no when standalone** (no `setup_logging` call site exists in the package) | `core` is the largest application surface in the estate — RBAC, users, tenants, documents, comments, notifications, invitations, analytics, automations store, the telemetry ingest itself — and it emits **no span and no metric of its own from anywhere.** Everything it has is inherited from whichever process mounts it. Verified by grepping the whole `core/` package for `opentelemetry`, `observability`, `registry.`, `get_tracer`, `get_meter`: the only five hits are the words "registry" and "trace" in prose comments |
| `utils` as a library | utils | `utils-obsm/utils/**` | **two explicit spans total** — `s3.download` (`s3_service.py:226`) and `weaviate.hybrid_search` (`weaviate_service.py:1011`) | **zero `registry.*` instruments of its own**; it emits legacy-shim metrics from `llm.py` only | n/a (library) | `utils` owns Postgres, S3, Weaviate, Redis, Bedrock, embeddings, SES and SMTP, and hand-instruments two operations |
| `api` gateway package | api | `api-obsm/flynapse_api/**` | HTTP server span + `automation.run` | **one metric of its own: `auth.rejections`** | yes | the request metrics are the auto-instrumentor's, not the repo's |

### G. Satellites — dashboard (PRE-MERGE; merged state unresolved)

All rows are from `/home/aditya/Code/dashboard` @ `4a2898bd`. `dashboard-obsm` is mid-merge under another agent and was not read.

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Next.js route handlers, all 12 under `app/api/**` (comments ×4, document-hub content-stream, documents ×4, tenant ×2, workorders export) | dashboard | `lib/telemetry/server-route.ts:32` (`withRoute`); e.g. `app/api/comments/route.ts:184` | **no** — `withRoute` enters an `AsyncLocalStorage` request context and creates **no span** | **no** | **yes** — every `logger.*` line carries `trace_id` + route template + method (`lib/telemetry/server-log.ts:62-85`) | **the Next server hop is a trace-id relay, not a traced hop.** The trace has a hole between the browser CLIENT span and the backend SERVER span on every route-handler path |
| `GET /health` (Next) | dashboard | `app/health/route.ts:3` | **no** | **no** | **no** — bare handler, no `withRoute`, no logger | fully uninstrumented; it sits under `app/` not `app/api/`, so the sweep guard (`tests/unit/telemetry/server-routes-wrapped.test.ts:15`) does not see it |
| Edge middleware (auth bounce, token clear, password-param strip) | dashboard | `middleware.ts:6`, matcher `:95-106` | **no** | **no** | **no** — zero telemetry imports | every auth redirect is invisible |
| `instrumentation.ts` `register()` | dashboard | `instrumentation.ts:21-26` | **no** | **no** | installs the server log sink only | **the Next OTel hook exists but starts no Node SDK.** No `@vercel/otel`, no `NODE_OPTIONS` preload, no `OTEL_*` env in `.env.example` / `amplify.yml` / `Dockerfile` / `compose.yaml` |
| `instrumentation.ts` `onRequestError` | dashboard | `instrumentation.ts:28-33` → `lib/telemetry/server-log.ts:120` | no | no | **yes** — `trace_id` parsed from the inbound `traceparent` | the line reaches `process.stderr` only; **nothing exports server logs** |
| Browser `fetch` / XHR to the backend | dashboard | `lib/telemetry/provider.ts:238-262` | **yes** — CLIENT spans via `@opentelemetry/instrumentation-fetch` / `-xml-http-request` | **no** | n/a | 10% export-time drop of **root CLIENT** spans by trace id (`lib/telemetry/sampling.ts:32,72-81`); errors, 5xx, children and non-CLIENT spans always kept |
| W3C `traceparent` propagation (browser) | dashboard | `lib/telemetry/provider.ts:307,232`; allow-list `:113-119` | — | — | — | **it does propagate**, cross-origin allow-listed to the API gateway origin only; **no `baggage`**, matching the estate's no-outbound-baggage invariant |
| `POST /chats/rag/stream` from the browser | dashboard | `lib/api/client.ts:170,187`; parented at `hooks/chat/streamingHelpers.ts:252` | **yes** — instrumented `fetch` CLIENT span, child of `browser.chat.turn`; **not** `EventSource` | no | n/a | whether the span ends at headers or at stream completion is unverified without a live run |
| Browser document load | dashboard | `lib/telemetry/provider.ts:263` | yes | no | n/a | — |
| Chat turn (user-facing unit of work) | dashboard | `lib/telemetry/chat-turn.ts:60` (`browser.chat.turn`) | **yes** — INTERNAL, with `ttf_init_ms`, `ttf_token_ms`, `total_ms`, `step_count`, `outcome` | **no** — the durations are span attributes, not instruments | n/a | percentiles must be derived from spans |
| Web Vitals (LCP/INP/CLS/FCP/TTFB) | dashboard | `lib/telemetry/web-vitals.ts:40-48` | no | **no — these are OTel LOG RECORDS (`browser.web_vital`) with numeric attributes, not metrics** | ambient context only | — |
| Browser log records (`warn`/`error`/`fatal`) | dashboard | `lib/telemetry/logger.ts:102-130` | no | no | **yes, conditionally** — `ship()` re-enters the failed request's trace via a stamped `traceId` | `debug`/`info` never ship |
| Browser error capture (4 global sources) | dashboard | `lib/telemetry/errors.ts:192-194`; `app/global-error.tsx:32` | no | no | **yes** — the support reference handed to the user *is* the trace id | — |
| Browser telemetry export | dashboard | `lib/telemetry/exporter.ts:98-102` | n/a | n/a | n/a | bespoke OTLP/JSON exporter, **traces + logs only — no `@opentelemetry/sdk-metrics` in `package.json` at all, and no `/v1/metrics` route** |
| Browser telemetry drop counter | dashboard | `lib/telemetry/provider.ts:148-154` (`browser.telemetry.dropped`) | no | **no — a log record, not a counter** | no | telemetry self-observability is itself log-shaped |
| Product analytics (6 facts → `POST /analytics/events`) | dashboard | `lib/telemetry/product-events.ts:32-39,256` | no | no | **no trace context at all** | **a separate analytics pipeline, not OTel** — zod-validated, batched, excluded from fetch instrumentation (`provider.ts:233`). No PostHog/GA/GTM/Segment/Sentry/Datadog anywhere in dashboard source |
| Node server startup / shutdown | dashboard | `Dockerfile:63`, `amplify.yml` | **no** | **no** | log sink only | no Node OTel SDK, **no SIGTERM flush hook** |
| Cron routes / webhooks / background jobs / server actions / `pages/api` | dashboard | — | n/a | n/a | n/a | **none exist in dashboard** — App Router only, no `vercel.json`, no edge runtime outside `middleware.ts`, zero `'use server'` |

Cross-check I can add from the backend side: the two backend endpoints the dashboard posts to **do exist** — `core/resources/logging/logging_endpoints.py:325-344` (OTLP ingest) and `core/resources/analytics/events_endpoints.py:67` (`POST /analytics/events`).

### H. Satellites — telegram-bot and shift-optimizer

**telegram-bot bootstraps differently from every other Python process in the estate.** It goes straight to `flynapse_otel` and never touches `utils.observability` (`telegram_bot/telemetry.py:66-68`), bootstraps at `telemetry.py:208` from `app.py:1335`, and declares only **three** instrumentors — `("httpx", "psycopg", "threading")` (`telemetry.py:121`). **It does not declare `urllib3`**, so the botocore→urllib3 fallback that covers every AWS call in the api-side processes **does not apply here**: telegram-bot's Cognito calls are genuinely unspanned. It has **no loguru at all**; its log route is stdlib `logging.basicConfig` (`app.py:466`) plus `flynapse_otel.logging.attach_stdlib_logging` (`telemetry.py:363`), and correlation works by the same rule (SDK `LoggingHandler` stamps the ambient context at emit). It **does** flush on exit — `shutdown_telemetry(5.0)` at `app.py:1228`.

**shift-optimizer bootstraps nothing.** There is no `bootstrap(...)` or `setup_logging(...)` call anywhere in its production code; the only one in the tree is `tests/unit/telemetry/conftest.py:43`. It consumes `utils.observability.registry` / `.tracing` (`app/services/run_telemetry.py:26-27`) and nothing else, and it has no Dockerfile, no compose file and no uvicorn invocation. **Its signals exist only because the api gateway hosts it:** `api-obsm/flynapse_api/routers/optimizer.py:10` imports `shift_optimizer.app.main` from inside the gateway process, and the gateway's `setup_logging()` has already run at `api-obsm/flynapse_api/main.py:8` — so in the mounted runtime the bootstrap, both sinks and the six instrumentors are all in place. That resolves the host-dependency: **mounted = instrumented; standalone = nothing.**

| Boundary | repo | file:line | span? | metric? | trace-correlated log? | gap |
|---|---|---|---|---|---|---|
| Process startup / bootstrap | telegram-bot | `telegram_bot/app.py:1325`, `:1335` → `telemetry.py:208` | **no** | **no** | **no** — "bot schema ready" (`app.py:1367`), "polling…" (`app.py:1416`) emit outside any span | no startup span or metric in telegram-bot |
| Startup schema DDL + storage reconciliation | telegram-bot | `app.py:1356-1362` (`db.bootstrap`), `app.py:1394` (`_reconcile_storage`) | **yes** — psycopg auto-instrumentor, but as parentless roots | **yes** — `db.client.operation.duration` | **no** — the repair lines (`app.py:1185-1194`) sit outside any span | repair outcome uncorrelated in telegram-bot |
| Telegram long-poll `getUpdates` | telegram-bot | `app.py:1417`; exclusion `telemetry.py:173`, set `:206` | **no — deliberately excluded** via `OTEL_PYTHON_HTTPX_EXCLUDED_URLS=.*/getUpdates` | **no** | **no** — httpx logger pinned to WARNING (`app.py:467`) | intentional; the consequence is the poll loop's health has no signal |
| Telegram update dispatch (**polling, not webhook**) | telegram-bot | `telegram_bot/telemetry.py:633` (`telegram.update`, CONSUMER), wired `app.py:663` | **yes** | **yes** — `telegram.updates` (`:649`), `telegram.updates.active` (`:631`/`:648`) | **yes** — every handler line nests inside | — |
| Update failure path / error handler | telegram-bot | `telemetry.py:651`, `app.py:619` | yes (exception + ERROR status) | yes — `telegram.updates{outcome="error"}` | yes | — |
| Copilot turn (chat lane) | telegram-bot | `handlers/chat.py:2060` → `telemetry.py:709` (`telegram.turn`) + children `telegram.turn.{gate,auth,backend,render}` (`:767`) | yes | yes — `telegram.turn.duration` (`:796`), `telegram.turn.phase.duration` (`:799`), `telegram.turn.cost` (`:801`), `telegram.turns` (`chat.py:2484`) | yes | — |
| Photo tail of a turn | telegram-bot | `handlers/chat.py:2301` → `telemetry.py:743` (`telegram.turn.photos`) | yes | yes — `telegram.turn.phase.duration{phase="photos"}` | yes | — |
| Upload door (manual PDFs) | telegram-bot | `handlers/uploads.py:1792`; refusals `:1454,:1779,:1969,:2617` | yes (inherited `telegram.update`) | yes — `telegram.uploads`, `telegram.refusals` | yes | no upload-duration histogram in telegram-bot |
| Invite redemption → provisioning door | telegram-bot | `handlers/invites.py:400,409`; refusals `:358,:372,:376` | yes (inherited; outbound leg spanned by httpx) | yes — `telegram.provisionings`, `telegram.refusals` | yes | no provisioning-latency metric in telegram-bot |
| Stale-update gate, maintenance kill-switch, group-chat gate | telegram-bot | `app.py:817`, `:898`, `:998` | yes (inherited) | yes — `telegram.refusals{reason=…}` | yes | — |
| Fastlane / weather lane | telegram-bot | `handlers/fastlane.py:417` | yes (inherited) — **no span of its own** | **refusal-only** — `telegram.refusals{reason=quota}`; no success counter | yes | no per-lane span; the lane's success path is unmeasured |
| Media / captioned-photo door | telegram-bot | `handlers/media.py:195` | yes (inherited) — no own span | refusal-only | yes | success path unmeasured |
| Library / manuals door | telegram-bot | `handlers/manuals.py:822` | yes (inherited) — no own span | refusal-only | yes | success path unmeasured |
| Salary door | telegram-bot | `handlers/salary.py:1459` | yes (inherited) — no own span | refusal-only | yes | success path unmeasured |
| Subscription / billing door (incl. pre-checkout) | telegram-bot | `handlers/subscription.py:447,569` | yes (inherited) — no own span | refusal-only | yes | **no payment-success counter** in telegram-bot |
| Weekly digest job — scheduled tick | telegram-bot | `handlers/digest.py:631` → `telemetry.py:823` (`telegram.job`, root) | yes | yes — `telegram.jobs{name="digest"}` | yes | no per-recipient send metric |
| Weekly digest job — startup catch-up | telegram-bot | `handlers/digest.py:616` → `telemetry.py:823` | yes | yes | yes | **second entrypoint to the same boundary, instrumented identically** |
| Document-watch poll job | telegram-bot | `handlers/document_watch.py:492`; armed `uploads.py:2322` | yes — `telegram.job{name="document_watch"}` | yes — `telegram.jobs` | yes | no poll-count or poll-latency metric |
| Outbound → api.telegram.org | telegram-bot | PTB httpx transport; instrumentor `telemetry.py:121`; URL redaction `telemetry.py:323-340` | yes — httpx auto | **no** — telegram-bot configures no meter provider for httpx metrics | yes | no outbound HTTP duration metric in telegram-bot |
| Outbound → copilot backend (SSE chat, files, dochub, flight-ops) | telegram-bot | `flynapse_client/client.py:70`, `flynapse_client/chat.py:31` | yes — httpx auto, nested under `telegram.turn.backend` | **no** | yes | no client-side error counter in telegram-bot |
| Outbound → presigned S3 GET | telegram-bot | `flynapse_client/dochub.py:203` | yes — httpx auto, query redacted | **no** | yes | — |
| Outbound → RSS/digest feeds | telegram-bot | `telegram_bot/digest.py:860` | yes — httpx auto, nested under `telegram.job` | **no** | yes | — |
| Outbound → satellite imagery hosts | telegram-bot | `telegram_bot/satellite.py:342` | yes — httpx auto | **no** | yes | — |
| **AWS Cognito (boto3) — login + refresh** | telegram-bot | `flynapse_client/auth.py:44,109`; driven via `asyncio.to_thread` from `identity.py:256,260` | **no** — no botocore instrumentor, and **`urllib3` is not declared in telegram-bot** (`telemetry.py:121`), so the fallback that covers AWS calls in the api-side processes does not apply here | **no** | yes (lines inside the turn are correlated; the call itself is invisible) | **genuinely dark AWS boundary in telegram-bot** — login latency disappears inside `telegram.turn.auth` |
| Postgres (bot store, pooled + unpooled) | telegram-bot | pool `app.py:1395`; call sites across `state.py`, `quotas.py`, `handlers/goodbye.py`, via `asyncio.to_thread` | yes — `psycopg` (v3) auto; context carried by the `threading` instrumentor | yes — `db.client.operation.duration` | yes | no pool-saturation instrument |
| Queue | telegram-bot | PTB in-process update queue only | n/a | n/a | n/a | **no Redis, SQS, Celery or broker in telegram-bot** |
| Process shutdown / flush | telegram-bot | `app.py:1228` → `telemetry.py:239` | **no** | **no** | **no** — the confirmation line (`telemetry.py:255`) is written after the OTLP handler has closed, stdout only | flush itself is correct and bounded; no shutdown span or metric |
| CLI: `mint_invites` | telegram-bot | `telegram_bot/mint_invites.py:155` | **no** | **no** | **no** | **no telemetry at all** — no bootstrap, so its psycopg calls are uninstrumented too |
| CLI: `seed_salary` | telegram-bot | `telegram_bot/seed_salary.py:135` | **no** | **no** | **no** | same |
| HTTP routes — all 36 (health, schedules, activities, roles, settings, duration-query, jobs, runs, export, network), **mounted runtime** | shift-optimizer | `shift_optimizer/app/main.py:49-58`; instrumented by `api-obsm/flynapse_api/telemetry/http_server.py:269` | **yes** — the gateway's SERVER span; **nothing in the shift-optimizer tree creates one** | **yes** — the gateway's `http.server.request.duration`; **no route metric in shift-optimizer** | **yes** — the gateway installed the sinks at `api-obsm/flynapse_api/main.py:8` before importing the sub-app | all HTTP coverage is borrowed |
| HTTP routes — **standalone runtime** (`uvicorn shift_optimizer.app.main:app`) | shift-optimizer | `shift_optimizer/app/main.py:37` | **no** | **no** | **no** | **second runtime, wholly dark.** No bootstrap, no sinks, no ASGI instrumentation anywhere in the repo |
| Run enqueue `POST /jobs/{job_id}/run` | shift-optimizer | `app/api/jobs.py:315-341`; link captured `:341` → `run_telemetry.py:209` | yes (gateway SERVER span) | **no** — no "runs enqueued" counter, only the terminal `optimizer.runs` | yes | queue-wait invisible |
| Background run execution (`BackgroundTask`) | shift-optimizer | `app/services/run_executor.py:173,192` → `run_telemetry.py:195` (`optimizer.run`) | **yes** — INTERNAL, fresh trace root **with a `Link`** to the request span | **yes** — `optimizer.runs`, `optimizer.run.duration`, `optimizer.runs.active` | **yes** — `logger.bind` (`run_telemetry.py:107`) + `contextualize(run_id=…)` (`:203`) | the run trace is disjoint from the request trace by design (`run_telemetry.py:3-7`). **This is the one background boundary in the estate that carries a `Link`** — the automations path does not |
| CP-SAT solve phase | shift-optimizer | `run_executor.py:488` → `run_telemetry.py:131` (`optimizer.solve`) | yes | yes — `optimizer.solve.duration` (`:145`) | yes | **a solve that raises records no duration sample** — the `record` is after the `yield` (`run_telemetry.py:137-145`) |
| Run output persist phase | shift-optimizer | `run_executor.py:229` → `run_telemetry.py:150` (`optimizer.persist`) | yes | **no** | yes | no persist-duration metric |
| Run failure path | shift-optimizer | `run_executor.py:275` → `run_telemetry.py:155` | yes (exception + ERROR + `error.type`) | yes — `optimizer.runs{status="failed"}` | yes (type only, by design) | — |
| Run row not visible under executing identity | shift-optimizer | `run_executor.py:202` → `run_telemetry.py:164-168` | yes (ERROR on `optimizer.run`) | **no — deliberately no counter** (`run_telemetry.py:164-166`) | yes | **a stuck-pending run is invisible to metrics** in shift-optimizer |
| Postgres (all optimizer CRUD) | shift-optimizer | `app/db/repository.py` → `app/db/postgres.py:27` → `utils.postgres_service` | yes — psycopg2 auto, declared by the **host** | **yes** — `db.client.operation.duration` | yes | **correction to the satellite audit:** it reported no DB metric; I verified the dbapi instrumentor does create and record `db.client.operation.duration` (`instrumentation/dbapi/__init__.py:522,886`). Nothing in shift-optimizer declares the instrumentor — the gateway does |
| Excel export render | shift-optimizer | `app/api/export.py:45` → `app/services/excel_export.py` | **no** | **no** | **no** — no log line on the path | workbook rendering is unmeasured in shift-optimizer |
| Lifespan startup (standalone only) | shift-optimizer | `app/main.py:22-35`, RLS check `:33` | **no** | **no** | **no** | and under the gateway this lifespan does not run at all (mounted sub-apps get none) |
| Process shutdown / flush | shift-optimizer | — | **no** | **no** | **no** | **no shutdown or flush call anywhere in shift-optimizer**; the lifespan has no post-`yield` teardown. Under the gateway the gateway's flush covers it |
| Seed path that executes a run in-process | shift-optimizer | `app/db/seed.py:494`, lazy import `:476` | yes — the same `optimizer.run`/`solve`/`persist` spans, but **unlinked** (no `link_context`) | yes — same four instruments | only if the calling process bootstrapped | **second entrypoint to the run boundary, instrumented differently:** no request link, and against no-op providers it emits nothing |
| CLI: historical-run backfill | shift-optimizer | `scripts/backfill_historical_runs.py:28`; work in `app/db/backfills.py:142,147,203,213` | **no** | **no** | **no** — loguru lines with no bootstrap and no active span | **second entrypoint to the same tables, entirely uninstrumented** |
| CLI: GHA seed derivation | shift-optimizer | `scripts/derive_gha_seed.py:333` | **no** | **no** | **no** | — |
| S3 / boto3 / Bedrock / LLM providers / Weaviate / Redis / queues | shift-optimizer | — | n/a | n/a | n/a | **none of these exist in shift-optimizer** — verified by grep over `shift_optimizer/` and `scripts/` |

---

## Summary counts

**Counting rule, stated so the numbers can be re-derived:** one row = one boundary. **Fully covered** = all three columns yes. **Partly covered** = one or two. **Uninstrumented** = none of the three. Rows marked `n/a` throughout are excluded: the `X-Trace-Id` header, the request-identity attribute row, the two telemetry bootstrap/shutdown mechanism rows, the `traceparent`-propagation and exporter rows, the §F repo-level summary rows, and every "none of these exist in this repo" row.

| Section | Boundaries | Fully covered | Partly covered | Uninstrumented |
|---|---:|---:|---:|---:|
| A — HTTP routes & mounted sub-apps | 21 | 14 | 2 | 5 |
| B — Background jobs & schedulers | 18 | **0** | 10 | 8 |
| C — External clients | 23 | 16 | 5 | 2 |
| D — Queues | 4 | **0** | 1 | 3 |
| E — Startup & shutdown | 7 | **0** | 3 | 4 |
| G — dashboard (pre-merge) | 15 | **0** | 9 | 6 |
| H — telegram-bot | 28 | 11 | 12 | 5 |
| H — shift-optimizer | 15 | 5 | 4 | 6 |
| **Total** | **131** | **46** | **46** | **39** |

**A qualifier on the 46 "fully covered".** In §C, **8 of the 16** fully-covered external-client rows are fully covered only because of the urllib3/httpx HTTP fallback: Weaviate object CRUD, Weaviate health check, every S3 operation except `download_pdf`, the legacy `recorded_llm_call` span, the embeddings span, Cognito, SES and DynamoDB. Those boundaries appear in a trace as an anonymous outbound HTTPS call with no `rpc.*`, no `db.*`, no `gen_ai.*` and no bucket/key/table/model identity. Counting by the three columns says covered; counting by "can an operator tell which dependency this was" says not.

**Worst-covered boundary kinds, by the numbers:**

1. **Queues — 0 of 4 fully covered.** The estate has no message broker; the durable queue is the `automation_runs` table. There is no producer span, no consumer span, no link between them, and no metric of any kind. Queue depth, queue wait and claim contention have no signal.
2. **Startup & shutdown — 0 of 7 fully covered**, 4 of 7 wholly uninstrumented. The gateway's entire boot and drain sequence is untraced; the only lifecycle spans in the estate (`mro.lifecycle.startup` / `.shutdown`) belong to a runtime that never runs in the served deployment.
3. **Background jobs & schedulers — 0 of 18 fully covered.** Not one background boundary in the four core repos emits a metric. Ten have a span and a correlated log; eight have neither.
4. **dashboard — 0 of 15 fully covered**, and structurally so: there is **no `@opentelemetry/sdk-metrics` in dashboard's `package.json` at all**, so no dashboard boundary can emit a metric. Every timing in that app is a span attribute or a log-record attribute.

**Best-covered boundary kinds:** HTTP routes under the gateway (14 of 21 fully covered, all from one middleware) and the agent/LLM path in copilot-mro (the only place in the estate where a boundary carries semconv-shaped spans *and* purpose-built metrics *and* correlated logs).

---

## Appendix — noticed in passing, for R.4

**Not orphan analysis.** No dashboard or alert file was opened. These are producer-side names R.4 will want to match against consumers, plus three things that looked orphan-shaped from the code side.

**Metric names produced by the estate (the full producer-side inventory):**

- api: `auth.rejections`
- copilot-mro (explicit registry): `agent.turn.calls`, `agent.turn.duration_seconds`, `gen_ai.client.operation.duration`, `gen_ai.client.token.usage`, `agent.model.calls`, `agent.model.cost_usd`, `agent.model.unpriced_calls`, `agent.tool.calls`, `agent.tool.attempts`, `agent.subagent.calls`, `agent.subagent.duration_seconds` — note `agent_shared/telemetry.py` has **two** construction paths for the same eleven names, a `meter.create_*` path (`:1362-1388`) and a `registry.*` path (`:1401-1455`); the registry path pins units, the meter path does not
- copilot-mro (legacy shim): `chat_block_save_failures_total`, `memory_get_latency_ms`, `memory_search_latency_ms`
- utils (legacy shim): `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request`, `embedding_requests_total`, `embedding_tokens_total`, `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`, `embedding_cache_tokens_avoided_total`
- telegram-bot (via `flynapse_otel.registry`, declared `telegram_bot/telemetry.py:856-893`): `telegram.updates`, `telegram.updates.active`, `telegram.turn.duration`, `telegram.turn.phase.duration`, `telegram.turn.cost`, `telegram.jobs`, `telegram.turns`, `telegram.uploads`, `telegram.provisionings`, `telegram.refusals` — **and the list is open-ended by construction**: `counted` (`telemetry.py:896-903`) auto-registers `telegram.<name>` for any new `counter=` value a handler passes, so a new series can appear without a code change here
- shift-optimizer (via `utils.observability.registry`, declared `app/services/run_telemetry.py:51-68`): `optimizer.runs`, `optimizer.run.duration`, `optimizer.solve.duration`, `optimizer.runs.active` — attribute keys hard-limited to `{status, solve_status}` (`run_telemetry.py:41`, enforced `:72-79`)
- auto-instrumentors: `http.server.request.duration`, `http.server.duration` (old semconv), `http.server.active_requests`, `http.client.request.duration`, `http.client.request.body.size`, `http.client.response.body.size`, `db.client.operation.duration`
- core: **none**
- dashboard: **none** (no metrics SDK)

**Span names produced by the estate:**

- api: `automation.run`; plus the ASGI middleware's `<METHOD> <route>` server spans
- copilot-mro: `mro.lifecycle.startup`, `mro.lifecycle.shutdown`, `chat.enhanced_chat`, `chat.enhanced_chat_stream`, `rag.pipeline.execute`, `db.chat.save_block`, `invoke_agent <runtime>`, `execute_tool <name>`, `agent_sdk.tool.<short>`, `document_hub.process`, `document_hub.cleanup`, `data_discovery.job.run`, `improvement.run`, `improvement.stage`, `memory.items.get_by_ids`, the memory-index operation span, `ingest.parse`
- utils: `s3.download`, `weaviate.hybrid_search`
- telegram-bot: `telegram.update` (CONSUMER), `telegram.turn`, `telegram.turn.{gate,auth,backend,render}`, `telegram.turn.photos`, `telegram.job` (with a `telegram.job.name` attribute)
- shift-optimizer: `optimizer.run`, `optimizer.solve`, `optimizer.persist`
- dashboard (browser): `browser.chat.turn` plus auto fetch/XHR/document-load spans
- core: **none**

**Dashboard-side names a Grafana panel or alert might reference** (pre-merge tree; all are OTel **log-record event names**, not metrics, unless noted): `browser.web_vital`, `browser.error`, `browser.log`, `browser.telemetry.dropped`, `browser.app.boot`, `browser.route.change`, `browser.auth.login`, `browser.pdf.render`, `browser.upload.started`, `browser.automation.run_triggered`, `browser.discovery.job_started`, `browser.settings.mutation`, `browser.chat.feedback_submitted`, `browser.feature.mutation`, `browser.auth.flow`, `browser.automation.run_settled`, `browser.discovery.job_settled`, `browser.export.requested`, `browser.optimizer.run_triggered`, `browser.ad_review.disposition_set` (`lib/telemetry/events.ts:29-52`); span name `browser.chat.turn` (`:55`); web-vital values `LCP`/`INP`/`CLS`/`FCP`/`TTFB` (`:271`). Product-analytics event names (separate pipeline): `document_opened`, `document_closed`, `session_started`, `session_ended`, `clarification_answered`, `upload_finished`. Numeric span/log attributes a panel would aggregate: `ttf_init_ms`, `ttf_token_ms`, `total_ms`, `step_count`, `attachment_upload_ms`, `dom_interactive_ms`, `dom_content_loaded_ms`, `load_complete_ms`, `ttfb_ms`, `change_ms`, `ready_ms`, `duration_ms`.

**Resource identifiers in play:** `service.namespace='flynapse'`; service names `api`, `mro-copilot` (from `settings.otel_service_name`), `automation-scheduler` (the worker's `SERVICE_NAME`), `ingest-parser` (every parser CLI), `data-discovery-job`, `telegram-bot` (`telegram_bot/telemetry.py:107`), `dashboard` (browser), `dashboard-server` (Next server log lines). **shift-optimizer has no service name of its own** — mounted, its spans carry the gateway's `api`.

**Deliberate exclusions a dashboard/alert must know about, or it will alert on a hole:** `/health/live`, `/health/ready`, every mounted sub-app's `/v1/health`, and the four browser OTLP ingest routes are all excluded from the gateway's spans and request metrics (`api-obsm/flynapse_api/telemetry/http_server.py:56,58,64`). Telegram's `getUpdates` long-poll is excluded from httpx spans (`telegram_bot/telemetry.py:173,206`). The dashboard drops 10% of **root CLIENT** spans at export time by trace id (`lib/telemetry/sampling.ts:32,72-81`). None of these will ever produce a series.

**Three things that looked orphan-shaped from the producer side** — recorded only, not investigated:

1. **Collector span-metrics dimensions are load-bearing for two panels.** `utils/s3_service.py:216-219` and `utils/weaviate_service.py:1003-1006` both carry comments saying `server.address` exists because the collector's span-metrics connector promotes it, and that without it the "Client call rate by dependency" panel buckets everything under an empty label and the "DB client p95 by system" panel drops S3 entirely. R.4 should check whether those two panels still exist and still filter that way — and note that **only the two spanned operations carry `server.address` at all**, so those panels can only ever see `s3.download` and `weaviate.hybrid_search`.
2. **Two metric vocabularies for the LLM boundary.** The legacy `llm_*` / `embedding_*` names and the semconv `gen_ai.*` / `agent.*` names both ship today from the same estate. A panel written against either one sees a partial picture.
3. **`agent_shared/telemetry.py` builds the same eleven instruments twice**, once through `meter.create_*` (units unset) and once through `registry.*` (units pinned). Which path a given process takes decides whether the series carries a unit.
4. **telegram-bot's counter namespace is open-ended.** `telemetry.py:896-903` registers `telegram.<name>` on first use for any `counter=` value a handler passes, so the set of live `telegram.*` series is not fully enumerable from the declaration block — R.4 should enumerate the `count(...)` call sites, not just `telemetry.py:856-893`.
5. **`shift-optimizer` deliberately emits no counter for a run that is invisible under the executing identity** (`run_telemetry.py:164-166`), so a class of stuck-pending run can never trip a metric-based alert. And `optimizer.solve.duration` is recorded after the `yield` (`run_telemetry.py:137-145`), so a solve that raises contributes no sample — a solver crash loop would *lower* the observed p95.

---

## What could not be determined without running the system

1. **Whether the OTLP collector actually receives anything from any of these processes.** Every judgement here is about what the code emits into the SDK, not about export success. `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SDK_DISABLED` and `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` are all read at runtime, and any of them can silence a boundary this document marks "yes".
2. **Which instrumentors actually applied in each deployed process.** `_apply_instrumentations` degrades to a WARNING on a missing package or a failed `.instrument()` (`flynapse_otel/bootstrap.py:317-341`) and there is no counter for it — so a process running without, say, the psycopg2 instrumentor would show as fully covered in this table and be dark in reality. The only way to know is `bootstrap.state().instrumentations` at runtime or the "Telemetry configured" log line.
3. **Whether `AUTOMATION_SCHEDULER_MODE` is `embedded`, `worker` or `off` in any environment.** That decides which of the two automations rows is the live one; `off` is the default and makes both inert.
4. **Whether copilot-mro and core are ever served standalone.** The "second runtime" rows are real code paths, but whether any deployment uses them is a deployment fact, not a code fact. If they are mount-only, those rows are dead code rather than live gaps.
5. **Whether the Lambda parser path is deployed.** `lambda_functions/s3_pdf_processor_lambda.py` is uninstrumented; whether it runs is an infrastructure question.
6. **Actual span parentage across `asyncio.to_thread` / `create_task` boundaries.** contextvars propagation says the parent should be carried, but the background S3 PUT and the background chat-block save both start after their request span has ended, so what the trace actually looks like needs a live run.
7. **Whether `traceparent` survives the network path** browser → CloudFront/Amplify/ALB → gateway. Nothing in any repo configures or asserts that, and it decides whether the dashboard's CLIENT spans and the gateway's SERVER spans are in one trace at all.
8. **SSE span duration semantics** for `/chats/rag/stream` — whether the browser's fetch CLIENT span ends at response headers or at stream completion.
9. **Whether telegram-bot's OTLP route is live in any deployment.** `telegram-bot/.env.sample:134` ships `OTEL_SDK_DISABLED=true` as the documented local default; under it `configure_telemetry` returns at `telemetry.py:219` and **every telegram-bot span, metric and log export above is a no-op**. Which value production carries is deployment config, not a tree fact.
10. **Whether shift-optimizer is ever served standalone.** If it is, everything in its §H block collapses to the "standalone runtime, wholly dark" row. The repo has no Dockerfile, no compose file and no uvicorn invocation, and its own docstring (`app/main.py:25-27`) says it runs mounted — which is evidence, not proof.
11. **Whether shift-optimizer's Postgres queries are traced at first use.** `utils/postgres_service.py:151-154` returns an *uncached* untraced `RealDictCursor` when the instrumentor has not been applied yet, so tracing depends on bootstrap-vs-first-query ordering in the host process. Not decidable statically.
12. **Whether the `threading` instrumentor actually carries context across every `asyncio.to_thread` hop** in telegram-bot and in copilot-mro's background saves. Asserted in-code and covered by unit tests, not verifiable without a run.
