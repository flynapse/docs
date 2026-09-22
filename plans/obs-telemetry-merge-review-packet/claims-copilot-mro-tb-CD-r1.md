# Claims packet — copilot-mro M-TRACEBACK lanes C (services) + D (scripts), review r1

Independent adversarial review, Opus 5, 2026-09-22. **PARTIAL — paused by the controller (agent cap cut to 1).**

**What is final and what is not.** Every lane-C and lane-D finding below is FINAL: the first
reviewer completed the whole packet (both lane heads, the register, the scope arithmetic, 17
mutants, the probes, the per-head full lanes and rehearsals 1 and 2) before it was killed; a
second reviewer spot-checked its DONE items and they held. The ONE item still owed is
**rehearsal 3 onto the moved obs-merge head `ce545211`** — the merges are done and resolved, the
test runs on them are not. Resume plan, recipe and remaining steps in order:
`~/.claude/scratch/obs-merge/tb-review-cd/PAUSED.md`. **The verdicts below do not change with
rehearsal 3**: it produced the same six conflicts with the same resolutions and the same register
arithmetic as rehearsals 1 and 2, and none of the six new obs-merge commits touches a file either
lane edits.

**Controller asks answered:**
- **The A+B privacy-guard question.** `tests/agent_sdk/core` + `tests/architecture` are green at `ece9c60e`, at `3637540d` and on both merge rehearsals. `test_served_api_runtime_and_tool_ordinary_logs_do_not_emit_content` PASSED at all four. Lanes C and D have no site in that guard's scope. Row X-1.
- **The owner's typed-refusal carve-out.** The HELD `seed_dev_tenant.py::main` site **is that shape**. `Aborted(RuntimeError)` is script-local, raised only in this file, at 9 sites that interpolate identifiers only, and it is caught by its own type. See the section at the end.

**Verdicts:**

| lane | verdict | P0 | P1 | P2 | P3 |
|---|---|---|---|---|---|
| C | **FIX-FIRST** | 0 | 1 | 3 | 4 |
| D | **FIX-FIRST** | 0 | 1 | 2 | 3 |
| shared scope guard | — | — | — | — | 1 |

**Both P1s are one estate defect** (C-1 = D-1):
- `failure_fields(exc)` puts the error type and frames into loguru kwargs or stdlib `extra`.
- Any process that never calls `setup_logging` has a sink that drops those fields: the deployed S3 PDF Lambda, six stdlib `basicConfig` AD scripts, and three loguru scripts.
- In those processes the converted line is now a bare constant. There is no type, no frames, and no ids — the conversion moved the ids into kwargs, and the sink drops them.
- The lanes' tests capture records upstream of the sink, so they cannot see this.
- The cheapest fix is outside both lanes: one utils change, making the safe-default loguru sink and a stdlib formatter render the flattened extras.
- **If that fix lands, or the controller rules the entrypoints call `setup_logging`,** both lanes are MERGE-CLEAN on their own diffs. The one exception is lane C's C-9, which is two small tests.

**Nothing in either lane ships a content leak (no P0).** The register, the frozen seed digest and every scope approval are arithmetically clean and guard-proved (R1, S1, S2 killed).

## Read-only statement

- Nothing was edited, committed, checked out, merged, stashed or reset in `copilot-mro-obsm-tbC`, `copilot-mro-obsm-tbD`, `copilot-mro-obsm` or any sibling. Nothing was pushed.
- No database, docker or live stack was used, and no sub-agent.
- The real worktrees are untouched: `obs-merge-tbC` is at `ece9c60e` and `obs-merge-tbD` at `3637540d`. Their state was only read, through `git diff` and `git archive`.
- All work ran in `~/.claude/scratch/obs-merge/tb-review-cd/` (durable):
  - `clone/` — a local clone of `copilot-mro/.git` with its origin removed. Branch `merged` holds the rehearsal merges; `r7b`, `tbA` and `tbB` were fetched for `git merge-tree`.
  - `wtC`, `wtD`, `wtBase` — worktrees of that clone at `ece9c60e`, `3637540d` and `735f8213`. Every mutant ran in them, and each was restored and verified clean.
  - `C/`, `D/`, `base/` — `git archive` copies, used for reading.
  - Scripts: `run.sh` (the lane recipe), `regdiff.py`, `regmerge.py`, `scope_check.py`, `binding.py`, `shadow.py`, `aborts.py`.
  - `probe/` — the sink probes. `mut/` — the mutants and `results.txt`. `NOTES.md`.

| lane | worktree | branch | range |
|---|---|---|---|
| C services | `/home/aditya/Code/copilot-mro-obsm-tbC` | `obs-merge-tbC` | `735f8213..ece9c60e` (11 commits, 33 files) |
| D scripts | `/home/aditya/Code/copilot-mro-obsm-tbD` | `obs-merge-tbD` | `735f8213..3637540d` (8 commits, 39 files) |

**The recipe**, run from the tree root:

`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PHASE1C_UTILS_REPOSITORY=/home/aditya/Code/utils-obsm PYTHONPATH=<tree>:core-obsm:utils-obsm:api-obsm:flynapse-otel pytest-slot.sh -- api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -q -p no:cacheprovider`

- `copilot_mro.app.__file__` was `<tree>/copilot_mro/app/__init__.py` in every run.
- `utils.__file__` was `utils-obsm/utils/__init__.py`.
- Each mutant ran with a fresh `PYTHONPYCACHEPREFIX` (`mutant.sh`).

---

## Lanes

