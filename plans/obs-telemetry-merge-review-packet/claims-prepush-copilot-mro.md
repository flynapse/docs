# Claims packet: pre-push FULL-DIFF review — copilot-mro (queue step 16b, review 9 of 9)

Fable 5 reviewer, 2026-09-23. **Verdict: PUSH-CLEAN — 0 P0 · 0 P1 · 0 P2 · 3 P3 (record-only).**
The mandated judgement call (`memory_items.user_id` kept on retained knowledge) is **CONFIRMED**
as inside the owner's ruling — its own row below.

READ-ONLY on the real tree: nothing in `/home/aditya/Code/copilot-mro-obsm` was edited, checked
out, stashed or committed; at close it is tracked-clean at `9debf188` (verified). Every run used
either the `git archive` copy under `~/.claude/scratch/obs-merge/prepush-mro/tree/` or a
`git clone --shared` detached at `9debf188` under `.../prepush-mro/clone/` (the git-reading scope
guard needs a checkout; the clone was restored clean after the one mutation round). Durable
notes, diffs and logs: `~/.claude/scratch/obs-merge/prepush-mro/` (`prod-app.diff`,
`prod-scripts.diff`, `prod-deployment.diff`, `logs/`, `run.sh`).

## Anchor and range — measured state

| fact | measured |
|---|---|
| repo / branch / HEAD | `/home/aditya/Code/copilot-mro-obsm` · `obs-merge` · `9debf188bd427ad14f9c8bef819d749bd8c285f7` |
| pushed main (ls-remote, not tracking refs) | `refs/heads/main` = `380601ee421245ad41461772d9e8708b3c8eff58` — an ANCESTOR of HEAD (merge-base = itself); unmoved, matching CHECKPOINT 43 PUSH TRUTH |
| pushed langgraph-merge (ls-remote) | `417df303758dc12dd6c9d426a2fb9b38755a1d99` — the 2026-09-15 20:40 -0700 observability-rebuild **batch-2 push** (phases ≤P10, reviews R12–R21, batch-2 Fable gate R22); also an ancestor of HEAD |
| colleague source branch (ls-remote) | `refs/heads/obs-telemetry-merge` = `c2fc8bb1` — the colleague's own pushed input branch (the same pattern Add. 271 ratified for api's anchor) |
| full main..HEAD | `380601ee..9debf188` = 2,558 commits |
| **EXCLUDED as already gated** | `380601ee..417df303` = 2,231 commits: the LangGraph scale-out line (its own gate-passed project) and the observability-rebuild batch-2 (R12–R21 + R22 Fable gate, pushed 2026-09-15/16 as `417df303` = origin/langgraph-merge). Reason: every commit is reachable from the R22-gated PUSHED tip — same by-construction exclusion the api review used. |
| **REVIEWED RANGE** | `417df303..9debf188` = **327 commits**, 593 files, +65,670 / −4,642 |

Range composition (measured by authorship + topology, never assumed):
- **46 commits** `417df303..c2fc8bb1`, ALL authored `ishaan.jain` — the COLLEAGUE'S INPUT
  (2026-09-08 → 09-19). `git cherry 417df303 c2fc8bb1`: 30 of the 32 pre-merge patches have no
  equivalent on langgraph-merge — new work, not re-gated rebuild work. Merged 2026-09-20 by
  `e26be7dd` ("conflict resolution only", ^1 = `417df303`, ^2 = `c2fc8bb1`, author aditya.goel).
- **281 commits** `e26be7dd` + descendants, ALL authored `aditya.goel` — the merge project's own
  work (163 first-parent + 117 side-branch commits from the cli/g106/panels/r7b/tbA–tbD merges).

### Sub-ranges the brief names — all separately covered

