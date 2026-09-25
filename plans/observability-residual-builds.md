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

- **R-DET-TRIAGE:** detector findings are registered with a TRUE dated reason of one of four kinds (SANCTIONED /
  OVER-REPORT / LATENT / OPEN LEAK); log/stdout leaks with the house fix are fixed pre-adoption; body/raise shapes
  whose fix changes an HTTP or error contract are registered OPEN LEAK and listed in Future Improvements (owner
  decision). Cost if wrong: copilot-mro's ~12 body-echo sites stay open until that decision.
- **R-DET-RETIRE:** an old guard retires only where the recon measured the detector flagging EVERY leak shape it
  pins, re-proved by replay in the lane (api logs + spans, copilot-mro spans + traceback bodies, telegram logs,
  shift spans + the exception-text half of its log guard); everything partial stays. Cost if wrong: a kept
  duplicate guard (harmless) or, for a retirement, a shape the replay did not cover.
- **R-DET-PPTG14:** PP-TG-14 re-triaged as a REAL stderr leak with a one-base drop-in fix (rebase `FailureFormatter`
  on `TypesAndFramesFormatter`) — fixed inside Task 7. Cost if wrong: the bot's stderr lines change shape for
  third-party records only.

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

- [ ] Add a named literal `TENANT_SCOPED_INSTRUMENTS` (frozenset of exactly the eight names `agent.turn.calls`,
  `agent.model.calls`, `agent.model.cost_usd`, `agent.model.unpriced_calls`, `agent.tool.calls`,
  `agent.tool.attempts`, `agent.subagent.calls`, `agent.ledger.write_failures`) to
  `copilot_mro/app/services/agent_shared/telemetry.py`, beside `_HISTOGRAM_WITHHELD_KEYS` (~:1416–1421), with a
  comment naming the ruling: an instrument gains `tenant.id` only by being added here.
- [ ] New guard `tests/unit/agent_shared/test_tenant_scoped_instruments.py`, derived from BEHAVIOUR, not source
  text: build `RuntimeTelemetry` on an SDK `MeterProvider` with an `InMemoryMetricReader` (as
  `test_genai_metric_labels._telemetry` does), take a `for_turn` view carrying a tenant, drive every metric
  recorder (R2 §A4(b) lists them, including the priced and unpriced model-usage paths). Assert: (1) every
  instrument object on the telemetry instance produced at least one point (driver completeness — a new
  instrument the driver misses fails); (2) the set of metric names whose points carry `tenant.id` EQUALS the
  literal; (3) no histogram is in the literal or carries `tenant.id`.
- [ ] Mutation proofs (each must turn the guard red; record mutation + failing test name): drop `tenant.id`
  from `for_turn`; add `tenant.id` to the subagent attributes of a non-listed path or a new counter; empty
  `_HISTOGRAM_WITHHELD_KEYS`; remove one name from the literal.
- [ ] Text-only updates of the stale "G.17 is OPEN" prose: `tests/integration/otel/test_browser_derived_metrics.py`
  (~:28, :83, :301), `deployment/otel/base.yaml` (~:281, :287), `deployment/otel/README.md` (~:249). That test
  runs in the pytest+pyyaml-only CI lane — do not add imports to it.
- [ ] Run: the new guard, `tests/unit/agent_shared/`, `tests/integration/otel/` (non-docker), `tests/unit/infra/`.
- Recorded fact (no change): in production only five of the eight counters carry a tenant today; the tool and
  subagent counters get one only through `for_turn`, because both runtimes bind those observers unscoped
  (`agent_pipeline.py:263-275, 691-699`). The ruled list keeps all eight (packet rows 20–22 "turn view").

### Task 2: C4 — declare the approved resource budgets in compose (copilot-mro, lane M)

