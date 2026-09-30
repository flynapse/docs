# copilot-mro full-suite reds — diagnosis and fix plan

**CLOSED and PUSHED (2026-09-30):** core `badd671`, copilot-mro `973200cb` (register update `9b433aea`). The
post-merge whole-tree non-db lane on the primary: 15,142 passed, 0 failed, 0 errors. The db lane outside `tests/db`
now collects and surfaced FI-14 (two SQL-example live checks on aged seed dates).

Register: copilot-mro `docs/plans/open-items.md` §8 **FI-13**. Raw evidence, probes and logs:
`~/.claude/scratch/full-suite-reds/` (`diagnosis.md` is the incremental record; `probe/` holds the
diagnostic pytest plugins used to find the polluters).

## Context

The first real full-suite runs (2026-09-29, the post-merge gates of the user-erasure P2 and the
DB-roles steps 1–2 merges) surfaced reds that no earlier gate ever ran. Every one is pre-existing:
identical before and after both merges, and A and B are red at the older pushed `fccd7b6f` too.

- Tree: `/home/aditya/Code/copilot-mro-reds`, branch `full-suite-reds` from `langgraph-merge`
  `3f46076d`. It builds against the PRIMARY `core` and `utils`.
- Standard prefix for every command below, run from the tree root: `PYTHONPATH=<tree>
  DEBUG=false POSTGRES_DB=copilot_mro_test /home/aditya/Code/pytest-slot.sh --
  /home/aditya/Code/api/.venv/bin/python -m pytest -p no:cacheprovider`, adding
  `-W ignore::UserWarning:_scripts_workspace_root_impl` under `-n`.
