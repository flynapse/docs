# Observability, telemetry and logging rebuild — design (2026-09-05)

Status: **RULED 2026-09-05 (revision 3).** Nothing in this document is implemented. The owner ruled on the
§11 decisions the same day; §11 now records the rulings, and the sections below were updated to match.
Open: the LLM content-capture policy (§6.5) is deferred by the owner and stays a placeholder.
Revision 2 (same day): triaged an adversarial review — nine P1 findings fixed inline (Amplify SSR reach,
botocore double-count, mounted sub-app routes, loguru bridge, CLI delta metrics in `oss`, CLI metric
cardinality, RLS on reporting reads, operator-scope ruling, PromQL alarms in Terraform) and the P2 notes folded
into §3–§9 and §12.

Companion documents (all under `docs/`):
- `plans/observability-rebuild-audit.md` — current-state audit (2026-09-04), gaps G1–G17.
- `plans/observability-rebuild-research/01-…` — adversarial verification of the audit + backend inventory; adds gaps G18–G34.
- `…/02-…` — frontend telemetry, product-analytics contract, deployment wiring; adds 12 frontend/deploy findings.
- `…/03-…` — Postgres product-data inventory; the 10 panels mapped to tables; 22 ranked candidate views.
- `…/04-…` — managed backends (AWS, Azure, Grafana Cloud, New Relic, Datadog, Honeycomb) and the portability layer.
- `…/05-…` — LLM/agent observability: GenAI semconv, platforms, AWS GenAI observability, cost attribution.
- `…/06-…` — Claude Agent SDK built-in telemetry facts.

---

## 1. Problem statement

The estate has a telemetry *shape* (OTel SDK bootstrap, a collector, Loki/Prometheus/Tempo/Grafana on one
EC2 box, a Loki-backed product analytics page) but almost none of it carries real signal:

- **Product**: the customer-facing settings dashboard runs LogQL against a Loki whose address is set by no
  deployment artifact (G29) — every panel fails in POC, demo and AWS dev; two panels are dead by design (G1, G7);
  the panel that shows tokens is blind to the Claude Agent SDK loop, the majority of spend (G8).
- **Backend**: no auto-instrumentation and no outbound trace propagation (G4, G5), so traces are eight
  hand-rolled spans with nothing underneath; metrics have per-request cardinality and wrong instrument kinds
  (G19–G21); the LangGraph runtime emits no spans, no metrics and no cost-ledger row (G26); stdlib logging is
  never bridged, so whole subsystems never reach the log store (G22); `RuntimeTelemetry`, the agent metrics
  layer, is written and unwired (G9).
- **Frontend**: ~1,650 lines of telemetry code whose delivery is commented out (G1); browser OTel exports to the
  user's own localhost on Amplify (G2); "our team has been notified" is false.
- **LLM**: the two Postgres ledgers (`llm_usage`, `llm_model_calls`) are complete and correct but have no
  consumer except the automation budget gate; there is no USD metric anywhere; prompt text is shipped to an
  unauthenticated Loki with unlimited retention on a public-subnet box (G18, G31).
- **Operations**: no alerts, no SLOs, no readiness probes, `:latest` images everywhere, collector in debug mode,
  Grafana `admin/admin`, metrics endpoint ungated in production (G17, G28, G30).

The owner's constraints:
1. **POC**: the whole stack must still run as OSS containers on one EC2 box with no extra client infrastructure.
2. **Production**: no self-managed Loki/Prometheus/Tempo; use the client cloud's native/managed backend.
3. **Application code must not change when the backend changes.**
4. The product settings dashboard must read from a backend **datastore**, not the log store, and gain views.

## 2. Goals and non-goals

**Goals**
- One instrumentation contract in every service and the browser, backend-agnostic by construction.
- A collector "profile" per backend, selected by deployment, that is the only thing that changes.
- Real traces (request → DB/Redis/Weaviate/S3/Bedrock → agent turn → tool → subagent), real RED metrics,
  structured JSON logs with trace correlation, in every environment.
- LLM/agent observability: cost, tokens, latency, outcomes and tool usage as first-class telemetry, keyed to
  the ledger, with a deliberate prompt-content policy.
- Product analytics decoupled from observability: Postgres read API, new fact tables where facts are missing,
  a rebuilt settings dashboard with client-relevant views.
- Alerts and dashboards as code, portable where the backend allows.
- Fix the security and hygiene defects found by the audit and research.

**Non-goals**
- Building an evaluation/annotation platform for prompts (an optional add-on, §6.5).
- Billing tenants from telemetry (the ledger is the system of record; the bill reconciles in Cost Explorer).
- Multi-region or HA for the telemetry backend (managed backends provide it; the POC box is single-node by design).
- Rewriting `shift-optimizer`, `telegram-bot`, `lambdas`, `llm-platform` telemetry in the first pass (they get
  the shared contract when they next change; see §10).

## 3. Architecture

### 3.1 The invariant: OTel everywhere, one gateway collector, profiles behind it

```
                    ┌──────────────────────────── application tier (never knows the backend) ─────────────────────────┐
 browser ──OTLP/HTTP──► api gateway /telemetry/v1/*  ──┐
 (dashboard)          (auth, size/rate limit,         │
                       identity headers, pass-through)│
 Next.js SSR — not in v1 (Amplify WEB_COMPUTE has no  │
   VPC egress; see §12 probe)                         │
 api / core / copilot-mro / shift-optimizer ──────────┤      OTLP/HTTP-protobuf, standard OTEL_* env
 automations worker ─────────────────────────────────┤
 Claude Code CLI (Agent SDK subprocess) ─────────────┤      (built-in telemetry, env-configured)
 lambdas / telegram-bot (later) ─────────────────────┘
                                                      ▼
                                   ┌──────────── gateway collector (one per environment) ────────────┐
                                   │ base.yaml: otlp receiver · memory_limiter · resourcedetection ·  │
                                   │ attributes/transform (identity, env) · redaction · filter · batch │
                                   ├──────────────────────── profile overlay ──────────────────────────┤
                                   │ backend-oss.yaml   → Loki /otlp · Tempo · Prometheus (remote-write)│
                                   │ backend-aws.yaml   → CloudWatch Logs OTLP · X-Ray OTLP · CW Metrics│
                                   │                      OTLP, all via sigv4auth (instance/task role) │
                                   │ backend-azure.yaml → Azure Monitor OTLP (otlphttp + azure_auth,   │
                                   │                      cumulativetodelta)  [designed, built on demand]│
                                   └───────────────────────────────────────────────────────────────────┘
 Postgres (llm_usage · llm_model_calls · chat_turn_facts · product_events · llm_turn_content)
   ◄── ledger/fact writes from app code ──►  product analytics read API ──► settings dashboard (FE)
```

