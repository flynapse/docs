# Claims packet — shift-optimizer r2 CLOSING REVIEW (the P2 batch: fail-closed reader redesign)

Independent closing review (Fable 5), 2026-09-22. It covers review r1's fix batch on
shift-optimizer: the SO-11/12/13 **fail-closed kept-error reader redesign**, the SO-15
route-response door census, the P3 fixes (SO-14/16/17), the load-robust timing test, the
witness-isolation follow-up (`163bf09`) and the closing docs tick. This closing round exists
because the fix work included a redesign; the redesign was this review's center of gravity. The
verdict is issued from the ACTUAL DIFF at pinned SHAs; the r1 packet, the implementer's scratch
and the ledger were used as indexes only, and every number below was measured by this review.

**Read-only attestation.** No real tree was edited, committed, checked out, stashed or pushed.
Every test and mutation ran against a `git archive` copy of `79fe140` in private scratch
(`~/.claude/scratch/obs-merge/shift-r2/ws-79fe140/shift-optimizer`). After all runs the copy was
diffed recursively against a fresh archive extraction in BOTH directions: byte-identical, the
only addition being pytest's own `.pytest_cache` (the lane runs did not pass
`-p no:cacheprovider`; the mutation runs did). Real tree re-verified at the end: HEAD
`79fe1402de99d1e43076bc644bce53c6462115ff`, branch `main`, `git status --porcelain` empty,
no stash.

| repo | tree | branch | range | commits |
|---|---|---|---|---|
| shift-optimizer | `/home/aditya/Code/shift-optimizer` (clean at `79fe140`, verified at start and end) | `main` (unpushed) | `8bd4d66..79fe140` | 8, listed below |

**Range reconciliation — CLEAN.** The 8 commits are each accounted for by the SDD ledger
(launch line `progress.md:8098`, agents-table row `:8128`, Addendum 224, Addendum 234) and by
the repo plan `docs/plans/kept-error-text-guards.md`. Every commit's diff was read end-to-end.

| SHA | What | Accounted by |
|---|---|---|
| `eb7c48a` | P3-1 (SO-16): `MAX_REQUIREMENT`/`MAX_COST_FACTOR`/`MAX_RULE_STAFFING` ceilings, day-cap clamp, `_parse_int` OverflowError; census 38 → 42 | r1 fix work |
| `2a8e3de` | P3-2 (SO-17): `csv.Error` → plain ValueError → the fixed 400 sentence | r1 fix work |
| `0b4de00` | P3-3 (SO-14): declared-gap list made true + pinned-as-missed | r1 fix work |
| `8792ffc` | SO-11/12/13: the fail-closed reader (`tests/_kept_text_reader.py`, 1733 lines) + `tests/_kept_errors.py` + the raise-site guard rebuilt on it | the redesign |
| `b30fabc` | SO-15: the response-door census | door census |
| `163bf09` | Witness isolation for the three masked mutants | witness commit |
| `08970d2` | Weekly-solve budget in CPU seconds (`time.process_time`) | load-robust timing test |
| `79fe140` | Docs only: plan item-4 tick + mutation/lane implementation note | final tick |

Nothing in the range is unaccounted for.

**How the lanes were run.** From the copy's root, api venv interpreter, every run through
`pytest-slot.sh`:

```
DEBUG=false PYTHONPATH=<copy> [ENV_FILE=/home/aditya/Code/api/.env POSTGRES_DB=shift_optimizer_test]
/home/aditya/Code/pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest ...
```

- Seat proof (quoted once, held for every run): `rootdir:
  /home/aditya/.claude/scratch/obs-merge/shift-r2/ws-79fe140/shift-optimizer`;
  `shift_optimizer.__file__` inside that copy; `utils.__file__` =
  `/home/aditya/Code/utils/utils/__init__.py` — the api venv's `.pth` resolves `utils` to the
  PRE-MERGE sibling. That is how every shift lane was run and claimed (r1, the implementer, and
  this review); recorded as-run, not "fixed".
