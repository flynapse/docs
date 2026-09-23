# Claims packet: flynapse-otel PRE-PUSH full-diff review (queue step 16b, first of nine)

Fable pre-push reviewer, 2026-09-22. READ-ONLY on the real tree throughout: no checkout, stash,
commit or edit against `/home/aditya/Code/flynapse-otel`; HEAD `c93a9c987ef7…` verified clean at
start AND at end of review. Every run on the reviewer's own `git clone` of the repo at
`~/.claude/scratch/obs-merge/prepush-otel/tree/` (its own in-project `.venv`, poetry-installed from
the lockfile; import provenance verified — `flynapse_otel.failure.__file__` resolves inside the
clone; `origin/main` ref mirrored to `850bb9d` for ratchet fidelity; empty `core/` and `dashboard/`
sibling stubs beside it for the root-anchoring tests). Every pytest through
`/home/aditya/Code/pytest-slot.sh --`; mutants through `/home/aditya/Code/mutant.sh` (each with its
own green baseline; scratch tree verified `git status` clean after every restore).

**Range RULED by the controller: `1cafda2..c93a9c9` (74 commits)** — the FULL colleague scope, NOT
merge-base..HEAD. Stop-and-ruling record: origin/main is `850bb9d`, not the brief's `1cafda2`; the
42 commits `1cafda2..850bb9d` were pushed by the owner 2026-09-21/22 BEFORE the pre-push gate was
ratified (Add. 261 corrects the ledger's stale "nothing pushed"; a remote audit found flynapse-otel
the only repo whose origin moved). Rows whose commits fall in `1cafda2..850bb9d` are marked
**ALREADY-PUSHED**; a P0/P1 there gates the same (FIX-FIRST), remedy = fix-forward commit and
eventual push, never any history rewrite.

