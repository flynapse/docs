# Observability Rebuild — Phase 1c: Stable Non-Agent Telemetry

> Execution companion to `docs/plans/observability-rebuild.md`, Phase 1c. Implement on the
> per-repository `obs-non-agent` branches. Write the focused test first for every task and pause if
> an approved production path has changed or enters the agent/runtime migration conflict zone.

**Goal.** Add useful operation-level telemetry at stable application boundaries that can be completed before
the LangGraph migration, without editing agents, tools, skills, prompts, provider calls or deployment topology.

**Owner approval.** The owner approved continuing this pre-migration work on `obs-non-agent` on 2026-09-08.

## 1. Frozen scope and branch baseline

The four repositories use the same branch label but remain independent Git histories:

| Repository | Branch | Starting point for this phase | Current role |
|---|---|---|---|
| `copilot-mro` | `obs-non-agent` | `ac680bf2` from `langgraph-merge` | MRO lifecycle and stable job boundaries |
| `utils` | `obs-non-agent` | `9f74a11` from `langgraph-merge` | Shared S3 and Weaviate client spans |
| `core` | `obs-non-agent` | Phase 8.1 commit `03e15db` | Product-event ingestion; no Phase 1c production edit |
| `dashboard` | `obs-non-agent` | Phase 8.1 commit `9233b99` | Flynapse UI product events; no Phase 1c production edit |

The approved production-path manifest is exactly:

- `copilot-mro/copilot_mro/app/main.py`
- `copilot-mro/copilot_mro/app/services/memory/memory_index.py`
- `copilot-mro/copilot_mro/app/services/memory/memory_db.py`
- `copilot-mro/copilot_mro/app/services/document_hub/processing.py`
- `copilot-mro/copilot_mro/app/services/document_hub/cleanup.py`
- `copilot-mro/copilot_mro/app/services/document_hub/operations.py`
- `copilot-mro/copilot_mro/app/services/data_discovery/runner.py`
- `copilot-mro/copilot_mro/app/services/data_discovery/cli.py`
- `copilot-mro/copilot_mro/app/services/improvement/scheduler.py`
- `copilot-mro/copilot_mro/app/services/improvement/runner.py`
- `copilot-mro/copilot_mro/app/services/parsers/amos_parser.py`
- `copilot-mro/copilot_mro/app/services/parsers/amos_metadata_backfill.py`
- `copilot-mro/copilot_mro/app/services/parsers/ftd_parser.py`
- `copilot-mro/copilot_mro/app/services/parsers/ifim_parser.py`
- `copilot-mro/copilot_mro/app/services/parsers/tn_parser.py`
- `copilot-mro/copilot_mro/app/services/parsers/crew_manual_parser.py`
- `copilot-mro/copilot_mro/app/services/parsers/mel_parser.py`
- `copilot-mro/copilot_mro/app/services/s3_pdf_processor.py`
- `utils/utils/s3_service.py`
- `utils/utils/weaviate_service.py`

An automated diff guard must fail if Phase 1c changes another production path. Tests and this plan are exempt
from that guard. No `config.py`, dependency/lock file, Docker/Collector file, database schema or product-event
contract belongs to this phase.

## 2. Signal contract

All names and attributes below are application-owned OTLP trace data. They use the existing Utils bootstrap and
SDK only. No new metric is introduced. A span inherits the current trace when one exists and becomes a root only
for a standalone process.

