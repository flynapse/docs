# Observability Rebuild — Current-Branch Rescoping Baseline

**Status:** Task 8.0 complete as a static, pre-Gate-M audit on 2026-09-08. No application code was changed.
This is the current-state baseline for Phase 8; it is not the final Task R inventory. Task R must refresh this
file after the owner declares Gate M. The 2026-09-17 Task 4 reassessment below supersedes only the dated
Gate M and turn-facts blockers; it still does not count as R.1 completion.

## 1. Audit basis

The six in-scope workspace repositories were clean when inspected.

| Repository | Branch | HEAD |
|---|---|---|
| `api` | `langgraph-merge` | `a19a931` |
| `core` | `master` | `988571b` |
| `copilot-mro` | `langgraph-merge` | `ac680bf2` |
| `dashboard` | `agent_sdk` | `b87ced0` |
| `utils` | `langgraph-merge` | `9f74a11` |
| `iac` | `main` | `5996e5a` |

Evidence labels used below:

- **Observed:** present in the checked-out files above.
- **Historical runtime evidence:** recorded by an earlier dated probe; not rerun during this documentation task.
- **Planned:** described by a plan but not found in the current implementation.
- **Unknown:** requires a live environment, provider credentials or an owner decision.

## 2. Outcome

1. The accepted two-contract architecture is already visible: operational telemetry uses OTLP, while approved
   product events use the authenticated Core API and PostgreSQL. Phase 8 must keep that separation.
2. The OpenTelemetry Collector already exists and is the deployment-owned routing boundary. OSS, AWS and Azure
   overlays exist; New Relic and production queue persistence do not.
3. The client dashboard already lives inside the Flynapse settings UI and reads the Core Product Analytics API.
   It has 42 locally registered panels, but it has no server-owned per-client dashboard profile.
4. Both Agent SDK/Claude and LangGraph runtimes now exist behind one deployment selector. The old Batch 5 and
   post-Batch-5 parity blockers have current completion evidence, but this still does not satisfy Gate M because
   no tracked owner declaration says the conflict zone is stable for Stream L.
5. Agent/runtime model-usage telemetry is now wired at the shared pipeline boundary, but Task R has not refreshed
   the runtime inventory or approved a post-merge signal catalogue. The online `chat_turn_facts` writer,
   application-side content capture and the eval-results workbench remain incomplete. Plans and dashboard
   definitions must not be read as proof that those signals are live.

## 3. File-level current state

### 3.1 Operational telemetry and deployment profiles

| Area | Observed now | Remaining work |
|---|---|---|
| Shared server telemetry | `utils/utils/observability/bootstrap.py:1-18,90-145` configures traces, metrics and logs from standard `OTEL_*` values over OTLP/HTTP. `api/flynapse_api/main.py:6-8,274` installs the shared logging/bootstrap and gateway instrumentation. | `copilot-mro/copilot_mro/app/config.py:949-956` still exposes legacy `OTEL_ENDPOINT`/`OTEL_ENABLED`; `app/main.py:239` still serves `/metrics`; and `app/api/chat_management.py:988-990,1304-1306` still logs raw request text. The 2026-09-08 planning review split this work: Phase 1c may now handle the stable MRO lifecycle, direct-scrape route and non-agent dependency/job spans; legacy config and chat/runtime work remain owner-coordinated or gated for Phase 1b/3. |
| Browser telemetry | `dashboard/lib/telemetry/exporter.ts:1-23,89-121` serializes OTLP traces/logs and sends them through Flynapse API ingest routes; the browser never receives a Collector URL. `core/core/resources/logging/logging_endpoints.py:158-181,214-271,309-330` validates and forwards the opaque payload with server-stamped identity. | Browser metrics are intentionally represented as bounded log events such as Web Vitals. Current live delivery was not rerun in this audit; the 2026-09-05 probe remains historical evidence. |
| Collector boundary | `copilot-mro/deployment/otel/base.yaml` owns the OTLP receivers, identity, content, cardinality, redaction/filtering, batching and the shared `file_storage/production_queue` extension with directory creation enabled for fresh local defaults. Backend overlays own complete pipelines. | 2026-09-17 update: profile-specific `durability-production-{oss,aws,azure,newrelic}.yaml` fragments add bounded retry/queue settings without replacing pipeline processor lists or adding incomplete exporters from other backends. This is configuration evidence only; pinned Docker validation, live provider retrieval and queue restart survival remain pending. |
| Destination overlays | `backend-oss.yaml` routes to Tempo, Prometheus and Loki. `backend-aws.yaml` routes traces, metrics and logs to X-Ray/CloudWatch using workload identity. `backend-azure.yaml` is authored but not deployed. `backend-newrelic.yaml` now routes all five operational pipelines to New Relic OTLP/HTTP using deployment-supplied endpoint and license-key header. | AWS/Azure/New Relic are not production-supported until retrieved canaries pass. Azure also needs the Phase 8.5 supportability decision refreshed at execution time. |
| Tenant metric dimensions | `utils/utils/observability/registry.py:26-41,77-87` forbids user/session/raw-path keys but not tenant identity. `utils/utils/observability/metrics.py:76-101` accepts `tenant_id`. `base.yaml:75-115` removes unbounded keys and deliberately promotes `tenant.id` for Claude Code metrics. | The implementation is permissive rather than governed by an explicit list of tenant-scoped instruments. Task R/8.3 must catalogue the approved instruments and prove a cardinality bound; user/session/chat/document/request dimensions stay forbidden. |
| Current Docker POC | The standalone observability compose starts separate Collector, Prometheus, Loki, Tempo and Grafana services with the OSS overlay. The root and POC compose files use the same separate services. No `otel-lgtm` service exists. | `deployment/docker-compose.yml:85-122` and `deployment/poc/docker-compose.yml:43-78` currently make Phoenix and its Collector fragment mandatory. Task 8.4 makes only that addition optional; it does not replace the native services. |
| Cloud deployment artifacts | `iac/otel_gateway.tf`, `iac/cloudwatch.tf`, `iac/cloudwatch_dashboards.tf` and `iac/modules/otel-gateway/` contain AWS Collector/IAM/dashboard deployment assets, including an optional Phoenix sidecar. | These artifacts are not current deployment proof. The owner-deferred apply/live-provider work remains deferred; Phase 8 must not expand the multi-host topology. Azure has no IaC here. |

