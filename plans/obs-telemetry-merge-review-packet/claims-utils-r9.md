# Claims packet — utils review round 9 (`179cc6d..fe45c35`)

**Verdict: MERGE-CLEAN — P0 0 · P1 0 · P2 1 · P3 5.** (Merge-blocking is P0/P1 only.)

Independent adversarial review (Opus), 2026-09-22, resumed twice: once after the first reviewer was killed, once
after the owner cut the agent cap. Read-only against every real tree throughout. utils-obsm HEAD is `fe45c35`
and clean at the end of the review, as it was at the start.

This is the LAST utils round, and the owner trimmed the scope to two things at full rigour — the fail-closed
metric-inventory redesign, and the exact `fabb94c` args walk (the SPEC for the flynapse-otel port) — with
everything else light. Both are answered below; the walk spec is written out in full so the port needs no
re-derivation.

## How it was run

Copies are `git archive`s under `~/.claude/scratch/obs-merge/utils-review-r9/`. **Every copy was md5-verified
file-by-file against `git show <sha>:<path>`**: `ws/utils-obsm`, `work/head`, `dec/utils-obsm` vs `fe45c35`;
`work/base`, `wsb/utils-obsm` vs `179cc6d` — 157 files each, 0 mismatches, before and after the mutation batch.

**The sibling is PINNED.** The inventory's copilot-mro limb reads the sibling CHECKOUT, not a commit, and that
tree moved twice during the review (`c27db590` → `ce545211` → `16760afc`), flipping a mutation baseline red on a
`processing.py` line that no longer exists. Everything reported here was measured against a `git archive` of
copilot-mro-obsm **`ce545211`** (`sib/copilot-mro-obsm`, 576 `.py` files md5-verified, 0 mismatches), symlinked
into `ws/`, `wsb/` and `dec/`. No probe or lane read the live sibling worktree. See P3-5.

Lane recipe, every run through `pytest-slot.sh`, `-n 2`, one at a time, behind a load gate:

```
ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test \
PYTHONPATH=<copy>:/home/aditya/Code/core-obsm:/home/aditya/Code/flynapse-otel:<plug> \
/home/aditya/Code/pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest \
  -p r9report -p no:randomly -o addopts="-ra --strict-markers" -n 2 -q tests
```

The `r9report` plugin prints `rootdir`, `utils.__file__` and `flynapse_otel.__file__` in every header; all three
were inside the copy in every run.

**Copy hygiene — a defect in my own predecessor's tree, found and fixed.** The mutation tree `dec/` carried three
UNTRACKED files from the killed lane (`tests/unit/infra/test_r9_probe_setup_swap.py`,
`tests/unit/observability/test_r9_probe_args_sinks.py`, `utils/_r9_names.py`). The md5 sweep could not see them
because it iterates `git ls-tree`, which has no entry for a file that is not in the commit. Both probe test files
were removed before the mutation batch; the killed lane's four KILLED verdicts were re-checked and each names a
real guard test in its log, so they stand. **A `git ls-tree`-driven md5 sweep proves no file was CHANGED; it does
not prove none was ADDED. A copy check needs both directions.**

## Lane totals

| run | tree | sibling | result |
|---|---|---|---|
| full lane at HEAD (killed lane) | `ws/utils-obsm` | live `c27db590` | 1986 passed, 6 failed, 0 skipped, 77 s |
| full lane at HEAD (resume) | `ws/utils-obsm` | live `ce545211` | 1979 passed, 9 failed, 4 skipped, 60 s |
| full lane at HEAD (pinned) | `dec/utils-obsm` | archive `ce545211` | **1981 passed, 7 failed, 4 skipped, 43 s** |
| per-commit sweep, all 14 commits (`parallel-commits.sh -L -j 2`, serial inner, cross-repo file deselected) | `pc/ws-<sha>` | live | 1909 → **1968 passed, 0 skipped**, +1 identical artefact red at every commit |
| **the artefact tests read-only in the REAL tree** | `/home/aditya/Code/utils-obsm` | live | **48 passed in 2.66 s, rc 0, `git status` byte-identical before and after** |

Every run is 1992 items. **Every red and every skip in every copy lane is a copy-location artefact**, and this is
now proven, not asserted: the three files that carry them —
`tests/unit/infra/test_cross_repo_reads_name_their_checkout.py`, `tests/unit/infra/test_root_anchoring.py`,
`tests/unit/safety/test_no_provenance_laundering.py` — are 48/48 green read-only in the real tree. Each names its
own reason in the copy ("scanned core-obsm while core-obsm matches this worktree", "only one utils checkout in
this workspace", "no dashboard checkout beside this repo"). The count varies with where the copy sits, which is
exactly what those guards exist to detect.

**Production diff in the whole range is 33 lines across two files**, and only one of them changes behaviour:
`utils/_exception_text.py` (+18/−1, the args walk) and `utils/weaviate_service.py` (+15/−2, **docstrings and
comments only** — verified by diffing with comment lines stripped). Everything else in the range is test code and
the plan. The one behaviour change strictly increases withholding.

---

## Findings, ranked

### P2-1 — The fail-closed inventory is much better and still does not declare what it cannot see (25 shapes, 5 proved in the estate)

`b1d9834`, `5c7f81e`, `852de2e`, `6ea14ea`, `fffbf1a` replace the r8 "enumerate the writes" reader with a
fail-closed one: a label dict's keys are read only when EVERY mention of the name in its function is a recognised
binding, write or no-op use; anything else is reported with its line. **It works.** Across 120 plants run through
the module's own `_emissions` (so the verdict is the tests' own `BY_NAME` / `_Family.keys` / `.kind`):