- `ALLOW_TESTS_AGAINST_PROTECTED_DB` was never set. Siblings (`core`, `utils`, `api`,
  `copilot-mro`, `dashboard`, `flynapse-otel`) symlinked beside the copy so `tests/_root.py`
  anchors as in the workspace.
- The db-lane trap reconfirmed the cheap way: the lane was run WITH
  `ENV_FILE`+`POSTGRES_DB`+`PYTHONPATH` and passed; the r1 packet had already measured the
  collection-time refusal without `ENV_FILE`.

**Lane totals vs claimed** (claims: Addendum 234, the plan's closing note, the implementer's
`lane_notdb_head.log`/`lane_db_head.log`).

| lane | claimed | this review (own copy) | match |
|---|---|---|---|
| `-m "not db"` `-n 2` | 1137 passed, exit 0 | **1137 passed, exit 0** (15.8 s; `shift-r2/lane_notdb.log`) | YES |
| db, SERIAL | 150 passed / 1 skip, exit 0 | **150 passed / 1 skipped, exit 0** (101.7 s; `shift-r2/lane_db.log`) | YES |

The skip was pinned with a dedicated `-rs` run of the seed file (db budget run 2 of 2):
`tests/db/persistence/test_seed.py:214` — "optimizer_schedules already populated (8 rows) —
verified seed_if_empty() is an idempotent no-op" — the claimed skip verbatim.

**Mutation re-execution (measured; log `~/.claude/scratch/obs-merge/shift-r2/mutants_r2.log`,
per-mutant pytest logs in `shift-r2/mut/out/`).** All runs with `/home/aditya/Code/mutant.sh`
against this review's own copy — the implementer's HEAD batch ran on the real tree; this
review's may not and did not. Green baseline first in every case (`mutant.sh` refuses a red
baseline; baseline once per distinct test command); kill = pytest exit 1 only. Sample chosen
adversarially: the three formerly masked mutants, two DECLARED_GAPS-shrinking branches (shapes
that moved from declared-gap to refused in the redesign), and the door-census mutant.