- Whole-tree non-db lane (the gate's stream A): `tests --ignore=tests/e2e --ignore=tests/db -m
  "not db and not corpus_live and not live_agent_state and not compose_stack and not
  live_browser_server and not weaviate_live" -n 4`. Last result on both gates: 14 failed, 4 errors
  (A ×3, B ×1, C ×10, D ×2 collected twice), 15,009 passed.
- **Fast whole-tree repro of C and D (about one minute):** the same whole-tree arguments with
  `-n 0 --continue-on-collection-errors -k "test_debug_dumps or test_lang_sad_activation"`. C
  and D both happen at COLLECTION time, so `-k` keeps every polluting import while running only
  the victims. Today: 10 failed, 21 passed, 2 errors.

Test or code, per red: A test (stale), B test (stale), C test isolation (two polluters), D a
cross-repo helper name collision (code, in core's scripts), E test isolation (two files).

---

## A. `tests/config/settings/test_config.py` ×3

**Symptom.** `'Settings' object has no attribute 'followup_max_additional_attempts'` (×2) and
`'sandbox_max_concurrent'`. Deterministic, alone and at `fccd7b6f`.

**Cause.** The settings were removed ON PURPOSE and the tests were left behind.
- `4ee3748d` (2026-07-21, legacy pipeline removal) deleted their only consumers: the legacy
  excel-writer service (`sandbox_max_concurrent`, `sandbox_queue_timeout`) and the legacy
  `main_agent` (`followup_max_additional_attempts`).
- `eca771b3` (2026-07-26) then removed about fifty-five dead fields from `copilot_mro/app/config.py`
  in one sweep, these three among them. At `eca771b3^` nothing outside `config.py` and this test
  read them.
- The live sandbox capacity gate is env-driven in
  `copilot_mro/app/services/agent_shared/tools/system/_sandbox_core.py:52-54`
  (`AGENT_SDK_RUN_CODE_MAX_CONCURRENT`, `AGENT_SDK_RUN_CODE_QUEUE_TIMEOUT_S`) and is covered by
  `tests/agent_sdk/tools/system/test_agent_sdk_sandbox_core.py`.
- It was catalogued as "settings drift" three times and never fixed
  (`consumer-product-merge.md`, `langchain-1x-upgrade.md` P1 and P2,
  `langgraph-parallel-wrappers-audit-merge-scaleout.md`).

**Test or code.** Test. The behaviour it pins no longer exists by design.

**Fix.** Delete the three stale tests and keep `test_cross_source_fusion_flag_defaults_on_and_reads_environment`,
which pins a live setting. No production change. Blast radius: that one file.

**Proof.** `tests/config/settings/test_config.py` goes from 3 failed, 1 passed to 1 passed. A repo
search for the three setting names and their env aliases outside `docs/` then returns nothing. No
mutant, because nothing is left to mutate.

---

## B. `tests/parsers/pilot/test_parser_metadata_sidecars.py::test_ftd_insert_to_postgres_ensures_standalone_tables`

**Symptom.** `assert [] == [('ftd_documents',)]` at `:857`. Deterministic, alone and at `fccd7b6f`.

**Cause.** The FTD gate changed on purpose and the test's stub did not follow.
- The table did NOT move. It is still `ftd_documents` (`ftd_parser.py:1453`, `:1509`).
- `3adba3ef` (2026-08-13, "provisioning creates relations; seeders, ingest and tests assert")
  changed `_ensure_ftd_postgres_tables` (`copilot_mro/app/services/parsers/ftd_parser.py:1432-1460`)
  from `initialize_postgres_tables` (create) to `assert_tables_present` (check only). The reason:
  the app role has no CREATE, so the old self-heal could only log and let the insert run anyway.
  That commit updated five `tests/db` fixtures but not this test.
- The test's fake `copilot_mro.app.db.postgres_table_definitions` (`:821-836`) still offers only
  `initialize_postgres_tables`. The gate's `from … import assert_tables_present` (`:1448`)
  therefore raises ImportError, the gate logs "definitions unavailable" and returns, and nothing is
  recorded. The INSERT still runs, so only the first assertion fails.
- The crew and AD-compliance gates from the same commit are pinned in
  `tests/unit/ingest/test_ingest_table_provisioning_gate.py`. The FTD gate is pinned nowhere else.

**Test or code.** Test (stale stub). One code-side discrepancy turned up on the way; it does not
cause this red and goes under Future Improvements: the gate's docstring says an absent table
"propagates", but its only caller swallows it.

**Fix.** Rewrite the test against the check-only contract, in the sibling suite's style: "what does
not happen" is asserted as well as what does.
- The fake definitions module offers a recording `assert_tables_present`, plus a recording
  `initialize_postgres_tables` that must stay uncalled, because the gate must issue no DDL.
- Assert the gate checked exactly `ftd_documents`, no DDL ran, the INSERT into `ftd_documents` was
  issued, and nothing went to `manual_metadata`.
- Add the absent-table case: the fake assertion raises the provisioning `RuntimeError`, and no
  INSERT into `ftd_documents` reaches the Postgres stub. That is the behaviour `3adba3ef` exists
  for. Pin only "no INSERT", which holds under either ruling on the swallow question.
- Rename the test to say "asserts" rather than "ensures".

Test-only, one file.

**Proof.** The single test is red now and green after, and the new absent-table test is green.
Mutants, through `mutant.sh`, aimed at `tests/parsers/pilot/test_parser_metadata_sidecars.py`:
1. The gate checks a different table name. It must be killed.
2. The gate goes back to calling `initialize_postgres_tables`. It must be killed.
3. The absent-table raise is removed from the gate. The absent-table test must kill it.

A survivor is reported only after the full lane passes with it applied. The full lane here is the
folders covering `ftd_parser.py`: `tests/parsers/`, `tests/unit/ingest/`, and any other folder that
imports it.

---

## C. `tests/unit/lang_agent/test_debug_dumps.py` ×9 and `test_lang_sad_activation.py::test_a_model_that_calls_the_tool_gets_the_framed_context_and_the_record_reads_used` (whole-tree only)

(The brief counted C as ten `test_debug_dumps` failures plus one SAD failure. Both logs show nine
plus one, ten in total.)

**Symptom.** No dump files are written: empty listings and `StopIteration`. All pass alone.

**Cause: two polluters leave a second live copy of `copilot_mro.app.services._debug_dump`.**
- `tests/agent_sdk/core/test_agent_sdk_debug_hooks.py:21-34` and
  `tests/agent_sdk/core/test_agent_sdk_tool_io_capture_sink.py:20-31` each run a hand-rolled `_load`
  at module scope. It writes a freshly executed `_debug_dump` into `sys.modules` under the real
  dotted name and never restores it. The parent package's `_debug_dump` attribute keeps pointing at
  the original.
- Why they load it: `load_sdk_module("_debug_hooks")` has to bind that copy, because
  `agent_shared/_debug_hooks.py:15` imports `dump_debug` from the real dotted name. They only need
  the copy while that one load runs.
- The victim side: `copilot_mro/app/services/lang_agent/debug_dump.py:25` imports `dump_debug` with
  a relative import, which resolves through `sys.modules`. In a whole-tree run it first executes
  AFTER the polluters, so the lang wrapper writes through the copy.
- The victims' fixtures (`test_debug_dumps.py:35-43` `dumps_on`, `test_lang_sad_activation.py:205-209`)
  reach the module by importing `_debug_dump` from the package. Python answers that from the PARENT
  ATTRIBUTE, which is the original. So the fixtures patch `_debug_enabled` and `_repo_root` on a
  module nobody writes through, `DEBUG=false` stands, and nothing is dumped.
- How it was found: `probe/modwatch.py` reports, per collected module, whether `sys.modules` and the
  parent attribute still agree. They agree after `test_agent_sdk_audio_context_harvest.py` (the
  first real import). They split after `test_agent_sdk_debug_hooks.py` and split again after
  `test_agent_sdk_tool_io_capture_sink.py`.
- History: the `debug_hooks` loader dates from June/July, the capture-sink copy from `54a01f39`
  (2026-09-14), and the victims from `96c65c3f` (2026-08-21) and `3d4643d1` (2026-09-10). So C has
  been red in every whole-tree run since 2026-08-21.

**Test or code.** Test isolation. The polluters are wrong; the victims are not.

**Fix.** In each polluter, run the private `_debug_dump` load and the `_debug_hooks` load inside the
existing `tests/_sdk_loader.py` `evicted_modules` window, naming `copilot_mro.app.services._debug_dump`.
- On exit, that helper restores BOTH `sys.modules` and the parent attribute. Its docstring describes
  exactly this "two live copies outlive the test" failure.
- The polluters' own tests keep working. Their `hooks_mod` holds the copy's `dump_debug`, whose
  globals are the copy's, so their existing direct patching of the copy still steers it.
- This mirrors the scoped-load precedent in `tests/agent_sdk/tools/synthesis/test_pilot_generation_prompt.py`
  (test-hygiene audit 5.2a).

Test-only, two files; the victims are untouched. Simulated without editing: `probe/simfix_c.py`
restores the entry right after each polluter is collected, and harvest plus both polluters plus both
victims then gives 64 passed.

**Proof.**
- Minimal repro, red now (10 failed, 48 passed): `tests/agent_sdk/core/test_agent_sdk_audio_context_harvest.py
  tests/agent_sdk/core/test_agent_sdk_debug_hooks.py tests/unit/lang_agent/test_debug_dumps.py
  tests/unit/lang_agent/test_lang_sad_activation.py -n 0`. The same with
  `test_agent_sdk_tool_io_capture_sink.py` in place of `…debug_hooks.py` also gives 10 failed. Both
  go green after the fix.
- The fast whole-tree repro from Context: the ten C failures go away.
- Mutant: remove the window from either polluter alone. Its minimal repro turns red again, which
  proves each wrapper is needed.
- Optional: `probe/splitcount.py` (`-p splitcount --co`) no longer lists `_debug_dump`.

---

## D. `tests/unit/chat_history/test_chat_turn_facts_value_gates.py` and `…_writer.py` — collection ERROR (whole-tree only)

**Symptom.** `cannot import name 'sibling_variant' from '_workspace'
(/home/aditya/Code/copilot-mro-reds/scripts/_workspace.py)`, raised while loading core's
`scripts/backfill_chat_turn_facts.py` by path. Both files pass alone (73 passed).

**Cause: a helper NAME shared by two repos, resolved through `sys.path` order (not the module
cache).**
- core's `scripts/backfill_chat_turn_facts.py:98-99` APPENDS its own directory to `sys.path` (so it
  comes last) and then imports `_workspace` by bare name. Core's other four users of the helper do
  the same: `run_db_lane.py`, `review_improvement_findings.py`, `purge_product_events.py` and
  `set_tenant_content_capture.py`.
- copilot-mro also has a `scripts/_workspace.py`, with a different API (`sibling_checkout`, not
  `sibling_variant`).
- From the first seed test onward, copilot-mro's `scripts/` sits at `sys.path[0]`.
  `tests/seeds/aog/test_aog_seed.py` loads `scripts/aog/seed_aog.py`, whose line 30 inserts it,
  and about twenty more collected files insert it again. So core's bare import finds copilot-mro's
  file first.
- `probe/modwatch.py` shows `_workspace` absent from `sys.modules` until this very import.
  `probe/pathwatch.py` shows copilot-mro's `scripts/` at index 0 from `test_aog_seed.py` onward.
- copilot-mro itself never imports its helper by bare name. Both of its consumers load it BY PATH
  under unique names: `scripts/ad/_common.py:26-40` and `scripts/migrate_tenancy_schema.py:1126-1136`.
- `_workspace.py` is the only module basename that copilot-mro's `scripts/` and `scripts/ad/`
  share with core's `scripts/`.
- Both helpers landed the same day in parallel lanes (copilot-mro `5a783cb8`, core `f0d7ef5`, both
  2026-09-21). The D tests date from 2026-09-20, so D has been red in every whole-tree run since
  2026-09-21.
- core's comment at `:94-98` says the append "makes the import hold when a test loads the file by
  path". That is false in any process where another `_workspace.py` comes earlier on `sys.path`.

**Test or code.** Code: a bare-name import of a name another repo also defines. This is FI-9's
class. FI-9 was closed by *removing the shared name rather than guarding it*: shift-optimizer's
bare-imported helper became `_optimizer_schema.py`.

**Fix: remove the shared name. OWNER DECISION on which side.**
- **Recommended: rename core's helper** to a workspace-unique name (for example
  `_core_workspace.py`).
  - Update its five bare importers, their comments, and core's guard
    `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` (about sixteen references to
    the name).
  - Why this side: it is the side that imports by bare name, which is the fragile half. After the
    rename, no other repo's `_workspace.py` on any path can capture it.
  - Blast radius: core `scripts/` and one core guard test. It needs a core branch in a core worktree
    (not the primary checkout), a core full suite at hand-back, and a core merge.
