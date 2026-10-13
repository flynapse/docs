# Client Document Ingestion Implementation Plan

Status: **Approved plan, amended through 2026-10-12** to keep product revision behavior in Copilot MRO, reuse
existing persistence, reconcile the completed Task 5 implementation with the authoritative COMPLY File Share
contract, and carry the automation worker's native `started_at` execution fence through shared and product-side
writes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking. Update the status checklist and append implementation notes, learnings, and post-review changes under the task that produced them.

**Goal:** Deliver a small, provider-neutral document synchronization package that runs COMPLY sources twice daily, publishes verified revisions safely into Copilot MRO, preserves per-document availability through partial failures, and attempts a persisted email report for every completed sync without coupling the feature to Document Hub.

**Architecture:** A new `document-ingestion` Python repository owns provider connectors, schedules, two tenant-scoped source-state tables, retries, raw-content staging, run classification, and report composition. The existing API automation worker is the composition root and carries each source occurrence, summary, and report-delivery state on one fenced one-shot `automation_runs` row. Copilot MRO owns its parser-specific revision, publication, visibility, removal, and rollback strategy and reuses its existing document stores wherever possible. There is no connector service, event bus, workflow engine, dashboard, or Document Hub dependency.

**Tech Stack:** Python 3.11, Poetry, frozen dataclasses and typing protocols, HTTPX/httpcore, PostgreSQL with forced RLS, Flynapse `utils`, the existing automation worker, Copilot MRO parsers, S3, Weaviate, FastAPI for internal administration, Terraform, ECS Fargate, OpenTelemetry, and SMTP.

**Spec:** [`../specs/2026-10-08-client-document-ingestion-design.md`](../specs/2026-10-08-client-document-ingestion-design.md)

## Global Constraints

- Work in the independent repositories under `/Users/ishaanjain/flynapse`; never treat the workspace parent as one Git repository.
- Pause after every phase below. Present the exact diffs, test output, unresolved risks, and proposed next phase before continuing.
- Use test-first changes. Each task starts with the named failing test and ends with the focused suite plus the relevant repository regression lane.
- Preserve unrelated user changes. Do not clean, reset, or rewrite another repository's worktree.
- Do not import Document Hub code, tables, routes, capabilities, or UI. Add an import-boundary test so this remains enforced.
- `document-ingestion` may depend on `flynapse-utils`; it must not depend on `core`, `copilot-mro`, FastAPI, or dashboard code.
- Copilot MRO may depend on the shared contract. The API may depend on both and is the only composition root.
- COMPLY checksum is authoritative for `new` and `updated` records. Do not silently use the fallback metadata signal when an active COMPLY record lacks a complete canonical checksum; record the item as parked/failed for the run and surface it in the report. A `deleted` record may omit checksum and still maps authoritatively to `REMOVED`.
- Treat the 2026-10-09 vendor guide plus its live UAT Swagger schema as the authoritative COMPLY wire contract: use `/qp-fileshare-service/api/comply/documents/changes` and `/qp-fileshare-service/api/comply/documents/download-links`; map required status `new|updated` to `UPSERT` and `deleted` to `REMOVED`; never infer deletion from absence.
- One content revision gets an initial attempt plus at most five automatic retries. A newer revision atomically supersedes every older unfinished revision, and the older revision never runs or publishes again.
- A removal is successful when the Copilot adapter confirms that the document is no longer retrievable under the product's selected removal strategy. Physical product-store cleanup is idempotent, separately tracked, and cannot reactivate the document.
- Phase 3 must inventory and reuse Copilot MRO's existing document relations, catalog, chunks, parser-specific relations, S3 layouts, and Weaviate objects. Add product schema only when that assessment proves a concrete invariant cannot be met otherwise.
- Advance a source checkpoint only after a complete fixed window is durably staged. Advance a source schedule only after its one-shot occurrence is durably enqueued.
- Do not activate a production COMPLY source until the client confirms stable document IDs across revisions, active-document checksum format/requiredness, and filtered-pagination snapshot behavior. Newest-first ordering and the deletion-record shape are resolved by the authoritative contract and must be verified by contract tests.
- The first activation supports only document families whose Copilot parser mapping and mandatory output stores have been explicitly verified.
- The first release assigns one operator to one source. A client corpus shared by several operators is represented by several source configurations; do not add operator fan-out to the runner.
- Run standalone `document-ingestion` tests from its own installed dev environment. Use the shared API Poetry environment for cross-repository tests and prefix Copilot tests with `DEBUG=false`.
- Before Task 11 installs the sibling package into API, prefix API-hosted ingestion tests with `PYTHONPATH=../document-ingestion`; remove that temporary path prefix after the declared dependency is installed.

## Review Focus

Review each phase specifically for:

1. lossless checkpoint movement and idempotent schedule enqueue;
2. stale-worker and stale-revision fencing;
3. tenant/operator isolation in Postgres and Weaviate;
4. truthfulness of the product-defined operation outcome;
5. no visibility window during update or removal;
6. mutually exclusive run counts and the exact 5% boundary;
7. credential, signed-URL, and content redaction;
8. dependency direction and absence of Document Hub coupling;
9. mixed-version deployment and rollback safety; and
10. whether a proposed abstraction is needed for COMPLY plus one test connector now.

## Implementation baselines and branch discipline

These local baselines and feature branches were rechecked on 2026-10-10. Fetch and confirm each tracked base is still the approved latest-code baseline before changing that repository; if it moved, review the incoming diff before rebasing or merging. Do not commit cross-repository work to a workspace-root Git history.

| Repository | Approved base | Feature branch | Rechecked commit |
|---|---|---|---|
| `api` | `langgraph-merge` | `doc-ingestion-pipeline` | `44f7684c6410cb12f0e56f3aec6b4561efb1969a` |
| `core` | `master` | `doc-ingestion-pipeline` | `a653c4758f5fe10206baf8594ed548de9c3d12cb` |
| `copilot-mro` | `langgraph-merge` | `doc-ingestion-pipeline` | `e429a8ba920b1e591d49d112addbf0ae369e312f` |
| `iac` | `main` | `doc-ingestion-pipeline` | `a772a0af05ee831651c3b13e3259a8b0f6c54e48` |
| `docs` | `main` | `doc-ingestion-pipeline` | `6c93b8da81f17ed701bbd34c263cb88a306988ac` |
| `utils` | `langgraph-merge` | no feature branch expected | `9c36bba16dd82c505d272141c6b35f18c3c6be16` |
| `document-ingestion` | local repository | `doc-ingestion-pipeline` | `a9babc1f8de41c26eb94ca40302a6951058e1de9` |

`utils` is a consumed dependency and is not expected to change. The new `document-ingestion` repository has no configured remote; its remote, default branch, and protection must be agreed before its first push rather than invented in code or scripts.

---

## Frozen implementation decisions

### Persistence and execution

- The shared package adds exactly two relations: `document_ingestion_sources` and `document_ingestion_revisions`.
- Both declare `tenancy="tenant"`, receive tenant-leading keys and forced RLS from the existing table framework, and are read only inside an explicit tenant binding.
- `document_ingestion_revisions` holds both document identity and source-level revision history. A partial unique constraint permits exactly one current row for `(tenant_id, source_id, external_document_id)`; same-signal metadata updates that row instead of creating a new content revision.
- The new tables contain no lease or active-run claim. The existing `automation_runs` one-shot row remains the only source-run claim, recovery record, execution fence, and run-summary record; do not add `document_ingestion_documents`, `document_ingestion_runs`, or a second run identity.
- Existing `automation_runs.params` carries source/occurrence context. Existing `automation_runs.result` carries the fixed window, business status, counts, bounded failures/backlog, next schedule, and report-delivery state.
- Keep the generic `automation_runs.status` as the carrier's technical lifecycle (`claimed`, `running`, `completed`, `failed`, `timed_out`, and existing variants). Store the agreed ingestion outcome separately as `automation_runs.result.document_ingestion.status`; do not add the four business values to the generic status column. A handled untrustworthy scan reports business `failed`, attempts its email, and returns normally so the carrier may close technically `completed`. Only an unhandled executor/boot failure closes the carrier technically failed or timed out.
- Each source revision stores a monotonic per-document ordinal plus the carrier run, attempt, and `started_at` execution fence that currently own processing. Shared claims and settlement compare the current-row flag, ordinal, carrier run, attempt, and execution fence. The retry number is not a unique execution identity: stale recovery can briefly leave two workers inside one attempt namespace. Product publication ordering is owned and tested by the product adapter, not by a shared publication fence.
- A run with a trustworthy scan has non-null counts and one of `completed`, `partially_completed`, or `needs_attention`. An untrustworthy scan is `failed` and its document counts are null rather than invented.

### Schedule claim

- Add optional `dedupe_key` and `concurrency_key` fields to the generic one-shot primitive. The occurrence dedupe key covers `(tenant_id, kind, dedupe_key)` and remains unique after a run is terminal; the source concurrency key covers `(tenant_id, kind, concurrency_key)` only while a row is `claimed` or `running`.
- A scheduled ingestion occurrence uses `document-ingestion:<source_id>:<scheduled_for-utc>` as its dedupe key and `document-ingestion:<source_id>` as its concurrency key. A manual run uses a fresh `manual:<uuid>` occurrence key but the same source concurrency key.
- The due pass calls `ensure_one_shot_run(...)`, then compare-and-set advances `sources.next_run_at` from that exact due instant to the next future local slot. A crash between those actions safely finds the same run on the next tick and completes the schedule advance.
- If a different occurrence for that source is still active, enqueue returns `busy` with the blocking run ID and leaves the later schedule due. The first tick after the active run closes enqueues one catch-up occurrence and advances to the next future slot.
- Recovery from several missed slots enqueues once and computes the next future slot; it never replays all missed slots.