| Boundary | Span name and kind | Allowed attributes | Outcomes | Primary consumer |
|---|---|---|---|---|
| S3 PDF download | `s3.download`, `CLIENT` | `rpc.system=aws-api`, `rpc.service=S3`, `rpc.method=DownloadFile`, `operation.outcome`; downloaded byte count only on success | `success`, `not_found`, `unavailable`, `error` | `fn-dependencies` latency/error and trace drill-down |
| Weaviate hybrid search | `weaviate.hybrid_search`, `CLIENT` | `db.system=weaviate`, `db.operation=hybrid_search`, `tenant.id`, `search.mode`, requested/result counts, `operation.outcome` | `success`, `error` | `fn-dependencies` latency/error and trace drill-down |
| MRO startup/shutdown | `mro.lifecycle.startup` and `mro.lifecycle.shutdown`, `INTERNAL` | phase, bounded dependency/check name, `operation.outcome` | `success`, `degraded`, `error` | `fn-platform-health` and correlated startup logs |
| Memory collection/index | `memory.collection.ensure`, `memory.index.upsert`, `memory.index.delete`, `INTERNAL` | `tenant.id`, bounded memory type/scope/action, `operation.outcome` | `success`, `skipped`, `error` | background-operation trace drill-down |
| Memory search/reindex | `memory.search`, `memory.reindex`, `INTERNAL` | `tenant.id`, bounded search type/scope, requested/result/batch counts, `operation.outcome` | `success`, `skipped`, `error` | background-operation trace drill-down |
| Memory get-by-id batch | `memory.items.get_by_ids`, `INTERNAL` | `tenant.id`, requested/result counts, `operation.outcome` | `success`, `error` | trace drill-down; replaces `item_count` metric label |
| Document Hub attempt | `document_hub.process`, `INTERNAL` | `tenant.id`, bounded document kind/parser kind/result status, attempt number, `operation.outcome` | `success`, `stale`, `needs_attention`, `error` | `fn-platform-health` background jobs |
| Document Hub cleanup | `document_hub.cleanup`, `INTERNAL` | aggregate scanned/reconciled/deleted/error counts, `operation.outcome` | `success`, `partial`, `error` | `fn-platform-health` background jobs |
| Data Discovery job | `data_discovery.job.run`, `INTERNAL` | `tenant.id`, `job.id`, bounded level/status, attempt number, `operation.outcome` | `completed`, `failed`, `exhausted`, `already_terminal`, `not_visible` | `fn-platform-health` background jobs |
| Improvement run/stage | `improvement.run` and child `improvement.stage`, `INTERNAL` | `tenant.id`, run/stage bounded status/name, aggregate counts, `operation.outcome` | `success`, `refused`, `partial`, `error` | `fn-platform-health` background jobs |
| Parser command | `ingest.parse`, `INTERNAL` | `parser.kind`, `operation.outcome`; aggregate processed/failed counts when returned | `success`, `partial`, `error` | `fn-platform-health` ingest jobs |

Never attach prompt, response, query, retrieved text, document text, S3 bucket/key, local path, collection/object
identity, event/result body or credentials. Do not add user, session, chat, document or request identifiers. Tenant
identity is permitted on spans/logs, not added as a metric label by this phase. Exception type may be recorded;
exception text is kept out unless the existing content-free logging policy already permits it.

Returned failures must set `operation.outcome` and ERROR status explicitly. Raised exceptions are recorded and
re-raised unchanged. Successful spans set an explicit success outcome. Disabled OTel remains a behaviorally
transparent no-op.

## 3. Test-first execution tasks

The following new basenames were checked for collisions before implementation and are reserved for this phase.

### Task 1c.0 — scope and drift gate

- [x] Freeze the production manifest and signal table in this document.
- [x] Confirm no approved target changed after the 2026-09-08 audit baseline.
- [x] Add `tests/unit/observability/test_phase1c_nonagent_scope_guard.py` in Copilot MRO. It rejects production
  paths outside the manifest and imports from the agent/tool/skill conflict zone in the Phase 1c diff.
- [x] Record the guard inputs: MRO `ac680bf2..HEAD`; Utils `9f74a11..HEAD`. The Utils repository is supplied
  through `PHASE1C_UTILS_REPOSITORY` in non-sibling CI layouts.

### Task 1c.1 — shared storage clients (`utils`)

- [x] Add failing `utils/tests/unit/observability/test_nonagent_storage_client_spans.py` coverage for S3 download
  success, returned failure, client exception, parent propagation, content exclusion and disabled-SDK behavior.
