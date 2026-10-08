# Client Document Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task.

**Goal:** Deliver a small, provider-neutral document synchronization package that runs COMPLY sources twice daily, publishes verified revisions safely into Copilot MRO, preserves per-document availability through partial failures, and attempts a persisted email report for every completed sync without coupling the feature to Document Hub.

**Architecture:** A new `document-ingestion` Python repository owns provider connectors, schedules, four tenant-scoped state tables, retries, raw-content staging, run classification, and report composition. The existing API automation worker is the composition root and carries each source occurrence on one fenced one-shot `automation_runs` row. Copilot MRO owns a narrow adapter plus one active-revision binding table; revision-qualified S3 and Weaviate artifacts remain invisible until a verified Postgres cutover. There is no connector service, event bus, workflow engine, dashboard, or Document Hub dependency.

**Tech Stack:** Python 3.11, Poetry, Pydantic, HTTPX, PostgreSQL with forced RLS, Flynapse `utils`, the existing automation worker, Copilot MRO parsers, S3, Weaviate, FastAPI for internal administration, Terraform, ECS Fargate, OpenTelemetry, and SMTP.

**Spec:** [`../specs/2026-10-08-client-document-ingestion-design.md`](../specs/2026-10-08-client-document-ingestion-design.md)

## Global Constraints

- Work in the independent repositories under `/Users/ishaanjain/flynapse`; never treat the workspace parent as one Git repository.
- Pause after every phase below. Present the exact diffs, test output, unresolved risks, and proposed next phase before continuing.
- Use test-first changes. Each task starts with the named failing test and ends with the focused suite plus the relevant repository regression lane.
- Preserve unrelated user changes. Do not clean, reset, or rewrite another repository's worktree.
- Do not import Document Hub code, tables, routes, capabilities, or UI. Add an import-boundary test so this remains enforced.
- `document-ingestion` may depend on `flynapse-utils`; it must not depend on `core`, `copilot-mro`, FastAPI, or dashboard code.
- Copilot MRO may depend on the shared contract. The API may depend on both and is the only composition root.
- COMPLY checksum is authoritative. Do not silently use the fallback metadata signal when a COMPLY record lacks a checksum; record the item as parked/failed for the run and surface it in the report.
- One content revision gets an initial attempt plus at most five automatic retries. A newer revision atomically supersedes every older unfinished revision, and the older revision never runs or publishes again.
- A removal is successful when the Copilot adapter has advanced the product fence and made the document non-retrievable. Physical S3/Weaviate cleanup is idempotent, separately tracked, and cannot reactivate the document.
- Advance a source checkpoint only after a complete fixed window is durably staged. Advance a source schedule only after its one-shot occurrence is durably enqueued.
- Do not activate a production COMPLY source until the client supplies the deletion-record shape and confirms stable document IDs, checksum format/requiredness, and filtered-pagination ordering/snapshot behavior.
- The first activation supports only document families whose Copilot parser mapping and mandatory output stores have been explicitly verified.
- The first release assigns one operator to one source. A client corpus shared by several operators is represented by several source configurations; do not add operator fan-out to the runner.
- Use the shared API Poetry environment for cross-repository tests and prefix Copilot tests with `DEBUG=false`.

## Review Focus

Review each phase specifically for:

1. lossless checkpoint movement and idempotent schedule enqueue;
2. stale-worker and stale-revision fencing;
3. tenant/operator isolation in Postgres and Weaviate;
4. truthfulness of Copilot success receipts;
5. no visibility window during update or removal;
6. mutually exclusive run counts and the exact 5% boundary;
7. credential, signed-URL, and content redaction;
8. dependency direction and absence of Document Hub coupling;
9. mixed-version deployment and rollback safety; and
10. whether a proposed abstraction is needed for COMPLY plus one test connector now.

## Implementation baselines and branch discipline

These code baselines were inspected on 2026-10-08 and were clean. Before Task 1, fetch and confirm that the named branch is still the approved latest-code baseline, then create an isolated feature branch/worktree in each repository that the current phase changes. Do not commit cross-repository work to a workspace-root Git history.

| Repository | Approved starting branch | Inspected commit |
|---|---|---|
| `api` | `langgraph-merge` | `44f7684c6410cb12f0e56f3aec6b4561efb1969a` |
| `core` | `master` | `a653c4758f5fe10206baf8594ed548de9c3d12cb` |
| `copilot-mro` | `langgraph-merge` | `a8d4f8768bc25a573617f71dc8ca6648d37d2aad` |
| `iac` | `main` | `a772a0af05ee831651c3b13e3259a8b0f6c54e48` |
| `utils` | `langgraph-merge` | `9c36bba16dd82c505d272141c6b35f18c3c6be16` |

`utils` is a consumed dependency and is not expected to change. The new `document-ingestion` repository needs its remote/default branch and protection confirmed before its first push; do not invent those values in code or scripts.

---

## Frozen implementation decisions

### Persistence and execution

- The shared package owns exactly four relations: `document_ingestion_sources`, `document_ingestion_documents`, `document_ingestion_revisions`, and `document_ingestion_runs`.
- All four declare `tenancy="tenant"`, receive tenant-leading keys and forced RLS from the existing table framework, and are read only inside an explicit tenant binding.
- The tables contain no lease or active-run claim. The existing `automation_runs` one-shot row remains the only source-run claim, recovery record, and execution fence.
- `document_ingestion_runs.run_id` is the carrier `automation_runs.run_id`; do not mint a second run identity.
- Each revision stores a monotonic per-document ordinal plus the carrier run/attempt that currently owns processing. Both shared settlement and Copilot publication compare all of them, so a timed-out worker or late revision cannot publish after recovery, overwrite a newer upsert, or resurrect a removed document.
- A run with a trustworthy scan has non-null counts and one of `completed`, `partially_completed`, or `needs_attention`. An untrustworthy scan is `failed` and its document counts are null rather than invented.

### Schedule claim

