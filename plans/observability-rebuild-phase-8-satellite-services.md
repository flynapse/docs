# Observability rebuild — Phase 8: satellite services (Telegram bot, Shift Optimizer) + shared OTel package

**Status:** OPENED 2026-09-10 (owner request: "can we add metrics, traces, and logs to the Telegram and Shift
Optimizer repos meanwhile?"). Build + Opus review now; **Fable review gate Sunday night 2026-09-13**; merges
HELD until that gate. Master plan: `docs/plans/observability-rebuild.md` §11b (this phase) and §15 (ledger).

**Goal.** Bring the two services the design spec left for "when next touched" (spec §2 non-goals, §10) onto the
§3.1 contract now, without touching the LangGraph conflict zone: the Telegram bot as a standalone OTel process
(traces, metrics, logs), the Shift Optimizer's solver runs as first-class spans/metrics inside the api process,
Grafana + CloudWatch dashboards for both, and the spec's deferred per-product **optimizer** tab on the settings
product dashboard (spec §7.3 "per-product tabs when those tenants exist"). The shared implementation moves from
`utils/utils/observability/` into a new lean package so a service that must not depend on `utils` can use it.

**Owner rulings 2026-09-10 (this phase):**
1. Telegram bootstrap = **extract a shared `flynapse-otel` package** (not an in-repo copy, not a full `utils` dep).
2. Telegram scope = **plumbing + existing signals as OTel metrics + Grafana panels**; the bot has no frontend, so no
   product-dashboard work for it. It will run on AWS eventually → its dashboards get the **`aws` dialect too**.
3. Shift Optimizer = backend signals **and** frontend product-dashboard panels (the deferred optimizer tab).
4. Execution = streams in parallel; Opus implementers + Opus adversarial reviewers now; a **second, Fable review
   phase** designed in chunks small enough to review one at a time (§8 below).

**Spec sections:** §3.1 (contract), §3.3 (instrumentation rules), §4 (backend foundation), §7.1/§7.3 (product
dashboard; per-product tab inherits the product capability), §9 (dashboards, both dialects), §10 (later services).

**Inherited constraints (master §1, §11a, §12):** no edits in the migration conflict zone; branch app repos from
their current mainline (`utils`/`api`/`copilot-mro` = `langgraph-merge`, `core` = `master`, `dashboard` =
`agent_sdk`, `shift-optimizer`/`telegram-bot`/`iac` = `main`); commit by pathspec, never `git add -A`; no
credentials in output, commits or screenshots; no user content in log fields or span attributes; plan files carry
no code; Terraform validated, never applied by agents; nothing pushed. Phase-8 specific: **all merges wait for the
Fable gate**; the shared `api/.venv` refresh (`env -u VIRTUAL_ENV poetry install` in `api/`) is a **merge-time
precondition** (Stream O adds a path dependency to `utils`), not a build-time one — every stream builds and tests
in its own or the `wt-obs-u` bundle environment with `PYTHONPATH` pinned; ≤3 agents concurrently (WSL memory).

---

## 1. Streams, worktrees, waves

| Stream | Scope | Worktree(s) / branch | Depends on | Wave |
|---|---|---|---|---|
| **O — shared package** | new repo `flynapse-otel`; `utils` re-export shim + dependency + test moves | new repo `/home/aditya/Code/flynapse-otel` (`main`); `/home/aditya/Code/utils-obs8` (`obs8-utils` off `langgraph-merge`) | nothing | 1 |
| **S — optimizer backend signals** | run/solve spans, metrics, health exclusion, logging completeness | `/home/aditya/Code/shift-optimizer-obs8` (`obs8-optimizer` off `main`); `/home/aditya/Code/api-obs8` (`obs8-api` off `langgraph-merge`) | nothing (uses the unchanged `utils.observability` API) | 1 |
| **PA8 — optimizer product tab** | core panel specs + dashboard registry entries for the `optimizer` tab | `/home/aditya/Code/core-obs8` (`obs8-core` off `master`); `/home/aditya/Code/dashboard-obs8` (`obs8-dashboard` off `agent_sdk`) | nothing | 2 |
| **D8 — dashboards, both dialects** | catalogue views 7+8, Grafana JSON, CloudWatch bodies, two alert rules | `/home/aditya/Code/copilot-mro-obs8` (`obs8-dashboards` off `langgraph-merge`, `deployment/**` only); `/home/aditya/Code/iac-obs8` (`obs8-iac` off `main`) | the pinned names in §3 (no code dependency) | 2 |
| **T — Telegram bot** | bootstrap via `flynapse-otel`, spans, metrics, logs, redaction, Docker/compose | `/home/aditya/Code/telegram-bot-obs8` (`obs8-telegram` off `main`) | O's package importable (path dep `../flynapse-otel`) | 3 |

Waves run as slots free up (≤3 agents: two implementers + one reviewer at any moment). Reviewers are fresh
agents briefed with this plan's stream section + the diff; findings are triaged by the session lead (real gap →
fix pass by the same implementer → re-verification by the same reviewer; intentional → §9 Future Improvements).
Every agent is reported as `name — model`; all agents in the build phase are **Opus 5** (Fable rate-limited until
the gate).