- **Alternative, copilot-mro only: rename copilot-mro's `scripts/_workspace.py`.**
  - Update its two by-path loaders and about fifteen path references across three tests
    (`test_ad_acquire_watermark.py`, `test_cross_repo_reads_name_their_checkout.py`,
    `test_phase1c_nonagent_scope_guard.py`).
  - This ends today's collision without touching core. But core's bare import of the generic name
    stays exposed to the next repo that adds a `_workspace.py` to a directory on the path.
- Rejected: inserting at the front of the path instead of appending, or evicting `_workspace` around
  the load. That guards the collision instead of removing it, which is the approach FI-9 found
  unable to catch the mis-bind it was written for.

**Proof.**
- Minimal repro, red now (6 passed, 2 errors in 1.3 s): `tests/seeds/aog/test_aog_seed.py
  tests/unit/chat_history/test_chat_turn_facts_value_gates.py tests/unit/chat_history/test_chat_turn_facts_writer.py
  -n 0 --continue-on-collection-errors`. After the fix: 0 errors.
- The fast whole-tree repro from Context: the two D errors go away.
- If core is renamed: core's own tests that load the five scripts are green, and so is its full
  suite at hand-back, notably `tests/unit/analytics/`, `tests/unit/infra/` and
  `tests/unit/observability/`.
- No mutant. The rename is structural; the minimal repro is the discriminating test.

---

## E. xdist-only reds in `tests/api/tenancy/` (both files carry `pytest.mark.db`)

The gate runs db lanes serially, so E only appeared when someone ran these files under `-n 4`. Both
are still real defects, because each test fails when SELECTED ALONE, serially. Neither needs xdist to
prove, and per the workspace rule, shared-DB lanes stay at `-n 0`.

### E1. `test_operator_grain_isolation.py`: 4 errors under `-n 4`, 8 passed serially

**Cause.** The `resolve` fixture imports `flynapse_api.middleware.cache` at `:309`, BEFORE calling
`_load_middleware()` at `:313`.
- `_load_middleware()` (`:94-100`) is what puts api's `flynapse_api/` directory on `sys.path`. It
  reproduces the deployment's path.
- Importing the cache module runs `flynapse_api/middleware/__init__.py`, which imports `.auth`.
  `api/flynapse_api/middleware/auth.py:36` does `from auth.dependencies import …`, which only
  resolves with that directory on the path.
- Serially, the gate test (`:109`, which calls `_load_middleware()` at `:166`) runs first in the
  same process and leaves the path in place. So the fixture works only as a side effect of a sibling
  test. Under xdist, the four `resolve` tests land on workers that never ran the gate test.
- Written this way since `70ae423d` (2026-08-03).

**Test or code.** Test (a hidden dependency on another test).

**Fix.** In `resolve`, establish the gateway path (`_load_middleware()`) before importing the
cache manager. Test-only, one fixture.