- Add optional `dedupe_key` and `concurrency_key` fields to the generic one-shot primitive. The occurrence dedupe key covers `(tenant_id, kind, dedupe_key)` and remains unique after a run is terminal; the source concurrency key covers `(tenant_id, kind, concurrency_key)` only while a row is `claimed` or `running`.
- A scheduled ingestion occurrence uses `document-ingestion:<source_id>:<scheduled_for-utc>` as its dedupe key and `document-ingestion:<source_id>` as its concurrency key. A manual run uses a fresh `manual:<uuid>` occurrence key but the same source concurrency key.
- The due pass calls `ensure_one_shot_run(...)`, then compare-and-set advances `sources.next_run_at` from that exact due instant to the next future local slot. A crash between those actions safely finds the same run on the next tick and completes the schedule advance.
- If a different occurrence for that source is still active, enqueue returns `busy` with the blocking run ID and leaves the later schedule due. The first tick after the active run closes enqueues one catch-up occurrence and advances to the next future slot.
- Recovery from several missed slots enqueues once and computes the next future slot; it never replays all missed slots.

### Product publication

- Copilot adds one tenant+operator relation, `copilot_client_document_bindings`, keyed by `(tenant_id, operator_id, source_id, external_document_id)`.
- The binding stores the highest applied ordinal, lifecycle (`active` or `removed`), active revision/product document IDs, and pending-purge identity. The applied ordinal remains after removal so an older retry cannot reactivate the document.
- Product IDs and storage/index prefixes are deterministic and revision-qualified, for example `client_<revision_uuid_hex>`.
- Parsing first produces local output only. S3 and Weaviate receive revision-qualified staged artifacts. Query-visible Postgres rows, catalog replacement, and binding cutover occur in one Postgres transaction after mandatory artifacts verify.
- Managed Weaviate objects carry source, external document, revision, ordinal, managed, and publication-state properties. Retrieval excludes staged objects before top-k and post-filters published managed results against the binding. Legacy objects remain unaffected.
- The adapter returns `ProductReceipt` only after the cutover is verified. For removal it first advances the binding to `removed` and deletes query-visible Postgres/catalog rows in one transaction; residual S3 and Weaviate purge can then retry independently.
- Immediately before binding cutover, the adapter calls the shared `PublicationFence` on the same Postgres cursor. That check locks the shared document/revision rows and proves the revision is still current and owned by this carrier run/attempt; there is no check-then-publish race.

### Reporting and cleanup

- Current-run `added`, `changed`, `removed`, and `failed` counts include only actionable revisions attempted in that run. Unchanged observations are excluded.
- `removed` is counted after logical removal, not after physical purge.
- The email contains a separate unresolved backlog section for retryable, exhausted, parked, and cleanup-pending revisions; those counts do not alter the current-run failure percentage.
- One best-effort email attempt is made after every terminal ingestion run and its result is persisted. Email failure does not change ingestion status.
- The 48-hour value initially marks old bytes cleanup-eligible. Physical deletion stays disabled until the client's retention requirement is confirmed; object-store lifecycle remains the physical-erasure authority meanwhile.

## Phase map

| Phase | Outcome | Repositories |
|---|---|---|
| 1 | Shared contracts, state schema, and generic idempotent one-shot enqueue | `document-ingestion`, `core`, `copilot-mro` migration scripts |
| 2 | Lossless COMPLY enumeration, scheduling, runner, retries, content staging, and reports | `document-ingestion` |
| 3 | Copilot MRO staged publication, visibility fencing, removal, and cleanup receipts | `copilot-mro` |
| 4 | Worker composition, platform-admin control plane, audit, and lifecycle wiring | `api`, `core` |
| 5 | Package closure, standalone worker deployment, acceptance fixture, and controlled activation | `api`, `copilot-mro`, `iac`, `docs` |

## Phase 1 — Shared foundation and execution claim

### Task 1: Scaffold the shared repository and freeze its public contract

**Files:**

- Create `document-ingestion/pyproject.toml`
- Create `document-ingestion/README.md`
- Create `document-ingestion/document_ingestion/__init__.py`
- Create `document-ingestion/document_ingestion/contracts.py`
- Create `document-ingestion/document_ingestion/models.py`
- Create `document-ingestion/document_ingestion/errors.py`
- Create `document-ingestion/document_ingestion/connectors/__init__.py`
- Create `document-ingestion/document_ingestion/connectors/registry.py`
- Create `document-ingestion/tests/unit/test_models.py`
- Create `document-ingestion/tests/unit/test_status.py`
- Create `document-ingestion/tests/unit/test_dependency_direction.py`

**Contract:**

- Define `SourceConnector.enumerate_changes(...)` and `download(...)` without provider branching in the runner.
- Define `ProductDocumentConsumer.ingest(...)`, `remove(...)`, and `cleanup(...)`.
- Define `PublicationFence.assert_publishable(cursor, context)`; the shared repository implements it and the Copilot adapter must invoke it inside the final product transaction.
- Define immutable `SourceConfig`, `SyncWindow`, `ChangeRecord`, `RevisionWorkItem`, `DownloadedDocument`, `ProductExecutionContext`, `ProductReceipt`, `ProductRemovalReceipt`, and `RunSummary` models.
- `ProductExecutionContext` carries tenant, one operator ID, source, external document, revision ID, revision ordinal, carrier run ID, and carrier attempt.
- `ProductRemovalReceipt` distinguishes `logical_removal_applied` from `purge_complete`; the runner treats only the former as the removal success boundary.
- Define closed enums for provider operation, revision/apply state, document lifecycle, cleanup state, report state, and the four run statuses.
- Limit runtime dependencies to Pydantic, HTTPX, Loguru, and `flynapse-utils`. The test must fail if the package imports `core`, `copilot_mro`, FastAPI, or any Document Hub module.

**TDD:**

1. Write boundary tests for 0 failures, exactly 5%, and greater than 5%, plus the zero-actionable case.
2. Write serialization/validation tests for checksum form, non-empty external ID, 24–48 hour retention, distinct schedule times, and immutable execution identity.
3. Run `poetry run pytest tests/unit/test_models.py tests/unit/test_status.py tests/unit/test_dependency_direction.py -q`; expect import/model failures.
4. Implement only the models, protocols, status calculator, and static registry required to pass.
5. Run `poetry run pytest tests/unit -q` and `poetry run mypy document_ingestion`.

