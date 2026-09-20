# Observability Rebuild — Implementation Plan (master)

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (one fresh
> subagent per task, review between tasks) or superpowers:executing-plans. Steps use checkbox syntax for
> tracking. This is the **master** plan: each phase gets a detail plan
> (`docs/plans/observability-rebuild-phase-<id>.md`, task-level, test-first) written at phase start. Runtime-
> dependent work waits for the migration gate (§2); Phase 1c is the explicitly audited exception for stable
> non-agent boundaries whose target files are outside that conflict zone.

**Goal:** Replace the decorative telemetry estate with a backend-agnostic OTel contract, a collector-profile
swap layer (`oss` one-box / `aws` CloudWatch), real traces/metrics/logs, LLM/agent observability on top of
the cost ledgers, a Postgres-backed product dashboard, and an eval workbench — per the ruled spec.

**Architecture:** server services emit OTLP/HTTP to one gateway collector; the browser sends OTLP through the
authenticated Flynapse API forwarder to that collector. Only the collector's profile overlay and IaC know the
backend. Product analytics read Postgres, never the log store. LLM cost truth
stays in `llm_usage`/`llm_model_calls`; telemetry carries structure and cost attributes; content goes to a
tenant-scoped relation and, sampled, to Phoenix.

**Tech stack:** Python 3.11 / FastAPI / loguru; `opentelemetry-sdk 1.44.0` + contrib `0.65b0`;
`otel/opentelemetry-collector-contrib` (pinned); Loki/Prometheus/Tempo/Grafana (oss); CloudWatch OTLP
endpoints + `sigv4auth` (aws); Next.js 15.2.4 + OTel JS 2.x; Postgres with RLS; optional Arize Phoenix;
Terraform.

**Spec:** `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` (rev 4, rulings 1–20 in §11).
**Research:** `docs/plans/observability-rebuild-audit.md`, `docs/plans/observability-rebuild-research/01..09`
(08 = Task R's starting baseline, folded from `obs-telemetry-merge` with its Gate M finding corrected;
09 = the outcome/span-attribute reconciliation that merge left owed to R.2).

## Global constraints (from the spec; every task inherits them)
- Application code never learns the backend: OTLP/HTTP-protobuf, standard `OTEL_*` env only, no vendor SDKs.
- Resource identity: `service.namespace=flynapse`, `service.name`, `service.version`, `service.instance.id`,
  `deployment.environment.name`. W3C `tracecontext` in and out; no outbound `baggage`.
- No user, session, chat, document or request identifier and no raw URL path on any metric. `tenant.id` is
  allowed only on explicitly approved tenant-scoped instruments with a documented cardinality bound; units
  declared; `{USD}` not `USD`.
- No user content in log lines; prompt/completion bodies only in `llm_turn_content` and the Phoenix pipeline.
- Pins: `opentelemetry-sdk==1.44.0`, `opentelemetry-exporter-otlp-proto-http==1.44.0`, contrib `==0.65b0`;
  collector image pinned; every compose image pinned.
- Test layout: two levels (`tests/<kind>/<domain>/`), globally unique basenames, `tests/_root.py` for paths;
  dynamic-loader pattern for copilot-mro planner modules; run from the shared `api` Poetry env with
  `DEBUG=false`.
- Git: Claude commits only files it created plus test edits, by pathspec; pre-existing production files stay
  uncommitted for the owner. One implementer per worktree; concurrent agents bounded by the session cap.
- Owner rulings (spec §11) are not re-litigated by tasks; deviations go to the phase's implementation notes.

---

## 1. Base-branch strategy (owner constraint, 2026-09-05)

The LangChain/LangGraph migration is in flight (`langgraph-merge` in `api`, `copilot-mro`, `utils`; batch 2
and the citation-ids branch in worktrees). **New observability code must land on top of that code.** So:

| Area | Migration touches it? | Rule |
|---|---|---|
| `copilot-mro/copilot_mro/app/services/{agent_shared,lang_agent,agent_claude}/**`, `api/chat_management.py`, `agent_pipeline.py`, `utils/utils/llm.py` | **Yes** (conflict zone) | No edits until the migration gate (§2). |
| `utils/utils/observability/**`, `utils/utils/logging_config.py` (delegation only), new `utils/utils/observability/*.py` modules | No (additive) | Stream U may proceed; branch from `langgraph-merge`; rebase on each batch merge. |
| `api/flynapse_api/{main.py,middleware/**}` | No | Stream U wiring may proceed after the utils modules exist. |
| Stable non-agent seams listed in Phase 1c: MRO lifecycle; memory; Document Hub processing/cleanup; Data Discovery one-job runner; improvement scheduler/runner; approved parser command entrypoints; shared S3/Weaviate clients | No target file is in the conflict zone and no target-file change appears in the 2026-09-01..2026-09-08 migration history at audit time | Stream N may proceed from the current `langgraph-merge` heads, subject to the Phase 1c path/drift guard. It may wrap a call into changing code, but must not edit that code, its dependency imports or the wrapper's signature/control flow. |
| `core/**` (master), `dashboard/**` (agent_sdk), `iac/**` (main), `copilot-mro/deployment/**` | No | Streams I, F, P proceed now. |
| `copilot-mro/.../postgres_table_definitions_modules/{chat,llm_usage}.py`, `chat_history/blocks.py` | Indexes: no; `chat_turn_facts` writer: **yes** (block-save path) | Index lines + table definition now; the writer after the gate. |
| `copilot-mro/tests/e2e/**` (eval harness) | Tests only | Stream E harness side may proceed. |

Branch names: `obs-infra` (copilot-mro, deployment/ only, from `langgraph-merge`), `obs-utils` (utils, from
`langgraph-merge`), `obs-api` (api, from `langgraph-merge`), `obs-analytics` (core from `master`; dashboard
from `agent_sdk`), `obs-frontend` (dashboard from `agent_sdk`) and `obs-iac` (iac from `main`). The pre-migration
audit/application work uses the common label `obs-non-agent` in each independent repository: the existing Core
and dashboard branches retain Phase 11.1 and continue into 11.2; copilot-mro and utils carry Phase 1c, with MRO
deployment-only 11.4/11.5 changes added as separate commits. Runtime-dependent work branches from
`langgraph-merge` **after** the gate as `obs-agent`. Phase 1c uses one implementer across its two repositories,
rebases before each task and never shares a production file with the migration owner.

## 2. The migration gate and the rescoping task (Gate M → Task R)

**Gate M — owner declares "migration landed"**: the LangChain batches the owner is running are merged into
`langgraph-merge` and no further batch is expected to touch the conflict zone for the duration of Stream L.

**GATE M DECLARED 2026-09-14 by the owner** — "langraph migration is done. so we can build and moerge now." — given
while ruling phase 10's `/rag/stream` item (copilot-mro `langgraph-merge` @ `a24189ee`; S4 pushed at `4ba3c7f0`). The
§1 conflict-zone freeze is lifted. Task R below is UNBLOCKED but starts only on its own owner go; phase 10 does not
start it.

**Task R — rescoping (after Gate M, before any Stream L task)**
- [ ] R.1 Re-run the backend inventory of research 01 §2.1–2.4 (metrics, spans, log families, LLM call paths)
      against the merged code; write the diff to `docs/plans/observability-rebuild-research/08-post-migration-rescoping.md`
      (Opus agent, read-only). Enumerate every new module under `lang_agent/`, `agent_shared/` and any new
      runtime/tool/subagent code paths that need logging context, spans or metrics.
- [ ] R.2 Produce the **backend signal catalogue** (spec §4): per service and subsystem, every span (name,
      kind, attributes, parent) and every metric (name, kind, unit, attributes, cardinality bound), each
      mapped to the dashboard/alert that consumes it, with the current-vs-target diff. Include the new
      LangChain code's needs found in R.1.
- [ ] R.3 Owner reviews the catalogue; rulings recorded in this file under **Rescoping notes** (§14).
- [ ] R.4 Write the detail plans for the Phase 1b runtime remainder and Phase 3 from the approved catalogue;
      do not duplicate stable boundaries completed by Phase 1c; re-check phases 5 and 7
      items that touch the conflict zone (`chat_turn_facts` writer, content-capture write site, harness hooks).

---

## 3. Streams and sequencing

The original streams and their execution dependencies are listed below. Stream A was added by the later audit
follow-up. Stream N was added by the 2026-09-08 code review to separate stable non-agent work from the runtime
conflict zone; A's and L's runtime tasks still wait for Gate M and Task R.

| Stream | Phase(s) | Repos / branch | Depends on | Starts |
|---|---|---|---|---|
| **I — infra & profiles** | 0 (infra half), 2, 6 (oss dashboards/rules scaffold), 7 (optional Phoenix container) | copilot-mro `deployment/` (`obs-infra`), iac (`obs-iac`) | nothing | now |
| **U — telemetry library + gateway wiring** | 1a (utils), 1b-api (api gateway) | utils (`obs-utils`), api (`obs-api`) | nothing for 1a; 1a for 1b-api | now |
| **N — stable non-agent telemetry** | 0 (safe MRO hygiene), 1c | copilot-mro + utils (`obs-non-agent`) | merged Stream U; Phase 1c signal-slice approval | now |
| **P — product analytics** | 5 | core (`obs-analytics`), dashboard (`obs-analytics`), copilot-mro table definitions (tiny) | nothing (writer deferred) | now |
| **F — frontend telemetry** | 4 | dashboard (`obs-frontend`) | P's ingest evolution for the switch-over only | now |
| **L — agent runtime** | 0 (chat/runtime hygiene), Phase 1b runtime remainder, 3, `chat_turn_facts` writer, content capture | copilot-mro (`obs-agent`), utils `llm.py` | **Gate M + Task R** | after gate |
| **D — dashboards & alerts** | 6 | copilot-mro `deployment/`, iac | catalogue (R.2) for LLM/agent views; instrumentor names for service views | service views now; agent views after R |
| **E — evals** | 7 | copilot-mro `tests/e2e` (harness), deployment (Phoenix) | optional Phoenix activation (I); content copy needs L | harness now; Phoenix wiring after L |
| **A — audit follow-ups** | 11 (§11e; written as "8") | core, dashboard, copilot-mro `deployment/`, and later iac | current-state reconciliation; runtime work also needs Task R (Gate M declared 2026-09-14/15) | non-runtime tasks after 11.0; runtime task after Task R |

Merge order for the dashboard repo: `obs-analytics` first (settings page + analytics client), then
`obs-frontend` rebased on it (they share `package.json` and `lib/api/*`).

---

## 4. Phase 0 — Hygiene quick wins

**Infra half (Stream I, now)**
- [ ] 0.1 Pin every observability image in the four compose files (`observability-local/observe-docker-compose.yml`,
      `deployment/docker-compose.yml`, `deployment/poc/docker-compose.yml`, `deployment/demo/docker-compose.yml`)
      to explicit versions — **the latest stable release of each** (Grafana, Loki, Tempo, Prometheus,
      `otel/opentelemetry-collector-contrib`, Phoenix), verified against the projects' release pages at task
      time (owner request: latest images with the latest updates, never a floating `:latest` tag); record the
      chosen versions and their release dates in `deployment/otel/VERSIONS.md` together with a bump policy
      (re-check monthly; bump with a compose smoke run). Remove the `debug` exporter from all pipelines and set
      collector telemetry log level to `info`. Test: `otelcol validate` on the config in CI (Task 2.1 supplies the CI job; until then a local
      `docker run … validate`). Commit (new/changed compose files are pre-existing → report the diff; new CI
      files commit).
- [ ] 0.2 Loki: `auth_enabled: true` with a single tenant header from the collector; `limits_config.retention_period`
      + `compactor` per spec retention; Tempo `block_retention` 72h (POC) via env; Prometheus retention env.
      Test: compose smoke (Task 2.3) asserts a log written now is queryable and one older than retention is not
      (fixture with backdated timestamps).
- [ ] 0.3 Grafana admin password from env/secret, never `admin/admin`; all admin ports loopback-bound in every
      compose file; README Jaeger references removed.
- [ ] 0.4 iac: trim `aws_instance.weaviate_observability` security group to 22 (allowed IP), 8080/50051
      (Weaviate from the app SGs) and 4318 (OTLP from the app SGs only); drop 3000/9090/3100/3200/9464/13133/1777/14250/14268.
      Test: `terraform plan` shows only SG rule removals; a review checklist item confirms no app path used them.

**Application hygiene, split by code-ownership boundary**
- [ ] 0.5a **Stream N, now:** remove the raw `query` field from the "Memory search completed" log in
      `memory_index.py` and the shared Weaviate hybrid-search log; retain only bounded metadata such as
      `query_chars`, operation type and result count. Phase 1c owns the tests. The actual query arguments passed
      to search functions are business inputs and remain unchanged.
- [ ] 0.5b **Stream L, after Gate M + R:** remove `query=request.message` from the two "Enhanced chat request
      received" calls in `chat_management.py`; add `query_chars` instead. Test with the existing no-content AST
      scan. This task stays gated because it edits the active chat orchestration path.
- [ ] 0.6a **Stream N, now:** delete only the MRO `/metrics` route in `copilot-mro/app/main.py`. The API redirect,
      scrape token and API direct dependency were already removed by Stream U. Test that the composed route table
      has no `/metrics` path.
- [ ] 0.6b **Dependency-file coordination point:** remove the now-unused direct `prometheus-client` declaration
      from `copilot-mro/pyproject.toml` and refresh its lock only after the migration owner confirms dependency
      files are idle, or after Gate M. This cleanup must not delay 0.6a or Phase 1c.

**Acceptance for phase 0:** compose stacks start with pinned images and no debug exporter; retention and auth
verified by the smoke; no user text in the identified memory/Weaviate/chat log calls; no `/metrics` route.

---

## 5. Phase 1 — Backend telemetry foundation

### 1a — `utils` library (Stream U, now; additive modules, no call-site changes)

**Files (all new unless noted):** `utils/utils/observability/bootstrap.py`, `.../registry.py`,
`.../log_bridge.py`, `.../intercept.py`, `.../resource.py`; `utils/utils/observability/tracing.py` and
`metrics.py` reduced to thin helpers; `utils/utils/logging_config.py` modified only to delegate to
`log_bridge`. Tests under `utils/tests/unit/observability/`.

- [ ] 1a.1 `bootstrap(service_name: str, *, version: str | None = None) -> None`: idempotent; honours
      `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL` (default
      `http/protobuf`), `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_TRACES_SAMPLER(_ARG)`; builds Tracer/Meter/Logger
      providers with OTLP/HTTP exporters and the resource of `resource.py` (`service.namespace=flynapse`,
      `service.instance.id` = hostname+pid, `deployment.environment.name` from env). Tests: second call is a
      no-op; disabled → no exporters; resource attributes present; protocol default http.
- [ ] 1a.2 `registry.py`: `counter(name, unit, description)`, `histogram(...)`, `observable_gauge(name, unit,
      callback)`, `up_down_counter(...)`; refuses duplicate names with different kinds; validates units against
      an allow-list (`1`, `s`, `ms`, `By`, `{USD}`, `{token}`, `{request}`); an attribute-key lint that raises on
      `session_id`, `user_id`, `enduser.id`, `path`, `url`. Tests for each rule.
- [ ] 1a.3 `log_bridge.py`: loguru sink over `LoggingHandler` that flattens `record["extra"]` to top-level
      attributes, sets the record time from `record["time"]`, maps levels, attaches exception info; JSON stdout
      sink (`serialize=True`) with the same flattening; no file sinks. Tests with an in-memory log exporter:
      attribute names are top-level (`tenant_id`, not `extra.tenant_id`), timestamps equal the loguru time,
      trace/span ids present when a span is active, numeric extras stay numeric.
- [ ] 1a.4 `intercept.py`: stdlib `InterceptHandler` installed on the root logger and explicitly on
      `uvicorn.access`, `uvicorn.error`, `botocore`, `httpx`; `opentelemetry.*` loggers excluded. Tests: a
      `logging.getLogger("x").warning(...)` reaches the in-memory exporter; an `opentelemetry.sdk` logger does
      not; uvicorn access logger with `propagate=False` still reaches it.
