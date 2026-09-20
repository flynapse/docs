# Claims packet — Phase G.5 (the online `chat_turn_facts` writer)

Assembled 2026-09-20 by an **independent adversarial reviewer** who did not write the work. Nothing was
committed, edited, stashed or reverted; every experiment below ran against copies in a scratchpad or
against the `copilot_mro_test` database with its own throwaway tenant, cleaned up in a `finally`.

| phase | repo | worktree | branch | committed | uncommitted (the actual work) |
|---|---|---|---|---|---|
| G.5 | copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `c80c686d` — **test files only** | `copilot_mro/app/db/chat_history/blocks.py` (+102), `copilot_mro/app/db/postgres_table_definitions_modules/chat_turn_facts.py` (+238) |

**Scope isolation, re-verified.** `git diff --stat` lists 25 modified paths. A per-file grep for
`chat_turn_facts` across every one of them returns hits in **exactly two**: `blocks.py` (10) and
`chat_turn_facts.py` (13). The other 23 are untouched by this work and were not reviewed.

Test lanes, re-measured at assembly (`rootdir` printed on every run, all three merged worktrees on
`PYTHONPATH`, `POSTGRES_DB=copilot_mro_test`, `DEBUG=false`, shared `api` Poetry env, never `-q`):

| lane | rootdir | result |
|---|---|---|
| `tests/unit/chat_history` | `/home/aditya/Code/copilot-mro-obsm` | 95 collected / **87 passed, 8 skipped** in 1.27s |
| `tests/db/chat_history` | `/home/aditya/Code/copilot-mro-obsm` | **27 passed** in 0.93s |
| combined: `unit/chat_history` + `db/chat_history` + `unit/metering` + `registries/tables` | `/home/aditya/Code/copilot-mro-obsm` | **274 passed, 8 skipped** in 5.70s — no new failure surfaced by combining |

Both recorded figures reproduce exactly. The deliberate combined run found nothing the directories hid.

---

## What I tried to break and could not

Recorded separately from what I did not test, because they are different claims.

1. **The owner's ruling, against real Postgres.** The unit guard proves the savepoint bracket against a
   fake cursor. I proved the *property* live. A throwaway tenant, nine consecutive `save_block` calls
   through the real `ChatHistoryDB`, each with a scoreboard engineered to break the facts INSERT in a
   different way. **Three of them failed the projection. All nine blocks committed**, `chat_blocks`
   held 9 rows and `chat.total_blocks` read 9. The savepoint recovers the subtransaction and the
   transaction stays usable. The ruling is real in production, not only in the stub.
2. **Dict-projected vs jsonb-round-tripped parity.** I built fifteen adversarial payloads (tuples,
   `MappingProxyType`, `Decimal`, `datetime`, `frozenset`, non-string dict keys, over-long ints, NaN,
   unicode, empty containers) and found six that diverge **at the projection function**. Then I checked
   whether any of them can reach `block_data`, and **none can**: `block.model_dump(mode="json")`
   normalises tuple→list, frozenset→list, `Decimal`→str, `datetime`→str, and *raises* on
   `MappingProxyType` — before `dumps_jsonb` is ever called. The `default=str` safety net in
   `dumps_jsonb` is effectively dead on this path. The parity holds; see G5-12 for what that means for
   the guard.
3. **`BaseException` escaping `except Exception`.** I could not construct a realistic production path.
   `save_block` is synchronous with no await points, so `asyncio.CancelledError` (a `BaseException`
   since 3.8) cannot be injected mid-function; `MemoryError` and `RecursionError` are `Exception`
   subclasses and are caught. `KeyboardInterrupt`/`SystemExit` remain theoretically uncaught — see
   G5-18, downgraded accordingly.
4. **The function-local import's stated rationale.** I reproduced the cycle exactly: with the aggregator
   unloaded, `importlib.import_module("copilot_mro.app.db.postgres_table_definitions_modules.chat_turn_facts")`
   raises `ImportError: cannot import name 'get_chat_turn_facts_postgres_table_definitions' from
   partially initialized module … (most likely due to a circular import)`. The reason given is true.
   What I *did* break is the conclusion drawn from it — see G5-14.
5. **The projection/upsert parity diff, verified field by field myself.** Comment- and blank-stripped
   body diff of the two `facts_from_block_data` implementations: **exactly one line differs**, the
   constant name (`_ANSWER_VALUES` vs `ANSWER_FOUND_VALUES`). `FACTS_UPSERT_SQL` vs `_UPSERT_SQL`:
   **byte-identical** modulo the constant name. `facts_upsert_params` vs `_as_params`: identical modulo
   the function name. The claim is literally true.

### What I did not test

- Any behaviour under **concurrency** — two saves of the same `block_id` racing, or a deadlock on the
  facts INSERT. Postgres' subtransaction recovery covers deadlock in principle; I did not force one.
- The **latency cost** of three extra round trips per saved block on the user-facing path (G5-19).
- **Live/production** behaviour: everything here ran against `copilot_mro_test`.
- The other 23 uncommitted production files, by instruction.
- `core-obsm`'s own test suite (I read its drift pin and resolved its sibling path, but did not run it).

---

## Defects, ranked

Severity is what a **user or an operator experiences**, independent of the tier/claim-state axis below.

### P0 — none.

I attacked the property the owner ruled on and it held against the real driver. No finding below costs
a user their chat turn or exposes another tenant's data. Tier 0 stays empty, as in all nine prior slices.