**Commit:** `feat: define document ingestion contracts`

### Task 2: Add the four shared tables and register their tenancy

**Files:**

- Create `document-ingestion/document_ingestion/persistence/__init__.py`
- Create `document-ingestion/document_ingestion/persistence/table_definitions.py`
- Create `document-ingestion/tests/unit/test_table_definitions.py`
- Create `document-ingestion/tests/db/conftest.py`
- Create `document-ingestion/tests/db/test_rls_isolation.py`
- Create `document-ingestion/tests/db/test_tenant_cascade.py`
- Modify `copilot-mro/scripts/migrate_tenancy_schema.py`
- Modify `copilot-mro/scripts/provision_rls.py`
- Modify `copilot-mro/tests/unit/db/test_migration_targets.py`
- Modify `copilot-mro/tests/unit/db/test_migration_declared_column_shape.py`
- Modify `copilot-mro/tests/unit/db/test_provision_rls_class_inference.py`
- Modify `copilot-mro/tests/db/tenancy/test_schema_conformance.py`

**Schema:**

- `sources`: source/client/display identity, immutable provider-source key, tenant, one operator ID, product key, opaque `product_config`, connector type/config, secret reference, two local schedule times, timezone, `next_run_at`, enabled/decommissioning state, recipients, retention, checkpoint, config revision, and created/updated actor/time.
- `documents`: `(source_id, external_document_id)`, lifecycle, current revision/ordinal, active revision/ordinal, current signal, current provider metadata, and active product receipt.
- `revisions`: revision identity/ordinal, operation and stable change key, checksum/provider metadata, classification (`added|changed|removed`), apply state, processing owner run/attempt, attempt count, bounded failure code/summary, product receipt, raw storage key, supersession, and cleanup eligibility/request/completion state.
- `runs`: carrier run ID/attempt, source and scheduled occurrence, fixed window/checkpoints, scan trust state, nullable outcome counts, separate backlog counts, bounded failure summary, report delivery result, next run, and timings.
- Enforce unique `(tenant_id, source_id, external_document_id, change_key)` revisions and ordered retry indexes that require the revision to remain the document's current target.
- Add tenant foreign keys with cascade, but do not interpret database cascade as sufficient product-artifact erasure.
- Register `document-ingestion` after `core` in tenancy migration/provisioning so the tenant parent exists first.

**TDD:**

1. Make registry tests fail because the four definitions and fourth registry are absent.
2. Make live disposable-Postgres tests fail for cross-tenant reads/writes, invalid state values, duplicate change keys, and tenant cascade.
3. Implement table definitions and registry wiring.
4. From `api`, run `DEBUG=false poetry run pytest ../document-ingestion/tests/unit/test_table_definitions.py ../copilot-mro/tests/registries -q`.
5. Against a throwaway database, run `DEBUG=false poetry run pytest ../document-ingestion/tests/db/test_rls_isolation.py ../document-ingestion/tests/db/test_tenant_cascade.py -m postgres -q`.
6. Dry-run both migration scripts with registry set `core,copilot-mro,shift-optimizer,document-ingestion`; inspect that all four tables are tenant-scoped and FORCE RLS.

**Commits:**

- `document-ingestion`: `feat: define ingestion persistence schema`
- `copilot-mro`: `feat: register ingestion tenancy schema`

### Task 3: Make one-shot enqueue idempotent by occurrence and exclusive by source

**Files:**

- Modify `core/core/db/table_definitions.py`
- Modify `core/core/resources/automations/models/schemas.py`
- Modify `core/core/resources/automations/services/automation_store.py`
- Modify `core/core/resources/automations/postgres_init.py` if its schema/preflight assertions pin the column set
- Modify `core/tests/db/automations/test_automation_tables.py`
- Modify `core/tests/db/automations/test_one_shot_runs.py`
- Modify `api/tests/unit/automations/test_store_call_signatures.py`
- Modify `core/tests/unit/automations/test_run_traceparent_carrier.py` if the selected column list is pinned there

**Behavior:**

- Add nullable `automation_runs.dedupe_key` and `automation_runs.concurrency_key`.
- Add a unique occurrence index on tenant, kind, and dedupe key for every non-null key, regardless of terminal state, plus a partial unique active-source index on tenant, kind, and concurrency key for `claimed|running` rows.
- Keep `enqueue_one_shot_run(...)` backward compatible.
- Add `ensure_one_shot_run(..., dedupe_key=..., concurrency_key=...) -> OneShotEnqueue(state, run_id, blocking_run_id)` with closed states `created`, `existing`, and `busy`.
- On conflict, read the existing row under the same tenant and verify kind, source payload identity, operator context, and scheduled occurrence. Return it only when it is the same logical job; otherwise fail loudly.
- Preserve the existing `claimed -> running` take, stale recovery, attempt increment, trace link, and `started_at`-fenced close.

**TDD:**

1. Add concurrent DB tests proving two producers receive one run ID for one occurrence.
2. Prove a terminal row still deduplicates that same occurrence, a different occurrence is `busy` while the source's first run is active, and it can enqueue after the first run closes.
3. Prove another source can run concurrently and that scheduled versus manual runs for one source cannot overlap.
4. Prove calls without either key retain one-call/one-run behavior.
5. From `api`, run `DEBUG=false poetry run pytest ../core/tests/db/automations/test_one_shot_runs.py ../core/tests/db/automations/test_automation_tables.py -m postgres -q`.
6. Run `DEBUG=false poetry run pytest ../core/tests/unit/automations -q`.

**Commit:** `feat: support idempotent one-shot enqueue`

### Task 4: Implement the repository state machines and schedule calculation

**Files:**

- Create `document-ingestion/document_ingestion/persistence/repository.py`
- Create `document-ingestion/document_ingestion/scheduling.py`
- Create `document-ingestion/tests/unit/test_scheduling.py`
- Create `document-ingestion/tests/db/test_repository.py`
- Create `document-ingestion/tests/db/test_checkpoint_atomicity.py`
- Create `document-ingestion/tests/db/test_revision_state_machine.py`
- Create `document-ingestion/tests/db/test_processing_fence.py`