### 3.2 Product records and dashboards

| Area | Observed now | Remaining work |
|---|---|---|
| Product-event wire | `dashboard/lib/telemetry/product-events.ts:1-14,24-105,195-240` validates, queues and retries six approved event types to `POST /analytics/events`. `core/core/resources/analytics/schemas.py:68-84,133-144` enforces the server-owned identity boundary. | The wire has no stable producer-created `event_id` or `schema_version`; the response reports only `accepted`. A retry can be counted twice. Task 8.1 owns the additive compatibility change. |
| Product-event storage | `core/core/resources/analytics/events_store.py:47-108` stamps tenant/user/session and performs a plain insert. `core/core/db/table_definitions.py:1369-1457` defines a tenant-scoped table whose effective primary key ends in `event_id`. | The database generates a new event ID for every attempt, and the insert has no conflict handling. Task 8.1 can use the existing `(tenant_id, event_id)` key for deduplication and must log only newly accepted rows. |
| Product Analytics API | `core/core/resources/analytics/analytics_endpoints.py:44-168` serves one authorized PostgreSQL-backed panel at `GET /analytics/chat-quality`; `core/core/resources/analytics/registry.py:46-56,71-156` owns six tabs and panel authorization. | This API already exists in **Core**, not Copilot MRO. Phase 8 extends it with a profile endpoint; it does not create or move a new analytics service. |
| Flynapse client dashboard | `dashboard/app/(dashboard)/settings/department/dashboard/page.tsx:303-343` is the native Flynapse settings page. `dashboard/lib/api/analytics-api.ts:193-210` fetches panel data from Core. The frontend registry contains 42 panel IDs. | Panel/tab selection is compiled into the frontend registry and local permission logic. No `dashboard_profile`, `effective_panels` or profile-version contract exists. Task 8.2 makes selection server-owned per client while keeping per-panel authorization. |
| Backend/operator dashboard | Six provisioned Grafana dashboards exist under `deployment/observability-local/grafana/provisioning/dashboards/flynapse/`. The datasources file configures Prometheus, Loki, Tempo and restricted `flynapse_readonly` PostgreSQL. | Several LLM/agent panels are definitions only because their producers are not wired. The catalogue's old “DARK until Stream F” labels are stale for merged browser code and historical 2026-09-05 probes; current runtime health still requires a fresh canary. Grafana remains the POC/operator tool, not a client destination. |

### 3.3 LLM/agent observability and durable turn facts

