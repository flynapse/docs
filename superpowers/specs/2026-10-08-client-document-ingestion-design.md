# Client document ingestion — design

Status: **Proposed for owner review (2026-10-08).** This document records the architecture and product
decisions agreed during design discussion. It does not authorize implementation. The implementation plan is
written only after this specification is reviewed and approved.

## 1. Problem statement

Flynapse needs to keep a client's document corpus synchronized with Flynapse product datastores. The first
client, COMPLY, exposes one endpoint that lists document changes and another that returns short-lived download
links. Later clients may expose documents through a different mechanism, such as another API or SFTP.

The ingestion mechanism must be reusable without becoming a general document platform. It must isolate
provider-specific access from product-specific parsing and indexing, process documents independently so a few
failures do not interrupt agent functionality, and give Flynapse operators a simple email report after every
executed sync.

Copilot MRO is the first product consumer. Its existing parsing, cataloguing and indexing methodology remains
authoritative. Document Hub is a separate feature and is not part of this design.

## 2. Goals and non-goals

### Goals

- Add a small shared Python repository, `document-ingestion`, containing provider-neutral synchronization code.
- Implement only the COMPLY connector in the first release.
- Make a later provider require a connector module and registration, not changes throughout the codebase.
- Keep parsing, indexing, retrieval and product deletion behavior owned by Copilot MRO.
- Run two configurable syncs per source per local day and catch up once when the worker recovers after a missed
  schedule.
- Detect actual COMPLY content changes by checksum and download only documents whose content signal changed.
- Process additions, changes and removals independently; successful work remains applied even when other
  documents fail.
- Persist current source state, revision metadata, retry state, checkpoints and run summaries.
- Send one email report after every sync execution reaches a terminal result.
- Restrict source configuration and manual operational actions to Flynapse internal platform administrators.

### Non-goals

- Integrating with Document Hub or reusing its tables, permissions, API routes or UI.
- Building a generic parsing or indexing platform.
- Building connectors other than COMPLY in the first release.
- Deploying a separate service per connector.
- Building a connector plugin marketplace, workflow engine or event bus.
- Building an ingestion dashboard.
- Deactivating a complete source because individual documents failed.
- Rolling back successful document operations because other documents failed.
- Monitoring a schedule that never launched; absence of an expected email is sufficient for the first release.
- Solving provider-specific edge cases that are not present in the first client contract.

## 3. Options considered

### Option A — shared library plus product adapter (selected)

Create a small shared Python package for connectors, synchronization, state and reports. Copilot MRO implements
the product adapter, and the existing automation worker imports both packages and composes them.

This preserves the dependency direction: the shared package knows only a narrow product callback, while
Copilot MRO continues to own its parsers and indexes. A later product adds its own adapter. The cost is one new
repository and explicit package/version coordination with the worker.

### Option B — place the pipeline inside Copilot MRO

This would minimize the first implementation but would make provider synchronization a Copilot MRO feature.
Supporting another product would either duplicate synchronization code or require extracting it later. It is
rejected because the ingestion process is intended to serve several products.

### Option C — standalone ingestion service with dynamic plugins

This would provide maximum deployment independence, but it adds an API boundary, service deployment, service
authentication and plugin lifecycle before any second connector or product exists. It is rejected as
unnecessary complexity.

## 4. Architecture and ownership

The selected architecture has three domain boundaries and one composition boundary:

```text
COMPLY API
    |
    v
document-ingestion package
  COMPLY connector -> sync runner -> state/revision repository -> email report
                            |
                            v
                  ProductDocumentConsumer
                            |
                            v
Copilot MRO adapter -> existing Copilot MRO parsers, catalogs and indexes

API automation worker: imports the shared runner and the Copilot MRO adapter and connects them
```

### 4.1 `document-ingestion` repository

The shared repository owns:

- the connector interface and a simple connector registry;
- the COMPLY connector;
- normalized change and downloaded-document models;
- scheduling and due-source claiming;
- change detection, download and checksum verification;
- checkpoints, revision metadata, retry state and run summaries;
- source-document staging and retention eligibility;
- run status calculation;
- email report composition and delivery through the existing shared email utility.

It does not import Copilot MRO, Document Hub, FastAPI or dashboard code. It is a library loaded into the
automation worker, not an independently deployed application.

The initial package should stay small. Logical modules are `connectors`, `models`, `runner`, `repository`,
`scheduling` and `reporting`. These are code-organization boundaries, not independently deployed components.

