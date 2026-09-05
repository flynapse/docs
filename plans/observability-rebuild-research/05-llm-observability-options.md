# 05 — LLM / agent observability options (research, 2026-09-05)

Lens: what is *different* about observing LLM and agent workloads, what the 2026 ecosystem offers, and what
fits this estate (Claude Agent SDK loop on Bedrock, LangGraph runtime, direct Bedrock/Azure calls, Ollama/vLLM
offline tiers, a durable Postgres cost ledger). Read-only research; every codebase claim carries `path:line`.
Companion to `docs/plans/observability-rebuild-audit.md` (§2, G6, G8, G9, G16) and the shared brief.

Conventions: web sources are cited inline as `[n]` and listed in §10 with the date I read them (all 2026-09-05)
and the source's own date where it states one. "Not verified" marks a claim I could not confirm from a primary
source today.

## 0. What already exists (the ground the recommendation must fit)

| Thing | Where | State |
|---|---|---|
| OTel bootstrap (TracerProvider + OTLP gRPC span exporter; MeterProvider + periodic OTLP metric exporter; resource `service.name`) | `utils/utils/observability/tracing.py:100-114`, `utils/utils/observability/metrics.py:143-173` | Live; single `OTEL_ENDPOINT` |
| Installed OTel packages (shared `api` venv) | `api/.venv`: `opentelemetry-api/sdk 1.37.0`, `opentelemetry-instrumentation{,-fastapi,-asgi,-logging} 0.58b0`, `opentelemetry-semantic-conventions 0.58b0` | **No** GenAI instrumentor, no OpenInference/OpenLLMetry/Langfuse/Logfire/Phoenix client installed |
| Claude Agent SDK | `claude-agent-sdk 0.2.128` (`pip show`), `anthropic 0.109.2`, `boto3 1.43.86`, `langchain 1.3.18`, `langgraph 1.2.11`, `langsmith 0.11.2` (transitive only) | |
| SDK loop root span + per-tool child spans | `copilot-mro/copilot_mro/app/services/agent_shared/loop_observability.py` (note: the module lives under `agent_shared/`, not `agent_claude/` as the brief says): identity attrs `tenant_id`/`user_id`/`chat_id` unprefixed (`:24-42`), request attrs `sdk.model/department/max_turns/max_budget_usd/has_history/has_memory` (`:45-71`), usage attrs `sdk.num_turns`, `sdk.input_tokens`, `sdk.cache_read_input_tokens`, `sdk.total_cost_usd`, `sdk.direct_cost_usd`, `sdk.embedding_cost_usd`, `sdk.combined_cost_usd`, `sdk.cache_hit_rate`, `sdk.is_error`, `sdk.loop_error` (`:75-136`); tool spans `agent_sdk.tool.<short>` with `tool.name`, `tool.is_error`, `tool.duration_ms`, back-dated through the low-level tracer (`:139-147`, `:208-242`) | Live, exported to Tempo, viewed by nobody (audit G6) |
| Root span opened in the orchestrator | `copilot-mro/copilot_mro/app/services/agent_claude/orchestrator.py:2596-2624` (`tracing.as_current_span("agent_sdk.run_query", ...)` via `get_tracing_service(settings.otel_service_name, settings.otel_env, settings.otel_version)`) | Live |
| `ClaudeAgentOptions(...)` construction | `orchestrator.py:2164-2213` — model, system_prompt, allowed_tools, mcp_servers, strict_mcp_config, agents, skills, hooks, `max_budget_usd`, setting_sources, add_dirs, permission_mode, max_turns, max_buffer_size, include_partial_messages, thinking. **No `env=`** is passed (rg for `OTEL_`, `TRACEPARENT`, `env={` across `agent_claude/*.py` returns nothing) | So the CLI's built-in telemetry is off and cannot be turned on per-call today |
| `ResultMessage` consumption | `orchestrator.py:2574-2588` logs every field; `summarize_usage(result, ..., direct_usage=current_llm_usage_totals())` at `:3071-3080`; `record_turn_usage(...)` awaited via `asyncio.to_thread` at `:3094`; `record_sdk_model_usage(result.model_usage, ...)` at `:3117-3120` | Live |
| Usage summary contract | `agent_shared/loop_controls.py:275-372` — reads `result.usage.{input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}`, `result.total_cost_usd` as `sdk_cost`, folds direct + embedding axes, `combined_cost_usd` at 9 dp, **None propagates** (an unmeasured term makes the sum unmeasured) | Live |
| Ledger writer | `agent_shared/usage_ledger.py:235-345` `record_turn_usage` — refuses with `UNBOUND` and an ERROR log when no `current_db_tenancy()` binding; idempotent on `(tenant_id, block_id)`; `book_turn_on_failure` (`:389`) books the direct/embedding axes when the loop dies before a `ResultMessage` | Live |
| Per-model SDK rows | `agent_shared/model_call_ledger.py:355-420` `record_sdk_model_usage` — one `llm_model_calls` row per model from `ResultMessage.model_usage` (`origin='sdk_loop'`, `outcome='aggregate'`); docstring warns reporting must exclude one of the two origins to avoid double counting | Live |
| Ledger tables | `copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/llm_usage.py:73-129` (fields; `sdk_cost_usd`, `direct_cost_usd`, `embedding_cost_usd`, `total_cost_usd`, `cost_complete`, `direct_unpriced_calls`, token buckets, `cache_hit_rate`, `loop_error`, `is_error`), `"tenancy": "tenant"` (`:131`), CHECK `llm_usage_cost_complete_check` (`:163-167`); `llm_model_calls.py:64-118` (`provider/model/deployment/region`, `cost_source` ∈ provider_reported/versioned_pricing/unavailable, `cost_estimated`, `usage_estimated`, `pricing_version`, `latency_seconds`, `outcome`, `graph_node`), `"tenancy": "tenant"` (`:121`) | Live, RLS-tenanted, complete |
| Direct-call metrics + Bedrock rate card | `utils/utils/llm.py:351-452` (`llm_tokens_total`, `llm_tokens_per_request`, `llm_requests_total`, `llm_request_duration`), `:1180-1300` (`embedding_requests_total`, `embedding_tokens_total`, `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`), `compute_bedrock_cost` at `:637` with a version-aware rate card (`:550-636`; comment `:560` says the Marketplace agreement, not list price, governs what is paid) | Live for direct calls only (audit G8) |
| `RuntimeTelemetry` (17 instruments) | `agent_shared/telemetry.py:18-131`; imported only by `tests/unit/agent_shared/test_telemetry.py` (rg); `lang_agent/runtime_factory.py` has no telemetry/tracer/meter reference (rg empty); `copilot-mro/docs/plans/s2-cost-parity.md:134` names `RuntimeTelemetry.record_model_usage` as the intended (unwired) third ledger sink | Dead code (audit G9) |
| LangGraph runtime OTel | `lang_agent/*.py`: rg for `callbacks|BaseCallbackHandler|opentelemetry|tracer` returns nothing | **Zero** spans/metrics from the lang runtime today |
| Prompt/completion capture | `copilot-mro/copilot_mro/app/services/_debug_dump.py:195-218` (`dump_debug`, gated on `settings.debug`, 3-day retention `:25`); `lang_agent/debug_dump.py:1-30` mirrors it and reuses `agent_shared/_debug_hooks.redact_sensitive` (`:28`, `:59`, `:101`, `:131`) | Filesystem only, dev-gated (audit G16) |
| LangSmith | `api/tests/unit/infra/test_no_langsmith_integration.py:25-37` forbids imports, env vars, callbacks and the `smith.langchain.com` hosts; the file states no rationale. The policy source is `copilot-mro/docs/plans/lang-agent-parallel-runtime-implementation-plan.md:248` — "no direct dependency, import, API key, environment variable, callback, tracing, configuration, trace identity, or **hosted-service traffic**" | Banned; treat "no hosted LangChain traffic" as the reason |
| Offline LLM tiers | vLLM `/metrics` Prometheus scrape stanza `llm-platform/profiles/gpu-prod/prometheus-scrape.yml` (job `gpu-prod-vllm-qwen3-8b-32k`, target `127.0.0.1:8000`); no OTel code in `llm_platform/` (rg hits only `profiles.py`/`certify.py` for "prometheus") | vLLM metrics scrapable; Ollama dev tiers emit nothing |
| Tests/dashboards that pin today's names | `tests/agent_sdk/core/test_agent_sdk_loop_observability.py:61-111` pins every `sdk.*` key; `tests/architecture/agent_runtime/test_agent_shared_rename_checkpoint.py:244-245` pins `agent_sdk.run_query` / `agent_sdk.tool.<name>`; `tests/unit/agent_shared/test_telemetry.py:170-171` pins `agent.model.calls` / `agent.model.cost_usd`; `deployment/observability-local/grafana/dashboards/llm-metrics-dashboard.json:112-588` reads `llm_requests_total`, `llm_request_duration_bucket`, `llm_tokens_total`, `llm_tokens_per_request_bucket` | Any rename has a known re-bank list |
| AWS-native GenAI observability in IaC | `iac/*.tf`: no ADOT, Application Signals, X-Ray or Transaction Search resources (rg); "cloudwatch" only in generic log permissions in `iac/amplify.tf`, `iac/waf.tf`, `iac/gpu-host/iam.tf` | Nothing to build on |

## 1. OpenTelemetry GenAI semantic conventions — status and shape

