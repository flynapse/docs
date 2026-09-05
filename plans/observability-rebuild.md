# Observability Rebuild — Implementation Plan (master)

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (one fresh
> subagent per task, review between tasks) or superpowers:executing-plans. Steps use checkbox syntax for
> tracking. This is the **master** plan: each phase gets a detail plan
> (`docs/plans/observability-rebuild-phase-<id>.md`, task-level, test-first) written at phase start —
> after the migration gate (§2) for every app-dependent phase, because the base code will have moved.

**Goal:** Replace the decorative telemetry estate with a backend-agnostic OTel contract, a collector-profile
swap layer (`oss` one-box / `aws` CloudWatch), real traces/metrics/logs, LLM/agent observability on top of
the cost ledgers, a Postgres-backed product dashboard, and an eval workbench — per the ruled spec.

**Architecture:** every service and the browser emit OTLP/HTTP to one gateway collector; only the collector's
profile overlay and IaC know the backend. Product analytics read Postgres, never the log store. LLM cost truth
stays in `llm_usage`/`llm_model_calls`; telemetry carries structure and cost attributes; content goes to a
tenant-scoped relation and, sampled, to Phoenix.

**Tech stack:** Python 3.11 / FastAPI / loguru; `opentelemetry-sdk 1.44.0` + contrib `0.65b0`;
`otel/opentelemetry-collector-contrib` (pinned); Loki/Prometheus/Tempo/Grafana (oss); CloudWatch OTLP
endpoints + `sigv4auth` (aws); Next.js 15.2.4 + OTel JS 2.x; Postgres with RLS; Arize Phoenix; Terraform.

**Spec:** `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` (rev 4, rulings 1–20 in §11).
**Research:** `docs/plans/observability-rebuild-audit.md`, `docs/plans/observability-rebuild-research/01..07`.

## Global constraints (from the spec; every task inherits them)
- Application code never learns the backend: OTLP/HTTP-protobuf, standard `OTEL_*` env only, no vendor SDKs.
- Resource identity: `service.namespace=flynapse`, `service.name`, `service.version`, `service.instance.id`,
  `deployment.environment.name`. W3C `tracecontext` in and out; no outbound `baggage`.
- No `session_id`, `user_id`, `enduser.id` or raw URL path on any metric; units declared; `{USD}` not `USD`.
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
| `core/**` (master), `dashboard/**` (agent_sdk), `iac/**` (main), `copilot-mro/deployment/**` | No | Streams I, F, P proceed now. |
| `copilot-mro/.../postgres_table_definitions_modules/{chat,llm_usage}.py`, `chat_history/blocks.py` | Indexes: no; `chat_turn_facts` writer: **yes** (block-save path) | Index lines + table definition now; the writer after the gate. |
| `copilot-mro/tests/e2e/**` (eval harness) | Tests only | Stream E harness side may proceed. |

Branch names: `obs-infra` (copilot-mro, deployment/ only, from `langgraph-merge`), `obs-utils` (utils, from
`langgraph-merge`), `obs-api` (api, from `langgraph-merge`), `obs-analytics` (core from `master`; dashboard
from `agent_sdk`), `obs-frontend` (dashboard from `agent_sdk`), `obs-iac` (iac from `main`). App-dependent
work branches from `langgraph-merge` **after** the gate as `obs-agent`.

## 2. The migration gate and the rescoping task (Gate M → Task R)

**Gate M — owner declares "migration landed"**: the LangChain batches the owner is running are merged into
`langgraph-merge` and no further batch is expected to touch the conflict zone for the duration of Stream L.

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
- [ ] R.4 Write the detail plans for phases 1b and 3 from the approved catalogue; re-check phases 5 and 7
      items that touch the conflict zone (`chat_turn_facts` writer, content-capture write site, harness hooks).

---

## 3. Streams and sequencing

Four streams start now in separate worktrees (owner: "as much as possible"); Stream L waits for Gate M.