**Behavior:**

- Compute the two daily local slots with `zoneinfo`, including DST fold/gap behavior, and return the next future UTC instant.
- Expose a due occurrence with exact `scheduled_for`, dedupe key, and `next_run_at`; do not mutate the schedule until the caller supplies the durable carrier run ID.
- Compare-and-set advance `next_run_at` only from the occurrence that was enqueued.
- `stage_complete_window(...)` locks the source, verifies the old checkpoint, inserts/deduplicates every normalized change, assigns increasing per-document ordinals, supersedes older unfinished revisions, records scan completion, and advances the checkpoint in one transaction.
- A newer revision changes older `staged`, `processing`, `retryable`, `exhausted`, or `parked` revisions to `superseded`; every claim and settle operation also checks that the revision remains current.
- Claim a revision with carrier run ID and attempt. Settlement is a compare-and-set on revision, current target, carrier ID, and carrier attempt.
- Implement `assert_publishable(cursor, context)` as a locking check of the same revision/current-target/carrier fence for use inside the Copilot binding transaction.
- Cap attempts at six total. Queries never return superseded or exhausted work.
- Preserve the active revision/receipt when a changed revision fails. Tombstone lifecycle only after the product removal receipt confirms logical removal.

**TDD:**

1. Start with failing schedule tests for both local times, DST, on-time slots, multi-slot outage catch-up, and no replay.
2. Add failing transaction tests for a crash/exception on the last staged record and a competing checkpoint writer; neither may move the checkpoint.
3. Add failing race tests: old processing attempt versus recovered attempt, old failed revision versus newer revision, upsert versus later removal, and stale upsert after removal.
4. Implement the minimum repository and pure schedule functions.
5. Run unit tests, then the four DB files against a disposable Postgres database.

**Commit:** `feat: persist fenced ingestion state`

**Phase 1 review gate:** Stop. Verify schema/RLS, state transitions, schedule enqueue invariants, and the generic one-shot change before connector or product work begins.

## Phase 2 — COMPLY connector and shared runner

### Task 5: Implement lossless COMPLY enumeration and secure downloads

**Files:**

- Create `document-ingestion/document_ingestion/connectors/comply.py`
- Create `document-ingestion/document_ingestion/connectors/signed_url_client.py`
- Create `document-ingestion/tests/fixtures/comply/changes_page_*.json`
- Create `document-ingestion/tests/fixtures/comply/download_links_mixed.json`
- Create `document-ingestion/tests/fixtures/comply/deletion_record.json` only when the client supplies the real shape
- Create `document-ingestion/tests/unit/test_comply_connector.py`
- Create `document-ingestion/tests/unit/test_signed_url_client.py`

**Behavior:**

- The first scan uses no time filters and must read every declared page. Incremental scans use inclusive start/end filters and a fixed end equal to run start.
- Request at most 100 change rows per page and at most 50 download links per POST.
- Start page-number pagination at the documented zero-based page `0`.
- Normalize a confirmed full `sha256:<64 hex>` value to lowercase hex. A missing checksum is `missing_required_checksum`; an abbreviated, malformed, or wrong-algorithm value is `invalid_required_checksum`. Both are per-document parked/failed outcomes, never fallback signals or prefix checks.
- Deduplicate exact boundary records by external ID plus stable change key; refuse contradictory records sharing that key.
- Validate page number, page size, total pages/count, non-empty progress, and a stable response shape. Treat any inconsistency as an untrustworthy scan and leave the checkpoint unchanged.
- Map deletion only from the client's supplied deletion field. Never infer deletion from absence.
- Resolve the bearer token through the injected secret resolver. The API client and download client share no bearer/cookie state.
- Signed downloads require HTTPS and an allowlisted host, revalidate every redirect, reject userinfo/IP literals/private/link-local resolutions, use bounded timeouts, stream through a hard byte cap, and never log or persist the URL/query.
- Fetch a fresh signed link on expiry; do not cache one beyond the immediate attempt.

**TDD:**

1. Use HTTPX mock transports for zero-based pagination, inclusive duplicates, mutable totals, truncated pages, mixed link results, 50-ID batching, expiry refresh, size overflow, redirect, malformed/abbreviated checksum, and checksum mismatch.
2. Prove the bearer header reaches only the COMPLY API origin.
3. Prove logs and raised public errors contain neither token nor signed URL.
4. Run `poetry run pytest tests/unit/test_comply_connector.py tests/unit/test_signed_url_client.py -q`.
5. Leave the deletion-mapping test skipped with one explicit client-contract reason until the fixture arrives; production activation cannot waive it.

**Commit:** `feat: add secure COMPLY connector`

### Task 6: Implement raw-content staging, the sync runner, cleanup state, and reports

**Files:**

- Create `document-ingestion/document_ingestion/storage.py`
- Create `document-ingestion/document_ingestion/runner.py`
- Create `document-ingestion/document_ingestion/cleanup.py`
- Create `document-ingestion/document_ingestion/reporting.py`
- Create `document-ingestion/tests/unit/test_storage.py`
- Create `document-ingestion/tests/unit/test_runner.py`
- Create `document-ingestion/tests/unit/test_cleanup.py`
- Create `document-ingestion/tests/unit/test_reporting.py`
- Create `document-ingestion/tests/integration/test_fake_connector_end_to_end.py`

**Behavior:**

