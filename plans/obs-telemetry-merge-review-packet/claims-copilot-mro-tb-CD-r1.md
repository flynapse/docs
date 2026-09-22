# Claims packet — copilot-mro M-TRACEBACK lanes C (services) + D (scripts), review r1

> **PARTIAL** — guards, touched-module runs, merge rehearsal and the full merged unit lane are done.
> Still to come: the mutation results, which are running.

Independent adversarial review, Opus 5, 2026-09-22.

**Verdicts (provisional):**
- **Lane C: FIX-FIRST** — 0 P0 · 1 P1 · 2 P2 · 5 P3
- **Lane D: FIX-FIRST** — 0 P0 · 1 P1 · 2 P2 · 2 P3

The two P1s are one estate defect seen from both lanes:
- `failure_fields` writes the error type and the frames into kwargs or `extra`.
- In any process that never calls `setup_logging`, the sink drops those fields.
- The lanes' tests capture log records at a layer that still has the fields, so they stay green.

## Read-only statement

- Nothing was edited, committed, checked out, merged, stashed or reset in `copilot-mro-obsm-tbC`, `copilot-mro-obsm-tbD`, `copilot-mro-obsm` or any sibling. Nothing was pushed.
- No database, docker or live stack was used, and no sub-agent.
- All work ran in `~/.claude/scratch/obs-merge/tb-review-cd/` (durable):
  - `clone/` — a local clone of `copilot-mro/.git` with its origin removed. Branch `merged` holds the rehearsal merges.
  - `wtC`, `wtD`, `wtBase` — worktrees of that clone at `ece9c60e`, `3637540d` and `735f8213`.
  - `C/`, `D/`, `base/` — `git archive` copies, used for reading.
  - `run.sh` — the lane recipe. `probe/` — the sink probes. `mut/` — the mutants. `NOTES.md`.

| lane | worktree | branch | range |
|---|---|---|---|
| C services | `/home/aditya/Code/copilot-mro-obsm-tbC` | `obs-merge-tbC` | `735f8213..ece9c60e` (11 commits, 33 files) |
| D scripts | `/home/aditya/Code/copilot-mro-obsm-tbD` | `obs-merge-tbD` | `735f8213..3637540d` (8 commits, 39 files) |

**The recipe**, run from the tree root:

`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PHASE1C_UTILS_REPOSITORY=/home/aditya/Code/utils-obsm PYTHONPATH=<tree>:core-obsm:utils-obsm:api-obsm:flynapse-otel pytest-slot.sh -- api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -q -p no:cacheprovider`

- `copilot_mro.app.__file__` was `<tree>/copilot_mro/app/__init__.py` in every run.
- `utils.__file__` was `utils-obsm/utils/__init__.py`.

---

## Lanes

| run | result |
|---|---|
| both guards @ `ece9c60e` (wtC) | 213 passed |
| both guards @ `3637540d` (wtD) | 213 passed |
| lane C touched-module tests (131 files, `-n 2 -m "not db"`) | 2718 passed, 2 skipped, 8 errors — the known `test_nonagent_lifecycle_spans` set; the same file alone gives 8 passed |
| lane D touched-module tests (62 files) | 1572 passed, 8 errors (the known set), 4 failed in `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` — **location artifacts:** the same 4 fail at `735f8213` from the same scratch path |
| both guards on the merged rehearsal `797c6898` | 213 passed |
| full `tests/unit -n 2 -m "not db"` on the merged rehearsal | **6692 passed, 23 skipped, 5 failed, 6 errors** (551 s). All 11 reds are location artifacts: `_root.RootAnchorError` for `dashboard`/`core` from `~/.claude/scratch`, plus `test_cross_repo_reads_name_their_checkout` ×4 and `test_root_anchoring` ×1. **All 11 reproduce at `735f8213` from the same path** (`--continue-on-collection-errors`: 5 failed, 3 errors). None is in a file either lane touched. |

**Known pre-existing reds, confirmed at `735f8213`:**
- `test_memory_operator_attribution.py` run serially before `test_nonagent_lifecycle_spans.py` gives **62 passed, 8 errors**. The pollution is order-dependent, not xdist-only.
- `tests/unit/tenancy/test_seed_dev_tenant.py` alone gives **12 failed, 5 passed**.
- `test_backend_lifecycle_and_failures.py::…[deadline]` alone gives 2 passed; it is load-sensitive only.
- None of the three appeared as a regression.

