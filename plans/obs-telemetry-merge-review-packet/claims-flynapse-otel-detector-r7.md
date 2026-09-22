# Claims packet: flynapse-otel review r7 — detector (the answer to r6: narrowing withdrawn, qualified refusal types, ratchet baseline, literal policy, URL widening, P3s)

**PARTIAL — in progress (PAUSED by the owner 2026-09-22; resume from `~/.claude/scratch/obs-merge/otel-review-r7/PAUSED.md`).** Independent adversarial review by Opus, 2026-09-22. Read-only throughout: no code tree edited, checked out, stashed or committed. Every commit was extracted with `git archive` into a private scratch copy; every mutation runs in scratch through `mutant.sh` (baseline first, md5-verified restore). The detector mutation battery (27 mutants, specs written) had NOT started at the pause; every row below marked "Mutation-proved? no (TODO)" is waiting on it.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` (HEAD moving: `df503c2` at the pause, a live implementer) | `main` | `5c7e1dc~1..4b48507` | `5c7e1dc` `5b86943` `575e1b9` `dd4cec5` `56b1814` `05e1a6e` `850bb9d` `4b48507` |

**How I ran it.** Each commit extracted to `scratchpad/otel-review-r7/c/<sha>` with `utils`, `core`, `dashboard` symlinked beside (the parity test reads utils `594327e` by `git show`; that SHA exists in both `utils` and `utils-obsm`). Command from the extract root, every pytest through `/home/aditya/Code/pytest-slot.sh --`: `DEBUG=false PYTHONPATH=<extract> PYTHONPYCACHEPREFIX=<per-sha> flynapse-otel/.venv/bin/python -m pytest -p no:cacheprovider`. Python 3.11.15; no xdist in that venv, so every lane is serial. `flynapse_otel.__file__` pointed into the extract on every run (printed before each lane); rootdir was the extract. Per-commit lanes ran with `parallel-commits.sh -L -j 2`, logs at `scratchpad/otel-review-r7/pc/<sha12>.log` (counts derived from the progress dots; the summary line is cut by the script).

**Every commit is green at its own HEAD** (rc=0; 1 skipped = `test_root_anchoring`'s other-checkout proof, 1 xfailed = the declared SyntaxError header forgery):

| commit | passed | rc |
|---|---|---|
| 5c7e1dc | 2346 | 0 |
| 5b86943 | 2372 | 0 |
| 575e1b9 | 2381 | 0 |
| dd4cec5 | 2404 | 0 |
| 56b1814 | 2428 | 0 |
| 05e1a6e | 2432 | 0 |
| 850bb9d | 2485 | 0 |
| 4b48507 | 2485 | 0 |
| d1e531f (range B end, baseline) | 2576 | 0 (55 s) |

**Verdict so far: FIX-FIRST (provisional — 0 P0 · 1 P1 · 3 P2 · 5 P3; the mutation battery and the corpus re-scan are still owed).** The r6 answers hold in substance: the every-argument floor is sound against every rebinding I posed (13/13), the refusal proof refuses every alias/tuple/negation/annotation attack I posed (11/11 leaks caught, 5/5 legitimate spellings clean), the literal policy reader is never wider than execution (18 shapes), and the URL rule's r6 residuals are closed as claimed except where declared. What stops a clean pass: the P2-1 fix turned r6's attack 2 from fail-closed into fail-open (a moved register without `moved_from` adopts the moved text as its own baseline), a sanctioned refusal's `__cause__`/`__context__` ride into a body, and the revoked-builtin-trust mechanism fails OPEN for namespace reads.

**Lesson #14 judgement (the narrowing).** The third attempt is a DESIGN, not a patch: the mechanism was removed, not re-proven. What remains is a sound floor (a call's value carries every argument's text, with no resolution to defeat — verified on 13 rebinding shapes, `p_floor.py`) plus one ADDITIVE table (`return_carried`) whose resolution can only add taint, never remove it. The cost (three over-report keys estate-wide, each verified below to be an over-report) is paid in registers or bounded readers, and the package docstring says so. This satisfies the rule.

---
## Findings, ranked

### No P0

### P1-1 (tier 2, severity 1): a register moved without `moved_from` gets the MOVED text as its baseline — r6's attack 2 now passes where r6 failed closed (575e1b9)

**Where.** `flynapse_otel/testing/exception_text/_ratchet.py:136-148`: when `path` is absent at the base and `moved_from` is not given, the baseline is `path` at the oldest commit after the base that ADDED it (`git log --full-history --diff-filter=A <base>..HEAD -- <path>`). With a pathspec, git cannot see a rename (the old path is outside the pathspec), so a `git mv` + edit in one commit is an `A` — and that commit's content becomes the baseline.

**Measured** (`scratchpad/otel-review-r7/ratchet/ws/repo`, a scratch clone with `origin/master`): base register count 2 with one REPAIRED key; branch commit `git mv tests/guard/register.py tests/register_v2.py` + count 5, the repaired key re-added, `REPAIRED = frozenset()`.
- `merge_base_text(repo, "tests/register_v2.py", "origin/master")` → returns the MOVED text; `ratchet_problems(...)` → `[]`.
- with `moved_from="tests/guard/register.py"` → `GREW 2 -> 5`, two `NEW KEY`, `UN-REPAIRED`.
- At r6 (`927a729`, `missing_ok` absent) the same shape raised `FileNotFoundError` (fail closed; r6 packet R6-09).

**Scenario.** An implementer moves a repo's register into a new folder while "tidying" and grows it in the same commit; the guard's `moved_from` is not passed (the guard is edited anyway to point at the new path). The ratchet is green. The plan's claim "a move keeps its old one" holds only when the guard author cooperates, which is what the ratchet exists not to assume.

**Fix.** Make the adoption fallback explicit and rename-aware: (a) require `adopted=True` (or `moved_from`) from the guard before the fallback is used, so a reviewer sees the flag in the same diff as the move; (b) in the fallback, read the adding commit's full `--name-status -M` diff and refuse when `path` is the target of an `R`/`C` whose source is not `moved_from`, or when the commit also deletes a file that parses as a register. Pin both with the scratch shape above.

### P2-1 (tier 1, severity 2): a sanctioned refusal's `__cause__` / `__context__` is a body (5b86943)

**Where.** `_module.py:674-716` (`_visit_attribute`): for `err.__cause__` the attribute has no rule of its own, so the value's token — `{EXC: {"body"}}` for a caught refusal — passes through. Same for `__context__`.

**Measured** (`p_refusal2.py`, `p_refusal3.py`, policy `refusal_types={"<mod>.Refusal"}`): three plants silent while their siblings are caught:
- `except Refusal as err: raise HTTPException(403, detail=str(err.__cause__))`
- `except Refusal as err: return JSONResponse({"detail": str(err), "context": err.__context__})`
- `except Exception as err: if isinstance(err, Refusal): raise HTTPException(403, detail=f"{err}: {err.__context__}")`
The same reads on a NON-refusal are caught (`p_brief.py` `leak_cause_read`, `leak_context_read`).

**Scenario.** core: `raise Refusal("tenant not permitted") from exc` inside a handler, then an endpoint's `except Refusal as err: detail=f"{err} ({err.__cause__})"` — the designed sentence plus psycopg's message (with bound values) in the 403 body.

**Fix.** In `_visit_attribute`, when `attr in ("__cause__", "__context__", "__traceback__", "__notes__")` and the value's token is sanctioned by a refusal, emit the read with `V.NOWHERE` (the chained exception is foreign, not designed). One corpus row per spelling.

### P2-2 (tier 1, severity 2): revoked builtin trust turns the namespace reads OFF — fail-open where every other revocation fails closed (850bb9d / pre-existing)

**Where.** `_module.py:719-738` (`_visit_call`): `locals()`, `vars()`, `globals()` and `vars(obj)` are read only while `facts.trusted(name, node)`; a star import, `exec` or a `globals()[…]` write anywhere in the module revokes trust, and the call then falls through to "every argument counts" — which for a zero-argument `locals()` is nothing.

**Measured** (`p_trusted.py` vs `p_revoked.py`, identical but for `from os.path import *`): trusted 4/4 caught; revoked 1/4 — `"{err}".format_map(locals())`, `log.error(vars(report))`, `log.error(globals())` all SILENT; `report.__dict__` still caught (an attribute path). The r6 packet's `format_map(locals())` case in `p_brief.py` went silent the same way when an `exec` plant shared the module.

**Exposure.** 5 production modules in the estate carry a star import (utils 3, core 1, api 1); 0 namespace reads in production code today. Fail-closed for `type`/`isinstance` (over-reports, correct), fail-open for the namespace reads (wrong direction).

**Fix.** Under revoked trust, read `locals()`/`vars()`/`globals()`/`vars(obj)` ANYWAY (the revocation means "cannot trust it is the builtin", and the builtin reading is the conservative one). Rows for the revoked variants.

### P2-3 (tier 1, severity 2): the fixed-point decoder is quadratic inside the scan bound, on the emitting thread (56b1814 / 05e1a6e)

**Where.** `withholding.py:788-802` (`_decoded`): up to `len(text)+2` passes, each an `unquote` of the whole component; a one-layer-per-pass chain (`%` + `25`×k) needs k passes.

**Measured** (`withhold_url_secrets`, load 12): `GET /p?a=%2525…41 HTTP/1.1` — 8 KB 0.14 s, 16 KB 0.44 s, 32 KB 0.96 s, 64 KB (just under `URL_SCAN_LIMIT`) **4.9 s**. The docstring's "bounded by the text's length" is true of the PASS COUNT, which is the quadratic bound.

**Scenario.** uvicorn's access line goes through this rule (`test_uvicorns_access_line_ships_without_an_inbound_query_credential`); h11's request-line limit (16 KB) gives ~0.4 s of event-loop time per hostile request line.

**Fix.** Cap the passes (8 is generous for real encodings) and treat "still changing at the cap" as a credential: withhold the component whole (fail closed). Pin with a timing row at the scan limit.

### P3s

- **P3-1 (docs, 4b48507 bounds).** The 20x/100x ratios are constant-factor smoke; the quadratic proof is the COUNT-based pair (`test_each_anchor_kind_is_searched_once_per_match_not_once_per_token`, `test_a_query_continued_past_a_space_walks_each_following_word_once`). The loosening cannot hide a rescan-per-URL regression (the counts pin it — mutant DT24 is written to prove that; not yet run), but a 2–5x constant regression now fits under either bound, as it did under the old ones. Say so in the docstring instead of "far under a quadratic".
- **P3-2 (docs).** Metric attributes are declared "the export boundary's job", but the boundary has NO metrics seat: `bootstrap.py` withholds spans and logs only; `registry._lint_attributes` refuses forbidden KEYS "whatever their value". `counter.add(1, {"error": str(exc)})` ships (`p_brief.py`, 2 plants). Exposure 0 in production code (rg over six trees; hits are e2e reporters). Either give the registry a value lint (no free text beyond a length/shape bound) or have the detector read `.add`/`.record` attributes as a sink; and stop declaring it to a seat that does not exist.
- **P3-3 (docs, telegram r5 P2-1).** The eighth telegram finding is by design (R-EVERY-ARGUMENT: `_failure_detail(exc)` into a raise). A register entry at a RAISE or BODY site is blind to a same-site regression by construction (same key, same site text), and a bounded reader cannot sanction those sinks. The docstring should say: an over-report at a raise/body site is resolved by restructuring the site (inline the class name), never by a register entry. NOT a detector gap.
- **P3-4 (docs, telegram r5 P2-2).** The chain half (`from exc`, or the implicit `__context__` of ANY raise inside an except) carries the exception OBJECT, not text; the detector reads text, and flagging every raise-in-except would be a whole-estate over-report. The leak paths of a chain are the RENDERERS, which are caught (`format_exception`, `logger.exception`, `exc_info=`), and the export seats withhold the chain (`frames_only` keeps the leading block's headers; `withheld_quotes` walks `__cause__`/`__context__`). For a repo with no withholding renderer (telegram-bot) its own `unchained` guard is the right seat. NOT a detector gap; declare the chain in the docstring's limits.
- **P3-5 (docs).** `load_policy` reads a module-level `exec(...)`, `globals()[...] = ...` or `setattr(sys.modules[__name__], ...)` as if absent (L2, L3, L13 ACCEPTED as the narrow policy). This is the fail-closed direction (the executed current policy is wider and is flagged), but `_check_uses` could refuse those three spellings outright for hygiene.

---
## What I tried to break and could not

- **The every-argument floor** (`p_floor.py`, 13 plants): a constant-returning helper reached through a module `setattr`, `types.MethodType`, a constructor-injected override, a lambda, keyword-only and `*args`/`**kwargs` calls, a nested call, a class constructor, a `partial`, an external module's function, a dict dispatch. All caught.
- **The refusal proof** (`p_refusal2.py`, `p_refusal3.py`): a tuple with a stranger, a refusal in a LOG, negated `isinstance`, an `else` branch, a stored `isinstance` result, a read after the `if`, an `elif` stranger, `type(err) is not`, a ternary, `issubclass`, a local subclass, `self.Refusal`, a local alias rebinding (module-wide un-proof, fail closed), an annotation of a stranger or a union, a refusal BUILT from caught text or the caught object. All caught. The five legitimate spellings (a plain handler, a named subclass, a tuple of refusals, a positive narrowing, a refusal annotation) are clean.
- **The brief's list** (`p_brief.py`, 49): `m = str(exc)` rebound through a helper and locally (twice), `format_map` with a dict, `%` with a value, tuple and dict, `exc.args[0]`, unpacked args, `format_exception`/`format_exception_only`, `repr`, `!r`, `ascii`, `format`, `__str__()`, `__notes__` (and joined), a chained raise with the text, `__cause__`/`__context__` of a plain exception, span `set_attribute`/`set_attributes`/`add_event`, `getattr(log, "error")`, `getattr(log, level)`, bytes, `__traceback__` walk, `with_traceback`, `print(file=stderr)`, `sys.exc_info()[1]`, `except*` (group and members), a lambda helper, a dict comprehension, a walrus, `extra=`, `bind()`, `log.log`, `warnings.warn`, `os.write`. 44 caught; the 5 misses are the chain half (by design), the metric label ×2 (P3-2) and `exec`/`eval` of a string (declared).
- **The literal policy reader** (18 texts): a post-assignment `update`, `**kw`, a builder, a foreign import, a module alias, a name bound twice, chained targets, an `IfExp`, a generator, a walrus, `dict(**a)`, handing the name to a call, list `+`: all refused; a field read, `|` unions, string literals: accepted. An env-widening in the CURRENT module against an identical base text: `NEW READER 'x'`.
- **The over-report keys** (read-only in `utils-obsm` `179cc6d`, `copilot-mro-obsm` `557a178f`): `_embedding_failure_outcome` and `_weaviate_failure_outcome` return an `isinstance`-chosen constant and `_finish_*_span` reads `error` for `type(error).__name__` only; `failure_text` returns `f"{what} failed ({type(exc).__name__})"` and `state` is tainted flow-insensitively through `state["error"]`. All three are over-reports of the withdrawn text-free rule, as claimed.

## What I did not test (TODO at resume)

- The 27-mutant detector battery (`scratchpad/otel-review-r7/mut/dt/`, specs written, `run.sh` ready, aimed per mutant): DT01–DT03 refusal proof, DT04–DT09 ratchet and dates, DT10–DT15 policy validation and the literal reader, DT16–DT18 N20/N15/first-argument, DT19 whole-source sites, DT20–DT26 URL (three passes, 8→2 words, scan limit off, unknown container, rescan-from-zero, JSON escape, fullwidth anchor).
- The estate re-scan (six snapshots + the two adoption trees) against `de501a8` and `927a729`: the "0 missing, 3 new keys" claim is verified only at the three named sites, not as a full diff.
- The corpus (1597 rows) row by row; the implementer's N/Q/B/F/D/E mutation tables row by row.
- The r6 URL residual list (V01 >8 words, V05 newline, V13 quadruple, V35/V36 fullwidth, V50 `&`, V38 Slack path, the six names) re-posed at `4b48507`; the r6 `_vetted` B14 set/frozenset/deque cases.
- `05e1a6e`'s "no unknown type ships" beyond reading the code; `850bb9d`'s N20/N15 rows beyond reading the code.
- Python 3.12+ syntax; the live bootstrap.

---
## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier is §2.3a's: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk: F1 = contract and privacy; F3 = residual. "Mutation-proved? no (TODO)" = the battery had not run at the pause.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7-01 | flynapse-otel | `_scan.py:337-403`, `_module.py:719-798` (5c7e1dc) | Narrowing withdrawn: a call's value carries EVERY argument's text; one additive `return_carried` table | r6 P1-1, lesson #14 | 13/13 rebinding shapes caught (`p_floor.py`); the floor needs no resolution; the table only adds | corpus `rev:otel-r6/proof*` | no (TODO: DT18) | 1 | 1 | F1 | **SETTLED in substance** (design, not patch) — pending DT18 |
| R7-02 | flynapse-otel | `_scan.py:194-269`, `_model.py:289-294`, `:313-327` (5b86943) | Refusal types are qualified names matched only by a PROVEN class; bare/builtin names refused; undefined-in-scan refused | r6 P1-2 | 11 leak plants caught, 5 legitimate spellings clean; a local alias anywhere un-proves module-wide (fail closed) | `test_exception_text_policy.py`, corpus `rev:otel-r6/refusal` | no (TODO: DT01–DT03, DT12, DT13) | 1 | 1 | F1 | **SETTLED in substance** |
| R7-03 | flynapse-otel | `_module.py:674-716` | A sanctioned refusal's `__cause__`/`__context__` inherit the body sanction | (none: unexamined) | 3 plants ship the chained exception in a body (`p_refusal2.py` ×2, `p_refusal3.py` ×1) | none | not applicable | 2 | 1 | F1 | **OPEN** (P2-1) |
| R7-04 | flynapse-otel | `_ratchet.py:77-153` (575e1b9) | `merge_base_text` never returns None: base → `moved_from` at base → oldest adding commit → raise | r6 P2-1 | Scratch repo: a `git mv` + widen in one commit, no `moved_from` → the moved text IS the baseline, `ratchet_problems == []`; with `moved_from` 4 problems; r6 raised | `test_exception_text_ratchet.py` (B1–B8) | no (TODO: DT04–DT07) | 1 | 2 | F1 | **PARTIAL → REFUTED for the move case** (P1-1) |
| R7-05 | flynapse-otel | `_model.py:357-533` (dd4cec5) | `load_policy` reads the base literally; foreign imports, other calls, double bindings, later mutation refused; `Policy`/`BoundedReader` frozen tuples | r6 P2-2 | 18 texts behave as documented; module-level `exec`/`globals()`/`setattr` read as absent = the NARROW reading (fail-closed direction); env-widening in the current module → `NEW READER` | `test_exception_text_policy.py` (F1–F12) | no (TODO: DT14, DT15) | 1 | 1 | F1 | **SETTLED in substance** |
| R7-06 | flynapse-otel | `withholding.py:788-802` | Decoding to a true fixed point, "bounded by the text's length" | r6 P2-3 (V13) | Quadratic: 64 KB nested chain 4.9 s inside the scan bound; 16 KB 0.44 s | `test_the_scan_bound_keeps_the_cost_bounded` (a different shape) | no (TODO: DT20) | 2 | 1 | F1 | **PARTIAL** (P2-3) |
| R7-07 | flynapse-otel | `tests/…url_secrets.py:616-650` (4b48507) | Cost bounds 10x→20x, 40x→100x | flakes under load | The count-based tests are the quadratic proof; the ratios never proved more than a constant | the two count tests | no (TODO: DT24) | 3 | 1 | F1 | **ASSERTED** (P3-1) |
| R7-08 | flynapse-otel | `_module.py:719-738` | Namespace reads only under builtin trust | (pre-existing) | Star import → `locals()`/`vars(obj)`/`globals()` reads silent (3/4 missed vs 4/4) | none | not applicable | 2 | 1 | F1 | **REFUTED** (P2-2) |
| R7-09 | flynapse-otel | `__init__.py:88-89`; `registry.py:77-87` | Metric attributes are the export boundary's job | docstring | No metrics withholding seat exists; key lint only; 2 plants ship; estate exposure 0 | none | not applicable | 2 | 1 | F1 | **OPEN** (P3-2) |
| R7-10 | flynapse-otel | `_module.py:338-358`, `:730-738` (850bb9d) | N20 setdefault chain and N15 `vars(obj)` caught; N01–N04/N18 declared | mro r7 | `p_trusted.py`: `vars(report)` caught; N20 not re-posed | corpus `rev:otel-r6/mro7*` | no (TODO: DT16, DT17) | 2 | 1 | F1 | **ASSERTED** |
| R7-11 | flynapse-otel | `_facts.py:391` → whole source; `_ratchet.py:22-30`, `:61-71` (850bb9d) | Whole-source sites; non-ISO dates refused after NFKC | r6 P3 | Code read only | ratchet tests D1–D5 | no (TODO: DT08, DT09, DT19) | 3 | 1 | F1 | **ASSERTED** |
| R7-12 | flynapse-otel | `_model.py:215-220` | `_NEVER_READERS` derived from the vocabulary | r6 P3 (drifting copy) | Code read: builtins ∪ MESSAGE ∪ FRAMES ∪ SYS | policy tests D6/D7 | no (TODO: DT10) | 3 | 0 (if DT10 red) | F1 | **ASSERTED** |
| R7-13 | flynapse-otel | `withholding.py:707-732` (05e1a6e) | `_vetted` walks set/frozenset/deque; any other object is `<unvetted>`; 64 KB scan bound fails closed | r6 P3 (B14) | Code read | url tests | no (TODO: DT22, DT23) | 2 | 1 | F1 | **ASSERTED** |
| R7-14 | estate | utils `EmbeddingService._embed`, `_traced_weaviate.decorate.traced`; copilot-mro `build_document_source_answer_binding.handler` | Three new keys are over-reports of the withdrawn text-free rule | implementer | Read at utils-obsm `179cc6d`, copilot-mro-obsm `557a178f`: constant/class-name returns; `state` tainted through `state["error"]` | none | not applicable | 3 | 1 | F1 | **SETTLED** |
| R7-15 | telegram-bot / flynapse-otel | telegram r5 P2-1 | The eighth finding at `56b1814` is a detector gap? | telegram reviewer | By design (R-EVERY-ARGUMENT at a raise site); a register entry there is blind to same-site regression; resolution = restructure the site | none | not applicable | 3 | 1 | F1 | **SETTLED: not a gap** (P3-3 docs) |
| R7-16 | telegram-bot / flynapse-otel | telegram r5 P2-2 | The chain half unread is a detector gap? | telegram reviewer | The chain is an object, not text; renderers are caught; export seats withhold the chain | none | not applicable | 3 | 1 | F1 | **SETTLED: not a gap** (P3-4 docs) |
| R7-17 | flynapse-otel | all 8 commits (+ `d1e531f`) | Each commit green at its own HEAD | process | 2346 → 2576 passed, rc=0 everywhere | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |
| R7-18 | flynapse-otel | estate re-scan (six snapshots, two adoption trees) | 0 missing vs `de501a8`, 3 new keys | implementer | NOT re-run | none | not applicable | 3 | 1 | F1 | **TODO** |
| R7-19 | flynapse-otel | `tests/fixtures/exception_text/corpus.json` (1597 rows) | Every r6 plant is a row | implementer | NOT re-derived | the corpus test | not applicable | 3 | 1 | F1 | **TODO** |

**Tier 0.** None yet: no mutant of mine has run against the detector (the battery is written and waiting).

---
## Open claims, tier 2 first

**Tier 2**
1. **R7-04 (P1-1):** the adoption fallback adopts a moved register's text; r6's attack 2 passes without `moved_from`.

**Tier 1**
1. **R7-03 (P2-1):** a refusal's `__cause__`/`__context__` in a body.
2. **R7-08 (P2-2):** namespace reads off under revoked trust.
3. **R7-06 (P2-3):** the quadratic decoder inside the scan bound.
4. **R7-09 (P3-2):** metric attributes declared to a seat that does not exist.
5. **R7-07, R7-15, R7-16, and the P3-5 hygiene note.**

**TODO at resume:** the mutation battery (R7-01/02/04/05/06/07/10/11/12/13 "Mutation-proved?"), R7-18, R7-19, and the r6 URL residual re-pose.
