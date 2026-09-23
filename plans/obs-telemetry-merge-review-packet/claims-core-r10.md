# Claims packet: core review r10 — NARROW closing review (`16cd1ae..19403fa`, 15 commits)

Independent adversarial closing review (Fable), 2026-09-22, of the four r9 P2 fixes ONLY —
owner-ruled narrow scope. **Verdict: MERGE-CLEAN — 0 P0 / 0 P1 / 0 P2 / 1 new P3.**
All four items CLOSED. Merge-blocking = P0/P1 only; nothing blocks.

Scope: P2-1 `ce222eb`, P2-2 `5d0b324`, P2-3 `398b19a`, P2-4 `600730e`, each verified from the
ACTUAL DIFF and the files at HEAD `19403fa`. The other 11 commits of the range were skimmed for
interference only: three touch `tests/fixtures/scratch_tenants.py` (`5dff45e` dedupe, `28840bf`
docstring, `2622d6f` reload/second-copy refusal) and one rewrites the same SQL builder as P2-3
(`62c2d59` regrouping) — the liveness `CASE` survives it at HEAD (verified in the HEAD SQL, and
killed-when-removed below). Nothing in the range undermines the four.

## Attestation and recipe

- Real tree `/home/aditya/Code/core-obsm`: HEAD `19403fae5e1f1ba7a0b4e87ef6cab439d56ac52d`,
  `git status --porcelain` EMPTY at review start AND at review end. **Nothing real was edited,
  committed, or run in the real tree.** No push, no amend, no subagents, no network beyond
  localhost:5432.
- **C15 was NEVER executed as a script against any database.** Its statements were exercised only
  by (a) the committed db test (`tests/db/analytics/test_anonymise_deleted_chats_script_db.py`:
  app role, one scratch tenant, transaction ALWAYS rolled back, BEGIN/COMMIT never executed) and
  (b) this review's pg_temp shadow probes — `public.` rewritten to `pg_temp.`, CREATE TEMP TABLE
  in the session's temp schema only, zero reads or writes of real relations, rolled back. ("No
  DDL" is honored as no DDL on real schemas; pg_temp shadow tables are the brief's sanctioned
  vehicle for C15 execution evidence.)
- Every run used a `git archive` copy: `~/.claude/scratch/obs-merge/core-r10/ws/core-obsm`
  (durable scratch). Per the r9 recipe, every workspace checkout is symlinked beside the copy,
  with siblings PINNED by archive: `utils-obsm` `2f33a1c` and `flynapse-otel` `ff20ca9` (both
  live trees clean at those SHAs) linked from `sib/` in place of the live trees.
