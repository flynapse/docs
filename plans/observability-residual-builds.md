# Observability Residual Builds — Implementation Plan

> **For agentic workers:** SDD-driven (owner, 2026-09-24: "sdd driven opus agents"). Controller = the
> owner's Opus session; implementers AND task reviewers = Opus 5.5 subagents, fresh agent per task, one
> implementer per working tree. Ledger: `/home/aditya/Code/.superpowers/sdd/observability-residual-builds/progress.md`
> (resolved by the SDD workspace script). Durable scratch: `~/.claude/scratch/obs-residuals/<lane>/`.
> Checkbox syntax tracks progress.

**Goal:** build the four implementable residuals the owner approved from the 2026-09-24 list of record
(master plan §18): the G.17 tenant-scoped instrument allow-list as code, the C4 compose resource budgets,
the I3 collector-restart proof, and the shared exception-text detector adopted beyond utils
(core → api → copilot-mro → telegram-bot → shift-optimizer, PP-TG-14 re-triaged inside the telegram lane).

**Model policy (owner, 2026-09-24):** Opus for every agent — implementers, task reviewers, the final
whole-batch review. Reviewers are fresh and adversarial and RE-RUN the named proofs (mutation runs,
red-befores): implementer reports are indexes, never evidence. Concurrency cap 2 (session default; the
owner may raise it).

**Evidence base (read-only recon, 2026-09-24; trust over plan prose):**
`~/.claude/scratch/obs-residuals/research/R1-detector-adoption.md` (detector census, five repos) ·
`~/.claude/scratch/obs-residuals/research/R2-mro-lane.md` (G.17 / C4 / I3 facts and test designs).
Trees at plan time: copilot-mro `1966f998` (langgraph-merge) · core `21cd644` (master) · api `a8a3fb2`
(langgraph-merge) · telegram-bot `47a08b7` (main) · shift-optimizer `f5f732c` (main, remote named `main`) ·
utils `4b67458` · flynapse-otel `438d768`.

## Global constraints

- No exception **message** text and no user content in any log record, span attribute, health body or
  persisted summary — type + frame headers only (`failure_fields` / `rendered_failure`).
- Every test run through `/home/aditya/Code/pytest-slot.sh -- <cmd>` from the shared `/home/aditya/Code/api/.venv`,
  `DEBUG=false`; `POSTGRES_DB=copilot_mro_test` where a conftest asks; `-n 2` for full lanes (two agents live);
  serial for DB lanes and lanes with a session-end exit check. Check pytest's OWN exit status, never a pipe's.
- Mutation proofs via `/home/aditya/Code/mutant.sh` (baseline-checked, cold bytecode) for every new guard; write
  the mutation and the failing test's name into the report.
- Worktrees at sibling depth `/home/aditya/Code/<repo>-res[-tag]`, `.env` symlinked in, worktree path in
  `.git/info/exclude`, `PYTHONPATH` pinned to the worktree first on every run. Commit early and often by
  named pathspec (`git commit -- <paths>`); never `git add -A`, never amend, never rebase or squash.
- Two-level test layout (kind, then domain), globally unique basenames, no depth-coupled paths
  (`tests/_root.py` helpers) — each repo's `tests/unit/infra` guards enforce this.
- Nothing merges before its task review closes (P0/P1 = Critical/Important block; P2/P3 → Future
  Improvements). Merges are local `--no-ff` into the repo mainline by the controller. **Nothing is pushed —
  the owner pushes.**
- No code snippets in this plan (workspace rule); tasks carry file:line targets.
- Executors do not edit this plan file; they report exact text for the controller to apply.

## Controller rulings (pre-flight; each also in the ledger)

- **R-G17-DOOR:** ship the ruled minimum — named literal + behaviour-derived equality guard. Making the
  recording door enforce the list needs a public `name` on flynapse-otel's instrument handles (a sibling-repo
  change) — NOT built; recorded in Future Improvements. Cost if wrong: the list is detected, not enforced, until
  that small follow-up.
- **R-C4-SYNTAX:** service-level `mem_limit` / `cpus` / `pids_limit` (the ruling's own words; Compose rejects
  mixing with `deploy.resources.limits` at distinct values), on BASE service blocks only; overlays declare none.
  The budget repeats across the six base files, held equal by one test literal. Cost if wrong: six-file edit to
  change a number.
- **R-I3-SCOPE:** the proof covers the oss profile's traces + logs (Prometheus remote-write has no file-backed
  queue by design), crash-and-replace (`kill -9` + a new container on the same volume), with a mandatory
  in-memory negative control. aws/azure/newrelic stay config-only (credentials). Cost if wrong: none — narrower
  than I3's full wording, which stays open for the other providers.

- **R-DET-TRIAGE** (amended 2026-09-24 at Task 5 review: a column/persisted leak with an in-repo precedent fix
  is FIXED, not registered): detector findings are registered with a TRUE dated reason of one of four kinds (SANCTIONED /
  OVER-REPORT / LATENT / OPEN LEAK); log/stdout leaks with the house fix are fixed pre-adoption; body/raise shapes
  whose fix changes an HTTP or error contract are registered OPEN LEAK and listed in Future Improvements (owner
  decision). Cost if wrong: copilot-mro's ~12 body-echo sites stay open until that decision.
- **R-DET-RETIRE:** an old guard retires only where the recon measured the detector flagging EVERY leak shape it
  pins, re-proved by replay in the lane (api logs + spans, copilot-mro spans + traceback bodies, telegram logs,
  shift spans + the exception-text half of its log guard); everything partial stays. Cost if wrong: a kept
  duplicate guard (harmless) or, for a retirement, a shape the replay did not cover.
- **R-DET-PPTG14:** PP-TG-14 re-triaged as a REAL stderr leak with a one-base drop-in fix (rebase `FailureFormatter`
  on `TypesAndFramesFormatter`) — fixed inside Task 7. Cost if wrong: the bot's stderr lines change shape for
  third-party records only. *This supersedes, for exception text ONLY, the earlier position that stdout/stderr prints
  third-party records verbatim; a library's own non-exception words still print as written (see OD-1 for the pilot
  words that still reach stderr through two PTB records).*

## Lanes and order