### Product revision and publication

- Phase 3 changes only `copilot-mro`. It begins with an evidence-backed inventory of the existing `mro_documents`, `pilot_documents`, `crew_documents`, `chunks`, parser-specific relations, catalog behavior, S3 layouts, and Weaviate objects for each supported parser family.
- Copilot MRO chooses and owns the revision, idempotency, stale-execution, publication, visibility, removal, cleanup, and rollback rules that fit each parser family. The shared package neither implements nor prescribes them.
- The shared execution context supplies source ID, external document ID, source revision ID and ordinal, carrier run ID, carrier attempt, and the carrier take's `started_at` execution fence. Copilot uses that context to reject stale work under its selected product-side strategy; the attempt remains useful for retry diagnostics but is never treated as the unique worker fence.
- No binding table, active pointer, revision-qualified artifact layout, Weaviate property set, or cutover transaction is predetermined. Reuse existing product storage first; add the smallest product-owned column or relation only if the Phase 3 assessment demonstrates a missing invariant.
- The adapter returns a closed success/failure/removal outcome plus opaque product data only after the product's own mandatory representations and retrieval guarantees have been verified. The shared runner does not interpret product artifact identities.

### Reporting and cleanup

- Current-run `added`, `changed`, `removed`, and `failed` counts include only actionable revisions attempted in that run. Unchanged observations are excluded.
- `removed` is counted after logical removal, not after physical purge.
- The email contains a separate unresolved backlog section for retryable, exhausted, parked, and cleanup-pending revisions; those counts do not alter the current-run failure percentage.
- One best-effort email attempt is made after every terminal ingestion run and its result is persisted. Email failure does not change ingestion status.
- The 48-hour value initially marks old bytes cleanup-eligible. Physical deletion stays disabled until the client's retention requirement is confirmed; object-store lifecycle remains the physical-erasure authority meanwhile.

## Phase map

| Phase | Outcome | Repositories |
|---|---|---|
| 1 | Shared contracts, two-table source state, and generic idempotent one-shot enqueue | `document-ingestion`, `core`, `api` tests, `copilot-mro` migration scripts |
| 2 | Authoritative COMPLY contract reconciliation, lossless enumeration, scheduling, runner, retries, content staging, and reports | `document-ingestion` |
| 3 | Copilot MRO storage assessment and product-owned revision, publication, visibility, and logical removal; physical cleanup deferred | `copilot-mro` |
| 4 | Worker composition, platform-admin control plane, audit, and lifecycle wiring | `api`, `core`, `copilot-mro` |
| 5 | Package closure, standalone worker deployment, acceptance fixture, and controlled activation | `api`, `copilot-mro`, `iac`, `docs` |

## Current implementation status

- [x] **Task 1** — Implemented and independently reviewed in the uncommitted `document-ingestion` working tree over baseline `a9babc1`; no commit was created under the review-before-commit policy.
- [x] **Task 2** — Implemented and independently reviewed in the uncommitted `document-ingestion` and `copilot-mro` working trees; no `utils` change was required.
- [x] **Task 3** — Implemented and independently reviewed in the uncommitted `core` and `api` working trees.
- [x] **Task 4** — Implemented and independently reviewed after two focused fix rounds in the uncommitted `document-ingestion` working tree.
- [x] **Task 5** — Implemented and reviewed in `document-ingestion` commit `a9babc1`; its original routes and skipped deletion assumption are historical and are superseded by mandatory Task 5A.
- [x] **Task 5A** — Implemented, independently reviewed, and approved after one documentation-only fix round; no commit was created.
- [x] **Task 6** — Implemented and independently approved after four focused fix rounds plus the Phase 2 whole-diff review; no commit was created. One non-blocking parked-observation deduplication optimization remains deferred before large-scale activation.
- [x] **Task 7** — Product storage/retrieval assessment independently accepted after five focused review rounds;
  exact Task 8 files, state machine, test obligations and activation prerequisites are locked.
- [x] **Task 8** — Offline MVP implemented, independently tested, and accepted after three focused fix rounds.
  Copilot now owns AMM/SRM parsing, generation-qualified mandatory artifacts, exact publication/visibility,
  logical removal, and product-side revision fencing; Core retains only an opaque cache-version seam and shared
  ingestion retains only generic exact-final-carrier settlement. The 2026-10-13 MVP ruling removes automated
  physical cleanup, durable provider-call admission and rollback orchestration from Phase 3. Production activation
  remains gated on client-approved fixtures and target S3/Weaviate acceptance. No commit was created.
- [ ] **Task 9** — Not started.
- [ ] **Task 10** — Not started.
- [ ] **Task 11** — Not started; the local `document-ingestion` repository still needs its remote/default branch and protection before first push.
- [ ] **Task 12** — Not started.
- [ ] **Task 13** — Not started; production activation remains gated by the named client confirmations.

## Phase 1 — Shared foundation and execution claim

### Task 1: Scaffold the shared repository and freeze its public contract

**Implementation status (2026-10-11): Complete and independently reviewed; uncommitted.**

**Implementation notes:**

- Finalized the `flynapse-document-ingestion` distribution while preserving the `document_ingestion` import module and Task 5's connector API.
- Added immutable shared models, the four narrow injected protocols, exact run-status classification, and an explicit static connector registry without product, API, Dashboard, FastAPI, or Document Hub dependencies.
- Added a terminal `ReportDeliveryResult`; its optional diagnostic is sanitized and bounded at 500 characters. Independent review accepted that as the minimal enforceable interpretation of the agreed bounded-result contract.
- `errors.py` and `connectors/base.py` required no edits because the reviewed Task 5 implementation already satisfied this task's error and connector contracts. `signed_url_client.py` received only two type declarations needed for the new mypy gate; runtime behavior is unchanged.
- The shared model originally required checksum for every operation because the deletion contract was unknown. Task 5A now owns the narrowly scoped nullable-checksum change for `REMOVED`; `UPSERT` checksum enforcement remains unchanged.

**Post-review verification (2026-10-11):**

- `poetry check` completed successfully.
- `poetry run pytest -p no:cacheprovider -q` completed with **79 passed and 1 skipped**.
- `poetry run mypy --cache-dir=/private/tmp/doc-ingestion-task1-controller-mypy document_ingestion` completed with **no issues in 9 source files**.
- `git diff --check` completed successfully. Independent re-review reported no Critical, Important, or Minor findings.

**Files:**

- Modify `document-ingestion/pyproject.toml`
- Create `document-ingestion/poetry.lock`
- Create `document-ingestion/README.md`
- Modify `document-ingestion/document_ingestion/__init__.py`
- Create `document-ingestion/document_ingestion/contracts.py`
- Modify `document-ingestion/document_ingestion/models.py`
- Modify `document-ingestion/document_ingestion/errors.py`
- Modify `document-ingestion/document_ingestion/connectors/base.py`
- Modify `document-ingestion/document_ingestion/connectors/__init__.py`
- Create `document-ingestion/document_ingestion/connectors/registry.py`
- Create `document-ingestion/tests/unit/test_models.py`
- Create `document-ingestion/tests/unit/test_status.py`
- Create `document-ingestion/tests/unit/test_dependency_direction.py`

**Contract:**

- Preserve the implemented provider-neutral `DocumentConnector.enumerate_changes(...)` and `download_documents(...)` interface in `connectors/base.py`; do not introduce a competing `SourceConnector` name or break Task 5 callers.
- Define awaitable `ProductDocumentConsumer.ingest(*, document: ProductDocumentInput, context: ProductExecutionContext) -> ProductOperationOutcome`, `remove(*, context: ProductExecutionContext, provider_metadata: Mapping[str, object]) -> ProductOperationOutcome`, and `cleanup(*, context: ProductExecutionContext, opaque_product_data: Mapping[str, object]) -> ProductOperationOutcome` operations so bounded document concurrency does not block the worker event loop.
- Define only the two other infrastructure boundaries the runner needs: an awaitable `RawContentStore` that persists/deletes revision-qualified content and returns `StoredContentReceipt`, and an awaitable `ReportSender` that sends one already-composed report and returns a closed delivery result. Keep S3/SMTP implementation details in the API composition root or a narrow shared adapter, not in the domain contracts.
- Define an injected `RunResultStore` protocol with synchronous compare-and-set operations `persist_summary(run_id, attempt, execution_started_at, summary) -> bool`, `claim_report_delivery(run_id, attempt, execution_started_at) -> bool`, and `finish_report_delivery(run_id, attempt, execution_started_at, result) -> bool`. The API adapter implements them against a row that is still `running` with that exact `started_at`; `attempt` remains diagnostic and must not replace the timestamp fence. The shared runner must not import `core` or know the `automation_runs` implementation.
- Preserve Task 5's immutable `NormalizedChange`, `EnumerationResult`, `DownloadedDocument`, and `DownloadBatch` dataclasses. `DownloadedDocument` remains the connector's bounded in-memory transfer result.
- Add immutable `SourceConfig`, `SyncWindow`, `RevisionWorkItem`, `StoredContentReceipt`, `ProductDocumentInput`, `ProductExecutionContext`, `ProductOperationOutcome`, and `RunSummary` dataclasses. `ProductDocumentInput` carries the short-lived local path, normalized metadata, and `StoredContentReceipt` passed to the product adapter; it is distinct from `DownloadedDocument`.
- `ProductExecutionContext` carries tenant, one operator ID, source, external document, revision ID, revision ordinal, carrier run ID, carrier attempt, and immutable `carrier_started_at`.
- `ProductOperationOutcome` has a closed operation result and opaque product payload. A removal succeeds only when the closed result confirms `non_retrievable`; product-specific receipt fields, revision semantics, and cleanup mechanics remain opaque.
- Define closed enums for provider operation, source-revision/apply state, cleanup eligibility, report state, product operation result, and the four ingestion business statuses. Name the last type `IngestionRunStatus` so it cannot be confused with the generic automation carrier status.
- Rename the bootstrap distribution from `document-ingestion` to the final `flynapse-document-ingestion` name while keeping the import module `document_ingestion`.
- Retain the implemented standard-library logging and frozen-dataclass model style. Do not add a second logging or model framework without a demonstrated need.
- Keep runtime dependencies to the standard library, HTTPX/httpcore, and `flynapse-utils` only when first consumed. Add pytest and mypy as development dependencies. The boundary test must fail if the package imports `core`, `copilot_mro`, Dashboard, FastAPI, the API package, or any Document Hub module.

