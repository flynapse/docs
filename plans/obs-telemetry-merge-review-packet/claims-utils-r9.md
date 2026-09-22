# PARTIAL — Claims packet — utils review round 9 (`179cc6d..fe45c35`)

**PARTIAL: the review is PAUSED (owner cut the agent cap to 1), not finished.** Attack 2, the mutation batch
and the settlement of every r8 row are outstanding. Resume state:
`~/.claude/scratch/obs-merge/utils-review-r9/PAUSED.md` (DONE / IN FLIGHT / REMAINING / RECIPE).

Independent adversarial review (Opus), 2026-09-22, resumed once after the first reviewer was killed. Read-only
against every real tree. utils-obsm HEAD is `fe45c35` and clean. Copies are `git archive`s under
`~/.claude/scratch/obs-merge/utils-review-r9/`; on resume **every copy was md5-verified file-by-file against
`git show <sha>:<path>`** — `ws/utils-obsm`, `work/head`, `dec/utils-obsm` vs `fe45c35` and `work/base`,
`wsb/utils-obsm` vs `179cc6d`: 157 files each, **0 mismatches** (so the killed lane's probe output is reusable,
and `mutant.sh` restored `dec/` intact).

**Sibling under test moved mid-review.** The inventory's copilot-mro limb reads the LIVE sibling working tree.
The killed lane measured against copilot-mro-obsm `c27db590`; it is now `ce545211`, and one mutation baseline
(`DW06`) went red on `processing.py:577 passes 'tenant_id' to document_hub_processing_duration_seconds` while
that tree was mid-edit — a state the current source no longer has. See P3-U9-1.

## Lane

Recipe (every run through `pytest-slot.sh`, `-n 2`, one at a time):
`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test
PYTHONPATH=<copy>:/home/aditya/Code/core-obsm:/home/aditya/Code/flynapse-otel:<plug>` →
`api/.venv/bin/python -m pytest -p r9report -p no:randomly -o addopts="-ra --strict-markers" -n 2 -q tests`.
The `r9report` plugin prints `rootdir`, `utils.__file__`, `flynapse_otel.__file__`; both were inside the copy in
every run.

| run | tree | sibling | result |
|---|---|---|---|
| full lane at HEAD (killed lane, 05:19) | `ws/utils-obsm` | `c27db590` | 1986 passed, **6 failed**, 0 skipped, 77 s |
| full lane at HEAD (resume, 05:35) | `ws/utils-obsm` | `ce545211` | 1979 passed, **9 failed**, **4 skipped**, 60 s |
| per-commit sweep, all 14 commits (`parallel-commits.sh -L -j 2`, serial inner, cross-repo file deselected) | `pc/ws-<sha>` | live | 1909 → **1968 passed**, 0 skipped, **+1 identical artefact red at every commit** |
| the artefact files, read-only in the REAL tree (killed lane) | `/home/aditya/Code/utils-obsm` | live | **27 passed** in 3.2 s |

Both totals are 1992 items. Every red and every skip is in two files only —
`tests/unit/infra/test_cross_repo_reads_name_their_checkout.py`, `tests/unit/infra/test_root_anchoring.py` — plus
`tests/unit/safety/test_no_provenance_laundering.py::test_the_scan_reaches_the_code_it_is_defending`, and each
names the copy's location as the reason ("scanned core-obsm while core-obsm matches this worktree"; "only one
utils checkout in this workspace"; "no dashboard checkout beside this repo"). The 27 that were re-run read-only
in the real tree are green. **OWED on resume:** `test_root_anchoring.py` was not in that real-tree re-run — the
3 extra reds and the 4 skips of the resume run are not yet proven to be artefacts by a real-tree run.

## Findings so far (provisional severities)

### P1-1 (provisional) — the fail-closed reader still passes key-adding writes and family misreads SILENTLY

59 plants through the real `_emissions` at `fe45c35` (`probes/attack1.py`, harness calls the module's own
`_emissions` / `BY_NAME` / `_Family.keys` / `.kind`, so the verdict is the tests' own). The redesign (b1d9834,
5c7f81e, 852de2e, 6ea14ea, fffbf1a) genuinely closed 20 shapes that were silent at `179cc6d` — K01-03, K10,
K19-25, K30-32, N01, N03, N09, N17, N20, N22, W07 — including the r8 decoys A, B and C. **18 shapes still come
out silently GREEN** (no emission recorded, nothing in `unresolved`, no test fails). All 18 are also silent at
`179cc6d`, so they are pre-existing rather than regressions:

| # | shape | why it is silent |
|---|---|---|
| K15/K16/K36/K37 | `labels = alias = {…}` then `alias["email"]=e` / `.update(email=e)` / `\|= {...}`, and the 3-way chain | the single-target form (`alias = labels`) is REPORTED (r8 A); a chained assignment binds both names to one display and neither mention is read as an alias |
| W01–W04 | a forwarder referenced but not called at a site the reader recognises: `functools.partial(_emit, …)()`, `go = _emit; go(…)`, `run_later(_emit, …)`, `getattr(mod,"_emit")(…)` | the forwarder's own body is skipped as a known forwarder, and no recognised call site credits the family |
| W06 | a decorator that injects a key into the forwarder (`kwargs["email"]=…`) | the decorator is not read; the caller's keys are what is credited |
| W08/W09 | a wrapper CLASS method named `increment_counter` / `record_histogram` that adds a key or changes the kind | `_METHOD_KINDS` is matched on the callee name, so the wrapper's own definition is read as an emission seat, not as an interposer |
| W10 | a forwarder that rebinds its family parameter (`name = "llm_tokens_total"`) | the family is taken from the caller's argument |
| W12 | a method whose first parameter is named `this`, not `self` | the family index shifts by one |
| W13/W14 | `from utils.observability.metrics import increment_counter as inc` / `record_document_hub_metric as rec`, then `inc(...)` | the alias is not a `_METRIC_CALLEES` name |
| N10-N13, N18, N19, N21 | an IMPORTED constant rebound in the IMPORTING module (under `if`, through `global`, top-level non-literal, by `for`, `with`-as, `def`, or in a re-exporter) | the constant resolves through the import to the defining module; the importing module's own rebinding is not counted as a second binding |
| N14/N15 | module-level `locals()["FAMILY"]=…` / `vars()["FAMILY"]=…` | `_MODULE_REFLECTION` is `{globals, exec, eval}` — `locals`/`vars` at module scope are the same dict and are not named |

**Mutation-proved in the real estate** (plant appended to `utils/llm.py` in the `dec/` copy, whole inventory lane):
`DK15` (the chained alias, K15) **SURVIVED** — the full inventory lane is green with a live `email` label on
`llm_requests_total`. `DD` (r8 D, the computed metric-method name) SURVIVED and is declared. The r8 decoys `DA`
(alias), `DB` (closure), `DC` (helper) and the control `DE` are now **KILLED**, which is what the redesign was for.
`DW01`, `DN11`, `DW06`, `DW08` have not been run to a clean verdict yet (DW06/DW08 hit the moving sibling).

Judged against the file's own contract — "What it cannot see is declared, each limit pinned
(`_NOT_SEEN_BY_DESIGN`)" — none of these 18 is in that register, and the register names exactly five shapes. So
the docstring still overclaims, for the fourth round. The runtime shim bounds the consequence (an undeclared key
is DROPPED, never exported), so this is a guard-coverage finding, not a leak.

### P3-U9-1 (provisional) — the utils lane's verdict depends on another repo's WORKING TREE

`_sibling_emissions()` reads `copilot-mro-obsm`'s checked-out files, not a commit. While that tree was mid-edit
(between `c27db590` and `ce545211`) the utils inventory lane went red on a copilot-mro line. A utils verdict is
only meaningful beside a NAMED sibling SHA; this packet names `ce545211`.

### P3 (provisional, carried from the killed lane's probes)

- `fabb94c`'s args walk reaches only direct `BaseException` ELEMENTS of `args`. An exception inside a tuple, list
  or dict inside `args` (A2-A4), one kept as an attribute by a custom `__init__` (A9), one behind an `args`
  property returning a list (A10), one held in `__notes__` (A12), and a non-exception wrapper whose `__str__`
  renders it (A14) all still ship their text. Walk spec and bounds: see below.
- P3-6's docstring pin (1a690d8) reads only bullet lines; the r8 M25 prose replay is expected to survive.
- P3-4 (e528cbe) pins `_RESERVED_LOG_RECORD_ATTRIBUTES` by identity; the seat the bridge actually reads is
  `_RESERVED_ATTRIBUTES` (`log_bridge.py:119,154`).