**Status (2026-09-05): still `Development`; nothing GenAI-specific is Stable.** With semantic-conventions
v1.42.0 (2026-06-12) all `gen_ai.*` content was deprecated in the main repo and moved to the dedicated
`open-telemetry/semantic-conventions-genai` repository, which as of 2026-07-17 had no tagged release and no
schema URL [1][2]. Every convention document I fetched from that repo carries `Status: Development` [3][4][5][6].
Renames worth knowing when reading third-party emitters: `gen_ai.system` → `gen_ai.provider.name` (v1.37.0,
Aug 2025), `gen_ai.usage.prompt_tokens` → `gen_ai.usage.input_tokens` (v1.27.0), per-message events
(`gen_ai.content.prompt`, `gen_ai.choice`, ...) → one `gen_ai.client.inference.operation.details` event plus
structured `gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.system_instructions` (v1.37.0) [2].
Practical rule from the same source: pin instrumentation versions and accept both spellings in queries [2].

### 1.1 Spans [3][5]
- Span name `"{gen_ai.operation.name} {gen_ai.request.model}"`, kind CLIENT for remote inference.
- `gen_ai.operation.name` values: `chat`, `generate_content`, `text_completion`, `embeddings`, `execute_tool`,
  `create_agent`, `invoke_agent`, `retrieval`, `create_memory`/`update_memory`/`delete_memory`.
- Required: `gen_ai.operation.name`, `gen_ai.provider.name` (well-known values include `anthropic`,
  `aws.bedrock`, `azure.ai.openai`, `azure.ai.inference`, `openai`, `deepseek`, `mistral_ai`, ...).
- Conditionally required: `gen_ai.request.model`, `error.type`, `gen_ai.conversation.id` (session/thread id).
- Recommended: `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, **`gen_ai.usage.cache_read.input_tokens`**,
  **`gen_ai.usage.cache_write.input_tokens`**, `gen_ai.response.model`, `gen_ai.response.finish_reasons`, `server.address`.
- Opt-in (flagged "likely to contain sensitive information including user/PII data"): `gen_ai.input.messages`,
  `gen_ai.output.messages`, `gen_ai.system_instructions` — JSON-structured message arrays.
- Agent spans [5]: `create_agent {gen_ai.agent.name}` and `invoke_agent {gen_ai.agent.name}`; kind CLIENT when the
  agent is a remote service, **INTERNAL when the agent runs in-process** (LangChain/CrewAI style); attributes
  `gen_ai.agent.id/name/description/version`, `gen_ai.conversation.id`, `gen_ai.data_source.id`, `gen_ai.usage.*`.
- Tool span [3]: `gen_ai.operation.name = execute_tool`, kind INTERNAL, nested under the inference span or the agent
  span; Required `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type` (well-known value `function`);
  Recommended `gen_ai.tool.description`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` (both content-bearing);
  `error.type` on failure. Nothing MCP-specific in the agent/tool documents I read.

### 1.2 Metrics [4]
| Metric | Instrument | Unit | Required attrs | Note |
|---|---|---|---|---|
| `gen_ai.client.token.usage` | Histogram | `{token}` | `gen_ai.operation.name`, `gen_ai.provider.name`, **`gen_ai.token.type` ∈ {`input`, `output`}** | Buckets 1…67,108,864. **No cache/reasoning token type exists** — cache tokens are span attributes only |
| `gen_ai.client.operation.duration` | Histogram | `s` | same + `error.type` | Buckets 0.01…81.92 s |
| `gen_ai.client.operation.time_to_first_chunk`, `...time_per_output_chunk` | Histogram | `s` | | streaming |
| `gen_ai.server.request.duration`, `gen_ai.server.time_to_first_token`, `gen_ai.server.time_per_output_token` | Histogram | `s` | | for the serving side (vLLM-class) |

**There is no cost metric and no cost span attribute in the conventions** [3][4]. De-facto practice: LiteLLM,
OpenLIT and PostHog emit/read a float span attribute **`gen_ai.usage.cost`** (USD); Langfuse reads it (its own
`langfuse.observation.cost_details` was the buggy path, issue #11030) [7][8]; Opik silently drops it (issue #5620)
[9]; Claude Code uses its own `cost_usd` / `cost_usd_micros` event attributes and a `claude_code.cost.usage`
counter with unit `USD` [10]. Treat `gen_ai.usage.cost` as the interoperable attribute name, and expect it to be
ignored by some backends.

### 1.3 Events and content capture [6][11]
- Event `gen_ai.client.inference.operation.details` carries the same `gen_ai.input.messages` /
  `gen_ai.output.messages` / `gen_ai.system_instructions` structures as log-record attributes; a separate
  `gen_ai.evaluation.result` event exists for eval scores.
- The env-var contract lives in `opentelemetry-util-genai` (the util every official instrumentor uses) [11]:
  - `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` — required to get the v1.37+ shape at all.
  - `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` ∈ `NO_CONTENT` (default) | `SPAN_ONLY` | `EVENT_ONLY` | `SPAN_AND_EVENT`.
  - `OTEL_INSTRUMENTATION_GENAI_EMIT_EVENT` true/false (defaults follow the mode above).
  - Upload hook: `OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK=upload`, `OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH`
    (any fsspec URI, e.g. `s3://…`), `OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT=json|jsonl`,
    `OTEL_INSTRUMENTATION_GENAI_UPLOAD_MAX_QUEUE_SIZE` (20) — offloads message bodies to object storage and leaves a
    reference on the span. This is the official answer to "prompts are too big for span attributes".
- Backends are still catching up with the v1.37 event shape: Langfuse showed null input/output for
  event-based content until PR #13674 (issue opened 2026-03-18, closed) [12].

## 2. Claude Agent SDK / Claude Code built-in telemetry

### 2.1 Mechanism
The Python Agent SDK "does not produce telemetry of its own"; it spawns the Claude Code CLI, which has OTel
built in, and passes configuration through as environment variables [13]. Two facts verified in the installed
SDK (`claude-agent-sdk 0.2.128`):
- `ClaudeAgentOptions.env: dict[str, str]` exists (`api/.venv/lib/python3.11/site-packages/claude_agent_sdk/types.py:1903`)
  and is merged **on top of** the inherited process environment
  (`claude_agent_sdk/_internal/transport/subprocess_cli.py:689-694`). So either a container-level env or a per-call
  `env=` works; per-call lets each `query()` carry its own `OTEL_RESOURCE_ATTRIBUTES` (tenant/user) [13].
- The transport **auto-injects W3C `TRACEPARENT`/`TRACESTATE`** from the active OTel span into the child process
  (`subprocess_cli.py:696-720`), unless the caller set them explicitly in `env`. The CLI honours inbound
  `TRACEPARENT` for SDK / `-p` runs, so its `claude_code.interaction` span nests under our
  `agent_sdk.run_query` span, and its OTLP event records carry our `trace_id`/`span_id` even with no traces
  exporter (CLI ≥ v2.1.212) [10][13]. Today nothing is exported, so this linkage is unused.

Enable switches [10][13]: `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus `OTEL_METRICS_EXPORTER=otlp|prometheus`,
`OTEL_LOGS_EXPORTER=otlp`, `OTEL_TRACES_EXPORTER=otlp` (+ `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, traces are beta);
`OTEL_EXPORTER_OTLP_PROTOCOL` (`grpc` | `http/protobuf` | `http/json`), `OTEL_EXPORTER_OTLP_ENDPOINT`, per-signal
`OTEL_EXPORTER_OTLP_{METRICS,LOGS,TRACES}_{PROTOCOL,ENDPOINT,HEADERS}`, mTLS vars, export intervals
`OTEL_METRIC_EXPORT_INTERVAL` (60000 ms), `OTEL_LOGS_EXPORT_INTERVAL` / `OTEL_TRACES_EXPORT_INTERVAL` (5000 ms),
`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` (default **delta**), `OTEL_SERVICE_NAME` (default `claude-code`),
`OTEL_RESOURCE_ATTRIBUTES`. Traps: never use the `console` exporter under the SDK (stdout is the SDK message channel)
[13]; export errors are silent unless `CLAUDE_CODE_OTEL_DIAG_STDERR=1` (CLI ≥ 2.1.179) and the SDK `stderr`
callback is wired [13]; the CLI batches and its exit flush has a short timeout, so short-lived runs should lower the
intervals [13]; the CLI does **not** forward `OTEL_*` to MCP servers/subprocesses [10] (irrelevant for the in-process
`mro` MCP server, relevant if `playwright` is ever instrumented).

### 2.2 Metrics [10]
Standard attributes on every metric/event: `session.id` (toggle `OTEL_METRICS_INCLUDE_SESSION_ID`, default true),
`app.version` (`OTEL_METRICS_INCLUDE_VERSION`, default false), `app.entrypoint` (`sdk-py` for us; default off),
`organization.id`, `user.account_uuid` / `user.account_id` (`OTEL_METRICS_INCLUDE_ACCOUNT_UUID`, default true),
`user.id` (anonymous id from `~/.claude.json`), `user.email`, `terminal.type`, plus every key from
`OTEL_RESOURCE_ATTRIBUTES` as data-point labels unless `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES=false`.

| Metric | Unit | Attributes |
|---|---|---|
| `claude_code.session.count` | — | `start_type` |
| `claude_code.cost.usage` | USD | `model`, `query_source` (`main`/`subagent`/`auxiliary`), `speed`, `effort`, `agent.name`, `skill.name`, `plugin.name`, `marketplace.name`, `mcp_server.name`, `mcp_tool.name` |
| `claude_code.token.usage` | tokens | `type` ∈ `input`/`output`/`cacheRead`/`cacheCreation`, `model`, `query_source`, ... same attribution set |
| `claude_code.lines_of_code.count`, `.pull_request.count`, `.commit.count`, `.code_edit_tool.decision`, `.active_time.total` | — / s | coding-assistant metrics, noise for us |