| run | result |
|---|---|
| both guards @ `ece9c60e` | 213 passed |
| both guards @ `3637540d` | 213 passed |
| lane C touched-module tests (131 files, `-n 2 -m "not db"`) | 2718 passed, 2 skipped, 8 errors — the known `test_nonagent_lifecycle_spans` set. The file alone gives 8 passed. |
| lane D touched-module tests (62 files) | 1572 passed, 8 errors (the known set), 4 failed in `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` — **location artifacts:** the same 4 fail at `735f8213` from the same scratch path |
| both guards on the merged rehearsal `797c6898` | 213 passed |
| full `tests/unit -n 2 -m "not db"` on the merged rehearsal | **6692 passed, 23 skipped, 5 failed, 6 errors** (551 s). All 11 reds are location artifacts: `_root.RootAnchorError` for sibling `dashboard`/`core` from `~/.claude/scratch` (3 files collect-error), `test_cross_repo_reads_name_their_checkout` ×4 and `test_root_anchoring` ×1. **All 11 reproduce at `735f8213` from the same path.** None is in a file either lane touched. |
| the same full lane with all five surviving mutants applied | **identical: 6692 passed, the same 11 location reds** (602 s) |
| full `tests/unit -n 2 -m "not db"` @ `ece9c60e` (wtC) | **6667 passed, 23 skipped, 5 failed, 6 errors** (616 s): the same 11 location reds, nothing else |
| full `tests/unit -n 2 -m "not db"` @ `3637540d` (wtD) | **6665 passed, 23 skipped, 5 failed, 6 errors** (591 s): the same 11 location reds, nothing else |
| `tests/agent_sdk/core` + `tests/architecture` (`-n 2 -m "not db"`) @ wtC / wtD / rehearsal `797c6898` / rehearsal `db7830dc` | 1426 / 1426 / 1428 / 1428 passed, 1 skipped. In each tree 2 architecture files collect-error with `RootAnchorError` for sibling `api`, which is a location artifact reproduced at `735f8213`. Re-run with `SIBLING_CHECKOUTS=api=/home/aditya/Code/api-obsm`, those files plus `test_agent_sdk_ordinary_log_privacy.py` give **22 passed in all four trees**. |
| both guards + `test_tool_results_carry_no_exception_text.py` + `test_sdk_tool_handlers_are_seated.py` + `test_register_ratchet_history.py` on rehearsal `db7830dc` (current obs-merge `37e84d1c` + C + D) | 297 passed |
| the lanes' own full lanes, read from their notes | C `ece9c60e`: 6764 passed, 1 failed (deadline), 8 errors (known). D `3637540d`: 6763 passed, 1 failed (deadline), 8 errors (known). |

**Known pre-existing reds, confirmed at `735f8213`:**
- `tests/unit/memory/test_memory_operator_attribution.py` run serially before `test_nonagent_lifecycle_spans.py` gives **62 passed, 8 errors**. The pollution is order-dependent, not xdist-only.
- `tests/unit/tenancy/test_seed_dev_tenant.py` alone gives **12 failed, 5 passed**.
- `test_backend_lifecycle_and_failures.py::…[deadline]` alone gives 2 passed, and it passed inside both merged full lanes. It is load-sensitive only.

---

## Mutation proofs — 17 runs: 12 killed, 5 survived

Each survivor was aimed first. Then all five were applied **together** to the merged rehearsal, and the full unit lane stayed green: 6692 passed, the same 11 location reds. With all five applied, one run confirms every survivor. The only caveat: the three location-red files did not collect in that run, and none of them concerns these sites.

| mutant | target | aimed at | result |
|---|---|---|---|
| C1 | `level1._safe_failure_message` loses its `__cause__` unwrap | `test_sad_batch_output_retention.py` | KILLED — the fan-out pin `failure_message == "output rejected"` holds |
| C2 | MRO `get_document_by_id` 500 body `error=f"Service error: {e}"` | guard + `tests/unit/documents` | **SURVIVED** (full lane) |
| C3 | Lambda `lambda_handler` 500 body `f"Lambda function error: {e}"` | guard + `tests/unit/ingest` | **SURVIVED** (full lane) |
| C4 | Lambda refusal 400 body `str(exc)` | `test_s3_lambda_pins_its_operator.py` | KILLED |
| C5 | pilot `list_documents` 500 body `f"Service error: {exc}"` | guard + `tests/unit/documents` | **SURVIVED** (full lane) |
| D1 | `dispatch_ad_notifications.main` drops `failure_fields` entirely | guard + `tests/unit/ad` | **SURVIVED** (full lane) |
| D2 | `provision_rls.tenancy_of` raises `from None` | `test_provision_rls_class_inference.py` | KILLED |
| D3 | `materialize_ad_corpus.run_pair_in_savepoint` refusal carries `{exc}` (goes via `PairOutcome` to the summary print) | guard + `tests/unit/ad` | **SURVIVED** (full lane) |
| D4 | `seed_dev_tenant.assert_bindable` raised message carries `{exc}` | guard | KILLED |
| D5 | `certify_model_profile.main` probe detail carries `{exc}` | guard | KILLED |
| R1 | lane C `REPAIRED` drops `weaviate_boot_check…assert_partitions_provisioned` | guard | KILLED |
| S1 | lane C scope approval `level1.py` removed | scope guard | KILLED |
| S2 | lane D scope approval `provision_rls.py` removed | scope guard | KILLED |
| lane C m1, re-run | `mro_document_service._sort_documents` logs `{e}` | guard | KILLED |
| lane D m2, re-run | `provision_rls.tenancy_of` raised `{exc}` | guard | KILLED |

**What the kills and survivors show:**
- The lanes' own six mutants all plant exception text into the log, print or raise call itself. That is the shape the guard reads.
- Every mutant here that sends text *through a value* survives: C2, C3, C5, D3. Those are the response bodies the lane fixed, and a report field. So does D1, which removes the failure description altogether.
- The body fixes the lane C plan note advertises have no pin (C-9).

---

## Lane C — findings

### C-1 (P1, tier 1) — the Lambda's failure logs now carry nothing: no type, no frames, no message

`lambda_functions/s3_pdf_processor_lambda.py` never calls `setup_logging`, and utils' `_loguru_default.py` docstring says the same of "the S3 PDF lambda". Its sink is the safe loguru default, which writes loguru's default line with no `{extra}`. Every `logger.error("…", **failure_fields(e))` in the Lambda process loses `error_type` and `stack`:
- 5 sites in the Lambda file;
- 8 in `s3_pdf_processor.py`, when it runs inside the Lambda.

The processor's own CLI `_main` does call `setup_logging` and is fine. The SAD CLI (`data_discovery/cli.py`) calls `bootstrap`, not `setup_logging`; it is not probed.

**Probe** (`probe/lambda_probe.py`, the real `lambda_handler` with a list event):

| tree | log line | 500 body |
|---|---|---|
| `735f8213` | `Lambda function error: 'list' object has no attribute 'get'` + `[rendered traceback withheld]` | `Lambda function error: 'list' object has no attribute 'get'` |
| `ece9c60e` | `Lambda function error` — nothing else | `Lambda function error: AttributeError` |

The message is gone, which is correct. But the ruling's replacement — the type and the frames — reaches no sink. The type survives only in the body, and only for the caller.

**Failure scenario.** A production ingest run fails. CloudWatch (`/aws/lambda/s3-pdf-processor-<env>`) shows `Error processing PDF` with nothing an operator can act on. Diagnosing it takes a reproduction.