What never changes across backends (the contract):
- Wire: OTLP 1.x over HTTP/protobuf to `OTEL_EXPORTER_OTLP_ENDPOINT` (the gateway). gRPC is dropped:
  CloudWatch and Azure endpoints are HTTP-only and the browser can only do HTTP.
- Configuration: the standard OTel SDK env set only — `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`,
  `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`,
  `OTEL_TRACES_SAMPLER(_ARG)`, `OTEL_PYTHON_EXCLUDED_URLS`. The `utils.config` indirection (`OTEL_ENDPOINT`,
  `OTEL_ENABLED`, `OTEL_ENV`, `OTEL_VERSION`) is deleted (fixes G13, G14).
- Resource identity: `service.namespace=flynapse`, `service.name` (one per deployable — `api`, `automation-worker`,
  `dashboard`, `dashboard-ssr`, `claude-code`, `telegram-bot`, …), `service.version`, `service.instance.id`,
  `deployment.environment.name`. Sub-apps mounted in the gateway share the gateway's identity and are
  distinguished by `http.route` prefix (fixes G12, G32).
- Semantic conventions: HTTP server/client, DB, GenAI (`gen_ai.*`), log-record attributes `tenant.id`,
  `enduser.id`, `session.id`, `request.id`. W3C `tracecontext` propagation inbound **and** outbound; `baggage`
  is **not** propagated outbound (tenant/user identity must not leak to Bedrock, Azure, NOTAM/weather hosts).
- Collector front half (receivers, processors) identical everywhere; only exporters, auth extensions and the
  `service:` block differ per profile. The gateway has a stable private DNS name per environment so
  `OTEL_EXPORTER_OTLP_ENDPOINT` never changes when the collector moves hosts.

What changes per backend and is planned as work, not config: query language, dashboards, alert rules, and
where humans look (§9).

### 3.2 Deployment profiles

| Profile | Where | Collector runs as | Backend | UI |
|---|---|---|---|---|
| `oss` | local dev, **POC one-box**, offline/GPU boxes | container in the compose stack | Loki + Prometheus + Tempo (pinned images, auth on, retention set) | Grafana OSS (provisioned from repo JSON) + Grafana Postgres datasource for exact spend |
| `aws` | Flynapse dev/demo (App Runner + Amplify + Lambda) **and** client AWS production (ECS) | Flynapse's own account: the existing `weaviate_observability` EC2 keeps **only** the collector container (aws overlay) once Loki/Prom/Tempo/Grafana are removed — no new cluster for one container. Client accounts: a Terraform module that runs the collector as a task on the client's ECS cluster (or one Fargate service where no cluster exists), private subnet, task role with the CloudWatch OTLP permissions | CloudWatch Logs OTLP, X-Ray OTLP with Transaction Search + Application Signals, CloudWatch OTel-metrics OTLP (PromQL; announced GA 2026-06 — confirmed by the §12 probe before IaC) | CloudWatch console; dashboards + alarms in Terraform; Amazon Managed Grafana optional per client (§9.3) |
| `azure` | a future Azure client | container app / VM | Azure Monitor OTLP (App Insights with OTLP on; Log Analytics KQL; Azure Monitor workspace PromQL); `cumulativetodelta` in the overlay | portal "dashboards with Grafana" (free) + KQL | 

Rationale for `aws` in Flynapse's own account rather than Grafana Cloud: we ship the `aws` overlay to
clients, so we must run it ourselves. Grafana Cloud is the only managed backend where the OSS dashboards port
1:1 (research 04 §3) and remains the documented fallback if the team prefers one dialect; it is not part of
the plan. New Relic / Honeycomb are config-only swaps if a client mandates them; Datadog is not.

The shared `weaviate_observability` EC2 stops hosting telemetry once `aws` lands. It keeps Weaviate only
(and moves to a private subnet as a separate item, out of scope here).

### 3.3 Signal-by-signal design

**Traces.** Root spans come from the FastAPI/ASGI instrumentor with a templated `http.route` (fixes G20's
span-name cardinality). The gateway mounts `core`, `copilot-mro` and `shift-optimizer` as sub-apps, and the
instrumentor resolves a mounted request to the `Mount` prefix, not the sub-app route — so **each sub-app is
instrumented with its own `instrument_app`** and the gateway's instrumentor excludes the mount prefixes, giving
exactly one SERVER span per request with `http.route = <mount prefix> + <sub-app route>` (asserted by the
in-process smoke). Requests rejected by gateway middleware before routing (401/403) produce a counter, not a
span. Client spans from `httpx`/`requests`/`psycopg2`/`redis` instrumentors. `botocore` is **not**
instrumented: its Bedrock extension would emit a second `gen_ai.*` span/histogram for every LangGraph
Converse call beside the ledger-driven ones (§6.3); S3 calls get a thin wrapper span in `utils/s3_service`
instead. Weaviate has no upstream instrumentor: a wrapper on the **connection factory** (`weaviate_connection()`,
which the RAG retrieval path uses — not only `utils/weaviate_service`) adds `db.system=weaviate` spans. Agent
turns and tools are `invoke_agent`/`execute_tool` spans (§6.2). Background work (automations worker,
document-hub processing, improvement loop) opens its own root span with `tenant.id` and links to the
scheduling run. Sampling: `parentbased_traceidratio` 1.0 for server-side spans in `oss` and `aws` (CloudWatch
bills per GB and indexes 1%); browser fetch/XHR spans are head-sampled at 10% by default (vitals and errors
are never sampled). Health/metrics routes excluded.