| sub-range | commits | coverage here |
|---|---|---|
| (a) CLI-telemetry | `10ef633a 9d6be4b6 7880bc44 a532a23c 0849309a 42b9c1b2 b5cf1524` + merge `557a178f` | Diffs of all 7 r2-fix commits read (production hunks in full: `claude_cli_telemetry.py` status-code-only category + LOGS-timeout pin; `base.yaml` allowlist prose; the CHECK-convalidated migration + owner SQL). **The merge was re-derived mechanically**: `git merge-tree --write-tree --merge-base=6aef26e3 735f8213 b5cf1524` vs `557a178f^{tree}` differs ONLY by the three conflict markers — the resolution is the pure union it claims (135-entry scope-guard list, both sides kept, nothing smuggled). The 19 earlier branch commits carry cli-r1/r2 round coverage (MERGE-CLEAN 0/0/2P2/4P3; both P2s fixed by the commits above). |
| (b) feedback-gate fix `8b1bfaee..e76fa21c` (3 commits) | `0e32212c 506547a0 e76fa21c` | FIRST-REVIEW rigour, hunk-by-hunk (below + proofs) |
| (c) anon-copies extension `e76fa21c..9debf188` (3 commits) | `9a68ef23 34bab392 9debf188` | FIRST-REVIEW rigour, hunk-by-hunk (below + proofs), incl. the judgement-call row |

### Commit coverage reconciliation (prior claims files used as INDEXES, never as evidence)

Every commit in the range sits in at least one prior reviewed span EXCEPT (b) and (c): colleague
input + merge repair (phase C/D/E claims + rounds packet), the 09-20/21 G-item, census and
hygiene work (rounds, r6 `0d9ecf0b..2b6170b0`, r7 `2b6170b0..5ea91b80`, r8 `62c7413d..735f8213`),
the CLI branch (cli-r1/r2), the r8-fix batch `557a178f..16760afc` (r9 closing, MERGE-CLEAN
0/0/0/4), r7b + tbA–tbD (+ the five Add. 250 merges; r7b ×3, tb-AB-r1, tb-CD-r1 — tb-CD's gating
P1 re-verdicted MERGE-CLEAN), and the step-15 follow-ups `55519cf1..8b1bfaee` (12 commits closing
CD/r7b-r3/r9 findings — no independent closing review of their own, so their production diffs
were read here at elevated rigour: the judge-residency endpoint rework, the G.105 residue sites,
the authored-refusal carve-out (a) restorations, the chart_create describer seat, the marker-gate
and proxy-blank commits).

## Range shape (recomputed, never quoted)

- Production (`copilot_mro/`, `scripts/`, `deployment/`, `lambda_functions/`, `demo/`,
  Dockerfiles, pyproject/poetry.lock): 319 files, +19,292 / −3,346. Tests: 257 files, +44,663 /
  −1,220. Docs: 14 files, +1,693 / −70.