- [ ] 1a.5 `setup_logging(name, env)` becomes a thin call to `bootstrap` + `log_bridge.install`; `setup_loguru`'s
      "skip if any handler exists" branch removed (idempotence handled by a module flag). Tests: calling twice
      installs sinks once; `LOG_COLORS` honoured on stdout only in dev.
- [ ] 1a.6 Pin the OTel packages in `utils/pyproject.toml` and add the instrumentation packages listed in spec
      §4 (no `-botocore`); `poetry lock` in the shared `api` env; dependency-drift test asserting the pins.
- [ ] 1a.7 Delete `utils/utils/config.py` `otel_endpoint`/`otel_enabled`/`otel_service_name` fields and their
      readers (spec §3.1); grep-test that no code reads `OTEL_ENDPOINT` or `OTEL_ENABLED`.

**Interfaces produced:** `bootstrap()`, `registry.counter/histogram/observable_gauge/up_down_counter`,
`log_bridge.install(level: str)`, `intercept.install()`, `resource.build(service_name, version)`.

### 1b-api — gateway wiring (Stream U, after 1a; api repo)
- [ ] 1b.1 `api/flynapse_api/main.py`: call `bootstrap("api")` before `PostgresService` builds its pool (verify
      import order; test in `tests/integration/otel/test_pool_instrumented.py` that one pooled query yields a
      `db.*` span). Instrument the gateway with `FastAPIInstrumentor.instrument_app(app, excluded_urls=<mount
      prefixes + health>)`; instrument each mounted sub-app (`core`, `copilot-mro`, `shift-optimizer`) with
      `instrument_app(subapp)`. Test: in-process smoke with an in-memory exporter — one SERVER span per request,
      `http.route` = mount prefix + sub-app route for a mounted route; zero spans for `/health/live`.
- [ ] 1b.2 Apply `httpx`, `requests`, `urllib3`, `psycopg2`, `redis` instrumentors in `bootstrap` (behind
      `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS`). Test: an outbound `httpx` call carries `traceparent` (assert on a
      local test server); a redis call produces a `db.system=redis` span (fakeredis or skip-if-absent).
- [ ] 1b.3 Replace `middleware/observability.py`'s hand-rolled metrics and server span with: a two-line
      `X-Trace-Id` response-header middleware; an `auth.rejections` counter for gateway-level 401/403 (no span);
      delete `active_sessions`/`active_users`/`http_requests_total`/`http_request_duration_seconds`. Test: the
      metric names no longer appear in the in-memory reader; `X-Trace-Id` present.
- [ ] 1b.4 `middleware/logging.py` keeps `logger.contextualize` binding; add `request.id`/`tenant.id`/
      `enduser.id`/`session.id` as span attributes on the current server span in a `server_request_hook`.
      Test: attributes present on the span.
- [ ] 1b.5 Health: `GET /health/live` (static) and `GET /health/ready` (calls copilot-mro's aggregate probe
      body; no `debug` field). Test: ready returns per-dependency verdicts; live never touches dependencies.
- [ ] 1b.6 Automations worker: `bootstrap("automation-worker")`; each run opens a root span with `tenant.id`,
      `automation.run_id`, a `Link` to nothing yet (the scheduling span lands in L); `logger.contextualize`
      bound for the run. Test: a fake executor run yields a root span and bound log attributes.

### 1c — stable non-agent application telemetry (Stream N, now; independent of Gate M)

**Phase 1c is a re-cut of our own gated 1b.7 and 1b.8 (recorded at the fold, 2026-09-20).** It keeps its
number — nothing of ours ever claimed "1c" — but it is not new scope. Our 1b.7 and 1b.8 held, behind Gate M,
exactly what 1c carved out and built before the gate: the MRO lifecycle bootstrap, the S3 and Weaviate wrapper
spans, the six dead `document_hub_qna_*` constants, the parser `__main__` service names, and the document-hub /
improvement / data-discovery background roots. Their insight was that none of those files sit in the conflict
zone, so the gate never applied to them; they proved it with a path manifest and a drift guard rather than by
argument. What the gate really covered is what is now "1b-mro — runtime handoff remainder" below. Two items of
ours did **not** come across and remain owed: the **Weaviate connection-factory** span (1b.7's wrapper, carried
as G.10 in the merge plan) and the removal of `prometheus-client` from `copilot-mro/pyproject.toml` (their
0.6b, still declared in the merged tree — the `/metrics` route itself is gone).

**Planning status:** approved scope only; no application code was changed when this phase was added. Before
implementation, write `docs/plans/observability-rebuild-phase-1c-stable-nonagent.md` with the exact signal slice
and tests below, then obtain owner approval. Audit baseline: copilot-mro `ac680bf2` and utils `9f74a11` on
`langgraph-merge`, both clean on 2026-09-08.

**Why this work is safe now.** A component is included only when its edited file is outside the declared
agent/runtime conflict zone, the intended function is a stable coarse-grained operation boundary, the target file
was not changed by the 2026-09-01..2026-09-08 migration commits, and instrumentation can be additive without
changing its signature, return value, persistence or control flow. A wrapper may call code that is still moving;
that does not authorize edits below the wrapper. Re-run these checks at task start—if a target has drifted, move
that task behind Gate M instead of resolving an ownership conflict in this phase.

| Included component | Source evidence at the audit baseline | Why it belongs in this phase |
|---|---|---|
| MRO process lifecycle and direct-scrape cleanup | `copilot-mro/copilot_mro/app/main.py:59-150` is the single lifespan boundary for boot checks, enqueuer installation and the improvement timer; `:239-245` is the remaining direct `/metrics` route. `core/__init__.py:7-10` and `app/main.py:11-13` already call shared `setup_logging`. | One additive lifecycle boundary covers start/stop outcomes without entering chat or agent code. No second bootstrap is needed; only the remaining direct scrape route is removed. |
| Shared S3 and Weaviate clients | `utils/utils/observability/bootstrap.py:47-57` deliberately does not auto-instrument botocore; `utils/utils/s3_service.py:162-205` handles S3 outcomes in one wrapper, including returned failures; `utils/utils/weaviate_service.py:943-995` is the shared hybrid-search boundary and currently logs the raw query. The operator dashboard explicitly expects Weaviate/S3 client spans in `copilot-mro/deployment/otel/dashboards/CATALOGUE.md:63-79`. | Instrumenting the shared clients covers callers once and supplies the already-designed dependency view. Explicit status is required where wrappers return failure instead of raising. No botocore instrumentor is added, so LLM spans are not duplicated. |
| Memory indexing/search | `memory/memory_index.py:138,273,362,389,590` exposes the stable collection/upsert/delete/search/reindex operations; `:555-570` records latency and logs raw query text. `memory/memory_db.py:801-841` has the current get-by-id timing and uses `item_count` as a metric label. | Operation spans and log correlation belong at these public memory boundaries. Existing Postgres auto-instrumentation already covers SQL, so individual DAO methods are not duplicated; the unbounded numeric label and raw content can be removed without changing memory behavior. |
| Document Hub processing and cleanup | `document_hub/processing.py:1-25` explicitly defines the queue-independent end-to-end processing interface and `:133-141` wraps one attempt. `document_hub/cleanup.py:193-219` defines the single restartable sweep entry. Existing processing/cleanup metrics are emitted from these paths. | These are stable job lifecycle seams. Their spans naturally become children of the existing API automation-run span when context exists, or roots for standalone execution; no new queue or duplicate automation root is introduced. |
| Data Discovery job runner | `data_discovery/runner.py:1-19` explicitly defines the automations attachment seam; `:98-151` runs one tenant/job to a terminal or skipped outcome. `data_discovery/cli.py:137-147` is a standalone entrypoint and currently has no telemetry bootstrap. | The one-job wrapper can carry bounded tenant/job trace context without touching `data_discovery/agent/**`, tools, templates or providers. The CLI needs the same shared bootstrap when run outside the API process. |
| Improvement scheduler and batch runner | `improvement/scheduler.py:139-188` dispatches and isolates one tick; `improvement/runner.py:1-45,436-620` defines one tenant batch and its sequential stage lifecycle. Both are loader-friendly and use stdlib logging, which the merged shared intercept already exports. | Adding one run span plus bounded stage spans closes the lifecycle gap while leaving LLM calls and agent-shared prompt/tool modules untouched. Existing log export is reused; this phase only makes outcome and correlation structured. |
| Parser/ingest command entrypoints | Seven non-LLM `main` functions in `services/parsers/` plus `services/s3_pdf_processor.py:680-692` already call `setup_logging`, but mint eight parser-specific service names; the entrypoint calls are outside the recent migration diff. | Standardizing only these command boundaries to `service.name=ingest-parser` plus a root-span `parser.kind` prevents service-name explosion. Parser internals, OCR, prompt and LLM call sites are not edited; `amos_post_processing.py` is excluded because it directly imports `utils.llm`. |

**Allowed production-path manifest (no other production file is authorized by Phase 1c):**

- `copilot-mro/copilot_mro/app/main.py`
- `copilot-mro/copilot_mro/app/services/memory/{memory_index.py,memory_db.py}`
- `copilot-mro/copilot_mro/app/services/document_hub/{processing.py,cleanup.py,operations.py}`
- `copilot-mro/copilot_mro/app/services/data_discovery/{runner.py,cli.py}`
- `copilot-mro/copilot_mro/app/services/improvement/{scheduler.py,runner.py}`
- Parser command modules under `copilot-mro/copilot_mro/app/services/parsers/`: `amos_parser.py`,
  `amos_metadata_backfill.py`, `ftd_parser.py`, `ifim_parser.py`, `tn_parser.py`, `crew_manual_parser.py` and
  `mel_parser.py`; plus `copilot-mro/copilot_mro/app/services/s3_pdf_processor.py`
- `utils/utils/{s3_service.py,weaviate_service.py}`

Tests may be added only under the matching existing Copilot MRO unit-test domains (`observability`, `memory`,
`document_hub`, `data_discovery`, `improvement`), `copilot-mro/tests/parsers/`, and
`utils/tests/unit/observability/`. The detail plan must name globally unique test basenames before implementation.

**Phase boundary—reviewed but not included now:**

- `agent_shared/**`, `agent_claude/**`, `lang_agent/**`, `agent_pipeline.py`, `chat_management.py`, all tool/skill
  modules, `data_discovery/agent/**`, and `utils/utils/llm.py` remain owned by Gate M, Task R and Phase 3.
- `amos_post_processing.py` and parser internals such as `image_transcription.py` are not edited because they
  directly touch the in-flight LLM/prompt paths. They remain gated even though they expose command entrypoints.
- `lambda_functions/s3_pdf_processor_lambda.py:156-225` is a separate execution unit, logs the full event/result,
  and has neither shared bootstrap nor an invocation-end flush contract. `Dockerfile.lambda:41-88` confirms the
  separate runtime image. Defer Lambda OTel until its OTLP reachability, cold-start idempotence and flush behavior
  have a small deployment-specific design and canary; cleaning its raw logs can be a separate security hotfix.
- Request-scoped provisioning, notification, media, scraper and classification services receive gateway server
  spans plus existing database/HTTP/Redis auto-instrumentation. They get no custom spans until a dashboard, alert
  or incident question proves a missing operation boundary.

**Rules for every Phase 1c task:**

- Use only the merged Utils OTel API and standard `OTEL_*` configuration. Add no exporter, provider, vendor SDK,
  package dependency, product-event write or PostgreSQL telemetry table.
- Preserve signatures, return values, exception/return-error semantics, database writes and scheduling behavior.
  Add no queues, retries, workers or deployment changes.
- Use one span per operation/lifecycle boundary, not per record, chunk or result. Existing automation context is
  the parent when present. Use bounded status/type/count attributes; never record prompt, query, document text,
  object key, local path, event/result body or credentials.
- Tenant identity may appear on traces/logs and only on already-approved bounded metrics. No user/session/chat/
  document/request identifier and no count value becomes a metric label. Prefer span-derived dependency metrics;
  add a new application metric only when its catalogue row names the consuming panel/alert and cardinality bound.
- Do not edit `config.py`, any `pyproject.toml`/lock file, the conflict-zone paths above, or a target file changed
  by the migration after this audit. The detail plan begins with an allowed-path test and a fresh history/diff
  check; any violation stops the affected task.

**Tasks (each gets a failing focused test before implementation):**

- [x] 1c.0 Freeze the allowed-path manifest and approve the Phase 1c signal slice: span name/kind/parent,
      bounded attributes, outcome rules and consuming dashboard for every signal. Recheck target-file history and
      direct imports against the current heads. Detail and verification ledger:
      `docs/plans/observability-rebuild-phase-1c-stable-nonagent.md`.
- [x] 1c.1 Add manual CLIENT spans to the shared S3 and Weaviate wrappers; explicitly mark returned failures;
      remove raw query/key/path values from touched logs. Tests live under `utils/tests/unit/observability/` and
      prove success, raised failure, returned failure, parent propagation and disabled-SDK no-op behavior.
- [x] 1c.2 Add structured MRO startup/shutdown outcome telemetry and complete 0.6a. Do not change health-request
      trace policy, configuration or bootstrap ordering. Test lifecycle success/failure and route absence.
- [x] 1c.3 Add memory operation spans, complete 0.5a for memory, and remove `item_count` as a metric dimension
      while retaining the measurement as a span/log value. Extend the existing memory tests; do not instrument
      every DAO call.
- [x] 1c.4 Add Document Hub processing-attempt and cleanup-sweep spans/context; keep current metrics and remove
      the six dead `document_hub_qna_*` constants only after a zero-call-site test. Extend the existing Document
      Hub processing/cleanup tests.
- [x] 1c.5 Add one Data Discovery job span and bound log context at `run_job`; bootstrap the standalone CLI.
      Test completed, failed, exhausted, already-terminal and invisible-job outcomes without importing or editing
      `data_discovery/agent/**`.
- [x] 1c.6 Add one Improvement run span and bounded child stage spans; structure lifecycle logs without changing
      stage isolation or timer policy. Extend the existing scheduler/runner tests with injected stages only—no
      real model calls.
- [x] 1c.7 Standardize the eight approved parser command resources to `service.name=ingest-parser`, attach
      `parser.kind` to the root span,
      and open one root processing span per invocation. Test the command wrappers without executing real OCR,
      storage or model work.
- [x] 1c.8 Run the phase acceptance topology and safety scans. Record observed output in the Phase 1c detail
      plan; do not mark Lambda, agent/tool/skill paths or production provider delivery covered by this phase.

**Acceptance for Phase 1c:** with in-memory exporters, automation → Document Hub/Data Discovery → S3/Weaviate
forms one trace when invoked through the worker, while standalone jobs/parsers form one root; every failure has an
outcome and correlated content-free log; disabled OTel preserves behavior; forbidden metric labels and raw-content
scans pass; the production diff contains only the allowed paths. A local Collector canary must retrieve at least
one memory, Document Hub, Data Discovery, improvement and parser trace before the phase is called complete.

### 1b-mro — runtime handoff remainder (Stream L, ~~after Gate M + R~~ after Task R; Gate M declared 2026-09-14/15)

The original 1b-mro bucket mixed stable application seams with the changing agent runtime. Those stable tasks are
now Phase 1c. After Task R, this subsection owns only context handoff gaps that cross from the application shell
into the selected Agent SDK/LangGraph runtime and are not already owned by Phase 3.

- [ ] 1b.7 From R.2's approved catalogue, instrument only the gateway/chat-to-runtime handoff needed to preserve
      the incoming server/automation parent and bound identity across the selected runtime. R.4 must name the
      exact post-migration files and prove it does not duplicate Phase 3's `invoke_agent` root.
- [ ] 1b.8 Prove both runtimes inherit the same trace and log context for equivalent request/background entry;
      retire this task as no-op if Task R finds the existing handoff already complete.

