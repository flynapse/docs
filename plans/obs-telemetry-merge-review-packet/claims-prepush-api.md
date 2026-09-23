# Claims packet: pre-push FULL-DIFF review — api (queue step 16b)

Fable 5 reviewer, 2026-09-22 (night). READ-ONLY on the real tree: nothing in
`/home/aditya/Code/api-obsm` was edited, checked out, stashed or committed; every run used a
`git archive` copy under `~/.claude/scratch/obs-merge/prepush-api/ws/` (`api` at HEAD, plus
sibling archives `core-obsm df6a352`, `utils-obsm 23e849c`, `copilot-mro-obsm 9a68ef23`,
`flynapse-otel c93a9c9`, `shift-optimizer ec383cc`, all clean at archive time, declared via
`SIBLING_CHECKOUTS`). Durable notes and logs: `~/.claude/scratch/obs-merge/prepush-api/`
(`NOTES.md`, `logs/`, `mut/`, `prod.diff`).

## Anchor and range — measured state

| fact | measured |
|---|---|
| repo / branch / HEAD | `/home/aditya/Code/api-obsm` · `obs-merge` · `4bc2d4f69c9f9f165b7fe570cadcdf0efaffe6a0` · tree CLEAN |
| candidate anchor `087e298` | exists; `git merge-base --is-ancestor 087e298 HEAD` holds |
| `087e298..HEAD` | **106 commits** |
| pushed mainline | `origin/langgraph-merge` = `44bd8d1` (the 2026-09-16 R22 batch-2 push). `087e298..44bd8d1` = 6 commits (follow-up batches 1+2, pushed 2026-09-15/16, R22-gated) — already on origin; SKIMMED, not re-gated |
| also already pushed | `34e30c7`, `081b2e6`, `6f22498` (2026-09-16/17 warn-mode work) = the tip of `origin/obs-telemetry-merge`, brought in by merge `37121a3` |
| ratified pre-push range (ledger §"Last gate before any push": merge-base with the pushed mainline .. HEAD) | `44bd8d1..HEAD` = **100 commits**; colleague-era (2026-09-20 onwards) work begins at `4da716f` / merge `37121a3` — **97 commits at full rigour** |

The brief's "begins with colleague-era work" holds for the RATIFIED range; the candidate anchor
`087e298` merely predates two already-pushed spans. Anchor staleness, fully explained by the
remote refs — not a contradiction, so the review proceeded and this header records it.

**First-review spans (no prior closing review): the r10 trimmed batch `fbd394c..58ecfc7`
(`10e2316 6d86976 cb792af 1486732 718b389 f62e554 58ecfc7`) and the weaviate `.remediation`
carve-out `4bc2d4f`.** Both read diff-first, full hunk-by-hunk; their proofs re-executed below.

## Range shape (recomputed, never quoted)

- `087e298..HEAD`: 129 files, +23,436 / −1,094.
- Production only (no tests/docs/poetry.lock): 44 files, +3,104 / −888 — read in FULL
  (`prod.diff` in the scratch dir).
- Test deletions total 206 lines. The only test file >50 deleted is `tests/unit/auth/test_jwks.py`
  (−84): the `c2c99be` rewrite replaced a print-script (import-time file sink, TWO live Cognito
  GETs, zero assertions) with a stubbed-fetch, sentinel-pool, asserting suite — a strengthening,
  not a weakening. The one deleted production file, `routers/cache_management.py` (−247,
  `d6ab632` M-DEADROUTER), was verified unmounted at the anchor (`git grep cache_management
  087e298 -- flynapse_api/main.py` = empty) and took no tests with it. **No guard was weakened
  silently anywhere in the range.**

## Commit coverage reconciliation

Every commit in `44bd8d1..HEAD` sits in exactly one reviewed span: the C2 merge batch
(`claims-C2-api.md`), the post-C2 rounds window (`claims-api-rounds.md`), r6 `517f655..73f2aa3`
(12 commits, incl. the JWKS fix `c2c99be`/`73f2aa3`, the traceparent consumer `6ae9701`,
M-INVITE-FRAGMENT `8d7f587`, M-PERMISSIONS-ENDPOINT `35639cb`), r7 `73f2aa3..847c34c`, r8
`847c34c..b3178f4`, r9 `e3ba207..fbd394c` (+ 8 routed commits `66868f8 a3004d0 d6ab632 cc56667
f985d8d 1b1d088 0c176bb 0e225bd`) — plus the two first-review spans above, reviewed here. The
claims files were used as indexes only; the production half of every commit was read from the
actual diff in `prod.diff`, and the first-review spans' test halves hunk-by-hunk.

## Lanes at `4bc2d4f` (scratch archive; all serial through `pytest-slot.sh`, `DEBUG=false`;
unit and integration inside `ns.sh` — private net namespace, DNS witness, libc netlog)