**TDD:**

- [x] **Step 1:** Update the manifest, lock dependencies, and install the development environment with `poetry lock` followed by `poetry install --with dev`.
- [x] **Step 2:** Write boundary tests for 0 failures, exactly 5%, and greater than 5%, plus the zero-actionable case.
- [x] **Step 3:** Write serialization/validation tests for checksum form, non-empty external ID, 24–48 hour retention, distinct schedule times, immutable execution identity, and compatibility with Task 5's existing connector models.
- [x] **Step 4:** Run `poetry run pytest tests/unit/test_models.py tests/unit/test_status.py tests/unit/test_dependency_direction.py -q`; expect import/model failures.
- [x] **Step 5:** Implement only the models, protocols, status calculator, static registry, and manifest changes required to pass.
- [x] **Step 6:** Run `poetry run pytest tests/unit -q` and `poetry run mypy document_ingestion`; the existing Task 5 connector/download tests must remain green.

**Commit:** `feat: define document ingestion contracts`

No Task 1 commit has been created yet; review completed against the uncommitted working tree as requested.

### Task 2: Add the two shared tables and register their tenancy

**Implementation status (2026-10-12): Complete and independently reviewed; uncommitted.**

**Implementation notes:**

- Added exactly `document_ingestion_sources` and `document_ingestion_revisions` through the shared table-builder path, with tenant-leading keys/indexes, forced tenant RLS, source/revision cascades, closed lifecycle checks, one-current-row enforcement, and source-local current-only retry ordering.
- Persisted the source business owner as `source_operator_id` while preserving `SourceConfig.operator_id` as the domain/API name. This keeps business ownership distinct from the reserved RLS `operator_id` axis and avoids a shared `utils` classifier exception.
- Registered `document-ingestion` immediately after `core` in migration and provisioning discovery. No ingestion documents/runs table or second run identity was introduced, and `automation_runs` remains unchanged.
- Added the portable editable `flynapse-utils` sibling dependency at its first production use. No `utils` source file changed.
- Independent GPT-5.6 Sol `xhigh` review reported no Critical, Important, or Minor findings and approved the task. The reviewer accepted the zero-write provisioner verification as sufficient for Task 2: it found zero RLS enforcement violations and no ingestion finding, while its nonzero exit came only from unrelated security objects absent from the schema-only scratch database.

**Post-review verification (2026-10-12):**

- `poetry check`, the complete `document-ingestion` unit suite, mypy, and `git diff --check` passed: **85 passed, 1 deliberate skip**, and **no type issues in 11 source files**.
- The required cross-repository registry lane passed: **201 passed** with five pre-existing SWIG deprecation warnings.
- The named Copilot migration/provision unit lane passed: **203 passed** with five pre-existing SWIG deprecation warnings.
- Live disposable-Postgres isolation/state/uniqueness/cascade tests passed: **7 passed**.
- Full schema conformance passed: **89 passed, 1 expected xfail**.
- No Task 2 commit was created; Task 1 and Task 2 remain stacked but file-scoped and independently reviewed.

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

- `sources`: source/client/display identity, immutable provider-source key, tenant, one operator ID stored as `source_operator_id` (mapped to the domain/API field `SourceConfig.operator_id`), product key, opaque `product_config`, connector type/config, secret reference, two local schedule times, timezone, `next_run_at`, enabled/decommissioning state, recipients, retention, checkpoint, config revision, and created/updated actor/time. The non-reserved storage name keeps business ownership distinct from the shared RLS `operator_id` axis.
- `revisions`: source/document identity, revision identity/ordinal, operation and stable change key, checksum/provider metadata, classification (`added|changed|removed`), `is_current`, apply state, processing owner run/attempt/`started_at`, attempt count, bounded failure code/summary, opaque product outcome, raw storage key, supersession, and cleanup eligibility/request/completion state.
- Enforce unique `(tenant_id, source_id, external_document_id, change_key)` revisions plus a partial unique current-row constraint on `(tenant_id, source_id, external_document_id) WHERE is_current`. Ordered retry indexes require the revision to remain current.
- Store same-signal metadata changes on the current revision row without creating a new content revision.
- Reuse `automation_runs.params` and `automation_runs.result` for occurrence context and the fixed-window/run/report summary. Do not define a documents table, ingestion run table, or second run identifier.
- Add tenant foreign keys with cascade, but do not interpret database cascade as sufficient product-artifact erasure.
- Register `document-ingestion` after `core` in tenancy migration/provisioning so the tenant parent exists first.

**TDD:**

- [x] **Step 1:** Make registry tests fail because the two shared definitions and ingestion registry are absent.
- [x] **Step 2:** Make live disposable-Postgres tests fail for cross-tenant reads/writes, invalid state values, duplicate change keys, and tenant cascade.
- [x] **Step 3:** Implement table definitions and registry wiring.
- [x] **Step 4:** From `api`, run `PYTHONPATH=../document-ingestion DEBUG=false poetry run pytest ../document-ingestion/tests/unit/test_table_definitions.py ../copilot-mro/tests/registries -q`.
- [x] **Step 5:** Against a throwaway database, run `DEBUG=false poetry run pytest ../document-ingestion/tests/db/test_rls_isolation.py ../document-ingestion/tests/db/test_tenant_cascade.py -m postgres -q`.
- [x] **Step 6:** Dry-run both migration scripts with registry set `core,copilot-mro,shift-optimizer,document-ingestion`; inspect that both new tables are tenant-scoped and FORCE RLS and that no ingestion documents/runs table is emitted.

**Commits:**

- `document-ingestion`: `feat: define ingestion persistence schema`
- `copilot-mro`: `feat: register ingestion tenancy schema`

### Task 3: Make one-shot enqueue idempotent by occurrence and exclusive by source

**Implementation status (2026-10-12): Complete and independently reviewed; uncommitted.**

**Implementation notes:**

- Added nullable generic occurrence and source-concurrency keys plus tenant-leading one-shot-only unique indexes. The legacy enqueue path remains one-call/one-run; the new helper returns closed `created`, `existing`, or `busy` outcomes and lets PostgreSQL arbitrate producer races.
- Canonicalized occurrence identity using PostgreSQL JSONB equality and the tenancy binder's sorted/deduplicated operator-set semantics. Independent review initially found both identity gaps; Fix Round 1 added real-Postgres regressions and resolved them without changing public signatures.
- Added generic exact-`started_at` fenced summary/report compare-and-set helpers and preserved namespaced results through normal close. The API dispatcher passes the take's exact fence to every one-shot handler, and all existing handler families remain compatible.
- Independent GPT-5.6 Sol `xhigh` review approved Fix Round 1 with all findings addressed and no new Critical or Important breakage. No commit was created.

**Post-review verification (2026-10-12):**

- Live PostgreSQL automation schema/concurrency/fence lane: **51 passed**.
- Complete core automation unit lane: **256 passed**; the traceparent file passes **15/15** in isolation.
- Affected API one-shot compatibility suites: **43 passed** with six pre-existing checkout/SWIG warnings.
- The exact combined-order comparison remains **269 passed, 2 failed**, matching the pre-Task 3 baseline failures in the same two OpenTelemetry exporter assertions; no telemetry code changed.
- `git diff --check` passed in both repositories. Focused typing checks for the additions passed; repository-wide formatting/type baselines remain pre-existing and unchanged.

**Files:**

- Modify `core/core/db/table_definitions.py`
- Modify `core/core/resources/automations/models/schemas.py`
- Modify `core/core/resources/automations/services/automation_store.py`
- Modify `core/core/resources/automations/postgres_init.py` if its schema/preflight assertions pin the column set
- Modify `core/tests/db/automations/test_automation_tables.py`
- Modify `core/tests/db/automations/test_one_shot_runs.py`
- Modify `api/tests/unit/automations/test_store_call_signatures.py`
- Modify `api/flynapse_api/automations/one_shot.py`
- Modify `api/tests/integration/automations/test_one_shot_dispatch.py`
- Modify `core/tests/unit/automations/test_run_traceparent_carrier.py` if the selected column list is pinned there