### P1

**P1-a — The relation cannot see the turns the panels most want to count, and the stated mitigation is
wrong for that class.** `blocks.py:552-563` cites AD-3 Ruling 5 as the *precedent for the savepoint*.
Ruling 5's own reason is different, and `tests/unit/metering/test_ledger_write_point.py:247-256` states
it verbatim: *"every turn whose block was never persisted (a 500 before the save, a stream whose
background save timed out, an automation whose block was rejected) would go unbooked."* The facts writer
is now sited in exactly the place that ruling forbids for the ledger, and inherits exactly that gap.
**Operator experience:** the Quality and Reliability panels compute failure rates over a denominator
that structurally excludes failed turns — `/rag` 500s before `save_block`, `/rag/stream`'s background
save can time out, and the automations executor skips the save on a failed run. The docstring's
mitigation — *"a gap shows as a dip in the series rather than as quietly plausible numbers"* — is false
for this class: those turns never had a block, so they are invisible rather than a dip, and the backfill
cannot fill them either, because it reads `chat_blocks`. The relation's contract ("one row per persisted
chat turn") is consistent; the *panels'* reading of it is not, and nothing says so.

**P1-b — Three unvalidated scoreboard fields can cost the row, not two — and a fourth corrupts it.**
Live-proved on `copilot_mro_test`, one `save_block` per case:

| scoreboard input | outcome |
|---|---|
| `tool_count = 2**40` | block kept, **facts row MISSING** (integer out of range) |
| `tool_count = "two"` | block kept, **facts row MISSING** (invalid input syntax for integer) |
| `query_type = {"a": 1}` | block kept, **facts row MISSING** — *not flagged by the implementer* |
| `query_type = ["a", "b"]` | **row written with `query_type = '{a,b}'`** — the PostgreSQL array literal. *Not flagged; this is corruption, not absence* |
| `confidence_probability = 1e308` | row written, `confidence` = a **309-digit numeric** in a column documented "0..1" |

**Operator experience:** a `query_type` panel grows a bogus `{a,b}` bucket that no router ever emitted,
and any `AVG(confidence)` is poisoned by a single turn. `answer_found` has a CHECK constraint and a
vocabulary gate; `query_type`, `capability_outcome` and `confidence` have neither.

**P1-c — The cross-repo pin both docstrings cite as the guarantee resolves to the wrong checkout.**
`core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py:24` is
`_MRO_ROOT = sibling_repo(__file__, "copilot-mro")`. Resolved live: `/home/aditya/Code/copilot-mro` —
the **pre-merge** sibling, whose `chat_turn_facts.py` contains **no `facts_from_block_data`**.
`chat_turn_facts.py:27` says *"Rows the two produce are indistinguishable, which is pinned from core's
side"*; it is not. (Already logged as merge-plan G.25(a) — the defect is not new, but G.5 leans on it in
a docstring without qualification, and the pin compares only constants, never the projection body.)

**P1-d — A chat delete breaks parity permanently and unreconcilably, and retains user data in a read
relation.** Live-proved: `create_chat` → `save_block` → `delete_chat`. After the delete,
`chat_blocks.deleted = true`, the backfill's `WHERE cb.deleted = false` yields **nothing** for that
block, and the `chat_turn_facts` row **survives intact** carrying `user_id`, `session_id` and
`cited_documents` (the titles of the documents the answer cited). A panel-style
`SELECT count(*) FROM chat_turn_facts` still counts it. So: (i) "rows the two produce are
indistinguishable" is false after any delete; (ii) the backfill can never reconcile it; (iii) unlike
`chat_blocks` — retained for audit but filtered out of **every** read — this relation is retained *and*
read. The implementer flagged the panel-counting half only.

**P1-e — The property the owner ruled on has no guard against a real connection.** The savepoint half is
proved only by `tests/unit/chat_history/test_chat_turn_facts_writer.py:344`, against a hand-written
`_Cursor` that raises a plain `RuntimeError` on a matched statement and a `_Conn` whose `commit()`
increments a counter. That stub cannot model Postgres aborting a transaction on a failed statement, so
"the block still commits" is proved by a counter on a fake. The db lane — which has the real driver —
has **zero failure-path coverage**: all four of its cases are happy paths. I proved the property myself
(see "could not break", item 1), so nobody is harmed today; the point is that the next change here will
be certified by a stub that would stay green if Postgres' semantics changed underneath it.

### P2

**P2-a — Three mutation-proved holes in the parity guard.** Sources mutated in memory, exec'd as fresh
modules, run against the six shapes `test_the_writers_projection_equals_the_backfills` parametrises.
Full results in G5-12; the survivors: dropping `_opt_float`'s `isinstance(value, bool)` exclusion
(**M1**), replacing `len(set(tool_set))` with `len(tool_set)` (**M2**), and dropping `cited_documents`
from `facts_upsert_params`' json-serialised tuple (**M10**). M10 also survives
`test_the_two_mirrors_agree_on_the_contract_constants`, because that test compares `FACTS_COLUMNS`,
`FACTS_VERSION`, the vocabulary and `FACTS_UPSERT_SQL` — **but never `facts_upsert_params` against
`_as_params`**. Under M10 the two builders produce different rows and every guard stays green.

**P2-b — The `department` equality claim is false as literally written.** See G5-08; the commissioned
sub-review's findings are relayed verbatim in the hand-back.

