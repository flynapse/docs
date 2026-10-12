# Client document ingestion — design

Status: **Approved for implementation planning (2026-10-08; amended through 2026-10-10).** This document records the
architecture and product decisions agreed during design discussion and the corrections accepted in subsequent
reviews. The 2026-10-09 amendment keeps source-level revision tracking in the shared package while moving every
parser-specific revision and publication decision into the consuming product, and reduces new shared storage to
the two relations that do not already exist. The 2026-10-10 review carries the automation take's native
`started_at` fence through downstream writes and separates ingestion business outcome from the carrier's
technical lifecycle status. It does not by itself authorize implementation; execution begins only from an
approved implementation plan.

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
- Persist source configuration, source-level revision metadata, retry state and checkpoints in the two shared
  relations, and persist execution summaries on the existing `automation_runs` row.
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
- checkpoints, source-level revision metadata and retry state;
- source-document staging and retention eligibility;
- run status calculation;
- email report composition and delivery through the existing shared email utility.

It does not import Copilot MRO, Document Hub, FastAPI or dashboard code. It is a library loaded into the
automation worker, not an independently deployed application.

The initial package should stay small. Logical modules are `connectors`, `models`, `runner`, `repository`,
`scheduling` and `reporting`. These are code-organization boundaries, not independently deployed components.

### 4.2 Copilot MRO

Copilot MRO owns a `ProductDocumentConsumer` adapter that implements three operations:

- ingest a downloaded document and normalized metadata using existing Copilot MRO parsing, cataloguing and
  indexing behavior, returning an opaque durable product outcome only after the product's own success criteria
  are satisfied;
- remove a document from every Copilot MRO datastore and index in which that ingestion placed it;
- expose the existing cleanup contract without enabling automated physical deletion until retention and deletion
  requirements are approved.

**Phase 3 MVP amendment (2026-10-13):** Phase 3 guarantees logical publication and non-retrievability, not
physical artifact reclamation. It keeps immutable generation-qualified artifacts, one product writer, exact
source/carrier fencing and an active publication pointer. It does not add durable per-provider-call admission,
write-close leases, cleanup ownership/takeover, timed quiescence, rollback orchestration or an automated physical
cleanup worker. A failed, superseded or removed generation may leave non-visible residue recorded in its bounded
manifest. Reclamation and rollback are later work after the client retention policy is known.

The adapter owns mapping client document metadata to Copilot MRO parser choices, tenant/operator attribution,
product metadata, product-side revision handling and deletion details. Phase 3 first inventories the existing
`mro_documents`, `pilot_documents`, `crew_documents`, `chunks`, parser-specific Postgres relations, S3 layouts
and Weaviate objects. It reuses them wherever they can satisfy product invariants and adds a product-owned
column or relation only when that inventory proves a concrete gap. No shared design mandates an active-revision
pointer, binding table, revision-qualified artifact layout or cutover algorithm.

The shared call context carries the source revision identity and ordinal plus carrier run, attempt and the
winning one-shot take's `started_at`. Copilot MRO uses those inputs in its own idempotency and stale-execution
rules, chosen to match the parser family and its existing stores. The attempt remains a useful retry counter,
but it is not a unique worker identity: recovery can briefly leave two executions in the same attempt
namespace. The shared runner validates only the closed operation outcome and treats the remaining outcome
payload as opaque product data. Unsupported or unclassifiable documents return a document-level failure; they
do not move product-specific logic into the shared runner.

Copilot MRO depends on the shared contract. The shared repository never depends on Copilot MRO. The API worker
is the composition root that imports both.

### 4.3 API automation worker and infrastructure

The existing standalone automation worker is the execution host. The first implementation enables and deploys
that worker rather than introducing an ingestion-specific service. The API process no longer needs to perform
the heavy synchronization work in a request path.

