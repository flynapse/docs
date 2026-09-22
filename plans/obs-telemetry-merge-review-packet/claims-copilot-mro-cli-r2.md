# Claims packet — copilot-mro `obs-merge-cli` review r2 (answers cli review r1)

Independent adversarial review, Opus, 2026-09-21. **Verdict: MERGE-CLEAN** — 0 P0 · 0 P1 · 2 P2 · 4 P3.

Every r1 P1 and P2 is closed in the form r1 asked for. Each P1 fix leaves one residual:
- **P1-1.** The category the controller call wanted to keep does not exist on the events it was kept for.
- **P1-2.** The new guard pins the options object, not the argv the CLI actually parses.

Neither residual ships content or a secret, and both are cheap to fix.

**Read-only on every code tree.**
- Nothing was edited, staged, committed, merged, checked out or stashed in `copilot-mro-obsm-cli`, `copilot-mro-obsm`, `copilot-mro-obsm-r7b` or any sibling. Nothing was pushed.
- No DB, DDL/DML, docker, otelcol, terraform, AWS, Bedrock or Claude CLI call was made. No sub-agent was used.
- At the end, `copilot-mro-obsm-cli` was still at `f1100629` with a clean status.
- copilot-mro's `obs-merge` moved from `6145d42a` to `ac7cda74` during the review, by another lane. Both tips were trial-merged; see below.

All work ran in `scratchpad/cli-review-r2/`:
- **`ws/copilot-mro`**: a `git clone --no-hardlinks` of copilot-mro with origin removed. Every per-SHA lane ran here, on detached checkouts that were clean before each run.
- **`wsm/copilot-mro`**: a second clone for the trial merges. `obs-merge-cli` `f1100629` was merged into `obs-merge` `6145d42a` (scratch `1c14ae44`), then into `ac7cda74` (scratch `8a5ca240`).
- **`mut/copilot-mro`**: a `git archive` of `f1100629`. Every mutant ran here.
- **`sib/`**: `git archive` snapshots of utils-obsm `4d86ae9`, core-obsm `1232f21` and flynapse-otel `05e1a6e`. `05e1a6e` is flynapse-otel's committed `HEAD`; the checkout's uncommitted edits were not used.
- **Other siblings.** `api`, `dashboard` and `docs` resolve to their `-obsm` checkouts, and the rest to the primary checkouts, all as read-only symlinks.