**Metrics.** Auto-instrumentation supplies `http.server.request.duration` (replaces the hand-rolled HTTP
metrics with their session/user/path labels — fixes G19–G21). App metrics keep a small, documented set:
document-hub families (already good), ledger-driven `gen_ai.client.*` + `agent.*` families (§6.3),
`chat_block_save_failures_total`, memory latencies. Rules: no `session_id`/`user_id`/raw-path labels; numeric
values are never labels; units declared (`s`, `By`, `USD`, `{token}`) — dashboards are written against the
post-normalisation names from day one. `MetricsService` is replaced by direct OTel `Meter` use behind a tiny
registry so instrument kinds are explicit (a gauge is an observable gauge, not an up-down counter).

**Logs.** loguru stays as the API surface. Sinks become: (1) JSON to stdout (`serialize=True`) so any
stdout-scraping agent works (fixes G15); (2) an OTLP sink that is a ~15-line adapter over the OTel
`LoggingHandler`: it flattens loguru's `extra` into top-level log-record attributes (the stock handler would
nest them under one `extra` map), sets the record time from loguru's `record["time"]` (event time, not sink
time — fixes G24 without the monotonic bump), and lets the SDK attach trace/span ids; (3) a stdlib
`InterceptHandler` on the root logger **and** on `uvicorn.access`/`uvicorn.error` (they do not propagate),
with `opentelemetry.*` loggers excluded to avoid export-failure loops, so `logging.getLogger()` users
(data-discovery, improvement loop, botocore, httpx) flow through the same sinks (fixes G22). File sinks are
removed (G25). `setup_logging` is idempotent and explicit, not "skip if any handler exists" (G23). Bound
context: `tenant_id`, `user_id`, `session_id`, `request_id` at the gateway, plus `chat_id`/`block_id`/`department`
in the pipeline, plus the same fields on every background root (automations executor, doc-hub processing).
**No user content in log lines** — the `query=request.message` and memory-search `query=` fields are removed
(G18); a `redaction` processor in `base.yaml` is the second line of defence (allow-listed attribute keys;
email/token patterns masked). The `X-Trace-Id` response header is kept by a two-line middleware.

**Events (browser + product).** Browser telemetry is OTLP (JSON encoding from the web exporters): spans from
fetch/XHR/document-load instrumentation and OTel log records for Web Vitals (`event.name=browser.web_vital`),
errors (`browser.error`), and a curated product-event set (§7.4). They enter through the api gateway, which
authenticates, enforces size and per-user rate limits, stamps `X-Tenant-Id`/`X-User-Id`/`X-Session-Id` from
the verified identity, and forwards the body **opaque** to the collector — no OTLP decoding in Python. The
collector's dedicated `browser` pipeline copies the identity headers onto records (`include_metadata` +
`attributes from_context`) and applies the attribute allow-list and redaction. The browser never sees a
collector URL.

### 3.4 Why the browser goes through the api gateway, not a public collector or a Next.js route