| Lane | Tree (worktree / branch / base) | Tasks | Merge into |
|---|---|---|---|
| M | `copilot-mro-res` / `res-mro` / `1966f998` | 1 → 2 → 3 | copilot-mro `langgraph-merge` |
| X-core | `core-res` / `res-detector` / `21cd644` | 4 | core `master` |
| X-api | `api-res` / `res-detector` / `a8a3fb2` | 5 | api `langgraph-merge` |
| X-mro | `copilot-mro-res-det` / `res-detector` / mro mainline AFTER lane M merges | 6 | copilot-mro `langgraph-merge` |
| X-tg | `telegram-bot-res` / `res-detector` / `47a08b7` | 7 | telegram-bot `main` |
| X-shift | `shift-optimizer-res` / `res-detector` / `f5f732c` | 8 | shift-optimizer `main` |

Slot A runs lane M; slot B runs the detector lanes in the merge plan's order; reviews take the next free slot.
Task 3 needs docker reachable from WSL (Docker Desktop's WSL integration is OFF at plan time — owner step), so it
runs last in lane M.

---

## Detector adoption recipe (shared by Tasks 4–8)

**Pattern:** utils' S5 adoption — `utils/tests/unit/observability/_exception_text_policy.py`,
`test_utils_exception_text_register.py`, `exception_text_register.json` (copy the shape, adapt per repo). Facts,
traps T1–T11 and per-repo numbers: R1 (`~/.claude/scratch/obs-residuals/research/R1-detector-adoption.md`);
the recon's probe scripts and raw findings are in `~/.claude/scratch/obs-residuals/recon-detector/` (reuse them).

**Commit sequence (T5 — the adoption commit may not delete a file):**
1. *Pre-adoption fixes* (only if the task lists any): one commit per fix, each with its own planted-leak test.
2. *Adoption commit:* policy module + register JSON + guard test (+ floors). The register EQUALS today's scan.
   `ADOPTED_AFTER` = this commit's parent; `AGAINST` = the repo's remote mainline ref (T6).
3. *Retirement commit(s)* (only where the task says RETIRE): delete the named old guard, after replaying its own
   leak corpus through the detector under the repo's policy and showing EVERY leak shape flagged. A rule the
   detector misses stays (keep the file, or split out the missed rule, as the task says).

**Register rulings (R-DET-TRIAGE):** every entry carries a dated reason that is TRUE of the site, in one of four
kinds — `SANCTIONED <why>` (refusal / kept type / carve-out not expressible as policy), `OVER-REPORT <evidence>`
(the detector flags text that provably is not exception text), `LATENT <why>` (text rides a raised message that no
sink renders today), `OPEN LEAK <sink>` (real, not fixed in this batch — also listed in the plan's Future
Improvements with file:line). A log/stdout leak with the house fix (constant message + `failure_fields`) is FIXED
pre-adoption, not registered; a body/raise shape whose fix would change an HTTP or error contract is registered
`OPEN LEAK`, never "fixed" by rewording a response the dashboard reads.

**Guard test requirements:** scan the task's roots once per process (the scan is expensive in copilot-mro — cache
it); non-vacuity (module-count floor + witness modules; a planted leak flagged and the sanctioned shape clean —
where a repo-local reader source exists, plant into `tmp_path` and `scan()` there, T4); register ⇔ scan equality
(`reconcile`); every entry declares its sites; register-only-shrinks and policy-only-narrows ratchets via
`merge_base_text(..., adopted_after=ADOPTED_AFTER, base_may_be_head=True)`; floors for every module with ≥ 3
`failure_fields` log calls in handlers (true count minus one), counting the repo's real logger names (T7).

