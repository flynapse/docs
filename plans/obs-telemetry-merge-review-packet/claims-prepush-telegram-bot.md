# Claims packet: telegram-bot pre-push FULL-DIFF review (`3102fcc..47a08b7`, 31 commits)

Pre-push gate review (queue step 16b, one of the nine ratified per-repo colleague-scope reviews;
review-trust framework, ledger Addendum 228). Reviewer: Fable, 2026-09-22. READ-ONLY on the real
tree throughout; every run from `git archive` copies under
`~/.claude/scratch/obs-merge/prepush-telegram/` (`ws-head` for lanes, `ws-mut` for mutations —
no worktree touched the real checkout). Durable logs and notes in the same directory
(`notes.md`, `logs/`, `mutation-results.txt`, `detector_rescan.py`).

| repo | tree | branch | HEAD | remote | range |
|---|---|---|---|---|---|
| telegram-bot | `/home/aditya/Code/telegram-bot` (clean, `git status --porcelain` empty) | `main` | `47a08b7a39a682743dada74e44cfcae0da853b67` | `git ls-remote origin refs/heads/main` = `3102fcc400273353835d311b2a91e1ef1307d28c` (unmoved) | `3102fcc..47a08b7`, `git rev-list --count` = 31 |

**How I ran it.**
- **Copies.** telegram-bot archived at `47a08b7`; flynapse-otel archived at its live committed
  HEAD `c93a9c9` (clean when read) beside it, where the provenance test requires the sibling.
- **Interpreter.** telegram-bot's own `.venv` (Python 3.11.15), `VIRTUAL_ENV` unset,
  `PYTHONPATH=<otel copy>:<copy>:<copy>/tests`, a fresh `PYTHONPYCACHEPREFIX` per run
  (`mktemp -d` in the runner), `-p no:cacheprovider`. Provenance printed from pytest's own
  output: both `telegram_bot.__file__` and `flynapse_otel.__file__` resolve into the scratch
  copies (`logs/provenance.log`).
- **No database, no network.** `BOT_TEST_DB_URL=postgresql://127.0.0.1:1/none` (closed loopback
  port) so the Postgres-backed tests SKIP through their own fixture; skip reasons recomputed
  (`-rs`): 299 "no Postgres reachable" + 1 opt-in live-stack test = the 300. No netguard of my
  own was built (three prior rounds measured 0 refusals with one); no test in the lane needed a
  live service — the suite drives `httpx.MockTransport` and loopback stubs. `copilot_mro_test`
  untouched; no DB MCP used.
- **Every pytest through `pytest-slot.sh`** (no exit-75 occurred). Mutations through `mutant.sh`
  (baseline-checked, cold bytecode, md5-verified restore — its own contract). This repo's lane is
  serial: the `.venv` has no pytest-xdist, matching every banked round.
- **Exit statuses.** Taken from the runner's `RC=` line (pytest's own `$?`), never a pipe's.

**Full lane at HEAD, recomputed:** `2229 passed, 300 skipped, rc 0` (133 s; 2 warnings, both the
OTel SDK's own `LoggingHandler` deprecation, not the range's). Matches `a6b94cc`'s recorded count;
the three commits above it add no tests (doc/prose + one rename). `ruff check .` clean over the
whole copy (ruff 0.16.3); `mypy` clean over the five key touched modules (`client.py`,
`errors.py`, `auth.py`, `telemetry.py`, `failure.py`).

**Coverage reconciliation.** 24 of the 31 commits carry independent review already:
`8ca41ea`,`fa37f7e` (TG-R1) → `cd5930e` (fixes; implementer-proved); `cda382c`,`dcc4a4c`,
`47c6fbd`,`b510c75` (TG-R2) → `12f2968`,`a3e2e6b`,`385b1f4` (TG-R2Δ) → `0f0337e`
(implementer-proved); `52cd5b6`..`cfb1d98` (r3); `0551de6`..`0af46b1` (r4); `b30d0a3`..`645b334`
(r5). I read every commit's actual diff and reconciled it file-by-file against those packets: no
undocumented production change, no silent guard weakening (every removed test function is a
reviewed replacement — leak-pinning premises inverted into absence guards, the 1-case ambient test
parametrized to 3). The SEVEN commits `e0da52b`..`47a08b7` (the r5 fix batch) had NO independent
review before this one and got first-review rigour here, including re-executed proofs for each
code-bearing commit.

## Proofs re-executed (8/8 as expected; `mutation-results.txt`, all restores verified by mutant.sh)