- `run_source_sync(...)` begins/resumes the run by carrier run ID and attempt, enumerates the complete window, stages it atomically, then processes only current actionable revisions independently.
- Download into a bounded temporary file, verify size and checksum, persist under a tenant/source/revision-qualified raw-content key, and pass a short-lived local path plus stored-content receipt to the product adapter.
- Same-checksum observations update metadata but create no content revision and invoke no download or adapter.
- The same-checksum shortcut applies only while the document is active. An `UPSERT` after `removed` creates a higher-ordinal revision and reingests it, preventing the tombstone from swallowing a legitimate reappearance.
- Process one document failure without rolling back neighboring successes or changing source enabled state.
- Process actionable revisions through a configurable bounded semaphore; preserve independent outcomes without starting unbounded parser/index work during a large initial import.
- Retry only current retryable revisions; the sixth failed total attempt becomes exhausted.
- Treat `ProductReceipt` as the upsert success boundary and `logical_removal_applied` as the removal success boundary.
- Mark superseded/removed raw content cleanup-eligible at the configured time. Keep physical deletion execution behind a default-off switch until the client retention SLA is confirmed.
- Calculate mutually exclusive counts and the four run statuses. Persist failure summaries as bounded codes/sanitized text.
- Compose one report with current-run counts, status, next schedule, concise failures, and separate retryable/exhausted/parked/cleanup backlog. Attempt delivery once and persist sent/failed independently of ingestion status.
- Claim report delivery with a run-row compare-and-set before sending, so a recovered carrier attempt cannot send the same terminal report twice.

**TDD:**

1. Add runner cases for initial full scan, zero changes, unchanged active checksum, add, update success, update failure retaining old receipt, removal logical success with purge pending, same-checksum resurrection after removal, checksum mismatch, mixed 4%/5%/>5% failures, and failed listing.
2. Add supersession tests where revision N is processing or retryable when N+1 arrives; N must lose both settle and product-call eligibility.
3. Use a second fake connector in the integration test and assert the runner contains no COMPLY type check.
4. Run `poetry run pytest tests/unit tests/integration/test_fake_connector_end_to_end.py -q`.
5. Run `poetry run mypy document_ingestion`.

**Commit:** `feat: run and report document syncs`

**Phase 2 review gate:** Stop. Review the COMPLY wire contract, checkpoint proof, security boundary, status math, retry/supersession behavior, and report examples. Do not start Copilot changes until the shared contract is accepted.

## Phase 3 — Copilot MRO publication safety

### Task 7: Add the product binding and retrieval visibility gate

**Files:**

- Create `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/client_document_ingestion.py`
- Modify `copilot-mro/copilot_mro/app/db/postgres_table_definitions.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/__init__.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/models.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/repository.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/visibility.py`
- Modify `copilot-mro/copilot_mro/app/services/llama_index/llama_index_query.py`
- Modify `copilot-mro/copilot_mro/app/services/agent_shared/tools/retrieval/_amos_weaviate.py`
- Modify `copilot-mro/copilot_mro/app/services/agent_shared/tools/retrieval/chunk_fetch.py` only if it must pass visibility context not already held by the query service
- Modify `copilot-mro/scripts/provision_weaviate_mt.py`
- Create `copilot-mro/tests/unit/client_document_ingestion/test_repository.py`
- Create `copilot-mro/tests/unit/retrieval/test_client_document_visibility.py`
- Create `copilot-mro/tests/integration/client_document_ingestion/test_visibility_cutover.py`
- Modify `copilot-mro/tests/registries/tables/test_postgres_table_definitions.py`
- Modify `copilot-mro/tests/registries/tenancy/test_tenancy_classifications.py`
- Modify `copilot-mro/tests/registries/tenancy/test_tenancy_declaration.py`

**Behavior:**

- Define `copilot_client_document_bindings` as tenant+operator, with applied revision/ordinal, lifecycle, active revision/product ID, purge identity/state, and timestamps.
- Repository transitions return explicit `activated`, `already_active`, `removed`, or `superseded_by_newer` outcomes and use ordinal compare-and-set after the shared publication fence succeeds on the same transaction cursor.
- Add non-searchable Weaviate properties for managed/source/external/revision/ordinal/publication state.
- Pre-filter staged managed objects out of search before top-k. Post-filter every managed search/direct-fetch result against the binding and fail closed for managed results if the binding cannot be read; legacy objects remain available.
- Cover hybrid/vector/BM25/filter queries plus direct single- and multi-chunk retrieval.
- Run a real-Weaviate contract test for legacy objects with absent managed/publication properties. If the chosen null predicate is not supported, migrate legacy objects to `managed=false` before enabling the query filter; do not guess.

**TDD:**

1. Make table/tenancy tests fail on the missing binding.
2. Make visibility tests fail for staged revision leakage, old published revision after cutover, stale upsert after removal, accepted higher-ordinal resurrection, wrong operator partition, and binding-store failure.
3. Implement schema, repository, and central visibility helper; route every retrieval entrance through it.
4. From `api`, run the focused unit/registry tests with `DEBUG=false`.
5. Run the real-Weaviate legacy-null contract only against a user-provided disposable test collection.

**Commit:** `feat: gate client document visibility`

### Task 8: Build the strict Copilot adapter, atomic cutover, removal, and receipts

**Files:**

- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/parser_adapter.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/artifacts.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/consumer.py`
- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/composition.py`
- Modify `copilot-mro/copilot_mro/app/services/parsers/pdf_parser.py`
- Modify `copilot-mro/copilot_mro/app/services/llama_index/llama_index_ingestion.py`
- Modify `copilot-mro/copilot_mro/app/services/doc_catalog.py`
- Create `copilot-mro/tests/unit/client_document_ingestion/test_parser_adapter.py`
- Create `copilot-mro/tests/unit/client_document_ingestion/test_artifacts.py`
- Create `copilot-mro/tests/unit/client_document_ingestion/test_consumer.py`
- Create `copilot-mro/tests/integration/client_document_ingestion/test_product_cutover.py`
- Create `copilot-mro/tests/integration/client_document_ingestion/test_product_removal.py`

**Behavior:**

