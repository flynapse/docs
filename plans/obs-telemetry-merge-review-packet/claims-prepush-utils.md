# Claims packet — utils PRE-PUSH full-diff review (queue step 16b)

**Verdict: PUSH-CLEAN — P0 0 · P1 0 · P2 1 · P3 0.** (The push gate is P0/P1 only; the one P2 is
PPU-08, a sweep-coverage gap whose live production line PRE-dates this range.)

Independent pre-push reviewer (Fable), 2026-09-22. READ-ONLY on the real tree throughout.

## Anchor and range

- Tree: `/home/aditya/Code/utils-obsm`, branch `obs-merge`, HEAD **`23e849c`**, clean (verified at start).
- **The literal `git merge-base main obs-merge` is WRONG-ERA and was rejected by measurement**: local
  and `origin/main` both sit at `e13e0ab` (2026-08-17); utils' rebuild work was never merged to `main`.
  The mainline-of-record is `langgraph-merge`, pushed at **`289ba71`** (obs10 batch 2, 2026-09-15,
  = `origin/langgraph-merge`), which is an ancestor of `obs-merge` and
  `merge-base(langgraph-merge, obs-merge)`.
- **Range reviewed: `289ba71..23e849c` — 141 commits (138 first-parent)**, beginning exactly with the
  C1 colleague merge `9c5a8d7` / triage `e6b464e` (2026-09-19), as the ledger describes. The phases
  ≤P10 (Fable-gated R12–R21) are excluded by construction: they are all at or below `289ba71`.
- Claims indexes reconciled against (never as evidence): `claims-C1-utils-B1-core.md`,
  `claims-utils-rounds.md`, `claims-utils-r5..r9.md`, `claims-G10-weaviate-spans.md`.
- **Unreviewed tail**: `fe45c35..23e849c` (9 commits — the r9 fix batch + the M-FAILURE-HOME
  re-exports) has had NO prior round; it gets first-review rigour here.

## Pins and lane recipe

- Scratch: `~/.claude/scratch/obs-merge/prepush-utils/` — `git archive` copies only, real trees untouched.
  - `ws/utils-obsm` = archive of `23e849c` (172 files, count-verified vs `ls-tree`).
  - `ws/flynapse-otel` = archive of **`c93a9c9`** (77 files) — equals the live clean checkout's HEAD.
  - `ws/copilot-mro-obsm` = archive of **`e76fa21c`** (2046 files) — the committed HEAD; the live
    worktree had 2 dirty files, never read.
  - Every other workspace checkout symlinked beside the copy (the `parallel-commits.sh -L` recipe).
- Lane: `ENV_FILE=api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=<copy>:core-obsm:<fo-pin>:<plug>`
  `pytest-slot.sh -- api/.venv python -m pytest -p prepushreport -p no:randomly -o addopts="-ra --strict-markers" -n 2 -q tests`.
  A session-start plugin records rootdir + `utils.__file__` + `flynapse_otel.__file__` per process
  (`logs/*.proof`): all inside the copy in every copy run; real-tree runs resolve
  `/home/aditya/Code/utils-obsm` + `/home/aditya/Code/flynapse-otel` (= the `c93a9c9` pin).

## Lane totals (recomputed, not quoted)

| run | tree | result | exit |
|---|---|---|---|
| full lane at HEAD (run 1) | copy | 2036 passed, 7 failed (2043 items), 47.6 s | 1 |
| full lane at HEAD (run 2, identity-proofed) | copy | 2036 passed, 7 failed — failure set md5-identical to run 1 | 1 |
| the 3 location-sensitive guard files, read-only | REAL tree | **48 passed, 0 failed, 2.93 s; `git status` byte-identical before/after** | 0 |

All 7 copy failures live in `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` (6) and
`tests/unit/safety/test_no_provenance_laundering.py` (1): each is a copy-location artefact — symlinked
siblings resolve to `/home/aditya/Code/*` while the listing shows `ws/*` paths, and a `git archive`
carries no `.git`, so the git-family exclusion of pre-merge primaries cannot pair `utils` with
`utils-obsm`. Proven, not argued: the same tests are 48/48 green read-only in the real tree.
2036 + 7 = 2043 items — reproduces the rulings-batch reference (2043 passed in the real tree).

## Claims table