**Behavior:**

- Add nullable `automation_runs.dedupe_key` and `automation_runs.concurrency_key`.
- Add a unique occurrence index on tenant, kind, and dedupe key for every non-null definitionless one-shot key, regardless of terminal state, plus a partial unique active-source index on tenant, kind, and concurrency key for definitionless one-shot rows in `claimed|running`. Both predicates must explicitly require `automation_id IS NULL` and the one-shot trigger so definition-backed automation rows are unaffected.
- Keep `enqueue_one_shot_run(...)` backward compatible.
- Add `ensure_one_shot_run(..., dedupe_key=..., concurrency_key=...) -> OneShotEnqueue(state, run_id, blocking_run_id)` with closed states `created`, `existing`, and `busy`.
- On conflict, read the existing row under the same tenant and verify kind, source payload identity, operator context, and scheduled occurrence. Return it only when it is the same logical job; otherwise fail loudly.
- Preserve the existing `claimed -> running` take, stale recovery, attempt increment, trace link, and `started_at`-fenced close.
- Extend the generic one-shot handler ABI with keyword-only `execution_started_at`, sourced from `OneShotTake.started_at`. The currently registered production handlers already tolerate additional keyword arguments through `**_ignored`, so they require no behavior change; verify that compatibility in dispatch tests. The ingestion handler requires the value. Do not infer this fence from wall-clock time or from `attempt`.
- Add generic compare-and-set helpers for a handler to write its namespaced business summary and claim/finish one report-delivery attempt under `automation_runs.result.document_ingestion`. Every mutation must match `run_id`, `status='running'`, and the take's exact `started_at`; it may additionally verify `attempt`, but attempt alone is insufficient. Do not add ingestion-specific columns, teach `core` the ingestion status vocabulary, or make `core` import the shared package.
- Ensure the normal one-shot close merges or preserves that namespaced result instead of replacing it with a second ingestion record.

**TDD:**

- [x] **Step 1:** Add concurrent DB tests proving two producers receive one run ID for one occurrence.
- [x] **Step 2:** Prove a terminal row still deduplicates that same occurrence, a different occurrence is `busy` while the source's first run is active, and it can enqueue after the first run closes.
- [x] **Step 3:** Prove another source can run concurrently and that scheduled versus manual runs for one source cannot overlap.
- [x] **Step 4:** Prove calls without either key retain one-call/one-run behavior.
- [x] **Step 5:** Prove a recovered or zombie handler with the same run/attempt but an older `execution_started_at` cannot write the ingestion summary, claim/finish report delivery, or close the row; prove current concurrent writers cannot overwrite one another and normal close preserves the namespaced result.
- [x] **Step 6:** Prove the executor passes its take's exact `started_at` to ingestion and that every pre-existing one-shot kind still dispatches with unchanged behavior.
- [x] **Step 7:** From `api`, run `DEBUG=false poetry run pytest ../core/tests/db/automations/test_one_shot_runs.py ../core/tests/db/automations/test_automation_tables.py -m postgres -q`.
- [x] **Step 8:** Run `DEBUG=false poetry run pytest ../core/tests/unit/automations -q` plus the focused API one-shot dispatch suites affected by the ABI extension.

**Commit:** `feat: support idempotent one-shot enqueue`

### Task 4: Implement the repository state machines and schedule calculation

**Implementation status (2026-10-12): Complete and independently reviewed.**

**Implementation notes:**

- Repository transactions are caller-owned. Complete-window staging uses a method-local savepoint so a failed or ambiguous window rolls back its revisions and checkpoint without committing, rolling back, or clearing the caller's tenant binding.
- Processing recovery exposes the complete stored carrier fence and atomically exhausts current processing residue that has reached six attempts, preventing checkpointed work from becoming undiscoverable after a crash.
- Provider timestamps and repository time inputs are timezone-aware and checkpoints are monotonic. Distinct observations for one document at the same provider timestamp are rejected as an ambiguous window, including when the observations arrive across separate windows; exact normalized duplicates are no-ops.
- Checksum-less content fallback remains deliberately deferred. Task 5A permits `None` only for an authoritative `REMOVED` event; every COMPLY `UPSERT` still requires canonical SHA-256. A future connector that detects content changes without checksums must separately extend the connector-owned signal contract and its tests before activation.
- Independent Fix Round 2 review found no remaining Critical, Important, or Minor issues. Controller verification: Task 4 DB **39 passed**; Task 2 RLS/cascade DB **7 passed**; full units **92 passed, 1 intentional skip**; mypy, Poetry, diff, and disposable-schema cleanup checks passed.

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
- Claim a revision with carrier run ID, attempt, and execution `started_at`. Settlement is a compare-and-set on revision identity, `is_current`, ordinal, carrier ID, carrier attempt, and carrier execution fence. The timestamp fence is what rejects a zombie that shares the same retry number.
- Cap attempts at six total. Queries never return superseded or exhausted work.
- Store the opaque product outcome only after successful fenced settlement. A failed shared settlement never authorizes the shared repository to undo or reinterpret product state.

**TDD:**

- [x] **Step 1:** Start with failing schedule tests for both local times, DST, on-time slots, multi-slot outage catch-up, and no replay.
- [x] **Step 2:** Add failing transaction tests for a crash/exception on the last staged record and a competing checkpoint writer; neither may move the checkpoint.
- [x] **Step 3:** Add failing race tests: two executions sharing a run/attempt but carrying different `started_at` fences, old processing attempt versus recovered attempt, old failed revision versus newer revision, upsert versus later removal, and stale upsert after removal.
- [x] **Step 4:** Implement the minimum repository and pure schedule functions.
- [x] **Step 5:** Run unit tests, then the four DB files against a disposable Postgres database.

**Commit:** `feat: persist fenced ingestion state`

**Phase 1 review gate (passed 2026-10-12):** Tasks 1-4 are implemented and independently reviewed; Task 5 is the approved out-of-order exception already recorded below. Schema/RLS, state transitions, schedule enqueue invariants, and the generic one-shot change have focused verification. The later authoritative COMPLY contract does not reopen Phase 1 generally, but Task 5A must reconcile its one shared-model impact before Task 6 begins.

## Phase 2 — COMPLY connector and shared runner

### Task 5: Implement lossless COMPLY enumeration and secure downloads

**Implementation status (2026-10-09): Complete and reviewed.**

**Implementation notes:**

- Implemented in local `document-ingestion` commit `a9babc1` on branch `doc-ingestion-pipeline`.
- The task also created the minimal package scaffold, immutable connector dataclasses, connector protocols, and sanitized error hierarchy needed to implement and test the connector. At that point those files only partially scaffolded Task 1; Task 1 has since completed the product/run contracts, status calculation, package naming, dependency-boundary tests, and development lockfile.
- The repository is intentionally local-only for now and has no Git remote. Task 11 retains the pre-push remote/default-branch/protection gate.

**Post-review verification (2026-10-10):**

- From `api`, `PYTHONPATH=../document-ingestion DEBUG=false poetry run pytest ../document-ingestion/tests/unit/test_comply_connector.py ../document-ingestion/tests/unit/test_signed_url_client.py -q` completed with **42 passed and 1 skipped**.
- The single historical skip represented the then-unknown deletion field. The 2026-10-09 vendor guide and authoritative UAT Swagger now resolve that contract; Task 5A must replace the skip with executable contract coverage.
- Task 1 has installed the repository's standalone development environment with `poetry lock` and `poetry install --with dev`; direct `poetry run ...` commands from `document-ingestion` are now the canonical standalone test lane.

**Files:**

- Create `document-ingestion/document_ingestion/connectors/comply.py`
- Create `document-ingestion/document_ingestion/connectors/signed_url_client.py`
- Create `document-ingestion/tests/fixtures/comply/changes_page_*.json`
- Create `document-ingestion/tests/fixtures/comply/download_links_mixed.json`
- Create `document-ingestion/tests/unit/test_comply_connector.py`
- Create `document-ingestion/tests/unit/test_signed_url_client.py`

**Behavior:**

- The first scan uses no time filters and must read every declared page. Incremental scans use inclusive start/end filters and a fixed end equal to run start.
- Request at most 100 change rows per page and at most 50 download links per POST.
- Start page-number pagination at the documented zero-based page `0`.
- Normalize a confirmed full `sha256:<64 hex>` value to lowercase hex. This original behavior applied one checksum rule to every record; Task 5A narrows it so the rule remains strict for active records while authoritative removals may omit checksum.
- Deduplicate exact boundary records by external ID plus stable change key; refuse contradictory records sharing that key.
- Validate page number, page size, total pages/count, non-empty progress, and a stable response shape. Treat any inconsistency as an untrustworthy scan and leave the checkpoint unchanged.
- Historical assumption: deletion mapping awaited the client's field. Task 5A supersedes this with the required `status` enum while preserving the rule that absence never means deletion.
- Resolve the bearer token through the injected secret resolver. The API client and download client share no bearer/cookie state.
- Signed downloads require HTTPS and an allowlisted host, revalidate every redirect, reject userinfo/IP literals/private/link-local resolutions, use bounded timeouts, stream through a hard byte cap, and never log or persist the URL/query.
- Fetch a fresh signed link on expiry; do not cache one beyond the immediate attempt.

**TDD:**

