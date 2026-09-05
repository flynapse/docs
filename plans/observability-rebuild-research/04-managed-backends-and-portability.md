# 04 — Managed backends and the portability layer

Research deliverable for the observability rebuild (lens: **production backend choice + portability**).
Written 2026-09-05. External facts carry a URL and the date of the source; codebase facts carry `path:line`.
Read-only research — nothing in any repo was changed.

## 0. Framing

Design goal under evaluation (from the brief): application code speaks **OTel only** → OTLP → a
collector; the **collector config + IaC is the single swap point** between (a) the POC all-in-one OSS
stack on one EC2 box and (b) a managed backend in production. This document answers "what should the
managed backend be, per deployment target, and what exactly must stay constant for the swap to be a
config change".

What the estate looks like today (grounding for the swap):
- POC collector config: `copilot-mro/deployment/observability-local/otel-collector-config.yaml`
  — OTLP receiver (grpc 4317 / http 4318 with CORS from `${OTEL_CORS_ORIGIN_*}`), `prometheus`
  exporter on :9464 (scraped), `otlp/traces` → Tempo, `otlphttp/logs` → Loki `/otlp`, plus a
  `debug` exporter with `verbosity: detailed` on **every** pipeline (that alone will hurt at any volume).
- Production wiring: App Runner and Lambda point `OTEL_ENDPOINT` at the private IP of the single
  `weaviate_observability` EC2 (`iac/apprunner.tf:42`, `iac/lambda.tf:109`). No CloudWatch log groups,
  X-Ray, or ADOT in `iac/` (audit §1).
- Python deps are unpinned (`utils/pyproject.toml:41-43`, `api/pyproject.toml:24-29`,
  `copilot-mro/pyproject.toml:79-84` all `"*"`); the only instrumentation packages present are
  `opentelemetry-instrumentation-fastapi` and `-logging`. Python 3.11 (`api/pyproject.toml:10`).
- Dashboard pins an old OTel-JS line: `@opentelemetry/sdk-trace-web ^1.24.0`, instrumentation
  `^0.50.0` (`dashboard/package.json:24-30`), `web-vitals ^5.1.0` (`:89`), Next `15.2.4` (`:72`).
  No `instrumentation.ts` exists in `dashboard/` (checked root and `src/`).
- Grafana dashboards: 8 JSON files under `copilot-mro/deployment/observability-local/grafana/dashboards/`.

Terminology used below: **"ports unchanged"** = the existing Grafana JSON (PromQL/LogQL/TraceQL
datasource queries) works against the backend with only a datasource UID swap. **"needs rewrite"** =
the query language or the data model differs, so panels/alerts must be re-authored.

---

## 1. AWS native — CloudWatch family

### 1.1 OTLP ingestion status (as of 2026-09)