**Proofs (each named in the report, re-run by the reviewer):** (a) ratchet green at HEAD; (b) a seeded new leak
in a production module turns the register test red (`mutant.sh`); (c) a grown register count and an added site turn
the ratchet red (edit a scratch copy committed on a throwaway branch, or the recon's ratchet probe); (d) each
retirement's per-shape replay table; (e) the repo's full unit lane + `tests/unit/infra` green.

**Merge:** controller merges with `--no-ff` (TRUE merge — never rebase or squash; the ratchet anchors on the
adoption commit). Nothing is pushed.

---

### Task 1: G.17 — the approved tenant-scoped instrument list as code (copilot-mro, lane M)

**Ruling:** owner approved G.17 packet rows 1–23 (2026-09-24, `privacy-logging-hygiene-batch.md` "G.17
packet"). Rows 1–15 are utils' and already live in utils' family registry (R2 §A5: equal). This task codifies
copilot-mro's rows 16–23. Evidence: R2 §A1–A4.

- [x] Add a named literal `TENANT_SCOPED_INSTRUMENTS` (frozenset of exactly the eight names `agent.turn.calls`,
  `agent.model.calls`, `agent.model.cost_usd`, `agent.model.unpriced_calls`, `agent.tool.calls`,
  `agent.tool.attempts`, `agent.subagent.calls`, `agent.ledger.write_failures`) to
  `copilot_mro/app/services/agent_shared/telemetry.py`, beside `_HISTOGRAM_WITHHELD_KEYS` (~:1416–1421), with a
  comment naming the ruling: an instrument gains `tenant.id` only by being added here.
- [x] New guard `tests/unit/agent_shared/test_tenant_scoped_instruments.py`, derived from BEHAVIOUR, not source
  text: build `RuntimeTelemetry` on an SDK `MeterProvider` with an `InMemoryMetricReader` (as
  `test_genai_metric_labels._telemetry` does), take a `for_turn` view carrying a tenant, drive every metric
  recorder (R2 §A4(b) lists them, including the priced and unpriced model-usage paths). Assert: (1) every
  instrument object on the telemetry instance produced at least one point (driver completeness — a new
  instrument the driver misses fails); (2) the set of metric names whose points carry `tenant.id` EQUALS the
  literal; (3) no histogram is in the literal or carries `tenant.id`.
- [x] Mutation proofs (each must turn the guard red; record mutation + failing test name): drop `tenant.id`
  from `for_turn`; add `tenant.id` to the subagent attributes of a non-listed path or a new counter; empty
  `_HISTOGRAM_WITHHELD_KEYS`; remove one name from the literal.
- [x] Text-only updates of the stale "G.17 is OPEN" prose: `tests/integration/otel/test_browser_derived_metrics.py`
  (~:28, :83, :301), `deployment/otel/base.yaml` (~:281, :287), `deployment/otel/README.md` (~:249). That test
  runs in the pytest+pyyaml-only CI lane — do not add imports to it.
- [x] Run: the new guard, `tests/unit/agent_shared/`, `tests/integration/otel/` (non-docker), `tests/unit/infra/`.
- Recorded fact (no change): in production only five of the eight counters carry a tenant today; the tool and
  subagent counters get one only through `for_turn`, because both runtimes bind those observers unscoped
  (`agent_pipeline.py:263-275, 691-699`). The ruled list keeps all eight (packet rows 20–22 "turn view").

### Task 2: C4 — declare the approved resource budgets in compose (copilot-mro, lane M)

**Ruling:** owner approved the C4 packet's budgets (2026-09-24): otel-collector 512 MiB · phoenix 2 GiB · loki
512 MiB · prometheus 512 MiB · tempo 256 MiB; `cpus: 1.0` and `pids_limit: 128` per service. Evidence: R2 §B.

- [x] Add service-level `mem_limit`, `cpus`, `pids_limit` (R-C4-SYNTAX) to every BASE definition of the five
  services (15 blocks) in: `deployment/docker-compose.yml`, `deployment/observability-local/observe-docker-compose.yml`,
  `deployment/poc/docker-compose.yml`, `deployment/demo/docker-compose.yml`, `deployment/docker-compose.phoenix.yml`,
  `deployment/poc/docker-compose.phoenix.yml`. Overlay blocks (no `image:`), including the smoke overlay and the
  phoenix files' otel-collector partials, get none.
- [x] New guard `tests/integration/otel/test_compose_resource_budgets.py`, pure YAML (runs in the CI otel lane),
  modelled on `test_grafana_service_health_and_env.py` (`_ComposeLoader` for `!override`/`!reset`, glob-found
  compose files, base blocks = those with `image:`): one `BUDGETS` literal citing the C4 ruling; every base block
  of the five services declares exactly it; no override block sets `mem_limit`/`cpus`/`pids_limit`/`deploy`; the
  scan finds at least 15 base blocks, per service (non-vacuity).
- [x] Mutation proofs: change one file's value; drop one block's key; add a key to an overlay — each red.
- [x] The commit message states the behaviour change: the collector's `memory_limiter` (`base.yaml:34-37`,
  80 %) now computes against the 512 MiB cgroup (~410 MiB hard / ~307 MiB soft) instead of host RAM.
- [x] If docker is reachable: render every touched stack with `docker compose config` and boot the C4 recipe
  (packet) once with the limits in force — all five healthy. If not reachable: record that the boot is owed.

### Task 3: I3 — the file-backed queue survives a collector crash (copilot-mro, lane M)

**Scope:** R-I3-SCOPE. Design and pitfalls: R2 §C3 (follow it; deviations need a reason in the report).

- [x] New `tests/integration/otel/test_collector_queue_survives_restart.py`, marker `compose_stack`, skipped
  unless `OTEL_COMPOSE_SMOKE=1` and `docker info` succeeds; stdlib + docker CLI only; raw `docker run` on a
  private network with pinned images from `_versions_md.image_pin` and ephemeral loopback ports, modelled on
  `test_alertmanager_delivery_failures.py:250-340`; reuse the smoke helpers rather than copying them.
- [x] Positive run: collector with `base.yaml` + `backend-oss.yaml` + `durability-production-oss.yaml` and a
  uid-10001-owned named volume at `OTEL_FILE_STORAGE_DIR`, backends absent; send N spans + N logs with unique ids;
  wait for the exporters' retry line (proves they reached the queue); `kill -9` and remove; start a new
  collector on the same volume; start Tempo + Loki under their aliases; within a ≥ 60 s deadline all N ids
  arrive; the new collector's `otelcol_exporter_sent_spans_total` / `…_sent_log_records_total` equal N exactly.
- [x] Negative control (mandatory): same flow without the durability overlay loses every pre-crash id (canary
  proves the backend path works; wait past `max_interval`).
- [x] Teardown removes every container, network and volume it created, pass or fail.
- [x] A real green run is required to close the task (a skip is not a proof); record the run's output and
  duration in the report. If docker is still unreachable, report BLOCKED with the test committed.
- Recorded finding (no change): every compose stack mounts the collector's `/tmp` as tmpfs, so the shipped
  queue directory is wiped on stop; durability holds only where a volume is mounted (`base.yaml:443-445`).

### Task 4: detector adoption — core (lane X-core)

Worktree `core-res` / branch `res-detector` / base `21cd644`. `AGAINST="origin/master"`. Roots `core`, `scripts`,
`setup`. New files in `tests/unit/observability/`. Env: shared api venv, `POSTGRES_DB=copilot_mro_test`. R1 §core.

- [x] Pre-adoption fix: `core/exceptions/__init__.py:1` star re-export → explicit re-export (T8), so the refusal
  policy resolves. Prove the old re-exported names are unchanged (every name previously exported still imports).
- [x] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; `refusal_types` = the seven R1 §core item 3 names.
  Expected register ≈ 4 entries (`request_identity.py:71/99/121` — SANCTIONED, T9; `http_errors.py:203` —
  OVER-REPORT). Re-measure; the register equals what the scan finds.
- [x] Floors (≥ 3 calls rule) from R1 §core item 6, re-counted at the worktree HEAD.
- [x] RETIRE: none. KEEP the log guard (misses the return hand-off, T11b), the span guard (misses `_describe()`),
  and the column/router/refusal/comment/response-body guards (different properties). Record the two detector
  gaps in the report for the plan's Future Improvements.

### Task 5: detector adoption — api (lane X-api)

Worktree `api-res` / branch `res-detector` / base `a8a3fb2`. `AGAINST="origin/langgraph-merge"`. Root
`flynapse_api`. New files in `tests/unit/telemetry/`. Env: shared api venv; run SERIALLY (`-n 0` — a
`pytest_sessionfinish` hook sets the exit status). R1 §api.

- [x] Pre-adoption fix (REAL log leak): `flynapse_api/middleware/rate_limit.py:147-150` `_degrade` logs the Redis
  exception's repr → constant message + `failure_fields(cause)`; planted-sentinel test proves no exception text in
  the record (red before).
- [x] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; `column_recorders` = the six R1 §api item 3 names (adds
  zero findings, arms the column rules).
- [x] Register: the eight raised-message sites → `LATENT`; `executor.py:991,1009` → `OVER-REPORT`;
  `executor.py:1019` and `one_shot.py:236` (`reason` token) → triage each with evidence (`OVER-REPORT` if the
  value is a closed vocabulary, else `OPEN LEAK`) — *post-review: executor's reason leak FIXED (fix round 1)*; `startup/weaviate_partitions.py:91` → `SANCTIONED` (owner
  carve-out `_REMEDIATION_ATTRIBUTES`).