- [x] **Step 1:** Use HTTPX mock transports for zero-based pagination, inclusive duplicates, mutable totals, truncated pages, mixed link results, 50-ID batching, expiry refresh, size overflow, redirect, malformed/abbreviated checksum, and checksum mismatch.
- [x] **Step 2:** Prove the bearer header reaches only the COMPLY API origin.
- [x] **Step 3:** Prove logs and raised public errors contain neither token nor signed URL.
- [x] **Step 4:** Task 1 installed the repository's development environment; run `poetry run pytest tests/unit/test_comply_connector.py tests/unit/test_signed_url_client.py -q` from `document-ingestion`. The API-environment command above remains historical verification evidence.
- [x] **Step 5:** Historical state: deletion mapping remained skipped because the contract was then unknown. Task 5A replaces this skip and re-verifies the connector before Task 6.

**Commit:** `feat: add secure COMPLY connector`

### Task 5A: Reconcile the authoritative COMPLY File Share contract

**Implementation status (2026-10-12): Complete and independently reviewed; uncommitted.**

Implementation evidence: full units passed **120 tests**; the Task 4 PostgreSQL lane passed **41 tests**; the Task 2 RLS/cascade PostgreSQL lane passed **7 tests**; mypy reported no issues in 13 source files; `poetry check` and `git diff --check` passed; and targeted live UAT OpenAPI inspection matched the amended route/status/checksum/download-link contract. The implementation remains uncommitted at unchanged `document-ingestion` HEAD `a9babc1` and introduced no migration, table, product logic, Document Hub dependency, plugin framework, or fallback signal. The first independent review found no code/test defect and two documentation-state contradictions; Fix Round 1 corrected both, and scoped re-review found all findings addressed with no new Critical or Important breakage.

This is a correction task, not a new abstraction. Preserve the reviewed connector boundary, security controls,
two-table persistence design, checkpoint semantics, and strict active-document checksum policy. Change only the
wire contract and the minimum shared representation required for checksum-less removals.

**Files:**

- Modify `document-ingestion/document_ingestion/models.py`
- Modify `document-ingestion/document_ingestion/connectors/comply.py`
- Modify `document-ingestion/document_ingestion/persistence/repository.py`
- Modify `document-ingestion/tests/unit/test_models.py`
- Modify `document-ingestion/tests/unit/test_comply_connector.py`
- Create `document-ingestion/tests/fixtures/comply/deletion_record.json`
- Modify `document-ingestion/tests/db/test_repository.py`
- Modify `document-ingestion/tests/db/test_revision_state_machine.py`
- Update `document-ingestion/README.md` only where it states the COMPLY routes or status/checksum contract
- Update this plan, its source design, and the SDD progress ledger with final test/review evidence

**Contract and behavior:**

- Use `GET /qp-fileshare-service/api/comply/documents/changes` and `POST /qp-fileshare-service/api/comply/documents/download-links`. Keep the configured API base as an origin/base URL; do not duplicate the service prefix in configuration.
- Require `id`, `name`, `last_updated`, and `status` on every change. Map `new` and `updated` to `ProviderOperation.UPSERT`; map `deleted` to `ProviderOperation.REMOVED`; reject a missing or unknown status as an untrustworthy scan. Never infer removal from absence.
- Change `NormalizedChange.checksum` to `str | None` with a closed invariant: `UPSERT` requires a canonical lowercase `sha256:<64 hex>` checksum; `REMOVED` permits `None` and validates canonical form if a checksum is supplied. The COMPLY connector normalizes removals to `checksum=None` while retaining the untouched provider record in opaque metadata.
- Keep missing, abbreviated, malformed, or wrong-algorithm checksums on `new`/`updated` as per-document `missing_required_checksum` or `invalid_required_checksum` issues. Do not introduce the future connector fallback signal.
- Never request a download link for `REMOVED`. Continue rejecting any download batch containing a non-`UPSERT` change.
- Treat `version`, `size_bytes`, `document_type`, and other undeclared fields as optional opaque metadata. Validate a download response's required `id`, `filename`, and `download_link`, but retain the staged change record's name as the document identity metadata.
- Enforce the documented newest-first order: `last_updated` must be non-increasing within and across pages; equal timestamps are allowed. Any reversal makes the scan untrustworthy and leaves the checkpoint unchanged. Snapshot stability remains a production-activation confirmation.
- Preserve exact-boundary deduplication and contradictory-record rejection. Include operation/status and timestamp in the normalized observation comparison so a null removal checksum cannot collapse a distinct provider event.
- Round-trip nullable removal checksums through the existing nullable database column. Change keys, equality checks, current-row reconstruction, exact replay, supersession, and equal-timestamp ambiguity detection must remain deterministic with `None`; no schema migration or new table is allowed.

**TDD:**

- [x] **Step 1:** Add failing route/request tests for the two exact File Share paths, zero-based pagination, page size 100, download batches of 1–50 IDs, and required download response fields.
- [x] **Step 2:** Replace the historical deletion skip with sanitized `new`, `updated`, and `deleted` fixtures. Prove status mapping, null/omitted deletion checksum, no removal download, missing/unknown status rejection, and strict checksum issues for active records.
- [x] **Step 3:** Add failing ordering tests for a reversal within one page and across a page boundary plus an accepted equal-timestamp boundary.
- [x] **Step 4:** Add model tests proving `UPSERT` rejects `None`, `REMOVED` accepts `None`, and any supplied checksum remains canonical.
- [x] **Step 5:** Add PostgreSQL tests for checksum-less removal insert/reconstruction, exact replay, removal after upsert, upsert after removal, and equal-timestamp upsert/removal ambiguity. Re-run Task 4's complete-window/checkpoint and stale-revision lanes.
- [x] **Step 6:** Run `poetry run pytest tests/unit -q`, the Task 2/4 PostgreSQL lanes, `poetry run mypy document_ingestion`, `poetry check`, and `git diff --check`.
- [x] **Step 7:** Independently review the scoped diff against the live Swagger schema, this plan, and the design spec. Resolve all Critical/Important findings and re-run affected plus full verification before marking Task 5A complete. Do not commit before review.

**Commit:** `fix: align COMPLY connector with file share contract`

**Task 5A review gate (passed 2026-10-12):** The authoritative route/status mapping, strict active-checksum
invariant, checksum-less removal round-trip, descending-order validation, and no-download removal behavior are
proven. Independent re-review resolved the documentation findings, so Task 6 may begin.

### Task 6: Implement raw-content staging, the sync runner, cleanup state, and reports

**Files:**

- Create `document-ingestion/document_ingestion/storage.py`
- Create `document-ingestion/document_ingestion/runner.py`
- Create `document-ingestion/document_ingestion/cleanup.py`
- Create `document-ingestion/document_ingestion/reporting.py`
- Modify `document-ingestion/document_ingestion/models.py`
- Modify `document-ingestion/document_ingestion/connectors/comply.py`
- Modify `document-ingestion/document_ingestion/contracts.py`
- Modify `document-ingestion/document_ingestion/persistence/repository.py`
- Create `document-ingestion/tests/unit/test_storage.py`
- Create `document-ingestion/tests/unit/test_runner.py`
- Create `document-ingestion/tests/unit/test_cleanup.py`
- Create `document-ingestion/tests/unit/test_reporting.py`
- Modify `document-ingestion/tests/unit/test_models.py`
- Modify `document-ingestion/tests/unit/test_comply_connector.py`
- Create `document-ingestion/tests/integration/test_fake_connector_end_to_end.py`
- Create `document-ingestion/tests/db/test_runner_state.py`

**Behavior:**