| repo | worktree | branch | range | siblings |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm-cli` | `obs-merge-cli` | `7416d7a4..f1100629` (11 commits) | utils-obsm `4d86ae9`, core-obsm `1232f21`, flynapse-otel `05e1a6e` (archives) |

**The lane recipe, as run, from the tree root:**

`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPYCACHEPREFIX=<fresh per run> PYTHONPATH=<netguard>:<tree>:<utils>:<core>:<flynapse-otel> /home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider --rootdir=<tree> -m "not db" tests/<lane>`

- pytest's own exit status is written to the log. It was never read through a pipe.
- `rootdir` was the scratch tree in every run.
- `copilot_mro.app.__file__` was `<tree>/copilot_mro/app/__init__.py` in `ws`, `wsm` and `mut`, probed with the same `PYTHONPATH`. `utils` and `flynapse_otel` resolved to the archives.

**The netguard** is a `sitecustomize`. It refuses:
- every non-loopback connect;
- every loopback connect below port 20000;
- any launch of `claude`, `_bundled/claude`, `docker`, `otelcol`, `terraform` or `psql`.

It logs each refusal and each launch together with the test id.

**The Claude CLI was never launched.**
- Across every lane and every mutant, the only executables started were `git`, the venv python and `uname`.
- It refused 12 `docker` launches, from the pre-existing compose and grafana tests.
- It refused connects to IMDS (`169.254.169.254`), made by botocore's credential chain inside pre-existing `agent_claude` tests.
- The bundled binary was read only as bytes, with `grep -boa` and `dd`.

**Method for the CLI claims.** I read Claude Code 2.1.220 (`claude_agent_sdk/_bundled/claude`, SDK 0.2.128) by byte offset. All offsets are in that file:
- **`Ac()` @250663751** is the event emitter.
  - Its `body` is `` `claude_code.${e}` ``, a constant per event.
  - Its common attributes are `qRt()`, the `event.*` keys and `prompt.id`.
- **The API-error path.** `Ac("api_error", …)` is @254587807, followed by `Ac("api_retries_exhausted", …)`. The message builder `u$y` is @254583420.
- **`Cpo()` @252028519** is the CLI's closed error classifier (`auth_error`, `rate_limit`, `api_timeout`, …).
- **The class-field bounders.** `wRo()` is @256808847, and `jp()` / `q0t()` are @247325074 / @247325582.
- **Telemetry init.** `oI_()`, `sYd()` and `EFo()` are @~258552000: telemetry init, the logs exporter and its config.
- **`oYd()` @258549740** is the resource merge.
- **The bundled OTLP exporter's env readers** `hh_()` / `Ah_()` are @~258012400.

In the SDK I read `SubprocessCLITransport._build_command` (`subprocess_cli.py:459-620`, `extra_args` at `:611`) and `close()` (`:880-915`).

---

## Findings, ranked

### No P0, no P1

The strongest attack was r1's: what leaves the process, on any event, with every flag as pinned? After `a76df7b8` the answer contains no provider or exception text at all.

- **The free text is gone.** `error` and `error_message` are outside the keep-list, so `keep_matching_keys` deletes them on every CLI record, whatever the event. R19, which re-admits `error`, turns 3 tests red.
- **The body is constant:** `claude_code.<event>`.
- **The resource holds nothing sensitive.** It carries `service.*`, `os.*`, `host.arch` and `wsl.version`, plus the parent's own `OTEL_RESOURCE_ATTRIBUTES`. In every deployment that is `service.namespace=flynapse,deployment.environment.name=<env>` (`iac/apprunner.tf:48-51`, `iac/lambda.tf:118-121`).
- **The surviving class fields are bounded by the CLI itself**, not only by our cap (see "What I tried to break").
- **The `--settings` argv carries no secret.** It holds the static pins, the logs endpoint and the resource attributes, none of them secret in any deployment. A non-empty header value is kept off it (R01 red).
- **Traces and metrics stay off.** Metrics are now also dropped at the collector.

### P2-1 — `api_error` and `api_retries_exhausted` carry no error class, so after the drop a non-HTTP failure has no category at all

Four texts and a test fixture say a class survives. It does not.

**Where the claim is made.**
- `copilot_mro/app/services/claude_cli_telemetry.py:4-6`: "`api_error`: status code, attempt number, error class".
- `deployment/otel/base.yaml:156-162`: "A failure is carried by its CATEGORY only: `status_code`, `attempt`, and the CLI's own regex-bounded class fields `error_type` / `error_name` / `error_code`".
- The plan's r1-fixes note, `observability-telemetry-merge-and-completion.md:972-974`.
- The `f1100629` commit message.

**Where the test asserts it.** `tests/integration/otel/test_claude_code_log_allowlist.py:201-222` feeds `api_error` and `api_retries_exhausted` records that carry `error_type="auth_error"` and `error_name="AccessDeniedException"`, and asserts both survive.

**What the CLI actually writes.**
- `api_error` carries `model`, `error`, `duration_ms`, `attempt`, `request_id`, `client_request_id`, `speed`, `query_source`, `effort` and the attribution keys. It adds `status_code` only when the error is an `APIError`.
- `api_retries_exhausted` carries the same keys, minus `duration_ms` and `attempt`, plus `total_attempts` and `total_retry_duration_ms`.
- Neither event has `error_type`, `error_name` or `error_code`.
- The CLI does compute a closed class, `H = Cpo(e)`. It hands `H` only to `O("tengu_api_error", {errorType: H, …})`, its first-party analytics, and never to OTel.
- The three class fields exist on other events: `tool_result` (`error_type = wRo(e)`), `internal_error` (`error_name`, `error_code`) and `mcp_server_connection` (`error_code`). None of them is an event the controller call was about.

**The Bedrock 403, witnessed in the binary.**
- `Cpo` returns `"auth_error"` for any `APIError` with status 401 or 403.
- The CLI then takes the `w("API auth_error: …")` debug-log branch. It never calls `xe()`, so no `internal_error` record is written either.
- What reaches a backend is `event.name=api_error`, `status_code=403`, `attempt`, `model`, `duration_ms`, `request_id` and so on: the status code, and no class. That is safe and useful.
- A failure with no HTTP status has no category at all. That covers a connection reset, DNS, TLS, `api_timeout`, and a credential-provider error raised before the request. Each one reaches a backend as an `api_error` with no category of any kind, and they all read the same.

**Why it matters.** Nothing leaks. But it is a gap in the signal contract:
- Against the ruling ("per-API-call … errors").
- Against the controller's call ("only a capped category (status code / error type) is kept").
- And the test is green about a record shape the producer never emits. That is the RV4 pattern.

**The fix is a controller call:**
- **(a) Accept `status_code` as the whole category.** Correct the four texts. Make the test fixture the CLI's real `api_error` shape, with no class fields, and assert that `status_code` survives and nothing else does.
- **(b) Derive a closed category at the collector, before the keep-list, and keep it.**
  - For example: `set(log.attributes["error_kind"], "no_http_status") where log.attributes["event.name"] == "api_error" and log.attributes["status_code"] == nil`.
  - Optionally refine it with `IsMatch` rules on `error` (`timeout`, `ECONN…`) whose output is only a constant.
  - Either way no text leaves, only a constant. Add `error_kind` to `KEEP_SET`.

### P2-2 — P1-2's new guard pins `options.env` and `options.settings`, not the argv the CLI parses

With `extra_args`, a second `--settings` gets onto the argv and replaces the pins' flag layer.

**Where.** The guards are `tests/agent_sdk/core/test_agent_sdk_cli_telemetry_reaches_query.py:90-109` and `tests/unit/agent_claude/test_claude_cli_telemetry_env.py:407-466`. They guard `copilot_mro/app/services/agent_claude/orchestrator.py:2360-2409`.

**The mutant.** R06 adds `extra_args={"settings": "{}"}` to the orchestrator's one `ClaudeAgentOptions(...)` call. All 20 tests stay green:
- the AST test still sees both builder keywords and no splat;
- the `run_query` test still sees `options.env` and `options.settings` intact.

**What the mutant does to the CLI.**
- I built the argv offline, through the real `SubprocessCLITransport._build_command()`, without starting a process.
- It carries `--settings` twice: ours first, then `{}`. The SDK appends "extra args for future CLI flags" after its own `--settings` (`subprocess_cli.py:611`).
- The CLI declares `.option("--settings <file-or-json>", …)` with no parser function, so commander keeps the last value. The flag layer becomes `{}`.
- Any settings file the CLI loads is then laid over `options.env` unopposed again. The orchestrator loads `project`. This is the exact channel r1's CLI-04 closed.
- The hidden policy-tier option `--managed-settings`, passed through `extra_args`, would outrank even the pins.

**Why P2 and not P1.** No code passes `extra_args` today. This is a hole in the guard, not a live defect.

**The fix.** Either:
- In the `run_query` test, feed the recorded options into the real `SubprocessCLITransport(prompt=…, options=options)._build_command()`, as the unit test already does for its own options. Assert exactly one `--settings`, whose JSON equals `{"env": expected}`, and no `--managed-settings`.
- Or have the AST test refuse an `extra_args` keyword on the one options call.

### P3-1 — Header resolution is not proved against the exporter

`tests/unit/agent_claude/test_claude_cli_telemetry_env.py:331-373` claims the destination is "resolved exactly as the real `OTLPLogExporter()` resolves them — proved against that exporter, decoys included".
- For the endpoint, that holds: R02 goes red.
- For headers, no case sets `OTEL_EXPORTER_OTLP_LOGS_HEADERS` to a non-empty value. So the rule that the logs-specific variable beats the generic one can be deleted or reversed with every test green:
  - R03 ignores the logs-specific variable (`headers = environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")`): 61 passed.
  - R04 lets the generic variable win: 61 passed.

