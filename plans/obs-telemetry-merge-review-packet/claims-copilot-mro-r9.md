# Claims packet — copilot-mro review r9 (`557a178f..16760afc`, 16 commits — the r8 fix batch)

Independent adversarial closing review, Fable 5, 2026-09-22. **Verdict: MERGE-CLEAN** — **0 P0 · 0 P1 ·
0 P2 · 4 P3.** Every r8 merge-blocking and P2 finding is closed in the form r8 asked for or better;
P1-1's lock is measured across two sessions and mutation-proved both directions; both r8 survivors
(SV1b, SV3) now die to the new guards.

Read-only on every code tree: nothing edited, committed, checked out or stashed in `copilot-mro-obsm`
or any sibling; nothing pushed; nothing amended. At the end of the review the real tree is still
`16760afc` with a clean status (only ignored bytecode; its two stashes are pre-existing, other-branch,
untouched). All runs in a `git clone --shared` of `16760afc` at
`~/.claude/scratch/obs-merge/mro-r9/wsp/copilot-mro-obsm` (clean after every mutation round — mutant.sh
restore verified), beside ARCHIVES of the siblings pinned at utils-obsm `2f33a1c`, core-obsm `19403fa`,
api-obsm `58ecfc7`, flynapse-otel `ff20ca9`, dashboard-obsm `f8c4614`, shift-optimizer `79fe140`
(`wsp/SIBLINGS.txt`); `PYTHONPATH` points at the archives, so no sibling could move under this review.
Netguard `sitecustomize` (r8's, verbatim): strips the api venv's primary-checkout `.pth` entries,
refuses + logs every non-loopback connect/DNS and every loopback port but 5432, wraps
`psycopg2.connect`. Unit and agent_sdk lanes inside `unshare -rn`. Every run through
`/home/aditya/Code/pytest-slot.sh`. Checkout pin proved under the lane env:
`copilot_mro.app.__file__` = the clone and `copilot_mro.__path__` = the clone only (the netguard
stripped the primary entries). DB-writing runs against `copilot_mro_test`: **two, both serial** (the
db lane and one `-rA` re-listing of the roundtrip file); the mutation rounds used pg_temp-only
`-k` selections that write no real row (r8 precedent), all against `copilot_mro_test` only. No DDL.

| repo | tree under review | branch | range | siblings |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `557a178f..16760afc` — HEAD `16760afc2c282e174601dfc4d7c6d93c8289fd43`, verified clean at start and at end | pinned archives (above) |

**Lane recipe, as run:** `pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest -o
addopts="-ra --strict-markers" -p no:cacheprovider` from the clone root, `ENV_FILE=/home/aditya/Code/api/.env
DEBUG=false POSTGRES_DB=copilot_mro_test`, `PYTHONPATH=<netguard>:<clone>:core-obsm:utils-obsm:api-obsm:flynapse-otel`
(all archive paths under `wsp/`). `-n 2` on unit and agent_sdk only, serial elsewhere.

---

## Seam check: `735f8213..557a178f` (29 commits — the obs-merge-cli merge)

r8 read up to `735f8213`; these commits reached the tree before the fix batch. Coverage:

- 9 initial CLI commits (`a18635e9..7416d7a4`): reviewed — `claims-copilot-mro-cli-r1.md` (FIX-FIRST 0/2/3/8).
- 11 r1-fix commits (`7416d7a4..f1100629`): reviewed — `claims-copilot-mro-cli-r2.md` (MERGE-CLEAN 0/0/2/4).
- **7 r2-fix commits** (`10ef633a`, `9d6be4b6`, `7880bc44`, `a532a23c`, `0849309a`, `42b9c1b2`, `b5cf1524`)
  **and the merge commit `557a178f` itself: no independent review.** Covered only by the implementer's own
  record (SDD ledger "cli r2 fixes DONE + MERGED": mutants M1–M6 killed after the fix-forward; the merging
  agent's own lanes green, the one predicted conflict resolved as a 135-entry union). The cli-r2 verdict was
  already MERGE-CLEAN (P2/P3 only) and Add. 212's owner simplification applied the light recipe to P3 fixes.
  **Gap surfaced for the controller's ledger; not re-reviewed in depth here, per the brief.**

---

## Findings, ranked

### No P0, no P1, no P2

The fix batch does what Addendum 226 claims, where it claims it. Every claim I sampled reproduced from
ground; nothing merge-blocking remains in this range.

### P3-1 — the feedback liveness gate has no two-session lock proof of its own

`feedback.py`'s `_SAVE_FEEDBACK_SQL` reads the block under `FOR SHARE` inside `NOT EXISTS`; its
cross-session behaviour ("a feedback that arrives during the delete waits and is refused") is asserted
from `FOR SHARE` semantics, not measured — the two-session EPQ proof exists only for the settle gate
(`test_a_settle_racing_an_uncommitted_delete_waits_for_it_then_lands_anonymised` /
`test_an_in_flight_settle_holds_off_the_deletes_first_statement`, both PASSED here), whose mechanism
(locking SELECT vs a soft-delete `UPDATE` row lock, same isolation level, same pool) is the same genus.
The one-session refusal is measured on pg_temp shadows and the statement shape is pinned (P25a and P25b
both KILLED here). Cheap to add a mirrored two-session pair later; not blocking.

### P3-2 — the behavioural re-seed rule can be laundered by a double-reporting detector edit

`_unexplained` demands the NEW detector find each admitted `(key, code)` excess more than the OLD one
does over today's tree. A guard edit that deliberately reports an existing site twice under the same
`(key, code)` (a second pattern matching the same call) manufactures that delta without any real
discovery. This is the deliberate-guard-edit class the ratchet doctrine accepts (guards prove shape;
the guard file itself is reviewed, and `REVIEWED_RESEEDS` is pinned exactly to `ac43ff2c` by
`test_the_reviewed_reseeds_are_exactly_the_one_that_predates_the_rule`). Recorded so the next round
does not rediscover it.

### P3-3 — pipeline-level unit tests reach for a live Postgres (~80 attempts per unit run)

The psycopg2-wrapping netguard (which r8's unit census predated — its socket patch cannot see libpq)
shows ~80 `pg-connect('localhost',5432,'copilot_mro_test')` attempts inside the netns unit lane, from
pipeline-composition tests (`test_query_adapter_binds_accumulator`, `test_route_kwargs_composed_path`,
`test_backend_lifecycle_and_failures`, `test_served_path_streaming_and_accounting`, …) whose
never-raise accounting seams (usage/model-call ledgers, and now the settle writer) swallow the refused
connection — every one of them green without a database. The range's NEW
`test_the_pipeline_records_every_settled_turn_facts…` test contributes 7 of them (its settle seam is a
fake; the attempts come from the pipeline's other best-effort accounting). Pre-range genus,
instrument-revealed, no correctness effect; it costs latency per run and quietly touches the real test
DB when one is up. Candidate for a later seam-defaults sweep.

### P3-4 — promtool validation of the ten rewritten alert branches is still owed (declared)

P2-4's per-(job,instance) gate rewrote all ten first-event branches; `promtool check rules` was not run
(docker-gated), as the commit itself declares. The PromQL was verified here by hand (set-operator
matching semantics, precedence, the three limbs' truth table) and by the shipped simulator (P24a
re-KILLED: the newly-started limb's `[1d]` narrowed to `[1h]` dies to the 5-hour-stall case). Carries
the batch's own declaration forward as the residual it is; the real otelcol/prometheus validation rides
the existing CI/owner item.

Folded residuals (recorded, unnumbered): `declared_nullable_columns_exist` skips a relation none of
whose declared columns exist live (deferred to the NOT-NULL/relation properties, which do not cover an
all-nullable drift — contrived, since every tenant relation declares live NOT NULL injected columns);
a future committed re-seed costs two whole-tree detector sweeps on every run of the guard, forever
(the commit prices this at ~48 s a pair — fine until someone re-seeds often).

---

## What I verified, and how (the r8-fix claims, settled from ground)

- **P1-1 (`cb250d9d`) — THE merge-blocking finding.** Read end-to-end. `SETTLED_FACTS_UPSERT_SQL` is now
  `INSERT … SELECT CASE WHEN chats.deleted THEN <deleted-user>/NULL … FROM chats WHERE tenant+chat FOR
  SHARE OF chats ON CONFLICT … WHERE turn_outcome IS NULL`; the delete's first statement is the named
  `_SOFT_DELETE_CHAT_SQL` whose row lock conflicts with it. Verified by hand: EPQ re-evaluation lands the
  anonymised shape when the settle waits out an uncommitted delete; READ COMMITTED statement snapshots
  make the delete's later `ANONYMISE_CHAT_FACTS_SQL` see a settle row that committed while its
  soft-delete waited; shape parity with the anonymise SQL holds (settle columns carry no
  `cited_documents`, so `user_id`/`session_id` is the whole personal payload); no deadlock (both writers
  take `chats` first). **Premise verified, not assumed:** the pipeline's only production consumers are
  `chat_management.py:1163` / `:1508`, both `create_chat` before executing, and the delete is soft — so
  "a turn with no chat row lands nothing" costs no production turn. `settled_facts_params`' new dict
  signature has exactly one call site, updated. **Measured:** the four db tests including BOTH
  two-session lock proofs PASSED here (independently re-run; `pg_stat_activity` wait observed by the
  test), the pre-C12 single-WARNING path is pinned, and mutants P11a (drop `FOR SHARE`), P11b
  (`FOR KEY SHARE`) and my own N1 (the `session_id` CASE dropped — settle keeps a deleted chat's
  session) all KILLED.
- **P2-1 (`1d64829c` + gap `9a290d61`).** The digest rule is gone; `unbound_reseeds` runs BOTH guard
  versions over today's tree and demands each admitted `(key, code)` excess be found by the new detector
  and not the old; working-tree re-seeds are judged against the guard at HEAD (P21b re-KILLED — the gap
  commit's separating case works); a dead constant explains nothing; a detector that cannot run fails
  closed; `REVIEWED_RESEEDS` is pinned to exactly the one pre-rule re-seed.
- **P2-2 (`e17c779b`).** `IMPORTED_BUILDERS` names `sad_runner.tool_text_result` with its text slot;
  aliases and relative imports resolve; the home module counts; a local `def` shadows;
  `SAD_BUILDER_USERS` pins the five live resolving modules. **r8's SV3 survivor re-run here: KILLED.**
  My own N2 (the map keyed to a wrong module path) also KILLED by the file's own pins.
- **P2-3 (`fc0534d6`).** `_Scan` follows the factory by provenance (SDK import under any alias,
  `.tool`, `getattr`, bound names), treats `SdkMcpTool(...)` as a registration seated by its handler,
  and REPORTS any unrecognised use (partial/stored/returned) — fail closed; the `>= 14` floor became an
  exact per-module census witness. **r8's SV1b survivor re-run here: KILLED.**
- **P2-4 (`8b23b366`).** All ten branches gate per `(job, instance)` with the newly-started limb
  (`target_info unless last_over_time(target_info[1d] offset W)`); truth-table verified by hand;
  the >1-day-stall price is declared in the rules header; P24a re-KILLED. promtool owed (P3-4 above).
- **P2-5 (`56daa56f`).** Gate read, endpoint's `if success` path verified against `postgres.execute`'s
  rowcount return (pinned utils archive read); refusal measured (pg_temp), P25a/P25b re-KILLED; the
  out-of-scope memory/improvement copies are a properly recorded OPEN owner question in the workspace
  plan's M-FACTS-ANONYMISE row (with the `p25_measure.py` evidence pointer) — verified present.
- **P3-1..P3-8** diffs all read; each production change inspected (`turn_error_type` allowlist +
  self-maintaining census; the admin flag riding every returned handle with `_target` declared; the
  settle's own-txn raw-cursor write with `apply_session_tenancy`; `declared_nullable_columns_exist`
  which found `automation_runs.traceparent` live in my lane run). P3-9/P3-10 are OUT by owner ruling —
  not demanded.
- **Finisher `16760afc`.** Docstring family only; swept the tree — zero stale `detector_digest` /
  "detector unchanged" references remain.
- **Docstring-family sweep** for P1-1's "impossible by construction": gone; every remaining mention of
  the settle SQL states the new contract.

## Lane totals vs the fix batch's claims

| lane | claimed (real tree, Add. 226) | this review (scratch clone) | reconciliation |
|---|---|---|---|
| `tests/unit` `-n 2` (netns) | 6851 passed / 10 skipped / 0 failed | **6831 passed / 6 failed / 24 skipped** (5:14) | totals 6861 = 6861 EXACT. 6 red = the 5 known workspace-shape infra tests (`test_cross_repo_reads_name_their_checkout` ×4, `test_root_anchoring` ×1) + P3-9's workout DB test (netns; its refused `pg-connect` in the netguard log); 14 extra skips = llm-platform sibling ×11, cross-repo ordering ×1, root_anchoring dashboard ×1, phase1c utils ×1 — every delta a scratch-shape artefact |
| `tests/agent_sdk` `-n 2` (netns) | — (not re-claimed by the batch) | **4167 passed / 40 skipped / 0 failed** (1:37) | r8 baseline 4165/40; +2, green; network = the known 5 pg-connect files only |
| `tests/integration/otel` serial | 240 passed (27 skips) | **240 passed / 27 skipped** (15 s) | EXACT; zero netguard events |
| db lane (`tests/db/chat_history` + `tests/db/tenancy` + `tests/api/chat/test_feedback_on_a_deleted_chat.py`) serial | 500 passed / 3 failed / 20 skipped | **500 passed / 3 failed / 20 skipped** (1:16) | EXACT. The 3 reds are the mapped test-DB drift, and `test_the_live_database_conforms` names `automation_runs.traceparent` + `chat_turn_facts.turn_outcome`/`turn_error_type` (C12) + `llm_turn_content` — the new gate demonstrably working; no new red |
| observability+agent_shared+infra at HEAD | 1908 passed | covered by the full unit lane at `16760afc` (superset, green modulo the artefacts above) | consistent |

**Network, all lanes:** unit — 2 refused `127.0.0.1:8080` (the known Weaviate probe), 1 refused DNS
(`no-such-host.invalid`, deliberate), 80 refused pg-connects (P3-3 above); agent_sdk — 5 pg-connects
(the known unmarked live-Postgres files, skipped); otel — nothing at all; db lane — localhost:5432
only: `copilot_mro_test`, the two throwaway conformance DBs, `postgres`, and the one deliberate
`copilot_mro` read (`test_corpus_read_door`, pre-existing by design). **Zero AWS / IMDS / SSO / Bedrock
/ S3 / Redis / OTLP / Cognito attempts anywhere.**

## Mutation sample (re-execution duty — recomputed, not transcribed)

12 rounds run here via `/home/aditya/Code/mutant.sh` on the scratch clone (cold bytecode per round,
baseline-checked, restore verified; log `~/.claude/scratch/obs-merge/mro-r9/logs/mutants.txt`):

| round | target | aimed at | result |
|---|---|---|---|
| P11a drop `FOR SHARE` | settle SQL | unit settled pins | **KILLED** |
| P11b `FOR KEY SHARE` | settle SQL | unit settled pins | **KILLED** |
| **N1 (new)** `session_id` CASE dropped | settle SQL | db pg_temp `settling_after`/`live_chats_settle` | **KILLED** |
| P25a gate dead (`WHERE false`) | feedback SQL | db pg_temp `feedback_on_a` | **KILLED** |
| P25b `FOR SHARE` dropped | feedback SQL | unit feedback-after-delete | **KILLED** |
| P24a newly-started `[1d]`→`[1h]` | pipeline alerts | first-event gap simulator | **KILLED** |
| P21b old detector ≠ HEAD | `_register_ratchet.py` | ratchet history tests | **KILLED** |
| **N2 (new)** `IMPORTED_BUILDERS` wrong module path | tool-result guard | the guard file | **KILLED** |
| **SV1b (r8 survivor)** keyword-registered unseated tool in `provider.py` | SAD provider | seat guard | **KILLED** |
| **SV3 (r8 survivor)** `_tool_text_result({'error': str(exc)})` in `provider.py` | SAD provider | tool-result guard | **KILLED** |

(The first two rows' baselines double as the unit-pin witnesses; the batch's own 21 banked rounds in
`mro-impl-r9/mutants.txt` are consistent with these 10 — every sampled one reproduced.)

## Claims table

Severity: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or
process. Tier (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 =
irreversible or estate-shaping. Chunk: F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R9-01 | copilot-mro | `chat_turn_facts.py:648-694`; `chats.py:21-33`; `turn_facts.py:155` | Settle reads chat liveness under `FOR SHARE`; deleted chat → anonymised shape; no chat row → nothing | r8 P1-1 | Two-session proofs PASSED here; EPQ + parity + premise verified by reading; 3 mutants killed | roundtrip db tests + unit shape pins | yes — r9 (P11a, P11b, N1) | 0 | 0 | F1 | SETTLED (r8 P1-1 CLOSED) |
| R9-02 | copilot-mro | `tests/_register_ratchet.py:103-244` | Re-seed judged by both detectors' behaviour over today's tree; `detector_digest` deleted; `REVIEWED_RESEEDS` pinned exactly | r8 P2-1 | Redesign read; throwaway-repo tests; P21b re-killed | ratchet history tests + both guards | yes — r9 (P21b) | 1 | 0 | F1 | SETTLED (double-report launder = P3-2 residual) |
| R9-03 | copilot-mro | `test_tool_results_carry_no_exception_text.py:95-105,358-390` | `tool_text_result` sanctioned as a cross-module result builder | r8 P2-2 | SV3 re-run KILLED; N2 killed; 5 live resolvers pinned | the guard file | yes — r9 (SV3, N2) | 1 | 0 | F1 | SETTLED (r8 P2-2 CLOSED) |
| R9-04 | copilot-mro | `test_sdk_tool_handlers_are_seated.py:30-250` | Seat rule follows the factory by provenance, fails closed, exact census 14 | r8 P2-3 | SV1b re-run KILLED | that file | yes — r9 (SV1b) | 1 | 0 | F1 | SETTLED (r8 P2-3 CLOSED) |
| R9-05 | copilot-mro | both alert rule files, 10 branches | Per-(job,instance) gate + newly-started limb, 1d horizon declared | r8 P2-4 | Truth table by hand; P24a re-killed; promtool owed | `test_first_event_branch_gap.py` | yes — r9 (P24a) | 2 | 1 | F1 | SETTLED (promtool = P3-4) |
| R9-06 | copilot-mro | `feedback.py:23-58,101-131`; `user_feedback.py:251-262` | Feedback on a deleted block refused in-statement; refused save propagates nothing; owner question recorded for the other copies | r8 P2-5 | Read + pg_temp measure; endpoint path verified; plan row verified | db + unit + api tests | yes — r9 (P25a, P25b) | 2 | 1 | F1 | SETTLED within ruling (two-session proof = P3-1; copies = OPEN owner question) |
| R9-07 | copilot-mro | P3-1..P3-8 commits | Eight r8 P3s implemented as asked; P3-9/P3-10 OUT by owner ruling | r8 P3s | Diffs read; lanes green; `traceparent` found by the new gate in my run | each commit's tests | batch's own (sampled indirectly) | 2 | 1 | F1 | SETTLED |
| R9-08 | copilot-mro | `557a178f..16760afc` lanes | "unit 6851 · otel 240 · db 500/3/20 · obs 1908" | Add. 226 | All four independently reproduced/reconciled EXACTLY (table above) | — | — | 3 | 1 | F3 | SETTLED |
| R9-09 | copilot-mro | seam `735f8213..557a178f` | cli r2-fix commits + merge commit have no independent review | seam duty | Ledger + packet listing; commits listed | — | — | 3 | 1 | F2 | SURFACED (controller item) |
| R9-10 | copilot-mro | unit lane network | Pipeline unit tests attempt live pg-connects (~80) | instrument-revealed | netguard psycopg2 wrapper log | none | no | 2 | 1 | F3 | OPEN (P3-3) |

## Future improvements

1. **A two-session lock proof for the feedback gate** (P3-1): mirror the settle pair — a feedback
   racing an uncommitted `delete_chat` waits on the block's row and is refused; an in-flight feedback
   holds off the delete's `UPDATE chat_blocks`. ~40 lines by analogy to the existing pair.
2. **Bind the re-seed rule against double-reporting** (P3-2): assert each admitted site is found at
   most once per (key, code) by the new detector, or dedupe sites by (file, line) before counting.
   Deferred: the attack requires a reviewed guard edit, and the pinned `REVIEWED_RESEEDS` narrows the
   surface to future commits.
3. **Seam-default the pipeline's best-effort accounting in unit tests** (P3-3): a conftest-level
   default that replaces the ledgers/settle executor with in-memory fakes for `tests/unit`, keeping
   the netns lanes connection-silent and shaving the refused-connect latency.
4. **Run promtool/otelcol over the rewritten rules** (P3-4): already on the CI/owner item from the cli
   lane; the ten new expressions should ride it.

**Verdict: MERGE-CLEAN — 0 P0 · 0 P1 · 0 P2 · 4 P3.** The r8 fix batch is what Addendum 226 says it
is: P1-1's settle/delete race is closed by a lock that was measured across sessions here and whose
mutants die; the four P2 guard redesigns each kill the exact survivor that proved the r8 gap; the lane
numbers reproduce to the test; and the four P3s left are coverage niceties and declared residuals, none
of which touches the merge.