- [x] Add the same focused coverage for Weaviate hybrid-search success and raised failure.
- [x] Instrument only `download_pdf` and `hybrid_search`. Remove raw S3 key/local-path and raw Weaviate query
  values from logs touched by the task. Preserve each current return/raise contract.
- [x] Run the new test and the existing Utils observability suite.

### Task 1c.2 — MRO lifecycle

- [x] Add failing `tests/unit/observability/test_nonagent_lifecycle_spans.py` coverage for hard-check success,
  hard-check failure, optional installer/timer degradation, shutdown success/failure and `/metrics` absence.
- [x] Add startup/shutdown spans and structured, content-free outcomes in `app/main.py`; remove only the MRO
  direct Prometheus `/metrics` route. Do not change bootstrap/import order or health behavior.
- [x] Run the new test plus `tests/api/startup/test_mro_docs_exposure.py`.

### Task 1c.3 — memory operations

- [x] Add failing `tests/unit/memory/test_memory_operation_telemetry.py` around the six approved public
  boundaries. Cover success, skip/empty, raised failure, parent propagation and attribute allow-list.
- [x] Remove the raw query from `search_memory` logs.
- [x] Remove `item_count` from metric attributes in `get_memory_items_by_ids`; retain requested/result counts on
  the operation span and structured log. Do not add spans to other DAO methods already represented by SQL spans.
- [x] Run the new test and the existing focused memory index/DB unit tests.

### Task 1c.4 — Document Hub operations

- [x] Add failing `tests/unit/document_hub/test_document_hub_operation_telemetry.py` for processing outcomes,
  cleanup success/partial failure, parent propagation and content exclusion.
- [x] Add only the attempt and sweep spans; keep current counters/histograms unchanged.
- [x] Prove the six `DOCUMENT_HUB_QNA_*` constants have no call sites before removing them from `operations.py`.
- [x] Run the new test plus the existing processing-attempt and cleanup unit tests.

### Task 1c.5 — Data Discovery

- [x] Add failing `tests/unit/data_discovery/test_data_discovery_operation_telemetry.py` for completed, failed,
  exhausted, already-terminal and invisible-job results, with a fake executor only.
- [x] Add one `run_job` span and bounded log context. Bootstrap the standalone CLI as `data-discovery-job`.
- [x] Prove the test neither imports nor edits `data_discovery/agent/**`.
- [x] Run the new test plus the existing job-seam, enqueue and safety unit tests.

### Task 1c.6 — Improvement lifecycle

- [x] Add failing `tests/unit/improvement/test_improvement_operation_telemetry.py` with injected stages and no
  real model calls. Cover refused, complete, partial and stage-error outcomes.
- [x] Add one run span and one child per stage. Preserve sequential execution, rollback and timer policy.
- [x] Run the new test plus the existing runner and scheduler unit tests.

### Task 1c.7 — parser command resources

- [x] Add failing `tests/parsers/base/test_parser_entrypoint_telemetry.py` that invokes command wrappers with all
  storage/OCR/parser work stubbed.
- [x] Standardize the eight approved commands on `setup_logging(name="ingest-parser", ...)`, which invokes the
  shared bootstrap; open one `ingest.parse` root when standalone and set the bounded `parser.kind` attribute.
- [x] Confirm no parser internal, OCR, prompt, LLM path or `amos_post_processing.py` was edited.
- [x] Run the new test plus parser-interface and affected command tests.

### Task 1c.8 — acceptance

- [x] Run all new Phase 1c tests and the focused existing suites named above.
- [x] Run the allowed-path, forbidden-import, raw-content and forbidden-metric-label scans.
- [x] With in-memory exporters, prove parent continuity through a representative injected job process to
  S3/Weaviate operations. This proves context propagation across the real wrappers; it does not claim that the
  current non-agent Data Discovery implementation directly calls both clients.
- [x] With `OTEL_SDK_DISABLED=true`, prove the same functions retain their results and exceptions.
- [x] Send one trace for each operation family to the local Collector and record the observed trace IDs here.
  With owner approval, `otel-collector` and `tempo` were recreated only for the existing `deployment` compose
  project from the `obs-non-agent` worktree. The Collector accepted each OTLP/HTTP JSON canary and Tempo returned
  every operation name by trace ID.