| | attack 1 (74 plants) | attack 2 (46 plants) | total |
|---|---|---|---|
| RED (a guard test fails) | 5 | 14 | 19 |
| REPORTED (lands in `unresolved`, which is asserted empty) | 42 | 30 | 72 |
| **silently GREEN — a smuggled key or a misread family passes** | **24** | **1** | **25** |
| GREEN and CORRECT (the plant smuggles nothing: K35, N02, N16, Q16) | 3 | 1 | 4 |
| closed by this range (silent at `179cc6d`, no longer) | 22 | 2 | **24** |
| regressions (silent at `fe45c35`, not at `179cc6d`) | 0 | 0 | **0** |

Four more changed from a precise RED to a fail-closed REPORTED (K33, N05, P17, Q15) — both outcomes fail the
suite, so nothing is lost; it is the over-reporting the implementer's plan already accepts. Two changed from
REPORTED to GREEN (N02, N16), and both are CORRECT: an aliased import, and a same-name binding in a module the
emitter does not import, now resolve instead of being reported.

The estate view is unchanged by the redesign: **24 emissions (12 utils + 12 copilot-mro), 0 unresolved,
byte-identical between `fe45c35` and `179cc6d`** against the pinned sibling. So the new reader introduced no
over-report against live code.

**What is still silent.** None of the 25 is in `_NOT_SEEN_BY_DESIGN`, which names exactly five limits, and the
module docstring says "What it cannot see is declared, each limit pinned as unseen". That claim is false for 25
shapes, in four families: a chained binding (4), the callee/forwarder side (11), an importing module's rebinding (8), and module-level reflection (2).

| # | shape | why it is silent |
|---|---|---|
| **K15 / K16 / K36 / K37** | a CHAINED assignment — `labels = alias = {…}` then `alias["email"]=e`, `.update(email=e)`, `\|= {…}`, and the 3-way chain | seat: `test_legacy_family_inventory.py:336`. For the `labels` mention the parent is an `Assign` whose `value` is a `Dict`, so it reads as a clean display; the assignment's OTHER targets are never examined. One dict, two names, and only one is checked. The single-target form (`alias = labels`) IS reported (r8 A). |
| **W01–W04** | a forwarder REFERENCED but not called at a recognised site: `functools.partial(_emit, …)()`, `go = _emit; go(…)`, `run_later(_emit, …)`, `getattr(mod, "_emit")(…)` | `6ea14ea` added "a reference to a metric method that is not called right there is reported" — but only for `_METRIC_CALLEES`. A reference to a user FORWARDER is not covered, and the forwarder's own body is skipped as known, so nothing is credited anywhere. The docstring's "every other way a module reaches a metric method in its source" over-reaches here. |
| **W06** | a decorator that injects a key into the forwarder | decorators are not read; the caller's own keys are what is credited |
| **W08 / W09** | a wrapper CLASS method named `increment_counter` / `record_histogram` that adds a key or changes the kind | `_METHOD_KINDS` matches on the callee NAME, so the wrapper's definition reads as an emission seat, not as an interposer (see P3-3) |
| **W10 / W12** | a forwarder that rebinds its family parameter / a method whose first parameter is named `this`, not `self` | the family comes from the caller's argument / `_forwarders`' `offset` only knows `self` and `cls` |
| **W13 / W14** | `from utils.observability.metrics import increment_counter as inc` (or `record_document_hub_metric as rec`), then `inc(…)` | the alias is not a `_METRIC_CALLEES` name |
| **N10–N13, N18, N19, N21, Q11** | an IMPORTED constant rebound in the IMPORTING module — under `if`, through `global`, a top-level non-literal, by `for`, `with`-as, `def`, in a re-exporter, or in an `except ImportError:` branch (Q11, new this round) | seat: `_Modules.resolve` (`:604`). `constants()` only records a TOP-LEVEL `Assign` of a string literal, so a rebinding anywhere else leaves no entry, and `resolve` then follows the import to the defining module. The per-module `bindings` counter that would catch it is computed in `constants()` and not consulted on the import path. |
| **N14 / N15** | module-level `locals()["FAMILY"]=…` / `vars()["FAMILY"]=…` | `_MODULE_REFLECTION` is `{globals, exec, eval}`; at module scope `locals()` and `vars()` are the same dict |