### 4.2 Copilot MRO

Copilot MRO owns a `ProductDocumentConsumer` adapter that implements two operations:

- ingest a downloaded document and normalized metadata using existing Copilot MRO parsing, cataloguing and
  indexing behavior;
- remove a document from every Copilot MRO datastore and index in which that ingestion placed it.

The adapter owns mapping client document metadata to Copilot MRO parser choices, tenant/operator attribution,
product metadata and deletion details. Unsupported or unclassifiable documents return a document-level
failure; they do not move provider-specific logic into the shared runner.

Copilot MRO depends on the shared contract. The shared repository never depends on Copilot MRO. The API worker
is the composition root that imports both.

### 4.3 API automation worker and infrastructure

The existing standalone automation worker is the execution host. The first implementation enables and deploys
that worker rather than introducing an ingestion-specific service. The API process no longer needs to perform
the heavy synchronization work in a request path.

The worker installs one ingestion feature wiring module. On each scheduler tick it asks the shared package for
due sources. The shared repository claims a source before queueing or running it, so at most one sync for a
source is active at a time. Existing one-shot job execution may carry an individual source run, but source
schedules and checkpoints remain owned by `document-ingestion`, not by user chat-automation definitions.

## 5. Connector contract

A connector has two responsibilities:

1. Enumerate normalized change records for a bounded sync window.
2. Download content for an `UPSERT` record when the runner classifies it as added or changed.

A normalized change contains:

- source-local external document identifier;
- provider operation: `UPSERT` or `REMOVED`;
- file name and provider update timestamp;
- checksum when supplied;
- size and provider version when supplied;
- document type and provider metadata needed by the product adapter.

Provider authentication, pagination, request batching, signed-link refresh and provider error translation stay
inside the connector. The runner classifies an `UPSERT` as added, changed or unchanged by comparing it with
persisted document state. It must not contain `if provider == ...` behavior.

The registry is deliberately static: one connector module plus one registry entry. Dynamic package discovery
or runtime plugin installation is out of scope.

### 5.1 COMPLY connector

The COMPLY connector uses:

- `GET /qp-data-share/api/documents/changes` for initial enumeration and incremental windows;
- `POST /qp-data-share/api/documents/download-links` in batches of at most 50 identifiers;
- fresh signed links, which are valid for 15 minutes and are never persisted;
- the bearer credential referenced by the source configuration.

The client has confirmed that deletion information will be returned through the changes endpoint. The updated
field shape or example deletion record is an implementation prerequisite for mapping the provider record to
`REMOVED`, not a design decision. All other returned document records map to `UPSERT`. Until the deletion
contract arrives, absence from a page or listing must never be interpreted as deletion.

The connector enumerates a fixed window ending at the run start time. Pagination results are deduplicated by
external identifier and change signal. Incremental windows overlap at the previous checkpoint boundary because
the documented time filters are inclusive; idempotent document state absorbs the duplicate boundary record.
The checkpoint advances only after the complete change listing has been read. Document-level failures are
persisted independently, so advancing the listing checkpoint cannot lose them.

## 6. Change detection and document lifecycle

### 6.1 Identity and change signals

The internal document identity is `(source_id, external_document_id)`.

For COMPLY, a changed checksum is the authoritative content-change signal:

- same checksum: persist any updated provider metadata, but do not download, parse or index again;
- changed checksum: create a revision, download, verify and send it to the product adapter;
- downloaded checksum mismatch: fail that document operation and do not call the product adapter.

The connector normalizes the documented `sha256:` form before comparison and verification. The client must
confirm identifier stability and checksum algorithm/requiredness before production activation.

For a future connector that supplies no checksum, the fallback change signal is a composite of its stable
remote identity, file name/path, size and modification timestamp plus any provider revision value. Only a
changed composite signal is downloaded. This is intentionally less authoritative than a checksum and remains
connector-owned.

### 6.2 Independent document behavior

There is no source-level activation gate for either the initial or a recurring import.

- A successfully added document becomes available after Copilot MRO successfully parses and indexes it.
- A successfully changed document replaces its earlier product representation.
- If a changed document fails, its last successful product representation remains available.
- A failed new document remains unavailable until a later attempt succeeds.
- A successful `REMOVED` event makes the document unavailable to agents immediately and removes its
  product-specific records and index entries.