Cardinality: with defaults every metric series is split by `session.id` **and** `user.account_uuid`; for a server
that runs one `query()` per chat turn, `session.id` is effectively per-turn — set `OTEL_METRICS_INCLUDE_SESSION_ID=false`
and `OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false` on the metrics path, keep low-cardinality resource attrs
(`deployment.environment`, `service.name`, department), and carry tenant/user on **events/spans**, not metrics [10][13].
When Prometheus is the only exporter the units are stripped, so names become `claude_code_cost_usage_USD_total`-style
only via OTLP → Prometheus, not via the CLI's own Prometheus endpoint [10][14].

### 2.3 Events (OTLP log records) [10]
`claude_code.user_prompt` (`prompt_length`; `prompt` redacted unless `OTEL_LOG_USER_PROMPTS=1`),
`claude_code.assistant_response` (`response` redacted unless `OTEL_LOG_ASSISTANT_RESPONSES=1`),
`claude_code.tool_result` (`tool_name`, `tool_use_id`, `success`, `duration_ms`, `error_type`, `tool_input_size_bytes`,
`tool_result_size_bytes`, `mcp_server_scope`; `tool_parameters`/`tool_input` only with `OTEL_LOG_TOOL_DETAILS=1`),
**`claude_code.api_request`** (`model`, `cost_usd`, `cost_usd_micros`, `duration_ms`, `input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_creation_tokens`, `request_id`, `client_request_id`, `speed`, `effort`, `query_source`,
`agent.name`, `skill.name`, `mcp_server.name`, `mcp_tool.name`), `claude_code.api_error` (`status_code`, `attempt`),
`claude_code.api_refusal`, `claude_code.tool_decision`, `claude_code.permission_mode_changed`, `claude_code.auth`,
`claude_code.mcp_server_connection`, and — only with `OTEL_LOG_RAW_API_BODIES=1|file:<dir>` —
`claude_code.api_request_body` / `claude_code.api_response_body` (full Messages API JSON, inline truncated at
`CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` = 61,440 UTF-16 units, or untruncated on disk with a `body_ref` path;
extended-thinking always redacted). Every event carries `prompt.id`, `event.sequence`, `workspace.host_paths`.
**`api_request` is the per-model-call granularity the ledger lacks** (the ledger books one aggregate per turn per model,
`model_call_ledger.py:362-370`).

