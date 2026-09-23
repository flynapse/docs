# Claims packet — shift-optimizer PRE-PUSH FULL-DIFF review (queue step 16b)

Pre-push colleague-scope review (Fable 5), 2026-09-22. One of the nine ratified per-repo
reviews (review-trust framework, ledger Addendum 228). READ-ONLY on the real tree; every
execution against a `git archive` copy in `~/.claude/scratch/obs-merge/prepush-shift/`.

## Anchor and range

| repo | tree | branch | HEAD | anchor | commits |
|---|---|---|---|---|---|
| shift-optimizer | `/home/aditya/Code/shift-optimizer` | `main` (unpushed) | `ec383cc57547bc6ed66c79c6f26405bd580a6efa` (clean, `git status --porcelain` empty, no stash) | `1ba897e` (batch-2 push 2026-09-16, rebuild-era gated state; verified present and `merge-base --is-ancestor` of HEAD) | **17**, linear (0 merge commits), 2026-09-21 01:11 → 2026-09-22 21:17 |

Range = `1ba897e..ec383cc`, and it begins with the colleague work as described: the
G.100/M-TRACEBACK conversions (`ab33bf0`, `3f1543f`), the withholding-guard P2 closures
(`5f6f942`, `71f636a`), M-SHIFT-RUNERROR (`fe0a07a`..`8bd4d66`), the r1 P2/P3 batches
(`eb7c48a`..`79fe140`), and the R2 witnesses (`ec383cc`). Nothing outside that description
is in the range.

## Commit inventory and index reconciliation

| SHA | Subject (abbrev) | Indexed by |
|---|---|---|
| `ab33bf0` | spans withhold message, export class (G.100) | SO-R0 rows SO0-01..03 (claims-satellites-rounds.md) |
| `3f1543f` | failure logs: class+frames, never message (M-TRACEBACK) | SO0-04 |
| `5f6f942` | withholding guards' alias/door gaps (P2-1..P2-4) | SO0-08..SO0-11 (implementer-proved only) |
| `71f636a` | not_visible → error.type; descriptions refused | SO0-03/SO0-19 (implementer-proved only) |
| `fe0a07a` | run error door `run_error_text` (M-SHIFT-RUNERROR) | r1 SO-01/SO-02 |
| `ed403b9` | SolverInputError kept | r1 SO-03 |
| `1435728` | duration-query + upload exact-type 400s | r1 SO-05/SO-06 |
| `8bd4d66` | raise-site guard | r1 SO-09..SO-15 |
| `eb7c48a` | P3-1 ceilings (SO-16) | r2 SR2-05 |
| `2a8e3de` | P3-2 csv.Error → fixed 400 (SO-17) | r2 SR2-06 |
| `0b4de00` | P3-3 declared gaps true+pinned (SO-14) | r2 (range table) |
| `8792ffc` | fail-closed reader redesign (SO-11..13) | r2 SR2-01/SR2-02 |
| `b30fabc` | response-door census (SO-15) | r2 SR2-03 |
| `163bf09` | witness isolation (masked trio) | r2 SR2-04 |
| `08970d2` | CPU-seconds budget | r2 SR2-07 |
| `79fe140` | docs tick (47/47, lanes green) | r2 SR2-11 |
| `ec383cc` | R2-1/R2-2 witnesses + R2-3 coupling comment | **UNREVIEWED** — first-review rigour here (step-15 landing note only: lanes 139 / 127) |

## Execution evidence (all on the review's own `git archive` copy of `ec383cc`; real tree untouched)

Copy: `~/.claude/scratch/obs-merge/prepush-shift/ws-ec383cc/shift-optimizer`, six siblings
symlinked beside it. Provenance (probed before any run): `shift_optimizer.__file__` inside the
copy; **`utils.__file__` = `/home/aditya/Code/utils/utils/__init__.py` — the api venv's `.pth`
resolves `utils` to the PRE-MERGE sibling, the recorded, expected condition for every shift lane
(r0, r1, r2, implementer); recorded as-run, not "fixed"**; `flynapse_otel` = the sibling
checkout. Every pytest through `pytest-slot.sh`; `ALLOW_TESTS_AGAINST_PROTECTED_DB` never set;
the not-db lanes were redirected by the repo's own guard to `shift_optimizer_test` (warning
quoted in `lane3_notdb.log`); the db lane ran with `ENV_FILE`+`POSTGRES_DB=shift_optimizer_test`,
SERIAL.

**Lanes (recomputed, not quoted):**