The production mirror at `claude_cli_telemetry.py:130-132` is correct today, and no deployment sets any OTLP header.

**The fix:** add one `DESTINATION_CASES` row with both header variables non-empty and different.

### P3-2 — The owner SQL's content-CHECK read-back matches by substring and ignores `convalidated`

`scripts/drop_llm_turn_content_spill.sql:168-176` accepts the named check when `pg_get_constraintdef(oid) LIKE '%content IS NOT NULL%'`. That predicate also accepts checks that do not enforce the invariant:
- `CHECK ((content IS NOT NULL) OR true)`;
- `CHECK (NOT (content IS NOT NULL))`;
- a `NOT VALID` check, whose definition still contains the text.

Two more gaps line up with it:
- The precondition at `:109-120` checks only the name and `contype`.
- `converge_named_checks` (`scripts/migrate_tenancy_schema.py:2812-2814`) skips any live check that already has the declared NAME, without comparing its definition.

So a hand-made constraint under that name would be neither corrected by the migration nor caught by the SQL.

**How much it matters.** The case is contrived: it needs a manual constraint under this exact name. The spilled-row refusal still runs, so no NULL row can be orphaned today. But the read-back is the script's last line, and the text is now pinned by exact equality (`EXPECTED_DROP_SQL`), so the weak predicate is locked in.

**The fix**, in both the precondition and the read-back: `pg_get_constraintdef(oid) = 'CHECK ((content IS NOT NULL))' AND convalidated`, then update the pin.

### P3-3 — The loss the exit bounds accept is invisible, and the per-request bound can be outranked

**The loss is invisible.**
- When a flush or a shutdown times out, the CLI writes one of these through `w()`, its debug log:
  - `Telemetry flush timed out … Some metrics may not be exported`;
  - `OpenTelemetry telemetry flush timed out after …ms`.
- Nothing reads that log; the SDK captures no CLI stderr in this configuration.
- The module comment declares the trade-off (`claude_cli_telemetry.py:95-99`). The plan's r1-fixes note does not; it records only "each 1000 ms" (`:978`).

**The per-request bound can be outranked.**
- `OTEL_EXPORTER_OTLP_TIMEOUT` is the GENERIC timeout.
- The bundled exporter reads `OTEL_EXPORTER_OTLP_${SIGNAL}_TIMEOUT ?? OTEL_EXPORTER_OTLP_TIMEOUT` (`hh_()`), and the logs-specific name is pinned nowhere.
- So an inherited or settings-file `OTEL_EXPORTER_OTLP_LOGS_TIMEOUT` defeats "each export request to 1 s".
- The exit bound itself still holds. Flush and shutdown are each `Promise.race`d against the two `CLAUDE_CODE_OTEL_*_TIMEOUT_MS`, which both carriers pin.

**The fix.** Add one sentence to the plan note: the trade-off, and that the loss is unobservable. Optionally, pin `OTEL_EXPORTER_OTLP_LOGS_TIMEOUT` beside the generic one.

### P3-4 — Stale or over-claiming prose (the docstring family again)

- **The env test's point 4** (`tests/unit/agent_claude/test_claude_cli_telemetry_env.py:17-20`) says "read off its AST (driving `run_query` far enough to construct its options needs the whole tool surface and a live SDK), and nothing touches `options.env` / `options.settings` afterwards".
  - `69a9b3a5` drives `run_query` offline.
  - The AST test is exactly what could not prove "afterwards": R07, R08 and R15 all pass it.
- **The spill test's point 3** (`tests/registries/tables/test_llm_turn_content_spill_retired.py:17-26`) says the migration "must add nothing, drop nothing". Since `b181a81e` the test body requires exactly one write, the `ADD CONSTRAINT`.
- **The enforced order.** The plan says "so the ORDER IS ENFORCED: code → migration → SQL" (`:979-980`). The SQL header says "and only then run this — it refuses otherwise" (`drop_llm_turn_content_spill.sql:33-38`).
  - The script can detect that the migration ran, because the CHECK exists.
  - It cannot detect that the code is deployed.
  - So only migration → SQL is enforced. Code-first remains a documented precondition.
- **The cap test's docstring** (`test_every_kept_value_is_capped_short`, `test_claude_code_log_allowlist.py:225-227`) says "the CLI bounds its class fields at ~70 chars".
  - `error_type` (`wRo`) is at most 70 characters, and `error_code` (`jp`) at most 64.
  - `error_name` (`q0t`, `/^[A-Z][a-zA-Z]*$/`) is letters-only, with no length bound. Our 128 cap is what bounds it.
- **P2-1's four texts** belong to this family too.

---

## Trial merge into `obs-merge`

**Tip 1: `6145d42a`.** This was the tip when the review began. It is 23 commits past the branch point `6aef26e3` and includes `f2984cd8`.
- `git merge --no-ff --no-commit cli` gave **exactly one textual conflict, as predicted:** `tests/unit/observability/test_phase1c_nonagent_scope_guard.py`. Both sides append to `MRO_POST_MERGE_PRODUCTION_PATHS`: obs-merge its r6/r7 entries, this branch its M-CLI-TELEMETRY and M-CAPTURE-TRUNCATE entries.
- I resolved it as the union: deleted the three marker lines, kept both blocks and re-parsed the file. I committed the resolution alone in scratch as `1c14ae44`.
- No other file is changed on both sides. I checked this with `comm` over the two `--name-only` diffs from `6aef26e3`.

