# Observability rebuild — Phase 6 detail plan (Stream D: dashboards, alerts, runbooks)

## 0. Header

- **Goal.** Replace the eight legacy Grafana boards with the six `oss` views of spec §9.2, provisioned as JSON from the repo; wire the spec §9.4 alerts into the existing empty `rule_files` seam with an Alertmanager container (Slack + email receivers on placeholder targets, ruling 19); ship runbook stubs per alert; author the CloudWatch (`aws`) equivalents of §9.3 to the extent probe B1c's recorded outcome permits, gating the rest as owner-ruled steps.
- **Master-plan tasks covered:** 6.1, 6.2, 6.3, 6.4 (authorable subset), 6.5, 6.6. **Spec:** §9.1–§9.4, §6.3 (metric names), §6.4 (`claude_code.*`), §6.6 (ledger honesty), ruling 10/19.
- **Branches / worktrees.** `obs-infra` in `/home/aditya/Code/copilot-mro-obs-infra` (deployment files + `tests/integration/otel/**` + `docs/runbooks/**`; the Stream I implementer has FINISHED, so one-implementer-per-worktree holds when the phase-6 implementer starts there). `obs-iac` in `/home/aditya/Code/iac-obs` (CloudWatch dashboards, SNS/Slack/email plumbing; validate-only — `plan`/`apply` are owner steps).
- **Legacy boards being replaced** (research 01, files under `deployment/observability-local/grafana/dashboards/`): `backend-metrics`, `chat-metrics`, `chat-quality`, `comments-service`, `authorization-metrics`, `document-viewer-metrics`, `frontend-perf`, `llm-metrics` — all querying dead series (audit G7/G8); `chat-quality` content was rebuilt product-side in Phase 5. The spec's "test-cookie" board is one of these panels, dropped.

## 1. Inherited constraints (master "Global constraints", brief "Hard constraints", §11a)

1. Plan/doc files contain no code snippets; dashboards, queries and rules are described in prose with exact identifiers in backticks.
2. Git: commit only files this phase creates plus test edits, by pathspec; never `git add -A`; edits and deletions of pre-existing files (compose, `prometheus.yml`, `loki-config.yaml`, `tempo.yaml`, provisioning YAML, `VERSIONS.md`, the legacy dashboard JSONs, `test-observability.py`, iac `README.md`) stay uncommitted and are listed in the uncommitted-edit ledger. Check `git diff --cached --name-only` before each commit; retry on `index.lock`.
3. Test layout: `tests/integration/otel/<file>` in copilot-mro, globally unique basenames (verified free: `test_grafana_dashboards.py`, `test_alert_rules_layout.py`, `test_alertmanager_config.py`, `test_grafana_provisioning_smoke.py`), `tests/_root.py` `repo_root` for every path — never `parents[N]`.
4. Standing pytest command, from the shared env with `PYTHONPATH` pinned to the worktree: `cd /home/aditya/Code/api && DEBUG=false PYTHONPATH=/home/aditya/Code/copilot-mro-obs-infra poetry run pytest /home/aditya/Code/copilot-mro-obs-infra/tests/integration/otel/<file> -q`.
5. §11a: every new container pinned to the latest stable verified at task time, recorded in `deployment/otel/VERSIONS.md`; every task carries a logging-coverage checkbox (most tasks here touch no runtime script — the checkbox records that).
6. Owner rulings are not re-litigated; deviations go to the implementation notes. No edits to any conflict-zone file; this phase touches no application code at all.
7. Foreground `sleep` is blocked — poll with bounded until-loops (the existing smoke conftest shows the pattern).

## 2. Ground truth — the landed signal contracts these dashboards are built against

Read from the code on 2026-09-05; the guard tests pin the parts that can drift.

### 2.1 Prometheus series (after `prometheusremotewrite` normalisation; `job` = `service.namespace/service.name`, i.e. `flynapse/api`, `flynapse/automation-worker`)

| Emitter (OTel name, unit) | Prometheus series | Key labels | Lights up |
|---|---|---|---|
| `http.server.request.duration` (s, histogram; NEW semconv; full mounted `http.route`) | `http_server_request_duration_seconds_bucket` / `_sum` / `_count` | `job`, `http_route`, `http_request_method`, `http_response_status_code`, `error_type` | at `obs-api` deploy (landed) |
| `http.server.active_requests` | `http_server_active_requests` | `job` | same |
| `auth.rejections` (`{request}`) | `auth_rejections_total` | `job` | same |
| resource per exporting service | `target_info` | `job`, `instance` | same |
| collector self-telemetry (Prometheus scrape of `otel-collector:8888`, job `otel-collector`) | `otelcol_exporter_send_failed_{spans,metric_points,log_records}_total`, `otelcol_exporter_queue_size`, `otelcol_exporter_queue_capacity`, `otelcol_receiver_accepted_{spans,metric_points,log_records}_total`, `otelcol_receiver_refused_*_total` | `exporter`, `receiver` | now (T3 verifies exact spellings against a live `:8888` scrape — collector minors rename) |
| Tempo metrics-generator (remote-written, external label `source="tempo"`) | `traces_spanmetrics_latency_bucket`/`_sum`/`_count`, `traces_spanmetrics_calls_total`, `traces_service_graph_request_total`, `traces_service_graph_request_failed_total`, `traces_service_graph_request_server_seconds_bucket` | `service`, `span_name`, `span_kind`, `status_code` (+ dimensions added in T3: `db_system`, `peer_service`, `server_address`, `rpc_service`) | now for any received spans |
| spec §6.3 ledger-sink metrics — `gen_ai.client.operation.duration` (s), `gen_ai.client.token.usage` (`{token}`), `agent.model.calls`, `agent.model.cost_usd` (`{USD}`), `agent.model.unpriced_calls`, `agent.turn.calls`, `agent.turn.duration_seconds`, `agent.tool.calls`, `agent.tool.attempts`, `agent.subagent.calls`, `agent.subagent.duration_seconds`, `agent.ledger.write_failures` | `gen_ai_client_operation_duration_seconds_*`, `gen_ai_client_token_usage_*`, `agent_model_calls_total`, `agent_model_cost_usd_total`, `agent_model_unpriced_calls_total`, `agent_turn_calls_total`, `agent_turn_duration_seconds_*`, `agent_tool_calls_total`, `agent_tool_attempts_total`, `agent_subagent_calls_total`, `agent_subagent_duration_seconds_*`, `agent_ledger_write_failures_total` | `gen_ai_request_model`, `gen_ai_provider_name`, `gen_ai_token_type` (incl. `cache_read`, `cache_write`, `reasoning`, `tool_search_overhead`), `model_role`, `model_purpose`, `model_profile`, `model_cost_source`, `graph_node`, `agent_department`, `tenant_id`, `agent_outcome`, `tool_name`, `tool_outcome`, `tool_error_code`, `ledger`, `reason` | **DARK until Stream L** (emitters land after Gate M) |
| Claude Code CLI (`claude_code.token.usage`, `claude_code.cost.usage`; delta→cumulative in the `oss` overlay; `transform/genai_aliases` adds `tenant.id`, `agent.department`, `gen_ai_token_type`, `gen_ai_request_model`) | `claude_code_token_usage_total`, `claude_code_cost_usage_total` | `gen_ai_request_model`, `gen_ai_token_type`, `tenant_id`, `agent_department` | **DARK until Stream L** (3.x turns CLI telemetry on) |

### 2.2 Loki (OTLP ingest; index labels `service_name`, `service_namespace`, `deployment_environment_name`; everything else structured metadata, dots→underscores)

Browser records ride `logs/browser` with gateway-verified `tenant_id` / `enduser_id` / `session_id` upserted and the F-stream envelope (`route_pattern`, `app.version`): `event_name` ∈ `browser.web_vital` (metadata `metric` ∈ LCP/INP/CLS/FCP/TTFB, `value`, `delta`, `rating`, `navigation_type`, `vital_id`), `browser.error` (`error_kind`, `error_type`, `fingerprint`, `component`), `browser.route.change` (`route_pattern_from`, `route_pattern_to`, `change_ms`, `ready_ms`). **DARK until Stream F's F10 cut-over goes live.** Backend logs (live at deploy): loguru bridge with `tenant.id`, `request.id`, `code.function.name` spellings; the automations worker logs one line per run lifecycle boundary with bound `automation_id` / `automation_run_id`.

### 2.3 Postgres (datasource user `flynapse_readonly`; SELECT grants landed in Phase 5 task 5.2)

