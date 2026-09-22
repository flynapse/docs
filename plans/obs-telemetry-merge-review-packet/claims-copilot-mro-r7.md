# Claims packet — copilot-mro review r7 (`2b6170b0..5ea91b80`, 30 commits incl. the panels merge `ca752296`)

Independent adversarial review, Opus, 2026-09-21. **Verdict: FIX-FIRST** — 0 P0 · 1 P1 · 6 P2 · 14 P3.
Read-only on every code tree: nothing edited, committed, checked out or stashed in `copilot-mro-obsm`
or any sibling; nothing pushed; no DB, docker, AWS, Cognito or Bedrock call. Every mutation ran in a
private scratch clone (`scratchpad/mro-review-r7/wsa/`, origin removed) and every mutated file was
restored from a scratch copy and md5-checked against its `5ea91b80` blob.

| repo | worktree | branch | range | siblings (archives) |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `2b6170b0..5ea91b80` (the live lane's later commits are not reviewed) | utils-obsm `8572635`, core-obsm `dc41caa`, flynapse-otel `34c814a`; other siblings symlinked read-only |

Lane recipe, as run: `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers"
-p no:cacheprovider --rootdir=<copy>` from the copy's root, `ENV_FILE=/home/aditya/Code/api/.env
DEBUG=false POSTGRES_DB=copilot_mro_test`, `PYTHONPATH=<netguard>:<copy>:<utils>:<core>:<flynapse-otel>`,
a fresh `PYTHONPYCACHEPREFIX` per run, pytest's own exit status recorded. `rootdir` = the scratch copy in
every run; `copilot_mro.app.__file__` = the copy (`copilot_mro` is a namespace package whose `__path__`
also lists `/home/aditya/Code/copilot-mro/copilot_mro`, but `copilot_mro.app` is a regular package and
resolved in the copy). A `sitecustomize` network guard refused every non-loopback connect and recorded it.

**Network attempts refused (pre-existing hygiene item, none from this range's files):** AWS SSO
`oidc.ap-south-1.amazonaws.com` and IMDS `169.254.169.254` — 139 from `tests/agent_sdk/core`
(`test_agent_sdk_sad_additive_property.py`, `test_agent_sdk_document_hub_additive_property.py`), 10 from
`tests/agent_sdk/tools/documents` (`test_pdf_fetch_table_reuse.py`, `test_pdf_ocr_tables.py`), 10 from
`tests/unit/agent_shared/test_production_plan_binding.py` (two tests). All passed with the guard refusing.

---

## Findings, ranked

### No P0

No new sink ships exception text on a path that any earlier round had judged closed; the one live,
unregistered path found (P1-1) reaches the model provider, not a log, and is a sibling of the 50
registered M-TOOL-ERRORS debt entries rather than a regression.

### P1-1 — the SAD agent's 13 MCP tools hand the model an exception's raw text, and no guard can see it (Severity 0 · tier 2 · F1)

`copilot_mro/app/services/data_discovery/agent/{provider,context_provider,template_provider,analysis_provider}.py`
define 13 `@tool` handlers directly (provider.py:264-423, context_provider.py:99-247,
template_provider.py:95-154, analysis_provider.py:233-347), outside the shared `ToolDispatcher`. None has a catch-all: their
refusal channel is `raise ValueError("...")`, and everything the builders raise (driver, IO, parse
errors) propagates the same way. claude_agent_sdk's in-process server routes `tools/call` to the MCP
low-level handler, which ends in `except Exception as e: return self._make_error_result(str(e))`
(`mcp/server/lowlevel/server.py:590`). **Probe (in-process, no network):** a handler raising
`RuntimeError('connection to server at "10.1.2.3", port 5432 failed: FATAL: password authentication failed for user "restore_admin" SENTINEL-R7')`
came back as `CallToolResult(isError=True, content=[<that whole string>])` — the model receives the
message verbatim. The M-TOOL-ERRORS guard cannot see it twice over: its `ROOTS`
(`tests/unit/agent_shared/test_tool_results_carry_no_exception_text.py:50-54`) exclude
`services/data_discovery/agent`, and its detector only reads `except … as name` handlers, so an
UNCAUGHT exception is invisible even inside its roots. Dispatcher-backed tools are safe here (the
dispatcher turns an uncaught handler error into the constant "Tool handler failed.", `dispatcher.py:710-716`).
**Scenario:** the SAD Level-2 run's catalog DB drops or refuses a connection mid-analysis; the model's
next turn carries the driver's host/user/SQL text, is replayed on every later call and sent to Bedrock.
**Fix:** one wrapper where the SAD tools are built (or at `sad_runner.py:322`'s server) that keeps the
deliberate constant-sentence `ValueError` refusals and turns anything else into
`failure_text(<what>, exc)`; add `data_discovery/agent` to `ROOTS` and a rule "an `@tool`/`tool(...)`
handler with no catch-all is a site".

### P2-1 — the history ratchet is defeated by a merge that discards a side branch's repair (Severity 1 · tier 1 · F1)

`tests/_register_ratchet.py:38` reads `git log --format=%H -- <register>`. Default history
simplification follows only the parent a merge is TREESAME to, so a side-branch version of the
register vanishes from the walk whenever the merge takes the other side's register — exactly the
conflict the M-TRACEBACK fan-out will produce, since every lane edits `DEBT`/`REPAIRED`. **Repro
(scratch clone):** side branch `S1` repairs `state_tools.py::_get` (code, DEBT entry removed, key added
to REPAIRED; 19 passed); mainline `M1` unrelated; `git merge -s ours` (a "take ours" resolution) → the
leak is back, the key is back in DEBT, REPAIRED lost it, and the tool-error guard is **19 passed**.
`git log -- register` lists no `S1`; `git log --full-history -- register` lists it. **Proof of the
fix:** with `--full-history` added at `_register_ratchet.py:38` (scratch only) the same merge goes red
(`state_tools.py::_get (absent) vs b737183250`). The same applies to the M-TRACEBACK register (shared
helper). **Fix:** `--full-history` (and refuse a shallow repository — P2-2).

### P2-2 — the ratchet's history is path- and depth-bound: a moved register, or a shallow clone, has none (Severity 1 · tier 1 · F1)

(a) **Rename.** `committed_versions` has no `--follow`: moving the register and its guard into a
domain folder (a move the layout rule invites) starts a fresh history. **Repro:** from `S1`, one commit
that restores the `state_get` leak, restores its DEBT entry, drops it from REPAIRED and `git mv`s both
files to `tests/unit/agent_shared/tool_errors/` → **19 passed** (the same un-repair WITHOUT the move is
red — see "could not break"). (b) **Shallow clone.** `git clone --depth 1` of that red un-repair commit →
**19 passed**: the walk sees one version. CI (`.github/workflows/otel-tests.yml`, default
`actions/checkout` depth 1) does not run these suites today, so this bites the day they are added.
**Fix:** `--follow` (or pin the register's historical paths), and `git rev-parse --is-shallow-repository`
→ fail, never pass.

### P2-3 — `ALLOWED` blesses an error CODE, uncounted; db_query's `sql_rejected` already blesses infrastructure text (Severity 1 · tier 1 · F1)

`_split()` (`test_tool_results_carry_no_exception_text.py:321`) drops every site whose `(module, code)`
is in `ALLOWED`, and `ALLOWED` is compared by equality of KEYS only — so the number of sites under an
allowed code is unbounded. **Repro:** a new `except ConnectionError as exc: return
_error("sql_rejected", f"Query rejected: {exc}", committed)` in db_query → **19 passed**. The live
allowed site is already wider than its reason: the `except ValueError` at `db_query.py:757-762` wraps
the whole handler body from `:628` (bind, relation bind, execution, row serialisation, card and DataView
registration), while the ALLOWED reason says "the SQL guard refused the model's OWN query". d908c22c
refused to allow `read_docx` for exactly this reason ("one handler covers both, so allowing it would
bless infrastructure text too"); db_query got the allowance anyway. **Fix:** count allowed sites per
`(module, qualname, code)` like DEBT, and split db_query's guard refusal from the rest of the body.

### P2-4 — M-RUN-REASON holds, but four of its five writers are unguarded (Severity 1 · tier 2 · F1)

6aef26e3 converted every writer correctly (read, and the runner mutation below is red). But only the
runner is pinned. **Repro:** restore message text in `collect_explicit.py`'s `details["read_error"]`
and in the distiller's `evidence.audit[].note` (`distiller.py:493`) → `tests/unit/improvement` +
`tests/api/improvement` **528 passed** (the 3 reds are the pre-existing ones, identical at `2b6170b0`)
and `tests/unit/observability` **489 passed**: the M-TRACEBACK detector reads log/print/raise sinks, not
stored values, and the scope guard approves both files as paid-down. `collect_implicit` and
`detect_telemetry` are the same shape. These fields are rendered verbatim by `GET /improvement/runs`,
`ImprovementRunHistory.tsx` and `FindingDetailDrawer.tsx`. **Fix:** one behavioural test per stage (a
sentinel in the raised exception reaches no stored field), or a sweep over `details[...] =` /
`"note":` writes in `services/improvement`.

### P2-5 — the tool-result detector: undeclared holes, a decoy seat, and one live unregistered site (Severity 1 · tier 1 · F1)

Plants against `offences()` at `5ea91b80` (`scratchpad/mro-review-r7/probes/tool_plants.py`):
MISSED — a Name bound from the exception passed as the seat's `what` (`label = str(exc);
tool_failure_result("x", label, exc)`: `_free_reads`, `:83-94`, frees EVERY Name argument of a
sanctioned helper, and `failure_text` renders `what` verbatim); text bound in a handler and put into a
result AFTER it; `sys.exc_info()`; a `gather(..., return_exceptions=True)` element; `traceback.format_exc()`
in a result; a dict built from the exception and returned through a name; `model_copy(update=...)`.
Caught: `json.dumps({... str(exc)})`, `ToolError(**kw)`, `str(exc.__cause__)`. The docstring's
"declared" list names none of the missed shapes except `self`. **Decoy seat:** the seat is matched by
module TAIL (`:68`, `:74`, and `:456` excludes every `*/tool_failures.py` from the users check). A local
`tools/state/tool_failures.py` whose `tool_failure_result` returns `f"{what} failed: {exc}"`, used to
"convert" `state_get` (DEBT → REPAIRED, HELPER_USERS += the file, as the failure message instructs) →
**22 passed** across both tool guards; only the scope guard's allowlist flags the new file. **Live
instance:** `build_workout.py:746` appends `str(r)` of a gather element to `errors`, which reaches the
model at `:1319`/`:1350`; it is in no register (the `_one` handler's site is; this backstop is in
`build_workout_rows`). Rare (the backstop fires only if `_one` raises outside its own catch). **Fix:**
free only the exception slot of a sanctioned helper and require `what` to be a constant; resolve the
seat by full module path; route the shapes above to the shared corpus (M-SHARED-CHECK).

### P2-6 — M-TRACEBACK detector: r6's seven are caught, 12 of 24 new plants are not (Severity 1 · tier 1 · F1)

r6's 47 plants re-run at `5ea91b80`: **34 caught / 13 missed**; all seven live-shape plants r6 named
(02d, 02e, 13, 13b, 16, 17, 18) are now CAUGHT, and the 13 misses are all on the guard's declared
"cannot see" list. New plants (`probes/plants7.py`, `plants7b.py`), appended to `document_hub/jobs.py`:
caught — tuple `isinstance`, `asyncio.wait` done set, `+=` onto a list, dict comprehension in a handler,
`logger.opt(lazy=True)` lambda, `ExceptionGroup.exceptions`, default-arg closure, queue item narrowed,
`setdefault(...).append`, gather + negated `continue`, gather zipped + negated. **Missed, and not
declared:** `task.exception()` used INLINE in a log call (`logger.error("…{}", task.exception())`, and
in an f-string); a walrus `(err := future.exception())`; a `def note(**kw): logger.error("x", **kw)`
helper fed `detail=str(e)`; gather results by index (`results[0]`), by tuple unpacking, and by a
comprehension filter; `type(r) is ValueError` and `match r: case Exception()` narrowing; a
`partial(logger.error, …, detail=str(e))` built in the handler and called after it; a sanctioned
describer fed a Name bound from the exception (N32 — same `_free_reads`-style freeing); a decoy module
named `tool_failures.py` / a file stemmed `flightops_brief.py` whose describer returns `str(exc)` (the
home is matched by tail, `test_no_exception_text_in_logs.py:330`, `:365`). No live instance of any in
copilot-mro today (grepped). **Fix:** these belong in the shared corpus; resolve describer homes by full
module path.

### P3s

1. **P3-1 (sev 2, tier 2) First-event branch: a false-fire shape, and a hand list.** `x unless x offset
   W` also returns every series that merely lacked a sample at `t−W`: a scrape-path gap that covers
   `[t−W−5m, t−W]` (≈10 min of Prometheus/collector outage, a laptop sleep in the oss stack) makes all
   seven pipeline rules and both agent rules fire, for 5 minutes, for every label set that ever failed
   in the live process. Owner-tunable; worth a runbook line. Separately,
   `test_an_any_occurrence_rule_looks_back_further_than_it_holds` checks only the hand-kept
   `_ANY_OCCURRENCE_ALERTS` (`test_alert_rules_layout.py:1067`), while 57f486c6 made the first-event
   test derive any-occurrence rules by SHAPE; `AlertmanagerNotificationsFailing`
   (`flynapse-platform-alerts.yml:96-99`, `increase[10m] > 0` for `10m`) is any-occurrence by that
   shape and has W = H, the defect that test documents ("a single increment can never fire the
   rule"). Derive the list from `_is_any_occurrence`.
2. **P3-2 (sev 2, tier 1) A retired family comes back under a computed name.** The guard is a
   substring scan (`test_retired_legacy_metrics_stay_deleted.py:107-109`); adding
   `record_histogram(f"memory_{kind}_latency_ms", …)` to `memory_db.py` → **3 passed**, and utils
   `8572635` still declares (so emits) every `retire` family until its step 2.
3. **P3-3 (sev 2, tier 1) The raw-handle sweep (4b5aea14).** No live bypass: every production
   `client.collections` goes through `weaviate_connection()`, scripts are the named exemptions, and the
   memory GC deletes through `memory_index.delete_memory_index_doc`. But `raw_client_uses()` misses
   `from utils import weaviate_service; weaviate_service.weaviate_client.get_collection(...)` — a
   "<module alias>.weaviate_client" spelling its docstring claims — plus a fresh `Weaviate()` instance
   and a raw `weaviate.connect_to_*` client. And the door `weaviate_connection()` is not "one that cannot
   read data" (`weaviate_tenancy.py:760-774`): `.collections.get(name).with_tenant(<any key>)` returns a
   traced handle whose `query` reads any partition, ungated (only traced).
4. **P3-4 (sev 3, tier 1) 8ee94301's direct `from flynapse_otel.withholding import withhold_url_secrets`
   (`mro_document_service.py:24`).** Judgement: it works and is not a runtime risk today — utils
   imports the same name at import (`intercept.py:15`, `log_bridge.py:56`) and the lock carries
   flynapse-otel 0.1.1 transitively — but it is copilot-mro's only direct import of a package its
   `pyproject.toml` does not declare (it declares only `flynapse-utils = {path = "../utils"}`), so no
   constraint protects it across M-VERSIONS' breaking 0.2.0. Declare `flynapse-otel` beside utils, or
   re-export the rule from `utils.observability` (the M-FAILURE-HOME convention). Note the shared rule
   is looser than the deleted local one by design: a benign query and `;jsessionid=` survive.
5. **P3-5 (sev 3, tier 1) Outside a git checkout, one module kills the whole observability lane.**
   `test_retired_legacy_metrics_stay_deleted.py:102` runs `git ls-files` at IMPORT: an archive copy
   collects `1 error` and runs **0** of 489 tests in `tests/unit/observability`. The ratchet tests
   fail (fail-closed, correctly) and 3 more tests need git (`test_weaviate_tenant_fanout`, two
   alertmanager tests). Reviewer lanes need clones; a collection-time `pytest.skip`/fixture would keep
   the other 488 running.
6. **P3-6 (sev 1, tier 1) The scope guard's paid-down rule (5ea91b80) is whole-file and temporary.**
   `_paid_seeded_paths` approves any change to a seeded file once its debt TOTAL fell by one site; when
   the fan-out has touched all ~190 seeded files, the wholesale approval r6 P3-7 removed is back. The
   docstring's "for exactly the work it approved" overclaims.
7. **P3-7 (sev 2, tier 2) The subagent vocabulary pin (a3660fb6) misses `agents |= {...}`**
   (scratch plant in `orchestrator.py` → `test_genai_metric_labels.py` **5 passed**), `agents =
   {**agents, …}` and `subagent_specs += [...]`. A missed registration records as `other`, not a leak.
8. **P3-8 (sev 2, tier 1) `record_document_hub_metric` now RAISES on a histogram given a tenant**
   (`document_hub/operations.py:77-78`, fee2dd1d), before the try. The module's contract is that
   metrics "must cost a debug line, never a failed upload"; a future caller making this mistake fails
   the processing attempt in production. Latent (the one histogram caller passes no tenant). Refuse in
   a test/static check; drop-and-warn at runtime.
9. **P3-9 (sev 2, tier 1) The `diagnose=False` sink guard (6de36235)** matches only `logger.add` by that
   name — not an alias (`from loguru import logger as log`) and not `logger.configure(handlers=[…])`.
   No live instance.
10. **P3-10 (sev 3, tier 1) Two commits are red at their own HEAD with the siblings of their minute:**
    `ffc49de9` (2 in `test_weaviate_doors_are_traced`, utils `26e7126` landed 7 min earlier) and
    `ca752296` (`test_the_inventory_is_exactly_the_declared_port_set`, utils `8572635` landed 8 min
    earlier). Both self-reported; fixed by `a9149afb` and `d091a372`. Cross-repo order, not code.
11. **P3-11 (sev 3, tier 1) `WeaviateCollectionNotProvisioned`'s message interpolates the collection
    name** (`llama_index_initialization.py:279`), against e15f5962's own premise that a collection name
    is a tenant's identity. Logged by type only today (`failure_fields`).
12. **P3-12 (sev 3, tier 2) The G.105 sink census omits the user.** A tool error's text reaches the
    user's live step trace: `progress_translator.py:222-227` → `summarize_tool_output` →
    `_toollog.summarize_tool_result` = `[error] <first 160 chars>`. So the 50 registered M-TOOL-ERRORS
    debt entries also land in the browser (and wherever the step trace is persisted), not only the model
    and `llm_turn_content`.
13. **P3-13 (sev 2, tier 2) Embedding panel term B is biased — confirmed.** `sum(increase(
    embedding_requests_total[1h])) - sum(increase(embedding_cost_usd_count[1h]))`: the requests counter
    is per tenant × model × status, the cost histogram per model (d091a372 kept both), and `increase()`
    drops each series' first event — with many tenants the "unpriced" term reads low or negative.
    Already routed (utils r5 → copilot-mro P3-11).
14. **P3-14 (sev 1, tier 1) The re-seed door and the same-key swap.** Re-seeding = the register's
    `SEEDED` + one digest line in the guard (the M-TRACEBACK guard also pins `508`/`727`) → a new debt key
    recorded, **19 passed**; and because versions with a different `SEEDED` are skipped
    (`test_no_exception_text_in_logs.py:1848`, `test_tool_results_carry_no_exception_text.py:397`), a
    re-seed also forgets every earlier REPAIRED key. A same-key swap (repair one site, add a same-code
    site in the same function) → **19 passed** (r6's M2, inherent). Carry REPAIRED across seeds; bind the
    seed digest to a digest of `detect`'s source.

---

## Lanes — every commit at its own HEAD

Each commit checked out (detached) in a scratch CLONE (`wsg/`, needed by the git-reading guards), the
lanes it touches run one directory at a time. `rootdir` = the clone in every run. Siblings are the
archives named above, so a commit older than a sibling commit can go red for the SIBLING's reason; those
reds were re-run against the sibling of their minute.

| commit | lanes (pytest's own counts) | reds, and why |
|---|---|---|
| `e15f5962` | observability 440+2F · tenancy 200 · retrieval 44 · memory 168 | 2F = drift (A) |
| `a8d86711` | observability 440+2F · retrieval 51 · privacy 4 | A |
| `bf071877` | observability 443+2F · memory 168 · document_hub 499 | A |
| `d908c22c` | observability 440+2F · agent_shared 1155 · tools/system 76 | A |
| `01244544` | observability 440+2F · agent_shared 1155 · tools/optimizer 98 | A |
| `6de36235` | observability 446+2F · scripts 43 | A |
| `9900a933` | observability 443+2F · integration/otel 168+1F | A; 1F = drift (B) |
| `dd589d24` | observability 444+2F | A |
| `145cb929` | integration/otel 168+1F | B |
| `c56f88f3` | observability 444+2F · integration/otel 170+1F | A, B |
| `df2a5c86` | observability 446+2F · infra 131+1F · scripts 43 · integration/ad 2 | A; infra 1F = harness (C) |
| `dc4bf340` | observability 444+2F · integration/otel 172+1F | A, B — **spot re-run with utils `255848e`: 14 passed** |
| `9f23483a` | observability 446+2F · agent_shared 1157 · flightops 41 · tools/synthesis 322 | A |
| `9e6d8739` | observability 446+2F · privacy 4 · retrieval 51 | A |
| `503239d3` | observability 446+2F · infra 131+1F | A, C |
| `ac43ff2c` | observability 470+2F · agent_services/flightops 7 · agent_shared 1157 | A — **spot re-run with utils `255848e`: 8 passed** |
| `ffc49de9` | observability 473+2F · agent_shared 1159 | A — **red at its own HEAD** (utils `26e7126` 7 min earlier; self-reported) |
| `a9149afb` | observability 474 · tenancy 200 · retrieval 51 | — |
| `ca752296` | observability 478 · agent_shared 1159 · memory 168 · document_hub 499 · integration/otel 170+2F+1E · infra 131+1F · retrieval 51 · tenancy 200 · flightops 41 · agent_services/flightops 7 · tools/optimizer 98 | B — **red at its own HEAD** (utils `8572635` 8 min earlier; Add. 99); C; 1F+1E = harness (D) |
| `d091a372` | observability 478 · integration/otel 172+1F+1E | D |
| `fee2dd1d` | observability 478 · document_hub 501 · integration/otel 172+1F+1E | D |
| `2a8f2f48` | observability 479 · retrieval 51 · tenancy 200 · memory 168 | — |
| `57f486c6` | integration/otel 173+1F+1E | D |
| `6aef26e3` | observability 479 · improvement 450+3F · api/improvement 78 | 3F pre-existing (identical at `2b6170b0`: 449+3F) |
| `4b5aea14` | observability 488 · memory 168 · retrieval 51 | — |
| `8ee94301` | observability 488 · documents 40 | — |
| `0d8934ee` | observability 488 · demo 122 | — |
| `a3660fb6` | observability 488 · agent_shared 1160 | — |
| `7acfe7c0` | observability 488 · agent_shared 1161 | — |
| `5ea91b80` | observability 489 (+1 skipped); HEAD archive + clone lanes below | — |

(A) `test_weaviate_doors_are_traced` ×2 — utils `26e7126` deleted `WeaviateProvisioningError`, fixed by
`a9149afb`. (B) `test_the_inventory_is_exactly_the_declared_port_set` — utils `8572635` added
`embedding_spend_usd_total`, fixed by `d091a372`. (C) `test_sibling_variant_picks_the_checkout_that_matches_this_one`
— my workspace's `api`/`api-obsm` are symlinks and the git-family resolver returns the resolved path.
(D) `test_browser_derived_metrics.py` ×2 — my clone is a PRIMARY checkout, so `_root` resolves the primary
`dashboard` (no contract file); with `SIBLING_CHECKOUTS=dashboard=dashboard-obsm` 8 passed + 2 skipped, and
in the archive copy 10 passed.

**HEAD `5ea91b80`, other lanes** (archive copy unless noted): agent_shared 1160+1F (the ratchet needs
git; **clone: 19/19** for that file), memory 168, document_hub 501, retrieval 50+1F (git), flightops 41,
integration/otel 173+2F (git), documents 40, agent_services 44, agent_sdk/tools 2185+2F (live-data SQL
examples, outside the range), tenancy 200, infra 131+1F (C), demo 122, scripts 43, health 7,
api_surface 1, api/improvement 78, api/document_hub 73, api/memory 20, agent_sdk/core 1371,
weaviate_migration 62, document_hub_ingest 8, architecture 61+8F (git-dependent snapshots, as r6
recorded); **observability in the archive: 1 collection error, 0 run** (P3-5) — **clone: 489 passed, 1
skipped**.

---

## What I tried to break and could not

- **A regrowth committed on the branch itself.** Repair `state_get` (commit), then un-repair it on the
  same branch (commit): `test_the_register_never_regrows_across_its_history` red (`…::_get (absent) vs
  b737183250`). The local ratchet walks the whole of HEAD's history, so detector r5's "`against` is the
  branch itself" defeat does not apply to it. `REPAIRED` cannot be edited independently: it must EQUAL
  `SEEDED − DEBT` (`test_repaired_is_exactly_what_the_seed_lost`), so every REPAIRED edit is a DEBT edit.
- **The ac43ff2c re-seed was honest.** None of the 29 keys repaired under the old seed (535 keys) is in
  the new one (508); the 4 new keys are the 4 the commit names.
- **The detector mutation holds.** Emptying `_CONTAINER_WRITERS` turns
  `test_no_module_logs_an_exceptions_text` red (restored, md5 = HEAD blob).
- **r6's seven live plants** (02d, 02e, 13, 13b, 16, 17, 18) are all caught at `5ea91b80`.
- **M-RUN-REASON's values and parser.** Every improvement writer stores `type(exc).__name__` or
  `<where>: <Type>`; the validators' `note`s are domain sentences, never exception text; the runner's
  stage error back to `"<Type>: <message>"` turns 2 tests red (restored, md5 = HEAD blob).
  `_ERROR_KIND` (`scheduler.py:243`) parses `run: ValueError`, the legacy `run: ValueError: secret`
  (type only), `latest_watermarks: TimeoutError: `, and leaves `finish_run: run row not updated (…)` as
  `finish_run` and a multi-word or multi-line tail typeless.
- **The stored `optimizer_runs.error` never reaches the model raw.** Both readers
  (`optimizer_plan_digest` via `_digest_core.plan_digest:683`, `optimizer_decompose:302`) go through
  `run_error_for_model` (fullmatch on five shapes, id alphabet `[A-Za-z0-9_-]{1,64}`); the raw value stays
  in `context` and `_run_context` does not copy it; no other copilot-mro reader of the column.
- **document_source_answer** (9f23483a): `state["error"]` is `failure_text(...)` or the synthesis error
  CODE, the tool result is the seat's; the synthesis result it forwards carries cited_synthesis's own
  (registered) debt. **flightops `_log_detail`** keeps class, host and status only.
- **Dispatcher-backed tools**: an uncaught handler exception becomes "Tool handler failed."
  (`dispatcher.py:710-716`); argument/idempotency/resource refusals are constants; the lang runtime's
  `_tool_message` renders `code: message` of that result.
- **Panels and rules name real series.** All 18 `LEGACY_SERIES` rows equal utils `8572635`'s `port`
  declarations by name, kind and unit (computed, not read); the 15 panels use the exported names
  (`llm_request_duration_seconds_bucket`, `document_hub_processing_duration_seconds_bucket`,
  `embedding_cost_usd_count`, `_total` counters); every alert selector value is one the emitter writes
  (`status="failed"|"succeeded"` = `DocumentHubProcessingAttemptStatus`, `status="processing"` =
  `DocumentHubDocumentStatus.PROCESSING`, `outcome="failed"`, cleanup statuses in utils' closed sets);
  `tenant_id` is not deleted by `attributes/metric_cardinality`.
- **`{USD}` float counter naming.** prometheusremotewrite's translator drops a braced unit (no suffix)
  and appends `_total` after removing an existing `total` token, so `embedding_spend_usd_total` exports
  under its declared name; the float add is accepted (`LegacyMetricsService.increment_counter` → the
  registry counter, `metrics.py:315-320`).
- **First-event pairing, single events.** For each pipeline rule W > H, the `unless … offset W` branch
  holds a first-ever series true for W, and `instance = service.instance.id` makes a restarted process's
  first failure a new series; the `DocumentHubProcessingStuck` `(A or A') unless (B or B')` matches on the
  empty label set as intended.
- **P3-6 (7acfe7c0).** `_safe_record` (`telemetry.py:1585-1597`) is the only `.record` on the four
  runtime histograms; the only tenant key any of them is given is `tenant.id`; the utils shim drops
  undeclared keys on a declared histogram (`LegacyMetricsService._attributes`); no direct meter use.
- **P2-2 (4b5aea14), live code.** No production module takes a raw handle outside the exemptions; the
  memory GC deletes through `delete_memory_index_doc`; `llama_index_initialization`, `tenant_partitions`,
  `operator_partitions`, `document_hub/indexing` and `weaviate_boot_check` use `weaviate_connection()`.
- **`_root.py`** md5 `3d192468…` is byte-identical at copilot-mro `503239d3`/`5ea91b80`, api-obsm
  `6ae9701` and HEAD, utils `8572635`, core `dc41caa`; `df2a5c86`'s copy = api `517f655`'s (`29a0841a`).
- **Linter over the merged range.** pyflakes over every changed `.py`, base vs head: no new undefined
  name; 4 new unused imports (`optimizer_runs.py` `ToolError`, three test files).
- **Other commits read clean:** e15f5962 (14 refusals constant, ids as attributes), a8d86711 (four
  `query=` → `query_chars=`), 9e6d8739 (30 conversions, no `{}`+kwargs, `error_message` type-only),
  6de36235 (the sink removed; utils' safe default remains), notam_service (url/params carry no key —
  the keys ride headers), bf071877 (every audit event kept), dc4bf340 (`weaviate.connect` is utils'
  `weaviate.{operation}` span name).

## What I did not test

- **The live lane's commits after `5ea91b80`**, and every sibling's uncommitted work.
- **A real Prometheus/collector.** The naming, pairing and false-fire analysis is by the translator's
  rules and PromQL semantics; nothing was scraped or evaluated. No `promtool`/`otelcol` run.
- **CloudWatch/AWS alarms** (wait on C2), the dashboard renderers of improvement runs, and the persisted
  step trace (P3-12's second store is inferred from `progress_translator`, not traced to a table).
- **SAD end to end.** P1-1 is proved at the SDK/MCP layer with a synthetic handler; no SAD run, no
  catalog DB. Whether the Claude Code CLI's own session transcript also persists that tool result was
  not checked.
- **Two harness reds (C, D in the lanes table)** — `test_sibling_variant_picks_the_checkout_that_matches_this_one` fails in my clone lanes because my
  scratch workspace's `api`/`api-obsm` are SYMLINKS (the git-family resolution returns the resolved
  path; C), and `test_browser_derived_metrics.py` resolves the primary `dashboard` in a primary clone
  (D; green with the sibling declared). Judged harness artifacts; neither was reproduced on a
  symlink-free workspace or a worktree clone.
- **Order-dependent reds** named in Add. 99/100 (lang_agent/agent_claude) — lanes were run per directory.
- **`tests/agent_sdk/tools/database/test_agent_sdk_sql_examples_live.py`** — 2 red (data-dependent
  "returns real data" against `copilot_mro_test`); outside the range.
- **Architecture lane** — 8 red in an archive copy (git-dependent snapshot tests), as r6 recorded; not
  re-run in a clone.

---

## Claims table

Severity: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or
process. Tier (§2.3a): 0 = settled by a guard I SAW fail, 1 = consequential but reversible, 2 =
irreversible or estate-shaping. Chunk: F1 contract + privacy, F2 the merge itself, F3 the residual.
Rows re-stating an existing packet row name it in "Why".

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7-01 | copilot-mro | `services/data_discovery/agent/{provider,context_provider,template_provider,analysis_provider}.py` (13 `@tool`); `test_tool_results_carry_no_exception_text.py:50-54` | M-TOOL-ERRORS seat + guard declared the lane part COMPLETE; SAD tools are outside `ROOTS` and raise uncaught | the guard sweeps only dispatcher-backed tool roots and only caught exceptions | In-process probe: a raising `@tool` → `CallToolResult(isError=True, text=<whole message>)` via `mcp/server/lowlevel/server.py:590` | none | yes — r7 behavioural probe (sentinel arrived verbatim) | 0 | 2 | F1 | OPEN (new; P1-1) |
| R7-02 | copilot-mro | `tests/_register_ratchet.py:38` | Ratchet reads `git log -- <register>` | "DEBT fits under every committed version on HEAD's history" (R6-03 fix) | Scratch: side-branch repair + `merge -s ours` → 19 passed; with `--full-history` → red | `test_the_register_never_regrows_across_its_history` (both guards) | yes — r7: fixed guard red, shipped guard green | 1 | 1 | F1 | REFUTED (P2-1) |
| R7-03 | copilot-mro | `tests/_register_ratchet.py:38` | No `--follow`; no shallow check | same | Move of register+guard with un-repair → 19 passed; `--depth 1` clone of a red commit → 19 passed | same | yes — r7 | 1 | 1 | F1 | REFUTED (P2-2) |
| R7-04 | copilot-mro | `_register_ratchet.py`; `test_tool_results_carry_no_exception_text.py:390-405` | Un-repair committed on the branch itself | R6-03 fix, detector r5 P2-2's shape | Scratch commit `2c8aa65d` → red "`…::_get (absent) vs b737183250`" | ratchet test | yes — r7 saw it fail | 1 | 0 | F1 | SETTLED |
| R7-05 | copilot-mro | `test_no_exception_text_in_logs.py:1848`; `test_tool_results_carry_no_exception_text.py:397` | Versions with a different `SEEDED` skipped; re-seed = register + digest (+ counts) | "a different seed is a different detector" | Scratch re-seed adding a new debt key → 19 passed; REPAIRED history forgotten | `test_the_register_only_shrinks` (digest) | yes — r7 (passes) | 1 | 1 | F1 | PARTIAL (door is by design; REPAIRED not carried) |
| R7-06 | copilot-mro | same registers | Counts per `key × shape` | R6-03 "M2 inherent" | Same-key swap (repair one site, add a same-code site) → 19 passed | sweep equality | yes — r7 (passes) | 1 | 1 | F1 | OPEN (inherent, re-confirmed) |
| R7-07 | copilot-mro | `test_no_exception_text_in_logs.py` REPAIRED tests | REPAIRED = SEEDED − DEBT, append-only | R6-03 | Any REPAIRED edit is a DEBT edit; x7 red | `test_repaired_is_exactly_what_the_seed_lost` | yes — r7 | 1 | 0 | F1 | SETTLED |
| R7-08 | copilot-mro | `test_tool_results_carry_no_exception_text.py:321`; `db_query.py:757-762` | ALLOWED keyed `(module, code)`, uncounted; `sql_rejected` allowed | model must fix its own SQL | New `except ConnectionError` → `sql_rejected` + `str(exc)` → 19 passed; the live `except ValueError` wraps the whole body from `:628` | `test_the_allowed_register_is_exactly_the_live_allowed_sites` | yes — r7 (passes) | 1 | 1 | F1 | REFUTED (P2-3) |
| R7-09 | copilot-mro | `test_tool_results_carry_no_exception_text.py:83-94` | Sanctioned helpers free every Name argument | helpers are type-only | Plants T01/T02, T03, T04, T05, T13, T15 missed | `test_the_detector_flags` | yes — r7 plants | 1 | 1 | F1 | OPEN (P2-5) |
| R7-10 | copilot-mro | `agent_shared/tools/workout/build_workout.py:746` → `:1319` | gather backstop appends `str(r)` to `errors`, returned to the model | "a stray raise becomes a batch-level error" | Read; no register entry for `build_workout_rows` | none | no | 0 | 1 | F1 | OPEN (latent, unregistered) |
| R7-11 | copilot-mro | `test_tool_results_carry_no_exception_text.py:68,74,456` | Seat matched by module TAIL `tool_failures` | "a local decoy of the same name is not blessed" | Decoy `tools/state/tool_failures.py` "converting" `state_get` → 22 passed (both tool guards); scope guard allowlist flags the new file | tool guards; scope guard | yes — r7 | 1 | 1 | F1 | REFUTED (P2-5) |
| R7-12 | copilot-mro | `test_no_exception_text_in_logs.py` (ac43ff2c) | Containers, isinstance, gather, `future.exception()`, lambda sinks, aliases | R6-02 fix | r6's 47 plants: 34 caught / 13 missed; its 7 named live shapes all caught; 13 misses all declared | `test_no_module_logs_an_exceptions_text` + plants | yes — r7 re-ran r6's harness | 1 | 0 | F1 | SETTLED (for the r6 shapes) |
| R7-13 | copilot-mro | `test_no_exception_text_in_logs.py:330,365` + detector | Same detector | — | 24 new plants: 12 missed (inline `task.exception()`, walrus, `**kw` helper, gather index/unpack/comprehension, `type is`/`match`, partial, describer Name arg, decoy homes by tail/stem) | same | yes — r7 plants | 1 | 1 | F1 | OPEN (P2-6; → shared corpus) |
| R7-14 | copilot-mro | `test_no_exception_text_in_logs.py:192-194` | Container-writer rule | R6-02 | `_CONTAINER_WRITERS` emptied → sweep red; restored, md5 = blob | sweep | yes — r7 | 1 | 0 | F1 | SETTLED |
| R7-15 | copilot-mro | `improvement/runner.py:813` | Stage error = `type(exc).__name__` | M-RUN-REASON | Mutant `"<Type>: <msg>"` → 2 red (`test_no_stored_run_reason_carries_an_exceptions_message`, `test_raising_stage_…`) | those two | yes — r7 | 0 | 0 | F1 | SETTLED |
| R7-16 | copilot-mro | `collect_explicit.py:425`, `distiller.py:493` (+ `collect_implicit`, `detect_telemetry` details) | Stored details/audit note = type only | M-RUN-REASON (FX-10) | Mutants with message text → improvement 528 passed, observability 489 passed | none | yes — r7 (survived) | 1 | 2 | F1 | PARTIAL (values right, unguarded; P2-4) |
| R7-17 | copilot-mro | `improvement/scheduler.py:243` | `_ERROR_KIND` accepts `(?=:\|$)` | both stored shapes | 9 strings incl. legacy, constant, multi-line — type only or none | scheduler test | no (probe) | 3 | 1 | F1 | ASSERTED |
| R7-18 | copilot-mro | `tools/optimizer/_digest_core.py:611-656`; `optimizer_plan_digest.py:209`; `optimizer_decompose.py:302` | Stored run error by SHAPE | M-TOOL-ERRORS × M-SHIFT-RUNERROR | Both readers routed; no other reader; fullmatch shapes | `test_agent_sdk_optimizer_digest_core.py` (12 cases) | implementer (2 red); not re-run | 0 | 1 | F1 | ASSERTED |
| R7-19 | copilot-mro | `tools/synthesis/document_source_answer.py:355-372` | state/result carry type or code | R6-01 | Read | `test_document_source_answer_binding.py` | implementer | 0 | 1 | F1 | ASSERTED |
| R7-20 | copilot-mro | `agent_shared/dispatcher.py:710-716` | Uncaught handler error → constant | — | Read | dispatcher tests | no | 0 | 1 | F1 | ASSERTED |
| R7-21 | copilot-mro | `tests/integration/otel/_emitted_series.py:166-207`; `llm-agents.json`; `platform-health.json` | 18 ports charted in 15 panels | M-LEGACY-PANELS (FX-03) | Computed equality vs utils `8572635` FAMILIES (name/kind/unit); exported names and suffixes checked | `test_legacy_series_inventory.py` | implementer (M5–M13); not re-run | 2 | 2 | F1 | ASSERTED |
| R7-22 | copilot-mro | `flynapse-pipeline-alerts.yml` (7 rules) | Selectors and label values | FX-04 | Every selector value is one the emitter writes (enum values, utils closed sets) | `test_alert_rules_layout.py` | implementer | 2 | 2 | F1 | ASSERTED |
| R7-23 | copilot-mro | pipeline + agent rules | `increase > 0 or count(x unless x offset W) > 0` | lazy counters' first event | Correct for a single event (W > H); a scrape-path gap ≈10 min fires every rule for every surviving label set | paired-offset tests | no | 2 | 1 | F1 | PARTIAL (P3-1) |
| R7-24 | copilot-mro | `test_alert_rules_layout.py:1067`; `flynapse-platform-alerts.yml:96-99` | W > H checked for a hand list | FX-08 | `AlertmanagerNotificationsFailing` is any-occurrence by shape with W = H = 10m, absent from the list | `test_an_any_occurrence_rule_looks_back_further_than_it_holds` | no | 2 | 1 | F1 | OPEN (P3-1) |
| R7-25 | copilot-mro | embedding spend panel (d091a372) | `{USD}` float counter `embedding_spend_usd_total` | M-LEGACY-TENANT (FX-05) | Translator: braced unit adds no suffix; `_total` deduped; float `add` accepted | `test_no_query_groups_a_legacy_histogram_by_tenant` | implementer | 2 | 2 | F1 | ASSERTED |
| R7-26 | copilot-mro | `llm-agents.json` "Embedding spend per hour by tenant" term B | requests − priced | fleet-wide unpriced companion | Series granularity differs (tenant×model×status vs model); `increase` drops each first event → low/negative | none | no | 2 | 2 | F1 | OPEN (known: utils r5 → copilot-mro P3-11) |
| R7-27 | copilot-mro | `test_retired_legacy_metrics_stay_deleted.py:102-109` | Retired families by substring | M-LEGACY-DELETE (FX-02) | `f"memory_{kind}_latency_ms"` plant → 3 passed; utils still declares until step 2 | that file | yes — r7 (passes) | 2 | 1 | F1 | PARTIAL (P3-2) |
| R7-28 | copilot-mro | same file `:102` | `git ls-files` at import | — | Archive copy: `tests/unit/observability` collects 1 error, runs 0 | — | yes — r7 (observed) | 3 | 1 | F3 | OPEN (P3-5) |
| R7-29 | copilot-mro | `tests/unit/observability/test_weaviate_raw_handles_stay_behind_the_door.py:52-80` | Sweep for `get_collection`/`client`/`get_client` on the utils singleton | R6-04 fix | No live bypass; misses `from utils import weaviate_service` spelling (claimed), new `Weaviate()`, raw `connect_to_*` | that file | yes — r7 plants | 2 | 1 | F1 | PARTIAL (P3-3) |
| R7-30 | copilot-mro | `weaviate_tenancy.py:760-774` | `weaviate_connection()` "cannot read data" | M-WEAVIATE-DOOR | `.collections.get(x).with_tenant(any)` → traced, ungated `query` | none | no | 2 | 2 | F1 | REFUTED (docstring; no live use) |
| R7-31 | copilot-mro | `agent_shared/telemetry.py:1382,1585-1597` | Tenant withheld at `_safe_record` | R6-20 (P3-6) | Only record door; only `tenant.id` supplied; utils shim drops undeclared keys | `test_no_histogram_the_runtime_records_carries_a_tenant` | implementer | 2 | 2 | F1 | ASSERTED |
| R7-32 | copilot-mro | `document_hub/operations.py:77-81` | Seat RAISES on histogram + tenant | M-LEGACY-TENANT (FX-06) | Before the try; contradicts "never a failed upload"; no caller does it | `test_the_metric_seat_refuses_a_tenant_on_a_histogram` | implementer | 2 | 1 | F1 | OPEN (P3-8, latent) |
| R7-33 | copilot-mro | `mro_document_service.py:24`; `pyproject.toml:104` | Import flynapse-otel directly, undeclared | R6-05 | Works via utils; no version constraint across M-VERSIONS 0.2.0 | `test_every_url_field_in_the_module_goes_through_the_shared_rule` | implementer | 3 | 1 | F1 | OPEN (P3-4, judged) |
| R7-34 | copilot-mro | `test_phase1c_nonagent_scope_guard.py` `_paid_seeded_paths` | Seeded file approved once its debt fell | R6-21 | Whole-file; after the fan-out every seeded file is paid | `test_a_seeded_file_is_approved_only_once_its_debt_is_paid_down` | implementer | 1 | 1 | F3 | PARTIAL (P3-6) |
| R7-35 | copilot-mro | `test_genai_metric_labels.py:143-265` | Vocabulary pinned to registration sites | R6-10 | `agents \|= {…}` plant → 5 passed | `test_the_vocabulary_is_exactly_what_the_two_runtimes_register` | yes — r7 (passes) | 2 | 2 | F1 | PARTIAL (P3-7) |
| R7-36 | copilot-mro | `tests/unit/observability/test_loguru_safe_default_reaches_workers_and_images.py:70-89` | `logger.add` must pass literal `diagnose=False` | G.117 | Name `logger` only; no `configure` | that test | implementer | 2 | 1 | F1 | PARTIAL (P3-9) |
| R7-37 | copilot-mro | `ffc49de9`, `ca752296` | Landed after the utils commits that redden them | — | 2 red / 1 red at own HEAD; green with utils `255848e` at `ac43ff2c`/`dc4bf340` (spot) | — | — | 3 | 1 | F2 | ASSERTED (self-reported; P3-10) |
| R7-38 | copilot-mro | `llama_index_initialization.py:279` | Not-provisioned message names the collection | M-WEAVIATE-REFUSAL intent (FX-07) | Read; logged by type | none | no | 3 | 1 | F1 | OPEN (P3-11) |
| R7-39 | copilot-mro | `agent_claude/progress_translator.py:222-227`; `_toollog.py:47-54` | Error tool results summarised to the user | — | `[error] <first 160 chars>` in the step trace | none | no | 3 | 2 | F3 | OPEN (P3-12) |
| R7-40 | copilot-mro | `tests/_root.py` | Byte copy | G.53 (FX-11) | md5 `3d192468` in 5 trees | carry tests | no | 3 | 1 | F3 | ASSERTED |
| R7-41 | copilot-mro | `_mro_exception_text_debt.py` (ac43ff2c) | Re-seed 508/727 | R6-02 | 0 of 29 old-seed repairs re-admitted; 4 new keys = the 4 named | digest pin | no | 1 | 1 | F1 | ASSERTED |
| R7-42 | copilot-mro | `weaviate_tenancy.py` refusals (e15f5962) | Constant sentences; ids as attributes | M-WEAVIATE-LEFTOVERS (b) | Read | `test_weaviate_tenancy_refusals_name_no_ids.py` | implementer | 0 | 2 | F1 | ASSERTED |
| R7-43 | copilot-mro | `llama_index_query.py:98,228,260,332` (a8d86711); package (9e6d8739) | `query_chars`; 30 conversions | R6-06 | Read; privacy guard roots include the package | `test_llama_index_logs_no_query_text.py`; privacy guard | implementer | 0 | 1 | F1 | ASSERTED |
| R7-44 | copilot-mro | `agents/notams/notam_service.py:97-112` (ac43ff2c) | url/params/type/status | FX-09 | Keys ride headers, not params | `test_notam_service.py` | implementer | 0 | 1 | F1 | ASSERTED |
| R7-45 | copilot-mro | merge `ca752296` | `--no-ff`, no edits | FX-01 | Lanes at the merge (see lanes table) | — | — | 3 | 1 | F2 | ASSERTED |
| R7-46 | copilot-mro | test sessions | Refusing network guard | Add. 102/111 hygiene item | 159 refused AWS/IMDS attempts from 7 tests, none in range files | — | — | 2 | 1 | F3 | OPEN (pre-existing) |

## Open claims, tier 2 first

- **Tier 2:** **R7-01** (SAD tool relay — convert and sweep before M-TOOL-ERRORS is called complete),
  **R7-16** (M-RUN-REASON's four unpinned writers), **R7-26** (embedding term B, already routed),
  **R7-30** (the ungated `weaviate_connection` docstring), **R7-39** (the step-trace sink the census
  omits), and PARTIAL **R7-35** (vocabulary pin).
- **Tier 1, guard or lock integrity:** **R7-02**, **R7-03** (the ratchet's history: merges, renames,
  shallow clones — fix before the fan-out merges back), **R7-08** (ALLOWED uncounted), **R7-09/R7-11**
  (tool detector: free Name args, decoy seat), **R7-13** (M-TRACEBACK misses → corpus), **R7-05/R7-06**
  (re-seed door, swap), **R7-34**, **R7-36**.
- **Tier 1, coverage and residual:** **R7-10** (build_workout gather backstop), **R7-23/R7-24** (pairing
  false-fire; W = H on AlertmanagerNotificationsFailing), **R7-27/R7-28**, **R7-29**, **R7-32**,
  **R7-33** (the undeclared direct dependency — owner/controller call), **R7-38**, **R7-46**.

**Verdict: FIX-FIRST**, scoped. The range's code changes are correct where they claim to be (every
M-RUN-REASON writer, the optimizer run-error shape gate, the tier-0 sites, the tenant-free histograms,
the panels' series and names, the refusal sentences) and every commit is green at its own HEAD on the
lanes it touches, except two sibling-order reds both self-reported and fixed within minutes. What must
land first: R7-01 (an unregistered, guard-invisible exception-text channel to the model) and R7-02/R7-03
(the ratchet the M-TRACEBACK fan-out depends on is defeated by the fan-out's own merge shape). R7-16 is
a small test addition that should ride with them.