**Fix, pick one:**
- utils' safe-default sink renders the flattened `extra` (one change, covering every process without `setup_logging`); or
- the Lambda module calls `setup_logging`.

### C-2 (P2, tier 2, pre-existing) — `analysis_fallback_reason` puts exception text into the PUBLIC Level-2 summary

`DataDiscoveryService._analyze_level2_context` is REPAIRED, and its log line was converted. The same `except` block still returns `"analysis_fallback_reason": f"{type(exc).__name__}: {exc}"[:400]`. The text then travels:
1. into `build_level2_safe_summary` (`takeaways.py:446`, "the bounded public Level 2 summary persisted on runs and manifests");
2. through `strip_blocked_keys`, which does not block this key (it blocks only secret, raw and sample keys);
3. into the run view `safe_summary` (`service.py:1489`);
4. to the dashboard `DiscoveryLevel2SafeSummary.analysis_fallback_reason` (`dashboard/types/data-discovery.ts:287`).

This is the SAD-22/23 class the same file says was closed.

**Failure scenario.** A hybrid Level-2 analysis fails, for example with a pydantic `ValidationError` whose `input_value=` quotes the model's output about the customer's schema, or with a CLI `ProcessError` carrying stderr and paths. The text is persisted on the run and manifest and served to the tenant's users.

### C-3 (P2, tier 2, pre-existing) — Document Hub stores `str(exc)` in document metadata that the API serves

`DocumentHubProcessingService.process` is in the module where lane C converted two log sites. It passes `internal_error=str(exc)` at four points: raw fetch (`:221`), parser (`:243`), artifact write (`:283`) and index (`:306`).

- `_merged_processing_metadata` writes the value to `metadata.processing.internal_error`, up to 1000 characters.
- `DocumentHubDocumentRecord.metadata` (`schemas/document_hub.py:360`) is returned whole by `GET /document-hub/documents` and `GET /documents/{id}`.
- No code strips `internal_error`; `rg` finds it only in `processing.py`.

**Failure scenario.** A parser or Weaviate batch exception quotes chunk text, or an S3 error names a bucket or key. The text lands in the JSON body for everyone who can list the document.

### C-9 (P2, tier 2) — the response-body fixes the lane claims have no pin

The plan note says "MRO/pilot document 500 `error`, S3 PDF processor + Lambda results/bodies … now name type or a constant". Some of those fixes are pinned and some are not.

**Unpinned** — three mutants restore exception text and pass the full lane:
- C2: the MRO `get_document_by_id` 500 body;
- C5: the pilot `list_documents` 500 body;
- C3: the Lambda `lambda_handler` 500 body.

**Pinned** — the lane added tests for:
- the refusal body (C4 killed);
- the two ingest-helper dicts;
- `ProcessingResult.error_message`.

The guard reads only log, print and raise calls, so it is blind to a body.

**Failure scenario.** A later edit puts `{e}` back into any of the seven unpinned 500 bodies, and the suite stays green:
- MRO `get_document_by_id` and `list_documents`;
- pilot `get_document_by_id` and `list_documents`;
- Lambda `lambda_handler`, `process_single_pdf_handler` and `process_folder_handler`.

Three of the seven were mutated. For the other four, `rg` over `tests/unit/{ingest,documents}` finds no test that reads those bodies.

**Fix:** one parametrised test per service. Force the `except`, then assert that the body carries the type or the constant and not the words.

### C-4 (P3, tier 1) — second-hand prints in REPAIRED re-index code

- `DocumentHubReindexService._select` (REPAIRED, `reindex.py:648`) builds `detail=f"…at {key} ({exc})…"`.
- `preflight_span_properties` (`:295`) builds `"…could not be read ({exc})…"`.
- Both are printed by `scripts/document_hub_reindex.py`, whose docstring says the output is "piped to a file or a log".
- `cleanup_deleted_documents` (REPAIRED, `cleanup.py:466`) writes `failure_message=str(exc)` into a deleted document's `metadata.cleanup`. That is DB only.

### C-5 (P3, tier 1) — the Weaviate partition refusal no longer names the collection, but its remedy still says "the named collection"

- The test went from pinning `"DocumentHubDocuments" in str(excinfo.value)` to pinning its absence.
- `main.py:139` logs only `error_type`, so the collection is visible only in uvicorn's rendering of the chained cause.
- The name is code-owned: `live_partitions()` iterates `mt_collection_names()`. The refusal could name it from the loop variable without quoting Weaviate.

### C-6 (P3, tier 1) — `_validate_connection` collapses three authored `net_guard` messages into one

`raise ValueError(str(exc))` became `"That database host could not be reached."`. `OutboundAddressRefused` carries only `net_guard`'s own constants: "A database host is required.", "…outbound policy is misconfigured." and "…could not be reached." (`net_guard.py:99,113,123,135`). No foreign text was at risk.

After the change:
- an empty host reads "could not be reached";
- a malformed allow-list looks the same to the user, and in the log it can be told apart only by frame line.

No test pins the old wording.

### C-7 (P3, tier 2, pre-existing) — the `_safe_failure_message` comment overstates the scope approval's premise

The approved hunk makes `_safe_failure_message` read `__cause__`, with the comment "the batch row keeps the validator's own words". But the function passes ANY exception's text, up to 240 characters, into the schema-batch row: provider, psycopg2 or Bedrock errors. It is not the SAD-22 whitelist `runner.safe_failure_message`. It is DB-only: no API route reads batch rows.

### C-8 (P3, tier 1, the shared scope guard) — `_function_spans` collides on a property getter and setter

`MRODocumentService.s3_service` has a getter and a setter under one qualname. The setter's span overwrites the getter's, so the getter's converted hunk (line 165) counts as outside its repaired function. Here the file's older whole-file approval masks it. The failure is fail-closed: it forces an approval that is not needed, and never admits an unapproved edit.

### Settled or refuted for lane C

- **The document 500 bodies change contract safely.**
  - The route's `"not found" in result.error.lower()` → 404 mapping can no longer fire on traceback text. Before, any traceback containing "not found" became a 404 whose `detail` was the traceback.
  - The dashboard's `app/api/documents/[id]/route.ts` never reads `detail`.
  - No test anywhere under `tests/` pins the old prefixes.
