# Post-merge owed-work batch — 11 items, all owner-approved 2026-08-14

Sequel to `three-stream-merge.md` (§4's "owed engineering" list). The owner selected ALL of
items 11–21 for implementation and ruled the deferred set (22–24) stays deferred. This file is
the working plan; check items off as they land. **The production AD rollout is running in
parallel — nothing here may touch the `copilot_mro` database or S3; all validation runs against
`copilot_mro_test` and the local Weaviate's scratch partitions.**

## Session directive (owner, 2026-08-14)

SDD-driven: each delegated item gets a written spec (in the subagent brief), implementer works in
its own sibling worktree, ledger notes land back in this file on completion. Concurrency cap for
this session: **3 subagents in parallel** (owner override of the default 2), model opus or fable
by task complexity. Transfer path for delegated work: subagents commit ONLY their new files on
their worktree branch; the orchestrator cherry-picks those commits into `agentsdk` in the main
checkout, then removes the worktree.

## Priority order (time-critical first)

- [x] **19 — Verdict-delta tool** (`copilot-mro/scripts/ad/verdict_delta.py`, NEW).
      URGENT: the owner must snapshot production BEFORE running rollout step 4 (evaluate) —
      Phase A (the running scrape) does not write verdicts, so the pre-evaluate state is
      current until then. Design: `--snapshot FILE` dumps every `ad_fleet_applicability`
      row's (tenant, operator, agency, ad_number, applicability_state, applicability_basis,
      review_disposition) as JSON; `--compare FILE` prints, per (tenant, operator): a
      state-transition matrix (old→new counts), the newly-applicable AD list, ADs that left
      `applicable`, and rulings cleared by fingerprint invalidation. Read-only; `--database`
      required, never inferred (house rule for AD CLIs).
- [x] **16 — `Corpus.retract` cross-partition test** (copilot-mro, live-Weaviate lane).
      URGENT: before rollout step 8. The property: retracting one partition's copy of a
      shared-UUID AD document deletes ONLY that partition's objects; every other partition's
      copy (same UUIDs — the corpus-seed copies preserve UUIDs) survives. Build: scratch
      tenant partitions on the local cluster (mirror `operator_corpus_seed` naming), seed two
      partitions with same-UUID objects, run the real `Corpus.retract` from
      `materialize_ad_corpus.py` against one, assert the other is intact and the target empty,
      clean up partitions in `finally`.
- [x] **13a — Effective-state consumption** (copilot-mro). The dispatcher
      (`ad_notification_dispatcher.py`) and the catalog/database-skill listings still read
      `applicability_state` raw; a `ruled_not_applicable` AD keeps surfacing as an open
      question. Fix: one shared SQL expression / helper for effective state
      (`COALESCE`-style: disposition overrides machine state), applied at the dispatcher's
      per-operator gate and the catalog listing surfaces; prompt-facing disclosure updated so
      the model knows a ruling exists. Tests: dispatcher unit (ruled-out AD not notified),
      catalog listing (effective state column).
- [x] **18 — Junk-only roster gate** (copilot-mro). `roster_preflight` already detects a
      roster whose every row is `unrecognised_family`/`uncanonicalisable`; the sweep still
      verdicts the whole catalog confidently against it. Fix: in `evaluate_ad_applicability.py`
      AND `ad_review_service.recompute_operator`, a junk-ONLY roster refuses like the empty
      roster does (distinct refusal reason in the report/preflight payload). Tests: unit for
      the classification, service refusal, script refusal.
- [x] **17 — `skip_unless_corpus_estate` probe** (copilot-mro,
      `tests/fixtures/tenancy/rls_connections.py`). It currently probes for a synthetic tenant
      row; a database holding a full corpus still skips every corpus instrument. Fix: measure
      the thing itself (e.g. a chunks/manual-corpus row-count threshold under any tenant), keep
      the skip message naming what was measured. Then run the formerly-dormant pins on
      `copilot_mro_test` and triage what wakes up.