**Acceptance for phase 1:** the merged Stream U smoke remains green; Phase 1c's operation topology and safety
checks pass; after Gate M, the Phase 1b runtime handoff proof passes without duplicate roots. Cardinality lint and
the no-legacy-config checks remain green throughout.

---

## 6. Phase 2 — Collector profiles and infrastructure (Stream I, now)

**Files:** `copilot-mro/deployment/otel/base.yaml`, `backend-oss.yaml`, `backend-aws.yaml`,
`backend-azure.yaml` (authored, validated, not deployed), `deployment/otel/README.md`; compose files updated
to mount `base.yaml` + one overlay; `iac/otel_gateway.tf`, `iac/cloudwatch.tf`, `iac/variables.tf` additions;
CI job `otelcol-validate`.

- [ ] 2.1 `base.yaml`: `otlp` receiver (http only, CORS off — browsers never hit it directly; `include_metadata:
      true`), `memory_limiter`, `resourcedetection` (env, system, ec2), `attributes/browser` (`from_context`
      headers → `tenant.id`, `enduser.id`, `session.id`), `transform/genai_aliases` (CLI `claude_code.*` →
      `gen_ai.*` aliases; promote `tenant.id`/`agent.department`/`deployment.environment.name` from resource
      to `claude_code.*` metric datapoints), `redaction` (allow-listed keys; email/token masks), `filter`
      (drop health routes, drop `gen_ai.input/output.messages` on every pipeline except `content`), `batch`.
      Pipelines: `traces`, `metrics`, `logs`, `browser/*` (traces + logs from the ingest headers), `content`
      (traces carrying bodies → Phoenix only). CI: `otelcol validate` for base + each overlay.
- [ ] 2.2 `backend-oss.yaml`: `prometheusremotewrite` → Prometheus (with `deltatocumulative` before it),
      `otlp` → Tempo, `otlphttp` → Loki `/otlp` with the tenant header, and `otlphttp` → Phoenix for `content`
      only when the optional content fragment is enabled (Phase 11.4);
      full `service:` block restated. Compose: Prometheus `--web.enable-remote-write-receiver`, scrape config
      reduced to self.
- [ ] 2.3 Compose smoke test (`copilot-mro/tests/integration/otel/test_oss_profile_smoke.py`, marker-gated):
      start the `oss` stack, send one span, one metric, one log via OTLP/HTTP, assert Tempo/Prometheus/Loki return
      them; assert `job` label = `flynapse/<service>`; assert a delta-temporality counter arrives cumulative.
- [ ] 2.4 `backend-aws.yaml`: three `otlphttp` exporters (logs with `x-aws-log-group`/`x-aws-log-stream`
      headers, traces to `xray.<region>/v1/traces`, metrics to `monitoring.<region>/v1/metrics`) with
      `sigv4auth` ×3; `content` pipeline exporter absent unless a Phoenix endpoint env is set. Validate in CI.
- [ ] 2.5 iac (Flynapse account): collector container on the existing EC2 (`demo_ec2_setup.sh` runs the aws
      overlay only; Loki/Prometheus/Tempo/Grafana containers removed from `deployment/demo/docker-compose.yml`);
      instance role gains the CloudWatch OTLP permissions; Transaction Search enabled (`aws_xray_…` / CLI step
      documented if no resource exists); `aws_cloudwatch_log_group` per service with retention; WAF logging
      configuration; Lambda and App Runner log groups with retention; private DNS name for the gateway
      (`otel.<env>.internal`); App Runner + Lambda env `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel.<env>.internal:4318`.
      Test: `terraform validate` + `plan` in CI; a post-apply probe script sends one OTLP request and checks
      the log group receives it (owner-run; documented in `iac/README`).
- [ ] 2.6 **Deployment deferred:** Terraform module `iac/modules/otel-gateway` for a later client-account
      rollout (ECS task definition + service, task role, log groups, SSM parameters for the overlay env);
      `examples/` with a plan test. Existing artifacts may remain, but Phase 11 does not deploy or expand this
      topology while the approved target is one Docker host per client deployment.
- [ ] 2.7 Probes (spec §12, infra-side): CloudWatch OTel-metrics endpoint GA + temporality; Logs OTLP stored
      field paths; PromQL alarm support in the pinned AWS provider (fallback `awscc`). Results recorded in §9.
- [ ] 2.8 `backend-azure.yaml` authored and validated (`otlphttp` + `azure_auth`, `cumulativetodelta`); no IaC.

**Acceptance for phase 2:** `oss` smoke green; `aws` overlay validated; dev App Runner traffic visible in
CloudWatch Logs/X-Ray/metrics via the EC2-hosted collector; the four OSS containers gone from the demo box.

---

## 7. Phase 3 — LLM and agent observability (Stream L, after Gate M + R)

Detail plan written in R.4 from the approved catalogue. Items known now:
- [ ] 3.1 Rename spans: `agent_sdk.run_query` → `invoke_agent <runtime>` with the spec §6.2 attributes;
      `agent_sdk.tool.<name>` → `execute_tool <name>` with `gen_ai.tool.*`; subagent child spans. Re-bank the
      pinned tests listed in research 05 §7.1.
- [ ] 3.2 Wire `RuntimeTelemetry` from the ledger sink (`record_turn_usage` / `ModelUsage` sink) with the §6.3
      names (`gen_ai.client.operation.duration`, `gen_ai.client.token.usage` + extended token types,
      `agent.model.cost_usd {USD}` + `agent.model.unpriced_calls`, `agent.ledger.write_failures`); retire
      `llm_*` metrics in `utils/llm.py` (keep `embedding_*`).
- [ ] 3.3 LangGraph runtime: `opentelemetry-instrumentation-genai-langchain` under the same root span,
      `NO_CONTENT`; no botocore/anthropic/openai instrumentors (lint test).
- [ ] 3.4 CLI telemetry: `ClaudeAgentOptions(env=…)` in the orchestrator and the SAD runner with the spec §6.4
      env set; stderr callback wired with `CLAUDE_CODE_OTEL_DIAG_STDERR=1`. Test: the env dict is built from
      settings + request context; a fake transport asserts the keys.
- [ ] 3.5 Content capture: `llm_turn_content` table definition (tenant-scoped, RLS, S3 keys + metadata),
      tenant `content_capture` flag (opt-out) on the tenant record, write at the ledger site with
      `redact_sensitive`, owner-run purge script (30 d). Tests: opt-out tenant writes nothing; redaction
      version stamped; RLS boot check passes.
- [ ] 3.6 Sampled OTLP copy to the `content` pipeline (attributes `gen_ai.input.messages`/`output.messages`),
      sampling rate env, honours the opt-out. Test: flag off → no content attributes on the span.
- [ ] 3.7 `chat_turn_facts` writer on the block-save path (same transaction), from the pipeline result and
      `ChatBlock` metadata (spec §7.2). Test: a saved block yields exactly one facts row; a failed turn yields
      none and `llm_usage` still books.

---

## 8. Phase 4 — Frontend telemetry (Stream F, now; switch-over waits for 5.5)

**Files:** `dashboard/lib/telemetry/{provider.ts,exporter.ts,events.ts,session.ts,web-vitals.ts,errors.ts}`
(new), `instrumentation.ts` deferred; `components/providers/LoggingProvider.tsx` replaced by
`TelemetryProvider.tsx`; `lib/logging/**` deleted after cut-over; `amplify.yml` untouched (the browser
posts to the api). Tests under `dashboard/tests/unit/telemetry/`.

- [ ] 4.1 Catalogue review gate: owner reviews research 07 Part 3; rulings recorded in §9; the approved list
      becomes `events.ts` (typed event names, attribute schemas, sampling per event).
- [ ] 4.2 OTel JS 2.x upgrade (`@opentelemetry/sdk-trace-web`, `instrumentation-fetch`, `-xml-http-request`,
      `-document-load`, `web-vitals 6`); probe Node ≥ 18.19 on the Amplify build image (§12). Test: `npm run
      typecheck` + `npm test` green.
- [ ] 4.3 `exporter.ts`: OTLP/JSON exporter over the authenticated fetch helper with the wedge designed out
      (4xx → drop + `browser.telemetry.dropped` counter; 5xx/network → bounded backoff then drop; hard queue cap
      with oldest-first eviction; `visibilitychange`/`pagehide` best-effort flush). Tests: the wedge replay
      (one bad batch then good ones ship); cap eviction; 4xx not retried.
- [ ] 4.4 `provider.ts`: `WebTracerProvider` with the resource (`service.name=dashboard`, version, env),
      fetch/XHR spans head-sampled 10%, `propagateTraceHeaderCorsUrls` = API origin only, `session.id` from
      `getSessionId()`. Tests: sampling ratio applied; no `traceparent` on a third-party URL.
- [ ] 4.5 `web-vitals.ts` and `errors.ts`: vitals as log records (`event.name=browser.web_vital`), errors from
      the boundary, window error, unhandled rejection, resource error, plus the 10 `error.tsx` segment
      boundaries. Tests: each source produces one record with the schema from `events.ts`.
- [ ] 4.6 Catalogue emitters at the 7 choke points of research 07 Part 4 (API wrapper, router, provider
      root, TanStack `MutationCache` via `mutation.meta`, chat stream hook, `DocumentCard`, PDF viewer), MUST
      events first. Tests per choke point with a fake exporter.
- [ ] 4.7 Product events client: `postProductEvents(batch)` to `/analytics/events` (typed, ≤50), used by
      `document_opened`/`document_closed`/`session_*`/`clarification_answered`/`upload_finished` emitters.
      Test: schema validation and batching.
- [ ] 4.8 Wrapper for `logger.*`: `warn`/`error`/`fatal` → OTel log records; `info`/`debug` → console in dev,
      dropped in prod (ruling 16). Test: prod mode emits nothing for `info`.
- [ ] 4.9 Cut-over: point the exporter at the evolved ingest routes (5.5), delete `lib/logging/**` and the
      old provider, remove `OTEL_EXPORTER_OTLP_ENDPOINT` from `runtime-config.ts`. Test: no reference to the
      old module remains (lint); ErrorBoundary copy states what is delivered.

**Acceptance for phase 4:** in the POC stack, a browser session produces vitals, one error, route timings,
fetch spans linked to backend traces, and `document_opened` rows in `product_events`; the wedge test is green.

---

## 9. Phase 5 — Product analytics rebuild (Stream P, now)

**Files:** `core/core/resources/analytics/{registry.py,panels/*.py,repository.py,events_endpoints.py,schemas.py}`
(new/rewritten), `analytics_endpoints.py` (kept contract), `services/chat_quality_service.py` deleted;
`core/core/resources/logging/logging_endpoints.py` evolved (5.5); table definitions:
`core/core/db/table_definitions.py` (`product_events`), `copilot-mro/.../postgres_table_definitions_modules/chat.py`
(indexes), new `chat_turn_facts.py` module; `dashboard/app/(dashboard)/settings/department/dashboard/**` and
`lib/api/analytics-api.ts` rebuilt; `scripts/backfill_chat_turn_facts.py` (owner-run). Tests under
`core/tests/api/analytics/`, `core/tests/db/analytics/`, `dashboard/tests/unit/analytics/`.

- [ ] 5.1 Storage: indexes `chat_blocks (tenant_id, block_timestamp)`, `chat_feedback (tenant_id, created_at)`,
      `comments (tenant_id, created_at)`; `product_events` definition (spec §7.2 columns, allow-listed names
      incl. `clarification_answered`, `upload_finished`); `chat_turn_facts` definition (no writer yet).
      Tests: DDL single-source tests extended; RLS boot check green; index names verified.
- [ ] 5.2 Grants: `flynapse_readonly` SELECT on the analytics relations (provisioning script addition, owner-run);
      Grafana Postgres datasource in the `oss` profile uses it. Test: provisioning report lists the grants.
- [ ] 5.3 Panel registry + repository: `PanelSpec(id, sql_builder, aggregator, filters, requires)`; SQL runs
      under the request's tenancy binding via `PostgresService`; owner binds the full operator roster, capability
      holders stay entitlement-scoped (ruling 9), with `scope_note` in the response; money tiles return
      `unpriced_count` beside every USD sum. Panels: the 10 rebuilt (spec §7.3) + Usage/Quality/Cost/
      Reliability/Operations/Improvement views. Tests: one seeded-DB test per panel (two tenants, assert
      isolation and the numbers); envelope compatibility test against the existing TS types.
- [ ] 5.4 `POST /analytics/events`: typed batch (≤50), allow-listed names, server-side tenant/user stamping,
      re-emit as OTel log records; 60 rpm per user. Tests: schema, quarantine of client-supplied tenant ids,
      rate limit, one row per event.
- [ ] 5.5 Ingest evolution (ruling 3): `/logging/ingest` and `/logging/public/ingest` accept OTLP JSON on
      `/v1/logs` and `/v1/traces` sub-paths, enforce size/rate limits, stamp `X-Tenant-Id`/`X-User-Id`/
      `X-Session-Id`, forward opaque to the collector; loguru re-logging removed; the three-route test re-banked.
      Tests: pass-through body equality; anonymous route stamps the sentinel; oversize → 413.
- [ ] 5.6 Backfill script for `chat_turn_facts` from `chat_blocks.block_data` (idempotent, re-runnable, uses
      `flynapse_readonly` for reads and the owner role for writes; scheduled daily until the writer lands in 3.7).
      Test: fixture blocks → expected facts rows; second run is a no-op.
- [ ] 5.7 Dashboard page rebuild: tabs per spec §7.3 (Improvement tab owners-only, after the finding-body
      review task 5.8), typed error states (rate-limited / unavailable / empty), `3m` range, unpriced footnote on
      money tiles, scope note on operator-scoped tiles, refresh button. Tests: render per panel variant; error
      state mapping; owner-vs-capability scope note.
- [ ] 5.8 One-time review of existing `improvement_findings` bodies for internal references (owner + Claude
      report); findings stay hidden from the tab until the report is accepted.
- [ ] 5.9 Delete `chat_quality_service.py`, `LOKI_BASE_URL`, LogQL constants and the Loki tests; grep-test that
      `core` has no Loki reference.

**Acceptance for phase 5:** every tab renders against a seeded two-tenant DB with correct isolation; the old
Loki path is gone; `product_events` rows arrive from the frontend (with phase 4) or from a curl in tests.

---

## 10. Phase 6 — Dashboards, alerts, runbooks (Stream D)

- [ ] 6.1 Six-view catalogue file `deployment/otel/dashboards/CATALOGUE.md` (name, question, signals, per-backend
      query notes) — the shared spec for both dialects.
- [ ] 6.2 Grafana JSON for `oss` (service overview, dependencies, LLM & agents, agent turn explorer, frontend,
      platform health) provisioned from the repo; Postgres datasource panels via `flynapse_readonly`. Test:
      JSON schema check + a datasource-uid lint in CI; smoke loads each dashboard via the Grafana API.
- [ ] 6.3 Prometheus rule YAML for the spec §9.4 alerts; contact points Slack + email with placeholder
      targets until the owner supplies them (ruling 19). Test: `promtool check rules`.
- [ ] 6.4 CloudWatch: Terraform dashboards (six bodies), PromQL alarms or the fallback from 2.7, SNS topic →
      Slack webhook + email. Test: `terraform validate`; a plan diff review.
- [ ] 6.5 Runbooks: `docs/runbooks/observability/{oss-profile,aws-profile,alerts}.md` (how to switch profile,
      rotate secrets, read a trace, answer "what did tenant X spend").
- [ ] 6.6 Delete the eight legacy dashboards and `test-observability.py`.

---

## 11. Phase 7 — LLM evals workbench (Stream E)

- [ ] 7.1 Phoenix container available as an **optional** addition to the `oss` profile (existing Postgres, auth
      on, retention env, one project per tenant + `internal`); client-account variant in the `otel-gateway`
      module remains optional. Phase 11.4 owns removal of the current mandatory compose coupling.
      Test: compose smoke sends one `invoke_agent` trace through the `content` pipeline and finds it in Phoenix.