- **How the production diff was read.** The three diff files were generated once from the real
  repo and read from the scratch dir: `copilot_mro/` app diff read serially through the api layer,
  chat-history store (blocks/chats/feedback/deleted_chat_copies in full), table definitions
  (chat_turn_facts, llm_turn_content), main.py lifespan spans, agent_claude adapters +
  orchestrator (CLI-telemetry + capture wiring), agent_evaluation (contracts/adapter/runners in
  full — the residency check verified to implement r7b-r3 P2(a) ConfiguredEndpointProvider,
  P2(b) backslash/userinfo = no host, trailing-dot, https-only, inet_aton P3s), `_debug_hooks`
  redaction, `llm_content_capture` accumulator/budget/truncated-secret handling, and the
  M-TRACEBACK conversion sweep. The remainder (telemetry.py span internals, model_gateway,
  pipeline, tools/*, weaviate_tenancy, improvement/memory/data_discovery services — all subjects
  of the r6–r9/tb/CD mutation-proved rounds) was covered by whole-diff adversarial pattern
  sweeps over every ADDED line: exception-text leaks (`str(exc)`, `format_exc`,
  `logger.exception`, `{exc}` interpolations), span-attribute content leaks, added `print(`s,
  `os.environ` writes, secret-bearing assignments. Every hit was triaged in context; all
  resolved to (i) comments/docstrings about the OLD behaviour, (ii) M-TOOL-ERRORS
  detector-governed tool-result seats (ALLOWED or registered; the tool-result guard is green at
  HEAD), (iii) the deliberate read_docx regex carve-out that reads `re.error.msg`/`.pos` off the
  TYPED cause, or (iv) script prints carrying `type(exc).__name__` / `failure_fields` stacks
  only. **No new leak site.**
- **Test-deletion audit.** Every test file with >50 deleted lines maps to a reviewed, purposeful
  commit: `test_no_exception_text_in_logs.py` (−239/+2,456 — the guard REWRITE that grew it,
  16760afc/ee37c6e3 lineage), `tests/agent_sdk/conftest.py` (−197, hygiene 3a Bedrock doubles,
  62c7413d/614b95ee), `tests/integration/otel/conftest.py` (−114, G.70/75/47 + merge),
  `test_feedback_propagator.py` (−62, hygiene 5.5), `test_agent_sdk_tool_io_state.py` (−66,
  colleague-era checkpoint), `_toollog_index.py` (−58, D.2/D.7/D.10). No guard silently weakened.

## Sub-range (b) — the feedback gate, verified at `9debf188`

- `_SAVE_FEEDBACK_SQL` (`copilot_mro/app/db/chat_history/feedback.py:26-42`) carries the exact
  `0e32212c` shape: `WHERE COALESCE((SELECT deleted FROM chat_blocks WHERE tenant_id = %s AND
  block_id = %s FOR SHARE), false) = false` — a scalar locking sub-SELECT whose `deleted` is
  tested OUTSIDE it. The broken `NOT EXISTS (… AS block WHERE block.deleted)` form is gone, and
  the shape pin (`tests/unit/chat_history/test_chat_feedback_after_delete.py`) now asserts its
  ABSENCE (`assert "AS block WHERE block.deleted" not in sql`) as well as the new form.
- **Predicate-pushdown sweep (Add. 253's defect), whole production tree:** exactly four
  `FOR SHARE` sites exist — feedback.py:32, memory_db.py:231, signals.py:48 (all three the
  COALESCE-scalar/tested-outside shape) and `SETTLED_FACTS_UPSERT_SQL`
  (chat_turn_facts.py:674-682, top-level `FOR SHARE OF chats` with the raced column READ via
  CASE, never filtered). **The defect shape — an outer WHERE on the raced column beside a
  locking sub-select — exists nowhere.**
- **The two-session red/green pair exists and is real**: `tests/db/chat_history/
  test_chat_turn_facts_db_roundtrip.py::test_feedback_racing_an_uncommitted_delete_waits_for_it_
  then_is_refused` + `::test_an_in_flight_feedback_holds_off_the_deletes_block_statement` — two
  connections, real `chat_blocks` rows, waiting proved via `pg_stat_activity` /
  `pg_blocking_pids`, TEMP shadow only for `chat_feedback` itself; the header records why both
  were red at the first gate. **Re-executed green here (db run 1)**, together with the settle
  pair it mirrors (r9 P3-1). Red-at-`8b1bfaee` is Add. 255's verbatim record plus the
  gate-revert mutants it banked (index); not re-run — the db budget went to the first-review
  range (c) instead.
- `506547a0` (pair header names its source row) and `e76fa21c` (the three authored-refusal
  `ABORTED: <remedy>` pins) read in full; the three pins **re-executed green** in the unit run.

## Sub-range (c) — the anon-copies extension, first review

Files read hunk-by-hunk at `34bab392`/`9debf188`: `deleted_chat_copies.py` (new, 298 lines, every
SQL statement), `chats.py` (delete_chat integration), `signals.py` + `_shared.py`,
`memory_db.py`, `feedback_propagator.py`, `chat_turn_facts.py` prose, both new test files, the
spend-ledger test (`9a68ef23`), the scope-guard approvals (`9debf188`).

### Mandated confirmation 1 — THE LINE: **HOLDS**

`DELETED_CHAT_COPIES` places every copy exactly as ruled (Add. 271/273/274): compaction summaries
**delete** (`DELETE_COMPACTION_SQL`, + post-commit Weaviate doc reap); `chat_shares.user_id` +
`share_data{email,message,session_id}`, `agent_state.payload` (+ label, S3 pointer, version
bump), `memory_item_events.{metadata.comment,actor_user_id}`,
`improvement_signals.{user_id,detail.excerpt/reason}` and `improvement_findings.evidence.texts`
**scrub**; `_user_corrections`, `example_queries`, `evidence_excerpts`, finding `body`,
theme/title **keep**; `llm_turn_content` keep (append-only, 30-day purge — documented at the
delete seat as ruled); llm ledgers keep (numeric-only, PROVEN by `9a68ef23`'s test, re-executed).
The unit line test pins the owner's placements verbatim and that no statement touches a
keep-side copy (the only `memory_items` statement is the compaction DELETE) — re-executed 6/6.
The module adds `detail.reason` to the scrub (the implicit miner's paraphrase of the same turn)
— an extension TOWARD scrubbing, consistent with the line's direction.

SQL scrutiny beyond the tests: `SCRUB_FINDING_TEXTS_SQL`'s substring match is sound —
`clustering.signal_text` builds each stored entry as `excerpt.strip()[:500]` (NUL-stripped;
Postgres jsonb cannot hold NUL anyway), so a stored entry is ALWAYS a substring of its source
excerpt/comment; the `signal_ids ?| (ids UNION signatures)` selector covers the builder's
signature fallback; empty entries excluded; ordering (texts before signals) pinned by a unit
test. Idempotence: every statement keys on the not-yet-anonymised shape; the whole delete is one
transaction so no partial state survives a crash. The deliberate over-scrub (a live member's
identical substring also dropped) is Add. 274 residual 1 — errs toward scrubbing, accepted.

### Mandated confirmation 2 — THE JUDGEMENT CALL: **CONFIRMED** (own row, as required)

**Claim under review:** `memory_items.user_id` (the contributor's id) stays on retained
knowledge-base notes, while the owner ruled "real user NAME must be masked".
**Verdict: inside the ruling.** Four grounds, each checked against the tree or the rulings:
1. The name-masking ruling (Add. 257 ruling 6 / DR4-25) governs display surfaces, and its
   SANCTIONED mask is itself KEYED by `user_id` ("User NNN" keyed by `user_id`, Add. 269, held
   adversarially by the dashboard verdict) — the rulings corpus explicitly treats the opaque id
   as the acceptable pseudonym where names must not appear.
2. The knowledge-base ruling keeps the CONTRIBUTION after the contributor's chat goes;
   `memory_items.user_id` is declared "User scope identifier" (memory.py:97) — it is the
   user-scope KEY of user-scoped notes, not a display name. Blanking it would re-scope personal
   notes (a privacy regression, not an improvement) and break recall scoping.
3. The placement is deliberate, not an oversight: the SAME kind of id IS scrubbed where it marks
   the feedback trail (`improvement_signals.user_id`, `memory_item_events.actor_user_id`) and
   kept only where it attributes retained knowledge — both sides documented in the line module.
4. No surface renders it as a person: the field is `display: False`, and the 12-panel/8-table
   dashboard census (7th verdict) found only `spend_by_user` people-labelled — masked.
Caveat recorded as PP-MRO-1 (P3) below: chat deletion is not user erasure; the ruling reviewed
here covers the former only.

### Mandated confirmation 3 — the race gates: **HOLD** (read + measured)

- Both new gates are the `0e32212c` shape, read from the SQL: `_INSERT_SQL` (signals.py) and
  `_INSERT_FEEDBACK_EVENT_SQL` (memory_db.py) each read the block in a scalar
  `COALESCE((SELECT deleted … FOR SHARE), false)` aliased `gone` and test it OUTSIDE (CASE), so
  a LIVE block is locked; a blockless row is live; the insert always lands — anonymised when
  gone (user id → `DELETED_USER_ID`, text keys stripped) — matching "still evidence about the
  turn". The propagator passes `feedback_block_id` so only the feedback event takes the gated
  path. No pushdown-defect shape anywhere (sweep above).
- `insert_signals` commits **one transaction per row**, re-applying the tenancy binding each
  time (`bound_cursor` inside the loop; `_shared.py` names the exception), and the docstring
  states the WHY verified against the design: each insert takes a share lock on its block, and a
  batch holding several of one chat's blocks while `delete_chat` holds others of the same chat
  would DEADLOCK; per-row commits + signature dedup make an interrupted batch re-collectable.
- **Measured, both directions (db runs):** run 1 — all four race tests green at HEAD (signal +
  event, delete-first and in-flight). Run 2 — a REVIEWER-BUILT mutant (the signal insert
  de-gated in the clone: plain SELECT, no FOR SHARE, no CASE) **killed rc=1 with 2 failed, each
  on its aimed line** ("did not wait on the delete's lock" / "delete was not held off"), cold
  bytecode (`PYTHONPYCACHEPREFIX` fresh, `PYTHONDONTWRITEBYTECODE=1`), file restored and clone
  verified clean. The gates are load-bearing and the tests genuinely detect their loss.

### Mandated confirmation 4 — the full-operator-roster binding: **HOLDS**

`delete_chat` reads `OPERATOR_ROSTER_SQL` on the SAME cursor, inside the SAME transaction,
after `apply_session_tenancy`, then re-applies the session tenancy under
`db_tenancy(tenant_id, roster or ambient)` before any scrub statement — so the tenant+operator
relations (`memory_items`, `memory_item_events`) are reached across ALL operators (`operators`
is tenant-classed, so the requester's own binding reads the whole roster; the comment records
why: an event carries the operator of the note it audits, not the giver's). The docstring family
was swept with it ("first statement" → "first write", correct since the roster read precedes the
soft-delete and locks nothing). **Measured:** the db file's roster case (feedback on operator
B's note reached under a binding minted for operator A) is inside run 1's 28 green.

### Mandated confirmation 5 — scope-guard approvals at `9debf188`: **EXACT**

The commit adds exactly FOUR entries to `MRO_POST_MERGE_PRODUCTION_PATHS`
(`deleted_chat_copies.py`, `improvement/_shared.py`, `improvement/signals.py`,
`feedback_propagator.py`), each with the ruling reason; all four are genuinely touched by
`34bab392`; the other three touched production files (`chats.py`, `memory_db.py`,
`chat_turn_facts.py`) were ALREADY in the approved set from earlier phases — no over-approval,
no missing approval. **Proven by execution, not only reading:** the three git-diff guard tests
pass in the pinned clone (they cannot run from a tar archive — see PP-MRO-3).

## Proofs — re-executed vs index-verified

Re-executed by this reviewer (all through `pytest-slot.sh`, `DEBUG=false`, rootdir/`-c` pinned to
the scratch tree or clone, provenance lines read on every run — `copilot_mro.app.__file__` = the
scratch copy; siblings live obsm trees core `6899974` / utils `23e849c` / api `4bc2d4f` / otel
`c93a9c9`, unchanged across the review):

| proof | result | log |
|---|---|---|
| unit: line test ×6 · feedback shape pin ×2 · ledgers ×2 · authored-refusal remedy pins ×3 + scope-guard non-git tests | **19 passed** (3 archive artefacts, disproved below; 1 env-gated skip) | `logs/unit-run.log` |
| scope guard in the PINNED CLONE (artefact disproof) | **9 passed / 1 skipped** — the three git-diff tests PASS at `9debf188`; the archive failures were `RootAnchorError`-class layout artefacts, not violations | `logs/scope-guard-clone.log` |
| **db run 1 (serial):** `tests/db/chat_history/test_deleted_chat_copies_db.py` + `test_chat_turn_facts_db_roundtrip.py` | **28 passed** — the line, the cross-operator roster case, all four anon race directions, BOTH two-session pairs (settle + feedback), r8 P1-1's settle proofs | `logs/db-run1.log` |
| **db run 2 (serial):** reviewer-built de-gate mutant on `signals.py` in the clone | **KILLED rc=1, 2 failed on their aimed lines**; restore verified (`git status` clean) | `logs/db-run2-mutant.log` |
| mechanical re-merge of `557a178f` | tree-diff vs `git merge-tree` output = conflict markers only (pure union) | recomputed in-session |
| range arithmetic, authorship split, `git cherry`, ls-remote anchors | all recomputed | this file |

DB budget: **2 of 2 spent** (both serial, sole user, `copilot_mro_test`). Disclosure: one
~1-second aborted attempt before run 1 (collection `RootAnchorError` — the roundtrip file
anchors a `core/` sibling at the workspace root; fixed with sibling symlinks). It ran zero
tests and wrote nothing; counted inside run 1's lane, not as a third run.

Index-verified (NOT re-executed; sources named): the closing full unit lanes at `34bab392`
(3,226 passed / scope-guard flag → approved → 800 green) and guard set 239 + cross-repo 10
(Add. 274 + anon-lane NOTES/logs); the red-before at the `9a68ef23` archive (5 failed exactly as
predicted — `logs/db-run1-red-before.log` of the anon lane); Add. 255's gate-revert mutants and
r9's mutation battery; conformance 90/0/0; the seven prior copilot-mro round verdicts and their
banked mutants; the dashboard census backing confirmation 2(4).

## Findings

**No P0. No P1. No P2.**

- **PP-MRO-1 (P3, record-only → owner sheet).** The judgement call confirmed above is scoped to
  CHAT deletion. A future USER-erasure flow (offboarding/right-to-be-forgotten) would find
  contributor ids — and kept `_user_corrections` / `example_queries` text — on the tenant's
  knowledge base with no ruling covering that path. Nothing to fix pre-push; needs its own
  ruling if/when such a flow is built.
- **PP-MRO-2 (P3, record-only).** Two write windows outside the two RULED race gates remain
  ungated, exactly as Add. 274 residual 2 discloses: the distiller can file a finding from
  signals read before a delete, and a turn still running after the delete can re-land a
  compaction digest / agent_state / share. Verified real by reading the paths (no block gate at
  the distiller's insert; compaction runs off-path post-turn). Deliberate deferral — C15 (owner,
  post-push) and any re-run of the delete clean them; belongs in the plan's Future Improvements
  wording if not already there.
- **PP-MRO-3 (P3, informational — runner traps for later agents).** (i) The db roundtrip file
  anchors sibling repo `core` at the WORKSPACE root via `tests/_root.sibling_choice`, so a bare
  archive/clone with no sibling dirs fails at COLLECTION (`RootAnchorError`) — place
  `core`/`utils`/`api`/`flynapse-otel` symlinks beside the checkout. (ii) The phase-1c scope
  guard's three diff tests need a GIT CHECKOUT (a `git archive` copy fails them spuriously);
  use a shared clone. Same family as the banked otel `core/`-sibling trap (Add. 266).

**PUSH-CLEAN.** Nothing in `417df303..9debf188` blocks the Phase H push of copilot-mro. The
three P3s pool to the estate micro-batch / owner sheet as routed above.