---

## Lane C — findings

### C-1 (P1, tier 1) — the Lambda's failure logs now carry nothing: no type, no frames, no message

`lambda_functions/s3_pdf_processor_lambda.py` never calls `setup_logging`, and the utils module docstring says the same of the S3 PDF Lambda. Its sink is therefore utils' safe loguru default, which prints loguru's default line with no `{extra}`. Every `logger.error("…", **failure_fields(e))` in the Lambda process loses `error_type` and `stack`:
- 5 sites in the Lambda file;
- 8 in `s3_pdf_processor.py`, when it runs inside the Lambda.

**Probe** (`probe/lambda_probe.py`, the real `lambda_handler` with a list event):

| tree | CloudWatch-equivalent line | response body |
|---|---|---|
| `735f8213` | `Lambda function error: 'list' object has no attribute 'get'` + `[rendered traceback withheld]` | `Lambda function error: 'list' object has no attribute 'get'` |
| `ece9c60e` | `Lambda function error` — and nothing else | `Lambda function error: AttributeError` |

The message is gone, which is correct. But the ruling's replacement — the type and the frames — does not appear either. Only the caller who gets the 500 body sees the type. The frames are visible nowhere.

**Failure scenario.** A production ingest run fails. CloudWatch (`/aws/lambda/s3-pdf-processor-<env>`) shows `Error processing PDF` or `Lambda function error` with nothing an operator can act on. The only way to learn the cause is to reproduce it.

**Fix, pick one:**
- the utils safe-default sink renders the flattened `extra` (one change, covering every process that skips `setup_logging`); or
- the Lambda handler module calls `setup_logging`.

**Guard:** none. The lane's tests read records at a layer that still carries the fields.

### C-2 (P2, tier 2, pre-existing) — `analysis_fallback_reason` puts the exception text into the PUBLIC Level-2 summary

`DataDiscoveryService._analyze_level2_context` is REPAIRED, and its log line was converted. The same `except` block still returns `"analysis_fallback_reason": f"{type(exc).__name__}: {exc}"[:400]`. That text flows on:
1. into `build_level2_safe_summary` (`takeaways.py:446` — "the bounded public Level 2 summary persisted on runs and manifests");
2. then to the dashboard's `DiscoveryLevel2SafeSummary.analysis_fallback_reason` (`dashboard/types/data-discovery.ts:287`).

This is the SAD-22/23 class that the same file's docstring says was closed ("raw exception strings from a Level 2 run were persisted, returned by the API").

**Failure scenario.** A hybrid Level-2 run's Claude analysis fails, for example with a pydantic `ValidationError`. Its `input_value=` quotes the model's output about the customer's schema, or a CLI `ProcessError` carries stderr and paths. The text is persisted on the run and manifest and rendered to the tenant's users.

**Guard:** none. The guard is scoped to one function and to log and print sinks.

### C-3 (P2, tier 2, pre-existing) — Document Hub stores `str(exc)` in document metadata that the API serves

`DocumentHubProcessingService.process` has four sites, in the module whose two log sites lane C converted. The raw fetch, the parser, the artifact write and the index each pass `internal_error=str(exc)`.

`_merged_processing_metadata` writes that value to `metadata.processing.internal_error`, up to 1000 characters. `DocumentHubDocumentRecord.metadata` is returned whole:
- by `GET /document-hub/documents` (`DocumentHubDocumentListResponse`);
- by `GET /documents/{id}` (`DocumentHubDocumentResponse`).

No code strips `internal_error`; grep finds it only in `processing.py`.

**Failure scenario.** A parser or Weaviate batch exception quotes chunk text, or an S3 error names a bucket or key. That text lands in a JSON body visible to everyone who can list the document.

### C-4 (P3, tier 1) — second-hand prints in REPAIRED re-index code

- `DocumentHubReindexService._select` (REPAIRED): `detail=f"…at {key} ({exc})…"`.
- `preflight_span_properties`: `f"…could not be read ({exc})…"`.
- Both are printed by `scripts/document_hub_reindex.py:_print_item`/`main`, whose docstring says the output is "piped to a file or a log".
- `cleanup_deleted_documents` (REPAIRED) writes `failure_message=str(exc)` into a deleted document's `metadata.cleanup`. That is DB only.