Amplify WEB_COMPUTE has no VPC connectivity (research 04 §6 assumed otherwise; §12 probes it, but the design
does not depend on the answer), so a Next.js route handler cannot reach a private collector; the api already
has the VPC connector, the CORS allow-list for the dashboard origin, Cognito auth, tenant binding and a public
rate-limited ingest route (`core/resources/logging`). A public collector with a bearer token is security
theatre (the token is in the JS) and has no per-user rate limiting (there is no upstream rate-limit
processor). **Ruled:** the existing `core` ingest endpoints are **evolved, not replaced** — `POST
/logging/ingest` (authenticated; Cognito token as today's API calls) and `POST /logging/public/ingest`
(anonymous, 64 KiB / 50 records / 60 rpm per IP, tenant sentinel) keep their paths, auth, quarantine rules and
rate limits, and change their body to standard OTLP (`/v1/logs` and `/v1/traces` sub-paths) passed through
opaquely to the collector with the identity headers. The loguru re-logging path inside them is removed. The
routes are excluded from the api's own request metrics; the test that pins "exactly three logging routes" is
re-banked for the new sub-paths. Next.js SSR (route-handler) tracing is deferred: if the probe shows Amplify
can reach the api privately, SSR exports to the same route with a service credential in a later phase;
otherwise it stays out.

## 4. Backend telemetry foundation (Python)

Scope: `utils/` (the shared implementation), `api/`, `copilot-mro/`, `core/`, `shift-optimizer` (inherits),
automations worker.

- Pin `opentelemetry-sdk==1.44.0`, `opentelemetry-exporter-otlp-proto-http==1.44.0` (the gRPC exporter is
  what is installed today), contrib `==0.65b0` across the shared `api` env; add `-fastapi`, `-asgi`, `-httpx`,
  `-requests`, `-urllib3`, `-psycopg2`, `-redis`, `-logging`, `-threading` (no `-botocore`, §3.3). No
  `opentelemetry-distro`/`opentelemetry-instrument` CLI: bootstrap stays programmatic in one function
  `utils.observability.bootstrap(service_name)` driven purely by `OTEL_*` env, called once per process
  (gateway, worker, standalone copilot-mro, parser `__main__`s) and **before** `PostgresService` builds its
  connection pool (the pool is created at import today; instrumenting after it leaves pooled connections
  un-instrumented — a test asserts one pooled query produces a `db.*` span).
- Sub-app instrumentation as in §3.3: `instrument_app` on `core`, `copilot-mro`, `shift-optimizer` and the
  gateway, with the mount prefixes in the gateway's `excluded_urls`.
- **Signal catalogue first.** Phase 1 opens with a backend signal catalogue (the server-side twin of the
  frontend event catalogue in research 07): per service and subsystem, every span (name, kind, attributes,
  parent) and every metric (name, kind, unit, attributes, cardinality bound), each mapped to the dashboard or
  alert that consumes it, diffed against the current inventory in research 01 §2.1–2.2. Owner reviews it before
  instrumentation lands, so "more metrics and traces" is a deliberate, enumerated list rather than ad-hoc
  additions. Families already named by this spec: HTTP server/client, DB/Redis/Weaviate/S3 clients, agent turn
  / tool / subagent, model usage and cost, document-hub processing, memory, automations worker, ledger writes,
  ingest/telemetry pipeline health.
- Parser/ingest entrypoints (nine today, G32) all use `service.name=ingest-parser` with a `parser.kind`
  resource attribute; the six dead `document_hub_qna_*` metric constants are deleted.
- `utils/observability/{tracing,metrics}.py` shrink to thin helpers over the SDK: `get_tracer()`,
  `get_meter()`, `span(name, **attrs)`, a metric registry with explicit kinds/units. Singletons keyed on the
  process, not on the first caller (G27). `NoOp` behaviour comes from `OTEL_SDK_DISABLED=true`, not from
  bespoke classes.
- Outbound propagation: instrumentors inject `traceparent`; the automations executor and doc-hub processing
  create spans with `Link`s to the scheduling run; `asyncio.to_thread` stays the only thread hop (documented,
  with a test that `run_in_executor` is not used on the pipeline path).
- Health: `/health/live` (process up) and `/health/ready` (dependencies) on the gateway; the copilot-mro
  aggregate probe becomes the ready probe's body; the `debug` leak is removed (G28). Metrics scrape route and
  `prometheus_client` are deleted (G3, G30) — metrics are push-only via OTLP.
- Tests: unit tests for bootstrap idempotence, resource attributes, log bridge (JSON shape, trace correlation,
  stdlib intercept), redaction allow-list, cardinality guard (a test that asserts no metric attribute is named
  `session_id`/`user_id`/`path`), and an in-process smoke that a request produces server span → client span →
  correlated log through an in-memory exporter.

## 5. Collector profiles and infrastructure

- `deployment/otel/base.yaml` + `deployment/otel/backend-{oss,aws,azure}.yaml`; the collector image is
  `otel/opentelemetry-collector-contrib:<pinned>`; overlays restate the whole `service:` block (confmap
  replaces lists). One env file per environment supplies endpoints, region, log-group names, secrets.
- `oss`: Loki with `auth_enabled` and a retention period, Prometheus fed by the collector's
  `prometheusremotewrite` exporter (the `prometheus` scrape-exporter indirection goes; `job` =
  `service.namespace/service.name` is the per-service label dashboards use — G21), with a `deltatocumulative`
  processor in the overlay because the Claude Code CLI exports delta sums (§6.4) and remote-write drops them;
  Tempo with block retention; Grafana with a provisioned admin secret and dashboards/alert rules from the repo,
  plus a Postgres datasource using the reporting role (§7.2). POC retention defaults: logs 14 d, spans 3 d,
  metrics 30 d — the box currently shares a 30 GB root with Weaviate, so the `oss` profile requires its own
  ≥100 GB data volume and the retention knobs are env-driven. Ports bound to loopback or the compose network
  except OTLP from the api container. Health checks per container. All images pinned. The README's Jaeger
  references are removed.
- `aws` (Terraform module `otel-gateway`): collector task + role; `sigv4auth` ×3; log groups per service with
  retention (including the Lambda and App Runner service logs that auto-create never-expiring groups today);
  Transaction Search enabled; WAF logging to a log group; CloudWatch dashboards + alarms + SNS topic; App Runner
  and Lambda `OTEL_EXPORTER_OTLP_ENDPOINT` re-pointed at the gateway's private DNS name; the
  `weaviate_observability` box loses Loki/Prometheus/Tempo/Grafana and its public telemetry ports and keeps the
  collector (aws overlay) until Weaviate itself is re-homed. Metric alarms on OTLP-ingested metrics need PromQL
  alarms; if the pinned AWS provider still lacks `alarm-promql` support, the fallback is the `awscc` (Cloud
  Control) provider or Application Signals SLO alarms for the RED alerts — decided by the §12 probe.
- `azure`: overlay authored and validated against a throwaway App Insights resource once (probe), IaC written
  when a client needs it.
- Tests: config validation in CI (`otelcol validate` for every overlay), a compose smoke that sends one span,
  one metric and one log through `oss` and asserts they land; a Terraform plan check for `aws`.

## 6. LLM and agent observability

### 6.1 Principles
- **The ledger is the system of record for tokens and USD.** `llm_usage` / `llm_model_calls` keep their
  NULL-honest, `cost_complete`, `cost_source` semantics. Telemetry carries the same numbers as attributes and
  trend metrics; it never becomes an invoice.
- **One write site, three consumers.** The ledger sink (`record_turn_usage` / the `ModelUsage` sink) feeds
  Postgres, then the telemetry instruments, then (optionally) the content relation. No drift.
- **Structure to the telemetry backend, content to Postgres.** Prompt/completion bodies never ride OTLP.

### 6.2 Spans (both runtimes)
- Root `invoke_agent <runtime>` (INTERNAL): `gen_ai.operation.name=invoke_agent`, `gen_ai.provider.name`,
  `gen_ai.agent.name` (`claude` | `lang`), `gen_ai.request.model`, `gen_ai.conversation.id=<chat_id>`,
  `tenant.id`, `enduser.id`; on close `gen_ai.usage.{input,output}_tokens`,
  `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`, `agent.turns`,
  `agent.cache_hit_rate`, `agent.loop_error`, `error.type`, `agent.cost.{sdk,direct,embedding,combined}_usd`,
  `gen_ai.usage.cost` (= combined). Replaces `agent_sdk.run_query` + the unwired `agent.turn`.
- `execute_tool <name>` (INTERNAL): `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type=function`,
  `error.type`. Replaces `agent_sdk.tool.<name>`.
- Subagent runs: child `invoke_agent <subagent>` spans.
- LangGraph runtime: `opentelemetry-instrumentation-genai-langchain` (callback layer, `NO_CONTENT`) for
  chat/tool/chain spans under the same root. No botocore/anthropic/openai GenAI instrumentors anywhere — they
  would double-count the direct calls the ledger already prices and see nothing of the SDK loop.
- The Claude Code CLI's own beta spans stay off initially; its events already carry our trace ids because the
  SDK injects `TRACEPARENT`.

### 6.3 Metrics (from the ledger sink; `RuntimeTelemetry` wired and renamed)
- `gen_ai.client.operation.duration` (s) and `gen_ai.client.token.usage` ({token}) with
  `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `error.type`, `gen_ai.token.type`
  extended with `cache_read`, `cache_write`, `reasoning`, `tool_search_overhead`.
- `agent.model.calls`, `agent.model.cost_usd` (unit `{USD}` — a bare `USD` unit becomes
  `agent_model_cost_usd_USD_total` after Prometheus normalisation) **always paired with**
  `agent.model.unpriced_calls`; attributes `model.role/purpose/profile/cost_source/graph_node`,
  `agent.department`, `deployment.environment.name`, and `tenant.id` (tenant count is in the tens; revisit if
  it grows). Never `enduser.id` or `session.id` on any metric.
- `agent.turn.calls`, `agent.turn.duration_seconds` (`agent.outcome`), `agent.tool.calls`, `agent.tool.attempts`
  (`tool.name`, `tool.outcome`, `tool.error_code`), `agent.subagent.calls/duration_seconds`,
  `agent.ledger.write_failures` (`ledger`, `reason`) so ledger booking failures are alertable as a metric, not
  a log line.
- `utils/llm.py`'s `llm_*` families are retired once direct calls ride the same sink; `embedding_*` stay until
  embeddings do.

### 6.4 Claude Code CLI built-in telemetry
Turned on per call, in every environment, through `ClaudeAgentOptions(env=…)` in the orchestrator (and the
data-discovery SAD runner, which drives its own SDK loop): `CLAUDE_CODE_ENABLE_TELEMETRY=1`,
`OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, the gateway
endpoint, `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative` (the CLI defaults to delta; cumulative
is what Prometheus-style stores want, and the `azure` overlay converts back with `cumulativetodelta`),
`OTEL_METRICS_INCLUDE_SESSION_ID=false`, `OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false`,
`OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES=false` (so resource attributes do not become per-user metric labels),
`OTEL_RESOURCE_ATTRIBUTES=service.namespace=flynapse,service.name=claude-code,deployment.environment.name=…,
tenant.id=…,enduser.id=…,agent.department=…`, short export intervals (the CLI's exit flush is short; a
`query()` is one turn), `CLAUDE_CODE_OTEL_DIAG_STDERR=1` with the SDK stderr callback wired. The collector's
`base.yaml` promotes `tenant.id`, `agent.department` and `deployment.environment.name` from the resource onto
`claude_code.*` metric data points; `enduser.id` stays on events only. Gains: per-model-call
`claude_code.api_request` events (the grain the ledger lacks), `claude_code.token.usage` with cache buckets,
`claude_code.tool_result`, subagent attribution. All `OTEL_LOG_*` content flags stay unset outside dev. A
collector `transform` adds `gen_ai.*` aliases so GenAI-aware backends price these records.

### 6.5 Content capture policy and the (optional) LLM tool — **DEFERRED by the owner**
The owner will return to this decision. Until then: the G18 fix (no prompt text in logs) and the "structure
to telemetry, content to Postgres" principle stand; no `llm_turn_content` relation and no LLM tool are built;
`debug_dumps/` stays the dev-only capture. The proposal below is the placeholder for that decision.
- New tenant-scoped, RLS'd relation `llm_turn_content` keyed `(tenant_id, block_id[, call_id])`: redacted
  (`redact_sensitive`) prompt/completion/tool bodies or S3 object keys, `redaction_version`, `sha256`,
  `content_bytes`, `truncated`, `captured_at`; **off in production by default**, per-tenant opt-in, 30-day
  retention purge keyed on the same day bucket as spend. Written at the ledger write site. Replaces
  `debug_dumps/` for shared environments; developers use `OTEL_LOG_RAW_API_BODIES=file:<dir>` locally.
- No LLM platform in the base stack. If transcript review / evals are wanted in the POC, **Arize Phoenix**
  (one container, existing Postgres, ELv2) is the only one-box-friendly option; Langfuse needs ClickHouse and
  a 16 GiB box; LangSmith is banned by policy. Any such tool receives a sampled, redacted copy via OTLP from the
  same write site — it is a consumer, never the record.
- Bedrock model invocation logging stays off in production (account-wide, no tenant boundary).

### 6.6 Ledger completeness gaps (G26 and its sibling) — **DEFERRED by the owner**
The `lang` runtime writes no `llm_usage` row today, and the data-discovery SAD runner's usage goes to a
caller-supplied sink and stdlib logging only. Both are cost-ledger completeness defects; the owner ruled they
are **out of scope for this workstream** (a separate ledger workstream). Consequences recorded here so the
dashboards are honest: the spend views (§7.3) cover the Claude runtime, direct calls and automations; a
`lang`-served turn contributes no `llm_usage` row, and data-discovery spend is absent. The lang runtime still
gets spans and `RuntimeTelemetry` metrics through the ledger sink it already feeds (`llm_model_calls`), so its
telemetry is complete even though its per-turn ledger row is not. `improvement_runs.llm_spend` is likewise
treated as outside the tenant total until that workstream rules.

## 7. Product analytics (settings dashboard) rebuild

### 7.1 Read path
- New `core` module `analytics` with a **panel registry**: `panel_id → (SQL builder, aggregator, filters)`,
  executed through `PostgresService` under the request's bound tenancy (`app.tenant_id`/`app.operator_ids`
  GUCs), statement-timeout protected. Response envelope unchanged (`panel_id, range, last_updated,
  available_filters, data`) so the existing chart components are reused. Cache TTL and per-tenant rate limit
  kept. Errors are typed (rate-limited / unavailable / empty) so the UI can say which.