**Proof.** `tests/api/tenancy/test_operator_grain_isolation.py::test_an_ungranted_member_reaches_nothing
-n 0` gives 1 error (`No module named 'auth'`) now and passes after. The whole file serially stays
at 8 passed.

### E2. `test_endpoint_isolation.py::test_the_core_document_cache_keys_name_the_tenant`

**Cause.** The test (`:1027-1055`) issues no request of its own.
- It reads the keys `test_t2_document_filters_hold_no_t1_values` (`:968-1024`) left in the
  module-scoped `caches` recorder (`:347-384`). Its own guard message says "run them together".
- xdist gives each worker its own module-scoped fixture, so a worker without the writer sees an
  empty recorder. The same happens under any `-k` selection.
- Since `d073c114` (2026-07-30).

**Test or code.** Test (it reads another test's state).

**Fix.** Make the diagnosis test self-sufficient.
- It resets the `core_documents` recorder, then issues T1's and T2's `/documents/filters` requests
  itself, using the file's `_as_t1` / `_as_t2` helpers and the `client`, `auth`, `t1` and `t2`
  fixtures. It then runs its unchanged key-shape and two-tenant assertions.
- No assertion is removed, and it stays a separate test, so the "diagnosis vs contract" split in its
  docstring holds.
- Update the docstring's "reads the keys … left behind" paragraph.

Test-only, one test.

**Proof.** Selected alone serially, the test fails now (`cache.sets == []`) and passes after. The
whole file serially stays green. Optional mutant: a core document cache key that drops the tenant
must fail this test. Run it only in a core WORKTREE, never on the primary `core` checkout, which
other agents build against.

### E and FI-12

- **E: no.** FI-12 is placeholder `copilot_mro.app.db` packages left in `sys.modules` by the
  `tests/db/chat_history` stubs. E1 is an import-order dependency on a path side effect. E2 is a
  test reading another test's recorded state.
- **D: no.** It is FI-9's class, a helper name shared across repos.
- **C: same class, different cause.** C is FI-12's class (an unscoped module-table write at
  collection), but on a different module and file set. FI-12's fix (a lazy `app/db` package, or
  the `_package_stubs` helpers) does not touch C.

---

## F. `flynapse_readonly` narrowing (recorded only)

The owner revoked `pg_read_all_data` from `flynapse_readonly` and created `flynapse_inspect`. A
separate batch is repointing the tests that read beyond the 19-table allowlist. None was met in this
diagnosis: the whole-tree logs pre-date the revoke, and no run here hit a readonly-role permission
error.

---

## Tasks (implementer)

Read `## Lessons` first. One commit per red, each by named pathspec. Never amend, rebase, push or
merge. Commit early.

- [x] **A:** delete the three stale settings tests. Run `tests/config/settings/` and confirm the
      repo search for the retired names is empty.
- [x] **B:** rewrite the FTD gate test against `assert_tables_present`: the no-DDL half, the
      absent-table no-INSERT case, and the rename. Run `tests/parsers/pilot/` and `tests/unit/ingest/`.
      Run the three mutants through `mutant.sh`.
- [x] **C:** put `evicted_modules` around the `_debug_dump` and `_debug_hooks` loads in both
      polluters. Run the minimal repro (both variants), `tests/agent_sdk/core/` and
      `tests/unit/lang_agent/`, then the fast whole-tree repro. Run the per-polluter mutant.
- [x] **D:** rename core's helper to `_core_workspace.py` (controller ruling) in the core
      worktree `core-reds`. Run the minimal repro, then the
      touched folders on the renamed side. If core is renamed, run core's full suite at hand-back.
- [x] **E1:** reorder the `resolve` fixture. Run the single-test selection and the file, serially.
- [x] **E2:** make the cache-key test issue its own two requests. Run the single-test selection and
      the file, serially.
- [x] **Hand-back:** run the FULL copilot-mro non-db lane once, at `-n 4`, on the tip. Expect A–D
      absent from the failures; record the counts here. E is proven by the serial selections above,
      because db lanes stay serial.
- [ ] Update FI-13 in the register with the commits, and move it to closed once every item lands.
      (Commits recorded in `7784abfc`; it moves to closed when both branches merge.)
