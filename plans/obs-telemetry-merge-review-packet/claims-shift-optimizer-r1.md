# Claims packet — shift-optimizer M-SHIFT-RUNERROR and follow-ups (review r1)

Independent adversarial review (Opus), 2026-09-21. It covers the owner ruling **M-SHIFT-RUNERROR** (plan
§4a-bis) and its three follow-ups, filed under G.100. The review was read-only: no real tree was edited,
committed or checked out. Every mutation ran against a `git archive` copy in private scratch, and each copy
was restored and md5-checked against the `git show 8bd4d66:<path>` blob afterwards. All restores matched.

| repo | tree | branch | range | commits |
|---|---|---|---|---|
| shift-optimizer | `/home/aditya/Code/shift-optimizer` (clean at `8bd4d66`, no stash) | `main` (unpushed) | `fe0a07a~1..8bd4d66` | `fe0a07a` door · `ed403b9` SolverInputError · `1435728` 400 doors · `8bd4d66` raise-site guard |

**How it was run.** Each commit was extracted with `git archive` to
`scratchpad/shift-review-r1/ws-<sha>/shift-optimizer`. Sibling repos (`core`, `utils`, `api`, `copilot-mro`,
`dashboard`, `flynapse-otel`) were symlinked beside each copy, so that `tests/_root.py` anchors the same way it
does in the workspace. Each lane was run from the copy's root:

```
POSTGRES_DB=shift_optimizer_test DEBUG=false PYTHONPATH=<copy> ENV_FILE=/home/aditya/Code/api/.env \
PYTHONPYCACHEPREFIX=<fresh per run> \
/home/aditya/Code/api/.venv/bin/python -m pytest tests/<lane> -p no:randomly -rfE
```