- `run_source_sync(...)` begins/resumes through the carrier run ID, attempt, immutable `execution_started_at`, and injected `RunResultStore`, enumerates the complete window, stages it atomically, then processes only current actionable revisions independently. It creates no ingestion-run row.
- Accept the connector's bounded `DownloadedDocument`, verify size and checksum again at the runner boundary, write it to a bounded temporary file, compute a tenant/source/revision-qualified raw-content key, and require the `RawContentStore.persist(...)` adapter to write that exact caller-supplied key. Pass a `ProductDocumentInput` containing the short-lived path and verified `StoredContentReceipt` to the product adapter.
- Encode every tenant/source/revision filesystem identity component with a representation that cannot emit `.`, `..`, `/`, or `\\` path segments. Receipt validation and every later failure path must retain the exact caller-authorized storage key for cleanup tracking.
- Persist the returned raw-storage key through a current-revision/carrier-fenced repository write before invoking the product adapter. Keep cleanup and backlog queries in the existing repository rather than issuing SQL from the runner; add no table and no ingestion-run identity.
- Same-checksum observations update metadata but create no content revision and invoke no download or adapter.
- The same-checksum shortcut applies only while the document is active. An `UPSERT` after `removed` creates a higher-ordinal revision and reingests it, preventing the tombstone from swallowing a legitimate reappearance.
- Process one document failure without rolling back neighboring successes or changing source enabled state.
- Process actionable revisions through a configurable fixed-size worker pool; preserve independent outcomes without creating one task per revision or starting unbounded parser/index work during a large initial import. If one worker raises a technical defect, cancel and await every sibling before returning or re-raising.
- Retry only current retryable revisions; the sixth failed total attempt becomes exhausted.
- Treat the closed successful `ProductOperationOutcome` as the upsert boundary and `non_retrievable` as the removal boundary. Persist opaque product data without inspecting parser-specific revision or artifact fields.
- When a newly staged observation supersedes a revision that has raw content, mark that prior row cleanup-eligible at `window_end + source.retention_hours`; this includes a new removal superseding active content. Keep physical deletion execution behind a default-off switch until the client retention SLA is confirmed. Task 6 proves the disabled path and eligibility state only; it must not pretend physical deletion ran or invent the unresolved retention policy.
- Calculate mutually exclusive counts and the four ingestion business statuses. Persist the fixed window, business status, counts, bounded failures/backlog, and next schedule through the injected `RunResultStore` into `automation_runs.result.document_ingestion`; never write those business values into the carrier's generic `status` column.
- Compose one report with current-run counts, status, next schedule, concise failures, and separate retryable/exhausted/parked/cleanup backlog. Attempt delivery once and persist sent/failed independently of ingestion status.
- Claim report delivery through a compare-and-set on `automation_runs.result` before sending, fenced by the take's exact `started_at`, so a recovered or zombie execution cannot initiate the same terminal report twice. The shared package sees only the `RunResultStore` protocol; the API supplies the `core`-backed adapter.
- Validate enumeration issues before staging: a source-level issue makes the scan untrustworthy with null counts, while each document is counted at most once as failed. Non-parked document issues are excluded from staging and current-run processing; checksum-invalid parked observations follow the durable exception below.
- For a `new` or `updated` record whose required checksum is missing or invalid, atomically stage a current `parked` observation in the existing revisions table before advancing the checkpoint. Preserve its required provider identity/timestamp and opaque metadata, record a bounded failure code, supersede every older unfinished revision for that document, and never download it. Exact replay is a no-op; a later valid higher-timestamp observation supersedes it. Do not add a table or weaken the strict `NormalizedChange` checksum invariant.
- Issue order is not a connector contract. Group issues by document without first-item-wins behavior, retain every distinct checksum-invalid parked observation for atomic staging, and use the newest parked timestamp when reconciling same-window valid changes. Count/report only one failure per document. A parked payload is valid only for the missing/invalid-required-checksum codes; reject it on download or other issue kinds.
- Convert expected connector/listing/checksum/document failures into a persisted business outcome and report rather than raising past the runner. Only the explicit report-transport exception is an expected non-escaping delivery failure; persist terminal report failure before re-raising unexpected technical defects such as filesystem/permission errors when result persistence remains available.
- If the exact-fence report-delivery claim returns false, do not fabricate a local `claimed` state. Surface an explicit technical/fence-loss outcome without sending or finishing delivery; Task 9 still owns the concrete `core` compare-and-set implementation and its authoritative persisted-state tests.

**TDD:**

- [x] **Step 1:** Add runner cases for initial full scan, zero changes, unchanged active checksum, add, update success, update failure, confirmed non-retrievable removal with cleanup pending, same-checksum resurrection after removal, checksum mismatch, mixed 4%/5%/>5% failures, and failed listing.
- [x] **Step 2:** Add supersession tests where revision N is processing or retryable when N+1 arrives; N must lose both settle and product-call eligibility.
- [x] **Step 3:** Use a second fake connector in the integration test and assert the runner contains no COMPLY type check.
- [x] **Step 4:** Add PostgreSQL tests proving the carrier-fenced raw-storage-key write, configured cleanup eligibility on superseded raw content/removal, backlog counts, stale-settlement rejection, and no new table or runner-side SQL.
- [x] **Step 5:** Run `poetry run pytest tests/unit tests/integration/test_fake_connector_end_to_end.py -q` plus `tests/db/test_runner_state.py` against guarded `copilot_mro_test`.
- [x] **Step 6:** Run `poetry run mypy document_ingestion`, `poetry check`, and `git diff --check`.
- [x] **Step 7:** Independently review Task 6, resolve every Critical/Important finding through scoped fix rounds, and re-run the focused, full unit/integration, PostgreSQL, typing, package, and diff lanes before marking the task complete.
- [x] **Step 8:** Add a two-run PostgreSQL regression proving a checksum-invalid active observation is durably parked and supersedes older retryable/processing work before checkpoint advancement; correct the false report-claim result; run all Phase 2 lanes and obtain a clean whole-phase re-review.
- [x] **Step 9:** Add reversed-order, multiple-distinct-parked, and mixed parked/non-parked issue tests at the runner and PostgreSQL boundaries; reject parked payloads on unrelated issue codes; run all Phase 2 lanes and obtain a clean Fix Round 4 re-review.

**Commit:** `feat: run and report document syncs`

**Phase 2 review gate (accepted 2026-10-12):** Task 5A and Task 6 are implemented and independently reviewed. The final gate verified the authoritative COMPLY contract, lossless checkpointing, durable parked observations, retry/supersession behavior, bounded provider-neutral execution, status/report truthfulness, raw-content safety, and the two-table/product-agnostic boundary. Phase 3 may begin. The only explicit non-blocking deferred item is replacing list-membership parked-observation deduplication with keyed grouping before large-scale activation; Task 9 still owns the concrete `core` exact-`started_at` report-claim CAS.

## Phase 3 — Copilot MRO product-side revision and publication behavior

### Task 7: Assess existing Copilot stores and lock the product strategy

**Files:**

- Create `copilot-mro/docs/plans/client-document-ingestion-storage-assessment.md`
- Inspect `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/documents.py`
- Inspect `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/chunks.py`
- Inspect `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/manual.py`
- Inspect `copilot-mro/copilot_mro/app/services/doc_catalog.py`
- Inspect `copilot-mro/copilot_mro/app/services/s3_pdf_processor.py`
- Inspect `copilot-mro/copilot_mro/app/services/llama_index/llama_index_ingestion.py`
- Inspect the exact query/direct-fetch modules used by each parser family selected for activation

**Assessment:**

- For each supported parser family, trace the current authoritative Postgres rows, catalog entry, chunk rows, S3 keys, Weaviate objects, retrieval entrances, replacement behavior, and removal behavior.
- Record which existing stores and identifiers can carry source identity, idempotency, stale-execution rejection, revision ordering, visibility, and removal guarantees without schema changes.
- Define the product-owned strategy for a new document, changed document, failed change, removal, retry, stale carrier execution, higher-ordinal reappearance, and rollback. Different parser families may select different implementations while honoring the same external outcome contract.
- Identify any invariant that the current product stores cannot represent. If a gap exists, propose only the smallest Copilot-owned column or relation needed and explain why existing tables cannot satisfy it.
- Do not add `copilot_client_document_bindings` or product schema by default. The approved gap is one
  Copilot-owned `client_document_publications` relation. The only shared-ingestion exception discovered by the
  assessment is the exact-final-carrier exhausted-to-applied settlement CAS described in Task 8; it is generic
  delivery bookkeeping and must not contain product parsing, indexing, publication, revision or cleanup logic.
- End the assessment with the exact production modules, test files, data migrations, and retrieval paths Task 8 must change. Update Task 8's concrete file list at this gate rather than guessing parser-specific files now.

**Verification:**

- [ ] **Step 1:** Reconcile the assessment against the actual table definitions and one representative persisted document for every proposed parser family.
- [x] **Step 2:** Trace hybrid/vector/BM25/filter retrieval plus direct chunk/catalog/structured-data access where applicable; do not treat the main search path as the only visibility surface.
- [x] **Step 3:** Demonstrate how the chosen strategy rejects an older ordinal or carrier execution fence after newer product state has won, including two workers with the same run/attempt but different `started_at` values, without relying on a shared `PublicationFence`.
- [x] **Step 4:** Review the reuse/gap decision before creating any migration or production code.

**Task 7 review gate (accepted 2026-10-12):** The one-relation Copilot strategy, exact current/highest-ordinal
fencing, immutable execution generations, single external writer, durable per-call admission, closed-write cleanup,
two-branch legacy/managed retrieval, Core cache-version seam and AMM/SRM activation scope are independently
approved. Step 1 remains an activation prerequisite because the running environment did not contain a complete
representative current AMM/SRM document across Postgres, S3 and the intended `ManualsMT` collection; this blocks
fixture-backed parser/lifecycle acceptance, not the generic repository/visibility foundation.

**Post-review MVP ruling (2026-10-13):** retain the accepted logical publication, visibility and stale-worker
fences, but defer the durable provider-call admission/write-close/cleanup state machine. Phase 3 performs no
physical artifact deletion or rollback orchestration. Generation-qualified residue remains invisible and is
recorded for later reclamation after retention policy is known. Cost if wrong: storage residue grows until the
later cleanup phase, but agent-visible data remains fenced and current.

**Commit:** `docs: assess Copilot ingestion storage reuse`

### Task 8: Implement the Copilot adapter using the approved product strategy

**Implementation status (2026-10-13): Complete, independently tested, and independently accepted; uncommitted.**

**Implementation notes:**

- Added the lean Copilot-owned publication relation and exact current/highest/carrier/generation fences, one-writer
  ownership, legal lifecycle constraints, bounded manifests/outcomes, retry/replay, removal, and reappearance.
- Added product-config-selected AMM/SRM parsing, canonical page identities, a concrete injected S3/embedding/
  Weaviate artifact adapter, generation-qualified invisible staging, mandatory-store verification, and exact
  generation enablement before atomic product cutover.
- Added centralized operator-scoped legacy/managed visibility across central retrieval and workout, fail-closed
  managed authority, explicit legacy-only compatibility, mounted document/PDF removal checks, and an opaque Core
  cache-version provider without a Core-to-Copilot dependency.