Worktree mechanics (memory: plain `git worktree` at sibling depth, `.env` symlinked, `env -u VIRTUAL_ENV
POETRY_VIRTUALENVS_IN_PROJECT=true` for any in-worktree install). Test environments: O's new repo gets its own
Poetry env; `utils-obs8` tests run from the `wt-obs-u` bundle with `PYTHONPATH=/home/aditya/Code/flynapse-otel:
/home/aditya/Code/utils-obs8`; S from the bundle with `PYTHONPATH` to `shift-optimizer-obs8` + main `utils`;
PA8 core from the bundle with `POSTGRES_DB=copilot_mro_test`; T in its own worktree env (`poetry install` there);
D8 needs `terraform validate` + the phase-6 dashboard guards only.

---

## 2. Stream O — `flynapse-otel` shared package

**Why a repo.** Every workspace package is its own git repo consumed by sibling path dependency (`../x`); the
Telegram image is built from its own repo with a widened build context, so the package must live outside `utils`.

**What moves (from `utils/utils/observability/`):** `bootstrap.py`, `resource.py`, `registry.py`, `tracing.py`
— everything that imports only the OTel API/SDK. **What stays in `utils`:** `intercept.py`, `log_bridge.py`,
`metrics.py` (legacy `MetricsService` compat) — all loguru-bound — and `logging_config.py`.

**Package shape** (`/home/aditya/Code/flynapse-otel`): Poetry project `flynapse-otel`, module `flynapse_otel`,
Python `^3.11`; pins `opentelemetry-api`/`sdk`/`exporter-otlp-proto-http` **1.44.0** and
`opentelemetry-instrumentation` + `-threading` **0.65b0** (the two constants are the single source every consumer's
drift-pin test reads); dev: pytest, `opentelemetry-test-utils`. Tests: two-level layout with `tests/_root.py` and
the two guards copied from `utils`; the moved `utils` tests (`test_bootstrap_process_env`, `test_bootstrap_in_process`,
`test_client_instrumentors`, `test_resource_identity`, `test_registry_rules`, `test_tracing_helpers`) land under
`tests/unit/{bootstrap,registry,tracing}/` with unique basenames.

**API changes while moving (the only deliberate ones):**
- `bootstrap(service_name, *, version, environment, pipelines, instrumentations)` — the instrumentor set becomes a
  **caller-declared tuple of names** resolved against a catalogue in the package (`psycopg2`, `psycopg`, `httpx`,
  `requests`, `urllib3`, `redis`, `threading`, `logging` …); the U9 semantics stay for declared names (missing
  package → WARNING, failed apply → WARNING, never raise); `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` still opts out.
  The `utils` wrapper passes the current six names, so no utils consumer sees a change.
- The package logs through **stdlib `logging`** (structured via `extra`), never loguru; `utils`' intercept still
  routes those records into loguru for api processes.
- `shutdown(timeout)` — flushes and shuts the three providers; idempotent; the bot's `post_shutdown` calls it.
- `attach_stdlib_logging(level, *, logger_names_pinned)` in `flynapse_otel.logging` — the SDK `LoggingHandler`
  on the root logger for stdlib-logging services (the bot). `utils` keeps the loguru bridge.
- Everything else (`state()`, `Pipelines`, `BootstrapState`, `_reset_for_tests`, the registry's unit allow-list
  and forbidden-attribute lint, `get_tracer`/`span`, the resource detector) moves unchanged.

**`utils` side (worktree `utils-obs8`):** `flynapse-otel = {path = "../flynapse-otel", develop = true}` in
`pyproject.toml`; `utils/utils/observability/{bootstrap,resource,registry,tracing}.py` become thin re-export
modules so every existing import path (`utils.observability.bootstrap`, `from utils.observability import
registry`, `utils.observability.tracing.get_tracer`, the copilot-mro `metrics` import) keeps working; the six
moved tests are deleted here; `tests/unit/packaging/test_otel_pins_utils.py` becomes a drift-pin test asserting
utils' instrumentor pins equal the package's contrib constant and that utils declares no SDK pin of its own; a new
smoke test proves `utils.setup_logging` still configures providers through the package.

**Docker/compose consequence (owned by T, designed here):** the bot's `poetry export` resolves the path dependency
relative to the project, so the Dockerfile copies the package from an **additional build context** named `otel`
to the path the lock file expects before exporting; `api/compose.yaml` declares
`build.additional_contexts.otel: ../flynapse-otel`; a plain `docker build` documents `--build-context`.

**Acceptance:** package suite green in its own env; utils suite green from the bundle env with the package on
`PYTHONPATH` (1082 baseline, minus the six moved files, plus the new smoke + drift-pin); api boots in the bundle
env (`Telemetry configured` line with the same six instrumentors); `grep` finds no `from loguru` under
`flynapse_otel/`; no consumer import path changed (grep across api/core/copilot-mro/shift-optimizer).

---

## 3. Signal catalogue (pinned so D8 builds in parallel)

Names are final for this phase; D8's reviewer diff-checks them against T and S once those land (phase-6 pattern).
All metrics go through the registry (unit allow-list: `seconds`, `USD`, `ratio`, else count; identity keys are
forbidden as metric attributes).

### 3.1 Telegram bot (`service.name=telegram-bot`, `service.instance.id`, `deployment.environment` from env)