- **The Lambda bodies change contract safely.** Consumers: `invoke_with_json.py` prints the payload; `iac` defines the log group but has no metric filter keyed on the text.
- **The `s3_key` log field was never lost.** Refuted: `process_single_pdf` runs inside `logger.contextualize(s3_key=…)`.
- **`Level1BatchOutputWritten(output_key)`** has one caller, and no other lane edits those lines.
- **No stdlib extras are lost in the API process.** `utils.observability.intercept.InterceptHandler` forwards non-standard record attributes as loguru extras, and `setup_logging`'s sinks render `{extra}` (human) or flatten it (JSON). The improvement loop, Data Discovery and Document Hub run in-app.

---

## Lane D — findings

### D-1 (P1, tier 1) — ten scripts now print a bare constant: no type, no frames, and the moved ids are gone too

**Stdlib scripts.** `scripts/ad/dispatch_ad_notifications`, `evaluate_ad_applicability`, `fetch_ad_samples`, `fetch_new_ads`, `list_applicability_unknown` and `materialize_ad_corpus` have 14 calls between them.
- They configure `logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s")`.
- `extra=failure_fields(exc)` sets record attributes that the format never prints.
- `import utils` deliberately leaves the root logger without a handler.
- Probe (`probe/stdlib_basic.py`): `… ERROR dispatch_ad_notifications Dispatch failed`, and nothing else. The old line was the full traceback.

**Loguru scripts without `setup_logging`.** `build_referred_by_mapping` (6 calls), `load_task_hierarchy_locations` (3) and `update_chunks_with_task_hierarchy` (4).
- The safe default sink drops every kwarg.
- The conversion moved the ids out of the message and into kwargs: `document_id`, `wo_id`, `file_key`, `path`, `references_url`, `task_hierarchy_key`.
- Probe (`probe/loguru_default.py`): `… - Failed to upload a chunk`.
- `purge_llm_turn_content` (2 calls) is moot after the cli merge deleted the reaper.

**Mutant D1** removes `failure_fields` from `dispatch_ad_notifications` entirely and survives the full lane. Nothing checks that a failure is described at all.

The commit subjects say "log a failure by type and frames". At the terminal, these scripts show neither.

**Fix:** the same utils change as C-1, or have these entrypoints call `setup_logging`.

### D-2 (P2, tier 1) — authored remedies replaced by frame headers

The owner has now ruled that a typed refusal may print its remedy. Under that ruling, `create_akasa_solo_tenant` and `provision_rls` qualify as they stand; the other three do not yet (the table under the `seed_dev_tenant` section).

These handlers now print `ABORTED (<Class>); the property that was false is named at:` plus `frame_headers`:
- `create_akasa_solo_tenant.main` (`:1181`, `:1362`);
- `migrate_tenancy_schema.main` (`:4228`);
- `provision_rls.main` (`:2045`);
- `provision_weaviate_mt.provision` (`:798`, verify-only);
- `migrate_ifim_dynamodb.run` (`:443`, a `SystemExit`).

The `figure_arc_headless_e2e.run_arc` precondition also lost its authored cause. Its comment still says "Kept because it states the cause more precisely", which is now stale.

The abort messages carry **dynamic facts that are not in the source line**, so a frame header cannot recover them:
- `provision_rls:1698/1712`: the role, its wrong attributes, the flag and the variable;
- `create_akasa_solo_tenant:416`: the conflicting operator rows;
- `migrate_tenancy_schema`: which table and partition;
- `mirror_properties`: the property names and shapes. `--verify-only` exists "precisely *because* you suspect drift" and to report the full set, and it now says `SystemExit` per collection.

The new `ProvisionAborted` constants, such as `"the tenancy rule refused the class of 'operators'"`, are **never printed**: `main` prints only the type and the stack.

- Exit codes are unchanged.
- No test pins these printed remedies. Whatever is ruled for `seed_dev_tenant` should apply here too.

### D-3 (P2, tier 1) — second-hand text the single-function guard cannot see, in lane-D files

- **`certify_model_profile.py`:** 13 sites in the probe helpers build `Probe(…, f"{type(exc).__name__}: {exc}" | str(exc)[:160] …)`, at lines 900, 992, 1088, 1168, 1242/1251/1256, 1370, 1396, 1423, 1438, 1457 and 1490. The text is exposed three ways:
  - `Report.add` prints each `detail` immediately (`:125`);
  - `print_record` reprints the failures (`:1717`);
  - `--bank` writes `detail` to JSON (`:1677`).

  Only `main`'s copy was seeded; D5 proves the guard catches that copy.
- **`capture_oss_live_fixtures._run_probe`** (REPAIRED — its print was converted): `result["error"] = {"type": …, "message": str(exc)[:500]}` (`:465`) is banked into `tests/fixtures/lang_agent/*.json`, which is committed.
- **`seed_dev_tenant`:** `report.warnings` at lines 651 and 664 contain `({exc})` and are printed in the summary.
- **`provision_weaviate_mt.describe`:** `tenants = [f"<unreadable: {exc}>"]` (`:494`).

**Mutant D3** reintroduces `{exc}` into `run_pair_in_savepoint`'s `PairOutcome.refusal`, which the summary prints. It survives the full lane: the guard cannot follow a value from one function to another.

### D-4 (P3, tier 1) — over-conversion of values that are not exception text

| site | lost value | what it was |
|---|---|---|
| `reset_demo` [5] (`:617`) | `code` | the portal's HTTP status, an int |
| `manual_sandbox_check` (`:84`) | `exc.reason_code` | a literal vocabulary (`syntax_error`, `blocked_call`, …). Every "blocked" line now reads `TransformCodeValidationError`, which defeats the check |
| `manual_sandbox_check` (`:22`) | `exc.name` | the missing module |
| the 12 psycopg2 import guards | ImportError text | whether it was `No module named 'psycopg2'` or a libpq load error |
| `materialize_ad_corpus.run_pair_in_savepoint` (`:1024`) | the message | the refusal still says "A 'tenant not found' here means…" but no longer shows the text it refers to. A `casefold()` classification, as `weaviate_boot_check` does, would keep the hint |

### D-5 (P3, tier 1) — `test_provision_rls_class_inference` moved its pin to a place no consumer reads

The test used `match=` on the abort message. It now asserts the rule's words on `__cause__`. The pin is live — D2 is killed. But `provision_rls.main` prints neither the message nor the cause (D-2), so the test proves a property no operator sees.

### M-2 (P3, tier 1) — an r7b × tbD conflict that must be resolved by hand

See the merge rehearsal below.

### Settled for lane D