| # | target commit | mutant / plant | aimed at | result |
|---|---|---|---|---|
| A | `d43bd5d` (unreviewed) | `_off_loop` reverted to direct `asyncio.to_thread(call)` (the pre-fix shape — the red-before) | `test_facade_files_flightops.py` | **KILLED rc=1** |
| B | `a6b94cc` (unreviewed) | G14: `ensure_id_token`'s no-refresh refusal, `unchained` dropped | `test_cognito_auth.py` | **KILLED rc=1** |
| C | `a6b94cc` (unreviewed) | G15: `_token_set`'s no-ID-token refusal, `unchained` dropped | `test_cognito_auth.py` | **KILLED rc=1** |
| D | `e0da52b` (unreviewed) | M8 analogue: `{exc}` appended to the auth raise's message | `test_cognito_auth.py` | **KILLED rc=1** |
| E | `f72f291` (unreviewed) | X1: `send_json` back to `raise … from exc`, `unchained` out | `test_raises_in_handlers_are_unchained.py` ALONE | **KILLED rc=1** — the new AST guard catches the chain half by itself |
| F | `0f0337e` (implementer-proved only) | `_args_depth` rule off (`_stood_in(record.args)`) | `test_stdlib_logs_to_otlp.py` | **KILLED rc=1** — now reviewer-proved |
| G | `cd5930e` (implementer-proved only) | aliased-opener plant in `screening.py` (`use_span as _activate` + un-literaled `start_span`) — TG1-05's defeat class | `test_span_openers_pass_withholding_literals.py` | **KILLED rc=1** — now reviewer-proved |
| H | `47a08b7`'s claim | a `_WatchOver` message drifting to quote `{error}` | `test_raises_in_handlers_are_unchained.py` | **KILLED rc=1** — `ALLOWED_CHAINS`' equality witness pins the exact source text |

**Key absence checks re-run explicitly** (`logs/witnesses.log`): the log source sweep, both
behavioural log sinks, spans live+export, the chain-half AST guard, the `unchained` mechanism
tests, the Cognito set and the reply-sink conjunction test (`test_progress_editing.py`, a real
copilot turn through the real client with an h11 sentinel): **208 passed, 2 skipped** (the two
psycopg cases), rc 0. No raw exception text in bot replies or logs on any converted path.

## Claims table

| # | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PP-TG-01 | repo/remote state | main clean at `47a08b7`; `origin/main` = `3102fcc` unmoved; 31 commits | `git status --porcelain`, `rev-parse`, `ls-remote`, `rev-list --count` (re-checked before filing) | SETTLED |
| PP-TG-02 | full lane | 2229 passed + 300 skipped, rc 0 at HEAD, recomputed on the archive copy with pinned provenance | `logs/full-head.log` (RC=0), `logs/provenance.log` | SETTLED |
| PP-TG-03 | the 300 skips | 299 Postgres fixture-gated + 1 opt-in live-stack; no test needs a live DB or network | `logs/skips.log` (`-rs` recount) | SETTLED — no finding |
| PP-TG-04 | 31 commits | every diff reconciles with the banked packets; no undocumented production change; no guard weakened silently (removed tests are reviewed replacements) | file-by-file diff read; `git log --diff-filter=D` empty for tests/; removed-function census traced to replacements | SETTLED |
| PP-TG-05 | `flynapse_client/client.py:116-131` (`_off_loop`, `d43bd5d`) | a client failure crosses the to_thread seam as a VALUE and is raised loop-side under `unchained`; the revert is red | proof A KILLED | SETTLED |
| PP-TG-06 | `flynapse_client/auth.py:187-191`, `:229-231` (`a6b94cc`) | auth's two out-of-handler refusals are held by the parametrized ambient test (r5 G14/G15 closed) | proofs B, C KILLED | SETTLED |
| PP-TG-07 | `flynapse_client/auth.py:216-217` (`e0da52b`) | the class-at-the-raise rewrite is held by the behavioural Cognito set (the commit adds no test of its own) | proof D KILLED | SETTLED |
| PP-TG-08 | `tests/unit/telemetry/test_raises_in_handlers_are_unchained.py` (`f72f291`) | the chain half of the idiom is guarded in-repo: a constructed raise in a handler outside `with unchained():`+`from None` is red on the AST guard alone; equality witness pins `ALLOWED_CHAINS` | proofs E, H KILLED; guard read line-by-line (alias resolution, decoy `def unchained` rejected, relative imports resolved, self-tests) | SETTLED |
| PP-TG-09 | `telegram_bot/telemetry.py:483` + `_args_depth` (`0f0337e`) | the lone-mapping args rule (TG2D-06/P2-N1) — previously implementer-proved only | proof F KILLED | SETTLED — now reviewer-proved |
| PP-TG-10 | span sweep resolver (`cd5930e`) | TG1-05's defeat class (aliased/unbound openers) is caught — previously implementer-proved only | proof G KILLED | SETTLED — now reviewer-proved |
| PP-TG-11 | `flynapse_client/errors.py:95-110` (`a6b94cc` G3 deletion) | the deleted `__suppress_context__` line was dead: assigning `__cause__` sets the flag; observed via the mechanism test (no-`from` raise leaves a caller's handler with flag set, cause/context None) | in the witness run (`test_unchained_raise.py` green, incl. `test_a_raise_with_no_from_clause_…`); proofs B/C also assert the flag | SETTLED |
| PP-TG-12 | lint/type state | ruff clean whole-tree; mypy clean over the five key touched modules | run on the copy | SETTLED |
| PP-TG-13 | TG1-18 / TG1-19 (recorded, not mine to reopen) | no commit in range makes either WORSE: stdout's third-party rendering unchanged since `fa37f7e` (by ruling); the `failure.py` port improved (shape gate on both SQLSTATE sources), not diverged from M-FAILURE-HOME | diff read; `telegram_bot/failure.py` at HEAD vs the port's contract | SETTLED — confirmed no-worse |
| PP-TG-14 | `docs/plans/exception-text-withholding.md` P2-1 entry + the underscore paragraph in Future Improvements | **FINDING P3 (plan staleness, recurring shape):** the plan's rescan count ("unmutated 7", dated at otel `d1e531f`) and the `_WatchOver` underscore-blind-spot paragraph are stale at flynapse-otel HEAD: at `c93a9c9` the scan is **9** — otel `282a866` (detector r7 P2-4, "a raised private or name-mangled class is a construction") closed the blind spot AFTER `47a08b7`, so both `_WatchOver … headline_of(error)` raises now flag (`document_watch.py:566`, `:573`, `raise.caught-text`). Over-reports in substance: `headline_of` carries class/status/door only; the raise sink is never sanctioned, same class as triage row 4. No leak; the detector is NOT adopted here; no green guard depends on "7"; the sites' exact text is pinned in-repo (proof H). Fix at adoption: re-measure and re-triage against that day's otel HEAD; update the underscore paragraph then. | `detector_rescan.py` at `c93a9c9`: 53 modules, TOTAL 9 (`logs/detector-rescan.log`); otel `git log d1e531f..c93a9c9` | **OPEN (P3)** |
| PP-TG-15 | `test_raises_in_handlers_are_unchained.py` `_unchained_names` | **FINDING P3 (record-only):** a function PARAMETER named `unchained` is not treated as a rebind (module-level `def`/`class`/assign rebinds are), so a deliberately adversarial `def f(unchained): with unchained(): raise …` shadow could pass a decoy CM. Zero instances; fail-open only under adversarial code; conversely `async with unchained():` would be fail-closed (flagged though safe). | guard source read; shapes traced | **OPEN (P3)** |
| PP-TG-16 | `pyproject.toml:65` | push-order note: flynapse-otel is a PATH dependency (`../flynapse-otel`, develop=true); the bot at HEAD relies on the shared bootstrap's export seat (`flynapse_otel.withholding`, since otel `eac44c0`) — the push wave must carry flynapse-otel (its own pre-push lane exists). No version-resolution hazard (no version pin to go stale); no code defect. | pyproject read; import sites grepped | **OPEN (P3, coordination)** |
| PP-TG-17 | `claims-satellites-rounds.md` trees table | index nit: the r5 fix batch is `645b334..47a08b7` = **7** commits (`e0da52b` is its first); the table says "`e0da52b..47a08b7` = the r5 fix batch (6 commits)". Index-only; no evidence rests on it. | `git rev-list --count` both ranges | **OPEN (P3, docs index)** |

## Verdict

**PUSH-CLEAN: 0 P0 / 0 P1 / 0 P2 / 4 P3** (PP-TG-14 plan-staleness vs the moving otel HEAD,
PP-TG-15 a contrived guard shadow, PP-TG-16 push-order coordination, PP-TG-17 an index nit).
Nothing gates the push. No exception text, secret or pilot content reaches a reply, a log line, a
span or an exported record on any path the range touches, and every unreviewed commit's guard was
seen to fail under a mutation aimed at it.
