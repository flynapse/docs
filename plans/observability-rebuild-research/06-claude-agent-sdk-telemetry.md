# Claude Agent SDK telemetry — sourced facts (2026-09-05)

Researched by the claude-code-guide agent (Sonnet) from official docs. Each fact carries its source URL.

## 1. Built-in OpenTelemetry export
Source: https://code.claude.com/docs/en/monitoring-usage.md

- Enable: `CLAUDE_CODE_ENABLE_TELEMETRY=1` (required). Signal selection: `OTEL_METRICS_EXPORTER` (otlp/prometheus/console/none), `OTEL_LOGS_EXPORTER` (otlp/console/none), `OTEL_TRACES_EXPORTER` (otlp/console/none) — traces are explicitly Beta and need a second flag (below).
- Transport: `OTEL_EXPORTER_OTLP_PROTOCOL` (grpc/http-json/http-protobuf), `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`. Rotating headers via the `otelHeadersHelper` setting (https://code.claude.com/docs/en/settings-reference.md).
- Intervals: `OTEL_METRIC_EXPORT_INTERVAL` (ms, default 60000), `OTEL_LOGS_EXPORT_INTERVAL` (ms, default 5000).
- Content-logging flags, all OFF by default: `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_RAW_API_BODIES` (`=1` or `=file:<dir>`). Content truncated at 60 KB by default (`CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH`).
- Cardinality flags: `OTEL_METRICS_INCLUDE_SESSION_ID` (default true), `OTEL_METRICS_INCLUDE_ACCOUNT_UUID` (default true), `OTEL_METRICS_INCLUDE_VERSION` (default false), `OTEL_METRICS_INCLUDE_ENTRYPOINT` (default false), `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES` (default true).
- `OTEL_RESOURCE_ATTRIBUTES="k=v,k2=v2"` — custom resource attributes attached to every metric/event when `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES=true`.
- **Metrics**: `claude_code.session.count` (`start_type`), `claude_code.lines_of_code.count` (`type`, `model`), `claude_code.pull_request.count`, `claude_code.commit.count`, `claude_code.cost.usage` (USD; attrs `model`, `query_source`=main/subagent/auxiliary, `speed`, `effort`, `agent.name`, `skill.name`, `plugin.name`, `mcp_server.name`, `mcp_tool.name`), `claude_code.token.usage` (`type`=input/output/cacheRead/cacheCreation, same attrs as cost), `claude_code.code_edit_tool.decision`, `claude_code.active_time.total` (`type`=user/cli). Standard attrs on all: `session.id`, `app.version`, `app.entrypoint` (cli/sdk-cli/sdk-ts/sdk-py/claude-vscode), `organization.id`, `user.account_uuid`/`account_id`, `user.id`, `user.email`, `terminal.type`.
- **Events (logs)**: `claude_code.user_prompt`, `claude_code.assistant_response`, `claude_code.tool_result` (`tool_name`, `success`, `duration_ms`, `error_type`, `decision_source`), `claude_code.api_request` (`model`, `cost_usd`, `duration_ms`, `input_tokens`/`output_tokens`/`cache_read_tokens`/`cache_creation_tokens`, `request_id`), `claude_code.api_error` (`status_code`, `attempt`), `claude_code.api_refusal`, `claude_code.tool_decision`, `claude_code.api_request_body`/`api_response_body` (raw, gated), `claude_code.permission_mode_changed`, `claude_code.auth`, `claude_code.mcp_server_connection`. All correlate via `prompt.id`.
- **Traces**: Beta and off unless separately enabled — needs `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` plus `OTEL_TRACES_EXPORTER=otlp`. Span tree: `claude_code.interaction` → `claude_code.llm_request` / `claude_code.hook` / `claude_code.tool`. Detailed hook-span tracing needs `ENABLE_BETA_TRACING_DETAILED=1` + `BETA_TRACING_ENDPOINT`.

## 2. Env passing into the CLI subprocess / per-session tagging
Sources: https://code.claude.com/docs/en/agent-sdk/python.md, https://code.claude.com/docs/en/amazon-bedrock.md

- `ClaudeAgentOptions.env: dict[str, str]` — "Environment variables merged on top of the inherited process environment." The subprocess inherits the parent's `os.environ`; `env` overlays.
- No dedicated tenant-id API. Per-call tagging = set `OTEL_RESOURCE_ATTRIBUTES` in `ClaudeAgentOptions(env=...)` so that call's metrics/events carry it (subject to `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES`).

## 3. Programmatic usage (`ResultMessage` / `AssistantMessage`)
Sources: https://code.claude.com/docs/en/agent-sdk/python.md, https://code.claude.com/docs/en/agent-sdk/cost-tracking.md

- `ResultMessage`: `usage`, `total_cost_usd`, `duration_ms`, `duration_api_ms`, `num_turns`, `session_id`, `is_error`, `model_usage` (per-model breakdown), `subtype`.
- `AssistantMessage.usage` per step: `input_tokens`, `output_tokens` (placeholder — real count lands on the final `ResultMessage.usage`/`model_usage`), `cache_creation_input_tokens`, `cache_read_input_tokens`. `server_tool_use` not documented in the fetched excerpt.
- **Cost accuracy**: `total_cost_usd` is a client-side ESTIMATE from a bundled price table (or `modelPricing` override); can drift on pricing changes / unrecognized models. Applies on Bedrock too. Never bill end users off this field.

## 4. Hooks
Source: https://code.claude.com/docs/en/hooks.md

- Events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, `Notification`.
- Common fields: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `hook_event_name`, `agent_id`/`agent_type` (in subagents). Tool events add `tool_name`, `tool_input`, `tool_use_id`; `PostToolUse` adds `tool_response`; `PostToolUseFailure` adds `tool_error`.
- No built-in duration field on hook payloads — a caller builds tool spans by timestamping `PreToolUse`/`PostToolUse` matched on `tool_use_id`.

## 5. Subagents and usage attribution
Source: https://code.claude.com/docs/en/agent-sdk/cost-tracking.md

| Field | Subagent activity |
|---|---|
| `ResultMessage.usage` | Excluded — top-level loop only |
| `ResultMessage.total_cost_usd` | Included |
| `ResultMessage.model_usage` | Included, per model |

## 6. Cardinality / privacy / beta status
- All prompt/response/tool-content logging OFF by default; only the explicit `OTEL_LOG_*` flags enable it.
- Spans require the Beta flag; `OTEL_TRACES_EXPORTER` is documented Beta.
- Cost/usage numeric fields carry an explicit "not authoritative" disclaimer.

## Gaps
- `CLAUDE_CODE_ENABLE_TELEMETRY` confirmed via monitoring-usage.md (env-vars.md fetch was truncated).
- `server_tool_use` as a `Usage` field: not documented in the fetched material.
