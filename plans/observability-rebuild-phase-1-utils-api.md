# Observability rebuild — Phase 1 detail plan (Stream U: telemetry library + gateway wiring)

Planner: Claude Fable 5.1 (`claude-fable-5-1`), 2026-09-05. Covers master plan §5 tasks **1a.1–1a.7** and **1b.1–1b.6** (and the utils half of 1b.2). Spec sections: §3.1 (env contract, resource identity), §3.3 (signal design; the four adversarial-review facts), §4 (backend foundation, pins, sub-app instrumentation, health), §8 (G13/G14/G20/G28/G30 items), §13 (test kinds). Research grounding: 01 §1.3 (Prometheus name normalisation → units `{USD}`, never `USD`), §1.4 G13/G14/G19–G25/G27/G28, §2.1.0, §2.3, §2.5, §2.7; 04 §5.1–5.2.

**Goal.** Replace the decorative `utils.observability` estate with one programmatic, env-driven OTel bootstrap (traces, metrics, logs over OTLP/HTTP-protobuf), a loguru→OTLP log bridge with flat attributes and event-time timestamps, a stdlib intercept, an explicit metric registry with unit and attribute-key lints, thin compatibility shims so untouchable callers keep working, and gateway/worker wiring in `api`: one SERVER span per request with the full mounted `http.route`, `X-Trace-Id`, `auth.rejections`, `/health/live` + `/health/ready`, and a root span per automation run.

**Branches / worktrees.** `obs-utils` from `langgraph-merge` (utils `3470e80`) at `/home/aditya/Code/utils-obs`; `obs-api` from `langgraph-merge` (api `558b98f`) inside the bundle `/home/aditya/Code/wt-obs-u/api`, with `/home/aditya/Code/wt-obs-u/utils` a symlink to the utils worktree and `core`, `copilot-mro`, `shift-optimizer` symlinks to the main checkouts. All commands below use absolute paths.

**Amendments by the session lead (2026-09-05, before dispatch):** D1 (single mount-aware gateway instrumentation), D6 (semconv identity keys on the wire), D7 (readiness verdict) and D10 are accepted as session-lead defaults and recorded in master plan §15; the gateway also excludes the four browser-ingest routes from its own spans/metrics (U10, Stream P hand-off); a new task U16 adds the two anonymous ingest sub-paths to the auth skip list (Stream P hand-off); master 0.6's gateway half (`/metrics` redirect, `auth/metrics_scrape.py`, `METRICS_SCRAPE_TOKEN`, `prometheus-client` in `api`) is folded into U11 — the copilot-mro half stays with Stream L. If `poetry lock` in the bundle fails because a sibling path dependency (copilot-mro, core, shift-optimizer) constrains `opentelemetry-*` incompatibly, stop U1 and report the constraint — those pyprojects are not this stream's to edit.

## Inherited constraints (master plan "Global constraints", brief "Hard constraints", §11a)
- Conflict zone untouched: `copilot-mro/.../{agent_shared,lang_agent,agent_claude}/**`, `chat_management.py`, `agent_pipeline.py`, `utils/utils/llm.py`. Their calls to `get_metrics_service(...)`, `get_tracing_service(name, env, version)`, `.increment_counter/.record_histogram/.set_gauge/.observe_summary`, `.as_current_span/.as_current_server_span/.start_span/.end_span` keep working unchanged through the compatibility shims (tasks U3, U4).
- No code snippets in this file. Commit only created files plus test edits, by pathspec, after `git diff --cached --name-only`; pre-existing production files edited stay uncommitted and are listed in the ledger at the end. One implementer per worktree. Never a bare `poetry install` in a worktree.
- Two-level test layout, repo-unique basenames, `tests/_root.py` helpers, `DEBUG=false`, PYTHONPATH pinned to the worktree.
- §11a **logging coverage** checkbox on every task: right level on every failure path, bound context, no silent `except: pass`, no user content, structured kwargs, lifecycle lines for background work, stdlib loggers intercepted. Gaps too large for a task go to Future Improvements.
- Pins: `opentelemetry-sdk==1.44.0`, `opentelemetry-exporter-otlp-proto-http==1.44.0`, contrib `==0.65b0` — verified on PyPI 2026-09-05 (all uploaded 2026-07-16): `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-instrumentation-{fastapi,asgi,httpx,requests,urllib3,psycopg2,redis,logging,threading}`, `opentelemetry-test-utils`. The psycopg2 instrumentor's `_instruments_any` accepts `psycopg2-binary` (installed: 2.9.12). Shared env today: SDK 1.37.0, contrib 0.58b0, no client instrumentors — the bundle env (U1) is where the pins are installed.