| lane | claimed (step-15 note / r2) | this review | exit |
|---|---|---|---|
| raise-sites + run-error writers | 139 passed | **139 passed** (`lane1_sites_writers.log`) | 0 |
| raise-sites + door census | 127 passed | **127 passed** (`lane2_sites_census.log`) | 0 |
| full `-m "not db"` `-n 2` | 1137 at `79fe140` + 2 ec383cc witnesses | **1139 passed** (`lane3_notdb.log`) | 0 |
| db, SERIAL | 150 passed / 1 skip | **150 passed / 1 skipped** — the same pinned skip verbatim (`tests/db/persistence/test_seed.py:214`, "optimizer_schedules already populated (8 rows)"; `lane4_db.log`) | 0 |

**Mutation re-execution (`mutant.sh`, green baseline enforced, cold cache, file restored; log
`mutants_prepush.log`, per-mutant pytest logs `mut/out/`).** The r2 review's own preserved
mutation texts reused byte-for-byte for NEW1/NEW2/R08/H:

| mutant | provenance | at `79fe140` (r2, banked) | at `ec383cc` (this review) | died on (from the pytest log) |
|---|---|---|---|---|
| NEW1 splat args bind no parameter (reader `_arguments_for` Starred) | r2 NEW-1 | SURVIVED aimed + full lane | **KILLED rc=1** | EXACTLY `test_the_reader_refuses_every_leaking_shape[an exception reached through a splat call]` (1 failed / 126 passed) — the R2-1 witness, no collateral |
| NEW2 kept-named parameter not a rebinding (reader `_rebinding` ast.arg) | r2 NEW-2 | SURVIVED aimed + full lane | **KILLED rc=1** | EXACTLY `[a parameter named a kept type]` (1 failed / 126 passed) — the R2-2 witness, no collateral |
| R08 methods not resolved by name | banked (impl 47/47; r2 re-kill) | KILLED | **KILLED rc=1** | EXACTLY CLEAN `[a method called with the run's own ids]` — the `163bf09` witness |
| H `detail=str(exc)` wrapped into export.py | banked (r1 P2-4 mutant; r2 re-kill) | KILLED | **KILLED rc=1** | EXACTLY `test_every_door_that_can_carry_caught_text_is_named` |
| NEW3 kw-splat binds no parameter (reviewer-designed, the `**kw` twin R2-1 left optional) | this review | — | **SURVIVED aimed rc=0 (127 passed) AND SURVIVED the FULL not-db lane (1139 passed, rc=0)** → finding PP-01 | pristine-reader probe (`probe/probe_kw_splat.py`): the committed reader CATCHES the kw-splat shape (`['leak']`) — witness gap, not reader gap |

The NEW1/NEW2 SURVIVED→KILLED flip, with each kill attributed to exactly the witness `ec383cc`
adds, is the red-before proof for the unreviewed commit: the witnesses are load-bearing.

**Red-before proofs of the behavioral fix commits** (the commit's new test file overlaid onto a
`git archive` of its PARENT tree, run there):

- `2a8e3de`'s upload test at parent `eb7c48a`: exit 1, red EXACTLY on the 3 new
  `test_what_the_csv_module_refuses_gets_the_fixed_sentence[...]` cases (field over limit,
  header over limit, line break in unquoted field); 10 passed (`redbefore_csv_at_eb7c48a.log`).
- `eb7c48a`'s tests at parent `8bd4d66`: exit 1, red EXACTLY on the 8 new ceiling/extreme cases
  (`cost factor above the ceiling`, 3 × extreme formulas, cohort minimum past ceiling, 3 ×
  constraint-that-cannot-bind); 44 passed (`redbefore_extremes_at_8bd4d66.log`).

**Read-only attestation.** No real-tree edit, commit, checkout, stash or push. Real tree
re-verified at the end: HEAD `ec383cc57547...` unmoved, `git status --porcelain` empty, no
stash. The scratch copy was diffed recursively against a fresh `git archive` extraction after
all runs: byte-identical (every pytest ran `-p no:cacheprovider`; `mutant.sh` restored and
verified every mutated file).

## Diff review (every commit, actual diff)