| mutant | why chosen | banked | this review | died on |
|---|---|---|---|---|
| R08 methods not resolved by name | required; masked trio | KILLED | **KILLED rc=1** | CLEAN "a method called with the run's own ids" — the `163bf09` witness |
| R15 framework hook not an unknown caller | required; masked trio | KILLED | **KILLED rc=1** | LEAKING "a framework hook's parameters" |
| R31 dunders not unknown callers | required; masked trio | KILLED | **KILLED rc=1** | LEAKING "a dunder the language calls" |
| R07 chain attrs on any object not a source | DECLARED_GAPS-shrinking (the old `__context__` gap; SO-13 / r1 mutant C's rule) | KILLED | **KILLED rc=1** | the chain/notes/sys.last_* witness family (4 rows) |
| R10 mutation not propagated over aliases | DECLARED_GAPS-shrinking (the old "mutation through an alias" gap) | KILLED | **KILLED rc=1** | both mutation-alias witnesses |
| H `detail=str(exc)` in export (real tree) | the SO-15 census's reason to exist | KILLED | **KILLED rc=1** | `test_every_door_that_can_carry_caught_text_is_named` |
| NEW-1 splat args bind no parameter (reviewer-designed) | fail-closed attack | — | **SURVIVED aimed rc=0, and SURVIVED the FULL not-db lane (1137 passed)** → R2-1 |
| NEW-2 kept-named parameter not a rebinding (reviewer-designed) | fail-closed attack | — | **SURVIVED aimed rc=0, and SURVIVED the FULL not-db lane (1137 passed)** → R2-2 |

Each of the six sampled kills died on the exact witness the redesign names for it — the r1
misread's lesson ("a witness refused for two reasons proves neither") holds measurably at HEAD.

**Both survivors were pre-triaged with a probe against the UNMUTATED committed reader**
(`shift-r2/probe/probe_new_shapes.py`, run on a pristine extraction): the committed reader
CATCHES all three probed shapes — positional splat → `['leak']`, keyword splat → `['leak']`,
kept-named parameter → `['rebinding']`. So both survivals are witness-coverage gaps in the
mutation corpus, not behavior defects.

**Verdict: MERGE-CLEAN.** 0 P0 · 0 P1 · 0 P2 · 3 P3. The redesign holds: the fail-closed
property survived this review's independent attack; the two unwitnessed reader branches are
test-coverage gaps only; every independently re-measured number matches its claim.

---

## Findings, ranked

### No P0, no P1, no P2

The reader (1733 lines) was read end-to-end and attacked. Its over-approximation is genuine:
names resolve by Python's scope rules, imports link modules, unresolvable bindings are tainted
or findings, and the two-universe design (`CLEAN`/`ACTUAL`) is what lets one witness exercise
one rule — the mechanism behind the `163bf09` fix, traced by hand and confirmed by
re-execution. The live-tree registers match the tree: census 42 constructions over 7
(module, type) pairs; two exemptions; two named doors; every unregistered finding kind empty.
The witness corpus at HEAD: 80 LEAKING + 18 CLEAN + 4 DECLARED_GAPS (raise-site guard) and
11 REFUSED + 5 PASSED (door census).

### R2-1 (P3) — The reader's splat-binding branch has no mutant-killing witness

- **Where.** `tests/_kept_text_reader.py:823-826` (`_arguments_for`: a `Starred` argument
  reaches every parameter).
- **Probe.** Mutant NEW-1 (the Starred branch binds nothing): SURVIVED the aimed run over both
  guard files AND the full `-m "not db"` lane (1137 passed, rc 0). The unmutated reader catches
  the shape (`refuse(*parts)` with tainted `parts` → `['leak']`), so the branch works — it is
  just unproven.
- **Why it matters.** The plan's claim "one mutant per fail-closed branch of the reader
  (R01–R40)" is slightly overstated: a regression in this branch would go silently green, which
  is the exact failure mode the redesign exists to prevent. No live-tree exposure today (no
  splat call into a taint-relevant callee in the swept tree).
- **Fix.** One LEAKING witness: a helper reached only via `refuse(*parts)` with tainted
  `parts`, expected `{"leak"}` (and optionally its `**kw` twin). No reader change.

### R2-2 (P3) — A parameter named a kept type is an unwitnessed rebinding

- **Where.** `tests/_kept_text_reader.py:1630-1631` (`_rebinding`, the `ast.arg` branch).
- **Probe.** Mutant NEW-2 (drop the branch): SURVIVED the aimed run AND the full not-db lane
  (1137 passed, rc 0). The unmutated reader flags `def f(RunExecutionError): ...` as
  `['rebinding']`, so again: implemented, unproven.
- **Why it matters.** Same class of gap as R2-1. A shadowing parameter smuggles an arbitrary
  class under a kept name inside that scope; with the branch gone, silently.
- **Fix.** One LEAKING witness with a kept-named parameter, expected `{"rebinding"}`.

### R2-3 (P3) — The door-set sanction's module-level requirement is load-bearing in two places at once

- **Where.** `tests/_kept_text_reader.py:1700-1729` (`_in_door_set` requires the literal be
  bound at module level) and `tests/_kept_errors.py` (`user_facing_names` walks only
  `tree.body`, so only a module-level `USER_FACING_RUN_ERRORS` enters the kept-set derivation).
- **What was checked.** A function-local `USER_FACING_RUN_ERRORS = frozenset({...})` fails
  closed: `_in_door_set` refuses it (a `reference` finding) and the derivation ignores it —
  verified by reading both sides. No defect. Recorded so a future edit does not weaken one side
  assuming the other covers it; a one-line comment tying the two module-level requirements
  together would make the coupling explicit.

---

## What I tried to break and could not

- **The misread lesson (the brief's recorded prior misread).** The committed witnesses at HEAD
  isolate their rules: "a dunder the language calls" carries `guard.__exit__(None, None, None)`
  and "a framework hook's parameters" carries `handler.emit(current_record)`, so the
  never-called rule cannot refuse them, and the new CLEAN witness "a method called with the
  run's own ids" fails unless `obj.m()` resolves by name. Traced by hand through
  `_seed`/`_decorated`/`callees`, then proven by re-execution: R08 died on the CLEAN method
  witness, R15 and R31 each on their own LEAKING witness.
- **The fail-closed property, adversarially.** Attack shapes beyond the corpus, hand-traced
  and/or probed: a splat AT a kept construction (`RunExecutionError(*parts)`) is caught (taint
  recurses into `Starred`); `type(x)` single-arg is simultaneously a clean class READ and an
  unnameable class VALUE, so calling it is refused; an unnamed bare `except:` cannot bind, and
  `sys.exc_info()` inside it hits the source vocabulary; a function's own name-symbol is
  tainted when it returns taint (`_apply_function`), so plain-name calls of text-returning
  helpers taint without the `ret_clean` attribute path. The only two under-proofs found became
  NEW-1/NEW-2 — witness coverage, not behavior.
- **The eb7c48a ceilings.** NaN is refused by `_eval` (NaN comparisons are False, so the `not`
  fires); the int64 headroom arithmetic (1.68e10 × 1000 × 100000 = 1.68e18 < 2^63) is pinned
  live by `TestCeilingsFitTheModel` (elastic AND hard model at every ceiling at once); the
  day-cap clamp `min(cap, len(block_flags))` preserves the feasible set (each flag is 0/1, so
  the sum can never exceed the length).
- **The 2a8e3de generator hazard.** `_read_flights` is a real list-returning function at HEAD
  (no `yield`), so the `except csv.Error` around its call fires; `reader.fieldnames` — itself a
  `csv.Error` source for an over-limit header — is read inside the try. The test drives real
  refused bytes and asserts the library's wording is absent from the response.
- **The timing change (`08970d2`).** `process_time` counts every thread of the process; all
  three regression classes the guard exists for (cap dropped/ignored, more search workers, a
  model that blows up) spend more CPU, so none escapes the CPU-seconds budget.

## What I did not test

- Anything live: no stack, no docker beyond localhost:5432 for the db lane.
- The remaining 41 banked mutants (A, E, E2b, B1, B2, C, R01–R06, R09, R11–R14, R16–R30,
  R32–R40): not re-run. The adversarial sample of 6 reproduced 6/6 with kill-attribution
  matching the named witnesses; the banked log (`shift-impl-p2/mutants_head_08970d2.log`,
  47 lines, all `KILLED rc=1`, 0 SURVIVED/BROKE/NO-TESTS) is consistent in format and timing
  with the re-runs.
- copilot-mro / dashboard consumers (SO-19 / SO-20): out of this batch's scope, unchanged in
  the range.

---

## Claims table

Scales as in r1: Severity (this reviewer's), Tier (§2.3a: 0 = settled by a guard seen to fail,
1 = consequential but reversible, 2 = irreversible/estate-shaping), Chunk F1 = exception-text
guarding, F3 = residual UX/process.

| # | Repo | File:line | Decision taken | Evidence | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|
| SR2-01 | shift-optimizer | `tests/_kept_text_reader.py` (whole) | The fail-closed reader replaces the shape-list detector: an unresolvable binding is tainted or a finding | Read end-to-end; live tree green with unregistered kinds empty; independent probe + attack | **yes**: R07/R08/R10/R15/R31 re-killed here; 47/47 banked | — | 0 | F1 | **SETTLED**, scoped by R2-1/R2-2 (witness gaps, behavior verified by probe) |
| SR2-02 | shift-optimizer | `tests/unit/contracts/test_kept_error_raise_sites.py` | Registers by equality: census 42 over 7 pairs, 2 exemptions; every other kind absent | Corpus counted (80/18/4); lane green on copy | **yes** (sampled; r1's A/E/E2b/B1/B2/C banked) | — | 0 | F1 | **SETTLED** |
| SR2-03 | shift-optimizer | `tests/unit/contracts/test_response_door_census.py` | Door census: 2 named doors, 11 refused + 5 passed witnesses | H re-killed here, dying on the census equality | **yes**: H | — | 0 | F1 | **SETTLED** |
| SR2-04 | shift-optimizer | `163bf09` witnesses | Each witness exercises only its own rule | R08/R15/R31 die at HEAD, each on its named witness (kill-attribution from this review's pytest logs) | **yes** | — | 0 | F1 | **SETTLED** — the r1 misread's lesson holds |
| SR2-05 | shift-optimizer | `solver.py` / `requirement.py` / `run_executor.py` (`eb7c48a`) | User-authorable extremes refused with kept types naming field+bound; unbinding day cap clamped | Diff read; ceiling arithmetic checked; end-to-end tests read; both lanes green | in-lane behavioral tests (SO-16 was P3; not separately mutated) | — | 1 | F1 | **SETTLED by lanes** |
| SR2-06 | shift-optimizer | `schedule_processing.py` (`2a8e3de`) | `csv.Error` → plain ValueError → fixed sentence | Diff read; no generator hazard; real-bytes tests | in-lane | — | 1 | F1 | **SETTLED by lanes** |
| SR2-07 | shift-optimizer | `test_solver.py` (`08970d2`) | CPU-seconds budget replaces wall time | Regression classes all spend CPU; measured headroom in plan | n/a | — | 1 | F3 | **SETTLED** |
| SR2-08 | shift-optimizer | reader `_arguments_for` Starred (`:823-826`) | Splat binding implemented but unwitnessed | NEW-1 survived aimed + FULL lane; probe shows unmutated reader catches the shape | **yes — the gap is real and bounded** | 3 (P3) | 1 | F1 | **OPEN** → Future Improvements |
| SR2-09 | shift-optimizer | reader `_rebinding` ast.arg (`:1630-1631`) | Kept-named-parameter rebinding implemented but unwitnessed | NEW-2 survived aimed + FULL lane; probe shows unmutated reader catches the shape | **yes — the gap is real and bounded** | 3 (P3) | 1 | F1 | **OPEN** → Future Improvements |
| SR2-10 | shift-optimizer | `_in_door_set` / `user_facing_names` | Function-local door-set literal fails closed on both sides | Both sides read; coupling noted | n/a | 3 (P3) | 1 | F1 | **SETTLED** (note recorded) |
| SR2-11 | shift-optimizer | plan `docs/plans/kept-error-text-guards.md` + Add. 234 | The batch's claims: 47/47 at HEAD, lanes 1137 + 150/1skip | Both lane totals independently reproduced on this review's copy; skip pinned verbatim; 6-mutant adversarial sample reproduced 6/6 with matching kill-attribution | on sample | — | 1 | F3 | **SETTLED on sample** |

**Totals:** 11 claims — 9 SETTLED (one on sample), 2 OPEN (both P3 witness gaps).

**Verdict: MERGE-CLEAN — 0 P0 / 0 P1 / 0 P2 / 3 P3.**

---

## Future Improvements

1. **R2-1 — a splat witness.** Add to `LEAKING`: a helper whose parameter is reached only via
   `refuse(*parts)` with tainted `parts`, expected `{"leak"}` (optionally its `**kw` twin), so
   `_arguments_for`'s Starred branch has the mutant-killing witness the other branches have.
   One witness, no reader change.
2. **R2-2 — a kept-named-parameter witness.** Add to `LEAKING`:
   `def f(RunExecutionError): ...`, expected `{"rebinding"}`. Same shape of gap, same one-line
   fix.
3. **R2-3 — a comment tying `_in_door_set`'s module-level requirement to
   `user_facing_names`'s module-level walk**, so neither side is weakened alone.

## Lessons

- "One mutant per branch" is checked by designing mutants FOR the branches, not by recounting
  the log: the two unwitnessed branches were found by reading the reader for branches and the
  corpus for their witnesses, then proven missed by mutation (aimed + full lane), with a
  pristine-reader probe separating "witness gap" from "reader gap" before grading.
- A first packet draft must never carry predicted proof rows; this one briefly did and was
  reconciled to the measured log before finalising. Write PENDING, run, then fill.