| lane | result | note |
|---|---|---|
| unit | 978 passed, 20 skipped, 2 failed, 79 s | both failures + 13 of the skips are ARCHIVE-LAYOUT artefacts (below). Collected 1000 = r10's real-tree 982 + the carve-out's 18. |
| integration `-m "not postgres"` | 365 passed, 36 deselected, 1 failed, 14 s | the failure is r9's own documented artefact verbatim (`ws/core/core/fastapi_app.py` absent) |
| smoke + startup + api + middleware | 426 passed, 3 skipped | = r10's 21+69+26+310 exactly; 1 "wrong-checkout import" tag = the known `_ad_materialize_phase_c` false-positive (a module deliberately loaded by path from the PINNED copilot-mro sibling; same ‡ r8/r9 recorded) |
| integration collect | 402 | = r10's count |
| artefact disproof | **2 passed** | after symlinking primary sibling names (`ws/core → core-obsm` etc.), `test_worker_imports_no_gateway` and `test_sibling_repo_reaches_a_sibling_…` both PASS — measured proof the three failures are workspace-shape artefacts, and the worker's no-gateway import property HOLDS |
| Rule B `-m postgres` (DB run 1/2) | **22 passed**, 3.2 s | = the r10 banked clean count (was 10 before `10e2316`) |

**Provenance, read and recorded EVERY run** (the venv `.pth` standing trap): every lane's header
and config warnings print `SIBLING_CHECKOUTS declares core=…/ws/core-obsm,
utils=…/ws/utils-obsm, copilot-mro=…/ws/copilot-mro-obsm — results about X are about THAT tree`;
rootdir = the copy. The archive layout (no second checkout of any repo) is what the two failing
meta-tests assert about, which is their documented job.

**Network census.** Unit lane: DNS witness **0 queries**; libc netlog exactly 2 loopback events
(`getaddrinfo` + `connect 127.0.0.1:43641`), both from the network-guard's OWN forwarder test.
Integration lane: 0 DNS, 0 netlog events. The Cognito fetch log shape (`"Fetching JWKS from"`)
appears in **no lane log** (grep rc=1 across all). **Zero live Cognito fetches in every lane** —
the r9-fix property holds under measurement.

## Proofs re-executed (all via `mutant.sh`: own green baseline, cold bytecode, restore
md5-verified against the real tree's blob; only pytest exit 1 counted as a kill; pytest's own rc
read from the script's result line, never a tee's)

| id | mutant (file · change) | aimed at | result |
|---|---|---|---|
| M1 | `flynapse_api/automations/one_shot.py` · reason gate reverted to `getattr(exc, "reason", None)` (the `718b389` red-before) | `tests/integration/automations/test_one_shot_dispatch.py` + `tests/unit/automations/test_run_reason_family.py` | **KILLED rc=1** 7s |
| M2 | `automations/document_hub_cleanup.py` · `DocumentHubCleanupError` out of the `RunReasonError` family (the other `718b389` red-before) | `test_run_reason_family.py` | **KILLED rc=1** 4s |
| M3 | `startup/weaviate_partitions.py` · seat handler widened to `except Exception` (carve-out edge, production side) | `tests/unit/telemetry/test_gateway_logs_carry_no_exception_text.py` | **KILLED rc=1** 8s |
| M4 | the log sweep itself · `_authored_remediation`'s `not defined_here` condition dropped (carve-out guard weakened) | same file (the "same-named class defined at the seat" plant) | **KILLED rc=1** 9s |
| M5 | `tests/_leak_taint.py` · `MUTATING_METHODS` neutered to `{"__setitem__"}` (the `6d86976`/`cb792af` red-before) | both api_surface sweeps | **KILLED rc=1** 12s |
| M6 | Rule B which-row test · the four wildcard probes deleted (the `10e2316` red-before) — **DB run 2/2**, `-B` justified by DB run 1 having just run the EXACT command green | `tests/integration/registry -m postgres` | **KILLED rc=1** 9s |

**DB-budget ledger: 2 runs of 2** (run 1 = the clean 22-passed Rule B suite; run 2 = M6's mutated
run under `-B`), both serial against `copilot_mro_test`, nothing else running, sanctioned sole
user. Provenance printed and recorded on both. No schema-shaped failure appeared (the DB is
conformant, as briefed).