- The exit status was taken from `PIPESTATUS[0]`, and `ALLOW_TESTS_AGAINST_PROTECTED_DB` was never set.
- `rootdir` was `…/ws-<sha>/shift-optimizer` every time. `shift_optimizer.__file__` resolved inside that
  copy, and `utils.__file__` resolved to `/home/aditya/Code/utils/utils/__init__.py` (the api venv's `.pth`).
- No RLS heal fired.
- A first api/db pass without `ENV_FILE` exited 2 at collection: the conftest role-provenance guard refused it,
  correctly. The api/db numbers below come from the rerun with `ENV_FILE` set.

| commit | unit | api | smoke | db | parity |
|---|---|---|---|---|---|
| `fe0a07a~1` | 825 | 130 | 7 | 60 + 1 skip | 18 |
| `fe0a07a` | 854 | 167 | 7 | 60 + 1 skip | 18 |
| `ed403b9` | 855 | 174 | 7 | 60 + 1 skip | 18 |
| `1435728` | 855 | 192 | 7 | 60 + 1 skip | 18 |
| `8bd4d66` | 889 | 192 | 7 | 60 + 1 skip | 18 |

Every exit status was 0, so every commit is green at its own HEAD. Every count equals the implementer's recorded
count.

**Scales used below.**
- **Severity** is this reviewer's scale: 0 = a content leak that ships, 1 = guard or lock integrity,
  2 = a coverage gap, 3 = docs or process. `—` means the claim holds and there is no defect.
- **Tier** is §2.3a's scale: 0 = settled by a guard seen to fail when the property is removed, 1 = consequential
  but reversible, 2 = irreversible or estate-shaping.
- **Chunk**: F1 is every row that decides or guards what exception text reaches a client (the whole purpose of
  this range). F3 is residual UX and process. No row is F2, because nothing here is a merge resolution.

**Verdict: MERGE-CLEAN.** There are 0 P0 and 0 P1 findings, 4 P2 and 5 P3. No exception text ships at `8bd4d66`.
The P2s are all in the new raise-site guard, plus one coverage gap. They should be fixed forward, or recorded as
Future Improvements.

---

## Findings, ranked

### No P0, no P1

At `8bd4d66` every kept-type message is built from one of these:

- the user's own input;
- the run's own ids;
- solver status names;
- builtin numeric wording.

`probes/param_flow.py` confirmed that no kept construction receives except-bound text through a parameter
today. The three doors return only what they claim to return.

### P2-1 — An alias of a kept type is invisible to the census, the taint check and the subclass rule

- **Where.** `tests/unit/contracts/test_kept_error_raise_sites.py:154-163` builds `kept_aliases` only from
  `ImportFrom`. `kept_name` (`:172-178`) recognises nothing else.
- **Mutant A**, zero test edits, on `run_executor.py`:
  - `_Refusal = RunExecutionError`;
  - `payroll_estimate` wrapped in `except Exception as exc: raise _Refusal(f"Role {role.id!r}: the payroll
    estimate failed: {exc}")`.
- **Result.**
  - Both structural guards are green (63/63).
  - 931 of 933 unit + jobs_runs api tests are green.
  - The two reds are this review's own leak probe and `test_no_depth_coupled_paths` flagging that probe's
    `parents[1]`. Neither is a guard catching the mutant.
- **End to end**, through the real executor and runs router over the implementer's in-memory harness, the
  stored and returned value was `"Role 'ROLE-E1': the payroll estimate failed:
  SENTINEL-review-db.internal.example:5432"`, and `BODY_HAS_SENTINEL=True`.
- **Other shapes the census can't see** (decoys, 0 constructions seen):
  - a literal `getattr(rx, "RunExecutionError")(...)`;
  - `cls(str(e))` in a classmethod;
  - `type(err)(f"{err}…")`.
- **Docstring mismatch.** The declared gap reads "a getattr whose name is **not** a literal", but literal
  getattr is not handled either.

### P2-2 — The subclass rule can be dodged with an alias, which lets the kept-only handler launder text

- **Where.** `class_bases` (`:313-318`) reads raw base names and ignores the aliases the module has already
  computed.
- **Why it matters.** The guard's docstring (`:23-27`) rests the "a handler that catches only kept types may
  pass its message on" sanction entirely on this rule.
- **Mutant E**, zero edits, on `formula.py`: `_Base = FormulaError; class _LookupFailure(_Base)`, raised with
  `f"could not read {node.id}: {exc}"` in `_compute`.
  - Both guards green; 933 unit + catalog + withholding tests green.
  - `requirement._eval`'s `except FormulaError as exc` (`requirement.py:304`) wraps it into a
    RequirementError, and `run_error_text` stores `"Activity 'A1' rule 'R1': could not read x: could not convert
    string to float: 'SENTINEL-db.internal:5432'"`.
- **Mutant E2b**: the same shape through an import alias (`from …formula import FormulaError as _FE`) in
  `requirement.py`. Guards green.
- **A decoy** built with `type("S", (FormulaError,), {})` is also missed.
- **Why E2 was caught.** The same plant with the handler named `as exc` went red only because that name
  collided with an existing kept-only handler. Per-module taint by name flags it; that is coincidence, not
  design.

### P2-3 — Taint does not follow inside one module

- **Where.** `_bindings` (`:201-237`) propagates through assignments and returns of bare-name calls, and nothing
  else. The kept-only-handler sanction (`_taint`, `:242-245`) reads any attribute of the bound exception.
- **The undeclared bypasses**, each shown by a decoy, a real-tree mutant, or both:
  - An exception passed as an argument to an unannotated helper parameter, e.g. `def _refuse(detail): raise
    SolverInputError(f"…{detail}")` called as `_refuse(exc)`. Mutant B on `solver.py`:
    - B1 (no test edit): the census goes red (12 → 13), so the speed bump works.
    - B2 (census count bumped to 13, the natural developer response): all green. The leak detector itself never
      fires.
  - A method return, as in `raise X(self._why())`: `_loaded_names` yields only `self`.
  - A generator `yield`.
  - Mutable aliasing (`alias = parts; alias.append(str(e))`).
  - `future.exception()` as a source.
  - `__context__` / `__cause__` read inside a kept-only handler. Mutant C, zero edits:
    `requirement._eval` → `f"{exc.message} [{exc.__context__}]"`, and 933 unit + api tests stay green. The
    handler holds a kept exception, but its `__context__` is arbitrary. `raise … from None` suppresses the
    display of `__context__`; it does not clear it.
- **Not live today.** No current call site feeds except-bound text into a kept construction's parameter.

### P2-4 — Nothing guards the door side

- **What the guard sees.** The kept set is derived only from `USER_FACING_RUN_ERRORS` and from checks of the form
  `type(x) is X`.
- **What it doesn't.** A new route that returns `detail=str(exc)`, or a door written with `isinstance`,
  `type(x) in (…)` or `==`, is invisible to every guard in the repo. `test_no_exception_text_in_logs` covers logs
  only.
- **Mutant H**: `shift_optimizer/app/api/export.py:65` wrapped in `except ValueError as exc: raise
  HTTPException(400, detail=str(exc))`. Result: 933 unit + api tests green.
- **Today's state is clean.** A grep of the tree finds only these doors:
  - the three named doors;
  - the activities 422 (`activities.py:171-182`) and preflight (`preflight.py:215-228`), which return
    `RequirementError.message`, a kept type.
- **Fix.** A route-response census: every `HTTPException(detail=…)`, and every response value, whose expression
  reads an except-bound name must be a named door.

### P3-1 — User-authorable extreme numbers end a run as `internal error (…)`

- **Probe method.** Through the real routes (in-memory), POST /roles and POST /activities return 201 for each
  input below. The real executor then stores:

  | input | stored error | raw text | site |
  |---|---|---|---|
  | `costFactor` 1e20 | `internal error (ValueError)` | ortools "Value out of range: 10000000000000000000000" | `solver.py:318` has a lower bound only |
  | formula `1e308 * 10` | `internal error (OverflowError)` | "cannot convert float infinity to integer" | `requirement.py:132` |
  | formula yielding NaN | `internal error (ValueError)` | — | `requirement.py:132` |
  | formula `1e18` | `internal error (OverflowError)` | "Does not fit in an int64_t: 1000…" | `solver.py:219` |

- **Is it a leak?** No. The raw text is number-only, and no domain check existed before either. It is the same
  class of user-authored defect that `ed403b9` fixed.
- **Before `fe0a07a`** users saw the raw library text. Now they get a generic line with no hint.
- **Fix.** Upper and finiteness bounds in `_validate_inputs` and in `compute_requirement`, raising the kept
  types.
- **Related.** Preview 500s on the same formulas; that is pre-existing.
- **NaN/Inf are not reachable.** The API response fails to serialize them, and JSONB refuses them.

### P3-2 — An upload that the `csv` module refuses is a generic 500, not the 400 fixed sentence

A field larger than `csv.field_size_limit` raises `csv.Error`, which is not a `ValueError`. `parse_csv` lets
it escape, and the probe got `500 'Internal Server Error'`. There is no leak, and the behaviour is pre-existing.

### P3-3 — The declared-gap list in the guard is inaccurate

`test_kept_error_raise_sites.py:34-36` has these problems:

- The literal-getattr wording (P2-1).
- `sys.last_value` / `last_exc` are listed as sources, but `_reads_an_exception` (`:180-193`) matches them only as
  calls. They are attributes, so they are never detected. This is moot in a server.
- The `type` / `isinstance` sanction (`_loaded_names`, `:129-138`) skips the whole subtree of a three-argument
  `type(name, bases, {…})`, which can hide a read. The case is contrived.
- The list omits every bypass named in P2-1 to P2-3.

### P3-4 — Legacy rows keep raw text

There is no read-time fallback (`run_executor.py:185-196`, argued in the docstring). Rows written before
`fe0a07a` are still returned raw by `GET /runs/{id}` and `/jobs/{id}/runs`. The dashboard (`RunsPanel.tsx:316,406`,
`OutputsPanel.tsx:211`) and copilot-mro read them too. The owner's DML item is already recorded in Addendum 90.

### P3-5 — Consumers in other repos (noted, not edited)

- **copilot-mro** reads `run.error` raw into the LLM: `optimizer_plan_digest.py:110`,
  `optimizer_decompose.py:298-307`.
- **copilot-mro** builds `f"… error: {exc}"` in its optimizer tools: `optimizer_plan_digest.py:367`,
  `optimizer_decompose.py:378`, `optimizer_runs.py:430`.
- Both are already routed to copilot-mro **M-TOOL-ERRORS** (Addendum 90).
- **dashboard** renders `run.error` verbatim. That is clean for rows written after the fix.

---

## What I tried to break and could not

- **Door behaviour under every surprise kind.** The sentinel catalogue covers 10 kinds × 3 phases, plus a real
  pydantic error, a bare `FormulaError` (the parent of a member) and a member subclass. Four control mutants all
  went red:
  - M1 (door returns `str(exc)`): 33 failed;
  - M2 (SolverInputError dropped from the set): 4 tests failed, across the census, the derivation and the
    behavioural checks;
  - M4 (`isinstance` door): the derivation and the subclass test went red;
  - M5 (upload door returns `str(exc)`): 8 failed.
- **A SolverInputError site reverted to `ValueError`** (M3). Both the census equality and the ROLE_DEFECTS
  behavioural drive went red.
- **Exemption drift.** M6 (`{exc}` → `{exc!r}`) went red on EXEMPT equality.
- **A new taint on an existing kept site.** M7 (`exc.reason` appended to a ScheduleCsvError) went red.
- **The detector's declared shapes and more.** Beyond the implementer's 23 witnesses, these 14 extra decoys were
  all detected:
  - `.format`, `%`, `+` concatenation, `str.format(...)`, `format_map`;
  - a message built earlier then `raise … from None`;
  - `sys.exception()`, `from sys import exc_info as ei`, `traceback as tb`;
  - `__notes__`, exception-group members, `e.__str__()`, `type(e).__str__(e)`;
  - an `isinstance`-guarded `str(e)`.
- **Other exception-text routes.** No other route returns `str(exc)`, `repr` or `detail=exc`. There is no SSE and
  no websocket. `execute_run` cannot raise out of a background task. The api gateway's global handler returns
  `{"detail": "Internal server error"}` (`api/flynapse_api/main.py:480-483`); its log line is another repo's
  concern.
- **Content inside kept messages.** Every construction was read.
  - `RunExecutionError` carries only ids, or solver status names via `result.error` (`solver.py` builds these
    from constants and `status_name`).
  - `RequirementError` carries the rule's own type or mode repr and FormulaError text.
  - The `Invalid arguments` exemption can only hold builtin wording or numbers: `_apply` sees floats only.
  - The `Invalid syntax` exemption quotes only the user's formula. A NUL byte gives "source code string cannot
    contain null bytes".
  - `DurationQueryError` quotes the caller's own key; `ScheduleCsvError` is fixed text.
- **User-reachable plain ValueErrors in the run path.** All 16 input checks are now SolverInputError.
  `availability_from_starts` (`coverage.py:122`) is an internal invariant. `_parse_constraints` is tolerant, and
  `ConfigSnapshot` validates at write. Driving roles through the real POST /roles showed:
  - `break minutes 10**30` completes;
  - `duration 0.001` gives the SolverInputError "delivers no coverage".
- **Test weakening.** Every edit to a pre-existing test in the range is a strengthening
  (`pytest.raises(ValueError)` → the domain type). The coverage length-mismatch test now pins
  `type(...) is ValueError`.

## What I did not test

- **Anything live.** No live stack was run: no Postgres beyond the repo's own db lane, no docker, no gateway
  mount.
- **The api gateway's own log line.** `api/flynapse_api/main.py:474-478` logs `str(exc)` and a traceback. That is
  outside this range and belongs to the api lane.
- **The duration-query service against a real driver.** For example, psycopg2's NUL-byte `ValueError`. It is
  reasoned to take the fixed-sentence path, not driven.
- **The implementer's 16 + 10 + 9 + 14 recorded mutants.** Not reproduced one by one. The writer census
  (`test_run_error_column_writers.py`) was not mutated by this review; see SO-02.
- **copilot-mro and dashboard behaviour.** Read only; no code there was run.

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SO-01 | shift-optimizer | `shift_optimizer/app/services/run_executor.py:170-199` | `run_error_text`: exactly `RunExecutionError`, `RequirementError` and `SolverInputError` keep their message, matched by exact type; anything else stores `internal error (<Type>)` | M-SHIFT-RUNERROR: generic for surprises | 10 sentinel kinds × 3 phases + pydantic + parent + subclass drives through the real executor and the runs router | `tests/api/jobs_runs/test_api_run_error_withholding.py`: `test_a_surprise_stores_only_its_class_name`, `test_a_subclass_of_a_member_is_not_a_member`, `test_the_parent_of_a_member_is_not_a_member`, `test_the_user_facing_set_is_exactly_the_three_domain_types` | **yes**: M1 (door returns `str(exc)`) 33 failed; M2 (SolverInputError dropped) 4 failed | — | 0 | F1 | **SETTLED** |
| SO-02 | shift-optimizer | `run_executor.py:353-364`; census `tests/unit/persistence/test_run_error_column_writers.py:60-77` | The failed write is the only failure writer of `optimizer_runs.error`, and every `error` key in the tree is a named site | A second writer would bypass the door | Census equality over 5 sites; door-integrity decoys | `test_every_error_key_in_the_tree_is_a_named_site`, `test_no_error_key_carries_exception_text`, `test_the_door_is_the_one_def_in_the_executor` | implementer-recorded (16/16, Addendum 90); **not reproduced here** | — | 1 | F1 | **ASSERTED** |
| SO-03 | shift-optimizer | `shift_optimizer/app/services/solver.py:291-328`, `coverage.py:54-60`, `solver_errors.py:18` | The 16 input checks raise `SolverInputError(ValueError)`, and the type joins the kept set | `fe0a07a` had turned user-written refusals into `internal error (ValueError)` | 7 ROLE_DEFECTS driven from role rows; probe: `duration 0.001` keeps its message | `test_a_role_the_solver_refuses_keeps_its_message`; `test_every_construction_of_a_kept_type_is_a_named_site` | **yes**: M3 (one site back to ValueError) 2 failed | — | 0 | F1 | **SETTLED** |
| SO-04 | shift-optimizer | `shift_optimizer/app/services/coverage.py:121-122` | `availability_from_starts`' length check stays a plain `ValueError` | The solver builds `starts` itself, so a mismatch is a bug, not user input | Read: sole caller is `solver.py`, with `starts` of horizon length | `tests/unit/engine/test_coverage.py:162` `test_length_mismatch_rejected` (asserts `type(...) is ValueError`) | not recorded | — | 1 | F1 | **ASSERTED** |
| SO-05 | shift-optimizer | `shift_optimizer/app/api/duration_query.py:42-49`; `services/duration_query.py:137-160` | The 400 returns `str(exc)` only for the exact type `DurationQueryError`; any other ValueError gets `UNANSWERABLE_DETAIL` | pydantic, `int()` and codec text was not written for the caller | 5 sentinel ValueError kinds + a subclass, through the real router | `tests/api/duration_query/test_duration_query_error_withholding.py` (all 4 tests) | **yes**: M4 (`isinstance` door) 3 failed | — | 0 | F1 | **SETTLED** |
| SO-06 | shift-optimizer | `shift_optimizer/app/api/schedules.py:316-321`; `services/schedule_processing.py:160-216` | The upload 400 returns `str(exc)` only for the exact type `ScheduleCsvError`, raised at the 3 authored sites | Same | 3 real refused byte strings + 5 sentinel kinds + a subclass | `tests/api/schedules/test_api_schedule_upload_error_withholding.py` | **yes**: M5 (door returns `str(exc)`) 8 failed; M7 (`exc.reason` in a ScheduleCsvError) 1 failed | — | 0 | F1 | **SETTLED** |
| SO-07 | shift-optimizer | `shift_optimizer/app/services/formula.py:285-290`; `test_kept_error_raise_sites.py:84-87` | Exemption: `FormulaError(f"Invalid arguments to '{func.id}': {exc}")` | `_apply` sees floats only, so its text is builtin wording or numbers | Read `_apply` (`formula.py:295-310`): `min([])`, `int(nan/inf)`, `IndexError`, `OverflowError`. Probe: `round(1.5, nan)` → "cannot convert float NaN to integer" | `test_only_the_exempt_constructions_carry_caught_text` (EXEMPT by equality) | **yes** for the pin: M6 1 failed. The safety argument is judgment | — | 1 | F1 | **PARTIAL**: pin SETTLED; safety rests on reading `_apply`, and widening `_apply`'s inputs breaks it silently |
| SO-08 | shift-optimizer | `formula.py:114-120`; `test_kept_error_raise_sites.py:88-92` | Exemption: `FormulaError(errors[0])` carrying `Invalid syntax: {SyntaxError.msg}` | These are the parser's words about the user's own formula | Probe: a NUL byte in a formula (POST /activities 201) → stored "Invalid syntax: source code string cannot contain null bytes" | same EXEMPT equality | pin shares M6's assertion; the safety argument is judgment | — | 1 | F1 | **PARTIAL**: pin SETTLED; safety is judgment (CPython parser wording) |
| SO-09 | shift-optimizer | `tests/unit/contracts/test_kept_error_raise_sites.py:282-353` | The kept set is derived from the doors (`USER_FACING_RUN_ERRORS` + `type(x) is X` + FEEDS) and pinned by equality to KEPT_DEFINITIONS | A type added to a door is guarded without editing the file | M2, M4 and M5 each dropped a door member and the derivation went red | `test_the_kept_set_is_derived_from_the_doors`, `test_every_kept_type_is_defined_once_where_named` | **yes**: M2, M4, M5 | — | 0 | F1 | **SETTLED** for the two door forms it reads; see SO-13 |
| SO-10 | shift-optimizer | `test_kept_error_raise_sites.py:145-279` | Per-module taint over the declared sources and propagations | A kept message must not be built from caught text | 23 implementer witnesses; 14 extra reviewer decoys detected; M7 red on the real tree | `test_the_detector_refuses_every_leaking_shape`, `test_only_the_exempt_constructions_carry_caught_text` | **yes**: M7 1 failed | — | 0 | F1 | **SETTLED** for the declared shapes |
| SO-11 | shift-optimizer | `test_kept_error_raise_sites.py:154-178` | Kept-type aliases are resolved only through `from … import X as Y` | — | Mutant A (assignment alias) green on both guards and 931/933 unit + api; sentinel reached `GET /runs/{id}`. Literal `getattr`, `cls()` and `type(err)()` decoys: 0 constructions seen | **none** catches it | **yes, and the property fails**: A green | 1 (P2-1) | 1 | F1 | **REFUTED**: "every construction of a kept type is a named site" is false for aliases |
| SO-12 | shift-optimizer | `test_kept_error_raise_sites.py:313-318`, `:367-376`; sanction at `:23-27` | "Every in-tree subclass of a kept type is kept", which the kept-only-handler sanction relies on | — | Mutants E and E2b green (933 unit + api); E laundered `could not convert string to float: 'SENTINEL…'` into a stored RequirementError | **none** catches it | **yes, and the property fails**: E, E2b green | 1 (P2-2) | 1 | F1 | **REFUTED**: alias and dynamic subclasses escape the rule |
| SO-13 | shift-optimizer | `test_kept_error_raise_sites.py:201-263` | Taint propagates through assignments, loop/with targets, defaults, mutators and bare-name returns only | — | B2 (helper parameter, census bumped) green; C (`exc.__context__` inside a kept-only handler, zero edits) green on 933 tests; method-return, `yield`, mutable-alias and `future.exception()` decoys all missed. Measured: no live flow of this shape in the tree today | census catches a NEW construction (B1 red) but not the flow | **yes, and the property fails**: B2 and C green | 1 (P2-3) | 1 | F1 | **REFUTED**: undeclared intra-module gaps |
| SO-14 | shift-optimizer | `test_kept_error_raise_sites.py:34-36`, `:105`, `:129-138`, `:180-193` | The declared-gap list | Stating a gap is what makes it reviewable | Literal getattr is not handled; `sys.last_value` / `last_exc` are never detected (attributes, not calls); a three-argument `type()` subtree is skipped; P2-1..P2-3 are omitted | **none** | n/a | 3 (P3-3) | 1 | F1 | **OPEN** |
| SO-15 | shift-optimizer | `shift_optimizer/app/api/*.py` (e.g. `export.py:65`) | No census of route-response doors | The commits fix two routes by hand | Mutant H (`detail=str(exc)` in export) green on 933 tests. Today's doors, by grep: runs, duration-query, upload, and `RequirementError.message` in activities (`activities.py:171-182`) and preflight (`preflight.py:215-228`) | **none** | **yes, and the property is unguarded**: H green | 2 (P2-4) | 1 | F1 | **OPEN** |
| SO-16 | shift-optimizer | `solver.py:318` (lower bound only), `solver.py:219`, `requirement.py:132` | Extreme numbers a user can author end a run as `internal error (ValueError/OverflowError)` | No domain check existed before either | Probe: POST /roles and POST /activities 201, then the run stores `internal error (…)` for `costFactor` 1e20, formula `1e308*10`, a NaN formula and `1e18` | **none** | n/a | 2 (P3-1) | 1 | F3 | **OPEN** |
| SO-17 | shift-optimizer | `shift_optimizer/app/services/schedule_processing.py:203-224` | `csv.Error` (e.g. a field over the size limit) escapes as a generic 500 | `csv.Error` is not a `ValueError` | Probe: 200 000-character field → `500 'Internal Server Error'` | **none** | n/a | 2 (P3-2) | 1 | F3 | **OPEN** (pre-existing, no leak) |
| SO-18 | shift-optimizer (data) | `run_executor.py:185-196` | No read-time fallback for rows written before `fe0a07a` | New user-facing rows and legacy rows are byte-indistinguishable | Rows written before `fe0a07a` are still served raw by both runs endpoints, the dashboard and copilot-mro | **none** | n/a | 0 (P3-4, pre-existing data) | 2 | F1 | **OPEN**: owner DML, keyed on deploy time (Addendum 90) |
| SO-19 | copilot-mro | `copilot_mro/app/services/agent_shared/tools/optimizer/optimizer_plan_digest.py:110,367`; `optimizer_decompose.py:298-307,378`; `optimizer_runs.py:430` | The optimizer tools read `run.error` raw and build `f"… error: {exc}"` for the LLM | Another repo | Read only | **none** here | n/a | 0 (P3-5, other repo) | 2 | F1 | **OPEN**: routed to copilot-mro M-TOOL-ERRORS |
| SO-20 | dashboard | `components/features/optimizer/RunsPanel.tsx:316,406`; `OutputsPanel.tsx:211` | `run.error` rendered verbatim | — | Read only; clean for rows written after the fix | **none** | n/a | 3 | 1 | F3 | **OPEN** (a note; depends on SO-18) |
| SO-21 | shift-optimizer | `shift_optimizer/app/services/solver_errors.py:1-24`; `run_executor.py:120` | `SolverInputError` lives in an import-free leaf, so `run_executor` can import it at module scope without pulling in ortools | The lazy-ortools invariant | Smoke lane 7/7 at every commit | `tests/smoke/imports/test_import_smoke.py:11` `test_import_is_fast` | not recorded | — | 1 | F1 | **ASSERTED** |

**Tier 0 (SETTLED):** SO-01, SO-03, SO-05, SO-06, SO-09 and SO-10. Each one has been seen to fail with its
property removed in this review. Each can drop out of Fable's reading only as far as its stated scope; SO-09 and
SO-10 are scoped by SO-11 to SO-13.

**Totals:** 21 claims.

| state | count |
|---|---|
| SETTLED | 6 |
| PARTIAL | 2 |
| ASSERTED | 3 |
| REFUTED | 3 |
| OPEN | 7 |

---

## Open claims, tier 2 first

**Tier 2**

1. **SO-18.** Legacy `optimizer_runs.error` rows written before `fe0a07a` still carry raw `str(exc)` and are
   served raw by both runs endpoints, the dashboard and copilot-mro. The code cannot fix this. It is the owner's
   DML decision, keyed on deploy time, and is already recorded in Addendum 90.
2. **SO-19.** copilot-mro passes the column and its own `{exc}` text to the LLM. Routed to M-TOOL-ERRORS; nothing
   is owed in this repo.

**Tier 1**

3. **SO-11 (P2-1).** Resolve module-level `Name = Kept` assignments into `kept_aliases`. Treat a literal
   `getattr(…, "Kept")`, `cls(...)` inside a kept class, and `type(<kept-bound>)(...)` as constructions, so the
   census counts them too.
4. **SO-12 (P2-2).** Resolve base-class names through the same alias map. Refuse any dynamic `type(name, bases,
   …)` whose bases include a kept name.
5. **SO-13 (P2-3).** Bind call arguments to the callee's parameters within the module. Link `self.<m>()` and
   `<obj>.<m>()` to methods by name, and treat `yield` like `return`. In a kept-only handler, taint reads of
   `__context__`, `__cause__`, `__traceback__` and `args` on anything other than `.message`. Alternatively, keep
   the gaps and declare them.
6. **SO-15 (P2-4).** Add a route-response census: every `HTTPException(detail=…)` and every response value
   derived from an except-bound name must be a named door. This is the lock that "only three doors return a
   message" currently lacks.
7. **SO-16 (P3-1).** Add upper and finiteness bounds to `_validate_inputs` and `compute_requirement`, raising the
   kept domain types, so extreme user input gets a sentence rather than `internal error (…)`.
8. **SO-17 (P3-2).** Map `csv.Error` in `parse_csv` to a ScheduleCsvError, or to the fixed upload sentence.
9. **SO-14 (P3-3).** Correct the declared-gap list, whichever of items 3–5 is taken.
10. **SO-20.** A note only. The dashboard is correct once SO-18 is settled.