- Time ranges `1h/1d/1w/1m` plus `3m`; bucket by hour/day; empty buckets pre-seeded server-side as today.
- The Loki client, `LOKI_BASE_URL` and the LogQL constants are deleted from `core`.
- Money rule on every USD tile: `SUM(total_cost_usd)` always with `COUNT(*) FILTER (WHERE NOT cost_complete)`;
  never sum `automation_runs.cost_usd` and `llm_usage` together.
- Operator-scoped relations (`document_hub_documents`, `memory_items`) — **ruled**: bind the tenant's full
  operator list for **tenant owners only** (as the automations announcements path does); `view_dashboard`
  capability holders read entitlement-scoped and the tile says "for the operators you are entitled to". Counts
  are never cross-operator for a capability-only viewer.
- The panel registry lives in `core` (the owner of the product surface and of comments/automations/invitations
  tables) and reads the copilot-mro-owned ledger/chat tables through the shared `PostgresService`, as the
  automations executor already does across the same boundary.

### 7.2 Storage changes
- Indexes: `chat_blocks (tenant_id, block_timestamp)`, `chat_feedback (tenant_id, created_at)`,
  `comments (tenant_id, created_at)` (one line each in the definitions; the builder prefixes tenancy).
- `chat_turn_facts` projection table (tenant-scoped), one row per turn, minted from the pipeline result on the
  pre-minted `block_id` **in the same transaction as the block save** (no second failure mode; a turn that
  never persists a block has no facts row, and loop failures are therefore sourced from `llm_usage`, which
  books on failure, not from this table): `query_type`, `route`, `capability_outcome`, `answer_found`,
  `confidence`, `needs_clarification`, `latency_ms`, `tool_count`, `tool_failures`, `citation_count`,
  `cited_documents` (jsonb, small), `session_id`, `department`, `user_id`, `block_timestamp`. No question
  text: the "top questions" drill-down joins `chat_blocks` for the top-N rows only. Backfilled once from
  `block_data` by an owner-run script under the reporting role. This is the "one jsonb accessor investment"
  that unlocks quality, tools, intents and citations without detoasting `chat_blocks`.