| Signal | Endpoint | Status | Auth | Source |
|---|---|---|---|---|
| Traces | `https://xray.<region>.amazonaws.com/v1/traces` | GA (since Nov 2024); **requires Transaction Search enabled on the account** | SigV4 only (`sigv4auth` ext, `service: "xray"`); bearer token **not** supported for traces | [CloudWatch OTLP collector setup](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPSimplesetup.html) (fetched 2026-09-05); [Application Signals X-Ray OTLP announcement, Nov 2024](https://aws.amazon.com/about-aws/whats-new/2024/11/application-signals-otel-x-ray-otlp-endpoint-traces) |
| Logs | `https://logs.<region>.amazonaws.com/v1/logs` | GA | SigV4 (`service: "logs"`) **or** bearer token (API key) | same doc; headers `x-aws-log-group`, `x-aws-log-stream` are **required per exporter instance** |
| Metrics | `https://monitoring.<region>.amazonaws.com/v1/metrics` | Public preview Apr 2026 → **GA June 2026** ("native OpenTelemetry metrics with PromQL") | SigV4 (`service: "monitoring"`) **or** bearer token | same doc; timeline from [hidekazu-konishi.com, 2026-08-12](https://hidekazu-konishi.com/entry/opentelemetry_native_observability_on_aws.html) |

Key facts:
- All three are plain `otlphttp` exporters in an **upstream** collector (contrib distribution — `sigv4auth`
  is a contrib extension). No ADOT-specific exporter is needed any more. The AWS doc literally tells you
  to download the upstream collector release.
- **Log group is chosen by an exporter header**, not by resource attributes. One `otlphttp/logs` exporter =
  one log group. Routing per service therefore needs either one exporter per service + a `routing`
  connector keyed on `service.name`, or accept one shared group and rely on the OTLP resource fields
  (`resource.attributes.service.name` etc. land as structured JSON fields queryable in Logs Insights).
  (Verified below in §1.3.)
- Metrics GA (June 2026) adds **PromQL over OTel metrics in "Query Studio"** with resource attributes
  addressable as `@resource.service.name="…"` (konishi, 2026-08-12). This is *PromQL-compatible*, but
  the label naming (`@resource.` prefix) means our existing PromQL panels **do not port 1:1**.
- OTel metrics ingestion is billed **$0.50/GB ingested** (includes 15 months storage), separate from
  the classic per-metric custom-metric pricing ([CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/), fetched 2026-09-05).
- X-Ray SDKs and the X-Ray daemon entered **maintenance mode 2026-02-25** (security fixes only) —
  AWS's direction is unambiguously OTel/OTLP (konishi, 2026-08-12).

### 1.2 Transaction Search + Application Signals
- Enabling Transaction Search is an **account-level** switch; spans sent to X-Ray (incl. via the OTLP
  endpoint) are stored 100% as structured logs in the `aws/spans` log group "in the semantic convention
  format with W3C trace IDs", and a configurable % is indexed as trace summaries in X-Ray
  ([Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Transaction-Search.html), fetched 2026-09-05).
- Pricing: spans **$0.35/GB** (0–10 TB), $0.20/GB (10–30 TB), $0.15/GB beyond; Application Signals
  (service-level RED metrics/SLOs/topology derived from spans) $1.50 per million requests for the first
  100 M, then $0.75, then $0.30 (pricing page, fetched 2026-09-05). Legacy X-Ray trace pricing
  ($5 per million recorded) is what you pay **without** Transaction Search.
- AWS's own doc recommends `always_on` sampling (100% spans) when feeding Application Signals — the
  cost model is per GB of spans, so head sampling in the SDK is replaced by "pay per GB, index a %".
- Practical trap (secondary source, needs confirmation): the `sample-otel-cloudwatch-no-collector`
  repo states X-Ray "requires trace IDs where the first 4 bytes are a Unix timestamp" and silently drops
  fully-random IDs ([TRACES.md](https://github.com/aws-samples/sample-otel-cloudwatch-no-collector/blob/main/docs/TRACES.md)).
  The Transaction Search doc says W3C IDs are stored. Resolution in §1.3 below.

**Trace-ID resolution:** X-Ray accepts W3C-format (fully random) trace IDs since 2023-10-27
([AWS What's New](https://aws.amazon.com/about-aws/whats-new/2023/10/aws-x-ray-w3c-format-trace-ids-distributed-tracing);
requires ADOT collector ≥ 0.34.0 / CW agent ≥ 1.300030.0). The sample repo's "silently dropped" warning
predates this. `AwsXRayIdGenerator` is therefore optional; the default Python/JS id generators are fine.
Keep the W3C `tracecontext` propagator (not `xray`) — that is also what the browser SDK already injects
(`dashboard/lib/observability/otel.ts`, audit G2).

### 1.3 Do OTel resource attributes / service names survive well enough to keep the dashboards?

| Signal | How CloudWatch stores it | Query language | Existing Grafana panels port? |
|---|---|---|---|
| Logs | Structured JSON events in the log group named by the exporter header; resource, scope, body, severity, attributes are all preserved as fields (OTLP JSON shape shown in the [Logs OTLP doc](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_HTTP_Endpoints_OTLP.html)); 1 MB/event, 10k events/request, 5,000 req/s/region ([endpoint limits](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPEndpoint.html)) | Logs Insights (SQL-ish) | **No** — LogQL panels must be rewritten. Exact stored field paths (e.g. `resource.attributes.service.name`) need a live probe. |
| Metrics | Full OTel semantic structure kept: resource attributes → `@resource.<attr>` labels, scope + datapoint attributes → labels; **metric names keep their dots** (PromQL per Prometheus 3.0 UTF-8 names: `{"http.server.active_requests", "@resource.service.name"="myservice"}`) ([PromQL doc](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-PromQL.html), fetched 2026-09-05) | PromQL (CloudWatch dialect) via Query Studio, alarms, and a SigV4-signed Prometheus-compatible API (`/api/v1/query`, `query_range`, `series`, `labels`) | **No, not 1:1.** Our panels are written against the collector's `prometheus` exporter naming (`http_requests_total`, `service_name` labels). CloudWatch keeps `http.requests` + `@resource.service.name`. Every query needs a rename pass. PromQL API limits are tight: 500 series/query, 7-day range, 100k series scanned/24 h, 20 s execution — a busy Grafana dashboard can exhaust these. |
| Traces | 100% of spans as structured logs in `aws/spans` (semconv format, W3C ids); 1% indexed as trace summaries by default (free) ([Enable Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)); Application Signals builds RED metrics + service map from spans | Transaction Search visual editor, Logs Insights on `aws/spans`, X-Ray trace view | **No** — TraceQL panels do not port; but the Application Signals UI replaces most of what our (unused, audit G6) Tempo panels would show. |

Bottom line for AWS: the **app-side contract holds** (OTLP + semconv resource attributes are preserved end
to end), but **every dashboard and alert is a rewrite** into CloudWatch dialects. Grafana can sit on top
(AMG has CloudWatch + X-Ray built-in data sources, [AMG data sources](https://docs.aws.amazon.com/grafana/latest/userguide/AMG-data-sources.html);
the new PromQL API is SigV4-signed and AWS says Grafana can use it — not verified by us), but that still
does not make the JSON reusable.

### 1.4 What runs where (App Runner / Lambda / ECS) — sidecar vs gateway

| Compute | Sidecar collector possible? | Options | Note |
|---|---|---|---|
| **App Runner** (api today, `iac/apprunner.tf`) | **No** — App Runner has no sidecar containers; its built-in tracing is an "observability configuration" that ships **X-Ray traces only** through ADOT ([App Runner + X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-app-runner.html)) | (a) keep a **gateway collector** reachable through the VPC connector (what `OTEL_ENDPOINT` already does); (b) go **collector-less** with `aws-opentelemetry-distro` ≥ 0.10.0 sending SigV4-signed OTLP straight to the endpoints ([collector-less ADOT doc](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLP-UsingADOT.html)) — requires `OTEL_PYTHON_DISTRO=aws_distro`, `OTEL_PYTHON_CONFIGURATOR=aws_configurator`, and pins the app to AWS (violates constraint 3) | Gateway is the only option that keeps app code backend-agnostic. |
| **Lambda** (`iac/lambda.tf`) | Layer-based | New ADOT Lambda layers with Application Signals are collector-less but **export only to CloudWatch/X-Ray**; the legacy ADOT layer embeds a stripped collector and can export anywhere ([OTel blog, 2025](https://opentelemetry.io/blog/2025/observing-lambdas/), [ADOT Lambda](https://aws-otel.github.io/docs/getting-started/lambda/)) | Simplest portable choice: plain OTel SDK in the function → gateway collector over the VPC (current wiring). |
| **ECS** (the un-implemented `docs/production-architecture.md` target) | Yes | ADOT doc's primary pattern is a **sidecar per task** with task-role IAM ([ADOT on ECS](https://aws-otel.github.io/docs/setup/ecs)); a gateway service works equally | Either; gateway keeps one credential/config surface. |
| **EC2** (POC box) | n/a | Instance role + `CloudWatchAgentServerPolicy` is all the collector needs to reach all three endpoints ([OTLP setup doc](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPSimplesetup.html)) | This is exactly the POC→prod swap point: same box, different exporters. |

### 1.5 Pricing model (us-east-1 list prices, [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/), [AMG pricing](https://aws.amazon.com/grafana/pricing/), [AMP pricing](https://aws.amazon.com/prometheus/pricing/) — all fetched 2026-09-05)

| Item | Price |
|---|---|
| Logs ingest (Standard / Infrequent Access) | $0.50 / $0.25 per GB; storage $0.03/GB-month; first 5 GB free |
| Logs Insights | per GB scanned (free when run from console dashboards) |
| Custom metrics (classic, EMF/PutMetricData) | $0.30/metric-month first 10k, $0.10 to 250k, $0.05 beyond |
| **OTel metrics (OTLP endpoint)** | **$0.50 per GB ingested**, 15 months storage included — a fundamentally different meter from per-metric |
| Spans (Transaction Search) | $0.35/GB (0–10 TB), $0.20, $0.15; 1% indexed free |
| Application Signals | $1.50 per million requests (first 100 M), $0.75, $0.30 |
| Legacy X-Ray (no Transaction Search) | $5 per million traces recorded, 100k free |
| Dashboards | $3/dashboard-month (auto dashboards free) |
| Alarms | $0.10/alarm-metric-month |
| AMG | $9 editor/admin, $5 viewer per active user per workspace-month; ≥1 editor per workspace; 90-day trial (5 users) |
| AMP (only if we choose remote-write instead of the OTLP metrics endpoint) | $0.90 per 10 M samples (first 2 B), $0.03/GB-month, $0.10 per B query samples; free tier 40 M samples |

AMP is now **redundant** for our shape: the OTLP metrics endpoint + PromQL (GA 2026-06-16,
[announcement](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-cloudwatch-otel-metrics/)) covers
"Prometheus-style metrics in CloudWatch" without a second store. EMF (`awsemf` exporter) remains the path
to *classic* CloudWatch metrics (per-metric pricing, no PromQL) and is not recommended for new work.

### 1.6 IAM from the collector
- `sigv4auth` (contrib, **beta**) uses the AWS SDK default chain (env, shared config, IMDS, IRSA/web-identity)
  and supports `assume_role { arn, sts_region, external_id, web_identity_token_file }`
  ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/sigv4authextension/README.md)).
- Deployment in a **client's account**: collector runs in their account on an instance/task role → nothing
  cross-account. Deployment where **Flynapse hosts the collector but the client owns CloudWatch**: `assume_role`
  into a client-provided role with `external_id` — one extension block, no app change.
- Bearer tokens (API keys) exist for logs and metrics only, **not traces**; useful for non-AWS hosts
  (e.g. a POC box on-prem shipping to a client's CloudWatch) but a long-lived secret.

---

## 2. Azure native — Azure Monitor / Application Insights

### 2.1 OTLP status (as of 2026-09)
- **Direct OTLP ingestion from an OSS collector is GA.** Microsoft Learn (ms.date 2026-05-29): "Only the AMA
  and AKS paths are in preview. The other paths (Microsoft OpenTelemetry Distro and OpenTelemetry Collector)
  are generally available" ([OpenTelemetry with Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/opentelemetry-options)).
  Announcement: ["Direct OpenTelemetry ingestion into Azure Monitor is now generally available"](https://techcommunity.microsoft.com/blog/azureobservabilityblog/direct-opentelemetry-ingestion-into-azure-monitor-is-now-generally-available/4524044)
  (Community Hub, June 2026 — page body not fetchable; title + Learn page corroborate). Some sub-pages
  still carry "(Preview)" banners (e.g. [collect-use-observability-data](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/collect-use-observability-data),
  ms.date 2026-04-01) — the docs lag the GA.
- Mechanics ([Ingest OTLP with OTel Collector](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/opentelemetry-protocol-ingestion), ms.date 2026-05-27):
  - Create an Application Insights resource with **OTLP support = On** → it provisions the Data Collection
    Endpoint (DCE), Data Collection Rule (DCR), a Log Analytics workspace (logs + traces) and an Azure
    Monitor workspace (Prometheus metrics), and shows the three endpoint URLs.
  - Endpoints: `https://<dce>/dataCollectionRules/<dcr-immutable-id>/streams/Microsoft-OTLP-Traces/otlp/v1/traces`,
    `.../streams/Microsoft-OTLP-Logs/otlp/v1/logs`, `https://<metrics-dce>/.../streams/Custom-Metrics-Otel/otlp/v1/metrics`.
  - Exporter: plain **`otlphttp`** + contrib **`azure_auth`** extension (collector ≥ 0.132; the
    `managed_identity: {}` syntax needs ≥ 0.148.0). Identity needs **Monitoring Metrics Publisher** on the DCR.
    Managed identity on Azure compute; service principal / workload identity elsewhere.
  - **HTTP/protobuf only** (no gRPC, no JSON). **Metrics must be delta temporality + exponential
    histograms** for the Application Insights experiences — add `cumulativetodelta` in the collector or set
    the SDK preference. This is a real portability wrinkle: Prometheus/Mimir want cumulative.
- Where data lands: metrics → Azure Monitor workspace (PromQL, Grafana); logs + traces → Log Analytics in an
  OTel-semconv schema queried with **KQL**. Streams are `Microsoft-OTLP-Logs` / `Microsoft-OTLP-Traces`;
  the resulting table names were not stated in any page fetched — probe a live workspace.
- Application Insights blades (Performance, Failures, Search, end-to-end transaction) work on OTLP data;
  **Live Metrics does not**; Metrics Explorer on OTel metrics "can require manual PromQL" — Microsoft points
  metrics users at Grafana.
- The older contrib **`azuremonitor` exporter** (beta for all signals, connection-string auth) still exists and
  writes into classic App Insights tables (`AppRequests`/`AppDependencies`) ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/azuremonitorexporter/README.md)).
  It is the fallback if a client's tenant blocks the new path, but it has no PromQL story.

### 2.2 Visualisation
- **Azure Monitor dashboards with Grafana** — Grafana embedded in the Azure portal, **GA Nov 2025, no extra
  cost**, Azure Monitor data sources only, dashboards are ARM/Bicep resources
  ([GA post](https://techcommunity.microsoft.com/blog/azureobservabilityblog/announcing-general-availability-azure-monitor-dashboards-with-grafana/4468972),
  [Learn overview](https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/visualize-grafana-overview)).
- **Azure Managed Grafana** (Standard) — needed only for non-Azure data sources / alerting / reporting:
  ~$0.043/h per standard unit (~$31/month) + **$6 per active user/month**; Essential tier is cheaper but has
  no alerts ([pricing page](https://azure.microsoft.com/en-us/pricing/details/managed-grafana/) hides numbers
  behind JS; figures from [Azure FAQ mirror](https://docs.azure.cn/en-us/managed-grafana/faq) and secondary sources).

### 2.3 Pricing model (list, USD, secondary-sourced because the official page renders "$-" without JS —
[official page](https://azure.microsoft.com/en-us/pricing/details/monitor/), [monitoringcost.com 2026](https://monitoringcost.com/azure-monitor-cost), [pump.co 2026](https://www.pump.co/blog/azure-monitor-pricing/))

| Item | Price |
|---|---|
| Log Analytics — Analytics logs ingest | ~$2.30/GB PAYG (first 5 GB/month free); commitment tiers from 100 GB/day |
| Basic logs / Auxiliary logs | ~$0.50/GB / ~$0.05/GB (query charged per GB scanned) |
| Interactive retention | 31 days included (90 for App Insights); beyond → per GB-month |
| Managed Prometheus (Azure Monitor workspace) | ~$0.16 per 10 M samples ingested (18-month retention) + query samples |
| Application Insights | same meter as Log Analytics |
| Alerts | per metric/log alert rule-month |

Azure logs are **~4–5× CloudWatch's per-GB** ingest price; traces also land in Log Analytics, so span
volume is charged at the logs rate. Sampling matters more on Azure than on AWS.

### 2.4 Dashboards port?
- Metrics: PromQL over an Azure Monitor workspace → **probably yes** for panels, *if* Microsoft's OTLP→Prometheus
  naming matches the collector's (dots→underscores, unit/`_total` suffixes). Not verified by us — one
  probe with our `http_requests_total` panel answers it.
- Logs / traces: KQL → **rewrite**.
- Alerts: Prometheus rule groups exist as first-class resources (`azurerm_monitor_alert_prometheus_rule_group`)
  → PromQL rules **port**; log/trace alerts (KQL scheduled-query rules) do not.

---

## 3. Vendor-neutral SaaS with native OTLP endpoints

| Vendor | OTLP ingest | Auth | Query language / dashboards port | Browser RUM | Pricing (list, fetched 2026-09-05) |
|---|---|---|---|---|---|
| **Grafana Cloud** | Native OTLP gateway `https://otlp-gateway-<region>.grafana.net/otlp` (`/v1/{metrics,logs,traces}`) → Mimir / Loki / Tempo ([docs](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/)) | Basic auth: instance id + access-policy token (`headers: Authorization: Basic …`) | **PromQL / LogQL / TraceQL — identical to the POC stack. Dashboards port 1:1** (datasource UID swap). Metric naming uses the same OTLP→Prometheus translation as the collector's `prometheus` exporter (dots→`_`, unit suffix, `_total`; `job` = `service.namespace/service.name`, `instance` = `service.instance.id`; other resource attrs in `target_info`) ([format considerations](https://grafana.com/docs/grafana-cloud/send-data/otlp/otlp-format-considerations/)). Loki promotes the same 17 resource attributes to labels as OSS Loki ([Loki OTel](https://grafana.com/docs/loki/latest/send-data/otel/)) | Faro Web SDK → Frontend Observability; **50k sessions/month free** | Free: 10k series, 50 GB logs, 50 GB traces, 50 GB profiles, 3 users, 14-day retention. Pro: $19/month + $6.50 per 1k series (13 mo) + ≈$0.50/GB logs & traces (30 d; itemised $0.05 process + $0.40 write + $0.10 retain) + $8 per active user ([pricing](https://grafana.com/pricing/)) |
| **New Relic** | Native OTLP `https://otlp.nr-data.net` (:443/4317/4318; EU `otlp.eu01.nr-data.net`) ([docs](https://docs.newrelic.com/docs/opentelemetry/best-practices/opentelemetry-otlp/)) | `api-key: <license key>` header | **NRQL — rewrite.** Wants delta temporality; 1 MB payload cap, 64 resource attrs, 4,095-char strings | Proprietary browser agent (not OTel), links to backend traces | Free 100 GB/month + 1 full user; then $0.40/GB (Original) or $0.60/GB (Data Plus); users: Core $49, Full Platform $349+/month ([pricing](https://newrelic.com/pricing)) |
| **Datadog** | **No direct OTLP intake.** Either the Datadog Agent's OTLP receiver ("an ingesting Agent on every host") or the contrib `datadog` exporter (beta, all signals) ([OTLP in Agent](https://docs.datadoghq.com/opentelemetry/setup/otlp_ingest_in_the_agent/), [exporter README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/datadogexporter/README.md)) | `api.key` + site | **Datadog query syntax — rewrite** | Datadog RUM SDK; Measure $0.15 + Investigate $3.00 per 1k sessions (+$2.50 replay) ([secondary](https://rumcost.com/datadog-rum-pricing)) | Host-based: Infra $15–23/host, APM $31–40/host; logs $0.10/GB ingest + $1.70 per M indexed events; custom metrics allotment per host ([pricing](https://www.datadoghq.com/pricing/)) |
| **Honeycomb** | Native OTLP `https://api.honeycomb.io` (EU `api.eu1.honeycomb.io`) ([docs](https://docs.honeycomb.io/send-data/opentelemetry/)) | `x-honeycomb-team: <key>` | **Honeycomb query builder / BubbleUp — rewrite** (event-centric, no PromQL) | Frontend Observability included; OTel-web friendly | Free 20 M events + 100 M metric points/month, unlimited seats; Pro from $150/month (750 M events) ([pricing](https://www.honeycomb.io/pricing)) |

**Only Grafana Cloud preserves the existing PromQL/LogQL dashboards unchanged.** New Relic and Honeycomb are
OTLP-native and cheap to start but every panel and alert is re-authored. Datadog is the least
OTel-native (agent required) and the most expensive at our scale.

Portability detail worth recording: because both the POC (collector `prometheus` exporter + Loki `/otlp`)
and Grafana Cloud use the upstream OTLP→Prometheus/Loki translators, the **same collector config file
minus exporters** produces identical series names and labels in both — the swap really is exporter-only.

---

## 4. Portability mechanics — what stays constant, what changes

### 4.1 The invariant layer (never changes across backends)
1. **Wire protocol**: OTLP 1.x over HTTP/protobuf from every app to *one* gateway collector. Use
   `http/protobuf`, not gRPC: CloudWatch endpoints are HTTP-only, Azure is HTTP/protobuf-only, and the
   browser can only do HTTP. The app-side exporter never learns a vendor URL or credential.
2. **Resource identity** (semconv): `service.name`, `service.namespace` (= `flynapse`), `service.version`,
   `service.instance.id`, `deployment.environment.name`. Every backend above keys its UI on `service.name`
   (Application Signals "service", App Insights role, Grafana `job`). Fix audit G12 here, once.
3. **Signal semconv**: HTTP server/client (`http.server.request.duration`, `http.route`), DB, GenAI
   (`gen_ai.*` for the LLM ledger — this is what makes LLM spans/metrics readable by every vendor's
   "LLM observability" view), log record attributes (`tenant.id`, `user.id`, `session.id`).
4. **W3C trace context** propagation, both inbound and outbound (audit G5) — X-Ray, Azure, Tempo all accept
   W3C ids now; no `xray` propagator needed.
5. **Collector front half**: `otlp` receiver, `memory_limiter`, `batch`, `resourcedetection`,
   `attributes`/`transform` (tenant/env stamping), `redaction`/`filter` (PII, health checks). Identical in
   every environment.

### 4.2 The swap layer (changes per backend) — exporters + auth + query surfaces

| Backend | Exporters | Auth extension | Extra processors |
|---|---|---|---|
| POC (OSS on EC2) | `otlphttp/logs` → Loki `/otlp`, `otlp/traces` → Tempo, `prometheus` (scrape) or `prometheusremotewrite` → Prometheus | none | — |
| AWS CloudWatch | `otlphttp/logs` (+ `x-aws-log-group/stream` headers), `otlphttp/traces`, `otlphttp/metrics` | `sigv4auth` ×3 (`logs`, `xray`, `monitoring`) | optional `routing` connector → one logs exporter per service/log group |
| Azure Monitor | one `otlphttp/azuremonitor` with three `*_endpoint`s | `azure_auth` | `cumulativetodelta` (metrics) |
| Grafana Cloud | one `otlphttp` to the gateway | `basicauth` or static `headers:` | — |
| New Relic / Honeycomb | one `otlphttp` | static `headers:` (`api-key` / `x-honeycomb-team`) | `cumulativetodelta` recommended by NR |
| Datadog | `datadog` exporter (contrib) | `api.key` | `datadog` connector for APM stats |

What else changes and must be planned as work, not config: **query language → dashboards → alert rules →
RUM SDK** (see §7 and §8).

### 4.3 Collector config-by-environment patterns
Verified against the [collector configuration doc](https://opentelemetry.io/docs/collector/configuration/) and
[confmap README](https://github.com/open-telemetry/opentelemetry-collector/blob/main/confmap/README.md) (fetched 2026-09-05):
- **Env substitution**: `${env:VAR}` and `${env:VAR:-default}`; `$$` for a literal `$`. The POC config already
  uses `${OTEL_CORS_ORIGIN_1}` (`copilot-mro/deployment/observability-local/otel-collector-config.yaml`).
- **Multiple `--config`**: repeated flags (or `env:`/`yaml:`/`http:` providers) are merged: **maps deep-merge,
  lists are replaced by the later source**, later `--config` wins. An experimental gate
  `confmap.enableMergeAppendOption` appends lists instead, but only for `service.{extensions,receivers,exporters}`
  — do not design around it.
- Consequence: put receivers/processors/connectors in `base.yaml`, and in each `backend-<x>.yaml` define the
  `exporters:`, `extensions:` **and the complete `service:` block** (pipelines list exporters explicitly).
  Never write a bare `processors:` key in an overlay (null map wipes the base).
- `${file:exporters.yaml}` embedding and `--set service::pipelines::logs::exporters=[…]` exist for one-offs.
- IaC shape that follows: Terraform (AWS) / Bicep (Azure) / compose (POC) render **one env file** (endpoint
  URLs, region, log-group names, tokens via secret refs) and pick **one overlay file**; the container image
  and `base.yaml` are identical everywhere.

### 4.4 Processors that matter
- `resourcedetection` (detectors `env, system, ec2, ecs, lambda, azure`) — fills `cloud.*`, `host.*` so the
  same dashboards can filter by environment on any backend.
- `attributes`/`transform` (OTTL) — promote `tenant.id`/`user.id` from log/span attributes to resource level
  only if a backend needs it as a label (Loki label cardinality caveat: keep tenant as structured metadata,
  not an index label, unless tenant count is small). The collector **cannot invent** tenant context — the app
  must set it (it already binds it into loguru extra, `api/flynapse_api/middleware/logging.py:59-68`).
- `redaction` (traces **beta**, logs/metrics **alpha**) — allow-list attribute keys, regex-mask values, hash
  option ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/redactionprocessor/README.md)).
  Pair with `transform` `replace_pattern(...)` for bodies. Prompt/completion text (audit G16) must **never**
  ride OTLP to a SaaS backend unless the client agrees — keep it in Postgres and reference by id.
- `filter` — drop `/health`, `/metrics` spans; drop `debug` logs in prod.
- `tail_sampling` (**beta**, stateful: all spans of a trace must hit the same collector instance → single
  gateway or `loadbalancing` exporter tier; `decision_wait` × `num_traces` bounds memory)
  ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/tailsamplingprocessor/README.md)).
  Worth it for per-GB backends (Grafana Cloud, NR, Azure). On AWS, Transaction Search's model is "ingest 100%
  at $0.35/GB, index 1%" and AWS explicitly recommends `always_on` — so tail sampling is a cost knob, not a
  requirement there.
- `routing` connector (**alpha**) — OTTL `resource.attributes["service.name"] == …` → per-service pipelines;
  needed only for CloudWatch per-service log groups
  ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/connector/routingconnector/README.md)).
- Rate limiting: **no upstream `ratelimit` processor in contrib** (issue [#35204](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/35204) open;
  Elastic ships an out-of-tree one). `memory_limiter` is back-pressure, not per-client fairness. Do per-client
  limits in front of the collector (proxy / WAF), see §6.

### 4.5 Sidecar vs gateway
Gateway (one collector deployment per environment, apps export to it over the private network) is the
recommended shape: App Runner cannot run sidecars at all; Lambda and the browser need a network endpoint
anyway; tail sampling needs a single instance; and credentials/IAM live in exactly one place. Sidecars only
make sense on ECS/K8s for host metrics and local buffering — optional later.

---

## 5. Instrumentation coverage to close the audit gaps (versions as of 2026-09-05)

### 5.1 Python (services in `api/`, `copilot-mro/`, `core/`, `shift-optimizer/`, `telegram-bot/`, `lambdas/`)
Current release line: **`opentelemetry-sdk 1.44.0`** (Python ≥ 3.10) and contrib instrumentations
**`0.65b0`** (all contrib packages share the version; `opentelemetry-distro 0.65b0` pins
`opentelemetry-exporter-otlp 1.44.0`) — PyPI JSON fetched 2026-09-05
([sdk](https://pypi.org/pypi/opentelemetry-sdk/json), [fastapi instr.](https://pypi.org/pypi/opentelemetry-instrumentation-fastapi/json),
[distro](https://pypi.org/pypi/opentelemetry-distro/json)). Signal status: traces **stable**, metrics
**stable**, logs **"Development"** ([opentelemetry.io/python](https://opentelemetry.io/docs/languages/python/)) —
the logs SDK works and is what every vendor's Python doc uses, but its import path is still `opentelemetry.sdk._logs`.

| Gap | Package (pin to `==0.65b0`) | Notes |
|---|---|---|
| G4 HTTP server spans/metrics | `opentelemetry-instrumentation-fastapi` (already listed, `api/pyproject.toml:26`), `-asgi` | `FastAPIInstrumentor.instrument_app(app)` per sub-app; emits `http.server.request.duration` histogram → replaces the hand-rolled `http_request_duration_seconds` (audit §2) |
| G5 outbound propagation | `-httpx`, `-aiohttp-client`, `-requests`, `-urllib3` | inject `traceparent` automatically; kills the "no `propagate.inject` anywhere" defect |
| DB | `-asyncpg`, `-psycopg` (v3) / `-psycopg2`, `-sqlalchemy`, `-redis` | `db.*` semconv spans; SQL sanitisation via `redaction` if needed |
| AWS SDK (Bedrock, S3, Cognito) | `-botocore` | Bedrock calls become client spans; the GenAI semconv attributes still need to be set by `utils/utils/llm.py` |
| Lambda | `-aws-lambda` | root span + cold-start attrs; works with the gateway collector |
| Logs | `opentelemetry-sdk` `LoggingHandler` + `-logging` (already listed) | see 5.2 |
| Runtime | `-system-metrics`, `-threading`, `-asyncio` | optional; system metrics only useful on the POC box |

All names confirmed present in the contrib index ([readthedocs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/)).
Pin them — the estate's `"*"` constraints (`utils/pyproject.toml:41-43` etc.) will otherwise drift across
the `1.x`/`0.xb0` pair and break the shared `api` env.

### 5.2 Logs: OTel `LoggingHandler` vs the loguru OTLP sink
- Today: a bespoke loguru sink builds OTLP by hand (`utils/utils/logging_config.py:132-238`) and stdout is a
  non-JSON template (`:89-90`, audit G15).
- Replacement, zero app-code change at call sites: `logger.add(LoggingHandler(level=…, logger_provider=…))`
  — loguru accepts a stdlib `logging.Handler` as a sink, and the OTel handler attaches the active span's
  `trace_id`/`span_id` itself (log-bridge behaviour documented across vendor guides, e.g.
  [Dash0 guide](https://www.dash0.com/guides/opentelemetry-logging-python), [OTel logs example](https://opentelemetry.io/docs/zero-code/python/logs-example/)).
  Keep loguru's `extra` (`tenant_id`, `request_id`, …) — they arrive as log-record attributes.
- Add a second sink `logger.add(sys.stdout, serialize=True)` for JSON stdout so CloudWatch agent / Fluent Bit /
  Azure Monitor Agent paths work too (G15) — belt and braces for backends that scrape stdout.
- G13/G14 fix falls out of the SDK's own env contract: honour `OTEL_SDK_DISABLED=true` (spec kill-switch),
  `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_SERVICE_NAME`,
  `OTEL_RESOURCE_ATTRIBUTES=service.namespace=flynapse,deployment.environment.name=…`,
  `OTEL_TRACES_SAMPLER=parentbased_traceidratio` + `_ARG`, `OTEL_PYTHON_EXCLUDED_URLS=health,metrics`,
  `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true`, `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS`
  ([zero-code config](https://opentelemetry.io/docs/zero-code/python/configuration/)). Delete the
  `utils.config` endpoint indirection; one env contract for every service and every backend.
- `opentelemetry-instrument` (zero-code CLI) vs programmatic: with uvicorn/gunicorn workers the CLI has to wrap
  the worker process; the estate already initialises programmatically in `api/` — keep programmatic, but
  drive it purely from the env vars above (`opentelemetry-distro`'s configurator does exactly this).

### 5.3 JavaScript — Next.js SSR and the browser
- **SSR**: `instrumentation.ts` at the project root, `register()`; **stable in Next 15** (no
  `experimental.instrumentationHook`; the dashboard is on `15.2.4`, `dashboard/package.json:72`). Two routes:
  `@vercel/otel` **2.1.3** (`registerOTel({ serviceName })`, edge-safe) or `@opentelemetry/sdk-node`
  **0.222.0** behind `process.env.NEXT_RUNTIME === 'nodejs'` ([Next.js OTel guide](https://nextjs.org/docs/app/guides/open-telemetry), updated 2026-08-25).
  Next emits `[method] [route]`, `render route`, `fetch`, route-handler spans with `next.*` attributes;
  `NEXT_OTEL_VERBOSE=1` for more. **No `instrumentation.ts` exists today** (checked root and `src/`).
- **Version cliff**: `@vercel/otel 2.x` peer-requires OTel JS **2.x** (`@opentelemetry/sdk-trace-base >=2.0.0`,
  `instrumentation >=0.200.0`; npm registry fetched 2026-09-05). The dashboard pins `sdk-trace-web ^1.24.0`,
  `instrumentation-fetch ^0.50.0` (`dashboard/package.json:24-30`) — a major upgrade is part of the work.
  Current: `@opentelemetry/sdk-trace-web 2.11.0`, `instrumentation-fetch 0.222.0`,
  `instrumentation-document-load 0.67.0` (contrib web), `web-vitals 6.2.1` (dashboard has `^5.1.0`).
- **Browser**: `WebTracerProvider` + `FetchInstrumentation` + `XMLHttpRequestInstrumentation` (already wired,
  `dashboard/lib/observability/otel.ts:30-45`) + `DocumentLoadInstrumentation`; ship Web Vitals as OTel
  **log events** (`event.name = browser.web_vital`, attrs `name`, `value`, `rating`, `route`) via the OTLP logs
  exporter — this keeps RUM inside OTLP so it lands in any backend. Restrict
  `propagateTraceHeaderCorsUrls` to the API origin (G2 notes it is `[/.*/]`).
- **Amplify**: the SSR compute only sees env vars written into `.env.production` during build
  ([Amplify SSR env doc](https://docs.aws.amazon.com/amplify/latest/userguide/ssr-environment-variables.html));
  `dashboard/amplify.yml:10-11` allow-lists `ENV, APP_VERSION, API_BASE_URL, …, NEXT_PUBLIC_*` — **no `OTEL_*`**,
  which is why `runtime-config.ts:90-93` falls back to `localhost:4318` (G2). Add `OTEL_EXPORTER_OTLP_ENDPOINT`
  (server-side) to that grep; the browser must **not** get a collector URL at all (see §6).
- **Grafana Faro** alternative: `@grafana/faro-web-sdk 2.11.0` (bundles `web-vitals ^6`, errors, console,
  sessions, and an OTel-based tracing add-on). Collector `faro` receiver is **alpha** for logs and traces,
  contrib only ([README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/faroreceiver/README.md)).
  Assessment: excellent product if the backend is Grafana Cloud (native Frontend Observability, 50k
  sessions free), acceptable for the POC via the alpha receiver, but it makes the browser layer
  Grafana-shaped. OTel-web + web-vitals-as-events is the portable choice; adopt Faro only if Grafana Cloud
  is picked for production and the POC.

---

## 6. Browser telemetry ingestion — exposing an endpoint safely

Options evaluated:

| Option | Mechanics | Pros | Cons |
|---|---|---|---|
| A. Public collector OTLP/HTTP | `otlp.protocols.http.cors.allowed_origins/allowed_headers/max_age` (confighttp; `max_request_body_size` default 20 MiB), TLS at an ALB, `auth: { authenticator: bearertokenauth }` on the receiver (extension implements both server and client authenticators, **beta**; token/`filename`/`tokens` list) ([confighttp](https://github.com/open-telemetry/opentelemetry-collector/blob/main/config/confighttp/README.md), [bearertokenauth](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/bearertokenauthextension/README.md)) | Zero app code; browser SDK's native OTLP exporter | Any token shipped in JS is public → the "auth" only deters scanners; no user identity on the data; collector has **no rate limiter**; CORS preflight on every batch; PII stripping must be perfect at the collector; the collector becomes an internet-facing service (needs WAF, ALB, cert, its own scaling) |
| B. Proxy through **Next.js route handler** (`app/api/otlp/v1/{traces,logs}/route.ts`) | Same-origin POST from the browser → route handler validates the session cookie, attaches `user.id`/`tenant.id`/`session.id` as headers, forwards to the private collector; collector `otlp.protocols.http.include_metadata: true` + `attributes` processor `from_context` copies the headers onto every record | No CORS, no public collector, cookie auth = real identity, per-user rate limiting in the handler, allow-list of attribute keys at the edge, works on Amplify SSR compute (private VPC egress via the existing collector wiring) | A little Next code; the SSR compute is the ingress (Lambda-backed on Amplify — bursts cost invocations); payload size limits of the SSR runtime |
| C. Proxy through the **FastAPI gateway** (`api/`) | Same as B but at `/observability/v1/…`; `core` already owns a frontend log-ingest endpoint (`core/resources/logging/logging_endpoints.py`, audit §1) | One backend, reuse existing auth middleware + tenant binding; consolidates the current log ingest and OTLP into one sink | Cross-origin from the dashboard (but that CORS already exists for the API); adds telemetry traffic to the API's own request metrics (filter by route) |

**Recommendation: B for traces/vitals, and fold the existing core log ingest into the same shape (C) only if
the team prefers one Python sink.** Concretely:
- Browser exporters point at **relative** `/api/otlp/v1/traces` and `/api/otlp/v1/logs` (the code already
  defaults to `'/otlp/v1/traces'` when no endpoint is set, `dashboard/lib/observability/otel.ts:37`).
- The route handler: reject without a valid session; cap body at ~256 KB; token-bucket per user (e.g. 60
  batches/min); drop any attribute not in an allow-list (`http.url` query strings stripped, no bodies);
  stamp `X-Tenant-Id`, `X-User-Id`, `X-Session-Id` headers; forward with `fetch` to the collector's private
  OTLP/HTTP address; never forward client-supplied `Authorization`.
- Collector side: `include_metadata: true`; `attributes/browser: actions: [{key: tenant.id, from_context: X-Tenant-Id, action: upsert}, …]`;
  `redaction` as the second line; a dedicated `browser` pipeline so browser data can be tail-sampled/capped
  separately from server data.
- This keeps the browser 100% backend-agnostic (it never sees vendor URLs) and closes G2 without opening the
  collector to the internet.

---

## 7. Alerting + dashboards-as-code per backend

| Backend | Dashboards as code | Alert rules as code | Portability of our artefacts |
|---|---|---|---|
| **POC / any Grafana** (OSS, Grafana Cloud, AMG, Azure Managed Grafana) | File provisioning (`provisioning/dashboards/*.yaml` + JSON — the POC already does this), **Grafana Terraform provider** (`grafana_dashboard`, `grafana_folder`, `grafana_data_source`; works against OSS, Grafana Cloud, AMG and Azure Managed Grafana with a service-account token) ([provider](https://registry.terraform.io/providers/grafana/grafana/latest/docs)); Grafonnet / Foundation SDK generate the JSON if we want templating ([as-code overview](https://grafana.com/docs/grafana-cloud/developer-resources/infrastructure-as-code/)) | Grafana unified alerting via `grafana_rule_group`, `grafana_contact_point`, `grafana_notification_policy`, `grafana_mute_timing`; **Prometheus rule YAML imports directly** (`mimirtool rules load` against `<grafana>/api/convert/`, or the UI import) ([Grafana Cloud import](https://grafana.com/docs/grafana-cloud/observe-and-act/alert-and-measure-reliability/alerting/alerting-rules/alerting-migration/)) | JSON dashboards + Prometheus rule files port **unchanged** between POC and Grafana Cloud; also to AMG/Azure Managed Grafana **only** for panels whose datasource is Prometheus-compatible |
| **AWS CloudWatch** | `aws_cloudwatch_dashboard` (JSON body, CloudWatch widget schema — different from Grafana JSON) | `aws_cloudwatch_metric_alarm` (classic), PromQL alarms exist since 2026-06 ([PromQL alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-promql.html)) but Terraform support was still an open request as of 2026-04 ([issue #47446](https://github.com/hashicorp/terraform-provider-aws/issues/47446)) — verify provider version at implementation time; Application Signals SLOs as resources | Nothing ports verbatim: rewrite queries in CloudWatch PromQL dialect (`@resource.` labels, dotted names) and Logs Insights; or keep Grafana (AMG) as the UI and re-point panels at the CloudWatch/X-Ray data sources (still a rewrite of every query) |
| **Azure Monitor** | "Azure Monitor dashboards with Grafana" are ARM/Bicep resources (free, portal); Azure Managed Grafana via the Grafana Terraform provider | `azurerm_monitor_alert_prometheus_rule_group` (**PromQL rules — port from Prometheus rule files**) ([registry](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/monitor_alert_prometheus_rule_group)); `azurerm_monitor_scheduled_query_rules_alert_v2` for KQL log/trace alerts | Metric panels + PromQL alerts probably port (naming to verify, §2.4); log/trace panels and alerts are KQL rewrites |
| **New Relic / Datadog / Honeycomb** | Vendor Terraform providers (`newrelic_one_dashboard`, `datadog_dashboard_json`, `honeycomb_board`) | vendor alert resources (NRQL conditions, Datadog monitors, Honeycomb triggers/SLOs) | Full rewrite |

Design rule that maximises portability: **keep alerting on metrics, expressed as Prometheus rule YAML.**
That artefact is native in the POC, imports into Grafana Cloud, is a first-class Azure resource, and is a
mechanical dialect translation on CloudWatch. Log-derived alerts (LogQL / Logs Insights / KQL) are never
portable — derive a counter in the app instead (e.g. `llm.errors` rather than "count error logs").

---

## 8. Comparison matrix

Legend: ✅ yes · ◐ partial / with caveats · ❌ no. "Dashboards port" = our existing Grafana JSON
(PromQL/LogQL/TraceQL) works after a datasource swap.

| Backend | OTLP logs native | OTLP metrics native | OTLP traces native | Dashboards port unchanged | Browser RUM | Alerting | Managed-ness | Pricing model | Multi-cloud | Lock-in |
|---|---|---|---|---|---|---|---|---|---|---|
| **POC: OSS Loki/Prom/Tempo/Grafana on one EC2** | ✅ Loki `/otlp` | ✅ (collector `prometheus` exporter / remote-write) | ✅ Tempo | ✅ (baseline) | ◐ via our proxy → OTLP; Faro receiver alpha | Prometheus rules + Grafana unified alerting | ❌ self-run (the burden the owner wants out of) | EC2 + disk only | ✅ runs anywhere | none |
| **AWS CloudWatch** (Logs/OTel-metrics/X-Ray+Transaction Search, Application Signals; optional AMG) | ✅ GA (SigV4 or bearer; log group via header) | ✅ GA 2026-06 (SigV4/bearer; PromQL, per-GB) | ✅ GA (SigV4 only; needs Transaction Search on) | ❌ metric names/labels differ (`http.x` + `@resource.`), LogQL/TraceQL gone | ◐ CloudWatch RUM is a separate SDK (mobile OTLP endpoint only); browser stays OTLP via our proxy | CloudWatch alarms (classic + PromQL), SLOs; Terraform lagging for PromQL alarms | ✅ fully managed, in the client's account | logs $0.50/GB, OTel metrics $0.50/GB, spans $0.35/GB, App Signals per-request, AMG per-user | ❌ AWS only | medium: data model + query dialects; app code untouched |
| **Azure Monitor** (App Insights w/ OTLP, Log Analytics, Azure Monitor workspace; portal Grafana free) | ✅ GA (collector path) HTTP/protobuf | ✅ GA — **delta temporality + exp. histograms required** | ✅ GA | ◐ metrics PromQL likely (naming unverified); logs/traces KQL ❌ | ◐ App Insights JS SDK (proprietary) or our proxy → OTLP logs/traces | Prometheus rule groups (PromQL ✅ portable) + KQL scheduled queries | ✅ fully managed, in the client's tenant | logs ~$2.30/GB, Prometheus ~$0.16/10M samples, Managed Grafana $6/user (+~$31 instance) | ❌ Azure only | medium: KQL + DCR plumbing; app code untouched |
| **Grafana Cloud** | ✅ (OTLP gateway → Loki) | ✅ (→ Mimir) | ✅ (→ Tempo) | ✅ **1:1** | ✅ Faro / Frontend Observability (50k sessions free) or our proxy → OTLP | Prometheus rules import + unified alerting; Terraform provider | ✅ SaaS | free tier generous; Pro $19 + $6.50/1k series + ~$0.50/GB + $8/user | ✅ any cloud | low: OSS-compatible; can self-host the same stack (the POC) |
| **New Relic** | ✅ | ✅ (delta preferred) | ✅ | ❌ NRQL | ◐ proprietary browser agent (good), or our proxy → OTLP | NRQL conditions; Terraform provider | ✅ SaaS | 100 GB free; $0.40–0.60/GB; users $49–$349+ | ✅ | medium: NRQL + user pricing |
| **Datadog** | ◐ via agent / collector `datadog` exporter (beta) | ◐ same | ◐ same | ❌ | ◐ Datadog RUM SDK ($0.15 + $3.00/1k sessions) | monitors; Terraform provider | ✅ SaaS | per-host APM $31–40 + logs $0.10/GB + $1.70/M indexed | ✅ | high: agent-centric, host pricing |
| **Honeycomb** | ✅ | ✅ | ✅ | ❌ | ◐ frontend observability included; OTel-web native | triggers/SLOs; Terraform provider | ✅ SaaS | 20 M events free; Pro $150/mo | ✅ | medium: event model |

## 9. Recommendation (10 lines)

1. **Contract**: apps speak OTLP/HTTP-protobuf to one gateway collector; SDK config is the standard `OTEL_*` env set; resource identity = `service.namespace=flynapse` + `service.name` + `deployment.environment.name`; browser exports only to a same-origin proxy. Nothing else in app code is allowed to know the backend.
2. **(a) POC on one EC2 box**: keep the OSS stack (Loki/Prometheus/Tempo/Grafana) exactly as the swap baseline — `base.yaml` + `backend-oss.yaml`; drop the `debug` exporters; add the browser proxy; provision dashboards/rules from files. It doubles as the local dev stack.
3. **(b) Production in a client's AWS account**: **CloudWatch native** (Logs OTLP + OTel-metrics OTLP + X-Ray OTLP with Transaction Search + Application Signals), `sigv4auth` on the instance/task role, PromQL alarms, CloudWatch dashboards; AMG only if the client already runs it. Accept the dashboard rewrite — it is the price of "zero extra infrastructure in the client's account", and nothing in the app changes.
4. **(c) Production in a client's Azure account**: **Azure Monitor native** via the GA collector path (`otlphttp` + `azure_auth`, App Insights resource with OTLP support), `cumulativetodelta` in the overlay, portal "dashboards with Grafana" (free) for metrics, KQL for logs/traces, Prometheus rule groups for alerts.
5. **(d) Production in Flynapse's own account**: **Grafana Cloud** (start on Free, Pro when series/GB exceed the allowance). It is the only managed backend where the POC's dashboards, rules, and label semantics carry over unchanged, it is multi-cloud, and it removes the self-run burden without a rewrite.
6. Treat New Relic / Honeycomb as viable **fallbacks** if a client mandates them (both are OTLP-native, config-only swaps); treat Datadog as "only if the client already pays for it".
7. Keep **alerts as Prometheus rule YAML** and **dashboards as Grafana JSON** in the repo; maintain CloudWatch/Azure translations as separate, generated artefacts rather than forking the app's metric names.
8. Instrumentation work is backend-independent and should land first: pin `opentelemetry-sdk==1.44.0` + contrib `0.65b0`, add fastapi/httpx/aiohttp/asyncpg/psycopg/sqlalchemy/redis/botocore instrumentations, replace the loguru OTLP sink with `LoggingHandler` + JSON stdout, add Next `instrumentation.ts` (OTel JS 2.x upgrade), and the browser proxy route.
9. Cost posture: AWS per-GB meters (logs $0.50, spans $0.35, metrics $0.50) are cheap enough to skip tail sampling at POC/early-prod volumes; Azure's ~$2.30/GB logs (which also bill traces) and Grafana Cloud's per-GB/series meters justify tail sampling + a `filter` on health/debug noise in those overlays.
10. Two things to prove before committing IaC: that Grafana (AMG) can query CloudWatch's PromQL API within its 500-series/7-day limits for our busiest panel, and that Azure's OTLP→Prometheus naming matches ours for one existing panel.

## 10. Open probes / uncertainties (do these before design sign-off)
- CloudWatch Logs OTLP: exact stored field paths for resource/scope attributes (needed for Logs Insights queries and per-tenant filtering).
- CloudWatch OTLP metrics ingestion doc page (`CloudWatch-OTLP-Metrics`) was not fetchable; histogram/temporality handling for the metrics endpoint is inferred from the PromQL doc + limits table (1 MB / 1,000 datapoints / 150 labels per request).
- Azure: Log Analytics table names behind `Microsoft-OTLP-Logs/Traces`; whether the GA covers all regions; whether `azure_auth` + service principal works from a non-Azure POC box (docs say yes, untested).
- Grafana Cloud: OTLP gateway rate limits per stack (docs quote 15 MB/s traces; logs/metrics limits are per-plan).
- Terraform: `aws_cloudwatch_metric_alarm` PromQL criteria support in the provider version we pin.
- Secondary-sourced prices (Azure Log Analytics, Azure Managed Grafana, Datadog RUM) should be re-checked in the respective pricing calculators for the client's region.