### 2.4 Traces (beta) [10][13]
`claude_code.interaction` → `claude_code.llm_request` (`model`, `gen_ai.system`, `gen_ai.request.model`, `ttft_ms`,
`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `request_id`, `gen_ai.response.id`,
`stop_reason`, `gen_ai.response.finish_reasons`, `query_source`, `agent_id`, `parent_agent_id`) and
`claude_code.tool` → `claude_code.tool.blocked_on_user` / `claude_code.tool.execution` (`tool_use_id`,
`gen_ai.tool.call.id`, `success`), `claude_code.hook`. Subagent spans nest under the parent's `claude_code.tool`.
Only a handful of attributes use the `gen_ai.*` spelling (and the deprecated `gen_ai.system`); token counts are
bare `input_tokens` etc. — a backend that keys on `gen_ai.usage.input_tokens` will not price these spans without a
collector transform.

### 2.5 What the SDK returns in-process (already consumed)
`ResultMessage` (`types.py:1226-1258`): `subtype`, `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`,
`session_id`, `stop_reason`, `total_cost_usd`, `usage`, `result`, `structured_output`, `model_usage`,
`permission_denials`, `api_error_status`, `terminal_reason`. `ModelUsage` (`types.py:1200-1224`) per model:
`inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens`, `webSearchRequests`, `costUSD`,
`contextWindow`, `maxOutputTokens`, `canonicalModel`, `provider` (`'bedrock'`, `'firstParty'`, ...).
Per-message `AssistantMessage.usage` + `message_id` exist; the docs say to de-duplicate by message id and that
**per-step `output_tokens` is a placeholder** — read output tokens from the result [15]. `usage` on the result
**excludes subagents**; `total_cost_usd` and `model_usage` include them; on `error_max_budget_usd` the `usage` dict
omits the response that crossed the budget while `total_cost_usd` includes it; a crash may zero everything [15].
The orchestrator already prefers `total_cost_usd`/`model_usage` (`loop_controls.py:334-335`, `orchestrator.py:3117`).

### 2.6 Bedrock and cost reporting
- `total_cost_usd` / `costUSD` are **client-side estimates from a price table bundled at build time** (or a
  `modelPricing` settings table); "Do not bill end users or trigger financial decisions from these fields" [15].
  `costBasis` (`list`/`managed`/`unknown`) needs CLI ≥ 2.1.246; the `inference_geo` 1.1× data-residency multiplier
  needs Python SDK ≥ 0.2.144 (installed: 0.2.128) [15].
- The Bedrock page says nothing about cost accuracy; the SDK simply tags `provider: 'bedrock'` and prices by the
  canonical model at list price [15][16]. `utils/utils/llm.py:560` already records that the Marketplace agreement,
  not list price, governs what this account pays — so the ledger's `sdk_cost_usd` is a list-price estimate and
  `cost_source` for the SDK rows is effectively "provider_reported by a client-side table". Reconciliation to the
  bill happens only through Cost Explorer's per-model services (§4.4).
- Bedrock-specific telemetry gaps: `traceparent` is sent to the model API only when `ANTHROPIC_BASE_URL` is unset
  or points at Anthropic — not to Bedrock [10]; prompt caching on Bedrock is region-dependent ("if cache token
  counts stay at zero, check supported regions") [16]; Claude Code uses the Invoke API, not Converse [16] —
  relevant to which Bedrock instrumentor paths would fire if we ever instrumented the CLI's own HTTP (we cannot; it is
  a Node process).

## 3. LLM trace / eval platforms

Legend for "one-box": can it run inside the POC docker-compose on the single `weaviate_observability` EC2 box
next to Weaviate, otel-collector, Loki, Prometheus, Tempo, Grafana and Postgres.

### 3.1 Langfuse (v3/v4) [17][18][19][20][21]
- **Ingest:** OTLP **traces only** at `/api/public/otel` (`/v1/traces`), HTTP/protobuf and HTTP/JSON, **no gRPC**,
  Basic auth with project-scoped `pk-lf`/`sk-lf`, header `x-langfuse-ingestion-version: 4` for real-time ingest.
  Maps OTel GenAI (`gen_ai.request.model`, `gen_ai.usage.*`, `gen_ai.usage.cost`, `gen_ai.input.messages`/
  `gen_ai.prompt`), OpenInference (`input.value`/`output.value`), OpenLLMetry, MLflow; `langfuse.*` attributes win;
  trace-level `user.id`/`session.id` (or `langfuse.user.id`/`langfuse.session.id`) must be **propagated to every
  span** (recommended: OTel baggage + `BaggageSpanProcessor`). Metadata filterable only on top-level keys
  (`langfuse.trace.metadata.*`). Self-hosted OTLP hang bug reported on v3.120.0 (issue #9900) [21].
- **Self-host:** web + worker + Postgres + **ClickHouse** + Redis/Valkey + S3/MinIO; docker-compose recommended
  4 vCPU / 16 GiB (t3.xlarge), 100 GiB; ClickHouse alone 8 GiB, web and worker 4 GiB each; under-provisioned
  ClickHouse "can crash during background merges" [20]. **One-box: only if the box is upsized; otherwise no.**
  License MIT core; EE key gates organisation-creator controls, instance-management API, project-level RBAC,
  data-retention policies, audit logs, UI customisation [18][19].
- **Managed:** Cloud US/EU/JP/HIPAA regions. Hobby $0 (50k units/mo, 30-day access, 2 users), Core $29 (100k units,
  $8/100k overage, 90 days), Pro $199 (3-year access, data-retention management), Enterprise $2,499 (audit logs,
  SCIM, SLA); SSO enforcement + fine-grained RBAC via a $300/mo Teams add-on [19]. SOC 2 II / ISO 27001 / GDPR.
- **Tenancy:** organisation → projects; every record carries `projectId`; API keys are project-scoped; RBAC per
  project. Tenant isolation therefore means **one Langfuse project (and key pair) per tenant**, or one project per
  environment with `tenant.id` as filterable metadata (no hard isolation). Masking, retention, deletion exist [18].
- **Cost:** infers cost from usage + model price tables, or accepts ingested `gen_ai.usage.cost` [7][17].
- **Evals/annotation:** scores, annotation queues, LLM-as-judge evaluators, datasets, prompt management, playground.

### 3.2 Arize Phoenix [22][23][24]
- **Ingest:** OTLP gRPC `:4317` and HTTP `:6006/v1/traces`; native schema is **OpenInference** (`openinference.span.kind`
  ∈ LLM/TOOL/CHAIN/AGENT/RETRIEVER/EMBEDDING, `llm.*` attributes); `gen_ai.*` spans are handled through a
  translation layer (OpenInferenceSpanProcessor; open RFC #10622 for closer alignment) — expect some GenAI-semconv
  fields not to render until translated [24].
- **Self-host:** **single container** (`arizephoenix/phoenix`), SQLite by default or Postgres ≥ 14 via
  `PHOENIX_SQL_DATABASE_URL`; auth via `PHOENIX_ENABLE_AUTH` + `PHOENIX_SECRET` (OAuth2/LDAP, RBAC);
  retention `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS` (0 = infinite) [23]. Elastic License 2.0, "no license fees, no
  usage limits, no feature gates", air-gapped OK [22]. **One-box: yes** (reuses the existing Postgres).
- **Managed:** Arize AX / Phoenix Cloud (pricing not verified today).
- **Tenancy:** projects + RBAC; same per-tenant-project pattern as Langfuse.
- **Cost:** computed from model price tables on `llm.token_count.*`; no ingest of an arbitrary cost attribute confirmed.
- **Evals/annotation:** evals, datasets, experiments, prompt management, annotations.

### 3.3 OpenLLMetry / Traceloop [25]
- Not a backend — an Apache-2.0 instrumentation set: `opentelemetry-instrumentation-{anthropic,bedrock,openai,
  langchain,...}`, LangGraph, MCP, vector DBs; conventions "now part of OpenTelemetry" (they were the seed of
  `gen_ai.*`); content gated by `TRACELOOP_TRACE_CONTENT`; ships to any OTLP backend (Datadog, Grafana, New Relic,
  SigNoz, ...). Traceloop's hosted platform exists (pricing not researched — it is the least differentiated option).

### 3.4 Pydantic Logfire [26][27]
- **Ingest:** OTel-native SaaS (OTLP); 40+ integrations; LLM instrumentations for the Anthropic/OpenAI SDKs,
  LangChain and Pydantic AI are documented (per the docs index; **not re-verified** this session).
- **Self-host:** Enterprise only (self-hosted / custom retention / SSO / BAA) [27]. **One-box: no.**
- **Managed pricing (effective 2026-01-01):** free 10M spans+logs/mo, $2/M overage; Personal $0 (1 seat, 3 projects),
  Team $49/mo (5 seats, 5 projects), Growth $249/mo (unlimited); retention 30 days (Personal/Team), 90 days (Growth),
  custom on Enterprise [27]. Regions: US and EU (EU not verified today). SQL over traces, dashboards, alerts, evals.

### 3.5 LangSmith — **excluded by policy** (see §0). It would otherwise be the closest fit for the LangGraph runtime;
the ban is enforced at the dependency and config level, so nothing below assumes it.

### 3.6 Braintrust [28][29]
- **Ingest:** OTLP HTTP `https://api.braintrust.dev/otel/v1/traces` (EU: `api-eu`), `Authorization: Bearer`,
  `x-bt-parent: project_id:<id>`; maps `gen_ai.*` (incl. `gen_ai.input.messages`), `braintrust.*`, OpenInference,
  OpenLLMetry, Vercel AI SDK [28].
- **Self-host:** hybrid — data plane (traces, datasets) in your VPC, control plane managed [29]. **One-box: no.**
- **Pricing:** Starter free, 1 GB processed (~1M spans) + 10k scores, 14-day retention; Pro $249/mo, 5 GB, 30 days,
  50k scores [29]. Strong evals/experiments; weakest fit for an OSS-only POC.

### 3.7 Helicone [30][31]
- **Model:** proxy/gateway (`gateway.helicone.ai` + `Helicone-Target-Url`) or async logger; Bedrock is proxied but
  "lacks cost support" for the Bedrock domain [30]. No OTLP ingestion documented [30].
- **Self-host:** docker-compose of web, worker, jawn, Supabase/Postgres, ClickHouse, MinIO [31] — heavier than
  Phoenix, and a proxy in the Bedrock SigV4 path is incompatible with the CLI's Invoke-API streaming contract
  (§2.6) [16]. Free 10k req/mo, 7-day retention; Pro $79/mo [31]. Third-party roundups report a March 2026
  acquisition by Mintlify and "maintenance mode" [31] — **not verified from a primary source**. Not a candidate.

### 3.8 Opik (Comet) [32][33][9]
- **Ingest:** OTLP **HTTP only** (`/api/v1/private/otel/v1/traces`; "gRPC exporter will face errors"), headers
  `Authorization`, `Comet-Workspace`, `projectName` [32]. Drops pre-computed `gen_ai.usage.cost` (issue #5620) [9].
- **Self-host:** Apache 2.0; docker-compose of backend, frontend, MySQL, Redis, **ClickHouse**, ZooKeeper, MinIO
  [33]. **One-box: marginal** (ClickHouse again). Cloud free 25k spans/mo, 10 users, 60-day retention; Pro $19/mo
  for 100k spans, $5/100k extra [33]. Evals, datasets, experiments, LLM-judge metrics.

### 3.9 "Plain Grafana" — is a dedicated LLM tool needed at all? [34][35][36]
- Grafana Cloud ships an "AI Observability" solution (GenAI Observability dashboards for requests, cost, tokens,
  performance) fed by OpenLIT's `gen_ai.*` metrics/traces [34][35]. For **Grafana OSS** the same OpenLIT dashboards
  are importable and run on self-hosted Prometheus + Tempo [36]; OpenLIT "emits the official gen_ai.* semantic
  conventions plus a few vendor extensions … such as cost in USD" [36]. TraceQL filters on `gen_ai.*` attributes
  work in Tempo today.
- What Tempo/Grafana (or CloudWatch Logs Insights) do adequately: token/latency/error/cost time series per model,
  provider, department, tenant; per-turn trace waterfalls (turn → tool → subagent); span-metrics-derived RED.
- What they do **not** do: render prompt/completion transcripts side by side, diff prompt versions, run or store
  evaluations/annotations, group by conversation. If the team wants those, one LLM tool is needed; if it only
  wants ops + cost, Grafana on `gen_ai.*` metrics + the Postgres ledger is sufficient and adds no container.

## 4. AWS-native GenAI observability

### 4.1 CloudWatch "Generative AI observability" [37][38][39][40]
- Preview 2025-07, GA 2025-10 [38]; regions us-east-1/2, us-west-2, eu-central-1, eu-west-1, ap-south-1,
  ap-northeast-1, ap-southeast-1/2 [38] (ap-south-1 = the Bedrock region this account forces via the `global.`
  profile, see memory).
- Two views: **Model Invocations** (invocation count, latency, token counts by model/day, requests bucketed by
  input tokens, throttles, errors, and a per-`Request ID` drill-down showing the input/output bodies) — it
  **requires Bedrock model invocation logging delivered to CloudWatch Logs** [40]; and **Agents** (AgentCore
  primitives, or any self-hosted agent that emits GenAI-semconv spans through the ADOT SDK) [37][39].
- Self-hosted agent path (our case) [39]: `pip install aws-opentelemetry-distro>=0.10.0` (≥ 0.18.0 to route spans
  into your own log group), run under `opentelemetry-instrument`, env `AGENT_OBSERVABILITY_ENABLED=true`,
  `OTEL_PYTHON_DISTRO=aws_distro`, `OTEL_PYTHON_CONFIGURATOR=aws_configurator`,
  `OTEL_RESOURCE_ATTRIBUTES=service.name=<agent>,aws.log.group.names=/aws/bedrock-agentcore/runtimes/<id>`,
  `OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=…,x-aws-log-stream=runtime-logs,x-aws-metric-namespace=…`,
  `OTEL_EXPORTER_OTLP_TRACES_HEADERS=x-aws-log-group=…,x-aws-log-stream=spans` (optional),
  `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_TRACES_EXPORTER=otlp`; **CloudWatch Transaction Search must be
  enabled** (spans land in the `aws/spans` log group; X-Ray needs a resource policy); session via OTel baggage key
  `session.id`. Supported instrumentation libraries: OpenInference, OpenLLMetry, OpenLIT, Traceloop [39].
  **"The ADOT Collector is not supported for agent observability"** — the ADOT SDK or Lambda layer must export
  directly [39]. Escape hatch `DISABLE_ADOT_OBSERVABILITY=true` [39].
- Consequence for this estate: the LangGraph runtime can populate the Agents view via OpenInference-langchain +
  ADOT; the **Claude Agent SDK loop cannot** (the model calls happen inside the Node CLI, outside any Python
  instrumentor) — its `claude_code.*` spans still reach CloudWatch through the generic OTLP traces endpoint and
  Transaction Search, but not the curated GenAI views unless a collector transform rewrites them to `gen_ai.*`.
- Generic OTLP endpoints (no collector required, HTTP only, SigV4 or bearer token) [41]: traces
  `https://xray.{region}.amazonaws.com/v1/traces` (SigV4 only; 5 MB/req, 10,000 spans, **200 KB per span**, 16 KB
  resource+scope), logs `https://logs.{region}.amazonaws.com/v1/logs` (needs `x-aws-log-group`/`x-aws-log-stream`;
  1 MB/req, 1 MB per event, larger fields spill to "Large Log Objects" in nine regions), metrics
  `https://monitoring.{region}.amazonaws.com/v1/metrics` (150 labels, 40 KB metadata per data point; reported as public
  preview from 2026-04-02 [42] — **not verified against the AWS page**, which does not state a status). A collector
  needs `sigv4authextension` [41]. Pricing (third-party summaries of the AWS page, 2026-05/06 [43]): Application
  Signals with Transaction Search $0.35/GB ingested after a 3-month/100 GB trial; spans indexed as X-Ray traces
  $0.75/M after the first 1 %; "signals" tiered from $1.50/M.

### 4.2 Bedrock model invocation logging [44][45]
- Account+Region-wide switch (`PutModelInvocationLoggingConfiguration`), **not per application**; captures every
  `InvokeModel[WithResponseStream]` / `Converse[Stream]` on `bedrock-runtime` (not `bedrock-mantle`) with full
  request/response JSON up to 100 KB inline, larger bodies and images to S3; destinations CloudWatch Logs and/or S3
  (same account+region), KMS supported; record fields `requestId`, `operation`, `modelId` (model id or inference
  profile id), `identity.arn`, `requestMetadata`, `input.inputTokenCount`, `output.outputTokenCount` [44].
- **Per-request metadata tagging** [45]: `X-Amzn-Bedrock-Request-Metadata` header (InvokeModel) or
  `requestMetadata` body (Converse), ≤ 16 entries, ≤ 256 chars each, **lands only in invocation logs**, never in
  Cost Explorer/CUR; AWS's own guidance is to compute per-prompt cost from the logged token counts × the rate card
  (an estimate, "you maintain the rate card") and reconcile against CUR at model/usage-type/day grain. The Claude Code
  CLI exposes no hook to add this header (only `ANTHROPIC_CUSTOM_HEADERS`, which is how guardrail headers are set
  [16]) — feasible but untested for tenant tags; the direct `boto3` path (`utils/utils/llm.py`) can set
  `requestMetadata` trivially.
- This is the only AWS-side place where **prompt bodies** exist. Enabling it in production means every tenant's
  prompts sit in one log group/bucket under the account's KMS key with a single retention — tenant isolation would
  have to be re-imposed by S3 prefix + Athena, and CloudWatch data-protection masking policies are the only redaction.

### 4.3 Bedrock CloudWatch metrics [46]
Namespace `AWS/Bedrock`, dimension **`ModelId` only** (plus `ModelId+ImageSize+BucketedStepSize` for images):
`Invocations`, `InvocationLatency`, `InvocationClientErrors`, `InvocationServerErrors`, `InvocationThrottles`,
`InputTokenCount`, `OutputTokenCount`, `CacheReadInputTokens`, `CacheWriteInputTokens`, `TimeToFirstToken`,
`EstimatedTPMQuotaUsage`, `OutputImageCount`, `LegacyModelInvocations`, plus delivery success/failure metrics for
invocation logging. **No tenant, application or caller dimension.** An application inference profile ARN is passed
as `modelId`, so it should surface as the `ModelId` dimension value (not verified). These are the right source for
throttle/TTFT/quota alarms, not for attribution.

### 4.4 Cost attribution on the bill [47][48][49]
- **Cost Explorer trap** (memory note, verified 2026-07-16 on this account): Bedrock inference bills under per-model
  services named `Claude X (Amazon Bedrock Edition)`, not "Amazon Bedrock"; use a Cost Category with Service
  ENDS_WITH `(Amazon Bedrock Edition)` and filter `RECORD_TYPE=Usage` to see gross spend while credits absorb it.
- **Application inference profiles (AIPs)** [47]: per-model resources with cost-allocation tags that flow to Cost
  Explorer and CUR at usage-type/day grain; one profile per (model, tag-set) → proliferates across model rotations;
  the CLI supports pinning per-model AIP ARNs via `modelOverrides` or `ANTHROPIC_MODEL=arn:…application-inference-profile/…`
  [16], so **per-tenant AIPs are possible for the SDK loop** but mean N tenants × M models profiles.
- **Projects/Workspaces** [48]: cost tags for the `bedrock-mantle` Responses/Chat Completions endpoint only — not
  usable with the Invoke API the CLI uses [16][48].
- **IAM principal attribution**: `identity.arn` in invocation logs [44]; App Runner runs one role, so useless per tenant.
- Net: the bill can be split per model (always) and per tenant only via AIPs; per-turn/per-user attribution is
  **only** possible from our own ledger (or invocation logs + rate card, which is the same estimate AWS tells you to
  make). This is the strongest argument for keeping `llm_usage` as the system of record.

## 5. Instrumentation options for Bedrock + Claude Agent SDK + LangGraph (+ Azure OpenAI, Ollama/vLLM)

### 5.1 Inventory (2026-09) [50][51][52][25]
| Layer | Package | Emits | State |
|---|---|---|---|
| Anthropic SDK (Python) | `opentelemetry-instrumentation-genai-anthropic` 1.1b1 (needs `anthropic ≥ 0.51` — installed 0.109.2) | `gen_ai.*` spans, metrics, events via util-genai | released, Development [50] |
| LangChain/LangGraph | `opentelemetry-instrumentation-genai-langchain` 1.1b1 (`langchain ≥ 0.3.21,<2` — installed 1.3.18) | chat/tool/chain spans, `gen_ai.client.*` metrics | released, Development [50] |
| OpenAI/Azure OpenAI SDK | `opentelemetry-instrumentation-genai-openai` 1.1b0 (contrib `openai-v2` too) | same | released [50][51] |
| Bedrock (boto3) | contrib `opentelemetry-instrumentation-botocore` Bedrock extension: Converse/ConverseStream fully; InvokeModel for `anthropic.claude`, `amazon.titan`, `amazon.nova`, `cohere.*`, `meta.llama`, `mistral`; sets `gen_ai.system=aws.bedrock` (old spelling), `gen_ai.request.model/max_tokens/temperature/top_p/stop_sequences`, `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens/output_tokens` (**no cache tokens**), records `gen_ai.client.operation.duration` (s) + `gen_ai.client.token.usage` ({token}), choice events gated by `genai_capture_message_content()`; **botocore only, no aiobotocore** [52][53] | released |
| Bedrock (new-gen) | `opentelemetry-instrumentation-genai-bedrock` (`boto3 ≥ 1.40.46`) | | **unreleased skeleton** [50] |
| Claude Agent SDK | `opentelemetry-instrumentation-genai-claude-agent-sdk` (`claude-agent-sdk ≥ 0.1.14`) | | **unreleased skeleton** [50] — and would duplicate the CLI's own spans |
| OpenInference | `openinference-instrumentation-langchain` (+ anthropic, bedrock, openai) | OpenInference `llm.*` + span kinds; "follow OTel GenAI where applicable" | mature; what Phoenix and CloudWatch-ADOT expect [24][39][54] |
| OpenLLMetry | `opentelemetry-instrumentation-{anthropic,bedrock,langchain}` (LangGraph, MCP) | `gen_ai.*` (+ legacy `llm.*`), `TRACELOOP_TRACE_CONTENT` | mature [25] |
| Serving side | vLLM `--otlp-traces-endpoint` + Prometheus `/metrics` (`vllm:*`) [55]; Ollama: no native OTel/metrics (OpenLLMetry has an Ollama client instrumentor) | | vLLM scrape already declared in `llm-platform/profiles/gpu-prod/prometheus-scrape.yml` |
| Managed backends that read `gen_ai.*` natively | CloudWatch GenAI observability [37], Azure Monitor Application Insights "Agents view" (GA 2026-03, keyed on `gen_ai.agent.name`; also ingests Claude Code OTLP) [56], New Relic AI Monitoring [57], Grafana Cloud AI Observability [34], Langfuse/Braintrust/Logfire (§3) | | Constraint 2 is satisfiable by any of them if we emit `gen_ai.*` |

### 5.2 Which layer sees which call — and the double-count map
| Model call path | Who can observe it | Overlap risk |
|---|---|---|
| **SDK loop** (Claude via Bedrock, inside the Node CLI) | (a) CLI built-in telemetry (`claude_code.api_request` per call; metrics; beta spans); (b) our `agent_sdk.run_query` root span with `sdk.*` turn aggregates; (c) ledger `llm_usage` + `llm_model_calls(origin=sdk_loop)`; (d) Bedrock invocation logs / `AWS/Bedrock` metrics | No Python instrumentor sees these calls (not boto3, not `anthropic`) — so botocore/anthropic instrumentors **cannot** double count them. (a)+(b)+(c) are different grains (call / turn / durable turn) — fine if dashboards pick one per question. Skip the claude-agent-sdk instrumentor (skeleton, and it would re-emit (a)). |
| **Direct Bedrock calls** (`utils/utils/llm.py` classifiers, synthesis, judge, gates; boto3) | (e) botocore Bedrock extension; (f) existing `llm_*` metrics in `utils/llm.py`; (g) governed-gateway rows in `llm_model_calls` (lang runtime) or the request accumulator (Claude runtime); (h) `RuntimeTelemetry.record_model_usage` (unwired) | (e) and (f) would both count every call → **choose one**: either adopt (e) and retire `llm_requests_total`/`llm_tokens_total`, or wire (h) from the ledger sink and never install (e). (e) lacks cache tokens and is sync-only; the ledger sink has cache/reasoning tokens, `cost_source`, `usage_estimated` → prefer (h). |
| **LangGraph runtime** (`ChatBedrockConverse` / `AzureChatOpenAI` via `langchain-aws` / `langchain-openai`) | (i) `opentelemetry-instrumentation-genai-langchain` or `openinference-instrumentation-langchain` (callback-level: chat + tool + chain spans); (e) botocore extension underneath (Converse path — fully supported); (j) `openai` instrumentor underneath for Azure; (g) gateway ledger rows | (i)+(e) or (i)+(j) emit two spans and two token histograms per call. Pick **(i) for spans/structure** (it is the only thing that sees graph nodes and tools) and **(h)/(g) for money**; do not install (e)/(j). |
| **Embeddings** (Azure OpenAI) | `embedding_*` metrics in `utils/llm.py:1180-1300`; ledger `embedding_*` columns | Unaffected unless the openai instrumentor is installed. |
| **Offline tiers** (Ollama/vLLM via `openai_compatible_oss` profile) | gateway ledger rows (`deployment` = tier since P3.2, `llm_model_calls.py:83`); vLLM `/metrics`; vLLM OTLP traces | Server-side metrics complement, don't duplicate, client-side rows. |

Fit verdict for this estate: **no provider-level auto-instrumentor is worth installing**; the ledger already sees
every direct call with better fields than any instrumentor, and the SDK loop is invisible to all of them. The two
things that add information are the **CLI's own per-request events** (SDK loop granularity + cache tokens + subagent
attribution) and a **LangChain-level instrumentor for the lang runtime** (graph/tool structure), both emitting to the
same collector under the trace the orchestrator already opens.

## 6. Multi-tenant and compliance considerations for prompt/completion capture

### 6.1 What is special about LLM content
Prompt bodies are large (a cached system prompt + history + tool results: tens to hundreds of KB per call; the CLI's
inline cap is 60 KB and CloudWatch rejects spans over 200 KB [10][41]), they contain the tenant's documents and the
user's words verbatim, and their value is *per conversation*, not per time series. That rules out span attributes as
the primary carrier and makes "which store, keyed how, purged when" the real question.

### 6.2 The three candidate homes
| Home | Tenant isolation | Redaction | Retention | Size | Query/eval UX | Backend-swap cost (Constraint 3) |
|---|---|---|---|---|---|---|
| **Postgres ledger extension** (new relation keyed `(tenant_id, block_id[, call_id])`, bodies in `jsonb`/`text` or an S3 object key) | **Inherited**: the tenancy builder injects `tenant_id` + RLS exactly as for `llm_usage` (`llm_usage.py:131`); the same `current_db_tenancy()` gate that refuses unbound ledger writes (`usage_ledger.py:257-272`) applies | Apply `redact_sensitive` (`agent_shared/_debug_hooks`) at write, as `lang_agent/debug_dump.py:59` already does | A dated column + the same day-bucket index discipline; a purge job per tenant policy; `settings.debug`-style flag becomes a per-tenant/per-env column | TOAST handles MBs; or store an S3 key (KMS, per-tenant prefix) and keep only metadata in Postgres | SQL joins to `llm_usage`/`chat_blocks`; feeds the settings dashboard the owner wants on a **datastore** (brief §"goal"); no annotation UI | **Zero** — app-owned table; any LLM tool can be fed from it later |
| **LLM platform** (Langfuse/Phoenix project) | Project-per-tenant (N key pairs, N projects) or one project + `tenant.id` metadata (soft) [18][23] | Platform masking (Langfuse) or pre-redact in code | Platform policy (Langfuse: EE/Pro; Phoenix: `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS`) | Native | **Best**: transcript view, diff, scores, annotation queues, datasets | Vendor attribute names leak into code unless a collector `transform` adds them; switching tools re-maps |
| **Log backend** (Loki / CloudWatch Logs via OTLP events such as `claude_code.api_request_body` or `gen_ai.client.inference.operation.details`) | Labels only; today's Loki path filters tenant **after** the fetch (audit G10); CloudWatch would need a log group per tenant | CloudWatch data-protection masking; Loki none | Per stream/log group, coarse | 1 MB per event cap; LLOs in some regions [41] | grep-grade; no eval | Neutral, but repeats the Constraint-1/2 problem the rebuild exists to solve (product data in the log store, audit G11) |

### 6.3 Argument
1. The estate already has the durable, tenant-scoped, idempotent, NULL-honest per-turn record (`llm_usage`) with a
   completeness certificate and a per-attempt record (`llm_model_calls`) — content capture is a **third column
   family of the same fact** (what was said in the turn whose cost this row books), so it belongs next to it, keyed
   the same way. Putting it anywhere else creates a second tenant boundary to defend and a second retention clock.
2. Constraint 3 (app code must not change when the backend changes) is met only by the ledger option: the write
   site is application code and the export to any LLM tool is a downstream copy.
3. The LLM-tool UX (transcript view, evals, annotation) is real value but is a **consumer** of captured content, not
   its system of record. Feed it a copy — sampled, per-environment, opt-in per tenant — through OTLP from the same
   write site (the util-genai upload-hook pattern, `s3://` bodies + span reference, is the standard-conformant way
   to keep bodies out of spans [11]).
4. The log backend should carry **structural** events only (`claude_code.api_request`, `tool_result`, our own
   turn/tool events) — never bodies. `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_CONTENT`,
   `OTEL_LOG_RAW_API_BODIES` stay unset in shared environments; `OTEL_LOG_RAW_API_BODIES=file:<dir>` is a good
   **dev-only** replacement for `debug_dumps/` because it captures the CLI's exact request (system prompt, cache
   breakpoints, tool schemas) which `dump_debug` cannot see.