## Claims

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PP-1 | `api-obsm` @ `4bc2d4f` | repo state matches the brief: branch `obs-merge`, HEAD `4bc2d4f`, clean | `git status --porcelain` empty; `rev-parse` | HOLDS |
| PP-2 | range | the colleague-merge range is `44bd8d1..HEAD` (100), full-rigour span `4da716f`/`37121a3..HEAD` (97); anchor `087e298` stale by 6 pushed commits | remote refs + `rev-list` counts, header above | HOLDS (recorded) |
| PP-3 | `prod.diff` (44 files) | every production change in the range is R22-shaped: constant messages, `failure_fields`, `run_error()` closed vocabulary, spans marked by CLASS with both withholding keywords off; no `str(exc)` reaches a body, column, span or log | full read of the production diff; armed sweeps green in-lane; registers frozen `{keys:0, sites:0}` in ALL THREE sweeps (`response_bodies:634-639`, `run_error_column:539-544`, `gateway_logs` post-`4bc2d4f`) | HOLDS |
| PP-4 | `tests/unit/auth/test_jwks.py`, `tests/conftest.py:75` | no api test session reaches Cognito: `COGNITO_USER_POOL_ID` FORCED empty; fetch stubbed in the rewritten suite | DNS witness 0 queries, netlog loopback-only, fetch log shape absent from every lane log | HOLDS |
| PP-5 | `4bc2d4f` (carve-out) | `_REMEDIATION_ATTRIBUTES` is seat+class+attribute keyed, applies only under a sole-class handler to the bare attribute/`getattr` read; 17 edge plants + a registration test prove the live site is flagged without it; debt back to frozen 0/0 | full diff read; M3 (production edge) and M4 (guard edge) both KILLED; unit lane green incl. the 18 new tests | HOLDS |
| PP-6 | `fbd394c..58ecfc7` (r10) | the five r9 findings built (P2-1 probes-per-shape, P2-3 shared taint walk ×2, P3-11 nine log doors, P3-12 reason-from-TYPE, P3-10/13 prose) match their commit messages' claims | full diff read; M1/M2/M5/M6 killed; Rule B clean 22 = banked count; deferrals (P2-2, P3-1..9, P3-14) recorded in `docs/plans/api-review-r7-batch.md` Future Improvements (`:437 ff`, xdist half at `:457`) | HOLDS |
| PP-7 | `d6ab632` | the deleted cache router was dead: unmounted at the anchor, no importers, no tests deleted with it | `git grep` at `087e298` and `4bc2d4f`; commit diff | HOLDS |
| PP-8 | lanes | the 3 non-green lane items are workspace-shape artefacts, not regressions | symlink re-run: both fail-cases pass with primary-named siblings present; the wrong-checkout tag is the pre-existing `_ad_materialize_phase_c` by-path load from the PINNED sibling | HOLDS (artefacts) |
| PP-9 | `flynapse_api/telemetry/queue_telemetry.py` | metric labels are closed-vocabulary only; identity (tenant.id, enduser.id, run id) rides SPANS only — M-PII-IDS-conformant (ids, never emails/contact records) | diff read: `record_depth`/`record_wait`/`record_claim` attribute sets are literal; `consume_span` puts ids on the span | HOLDS |
| PP-10 | `announcements.py:466` (`"error": error`) | the bell payload's `error` is only ever the `run_error()`-composed column: the recorder is the sole caller that passes it, with the value the run was JUST closed with; the reaped/expired announce paths pass none, so no legacy unsanitised row text can ride the payload | diff read of all `announce_missed_run` call sites | HOLDS |

## Findings

**No P0. No P1. No P2.** Notes (P3/informational, none blocking):

- **P3-1 (informational).** The workspace meta-tests (`test_the_variant_hazard_is_real_in_this_
  workspace_right_now`, `test_sibling_repo_reaches_a_sibling_and_refuses_a_missing_one`,
  `test_worker_imports_no_gateway`'s existence pre-check) hard-code the doubled-checkout
  workspace shape, so any single-checkout archive run reports 2-3 reds a reader must re-derive
  as artefacts every round (r9 did, this review did). Their docstrings say this is deliberate
  (the failure is the prompt to re-decide §2 when the variant trees go away). No action for this
  push; when the `-obsm` trees are removed post-push, these fire by design.
- **P3-2 (informational, pre-existing).** The checkout pin attributes
  `flynapse_api.automations._ad_materialize_phase_c` (deliberately loaded by path from the
  pinned copilot-mro sibling) as a "wrong-checkout import" in smoke — a known false-positive of
  the sentinel's name-prefix heuristic, recorded since r8. Pre-dates this range.
- Deferred-work hygiene is in order: r9's P2-2 (xdist session-half) and the guard-bypass P3s are
  in the plan's Future Improvements with reasons, per the owner's cap — not silently dropped.

## Verdict

**PUSH-CLEAN: 0 P0 · 0 P1 · 0 P2 · 2 P3 (both informational/pre-existing).**
Range `44bd8d1..4bc2d4f` (100 commits; 97 colleague-era at full rigour; first-review rigour on
`fbd394c..58ecfc7` + `4bc2d4f`). 6/6 sampled proofs re-executed KILLED with pytest exit 1;
DB budget 2/2, serial, provenance recorded; zero Cognito traffic measured in every lane; all
three exception-text debt registers frozen empty; no silent guard weakening. The api push gate
is OPEN from this review's side.