- [x] Record commands/results below and update the master plan only after every acceptance item passes.

## 4. Deferred boundaries

This phase does not claim coverage for agents, model calls, tools, skills, prompt/retrieval content, the Lambda
parser runtime, cloud-vendor delivery or multi-host operation. `agent_shared/**`, `agent_claude/**`,
`lang_agent/**`, `agent_pipeline.py`, `chat_management.py`, `data_discovery/agent/**`, `utils/utils/llm.py`,
`amos_post_processing.py` and parser internals remain behind the LangGraph migration gate.

## 5. Verification record

| Check | Result |
|---|---|
| Target history recheck at phase start | PASS — no approved path changed after the recorded audit baseline |
| Phase 8.1 Core unit contract | PASS — 27 focused tests |
| Phase 8.1 Core isolated DB/API contract | PASS — 14 tests against a disposable PostgreSQL 16 database; scratch database and container removed |
| Phase 8.1 dashboard typecheck | PASS |
| Phase 8.1 dashboard unit contract | PASS — 13 focused tests |
| Phase 1c storage-client contract | PASS — 6 focused tests; initial run failed all 6 before implementation |
| Utils observability regression | PASS — entire `tests/unit/observability` suite; loopback tests rerun with sandbox permission |
| Utils Weaviate tenancy regression | PASS — entire focused file |
| Utils lazy-export regression | PASS — entire focused file |
| Phase 1c MRO lifecycle and docs-route contract | PASS — 10 tests; initial lifecycle run failed all 5 before implementation |
| MRO lifecycle adjacency regressions | PASS — 47 Document Hub/Data Discovery enqueue and improvement-scheduler tests |
| Phase 1c memory operation contract | PASS — 7 focused cases; initial run failed all 6 pre-implementation cases |
| MRO memory unit domain | PASS — 168 tests, including loader/isolation guards and disabled-SDK behavior |
| Phase 1c Document Hub operation contract | PASS — 9 focused cases; initial run failed all 6 pre-implementation span cases |
| MRO Document Hub unit domain | PASS — 498 tests; processing, cleanup and reconciliation semantics unchanged |
| Dead Document Hub Q&A constants | PASS — zero Python references, enforced by the focused contract test |
| Phase 1c Data Discovery operation contract | PASS — 9 focused cases; initial run failed all 6 pre-implementation signal cases |
| MRO Data Discovery unit domain | PASS — 318 tests; no `data_discovery/agent/**` production or test import added |
| Phase 1c Improvement operation contract | PASS — 7 focused cases; initial run failed all 6 pre-implementation signal/log cases |
| MRO Improvement runner/scheduler regression | PASS — 54 existing tests; sequential stages, rollback and timer policy unchanged |
| Wider Improvement unit domain | 442 passed, 3 pre-existing migration-owned source/skill roster failures; no failing test reads a Phase 1c path |
| Phase 1c parser command contract | PASS — 12 focused cases; initial run failed all 12 before implementation |
| MRO parser/ingest regressions | PASS — 112 passed, 6 existing skips; command arguments, operator resolution and parser behavior unchanged |
| Parser production-path scan | PASS — exactly the eight approved entrypoints changed; no parser internals, OCR, prompt, LLM or `amos_post_processing.py` edits |
| Phase 1c scope/drift guard | PASS — 3 tests over MRO `ac680bf2..HEAD` and Utils `9f74a11..HEAD`; allowed paths and conflict-zone imports enforced |
| Combined new Phase 1c contracts | PASS — 52 MRO cases and 6 Utils storage-client cases |
| Raw-content and metric-label safety | PASS — exported-content allow-list tests passed; production diff adds no metric instruments or forbidden labels |
| In-memory cross-repository topology | PASS — trace `8554fce42c30a7a2fd5efd7b26eb0ffa`: `automation.run` → `data_discovery.job.run` → `s3.download` / `weaviate.hybrid_search` |
| Disabled-SDK behavior | PASS — 5 MRO no-op behavior cases and 1 Utils storage case |
| Local Collector receiver | PASS — `deployment-otel-collector-1` recreated from `/private/tmp/flynapse-obs-non-agent/copilot-mro/deployment/docker-compose.yml`, image `otel/opentelemetry-collector-contrib:0.160.0`, command `--config=/etc/otel/base.yaml --config=/etc/otel/backend-oss.yaml --config=/etc/otel/content-phoenix.yaml`; OTLP/HTTP on `127.0.0.1:4318/v1/traces` returned 200 |
| Local Tempo retrieval | PASS — `deployment-tempo-1` recreated from the same compose project, image `grafana/tempo:3.0.3`, command `-config.file=/etc/tempo.yaml -config.expand-env=true`; `/ready` returned 200 and `/api/traces/{trace_id}` returned every Phase 1c canary operation |
| Tempo log noise | NON-BLOCKING — the previous parse-error restart loop is gone; Tempo still logs recurring single-binary backend-worker `no jobs found` messages while ready and queryable, so this is Phase 2 config hygiene rather than a Phase 1c blocker |
| Phase 1c implementation checks | PASS — code, focused regressions, scope, content, cardinality, parentage, no-op behavior and runtime trace-backend retrieval all passed; deferred boundaries above remain unchanged |

