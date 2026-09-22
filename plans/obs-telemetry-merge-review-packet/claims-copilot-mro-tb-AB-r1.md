# Claims packet — copilot-mro M-TRACEBACK lanes A + B, review r1 — **PARTIAL — in progress (merged-clone lanes running)**

Independent adversarial review, Opus 5, 2026-09-22. Read-only on every real tree: nothing edited, committed,
checked out, merged or stashed in `copilot-mro-obsm*`; nothing pushed; no docker, no live stack, no DB-writing
lane (`tests/api`, `tests/db`, `tests/integration`, `-m db`, `live_agent_state` never run). All runs on archive
copies / `--shared` scratch clones under `~/.claude/scratch/obs-merge/tb-review-ab/` (durable log `NOTES.md`;
tools `tools/`; mutants `mut/`, results `mut/results.txt`; lane logs `logs_*.txt`).

| lane | worktree | branch | range | files |
|---|---|---|---|---|
| A (served path) | `copilot-mro-obsm-tbA` | `obs-merge-tbA` | `735f8213..79bad4ac` (10 commits) | 94 production + 3 tests + register |
| B (parsers/ingest) | `copilot-mro-obsm-tbB` | `obs-merge-tbB` | `735f8213..752ba4a9` (11 commits) | 25 production + register |

Siblings on PYTHONPATH (live trees, read-only): core-obsm `16cd1ae`, utils-obsm `179cc6d`, api-obsm `fbd394c`,
flynapse-otel `0224a1a`. Recipe `tools/pt.sh <clone> <pytest args>` = load gate (1-min load ≤ 14, ≥ 4 GB) →
`pytest-slot.sh` → api venv python with `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test
PHASE1C_UTILS_REPOSITORY=/home/aditya/Code/utils-obsm PYTHONPATH=<clone>:core-obsm:utils-obsm:api-obsm:flynapse-otel`,
`-o addopts="-ra --strict-markers" -p no:cacheprovider`. Import seat proven: `rootdir: …/tb-review-ab/cloneA`,
`copilot_mro.app.__file__ = …/cloneA/copilot_mro/app/__init__.py` (primary checkout last on the namespace path).
Two symlinks in the scratch dir (`core`, `dashboard` → the `-obsm` trees) let `tests/_root.sibling_*` anchor.

Severity: 0 = a content leak that ships … 3 = docs/cosmetic. Tier (§2.3a): 0 = settled by a mutation-checked guard
this reviewer saw red; 1 = consequential, reversible; 2 = irreversible / estate-shaping.

---

## Verdicts (provisional until the merged lanes finish)