| repo | tree | branch | HEAD | origin/main | pushed / unpushed in range |
|---|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` | `main`, clean | `c93a9c987ef7…` | `850bb9d` (ls-remote confirmed; reflog "update by push") | 42 (`1cafda2..850bb9d`: FO rounds + detector r5 + r6 incl. the R6 fix batch) / 32 (`850bb9d..HEAD`: `4b48507`, 15 netguard, 8 detector-r7 fixes, 3 port commits, `ff20ca9`, `d9ccbba`, `91b8b34`, `50bcf30`, `c93a9c9`) |

**Full lane at HEAD `c93a9c9`, reproduced on the reviewer's clone** (clone venv python 3.11 /
pytest 9.1.1, serial — pytest-xdist is not a dependency of this repo; plain `pytest`, repo addopts
`-ra -q`): **2625 passed / 1 skipped / 1 xfailed, 40 warnings, 40.88 s, rc 0** — exactly the
reference totals, same two identities (the root-anchoring twin skip; the declared-strict
hand-built-SyntaxError-header xfail). Log: `~/.claude/scratch/obs-merge/prepush-otel/full-lane-HEAD-2.log`.
Runner notes for later agents: (a) the suite needs at least a `core/` directory beside the repo
(workspace shape) or one root-anchoring test fails, and a `dashboard/` directory turns its skip into
a pass; (b) `addopts` already carries `-q`, so `pytest -q` on the command line is `-qq` and
suppresses pytest's final counts line entirely — run plain `pytest`.

**Coverage map of the range against the filed claims files** (indexes, not evidence):
`1cafda2..e8d1df1` (12) = FO-R0…FO-R4 + G.110 + FO-A (`claims-flynapse-otel-rounds.md`, 60 rows);
`e8d1df1..34c814a` (12) = detector r5; `34c814a..927a729` (11) = r6; `927a729..4b48507` (8) =
r6-fix batch + r7's tail (r7 + netguard r1 filed in `claims-flynapse-otel-detector-r7.md` /
`-netguard-r1.md`); `4b48507..ff20ca9` (27) = the r8 CLOSING review (`claims-flynapse-otel-r8.md`,
Fable, MERGE-CLEAN 0/0/0/4 P3); `ff20ca9..c93a9c9` (4) = **no prior independent review** —
first-review rigour applied here (rows PP-12…PP-14). Segment counts recomputed: 12+12+11+8+27+4 = 74.

## Claims table

Severity P0–P3; the push gate is P0/P1. Verdicts: CONFIRMED / REFUTED / P-severity finding.

| id | file:line | claim reviewed | evidence I executed | verdict |
|---|---|---|---|---|
| PP-01 | (whole repo) | Full lane green at HEAD with the reference identities (2625/1/1) | Reproduced on my clone: rc 0, 2625 passed / 1 skipped / 1 xfailed, same skip + xfail identities | CONFIRMED |
| PP-02 | range bookkeeping | Ruled range = 74 commits `1cafda2..c93a9c9`; 42 pushed / 32 unpushed | `git rev-list --count` both segments; reflog "update by push"; `git ls-remote` confirms remote at `850bb9d` | CONFIRMED |
| PP-03 | `_ratchet.py` (0224a1a) · `_module.py` (595adjacent) · `withholding.py:802-816` (d85afaa) | Banked r8 mutants still die at HEAD: RA01 (unnamed adoption adopted), RB02 (refusal chain keeps its sanction), RD02 (still-changing decode judged as-is) | Re-run via `mutant.sh` on my clone at `c93a9c9`, own green baselines: **all three KILLED rc=1** (`~/.claude/scratch/obs-merge/prepush-otel/mut/results.txt`, logs beside it); targets byte-unchanged since `ff20ca9` (`git diff --name-only ff20ca9..c93a9c9` touches only `__init__.py`, `failure.py`, tests) | CONFIRMED |
| PP-04 | `failure.py:362` · `__init__.py:107,96-99` | The two unreviewed behaviour commits' guards bite (red-before): the args-walk enqueue, the no-OTel-on-import laziness, the `bootstrap` descriptor | My own mutants, `mutant.sh`, green baselines: **PP-M1** (`pending.extend(_held_in_args(link))` → `pending.extend(())`) KILLED rc=1 by `test_exception_quotes.py`; **PP-M2** (eager `_load_the_stack()` restored at import) KILLED rc=1 by `test_failure_imports_no_otel.py`; **PP-M3** (setter accepts modules) KILLED rc=1 (specs + logs: `…/prepush-otel/mut-own/`) | CONFIRMED |
| PP-05 | `flynapse_otel/__init__.py`, `failure.py` | ABSENCE (ruled design requirement): `import flynapse_otel.failure` loads no `opentelemetry*` module | Re-proved myself: direct interpreter probe on the clone — 0 `opentelemetry*` and 0 `flynapse_otel.testing*` modules after `import flynapse_otel.failure` AND after `import flynapse_otel`; stack loads whole on first attribute access; `flynapse_otel.bootstrap` stays the function. Plus the 4 fresh-interpreter guard tests in the lane and mutant PP-M2 | CONFIRMED |
| PP-06 | repo-wide | ABSENCE: `UTILS_PARITY_SHA` exists in no code | `grep -rn UTILS_PARITY_SHA` over flynapse-otel and utils-obsm/utils: only historical mentions in `docs/plans/m-failure-home.md` (implementation notes), zero code hits | CONFIRMED |
| PP-07 | `50bcf30` (parity retirement) | The retirement is compensated, not a silent guard loss: utils' `_exception_text` is an alias re-export held by an identity test on the utils side | Verified in utils-obsm COMMITTED HEAD (`23e849c`): `d6f8fbf` exists; `utils/_exception_text.py` is a pure re-export of `flynapse_otel.failure`; `tests/unit/observability/test_safe_loguru_default.py::test_the_exception_text_rules_are_flynapse_otels_own_objects` pins 18 names by COUNT EQUALITY and object IDENTITY (`is`) | CONFIRMED |
| PP-08 | `c93a9c9` (`failure.py:21-23`) | Docstring claim "both utils modules re-export it, the very same objects" is TRUE | utils-obsm `23e849c` ("observability.failure: a re-export of flynapse_otel.failure"): `utils/observability/failure.py` is a pure re-export; the second identity test (`test_the_failure_description_is_flynapse_otels_own_objects`, 18 names, `is`) exists | CONFIRMED |
| PP-09 | `tests/fixtures/exception_text/corpus.json` + `test_exception_text_corpus.py` | ABSENCE CHECK: the detector corpus round-trips and nothing is silently skipped | Independent probe on the fixture: JSON round-trip equal (`d == json.loads(json.dumps(d))`), 1617 rows, kinds leak 1343 / clean 251 / limit 23, local 24 and pinned 76 matching the test's equality registers; the lane executes every non-local row both ways plus the per-origin-and-kind EQUALITY floor, the rulings cross-check and the limit-rows-must-name-a-declared-limit check | CONFIRMED |
| PP-10 | range-wide test deletions | ABSENCE: no commit in range weakens a guard silently | Swept every commit deleting >10 test lines (17 hits): each maps to a filed claims row (FO fix passes, r5-r8 fix batches, conftest refactor to shared live views); the ONE wholly-deleted guard is the parity test (PP-07, compensated); `test_no_loguru_in_package`'s exclusion of `testing/` is compensated by the STRICTER `test_testing_package_isolation.py` (named-module equality, stdlib-only for detector/netguard/sitecustomize, pytest only in `network_plugin.py`, decoys for every import spelling, computed-import sites named with reasons); `test_shutdown_lifecycle` / `test_instrumentation_catalogue` deletions replace message-carrying asserts with class-only asserts plus a sentinel-absence assert — strengthenings | CONFIRMED |
| PP-11 | the 15 netguard commits + `ff20ca9` | Netguard code is committed but the PROJECT is out (Add. 215): break-check only — it breaks nothing at P0/P1 | `git show --name-only` over all 16: zero paths outside `flynapse_otel/testing/`, `tests/`, `docs/`; runtime isolation proven by the lane (`test_the_runtime_never_loads_the_testing_package_or_pytest`, `test_the_network_guard_installs_only_in_a_test_process`) and by my direct probe (0 `testing*` modules after runtime imports); the guarded session itself is proven by the reproduced full lane rc 0 | CONFIRMED (break-check only, per ruling) |
| PP-12 | `91b8b34` (`flynapse_otel/__init__.py`) — first review | Lazy PEP 562 package: no OTel on import, stack loads whole on first access, `bootstrap` stays the function whichever comes first | Full diff read. Descriptor analysis: the `bootstrap` property is a DATA descriptor (getter+setter), so it outranks the instance dict and the module-level `__getattr__` is never consulted for it; the setter drops only ModuleType (the import system's submodule binding) and accepts monkeypatched values; `_load_the_stack` binds via module globals (bypassing the setter, correctly); `import a.b as c` binds the function — SAME as the eager package did (the classic from-import overwrite), no behaviour change. The isolation scan still passes honestly: `_load_the_stack` imports by STRING LITERALS, so no `COMPUTED_IMPORT_SITES` entry was needed (the r5 MB03 lazy-`__getattr__` shape is exactly what this avoids). Estate grep: every consumer reaches submodules by real imports (`import flynapse_otel.bootstrap`, `from flynapse_otel.logging import …`, `importlib.import_module`), none by bare attribute access. Guard tests + PP-M2/PP-M3 | CONFIRMED; two P3 notes below |
| PP-13 | `d9ccbba` (`failure.py:336-374` + tests) — first review | The `_held_in_args` port matches the pinned r8 spec (claims-flynapse-otel-r8.md §walk-contract) point for point | Diff + full `failure.py` read: shallow reader (`try/except Exception` → `[]`, tuple-only, direct `BaseException` elements only), fourth enqueue source after group members, dedup at pop by `id()`, `_MAX_LINKS` checked after append — nothing else in the walk changed. Tests cover the reviewer's shape, two-level nesting, group member + cause holding one, hostile `args` property, direct-tuple-elements-only incl. an exception CLASS in args, 256-checked/257-withheld, self and mutual args cycles. Mutant PP-M1 red | CONFIRMED |
| PP-14 | r8 OPEN row R8-12 (P3-4) | The owed port landed and the parity thread is closed end-to-end | `d9ccbba` implements the spec and moved the pin to `fabb94c` with an args-held parity shape; `50bcf30` then retired the pin for the re-export (PP-07); r8's P3-4 is CLOSED at HEAD | CONFIRMED |
| PP-15 | `bootstrap.py` (range diff) | Final state matches the filed decisions: semconv latch above the disabled path + cleared in `_reset_for_tests` (FO0-07/08), `_refuse_foreign_globals` RAISES (FO2-04), withholding installed as the provider's OWN processor list on both pipes (G.110/G.112), body-size Drop views (M-LEGACY-DELETE, both semconv generations), degradation warnings name the failure's CLASS alone, `is_instrumented_by_opentelemetry` checked both sides of `instrument()` | Full range diff read; the lane's `test_bootstrap_process_env` / `test_process_global_ordering` / `test_withholding_seat_guard` / `test_unread_http_body_sizes_are_dropped` / `test_shutdown_lifecycle` all green in my run | CONFIRMED — ALREADY-PUSHED (pre-`850bb9d` parts) |
| PP-16 | `tracing.py` (range diff) | Final state matches FO0-01…04: four `**_WITHHOLD` call sites, `_withholding` takes a FACTORY under `_agnosticcontextmanager`, `end_span` writes the bounded pair (`error.type` + bare ERROR), the `use_span`-does-not-honour docstring + pin | Full range diff read; four call sites counted; the lane's `test_tracing_helpers` / `test_span_openers_withhold` green | CONFIRMED — ALREADY-PUSHED |
| PP-17 | `withholding.py` (new file, 991 lines) | Final state matches the FO2…FO4 + r5…r8 trajectory: `_on_ending` forwards to nobody; `frames_only` never opens a file; fail-closed `on_emit` (`UNVETTED`); plain rebuilds; mapping keys vetted with collision-merge; `URL_SCAN_LIMIT` fail-closed tail; `_decoded` 8-pass fail-closed at BOTH callers; `SECRET_PARAMETER_MARKERS` incl. `search`, `SECRET_PARAMETER_NAMES` = {code, pass, otp, t, pw, pin, sid, refresh}; span side G.111 by structure | Whole file read against the rows; RD02 re-killed (PP-03); the four log-pipe/URL test files green in the lane | CONFIRMED — ALREADY-PUSHED (pre-`850bb9d` parts; r7/r8 fixes unpushed) |
| PP-18 | whole range diff | No credential-shaped material entered the history | Sweep of every added line for AWS key ids, private-key blocks, `ghp_`/`xox` tokens, secret assignments: zero hits (sentinels are labelled sentinels) | CONFIRMED |
| PP-19 | `_ratchet.py` (whole file) | The baseline decider is exactly the r8-settled design: three sources only, remote-tracking `against` enforced, `adopted_after` a SHA never a ref, oldest-addition + parent-match + deletes-nothing verification, shallow refused, `--no-renames` + `log.follow=false` | Whole file read; RA01 re-killed (PP-03); the r8 `_SHA`-vs-branch-name ambiguity nicety remains recorded (harmless: the parent check re-verifies) | CONFIRMED |
| PP-20 | r8's still-open P3s | R8-04 (custom-attribute / string-spelled `getattr` chain carrier; `refusal_types` estate exposure 0), r8 P3-2 (two-commit-move docs row), P3-3 (`_1Error` gray zone) remain OPEN at HEAD | Re-checked: no code in `ff20ca9..c93a9c9` touches the detector; carried, non-gating | CONFIRMED (carried, P3) |
| PP-21 | `flynapse_otel/__init__.py` | NEW (this review): two behaviour deltas of the lazy package, both consumerless today | (a) A submodule not in `__all__` (`flynapse_otel.logging`, `.registry` as modules) is no longer reachable as a bare ATTRIBUTE before the stack loads — pre-lazy it was bound eagerly; estate grep shows every consumer imports properly, so no live breakage. (b) `del flynapse_otel.bootstrap` / `monkeypatch.delattr` now raises `AttributeError` (the data descriptor has no deleter); no estate use found | **P3** (recorded, not gating) |

## Verdict

**MERGE-CLEAN — 0 P0 · 0 P1 · 0 P2 · 3 P3** (PP-21's two notes + the carried r8 P3 set restated in
PP-20; nothing new above P3). The push gate is P0/P1: **nothing here blocks the push.**

The ALREADY-PUSHED segment (`1cafda2..850bb9d`, 42 commits) carries no P0/P1 either, so no
fix-forward commit is owed for it.

## What I did not test

- The banked r8 mutants beyond my three re-runs (RA02/RE01 and the RC/RF/RB/RD families stand on
  the r8 reviewer's re-runs and the implementer's bank); my sample covered three files/proof
  families and both unreviewed new commits.
- The netguard beyond the P0/P1 break-check, by owner ruling (Add. 215).
- The other repos' adoption of `flynapse_otel.testing` (each repo's own pre-push review).
- Whether anything on the pushed `850bb9d` was published to a package index (pyproject is still
  `0.1.1` at HEAD, no tag; publishing is owner-owed M-VERSIONS work, out of this gate).

Durable notes, lane logs, mutant specs/logs and the STOP record:
`~/.claude/scratch/obs-merge/prepush-otel/` (STOP-origin-main-moved.md, full-lane-HEAD-2.log,
mut/results.txt, mut-own/{results.txt,PP-M*/}, rerun_mutants.sh).
