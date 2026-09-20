# Observability rebuild — Phase 8: satellite services (Telegram bot, Shift Optimizer) + shared OTel package

**Status:** OPENED 2026-09-10 (owner request: "can we add metrics, traces, and logs to the Telegram and Shift
Optimizer repos meanwhile?"). **Phase A (build + Opus adversarial review) CLOSED 2026-09-11** — all five streams built, reviewed, fix-passed and
re-verified; **merges HELD for the Fable gate Sunday night 2026-09-13** (agenda §8b, progress §1a). Master plan: `docs/plans/observability-rebuild.md` §11b (this phase) and §15 (ledger).

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
in its own or the `wt-obs-u` bundle environment with `PYTHONPATH` pinned; ≤3 agents concurrently at first, raised to 5 by the owner on 2026-09-10 (WSL memory).

---

## 1. Streams, worktrees, waves

| Stream | Scope | Worktree(s) / branch | Depends on | Wave |
|---|---|---|---|---|
| **O — shared package** | new repo `flynapse-otel`; `utils` re-export shim + dependency + test moves | new repo `/home/aditya/Code/flynapse-otel` (`main`); `/home/aditya/Code/utils-obs8` (`obs8-utils` off `langgraph-merge`) | nothing | 1 |
| **S — optimizer backend signals** | run/solve spans, metrics, health exclusion, logging completeness | `/home/aditya/Code/shift-optimizer-obs8` (`obs8-optimizer` off `main`); `/home/aditya/Code/api-obs8` (`obs8-api` off `langgraph-merge`) | nothing (uses the unchanged `utils.observability` API) | 1 |
| **PA8 — optimizer product tab** | core panel specs + dashboard registry entries for the `optimizer` tab | `/home/aditya/Code/core-obs8` (`obs8-core` off `master`); `/home/aditya/Code/dashboard-obs8` (`obs8-dashboard` off `agent_sdk`) | nothing | 2 |
| **D8 — dashboards, both dialects** | catalogue views 7+8, Grafana JSON, CloudWatch bodies, two alert rules | `/home/aditya/Code/copilot-mro-obs8` (`obs8-dashboards` off `langgraph-merge`, `deployment/**` only); `/home/aditya/Code/iac-obs8` (`obs8-iac` off `main`) | the pinned names in §3 (no code dependency) | 2 |
| **T — Telegram bot** | bootstrap via `flynapse-otel`, spans, metrics, logs, redaction, Docker/compose | `/home/aditya/Code/telegram-bot-obs8` (`obs8-telegram` off `main`) | O's package importable (path dep `../flynapse-otel`) | 3 |

Waves run as slots free up (≤3 agents at first; the owner raised the cap to 5 on 2026-09-10, so waves 2 and 3
overlapped wave 1's reviews). Reviewers are fresh
agents briefed with this plan's stream section + the diff; findings are triaged by the session lead (real gap →
fix pass by the same implementer → re-verification by the same reviewer; intentional → §9 Future Improvements).
Every agent is reported as `name — model`; all agents in the build phase are **Opus 5** (Fable rate-limited until
the gate).

### 1a. Progress

- [x] Plan written (b2c71b8); R0 design chunk + §8a decision table added on owner request (9f78191)
- [x] O — built, reviewed, fixed, re-verified: `flynapse-otel` f0c6432, `utils-obs8` c8efbe3
- [x] S — built, reviewed, fixed: `shift-optimizer-obs8` f2591ef, `api-obs8` f8ff271
- [x] PA8 — built, reviewed, fixed, re-verified: `core-obs8` 6c97af7, `dashboard-obs8` bb78344 (46 panels)
- [x] D8 — built, reviewed, fixed, re-verified: `copilot-mro-obs8` ba14daa3, `iac-obs8` 094869d
- [x] T — built, reviewed, fixed twice: `telegram-bot-obs8` 0c55122
- [x] Fable R0 — design review DONE 2026-09-13 (reviewer Fable 5; brief in §11, full text
      `copilot-mro/.dev_runs/obs8-fable-gate/R0-design-review.md`): D-1…D-9 KEEP, each re-verified at source;
      D-10 CHANGE (§8b mechanics amended — post-merge lanes + moved-base rule); D-11 RULED (a) metric-only,
      fix in R2, exclusions revert in R5; D-12 RULED (a) gateway strip+inject, fix in R2, panel re-entry
      stays deferred; findings F-1…F-10 dispositioned in the brief
- [ ] R0 fix passes (before the affected chunk's review). DONE flynapse-otel @ `25dc158` (Opus 5; 164 passed;
      propagators needed `set_global_textmap` too — `opentelemetry.propagate` builds its composite at its own
      import, so the env setdefault alone was dead letters; mutation-proven). DONE telegram-bot-obs8 @
      `909510e` (Opus 5; F-1 type-keyed: any `telegram.Update` among a record's args → `Update(update_id=…)`
      stand-in in the OTLP copy only, the sole INFO+ model-object log site in PTB 22.8, mutation-checked,
      telemetry lane 75 passed; F-7b mypy override dropped, same 4 pre-existing errors; F-6 DEFERRED — see
      the deferred list). DONE api-obs8 @ `92a9006` (Fable 5; D-11a seam (a) held — subclass at the sole
      install site re-times both semconv histograms at upstream's own final-send condition, F-10 folded in
      (`active_requests` decrements at response end too), never-completing responses keep upstream behavior;
      D-12a strip+inject at `OptimizerPermissionMiddleware.dispatch`, identity = Cognito `sub` — the same
      value the gateway publishes as `X-Auth-User-ID`, deliberately not the `internal_user_id` surrogate;
      middleware lane 273, mutation-checked both fixes; known environmental: `test_pool_instrumented`
      connection-refused, local Postgres down; bundle `flynapse_utils.pth` still points at deleted
      `utils-obs` — main `utils` on `PYTHONPATH` is the workaround). DONE D8 trees @ `c29cc24a` /
      `36a982e` (Opus 5; true revert — alert rule byte-identical to pre-mitigation; F-4 line in CATALOGUE
      §7; no guard-test edits needed — the guards pin structure, not query text; otel lane 64/7, promtool
      live, terraform validate clean). ALL R0 FIX PASSES COMPLETE.
- [x] Fable R1 → MERGE-READY 2026-09-13 (no P0/P1/P2; three P3s → deferred list; brief:
      `copilot-mro/.dev_runs/obs8-fable-gate/R1-review.md` + §11): re-ran package 164 + utils 1023,
      independent estate-wide shim sweep with a live attribute-level probe, propagator import-order
      reasoning re-verified against installed SDK source, `py.typed` proven in wheel+sdist by rebuild;
      base unmoved. MERGED: utils `langgraph-merge` @ `718db0a` (`--no-ff`; only the 17 Stream O files;
      owner's uncommitted `utils/dev/.claude/CLAUDE.md` edit untouched); `flynapse-otel` stays `main` @
      `25dc158` (unpushed — GitHub copy lags at ed5f739 until owner pushes). Postconditions ALL GREEN
      2026-09-13: shared `api/.venv` refreshed (SDK 1.44.0 / contrib 0.65b0, flynapse-otel path dep; the
      repaired poetry.lock committed as api `langgraph-merge` `702c54f`); boot check from inside
      `flynapse_api/` (the `config` import resolves from there, not the repo root) → "Telemetry
      configured", service_name=api, six instrumentors [psycopg2, httpx, requests, urllib3, redis,
      threading]; utils 1023 + api middleware 253 (mainline baseline; 260 included Stream S's 7) from the
      shared env; OTLP connection-refused warnings = local collector down, environmental. BUNDLE ENV
      (`wt-obs-u`) RETIRED.
- [x] Fable R2 → MERGE-READY 2026-09-13 (no P0/P1/P2; three P3s; brief:
      `copilot-mro/.dev_runs/obs8-fable-gate/R2-review.md` + §11) and MERGED: shift-optimizer `main` @
      `23d3f2e`, api `langgraph-merge` @ `58a5c3b` (both `--no-ff`; api base drift = only the accounted
      `702c54f` relock). F-2 post-merge lanes on the MERGED trees: middleware 273, optimizer telemetry 23,
      both green from the shared env. Reviewer independently reproduced the D-11a mutation check, ran
      overlap + mid-body-exception probes (no cross-request bleed; gauge balanced on all four terminal
      paths), verified the D-12a identity byte-identical to `X-Auth-User-ID` at source, and found no route
      into the sub-app that skips the seam. P3s recorded: contrib trailers divergence (upstream's, subclass
      more correct than the span), proxy surface pinned to contrib version, ContextVar set/reset on
      excluded URLs (negligible). §11 S residual "run route duration includes the solve" RETIRED by
      `27c2351`; R5 still owes the exclusion reverts (already committed on the R5 branch).
- [x] Fable R3 → MERGE-READY 2026-09-13 (no P0/P1/P2; two P3s — future-status silence note + stale plan
      numbers, both plan spots fixed; brief: `copilot-mro/.dev_runs/obs8-fable-gate/R3-review.md` + §11)
      and MERGED: core `master` @ `a1a5f6c`, dashboard `agent_sdk` @ `6483a08` (both `--no-ff`, bases
      unmoved). Reviewer verified gating at three layers (mis-gated panel cannot register; per-capability
      deny matrix ran tonight; no route checks fewer capabilities), tenancy fail-closed in BOTH deployment
      shapes (`assert_rls_enforced` un-wrapped at boot + explicit `tenant_id` predicates in all four panel
      SQLs), D-12 grep-clean, fixtures byte-identical at 46. Suites: dashboard 51/51 + `tsc` clean; core
      121 passed / 127 skipped — every skip proven postgres-unreachable (DB down). OWED lanes CLEARED
      2026-09-13 after the owner restarted Postgres (container needed a second `docker start`; healthy on
      5432): db/analytics + api/analytics on merged core `master` = 156 ran, 0 failed, 0 skipped — R3's
      post-merge verification is complete.
      F-2 post-merge lanes on the MERGED trees (session lead): core unit/analytics + infra 119 green;
      dashboard `tsc` clean; analytics lane 51/51 — invocation note: the dashboard lane MUST use the
      repo's `test:unit` flags (`tsx --tsconfig tsconfig.test.json --test …`); a bare `tsx --test` fails
      the render tests with a phantom "React is not defined" (merged tree proven byte-identical to the
      reviewed branch before diagnosing — the 11 reds were invocation, not content).
- [x] Fable R4 → MERGE-READY 2026-09-13 (no P0/P1; five P3s → deferred list; brief:
      `copilot-mro/.dev_runs/obs8-fable-gate/R4-review.md` + §11; suite 2284/1, ruff clean, mypy same 4
      pre-existing; redaction attacked at all four places incl. live probes on the F-1 stand-in;
      propagation wire probe: traceparent in, baggage withheld) and MERGED: bot `main` @ `c6ee959` —
      preceded by the owner-approved WIP commit `f83f2fb` (owner's digest header-copy edit + wave6 notes;
      digest.py then auto-merged cleanly, delta verified = exactly the WIP). Hand-carry DONE: api
      `langgraph-merge` @ `7cd192f` (`additional_contexts: {otel: ../flynapse-otel}`). Bot env relocked +
      installed against the merged package (lockfile unchanged — the branch's committed lock was already
      right); full suite on merged `main`: 2284 passed / 1 skipped (4:51). Docker image rebuilt through
      the new additional context: `flynapse-telegram-bot:latest` Built, exit 0 — the D-1 build-context
      design and the poetry-export path pin are proven on the merged tree. R4 CLOSED.
- [x] Fable R5 → MERGE-READY AFTER FIXES 2026-09-13 (P1-1 runbook volume-guard wording + P2 phantom
      `manuals_poll`, both landed as `f03cb979`; three P3s → deferred list; brief:
      `copilot-mro/.dev_runs/obs8-fable-gate/R5-review.md` + §11; name check CLEAN — every queried
      series/label derived from emitter source + pipeline normalization; both dialects; lane 64/7 twice)
      and MERGED: iac `main` @ `7690c8d` (base unmoved; terraform validate + 8 templates parse post-merge);
      copilot-mro `langgraph-merge` @ `18909ee0` via the F-2 moved-base procedure — base had moved TWICE
      (owner's S4 gate merges: e421643c, then 5ddf0ba3): e421643c merged into the branch (`0be06fa3`,
      zero file overlap, otel lane 64/7 on the combination), e421643c..5ddf0ba3 verified to touch zero
      D8 paths, then `--no-ff`. Post-merge otel lane on the merged primary: first run failed
      `test_legacy_single_config_is_gone` on an EMPTY ROOT-OWNED DIRECTORY at
      `deployment/observability-local/otel-collector-config.yaml` — a stale docker bind-mount artifact
      of the crash-looping local stack, not the merge; `rmdir`'d, then 64/7 GREEN. (A stale container
      restarting with the old mount spec would recreate it — the owner's stack cleanup fixes it for
      good.)
- [ ] §10 live probe (session lead; one Telegram turn from the owner's phone) — OWNER RULING 2026-09-13:
      DEFERRED to the end of the whole gate ("no live test for now — we do that once everything is
      done"), batched with phase-9's extended re-probe. Stack prep for that pass: recreate the old
      `deployment` compose project from the current spec (its loki/tempo containers predate the
      `${VAR:-default}`/expand-env config style and crash-loop against the new files; the dead
      `deployment-otel-collector-1` still mounts the deleted legacy config and recreates the root-owned
      dir), and tear down the leftover `flynapse-otel-probe` overlay in the same pass. `down` without
      `-v` — volumes survive.
- [x] `flynapse-otel` pushed to GitHub 2026-09-11 — `github.com/flynapse/flynapse-otel` (private, repo created by the
      owner); `main` @ ed5f739 = a merge of GitHub's one-line README stub (e70f089) on top of the reviewed f0c6432, tree
      identical to f0c6432 (local SHAs preserved for the briefs); the push did not publish (the workflow publishes only
      on dispatch / `v*` tag / `[publish]` in the head commit)
- [ ] Owner: CI secrets on `flynapse/flynapse-otel` (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ROLE_ARN`),
      first CodeArtifact publish, utils source flip at publish time

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
- `shutdown(timeout_seconds)` — shuts the three providers on one daemon thread each against a shared deadline (no
  `force_flush`: SDK 1.44 ignores its timeout); the SDK drains the queues; one WARNING names any provider that missed
  the bound; idempotent; the bot's `post_shutdown` calls it last (as built after the O review).
- `attach_stdlib_logging(level, *, pinned_loggers)` in `flynapse_otel.logging` — the SDK `LoggingHandler`
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
All metrics go through the registry (registry unit allow-list as implemented: `1`, `s`, `ms`, `By`, `{USD}`,
`{token}`, `{request}`; identity keys are forbidden as metric attributes). The words `seconds`/`USD`/`ratio`
are the PA8 *panel-spec* vocabulary, not registry units — handing them to the registry is rejected (R0 F-8).

### 3.1 Telegram bot (`service.name=telegram-bot`, `service.instance.id`, `deployment.environment` from env)

| Kind | Name | Attributes / notes |
|---|---|---|
| span, root per update | `telegram.update` | kind CONSUMER; `telegram.update.kind` ∈ {message, command, callback_query, document, photo, other}; `telegram.command` (the command word only); `telegram.chat.type`; `telegram.user.id`; `enduser.id` + `tenant.id` once the identity is resolved; **no message text, no callback payload**; status ERROR + recorded exception on an unhandled handler error |
| span, child | `telegram.turn` | `telegram.lane`, `telegram.carrier`, `telegram.outcome`, `telegram.refund` ∈ {given, declined, failed} (the refund word, as built — not a bool), `telegram.refusal` on refused turns, `telegram.cost_usd`; children `telegram.turn.gate` / `.auth` / `.backend` / `.render` / `.photos` from the existing `TurnTiming` boundaries |
| span, root per job | `telegram.job` | `telegram.job.name` ∈ {digest, document_watch} (no manuals-poll job exists), outcome, error recorded (scrubbed) |
| span, auto CLIENT | httpx | as built: `UrlRedactingSpanProcessor.on_start` rewrites every URL attribute — the bot-token segment (matched by shape `bot\d+:[\w-]+`) → `<redacted>`, every query string dropped (presigned S3 URLs); sufficient because the instrumentor sets URL attributes at span creation (contrib 0.65b0 has no `url_filter`; its own `redact_url` does not cover `X-Amz-Signature`); `getUpdates` long-polls excluded by default (`OTEL_PYTHON_HTTPX_EXCLUDED_URLS=.*/getUpdates`, operator value wins); PTB's own client covered; `traceparent` propagates into the api gateway |
| span events / status | every exception the bot records | `record_failure(span, error)`: `exception.message`/`exception.stacktrace` pass the same token/URL scrubber; status description = the exception type name |
| span, auto CLIENT | psycopg (3) | `db.statement` without parameters; pool workers on their own threads are fine (no span parent) |
| counter | `telegram.updates` | `kind`, `outcome` ∈ {ok, error} |
| up-down | `telegram.updates.active` | — |
| counter | `telegram.turns` | `lane`, `carrier`, `outcome`, `refund` (mirrors the existing `count()` key set) |
| histogram, seconds | `telegram.turn.duration` | `lane`, `outcome`; buckets 1…600 s |
| histogram, seconds | `telegram.turn.phase.duration` | `phase` ∈ {gate, auth, backend, render, photos}; buckets 0.1…120 s |
| counter, `{USD}` | `telegram.turn.cost` | `lane` (from the backend's `cost_usd`; token counts are not available to the bot); Prometheus name `telegram_turn_cost_total` (a braced unit gets no suffix); **client-side mirror of backend-ledgered spend** — the api ledger's `agent.model` cost family counts the same dollars, so the two must never be summed (R0 F-4; CATALOGUE carries the same line) |
| counters | `telegram.uploads`, `telegram.provisionings`, `telegram.refusals` | the same attribute keys the matching `count()` lines carry today (as built: refusals carry `carrier`/`chat_type` and no `lane` on stale/maintenance/group/invite refusals; provisionings carry `created`); `user`, `age_seconds`, `citations`, `cost_usd`, `*_ms` never become labels |
| counter | `telegram.jobs` | `name`, `outcome` ∈ {ok, error, cancelled} |
| logs | stdlib root → OTLP | INFO and above; the `httpx` logger stays pinned to WARNING; as built: a never-raising filter on the OTLP handler ships a scrubbed COPY of each record (body, `exception.*` from `exc_info`, string and string-sequence extras — token shapes and URL queries removed); stdout format unchanged; trace/span ids attached by the handler |

Rule: **every existing `count()` line keeps emitting unchanged** (tests and README §11 pin the grammar); the OTel
metric is emitted beside it from the same call site.

### 3.2 Shift Optimizer (inside `service.name=api`; sub-app identity is the `/api/v1/optimizer/...` route)

| Kind | Name | Attributes / notes |
|---|---|---|
| span, root per run | `optimizer.run` | kind INTERNAL; **Link** to the request span that queued the background task (the server span has ended by then — a parent would be wrong); `optimizer.job.id`, `optimizer.run.id`, `tenant.id`, `optimizer.run.status` ∈ {completed, failed}, `optimizer.solve.status` ∈ {optimal, feasible, elastic, infeasible}, `error.type`; the exception `execute_run` swallows today is recorded on the span in `_record_failure` |
| span, child | `optimizer.solve` | around the CP-SAT solve (threadpool, CPU-bound); `optimizer.solve.workers`, `optimizer.solve.deterministic_time_cap` (renamed from `time_cap_seconds` at S triage — the value is CP-SAT deterministic time, not wall seconds) |
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
| ~~`optimizer_active_planners`~~ | ~~bucketed~~ | DROPPED at PA8 review — `launched_by` carries no identity until D-12 is ruled; the tab ships four panels (46 total) |

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
`tests/middleware/telemetry/test_health_not_traced.py` (as built) in the **api** worktree (`api-obs8`) beside the existing gateway
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
the URL-redacting span processor and the OTLP log-route scrubber (as built — contrib 0.65b0 has no httpx `url_filter`), `attach_stdlib_logging`, the metric instruments from §3.1, the update/turn/job span
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

**core (`core-obs8`):** `resources/analytics/panels/optimizer.py` (four `PanelSpec`s — five as drafted,
minus `optimizer_active_planners` per D-12 — registered via
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
42 + 4 = 46 (as built — `optimizer_active_planners` dropped at review, D-12).

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
| D-5 | httpx auto-instrumentation kept for the Telegram API (latency is real signal); as built the secret is removed in three places because contrib 0.65b0 has no `url_filter`: a span processor rewriting every URL attribute at span start, a scrubber on recorded exception events/status descriptions, and a never-raising scrubbed-copy filter on the OTLP log route (PTB logs a rejected token verbatim); `getUpdates` long-polls excluded by default | exclude `api.telegram.org` entirely via `OTEL_PYTHON_HTTPX_EXCLUDED_URLS`; scrub in the collector instead of the process | keep the signal, remove the secret before it leaves the process; tests assert no token/`X-Amz-` in any exported attribute, event, status or log record, including a real `InvalidToken` through PTB's network loop |
| D-6 | Optimizer run = its own root span with a **Link** to the request span (which has already ended when the `BackgroundTask` runs) | parent the run to the server span (would parent to an ended span); make the endpoint synchronous | matches OTel guidance for work that outlives its trigger; the estate's `run_span.py` pattern |
| D-7 | Optimizer metrics emitted from the api process under `service.name=api` with `optimizer.*` names (no separate service name) | a distinct `service.name=shift-optimizer` resource for the sub-app | one process = one resource; the route prefix and metric names identify the product |
| D-8 | Optimizer product tab = 5 Postgres panels under the existing panel registry, gated `view_dashboard` + `optimizer`, no new FE events | FE events for run triggered/exported (research-07 #22/#23) | the facts already exist in `optimizer_runs`; FE-only gestures stay deferred |
| D-9 | Dashboards in both dialects now (Grafana JSON + CloudWatch bodies), AWS deployment itself still deferred | oss only until AWS deploy | owner: the bot will run on AWS; the catalogue invariant is "edit both dialects" |
| D-11 | **Found at D8 review, needs an R0 ruling:** the gateway's ASGI middleware records `http.server.request.duration` AFTER a Starlette `BackgroundTask` finishes (upstream `finally` after `self.app`), so the optimizer run route's HTTP latency includes the whole solve. Phase-8 mitigation as built: the run route is excluded from the optimizer HTTP p95 panel and from phase 6's `ApiP95LatencyHigh`; panel/catalogue text says to read solve time from `optimizer_solve_duration_seconds` | (a) gateway records the duration at response end (custom hook/span processor — affects every background-task route estate-wide); (b) the run endpoint schedules the solve outside the request lifecycle (`asyncio.create_task`/threadpool) so the response is the end of the request; (c) accept the exclusion | plan §3.2's "HTTP RED needs nothing new" was wrong at design level; (a) is the principled fix but touches the shared gateway; (b) changes optimizer run semantics — Fable rules |
| D-12 | **Found at PA8 review, needs an R0 ruling:** optimizer run attribution (`optimizer_runs.launched_by`) comes from a client-supplied `X-User` header that nothing sends (always `system`) — so `optimizer_active_planners` was DROPPED from the tab (46 panels) rather than shipped always-wrong | (a) the api gateway's optimizer shim (`routers/optimizer.py`, which already resolves the authenticated user for its permission middleware) strips any client `X-User` and injects the authenticated user id for the sub-app — also closes the spoofable-attribution gap; (b) the optimizer reads the identity from the gateway's auth context directly; (c) leave attribution as `system` | (a) is small, lives in the api repo, and fixes attribution for every optimizer write; the panel returns once identity is real |
| D-10 | Two-phase review: Opus adversarial now → Fable gate in chunks R0–R5, merge per chunk, nothing merged on an Opus-only verdict; shared-env refresh after R1 | merge after Opus review; one big Fable review | owner: Fable limit returns Sunday; one review per bounded chunk keeps each within a session |

### 8b. Phase A CLOSED 2026-09-11 — the Sunday-night (2026-09-13) Fable gate agenda

Every stream is built, adversarially reviewed on Opus 5, fix-passed and re-verified; all worktrees are clean and
nothing is pushed. Branch tips the gate reviews (a chunk's reviewer starts from its §11 brief + this table):

| Chunk | Tree → branch @ tip | Base | Suite evidence (last run) |
|---|---|---|---|
| R0 | this plan §8a (D-1…D-12) | spec §3/§4/§7/§9/§10 | — (design review) |
| R1 | `/home/aditya/Code/flynapse-otel` `main` @ 25dc158 (= f0c6432 + the R0 F-5/F-7 fix; f0c6432 was pushed as ed5f739 — GitHub README stub merged, tree unchanged); `/home/aditya/Code/utils-obs8` `obs8-utils` @ c8efbe3 | new repo; utils `langgraph-merge` 9f74a11 | package 164; utils 1023 (bundle env) |
| R2 | `/home/aditya/Code/shift-optimizer-obs8` `obs8-optimizer` @ f2591ef; `/home/aditya/Code/api-obs8` `obs8-api` @ 92a9006 (= f8ff271 + D-11a `27c2351` + D-12a `92a9006`) | `main` 6a70135; api `langgraph-merge` a19a931 | optimizer telemetry lane 23 (+ 683/1/62 pre-existing RLS setup errors); api middleware 273 |
| R3 | `/home/aditya/Code/core-obs8` `obs8-core` @ 6c97af7; `/home/aditya/Code/dashboard-obs8` `obs8-dashboard` @ bb78344 | core `master` 988571b; dashboard `agent_sdk` b87ced0 | core analytics + infra 275/0; dashboard 51/51, `tsc` clean |
| R4 | `/home/aditya/Code/telegram-bot-obs8` `obs8-telegram` @ 909510e (= 0c55122 + the R0 F-1/F-7b fix) | `main` 1961778 | 2282 passed / 1 skipped at 0c55122 + telemetry lane 75 at 909510e (full lane re-runs at the R4 review); ruff clean; docker build OK |
| R5 | `/home/aditya/Code/copilot-mro-obs8` `obs8-dashboards` @ c29cc24a (= ba14daa3 + D-11 exclusion reverts + F-4 catalogue line; `deployment/**` only); `/home/aditya/Code/iac-obs8` `obs8-iac` @ 36a982e (= 094869d + aws-dialect revert) | copilot-mro `langgraph-merge` 07c2d4ee; iac `main` 5996e5a | otel lane 64/7 incl. promtool re-run at c29cc24a (alert rule byte-identical to its pre-mitigation blob); terraform validate + 8 bodies parse re-run at 36a982e; Grafana cold-boot 2 |

**Merge mechanics per chunk (session lead, after each Fable verdict):** `--no-ff` merge into the base branch named
above (flynapse-otel is already on its own `main`); R1 additionally: in `api/` run `env -u VIRTUAL_ENV poetry lock`
(also repairs the committed lock's stale `../../utils-obs` url) then `env -u VIRTUAL_ENV poetry install`, boot-check
`import flynapse_api.main` → "Telemetry configured" with six instrumentors, then re-run the utils + api middleware
lanes from the SHARED env (the bundle env retires after this); R2/R3 are ordinary merges; R4 additionally hand-carries
`api/compose.yaml` → `telegram-bot.build.additional_contexts: {otel: ../flynapse-otel}`, then `poetry lock` +
`install` in the bot's own env against the merged package; R5 is an ordinary merge (the README edit is already
committed). Owner-side later: GitHub secrets on the new `flynapse-otel` repo, its first CodeArtifact publish, the
source flip at publish time (§9 / D-1). Then the §10 live probe. If a Fable verdict changes a design row in §8a, the
affected chunk gets a fix pass BEFORE its review, in this session on whatever model is available.

**R0 amendments to these mechanics (F-2, 2026-09-13):** (i) EVERY chunk's merge is followed by that chunk's suite
lane(s) run on the merged result — R2: optimizer telemetry + api middleware lanes; R3: core analytics/infra + the
dashboard targeted lane with `tsc`; R4: the bot suite in its own env; R5: otel lane + promtool + `terraform
validate`. A chunk is done when the merged base is green, not when the branch was — the estate has already eaten
one silent merge drop (the TanStack trial's seven `meta.telemetry` keys). (ii) Moved-base rule: the gate runs
after the owner's LangGraph merge, so a base tip may no longer equal the SHA pinned above (`langgraph-merge`
bases are the likely movers). If it moved: merge the current base into the branch, re-run that chunk's lane,
then `--no-ff` — a verdict does not transfer to an unverified combination.


- **Gateway duration recorded after background work (D-11) — RULED at R0 (2026-09-13): (a), metric-only.** The
  SERVER span already ends at the final body send (upstream-guaranteed); only the duration histogram records
  after the background task. Fix in R2 (api tree): the histogram records at the final response send; R5 then
  reverts the run-route panel/alert exclusions. Fallback (c) — keep the exclusions — only if the api implementer
  finds no clean seam short of forking upstream code.
- **CloudWatch `attributes.tenant.id` path.** The log bridge renames `tenant_id → tenant.id`; Logs Insights parses
  dots as nesting, so the D8 queries' `attributes.tenant_id` is probably wrong — already RE-VERIFY-flagged for B1b.
- **Registry forbidden-attribute list does not include per-entity ids** (`run_id`, `job_id`, `chat_id`,
  `block_id`, …) — only session/user/url keys. Widening it is a follow-up once every existing metric's
  attributes are audited — and the widened list must NOT include `tenant.id`: spec §6.3 deliberately puts
  `tenant.id` on the `agent.model.*` metrics (tenant count is in the tens), so a blanket identity ban would
  break spec-legal metrics at registration (R0 F-3 reword).
- **PTB logs the full `Update` repr at CRITICAL when context-building fails** — deferral OVERTURNED at R0
  (2026-09-13, F-1): the stdout exposure predates phase 8, but the OTLP route to the log store is what this
  phase created, and the no-user-content constraint is absolute. Fixed in the R4 fix pass: the never-raising
  scrubbed-copy filter replaces the `Update` arg with its `update_id` in the OTLP copy; stdout unchanged.
- **Optimizer run attribution (D-12) — RULED at R0 (2026-09-13): (a).** The gateway's optimizer seam strips any
  inbound `X-User` and injects the authenticated id (trusted-proxy pattern; fix in R2). `optimizer_active_planners`
  re-enters the tab as a small follow-up once attribution has accumulated real data — not tonight (it would render
  over a history that is 100% `system`).
- **Standalone shift-optimizer is uninstrumented** (R0 F-9): this phase covers only the gateway-mounted
  deployment (bootstrap lives in the api process; the anchored health regexes assume the mount and would also be
  defeated by a uvicorn `root_path`). Correct as scoped, but the standalone path must not be assumed covered.
- **`panels/optimizer.py` imports private helpers from sibling panel modules** (`_stamp_times` from `quality`,
  `_float` from `usage`); the elegant home is a `panels/_shared.py` — deferred to keep the PA8 diff minimal.
- **Telegram `lane` is single-valued today** (`copilot` is the only `count(TURNS…)` call site); the by-lane panels
  become useful when other lanes emit.
- **R1 review P3s (Fable, 2026-09-13; none block anything):** (P3-1) bootstrap's `operator_set` check for
  `OTEL_PROPAGATORS` is key-presence, so an EMPTY value both keeps baggage live (the SDK treats empty as
  unset) and suppresses the corrective swap — no estate config sets the variable today; fix by testing
  truthiness when next in the file. (P3-2) the `py.typed` exclude-guard is substring-based and would miss a
  wildcard exclude; the complete guard builds to a tmpdir and asserts wheel membership. (P3-3) the
  no-baggage pin is skipped on the `OTEL_SDK_DISABLED` path — harmless (no instrumentors inject there) but
  the invariant is per-mode, not structural.
- **R4 review P3s (Fable, 2026-09-13; none block anything):** (P3-1) `record_failure` renders
  `str(error)`/`format_exception` unguarded on the span route — an exception whose `__str__` raises would
  escape the recording path (the log route guards the same renders); (P3-2) a foreign-bootstrapped process
  (`configured_by_this_call` false) gets log pins re-applied but no `UrlRedactingSpanProcessor` —
  unreachable via the bot's own `main()`; (P3-3) a hand-built log record with `list`-typed args carrying
  an `Update` bypasses the stand-in (impossible via `Logger._log`); (P3-4) the HandlerStop and
  context-build-return paths lack explicit span-closure assertions (structurally guaranteed, source
  verified); (P3-5) a future `block=False` handler's failure lands after span close — safely ignored, not
  mis-marked; contract noted for when one appears.
- **R5 review P3s (Fable, 2026-09-13):** (P3-1) panel/CATALOGUE text credits a contrib `url_filter` that
  doesn't exist at 0.65b0 — the mechanism is `UrlRedactingSpanProcessor.on_start`; fix the wording on next
  touch. (P3-2) refusals: CATALOGUE presents `lane` as unconditional but the emitter drops it on
  invite/stale/maintenance/group refusals (sum-over-lane deliberately < total) — the query is honest, the
  text should say so; `created` is a real provisionings dimension the CATALOGUE omits. (P3-3) the aws
  dotted text-dialect carries two unit-suffix conventions (inherited from phase 6, instances added both
  sides) inside probe-gated widgets — B1 falsifies one family, sweep then; CATALOGUE's aws severity
  example omits `FATAL`.
- **`service.version` is `unknown` estate-wide, not just from the bot image** (R0 F-6, examined and deferred at
  the R4 fix pass 2026-09-13): the only in-tree lever is a whole-variable `OTEL_RESOURCE_ATTRIBUTES`, which
  compose's `env_file` replaces with no merge (`.env.sample` documents that same variable for
  `deployment.environment.name`), and the compose build path lives in `api/compose.yaml` — another tree. The
  correct fix is a merge seam in `flynapse_otel.resource` (compose-provided attributes merged with
  code-provided ones), done once for every service; no service in the estate sets `service.version` today.

## 10. Live probe (after all merges; session lead runs it)
Smoke overlay collector (`flynapse-otel-probe` compose project, loopback remaps) + api via the shared env + the bot
from its own env with `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318` and `OTEL_SDK_DISABLED` unset; one
Telegram turn from the owner's phone (owner action) → Tempo shows `telegram.update` → `telegram.turn.backend` →
api SERVER span; one optimizer run through the dashboard → `optimizer.run` trace with its link; Prometheus has
the §3 metrics **and** `http_client_request_duration_seconds{server_address="api.telegram.org"}` (the httpx client histogram the Telegram board reads — free-text VERIFY marker, not a guarded DARK marker) plus `traces_spanmetrics_calls_total{service="telegram-bot"}`; Loki shows `severity_text`/`run_id` as structured metadata; Grafana renders both new boards; Loki carries `telegram-bot` logs with trace ids and no token or
presigned URL anywhere (grep the raw stream). Teardown by port + `compose down -v`.

## 11. Review briefs (Phase A output; input to Phase B)
_(one subsection per stream, written by each Opus reviewer, with the session lead's rulings folded in)_

### R0 — Fable gate design review (reviewer Fable 5, 2026-09-13; chunk CLOSED)

Full text: `copilot-mro/.dev_runs/obs8-fable-gate/R0-design-review.md`. Every load-bearing fact was re-verified
at source (installed contrib 0.65b0, Starlette 0.48.0, PTB 22.8, httpx 0.28.1), not inherited from the Opus
briefs. Verdicts: **D-1…D-9 KEEP** — highlights: PTB's `process_update` control flow proves a negative-group
handler can never close a per-update span (D-3); contrib httpx has no `url_filter`, its own redaction misses
`X-Amz-Signature` and path segments, URL attributes are set once at span creation, and the instrumentor's
failure path adds only `error.type` — so the three-place scrub is necessary and complete for the routes that
exist (D-5); Starlette ends the SERVER span at the final body send before background tasks run, which makes the
Link the only honest relationship (D-6); bonus: bootstrap's semconv opt-in means the httpx client histogram the
Telegram board reads should exist, downgrading that §10 VERIFY risk. **D-10 CHANGE** — the §8b mechanics
amendments above (post-merge lanes for every chunk; moved-base rule). **D-11 RULED (a)**, narrowed to
metric-only (the span is already right; only the histogram lies) — fix in R2, exclusions revert in R5, fallback
(c) only if no clean seam. **D-12 RULED (a)** — gateway strip+inject at the `OptimizerPermissionMiddleware`
seam; the hole as built is spoofable attribution, not just an empty column; panel re-entry stays deferred.
Findings: F-1 PTB-CRITICAL `Update` repr = message text on the OTLP route, deferral overturned → R4 fix; F-2 =
the §8b amendments; F-3 registry-widening reword (never `tenant.id`); F-4 `telegram.turn.cost` mirror rule
(§3.1 + CATALOGUE in R5); F-5 `OTEL_PROPAGATORS` setdefault `tracecontext` in bootstrap → R1; F-6
`service.version` from the bot image → R4 if cheap; F-7 `py.typed` → R1 (+ bot override drop); F-8 §3 unit
vocabulary corrected; F-9 standalone shift-optimizer named as uncovered; F-10 `active_requests` shares D-11's
distortion (R2 assesses). Residual risks: Prometheus-side post-normalisation names (§10 probe), live RLS state
on the optimizer tables (R3 may re-probe via the owner), CloudWatch dotted-field semantics (B1b), the
`auth_context` user-id shape (R2's tests prove it), Docker rebuild of the path pin (R4 merge step), base drift
(handled procedurally by the moved-base rule). Rescope summary: R2 and R4 get pre-review fix passes; R5's fix
pass follows the D-11 outcome; R3 unchanged.

### R1 — Fable gate review (reviewer Fable 5, 2026-09-13; verdict **MERGE-READY**; MERGED as utils `718db0a`)

Full brief: `copilot-mro/.dev_runs/obs8-fable-gate/R1-review.md`. Suites re-run (package 164, utils 1023
from the bundle env — needs `POSTGRES_DB=copilot_mro_test`, a pre-existing guard); independent estate-wide
shim sweep incl. a live attribute-level probe proving shim objects are identical to package objects; the
R0 fix commit's propagator reasoning verified against installed SDK source (composite built at
`opentelemetry.propagate` import → the `set_global_textmap` swap is necessary; swap has no victim — zero
baggage/textmap consumers estate-wide; contrib binds `inject` by function, so the swap takes effect);
`py.typed` proven in wheel+sdist by empirical rebuild. No P0/P1/P2; three P3s recorded in the deferred
list. Moved-base check: utils base unmoved at `9f74a11`. Reminder it flagged: `flynapse-otel` `25dc158`
is unpushed — the GitHub/CodeArtifact copy lags until the owner pushes.

### R2 — Fable gate review (reviewer Fable 5, 2026-09-13; verdict **MERGE-READY**; MERGED as shift-optimizer `23d3f2e` + api `58a5c3b`)

Full brief: `copilot-mro/.dev_runs/obs8-fable-gate/R2-review.md`. Suites from the shared env: api-obs8
middleware 273, optimizer telemetry 23 (full optimizer suite 597/145-skipped — every skip is
postgres-unreachable, collection arithmetic exact: +23 vs base). The two post-Opus fix commits attacked
hardest: D-11a seam verified line-by-line against installed contrib 0.65b0, mutation check independently
reproduced, live overlap + mid-body-exception probes (no cross-request bleed, gauge balanced on all four
terminal paths); D-12a strip proven over raw ASGI byte pairs for every casing/duplicate, injected identity
verified byte-identical to `X-Auth-User-ID` at source, no bypass route into the sub-app. Stream S
re-derived against §3.2: catalogue exact, closed vocabularies enforced at emission, health exclusion
regexes literal-pinned with nothing wrongly silenced. Three P3s in the deferred list (trailers divergence
— upstream's; proxy surface pinned to contrib version; ContextVar on excluded URLs). D-12 acceptance (2)
proven at the exact-Header-contract level; the real DB row lands in the §10 probe. Base drift = only the
accounted `702c54f` relock.

### R3 — Fable gate review (reviewer Fable 5, 2026-09-13; verdict **MERGE-READY**; MERGED as core `a1a5f6c` + dashboard `6483a08`)

Full brief: `copilot-mro/.dev_runs/obs8-fable-gate/R3-review.md`. Re-derived the whole surface: gating
attacked at three layers with the deny matrix running DB-free tonight; tenancy fail-closed verified in
code (boot refuses an unpolicied DB in both deployment shapes; every panel SQL carries its own
`tenant_id` predicate — safe even with RLS off); panel SQL checked against the authoritative
shift-optimizer DDL; D-12 grep-clean; drift fixtures byte-identical (46). Suites: dashboard 51/51 + `tsc`
clean; core 121/0 with 127 skips positively identified as postgres-unreachable (the db-lane conftest's
closed skip vocabulary means no real failure can hide as a skip). Two P3s: future status values render
silently (closed vocabulary today); stale plan numbers (fixed). Owed: the 154 DB-bound tests on merged
`master` when Postgres returns, before §10.

### R4 — Fable gate review (reviewer Fable 5, 2026-09-13; verdict **MERGE-READY**; MERGED as bot `c6ee959`)

Full brief: `copilot-mro/.dev_runs/obs8-fable-gate/R4-review.md`. Suite 2284/1 (= Phase A + the 2 fix
tests), ruff clean, mypy unchanged. The P0 redaction surface attacked at all four places with live probes
(subclassed `Update`, mapping-form args, poisoned mapping, hostile repr — all held); PTB source re-walked
to confirm `process_update` is the only INFO+ site handing an `Update` to a log call; propagation proven
at the wire (traceparent injected, baggage withheld even when deliberately set). D-3's three control-flow
paths source-confirmed leak-free; every Phase-A ruled fix re-verified present. Five P3s → deferred list.
Merge preceded by the owner-approved WIP commit `f83f2fb` (digest header copy); `digest.py` auto-merged,
delta verified = exactly the WIP. Hand-carry: api `7cd192f`.

### R5 — Fable gate review (reviewer Fable 5, 2026-09-13; verdict **MERGE-READY AFTER FIXES**, landed; MERGED as copilot-mro `18909ee0` + iac `7690c8d`)

Full brief: `copilot-mro/.dev_runs/obs8-fable-gate/R5-review.md`. The name check — the chunk's whole
point — came back clean: every queried series/label derived from emitter source plus the collector's
name-normalization rules (forced `flynapse` namespace, `{USD}` no-suffix, semconv opt-in), checked
against the landed S/T/O code including the 11-word turn-outcome vocabulary and anchored-matcher
semantics. Tonight's revert commits verified as true reverts (alert rule byte-identical to
pre-mitigation; zero `jobs/[^/]` or `D-11` leftovers). Fixes: P1-1 runbook volume-guard wording and the
P2 phantom `manuals_poll` — landed as `f03cb979` pre-merge. Three P3s → deferred list. Lane 64/7 (twice
on the branch, once post-merge after removing a stale docker-created directory); iac `terraform validate`
+ 8 templates parse post-merge.

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

### Stream D8 — review brief (reviewer Opus 5, 2026-09-10, re-verified after the fix pass; verdict **MERGE-READY** for chunk R5)
**Scope.** copilot-mro-obs8 `obs8-dashboards` 4bab848e..ba14daa3 off `langgraph-merge` 07c2d4ee; iac-obs8 `obs8-iac`
01f3644..094869d off `main`. Read-only review; nothing edited by the reviewer.
**Checked.** Suites re-run after the fix pass (otel lane 64 passed / 7 skipped with `OTEL_RULES_CHECK=1` incl. promtool;
`validate-rules.sh`; `terraform validate` + `fmt -check`; 8 CloudWatch bodies parse; JSON structure, unique ids, no
grid overlap, no `"type": "metric"`; scope = 10 files under `deployment/**`, `tests/integration/otel/**`,
`docs/runbooks/observability/alerts.md`). Every optimizer series/attribute diffed against the landed S code; Telegram
assumptions checked against the bot's `count()` sites and enums (T not landed at review time); collector job/Loki/Tempo
label paths, bridge flattening, httpx 0.65b0 + ASGI middleware source, Tempo metrics-generator dimensions, estate
route grep for the D-11 exclusion, phase-6 D6/D7 conventions, alert hygiene, CloudWatch subset.
**Findings → rulings.** P1-1 the optimizer "run failed" line is WARNING by design (S) and the ERROR-only log queries
excluded it → FIXED both dialects. P1-2 `http.server.request.duration` is recorded after the BackgroundTask so the
run route's p95 is the solve → FIXED on the board + phase 6's `ApiP95LatencyHigh` (exclusion verified to hit only the
optimizer route: the other `/run` routes have no `/jobs/` segment); gateway-side fix = design item **D-11 for R0**.
P1-3 httpx records no duration sample on transport exceptions → the backend-error panel was blind to a down backend
→ FIXED (turn-outcome share + Tempo span-metrics client-error share per `server_address`). P2 text/guard items FIXED
(explicit buckets, `solve_status` semantics, guards `> 5` turns / `>= 3` runs aligned rule↔panel↔catalogue↔runbook,
single-valued lane note). Open: panel-14 B ratio unguarded (nit — no row = no errors); CloudWatch widget reads
`attributes.tenant_id` while the bridge emits `tenant.id` (B1b-gated RE-VERIFY); the free-text VERIFY marker is not a
guarded DARK marker (the httpx series is now listed in §10).
**Residual risks (live probe / later gates).** `http_client_request_duration_seconds{server_address}` presence;
`job="flynapse/telegram-bot"`, Loki `service_name="telegram-bot"`, the `telegram.*` names/keys once T lands (refusal
`age_seconds` must not become a metric attribute); `severity_text`/`run_id` as Loki structured metadata; span-metrics
`server_address` populated for the bot's client spans; CloudWatch field paths (B1b).

### Stream S — review brief (reviewer Opus 5, 2026-09-10; verdict **MERGE-READY** for chunk R2)
**Scope.** shift-optimizer-obs8 `obs8-optimizer` 2afb6b6..f2591ef (P2 fixes landed: containment guard, ids on the dead-write line, `METRIC_ATTRIBUTE_KEYS` enforced at emission; telemetry lane 23) off `main` 6a70135;
api-obs8 `obs8-api` d63097b..f8ff271 (literal pattern pinned; middleware lane 260) off `langgraph-merge` a19a931.
**Checked.** Suites re-run from the bundle env (optimizer 683 passed / 1 skipped / 62 pre-existing `tests/api` setup
errors — `RLSEnforcementError` from utils' `rls_boot_check` on the local `shift_optimizer_test` DB, untouched by the
stream; telemetry lane 21; api middleware 260, integration/otel 30, infra guards 66); ruff clean; diff confined to the
stream's files. Scratch probes under the real gateway + a real BackgroundTask: the SERVER span ends before the run
starts, `optimizer.run` is a parentless root with exactly one link to it (different trace id), solve/persist
parented; sampled-out / SDK-disabled / no-request callers harmless; counter exactly once per path (success, persist
failure, solve raise, invisible run, dead terminal write); `runs.active` never negative; seconds buckets on both
histograms; the exception event carries the message only (plus the standard stacktrace tail), no other attribute or
log field; health regex exercised against 16 URLs (only the three mounted `/api/v1/<mount>/v1/health` paths are
silenced; the gateway's own health and every sub-path stay traced); `ortools` stays lazy; D8's series names/labels
match what S emits.
**Findings → rulings.** No P0/P1. P2 (a) the `signals.failed()`/WARNING prologue sat outside `_record_failure`'s
containment guard → FIX; (b) the dead-terminal-write line lacked job/tenant ids → FIX; (c) `METRIC_ATTRIBUTE_KEYS`
decorative and the registry lint accepts `run_id`/`job_id`/`tenant_id` on metrics → FIX by enforcing at emission;
widening the package's forbidden list → §9 (R1 follow-up); (d) tautological `HEALTH ⊆ DEFAULT` test → FIX (assert
the literal); (e) hardcoded `/api/v1`/`/v1` prefixes + dead `(\?.*)?` group — consistent with the pre-existing
probe pattern, note only; (f) plan §3.2 still named `time_cap_seconds` → corrected above.
**Residual risks (live probe only).** Prometheus-side names after exporter normalisation; Tempo's rendering of the
link; psycopg2 child spans under `optimizer.run`/`optimizer.persist` on the real DB path; the run route's HTTP
duration includes the solve (D-11); first-boot `seed_if_empty` runs `execute_run` in-process and counts as real
runs; a uvicorn `root_path` deployment would defeat both anchored health patterns (none configured).

### Stream PA8 — review brief (reviewer Opus 5, 2026-09-10, re-verified after the fix pass; verdict **MERGE-READY** for chunk R3)
**Scope.** core-obs8 `obs8-core` 988571b..6c97af7 (ed22e1f, 0fa9765, 6c97af7); dashboard-obs8 `obs8-dashboard`
b87ced0..bb78344 (0dc631b, bb78344). Diff confined to `core/resources/analytics/{panels/optimizer.py,
panels/__init__.py,registry.py}` + tests/fixtures; dashboard registry/types/utils/api + one test. The tab ships FOUR
panels (46 total).
**Checked.** Suites re-run (core analytics lanes + infra 275/0; dashboard 51/51 via the repo's `tsx --test`; `tsc`
clean). RLS proven with the SQL tenant predicate stripped AND the LEFT JOIN tenant predicate stripped, under
`flynapse_app` (non-BYPASSRLS; FORCE + one FOR ALL policy per relation), unbound and cross-bound → never another
tenant's row or job name; endpoint 403 `forbidden` matrix for every id (`view_dashboard`-only, `optimizer_run` as a
substitute, `optimizer` alone), owner 200; every id serialises with the pinned keys across all five ranges; a
NULL-duration completed row is excluded from median/histogram; drift fixtures diffed by script (46/46, order
identical); the clock fix restores in `finally`, is hour-aligned UTC −1 d, and the api lane uses `1w`/`1m` only (no
hour-boundary flake); layout/basename/depth rules green.
**Findings → rulings.** P1-1 `optimizer_active_planners` had no identity signal (`launched_by` is an unsent client
header, always `system`) → ruled DROP; D-12 opened for gateway-injected identity; verified gone from both trees.
P2-1 FOR-ALL/FORCE pins extended to `optimizer_runs`/`optimizer_jobs` → 4 cases PASS. P2-2/P2-4 docstrings and
descriptions landed. P2-3 shared `_float`/`_stamp_times` helper → §9. P2-5 (`flynapse_readonly` holds SELECT on the
optimizer pair although `READONLY_SELECT_RELATIONS` omits them; it is not the panel executor) → observation.
**Residual.** Live `copilot_mro` RLS state re-probed by the implementer only (the reviewer had no psql client; the
DB MCP is manual-invoke only); no browser render of the tab — the live probe (§10) covers it.

### Stream T — review brief (reviewer Opus 5, 2026-09-10/11, re-verified after the fix pass; verdict **MERGE-READY AFTER FIXES — all ruled fixes landed (last: 0c55122, 2282 passed); the R1/R2/R3 re-verification is folded into Fable chunk R4** )
**Scope.** `telegram-bot-obs8` `obs8-telegram` 6443d89 → 0c55122 (9 commits) off `main` 1961778; path
dep on `flynapse-otel`; `api/compose.yaml` `additional_contexts` hand-carried at merge.
**Checked.** Suites before/after the fix pass (2267 → 2279 / 1 skipped), ruff, mypy (4 pre-existing); lock additivity;
Dockerfile stages/pins (build not re-run by the reviewer — stack busy; the implementer's build succeeded); contrib 0.65b0 httpx
attribute timing (URL attributes are set at span creation, so an `on_start` rewrite is sufficient; contrib's own `redact_url`
covers `Signature`/`sig`/`X-Goog-Signature` but NOT `X-Amz-Signature`, so the processor is necessary) + excluded-URL read timing;
PTB 22.8 exception messages and INFO+ log sites; flynapse_client error builders; in-memory probes for token/presigned leaks on
attributes, events, status, log bodies/attributes, resource; filter recursion/refusal/malformed-args/None-traceback;
concurrency (two overlapping updates → two roots), active gauge, kind vocabulary; `count()`-site label audit vs
`COUNT_DIMENSIONS` and D8's catalogue (`user`, `age_seconds`, `citations`, `cost_usd`, `*_ms` never become labels);
job-context inheritance before/after; bootstrap order (psycopg instrumentor wraps `Connection.connect`, so pooled
connections are covered regardless of pool timing).
**Findings → rulings.** P1-1 a rejected-token boot shipped the token in `exception.stacktrace` over OTLP (PTB `Bot.initialize`
+ networkloop `_LOGGER.exception`) → FIXED d1ee421 (`redact_text` + a scrubbed-copy filter on the OTLP handler; stdout
unchanged by ruling) + pin 56cddc5. P2-1 a stale, ended update span was marked on job failures scheduled from handlers →
FIXED (`job is None and is_recording()`; `job_span` clears the variable) + mutation-checked test. P2-2 unredacted exception
events/status descriptions (safe today only because dochub raises `from None`) → FIXED (`record_failure`) + dochub 403/
transport pins. P2-3 telemetry tests read the developer's `.env` → FIXED (`IsolatedSettings`, `env_file=None`). P2-4
`getUpdates` long-polls (~8.6k valueless root traces/day, skewing the Telegram-API latency panel) → FIXED
(`OTEL_PYTHON_HTTPX_EXCLUDED_URLS` set-default `.*/getUpdates`, operator value wins). P2-5 PTB CRITICAL `Update` repr on
context-build failure → §9. Re-verification: P1-R1 the scrub filter could RAISE at the logging call site on a `%`-args
mismatch (`Handler.handle` guards `emit` only; production-only) → FIX (never-raising filter + malformed-call test);
P2-R2 `_scrubbed_for_otlp` shipped as a log attribute → FIX (class-marked copy); P2-R3 sequence extras unscrubbed → FIX.
**Residual risks (live probe).** Docker build under the pinned poetry 2.4.1 / export 1.10.0 (`-e` rendering) re-verified
by the implementer only; pooled psycopg `db.*` spans against a real DB; the `telegram.turn.backend` → api SERVER join;
exporter-failure log feedback with the collector down; a Loki raw-stream grep after a deliberate bad-token boot (P1-1
proof); confirmation that no `getUpdates` CLIENT span reaches Tempo.

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
`optimizer`, 200 with); dashboard: four `PANEL_REGISTRY` entries (post-D-12), tab/label/types, 51 analytics tests, `tsc` clean;
the settings page is registry-driven and unchanged. Drift fixture `EXPECTED_PANELS` = 46 on both sides (phase-5
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

### Stream T — landed 2026-09-10 (implementer Opus 5; telegram-bot-obs8 `obs8-telegram`, 6 commits off `main` 1961778)
`telegram_bot/telemetry.py` (bootstrap via `flynapse_otel` with `("httpx","psycopg","threading")`, `TracedApplication`
opening the root `telegram.update` span in `process_update` with `process_error` marking it, turn/phase/job span
helpers, all §3.1 instruments with the ruled explicit buckets, `shutdown_telemetry`), `observability.py` (`count()`
emits the OTel twin beside the unchanged log line; `TurnTiming.traced()`), `app.py` (bootstrap after settings and
before the DB pool; flush last in `_close`), `handlers/chat.py` (turn span, phase children + a `telegram.turn.photos`
child, `telegram.refusal=<reason>`, identity from the production tier read), digest + document-watch job spans,
Dockerfile (additional build context `otel` → `/flynapse-otel`; the export plugin renders the path dep as
`-e file:///flynapse-otel`, a grep-pinned `sed` makes it a plain path requirement), `.env.sample`, README §5/§11.
Tests: 2206 → 2267 passed (61 new) in the worktree env; ruff clean; mypy = 4 pre-existing; `docker build` with the
additional context succeeded and the image applies the three instrumentors. Deviations accepted at triage:
contrib 0.65b0 has no httpx `url_filter` → redaction is a `SpanProcessor.on_start` rewrite of every URL attribute
(token segment by shape `bot\d+:[\w-]+`, query strings dropped whole) — the reviewer attacks event/log leak paths
the processor cannot see; no manuals-poll job exists (`telegram.job.name ∈ {digest, document_watch}`);
`telegram.refund` is the refund word (`given|declined|failed`), not a bool; `configure_telemetry` adopts only the
`OTEL_*` lines of `.env` into the environment (set-default) so bare `poetry run` honours the documented local
default; voice/payment updates classify as `other`. Label divergences vs the D8 boards (code keys kept, boards
adjust at R5 if needed): `telegram.refusals` carries `carrier`/`chat_type` and NO `lane` on stale/maintenance/
group/invite refusals; `telegram.provisionings` also `created`; `telegram.turn.duration` and `telegram.updates`
also `outcome`; `telegram.jobs.outcome ∈ ok|error|cancelled`. Hand-carry at merge (api repo): `api/compose.yaml`
`telegram-bot.build.additional_contexts: {otel: ../flynapse-otel}`. Package gaps to feed R1: no `py.typed` (mypy
override in the bot), no per-instrumentor hook pass-through in `bootstrap`, SDK `LoggingHandler` deprecation.
Learnings: PTB 22 `process_update` never raises for handler errors — override `process_error`; `httpx.MockTransport`
is not instrumented (only `AsyncHTTPTransport`) → redaction proven over a loopback server; `main()`-driving tests
bootstrap real exporters unless the root conftest defaults the SDK off; `service.version` is `unknown` in the image
unless `OTEL_RESOURCE_ATTRIBUTES` sets it.

### Post-review fix passes (Phase A, 2026-09-10/11)
- **O:** fa9c623 bounded `shutdown` (daemon thread, no `force_flush`) · dbffeb7 attach lowers-never-raises + re-adds
  after `basicConfig(force=True)` · 01f9756 every catalogue entry exercised · 78e6d77 publish workflow + README ·
  utils c8efbe3 triple-form dependency + explicit `codeartifact` source · f0c6432 one shutdown thread per provider
  (shared deadline; process exit 0.75 s where it was ~15 s). Package 154 → 160; utils 1023.
- **S:** 1949d96 explicit seconds buckets + attribute rename · f2591ef containment guard around the failure-signal
  prologue, ids on the dead-write line, `METRIC_ATTRIBUTE_KEYS` enforced at emission · api f8ff271 literal pattern
  pinned. Telemetry lane 20 → 23; middleware 260.
- **PA8:** 0fa9765 seed clock anchored for the endpoint tests (nine reds on `master` since 2026-09-08) · 6c97af7 /
  dashboard bb78344 `optimizer_active_planners` dropped (D-12), RLS pins extended to the optimizer pair, wording.
  Core 186/9 → 275/0; dashboard 46 → 51.
- **D8:** ba14daa3 / iac 094869d WARN+ failure-log queries, run route excluded from the p95 panel and from phase 6's
  `ApiP95LatencyHigh` (D-11), backend-error panel rebuilt from turn outcomes + span metrics, guards aligned, text.
- **T:** d1ee421 + 56cddc5 token/URL scrubber on the OTLP log route and on exception events/status, stale-span guard
  for job failures, tests isolated from the developer's `.env`, `getUpdates` excluded · 0c55122 never-raising scrub
  filter, class-marked copy, sequence extras. Suite 2267 → 2282.

## 13. Lessons
_(plan-scoped; append after any owner correction)_

- **The deferred stronger-model gate reviews the design, not only the code (2026-09-10).** Tried: a Fable gate made
  of code chunks only (R1–R5), with the design treated as settled because the owner had answered the scoping
  questions. Owner corrected: "Fable will have to review not just the code implemented, but also the design to begin
  with." Rule: when a build runs on a weaker model ahead of a stronger-model review, the design is its own first chunk
  (R0) with a decision table of the alternatives considered, and a design change rescopes the affected code chunk
  before that chunk is reviewed; design items found during the build (D-11, D-12) are added to the same table.
- **A service that will deploy to AWS gets both dashboard dialects from the start (2026-09-10).** Tried: scoping the
  Telegram boards as Grafana panels only (the owner's option pick). Owner added: the bot will run on AWS eventually,
  so its backend boards need AWS panels too. Rule: for any new service board, ask where the service will run and
  author the `aws` dialect alongside `oss` whenever AWS is a target, even while the AWS deployment itself is deferred.