- **Lane A — FIX-FIRST** — 0 P0 · 0 P1 · **2 P2** · 7 P3 (+1 out-of-lane P2 routed to G.105). Both P2s are
  model-visible regressions against the explicit M-TOOL-ERRORS allowance ("`run_code`'s own syntax error", "regex
  errors, `read_docx` search"); each is a few lines at the tool seat.
- **Lane B — MERGE-CLEAN** — 0 P0 · 0 P1 · 0 P2 · 3 P3.
- **Merge rehearsal A→B onto `557a178f`** — only the register conflicts (1 hunk for A, 2 for B); the DEBT hunk must be
  resolved by DROPPING both sides' lines, not by a union (a union is caught: mutant M1 KILLED). Both guards green on
  the merged clone (213 passed).

---

## Lane A — `735f8213..79bad4ac`

| ID | Claim | Sev | Tier | Evidence | Verdict | Failure scenario |
|---|---|---|---|---|---|---|
| A-01 | Register: exactly the 171 A-served keys (224 sites) left `DEBT` and entered `REPAIRED`; no other lane's key moved; nothing lowered-but-kept; `SEEDED` text and `SEEDED_SHA256` unchanged; `DEBT`/`REPAIRED` sorted | — | 0 | `tools/regarith.py` (deleted 171 == REPAIRED+171, all `G.104/A-served`, 224 sites, SEEDED equal, pin equal); guard red on a dropped REPAIRED key (mutant R1 KILLED) and on a paid key re-entered in DEBT (R2 KILLED) | SETTLED | — |
| A-02 | Every hunk in the 94 production files lies inside a function whose debt fell, or is an import line — no scope-guard approval needed | — | 0 | `tools/confine.py` (the scope guard's own `hunks_outside_repairs` over `735f8213..79bad4ac`): 0 files with a hunk outside; the guard goes red on a planted module-level hunk in `_topic.py` (S1 KILLED) | SETTLED | — |
| A-03 | Both guards green at HEAD, cross-repo half included | — | 1 | `pt.sh cloneA …test_no_exception_text_in_logs.py …test_phase1c_nonagent_scope_guard.py -n 0` → 213 passed, exit 0. (The lane's own full-lane run SKIPPED the cross-repo half: `utils-obsm-tbA is not a checkout`.) | SETTLED | — |
| A-04 | No loguru brace hazard introduced | — | 1 | `tools/shapecheck.py`: 0 constant messages with `{`/`}` among calls carrying kwargs. The only NON-constant messages the lane newly gave kwargs to (`lifecycle._collect_prior` `failure_message`, `_advisory` `message`, `dataview_persistence` `f"{log_label}: …"` / `f"{tool_name}: …"`) are fed brace-free literals by all 11 `_collect_prior`/`_advisory` and ~20 `log_label=`/`tool_name=` callers; loguru 0.7.3 `_log` formats `message.format(*args, **kwargs)` whenever kwargs exist and does not catch | SETTLED-by-reading | a caller later passing a data-derived label makes `str.format` raise inside a fail-open handler |
| A-05 | Logger-kind/call-shape fit: no loguru call given `extra=` (G.92 limb four), no stdlib call given bare keywords; stdlib `workout_gate`/`resolve_workout` use `extra={**failure_fields(exc)}`; no explicit `error_type=`/`stack=`/… beside the splat | — | 1 | `tools/shapecheck.py` issues 0; `tools/dupkw.py` 0; `failure_fields` keys (`error_type`, `stack`, `aws_error_code`, `sqlstate`, `pg_primary`) collide with no `LogRecord` attribute | SETTLED-by-reading | — |
| A-06 | `failure_fields` always gets the innermost handler's own exception | — | 1 | `tools/ffarg.py`: 225 calls; the 4 "mismatches" are helpers taking the exception as a parameter (`_raise(exc)`, `_record_block_save_failure`, two pre-existing) | SETTLED-by-reading | — |
| A-07 | Operator identifiers kept: every non-exception placeholder of a removed f-string reappears as a field | — | 1 | `tools/idskept.py A.diff`: 12 checked, 0 dropped; the full 3845-line diff read | SETTLED-by-reading | — |
| A-08 | Levels preserved (`exception`→`error`, `opt(exception=True).warning`→`warning`, `exc_info=True` debug/warning → same) | — | 1 | full diff read | SETTLED-by-reading | — |
| A-09 | Conversion sample (≥ 40): 29 lane-A keys (every 6th REPAIRED addition: `ad_review.recompute`, `fleet_repository.get_fleet_record`, `amos_schema._load_amos_schema`, `legacy_adapter._collect_prior_dataviews`, `progress_translator._send`, `agent_state.put_state`, `lifecycle._classify_topic`, `tool_io_archive.archive_tool_io`, `dataview_persistence.persist_data_view`, `data_discovery.register_sad_runtime`, `dataview_to_filter`, `docx_write`, `file_ingest.pdf_fetch`, `recall_pdf_summary`, `inventory_plan._plan`, `compaction.compact_chat`, `memory_store.write_memory`, `amos_retrieve`, `document_search…resolve`, `search_answers…get`, `_judge_core.resolve_judge_figures`, `request_clarification`, `techpub_package`, `workout_gate.pick_subtask_parent`, `sql_report_service._render_and_register_excel_job`, `chat_file_service._download_file_bytes`, `application_state.build_application_state`, `transports.invoke`, `code_validator.validate`) — constant message, ids as fields, exception only through `failure_fields` | — | 1 | `tools/sample.py`; diff read | SETTLED-by-reading | — |
| A-10 | The "restructures" are behaviour-preserving: (a) `_InjectedLangChainTransport.invoke` — same `rejected_before_inference` branch, message now the class name; (b) `open_browser_session` logs `cause_type=type(exc.__cause__).__name__` = the old `exc.cause_type`, because `BrowserSession.open` is the ONLY constructor of `BrowserSpawnError` and always raises it `from exc`; (c) `schema_reference._disclose` log "<tool>: failed" → "schema_reference: failed" + `tool=`; (d) `chat_management` `reason, failure = …` split on two lines | — | 0 (a) / 1 (b–d) | (a) mutant A7 (`if True:` — every transient priced zero) KILLED by `test_a_timeout_is_retried_but_its_cost_stays_honestly_unknown`; (b)–(d) by reading | SETTLED (a) · ASSERTED (b–d) | see A-P3-5 |
| A-11 | `TransientModelError` message = class name only: not model-visible (retry-internal) and it SHRINKS what `model_gateway._error_snapshot` stores as `message` in `llm_turn_content` | — | 1 | `model_gateway.py:110-114,331`; tests build their own messages | SETTLED-by-reading | — |
| A-12 | `_specs_from_bank`, `BrowserSession.open` message changes are not model-visible (boot text; the spawn error is caught by `open_browser_session`, which logs type only); `services/sandbox/*` (`TransformCodeValidator`, `TransformResultValidator`) has NO production consumer — only `scripts/manual_sandbox_check.py` and `tests/sandbox/` | — | 1 | `rg -l services.sandbox` outside the package | SETTLED-by-reading | — |
| A-13 | The two rendered-exception test edits are stronger, not weaker: they now pin "type present AND no rendered exception" | — | 0 | A4 (`put_state` back to `opt(exception=True)`) KILLED by `test_agent_sdk_agent_state_wrapper.py`; A5 (`persist_data_view` drops `failure_fields`) KILLED by `test_agent_sdk_dataview_persist_warning.py` | SETTLED | — |
| A-14 | No prompt, skill, FE type or test parses any changed text (`invalid Python syntax`, `invalid regex`, `Chart rejected`, `citation correction …`, `browser server did not start`, `unresolved`) beyond prefixes that still match (`"invalid search" in …`) | — | 1 | `rg` over `.claude/skills`, `agent_shared/prompts`, `dashboard-obsm/src`, `tests` | SETTLED-by-reading | — |
| **A-P2-1** | **`run_code` syntax-error feedback regressed against an explicit owner allowance.** `_sandbox_core.validate_code` raises `RunCodeValidationError("syntax_error", "invalid Python syntax") from exc`; `execute` returns `{"error": exc.message}` to the model: no line, column or parser reason. M-TOOL-ERRORS keeps "`run_code`'s own syntax error / stderr" for the model; the ALLOWED entry `(_sandbox_core.py::execute, 'validation')` still says "the message names the line and the rule it must fix" — now false. The M-TRACEBACK guard forbids simply reverting the raise (A1 KILLED), so the text must be rendered at the seat | 2 | 1 | `_sandbox_core.py:198-203,466-469`; plan §4a-bis M-TOOL-ERRORS; `_tool_error_text_debt.py` ALLOWED; mutant A1 | OPEN | the model sends 60 lines with an unclosed `(` on line 41 and hears only "invalid Python syntax"; it re-sends near-identical code or rewrites wholesale, burning run_code turns |
| **A-P2-2** | **`read_docx` regex search lost the compiler's reason**, the other explicit M-TOOL-ERRORS allowance ("regex errors, `read_docx` search"). `_docx_core.search_paragraphs` raises `ValueError(f"invalid regex {query!r}") from exc`; `read_docx` shows `f"invalid search: {exc}"`. Sibling `_docx_write_core.py:452` still says `f"invalid regex {find!r}: {exc}"` — the two docx tools now disagree | 2 | 1 | `_docx_core.py:140-144`; `read_docx.py:252-255`; `_docx_write_core.py:452` | OPEN | `find="(\d+"` → read_docx: "invalid regex '(\d+'" (no "missing ), unterminated subpattern at position 0"); docx_write on the same pattern says why |
| A-P3-1 | `chart_create` tells the model "Fix and retry" and now gives it nothing to fix by: "Chart rejected: Chart definition failed schema validation.. Fix and retry — …" (pydantic loc/type gone; doubled period). Ruling-compliant — chart validation is not a named M-TOOL-ERRORS exception → **owner question** (recommendation below) | 3 | 1 | `charting_tool/validator.py:68-81`; `chart_create.py:278-284` | OPEN — owner | a series value is a string where a float is required; the model cannot tell which field and retries blind |
| A-P3-2 | `CitationRuntimeError` now reads "citation correction retry exhausted" also when the cause was `CitationRetryExhausted("citation correction is unavailable")` (no correction callback) — a mislabel. Not model-visible (the parent sees only `error.code`, `nodes.py:849`); it lands in the subagent run's `final_output` | 3 | 1 | `lang_agent/citations.py:414-424`; `test_graph_runtime.py:289,301` still document the old message | OPEN | a run record says "retry exhausted" for a runtime that never retried |
| A-P3-3 | `build_awic26_token_values`: the three `_resolve_cell_value` refusals ("asset not in grid", "no live source_id", "source_id not in sources") and missing-field KeyErrors all read "`{{cell:…}}`: unresolved"; the text reaches the model/operator via `techpub_package: {exc}` | 3 | 1 | `package_builder.py:200-211,335-338`; `techpub_tools.py:1432,1444,1766` | OPEN | the AWIC/26 checkpoint cannot say which config row is wrong. Type-only fix: three `KeyError` subclasses, append `type(exc).__name__` |
| A-P3-4 | `memory_store` spy edit keeps the error-vs-warning distinction but no longer pins diagnosability (before: `exception` level = traceback attached); the spy swallows fields and the test name "…is_still_an_exception_log" is stale | 3 | 1 | A6 (drop `**failure_fields(exc)` from `write_memory`) SURVIVED; no test that names `write_memory` reads `error_type`/`stack` (`rg`) | SETTLED (survivor) | a later edit drops `failure_fields` there; the failure logs with no type and nothing fails |
| A-P3-5 | `BrowserSpawnError.cause_type` is now written and never read — its docstring still calls it "the one part of the cause a LOG may carry" — and the logged `cause_type` is unpinned | 3 | 1 | A8 (`cause_type=type(exc).__name__`, i.e. always `BrowserSpawnError`) SURVIVED across the three browser test files; no test reads `cause_type` (`rg`) | SETTLED (survivor) | a future raise site without `from` logs `cause_type="NoneType"` silently |
| A-P3-6 | 12 lane-A files (8 lane-B) are wholesale-approved in the scope guard for other rulings, so the guard cannot see a stray hunk in them; "zero approvals" for those rests on A-02's computation, not on the guard | 3 | 1 | `comm` of the guard's quoted paths vs the lane file lists (`chat_management`, `db_query`, `docx_write`, `file_ingest`, `memory_curation`, `tenant_fact`, `amos_synthesis_core`, `techpub_tools`, `resolve_workout`, `workout_gate`, `browser_transport`, `memory_db`) | SETTLED-by-reading | a later commit adds non-conversion code to e.g. `techpub_tools.py` and the scope guard stays green |
| A-P3-7 | `initialize_postgres_tables`: a seed script on loguru's default sink now prints N identical "Failed to initialize Postgres table" lines — no table, no type (fields unrendered) — the regression the deleted comment described. Recipe-compliant; the refusal types (`ProtectedDatabaseError`, `UnstatedDatabaseError`) are self-describing once fields render | 3 | 1 | `postgres_table_definitions.py:846-859`; `utils/db_guard.py:136-140` | OPEN | dev runs a seed against an unnamed DB and sees 20 bare lines |

### Out of lane scope — second-hand leaks in lane-touched functions (route to G.105)

| ID | Claim | Sev | Tier | Evidence | Verdict | Failure scenario |
|---|---|---|---|---|---|---|
| X-1 | Neither guard sees these, and neither register holds them: `build_workout` returns `errors[:20]` to the model carrying `walk_card`'s `str(exc)` (`workout_gate.py:900` — judge/gateway exceptions; a declared M-TOOL-ERRORS blind spot, "text arriving through a helper's RETURN value", live); `read_docx` `files[].error` "could not read .docx: {exc}" / "invalid search: {exc}" (`read_docx.py:245,255`); `pdf_reader.py:93` and `chat_file_service.py:1145` put PyMuPDF / python-docx text into parse `issues` that reach the model and the FE preview | 2 | 1 | the M-TOOL-ERRORS detector's own `offences()` on those modules (`tools/toolsites.py`) counts only `read_docx:280`, `classify_node:482`, `build_workout:729,1358,1360`, `_sandbox_core:469`, `chart_create:280,319` — none of the listed lines | OPEN | a provider error quoting request content during a WORKOUT walk lands in the tool result, `llm_turn_content` (30 d) and Phoenix |
| X-2 | The tool results in lane-A handlers still carry `{exc}` (`db_query error`, `Could not load … schema`, `describe_dataview error`, …) — all registered M-TOOL-ERRORS debt (`M-TOOL-ERRORS/A-served`), untouched by design; the guard holds them (A2: a NEW such site is KILLED) | — | 0 | `_tool_error_text_debt.py`; mutant A2 | SETTLED | — |

## Lane B — `735f8213..752ba4a9`

| ID | Claim | Sev | Tier | Evidence | Verdict | Failure scenario |
|---|---|---|---|---|---|---|
| B-01 | Register: exactly the 177 B-parsers keys (266 sites) moved; SEEDED/pin unchanged; sorted | — | 1 | `tools/regarith.py` (same guard mechanics proven red by R1/R2 on lane A) | SETTLED-by-reading | — |
| B-02 | Zero hunks outside repaired functions/imports | — | 1 | `tools/confine.py cloneB 752ba4a9`: 0 of 25 files | SETTLED-by-reading | — |
| B-03 | Both guards green at HEAD | — | 1 | 213 passed, exit 0 | SETTLED | — |
| B-04 | Brace / shape / `failure_fields`-argument / identifier checks clean | — | 1 | shapecheck 0 (the one flagged `mel_parser.py:1189` f-string-with-args predates the lane); dupkw 0; ffarg 263/0; idskept 116 checked / 0 dropped | SETTLED-by-reading | — |
| B-05 | Conversion sample: 12 lane-B keys (`parse_sidecar.persist_parse_alias`, `ad_parser._write_ad_catalog_rows`, `amos_parser.insert_workorder_tree_to_postgres`, `amos_post_processing.load_chunks_from_s3`, `crew._peek_head_text`, `ftd.llama_doc_ingest`, `ifim.llama_doc_ingest`, `mel._extract_pdf_pages`, `pdf_parser…extract_with_handling`, `pdf_parser._save_page_as_image`, `tn._emit_outputs`, `training._extract_embedded_images_from_page`) plus the full 3092-line diff | — | 1 | `tools/sample.py`; diff read | SETTLED-by-reading | — |
| B-06 | The guard still holds lane B's conversions | — | 0 | lane mutant m1 re-run (crew `_extract_pdf_pages` back to `{exc}`) KILLED; B1 (`pdf_linearize` CLI prints `{e}`) KILLED | SETTLED | — |
| B-07 | `tn_parser` `logger.errpr`→`logger.error` is the right fix: the typo raised `AttributeError` inside the handler and the outer handler returned `{}`, discarding every extracted header field over a failed debug-CSV write | — | 1 | `tn_parser.py:713-719` read | SETTLED-by-reading | — |
| B-P3-1 | …but the accepted behaviour change is unpinned: B2 (typo restored) SURVIVED `tests/parsers` + `tests/unit/ingest` + `tests/smoke/ingest` + the guard (698 passed); the only test naming `_extract_header_fields_with_camelot` stubs the FTD one | 3 | 1 | mutant B2; `rg` | SETTLED (survivor) | the typo (or any raise in that handler) comes back and header fields silently vanish again |
| B-P3-2 | `pdf_linearize` CLI: the script's OWN refusal text ("S3 location cannot be empty", "Could not extract bucket from location: …", "Input path is not a directory: …") became "invalid argument (ValueError)"; the CLI configures no sink that renders fields. Lane D HELD the same shape (`seed_dev_tenant` ABORTED text) for a ruling; lane B converted it without one | 3 | 1 | `pdf_linearize.py:42-45,194-218,457-472` | OPEN — owner (same ruling as lane D's held site) | an operator mistypes the S3 URL and learns only "invalid argument" |
| B-P3-3 | Commit `67cdcd03` says 31 sites; the register moved 38 (21 entries). Not corrected forward (the lane total 266 and the PAUSED note's 133 are right) | 3 | 1 | `tools/percommit.py cloneB 752ba4a9` | SETTLED-by-reading | audit trail |
| B-08 | Lane A's commit messages: the two wrong counts (`8dc595d7` "31" → 26; `4a1f18b2` "21 / 84→63" → 20 / 84→64) are corrected forward in `5089758b` and `086bc5fe`; every other message matches the register movement | — | 1 | `tools/percommit.py cloneA 79bad4ac` | SETTLED-by-reading | — |

## Merge rehearsal — `obs-merge-tbA` then `obs-merge-tbB` onto `557a178f` (scratch clone `cloneM`)

| ID | Claim | Sev | Tier | Evidence | Verdict | Failure scenario |
|---|---|---|---|---|---|---|
| M-01 | Merging A onto `557a178f` conflicts ONLY in `_mro_exception_text_debt.py`, one hunk in `REPAIRED`: the cli merge's `scripts/purge_llm_turn_content.py::{main,reap_objects}` (+ its M-CAPTURE-TRUNCATE comment) vs lane A's 171 keys. Resolution: sorted union (the two `scripts/` keys and their comment sort last). DEBT auto-merges (cli's two D-scripts deletions + A's 171) | — | 1 | `git merge --no-ff origin/obs-merge-tbA` in `cloneM` → CONFLICT (content) in the register only; `tools/resolve_union.py` | SETTLED | — |
| M-02 | Merging B onto (`557a178f` + A) conflicts ONLY in the register, two hunks. (a) a **DEBT** hunk of 5 lines — B's two `faa_ad_fetcher` entries (still on the A side) vs A's three `sandbox/*` + `participation` entries (still on the B side): **the correct resolution drops all five** (each side paid its own); a union re-enters paid debt. (b) the **REPAIRED** hunk: sorted union, 351 keys (174 + 178 − the shared `improvement/runner.py::run_improvement`) | — | 0 | `tools/resolve_ab.py`; `tools/checkmerged.py`: DEBT 157 (C 90/129, D 67/100), `REPAIRED == seed − DEBT`, SEEDED unchanged, sorted, 0 duplicates; mutant M1 (keep-both resolution of the DEBT hunk) KILLED by the guard | SETTLED | a merger who "keeps both sides" re-enters 5 paid entries; the guard catches it, so the cost is a red merge, not a silent regrowth |
| M-03 | No conflict in `test_phase1c_nonagent_scope_guard.py` (neither lane touched it; the cli merge's 14-line edit merges clean) and none in any production file | — | 1 | `git diff --name-only --diff-filter=U` after each merge | SETTLED | — |
| M-04 | Both guards green on the merged clone | — | 1 | `pt.sh cloneM …both guards… -n 0` → 213 passed, exit 0 | SETTLED | — |
| M-05 | Full unit lane on the merged clone | — | 1 | running | pending | — |

## Lane runs

| run | result | reds, each explained |
|---|---|---|
| A `tests/unit -n 2 -m "not db"` (cloneA) | 6663 passed, 7 failed, 6 errors, 23 skipped | 5 × `test_cross_repo_reads_name_their_checkout` + 1 × `test_root_anchoring` = clone LOCATION (the same 6 fail at `735f8213` in the same directory); 3 collection errors (`ad_notification_payload_contract`, `chat_turn_facts_value_gates`, `…_writer`) = no sibling beside the clone — with the `core`/`dashboard` symlinks: 87 passed, 2 failed (`value_gates` mirror tests), the same 2 fail at `735f8213` (core-obsm has moved); 1 × `…[deadline]` (known, load-sensitive). The known 8 `test_nonagent_lifecycle_spans` errors did not fire (xdist order) |
| B `tests/unit -n 2 -m "not db"` (cloneB) | 6743 passed, 9 failed, 8 errors, 22 skipped | 8 × `test_nonagent_lifecycle_spans` (known placeholder-package pollution); 2 × `value_gates` (core drift, base same); 6 × `test_cross_repo_reads_name_their_checkout` (location, base same incl. `test_sibling_variant_picks…`); 1 × `test_package_stubs_link_their_parents` = "dictionary changed size during iteration" over `sys.modules` (a concurrent import race; 9/9 alone) |
| Lane A's `tests/api/chat` batch under `-n 2` | not repeated | noted per brief: `tests/api` may write `copilot_mro_test`; this review ran no `tests/api`, `tests/db` or `-m db` lane |

## Mutation log (`mut/results.txt`; `mutant.sh`, baseline-checked, cold bytecode)

| mutant | target test | result |
|---|---|---|
| A1 `validate_code` raise back to `f"invalid Python syntax: {exc}"` | M-TRACEBACK guard | KILLED |
| A2 `wdm_graph` result `f"wdm_graph query failed: {exc}"` | M-TOOL-ERRORS guard | KILLED |
| A4 `put_state` back to `logger.opt(exception=True).warning` | edited `test_agent_sdk_agent_state_wrapper.py` | KILLED |
| A5 `persist_data_view` without `failure_fields` | edited `test_agent_sdk_dataview_persist_warning.py` | KILLED |
| A6 `write_memory` without `failure_fields` | edited `test_agent_sdk_memory_store.py` | SURVIVED (lane-wide by `rg`) |
| A7 transient usage `if True:` | `test_model_adapters_and_routing.py -k 'rate_limit or timeout or transient'` | KILLED |
| A8 `cause_type=type(exc).__name__` | three browser test files | SURVIVED (lane-wide by `rg`) |
| R1 a lane-A key dropped from `REPAIRED` | M-TRACEBACK guard | KILLED |
| R2 a paid lane-A key re-entered in `DEBT` | M-TRACEBACK guard | KILLED |
| S1 module-level hunk in `_topic.py` | scope guard | KILLED |
| lane A m1 re-run (`legacy_adapter.execute` `{exc}`) | M-TRACEBACK guard | KILLED |
| lane B m1 re-run (crew `_extract_pdf_pages` `{exc}`) | M-TRACEBACK guard | KILLED |
| B1 `pdf_linearize` prints `{e}` | M-TRACEBACK guard | KILLED |
| B2 `tn_parser` back to `logger.errpr` | `tests/parsers` + `tests/unit/ingest` + `tests/smoke/ingest` + guard | SURVIVED (698 passed; lane-wide by `rg`) |
| M1 merged register: keep-both DEBT hunk | M-TRACEBACK guard on `cloneM` | KILLED |

## Recommendation on the two model-facing proposals

**1. A typed `int` `line` field on `RunCodeValidationError` — not enough on its own, and not the cheapest route.**
M-TOOL-ERRORS keeps the WHOLE syntax error for the model (line and the parser's reason — "'(' was never closed",
"invalid syntax. Perhaps you forgot a comma?"), not just a location. And the M-TRACEBACK detector treats any
attribute read of the caught exception as text (`_NUMERIC_EXCEPTION_ATTRIBUTES` = `returncode`, `errno`,
`status_code` only — the same rule that forced the `cause_type` restructure), so `line=exc.lineno` needs a detector
change first. **Right fix: render at the ALLOWED seat.** Keep the raise constant `from exc` (A1 proves the guard
requires that). In `_sandbox_core.execute`, when `exc.__cause__` is a `SyntaxError`, build the model text from its
`lineno`, `offset` and `msg` — the model's OWN code, in the ONE channel the ruling opens (`(execute, 'validation')`,
already an ALLOWED site: the M-TOOL-ERRORS detector counts the returned dict once, and the M-TRACEBACK detector does not
sweep tool-result dicts). No detector change, no register re-seed, logs stay type-and-frames. A typed `line` can be
added later if a LOG ever needs it, together with `lineno`/`offset` in `_NUMERIC_EXCEPTION_ATTRIBUTES` (both `int | None`
by `SyntaxError`'s contract). **Same pattern for A-P2-2:** `read_docx` renders `exc.__cause__.msg` and `.pos` of the
`re.error` at its seat. (That seat is today invisible to the M-TOOL-ERRORS detector — X-1 — so record it in `ALLOWED`
when the detector learns the container shape.)

**2. A location-and-type-only pydantic describer (like `block_save_failure_fields`) — right, for `chart_create` only,
and it needs an owner ruling.** The chart tool explicitly tells the model "Fix and retry"; `loc` (schema field names,
list indices, union tags) plus `type` (pydantic's fixed vocabulary: `missing`, `float_parsing`, …) is what it needs,
and neither carries the rejected input — never `msg`, `input` or `ctx`. The chart schema's only free-form mappings are
`Dict[str, Any]`, which never produce nested errors, so no data-derived dict key can land in `loc`. Build it as a
sanctioned type-only describer (home module + `_TYPE_ONLY_DESCRIBERS` entry + a behavioural test with a planted secret
in the input, as `block_save_failure_fields` has), keep list indices for the model channel (block_save strips them for
metric-label cardinality), and put it in `ChartValidationError`'s message (the raise rule then passes, because the
describer frees the exception slot). Owner question: add "chart validation" to M-TOOL-ERRORS' named exceptions, or rule
that loc+type is not "the message". Not needed for `services/sandbox/result_validator.py` — no production consumer (A-12).