| Area | Observed now | Remaining work |
|---|---|---|
| Runtime selection | `copilot-mro/copilot_mro/app/services/agent_pipeline.py:1-16,454-466` composes either `claude` or `lang` once per deployment. `config.py:1061-1069` exposes `AGENT_RUNTIME` and the LangGraph provider profile. | The LangGraph composition is still described as development/evaluation. Runtime availability is not the same as migration completion or production parity. |
| Gate M | `copilot-mro/docs/plans/s4-capability-batches.md:68,193-195` records the conversion program through Phase 5 with tools 56/56, skills 18/18 and an empty manifest. `copilot-mro/docs/plans/runtime-divergence-register.md:222` records the post-Batch-5 lang fuse/judge slice as closed and merged. | **Gate M is still not declared.** The old Batch 5 and parity-slice blockers are stale, but the governing master plan requires an owner declaration that no further batch is expected to touch the conflict zone during Stream L. No such declaration was found in the tracked docs. Owner: runtime migration owner. Next decision point: record Gate M explicitly, or record that the gate remains intentionally closed. |
| Runtime telemetry | `agent_pipeline.py:33-44` builds a backend-neutral `RuntimeTelemetry` facade; `agent_pipeline.py:174-178` adds it to the Claude lifecycle usage sinks, and `agent_pipeline.py:433-436` adds it to the LangGraph model usage sinks. | This is wiring evidence, not Task R approval. R.1 still must refresh the runtime call-site inventory, and R.2 still must approve the exact span/metric catalogue and cardinality bounds before Phase 3 production wiring or dashboard-lighting claims. Owner: observability workstream owner. |
| Durable turn facts | `postgres_table_definitions_modules/chat_turn_facts.py:15-24,43-78,107-148` defines the tenant-scoped projection and states "No writer yet". `core/scripts/backfill_chat_turn_facts.py:1-19,287-318` is the idempotent current writer. Runtime selection converges before route persistence: `chat_management.py:463-476` routes use the composed `get_agent_pipeline()`, and `agent_pipeline.py:1-17,524-533` selects Claude or LangGraph once per process. The served `/rag` path executes the pipeline then synchronously calls `chat_db.save_block` before returning (`chat_management.py:1119-1123,1199-1239,1254`). The `/rag/stream` path executes the same pipeline seam, queues `final`, then creates a timeout-bounded background save task (`chat_management.py:1441-1444,1583-1650`). `chat_history/blocks.py:24-32,589-631` inserts `chat_blocks` and updates chat rollups without inserting a facts row. | The online same-transaction writer is absent. Phase 3.7 remains its sole implementation owner after Gate M + Task R; Phase 8 must not add a second projection path. A future sole writer inside `save_block` can cover both database transactions because both served paths persist through that helper, but streaming clients can receive `final` before background persistence succeeds or fails. Owner: Phase 3.7 writer implementation owner. |
| Content capture and Phoenix | `base.yaml:63-73,191-204` strips content from ordinary telemetry and reserves marked copies. `content-phoenix.yaml:1-41` defines the optional content-only routing fragment and tenant project mapping. | No production app path currently emits the `flynapse.content_copy` marker or writes the planned `llm_turn_content` record. Therefore “off by default” is enforced, but config-enabled capture is still planned under Phase 3.5/3.6. |
| Eval workbench | A pinned Phoenix service/fragment and smoke infrastructure exist. | No `eval_results` table or completed harness/report flow was found. Phase 7.2-7.6 remain planned; Task 8.4 only makes Phoenix packaging optional. |

## 4. Phase 8 starting conditions

| Task | Starting condition after this audit | Gate |
|---|---|---|
| 8.1 Product-event reliability | Existing end-to-end event route and tenant key confirmed; identity/version/deduplication absent. | May start. |
| 8.2 Per-client Flynapse UI profile | Core panel authorization and 42-panel Flynapse UI registry confirmed; server profile absent. | May start. |
| 8.3 Runtime/facts completion | Two runtime adapters exist; model-usage telemetry is now wired through the pipeline boundary, but the online facts writer is absent and Task R has not refreshed the runtime inventory/catalogue. | Blocked on explicit Gate M declaration + Task R. |
| 8.4 Optional Phoenix | Standalone observability compose is Phoenix-free; root and POC compose files hard-wire Phoenix. | May start. |
| 8.5 Destination readiness | OSS/AWS/Azure/New Relic overlays and profile-specific production durability fragments exist as checked-in configuration. Non-container profile tests pass on 2026-09-17. | Pinned Docker validation, live provider canary retrieval, Azure supportability refresh, provider field-path evidence and production queue restart proof remain pending; live claims require credentials and owner go-ahead. |
| 8.6 Acceptance | Earlier local browser/OSS evidence is historical, not a substitute for the final matrix. | Last, after 8.1-8.5, Phase 1c and all required Stream L work: gated Phase 0 chat cleanup, Phase 1b runtime handoff and Phase 3. |