- `product_events` table (tenant-scoped): `event_name` (allow-listed: `document_opened`, `document_closed`
  (dwell), `session_started`, `session_ended`), `occurred_at`, `user_id`, `department`, `session_id`,
  `document_id`, `document_kind` (`catalog` | `document_hub` | `upload`), `source_surface`
  (`chat_citation` | `library` | `viewer`), `page_number`, `dwell_ms`, `route`. The browser POSTs each event
  **once** to `POST {api}/analytics/events` (authenticated, typed, 50/batch), which writes the row and
  re-emits it as an OTLP log record for ops. Retention 13 months.
- **Reporting role — ruled: reuse `flynapse_readonly`.** The app role is `NOBYPASSRLS`, unbound sessions fail
  closed, and the ledgers are append-only for it. The cluster already has `flynapse_readonly`
  (`NOSUPERUSER BYPASSRLS`, SELECT only, no writes; today used only by the pytest corpus census, password in
  `POSTGRES_READONLY_PASSWORD`). It is granted SELECT on the app database's analytics relations and becomes the
  Grafana Postgres datasource and the `chat_turn_facts` backfill reader. Purges (`product_events`; content if
  ever built) stay owner-run scripts under `postgres`, as every maintenance script is today. No new role.
- Retention defaults for the ledgers stay "forever" (append-only by privilege); `llm_model_calls` gets a
  rollup-then-prune decision in the plan (owner question).

### 7.3 Views (tabbed; v1 set)
Existing panels rebuilt on Postgres: Top users by messages, Active users over time, Message volume,
**LLM tokens + cost** (from the ledger, all runtimes, per model filter, with unpriced-count footnote), Chat
duration histogram (from `chat_turn_facts`), **Query type distribution** (from `chat_turn_facts` — the panel
was dead only in its query), Feedback over time, Top commenters, Comments over time. "Most accessed documents"
returns as **Documents opened** on `product_events`.

New client-admin views (from research 03, tranches T1/T2):

| Tab | View | Source |
|---|---|---|
| Usage & adoption | WAU/MAU, new users, active users per department, retention cohort (first activity from `chat_blocks`) | chat cluster, `users`, `user_departments` |
| Usage & adoption | Sessions and session duration; documents opened, dwell, top documents by distinct users | `product_events` |
| Quality | Answered / unsure / not-answered rate and confidence trend; clarification rate | `chat_turn_facts` |
| Quality | Feedback rate + negative-feedback drill-down (question text, comment) | `chat_feedback` + `chat_blocks` |
| Quality | Top questions / intents, top **unanswered** intents; most-cited manuals/documents | `chat_turn_facts` |
| Cost | Spend by department / user / model / origin (chat vs automation), cache-hit savings (with lower-bound caveat) | `llm_usage`, `llm_model_calls` |
| Reliability | Turn error & loop-failure rate (`max_turns`/`max_budget`/outage), model-call outcomes, latency percentiles per model/binding and end-to-end | `llm_usage`, `llm_model_calls`, `chat_turn_facts` |
| Operations | Document Hub processing: ready / needs-attention / failure codes, throughput, attempts | `document_hub_documents`, `automation_runs(kind=document_hub_process)` |
| Operations | Automation runs: outcomes, late runs, spend vs `max_budget_usd`, tool usage mix and per-tool failures | `automation_runs`, `automations`, `chat_turn_facts` |

Deferred (designed, not in v1): an Admin tab (onboarding funnel from `tenant_invitations`, access-change audit
feed from `authorization_events`, notification read-rate), memory growth/usefulness, improvement-loop
transparency (product decision on client visibility), data-discovery and optimizer run health (per-product
tabs when those tenants exist).

### 7.4 Frontend telemetry rebuild
- OTel JS 2.x upgrade (Node ≥ 18.19 on the Amplify build image — §12 probe); browser `WebTracerProvider` +
  fetch/XHR/document-load instrumentations, fetch/XHR spans head-sampled at 10%;
  `propagateTraceHeaderCorsUrls` restricted to the API origin. SSR `instrumentation.ts` deferred (§3.4).