### C-5 (P3, tier 1) — the Weaviate partition refusal no longer names the collection, but its remedy still says "the named collection"

- The test went from pinning `"DocumentHubDocuments" in str(excinfo.value)` to pinning its absence.
- `main.py` logs only `error_type`, so the collection is visible only through uvicorn's rendering of the chained cause.
- The name is code-owned: `live_partitions()` iterates `mt_collection_names()`. The refusal could name it from the loop variable without quoting Weaviate.

### C-6 (P3, tier 1) — `_validate_connection` collapses three authored `net_guard` messages into one

`raise ValueError(str(exc))` became `"That database host could not be reached."`. `OutboundAddressRefused` carries only `net_guard`'s own constants:
- "A database host is required."
- "…outbound policy is misconfigured."
- "…could not be reached."

No foreign text was at risk. After the change:
- an empty host reads "could not be reached";
- a malformed allow-list reads the same to the user, and in the log it is distinguishable only by frame line.

No test pins the old wording. This is a UX change the ruling did not require.

### C-7 (P3, tier 2) — the `_safe_failure_message` comment overstates the scope approval's premise

The approved hunk makes `_safe_failure_message` read `__cause__`. The comment says "the batch row keeps the validator's own words". But the function passes ANY exception's text, up to 240 characters, into the schema-batch row:
- provider errors;
- psycopg2 errors;
- Bedrock errors.

It is not the SAD-22 whitelist `runner.safe_failure_message`. It is DB-only: no API route reads batch rows. This is pre-existing and unchanged by the lane.

### C-8 (P3, tier 1) — scope-guard `_function_spans` collides on a property getter and setter

`MRODocumentService.s3_service` has a getter and a setter under one qualname. The setter's span overwrites the getter's, so the getter's converted hunk (line 165) counts as outside the repaired function. Here it is masked by the file's older whole-file approval. The failure is fail-closed: it forces an approval that is not needed. It never admits an unapproved edit.

### Settled or refuted for lane C

- **The 500 bodies change contract safely.**
  - The MRO/pilot `error` is `"Service error"`.
  - The route's `"not found" in result.error.lower()` → 404 mapping can no longer fire on traceback text. Before, any traceback containing "not found" became a 404 with the traceback as `detail`; that is an improvement.
  - The dashboard's `app/api/documents/[id]/route.ts` never reads `detail`.
  - No test outside `tests/unit` pins the old `Service error: ` prefix; searched across `tests/`.
- **The Lambda bodies change contract safely.** The 400 refusal is a constant and the 500s are type-only. Consumers: `invoke_with_json.py` prints the payload; `iac` has a log group but no metric filter keyed on the text.
- **The `s3_key` log field was never lost.** Refuted: `process_single_pdf` runs inside `logger.contextualize(s3_key=…)`.
- **`Level1BatchOutputWritten(output_key)`** has one caller, and lanes A, B and r7b keep the old signature only in untouched copies of the same lines. No conflict.

---

## Lane D — findings

### D-1 (P1, tier 1) — ten scripts now print a bare constant: no type, no frames, and the moved ids are gone too

**Stdlib scripts using `logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s")`.** These are `scripts/ad/dispatch_ad_notifications`, `evaluate_ad_applicability`, `fetch_ad_samples`, `fetch_new_ads`, `list_applicability_unknown` and `materialize_ad_corpus`, with 14 calls between them.
- `extra=failure_fields(exc)` sets record attributes that the format never prints.
- `import utils` deliberately leaves the root logger without a handler ("`logging.basicConfig` still works"), so nothing routes them to loguru.
- Probe (`probe/stdlib_basic.py`): `… ERROR dispatch_ad_notifications Dispatch failed`, and nothing more. The old line was the full traceback.

**Loguru scripts without `setup_logging`.** These are `build_referred_by_mapping` (6), `load_task_hierarchy_locations` (3) and `update_chunks_with_task_hierarchy` (4). `purge_llm_turn_content` (2) is moot after the cli merge.
- The safe default sink drops every kwarg.
- The conversion moved the ids out of the message and into kwargs: `document_id`, `wo_id`, `file_key`, `path`, `references_url`, `task_hierarchy_key`.
- The operator now reads `Failed to update references for a document` and cannot tell which one.
- Probe (`probe/loguru_default.py`): `… - Failed to upload a chunk`.