| Kind | Name | Attributes / notes |
|---|---|---|
| span, root per update | `telegram.update` | kind CONSUMER; `telegram.update.kind` ∈ {message, command, callback_query, document, photo, other}; `telegram.command` (the command word only); `telegram.chat.type`; `telegram.user.id`; `enduser.id` + `tenant.id` once the identity is resolved; **no message text, no callback payload**; status ERROR + recorded exception on an unhandled handler error |
| span, child | `telegram.turn` | `telegram.lane`, `telegram.carrier`, `telegram.outcome`, `telegram.refund` (bool), `telegram.cost_usd`; children `telegram.turn.gate` / `.auth` / `.backend` / `.render` from the existing `TurnTiming` boundaries |
| span, root per job | `telegram.job` | `telegram.job.name` ∈ {digest, document_watch, manuals_poll}, outcome, error recorded |
| span, auto CLIENT | httpx | `url_filter` replaces the bot token path segment with `<redacted>` and strips every query string (presigned S3 URLs); PTB's own httpx client is covered by the same instrumentor; `traceparent` propagates into the api gateway |
| span, auto CLIENT | psycopg (3) | `db.statement` without parameters; pool workers on their own threads are fine (no span parent) |
| counter | `telegram.updates` | `kind`, `outcome` |
| up-down | `telegram.updates.active` | — |
| counter | `telegram.turns` | `lane`, `carrier`, `outcome`, `refund` (mirrors the existing `count()` key set) |
| histogram, seconds | `telegram.turn.duration` | `lane`, `outcome` |
| histogram, seconds | `telegram.turn.phase.duration` | `phase` ∈ {gate, auth, backend, render, photos} |
| counter, USD | `telegram.turn.cost` | `lane` (from the backend's `cost_usd`; token counts are not available to the bot) |
| counters | `telegram.uploads`, `telegram.provisionings`, `telegram.refusals` | the same attribute keys the matching `count()` lines carry today |
| counter | `telegram.jobs` | `name`, `outcome` |
| logs | stdlib root → OTLP | INFO and above; the `httpx` logger stays pinned to WARNING (token/presigned-URL leak guard); stdout format unchanged; trace/span ids attached by the handler |

Rule: **every existing `count()` line keeps emitting unchanged** (tests and README §11 pin the grammar); the OTel
metric is emitted beside it from the same call site.

### 3.2 Shift Optimizer (inside `service.name=api`; sub-app identity is the `/api/v1/optimizer/...` route)

| Kind | Name | Attributes / notes |
|---|---|---|
| span, root per run | `optimizer.run` | kind INTERNAL; **Link** to the request span that queued the background task (the server span has ended by then — a parent would be wrong); `optimizer.job.id`, `optimizer.run.id`, `tenant.id`, `optimizer.run.status` ∈ {completed, failed}, `optimizer.solve.status` ∈ {optimal, feasible, elastic, infeasible}, `error.type`; the exception `execute_run` swallows today is recorded on the span in `_record_failure` |
| span, child | `optimizer.solve` | around the CP-SAT solve (threadpool, CPU-bound); `optimizer.solve.workers`, `optimizer.solve.time_cap_seconds` |
| span, child | `optimizer.persist` | the output write |
| counter | `optimizer.runs` | `status`, `solve_status` |
| histogram, seconds | `optimizer.run.duration` | `status` (from the existing `perf_counter` timing) |
| histogram, seconds | `optimizer.solve.duration` | `solve_status` |
| up-down | `optimizer.runs.active` | — |
| gateway | health exclusion | `/optimizer/v1/health` joins `HEALTH_EXCLUDED_URLS` (api repo) so it stops emitting spans and request-duration samples; test asserts zero spans for it and one for a real optimizer route |
| logs | loguru → existing bridge | `execute_run` lines carry `run_id`, `job_id`, `tenant_id`; one line per lifecycle boundary (start / finish / fail) |

HTTP RED for optimizer routes needs nothing new — `http.server.request.duration` with the full mounted
`http.route` already exists (Stream U, D1).

### 3.3 Optimizer product tab (Postgres, RLS-bound, `optimizer_runs` / `optimizer_jobs`)

Tab id `optimizer`, appended to core `TABS` and the dashboard `ANALYTICS_TABS`; requirement constant
`OPTIMIZER_REQUIRES = ("view_dashboard", "optimizer")` (pattern of `DOCUMENT_HUB_REQUIRES`; the `optimizer`
capability exists in `core/core/authz/catalog.py` and in the dashboard `PERMISSION_NAMES`). Panel ids — identical
on both sides, added to the existing byte-identity drift test:

| Panel id | Variant | Rows |
|---|---|---|
| `optimizer_runs_over_time` | bucketed by `started_at` (timestamp column rule) | `bucket`, `completed`, `failed` |
| `optimizer_run_summary` | stat tiles | `runs`, `completed`, `failed`, `failure_ratio` (unit `ratio`), `median_duration` (unit `seconds`) |
| `optimizer_run_duration_histogram` | histogram (same 12-bucket rule as `chat_time_duration_histogram`) | `bucket_start`, `bucket_end`, `bucket_label`, `count` |
| `optimizer_top_jobs` | ranked, limit 10 | `job_id`, `job_name`, `runs`, `last_status`, `last_run_at` |
| `optimizer_active_planners` | bucketed | `bucket`, `planner_count` (distinct `launched_by`) |

Empty-bucket and time-column conventions follow the phase-5 plan verbatim. The tab is hidden when the caller
lacks `optimizer`; the backend 403 stands on its own.

---

## 4. Stream S — Shift Optimizer backend signals

**Files (worktree `shift-optimizer-obs8`):** create `shift_optimizer/app/services/run_telemetry.py` (span + metric
helpers, imports `utils.observability` only — `ortools` stays lazily imported in `run_executor`); modify
`run_executor.py` (root span with the Link captured at enqueue time, phases, explicit exception recording,
lifecycle log lines), `app/api/jobs.py` (capture the request span context beside `background_tasks.add_task`),
`solver.py` only if the solve status is not already returned to the executor. Tests (two-level, in-memory exporter
from `opentelemetry-test-utils` in the api dev group): `tests/unit/telemetry/test_run_span_shape.py` (root span,
link present, attributes, exception recorded on failure, status enum values), `tests/unit/telemetry/
test_run_metrics.py` (counter/histogram names, units, attribute sets — through the registry lint),
`tests/api/telemetry/test_health_not_traced.py` in the **api** worktree (`api-obs8`) beside the existing gateway
tests. Logging-coverage checkbox per task (§11a).

**Steps per task:** failing test → run → implement → run → commit by pathspec; one commit per table row above.

**Acceptance:** optimizer suite green from the bundle env; api middleware lane green (253 baseline) plus the new
health test; a manual run in the live probe (§10) shows one `optimizer.run` trace with a link to the
`POST …/jobs/{id}/run` server span and the three metrics in Prometheus.

---

## 5. Stream T — Telegram bot

**Files (worktree `telegram-bot-obs8`):** `pyproject.toml` (path dep on `../flynapse-otel`; `opentelemetry-
instrumentation-httpx`, `-psycopg`, `-threading` at the package's contrib pin; lock regenerated in the worktree
env), `telegram_bot/telemetry.py` (bootstrap call with `instrumentations=("httpx", "psycopg", "threading")`,
the httpx `url_filter`, `attach_stdlib_logging`, the metric instruments from §3.1, the update/turn/job span
helpers, `shutdown` hook), `telegram_bot/app.py` (`main()` calls the bootstrap **before** the DB pool is built;
the traced application class via `ApplicationBuilder.application_class` so `process_update` opens the root span;
`post_shutdown` flushes), `telegram_bot/observability.py` (`count()` and `TurnTiming` emit the OTel twin beside
the log line), `handlers/chat.py` (turn span at `run_turn`, phase children at the `TurnTiming` boundaries),
`handlers/{digest,document_watch,manuals}.py` (job spans), `Dockerfile` + `.dockerignore` (additional context
`otel`, copied to the lock-relative path before `poetry export`; the import smoke also imports
`telegram_bot.telemetry`), `.env.sample` (`OTEL_*` keys documented; `OTEL_SDK_DISABLED=true` is the documented
local default when no collector runs), `README.md` §11 (one paragraph: the same counters now also ship as OTel
metrics; log grammar unchanged). `api/compose.yaml` (`additional_contexts`) is hand-carried by the session lead
at merge (the api worktree belongs to Stream S).

**Tests (two-level; in-memory exporters; PTB fakes from `tests/unit/bot/_telegram_fakes.py`):**
`tests/unit/telemetry/test_update_span.py` (one root span per update, kind/attributes, error status, no text
attribute ever — assert against a message whose text is a sentinel), `test_turn_span_phases.py`,
`test_httpx_url_redaction.py` (**no bot-token substring and no `X-Amz-` query in any exported attribute** for a
Telegram API call and a presigned-URL download), `test_metrics_beside_count_lines.py` (each `count()` key →
metric with the same attributes; the caplog grammar tests still pass unchanged), `test_stdlib_logs_to_otlp.py`
(a WARNING reaches the in-memory log exporter with trace correlation; an `httpx` INFO line does not),
`test_shutdown_flushes.py`, `test_otel_pins_bot.py` (drift-pin against the package constants), and an updated
`tests/unit/infra/test_import_provenance.py` if it enumerates allowed third-party imports.

**Acceptance:** bot suite green in the worktree env; `docker build` of the image succeeds with the additional
context (smoke stage imports the telemetry module); live probe (§10) shows a trace that starts at
`telegram.update` and continues into the api gateway's SERVER span.

---

## 6. Stream PA8 — optimizer product tab (core + dashboard)

**core (`core-obs8`):** `resources/analytics/panels/optimizer.py` (five `PanelSpec`s, registered via
`panels/__init__.py`), `registry.py` (`optimizer` tab, `OPTIMIZER_REQUIRES`), `tests/fixtures/analytics_seed.py`
(seed `optimizer_jobs`/`optimizer_runs` for two tenants), `tests/db/analytics/test_panels_optimizer_db.py`
(exact rows for tenant A, isolation for tenant B, empty window → `[]`), `tests/unit/analytics/
test_analytics_registry.py` (tab and requirement gating: holder of `view_dashboard` alone → 403), the panel-id
drift test extended. Verify first that `optimizer_runs`/`optimizer_jobs` carry the tenant RLS policy under
`flynapse_readonly` (they are tenant-keyed; the panel repository runs under the request binding) — if the policy
is absent the panels are **not registered** and the gap goes to §9.

**dashboard (`dashboard-obs8`):** `analytics-panel-registry.ts` (five entries, `tab: 'optimizer'`, `requires:
[VIEW_DASHBOARD, OPTIMIZER]`), `analytics-api.ts` (ids + row types), `chat-quality-panel-utils.tsx` (labels),
tests `tests/unit/analytics/analytics-panel-registry.test.ts` (tab hidden without `optimizer`, visible with it;
ids byte-identical to the backend list fixture). No new FE events (the facts come from Postgres — the research-07
LATER items #22/#23 stay deferred).

**Acceptance:** core db lane green (`POSTGRES_DB=copilot_mro_test`), dashboard tests exit 0, the drift test counts
42 + 5.

---

## 7. Stream D8 — dashboards, both dialects

**Files:** `copilot-mro/deployment/otel/dashboards/CATALOGUE.md` (views 7 `fn-telegram-bot` and 8
`fn-shift-optimizer`, each with the operator question, signals, panel table, alert rows, and the `aws` field-path
caveat), `deployment/observability-local/grafana/provisioning/dashboards/flynapse/telegram-bot.json` and
`shift-optimizer.json` (phase-6 conventions: datasource uids, dark-panel marker only where a series is not yet
emitted — none expected here; the guard tests in `tests/integration/otel/` extend their fixture lists), the oss
alert rules file (two rules: `TelegramTurnFailureRate` > 20 % over 15 m, `OptimizerRunFailureRate` > 30 % over
30 m, Slack + email routes as phase 6), `iac/cloudwatch_dashboards.tf` (two `aws_cloudwatch_dashboard` bodies in
the Query Studio PromQL dialect) and the alarm dialect phase 6 chose (the owner's alarm-dialect ruling still
pending → same interim), `VERSIONS.md` untouched.

**Telegram panels:** updates/min by kind; turns/min by outcome and by lane; turn p50/p95 and phase breakdown;
cost per hour and cost per turn (with the ledger-honesty footnote: bot cost is the backend's reported
`cost_usd`); refusals / uploads / provisionings; Telegram API client latency (`http.client.request.duration`
filtered to `server.address=api.telegram.org` — verify the httpx instrumentor emits it at 0.65b0; else a span-
derived Tempo panel); backend error ratio as seen by the bot; WARN+ log stream; trace-search link.
**Optimizer panels:** runs/hour by status; solve-status mix; run and solve p50/p95; active runs; HTTP RED for
`http.route=~"/api/v1/optimizer/.*"`; failures log stream (`run_id`, `job_id`); trace-search link.

**Acceptance:** dashboard guard tests green; `terraform validate` green; a Grafana render in the live probe (§10)
shows non-empty telegram and optimizer panels.

---

## 8. Review design — two phases

**Phase A (now, Opus 5):** one fresh adversarial reviewer per stream, briefed with that stream's section of this
plan + the diff, running the suites itself; triage by the session lead; fix pass; re-verification. Each reviewer
ends by writing a **review brief** into §11 of this file: scope, branch + commit range, what was checked, findings
with their triage rulings, residual risks it could not verify. That brief is what the Fable reviewer starts from.

**Phase B (Fable, Sunday night 2026-09-13, after the owner's LangGraph phase-6 merge):** five bounded chunks,
reviewed **one at a time** with a fresh Fable agent each, in this order — the order is the merge order:

| Chunk | Scope | Why its own review |
|---|---|---|
| **R0** | **The design itself** (this plan: §2 package split, §3 catalogue, §6 tab, §7 boards, the review/merge design) — against the spec and the surveyed facts, before any code is looked at | owner ruling 2026-09-10: "Fable will have to review not just the code implemented, but also the design"; the design was written and built on Opus, so Fable rules on it first — a design correction rescopes the code chunks below before they are reviewed |
| R1 | Stream O (package + utils shim) | estate-wide import surface; the only change that can break every process |
| R2 | Stream S + the api health exclusion | small; merge-sensitive (api on `langgraph-merge`) |
| R3 | Stream PA8 | RLS + capability gating on a new product surface |
| R4 | Stream T | the standalone service; secret-redaction is the P0 |
| R5 | Stream D8 | cross-stream name check against the landed T/S code; two dialects |

R0 is a read-only design review with a written verdict per decision in §8a (keep / change / reject, with the
reason); every "change" becomes a fix task on the affected stream before that stream's code chunk runs.
Each code chunk: reviewer reads the brief → re-runs the suites → tries to break it → verdict; fix pass on Fable if
needed → **merge that chunk** before starting the next. R1's merge is followed by the shared-env refresh and an
api boot check before R2 starts. If Fable's limit falls mid-gate, the remaining chunks wait; nothing is merged on
an Opus-only verdict.

---

### 8a. Design decisions for R0 (what Fable rules on, with the alternatives that were considered)

| # | Decision (as built) | Alternatives considered | Why this one |
|---|---|---|---|
| D-1 | Shared implementation extracted into a new sibling repo `flynapse-otel` consumed by path dependency; `utils.observability` stays as a re-export shim | (a) in-repo copy of the bootstrap in the bot; (b) bot depends on full `flynapse-utils`; (c) sub-package inside the utils repo | owner chose extraction; a repo (not a utils sub-directory) because every workspace package is a repo consumed via `../x` and the bot image is built from its own repo with an additional build context |
| D-2 | Package API changes limited to five: caller-declared `instrumentations` names against a catalogue; stdlib logging inside the package; `shutdown()`; `attach_stdlib_logging()`; scope name `flynapse_otel` | keep the fixed six-instrumentor list; keep loguru; no shutdown API | the bot has psycopg 3 and no loguru; a standalone process must flush on SIGTERM; a package used by the bot cannot label its scope `utils` |
| D-3 | Telegram root span per **update** (CONSUMER) via the PTB application class, turn/phase children from the existing `TurnTiming` boundaries, job spans for scheduled work | per-handler spans; per-turn only; a `TypeHandler` in a negative group (cannot close the span after later groups run) | one span per unit of work the bot receives; the phases are already measured |
| D-4 | Existing `count()`/`TurnTiming` log lines stay byte-identical; OTel metrics emitted beside them | replace the lines with metrics | tests + README §11 pin the grammar; log lines remain the offline story |
| D-5 | httpx auto-instrumentation kept for the Telegram API (latency is real signal) with a `url_filter` redacting the bot token and stripping every query string | exclude `api.telegram.org` entirely via `OTEL_PYTHON_HTTPX_EXCLUDED_URLS` | keep the signal, remove the secret; a test asserts no token/`X-Amz-` in any exported attribute |
| D-6 | Optimizer run = its own root span with a **Link** to the request span (which has already ended when the `BackgroundTask` runs) | parent the run to the server span (would parent to an ended span); make the endpoint synchronous | matches OTel guidance for work that outlives its trigger; the estate's `run_span.py` pattern |
| D-7 | Optimizer metrics emitted from the api process under `service.name=api` with `optimizer.*` names (no separate service name) | a distinct `service.name=shift-optimizer` resource for the sub-app | one process = one resource; the route prefix and metric names identify the product |
| D-8 | Optimizer product tab = 5 Postgres panels under the existing panel registry, gated `view_dashboard` + `optimizer`, no new FE events | FE events for run triggered/exported (research-07 #22/#23) | the facts already exist in `optimizer_runs`; FE-only gestures stay deferred |
| D-9 | Dashboards in both dialects now (Grafana JSON + CloudWatch bodies), AWS deployment itself still deferred | oss only until AWS deploy | owner: the bot will run on AWS; the catalogue invariant is "edit both dialects" |
| D-11 | **Found at D8 review, needs an R0 ruling:** the gateway's ASGI middleware records `http.server.request.duration` AFTER a Starlette `BackgroundTask` finishes (upstream `finally` after `self.app`), so the optimizer run route's HTTP latency includes the whole solve. Phase-8 mitigation as built: the run route is excluded from the optimizer HTTP p95 panel and from phase 6's `ApiP95LatencyHigh`; panel/catalogue text says to read solve time from `optimizer_solve_duration_seconds` | (a) gateway records the duration at response end (custom hook/span processor — affects every background-task route estate-wide); (b) the run endpoint schedules the solve outside the request lifecycle (`asyncio.create_task`/threadpool) so the response is the end of the request; (c) accept the exclusion | plan §3.2's "HTTP RED needs nothing new" was wrong at design level; (a) is the principled fix but touches the shared gateway; (b) changes optimizer run semantics — Fable rules |
| D-10 | Two-phase review: Opus adversarial now → Fable gate in chunks R0–R5, merge per chunk, nothing merged on an Opus-only verdict; shared-env refresh after R1 | merge after Opus review; one big Fable review | owner: Fable limit returns Sunday; one review per bounded chunk keeps each within a session |

## 9. Future Improvements
- **Gateway duration recorded after background work (D-11).** Every route that queues a Starlette `BackgroundTask`
  reports its HTTP duration including that task. Deferred to the R0 ruling; the complete fix is a gateway-side
  hook that closes the request duration at the final response send, with a test on a background-task route.
- **CloudWatch `attributes.tenant.id` path.** The log bridge renames `tenant_id → tenant.id`; Logs Insights parses
  dots as nesting, so the D8 queries' `attributes.tenant_id` is probably wrong — already RE-VERIFY-flagged for B1b.
- **Telegram `lane` is single-valued today** (`copilot` is the only `count(TURNS…)` call site); the by-lane panels
  become useful when other lanes emit.

## 10. Live probe (after all merges; session lead runs it)
Smoke overlay collector (`flynapse-otel-probe` compose project, loopback remaps) + api via the shared env + the bot
from its own env with `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318` and `OTEL_SDK_DISABLED` unset; one
Telegram turn from the owner's phone (owner action) → Tempo shows `telegram.update` → `telegram.turn.backend` →
api SERVER span; one optimizer run through the dashboard → `optimizer.run` trace with its link; Prometheus has
the §3 metrics **and** `http_client_request_duration_seconds{server_address="api.telegram.org"}` (the httpx client histogram the Telegram board reads — free-text VERIFY marker, not a guarded DARK marker) plus `traces_spanmetrics_calls_total{service="telegram-bot"}`; Loki shows `severity_text`/`run_id` as structured metadata; Grafana renders both new boards; Loki carries `telegram-bot` logs with trace ids and no token or
presigned URL anywhere (grep the raw stream). Teardown by port + `compose down -v`.

## 11. Review briefs (Phase A output; input to Phase B)
_(one subsection per stream, written by each Opus reviewer, with the session lead's rulings folded in)_


### Stream O — review brief (reviewer Opus 5, 2026-09-10; verdict **MERGE-READY** for chunk R1)
**Scope.** `flynapse-otel` `main` f058771 → f0c6432 (P2-7 parallel per-provider shutdown landed, 160 tests); `utils-obs8` `obs8-utils` 4602211 → c8efbe3
off `langgraph-merge`.
**Checked.** Both suites before/after the fix pass (154 → 160 / 1023); bundle api unit suite against the shim (406) and
the boot check (six instrumentors); line diffs of the four moved modules vs `langgraph-merge`; AST import-surface +
consumer grep; wheel build/METADATA; utils lock diffs (one `[[package]]` block, then content-hash only); nested
path-dep resolution + a dry-run install against api's committed lock; scope-name grep over dashboards/collector/iac;
logging-handler probes (levels, no-bootstrap, disabled, `basicConfig(force=True)`, exporter-failure visibility);
concurrency, shutdown-under-load, drain, reset-after-timeout, interpreter-exit probes; layout guards; workflow copy.
**Findings → rulings.** P1-1 `shutdown` bound not honoured → FIXED fa9c623 (no `force_flush`; provider shutdowns on
a daemon thread joined with the bound; blocking-exporter test). P1-2 api `poetry install` from the committed lock
never installs `flynapse-otel`, and that lock's utils url is the stale `../../utils-obs` (pre-existing from the
obs-api merge) → **merge precondition: `poetry lock` then `poetry install` in `api/`** (session lead, R1 merge).
P1-3 utils wheel would carry a `file://` requirement its own workflow refuses; new repo had no publish workflow →
FIXED 78e6d77 + c8efbe3 (estate triple-form dependency + explicit `codeartifact` source in utils; `package.yml` copied
to the new repo); remaining owner steps: GitHub secrets on the new repo, first CodeArtifact publish, source flip at
publish time. P2-1/P2-2 attach semantics → FIXED dbffeb7 (repeat call lowers, never raises; re-adds after
`basicConfig(force=True)`). P2-6 catalogue entries unexercised → FIXED 01f9756. P2-4 name shadowing → README.
P2-7 (re-verification): sequential provider shutdown left SDK atexit hooks armed past the bound (~15 s exit delay
measured) → ruled FIX (one thread per provider, shared deadline). P2-3 (boot-time degradation WARNINGs reach stderr
via `lastResort` before the intercept installs — same visibility as before) and P2-5 (`INSTRUMENTATIONS` shape, no
consumer) → recorded only.
**Residual risks.** GitHub secrets + first publish; T's use of `shutdown`/`attach` ordering; `psycopg`/`logging`
entries against a real DB/logging setup; the shared `api/.venv` once actually re-locked and refreshed.

## 12. Implementation notes / Learnings (per stream, as work lands)

### Stream O — landed 2026-09-10 (implementer Opus 5; commits flynapse-otel f058771→c1102db, utils-obs8 4602211, 0cb4afd)
Package: `flynapse_otel/{bootstrap,resource,registry,tracing,logging}.py`, `SDK_VERSION`/`CONTRIB_VERSION`,
154 tests (47 infra guards + 63 moved + 44 new) in its own env. utils: path dep + SDK pins dropped (five client
instrumentor pins kept), lock regenerated with zero version churn, shims + wrapper (`_reset_for_tests` also resets
the utils postgres cursor factory — that hook cannot live in the package), six tests moved, smoke + drift-pin
tests added; 1082 → 1023 (−63 moved, +4 new). Boot check green with the six instrumentors. Deviations accepted at
triage: instrumentation scope renamed `utils.observability` → `flynapse_otel` (nothing keyed on it; the reviewer
re-greps dashboards/collector configs); `attach_stdlib_logging(level, *, pinned_loggers)` also walls off the
`opentelemetry` logger tree (the G22 export-failure loop guard `utils.intercept` has); `instrumentations`
defaults to `()` and unknown names raise before the singleton check; `shutdown()` leaves `state()` set; the dev
group carries the five client instrumentors so the instrumentor tests run against real packages.
Learnings: `import flynapse_otel.bootstrap as b` gives the FUNCTION (the `__init__` re-export shadows the module)
— use `importlib.import_module`; under the bundle env run poetry with `env -u VIRTUAL_ENV` (the shell's
`VIRTUAL_ENV` silently points poetry at the 1.37 env); the SDK `LoggingHandler` is deprecated in 1.44 (kept, same
as `log_bridge`); Poetry 2.3.2 has no `lock --no-update` — plain `lock` is the no-update mode.

### Stream S — landed 2026-09-10 (implementer Opus 5; shift-optimizer-obs8 2afb6b6..2941bf2 + follow-up; api-obs8 d63097b)
`run_telemetry.py` (span + four metric helpers, in-memory test lane), `run_executor.py` (own `optimizer.run` trace
linked to the queueing request span; `optimizer.solve`/`optimizer.persist` children; exception recorded + ERROR
status; failure counted before the terminal DB write so an outage cannot lose it; lifecycle log lines with
`run_id`/`job_id`/`tenant_id`), `jobs.py` (request span context captured beside `add_task`), `solver.py` (the
worker count and deterministic cap become public constants so the span reads the real parameters). Gateway:
one anchored regex excludes every mounted sub-app `/api/v1/<mount>/v1/health` (sub-paths stay traced); test in
`api-obs8/tests/middleware/telemetry/`. Counts: optimizer 662 → 682 passed (+20; 62 pre-existing `tests/api`
errors — the local `shift_optimizer_test` DB fails utils' `rls_boot_check` until the owner re-runs
`provision_rls.py`); api middleware 253 → 260. A scratch probe with the real app under `instrument_gateway`
confirmed the linked trace, the four metrics, and the untraced health route. Triage: solver constants accepted;
`optimizer.solve.time_cap_seconds` RENAMED `optimizer.solve.deterministic_time_cap` (the value is CP-SAT dtime,
not wall seconds; no board reads it); the "run failed" line is WARNING with `error_type` only (the exception
message can quote user-authored formulas — it stays in the row's `error` column and the span event); an invisible
run (RLS/no row) gets ERROR status but no terminal `optimizer.run.status`/counter. Follow-up ruled from D8's
cross-check: explicit seconds histogram boundaries on both duration histograms.
Learnings: `poetry run` inside `wt-obs-u/api` resolves to the STALE shared `api/.venv` unless prefixed
`env -u VIRTUAL_ENV POETRY_VIRTUALENVS_IN_PROJECT=true` (applies to runs, not only installs); **the gateway ASGI
middleware records `http.server.request.duration` AFTER the BackgroundTask runs, so the run route's HTTP latency
includes the whole solve** (upstream behaviour — boards must read solve time from the run histogram);
`tests/smoke/imports/test_import_smoke.py::test_import_is_fast` is load-sensitive and fails cold at the branch
base too.

### Stream D8 — landed 2026-09-10 (implementer Opus 5; copilot-mro-obs8 4bab848e, d4bda565; iac-obs8 01f3644)
Grafana `telegram-bot.json` (uid `fn-telegram-bot`, 18 panels) + `shift-optimizer.json` (uid `fn-shift-optimizer`,
12 panels); CATALOGUE views 7/8 with `aws` notes + two alarm-translation rows (gated on the PromQL-alarm ruling);
`rules/prometheus/flynapse-satellite-alerts.yml` (`TelegramTurnFailureRate` >20 %/15 m critical,
`OptimizerRunFailureRate` >30 %/30 m warning, volume-guarded); `docs/runbooks/observability/alerts.md` stub
sections (outside `deployment/**` — accepted: the committed guard requires a runbook anchor per alert); guards
extended (8 uids, 4 rule files / 12 alerts, provisioning smoke imports `EXPECTED_UIDS`); iac: two D7-subset
CloudWatch bodies (Logs Insights `log` + `text` PromQL widgets only). Verification: otel lane 62/9 unchanged,
rules guard 12, `validate-rules.sh` green (promtool ×4, amtool), Grafana cold-boot smoke 2 passed (all 8 boards
provision), 30 PromQL expressions promtool-parsed, `terraform validate` success, 8 bodies parse. Uncommitted
2-line `deployment/observability-local/README.md` (six → eight boards) — pre-existing file, landed by the session
lead at merge. Deviation accepted: the cost counter's Prometheus name is **`telegram_turn_cost_total`** (the
registry spells the unit `{USD}`, and a braced unit gets no suffix — same as phase 6's `agent_model_cost_usd_total`);
plan §3.1 "USD" means `{USD}`. Learnings: the otel lane needs `POSTGRES_DB=copilot_mro_test`; a Grafana-provisioned
JSON does not prove PromQL syntax — promtool over synthetic recording rules does; the SDK default histogram
buckets are useless for 10–120 s turns/runs → explicit boundaries ruled for S and T.

### Stream PA8 — landed 2026-09-10 (implementer Opus 5; core-obs8 ed22e1f + follow-up; dashboard-obs8 0dc631b)
Tenancy gate PASSED before registering anything: `optimizer_runs`/`optimizer_jobs` are `tenancy="tenant"` in the
shift-optimizer table definitions, their `<table>_isolation` FOR ALL policies (`tenant_id =
current_setting('app.tenant_id', true)`) are live on both `copilot_mro_test` and `copilot_mro` with
`relforcerowsecurity=t`. core: `panels/optimizer.py` (five specs), `registry.py` (`optimizer` tab,
`OPTIMIZER_REQUIRES`), two-tenant seed, 30 db tests, registry/gate tests, endpoint contract tests (403 without
`optimizer`, 200 with); dashboard: five `PANEL_REGISTRY` entries, tab/label/types, 51 analytics tests, `tsc` clean;
the settings page is registry-driven and unchanged. Drift fixture `EXPECTED_PANELS` = 47 on both sides (phase-5
approach: transcribed, core compares per-tab sets, dashboard keeps order). Deviations accepted: bucketed rows use
`bucket_start` (the FE time-series variant reads it); run moment = `COALESCE(started_at, finished_at)` (a run that
fails before inputs resolve has no `started_at` and would vanish from the failure ratio); `optimizer_top_jobs`
renders as `table` (the `ranked` builder is document-shaped — same choice as `automation_spend_vs_budget`), LEFT JOIN
so a deleted job's runs still rank; `failure_ratio = failed/(completed+failed)` over terminal runs, `median_duration`
+ histogram over completed runs only; summary tiles answer `[]` on an empty window. Pre-existing defect found and
ruled FIX in this stream: 9 `tests/api/analytics` endpoint-contract tests red on `master` since 2026-09-08 because
the seed's fixed `NOW = 2026-09-01` aged out of the endpoint's real-clock `1w` window — fixed by anchoring the
endpoint seed to the real clock. Counts: core analytics lanes 186 → 220 passed (+ the 9 after the fix); dashboard
46 → 51.

## 13. Lessons
_(plan-scoped; append after any owner correction)_