- Add an optional document-ID override and a local-only/strict-write seam to the existing parser path; preserve every existing caller's behavior.
- Do not route the new adapter through `S3PDFProcessor.process_single_pdf()` or trust current top-level success booleans. Reuse parser/chunk/index logic through narrow calls and make mandatory write failures propagate.
- Inventory the exact S3 keys, catalog row, structured Postgres tables/rows, chunk IDs, Weaviate collection/partition/object count for each supported parser family before declaring it supported.
- Before changing a family-specific parser, stop and amend this task's file list with the exact confirmed parser module and test path. The client document-family mapping is an activation prerequisite, so this plan must not guess those files.
- Stage revision-qualified S3 and Weaviate output, verify S3 manifest/size and Weaviate batch/object counts, promote Weaviate objects to `published`, then execute one Postgres transaction that locks/verifies the shared publication fence, replaces the old query-visible product rows, writes catalog/chunks, and advances the binding.
- Return a deterministic receipt containing all artifact identities and counts only after re-reading the active binding and mandatory representations.
- On retry after cutover, recognize the already-active deterministic revision, re-verify it, and return the same receipt.
- Removal atomically advances the ordinal fence to `removed`, clears the active pointer, and deletes current query-visible Postgres/catalog/chunk rows. Verify retrieval is blocked before returning logical success.
- Purge revision-qualified Weaviate objects and S3 prefixes idempotently after retention eligibility, recording per-store counts. Purge failure never changes the removed lifecycle.

**TDD:**

1. Start with failure-injection tests for S3 partial upload, catalog failure, structured-row failure, chunk failure, Weaviate batch error, verification mismatch, pointer CAS loss, timed-out stale carrier attempt, and post-cutover retry.
2. Prove no receipt is returned before all mandatory representations and the binding verify.
3. Prove a failed update leaves the prior active document searchable and a staged new document invisible.
4. Prove removal blocks hybrid search, direct chunk fetch, and catalog/DB discovery before S3/Weaviate purge succeeds.
5. From `api`, run `DEBUG=false poetry run pytest ../copilot-mro/tests/unit/client_document_ingestion ../copilot-mro/tests/unit/retrieval/test_client_document_visibility.py -q`.
6. Run the two integration files against disposable Postgres/Weaviate/S3-compatible fixtures, then the non-live Copilot regression lane.

**Commit:** `feat: publish client document revisions safely`

**Phase 3 review gate:** Stop. Inspect one real receipt, one failed-update trace, one cutover, and one failed-purge removal. Confirm all agent retrieval doors honor the binding before worker composition.

## Phase 4 — Worker composition and administration

### Task 9: Wire due-source production and the source-sync one-shot handler

**Files:**

- Create `api/flynapse_api/automations/document_ingestion_jobs.py`
- Modify `api/flynapse_api/automations/loop.py`
- Modify `api/flynapse_api/automations/worker.py`
- Modify `api/flynapse_api/config/config.py`
- Create `api/tests/unit/automations/test_document_ingestion_jobs_handler.py`
- Create `api/tests/integration/automations/test_document_ingestion_due_enqueue.py`
- Create `api/tests/integration/automations/test_document_ingestion_one_shot_dispatch.py`
- Modify `api/tests/integration/automations/test_worker_entrypoint.py`
- Modify `api/tests/integration/automations/test_one_shot_dispatch_isolation.py`

**Behavior:**

- Register `document_ingestion_sync` in the existing one-shot feature wiring. The handler ABI remains keyword-only `tenant_id`, `user_id`, `params`, `attempt`, and `run_id`.
- Add one lazy due-producer call before the one-shot scan on each tick. It uses the existing paged tenant registry, binds one tenant, reads a bounded due-source batch, ensures the occurrence run, then compare-and-set advances the source schedule.
- Pass the source's single operator as a one-element `operator_ids` list on the one-shot row so the existing dispatcher binds tenant+operator before the handler calls Copilot.
- Compose connector registry, repository, content store, Copilot consumer, secret resolver, and SMTP report sender in this API module only.
- A global `DOCUMENT_INGESTION_ENQUEUE_ENABLED` switch controls new enqueueing but not handler registration, so rollback stops new work while already-claimed rows can drain.
- Add bounded `DOCUMENT_INGESTION_DOCUMENT_CONCURRENCY` and `DOCUMENT_INGESTION_RUN_MAX_SECONDS` settings. The due producer passes the latter to the one-shot row; the activation runbook records values proven by the fixture rather than hiding an unreviewed constant in code.
- Extend worker boot preflight to require the four shared tables and the Copilot binding table; create none at boot.

**TDD:**

1. Prove two ticking processes enqueue one occurrence, a crash before schedule CAS is repaired, a later occurrence waits behind an active run of the same source, a missed schedule queues once after that run closes, and different tenants cannot see each other's sources.
2. Prove the handler receives the carrier attempt and operator binding, persists the summary in `document_ingestion_runs`, and lets the carrier row record only whether the handler itself completed.
3. Prove enqueue-disable stops new rows but still serves an existing claimed ingestion row.
4. From `api`, run all four focused tests, then the existing one-shot and worker-entrypoint suites.

**Commit:** `feat: run client ingestion from automation worker`

### Task 10: Add the minimal platform-admin control plane and lifecycle hooks

**Files:**

- Create `api/flynapse_api/auth/platform_admin.py`
- Create `api/flynapse_api/routers/document_ingestion_admin.py`
- Create `api/flynapse_api/services/document_ingestion_admin.py`
- Create `api/flynapse_api/services/document_ingestion_lifecycle.py`
- Modify `api/flynapse_api/main.py`
- Modify `api/flynapse_api/partition_wiring.py`
- Modify `copilot-mro/copilot_mro/app/services/operator_teardown.py`
- Modify `copilot-mro/copilot_mro/app/services/tenant_teardown.py`
- Modify `core/core/db/authorization_events.py`
- Modify `core/tests/unit/db/test_authorization_event_writer.py`
- Modify `core/tests/unit/db/test_authorization_events_registry.py`
- Create `api/tests/unit/auth/test_platform_admin.py`
- Create `api/tests/integration/document_ingestion/test_admin_routes.py`
- Create `api/tests/integration/document_ingestion/test_admin_audit.py`
- Create `api/tests/integration/document_ingestion/test_source_decommission.py`
- Modify `copilot-mro/tests/unit/operator_teardown/test_operator_teardown_erase.py`
- Modify `copilot-mro/tests/unit/operator_teardown/test_operator_teardown_relations.py`
- Modify `copilot-mro/tests/unit/tenancy/test_tenant_teardown_credentials.py`