- **Exit codes are unchanged.**
  - Every changed `SystemExit` keeps a string argument, so the exit is 1 before and after.
  - The `ABORTED` handlers keep `return 2`.
  - No `return` or `sys.exit` changed in the diff.
- **Conversion shape is correct in both lanes.** An AST check (`binding.py`) of 110 (C) and 36 (D) `failure_fields` call sites found:
  - no loguru call with `extra=`;
  - no stdlib call with `**kwargs`, which would be a runtime TypeError in an `except` path;
  - no duplicate `error_type`/`stack` key;
  - no brace in a loguru message, and no f-string loguru message.
  - `shadow.py` found no nested `except … as exc` that shadows an outer name used later.
  - No `exc_info`, `opt(exception=)`, `logger.exception`, `format_exc` or `import traceback` was added.
  - Raised messages are constant, with `from exc`.

---

## Conversion sample — 36 sites read against the recipe

Legend:
- **ids** — the operator's identifiers are kept;
- **const** — the message is a constant, or an f-string of ids only;
- **ff** — the exception goes through `failure_fields`, or through `type(exc).__name__` for prints and raises;
- **sink** — the fields render where the process logs.

| # | site | ids | const | ff | sink | note |
|---|---|---|---|---|---|---|
| 1 | `ad_review_service.recompute_operator` ×3 | tenant_id, operator_id | ✓ | ✓ | ✓ API | |
| 2 | `data_discovery/notifications.notify` | job_id | ✓ | ✓ | ✓ | |
| 3 | `data_discovery/service._validate_connection` | host, cidr count (message) | ✓ | extra | ✓ | raise collapsed (C-6) |
| 4 | `…service._execute_level2` status update | — (none before) | ✓ | extra | ✓ | `status_exc` rename; the bare `raise` still re-raises the original |
| 5 | `…service._analyze_level2_context` | — | ✓ | extra | ✓ | fallback reason leaks (C-2) |
| 6 | `data_discovery/level1._run_one_batch` raise | output key on the attribute | ✓ | `from exc` | — | |
| 7 | `agent/sad_runner.record_usage` | log_name (`%s`) | ✓ | extra | ✓ | |
| 8 | `document_classification/policy._tenant_owns_operators` | tenant_id | ✓ | ✓ | ✓ | |
| 9 | `document_hub/cleanup._mark_cleanup` | tenant, document, status | ✓ | ✓ | ✓ | |
| 10 | `document_hub/reindex._select` | tenant, document, raw_s3_key | ✓ | ✓ | ✓ | `detail` still `{exc}` (C-4) |
| 11 | `document_hub/service._dispatch_processing` | document, attempt | ✓ | ✓ | ✓ | |
| 12 | `improvement/collect_explicit` per-row | feedback_id (`%s`) | ✓ | extra | ✓ | |
| 13 | `improvement/distiller.distill_stage` telemetry | signature | ✓ | extra | ✓ | audit notes are type only |
| 14 | `mro_document_service.get_document_by_id` | document_id | ✓ | ✓ | ✓ | body constant, unpinned (C-9) |
| 15 | `mro_document_service.export_workorders_to_csv` inner | work_order_number | ✓ | ✓ | ✓ | |
| 16 | `mro_document_service._extract_structured_references_from_column` | column_name | ✓ | ✓ | ✓ | |
| 17 | `mro_document_service._lookup_lifecycle_status` | document, agency, ad_number | ✓ | ✓ | ✓ | |
| 18 | `pilot_document_service.get_document_toc` | document_id | ✓ | ✓ | ✓ | |
| 19 | `s3_pdf_processor.process_s3_folder` inner | s3_key | ✓ | ✓ | ✗ in Lambda | `error_message` type only |
| 20 | `s3_pdf_processor.get_pdf_info` | s3_key | ✓ | ✓ | ✗ in Lambda | |
| 21 | `s3_pdf_processor_lambda.lambda_handler` | — (none before) | ✓ | ✓ | **✗** (C-1) | 500 body unpinned (C-9) |
| 22 | `s3_pdf_processor_lambda._refused_operator_response` | the event is logged at start | ✓ | ✓ | ✗ | body pinned (C4) |
| 23 | `weaviate_boot_check.assert_partitions_provisioned` | the collection is lost (C-5) | ✓ | `from error` | — | |
| 24 | `invoke_with_json.invoke_aws_lambda` | AWS code (shape-checked) | ✓ | ✓ | print | |
| 25 | `build_referred_by_mapping.populate_references_doc_ids_and_pages` | document_id, wo_id | ✓ | ✓ | **✗** (D-1) | |
| 26 | `build_referred_by_mapping.build_referred_by_mapping` | document_id | ✓ | ✓ | **✗** | |
| 27 | `load_task_hierarchy_locations.download_hierarchy` | file_key | ✓ | ✓ | **✗** | |
| 28 | `update_chunks_with_task_hierarchy.process_single_task_hierarchy` | task_hierarchy_key | ✓ | ✓ | **✗** | |
| 29 | `process_amm_by_size.main` | processor | ✓ | ✓ | ✓ (`setup_logging`) | |
| 30 | `scripts/ad/evaluate_ad_applicability` seeding | tenant/operator (message) | ✓ | extra | **✗** (the summary line has the type) | |
| 31 | `scripts/ad/materialize_ad_corpus.Corpus.materialize` | tenant/operator/document (message) | ✓ | extra | **✗** | |
| 32 | `scripts/ad/fetch_new_ads.main` | ad_number (message) | ✓ | extra | **✗** | |
| 33 | `copy_weaviate_to_mt.PartitionWriter._send` | target/key/uuid | ✓ | type | print | |
| 34 | `provision_rls.Provision.tenancy_of` | the table is in the raise | ✓ | `from exc` | never printed (D-2) | |
| 35 | `seed_corpus_attribution.permitted_targets` | authored remedy kept + type | ✓ | `from exc` | print | the model conversion |
| 36 | `reset_demo.main` [0][3][5] | identity; the HTTP code was lost at [5] (D-4) | ✓ | type | print | |

---

## Register, seed and scope arithmetic