The commit subjects claim "log a failure by type and frames". At the sink, those scripts show neither.

**Fix:** the same utils change as C-1. Alternatively, the scripts configure logging through `utils.observability.intercept.install()`/`setup_logging`, or keep ids in the message text.

### D-2 (P2, tier 1, needs the same ruling as `seed_dev_tenant`) — authored remedies replaced by frame headers

Five handlers print `ABORTED (<Class>); the property that was false is named at:` plus `frame_headers`:
- `create_akasa_solo_tenant.main` (×2);
- `migrate_tenancy_schema.main`;
- `provision_rls.main`;
- `provision_weaviate_mt.provision` (verify-only);
- `migrate_ifim_dynamodb.run` (`SystemExit`).

The `figure_arc_headless_e2e.run_arc` precondition also lost its authored cause. Its comment still says "Kept because it states the cause more precisely", which is now stale.

The abort messages carry **dynamic facts that are not in the source line**, so the frame header cannot recover them:
- `provision_rls:1698/1712`: which role, which attributes, which flag or variable;
- `create_akasa_solo_tenant:416`: the conflicting operator rows;
- `migrate_tenancy_schema`: which table and which partition;
- `mirror_properties`: the property names and shapes. `--verify-only` exists "precisely because you suspect drift" and to report the full set, and it now reports `SystemExit` per collection.

The new `ProvisionAborted` constants, such as `"the tenancy rule refused the class of 'operators'"`, are **never printed**: `main` prints only the type and the stack.

- Exit codes are unchanged.
- No test pins these printed remedies. `seed_dev_tenant`'s 9 tests are the only pins of this UX, which is why that site was held and these were not.
- Whatever the owner rules for `seed_dev_tenant`, the same rule has to apply to these five handlers.

### D-3 (P2, tier 1) — second-hand text the single-function guard cannot see, in lane-D files

- **`certify_model_profile.py`:** 13 probe helpers build `Probe(…, f"{type(exc).__name__}: {exc}" | str(exc)[:160] …)`, at lines 900, 992, 1088, 1168, 1242/1251/1256, 1370, 1396, 1423, 1438, 1457 and 1490. `print_record` prints them, and `--bank` writes them to JSON. Only `main`'s copy was seeded and converted.
- **`capture_oss_live_fixtures._run_probe`** (REPAIRED — its print was converted): `result["error"] = {"type": …, "message": str(exc)[:500]}` is banked into `tests/fixtures/lang_agent/*.json`, which is committed. This is the exact `str(e)[:500]`-into-a-fixture shape.
- **`seed_dev_tenant`:** `report.warnings` at lines 651 and 664 contain `({exc})` and are printed in the summary.
- **`provision_weaviate_mt.describe`:** `tenants = [f"<unreadable: {exc}>"]`.

### D-4 (P3, tier 1) — over-conversion of values that are not exception text

| site | lost value | what it was |
|---|---|---|
| `reset_demo` [5] | `code` | the portal's HTTP status, an int |
| `manual_sandbox_check` | `exc.reason_code` | a literal vocabulary (`syntax_error`, `blocked_call`, …). Every "blocked" line now reads the same class name, which defeats the check's purpose |
| `manual_sandbox_check` | `exc.name` | the missing module |
| the 12 psycopg2 import guards | ImportError text | whether it was `No module named 'psycopg2'` or a libpq load error |
| `materialize_ad_corpus.run_pair_in_savepoint` | the message | the refusal still says "A 'tenant not found' here means…" but no longer shows the text it refers to. A `casefold()` classification, as `weaviate_boot_check` does, would keep the hint without the text |

### D-5 (P3, tier 1) — `test_provision_rls_class_inference` moved its pin to a place no consumer reads

The test used `match="DEFINES the operator partition"` on the abort message. It now asserts that text on `__cause__`. `provision_rls.main` prints neither the message nor the cause (D-2). The pin is live — mutant D2 kills it — but it proves a property no operator sees.

### Settled for lane D

- **Exit codes are unchanged.**
  - Every changed `SystemExit` keeps a string argument, so the exit is 1 both before and after.
  - The `ABORTED` handlers keep `return 2`.
  - No `return` or `sys.exit` changed in the diff.