- [x] **21 — t1 `manual_type` estate gap** (copilot-mro). `test_t2_document_filters_hold_no_t1_values`
      fails at its own `pytest.fail` in `sample_manual_type`: `t1-primary-estate-0000` holds no
      `manual_type` that no other tenant shares. Fix: seed one synthetic manual-type row under
      t1 (fixture-owned, cleaned up, or a durable seed in the t1 estate) so the isolation probe
      has a discriminating value. The last copilot-mro api-lane red.
- [x] **20 — `scripts/ad/_common.py`** (copilot-mro, NEW). Hoist the duplicated `_add_repo_paths`
      (4 copies; its hardcoded-checkout bug was fixed three times separately) and the two-gate
      live-database guard (2 copies) into one module; repoint the AD CLIs. Behavior-neutral;
      prove with the existing AD unit lanes.
- [x] **13b — Phase C enqueue from the review page** (copilot-mro + dashboard). The page's
      recompute runs Phase B inline; Phase C (materialisation) must be ENQUEUED for the
      automations worker (its own process — the process-global attribution mutation is harmless
      there; corrected-D7 reading). Build: an automations job type wrapping
      `materialize_ad_corpus` for one (tenant, operator) WITHOUT `--retract`; the review page
      gains "Materialise" (enqueue + status); endpoint + FE + tests. Depends on the automations
      executor surface — coordinate with item 12's owner (api repo).
- [ ] **14 — Phase D notifications + retire the fetch-time gated path** (copilot-mro, LAST —
      biggest, and deliberately after the production rollout proves the pipeline). Two halves:
      (a) the evaluate sweep (CLI + in-app recompute) emits notifications for verdict
      transitions into the existing dispatcher (which then honors 13a's effective state);
      (b) retire `fetch_new_ads`' fetch-time verdict path — it strands
      `seed_compliance_for_ads`' trigger and `--notify`'s batch producer (re-home both onto the
      new pipeline) and deletes ~10 regression pins (rewrite against the new path). Removes the
      stub-stamping footgun (a legacy `--operator --backfill` after materialisation stamps
      measured `full` rows back to `stub`).

## Delegated to the api-repo subagent (separate working tree)

- [x] **11 — `_scan_every_tenant` coverage** (api). Pin: the loop visits EVERY registered
      tenant (a tenant added to the registry starts being scanned; a `tenant_id` predicate
      sneaking into the scan goes red). The two core xfails document exactly what was given up.
- [x] **12 — Automations budget gate charges combined cost** (api). Replace the SDK-only
      figure at `flynapse_api/automations/executor.py:310` with the `llm_usage` ledger's
      combined cost. Two recorded traps: a naive swap charges $0 on unpriced turns (fall back
      to the SDK figure when the ledger row is absent/incomplete — never charge less than the
      SDK figure); and the ledger row is written by copilot-mro's turn path, so the gate must
      read, not compute. Tests for both trap directions.

## Constraints

- Production `copilot_mro` + S3 + the production Weaviate partitions are OFF-LIMITS (rollout
  running). `copilot_mro_test` + scratch Weaviate partitions only.
- House commit rule: new files + existing-test-file edits committable; production-file edits
  stay uncommitted.
- One implementer per working tree: main session owns copilot-mro + dashboard; the subagent
  owns api. Item 13b's api-side (if any) waits for the subagent to finish.

## Implementation notes

- **19 (DONE, main-tree commit `cf23fddf`)** — `scripts/ad/verdict_delta.py` + 35 unit tests;
  live-proven on copilot_mro_test (snapshot 3,114 rows → planted transition reported exactly →
  restore → NO DIFFERENCES; refusal gates verified). Beyond spec: per-pair basis-transition
  counts, `--max-list` (default = everything), server-side `readonly=True` session, a test that
  scans the script for SQL write verbs, byte-stable snapshots (Python re-sort after ORDER BY).
  Rulings-cleared path is unit-proven only (estate holds zero dispositions).
  **Owner's pre-step-4 snapshot command** (from `/home/aditya/Code/copilot-mro`):
  `/home/aditya/Code/api/.venv/bin/python scripts/ad/verdict_delta.py --database copilot_mro
  --i-understand-this-is-live --snapshot /home/aditya/Code/copilot-mro/verdicts-before-phaseB.json`
  — after the sweep, same line with `--compare` and the same file.
- **16 (DONE, main-tree commit `b73e5f3f`)** — `tests/integration/ad/test_ad_corpus_retract_isolation.py`
  exercises the REAL `Corpus.retract` from `materialize_ad_corpus.py` (path-loaded, no package
  init) against a scratch MT collection with two production-named partitions holding same-UUID
  objects; retracted partition empty, sibling intact; mutation-proven (sabotaged assertion went
  red); scratch collection dropped + absence verified. Postgres half runs against a recording
  stub asserting the catalog DELETE's exact scope (deviation from "prefer no Postgres": the
  real code path still executes).
