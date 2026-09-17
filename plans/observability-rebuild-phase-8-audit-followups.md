# Observability Rebuild — Phase 8 Detail Plan: Audit Follow-ups and Production Readiness

> **For agentic workers:** use `superpowers:executing-plans` or
> `superpowers:subagent-driven-development`. Complete one task at a time, write the test first, and pause for
> owner review at every gate. Master plan: `docs/plans/observability-rebuild.md`, Phase 8. Audit basis:
> `docs/plans/observability-rebuild-audit.md` plus the owner decisions recorded below.

**Goal.** Close the remaining audit gaps without changing the accepted architecture: two application
contracts, a native Flynapse client dashboard backed by PostgreSQL, vendor-neutral operational telemetry
through the existing OpenTelemetry Collector, and deployment-owned destination adapters.

**Deployment boundary.** The current target is one Docker host per client deployment. This phase must not
introduce Kubernetes. The design may later be replicated across hosts because application containers continue
to emit the same OTLP contract to a configured Collector endpoint.

## 1. Decisions this phase must preserve

1. **Keep the two application contracts.** Operational traces, metrics and logs use OTLP. Approved product
   events use `POST /analytics/events` and are stored in tenant-scoped PostgreSQL tables. Do not route product
   events through the Collector and do not make telemetry stores authoritative for product reporting.
2. **Keep product analytics in Core.** The Product Analytics API, panel registry, authorization and RLS-backed
   reads remain in `core`; this phase does not move them into `copilot-mro`.
3. **Keep the current content policy.** Prompts, responses, retrieval text and tool inputs/results remain off by
   default. When Phase 3.5/3.6 implements controlled capture, it may be enabled only through that configuration;
   the current Collector-side suppression must not be mistaken for a completed application capture path.
4. **Allow tenant identity on deliberately tenant-scoped metrics.** It is a bounded exception, not a general
   labeling rule. User, session, chat, document and request identifiers remain forbidden metric dimensions.
5. **Keep restricted PostgreSQL access for operational dashboards.** Grafana may use `flynapse_readonly` for
   approved product panels; it must not become an application dependency.
6. **Keep the client inside Flynapse.** The client-facing dashboard remains part of the Flynapse UI. It does not
   redirect to, embed credentials for, or branch on Grafana, New Relic, Azure Monitor or CloudWatch.
7. **Keep the current Docker-native POC stack.** Phoenix becomes optional. Evaluation of a consolidated
   `otel-lgtm` container is deferred and is not an implementation task in this phase.

## 2. Data and control flow after Phase 8

| Concern | Producer | Boundary and storage | Consumer |
|---|---|---|---|
| Operational traces, metrics and logs | Shared OTel instrumentation in application services and browser telemetry | OTLP to the existing Collector; Collector profile sends to the current OSS stores in POC or the selected client platform in production | Restricted Grafana dashboard in the POC, or the client's New Relic, Azure Monitor or CloudWatch views |
| Approved product events | Flynapse UI product-event client | Authenticated Product Analytics API to tenant-scoped PostgreSQL | Flynapse UI content dashboard; approved backend product panels may read through the API or `flynapse_readonly` |
| Server-derived turn facts and LLM cost | Agent SDK and LangGraph runtime persistence paths | `chat_turn_facts`, `llm_usage` and `llm_model_calls` in PostgreSQL | Flynapse UI product analytics and approved backend product panels |
| Dashboard selection | Per-client profile stored server-side | Core resolves configured panels against supported panels, tenant features and authenticated role permissions | The same Flynapse UI build renders only the effective view set |
| Destination selection | Deployment configuration and secrets | Collector overlay; never returned to the browser | Deployment owner selects OSS, AWS, Azure or New Relic independently of the Flynapse UI profile |

The Flynapse UI and backend/operator dashboards can show overlapping product facts, but they do not have the
same scope. The Flynapse UI reads the Product Analytics API. The backend/operator experience combines
operational telemetry from its selected telemetry store with only the approved PostgreSQL product panels.

## 3. Sequencing and ownership

**Branch strategy (updated 2026-09-08):** use the local `obs-non-agent` branch name independently in Core,
dashboard, copilot-mro and utils. Core/dashboard retain the existing uncommitted Phase 8.1 work and 8.2 follows
it sequentially because their analytics files overlap. Copilot-mro/utils carry Phase 1c; MRO-only 8.4 and the
configuration portion of 8.5 follow as separate commits. A common name is a coordination label, not a shared Git
history or permission to mix the operational-telemetry and product-event contracts.

