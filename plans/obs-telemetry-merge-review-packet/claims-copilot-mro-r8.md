# Claims packet — copilot-mro review r8 (`62c7413d..735f8213`, 27 commits)

Independent adversarial review, Opus, 2026-09-22 (paused 01:58–02:10 by owner request, resumed). **Verdict:
FIX-FIRST** — **0 P0 · 1 P1 · 5 P2 · 10 P3.** P1-1 was **measured** on `copilot_mro_test`.

Read-only on every code tree: nothing edited, committed, checked out or stashed in `copilot-mro-obsm` (which moved
to `557a178f` during the review — out of range, not read) or any sibling; nothing pushed; no docker, AWS, Cognito,
Bedrock, Weaviate or Redis call (a netguard refused and logged every attempt). Every mutation ran in a scratch clone
through `/home/aditya/Code/mutant.sh` (cold bytecode, baseline-checked, restore md5-verified; `git status` of the
clone shows only the two untracked probe directories after every round). The one committed plant was made in a
second, disposable clone. DB-writing runs against `copilot_mro_test`: two, both serial (the `tests/db` census and the
rest-of-suite run, whose `tests/api` writes); the P1-1 probe file ran three times on `pg_temp` shadow tables and a
pre-C12 INSERT that fails, so it wrote no real row; no DDL, and the settle columns were NOT added to the test
database. Read-only touches: one `information_schema` query at the start, and the P3-9 unit test in the pair runs.