- [ ] Adversarial review of the diff by a fresh subagent, then triage.
      (Review done 2026-09-29: `review.md` in the SDD directory, 0 Critical, 1 Important, 2 Minor;
      its findings and the owner's FTD "stop" ruling are carried by fix round 2.)
- [x] **Fix round 2:** review I-1 (B's provisioned case pins the exact statement list, the absent
      case pins that nothing reached Postgres), M-1 (the idle `copilot_mro.app.db` placeholder
      dropped), M-2 (`pytest.raises` of the dedicated type, not `suppress`), and the owner's FTD
      "stop" ruling (a dedicated type, the insert's let-through, one check before the per-document
      loop). Mutants: the let-through removed, widened, and matching a bare `RuntimeError`; the
      gate converting everything; the pre-loop check removed; B1–B3 and the review's R1.
- [x] **Fix round 3 (last):** re-review m-1 (the absent run test pins "nothing parsed"), m-2 (the
      fake `utils.postgres` records `execute_many`, `fetch_one`, `fetch_all`), and the controller's
      rulings on the re-review's two notes: the command checks provisioning before its S3
      download, and logs a fixed remedy sentence and exits 1 when it catches the stop.

### Implementation notes (2026-09-29, implementer)

Trees: copilot-mro `/home/aditya/Code/copilot-mro-reds` on `full-suite-reds`; core
`/home/aditya/Code/core-reds` (plain `git worktree add`, branch `full-suite-reds` from `bcdccb3`).
Mutant inputs, kill logs and the hand-back script: `~/.claude/scratch/full-suite-reds/fix/`.

- **A** — copilot-mro `c8dbd60a`. `tests/config/settings/`: 11 passed. A case-insensitive
  `git grep` for the three names outside `docs/` (which also covers the env aliases) is empty.
- **B** — copilot-mro `4dd06234`. **Deviation:** the helper (`_stub_ftd_app_db`) also fakes
  `copilot_mro.app.db.row_tenancy`. The cause above holds for the whole-tree run (its log shows
  "definitions unavailable" and then "Inserted FTD"). Alone, or with just its file, the old test
  never reached the gate at all: the placeholder `copilot_mro.app.db` hid the real package, nothing
  earlier had loaded `row_tenancy`, so the insert's own import failed ("Postgres service
  unavailable") and it returned. Without that fake the rewrite was red in isolation. The absent-table
  case wraps the call in `contextlib.suppress(RuntimeError)`, so it holds under either ruling on the
  swallow. Old test alone: 1 failed; the two new tests: 2 passed. Folders covering `ftd_parser.py`
  (`tests/parsers/`, `tests/unit/ingest/`, `tests/smoke/ingest/`, `tests/unit/observability/`):
  1507 passed, 32 skipped. Mutants all KILLED (table below).
- **C** — copilot-mro `4fd40c4c`. Minimal repro: 10 failed, 48 passed → 58 passed; the capture-sink
  variant: 10 failed, 34 passed → 44 passed. Harvest + both polluters + both victims: 64 passed;
  polluters first, no harvest: 57 passed. `tests/agent_sdk/core/` + `tests/unit/lang_agent/`
  (`-n 4`): 2540 passed, 1 skipped. `probe/splitcount.py` no longer lists `_debug_dump` (the two
  latent splits under Future Improvements remain).
- **D** — core `a7f1d90`. Five importers, their comments (now saying why the name is unique), the
  helper's docstring, its internal root-loader spec name (`_core_workspace_root_impl`; nothing
  referenced the old one), 17 references in core's guard, and the G.61 plan's four mentions. Those
  are annotated "(now `_core_workspace.py`)" rather than rewritten, because they record commits made
  under the old name. Historical mentions in other repos (api `g53-checkout-pin-by-git-family.md:226`,
  workspace `observability-telemetry-merge-and-completion.md:3880`) are left as history.
  **copilot-mro-reds reads core-reds on its own:** the D tests call `sibling_variant(__file__,
  "core", …)`, which resolves the `-reds` variant. A probe (`probe/whichcore.py`) shows
  `backfill_for_value_gates`, `backfill_for_writer_parity` and `_core_workspace` loaded from
  `core-reds/scripts/`. Minimal repro: 6 passed, 2 errors → 79 passed. Fast whole-tree repro (C and
  D together): 10 failed, 21 passed, 2 errors → 31 passed. Core targeted
  (`tests/unit/{analytics,infra,observability,db,automations}`, `-n 4`): 2074 passed, 1 failed. The
  failure is `test_the_variant_hazard_is_real_in_this_workspace_right_now`, which depends on the
  workspace: it wants twin checkouts of api, core and copilot-mro, and no api twin exists today. It
  fails on the unchanged primary `core` too, together with
  `test_sibling_variant_falls_back_to_the_bare_name_when_there_is_no_twin`, the failure the
  post-merge gate recorded.
- **E1** — copilot-mro `a5389fdb`. Single-test selection: 1 error (`No module named 'auth'`) → 1
  passed. The file serially: 8 passed. Without the gate test: 7 passed.
- **E2** — copilot-mro `63e13f9f`. Alone: failed (`cache.sets == []`) → 1 passed. The file serially:
  26 passed. `tests/api/tenancy/` serially: 325 passed. The optional mutant ran in core-reds, with
  core-reds put on `PYTHONPATH` and the loaded file checked by the probe: a filters key without the
  tenant is KILLED by the diagnosis test alone.
- Register: copilot-mro `7784abfc`. FI-13 records the commits and stays open until both branches
  merge.

| Mutant | Aimed at | Result |
|---|---|---|
| B1: the gate checks `ftd_document` | `test_parser_metadata_sidecars.py` | KILLED rc=1 (both FTD tests) |
| B2: the gate goes back to `initialize_postgres_tables(table_names=["ftd_documents"])` | same | KILLED rc=1 (both FTD tests) |
| B3: `except RuntimeError: raise` removed from the gate | same | KILLED rc=1 (the absent-table test alone) |
| C: `debug_hooks` load unscoped | its minimal repro | KILLED rc=1 (10 failed) |
| C: `tool_io_capture_sink` load unscoped | its minimal repro | KILLED rc=1 (10 failed) |
| E2 (optional): core filters cache key drops the tenant | the diagnosis test | KILLED rc=1 |

**Hand-back lanes:** run once on the tips (copilot-mro-reds `7784abfc`, core-reds `a7f1d90`). Script and logs:
`~/.claude/scratch/full-suite-reds/fix/handback/`.
- copilot-mro whole-tree non-db lane (`-n 4`): **15,067 passed, 61 skipped, 320 deselected, 0
  failed, 0 errors** (exit 0). The gate recorded 14 failed, 4 errors, 15,009 passed and 34 skipped.
  - Collection matches the gate exactly apart from this batch: 15,128 selected here against 15,057
    plus the 2 D files there. The difference is +73 D tests, −3 A tests and +1 B test.
  - The 27 extra skips come from the worktree, not the fixes. `test_data/` is gitignored and
    exists only in the primary checkout, so its fixture-gated tests skip here: crew, ISDP, task-card,
    WDM FM, the AIXL/Akasa corpora and the NDT samples. So does the Phase-1c cross-repo guard,
    which looks for a `utils-reds`.
  - A skip census over the 152 non-db files that can skip lists every reason:
    `handback/skipcensus.log`. The merge gate on the primary runs those tests.
- core non-db (`tests/unit tests/api tests/test_comments_endpoints.py`, `-n 4`, `ENV_FILE` set):
  **4,044 passed, 1 failed.** The failure is `test_the_variant_hazard_is_real_in_this_workspace_right_now`,
  a workspace-state guard. It needs twin checkouts of api, core and copilot-mro, and today there is
  no api twin. It fails on the unchanged primary `core` too. The collected count, 4,045, is the same
  in core and core-reds.