## Facts that shaped the design (read from the code and the pinned upstream source)
1. `utils/utils/postgres_service.py:104` sets `self._pool = None`; the `ThreadedConnectionPool` is built lazily in `_ensure_pool` (`:234`) on the first query, not at import (the spec's "created at import" is one step off). The instrumentor patches `psycopg2.connect`, which the pool calls per connection — so the invariant is "bootstrap before the first pooled query", satisfied by `api/flynapse_api/main.py:7` (`setup_logging` before any sibling import) and by `worker._configure_logging` preceding `run_worker`.
2. contrib 0.65b0 `FastAPIInstrumentor.instrument_app` patches `app.build_middleware_stack` so its `OpenTelemetryMiddleware` is **outermost** (outside every user middleware and the app's `ServerErrorMiddleware`); its `server_request_hook` therefore runs **before** the gateway's RequestID/Auth middlewares; `_get_route_details` returns only `starlette_route.path`, so a request into a `Mount` yields `http.route` = the mount prefix (spec §3.3 confirmed); the `http.server.request.duration` attributes are taken from `default_span_details` (in `_server_duration_attrs_new`: `http.route`, `http.request.method`, `http.response.status_code`, `url.scheme`, `network.protocol.version`, `error.type`), not from the hook; `_start_internal_or_server_span` demotes a nested middleware's span to INTERNAL; new-semconv names require `OTEL_SEMCONV_STABILITY_OPT_IN=http`; the middleware records no `error.type` when an exception propagates — the 500 status is captured only when the response passes through its `send` wrapper.
3. Starlette 0.48 `Mount.matches` sets child `root_path = root_path + matched_path` and `app_root_path`, leaves `path` intact; `scope` is one dict mutated in place, so an outer middleware sees `scope["endpoint"]` after routing.
4. Legacy callers outside the conflict zone (rg, main checkouts): `api/flynapse_api/middleware/observability.py` (rewritten here), `copilot-mro/.../memory/{memory_db,memory_index}.py`, `document_hub/operations.py` (`set_gauge`), copilot-mro `main.py` `/metrics`, and parser/e2e `setup_logging(name=…, env=…)` callers. `register_*`, `NoOp*`, `OpenTelemetry*Service` classes have zero external references.
5. `api/tests/middleware/skip_paths/test_anonymous_skip_path_stack.py:28,67-78` instantiates `ObservabilityMiddleware` and calls its `dispatch` — a test edit in U12.

## Design decisions (stated once; tasks cite them)
- **D1 Gateway instrumentation = one mount-aware `OpenTelemetryMiddleware` at the gateway**, installed by `flynapse_api.telemetry.http_server.instrument_gateway`, which wraps `app.build_middleware_stack` exactly as upstream `instrument_app` does (inner original stack → `OpenTelemetryMiddleware` → bare outer `ServerErrorMiddleware`) but with our own `default_span_details` that descends through `Mount`s. One SERVER span and one metric sample per request, `http.route` = mount prefix + sub-app route on **both** span and metric, exception-500s carry `http.response.status_code=500`, auth's DB/Cognito work is inside the trace. Deviation from spec §3.3/master 1b.1 (per-sub-app `instrument_app` + gateway `excluded_urls`): that layout leaves the metric's route sub-app-relative, orphans the auth middleware's client spans for mounted routes, and either double-records the duration histogram or collapses the route; recorded for the owner. Consequence: requests rejected by auth (401/403) **do** get a SERVER span; the `auth.rejections` counter is still emitted (D5).
- **D2 Env contract (spec §3.1).** Read by the SDK natively: `OTEL_EXPORTER_OTLP_ENDPOINT` (unset → SDK default `http://localhost:4318`), `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_TRACES_SAMPLER`/`_ARG`, `OTEL_METRIC_EXPORT_INTERVAL`, `OTEL_PYTHON_EXCLUDED_URLS` (gateway), `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` (bootstrap). Read by `bootstrap`: `OTEL_SDK_DISABLED` (`true` → nothing configured, API no-op providers), `OTEL_EXPORTER_OTLP_PROTOCOL` (default `http/protobuf`; any other value → `RuntimeError` naming the variable at boot — there is no gRPC exporter any more), `OTEL_SEMCONV_STABILITY_OPT_IN` (set to `http` by `setdefault` before any instrumentor exists; a deployment may pre-set it). Deleted readers: `OTEL_ENDPOINT`, `OTEL_ENABLED`, `OTEL_SERVICE_NAME`-via-settings, `OTEL_ENV`, `OTEL_VERSION` in `utils/utils/config.py` (U8) and `api/flynapse_api/config/config.py` (U11). Local dev without a collector uses `OTEL_SDK_DISABLED=true` (documented in `.env.sample`).
- **D3 Resource identity precedence.** `resource.build` sets `service.namespace=flynapse` unconditionally; for every other key an `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME` value wins over the code argument (`service.name`, `service.version`, `deployment.environment.name`); `service.instance.id` = `<hostname>:<pid>`. Hand-off: `api/Dockerfile:88` (`ENV OTEL_SERVICE_NAME="copilots"`) must go so `api` and `automation-worker` self-name.
- **D4 stdout format switch** = the `env` argument of `setup_logging(name, env)`: `development`/`dev`/`local` → human format, `LOG_COLORS` honoured (and `NO_COLOR`); anything else → one JSON object per line. `api` passes `"development" if settings.debug else "production"`; `deployment.environment.name` comes from `OTEL_RESOURCE_ATTRIBUTES` first, the `env` argument second.
- **D5 Gateway-level rejections** are counted by `AuthRejectionMetricMiddleware` (executes before Auth) when `http.response.start` carries 401/403 **and** `"endpoint" not in scope` (no route matched → refused by middleware); route-level 403s are not counted.
- **D6 Log-record identity keys** are renamed on the wire by the bridge: `tenant_id→tenant.id`, `user_id→enduser.id`, `session_id→session.id`, `request_id→request.id` (spec §3.1 names); all other extras keep their loguru key. Hand-off to Stream I's redaction allow-list.
- **D7 Readiness verdict**: `/health/ready` returns 200 when the aggregate body's `status` is `healthy` or `degraded` **and** `services.postgres.status == "healthy"`; otherwise 503. Postgres is the one dependency every request needs (the boot check already refuses to serve without it).
- **D8 Legacy shims degrade, new API raises.** `registry.*` handles raise `AttributeKeyError` on forbidden keys; the legacy `MetricsService` shim drops forbidden keys with one WARNING per (metric, key), because its callers cannot be edited yet.
- **D9 Test seams.** `bootstrap(..., pipelines=Pipelines(...))` injects in-memory processors/readers; `bootstrap._reset_for_tests()`, `log_bridge._reset_for_tests()`, `intercept._reset_for_tests()`, `registry._reset_for_tests()` reset module state (bootstrap's uses `opentelemetry.test.globals_test.reset_{trace,metrics,logging}_globals` from `opentelemetry-test-utils`, imported lazily). Each repo's telemetry test tree has one session-scoped fixture that bootstraps once with in-memory pipelines; process-global env behaviour (disabled, protocol, idempotence) is tested in fresh subprocesses, the pattern `utils/tests/unit/packaging/test_lazy_exports.py` already uses.
- **D10** `opentelemetry-instrumentation-logging` and `-fastapi` are **not** activated/added by this stream (the bridge already correlates; the gateway wraps `OpenTelemetryMiddleware` from `-asgi` directly). Both are listed in spec §4; the drift test tolerates `-fastapi` at `0.65b0` because copilot-mro's pyproject still declares it.

## File structure

**utils (worktree `/home/aditya/Code/utils-obs`)** — create: `utils/utils/observability/resource.py` (resource identity), `bootstrap.py` (providers, exporters, env contract, instrumentors), `registry.py` (instrument registry + lints), `log_bridge.py` (loguru sinks: OTLP + JSON stdout), `intercept.py` (stdlib → loguru). Modify (uncommitted): `utils/utils/observability/__init__.py`, `metrics.py` and `tracing.py` (thin), `utils/utils/logging_config.py` (delegation only), `utils/utils/config.py` (field deletion), `utils/pyproject.toml`, `utils/poetry.lock`, `utils/.env.sample`. Tests (new dir `utils/tests/unit/observability/`): `conftest.py`, `_otel_capture_utils.py` (helpers), `test_resource_identity.py`, `test_bootstrap_process_env.py`, `test_bootstrap_in_process.py`, `test_registry_rules.py`, `test_legacy_metrics_service_compat.py`, `test_tracing_helpers.py`, `test_log_bridge_flattening.py`, `test_log_bridge_correlation.py`, `test_stdlib_intercept.py`, `test_setup_logging_delegation.py`, `test_no_legacy_otel_env_readers.py`, `test_client_instrumentors.py`; plus `utils/tests/unit/packaging/test_otel_pins_utils.py`.

**api (bundle `/home/aditya/Code/wt-obs-u/api`)** — create: `flynapse_api/telemetry/__init__.py`, `telemetry/http_server.py` (gateway instrumentation), `telemetry/request_identity.py` (span identity attributes), `telemetry/run_span.py` (automation root span), `flynapse_api/middleware/telemetry.py` (`X-Trace-Id`, `auth.rejections`), `flynapse_api/routers/health.py`. Modify (uncommitted): `flynapse_api/main.py`, `flynapse_api/config/config.py`, `flynapse_api/middleware/__init__.py`, `flynapse_api/middleware/logging.py`, `flynapse_api/automations/worker.py`, `flynapse_api/automations/executor.py`, `api/pyproject.toml`, `api/poetry.lock`, `api/Dockerfile`; delete `flynapse_api/middleware/observability.py`. Tests (new dirs `tests/integration/otel/`, `tests/unit/telemetry/`, `tests/middleware/telemetry/`, `tests/api/health/`): `tests/integration/otel/conftest.py`, `_otel_capture_api.py`, `test_gateway_http_instrumentation.py`, `test_pool_instrumented.py`, `test_automation_run_span.py`; `tests/unit/telemetry/test_gateway_bootstrap_order.py`, `test_no_legacy_otel_config_api.py`, `test_worker_service_name.py`; `tests/unit/infra/test_otel_pins_api.py`; `tests/middleware/telemetry/test_trace_id_header.py`, `test_auth_rejection_metric.py`, `test_request_identity_span_attributes.py`; `tests/api/health/test_health_probes.py`. Test edits: `tests/conftest.py`, `tests/startup/surface/test_gateway_root_surface.py`, `tests/middleware/skip_paths/test_anonymous_skip_path_stack.py`.

## Standard commands
- utils tests (from U1 on, the bundle env): `cd /home/aditya/Code/wt-obs-u/api && env -u VIRTUAL_ENV DEBUG=false PYTHONPATH=/home/aditya/Code/utils-obs poetry run pytest /home/aditya/Code/utils-obs/tests/unit/observability/<file> -q` (pytest's rootdir resolves to `utils-obs` from the path argument, so its `pyproject` ini, `tests/conftest.py` and `_root` apply).
- api tests: `cd /home/aditya/Code/wt-obs-u/api && env -u VIRTUAL_ENV DEBUG=false PYTHONPATH=/home/aditya/Code/wt-obs-u/api/flynapse_api:/home/aditya/Code/wt-obs-u/api:/home/aditya/Code/utils-obs poetry run pytest tests/<path> -q`.
- Commit: `cd <worktree> && git add <paths> && git diff --cached --name-only && git commit -m "<msg>" -- <paths>`. Retry on `index.lock`.

---

## U0 — Worktrees and the bundle (no code)
Covers brief rules 6–7; prerequisite for everything.
- [x] `git -C /home/aditya/Code/utils worktree add /home/aditya/Code/utils-obs -b obs-utils langgraph-merge` (the main utils checkout has uncommitted edits to `.env.sample` and `utils/dev/.claude/CLAUDE.md`; they are not carried over and must not be touched).
- [x] `mkdir -p /home/aditya/Code/wt-obs-u && git -C /home/aditya/Code/api worktree add /home/aditya/Code/wt-obs-u/api -b obs-api langgraph-merge`.
- [x] Symlinks so `../x` resolves from the bundle api: `ln -s /home/aditya/Code/utils-obs /home/aditya/Code/wt-obs-u/utils`, `ln -s /home/aditya/Code/core /home/aditya/Code/wt-obs-u/core`, `ln -s /home/aditya/Code/copilot-mro /home/aditya/Code/wt-obs-u/copilot-mro`, `ln -s /home/aditya/Code/shift-optimizer /home/aditya/Code/wt-obs-u/shift-optimizer`; `ln -s /home/aditya/Code/api/.env /home/aditya/Code/wt-obs-u/api/.env` (utils has no `.env`; its tests read the api one through the cwd).
- [x] The workspace root `/home/aditya/Code` is itself a git repo: append `utils-obs/` and `wt-obs-u/` to `/home/aditya/Code/.git/info/exclude`.
- [x] Verify: `git -C /home/aditya/Code/utils worktree list`, `git -C /home/aditya/Code/api worktree list`, `ls -la /home/aditya/Code/wt-obs-u`.
Acceptance: both worktrees on their branches at the base SHAs; `ls /home/aditya/Code/wt-obs-u/api/../utils/utils/observability` lists the utils worktree files.

## U1 (= 1a.6) — Pins, lock, install, dependency-drift tests
Spec §4 pins; master 1a.6; research 04 §5.1.
**Files.** Modify `utils/pyproject.toml`, `utils/poetry.lock`, `api/pyproject.toml`, `api/poetry.lock` (all uncommitted). Create `utils/tests/unit/packaging/test_otel_pins_utils.py`, `api/tests/unit/infra/test_otel_pins_api.py`.
**Interfaces.** utils `[tool.poetry.dependencies]`: `opentelemetry-api = "1.44.0"`, `opentelemetry-sdk = "1.44.0"`, `opentelemetry-exporter-otlp-proto-http = "1.44.0"`, `opentelemetry-instrumentation = "0.65b0"`, `opentelemetry-instrumentation-httpx`, `-requests`, `-urllib3`, `-psycopg2`, `-redis`, `-threading` all `"0.65b0"`; remove `opentelemetry-exporter-otlp-proto-grpc` and `prometheus-client` (no import of either anywhere in `utils/utils`). utils dev group: `opentelemetry-test-utils = "0.65b0"`, `fakeredis = "*"`. api dependencies: `opentelemetry-api = "1.44.0"`, `opentelemetry-sdk = "1.44.0"`, `opentelemetry-instrumentation-asgi = "0.65b0"`; remove `opentelemetry-instrumentation-fastapi`, `-logging`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-exporter-otlp-proto-grpc` (utils supplies the exporter; D10). `prometheus-client` is removed from api as well (the 0.6 gateway half is folded into U11). api dev group: `opentelemetry-test-utils = "0.65b0"`, `fakeredis = "*"` (path dependencies' dev groups are not installed, so both repos declare them).
**Steps.**
- [x] Write `test_otel_pins_utils.py`: `tomllib`-parse `repo_root(__file__, "pyproject.toml")` (pattern: `api/tests/unit/infra/test_no_langsmith_integration.py`); assert each pinned name maps to the exact version string; assert `opentelemetry-exporter-otlp-proto-grpc`, `prometheus-client`, `opentelemetry-instrumentation-botocore`, `opentelemetry-distro` are absent from every group; assert `importlib.metadata.version` of every pinned package equals the pin. Run it — fails on the old `"*"` lines.
- [x] Write `test_otel_pins_api.py` likewise for api (the three pins, the four removals plus `prometheus-client` absent, installed versions; if `opentelemetry-instrumentation-fastapi` is installed its version must be `0.65b0`).
- [x] Edit both pyprojects. Lock and install: `cd /home/aditya/Code/utils-obs && env -u VIRTUAL_ENV poetry lock`; `cd /home/aditya/Code/wt-obs-u/api && env -u VIRTUAL_ENV POETRY_VIRTUALENVS_IN_PROJECT=true poetry lock && env -u VIRTUAL_ENV POETRY_VIRTUALENVS_IN_PROJECT=true poetry install` (Poetry 2.3.2 keeps unrelated pins; expect 5–10 min). Confirm `git -C /home/aditya/Code/wt-obs-u/api status --short` does not list `.venv/`.
- [x] Verify `env -u VIRTUAL_ENV poetry run pip show opentelemetry-sdk opentelemetry-instrumentation-psycopg2 opentelemetry-test-utils` from the bundle reports 1.44.0 / 0.65b0 / 0.65b0.
- [x] Run both tests green: `… pytest /home/aditya/Code/utils-obs/tests/unit/packaging/test_otel_pins_utils.py` and `… pytest tests/unit/infra/test_otel_pins_api.py`.
- [x] Run the full utils suite once from the bundle (`… pytest /home/aditya/Code/utils-obs/tests -q`) to prove the SDK bump breaks nothing before new code lands.
- [x] Logging coverage: no module touched — nothing to check.
- [x] Commit (utils): `test_otel_pins_utils.py`; (api): `test_otel_pins_api.py`. Report the pyproject/lock diffs.
**Acceptance.** Both pin tests green in the bundle env; existing suites green.
| Likely finding | Triage |
|---|---|
| `-fastapi`/`-logging` listed in spec §4 but not added | intentional (D10); record in implementation notes |
| Two lock files changed | expected, uncommitted, reported |

## U2 (= 1a.1) — `resource.py` and `bootstrap.py`
Spec §3.1, §4; master 1a.1; research 01 G13/G14/G27; 04 §5.2.
**Files.** Create `utils/utils/observability/resource.py`, `bootstrap.py`; tests `utils/tests/unit/observability/conftest.py`, `_otel_capture_utils.py`, `test_resource_identity.py`, `test_bootstrap_process_env.py`, `test_bootstrap_in_process.py`.
**Interfaces produced.**
- `resource.NAMESPACE = "flynapse"`; `resource.instance_id() -> str` (`<hostname>:<pid>`); `resource.build(service_name: str, version: str | None = None, *, environment: str | None = None) -> Resource` (D3; `service.version` defaults to `"unknown"`; `deployment.environment.name` omitted when neither env nor argument supplies it).
- `bootstrap.Pipelines` frozen dataclass: `spans: SpanProcessor | None`, `metrics: MetricReader | None`, `logs: LogRecordProcessor | None` (each replaces the OTLP pipeline of its signal).
- `bootstrap.BootstrapState` frozen dataclass: `service_name`, `environment: str | None`, `disabled: bool`, `endpoint: str | None` (the env value, unresolved), `protocol: str`, `instrumentations: tuple[str, ...]` (empty until U9), `configured_by_this_call: bool`.
- `bootstrap.bootstrap(service_name: str, *, version: str | None = None, environment: str | None = None, pipelines: Pipelines | None = None) -> BootstrapState`: idempotent via a module-level state guarded by a lock; first call: read `OTEL_SDK_DISABLED` (SDK parse: lower-cased equals `true`), validate `OTEL_EXPORTER_OTLP_PROTOCOL` (D2), `os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")`, build the resource, `TracerProvider(resource)` + `BatchSpanProcessor(OTLPSpanExporter())` (http package) or the injected processor, `MeterProvider(resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())])` or the injected reader, `LoggerProvider(resource)` + `BatchLogRecordProcessor(OTLPLogExporter())` or the injected processor; set the three API globals; apply instrumentors (U9); disabled → set nothing, return `disabled=True`. Later calls return the stored state with `configured_by_this_call=False` and ignore arguments. `bootstrap.state() -> BootstrapState | None`; `bootstrap._reset_for_tests() -> None` (shutdown providers, uninstrument, reset API globals via `opentelemetry.test.globals_test`, clear state). Constants `DEFAULT_PROTOCOL = "http/protobuf"`, `SEMCONV_OPT_IN_DEFAULT = "http"`.
- conftest (session, autouse): sets `OTEL_SDK_DISABLED=false` through a session `pytest.MonkeyPatch`, calls `_reset_for_tests()`, then `bootstrap("utils-tests", version="0.0.0", environment="test", pipelines=Pipelines(SimpleSpanProcessor(InMemorySpanExporter()), InMemoryMetricReader(), SimpleLogRecordProcessor(InMemoryLogExporter())))`, then (from U5/U6 on) `log_bridge.install("DEBUG", json_stdout=True, colors=False)` and `intercept.install("DEBUG")`; yields a `Captured` namedtuple (`spans`, `metrics`, `logs`). A function-scoped autouse fixture clears the span and log exporters. `_otel_capture_utils.py`: `metric_points(reader, name) -> list` (walks `get_metrics_data()`), `span_named(exporter, name)`, `log_records(exporter) -> list`.
**Steps.**
- [x] Write `test_resource_identity.py`: `build("api")` → `service.namespace == "flynapse"`, `service.name == "api"`, `service.version == "unknown"`, `service.instance.id == instance_id()` and matches `<host>:<pid>`; with `OTEL_SERVICE_NAME=copilots` env → `service.name == "copilots"`; with `OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=prod,service.namespace=other` → environment `prod`, namespace still `flynapse`; `environment="development"` argument used only when the env has no value. Run — fails (module absent).
- [x] Write `test_bootstrap_process_env.py` (subprocess per case; inherit `PYTHONPATH`): disabled → `disabled` true, tracer provider class is the API `ProxyTracerProvider`; default → SDK `TracerProvider`, `protocol == "http/protobuf"`, span processor's exporter class is the http `OTLPSpanExporter`, meter provider has one `PeriodicExportingMetricReader`, logger provider set; `OTEL_EXPORTER_OTLP_PROTOCOL=grpc` → non-zero exit with `RuntimeError` text containing the variable name; `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318` → `state.endpoint` equals it; `OTEL_SEMCONV_STABILITY_OPT_IN` becomes `http` when unset and stays `http/dup` when preset; second call returns `configured_by_this_call False` and the same provider object; `OTEL_TRACES_SAMPLER=parentbased_traceidratio` + `_ARG=0.5` → the provider's sampler description mentions the ratio (SDK-native; proves the contract is not overridden). Run — fails.
- [x] Write `test_bootstrap_in_process.py` against the session fixture: a span started from `trace.get_tracer("t")` lands in the in-memory exporter with the resource attributes; `state().configured_by_this_call` is False on a repeat call; `state().disabled` is False.
- [x] Implement `resource.py`, `bootstrap.py`, conftest, helpers. Run the three files green.
- [x] Logging coverage: `bootstrap` logs nothing itself (the sinks do not exist yet when it runs; `setup_logging` emits the one "Telemetry configured" line in U7); the protocol refusal is an exception with the remedy in its message; exporter failures are the SDK's `opentelemetry.*` loggers (routed to stderr by U6).
- [x] Commit: the two modules, conftest, helper, three test files.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_resource_identity.py test_bootstrap_process_env.py test_bootstrap_in_process.py` (absolute paths).
**Acceptance.** Second call no-op; disabled → no exporters; resource attributes present; protocol default http; sampler env honoured.
| Likely finding | Triage |
|---|---|
| `opentelemetry.sdk._logs` private path | intentional — the logs SDK has no public alias at 1.44; note |
| `_reset_for_tests` imports a test-only package | intentional lazy import; production never calls it |
| Endpoint unset → export failures in dev | intentional (contract purity); `.env.sample` documents `OTEL_SDK_DISABLED=true` (U8) |

## U3 (= 1a.2) — `registry.py` and the legacy `MetricsService` shim
Spec §3.3 "Metrics", §4; master 1a.2; research 01 §1.3, G19/G20/G27.
**Files.** Create `utils/utils/observability/registry.py`; rewrite `metrics.py` (uncommitted); tests `test_registry_rules.py`, `test_legacy_metrics_service_compat.py`.
**Interfaces produced.** `registry.UNITS = frozenset({"1", "s", "ms", "By", "{USD}", "{token}", "{request}"})` (Phase 3 extends by editing the constant and its test); `registry.FORBIDDEN_ATTRIBUTE_KEYS = frozenset({"session_id", "session.id", "user_id", "user.id", "enduser.id", "path", "url", "url.path", "url.full", "http.target"})`; `RegistryError(ValueError)`, `AttributeKeyError(RegistryError)`; `registry.meter() -> Meter` (`metrics.get_meter("utils.observability", <utils version>)`, resolved at call time so proxies re-bind after bootstrap); `counter(name, unit, description) -> CounterHandle`, `up_down_counter(name, unit, description) -> UpDownCounterHandle`, `histogram(name, unit, description, *, boundaries: Sequence[float] | None = None) -> HistogramHandle`, `observable_gauge(name, unit, description, callback) -> None` (callback wrapped so each `Observation`'s attributes are linted); handles expose `add(value, attributes=None)` / `record(value, attributes=None)`; `registered() -> Mapping[str, str]` (name → kind); `_reset_for_tests()`. Rules: name must match the OTel instrument-name grammar (else `RegistryError`); unit not in `UNITS` → `RegistryError`; same name registered again with the same kind returns the same handle, with another kind → `RegistryError`; on every emission `None`-valued attributes are dropped and a key in `FORBIDDEN_ATTRIBUTE_KEYS` raises `AttributeKeyError` before the SDK is touched.
`metrics.py` keeps `MetricsService` (ABC, four abstract methods) and `get_metrics_service(name: str = "", env: str = "", version: str = "") -> MetricsService` (arguments accepted and ignored — G27 documented in the docstring; process singleton) returning `LegacyMetricsService`: `increment_counter` → `registry.counter(name, "1", "legacy auto-registered counter")`, `record_histogram`/`observe_summary` → `registry.histogram(name, "1", …)`, `set_gauge` → `registry.up_down_counter(name, "1", …).add(value, …)` (behaviour preserved for the one remaining caller `document_hub/operations.py:97`, retired by Stream L); `tenant_id` becomes the `tenant_id` attribute as today; forbidden keys are dropped with one `logger.warning("Dropped a forbidden metric attribute", metric=…, key=…)` per (metric, key) (D8). Delete `OpenTelemetryMetricsService`, `NoOpMetricsService`, all `register_*`, the try/except import guard and the module docstring's usage examples.
**Steps.**
- [x] Write `test_registry_rules.py`: unit allow-list (`{USD}` accepted, `USD` and `seconds` refused); name grammar; duplicate-name/different-kind refusal and same-kind identity; `None` attribute dropped (assert on the in-memory reader's point attributes); each forbidden key raises `AttributeKeyError` (parametrised over the set) and no point is recorded; `observable_gauge` callback observations reach the reader and a forbidden key in an observation raises at collection; `histogram(..., boundaries=…)` produces the given bucket boundaries. Run — fails.
- [x] Write `test_legacy_metrics_service_compat.py`: `get_metrics_service("a") is get_metrics_service("b")`; `increment_counter("llm_requests_total", tenant_id="t1", model="m", user_id="u")` → one point with attributes exactly `{tenant_id: t1, model: m}` and exactly one WARN log record in the in-memory log exporter (severity ≥ WARN, message contains the key) even after a second call; `record_histogram("llm_request_duration", 0.5, tenant_id=None, department=None)` → point with no attributes; `set_gauge("x", 1, tenant_id="t")` → an up-down-counter point; `observe_summary` → histogram point; `MetricsService` still importable from `utils` (lazy export unchanged). Run — fails.
- [x] Implement `registry.py`, rewrite `metrics.py`. Run both files green; run `utils/tests/unit/packaging/test_lazy_exports.py` and `utils/tests/unit/metering/` green (they stub `_get_metrics_service_safe`).
- [x] Logging coverage (`metrics.py`): the old module logged INFO on every registration and swallowed `.add` failures at DEBUG — gone; the shim's only log is the forbidden-key WARNING with `metric=`/`key=` kwargs; no `except: pass`.
- [x] Commit: `registry.py`, the two test files. `metrics.py` stays uncommitted (pre-existing).
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_registry_rules.py test_legacy_metrics_service_compat.py`.
**Acceptance.** All rules tested; legacy callers' call shapes (verified list in Facts 4) still type-check against the shim's signatures.
| Likely finding | Triage |
|---|---|
| Raising inside a request path for a bad attribute key | intentional per master 1a.2; new API only, shim degrades |
| `set_gauge` still monotonic garbage | intentional compatibility until 1b.7/1b.8; Future Improvements note |

## U4 — `tracing.py` thin helpers, `TracingService` shim, package exports
Spec §4 ("`get_tracer()`, `get_meter()`, `span(name, **attrs)`"); master 1a files line; research 01 G5 (extract-only stays for the shim), G27.
**Files.** Rewrite `utils/utils/observability/tracing.py` and `__init__.py` (uncommitted); test `test_tracing_helpers.py`.
**Interfaces produced.** `tracing.get_tracer(name: str = "utils.observability") -> Tracer` (via `trace.get_tracer` at call time); `tracing.span(name: str, **attributes) -> ContextManager[Span]` (`start_as_current_span`, INTERNAL, `None` attributes dropped); `TracingService` ABC unchanged; `SdkTracingService(TracingService)`: `as_current_server_span(name, attributes=None, parent_headers=None)` extracts W3C context with `opentelemetry.propagate.extract` and starts a SERVER span, `as_current_span(name, attributes=None)`, async `start_span`/`end_span` as before (status/exception recording kept); `get_tracing_service(name: str = "", env: str = "", version: str = "") -> TracingService` singleton, arguments ignored. Delete `OpenTelemetryTracingService`, `NoOpTracingService`, `_noop_context`, `OTEL_TRACING_AVAILABLE`. `__init__.py` exports: `bootstrap`, `BootstrapState`, `Pipelines`, `get_tracer`, `span`, `registry` (module), `get_metrics_service`, `get_tracing_service`, `MetricsService`, `TracingService`; `__all__` lists them. `utils/utils/__init__.py` `_EXPORTS` is untouched (its names still resolve).
**Steps.**
- [x] Write `test_tracing_helpers.py`: `span("work", tenant_id="t", nothing=None)` → one finished span, INTERNAL, attribute `tenant_id` present, `nothing` absent; `as_current_server_span("GET /x", parent_headers={"traceparent": "00-…-…-01"})` → kind SERVER, trace id equal to the header's, parent span id equal; `get_tracing_service("a") is get_tracing_service("b")`; `start_span`/`end_span(status="error", error=ValueError("x"))` → status ERROR and one exception event; `from utils.observability import bootstrap, span, registry` resolves. Run — fails.
- [x] Implement. Run green; run `test_lazy_exports.py` green.
- [x] Logging coverage (`tracing.py`): the old `logger.debug("Failed to start span…")` swallowers are gone; the shim has no failure path that needs a log (the SDK never raises on span operations).
- [x] Commit: `test_tracing_helpers.py` only (both modules pre-existing).
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_tracing_helpers.py /home/aditya/Code/utils-obs/tests/unit/packaging/test_lazy_exports.py`.
| Likely finding | Triage |
|---|---|
| Eager import of the SDK from `utils.observability` | intentional (small); `table_builder` import test still proves no client construction |

## U5 (= 1a.3) — `log_bridge.py`
Spec §3.3 "Logs" (sinks 1–2, adversarial fact: the stock handler nests `extra`); master 1a.3; research 01 §2.3.2, G15/G24/G25; 04 §5.2.
**Files.** Create `utils/utils/observability/log_bridge.py`; tests `test_log_bridge_flattening.py`, `test_log_bridge_correlation.py`; conftest gains the `log_bridge.install` call.
**Interfaces produced.** `log_bridge.IDENTITY_KEYS = {"tenant_id": "tenant.id", "user_id": "enduser.id", "session_id": "session.id", "request_id": "request.id"}` (D6); `log_bridge.flatten(record: Mapping[str, Any]) -> dict[str, Any]` — from a loguru record's `extra`: identity keys renamed; `str`/`bool`/`int`/`float` kept as-is; `None` dropped; homogeneous sequences of primitives kept; every other value (dict, `Decimal`, `datetime`, `UUID`, objects, mixed lists) → `str(value)`; a key colliding with a stdlib `LogRecord` reserved attribute (`name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `process`, `processName`, `message`, `asctime`, `taskName`) is emitted as `extra.<key>`. `log_bridge.install(level: str = "INFO", *, json_stdout: bool = True, colors: bool = False) -> tuple[int, int]` — idempotent by module flag (returns the cached sink ids on repeat); first call `logger.remove()`s existing handlers (no "skip if any handler exists" branch — G23), then adds (1) the stdout sink: JSON line sink when `json_stdout` (a callable that writes `json.dumps` of `time` ISO-8601 with offset from `record["time"]`, `level` name, `logger` (`record["name"]`), `function`, `line`, `message`, `trace_id`/`span_id` hex when a span is current, `exception` text when present, plus `flatten(record)` at top level, to `sys.stdout` looked up at call time), else the current human format with `colorize=colors`; (2) the OTLP sink: a callable building a stdlib `LogRecord` (`name`, `levelno = record["level"].no`, `levelname = record["level"].name`, `pathname`/`lineno`/`funcName` from the record, `msg = record["message"]`, empty `args`, `exc_info` from `record["exception"]`), setting `created = record["time"].timestamp()` (event time; `msecs`/`relativeCreated` derived — G24 fix without the monotonic bump), `setattr`-ing every flattened key, and calling `LoggingHandler(level=<level>, logger_provider=get_logger_provider()).emit(...)`; no file sinks (G25); no `enqueue`. `log_bridge._reset_for_tests()` removes the two sinks and clears the flag.
**Steps.**
- [x] Write `test_log_bridge_flattening.py`: `flatten` unit cases per rule above (parametrised); through the real sink: `logger.bind(tenant_id="t1", chat_id="c", count=3, ratio=0.5, flag=True, empty=None, meta={"a": 1}).info("m")` → the exported `LogRecord.attributes` has `tenant.id == "t1"` (and no `tenant_id`, no `extra.tenant_id`), `chat_id == "c"`, `count == 3` (int, not `"3"`), `ratio == 0.5`, `flag is True`, no `empty`, `meta == "{'a': 1}"`; `logger.bind(name="x").info("m")` → attribute `extra.name`; the JSON stdout line (capsys) parses and carries the same keys, `level == "INFO"`, `logger` set; the `exception` key and `exception.type`/`exception.stacktrace` attributes appear for `logger.exception` inside an `except`. Run — fails.
- [x] Write `test_log_bridge_correlation.py`: timestamp equals `int(record_time.timestamp() * 1e9)` computed from a `loguru` patcher-captured `record["time"]` (compare identically); inside `get_tracer("t").start_as_current_span("s")` the exported record's `trace_id`/`span_id` equal the span's and the JSON line's `trace_id` is the 32-hex form; outside a span both are 0/absent; severity: INFO → `SeverityNumber.INFO`, WARNING → `WARN`, ERROR → `ERROR`, SUCCESS (25) → a number strictly between INFO and WARN with `severity_text == "SUCCESS"`; `install()` twice returns identical ids and the handler count is unchanged; after `_reset_for_tests()` the sinks are gone. Run — fails.
- [x] Implement; wire the conftest. Run green.
- [x] Logging coverage: the bridge itself must never log through loguru from inside a sink (recursion); a sink failure is written once to `sys.stderr` with the exception type and then suppressed for that record (replacing the old `print(f"OTEL logging failed…")`).
- [x] Commit: `log_bridge.py`, two tests, conftest.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_log_bridge_flattening.py test_log_bridge_correlation.py`.
| Likely finding | Triage |
|---|---|
| Not literally `serialize=True` | intentional: loguru's serializer nests `record.extra`; the flattening contract needs the custom serializer (master 1a.3 wording) |
| Identity key rename vs master test wording (`tenant_id`) | intentional (D6, spec §3.1); test asserts `tenant.id` |

## U6 (= 1a.4) — `intercept.py`
Spec §3.3 sink (3); master 1a.4; research 01 G22.
**Files.** Create `utils/utils/observability/intercept.py`; test `test_stdlib_intercept.py`; conftest gains `intercept.install("DEBUG")`.
**Interfaces produced.** `intercept.InterceptHandler(logging.Handler)` (`emit` maps `record.levelname` to the loguru level when it exists else `record.levelno`, finds the caller depth by walking frames out of the `logging` module, forwards `record.getMessage()` with `exception=record.exc_info`); `intercept.EXPLICIT_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error", "botocore", "httpx")`; `intercept.EXCLUDED_LOGGER = "opentelemetry"`; `intercept.install(level: str = "INFO") -> None` — idempotent: root logger handlers replaced by one `InterceptHandler` (`logging.basicConfig(force=True, …)`) at `level`; each explicit logger gets its handlers replaced by an `InterceptHandler` and `propagate=False` (uvicorn's dictConfig sets `propagate=False` on `uvicorn`/`uvicorn.access` before the app is imported, so this runs after it and wins); the `opentelemetry` logger gets `propagate=False` and one `StreamHandler(sys.stderr)` at WARNING so exporter failures are visible but never re-enter the OTLP sink. `_reset_for_tests()` restores the previous handler/propagate state it recorded.
**Steps.**
- [x] Write `test_stdlib_intercept.py`: `logging.getLogger("x.y").warning("hello %s", "w")` → in-memory log record with body `hello w`, severity WARN, `attributes["code.function"]`/`code.filepath` pointing at the test file (depth correct); pre-configure `uvicorn.access` with `propagate=False` and a `NullHandler`, then `install()`, then `.info("GET / 200")` → record present; `logging.getLogger("opentelemetry.sdk.trace").warning("boom")` → no record in the exporter and the text appears on captured stderr; `install()` twice → root has exactly one `InterceptHandler`; a stdlib record with `exc_info` yields `exception.type`. Run — fails.
- [x] Implement; wire conftest. Run green.
- [x] Logging coverage: none beyond the module's purpose; `install` logs nothing (it runs before sinks may exist).
- [x] Commit: `intercept.py`, test, conftest.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_stdlib_intercept.py`.
| Likely finding | Triage |
|---|---|
| botocore DEBUG floods when `LOG_LEVEL=DEBUG` | intentional: root level = `LOG_LEVEL`; Future Improvements: per-logger caps |

## U7 (= 1a.5) — `setup_logging` delegation
Spec §3.3 (idempotent, explicit); master 1a.5; research 01 §2.3.1, G23.
**Files.** Rewrite `utils/utils/logging_config.py` (uncommitted); test `test_setup_logging_delegation.py`.
**Interfaces.** `logging_config.DEV_ENVIRONMENTS = frozenset({"development", "dev", "local"})`; `logging_config.is_dev(env: str) -> bool`; `setup_logging(name: str = "", env: str = "production") -> None`: `service = name or "flynapse-service"`; `state = bootstrap(service, version=settings.app_version, environment=env)`; `dev = is_dev(env)`; `log_bridge.install(settings.log_level, json_stdout=not dev, colors=dev and settings.log_colors and not os.getenv("NO_COLOR"))`; `intercept.install(settings.log_level)`; when `state.configured_by_this_call`, one `logger.info("Telemetry configured", service_name=…, environment=…, endpoint=…, protocol=…, disabled=…, instrumentations=…, json_stdout=…)`. Delete `setup_loguru`, `has_loguru_handlers`, `_setup_otel_integration`, `_unique_ns_from_seconds`, `_last_ts_ns`, the `Path`/`random`/`time` imports. `settings.log_dir` no longer read.
**Steps.**
- [x] Write `test_setup_logging_delegation.py` (uses `log_bridge._reset_for_tests()`/`intercept._reset_for_tests()` between cases; bootstrap stays the session one): `setup_logging("svc", "development")` twice → loguru handler count identical after the second call and `bootstrap.state().configured_by_this_call` False; `env="development"` + `settings.log_colors=True` (monkeypatch) → a captured stdout line that is not JSON and contains the human separators; `env="production"` with `log_colors=True` → stdout line parses as JSON (colors ignored outside dev); `NO_COLOR=1` in dev → no ANSI escapes; the "Telemetry configured" record reaches the in-memory log exporter with `service_name`, `protocol`, `disabled` attributes (first call only); `setup_loguru`/`has_loguru_handlers` no longer exist on the module. Run — fails.
- [x] Implement. Run green; run the whole `utils/tests` suite green.
- [x] Logging coverage (`logging_config.py`): the "Loguru handlers already exist" warning and the two "Loguru configured…" INFO lines are replaced by the single structured line; no `print`.
- [x] Commit: the test only.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_setup_logging_delegation.py`.
| Likely finding | Triage |
|---|---|
| `env` argument survives although spec deletes `OTEL_ENV` | intentional: the argument is the legacy call signature (parsers, e2e scripts); the env var is gone (U8/U11) |

## U8 (= 1a.7) — Delete the `utils.config` telemetry indirection
Spec §3.1, §8; master 1a.7; research 01 §2.7.1.
**Files.** Modify `utils/utils/config.py`, `utils/.env.sample` (uncommitted); test `test_no_legacy_otel_env_readers.py`.
**Steps.**
- [x] Write the test: scan `repo_root(__file__, "utils")` recursively for `*.py` and fail on any match of `OTEL_ENDPOINT`, `OTEL_ENABLED`, `otel_endpoint`, `otel_enabled`, `otel_service_name`, `METRICS_ENABLED`, `METRICS_EXPORT_INTERVAL`, `TRACING_ENABLED`, `TRACING_SAMPLING_RATE`, `exporter.otlp.proto.grpc`, `prometheus_client`; assert `utils.config.Settings.model_fields` lacks `otel_endpoint`, `otel_service_name`, `otel_enabled`, `log_dir`, `metrics_enabled`, `metrics_export_interval`, `tracing_enabled`, `tracing_sampling_rate` and still has `log_level`, `log_colors`, `app_version`, `debug`. Run — fails.
- [x] Before deleting each field, `rg` its attribute name across the main checkouts (`utils/utils`, `api/flynapse_api`, `core/core`, `copilot-mro/copilot_mro`, `shift-optimizer/shift_optimizer`): verified today that none of the eight has a reader outside `utils/utils/logging_config.py` (already rewritten) and the `config.py` declarations themselves (`settings.app_version` readers in copilot-mro are unaffected). Delete the fields and their comments.
- [x] `utils/.env.sample`: remove `OTEL_ENABLED=True`, `OTEL_ENDPOINT=…`, `OTEL_SERVICE_NAME=copilots`; add commented guidance lines for `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`, `OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=development`, `OTEL_SDK_DISABLED=true` (no collector locally).
- [x] Run the test green; run the full utils suite.
- [x] Logging coverage (`config.py`): the two import-time `print(...)` calls in `find_env_file` become `loguru.logger.debug(...)` with `path=` kwargs (the default stderr handler shows them before `setup_logging`; they are not failures).
- [x] Commit: the test.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_no_legacy_otel_env_readers.py`.

## U9 (= 1b.2, utils side) — Client instrumentors in `bootstrap`
Spec §3.3 (client spans, no botocore), §4 (before the pool); master 1b.2, probe "Pooled psycopg2 query → span"; research 01 §2.5.
**Files.** Modify `bootstrap.py` (created in U2, committable); test `test_client_instrumentors.py`; conftest unchanged.
**Interfaces.** `bootstrap.INSTRUMENTATIONS: tuple[tuple[str, str, str], ...]` = `("psycopg2", "opentelemetry.instrumentation.psycopg2", "Psycopg2Instrumentor")`, `("httpx", …, "HTTPXClientInstrumentor")`, `("requests", …, "RequestsInstrumentor")`, `("urllib3", …, "URLLib3Instrumentor")`, `("redis", …, "RedisInstrumentor")`, `("threading", …, "ThreadingInstrumentor")`; applied inside `bootstrap()` after the providers are set: names listed in `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` (comma-separated) skipped; missing package → skipped with `logger.warning("Instrumentation package missing", instrumentation=name)`; `.instrument(tracer_provider=…, meter_provider=…)` failures logged at WARNING with `instrumentation=`, `error=` and never raise; applied names recorded in `BootstrapState.instrumentations`; `_reset_for_tests` calls `.uninstrument()` on each. No `-botocore`, no `-fastapi`/`-asgi` here (api-side, U10).
**Steps.**
- [x] Write `test_client_instrumentors.py`: `bootstrap.state().instrumentations` equals the six names (fakeredis-independent); `psycopg2.connect` is wrapped (`Psycopg2Instrumentor().is_instrumented_by_opentelemetry` true); a stdlib `ThreadingHTTPServer` on `127.0.0.1:0` recording request headers: `httpx.get(url)` inside `span("outer")` → the server saw a `traceparent` whose trace id equals the outer span's and one CLIENT span with `http.request.method == "GET"` was exported; the same with `requests.get(url)` (exactly one CLIENT span — the urllib3 instrumentor is suppressed under requests); `pytest.importorskip("fakeredis")`: `fakeredis.FakeRedis().set("k", "v")` → a CLIENT span with `db.system == "redis"`; subprocess case: `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=redis,threading` → those two absent from `instrumentations`. Run — fails.
- [x] Implement. Run green. Re-run `test_bootstrap_process_env.py` (its "default" case now asserts six instrumentations).
- [x] Logging coverage: instrumentation skips and failures are WARNINGs with kwargs; the boot line (U7) lists what was applied.
- [x] Commit: `bootstrap.py` (created by U2 in this branch — commit the edit), the test.
**Test command.** `… pytest /home/aditya/Code/utils-obs/tests/unit/observability/test_client_instrumentors.py test_bootstrap_process_env.py`.
| Likely finding | Triage |
|---|---|
| Pool ordering "test" lives in api (U11), not here | intentional: the pooled query needs a live Postgres; here the connect wrapper is proven |
| DB semconv stays old (`db.system`) | intentional: opt-in is `http` only; spec §9.2 queries `db.system` |

## U10 (= 1b.1 part 1) — Gateway HTTP instrumentation module and in-process smoke
Spec §3.3 (one SERVER span, full route, health excluded), §4; master 1b.1; Facts 2–3; D1.
**Files.** Create `flynapse_api/telemetry/__init__.py`, `flynapse_api/telemetry/http_server.py`; tests `tests/integration/otel/conftest.py`, `_otel_capture_api.py`, `test_gateway_http_instrumentation.py`; edit `tests/conftest.py` (add `os.environ.setdefault("OTEL_SDK_DISABLED", "true")` at the top, before the repo-root install, so any test that reaches `setup_logging` in-process configures nothing).
**Interfaces.** `http_server.HEALTH_EXCLUDED_URLS = ("^https?://[^/]+/health/(live|ready)$",)`; `http_server.INGEST_EXCLUDED_URLS = ("/logging/(public/)?ingest/v1/(logs|traces)$",)` (Stream P hand-off: browser telemetry posts must not inflate the gateway's own spans and request metrics; `parse_excluded_urls` patterns are regex-searched against the full URL); `http_server.DEFAULT_EXCLUDED_URLS = HEALTH_EXCLUDED_URLS + INGEST_EXCLUDED_URLS`; `http_server.resolve_route(app, scope) -> str | None`: iterate `app.routes` (via `fastapi.routing.iter_route_contexts` when that public helper exists, else the list), `route.matches(scope)`; on `Match.FULL` for a `Mount` whose `app` has `routes`, recurse with the scope merged with the child scope and return `mount.path + sub_route` (or `mount.path` alone when the sub-app matches nothing); on `Match.FULL` otherwise return `route.path`; remember the last `Match.PARTIAL` path as fallback; `None` when nothing matches. `http_server.span_details(scope) -> tuple[str, dict]`: `"<METHOD> <route>"` and `{"http.route": route}` when a route resolved, else the sanitised method alone and no route attribute (mirrors upstream). `http_server.instrument_gateway(app, *, excluded_urls: Sequence[str] = (), tracer_provider=None, meter_provider=None) -> None`: refuses (`RuntimeError`) if `app.middleware_stack` is already built; idempotent via `app._flynapse_gateway_instrumented`; excluded list = given patterns plus the comma-separated `OTEL_PYTHON_EXCLUDED_URLS` value, through `opentelemetry.util.http.parse_excluded_urls`; wraps `app.build_middleware_stack` as upstream does — original stack → `OpenTelemetryMiddleware(..., default_span_details=span_details, excluded_urls=…, exclude_spans=["receive", "send"], tracer_provider, meter_provider)` → outer bare `ServerErrorMiddleware`. `http_server.uninstrument_gateway(app) -> None` (tests). The api conftest mirrors utils' (session `MonkeyPatch` sets `OTEL_SDK_DISABLED=false`, `bootstrap._reset_for_tests()`, `bootstrap("api-tests", pipelines=in-memory)`, `log_bridge.install("DEBUG", json_stdout=True)`, `intercept.install("DEBUG")`; function fixture clears exporters).
**Steps.**
- [ ] Write `test_gateway_http_instrumentation.py` with a fixture building a fresh gateway `FastAPI` (route `GET /api/v1/health`, route `GET /health/live`, route `GET /api/v1/boom` raising `RuntimeError`), a sub-app `FastAPI` with `GET /v1/chats/{chat_id}` mounted at `/api/v1/mro`, `instrument_gateway(gateway, excluded_urls=HEALTH_EXCLUDED_URLS)`, `TestClient(raise_server_exceptions=False)`. Cases: mounted GET → exactly one finished span, kind SERVER, name `GET /api/v1/mro/v1/chats/{chat_id}`, `http.route` identical, `http.request.method == "GET"`, `http.response.status_code == 200`, `url.path == "/api/v1/mro/v1/chats/abc"`; the `http.server.request.duration` point carries the same `http.route` and status; `http.server.active_requests` exists; `/health/live` → zero new spans and no new duration point; a POST to a stub route `/api/v1/core/logging/public/ingest/v1/logs` on a gateway instrumented with `DEFAULT_EXCLUDED_URLS` → zero spans and no duration point; `/api/v1/health` → route `/api/v1/health`; `/nope` → one span named `GET` without `http.route`, status 404; `/api/v1/boom` → span status ERROR with an `exception` event **and** `http.response.status_code == 500` on the span and on the duration point (the reason for the stack wrapping); `OTEL_PYTHON_EXCLUDED_URLS=/api/v1/health$` (monkeypatch before instrumenting a fresh app) excludes that route; `instrument_gateway` twice → still one span per request; a mounted sub-app that also has `OpenTelemetryMiddleware` is **not** part of this design (no test). Run — fails.
- [ ] Implement `http_server.py`; write conftest/helper; edit `tests/conftest.py`. Run green.
- [ ] Logging coverage: `instrument_gateway` logs one INFO line `Gateway HTTP instrumentation installed` with `excluded_urls=` (count) via loguru; the refusal is an exception.
- [ ] Commit: the two package files, conftest, helper, test, and the `tests/conftest.py` edit.
**Test command.** `… pytest tests/integration/otel/test_gateway_http_instrumentation.py`.
| Likely finding | Triage |
|---|---|
| Not `instrument_app` per sub-app as spec §3.3 says | deviation D1 with reasons; needs owner acknowledgement |
| Duplicates ~25 lines of upstream stack wrapping | intentional: the only way to inject `default_span_details`; pinned upstream, same Starlette dependency |

## U11 (= 1b.1 part 2) — `main.py` wiring, api config deletion, pooled-query span
Spec §3.1, §4 (bootstrap before the pool); master 1b.1, probe row; research 01 §2.7.1.
**Files.** Modify `flynapse_api/main.py`, `flynapse_api/config/config.py`, `flynapse_api/automations/worker.py` (`_configure_logging` only), `api/Dockerfile` (uncommitted); tests `tests/unit/telemetry/test_gateway_bootstrap_order.py`, `test_no_legacy_otel_config_api.py`, `tests/integration/otel/test_pool_instrumented.py`.
**Interfaces / edits.** `main.py` line 7 becomes `setup_logging("api", "development" if settings.debug else "production")`, still before every sibling import; immediately after the `FastAPI(...)` constructor: `instrument_gateway(app, excluded_urls=DEFAULT_EXCLUDED_URLS)` (import from `flynapse_api.telemetry.http_server`); the `print_routes`/"Final App Route" loop logs `logger.info("Gateway route", path=route.path)` (the current call passes `route.path` as a positional format argument and drops it). `config/config.py`: delete `otel_endpoint`, `otel_service_name`, `otel_env`, `otel_version`, `otel_enabled` (readers: only `main.py:7`, `middleware/observability.py:51-54` (deleted in U12), `worker.py:469`). `worker._configure_logging`: `setup_logging(SERVICE_NAME, "development" if api_settings.debug else "production")` (the `OTEL_SERVICE_NAME` env still wins through `resource.build`). `Dockerfile`: delete `ENV OTEL_SERVICE_NAME="copilots"` and `ENV LOG_DIR` (dead), HEALTHCHECK later (U14). Fold-in of master 0.6's gateway half (session-lead ruling): delete the `/metrics` redirect route in `main.py`, `flynapse_api/auth/metrics_scrape.py` and every reader of `METRICS_SCRAPE_TOKEN` in `api` (the `rg` sweep lists them; each deleted file/edit is reported), and `prometheus-client` from `api/pyproject.toml` (already removed in U1); the copilot-mro `/metrics` route and its `prometheus_client` import stay for Stream L.
**Steps.**
- [ ] Write `test_gateway_bootstrap_order.py` (AST over `repo_root(__file__, "flynapse_api", "main.py")`, pattern of `tests/startup/surface/test_gateway_root_surface.py`): the first module-level expression statement is a call to `setup_logging` whose first argument is the literal `"api"`, and it precedes every `Import`/`ImportFrom` of `utils.postgres_service`, `copilot_mro`, `core`, `shift_optimizer`, `routers`, `middleware`; a module-level `instrument_gateway(app, ...)` call exists and precedes every `app.mount(...)`, `app.add_middleware(...)`, `app.include_router(...)` and `setup_*_middleware(app)` call; no attribute access `settings.otel_service_name`/`otel_env`/`otel_version`. Run — fails.
- [ ] Write `test_no_legacy_otel_config_api.py`: scan `repo_root(__file__, "flynapse_api")` for `OTEL_ENDPOINT|OTEL_ENABLED|OTEL_ENV\b|OTEL_VERSION|otel_endpoint|otel_enabled|otel_env\b|otel_version|otel_service_name|prometheus_client` — no allow-list (the 0.6 gateway half is folded into this task). Run — fails.
- [ ] Write `test_pool_instrumented.py` marked `@pytest.mark.postgres`: after the session bootstrap, `get_postgres_service().fetch_one("SELECT 1 AS one")` returns `{"one": 1}` and the exporter holds one CLIENT span with `db.system == "postgresql"`, `db.statement` starting with `SELECT`, `net.peer.name`/`server.address` equal to `settings.postgres_host`; the pool must not have been opened before (assert `postgres._pool is None` at test start, else `pytest.skip` with the reason "pool opened before bootstrap in this process"). Run with `-m postgres` against the dev database named by `api/.env` (a read-only `SELECT 1`).
- [ ] Apply the edits. Run the three tests green; run `tests/startup`, `tests/unit`, `tests/middleware` green (`-m "not postgres"`).
- [ ] Logging coverage (`main.py`): fix the two positional-arg log calls; the mount `except ImportError` branches keep their WARNING but gain `error=` kwargs instead of f-string interpolation; `_startup_event`/`_shutdown_event` lines already structured. (`worker.py` covered in U15.)
- [ ] Commit: the three tests.
**Test command.** `… pytest tests/unit/telemetry/test_gateway_bootstrap_order.py tests/unit/telemetry/test_no_legacy_otel_config_api.py` and `… pytest tests/integration/otel/test_pool_instrumented.py -m postgres`.
| Likely finding | Triage |
|---|---|
| `/metrics` redirect and `prometheus-client` still present | intentional: master 0.6 owns it; optional fold-in listed in Open questions |
| The DEBUG-derived env argument | intentional (D4) |

## U12 (= 1b.3) — `X-Trace-Id`, `auth.rejections`, delete the hand-rolled metrics
Spec §3.3 (counter for gateway rejections, `X-Trace-Id` kept), §8 G20/G19; master 1b.3; D5.
**Files.** Create `flynapse_api/middleware/telemetry.py`; delete `flynapse_api/middleware/observability.py`; modify `middleware/__init__.py`, `main.py` (uncommitted); tests `tests/middleware/telemetry/test_trace_id_header.py`, `test_auth_rejection_metric.py`; edit `tests/middleware/skip_paths/test_anonymous_skip_path_stack.py` (replace the `ObservabilityMiddleware.dispatch` hop with `TraceIdHeaderMiddleware` driven as ASGI, or drop the hop and keep the auth→endpoint assertion — the test's subject is the skip path, not observability; choose the latter and say so in its docstring).
**Interfaces.** `middleware.telemetry.TRACE_ID_HEADER = "X-Trace-Id"`; `TraceIdHeaderMiddleware` (pure ASGI): on `http.response.start`, when `trace.get_current_span().get_span_context().is_valid`, append the 32-hex trace id header; never raises. `REJECTION_STATUSES = frozenset({401, 403})`; `AuthRejectionMetricMiddleware` (pure ASGI): on `http.response.start` with a status in the set and `"endpoint" not in scope`, `auth_rejections.add(1, {"http.response.status_code": status, "http.request.method": method})` where `auth_rejections = registry.counter("auth.rejections", "{request}", "Requests refused by gateway middleware before routing")` at module level. `setup_trace_id_header(app)` and `setup_auth_rejection_metric(app)`. `middleware/__init__.py` exports them and drops `ObservabilityMiddleware`/`setup_observability_middleware`. `main.py` add-order becomes: Security → TraceIdHeader (where Observability was) → Logging → [Auth] → AuthRejectionMetric (added right after Auth so it executes before it) → RateLimit → RequestID → CORS → ProxyHeaders; execution order therefore Proxy → CORS → RequestID → RateLimit → AuthRejectionMetric → Auth → Logging → TraceIdHeader → Security → routes, all inside the OTel middleware.
**Steps.**
- [ ] Write `test_trace_id_header.py`: mini gateway from U10's helper plus `setup_trace_id_header` → response `x-trace-id` equals the exported span's trace id in hex; with `uninstrument_gateway` (no span) → header absent, 200 still served. Run — fails.
- [ ] Write `test_auth_rejection_metric.py`: mini gateway with a pure-ASGI stub "auth" middleware that returns 401 for `Authorization`-less requests before routing, one route returning 403, `setup_auth_rejection_metric` outside the stub → after one anonymous request the `auth.rejections` point has value 1 with `{http.response.status_code: 401, http.request.method: "GET"}`; after the route-level 403 the value is unchanged; the in-memory reader contains none of `http_requests_total`, `http_request_duration_seconds`, `active_sessions`, `active_users` after both requests. Run — fails.
- [ ] Implement, delete `observability.py`, update `__init__.py`, `main.py`, and the skip-path test. Run the two tests plus `tests/middleware` green.
- [ ] Logging coverage: the deleted module had five silent `except Exception: pass` blocks — gone; the two new middlewares have no failure path that should log (a missing span is normal).
- [ ] Commit: `middleware/telemetry.py`, two tests, the skip-path test edit.
**Test command.** `… pytest tests/middleware/telemetry/test_trace_id_header.py tests/middleware/telemetry/test_auth_rejection_metric.py tests/middleware/skip_paths/test_anonymous_skip_path_stack.py`.
| Likely finding | Triage |
|---|---|
| 401/403 still produce spans | deviation D1 consequence; counter still delivered |
| `endpoint`-in-scope heuristic | intentional, tested; documented in the docstring |

## U13 (= 1b.4) — Request identity on the server span
Spec §3.1 (`request.id`, `tenant.id`, `enduser.id`, `session.id`), §3.3 bound context; master 1b.4.
**Files.** Create `flynapse_api/telemetry/request_identity.py`; modify `middleware/logging.py` (uncommitted: import + one call inside the `contextualize` block, plus the logging-coverage fix); test `tests/middleware/telemetry/test_request_identity_span_attributes.py`.
**Interfaces.** `request_identity.UNKNOWN = "unknown"`; `request_identity.bind_request_identity_to_span(*, request_id, tenant_id, user_id, session_id) -> None`: sets `request.id`, `tenant.id`, `enduser.id`, `session.id` on `trace.get_current_span()` for each value that is truthy and not `UNKNOWN`; no-op when the span is not recording. Called from `LoggingContextMiddleware.__call__` with the values it already extracts (why not a `server_request_hook`: with D1 the hook runs before Auth/RequestID populate `scope["state"]`; recorded deviation from master 1b.4 wording).
**Steps.**
- [ ] Write the test: mini instrumented gateway with a stub pure-ASGI middleware that writes `scope["state"]["request_id"]`, `["session_id"]` and `["auth_context"] = {"tenant_id": …, "user_id": …}`, then `LoggingContextMiddleware`, then a route → the SERVER span has the four attributes; with `auth_context` `None` and no session → only `request.id`; `"unknown"` values are not set; the in-memory log record for "Request received" carries `tenant.id`/`request.id` (bridge) and the span's trace id. Run — fails.
- [ ] Implement; edit `logging.py`. Run green plus `tests/middleware`.
- [ ] Logging coverage (`middleware/logging.py`): the completion line logs at WARNING when `status_code >= 500`, INFO otherwise, keeping `status_code`/`duration` kwargs; the failure line keeps `error=`/`traceback=`; `request_id.py` (touched? no — its interpolated warning is listed under Future Improvements for L/owner, not edited here).
- [ ] Commit: `request_identity.py`, the test.
**Test command.** `… pytest tests/middleware/telemetry/test_request_identity_span_attributes.py`.

## U14 (= 1b.5) — `/health/live` and `/health/ready`
Spec §4 (health), §8 G28; master 1b.5; D7.
**Files.** Create `flynapse_api/routers/health.py`; modify `main.py` (include the router with no prefix), `api/Dockerfile` HEALTHCHECK → `/health/live` (uncommitted); test `tests/api/health/test_health_probes.py`; edit `tests/startup/surface/test_gateway_root_surface.py` (`ROOT_LEVEL_ALLOWLIST` gains `/health/live` and `/health/ready` with the reason: orchestrator probes hold no token, so they must live outside `api_prefix`; the auth middleware already skips `/health` at the root).
**Interfaces.** `health.LIVE_PATH = "/health/live"`, `health.READY_PATH = "/health/ready"`, `health.router` (`APIRouter(tags=["Platform"])`); `GET /health/live` → 200 `{"status": "alive", "service": "api"}` touching nothing; `health._aggregate_probe()` returns `copilot_mro.app.api.health_check.health_check` (imported inside the function so tests monkeypatch the seam and the module stays import-light); `health.readiness_verdict(body: dict) -> bool` (D7); `GET /health/ready` → awaits the probe, returns its body verbatim with status 200 or 503; if the probe raises, 503 with `{"status": "unhealthy", "error": "<type name>"}` and one `logger.error("Readiness probe failed", error=traceback)`; the body never contains a `debug` key (asserted).
**Steps.**
- [ ] Write `test_health_probes.py`: a `FastAPI` with `health.router` included; `/health/live` → 200 and the exact body, with `health._aggregate_probe` monkeypatched to raise (proving live never calls it); `/health/ready` with a fake probe returning `status=healthy` and per-dependency verdicts → 200, body passthrough, `"debug" not in body`; `degraded` with postgres healthy → 200; `degraded` with postgres unhealthy → 503; `unhealthy` → 503; probe raising → 503 with the error shape; the surface test's allowlist contains both paths. Run — fails.
- [ ] Implement; include the router in `main.py` after the gateway routers; update the surface allowlist and Dockerfile. Run green plus `tests/startup`.
- [ ] Logging coverage: the readiness failure log with `error=`; live logs nothing (probe noise).
- [ ] Commit: `routers/health.py`, the test, the surface-test edit.
**Test command.** `… pytest tests/api/health/test_health_probes.py tests/startup/surface/test_gateway_root_surface.py`.
| Likely finding | Triage |
|---|---|
| Existing `{api_prefix}/health` stub kept | intentional (Dockerfile HEALTHCHECK compatibility until deploy files move); Future Improvements |
| Readiness rule | decision D7; owner may override |

## U15 (= 1b.6) — Automation run root span and bound log context
Spec §3.3 (background roots with `tenant.id`, links), §4; master 1b.6; research 01 §2.6.
**Files.** Create `flynapse_api/telemetry/run_span.py`; modify `automations/executor.py` (wrap the body of `execute_automation_run`), `automations/worker.py` (docstring "Structured logging" paragraph, `_configure_logging` already edited in U11) (uncommitted); tests `tests/integration/otel/test_automation_run_span.py`, `tests/unit/telemetry/test_worker_service_name.py`.
**Interfaces.** `run_span.SPAN_NAME = "automation.run"`; `run_span.automation_run_span(automation: Automation, run_id: str, scheduled_for: datetime) -> ContextManager[Span]`: `get_tracer("flynapse_api.automations").start_as_current_span(SPAN_NAME, kind=INTERNAL, links=())` with attributes `tenant.id`, `enduser.id` (= `automation.user_id`), `automation.id`, `automation.run_id`, `automation.kind`, `automation.department` (when set), `automation.scheduled_for` (ISO), combined through `contextlib.ExitStack` with `logger.contextualize(tenant_id=…, user_id=…, session_id=f"automation:{run_id}", automation_id=…, automation_run_id=run_id, department=…)`. `execute_automation_run` wraps its existing try/except in the context manager and sets `automation.run.status` to the terminal status on both the normal and the containment path (the containment path also records the exception via the span). A new trace root: the worker has no current span; embedded mode's scheduler task likewise.
**Steps.**
- [ ] Write `test_automation_run_span.py`: build a real `Automation` (fields as in `tests/integration/automations/test_execute_automation_run.py:_automation`), monkeypatch `executor_module._run` with an async fake that emits one `logger.info("fake run")` and returns `"completed"`, and `executor_module._recorder` with a stub returning a recording callable; `await execute_automation_run(automation, RUN_ID, SLOT)` → exactly one span, name `automation.run`, `parent is None`, kind INTERNAL, the attribute set above, `automation.run.status == "completed"`; the fake's log record in the in-memory exporter carries `tenant.id`, `enduser.id`, `session.id == "automation:<RUN_ID>"`, `automation_id`, `automation_run_id` and the span's trace id; second case: the fake raises → status `"failed"` returned, `automation.run.status == "failed"`, one exception event, the recorder stub called once with `STATUS_FAILED`. Run — fails.
- [ ] Write `test_worker_service_name.py`: AST over `automations/worker.py` asserts `SERVICE_NAME == "automation-worker"` and that `_configure_logging` calls `setup_logging` with `SERVICE_NAME` as its first argument and no `os.getenv` wrapper; runtime: `bootstrap`'s resource for `"automation-worker"` yields `service.name == "automation-worker"` when `OTEL_SERVICE_NAME` is unset (monkeypatch). Run — fails.
- [ ] Implement; edit executor/worker. Run green plus `tests/integration/automations -m "not postgres"` (the lane's conftest patches the ledger; the span wrapper must not change any outcome there).
- [ ] Logging coverage (executor lifecycle boundaries): the "starting run" line (`executor.py:981`) and the containment error (`:964`) become structured (`automation_id=`, `run_id=`, `slot=`, `department=` kwargs; the ids are also in the bound context now); `worker.py:435` "Automation worker running" and `:372/:397` warnings become kwargs (`tick_seconds=`, `concurrency=`, `pid=`, `error=`). The remaining f-string logs in `executor.py` (dozens) go to Future Improvements with the note "convert as the module is next touched by Stream L".
- [ ] Commit: `run_span.py`, the two tests.
**Test command.** `… pytest tests/integration/otel/test_automation_run_span.py tests/unit/telemetry/test_worker_service_name.py`.
| Likely finding | Triage |
|---|---|
| No `Link` to a scheduling span | intentional per master 1b.6 (lands in L) |
| Span kind INTERNAL not CONSUMER | intentional: no messaging system; documented |

## U16 — Auth skip list for the anonymous ingest sub-paths (Stream P hand-off)
Spec §3.4 (anonymous browser ingest through the gateway); phase 5 plan D7 and its hand-off table.
**Files.** Modify `flynapse_api/middleware/auth.py` (`_should_skip_auth` `skip_exact`; uncommitted); test `tests/middleware/skip_paths/test_public_ingest_skip_paths.py`.
**Interfaces.** `skip_exact` gains exactly two entries, `{api_prefix}/core{core_prefix}/logging/public/ingest/v1/logs` and `{api_prefix}/core{core_prefix}/logging/public/ingest/v1/traces` (spelled with the same prefix helpers the existing `.../logging/public/ingest` entry uses), and the old `.../logging/public/ingest` entry is removed in the same edit; the authenticated `.../logging/ingest/v1/*` routes are NOT skipped. `/health/live` and `/health/ready` are also asserted skipped (U14 relies on the root `/health` rule — if that rule is exact-match, add the two paths here and say so).
**Steps.**
- [ ] Write the test in the pattern of `tests/middleware/skip_paths/test_anonymous_skip_path_stack.py`: the two public sub-paths reach the endpoint without a token; the two authenticated sub-paths return 401 without a token; the retired `.../logging/public/ingest` path is no longer skipped; `/health/live` and `/health/ready` reach their endpoints without a token. Run — fails.
- [ ] Edit `auth.py`; run the test and the whole `tests/middleware` lane green.
- [ ] Logging coverage: the skip path emits no log line per request (unchanged); the auth refusal path keeps its structured WARNING.
- [ ] Commit: the test only.
**Test command.** `… pytest tests/middleware/skip_paths/test_public_ingest_skip_paths.py`.

## Phase close (Stream U)
- [ ] Full suites: `… pytest /home/aditya/Code/utils-obs/tests -q` and `… pytest tests -q -m "not postgres"` from the bundle; `-m postgres` for `test_pool_instrumented.py` against the dev database.
- [ ] Adversarial review per master §12 with this plan and both diffs; triage into Future Improvements / fixes.
- [ ] Implementation notes into master §15: D1 deviation, D6 renaming, pool laziness correction, `-fastapi`/`-logging` not added.

## Hand-offs to other streams
- **Stream I (compose/iac):** replace `OTEL_ENDPOINT=…:4317` with `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318` (`deployment/poc/docker-compose.yml:178`, `iac/apprunner.tf:42`, `iac/lambda.tf:109`); add `OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=<env>`; App Runner health path `/health/live`; `base.yaml` redaction allow-list must include `tenant.id`, `enduser.id`, `session.id`, `request.id`, `automation_id`, `automation_run_id`, `chat_id`, `block_id`, `department`; health filter drops `http.route` matching `/health/(live|ready)`; the `job` label is `flynapse/<service.name>` with names `api` and `automation-worker`.
- **Stream L (after Gate M):** copilot-mro `config.py:950-956` `otel_*` fields and `chat_management.py` three-argument `get_tracing_service(...)` calls keep working through the shims; retire `set_gauge` in `document_hub/operations.py`; `request_id.py:54` interpolated warning; `test-observability.py` generator.
- **Phase 6 dashboards:** `http.server.request.duration` (seconds, new semconv) keyed by `http.route` = full mounted route; `http.server.active_requests`; `auth.rejections` `{request}`; DB spans use `db.system`.

## Uncommitted-edit ledger (pre-existing production files; reported, not committed)
utils: `pyproject.toml`, `poetry.lock`, `utils/config.py`, `utils/logging_config.py`, `utils/observability/__init__.py`, `utils/observability/metrics.py`, `utils/observability/tracing.py`, `.env.sample`. api: `pyproject.toml`, `poetry.lock`, `flynapse_api/main.py`, `flynapse_api/config/config.py`, `flynapse_api/middleware/__init__.py`, `flynapse_api/middleware/logging.py`, `flynapse_api/middleware/observability.py` (deleted), `flynapse_api/automations/worker.py`, `flynapse_api/automations/executor.py`, `Dockerfile`.

## Decisions recorded for the owner (deviations from spec/master wording)
1. D1 — single mount-aware gateway instrumentation instead of per-sub-app `instrument_app`; 401/403 requests therefore carry a span (counter still emitted).
2. D6 — identity log keys renamed to the semconv spellings on the wire.
3. D10 — `-fastapi` and `-logging` not added/activated.
4. 1b.4 attributes set from `LoggingContextMiddleware`, not a `server_request_hook` (hook fires pre-auth under the outermost placement).
5. The pool is lazy (`postgres_service.py:104/:234`); the invariant enforced is "bootstrap before the first pooled query".

## Open questions for the owner
Session-lead defaults (2026-09-05, owner not at the keyboard — the implementer proceeds on these unless overruled): 1 — fold the api half of 0.6 into U11 (done above); the copilot-mro half stays with Stream L. 2 — D7 accepted.

1. Fold master 0.6's gateway half (`/metrics` redirect, `auth/metrics_scrape.py`, `prometheus-client` in `api/pyproject.toml`) into U11 now, or leave it to Stream L as assigned?
2. Readiness verdict D7 (Postgres hard, other dependencies soft) — confirm or change before U14.

## Implementation notes (Stream U implementer: Claude Fable 5.1, 2026-09-05)

### U0 — worktrees and the bundle
Done as specified, with one structural deviation forced by Poetry: the bundle's sibling entries
`wt-obs-u/{copilot-mro,core,shift-optimizer}` are **real directories whose top-level entries are
symlinks into the main checkouts** (everything except `.git`), not directory symlinks. Poetry
canonicalises a directory symlink with `Path.resolve()`, so a dir-symlinked `copilot-mro` resolved
to `/home/aditya/Code/copilot-mro`, whose own `../utils` then named the MAIN utils checkout while
the api's `../utils` named `utils-obs` — two sources for `flynapse-utils`, and `poetry lock` failed
on the conflict. With real directories the transitive `../utils` stays inside the bundle and every
path dependency agrees on `utils-obs`. `utils` itself stays a plain symlink (no transitive path
deps of its own are re-resolved through it). Both worktrees at their base SHAs; `utils-obs/` and
`wt-obs-u/` appended to the workspace `.git/info/exclude`.

### U1 — pins, lock, install, drift tests
As planned. Both pyprojects edited (uncommitted); `poetry lock` in `utils-obs` (no install);
`poetry lock` + `poetry install` in the bundle (fresh in-project `.venv`, ~9 min; `git status`
clean of `.venv/`). Installed and verified: sdk 1.44.0, psycopg2/test-utils 0.65b0. Pin tests were
run RED first from the shared env (worktree PYTHONPATH), then GREEN from the bundle. Full utils
suite from the bundle: **981 passed** (includes the U2 files, which landed before the full-suite
run). The api drift test tolerates an installed `-fastapi` at exactly 0.65b0 (it arrives through
copilot-mro's pyproject until Stream L retires it) — D10 recorded. Note every pytest invocation
needs `POSTGRES_DB=copilot_mro_test` beside `DEBUG=false`: the utils/api db_guard refuses a run
that names no test database (the plan's standard commands omit it).
Learning: at contrib 0.65b0 the api pip-index probes for `-psycopg2`/`-test-utils`/`-threading`
printed nothing from `pip index versions` (only sdk did), but all resolved fine at lock time.

### U2 — resource.py and bootstrap.py
As planned. `resource.build` implements D3 by filling only the keys the env detector did not set,
then merging a bare namespace-only Resource last (a `Resource.create` there would re-apply the
`unknown_service` fallback over the real name). `bootstrap` checks `OTEL_SDK_DISABLED` BEFORE the
protocol validation, so a disabled process never refuses to boot over a stray protocol value; the
state records the env protocol unvalidated in that case. The instrumentation-application loop and
its warning paths were written in U2 (inert while `INSTRUMENTATIONS` is empty); U9 fills the
registry. One SDK 1.44 fact the plan predicted slightly differently: `InMemoryLogExporter` no
longer lives in a `in_memory_log_exporter` submodule and is deprecated in favour of
`InMemoryLogRecordExporter`, which the conftest uses. Subprocess cases cap
`OTEL_EXPORTER_OTLP_TIMEOUT=1` so atexit flushes against no collector cannot stall a case.
Logging coverage: bootstrap logs nothing itself (sinks do not exist yet); the protocol refusal
names the variable and the remedy; instrumentor skips/failures are structured WARNINGs.

Commits so far: utils `31f4a5e` (U1 test), `31aafed` (U2); api `c16eec1` (U1 test).
Uncommitted pre-existing edits so far: utils `pyproject.toml`, `poetry.lock`; api `pyproject.toml`,
`poetry.lock`.

### U3 — registry.py and the legacy shim
As planned, with two recorded adjustments. (1) The compat test's warning assertions capture
loguru directly through a test sink: the plan sequenced the in-memory-log-exporter assertion
ahead of its own dependency (the bridge lands in U5). (2) The observable-gauge forbidden-key
"raises at collection" is real but contained: the wrapped callback raises `AttributeKeyError`,
and the SDK's callback guard converts that into a logged error and a dropped batch — the test
pins the observable outcome (no point recorded). `set_gauge` stays the up-down-counter mimicry
deliberately (G19 semantics preserved for the one Stream-L-owned caller; Future Improvements).

### U4 — tracing helpers and package exports
As planned. One structural fact worth knowing estate-wide: exporting the `bootstrap` FUNCTION
from `utils/observability/__init__` shadows the `bootstrap` SUBMODULE as a package attribute
(`import utils.observability.bootstrap as m` binds the function on Python 3.7+). Consumers that
need module attributes import from the submodule (`from utils.observability.bootstrap import
bootstrap, state`); the test conftest binds the module via `importlib.import_module`.

### U5 — log_bridge.py
As planned (custom serializer, not `serialize=True` — the stock one nests `extra`). SDK 1.44
facts: `InMemoryLogExporter` is deprecated/renamed (`InMemoryLogRecordExporter`, no longer in a
private submodule), and the SDK's own `LoggingHandler` is deprecated in favour of the
`-logging` package that D10 excludes — inert at the exact pins, but the next SDK bump must
revisit D10. Subprocess cases cap `OTEL_EXPORTER_OTLP_TIMEOUT=1`.

### U6 — intercept.py
As planned, two corrections against the plan's predicted spellings: SDK 1.44 emits the NEW
code-attribute names — `code.function.name`, `code.file.path`, `code.line.number` (not
`code.function`/`code.filepath`) — which Stream I's redaction allow-list and Phase 6 dashboards
must use; and the opentelemetry stderr wall uses a late-binding handler (looks up `sys.stderr`
at emit time) so capture/redirection is honoured. The frame walk uses the canonical loguru
recipe; the idempotence test counts InterceptHandlers only (pytest's own LogCaptureHandlers
ride the root at test time).

### U7 — setup_logging delegation
As planned, except the "Telemetry configured" assertion runs in a fresh subprocess (in this
session the conftest owns the first bootstrap, so no in-process call can see
`configured_by_this_call=True`; the plan's in-memory-exporter wording could not hold). The
full-suite run exposed a REAL defect this task fixed: `bootstrap._reset_for_tests()` replaced
the API proxy globals but left the registry's cached instrument handles bound to the dead
proxy, so metrics emitted after a reset silently vanished (surfaced as order-dependent
failures when `tests/unit/metering` preceded the observability lane) — the registry cache is
now cleared with the globals. Learning: every pytest command needs `POSTGRES_DB=copilot_mro_test`.

### U8 — utils.config deletion
As planned. The three `print(...)` calls in `find_env_file` became loguru debug/warning with
`path=` kwargs; `log_dir` deleted with the telemetry fields; `.env.sample` rewritten to the
standard contract (commented `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_RESOURCE_ATTRIBUTES` /
`OTEL_SDK_DISABLED=true` guidance). The scan test is text-level (comments and docstrings count),
so two of this branch's own module docstrings were reworded to stop naming the dead spellings.

### U9 — client instrumentors
As planned: the six instrumentors applied inside `bootstrap` after the providers, skips and
failures as structured WARNINGs, `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` honoured (subprocess
case), `_reset_for_tests` uninstruments. Verified live in-process: httpx propagates
`traceparent` matching the outer span; requests emits exactly ONE client span (nested urllib3
suppressed); fakeredis commands carry `db.system=redis` (old DB semconv — opt-in is `http`
only, as designed).

**Phase 1a closed 2026-09-05: full utils suite from the bundle env = 1076 passed, 0 failed.**
Commits (utils obs-utils): U1 `31f4a5e`, U2 `31aafed`, U3 `ee0c42f`, U4 `3c81e4c`, U5 `1ec6442`,
U6 `8052c39`, U7 `14d0c41`, U8 `9ec1aac`, U9 `5b114a3`.
Uncommitted utils edits so far: `pyproject.toml`, `poetry.lock`, `.env.sample`, `utils/config.py`,
`utils/logging_config.py`, `utils/observability/__init__.py`, `utils/observability/metrics.py`,
`utils/observability/tracing.py`.