**Proved in the estate, not only in a temp dir.** Five decoys planted in `utils/llm.py` of the mutation copy, each
run against the **whole suite**, one at a time, on the pinned tree (baseline 7 failed / 1981 passed / 4 skipped):

| decoy | class | aimed lane | FULL lane |
|---|---|---|---|
| `DK15` chained-assignment alias adds `email` to `llm_requests_total` | K15 | SURVIVED | **SURVIVED** (identical to baseline) |
| `DN11` imported constant rebound through `global` | N11 | SURVIVED | **SURVIVED** |
| `DW01` forwarder through `functools.partial` | W01 | SURVIVED | **SURVIVED** |
| `DW06` decorator injects `email` | W06 | SURVIVED | **SURVIVED** |
| `DW08` wrapper method named `increment_counter` | W08 | SURVIVED | **SURVIVED** |
| `DD` `getattr(svc, "increment_" + "counter")` | declared | SURVIVED | **SURVIVED** — and DECLARED, so correct |
| `DA` alias / `DB` closure / `DC` helper (the r8 decoys) | — | **KILLED** ×3 | — |
| `DE` control (undeclared family) | — | **KILLED** | — |

**Severity and why this is P2, not P1.** My provisional grade during the paused lane was P1; the completed
evidence does not support it, and I am downgrading it with the reasons stated:

- the mechanism is TEST-ONLY — no production code path changes;
- the runtime consequence is bounded by the shim, and the file's own docstring says so: an undeclared family
  exports no attribute and a declared one DROPS every key it does not declare. The failure mode is a label
  silently lost from a series, not a leak and not a cardinality explosion;
- the range is a strict improvement: 24 shapes closed, 0 regressions, estate view byte-identical;
- what remains is a false claim in a register and a docstring — a contract problem, not a mechanism problem. r8
  graded the same mechanism P2/severity 2, and it is materially better now.

**The ask (for the queued utils fix batch, not for this round).** Name the 25 shapes in `_NOT_SEEN_BY_DESIGN` in
the four families above, so the docstring's claim becomes true, and add the probe corpus as a test that holds the
register to it — otherwise the next shape is found the same way, by a reviewer. Two of the four families also
have a small, precise fix if the batch wants one instead of a declaration:

- **chained assignment** — at `:336`, when `len(parent.targets) > 1`, either read the other targets' mentions too
  or return the dict unreadable. One condition.
- **the importing module's rebinding** — `constants()` already counts every binding of every name per module
  (`bindings`). `resolve()` follows an import without consulting it. Returning `_Unreadable` when the importing
  module binds the name more than once (the import itself plus a rebinding) closes N10–N13, N18, N19, N21 and Q11
  together.

The W-family is the one that genuinely wants a declaration rather than a fix: chasing every way a callable can be
referenced is the enumeration this redesign exists to abandon.

### P3-1 — The `fabb94c` args walk is deliberately shallow, and the shapes it does not reach are not declared

Measured over 22 shapes (`probes/args_walk.py`). `fabb94c` closes exactly the shape r8 reported (`RuntimeError(
"wrapped", inner)` quoted as `{outer.args[1]}`) and its nesting, and it is correct and cheap. Still reaching the
JSON line and the OTLP body: an exception inside a tuple, list or dict inside `args`; one kept as a plain
attribute by a custom `__init__`; one behind an `args` PROPERTY that returns a list rather than a tuple; an
exception OBJECT appended to `__notes__` (the strings in `__notes__` are quoted, the objects are not walked); and
a non-exception wrapper object in `args` whose `__str__` renders the exception. `_partial_quotes` declares only "a
format-spec slice and any other fragment", which does not name these. Severity 2, pre-existing for four of the
five, latent on a pattern search (no estate call site has these shapes today).

### P3-2 — The flynapse-otel port now genuinely diverges, and only a pin hides it

`utils/_exception_text.py` was byte-identical to `1a42390` (md5 `4c3c2437…`) through r8; `fabb94c` changed it
(md5 `5b6899d5…`). `flynapse_otel/failure.py` at flynapse-otel `ff20ca9` contains **no `_held_in_args`** — its
`_every_link` still walks cause, context and group members only. The two copies are no longer the same renderer.
flynapse-otel's parity test reads utils at the PINNED `UTILS_PARITY_SHA = 1a42390…`
(`tests/unit/failure/test_failure_parity_with_utils.py:34`), so its lane is green and will stay green until the
pin moves — which is the drift hazard M-FAILURE-HOME names, now real rather than structural. The walk spec below
is what the port needs; it should land before `UTILS_PARITY_SHA` moves past `fabb94c`.

### P3-3 — A wrapper method named like a metric method poisons the module's forwarder table, and the key is then attributed to an unrelated call site