## 5. Status reconciliation

The original phase checkboxes in the master plan are retained as task definitions and historical sequencing;
they are not a reliable current-status ledger. The dated ledger in master §15 and this table are authoritative.

| Phase | Current status on this baseline |
|---|---|
| 0 | **Partial:** infrastructure hygiene landed; stable MRO memory/Weaviate and direct-scrape cleanup is assigned to Phase 1c, while chat-path cleanup remains gated. |
| 1 | **Partial:** shared utils/API foundation landed; the current-code review assigned stable non-agent roots/clients to pre-gate Phase 1c, while runtime handoff and Phase 3 remain post-Gate-M work. |
| 2 | **Implemented as artifacts; production unproven:** OSS/AWS/Azure/New Relic configs and AWS IaC exist, but pinned Collector validation, provider deployment/live retrieval and restart-survival proof are deferred. |
| 3 | **Planned/partial substrate:** model-usage telemetry emitters are wired at the shared runtime pipeline boundary, but Task R catalogue approval/live proof, content capture and the online facts writer remain pending. |
| 4 | **Implemented; historical runtime proof:** frontend OTLP/product-event cut-over is in the current code and was probed on 2026-09-05. |
| 5 | **Implemented except deferred writer/profile:** Core PostgreSQL analytics and the Flynapse UI are present; online facts and per-client profile remain. |
| 6 | **Implemented as dashboards/rules:** six Grafana dashboards exist; LLM/agent views remain dark until Phase 3 and some catalogue labels need refresh. |
| 7 | **Partial infrastructure only:** Phoenix packaging exists; mapping, eval persistence, harness and report flow remain. |
| 8 | **8.0 complete:** 8.1, 8.2, 8.4 and configuration-only 8.5 may proceed; 8.3 remains gated. |

## 6. Task R boundary

This document answers Task 8.0's question—whether Gate M can be declared—with **no**. It must not be treated as
R.1 completion. After the owner declares Gate M, R.1 must update the branch/HEAD baseline and re-enumerate all
runtime call sites; R.2 must then approve the exact span/metric catalogue before any Phase 3 production wiring.

## 7. Task 4 reassessment - 2026-09-17

Task 4 rechecked the merged `obs-telemetry-merge` state without changing runtime code. Current evidence retires
the old "Batch 5 not started" and "post-Batch-5 parity slice pending" blockers, but it does not open Gate M:

| Requirement | Current evidence | Status / owner |
|---|---|---|
| Gate M owner declaration | Conversion status is current in `s4-capability-batches.md`; R-PAR-2 is closed in `runtime-divergence-register.md`. No tracked owner declaration says the conflict zone is stable for Stream L. | **Closed** until the runtime migration owner records Gate M explicitly. |
| Task R.1 / R.2 | This file is still a Task 8.0 baseline. No post-Gate-M inventory or approved signal catalogue has been written here. Runtime/model telemetry emitters are wired, but catalogue approval and live proof remain pending. | **Pending**, owner: observability workstream owner. |
| Served persistence boundaries | `chat_management.py:463-476` routes consume the deployment-selected `get_agent_pipeline()` before persistence. Non-streaming `/rag` executes the pipeline and saves the block synchronously before returning (`chat_management.py:1119-1123,1199-1239,1254`). `/rag/stream` executes through the same runtime seam, queues the `final` event, then starts a timeout-bounded background `save_block` whose timeout/error handling logs or records failure without changing that already-queued client response (`chat_management.py:1441-1444,1583-1650`). | **Assessed.** A future sole same-transaction writer inside `save_block` can cover both database transactions, while preserving the current streaming ordering where final delivery precedes persistence. |
| Phase 3.7 online writer | `chat_turn_facts` DDL and Core backfill exist, but `chat_history/blocks.py` has no same-transaction facts upsert. | **Pending**, owner: Phase 3.7 writer implementation owner. |
| Backfill/version/idempotency contract | Unit projection and drift-pin tests pass with `FACTS_VERSION = 1`. The controller retried the database lane directly and the target `copilot_mro_test` database did not exist; the isolated Core database lane provisioned a scratch database, but the fixture's grant service failed with `permission denied for table tenants`. No idempotency database result exists from this run, and this is a scratch-lane/test-harness privilege blocker rather than evidence of a backfill logic failure. | **Static contract verified; DB proof owner/CI-run.** |

Next decision point: the runtime migration owner either records Gate M and dispatches Task R before any writer
implementation, or keeps Gate M closed with the same accountable roles named above. No duplicate writer is
authorized by this reassessment.
