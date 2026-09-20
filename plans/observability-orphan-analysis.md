# Task R.4 — orphan analysis (both directions) + attribute & cardinality compliance

Read-only audit. Nothing was written outside this scratchpad; no tree was modified.

## 0. What I read, and when

| Tree | Path | HEAD at read time | Working tree |
|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` @ `d8d2570c` | **21 files modified, uncommitted** — I read the working tree |
| api | `/home/aditya/Code/api-obsm` | `obs-merge` @ `9812f44` | clean except untracked `tests/unit/api_surface/` |
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` @ `e6b464e` | clean |
| core | `/home/aditya/Code/core-obsm` | `obs-merge` @ `d7f7b54` | clean |
| dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` @ `3afd524` | **4 untracked files — a third implementer is active** (see §5, item 15) |
| iac | `/home/aditya/Code/iac` | `obs-merge` @ `2d493c8` | clean (untracked `__pycache__` + a POC shell script only) |
| telegram-bot / shift-optimizer / flynapse-otel | `main` | — | clean |

**Moving-target caveat.** Every file under `copilot-mro-obsm/deployment/`, `docs/runbooks/observability/`,
`deployment/otel/dashboards/CATALOGUE.md` and `tests/integration/otel/_emitted_series.py` is *currently
being edited*. My reads are a snapshot taken between 09:05 and 09:30 on 2026-09-20. Where a claim
differs between `HEAD` and the working tree I say which I am quoting.

**In-flight exclusions (per the brief).** Three signals are being wired right now by the copilot-mro
implementer. They are **excluded from the orphan verdict** and listed separately in §2b:
`agent.subagent.calls`, `agent.subagent.duration_seconds`, `agent.ledger.write_failures`.
I confirmed by diff that all three are uncommitted: `git diff` on `telemetry.py` (+36),
`agent_pipeline.py` (+17), `lang_agent/backend.py` (+16), `agent_claude/orchestrator.py` (+13),
`agent_shared/subagent_runs.py` (+52), `usage_ledger.py` (+53), `model_call_ledger.py` (+20).

---

## 1. Emitted-but-unconsumed

**Consumers searched (the complete set):** 8 Grafana boards (85 panels total) under
`copilot-mro-obsm/deployment/observability-local/grafana/provisioning/dashboards/flynapse/*.json` ·
4 Prometheus rule files (12 rules) under `.../rules/prometheus/` · 1 Loki rule file (5 rules) at
`.../rules/loki/flynapse/browser-alerts.yml` · 4 runbooks under
`copilot-mro-obsm/docs/runbooks/observability/` · 8 CloudWatch dashboard templates under
`iac/dashboards/*.json.tftpl` · `iac/alarms.tf` (13 PromQL alarms + 6 log-metric-filter alarms + 3
classic alarms).

Panel census (`grep -c '"gridPos"'`): agent-turn-explorer 3 · dependencies 5 · frontend 19 ·
llm-agents 12 · platform-health 9 · service-overview 7 · shift-optimizer 12 · telegram-bot 18 = **85**.

### 1a. Metrics

| Signal | Kind | Emitter (file:line) | Consumption | Verdict |
|---|---|---|---|---|
| `agent.turn.calls` | counter | `copilot-mro-obsm/copilot_mro/app/services/agent_shared/telemetry.py:1406` / recorder `:1819` | charted (fn-llm-agents p6), rule (`AgentTurnFailureRatioHigh` oss+aws), iac markdown ×2 | consumed |
| `agent.turn.duration_seconds` | histogram | same file `:1411` / `:1819` | charted (fn-llm-agents p7), iac markdown | consumed |
| `agent.model.calls` | counter | `telemetry.py:1427` / `:1842` | charted (fn-llm-agents p2) **oss only** | consumed (oss); **no AWS consumer** |
| `agent.model.cost_usd` | counter | `telemetry.py:1432` / `:1842` | charted, rule (`TenantDailySpendHigh` oss+aws), runbook | consumed |
| `agent.model.unpriced_calls` | counter | `telemetry.py:1437` / `:1842` | charted, rule (`UnpricedModelCalls` oss+aws), runbook | consumed |
| `gen_ai.client.token.usage` | histogram | `telemetry.py:1421` / `:1842` | charted (fn-llm-agents p1, p5), iac markdown | consumed |
| **`gen_ai.client.operation.duration`** | histogram | `telemetry.py:1416` / `:1842` (recorded whenever `usage.latency_seconds is not None`) | **none** — named only in `CATALOGUE.md:151`'s name-mapping table; no panel, no rule, no alarm, no runbook query | **ORPHAN** |
| `agent.tool.calls` | counter | `telemetry.py:1442` / `:1871` | charted (fn-llm-agents p8 target C) **oss only** | consumed (oss); **no AWS consumer** |
| `agent.tool.attempts` | counter | `telemetry.py:1447` / `:1871` | charted (p8 A+B), iac markdown | consumed |
| `auth.rejections` | counter | `api-obsm/flynapse_api/middleware/telemetry.py:34` / emit `:85` | charted (fn-service-overview p5), iac markdown | consumed |
| `http.server.request.duration` | histogram | auto-instr., `api-obsm/flynapse_api/telemetry/http_server.py` (`OTEL_SEMCONV_STABILITY_OPT_IN=http` defaulted at `flynapse-otel/flynapse_otel/bootstrap.py:171`) | charted ×8, rules `ApiHighErrorRate`/`ApiP95LatencyHigh` (oss+aws) | consumed |
| `http.server.active_requests` | up-down | same instrumentation | charted (fn-service-overview p4), iac markdown | consumed |
| `http.client.request.duration` | histogram | auto-instr. httpx/requests/urllib3 — verified present at `.venv/.../opentelemetry/instrumentation/httpx/__init__.py:792`, attrs incl. `SERVER_ADDRESS` | charted (fn-telegram-bot p13), iac markdown | consumed |
| `telegram.updates` | counter | `telegram-bot/telegram_bot/telemetry.py:856` / emit `:649` | charted (p1) | consumed |
| `telegram.updates.active` | up-down | `:859` / `:631,:648` | charted (p2), iac markdown | consumed |
| `telegram.turns` | counter | `:883` via `counted()` `:896` | charted ×5, rule `TelegramTurnFailureRate` (oss+aws) | consumed |
| `telegram.turn.duration` | histogram | `:862` / `:796` | charted (p6) | consumed |
| `telegram.turn.phase.duration` | histogram | `:868` / `:799` | charted (p7) | consumed |
| `telegram.turn.cost` | counter | `:874` / `:801` | charted (p8, p9) | consumed |
| `telegram.jobs` | counter | `:877` / `:842` | charted (p15) | consumed |
| `telegram.uploads` | counter | `:886` | charted (p11) | consumed |
| `telegram.provisionings` | counter | `:887` | charted (p12) | consumed |
| `telegram.refusals` | counter | `:890` | charted (p10) | consumed |
| `optimizer.runs` | counter | `shift-optimizer/shift_optimizer/app/services/run_telemetry.py:51` / `:175` | charted ×3, rule `OptimizerRunFailureRate` (oss+aws) | consumed |
| `optimizer.run.duration` | histogram | `:54` / `:176` | charted (p5) | consumed |
| `optimizer.solve.duration` | histogram | `:60` / `:145` | charted (p6) | consumed |
| `optimizer.runs.active` | up-down | `:66` / `:194,:206` | charted (p3), iac markdown | consumed |

#### 1a-bis. The legacy `MetricsService` block — an entire unconsumed family

`utils-obsm/utils/observability/metrics.py` still ships `LegacyMetricsService`, which
**auto-registers a counter/histogram/up-down-counter on first use from the call site's own string**
(`metrics.py:100,110,123,133`). `get_metrics_service()` (`metrics.py:144`) always returns a live
service — there is no off switch. Every name below is therefore emitted whenever its code path runs,
and **not one of them is named by any panel, rule, alarm, or runbook query** (verified by grepping
all six consumer surfaces; the only `document_hub_*` hits in `CATALOGUE.md` are the `document_hub_documents`
**table**, not a metric).

| Signal | Kind | Emitter (file:line) | Consumption | Verdict |
|---|---|---|---|---|
| `llm_requests_total` | counter | `utils-obsm/utils/llm.py:393,444,799` | none | **ORPHAN** |
| `llm_request_duration` | histogram (unit `1`) | `utils/llm.py:400,451` | none | **ORPHAN** |
| `llm_tokens_total` | counter | `utils/llm.py:350` | none | **ORPHAN** |
| `llm_tokens_per_request` | histogram (unit `1`) | `utils/llm.py:358` | none | **ORPHAN** |
| `embedding_requests_total` | counter | `utils/llm.py:1179` | none | **ORPHAN** |
| `embedding_tokens_total` | counter | `utils/llm.py:1183` | none | **ORPHAN** |
| `embedding_cost_usd` | histogram (unit `1`) | `utils/llm.py:1189` | none | **ORPHAN** (and a USD figure recorded as a unitless histogram) |
| `embedding_request_duration` | histogram (unit `1`) | `utils/llm.py:1193` | none | **ORPHAN** |
| `embedding_cache_hits_total` | counter | `utils/llm.py:1299` | none | **ORPHAN** |
| `embedding_cache_tokens_avoided_total` | counter | `utils/llm.py:1304` | none | **ORPHAN** |
| `chat_block_save_failures_total` | counter | `copilot-mro-obsm/copilot_mro/app/api/chat_management.py:379` | none | **ORPHAN** |
| `memory_get_latency_ms` | histogram (unit `1`) | `copilot_mro/app/services/memory/memory_db.py:880` | none | **ORPHAN** |
| `memory_search_latency_ms` | histogram (unit `1`) | `copilot_mro/app/services/memory/memory_index.py:636` | none | **ORPHAN** |
| `document_hub_upload_total` | counter | `document_hub/operations.py:20`, emitted via `record_document_hub_metric` `:72` | none | **ORPHAN** |
| `document_hub_retry_total` | counter | `operations.py:21` | none | **ORPHAN** |
| `document_hub_delete_total` | counter | `operations.py:22` | none | **ORPHAN** |
| `document_hub_share_total` | counter | `operations.py:23` | none | **ORPHAN** |
| `document_hub_processing_total` | counter | `operations.py:24` | none | **ORPHAN** |
| `document_hub_processing_duration_seconds` | histogram (unit `1`) | `operations.py:25` | none | **ORPHAN** (unit `1` on a `_seconds`-named histogram) |
| `document_hub_parser_failure_total` | counter | `operations.py:26` | none | **ORPHAN** |
| `document_hub_index_upsert_total` | counter | `operations.py:27` | none | **ORPHAN** |
| `document_hub_cleanup_total` | counter | `operations.py:28` | none | **ORPHAN** |
| `document_hub_cleanup_vectors` | counter | `operations.py:29` | none | **ORPHAN** |
| `document_hub_cleanup_objects` | counter | `operations.py:30` | none | **ORPHAN** |
| `document_hub_notification_total` | counter | `operations.py:31` | none | **ORPHAN** |
| `document_hub_attempt_vector_cleanup_total` | counter | `operations.py:36` | none | **ORPHAN** |
| `document_hub_query_embedding_fallback_total` | counter | `operations.py:40` | none | **ORPHAN** |

**27 emitted, unconsumed metric families** from the legacy shim, plus `gen_ai.client.operation.duration`
= **28 orphaned metric families**. None is in `_emitted_series.SERIES`, and none can ever be caught by
its lint (see §5, FAMILY_TOKEN).

### 1b. Browser events (log records) — the `dashboard-obsm` merged tree

`lib/telemetry/events.ts:28-51` declares 20 event names + 1 span name (`CHAT_TURN_SPAN`, `:55`).
I verified a production producer for each by tracing the exported emitter and its wrappers.

| Signal | Emitter (file:line) | Consumption | Verdict |
|---|---|---|---|
| `browser.web_vital` | `lib/telemetry/web-vitals.ts` → `events.ts:282` | charted ×2 (fn-frontend p1,p2), 3 Loki rules, 3 CW alarms, iac widget | consumed |
| `browser.error` | `lib/telemetry/errors.ts` → `events.ts:297` | charted ×2, Loki rule `BrowserErrorRateHigh`, CW alarm, iac widget | consumed |
| `browser.route.change` | `lib/telemetry/use-route-telemetry.ts` → `events.ts:347` | charted (p5), iac widget, runbook | consumed |
| `browser.app.boot` | `components/providers/TelemetryProvider.tsx` → `events.ts:359` | charted (p19 "Slowest Pages") | consumed |
| `browser.telemetry.dropped` | `lib/telemetry/provider.ts` → `events.ts:321` | charted (p18, 7 targets), iac widget | consumed |
| `browser.feature.mutation` | `mutation-meta.ts:174` metas across hooks | charted (p11,p12), iac widget ×2 | consumed |
| `browser.settings.mutation` | `mutation-meta.ts:162` metas (12 hook sites) | charted (p13), iac widget | consumed |
| `browser.auth.flow` | `startAuthFlowTiming` → `events.ts:794`; 6 auth components | charted (p14), iac widget | consumed |
| `browser.optimizer.run_triggered` | `optimizerRunTelemetry` `mutation-meta.ts:189`, `useOptimizer.ts:551,576` | charted (p15), iac widget | consumed |
| `browser.export.requested` | `withExportRequested` `events.ts:874`; `WorkOrderCarousel.tsx:115`, `CanvasHeader.tsx:199` | charted (p16), iac widget | consumed |
| `browser.ad_review.disposition_set` | `hooks/mro/useAdReview.ts:186` | charted (p17), iac widget | consumed |
| `browser.automation.run_settled` | `lib/telemetry/long-running.ts` → `events.ts:835`; `useAutomations.ts:29` | charted (p17 target A), iac widget | consumed |
| `browser.discovery.job_settled` | `long-running.ts` → `events.ts:846`; `useDiscoverySettleTelemetry.ts:12` | charted (p17 target B), iac widget | consumed |
| **`browser.auth.login`** | `startLoginTiming` `events.ts:582` → `emitAuthLogin` `:369`; `components/features/auth/LoginView.tsx` | **none.** The fn-frontend "Auth flows" panel description (`frontend.json:228`) says so verbatim: *"no panel charts it — read it in Loki directly until one exists"* | **ORPHAN (documented)** |
| **`browser.pdf.render`** | `startPdfRenderTiming` `events.ts:611` → `:382`; `components/features/pdf-viewer/pdf-viewer-main.tsx` | none | **ORPHAN** |
| **`browser.upload.started`** | `withUploadTelemetry` `events.ts:536` → `:392` (call at `:541`); `hooks/document-hub/useDocumentHubMutations.ts:86` | none | **ORPHAN** |
| **`browser.automation.run_triggered`** | `hooks/api/useAutomations.ts:267` meta | none (only its `run_settled` sibling is charted) | **ORPHAN** |
| **`browser.discovery.job_started`** | `app/(dashboard)/data-discovery/page.tsx:179`, `.../jobs/[jobId]/page.tsx:712` | none (only `job_settled` is charted) | **ORPHAN** |
| **`browser.chat.feedback_submitted`** | `hooks/chat/useFeedback.ts:51` meta | none | **ORPHAN** |
| **`browser.log`** | `lib/telemetry/logger.ts` → `events.ts:313` | no panel, no rule, no runbook query. The only `{service_name=…}` raw-log panel on any board is telegram-bot's (`telegram-bot.json:284`); fn-frontend has none | **ORPHAN — log-search-only** |

### 1c. Spans — reachability reported separately from charted

The estate has **no span-metrics connector in the collector** (`deployment/otel/base.yaml` has no
`connectors:` block; neither overlay adds one). `traces_spanmetrics_*` comes from **Tempo's
metrics-generator** (`deployment/observability-local/tempo.yaml:34-66`, `overrides.defaults.metrics_generator.processors: [service-graphs, span-metrics]`),
remote-writing to Prometheus. Its configured dimensions are `db.system, peer.service, server.address,
rpc.service, url.template`. In the **aws** profile there is no Tempo — X-Ray Transaction Search is
the only trace surface, and it has no dashboard-widget form (`iac/dashboards/agent-turn-explorer.json.tftpl`
is two markdown panels saying exactly that).

| Span | Emitter (file:line) | Charted | Trace-search reachable | Verdict |
|---|---|---|---|---|
| `invoke_agent <runtime>` | `telemetry.py:1508` (`turn_span`) | no direct panel; attributes `gen_ai.operation.name` / `agent.outcome` are TraceQL selectors on fn-agent-turn-explorer p1,p2 | yes (Tempo; X-Ray TS) | consumed — trace search |
| `invoke_agent <runtime>` (content copy) | `telemetry.py:1731` (`record_content_copy_span`) | no | only on the `traces/content` pipeline (`filter/content_only`), which no checked-in backend profile exports in `backend-oss.yaml`/`backend-aws.yaml` | **unreachable in both shipped profiles** — see §4 |
| `execute_tool <name>` | `telemetry.py:1891`/`:1899` | **charted** — fn-agent-turn-explorer p3, `span_name=~"execute_tool .*"` over `traces_spanmetrics_latency_bucket` | yes | consumed |
| `retrieve evidence`, LLM/tool child spans | `telemetry.py:1336`, `:1761` | no | content pipeline only | same as content copy |
| `agent_sdk.tool.<short>` | `agent_shared/loop_observability.py:248` | no | yes, **but suppressed** whenever runtime telemetry exists (`agent_pipeline.py:276` `suppress_legacy_agent_sdk_spans=runtime_telemetry is not None`) | dead by design when OTel is on |
| `automation.run` | `api-obsm/flynapse_api/telemetry/run_span.py:22,45` | no | yes | trace-search-only |
| `optimizer.run` / `.solve` / `.persist` | `shift-optimizer/.../run_telemetry.py:32-34`, `:195,:131,:150` | `optimizer.run` selected by TraceQL on fn-shift-optimizer p11,p12; `.solve`/`.persist` not | yes | `.run` consumed; `.solve`/`.persist` trace-search-only |
| `telegram.update` | `telegram-bot/telegram_bot/telemetry.py:633` | TraceQL on fn-telegram-bot p17,p18 | yes | consumed |
| `telegram.turn` / `telegram.turn.<phase>` | `telemetry.py:709`,`:767` | no | yes | trace-search-only |
| `s3.download` | `utils-obsm/utils/s3_service.py:226` (CLIENT) | **charted indirectly** — fn-dependencies p2 `server_address`/`rpc_service` | yes | consumed via spanmetrics |
| `weaviate.hybrid_search` | `utils-obsm/utils/weaviate_service.py:1011` (CLIENT) | same | yes | consumed via spanmetrics |
| `db.chat.save_block` | `copilot_mro/app/api/chat_management.py:1332,:1734` | no (INTERNAL, not CLIENT — not in fn-dependencies' `SPAN_KIND_CLIENT` filter) | yes | trace-search-only |
| `mro.lifecycle.startup` / `.shutdown` | `copilot_mro/app/main.py:102,:235` | no | yes | trace-search-only |
| `ingest.parse` | 7 parsers (`mel_parser.py:1541`, `tn_parser.py:1974`, `crew_manual_parser.py:1546`, `amos_parser.py:4659`, `ifim_parser.py:2604`, `ftd_parser.py:2003`, `amos_metadata_backfill.py:272`) + `s3_pdf_processor.py:927` | no | yes | trace-search-only |
| `document_hub.process` / `.cleanup` | `document_hub/processing.py:137`, `cleanup.py:213` | no | yes | trace-search-only |
| `data_discovery.job.run` | `data_discovery/runner.py:142` | no | yes | trace-search-only |
| `improvement.run` / `.stage` | `improvement/runner.py:460,:507` | no | yes | trace-search-only |
| `memory.items.get_by_ids` + `memory_index` spans | `memory/memory_db.py:67`, `memory_index.py:96` | no | yes | trace-search-only |
| **`browser.chat.turn`** | `dashboard-obsm/lib/telemetry/chat-turn.ts:60` | **no panel, no rule.** Named only in `CATALOGUE.md` | yes (Tempo browser pipeline) | **ORPHAN — trace-search-only**; the one browser signal with no consumer at all |

**No span is an orphan merely for lacking a panel** — that is the intended shape for INTERNAL work
spans. The only span I would call a genuine gap is the **content-copy tree**, which is unreachable in
both shipped profiles (§4).

---

## 2. Consumed-but-unemitted

### 2a. Genuinely dead

| Consumer (where) | Signal it reads | Emitted by | Verdict |
|---|---|---|---|
| `fn-llm-agents` p10 "Claude Code CLI tokens and cost", target A (`llm-agents.json:189`) | `claude_code_token_usage_total` | **nothing in the estate.** No `CLAUDE_CODE_ENABLE_TELEMETRY` anywhere (grepped `copilot-mro-obsm/deployment`, `copilot_mro`, `api-obsm`, `iac`); the only hit is a *comment* in `base.yaml:98` | **DEAD** — correctly declared `dark` in `_emitted_series.py:141` and `CATALOGUE.md:273` |
| same panel, target B (`:194`) | `claude_code_cost_usage_total` | nothing | **DEAD**, correctly declared |
| `iac/dashboards/llm-agents.json.tftpl` markdown | `{"claude_code.token.usage"}`, `{"claude_code.cost.usage"}` | nothing | **DEAD**, declared |
| `flynapse-platform-alerts.yml:60` `AutomationWorkerSilent` — `absent(target_info{job="flynapse/automation-worker"})`, `for: 15m`, severity **warning** | `target_info` for `service.name=automation-worker` | `api-obsm/flynapse_api/automations/worker.py:111` sets that name, **but no checked-in compose runs the worker**: `deployment/docker-compose.yml` (11 services) and `deployment/observability-local/observe-docker-compose.yml` (7 services) contain none | **PERMANENTLY FIRING** in any oss deployment. `absent()` on a never-present series is `1` forever. The AWS twin is gated behind `automation_worker_deployed = false` (`iac/alarms.tf:61`) and is therefore *not created*; the oss twin has no such gate |
| `fn-platform-health` p6 "Automation worker heartbeat" (`platform-health.json:96-101`) | same `target_info` | same | **PERMANENTLY "worker absent = 1"** |
| `rules/loki/flynapse/browser-alerts.yml:99` `AutomationRunErrors` — `{service_name="automation-worker"}` | log stream for that service | same | **NEVER FIRES** — the inverse failure of the two above. Its own annotation calls it a "TRANSITIONAL LOG PROXY … arms as soon as worker logs flow"; nothing makes them flow |
| `iac/alarms.tf` `LedgerWriteFailures` description (`:210`) | *the description itself*: "DARK until Task R names and wires the ledger-write-failure signal: no instrument … is created anywhere in the estate" | the instrument now exists (in-flight) | **STALE ASSERTION** in iac `2d493c8`; the copilot-mro twin was updated in the same in-flight batch and iac was not |
| `iac/dashboards/llm-agents.json.tftpl` markdown: "Subagents: **DARK** — the instruments exist and nothing calls `record_subagent`" | — | `record_subagent` is now bound on both runtimes (in-flight) | **STALE ASSERTION** in iac `2d493c8` |

### 2b. In-flight (excluded from the verdict, per the brief)

| Consumer | Signal | State at `HEAD` `d8d2570c` | State in the working tree |
|---|---|---|---|
| `fn-platform-health` p5 "Ledger write failures (1h)" (`platform-health.json:118`) | `agent_ledger_write_failures_total` | dead | instrument `telemetry.py:1462`, recorder `:1922`, 8 call sites via `usage_ledger.py:84` / `model_call_ledger.py:70` |
| `flynapse-agent-alerts.yml:56` `LedgerWriteFailures` | same | dead; annotation said so | annotation rewritten to `WIRED 2026-09-20` |
| `iac/alarms.tf:208` `LedgerWriteFailures` | same | dead | **still says DARK** (iac not yet updated) |
| `fn-llm-agents` p9 "Subagent rate and p95 duration" (`llm-agents.json:168,:173`) | `agent_subagent_calls_total`, `agent_subagent_duration_seconds_bucket` | **dead** — instruments existed, `record_subagent` had no production caller | wired via `agent_shared/subagent_runs.observe_subagent_runs:105`, bound at `agent_pipeline.py:268,:684`, called at `lang_agent/backend.py:975` and `agent_claude/orchestrator.py:3560` |

### 2c. `ApiHighErrorRate` in `iac/alarms.tf` — confirmed non-functional under both shapes

`iac/alarms.tf:113-124`:

```
( sum by ("@resource.service.name") (rate({"http.server.request.duration", "http.response.status_code"=~"5.."}[5m]))
  / (sum by ("@resource.service.name") (rate({"http.server.request.duration"}[5m])) > 0.1) ) > 0.05
```

`http.server.request.duration` is a **histogram** (`api-obsm/flynapse_api/telemetry/http_server.py`,
contrib ASGI `duration_histogram_new`). The selector carries no suffix and no `le` filter, so it
selects the histogram itself.

| Stored shape | What the expression does | Can it fire correctly? |
|---|---|---|
| **Native histogram** | `rate(H)` yields a native histogram. PromQL supports `+`/`-` between two histograms and `*`/`/` only histogram-by-*float*; histogram ÷ histogram drops the sample. The volume guard `rate(H) > 0.1` is likewise a histogram-vs-float comparison, which is also invalid | **No — never fires.** Both the ratio and the guard are type errors; the alarm returns no series |
| **Classic `le`-labelled buckets** | `sum by (svc)` collapses every `le` bucket into one number, so each request is counted once per bucket it falls into. The ratio becomes a *latency-weighted* share, not the 5xx request share — and it is biased exactly the wrong way, because 5xx responses are typically fast and therefore land in **more** buckets than slow 2xx ones | **No — fires on the wrong quantity**, systematically over-stating the error share |

**Correct forms:**

| Shape | Numerator / denominator |
|---|---|
| Native | `sum by ("@resource.service.name") (histogram_count(rate({"http.server.request.duration", "http.response.status_code"=~"5.."}[5m])))` over `sum by (…) (histogram_count(rate({"http.server.request.duration"}[5m])))` |
| Classic buckets | add `"le"="+Inf"` to **both** selectors (the `+Inf` bucket *is* the request count), or read a `…_count` series if one exists on the endpoint — the file's own header asserts none does |

The file already flags this as unresolved (`alarms.tf:107-114`: *"both sides of this ratio want a
request count out of a histogram, and how that is written depends on what CloudWatch stores … Written
bare, as here"*). **The brief's claim is confirmed.** The **oss** twin
(`flynapse-api-alerts.yml:11`) is *correct*: it names `http_server_request_duration_seconds_count`
explicitly, which is a single series per label set.

`ApiP95LatencyHigh` (`alarms.tf:131-142`) is **not** broken the same way: `histogram_quantile` over a
native histogram tolerates the redundant `sum by (le, …)` (grouping by an absent label yields one
group), and over classic buckets the `le` grouping is exactly right. Its `increase({…}) >= 20` volume
guard has the same histogram-vs-float problem under the native shape, so that half would drop — worth
the same fix, but the alarm is not wrong in the same sense.

### 2d. Every other selector converted by iac `2d493c8`, checked against the three emitter repos

| Selector in `iac` | Emitted? | Where |
|---|---|---|
| `{"http.server.request.duration"}`, `"http.route"`, `"http.response.status_code"` | yes | contrib ASGI + `OTEL_SEMCONV_STABILITY_OPT_IN` defaulted to `http` at `flynapse-otel/flynapse_otel/bootstrap.py:52,171` |
| `{"http.server.active_requests"}` | yes | same instrumentation, wrapped at `api-obsm/flynapse_api/telemetry/http_server.py:225` |
| `{"http.client.request.duration"}`, `server.address` | yes | httpx instrumentation `0.65b0`, `__init__.py:792`, attrs `_client_duration_attrs_new` incl. `SERVER_ADDRESS` |
| `{"auth.rejections"}` | yes | `api-obsm/flynapse_api/middleware/telemetry.py:34` |
| `{"agent.turn.calls"}`, `"agent.outcome"` | yes | `telemetry.py:1406` / `:1819` |
| `{"agent.turn.duration_seconds"}` | yes | `:1411` |
| `{"agent.model.cost_usd"}`, `"tenant.id"`, `"model.profile"` | yes | `:1432`, attrs `:1784` + `for_turn` `:1469` |
| `{"agent.model.unpriced_calls"}` | yes | `:1437` |
| `{"agent.tool.attempts"}`, `"tool.name"`, `"tool.outcome"` | yes | `:1447`, attrs `:1800` |
| `{"gen_ai.client.token.usage"}`, `"gen_ai.request.model"`, `"gen_ai.token.type"` | yes | `:1421`, `:1842` |
| `{"agent.ledger.write_failures"}` | **in-flight** | `:1462` |
| `{"claude_code.token.usage"}`, `{"claude_code.cost.usage"}` | **no** | dead, declared |
| `{"telegram.turns"}`, `"outcome"`, `"lane"`, `"reason"`, `"verdict"` | yes | `telegram-bot/telegram_bot/telemetry.py:883-890`; `COUNT_DIMENSIONS` at `:139` contains all of them |
| `{"telegram.updates"}` `"kind"`, `{"telegram.updates.active"}`, `{"telegram.turn.duration"}`, `{"telegram.turn.phase.duration"}` `"phase"`, `{"telegram.turn.cost"}` `"lane"`, `{"telegram.jobs"}`, `{"telegram.uploads"}`, `{"telegram.provisionings"}`, `{"telegram.refusals"}` | yes | `:649,:631,:796,:799,:801,:842`, `:886-890` |
| `{"optimizer.runs"}`, `"status"`, `"solve_status"` | yes | `run_telemetry.py:175`; `METRIC_ATTRIBUTE_KEYS = {"status","solve_status"}` at `:42` |
| `{"optimizer.run.duration"}`, `{"optimizer.solve.duration"}`, `{"optimizer.runs.active"}` | yes | `:176,:145,:194` |
| `otelcol_exporter_send_failed_{spans,metric_points,log_records}`, `otelcol_exporter_queue_{size,capacity}`, `otelcol_receiver_refused_*`, `otelcol_process_uptime` | reaches CloudWatch via the periodic OTLP reader added in `backend-aws.yaml:69-76` → `otlphttp/cwmetrics` | **spelling unverifiable statically** — the aws-profile runbook records a 2026-09-15 capture-exporter observation for `otelcol_process_uptime` only |
| `"@resource.service.name"` values `api`, `telegram-bot`, `dashboard`, `automation-worker` | `api` ✓ (`iac/apprunner.tf:47`), `telegram-bot` ✓ (`telemetry.py` `SERVICE_NAME`), `dashboard` ✓, **`automation-worker` ✗ (not deployed)** | — |

**Verdict on 2d493c8: every converted selector but the two `claude_code.*` ones and
`agent.ledger.write_failures` names a metric something emits.** The conversion itself is sound; the
defect is `ApiHighErrorRate`'s *shape*, not its *name*.

### 2e. The CloudWatch attribute-path spelling — 4 alarms + 11 widgets at risk

The browser emitter writes the event name as a **dotted log attribute**: `events.ts:264`
`attributes: { 'event.name': name, …}`. Every CloudWatch consumer selects it as
**`attributes.event_name`** (underscore):

- `iac/alarms.tf:258,289,297,305` — the 4 browser metric filters behind `BrowserErrorRateHigh`,
  `WebVitalLcpP75Poor`, `WebVitalInpP75Poor`, `WebVitalClsP75Poor`.
- `iac/dashboards/frontend.json.tftpl` — 10 of its 11 Logs Insights widgets.

The same files address `service.name` **dotted** (`resource.attributes.service.name`) and one query
addresses `session.id` **dotted** (`frontend.json.tftpl:127` `by attributes.session.id`). Both
spellings cannot be right. The estate already knows: `docs/runbooks/observability/aws-profile.md:22-23`
says *"`event.name` (written `attributes.event_name` — Loki's sanitised spelling; the stored key is
`event.name`)"*, and `alarms.tf:53` lists it under the B1b RE-VERIFY block. **Verdict: consumed-but-
possibly-unemitted, self-declared unverified.** If CloudWatch preserves dotted keys — which the
`resource.attributes.service.name` usage assumes — all four browser alarms and ten widgets match nothing.
The same `alarms.tf:53` note flags `severity_number` (used at `:278`, `:323`) for the same reason.

### 2f. Consumers checked and found sound

| Consumer | Signal | Emitter confirmed |
|---|---|---|
| `fn-frontend` p7,p8 (`frontend.json:131,:146`) `rawSql` over `product_events` selecting `document_id`, `document_kind` | Postgres columns | real columns — `core-obsm/core/db/table_definitions.py:1407,1408`; `document_opened` is in `PRODUCT_EVENT_NAMES` `:1366` and emitted at `dashboard-obsm/lib/telemetry/use-document-view.ts:73`, `components/features/chat/DocumentCard.tsx:114` |
| `fn-llm-agents` p11,p12 `rawSql` over `llm_usage` / `llm_model_calls` | Postgres | written by the two ledgers the in-flight `count_lost_ledger_write` guards |
| `fn-dependencies` (5 panels), `fn-frontend` p6,p9, `fn-agent-turn-explorer` p3, `fn-telegram-bot` p14 target B | `traces_spanmetrics_{latency_bucket,calls_total}` + `db_system`/`server_address`/`rpc_service`/`url_template` | Tempo generator `tempo.yaml:58-66`; every board label is a configured dimension and `tests/integration/otel/test_tempo_span_metrics.py:118` guards that. **The family NAME is unproved against the `grafana/tempo:3.0.3` pin** (see §4) |
| `fn-platform-health` p9,p10,p11 | `prometheus_tsdb_head_series`, `loki_distributor_*`, `tempo_distributor_*` | the `prometheus`/`loki`/`tempo` scrape jobs in `prometheus.yml` |
| `flynapse-platform-alerts.yml:96` `AlertmanagerNotificationsFailing` | `alertmanager_notifications_failed_total` | the `alertmanager` scrape job |
| `flynapse-platform-alerts.yml:73` `TempoGeneratorSeriesNearCap` | `tempo_metrics_generator_registry_active_series_demand_estimate` | Tempo self-scrape; the cap it references is real (`tempo.yaml:85`) |
| `fn-service-overview` templating `label_values(http_server_request_duration_seconds_count, job)` | `job` label | `prometheusremotewrite/prom` with `target_info.enabled: true` (`backend-oss.yaml:17-22`) and `NAMESPACE = "flynapse"` (`flynapse-otel/flynapse_otel/resource.py:27`) → `job = flynapse/<service.name>` |
| every `browser.*` LogQL panel/rule label | Loki structured metadata | `test_grafana_dashboards.py:566` `test_browser_logql_reads_only_keys_the_collector_delivers` already enforces it against `transform/browser_allowlist` |

---

## 3. Attribute and cardinality compliance

### 3.0 There is no attribute allow-list. Name the surfaces.

The brief asked me to "find the allow-list". **It does not exist.** What exists:

| Surface | File:line | Kind | Contents |
|---|---|---|---|
| `flynapse_otel.registry.FORBIDDEN_ATTRIBUTE_KEYS` | `flynapse-otel/flynapse_otel/registry.py:27` | **DENY-list**, 10 keys, process-side | `session_id`, `session.id`, `user_id`, `user.id`, `enduser.id`, `path`, `url`, `url.path`, `url.full`, `http.target` |
| `flynapse_otel.registry.UNITS` | `registry.py:23` | ALLOW-list, but of **units**, not attributes | `1 s ms By {USD} {token} {request}` |
| collector `attributes/metric_cardinality` | `copilot-mro-obsm/deployment/otel/base.yaml:76` | **DENY-list**, 10 keys, collector-side, metrics pipeline only | `session.id`, `user.id`, `user.email`, `enduser.id`, `organization.id`, `terminal.type`, `app.entrypoint`, `url.path`, `http.target` |
| collector `transform/browser_allowlist` | `base.yaml:136` | ALLOW-list, **attribute-keyed**, browser pipelines only | ~90 record keys + 9 resource keys |
| `shift_optimizer…METRIC_ATTRIBUTE_KEYS` | `run_telemetry.py:42` | **per-instrument ALLOW-list**, raises on an unlisted key (`_labels` `:71`) | `status`, `solve_status` |
| `telegram_bot…COUNT_DIMENSIONS` | `telegram-bot/telegram_bot/telemetry.py:139` | per-family ALLOW-list, filters silently (`dimensions()` `:906`) | `lane reason carrier outcome refund verdict chat_type created` |

Three consequences worth the owner's attention:

1. **The two satellites are the only repos with a positive attribute contract.** `copilot-mro` and
   `api` have none — any new attribute ships unless it happens to collide with one of the 10
   forbidden keys.
2. **A forbidden key drops the whole datapoint, not the key.** `registry._lint_attributes` raises
   `AttributeKeyError`; `RuntimeTelemetry._safe_add`/`_safe_record` (`telemetry.py:1548,:1554`)
   catch `Exception` and `return`. Adding `enduser.id` to an agent metric would make that **series
   vanish silently**, not just lose a label. The legacy shim (`utils/observability/metrics.py:76`)
   drops the *key* with one WARNING instead — two opposite degradations for the same mistake.
3. **`tenant.id` is on no list, in either direction.** It is neither forbidden nor allow-listed;
   it is simply passed through. That is the ruling the owner owes.

### 3.1 Per-instrument attribute table

`D` = also carries `RuntimeTelemetry._default_attributes` from `for_turn` (`telemetry.py:1469`),
i.e. `tenant.id` + `agent.department`. **`for_turn` is applied only to the model-usage sink**
(`agent_pipeline.py:89,:222,:579`); the tool and subagent observers are bound from the *unscoped*
facade (`agent_pipeline.py:264,:272,:688,:693`), so they carry neither.

| Instrument | Attributes actually set | On a list? | Unbounded / user-controlled | Expected cardinality (label sets) |
|---|---|---|---|---|
| `agent.turn.calls` / `agent.turn.duration_seconds` (`telemetry.py:1819`) | `gen_ai.agent.name`, `agent.department`, `agent.outcome`, `tenant.id`, `deployment.environment.name` (**never passed — always `None`, always dropped**; `pipeline.py:493`) + D | none forbidden | **`tenant.id`** | runtimes 2 (`claude`/`lang`, canonicalised `telemetry.py:36-47`) × departments 3 (`MRO/PILOT/CREW`) × outcomes 2 = **12 per tenant**; ×2 instruments |
| `agent.model.calls`, `agent.model.cost_usd`, `agent.model.unpriced_calls`, `gen_ai.client.operation.duration` (`telemetry.py:1784`) | `gen_ai.operation.name` (const `chat`), `gen_ai.provider.name`, `gen_ai.request.model`, `model.role`, `model.purpose`, `model.profile`, `model.cost_source`, `model.graph_node`, `error.type` + D | none forbidden | **`tenant.id`**; **`gen_ai.request.model`** (provider-supplied string); **`model.profile`** (registry-supplied); **`error.type`** (outcome token) | roles ≤12 (`contracts/models.py:11-28`) × purposes 9 (literals) × graph_nodes ≈17 (10 static + `f"{prefix}:{decision}"` over 7 decisions, `lang_agent/decisions.py:88`) × models ~6-10 × cost_source ~3 × error.type ~8 (`model_gateway.py:276-403`: `transient_error`, `usage_normalization_error`, `response_normalization_error`, `cancelled`, `error`, …). Realistic joint occupancy **~150-400 per tenant** |
| `gen_ai.client.token.usage` (`telemetry.py:1855`) | the above **+ `gen_ai.token.type`** (6 values: input/output/reasoning/cache_read/cache_write/tool_search_overhead) | none forbidden | as above | **×6** the model row → **~900-2,400 per tenant** — the single largest family |
| `agent.tool.calls` / `agent.tool.attempts` (`telemetry.py:1800`) | `gen_ai.operation.name` (const), `tool.name`, `tool.outcome`, `tool.error_code`, `error.type` (**identical value to `tool.error_code`** — two labels, one value) | none forbidden | `tool.error_code` — `ToolError.code` is typed `str` in the contract (`contracts/tools.py:432`); **103 distinct `code="…"` literals** in `copilot_mro` | tools ~70 (73 distinct `name="…"` literals under `agent_shared/tools/`) × (1 success + ~3 realistic codes) ≈ **280**, **not tenant-scoped** |
| `agent.subagent.calls` / `.duration_seconds` (`telemetry.py:1811`) | `subagent.name`, `subagent.outcome` | none forbidden | **`subagent.name` is the MODEL's raw `subagent_type` string** — `agent_claude/_subagent_runs.py:59` takes `tool_input["subagent_type"]` verbatim, no catalogue validation, despite `subagent_runs.py:113` asserting "`name` is a catalogue agent name" | catalogue agents ~20 × outcomes 3 (`completed/error/incomplete`) = **~60 expected**; **worst case unbounded** — one hallucinated `subagent_type` per turn mints a permanent series. Not tenant-scoped |
| `agent.ledger.write_failures` (`telemetry.py:1922`, in-flight) | `ledger.name` (2), `ledger.outcome` (3), `tenant.id` + D | none forbidden | **`tenant.id`** | **6 per tenant** — the docstring's own arithmetic, and it is right |
| `auth.rejections` (`api-obsm/.../middleware/telemetry.py:85`) | `http.response.status_code` (2), `http.request.method` (~7) | none forbidden | none | **~14**, estate-wide |
| `http.server.request.duration` / `http.server.active_requests` | contrib ASGI new-semconv set: `http.request.method`, `http.route`, `http.response.status_code`, `url.scheme`, `network.protocol.version` | `url.path`/`http.target` would be forbidden — correctly **not** set (the route is templated, `http_server.py:8-17`) | none | routes ~220 × methods ~3 × statuses ~8 ≈ **5,000** per service, ×15 histogram buckets |
| `http.client.request.duration` | `error.type`, `http.request.method`, `http.response.status_code`, `network.protocol.version`, `server.address`, `server.port` (`_semconv.py:130`) | none forbidden | **`error.type` = `type(exc).__qualname__`** — an exception class name, unbounded in principle | hosts ~8 × methods ~4 × statuses ~8 ≈ **256**, + one series per distinct exception class |
| `telegram.turns` / `.uploads` / `.provisionings` / `.refusals` | the `COUNT_DIMENSIONS` subset each line carries | **positive allow-list** `telemetry.py:139` | none | lanes ~3 × carriers ~3 × outcomes ~6 × reasons ~10 → **~500** worst case; no tenant label |
| `telegram.updates` / `.active` / `.turn.duration` / `.turn.phase.duration` / `.turn.cost` / `.jobs` | `kind`(6)/none/`lane`+`outcome`/`phase`(5)/`lane`/`name`+`outcome` | closed vocabularies (`UPDATE_KINDS` `:144`) | none | **< 100 total** |
| `optimizer.runs` / `.run.duration` / `.solve.duration` / `.runs.active` | `status` (2), `solve_status` (4 + null) | **positive allow-list, raises** `run_telemetry.py:71` | none — run/job/tenant ids ride the **span** only (`:110-115`), by explicit design | **≤ 10**. The cleanest instrument in the estate |
| **legacy** `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request` | `tenant_id`, `model`, `status`, (+ provider) | `tenant_id` is **not** on `FORBIDDEN_ATTRIBUTE_KEYS` (only `user_id`/`session_id` are) | **`tenant_id`**, **`model`** (raw model string) | models ~10 × statuses 2 = **20 per tenant**, ×4 families |
| **legacy** `embedding_*` (6 families) | `tenant_id`, `model`, `status` | as above | **`tenant_id`**, `model` | **~20 per tenant** ×6 |
| **legacy** `chat_block_save_failures_total` (`chat_management.py:379`) | `tenant_id`, `department`, `reason`, `error_kind`, `field` | none forbidden | **`tenant_id`**; **`error_kind`** and **`field`** are free strings from the failure path | departments 3 × reasons ~8 × error_kinds ~15 × fields ~20 = **up to 7,200 per tenant** — **the worst single cardinality exposure in the estate** |
| **legacy** `memory_get_latency_ms`, `memory_search_latency_ms` | `tenant_id` + call-site kwargs | none forbidden | **`tenant_id`** | small per tenant, but unaudited |
| **legacy** `document_hub_*` (14 families, `operations.py:72`) | `tenant_id` + arbitrary `**attributes` per call site | none forbidden, **no allow-list at all** | **`tenant_id`**; every call site chooses its own keys | **unbounded by construction** — the helper forwards whatever the caller passes |
| browser records (all 20 events) | per-event `EVENT_ATTRIBUTE_KEYS` (`events.ts:67`) + envelope (`session.id`, `route_pattern`, `app.version`, `deployment.environment.name`) + gateway-upserted `tenant.id`/`enduser.id`/`session.id` (`base.yaml:51`) | **double allow-listed** (browser `emitRecord:239` strips off-list keys; collector `transform/browser_allowlist` re-strips) | these are **LOG records, not metrics** — `attributes/metric_cardinality` does not touch them, and `session.id`/`enduser.id` legitimately ride them | not a metric-cardinality concern; a Loki *stream* concern only if any of these became an index label, which `test_browser_logql_reads_only_keys_the_collector_delivers` prevents |

### 3.2 The tenant-scoped cardinality list the owner must rule on

Every metric below carries a **tenant identifier as a metric label**. Multiply each by the tenant count.

| # | Metric | Tenant label | Per-tenant label sets | Also carries |
|---|---|---|---|---|
| 1 | `gen_ai.client.token.usage` | `tenant.id` | **~900-2,400** (×15 histogram buckets + sum + count ⇒ ~15k-40k Prometheus series) | model, profile, role, purpose, graph_node, token type |
| 2 | `gen_ai.client.operation.duration` | `tenant.id` | ~150-400 (×17 series each) — **and nothing reads it** | as above |
| 3 | `agent.model.calls` | `tenant.id` | ~150-400 | as above |
| 4 | `agent.model.cost_usd` | `tenant.id` | ~150-400 | as above |
| 5 | `agent.model.unpriced_calls` | `tenant.id` | ~150-400 | as above |
| 6 | `agent.turn.calls` / `agent.turn.duration_seconds` | `tenant.id` | 12 | runtime, department, outcome |
| 7 | `agent.ledger.write_failures` (in-flight) | `tenant.id` | 6 | ledger, outcome |
| 8 | `chat_block_save_failures_total` (legacy) | `tenant_id` | **up to 7,200** | department, reason, error_kind, **field** |
| 9 | `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request` (legacy) | `tenant_id` | ~20 each | model, status |
| 10 | `embedding_requests_total`, `embedding_tokens_total`, `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`, `embedding_cache_tokens_avoided_total` (legacy) | `tenant_id` | ~20 each | model, status |
| 11 | `memory_get_latency_ms`, `memory_search_latency_ms` (legacy) | `tenant_id` | unaudited | call-site kwargs |
| 12 | 14 × `document_hub_*` (legacy) | `tenant_id` | **unbounded by construction** | caller-chosen keys |

**Non-tenant-scoped but worth a ruling:** `subagent.name` (model-authored, unvalidated) and
`tool.error_code` / `error.type` (103 literals, and `ToolError.code` is typed `str`).

### 3.3 The collector processors

| Processor | Verdict |
|---|---|
| `attributes/metric_cardinality` (`base.yaml:76`) | Present on the **metrics** pipeline of both shipped profiles (`backend-oss.yaml:56`, `backend-aws.yaml:93`). It is a 10-key **deny**-list. It does **not** delete `tenant.id`, `tenant_id`, `model`, `field`, `error_kind`, `subagent.name` or anything in §3.2 — i.e. **none of the estate's actual cardinality exposure is caught here.** It also runs *after* `transform/genai_aliases`, which is correct (the aliases add `tenant.id`, not a forbidden key) |
| `transform/browser_allowlist` (`base.yaml:136`) | **Confirmed attribute-keyed, not event-keyed.** Two `keep_matching_keys` calls on `span.attributes`/`log.attributes` plus one on `resource.attributes`. There is **no `event.name` filter anywhere** in the browser pipelines — no `filter/` processor, no condition on the record's event name |

**What attribute-keying implies, both directions:**

- **Direction 1.** A brand-new browser event reaches Loki/CloudWatch the moment it is emitted, with
  zero collector edits, provided its attribute keys happen to be on the ~90-key list — and *most new
  events reuse `outcome`/`duration_ms`/`error_type`, which are already on it*. So a new event is
  delivered and orphaned by default, invisibly. Empirically this is exactly what happened: **7 of the
  20 catalogued events are delivered and read by nothing**, and the only mechanical guard,
  `test_frontend_board_charts_every_phase9_browser_event` (`test_grafana_dashboards.py:553`),
  covers **only the 9 phase-9 events** listed at `:441-451`. The 7 orphans are precisely the
  pre-phase-9 members that tuple omits. That is a structural explanation, not a coincidence.
- **Direction 2.** A panel written against `event_name="browser.X"` fails silently in two distinct
  ways the allow-list cannot distinguish: the event is not emitted at all, or the event arrives but
  the attribute the panel unwraps was stripped. The second mode is guarded for panels
  (`test_browser_logql_reads_only_keys_the_collector_delivers`) but the guard reads the panel, not the
  emitter — a panel naming a *correct* key for an event nobody emits still passes.
- **One concrete hole this creates today.** `EVENT_NAMES.LOG` is in `OPEN_ATTRIBUTE_EVENTS`
  (`events.ts:205`), so the browser lets developer-authored payload keys through unfiltered — and
  then the collector allow-list strips every one of them that is not among the ~90. `browser.log`'s
  extras are therefore emitted, shipped and silently deleted at the collector. Since nothing charts
  `browser.log` either, nobody would notice.

---

## 4. What R.4 cannot determine without running the system

| # | Question | Why code reading cannot answer it |
|---|---|---|
| 1 | **Does any of this arrive?** Every "consumed" verdict above proves a *reference*, never a *retrieval*. `_emitted_series.py` itself says so: the entire agent half is `wired`, not `live`. No probe has seen an `agent_*` series in Prometheus. Acceptance is proved by query, never by a lint's exit code |
| 2 | **The Prometheus name each metric actually gets.** Unit→suffix mapping is computed statically in `_emitted_series.base_name`, but the exporter's real behaviour at the pinned versions — and whether `prometheusremotewrite` re-sanitises — is a scrape question |
| 3 | **Whether CloudWatch stores `http.server.request.duration` as a native histogram or `le` buckets.** This decides which of the two `ApiHighErrorRate` failure modes in §2c is the live one. Probe B1a |
| 4 | **Whether CloudWatch renders a dotted log-attribute key as `event.name` or `event_name`** (§2e). Four alarms and ten widgets hang on it. Probe B1b |
| 5 | **Tempo 3.0.3's span-metrics family name.** Six panels read `traces_spanmetrics_latency_bucket` / `traces_spanmetrics_calls_total`. The *labels* are guarded against `tempo.yaml`'s dimensions by `test_tempo_span_metrics.py`; the **metric name** is guarded by nothing and has been renamed across Tempo majors before |
| 6 | **The collector's own internal-metric names through the periodic OTLP reader** (`backend-aws.yaml:73`). The oss side is scraped and the spellings are recorded as live-verified at 0.160.0; the aws side rides a different reader and only `otelcol_process_uptime` has an observation behind it |
| 7 | **Whether the legacy `MetricsService` families actually flow.** They are emitted only when their code paths execute; I proved the call sites exist, not that they run in any deployment. Their cardinality estimates in §3.2 are structural upper bounds, not measurements |
| 8 | **`subagent.name`'s real value space.** Bounded in practice by which `subagent_type` strings the model emits — knowable only from live data |
| 9 | **Whether the content-copy span tree reaches any backend.** `filter/content_only` (`base.yaml:196`) is defined, but **neither `backend-oss.yaml` nor `backend-aws.yaml` declares a `traces/content` pipeline**. On a static read the whole `record_content_copy_span` tree (`telemetry.py:1731`) is exported nowhere in either shipped profile; only `content-phoenix.yaml` might carry it, and I did not trace that overlay to a deployment |
| 10 | **Whether `AutomationWorkerSilent` is actually firing.** Structurally it must (§2a). Whether Alertmanager is delivering it, and whether an operator has silenced it, is runtime state |
| 11 | **The in-flight batch's final shape.** Three files I quote (`_emitted_series.py`, `flynapse-agent-alerts.yml`, `platform-health.json`) are being edited as I write. Re-run §2b against the committed diff |

---

## 5. Everything in the brief that was wrong

| # | Brief's claim | Verdict |
|---|---|---|
| 1 | "an implementer … is at this moment creating an instrument for `agent.ledger.write_failures`" | **True.** Uncommitted: instrument `telemetry.py:1462`, recorder `:1922`, 8 call sites |
| 2 | "and possibly **subagent span** … call sites" | **False in one half.** Subagent *metric* call sites are being created (`observe_subagent_runs`, `subagent_runs.py:105`). There is **no subagent span** anywhere in the estate — not before, not in the in-flight diff. A subagent produces no span of its own in either runtime |
| 3 | "and tenant/department attributes on tool metrics" | **Not present at read time.** `agent.tool.calls` / `.attempts` carry neither. The cause is structural: `agent_pipeline.py:264,:693` bind `record_tool_operation` from the *unscoped* facade, while only `model_usage_sink(turn)` (`:89`) goes through `for_turn`. Same for `record_subagent` (`:272,:688`). If this is intended work, it is not in the tree yet |
| 4 | "`_emitted_series.py` … `FAMILY_TOKEN` … reported to cover only `agent.*` / `gen_ai.*` / `claude_code.*`" | **True**, plus two bare span tokens. The regex (`_emitted_series.py:190`) is `\b(?:agent\|gen_ai\|claude_code)[._][A-Za-z0-9_.]*\|\b(?:invoke_agent\|execute_tool)\b`. The in-flight diff does **not** touch it. **Blast radius: ~14 of 85 panels are inspected** (fn-llm-agents' 10 PromQL panels, fn-agent-turn-explorer's 3, fn-platform-health's ledger stat). **71 panels — 84% — are invisible to it**, including all of fn-service-overview (7), fn-dependencies (5), fn-telegram-bot (18), fn-shift-optimizer (12), fn-platform-health's other 8, and fn-frontend's 19. Of the 4 Prometheus rule files only `flynapse-agent-alerts.yml` is inspected; `flynapse-api-alerts.yml`, `flynapse-platform-alerts.yml` and `flynapse-satellite-alerts.yml` are not. Nothing named `otelcol_*`, `http_*`, `traces_spanmetrics_*`, `telegram_*`, `optimizer_*`, `auth_rejections_*`, `loki_*`, `tempo_*`, `prometheus_*`, `alertmanager_*`, `document_hub_*`, `llm_*` or `embedding_*` can ever be resolved, contradicted or flagged by it |
| 5 | "six browser events are emitted, delivered, and consumed by nothing" | **The six are right but the list is incomplete.** It is **seven events plus one span**: add **`browser.log`** (emitted `lib/telemetry/logger.ts` → `events.ts:313`; no panel, no rule, no runbook — I classify it *log-search-only*) and **`browser.chat.turn`** (a span, `chat-turn.ts:60`; *trace-search-only*). Also worth recording: `browser.auth.login`'s orphanhood is already stated verbatim inside the fn-frontend board at `frontend.json:228` |
| 6 | "The `LedgerWriteFailures` Prometheus rule states in its own annotation that no instrument exists" | **False of the working tree; true of `HEAD`.** `flynapse-agent-alerts.yml:56` now reads "WIRED 2026-09-20, retrieval unproved: … recorded by `agent_shared/usage_ledger.py`'s `count_lost_ledger_write`". **The false claim has moved to `iac`**, which at `2d493c8` still says "DARK until Task R names and wires the ledger-write-failure signal: no instrument … is created anywhere in the estate" (`alarms.tf:210`), and whose `llm-agents.json.tftpl` still says "Subagents: **DARK** — the instruments exist and nothing calls `record_subagent`". Both are now wrong |
| 7 | "`iac` `2d493c8` has converted every CloudWatch selector … to unsuffixed dotted brace-selector form" | **True.** Exactly **27 distinct dotted metric names** across `alarms.tf` + `dashboards/*.tftpl`, every one enumerated in §2d. Exception, correctly: the `otelcol_*` self-telemetry names keep their underscore spelling, because that is the instrument name the collector itself uses |
| 8 | "the AWS profile's metrics pipeline exports native OTLP via `otlphttp/cwmetrics` with no `prometheusremotewrite` exporter anywhere on that path" | **True — independently re-verified.** `backend-aws.yaml:42` defines `otlphttp/cwmetrics`; `:88-98` is the whole metrics pipeline; no `prometheusremotewrite` appears in `base.yaml` or `backend-aws.yaml`. `prometheusremotewrite/prom` exists only in `backend-oss.yaml:16` |
| 9 | "`ApiHighErrorRate` in `iac/alarms.tf` is non-functional under both candidate metric shapes" | **Confirmed.** Full analysis and both corrected expressions in §2c. Under native, the ratio *and* the volume guard are type errors and it never fires; under classic buckets it computes a latency-weighted share biased toward over-reporting. The **oss** twin is correct and is not affected |
| 10 | "the browser allow-list is attribute-keyed rather than event-keyed" | **True**, and it is worse than "no event gate": there is no `filter/` processor on either browser pipeline at all. Implications in §3.3 |
| 11 | "Check every instrument's attributes against **the registry's allow-list**" | **The premise is false.** There is no attribute allow-list in the registry — only a 10-key **deny**-list (`FORBIDDEN_ATTRIBUTE_KEYS`) and a *unit* allow-list. Positive per-instrument attribute allow-lists exist in exactly two repos, `shift-optimizer` and `telegram-bot`. `copilot-mro` and `api` have none. §3.0 |
| 12 | "`copilot-mro-obsm/tests/integration/otel/_emitted_series.py` … the derived metric inventory, mechanically verified" | **True but narrow.** It inventories **14 metric series** (12 `agent.*`/`gen_ai.*` + 2 `claude_code.*`) and **5 span signals** — counted by `grep -c 'Series('` / `'SpanSignal('`. The estate emits **57 metric families** (30 current + 27 legacy). 28 of them (§1a-bis + `gen_ai.client.operation.duration`) are orphans the inventory neither lists nor can detect |
| 13 | "`docs/plans/obs-telemetry-merge-review-packet/` — six claims files, **269 claims**" | Six files confirmed present. I did not recount the claims; the coverage matrix's header says 234 in one place and the brief says 269 — I flag the discrepancy rather than resolve it, since R.4 did not need it |
| 14 | "an implementer is active [in api-obsm] (adding a log-hygiene guard only)" | **Consistent.** `api-obsm` has exactly one untracked path, `tests/unit/api_surface/` |
| 15 | *(unstated)* | **A third implementer is active in `dashboard-obsm`.** Untracked: `contracts/browser-signals.json`, `scripts/generate-browser-signal-contract.mts`, `tests/fixtures/telemetry/browser-signals.ts`, `tests/unit/telemetry/browser-signal-contract.test.ts`. It is generating a machine-readable browser-signal inventory — the `_emitted_series.py` of the browser half — listing all 20 events + the `browser.chat.turn` span, each with `state: "wired"` and its producer files. It closes the *emitter* side of the §3.3 hole. It does **not** close the *consumer* side: nothing in it requires a panel. Worth telling whoever owns it that R.4 found seven events it will mark `wired` with no consumer at all |
| 16 | *(unstated)* | **`fn-shift-optimizer` has 12 panels, not 11**, and **`fn-telegram-bot` 18, not 17** — I mention it only because the R.3 matrix and CATALOGUE prose quote per-board counts, and mine come from `grep -c '"gridPos"'` on the JSON |
