# Task 2 Report — Collector Profiles Reconciliation

Status: `DONE_WITH_CONCERNS`

## Design Choice

I added a profile-level New Relic overlay and a separate `durability-production.yaml` fragment instead of changing application code or duplicating backend overlays.

The key composition choice is:

- `base.yaml` defines `file_storage/production_queue` with `/tmp` defaults so local POC startup does not require a host-mounted production volume.
- Every backend overlay enables `file_storage/production_queue` in `service.extensions`, preserving its complete operational pipeline definitions and processor order.
- `durability-production.yaml` deep-merges retry and queue settings into exporters only. It deliberately does not define `service:` because Collector config list merge would replace `service.extensions` and `service.pipelines`.
- OTLP/HTTP exporters use bounded `sending_queue.storage: file_storage/production_queue`.
- `prometheusremotewrite/prom` uses its native bounded `remote_write_queue` plus retry because the pinned exporter does not support exporterhelper `sending_queue`. OSS traces and logs still use the file-backed queue.

Official references used for that exception and contract check:

- New Relic OTLP ingest guidance: `https://docs.newrelic.com/docs/opentelemetry/best-practices/opentelemetry-otlp/`
- Collector exporterhelper persistent queue contract: `https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md`
- Collector Prometheus remote-write exporter docs: `https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/prometheusremotewriteexporter/README.md`

## Files Changed

Copilot MRO:

- `deployment/otel/backend-newrelic.yaml`
- `deployment/otel/durability-production.yaml`
- `deployment/otel/env/newrelic.env.example`
- `deployment/otel/base.yaml`
- `deployment/otel/backend-oss.yaml`
- `deployment/otel/backend-aws.yaml`
- `deployment/otel/backend-azure.yaml`
- `deployment/otel/env/oss.env.example`
- `deployment/otel/env/aws.env.example`
- `deployment/otel/env/azure.env.example`
- `deployment/otel/README.md`
- `deployment/otel/validate.sh`
- `deployment/otel/dashboards/CATALOGUE.md`
- `tests/integration/otel/test_collector_profiles.py`
- `tests/integration/otel/test_profile_env_documented.py`

Docs:

- `plans/observability-rebuild-phase-8-audit-followups.md`
- `plans/observability-rebuild-research/08-post-migration-rescoping.md`
- `.superpowers/sdd/observability-merge-completion/task-2-report.md`

## RED Evidence

Initial test command without an explicit test DB did not reach the new assertions:

```bash
DEBUG=false poetry run pytest tests/integration/otel/test_collector_profiles.py tests/integration/otel/test_profile_env_documented.py -q
```

Result: exit 4. The repo DB guard refused to run because `POSTGRES_DB` was unset and the `.env` path names protected `copilot_mro`.

Corrected RED command:

```bash
DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest tests/integration/otel/test_collector_profiles.py tests/integration/otel/test_profile_env_documented.py -q
```

Result: exit 1, `6 failed, 14 passed`.

Expected failure classes:

- existing OSS/AWS/Azure overlays did not enable `file_storage/production_queue`;
- `backend-newrelic.yaml` was missing;
- `durability-production.yaml` was missing;
- `base.yaml` had no production file-storage extension;
- env documentation tests failed because durability variables were not represented.

## GREEN Evidence

Targeted profile/env suite:

```bash
DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest tests/integration/otel/test_collector_profiles.py tests/integration/otel/test_profile_env_documented.py -q
```

Result: `20 passed, 1 warning`.

Full non-container OTel integration lane:

```bash
DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest tests/integration/otel -q
```

Result: `73 passed, 10 skipped, 1 warning`.

The warning was pytest cache write denial in the sandboxed worktree, not a test failure.

Shell/static checks:

```bash
bash -n deployment/otel/validate.sh
```

Result: exit 0.

```bash
git diff --check
```

Result: exit 0 in both `copilot-mro` and `docs` before their commits.

## Static Validation Results

Repository-native pinned Collector validation path: `deployment/otel/validate.sh`.

Result: not run, intentionally. The script invokes `docker run ... otel/opentelemetry-collector-contrib:<pin> validate ...`, and the task brief forbids launching Docker. I updated the script so owner/CI validation covers both:

- normal profile composition;
- production durability composition with `durability-production.yaml` appended and no Phoenix content fragment.

Non-container validation performed instead:

- YAML/profile shape tests passed;
- env documentation tests passed;
- full OTel integration lane passed;
- `validate.sh` shell syntax passed.

## Official Contract Mapping

New Relic:

- `backend-newrelic.yaml` uses `otlphttp/newrelic`.
- Endpoint comes from `NEW_RELIC_OTLP_ENDPOINT`.
- License key comes from `NEW_RELIC_LICENSE_KEY` via `headers.api-key`.
- `env/newrelic.env.example` leaves `NEW_RELIC_LICENSE_KEY` blank; no config default is committed.
- All five operational pipelines route to `otlphttp/newrelic`.

Durability:

- `base.yaml` defines `file_storage/production_queue`.
- `durability-production.yaml` applies bounded retry and bounded queues.
- OTLP/HTTP exporters use `sending_queue.storage: file_storage/production_queue`.
- OSS `prometheusremotewrite/prom` uses bounded `remote_write_queue` because it does not support `sending_queue`.
- README documents writable storage, disk sizing, overflow/drop conditions, retry exhaustion, disk failure, and that the queue is not permanent storage.

Pipeline and Phoenix contracts:

- All backend overlays still declare exactly `traces`, `metrics`, `logs`, `traces/browser`, `logs/browser`.
- Existing processor ordering is preserved; no application business code or Flynapse UI code changed.
- `durability-production.yaml` does not define `service:` and does not mention `PHOENIX_ENDPOINT`.
- `backend-newrelic.yaml` has no Phoenix exporter or content lane.
- `validate.sh` production-durability pass intentionally does not append `content-phoenix.yaml`.

Docs:

- Phase 8 plan now leaves CI/pinned validation, Azure support re-check, live canaries and restart proof unchecked.
- Current-state notes now identify New Relic/durability as configuration evidence only.

## Commit SHAs

- Copilot MRO: `1b9d17335465ccd28e3a9002d364ee79fe98efa7`
- Docs plan/current-state reconciliation: `d13a01af7d56b0e6da32505e9741555518286ff2`
- Docs report: committed after this file is written; final task status records the containing commit SHA.

## Final Statuses

- New Relic configuration: complete as checked-in Collector config.
- Production durability configuration: complete with the documented Prometheus remote-write exception.
- Non-container tests: passed.
- Pinned Collector Docker validation: pending by task constraint.
- Live provider trace/metric/log retrieval: pending by task constraint and credentials/infrastructure.
- Queue restart survival proof on a production-style mount: pending.
- Azure production support re-check: pending.

## Concerns

1. `prometheusremotewrite/prom` cannot use file-backed `sending_queue`; it has bounded in-memory `remote_write_queue` only. OSS traces/logs are file-backed, and cloud/New Relic OTLP exporters are file-backed.
2. Static shape tests do not replace pinned `otelcol validate`; CI or an owner-run Docker validation still needs to execute `deployment/otel/validate.sh`.
3. No live provider canary, provider query field-path evidence, Azure supportability refresh, or restart proof was run in this task.