- core db + authz (`tests/authz tests/db`, `-n 0`, `copilot_mro_test`): **997 passed, 1 skipped, 2
  xfailed** (exit 0), which is the gate's count. `tests/db/analytics` loads three of the renamed
  scripts.

**Learnings**
- A stale stub can hide a second order dependency. B's old test failed at its first assertion in
  every selection, but for a different reason in each, depending on what had run before it. A claim
  like "the rest still runs" needs checking in isolation, not only from the whole-tree log.
- A `-<variant>` worktree of a sibling is picked up by the other tree's `sibling_variant` without
  any path change. That covers by-path loads of the sibling's scripts. `import core` still comes
  from the venv `.pth` (the primary) unless `PYTHONPATH` names the worktree.
- Core's variant-hazard guard and its no-twin test depend on the workspace: their result changes
  with the checkouts beside core at run time. Creating `core-reds` changed it.
- A worktree has no gitignored `test_data/`, so its full lane skips about 27 tests that the
  primary's gate runs. Compare skip counts across trees with that in mind, and check skip reasons
  (`-rs`) before reading a skip delta as a regression.

### Fix round 2 (2026-09-29, fresh implementer): review I-1, M-1, M-2 and the owner's FTD "stop" ruling

Post-review changes, recorded here as the phase's source of truth. Brief:
`Code/.superpowers/sdd/copilot-mro-full-suite-reds/fix2-brief.md`; report `fix2-report.md` beside it.
Mutant inputs, runners and per-mutant pytest output: `~/.claude/scratch/full-suite-reds/fix2/`.