- If removal fails, the previous representation remains until the removal succeeds.

Successful operations are never rolled back because other documents in the run failed.

### 6.3 Revision history and content retention

Revision metadata is append-only for the lifetime of the source, subject to tenant/account erasure. It records
the provider version and metadata, checksum or fallback signal, detection time, processing outcome and removal
event. The revision count therefore reflects content changes identified by checksum or the connector's
fallback signal; metadata-only observations do not create a new content revision.

Raw bytes for the current successful revision remain available as required by the product pipeline. Bytes for
a superseded or removed revision become eligible for cleanup after a per-source retention period configured
between 24 and 48 hours. The initial COMPLY configuration uses 48 hours. Revision metadata survives content
cleanup. Physical deletion follows the object store's deletion policy; the ingestion record stores when
cleanup was requested and completed.

## 7. Scheduling, recovery and retries

Each source stores:

- an IANA timezone;
- one business-hours local time;
- one non-business-hours local time;
- the next due instant.

When a worker recovers and `next_run_at` is in the past, it runs the source once immediately and computes the
next future schedule. It does not replay every missed slot. A database claim prevents overlapping runs for the
same source.

An individual failed document operation remains pending and is reconsidered on the next scheduled sync. The
same document change receives at most five automatic retries after its first failed attempt. A later provider
revision is a new change and begins a new attempt sequence. Exhausted items remain visible in stored status and
email reporting for internal administrator follow-up; the first release does not add a dashboard.

Retries do not disable a source, block successful documents or cause completed product operations to roll
back.

## 8. Run status and email reporting

An actionable document is an addition, change or removal attempted during the run, including a pending retry.
Unchanged documents are excluded. Counts are mutually exclusive final outcomes:

- `added`: new documents successfully ingested;
- `changed`: existing documents successfully updated;
- `removed`: deletion events successfully applied;
- `failed`: actionable documents not successfully applied.

The failure percentage is:

`failed / (added + changed + removed + failed) * 100`

A successful scan with no actionable documents has a zero percent failure rate.

Run statuses are:

| Status | Meaning |
|---|---|
| `completed` | The source scan completed and no actionable document failed. |
| `partially_completed` | The source scan completed and the failure percentage is greater than zero and at most 5%. |
| `needs_attention` | The source scan completed and the failure percentage is greater than 5%. |
| `failed` | The execution began but could not establish or complete a trustworthy source scan, so document percentages are unavailable or unreliable. |

Every run that reaches one of these terminal statuses sends one email report. The report contains source/client,
run window, start/end time, status, added/changed/removed/failed counts, concise failure reasons, retry
eligibility and the next scheduled run. There is no separate escalation counter, recovery email or dashboard.
A process that never launches cannot send its own report and is deliberately outside the first-release scope.

Email recipients are configured per source and restricted to Flynapse operational recipients. Delivery uses
the existing shared email transport; report-delivery failure is logged on the persisted run but does not
change the ingestion outcome.

## 9. Persistence model

The shared repository owns four small Postgres relations:

1. **Sources** — client/source identity, tenant and operator context, product key, connector type, non-secret
   connector configuration, secret reference, schedules, retention, recipients, enabled state and checkpoint.
2. **Documents** — current state for `(source_id, external_document_id)`, current change signal, lifecycle,
   last successful product outcome and retry state.
3. **Document revisions** — append-only metadata and processing outcomes for content revisions and removals.
4. **Runs** — sync window, terminal status, counts, bounded failure summary, report-delivery result and timing.

Credentials and signed URLs are never stored in these tables. Connector credentials live in the deployment's
secret manager; the source row stores only a secret reference.

Writes are source-scoped and tenant/operator context is passed explicitly to the Copilot MRO adapter. Repeated
change records are idempotent: the same source, external document and change signal cannot create or apply the
same revision twice.

## 10. Administration and security

The first release has no UI. Source create/update, enable/disable and retry-reset operations are exposed through
minimal internal administration commands or API routes.

Current tenant-owner/settings-administrator permissions are not sufficient because client administrators must
not configure provider connections. The implementation introduces a Flynapse-internal `platform_admin`
authorization gate, or binds to an existing internal identity-provider role only if it has the same
cross-tenant staff-only meaning. Server-side authorization is authoritative; no dashboard-only guard is
accepted.

