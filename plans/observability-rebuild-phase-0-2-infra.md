# Observability rebuild — Stream I detail plan (Phase 0 infra half, Phase 2, Phoenix 7.1)

**Amendments by the session lead (2026-09-05, before dispatch):** `attributes/browser_identity` must `upsert`; the browser-forward contract names the core setting `OTEL_BROWSER_FORWARD_ENDPOINT` (port 4319) so it cannot be confused with the app's own OTLP endpoint; A7 also adds that variable to the `core`/`api` service env in every compose file that runs the api.

**Master-plan tasks covered:** 0.1, 0.2, 0.3, 0.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 7.1.
**Spec sections:** §3 (architecture/invariant), §5 (collector profiles and infrastructure), §8 (security/hygiene G17/G18/G30/G31), §9.1 (Grafana's role per profile), §12 (probes). Rulings 1, 2, 11, 13, 14 apply verbatim.
**Master plan:** `docs/plans/observability-rebuild.md` §4 (0.1–0.4), §6 (2.1–2.8), §11 (7.1), §11a (standing rules), §13 (probes).
**Research grounding:** research 01 G17a–e/G31/G32, research 02 Part 3 (compose stacks + Terraform wiring), research 04 §1 (CloudWatch OTLP/sigv4/Transaction Search) and §4 (confmap merge rule, processors), research 06 (Claude Code CLI metric/event names).

| Worktree | Path | Branch (base) | Scope |
|---|---|---|---|
| A | `/home/aditya/Code/copilot-mro-obs-infra` | `obs-infra` (from `langgraph-merge`) | `deployment/**`, `tests/integration/otel/**`, plus the two scope extensions in §2 |
| B | `/home/aditya/Code/iac-obs` | `obs-iac` (from `main`) | whole repo (Terraform root + `modules/`) |

---

## 1. Inherited constraints (every task)

1. Application code never learns the backend. Only the overlay and IaC know it. OTLP/HTTP only; gRPC is dropped app-side.
2. No user content in any log line; no `session_id`/`user_id`/`enduser.id`/raw path on any metric; units declared; `{USD}` not `USD`.
3. Every image pinned to the **latest stable release verified at task time** from the project's release page (§11a). Never `:latest`, never "the version that runs today" for the observability set. Versions + release dates + bump policy live in `deployment/otel/VERSIONS.md`.
4. **Logging coverage (§11a):** every task carries a logging-coverage checkbox. For this stream it means: shell scripts run under `set -euo pipefail` and echo one line per lifecycle boundary (start / finish / fail) with the artefact name; no silent failure branches; the collector's own telemetry stays at `info` with exporter failures visible; pytest fixtures dump container logs on failure instead of swallowing them; no secret or user content is echoed.
5. Git: commit only files you created plus test edits, by pathspec (`git add <paths> && git commit -- <paths>`), never `-A`/`-a`. Check `git diff --cached --name-only` before every commit. Edits to pre-existing files (the four compose files, `loki-config.yaml`, `tempo.yaml`, `prometheus.yml`, `README.md`, every `.tf`, both `*_ec2_setup.sh`) stay **uncommitted** and are listed in the implementation report. Two named exceptions in §2.
6. Terraform is validated with `terraform fmt -check`, `terraform init -backend=false`, `terraform validate` **only**. `terraform plan` and `terraform apply` are OWNER STEPS — the main root (`infra/main.tfstate`) is documented as **de-synced from live AWS and deliberately not resynced** (`iac/gpu-host/README.md` lines 8–13), so a plan taken by anyone but the owner is not a review artefact.
7. Never run `poetry install` in worktree A. This stream ships no Python package code; the tests run from the shared `api` env, which already carries `pyyaml 6.0.3`, `httpx 0.28.1`, `pytest 8.4.2`.
8. One implementer per worktree. Do not touch another stream's worktree.

## 2. Two deliberate scope extensions (state them in the report)

- **`.github/workflows/otelcol-validate.yml`** in worktree A. Master plan §6 lists "CI job `otelcol-validate`" among Phase 2's files, and a workflow cannot live under `deployment/`. It is a new file → committed.
- **`copilot-mro/pyproject.toml`**, one added entry in `[tool.pytest.ini_options] markers`. The repo runs `--strict-markers`, and that file's own comment rules that marker registration must happen there rather than in a conftest, so an unregistered `compose_stack` marker makes the smoke uncollectable. Treated as a test edit → committed, and named explicitly in the report as the single pre-existing file this stream commits.

## 3. Setup and the standing test command

**A0 — worktree A.** `git worktree add /home/aditya/Code/copilot-mro-obs-infra -b obs-infra langgraph-merge` from `/home/aditya/Code/copilot-mro`; symlink `.env` from the main checkout; append the worktree path to the main checkout's `.git/info/exclude`. Never nested, never the EnterWorktree tool.

**B0 — worktree B.** `git worktree add /home/aditya/Code/iac-obs -b obs-iac main` from `/home/aditya/Code/iac`; append the path to `.git/info/exclude`. `dev.tfvars` is tracked and already present; `.terraform.lock.hcl` is gitignored, so the provider version resolves at `init` time (probe B1c depends on this).

**Standing pytest command** (every worktree-A test task), run from the shared env with `PYTHONPATH` pinned to the worktree so namespace packages cannot resolve into the main checkout:

`cd /home/aditya/Code/api && DEBUG=false PYTHONPATH=/home/aditya/Code/copilot-mro-obs-infra poetry run pytest /home/aditya/Code/copilot-mro-obs-infra/tests/integration/otel/<file> -q`

The compose smoke additionally needs `OTEL_COMPOSE_SMOKE=1` in that environment.

**Standing validate command** (worktree A, collector configs): `docker run --rm --env-file deployment/otel/env/<profile>.env.example -v <abs worktree>/deployment/otel:/etc/otel:ro otel/opentelemetry-collector-contrib:0.160.0 validate --config=/etc/otel/base.yaml --config=/etc/otel/backend-<profile>.yaml`. Repeated `--config` merges maps and **replaces lists** (research 04 §4.3) — this is the whole reason overlays restate pipelines.

## 4. Pinned versions (verified 2026-09-05 from release pages / Docker Hub tag endpoints)

| Image | Pin | Released | Source checked |
|---|---|---|---|
| `otel/opentelemetry-collector-contrib` | `0.160.0` | 2026-09-02 | `opentelemetry-collector-releases` latest release; tag exists on Docker Hub (digest `sha256:799dc6cf…`) |
| `prom/prometheus` | `v3.14.0` | 2026-08-18 | prometheus/prometheus latest release; tag verified |
| `grafana/loki` | `3.7.7` | 2026-08-27 | grafana/loki latest release; tag verified |
| `grafana/tempo` | `3.0.3` | 2026-08-13 | grafana/tempo latest release; tag verified |
| `grafana/grafana` | `13.2.1` | 2026-09-01 (image), release 2026-09-02 | grafana/grafana latest release; tag verified |
| `arizephoenix/phoenix` | `version-20.8.0` | 2026-09-04 | `arize-phoenix-v20.8.0`; Docker Hub uses the `version-<semver>` convention |
| `dpage/pgadmin4` | `9.17` | 2026-07-31 | Docker Hub tags |
| `portainer/portainer-ce` (in `iac/demo_ec2_setup.sh`) | `2.45.0` | 2026-08-27 | Docker Hub tags |
| `naaive/weaviate-ui` | `v1.0.3` | 2023-09-14 (last release) | Docker Hub tags |
| `rediscommander/redis-commander` | `latest@sha256:19cd0c49f418779fa2822a0496c5e6516d0c792effc39ed20089e6268477e40a` | 2021-07-26 | no semver tags exist; digest pin is the only reproducible form |
| `redis`, `postgres` | already pinned (`7.2-alpine`, `16-alpine`) | — | leave |
| `semitechnologies/weaviate` | **exception — OWNER STEP** | — | 1.39.2 (2026-08-26) is current, but this is the RAG data plane with an on-disk index; pin to the version actually running, read by the owner with `docker image inspect semitechnologies/weaviate:latest --format '{{index .RepoDigests 0}}'` and `curl -s localhost:8080/v1/meta` on the demo and POC boxes. Record both in `VERSIONS.md` with the reason. The owner may override and take 1.39.2. |

`VERSIONS.md` bump policy to write: re-verify every image's latest stable on the first working day of each month; bump in one commit; run the A8 compose smoke; record the new version, its release date and the smoke result in the file's changelog table.

## 5. Corrections to the master plan that this plan applies (each verified against the pinned component)

1. The processor id is **`delta_to_cumulative`**, not `deltatocumulative` (contrib `metadata.yaml` `type: delta_to_cumulative`; the directory name is `deltatocumulativeprocessor`).
2. The Azure auth extension type is **`azure_auth`** (`azureauth` is the deprecated alias), stability beta — the master plan's spelling is right, worth pinning here because the alias is what most examples show.
3. `filter` drops **whole items**; it cannot delete an attribute. Stripping `gen_ai.input.messages` / `gen_ai.output.messages` from non-content pipelines is an `attributes` processor with `action: delete`. `filter` is still used, on whole spans, for health routes and for keeping/dropping the content copies.
4. "Pipelines `browser/*` and `content`" become the legal pipeline ids **`traces/browser`, `logs/browser`, `traces/content`** (a pipeline id is `<signal>[/name]`).
5. `prometheusremotewrite` **drops delta monotonic sums, histograms and summaries outright**, and derives `job` from `service.namespace`/`service.name` and `instance` from `service.instance.id` — so `delta_to_cumulative` must precede it, and the smoke's "delta arrives cumulative" assertion is proved by the series *existing at all*.
6. Master 0.2's "a log older than retention is not queryable" is **not** assertable in a smoke: Loki deletes on a compaction cycle, and backdated samples are refused by `reject_old_samples_max_age`. Replaced with: a log written now is queryable, **and** Loki's `/config` endpoint reports `retention_enabled: true` with the configured `retention_period`. Deviation recorded with this reason.
7. Master 2.2's "scrape config reduced to self" becomes **self + the collector's own telemetry endpoint** (`otel-collector:8888`, unpublished, inside the compose network). The §9.2 platform-health view needs collector/exporter health, and the removed `9464` Prometheus exporter was where it used to come from.
8. `aws_instance.weaviate_observability` has **no `iam_instance_profile`** today (`ec2.tf:2–36`) — the collector cannot sigv4-sign anything until B3 adds one. The master plan says "instance role gains the permissions"; there is no role to gain them.
9. `waf.tf`'s entire Web ACL, its rules and its outputs are **commented out** (lines 54–180); only the two `aws_wafv2_ip_set` resources are live. Research 02 §3.2 reads as though the ACL exists. WAF logging is therefore authored behind a variable (B8), not attached to a resource that does not exist.

---

## 6. File structure

### Worktree A (copilot-mro, `obs-infra`)

**Create:** `deployment/otel/base.yaml`; `deployment/otel/backend-oss.yaml`; `deployment/otel/backend-aws.yaml`; `deployment/otel/backend-azure.yaml`; `deployment/otel/content-phoenix.yaml`; `deployment/otel/VERSIONS.md`; `deployment/otel/README.md`; `deployment/otel/validate.sh`; `deployment/otel/env/oss.env.example`; `deployment/otel/env/aws.env.example`; `deployment/otel/env/azure.env.example`; `deployment/otel/smoke/docker-compose.smoke.yml`; `.github/workflows/otelcol-validate.yml`; `tests/integration/otel/test_compose_image_pins.py`; `tests/integration/otel/test_retention_config.py`; `tests/integration/otel/test_compose_port_bindings.py`; `tests/integration/otel/test_collector_base_config.py`; `tests/integration/otel/test_collector_profiles.py`; `tests/integration/otel/test_profile_env_documented.py`; `tests/integration/otel/test_oss_profile_smoke.py`; `tests/integration/otel/conftest.py`.

**Modify (uncommitted, reported):** `deployment/observability-local/observe-docker-compose.yml`; `deployment/docker-compose.yml`; `deployment/poc/docker-compose.yml`; `deployment/demo/docker-compose.yml`; `deployment/observability-local/loki-config.yaml`; `deployment/observability-local/tempo.yaml`; `deployment/observability-local/prometheus.yml`; `deployment/observability-local/README.md`; `deployment/observability-local/grafana/provisioning/datasources/datasources.yml`.
**Modify (committed, §2 exception):** `pyproject.toml` (one marker entry).
**Delete:** `deployment/observability-local/otel-collector-config.yaml` (superseded by base+overlay, task A7).

One responsibility per new file: `base.yaml` = receivers/processors/telemetry only, never pipelines; each `backend-*.yaml` = exporters + auth extensions + the complete `service.extensions`/`service.pipelines`; `content-phoenix.yaml` = the Phoenix exporter, its project-routing transform and the `traces/content` pipeline, appended as a third `--config` only where Phoenix exists; `validate.sh` = iterate profiles, nothing else; one test file per property.

### Worktree B (iac, `obs-iac`)

**Create:** `otel_gateway.tf` (instance profile, role, policies, Route 53 private zone/record); `cloudwatch.tf` (log groups, retention variable, `aws/spans` resource policy, WAF log group + logging configuration); `modules/otel-gateway/{main.tf,variables.tf,outputs.tf,README.md}`; `modules/otel-gateway/examples/basic/{main.tf,variables.tf}`; `scripts/otel_probe.sh`.
**Modify (uncommitted, reported):** `ec2.tf` (SG trim, instance profile attachment), `apprunner.tf`, `lambda.tf`, `variables.tf`, `demo_ec2_setup.sh`, `poc_ec2_setup.sh`, `README.md`.

---

## 7. Tasks — worktree A (copilot-mro, `obs-infra`)

### A1 — Pin every image; delete the `debug` exporter; collector telemetry at `info` (master 0.1; spec §8 G17a/G17c)

**Files.** Create `deployment/otel/VERSIONS.md`, `tests/integration/otel/test_compose_image_pins.py`. Modify the four compose files and `deployment/observability-local/otel-collector-config.yaml`.
**Interfaces.** Produces: the pinned-version table of §4, consumed by A6's CI job, A8's smoke and `iac/demo_ec2_setup.sh` (B3). Consumes: nothing.
**Steps.**
- [x] Write `test_compose_image_pins.py`: it resolves the four compose paths through `repo_root(__file__, "deployment", …)` from `tests/_root.py` (never `parents[N]`), parses each with `yaml.safe_load`, and asserts (a) every `services.*.image` value carries an explicit tag or digest, (b) no value ends in `:latest` unless it also carries an `@sha256:` digest, (c) the six observability images equal the exact pins of §4, (d) the pins in the compose files equal the pins listed in `VERSIONS.md` (parsed from its table) so the two cannot drift.
- [x] Run it — red (every image is `:latest`; `VERSIONS.md` absent).
- [x] Write `VERSIONS.md`: the §4 table (image, pin, release date, source URL, date verified), the monthly bump policy, and the Weaviate exception with its reason.
- [x] Apply the pins in all four compose files. `deployment/demo/docker-compose.yml` and `deployment/poc/docker-compose.yml` additionally set `container_name`-consistent pins for `weaviate` from the OWNER STEP value.
- [x] Swap `otel/opentelemetry-collector` → `otel/opentelemetry-collector-contrib:0.160.0` everywhere (the base image lacks `redaction`, `sigv4auth`, `delta_to_cumulative`, `azure_auth`).
- [x] In `otel-collector-config.yaml`: delete the `debug` exporter definition and its four pipeline references; set `service.telemetry.logs.level: info`; delete the `pprof` and `zpages` extensions and their `service.extensions` entries (G17a, G31 — `1777` is a remote heap/CPU-profile door).
- [x] Run the standing validate command against the *current* single config (env `OTEL_CORS_ORIGIN_1`/`_2` supplied inline) — exit 0.
- [x] Run the pytest command — green.
- [x] **Logging coverage:** collector self-telemetry stays at `info` (not `debug`, which logged every batch); no config value is echoed by any script touched here.
- [x] Commit `deployment/otel/VERSIONS.md` and `tests/integration/otel/test_compose_image_pins.py` by pathspec. Report the five modified pre-existing files.
**Acceptance.** No floating tag remains in any of the four compose files; `VERSIONS.md` and the compose files agree; the collector config validates with no `debug` exporter and `info` telemetry.

### A2 — Loki auth + retention, Tempo retention, Prometheus retention (master 0.2; spec §5, ruling 13, G31)

**Files.** Create `tests/integration/otel/test_retention_config.py`. Modify `loki-config.yaml`, `tempo.yaml`, the four compose files.
**Interfaces.** Produces the env contract `LOKI_RETENTION_PERIOD` (default `336h` = 14 d), `LOKI_TENANT_ID` (default `flynapse`), `TEMPO_BLOCK_RETENTION` (default `72h` = 3 d), `PROM_RETENTION_TIME` (default `30d`) — consumed by A5's overlay headers, A8's smoke, `poc_ec2_setup.sh` (B-side) and `deployment/otel/README.md`.
**Steps.**
- [x] Write `test_retention_config.py`: asserts `loki-config.yaml` has `auth_enabled: true`; `limits_config.retention_period` reads `${LOKI_RETENTION_PERIOD:-336h}`; a `compactor` block with `working_directory`, `retention_enabled: true`, `delete_request_store: filesystem`, `retention_delete_delay`, `compaction_interval`; `schema_config` index period stays `24h` (Loki refuses retention otherwise). Asserts `tempo.yaml` `compactor.compaction.block_retention` reads `${TEMPO_BLOCK_RETENTION:-72h}`. Asserts every compose service mounting either file passes `-config.expand-env=true` in its `command` (without it the `${…}` is taken literally and retention silently misconfigures). Asserts every Prometheus `command` carries `--storage.tsdb.retention.time=${PROM_RETENTION_TIME:-30d}` and `--web.enable-remote-write-receiver`.
- [x] Run — red.
- [x] Edit `loki-config.yaml` and `tempo.yaml`; add `-config.expand-env=true` to the Loki and Tempo commands in all four compose files; parameterise the Prometheus retention flag.
- [x] Run — green.
- [x] **Logging coverage:** none of these components' own logs change level; confirm Loki still logs rejected pushes (a 401 from a missing `X-Scope-OrgID` must be visible, not silent) by leaving `server.log_level` at its default `info`.
- [x] Commit the test by pathspec; report the six modified files.
**Acceptance.** Retention is env-driven with the ruled defaults on all four stacks; `auth_enabled: true` means every write and read must carry `X-Scope-OrgID`, which A5 (exporter header), A8 (query header) and the Grafana datasource (A3) all supply.

### A3 — Grafana secret, loopback binds, Jaeger purge (master 0.3; spec §8 G17b/G31, §9.1)

**Files.** Create `tests/integration/otel/test_compose_port_bindings.py`. Modify the four compose files, `grafana/provisioning/datasources/datasources.yml`, `observability-local/README.md`.
**Interfaces.** Produces `GRAFANA_ADMIN_PASSWORD` (required, no default) and `LOKI_TENANT_ID` consumption in the Grafana Loki datasource.
**Steps.**
- [x] Write `test_compose_port_bindings.py`: for each of the four compose files, every entry in `services.*.ports` must either be bound to `127.0.0.1` or appear in an explicit allow-list of `{"4318"}` (POC and demo only — the app tier and, until Stream F's cut-over, the POC browser reach the collector there). Asserts `9090`, `3100`, `3200`, `9464`, `13133`, `1777`, `14250`, `14268`, `4317`, `55679` appear nowhere as an all-interfaces publish. Asserts no `GF_SECURITY_ADMIN_PASSWORD=admin` and that the value is `${GRAFANA_ADMIN_PASSWORD:?…}` so compose fails fast when unset. Asserts `observability-local/README.md` contains no case-insensitive `jaeger` and no `16686`.
- [x] Run — red (Grafana is `admin/admin` in all four; seven ports are world-published; the README names Jaeger at lines 9, 23, 44, 84, 86, 142, 176).
- [x] Apply: Grafana password from `${GRAFANA_ADMIN_PASSWORD:?set GRAFANA_ADMIN_PASSWORD}`; drop the `9464`, `13133`, `1777`, `14250`, `14268`, `4317` publishes entirely (nothing outside the compose network consumes them once A7 lands — `9464` is replaced by the collector's own `8888` telemetry endpoint, unpublished); loopback-bind `9090`, `3100`, `3200`.
- [x] Rewrite the README: delete the Jaeger service from the component list, the architecture diagram, the URL table and the "view traces in Jaeger or Tempo" step; replace the `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` example with the `http/protobuf` 4318 form; state the admin-password requirement.
- [x] Add `httpHeaderName1: X-Scope-OrgID` / `secureJsonData.httpHeaderValue1: ${LOKI_TENANT_ID}` to the Grafana Loki datasource (without it every Loki panel 401s once A2 lands) and note that the Postgres datasource for exact spend arrives with Stream P task 5.2, not here.
- [x] Run — green.
- [x] **Logging coverage:** the compose `:?` form makes a missing secret a loud startup failure rather than a silent `admin/admin`.
- [x] Commit the test by pathspec; report the six modified files.
**Acceptance.** No admin plane is published off-host in any stack; Grafana refuses to start without a supplied password; the README describes only services that exist.

### A4 — `deployment/otel/base.yaml` (master 2.1, front half; spec §3.1, §3.3, §5)

**Files.** Create `deployment/otel/base.yaml`, `tests/integration/otel/test_collector_base_config.py`.
**Interfaces produced (the stream's public contract).** OTLP/HTTP `:4318` for services; OTLP/HTTP `:4319` for browser traffic forwarded by the api gateway (consumed by Stream P task 5.5 — `core` posts the opaque body to `/v1/logs` and `/v1/traces` on 4319 with `X-Tenant-Id`, `X-User-Id`, `X-Session-Id`; the core setting is `OTEL_BROWSER_FORWARD_ENDPOINT`, e.g. `http://otel-collector:4319`, distinct from the app's own `OTEL_EXPORTER_OTLP_ENDPOINT` on 4318, and every compose file that runs `core` sets it); span attribute `flynapse.content_copy="true"` marks the sampled content copy (consumed by Stream L task 3.6); health check on `:13133`; collector self-telemetry on `:8888` inside the compose network.
**Steps.**
- [x] Write `test_collector_base_config.py` asserting, over `yaml.safe_load` of `base.yaml`: two OTLP receivers (`otlp` on `0.0.0.0:4318`, `otlp/browser` on `0.0.0.0:4319`), both with `include_metadata: true`, neither declaring a `grpc` protocol, neither declaring `cors` (browsers never reach the collector directly — spec §3.4); the processor map contains exactly `memory_limiter`, `resourcedetection`, `attributes/browser_identity`, `attributes/strip_content`, `attributes/metric_cardinality`, `transform/genai_aliases`, `redaction`, `filter/drop_health`, `filter/content_only`, `filter/drop_content_copies`, `batch`; `attributes/browser_identity` reads `from_context: metadata.x-tenant-id` / `metadata.x-user-id` / `metadata.x-session-id` into `tenant.id` / `enduser.id` / `session.id` with `action: upsert` (a client-authored `tenant.id` inside the forwarded body never wins over the gateway's header); `attributes/strip_content` deletes `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.prompt`, `gen_ai.completion`; `attributes/metric_cardinality` deletes `session.id`, `user.id`, `user.email`, `enduser.id`, `organization.id`, `terminal.type`, `app.entrypoint`, `url.path`, `http.target`; `redaction` sets `allow_all_keys: true`, `summary: silent`, non-empty `blocked_key_patterns` and `blocked_values`; the file declares **no** `service.pipelines` and **no** `exporters`; `service.telemetry.logs.level` is `info`; `extensions` contains `health_check` and neither `pprof` nor `zpages`.
- [x] Run — red.
- [x] Author `base.yaml`. Receivers as above. `memory_limiter` with `check_interval: 1s`, `limit_percentage: 80`, `spike_limit_percentage: 20` — first in every pipeline. `resourcedetection` with `detectors: [env, system, ec2]`, `timeout: 2s`, `override: false`, `ec2.tags: []` (the short timeout is what keeps a laptop from stalling on IMDS). `transform/genai_aliases` in OTTL: on metrics whose name matches `^claude_code\.`, copy `tenant.id`, `agent.department` and `deployment.environment.name` from `resource.attributes` onto the datapoint (the CLI is configured with `OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES=false`, so the resource still carries them but they are not labels — this adds back exactly the three we want); alias `claude_code.cost.usage` and `claude_code.token.usage` datapoint attribute `model` to `gen_ai.request.model`, set `gen_ai.provider.name`, and normalise the `type` values `cacheRead`/`cacheCreation` into `gen_ai.token.type` values `cache_read`/`cache_creation`; on log records whose `event.name` is `claude_code.api_request`, alias `model`, `cost_usd`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` to `gen_ai.request.model`, `gen_ai.usage.cost`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read_input_tokens`, `gen_ai.usage.cache_creation_input_tokens` (names taken from research 06 §1). `filter/drop_health` drops spans whose `http.route` or `url.path` matches `^/health(/.*)?$` or `^/metrics$`. `filter/content_only` keeps only spans carrying `flynapse.content_copy == "true"`; `filter/drop_content_copies` drops exactly those. `batch` with `timeout: 5s`, `send_batch_size: 1024`, `send_batch_max_size: 2048`. `service.telemetry.resource` sets `service.name: otel-collector`; `service.telemetry.metrics.readers` exposes a Prometheus pull reader on `${env:OTELCOL_SELF_METRICS_HOST:-0.0.0.0}:8888` (unpublished in every compose file, so it is reachable by Prometheus and by nothing outside).
- [x] Run — green. (`base.yaml` alone cannot be `validate`d: a pipeline-less config has nothing to check. It is validated in A5 as part of each pair.)
- [x] **Logging coverage:** `service.telemetry.logs.level: info` keeps exporter send failures and queue drops visible without per-batch spam; `redaction` runs with `summary: silent` so it never adds diagnostic attributes naming what it masked.
- [x] Commit both files by pathspec.
**Acceptance.** The base carries the whole invariant front half of the pipeline (§3.1) and nothing backend-specific; every identity, redaction, cardinality and content rule the spec names has a named processor.

### A5 — `deployment/otel/backend-oss.yaml` (master 2.2; spec §5, ruling 2)

**Files.** Create `deployment/otel/backend-oss.yaml`, `tests/integration/otel/test_collector_profiles.py`.
**Interfaces.** Consumes A4's processors and A2's env contract. Produces the oss env set: `TEMPO_OTLP_ENDPOINT`, `PROM_REMOTE_WRITE_URL`, `LOKI_OTLP_ENDPOINT`, `LOKI_TENANT_ID`.
**Steps.**
- [x] Write `test_collector_profiles.py` as a table-driven test over every `deployment/otel/backend-*.yaml` that exists: each overlay declares `exporters`, declares a complete `service.pipelines` containing exactly `traces`, `metrics`, `logs`, `traces/browser`, `logs/browser`; every pipeline lists `memory_limiter` first and `batch` last; `attributes/strip_content` appears on `traces`, `logs`, `traces/browser` and `logs/browser`; `filter/drop_content_copies` appears on `traces`; `attributes/browser_identity` appears on the two browser pipelines and on no other; `attributes/metric_cardinality` appears on `metrics`; no overlay declares a bare empty `processors:` key (a null map wipes the base — research 04 §4.3); no overlay declares a `debug` exporter; `service.extensions` names every extension the overlay defines plus `health_check`.
- [x] Add the oss-specific assertions: `delta_to_cumulative` is defined in this overlay (not in base — it is oss-only) and appears in the `metrics` pipeline immediately before `batch`; the logs exporter carries the header `X-Scope-OrgID`.
- [x] Run — red.
- [x] Author `backend-oss.yaml`: exporters `otlphttp/tempo` (`traces_endpoint: ${env:TEMPO_OTLP_ENDPOINT:-http://tempo:4318/v1/traces}`), `prometheusremotewrite/prom` (`${env:PROM_REMOTE_WRITE_URL:-http://prometheus:9090/api/v1/write}`, `target_info` enabled, `resource_to_telemetry_conversion` disabled so only `job`/`instance` come from the resource), `otlphttp/loki` (`logs_endpoint: ${env:LOKI_OTLP_ENDPOINT:-http://loki:3100/otlp/v1/logs}`, header `X-Scope-OrgID: ${env:LOKI_TENANT_ID:-flynapse}`); processor `delta_to_cumulative` with `max_stale: 5m`, `max_streams: 100000`; `service.extensions: [health_check]`; all five pipelines restated in full. Consult the pinned version's exporter README (the `prometheusremotewriteexporter` README at tag `v0.160.0`) for the exact endpoint key before assuming it is top-level `endpoint`; `validate` is the arbiter.
- [x] Run the standing validate command for `oss` — exit 0. Run pytest — green.
- [x] **Logging coverage:** exporter `retry_on_failure` and `sending_queue` left at defaults so drops are logged; no exporter is configured to swallow errors.
- [x] Commit both files by pathspec.
**Acceptance.** `base.yaml` + `backend-oss.yaml` validates on the pinned image; the overlay restates every pipeline so the effective processor order is readable in one file.

### A6 — `validate.sh`, env examples, CI job (master 2.1, CI half)

**Files.** Create `deployment/otel/validate.sh`, `deployment/otel/env/{oss,aws,azure}.env.example`, `.github/workflows/otelcol-validate.yml`.
**Interfaces.** Consumed by CI and by every later config task as its test command.
**Steps.**
- [x] Write `validate.sh` (`set -euo pipefail`): takes an optional profile argument, defaults to all overlays present; for each, runs the pinned-image `validate` with `base.yaml` + the overlay (+ `content-phoenix.yaml` when the profile's env example sets `PHOENIX_ENDPOINT`); reads the image pin from `VERSIONS.md` so the script and the pins cannot drift; echoes one `validating <profile>` line before and one `ok <profile>` / `FAILED <profile>` line after; exits non-zero on the first failure.
- [x] Write the three env examples: every `${env:VAR}` occurring in the matching overlay, with a comment and the value used for validation (dummy endpoints/regions are fine — `validate` resolves substitutions, so an unset variable is a hard error and that is the point).
- [x] Verify by mutation: temporarily misspell a processor id in `backend-oss.yaml`, run `validate.sh oss`, confirm non-zero and the failing profile named; revert.
- [x] Write `.github/workflows/otelcol-validate.yml`: `on: pull_request` and `push` filtered to `deployment/otel/**` and `deployment/**/docker-compose*.yml`, plus `workflow_dispatch`; a single ubuntu-latest job, `actions/checkout@v4`, then `bash deployment/otel/validate.sh`. No AWS credentials and no secrets — this job must be runnable on a fork PR. (The repo's two existing workflows are both gated on `[test]`/`[publish]` commit markers and need secrets; this one is deliberately ungated because it is fast and hermetic.)
- [x] **Logging coverage:** every failure path in the script prints the profile and the collector's stderr; no `|| true`.
- [x] Commit all five files by pathspec.
**Acceptance.** `bash deployment/otel/validate.sh` exits 0 locally and in CI for every overlay that exists at that commit, and non-zero for a broken one.

### A7 — Compose files mount base + overlay; Prometheus scrape rewrite; delete the legacy config (master 2.2, compose half)

**Files.** Modify the four compose files and `prometheus.yml`. Delete `deployment/observability-local/otel-collector-config.yaml`.
**Interfaces.** Consumes A4–A6. Produces the mounted layout `/etc/otel/base.yaml` + `/etc/otel/backend-<profile>.yaml` used by B3's demo-box script.
**Steps.**
- [x] Extend `test_collector_profiles.py` with a compose-side assertion: every `otel-collector` service mounts `deployment/otel` at `/etc/otel` read-only and its `command` is exactly the two (or three, with Phoenix) `--config=/etc/otel/…` flags in base-then-overlay order; no compose file references `otel-collector-config.yaml`; no compose file publishes `9464`.
- [x] Run — red.
- [x] Edit the four compose files accordingly (oss overlay in `observability-local`, `deployment/docker-compose.yml` and `poc`; the demo file's collector is left mounting the oss overlay until B3 switches the box to `aws`, and A13 removes the four OSS containers from it).
- [x] Rewrite `prometheus.yml`: keep the `prometheus` self-scrape; replace the `otel-collector:9464` job with `otel-collector:8888` (the collector's own telemetry — see correction 7); keep `rule_files` present but empty with a comment pointing at Phase 6 task 6.3.
- [x] Delete `otel-collector-config.yaml`.
- [x] Run `validate.sh` and pytest — green. Bring up the local stack once by hand (`docker compose -f deployment/docker-compose.yml up -d otel-collector prometheus loki tempo`) and confirm all four containers reach a running state, then tear it down.
- [x] **Logging coverage:** confirm the collector's startup log names both config files (it lists resolved config sources at `info`), so a missed mount is visible in `docker logs`.
- [x] Commit nothing new; report the five modified files and the deletion (a deletion of a pre-existing file is reported, not committed).
**Acceptance.** Every stack runs the same `base.yaml` and differs only by overlay; the legacy single config is gone.

### A8 — `oss` compose smoke (master 2.3; spec §13)

**Files.** Create `deployment/otel/smoke/docker-compose.smoke.yml`, `tests/integration/otel/conftest.py`, `tests/integration/otel/test_oss_profile_smoke.py`. Modify `pyproject.toml` (marker).
**Interfaces.** Consumes A5/A7. Produces the reusable stack fixture that A9 extends.
**Steps.**
- [x] Register the marker in `pyproject.toml`: `compose_stack: starts a real docker compose stack (deselect with -m 'not compose_stack'; also requires OTEL_COMPOSE_SMOKE=1 and a reachable docker daemon)`.
- [x] Write `docker-compose.smoke.yml` as an override composed on top of `deployment/docker-compose.yml`: project-scoped host ports on loopback only (`127.0.0.1:14318`, `14319`, `13100`, `19090`, `13200`) so a running dev stack is never clobbered, and `tmpfs` mounts for the Loki, Tempo and Prometheus data paths (no host directories, no permission dance, nothing to clean up).
- [x] Write `conftest.py`: a session fixture that skips the module unless `OTEL_COMPOSE_SMOKE=1` and `docker info` succeeds; brings up only `otel-collector loki prometheus tempo` under project name `flynapse-otel-smoke` with both compose files; waits for the collector's `13133` health check and each backend's readiness with a bounded poll (deadline 120 s, 1 s interval) that raises with the collected `docker compose logs` on timeout; tears the project down with `down -v` in a finally.
- [x] Write `test_oss_profile_smoke.py`, marked `compose_stack`, resolving paths through `tests/_root.py`. It posts OTLP **JSON** (`content-type: application/json`) with `urllib.request` — no protobuf dependency, and the OTLP/HTTP receiver accepts JSON — to `/v1/traces`, `/v1/metrics`, `/v1/logs` on `127.0.0.1:14318`: one span with a known trace id, `service.namespace=flynapse`, `service.name=smoke-service`; one **delta** monotonic sum; one log record. Then, with the same bounded-poll helper: Tempo `GET /api/traces/<trace_id>` returns the span; Prometheus `GET /api/v1/query` finds the counter series and its `job` label equals `flynapse/smoke-service` and `instance` equals the sent `service.instance.id` (this single assertion proves both the `job` convention of G21 and that `delta_to_cumulative` ran — a delta sum reaching `prometheusremotewrite` unconverted is dropped outright); Loki `GET /loki/api/v1/query_range` with header `X-Scope-OrgID: flynapse` returns the log line, and the same query **without** the header returns 401 (proving `auth_enabled: true`); Loki `GET /config` reports `retention_enabled: true` and the configured `retention_period` (the A2 substitution for the un-assertable deletion test).
- [x] Add two negative assertions: a span with `http.route=/health/live` posted to the same endpoint never appears in Tempo (`filter/drop_health`); a span carrying `gen_ai.input.messages` appears in Tempo **without** that attribute (`attributes/strip_content`).
- [x] Run the pytest command with `OTEL_COMPOSE_SMOKE=1` — green. Run the suite without the variable and confirm the module skips.
- [x] **Logging coverage:** the fixture prints `docker compose logs` for every container on any failure or timeout; no bare `except`.
- [x] Commit the three new files plus `pyproject.toml` by pathspec.
**Acceptance.** One command proves span, metric and log land in the right store with the right labels, that health spans and content attributes are stripped, and that Loki refuses an untenanted read.

### A9 — Phoenix in the `oss` profile and the `content` pipeline (master 7.1; spec §6.5, ruling 11)

**Files.** Create `deployment/otel/content-phoenix.yaml`. Modify `deployment/docker-compose.yml`, `deployment/poc/docker-compose.yml`, `deployment/otel/smoke/docker-compose.smoke.yml`, `tests/integration/otel/test_oss_profile_smoke.py`, `tests/integration/otel/test_collector_profiles.py`.
**Interfaces.** Consumes the `flynapse.content_copy` marker from A4. Produces: Phoenix at `${PHOENIX_ENDPOINT:-http://phoenix:6006}`; project routing by resource attribute `openinference.project.name` (verified: the OTLP resource attribute is the canonical routing key, with the `x-project-name` HTTP header taking precedence).
**Steps.**
- [x] Extend `test_collector_profiles.py`: `content-phoenix.yaml` defines exactly one exporter (`otlphttp/phoenix`, `traces_endpoint: ${env:PHOENIX_ENDPOINT}/v1/traces`, header `authorization: Bearer ${env:PHOENIX_API_KEY}`), one processor (`transform/phoenix_project`) and exactly one pipeline (`traces/content`) whose processor list is `[memory_limiter, filter/content_only, transform/phoenix_project, redaction, batch]` — note `attributes/strip_content` is deliberately absent here and present nowhere else that matters; and that the shipped compose files set `PHOENIX_ENABLE_AUTH=true` with `PHOENIX_SECRET` from env.
- [x] Run — red.
- [x] Author `content-phoenix.yaml`. `transform/phoenix_project` sets the resource attribute `openinference.project.name` to `tenant-<tenant.id>` when `tenant.id` is present and to `internal` otherwise (one Phoenix project per tenant plus internal, per §6.5).
- [x] Add the `phoenix` service to `deployment/docker-compose.yml` and `deployment/poc/docker-compose.yml`: image `arizephoenix/phoenix:version-20.8.0`; `PHOENIX_SQL_DATABASE_URL` pointing at the stack's Postgres; `PHOENIX_ENABLE_AUTH=true`; `PHOENIX_SECRET=${PHOENIX_SECRET:?}`; `PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD=${PHOENIX_ADMIN_PASSWORD:?}`; `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=${PHOENIX_RETENTION_DAYS:-30}`; UI port `6006` bound to `127.0.0.1` only. Append `--config=/etc/otel/content-phoenix.yaml` to those collectors' commands.
- [x] Extend the smoke: the smoke override runs Phoenix with `PHOENIX_ENABLE_AUTH=false` on SQLite over a tmpfs `PHOENIX_WORKING_DIR` (creating a system API key needs an admin login, which is not a smoke's job — the auth-on posture is asserted structurally instead, above). The test posts one `invoke_agent` span carrying `gen_ai.*` attributes and `flynapse.content_copy="true"`, then polls `GET /v1/projects/internal/spans` until the span id appears, and separately asserts the same span does **not** appear in Tempo's `traces` pipeline (`filter/drop_content_copies`).
- [x] Run both tests — green.
- [x] **Logging coverage:** the Phoenix exporter keeps default retry/queue logging; the smoke's failure path dumps Phoenix's container log too.
- [x] Commit `content-phoenix.yaml` and the test edits by pathspec; report the three modified compose files.
**Acceptance.** A content-marked span reaches Phoenix's `internal` project and nothing else; the shipped profile runs Phoenix with auth on, a 30-day retention default and a loopback-only UI.

### A10 — `deployment/otel/backend-aws.yaml` (master 2.4; spec §5, research 04 §1.1/§1.6)

**Files.** Create `deployment/otel/backend-aws.yaml`. Modify `tests/integration/otel/test_collector_profiles.py`, `deployment/otel/env/aws.env.example`.
**Interfaces.** Consumes B4's log-group names and B3's instance role. Produces the aws env set: `AWS_REGION`, `CW_LOG_GROUP`, `CW_LOG_STREAM`.
**Steps.**
- [x] Extend the profile test with aws assertions: three `otlphttp` exporters using the **signal-specific** endpoint keys `logs_endpoint`, `traces_endpoint`, `metrics_endpoint` (the paths differ per signal, so a shared `endpoint` is wrong); values `https://logs.${env:AWS_REGION}.amazonaws.com/v1/logs`, `https://xray.${env:AWS_REGION}.amazonaws.com/v1/traces`, `https://monitoring.${env:AWS_REGION}.amazonaws.com/v1/metrics`; the logs exporter carries `x-aws-log-group: ${env:CW_LOG_GROUP}` and `x-aws-log-stream: ${env:CW_LOG_STREAM:-default}` (the log group is chosen by header, never by resource attribute); `compression: gzip` on all three; three `sigv4auth/*` extensions with `service` values `logs`, `xray`, `monitoring` and each exporter's `auth.authenticator` naming the matching one; **no** `delta_to_cumulative` (CloudWatch accepts delta); no Phoenix exporter in this file.
- [x] Run — red.
- [x] Author `backend-aws.yaml` with all five pipelines restated.
- [x] Run `validate.sh aws` — exit 0. Run pytest — green.
- [x] **Logging coverage:** sigv4 signing failures surface as exporter errors at `info`; do not lower the telemetry level to hide them.
- [x] Commit the overlay and test edits by pathspec.
**Acceptance.** The `aws` overlay validates on the pinned image with only env-supplied region and log-group values, and reaches CloudWatch through the instance role alone — no credentials in the config.

### A11 — `deployment/otel/backend-azure.yaml` (master 2.8)

**Files.** Create `deployment/otel/backend-azure.yaml`; modify the profile test and `azure.env.example`.
**Steps.**
- [x] Extend the profile test: one `otlphttp/azuremonitor` exporter with the three `*_endpoint` keys from `${env:AZURE_MONITOR_*}`, the `azure_auth` extension (type `azure_auth`; `azureauth` is the deprecated alias), and `cumulativetodelta` in the `metrics` pipeline before `batch` — Azure Monitor wants delta.
- [x] Run — red. Author. Run `validate.sh azure` and pytest — green.
- [x] **Logging coverage:** same as A10.
- [x] Commit by pathspec.
**Acceptance.** Authored and validated; **not deployed** and no IaC (spec §5) — the live-send probe stays on the §12 list until a client needs Azure.

### A12 — `deployment/otel/README.md` and the env-documentation guard (master 2.1, docs)

**Files.** Create `deployment/otel/README.md`, `tests/integration/otel/test_profile_env_documented.py`.
**Steps.**
- [x] Write `test_profile_env_documented.py`: scan every `${env:VAR}` (and `${env:VAR:-default}`) in `base.yaml`, the three overlays and `content-phoenix.yaml`; assert each VAR appears in the matching `env/*.env.example` **and** in the README's variable table; assert no example file names a variable no config reads (dead env rots).
- [x] Run — red. Write the README: how to switch profile (mount `deployment/otel`, pass base + one overlay + optionally the Phoenix fragment); the env table per profile; the port contract (4318 services, 4319 browser-forward, 8888 self-telemetry, 13133 health); the `flynapse.content_copy` marker contract for Stream L; the `X-Tenant-Id`/`X-User-Id`/`X-Session-Id` header contract for Stream U's ingest forward; the retention knobs; the "why no CORS and no gRPC" note; a pointer to `VERSIONS.md` and the bump policy.
- [x] Run — green. Commit both by pathspec.
**Acceptance.** Every knob any profile reads is documented once and guarded by a test.

### A13 — Demo compose keeps only the collector (master 2.5, compose side; ruling 14)

**Files.** Modify `deployment/demo/docker-compose.yml`.
**Depends on:** B3 (the box's setup script must supply the aws env file first, or the collector starts and fails to sign).
**Steps.**
- [x] Extend `test_compose_port_bindings.py`: the demo compose defines no `prometheus`, `loki`, `grafana` or `tempo` service, and its `otel-collector` mounts `base.yaml` + `backend-aws.yaml`.
- [x] Run — red. Remove the four services and their volumes/ports; point the collector at the aws overlay with `env_file: /opt/otel/collector.env`; leave `weaviate`, `weaviate-ui` untouched.
- [x] Run — green.
- [x] **Logging coverage:** note in the file's header comment that `/opt/persistent-data/observability-data/*` becomes orphaned data the owner may delete after verifying CloudWatch receipt (B10's probe) — an OWNER STEP, not a scripted deletion.
- [x] Commit nothing new; report the modified file.
**Acceptance.** The demo box's compose stands up the collector and Weaviate only; the four OSS containers are gone (§5, ruling 14).

### A14 — Retire the legacy `OTEL_ENDPOINT` compose env — **GATED on Stream U task 1a.7**

**Files.** Modify `deployment/poc/docker-compose.yml` (the `api` service).
**Rationale for the gate.** `poc/docker-compose.yml:178` sets `OTEL_ENDPOINT=http://otel-collector:4317`, which today's `utils.config` reads. Until Stream U's `bootstrap()` lands, removing it turns telemetry off on the POC. So A7 **adds** `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_SERVICE_NAME=api`, `OTEL_RESOURCE_ATTRIBUTES=service.namespace=flynapse,deployment.environment.name=poc` beside the legacy line with a comment naming this task, and A14 deletes the legacy line once `obs-utils` merges.
**Steps.**
- [ ] Confirm `obs-utils` has merged and `utils/utils/config.py` no longer reads `OTEL_ENDPOINT`.
- [ ] Delete the line; add an assertion to `test_collector_profiles.py` that no compose file sets `OTEL_ENDPOINT` or `OTEL_ENABLED`.
- [ ] Run — green. Report the modified file.
**Note for the report (out of this worktree's scope):** `copilot-mro/.env.sample:11-12` still carries `OTEL_ENDPOINT` and `OTEL_SERVICE_NAME=mro-copilot-rag`; `api/Dockerfile:88` hardcodes `OTEL_SERVICE_NAME="copilots"` (the source of G12). Both belong to Stream U — flag them, do not edit them.

---

## 8. Tasks — worktree B (iac, `obs-iac`)

### B1 — Probes (master 2.7; spec §12). Outcomes recorded in §11 of this file.

Each probe is a task with a recorded outcome; none of them changes state.
- [ ] **B1a — CloudWatch OTel-metrics OTLP GA and temporality in `ap-south-1`.** Re-verify the endpoint doc and confirm the region list; record whether cumulative histograms are accepted as sent. Fallback if it is not GA in `ap-south-1`: `prometheusremotewrite` to Amazon Managed Prometheus, which changes only `backend-aws.yaml`'s metrics exporter. **OWNER STEP** for the live confirmation: one signed POST of a cumulative histogram after B3's apply.
- [ ] **B1b — CloudWatch Logs OTLP stored field paths.** After the first real send (B10's probe script), record the exact JSON field paths for resource attributes (expected `resource.attributes.service.name`) — Phase 6's Logs Insights queries are written against them. **OWNER STEP** (needs a live account).
- [x] **B1c — PromQL alarms in the pinned provider.** Run `terraform init -backend=false` then `terraform providers schema -json` and grep the `aws_cloudwatch_metric_alarm` schema for PromQL/expression support. The root pins `aws ~> 5.0` (`main.tf:4-7`) and the lock file is gitignored, so the resolved version must be recorded verbatim. If absent, record the two fallbacks: raise the constraint, or add the `awscc` provider (which also supplies `awscc_xray_transaction_search_config`, see B5). Decide **before** Phase 6 task 6.4 — do not raise the provider constraint in this stream; that is an owner call with blast radius across the de-synced root.
- [ ] **B1d — Application Signals from vanilla SDK spans.** **OWNER STEP** after B3+B5: does the service map populate from our non-ADOT spans? If not, Phase 6 ships RED alarms only, no SLO objects.
- [x] Record all four outcomes in §11 with the date and the command or URL used.

### B2 — Trim the `weaviate_observability` security group (master 0.4; spec §8 G31)

**Files.** Modify `ec2.tf` (lines 96–115).
**Steps.**
- [x] Reduce the first (allowed-IP) `for_each` list to `[22]`; reduce the second (App Runner + Lambda SG) list to `[8080, 50051, 4318]`. Dropped: `3000, 9090, 3100, 3200, 9464, 13133, 1777, 14250, 14268, 8000, 9443, 7777`.
- [x] Write the review checklist into the commit-adjacent report, one line per dropped port with the evidence that no app path uses it: `3000/9090/3100/3200` were Grafana/Prometheus/Loki/Tempo UIs — A13 removes those containers and `core` never learned `LOKI_BASE_URL` (research 02 §4.2 finding 1, spec §12 probe 1); `9464` was the collector's Prometheus exporter, replaced by the unpublished `8888` (A7); `13133`/`1777` were health/pprof — health stays inside the host, pprof is deleted (A1); `14250`/`14268` were Tempo's alternative OTLP ports, never used by any client; `8000`/`9443` were Portainer; `7777` was weaviate-ui, which the demo compose already binds to loopback. `4317` was never in the list to begin with for the allowed-IP block but is in the App Runner block — it goes too, because every client moves to 4318 `http/protobuf` (spec §3.1).
- [x] `terraform fmt -check` and `terraform init -backend=false && terraform validate` — clean.
- [x] **OWNER STEP:** `terraform plan` and review that the diff is SG-rule removals only. Note the de-synced-root caveat (§1.6).
- [x] **Logging coverage:** n/a for HCL; the checklist is the artefact.
- [x] Report the modified file (uncommitted).
**Acceptance.** The box admits SSH from the allowed IP and, from the app SGs only, Weaviate's two ports and OTLP 4318.

### B3 — Instance profile, CloudWatch IAM, and the demo box running the `aws` overlay (master 2.5; ruling 14)

**Files.** Create `otel_gateway.tf` (role/profile/policy part). Modify `ec2.tf` (attach `iam_instance_profile`), `demo_ec2_setup.sh`.
**Steps.**
- [x] `otel_gateway.tf`: `aws_iam_role.otel_collector` with an EC2 trust policy; attach the AWS-managed `CloudWatchAgentServerPolicy` (this is exactly what the CloudWatch OTLP setup doc prescribes for an EC2 host, and it covers all three endpoints); add one small inline policy granting `logs:PutLogEvents` and `logs:CreateLogStream` scoped to the `arn:aws:logs:<region>:<account>:log-group:/flynapse/*` groups B4 creates (least privilege beside the managed policy); `aws_iam_instance_profile.otel_collector`. Attach the profile in `ec2.tf` — the instance has none today.
- [x] `demo_ec2_setup.sh`: after the repo clone, write `/opt/otel/collector.env` (`AWS_REGION`, `CW_LOG_GROUP`, `CW_LOG_STREAM`, `PHOENIX_ENDPOINT` only when a value is supplied), then bring up `deployment/demo/docker-compose.yml`. Build the collector's `--config` argument list in shell so the Phoenix fragment is appended only when `PHOENIX_ENDPOINT` is non-empty — a collector config cannot itself be conditional, and this is the seam where a conditional belongs. Remove the four `mkdir -p $PERSIST_DIR/observability-data/*` lines and the Portainer `docker run` line's floating tag (pin `portainer/portainer-ce:2.45.0`), or drop Portainer entirely if the owner agrees (record as an open question, not a unilateral deletion). Add `set -euo pipefail` and one echo per stage.
- [x] `terraform fmt -check`, `init -backend=false`, `validate` — clean. `bash -n demo_ec2_setup.sh` — clean.
- [x] **OWNER STEPS:** (1) `terraform plan`/`apply`; (2) the box only picks up compose changes when it pulls `main` (`demo/restart-services.sh` does `git pull origin main`), so the `obs-infra` branch must be merged to `main` before `restart-services.sh` will run the new stack; (3) confirm the collector container starts and its log shows both config sources.
- [x] **Logging coverage:** the script fails loudly on a missing env value rather than starting a collector that cannot sign; no secret is echoed.
- [x] Commit `otel_gateway.tf`; report `ec2.tf` and `demo_ec2_setup.sh`.
**Acceptance.** The demo EC2 has an instance profile with CloudWatch OTLP permissions and runs the collector under the `aws` overlay.

### B4 — Log groups with retention (master 2.5; ruling 13)

**Files.** Create `cloudwatch.tf`. Modify `variables.tf`.
**Steps.**
- [x] Add `variable "log_retention_days"` (number, default 30 — ruling 13's `aws` logs figure) and `variable "waf_web_acl_arn"` (string, default "") used by B8.
- [x] `cloudwatch.tf`: `aws_cloudwatch_log_group` for `/flynapse/${var.environment}/otel` (the collector's own OTLP target group named by `CW_LOG_GROUP`), plus explicit groups for the App Runner service and application logs and for both Lambda functions (`/aws/lambda/${var.cognito_signup_lambda_function_name}` and `/aws/lambda/s3-pdf-processor-${var.environment}`), each with `retention_in_days = var.log_retention_days`. These groups auto-create today with never-expiring retention (research 02 §3.2), so declaring them is the only way retention is ever set.
- [x] **OWNER STEP:** the auto-created groups already exist, so the first apply will fail with `ResourceAlreadyExistsException` unless each is imported first — `terraform import aws_cloudwatch_log_group.<name> <group-name>`, listed explicitly in `iac/README.md` (B10).
- [x] `fmt -check`, `init -backend=false`, `validate` — clean.
- [x] Commit `cloudwatch.tf`; report `variables.tf`.
**Acceptance.** Every log group the estate writes to is declared with a retention, and the import steps are written down.

### B5 — Transaction Search (master 2.5; research 04 §1.2)

**Files.** Modify `cloudwatch.tf`, `iac/README.md`.
**Steps.**
- [x] Add `aws_cloudwatch_log_resource_policy` granting `logs:PutLogEvents` / `logs:CreateLogStream` to the `xray.amazonaws.com` service principal on the `aws/spans` log group (the CloudFormation path needs `AWS::Logs::ResourcePolicy` + `AWS::XRay::TransactionSearchConfig`; the resource policy has a first-class `aws` provider resource, the toggle does not).
- [x] Document the enablement itself as an **OWNER STEP** (console: CloudWatch → Application Signals → Transaction Search; or the X-Ray trace-segment-destination CLI call), with the indexing percentage left at the 1 % default (100 % ingested at $0.35/GB, 1 % indexed free). Record the alternative in §11: if B1c's outcome adds the `awscc` provider anyway, `awscc_xray_transaction_search_config` replaces this OWNER STEP.
- [x] `fmt`/`validate` — clean. Report the modified files.
**Acceptance.** The spans log group's resource policy is in code; the account toggle is a single documented owner action with its alternative recorded.

### B6 — Private DNS name for the gateway (master 2.5; spec §3.1)

**Files.** Modify `otel_gateway.tf`.
**Steps.**
- [x] Add `aws_route53_zone.internal` — private, `name = "${var.environment}.internal"`, `vpc { vpc_id = aws_vpc.main.id }` (the VPC already has `enable_dns_hostnames` and `enable_dns_support`, `networking.tf:4-5`, so a private zone resolves) — and `aws_route53_record.otel`, an A record for `otel.${var.environment}.internal` pointing at `aws_instance.weaviate_observability.private_ip`.
- [x] `fmt`/`validate` — clean. Commit (the file is new to this stream).
**Acceptance.** `OTEL_EXPORTER_OTLP_ENDPOINT` never has to change when the collector moves hosts — the spec's stated reason for the name.

### B7 — Re-point App Runner and Lambda (master 2.5)

**Files.** Modify `apprunner.tf`, `lambda.tf`.
**Steps.**
- [x] Replace `OTEL_ENDPOINT = "http://<private ip>:4317"` in both files with `OTEL_EXPORTER_OTLP_ENDPOINT = "http://otel.${var.environment}.internal:4318"`, `OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"`, `OTEL_SERVICE_NAME` (`api`; `ingest-parser` for the pdf-processor Lambda), and `OTEL_RESOURCE_ATTRIBUTES` carrying `service.namespace=flynapse`, `deployment.environment.name=${var.environment}` and, for the Lambda, `parser.kind=s3-pdf-processor` (spec §4's fix for G32's thirteen identities).
- [x] **Same gate as A14:** keep the `OTEL_ENDPOINT` line beside the new ones with a comment naming task A14, and delete it in the same change that lands A14, so an apply before `obs-utils` merges does not blind the services.
- [x] Confirm the App Runner instance role does **not** need CloudWatch permissions (the app speaks OTLP to the gateway; only the collector signs).
- [x] `fmt`/`validate` — clean. Report both modified files.
**Acceptance.** Both compute services address the collector by its stable private name over HTTP/protobuf.

### B8 — WAF logging configuration (master 2.5)

**Files.** Modify `cloudwatch.tf`, `waf.tf`, `variables.tf`.
**Steps.**
- [x] Add `aws_cloudwatch_log_group.waf` named `aws-waf-logs-${var.environment}` (the `aws-waf-logs-` prefix is mandatory for a WAF log destination) with `retention_in_days = var.log_retention_days`.
- [x] Add `aws_wafv2_web_acl_logging_configuration` gated `count = var.waf_web_acl_arn != "" ? 1 : 0`, with a `redacted_fields` block for the `authorization` and `cookie` headers. **The Web ACL itself is commented out** (`waf.tf:54-180`) — do not uncomment it in this stream; the variable is the seam, and `iac/README.md` records that setting `waf_web_acl_arn` turns logging on once the owner restores the ACL.
- [x] `fmt`/`validate` — clean (validate with the default empty variable, i.e. `count = 0`).
- [x] Report the modified files.
**Acceptance.** Request logging is one variable away from live and the log group has a retention; nothing silently depends on a resource that does not exist.

### B9 — `iac/modules/otel-gateway` for client accounts (master 2.6; ruling 14)

**Files.** Create `modules/otel-gateway/{main.tf,variables.tf,outputs.tf,README.md}` and `modules/otel-gateway/examples/basic/{main.tf,variables.tf}`.
**Steps.**
- [x] Module contents: `aws_ecs_task_definition` running `otel/opentelemetry-collector-contrib` at the pin from `VERSIONS.md` (a module variable defaulting to `0.160.0`), Fargate, `awslogs` driver into a module-created log group; `aws_ecs_service` in the caller's private subnets with a module-created security group admitting `4318` and `4319` from a caller-supplied list of client security groups only; `aws_iam_role` task role with `CloudWatchAgentServerPolicy` plus the scoped logs inline policy; `aws_iam_role` execution role; `aws_ssm_parameter` entries for the overlay env (region, log group, log stream, optional Phoenix endpoint) referenced from the task definition's `secrets`; optional `phoenix_enabled` variable adding a second container (ruling 11's "optional client-account container"); `aws_service_discovery_private_dns_namespace` + service so clients get the same `otel.<env>.internal` contract. Config delivery: the module takes `collector_config_s3_uri` (base + overlay + optional fragment) so the same `deployment/otel` files ship unchanged — the module must not embed a copy of the config.
- [x] `examples/basic` is a standalone root (its own `terraform` block, no backend) that instantiates the module with dummy ids, purely so `validate` exercises it.
- [x] Follow the `gpu-host` root's conventions: `required_version` pinned, provider version pinned, `default_tags`, a README table of every resource created and why.
- [x] `terraform fmt -check`, `terraform init -backend=false && terraform validate` inside `modules/otel-gateway/examples/basic` — clean. **`plan` is an OWNER STEP** (needs credentials; it also proves nothing without a real cluster).
- [x] **Logging coverage:** the task definition sets the collector's own telemetry to `info` via `OTELCOL_SELF_METRICS_HOST` and the `awslogs` driver, so a client-account collector's failures are visible in their CloudWatch.
- [x] Commit the whole module and example by pathspec.
**Acceptance.** A client account gets the gateway as one module call with no copy of the collector config and no cross-account credential.

### B10 — `iac/README.md` and the post-apply probe script (master 2.5, verification)

**Files.** Create `scripts/otel_probe.sh`. Modify `README.md`.
**Steps.**
- [x] `scripts/otel_probe.sh` (`set -euo pipefail`): posts one OTLP/JSON log record and one span to `http://otel.<env>.internal:4318`, waits, then `aws logs filter-log-events` on `/flynapse/<env>/otel` for the marker string and `aws xray get-trace-summaries` for the trace id; prints one line per stage and exits non-zero if either is absent. **OWNER STEP to run** — it needs to run inside the VPC (from the demo box over SSH) with credentials.
- [x] `README.md`: an "Observability" section with the apply order (B2 → B3 → B4 with its imports → B5 with its owner toggle → B6 → B7 → B8), the `terraform import` lines for the pre-existing log groups, the Transaction Search enablement step, the probe invocation, and the de-synced-root warning from §1.6 in bold.
- [x] `bash -n scripts/otel_probe.sh` — clean. Commit the script; report the README.
**Acceptance.** Everything the owner must do by hand is one ordered list in the repo's own README, and the "did it actually arrive" question has a scripted answer.

---

## 9. Cross-stream and cross-worktree dependencies

| Edge | Direction | Note |
|---|---|---|
| A7 → B3 | A must land first | the box mounts `deployment/otel`; the script builds the `--config` list |
| A13 ← B3 | B first | the aws env file must exist before the demo collector loses its OSS backends |
| A2 → `poc_ec2_setup.sh` | A defines the env names, B writes them into `deployment/poc/.env` | add `LOKI_RETENTION_PERIOD`, `TEMPO_BLOCK_RETENTION`, `PROM_RETENTION_TIME`, `GRAFANA_ADMIN_PASSWORD`, `PHOENIX_SECRET`, `PHOENIX_ADMIN_PASSWORD`, `LOKI_TENANT_ID` to the generated file; every compose reference carries a default so a stale `.env` still boots (except the two `:?` secrets, which must fail loudly) |
| A4 → Stream U 1b / Stream P 5.5 | A produces | the browser-forward endpoint is port **4319**, not 4318, and the three identity headers are the contract |
| A4 → Stream L 3.6 | A produces | span attribute `flynapse.content_copy="true"` selects the Phoenix copy |
| A14, B7 ← Stream U 1a.7 | U first | the legacy `OTEL_ENDPOINT` lines come out only after `utils.config` stops reading it |
| A3 → Stream P 5.2 | P later | the Grafana Postgres datasource on `flynapse_readonly` is Phase 5's task, not this one |
| A5/A7 → Phase 6 | later | `prometheus.yml` keeps an empty `rule_files` for task 6.3 |

## 10. Accepted regressions and deferrals (record in the phase report)

- **The POC browser's direct OTLP path stops working when A4 lands.** `poc/docker-compose.yml:213` points the dashboard at `${OTEL_CROSS_ORIGIN}:4318/v1/traces` and the current collector allows that origin via CORS. `base.yaml` has no CORS by spec ruling (§3.4: the browser goes through the api gateway). This is the only environment where browser OTel works today (research 02 §3.3), and it goes dark until Stream F's task 4.9 cut-over. Spec-ruled, deliberate, stated in `deployment/otel/README.md`.
- **`ec2_poc.tf:183` still opens 4318 to `0.0.0.0/0`.** Master 0.4 scopes the SG trim to the demo box only. Once the browser stops posting directly (4.9), that rule should narrow to the ALB/app path — recorded as a Future Improvement, not done here, because closing it before the cut-over breaks the POC.
- **Weaviate is not bumped to the latest stable** (§4 exception) — data-plane index migration risk; the owner decides.
- **Portainer** on the demo box (`demo_ec2_setup.sh:18`) is pinned but not removed; whether it should exist at all is an open question below.

## 11. Probe outcomes (filled by B1; empty until run)

| Probe | Run on | Outcome | Decision it drives |
|---|---|---|---|
| B1a CloudWatch OTel metrics GA + temporality in `ap-south-1` | OWNER STEP (needs a live signed send after B3 apply) | doc re-verified 2026-09-05 (research 04 §1.1: GA 2026-06); the owner runs one signed POST of a cumulative histogram to `https://monitoring.ap-south-1.amazonaws.com/v1/metrics` from the demo box post-apply and records acceptance | keep `otlphttp/cwmetrics` or fall back to AMP remote-write |
| B1b Logs OTLP stored field paths | OWNER STEP (after the first real send — run `iac/scripts/otel_probe.sh <env>` then open the stored event in Logs Insights and record the exact field paths, expected `resource.attributes.service.name`) | pending live send | Phase 6 Logs Insights query shapes |
| B1c PromQL alarm support in the resolved `aws` provider | 2026-09-05, `terraform init -backend=false` (via a local-backend override; `providers schema` refuses to run against the un-initialized s3 backend) + `terraform providers schema -json` in `/home/aditya/Code/iac-obs` | resolved provider `hashicorp/aws 5.100.0` (constraint `~> 5.0`, lock gitignored). `aws_cloudwatch_metric_alarm` has NO PromQL/query-language field — only classic attrs + `metric_query.expression` (metric math / Metrics Insights). No `aws_xray_transaction_search_config` resource exists either (only encryption_config/group/resource_policy/sampling_rule). Fallbacks stand: raise the provider constraint or add `awscc` (which would also replace B5's manual toggle); do NOT raise the constraint in this stream — owner call, blast radius on the de-synced root | Phase 6 alarm dialect; whether `awscc` joins the root |
| B1d Application Signals from vanilla SDK spans | OWNER STEP (after B3+B5: send app traffic, open Application Signals, check the service map populates from non-ADOT spans) | pending live send | SLO objects vs RED alarms only |

## 12. Review-triage table (phase close)

| Lens | Question the reviewer must answer | Evidence |
|---|---|---|
| Config correctness | Does every overlay validate on the pinned image, and does the effective pipeline order match what the tests assert? | `validate.sh` output; `test_collector_profiles.py` |
| Security (G17/G31) | Is any admin plane, pprof, zpages or Prometheus exporter reachable off-host in any stack? Is Loki refusing untenanted reads? | `test_compose_port_bindings.py`; smoke's 401 assertion |
| Content safety | Can prompt/completion text reach any pipeline but `traces/content`? | `attributes/strip_content` assertions; smoke's strip assertion |
| Cardinality | Can `session.id`/`user.id`/`enduser.id`/path reach a metric datapoint? | `attributes/metric_cardinality` assertions |
| Reproducibility | Does any floating tag survive? Do `VERSIONS.md` and the compose files agree? | `test_compose_image_pins.py` |
| Terraform blast radius | Does any change destroy or replace a live resource? Are the pre-existing log groups imported before apply? | owner's `plan`; `iac/README.md` import list |
| Deferred items | Is every deferral in §10 stated with a reason, and is the POC 4318 rule tracked? | this file |
| Logging coverage | Does every script fail loudly, echo its stages, and leak nothing? | per-task checkbox |

## 13. Acceptance for Stream I

The `oss` smoke is green end to end (span, metric with `job=flynapse/<service>`, log, health-drop, content-strip, Phoenix content copy); `aws` and `azure` overlays validate in CI on every PR touching `deployment/otel/**`; the demo box runs the collector alone under the `aws` overlay with an instance profile and a private DNS name, its SG trimmed to four ports, its four OSS containers gone; App Runner and Lambda address `otel.<env>.internal:4318`; every log group has a retention; the `otel-gateway` module and its example validate; `VERSIONS.md` records every pin with its release date and the monthly bump policy.

## 14. Open questions for the owner

1. **Portainer on the demo box** (`demo_ec2_setup.sh:18`, ports 8000/9443, which B2 removes from the SG): keep it pinned and loopback-only, or delete it? B2 makes it unreachable either way; deleting the container is a state change I will not take unilaterally.
2. **Provider constraint.** If B1c shows the resolved `aws 5.x` lacks PromQL alarm support, do you want the constraint raised (`~> 6.0`) in this stream, the `awscc` provider added, or the decision deferred to Phase 6? Raising a provider constraint on a de-synced root is a blast-radius call, not a task call.
3. **`terraform plan` as a review artefact.** Given `iac/gpu-host/README.md` records the main root as de-synced from live AWS, do you want a reconciliation pass before any of Stream I's Terraform is applied, or should these resources move to their own self-contained root (the `gpu-host` pattern) and reference the existing VPC/EC2/SGs by data source instead?

---

## Implementation notes (Stream I implementer — Fable 5, 2026-09-05)

Worktree A commits `e70ecc80..189aa918` on `obs-infra`; worktree B commit `fae1c71` on `obs-iac`.
Every edit to a pre-existing file stays uncommitted per §1.5 and is listed in the final report.
Standing pytest command additionally needs `POSTGRES_DB=copilot_mro_test` (the shared env's
`utils.db_guard` refuses a run whose database came from `.env` defaults).

- **A0/B0** — worktrees created at sibling depth, `.env` symlinked, both paths appended to the
  main checkouts' `.git/info/exclude`. Session was killed twice (rate limit, then a WSL crash);
  both resumes verified existing state before continuing — nothing was recreated.
- **A1** — pins per §4; all six observability images pulled successfully, so no pin changed.
  `dpage/pgadmin4:9.17`, `naaive/weaviate-ui:v1.0.3`, `rediscommander/redis-commander@sha256`
  also applied. Weaviate left `:latest` (owner step recorded in `VERSIONS.md`); the pin test
  carries a named `PIN_EXEMPT` entry rather than a weakened rule.
- **A2** — as planned. Learning: Loki's `-config.expand-env=true` substitutes over the RAW file
  including comments — a `${...}` spelled inside a comment aborts startup with "unable to parse
  variable name". Comments now avoid the sequence.
- **A2 deviation (planned in §5.6 but larger)** — **Tempo 3.x restructured its config schema**:
  top-level `ingester:`/`compactor:` no longer exist; retention lives under
  `backend_scheduler.provider.compaction.compaction.block_retention` AND
  `backend_worker.compaction.block_retention` (both set; verified against the v3.0.3
  configuration docs). `tempo.yaml` was rewritten for the pinned major (wal path, work path,
  `stream_over_http_enabled`, `usage_report.reporting_enabled: false`); the retention test
  asserts the new paths and the absence of the 2.x blocks.
- **A3** — the plan's literal "allow-list of {4318}" would have severed real off-host consumers
  (Weaviate from App Runner/Lambda on the demo box, the POC's api/dashboard, local dev's
  host-run api). Implemented as a per-file `ALLOWED_PUBLIC` map (4318 everywhere, plus each
  file's data-plane ports) plus the plan's hard negative list for the ten admin/telemetry ports.
  Grafana password is `${GRAFANA_ADMIN_PASSWORD:?...}` in all stacks; `LOKI_TENANT_ID` is passed
  to Grafana for the datasource header; README rewritten without Jaeger.
- **A4** — as planned, plus the session lead's amendments (upsert; 4319 browser-forward) and the
  Stream U hand-off: the redaction test asserts no blocked pattern matches the nine identity/id
  keys (`tenant.id, enduser.id, session.id, request.id, automation_id, automation_run_id,
  chat_id, block_id, department`) nor a representative UUID value. Learning: the collector
  0.160 warns on the inline `service.telemetry.resource` map — switched to the
  `resource.attributes` array form. OTTL statements are written context-bare and the collector
  normalises them to `datapoint.`/`log.` prefixed paths (info log, harmless).
- **A5** — as planned; `prometheusremotewrite` still accepts the top-level `endpoint` key at
  v0.160.0 (the README now prefers `http.endpoint`; kept top-level for clarity, `validate` is
  the arbiter). The runtime logs deprecation *alias* warnings (`otlphttp`→`otlp_http`,
  `resourcedetection`→`resource_detection`, `prometheusremotewrite`→`prometheus_remote_write`) —
  aliases retained deliberately: they match every published example and the master plan's
  spellings; a rename is a future improvement once the aliases are actually removed upstream.
- **A6** — as planned; mutation-verified (misspelled processor → exit 1 naming the profile).
  Deviation: the repo's `.gitignore` has a Python-venv `env/` pattern that catches
  `deployment/otel/env/`, so the three example files are tracked via `git add -f` (once tracked,
  git follows them normally). The plan's named path was kept rather than renaming the directory.
- **A7** — as planned; CORS env vars deleted with the legacy config. The manual "bring the local
  stack up once" step was NOT run against `deployment/docker-compose.yml` directly: the dev
  stack was RUNNING under the same default compose project name and ports, and the no-disturb
  rule wins. Container startup (all four reach running + the collector's startup log naming both
  config sources) was proven through A8's project-scoped smoke instead.
- **A8** — green end to end (span in Tempo; delta sum arrives cumulative with
  `job=flynapse/smoke-service`, `instance=smoke-instance-1`; tenanted Loki read + 401 untenanted;
  `/config` reports retention; health span dropped; `gen_ai.input.messages` stripped).
  Learnings: (1) compose `!override` needed on `ports`, `volumes` AND the fixed-name network —
  merge appends ports (re-binding the dev stack's), and the base network's fixed
  name+subnet collides with the running dev network; (2) relative bind paths in an override file
  resolve against the PROJECT directory (first `-f` file's dir), not the override's own dir —
  a wrong path is auto-created as a root-owned host directory and the container then fails with
  "mount a directory onto a file"; (3) Loki (10001) and Prometheus (nobody) need
  `tmpfs mode: 0777`; (4) compose interpolates the WHOLE file even for unstarted services, so
  the fixture supplies dummy `GRAFANA_ADMIN_PASSWORD`/`PHOENIX_*` values.
- **A9** — as planned; the smoke posts a `flynapse.content_copy="true"` span, finds it in
  Phoenix's `internal` project via `/v1/projects/internal/spans` and proves Tempo 404s it.
  Deviation: the POC compose has NO Postgres service, so the POC Phoenix keeps SQLite on the
  persistent EBS volume (`PHOENIX_WORKING_DIR=/mnt/data`); the root compose Phoenix uses the
  stack's Postgres as planned. `transform/phoenix_project` reads `tenant.id` from resource OR
  span attributes (span wins, being the later statement) — content copies may carry it either way.
- **A10** — as planned. Deviation: `otelcol validate` INSTANTIATES `sigv4auth`, which walks the
  AWS credential chain and hard-fails without IMDS; `aws.env.example` therefore carries
  clearly-labelled validation-only dummy `AWS_ACCESS_KEY_ID`/`SECRET` so CI stays hermetic (the
  A12 guard names them as dead-env exemptions with the reason).
- **A11** — as planned; also verified `cumulative_to_delta` is the canonical id at the pin
  (`cumulativetodelta` deprecated), same rename family as §5.1 — the test pins the canonical
  spellings for both.
- **A12** — as planned; the guard resolves each profile's var set as base ∪ overlay
  (∪ fragment when the profile's example sets `PHOENIX_ENDPOINT`).
- **A13** — as planned (aws overlay + `env_file: /opt/otel/collector.env`; orphaned-data note in
  the file header). Follow-up: the A2 Prometheus count in `test_retention_config.py` now expects
  three stacks, since the demo lost its Prometheus by design.
- **A14** — **NOT executed; gated on Stream U task 1a.7** (checkboxes left open). A7 planted the
  standard `OTEL_*` set beside the legacy line with the gate comment.
- **B1** — B1c run and recorded in §11 (aws 5.100.0; NO PromQL alarm support; no Transaction
  Search resource; fallbacks stand — owner decides constraint-raise vs `awscc` at Phase 6).
  B1a/B1b/B1d recorded as OWNER STEPS in §11 with the exact commands. Learning: `terraform
  providers schema` refuses to run after `init -backend=false` when an s3 backend is configured —
  a throwaway gitignored `backend_override.tf` (local backend) unblocks it; removed afterwards
  and the standard `init -backend=false && validate` re-run clean.
- **B2** — SG trimmed to 22 (allowed IP) + 8080/50051/4318 (App Runner + Lambda SGs).
  Dropped-port evidence, one line each: `3000/9090/3100/3200` Grafana/Prometheus/Loki/Tempo UIs —
  containers removed by A13 and `core` never learned `LOKI_BASE_URL` (research 02 §4.2, probe
  G29); `9464` collector Prometheus exporter — replaced by unpublished `8888` (A7); `13133`
  health — consumed on-host only; `1777` pprof — deleted at A1; `14250/14268` Tempo alternative
  ports — no client ever used them; `7777` weaviate-ui — loopback-bound in compose; `8000/9443`
  Portainer — reachable over SSH tunnel only, and its fate is open question §14.1; `4317` gRPC —
  every client moves to 4318 http/protobuf (spec §3.1). OWNER STEP: `terraform plan` must show
  SG-rule removals only.
- **B3** — `otel_gateway.tf` (role with `CloudWatchAgentServerPolicy` + scoped `/flynapse/*`
  inline policy incl. the `:*` stream ARNs; instance profile), attached in `ec2.tf` (the
  instance had none). `demo_ec2_setup.sh` rewritten under `set -euo pipefail` with one echo per
  stage, a bounded EBS wait, Portainer pinned `2.45.0`, the observability-data mkdirs removed,
  `/opt/otel/collector.env` written (chmod 600, no secrets), and the Phoenix fragment appended
  via a compose override ONLY when the env file carries a non-empty `PHOENIX_ENDPOINT` — the
  conditional lives in the script, not the config. `ec2.tf`'s templatefile gains `aws_region` +
  `environment` args. OWNER STEPS in `iac/README.md`: plan/apply (note
  `user_data_replace_on_change` REPLACES the instance), merge `obs-infra` to copilot-mro `main`
  before `restart-services.sh` (the box pulls `main`), then confirm the collector log names both
  config sources.
- **B4** — `cloudwatch.tf` declares `/flynapse/<env>/otel`, both App Runner groups (named via
  `aws_apprunner_service.api.service_name`/`.service_id`), both Lambda groups — all at
  `var.log_retention_days` (default 30, ruling 13). Import list in `iac/README.md`.
- **B5** — `aws_cloudwatch_log_resource_policy.transaction_search_spans` grants
  `xray.amazonaws.com` write on `aws/spans` and `/aws/application-signals/data` with
  SourceAccount/SourceArn conditions. The account toggle is documented as an OWNER STEP (1%
  indexing default); `awscc_xray_transaction_search_config` noted as the alternative if B1c's
  outcome adds `awscc`.
- **B6** — private zone `<env>.internal` + A record `otel.<env>.internal` → the box's private IP.
- **B7** — both files gain the standard `OTEL_*` set beside the gated legacy `OTEL_ENDPOINT`
  (removed with A14); Lambda carries `parser.kind=s3-pdf-processor` and
  `OTEL_SERVICE_NAME=ingest-parser`; App Runner `OTEL_SERVICE_NAME=api`. Confirmed the App
  Runner instance role needs NO CloudWatch permissions (only the collector signs). Hand-off (2)
  applied as a GATE-COMMENTED `health_check_configuration` (`HTTP /health/live`): activating it
  before Stream U's root health routes exist would fail every health check and take the service
  down on apply — same gate as the legacy-line removal, spelled in the comment and README.
- **B8** — `aws_cloudwatch_log_group.waf` (`aws-waf-logs-` prefix, `provider = aws.global`
  because the ACL is CLOUDFRONT-scoped so the destination must live in us-east-1 — a detail the
  master plan didn't state) + `aws_wafv2_web_acl_logging_configuration` gated on
  `var.waf_web_acl_arn` with authorization/cookie redacted. Validates with the default empty
  variable (count = 0).
- **B9** — module + `examples/basic` written and validated (`fmt`, `init -backend=false`,
  `validate` inside the example). Config delivery via the collector's s3 confmap provider URIs;
  variable named `collector_config_s3_uris` (list — the plan's singular name could not carry
  base + overlay + fragment; noted here as the one interface rename). Task role additionally
  gets `s3:GetObject` on the caller-named config bucket. Learning: `cond ? [a,b] : [a]` is an
  inconsistent-tuple type error in HCL — `concat([a], cond ? [b] : [])` is the working form.
- **B10** — `scripts/otel_probe.sh` (bash -n clean; posts OTLP JSON log+span, bounded retries
  against `logs filter-log-events` and both X-Ray lookup forms, one echo per stage, exits
  non-zero on absence) + the README "Observability" section with the full apply order, imports,
  Transaction Search step, probe invocation and the de-synced-root warning in bold.

### Cross-stream hand-offs (produced by this stream)
- Browser-forward: port **4319**, headers `X-Tenant-Id`/`X-User-Id`/`X-Session-Id`, core setting
  `OTEL_BROWSER_FORWARD_ENDPOINT` (set in the POC api env; documented in `deployment/otel/README.md`).
- Content marker: span attribute `flynapse.content_copy="true"` (Stream L 3.6).
- For Stream U (flagged, NOT edited here): `copilot-mro/.env.sample:11-12` still carries
  `OTEL_ENDPOINT` + `OTEL_SERVICE_NAME=mro-copilot-rag`; `api/Dockerfile:88` hardcodes
  `OTEL_SERVICE_NAME="copilots"` (G12). A14 + the B7 legacy lines + the App Runner health check
  block all come out together after `obs-utils` merges.

### Uncommitted pre-existing edits (per §1.5, listed for the report)
- copilot-mro worktree: the four compose files, `loki-config.yaml`, `tempo.yaml`,
  `prometheus.yml`, `observability-local/README.md`, the Grafana datasources file; DELETED
  `observability-local/otel-collector-config.yaml`.
- iac worktree: `ec2.tf`, `apprunner.tf`, `lambda.tf`, `variables.tf`, `demo_ec2_setup.sh`,
  `README.md`.

## Lessons
- (2026-09-05) The standing pytest command from the brief lacked `POSTGRES_DB`; the shared env's
  db-guard refuses the run. Rule: every pytest invocation from the shared `api` env in this
  workspace carries `POSTGRES_DB=copilot_mro_test`.