Commits on copilot-mro `full-suite-reds` (tip before: `7784abfc`):
- `7365ca95` production + B's tests. `ftd_parser.py` gains `FtdTablesNotProvisioned(RuntimeError)`.
  The gate converts the check's `RuntimeError` into it (`raise … from exc`; its own message names
  `ftd_documents` and `provision_rls.py` and does not echo the cause's text, which the M-TRACEBACK
  guard forbids). `_insert_ftd_to_postgres` lets exactly that type through, beside the catalog
  write's `TenancyError` precedent. `process_ftd_pdfs` calls the gate once, first, when
  `insert_postgres` is set (controller ruling on the review's item 7), so the run stops before any
  catalog or FTD row. The module and gate docstrings say so.
- `265f7ea1` the post-merge scope guard (`tests/unit/observability/test_phase1c_nonagent_scope_guard.py`)
  approves `ftd_parser.py` under the owner's ruling. **Not in the brief; found by the covering
  lane:** the guard admits a post-merge production path only by approval, and it failed on the
  first run (1 failed, 1511 passed, 32 skipped). With the approval it passes.
- `039da2d2` register: FI-13's "still open, owner" sentence now records the ruling as built. FI-13
  stays `[ ]` until both branches merge.

B's tests (`tests/parsers/pilot/test_parser_metadata_sidecars.py`), 2 → 7:
- provisioned: the statement list is exactly the one `INSERT INTO ftd_documents` (I-1), plus
  `ddl == []`;
- absent (renamed `…stops_the_run_when_its_table_is_absent`): `pytest.raises(FtdTablesNotProvisioned)`
  (M-2; `contextlib` gone), message names the table and the remedy, `__cause__` is the check's
  refusal, `checked`, `ddl == []`, `fake_postgres.calls == []`;
- two degrade cases: the check meets a `ConnectionError` (the insert still goes ahead), and the
  insert itself raises a bare `RuntimeError` (logged, not raised). The second is the one that
  holds the let-through to exactly the dedicated type;
- run level: absent → `process_ftd_pdfs` raises with no catalog write and no Postgres statement;
  a provisioned control proves the harness reaches the per-document loop and that the check runs
  once; a dry run (`insert_postgres=False`) never checks.
- M-1: the idle `copilot_mro.app.db` placeholder is dropped. The docstring now says why
  `row_tenancy` is faked: so the insert never imports the real package. Each test passes alone,
  after the real `copilot_mro.app.db` has loaded (41 passed with the ingest gate suite first), and
  in whole-tree collection order.

| Mutant (`ftd_parser.py`, aimed at the B file, `-k` utils, core, flynapse-otel) | Result | Killed by |
|---|---|---|
| S: the let-through removed (the stop swallowed again) | KILLED rc=1 | the absent-table insert test alone |
| EL: the let-through widened to `except Exception: raise` | KILLED rc=1 | the failed-insert degrade test |
| ER: the let-through matches a bare `RuntimeError` | KILLED rc=1 | the failed-insert degrade test |
| EG: the gate converts every error, an unreachable service included | KILLED rc=1 | the unreachable-check degrade test |
| L: the pre-loop check removed (the only check is the insert's, after the catalog write) | KILLED rc=1 | the run-level absent test |
| D: the dry run checks too | KILLED rc=1 | the dry-run test |
| B1: the gate checks `ftd_document` | KILLED rc=1 | 6 tests |
| B2: the gate goes back to `initialize_postgres_tables` | KILLED rc=1 | 6 tests |
| B3: the gate's absent-table stop removed (the refusal degrades in the gate) | KILLED rc=1 | both absent tests |
| R1 (review): raw `CREATE TABLE` through `utils.postgres` before the check | KILLED rc=1 | 6 tests, both I-1 tests among them |

Hand-back lanes on the tip `039da2d2` (logs: `~/.claude/scratch/full-suite-reds/fix2/handback/`):
- the folders covering `ftd_parser.py` (`tests/parsers tests/unit/ingest tests/smoke/ingest
  tests/unit/observability`, `-n 4`): **1512 passed, 32 skipped, 0 failed** (the earlier 1507 plus
  the five new tests);
- the whole tree's collection order, `-n 0 -k "ftd_insert_to_postgres or ftd_run_ or ftd_dry_run"`:
  7 passed;
- on `7365ca95`, the other suites that sweep production files (`tests/unit/infra`, the conflict-target,
  background-tenancy and S3-listing sweeps): 192 passed, 1 skipped.

**Learnings**
- A scope guard over the working tree is a covering test of every production file. The covering
  lane for a production change here has to include `tests/unit/observability`, and an approval
  there travels with the change, citing the ruling that earned it.
- The M-TRACEBACK guard forbids a caught exception's text in a raised message. A converted error
  carries the cause by chaining (`from exc`) and states its own table and remedy.
- A degrade test has to put the non-provisioning error where the widened handler would see it.
  An unreachable check is caught inside the gate, so a widened let-through in the insert survives
  that case; only a failure of the insert itself kills it.



### Fix round 3 (2026-09-29, fresh implementer): re-review m-1, m-2 and notes 1–2

Brief: `Code/.superpowers/sdd/copilot-mro-full-suite-reds/fix3-brief.md` (re-review `rereview.md`
beside it). Mutant inputs, runners and logs: `~/.claude/scratch/full-suite-reds/fix3/mutants/`;
hand-back lane log: `~/.claude/scratch/full-suite-reds/fix3/handback/`.

Commit on copilot-mro `full-suite-reds` (tip before: `039da2d2`): `29fdf7e6`.
- **Note 1 (ruled: do it).** `_main` calls `_ensure_ftd_postgres_tables()` before
  `download_ftd_from_s3` when `--no-insert-postgres` is absent, so an unprovisioned database
  costs no download. `process_ftd_pdfs` keeps its own check for callers that skip `_main`; after a
  pass in `_main` it is a no-op (`_FTD_POSTGRES_TABLES_READY`). The docstring and the comment say so.
- **Note 2 (ruled: do it).** `_main` wraps the check, the download and the run in one `try` and
  catches `FtdTablesNotProvisioned` from either check. It logs one fixed sentence naming
  `ftd_documents` and `provision_rls.py`, never the error's text, and returns 1 (the span then
  records `operation.outcome=error`). The record also carries `failure_fields` of the refusal
  (the chained cause), so the operator's log keeps the refusal's TYPE (a missing table's
  `RuntimeError` vs a setup refusal): once the command catches the stop, the routed excepthook no
  longer prints the chain's types. **Deviation:** the first spelling,
  `failure_fields(exc.__cause__ or exc)`, was flagged by the M-TRACEBACK guard and the register
  reconciliation (a `BoolOp` argument is not a sanctioned `failure_fields` argument); a name bound
  in the handler (`refusal = exc.__cause__ if exc.__cause__ is not None else exc`) passes both.
- **m-1.** `_stub_one_document_ftd_run` records each parsed PDF and returns it. The absent run test
  asserts `parsed == []`; the provisioned control asserts the one PDF was parsed (vacuity guard).
- **m-2.** `FakePostgres` records `execute_many`, `fetch_one` and `fetch_all` as well as `execute`,
  mirroring the sibling provisioning-gate suite; the docstring says why.
- **Four command-level tests** (through `_main`, with the download and the operator resolver
  stubbed and every loguru record kept): absent → exit 1, no download, nothing parsed or written,
  the ERROR records are exactly the pinned sentence, `error_type == "RuntimeError"`, and the
  refusal's text reaches no record; the pre-download check degrades and the run's own check stops
  → the same sentence and exit 1; provisioned → exit 0, one download, one catalog write, one FTD
  insert, one check; `--no-insert-postgres` → exit 0, no check, the download happens.

| Mutant (`ftd_parser.py`, `-k` utils, core, flynapse-otel) | B file | Aimed at one test | Killed by |
|---|---|---|---|
| P: the check moved from before the loop to just before the first catalog write (m-1) | KILLED rc=1 | KILLED rc=1 | the run-level absent test (`parsed == []`) |
| R2: a best-effort `ALTER … ADD COLUMN` through `execute_many`, error swallowed (m-2) | KILLED rc=1 | KILLED rc=1 | the provisioned insert test (exact statement list) |
| L: the pre-loop check removed (re-run) | KILLED rc=1 | KILLED rc=1 | the run-level absent test |
| N: the command's pre-download check removed (note 1) | KILLED rc=1 | KILLED rc=1 | the command absent test (`downloads == []`) |
| DD: the command checks before its download on a dry run too | KILLED rc=1 | KILLED rc=1 | the command dry-run test |
| C1: the command's catch removed | KILLED rc=1 | KILLED rc=1 | the command absent test |
| C2: the command logs the error's text in place of the fixed sentence | KILLED rc=1 | KILLED rc=1 | the command absent test (pinned sentence) |
| C3: the stop exits 0 | KILLED rc=1 | KILLED rc=1 | the command absent test |
| C4: the refusal's type dropped (the stop's own type logged) | KILLED rc=1 | KILLED rc=1 | the command absent test (`error_type`) |
| C5: the catch covers only the pre-download check; the run's own stop escapes | KILLED rc=1 | KILLED rc=1 | the command in-run stop test |

Tally: 10/10 killed, both as a batch against the B file and each aimed at its one test; every
baseline green; the tree clean after each batch.

Hand-back lanes on `29fdf7e6`:
- the B file: 38 passed (34 plus the four command tests);
- the two M-TRACEBACK guards (`test_no_module_logs_an_exceptions_text`,
  `test_the_scan_reads_every_root_and_every_finding_is_registered`): 2 passed;
- the folders covering `ftd_parser.py` (`tests/parsers tests/unit/ingest tests/smoke/ingest
  tests/unit/observability`, `-n 4`): **1516 passed, 32 skipped, 0 failed** (the earlier 1512 plus the
  four command tests).

**Learnings**
- The M-TRACEBACK guard sanctions `failure_fields(<name>)`, not an arbitrary expression. To log a
  chained cause's type, bind the cause to a name in the handler and pass the name.