(rows accumulate as the review proceeds; final totals at the end)

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PPU-01 | whole tree | HEAD `23e849c` on `obs-merge`, clean; anchor `289ba71` measured via `langgraph-merge`; range = colleague-merge work only | `git status/rev-parse/merge-base/rev-list` (see Anchor) | VERIFIED |
| PPU-02 | whole suite | Full lane at HEAD: 2043 items, green modulo 7 proven copy-location artefacts; real-tree trio 48/48, status byte-identical | two copy lane runs + one read-only real-tree run, exits 1/1/0 | VERIFIED |
| PPU-03 | `utils/observability/log_bridge.py:113-120`; `tests/unit/observability/test_log_bridge_flattening.py:102-160` | b276c5a: one reserved set, the seat's own binding source-pinned (BinOp of exactly the two NAMES, no Constant/Set/Call) + value equality + live-record subset on the seat's set | diff read; seam to the d6f8fbf re-export verified at HEAD (the derivation pin follows the seat to `flynapse_otel.failure` and pins the re-export by identity); mutation M6 below | VERIFIED (production behavior-neutral: same union, one name) |
| PPU-04 | `utils/_stdlib_records.py` (new), `utils/_loguru_default.py:86-135,206-213`, `utils/observability/intercept.py:184-241`, `utils/observability/log_bridge.py:210-268` | 7613a4b + f799876 (routed P1, tb-review-cd C-1=D-1): unconfigured processes write withheld failure fields — record-factory subclass for the basicConfig path, extras written by the safe sink, one `flat_attributes` flattening for all three stdout seats; `setup_logging` stands the factory down (intercept saves/restores) | full diff read at first-review rigour. `flatten` reads ONLY `record["extra"]`, so the `_json_stdout_sink` swap to `flat_attributes(record["extra"])` is exactly equivalent (read at HEAD `log_bridge.py:138-158`). `STANDARD_RECORD_ATTRIBUTES` explicitly unions `{"message","asctime"}` (fo `failure.py:734-736`), so a multi-handler record's second `getMessage` cannot re-render Formatter-stamped fields as extras. `rendered_extras` fails closed to `WITHHOLDING_FAILED`; BaseException propagates by the module-wide declared rule. Probe preamble imports `os` (non-issue I chased). Mutants M5, M7; red-before probe below | VERIFIED |
| PPU-05 | `tests/unit/observability/test_legacy_family_inventory.py` (`860543c` + batch) | The r9 P2-1 ask landed: the two handed-over conditions (chained targets; binding count on the import path), 25-shape `_REVIEW_R9_CORPUS` held to measured outcomes, register bidirectionally pinned (`reached | older == set(_NOT_SEEN_BY_DESIGN)`) | diff read; mutants M3, M4 | VERIFIED |
| PPU-06 | `utils/_exception_text.py`, `utils/observability/failure.py` (d6f8fbf, e13e3fd, 23e849c) | M-FAILURE-HOME swap: both modules are pure re-exports of `flynapse_otel.failure` | AST comparison, all docstrings stripped: the 635 deleted `_exception_text` lines = 43 top-level names, ALL present in fo `c93a9c9`, code-identical except one inlined single-use local in `rendered_failure` (semantically identical); `failure.py`'s deleted `failure_fields`/`aws_error_code`/2 constants AST-identical. Fresh-subprocess identity re-proof: 18 names each module, every one `is` fo's object, nothing of their own | VERIFIED — zero behavior change |
| PPU-07 | package import contract | `import utils` loads NO `opentelemetry*`; `flynapse_otel.failure` legitimately loaded; `UTILS_PARITY_SHA` in no code | fresh subprocess (my own, not the suite): `otel-after-import-utils: []`; `git grep` at `23e849c` (utils) and `c93a9c9` (fo): hits only in plan prose, zero in code; fo's parity test retired at `50bcf30` | VERIFIED |
| PPU-08 | `utils/observability/metrics.py:159-169` vs `tests/unit/observability/test_utils_logs_no_exception_text.py:668-674` | **FINDING (P2)**: `_dropped` writes `reason=str(exc)` into a log extra — a real `str(exc)`-into-log line the sweep passes silently: the detector walks only `except` bodies, so a SAME-module helper handed the exception is invisible, and `KNOWN_GAPS` names only "a helper in ANOTHER module" | proven by execution: `leaks()` returns `[]` for both a synthetic same-module-helper plant and the real `metrics.py`. Line introduced at `520d5af` (phase 1a, PRE-range, R12–R21-gated era). Mechanism ledgered as G24-F13 (OPEN/DEFERRED §6, fix = M-SHARED-CHECK) — but the live instance is recorded NOWHERE (metrics.py in neither `LEAK_BACKLOG` nor `PAID_DOWN`) and the register understates the gap class. Content risk low (registry/kind/unhashable messages are code-shaped) | **OPEN — P2** (pre-range line; in-range register understatement). One-line fix: `reason=type(exc).__name__` or `**failure_fields(exc)`, plus widen the KNOWN_GAPS wording |
| PPU-09 | `tests/` (range-wide) | No guard weakened: every deleted test/assertion maps to an indexed redesign (M-LEGACY-DELETE, M-LEGACY-TENANT, G.110/G.115 live-span move, sweep self-discovery superseding the postgres-only file); `LAYOUT_EXEMPTIONS` is `{}` and the layout guard untouched in range; the deleted postgres sweep's successor covers `postgres_service` with a minus-one ratchet floor (7, true 8) | `git diff` deleted-line audit; register reads at HEAD | VERIFIED |
| PPU-10 | `utils/*` (range-wide) | Production leak screen: added lines carrying `str(exc)`/f-string interpolation all resolve safe — `_extract_retry_after` parses `\d+` only and logs the integer; tenancy refusals are constant sentences with ids as attributes (r6/r7-indexed); `parse_s3_url` raises name fields, not the URL; registry shape errors quote code constants; span seats write bounded vocab, `record_exception=False`, class names only | pattern screen over the full `289ba71..23e849c` production diff + contextual reads of every flagged site | VERIFIED (except PPU-08) |