**Behavior:**

- Require the signed ID-token claim `cognito:groups` to contain the configured Flynapse staff group. Tenant-owner or settings-admin roles alone receive 403.
- Expose no dashboard. Provide minimal internal create/read/update, enable/disable, connector-validation dry run, manual-run, retry-reset, and decommission operations. The validation path may authenticate and enumerate bounded fixture/live pages but cannot stage records or advance schedule/checkpoint state.
- Permit schedule, recipients, secret reference, connector config, and product config updates with optimistic `config_revision`. After first run, reject tenant, operator, product key, connector type, and provider identity changes.
- Rebind to the target tenant only after the platform-admin gate succeeds; every repository call remains RLS-scoped.
- Add `ingestion_source` to the existing authorization-event vocabulary. In one transaction, write each mutation and its actor/reason/before/after configuration to the source row plus `authorization_events`.
- Decommission disables scheduling and logically removes current documents through one-shot work; it never hard-deletes history first.
- Register ingestion as an explicit tenant/operator erasure step. Erasure retention rules override normal revision retention: final identity deletion waits for logical removal plus verified raw/product cleanup, or remains `needs_attention` in the existing erasure ledger. Never cascade away the only cleanup receipt and then claim cleanup can continue.

**TDD:**

1. Prove no token, ordinary user, tenant owner, and tenant settings admin are denied; only the configured staff group passes.
2. Prove a platform admin may target another tenant only through the audited service and cannot bypass immutable identity fields.
3. Prove mutation and audit event commit or roll back together.
4. Prove decommission and tenant/operator teardown preserve tombstones/cleanup receipts until product visibility is blocked.
5. Run the focused API tests and affected core authorization-event tests.

**Commits:**

- `core`: `feat: audit ingestion source administration`
- `copilot-mro`: `feat: include client documents in lifecycle teardown`
- `api`: `feat: add ingestion administration controls`

**Phase 4 review gate:** Stop. Review the exact admin authorization claim, cross-tenant binding, audit records, teardown behavior, and absence of any dashboard/Document Hub change.

## Phase 5 — Packaging, deployment, and activation

### Task 11: Add the new repository to the package and image closure

**Files:**

- Modify `api/pyproject.toml`
- Modify `api/poetry.lock`
- Modify `copilot-mro/pyproject.toml`
- Modify `copilot-mro/poetry.lock`
- Modify `iac/scripts/build_api_image.sh`
- Modify `iac/scripts/api_image.Dockerfile` only if its dependency-closure comments/tests require it
- Modify `iac/tests/unit/demo_box/test_demo_box_api_image.py`
- Modify `api/tests/conftest.py`
- Modify `api/tests/unit/infra/test_checkout_variant_pin.py`
- Modify `api/tests/unit/infra/test_cross_repo_reads_name_their_checkout.py`

**Behavior:**

- Name the distribution `flynapse-document-ingestion` and module `document_ingestion`.
- Add the sibling path dependency to API and Copilot MRO for the current workspace/build model.
- Add `document-ingestion=<commit>` to the committed-source image staging list, usage, labels, and path-dependency closure check.
- Keep the image immutable by commit tags and prove uncommitted shared-package files cannot enter it.
- Establish the remote repository and branch protection before the first shared commit is pushed; do not invent a remote or default branch during implementation.

**TDD:**

1. Make the image-closure test fail on the new path dependency.
2. Update manifests/locks and build-script assertions.
3. From `api`, run `poetry check`, the import-boundary tests, and focused package tests.
4. From `iac`, run the demo-box image tests and the build script's non-network validation path.

**Commits:**

- `api`: `build: add document ingestion package`
- `copilot-mro`: `build: depend on document ingestion contract`
- `iac`: `build: stage document ingestion in api image`

### Task 12: Deploy the existing worker as one background service

**Files:**

- Create `iac/automation_worker.tf`
- Modify `iac/variables.tf`
- Modify `iac/dev.tfvars`
- Modify `iac/cognito.tf`
- Modify `iac/apprunner.tf`
- Modify `iac/apprunner_iam.tf` or extract shared runtime/task policies into a clearly named common file
- Modify `iac/ec2.tf` and `iac/elasticache.tf` for worker security-group access to Postgres, Weaviate, Phoenix, OTLP, and Redis
- Modify `iac/cloudwatch.tf`
- Modify `iac/alarms.tf`
- Create `iac/tests/unit/automation_worker/test_automation_worker_service.py`
- Modify `iac/README.md`

**Behavior:**

- Create one ECS Fargate cluster/service using the existing API image with command `python -m flynapse_api.automations.worker`; do not create an ingestion-specific service or fake HTTP listener.
- Run one desired task initially in a public subnet with a public IP for COMPLY/AWS egress, no inbound rule, and only the required database/vector-store/collector security-group paths. Do not add a NAT gateway solely for this worker.
- Give the execution role ECR/log/declared runtime-secret access and the task role least-privilege S3 plus `GetSecretValue` for an explicit list of connector secret ARNs.
- Create the configured `platform_admin` Cognito group in the internal/default user pool; user membership remains an explicit operator action and is never inferred from tenant roles.
- Share the API's non-secret runtime map rather than copy a drifting second list. Set API scheduler mode to `off` and worker mode to `worker` in the same deployment.
- Keep ingestion enqueue disabled on the first worker deploy. Enable existing worker liveness/error alarms only after logs prove `service.name=automation-worker` and five-minute liveness records.
- Migration and RLS verification must complete before the worker task starts.

**TDD and validation:**

1. Add static tests for desired count, command, network exposure, scheduler modes, secret references, task/execution role separation, log group, and alarm gate.
2. Run `terraform fmt -check`, `terraform validate`, and the focused IaC unit tests.
3. Review `terraform plan` for exactly one worker service, no public listener, API scheduler off, required SG additions, and alarms gated correctly.
4. Deploy with enqueue disabled; verify boot preflights, liveness logs, OTLP identity, DB/Weaviate access, and clean SIGTERM drain.

**Commit:** `feat: deploy standalone automation worker`

