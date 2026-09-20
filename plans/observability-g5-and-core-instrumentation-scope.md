# G.5 (`chat_turn_facts` writer) and the `core` darkness — read-only scoping

Every claim below was read in the tree named. Trees as of 2026-09-20:
`core-obsm` `obs-merge` @ `d7f7b54` (clean) · `copilot-mro-obsm` `obs-merge` @ `d8d2570c`
(**13 modified files, another implementer in flight**) · `utils-obsm` `obs-merge` (clean) ·
`docs-obsm` `obs-merge` (clean, and **behind** `/home/aditya/Code/docs` `main` @ `12a1783`) ·
`api-obsm` · `flynapse-otel`.

---

## 1. G.5 — implementable spec

### 1.1 Where the relation lives (brief said "which repo" — answer: split across two)

| Artefact | Repo / tree | Path |
|---|---|---|
| Table definition (DDL, columns, keys, indexes, CHECK) | **copilot-mro** | `copilot-mro-obsm/copilot_mro/app/db/postgres_table_definitions_modules/chat_turn_facts.py` |
| Registry wiring (import + `_DEFINITION_SOURCES`) | copilot-mro | `copilot-mro-obsm/copilot_mro/app/db/postgres_table_definitions.py:65` and `:143` |
| Reference projection + the only writer today | **core** | `core-obsm/scripts/backfill_chat_turn_facts.py` (470 lines) |
| Readers (the panels) | **core** | `core-obsm/core/resources/analytics/panels/{quality,reliability,operations}.py` |
| RLS + role grants | copilot-mro | `copilot-mro-obsm/scripts/provision_rls.py` — `READONLY_SELECT_RELATIONS` at `:273` |
| Privacy census pin | copilot-mro | `copilot-mro-obsm/tests/registries/tables/test_postgres_table_definitions.py:833` (`PRIVATE_RELATIONS`, a **test** constant, not production — the module docstring's "listed in `PRIVATE_RELATIONS`" reads as if it were production) |
| Tenancy pin + index pin | copilot-mro | `copilot-mro-obsm/tests/registries/tenancy/test_tenancy_classifications.py:142`, `:454` |
| Cross-repo drift pin | core | `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py` |

There is **no migration file**. The estate has no Alembic-style migrations for this relation: DDL is
generated from the registry declaration by `_build_create_table_sql` and applied by
`migrate_tenancy_schema.py` (the merge plan's "DB STEP", already run — plan §3 Status, 2026-09-20).

**Columns and keys**, as declared in `CHAT_TURN_FACTS_FIELDS` plus the builder's injection:
`tenant_id` (builder-injected, NOT NULL, leads the PK), `block_id`, `chat_id`, `user_id`,
`department`, `session_id`, `block_timestamp`, `query_type`, `route`, `capability_outcome`,
`answer_found`, `confidence`, `needs_clarification`, `latency_ms`, `tool_count`, `tool_failures`,
`tool_usage` (jsonb), `citation_count`, `cited_documents` (jsonb), `facts_version`, `created_at`
(DB default `now()`).
Primary key declared `["block_id"]`, **widened by the builder to `(tenant_id, block_id)`** — that
pair is the `ON CONFLICT` target. NOT NULL: `block_id`, `block_timestamp`, `needs_clarification`,
`facts_version`, `created_at`. One CHECK, `chat_turn_facts_answer_found_check`, restricting
`answer_found` to `Yes | Unsure | No | NULL`. One index, declared tenant-less and hoisted by the
registry to `chat_turn_facts_time_idx_tnt ON chat_turn_facts (tenant_id, block_timestamp)`.
Tenancy class `tenant` (not operator-scoped). No FK to `chat_blocks`, deliberately.

**"The backfill's facts version" is concretely `FACTS_VERSION = 1`**, declared twice — once in the
copilot-mro registry module and once, mirrored, in the core backfill script — and pinned equal by
`test_chat_turn_facts_drift_pin.py::test_the_facts_version_is_identical`. The writer lands **at
version 1**, not at a new version; bumping it is what re-projects rows, and the writer must not do
that on arrival or it would silently re-project nothing (there is nothing to re-project) while
making the backfill's version-1 rows permanently un-supersedable in the wrong direction.

### 1.2 The block-save path — named exactly

**`ChatHistoryBlocksMixin.save_block`**, in
`copilot-mro-obsm/copilot_mro/app/db/chat_history/blocks.py`, **line 540**.

The transaction it already runs in, line by line:

| Line | What happens |
|---|---|
| 565–569 | `block_data = block.model_dump(mode="json")`; `metadata` defaulted to `{}`; `metadata["session_id"] = session_id` stamped |
| 572 | `now = datetime.utcnow()` |
| 577 | `with postgres.connection() as conn:` — a **raw pooled connection**, `conn.rollback()` first for a clean boundary |
| 581 | `SET LOCAL statement_timeout = 15000` (covers every statement in the transaction, including a facts write) |
| 585 | `postgres.apply_session_tenancy(cur)` — sets the RLS session variables; a raw cursor bypasses `_apply_transaction_context`, so this is what binds the tenant |
| 588–601 | `_LOCK_CHAT_FOR_SAVE_SQL` — `SELECT … FOR UPDATE` on `chats`, gated on `chat_id`, `tenant_id`, `user_id`, `department IS NOT DISTINCT FROM %s`, `deleted = false`. Ownership + liveness + serialization in one |
| 604–612 | topic segment advanced; `block_data["metadata"]["topic_segment_id"]` stamped |
| 615 | `_INSERT_BLOCK_SQL` — `INSERT … ON CONFLICT (tenant_id, block_id) DO NOTHING` |
| 634 | `if cur.rowcount == 1:` — the chat rollup applies only on a real insert |
| 656 | `conn.commit()` — followed by cache-generation renewal and cache invalidation **outside** the transaction |

**Where the facts upsert goes: inside the `if cur.rowcount == 1:` branch at line 634, on the same
cursor, before `conn.commit()` at 656.** Putting it there rather than unconditionally is not an
optimisation — it makes the writer's idempotency the *same fact* as the block insert's, instead of
a second independent one.

**Both call sites** are in `copilot-mro-obsm/copilot_mro/app/api/chat_management.py`:
- `:1339` — non-streaming `/rag`, synchronous, inside a `db.chat.save_block` span opened at `:1333`.
- `:1713` — inside `_build_and_save_chat_block_sync`, driven from `_save_chat_block` through
  `asyncio.to_thread` under `asyncio.wait_for(…, STREAM_BLOCK_SAVE_TIMEOUT_SECONDS)`, span at `:1735`.
`asyncio.to_thread` copies the context, so the RLS binding survives; it already must, because
`save_block` works today.

**Both paths build the full block metadata before calling**, so every input the projection needs is
present: `routing_scoreboard` is stamped into block metadata at
`copilot-mro-obsm/copilot_mro/app/api/chat_management_helper.py:192–194`, upstream of both calls.

### 1.3 Field-by-field: what the backfill computes, and whether the writer can

`facts_from_block_data(block_row)` in `core-obsm/scripts/backfill_chat_turn_facts.py`. Its
`block_row` carries `tenant_id`, `block_id`, `chat_id`, `user_id`, `block_timestamp`, `department`
(from `LEFT JOIN chats`) and the deserialized `block_data`.

| Field | Backfill source | Available in `save_block`? | Note |
|---|---|---|---|
| `tenant_id` | row | yes — parameter | |
| `block_id` | row | yes — `block.block_id` | |
| `chat_id` | row | yes — parameter | |
| `user_id` | row | yes — parameter | |
| `department` | `chats.department` via LEFT JOIN | yes — parameter | **Provably equal**: `_LOCK_CHAT_FOR_SAVE_SQL` gates on `c.department IS NOT DISTINCT FROM %s`, so a save only proceeds when the parameter equals the chat row's column, NULLs included |
| `session_id` | `block_data.metadata.session_id` | yes — stamped at line 569, before the insert | |
| `block_timestamp` | `chat_blocks.block_timestamp` | yes — `block.timestamp`, the same value the insert writes | |
| `query_type` | `metadata.routing_scoreboard.query_type` | yes | |
| `route` | sorted, comma-joined `scoreboard.tool_set`, truncated to `_ROUTE_MAX_CHARS = 200` | yes | |
| `capability_outcome` | `scoreboard.capability_outcome` | yes | |
| `answer_found` | `scoreboard.answer_found`, falling back to `metadata.answer_found` **only when `routing_scoreboard` is absent from metadata**; any value outside `("Yes","Unsure","No")` projects to NULL | yes | the legacy fallback is dead for new turns but must be kept verbatim |
| `confidence` | `scoreboard.confidence_probability`, falling back to `metadata.confidence_probability` **only when the scoreboard is falsy** | yes | |
| `needs_clarification` | scoreboard, else metadata, then `bool(...)` | yes | |
| `latency_ms` | `scoreboard.latency_ms`, else `assistant_response.execution_time * 1000.0` | yes | |
| `tool_count` | `scoreboard.tool_count`, else `len(set(tool_set))`, else `len(tool_usage)` | yes | three-level fallback, order matters |
| `tool_failures` | `scoreboard.status_counts.failed`, else summed from `tool_usage` | yes | |
| `tool_usage` | per-tool `{name, calls, failures}` aggregated from `metadata.tool_call_log`, `name` defaulting to `"unknown"`, `failures` counted on `entry.is_error`, sorted by name | yes | |
| `citation_count` | `len(block_data.citations)` when it is a list, else 0 | yes | |
| `cited_documents` | distinct `{doc_uid, document, manual_type}` from `citations`, capped at `_CITED_DOCUMENTS_CAP = 20`; **falls back to `document_batch`** (`document_id`→`doc_uid`, `title`→`document`, `manual_type` NULL) only when `citations` is empty/not a list; `None` when empty | yes | |
| `facts_version` | constant `1` | yes | |
| `created_at` | not in `FACTS_COLUMNS` — DB default | n/a | |

**Nothing in the projection is uncomputable at save time.** That is the finding: the whole
projection reads `block_data` plus five scalars the save call already holds.

Two residual divergence risks, both provable by test rather than by argument:
1. **Dict-vs-jsonb round trip.** The backfill projects the value Postgres returns from a `jsonb`
   column; the writer would project the in-memory `model_dump(mode="json")` dict that is about to
   be serialized by `dumps_jsonb` (`_tables.py`, `ensure_ascii=True, default=str`). Key order and
   duplicate keys are irrelevant to the projection, and every value it reads is a JSON scalar or
   list, so equality is expected — but it must be **proved by a DB-lane test that saves a block and
   then runs the backfill's own `facts_from_block_data` over the stored row**, not asserted.
2. **Soft-deleted blocks.** `chats.py:342–352` soft-deletes `chats` and `chat_blocks`; **nothing
   deletes `chat_turn_facts`**, and the relation has no `deleted` column. The backfill's
   `_BLOCKS_SQL` filters `cb.deleted = false`. Today that is consistent (the backfill never creates
   a facts row for a deleted block and never removes one). With the online writer it stays
   consistent — but every panel keeps counting turns from chats the user deleted. Pre-existing;
   G.5 inherits it rather than causing it. See open question Q4.

### 1.4 Idempotency — the mechanism that exists

Two layers, both already in the tree. **Propose nothing new.**

1. **`_INSERT_BLOCK_SQL`** (`blocks.py:21–31`): `ON CONFLICT (tenant_id, block_id) DO NOTHING`, and
   the rollup runs only on `cur.rowcount == 1`. This is what makes the at-least-once background
   save idempotent today.
2. **`_UPSERT_SQL`** in the backfill: `INSERT … ON CONFLICT (tenant_id, block_id) DO UPDATE SET …
   WHERE chat_turn_facts.facts_version < EXCLUDED.facts_version`. A same-version re-run updates
   nothing and reports rowcount 0; a higher version supersedes. The `WHERE` on a `DO UPDATE` is a
   no-op, not an error, when it fails.

The supporting constraint is the **primary key `(tenant_id, block_id)`**, widened from the declared
`["block_id"]` by the tenancy builder. There is no unique index beyond the PK and no version column
other than `facts_version` itself.

Consequence the plan does not state: **at a single `facts_version`, the backfill can create missing
rows but cannot correct wrong ones.** "Available for a one-off reconciliation" therefore means
"fill gaps", not "repair". See open question Q1.

### 1.5 Where the projection function should live on the copilot-mro side

`core` cannot import `copilot_mro` (no dependency edge — stated in the registry module's docstring
and re-stated in the drift pin's). The writer therefore needs its own copy of
`facts_from_block_data`, and that copy becomes the third mirror of one contract.

**Recommended:** put `facts_from_block_data` and the upsert SQL **in the existing registry module**
`postgres_table_definitions_modules/chat_turn_facts.py`, beside `FACTS_VERSION`, `FACTS_COLUMNS` and
`ANSWER_FOUND_VALUES`. Reasons, in order: that module already declares itself the contract's home;
`core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py` **already dynamic-loads exactly
that module**, so widening the pin from constants to behaviour costs no loader change; and the
module's only import is `_build_create_table_sql` from the aggregator, which the app imports at boot
anyway.

**Rejected alternative, and why it must be rejected explicitly:** a new stdlib-only sibling of
`copilot_mro/app/db/chat_history/_tables.py`. It reads better by separation of concerns, but
`copilot_mro/app/db/chat_history/__init__.py` imports `ChatHistoryDB` from `.db`, and
`copilot_mro/app/db/__init__.py` imports the whole document/registry stack. The drift pin stubs
`copilot_mro.app.db` but **not** `copilot_mro.app.db.chat_history`, so importing a module under
`chat_history` from the pin would execute the real package `__init__` and drag in Postgres/Redis —
the exact package-init cost the repo's dynamic-loader convention exists to avoid. If this shape is
chosen anyway, the pin's `_load_registry_module` must gain a `_ensure_package` stub for
`copilot_mro.app.db.chat_history`.

### 1.6 Steps, by file

**copilot-mro tree**
1. `copilot_mro/app/db/postgres_table_definitions_modules/chat_turn_facts.py` — add
   `facts_from_block_data` (a verbatim port of the backfill's, including `_opt_float`,
   `_ROUTE_MAX_CHARS`, `_CITED_DOCUMENTS_CAP` and the three fallback orders) and the parameterised
   upsert statement built from `FACTS_COLUMNS` with `%s::jsonb` on `tool_usage` and
   `cited_documents`. Replace the docstring's "**No writer yet**" paragraph with the writer's
   location.
2. `copilot_mro/app/db/chat_history/blocks.py` — inside `save_block`'s `if cur.rowcount == 1:`
   branch (line 634), on the same cursor, project `block_data` plus the five scalars and execute the
   upsert. The projection input must be the dict **after** the line-569 `session_id` stamp.
3. Failure policy: a facts-write failure must **not** lose the block. Two candidate shapes, and this
   is a decision the implementer must not take silently — see open question Q2.
4. Tests: a pure projection test under `tests/unit/chat_history/` reusing the three block shapes
   `core-obsm/tests/unit/analytics/test_chat_turn_facts_projection.py` already fixes as the
   contract; and a DB-lane test under `tests/db/chat_history/` (beside
   `test_chat_history_roundtrip.py`) that saves a block, reads the facts row back, and asserts it
   equals what the backfill's own `facts_from_block_data` produces from the stored `chat_blocks`
   row. The second test is the only thing that actually proves indistinguishability.
5. Idempotency test: save the same `block_id` twice; assert one block row, one facts row, rowcount 0
   on the second, and `created_at` unchanged.

**core tree**
6. `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py` — add a behavioural limb:
   the copilot-mro `facts_from_block_data` and the backfill's must return equal dicts over the same
   block shapes. Without this the mirror is pinned on names and versions only, which is what the
   phase-5 adversarial review already called a P1 once.
7. `core-obsm/scripts/backfill_chat_turn_facts.py` — the module docstring still says "until the
   block-save path mints those rows inline … this script is the only writer" and still carries the
   **owner crontab block**. The crontab was dropped by the owner on 2026-09-19 (plan G.9). Both must
   be rewritten to "gap-fill reconciliation, scheduled nowhere". Docs-only, no behaviour change.

**docs tree**
8. `/home/aditya/Code/docs/plans/observability-telemetry-merge-and-completion.md` — tick G.5, record
   notes. `docs/plans/observability-rebuild.md` item 11.3 closes with it.

### 1.7 Tree split — how many implementers

Three trees are touched: `copilot-mro-obsm` (steps 1–5), `core-obsm` (6–7), `docs`/`docs-obsm` (8).
Under **one implementer per working tree**, and given that file-disjointness does not make two
implementers safe:

- **`copilot-mro-obsm` is OCCUPIED.** 13 modified files on `obs-merge` @ `d8d2570c` — the G-APP
  slice (`agent_pipeline.py`, `model_call_ledger.py`, `telemetry.py`, `usage_ledger.py`,
  `lang_agent/backend.py`, four `deployment/` files, two runbooks, `_emitted_series.py`). None is a
  G.5 file, which is irrelevant under the rule. **G.5 cannot start there until G-APP hands the tree
  back.**
- `core-obsm` and `docs-obsm` are both clean.

**Recommendation: ONE implementer, sequentially, not two.** The core-side work is one test limb and
one docstring, and it is only meaningful once the copilot-mro projection exists to pin against —
splitting it across two agents buys nothing and costs a handoff. Run it as a single agent that works
`copilot-mro-obsm` first, then `core-obsm`, then docs. The only thing that would force a split is a
decision to move the constants into a new `chat_history` module (§1.5 rejected alternative), which
makes the core loader change a genuine prerequisite rather than a follow-on.

### 1.8 Affected panels — it is three tabs, nine panels, not three panel families of equal weight

The relation is read by **9 of the 46 registered panels**, in three of the seven panel modules.
**Zero Grafana panels read it** — `grep -rl chat_turn_facts` over
`copilot-mro-obsm/deployment/` returns nothing, and the brief's pointer to
`deployment/observability-local/grafana/provisioning/dashboards/flynapse/` is looking in the wrong
place. These are the product's own settings-dashboard panels in `core`.

| Module (tab) | Panel id | Query shape | Dark today? |
|---|---|---|---|
| `quality.py` | `router_intent_distribution` | `COALESCE(query_type,'other')`, count, grouped | fully |
| `quality.py` | `chat_time_duration_histogram` | `latency_ms / 1000.0`, bucketed in Python by `histogram_rows` | fully |
| `quality.py` | `answer_outcomes_over_time` | per-bucket counts filtered on `answer_found`, `avg(confidence)` | fully |
| `quality.py` | `clarification_rate_over_time` | turns + `needs_clarification` from facts, FULL OUTER JOIN to `clarifications_answered` from `product_events` | **partially** — the `product_events` series has data, the facts series does not |
| `quality.py` | `top_unanswered_intents` | `answer_found = 'No'` grouped by `query_type` | fully |
| `quality.py` | `unanswered_questions` | facts LEFT JOIN `chat_blocks` for a 200-char excerpt, LIMIT 50 | fully |
| `quality.py` | `top_cited_documents` | `jsonb_array_elements(cited_documents)`, LIMIT 20 | fully |
| `reliability.py` | `turn_latency_over_time` | `percentile_cont(0.5/0.95)` over `latency_ms/1000` | fully |
| `operations.py` | `tool_usage_mix` | `jsonb_array_elements(tool_usage)`, summed calls/failures, LIMIT 20 | fully |

Not affected, and worth saying so because "three panel families are empty" implies otherwise:
`quality.feedback_received_over_time` and `quality.negative_feedback_drilldown` read `chat_feedback`;
all three other `reliability` panels read `llm_usage` / `llm_model_calls`; six of seven `operations`
panels read `document_hub_documents` / `automation_runs`. The `cost`, `usage`, `improvement` and
`optimizer` tabs are untouched.

**One caveat on "empty".** What is verified is that the merged tree contains **no online writer** —
`blocks.py` holds no `chat_turn_facts` statement, which the master plan also re-verified on
2026-09-20. Whether any given database has rows depends on whether someone ran the backfill by hand;
that was not probed (no live DB query was made). The honest statement is "no writer, so rows exist
only where the backfill was run manually".

### 1.9 Gate M — genuinely unblocked, but not the only gate

**Gate M is declared.** `docs/plans/observability-rebuild.md` §2: *"GATE M DECLARED 2026-09-14 by the
owner — 'langraph migration is done. so we can build and moerge now.'"*, given while ruling phase
10's `/rag/stream` item, at copilot-mro `langgraph-merge` @ `a24189ee`. The §1 conflict-zone freeze
is lifted. The contrary reading came from `plans/observability-rebuild-research/08-post-migration-
rescoping.md`, which arrived on the colleague's branch, was cut before 2026-09-14 and therefore
could not see the declaration; Phase F.3 corrected it in place with a banner. The SDD ledger repeats
the correction at line 757.

**But the same section adds a second gate the merge plan's G.5 line does not mention:** *"Next
decision point: dispatch **Task R** before any writer implementation"*, and `observability-rebuild.md`
item 11.3 reads *"~~After Gate M + Task R~~, **after Task R**, close the Phase 3.7 `chat_turn_facts`
writer"*. Task R is **G.1** of the same Phase G and is **unstarted**. G.5 as written in the merge
plan states only "unblocked by Gate M". Whether the Task R precondition still binds is open question
Q3 — it is the single most likely way to build G.5 in the wrong order.

---

## 2. G.5 — open questions that must be answered before it can be built

**Q1 — What does "available for a one-off reconciliation" mean, given that the version guard makes
same-version repair impossible?** At `facts_version = 1` the backfill's
`WHERE chat_turn_facts.facts_version < EXCLUDED.facts_version` means it can create a missing row and
can never correct a wrong one. So reconciliation after the writer lands is gap-fill only.
*Settled by:* an owner ruling on one of three — (a) accept gap-fill-only, (b) give the backfill a
`--force` that drops the version predicate for a named window, (c) land the writer at
`FACTS_VERSION = 2` so a reconciliation run at 2 can supersede writer rows (and then the drift pin,
the registry module and the backfill all move together). I would expect (a), but it must be said out
loud, because the plan's phrase currently implies repair.

**Q2 — What happens when the facts upsert fails but the block insert succeeded?** They are in one
transaction, so the default is that the whole save rolls back and the turn reports `persisted=False`
— an analytics projection would then be able to lose a user's chat history. The alternative, a
SAVEPOINT around the facts write so a projection failure degrades to a logged warning, breaks the
plan's own "same transaction" wording.
*Settled by:* an owner ruling. The precedent argues for the savepoint: `llm_usage` is deliberately
NOT written from `save_block` (`usage_ledger.py:3` — AD-3, Ruling 5) precisely so ledger concerns
cannot take the turn down. The counter-argument is that the plan says "same transaction" and a
savepoint still is one.

**Q3 — Does the Task R precondition on the writer still bind?** `observability-rebuild.md` 11.3 and
the research-08 correction both say the writer follows Task R; the merge plan's G.5 line cites only
Gate M; Task R is G.1 and unstarted.
*Settled by:* the owner, or by reading R.4's stated content — R.4 is "re-check phases 5 and 7 items
that touch the conflict zone (`chat_turn_facts` writer, content-capture write site, harness hooks)".
That is literally a re-check of this item, which is an argument that R should precede it.

**Q4 — Should deleting a chat delete its facts rows?** `chats.py:342–352` soft-deletes `chats` and
`chat_blocks`; nothing touches `chat_turn_facts`, and the relation has no `deleted` column, so all
nine panels keep counting turns from deleted chats. The backfill has the same behaviour, so this is
inherited, not introduced.
*Settled by:* an owner ruling on whether analytics is expected to honour a user's chat deletion. If
yes, the work is a delete (or a `deleted` column plus nine panel predicates) and belongs in G.5's
scope or a new item; if no, it should be written into the registry module's docstring so the next
reader stops rediscovering it.

**Q5 — Is a dict-projected row byte-identical to a jsonb-round-tripped one?** Expected yes; not
proved. *Settled by:* the DB-lane test in §1.6 step 4 — save a block, then run the backfill's
`facts_from_block_data` over the stored `chat_blocks` row and assert dict equality. This is cheap and
should simply be built rather than asked.

**Q6 — Does `flynapse_app` actually hold INSERT/UPDATE on `chat_turn_facts` in every provisioned
database, and does the tenant RLS policy's `WITH CHECK` admit the writer's row?** `provision_rls.py`
grants `SELECT, INSERT, UPDATE, DELETE ON ALL TABLES` to `APP_ROLE` (`:802`) plus default
privileges (`:806`), and `chat_turn_facts` is **not** in `APPEND_ONLY_RELATIONS` (so UPDATE is not
revoked, which the `DO UPDATE` needs). `save_block` already calls `apply_session_tenancy`. Every
link reads correct, but no INSERT has ever been executed against this relation as `flynapse_app`.
*Settled by:* the DB-lane test of Q5 running as the app role, not as the owner. If the lane's
fixture connects as the owner, the test proves nothing about production.

**Q7 — Which `docs` checkout is authoritative?** `/home/aditya/Code/docs` (`main` @ `12a1783`,
"Phase B2 closed") and `/home/aditya/Code/docs-obsm` (`obs-merge`) hold **different** copies of
`observability-telemetry-merge-and-completion.md`. G.5's plan edits must go to whichever is the live
one or they will be lost.
*Settled by:* the controller stating it. Evidence points at `docs` `main` being ahead.

---

## 3. `core` darkness

### 3.1 Verification results

| Claim in the brief | Verdict | Evidence |
|---|---|---|
| `core-obsm/core/` has zero matches for `opentelemetry`, `get_tracer`, `get_meter` | **TRUE** | `grep -rn 'opentelemetry\|get_tracer\|get_meter' core/ --include=*.py` → 0 |
| No `setup_logging()` call site anywhere in the package | **TRUE, and stronger** — zero in the whole repo, tests included | `grep -rn setup_logging .` over `core-obsm` → 0 |
| Every signal it has is inherited from whichever process mounts it | **TRUE** | `api-obsm/flynapse_api/main.py:8` calls `setup_logging`; `instrument_gateway` at `:352` wraps the whole stack including mounts; `core`'s DB/S3/httpx work runs through `utils`, whose clients are traced and whose instrumentors (`psycopg2`, `httpx`, `requests`, `urllib3`, `redis`, `threading`) are installed by `utils/observability/bootstrap.py` |
| `core/fastapi_app.py` around line 148 is the standalone boot | **FALSE as located.** Line 148 is a comment about authorization middleware. The standalone paths are `lifespan` at **line 100**, the module-level `app = FastAPI(...)` at **116**, and `if __name__ == "__main__": uvicorn.run("fastapi_app:app", …)` at **263–266**. There is also `core-obsm/start_api.sh` |
| Booted standalone, neither loguru sink is installed | **TRUE but over-stated.** The two *configured* sinks (JSON-or-human stdout + OTLP, `utils/observability/log_bridge.py:203`) are absent, so nothing is exported and no line carries a trace id. **loguru's own default stderr handler survives**, because `log_bridge.install`'s `logger.remove()` is what removes it and it never runs. So a standalone `core` prints unstructured human lines to stderr |
| The process is wholly dark | **TRUE for traces and metrics.** `bootstrap()` never runs, so no `TracerProvider`/`MeterProvider` is set and none of the six instrumentors is installed: `utils`' own client spans resolve against the no-op global provider and go nowhere, and `psycopg2`/`httpx` emit nothing at all |
| `core` is the largest application surface in the estate | **PARTLY FALSE.** By HTTP routes it is (marginally) the largest: **86** decorated routes vs `copilot_mro` **85** and `flynapse_api` **12**. By code it is not close: **138** Python files / **30,896** lines vs `copilot_mro`'s **573** / **245,487** — and `copilot_mro` *is* instrumented. Say "the largest route surface", not "the largest application surface" |

### 3.2 Is `core` ever actually served standalone? — RESOLVED: no

Resolved from configuration, not from running the system. Every place a service could be declared
was checked:

- **No Dockerfile.** `find -maxdepth 3 -iname 'Dockerfile*'` over the workspace finds one for `api`
  (×2), `copilot-mro` (×2), `dashboard`, `telegram-bot` and `lambdas/cognito-lambdas`. **None for
  `core`.**
- **No iac service** — but the supporting claim was WRONG and is corrected 2026-09-20. `core` DOES appear in `iac`: `amplify.tf:76` sets `CORE_PREFIX = "/core/v1"`, and `apprunner_iam.tf:86,110` name core's Cognito needs. **None of them declares a service**, so the conclusion stands — but "appears in no `iac/*.tf`" was false, and a reader checking it would have found the opposite.
- **No compose service.** The only `core` strings in any compose file are
  `copilot-mro-obsm/deployment/poc/docker-compose.yml:210` (a comment about the browser-forward
  contract) and `:250` (`CORE_PREFIX=/core/v1`, an env var **for the gateway**).
- **No entry point.** `core-obsm/pyproject.toml` declares no `[tool.poetry.scripts]`; the package
  is published as a **library wheel** (`name = "core"`, `packages = [{include = "core"}]`) by its
  only workflow, `.github/workflows/package.yaml`, which builds and publishes to CodeArtifact and
  runs no service.
- **The one script that claims to boot it is broken.** `core-obsm/start_api.sh` ends in
  `poetry run python fastapi_app.py`, but there is no `fastapi_app.py` at the repo root — it is at
  `core/fastapi_app.py`. Last touched **2026-08-07** (`5e75eaa`), unreferenced by anything else in
  the workspace.
- **Everything that does reference `core.fastapi_app` is a test or a comment.** The one production
  consumer is `api-obsm/flynapse_api/routers/users.py`, which imports `core.fastapi_app.app`,
  registers the Weaviate partition hooks, and re-exports it; `flynapse_api/main.py:424` mounts it at
  `{api_prefix}/core`. `main.py:129` then calls `core.fastapi_app.run_rbac_startup_seed` from the
  gateway's own lifespan, precisely because a mounted sub-app gets none.

**Conclusion: `core` is a library mounted into the gateway. It is served standalone nowhere in this
workspace.** The residual uncertainty is not "undeterminable" — it is bounded to one thing: whether
any human runs `uvicorn core.fastapi_app:app` or `cd core && python fastapi_app.py` by hand while
developing. That would be settled by the `dev-stack` skill's documented commands or by the owner
saying so; nothing in the tree does it.

### 3.3 Three options, costed

**(a) Do nothing, on the grounds that `core` is only ever mounted.**
*Cost:* zero.
*What breaks if the assumption is ever false:* the moment anyone serves `core` directly — a debug
run, an incident bypass, a future split of `core` into its own service, a Lambda handler wrapping
`core.fastapi_app.app` — that process emits no spans, no metrics and no exported logs, and **nothing
says so**. It looks healthy. Worse, it is not a silent *degradation*: `core`'s `lifespan` refuses to
start on an unenforced database (`assert_rls_enforced`) and the RBAC seed runs, so the process
behaves correctly while being invisible. The failure mode is "we ran a production-shaped surface for
a week and have no telemetry for it", discovered only when someone goes looking.
*Also worth noting:* doing nothing leaves `start_api.sh` in the tree as a stale invitation to do
exactly that.

**(b) The minimum honest fix — recommended.**
*File:* `core-obsm/core/fastapi_app.py`.
*Where:* as the **first statement of `lifespan`** (line 100), before `assert_rls_enforced` at 111.
*Call:* `utils.logging_config.setup_logging(<service name>, <environment>, distribution="core")` —
`core` already depends on `flynapse-utils` as a path dependency, so there is no new dependency and
no new package. The `distribution="core"` argument is what gives the resource a code-derived
`service.version` from the wheel's metadata.
*The guard condition:* **`lifespan` itself is the guard.** Its own docstring already states the
discriminator — *"Only reached when `core` is booted standalone: a sub-app mounted under the gateway
gets no lifespan of its own"* — and the estate already relies on that fact in two directions
(`main.py:129` calls `run_rbac_startup_seed` from the gateway *because* core's lifespan will not
fire). No `if` is needed.
*And the brief's stated worry does not apply:* `setup_logging` is documented "Idempotent end to end",
`log_bridge.install` is "Idempotent by module flag" (`log_bridge.py:206–209`), and `bootstrap`
returns `state.configured_by_this_call`. So even if a future FastAPI propagated sub-app lifespans,
the second call would be a no-op, not a double-install. **There is no double-install hazard to guard
against** — that premise in the brief is wrong.
*Cost:* one import, one call, one test (mount `core` under a bare gateway and assert the lifespan did
not fire; boot it standalone and assert the sinks were installed). Minutes.
*What it buys:* a standalone `core` gets JSON stdout, OTLP log export, trace-correlated log records,
the six client instrumentors (so `utils`' Postgres/S3/Weaviate/httpx spans stop being no-ops), and a
`TracerProvider`/`MeterProvider`. It gets **no spans of its own** — that is (c).
*What it does not fix:* the module body logs (`logger.info("Including API routers")` at line 153,
`"All API routers included successfully"`) still emit before `lifespan` runs, through loguru's
default handler. Accepting that is the honest boundary of "minimum"; moving it would require a
separate entry module that calls `setup_logging` before importing the app.
*Adjacent, near-free:* fix or delete `start_api.sh`. Leaving a boot script that cannot work is worse
than having none.

**(c) Instrument `core` properly.**
*Scope, measured rather than guessed:* **86 HTTP routes across 17 resource areas** (`analytics`,
`automations`, `channel_provisioning`, `comments`, `departments`, `document_viewer`, `identity`,
`invitations`, `logging`, `notifications`, `rbac`, `roles`, `tenants`, `user`, `user_departments`,
`user_operators`, `user_roles`), plus `authz`, `db` and `middleware`.

Most of that needs nothing. The boundaries that would actually be **new** signal, in priority order:

1. **The browser OTLP ingest path** — `core/resources/logging/logging_endpoints.py`. This is §4 and
   is the one that matters. 4 routes, a rate limiter, an envelope validator and an outbound forward,
   and today the gateway is explicitly told not to look at it.
2. **`POST /analytics/events`** — `core/resources/analytics/events_endpoints.py`. Already traced as a
   gateway route, but the accepted-vs-deduplicated split (the `ON CONFLICT DO NOTHING` result that
   B1.7 built) is a business outcome no metric carries.
3. **The analytics panel registry** — `core/resources/analytics/panel_service.py` and
   `repository.py`. 46 panels, each an ad-hoc SQL query under a limiter and a cache. A per-panel
   span (`panel_id` as an attribute, bounded at 46) and a cache hit/miss counter are the difference
   between "the settings dashboard is slow" and "`top_cited_documents` is slow for tenant X".
4. **Turnstile siteverify** — `core/resources/user/turnstile.py:54`. An outbound `httpx` call, so it
   already gets a CLIENT span from the instrumentor; what is missing is the *verdict* (pass / fail /
   timeout), which is a signup-funnel fact.
5. **Cognito** — `core/resources/channel_provisioning/services/cognito_identities.py` and the user
   service. boto3, and the **botocore instrumentor is banned by design**
   (`utils/observability/bootstrap.py:32–34`, to avoid double-counting `gen_ai.*`), so these calls
   are untraceable without hand-written spans. This is a real, currently invisible dependency.
6. **The RBAC startup seed** — `run_rbac_startup_seed`, which reconciles every existing tenant at
   boot. One span, one duration, one failure counter.

Everything else — Postgres, S3, Redis, plain HTTP out — is **already covered** by `utils`' traced
clients and the six instrumentors, *provided* (b) has landed so the providers exist. That is the
cost argument for doing (b) first: it converts a large amount of existing-but-inert instrumentation
into live signal for a one-line change.
*Cost:* roughly six focused boundaries, each a span plus one or two explicit instruments registered
through `utils.observability.registry`, plus catalogue rows and a cardinality review for `panel_id`
and `signal`. Well under a day of AI-execution time for an implementer who already has (b), but it
needs Task R's catalogue (G.1 / R.2) to approve the names first, or it will invent a vocabulary the
estate then has to migrate.

**Recommendation: (b) now, as part of G.5's slice or immediately beside it; (c) scoped into Task R
(G.1) and built from R.2's approved catalogue; never (a).**
(b) is a one-line change with an existing, documented guard and no double-install hazard. (c) is real
work whose main risk is naming, and the estate has a live, unstarted task whose entire job is to
approve names. Doing (c) before R is how you get a third outcome vocabulary — the merge already has
two (`operation.outcome` vs `agent.outcome`/`tool.outcome`, plan F.4) and 16 values across 49 call
sites with no declared set.

---

## 4. The ingest-route blind spot

### 4.1 Verification

**The exclusion is real and is where the brief says.**
`api-obsm/flynapse_api/telemetry/http_server.py`, `INGEST_EXCLUDED_URLS` at **line 64** — a single
regex, `/logging/(public/)?ingest/v1/(logs|traces)(\?.*)?$`, regex-*searched* against the full URL,
covering exactly four routes (authenticated + public × logs + traces). It is folded into
`DEFAULT_EXCLUDED_URLS` at line 67 alongside `HEALTH_EXCLUDED_URLS`, and passed at
`flynapse_api/main.py:352` as `instrument_gateway(app, excluded_urls=DEFAULT_EXCLUDED_URLS)`. Inside
`instrument_gateway` the patterns become an `ExcludeList` handed to `_ResponseEndOtelMiddleware`, so
upstream skips **both** the SERVER span **and** `http.server.request.duration` /
`http.server.active_requests` for a matching URL. The stated reason is in the comment at line 61–63:
*"the gateway must not inflate its own spans/metrics with telemetry deliveries (Stream P hand-off)"*.

**The asymmetry is real.** `POST /analytics/events` lives on the analytics router
(`core/resources/analytics/events_endpoints.py:67–68`, mounted at `/analytics/events`) and matches
neither exclusion regex, so it is fully traced and metered. Two browser-facing ingest doors in the
same repo, one observed and one not.

**Two corrections to the brief's framing:**
1. The ingest path is not *entirely* without signal. `httpx` **is** in `INSTRUMENTATIONS`
   (`utils/observability/bootstrap.py:35–42`), so the collector forward in
   `logging_endpoints.py:178–185` still emits a CLIENT span — but with the SERVER span suppressed it
   is a **root span with no parent**, carrying no route, no tenant and no outcome. That is arguably
   worse than nothing: it is orphan noise that also fails to answer the question.
2. Nothing else observes it either. There is **no** `ingest` metric anywhere in `api`, `core` or
   `flynapse-otel`, and no Grafana panel reads one — the two "ingest" panels on `platform-health.json`
   (`Loki ingest`, `Tempo ingest`) are collector-internal and unrelated.

### 4.2 Recommendation: keep the exclusion, add a dedicated instrument

Removing `INGEST_EXCLUDED_URLS` is the wrong answer, and the stated reason is only half of why. The
obvious half is volume: at `MAX_PUBLIC_REQUESTS_PER_MINUTE = 60` per IP and
`MAX_AUTH_REQUESTS_PER_MINUTE = 120` per tenant:user, these four routes can dominate
`http.server.request.duration` and make every other route's percentile unreadable. The half the
comment does not state is worse — a telemetry delivery that produces a SERVER span produces telemetry
about telemetry, and if that span is itself exported through the same collector the browser is
posting to, a collector outage becomes self-amplifying.

**But "do not put it in the gateway's request metrics" is not the same as "do not measure it", and
the exclusion currently means the second.** The right shape is a dedicated, small-cardinality
instrument owned by the handler, registered through `utils.observability.registry`, dimensioned by
`signal` (`logs`|`traces`), `public` (bool) and `outcome`, and a single handler-owned span named for
the ingest operation so the orphan httpx CLIENT span gets a parent. Four dimensions, bounded values,
no route explosion, and it lives on the `core` side where the decisions are actually taken — which
also makes it the first concrete item of §3 option (c).

Two dependencies worth stating: this only works once §3(b) has landed, or a standalone `core`'s
instrument resolves against a no-op meter; and the metric names must come from Task R's catalogue
(R.2), not be invented here.

### 4.3 The failure modes nothing surfaces today

All read from `core-obsm/core/resources/logging/logging_endpoints.py`. Each is a **log line only** —
loguru through the gateway's sinks, uncorrelated (the SERVER span the log record would borrow its
trace id from does not exist), unaggregated, and with no panel or alert reading it.

| Failure mode | Where | What exists today | Why it matters |
|---|---|---|---|
| **Rate limiting** | `_enforce_rate_limit`, `:105–106` → 429 | one `logger.warning("rate limited telemetry ingest", subject=key)` | A client stuck in a retry loop, or a real user losing telemetry, look identical. The `subject` is an IP on the public routes — unaggregated, it is also the only place a flood is visible |
| **Collector 5xx** | `:268–275` → 503 | `logger.error("collector answered a server error", collector_status=…)` | The single most important signal on the path: the collector is down and the browser's telemetry is being dropped. Nothing counts it, nothing alerts on it |
| **Collector network failure / timeout** | `:248–256` → 503 | `logger.error("collector forward failed", error=str(exc))` | Same, and distinct — a timeout is a saturated collector, a connection error is a dead one |
| **Collector 4xx** | `:259–267` → 400 | `logger.warning("collector rejected a telemetry batch")` | A browser shipping malformed OTLP — a **dashboard regression**, visible nowhere near the dashboard |
| **Drop-on-unset** | `:238–239` → 204 | `_warn_endpoint_unset_rate_limited`, deliberately rate-limited to one line | The worst one. `otlp_forward_endpoint` unset means **every browser batch is silently discarded with a 204 success**, and by design the warning is throttled. A misconfigured deploy is indistinguishable from a healthy one from both ends |
| **413 oversize body** | `:231` | nothing at all — a bare `HTTPException` | `MAX_PUBLIC_BODY_BYTES = 64 KiB` / `MAX_AUTH_BODY_BYTES = 256 KiB`. A dashboard release that grows its batch size past the cap loses telemetry with no log, no metric and no trace |
| **413 oversize batch** | `:235` | nothing at all | `MAX_PUBLIC_BATCH = 50` / `MAX_AUTH_BATCH = 200`, counted by `validate_otlp_envelope` |
| **415 wrong content type** | `_require_json_content_type`, `:118–124` | nothing at all | |
| **400 malformed envelope** | `validate_otlp_envelope`, `:138` | nothing at all | |
| **499 client disconnect** | `:277–289` | one `logger.info` | Routine and correctly handled, but its *rate* is a real signal about page-unload flush behaviour |
| **Success volume** | `:257–258` → `{}` | nothing | There is no "batches accepted" count anywhere, so none of the above has a denominator |

The three silent ones — 413, 415, 400 — are the sharpest finding: they raise straight out of
`_pass_through`'s try block with **no log statement at all**, and because the route is excluded there
is no span and no `http.server.request.duration` sample carrying the status code either. A
dashboard release that starts posting batches over the cap is, today, completely undetectable from
the server side.

---

## 5. Everything in this brief that was wrong

1. **"Find them in `copilot-mro-obsm/deployment/observability-local/grafana/provisioning/dashboards/
   flynapse/`."** No Grafana dashboard reads `chat_turn_facts` — zero matches under
   `copilot-mro-obsm/deployment/`. The affected panels are `core`'s Python panel registry
   (`core-obsm/core/resources/analytics/panels/`), rendered by the product's own settings dashboard.
2. **"Three panel families."** Three panel *modules* / tabs is right, but it implies three whole
   families are dark. It is **9 panels out of 46**: 7 of 9 in `quality`, 1 of 4 in `reliability`,
   1 of 7 in `operations`. `clarification_rate_over_time` is only half dark — its
   `clarifications_answered` series comes from `product_events`.
3. **"Where does `chat_turn_facts` live … which repo owns it."** Not one repo. The **DDL and the
   contract constants are copilot-mro's**; the **projection, the only writer and every reader are
   core's**. The split is the whole reason there is a drift pin.
4. **"Unblocked by Gate M"** — true, but incomplete. `observability-rebuild.md` item 11.3 and the
   corrected research-08 both put the writer **after Task R**, which is G.1 and unstarted. G.5's own
   line in the merge plan omits that.
5. **"Idempotent at the backfill's facts version"** — true as stated, but it has an unstated
   consequence: at a single `facts_version` the backfill can only *create* missing rows, never
   *correct* wrong ones. "Available for a one-off reconciliation" therefore cannot mean repair.
6. **"core/fastapi_app.py (reportedly around line 148)."** Line 148 is a comment about authorization
   middleware. The standalone entry points are `lifespan` at **100**, `app = FastAPI(...)` at **116**
   and `if __name__ == "__main__"` at **263**.
7. **"Neither loguru sink is installed and the process is wholly dark."** The two *configured* sinks
   are absent and traces/metrics are genuinely dead — but loguru's **default stderr handler
   survives**, because `log_bridge.install`'s `logger.remove()` is precisely what would have removed
   it. A standalone `core` prints unstructured lines to stderr; it is not silent.
8. **"guarded so that mounting does not double-install sinks."** No guard is needed.
   `setup_logging` is documented idempotent end to end, `log_bridge.install` is idempotent by module
   flag (`log_bridge.py:206–209`), and `bootstrap` reports `configured_by_this_call`. Separately, the
   natural placement (`lifespan`) is *already* the standalone-vs-mounted discriminator, by Starlette's
   own semantics and by this file's own docstring.
9. **"`core` is the largest application surface in the estate."** Largest **route** surface, by one
   route: 86 vs `copilot_mro`'s 85. By code it is 138 files / 30,896 lines against `copilot_mro`'s
   573 / 245,487 — and `copilot_mro` is instrumented.
10. **"The telemetry front door has no signal of its own."** Nearly true, and the exception matters:
    `httpx` is instrumented, so the collector forward still emits a CLIENT span — as an **orphan root
    span** with no route, tenant or outcome. Noise that does not answer the question, rather than
    silence.
11. **"rate limiting, collector 5xx, drop-on-unset and 413/429 are uncorrelated log lines."**
    Understated. 429, collector 4xx/5xx, network failure and drop-on-unset are log lines. **413, 415
    and 400 have no log line at all** — they raise out of `_pass_through` unlogged, and the exclusion
    removes the status-code-bearing span and metric too, so they are entirely invisible.
12. **"The coverage audit listed [standalone `core`] as undeterminable without running the system."**
    It is determinable from configuration and the answer is **no**: no Dockerfile, no `iac` service,
    no compose service, no `[tool.poetry.scripts]`, a library-publishing workflow only, and the one
    script that claims to boot it (`core-obsm/start_api.sh`, last touched 2026-08-07) points at a
    path that does not exist.

### Minor, but worth recording

- `core-obsm/scripts/backfill_chat_turn_facts.py:52` computes `REPO_ROOT = Path(__file__).resolve().
  parents[1]` — a **depth-coupled path**, the pattern `tests/unit/infra/test_no_depth_coupled_paths.py`
  exists to forbid. It is a script rather than a test, so the guard does not sweep it. Cheap to fix
  while the file is open for its docstring rewrite.
- The same file still carries the **owner crontab block** the owner dropped on 2026-09-19, and still
  claims to be "the only writer" "until task 3.7 lands".
- `chat_turn_facts.py`'s docstring says the relation "is listed in `PRIVATE_RELATIONS`", which reads
  as a production registry. It is a **test** constant, at
  `copilot-mro-obsm/tests/registries/tables/test_postgres_table_definitions.py:790`.