| PPU-11 | range history | Nothing added-then-removed hides in the cumulative diff: per-commit patch screen finds no transient secret; the two deleted test files (`test_utils_resolves_to_this_checkout.py` at 4a7517f, `test_postgres_service_logs_no_exception_text.py` at 1cdebad) both have verified successors (the find_spec checkout pin; the self-discovering sweep with `postgres_service.py: 7` ratchet) | `git log -p` screens over `289ba71..23e849c` | VERIFIED |
| PPU-12 | round chain | The index chain is continuous and no P0/P1 is open anywhere in it: C1 → G-lanes/r1–r4 (rounds file, with its "what no round covered" table) → r5 → r6 → r7 (FIX-FIRST) → r8 (MERGE-CLEAN 0/0) → r9 (MERGE-CLEAN 0/0) → the r9 fix batch + re-exports (this review, first rigour). C1's open rows: C1-14 closed by G.10's one-factory rework (verified at `_weaviate_span`), C1-15 routed to other repos, C1-16/17 ledgered deferrals since reworked by the outcome-vocabulary (`1a2680e`) and escape-handling (`80b242e`, `7dc9d6e`) commits | index reads + tree greps | VERIFIED |
| PPU-13 | `tests/` (range-wide) | Added skip/xfail markers are all probe machinery (the swap-then-skip guard cases, armed probes, sibling-absence conditions) — no guard weakened by marker; real-tree lane runs 0 skipped | diff screen + lane tallies | VERIFIED |
| PPU-14 | `utils/_stdlib_records.py` + `utils/_loguru_default.py` at `fe45c35` vs `23e849c` | RED-BEFORE re-executed behaviorally: a basicConfig process logging `extra=failure_fields(exc)` writes `ERROR script dispatch failed` BARE at `fe45c35` and `... | {'error_type': 'RuntimeError', 'stack': '<frame headers>'}` at HEAD; the exception's message (a planted sentinel) absent in BOTH | probe run on `git archive` copies of both commits (`base/`, `ws/`), outputs in scratch | VERIFIED |

## Mutation re-execution (`mutant.sh`, cold cache, baseline-checked, scratch copies only)