- Preserved the shared/product boundary: shared ingestion changed only the generic exact-final-carrier settlement
  slice; parsing, indexing, product revision state, visibility, and logical removal remain in Copilot MRO.
- Independent review rejected the first pass for six concrete runtime/test gaps. Three bounded fix rounds corrected
  transaction/RLS ownership, the concrete artifact adapter, non-contiguous page IDs, strict manifest semantics,
  fail-closed authority/legacy behavior, operator isolation, and registry test isolation. Final re-review returned
  `ACCEPTED` with no remaining Critical, Important, or Minor finding.
- Fresh controller verification: Copilot focused/regression **108 passed**; Core **18 passed**; shared units
  **188 passed**; guarded Copilot publication/composition DB **24 passed**; guarded shared final-carrier DB
  **22 passed**; bounded Ruff lint/format and all three repository diff checks passed.
- Client-approved AMM/SRM fixtures, target `ManualsMT`/S3/embedding/Weaviate acceptance, credentials, realistic
  volume/performance, Task 9 worker construction, and later deployment remain explicit activation/future-phase
  gates. No production activation claim is made.

**Files:**

- Create `copilot-mro/copilot_mro/app/services/client_document_ingestion/{__init__,parser_adapter,consumer,composition,publication_repository,visibility}.py`.
- Create `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/client_document_ingestion.py` and
  register it in `copilot_mro/app/db/postgres_table_definitions.py`; do not create a numbered SQL migration or
  modify the existing migration/RLS scripts.
- Modify only the approved Copilot product paths: `pdf_parser.py`, `doc_catalog.py`, the three
  `llama_index` initialization/ingestion/query modules, `workout_gate.py`, `mro_documents_endpoints.py`,
  `main.py`, and `scripts/provision_weaviate_mt.py`.
- Create the approved Copilot unit, integration, registry, live-DB/RLS/concurrency, direct-workout and AMM/SRM
  fixture tests listed in `copilot-mro/docs/plans/client-document-ingestion-storage-assessment.md`.
- In Core, add only the opaque document-viewer cache-version helper and its list-key/mounted-route tests. Core
  must not query or interpret the Copilot publication relation.
- In shared `document-ingestion`, modify only `document_ingestion/persistence/repository.py`,
  `tests/db/test_processing_fence.py`, and `tests/db/test_runner_state.py` for the exact-final-carrier settlement
  exception. Do not change its runner, public product contract, schema, migrations, work-list or claim logic.

**Behavior:**

- Initial activation supports AMM/SRM only. Map normalized source metadata to that parser family and reuse its
  existing document, catalog/chunk, S3 and Weaviate stores wherever the assessment proved them sufficient.
- Persist one immutable Copilot publication-generation row per carrier execution. Allow multiple generations for
  one source revision, but permit only one current row, one active row and one authoritative successful outcome.
  Every claim, terminal transition and cutover must prove the exact carrier/generation and the source's current
  highest ordinal.
- Preserve existing callers while adding only the narrow strict-write/idempotency seams required by the approved family strategy. Mandatory product-store failures must propagate instead of being hidden by a top-level success boolean.
- Use the supplied source revision ordinal, carrier run ID, carrier attempt, and `carrier_started_at` in product-owned idempotency and stale-work checks. A late older revision or stale recovered execution must not overwrite a newer successful product representation or reactivate a removed document; attempt alone is not a sufficient worker identity.
- Give each generation one durable writer token; exact duplicate callers observe only. S3/Weaviate artifacts are
  generation-qualified, and only an exact current/highest generation may publish. A superseded writer can leave
  residue only in its invisible namespace and can never cut over product visibility.
- Query legacy vectors lacking managed publication identity separately from managed candidates matching the active
  publication and generation; boundedly over-fetch, validate, merge and deduplicate. Apply the same visibility
  authority to direct workout, catalog/chunk, structured SQL, mounted Core and document-viewer entrances.
- Return the shared closed `ProductOperationOutcome` only after the selected parser family's mandatory representations and retrieval behavior verify. Keep artifact identities and internal revision details in the opaque payload.
- A failed change leaves the last successful product representation usable. A successful new/changed document becomes retrievable only after that family's complete product operation succeeds.
- A successful removal verifies that every applicable retrieval entrance is blocked before returning
  `non_retrievable`. Physical deletion is not executed in Phase 3; bounded artifact identity is retained for a
  later cleanup phase.
- Implement only the one approved Copilot-owned publication relation. All parsing, indexing, product revision and
  generation state, publication/visibility and logical removal remain in Copilot MRO. Physical cleanup and
  rollback are explicitly deferred rather than partially implemented.
- For observer timeouts on attempts 1–5, return existing `FAILED/product_operation_in_progress`; a later carrier
  may replay a stored successful Copilot outcome without mutation. On attempt 6, allow only the immutable same
  final carrier to acknowledge its already-running `APPLIED` or confirmed `NON_RETRIEVABLE` outcome by changing
  the exact current shared row from exhausted to applied. This creates no seventh claim or product execution.
- If the final process dies after Copilot commits success but before acknowledgement, keep the shared revision
  exhausted/needs-attention. Activation requires accepted alerting and manual reconciliation; do not claim an
  automatic seventh retry.

**TDD:**

- [x] **Step 1:** Complete the lean publication repository and live PostgreSQL constraint/RLS/concurrency tests:
  multi-generation retry, exact-execution idempotency, current/highest fencing, sole-writer ownership, bounded
  manifests/outcomes and legal operation/state combinations. Remove admission/write-close/cleanup execution.
- [x] **Step 2:** Add visibility characterization before implementation for hybrid/vector/BM25/filter, direct
  workout/chunk/catalog/structured-data, mounted Core and cache behavior; then prove legacy and managed branches.
- [x] **Step 3:** Prove retry idempotency, stale ordinal/carrier rejection (including same attempt and older
  `started_at`), failed-generation retry, successful-outcome replay after settlement loss, supersession, removal
  and reappearance. Prove superseded generation residue is invisible; do not delete it.
- [x] **Step 4:** Prove exact duplicates never become a second writer and no stale/superseded generation can
  publish, even if its synchronous parser/index calls finish later.
- [x] **Step 5:** Prove attempts 1–5 observer timeout/replay and attempt-6 exhausted-to-applied behavior for both
  `APPLIED` and confirmed `NON_RETRIEVABLE`, including rejection of a different carrier, stale ordinal and
  noncurrent revision, and no seventh claim/work eligibility.
- [x] **Step 6:** Implement the AMM/SRM product-config mapping and synchronous product consumer using existing
  Copilot parser/indexing seams. Add failure injection around mandatory stores; prove no early success,
  prior-document availability after failed update, failed-new invisibility and complete logical-removal visibility
  blocking. Sanitized synthetic fixtures may prove offline behavior; production activation still requires client-
  approved representative fixtures.
- [x] **Step 7:** Run focused Copilot unit/integration/live-DB lanes, affected Core tests, the three shared
  settlement tests, the non-live Copilot regression lane, typing/package checks and `git diff --check`.
- [x] **Step 8:** Independently review the complete Phase 3 diff before any commit.

**Commit:** `feat: consume synchronized documents in Copilot MRO`

**Phase 3 review gate:** Stop. Compare implementation against the approved storage assessment plus the MVP scope
override. Inspect one successful add, failed update, stale-execution rejection, logical removal and retry for
AMM/SRM. Do not require or claim physical cleanup or rollback.
Confirm product behavior remains in Copilot MRO and that shared-ingestion changes are exactly the three-file
generic settlement exception above. Do not activate until the representative fixtures/mappings, target
`ManualsMT`/S3 behavior, retention/cleanup policy and final-attempt manual reconciliation are accepted.

**Phase 3 review result (2026-10-13):** Offline MVP accepted after independent development, testing, and extra-high
review. Product/shared/Core boundaries and the no-cleanup/no-rollback scope were preserved. The production source
must remain disabled until the named client fixtures and target-environment activation gates are satisfied.

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

- Register `document_ingestion_sync` in the existing one-shot feature wiring. Its keyword-only handler ABI receives `tenant_id`, `user_id`, `params`, `attempt`, `run_id`, and required `execution_started_at`; the executor supplies the value stamped by the winning `OneShotTake` in Task 3.
- Add one lazy due-producer call before the one-shot scan on each tick. It uses the existing paged tenant registry, binds one tenant, reads a bounded due-source batch, ensures the occurrence run, then compare-and-set advances the source schedule.
- Pass the source's single operator as a one-element `operator_ids` list on the one-shot row so the existing dispatcher binds tenant+operator before the handler calls Copilot.
- Compose connector registry, repository, content store, Copilot consumer, secret resolver, SMTP report sender, and the `core`-backed `RunResultStore` in this API module only.
- A global `DOCUMENT_INGESTION_ENQUEUE_ENABLED` switch controls new enqueueing but not handler registration, so rollback stops new work while already-claimed rows can drain.
- Add bounded `DOCUMENT_INGESTION_DOCUMENT_CONCURRENCY` and `DOCUMENT_INGESTION_RUN_MAX_SECONDS` settings. The due producer passes the latter to the one-shot row; the activation runbook records values proven by the fixture rather than hiding an unreviewed constant in code.
- Extend worker boot preflight to require the two shared tables and only the product schema explicitly approved in Task 7; create none at boot.
- Keep technical carrier status and ingestion business status distinct in logs and status reads. A handled business `failed`/`needs_attention` result still lets the one-shot executor close the carrier `completed`; an unhandled handler exception closes it technically `failed` and must not invent document counts.

