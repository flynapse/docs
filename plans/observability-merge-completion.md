# Observability Merge Completion Plan

**Governing plan:** `docs/plans/observability-rebuild-phase-8-audit-followups.md`

**Goal:** close the implementation gaps found in the `obs-telemetry-merge` audit without changing the accepted observability architecture or interfering with unfinished agent-runtime migration work.

## Global Constraints

- Keep the two application contracts: operational telemetry uses vendor-neutral OTLP; approved product events use the authenticated Product Analytics API and tenant-scoped PostgreSQL.
- Keep the client-facing dashboard inside the Flynapse UI. Grafana and provider consoles remain restricted operator surfaces.
- Keep the current single-host Docker model. Do not add Kubernetes or `otel-lgtm`.
- Keep Phoenix optional and LLM content capture off by default unless explicitly enabled.
- Do not add a second `chat_turn_facts` writer. Phase 3.7 remains the sole owner of the online projection.
- Do not put user, session, chat, document, or request identifiers into metric labels. Tenant labels remain limited to explicitly approved tenant-scoped instruments.
- Destination changes must remain Collector/deployment configuration changes; application business code and the Flynapse UI bundle must not become vendor-specific.
- Do not launch containers or UI processes from Codex during this plan. Live UI, Phoenix, and provider canaries remain owner-run checks.
- Use test-first development for every behavior change. Preserve backward compatibility unless the governing plan explicitly authorizes otherwise.
- Work only on `obs-telemetry-merge` in each affected repository and preserve unrelated user changes.

### Task 1: Stabilize the Existing Merge-Branch Work

**Repositories:** `api`, `copilot-mro`

**Files:** inspect every currently modified or untracked file reported by Git; do not commit `.env.codex-backup-20260916T043907Z` or any credentials.

- [x] Classify the existing API and Copilot MRO changes into coherent units: Weaviate local-startup policy, agent telemetry/Phoenix content wiring, and Phoenix evaluation tooling.
- [x] Verify each unit against the governing plan and existing tests before staging it.
- [x] Run focused tests for the API lifecycle, MRO lifecycle, partition boot check, agent telemetry, model gateway, content capture, Collector profiles, and evaluation tooling where present.
- [x] Commit only coherent, reviewed units with repository-specific commits. Leave unrelated or unsafe files untouched and record them as pending.
- [x] Confirm `core`, `utils`, and `dashboard` remain clean before moving to new feature work.

**Acceptance:** the implementation baseline is understandable and reproducible; no secret or backup file is committed; every committed unit has fresh focused test evidence.

### Task 2: Reconcile Production Collector Profiles With the Plan

**Repositories:** `copilot-mro`, `docs`

**Files:** `copilot-mro/deployment/otel/`, its Collector profile tests and documentation, plus the Phase 8 plan and current-state research notes.

- [x] Add failing profile tests proving New Relic configuration and production durability fragments exist, validate without secrets, route traces/metrics/logs, and do not enable the optional content lane.
- [x] Add the missing New Relic overlay and environment example using deployment-supplied endpoint and secret values.
- [x] Add bounded retry, memory limiting, file-backed queue/storage, and documented disk/overflow behavior for production profiles without changing application images.
- [x] Validate OSS, AWS, Azure, and New Relic profile composition with the repository-native non-container static validation suite.
- [x] Correct Phase 8 implementation notes so configuration-only evidence, live provider canaries, and unsupported provider paths are accurately separated.

**Acceptance:** checked-in files match the plan's configuration claims; static validation passes; live provider retrieval and restart proof remain visibly pending until owner-run credentials and infrastructure are available.

### Task 3: Implement Per-Client Flynapse UI Dashboard Profiles

**Repositories:** `core`, `dashboard`

**Files:** Core analytics profile, endpoint, registry, schema, table definitions, migrations and tests; dashboard analytics API client, panel registry, page, and tests listed by Phase 8 Task 8.2.

- [x] Write Core resolver tests for configured-versus-supported panels, feature gates, role/capability intersection, fail-closed unknown panels, sensitive-panel control, and deterministic ordering.
- [x] Write database tests for tenant isolation and the safe default profile.
- [x] Implement one server-owned, versioned dashboard profile per tenant and an authenticated endpoint that derives tenant identity from trusted request context.
- [x] Preserve authorization on every existing panel endpoint; the profile controls presentation only.
- [x] Write dashboard tests for POC-safe, restricted-client, tenant-owner, and capability-holder views using one frontend build.
- [x] Update the Flynapse UI to render the server-returned effective tabs and panels without exposing destinations, credentials, vendor queries, or external observability links.
- [x] Run focused Core analytics/database/API tests and dashboard unit/type checks.