### Runtime acceptance commands

- `docker compose --env-file /private/tmp/phase1c-observability.env -p deployment -f /private/tmp/flynapse-obs-non-agent/copilot-mro/deployment/docker-compose.yml config --quiet` -> exit 0; only the obsolete Compose `version` warning.
- `docker compose --env-file /private/tmp/phase1c-observability.env -p deployment -f /private/tmp/flynapse-obs-non-agent/copilot-mro/deployment/docker-compose.yml up -d --no-deps --force-recreate otel-collector tempo` -> exit 0; recreated only `deployment-otel-collector-1` and `deployment-tempo-1`.
- `docker inspect` confirmed the recreated containers now point at the `obs-non-agent` worktree compose file and current commands.
- `curl http://127.0.0.1:3200/ready` -> 200.
- `curl -X POST http://127.0.0.1:4318/v1/traces -d '{}'` -> 200.
- `python3 /private/tmp/phase1c_trace_backend_canary.py` -> exit 0; every observed Tempo trace contained the expected single operation name. The temporary env and canary files were non-secret runtime artifacts and were removed after recording this evidence.

### Collector canary IDs retrieved from Tempo

| Operation | Observed Tempo trace ID |
|---|---|
| `s3.download` | `1d83e8aad5da202c4f567eee39f6f9a0` |
| `weaviate.hybrid_search` | `b91a09485375fb1357431bc811719108` |
| `mro.lifecycle.startup` | `befa71e17f20e48303ecd6933425d1c4` |
| `mro.lifecycle.shutdown` | `3d1e648b13767a26f756a53fea5c912c` |
| `memory.collection.ensure` | `77c4de05a6dd26427615164b79355005` |
| `memory.index.upsert` | `e42552602aa11914169b148adfc0b60f` |
| `memory.index.delete` | `5d423211b36f08b35e7b93d212b71ff3` |
| `memory.search` | `c515aa4bff1704b6901b9be858ca7714` |
| `memory.reindex` | `014cbc19a77aa8be4f4b0d029490e0ae` |
| `memory.items.get_by_ids` | `a2b12eb23051bec96a5584feef9f5ec9` |
| `document_hub.process` | `e993449de15b364c948ad3b8bdb56bc5` |
| `document_hub.cleanup` | `7eab847e3eeba4651e29e92ea10a447e` |
| `data_discovery.job.run` | `681f8d9c5f456ec550ad6e8b4156c888` |
| `improvement.run` | `8776a5e6d46d0c556a08f11765ad4c36` |
| `improvement.stage` | `1fa4e11c3a8a6eabffe7b2eda6dba19b` |
| `ingest.parse` | `fbf6f655b4f215c02d14f7a25d2c54ff` |