- **Conversion shape is correct.**
  - Across 110 (C) and 36 (D) `failure_fields` call sites an AST check found: no loguru call with `extra=`, no stdlib call with `**kwargs` (a runtime TypeError), no duplicate `error_type`/`stack` key, no brace in a loguru message, no f-string loguru message.
  - No nested `except … as exc` shadows an outer name that is used later.
  - No `exc_info`, `opt(exception=)`, `logger.exception` or `format_exc` was added.

---

## Register, seed and scope arithmetic

| check | lane C | lane D |
|---|---|---|
| DEBT keys / sites deleted | 90 / 129 (seed 90/129) | 68 / 101 (seed 69/102) |
| deleted == REPAIRED additions | yes | yes |
| partial lowerings / keys added to DEBT | none / none | none / none |
| another lane's keys touched | none | none |
| keys left | none | `scripts/seed_dev_tenant.py::main` (held) |
| `SEEDED` text, and `SEEDED_SHA256 = 80a7ff66…` in the guard | unchanged; guard file untouched | unchanged; guard file untouched |
| hunks outside repaired functions (`scope_check.py` reuses the guard's own `hunks_outside_repairs`) | `level1.py` 57-59, 62-63, 1376-1378 = the class docstring, `__init__` and `_safe_failure_message`, exactly the approval's reason | only module-level import-guard lines, in **8** approved files, not 5: the three `scripts/ad/*` approvals came with the killed agent's `c5cea97d`. `manual_sandbox_check` has two lines of one `try` |

---

## Merge rehearsal

Run in the scratch clone: `557a178f` + `obs-merge-tbC` → `ad862d21`, then + `obs-merge-tbD` → `797c6898`.

| step | conflict | correct resolution |
|---|---|---|
| +C | `data_discovery/agent/sad_runner.py` imports | keep both: `from utils.observability import failure_fields`, a blank line, then cli's `from ...claude_cli_telemetry import …` |
| +C | register `REPAIRED` | union of lane C's 90 keys and cli's two `purge_llm_turn_content` keys, keeping cli's comment above them |
| +C | scope guard `MRO_POST_MERGE_PRODUCTION_PATHS` | union: cli's M-CLI-TELEMETRY + M-CAPTURE-TRUNCATE block, then lane C's `level1.py` entry |
| +D | `scripts/purge_llm_turn_content.py` | **take obs-merge's side of the whole file.** The cli merge (M-CAPTURE-TRUNCATE) deleted `reap_objects` and `main`'s reap block — the two sites lane D converted. Lane D's `failure_fields` import would be left unused. Lane D's "101/102" therefore lands as 99 conversions plus 2 made moot by deletion. |
| +D | register | set-level: delete lane D's remaining 66 DEBT keys (its 2 purge keys are already gone), add its 66 REPAIRED keys, and do **not** duplicate the two purge keys cli already REPAIRED |
| +D | scope guard | union: the previous block plus lane D's 8 import-guard files |
| +D | `scripts/migrate_tenancy_schema.py` | auto-merged cleanly: cli's `checks()`/`convalidated` and lane D's `main` print are disjoint |

After the rehearsal:
- Merged register against `557a178f`: −156 keys, −228 sites; REPAIRED +156, none removed; only `seed_dev_tenant.py::main` is left in lane D; `SEEDED` is unchanged.
- `MRO_POST_MERGE_PRODUCTION_PATHS` has 135 entries at `557a178f` and **144** after the rehearsal: 135 + 1 (lane C) + 8 (lane D).
- Both guards give 213 passed. The full lane result is in the Lanes table.

**r7b is ordered BEFORE tbA..D (cli → r7b → tbA..D).** `git merge-tree` shows:
- `r7b × tbD` conflicts in `scripts/ad/evaluate_ad_applicability.py`, in `_post_commit_side_effects`' `expected_dispatch_failures` handler:
  - r7b adds `roster_refusal` and `_NO_CLEAN_REPLAY`, and logs `"… failed (%s). " + _NO_CLEAN_REPLAY, type(exc).__name__`;
  - lane D logs the old sentence with `extra=failure_fields(exc)`.
  - **Resolution:** keep r7b's block and text, and add `extra=failure_fields(exc)`. Keep r7b's `(%s)` type in the message, because under this script's `basicConfig` (D-1) that is the only place the type is visible.
- The register also conflicts there. r7b lowered that key from `logger.exception` 5 to 4, and lane D deletes it. **Resolution:** delete it and add it to REPAIRED.
- `tests/unit/ad/test_ad_evaluate_transitions.py` auto-merges but needs a run.
- `r7b × tbC` has no lane-C conflict; only r7b's own `tests/unit/metering/test_usage_ledger_write_guards.py` conflicts.

---

## `seed_dev_tenant.py::main` — evidence on the "authored refusal" question (no ruling)

**For keeping `print(f"ABORTED: {exc}")`:**
- All 9 `raise Aborted(...)` sites, after lane D's `assert_bindable` fix, interpolate only constants and identifiers: database names, environment-variable names, missing-credential names, tenant id, tenant name, domain and user keys. AST check: `aborts.py`.
- The one site that could carry a DSN already prints the type only: line 292, "The exception text is not echoed — it carries the DSN". The author already follows the discipline.
- The messages ARE the remedies, and the 9 tests pin that deliberately: "the remedy is a variable, and the abort names it", "the remedy is named, not left to be deduced", "the abort names both identities", "presence is reported; values are never echoed".
- The script is dev-only (`ALLOWED_DATABASES`) and runs in an operator's terminal.
- The guard still scans every `raise Aborted(f"…{exc}")` at the raise site as `exception-text-in-a-raised-message`: mutant D4 is killed. Keeping the print therefore does not blind the guard to foreign text entering `Aborted`, as long as `Aborted` is raised only within the scanned files.

**Against:**
- The guard's print shape cannot tell authored text from foreign text. A permanent DEBT entry is an exemption that works by name, and the register's anti-gaming design treats DEBT as owed.
- The premise "an abort class carries only authored text" is false for at least one sibling. `MigrationAborted` interpolates `pg_dump` stderr (`migrate_tenancy_schema.py:3715` `{tail}`, `:3822` `{result.stderr}`).
- Two aborts echo customer-entered values: the tenant name ("Someone Else") and a domain.
- If the owner keeps the print, the durable form is a TYPE, not a carve-out. For example, an `AuthoredRefusal` base whose raise sites the guard checks for identifier-only interpolation. That form would also restore D-2's five handlers.

---

## Claims table

**Severity**, my own scale:
- P0 = a content or secret leak the lanes ship;
- P1 = a lost property the lanes claim, or guard integrity;
- P2 = a coverage or contract gap;
- P3 = docs or process, or an operability nit;
- — = none.

**Tier**, per §2.3a:
- 0 = settled by a mutation-checked guard I saw red, on a mechanical decision;
- 1 = consequential but reversible;
- 2 = content, privacy or estate-shaping.

| # | Lane | File:line | Claim (decision taken) | Evidence (command) | Verdict | Severity | Tier | Failure scenario |
|---|---|---|---|---|---|---|---|---|
| C-1 | C | `lambda_functions/s3_pdf_processor_lambda.py:233` et al.; `utils/_loguru_default.py` | Lambda failures are logged "by type and frames" | `probe/lambda_probe.py` at base vs `ece9c60e`: the line becomes `Lambda function error` only | **REFUTED** (the property is absent at the sink) | P1 | 1 | a production ingest failure is undiagnosable from CloudWatch |
| C-2 | C | `data_discovery/service.py:1367` → `takeaways.py:446` → `dashboard/types/data-discovery.ts:287` | `_analyze_level2_context` is REPAIRED | `rg analysis_fallback_reason`; code read | OPEN (pre-existing leak survives in a REPAIRED function) | P2 | 2 | Claude SDK error text on the tenant's public L2 summary |
| C-3 | C | `document_hub/processing.py:221,243,283,306` → `schemas/document_hub.py:360` | DocHub failures stay out of bodies | `rg internal_error` (no stripper); the response models return `metadata` whole | OPEN (pre-existing) | P2 | 2 | parser, S3 or Weaviate error text in `GET /document-hub/documents` |
| C-4 | C | `document_hub/reindex.py:295,648`; `cleanup.py:466` | `_select` is REPAIRED | `scripts/document_hub_reindex.py:_print_item` prints `item.detail` | OPEN | P3 | 1 | S3 or Weaviate error text in a re-index run log |
| C-5 | C | `weaviate_boot_check.py:633-646`; test `:163` | the refusal is a constant; the name travels on the cause | code read; `main.py:139` logs only `error_type` | ASSERTED (the lane's mutant m3 is killed) / operability OPEN | P3 | 1 | the operator cannot tell which collection to restore |
| C-6 | C | `data_discovery/service.py:327-330`; `net_guard.py:99,113,123,135` | the SAD refusal is a constant | code read | OPEN | P3 | 1 | an empty host reads "could not be reached" |
| C-7 | C | `data_discovery/level1.py:1375-1379` | the batch row keeps "the validator's own words" | code read versus `runner.safe_failure_message` | OPEN (pre-existing; the comment overstates) | P3 | 2 | a provider or psycopg2 error text in a batch row (DB only) |
| C-8 | guard | `test_phase1c_nonagent_scope_guard.py:_function_spans` | spans are keyed by qualname | `scope_check.py`: `mro_document_service.py` hunk (165,165) counted as outside | OPEN | P3 | 1 | a property getter's conversion needs an approval it should not |
| C-9 | C | MRO/pilot 500 bodies | `error="Service error"` constant; the 404 mapping is safe | route read; dashboard grep; tests grep | ASSERTED; mutants C2/C5 pending | — | 1 | — |
| C-10 | C | Lambda 400/500 bodies | the refusal is a constant; the 500s are type-only | tests `test_s3_lambda_pins_its_operator.py`; mutants C3/C4 pending | ASSERTED | — | 1 | — |
| C-11 | C | register | 90/129 paid, == REPAIRED, seed unchanged | `regdiff.py` | ASSERTED (guard green) | — | 1 | — |
| C-12 | C | scope `level1.py` | the approval covers exactly its hunks | `scope_check.py` | ASSERTED | — | 1 | — |
| D-1 | D | `scripts/ad/*` (14 calls), `build_referred_by_mapping`, `load_task_hierarchy_locations`, `update_chunks_with_task_hierarchy` (13) | scripts "log a failure by type and frames" | `probe/stdlib_basic.py`, `probe/loguru_default.py` | **REFUTED** at the sink | P1 | 1 | "Dispatch failed", "Failed to update references for a document" — no type, no frames, no id |
| D-2 | D | `create_akasa_solo_tenant.py:1181,1362`; `migrate_tenancy_schema.py:4228`; `provision_rls.py:2045`; `provision_weaviate_mt.py:798`; `migrate_ifim_dynamodb.py:443`; `e2e/figure_arc_headless_e2e.py:202` | an abort prints its type and frames | `aborts.py`; code read | OPEN (owner ruling) | P2 | 1 | the operator cannot learn which role, table or rows failed |
| D-3 | D | `certify_model_profile.py` ×13; `capture_oss_live_fixtures.py:465`; `seed_dev_tenant.py:651,664`; `provision_weaviate_mt.py:494` | lane-D files print no exception text | `rg` over the lane's files; mutant D3 pending | OPEN | P2 | 1 | error text in a certification record or a committed fixture |
| D-4 | D | `reset_demo.py:617`; `manual_sandbox_check.py:22,84`; 12 import guards; `materialize_ad_corpus.py:1024` | non-exception values converted | code read | OPEN | P3 | 1 | the sandbox check cannot say which rule blocked a transform |
| D-5 | D | `tests/unit/db/test_provision_rls_class_inference.py:294,378` | the pin moved to `__cause__` | mutant D2 pending | OPEN | P3 | 1 | the pin proves a property no operator sees |
| D-6 | D | register | 68/101 paid, 1 held, seed unchanged | `regdiff.py` | ASSERTED | — | 1 | — |
| D-7 | D | scope, 8 files | only module-level import guards lie outside repaired functions | `scope_check.py` | ASSERTED | — | 1 | — |
| D-8 | D | all `SystemExit`/`return` | exit codes unchanged | diff scan | SETTLED by reading (no guard) → ASSERTED | — | 1 | — |
| M-1 | merge | see Merge rehearsal | C then D merge onto `557a178f` with 6 mechanical conflicts; purge is taken from obs-merge | scratch `797c6898`; guards 213 passed; full lane all green bar location artifacts | ASSERTED | — | 1 | — |
| M-2 | merge | `scripts/ad/evaluate_ad_applicability.py` | r7b × tbD conflict | `git merge-tree r7b tbD` | OPEN (resolve at merge time) | P3 | 1 | resolving to either side drops r7b's refusal text or lane D's frames |