5. Bedrock invocation logging is a fourth, account-wide copy with no tenant boundary; leave it **off** in production
   (or on → S3 + KMS + short lifecycle, purely for incident forensics), and never rely on it for product features.

### 6.4 Policy sketch (input to the plan, not a decision)
- Capture flag: per environment default (dev on, staging on, prod **off**), overridable per tenant (contractual
  consent), stored where the tenancy binding is resolved, read at the ledger write site.
- Always redact before persisting (`redact_sensitive`), record the redaction version, store bodies with
  `content_bytes`, `truncated`, `sha256` so a later eval run can prove what it evaluated.
- Retention: 7–30 days by default, tenant-overridable; purge job keyed on the same day bucket as spend.
- Access: the same RBAC that guards `chat_blocks`; export to an LLM tool only from a sampled, redacted view.

## 7. Reconciling with what exists

### 7.1 `RuntimeTelemetry` instruments and `loop_observability` attributes → GenAI semconv
Guiding rule: adopt `gen_ai.*` names **where a convention exists and carries the same meaning**, keep app-namespaced
names for everything the conventions do not model (turn outcome, cost, tool attempts, subagents), and never put
custom attributes under `gen_ai.*`. Rename at the emitter once; every backend then works unchanged (Constraint 3),
and vendor aliases (`langfuse.session.id`, `user.id`, `session.id`) are added by a collector `transform` processor,
not by application code.