- A small OTLP/JSON exporter that posts through the existing authenticated fetch helper to the api telemetry
  route with a bounded queue and a best-effort `visibilitychange`/`pagehide` flush. **The re-queue wedge that
  caused the 2026-02 shutdown (a permanently rejected batch re-queued to the front forever) is designed out,
  not patched**: a 4xx response drops the batch and increments a `browser.telemetry.dropped` counter; 5xx and
  network failures retry with backoff up to a fixed attempt count, then drop; the queue has a hard cap with
  oldest-first eviction; a unit test replays the wedge scenario (one bad batch followed by good ones) and
  asserts the good ones ship. The old `logger.ts` queue and both commented-out delivery calls are deleted. **Accepted loss**: the
  final flush on unload cannot refresh a Cognito token, `sendBeacon` cannot carry the auth header, and
  keepalive bodies cap at 64 KiB — events in the last few seconds of a closing tab may be lost; nothing
  product-critical rides that path (`document_closed` dwell is best-effort).
- Replace the 24-event / 32-custom-metric logger with a **curated event catalogue** — ruled, with the
  owner's caveat that the dashboard has grown many pages and features since those events were written, so the
  catalogue is **scoped from a fresh inventory of the current app, not from the old list**. Phase 4 therefore
  starts with a page/feature inventory of `dashboard/app` and the feature components (chat per department,
  document viewer, Document Hub, automations, data discovery, optimizer/rostering, settings, memory,
  improvement) and produces an event catalogue (name, trigger, attributes, sampling, which product view or
  ops panel consumes it) that the owner reviews before implementation. Baseline members: Web Vitals (5),
  `browser.error` (boundary, window error, unhandled rejection, resource error), route timing
  (`route_change_ms`, `route_ready_ms`), API timing (from fetch spans, not custom metrics), PDF
  open/page-switch timings, login-to-ready, and the product events of §7.2 (`document_opened` from
  `DocumentCard`/viewer mount, `document_closed` with dwell, session start/end). Click-level
  `user_interaction`, `window_resize`, scroll milestones, memory polling are dropped. `session.id` = the
  `X-Session-ID` the API client already sends; `trace_id` from the active span. Research file 07 carries the
  inventory and the draft catalogue.
- `ErrorBoundary` reports only what is actually delivered. `logger.*` free-text calls become structured OTel log
  records with the same API (thin wrapper), sampled at `info` in production.
- The legacy `core` log-ingest routes and `LoggingProvider` delivery code are removed after cut-over.

## 8. Security and hygiene items folded in

| Item | Fix |
|---|---|
| G18 prompt text in logs | remove `query=` fields; redaction processor; test asserting no log record attribute named `query`/`message` on the chat path |
| G31 unauthenticated public Loki/Prometheus/OTLP | `oss` profile binds admin ports to loopback/compose network, Loki auth + retention; `aws` profile has no public telemetry ports; EC2 SG trimmed |
| G30 metrics scrape ungated | route deleted (push-only) |
| G17 collector debug, `admin/admin`, `:latest` | removed / secret-provisioned / pinned |
| G28 readiness | `/health/live`, `/health/ready` |
| G20 cardinality | instrumentor route templating; attribute lint test |
| Content flags | `OTEL_LOG_*`, `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` unset in shared envs; CI check on the env templates |

## 9. Dashboards, alerts, and Grafana's role

### 9.1 Is Grafana still needed?
- **`oss` profile: yes** — it is the only UI for Loki/Prometheus/Tempo and the POC's whole point.
- **`aws` profile: no** — CloudWatch's console (Logs Insights, Query Studio PromQL, Transaction Search,
  Application Signals service map/SLOs, alarms) covers the operational views; dashboards live in Terraform.
  Amazon Managed Grafana is an optional per-client add-on ($9/editor, $5/viewer per month) for teams that want
  Grafana UX; it does not make the OSS JSON reusable (data model differs), so it is a UX choice, not a
  portability one.
- Product views never depend on either: they are in the settings dashboard on Postgres.

### 9.2 The Grafana set for `oss` (replaces the eight current dashboards)
1. **Service overview** — RED per service and route from `http.server.request.duration`; in-flight; 5xx by
   route; p50/p95/p99; top slow routes. (Replaces backend/comments/authorization/document-viewer boards;
   the "test-cookie" board is dropped.)
2. **Dependencies** — client-span latency/error by `db.system`/`peer.service` (Postgres, Redis, Weaviate, S3,
   Bedrock); span-metrics service graph.
3. **LLM & agents** — token histograms and USD counter (+ unpriced) by model/provider/department/runtime;
   cache-hit ratio; turn outcomes; tool calls/failures; subagent counts; CLI `claude_code.*` metrics; Bedrock
   throttles (from CloudWatch in `aws`, absent in `oss`); **exact spend panel from the Postgres datasource**
   (reporting role, §7.2).
4. **Agent turn explorer** — first Tempo panels: slowest/failed `invoke_agent` turns (TraceQL), tool latency
   table, click-through to the waterfall.
5. **Frontend** — Web Vitals by route and rating, browser errors, route timings, API latency as seen from the
   browser, document-open events.
6. **Platform health** — collector/exporter health, log/span/metric ingest rates, ledger booking failures,
   doc-hub processing, automations worker heartbeat and late runs, Loki/Tempo/Prometheus storage.

### 9.3 CloudWatch equivalents (`aws`)
Same six views as hand-maintained Terraform `aws_cloudwatch_dashboard` bodies (Logs Insights + PromQL
widgets); Application Signals SLOs for API availability/latency and agent-turn success **if** the §12 probe
shows Application Signals populates from vanilla-SDK spans (the AWS distro is not an option under constraint
3); and the alarms below. The six-view catalogue (name, question, signals) is the shared spec; the two dialects
are maintained by hand — there is no generator.

### 9.4 Alerts (as Prometheus rule YAML; translated to CloudWatch alarms)
API 5xx ratio, p95 latency per route, agent turn failure ratio, `agent.model.unpriced_calls` > 0 sustained,
tenant daily spend vs budget, `agent.ledger.write_failures`, doc-hub processing failures, automation
late/failed runs, collector exporter failures/queue, browser error rate, Web Vitals p75 regressions.
**Ruled routing: Slack channel and email** — SNS → Slack webhook + SES/SNS email in `aws`; Alertmanager or
Grafana contact points (Slack webhook + SMTP) in `oss`. Channel names and recipients are plan-time inputs.