- [x] Floors (≥ 3 calls rule) from R1 §api item 6, re-counted.
- [x] RETIRE: `tests/unit/telemetry/test_gateway_logs_carry_no_exception_text.py` (59/59) and
  `tests/unit/telemetry/test_api_spans_withhold_exception_text.py` (16/16) — each after its replay. KEEP the
  response-body sweep (60/61, aliased response class T11a), the run-error-column guard (rules 2–3), and
  `tests/_leak_taint.py` while any kept guard imports it.

### Task 6: detector adoption — copilot-mro (lane X-mro)

Worktree `copilot-mro-res-det` / branch `res-detector` / base = copilot-mro `langgraph-merge` AFTER lane M
merges. `AGAINST="origin/langgraph-merge"`. Roots `copilot_mro`, `scripts`, `deployment`, `lambda_functions`,
`demo` and the root `__init__.py`. New files in `tests/unit/observability/`. Env: shared api venv,
`POSTGRES_DB=copilot_mro_test`. Scan ≈ 56 s / 608 MB (T10) — one scan per process, and say how the lane's
wall-clock changed. R1 §copilot-mro.

- [x] Pre-adoption fix (REAL log leaks): the seven `_logger().opt(exception=True)` sites in
  `improvement/prompt_hook.py` (~:210) and `improvement/rules_renderer.py` (~:227, :265, :302 and siblings) →
  constant message + `failure_fields(exc)`; planted-sentinel test (red before).