| repo | worktree | branch | range | siblings on `PYTHONPATH` (live trees, the brief's recipe) |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `62c7413d..735f8213` — HEAD `735f82131006bc43547ffe15bc7a5967764389be` | live trees, which moved under the review: utils-obsm `179cc6d` → `0ce3fa8`, core-obsm `fe41002` → `c6a81e9` → `b730a95` → `16cd1ae`, api-obsm `e3ba207` → `02c9710` → `2d49c3f` → `fbd394c`, flynapse-otel `0960c16` → `df503c2` → `d85afaa`. No red in any lane traces to a sibling (every red is classified below); archives of the SHAs at resume are in `scratchpad/mro-review-r8/wsp/SIBLINGS.txt` |

**Lane recipe, as run:** `/home/aditya/Code/pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest
-o addopts="-ra --strict-markers" -p no:cacheprovider` from the copy's root, `ENV_FILE=/home/aditya/Code/api/.env
DEBUG=false POSTGRES_DB=copilot_mro_test`, `PYTHONPATH=<netguard>:<copy>:core-obsm:utils-obsm:api-obsm:flynapse-otel`.
The copy is a `git clone --shared` of `735f8213` (byte-identical to its `git archive`; the git-reading guards need a
clone) placed in a scratch workspace beside archives of utils-obsm, core-obsm, api-obsm, flynapse-otel,
dashboard-obsm and shift-optimizer (so sibling-anchored tests resolve). `rootdir` = the copy in every run;
`copilot_mro.__path__ == [<copy>/copilot_mro]` (namespace package, one entry), `copilot_mro.app.__file__` = the copy.
The netguard `sitecustomize` strips the api venv's primary-checkout `.pth` entries, refuses and logs every
non-loopback connect / DNS lookup and every loopback port but 5432, and wraps `psycopg2.connect` (libpq's own sockets
are invisible to a Python socket patch) to record host/port/database. The unit and agent_sdk lanes ran inside
`unshare -rn` (loopback only, so no Postgres either). `-n 2` on those two lanes, `-n 0` everywhere else.

---

## Findings, ranked

### No P0

No tool result, log, span or stdout sink carries a planted exception message on any path this range fixed or
seated: a sentinel planted in the SAD seat's handler and in `docx_write`'s registration failure reaches no tool
result, no stdlib record, no span and no shipped loguru sink (the only rendering is `docx_write`'s
`logger.exception`, already registered M-TRACEBACK debt ×3, printed in pytest by loguru's stock handler, which utils
deliberately does not replace under pytest — `_loguru_default.py:36`).

### P1-1 — a turn that settles after its chat was deleted lands a PERSONAL `chat_turn_facts` row that nothing ever anonymises (Severity 0 · tier 2 · F1) — MEASURED

M-FACTS-FAILURES' settle-time writer and M-FACTS-ANONYMISE's delete do not compose.
`agent_shared/turn_facts.py:101` runs `SETTLED_FACTS_UPSERT_SQL` (`chat_turn_facts.py:651-657`), a plain upsert with
no chat-liveness predicate and no lock. The save-time writer is protected by `save_block`'s
`_LOCK_CHAT_FOR_SAVE_SQL … deleted = false FOR UPDATE` (`blocks.py:39-44`); the settle writer is not. `delete_chat`
anonymises by `chat_id` once (`chats.py:371`), in its own transaction.

**Scenario:** the user deletes a chat — sidebar, another tab, another device — while a 30–120 s turn is in flight,
or an automation's chat is deleted mid-run. The delete commits: `ANONYMISE_CHAT_FACTS_SQL` matches 0 rows. The turn
settles: the placeholder row lands with `user_id`, `session_id`, `chat_id`, `department`. The block save that
follows is refused by the liveness lock, so the row stays at `facts_version = 0`, personal, permanently, in a
relation nine panels read. **Measured** (`tests/db/r8probe/test_r8_anonymise_race_probe.py`, the module's own SQL
constants on `pg_temp` shadow tables of `chat_turn_facts`/`chats` in `copilot_mro_test`): delete-first → the row
keeps `user-SENTINEL-R8` / `sess-SENTINEL-R8` / the chat id / `MRO`, and `_LOCK_CHAT_FOR_SAVE_SQL` returns no row
for the deleted chat; the control (settle, then delete) is anonymised. 3 passed. The module docstring's "a facts row
with no block is impossible by construction" (`chat_turn_facts.py:60`) has been false since `d4792d6b`: every settle
row precedes its block.

**Fix:** give the settle write the same liveness gate — `INSERT … SELECT … WHERE EXISTS (SELECT 1 FROM chats WHERE …
AND deleted = false)`, so a deleted chat's turn writes nothing (or writes the anonymised shape directly). A test:
the race above against the real relation once C12 adds the columns.

### P2-1 — the "re-seed must come with a changed detector" rule (ee37c6e3) is vacuous at HEAD, for both registers (Severity 1 · tier 1 · F1) — MEASURED

`_register_ratchet.unbound_reseeds` (`tests/_register_ratchet.py:152`) compares a working-tree re-seed against the
guard **as of the register's last commit**, not against HEAD's guard. Both registers were last committed before their
guards last changed (tool-error register `a23cc07e`, guard changed at `5ac2ab1c`/`f2984cd8`/`ee37c6e3`; M-TRACEBACK
register `6aef26e3`, guard changed at `f2984cd8`/`ee37c6e3`), so any working-tree re-seed today "comes with a new
detector". **Plant** (disposable clone `rs/`): restore the `docx_write` registration leak (debt 1 → 2), set the
`SEEDED` and `DEBT` lines to 2, update `SEEDED_SHA256`, detector untouched → `test_tool_results_carry_no_exception_text.py`
**37 passed** in the working tree, and **37 passed committed** (`0597e5a5`: the committed pair compares the guard at
the new commit with the guard at `a23cc07e`). **Control:** commit a register touch first (so the register's last
commit postdates the guard), then the same re-seed → `test_a_reseed_comes_with_a_new_detector` **red**. Then add one
dead constant (`_R8_NO_OP = 0`) to the guard → **37 passed**: `detector_digest` counts any AST change as a new
detector. Because count regrowth is seed-scoped, a re-seed resets the debt ceiling — the lock the M-TRACEBACK fan-out
depends on. **Fix:** compare against HEAD's committed guard (and the working guard against HEAD's), and bind a re-seed
to evidence it needed one — e.g. require every newly seeded key to be a site the OLD detector does not find and the
new one does (run both `detect()` versions over the tree).

### P2-2 — the SAD tools' result channel is invisible to the tool-result detector (Severity 1 · tier 1 · F1) — MUTATION-PROVED (survivor)

`36aa4254` added `services/data_discovery/agent` to the detector's `ROOTS` "to hold any result they build from caught
text". The SAD tools build their results with `sad_runner.tool_text_result(...)` (`sad_runner.py:137`) — an imported
plain-dict builder, neither a `CONSTRUCTOR` nor a module-local builder — so no SAD result is ever a site. **SV3:**
`except Exception as exc: return _tool_text_result({"status": "audit_failed", "error": str(exc)})` in
`provider.py`'s report-failure tool **SURVIVED** the full `tests/unit/agent_shared` lane + the M-TRACEBACK guard
(1400 passed). The other SAD channel is held, by the OTHER guard: SV2 (`raise ToolRefusal(f"… {exc}")`) passes both
tool guards but is **killed** by `test_no_module_logs_an_exceptions_text` (a raise sink). No live instance (every
live `ToolRefusal` and `tool_text_result` payload read). **Fix:** sanction `tool_text_result` as a result builder
(a cross-module builder map, or treat a call to it as a result construction).

### P2-3 — the structural seat guard sees a registration only by name and positional arity (Severity 1 · tier 1 · F1) — MUTATION-PROVED (survivor)

`test_sdk_tool_handlers_are_seated.py:30-37`: a registration is `tool(...)`/`X.tool(...)` with ≥ 2 positional args.
Plants (`probes/seat_plants8.py`): `@tool(name=…, description=…, input_schema=…)`, `from claude_agent_sdk import tool
as sdk_tool`, a direct `SdkMcpTool(handler=raw)` and `partial(tool, …)(raw)` are all **invisible** (0 registrations
counted). **SV1b** — a NEW keyword-registered, unseated tool in `provider.py` raising `RuntimeError` — **SURVIVED** the
full lane (1400 passed); its message would reach the model verbatim through MCP's `_make_error_result(str(e))`.
Converting an EXISTING tool to keyword form (SV1) is killed only by the `registrations >= 14` floor (`:98`). **Fix:**
resolve `tool` by import (`_module_paths`), count keyword arguments, treat `SdkMcpTool(` as a registration — or,
better, seat at the server: wrap every handler where `create_sdk_mcp_server` is called.

### P2-4 — the first-event branch still fires after a single exporter stalls for more than the lookback hour (Severity 2 · tier 1 · F1) — MEASURED with the shipped simulator

`7130d4d0`'s gate is fleet-wide `count(last_over_time(target_info[1h] offset W)) > 0`; its three cases stop at a
20-minute single-process stall. With the test file's own `new_branch` (`probes/gap_probe.py`): one process's exporter
stalled while another keeps delivering (a host's collector agent down, one SDK exporter wedged) — 61 min → 3 firing
evaluations on resume; **70 min → 12 consecutive evaluations** on every W = 15m rule (`for: 5m` met); 90 min → 32 on
`DocumentHubProcessingStuck` / `UnpricedModelCalls` (W = 1h, `for: 30m` met); ≥ 120 min → the whole W. The rule
header's "a stalled process is covered by the hour" is exactly that boundary. M6 (`[1h]` → `[1m]`) is killed, so the
shipped cases do bite. **Fix:** gate per instance before the `count by`: `(x unless last_over_time(x[1h] offset W))
and on(instance) last_over_time(target_info[1h] offset W)`, and add a > 1 h single-instance case.

### P2-5 — the delete anonymises one copy of the typed feedback comment; the others, and feedback filed after the delete, survive (Severity 2 · tier 2 · F1) — REASONED from code, not run

`de2665b3` states its aim as removing "the comment the user TYPED" and its giver. But `POST /response/feedback`
(`api/user_feedback.py:216-300`) also runs `propagate_feedback_to_traces`, which writes the comment and the giver into
`memory_events` (`record_memory_event(actor_user_id=user_id, metadata={"block_id", "comment"})`,
`feedback_propagator.py:76-82`) and, on `thumbs_down`, into the trace payload (`:73`); and the improvement collector
excerpts it into findings (`collect_explicit.py:357`). `delete_chat` touches none of them. Separately,
`save_response_feedback` (`chat_history/feedback.py:16`) checks no block or chat liveness, so feedback filed after the
delete (a stale tab) lands giver + comment + session un-anonymised — the P1-1 race in the feedback half. **Fix:**
refuse feedback on a deleted block; decide (owner) whether M-FACTS-ANONYMISE covers the memory and improvement copies.

> **UPDATE (SDD Addenda 253/255/256/263).** The gate half was built in the r8 fix batch, but its cross-session claim
> was **REFUTED by measurement**: the outer `WHERE block.deleted` predicate was pushed into the `FOR SHARE` sub-select,
> so a LIVE block — the entire race case — was never locked; a feedback racing an uncommitted delete landed ungated.
> **FIXED at `0e32212c`** (top-level-lock shape; two-session pair red at `8b1bfaee`, green after; revert-mutants killed
> against each test). The copies half is now OWNER-RULED (scrub every copy carrying user text; numeric spend rows stay)
> and the full surviving-copy census is measured in Addendum 263 — the extension lane builds it.
>
> **UPDATE (Add. 274, 2026-09-23).** The copies half is BUILT: copilot-mro `34bab392` (+`9a68ef23` spend-ledger test, `9debf188` scope-guard approvals) scrubs the ruled copies inside `delete_chat`'s transaction via `deleted_chat_copies.DELETED_CHAT_COPIES` (line-as-data, unit-pinned), with `0e32212c`-shape gates on the two race windows and full-operator-roster binding for memory scrubs (db-proved cross-operator). core `170e2ab` extends C15 the same way (pg_temp proofs only). Residuals for the prepush review: `memory_items.user_id` KEPT on retained notes (judgement call — confirm), distiller/still-running-turn windows outside the two gates (record-only).

### P3s

1. **P3-1 (sev 1, tier 1) Undeclared tool-detector misses.** A dict bound BEFORE a handler, filled inside it and
   returned after (**SV4 survived the full lane**); `out.setdefault(k, []).append(str(exc))` (a Call receiver);
   `isinstance(r, X)` narrowing only when `X` ends in `Error`/`Exception`. Caught, for the record: 18 other shapes
   (`exc.args[0][:80]`, `TPL.format(error=exc)`, `__cause__`, `__notes__`, `except*`, walrus, ternary, `**kw` after the
   scope, `+=` after the scope, an inner `def`, `enumerate` + `isinstance`, `BaseException`).
2. **P3-2 (sev 2, tier 1) `turn_error_type` trusts any `.code`** (`turn_facts.py:41-52`): 16 exception shapes probed —
   13 give a class or a numeric code; a text-valued `.code` (`SystemExit(str)`, `openai.APIError`'s body `code`, any
   custom object) is stored verbatim. No live class does it. Shape-gate the code as `aws_error_code` does.
3. **P3-3 (sev 2, tier 1) The admin door still hands out data-capable handles** (`weaviate_tenancy.py:588, 617-639`):
   `collections.create(…)`'s handle is wrapped with `admin=False` (`.query` allowed — fake-client probe);
   `handle.with_consistency_level(…)` returns the raw collection; `door._target` is raw. The direct spellings are
   refused (M11 killed). `llama_index_initialization.py:367` calls `collections.create` through the door today.
4. **P3-4 (sev 3, tier 1) Before C12, every settled turn logs an ERROR, not only a WARNING.** Measured:
   `utils.postgres_service` "Postgres execute failed" (ERROR, `sqlstate=UndefinedColumn`, the SQL with placeholders)
   then the writer's WARNING; `FAILED` returned, nothing raised, pool clean, 0 rows, no user/session/secret in either
   record. Until the owner runs C12, M-FACTS-FAILURES records nothing and adds one ERROR line per turn.
5. **P3-5 (sev 2, tier 1) The conformance gate cannot see a missing nullable declared column.** `copilot_mro_test`
   lacks `chat_turn_facts.turn_outcome` / `turn_error_type`; `test_the_live_database_conforms` lists 4 other
   violations and not these — `declared_column_types_match_live` skips an absent column (`test_schema_conformance.py:1248`)
   and defers to two properties that only cover NOT NULL columns and whole relations. The settle DB tests skip instead.
6. **P3-6 (sev 1, tier 1) The memory-gc tripwire's per-test half guards a path the lane never runs** (b141776e).
   M15 (the lazy import spelled `from . import memory_index`) **survived** alone and after the lifecycle file: no test
   executes `_index_delete` (every sweep injects `delete_doc`, patches `_index_delete`, or reclaims nothing). Only
   the load-time half is live.
7. **P3-7 (sev 2, tier 2) The subagent vocabulary pin (6145d42a) still passes over four spellings** its message says
   are "refused, never passed over": `a = agents; a["x"] = …`, a helper that mutates `agents`, a walrus rebinding on
   the Claude side; an alias `.append`, a mutating helper and a slice assignment on the lang side
   (`probes/vocab_plants8.py`). A missed registration records as `other`.
8. **P3-8 (sev 2, tier 1) The static histogram-tenant check (af0d132e) misses a key added by subscript.** M9
   (`labels["tenant_id"] = job.tenant_id` before the histogram call) **survived** the full `document_hub` +
   `observability` lanes (1026 passed); M9b (the key in the literal) is killed. The runtime drop still strips it.
9. **P3-9 (sev 2, tier 1) A unit test depends on a live Postgres, and its seam patch is inert.**
   `tests/unit/agent_claude/test_workout_tool_adapters.py:397` swaps `rwm._default_executor` AFTER the binding captured
   `executor = execute_select or _default_executor` (`resolve_workout.py:925`), so it opens the real pool: green only
   with Postgres up (netguard: `pg-connect localhost:5432/copilot_mro_test`), red in the netns — where the failing tool
   result carried the driver's `connection to server at "localhost"…` text (the registered `_resolve_workout` debt
   site). Pre-range (`a988bc92`); not in the implementer's census because it ran with a database.

10. **P3-10 (sev 2, tier 1) One `tests/api` test reaches AWS Cognito.** `tests/api/tenancy/test_operator_grain_isolation.py::test_the_gate_actually_runs_against_this_database`
    looked up `cognito-idp.ap-south-1.amazonaws.com:443` (refused by the netguard; the test passed regardless). Not in
    the audit's live-services table and outside every guard this range added. Pre-range file.

Folded residuals (no live instance, recorded so the next round does not rediscover them): the `diagnose=False` sink
guard misses `log = logger; log.add(…)` and `logger.configure(**config)`; the embedding-panel pin's regex misses a
grouped difference `sum by (m) (increase(a)) - sum by (m) (increase(b))`; the retired-legacy rule misses a door
reached through `getattr` (declared; M7c survived).

---

## Census

The implementer's mapping (`scratchpad/mro-impl/census/census_mapping.tsv`) no longer exists (the session scratchpad
was emptied at the restart), so the "12 red at HEAD" claim was re-derived from the commit messages: test_config ×3,
schema_conformance ×3, FTD sidecar ×1, 5 clone-only.

| lane | at `62c7413d` | at HEAD `735f8213` | reds at HEAD, and what they are | unmapped |
|---|---|---|---|---|
| `tests/unit` (`-n 2`, netns) | not run (control pair only, below) | **6663 passed, 6 failed, 6 errors, 24 skipped** (10:24) | 6 E = 3 files × 2 workers, `RootAnchorError` for `core`/`dashboard` in a bare scratch clone — **pass in the sibling layout (130 passed)**; 5 F = the workspace-shape infra tests (`test_cross_repo_reads_name_their_checkout` ×4, `test_root_anchoring` ×1) = the mapped "5 clone-only"; 1 F = P3-9 (DB dependency; netns) | P3-9 (harness-dependent) |
| `tests/agent_sdk` (`-n 2`, netns) | — | **4165 passed, 40 skipped, 0 failed** (2:36) | none; 37 of the skips are the 5 unmarked live-Postgres files (audit item 9) refused by the netns | — |
| `tests/db` (serial) | — | **680 passed, 3 failed, 21 skipped, 1 xfailed** (4:48) | schema_conformance ×3 (`data_discovery_jobs.*_count` nullable; `llm_turn_content` absent) = mapped test-DB drift | — |
| everything else (18 dirs, one serial process) | — | **2660 passed, 7 failed, 70 skipped** (3:52) | test_config ×3 and the FTD sidecar ×1 = mapped; 3 = scratch-layout harness: `test_cache_key_families` and `test_cross_store_isolation` read the PRIMARY `api`/`core` checkouts by name (absent beside my clone; present in the real workspace), `test_agent_shared_pilot_contract_checkpoint` runs `git show <api sha>` in the api sibling (an archive here; the commit exists in both real api checkouts) | none real |
| order pairs (16 runs, one process each) | DataView pair: **4 failed / 18 passed** | **all green in both orders** | — | — |

**Network, every lane at HEAD:** unit — 1 refused DNS (`no-such-host.invalid`, `test_data_discovery_safety`, audit
item 8), 2 refused `127.0.0.1:8080` (Weaviate, `test_pilot_scenarios::test_recall_arc_…`, audit item 8), 1 Postgres
(P3-9); agent_sdk — 5 Postgres attempts (item 9's files), nothing else; db — Postgres only (`copilot_mro_test`, two
throwaway conformance databases, `postgres`, and one deliberate read of the dev `copilot_mro` by
`test_corpus_read_door.py`); rest — 8 refused `127.0.0.1:8080` at COLLECTION (module-level Weaviate availability probes in 8 `tests/integration` files, skip gates by design) and **1 refused DNS lookup of `cognito-idp.ap-south-1.amazonaws.com`** from `tests/api/tenancy/test_operator_grain_isolation.py::test_the_gate_actually_runs_against_this_database` (P3-10). **No IMDS, SSO, Bedrock, S3, Redis or OTLP attempt in any lane**, and no AWS attempt at all in the unit and
agent_sdk lanes — the 614b95ee session pins and suite-wide guards hold; the one AWS reach (Cognito, P3-10) is in
`tests/api`, which those guards do not claim.

---

## What I tried to break and could not

- **Every guard this range added bit its mutant:** M1/M2 (`docx_write` warnings back to `{exc}`) and M3
  (`build_workout` package-resolve) killed by their behavioural pins, M1b also by the static sweep; M8 (the seat
  relays `str(exc)`) and M12 (a SAD tool unseated) killed; M6 (`[1h]` → `[1m]` on one rule) killed by the gap
  simulator; M7 (a retired family via a module constant) and M7b (an f-string name) killed; M9b killed; M10 (the
  collection name back in the exception's args) and M11 (`admin=True` dropped) killed; M4 (the feedback anonymise
  dropped) killed by the unit transaction fake; M13 (`turn_error_type = str(error)`) and M14 (a settle rewrites a
  settle) killed. Results: `~/.claude/scratch/obs-merge/mro-review-r8/logs/mutants.txt`.
- **The seat end to end.** A sentinel raised inside a seated SAD handler, through the SDK's own in-process MCP
  server: the tool result carries `RuntimeError` only; the seat's stdlib record carries type and frame headers; no
  span opens; nothing on stdout/stderr (`probes/test_r8_sink_follow_probe.py`).
- **The settle writer's idempotency and category.** `ON CONFLICT … WHERE turn_outcome IS NULL` — a second settle
  rewrites nothing (M14 killed); the block projection never names the two columns; `StructuredError.code` is a literal
  token at all 20 construction sites; the pipeline's two settle calls pass the `RuntimeOutcome` or the exception, never
  a string. Pre-C12 the writer never raises (measured).
- **The order-dependence fixes.** All 16 pair runs green in both orders (excel ↔ data planning 22/22, lifecycle ↔ gc
  31/31, synthesis ↔ the five victims 369/369, writers ↔ tenancy 47/47, propagator ↔ lifecycle 16/16,
  `tests/unit/db` + `document_hub` ↔ the pilot runtime 897/897, cards ↔ workout 41/41, referred-by ↔ data planning
  27/27); the DataView pair reproduces at `62c7413d` (4 failed). The `copilot_mro.app.db` stub removal: the DB lane
  ran `chat_history` before `improvement` with no errors.
- **The three commit-claimed session pins** (EC2 metadata off, OTel off, in-memory cache) and the Bedrock/S3 lift:
  zero IMDS, OTLP, Redis, SSO, S3 or Bedrock attempts in the unit and agent_sdk lanes inside a network namespace.
- **The feedback anonymise SQL** removes exactly the identifying payload keys the writer stores (`user_id`, `comment`,
  `session_id`); a NULL payload stays NULL; the DB pin passed in the census.
- **The embedding panel's term B** is correct: `embedding_requests_total` is always `status="success"`
  (`utils/llm.py:1261`) and the cost histogram is recorded only when priced.
- **The re-seed limb when its premise holds** (register committed after the guard): red, as designed.

## What I did not test

- A live Prometheus: P2-4 uses the shipped simulator's selection semantics, not a scrape.
- P2-5 is reasoned from code (no memory-trace or improvement run).
- `tests/unit` at `62c7413d` as a whole lane (only the DataView control pair), and the census at `62c7413d`.
- The scope guard's function-granular rule (`b1ade15d`) beyond reading (one edge noticed, not planted: a pure-deletion
  hunk is attributed to the line before it, so a deletion just below a repaired function reads as inside it).
- The raw-handle sweep additions (`7839f0b2`) beyond reading; `repo_modules_restored`'s effect on a module first
  imported inside the block by a module that existed before it (a possible class fork, not measured).
- The out-of-range cli merge (`b5cf1524`, in the real tree's `557a178f`).

---

## Claims table

Severity: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process.
Tier (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or
estate-shaping. Chunk: F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R8-01 | copilot-mro | `turn_facts.py:101`; `chat_turn_facts.py:651-657`; `blocks.py:39-44`; `chats.py:371` | Settle-time facts row = plain upsert, no liveness gate | M-FACTS-FAILURES | DB probe (pg_temp): delete-first leaves user/session/chat/department; lock refuses the block; control anonymised | none | yes — r8 probe (defect measured) | 0 | 2 | F1 | REFUTED (P1-1) |
| R8-02 | copilot-mro | `chat_turn_facts.py:690-720`; `chats.py:371-377` | Delete anonymises facts + feedback in one transaction | M-FACTS-ANONYMISE | DB pins passed in the census; M4 killed (unit fake); M5 (keep session) survives the unit lane, asserted only by the DB pin | `test_a_deleted_chats_rows_…`, `test_a_deleted_chats_feedback_…` | yes — r8 (M4) | 0 | 0 | F1 | SETTLED (for the rows that exist at delete time) |
| R8-03 | copilot-mro | `api/user_feedback.py:216-300`; `feedback_propagator.py:73-82`; `collect_explicit.py:357`; `feedback.py:16` | Anonymise `chat_feedback` only | de2665b3 "the comment the user TYPED" | Read: comment + giver copied to memory events/payloads and improvement excerpts; feedback after delete not gated | none | no | 2 | 2 | F1 | GATE HALF FIXED `0e32212c` (its first cross-session shape REFUTED by measurement first — Add. 253/255); copies half OWNER-RULED, census in Add. 263, extension lane building |
| R8-04 | copilot-mro | `turn_facts.py:41-52` | `turn_error_type` = `.error.code` → `.code` → class | "never a message" | 16-shape probe: text-valued `.code` stored; M13 killed | `test_a_failed_turn_carries_a_category_never_a_message` | yes — r8 (M13) | 2 | 1 | F1 | PARTIAL (P3-2) |
| R8-05 | copilot-mro | `turn_facts.py:97-113`; utils `postgres_service.py:428-431` | Pre-C12: warn + swallow | brief | Measured: ERROR + WARNING, FAILED, no raise, pool clean, 0 rows | none | yes — r8 probe (measured) | 3 | 1 | F1 | PARTIAL (P3-4) |
| R8-06 | copilot-mro | `chat_turn_facts.py:651-657` | Settle upsert idempotent, one row per turn | M-FACTS-FAILURES | M14 killed; unit pins on the SQL | `test_the_block_projection_supersedes_…` | yes — r8 (M14) | 1 | 0 | F1 | SETTLED |
| R8-07 | copilot-mro | `tests/db/tenancy/test_schema_conformance.py:1248` | Missing declared columns left to other properties | conformance design | Live DB lacks the two settle columns; gate silent | `test_the_live_database_conforms` | no | 2 | 1 | F1 | OPEN (P3-5) |
| R8-08 | copilot-mro | `tools/_shared/tool_failures.py:76-105` | Seat: non-`ToolRefusal` → `"<what> failed (<Class>)"` | M-TOOL-ERRORS (36aa4254) | M8 killed; sink-follow probe: no sink carries the sentinel | `test_a_sad_tools_infrastructure_failure_…` | yes — r8 (M8) | 0 | 0 | F1 | SETTLED |
| R8-09 | copilot-mro | `test_sdk_tool_handlers_are_seated.py:30-37,98` | Structural rule over every `tool(...)` registration | r7 P1-1 | Keyword/alias/`SdkMcpTool`/`partial` invisible; SV1b survived full lane; SV1 killed by the floor only; M12 killed | that file | yes — r8 (SV1b survived) | 1 | 1 | F1 | REFUTED (P2-3) |
| R8-10 | copilot-mro | `test_tool_results_carry_no_exception_text.py:56-61`; `sad_runner.py:137` | SAD root holds results built from caught text | r7 P1-1 | SV3 survived full lane; SV2 killed by M-TRACEBACK | tool guard | yes — r8 (SV3 survived) | 1 | 1 | F1 | REFUTED (P2-2) |
| R8-11 | copilot-mro | same detector | Declared-miss list complete (5ac2ab1c) | r7 P2-5 | SV4 survived full lane; `setdefault` chain and suffix rule missed; 18 shapes caught | `test_the_detector_flags` | yes — r8 (SV4) | 1 | 1 | F1 | PARTIAL (P3-1) |
| R8-12 | copilot-mro | `docx_write.py:827,862`; `build_workout.py:1244` | Three live leaks → `failure_text` | M-TOOL-ERRORS | M1, M1b, M2, M3 killed; sink-follow: tool result clean | `test_docx_write_tool.py` ×2; `test_build_workout_bundle.py` | yes — r8 | 0 | 0 | F1 | SETTLED |
| R8-13 | copilot-mro | `tests/_register_ratchet.py:106-160` | Re-seed must come with a changed detector | r7 P3-14 | Re-seed plant passes (working tree + committed); control red; dead constant re-binds | `test_a_reseed_comes_with_a_new_detector` (both guards) | yes — r8 plant (survived) | 1 | 1 | F1 | REFUTED (P2-1) |
| R8-14 | copilot-mro | `_register_ratchet.py` REPAIRED carry | REPAIRED carried across seeds | r7 P3-14 | Read; plant kept REPAIRED intact (37 passed) | `test_repaired_is_exactly_what_the_seed_lost` | no | 1 | 1 | F1 | ASSERTED |
| R8-15 | copilot-mro | `flynapse-pipeline-alerts.yml`, `flynapse-agent-alerts.yml` (10 branches) | Hour lookback + fleet `target_info` gate | r7 P3-1 | Shipped 3 cases hold; single-exporter stall ≥ 61 min fires; M6 killed | `test_first_event_branch_gap.py` | yes — r8 (M6) | 2 | 1 | F1 | PARTIAL (P2-4) |
| R8-16 | copilot-mro | `weaviate_tenancy.py:504-520, 588, 617-639, 800-816` | Admin door refuses data surfaces | r7 P3-3 | M11 killed; `collections.create` handle / `with_consistency_level` / `_target` pass | `test_the_admin_door_refuses_…` | yes — r8 (M11) | 2 | 1 | F1 | PARTIAL (P3-3) |
| R8-17 | copilot-mro | `weaviate_tenancy.py:203-217` | Collection name as attribute | r7 P3-11 | M10 killed | `test_weaviate_doors_are_traced.py` | yes — r8 (M10) | 3 | 0 | F1 | SETTLED |
| R8-18 | copilot-mro | `test_retired_legacy_metrics_stay_deleted.py:154-205` | Doors name a family by literal / constant | r7 P3-2 | M7, M7b killed; M7c (`getattr`) survived — declared | that file | yes — r8 | 2 | 0 | F1 | SETTLED (declared hole remains) |
| R8-19 | copilot-mro | `test_no_exception_text_in_logs.py`; `tests/_module_paths.py` | Describer homes by full path; exc slot only | r7 P2-6 | Read; SV2 shows the raise sink live | `test_a_describer_home_is_matched_…` | partly — SV2 killed by the sweep | 1 | 1 | F1 | ASSERTED |
| R8-20 | copilot-mro | `document_hub/operations.py:86-94`; `test_document_hub_operation_telemetry.py:361-403` | Histogram tenant: drop at runtime, refuse statically | r7 P3-8 | M9b killed; M9 (subscript) survived full lanes | that test | yes — r8 (M9 survived) | 2 | 1 | F1 | PARTIAL (P3-8) |
| R8-21 | copilot-mro | `test_genai_metric_labels.py` (6145d42a) | Every write into agents / subagent_specs read or refused | r7 P3-7 | 6 spellings pass unread | that file | yes — r8 plants | 2 | 2 | F1 | PARTIAL (P3-7) |
| R8-22 | copilot-mro | `test_loguru_safe_default_reaches_workers_and_images.py:70-116` | Aliases + `configure(handlers=)` | r7 P3-9 | `log = logger` rebinding, `configure(**cfg)` missed; no live instance | that file | no | 2 | 1 | F1 | PARTIAL (folded) |
| R8-23 | copilot-mro | `llm-agents.json` term B; `test_grafana_dashboards.py` pin | Presence count; board-wide pin | r7 P3-13 | Term B correct; pin misses a grouped difference | that pin | no | 2 | 1 | F1 | PARTIAL (folded) |
| R8-24 | copilot-mro | `test_phase1c_nonagent_scope_guard.py:433-472` | Function-granular approval | r7 P3-6 | Read; deletion-hunk edge noted | its pins | no | 1 | 1 | F3 | ASSERTED |
| R8-25 | copilot-mro | `tests/conftest.py`, `tests/_live_state_guards.py` (614b95ee) | Session pins + suite-wide Bedrock/S3 guards | audit §6 items 1, 3, 3a | Netns lanes: 0 AWS/IMDS/SSO/S3/Bedrock/Redis/OTLP attempts | `test_session_pins.py` | no | 2 | 1 | F3 | SETTLED (by measurement) |
| R8-26 | copilot-mro | b61d8400 excel writer; `test_referred_by_repoint.py` | Restore real modules after the test | census DataView cluster | BASE 4 failed; HEAD 22/22 and 27/27 both orders | the pair | yes — r8 (BASE red, HEAD green) | 2 | 0 | F3 | SETTLED |
| R8-27 | copilot-mro | b141776e, b428733d, 2992a8c5, a45b617a, ea28fad2 | Audit 5.1–5.6 polluter/victim fixes | audit §5 | All pairs green both orders | pairs | no (reproduction only for 5.x at HEAD) | 2 | 1 | F3 | SETTLED (green both orders) |
| R8-28 | copilot-mro | `tests/unit/memory/test_memory_gc.py` (b141776e) | Tripwire records a sweep-time lazy import | audit 5.1 | M15 survived alone: `_index_delete` never executed in the lane | that file | yes — r8 (M15 survived) | 1 | 1 | F3 | PARTIAL (P3-6) |
| R8-29 | copilot-mro | `test_workout_tool_adapters.py:397`; `resolve_workout.py:925` | Executor patched after binding | pre-range | Netns red; green only with Postgres | none | no | 2 | 1 | F3 | OPEN (P3-9) |
| R8-30 | copilot-mro | de2665b3 db stub removal | `copilot_mro.app.db` stub installed only when absent, removed after | census 13 errors | DB lane: chat_history before improvement, 0 errors | — | no | 2 | 1 | F3 | SETTLED (by lane) |
| R8-31 | copilot-mro | census | "95 → 12 red, none new" | implementer | Mapping file gone; re-derived and re-run: test_config ×3, schema_conformance ×3, FTD ×1 red as mapped; 5 workspace-shape infra = the "clone-only" five; every other red is a scratch-layout artefact green in the real workspace's shape, except P3-9 (red only without a database) | — | — | 3 | 1 | F3 | SETTLED (by re-run; the mapping itself unverifiable) |
| R8-33 | copilot-mro | `tests/api/tenancy/test_operator_grain_isolation.py` | — (pre-range) | — | Netguard: 1 refused Cognito DNS lookup during the test | none | no | 2 | 1 | F3 | OPEN (P3-10) |
| R8-32 | copilot-mro | audit items 7, 8, 9, 10, 11 | Deferred | implementer | 0 diff lines in each item's files; items 8/9 still reach the network / DB (netguard) | — | — | 3 | 1 | F3 | SETTLED (untouched, confirmed) |

## Open claims, tier 2 first

- **Tier 2:** **R8-01** (P1-1 — gate the settle write on chat liveness before C12 turns it on), **R8-03** (P2-5 —
  feedback after delete, and the comment's other copies; owner scope call for the memory/improvement copies),
  **R8-21** (vocabulary pin).
- **Tier 1, guard or lock integrity:** **R8-13** (re-seed rule vacuous — fix before the M-TRACEBACK fan-out merges
  back, since a re-seed resets the ceiling), **R8-09** and **R8-10** (the seat guard's registration match; the SAD
  result builder), **R8-11**, **R8-28**, **R8-20**.
- **Tier 1, coverage and residual:** **R8-15** (per-instance gate), **R8-16**, **R8-04**, **R8-05**, **R8-07**,
  **R8-29**, **R8-33**, **R8-22/R8-23** (folded).

**Verdict: FIX-FIRST.** The range does what its commits say where they say it: every guard it added kills its
mutant, the three tool-result leaks are closed and pinned, the seat holds end to end, the order-dependent reds are
gone in both orders, and neither network-isolated lane reaches AWS or Bedrock. What must land first is **P1-1**: the
settle-time writer re-creates exactly the personal row M-FACTS-ANONYMISE removes, for any chat deleted mid-turn — a
one-predicate fix, best made before C12 activates the writer. **P2-1** should ride with it, because the re-seed door
it leaves open is the one the fan-out merge will walk through.