**Tip 2: `ac7cda74`.** `obs-merge` moved to this tip during the review, gaining 13 commits: r7 P3-8…P3-14 and "Test hygiene" 5.1–5.7 / §6.8.
- Two of those commits touch files this branch also changes: `llm-agents.json` and `deployment/otel/dashboards/CATALOGUE.md` (r7 P3-13, the embedding panel).
- Both files **auto-merge without conflict**. The merged board parses: 18 panels, no duplicate id, no CLI panel.
- The catalogue keeps obs-merge's edits and this branch's removal of the CLI row and its spec.
- The scope guard conflicts exactly as before. I resolved it the same way and committed it in scratch as `8a5ca240`.

**Semantic conflicts: looked for, none found.**
- In obs-merge, r7 P3-6 made the approval of a seeded file function-granular.
- r7 P2-5 widened the tool-result detector.
- r7 P3-14 made REPAIRED carry across seeds.
- This branch's production files are all approved by explicit entries: `claude_cli_telemetry.py`, `sad_runner.py`, the registry module, the purge, the owner SQL, `llm_content_capture.py`, the DAO and `config.py`. None of them is a tool module.
- This branch's `_mro_exception_text_debt.py` edit (the purge's two reaper sites moved to REPAIRED) merges cleanly under the new carry rule.

**The merged lanes.** All three trees' red sets were compared by test id.

| lane | merged `6145d42a`+`f1100629` | merged `ac7cda74`+`f1100629` | cli `f1100629` |
|---|---|---|---|
| unit/observability | 515 passed, 1 skipped | 524 passed, 1 skipped | 479, 1 skipped |
| integration/otel | 210 passed, 26 skipped, 3F + 9E | 211 passed, 26 skipped, 3F + 9E | 178, 26 skipped, 3F + 9E |
| registries/tables (capture) | 81 | 81 | 81 |
| unit/agent_shared (capture writer) | 1197, 1 skipped | 1198, 1 skipped | 1160, 1 skipped |
| unit/db (purge) | 341 + 1F | 341 + 1F | 341 + 1F |
| unit/agent_claude | 291 | 291 | 291 |
| unit/data_discovery | 368 | 368 | 368 |
| agent_sdk/core | 1377, 1 skipped | 1377, 1 skipped | 1373, 1 skipped |
| unit/infra | 131 + 3F, 2 skipped | not run | 128 + 3F, 2 skipped |

Every red in the merged trees has the same test ids as the cli HEAD's reds. Those are the environmental reds listed below.

**Process.** Resolve the conflict by union, and commit the resolution alone.

---

## Lanes — every commit at its own SHA

Each commit was checked out, detached, in `ws/`. The lanes it touches were run one directory at a time, with `-m "not db"`. Counts are pytest's own.

| commit | lanes | reds |
|---|---|---|
| `7416d7a4` (base) | otel 173 +3F +9E (26 skipped) · observability 479 (1 skipped) · agent_claude 284 | env |
| `a76df7b8` | otel 174 +3F +9E · observability 479 | env, same ids |
| `a0333a38` | otel 176 +3F +9E · observability 479 | env, same ids |
| `69a9b3a5` | agent_sdk/core 1373 (1 skipped) · infra 128 +3F (2 skipped) | env (infra) |
| `c0ae7f54` | agent_claude 290 · data_discovery 368 · reaches_query 2 | none |
| `5ecc7de0` | agent_claude 291 · data_discovery 368 · reaches_query 2 | none |
| `b181a81e` | registries/tables 81 · unit/db 341 +1F · observability 479 | env (unit/db) |
| `717573bc` | registries/tables 81 | none |
| `43962c12` | otel 177 +3F +9E · observability 479 | env, same ids |
| `d4bf083a` | otel 178 +3F +9E · observability 479 | env, same ids |
| `60c6bc85` | observability 479 | none |
| `f1100629` | otel 178 +3F +9E · observability 479 · agent_claude 291 · data_discovery 368 · registries/tables 81 · agent_sdk/core 1373 · infra 128 +3F · unit/db 341 +1F · agent_shared 1160 | env, same id sets |

**The environmental reds.** They are identical by test id at every SHA that ran the lane, and in both merged trees. They are the same as r1's.
- **otel, 3 failed + 9 errors.**
  - 10 tests stop on a `docker` launch the netguard refuses: 6 compose-sample tests, 2 grafana running-stack tests and 2 smoke network-scoping tests.
  - 2 `test_browser_derived_metrics.py` tests read a `dashboard/contracts/browser-signals.json` that the dashboard-obsm checkout lacks.
- **unit/db, 1 failure.** `test_every_documented_invocation_names_a_database…` names three lines outside this range: `test_sad_environment_failures_withhold_secrets.py:532`, `scripts/e2e/figure_arc_headless_e2e.py:32` and `scripts/inspect_llm_turn_content.py:9`.
- **infra, 3 failures.** The `test_cross_repo_reads_name_their_checkout.py` tests assert the real workspace's `-obsm` variants, and the scratch workspace has none.

**The deltas match the new tests exactly.**
- **otel:** +1 at `a76df7b8` (the cap test), +2 at `a0333a38` (keep-list equality and the service-name pin), +1 at `43962c12` (the collector metrics drop) and +1 at `d4bf083a` (the gateway-vocabulary test), for 173 → 178.
- **agent_claude:** +6 at `c0ae7f54` (five destination cases and the credential test) and +1 at `5ecc7de0` (the exit bounds), for 284 → 291.
- **agent_sdk/core:** +2 at `69a9b3a5`, for 1371 → 1373. The implementer reported 1373 passed and 1 skipped; that is reproduced.

---

## Mutation proofs — 21 mutants: 17 killed, 4 survived