**P2-c — The silent-failure path is avoidable in one line, and the elegant fix was not considered.**
See G5-14.

**P2-d — The only signal for a silently missing row is a warning whose fields do not survive the sinks.**
See G5-15.

**P2-e — Smaller:** a dead return value (G5-16); a non-total exception handler (G5-17); a `BaseException`
gap (G5-18); unmeasured added latency on the user-facing save path (G5-19); six parity shapes that are
barely non-redundant (G5-13).

---

## The ordering question (brief item 7) — STALE PRECONDITION

Plainly: **the precondition is stale.** Task R (G.1) is a read-only audit whose every deliverable is a
document; it changes no production code, and it does not touch `blocks.py`, `save_block`, `block_data`,
`metadata`, `routing_scoreboard` or the projection's columns. The writer emits **no span, no metric, no
attribute and no cardinality surface**, so R.2 — the unrun half that matters — has nothing to approve
here. The merge plan's two widened halves of G.1 (R.3 coverage matrix, R.4 orphan analysis) **already
ran, read-only, on 2026-09-20**, and `chat_turn_facts` appears **zero times** in either output.

`observability-rebuild.md:639-643`, item 11.3, in full:

> - [ ] 11.3 ~~After Gate M + Task R,~~ **after Task R**, close the Phase 3.7 `chat_turn_facts` writer and prove
>       Agent SDK/LangGraph fact, ledger and telemetry parity without adding a second writer. The writer is
>       carried as G.5 in `docs/plans/observability-telemetry-merge-and-completion.md`; the backfill **schedule**
>       was dropped by the owner 2026-09-19, so the online writer is the sole populator and there is nothing to
>       reconcile a timer against.

11.3 is a **parity/completion gate**, not the build; it explicitly delegates the writer to G.5 and asks
only for "prove parity" and "no second writer". The caveat, stated honestly: master-R.4's literal text
*does* name this item — *"re-check phases 5 and 7 items that touch the conflict zone (`chat_turn_facts`
writer, …)"* — so the implementer should not be credited with having cleared the gate. But the two things
a re-check could have changed are both already settled independently: whether the writer should exist
(the owner dropped the backfill schedule 2026-09-19, making it the sole populator) and what shape it
projects (pinned on three sides by the DDL, the 2026-09-05 backfill and the drift pin). The live half of
the constraint was the §1 conflict-zone freeze, retired by Gate M on 2026-09-14/15. Recommended
disposition: strike the Task R precondition from 11.3's *writer* half, keep it on 11.3's *parity-proof*
half, and record it as the owner ruling answering the already-open Q3.