**Acceptance:** changing a tenant profile changes the next Flynapse UI dashboard response without rebuilding the frontend; unsupported and unauthorized panels fail closed; direct panel APIs remain protected.

### Task 4: Reassess the Turn-Facts Migration Gate

**Repositories:** `copilot-mro`, `core`, `docs`

**Files:** current Agent SDK/LangGraph completion and persistence boundaries, Phase 3.7 projection work, `chat_turn_facts` backfill/tests, and the Phase 8 gate record.

- [x] Re-run the file-level Gate M and Task R assessment against the merged branch, including both runtime persistence paths and the post-merge signal catalogue.
- [x] If any prerequisite remains incomplete, update the plan with exact blocking files/owners and do not alter the runtime or add a writer.
- [ ] If all prerequisites are satisfied, create a separate reviewed implementation task for the sole Phase 3.7 writer before changing production code.
- [x] Verify existing backfill and drift-pin tests still express the same `facts_version` and idempotency requirements.

**Acceptance:** the gate has current evidence and one unambiguous owner. No duplicate writer or speculative runtime edit is introduced.

### Task 5: Align Grafana Dashboards and the Signal Catalogue

**Repository:** `copilot-mro`

**Files:** Grafana Flynapse dashboards under `deployment/observability-local/grafana/provisioning/dashboards/flynapse/`, `deployment/otel/dashboards/CATALOGUE.md`, and dashboard/profile tests.

- [x] Map every agent/LLM panel to the metric, span, or log name emitted by the merged implementation.
- [x] Add failing static dashboard tests for stale dark labels, missing signal names, invalid data-source references, and unsupported-panel wording.
- [x] Update descriptions and queries only where the emitted contract proves the signal exists; keep panels dark when live retrieval remains unproved.
- [x] Preserve the separation between operational telemetry panels and PostgreSQL-backed product panels.
- [x] Run dashboard JSON, Collector profile, and signal-name contract tests.

**Acceptance:** the catalogue and dashboard descriptions no longer contradict the merged emitters, and they do not claim live data that has not been retrieved.

### Task 6: Backend Acceptance and Final Review

**Repositories:** all affected repositories

- [x] Run the focused backend/unit/integration checks accumulated by Tasks 1–5 without starting containers or UI processes.
- [ ] Run two-tenant product-event and dashboard-profile automated tests, metric-cardinality contract tests, and destination-swap static tests.
- [x] Record owner-run checks separately: Flynapse UI rendering, Grafana live population, Phoenix traces, single-host Docker runs, provider canary retrieval, and queue restart proof.
- [x] Update the master and Phase 8 status ledgers using only fresh evidence.
- [ ] Run one whole-change GPT-5.6 Sol Extra High architecture/code review and resolve all Critical and Important findings before completion.

**Acceptance:** all locally executable checks pass with recorded commands and outputs; every unexecuted live check remains clearly pending; the final review finds no unresolved Critical or Important issue.

## Review Notes

Implementation notes, deviations, rulings, test evidence, and final residual risks will be appended here as each task is completed.