- P3-5 (5d81811) still misses SQL that does not open the string (a comment, `BEGIN;`, a CTE, `executescript`),
  concatenated SQL, `DROP MATERIALIZED VIEW/TYPE/EXTENSION/OWNED`, Redis `execute_command("FLUSHALL")` and Redis
  `unlink` (excluded by `_NOT_DESTRUCTIVE_HERE` and undeclared).

## The `fabb94c` args walk — SPEC for the flynapse-otel port (P3-7)

`_every_link(exc) -> list[BaseException] | None` (`utils/_exception_text.py:234-263` at `fe45c35`). It feeds
WITHHOLDING only, never rendering. Exact behaviour, measured (`probes/args_walk.py`, 22 shapes):

1. **Worklist, not recursion.** `pending = [exc]`; `pop()` from the end (LIFO); `seen` is a set of `id()`;
   `found` is the emission order. No recursion, so no stack bound.
2. **What each popped link enqueues**, in this order: `__context__`, then `__cause__` (both only when not
   `None` — a SUPPRESSED `__context__` is walked too); then, if it is a `BaseExceptionGroup`, every member of
   `.exceptions`; then every direct element of `.args` that `isinstance(..., BaseException)`.
3. **`_held_in_args` is deliberately shallow.** It reads `link.args` inside `try/except Exception` (an `args`
   that raises offers no link — note: a `BaseException` from the property PROPAGATES), returns `[]` unless the
   value `isinstance(..., tuple)`, and filters direct elements only. It does NOT descend into a tuple, list,
   dict, set or any other container held in `args`, does NOT read instance attributes, and does NOT read
   `__notes__` objects.
4. **Termination.** `seen` by `id()` makes every cycle finite: `e.args = (e, inner)` and a mutual `a ↔ b` cycle
   both return in <1 ms. Depth is bounded by the same counter, not by the walk shape.
5. **The bound is a LINK COUNT, checked after append.** `if len(found) > _MAX_LINKS: return None` with
   `_MAX_LINKS = 256`. So 256 links are checked and 257 returns `None`; measured: 255 exceptions in `args` plus
   the outer = 256 links, still checked; 257 returns `None`. `None` makes every caller write
   `WITHHELD_MESSAGE` ("[message withheld: too much to check for exception text]") — fail-closed, and 100k
   exceptions in `args` cost 11 ms.
6. **Quoting, separately.** `_partial_quotes` quotes STRING args (and `args`'s own repr, an `OSError`'s
   `filename`/`filename2`, each `__notes__` STRING, a botocore `response["Error"]["Message"]`, and the first
   line of a multi-line `str()`). An exception found by the walk is withheld by its own `str()`/`repr()`, with
   the delimiter rules (`_MIN_FREE_QUOTE = 8`: a shorter single-argument quote is only replaced between
   delimiters — `KeyError('hunt2')` quoted as `x'hunt2'y` is NOT replaced).
7. **Measured leaks the port must decide on** (each ships the inner exception's text on the JSON line and the
   OTLP body): an exception inside a tuple / list / dict inside `args`; one kept as a plain attribute by a
   custom `__init__`; one behind an `args` property that returns a LIST (not a tuple); an exception object
   appended to `__notes__`; a non-exception wrapper object in `args` whose `__str__` renders the exception.
   Clean: the direct `args[1]` shape, two and three levels of `args` nesting, a group member holding one in
   `args`, a `__cause__` whose `args` hold one, an exception CLASS (not instance) in `args`, a
   `KeyboardInterrupt` in `args`.

**The port must reproduce points 1-5 exactly**, because `flynapse_otel/failure.py` carries a copy of
`_every_link` and utils is to delete its own after adopting it (P3-7 / M-FAILURE-HOME). The bound in particular
is a fail-closed switch, not an optimisation: a port that recurses, or that counts differently, changes which
records are withheld whole.

## Claims table

**PARTIAL — not yet written.** The r8 rows this batch must settle (`claims-utils-r8.md`) and their seats:
U8-10/P2-1 → b1d9834 + 5c7f81e + 852de2e + 6ea14ea + fffbf1a; U8-21/P3-1 → fabb94c; U8-12/P3-2 → 7dc9d6e;
U8-14/P3-3 → cf3a92b; U8-17/P3-4 → e528cbe; U8-15/P3-5 → 5d81811 and P3-10 → fd28a4c; U8-18/P3-6 → 1a690d8;
U8-22/P3-7 → NOT fixed (the port is owed; the walk spec above is its input); U8-13/P3-8, P3-9 and U8-11 →
routed to the copilot-mro lane.