| Today (`agent_shared/telemetry.py` / `loop_observability.py`) | Proposed | Why |
|---|---|---|
| span `agent.turn` {`agent.runtime`, `agent.department`} (`telemetry.py:50-62`) and span `agent_sdk.run_query` {`sdk.model`, `sdk.department`, `sdk.max_turns`, `sdk.max_budget_usd`, `sdk.has_history`, `sdk.has_memory`, `tenant_id`, `user_id`, `chat_id`} (`loop_observability.py:45-71`) | **one** `invoke_agent <runtime>` span, kind INTERNAL, `gen_ai.operation.name=invoke_agent`, `gen_ai.provider.name` (`anthropic` for the SDK loop; `aws.bedrock`/`azure.ai.openai`/custom for lang), `gen_ai.agent.name=<runtime>` (`claude`/`lang`), `gen_ai.request.model`, `gen_ai.conversation.id=<chat_id>`; keep `agent.department`, `agent.max_turns`, `agent.max_budget_usd`, `agent.has_history`, `agent.has_memory`; identity as `tenant.id`, `enduser.id` (stable OTel attr) with `chat_id` retained as `gen_ai.conversation.id` | Both runtimes get the same root span; agent semconv exists [5] |
| usage attrs `sdk.input_tokens`, `sdk.output_tokens`, `sdk.cache_read_input_tokens`, `sdk.cache_creation_input_tokens`, `sdk.num_turns`, `sdk.cache_hit_rate`, `sdk.is_error`, `sdk.loop_error`, `sdk.subtype` (`:75-136`) | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`; keep `agent.turns`, `agent.cache_hit_rate`, `agent.loop_error`, `agent.subtype`; `error.type` on failure | Direct 1:1 with recommended span attrs [3] |
| cost attrs `sdk.total_cost_usd`, `sdk.direct_cost_usd`, `sdk.embedding_cost_usd`, `sdk.combined_cost_usd` (`:101-125`) | keep all four under `agent.cost.{sdk,direct,embedding,combined}_usd` **and** stamp `gen_ai.usage.cost=<combined>` | No convention; `gen_ai.usage.cost` is what Langfuse/PostHog/OpenLIT read [7][36] |
| span `agent_sdk.tool.<name>` {`tool.name`, `tool.is_error`, `tool.duration_ms`} (`:139-147`, `:208-242`) | `execute_tool <name>`, INTERNAL, `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id=<tool_use_id>`, `gen_ai.tool.type=function`, `error.type`; drop `tool.duration_ms` (span duration) | Tool span convention exists [3]; `tool_use_id` is already tracked by `ToolSpanTracker` (`:150-192`) but not stamped |
| counters `agent.tool.calls`, `agent.tool.attempts` {`tool.capability_id`, `tool.name`, `tool.outcome`, `tool.error_code`, `tool.state_committed`} (`telemetry.py:104-115`) | keep names; add `gen_ai.tool.name` alias of `tool.name` | No tool metric in semconv; `ToolOperationRecord` (`dispatcher.py:86-97`) is content-free by contract — the right source |
| counters `agent.model.calls`, `agent.model.{input,output,reasoning,cache_read,cache_write,tool_search_overhead}_tokens`, histogram `agent.model.latency_seconds` {`model.role`, `model.purpose`, `model.profile`, `model.provider`, `model.outcome`, `model.cost_source`, `model.graph_node`} (`telemetry.py:80-102`) | `gen_ai.client.operation.duration` (s) and `gen_ai.client.token.usage` ({token}) with `gen_ai.operation.name=chat|embeddings`, `gen_ai.provider.name`, `gen_ai.request.model`, `error.type`, `gen_ai.token.type` — **extend** `gen_ai.token.type` with `cache_read`, `cache_write`, `reasoning`, `tool_search_overhead` (documented vendor extension; the spec only defines `input`/`output` [4]); keep `agent.model.calls` (cheap, and its attrs carry `model.role/purpose/profile/cost_source/graph_node`, which have no semconv home) | Histogram `_sum` gives totals; buckets give per-call size distribution the counters could not |
| counter `agent.model.cost_usd` (USD, only when priced, `telemetry.py:99-100`) | keep; add `agent.model.unpriced_calls` counter | Metrics cannot express NULL; the pair lets a panel show "$X (N unpriced calls)" — the same certificate the ledger enforces (`llm_usage.py:163-167`) |
| `agent.turn.calls`, `agent.turn.duration_seconds`, `agent.subagent.calls`, `agent.subagent.duration_seconds` | keep; subagent runs also get child `invoke_agent <name>` spans | No convention |
| `utils/utils/llm.py` `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`, `llm_tokens_per_request` (`:351-452`) | retire once the ledger sink emits the two `gen_ai.client.*` histograms for direct calls; keep `embedding_*` until embeddings ride the same sink | Removes the G8 split (SDK vs direct) at the metric layer |
| CLI events/metrics (`claude_code.*`) | leave names alone; collector `transform` adds `gen_ai.provider.name=anthropic`, `gen_ai.request.model=model`, `gen_ai.usage.input_tokens=input_tokens` … on `claude_code.llm_request` spans and `api_request` events so backends price them | Cheapest way to make CLI telemetry legible to GenAI-aware backends |

Re-bank list for the rename: `tests/agent_sdk/core/test_agent_sdk_loop_observability.py:61-111`,
`tests/unit/observability/test_run_query_span_identity.py`, `tests/unit/observability/test_turn_{combined,embedding}_cost.py`,
`tests/architecture/agent_runtime/test_agent_shared_rename_checkpoint.py:244-245` (+ `agent_shared_rename_baseline.json:1256`),
`tests/unit/agent_shared/test_telemetry.py:48-171`, and `deployment/observability-local/grafana/dashboards/llm-metrics-dashboard.json`.
The rename is a name-only refactor of `loop_observability.py` + `telemetry.py`; the orchestrator call sites stay.

### 7.2 Where cost is computed and where it should appear
- **System of record: the ledger, unchanged.** It is the only place with NULL semantics, `cost_complete`,
  `cost_source`/`pricing_version`, idempotency and tenancy (`llm_usage.py:73-167`, `llm_model_calls.py:64-118`);
  the CLI's `total_cost_usd` is a list-price estimate by Anthropic's own admission [15], and AWS says the same of
  token×rate-card estimates [45]. Bill reconciliation stays a Cost Explorer job at model/day grain (§4.4).
- **Spans carry cost** (already do): per-turn `agent.cost.*` + `gen_ai.usage.cost` on the root span — for trace
  debugging ("why did this turn cost $0.80") and so an LLM tool shows the same number as the ledger. Per-call cost
  on `execute_tool`/`chat` spans only where the source is provider- or rate-card-priced (the ledger's `ModelUsage`);
  absent otherwise — same "absent, never 0" rule as `usage_span_attributes` (`loop_observability.py:96-100`).
- **Metrics carry cost** for trend/alert panels only: `agent.model.cost_usd` by `gen_ai.provider.name`,
  `gen_ai.request.model`, `model.role`, `agent.department`, `deployment.environment`, plus `tenant.id` **only** while
  tenant count stays in the tens (Claude Code's own metrics already carry `user.account_uuid` by default, so the
  ecosystem accepts this); always pair with `agent.model.unpriced_calls`. Never derive a tenant invoice from metrics.
- **The settings dashboard and any "tokens used / spend" product view read Postgres** (a small read API over
  `llm_usage`/`llm_model_calls`, RLS-scoped) — this retires the Loki-backed analytics path (audit G10/G11) for
  the LLM half of the page; a Grafana Postgres datasource gives the ops view the same exact numbers.
- Emitter placement: **one** sink — the ledger write site (`record_turn_usage` / the `ModelUsage` sink) — feeds
  Postgres, then `RuntimeTelemetry`, then (optionally) an OTLP content event. One snapshot, three consumers, no
  drift (the S2 plan already designed `record_model_usage` as exactly this third sink, `s2-cost-parity.md:134`).

## 8. Comparison matrix

| Option | OTLP ingest / semconv | One-box POC? | Managed | Tenancy model | Content controls | Cost tracking | Evals / annotation | Entry price | Fit here |
|---|---|---|---|---|---|---|---|---|---|
| **Grafana OSS + Tempo/Prometheus on `gen_ai.*`** (+ Postgres datasource) | any OTLP; OpenLIT-style dashboards on `gen_ai.client.*` [36] | **Yes** (already there) | Grafana Cloud AI Observability [34] | by label/attr; Postgres RLS for exact $ | none (we send no bodies) | ledger exact + metric trends | none | $0 | **Baseline** |
| **Arize Phoenix** | OTLP gRPC 4317 / HTTP 6006; OpenInference native, `gen_ai.*` via translation [23][24] | **Yes** (1 container + existing Postgres) | Arize AX | project per tenant; RBAC | pre-redact; retention env | price tables | yes | $0 (ELv2) | **Best OSS LLM tool for the one-box** |
| **Langfuse** | OTLP HTTP traces only; `gen_ai.*`, OpenInference, OpenLLMetry; `gen_ai.usage.cost` [17] | Only with ClickHouse+Redis+MinIO and a 16 GiB box [20] | Cloud US/EU/JP/HIPAA; $0/$29/$199/$2,499 [19] | project per tenant; project keys; EE RBAC/retention/audit | masking (cloud/EE), pre-redact | infers or ingests | yes (strong) | $0 OSS / $29 | Best managed OSS-heritage tool; too heavy for the one-box |
| **Pydantic Logfire** | OTel-native SaaS | No | Yes; free 10M spans, $2/M, $49/$249 [27] | projects | scrubbing (not verified) | yes | yes | $0 | Good managed fallback; no self-host below Enterprise |
| **Braintrust** | OTLP HTTP; `gen_ai.*`, OpenInference, OpenLLMetry [28] | No (hybrid data plane only) | Yes; free 1 GB, $249 Pro [29] | projects | pre-redact | yes | **strongest** | $0 | Eval-first; not a POC fit |
| **Opik** | OTLP HTTP only; drops `gen_ai.usage.cost` [9][32] | Marginal (ClickHouse+MySQL+Redis+MinIO) [33] | Yes; free 25k spans, $19 Pro [33] | workspace/project | pre-redact | own pricing | yes | $0 (Apache-2.0) | Second OSS choice after Phoenix |
| **Helicone** | proxy/gateway; no OTLP documented [30] | Heavy; proxy incompatible with CLI Bedrock streaming [16] | Yes; free 10k req, $79 [31] | properties | omit headers | no Bedrock cost [30] | basic | $0 | Not a fit |
| **OpenLLMetry/Traceloop** | instrumentation, any backend [25] | n/a | Traceloop | n/a | `TRACELOOP_TRACE_CONTENT` | `gen_ai.usage.*` | via backend | $0 | Only if a LangChain instrumentor is wanted; official `genai-langchain` is the more neutral pick |
| **LangSmith** | — | — | — | — | — | — | — | — | **Banned** (`test_no_langsmith_integration.py`) |
| **CloudWatch GenAI observability** | OTLP HTTP endpoints (SigV4); GenAI views need ADOT SDK + `gen_ai.*` spans [39][41] | No (AWS) | Native; $0.35/GB + span indexing [43] | account-wide; log-group per tenant at best | data-protection masking | Bedrock metrics per ModelId; $ only via CE/AIP | none | usage-based | **Production backend for the AWS estate**; Model Invocations view needs invocation logging |
| **Azure Monitor App Insights Agents view** | `gen_ai.*` native, GA 2026-03 [56] | No | Native | resource per tenant | — | tokens | none | usage-based | Production backend for an Azure client |
| **New Relic AI Monitoring** | `gen_ai.*` native [57] | No | Yes | account/entity | — | yes | some | usage-based | Production backend option; not researched in depth |

## 9. Recommendation (10 lines)
1. **(a) POC one-box:** keep the existing collector → Prometheus/Tempo/Loki/Grafana; add **no** LLM platform by default. Ops+cost views come from `gen_ai.*` metrics (OpenLIT-style dashboards) plus a **Grafana Postgres datasource** over `llm_usage`/`llm_model_calls`.
2. If transcript review / evals are wanted in the POC, add **Phoenix** (one container, existing Postgres, ELv2, retention env) — never Langfuse/Opik on the one-box (ClickHouse).
3. **(b) AWS production:** OTel collector with `sigv4authextension` → CloudWatch OTLP traces/logs (+ metrics when GA), Transaction Search on; Bedrock CloudWatch metrics for throttle/TTFT alarms; Cost Explorer per-model Cost Category (`ENDS_WITH "(Amazon Bedrock Edition)"`, `RECORD_TYPE=Usage`) for the bill; managed LLM tool (Langfuse Cloud EU/Logfire) only as an optional, sampled consumer.
4. Wire `RuntimeTelemetry` from the ledger sink (the S2 design), renamed to the §7.1 mapping (`gen_ai.client.operation.duration`, `gen_ai.client.token.usage` with extended token types, `agent.*` for the rest); rename the root/tool spans to `invoke_agent` / `execute_tool` with `gen_ai.*` attrs; retire `llm_*` metrics from `utils/llm.py`.
5. Turn on the **CLI's built-in telemetry** through `ClaudeAgentOptions(env=…)` in the orchestrator (`orchestrator.py:2164`): `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp` (no traces beta initially), `OTEL_METRICS_INCLUDE_SESSION_ID=false`, `OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false`, `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=…,tenant.id=…,enduser.id=…`, short export intervals, `CLAUDE_CODE_OTEL_DIAG_STDERR=1`; the SDK's automatic `TRACEPARENT` injection puts it under our span for free.
6. Instrument the LangGraph runtime once, at the LangChain callback layer (`opentelemetry-instrumentation-genai-langchain`, `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, `NO_CONTENT`); install **no** botocore/anthropic/openai instrumentors (they would double count the direct calls the ledger already prices and see nothing of the SDK loop).
7. **(c) Stays in Postgres:** `llm_usage`, `llm_model_calls` (system of record for tokens and USD), plus a new tenant-scoped, RLS'd, redacted **turn-content relation** (or S3 object keys) keyed `(tenant_id, block_id)`. **Goes to the telemetry backend:** structural spans/metrics/events only — including cost *attributes* (`gen_ai.usage.cost`, `agent.cost.*`) and the paired `unpriced_calls` counter — never prompt bodies.
8. The product settings dashboard reads the ledger through a small read API, not Loki and not the LLM tool.
9. **(d) Content capture policy:** off in prod by default, per-tenant opt-in, redacted (`redact_sensitive`) at the single ledger write site, 7–30-day retention, exported to an LLM tool only as a sampled copy; CLI `OTEL_LOG_USER_PROMPTS`/`…RAW_API_BODIES` unset outside dev (`OTEL_LOG_RAW_API_BODIES=file:<dir>` replaces `debug_dumps/` for developers); Bedrock invocation logging off in prod.
10. Treat every `gen_ai.*` name as Development-status: pin instrumentation versions, keep a collector `transform` for vendor aliases and for the CLI's non-standard token attribute names, and re-bank the pinned tests listed in §7.1 when renaming.