- [x] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS` plus the repo reader `block_save_failure_fields` from
  `copilot_mro.app.api.chat_management_helper`, sinks `{log}` (T4 applies to the self-test).
- [x] Register: the broad-exception body echoes (`data_discovery.py` `_detail(exc)` funnels, `document_hub.py`
  funnels, `chat_files.py:123,238,381`, `chat_management.py:981,1058,1154,1501`) → `OPEN LEAK body` (their fix is
  a refusal-type conversion like core's B-F2 — it changes dashboard-visible messages, so it is its own owner
  decision); the R1 §copilot-mro item 4 SANCTIONED/OVER-REPORT rows as classified there, each re-verified;
  `ingest_operator.py:108` → triage with evidence.
- [x] Floors (≥ 3 calls rule), re-counted.
- [x] RETIRE: `tests/unit/observability/test_mro_spans_withhold_exception_text.py` (8/8 + 6/6) and
  `tests/unit/api_surface/test_no_traceback_response_bodies.py` (5/5) — each after its replay. KEEP the log guard
  `test_no_exception_text_in_logs.py` (138/140 — T11c) with its debt register and ratchet, and the tool-results
  guard (not a detector sink).

### Task 7: detector adoption — telegram-bot, with PP-TG-14 re-triage (lane X-tg)

Worktree `telegram-bot-res` / branch `res-detector` / base `47a08b7`. `AGAINST="origin/main"`. Roots
`telegram_bot`, `flynapse_client`. New files in `tests/unit/telemetry/`. Env: the repo's OWN
`/home/aditya/Code/telegram-bot/.venv` (the shared venv lacks `telegram`), NO xdist (run without `-n`). R1
§telegram-bot and §PP-TG-14.

- [x] Pre-adoption fix — PP-TG-14 (owner-deferred to this re-triage; measured REAL: third-party `exc_info` and
  `%s`-exception records print full messages to stderr): rebase `FailureFormatter`
  (`telegram_bot/failure.py:85-109`) on `flynapse_otel.logging.TypesAndFramesFormatter`, keeping the bot's
  `[Type …]` suffix and `stack` extra. Test with a chained sentinel exception for all three record kinds in R1's
  table (red before for the two third-party kinds); re-run `test_logs_withhold_exception_text.py`.
- [x] Policy: readers `failure_fields@telegram_bot.failure` and `headline_of@flynapse_client.errors`;
  `seed_attributes={"error"}`. Expected register ≈ 5 keys; each re-verified.
- [x] Floors (≥ 3 calls rule) with the counter widened to the detector's `DEFAULT_LOGGER_NAMES` (T7 — the bot
  logs through `LOGGER`).
- [x] RETIRE: `tests/unit/telemetry/test_logs_carry_no_exception_text.py` (72/72 with the seed) after its replay.
  KEEP `test_span_openers_pass_withholding_literals.py` (31/33, T11d), `test_raises_in_handlers_are_unchained.py`,
  and the behavioural withholding tests.

### Task 8: detector adoption — shift-optimizer (lane X-shift)

Worktree `shift-optimizer-res` / branch `res-detector` / base `f5f732c`. `AGAINST="main/main"` (the remote is
NAMED `main`). Roots `shift_optimizer`, `scripts`. New files in `tests/unit/telemetry/`. Env: shared api venv,
`POSTGRES_DB=copilot_mro_test`. R1 §shift-optimizer.

- [x] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; no column recorders (the column-writer guard already
  pins that door). Register ≈ 8 entries as R1 classifies them, each re-verified.
- [x] Floors: shift has only 3 calls in 2 modules, so the ≥ 3 rule selects none; carry both modules EXACT instead
  (`app/db/postgres.py` 2, `services/run_executor.py` 1), as utils does for small counts. *Post-review: `run_executor`
  is floored at 2 — the brief's count missed the `RunSignals.log` property (`:346`, `:367`); reviewer-confirmed.*
- [x] RETIRE: `tests/unit/telemetry/test_no_exception_text_on_spans.py` (48/48). SPLIT
  `tests/unit/telemetry/test_no_exception_text_in_logs.py`: its exception-text rules (59/61 — the two misses are
  format-string rules) retire; the format-string rules move to a new `test_log_messages_are_not_format_strings.py`
  (as utils keeps its own). KEEP `test_kept_error_raise_sites.py` and `test_run_error_column_writers.py`.

---

## Review & merge protocol

1. Per task: fresh Opus implementer → fresh Opus adversarial task reviewer (brief + report + review package +
   the global constraints), required to re-run the named mutation proofs and red-befores. Fix rounds per the SDD
   loop (P0/P1 only); P2/P3 → Future Improvements.
2. Controller merges each lane locally with `--no-ff` after its last task closes, then re-runs the lane's
   touched suites on the mainline. Detector lanes: TRUE merge only (the ratchet anchors on the adoption commit).
3. Final whole-batch review (Opus) over all merged ranges, pointed at the ledger's deferred minors.
4. Owner pushes.

## Future Improvements

- Recording-door enforcement of `TENANT_SCOPED_INSTRUMENTS` (R-G17-DOOR): add a public `name` to flynapse-otel's
  `CounterHandle`/`HistogramHandle` (`flynapse_otel/registry.py:88-116`), then have `_safe_add` strip `tenant.id`
  from any unlisted instrument.
- POC box: `iac/poc_ec2_setup.sh:80-84` sparse-checks out no `deployment/otel`, yet `poc/docker-compose.yml:48`
  bind-mounts `../otel` — the POC collector's config directory looks absent (R2 §B3; unverified live).
- Compose stacks mount the collector's `/tmp` as tmpfs; if a durability overlay is ever layered onto a compose
  stack it needs a real volume, and the tmpfs counts against the 512 MiB budget (R2 §B2, §C1).

### From the final whole-batch review (L1/L2/L3, 2026-09-25) — ready text from `final-review-L3-completeness.md` Q4

#### flynapse-otel (detector)
- **FI-OTEL-1 — Follow a caught exception's text RETURNED by a helper (T11b), to logs, spans, stdout and bodies.**
  Missing: `core`'s log guard shape (a handler returns `{'error': str(exc)}`, the caller logs it) and span shape
  (`_describe()` returns `f"failed: {exc}"` into `set_attribute`) are not flagged; the same blindness let
  `copilot_mro` `document_hub/reindex.py:290-299` (D1) and `api/flightops_brief.py:246-247` through. Deferred: a
  detector change in a sibling repo, out of this batch. Complete fix: taint a function's return when it returns
  text derived from a caught exception, and flag the callers' sinks; then retire core's two kept guards (after a
  replay) and shrink mro's kept log guard to its authored-refusal rule.
- **FI-OTEL-2 — A `detail=` keyword on ANY call as a sink; more generally a stream-callback argument, a yielded
  value and a returned record's field.** Missing: the detector reads `detail` only on `HTTPException`/response
  classes/raises/route returns. Deferred: sibling-repo change. Complete fix: add the receiver-agnostic `detail`
  sink (and the other three), replay mro `test_detail_keywords_carry_no_caught_text.py`'s planted shapes, retire it.
- **FI-OTEL-3 — `log.catch` on ANY receiver**, as `log.logger-exception` already is (`_module.py:1509/1564` gate on
  `is_logger`), plus an imported loguru `Logger` class alias. Deferred: sibling-repo change. Complete fix: match
  `.catch` / `getattr(_, "catch")` receiver-agnostically with corpus rows (parameter receiver as context manager,
  decorator, value); retire shift's `catch_references`.
- **FI-OTEL-4 — Narrow the span-name-string carve-out** (`_module.py:1553-1554` skips every dict key) to keys of
  withholding-splat mappings; retire shift's `span_names_as_strings`.
- **FI-OTEL-5 — Door-as-value (T11f):** `print` or a std stream's `write` taken as a value, a logger door stored on
  `self` or returned by a function. Complete fix: extend `log.door-as-value` / `output.*` to any non-callee
  reference; retire shift's `door_values`; re-check the retired core/api/telegram guards' shapes.
- **FI-OTEL-6 — Follow a re-export inside the scan** for bare `use_span` / `Status` names (mro M-1: a re-exported
  name escapes; no live case).
- **FI-OTEL-7 — An aliased response class in a helper (T11a)**; then api's kept response-body sweep can retire
  after a replay.
- **FI-OTEL-8 — Policy notions the register now fakes:** a sanctioned BODY sanitiser (core `caller_safe_*`), a
  typed attribute of a named class in a log sink (api's Weaviate seat), a sanctioned helper that must be imported
  from its home and bound once (telegram `configuration_error`, `headline_of`), and estate-home refusal types (T9:
  `utils.request_tenancy.TenancyDecisionError`, 3 core + 3 mro SANCTIONED entries). Each retires a repo-local pin
  or entry.
- **FI-OTEL-9 — Public vocabulary and discovery:** export `HTTP_EXCEPTIONS` and `DEFAULT_LOGGER_NAMES`; make
  `discover` read dot-directories under an explicit root (or expose the module list) so repo-local rules and the
  scan agree on the file set (shift X1).
- **FI-OTEL-10 — Shared register-test helpers** (Q3-d) and the **R-SPLAT runtime proof** moved from shift into
  flynapse-otel.

#### copilot-mro
- **FI-MRO-1 — OPEN LEAK body echoes (owner decision OD-5), 40 register entries.** `app/api/chat_files.py:123`
  (403/400 by substring), `:238` (404), `:381` (400); `app/api/chat_management.py:981, :1058, :1154, :1501`;
  `app/api/data_discovery.py:71-99` (`_detail`/`_raise`, 20 funnels); `app/api/document_hub.py:110-118`
  (`_raise_for_error`, 11 funnels). Plus the detector-blind `app/api/flightops_brief.py:246-247`. Deferred: the fix
  changes dashboard-visible messages. Complete fix: a refusal type the services raise for caller-facing sentences,
  everything else a fixed sentence plus a `failure_fields` log line; add the class to `refusal_types`, move the keys
  to `repaired`; `DocumentHubUploadPolicyError` becomes a policy refusal type in the same change.
- **FI-MRO-2 — Register reason precision.** `_station_brief`/`build_brief` reasons should name their behavioural pin
  `tests/unit/flightops/test_brief_endpoint_logic.py` (the register absorbs a `_log_detail` regression; review m4);
  the `request_identity._raise_http` reason's caller list should add `improvement.py`. Body OVER-REPORTs
  (`health_check` ×7, `tool_failures.seated`, `validator` ×2, `migrate_ifim.run`) could leave the register by
  inlining their describers into the sink expression.
- **FI-MRO-3 — C4 guard hardening.** Identify the five services by image repository (the `_versions_md` pins), resolve
  `extends:` before classifying, and flag an unbudgeted instance under another service name; drop the redundant
  aggregate assert and fix the "phoenix overlays" wording at `:44`. If OD-2 rules swap in, add `memswap_limit` to
  the budget keys; otherwise narrow the docstring to "the ruled keys".
- **FI-MRO-4 — memory_limiter measures Go heap, not the cgroup.** The ~102 MiB between the 410 MiB hard limit and
  512 MiB must hold runtime overhead plus the tmpfs `/tmp`; a persistent queue on tmpfs would OOM-kill before
  back-pressure. Complete fix: any stack layering a durability overlay mounts a volume (extends the existing tmpfs FI).
- **FI-MRO-5 — Compose smoke start deadline.** Phoenix boots in 94–135 s on the dev box; `_otel_smoke.py:54` allows
  120 s, so the gated smoke can flake independent of C4. Raise to ~180 s or wait per service.
- **FI-MRO-6 — G.17 driver completeness per recorder (Task 1 F2).** Wrap every public `record_*` / `*_sink` on
  `RuntimeTelemetry` with a call-tracking proxy; each must be driven or named in a spans-only exemption set with its
  reason, so a new recorder fails until driven.
- **FI-MRO-7 — G.17 guard runtime** 2.4–5.4 s under the repo conftest (the neighbour's direct-import style the brief
  mandated); a dynamic loader would bring it under 2 s.
- **FI-MRO-8 — otel test helpers** (Q3-a compose loader, Q3-b docker gate/helpers/payload builders; the I3 deadline
  becomes its own ≥ 60 s constant).
- **FI-MRO-9 — I3 proof polish:** re-read the sent counters after a settle before asserting exactly N; remove
  containers with `-v`; correct the replay-window comment (the 5 s batch timeout is margin, not a term).
- **FI-MRO-10 — Note on M-TOOL-ERRORS:** a failed tool's summary also reaches the SSE step stream
  (`progress_translator.py:222-229`), so the recorded tool-result debts (`workout_gate.py:483`,
  `build_workout.py:730`) have that sink too.
- **FI-MRO-11 — detail pin non-vacuity per root:** its `_modules()` silently reads nothing for a missing root (the
  register's `discover` raises); assert each root exists, or take the roots from the register module.

#### core
- **FI-CORE-1 — Kept log + span guards** retire only after FI-OTEL-1 lands (return hand-off gaps, measured).
- **FI-CORE-2 — Policy docstring slips** (`_core_exception_text_policy.py:16, :19`): TenantTeardownRefused has three
  fixed sentences (the class docstring `tenant_service.py:271` also says two); CommentPermissionError's message names
  the caller's own user id. **DONE in the final fix wave (core `bf14bad`).**

#### api
- **FI-API-1 — Non-vacuity plant for span writers:** add a caught-text `set_attribute`, a `record_exception` and a
  status description to the plant, and their rules to the required set (the retired span guard self-checked them).
- **FI-API-2 — Seat pin:** count `ast.arg` and `except … as` names as bindings (a parameter named
  `WeaviatePartitionError` survives; inherited from the retired guard).
- **FI-API-3 — Reason and prose:** cite `tests/integration/automations/test_one_shot_dispatch.py::test_a_stray_reason_attribute_is_not_written_to_the_column`
  as the one_shot gate's pin; optionally write the busy/no-verdicts constants directly at `executor.py:995/:1013` so
  the entry can leave the register; LATENT raise sites → constant raise messages; wrap the 128-char docstring line.

#### telegram-bot
- **FI-TG-1 — stderr user content (owner decision OD-1)** and a bounded reader for `RetryAfter.retry_after` (an int;
  operators lose the seconds after PP-TG-14).
- **FI-TG-2 — Pin and prose:** count a star import as a binding in `_bindings`; the pin comment `:124-126` should
  say the old guard refused six of the eight; one plan sentence that `report_failure` is held behaviourally only;
  `failure.py:101-102` and `telemetry.py:45-47` should say the base still withholds URL credentials and rendered
  tracebacks on a no-exception record; rename `…_left_on_stdout` (`test_stdlib_logs_to_otlp.py:131`).
- **FI-TG-3 — Report items:** `document_watch._read`'s two entries leave the register with the class name inline;
  the bot's `stack` extra quotes source lines (port `frame_headers`); `configuration_error` as a reader; the telemetry
  session fixture should re-attach its OTLP handler per test (21 order-dependent failures, identical at base).

#### shift-optimizer
- **FI-SHIFT-1 — Censuses and plant:** carry `SPAN_MARKING_MODULES` and `LOGURU_MODULES` as tripwires (or record the
  drop), and widen the non-vacuity plant to the span-writer rules (as FI-API-1).
- **FI-SHIFT-2 — dq1:** restructure the two exact-type body doors so the type check sits in the sink expression, or
  pin their shape; behavioural door tests hold them today.
- **FI-SHIFT-3 — Dot-directories:** the split-out rules' `_trees()` inherit `discover`'s dot-directory skip, which
  the retired guards' `rglob` did not have; walk the roots directly or assert the two sets agree (none exist today).

#### Added by the controller from L1/L2 and the fix wave
- **FI-OTEL-11 — Message renderers by NAME on any receiver** (the retired shift/mro guards matched `format_exc`-style
  renderers on any receiver; a third-party renderer or a wrapper passed into a non-HTTPException `detail=` is now
  unflagged — L1 M-3).
- **FI-OTEL-12 — Sinks INSIDE a registered helper, per sink not per kind.** telegram's `REGISTERED_HELPER_REACH` pin
  (`8f27e4f`) tracks sink KINDS, so a `raise SystemExit(token)` added inside `_run_turn` is still absorbed (the token
  already reaches a raise there); the retired guard refused it. Complete fix: the detector reports the sinks a
  helper-call's value reaches (or folds per-kind sink counts into the site fingerprint); then drop the pin.
  Interim small fix (re-review): a plain AST read pin (~15 lines) holding `_run_turn`'s `token` and
  `continue_chat_id` to one load each, as `stream_turn`'s arguments — catches `SystemExit(token)`, but not a
  `SystemExit` of a derived value, and flags harmless new reads of the token.
- **FI-TG-5 — The reach pin compares `Finding.detail` byte for byte** (it embeds a 40-character `unparse` of each
  argument), so a cosmetic flynapse-otel change to `detail`'s format fails the pin while the register stays clean.
  A structured field on `Finding` would be sturdier (fix-wave re-review).
- **FI-CORE-3 / FI-MRO-12 — `request_identity` SANCTIONED seats are absorbable** (widening the `except` at core
  `request_identity.py:98`/`:120` still reconciles clean; api and telegram pin their seats by shape) — add a seat
  shape pin like api's (L2 M-1).
- **FI-ALL-1 — Scan roots cover every production module** is asserted only in telegram-bot; the other four would
  silently miss a new top-level package (L2 M-6). Add the check, or derive roots from `git ls-files`.
- **FI-TG-4 — Floors lost the exact total** (106 failure lines → per-module floors; up to 13 lines deletable unseen;
  allowed by the floors ruling) (L1 M-5).
- **FI-MRO-13 — Stale floor comment:** `FAILURE_FIELDS_FLOORS` reindex entry says `# true 6`; after `2e88cdfb` the
  true count is 7 (floor 5 still valid).