## 10. Phasing (outline; the implementation plan follows approval)

| Phase | Scope | Notes |
|---|---|---|
| 0 | Hygiene quick wins: drop prompt text from logs; collector debug off; pin images; Loki auth/retention; Tempo retention; metrics route gated/deleted | small, independent, ship first |
| 1 | Backend telemetry foundation (§4) in `utils` + `api` + `copilot-mro` + `core` + worker | backend-agnostic; largest code change |
| 2 | Collector profiles + IaC (§5): `oss` compose, `aws` Terraform, dev estate migrated, EC2 box de-scoped | can start in parallel with 1 |
| 3 | LLM/agent observability (§6) incl. CLI telemetry and the `gen_ai.*` rename; ledger fixes and content capture excluded (deferred) | depends on 1 |
| 4 | Frontend telemetry rebuild (§7.4): surface inventory + event catalogue (owner-reviewed) → OTel JS 2.x → OTLP ingest evolution on the existing `core` routes | depends on 1 for the ingress route; FE work independent |
| 5 | Product analytics rebuild (§7.1–7.3): storage, read API, FE settings dashboard | independent of 1–4; parallel worktree |
| 6 | Dashboards, alerts, runbooks for `oss` and `aws` (§9) | after 1–5 land |

Later services (`telegram-bot`, `lambdas`, `shift-optimizer` standalone, `llm-platform` vLLM scrape via the
collector's `prometheus` receiver) adopt the §3.1 contract when next touched. Azure profile on demand.

## 11. Rulings (owner, 2026-09-05)

| # | Decision | Ruling |
|---|---|---|
| 1 | Backends | **CloudWatch-native** for Flynapse's own estate and client AWS production; `azure` designed now, built when a client needs it; Grafana Cloud / New Relic not pursued. |
| 2 | Grafana's role | **OSS profile only**; CloudWatch console + Terraform dashboards in `aws`; AMG optional per client. |
| 3 | Browser ingress | **Evolve the existing `core` ingest endpoints to OTLP** (same paths, auth, quarantine, limits; opaque pass-through to the collector). See §3.4. |
| 4 | LLM content capture | **Deferred** — owner will come back to it. §6.5 stays a placeholder; nothing content-related is built. |
| 5 | Product dashboard v1 | **Full proposed set** (§7.3), including `chat_turn_facts` and `product_events` + `/analytics/events`. |
| 6 | Frontend events | **Curated**, scoped from a fresh inventory of the current dashboard app (§7.4); catalogue reviewed by the owner before implementation. |
| 7 | Ledger completeness (G26 LangGraph, data-discovery spend, `improvement_runs.llm_spend`) | **Deferred** to a separate ledger workstream (§6.6). |
| 8 | Reporting role | **Reuse `flynapse_readonly`** (existing `BYPASSRLS`, SELECT-only); grant SELECT on the app DB; purges stay owner-run (§7.2). |
| 9 | Operator scope of analytics | **Owners see the whole tenant; capability holders are entitlement-scoped and labelled** (§7.1). |
| 10 | Alert routing | **Slack channel + email** (§9.4). |

Defaults adopted without a separate ruling (say so if any should change):
- **Retention**: `aws` logs 30 d, spans 7 d (100% ingested, 1% indexed), metrics per backend default; `oss` POC
  logs 14 d, spans 3 d, metrics 30 d on a dedicated ≥100 GB volume; `product_events` 13 mo; ledgers forever
  with a `llm_model_calls` rollup decision deferred to the plan.
- **Collector hosting in Flynapse's own account**: the existing EC2 keeps only the collector (aws overlay);
  the client-facing Terraform module is ECS-based.
- **Improvement findings** are treated as internal-only (not client-visible) in the dashboard.
- **Parallelism**: phases 1+2 and 5 in separate worktrees (different repos), one implementer per tree.

## 12. Probes to run before the plan is finalised (cheap; each names the fallback if it fails)
- Live POC `.env`: confirm `LOKI_BASE_URL` is unset (G29) — decides whether Phase 0 needs a stop-gap for the
  current settings page or the rebuild simply replaces a dead page.
- CloudWatch OTel-metrics OTLP endpoint: confirm GA in the target regions and its temporality/histogram
  handling with one cumulative histogram — fallback: `prometheusremotewrite` to Amazon Managed Prometheus.
- CloudWatch Logs OTLP: stored field paths for resource attributes (needed for Logs Insights dashboards).
- Application Signals from vanilla OTel SDK spans (no AWS distro): does the service map/SLO populate —
  fallback: RED alarms on the OTLP metrics only, no SLO objects.
- PromQL alarms in the pinned Terraform AWS provider — fallback: `awscc` provider or SLO alarms.
- Amplify WEB_COMPUTE → private api reachability (decides whether SSR telemetry can ever join) and Node
  version on the Amplify build image (OTel JS 2.x needs ≥ 18.19).
- One pooled `psycopg2` query → `db.*` span with bootstrap ordered before pool creation.
- CloudWatch PromQL API limits against the busiest planned panel (only matters if AMG is chosen).
- Azure: one `otlphttp`+`azure_auth` send from a non-Azure host and the resulting metric names (only when the
  `azure` profile is built).

## 13. Error handling and testing summary
- Telemetry is never allowed to fail a request: exporters are batched and best-effort; the SDK is disabled
  cleanly by `OTEL_SDK_DISABLED`; ingress routes drop over-limit batches with a 4xx and a counter, never 5xx.
- Product analytics degrades explicitly: rate-limited, unavailable, empty are distinct states in the UI.
- Test kinds per repo follow the two-level layout: `tests/unit/observability/*` (bootstrap, bridge,
  cardinality lint, redaction), `tests/api/telemetry/*` (ingress contract, auth, limits), `tests/api/analytics/*`
  (panel registry against a seeded DB, RLS binding), `tests/integration/otel/*` (in-memory exporter smoke),
  compose smoke for `oss`, `otelcol validate` for every overlay, dashboard JSON schema checks.