- **2026-09-17 — Task 1 complete.** Existing work was split into API and Copilot MRO Weaviate warning-mode commits, a Phoenix content-trace projection commit, and an offline Phoenix evaluation-runner commit. Independent review found and the fix round corrected broad exception swallowing, unbound evaluator result identity, unsafe judge labels, and missing API behavior coverage. Controller verification passed 103 focused startup, partition, lifecycle and evaluation tests. The only remaining scoped working-tree item is the deliberately uncommitted API `.env.codex-backup-20260916T043907Z`; no container, UI or live-provider checks were run.
- **2026-09-17 — Task 2 complete within the no-container boundary.** Added a New Relic OTLP/HTTP profile and backend-specific production durability fragments, enabled safe file-storage directory creation, and added merged-composition tests so one profile cannot inherit incomplete exporters from another. Controller verification passed the full non-container Collector lane: 73 passed and 10 compose/runtime checks skipped. Pinned Collector Docker validation, live provider retrieval, Azure supportability refresh, Prometheus restart durability and production-mounted queue restart proof remain pending owner/CI checks. A transient SDD report is absent from the tracked final tree but remains in an earlier local docs-branch commit; purge it through owner-approved history rewrite or squash integration.
- **2026-09-17 — Task 3 complete within the no-UI boundary.** Added a tenant-RLS `dashboard_profiles` relation, trusted-context `GET /analytics/dashboard-profile`, and deterministic server-side intersection of configured, supported, feature-enabled and authorized panels. The Flynapse UI now renders only the returned profile, fails closed on missing/error/unknown state, and keys profiles, filters and panel caches to the resolved tenant so stale cross-tenant responses cannot render. The profiled page no longer mounts the separate LLM-turn summary card outside the allow-list; its component remains available elsewhere. Independent review required two fix rounds and then approved all findings. Controller verification passed 138 focused Core unit/API checks, the isolated three-test two-tenant database lane, 26 Dashboard profile/page tests, TypeScript checking and touched-file lint. Browser rendering remains an owner-run Task 6 check.
- **2026-09-17 — Task 4 reassessed the turn-facts gate without changing runtime code.** The old Batch 5 and post-Batch-5 parity blockers are stale in current Copilot MRO docs, but Gate M remains closed because the required owner declaration is absent and Task R has not refreshed the merged runtime inventory or approved the signal catalogue. The selected Claude/LangGraph runtimes converge before the route persistence boundaries through the composed `get_agent_pipeline()` seam. The non-streaming `/rag` route saves the built chat block synchronously before returning; `/rag/stream` queues the `final` response and then runs a timeout-bounded background `save_block` whose failure does not change the already-queued client response. The sole Phase 3.7 online writer remains pending: `chat_turn_facts` DDL and Core backfill exist, but `save_block` has no same-transaction facts upsert. A future sole writer inside `save_block` can cover both database transactions, while preserving the current streaming ordering where final delivery precedes persistence. Owners are explicit: runtime migration owner for Gate M, observability workstream owner for Task R inventory/catalogue execution and approval, and Phase 3.7 writer implementation owner for the sole online writer. Verification passed 10 Core projection/drift-pin tests, 1 Copilot MRO index/tenancy test and 24 dashboard/rule dark-signal tests with 1 Docker/promtool-gated skip. The database idempotency lane has no result: the direct retry found no `copilot_mro_test` database, and the isolated Core scratch lane then hit `permission denied for table tenants` in the fixture grant service. This is a scratch-lane/test-harness privilege blocker, not evidence of a backfill logic failure. The "all prerequisites satisfied" implementation-task branch was not taken.
- **2026-09-17 — Task 5 complete within the no-container boundary.** Preserved the six Grafana dashboard UIDs while removing the Grafana PostgreSQL datasource and product/business panels, leaving those tenant-scoped records in the Flynapse UI/API. Agent/LLM panels now use exact merged contracts, including Prometheus-translated counter/histogram names for OSS, `span.agent.outcome = "error"` for failed turns, and `tool_outcome="failure"` for failed tool attempts. AWS catalogue examples retain original dotted OTLP instrument names and CloudWatch brace selectors rather than Prometheus suffixes. A per-panel catalogue inventory records UID, title, exact query, emitted/static/live state, source and wiring; pending subagent, ledger-failure and Claude Code signals remain dark. Independent review required three fix rounds to correct query semantics and make the static tests bind every inventory record and reject unsupported live claims without false positives. Controller verification passed 72 non-container dashboard, alert, Collector, telemetry and acceptance checks with 2 environment-gated skips. Live Grafana/Prometheus/Tempo retrieval remains an owner-run Task 6 check.
- **2026-09-17 — Task 6 testing/documentation seat complete with blockers.** No containers, UI/browser processes, Grafana, Phoenix, Weaviate, cloud-provider services or live canaries were started. Fresh local checks passed the startup/partition/lifecycle lane (`62 passed`), agent/Phoenix evaluation lane (`119 passed`), full non-container OTel integration lane (`79 passed, 10 skipped`), Core analytics/API/static lane (`167 passed, 1 skipped`), explicit metric-cardinality and destination/profile composition lane (`31 passed`), Task 5 dashboard/alert/Collector/telemetry acceptance lane (`72 passed, 2 skipped`), Dashboard profile/product-event unit lane (`42 passed`), Dashboard typecheck, touched-file Dashboard lint, Copilot MRO `poetry check --lock`, and `bash -n deployment/otel/validate.sh`. The dashboard-profile scratch DB lane passed (`3 passed`) and dropped its throwaway database. The product-event replay scratch DB lane is blocked before assertions by `psycopg2.errors.InsufficientPrivilege: permission denied for table tenants` in the tenant fixture (`5 errors`); the facts-backfill scratch DB lane reproduces the same fixture-grant blocker (`2 errors`). Branch-wide Dashboard lint still fails only on the unrelated existing `hooks/pdf-viewer/use-pdf-search.ts:79-80` `prefer-const` findings. Owner-run checks remain pending for Flynapse UI rendering/profile switching, Grafana/Prometheus/Tempo live population, Phoenix traces/evaluations, pinned Collector Docker validation, single-host Docker base/Phoenix runs, provider canaries/field paths, production queue restart proof, Azure support refresh, Agent SDK/LangGraph runtime parity after Gate M plus Task R, and the separate GPT-5.6 final review. The API `.env.codex-backup-20260916T043907Z` remains untracked and uninspected.