`_forwarders` keys its table by `function.name` (`:770`), and at `:766` it unions `forwarded.keys` into the
caller's keys **whichever branch matched** — including the `callee in _METHOD_KINDS` branch. So a class method
named `increment_counter` that adds a key to its own `**kwargs` (the W08 shape, silent on its own) registers a
forwarder called `increment_counter` carrying that key, and every OTHER function in the module that calls the real
`increment_counter` inherits it. Measured: `DW06` and `DW08` each survive the full lane alone; applied together
the lane goes red with `llm.py:1777 passes 'email' to llm_requests_total` — a line in the DW06 plant, reported
because of a key that came from the DW08 plant. Fail-closed reporting at the wrong site is worse than silence to
debug. Severity 2, test-only, no estate occurrence.

### P3-4 — The module-mains destruction register still misses eleven spellings, none of them declared

`5d81811` genuinely widened the rule (f-string literal parts, implicit concatenation, `text()`, lowercase,
`sql.SQL(...)`, `ALTER TABLE … DROP`, SQL in a keyword or list argument, and `flushdb`/`flushall` including a
`getattr` spelling and an alias of the client or the method). Re-measured at `fe45c35` over 30 shapes
(`probes/mains_probe.py`): still missed — SQL built by `+` concatenation; SQL behind a leading `--` comment, a
`BEGIN;` or a CTE (all three follow from the deliberate start-of-string anchor); `DROP MATERIALIZED VIEW`,
`DROP TYPE`, `DROP EXTENSION` and `DROP OWNED`; `executescript` with the destruction after the first statement;
`execute_command("FLUSHALL")`; Redis `unlink`; and SQL bound to a variable first. The remote `remove` IS declared.
No live offender: the package passes both rules and the two `__main__` blocks delegate to argparse `main()`s.
Severity 3.

### P3-5 — The utils lane's verdict depends on another repo's WORKING TREE

`_sibling_emissions()` resolves `<workspace>/copilot-mro-obsm/copilot_mro` and parses the checked-out files. While
that tree was mid-edit the utils inventory lane went red on a copilot-mro line (`processing.py:577 passes
'tenant_id' to document_hub_processing_duration_seconds`) that the committed source does not contain. This is the
design working as intended — a cross-repo estate guard must read the estate — but it means a utils verdict is only
meaningful beside a NAMED sibling SHA, and a review or CI lane should read an archive, not the worktree. This
packet pins `ce545211`. Severity 3, process.

---

## The `fabb94c` args walk — SPEC for the flynapse-otel port (P3-2 / M-FAILURE-HOME)

`_every_link(exc) -> list[BaseException] | None`, `utils/_exception_text.py:234-263` at `fe45c35`. It feeds
WITHHOLDING only, never rendering, so no rendered field changes with it. Measured, not paraphrased
(`probes/args_walk.py`, 22 shapes, output in `args_walk_head.txt`):

1. **Worklist, not recursion.** `pending = [exc]`; `link = pending.pop()` (LIFO); `seen` is a set of `id(link)`;
   `found` is the emission order. No recursion, so no stack bound and no `RecursionError` on a deep chain.
2. **What each popped link enqueues, in this order:** `__context__`, then `__cause__`, each only when not `None`
   — a SUPPRESSED `__context__` (`raise X(...) from None`) is walked too, because that is exactly where the new
   exception's message quotes it; then, when the link `isinstance(..., BaseExceptionGroup)`, every member of
   `.exceptions`; then every exception `_held_in_args(link)` returns.
3. **`_held_in_args` is deliberately shallow.** It reads `link.args` inside `try/except Exception` and returns
   `[]` when that raises — note a `BaseException` from an `args` property PROPAGATES, by the same rule as the rest
   of the module. It returns `[]` unless the value `isinstance(..., tuple)` (a property returning a LIST yields
   nothing), and then filters `isinstance(arg, BaseException)` over the DIRECT elements only. It does not descend
   into a tuple, list, dict or set held in `args`, does not read instance attributes, and does not read
   `__notes__`.
4. **Termination.** `seen` by `id()` makes every cycle finite. `e.args = (e, inner)` and a mutual `a ↔ b` cycle
   each return in under a millisecond. Depth is bounded by the link counter, not by the walk's shape: 5,000 links
   of `args` nesting returns `None` in ~0 ms.
5. **The bound is a LINK COUNT, tested after the append.** `found.append(link)`, then
   `if len(found) > _MAX_LINKS: return None`, with `_MAX_LINKS = 256`. So **256 links are checked and 257 returns
   `None`** — measured: 255 exceptions in `args` plus the outer = 256 links, still checked and still correctly
   withheld; one more returns `None`. `None` makes every caller write `WITHHELD_MESSAGE` ("[message withheld: too
   much to check for exception text]"). This is a fail-closed switch, not an optimisation: a port that recurses,
   or that tests the bound before the append, changes which records are withheld whole. 100,000 exceptions in
   `args` cost 11 ms.