The worker installs one ingestion feature wiring module. On each scheduler tick it asks the shared package for
due sources, tenant by tenant under the existing tenancy binding. Each source occurrence is enqueued as an
idempotent existing one-shot automation run; that run row is the sole claim, lease, recovery and fencing
authority. Its occurrence key makes a repeated enqueue of the same `(source_id, scheduled_for)` return the
existing run, closing the enqueue/advance crash gap; its active source key prevents a later scheduled or manual
occurrence from starting while an earlier occurrence for that source is still claimed or running. Both keys
belong to the same run row, not to a second source lease. The source schedule advances only after the durable
occurrence enqueue succeeds. Source schedules and checkpoints remain owned by `document-ingestion`, not by
user chat-automation definitions.

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

- `GET /qp-fileshare-service/api/comply/documents/changes` for initial enumeration and incremental windows;
- `POST /qp-fileshare-service/api/comply/documents/download-links` in batches of at most 50 identifiers;
- fresh signed links, which are valid for 15 minutes and are never persisted;
- the bearer credential referenced by the source configuration.

The 2026-10-09 vendor guide and its authoritative UAT Swagger contract define a required `status` field with
the values `new`, `updated`, and `deleted`. `new` and `updated` map to `UPSERT`; `deleted` maps to `REMOVED`.
A deleted record is not downloaded and may have a null or omitted checksum. Absence from a page or listing is
never interpreted as deletion.

The authoritative change schema requires `id`, `name`, `last_updated`, and `status`. It currently treats
`checksum` as optional and nullable and does not advertise the older document metadata fields (`version`,
`size_bytes`, `document_type`, or `updated_by`). The connector may preserve additional fields as opaque
provider metadata, but it must not depend on those older fields. The download-link response filename is
validated as response data but does not replace the name from the staged change record.

The initial import enumerates the complete source without time filters; "100% initial import" means every page
must be read and staged before that scan is trustworthy, not that already-successful documents wait for failed
neighbors before publication. Incremental imports enumerate a fixed window ending at the run start time.
Pagination results are deduplicated by external identifier and change signal. Incremental windows overlap at
the previous checkpoint boundary because the documented time filters are inclusive; idempotent document state
absorbs the duplicate boundary record.

Every normalized record in the fixed window is staged durably before processing. Staging the complete set and
compare-and-set advancing the old checkpoint to the window end occur in one database transaction. A partial or
unstable listing leaves the checkpoint unchanged. The guide confirms newest-first (`last_updated` descending)
ordering, which the connector validates within and across pages. Before production activation, COMPLY must
still confirm the snapshot behavior of filtered pagination; if it is not snapshot-stable, the connector must
use an agreed stabilizing re-scan/reconciliation rule rather than assuming page-number pagination is lossless.
Document-level failures are processed from staged records independently after the checkpoint transaction, so
checkpoint advancement cannot lose them.

## 6. Change detection and document lifecycle

### 6.1 Identity and change signals

The internal document identity is `(source_id, external_document_id)`.

For COMPLY, a changed checksum is the authoritative content-change signal:

- same checksum on an active document: persist any updated provider metadata, but do not download, parse or
  index again;
- changed checksum: create a revision, download, verify and send it to the product adapter;
- `deleted`: create a removal revision from the required provider status without requiring or synthesizing a
  checksum, and do not request a download link;
- `UPSERT` after the document is tombstoned: create a higher-ordinal revision and reingest even if its checksum
  matches the last active revision; a prior removal cannot turn a reappearance into a metadata-only no-op;
- downloaded checksum mismatch: fail that document operation and do not call the product adapter.

For `new` and `updated`, the connector normalizes the documented `sha256:` form before comparison and
verification. It never treats a missing, abbreviated, or malformed digest as authoritative content proof: such
an active record is parked/failed for the run and is never assigned the fallback metadata signal. Before the
source checkpoint advances, that parked observation is written atomically to the existing source-revision
history with its provider timestamp, metadata and bounded failure code. It becomes the current observation and
supersedes every older unfinished revision for that document, so neither a brand-new invalid record nor a newer
invalid record can disappear after one report or allow older work to resume. An exact replay is a no-op; a later
valid higher-timestamp observation supersedes the parked row and starts its own attempt sequence. This uses the
existing revisions relation and does not create a third table or relax `NormalizedChange` checksum validity.
The examples in the supplied API document are shortened, so production requires the client to confirm that
real active responses contain the complete digest. The client must confirm identifier stability and
active-document checksum algorithm/requiredness before production activation. A null checksum on `deleted` is
valid and does not weaken the active-document rule.