**Ruling:** owner approved the C4 packet's budgets (2026-09-24): otel-collector 512 MiB · phoenix 2 GiB · loki
512 MiB · prometheus 512 MiB · tempo 256 MiB; `cpus: 1.0` and `pids_limit: 128` per service. Evidence: R2 §B.

- [ ] Add service-level `mem_limit`, `cpus`, `pids_limit` (R-C4-SYNTAX) to every BASE definition of the five
  services (15 blocks) in: `deployment/docker-compose.yml`, `deployment/observability-local/observe-docker-compose.yml`,
  `deployment/poc/docker-compose.yml`, `deployment/demo/docker-compose.yml`, `deployment/docker-compose.phoenix.yml`,
  `deployment/poc/docker-compose.phoenix.yml`. Overlay blocks (no `image:`), including the smoke overlay and the
  phoenix files' otel-collector partials, get none.
- [ ] New guard `tests/integration/otel/test_compose_resource_budgets.py`, pure YAML (runs in the CI otel lane),
  modelled on `test_grafana_service_health_and_env.py` (`_ComposeLoader` for `!override`/`!reset`, glob-found
  compose files, base blocks = those with `image:`): one `BUDGETS` literal citing the C4 ruling; every base block
  of the five services declares exactly it; no override block sets `mem_limit`/`cpus`/`pids_limit`/`deploy`; the
  scan finds at least 15 base blocks, per service (non-vacuity).
- [ ] Mutation proofs: change one file's value; drop one block's key; add a key to an overlay — each red.
- [ ] The commit message states the behaviour change: the collector's `memory_limiter` (`base.yaml:34-37`,
  80 %) now computes against the 512 MiB cgroup (~410 MiB hard / ~307 MiB soft) instead of host RAM.
- [ ] If docker is reachable: render every touched stack with `docker compose config` and boot the C4 recipe
  (packet) once with the limits in force — all five healthy. If not reachable: record that the boot is owed.

### Task 3: I3 — the file-backed queue survives a collector crash (copilot-mro, lane M)

**Scope:** R-I3-SCOPE. Design and pitfalls: R2 §C3 (follow it; deviations need a reason in the report).

- [ ] New `tests/integration/otel/test_collector_queue_survives_restart.py`, marker `compose_stack`, skipped
  unless `OTEL_COMPOSE_SMOKE=1` and `docker info` succeeds; stdlib + docker CLI only; raw `docker run` on a
  private network with pinned images from `_versions_md.image_pin` and ephemeral loopback ports, modelled on
  `test_alertmanager_delivery_failures.py:250-340`; reuse the smoke helpers rather than copying them.
- [ ] Positive run: collector with `base.yaml` + `backend-oss.yaml` + `durability-production-oss.yaml` and a
  uid-10001-owned named volume at `OTEL_FILE_STORAGE_DIR`, backends absent; send N spans + N logs with unique ids;
  wait for the exporters' retry line (proves they reached the queue); `kill -9` and remove; start a new
  collector on the same volume; start Tempo + Loki under their aliases; within a ≥ 60 s deadline all N ids
  arrive; the new collector's `otelcol_exporter_sent_spans_total` / `…_sent_log_records_total` equal N exactly.
- [ ] Negative control (mandatory): same flow without the durability overlay loses every pre-crash id (canary
  proves the backend path works; wait past `max_interval`).
- [ ] Teardown removes every container, network and volume it created, pass or fail.
- [ ] A real green run is required to close the task (a skip is not a proof); record the run's output and
  duration in the report. If docker is still unreachable, report BLOCKED with the test committed.
- Recorded finding (no change): every compose stack mounts the collector's `/tmp` as tmpfs, so the shipped
  queue directory is wiped on stop; durability holds only where a volume is mounted (`base.yaml:443-445`).

### Task 4: detector adoption — core (lane X-core)

Worktree `core-res` / branch `res-detector` / base `21cd644`. `AGAINST="origin/master"`. Roots `core`, `scripts`,
`setup`. New files in `tests/unit/observability/`. Env: shared api venv, `POSTGRES_DB=copilot_mro_test`. R1 §core.