6. **Quoting is a separate layer.** `_partial_quotes` quotes STRING args, the `args` tuple's own repr, an
   `OSError`'s `filename` and `filename2`, each STRING in `__notes__`, a botocore
   `response["Error"]["Message"]`, and the first line of a multi-line `str()`. An exception the walk FINDS is
   withheld by its own `str()` and `repr()` under the delimiter rules — `_MIN_FREE_QUOTE = 8`, so a shorter
   single-argument quote is replaced only between delimiters (`KeyError('hunt2')` quoted as `x'hunt2'y` is
   deliberately not replaced).
7. **Measured clean:** the direct `args[1]` shape; two and three levels of `args` nesting; a group member holding
   one in `args`; a `__cause__` whose `args` hold one; an exception CLASS (not instance) in `args`; a
   `KeyboardInterrupt` in `args`; both cycles; and everything past the bound.
8. **Measured leaking** (the port should decide these deliberately rather than inherit them): an exception inside
   a tuple, list or dict inside `args`; one kept as an attribute by a custom `__init__`; one behind an `args`
   property returning a list; an exception object in `__notes__`; a non-exception wrapper in `args` whose
   `__str__` renders it. See P3-1.

**Points 1–5 are the contract.** `flynapse_otel/failure.py` must reproduce them exactly before
`UTILS_PARITY_SHA` moves past `fabb94c` and utils deletes its copy.

---

## Mutations

`mutant.sh` throughout (cold cache, baseline first, restore verified), on the `dec/` copy only, against the pinned
sibling. **18 distinct mutants: 12 KILLED, 6 SURVIVING** — one of the six is a declared limit and the other five
are the P2-1 classes above, each additionally confirmed against the FULL suite one at a time.

| mutant | what it removes / plants | aimed at | result |
|---|---|---|---|
| **IMA** | the fail-closed default of `_Labels._mention` (unreadable → `None`) | the inventory file | KILLED |
| **IMB** | a recognised constant-key write stops recording its key | the inventory file | KILLED |
| **IMD** | the own-scope check in `_own_nodes` | the inventory file | KILLED |
| **IMP1** | the single-binding count for a module constant | the inventory file | KILLED |
| **IMC** | a `_NOT_SEEN_BY_DESIGN` entry deleted (the register claims less than the docstring) | the inventory file | KILLED |
| **IMLA1** | the `_SQL_DESTRUCTION` payload rule | `test_module_mains_cannot_delete.py` | KILLED |
| **IMS1** | the new setup-phase `LoadedModuleWatch.enforce` (P3-3's fix) | `test_checkout_variant_pin.py` | KILLED |
| **IMX1** | `pending.extend(_held_in_args(link))` — the whole `fabb94c` walk | `test_stdout_sinks_withhold_exception_text.py` | KILLED |
| DA / DB / DC | the r8 decoys: an alias, a closure, a helper writes the label dict | the inventory lane | KILLED ×3 |
| DE | control: an undeclared family emitted from `llm.py` | the inventory lane | KILLED |
| DD | `getattr(svc, "increment_" + "counter")(…)` | the inventory lane | SURVIVED — **declared** |
| DK15 / DN11 / DW01 / DW06 / DW08 | the five P2-1 classes | the inventory lane, then the FULL lane | **SURVIVED** ×5 |

The 8 `IM*` are a sample of the implementer's 34, re-created from the diff and re-run independently: **8 of 8
killed**, so the implementer's "34 distinct, all killed" holds on the sample. A sixth combined run (all six
surviving plants at once) is what produced P3-3.

---

## Every r8 row, settled

`claims-utils-r8.md` carries 22 rows. This range answers ten of them; the rest are unchanged or were routed.