- **Deletion scan of the whole range** (`git show <sha> -- tests/` filtered to removed
  assertions/tests, all 17 commits): every deletion is a documented replacement or
  strengthening — the span-event assertions removed at `ab33bf0`/`71f636a` return as two-seat
  (exported + live) assertions incl. `_assert_no_sentinel_anywhere` over BOTH seats;
  `pytest.raises(ValueError)` → domain types at `ed403b9` (with the one intentionally-plain
  `ValueError` now pinned `type(...) is ValueError` and the reason in a comment);
  `test_the_user_facing_set_is_exactly_the_two_domain_types` → `..._three_...`; the old
  shape-list detector deleted wholesale at `8792ffc` for the fail-closed reader; wall-clock
  `elapsed < 15.0` → CPU seconds at `08970d2`. **No commit weakens a guard silently.**
- **Production diffs read in full**: `run_telemetry._span` (both keywords literal `False`,
  `error.type` + bare ERROR, re-raise; `Exception` not `BaseException`), `RunSignals.failed`
  takes the class NAME, `not_visible` → `error.type="run_not_visible"` + bare status;
  M-TRACEBACK's five failure lines (`**failure_fields(exc)`, constant templates, the `"{}"`
  loguru re-format fix in postgres.py); `run_error_text` exact-type door + `USER_FACING_RUN_ERRORS`;
  `SolverInputError` in an import-free leaf (lazy-ortools invariant intact); the two 400 doors
  with exact-type checks and fixed sentences; the `eb7c48a` ceilings (int64 headroom
  1.68e10 × 1000 × 1e5 = 1.68e18 < 2^63; NaN refused upstream by `_eval`'s chained-comparison
  `not`; `max(requirement)` safe — length == horizon > 0 checked first; day-cap clamp
  `min(cap, len(block_flags))` preserves the feasible set; `_parse_int` + `OverflowError`);
  `2a8e3de`'s `csv.Error` → plain ValueError with `_read_flights` a real list-returning
  function (no generator hazard; the only "yield" hit in the module is docstring prose).
- **Guard/test files read in full at HEAD**: `_kept_text_reader.py` (1737 lines),
  `_kept_errors.py`, `test_kept_error_raise_sites.py` (82 LEAKING / 18 CLEAN / 4 DECLARED_GAPS
  + 6 tree tests), `test_response_door_census.py` (2 DOORS, 11 REFUSED, 5 PASSED),
  `test_run_error_column_writers.py`, `test_api_run_error_withholding.py`,
  `test_duration_query_error_withholding.py`, `test_api_schedule_upload_error_withholding.py`,
  `test_no_exception_text_in_logs.py`, `test_no_exception_text_on_spans.py`,
  `test_failure_logs_withhold_exception_text.py`, `test_run_spans_withhold_exception_text.py`,
  `test_run_span_shape.py` edits, `_sentinel_exceptions.py`, the engine test edits, and
  `docs/plans/kept-error-text-guards.md`.