Numbering hazard worth carrying forward: the master plan's `R.3`/`R.4` and the merge plan's widened
`R.3`/`R.4` are **different tasks**, and only the master's R.4 names this writer.

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|
| G5-01 | copilot-mro | `blocks.py:581,612,617-618` | Wrap the projection in `SAVEPOINT chat_turn_facts` → write → `RELEASE`; on failure `ROLLBACK TO` + `RELEASE` + one warning, and let the block commit | The owner's ruling made real: an analytics projection must never cost a user their chat turn. Without it Postgres aborts the whole transaction on the first failed statement | **Live-proved by this review, not by the suite.** Nine `save_block` calls against `copilot_mro_test`, three with scoreboards that break the facts INSERT: all nine blocks committed, `chat_blocks` held 9, `chat.total_blocks` read 9, three `chat_turn_facts` rows absent. The savepoint recovers the subtransaction and the transaction stays usable | `tests/unit/chat_history/test_chat_turn_facts_writer.py::test_a_failing_facts_write_is_rolled_back_to_its_savepoint_and_the_block_commits` (:344) + `::test_the_happy_path_releases_its_savepoint_without_rolling_back` (:365) — **both against a fake cursor; see G5-02** | not recorded by the implementer. This review's live run is a property proof, not a mutation proof | 1 | G5 | ASSERTED |
| G5-02 | copilot-mro | `tests/unit/chat_history/test_chat_turn_facts_writer.py:112-158`; `tests/db/chat_history/test_chat_turn_facts_db_roundtrip.py:197-305` | Prove the savepoint property against a hand-written `_Cursor`/`_Conn`; give the db lane four happy paths only | The unit stub makes the statement sequence assertable without a database | The stub raises a plain `RuntimeError` on a substring match and its `commit()` increments a counter; it cannot model Postgres aborting a transaction. **The db lane has zero failure-path coverage** — all four cases are happy paths | `::test_a_failing_facts_write_is_rolled_back_to_its_savepoint_and_the_block_commits` (:344) exists and passes; it does not exercise a real connection. **No db-lane guard exists for this property** | **no.** A mutation removing the savepoint while keeping the `except` would leave the stub's commit counter at 1 and the property untested | 1 | G5 | OPEN |
| G5-03 | copilot-mro | `blocks.py:748-757` (call site, inside `cur.rowcount == 1`) | Mint the row only where the block insert did, on the save's own cursor, before the commit | Makes the projection's idempotency the *same fact* as the block insert's `ON CONFLICT DO NOTHING`, not a second one | A retry (`rowcount == 0`) skips the whole branch, so not even the `SAVEPOINT` is issued — asserted positively | `::test_a_retried_save_inserts_no_block_and_writes_no_facts` (:329), which asserts both `facts_writes() == []` **and** `not any(sql.startswith("SAVEPOINT"))`; db-lane `::test_a_re_saved_block_writes_no_second_facts_row_and_moves_no_timestamp` (:284) | not recorded | 1 | G5 | ASSERTED |
| G5-04 | copilot-mro / core | `chat_turn_facts.py:195-344` vs `core-obsm/scripts/backfill_chat_turn_facts.py:134-344` | Mirror the backfill's projection, upsert SQL and params builder verbatim rather than importing (no `core` → `copilot_mro` dependency edge) | Two copies of one contract; the mirror is what the drift pin exists for | **Re-verified by this review, field by field.** Comment/blank-stripped body diff of the two `facts_from_block_data`: **exactly one differing line**, the constant name. `FACTS_UPSERT_SQL` vs `_UPSERT_SQL`: identical. `facts_upsert_params` vs `_as_params`: identical modulo the name. The claim is literally true | `::test_the_writers_projection_equals_the_backfills` (:475, six parametrised shapes) + `::test_the_two_mirrors_agree_on_the_contract_constants` (:481) | **yes, by this review** — eleven mutations, eight caught; see G5-12 for the three survivors | 1 | G5 | SETTLED |
| G5-05 | copilot-mro | `tests/db/chat_history/test_chat_turn_facts_db_roundtrip.py:183-194,224` | Prove dict-projection == jsonb-projection by running the **backfill's** `facts_from_block_data` over the stored row and comparing, with a narrow `Decimal`→`float` coercion on the two `numeric` columns only | Equality asserted rather than argued; a blanket `str()` would launder real divergences | **The property holds, and for a reason the docstring does not state.** I built 15 adversarial payloads and found 6 that diverge at the projection — then showed none can reach `block_data`, because `model_dump(mode="json")` normalises tuple→list, frozenset→list, `Decimal`→str, `datetime`→str and *raises* on `MappingProxyType`. The numeric coercion is not the only divergence class; it is the only one that **survives pydantic** | `::test_a_saved_block_lands_a_facts_row_the_backfill_would_have_written` (:197) | not recorded. **The load-bearing fact — that `model_dump(mode="json")` is the normaliser — is guarded by nothing.** Switching `save_block:648` to `model_dump()` (python mode) would let tuples and datetimes through and silently break parity; no test would fail | 2 | G5 | ASSERTED |
| G5-06 | copilot-mro | `blocks.py:748-757`, `chat_turn_facts.py:205-209` | Pass the save's `department` parameter rather than joining `chats` | The lock gate `c.department IS NOT DISTINCT FROM %s` means no block exists where they differ | The gate is asserted on the statement itself, so a future relaxation breaks the test rather than a panel | `::test_the_writer_projects_the_department_the_lock_gate_proved_equal` (:309), which asserts `"department IS NOT DISTINCT FROM %s" in BLOCKS._LOCK_CHAT_FOR_SAVE_SQL` and round-trips `"PILOT"` and `None` | not recorded | 1 | G5 | ASSERTED |
| G5-07 | copilot-mro | `blocks.py:581-612` | Open the savepoint **before** the function-local import and the projection, so an `ImportError` or a projection crash is inside the bracket | "A broken mirror must degrade to a warning, not to a lost turn" | Correct ordering, and I could not break it: every exception path I could raise from the projection leaves the bracket open and recoverable | `::test_a_broken_projection_import_degrades_to_a_missing_row_not_a_lost_block` (:374) — substitutes a bare `ModuleType` for the dotted name and asserts the full `SAVEPOINT`/`ROLLBACK TO`/`RELEASE` sequence and `commits == 1` | not recorded | 1 | G5 | ASSERTED |
| G5-08 | copilot-mro | `chat_turn_facts.py:208` | Rest the department-equality argument on "**nothing in the estate ever UPDATEs `chats.department`**" | If true, writer and backfill cannot disagree; if false, they disagree *silently* | **FALSE as literally stated; true if narrowed to "no runtime code path".** A commissioned exhaustive sub-review found **two** estate-resident statements that do literally UPDATE the column, both via dynamically-composed `INSERT … ON CONFLICT … DO UPDATE SET` that no `rg "UPDATE chats"` can see: `copilot-mro-obsm/scripts/seed_test_estate.py:388-406` (builder at `:81-97`) and `copilot-mro-obsm/tests/fixtures/tenancy/second_tenant.py:425-443` (builder at `:273-299`, whose docstring makes the UPDATE deliberate). Both write a *constant*, so no divergence is produced today. Ruled out with evidence: no ORM anywhere, no triggers on `chats` (live `pg_trigger` query), no `MERGE`/`COPY`/`executemany` writer, no migration or `.sql` that backfills the column, no HTTP surface (no PATCH/PUT on `/chats`), `ChatInfo` has no `department` field so the `chat_data` jsonb cannot smuggle it | none — the guard asserts the *lock gate*, which is the other limb of the argument. **Nothing guards the no-UPDATE limb** | not recorded | 2 | G5 | OPEN |
| G5-09 | copilot-mro | `blocks.py:552-563` | Cite AD-3 / Ruling 5 (`usage_ledger.py`) as the **precedent for the savepoint**, and site the facts write in `save_block` anyway | The savepoint answers the "a failed write must not lose the block" direction | **The cited ruling's own reason is the other direction, and it is unaddressed.** `tests/unit/metering/test_ledger_write_point.py:247-256` states it verbatim: *"every turn whose block was never persisted (a 500 before the save, a stream whose background save timed out, an automation whose block was rejected) would go unbooked."* The facts relation inherits exactly that. The docstring's mitigation — *"a gap shows as a dip in the series rather than as quietly plausible numbers"* — is false for this class: those turns never had a block, so they are invisible, and the backfill (which reads `chat_blocks`) cannot fill them | none. `test_ledger_write_point.py::test_the_ledger_is_not_written_from_the_block_persistence_path` (:247) guards the *ledger*, by asserting `record_turn_usage` and the string `llm_usage` are absent from `blocks.py` — which is why this module names that relation by file rather than by name. No equivalent exists for the facts relation, and none could: the write *is* in the block-persistence path, deliberately | not recorded | 2 | G5 | OPEN |
| G5-10 | copilot-mro | `chat_turn_facts.py:239-243` (`tool_count`), `:245-246` (`tool_failures`), `:334` (`query_type`), `:340` (`confidence`) | Take four scoreboard values straight into typed columns with no validation — flagged as inherited from the backfill, and left | The projection is a verbatim mirror; validating on one side alone would break parity | **Live-proved, one `save_block` per case:** `tool_count = 2**40` → missing row; `tool_count = "two"` → missing row; `query_type = {"a":1}` → missing row (**not flagged**); `query_type = ["a","b"]` → **row written with `'{a,b}'`, the PG array literal** (**not flagged — corruption, not absence**); `confidence = 1e308` → a 309-digit numeric in a column documented "0..1". Live DDL confirms `tool_count`/`tool_failures`/`citation_count` are `integer` and every varchar is unbounded, so length is not the hazard — type and range are. `answer_found` has both a CHECK and a vocabulary gate; these four have neither | none — no test supplies a malformed scoreboard on either side of the mirror | not recorded | 2 | G5 | OPEN |
| G5-11 | copilot-mro / core | `chat_turn_facts.py:27`; `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py:24` | Assert that indistinguishability is *"pinned from core's side"* | A mirror is a drift hazard; the pin is what makes it safe | **The pin resolves to the wrong checkout.** `_MRO_ROOT = sibling_repo(__file__, "copilot-mro")` → resolved live to `/home/aditya/Code/copilot-mro`, the **pre-merge** sibling, whose `chat_turn_facts.py` has **no `facts_from_block_data`** (verified by reading the file). The pin stays green while reading a tree that does not contain the code under review — and it compares only `FACTS_COLUMNS`, `FACTS_VERSION` and the vocabulary, never the projection body. Known as merge-plan **G.25(a)**; G.5 cites it unqualified | `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py` — **resolves, but against the pre-merge checkout.** The only body-level comparison in the estate is copilot-mro-obsm's `::test_the_writers_projection_equals_the_backfills` (:475), which loads core-obsm correctly via `sibling_repo(__file__, "core-obsm", …)` | not recorded | 2 | G5 | OPEN |
| G5-12 | copilot-mro | `tests/unit/chat_history/test_chat_turn_facts_writer.py:458-491` (`_PARITY_SHAPES`, :475, :481) | Six block shapes, compared field by field, plus two anti-vacuity guards | Two empty dicts are equal; the shapes and the populated-column floor are what stop the comparison being vacuous | **Eleven mutations run by this review** (sources mutated in memory, exec'd as fresh modules, run against the same six shapes — nothing on disk touched). **Eight caught, three survive.** Caught: citation de-duplication, unsorted `route`, `_ROUTE_MAX_CHARS` 200→100, `_CITED_DOCUMENTS_CAP` 20→10, `tool_usage` failure counting, `bool()` coercion of `needs_clarification`, the `answer_found` vocabulary gate. **Survivors: (M1)** dropping `_opt_float`'s `isinstance(value, bool)` exclusion at `:190` — no shape supplies a bool where a number is expected, so `confidence_probability: True` → `1.0` goes unseen; **(M2)** `len(set(tool_set))` → `len(tool_set)` at `:225` — no shape has a duplicated tool; **(M10)** dropping `cited_documents` from `facts_upsert_params`' json-serialised tuple at `:366` — **survives the parity shapes *and* the constants test, and the two builders then produce different rows.** M10 is the structural hole: `test_the_two_mirrors_agree_on_the_contract_constants` compares `FACTS_COLUMNS`, `FACTS_VERSION`, the vocabulary and `FACTS_UPSERT_SQL`, but **never `facts_upsert_params` against `_as_params`**. Also: every caught mutation except one was caught by **exactly one** of the six shapes | `::test_the_parity_comparison_is_not_vacuous` (:493), `::test_the_write_assertions_are_not_vacuous` (:534) — both resolve and both do real work (20 columns, ≥18 populated, five distinct projections of six shapes) | **yes, by this review** — M1/M2/M10 named above, each with the exact source edit and the exact assertion that stayed green | 2 | G5 | OPEN |
| G5-13 | copilot-mro | `tests/unit/chat_history/test_chat_turn_facts_writer.py:458-491` | Fix six shapes as the contract, kept locally rather than imported from core | "A shape this side never exercised is a shape the mirror can drift on" | Right instinct, thin execution: the shapes are barely non-redundant. Each caught mutation above was caught by exactly one shape (M8 excepted), and the branches no shape enters are exactly where M1 and M2 live — a bool in a numeric slot, and a repeated tool | `::test_the_parity_comparison_is_not_vacuous` (:493) asserts five distinct projections of six shapes, which measures distinctness, not **branch coverage** | not recorded | 1 | G5 | OPEN |
| G5-14 | copilot-mro | `blocks.py:582-592` | Import the projection **inside** the savepoint, function-locally, so an `ImportError` degrades to a missing row rather than a crash | A module-scope import enters the registry's leaf/aggregator cycle at the leaf and raises at boot | **The rationale is true and I reproduced it**: with the aggregator unloaded, importing the leaf raises `ImportError: cannot import name 'get_chat_turn_facts_postgres_table_definitions' from partially initialized module … (circular import)`. **But the conclusion does not follow.** The leaf's *only* dependency on the aggregator is `_build_create_table_sql` (`chat_turn_facts.py:47`), which the aggregator itself merely re-exports from `utils.table_builder` (`postgres_table_definitions.py:18-21`). I loaded the leaf successfully with the aggregator stubbed to that one symbol. Importing `build_create_table_sql` from `utils.table_builder` directly dissolves the cycle for this leaf, lets `blocks.py` import at module scope, and converts a **silent missing row** into a **loud boot failure** — which is the direction this codebase prefers everywhere else. The deliberate silent-failure path is therefore avoidable, not forced | `::test_a_broken_projection_import_degrades_to_a_missing_row_not_a_lost_block` (:374) guards the degradation; nothing guards the *necessity* of it | not recorded | 2 | G5 | OPEN |
| G5-15 | copilot-mro | `blocks.py:619-628` | One `logger.warning(..., extra={...})` per failed projection, five diagnostic fields, no metric | "A broken mirror must degrade to a warning" | **The fields do not survive the sinks.** `logger` is loguru (`blocks.py:14`). `extra={...}` is the stdlib idiom: loguru puts it at `record["extra"]["extra"]` (verified: `probe message || extra={'extra': {...}}`), and `utils/observability/log_bridge.py:84-101` `flatten()` then stringifies the non-primitive value into **one** attribute. The human sink drops it entirely — my live run printed `chat_turn_facts projection failed; block save continues without it` with no block id and no error text. The estate's own telemetry convention spreads kwargs (`**failure_fields(error)`). **And there is no counter or metric**, so in an observability-rebuild phase the observability writer's own failure rate is invisible to every dashboard. Mitigating: `extra={...}` is this file's existing convention at `:362`, `:468`, `:685`, `:853` | none — no test asserts anything about the warning's payload | not recorded | 2 | G5 | OPEN |
| G5-16 | copilot-mro | `blocks.py:541-546`, `:578`, `:748` | `_write_chat_turn_facts` returns `bool`, *"for the tests that pin this behaviour"* | — | **Nothing consumes it.** The call site at `:748` discards it, and `grep -rn "_write_chat_turn_facts" tests/ copilot_mro/` returns exactly the definition and that one call. The unit tests assert on `cursor.facts_writes()`, never on the return. The docstring's justification is false | none | not recorded | 1 | G5 | OPEN |
| G5-17 | copilot-mro | `blocks.py:614-618` | Deliberately do **not** catch a failure in the recovery itself, on the grounds that the connection is then unusable | "The outer handler's rollback is the right answer" | **The reasoning holds for the case it names and is narrower than the docstring implies.** The only way to reach an uncatchable recovery is for `cur.execute("SAVEPOINT chat_turn_facts")` at `:581` to fail — the `ROLLBACK TO` at `:617` then raises `InvalidSavepointSpecification`, escapes uncaught, and `save_block`'s outer handler rolls back and re-raises: **the block is lost.** Within `save_block`'s flow the transaction is healthy at that point (every preceding statement would already have raised), so the realistic trigger is a dying connection — where the block was lost anyway. A narrower residual: `RELEASE` succeeding server-side but erroring client-side would leave `ROLLBACK TO` addressing a released savepoint. Both are connection-death shaped; the conclusion survives, the docstring overstates it | none — no test drives a failure of the savepoint statement itself | not recorded | 1 | G5 | OPEN |
| G5-18 | copilot-mro | `blocks.py:614` | `except Exception`, not `except BaseException` | — | I tried and could not reach it in production. `save_block` is synchronous with no await points, so `asyncio.CancelledError` (a `BaseException` since 3.8) cannot be injected mid-function; `MemoryError` and `RecursionError` are `Exception` subclasses and are caught; `GeneratorExit` is unreachable here. `KeyboardInterrupt`/`SystemExit` remain theoretically uncaught — a local dev run or a signal handler that raises. Recorded as a known narrow gap, not a defect | none | not recorded | 1 | G5 | OPEN |
| G5-19 | copilot-mro | `blocks.py:581`, `:611`, `:612` | Three extra round trips (`SAVEPOINT`, the upsert, `RELEASE`) per saved block, inside the user-facing save transaction, under `SET LOCAL statement_timeout = 15000` | Same transaction, same cursor, one fact of idempotency | Unmeasured by the implementer and unmeasured here. `statement_timeout` is per-statement so there is no cumulative abort risk; the cited precedent (`usage_ledger`) dispatches its write to `asyncio.to_thread` instead. Likely immaterial at ~2 ms RTT; recorded because "likely" is not "measured" | none | not recorded | 1 | G5 | OPEN |
| G5-20 | copilot-mro / core | `chat_turn_facts.py:27`; `core-obsm/scripts/backfill_chat_turn_facts.py:272-278` | Keep the backfill as a gap-fill tool whose rows are *"indistinguishable"* from the writer's | At one `facts_version` it can create a missing row and never correct a wrong one | **Live-proved false after any delete.** `create_chat` → `save_block` → `delete_chat`: `chat_blocks.deleted = true`, the backfill's `WHERE cb.deleted = false` yields nothing for that block, and the facts row **survives** carrying `user_id`, `session_id` and `cited_documents` (the titles the answer cited). A panel-style count still counts it. So the two writers are *not* indistinguishable after a delete, the backfill can never reconcile it, and — unlike `chat_blocks`, which is retained for audit but filtered out of every read — this relation is retained **and** read. `core-obsm/core/resources/analytics/panels/{quality,reliability,operations}.py` carry no `deleted` filter (grep: zero hits). The implementer flagged the panel-counting half only | none — no test deletes a chat and looks at `chat_turn_facts` | not recorded | 2 | G5 | OPEN |
| G5-21 | copilot-mro | `tests/unit/chat_history/test_chat_turn_facts_writer.py:44-64` | Pin this worktree's registry module into `sys.modules` by dotted name and assert `module.__file__` | `copilot_mro` is a PEP 420 **namespace** package (verified: no `__init__.py` in either checkout) whose `__path__` spans this worktree and the pre-merge sibling; an unpinned import could resolve to a copy with no projection, an `ImportError` the writer's own savepoint swallows | The hazard is real and the assertion is the right shape: the sibling's `chat_turn_facts.py` genuinely has **no `def facts_from_block_data`** (verified). `_load_facts_contract` pins the dotted name, so `save_block`'s relative import resolves through `sys.modules` to the pinned module — **sufficient for this test file**. Two limits worth stating: it is a *test-environment* hazard only (one checkout exists in production), and the assertion protects this file, not the estate — `core-obsm`'s drift pin has the mirror-image bug and is not protected (G5-11) | `::_load_facts_contract` (:50, the `assert Path(module.__file__) == _REGISTRY_DIR / "chat_turn_facts.py"` at :63) — resolves and fires at import time | not recorded | 1 | G5 | ASSERTED |
| G5-22 | copilot-mro | `tests/unit/chat_history/test_chat_blocks_cache_generation.py` (`c80c686d`, `:64`, `:74-82`, `:90-96`) | Teach the Postgres stand-in `SAVEPOINT`/`RELEASE`/`ROLLBACK TO` and assert one facts row per save | The stand-in enumerates every statement `save_block` issues and refused the new ones | The stand-in models the savepoint by **staging** and discarding, so "a savepoint whose rollback did not discard the staged write" is distinguishable from one that did — which is the property a naive counter would miss | `tests/unit/chat_history/test_chat_blocks_cache_generation.py` (24 cases, all green in both the isolated and the combined run) | not recorded | 1 | G5 | ASSERTED |
| G5-23 | copilot-mro | `tests/unit/chat_history/_chat_history_store_loader.py` (`c80c686d`) | Stop unconditionally popping `copilot_mro.app.db.chat_history.{_tables,base,chats,blocks}`; restore a real one when present | Popping is only correct while nothing real is loaded; ordered after a test that imports the app for real it left a `ChatHistoryDB` bound to a `chats` module the name no longer resolved to, so `test_chat_history_roundtrip`'s delete-race monkeypatch patched a module the live object never consulted — **a hook that never fired, in a suite that reported green** | A genuine pre-existing green-suite defect, found only because the new file sorts last in its directory. This is the kind of finding the phase is supposed to produce | `tests/db/chat_history/test_chat_history_roundtrip.py` (27 db-lane cases green) | not recorded — no test asserts the loader restores rather than pops | 1 | G5 | ASSERTED |
| G5-24 | copilot-mro | `docs/plans/observability-rebuild.md:639-643` (item 11.3); `observability-rebuild-phase-11-audit-followups.md:78`, `:84-85`, `:192-198` | Build G.5 although two documents order it after Task R (G.1), which is unstarted | Built on instruction | **STALE PRECONDITION.** Task R is read-only and produces documents; it touches none of `blocks.py`, `save_block`, `block_data`, `metadata`, `routing_scoreboard` or the projection's columns. The writer emits no span, metric, attribute or cardinality surface, so R.2 has nothing to approve. The merge plan's two widened halves of G.1 (R.3 coverage matrix, R.4 orphan analysis) **already ran read-only on 2026-09-20** and mention `chat_turn_facts` **zero times**. 11.3 is a parity gate that delegates the writer to G.5. Caveat: master-R.4 does name this item — but both things a re-check could change are already settled (the owner dropped the backfill schedule 2026-09-19; the shape is pinned by DDL + backfill + drift pin). The live half of the constraint was the §1 conflict-zone freeze, retired by Gate M on 2026-09-14/15 | none — a plan ordering is not a testable property | not recorded | 2 | G5 | OPEN |

**G5 counts — 24 rows.** Tier: 0 = **0**, 1 = 13, 2 = 11. Chunk: G5 = 24.
Claim state: **SETTLED = 1 · ASSERTED = 8 · OPEN = 15.**

SETTLED: G5-04.
ASSERTED: G5-01, G5-03, G5-05, G5-06, G5-07, G5-21, G5-22, G5-23.
OPEN: G5-02, G5-08, G5-09, G5-10, G5-11, G5-12, G5-13, G5-14, G5-15, G5-16, G5-17, G5-18, G5-19, G5-20, G5-24.

---

## Open claims, tier 2 first

### Tier 2, OPEN — no guard, judgment only

| id | Claim | What an auditor has to settle |
|---|---|---|
| **G5-09** | **The relation cannot see the turns the panels exist to count.** The writer is sited exactly where AD-3 Ruling 5 forbids the ledger, for reasons the ruling itself states and this module does not address: a 500 before the save, a stream whose background save timed out, an automation whose block was rejected. The savepoint answers the opposite direction | Is a Quality/Reliability panel set whose denominator structurally excludes failed turns acceptable — and if so, must the docstring's "a gap shows as a dip in the series" claim be corrected, since these gaps are invisible rather than dips and the backfill cannot fill them? |
| **G5-10** | **Four unvalidated scoreboard fields, of which the implementer flagged two.** Live-proved: `query_type` as a dict costs the row; `query_type` as a **list** silently writes the PostgreSQL array literal `'{a,b}'`; `confidence = 1e308` writes a 309-digit numeric into a column documented "0..1" | Is "mirror the backfill verbatim, defects included" the right boundary when the mirror now runs online on every turn — or does the pair need a shared validation step landed on both sides in one pass? A corrupt `query_type` bucket is worse than a missing row and was not flagged |
| **G5-11** | **The cross-repo pin cited as the guarantee reads the pre-merge checkout.** `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py:24` resolves to `/home/aditya/Code/copilot-mro`, whose module has no projection. Known as G.25(a); G.5 cites it unqualified in a production docstring | Should G.5 ship a docstring asserting a guarantee that the named guard does not provide — or does G.25(a) block G.5's close? |
| **G5-12** | **Three mutation-proved holes in the parity guard**, one of them structural: `facts_upsert_params` is **never** compared against the backfill's `_as_params` by any test, so a drift in the params builder produces different rows with every guard green | Is a parity claim complete when it compares the projection and the SQL but not the binding? The fix is one assertion; the question is whether the phase closes without it |
| **G5-14** | **The deliberate silent-failure path is avoidable in one line.** The leaf's only dependency on the aggregator is `_build_create_table_sql`, which the aggregator merely re-exports from `utils.table_builder`. Importing it directly dissolves the cycle and lets `blocks.py` import at module scope — turning a silent missing row into a loud boot failure | Is a silent runtime degradation the right trade when a one-line import change makes the failure loud at boot? The rationale given is true; the conclusion drawn from it is not forced |
| **G5-15** | **The only signal for a silently missing row is a warning whose five fields arrive as one stringified blob** (loguru nests `extra=` to `record["extra"]["extra"]`; `flatten()` then `str()`s it), are dropped entirely by the human sink, and are accompanied by **no counter or metric** | In an observability rebuild, is a log line with no queryable attributes and no metric an adequate signal for a data-loss path the docstring itself says will happen? |
| **G5-20** | **A chat delete breaks projection parity permanently and retains user data in a read relation.** The facts row survives `delete_chat` with `user_id`, `session_id` and cited document titles; the backfill would never produce it; the panels count it | Is retaining a per-user projection — including the titles of documents the user's answer cited — past a user-initiated delete acceptable, given `chat_blocks` is retained but filtered out of every read? And does "rows the two produce are indistinguishable" need qualifying? |
| **G5-08** | **The department-equality argument's second limb is false as literally written.** Two seed/fixture upserts write `chats.department` via composed `DO UPDATE SET`; both write a constant, so no divergence exists today, but the invariant is asserted, not enforced (RLS grants the app role UPDATE on `chats`) | Accept a narrowed docstring ("no runtime code path ever UPDATEs `chats.department`"), or enforce it — a `BEFORE UPDATE` trigger would, and would break both seeders on their second run |
| **G5-24** | **G.5 was built out of order on paper.** Two documents order it after Task R; the gate is vestigial (a telemetry-catalogue precondition attached to a non-telemetry item by phase inheritance) but it has not been struck | Owner ruling on the already-open **Q3**: strike the Task R precondition from 11.3's writer half, keep it on the parity-proof half, and record it beside M-SAVEPOINT |

### Tier 1, OPEN

| id | Claim |
|---|---|
| **G5-02** | **The owner's ruling has no guard against a real connection.** The savepoint property is proved only against a hand-written `_Cursor` that cannot model Postgres aborting a transaction, and a `_Conn` whose `commit()` is a counter. The db lane's four cases are all happy paths. This review proved the property live; the repo does not. |
| **G5-13** | The six parity shapes are barely non-redundant — every mutation caught was caught by exactly one shape (M8 excepted), and the uncovered branches are exactly where the two surviving projection mutations live. Distinctness is asserted; branch coverage is not. |
| **G5-16** | `_write_chat_turn_facts` returns a `bool` *"for the tests that pin this behaviour"*. Nothing consumes it — not the call site, not any test. |
| **G5-17** | The recovery is not total: if `SAVEPOINT` itself fails, `ROLLBACK TO` raises `InvalidSavepointSpecification`, escapes uncaught, and the block is lost. The stated reasoning covers connection death but the docstring claims more than the code guarantees. |
| **G5-18** | `except Exception` leaves `KeyboardInterrupt`/`SystemExit` uncaught. No realistic production path found — `save_block` is synchronous, so `CancelledError` cannot be injected — but the gap is unstated. |
| **G5-19** | Three extra round trips per saved block inside the user-facing save transaction, unmeasured on both sides. The cited precedent dispatches its write to a thread instead. |