**TDD:**

- [x] **Step 1:** Prove two ticking processes enqueue one occurrence, a crash before schedule CAS is repaired, a later occurrence waits behind an active run of the same source, a missed schedule queues once after that run closes, and different tenants cannot see each other's sources.
- [x] **Step 2:** Prove the handler receives the carrier attempt, exact `execution_started_at`, and operator binding; persists business summary/report state only while that fence owns the row; closes a handled business `failed` result technically `completed`; and closes an unhandled exception technically `failed` without fabricating counts.
- [x] **Step 3:** Prove enqueue-disable stops new rows but still serves an existing claimed ingestion row.
- [x] **Step 4:** From `api`, run the five focused test files named above, then the existing one-shot and worker-entrypoint suites.

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
- Decommission disables scheduling and asks the product adapter to make current documents logically
  non-retrievable through one-shot work; it never hard-deletes source history or physical artifacts.
- Register ingestion as an explicit tenant/operator erasure step only to disable scheduling, establish confirmed
  logical non-retrievability, and preserve revision/artifact evidence. Physical raw/S3/vector cleanup remains
  deferred. If the existing erasure workflow requires verified physical deletion before final identity deletion,
  leave it honestly `needs_attention`; never cascade away the evidence or claim cleanup completed.

**TDD:**

- [x] **Step 1:** Prove no token, ordinary user, tenant owner, and tenant settings admin are denied; only the configured staff group passes.
- [x] **Step 2:** Prove a platform admin may target another tenant only through the audited service and cannot bypass immutable identity fields.
- [x] **Step 3:** Prove mutation and audit event commit or roll back together.
- [x] **Step 4:** Prove decommission and tenant/operator teardown preserve source revision/artifact evidence,
  block product retrieval, perform no physical deletion, and leave any physical-erasure requirement
  `needs_attention`.
- [x] **Step 5:** Run the focused API tests and affected core authorization-event tests.

**Commits:**

- `core`: `feat: audit ingestion source administration`
- `copilot-mro`: `feat: include client documents in lifecycle teardown`
- `api`: `feat: add ingestion administration controls`

**Phase 4 review gate:** Stop. Review the exact admin authorization claim, cross-tenant authorization and tenant context, audit records, teardown behavior, and absence of any dashboard/Document Hub change.

**Phase 4 review result (2026-10-13):** Accepted with activation-only concerns after the requested three-agent
development, testing and review workflow. The final focused evidence closed the transaction-durability,
product-owned decommission, deterministic retry/fairness, exact target-operator binding, configuration-validation,
fault-isolation, connector-validation and audit findings. Physical cleanup, rollback, dashboard/Document Hub and
Phase 5 work remain absent. Guarded real-PostgreSQL concurrency/RLS verification remains required before source
activation because this environment did not provide the explicit disposable owner/application-role credentials.

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

- Preserve the `flynapse-document-ingestion` distribution name and `document_ingestion` import module established by Task 1.
- Add the sibling path dependency to API and Copilot MRO for the current workspace/build model.
- Add `document-ingestion=<commit>` to the committed-source image staging list, usage, labels, and path-dependency closure check.
- Keep the image immutable by commit tags and prove uncommitted shared-package files cannot enter it.
- Establish the remote repository and branch protection before the first shared commit is pushed; do not invent a remote or default branch during implementation.

**TDD:**

- [ ] **Step 1:** Make the image-closure test fail on the new path dependency.
- [ ] **Step 2:** Update manifests/locks and build-script assertions.
- [ ] **Step 3:** From `api`, run `poetry check`, the import-boundary tests, and focused package tests.
- [ ] **Step 4:** From `iac`, run the demo-box image tests and the build script's non-network validation path.

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

- [ ] **Step 1:** Add static tests for desired count, command, network exposure, scheduler modes, secret references, task/execution role separation, log group, and alarm gate.
- [ ] **Step 2:** Run `terraform fmt -check`, `terraform validate`, and the focused IaC unit tests.
- [ ] **Step 3:** Review `terraform plan` for exactly one worker service, no public listener, API scheduler off, required SG additions, and alarms gated correctly.
- [ ] **Step 4:** Deploy with enqueue disabled; verify boot preflights, liveness logs, OTLP identity, DB/Weaviate access, and clean SIGTERM drain.

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
- Prove successful documents are queryable while neighbors fail; failed update retains its old active answer;
  removed documents are immediately absent while physical residue remains deliberately retained; older failed
  revisions never rerun after a newer revision.
- Kill the worker after enqueue, during download, before the product operation commits, and after product success. Prove recovery reuses the occurrence/run, gives the new take a different `started_at`, rejects the stale execution in shared and product settlement even when the attempt number is shared, and initiates at most one terminal report attempt.
- Verify report counts/status at 0%, 5%, and >5% plus the separate unresolved/deferred-cleanup backlog.

**Activation order:**

- [ ] **Step 1:** Commit sanitized contract fixtures for `new`, `updated`, and `deleted`; record the still-required stable-ID, active-checksum, and filtered-pagination snapshot confirmations in the runbook. The fixtures prove the documented shape but do not replace those production confirmations.
- [ ] **Step 2:** Run all non-live suites, disposable Postgres RLS/schema suites, and disposable Weaviate/S3-compatible integration suites.
- [ ] **Step 3:** Apply the two shared tables, generic `automation_runs` columns/indexes, and only the minimal product migration approved by Task 7, with enqueue disabled.
- [ ] **Step 4:** Deploy the approved Copilot product strategy, adapter, API wiring, and worker; verify legacy retrieval unchanged.
- [ ] **Step 5:** Create one disabled COMPLY source through the platform-admin route and run a manual dry-run/list-only validation that cannot advance the checkpoint.
- [ ] **Step 6:** Enable one low-risk tenant/operator source, reconcile the first product outcome against the mandatory stores identified by Task 7, and verify the report email.
- [ ] **Step 7:** Observe two scheduled runs, including one with a controlled document failure, before expanding.
- [ ] **Step 8:** Keep physical cleanup disabled and record retention/reclamation as a later client-approved phase;
  Phase 5 activation must not enable or claim physical cleanup.

**Verification commands:**

From `api`:

```bash
DEBUG=false poetry run pytest ../document-ingestion/tests/unit -q
DEBUG=false poetry run pytest ../document-ingestion/tests/integration -q
DEBUG=false poetry run pytest tests/unit/automations/test_document_ingestion_jobs_handler.py -q
DEBUG=false poetry run pytest tests/integration/automations/test_document_ingestion_due_enqueue.py -q
DEBUG=false poetry run pytest tests/integration/automations/test_document_ingestion_one_shot_dispatch.py -q
DEBUG=false poetry run pytest ../copilot-mro/tests/unit/client_document_ingestion -q
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

1. Expand Postgres first. The new nullable `automation_runs.dedupe_key`/`concurrency_key`, two shared tables and any Task 7-approved additive product change must be proven safe for older API/workers.
2. Deploy any product-side visibility or retrieval change required by the approved Copilot strategy before ingestion can write product data. Legacy behavior must be proven first.
3. Deploy the capable worker with enqueue disabled. Older workers ignore an unregistered kind, but the environment must never enqueue ingestion work when no capable worker is present.
4. Stop new work by disabling ingestion enqueue and sources; let claimed rows drain or be recovered by the existing one-shot reaper.
5. Preserve the two shared tables, checkpoints, source revision/removal history, opaque product outcomes, approved product-side state, and one-shot dedupe columns during rollback. Never roll a checkpoint backward or erase removal history automatically.
6. Product-data rollback follows the parser-family strategy approved in Task 7. Restore a prior representation only when that product's retained artifacts and retrieval invariants re-verify; otherwise reingest.
7. Do not automatically undo a provider removal. Resurrection requires a later, higher-ordinal UPSERT or an explicit audited administrator action after client confirmation.
8. Physical cleanup is the last irreversible action and remains separately enabled. Once prior artifacts are physically purged, rollback requires reingestion.

## Final self-review checklist

- Every goal and acceptance criterion in the approved spec maps to at least one task and test above.
- The COMPLY connector is the only provider-specific production module; the fake connector proves runner neutrality.
- Product-specific parsing, revision management, publication, visibility, removal, cleanup, and rollback stay in Copilot MRO; shared code carries only source revision context, protocols, and opaque outcomes.
- Source-run occurrence dedupe/active-source exclusion and source-revision processing fences remain shared; all stale-worker mutations use the carrier take's `started_at` rather than attempt alone, and each product independently proves its stale-work/idempotency strategy.
- Only `document_ingestion_sources` and `document_ingestion_revisions` are added by the shared package. Run context and results reuse `automation_runs`, and Copilot schema is added only after Task 7 proves an invariant gap.
- Initial import is a complete listing but not an all-or-nothing publication gate.
- `removed` means non-retrievable, while cleanup state reports physical residue honestly.
- Exactly five automatic retries means six total attempts.
- Run counts exclude unchanged documents and inactive backlog; the report still exposes unresolved backlog.
- Platform-admin authorization is server-side, staff-only, cross-tenant, and audited.
- The deploy uses one existing automation-worker process, not one service per connector.
- Production activation remains blocked on stable document IDs, active-document checksum format/requiredness, filtered-pagination snapshot behavior, and supported parser mapping. Deletion mapping and newest-first ordering are resolved and must remain covered by contract tests.