`llm_usage` (spend day expression `COALESCE(started_at, created_at)`, `total_cost_usd`, `cost_complete`, `origin`, `department`, `model`), `llm_model_calls` (`created_at`, `cost_usd`, `model`, `outcome`, `latency_seconds`, `binding`), `product_events` (`event_name`, `occurred_at`, `document_id`, `document_kind`), `automation_runs` (`kind`, `status`, `late_run`, `duration_seconds`, `queue_seconds`), `automations`, `document_hub_documents` (`status`, `failure_code`), `chat_turn_facts`. Ledger honesty (spec §6.6): `lang`-served turns write no `llm_usage` row and data-discovery spend is absent — every spend panel carries that footnote, and no USD sum renders without its `cost_complete=false` count.

## 3. Decisions (stated once; tasks cite them)

- **D1 — provisioning location.** The six new dashboards are JSON files under `deployment/observability-local/grafana/provisioning/dashboards/flynapse/`, loaded by a second file provider named `flynapse` (folder `Flynapse`, path `/etc/grafana/provisioning/dashboards/flynapse`) added to the existing `dashboards.yml`. Grafana's provider reader only parses YAML in that directory, so JSON siblings are safe. The legacy provider and its `/var/lib/grafana/dashboards` mount survive until T9.
- **D2 — datasource uids.** Dashboard JSON references datasources by uid only: `prometheus`, `loki`, `tempo` (uid added to the existing Tempo entry — it has none today), and new `flynapse-postgres` (type `postgres`, user `flynapse_readonly`, password `$POSTGRES_READONLY_PASSWORD` via provisioning env-interpolation, host from `$POSTGRES_DATASOURCE_HOST`, database from `$POSTGRES_DATASOURCE_DB`; compose supplies defaults `postgres:5432` / `copilot_mro`). In the standalone `observe-docker-compose.yml` stack there is no Postgres service; the datasource is then unhealthy and exact-spend panels show a query error — documented in the README edit, accepted (that stack can point `POSTGRES_DATASOURCE_HOST` at the app DB host).
- **D3 — rules layout and the Alertmanager placeholder seam.** Prometheus rule YAML lives in `deployment/observability-local/rules/prometheus/` (three files: `flynapse-api-alerts.yml`, `flynapse-platform-alerts.yml`, `flynapse-agent-alerts.yml`); `prometheus.yml`'s empty `rule_files` becomes the single glob `/etc/prometheus/rules/*.yml` plus an `alerting.alertmanagers` target `alertmanager:9093`; the three Prometheus-bearing stacks mount the rules directory read-only. Alertmanager is a new pinned container (latest stable verified at task time; `v0.34.0`, released 2026-08-16, verified 2026-09-05 — re-verify at pin), loopback-only on `127.0.0.1:9093`. Because Alertmanager does not expand environment variables, secrets use its `_file` fields: `slack_api_url_file` and `smtp_auth_password_file` point at `/etc/alertmanager/secrets/…`, and each compose stack mounts those from env-var-selected host paths defaulting to committed placeholder files (`deployment/observability-local/alertmanager/slack_webhook_url.placeholder`, `smtp_password.placeholder`); the owner sets `ALERTMANAGER_SLACK_WEBHOOK_FILE` / `ALERTMANAGER_SMTP_PASSWORD_FILE` in the gitignored `.env` at rollout — nothing blocks on real targets and no secret can be committed. Non-secret placeholders (email `to:`, SMTP host, Slack channel) are literals in `alertmanager.yml` flagged in the runbook's rollout checklist.
- **D4 — browser alerts run on the Loki ruler.** `browser error rate` and `Web Vitals p75` exist only in Loki, so those rules are Loki-ruler rule files (same Prometheus rule-file schema, LogQL expressions) under `deployment/observability-local/rules/loki/flynapse/browser-alerts.yml` (tenant directory = `LOKI_TENANT_ID` default). `loki-config.yaml` gains a `ruler` block (local rule storage at `/loki/rules`, `alertmanager_url` `http://alertmanager:9093`, ruler API enabled) — a reported edit. `promtool` cannot parse LogQL, so these files are validated structurally by the guard test and at boot by the smoke.
- **D5 — runbooks live in the copilot-mro repo** at `docs/runbooks/observability/{oss-profile,aws-profile,alerts}.md` (the master's `docs/runbooks/…` path read repo-relative, as every other master path in this repo is). They ship with the rules they document and are guard-testable via `repo_root`. Every alert's `runbook` annotation is that repo path plus a stable per-alert anchor.
- **D6 — dark-panel convention.** Every panel or rule whose source series does not exist yet carries a description beginning `DARK until Stream L:` (or `DARK until Stream F cut-over:`) naming its source metric. The guard test enforces it mechanically: any dashboard target or rule expression naming an `agent_*`, `gen_ai_*` or `claude_code_*` series must carry the Stream L note; any `browser.*` reference the Stream F note. Alerts on absent series simply never fire — `promtool` accepts them; nothing errors at runtime.
- **D7 — CloudWatch authorable subset (probe ledger).** B1c (recorded in the phase-0-2 plan §11): resolved provider `hashicorp/aws 5.100.0`, **no** PromQL alarm support, no `awscc` in the root, constraint not to be raised by this stream. B1b (Logs OTLP stored field paths) and B1d (Application Signals from vanilla spans) are owner-owed. Therefore: the six `aws_cloudwatch_dashboard` bodies ARE authored (the provider treats the body as an opaque JSON string) using only widget families with a documented stable schema — Logs Insights `log` widgets (queries written against the expected `resource.attributes.service.name` paths, re-verified after B1b) and `text` widgets carrying the canonical Query Studio PromQL and Transaction Search queries as copy-paste console links; the SNS → Slack webhook + email plumbing IS authored; PromQL **alarms**, PromQL **metric widgets** (their body schema is undocumented — one console export is needed) and App Signals **SLO objects** are gated owner-ruled items in §Open questions, not invented dialects.
- **D8 — commit policy applied here.** New files and test edits are committed by pathspec. `VERSIONS.md` (Alertmanager row), all compose files, `prometheus.yml`, `loki-config.yaml`, `tempo.yaml`, both provisioning YAMLs, READMEs, and the T9 deletions are pre-existing → uncommitted, reported. The pin guard `test_compose_image_pins.py` gains the Alertmanager entry as a committed test edit; it reads the working tree, so it stays green despite the split.

## 4. File structure

**copilot-mro-obs-infra (branch `obs-infra`) — create (committed):** `deployment/otel/dashboards/CATALOGUE.md`; `deployment/observability-local/grafana/provisioning/dashboards/flynapse/{service-overview,dependencies,llm-agents,agent-turn-explorer,frontend,platform-health}.json`; `deployment/observability-local/rules/prometheus/{flynapse-api-alerts,flynapse-platform-alerts,flynapse-agent-alerts}.yml`; `deployment/observability-local/rules/loki/flynapse/browser-alerts.yml`; `deployment/observability-local/alertmanager.yml`; `deployment/observability-local/alertmanager/{slack_webhook_url.placeholder,smtp_password.placeholder}`; `deployment/observability-local/validate-rules.sh`; `deployment/otel/smoke/docker-compose.grafana-smoke.yml`; `.github/workflows/rules-validate.yml`; `docs/runbooks/observability/{oss-profile,aws-profile,alerts}.md`; tests `tests/integration/otel/{test_grafana_dashboards,test_alert_rules_layout,test_alertmanager_config,test_grafana_provisioning_smoke}.py`.

**Modify (reported, uncommitted):** `deployment/observability-local/{observe-docker-compose.yml,prometheus.yml,loki-config.yaml,tempo.yaml,README.md}`, `deployment/{docker-compose.yml,poc/docker-compose.yml}`, `grafana/provisioning/{dashboards/dashboards.yml,datasources/datasources.yml}`, `deployment/otel/VERSIONS.md`. **Test edits (committed):** `test_compose_image_pins.py`, `test_compose_port_bindings.py`. **Delete (reported):** the eight legacy dashboard JSONs, `deployment/observability-local/test-observability.py`, plus the legacy provider block and `grafana/dashboards` mounts (edits).

**iac-obs (branch `obs-iac`) — create (committed):** `cloudwatch_dashboards.tf`, `dashboards/{service-overview,dependencies,llm-agents,agent-turn-explorer,frontend,platform-health}.json.tftpl`, `alerting.tf`, `lambda_src/sns_to_slack.py`. **Modify (reported):** `README.md` (owner-step additions only).

## 5. Standard commands

- Pytest (per task): the §1.4 standing command naming the task's test file.
- Rules check: `bash /home/aditya/Code/copilot-mro-obs-infra/deployment/observability-local/validate-rules.sh` — runs `promtool check rules` on each `rules/prometheus/*.yml` and `amtool check-config` on `alertmanager.yml` via `docker run` of the pinned `prom/prometheus:v3.14.0` / `prom/alertmanager:v0.34.0` images (entrypoint override), and a YAML-shape pass over the Loki rule file. Also invoked by the always-on guard tests when `OTEL_RULES_CHECK=1` and docker is reachable.
- Grafana smoke: `cd /home/aditya/Code/api && DEBUG=false PYTHONPATH=/home/aditya/Code/copilot-mro-obs-infra OTEL_COMPOSE_SMOKE=1 poetry run pytest /home/aditya/Code/copilot-mro-obs-infra/tests/integration/otel/test_grafana_provisioning_smoke.py -q -m compose_stack`.
- iac: `cd /home/aditya/Code/iac-obs && terraform fmt -check -recursive && terraform init -backend=false && terraform validate` (local-backend override per the phase-0-2 B1c learning if `init` refuses).
- Commits: `git -C /home/aditya/Code/copilot-mro-obs-infra add <paths> && git -C /home/aditya/Code/copilot-mro-obs-infra commit -m "obs D<n>: <what>" -- <paths>` (same shape in `iac-obs`); retry on `index.lock`.

## 6. Tasks (dependency order)

### T1 (= 6.1) — Six-view catalogue, the shared spec for both dialects

**Files.** Create `deployment/otel/dashboards/CATALOGUE.md`.
**Interfaces produced.** One section per view — exact name, uid, the operator question it answers, its signals (series/LogQL selectors/TraceQL/SQL sources from §2 of this plan, with per-panel dark markers), and per-backend query notes: `oss` = PromQL/LogQL/TraceQL/SQL as authored in T2/T3; `aws` = the CloudWatch translation (Logs Insights query text against the expected `resource.attributes.*` paths flagged "re-verify after B1b", Query Studio PromQL with `@resource.service.name` labels and dotted metric names, Transaction Search in place of TraceQL, exact-spend panels marked "Postgres — reachable only where the app DB is; not a CloudWatch surface"). Ends with the alarm translation table consumed by T12: each T5/T6/T7 alert → its CloudWatch expression intent and which gate (PromQL-alarm ruling, B1b, B1d) blocks it.
**Steps.**
- [x] Write the catalogue covering exactly the six §9.2 views; cross-check every §9.2 sentence has a panel row and every §9.4 alert appears in the translation table.
- [x] Logging coverage: no scripts touched — n/a, recorded.
- [x] Commit `deployment/otel/dashboards/CATALOGUE.md` by pathspec.
**Acceptance.** Catalogue names all six views with no view lacking signals or backend notes; the T2 guard test (next task) will pin JSON↔catalogue agreement.
**Review triage.** "Catalogue duplicates the plan" → intended: the plan is process, the catalogue is the maintained artefact both dialects are edited against (spec §9.3 "the shared spec").

### T2 (= 6.2 part 1) — Provisioning seam, datasources, guard test, first dashboard

**Files.** Create `tests/integration/otel/test_grafana_dashboards.py` and `grafana/provisioning/dashboards/flynapse/service-overview.json`. Modify (reported): `dashboards.yml` (add the D1 `flynapse` provider), `datasources.yml` (Tempo `uid: tempo`; add `flynapse-postgres` per D2), the three stacks' Grafana service env (`POSTGRES_READONLY_PASSWORD`, `POSTGRES_DATASOURCE_HOST`, `POSTGRES_DATASOURCE_DB` passthrough).
**Interfaces.** Guard test module constants: `DASHBOARD_DIR`, `EXPECTED_UIDS = ("fn-service-overview", "fn-dependencies", "fn-llm-agents", "fn-agent-turn-explorer", "fn-frontend", "fn-platform-health")`, `ALLOWED_DATASOURCE_UIDS = ("prometheus", "loki", "tempo", "flynapse-postgres")`. Checks per JSON: parses; `uid`/`title` present, unique, uid in `EXPECTED_UIDS`; every panel's datasource uid allowed and declared in `datasources.yml`; every target has a non-empty `expr`/`rawSql`/TraceQL `query`; D6 dark-note lint (`agent_`/`gen_ai_`/`claude_code_` ⇒ "DARK until Stream L" in the panel description; `browser.` ⇒ Stream F note); every uid has a catalogue section and vice versa; refuses any legacy-board uid. Until T3 lands the remaining five files, the test asserts only over files present plus "at least `fn-service-overview` exists" (flipped to all-six in T3).
**Service-overview panels** (all Prometheus, live at deploy; template variable `job` over `label_values` of `http_server_request_duration_seconds_count`): request rate by `job` (5m `rate` of the `_count` series summed by `job`); 5xx ratio by `job` (`http_response_status_code` matching 5xx over total, guarded against zero traffic); p50/p95/p99 (`histogram_quantile` over `_bucket` summed by `le`,`job`); top-10 slow routes table (p95 by `http_route`); 5xx by route (top-10 rate filtered 5xx, by `http_route`); in-flight (`http_server_active_requests` by `job`); auth rejection rate (`auth_rejections_total` rate by `job` — the authorization board's replacement signal).
**Steps.**
- [x] Write the failing guard test; run (red: no directory, no JSON).
- [x] Add the provider + datasource edits and author `service-overview.json` (Grafana 13.2.1 schema; panels above; description strings name their series).
- [x] Run the guard test (green). Logging coverage: n/a, recorded.
- [x] Commit `tests/integration/otel/test_grafana_dashboards.py` and `grafana/provisioning/dashboards/flynapse/service-overview.json`; report the YAML/compose edits.
**Test command.** §1.4 standing command with `test_grafana_dashboards.py`.
**Acceptance.** Guard green; `docker compose config` on each edited stack still parses (compose interpolation unbroken).
**Review triage.** "Datasource secrets in YAML" → no: password is env-interpolated at Grafana boot, never committed. "Postgres datasource unhealthy in the standalone stack" → D2, accepted + documented.

### T3 (= 6.2 part 2) — The remaining five dashboards

**Files.** Create the five JSONs under `grafana/provisioning/dashboards/flynapse/`. Modify (reported): `tempo.yaml` — add `span_metrics` dimensions `db.system`, `peer.service`, `server.address`, `rpc.service` under the metrics-generator processor config; `prometheus.yml` — add self-scrape jobs `loki` (`loki:3100`) and `tempo` (`tempo:3200`) for storage/ingest panels.
**Dashboards (every panel names its source; dark markers per D6):**
- `fn-dependencies` — client-span p95/error-rate by dependency from `traces_spanmetrics_latency_bucket` / `traces_spanmetrics_calls_total` filtered `span_kind="SPAN_KIND_CLIENT"`, grouped by the new `db_system` (postgresql, redis) and `server_address`/`rpc_service` (Weaviate, S3, Bedrock); error share via `status_code="STATUS_CODE_ERROR"`; a service-graph node panel on the `tempo` datasource (service map is already wired to `prometheus`); DB span note: OLD semconv `db.system` per the Phase 1 hand-off.
- `fn-llm-agents` — ALL Prometheus panels dark until Stream L: token throughput by `gen_ai_request_model`×`gen_ai_token_type` (rate of `gen_ai_client_token_usage_sum`); model-call rate and `agent_model_cost_usd_total` hourly increase by `tenant_id`/`model_profile` **always beside** `agent_model_unpriced_calls_total`; cache-hit ratio (cache_read over cache_read+input+cache_write token sums); turn outcomes (`agent_turn_calls_total` by `agent_outcome`) and p95 `agent_turn_duration_seconds`; tool calls/failures (`agent_tool_attempts_total` by `tool_name`, failures via `tool_outcome`/`tool_error_code`); subagent rate + p95 duration; CLI `claude_code_token_usage_total` / `claude_code_cost_usage_total` by model and `gen_ai_token_type`. Bedrock-throttle panel intentionally absent in `oss` (catalogue notes the `aws` source). LIVE NOW: two exact-spend panels on `flynapse-postgres` — daily tenant spend from `llm_usage` (`SUM(total_cost_usd)` with its mandatory `COUNT(*) FILTER (WHERE NOT cost_complete)` companion, bucketed on `COALESCE(started_at, created_at)` under the Grafana time-range macro) and spend by `model` from `llm_model_calls` (`SUM(cost_usd)` + NULL-cost count); both footnoted with the §6.6 lang/data-discovery caveat.
- `fn-agent-turn-explorer` — dark until Stream L; `tempo` datasource: slowest turns (TraceQL: spans where `gen_ai.operation.name` equals `invoke_agent`, table of duration, `tenant.id`, `gen_ai.agent.name`, sorted desc); failed turns (same selector with error status); tool-latency table (Prometheus: p95 of `traces_spanmetrics_latency_bucket` for `span_name` matching the `execute_tool ` prefix, by `span_name`); every table row links through to the trace waterfall (Tempo data links).
- `fn-frontend` — dark until Stream F cut-over: Web Vitals p75 by `route_pattern`×`metric` (LogQL `quantile_over_time` 0.75 unwrapping `value` over `service_name="dashboard"` records with `event_name="browser.web_vital"`); rating distribution (`count_over_time` by `rating`); browser errors by `error_kind` + top `fingerprint` table; route-change timings (p75 of unwrapped `change_ms`/`ready_ms` by `route_pattern_to`); browser-seen API latency (p95 `traces_spanmetrics_latency_bucket` for `service="dashboard"` client spans). LIVE at Phase 5: document opens from `product_events` (`event_name='document_opened'` daily count + top `document_id`×`document_kind`) on `flynapse-postgres`.
- `fn-platform-health` — collector exporter failures/queue fill/receiver refusals and per-signal ingest rates from the `otelcol_*` series (live; exact spellings verified against a live `:8888` scrape during this task and pinned in the JSON); `agent_ledger_write_failures_total` (dark until L); worker heartbeat (seconds since the newest `target_info` sample for `job="flynapse/automation-worker"`, plus an absent-series stat); doc-hub processing and automations panels on `flynapse-postgres` (`automation_runs` failed/late over time split on `kind='document_hub_process'`; `document_hub_documents` `needs_attention` by `failure_code`); Loki/Tempo/Prometheus health from the new scrape jobs (`prometheus_tsdb_head_series`, Loki distributor ingest-bytes rate, Tempo ingester received-bytes rate — exact series confirmed from each `/metrics` at task time and named in the JSON).
**Steps.**
- [x] Flip the guard test to require all six uids (run: red with one file).
- [x] Author the five JSONs; make the `tempo.yaml` + `prometheus.yml` edits; re-run the guard (green).
- [x] Boot the local `observe-docker-compose.yml` stack once and verify the two new scrape targets are up and the span-metrics dimension labels appear; record actual `otelcol_*`/Loki/Tempo series spellings in the JSON and the catalogue.
- [x] Logging coverage: n/a, recorded. Commit the five JSONs (pathspec); report edits.
**Test command.** As T2.
**Acceptance.** Guard green over six files; every §9.2 bullet maps to a panel (checked against the catalogue); dark-note lint passes.
**Review triage.** "Panels on series that don't exist" → D6: deliberate, spec-ordered, mechanically labelled. "`server_address` cardinality" → bounded host set (RDS/Redis/Weaviate/S3/Bedrock endpoints), reviewed at scrape.

### T4 (= 6.2 part 3) — Grafana provisioning smoke via the API

**Files.** Create `tests/integration/otel/test_grafana_provisioning_smoke.py` and `deployment/otel/smoke/docker-compose.grafana-smoke.yml`.
**Interfaces.** Marker `compose_stack`, env gate `OTEL_COMPOSE_SMOKE=1` (registered pattern). The override runs ONLY the `grafana` service from `observe-docker-compose.yml` (`--no-deps`), project name `flynapse-grafana-smoke`, tmpfs data dir, loopback remap of 3000 to a smoke port, dummy `GRAFANA_ADMIN_PASSWORD`/`LOKI_TENANT_ID`/`POSTGRES_READONLY_PASSWORD`. The test polls `/api/health` with a bounded loop (conftest pattern), then asserts via basic-auth API: `/api/dashboards/uid/<uid>` returns each of the six with its expected title, and `/api/datasources` lists the four uids. Teardown always `down -v`.
**Steps.**
- [x] Write the failing test (red while it asserts against a stack not yet running / before provisioning fix-ups); implement the override; run with `OTEL_COMPOSE_SMOKE=1` (green).
- [x] Logging coverage: n/a (test-only). Commit both files by pathspec.
**Test command.** §5 Grafana smoke line.
**Acceptance.** Six dashboards load via the API from a cold container; datasource provisioning parses with env interpolation.
**Review triage.** "Smoke doesn't query panels" → datasource-backed query smoke needs the full stack + emitters; the compose smoke of A8 covers pipeline flow; panel-query verification is the phase-close manual step in the runbook.

### T5 (= 6.3 part 1) — Prometheus alert rules into the `rule_files` seam

**Files.** Create the three rule files under `rules/prometheus/`, `validate-rules.sh`, `.github/workflows/rules-validate.yml`, `tests/integration/otel/test_alert_rules_layout.py`. Modify (reported): `prometheus.yml` (glob + alertmanagers), the three stacks (mount `rules/prometheus` at `/etc/prometheus/rules`, read-only).
**Alert set** (labels: `severity`; annotations: `summary`, `description`, `runbook` = `docs/runbooks/observability/alerts.md#` + lower-cased alert name; all route to receiver `flynapse-obs`):
| Alert (file) | Expression intent | Threshold / for | Severity |
|---|---|---|---|
| `ApiHighErrorRate` (api) | 5xx share of `http_server_request_duration_seconds_count` per `job`, 5m rate, with a >0.1 rps traffic guard | >5% for 10m | critical |
| `ApiP95LatencyHigh` (api) | `histogram_quantile` 0.95 per `job`×`http_route` | >5 s for 15m | warning |
| `CollectorExporterFailures` (platform) | any positive rate across the three `otelcol_exporter_send_failed_*_total` | >0 for 10m | critical |
| `CollectorExporterQueueNearFull` (platform) | max `otelcol_exporter_queue_size` over `otelcol_exporter_queue_capacity` | >0.8 for 10m | warning |
| `CollectorReceiverRefusing` (platform) | positive rate of `otelcol_receiver_refused_*_total` | >0 for 10m | warning |
| `AutomationWorkerSilent` (platform) | `absent` of `target_info` for `job="flynapse/automation-worker"` | 15m | warning |
| `AgentTurnFailureRatioHigh` (agent, DARK-L) | error-outcome share of `agent_turn_calls_total` by `agent_outcome`, 15m window, volume-guarded | >10% for 15m | critical |
| `UnpricedModelCalls` (agent, DARK-L) | 30m increase of `agent_model_unpriced_calls_total` | >0 for 30m | warning |
| `LedgerWriteFailures` (agent, DARK-L) | 10m increase of `agent_ledger_write_failures_total` | >0 for 5m | critical |
| `TenantDailySpendHigh` (agent, DARK-L) | 24h increase of `agent_model_cost_usd_total` summed by `tenant_id` | >$50 (default — owner ruling pending) for 30m | warning |
**Guard test** checks: YAML parses into groups/rules; every alert carries `severity` ∈ {`warning`,`critical`}, `summary`, `description`, `runbook` whose file exists under `repo_root` (anchor check lands with T8 and is asserted from T8 on); the `prometheus.yml` glob covers exactly these files; each of the three stacks mounts the directory; D6 dark-note lint on `agent_*` expressions; env-gated (`OTEL_RULES_CHECK=1` + docker) subprocess run of `promtool check rules` via `prom/prometheus:v3.14.0`.
**Steps.**
- [x] Write the failing guard test; run (red).
- [x] Author the three rule files, `validate-rules.sh` (set-strict shell; echoes one line per file checked and a fail line naming the file — that is its logging coverage), the workflow (runs the script on PRs touching `deployment/observability-local/rules/**` or `alertmanager.yml`), and the `prometheus.yml`/compose edits.
- [x] Run the guard; run `validate-rules.sh` (promtool green). Logging coverage checkbox: `validate-rules.sh` reviewed — [x].
- [x] Commit the three rule files + script + workflow + test by pathspec; report edits.
**Test command.** §1.4 with `test_alert_rules_layout.py`; plus the §5 rules-check line.
**Acceptance.** `promtool check rules` exits 0 on all three files; guard green; a booted local stack shows the rules on the Prometheus rules page.
**Review triage.** "Doc-hub failures and automation late/failed-run alerts missing" → deliberate: no metric emitter exists (Postgres-only signals today); Loki proxy in T7, real counters are a Stream L / R.2 hand-off recorded in Open questions — not authorable here without inventing metric names.

### T6 (= 6.3 part 2) — Alertmanager container with Slack + email receivers

**Files.** Create `alertmanager.yml`, the two placeholder secret files, `tests/integration/otel/test_alertmanager_config.py`. Modify (reported): the three compose stacks (service `alertmanager`, image `prom/alertmanager:v0.34.0` — re-verify latest stable at pin time per §11a — loopback `127.0.0.1:9093`, mounts for config + the D3 env-selected secret files, restart policy, observability network), `VERSIONS.md` (new row + changelog line). Test edits (committed): `test_compose_image_pins.py` (`OBSERVABILITY_PINS` gains `prom/alertmanager`), `test_compose_port_bindings.py` (9093 must be loopback).
**Interfaces.** `alertmanager.yml`: root route → receiver `flynapse-obs`, `group_by` alertname+severity, child route matching `severity="critical"` with a shorter `repeat_interval`; receiver `flynapse-obs` with `slack_configs` (`api_url_file` `/etc/alertmanager/secrets/slack_webhook_url`, `send_resolved` true) and `email_configs` (`to` placeholder `ops-placeholder@flynapse.ai`, smarthost placeholder `smtp.placeholder.invalid:587`, `auth_password_file` `/etc/alertmanager/secrets/smtp_password`); no inhibit rules.
**Guard test:** config YAML shape (route/receivers agree with what T5 rules target), `_file` fields only (asserts no inline `api_url`/`auth_password` keys anywhere), placeholder files exist and contain no `hooks.slack.com/services/T`-shaped real webhook, all three stacks pin the image to the `VERSIONS.md` value and mount the secrets, port loopback; env-gated `amtool check-config` via the pinned image.
**Steps.**
- [x] Write the failing guard test; run (red).
- [x] Verify the current latest stable Alertmanager release; pin it (update this plan's implementation notes if it moved past `v0.34.0`); author config + placeholders; wire the three stacks; add the `VERSIONS.md` row.
- [x] Run guard + `validate-rules.sh` (now also amtool). Boot the local stack: Prometheus `/api/v1/alertmanagers` shows the target; fire a synthetic alert (amtool against loopback 9093) and see it in the Alertmanager UI. Logging coverage: n/a beyond the script already covered.
- [x] Commit config, placeholders, test file, and the two test edits by pathspec; report compose/`VERSIONS.md` edits.
**Test command.** §1.4 with `test_alertmanager_config.py`.
**Acceptance.** `amtool check-config` exits 0; synthetic alert visible; nothing blocks on real targets (ruling 19).
**Review triage.** "Placeholder email will bounce" → intended until rollout; the runbook rollout checklist is the owner's cue. "Why not env expansion" → Alertmanager has none; `_file` fields are its supported secret path.

### T7 (= 6.3 part 3) — Loki-ruler browser alerts

**Files.** Create `rules/loki/flynapse/browser-alerts.yml`. Modify (reported): `loki-config.yaml` (D4 ruler block), the three stacks (mount `rules/loki` at `/loki/rules`, read-only). Test edit (committed): extend `test_alert_rules_layout.py` to validate the Loki file (same schema checks; LogQL expressions checked structurally — non-empty, name the `event_name` values — since promtool cannot parse them) and the tenant-directory convention.
**Alert set** (all DARK until Stream F cut-over; receiver/routing identical via the shared Alertmanager):
| Alert | Expression intent | Threshold / for | Severity |
|---|---|---|---|
| `BrowserErrorRateHigh` | count of `browser.error` records over 15m for `service_name="dashboard"` | >30 per 15m (default — owner may retune) for 15m | warning |
| `WebVitalLcpP75Poor` | 30m p75 of unwrapped `value` where `metric="LCP"` | >4000 ms for 30m | warning |
| `WebVitalInpP75Poor` | same for `INP` | >500 ms for 30m | warning |
| `WebVitalClsP75Poor` | same for `CLS` | >0.25 for 30m | warning |
| `AutomationRunErrors` | count of worker error-severity log records (`service_name` of the worker) over 15m — the authorable proxy for failed runs until Stream L emits a counter | >0 for 15m | warning |
**Steps.**
- [x] Extend the guard (red), author the rule file + ruler/mount edits, re-run (green).
- [x] Boot the local stack; assert the ruler loaded the group via Loki's Prometheus-compatible rules API (bounded poll).
- [x] Logging coverage: n/a. Commit the rule file + test edit by pathspec; report edits.
**Test command.** As T5.
**Acceptance.** Ruler lists the group; no Loki boot error; guard green.
**Review triage.** "Log-derived alerts are non-portable" (research 04 §7 rule) → acknowledged: browser signals exist only as logs by design (spec §7.4); the CloudWatch translation via Logs Insights/metric filters is catalogued and gated on B1b; `AutomationRunErrors` is explicitly transitional.

### T8 (= 6.5) — Runbooks

**Files.** Create `docs/runbooks/observability/{oss-profile.md,aws-profile.md,alerts.md}`. Test edit (committed): `test_alert_rules_layout.py` gains the anchor check — every alert name across `rules/**` has a matching heading in `alerts.md`.
**Content.** `oss-profile.md`: switching profile (base+overlay flags, the README's port contract), rotating secrets (`GRAFANA_ADMIN_PASSWORD`, `LOKI_TENANT_ID` scope, `POSTGRES_READONLY_PASSWORD`, Phoenix keys), reading a trace end-to-end (Grafana → Tempo → span attributes), answering "what did tenant X spend" (the exact-spend SQL over `llm_usage` with the `cost_complete` and §6.6 lang/data-discovery caveats), and the **alert-target rollout checklist** (set the two `ALERTMANAGER_*_FILE` env vars, replace the email/SMTP placeholders, re-run `validate-rules.sh`). `aws-profile.md`: the same operator questions on CloudWatch surfaces (Logs Insights, Query Studio PromQL, Transaction Search), the owner-owed steps B1b/B1d/Transaction-Search toggle with their exact commands from the phase-0-2 plan §11, SSM webhook parameter for T11, and the PromQL-alarm gate status. `alerts.md`: one section per alert (all fifteen from T5/T6/T7): meaning, first checks, which dashboard panel to open, known causes, escalation; DARK alerts state their arming condition.
**Steps.**
- [x] Extend the guard with the anchor check (red — no runbooks); write the three files; re-run (green).
- [x] Logging coverage: n/a. Commit the three runbooks + test edit by pathspec.
**Test command.** As T5.
**Acceptance.** Anchor check green; every §9.4-derived alert has a stub; no "TBD" text (guard greps for it).
**Review triage.** "Stubs are thin" → stubs are the 6.5 deliverable; operational depth accrues with incidents.

### T9 (= 6.6) — Delete the legacy boards and the synthetic generator

**Files.** Delete (working tree, reported — not committed per D8): the eight JSONs under `grafana/dashboards/`, `test-observability.py`. Modify (reported): `dashboards.yml` (drop the legacy provider), the three stacks' Grafana service (drop the `grafana/dashboards` mount), `observability-local/README.md` (already-dirty file: document the new layout).
**Steps.**
- [x] Grep the repo for references to the deleted paths (`rg -n "test-observability|grafana/dashboards"`) — the A-stream guards iterate compose files, not dashboards; fix any hit found (expected: README only).
- [x] Delete + edit; re-run the whole otel lane (T2 guard must not regress; smoke re-run proves Grafana boots with only the `flynapse` provider).
- [x] Logging coverage: n/a. Nothing to commit; record every deletion in the uncommitted-edit ledger.
**Test command.** §1.4 with the whole `tests/integration/otel/` directory.
**Acceptance.** Lane green; smoke green; Grafana shows only the `Flynapse` folder's six boards.
**Review triage.** "Deletions uncommitted feels unfinished" → D8/brief rule: pre-existing files are the owner's to commit; the ledger makes it one `git add` for him.

### T10 (= 6.4 part 1, iac-obs) — CloudWatch dashboard bodies

**Files.** Create `cloudwatch_dashboards.tf` + the six `dashboards/*.json.tftpl` templates (variables: region, the `aws_cloudwatch_log_group` names already defined in `iac/cloudwatch.tf`, referenced by resource — no hard-coded group strings).
**Interfaces.** Six `aws_cloudwatch_dashboard` resources named `flynapse-<view>`. Per D7 each body carries: Logs Insights `log` widgets (service RED from the OTLP log groups against expected `resource.attributes.service.name` paths, browser/worker error counts, marked re-verify-after-B1b in a comment field of the query text) and `text` widgets holding the canonical Query Studio PromQL (dotted names + `@resource.` labels, from the T1 catalogue) and Transaction Search / Application Signals console pointers. Every variable used by a template is declared in `cloudwatch_dashboards.tf` itself (no `variables.tf` edit). Note in the resource comments: $3/dashboard-month.
**Steps.**
- [x] Author templates + resources; run `terraform fmt -check -recursive`, `terraform init -backend=false`, `terraform validate` (red → green as usual; validate is the test here — there is no pytest in iac).
- [x] Logging coverage: n/a (no runtime scripts). Commit `cloudwatch_dashboards.tf` + `dashboards/` by pathspec.
**Acceptance.** `terraform validate` exits 0; each template renders (validate exercises `templatefile`); six views mirror the T1 catalogue's aws column.
**Review triage.** "No PromQL metric widgets" → D7: widget schema undocumented; gated on the one-console-export probe (Open questions), not guessed.

### T11 (= 6.4 part 2, iac-obs) — SNS topic, email subscriptions, Slack forwarder

**Files.** Create `alerting.tf`, `lambda_src/sns_to_slack.py`.
**Interfaces.** `aws_sns_topic` `observability_alerts`; `aws_sns_topic_subscription` email per entry of `var.alert_email_addresses` (list, default empty — placeholder-safe, ruling 19); a Python 3.12 `aws_lambda_function` `sns_to_slack` (archive_file of `lambda_src/`, its own log group with retention per the `cloudwatch.tf` pattern, role limited to logs + `ssm:GetParameter` on the webhook parameter) subscribed to the topic, created only when `var.alert_slack_webhook_ssm_parameter` (default empty) is set; `aws_lambda_permission` for SNS. The handler reads the webhook URL from SSM once per cold start, posts a compact Slack message (alarm name, state, reason, region link), and logs one structured line per lifecycle boundary (received/posted/failed with alarm name and status code, never the full SNS payload body) — that is this task's logging-coverage item.
**Steps.**
- [x] Author both files; `terraform fmt`/`init -backend=false`/`validate` green; a local `python3 -m py_compile` of the handler.
- [x] Logging coverage checkbox for `sns_to_slack.py`: [x] verified per §11a (bound context, no silent except, no payload dump).
- [x] Commit `alerting.tf` + `lambda_src/sns_to_slack.py` by pathspec; report the `README.md` owner-step addition (create the SSM SecureString, confirm email subscriptions).
**Acceptance.** Validate green; with both vars at defaults the plan surface adds only the topic (checked by reading the graph, not by running `plan` — owner step).
**Review triage.** "Alarms → topic wiring absent" → nothing can target the topic until the alarm dialect is ruled (T12); the topic ships first so the ruling lands into a ready seam.

### T12 (= 6.4 part 3) — CloudWatch alarm dialect: owner-gated, documented, not invented

**Files.** None in Terraform. The T1 catalogue's alarm translation table + `aws-profile.md` (T8) carry, per §9.4 alert: the CloudWatch expression intent, and which gate blocks authoring — PromQL alarms need an owner ruling (raise `hashicorp/aws` past 5.100.0, add `awscc`, or defer; B1c evidence in the phase-0-2 plan §11), Logs-Insights-derived alarms need B1b's stored field paths, SLO objects need B1d.
**Steps.**
- [x] Verify the table covers all §9.4 alerts and names each gate; record the three-way ruling request in Open questions.
**Acceptance.** No invented dialect anywhere in `iac-obs`; grep for `aws_cloudwatch_metric_alarm` returns nothing new.
**Review triage.** "Phase 6 ships without aws alerts" → correct and deliberate: B1c ruled the provider can't express them; the ruling is the owner's blast-radius call (phase-0-2 plan, same conclusion).

### T13 — Phase close

- [x] Full lane: §1.4 command over `tests/integration/otel/` (plus `OTEL_COMPOSE_SMOKE=1` smokes and `OTEL_RULES_CHECK=1`); `terraform validate` in `iac-obs`. **70 passed** (92s, both smokes booted real containers); validate green; all six tftpl bodies JSON-parse after variable substitution.
- [ ] Adversarial review subagent per master §12 — **NOT RUN: the session brief forbids this implementer from spawning subagents.** Owed to the owner / a fresh agent; brief it with this plan + `git -C copilot-mro-obs-infra diff a9daa317..394e0d89` and the uncommitted working-tree diff, plus the two iac-obs commits. A self-review pass ran instead (JSON parse of all bodies, full lane, boot checks per task) — it is not a substitute.
- [x] Implementation notes + learnings into master §15; uncommitted-edit ledger finalised below; owner review before any merge.

## 7. Acceptance for Phase 6 (master §10)

Six provisioned dashboards load from a cold Grafana (smoke-proven), each panel naming a real or explicitly-dark source; `promtool check rules` and `amtool check-config` exit 0; the Loki ruler loads the browser rules; Alertmanager runs loopback-only with placeholder Slack/email targets; runbook stubs exist for every alert (guard-enforced anchors); legacy boards and `test-observability.py` are gone from the working tree; `iac-obs` validates with six dashboard bodies + the SNS/Slack/email seam; nothing was committed outside created files + test edits.

## 8. Uncommitted-edit ledger (FINAL, 2026-09-05 — everything below sits in the working tree on top of Stream I's own uncommitted edits, which are untouched)

**copilot-mro-obs-infra, phase-6 edits to pre-existing files:**
- `deployment/observability-local/observe-docker-compose.yml` — Grafana Postgres env passthrough; alertmanager service; prometheus + loki rules mounts; legacy dashboards mount dropped
- `deployment/docker-compose.yml` — same four changes, `./observability-local/` paths
- `deployment/poc/docker-compose.yml` — same four changes, `../observability-local/` paths (comment notes the POC has no postgres service)
- `deployment/observability-local/prometheus.yml` — `rule_files` glob + `alerting.alertmanagers`; `loki`/`tempo` scrape jobs
- `deployment/observability-local/loki-config.yaml` — D4 ruler block (`rule_path: /loki/rules-temp`)
- `deployment/observability-local/tempo.yaml` — span-metrics dimensions (`db.system`, `peer.service`, `server.address`, `rpc.service`)
- `deployment/observability-local/grafana/provisioning/dashboards/dashboards.yml` — flynapse provider added (T2), legacy provider removed (T9)
- `deployment/observability-local/grafana/provisioning/datasources/datasources.yml` — Tempo `uid: tempo`; `flynapse-postgres` datasource
- `deployment/observability-local/README.md` — new-layout documentation (already dirty from Stream I)
- ~~`deployment/otel/VERSIONS.md`~~ — **COMMITTED in the fix pass** (`62792306`; session-lead ruling: the file was created by this branch's own A1 commit, so the never-commit-pre-existing-files rule does not apply to it)
- **Deletions:** the eight `grafana/dashboards/*-dashboard.json` files, `deployment/observability-local/test-observability.py`

**iac-obs:** `README.md` — "Phase 6 — dashboards and alert routing (owner steps)" section incl. the validate steps for `scripts/validate_dashboards.sh` and the merge note below (already dirty from Stream I).

**MERGE HAND-CARRY (iac-obs):** the committed `cloudwatch.tf` (Stream I) and `alerting.tf` (T11) both reference `var.log_retention_days`, declared ONLY in the uncommitted `variables.tf` delta — that delta (and the rest of Stream I's uncommitted edits) MUST land together with the branch merge or `terraform validate` fails on the root. Stated in the iac README merge note as well.

Stream I's inherited uncommitted edits (both worktrees) verified untouched: `deployment/demo/docker-compose.yml`, `otel-collector-config.yaml` deletion, and the iac `apprunner.tf`/`ec2.tf`/`lambda.tf`/`variables.tf`/`*_ec2_setup.sh` diffs are byte-identical to the inherited baseline.

## 9. Review triage (phase-level)

| Likely finding | Triage |
|---|---|
| Dark panels/rules outnumber live ones on the LLM views | By design (owner-ordered sequencing): authored against spec §6.3 names so Stream L lights them without a dashboard change; D6 makes darkness self-documenting and lint-enforced |
| Thresholds are defaults, not SLOs | Ruling 19 pattern: defaults listed in Open questions for owner tuning; changing a threshold is a one-line rule edit |
| `AutomationRunErrors` is log-derived | Transitional proxy, labelled; the counter emitter is a recorded Stream L hand-off |
| VERSIONS.md row uncommitted while its pin test is committed | D8; working-tree-consistent, listed in the ledger |
| Doc-hub failure alert absent | No emitter exists; refusing to invent a metric name is the §11a-consistent choice — R.2 catalogue names it, then it's a one-rule addition |

## 10. Open questions for the owner

1. **CloudWatch alarm dialect (blocks T12's successor):** raise `hashicorp/aws` past 5.100.0 for PromQL alarms, add the `awscc` provider (also replaces the Transaction Search manual toggle), or defer aws alerting to a later batch? (B1c evidence: `aws_cloudwatch_metric_alarm` in 5.100.0 has no PromQL field.)
2. **Alert thresholds defaulted by this plan:** API 5xx 5%/10m, p95 5 s/15m, tenant daily spend $50 (flat, per tenant), browser errors 30/15m, Web Vitals poor-tier cut-offs (LCP 4 s, INP 500 ms, CLS 0.25), worker-silent 15m. Confirm or retune; per-tenant budget overrides need a budget source (env-templated rules or a future budget series) — say which.
3. **Slack/email targets (ruling 19):** supply the webhook (as a file path via `ALERTMANAGER_SLACK_WEBHOOK_FILE`, and the SSM SecureString name for aws), the SMTP smarthost + credentials, and the recipient list; the rollout checklist is in `oss-profile.md`.
4. **PromQL metric-widget schema probe:** export one Query Studio PromQL widget's JSON from the CloudWatch console so T10's bodies can be upgraded from text-widget pointers to live widgets (pairs with owner-owed B1b/B1d).
5. **Stream L hand-off to ratify:** doc-hub processing failures and automation late/failed runs need counters at their write sites (naming via R.2) before their §9.4 alerts can be authored portably.

## 11. Implementation notes

### T12 (no files — verification only)
The catalogue's alarm translation table covers every §9.4 item: API 5xx / p95 / turn-failure /
unpriced / tenant-spend / ledger-failures / collector exporter+queue (+ a receiver-refusals extra
row) / doc-hub processing failures (no-emitter row) / automation late-failed (proxy + counter
gate) / browser errors / three Web Vitals rows, plus the B1d SLO row — each naming its gate
(PromQL-alarm ruling / B1b / B1d / No emitter). `rg "aws_cloudwatch_metric_alarm|aws_applicationsignals"`
over `iac-obs/*.tf` returns nothing. The three-way ruling request was already §10.1 from
planning; nothing new to add. `aws-profile.md` (T8) carries the gate status prose.

### T11 (iac-obs commit `44fc0db`)
Both files authored; fmt/`init -backend=false`/validate green (`hashicorp/archive` v2.8.0
resolved implicitly at init — no `main.tf` edit needed; the lock file is gitignored) and
`py_compile` clean. Both variables declared in `alerting.tf` itself. Graph reading with defaults:
every Slack-path resource shares the one `count` gate, the email subscription iterates the empty
list → only `aws_sns_topic.observability_alerts` materialises, as the acceptance requires. The
role is hand-rolled least-privilege (logs:CreateLogStream/PutLogEvents on the pre-created group +
`ssm:GetParameter` on the one parameter — deliberately NOT the repo's shared `lambda_exec` role,
which carries S3FullAccess). Logging coverage VERIFIED for `sns_to_slack.py`: structured JSON
lines at received/webhook_loaded/posted/failed with alarm name + status, exceptions re-raised
after logging (SNS retries apply), reason truncated to 500 chars, webhook URL and full payload
never logged. Reported edit: `README.md` phase-6 owner-step section.

### Fix pass after adversarial review (obs-infra `62792306`+`b147798a`, iac-obs `eeb2b2b`)
Verdict was NOT MERGE-READY with one P1: the committed tree's `rules-validate` CI was
deterministically red — `alertmanager.yml` committed while its VERSIONS.md pin row was an
uncommitted edit, so `validate-rules.sh` died "no pin" on a `git archive HEAD` export.
Session-lead RULING applied: VERSIONS.md is branch-created (Stream I's A1), not pre-existing —
the row is now committed (`62792306`) and `git show HEAD:...VERSIONS.md` carries the pin; the
script's missing-pin failure stays loud. P2s: the layout guard now reads the promtool pin from
VERSIONS.md (`_versions_md_pin` — one drift seam with the amtool test and the script);
`AutomationRunErrors` matches `(?i)(error|critical|fatal)` (alerts.md wording updated);
`platform-health.json` gives the lines/s and spans/s targets `cps` via byName overrides (`Bps`
stays for the bytes defaults); the six tftpl bodies gained a committed mechanical guard —
`iac-obs/scripts/validate_dashboards.sh` (dummy-substitute + JSON-parse + widget-shape check,
chosen over a sibling-repo pytest because `sibling_repo("iac")` under a worktree resolves to
the MAIN checkout and would silently skip until merge), wired into the README validate steps;
the `var.log_retention_days` hand-carry is recorded in §8 and the iac README merge note.
Re-validation: guard lane 63 passed with `OTEL_RULES_CHECK=1`; `validate-rules.sh` all green;
`validate_dashboards.sh` all six parse.

### T13 (phase close)
Full lane 70 passed (both compose smokes + promtool/amtool env-gated checks); `terraform
validate` green; all six CloudWatch bodies JSON-parse after variable substitution (T13
self-check). Dark-panel census — service-overview 0/7, dependencies 0/5, llm-agents 10/12
(the two Postgres exact-spend panels are live), agent-turn-explorer 3/3, frontend 6/8 (the two
product_events panels are live), platform-health 1/11; dark rules 4/10 Prometheus + 4/5 Loki
(AutomationRunErrors is a transitional proxy, not dark). Master §15 entry written. DEVIATION:
the master §12 adversarial-review subagent could not be spawned (session brief forbids
subagents) — recorded as owed in T13's checkbox; the known Future-Improvement candidates
(node-exporter/disk panels, Grafana unified alerting second lane, per-tenant budget series)
stand untriaged for that review. `product_events`/`automation_runs.late_run|queue_seconds`
columns could not be re-verified in this worktree (they land with Stream P/the automations
substrate in `core`) — used exactly as §2.3 contracts them; `automation_runs` core columns and
`llm_usage`/`llm_model_calls`/`document_hub_documents` were re-verified from table definitions.

### T10 (iac-obs commit `0acbf10`)
Six bodies authored per the catalogue's aws column; `terraform fmt -check` clean on the new
file, `init -backend=false` + `validate` green (validate renders all six `templatefile` calls).
Log groups by resource (`aws_cloudwatch_log_group.otel` / `.apprunner_application`); no new
input variables were needed (`var.aws_region` pre-exists), so nothing beyond
`cloudwatch_dashboards.tf` declares anything. Every Logs Insights query carries the
`# RE-VERIFY after probe B1b` flag inline. One deliberate D7 extension, recorded: the
Bedrock-throttle panel is a CLASSIC `metric` widget on the native `AWS/Bedrock` namespace —
classic metric widgets have a documented stable schema; only the PromQL metric-widget schema is
unprobed (open question 4), and the T1 catalogue already committed this panel to the classic
form. Logging coverage: n/a.

### T9 (commit `394e0d89` — test edit only; deletions uncommitted per D8)
Grep found references only in the files T9 itself edits (three compose mounts, the legacy
provider) plus a comment in the T4 smoke override (refreshed). Eight legacy JSONs +
`test-observability.py` deleted in the working tree; legacy provider block and the three
`grafana/dashboards` mounts dropped; README rewritten for the new layout (services list gains
Alertmanager, config-file list gains the rules/alertmanager/CATALOGUE pieces, port list gains
9093). One regression the lane re-run caught, fixed as a committed test edit: the A-stream guard
`test_prometheus_scrapes_self_and_collector_telemetry_only` pinned the scrape set to exactly
self+collector, which T3's loki/tempo jobs legitimately extend — renamed to
`test_prometheus_scrape_set_is_the_observability_plane_only` with the four-target set (still a
closed set, so a stray app-scrape still fails). Lane 61 passed / 2 skipped; Grafana smoke 2
passed against the single-provider layout. Logging coverage: n/a.

### T8 (commit `3b9e1069`)
Anchor + no-TBD checks red first (2 failed), then 11 passed. All fifteen alerts have stubs
(meaning / first checks / dashboard panel / known causes / escalation; DARK alerts name their
arming condition; `AutomationRunErrors` documented as the transitional proxy with its Stream L /
R.2 replacement). `oss-profile.md` carries the rollout checklist with the two
`ALERTMANAGER_*_FILE` env vars and the amtool re-check; `aws-profile.md` carries the owner-owed
B1b/B1d/Transaction-Search/SSM steps with the exact commands (cross-checked against the
iac-obs README's Observability section) and the B1c gate status. Logging coverage: n/a.

### T7 (commit `f12d3c0b`)
Guard extended (4 new tests red first), then 9 passed. Rule file authored with the five alerts;
`loki-config.yaml` gained the D4 ruler block with `rule_path: /loki/rules-temp` (the ruler's
WRITABLE scratch dir — the guard asserts it differs from the read-only mount, a detail D4 left
implicit); three stacks mount `rules/loki` at `/loki/rules:ro`. Boot check: Loki 3.7.7 came up
clean and `/prometheus/api/v1/rules` (with `X-Scope-OrgID: flynapse`) listed `flynapse-browser`
with all five alerts. Two shading decisions recorded: `AutomationRunErrors` carries a
TRANSITIONAL-proxy description, not a Stream F dark note (worker logs are live at deploy; only
the four `browser.*` rules are DARK-F — the T7 table's "all DARK" header over-generalised), and
its severity filter matches OTLP structured metadata `severity_text` case-insensitively.
Logging coverage: n/a. Reported edits: `loki-config.yaml`, three compose stacks (loki rules
mount).

### T6 (commit `bee5fbbd`)
Pin re-verified at task time: `v0.34.0` is STILL the latest stable (GitHub latest release,
2026-08-16, prerelease false; Docker Hub tag pulled by the amtool run) — the plan's value stands.
Guard red (4 failed) → 5 passed with `OTEL_RULES_CHECK=1` (amtool exit 0, placeholders mounted
exactly as compose mounts them). One correction against my first draft, caught by the guard's red
run: `auth_password_file` (and smarthost/from/username placeholders) belong INSIDE
`email_configs`, not in `global` — the interface table's shape is enforced verbatim. Boot check:
Prometheus `/api/v1/alertmanagers` shows `http://alertmanager:9093/api/v2/alerts` active, all 10
rules load (flynapse-agent 4 / api 2 / platform 4), and an amtool-fired `SyntheticT6Check`
reads back `active` from `/api/v2/alerts`. Test edits: pin table + 9093 added to `ADMIN_PORTS`.
Logging coverage: n/a beyond `validate-rules.sh`. Reported edits: three compose stacks
(alertmanager service), `VERSIONS.md` (row + changelog).

### T5 (commit `2808d536`)
Guard red first (5 failed), then 6 passed WITH `OTEL_RULES_CHECK=1` — promtool (pinned image)
accepted all three files. `validate-rules.sh` green (promtool OK ×3; loud SKIP lines for
`alertmanager.yml`/Loki rules, which land at T6/T7 — the script resolves the alertmanager pin
lazily so it cannot die before T6 adds the VERSIONS.md row). Deviations/decisions:
- The otelcol expressions use the T3-verified SUFFIXLESS spellings (`otelcol_exporter_send_failed_spans`
  etc.), not §2.1's `_total` forms.
- `AgentTurnFailureRatioHigh` assumes the error outcome is spelled `agent_outcome="error"` — the
  §6.3 label vocabulary lands with Stream L; noted for the Stream L hand-off to confirm.
- The T5 guard checks the runbook annotation FORMAT only (`docs/runbooks/observability/alerts.md#<lowercase-name>`);
  file-existence + anchor checks land with T8, else T5 could never be green (the plan's
  "file exists" phrasing is unsatisfiable before T8 creates the file).
- The script reads image pins out of `VERSIONS.md` (awk over the table) instead of hardcoding —
  drift-free against the pin guard.
Logging coverage: `validate-rules.sh` reviewed — `set -euo pipefail`, one OK line per file, FAIL
lines name the file, explicit loud SKIPs, no `|| true`. Reported edits: `prometheus.yml`
(rule_files glob + alerting block), three compose stacks (rules mount, ro).

### T4 (commit `b704c68c`)
Override boots ONLY grafana (project `flynapse-grafana-smoke`, loopback 13000, tmpfs
`/var/lib/grafana` mode 0777 for uid 472, `depends_on` cleared, project-scoped network — the A8
override's posture). The legacy `/var/lib/grafana/dashboards` mount is deliberately absent from
the override (the legacy provider logs a missing path and carries on; T9 removes it). Smoke went
GREEN on the first full boot (2 passed, 53s) — no provisioning fix-ups were needed, so the
planned red phase never materialised; the test asserts titles read from the provisioned JSONs
(rename-following) and the four datasource uids (proving env interpolation parsed cold).
Logging coverage: n/a.

### T3 (commit `0e0c0666`)
Five views authored; guard flipped to all-six (red with one file first, then 9 passed). The boot
probe ran against `deployment/docker-compose.yml` + the A8 smoke override rather than the bare
observe stack — the observe stack's host bind-mount data dirs are created root-owned and all three
non-root backends crash-loop on `permission denied` (pre-existing property; the smoke override's
tmpfs exists for exactly this). Probe findings, all pinned in the JSON and catalogue:
- All four scrape targets up (`prometheus`, `otel-collector`, `loki`, `tempo`).
- A client span with `db.system`/`server.address` produced `traces_spanmetrics_calls_total{db_system="postgresql", server_address="postgres", span_kind="SPAN_KIND_CLIENT"}` — the T3 `tempo.yaml` dimensions work.
- **DEVIATION from §2.1 ground truth:** collector 0.160.0's internal Prometheus reader exports
  self-telemetry WITHOUT the `_total` suffix: `otelcol_receiver_accepted_{spans,metric_points,log_records}`,
  `otelcol_receiver_refused_*`, `otelcol_receiver_failed_*`, `otelcol_exporter_sent_*` — all
  verified live. `otelcol_exporter_send_failed_*` was absent (lazily created on first failure);
  its suffixless spelling is taken from the verified family pattern, noted in the panel
  description. T5's rules use the suffixless spellings.
- Loki ingest: `loki_distributor_bytes_received_total` + `loki_distributor_lines_received_total`
  (lazily created — appeared only after the probe pushed a log). Tempo ingest:
  `tempo_distributor_bytes_received_total` + `tempo_distributor_spans_received_total`.
  `prometheus_tsdb_head_series` confirmed. `target_info{job="flynapse/api"}` shape confirmed.
- `traces_service_graph_request_failed_total` (named in §2.1) was NOT present on the live probe
  (also lazily created); no panel uses it.
Test edit in the same commit: `_target_query_text` treats a Tempo `queryType: serviceMap` target
as non-empty (its filter is `serviceMapQuery`). Logging coverage: n/a. Reported edits:
`tempo.yaml` (span_metrics dimensions), `prometheus.yml` (loki/tempo scrape jobs).

### T2 (commit `661a0dea`)
Guard test red first (3 failures: no dir, undeclared datasource uids, no provider), then green (8
passed) after the D1 provider block, the Tempo `uid: tempo` + `flynapse-postgres` datasource, the
three stacks' env passthrough and `service-overview.json` (7 panels per plan). The all-six-uids
check is deliberately absent until T3, per the plan. Deviation of note: the POC stack has NO
postgres service (the api uses an external DB) — the compose comment there says the box env must
set `POSTGRES_DATASOURCE_HOST`; same accepted-unhealthy posture as the standalone stack. The
pytest command additionally needs `POSTGRES_DB=copilot_mro_test` (repo-wide db_guard, pre-dating
this phase). All three stacks re-parse under `docker compose config`. Logging coverage: n/a.
Reported edits: `dashboards.yml`, `datasources.yml`, three compose files.

### T1 (commit `1ec25b9c`)
Catalogue written with the six views, per-panel dark markers, oss/aws query notes and the alarm
translation table (11 §9.4 items + a receiver-refusals extra row + the B1d SLO row). Alertmanager
latest stable re-verified at task time: still `v0.34.0` (GitHub release 2026-08-16, prerelease
false; Docker Hub tag present) — the plan's pin stands. No deviations. Logging coverage: n/a (no
scripts).

## 12. Lessons

_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule for next time)_

- **Commit-split coherence beats rule literalism.** I treated VERSIONS.md as "pre-existing →
  never commit" while committing `alertmanager.yml` and the pin tests that depend on its row —
  leaving the COMMITTED tree deterministically red in CI. Corrected by session-lead ruling: a
  file CREATED by the same branch is not "pre-existing"; and before closing a task, check what a
  `git archive HEAD` export would do — every committed artefact's hard dependencies must be
  committed with it.
- **One drift seam per pinned value.** I hard-coded the promtool image in one test while two
  sibling checks read VERSIONS.md. When a pin has a single source of truth, every consumer reads
  it — never re-spell it, even as a test constant.
- **Hand-checks become guards before phase close.** The six tftpl bodies were only
  human-verified JSON until the reviewer flagged it; anything that would otherwise fail only at
  an owner-run apply deserves a committed mechanical check in the same phase.
