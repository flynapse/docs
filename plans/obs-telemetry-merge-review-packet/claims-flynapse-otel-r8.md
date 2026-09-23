# Claims packet: flynapse-otel CLOSING review r8 — the ratchet P1-1 fix, the detector P2/P3 batch, the range to `ff20ca9`

Independent closing review by Fable, 2026-09-22. Read-only throughout: no code tree edited, checked out, stashed or committed; nothing pushed; nothing amended. Every run on the reviewer's own `git archive` extract of `ff20ca9` under `~/.claude/scratch/obs-merge/otel-r8/` (siblings `utils`/`core`/`dashboard` symlinked beside it, per the r7 recipe). Provenance quoted once: `flynapse_otel.__file__ = /home/aditya/.claude/scratch/obs-merge/otel-r8/c/ff20ca9/flynapse-otel/flynapse_otel/__init__.py` (printed under the lane's PYTHONPATH before the lane); the lane's one skip names the extract dir as its search root, so `rootdir` was the extract. Every pytest through `/home/aditya/Code/pytest-slot.sh --`; mutants through `/home/aditya/Code/mutant.sh` (which reads PYTEST's exit directly — `bash -c "$CMD"` then `rc=$?`, no tee in the path); mutated files md5-verified against the `ff20ca9` blobs after restore (`_ratchet.py` `b0531f88…`, `_module.py` `87a157b5…`, both MATCH before and after).