| r8 row | r8 state | seat in this range | now |
|---|---|---|---|
| U8-10 (P2-1) the label-key reader | PARTIAL | `b1d9834`, `5c7f81e`, `852de2e`, `6ea14ea`, `fffbf1a` | **REDESIGNED — 24 shapes closed, 0 regressions, the three r8 decoys now KILLED. Residual P2-1 (25 undeclared shapes).** |
| U8-21 (P3-1) an exception in `args` | OPEN | `fabb94c` | **SETTLED for the reported shape** (IMX1 red). Residual P3-1 (containers, attributes, `__notes__`, list-args, wrappers). |
| U8-12 residual P3-2 (a helper on another thread) | residual | `7dc9d6e` | **DECLARED and pinned both ways** — `executor.submit` → `interrupted`, `copy_context().run` → `success`; the `ContextVar.reset` `ValueError` declared on the same grounds. Closed. |
| U8-14 residual P3-3 (a swap in fixture setup then a skip) | residual | `cf3a92b` | **FIXED, not declared** — a `pytest_runtest_setup` wrapper enforces in a `finally`; the swap now ERRORs in setup. IMS1 red. Closed. |
| U8-17 (P3-4) the reserved set derived vs hand-typed | PARTIAL (M24 survived) | `e528cbe` | **SETTLED** — identity pin (`log_bridge._RESERVED_LOG_RECORD_ATTRIBUTES is _exception_text.STANDARD_RECORD_ATTRIBUTES`) plus a SOURCE pin that the shared set is built from a live `LogRecord().__dict__`. Red on every Python, not only 3.12+. (Note: `_RESERVED_ATTRIBUTES` at `log_bridge.py:119` derives from the pinned name, so the bridge's own seat is covered transitively; a hand-typed literal introduced at `:119` itself would be caught only by the content test.) |
| U8-15 residual P3-5 (the mains register) | residual | `5d81811` | **PARTLY SETTLED** — flush names and SQL payloads caught, the remote `remove` declared. Residual P3-4 (eleven spellings). |
| U8-15 residual P3-10 (the message overcounts) | residual | `fd28a4c` | **SETTLED** — plan corrected to four mutations. |
| U8-18 (P3-6) the "Known gaps" prose | ASSERTED (M25 survived) | `1a690d8` | **SETTLED** — the gap CLAIM is now structural (a bullet list held equal to `KNOWN_GAPS` and disjoint from `WIDENED_LEAK_SHAPES`); the caught-shapes paragraph stays prose by design. The claim M25 falsified is pinned. |
| U8-19 (G18-04) the series total | SETTLED | `179cc6d` (base) | unchanged; still pinned at 487,939 |
| U8-22 (P3-7) two live copies of the renderers | ASSERTED | not fixed | **ESCALATED to a real divergence** — see P3-2. The port is owed; the spec above is its input. |
| U8-07 `_exception_text.py` byte-identical to `1a42390` | SETTLED | `fabb94c` | **SUPERSEDED** — deliberately no longer identical (md5 `4c3c2437…` → `5b6899d5…`). The parity pin still reads `1a42390`, so nothing is red. |
| U8-13 (P3-8, P3-9), U8-11 | routed | — | still routed to the copilot-mro lane; unchanged by this range |
| U8-01 … U8-06, U8-08, U8-09, U8-16, U8-20 | SETTLED | untouched by the range | unchanged |

---

## What I tried to break and could not

- **The redesigned reader, 120 plants.** 19 RED, 72 REPORTED. Every `setattr`/`operator.setitem`/`dict.__setitem__`
  /`__setitem__`/`type().__setitem__` route, `|=` in both its display and `dict()` forms, `.update(**x)`,
  `.update(<list of pairs>)`, `.setdefault`, `**` splats at the call and inside a display, walrus displays,
  computed and f-string keys, `exec`/`eval`/`locals()`/`f_locals` in a function, `global`/`nonlocal`, match-mapping
  rest, `for` targets, `del`-then-rebind, annotated and conditional displays, `dict()` calls, dict subclasses,
  comprehensions, class bodies, lambdas, decorator expressions, nested/async/`self`/default-family forwarders, a
  forwarder calling through a bound-method alias, Enum members and `.value`, dict and list lookups, class
  attributes, module `__getattr__`, `TYPE_CHECKING` branches, two-level relative imports, `__all__` re-exports —
  each is red or reported with its line.
- **Implicit string concatenation does not defeat it** (`labels["e" "mail"]`, `"llm_probe" "_leak_total"`): both
  are single `Constant` nodes and both go red. A reader that matched on source text would have missed them.
- **The args walk's termination.** Cycles, 5,000-deep `args` nesting, 100,000 exceptions in one `args`, 20,000
  shared args across three chain links, and the exact bound (256 checked, 257 withheld) — all terminate, all
  fail closed.
- **The estate.** 24 emissions, 0 unresolved, identical at both ends of the range against the pinned sibling.
- **The implementer's own guards.** 8 of the 34 mutants re-created independently; 8 killed.

## What I did not test

- Any live collector, Weaviate, Cognito, AWS or Postgres path; no docker, no network, no DB writes outside
  `copilot_mro_test`.
- Python 3.12+ (`_MAX_LINKS` behaviour is version-independent; the reserved-set content check is not, which is why
  `e528cbe` added the identity and source pins).
- flynapse-otel's own suite under mutation — I read its parity pin and its `failure.py`, and measured the absence
  of `_held_in_args`; the fo lane owns the rest.
- The other 26 of the implementer's 34 mutants (an 8-sample was the owner's scope).
- copilot-mro at `16760afc`: everything here is measured against the pinned `ce545211`.

---

## Claims table