### Task 13: Prove the end-to-end acceptance path and enable one source

**Files:**

- Create `api/tests/e2e/document_ingestion/test_comply_fixture_sync.py`
- Create `api/tests/e2e/document_ingestion/test_worker_recovery.py`
- Create `api/tests/e2e/document_ingestion/test_mixed_document_outcomes.py`
- Create `docs/runbooks/client-document-ingestion.md`
- Update `docs/superpowers/specs/2026-10-08-client-document-ingestion-design.md` only if client answers change a parked contract

**Acceptance fixture:**

- Use a fake COMPLY server with paginated initial data, unchanged checksum, changed checksum, one deletion, one download failure, one checksum mismatch, and a newer revision that supersedes an older failure.
- Run due source → one one-shot row → complete-window stage/checkpoint → Copilot adapter → report.
- Prove successful documents are queryable while neighbors fail; failed update retains its old active answer; removed document is immediately absent while purge is forced to fail; older failed revision never reruns after the newer revision.
- Kill the worker after enqueue, during download, before product cutover, and after cutover. Prove recovery reuses the occurrence/run, fences stale settlement, and sends at most one terminal report attempt.
- Verify report counts/status at 0%, 5%, and >5% plus separate unresolved/cleanup backlog.

**Activation order:**

1. Obtain and commit sanitized client fixtures for deletion and all required metadata; record stable-ID, checksum, and pagination confirmations in the runbook.
2. Run all non-live suites, disposable Postgres RLS/schema suites, and disposable Weaviate/S3-compatible integration suites.
3. Apply additive tables/columns/indexes and Weaviate properties with enqueue disabled.
4. Deploy retrieval gates, Copilot adapter, API wiring, and the worker; verify legacy retrieval unchanged.
5. Create one disabled COMPLY source through the platform-admin route and run a manual dry-run/list-only validation that cannot advance the checkpoint.
6. Enable one low-risk tenant/operator source, reconcile the first receipt against Postgres/S3/Weaviate, and verify the report email.
7. Observe two scheduled runs, including one with a controlled document failure, before expanding.
8. Keep physical cleanup disabled until retention behavior is confirmed; then enable it separately and verify object-version semantics.

**Verification commands:**

From `api`:

```bash
DEBUG=false poetry run pytest ../document-ingestion/tests/unit -q
DEBUG=false poetry run pytest ../document-ingestion/tests/integration -q
DEBUG=false poetry run pytest tests/unit/automations/test_document_ingestion_jobs_handler.py -q
DEBUG=false poetry run pytest tests/integration/automations/test_document_ingestion_due_enqueue.py -q
DEBUG=false poetry run pytest tests/integration/automations/test_document_ingestion_one_shot_dispatch.py -q
DEBUG=false poetry run pytest ../copilot-mro/tests/unit/client_document_ingestion -q
DEBUG=false poetry run pytest ../copilot-mro/tests/unit/retrieval/test_client_document_visibility.py -q
DEBUG=false poetry run pytest ../copilot-mro/tests/integration/client_document_ingestion -q
```

Against a disposable Postgres database:

```bash
DEBUG=false poetry run pytest ../document-ingestion/tests/db -m postgres -q
DEBUG=false poetry run pytest ../core/tests/db/automations/test_one_shot_runs.py -m postgres -q
DEBUG=false poetry run pytest ../core/tests/db/automations/test_automation_tables.py -m postgres -q
```

Run the full non-live Copilot regression lane last:

```bash
DEBUG=false poetry run pytest ../copilot-mro/tests -m "not db and not postgres and not corpus_live and not weaviate_live and not compose_stack and not live_agent_state and not live_browser_server" -q
```

**Commits:**

- `api`: `test: prove client ingestion acceptance path`
- `docs`: `docs: add client ingestion runbook`

**Phase 5 review gate:** Stop before enabling the production source. Present client contract evidence, full test results, migration/RLS verification, Terraform plan/deploy evidence, one disabled-source dry run, rollback readiness, and the exact activation change.

## Mixed-version and rollback plan

1. Expand Postgres and Weaviate first. New nullable `automation_runs.dedupe_key`/`concurrency_key`, new tables, indexes, and properties are safe for older API/workers.
2. Deploy retrieval gates before any managed object can be written. Legacy-object behavior must be proven first.
3. Deploy the capable worker with enqueue disabled. Older workers ignore an unregistered kind, but the environment must never enqueue ingestion work when no capable worker is present.
4. Stop new work by disabling ingestion enqueue and sources; let claimed rows drain or be recovered by the existing one-shot reaper.
5. Preserve shared tables, binding rows, checkpoints, tombstones, receipts, and the one-shot dedupe column during rollback. Never roll a checkpoint backward or remove a tombstone automatically.
6. Before binding cutover, rollback deletes revision-qualified staged artifacts. After cutover, repoint to the previous receipt only if every retained artifact re-verifies; otherwise reingest.
7. Do not automatically undo a provider removal. Resurrection requires a later, higher-ordinal UPSERT or an explicit audited administrator action after client confirmation.
8. Physical cleanup is the last irreversible action and remains separately enabled. Once prior artifacts are physically purged, rollback requires reingestion.

## Final self-review checklist

- Every goal and acceptance criterion in the approved spec maps to at least one task and test above.
- The COMPLY connector is the only provider-specific production module; the fake connector proves runner neutrality.
- Product-specific parsing/indexing stays in Copilot MRO; shared code carries only protocols and receipts.
- Source-run occurrence dedupe/active-source exclusion, document processing fence, and product publication fence are separate and each has a race test.
- Initial import is a complete listing but not an all-or-nothing publication gate.
- `removed` means non-retrievable, while cleanup state reports physical residue honestly.
- Exactly five automatic retries means six total attempts.
- Run counts exclude unchanged documents and inactive backlog; the report still exposes unresolved backlog.
- Platform-admin authorization is server-side, staff-only, cross-tenant, and audited.
- The deploy uses one existing automation-worker process, not one service per connector.
- Production activation remains blocked on the four named COMPLY contract confirmations and supported parser mapping.