| mutant | seat | aimed lane | expected | result |
|---|---|---|---|---|
| M1 (banked IMX1, re-aimed at the re-export era) | `ws/flynapse-otel/flynapse_otel/failure.py:362` — drop `pending.extend(_held_in_args(link))` | `test_stdout_sinks_withhold_exception_text.py` | KILLED | **KILLED rc=1 10s** — utils' guard reaches the OTel implementation THROUGH the re-export |
| M2 (banked IMS1) | `tests/conftest.py` — drop the setup-phase `_LOADED.enforce` finally | `test_checkout_variant_pin.py` | KILLED | **KILLED rc=1 32s** |
| M3 (banked MB5-class) | inventory `bound != 1` → `bound > 2` (import-path binding count) | `test_legacy_family_inventory.py` | KILLED | **KILLED rc=1 6s** |
| M4 (banked IMC, new register) | delete a `_NOT_SEEN_BY_DESIGN` entry | `test_legacy_family_inventory.py` | KILLED | **KILLED rc=1 10s** |
| M5 (own, the P1 seat) | `ExtrasInMessageRecord.getMessage` drops the extras suffix | `test_unconfigured_extras_reach_the_line.py` | KILLED | **KILLED rc=1 17s** |
| M6 (own, b276c5a seat) | `_RESERVED_ATTRIBUTES` replaced by a VALUE-IDENTICAL hand-typed literal (value equality stays green; only the source pin can catch it) | `test_log_bridge_flattening.py` | KILLED | **KILLED rc=1 8s** |
| M7 (own, MA4-class) | `rendered_extras` withholding dropped (`withheld = dict(extras)`) | `test_unconfigured_extras_reach_the_line.py` | KILLED | **KILLED rc=1 8s** |

**7 of 7 KILLED** (4 banked re-executions + 3 of my own), every run `mutant.sh` (cold cache,
green baseline enforced, restore verified), every pytest through `pytest-slot.sh`, and every run's
rootdir + `utils.__file__` + `flynapse_otel.__file__` recorded inside the pinned copies
(`logs/mutants.proof`, deduplicates to exactly the three copy paths).

## Late rows

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PPU-15 | `utils/_exception_text.py` ↔ `flynapse_otel/failure.py` | r9's P3-2/U9-08 (the renderers diverged; the parity pin hid it) is RESOLVED, not merely re-pinned: fo `c93a9c9` carries the full fabb94c-era implementation (`_held_in_args` at `:366`, `_MAX_LINKS=256`), utils deleted its copy, ONE definition remains; fo's parity test retired (`50bcf30`) | the PPU-06 AST proof; M1 proves utils' stdout guard still kills a mutation IN the fo implementation through the re-export | VERIFIED |
| PPU-16 | lane totals | The tail's recorded figures reconcile with mine: r9-batch plan 2004 (item a) → 2041 (item b) → +2 identity tests (d6f8fbf, 23e849c) = **2043**, my measured item count | recomputation | VERIFIED |

## What I did not test

- Any live collector, Weaviate, AWS, SMTP or Postgres path; no docker, no network writes.
- Per-commit greenness of the 9-commit tail (`fe45c35..23e849c`): HEAD is proven; the
  intermediate lanes are the implementer's own recorded figures (2004/2041), which reconcile
  (PPU-16) but were not re-run per commit.
- The other banked mutants beyond the 4 re-executed (r9 ran 18; the implementer 34+MB1-5; my
  sample re-proves the load-bearing seats, including both post-r9 production seats).
- flynapse-otel's own suite at `c93a9c9` (the fo lane owns it); I proved utils' guards reach its
  `failure.py` (M1) and its lazy package import from utils' side (PPU-07).
- copilot-mro beyond the pinned `e76fa21c` archive the inventory limb parsed.

## Verdict

**PUSH-CLEAN — P0 0 · P1 0 · P2 1 · P3 0.**

16 claims: 15 VERIFIED, 1 OPEN (PPU-08, P2 — `metrics.py:169` `reason=str(exc)` invisible to the
log sweep through a SAME-module helper; mechanism ledgered G24-F13/DEFERRED, line pre-range at
`520d5af`; asks: the one-line production fix, a `KNOWN_GAPS` wording widening, and a
`LEAK_BACKLOG` or paydown entry for `metrics.py` — routed to the queued fix lane, NOT
push-blocking). Anchor `289ba71` (origin/langgraph-merge), range `289ba71..23e849c`, 141 commits,
HEAD clean before and after; both real trees byte-untouched (read-only runs proven by
`git status` capture).