- **13a (DONE; production edits uncommitted, tests commit `8641aa94`)** — one fold, defined in
  `aircraft_normalize` (`REVIEW_DISPOSITION_EFFECTIVE_STATE`, `effective_applicability()`,
  `effective_applicability_sql(alias)`; registry asserts vocabulary sync both directions).
  Consumers repointed: dispatcher gate `_APPLICABLE_TO_FLEET_SQL`, batch selectors'
  `_APPLIES_TO_FLEET` (dispatch script), audit predicate + basis-display
  (`list_applicability_unknown`), review service `_effective_state` (now delegates), and the
  model-facing disclosure (`applicability_state` description, lifecycle-defaults body + worked
  example render the expression from the helper). Live-proven: the dispatcher's own SQL under a
  real binding flips with rulings both directions; audit question closes and reopens. Lanes:
  unit/ad 411/0, db/ad 35/0, registries 164/0.
- **Found-and-fixed while landing 16 (commit `148ec265`)** — the ad-applicability merge left
  test-infra's attribution gate referencing the deleted Model A constant
  (`AD_COUNT_PER_PARTITION`), failing ALL of `tests/integration` at collection. Rebuilt the
  gate's expectations Model-B-style: `AD_POPULATION` sentinel resolved by measuring the
  partition at comparison time; broadcast-width bound restated per partition. 61 tests collect
  again.
- **11+12 (DONE, api repo — subagent)** — 11: `tests/unit/automations/test_scan_every_tenant.py`
  (4 tests, commit `148e720`), registry-equality + newcomer-scanned-next-tick + failure
  isolation, mutation-proven. 12: executor charges `max(ledger combined, SDK figure)` via
  `_ledger_charge` (uncommitted production edit + commit `848fe30` tests); never charges $0 on
  unpriced turns, reads-not-computes pinned. api suite 750/0. Flagged for a later ruling:
  timeout/pipeline-exception paths still record no `cost_usd`.

- **18 (DONE; tests commit `5932c703`, production edits uncommitted)** — `PreflightReport.junk_only`
  (all rows uncanonicalisable/unrecognised-family; family-grade rows keep a roster evaluable),
  `evaluate_pair` + `recompute_operator` refuse under distinct `refusal_reason`
  (`empty_roster` / `junk_only_roster`), report renders both refusal classes separately.
  AD unit lane 420/0.

- **20 (DONE; `scripts/ad/_common.py` + guard-test updates commit `6743fda2`, CLI edits
  uncommitted)** — nine `add_repo_paths` copies (five still hardcoding the primary checkout's
  name) and three guard copies hoisted; the guard's per-script live-run sentence became the
  required `action` parameter. Proven: unit lanes 452/0, `--help` on all five CLIs, verbatim
  guard refusals, full `--dry-run` evaluate sweep on copilot_mro_test (3 pairs, 1,038 verdicts
  each, states unchanged, both refusal counters rendering).