| check | lane C | lane D |
|---|---|---|
| DEBT keys / sites deleted | 90 / 129 (the whole lane seed) | 68 / 101 (seed 69 / 102) |
| deleted == REPAIRED additions | yes (`regdiff.py`) | yes |
| partial lowerings / keys added to DEBT | none / none | none / none |
| another lane's keys touched | none | none |
| keys left | none | `scripts/seed_dev_tenant.py::main` (held) |
| `SEEDED` text, and `SEEDED_SHA256 = 80a7ff66…` | unchanged; guard file untouched | unchanged; guard file untouched |
| REPAIRED is complete (a paid key missing from REPAIRED fails the guard) | **R1 KILLED** | same guard |
| hunks outside repaired functions (`scope_check.py`, the guard's own `hunks_outside_repairs`) | `level1.py` 57-59, 62-63, 1376-1378 = class docstring, `__init__`, `_safe_failure_message`, exactly the approval's stated reason | only module-level import-guard lines, in **8** approved files — `scripts/ad/{evaluate_ad_applicability,materialize_ad_corpus,verdict_delta}` (from the killed agent's `c5cea97d`) plus the 5 named. `manual_sandbox_check` has 2 lines of one `try` |
| each approval is needed | **S1 KILLED** | **S2 KILLED** |

---

## Merge rehearsal

Scratch clone: `557a178f` + `obs-merge-tbC` → `ad862d21`, then + `obs-merge-tbD` → `797c6898`.

| step | conflict | correct resolution |
|---|---|---|
| +C | `data_discovery/agent/sad_runner.py` imports | keep both: `from utils.observability import failure_fields`, a blank line, then cli's `from ...claude_cli_telemetry import …` |
| +C | register `REPAIRED` | union of lane C's 90 keys and cli's two `purge_llm_turn_content` keys, keeping cli's comment above its keys |
| +C | scope guard `MRO_POST_MERGE_PRODUCTION_PATHS` | union: cli's M-CLI-TELEMETRY + M-CAPTURE-TRUNCATE block, then lane C's `level1.py` entry |
| +D | `scripts/purge_llm_turn_content.py` | **take obs-merge's side of the whole file.** M-CAPTURE-TRUNCATE (cli) deleted `reap_objects` and `main`'s reap block — the two sites lane D converted — and lane D's `failure_fields` import would be left unused. Lane D's "101/102" therefore lands as 99 conversions plus 2 made moot by deletion. |
| +D | register | set-level (`regmerge.py`): delete lane D's remaining 66 DEBT keys (its 2 purge keys are already gone), add its 66 REPAIRED keys, and do **not** duplicate the two purge keys cli already REPAIRED. The DEBT side conflicts because both lanes deleted adjacent lines, so resolve by key, not by hunk. |
| +D | scope guard | union: the previous block plus lane D's 8 import-guard files |
| +D | `scripts/migrate_tenancy_schema.py` | auto-merged cleanly: cli's `checks()`/`convalidated` and lane D's `main` print are disjoint |

After the rehearsal:
- Merged register against `557a178f`: −156 keys, −228 sites; REPAIRED +156, none removed; lane C has no keys left; lane D has only `seed_dev_tenant.py::main`; `SEEDED` is unchanged.
- `MRO_POST_MERGE_PRODUCTION_PATHS` has 135 entries at `557a178f` and **144** after: 135 + 1 + 8.
- Both guards give 213 passed.
- The full unit lane is green bar the location artifacts (the Lanes table).

**Rehearsal 2, onto the moving head.** obs-merge moved to `37e84d1c`: 9 commits past `557a178f`, including M-TOOL-ERRORS r8's widened tool-result detector and a `_register_ratchet.py` change. C then D merged onto it as `3a07a4ff` → `db7830dc`:
- the same 6 conflicts arose, with the same resolutions;
- the guards, the widened tool-result detector, the seat guard and the ratchet-history test give **297 passed**;
- `tests/agent_sdk/core` + `tests/architecture` are green (the Lanes table).

**Rehearsal 3, onto the head as it stands now (PARTIAL — merges done, runs owed).** obs-merge
moved again, `37e84d1c` → `ce545211`: 6 commits, 8 files (`agent_shared/turn_facts.py`,
`weaviate_tenancy.py` and 6 test files). **None of the 8 is touched by lane C or lane D.** In the
scratch clone, branch `merged3` = `ce545211` + `tbC` (`e391546c`) + `tbD` (`f5ba5a93`), plus a
sort tidy (`02e866b1`):
- **the same 6 conflicts arose, with the same resolutions** — no new conflict, and
  `scripts/migrate_tenancy_schema.py` auto-merged cleanly again;
- the set-level register resolution is arithmetically identical to rehearsals 1 and 2: 68 lane-D
  DEBT keys deleted, 66 removed from ours (cli had already taken the 2 `purge` keys), 66 REPAIRED
  added, 2 already present;
- `scripts/purge_llm_turn_content.py` taken from obs-merge is byte-identical to
  `ce545211:scripts/purge_llm_turn_content.py`;
- `SEEDED_SHA256 = 80a7ff66…` is unchanged.
- **Owed:** the guards, `tests/agent_sdk/core` + `tests/architecture`, the r8-era extras and the 5
  new pins the moved head brought, all on `merged3` (steps 2–6 of `PAUSED.md`).

**A nit about the rehearsal tool, not the lanes.** `regmerge.py` appends each inserted key to its
index list out of file order, so a run of new keys lands **reversed**; rehearsal 2's register
(`db7830dc`) is unsorted from line 86 of `REPAIRED` for that reason. `REPAIRED` is a `frozenset`
and the guard is order-blind, so it is cosmetic — but whoever resolves the register by hand should
keep the file sorted, as `merged3` now is.

**r7b is ordered BEFORE tbA..D (cli → r7b → tbA..D).** `git merge-tree` shows:
- **`r7b × tbD` conflicts in `scripts/ad/evaluate_ad_applicability.py`**, in `_post_commit_side_effects`' `expected_dispatch_failures` handler:
  - r7b adds `roster_refusal` and `_NO_CLEAN_REPLAY`, and logs `"… failed (%s). " + _NO_CLEAN_REPLAY, type(exc).__name__`;
  - lane D logs the old sentence with `extra=failure_fields(exc)`.
  - **Resolution:** keep r7b's block and text, and add `extra=failure_fields(exc)`. Keep r7b's `(%s)` type in the message: under this script's `basicConfig` (D-1) it is the only place the type is visible.
- **The register also conflicts on that key.** r7b lowered it from `logger.exception` 5 to 4, and lane D deletes it. **Resolution:** delete the key and add it to REPAIRED.
- `tests/unit/ad/test_ad_evaluate_transitions.py` auto-merges but has to be run.
- `r7b × tbC` has no lane-C conflict; only r7b's own `tests/unit/metering/test_usage_ledger_write_guards.py` conflicts.
- Lanes A and B share only the register with C and D. Every lane deletes disjoint keys, so the set-level resolution above applies to each in turn.

---

## `seed_dev_tenant.py::main` — the "authored refusal" question

**Owner ruling (2026-09-22, relayed by the controller): a typed, sanctioned refusal may print its remedy.** The HELD site **is that shape**:
- `class Aborted(RuntimeError)` is defined at `seed_dev_tenant.py:162`.
- It is raised only in this file, at 9 sites. Every interpolation is an identifier or a constant (`aborts.py`), after lane D's `assert_bindable` fix (`from exc`, message constant; D4 KILLED).
- `main` catches it by its own type, `except Aborted as exc`.
- Nothing outside the file raises or imports it.

Two caveats for whoever writes the sanction:
1. Two messages echo customer-entered identity values: the tenant name and a domain (the tests' "Someone Else", "other.example").
2. The guard follows text only within one function. A future `helper(exc)` that formats an exception in another function and feeds the result to `raise Aborted(…)` would not be seen (mutant D3 shows that blind spot on a sibling script).

**The same ruling applied to lane D's converted siblings (D-2):**

| handler | shape | may print its remedy under the ruling? |
|---|---|---|
| `create_akasa_solo_tenant` | `Aborted(RuntimeError)`, 12 raise sites, identifiers and reference rows only | **yes** |
| `provision_rls` | `ProvisionAborted(RuntimeError)`, 6 raise sites, identifiers only once lane D fixed `tenancy_of`/`sentinel_grain_of` | **yes** |
| `migrate_tenancy_schema` | `MigrationAborted` | **no, as it stands.** Two raise sites carry `pg_dump` stderr (`:3715` `{tail}`, `:3822` `{result.stderr}`); they need converting first |
| `provision_weaviate_mt.provision` | a bare `SystemExit` from `mirror_properties` — authored, but not a typed refusal | needs a type |
| `migrate_ifim_dynamodb.run` | utils' `TenancyError` — authored in utils, not script-local | owner call |

The evidence gathered before the ruling follows, kept for the record.

**For keeping `print(f"ABORTED: {exc}")`:**
- All 9 `raise Aborted(...)` sites interpolate only constants and identifiers (AST: `aborts.py`), after lane D's `assert_bindable` fix: database names, environment-variable names, missing-credential names, tenant id, tenant name, domain and user keys.
- The site that could carry a DSN already prints the type only: `:292`, "The exception text is not echoed — it carries the DSN". The author already follows the discipline.
- The messages ARE the remedies, and the tests pin that on purpose:
  - "the remedy is a variable, and the abort names it";
  - "the remedy is named, not left to be deduced";
  - "the abort names both identities";
  - "presence is reported; values are never echoed".
- The script is dev-only (`ALLOWED_DATABASES`) and prints to an operator's terminal.
- **Keeping the print does not blind the guard.** `raise Aborted(f"…{exc}")` is caught at the raise site as `exception-text-in-a-raised-message` (**mutant D4 KILLED**). Foreign text entering `Aborted` stays guarded as long as `Aborted` is raised only in scanned files.

**Against:**
- The guard's print shape cannot tell authored text from foreign text. A permanent DEBT entry is an exemption by name, and the register treats DEBT as owed.
- "An abort class carries only authored text" is false for at least one sibling: `MigrationAborted` interpolates `pg_dump` stderr (`migrate_tenancy_schema.py:3715` `{tail}`, `:3822` `{result.stderr}`).
- The guard follows text only within one function. A helper that formats an exception in one function and raises `Aborted` in another is invisible to it (mutant D3 shows the shape).
- Two aborts echo customer-entered values: the tenant name ("Someone Else") and a domain.
- **Consistency.** Four sibling handlers of the same kind were converted (D-2). Whichever way this is ruled, those five handlers should follow the same ruling.
- If the print is kept, the durable form is a TYPE, not a carve-out: for example, an `AuthoredRefusal` base whose raise sites the guard checks for identifier-only interpolation. That type would also let D-2's handlers print their remedies again.

---

## Claims table

**Severity**, my own scale:
- P0 = a content or secret leak the lanes ship;
- P1 = a property the lanes claim that is absent, or guard integrity;
- P2 = a coverage or contract gap;
- P3 = docs, process or an operability nit;
- — = none.

**Tier**, per §2.3a:
- 0 = settled by a mutation-checked guard I saw red, on a mechanical decision;
- 1 = consequential but reversible;
- 2 = content, privacy or estate-shaping.

| # | Lane | File:line | Claim (decision taken) | Evidence (command) | Verdict | Severity | Tier | Failure scenario |
|---|---|---|---|---|---|---|---|---|
| C-1 | C | `lambda_functions/s3_pdf_processor_lambda.py:233` et al.; `utils/_loguru_default.py` | Lambda failures are logged "by type and frames" | `probe/lambda_probe.py` at base vs `ece9c60e` | **REFUTED** at the sink | P1 | 1 | a production ingest failure cannot be diagnosed from CloudWatch |
| C-2 | C | `data_discovery/service.py:1367` → `takeaways.py:446` → `service.py:1489` → `dashboard/types/data-discovery.ts:287` | `_analyze_level2_context` is REPAIRED | `rg analysis_fallback_reason`; `safe_payloads` blocked-key read | OPEN (pre-existing, survives a REPAIRED function) | P2 | 2 | Claude SDK error text in the tenant's public L2 summary |
| C-3 | C | `document_hub/processing.py:221,243,283,306` → `schemas/document_hub.py:360` | DocHub failures stay out of bodies | `rg internal_error` (no stripper); the response models | OPEN (pre-existing) | P2 | 2 | parser, S3 or Weaviate error text in `GET /document-hub/documents` |
| C-9 | C | `mro_document_service.py:436,516`; `pilot_document_service.py:218,288`; `s3_pdf_processor_lambda.py:233,362,496` | the 500 bodies are constant or type-only | mutants C2, C3, C5 SURVIVED on the full lane | ASSERTED (unguarded) | P2 | 2 | `{e}` returns to a 500 body and the suite stays green |
| C-4 | C | `document_hub/reindex.py:295,648`; `cleanup.py:466` | `_select` is REPAIRED | `scripts/document_hub_reindex.py:_print_item` prints `item.detail` | OPEN | P3 | 1 | S3 or Weaviate error text in a re-index run log |
| C-5 | C | `weaviate_boot_check.py:633-646`; test `:163` | the refusal is a constant; the name travels on the cause | code read; `main.py:139` | SETTLED as a constant (lane m3 killed); operability OPEN | P3 | 1 | the operator cannot tell which collection to restore |
| C-6 | C | `data_discovery/service.py:327-330`; `net_guard.py:99-135` | the SAD refusal is a constant | code read | OPEN | P3 | 1 | an empty host reads "could not be reached" |
| C-7 | C | `data_discovery/level1.py:1375-1379` | the batch row keeps "the validator's own words" | read against `runner.safe_failure_message`; C1 killed | OPEN (the comment overstates; pre-existing) | P3 | 2 | provider or psycopg2 error text in a batch row (DB only) |
| C-8 | guard | `test_phase1c_nonagent_scope_guard.py:_function_spans` | spans are keyed by qualname | `scope_check.py`: `mro_document_service.py` (165,165) counted as outside | OPEN | P3 | 1 | a property getter's conversion needs an approval it should not |
| C-10 | C | Lambda 400 refusal | the refusal body is a constant | C4 KILLED | SETTLED | — | 1 | — |
| C-11 | C | register | 90/129 paid, == REPAIRED, seed unchanged | `regdiff.py`; R1 KILLED | SETTLED | — | 0 | — |
| C-12 | C | scope `level1.py` | the approval covers exactly its 3 hunks and is needed | `scope_check.py`; S1 KILLED | SETTLED | — | 0 | — |
| C-13 | C | `level1._safe_failure_message` | the user-facing batch text survives the constant wrapper | C1 KILLED | SETTLED | — | 1 | — |
| D-1 | D | `scripts/ad/*` (14 calls); `build_referred_by_mapping`, `load_task_hierarchy_locations`, `update_chunks_with_task_hierarchy` (13) | scripts "log a failure by type and frames" | `probe/stdlib_basic.py`, `probe/loguru_default.py`; D1 SURVIVED on the full lane | **REFUTED** at the sink | P1 | 1 | "Dispatch failed", "Failed to update references for a document" — no type, frames or id |
| D-2 | D | `create_akasa_solo_tenant.py:1181,1362`; `migrate_tenancy_schema.py:4228`; `provision_rls.py:2045`; `provision_weaviate_mt.py:798`; `migrate_ifim_dynamodb.py:443`; `e2e/figure_arc_headless_e2e.py:202` | an abort prints type + frames | `aborts.py`; code read | OPEN (owner ruling) | P2 | 1 | the operator cannot learn which role, table, rows or property failed |
| D-3 | D | `certify_model_profile.py` ×13; `capture_oss_live_fixtures.py:465`; `seed_dev_tenant.py:651,664`; `provision_weaviate_mt.py:494` | lane-D files print no exception text | `rg` over the lane's files; D3 SURVIVED on the full lane | OPEN | P2 | 1 | error text in a certification record or a committed fixture |
| D-4 | D | `reset_demo.py:617`; `manual_sandbox_check.py:22,84`; 12 import guards; `materialize_ad_corpus.py:1024` | non-exception values converted | code read | OPEN | P3 | 1 | the sandbox check cannot say which rule blocked a transform |
| D-5 | D | `tests/unit/db/test_provision_rls_class_inference.py:294,378` | the pin moved to `__cause__` | D2 KILLED (the pin is live) | OPEN (it pins the wrong place) | P3 | 1 | the pin proves a property no operator sees |
| D-6 | D | register | 68/101 paid, 1 held, seed unchanged | `regdiff.py`; the same guard as R1 | SETTLED | — | 0 | — |
| D-7 | D | scope, 8 files | only module-level import guards lie outside repaired functions, and each approval is needed | `scope_check.py`; S2 KILLED | SETTLED | — | 0 | — |
| D-8 | D | every `SystemExit`/`return` | exit codes unchanged | diff scan | ASSERTED (no guard) | — | 1 | — |
| D-9 | D | `seed_dev_tenant.assert_bindable` | the raised message is a constant, with `from exc` | D4 KILLED | SETTLED | — | 1 | — |
| M-1 | merge | see Merge rehearsal | C then D merge onto `557a178f` with 6 mechanical conflicts; purge is taken from obs-merge | scratch `797c6898`; guards 213; full lane green bar location artifacts | ASSERTED | — | 1 | — |
| M-2 | merge | `scripts/ad/evaluate_ad_applicability.py` `_post_commit_side_effects` | r7b × tbD conflict | `git merge-tree r7b tbD` | OPEN (resolve at merge time) | P3 | 1 | resolving to either side drops r7b's refusal text or lane D's frames |
| M-3 | merge | rehearsal onto obs-merge `37e84d1c` | the same 6 conflicts and resolutions hold on the moved head | scratch `db7830dc`; guards + M-TOOL-ERRORS detector + seat + ratchet: 297 passed | ASSERTED | — | 1 | — |
| M-4 | merge | rehearsal 3, onto obs-merge `ce545211` | the same 6 conflicts and resolutions hold on the head as it stands now; no new-commit file overlaps either lane | scratch `merged3` = `ce545211`+tbC `e391546c`+tbD `f5ba5a93`; regmerge 68/66/66/2; purge byte-identical to `ce545211`'s | **PARTIAL** — merges done, the runs on `merged3` are owed (`PAUSED.md` steps 2–6) | — | 1 | — |
| M-5 | tooling | `regmerge.py` (reviewer's own script) | a run of inserted REPAIRED keys lands reversed; `db7830dc` is unsorted too | `sort -c` over the `REPAIRED` block | OPEN (cosmetic — `REPAIRED` is a frozenset, the guard is order-blind) | P3 | 1 | a hand resolver copies the unsorted block into the real merge |
| X-1 | C, D | `tests/agent_sdk/core/test_agent_sdk_ordinary_log_privacy.py`; `tests/architecture` | neither lane has a site in the ordinary-log privacy guard's scope | the two dirs at wtC, wtD, `797c6898`, `db7830dc`: green; the privacy test PASSED ×4 (`SIBLING_CHECKOUTS=api=…` for the 2 location-red architecture files, red at base too) | SETTLED by run (not mutation) → ASSERTED | — | 1 | — |
| X-2 | D | `seed_dev_tenant.py:162,1173` | the HELD site is a typed sanctioned refusal (owner carve-out) | `aborts.py`; `rg` for outside raisers/importers: none | ASSERTED | — | 1 | — |