| Task | May start | Depends on | Owns |
|---|---|---|---|
| 8.0 Current-state reconciliation | immediately | latest checked-out branches | status and contract baseline only |
| 8.1 Product-event reliability | after 8.0 | current Phase 4/5 event path | event identity, versioning and deduplication |
| 8.2 Per-client Flynapse UI profiles | after 8.0 | current Core panel registry and dashboard registry | server-owned effective view contract |
| 8.3 Turn-fact/runtime completion gate | after Gate M and Task R | Phase 3.2, 3.3 and 3.7 | parity and reconciliation; no second writer |
| 8.4 Optional Phoenix packaging | after 8.0 | current Docker compose profiles | optional POC footprint only |
| 8.5 Production destination readiness | after 8.0; live sends require client credentials | Phase 2 Collector boundary | deployment adapters, durability and canaries |
| 8.6 Final acceptance | last | 8.1–8.5, Phase 1c and required Stream L work | cross-repository proof and plan closeout |

Tasks 8.1, 8.2, 8.4, Phase 1c and configuration-only parts of 8.5 may run independently. Phase 1c is limited to
the stable non-agent paths and safety guard defined in the master plan. Task 8.3 must not bypass Gate M or Task R.
Task 8.6 cannot close while Phase 1c, the gated Phase 0 chat cleanup, Phase 1b runtime handoff or required Phase 3
work is unfinished, or while a required provider is represented only by configuration validation.

## 4. Tasks

### Task 8.0 — Reconcile the plan with the current branches

**Files:** update `docs/plans/observability-rebuild-research/08-post-migration-rescoping.md`; update the master
plan's status ledger. Do not change application code in this task.

- [x] Re-run the focused inventory against current `api`, `core`, `copilot-mro`, `dashboard`, `utils` and
      `iac` branches. Record observed implementation separately from planned work.
- [x] Confirm whether Gate M can be declared. If it cannot, identify the remaining merge dependency and leave
      Task 8.3 blocked without blocking the other Phase 8 tasks.
- [x] Pin the current Product Analytics API, product-event wire, table keys, Collector overlays, Docker services,
      Phoenix coupling, dashboard registries and both agent runtimes.
- [x] Reconcile stale master-plan checkboxes and links. Historical implementation notes remain historical and
      must not be rewritten as current facts.

**Acceptance:** every Phase 8 task begins from a file-level current-state table; no item is marked implemented
solely because it exists in an older plan.

### Task 8.1 — Make product-event delivery idempotent and versioned

**Files:** modify `dashboard/lib/telemetry/product-events.ts`,
`dashboard/tests/unit/telemetry/product-events-client.test.ts`,
`dashboard/tests/unit/telemetry/ingest-contract.test.ts`,
`core/core/resources/analytics/schemas.py`, `events_store.py`, `events_endpoints.py`,
`core/core/db/table_definitions.py`, `core/tests/unit/analytics/test_product_events_schema.py`,
`core/tests/unit/db/test_product_events_definition.py`, `core/tests/api/analytics/test_events_endpoint.py`, and
`core/tests/db/analytics/test_product_events_store_db.py`. Use the existing registry migration path; edit the
migration runner only if the failing migration test proves it is required.

**Contract:**

- The browser creates one stable `event_id` when an event enters the in-memory queue and retains it across
  retries and batch replay. Browser reload durability is not added in this phase.
- Every newly produced event carries an explicit `schema_version` from a single frontend contract constant.
- Core accepts the old and new shapes during the rollout window. Missing identity/version fields receive
  server-generated compatibility values; new Flynapse UI code must always send both.
- PostgreSQL uses the existing tenant-scoped primary key ending in `event_id`. Inserts ignore that key's
  conflicts and return separate accepted and duplicate counts.
- Only newly accepted rows are re-emitted as operational log records. A duplicate retry must not look like a
  newly accepted business event.

**Steps:**

- [x] Add failing frontend tests proving identity is assigned before enqueue, survives a retry, and remains
      unchanged when the same queued batch is posted again.
- [x] Add failing Core schema and endpoint tests for UUID validation, schema-version validation, backward
      compatibility and the accepted-versus-duplicate response.
- [x] Add failing database tests proving two posts of the same tenant/event key create one row, while the same
      event key in two tenants remains isolated.
- [x] Implement the contract from browser queue through endpoint and PostgreSQL, then run the focused frontend,
      Core unit, API and database suites.
- [x] Document the compatibility window and the future removal gate for server-generated event identity. Do not
      add IndexedDB or a Collector route for product events.

**Acceptance:** retrying a batch cannot double-count a product event; existing deployed clients still receive a
successful response; the endpoint reports duplicates; RLS and cross-tenant tests remain green.

### Task 8.2 — Add a per-client Flynapse UI dashboard profile