- **17+21 (DONE, subagent; commits `2c68e243` + `088e2cbf` cherry-picked into `agentsdk`)** —
  probe now counts rows over the relations each instrument names (`CORPUS_ESTATE_FLOOR`
  1,000; absent relation ≠ 0; topology's chunks count tenant-scoped — an unscoped count reads
  the 305k attribution snapshot). 31 dormant pins woke: 29 pass, 2 were unrunnable pins fixed
  in place (captured parameterised SQL executed without its params). t1's discriminating
  `manual_type` is a fixture-owned probe row (`T1_ISOLATION_PROBE_MANUAL`, `__ALL__` grain,
  swept by the fixture's own cleanup), clearing the last copilot-mro api-lane red (26/26).
- **Follow-ons landed with the wake-up (commit `e05ac405` + estate seed)** — enabled `new_ad`
  in-app subscriptions seeded into copilot_mro_test (the fixture-time estate gap behind two
  errors), and the cross-airline "crossing" control now SKIPS with the premise named when no
  operator pair on the corpus can demonstrate the retired rule's harm (t1's operators both fly
  737 variants; the no-trespass half still runs). Lane: db/tenancy 387 passed + named skips,
  0 errors.

- **13b (CLOSED 2026-08-14 — built, adversarially reviewed, all findings fixed or ruled)** —
  contract: `automations` gains
  `kind varchar DEFAULT 'chat'` + `params jsonb`; materialise rows are
  `kind='ad_materialize'`, `params={"operator_id"}`, `enabled=False`, dept `mro`, budget 0;
  enqueue = one reused row per (tenant, operator) + `claim_run(TRIGGER_MANUAL)`; FE polls
  core's runs endpoint.
  - **copilot-mro half DONE** (uncommitted: `enqueue_materialize` in `ad_review_service.py`,
    `POST /ads/review/materialize` in `ad_review.py`; tests commit `82a5c6cd`, 424/0 lane).
    Enqueue seam live-proven on copilot_mro_test under a real tenancy binding: contract-exact
    row, one claimed manual run, second press returns the in-flight run, clean teardown.
  - **api/core half DONE (subagent)** — api commits `fa06840`+`9c5e6b0`, core `af19df6`;
    uncommitted production edits in table_definitions/schemas/automation_store/executor/loop.
    Runner (`flynapse_api/automations/ad_materialize.py`) path-loads the REAL materialise
    script and mirrors its live arc per pair (`run_pair_in_savepoint`, `verify=False`,
    `retract=False`); serialisation is a module `threading.Lock` held by the worker thread
    (an asyncio lock would release on the `wait_for` cancellation while the zombie thread
    ran on). Spec-gap fixed: `decide_manual` stood down every disabled automation, so
    `ONE_SHOT_KINDS` exempts `ad_materialize` from the disabled gate only. api suite 766/3,
    core automations 290 green, convergence proven live (copilot_mro_test genuinely lacked
    the columns), dispatch + gate mutation-proofed.
  - **dashboard half DONE (subagent, commit `f366de31`)** — `materializeAdCorpus` client,
    `useMaterializeAdCorpus` hook (run_id-matched watch, 5s poll while pending, 30-min bound,
    list refresh on completion), button + progress lane on the review page; unit 1374/0
    (+18), tsc + lint clean, no-poll and always-invalidate mutants killed. Two test-infra
    traps recorded in dashboard's `docs/plans/ad-review-frontend.md` Lessons (query-core
    fixes `isServer` at import time; `queryClient.clear()` leaks mutation gc timers).
  - Known accepted edges: the $5 reservation floor holds per run while it executes
    (dev-acceptable, noted); `attributed_to`'s settings-singleton race is closed by the
    runner's per-process lock, not by refactoring the script mid-rollout; the run row
    carries no `cost_usd` (asserted absent, not zero).
  - **Adversarial review returned: 1 blocker + 4 real gaps + 3 nits; verdict
    ship-with-fixes. Triage + fixes:**
    - F1 (blocker — shared row runs as its first creator; owner-gated poll blinds every
      other reviewer; departed owner bricks the operator): FIXED in copilot-mro — rows are
      per (tenant, operator, PRESSER), in-flight dedupe spans all owners, and the page polls
      a new pair-scoped `GET /ads/review/materialize/status` (never owner-gated, carries
      `error` + `reason`). Tests commit `66155881`; live smoke re-proven (three pressers,
      one run, status active).
    - F2 (REST can create/enable the kind → nightly due-scan fires) + F3 (hung thread holds
      the lock forever, leaks a pool thread per later run) + F4 (embedded scheduler mode
      runs the process-global attribution mutation inside the gateway): FIXED by the
      api/core fix agent (test commits api `3f5d810`, core `c54c652`; production edits
      uncommitted incl. an `announcements.py` copy entry the repo's own reason-drift guard
      forced). Create-route 422s non-chat kinds; `decide`'s kind gate sits ABOVE the
      `enabled` check (below it the guard is unreachable — pinned by a precedence test) and
      `one_shot_kind` is a silent reason (the missed-run copy would promise a retry that
      never comes); lock `acquire(timeout=120)` fails fast as `materialise_busy` (the
      restored unbounded-acquire mutant reproduced the exact hang); `requires_worker_mode`
      closes the run failed outside worker mode. api suite 780/3, core lanes 329 green,
      all mutants killed and files verified byte-identical after restore.
    - F5 (FE dropped the actionable `error` sentence) + F7 (limit-1 watch misreports a
      superseded run): FIXED by the dashboard fix agent (tests commit `6fed6b54`) — watch
      repointed to the pair-scoped status endpoint (mounted tests assert the owner-gated
      route is NEVER called), newer-run mismatch → its own "superseded" copy (an OLDER
      reported run means our press isn't visible yet — wait, don't misdeclare), `error`
      shown over `reason` on every real ending. Two extras kept: persistently failing
      status reads END the watch carrying the transport's message (3 fails + erroring), and
      a latent bug fixed — only TERMINAL answers short-circuit, so the 30-min bound now
      reaches a run stuck reporting `running`. 1384/0 unit, tsc + lint clean, 8 mutants
      killed.
    - F6 (completed note overclaims; retraction-candidates count only logged) — ACCEPTED as
      a nit for now; recorded under Future improvements. F8 (stub-only schema construction,
      untested route handlers) — FIXED with the F1 commit (real-model construction + direct
      route-handler tests).

