# Claims packet: flynapse-otel review r7 — detector (the answer to r6: narrowing withdrawn, qualified refusal types, ratchet baseline, literal policy, URL widening, P3s)

Independent adversarial review by Opus, 2026-09-22 (paused once by the owner, resumed; this is the final version). Read-only throughout: no code tree edited, checked out, stashed or committed. Every commit was extracted with `git archive`. The mutation battery ran in a durable extract (`~/.claude/scratch/obs-merge/otel-review-r7/c/4b48507`) through `mutant.sh`: one green baseline per aimed test set, then each mutant with `-B`, cold bytecode, restored; every mutated file was md5-verified against its `4b48507` blob afterwards (all MATCH). Ratchet experiments ran in a scratch git repo (`…/ratchet_ws/repo`).

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` (HEAD `df503c2` at the end; the range is fixed) | `main` | `5c7e1dc~1..4b48507` | `5c7e1dc` `5b86943` `575e1b9` `dd4cec5` `56b1814` `05e1a6e` `850bb9d` `4b48507` |

**How I ran it.**
- **Sibling repos.** Each extract had `utils`, `core` and `dashboard` symlinked beside it. The parity test reads utils `594327e` by `git show`.
- **Command.** From the extract root, every pytest through `/home/aditya/Code/pytest-slot.sh --`, one at a time: `DEBUG=false PYTHONPATH=<extract> PYTHONPYCACHEPREFIX=<per-sha> flynapse-otel/.venv/bin/python -m pytest -p no:cacheprovider`. Python 3.11.15, with no xdist in that venv, so every lane is serial.
- **Provenance.** `flynapse_otel.__file__` was printed inside the extract before each lane; rootdir was the extract.
- **Per-commit lanes.** `parallel-commits.sh -L -j 2`. The script cuts the summary line, so counts come from the progress dots.
- **Detector plants.** A harness scans one plant module per file: a `leak_*` function must produce a finding and a `clean_*` must not. Plants are in `~/.claude/scratch/obs-merge/otel-review-r7/attacks/`.

**Every commit is green at its own HEAD** (rc=0; 1 skipped = `test_root_anchoring`'s other-checkout proof, 1 xfailed = the declared SyntaxError header forgery):

| commit | 5c7e1dc | 5b86943 | 575e1b9 | dd4cec5 | 56b1814 | 05e1a6e | 850bb9d | 4b48507 | (d1e531f) |
|---|---|---|---|---|---|---|---|---|---|
| passed | 2346 | 2372 | 2381 | 2404 | 2428 | 2432 | 2485 | 2485 | 2576 |

**Verdict: FIX-FIRST — 0 P0 · 1 P1 · 4 P2 · 5 P3.**

The r6 answers hold in substance, and 26 of 26 mutants are red:
- The every-argument floor is sound against every rebinding I posed (13/13).
- The refusal proof refuses every alias, tuple, negation and annotation attack I posed (11/11 leaks caught, 5/5 legitimate spellings clean).
- The literal policy reader is never wider than execution (18 texts).
- The URL rule's r6 residuals are closed except where declared.
- The estate re-scan reproduces exactly: 0 missing, and the three new keys are over-reports.

Four things stop a clean pass:
- The P2-1 fix turned r6's attack 2 from fail-closed into fail-OPEN: a moved register without `moved_from` adopts the moved text as its own baseline (P1-1).
- A sanctioned refusal's `__cause__`/`__context__` ride into a body.
- Revoked builtin trust switches the namespace reads off.
- A raised class whose name starts with `_` is not read at all. This one is pre-existing and undeclared.

**Lesson #14 judgement.**
- **The narrowing.** The third attempt is a DESIGN, not a patch. The mechanism was REMOVED, not re-proven. What remains is a floor that needs no resolution (a call's value carries every argument's text): DT18, which drops the first argument, is red, and 13 rebinding shapes are caught. Beside it sits one ADDITIVE table (`return_carried`), whose resolution can only add taint. The price is three over-report keys estate-wide, each verified below to be an over-report. The rule is satisfied.
- **The ratchet baseline.** The ratchet's BASELINE mechanism is now on its third consecutive finding: r5 P2-2 (local refs), r6 P2-1 (no baseline at adoption) and r7 P1-1 (the fallback adopts moved text). The first two were P2s, so the rule is not yet triggered. But the pattern matches the G.53 lesson: each fix infers the baseline from repository shape, and the next review finds a shape the inference misreads. **Before patching P1-1, write down where a register's baseline is DECIDED ONCE.** One candidate: an explicit, reviewed `ADOPTED_AT = "<sha>"` constant, or a `moved_from` that the guard must state. Stop inferring it from `git log`.

**Adoption guidance.**
- **The SCAN (findings plus `reconcile`)** can be adopted now. Register the three new over-report keys, or better, give utils a span-safe bounded reader for its two outcome helpers. At a RAISE or BODY site, resolve an over-report by restructuring the site, never by a register entry (P3-3).
- **The RATCHET** should wait for P1-1. Until then every consumer guard passes `moved_from` on any register move, and reviewers read register moves by hand.

---
## Findings, ranked

### No P0

Estate exposure of every finding below is zero today. The re-scan and the per-finding estate counts are in each finding.

### P1-1 (tier 2, severity 1): a register moved without `moved_from` gets the MOVED text as its baseline, so r6's attack 2 now passes where r6 failed closed (575e1b9)

**Where.** `flynapse_otel/testing/exception_text/_ratchet.py:136-148`.
- When `path` is absent at the base and `moved_from` is not given, the baseline becomes `path` at the oldest commit after the base that ADDED it (`git log --full-history --diff-filter=A <base>..HEAD -- <path>`).
- With a pathspec, git cannot see a rename, because the old path is outside the pathspec.
- So a `git mv` plus an edit in one commit is an `A`, and that commit's content becomes the baseline.

**Measured** (scratch repo with `origin/master`). The base register has count 2 and one REPAIRED key. The branch commit is `git mv tests/guard/register.py tests/register_v2.py` + count 5, the repaired key re-added, and `REPAIRED = frozenset()`.
- `merge_base_text(repo, "tests/register_v2.py", "origin/master")` returns the MOVED text, and `ratchet_problems(...)` returns `[]`.
- With `moved_from="tests/guard/register.py"` it reports `GREW 2 -> 5`, two `NEW KEY` and `UN-REPAIRED`.
- At r6 the same shape raised `FileNotFoundError`, failing closed (r6 packet R6-09).
- A COPY (the old file kept, the new one widened) behaves the same.

The implementer's pins for the existing branches hold: DT04 (newest addition), DT05 (`moved_from` read at HEAD), DT06 (never-committed reads as "") and DT07 (HEAD rev-parse failure ignored) are all red. The move hole itself has no guard.

**Scenario.** An implementer tidies a repo's tests: moves the register into a new folder and repoints the guard's path. Any growth committed in the same commit is then invisible. The plan's "a move keeps its old one" holds only when the guard author cooperates, which is the assumption the ratchet exists to remove.

**Fix** (after the design note above).
- Make the adoption fallback explicit: the guard states `adopted=True` or `moved_from`, visible in the same diff as the move.
- In the fallback, run `git log -M --name-status` on the adding commit. Refuse when `path` is the target of an `R`/`C` whose source is not `moved_from`, or when the commit deletes another file the guard's loader accepts as a register.
- Pin both with the scratch shape above.

### P2-1 (tier 1, severity 2): a sanctioned refusal's `__cause__` / `__context__` is a body (5b86943)

**Where.** `_module.py:674-716` (`_visit_attribute`). `err.__cause__` has no rule of its own, so the value's token — `{EXC: {"body"}}` for a caught refusal — passes through. The same happens for `__context__`.

**Measured.** Policy `refusal_types={"<mod>.Refusal"}`; plants in `p_refusal2.py` and `p_refusal3.py`. Three plants are silent while their siblings are caught:
- `except Refusal as err: raise HTTPException(403, detail=str(err.__cause__))`;
- `except Refusal as err: return JSONResponse({"detail": str(err), "context": err.__context__})`;
- `if isinstance(err, Refusal): raise HTTPException(403, detail=f"{err}: {err.__context__}")`.

The same reads on a NON-refusal are caught (`p_brief.py` `leak_cause_read`, `leak_context_read`).

**Scenario.** core raises `raise Refusal("tenant not permitted") from exc` inside a handler, and an endpoint then writes `except Refusal as err: detail=f"{err} ({err.__cause__})"`. The 403 body carries the designed sentence plus psycopg's message with its bound values.

**Fix.** In `_visit_attribute`, read `__cause__`, `__context__` and `__traceback__` of a refusal-sanctioned value with `V.NOWHERE`: the chained exception is foreign, not designed. Add one corpus row per spelling.

### P2-2 (tier 1, severity 2): revoked builtin trust turns the namespace reads OFF — fail-open where every other revocation fails closed (pre-existing; 850bb9d extended the family)

**Where.** `_module.py:719-738` (`_visit_call`).
- `locals()`, `vars()`, `globals()` and `vars(obj)` are read only while `facts.trusted(name, node)`.
- A star import, an `exec` or a `globals()[…]` write ANYWHERE in the module revokes that trust.
- The call then falls through to "every argument counts", which for a zero-argument `locals()` is nothing.

**Measured.** `p_trusted.py` and `p_revoked.py` are identical except for one `from os.path import *`. Trusted: 4/4 caught. Revoked: 1/4 caught. `"{err}".format_map(locals())`, `log.error(vars(report))` and `log.error(globals())` are all SILENT; `report.__dict__` is still caught (an attribute path).

**Exposure.** 5 production modules in the estate carry a star import (utils 3, core 1, api 1). There are 0 namespace reads in production code. Every other consumer of revoked trust fails closed: readers are unsanctioned, refusal classes unproven, and `type`/`isinstance` read as helpers (over-reports).

**Fix.** Under revoked trust, read `locals()`/`vars()`/`globals()`/`vars(obj)` anyway: the builtin reading is the conservative one. Add rows for the revoked variants.

### P2-3 (tier 1, severity 2): the fixed-point decoder is quadratic inside the scan bound, on the emitting thread (56b1814 / 05e1a6e)

**Where.** `withholding.py:788-802` (`_decoded`). It makes up to `len(text)+2` passes, each an `unquote` of the whole component. A one-layer-per-pass chain (`%` + `25`×k) needs k passes.

**Measured** (`withhold_url_secrets`, load 12). On `GET /p?a=%2525…41 HTTP/1.1`:

| input | time |
|---|---|
| 8 KB | 0.14 s |
| 16 KB | 0.44 s |
| 32 KB | 0.96 s |
| 64 KB (just under `URL_SCAN_LIMIT`) | **4.9 s** |

The docstring's "bounded by the text's length" is true of the PASS COUNT, and that bound is what makes it quadratic. DT20 (three passes) and DT22 (scan limit off) are red, so the rule and the bound are pinned; the cost inside the bound is not.

**Scenario.** uvicorn's access line goes through this rule (`test_uvicorns_access_line_ships_without_an_inbound_query_credential`). With h11's 16 KB request-line limit, a hostile request line costs about 0.4 s of event-loop time.

**Fix.** Cap the passes (8 is generous for real encodings), and treat "still changing at the cap" as a credential: withhold the component whole, failing closed. Pin it with a timing row at the scan limit.

### P2-4 (tier 1, severity 2): a raised class whose name starts with an underscore is not a construction (pre-existing, undeclared; `_module.py:1420`)

**Where.** `_unwrap_raised` treats a raised `Call` as a construction only when `name[:1].isupper()`. `_WatchOver(…)` is therefore read as an ordinary call. Its arguments land in no helper slot (a class is not a function), so nothing is found.

**Measured** (`p_underscore.py`, telegram r5 input). At `4b48507` 5 of 7 plants are missed:
- `raise _WatchOver(f"watch ended ({error})") from error`;
- `raise _Private(str(error))`;
- `raise errors._Hidden(str(error))`;
- `exc = _WatchOver(str(error)); raise exc`;
- a name-mangled `__Mangled`.

The renamed `WatchOver` is caught, and so is a lowercase factory (`raise.factory-text`). The miss is identical at `34c814a` and `927a729`; the line dates from `d15350a`. The declared limits name "a class reached through a lowercase name or an attribute", and an underscore-then-capital class is neither.

**Exposure.** There are 64 `raise _Class(` sites across 7 repos. The ones with a caught name in their arguments are telegram-bot `document_watch.py:566,573` (through its `headline_of` reader) and copilot-mro `dispatcher.py:217,299` (a `ToolError`, not caught text), so there are 0 known live leaks.

**Fix.** `name.lstrip("_")[:1].isupper()`. Better, and failing closed: a raised call is a construction unless it resolves to a function in the scan. Add rows for the five shapes.

### P3s

- **P3-1 (the `4b48507` bounds: the ratio tests are not a proof against quadratic behaviour).**
  - DT24 re-finds EVERY anchor kind per token: the quadratic rescan per URL.
  - Its full URL file fails only `test_each_anchor_kind_is_searched_once_per_match_not_once_per_token`, the count test, and `test_the_scan_bound_keeps_the_cost_bounded`.
  - **Both ratio tests (20x and 100x) PASS under that quadratic mutant.**
  - So the regression the brief asks about would hide under the ratio bounds; the COUNT tests catch it.
  - Loosening the ratios lost nothing, because they never proved more than a constant factor. The docstrings' "far under a quadratic's cost" should instead say the count tests carry the quadratic proof.
- **P3-2 (metric attributes are declared to a seat that does not exist).**
  - The package docstring (`__init__.py:88-89`) calls metric attributes "the export boundary's job".
  - `bootstrap.py` withholds spans and logs only, and `registry._lint_attributes` refuses forbidden KEYS "whatever their value".
  - `counter.add(1, {"error": str(exc)})` and `attributes={"error.message": str(exc)}` ship (`p_brief.py`). Exposure in production code is 0: the six-tree `rg` hits are e2e reporters.
  - **Fix:** give the registry a value lint, or read `.add`/`.record` attributes as a sink, and correct the declaration.
- **P3-3 (telegram r5 P2-1 is NOT a detector gap).**
  - The eighth telegram finding is by design: under R-EVERY-ARGUMENT, `_failure_detail(exc)` flows into a raise.
  - A register entry at a RAISE or BODY site is blind to a same-site regression by construction: same key, same site text. And a bounded reader cannot sanction those sinks.
  - **Fix (docs):** the docstring should say that an over-report at a raise or body site is resolved by restructuring the site (inline `type(exc).__name__`), as telegram did.
- **P3-4 (telegram r5 P2-2 is NOT a detector gap).**
  - The chain half — `from exc`, or the implicit `__context__` of ANY raise inside an `except` — carries the exception OBJECT, not text. Flagging every raise-in-except would over-report estate-wide.
  - The chain's leak paths are the RENDERERS, which are caught (`format_exception`, `logger.exception`, `exc_info=`). The export seats withhold the chain: `frames_only` keeps the leading block's headers, and `withheld_quotes` walks `__cause__`/`__context__`.
  - For a repo with no withholding renderer, its own `unchained` guard is the right seat.
  - **Fix (docs):** declare the chain in the docstring's limits.
- **P3-5 (`load_policy` hygiene).**
  - A module-level `exec(...)`, `globals()[...] = ...` or `setattr(sys.modules[__name__], ...)` in the BASE text is read as if absent (L2, L3 and L13 are ACCEPTED as the narrow policy).
  - That is the fail-closed direction: the executed current policy is wider, and it is flagged.
  - **Fix:** `_check_uses` could refuse the three spellings outright.

---
## What I tried to break and could not

- **The every-argument floor** (`p_floor.py`, 13 plants). A constant-returning helper reached through a module `setattr`, `types.MethodType`, a constructor-injected override, a lambda, keyword-only and `*args`/`**kwargs` calls, a nested call, a class constructor, a `partial`, an external module's function and a dict dispatch: all caught. DT18 (first argument dropped) is red.
- **The refusal proof** (`p_refusal2.py`, `p_refusal3.py`).
  - Caught: a tuple with a stranger, a refusal in a LOG, a negated `isinstance`, an `else` branch, a stored `isinstance` result, a read after the `if`, an `elif` stranger, `type(err) is not`, a ternary, `issubclass`, a local subclass, `self.Refusal`, an annotation of a stranger or a union, and a refusal BUILT from caught text or from the caught object.
  - A local alias rebinding anywhere un-proves the class module-wide, which fails closed.
  - Clean, as they should be: the five legitimate spellings.
  - DT01 (tail match), DT02 (rebound names off), DT03 (`revoked_all` ignored), DT12 (undefined refusal allowed) and DT13 (bare names allowed) are red.
- **The brief's list** (`p_brief.py`, 49 plants; 44 caught).
  - Rebinding and formatting: `m = str(exc)` rebound through a helper, and twice locally; `format_map`; `%` with a value, a tuple and a dict.
  - Reading the exception: `exc.args[0]`, unpacked args, `format_exception`/`_only`, `repr`, `!r`, `ascii`, `format`, `__str__()`, `__notes__` (also joined), `__cause__`/`__context__` of a plain exception, a `__traceback__` walk, `with_traceback`, `sys.exc_info()[1]`, `except*` (the group and its members).
  - Sinks: a chained raise with the text; span `set_attribute`/`set_attributes`/`add_event`; `getattr(log, "error")` and `getattr(log, level)`; `print(file=stderr)`; `extra=`; `bind()`; `log.log`; `warnings.warn`; `os.write`.
  - Carriers: bytes, a lambda helper, a dict comprehension, a walrus.
  - The 5 misses: the chain half (by design, P3-4), the metric label ×2 (P3-2), and `exec`/`eval` of a string (declared).
- **The literal policy reader** (18 texts).
  - Refused: a post-assignment `update`, `**kw`, a builder, a foreign import, a module alias, a name bound twice, chained targets, an `IfExp`, a generator, a walrus, `dict(**a)`, handing the name to a call, list `+`.
  - Accepted, as documented: a field read, `|` unions, string literals.
  - An env-widening in the CURRENT module against an identical base text is flagged `NEW READER 'x'`.
  - DT14 (`_check_uses` off) and DT15 (a foreign import followed) are red.
- **The mro r7 plants.** `vars(report)` of a local object is caught (DT17 red); the setdefault chain is pinned (DT16 red).
- **Sites, dates and never-readers.** DT19 (site hash cut at 400), DT08 (other date spellings skipped), DT09 (no NFKC before dates) and DT10 (frames renderers dropped from the never-readers) are all red.
- **URL residuals** (`url/url7.py`, r6's cases re-posed).
  - 13 of 15 are now held: quadruple and quintuple encoding; `pw`/`pin`/`sid`/`access_code`/`refresh`/`bearer`; `＆`/`？`; the JSON `&`; the fullwidth `ｔｏｋｅｎ`.
  - V05 (a newline) and V38 (a Slack path) ship, both DECLARED (g111 plan :832-835). So do the Bearer line, the schemeless DSN and a bare value, all declared.
  - A Postgres host is now kept; the git+ssh host is still lost (declared :830).
  - DT20, DT21 (8→2 words), DT25 (JSON escape) and DT26 (fullwidth anchor) are red.
- **`_vetted`.** 23 container and object shapes through `_safely_vetted` are all held. set, frozenset, deque, namedtuple and the mapping keys are reduced; dataclass, object, array, bytearray, memoryview, generator, exception and `UserString` become `<unvetted>`. DT23 (an unknown container passes through) and DT22 (scan limit off) are red.
- **Estate re-scan (R7-18).**
  - Current heads: utils-obsm `179cc6d`, core-obsm `b730a95`, api-obsm `2d49c3f`, copilot-mro-obsm `557a178f`, shift-optimizer `2a8e3de`, telegram-bot `47a08b7`.
  - Policy `failure_fields`; `de501a8` vs `4b48507`.
  - **0 missing in all six.** NEW is exactly the three claimed keys: utils `EmbeddingService._embed` and `_traced_weaviate.decorate.traced` (1 each), and copilot-mro `build_document_source_answer_binding.handler` (2).
  - Read at those heads, all three are over-reports. `_embedding_failure_outcome` and `_weaviate_failure_outcome` return an `isinstance`-chosen constant, and `_finish_*_span` reads `error` only for `type(error).__name__`. `failure_text` returns `f"{what} failed ({type(exc).__name__})"`, and `state` is tainted flow-insensitively through `state["error"]`.
- **Corpus (R7-19).**
  - 1595 rows at `4b48507`: 1559 at `5c7e1dc`, 1574 at `5b86943`, 1595 from `850bb9d`. The brief said 1597.
  - The r6 families are present as the plan says: proof 40, proof-text-free 38, returns 25, chain 28, refusal 15 (11 leak, 4 clean), mro7var 9 (1 limit).
- **Moving a merge base with one hunk.**
  - A guard hunk can change `against` to a remote-tracking ref at HEAD and add `base_may_be_head=True`, or delete the call. Both are inherent, since the guard is code, and both show in review as a guard edit.
  - What P1-1 adds is a move that needs NO guard change beyond the path.
  - Deleting a register and re-adding it larger does not reset the baseline (DT04 red).

## What I did not test

- The implementer's N/Q/B/F/D/E mutation tables, row by row. I ran 26 independent mutants instead.
- Python 3.12+ syntax, and the live bootstrap.
- Kill REASONS per mutant. `mutant.sh` records only the result line. The kills are aimed; I re-ran DT24 with its output kept, to settle P3-1.
- telegram-bot's own policy (the 7→8 count). I re-scanned under the `failure_fields` policy only; P3-3 answers the question structurally.

---
## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier is §2.3a's: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk: F1 = contract and privacy; F3 = residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7-01 | flynapse-otel | `_scan.py:337-403`, `_module.py:719-798` (5c7e1dc) | Narrowing withdrawn: a call's value carries EVERY argument's text; one additive `return_carried` table | r6 P1-1, lesson #14 | 13/13 rebinding shapes caught (`p_floor.py`); no resolution to defeat; the table only adds | corpus `rev:otel-r6/proof*` | yes: DT18 red | 1 | 0 | F1 | **SETTLED** (design, not patch) |
| R7-02 | flynapse-otel | `_scan.py:194-269`, `_model.py:289-294`, `:313-327` (5b86943) | Refusal types are qualified names, matched only through a PROVEN class; bare, builtin and undefined names refused | r6 P1-2 | 11 leak plants caught, 5 legitimate spellings clean | `test_exception_text_policy.py`, corpus `rev:otel-r6/refusal` | yes: DT01, DT02, DT03, DT12, DT13 red | 1 | 0 | F1 | **SETTLED** |
| R7-03 | flynapse-otel | `_module.py:674-716` | A sanctioned refusal's `__cause__`/`__context__` inherit the body sanction | (unexamined by the implementer) | 3 plants ship the chained exception in a body | none | not applicable | 2 | 1 | F1 | **OPEN** (P2-1) |
| R7-04 | flynapse-otel | `_ratchet.py:77-153` (575e1b9) | `merge_base_text` never returns None: base → `moved_from` at the base → oldest adding commit → raise | r6 P2-1 | Scratch repo: `git mv` + widen, no `moved_from` → the moved text IS the baseline, `[]`; r6 raised | `test_exception_text_ratchet.py` | yes, for the stated branches: DT04, DT05, DT06, DT07 red; the move hole has no guard | 1 | 2 | F1 | **REFUTED for the move case** (P1-1) |
| R7-05 | flynapse-otel | `_model.py:357-533` (dd4cec5) | `load_policy` reads the base literally; foreign imports, other calls, double bindings and later mutation refused; `Policy`/`BoundedReader` frozen | r6 P2-2 | 18 texts behave as documented; `exec`/`globals()`/`setattr` read as absent (the narrow direction) | `test_exception_text_policy.py` | yes: DT14, DT15 red | 1 | 0 | F1 | **SETTLED** (P3-5 hygiene) |
| R7-06 | flynapse-otel | `withholding.py:788-802` | Decoding to a true fixed point, "bounded by the text's length" | r6 P2-3 (V13) | Quadratic: a 64 KB chain costs 4.9 s inside the scan bound; 16 KB costs 0.44 s | url tests | the rule yes (DT20 red); its cost no | 2 | 1 | F1 | **PARTIAL** (P2-3) |
| R7-07 | flynapse-otel | `tests/…url_secrets.py:616-650` (4b48507) | Cost bounds loosened: 10x→20x, 40x→100x | flakes under load | DT24 (a quadratic per-token re-find) passes BOTH ratio tests; only the count test and the scan-bound timing fail | `test_each_anchor_kind_is_searched_once_per_match_not_once_per_token` | yes: DT24 red, via the count test only | 3 | 0 | F1 | **SETTLED** (the count test is the proof; P3-1 docs) |
| R7-08 | flynapse-otel | `_module.py:719-738` | Namespace reads only under builtin trust | (pre-existing) | A star import silences `locals()`/`vars(obj)`/`globals()` reads (3/4 missed vs 4/4) | none | not applicable | 2 | 1 | F1 | **REFUTED** (P2-2) |
| R7-09 | flynapse-otel | `__init__.py:88-89`; `registry.py:77-87` | Metric attributes are "the export boundary's job" | docstring | No metrics seat exists; key lint only; 2 plants ship; estate exposure 0 | none | not applicable | 2 | 1 | F1 | **OPEN** (P3-2) |
| R7-10 | flynapse-otel | `_module.py:338-358`, `:730-738` (850bb9d) | N20 setdefault chain and N15 `vars(obj)` caught; N01–N04 and N18 declared | mro r7 | `vars(report)` caught (`p_trusted.py`) | corpus `rev:otel-r6/mro7var` | yes: DT16, DT17 red | 2 | 0 | F1 | **SETTLED** |
| R7-11 | flynapse-otel | `_model.py:42-45`; `_ratchet.py:22-30`, `:61-71` (850bb9d) | Whole-source sites; non-ISO dates refused after NFKC | r6 P3 | mutants | ratchet and policy tests | yes: DT08, DT09, DT19 red | 3 | 0 | F1 | **SETTLED** |
| R7-12 | flynapse-otel | `_model.py:215-220` | `_NEVER_READERS` derived from the vocabulary | r6 P3 (a drifting copy) | builtins ∪ MESSAGE ∪ FRAMES ∪ SYS | policy tests | yes: DT10 red | 3 | 0 | F1 | **SETTLED** |
| R7-13 | flynapse-otel | `withholding.py:707-732`, `:325` (05e1a6e) | `_vetted` walks set/frozenset/deque; any other object is `<unvetted>`; a 64 KB scan bound that fails closed | r6 P3 (B14) | 23 shapes held | url and exception-text log tests | yes: DT22, DT23 red | 2 | 0 | F1 | **SETTLED** |
| R7-14 | estate | utils `EmbeddingService._embed`, `_traced_weaviate.decorate.traced`; copilot-mro `build_document_source_answer_binding.handler` | The three new keys are over-reports of the withdrawn text-free rule | implementer | Read at the current heads: constant or class-name returns | none | not applicable | 3 | 1 | F1 | **SETTLED** |
| R7-15 | telegram-bot / flynapse-otel | telegram r5 P2-1 | Is the eighth finding at `56b1814` a detector gap? | telegram reviewer | By design (R-EVERY-ARGUMENT at a raise site); resolved by restructuring the site | none | not applicable | 3 | 1 | F1 | **SETTLED: not a gap** (P3-3 docs) |
| R7-16 | telegram-bot / flynapse-otel | telegram r5 P2-2 | Is the unread chain half a detector gap? | telegram reviewer | The chain is an object; renderers are caught; export seats withhold it | none | not applicable | 3 | 1 | F1 | **SETTLED: not a gap** (P3-4 docs) |
| R7-17 | flynapse-otel | all 8 commits (+ `d1e531f`) | Each commit green at its own HEAD | process | 2346 → 2576 passed, rc=0 everywhere | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |
| R7-18 | estate | six consumer trees at their current heads | 0 missing vs `de501a8`; 3 new keys | implementer | Reproduced exactly | none | not applicable | 3 | 1 | F1 | **SETTLED** |
| R7-19 | flynapse-otel | `tests/fixtures/exception_text/corpus.json` | The r6 plants are rows | implementer | 1595 rows; the six r6 families present with the stated counts | the corpus test | not applicable | 3 | 1 | F1 | **SETTLED** (count 1595, not the brief's 1597) |
| R7-20 | flynapse-otel | `_module.py:1420` (`_unwrap_raised`) | A raised `Call` is a construction when its tail name starts with an uppercase letter | (pre-existing, `d15350a`) | 5 of 7 underscore-class plants missed; 64 `raise _Class(` sites in the estate; 0 known live leaks | none | not applicable | 2 | 1 | F1 | **OPEN** (P2-4, undeclared) |

**Tier 0 (settled by guards I SAW fail):** R7-01, R7-02, R7-05, R7-07, R7-10, R7-11, R7-12, R7-13. These properties do not go to Fable. R7-04's stated branches are tier 0 too (DT04–DT07); its move case is not.

---
## Open claims, tier 2 first

**Tier 2**
1. **R7-04 (P1-1): the ratchet adopts a moved register's text.** Write down where the baseline is decided once, then fix.

**Tier 1**
1. **R7-20 (P2-4):** underscore-prefixed raised classes are unread (undeclared; telegram's `_WatchOver` shape).
2. **R7-03 (P2-1):** a refusal's `__cause__`/`__context__` reaches a body.
3. **R7-08 (P2-2):** namespace reads are off under revoked trust.
4. **R7-06 (P2-3):** the quadratic decoder inside the scan bound.
5. **R7-09 (P3-2):** metric attributes are declared to a seat that does not exist.
6. **Docs:** P3-1 (ratio vs count), P3-3/P3-4 (the telegram answers), P3-5 (literal-reader hygiene).

---
## Appendix: mutation battery (26 mutants of `4b48507`, plus one re-run with output kept)

`~/.claude/scratch/obs-merge/otel-review-r7/mut/dt/`. Each mutant was aimed at the test files that own its behaviour and run with `-x` and cold bytecode. A baseline was run once per distinct test set, and every one was green. All 26 are red, and every restore matched the `4b48507` blob.

| mutant | what it breaks | result |
|---|---|---|
| DT01 | refusal classes matched by tail again | KILLED |
| DT02 | the rebound-names check off | KILLED |
| DT03 | `revoked_all` ignored for classes | KILLED |
| DT04 | the NEWEST addition is the baseline | KILLED |
| DT05 | `moved_from` read at HEAD | KILLED |
| DT06 | a never-committed register reads as "" | KILLED |
| DT07 | a HEAD rev-parse failure ignored | KILLED |
| DT08 | non-ISO date spellings skipped | KILLED |
| DT09 | no NFKC before dates | KILLED |
| DT10 | frames renderers dropped from the never-readers | KILLED |
| DT11 | the reader home check off | KILLED |
| DT12 | a refusal the scan does not define allowed | KILLED |
| DT13 | bare refusal names allowed | KILLED |
| DT14 | `_check_uses` off | KILLED |
| DT15 | a foreign import followed | KILLED |
| DT16 | the setdefault chain not a store | KILLED |
| DT17 | `vars(obj)` fields not read | KILLED |
| DT18 | the first argument of a call dropped | KILLED |
| DT19 | the site hash cut at 400 characters again | KILLED |
| DT20 | decode three passes only | KILLED |
| DT21 | continuation 8 → 2 words | KILLED |
| DT22 | the scan limit off | KILLED |
| DT23 | an unknown container passes through `_vetted` | KILLED |
| DT24 | every anchor kind re-found per token (quadratic) | KILLED — by `test_each_anchor_kind_is_searched_once_per_match_not_once_per_token` and `test_the_scan_bound_keeps_the_cost_bounded` only; **both ratio tests passed** |
| DT25 | the JSON `\uXXXX` escape not decoded | KILLED |
| DT26 | the fullwidth anchor dropped | KILLED |