- Lane recipe (the r9 packet's): from the copy root, through `pytest-slot.sh`;
  `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test
  POSTGRES_USER=flynapse_app`, `PYTHONPATH=<copy>:<sib>/utils-obsm:<sib>/flynapse-otel`, shared
  api venv python, `-p impl9hdr -p no:randomly -o addopts="-ra --strict-markers"`. unit+authz
  `-n 2`; api serial; db serial.
- Indexes used, then verified against ground: `claims-core-r9.md`, SDD ledger Addenda 216/231,
  implementer scratch `~/.claude/scratch/obs-merge/core-impl-r9/` (PAUSED.md,
  mutation-results.txt, logs). Every number below is recomputed from this review's own probe
  files under `~/.claude/scratch/obs-merge/core-r10/` (logs/, mutation-results.txt, probes/).

## Provenance (impl9hdr header, present in every lane log)

    rootdir=/home/aditya/.claude/scratch/obs-merge/core-r10/ws/core-obsm
    core.__file__=/home/aditya/.claude/scratch/obs-merge/core-r10/ws/core-obsm/core/__init__.py
    utils.__file__=/home/aditya/.claude/scratch/obs-merge/core-r10/sib/utils-obsm/utils/__init__.py
    flynapse_otel.__file__=/home/aditya/.claude/scratch/obs-merge/core-r10/sib/flynapse-otel/flynapse_otel/__init__.py

The shared venv's `.pth` hazard did not bite: PYTHONPATH won in every run, per the header.

## Lanes at HEAD `19403fa` (this review's own runs, on the copy)

| lane | result | note |
|---|---|---|
| unit+authz `-n 2` | **2619 passed, 2 failed** | the 2 = the r9 packet's known COPY-symlink artefacts `test_sibling_variant_*` (`sibling_variant` realpaths through the workspace symlinks; green on the real tree — implementer log at `b540596`: 2621 passed rc=0, and the range head adds only markdown). No leak line. |
| api serial | **1221 passed, rc=0** | no leak line, zero skips |
| db serial (budget run 1: quality + C15 + harness, turn_outcome pair deselected) | **27 passed, 2 deselected, rc=0** | = the implementer's db-lane green; doubles as the mutation baseline (same exact command) |
| aimed sentinel guards (xdist pytester + combined-session + rules) | 23 passed, rc=0 | |
| aimed P2-3 unit (read_only_live_chat_blocks + registry + drift pin) | 333 passed, rc=0 | |

A first unit+authz/api pass BEFORE the workspace symlinks were laid showed 11F/2E resp. 1F —
all sibling-layout artefacts (drift pins reading copilot-mro's contract copy, cross-repo checkout
tests, one automation run-now red); all vanish with the r9 layout step. Superseded, kept in
`logs/*-19403fa.log` beside the `-r2` logs.

## DB budget accounting

At most 2 DB-touching runs were allowed; exactly 2 were used: (1) the db-lane baseline above;
(2) the `mutant.sh -B` liveness-CASE mutant run (same exact command). The three C15-seat proofs
ran through `mutant.sh` with pg_temp shadow probes — sessions that create ONLY temp tables and
roll back, touching no real relation — outside the budgeted class by the brief's own preference
("mutant probes prefer pg_temp shadow selections").

**One protocol slip, stated here (r9 precedent).** The budgeted mutant run's command piped pytest
through `tee`, so `mutant.sh` read tee's exit 0 and printed `SURVIVED`. The run's own captured
output (`logs/db-run2-mut-p23.log`) shows the aimed kill — `FAILED …
test_a_title_cited_only_from_a_chat_deleted_before_anonymisation_labels_no_row`, `1 failed, 26
passed, 2 deselected`, no collection error — i.e. pytest exit 1. True verdict KILLED; the file's
restore was verified by md5 against the `19403fa` blob; the run was NOT repeated because the
budget was spent. The correction is recorded inline in `mutation-results.txt`. Two later
`mutant.sh` lines are probe-plumbing artefacts, likewise annotated inline (a probe that imported
a sibling probe SCRIPT whose body ran on import; a missing `import os`): the real gate result is
the `-r3` line.

---

## Per-item assessment — each of the four: CLOSED / PARTIAL / NOT CLOSED

### P2-1 (`ce222eb`) — **CLOSED.** The real registration is behaviourally pinned

**The fix, verified in the diff and at HEAD.** The pytester behaviour file
(`tests/unit/harness/test_scratch_tenant_sentinel_reports_under_xdist.py:35-61`) no longer
carries a COPY of the registration: its run conftest loads the REAL `tests/conftest.py` by file
and registers it as a plugin (`pytest_configure` is historic, so the real registration line at
`tests/conftest.py:183-188` executes in every scenario run). The AST shape test r9 indicted is
REMOVED (`test_scratch_tenant_rules.py`), superseded by behaviour.

**Probes.**
- Aimed re-run of the pytester pin file: green (in the 23-passed aimed run and both unit lanes).
- **My own NEW mutant** (`r10-P2-1-registration-env-gated-shape-preserved`): the registration in
  the real conftest gated on an env var that is never set, with a `register(` call and the
  constant `"tests.fixtures.scratch_tenants"` KEPT in the file — the exact refactor class r9's
  failure scenario names, which the old shape guard passed. **KILLED** in 19s by the behavioural
  pin (leak no longer named, run exits 0, the pin demands TESTS_FAILED).
- The r9 REG-mutant class (register `tests.fixtures` instead) was re-killed by the implementer at
  `ce222eb` (`r9-REG-sentinel-never-registered KILLED`, their mutation-results); my env-gated
  variant covers the disable-in-place class from a second angle.
- Second-copy routes are refused at import (`scratch_tenants.py:63-86`, `2622d6f`): any other
  name, and a spec-loaded copy under the canonical name, raise ImportError — so a "registered a
  copy" mutant cannot exist silently.

### P2-2 (`5d0b324`) — **CLOSED** for the r9 hazard; one NEW P3 limit (below)

**The fix, verified in the diff and at HEAD.** `mint_and_register`
(`tests/fixtures/scratch_tenants.py:249-260`) registers only while `over_the_real_pool()`: both
grant-pool seats (`tenant_service.get_grant_service`, `utils.postgres_service.get_grant_service`)
are identical (`is`) to what they were when adoption began. The r9-measured hazard — a bare
`pytest` combined session registering the unit lane's stubbed `t-1` seven times, the sentinel
then deleting a shared-DB row the run never created — is closed for every in-tree spelling:
`tests/unit/db/test_tenant_service.py` stubs at exactly the watched seat
(`monkeypatch.setattr(_MODULE + ".get_grant_service", …)`).

**Probes.**
- **The review's own combined-session probe, now a committed test**
  (`test_production_mints_in_a_combined_session.py`: subprocess run over the real api adoption
  file + the real unit tenant-service file; registry recorded then EMPTIED before the sentinel):
  re-ran green (aimed run + both unit lanes).
- The in-process pair (`test_a_mint_over_a_substituted_grant_pool_is_not_registered[…]`, either
  seat substituted, then restored): green.
- **My own NEW mutant** (`r10-P2-2-seat-check-weakened-all-to-any`): `all(…)` → `any(…)` — a
  single-seat substitution would register again. **KILLED** in 5s.
- **My own NEW plant — a stubbed mint that tries to register — DEFEATS the seat check** (see
  finding r10-P3-1 below): a pool stub placed BELOW both watched seats (the memo global
  `utils.postgres_service._grant_service`) keeps both getters' identity, the REAL `mint_tenant`
  writes nothing real, and the shim REGISTERS `t-1`
  (`probes/test_r10_plant_below_seat.py`, `logs/p22-plant-below-seat.log`:
  `{'t-1': 'mint_tenant'}`). No in-tree test stubs there (grepped: no test touches
  `_grant_service` or instance/method-level grant stubbing with a real mint), and the docstring
  scopes its claim to the two seats — but the limit is NOT declared. P3, not merge-blocking.

### P2-3 (`398b19a`) — **CLOSED.** A dead-block title cannot reach the label at `19403fa`

**The fix, verified in the diff AND re-verified at HEAD after `62c2d59` rewrote the same
builder.** `_cited_documents_sql` (`quality.py:482-500` at HEAD) reads the title through
`CASE WHEN cb.block_id IS NOT NULL THEN cited ->> 'document' END` over a
`LEFT JOIN chat_blocks cb ON cb.tenant_id = f.tenant_id AND cb.block_id = f.block_id AND
cb.deleted = false` — liveness only, no `block_data` read; `max(title)` can then only see
live-citation titles, whatever a deleted chat's row still carries. The `62c2d59` regrouping
(`GROUP BY doc_uid, CASE WHEN doc_uid IS NULL THEN kind END, CASE … THEN title END`) keeps the
CASE intact; a dead uid-less citation groups by its kind with NULL id and NULL label, exactly as
the panel comment declares. The panel comment, the module docstring (`quality.py:5-19`) and the
C15 header's "what the dashboard shows meanwhile" all now state the read-side defence and the one
window it cannot cover (a HALF-deleted chat's blocks are live until C15 runs — r9 P3-9's shape,
fixed in C15's blocks half, owner-gated to run; consistent, no overclaim).

**Probes.**
- db guard test `test_a_title_cited_only_from_a_chat_deleted_before_anonymisation_labels_no_row`
  (plants a pre-anonymisation deleted chat citing a private upload, a uid-less private title and
  a private RENAME of a live document): green in the baseline run.
- **Mutation proof re-run via `mutant.sh`** (budgeted run 2): the CASE replaced by
  `cited ->> 'document' AS title` (the r9 defect restored) — the guard test FAILS, 26 others
  pass. **KILLED** (verdict-line artefact corrected above; the kill is in
  `logs/db-run2-mut-p23.log`). `quality.py` restore verified by md5 against the `19403fa` blob.
- Aimed unit re-run green (333 passed), including
  `test_every_panel_reading_chat_blocks_filters_deleted_blocks`, which now covers this join too.

### P2-4 (`600730e`) — **CLOSED.** C15 idempotent on NULL payload; the gate stops the COMMIT; reach widened; header honest

**The script, read end-to-end at HEAD (236 lines), never run.** Verified by reading:
- **NULL-payload idempotency:** the feedback predicate is now
  `cf.user_id IS DISTINCT FROM 'deleted-user' OR (cf.feedback_data IS NOT NULL AND (… ? 'comment'
  OR … ? 'session_id' OR … ->> 'user_id' IS DISTINCT FROM 'deleted-user'))`. An un-anonymised
  NULL-payload row is rewritten ONCE (user_id; `NULL - 'comment' … || …` stays NULL, as the
  delete leaves it); on a second run both disjuncts are false. An already-anonymised NULL-payload
  row is never touched.
- **The gate:** a `DO` block, last before COMMIT, `RAISE EXCEPTION` on any non-zero of the three
  read-back counts — aborting the transaction, so the trailing `COMMIT` is a ROLLBACK with or
  without `-v ON_ERROR_STOP=1` (both modes stated in the header). A non-object payload stops the
  run rather than being guessed at (array: caught by the gate's `->> 'user_id'` disjunct, pinned
  by `test_a_row_the_rewrite_cannot_anonymise_stops_the_run_before_commit`; scalar: the `-`
  operator errors at the UPDATE — either way nothing commits).
- **Reach:** facts rows found by `coalesce(f.chat_id, (SELECT cb.chat_id …))` (NULL-`chat_id`
  rows via their block); the blocks half soft-deletes live blocks of deleted chats with the
  chat's own `deleted_at`; the one declared unreachable shape (NULL `chat_id` AND no block row)
  is stated under WHAT IT CANNOT REACH.
- **Header corrected:** it no longer claims the dashboard is already clean — it names `398b19a`'s
  read-side defence AND the half-deleted-chat window that stays visible until the script runs.
- Safety unchanged from r9's checks: BYPASSRLS refusal, `search_path = pg_catalog, pg_temp` with
  every relation written `public.<name>`, row locks only.

**Probes — all four db seats of the implementer's closing four-mutant run (Addendum 231)
independently re-proven by this review:**

| seat | vehicle | baseline | mutant | verdict |
|---|---|---|---|---|
| P2-3 liveness CASE (`quality.py`) | `mutant.sh -B`, the real db lane (budgeted run 2) | 27 passed rc=0 (run 1, same exact command) | the title guard test FAILS, 26 pass | **KILLED** |
| P2-4 feedback `cf.feedback_data IS NOT NULL` | `mutant.sh` + pg_temp probe (`probe_c15_feedback_null_pg_temp.py`) | `first_run_rewrites=1 second_run_rewrites=0`, payload stays NULL | `first=2 second=2` — the NULL payload rewritten every run (the r9 defect resurrected) | **KILLED** |
| P2-4 gate RAISE threshold | `mutant.sh` + pg_temp probe (`probe_c15_gate_pg_temp.py`) | "GATE RAISED … 1 live block(s) … NOTHING is committed" | "GATE DID NOT STOP THE RUN" | **KILLED** (`-r3` line) |
| P3-9 `coalesce(f.chat_id, …)` | `mutant.sh` + pg_temp probe (`probe_c15_coalesce_pg_temp.py`) | `facts_rows_anonymised=1`, the NULL-`chat_id` row anonymised through its block | UNREACHED — the row keeps its asker | **KILLED** |

The pg_temp probes execute the script FILE's own statements (parsed with the db test's parser,
`public.` → `pg_temp.`), so the SQL text under proof is the committed text. C15 file restore
after each mutant verified by md5 against the `19403fa` blob.

---

## Findings

### r10-P3-1 (tier 1, NEW): a mint over a pool stubbed BELOW the watched seats still registers — an undeclared limit of the P2-2 fix

**Where:** `tests/fixtures/scratch_tenants.py:236-260` (`over_the_real_pool` watches the two
getter FUNCTIONS by identity); `utils-obsm utils/postgres_service.py:568` (the memo global
`_grant_service` the real getter consults).

**Measured** (`probes/test_r10_plant_below_seat.py`, `logs/p22-plant-below-seat.log`): with
`postgres_service._grant_service` set to a fake service (fake shapes copied from
`tests/unit/db/test_tenant_service.py`), both watched getters keep their identity, the REAL
`mint_tenant` runs against the fake — writing nothing real — and the shim registers
`{'t-1': 'mint_tenant'}`.

**Failure scenario.** A future unit test that stubs the pool at the memo global (or at
instance/class-method level) while calling the real `mint_tenant` with a colliding id re-opens
exactly the r9 P2-2 hazard in a combined session. Today this is THEORETICAL: no in-tree test
stubs below the seats (grep: `_grant_service` appears in no test; the only real-mint-over-stub
file uses the watched seat), and harm additionally requires an id collision with a foreign row.

**Fix (one line of text or one seat):** declare the limit in the shim's docstring beside the two
watched seats, or also capture `postgres_service._grant_service` at adoption start and require it
unchanged. Not merge-blocking.

### Protocol notes (this review's own, not the tree's)
1. The budgeted-mutant verdict-line artefact and its correction (see DB budget accounting).
2. Two pg_temp probe plumbing retries, annotated inline in `mutation-results.txt`.
3. The pre-layout first lane pass, superseded by the `-r2` runs.

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state | Answers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r10-01 | core | `tests/conftest.py:183-188`; `test_scratch_tenant_sentinel_reports_under_xdist.py:35-61` | the behaviour runs load and register the REAL root conftest; the shape test removed | r9 P2-1 | aimed green; NEW env-gated shape-preserving mutant KILLED (19s); impl's REG mutant re-killed at `ce222eb` | the pytester leak scenarios | yes (mine + impl's) | — | 0 | F2 | **CLOSED** | r9-02 |
| r10-02 | core | `tests/fixtures/scratch_tenants.py:236-260`; `test_production_mints_in_a_combined_session.py`; `test_scratch_tenant_rules.py:195-223` | a mint registers only while BOTH grant-pool seats hold their adoption-time identity | r9 P2-2 | combined-session probe green; either-seat pair green; NEW all→any mutant KILLED (5s) | both probe tests | yes | — | 0 | F2 | **CLOSED** for every in-tree spelling | r9-06 |
| r10-03 | core | `tests/fixtures/scratch_tenants.py` + `utils postgres_service.py:568` | seats watched by getter identity only; below-seat stubs unwatched, undeclared | — | NEW plant: below-seat stub REGISTERS `t-1` (`logs/p22-plant-below-seat.log`); no in-tree occurrence | none | plant | 3 | 1 | F2 | **OPEN, r10-P3-1** | new |
| r10-04 | core | `core/resources/analytics/panels/quality.py:482-500` | title only via the liveness CASE over a live-block LEFT JOIN; survives `62c2d59`'s regrouping | r9 P2-3 | db guard green (run 1); CASE-removed mutant KILLED (run 2, log-proved); 333 aimed unit green; texts corrected | `test_a_title_cited_only_…_labels_no_row` + the panel liveness rule | yes (re-run) | — | 0 | F1 | **CLOSED** (residual = half-deleted chats until C15 runs — declared in the header and comment, = r9 P3-9's design) | r9-10 |
| r10-05 | core | `scripts/rbac/anonymise_already_deleted_chats.sql` (236 lines, read whole) | NULL payload judged only when present; gate `DO` RAISE before COMMIT; coalesce block-reach; live blocks of deleted chats soft-deleted; header honest | r9 P2-4 + P3-9 | db test green ×3 cases (run 1); ALL FOUR seats independently re-killed (1 real-lane + 3 pg_temp, table above) | `test_anonymise_deleted_chats_script_db.py` | yes (all four seats re-run) | — | 0 | F1 | **CLOSED**; C15 itself stays NEVER-RUN, owner-gated | r9-17, r9-18 |
| r10-06 | core | lanes at `19403fa` | the range holds the lanes green | plan §2.4 | unit+authz 2619+2 copy artefacts; api 1221 rc=0; db 27 rc=0; no leak lines | the lanes | n/a | — | 1 | F2 | SETTLED (copy artefacts named) | r9-25 |

## Open claims

**Tier 1:** r10-03 (r10-P3-1) — declare or close the below-seat registration limit. One line.

**Owner-owed, untouched by this review (carried, not re-litigated):** r9-28 (`llm_usage` spend +
widened M-FACTS-ANONYMISE scope), r9-15 (panel-cache closure), the C15 RUN itself (blocked on the
chat-delete anonymisation scope ruling). The controller's packet debt (flipping the 15 answered
r9 rows) stands per Addendum 231.

## Verdict

**MERGE-CLEAN — 0 P0 / 0 P1 / 0 P2 / 1 P3 (r10-P3-1), scoped to the four items.**
P2-1 CLOSED · P2-2 CLOSED · P2-3 CLOSED · P2-4 CLOSED.

## Future improvements
- Close or declare r10-P3-1 (below-seat mint registration) — cheapest as one docstring line;
  the elegant close also captures the memo global at adoption start.
- The two `test_sibling_variant_*` copy artefacts could accept a symlinked workspace (realpath
  the expectation) so review copies run the lane clean; deliberately not changed here.