## Production AD rollout — COMPLETE 2026-08-14 (all eight steps)

Owner-run, verified step by step: Phase A backfill to 2020 (catalog 1,033 → 2,167; killed
deliberately at 2020, watermark correct for incremental acquires), AIXL roster repair,
evaluate (27/39/27 applicable; the 111 not_applicable→unknown demotions are the engine-axis
honesty fix; AIXL's 21 flips = the roster repair exactly as rehearsed; ONE AD left applicable
— FAA 2023-15-05, now family_grade_ambiguous, awaiting a human ruling on the review page),
materialise 256/281/256 docs (`--ceiling 350`; the default 150 would have refused every
pair), retract of AIXL's 8 stale docs (−70 objects, AIXL only — cross-partition isolation
held live). Verdict-delta snapshots/compares read clean at every step; rulings cleared 0.
ManualsMT census re-pinned (commit `5bf3be4c`) with the identity hash corrected to exclude
`ingested_at` (write provenance necessarily differs per pair under Model B).

**Item 14's gate is now OPEN** — the pipeline is proven end to end in production.
Item 14 execution started 2026-08-14 under its own plan:
`copilot-mro/docs/plans/ad-phase-d-notifications.md` (owner-approved design — three
effective-state transition classes, commit-then-notify, legacy path retired in Phase 4).
**All five phases LANDED the same day** (test commits `fffc82f`, `5bf0cccd`, `a18c2426`,
`c7fd8af7` in copilot-mro; `31df79d` + `37e0d1c` in dashboard; production edits uncommitted
per house rule). The notification path is **live-verified on `copilot_mro_test`** — one sweep
wrote 8 rows across all three types with correct payloads. `fetch_new_ads.py` is now
acquisition-only (1064 → 424 lines; legacy `--operator`/`--notify` invocations exit 2 by name),
so the stub-stamping footgun is closed. **Item 14 CLOSED 2026-08-14**: both review fix passes
landed (seeder tenant-RLS defect, dispatcher counter/abort defects) plus a final review + fix
round that caught and closed a BLOCKER the first fix introduced (`load_fleet` had no tenant
predicate and the settings pool is the `postgres` superuser, so the tenant threading re-stamped
foreign tails — now tenant-scoped everywhere, mutation-proven). Final state: lanes 532 (unit/ad
+ db/ad) / 1409 (dashboard) green; live re-smoke seeds 24 tenant-correct compliance rows
(zero foreign tails) with proven idempotence. Fix-pass test commits: `c6aad223`, `983d9e83`,
`0033d98` (dashboard), `942d5b45`.