Connector calls use bounded timeouts, redact credentials and signed URLs from logs, and validate download size
and checksum before product processing. Each run and document operation carries stable source, run and external
document identifiers in logs and traces, without logging document contents or credentials.

## 11. Failure boundaries

- A provider authentication, listing or pagination failure produces a `failed` run. The checkpoint does not
  advance.
- A download, checksum, parse, index or delete failure is document-scoped. It contributes to `failed` count
  and the run is classified from the percentage.
- A report-email failure does not rewrite the ingestion status; the persisted run records delivery failure.
- A worker restart cannot create concurrent runs for one source because the source claim is durable.
- A repeated inclusive-window record is a no-op after its revision identity has already succeeded.
- A new or changed document is never considered successful until the Copilot MRO adapter confirms its complete
  parse/catalog/index operation.

## 12. Validation strategy

The implementation must prove the following without depending on a live COMPLY environment:

- connector contract tests for pagination, 50-ID link batches, signed-link refresh, checksum normalization,
  mixed success/error responses and the client-supplied deletion record;
- runner unit tests for unchanged, added, changed, removed and checksum-mismatch paths;
- status tests at 0%, exactly 5% and greater than 5% failure boundaries;
- retry tests proving the next-run pickup and five-retry ceiling;
- schedule tests for both local times, timezone conversion, recovery catch-up and overlap prevention;
- repository tests for idempotency, checkpoint advancement and append-only revision metadata;
- report tests proving counts, status and delivery are attempted for every terminal run;
- a Copilot MRO adapter integration test that uses the existing parser/index path and a deletion test that
  removes all product representations;
- an end-to-end fixture run showing that successful documents remain usable when neighboring documents fail;
- a second fake connector in tests only, proving the runner has no COMPLY-specific branches;
- an import/dependency test proving `document-ingestion` does not import Copilot MRO or Document Hub.

Production activation additionally requires the client's updated deletion record, confirmation that document
IDs are stable across revisions, and confirmation of checksum format and requiredness.

## 13. Acceptance criteria

The first release is complete when:

1. A configured COMPLY source runs twice daily in its timezone and once immediately after a missed due time
   when the worker recovers.
2. The first and later scans make each successfully processed document available without waiting for the full
   source.
3. Same-checksum records are not downloaded or reprocessed; changed checksums are downloaded and verified.
4. COMPLY deletion events remove the corresponding Copilot MRO document from agent use.
5. A failed addition, change or removal does not disable the source or undo successful operations.
6. Run status follows the agreed four-state model and one report email is attempted after every terminal run.
7. Revision metadata remains queryable after superseded content cleanup.
8. Only Flynapse internal platform administrators can configure or operate sources.
9. No implementation code imports or depends on Document Hub.
10. Adding a second provider for Copilot MRO requires a connector and registration/configuration only; adding a
    second product requires a product adapter and composition registration, not changes to the runner.

## 14. Current-code evidence and constraints

- The API already contains a standalone automation-worker entry point and a feature wiring registry
  (`api/flynapse_api/automations/worker.py`, `api/flynapse_api/automations/loop.py`).
- Current infrastructure runs the scheduler embedded in the API and explicitly deploys no standalone worker
  (`iac/dev.tfvars`, `iac/alarms.tf`); deploying the existing worker is implementation work.
- Copilot MRO already owns parser routing and LlamaIndex ingestion
  (`copilot_mro/app/services/s3_pdf_processor.py`,
  `copilot_mro/app/services/llama_index/llama_index_ingestion.py`).
- The estate already has a shared SMTP email transport
  (`core/core/resources/notifications/services/email_dispatcher.py`, `utils/utils/smtp_email_service.py`).
- Existing authorization exposes tenant-owner and capability concepts, not a confirmed Flynapse-internal
  platform-administrator boundary (`api/flynapse_api/middleware/auth.py`,
  `dashboard/components/features/settings/settingsAdminAccess.ts`).
- Document Hub is explicitly a tenant/operator user-library feature with its own capabilities and lifecycle;
  it is evidence for keeping this pipeline separate, not a component of this design.

## 15. Deliberately deferred work

- Additional provider connectors and provider-specific capabilities not needed by COMPLY.
- A source-management dashboard.
- Independent missed-schedule monitoring or escalation.
- Cross-product fan-out from one source in a single run.
- Horizontal ingestion-worker scaling beyond the durable one-source claim.
- A generic product adapter/plugin discovery framework.
- Optimization based on production volume measurements.