**Files:** create `core/core/resources/analytics/dashboard_profiles.py`; modify
`core/core/resources/analytics/{analytics_endpoints.py,panel_service.py,registry.py,schemas.py}` and
`core/core/db/table_definitions.py`; add Core unit/API/database tests under `core/tests/{unit,api,db}/analytics/`.
Modify `dashboard/lib/api/analytics-api.ts`,
`dashboard/components/features/analytics/analytics-panel-registry.ts`, and
`dashboard/app/(dashboard)/settings/department/dashboard/page.tsx`; extend the corresponding dashboard tests
under `dashboard/tests/unit/analytics/`.

**Contract:**

- Store one server-owned dashboard profile per tenant/client in PostgreSQL, with a profile version and an
  allow-list of panel IDs. Seed a safe default through the existing table registry/provisioning path.
- Core returns an effective dashboard profile calculated as:
  configured client panels intersected with registered backend panels, enabled tenant features and the
  authenticated caller's role/capabilities.
- The profile response contains only presentation capabilities required by the Flynapse UI: effective tabs,
  panel IDs, field/redaction flags and a version. It never contains the observability destination, exporter
  credentials or vendor query details.
- Every panel request retains its existing server authorization. Hiding a panel in the UI is not an access
  control.
- Sensitive views such as user rankings, question excerpts and Improvement remain explicitly controllable.

**Steps:**

- [ ] Write the resolver tests first: configured versus supported panels, feature gating, owner/capability
      intersection, unknown panel fail-closed behavior, and deterministic output ordering.
- [ ] Add RLS tests proving one tenant cannot read or alter another tenant's profile.
- [ ] Add the authenticated profile endpoint and tests proving a caller cannot request a wider profile or
      supply a tenant identity.
- [ ] Change the Flynapse UI registry/page to render the effective profile. Test POC-safe, restricted-client,
      tenant-owner and capability-holder views using the same frontend build.
- [ ] Verify that changing a dashboard profile neither changes Collector configuration nor exposes an external
      observability link to ordinary client users.

**Acceptance:** a server-side per-client change alters the next Flynapse UI dashboard response without a
frontend rebuild; unsupported or unauthorized panels never appear; direct panel calls remain protected.

### Task 8.3 — Close `chat_turn_facts` and dual-runtime coverage

**Ownership:** Phase 3.7 remains the only online `chat_turn_facts` writer task. Phase 8 must not add a second
writer or a second projection implementation. Begin only after Gate M, Task R and the refreshed backend signal
catalogue.

**Likely files after Task R:** the shared Agent SDK/LangGraph completion and persistence boundary under
`copilot-mro/copilot_mro/app/services/agent_shared/`, runtime adapters under `agent_claude/` and `lang_agent/`,
the block-save path, `agent_shared/telemetry.py`, `agent_shared/model_call_ledger.py`, and their focused tests;
`core/scripts/backfill_chat_turn_facts.py` plus its projection, drift-pin and database tests.

- [ ] Let the original Stream L owners complete the gated Phase 0 chat cleanup, Phase 1b runtime handoff and
      Phase 3 against
      the post-merge call graph. Task 8.3 coordinates the Phase 3.2, 3.3 and 3.7 parity/reconciliation proof;
      it must not create competing implementations.
- [ ] Persist the facts row in the same transaction as the successful block save and make the write idempotent
      on the tenant/block key.
- [ ] Prove Agent SDK and LangGraph produce the same required fact fields, cost completeness semantics, span
      names and bounded metric attributes for equivalent outcomes.
- [ ] Reconcile online projection and backfill output at the same `facts_version`; prove reruns do not duplicate
      or regress newer rows.
- [ ] Confirm the previously dark quality, reliability, LLM and agent panels receive real signals. Adjust the
      dashboard catalogue to actual emitted names rather than adding synthetic emitters.

**Acceptance:** successful turns from both runtimes produce one matching block, facts row and ledger record;
failed turns follow the ruled persistence behavior; backfill and online projection agree; mapped operational
panels are queryable with real data.

### Task 8.4 — Make Phoenix optional in the current Docker POC

**Files:** modify the applicable Docker compose files and `copilot-mro/deployment/otel/README.md`; add a
Phoenix-specific compose override if that is the smallest clean separation; extend
`copilot-mro/tests/integration/otel/test_collector_profiles.py`, `test_profile_env_documented.py` and relevant
compose smoke tests.

- [x] Make the default single-host Docker stack boot without Phoenix secrets, the Phoenix service or the
      `content-phoenix.yaml` Collector fragment.