- **FI-CORE-4 — Pre-existing count slip, same family as FI-CORE-2:** `tests/api/tenancy/test_tenant_teardown.py:1040`
  says "the two fixed sentences the success body carries" but iterates three names (fix-wave re-review).

## Owner decisions raised by this batch (RULED by the owner 2026-09-25)

- **OD-1 → HIDE** (render the two PTB records like the OTLP route) · **OD-2 → no `memswap_limit`** · **OD-3 → keep
  phoenix at 1.0 CPU** · **OD-4 → run the gated `otel-tests` dispatch once, after the owner pushes copilot-mro** (the
  I3 test is not on origin until then) · **OD-5 → FIX** (convert the body echoes) · **OD-6 → fsync OFF for now**.
  OD-1 and OD-5 are follow-up builds (research first, then a plan); the rest need no code.

The original questions, as put to the owner:

- **OD-1 — pilot words on the bot's stderr.** Two PTB records (the `Update` repr when a CallbackContext cannot be
  built; the raw getUpdates batch on a parse failure) print the pilot's message/caption/button payload at CRITICAL
  to stderr (the OTLP copy already withholds it). Keep, or render them like the OTLP route (operators lose the payload
  when debugging a parse failure).
- **OD-2 — swap.** `mem_limit` alone lets a container use the same amount again in swap before an OOM kill (WSL2).
  Keep, or set `memswap_limit` = `mem_limit` (hard ceiling; 15 lines across six files; joins the guard's keys).
- **OD-3 — phoenix CPU.** 1.0 CPU saturates under content-span bursts (all landed within ~10 s; boot 94–135 s).
  Keep, or raise to 2.0.
- **OD-4 — first hosted run of the I3 proof.** Dispatch `otel-tests` with `gated: true` once after the push (~3 min),
  or let the first real gated dispatch find any runner limit.
- **OD-5 — copilot-mro body echoes (40 OPEN LEAK entries + `flightops_brief._failure_message`).** Keep (raw
  ValueError/PermissionError/LookupError text reaches the dashboard), or convert to refusal types (users see generic
  text for non-refusal failures; the frontend's specific strings change).
- **OD-6 — collector queue fsync.** Off: survives a process crash, not host power loss. On: survives power loss, at
  an fsync per queue write.
- Carried from the owner walk: the three provisional confirmations (A-R1, C-R1, D-R2) and the Amplify AL2023/Node 22
  console check; the Portainer residual (pin `iac/poc_ec2_setup.sh` to 2.45.0, fix the stale demo comment) awaits a yes.

## Lessons

_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule next time)_

## Implementation notes

_(per task, filled as work lands)_

#### Notes: Task 1 — G.17 guard: DONE (res-mro `f5fa2eb6`, `ed502f8b`, fix `f3a49524`; review clean after 1 fix round)
- Literal `TENANT_SCOPED_INSTRUMENTS` (8 names) in `agent_shared/telemetry.py`; guard
  `tests/unit/agent_shared/test_tenant_scoped_instruments.py` derived from recorded points.
- **Deviation (reviewer-accepted):** turn / ledger / model-usage recorders are driven the way production calls
  them (unscoped facade, tenant as an argument); only tool and subagent go through `for_turn` — an all-`for_turn`
  driver let a `record_turn` tenant-drop mutant survive.
- **Fix round 1 (F1):** "carries tenant" was any-point; now any-point ⇒ listed AND every point of a listed counter
  carries it (reviewer's unpriced-path mutant now KILLED). `base.yaml:281` left as is (still true).

#### Notes: Task 2 — C4 compose budgets: DONE (res-mro `82b3cca9`; review clean) — boot check DONE after docker returned
- 15 base blocks / 6 files; guard `tests/integration/otel/test_compose_resource_budgets.py` (pure YAML).
- Also added the demo compose + both phoenix files to `test_phase1c_nonagent_scope_guard.py`'s approved paths
  (reviewer proved it necessary and exact).
- Owed: boot with limits in force, with a load step (phoenix `pids_limit: 128` is tightest); memory_limiter
  watches heap only (tmpfs invisible to it); WSL2 swap can add up to `mem_limit` again (no `memswap_limit`).

#### Notes: Task 3 — I3 queue-survives-crash proof: DONE (res-mro `1fe80187`, `3775a60e`; review clean)
- `tests/integration/otel/test_collector_queue_survives_restart.py` (marker `compose_stack`, gated on
  `OTEL_COMPOSE_SMOKE=1` + docker). Live green ×3 (implementer ×2, reviewer ×1): positive ~60 s, in-memory
  negative control ~107 s. Confirmed live at 0.160: retry line `Exporting failed. Will retry the request after
  interval.`; sent counters UNSUFFIXED (`otelcol_exporter_sent_spans{exporter=…}`); busybox chown to 10001.
- Mutants: file_storage removed from the tempo / loki exporter → exactly that signal lost; collector B on tmpfs
  instead of the volume → both lost (reviewer). Scope: process crash, not host power loss (queue fsync off).
- Was BLOCKED ~1 h on Docker Desktop's WSL integration (owner re-enabled it); Task 2's owed boot check ran then
  (all five healthy under load; PIDs ≤ 47; no OOM; see task-2 report).

**Lane M MERGED:** copilot-mro langgraph-merge `89b3e2d4` (--no-ff of `3775a60e`).

#### Notes: Task 4 — core detector: DONE + MERGED (core master `cb4f56e`; review clean)
- `33a6288` explicit re-export (T8) · `4a2b0bb` adoption: register 4 (3 SANCTIONED request_identity T9 · 1
  OVER-REPORT http_errors 422), policy = failure_fields + 7 refusal types, 17 floors. Nothing retired.

#### Notes: Task 5 — api detector: DONE + MERGED (api langgraph-merge `f616c3b`; review clean after 1 fix round)
- `e2d3b65` rate-limit log leak fixed · `89cf1be` adoption · `6c8a2f4` gateway log guard retired, its Weaviate
  carve-out SEAT rule split into a shape check (the register alone matched the seat call's own text) ·
  `25dae5a` span guard retired · **fix round 1 `a68f7b3`:** `executor.py` reason leak FIXED with the
  `one_shot.py:221` RunReasonError gate (R-DET-TRIAGE amended: a column/persisted leak with an in-repo precedent
  fix is fixed). Final register 7 LATENT · 2 OVER-REPORT · 1 SANCTIONED · 0 OPEN LEAK.
- Env: api runs need `POSTGRES_DB=copilot_mro_test` + `SIBLING_CHECKOUTS=copilot-mro=/home/aditya/Code/copilot-mro`.

#### Notes: Task 6 — copilot-mro detector: DONE + MERGED (copilot-mro langgraph-merge `e4534758`; review clean after 1 fix round)
- `60975403` the 7 rules-injection `_logger().opt(exception=True)` warnings → constant + handler-local
  `failure_fields` (red-before sentinel test) · `b664473a` phase-1c scope approval for the two modules ·
  `7916e237` adoption: register 66 keys / 77 findings (40 OPEN LEAK body · 15 SANCTIONED · 11 OVER-REPORT), policy
  = failure_fields + `block_save_failure_fields` reader, 82 floors · `f532447e` span guard retired (15/15; carve-out
  edges 6/6 caught by the register — stricter), its driven half split to `test_turn_span_withholds_exception_text.py` ·
  `b6563d6b` api_surface traceback pin retired · `2cbc913e` pointers.
- **Fix round 1 (I-1):** the retired pin's receiver-agnostic `detail=` rule split back out as
  `tests/unit/observability/test_detail_keywords_carry_no_caught_text.py` (`68d70dd0`); it found and `39d29467` fixed a
  live leak — `document_hub/reindex.py:648` put an S3 `head_object` failure's text into a plan item the reindex script
  prints.
- Base deviation (ruled): based on `82b3cca9` (Tasks 1+2) rather than waiting for lane M's merge.
- Report file write was refused by the harness for this implementer; the controller saved it from the hand-back.

#### Notes: Task 7 — telegram-bot detector + PP-TG-14: DONE + MERGED (telegram-bot main `c7292c9`; review clean)
- `d024402` `FailureFormatter` rebased on `TypesAndFramesFormatter` (third-party `exc_info` and `%s`-exception records
  no longer print their text; bot lines byte-identical) · `017dce8` adoption: 5 keys / 9 findings (4 SANCTIONED,
  1 OVER-REPORT), readers `failure_fields@telegram_bot.failure` + `headline_of@flynapse_client.errors`, seed `error`,
  11 floors · `7f6a600` log guard retired (72/72 leaks, 24/24 encoded rules; 8 `configuration_error` re-bindings
  → new binding pin) · `66c0eba` wording.

#### Notes: Task 8 — shift-optimizer detector: DONE + MERGED (shift-optimizer main `2332195`; review clean after 1 fix round)
- `943f853` adoption: 8 entries (6 SANCTIONED, 2 OVER-REPORT), floors exact (run_executor 2 — see Task 8) ·
  `a7687db` span guard retired (61/61; opener census + splat proof moved into the register test) · `a4b8f2d` log guard
  split (61/61 exception-text rules retired; 3 format-string rules → `test_log_messages_are_not_format_strings.py`;
  door-as-value, handler log-call equality, stdlib-logging ban kept in the register test) · `2c53671`.
- **Fix round 1 (I-1 + M-1):** `516dcd0` split-out rules — loguru `.catch` on ANY receiver, and span-call names as
  strings / dict keys (the detector recognises neither).

**All eight tasks merged locally 2026-09-25; nothing pushed.** copilot-mro `e4534758` · core `cb4f56e` · api `f616c3b`
· telegram-bot `c7292c9` · shift-optimizer `2332195`.

#### Notes: final whole-batch review + fix wave (2026-09-25)
- Three Opus lenses (L1 retirements, L2 correctness, L3 completeness), all FIX-FIRST, 0 Critical. L2 proved all five
  registers green at the mainlines and the ratchet safe across six simulated push/rebase/squash scenarios (owner:
  if a remote moved, MERGE it in — never `pull --rebase`). L1: every retired guard's leak corpus fully re-caught
  (api 88, mro 27, tg 72, shift 106); losses were implicit rules only.
- Fix wave (three per-tree Opus fixers, branch `res-final-fix` in `<repo>-fix` worktrees): copilot-mro `65a1eff8`
  (detail pin reads HTTPException under broad handlers — a widened relay handler was unseen), `2e88cdfb` (D1 reindex
  schema-probe leak), `190e9972`, `1f24b66e` (docstrings); telegram-bot `8f27e4f` (`REGISTERED_HELPER_REACH` pin — a
  new log line inside `_run_turn` was absorbed); core `bf14bad` (422 entry SANCTIONED + docstring slips); shift
  `3e13fcf` (true `_record_failure` reason).
- Scoped re-review (Opus): all 7 ADDRESSED — PASS; every fix mutant KILLED (the L1 widening plus two more relays; the
  reindex revert; the token log, `exit()` and a derived-value log in `_run_turn`); the declared `SystemExit(token)`
  residual survives as disclosed (FI-OTEL-12). Two Minor wording slips fixed by the controller before merge, text
  only: copilot-mro `971813c5` (the detail pin retires only once body findings also carry handler breadth — else
  deleting it reopens I-1) and core `36ca70d` ("two Refusal-raising validators").

**Fix wave MERGED 2026-09-25 (--no-ff, nothing pushed):** copilot-mro `ea56f459` · core `17699d9` · shift-optimizer
`f86c6c5` · telegram-bot `a1d1f2a` (api untouched: `f616c3b`). Post-merge at the mainlines: copilot-mro
observability/document_hub/agent_shared/improvement 3247 passed, 1 skipped · core observability + 422 + disclosure
sweep 682 passed · shift telemetry 228 passed · telegram-bot full unit 2457 passed. Fix worktrees removed, branches
deleted.

**Environmental reds (all lanes):** `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` variant/twin
tests fail on disk shape (primary checkout suffix `''`, missing or extra `<repo>-*` worktrees) — pre-existing,
proven identical at base; they change as this batch's worktrees come and go.