| repo | tree | branch | range reviewed | HEAD |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` | `main` (this repo has NO obs-merge branch) | `4b48507..ff20ca9` (27 commits; r7's pinned reviewed range ended at `4b48507`) | `ff20ca9b307fe28ec7a6a94a0378fe51b189cf0a`, verified clean (`git status --porcelain` empty), 28 ahead of `origin/main`, unpushed |

**Attestations.**
- Tree untouched: `ff20ca9` clean on `main` at review start and end; no checkout/stash/reset/commit issued against any real tree.
- Parked patch untouched: `~/.claude/scratch/obs-merge/otel-impl-r8/parked-netguard-r9a/r9a-blank-proxies.patch` exists, 8766 bytes, sha256 `62ac98935d6aa539e80edc26812fe098f66119c70fa990ffb160893b96255d65`, mtime 2026-09-22 05:35 (pre-dates this review; read-only `stat`/`sha256sum` only).
- Netguard is OUT of the project (owner, Add. 215): the 15 committed netguard/testing-module commits were checked ONLY for P0/P1-grade breakage — no bypass hunting, no landing check, no hardening findings.

**Range reconciliation — all 27 commits accounted for.**
- Detector/ratchet fix batch (Add. 218, full rigour): `0224a1a` (ratchet P1-1) · `595acc8` (P2-1) · `08bf7cb` (P2-2) · `d85afaa` (P2-3 + P3-1) · `282a866` (P2-4) · `541e2f3` + `b7b33d2` (P3-5) · `4e1583a` (P3-2/3/4 declarations) — 8.
- Netguard/testing module (P0/P1 break-check only): `5146857`, `d1e531f` (netguard r1 review's range), `72318a2`, `216ca28`, `d48b686`, `1c7165c`, `334888c`, `85dd378`, `0c15ca8`, `c19552d`, `d8d8801`, `e3e68b4`, `1749854`, `87ef702`, `dd78644` — 15.
- M-FAILURE-HOME port lane (Add. 178, `otel-impl-port`, landed during r7): `9640129` (utils r6 parity), `0960c16` (utils r7 parity, pin `1a42390`), `df503c2` (`search` URL marker, core r8 P1-1's estate half; behaviourally verified live by the api r9 review, Add. 209) — 3. Not in the brief's expected list; read end-to-end here and rowed below.
- `ff20ca9` — docs-only (`docs/plans/m-shared-netguard.md` alone, by `--stat`) — 1.

**Full lane at `ff20ca9`, reproduced on the reviewer's extract** (api venv python 3.11.15 / pytest 8.4.2 / xdist `-n 2`, `-p no:cacheprovider`, `DEBUG=false`): **2737 passed / 1 skipped / 1 xfailed, 40 warnings, 37.90 s, rc 0** — exactly Add. 235's claim, with the same identities (the root-anchoring skip; the declared-strict SyntaxError-header xfail). The +5 vs `87ef702` (2732, implementer log) are `dd78644`'s driver-seat per-rule rows; `ff20ca9` adds no tests over `dd78644`.

**Verdict: MERGE-CLEAN — 0 P0 · 0 P1 · 0 P2 · 4 P3.** Merge-blocking is P0/P1 only; nothing here blocks. The r7 verdict's 0/1/4/5 are all closed by the batch, each closure re-proven below.

---
## The r7 findings, re-proven at `ff20ca9`

- **P1-1 (ratchet, `0224a1a`).** The baseline is now DECIDED in `merge_base_text` from exactly three sources; a path new since the base with no `adopted_after` RAISES naming the candidate (fail-closed where r7 measured fail-open); an adoption commit that deletes ANY file is refused whatever `adopted_after` says (`--no-renames` on both the log and the diff, `log.follow` pinned off, shallow clones refused, refs refused as `adopted_after`, re-adds held to the first adoption). The r7 `ratchet_ws` repro is a committed test in BOTH shapes (`moved`/`copied` parametrized), and `moved_from` still yields exactly the review's four problems. Re-proven here: RA01 and RA02 re-run KILLED on my extract; RA01 additionally replayed by hand with output kept — the kill is `test_an_adoption_the_guard_does_not_name_is_refused_and_the_candidate_is_named` and `…moved_or_copied…[copied]`, both `DID NOT RAISE ValueError`, i.e. exactly the r7 hole re-opened.
- **P2-1 (detector, `595acc8`).** `V.FOREIGN_ATTRIBUTES = {__cause__, __context__, __traceback__, __notes__}`; in `_visit_attribute` a foreign attribute re-emits its value's reads with every label → `V.NOWHERE` and stops — the chain is text, allowed nowhere, for refusal-sanctioned and plain values alike (strictly-more-conservative direction). 7 leak + 1 clean corpus rows (`rev:otel-r7/refusal-chain`), including the bound-to-a-name and narrowed-`isinstance` spellings. Re-proven: RB02 re-run KILLED; my NEW1 (below) KILLED.
- **P2-2 (detector, `08bf7cb`).** The `facts.trusted` gate is gone from the namespace reads: `locals()`/`vars()`/`globals()`/`vars(obj)` are read under revoked or shadowed trust too, and an untrusted call ALSO falls through to the every-argument floor — strictly more reads. Re-proven: my NEW2 (below) KILLED.
- **P2-3 + P3-1 (URL rule, `d85afaa`).** `_decoded` allows `_DECODE_PASSES = 8` changing passes and returns `None` still-changing; both callers (`_withheld_run`, `_carries_secret` — the only two, grep-verified) fail closed. Measured on my extract: the r7 quadratic shape (`%` + `25`×k) costs **1.0 ms at 16 KB and 2.9 ms at 64 KB** (r7: 0.44 s / 4.9 s), and a 9-layer-encoded `token` is withheld whole. The ratio-test docstrings now say the count tests carry the quadratic proof. Re-proven: RD02 re-run KILLED.
- **P2-4 (detector, `282a866`).** `_class_named` strips leading underscores at both `_unwrap_raised` sites; `raise _WatchOver(…)`, `errors._Hidden(…)` and `__Mangled(…)` are constructions; the declared limit names the private/mangled forms. Estate re-scan (implementer): +1 key, telegram-bot `document_watch._read` ×2 — already known to and routed through the telegram lane (Add. 186). Re-proven: RE01 re-run KILLED (its replacement text IS the `df503c2` predicate, so the kill is also the red-before proof for the corpus rows).
- **P3-5 (`541e2f3` + `b7b33d2`).** `_check_unseen_bindings` refuses `exec`/`eval`/`__import__`/`globals`/`locals`/`vars`/`setattr`/`delattr` calls and `sys.modules` anywhere in a policy text; foreign imports were already refused, so the aliased spellings have no entry point. Read; banked RF01–03 killed (not re-run here).
- **P3-2/3/4 (`4e1583a`).** Docs-only against the package docstring; each declaration checked against the code it describes: the metrics no-seat truth (registry lints KEYS only — confirmed in `registry.py`), the restructure-not-register rule for raise/body sites, the chain-is-an-object declaration. Accurate.

## Findings, ranked

### No P0. No P1. No P2.

### P3-1: the refusal sanction still rides through a CUSTOM attribute or a string-spelled read (`_module.py`, the `595acc8` neighbourhood)

`FOREIGN_ATTRIBUTES` is an enumeration, so two adjacent carriers of the chain stay sanctioned: a refusal class that stores its cause under its own name (`self.original = cause` in `__init__`, then `except Refusal as err: detail=str(err.original)`) and the string-spelled `str(getattr(err, "__cause__"))` (a Call, not an Attribute — the every-argument floor hands the value `err`'s token WITH its body sanction). Both matter only for a value a `refusal_types` policy sanctions. **Estate exposure 0, measured here: `grep -rn refusal_types` over all six consumer trees (utils-obsm, core-obsm, api-obsm, copilot-mro-obsm, shift-optimizer, telegram-bot) returns no `.py` hit — no estate policy declares refusal types at all.** Fix when an adopter appears: treat every dunder read of a refusal-sanctioned value except `args` as foreign, and read `getattr(x, "<literal>")` as the attribute it spells.

### P3-2: the adoption design's residual shapes want one more table row (docs; `0224a1a`)

A COPY (old register kept) or a TWO-COMMIT move (delete in one commit, add widened in the next) with an explicit `adopted_after` DOES adopt the widened text: the adding commit deletes nothing, so the delete check passes. The copy is DECLARED in the plan's design table with its reasoning (similarity detection rejected for the false-copy/false-adoption cases; an explicit re-adoption is a guard edit a reviewer reads — the same "inherent" class r7 itself accepted for `against` edits). The two-commit split is the same trust model but has no row of its own. Add the row; no code change is owed.

### P3-3: `_class_named` reads `_1Error` as a plain call (undeclared gray zone; `282a866`)

`"_1Error".lstrip("_")[:1].isupper()` is False, so an underscore-then-digit class raised with caught text is unread — neither the amended construction declaration (CapWords/private/mangled) nor the lowercase-name declared limit names it. Estate has no such class (it is a PEP 8 violation to begin with). One sentence in the declared limits, or `lstrip("_")[:1]` → first-alpha check, closes it.

### P3-4: the M-FAILURE-HOME walk has diverged from utils at `fabb94c` (known: U9-08; the port-spec delta is pinned below)

Not a defect in this range — the parity pin (`UTILS_PARITY_SHA = 1a42390`) is exact for what was ported, and the parity test is green — but the queue-step-13 port owes the `fabb94c` delta before the pin moves. See the walk-contract section.

---
## The `fabb94c` walk contract vs `flynapse_otel/failure.py` at `ff20ca9` (the deferred claims-file walk)

Read side by side: `claims-utils-r9.md` §"The `fabb94c` args walk — SPEC" (points 1–5 are the contract) and `flynapse_otel/failure.py:335-356` (`_every_link`) at `ff20ca9`.

| contract point | at `ff20ca9` |
|---|---|
| 1. Worklist, not recursion: `pending=[exc]`, LIFO `pop()`, `seen` by `id()`, `found` = emission order | **PRESENT, exact** (`failure.py:340-347`) |
| 2. Each popped link enqueues `__context__` then `__cause__` (non-None; a SUPPRESSED `__context__` walked too), then group members (`isinstance(..., BaseExceptionGroup)` → `.exceptions`) | **PRESENT, exact**, including the suppressed-context walk (no `__suppress_context__` check in `_every_link`; declared in its docstring) (`failure.py:351-355`) |
| 2 (tail). …then every exception `_held_in_args(link)` returns | **ABSENT** — `_held_in_args` does not exist in the file (grep count 0): an exception held directly in another's `args` tuple is not walked, so a quote of it is not withheld |
| 3. `_held_in_args` shallow: `link.args` in `try/except Exception`, `[]` on raise, tuple-only, direct `BaseException` elements only | **N/A — the function is absent**; the port must add it exactly this shallow (not the container/attribute/`__notes__` descent utils declined, P3-1 there) |
| 4. Termination: `seen` by `id()` bounds every cycle; depth bounded by the link counter | **PRESENT, exact** |
| 5. Bound is a LINK COUNT tested AFTER the append: `found.append(link)` then `if len(found) > _MAX_LINKS: return None`, `_MAX_LINKS = 256` (256 checked, 257 → None); `None` → `WITHHELD_MESSAGE` at every caller | **PRESENT, exact** (`failure.py:322`, `:348-350`; callers `:294-296`, `:652-659`) |

**Porting spec for queue step 13:** add `_held_in_args` (contract point 3, verbatim semantics) as the FOURTH enqueue source in `_every_link`, after the group members; change nothing else in the walk — points 1, 4, 5 and the rest of 2 are already byte-equivalent in behaviour. Then move `UTILS_PARITY_SHA` past `fabb94c` and re-run the parity lane. Until then the pin at `1a42390` keeps the parity test green while the renderers are diverged (utils `_exception_text.py` md5 `4c3c2437…` → `5b6899d5…` at `fabb94c`).

---
## Mutation work (all on the reviewer's extract, repo venv, aimed per the banked specs' test files)

**Banked proofs re-run (5 of the batch's, incl. the mandatory ratchet P1-1):**

| mutant | behaviour re-broken | result here | banked |
|---|---|---|---|
| RA01_unnamed_adoption_adopted | the r7 P1-1 hole itself (unnamed adoption adopted again) | **KILLED rc=1** (+ manual replay: killed by the two adoption tests, `DID NOT RAISE ValueError`) | KILLED |
| RA02_deletion_check_off | a move named as an adoption accepted | **KILLED rc=1** | KILLED |
| RB02_sanction_kept | a refusal's chain keeps the body sanction (P2-1) | **KILLED rc=1** | KILLED |
| RD02_unsettled_judged_as_is | a still-changing text judged as-is instead of withheld (P2-3) | **KILLED rc=1** | KILLED |
| RE01_underscore_class_a_call_again | the `df503c2` predicate restored (P2-4) | **KILLED rc=1** | KILLED |

Each run had its own green baseline on the unmutated extract (`mutant.sh` default; no `-B` on first-of-set). Results recomputed from MY `mut-rerun/results.txt` and run logs, not the implementer's transcript. Restores md5-verified against the `ff20ca9` blobs.

**New mutants designed here (both against the P2 fixed behaviours, leak direction):**

| mutant | what it breaks | result |
|---|---|---|
| NEW1_foreign_reads_swallowed | the `FOREIGN_ATTRIBUTES` branch returns WITHOUT re-emitting the value's reads — `err.__cause__` produces no reads at all (fail-open by silence, the opposite direction from banked RB01/RB02) | **KILLED rc=1**; manual replay: corpus row `0038-leak-api-__traceback__.tb_frame` stops being found |
| NEW2_globals_flag_flipped | `_namespace_reads(node, func.id != "globals", out)` — `globals()` read as locals and vice versa, in the trusted AND revoked paths (P2-2's row family) | **KILLED rc=1** |

**Timing probe (P2-3, ground):** 16 KB hostile line 1.0 ms, 64 KB 2.9 ms, 9-layer token withheld — reproduces the claimed ~0.004 s at the scan bound.

## Netguard break-check (P0/P1 grade only, per Add. 215)

- No netguard commit touches a runtime module: `git show --name-only` over all 15 shows only `flynapse_otel/testing/`, `tests/` and `docs/` paths.
- A production import (`flynapse_otel` + `bootstrap` + `withholding` + `failure`) loads ZERO `flynapse_otel.testing.*` modules and leaves `socket.socket` unpatched (probe on the extract).
- The guarded test session itself is proven by the reproduced full lane (rc 0 under xdist `-n 2` — the xdist hand-off included).
- Parked patch attested untouched (header). Nothing further examined, by ruling.

## What I did not test

- The banked RC/RF/RA03–RA15/RB01/RB03–06/RD01/RD03–05/RE02 mutants row by row (15 of the batch's 33 detector/ratchet mutants stand on the implementer's results; my 5 re-runs + 2 new mutants sampled every fixed behaviour).
- The implementer's estate re-scans (P2-1 "0 change", P2-4 "+1 telegram key") — accepted as implementer-proved; my own estate measurement was the `refusal_types` zero-exposure grep.
- The netguard beyond the break-check, by owner ruling.
- The two port commits' internal behaviour beyond the walk contract and the green parity lane (their source was reviewed as utils rounds 6–7).

---
## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk: F1 = contract and privacy; F2 = parity/port; F3 = residual/process.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R8-01 | flynapse-otel | `_ratchet.py:82-218` (0224a1a) | A register new since the base is held to the adoption its guard NAMES (`adopted_after`), verified: oldest addition, parent match, deletes-nothing, `--no-renames`, `log.follow` off, shallow refused, refs refused | r7 P1-1 | The r7 repro raises in both shapes; design section written FIRST as r7 demanded | `test_exception_text_ratchet.py` (61 tests) | **yes, re-run here: RA01, RA02 red** (RA01 ground-replayed) | 1 | 0 | F1 | **SETTLED** |
| R8-02 | flynapse-otel | plan design table (0224a1a) | A copy or split move with an EXPLICIT `adopted_after` adopts its own text — accepted as a reviewed guard edit; similarity detection rejected with reasons | design | Copy row declared; two-commit split has no row | n/a | not applicable | 3 | 1 | F1 | **SETTLED by declaration; P3-2 docs row owed** |
| R8-03 | flynapse-otel | `_module.py:724-731`, `_vocabulary.py:115` (595acc8) | A sanctioned refusal's `__cause__`/`__context__`/`__traceback__`/`__notes__` are text, allowed nowhere | r7 P2-1 | 7 leak + 1 clean corpus rows; conservative for plain values too | corpus test | **yes, re-run here: RB02 red; NEW1 red** (ground-replayed) | 1 | 0 | F1 | **SETTLED** |
| R8-04 | flynapse-otel | `_module.py` (adjacent to 595acc8) | A custom attribute (`err.original`) or `getattr(err, "__cause__")` still carries the sanction | this review | Enumerated `FOREIGN_ATTRIBUTES`; the floor hands the sanctioned token through a Call | none | not applicable | 2 | 1 | F1 | **OPEN (P3-1)** — exposure 0, `refusal_types` grep empty across all six trees |
| R8-05 | flynapse-otel | `_module.py:733-756` (08bf7cb) | Namespace reads read under revoked/shadowed trust; untrusted calls also take the floor | r7 P2-2 | 6 leak + 1 clean rows; strictly more reads | corpus test | **yes: NEW2 red here**; banked RC01/RC02 | 1 | 0 | F1 | **SETTLED** |
| R8-06 | flynapse-otel | `withholding.py:781-816,921-923` (d85afaa) | 8 changing decode passes; still-changing → `None` → withheld whole at BOTH callers (the only two) | r7 P2-3/P3-1 | 64 KB = 2.9 ms measured here; 9-layer token withheld; count test carries the quadratic proof | url tests | **yes, re-run here: RD02 red**; banked RD01/03/04/05 | 1 | 0 | F1 | **SETTLED** |
| R8-07 | flynapse-otel | `_module.py:136-141,1434-1444` (282a866) | A raised `_Private`/`__Mangled` class is a construction (`lstrip("_")`); limits amended | r7 P2-4 | 5 leak + 2 clean rows; RE01's mutant text IS the old predicate | corpus test | **yes, re-run here: RE01 red** | 1 | 0 | F1 | **SETTLED**; `_1Error` gray zone = P3-3 |
| R8-08 | flynapse-otel | `_model.py:419-444` (541e2f3, b7b33d2) | `load_policy` refuses `exec`/`eval`/`__import__`/namespace builtins/`setattr`/`delattr`/`sys.modules` anywhere in the text | r7 P3-5 | Ten spellings pinned; foreign imports already refused, so aliases have no entry | policy tests | banked RF01–03 (not re-run) | 2 | 1 | F1 | **SETTLED** |
| R8-09 | flynapse-otel | `__init__.py:71-107` (4e1583a) | The declarations state the metrics no-seat truth, restructure-not-register, and the chain-as-object | r7 P3-2/3/4 | Each checked against the code it describes (registry lints keys only) | limit-quote rows | not applicable | 3 | 1 | F1 | **SETTLED** |
| R8-10 | flynapse-otel | HEAD `ff20ca9` | Full lane green at HEAD | Add. 235 | **Reproduced on my extract: 2737 / 1 skip / 1 xfail, rc 0**, same identities; +5 vs `87ef702` = driver-seat rows | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |
| R8-11 | flynapse-otel | 15 netguard/testing commits | Committed netguard stays as history and breaks nothing at P0/P1 | Add. 215 | No runtime module touched; production import loads no `testing.*`, socket unpatched; lane green under xdist | packaging isolation test | not applicable | 1 | 1 | F3 | **SETTLED (break-check only)** |
| R8-12 | flynapse-otel / utils | `failure.py:335-356`; parity pin `1a42390` (9640129, 0960c16) | The port matches the `fabb94c` walk contract on points 1, 4, 5 and 2-except-args; `_held_in_args` is ABSENT | claims-utils-r9 U9-08 | Point-by-point table above; grep count 0; parity green because the pin pre-dates `fabb94c` | parity test | not applicable | 3 | 1 | F2 | **OPEN (P3-4)** — the port spec for queue step 13 is pinned above |
| R8-13 | flynapse-otel | `withholding.py:329-357` (df503c2) | `search` is a SECRET_PARAMETER_MARKER: typed text withheld estate-wide | core r8 P1-1 | Diff read; api r9 verified the behaviour on a real uvicorn (Add. 209); S1–S3 banked | url tests | implementer S1–S3 | 1 | 1 | F1 | **SETTLED** |
| R8-14 | flynapse-otel | `4b48507..ff20ca9` | All 27 commits reconcile to ledger provenance (8 batch + 15 netguard + 3 port + 1 docs) | process | Commit-by-commit list above; `ff20ca9` docs-only by `--stat` | n/a | not applicable | 3 | 1 | F3 | **SETTLED** |
| R8-15 | estate | six consumer trees | No estate policy declares `refusal_types`, so R8-04's exposure is 0 today | this review | `grep -rn refusal_types --include=*.py`: 0 hits in all six | none | not applicable | 3 | 1 | F1 | **SETTLED** |
| R8-16 | telegram-bot | `document_watch.py:566,573` | P2-4's estate re-scan key (+1, `_read` ×2) is the telegram lane's item | implementer, Add. 186 | Routed and already known there | telegram lane | not applicable | 3 | 1 | F1 | **SETTLED as routed** |

**Tier 0 (settled by guards I saw fail):** R8-01, R8-03, R8-05, R8-06, R8-07.
**OPEN:** R8-04 (P3-1), R8-12 (P3-4, the port's input); docs rows R8-02 (P3-2) and the P3-3 sentence.

---
## Future Improvements

- **P3-1 closure** (when a `refusal_types` adopter appears): every dunder read of a refusal-sanctioned value except `args` foreign by default; `getattr(x, "<string literal>")` read as the attribute it spells. Until then the zero-exposure grep is the guard.
- **P3-2 docs:** one more design-table row naming the two-commit move (delete, then add-widened, `adopted_after` on the add) as the same explicit-re-adoption class as the copy.
- **P3-3:** declare or close the `_1Error` gray zone (first-alphabetic-character check instead of `[:1]` after `lstrip`).
- **Ratchet nicety:** `_SHA` accepts a 7-hex string that is also a BRANCH name (git prefers the ref on ambiguity) — harmless today because the parent check re-verifies against the fixed adoption commit every run (a moved ref fails closed), but `--verify` with a `^{commit}` on an explicit `refs/…`-rejecting spelling would remove the ambiguity.
- **P3-4:** the M-FAILURE-HOME port lands `_held_in_args` per the pinned spec, then advances `UTILS_PARITY_SHA` past `fabb94c`.