- [ ] Pre-adoption fix: `core/exceptions/__init__.py:1` star re-export → explicit re-export (T8), so the refusal
  policy resolves. Prove the old re-exported names are unchanged (every name previously exported still imports).
- [ ] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; `refusal_types` = the seven R1 §core item 3 names.
  Expected register ≈ 4 entries (`request_identity.py:71/99/121` — SANCTIONED, T9; `http_errors.py:203` —
  OVER-REPORT). Re-measure; the register equals what the scan finds.
- [ ] Floors (≥ 3 calls rule) from R1 §core item 6, re-counted at the worktree HEAD.
- [ ] RETIRE: none. KEEP the log guard (misses the return hand-off, T11b), the span guard (misses `_describe()`),
  and the column/router/refusal/comment/response-body guards (different properties). Record the two detector
  gaps in the report for the plan's Future Improvements.

### Task 5: detector adoption — api (lane X-api)

Worktree `api-res` / branch `res-detector` / base `a8a3fb2`. `AGAINST="origin/langgraph-merge"`. Root
`flynapse_api`. New files in `tests/unit/telemetry/`. Env: shared api venv; run SERIALLY (`-n 0` — a
`pytest_sessionfinish` hook sets the exit status). R1 §api.

- [ ] Pre-adoption fix (REAL log leak): `flynapse_api/middleware/rate_limit.py:147-150` `_degrade` logs the Redis
  exception's repr → constant message + `failure_fields(cause)`; planted-sentinel test proves no exception text in
  the record (red before).
- [ ] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; `column_recorders` = the six R1 §api item 3 names (adds
  zero findings, arms the column rules).
- [ ] Register: the eight raised-message sites → `LATENT`; `executor.py:991,1009` → `OVER-REPORT`;
  `executor.py:1019` and `one_shot.py:236` (`reason` token) → triage each with evidence (`OVER-REPORT` if the
  value is a closed vocabulary, else `OPEN LEAK`); `startup/weaviate_partitions.py:91` → `SANCTIONED` (owner
  carve-out `_REMEDIATION_ATTRIBUTES`).
- [ ] Floors (≥ 3 calls rule) from R1 §api item 6, re-counted.
- [ ] RETIRE: `tests/unit/telemetry/test_gateway_logs_carry_no_exception_text.py` (59/59) and
  `tests/unit/telemetry/test_api_spans_withhold_exception_text.py` (16/16) — each after its replay. KEEP the
  response-body sweep (60/61, aliased response class T11a), the run-error-column guard (rules 2–3), and
  `tests/_leak_taint.py` while any kept guard imports it.

### Task 6: detector adoption — copilot-mro (lane X-mro)

Worktree `copilot-mro-res-det` / branch `res-detector` / base = copilot-mro `langgraph-merge` AFTER lane M
merges. `AGAINST="origin/langgraph-merge"`. Roots `copilot_mro`, `scripts`, `deployment`, `lambda_functions`,
`demo` and the root `__init__.py`. New files in `tests/unit/observability/`. Env: shared api venv,
`POSTGRES_DB=copilot_mro_test`. Scan ≈ 56 s / 608 MB (T10) — one scan per process, and say how the lane's
wall-clock changed. R1 §copilot-mro.

- [ ] Pre-adoption fix (REAL log leaks): the seven `_logger().opt(exception=True)` sites in
  `improvement/prompt_hook.py` (~:210) and `improvement/rules_renderer.py` (~:227, :265, :302 and siblings) →
  constant message + `failure_fields(exc)`; planted-sentinel test (red before).