**Severity**: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process,
— = nothing owed. **Tier**: 0 = settled by a guard I SAW fail, 1 = consequential but reversible, 2 = irreversible
or estate-shaping. **Chunk**: F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|
| U9-01 | utils | `tests/unit/observability/test_legacy_family_inventory.py:222-431`, `:490-633`, `:705-786`, `:917-937` | Keys and families are read fail closed: any mention the reader does not recognise is reported with its line, not trusted (`b1d9834`, `5c7f81e`, `852de2e`, `6ea14ea`, `fffbf1a`) | 120 plants: 19 RED, 72 REPORTED, 25 silent (+4 correctly green); 24 shapes closed, 0 regressions; estate view byte-identical | `test_every_emission_shape_is_resolved_or_reported[*]`, `test_no_emission_shape_went_unresolved[*]`, `test_every_emitted_attribute_key_is_declared[*]`, `test_a_constant_resolves_through_the_module_that_binds_it` | **yes** — IMA, IMB, IMD, IMP1, IMC red; DA, DB, DC, DE red | 2 | 1 | F1 | **PARTIAL — P2-1** (25 shapes undeclared; 5 mutation-proved in the estate) |
| U9-02 | utils | `tests/unit/observability/test_legacy_family_inventory.py:336` | A chained assignment binds one display to several names and only the mentioned one is read | `DK15` survives the aimed lane and the FULL lane | none | **yes** — DK15 SURVIVES | 2 | 1 | F1 | **OPEN — P2-1** |
| U9-03 | utils | `tests/unit/observability/test_legacy_family_inventory.py:604-631` | A constant resolves through the import to the defining module without consulting the importing module's own rebindings | N10-N13, N18, N19, N21, Q11 silent; `DN11` survives the FULL lane | none | **yes** — DN11 SURVIVES | 2 | 1 | F1 | **OPEN — P2-1** |
| U9-04 | utils | `tests/unit/observability/test_legacy_family_inventory.py:705-786` | A forwarder referenced-not-called, decorated, renamed, `this`-bound or import-aliased is not read | W01-W04, W06, W08-W10, W12-W14 silent; `DW01`, `DW06`, `DW08` survive the FULL lane | none | **yes** — DW01, DW06, DW08 SURVIVE | 2 | 1 | F1 | **OPEN — P2-1** |
| U9-05 | utils | `tests/unit/observability/test_legacy_family_inventory.py:766, 770` | The forwarder table is keyed by bare function name and its keys are unioned in even on the `_METHOD_KINDS` branch | DW06 and DW08 each survive alone; together the lane reddens at DW06's line for DW08's key | — | **yes** — the combined run | 2 | 1 | F3 | **OPEN — P3-3** |
| U9-06 | utils | `utils/_exception_text.py:234-263`, `:266-276` | An exception held directly in another's `args` tuple is a chain link, so a quote of it is withheld (`fabb94c`) | 22-shape walk; the reported shape and its nesting are clean; bounds and cycles measured | `test_stdout_sinks_withhold_exception_text.py` (the `fabb94c` cases) | **yes** — IMX1 red | 2 | 0 | F1 | **SETTLED**; residual P3-1 |
| U9-07 | utils | `utils/_exception_text.py:266-276` | The walk is shallow by design: containers, attributes, list-valued `args`, `__notes__` objects and wrapper objects are not reached, and not declared | 5 measured leaks on the JSON line and the OTLP body | none | n/a — behaviour probe | 2 | 1 | F1 | **OPEN — P3-1** |
| U9-08 | utils ↔ flynapse-otel | `utils/_exception_text.py` (md5 `5b6899d5…`); `flynapse_otel/failure.py` at `ff20ca9`; `tests/unit/failure/test_failure_parity_with_utils.py:34` | The two renderers have diverged; the parity pin at `1a42390` hides it until it moves | `_held_in_args` absent from the port (grep count 0); utils no longer byte-identical to `1a42390` | flynapse-otel's parity test (not run by me) | n/a — measured | 3 | 1 | F2 | **OPEN — P3-2**; the walk spec above is the port's input |
| U9-09 | utils | `utils/weaviate_service.py:72-84`, `:163-176`, `:194-219` | A helper on a thread the door's context did not reach writes nothing and the door closes `interrupted` — declared, and pinned both ways (`7dc9d6e`) | docstrings and comments only (verified by a comment-stripped diff) | `test_a_helper_on_a_thread_the_door_did_not_reach_leaves_the_door_interrupted` | not sampled (IMW1 prepared, outside the 8-sample) | 3 | 0 | F2 | **SETTLED (declared)** |
| U9-10 | utils | `tests/conftest.py:46-56` | The loaded-module check also runs after SETUP, in a `finally`, so a fixture that swaps `sys.modules` and then skips ERRORs instead of reporting SKIPPED (`cf3a92b`) | the fifth probe and the `setup-skip` ending case | `test_a_sys_modules_swap_fails_the_test_whatever_its_body_did_next[setup-skip]`, `test_swap_in_setup_then_skip` | **yes** — IMS1 red | — | 0 | F2 | **SETTLED (fixed)** |
| U9-11 | utils | `utils/observability/log_bridge.py:99,119`; `tests/unit/observability/test_log_bridge_flattening.py` | The reserved set is held to the shared one by IDENTITY, and that set to a live `LogRecord().__dict__` in its SOURCE (`e528cbe`) | r8's surviving M24 is red on every Python now | `test_the_reserved_set_is_the_derived_one_not_a_copy_of_it` | implementer's M24-replay and M24c red (not re-sampled) | — | 0 | F3 | **SETTLED** |
| U9-12 | utils | `tests/unit/safety/test_module_mains_cannot_delete.py` | SQL payloads and `flush*` are caught; the remote `remove` is declared (`5d81811`) | 30-shape probe re-run at `fe45c35`: 19 caught, 11 missed and undeclared, no live offender | `test_destruction_without_a_destructive_callee_is_still_caught`, `test_sql_that_only_mentions_a_keyword_is_not_read_as_sql` | **yes** — IMLA1 red | 3 | 0 | F3 | **SETTLED**; residual P3-4 |
| U9-13 | utils | `tests/unit/observability/test_utils_logs_no_exception_text.py:28-45`, `:682-691` | The docstring's gap LIST is the register's keys, held equal and disjoint from the caught set (`1a690d8`) | r8's surviving M25 claim is now structural | `test_the_docstring_lists_exactly_the_known_gaps` | implementer's MG1/MG2 (not re-sampled) | — | 0 | F3 | **SETTLED** |
| U9-14 | utils | `docs/plans/utils-review-r8-batch.md` | `0e93618`'s message overcounted its mutations by one; corrected to four (`fd28a4c`) | read | n/a | n/a | — | 0 | F3 | **SETTLED** |
| U9-15 | utils | whole range | 14 commits, each green at its own HEAD, 0 skipped; the full lane at HEAD is green modulo copy-location artefacts | 1909 → 1968 passed per-commit; 1981/7/4 at HEAD on the pinned tree; **48/48 green read-only in the real tree**, `git status` unchanged | the suite | n/a (measurement) | — | 0 | F2 | **SETTLED (measured)** |
| U9-16 | utils ↔ copilot-mro | `tests/unit/observability/test_legacy_family_inventory.py:1023-1026` | The copilot-mro limb parses the sibling CHECKOUT, so a utils verdict is only valid beside a named sibling SHA | a mutation baseline flipped red on a `processing.py` line the committed source does not contain | — | n/a — measured | 3 | 1 | F3 | **OPEN — P3-5** (process; this packet pins `ce545211`) |