**Both tenancy rulings RESOLVED and SHIPPED 2026-08-15** (implemented + adversarially
reviewed + cleanup round; record = `docs/plans/tenancy-root-fixes.md`, test commits utils
`59b2280`+`f6ef56b`, copilot-mro `06e19b0b`+`2ee6c773`, core `a94af8a`):
`RowTenancy._tenant_id` now prefers the in-force binding over settings, and the settings-pool
default user is `flynapse_app` (superuser only by explicit config), with belt-and-braces
tenant/operator predicates on both AD gate queries, the copilot-mro check/composition
split-brain closed, `run_db_lane.py` restored via owner credentials, and the missing-`.env`
canary back in `db_guard`.

**DONE 2026-08-15**: checked notifications bootstrap on the api worker's boot path —
bootstrap-then-verify via new `_require_notification_tables()` (refusal names core's
owner-run bootstrap), adversarially reviewed, 53/53 green with mutation proof; notes +
triage = `docs/plans/tenancy-root-fixes.md` §"Checked notifications bootstrap". Test commit
api `c476f19`; production edits (`worker.py`, core `notifications/postgres_init.py`
docstring) UNCOMMITTED for the owner.

Still with the owner: commit the uncommitted production edits across repos (and note utils
`231517c` bundles the tenancy production edits with unrelated LLM-metering work — split it
if separability matters); the email digest + recompute-route legs of the AD smoke need a dev
stack/SMTP session; rule FAA 2023-15-05 on `/mro/airworthiness`.
Outstanding for the owner: rule FAA 2023-15-05 on `/mro/airworthiness` (AIXL, unknown
filter); the pre-existing estate-vs-cluster entitlement contention
(`test_every_counted_partition_is_an_entitled_one` + 5 siblings) remains on the ruling
register, unchanged by the rollout.

## Future improvements

- **F6 (accepted nit)** — the completed materialise note overclaims when targets=0, and the
  runner's summary counts (materialized / unmaterialisable / retraction_candidates — stale
  not_applicable docs still in the corpus) exist only as a worker log line; the run row has
  no field for them. Complete fix: a small `result jsonb` on `automation_runs` the runner
  fills, surfaced by the status endpoint and rendered on the page. Deferred: retraction is
  CLI-owned by recorded decision, and the counts are visible in worker logs today.
- **$5 reservation floor per materialise run** (`reservation_for` deliberately floors at the
  default): harmless at dev scale, but a bulk-materialise UI would drain a tenant's $50/day
  on free jobs. Complete fix: exempt non-LLM kinds from `_reserve` — a deliberate money-path
  change needing its own review.
- **`attributed_to`'s settings-singleton mutation** is still the underlying hazard the
  runner's lock and worker-mode guard fence off. The elegant fix is threading explicit
  attribution through `row_tenancy.tenancy_values` so Phase C never mutates process globals
  — deferred until after the production rollout retires the pressure on that script.

## Lessons

- (from the merge session) Clear `__pycache__` before trusting any lane verdict on WSL2 —
  stale bytecode fakes both green and red. Run every new live test file ALONE as well as in
  its lane.