For a future connector that supplies no checksum, the fallback change signal is a composite of its stable
remote identity, file name/path, size and modification timestamp plus any provider revision value. Only a
changed composite signal is downloaded. This is intentionally less authoritative than a checksum and remains
connector-owned.

### 6.2 Independent document behavior

There is no source-level activation gate for either the initial or a recurring import.

- A successfully added document becomes available only after Copilot MRO satisfies the publication guarantees
  defined for the selected parser family and reports success.
- A successfully changed document replaces or supersedes its earlier product representation according to that
  product-owned strategy only after the new representation satisfies the same guarantees.
- If a changed document fails, its last successful product representation remains available.
- A failed new document remains unavailable until a later attempt succeeds.
- A `REMOVED` event is successful only after the product reports that the document is no longer retrievable.
  Phase 3 removes or gates every live product reference, but it does not physically reclaim generation-qualified
  S3/Weaviate residue. That later cleanup cannot be allowed to reactivate a document.

Successful operations are never rolled back because other documents in the run failed.

### 6.3 Revision history and content retention

Revision metadata is append-only for the lifetime of the source, subject to tenant/account erasure. It records
the provider version and metadata, checksum or fallback signal, detection time, processing outcome and removal
event. The revision count therefore reflects content changes identified by checksum or the connector's
fallback signal; metadata-only observations do not create a new content revision.

Raw bytes for the current successful revision remain available as required by the product pipeline. Bytes for
a superseded or removed revision become eligible for cleanup after a per-source retention period configured
between 24 and 48 hours. The initial COMPLY configuration uses 48 hours. Revision metadata survives content
cleanup. Cleanup eligibility is a logical ingestion state, not a promise that every physical byte has already
been erased. Physical deletion follows the object store's versioning and lifecycle policy; the ingestion record
stores eligibility, request and verified-completion times separately. A stricter physical-erasure SLA is
deferred until the client supplies its retention requirement.

## 7. Scheduling, recovery and retries

Each source stores:

- an IANA timezone;
- one business-hours local time;
- one non-business-hours local time;
- the next due instant.

When a worker recovers and `next_run_at` is in the past, it enqueues the source once immediately and computes
the next future schedule. It does not replay every missed slot. The idempotent one-shot run row for that source
occurrence prevents overlap, is re-queued by the existing stale-run recovery path after a worker crash, and
fences a superseded worker execution from settling current state. The fence is the take's exact `started_at`,
not the retry number alone.

An individual failed document operation remains pending and is reconsidered on the next scheduled sync. The
same document change receives at most five automatic retries after its first failed attempt. A later provider
revision is a new change and begins a new attempt sequence; it atomically marks every older pending or failed
revision for that document `superseded`, and those older revisions must never run or publish afterward.
Exhausted items remain visible in stored status and email reporting for internal administrator follow-up; the
first release does not add a dashboard.

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

Ingestion business statuses are:

| Status | Meaning |
|---|---|
| `completed` | The source scan completed and no actionable document failed. |
| `partially_completed` | The source scan completed and the failure percentage is greater than zero and at most 5%. |
| `needs_attention` | The source scan completed and the failure percentage is greater than 5%. |
| `failed` | The execution began but could not establish or complete a trustworthy source scan, so document percentages are unavailable or unreliable. |

Every run that reaches one of these terminal business statuses attempts one email report. The report contains
source/client, run window, start/end time, status, added/changed/removed/failed counts, concise failure reasons,
retry eligibility and the next scheduled run. Current-run counts stay limited to operations attempted in that
run; an additional backlog section reports unresolved and retry-exhausted revisions so they cannot disappear
from view after their failure run. There is no separate escalation counter, recovery email or dashboard. A
process that never launches cannot send its own report and is deliberately outside the first-release scope.

Email recipients are configured per source and restricted to Flynapse operational recipients. Delivery uses
the existing shared email transport; report-delivery failure is logged on the persisted run but does not
change the ingestion outcome.