The recipe for each:
1. Back up the file.
2. Apply the edit. It must match exactly one occurrence, or the run refuses.
3. Grep-confirm the edit landed.
4. Run the named tests under a fresh `PYTHONPYCACHEPREFIX`.
5. Restore the file from the backup.
6. md5 the file against its `f1100629` blob.

All 21 restores matched. R06–R08 and R15–R18 replay r1's survivors or strip the pins after construction. The rest are my own.

| id | file | mutation | tests run | result |
|---|---|---|---|---|
| R01 | `claude_cli_telemetry.py` | a non-empty header stays in the `--settings` JSON (`if False and any(…)`) | env + SAD | **killed** 1F — `test_a_credential_bearing_header_rides_in_the_env_only_never_on_the_argv` |
| R02 | same | ignore `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | env + SAD | **killed** 1F — `…go_where_this_process_own_logs_go[logs-specific-beats-generic-decoy]` |
| R03 | same | headers: logs-specific ignored | env + SAD + reaches_query | **SURVIVED**, 61 passed — P3-1 |
| R04 | same | headers: generic beats logs-specific | env + SAD + reaches_query | **SURVIVED**, 61 passed — P3-1 |
| R05 | same | `OTEL_RESOURCE_ATTRIBUTES` dropped from the settings carrier | env | **killed** 8F |
| R06 | `orchestrator.py` | `extra_args={"settings": "{}"}` on the one options call | env + reaches_query | **SURVIVED**, 20 passed — P2-2 |
| R07 | same | `query(…, options=dataclasses.replace(options, settings=None))` at the call site | env + reaches_query | **killed** 2F, by reaches_query only (the AST test passes it) |
| R08 | same | MT10 replay: `options = replace(options, env={}, settings=None)` after construction | env + reaches_query | **killed** 2F, by reaches_query only |
| R09 | `base.yaml` | the genai condition loses its parentheses (`A or B and C`) | 4 otel files | **killed** 1F — `test_the_genai_aliases_are_log_only…` |
| R10 | `backend-oss.yaml` | a second otlp-fed `metrics/extra` pipeline without the drop | 4 otel files | **killed** 1F — `test_collector_profiles.py::test_every_overlay_declares_the_complete_backend_half` |
| R11 | registry module | the CHECK becomes `content IS NOT NULL OR truncated` | registries/tables | **killed** 2F |
| R12 | owner SQL | read-back loosened to `LIKE '%content%'` | spill_retired | **killed** 1F (the exact pin) |
| R13 | `base.yaml` | cap 128 → 256 | 4 otel files | **SURVIVED**, 48 passed. By design: the test pins `70 <= cap <= 256`, not 128 |
| R14 | `backend-aws.yaml` | the metrics drop moved after `resourcedetection` | 4 otel files | **killed** 1F — `test_the_collector_drops_any_claude_code_metric…` |
| R15 | `orchestrator.py` | MT11 replay: `setattr(options, "settings", None)` | env + reaches_query | **killed** 2F, by reaches_query only |
| R16 | same | MT15 replay: a different `ClaudeAgentOptions` reaches `query()` | env + reaches_query | **killed** 3F (the AST test and both reaches_query cases) |
| R17 | owner SQL | MX08 replay: `IF false THEN <drop> END IF` | spill_retired | **killed** 1F (the exact pin) |
| R18 | `base.yaml` | MC04 replay: keep-list widened with `system_reminders` | 4 otel files | **killed** 1F — `test_the_keep_list_is_exactly_the_declared_set` |
| R19 | `base.yaml` | `error` re-admitted to the keep-list | 4 otel files | **killed** 3F |
| R20 | `claude_cli_telemetry.py` | shutdown bound 1000 → 5000 | env | **killed** 8F |
| R21 | `base.yaml` | the alias writes `cache_creation.input_tokens`, not the gateway's name | 4 otel files | **killed** 3F |

r1's survivors on the claims this range answers are all killed now: MT10 (R08), MT11 (R15), MT15 (R16), MX08 (R17) and MC04 (R18).

---

## What I tried to break and could not

- **Provider or exception text, by any channel.**
  - **Attributes.** The keep-list is exact (R18, R19) and holds no free-text key.
    - `category` (on `api_refusal`) is a closed set, and is additionally gated by `_g()`.
    - `source` and `decision_source` are the CLI's closed vocabulary (`Mtd` / `cIy`): `config`, `rule:<source>`, `hook:<name>`, `classifier:<name>`.
    - `model`, `request_id` and `query_source` are identifiers.
  - **The body** is constant.
  - **The resource** is the CLI's own plus the parent's `OTEL_RESOURCE_ATTRIBUTES`. That value is now pinned in the flag layer, so no settings file can add to it.
  - **Headers** come from the parent only.
  - **The argv** carries no header value (R01).
- **The class fields are bounded by the CLI, not only by us.**
  - `error_type = wRo(e)`. It is an `errorClass` matching `^[a-z][a-z0-9_]{2,59}$`, else `Error:` + `jp(e)`, else a name matching `^[A-Za-z]{4,60}$`, else `Error` / `UnknownError`. So it is at most 70 characters.
  - `error_code = jp(e)`: an `e.code` matching `^[A-Z][A-Z0-9_]{0,63}$`.
  - `error_name = q0t(e.name)`: `^[A-Z][a-zA-Z]*$`.
  - None of the three can hold an ARN, an account id (digits), a path or a prompt.
  - `mcp_server_connection.error_code` is a constant (`FIRST_PARTY_AUTH_REJECTED`, …).
- **Endpoint precedence.**
  - The CLI builds its logs exporter with no `url` (`EFo()`).
  - The bundled exporter reads `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` as-is, else the generic endpoint plus `/v1/logs`. So the flag-layer pin wins over every settings file.
  - The one route around it is not a settings file. It is a stored, pinned `enterpriseGateway` credential, which `AXi()` reads from secure storage and an interactive `/login` to a cloud gateway writes.
    - With that credential present, `EFo()` sets `url = <gateway>/v1/logs`.
    - It also adds `user.id`, `user.email` and `user.groups` to the RESOURCE.
  - The container has no such store. `CLAUDE_CODE_USE_GATEWAY` sets `unpinned: true`, which does not trigger the route. Recorded as CLI-R2-16.
- **`service.name=claude-code` really is set.**
  - `oYd()` merges `{service.name: "claude-code"}`, then os, then `host.arch`, then `envDetector`; the last one wins.
  - `envDetector` gives `OTEL_SERVICE_NAME` precedence over a `service.name` inside `OTEL_RESOURCE_ATTRIBUTES`.
  - Both carriers pin `OTEL_SERVICE_NAME`.
  - The collector's `resourcedetection` runs with `override: false`.
- **`(A or B) and C`.**
  - OTTL's grammar is: `booleanExpression := term ("or" term)*`, `term := booleanValue ("and" booleanValue)*`, and `booleanValue := "not"? (comparison | constExpr | "(" booleanExpression ")")`.
  - So `and` binds tighter than `or`, and parentheses group. The aliases condition is exactly "the CLI's record AND an `api_request`". The allowlist's bare `A or B` needs no parentheses.
  - R09 shows the pin catches the ungrouped spelling, which would have aliased `A or (B and C)`.
  - This is the first parenthesised condition in the tree. No real otelcol 0.160.0 has loaded it (OWED).
- **Adding the CHECK to existing rows.**
  - `llm_turn_content` and `llm_turn_content_storage_check` were created together (`54a01f39`). So every live row satisfies `(content IS NULL) <> (content_s3_key IS NULL)`.
  - No code ever set the key, so every row has `content`.
  - `converge_named_checks` adds the constraint with a validating `ADD CONSTRAINT … CHECK`, not `NOT VALID`. A violating row would fail the migration loudly rather than slip in.
- **Running the owner SQL without the CHECK.**
  - The precondition checks the name first, under the ACCESS EXCLUSIVE lock, which is taken before any read (`:103`) and bounded by `lock_timeout`.
  - The read-back then checks the name and the predicate.
  - Everything is one transaction, so a failing read-back rolls back the drop.
  - Only P3-2's substring and `convalidated` gap remains.
- **Metrics.**
  - The four `metrics` pipelines are the only otlp-fed metrics pipelines, and `test_collector_profiles.py` pins the pipeline set (R10).
  - `metrics/browser` is fed by `signaltometrics/browser`, and `content-phoenix` has only `traces/content`.
  - Every CLI meter instrument is named `claude_code.*`.
- **The exit bound.**
  - The SDK's `close()` sends stdin EOF, waits under `fail_after(5)`, then sends SIGTERM.
  - The CLI's exit takes at most the flush (a 1 s race) plus the shutdown (a 1 s race), which fits inside that grace.
- **Pins built per call, not frozen.**
  - Both runners call the builders when they construct the options.
  - The `OTEL_SDK_DISABLED` case in the `run_query` test would fail an import-time constant.

## What I did not test

- **A real otelcol 0.160.0 loading the four overlays.** That covers the parenthesised condition, `metric.name` in the filter processor's metric context, and `keep_matching_keys` / `truncate_all`. It is banned here, and is the implementer's OWED (2).
- **A real CLI run and a live Bedrock 403.** The record shape is read from the minified binary.
- **Commander's last-value rule for a repeated `--settings`.** It is read from the option declaration (no parser function), not executed.
- **The owner SQL against a database** (OWED), and every `tests/db` lane.
- **Whether a persisted test or dev database's conformance check** reports the new named CHECK as missing until the migration is re-run.
- **Lanes outside those listed:** `tests/agent_sdk` beyond `core`, `tests/architecture` and `tests/api`.

---

## Claims table

**Severity**, my own scale:
- 0 = a content or secret leak that ships;
- 1 = guard or lock integrity;
- 2 = a coverage or contract gap;
- 3 = docs or process;
- — = none.

**Tier**, per §2.3a:
- 0 = settled by a mutation-checked guard I saw red, on a mechanical or doc decision;
- 1 = consequential but reversible;
- 2 = irreversible or estate-shaping: the signal contract, content and privacy, schema.

A row's tier follows the decision it embodies. Its claim state follows its guard.

| # | Repo | File:line | Claim (decision taken) | r1 finding answered | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CLI-R2-01 | copilot-mro | `deployment/otel/base.yaml:164-172` | No free-text `error`/`error_message` leaves on ANY CLI event; neither key is in the keep-list | P1-1 / CLI-12 | Binary: `error` is written on `api_error`, `api_retries_exhausted`, `compaction`, `mcp_server_connection`, `tool_result` (the last only under `_g()`); `keep_matching_keys` deletes every unlisted key | `test_the_keep_list_is_exactly_the_declared_set` (`test_claude_code_log_allowlist.py:157`), `test_no_free_text_error_reaches_a_backend_only_its_category` (`:201`) | yes — R19 (`error` re-admitted) 3F | — | 2 | F1 | SETTLED |
| CLI-R2-02 | copilot-mro | `base.yaml:156-162`; `claude_cli_telemetry.py:4-6`; test `:201-222` | "A failure survives as its category: `status_code`, `attempt`, `error_type`/`error_name`/`error_code`" | P1-1 (controller call: keep a capped category) | Binary: `api_error`/`api_retries_exhausted` carry NO class field; `H = Cpo(e)` goes only to `tengu_api_error`; a Bedrock 403 exports `status_code=403` only; a no-status failure exports no category | the test's fixture puts class fields on `api_error`, which the CLI never does | n/a — the guard asserts a record shape the producer never emits | 2 | 2 | F1 | **OPEN** — P2-1 |
| CLI-R2-03 | copilot-mro | `base.yaml:172` | The class fields are bounded by the CLI's own regexes; every kept value is capped at 128 | P1-1 | `wRo` ≤ 70, `jp` ≤ 64 uppercase, `q0t` letters-only (unbounded length), `mcp_server_connection.error_code` constants | `test_every_kept_value_is_capped_short` (`:225`) | partly — the test pins `70 <= cap <= 256`; R13 (cap 256) SURVIVES by design | 3 | 2 | F1 | SETTLED as "≤ 256"; exact 128 ASSERTED; "~70" prose is P3-4 |
| CLI-R2-04 | copilot-mro | `base.yaml:171`; test `:48-62` | The keep-list equals a literal set; every alternative is a literal key | P2-3 / CLI-09 | The YAML regex is parsed, OTTL-unescaped and split | `:157` | yes — R18 (MC04 replay) 1F; R19 3F | — | 2 | F1 | SETTLED |
| CLI-R2-05 | copilot-mro | `base.yaml:112`, `:169` | Both conditions are `service.name == "claude-code"` OR the CLI scope; the aliases condition is `(…) and event.name == "api_request"` | P2-3 / CLI-10 | `oYd()` merge order; `envDetector` gives `OTEL_SERVICE_NAME` precedence; OTTL grammar grouping | `:140`, `:148`, `:173`, `:250` | yes, for the text — R09 (parentheses dropped) 1F | — | 2 | F1 | SETTLED (text); semantics ASSERTED (no otelcol) |
| CLI-R2-06 | copilot-mro | `orchestrator.py:2360-2409`, `:2889` | The options object that reaches `query()` carries the env and settings pins, built per call | P1-2 / CLI-06 | The real `run_query` is driven offline with `query` replaced by a recorder | `test_the_options_that_reach_query_carry_the_cli_telemetry_pins` (`reaches_query.py:90`) | yes — R07 2F, R08 (MT10) 2F, R15 (MT11) 2F, R16 (MT15) 3F; the AST test alone passes R07, R08 and R15 | — | 1 | F1 | SETTLED |
| CLI-R2-07 | copilot-mro | same; SDK `subprocess_cli.py:611` | …and therefore the CLI's flag layer carries the pins | P1-2 residual | `extra_args` puts a second `--settings` after ours (real `_build_command`, offline); commander keeps the last value | none on the argv | **R06 SURVIVES** (20 passed) | 1 | 1 | F1 | **OPEN** — P2-2 |
| CLI-R2-08 | copilot-mro | `claude_cli_telemetry.py:117-137` | The logs endpoint equals this process's own `OTLPLogExporter` endpoint, and it and the resource attributes are pinned in both carriers | P2-1 / CLI-08 | `EFo()` passes no `url`; the exporter reads `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` as-is | `test_the_cli_logs_go_where_this_process_own_logs_go` (5 cases, `:354`), `:272`, SAD `test_sad_agent_runner.py:209` | yes — R02 1F, R05 8F | — | 2 | F1 | SETTLED |
| CLI-R2-09 | copilot-mro | `claude_cli_telemetry.py:130-132` | Headers resolve logs-specific first, then generic, as the exporter does | P2-1 | read; correct today | `:354` (no case sets logs headers) | **R03 and R04 SURVIVE** | 2 | 1 | F1 | ASSERTED — P3-1 |
| CLI-R2-10 | copilot-mro | `claude_cli_telemetry.py:149-156` | A non-empty header never reaches the argv; otherwise the argv carries only non-secrets | P2-1 | The iac and compose values; the offline argv | `test_a_credential_bearing_header_rides_in_the_env_only_never_on_the_argv` (`:376`) | yes — R01 1F | — | 2 | F1 | SETTLED |
| CLI-R2-11 | copilot-mro | `claude_cli_telemetry.py:95-102` | The exit is bounded: flush, shutdown and each export request at 1000 ms, inside the SDK's 5 s grace | r1 "did not test: shutdown latency" | `iI_`/`oI_` `Promise.race`; SDK `close()` `fail_after(5)`; `hh_()` reads `LOGS_TIMEOUT` before the generic one | `test_the_exit_latency_bounds_are_names_the_cli_reads…` (`:257`), `:160` | yes — R20 8F | 3 | 1 | F1 | SETTLED (the bounds); the silent loss and the outranked request timeout are OPEN — P3-3 |
| CLI-R2-12 | copilot-mro | `base.yaml:214-218`; the four overlays' `metrics` pipelines | Any `claude_code.*` metric is dropped first in every otlp-fed metrics pipeline | P3-2 / CLI-16 | The pipeline set is fixed by the profile test | `test_cli_metrics_stay_off.py:89`; `test_collector_profiles.py:84` | yes — R14 1F, R10 1F | — | 1 | F1 | SETTLED (config); `metric.name` under otelcol ASSERTED |
| CLI-R2-13 | copilot-mro | `base.yaml:118-119` | The aliases write the gateway's `gen_ai.usage.cache_read.input_tokens` / `cache_write.input_tokens` | P3-7 / CLI-14 | `model_gateway.py:232-233` | `test_claude_code_log_allowlist.py:275`; `test_collector_base_config.py:174` | yes — R21 3F | — | 2 | F1 | SETTLED |
| CLI-R2-14 | copilot-mro | the test sessions | No test launched the CLI or otelcol; the docker launches were refused | CLI-18 | the netguard log | review-side guard | observed | — | 1 | F3 | SETTLED (observed) |
| CLI-R2-15 | copilot-mro | the CLI resource (`oYd()`) | `service.name=claude-code` wins; the resource carries only the CLI's own and the parent's attributes | P2-1 / P2-3 | read from the binary | `:148` pins only the module value | not mutable (vendor internals) | — | 2 | F1 | ASSERTED (read) |
| CLI-R2-16 | copilot-mro | the CLI's `EFo()` / `AXi()` | A stored, pinned `enterpriseGateway` credential reroutes the logs and adds `user.*` to the resource, past both carriers | P2-1 residual | read from the binary; no store in the image | none | not recordable | 3 | 2 | F1 | ASSERTED — latent |
| CLI-R2-17 | iac | `5f3380c` (in iac `HEAD` `9828e17`) | r1 P3-3: the iac board and the vocabulary test no longer name the retired series | CLI-17 | grep clean | iac's `test_cli_metrics_stay_off.py` (not run here) | not by me | — | 1 | F3 | ASSERTED |
| CAP-R2-01 | copilot-mro | `llm_turn_content.py:140` | A named `CHECK (content IS NOT NULL)` is declared, and `converge_named_checks` adds it with validation | P2-2 / CAP-02 | The table and the either/or CHECK were created together (`54a01f39`); `migrate_tenancy_schema.py:2797-2829` | `test_llm_turn_content_spill_retired.py:62`, `:169` | yes — R11 2F | — | 2 | F1 | SETTLED |
| CAP-R2-02 | copilot-mro | `drop_llm_turn_content_spill.sql:97-178` | ACCESS EXCLUSIVE taken first; refuses without the CHECK; the text is pinned exactly | P3-4 / CAP-08, CAP-09 | read | `:279` (`EXPECTED_DROP_SQL` `:240`) | yes — R12 1F, R17 (MX08) 1F | — | 2 | F1 | SETTLED (text); execution OWED |
| CAP-R2-03 | copilot-mro | the SQL `:109-120`, `:168-176`; `migrate_tenancy_schema.py:2812-2814` | The read-back is a `LIKE` substring with no `convalidated`, and converge skips by name | P3-4 residual | read | the exact pin locks the weak predicate in | n/a | 2 | 2 | F1 | **OPEN** — P3-2 |
| CAP-R2-04 | copilot-mro | plan `:979-980`; the SQL `:33-38` | "ORDER IS ENFORCED: code → migration → SQL" | P3-4 | The SQL can detect only the CHECK | none | n/a | 3 | 1 | F3 | **OPEN** — P3-4 |
| DOC-R2-01 | copilot-mro | env test `:17-20`; spill test `:17-26`; `claude_cli_telemetry.py:4-6`; `base.yaml:160-162`; allowlist test `:226` | Stale or over-claiming prose | new | read | none | n/a | 3 | 0 | F3 | **OPEN** — P3-4 |
| DOC-R2-02 | copilot-mro | scope guard `:335-337`; `docs/plans/s4-browser-on-lang-slice.md:363` | r1 P3-1 and P3-8 corrected | P3-1 / CAP-11, P3-8 / DOC-01 | grep | none | n/a | — | 0 | F3 | ASSERTED (closed by reading) |
| MRG-R2-01 | copilot-mro | `test_phase1c_nonagent_scope_guard.py:328-384` | Merging into obs-merge `6145d42a` and `ac7cda74` gives one conflict each, resolved by union; the board and catalogue auto-merge soundly | P3-5 / MRG-01 | scratch merges `1c14ae44`, `8a5ca240`; the merged lanes | the merged lanes | not recorded | — | 1 | F2 | ASSERTED (measured) |
| MRG-R2-02 | copilot-mro | range `7416d7a4..f1100629` | Every commit is green at its own SHA on the lanes it touches | MRG-02 | the per-SHA table; red sets identical by test id | the lanes | n/a | — | 1 | F2 | ASSERTED (measured) |
| MRG-R2-03 | copilot-mro | `a18635e9..f1100629` | Land as one unit | P3-6 / MRG-03 | recorded in the plan (`:984`) | none | n/a | 3 | 1 | F2 | ASSERTED (recorded) |

---

## Open claims, tier 2 first

**Tier 2 — open**

1. **CLI-R2-02 (P2-1).** `api_error` and `api_retries_exhausted` carry no class field, so a failure with no HTTP status has no category, while four texts and a test fixture say one survives.
   - The controller decides: accept `status_code` only (correct the texts and the fixture), or derive a closed `error_kind` at the collector.
2. **CAP-R2-03 (P3-2).** The owner SQL reads the content CHECK back by substring and without `convalidated`, and `converge_named_checks` skips by name.
   - Use equality against `CHECK ((content IS NOT NULL))` `AND convalidated` in both the precondition and the read-back, then update the pin.

**Tier 1 — open**

3. **CLI-R2-07 (P2-2).** The P1-2 guard pins the options object, not the argv, and `extra_args` can add a second `--settings` (R06).
   - Assert on the real `_build_command()`: exactly one `--settings` equal to the pins, and no `--managed-settings`.
4. **CLI-R2-09 (P3-1).** The logs-specific header precedence is unproved (R03, R04).
   - Add one destination case with both header variables set.
5. **CLI-R2-11 (P3-3).** The exit-bound loss is unobservable and missing from the plan note, and `OTEL_EXPORTER_OTLP_LOGS_TIMEOUT` outranks the pinned generic timeout.
6. **CAP-R2-04 (P3-4).** "ORDER IS ENFORCED: code → migration → SQL" overclaims; only migration → SQL is enforced.

**Tier 0 — open (docs)**

7. **DOC-R2-01 (P3-4).** Stale prose: the env test's point 4, the spill test's point 3, the "~70 chars" docstring, and P2-1's texts.

**Counts: 26 claims.**
- 13 SETTLED (one of them observed, not mutated), several of them with a narrower sub-claim ASSERTED.
- 8 ASSERTED.
- 5 OPEN.
- Tier 0: DOC-R2-01 is open and DOC-R2-02 is closed by reading.

**Mutants: 21 valid runs — 17 killed, 4 survived.**
- The survivors are R03, R04, R06 and R13.
- R13 is not a finding: the test deliberately pins a range.
- R03 and R04 are P3-1; R06 is P2-2.