- [ ] 7.2 Attribute-mapping probe (spec §12): our `gen_ai.*` span → Phoenix renders model, tokens, cost, tools;
      add OpenInference aliases to `transform/genai_aliases` where needed.
- [ ] 7.3 `eval_results` table (tenant-scoped): `profile`, `registry_revision`, `department`, `golden_set_id`,
      `judge_version`, `metric`, `score`, `run_id`, `created_at`; written by the harness; read via
      `flynapse_readonly` for reports. Tests: DDL + RLS checks; one seeded query "v2 vs v1".
- [ ] 7.4 Harness → Phoenix: the e2e/eval harness (`tests/e2e/*`) pushes datasets and experiment runs with judge
      scores keyed by the ledger's `profile` + `registry_revision`. Test: dry-run mode produces the payload
      without a Phoenix endpoint.
- [ ] 7.5 Per-tenant quality report generator (markdown/PDF via the existing doc-render helper): accuracy, answer
      rate, regressions across versions, cost per query — the client-review artefact. Test: fixture results →
      deterministic report.
- [ ] 7.6 Sampled production copy honouring the opt-out (from 3.6) reaches the tenant's Phoenix project only in
      the same account (data residency, spec §6.5). Test: cross-account exporter config is refused by the
      overlay validation.

---

## 11a. Standing rules for every task (owner requests, 2026-09-05)
- **Logging completeness along the way.** Whenever a task touches a module, the implementer checks that
  module's logging and fixes what is incomplete in the same task: every failure path logs at the right
  level with the bound context (`tenant_id`, `request_id`, ids of the entity involved), no silent
  `except: pass`, no user content in log fields, structured kwargs instead of interpolated prose,
  `logging.getLogger()` users covered by the intercept, and one log line per lifecycle boundary
  (start/finish/fail) for background work. Each detail-plan task carries a "logging coverage" checkbox; the
  phase-close review verifies it. Gaps too large for the task go to **Future Improvements** with a note.
- **Latest stable images, pinned.** Every observability container (Grafana, Loki, Tempo, Prometheus, the
  collector, Phoenix) runs the latest stable release at the time a task pins it; versions live in
  `deployment/otel/VERSIONS.md` with a monthly bump check (task 0.1).
- **Dashboards are in scope.** Phase 6 rebuilds the Grafana dashboard set (six views replacing the eight
  legacy boards) and their CloudWatch equivalents; it is not a separate project.

## 11b. Phase 8 — Satellite services + shared OTel package (opened 2026-09-10)

Owner request while Gate M is still closed: bring `telegram-bot` and `shift-optimizer` (spec §10 "later
services") onto the §3.1 contract now — traces, metrics, logs, Grafana **and** CloudWatch dashboards for both,
plus the spec §7.3 deferred **optimizer** product tab. Owner rulings: the shared implementation is **extracted
into a lean `flynapse-otel` package** (new sibling repo; `utils.observability` becomes a re-export shim) so the
bot never depends on `utils`; Telegram = plumbing + existing counters as OTel metrics + dashboards (no frontend);
optimizer = backend signals + product tab; streams in parallel on Opus, with a **second review phase on Fable**
in five bounded chunks (Sunday night 2026-09-13) — **no merge before that gate**. The shared `api/.venv`
refresh becomes a merge-time precondition. Detail plan: `observability-rebuild-phase-8-satellite-services.md`
(streams O / S / PA8 / D8 / T, pinned signal catalogue, review design, live probe).

## 11c. Phase 9 — Dashboard telemetry completion (opened 2026-09-11)

Owner request after the 2026-09-11 dashboard audit ("is the dashboard repo complete from a metrics, tracing, and
logging perspective?" — no: the browser pipeline is sound, but URL/email leaks, dead correlation, a dark Next.js
server hop and uncovered product areas remain): address every gap **except Rostering** (a demo prototype); an
independent agent reviews the plan before the build; **Fable reviews the design and all code when its limit
returns — no merge before that gate** (the phase-8 rule). Four parallel Opus streams off the current mainlines —
**F9** browser correctness + correlation (dashboard + the api CORS headers), **E9** event coverage (seven catalogue
events incl. the five phase-4 LATER rows, #19 completion), **N9** Next.js server side (trace forwarding, structured
server log lines, `onRequestError`), **M9** collector allow-list + log-body masking, Tempo endpoint dimensions and
`fn-frontend` panels in both dialects (aws browser alarms documented; their Terraform waits for the owner's alarm-dialect ruling) — then **P9**, one live probe on a
local integration tree that also retires the frontend board's DARK labels. Fable chunks R6 (design) → RC (the owner's TanStack useMutation conversion, Fable-gated too, merged into `agent_sdk` first) → R7–R10 follow
the phase-8 chunks. Detail plan: `observability-rebuild-phase-9-dashboard-telemetry-completion.md` (gap register §0,
pinned catalogue §2, decisions D9-1…D9-16 in §8a).

## 11d. Phase 10 — Owner follow-ups (opened 2026-09-14)

Owner request after the post-gate "what's left" answer: pick nine items, "design and plan them. we build and review
using opus and post that fable reviews". Items: response validation at the dashboard API layer; the `/rag/stream`
final-before-save race (built AND merged — Gate M declared, §2); alert thresholds + real Slack/email targets; the
Document Hub double `document_opened`; the CloudWatch alarm dialect (ruled: `hashicorp/aws ~> 6.42`); the worktree
`next build` trap (a config guard — research showed `outputFileTracingRoot` does not close it); per-project smoke
networks; `service.version` estate-wide; the RLS re-run on `shift_optimizer_test` plus a self-healing test-DB
preflight. Six Opus streams (V10 dashboard, W10 chat write path, K10 oss alerting + smoke, A10 aws alarms, S10
service version, L10 RLS lane), an Opus adversarial review each, then Fable chunks R12–R16 with a merge after each
verdict. Detail plan: `observability-rebuild-phase-10-owner-follow-ups.md` (item register §0, pins §2).

## 11e. Phase 11 — Audit follow-ups and production readiness (Stream A; arrived as "Phase 8", renumbered 2026-09-20)

Detail plan: `docs/plans/observability-rebuild-phase-11-audit-followups.md`. Written on
`origin/obs-telemetry-merge` as **Phase 8** and renumbered to **11** at the 2026-09-20 fold: §11b's Phase 8
(satellite services) landed on our mainline while that branch was live, so two phases carried the same number
and two detail plans carried the same filename stem. Their Phase **1c** keeps its number — see §5 — because
nothing of ours claims 1c; it is a re-cut of our gated 1b.7/1b.8, recorded there.

This phase contains only the remaining audit deltas and cross-phase proof. It does not reopen the accepted
two-contract architecture or duplicate ownership already assigned to Phase 3.

- [x] 11.0 Reconcile the master plan and audit against the latest checked-out branches; declare Gate M only from
      current evidence and write the post-migration rescoping record. **Its answer ("Gate M cannot be
      declared") was wrong by 2026-09-14/15** — see §2, §14 and §15.
- [x] 11.1 Add stable browser-created product `event_id`, `schema_version`, tenant-scoped idempotent insertion,
      and accepted-versus-duplicate reporting while preserving old-client compatibility.
- [x] 11.2 Add a server-owned per-client Flynapse UI dashboard profile. Effective panels are the configured
      client panels intersected with supported panels, tenant features and authenticated role permissions.
- [ ] 11.3 ~~After Gate M + Task R,~~ **after Task R**, close the Phase 3.7 `chat_turn_facts` writer and prove
      Agent SDK/LangGraph fact, ledger and telemetry parity without adding a second writer. The writer is
      carried as G.5 in `docs/plans/observability-telemetry-merge-and-completion.md`; the backfill **schedule**
      was dropped by the owner 2026-09-19, so the online writer is the sole populator and there is nothing to
      reconcile a timer against.
- [x] 11.4 Make Phoenix optional in the current single-host Docker POC. Keep the separate native services;
      `otel-lgtm` evaluation is deferred.
- [ ] 11.5 Add the New Relic Collector profile, production queue/retry persistence, retrieved canaries for every
      provider claimed supported, and an explicit Azure production-support go/no-go gate.
      Config-only implementation and the provider catalogue matrix are complete in `copilot-mro` branch
      `obs-telemetry-merge`; fresh non-container tests passed profile composition, env documentation,
      destination-swap/static contracts and metric-cardinality checks. Live provider canaries, provider-specific
      field-path evidence and file-queue restart proof remain. ~~Azure is marked production `NO-GO` while
      Microsoft's Collector OTLP path remains Preview.~~ **Corrected 2026-09-20:** no `NO-GO` marker exists in
      the merged tree; `deployment/otel/README.md` records `backend-azure.yaml` as "authored + validated, not
      deployed", which is §2.8's status and not a support ruling. The go/no-go gate is still owed.
- [ ] 11.6 After Phase 1c plus the gated Phase 0 chat cleanup, Phase 1b runtime handoff and required Phase 3 work
      are complete, run the final tenant-isolation, dashboard-profile, runtime-parity, Docker-resource and
      destination-swap acceptance matrix; close only claims backed by runtime evidence.

**Acceptance for phase 11:** product-event retries do not double-count; the same Flynapse UI build renders a
server-controlled view set per client; ordinary clients never need an external observability UI; Phoenix is
optional; a supported production destination is selected without application business-code changes; every
production-support claim includes a retrieved trace, metric and log canary.

**Where the merge overruled them.** Phase 11's Task 5 removed the Grafana `flynapse-postgres` datasource and
the two `fn-llm-agents` exact-spend panels; ruling **M-GRAFANA** keeps both and refuses `deleteDatasources`.
Phase 11's acceptance harness (`deployment/observability-acceptance/**`) is dropped by **M-ACCEPT**. The
rulings live in `docs/plans/observability-telemetry-merge-and-completion.md` §4.

## 12. Review protocol (every phase)
1. Detail plan written at phase start (test-first tasks); owner reviews it.
2. Implementer agent per worktree (Opus for mechanical/enumerated work, Fable for design-heavy or merge-sensitive
   work); tests written with the code; targeted `pytest`/`npm test`/`terraform validate` per task.
3. Phase close: independent adversarial review subagent briefed with the phase scope + the diff; findings
   triaged (real gap → fix now; deferred → **Future Improvements** below with reasoning).
4. Implementation notes and learnings recorded per phase in this file as work lands; user corrections go to
   **Lessons**.
5. Rebase app-dependent branches on each migration merge; re-run the phase's test cycle after rebase.

## 13. Probes checklist (spec §12)
| Probe | When | Fallback |
|---|---|---|
| POC `.env`: `LOKI_BASE_URL` unset (G29) | before 5.7 | none needed — P replaces the page |
| CloudWatch OTel-metrics OTLP GA + temporality | 2.7 | `prometheusremotewrite` → AMP |
| CloudWatch Logs OTLP stored field paths | 2.7 | adjust Logs Insights queries |
| Application Signals from vanilla SDK spans | 2.5 | RED alarms only, no SLO objects |
| PromQL alarms in the pinned AWS provider | 2.7 | `awscc` provider / SLO alarms |
| Amplify WEB_COMPUTE → private api reachability; Node ≥ 18.19 on the build image | 4.2 | SSR telemetry stays out |
| Pooled psycopg2 query → span with bootstrap ordering | 1b.1 | reorder pool creation |
| Phoenix `gen_ai.*` rendering | 7.2 | collector aliases |
| Azure OTLP send + metric naming | only when `azure` is built | — |
| Phase 8 satellites: bot trace continues into the api SERVER span; optimizer run trace links to its request; `telegram-bot`/`shift-optimizer` boards render; `http_client_request_duration_seconds{server_address="api.telegram.org"}` present; no token/presigned URL in the Loki raw stream after a deliberate bad-token boot; no `getUpdates` CLIENT span in Tempo | after the phase-8 R5 merge (phase-8 plan §10) | fix per finding before calling phase 8 done |
| Phase 9 dashboard completion: no query/token in any browser span or record; masked email in browser + backend log bodies; toast/fallback Reference opens its trace; Next route hop keeps the browser → api trace; first-load request traced; the seven new events in Loki; span metrics carry `url_template` | P9 on the integration tree (phase-9 plan §7), before the Fable gate; checks 2/4/5 again after the R10 merge | fix per finding before calling phase 9 done |
| Product-event retry returns one row plus a duplicate count | 11.1 | keep compatibility values for old clients; do not route through Collector |
| Per-client Flynapse UI profile intersection | 11.2 | fail closed to the safe default and retain endpoint authorization |
| New Relic trace/metric/log retrieval | 11.5 | do not claim production support until the canary is retrieved |
| Azure production-support status | 11.5 | supported bridge or `NO-GO` if the required direct path lacks an acceptable support commitment |
| Collector file-backed queue restart | 11.5 | provider remains not production-ready until durability passes |

## 14. Rescoping notes (filled at Task R)

**Task R's starting baseline is research 08, with its central finding corrected (folded 2026-09-20).**
`docs/plans/observability-rebuild-research/08-post-migration-rescoping.md` is the file-level inventory Task R
starts from: branch/HEAD table, the operational-telemetry and product-record current state, and a per-phase
status reconciliation. It arrived from `origin/obs-telemetry-merge` and **its central finding is wrong** —
see the correction banner at the head of that file. Read it as a current-state inventory, not as a gate ruling.

**Correction: Gate M is DECLARED.** Both notes below conclude Gate M is closed. It was declared by the owner on
**2026-09-14/15** — "langraph migration is done. so we can build and moerge now." — recorded in §2, in the §15
ledger and in `observability-rebuild-phase-10-owner-follow-ups.md`. Their branch was cut before that date and
looked for the declaration only in docs reachable from the branch, which is why it could not find it. Every
deferral below that rests on "Gate M is closed" is void; what is genuinely owed is **Task R**, which is
unblocked and unstarted, and which the merge plan carries as **G.1**, widened to an estate-wide coverage audit.

**Correction: the `chat_turn_facts` backfill schedule is DROPPED.** The owner dropped it on 2026-09-19. The
online writer (merge plan G.5) is the sole populator; `core/scripts/backfill_chat_turn_facts.py` remains
available for a one-off reconciliation and is scheduled nowhere. Anything below that treats the backfill as
"the current writer" or asks for online/backfill agreement on a timer is describing a schedule that no longer
exists.

**Their pre-gate Task 11.0 baseline (2026-09-08), as written:**
research 08 records the current branches and the Phase 11 starting state. It finds both runtime adapters
present but does ~~not declare Gate M: migration Batch 5, the post-Batch-5 fuse/judge parity slice and the
owner's explicit stability declaration remain~~ — **corrected above; Gate M was declared 2026-09-14/15**. This
is not R.1 completion; R.1-R.4 remain unchecked and must refresh the runtime inventory.

**Their Task 4 reassessment (2026-09-17, documentation-only), as written:**
The old Batch 5 and post-Batch-5 parity blockers are stale: the Copilot MRO S4 status now records Phase 5 closed
with tools 56/56, skills 18/18 and manifest 0, and the runtime divergence register records R-PAR-2 closed and
merged. ~~Gate M still remains **closed** because the required owner declaration has not been recorded: no
tracked doc states that no further batch is expected to touch the conflict zone during Stream L.~~ **Wrong —
the declaration exists, dated 2026-09-14/15, on a mainline this branch predates.** Task R also remains
unrun: R.1-R.4 are still unchecked, and no approved post-merge runtime signal catalogue exists. Current owners:
~~the runtime migration owner owns the Gate M declaration;~~ the observability workstream owner owns Task R runtime
inventory/catalogue execution and approval; the Phase 3.7 writer implementation owner owns the sole online
`chat_turn_facts` writer. Current code evidence also keeps Phase 3.7 pending: the selected Claude/LangGraph
runtimes converge before the route persistence boundary through `get_agent_pipeline()`, non-streaming `/rag`
saves the built chat block synchronously before return, and `/rag/stream` queues `final` before starting a
timeout-bounded background `save_block` whose failure does not change the client response. A future sole writer
inside `save_block` can cover both database transactions, but the block-save transaction does not yet insert or
upsert a facts row — **re-verified 2026-09-20 on the merged tree: `copilot_mro/app/db/chat_history/blocks.py`
still holds no `chat_turn_facts` write.** Next decision point: ~~record Gate M explicitly, then~~ dispatch
Task R before any writer implementation.

**Attribute and outcome vocabulary, for R.2.** The catalogue R.2 has to approve now has two competing outcome
spellings and a set of span attributes no document named before this merge. Both are enumerated, with the
ruling and its reasoning, in
`docs/plans/observability-rebuild-research/09-outcome-and-span-attribute-reconciliation.md`.

## 15. Implementation notes / Learnings (per phase, filled as work lands)

The task checkboxes in the original phase sections preserve their planned scope and sequencing. For current
status, use the dated ledger below and the Task 11.0 file-level baseline rather than inferring implementation from
an old unchecked box or from plan text alone.

**2026-09-05 — execution kicked off (planning step).** Owner rulings: all four app-independent streams
start now, subagent-driven, up to 8 agents this session, Opus or Fable 5 by complexity. Four planner agents
are writing the detail plans (`observability-rebuild-phase-{0-2-infra,1-utils-api,5-analytics,4-frontend}.md`);
none has landed yet. Mid-flight additions already sent to the planners: per-tab permission gating (spec
§7.1), the §11a standing rules (latest stable images pinned + `VERSIONS.md`; logging coverage checkbox per
task). Next: review each detail plan as it lands (spec coverage, placeholder scan, conflict-zone check),
then dispatch one implementer per worktree; Stream F's 4.1 catalogue review is an owner gate (the owner has
seen the event summary; no trims requested yet). Migration status at kickoff: batch 1 merged into
`langgraph-merge`; batch 2 active in `copilot-mro-s41` (`s44-batch2-lang`) and `copilot-mro-s44b2`; Gate M
not near.

- **2026-09-05 — detail plans landed, implementers dispatched.** The four planners ran as read-only agents and
  returned their plans as text; the session lead wrote and committed them. Landed: phase 5 analytics (amended:
  D3a per-panel capability gating on both sides per spec §7.1; a logging-coverage checkbox per task; the browser
  ingest forward targets the collector's browser receiver on port 4319 via `OTEL_BROWSER_FORWARD_ENDPOINT`;
  `sessions_over_time` reads the last `session_ended` row per session), phase 0–2 infra (amended:
  `attributes/browser_identity` upserts; the 4319 contract), phase 4 frontend (amended: the 4.1 gate is cleared
  by the owner's in-session review of the 25-event summary — MUST+SHOULD approved, the five LATER rows out of v1;
  the product-events body follows phase 5 D5/D6 with no `session_id`/`tenant_id`/`user_id` in the body).
  Implementers running in their worktrees: P backend (`core-obs`, Fable 5), P frontend
  (`dashboard-obs-analytics`, Opus), I (`copilot-mro-obs-infra` + `iac-obs`, Fable 5), F
  (`dashboard-obs-frontend`, F0–F9, Fable 5; F10 waits for 5.5 + the rebase). Phase 1 (utils/api) plan landed too (amended: the gateway
  excludes the four browser-ingest routes from its own spans/metrics; task U16 adds the anonymous ingest
  sub-paths to the auth skip list; master 0.6's gateway half — `/metrics` redirect, `metrics_scrape.py`,
  `METRICS_SCRAPE_TOKEN`, `prometheus-client` in api — is folded into U11, the copilot-mro half stays with
  Stream L; session-lead defaults D1 single mount-aware gateway instrumentation instead of per-sub-app
  `instrument_app`, D6 semconv identity keys on the wire, D7 readiness = Postgres hard, D10 no `-fastapi`/
  `-logging` packages) and its implementer runs in `utils-obs` + `wt-obs-u/api` (Fable 5). Session-lead defaults taken while the owner was away are listed under each plan's "Open
  questions" (chat_turn_facts gains `tool_usage`/tool-set `route`; authenticated ingest limits 256 KiB / 200
  records / 120 rpm; no `llm_model_calls` rollup this phase; export-time deterministic 10% ratio drop for browser
  fetch spans so the sampled flag always propagates).