## 9. Persistence model

The shared repository adds only two Postgres relations:

1. **Sources** — client/source identity, tenant and operator context, product key, connector type, non-secret
   connector configuration, secret reference, schedules, retention, recipients, enabled state and checkpoint.
2. **Document revisions** — source-level identity, append-only content/removal history and processing outcomes.
   Each row carries `(source_id, external_document_id)`, change signal, provider metadata, ordinal, operation,
   attempt state, the owning carrier run/attempt/`started_at` fence, supersession and raw-content cleanup state.
   A partial unique current-row constraint provides the latest source observation without a separate documents
   table. Same-signal metadata updates the current row and does not create a content revision.

The existing tenant-scoped `automation_runs` relation is the only execution record. Its existing `params`
contains the source/occurrence context and its existing structured `result` contains the fixed sync window,
business status, outcome counts, bounded failures, backlog summary, next schedule and report-delivery state.
The four ingestion outcomes live under a namespaced object in `result`; they are not new values for the
generic `automation_runs.status` column. That column remains the carrier's technical worker lifecycle. A
handled sync whose business outcome is `failed` or `needs_attention` can therefore close the carrier
technically `completed` after persisting and reporting the truthful business result. An unhandled exception or
timeout closes the carrier technically failed/timed out and must not invent document counts. The run's normal
lifecycle columns remain the worker claim, recovery and execution audit. No
`document_ingestion_documents` or `document_ingestion_runs` relation is added.

Credentials and signed URLs are never stored in these tables. Connector credentials live in the deployment's
secret manager; the source row stores only a secret reference.

Both new relations are tenant-classed with tenant-leading keys and forced row-level security; the existing
`automation_runs` relation already has tenant RLS. Global discovery uses the existing paged tenant registry,
then binds exactly one tenant and the source's declared operator for source reads, connector state, adapter work
and settlement. An immutable execution context carries tenant, operator, source, product, source revision,
carrier run/attempt and carrier `started_at` through every adapter call. Repeated change records are idempotent:
the same source, external document and change signal cannot create or apply the same source revision twice.

## 10. Administration and security

The first release has no UI. Source create/update, enable/disable and retry-reset operations are exposed through
minimal internal administration commands or API routes. Tenant, operator, product, connector type and provider
identity are immutable after the first run; reassignment creates a new source and explicitly decommissions the
old one. Every privileged mutation records actor, reason, time and the before/after configuration revision, and
ingestion cleanup participates in tenant/operator erasure rather than leaving orphaned state.

Current tenant-owner/settings-administrator permissions are not sufficient because client administrators must
not configure provider connections. The implementation introduces a Flynapse-internal `platform_admin`
authorization gate, or binds to an existing internal identity-provider role only if it has the same
cross-tenant staff-only meaning. Server-side authorization is authoritative; no dashboard-only guard is
accepted.

Connector calls use bounded timeouts, redact credentials and signed URLs from logs, and validate download size
and checksum before product processing. API calls and signed-link downloads use separate clients; bearer tokens
and cookies are never forwarded to the storage host. Downloads require HTTPS, an approved host, redirect
revalidation, rejection of private/link-local destinations and a hard streaming byte cap before checksum
verification. Each run and document operation carries stable source, run and external document identifiers in
logs and traces, without logging document contents or credentials.

## 11. Failure boundaries

- A provider authentication, listing or pagination failure produces a `failed` run. The checkpoint does not
  advance.
- A download, checksum, parse, index or delete failure is document-scoped. It contributes to `failed` count
  and the run is classified from the percentage.
- A report-email failure does not rewrite the ingestion status; the persisted run records delivery failure.
- A worker restart cannot create a second active carrier row for one source. Recovery can briefly overlap a
  zombie and a fresh execution of that row, so every shared/result/product mutation is fenced to the winning
  take's exact `started_at`; the retry number alone is insufficient.
- A repeated inclusive-window record is a no-op after its revision identity has already succeeded.
- A later `UPSERT` for a removed document creates a higher-ordinal revision even when it repeats the old
  checksum; only that newer revision may reactivate the document.