- **Key absence checks at HEAD** (grep + the re-run suites): the only `str(exc)`/`{exc}` sites
  in production are the four censused doors/exemptions (`formula.py:290` EXEMPT,
  `run_executor.py:199` the door's kept branch, `schedules.py:318`, `duration_query.py:45`);
  the only `record_exception`/`set_status_on_exception` tokens are `_span`'s literal-`False`
  pair; zero `logger.exception` anywhere. The full detector/witness battery re-ran green
  inside the 1139-test lane on this review's copy.

## Findings

### PP-01 (P3) — The reader's keyword-splat branch is implemented but unwitnessed

- **Where.** `tests/_kept_text_reader.py:832-835` (`_arguments_for`, `keyword.arg is None` →
  every parameter). The positional-splat branch got its witness at `ec383cc` (R2-1); r2's
  packet left "its `**kw` twin" optional and it was not added.
- **Probe.** Reviewer mutant NEW3 (the branch binds nothing): SURVIVED the aimed guards run
  (127 passed, rc 0) AND the FULL `-m "not db"` lane (1139 passed, rc 0). The pristine
  committed reader CATCHES the shape (`refuse(**parts)` with a tainted dict → `['leak']`,
  probe log) — a witness-coverage gap, not a behavior defect. No live-tree exposure (no
  kw-splat call into a taint-relevant callee in the swept tree).
- **Fix.** One LEAKING witness: `refuse(**parts)` with tainted `parts`, expected `{"leak"}`.
  One dict entry, no reader change. Same class and severity as r2's R2-1/R2-2, which the
  push gate does not block on.

### PP-02 (P3, process) — The deferred kw-twin is recorded nowhere in the repo

`docs/plans/kept-error-text-guards.md`'s "Future Improvements" section is empty: r2's R2-1/
R2-2/R2-3 were implemented forward at `ec383cc` (the better outcome), but the one item
consciously left undone (the `**kw` witness) lives only in the workspace packet. A one-line
entry in the repo plan would keep the repo's own record complete.

### What I tried to break and could not

- **`ec383cc` itself (first-review rigour).** The two witnesses isolate their rules: under
  NEW1 exactly the splat witness fails (1 failed / 126 passed), under NEW2 exactly the
  kept-named-parameter witness — no second refusal masks either (the r2 misread's lesson holds
  for the new witnesses too). On the unmutated reader both report exactly their expected kinds
  (lanes green). The R2-3 comments sit on both coupled sites (`_in_door_set`,
  `user_facing_names`) and say the same thing; no code change rode along in the commit.
- **Guard-weakening across the range.** The full-range deletion scan (above): nothing dropped
  without a stronger replacement; registers only ever gained members (kept set 2 → 3 types,
  census 38 → 42, DECLARED_GAPS 16 → 4 with each closure moved into LEAKING).
- **The lanes' provenance.** `rootdir` and `conftest` paths in every log point inside the
  review's copy; the test-DB redirect warning fired (protected DB untouched); the db lane ran
  serial with `POSTGRES_DB=shift_optimizer_test`.

## What I did not test

- Anything live (no stack, no gateway mount; Postgres only via the repo's own db lane against
  `shift_optimizer_test`).
- The other 43 banked mutants (r1's A/E/E2b/B1/B2/C + reader R01–R07, R09–R40 minus the
  sampled ones): the 4-mutant re-execution reproduced 4/4 with kill-attribution matching the
  named witnesses, and the banked logs are format- and timing-consistent.
- copilot-mro / dashboard consumers (SO-19/SO-20) and legacy-row DML (SO-18): owner-owed,
  unchanged in this range, tracked in the r1 packet and Addendum 90.

## Claims table

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PP-A | range `1ba897e..ec383cc` | Anchor correct; 17 linear commits, all colleague-merge work, nothing unaccounted | `merge-base --is-ancestor`; commit list vs SO-R0/r1/r2 indexes; 0 merges; dates 2026-09-21+ | **SETTLED** |
| PP-B | whole range, tests/ | No commit weakens a guard silently | full-range deletion scan; every deletion mapped to its strengthening | **SETTLED** |
| PP-C | `run_telemetry.py` / `run_executor.py` / `postgres.py` | G.100 + M-TRACEBACK conversions hold at HEAD (class+frames only; two-seat tests) | production diffs read; grep absence checks; telemetry suites green in the 1139 lane on the copy | **SETTLED** |
| PP-D | `run_error_text` + the two 400 doors | M-SHIFT-RUNERROR: exact-type doors, fixed sentences for surprises | diffs read; api withholding suites green on the copy; H re-KILLED (door census); red-before proofs at the parent trees (3 + 8 tests red exactly) | **SETTLED** |
| PP-E | `tests/_kept_text_reader.py` + both guard registers | The fail-closed reader + censuses hold; lanes reproduce (139/127/1139/150+1skip, all exit 0) | all four lanes recomputed on the copy; R08 re-KILLED on its named CLEAN witness | **SETTLED** |
| PP-F | `ec383cc` witnesses | R2-1/R2-2 witnesses are load-bearing and isolated; R2-3 comment on both sides | NEW1/NEW2 SURVIVED→KILLED flip, each dying on exactly its witness | **SETTLED** |
| PP-G | reader `_arguments_for:832-835` | kw-splat branch unwitnessed (PP-01) | NEW3 survived aimed + FULL lane; pristine probe `['leak']` | **OPEN — P3** |
| PP-H | repo plan Future Improvements | deferred kw-twin unrecorded in-repo (PP-02) | plan read at HEAD | **OPEN — P3 (process)** |

**Totals:** 8 claims — 6 SETTLED, 2 OPEN (both P3).

## Verdict

**PUSH-CLEAN: 0 P0 · 0 P1 · 0 P2 · 2 P3.** The push gate (P0/P1 = FIX-FIRST) is clear.
Every re-executed number matched or exceeded its claim; the one measured gap (PP-01) is a
mutation-corpus witness gap over behavior the reader demonstrably has, and r2 had already
scoped it as optional.

Durable notes and logs: `~/.claude/scratch/obs-merge/prepush-shift/` (lane logs, `mutants_prepush.log`,
`mut/` specs + per-mutant pytest logs, `probe/`, red-before logs, `NOTES.md`).