**2026-09-05 — Phase 1 (Stream U, utils + api) COMPLETE.** U0–U16 landed in `utils-obs`
(`obs-utils`, 10 commits to `62b99ff`) and `wt-obs-u/api` (`obs-api`, 8 commits to `2a00a58`);
utils suite 1076 green, api 1079 green (`-m "not postgres"`; 4 pre-existing/environmental
skips), the `-m postgres` pooled-query span probe PASSES. Deviations recorded for the owner
(details in the phase plan): **D1** one mount-aware gateway `OpenTelemetryMiddleware` instead
of per-sub-app `instrument_app` — full `http.route` on span AND duration metric, 401/403s do
carry a span (counter still emitted); **D6** identity log keys renamed on the wire
(`tenant.id`/`enduser.id`/`session.id`/`request.id`); **D10** `-fastapi`/`-logging` not
added; 1b.4 attributes bound from `LoggingContextMiddleware`, not a `server_request_hook`;
the pool is LAZY (`_ensure_pool` on first query) — the enforced invariant is "bootstrap before
the first pooled query", and making it hold required a real fix in `utils/postgres_service.py`
(per-cursor `RealDictCursor` bypassed the instrumentor's traced factory; now wrapped).
SDK-1.44 facts for other streams: log code attributes are the NEW spellings
(`code.function.name`/`code.file.path`/`code.line.number`) — Stream I's redaction allow-list
and Phase 6 dashboards must use them; `InMemoryLogRecordExporter` replaces the deprecated
`InMemoryLogExporter`. Master 0.6's gateway half is DONE (route, `metrics_scrape.py`, token
readers, `prometheus-client` all gone from api; at that date the copilot-mro half stayed with Stream L, and the
2026-09-08 review later split its stable non-agent portion into Phase 1c).
Local dev without a collector: `OTEL_SDK_DISABLED=true` (`OTEL_ENABLED` is no longer read
anywhere in utils/api).

**2026-09-05 — Phase 6 (Stream D, dashboards/alerts/runbooks) COMPLETE, both worktrees.**
Detail plan `observability-rebuild-phase-6-dashboards.md` (per-task notes in its §11). obs-infra
`1ec25b9c..394e0d89` (9 commits, T1–T9), iac-obs `0acbf10`+`44fc0db` (T10–T11); T12 verification
clean (no alarm resources anywhere). Full otel lane **70 passed** with both compose smokes and
docker-gated promtool/amtool; `terraform validate` green. Landed: the six-view catalogue + alarm
translation table (`deployment/otel/dashboards/CATALOGUE.md`); six provisioned Grafana views
(`fn-*`, folder `Flynapse`, legacy provider + eight boards + `test-observability.py` deleted in
the working tree); 10 Prometheus alerts + 5 Loki-ruler alerts (Alertmanager v0.34.0, loopback,
`_file` placeholder secrets per ruling 19); `validate-rules.sh` + `rules-validate` workflow;
three runbooks with guard-enforced per-alert anchors; six CloudWatch dashboard bodies + the
SNS/email/Slack-forwarder seam. **Learnings for other streams:** (1) collector 0.160.0's `:8888`
internal telemetry exports WITHOUT `_total` (`otelcol_receiver_accepted_spans`,
`otelcol_exporter_sent_spans`, …) — verified live; Stream L must not assume `_total` on otelcol
series, and the send_failed family is lazily created (absent until the first failure). (2) The
error outcome in the `agent_turn_calls_total` rules is assumed spelled `agent_outcome="error"` —
Stream L must confirm or the AgentTurnFailureRatioHigh expression needs a one-line retune.
(3) Loki ingest counters (`loki_distributor_bytes_received_total`) are also lazily created.
(4) The observe stack's host bind data dirs are root-owned on a fresh checkout and crash-loop
all non-root backends — the tmpfs smoke overrides are the reliable boot path. Deviation from
master §12: the session brief forbade subagents, so the independent adversarial review of phase
6 is still OWED (owner or a fresh agent; brief it with the detail plan + both diffs). Owner
steps queued in the detail plan §10: alarm dialect ruling, threshold review, real alert targets,
PromQL widget console export, Stream L counter hand-off.