**Totals: 16 claims** — 8 SETTLED (7 by a guard I saw fail, 1 measured), 1 PARTIAL (U9-01), 7 OPEN
(U9-02..U9-05, U9-07, U9-08, U9-16). No claim is tier 2. No P0 and no P1.

---

## Future Improvements (candidates — the owner ruled P3s are not a new round)

- **Declare the 25 shapes** (P2-1). What is missing: `_NOT_SEEN_BY_DESIGN` names five limits while the reader
  cannot see twenty-five more, and the module docstring asserts the register is complete. Why it is this way: rounds
  6-8 each closed shapes by enumeration, and this round's redesign replaced that with fail-closed reading — but
  the register was not re-derived against a fresh probe corpus afterwards. The complete solution is the register
  entries in four families PLUS a test
  that holds the register to a checked-in corpus, so the register cannot drift behind the reader again.
- **Two small fixes if the batch prefers them to a declaration** (P2-1): the `len(parent.targets) > 1` condition
  at `:336`, and consulting the already-computed `bindings` before following an import in `_Modules.resolve`.
  Together they close twelve of the twenty-five. The W-family (eleven shapes) should be declared rather than chased.
- **Key the forwarder table by definition, not by bare name** (P3-3). What is suboptimal: `found[function.name]`
  merges unrelated functions that share a name, and the keys of one are unioned into the callers of another. Why:
  matching callers to forwarders by name is what makes a bare-name call site readable at all. The complete
  solution is to mark a name ambiguous as soon as two definitions of it differ in ANY field (today only
  `(param, index)` and `ambiguous` do that), so a wrapper named like a metric method makes the name unreadable
  instead of contributing its keys.
- **Decide the args walk's five remaining shapes** (P3-1) in the flynapse-otel port rather than inheriting them —
  a bounded container descent (the same `_MAX_LINKS` counter) would close the tuple/list/dict cases, and
  `__notes__` objects are a two-line addition. An `args` property returning a list and an arbitrary wrapper object
  are better declared.
- **Widen the mains register or declare the eleven** (P3-4). The start-of-string anchor is a deliberate choice
  (a log line naming `DROP TABLE` is not SQL), so the comment/`BEGIN;`/CTE cases should be declared; the four
  missing `DROP` objects and `execute_command("FLUSHALL")` are enumeration gaps worth closing.
- **Read the sibling from an archive in review and CI lanes** (P3-5), or record the sibling SHA in the lane
  header, so a utils result is reproducible while copilot-mro lanes are in flight.