## 10. Sources (read 2026-09-05)
1. OpenTelemetry's GenAI semantic conventions are NOT stable yet (DEV Community, 2026) — https://dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet-heres-what-actually-shipped-in-2026-3mke
2. John Hodge, "The state of the OpenTelemetry GenAI semantic conventions (July 2026)" (dated 2026-07-17) — https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/
3. semantic-conventions-genai `docs/gen-ai/gen-ai-spans.md` (Status: Development) — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
4. semantic-conventions-genai `docs/gen-ai/gen-ai-metrics.md` — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-metrics.md
5. semantic-conventions-genai `docs/gen-ai/gen-ai-agent-spans.md` — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
6. semantic-conventions-genai `docs/gen-ai/gen-ai-events.md` — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md
7. Langfuse issue #11030 "OTEL ingested langfuse.observation.cost_details does not work (gen_ai.usage.cost does)" — https://github.com/langfuse/langfuse/issues/11030
8. Langfuse, "LLM cost management" — https://langfuse.com/resources/engineering/llm-cost-management
9. Opik issue #5620 "LiteLLM OTel: gen_ai.usage.cost is silently dropped" — https://github.com/comet-ml/opik/issues/5620
10. Claude Code docs, "Monitoring" (metrics, events, traces beta, env vars) — https://code.claude.com/docs/en/monitoring-usage
11. opentelemetry-util-genai README (capture modes, upload hook) — https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/util/opentelemetry-util-genai/README.rst
12. Langfuse issue #12657 (opened 2026-03-18, fixed by PR #13674) — https://github.com/langfuse/langfuse/issues/12657
13. Claude Agent SDK docs, "Observability with OpenTelemetry" — https://code.claude.com/docs/en/agent-sdk/observability
14. Dash0, "Monitoring Claude Code usage and costs with OpenTelemetry" — https://www.dash0.com/guides/monitoring-claude-code-opentelemetry
15. Claude Agent SDK docs, "Track cost and usage" — https://code.claude.com/docs/en/agent-sdk/cost-tracking
16. Claude Code docs, "Claude Code on Amazon Bedrock" — https://code.claude.com/docs/en/amazon-bedrock
17. Langfuse, "OpenTelemetry (OTEL) for LLM observability" — https://langfuse.com/integrations/native/opentelemetry
18. Langfuse, self-hosting overview / data isolation / license key — https://langfuse.com/self-hosting , https://langfuse.com/security/data-isolation , https://langfuse.com/self-hosting/license-key
19. Langfuse pricing — https://langfuse.com/pricing
20. Langfuse docker-compose / ClickHouse sizing — https://langfuse.com/self-hosting/deployment/docker-compose , https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse , https://github.com/orgs/langfuse/discussions/5785
21. Langfuse issue #9900 "OTEL endpoint hangs on self-hosted v3.120.0" — https://github.com/langfuse/langfuse/issues/9900
22. Arize Phoenix self-hosting — https://arize.com/docs/phoenix/self-hosting
23. Phoenix self-hosting configuration (env vars, Postgres, retention, ports) — https://arize.com/docs/phoenix/self-hosting/configuration
24. Phoenix, "Translating semantic conventions" + issue #10622 — https://arize.com/docs/phoenix/tracing/concepts-tracing/translating-conventions , https://github.com/Arize-ai/phoenix/issues/10622
25. OpenLLMetry (Traceloop) README — https://github.com/traceloop/openllmetry
26. Pydantic Logfire docs — https://pydantic.dev/docs/logfire/
27. Logfire pricing (change effective 2026-01-01) — https://pydantic.dev/pricing , https://x.com/pydantic/status/1998134821135237613 , https://pydantic.dev/docs/logfire/deploy/enterprise/
28. Braintrust OpenTelemetry integration — https://www.braintrust.dev/docs/guides/traces/integrations/opentelemetry
29. Braintrust pricing summaries (2026) — https://www.truefoundry.com/blog/braintrust-pricing , https://costbench.com/software/ai-observability/braintrust/
30. Helicone gateway docs — https://docs.helicone.ai/getting-started/integration-method/gateway
31. Helicone self-host/pricing roundups (2026; acquisition claim unverified) — https://github.com/Helicone/helicone , https://www.morphllm.com/llm-observability-tools
32. Opik OpenTelemetry overview — https://www.comet.com/docs/opik/tracing/opentelemetry/overview
33. Opik architecture / docker-compose / pricing — https://www.comet.com/docs/opik/self-host/architecture , https://github.com/comet-ml/opik/blob/main/deployment/docker-compose/README.md
34. Grafana Cloud GenAI Observability setup — https://grafana.com/docs/grafana-cloud/monitor-applications/ai-observability/genai/observability/setup/
35. OpenTelemetry blog, "Inside the LLM call: GenAI observability with OpenTelemetry" (2026) — https://opentelemetry.io/blog/2026/genai-observability/
36. VictoriaMetrics, "OpenLIT SDK + self-hosted stack" (OpenLIT emits gen_ai.* + cost extension) — https://victoriametrics.com/blog/victoriametrics-openlit-agents-observability/ ; Grafana, "How to monitor LLMs in production with Grafana Cloud, OpenLIT, and OpenTelemetry" — https://grafana.com/blog/ai-observability-llms-in-production/
37. Amazon CloudWatch, "Generative AI observability" — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/GenAI-observability.html
38. AWS What's New: preview 2025-07, GA 2025-10 — https://aws.amazon.com/about-aws/whats-new/2025/10/generative-ai-observability-amazon-cloudwatch
39. Bedrock AgentCore, "Add observability" (ADOT env vars, non-AgentCore agents, Transaction Search) — https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
40. CloudWatch, "Model Invocations" — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/model-invocations.html
41. CloudWatch, "OTLP Endpoints" — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPEndpoint.html
42. aws-samples, "sample-otel-cloudwatch-no-collector" (metrics OTLP preview note) — https://github.com/aws-samples/sample-otel-cloudwatch-no-collector/blob/main/docs/TRACES.md
43. CloudWatch pricing summaries (2026-05/06) — https://cubeapm.com/blog/aws-cloudwatch-pricing-and-review/ , https://aws.amazon.com/cloudwatch/pricing/
44. Bedrock, "Monitor model invocation using CloudWatch Logs and Amazon S3" — https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
45. Bedrock, "Per-request metadata tagging" — https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-request-metadata.html
46. Bedrock, "Monitor bedrock-runtime inference using CloudWatch metrics" — https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html
47. Bedrock, "Application inference profiles" — https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html
48. Bedrock, "Projects" (cost attribution, mantle only) — https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-projects.html
49. Memory note (verified 2026-07-16 on this account): `~/.claude/projects/-home-aditya-Code/memory/reference_bedrock_cost_explorer_per_model_service.md`
50. opentelemetry-python-genai README (released/unreleased instrumentors) — https://github.com/open-telemetry/opentelemetry-python-genai/blob/main/README.md
51. opentelemetry-python-contrib `instrumentation-genai/` — https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation-genai
52. opentelemetry-instrumentation-botocore README (Bedrock extension) — https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-botocore/README.rst
53. botocore Bedrock extension source — https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-botocore/src/opentelemetry/instrumentation/botocore/extensions/bedrock.py
54. OpenInference LangChain instrumentation — https://arize-ai.github.io/openinference/python/instrumentation/openinference-instrumentation-langchain/
55. vLLM metrics design / OTel tracing — https://docs.vllm.ai/en/latest/design/metrics/ , https://www.dash0.com/blog/observing-vllm-with-opentelemetry-and-dash0
56. Azure Monitor, "Monitor AI agents with Application Insights" (GA 2026-03) — https://learn.microsoft.com/en-us/azure/azure-monitor/app/agents-view
57. New Relic GenAI semconv support (2026 roundup) — https://uptrace.dev/blog/opentelemetry-ai-systems