- A command that catches a run-level stop takes over what the excepthook used to show. Carry the
  cause's type into the record, or the operator loses which refusal it was.

## Owner decisions

1. **D, which side drops the name.** Controller ruling (2026-09-29): rename core's helper to
   `_core_workspace.py` (it is the bare-name importer, so this closes the class for core). Done in a
   core worktree `core-reds`, branch `full-suite-reds`, from core `master` `bcdccb3`. The owner may
   override before the merge.
2. **B's side finding:** should FTD ingest stop on an unprovisioned database, as the gate's
   docstring and `3adba3ef`'s message say, or keep logging per document? **Owner ruled STOP
   (2026-09-29).** Controller ruling on where: check once, before the per-document loop, so nothing
   is written before the stop. Built in fix round 2 (below).

## Future Improvements

- [x] **FTD gate swallow — DONE in fix round 2 (copilot-mro `7365ca95`), owner ruled "stop".** The
  gate now raises `FtdTablesNotProvisioned`, the insert lets exactly that type through, and
  `process_ftd_pdfs` checks once before its per-document loop. The finding as recorded:
  `_ensure_ftd_postgres_tables` re-raises the provisioning `RuntimeError` and
  documents that it "propagates, because no retry of the ingest fixes an unprovisioned database".
  - Its only caller, `_insert_ftd_to_postgres` (`ftd_parser.py:1499-1537`), wraps it in a blanket
    `except Exception` that logs.
  - So an unprovisioned database gives one error line per document and the run carries on. The
    insert is skipped, so no write lands in a missing relation.
  - Its sibling `_insert_to_doc_catalog` re-raises its run-level `TenancyError` for exactly this
    reason (`:1424`).
  - Complete fix, if the owner rules "stop": the gate raises a dedicated provisioning error type and
    the insert lets that type through, as the catalog write does. The B test then gains a
    `raises` assertion.
  - If the ruling is "degrade", only the docstring changes.
- **The crew ingest swallows its gate's stop the same way (found in fix round 2, not in scope).**
  `_ensure_crew_tables` re-raises the provisioning `RuntimeError` and documents that it propagates,
  but its caller (`crew_manual_parser.py`, the `try` around `_ensure_crew_tables() and
  insert_postgres`) lets only `TenancyError` through and logs everything else. So an unprovisioned
  `crew_manual_sections` gives one logged error per manual, exactly the FTD defect before this round.
  The owner's ruling named FTD only, so crew was left alone. The complete fix is the FTD one: a
  dedicated type raised by the gate, let through by the caller, a check before any catalog write
  (the crew catalog write also comes first), and the sibling suite
  `tests/unit/ingest/test_ingest_table_provisioning_gate.py` gaining the run-level stop and the
  degrade boundary. The shared `assert_tables_present` could raise a dedicated
  `RuntimeError` subclass itself, so each gate matches a type instead of converting; that was not
  done here because B's test replaces `postgres_table_definitions` wholesale and the controller
  ruled the type into `ftd_parser.py`.
- **Two more split modules, latent.** `probe/splitcount.py` at the end of whole-tree collection
  lists three real-name modules whose `sys.modules` entry differs from their parent attribute:
  - `copilot_mro.app.services._debug_dump` (C);
  - `copilot_mro.app.services.document_hub.parsers` (split by
    `tests/unit/document_hub/test_document_hub_chunk_spans.py` and
    `…/test_document_hub_docling_pagination.py`);
  - `copilot_mro.app.services.file_readers.pdf_reader` (split by
    `tests/file_readers/pdf/test_pdf_reader_section_spans.py`).

  No red is attributed to the last two today. They are C waiting for a victim. The complete fix is
  the same `evicted_modules` scoping, plus a guard: a conftest `pytest_collection_finish` check that
  fails the session when any `copilot_mro.*` module's `sys.modules` entry and parent attribute
  disagree. That turns this whole class into a named failure at collection instead of a
  whole-tree-only red.
- **Cross-repo helper-name guard.** D and FI-9 are the same defect twice. A guard in copilot-mro's
  `tests/unit/infra/` could fail when a bare-importable module in `scripts/` (or a directory the
  scripts put on the path) shares its basename with one in a sibling repo's `scripts/` that the
  suite loads. That would stop the third occurrence. It was deferred because it needs a decision on
  which sibling directories count.
- **core's variant-hazard tripwire has tripped (found at hand-back, not caused by this batch).**
  `core/tests/unit/infra/test_cross_repo_reads_name_their_checkout.py::test_the_variant_hazard_is_real_in_this_workspace_right_now`
  asserts that api, core and copilot-mro each have a twin checkout, and today no api twin exists.
  - Its docstring says the failure is the prompt for a deliberate decision on whether that file's
    §2 still earns its place.
  - `…falls_back_to_the_bare_name_when_there_is_no_twin` is the same kind of workspace-state test,
    and it is the red the post-merge gate recorded on the primary.
  - Neither is a code defect. Both need an owner or core-lane decision: re-baseline the witness set
    or retire the guard.
- **The FTD command's S3 download is never cleaned up (pre-existing, seen in the re-review).**
  `download_ftd_from_s3` always returns `should_cleanup=False`, so every run from an S3 root leaves
  an `ftd_s3_download_*` directory behind, and its path is never logged. Fix round 3 stopped an
  unprovisioned database from costing a download, but a failed or finished run still leaks one.
  The complete fix: return `should_cleanup=True` for a temp download and clean it in `_main`'s
  `finally`, not only at the end of `process_ftd_pdfs` (a stop or a crash skips that).
- **Whole-tree lane in the standing gates.** None of A–E was ever run whole-tree before 2026-09-29.
  With the reds gone, the gate's stream A becomes a meaningful merge gate. Its counts should be
  recorded per merge, as the workspace test-run rules already require.

## Lessons