- [x] Provide one explicit optional Docker activation path that starts Phoenix and adds only the content
      pipeline fragment. Keep the existing content opt-out, tenant isolation and retention rules.
- [x] Prove the default OSS trace/metric/log canary passes without Phoenix and the optional LLM trace/eval
      canary passes with it.
- [x] Keep the current separate Collector, Loki, Prometheus, Tempo and Grafana containers. Record `otel-lgtm`
      only as a deferred evaluation; do not add its image, compose service or migration work here.

**Acceptance:** `docker compose up` for the base POC has no Phoenix dependency; enabling the documented optional
profile adds Phoenix without changing application images or the operational OTLP pipelines.

**Implementation note — 2026-09-09:** completed in `copilot-mro` branch `obs-non-agent`.
Default root and POC Docker stacks now load only `base.yaml + backend-oss.yaml`; Phoenix is enabled only through
`deployment/docker-compose.phoenix.yml` or `deployment/poc/docker-compose.phoenix.yml`. Validation evidence:
root/POC compose config passed for default and Phoenix variants; live default OSS smoke passed 4 tests without
Phoenix; live optional Phoenix smoke passed the content-copy test. `otel-lgtm` remains deferred.

### Task 8.5 — Complete production destination adapters and durability

**Files:** create `copilot-mro/deployment/otel/backend-newrelic.yaml` and its environment example; create or
extend a production durability fragment under `copilot-mro/deployment/otel/`; modify
`copilot-mro/deployment/otel/{README.md,validate.sh,dashboards/CATALOGUE.md}` and the Collector profile tests.
Extend the existing provider probe script or add one focused script under `copilot-mro/deployment/otel/`.
Update `iac` only after its existing deployment deferral is lifted.

- [x] Add a New Relic Collector overlay using deployment-supplied endpoint and secret values. Application code
      and application images must remain unchanged.
- [x] Add bounded retry, memory queue and file-backed queue support for production profiles. Document disk
      sizing, permissions, overflow behavior and the fact that a Collector queue is not permanent storage.
- [ ] Validate OSS, AWS, Azure and New Relic overlays in CI with secrets absent. Validation must prove the
      three operational signals route correctly and the optional content lane is not enabled accidentally.
- [ ] For each production provider, send a uniquely identified trace, metric and log from the same unchanged
      canary producer; retrieve all three from the destination and record the provider query/link evidence.
- [ ] Reverify Azure Monitor's direct Collector ingestion support against current official documentation at
      execution time. If the required path is still preview or lacks an acceptable support commitment, mark
      Azure production support `NO-GO` and document the supported bridge rather than claiming parity.
- [x] Update the shared dashboard catalogue with provider translations and explicit unsupported panels. Exact
      PostgreSQL product panels remain separate from telemetry-store translations.
- [x] Verify a destination change changes only Collector/deployment configuration, secrets and provider
      dashboards—not application business code or the Flynapse UI bundle.

**Acceptance:** New Relic has the same configuration-validation coverage as existing profiles; every provider
claimed production-ready has retrieved log/metric/trace canary evidence; production queues survive a Collector
restart; unsupported provider features are explicit.

**Implementation note — 2026-09-17:** configuration artifacts were reconciled in `copilot-mro` branch
`obs-telemetry-merge`: `backend-newrelic.yaml`, `env/newrelic.env.example`, `durability-production.yaml`,
profile env documentation, `validate.sh` production-durability composition, and the dashboard catalogue status
note now exist. Non-container tests prove the checked-in profile shape, env documentation, all five operational
pipelines, processor ordering, New Relic OTLP/HTTP + `api-key` header wiring, bounded retry/queue settings and
the absence of an implied Phoenix content lane. The pinned Collector validation path still runs through Docker,
so it was not executed in this task. CI/pinned-Collector validation, owner-run provider trace/metric/log
retrieval, Azure production support re-check, provider field-path evidence and production-mounted queue restart
survival remain open. Configuration evidence must not be treated as live provider evidence.

### Task 8.6 — Cross-phase acceptance and closeout

- [ ] Run a two-tenant product-event replay: one logical event per tenant, duplicate retries, correct accepted
      and duplicate counts, and no cross-tenant reads.
- [ ] Run a two-tenant dashboard-profile matrix across tenant owner, restricted administrator and capability
      holder. Confirm the Flynapse UI is the only ordinary client-facing dashboard surface.
- [ ] Run Agent SDK and LangGraph turns covering success, model error, tool error and unpriced usage; reconcile
      PostgreSQL records with traces and metrics without requiring one-to-one telemetry durability.
- [ ] Run the single-host Docker POC within an agreed resource budget, first without Phoenix and then with its
      optional profile.