| Stream | Phase(s) | Repos / branch | Depends on | Starts |
|---|---|---|---|---|
| **I — infra & profiles** | 0 (infra half), 2, 6 (oss dashboards/rules scaffold), 7 (Phoenix container) | copilot-mro `deployment/` (`obs-infra`), iac (`obs-iac`) | nothing | now |
| **U — telemetry library + gateway wiring** | 1a (utils), 1b-api (api gateway) | utils (`obs-utils`), api (`obs-api`) | nothing for 1a; 1a for 1b-api | now |
| **P — product analytics** | 5 | core (`obs-analytics`), dashboard (`obs-analytics`), copilot-mro table definitions (tiny) | nothing (writer deferred) | now |
| **F — frontend telemetry** | 4 | dashboard (`obs-frontend`) | P's ingest evolution for the switch-over only | now |
| **L — agent runtime** | 0 (app half), 1b-mro, 3, `chat_turn_facts` writer, content capture | copilot-mro (`obs-agent`), utils `llm.py` | **Gate M + Task R** | after gate |
| **D — dashboards & alerts** | 6 | copilot-mro `deployment/`, iac | catalogue (R.2) for LLM/agent views; instrumentor names for service views | service views now; agent views after R |
| **E — evals** | 7 | copilot-mro `tests/e2e` (harness), deployment (Phoenix) | Phoenix container (I); content copy needs L | harness + container now; wiring after L |

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

**App half (Stream L, after Gate M — or as an immediate owner-applied hotfix, recommended)**
- [ ] 0.5 Remove `query=request.message` from the two "Enhanced chat request received" log calls in
      `chat_management.py` and `query=` from the two memory-search log calls in `memory_index.py`; add
      `query_chars` (length) instead. Test: a unit test over the log call sites asserting no `query`/`message`
      kwarg (AST scan of the two modules, in `tests/unit/observability/test_no_user_content_in_logs.py`).
- [ ] 0.6 Delete the `/metrics` route in `copilot-mro/app/main.py`, the gateway redirect in `api/main.py`, the
      `X-Metrics-Token` gate and `prometheus_client` from all three `pyproject.toml`s. Test: route table
      assertion that no `/metrics` path is registered; dependency lint in the existing infra tests.

**Acceptance for phase 0:** compose stacks start with pinned images and no debug exporter; retention and auth
verified by the smoke; no user text in the four log calls; no `/metrics` route.

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

### 1b-mro — copilot-mro wiring (Stream L, after Gate M + R)
- [ ] 1b.7 `copilot-mro/app/main.py` and `core/__init__.py`: `bootstrap` via `setup_logging`; parser
      `__main__`s use `service.name=ingest-parser` + `parser.kind`. Weaviate connection-factory wrapper span;
      S3 wrapper span in `utils/s3_service`. Delete the six dead `document_hub_qna_*` constants. Tests per
      wrapper (span name/attributes) and a constants-absent test.
- [ ] 1b.8 Background roots: document-hub processing, improvement loop, data-discovery runner open spans with
      `tenant.id` and bind log context. Tests with the dynamic-loader pattern.

**Acceptance for phase 1:** `tests/integration/otel/` smoke proves request → DB/HTTP client spans → correlated
JSON log with trace id, through an in-memory exporter, in api; cardinality lint passes; no `OTEL_ENDPOINT`
reader remains; worker emits a root span.

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
      `otlp` → Tempo, `otlphttp` → Loki `/otlp` with the tenant header, `otlphttp` → Phoenix for `content`;
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
- [ ] 2.6 Terraform module `iac/modules/otel-gateway` for client accounts (ECS task definition + service,
      task role, log groups, SSM parameters for the overlay env); `examples/` with a plan test.
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

- [ ] 7.1 Phoenix container in the `oss` profile (existing Postgres, auth on, retention env, one project per
      tenant + `internal`); client-account variant in the `otel-gateway` module as an optional container.
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

## 14. Rescoping notes (filled at Task R)
_(empty until Gate M)_

## 15. Implementation notes / Learnings (per phase, filled as work lands)
_(empty)_

## 16. Future Improvements
_(empty)_

## 17. Lessons
_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule for next time)_

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