- **2026-09-05 — BUILD PHASE COMPLETE: all six streams closed MERGE-READY after adversarial review + fix
  passes.** Verdicts: P dashboard (review clean, 42 panels), P backend (2768 green; facts drift-pin landed),
  Stream I (5-test live smoke incl. the 4319 identity-upsert case), Stream U (tracer property restored; any-order
  merge via the transitional skip entry), Stream F (session-attribution fix verified await-free on the code
  path; 1747 green; F10 gated), Phase 6 (series names verified against live producers; suffixless `otelcol_*`
  confirmed empirically; CI green from a `git archive` simulation). Every stream's detail plan carries its
  Implementation notes, review triage, and uncommitted-edit ledger.

  **Merge sequence (owner-driven; each merge must also land that worktree's LEDGERED UNCOMMITTED EDITS —
  a rebase/merge carries only commits):**
  1. utils `obs-utils` → `langgraph-merge`; api `obs-api` → `langgraph-merge` (any order vs core now; AFTER
     core's routes are live, delete the transitional `/logging/public/ingest` skip entry + its test pin).
  2. core `obs-analytics` → `master` (then the api transitional-entry deletion above becomes due).
  3. copilot-mro `obs-infra` → `langgraph-merge` (demo box pulls `main` — it only picks the new stack up when
     `main` receives it); apply the Stream P patch `stream-p-copilot-mro.patch` (foreign hunk already stripped)
     to the same branch.
  4. dashboard: `obs-analytics` → `agent_sdk` first (hand-carry its 7 uncommitted files incl. the typed-error
     `fetch-utils.ts`), then `obs-frontend` REBASED onto it (zero file overlap verified), then task 4.9/F10
     (cut-over) once core 5.5 is merged/deployed.
  5. iac `obs-iac` → `main` (MUST include the uncommitted `variables.tf` delta or root validate fails); then
     the Terraform owner sequence from `iac-obs/README.md`: B2 plan (SG removals only) → B3 plan/apply (demo
     instance is REPLACED; Weaviate EBS survives) → B4 with 4 log-group imports → B5 Transaction Search toggle
     → B6/B7/B8 → `scripts/otel_probe.sh`.
  6. Post-merge tasks now un-gated: A14 (delete legacy `OTEL_ENDPOINT` lines) after obs-utils lands.

  **Owner checklist (accumulated):** Weaviate pin from the live digest + Portainer keep/delete; Amplify AL2023
  image + Node 22 pin; improvement-findings review script → then `ANALYTICS_IMPROVEMENT_TAB_ENABLED=true`;
  chat_turn_facts backfill crontab (line in the phase-5 plan); alert-threshold review (phase-6 plan §10.2) +
  real Slack/email targets via `ALERTMANAGER_*_FILE`/SSM; CloudWatch alarm-dialect ruling (provider raise vs
  `awscc` vs defer); B1a/B1b/B1d live probes; PromQL widget console-export probe; POC acceptance run at F10.
  Phase 8 (2026-09-11): `flynapse-otel` GitHub repo CREATED + pushed (private, `main` @ ed5f739); still owed: its CI
  secrets, first CodeArtifact publish, flip
  the utils dependency to the `codeartifact` source at publish time; re-run `provision_rls.py` against the local
  `shift_optimizer_test` DB (utils' `rls_boot_check` fails on stale memory-item policies → 62 optimizer `tests/api`
  setup errors, pre-existing).
  **Owner rulings open:** phase-8 D-11 (the gateway records HTTP duration after BackgroundTasks) and D-12 (optimizer
  run attribution from an unsent, spoofable `X-User` header) — Fable R0 recommends, owner rules; ~~hub-citation
  double-surface (one gesture = two `document_opened` rows)~~ CLOSED 2026-09-15 by phase 10 Task 2 (D10-6: the preview
  dialog owns the fact for every opener; merged into dashboard `agent_sdk` as `0bc5429` after Fable gate R13); Gate M
  declaration when LangGraph lands → Task R rescoping → Stream L (phase 0 app half, 1b-mro, phase 3, the
  `chat_turn_facts` writer, content capture) + phase 7 eval harness; Stream L must also confirm the
  `agent_outcome="error"` spelling + doc-hub/automation counters the dark phase-6 panels assume.

- **2026-09-05 — MERGES EXECUTED (session lead).** All six repos merged with their ledgered uncommitted edits
  landed as explicit commits on each stream branch first: utils `obs-utils` → `langgraph-merge` (the main
  checkout's two unrelated dirty files protected via tagged stash, applied by SHA, auto-merged clean); api
  `obs-api` → `langgraph-merge`; core `obs-analytics` → `master` (the core ledger was initially missed — the
  first merge went out without the uncommitted endpoint/schema/definition edits and the suite caught it with
  ImportErrors; ledger landed and merged in a follow-up, plus stale `__pycache__` dirs from the deleted Loki
  service removed); dashboard `obs-analytics` → `agent_sdk`, then `obs-frontend` rebased (11 commits, zero
  conflicts) and fast-forwarded; copilot-mro Stream P edits committed on `langgraph-merge` then `obs-infra`
  merged; iac `obs-iac` → `main` (unrelated dirty `apprunner_iam.tf` untouched, verified against the merge
  file list). Post-merge owed commits landed: the transitional bare public-ingest skip entry retired (auth +
  two test files, incl. one stale legacy public-path parameter the old contract test still pinned) and A14
  (legacy `OTEL_ENDPOINT` removed from the POC compose, `apprunner.tf`, `lambda.tf`, with a new
  no-legacy-env assertion over every compose file).
  **Post-merge verification, all green:** utils 1082; api 1080 + 3 skips (253 middleware); core 2768 + 2
  skips + 2 xfail; copilot-mro otel lane 62 + 9 env-gated skips, registries/db 488 + the 1 pre-existing
  migration-snapshot red; dashboard npm ci + typecheck + full unit suite exit 0, zero failures; iac terraform
  validate + all six dashboard templates parse + both setup scripts `bash -n`.
  **Now unblocked:** task 4.9/F10 (frontend cut-over — core's ingest routes are merged and `obs-frontend` sits
  on top of `obs-analytics`). **Consistency step owed:** the shared `/home/aditya/Code/api/.venv` still holds
  the old lock (SDK 1.37); run `env -u VIRTUAL_ENV poetry install` in `api/` when the parallel LangGraph
  session is idle — until then utils/api suites must run from the `wt-obs-u` bundle env as above. Worktrees
  and stream branches left in place for the owner to prune.

- **2026-09-05 — pruning + testing-scope ruling (owner).** Five merged worktrees removed with their stream
  branches (`utils-obs`, `core-obs`, `dashboard-obs-analytics`, `copilot-mro-obs-infra`, `iac-obs`). Kept
  deliberately: `dashboard-obs-frontend` (F10 under adversarial review; pruned after the merge) and
  `wt-obs-u` (`obs-api` branch pinned by its worktree — this bundle env is the only environment with the new
  OTel pins until the shared `api/.venv` refresh, so it stays as the utils/api test runner). Owner ruling:
  **AWS deployment work is DEFERRED until everything is implemented** — the Terraform apply chain, demo-box
  switch, Transaction Search, Amplify pin all wait. For now the three collector profiles are exercised FROM
  THE LAPTOP only: `oss` via the local compose stack (already live-smoked), `aws` and `azure` as
  config-validation plus, when the owner supplies credentials/workspace values in a local env file, a
  laptop-run collector shipping a test signal to CloudWatch / Azure Monitor (the B1a/B1b field-path probes can
  ride that same laptop send). No IaC apply until the deferral lifts.
- **2026-09-05 — F10 merged + LIVE PROBE PASSED (phase 4 acceptance).** F10 reviewed MERGE-READY (all gates
  re-run; the pre-existing lint fix verified as a pure rename) and fast-forwarded into `agent_sdk`; the last
  two worktrees pruned (`dashboard-obs-frontend`; `wt-obs-u` retained as the pinned-deps test env). Live probe
  (owner-chosen, session-lead-run) against the isolated smoke-overlay stack (collector+Loki+Tempo+Prometheus
  on loopback remaps) + the merged backend (bundle env, OTel to 14318/14319) + the production-built dashboard
  + a CDP-driven session (owner logged in): **Loki** carries `browser.web_vital` ×10, `browser.app.boot` ×2,
  `browser.auth.login` ×2, `browser.route.change` ×2, `browser.error` ×1 (synthetic), every stream labelled
  with the REAL `tenant_id` upserted from the gateway headers; **product_events** holds `session_started` +
  `document_opened` rows under RLS on the dev DB; **Tempo** holds one trace spanning BOTH services — the
  browser CLIENT span parenting the api SERVER span named with the full mounted route
  (`GET /api/v1/mro/v1/document-hub/capabilities`) and the api's own httpx/redis/postgres CLIENT spans
  beneath it; the core forwarder POSTed the collector's 4319 with 200s (59 ingest requests). To make the dev
  DB serve the new tables the owner migration + provision ran against `copilot_mro` (snapshot banked in
  `.dev_runs/obs-probe-20260905/`; 1447 stmts; readonly grants applied=20). Stack torn down after. Phase 4
  acceptance (master §8) is met.
- **2026-09-10 — Phase 8 OPENED (§11b).** Surveys: the bot is a standalone long-polling PTB 22 process with its
  own Poetry env, stdlib logging, psycopg 3, home-grown `count()`/`TurnTiming` log lines and **no `utils`
  dependency**; the optimizer is mounted at `/api/v1/optimizer` and already inherits HTTP spans/metrics/logs and
  psycopg2 spans from Stream U — only the solver run (a `BackgroundTask` that outlives the server span) lacks
  signal. Build on Opus in five worktree streams, ≤3 agents concurrent; merges held for the Fable gate.

- **2026-09-11 — Phase 8 Phase A CLOSED (build + Opus review).** Five streams built in nine worktrees, each
  adversarially reviewed, fix-passed and re-verified on Opus 5: O `flynapse-otel` package + utils shim (R1
  MERGE-READY), S optimizer run/solve spans + metrics + gateway health exclusion (R2 MERGE-READY), PA8 optimizer
  product tab — four panels, 46 total (R3 MERGE-READY), T Telegram bot telemetry incl. token/presigned-URL scrubbing
  on spans AND the OTLP log route (R4 MERGE-READY AFTER FIXES, all landed), D8 Grafana + CloudWatch boards + two
  alerts (R5 MERGE-READY). Two design items surfaced for the Fable R0 review: D-11 (gateway records HTTP duration
  after BackgroundTasks — the optimizer run route's p95 is the solve; mitigated on boards + `ApiP95LatencyHigh`) and
  D-12 (optimizer run attribution comes from an unsent, spoofable client `X-User` header — `optimizer_active_planners`
  dropped until the gateway injects identity). Pre-existing defects found and fixed in-stream: nine core analytics
  endpoint tests red since 2026-09-08 (seed clock aged out); found and deferred to the R1 merge: api's committed
  `poetry.lock` still points at the deleted `../../utils-obs` worktree path. Nothing merged, nothing pushed; the
  Sunday-night agenda, branch tips and merge mechanics are in the phase-8 plan §8b.
- **2026-09-11 — Phase 9 OPENED (§11c); Phase A building.** Trigger: the dashboard telemetry audit (two read-only agents
  at `agent_sdk` `b87ced0`) answered "not complete". Plan v1 `e1845fd` → an independent Opus plan review (READY AFTER
  CHANGES, 6 P1) → v2 `087da6f` (triage in the phase-9 plan §10a). Four Opus streams in six worktrees: F9
  `dashboard-obs9`/`obs9-browser` + `api-obs9`/`obs9-api`; E9 `dashboard-obs9e`/`obs9-events`; N9
  `dashboard-obs9n`/`obs9-server`; M9 `copilot-mro-obs9`/`obs9-deploy` + `iac-obs9`/`obs9-iac`, stacked on the phase-8 D8
  branches by merges `9976fa7c` / `9231863`. Status at this entry: M9 MERGE-READY (a final P3 mini pass); N9 MERGE-READY
  AFTER FIXES (fix pass running); F9 built (unit 1815/1815, api 322) and in review; E9 building (E9.1–E9.3 committed).
  Findings worth keeping: the api's trace-id middleware sat inside auth, so auth-converted 500s and 401s left without
  `X-Trace-Id` (fixed in F9); production `next build` strips literal `console.x` calls on the server too while computed
  calls survive (server lines now go through `process.stdout`); the pinned collector's `redaction` already masks STRING
  log bodies (G9-03 disproved and test-pinned); Tempo span metrics gain `url.template` only, under a 100000-series cap.
  **Coordination:** the owner launched a separate TanStack useMutation conversion (session code-26,
  `/home/aditya/Code/dashboard-tanstack`, plan `dashboard/docs/plans/tanstack-mutation-conversion.md`). Split in the
  phase-9 plan §1b: it owns the 34 direct writes, their reads and the settings telemetry (plus one core change —
  department-delete auth-cache invalidation); phase 9 owns the event catalogue and existing mutations. Owner ruling: that
  work is **Fable-gated too** — chunk RC after R6, merged before phase 9's code chunks, with fixed merge rules
  (`useOptimizer` `meta` combined; the settings-api department blocks taken from RC). **Owner items from this phase:**
  confirm the production Amplify branch sets `ENV=production` (`iac/amplify.tf:71` defaults `dashboard_env` to
  `development`, which keeps info/debug server lines on); the aws browser alarms join the pending alarm-dialect ruling
  (documented only); a non-blocking look at the §2.1 catalogue delta; FYI the local `deployment` Loki and Tempo
  containers (created 2026-03-10) crash-loop (~1,880 restarts) on the phase-6 `${…}` configs — `docker compose up -d
  loki tempo` in `copilot-mro/deployment` recreates them with `-config.expand-env=true`; a leftover
  `flynapse-otel-probe` collector holds 14318/14319/14313. Session-scratchpad notes, briefs and the P9 runbook are copied
  to `copilot-mro/.dev_runs/obs9-phaseA/`. Nothing merged, nothing pushed.
- **2026-09-11 — Phase 9 P9 live probe PASSED; Phase A closing.** F9 (`af9f307` + api `72df51a`), E9 (`08b7650`) and N9
  (`c52f034`) were re-verified MERGE-READY. M9 is MERGE-READY, and its M9.6 DARK flip landed after the probe (`90a60040` / iac `1d2b400`). P9 ran on a throwaway
  integration tree of the three dashboard branches, merged with 0 conflicts. Checks 1–9 passed; the gaps are named in the
  phase-9 plan §7 "P9 results": the S3 half of check 2 is blocked by an expired AWS SSO token, optimizer run triggers were
  not exercised because they would solve the owner's pinned jobs, and Data Discovery is not open to this account.
  New from P9: stream C9 — core's ingest route now answers a client disconnect with 499 and one INFO line, not a 500 with
  an ERROR traceback — as Fable chunk R11. Gate agenda: phase-9 plan §8b.
  **Owner items added:**
  - The local `api/.env` sets `OTEL_SERVICE_NAME=copilots`, plus the dead `OTEL_ENABLED` / `OTEL_ENDPOINT` keys. Change it to
    `api` (App Runner already sets `api`).
  - `NewPasswordView` always calls `confirmResetPassword`, so a user sent there by the login NEW_PASSWORD_REQUIRED
    challenge cannot finish. This is a product bug outside phase 9.
  - The automations failed-run panel shows no reference (phase-9 plan §9).

  Still open from earlier: Amplify `ENV=production`, the alarm-dialect ruling (the browser alarms are documented only),
  the §2.1 catalogue look, the crash-looping local `deployment` Loki and Tempo, and the leftover `flynapse-otel-probe`
  collector.
- **2026-09-11 — Phase 9 Phase A CLOSED.**
  - **M9.6 DARK flip landed** (`90a60040` / iac `1d2b400`).
    - The panels P9 saw now read LIVE, with the date.
    - Panels 12, 14, 17 B and 18 keep a dated DARK note.
    - The feature failure ratio leaves out the TanStack helper's client-side refusals.
  - **C9 landed:** core-obs9 `obs9-core` @ `8e3c3ce`, Opus-reviewed and re-verified MERGE-READY twice.
    - Telemetry ingest and product events now answer a client disconnect with a 499 and one INFO line.
    - The review also found the phase-5 chat-quality contract test red on core `master` since about 2026-09-08, from a
      seed-date time-bomb. It is fixed in tests only, plus a unit test for the real-clock default.
  - **F9.9, after the close** (`279df2f`): one precedence for the server's own sentence on a failed request — reported by
    the owner's TanStack session, reviewed MERGE-READY with a fix pass. The F9 gate tip moves with it.
  - **M9.7, 2026-09-12** (`0259fd8d` / iac `a0059f9`): the settings panels keep client-side refusals apart too, now that
    the owner's invitations conversion produces that shape. The M9 gate tips move with it.
  - The gate agenda with every tip is in phase-9 plan §8b. Nothing is merged or pushed.
- **2026-09-12 — Phase 9 post-close batch, the guard audit, and a trial integration merge of the finished TanStack work.**
  Nothing merged or pushed; every tree below verified clean at its tip on 2026-09-13.
  - **Post-close fixes, each reviewed or mutation-proven:**
    - F9.9 + F9.10 (`01a3882`): one precedence for the server's own sentence on a failed request; guard fixes.
    - E9.9 / E9.9b / E9.10 (`bc9fbcc`):
      - a telemetry bug can no longer change a write's outcome — TanStack catches a settle-hook throw and re-reports the
        write as failed;
      - at most one settle record per mutation, keyed on the mutation objects because `mutationId` restarts per client;
      - all five timing wrappers used to emit success inside the try they catch;
      - 18 test files moved off literal event names.
    - N9.6 (`7fc2bcc`): guard fixes.
    - M9.7 + M9.8 (`83f4a8f7` / iac `b72307b`): the settings-side refusal split, and wording that no longer promises a
      refusal sends no request (one gate runs an N+1 scan first).
  - **Guard audit (phase-9 plan §8c):** absence assertions that pass for the wrong reason, in eight shapes. New rule
    D9-20: every absence assertion carries a positive control in the same run.
  - **The TanStack conversion (RC, session code-26) FINISHED.** Dashboard `tanstack-conversion` (tip `173706c`; trial
    pinned at `b728d33`, and everything above it is their plan document only) and core `tanstack-dept-delete` @
    `401c2a6`. Phase 9 reviewed their composite-write swap before their gate and ruled:
    - refusals stay one class;
    - a rollback request emits nothing;
    - a coarse `error_type` is accepted on five composite paths.
  - **Trial integration merge (throwaway, kept for the gate):**
    - dashboard `dashboard-obs9x` @ `dc7a043` — RC, then F9, E9, N9 — **2333 of 2333**, `tsc` and lint clean, 15 guards
      green;
    - core `core-obs9x` @ `694113a` — every R11 count exact, zero conflicts.
  - **What only the merged tree showed:**
    - git silently dropped seven `meta.telemetry` keys (two `meta:` keys in one literal, the later wins), and only `tsc`
      TS1117 saw it;
    - the double-emission guard's fixtures had gone inert after RC's deletion;
    - the coverage floor of 45 accepted a sweep blind to 27 of 77 sites; it is raised to 70;
    - the plan's counts were branch-relative: settings emitters are 27, not 19, and the "43 bare feature writes" did not
      exist — 8 are bare.
  - **Core merge order changed:** R11 merges into core `master` FIRST, which cures the 9 analytics contract tests red on
    `master` today.
  - **New owner decision:** 14 known per-call callbacks across both teams report a landed write as failed if a response
    field is absent. Their complete answer is response validation at the API layer (phase-9 plan §9).

**2026-09-13/14 — The phase-8 Fable gate ran end-to-end, merged and pushed; phase 9's gate opened and paused
at the owner's request.** Session model set to Fable 5; chunks one at a time, a fresh Fable reviewer each,
per D-10. R0 (design): D-1…D-9 KEEP, D-10 mechanics amended (post-merge lanes every chunk + moved-base
rule), D-11 RULED (a) metric-at-final-send (narrowed: the span was already right), D-12 RULED (a) gateway
X-User strip+inject; ten adversarial findings, four fix passes landed the same night (flynapse-otel
`25dc158` — `py.typed` + tracecontext-only pin, which needed `set_global_textmap` because
`opentelemetry.propagate` builds its composite at its own import; api `92a9006` — both rulings, F-10
folded in, mutation-checked; bot `909510e` — the PTB CRITICAL `Update`-repr scrub, type-keyed; D8
`c29cc24a`/`36a982e` — true reverts of the D-11 exclusions + the F-4 mirror line). R1–R5 all
MERGE-READY (R5 after two one-line text fixes `f03cb979`) and merged with green post-merge lanes: utils
`718db0a`, api relock `702c54f` (shared `api/.venv` refreshed, `wt-obs-u` retired; boot check =
"Telemetry configured", six instrumentors), shift-optimizer `23d3f2e` + api `58a5c3b`, core `a1a5f6c` +
dashboard `6483a08`, bot `c6ee959` (owner WIP `f83f2fb` committed first by owner choice; compose
hand-carry api `7cd192f`; image rebuilt through the `otel` additional context), copilot-mro `18909ee0`
(moved-base procedure — the owner's S4 merges moved that base twice mid-gate, zero overlap) + iac
`7690c8d`. Environmental finds, all resolved: the dashboard lane needs the repo's canonical
`--tsconfig tsconfig.test.json` flags (bare `tsx --test` = phantom "React is not defined"); a stale
docker bind-mount kept recreating the deleted legacy collector config as a root-owned dir (removed; the
old `deployment`-project loki/tempo crash-loop because their containers predate the expand-env config
style — recreate that project from the current spec at the live pass); Postgres needed a second
`docker start`. R3's owed DB lanes then cleared: 156 ran, 0 failed on merged core `master`. PUSHED
2026-09-14: all eight repos fast-forwarded (flynapse-otel, utils, shift-optimizer, api, core, dashboard,
telegram-bot, iac); copilot-mro deliberately NOT pushed — its `langgraph-merge` carries ~85 unpushed S4
commits with that session's own tag-riding push protocol. Phase 9: R6 (design) — every D9 decision KEEP,
§8b mechanics amended (the R11 C9.2-vs-`0fa9765` conflict ruling, RC re-pin procedure, R10 base-merge fix
pass, the owner §2.1 look scheduled before R8's merge, extended post-R11 re-probe, I-7 skip-is-not-a-pass
rule); RC-D/RC-1/RC-2 ran in the owner's parallel chat (tip moved to `fec72f2`+, RC-2 fix pending); R7
(F9) reviewed MERGE-READY (dashboard 1853/1853 canonical lanes, api 322, both moved bases re-verified
disjoint; one P2: bare `npx eslint` is a silent no-op in this repo — `next lint` is the only valid
invocation) — merge HELD behind RC and the pause. Owner rulings tonight: live probes (phase-8 §10 + the
extended re-probe) DEFERRED to one batch at the end of the gate; gate briefs durably in
`copilot-mro/.dev_runs/obs8-fable-gate/` and `obs9-fable-gate/`.

**2026-09-14 (day) — every gate review closed; the merge sequence nearly done.** Reviews R8 (E9), R9 (N9),
R10 (M9), R11 (C9) all returned MERGE-READY on Fable 5 (briefs in `copilot-mro/.dev_runs/obs9-fable-gate/`).
Notable review products: R9 root-caused and defused the worktree `next build` standalone trap after it wiped
the shared dashboard `node_modules` (restored via `npm ci`; §1c now carries the rm-before-build rule; the
RC session was warned about the 12-minute invalid-lane window); the two base `prefer-const` lint reds fixed
on `agent_sdk` (`c7b9eb9`); R10 ran the two-way allow-list↔catalogue diff mechanically (zero missing keys)
and caught nine guard mutations; R11 verified the F-R6-1 conflict ruling, AMENDED it (F-R11-1: take
master's contract file WHOLESALE — the dangerous pin auto-merges silently; keep-both demonstrated 9-red)
and was merged as core `master` @ `8571373` (full core `tests/api` exit-0 post-merge). The RC session then
handed off: all nine RC chunks closed; core-side RC merged @ `e10a9ce` (C9-first held); dashboard-side RC
merged @ `40b2c7f` after a 2136/2136 + tsc-clean lane at the final tip `915078a`. R7 merged: api side
`fc35d08` (F-R6-4 followed, 342 green combined), dashboard side `505ca7a` — merged-tree lane initially red
with 15 failures in three F9×RC semantic clusters, ALL resolved test-side by a Fable fix pass (zero
production changes; commits `98e9130`/`590f2b2`/`cf1d0cb`; lane 2210/2210; a renamed log sentinel had left
12 files of global-handler assertions silently vacuous — re-armed). R10 merged while R8 was blocked:
copilot-mro `2cd98bde` + iac `3b5f414`, otel lane 79/8 + terraform validate green post-merge. Owner
approvals in-session: **§2.1 catalogue APPROVED** ("§2.1 OK", with the products-vs-mechanism clarification
recorded); the NewPasswordView challenge fix declared finished and committed by the session lead as
`2af8239` (auth lane 208/208 against it) — unblocking R8's `NewPasswordView.tsx` overlap. The R8 merge
launch then hit Fable's session limit (reset 05:50 PT) and was relaunched on Fable at 05:51 on the owner's
word. Remaining after R8: the R9 (N9) dashboard merge, then only the live batch (stack recreate, probe
teardown, phase-8 §10 probe, extended re-probe F-R6-6, the compose smokes' clean 87-run). One new
owner/backend item out of RC-8: `/rag/stream` emits `final` before the block save (migration-zone file —
waits for Gate M or an owner ruling).

**2026-09-14/15 — phase 10 opened; Gate M declared.** After the post-gate housekeeping, the owner picked nine
follow-ups and asked for design + plan (Opus build and review, then Fable). Five read-only Opus 5 research agents
reported; findings that changed the recorded picture: response validation has 8 callback flip sites + 6 post-await
reads (not 3 + 11), and two AD-review routes plus core `POST /operators` declare no response model; `/rag/stream`
also races follow-up turns and a 300 s history-cache write-back, and no out-of-zone fix closes it; the Document Hub
double count was already fixed by F10 `1f2aa95`, but inline Hub chips now emit zero opened rows (the §15 "hub-citation
double-surface" ruling line above is stale — it was ruled at F10); `outputFileTracingRoot` does not close the worktree
build trap (the start-of-build `cleanDistDir` delete and every `next dev` start follow the planted symlink); two smoke
overrides carry fixed network names; api/worker report a fake `0.1.0` version (not `unknown`), the bot `unknown`, the
browser a hard-coded `1.0.0`; `shift_optimizer_test` policies stale since the 2026-08-17 sentinel predicate change;
following the alert rollout checklist as written turns a guard red, and delivery failures are silent; the aws 5→6
raise would replace both EC2 instances unless `user_data` moves to `user_data_base64`. **Owner rulings:** narrow zod
contracts at the API layer; "langraph migration is done. so we can build and moerge now." (= **Gate M declared**, §2);
real Slack + email targets now — prod and dev Slack channels, email for prod critical only, the platform's SMTP relay;
CloudWatch dialect = raise `hashicorp/aws` to `~> 6.42`. Plan v1 written (`observability-rebuild-phase-10-owner-follow-ups.md`);
an independent Opus plan review runs before the owner's plan review; nothing built yet.
### Folded from `obs-telemetry-merge` (ishaan.jain), merged 2026-09-20 — their branch's own ledger entries

Their entries keep their original dates; they entered THIS ledger only at the 2026-09-20 merge, so nothing
below was known to this plan when it was dated. Phase numbering is corrected to **Phase 11** throughout (their
"Phase 8" collided with our satellite-services Phase 8 — see §11e). Where a claim is now false, the correction
is inline and marked, not deleted.

- **2026-09-08 — audit follow-up phase approved (their Phase 8 → our Phase 11).** It was added as a separate
  plan linked from this
  master. It preserves the existing two application contracts and owns the remaining deltas: product-event
  idempotency/versioning, per-client Flynapse UI dashboard profiles, post-gate runtime/facts reconciliation,
  optional Phoenix packaging, New Relic/provider readiness and the final cross-phase acceptance matrix.
  `otel-lgtm`, multi-host orchestration and Kubernetes remain deferred. Phase 11.0 is the next planning gate;
  it must refresh current branch facts before implementation checkboxes are trusted.

- **2026-09-08 — Task 11.0 current-branch audit COMPLETE.** Static evidence was refreshed across `api`
  `a19a931`, `core` `988571b`, `copilot-mro` `ac680bf2`, `dashboard` `b87ced0`, `utils` `9f74a11` and `iac`
  `5996e5a`; all six worktrees were clean. The authoritative file-level table is research 08. Key result:
  operational OTLP, the Collector boundary, PostgreSQL product analytics, the native 42-panel Flynapse UI and
  both runtime adapters exist. Product-event idempotency/versioning, the per-client UI profile, New Relic,
  production Collector queues, application content capture and the online `chat_turn_facts` writer do not.
  Root/POC Docker currently hard-wire Phoenix. ~~Gate M is **not declared** because Batch 5 and its subsequent
  parity slice remain;~~ **corrected 2026-09-20: Gate M was declared 2026-09-14/15 (§2, §14)** — only Task 11.3
  stays blocked, on Task R. No runtime probe was rerun, so the 2026-09-05 browser/OSS
  results remain historical evidence rather than a claim about today's running services.

- **2026-09-08 — Task 11.1 product-event reliability COMPLETE in isolated worktrees.** The Flynapse UI assigns
  a stable queue-time UUID and schema version 1; Core retains old-client compatibility values, stores the
  version, ignores duplicate `(tenant_id, event_id)` inserts, reports accepted and duplicate counts, and
  re-logs accepted rows only. The registry migration must precede Core, then the same Flynapse UI bundle may
  deploy. Compatibility defaults remain until supported-client adoption is evidenced and a separate breaking
  change is approved. Focused and broader frontend/Core suites passed, including scratch-Postgres RLS,
  duplicate-replay, cross-tenant and pre-11.1-to-current registry migration tests; exact evidence and the one
  isolated-worktree collection limitation are recorded in the Phase 11 detail plan.

- **2026-09-08 — Phase 1c stable non-agent scope ADDED; implementation not started.** A current-code review of
  copilot-mro `ac680bf2` and utils `9f74a11` separated stable lifecycle/job/client boundaries from the active
  LangGraph/tool/skill paths. Phase 1c may proceed before Gate M only after its signal-slice detail plan is
  approved and its path/drift guard passes. Included: MRO lifecycle, memory, Document Hub processing/cleanup,
  Data Discovery one-job runner, improvement scheduler/runner, approved non-LLM parser command entrypoints, and shared S3/
  Weaviate clients. Lambda and all agent/tool/skill/LLM internals remain excluded. This entry records planning
  only; it is not implementation evidence.

- **2026-09-08 — Phase 1c stable non-agent telemetry COMPLETE in isolated worktrees.** `obs-non-agent` now
  carries bounded spans/log context for shared S3/Weaviate clients, MRO lifecycle, memory, Document Hub
  processing/cleanup, Data Discovery job runner, Improvement runner/stages and approved parser entrypoints.
  The scope guard keeps agent/tool/skill/LLM internals excluded until Gate M. Runtime acceptance was completed
  after owner-approved local stack reconciliation: only `otel-collector` and `tempo` were recreated under the
  existing `deployment` compose project from the `obs-non-agent` checkout, and Tempo returned all 16 Phase 1c
  operation canaries by trace ID. Exact tests, scan results and trace IDs are recorded in the Phase 1c detail
  plan.

## 16. Future Improvements

- Evaluate a single-container `otel-lgtm` POC only after the current Docker-native Phase 11 baseline is accepted.
  This is a footprint experiment, not a prerequisite and not a change to the application OTLP contract.
- Design a multi-host Collector topology only when load, availability or client deployment requirements justify
  it. The current scope remains one Docker host per client deployment.

## 17. Lessons
_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule for next time)_

## 18. Resume brief (first written 2026-09-05; phase-8 and phase-9 paragraphs updated 2026-09-11; `obs-telemetry-merge` folded 2026-09-20)

Original 2026-09-05 snapshot: no implementers or reviewers were running. Every stream (I infra, U utils/api,
P backend + dashboard analytics, F frontend, D phase-6 dashboards) was adversarially reviewed MERGE-READY,
merged estate-wide with green verification, and every worktree's ledgered uncommitted edits landed as explicit
commits. §15 above is the authoritative dated ledger (merge note, probe note, owner checklist, deferral
rulings). F10 cut-over is merged into dashboard `agent_sdk`; the live probe PASSED: Loki carries all five
browser event types with tenant_id upserted from gateway headers, `product_events` holds rows under RLS, and
one Tempo trace spans dashboard CLIENT → api SERVER (full mounted route) → db CLIENT spans. Dev DB
`copilot_mro` was migrated + provisioned for `product_events`/`chat_turn_facts` (snapshot banked in
`.dev_runs/obs-probe-20260905/`). Worktrees pruned except `/home/aditya/Code/wt-obs-u` — its bundle env is
the ONLY env with the new OTel pins until the owner runs the shared-venv refresh (`env -u VIRTUAL_ENV poetry
install` in `api/`, only when the parallel LangGraph session is idle); until then run utils/api tests from
the bundle with PYTHONPATH pinned to the MAIN checkouts. Everything is local/unpushed per workspace norm.

**Phase 8 — FABLE-GATED AND MERGED 2026-09-13.** All six chunks closed the same night: R0 design (D-1…D-9
KEEP; D-11 ruled (a) metric-at-final-send, D-12 ruled (a) gateway X-User strip+inject, D-10 mechanics
amended) with four fix passes; then R1–R5 each reviewed by a fresh Fable agent and merged: utils
`langgraph-merge` `718db0a` (+ api relock `702c54f`; shared `api/.venv` refreshed — new OTel pins,
`wt-obs-u` bundle RETIRED), shift-optimizer `main` `23d3f2e` + api `58a5c3b` (D-11a/D-12a fixes in), core
`master` `a1a5f6c` + dashboard `agent_sdk` `6483a08`, bot `main` `c6ee959` (owner WIP committed first as
`f83f2fb`; compose hand-carry api `7cd192f`; image rebuilt through the `otel` additional context), and
copilot-mro `langgraph-merge` `18909ee0` + iac `main` `7690c8d` (R5 fixes `f03cb979` landed pre-merge;
moved-base procedure used — the owner's S4 merges moved that base twice mid-gate). Every post-merge lane
green (bot 2284/1, middleware 273, otel 64/7 after removing a stale docker-created legacy-config dir).
Briefs: phase-8 plan §11 + `copilot-mro/.dev_runs/obs8-fable-gate/`. PUSHED 2026-09-14 (all eight repos;
copilot-mro withheld — S4 freight + its tag protocol). R3's owed DB lanes CLEARED (156/0 on merged
`master` once Postgres came back). STILL OWED phase-8: only the §10 live probe — owner-DEFERRED to one
live batch at the end of the whole gate, together with phase-9's extended re-probe.

**Phase 9 (added 2026-09-11) — built, reviewed, trial-merged; WAITING ON THE FABLE GATE (state as of 2026-09-13).**
Dashboard telemetry completion covers every gap from the 2026-09-11 dashboard audit except Rostering, which is demo-only.
Five Opus streams were each built, Opus-reviewed, fixed and re-verified. The P9 live probe PASSED. A post-close batch
(2026-09-12) fixed what the guard audit and the TanStack exchange found. A throwaway integration merge of everything,
including the owner's finished TanStack conversion, is green.

Gate tips (verified clean 2026-09-13; phase-9 plan §8b has the table, the evidence, the merge mechanics and the trial
results):
- **F9:** `dashboard-obs9` `obs9-browser` @ `01a3882` + `api-obs9` `obs9-api` @ `72df51a`.
- **E9:** `dashboard-obs9e` `obs9-events` @ `bc9fbcc`.
- **N9:** `dashboard-obs9n` `obs9-server` @ `7fc2bcc`.
- **M9:** `copilot-mro-obs9` `obs9-deploy` @ `83f4a8f7` + `iac-obs9` `obs9-iac` @ `b72307b`, stacked on phase-8 D8.
- **C9:** `core-obs9` `obs9-core` @ `8e3c3ce`.
- **RC (owner's TanStack conversion, session code-26):** `dashboard-tanstack` `tanstack-conversion` — the
  `173706c` pin is STALE: RC-D/RC-1/RC-2 ran 2026-09-13 in the owner's parallel review chat and landed fix
  commits (observed `fec72f2`; RC-2 fix pending, the tip moves again). RE-PIN at the tip that closes RC-8
  (R6 F-R6-2); the changed-file set is stable (159), so chunk ownership stands. Core side still
  `core-tanstack` `tanstack-dept-delete` @ `401c2a6`. Never merge the `tanstack-t11…t18`, `tanstack-guard`
  or `tanstack-phase3-fix` refs — all are absorbed into `tanstack-conversion`.
- **Trial trees (reference, not for merging):** `dashboard-obs9x` `obs9-trial-merge` @ `dc7a043` (2333 of 2333) and
  `core-obs9x` `obs9-trial-merge` @ `694113a`. Reports: `copilot-mro/.dev_runs/obs9-phaseA/phase9-trial-merge-*.md`.

**Gate order (status as of the 2026-09-14 pause):**
1. Phase 8 R0–R5 — DONE, merged, pushed.
2. Phase 9 R6, the design — DONE (all KEEP; §8b amendments in the phase-9 plan).
3. RC — COMPLETE AND MERGED 2026-09-14: all nine chunks closed in the owner's parallel chat (final tips
   `915078a` dashboard / `401c2a6` core); merged as dashboard `40b2c7f` (2136/2136 at the tip first) and
   core `e10a9ce` (after C9).
4. **THE GATE IS COMPLETE (2026-09-14, morning).** Every review chunk closed on Fable, every merge
   landed: dashboard `agent_sdk` @ `0a4dbec` = RC (`40b2c7f`) + R7 F9 (`505ca7a` + fix `cf1d0cb`) + the
   auth challenge fix (`2af8239`) + R8 E9 (`1d7326c`: TS1117 combines at the trial's exact 20/19/13
   reference, six wrapper→hook moves, floor 70, upload exemption, A-2 PASSES, the challenge outcome now
   EMITS) + R9 N9 (`0a4dbec`, zero conflicts, 2368/2368, build evidence clean); api `langgraph-merge` @
   `fc35d08`; core `master` @ `e10a9ce` (R11 `8571373` before RC, per the ruling); copilot-mro
   `langgraph-merge` @ `2cd98bde`; iac `main` @ `3b5f414`. Phase-9 merges are LOCAL AND UNPUSHED (the
   owner authorized pushing phase 8 only). Remaining: (a) the live batch — recreate the `deployment`
   compose project from the current spec, tear down the `flynapse-otel-probe` overlay, phase-8 §10
   probe (one Telegram turn from the owner's phone), the extended re-probe F-R6-6 (checks 2/4/5 + one
   settings mutation + one Document-Hub write + the M9.6 panel-12 flip), the compose smokes' one clean
   87-run; (b) owner decisions/items: push phase 9, response validation at the API layer (§9), the
   /rag/stream final-before-save race (migration zone → Gate M), worktree cleanup (nine absorbed
   tanstack trees + the obs8/obs9 trees), the durable worktree-build fix (`outputFileTracingRoot`),
   and the long-standing §15 owner checklist.
5. **Post-gate housekeeping DONE 2026-09-14 (owner-ordered):** phase 9 PUSHED — all five repos
   fast-forwarded (dashboard `0a4dbec`, api `fc35d08`, core `e10a9ce`, iac `3b5f414`, copilot-mro
   `46e3aa83` incl. S4's ledger commits). The `flynapse-otel-probe` overlay TORN DOWN (its shared smoke
   network removed with it — the §9 isolation defect's live trigger is gone). The `deployment` project's
   observability services RECREATED from the current spec (collector/prometheus/alertmanager/loki/
   grafana/tempo; grafana's admin password carried from the old container without display; tempo needed
   its bind-mounted `tempo_data` chowned to the new image's 10001 uid — the old crash-loop's config
   half was cured by the recreate, the ownership half by the chown; legacy config dir NOT recreated; all
   six Up). WORKTREES REMOVED: all 30 gate trees (obs8/obs9/tanstack/t11–t18/guard/trials) + the retired
   `wt-obs-u` bundle; the nine absorbed task branches deleted; `obs*`/`tanstack-conversion` branch refs
   and the S4 session's `copilot-mro-s44pm` kept; the RC gate ledger (103 files) backed up to
   `copilot-mro/.dev_runs/tanstack-gate/` before removal. Owner then ordered the remaining tanstack
   refs gone too: `tanstack-conversion`, `tanstack-phase3-fix` (dashboard) and `tanstack-dept-delete`
   (core) safe-deleted 2026-09-14 — git's `-d` confirmed each fully merged; no remote tanstack branch
   ever existed. The TanStack estate now lives only in the mainline history, the merged plan doc, and
   the `.dev_runs/tanstack-gate/` archive. Then ALL obs branch refs too (owner "yes", 2026-09-14):
   every `obs8-*`/`obs9-*` branch across the eight repos safe-deleted as merged (plus a stray older
   `obs-api`); the two `obs9-trial-merge` throwaways force-deleted (never merged by design — their
   reports live in `.dev_runs/obs9-phaseA/`). Zero gate branches remain anywhere; the gate exists only
   in mainline history, the plan files, the `.dev_runs` archives, and memory. The SHAs recorded in the
   plans' historical tables refer to commits still reachable through the merge commits. STILL OWED from the live batch: the phase-8
   §10 probe (one Telegram turn from the owner's phone) and the extended re-probe F-R6-6 (checks 2/4/5 +
   settings + Document-Hub records + the panel-12 flip; needs P9's probe-only forcing edits for check
   4); the smokes' clean 87-run LANDED right after the teardown: **87 passed / 0 skipped in one run** on the
   merged tree (compose smokes + rules + masking proof included) — that residual is CLOSED. The live
   batch is now ONLY the two probes needing the owner: the phase-8 §10 probe (one Telegram turn) and
   the extended re-probe F-R6-6.
5. One live batch at the end: phase-8 §10 probe + the extended re-probe (F-R6-6) — recreate the old
   `deployment` compose project from the current spec first; tear down the leftover
   `flynapse-otel-probe` overlay in the same pass.

**Phase 10 (opened 2026-09-14) — owner follow-ups; EXECUTING since 2026-09-15 (plan v5, SDD, agent cap 10).** The
Fable plan review and its scoped re-verify are folded; the owner gave the go. L10.0 done (Postgres stale-mount incident
resolved by an owner restart; `shift_optimizer_test` migrated + reprovisioned, optimizer tests/api 130 passed). Tasks 9
and 14 complete; Task 7 re-planned to a generation-versioned cache key after its stop condition hit; checkpoint #3 (same
day): Tasks 5, 7, 9, 14, 18 complete; 10, 17, 20 in scoped re-review; 19 in task review; 3, 4, 6, 15 implementing;
lane-close reviews running for `stream` and `cache`; 1, 2, 8, 13 queued; 11→12, 16, 21 follow their lanes. No Fable
chunk requested yet; nothing merged or pushed. **PHASE 10 PHASES A + B COMPLETE 2026-09-15:** all 22 tasks complete, all 15 lanes closed, all ten Fable chunks (R12–R21) MERGED — dashboard `agent_sdk` 4a2898b, copilot-mro `langgraph-merge` 81965357, api `langgraph-merge` 087e298, utils 6ba3ab5→a9ca707, shift-optimizer `main` 88e9803, telegram-bot 3102fcc, flynapse-otel 1cafda2, iac `main` f35ec20. PUSHED 2026-09-15 on the owner's word (all eight repos; shift-optimizer's remote is named `main`); all 24 obs10 worktrees + branches removed; utils 0.1.39 / flynapse-otel 0.1.1 / api NOT published (api publishes from main/develop only). Remaining = §10 live batch (owner present; the R19 relative plan gate is step 1 of the iac apply — control `3b5f414` by SHA vs `main`, valid under state drift) + owner-owed §13 rulings + worktree cleanup on the owner's word. Ledger tail = the record. Earlier resume text:
`.superpowers/sdd/observability-rebuild-phase-10-owner-follow-ups/progress.md` (task table + agent ids). Nothing merged
or pushed; merges only after each Fable chunk verdict (handoff dir `copilot-mro/.dev_runs/obs10-fable-gate/`, Fable chat
`code-a9`). v3 re-laid execution as SDD with 15 parallel lanes (Opus controller + Opus implementers and
reviewers here; Fable reviews in a separate Fable chat via handoff files + a SendMessage doorbell; lane locks for heavy
commands). v4 folds in the owner's Fable plan review (READY AFTER CHANGES, 1 P1 / 5 P2): the provider raise now leaves
`user_data` untouched — the earlier `user_data_base64` move was itself the replacement risk.
Nine owner-picked items, designed from five Opus research reports; owner rulings recorded in the phase plan header and
§15; **Gate M DECLARED** (§2 — Task R unblocked, not started); alert literals supplied (`#prod-alerts`, `#dev-alerts`,
email `aditya@flynapse.ai`, the platform's SMTP relay). The independent Opus plan review returned READY AFTER CHANGES
(4 P1 / 11 P2), all folded into v2 (triage table §10a): the chat-blocks cache is removed rather than guarded, no backend
response models, the save task survives disconnect and drains in the gateway lifespan, a null-target Alertmanager config
until the owner's secret files exist, `hashicorp/aws ~> 6.43`, and an owner read-only `terraform plan` gate before the iac merge (R19 in v3 numbering).
Next: owner go → L10.0 (RLS re-run, session lead) → 15 parallel SDD lanes on Opus (task reviews + lane reviews) → Fable
chunks R12–R21 with a merge after each verdict → the live batch (alert receipt, stream reopen, versions, plus the
carried phase-8 §10 and F-R6-6 probes). Detail: `observability-rebuild-phase-10-owner-follow-ups.md` §1a. **Post-phase follow-ups 2026-09-15 (PUSHED the same day; first `otel-tests` CI run green, 106 passed / 25 skipped):** api `3c45dff` (psycopg instrumentor in the dev group — the `poetry lock --regenerate` route could not add it, see phase-10 §13); copilot-mro `langgraph-merge` → `070f72c3` (SSE `error` frame = constant + trace id; `otel-tests.yml` CI lane; contract doc); shift-optimizer `main` → `5ee3f45` (`shift_optimizer` refused by the test guard for every kind). Owner rulings FU-GUARD/FU-SSEFRAME/FU-SSM/FU-SENDAS taken; FU-MOVED deferred to the first apply. **Second follow-up batch, same night (Fable gate R22 CLOSED MERGE-READY 2026-09-16 after two fix rounds; PUSHED 2026-09-16 in order — final tips utils `289ba71` → copilot-mro `417df303` → api `44bd8d1`, shift-optimizer `1ba897e`; record `copilot-mro/.dev_runs/obs10-fable-gate/R22-merged.md`):** utils `c4c6cef`→`289ba71` (`failure_fields`: type + frames, never the message; `pg_primary` class-gated; human sink `diagnose=False`; the stdlib→loguru intercept now carries `extra=`; health probes return class names), copilot-mro `c27a8fcf`→`2bd36558` (in-repo git-ignored Alertmanager secrets dir; the exception-text sweep of the chat routes/store/health/pipeline/scheduler with a 50-shape AST guard; sync `/rag` honours a refused save + logs the resolved chat id; all health legs status + `error_type`; POC api grace 110 s), api `bedd4ab`→`73da119` (shutdown budget 108 s: uvicorn `--timeout-graceful-shutdown 25`, bounded clock stops + unwinds, bounded drains, bounded OTel flush called last; grace 110 s). MERGE ORDER utils → copilot-mro → api. App Runner window ≥ 110 s (owner). **Stream L (Task R + phase-0 app half 0.5/0.6 + 1b-mro + phase 3) has NOT started — the chat routes still log `query=request.message`; 0.5 is the recommended immediate hotfix.**

**Exception in core:** R11 merges into core `master` BEFORE RC's core commit — the order stands, but the
old reason ("cures 9 red contract tests") is STALE: master is green since R3's `0fa9765` (2026-09-13), and
that fix CONFLICTS with C9.2 (same file, same time-bomb, opposite mechanism). R6 ruled the resolution:
take master's `recent_anchor()` seed mechanism, drop C9.2's autouse pin entirely — never keep both (phase-9
plan §8b R6 amendments, F-R6-1). The core trial's "zero conflicts" was measured on the old base and does
not transfer. After R11, the EXTENDED re-probe (F-R6-6): checks 2/4/5 + one settings mutation + one
Document-Hub write in Loki + the M9.6 flip for panel 12.

**Rules for the real merge, learned on the trial tree:**
- Run `tsc --noEmit` BEFORE the unit lane. TS1117 on a resolved file means two `meta:` keys: combine the literals, never
  drop a side. Then confirm by count that `telemetry` survived at every site.
- Anything counted on either branch stays counted. Where RC's hook supersedes a phase-9 call-site wrapper, the telemetry
  moves into that hook's existing meta literal in the same change.
- Every count the plan quotes is branch-relative: re-check it on the merged tree.
- Read the other side's BRANCH, not the shared base.

Durable copies of every note, brief, review and trial report: `copilot-mro/.dev_runs/obs9-phaseA/`.

Next work, in order: (0) the Sunday Fable gate (2026-09-13): phase 8 R0–R5, then its §10 live probe, then phase 9's chunks R6 → RC (RC-D, RC-1…RC-8) → R7–R11, using the trial trees and the merge rules above; (1) owner checklist in §15 (alert thresholds + Slack/email targets, CloudWatch
alarm-dialect ruling, Amplify AL2023 + Node 22, improvement-findings review → tab flag, backfill crontab,
Weaviate pin, Portainer, B1a/B1b/B1d probes); (2) AWS deployment DEFERRED by owner ruling until all
implementation is done — laptop-only profile testing until then; (3) Gate M when the owner declares the
LangGraph migration landed → Task R rescoping → Stream L (phase 0 app half, 1b-mro, phase 3 LLM/agent
telemetry, `chat_turn_facts` writer 3.7, content capture) — the dark phase-6 panels light up here and Stream
L must confirm the `agent_outcome="error"` spelling + doc-hub/automation counters; (4) phase 7 eval harness
(Phoenix container done). Per-stream detail: `docs/plans/observability-rebuild-phase-*.md` (implementation
notes, review triage, Lessons in each).
### Folded from `obs-telemetry-merge`, 2026-09-20 — their branch's own continuation notes

Their duplicate copy of the "Next work" list above is dropped: its item (1), "review/merge the isolated
`obs-non-agent` branches when desired", is exactly what the 2026-09-20 merge did. Their phase numbering is
corrected to **Phase 11** (§11e). The two continuations are kept as their evidence, with the false claim
corrected in place rather than removed.

**Their 2026-09-08 continuation:** Phases 11.0 and 11.1 are complete; their pre-gate baseline and
implementation evidence are recorded in research 08 and the Phase 11 detail plan. Phase 1c is complete in
isolated worktrees; runtime acceptance left `deployment-otel-collector-1` and `deployment-tempo-1` running from
the `obs-non-agent` checkout. Tasks 11.2, 11.4 and the configuration-only part of 11.5 may proceed without
waiting for runtime work. ~~Task 11.3 still requires Gate M and Task R.~~ **Corrected 2026-09-20:** Gate M was
declared 2026-09-14/15 (§2, §15), so 11.3's gate is open; what is actually owed is Task R, and 11.3's writer
half is owned by Phase 3.7 / merge-plan G.5, not by Phase 11. Phase 11.6 is the final integration gate. Do not
implement `otel-lgtm` or Kubernetes as part of this continuation.

**Their 2026-09-17 continuation:** Task 11.2 is implemented and refreshed on `obs-telemetry-merge`; the Core
dashboard-profile resolver/API/static lane, isolated dashboard-profile scratch DB lane, Dashboard mounted/profile
unit tests, Dashboard typecheck and touched-file lint passed. The configuration-only part of 11.5 is also refreshed:
metric-cardinality and destination/profile composition tests, the non-container OTel lane, the Task 5
dashboard/alert/Collector bundle, Copilot MRO `poetry check --lock`, and `bash -n deployment/otel/validate.sh`
passed. Task 11.6 is complete within the bounded non-container review scope: the product-event replay scratch DB lane still blocks before assertions on
`permission denied for table tenants`, the facts-backfill scratch DB lane reproduces the same fixture-grant
blocker, and no owner-run UI, Grafana/Prometheus/Tempo, Phoenix, Docker, provider-canary or queue-restart proof
has run. The final GPT-5.6 architecture/code review found one Important AWS Query Studio catalogue
contradiction; Copilot MRO commit `4838cfc` corrected it, the full static lane passed again (`72 passed,
2 skipped`), and the scoped GPT-5.6 re-review approved the result with no unresolved Critical or Important
issue. One non-blocking Minor remains: API warning mode does not expose its degraded result in health state.
~~Gate M remains closed and Task R remains unrun.~~ **Corrected 2026-09-20:** Gate M was **declared
2026-09-14/15** — their branch was cut before that and could not see it. Task R is indeed unrun, and is now
unblocked; the merge plan carries it as G.1, widened to an estate-wide coverage audit.

**2026-09-20 — `obs-telemetry-merge` folded into this plan.** The colleague's six-repo branch is being merged
under `docs/plans/observability-telemetry-merge-and-completion.md`, which is the live document for that work
(merge strategy, the twenty rulings in its §4, the Phase 0 findings register in its §5, and the Phase G gap
list that supersedes "next work" above). This master plan keeps the rebuild's own record; read the merge plan
for what is executing now.

---

## Appendix A — Draft contract clause: conversation content capture (for legal review; ruling 20)

**Conversation Content Processing.** To operate, support and improve the Service, Flynapse records the text
of user questions, assistant answers and the intermediate tool inputs and outputs produced while answering
("Conversation Content"), together with usage metadata (timestamps, token counts, model identifiers, cost
estimates, latency). Conversation Content is redacted automatically at the time of recording to remove
credentials, access tokens, email addresses, phone numbers and other patterns Flynapse designates as sensitive,
and is stored in the Customer's dedicated tenant partition with row-level access control. Conversation Content
is retained for thirty (30) days from recording and then deleted; usage metadata is retained for the term of
the Agreement. Conversation Content is used only to (a) diagnose and resolve support issues raised by the
Customer, (b) evaluate answer quality against the Customer's own reference questions, and (c) tune prompts and
model selection for the Customer's deployment. It is not used to train foundation models and is not shared with
third parties other than the model providers already named in the Agreement, which receive it transiently to
generate answers. Where the Service is deployed in the Customer's cloud account, Conversation Content never
leaves that account. The Customer may opt out of Conversation Content recording at any time by written notice,
after which only usage metadata is recorded; opting out may limit Flynapse's ability to diagnose answer-quality
issues. On termination, Conversation Content is deleted within thirty (30) days.

## Appendix B — Detail-plan template (per phase)
Header (goal, spec sections, branch, worktree), Global constraints (inherited), File structure, Tasks with:
Files (create/modify/test), Interfaces (consumes/produces), Steps (write failing test → run → implement → run →
commit by pathspec), Acceptance, Review triage table.