- [ ] Run the destination-swap test with identical application images and compare required resource attributes,
      metric units, trace propagation and redaction at every supported destination.
- [ ] Check metric cardinality: `tenant.id` appears only on the explicitly approved tenant-scoped instruments;
      user, session, chat, document and request IDs do not appear as metric labels.
- [ ] Refresh the dashboard catalogue's live/dark status markers from the final canaries; remove stale phase
      labels without claiming any signal that was not retrieved.
- [ ] Update the master checkboxes, provider support matrix, implementation notes, residual risks and owner-run
      deployment steps. Keep unexecuted live checks visibly pending.

**Phase acceptance:** both application contracts are reliable and tenant-safe; the Flynapse UI view set is
configurable per client; operational backends can be selected through Collector profiles; Phoenix is optional;
every production-support claim is backed by a retrieved canary; no Kubernetes or `otel-lgtm` implementation has
entered scope.

## 5. Explicitly deferred

- Replacing the current POC services with the `otel-lgtm` container.
- Multi-host Collector topology and orchestration changes.
- Kubernetes manifests, operators or Helm charts.
- Browser IndexedDB persistence for product events.
- A universal application outbox. Reconsider it only for product events that become contractual, billing or
  audit records and therefore require transaction-coupled delivery.
- Vendor-specific application SDKs. A later exception requires a demonstrated feature gap, a shared adapter
  boundary and owner approval.

## 6. Review checklist

- [x] Current versus planned wording is accurate after Task 8.0.
- [ ] No task merges the operational and product-event contracts.
- [ ] No frontend profile exposes vendor configuration or weakens backend authorization.
- [ ] No provider is called production-supported from static configuration alone.
- [ ] No metric gains an unbounded identifier.
- [ ] No product total treats sampled or expired telemetry as authoritative.
- [ ] No duplicate writer or projection is introduced for `chat_turn_facts`.
- [ ] Docker-only and single-host constraints remain explicit.
- [ ] `otel-lgtm` remains deferred.

## 7. Implementation notes / learnings

_(Append dated evidence, deviations, test results and owner rulings as the phase is executed.)_

- **2026-09-08 — Task 8.0 complete (documentation-only).** The current six-repository baseline is recorded in
  `docs/plans/observability-rebuild-research/08-post-migration-rescoping.md`. Both runtimes exist behind the
  deployment selector, but Gate M is **not declared**: migration Batch 5, its post-Batch-5 parity slice and the
  owner's stability declaration remain. Product-event reliability, per-client Flynapse UI profiles, optional
  Phoenix packaging and configuration-only provider work may proceed. The audit also corrected one wording
  error: Collector-side content suppression exists, while application-side configurable capture remains
  planned under Phase 3.5/3.6. No application code or runtime state changed.
- **2026-09-08 — Task 8.1 complete in isolated worktrees.** Dashboard now assigns a UUID and schema version 1
  when a validated event enters its in-memory queue and reuses that envelope for retries. Core accepts both
  the legacy shape and the versioned shape, supplies compatibility values for omitted fields, and performs one
  tenant-scoped batch insert with conflict-ignore and returned accepted keys. The endpoint reports `accepted`
  and `duplicates` separately and emits operational product-event logs only for accepted rows. PostgreSQL adds
  `schema_version` through the existing registry migration path; no migration-runner change, IndexedDB, outbox
  or Collector route was added.
- **Task 8.1 rollout order and compatibility gate.** Apply the Core registry migration first, deploy Core
  second, and deploy the Flynapse UI third. Core must keep generating missing event IDs and version 1 for old
  clients until deployment evidence shows the supported Flynapse UI population always sends both fields.
  Removing those defaults is a separate owner-approved breaking-contract change; browser-generated IDs remain
  non-durable across reloads by this task's explicit scope.
- **Task 8.1 verification.** Dashboard: 69 telemetry unit tests and TypeScript typecheck passed. Core: 27
  focused schema/table tests, 14 scratch-Postgres API/store tests under a non-bypass RLS role, and 189 broader
  analytics/error-contract tests passed. The standard registry migration also upgraded a disposable database
  created from the pre-8.1 schema, adding the version column, default, `NOT NULL` and named check constraint
  without a migration-runner edit. All scratch databases and temporary test roles were removed. The broad
  Core run excluded only `test_chat_turn_facts_drift_pin.py`, which cannot locate its required sibling
  `copilot-mro` repository from the isolated worktree. Dashboard's repository-wide changed-file lint remains
  blocked by two pre-existing `prefer-const` findings in `hooks/pdf-viewer/use-pdf-search.ts`; the modified
  files typecheck and their tests pass.