- A newer revision supersedes older pending work before either can publish, and superseded work is never
  retried.
- A new, changed or removed document is never considered successful until the product adapter confirms the
  product-defined operation outcome. The shared runner does not inspect or prescribe the product's internal
  revision, publication or removal mechanism.

## 12. Validation strategy

The implementation must prove the following without depending on a live COMPLY environment:

- connector contract tests for newest-first pagination, 50-ID link batches, signed-link refresh, checksum
  normalization, mixed success/error responses, and authoritative `new`/`updated`/`deleted` records;
- runner unit tests for unchanged, added, changed, removed and checksum-mismatch paths;
- status tests at 0%, exactly 5% and greater than 5% failure boundaries;
- retry tests proving the next-run pickup, five-retry ceiling and newer-revision supersession;
- schedule tests for both local times, timezone conversion, idempotent enqueue, recovery catch-up and overlap
  prevention;
- repository tests for tenant isolation, idempotency, atomic staging/checkpoint advancement, page mutation and
  append-only content/removal revision history plus in-place same-signal current-metadata updates;
- report tests proving current-run counts, unresolved/exhausted backlog and delivery are attempted for every
  terminal run;
- a Copilot MRO adapter assessment that inventories existing product tables and artifacts before any schema is
  added, followed by integration tests for the selected parser-family publication and deletion strategy;
- an end-to-end fixture run showing that successful documents remain usable when neighboring documents fail;
- a second fake connector in tests only, proving the runner has no COMPLY-specific branches;
- an import/dependency test proving `document-ingestion` does not import Copilot MRO or Document Hub.

Production activation additionally requires confirmation that document IDs are stable across revisions,
confirmation of active-document checksum format and requiredness, and confirmation of the snapshot behavior of
time-filtered pagination. Ordering direction and deletion mapping are now resolved by the vendor guide and
authoritative Swagger contract. Missing COMPLY checksums on `new` or `updated` records are deliberately not
assigned a fallback until the client answers the active-checksum contract question.

## 13. Acceptance criteria

The first release is complete when:

1. A configured COMPLY source runs twice daily in its timezone and once immediately after a missed due time
   when the worker recovers.
2. The first and later scans make each successfully processed document available without waiting for the full
   source.
3. Same-checksum records are not downloaded or reprocessed; changed checksums are downloaded and verified.
4. COMPLY deletion events immediately remove the corresponding Copilot MRO document from agent use; Phase 3
   records but does not physically reclaim generation-qualified residue.
5. A failed addition, change or removal does not disable the source or undo successful operations.
6. Run status follows the agreed four-state model and one report email is attempted after every terminal run.
7. Revision metadata remains queryable after superseded content cleanup.
8. Only Flynapse internal platform administrators can configure or operate sources.
9. No implementation code imports or depends on Document Hub.
10. Adding a second provider for Copilot MRO requires a connector and registration/configuration only; adding a
    second product requires a product adapter and composition registration, not changes to the runner.
11. A newer provider revision prevents every older failed revision of the same document from running or
    publishing afterward.

## 14. Current-code evidence and constraints

- The API already contains a standalone automation-worker entry point and a feature wiring registry
  (`api/flynapse_api/automations/worker.py`, `api/flynapse_api/automations/loop.py`).
- Current infrastructure runs the scheduler embedded in the API and explicitly deploys no standalone worker
  (`iac/dev.tfvars`, `iac/alarms.tf`); deploying the existing worker is implementation work.
- Copilot MRO already owns parser routing and LlamaIndex ingestion
  (`copilot_mro/app/services/s3_pdf_processor.py`,
  `copilot_mro/app/services/llama_index/llama_index_ingestion.py`).
- Copilot MRO already owns the `mro_documents`, `pilot_documents`, `crew_documents` and `chunks` relations plus
  parser-specific manual relations; Phase 3 must reuse these wherever possible and justify any additional
  product schema from a demonstrated invariant gap.
- Core's existing tenant-scoped `automation_runs` relation already stores one-shot context and a structured
  result, so ingestion adds only generic occurrence/concurrency keys rather than a second run ledger.
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