- [ ] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS` plus the repo reader `block_save_failure_fields` from
  `copilot_mro.app.api.chat_management_helper`, sinks `{log}` (T4 applies to the self-test).
- [ ] Register: the broad-exception body echoes (`data_discovery.py` `_detail(exc)` funnels, `document_hub.py`
  funnels, `chat_files.py:123,238,381`, `chat_management.py:981,1058,1154,1501`) → `OPEN LEAK body` (their fix is
  a refusal-type conversion like core's B-F2 — it changes dashboard-visible messages, so it is its own owner
  decision); the R1 §copilot-mro item 4 SANCTIONED/OVER-REPORT rows as classified there, each re-verified;
  `ingest_operator.py:108` → triage with evidence.
- [ ] Floors (≥ 3 calls rule), re-counted.
- [ ] RETIRE: `tests/unit/observability/test_mro_spans_withhold_exception_text.py` (8/8 + 6/6) and
  `tests/unit/api_surface/test_no_traceback_response_bodies.py` (5/5) — each after its replay. KEEP the log guard
  `test_no_exception_text_in_logs.py` (138/140 — T11c) with its debt register and ratchet, and the tool-results
  guard (not a detector sink).

### Task 7: detector adoption — telegram-bot, with PP-TG-14 re-triage (lane X-tg)

Worktree `telegram-bot-res` / branch `res-detector` / base `47a08b7`. `AGAINST="origin/main"`. Roots
`telegram_bot`, `flynapse_client`. New files in `tests/unit/telemetry/`. Env: the repo's OWN
`/home/aditya/Code/telegram-bot/.venv` (the shared venv lacks `telegram`), NO xdist (run without `-n`). R1
§telegram-bot and §PP-TG-14.

- [ ] Pre-adoption fix — PP-TG-14 (owner-deferred to this re-triage; measured REAL: third-party `exc_info` and
  `%s`-exception records print full messages to stderr): rebase `FailureFormatter`
  (`telegram_bot/failure.py:85-109`) on `flynapse_otel.logging.TypesAndFramesFormatter`, keeping the bot's
  `[Type …]` suffix and `stack` extra. Test with a chained sentinel exception for all three record kinds in R1's
  table (red before for the two third-party kinds); re-run `test_logs_withhold_exception_text.py`.
- [ ] Policy: readers `failure_fields@telegram_bot.failure` and `headline_of@flynapse_client.errors`;
  `seed_attributes={"error"}`. Expected register ≈ 5 keys; each re-verified.
- [ ] Floors (≥ 3 calls rule) with the counter widened to the detector's `DEFAULT_LOGGER_NAMES` (T7 — the bot
  logs through `LOGGER`).
- [ ] RETIRE: `tests/unit/telemetry/test_logs_carry_no_exception_text.py` (72/72 with the seed) after its replay.
  KEEP `test_span_openers_pass_withholding_literals.py` (31/33, T11d), `test_raises_in_handlers_are_unchained.py`,
  and the behavioural withholding tests.

### Task 8: detector adoption — shift-optimizer (lane X-shift)

Worktree `shift-optimizer-res` / branch `res-detector` / base `f5f732c`. `AGAINST="main/main"` (the remote is
NAMED `main`). Roots `shift_optimizer`, `scripts`. New files in `tests/unit/telemetry/`. Env: shared api venv,
`POSTGRES_DB=copilot_mro_test`. R1 §shift-optimizer.

- [ ] Policy: `failure_fields` = `ESTATE_FAILURE_FIELDS`; no column recorders (the column-writer guard already
  pins that door). Register ≈ 8 entries as R1 classifies them, each re-verified.
- [ ] Floors: shift has only 3 calls in 2 modules, so the ≥ 3 rule selects none; carry both modules EXACT instead
  (`app/db/postgres.py` 2, `services/run_executor.py` 1), as utils does for small counts.
- [ ] RETIRE: `tests/unit/telemetry/test_no_exception_text_on_spans.py` (48/48). SPLIT
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

## Lessons

_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule next time)_

## Implementation notes

_(per task, filled as work lands)_
