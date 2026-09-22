# Claims packet — copilot-mro `obs-merge-cli` review r1 (M-CLI-TELEMETRY + M-CAPTURE-TRUNCATE)

Independent adversarial review, Opus, 2026-09-21. **Verdict: FIX-FIRST** — 0 P0 · 2 P1 · 3 P2 · 8 P3.

Read-only on every code tree. Nothing was edited, committed, checked out or stashed in
`copilot-mro-obsm-cli` or any sibling, and nothing was pushed. No DB, DDL/DML, docker, otelcol, AWS,
Bedrock or Claude CLI call was made. Every run and every mutation used private scratch copies under
`scratchpad/mro-cli-review/`: `git archive` copies per commit (`t/<sha>/`), a mutation copy of HEAD
(`t/mutws/`), a scratch clone for the git-reading guards (`wsc/`, origin removed), and a scratch clone
where `7416d7a4` was merged into `obs-merge` `245e4d47` (`wsm/`). There were 49 mutation runs: 47 valid and
2 superseded.
- MC13 collected only the three named files, because pytest de-duplicated the directory argument. It
  was rerun on the whole lane as MC13b.
- MX04 set a field key the registry ignores. It was rerun through `not_null_fields` as MX04b.

Every mutated file was restored from a scratch backup and md5-checked against its `7416d7a4` blob.
All 49 restores matched, and a final sweep of all 16 touched files matched HEAD.

At the end of the review, `copilot-mro-obsm-cli` was still at `7416d7a4` with a clean status. Other
trees moved during the review, and none of those moves came from it:
- `api-obsm` went from `847c34c` to `d93f75e`.
- `dashboard-obsm` went from `09bacba` to `2a9b0f4`.
- `iac` went from `013dc89` to `97cae73`.
- `telegram-bot` gained uncommitted edits: `flynapse_client/errors.py` and an untracked
  `tests/unit/sdk/test_unchained_raise.py`.

These are other lanes' work. My lanes never ran their suites and wrote no source files. Because
`api` and `dashboard` were symlinked to those live checkouts, cross-repo reads in my lanes saw a
moving target. The only red that touches them (the browser contract) is also red at the base.

| repo | worktree | branch | range | siblings (archives) |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm-cli` | `obs-merge-cli` | `6aef26e3..7416d7a4` (9 commits) | utils-obsm `594327e`, core-obsm `dc41caa`, flynapse-otel `927a729`; api/dashboard/docs → their `-obsm` checkouts, the rest → the primary checkouts (symlinks, read-only) |

The lane recipe, as run:
- The command: `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider --rootdir=<copy> -m "not db" tests/<lane>`, run from the copy's root.
- The environment: `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`, with `PYTHONPATH=<netguard>:<copy>:<utils>:<core>:<flynapse-otel>`.
- A fresh `PYTHONPYCACHEPREFIX` for every run, and pytest's own exit status recorded, never a pipe's.
- `rootdir` was the scratch copy in every run. `copilot_mro.app.__file__` was `<copy>/copilot_mro/app/__init__.py` in every run.

The guard is a `sitecustomize`. It refused:
- every non-loopback connect;
- every loopback connect below port 20000, which covers every real service port;
- any launch of `claude`, `_bundled/claude`, `docker` or `otelcol`.

It logged each refusal and each subprocess launch, together with the test id.

**The Claude CLI was never launched by any test.** This covers every lane and every mutant. The only
executables launched were `git`, the venv python (test children), `bash -c exit 0` and `uname`. Twenty
`docker` launches, from the pre-existing compose and grafana tests in `tests/integration/otel`, were
refused. `test_the_installed_sdk_hands_these_pins_to_the_cli…` drives the real
`SubprocessCLITransport.connect` with `open_process` replaced. It sets
`CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1` and `cli_path="/nonexistent/claude"`, so even the SDK's
`claude -v` probe cannot reach the binary. The two binary-reading guards only mmap the file.

**Method for the CLI claims.** I read the bundled Claude Code 2.1.220 binary
(`claude_agent_sdk/_bundled/claude`) by byte offset:
- the event emitter `Ac()` (@250665534) and its 27 events: 25 literal names, plus `api_request_body` / `api_response_body`, which are emitted through a variable;
- `api_error`'s message builder `u$y` (@254583420);
- the settings-env application `l9()`/`Lut()` (@252854598) and its source order;
- the telemetry init `oI_` (@258555943);
- the flag readers `_g()`, `lrr()`, `yes()`, `Yt()` and `SFo()`.

All byte offsets are in that file.

---

## Findings, ranked

### No P0

The strongest attack was to ask, for every event, what leaves the process with every content flag off. With
the pins as built, the only conversation content the CLI could write is gated by a flag this change pins to
an explicit false:
- `user_prompt.prompt` and `assistant_response.response` are `"<REDACTED>"`.
- `tool_decision.tool_parameters` carries only `mcp_server_name` / `mcp_tool_name` for SDK-host MCP tools
  (`M8r` returns early when `_g()`, which is `OTEL_LOG_TOOL_DETAILS`, is false).
- `tool_result.error` is written only under `_g()`.
- `tool_input` is written only under `OTEL_LOG_TOOL_CONTENT`.
- `system_prompt` and `tool` need both beta tracing and `OTEL_LOG_USER_PROMPTS`.
- The raw bodies need `OTEL_LOG_RAW_API_BODIES` truthy or `file:`.

The collector allow-list then drops every one of those keys anyway. I found no path by which prompt,
response or tool text reaches the logs pipeline. The one free-text survivor is P1-1.

---

### P1-1 — `api_error.error` ships the provider's raw error text to every logs backend, and a test pins it in

**Where.**
- The pin: `deployment/otel/base.yaml:165`.
- The test that locks it in: `tests/integration/otel/test_claude_code_log_allowlist.py:155-174`.
- The ruling as implemented: `975890e6`.

**What happens.** The CLI builds the `error` field as `u$y(e)`: the provider's
`e.error?.error?.message`, or else `Error.message`. It emits it on every `api_error` and
`api_retries_exhausted` event, and no `OTEL_LOG_*` flag gates it. The allow-list keeps it on exactly
those two events, capped at 1024 characters, and `redaction` masks emails, AKIA ids, bearer tokens
and JWTs, not ARNs or account ids. The Bedrock error body is `{"message": …}` with no nested
`error.error`, so the field becomes the bundled SDK's `APIError.makeMessage` output,
`` `${status} ${body.message}` `` (confirmed in the binary).

**The failure scenario.** The Bedrock role loses `bedrock:InvokeModelWithResponseStream` on the
`global.*` inference profile. Every attempt then exports an `api_error` whose `error` field is
`403 User: arn:aws:sts::<account>:assumed-role/<role>/<session> is not authorized to perform: bedrock:InvokeModelWithResponseStream on resource: arn:aws:bedrock:ap-south-1:<account>:inference-profile/global.anthropic.…`
The record reaches Loki, CloudWatch, Azure Monitor or New Relic.

That is the exact datum G.7(a) documents `utils/observability/failure.py` as built never to read
("`response["Error"]["Message"]`, the field that carries the ARN, is never read"). The estate's
export-seat withholding does not cover this channel:
- flynapse-otel's `WithholdingLogRecordProcessor`, and the G.110/G.112 work, sit in Python processes;
  the CLI is a Node binary.
- The collector is the only seat, and it was configured to keep the text.

**Where the evidence stops.** I did not observe a live 403 (no AWS calls). The message shape is
AWS's standard AccessDenied text, and the plumbing is read from the binary. I also looked for prompt
content in this field and could not reach any. The one bundled-SDK error that embeds model output,
`Unable to parse tool parameter JSON from model … JSON: ${buf}` (@247277114), lives in `MessageStream`.
The CLI's main loop does not use `MessageStream`: it concatenates `partial_json` itself (@258981578).

**The decision.** This is an owner ruling to take, not a mechanical fix. "Per-call errors" can be met
without the text: `status_code`, `attempt` and `model` survive, and a closed error category could be
derived at the collector. The options:
- (a) Drop `error` on every CLI event.
- (b) Keep it and record the ARN exposure as accepted.
- (c) Reduce it to a category.

Until one of these is ruled, the test asserts the leaky behaviour, which is the RV4 "test asserts the
defect" shape.

### P1-2 — The orchestrator half of the env guard is shape-only, and three rewrites that strip the pins pass it

**Where.** `tests/unit/agent_claude/test_claude_cli_telemetry_env.py:281-340`, which guards
`copilot_mro/app/services/agent_claude/orchestrator.py:2360-2409`.

**What the test does.** It parses the orchestrator and asserts four things:
- there is one `ClaudeAgentOptions(` call;
- that call has `env=claude_cli_telemetry_env()` and `settings=claude_cli_telemetry_settings()`;
- neither builder name is shadowed;
- no `options.env` / `options.settings` attribute node appears after construction.

Its docstring says nothing can touch the pins after construction, but each of these mutants left all
52 tests green:

| mutant | change | result |
|---|---|---|
| MT10 | `options = dataclasses.replace(options, env={}, settings=None)` after construction | 52 passed |
| MT11 | `setattr(options, "settings", None)` after construction | 52 passed |
| MT15 | `query(prompt=prompt, options=claude_agent_sdk.ClaudeAgentOptions(model=…, mcp_servers=…))` — the pinned object is never used | 56 passed (with `test_agent_sdk_orchestrator_tenancy_wiring.py`) |

The controls were killed:
- MT08, dropping `settings=`: 1 failed.
- MT09, splatting a content flag into `env=`: 1 failed.

The SAD runner's half is behavioural and holds (MT12, MT13 and MT14 all killed). Only the
orchestrator's half, the seat every `/rag` turn uses, is proved by shape.

**The fix.** Pin what reaches `query()`. Either monkeypatch `orchestrator.query` and drive `run_query`
through the existing agent_sdk fakes, or at minimum assert that `query(...)`'s `options=` is the name
bound by the one constructor, and that that name is never rebound.

### P2-1 — The endpoint is not pinned, so a settings file can redirect the logs this change turns on, past the collector allow-list

**Where.**
- `copilot_mro/app/services/claude_cli_telemetry.py:32-37`, which says the endpoint is "inherited…
  the config the rest of copilot-mro uses".
- The docstring at `:24-30`.

**What the CLI does.** `l9()` (@252854598) applies `env` from these sources, each later one
overwriting the earlier ones:
1. the global config (`~/.claude.json`);
2. user settings;
3. project settings;
4. local settings;
5. flag settings (`--settings`);
6. policy settings.

`wT()` always adds the flag and policy sources. Project and local settings are barred from only three
keys (`Zmy`), none of them `OTEL_*`.

**What that means.** The flag layer wins for the keys it pins, but it pins no endpoint. So any settings
file the CLI loads can set `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` /
`OTEL_EXPORTER_OTLP_HEADERS`:
- the SAD runner loads user, project and local settings;
- the orchestrator loads project settings;
- both load the global config.

The per-call records, which this change switches ON (`CLAUDE_CODE_ENABLE_TELEMETRY=1`), then go there
instead of to our collector. That bypasses `transform/claude_code_allowlist`, and with it:
- its drop of `user.id` / `user.email` / `organization.id`;
- its `error` scoping.

An inherited signal-specific `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` in the parent does the same, because
it outranks the generic variable the app itself reads. `OTEL_RESOURCE_ATTRIBUTES` from a settings file
lands on the RESOURCE, which the allow-list never prunes.

**The failure scenario.** A developer keeps the documented Claude Code monitoring snippet (a vendor
`OTEL_EXPORTER_OTLP_ENDPOINT` plus auth headers) in `~/.claude/settings.json`. Every SAD agent's
per-call records then go to the vendor, not the estate collector.

**How much it matters today.** Content stays off, so this is metadata plus P1-1's error text. No
settings file on this box names an OTLP key: I checked `~/.claude/settings.json`, `~/.claude.json`,
the workspace `.claude/settings{,.local}.json`, and api/copilot-mro(-obsm)/`.claude`. The image
ships none. So this is latent.

**The fix.** Resolve the process's own endpoint at call time and pin
`OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` in both carriers (the endpoint is not a secret, unlike headers, so
the `--settings` argv is fine). Then correct the docstring.

### P2-2 — Retiring the either/or CHECK removes the database's only guarantee that `content` is set; a named CHECK would have kept it

**Where.**
- `copilot_mro/app/db/postgres_table_definitions_modules/llm_turn_content.py:59-65`.
- The docstring at `:1-14`.
- `scripts/drop_llm_turn_content_spill.sql:18-21`.

**What changed.** `(content IS NULL) <> (content_s3_key IS NULL)`, with the key always NULL, is what
forced `content` NOT NULL on every live table. After the owner's DROP, nothing in the database forbids
a content-less row. "The writer always sets it" is an application-side claim.

The implementer rejected a NOT NULL declaration because the migration never tightens a pre-existing
column. That is correct, and MX04b shows the suite would catch the divergence. But
`scripts/migrate_tenancy_schema.py:2797-2829` (`converge_named_checks`) DOES add a declared named
CHECK that is missing on a live table. So declaring `("llm_turn_content_content_present_check",
"content IS NOT NULL")` would carry the invariant across the drop, with no conformance divergence and
no extra step in the owner-run SQL.

This is tier 2 (schema). It is cheap now, and a migration-plus-backfill question once NULL rows exist.

### P2-3 — The allow-list's keep-pattern is not pinned by equality, and it fails closed only while the scope string matches

**Where.** `deployment/otel/base.yaml:157-166`, and
`tests/integration/otel/test_claude_code_log_allowlist.py:37-60`, `:147-152`.

**What the test checks.** Two things:
- `KEPT ⊆ pattern`;
- `DROPPED ∩ pattern = ∅`, where DROPPED is a 26-key witness list.

Widening the pattern with a key that is not a witness passes. Each of these mutants left all 23 tests
green:
- MC04 adds `system_reminders`;
- MC05 adds `description|full_command_preview`.

MC01, MC02 and MC03 (`prompt`, `tool_parameters`, `user.email`) were killed.

**The scope condition.** The condition is exact and is witnessed against the binary: MC06 was killed,
and `getLogger("com.anthropic.claude_code.events"` is the only scope the CLI uses, at 3 sites. But a
future CLI that renames the scope turns the processor into a no-op on every CLI record. That is
fail-OPEN, the opposite of the docstring's "fails CLOSED". The binary witness would catch it only on
an SDK bump in this lane, and only if the old string also disappears.

**The fix.** Pin the keep-pattern by literal equality, as the env test does for the env, and key the
condition on `resource.attributes["service.name"] == "claude-code"` (which this change pins) OR the
scope.

---

### P3-1 — Stale "content NOT NULL" prose survived `5333e3cf`

- `tests/unit/observability/test_phase1c_nonagent_scope_guard.py:335` says "(column + both CHECKs,
  `content` NOT NULL)".
- `tests/registries/tables/test_llm_turn_content_spill_retired.py:222`, a docstring, says "the NOT NULL
  the registry now declares". The test body directly below asserts `"SET NOT NULL" not in sql`.

Both are left over from the first cut (`4c02a10e`), which declared NOT NULL; `5333e3cf` reversed it.

### P3-2 — `test_cli_metrics_stay_off.py` is named for a property it does not test; metrics-off rests on the env pin alone

**What the file proves.** No board, rule, catalogue row or inventory entry reads `claude_code_*`. The
dotted form, the quoted form and a rule are all caught: MM1, MM2 and MM3 were killed.

**What it does not prove.** Nothing proves the CLI's metrics stay off. Nothing on the collector drops a
`claude_code.*` metric either, and the metric half of `genai_aliases` is gone. So if a managed policy
or a future CLI default emits them, they flow through `attributes/metric_cardinality` to every metrics
backend unlabelled, and they duplicate the ledger again.

**What to do.** Either add a `filter` on the four metrics pipelines, or rename the test and record that
the env pin is the only line.

The replacement is documented only as prose (`CATALOGUE.md:178-182`). There is no LogQL example and no
panel.

### P3-3 — The iac half still names the retired series (owed, re-stated OPEN)

These are re-stated from the implementer's own OWED list:
- `iac/dashboards/llm-agents.json.tftpl:7` still documents `{"claude_code.token.usage"}` /
  `{"claude_code.cost.usage"}` as "DARK until a producer…". That is false twice now: there is a
  producer, and it is log-only.
- `iac/tests/unit/observability/test_validate_metric_vocabulary.py:100-101` still lists both.

### P3-4 — The DROP's shape test cannot see a drop that does nothing, and the refusal and the drop are not under one lock

**The shape test.** MX08 wrapped the `ALTER` in `IF false THEN … END IF`, and all 43 tests passed. This
is the implementer's own "execute it against a scratch DB" OWED item, re-stated.

**The lock.** Separately, the refusal's `count(*)` runs under ACCESS SHARE, and the `ALTER` then
upgrades to ACCESS EXCLUSIVE. A concurrent INSERT between the two cannot carry a key today, because no
code writes the key. A `LOCK TABLE public.llm_turn_content IN ACCESS EXCLUSIVE MODE` before the count
would make the refusal and the drop atomic.

### P3-5 — The merge into `obs-merge` conflicts in the scope guard (resolved in scratch; the merged tree runs green-equivalent)

Merging `7416d7a4` into `obs-merge` `245e4d47` conflicts textually in
`tests/unit/observability/test_phase1c_nonagent_scope_guard.py`: both sides append to
`MRO_POST_MERGE_PRODUCTION_PATHS`.

I resolved it as the union in a scratch clone. The merged lanes then ran:

| lane | result |
|---|---|
| observability | 489 passed |
| agent_claude | 284 |
| data_discovery | 368 |
| registries/tables | 81 |
| agent_shared | 1162 |
| otel | 173 passed, with the same 12 environmental reds as the cli HEAD |
| unit/db | 341 passed, with the same 1 red |

`obs-merge`'s narrowing of the seed approval to paid-down files (`_paid_seeded_paths`, r6 P3-7) does
not bite, because every production file this range changes is approved by an explicit entry.

**Process.** Resolve by union, and commit the resolution alone (lesson: a merge commit carries the
conflict resolution only).

### P3-6 — `a18635e9` on its own is weaker than its base; land the range as a unit

`a18635e9` switches CLI telemetry ON with a single carrier (`options.env`) and no collector allow-list:
- the allow-list arrives in `4de21777`;
- the `--settings` carrier arrives in `a32fd6fc`.

At `a18635e9` alone, a settings file that sets only `OTEL_LOG_USER_PROMPTS=1` would export prompts
through a pipeline that keeps them. At the base, nothing turned the CLI's telemetry on.

Every commit is green, so a bisect is safe. A cherry-pick of the first commit is not.

### P3-7 — The alias fix makes a dead enrichment live, with a vocabulary that differs from the app's own

`transform/genai_aliases` now fires on CLI `api_request` records (`base.yaml:105-118`). It writes
`gen_ai.usage.cache_read_input_tokens` / `…cache_creation_input_tokens`. The app's gateway writes
`gen_ai.usage.cache_read.input_tokens` / `…cache_write.input_tokens`
(`copilot_mro/app/services/agent_shared/model_gateway.py:232-233`).

Nothing reads either on the logs pipe today. Converge the names before anything does.

### P3-8 — A plan doc's statement about the Claude CLI spawn env is now false

`copilot-mro/docs/plans/s4-browser-on-lang-slice.md:363` says the SDK spawns the CLI with
`os.environ` plus `ClaudeAgentOptions.env`, "which the orchestrator leaves unset". That is no longer
true:
- the orchestrator sets `options.env`;
- the CLI's stdio spawn of the `playwright` MCP server inherits the pins;
- the register's A41 "(v)" asymmetry gains `OTEL_*` / `CLAUDE_CODE_ENABLE_TELEMETRY` on the Claude side.

The Node server reads none of them, so this is prose only (the "grep the docstring family" lesson).

---

## Lanes — every commit at its own SHA

Each commit was checked out, detached, in the private scratch clone (`wsc/`), because the scope guard,
the debt-register ratchet and the cross-repo tests read git. The lanes it touches were run one directory
at a time. `rootdir` was the clone in every run, and the clone was clean before each checkout.
`agent_sdk/core` ran in the `git archive` copies. Counts are pytest's own.

| commit | lanes | reds |
|---|---|---|
| `6aef26e3` (base) | observability 479 (+1 skip) · agent_claude 273 · infra 128 +3F · agent_shared 1159 · otel 164 +3F +9E · unit/db 341 +1F · data_discovery 363 · registries/tables 77 · agent_sdk/core 1371 | env (below) |
| `a18635e9` | observability 479 · agent_claude 282 · data_discovery 368 | none |
| `cb5d309d` | observability 479 · otel 167 +3F +9E | env, same id set as base |
| `4de21777` | observability 479 · otel 172 +3F +9E | env, same id set |
| `4c02a10e` | observability 479 · registries/tables 81 · agent_shared 1160 · unit/db 341 +1F · infra 128 +3F | env, same id sets |
| `258a5d64` | registries/tables 81 | none |
| `5333e3cf` | observability 479 · registries/tables 81 | none |
| `a32fd6fc` | observability 479 · agent_claude 284 · data_discovery 368 | none |
| `975890e6` | otel 173 +3F +9E | env, same id set |
| `7416d7a4` | observability 479 · agent_claude 284 · infra 128 +3F · agent_shared 1160 · otel 173 +3F +9E · unit/db 341 +1F · data_discovery 368 · registries/tables 81 · agent_sdk/core 1371 | env, same id sets |
| merged `245e4d47`+`7416d7a4` (scratch, union resolution) | observability 489 · agent_claude 284 · data_discovery 368 · otel 173 +3F +9E · registries/tables 81 · agent_shared 1162 · unit/db 341 +1F | env, same id sets as the cli HEAD |

**The environmental reds.** Each was diffed by test id against the base, and they are identical at
every commit that ran the lane.
- **otel: 3 failures and 9 errors.**
  - 10 tests stop on a `docker` launch the review guard refuses: 6 compose-sample tests, 2 grafana
    running-stack tests and 2 smoke network-scoping tests.
  - 2 `test_browser_derived_metrics.py` tests (1 error, 1 failure) read a
    `dashboard/contracts/browser-signals.json` that the scratch workspace's dashboard sibling lacks.
- **unit/db: 1 failure.** `test_every_documented_invocation_names_a_database…` names three lines
  outside this range: `test_sad_environment_failures_withhold_secrets.py:532`,
  `scripts/e2e/figure_arc_headless_e2e.py:32` and `scripts/inspect_llm_turn_content.py:9`.
- **infra: 3 failures.** The `test_cross_repo_reads_name_their_checkout.py` tests assert the real
  workspace's `-obsm` variants, and the scratch workspace has none.

**The deltas match the new tests exactly:**
- agent_claude: +9 at `a18635e9`, and +2 at `a32fd6fc`.
- otel: +3 at `cb5d309d`, +5 at `4de21777` and +1 at `975890e6`.
- agent_shared: +1 at `4c02a10e`.
- data_discovery: +5 at `a18635e9`.
- registries/tables: +4 at `4c02a10e`.

The archive copies at HEAD show 3 more agent_claude reds (a `git show` at run time), 1 more
agent_shared red (a register-history read) and a collection error in observability (a `git ls-files`
at import). All of these are artefacts of a git-less copy, and all are green in the clone.

---

## What I tried to break and could not

- **The content flags.** I read every one of the 27 `Ac()` events. With the six pins the CLI
  writes no prompt, response, tool input, tool output, system prompt or body. Each gate was checked
  against its reader:
  - `lrr()` / `K1g()` read `OTEL_LOG_USER_PROMPTS`.
  - `olu()` is `OTEL_LOG_ASSISTANT_RESPONSES ?? OTEL_LOG_USER_PROMPTS`, a triBool, so `"0"` does not
    fall through. MT07 (an empty string) was killed.
  - `_g()` reads `OTEL_LOG_TOOL_DETAILS` and `Per()` reads `OTEL_LOG_TOOL_CONTENT`.
  - `Lud()` reads `process.env.OTEL_LOG_RAW_API_BODIES` through `Yt`: `"0"` means disabled.
  - `qP()` needs `ENABLE_BETA_TRACING_DETAILED && BETA_TRACING_ENDPOINT`.
- **Traces.** `yes()` is `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA ?? ENABLE_ENHANCED_TELEMETRY_BETA`, on
  the raw string, so `"0"` shadows an inherited `ENABLE_…=1`. `OTEL_TRACES_EXPORTER=none` then
  installs no exporter, and beta tracing's own provider needs `qP()`.
- **Metrics.** `SFo()` filters `none`, so the CLI builds no metric reader. The pin is killed by MT03.
- **Settings precedence.** The source list is `V$ = [user, project, local, flag, policy]`, and `wT()`
  always adds flag and policy. Plugins' `settings` are not an env source. So only policy outranks the
  pins, and there is no managed policy on the box, in `/etc/claude-code`, or in the image (the
  `Dockerfile` names none).
- **Settings-file carriers.** None exists today, measured on this box. `copilot-mro` tracks only
  `.claude/skills`.
- **Child processes.** The only CLI child is the optional `playwright` MCP server (`bash -lc … npx
  @playwright/mcp`), a Node process with no OTel. The SDK MCP servers and hooks are in-process.
- **Baggage.** flynapse-otel pins `OTEL_PROPAGATORS=tracecontext` (`bootstrap.py:77-79`), so the
  SDK's `propagate.inject` hands the CLI `TRACEPARENT`/`TRACESTATE` only, never `BAGGAGE`.
- **`OTEL_SDK_DISABLED`.** It is parsed exactly as `flynapse_otel.bootstrap:191` parses it. MT06 was
  killed.
- **The collector wiring.**
  - The allow-list is on all four `logs` pipelines, first after `resourcedetection`. MC11 and MC12 were
    killed.
  - A second otlp-fed logs pipeline without it (MC13) was killed, by
    `test_collector_profiles.py::test_every_overlay_declares_the_complete_backend_half`.
  - `logs/browser` receives only `otlp/browser`.
  - `content-phoenix` carries only `traces/content`, and the CLI exports no traces.
  - The alias condition and its log-only placement were killed by MC14 and MC15.
- **The DROP SQL.**
  - `row_security = off` makes an RLS-filtered count raise instead of reading zero.
  - `search_path` is pinned to `pg_catalog, pg_temp`, with every relation `public.`-qualified.
  - A second run finds no column, drops nothing, and still reads back.
  - The script runs in one transaction; without `ON_ERROR_STOP`, an error aborts it and `COMMIT`
    becomes a rollback.
  - The refusal comes before the drop, and the read-back is by predicate. There is no `CASCADE`, so a
    dependent view or policy would abort the run safely.
  - MX05, MX06, MX07 and MX10 were all killed.
- **Code first, then the SQL.**
  - The new writer's INSERT omits the column, so the old CHECK still holds (content is set).
  - The purge no longer RETURNs the column.
  - `fetch_row`'s `SELECT *` feeds `summarize_row`, which reads by `.get`.
  - The migration notes the column "left in place" and writes nothing. MX13, a migration that drops
    undeclared columns, was killed.
- **No reference remains.** No other tree names `content_s3_key`: I searched core-obsm, utils-obsm,
  api-obsm, dashboard-obsm, iac, flynapse-otel, telegram-bot, shift-optimizer and lambdas. In this
  repo only the registry docstring, the owner SQL and tests name it. MX01, MX02 and MX09 were killed.
- **Truncation.** The 262 144-byte default is pinned (MX03 killed), a >256 KB turn stays inline and
  flagged (MX12b killed), and `truncated … NOT NULL` is pinned (MX11 killed).

## What I did not test

- The OTTL in a real otelcol 0.160.0: `keep_matching_keys` / `delete_matching_keys … where` /
  `truncate_all` in the `log` context. This is banned here and is the implementer's OWED (2). The
  Python model is only a model.
- A real CLI run. The record shape is read from the minified binary, not observed.
- A live Bedrock AccessDenied through the CLI, for P1-1's exact text.
- Executing the DROP SQL (OWED, P3-4), and every `tests/db` lane (`-m "not db"` everywhere).
- **Per-call shutdown latency.** Each SDK call's CLI now builds an OTLP log exporter and flushes it on
  exit, bounded by `CLAUDE_CODE_OTEL_SHUTDOWN_TIMEOUT_MS` (2 s default). Against a slow or blackholed
  endpoint, that is added to every turn's stream close. It is unmeasured.
- Whether CLI records actually parent under our trace. `X1g()` honours `TRACEPARENT` when
  non-interactive, but that needs an active span at `connect()`, which I did not trace.
- Remote managed settings (an OAuth org feature, not reachable on Bedrock).
- Lanes outside those listed in the table above: the whole of `tests/agent_sdk` beyond `core`,
  `tests/architecture`, and `tests/api`.

---

## Claims table

Severity: 0 content leak that ships · 1 guard or lock integrity · 2 coverage gap · 3 docs/process ·
— none. Tier per §2.3a (0 = mechanical/additive/doc, proved by a guard seen to fail).

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CLI-01 | copilot-mro | `copilot_mro/app/services/claude_cli_telemetry.py:61-97` | One env for every SDK call: CLI logs on (otlp, http/protobuf, 1 s batch), metrics `none`, traces `none`, enhanced beta `0`, `OTEL_SERVICE_NAME=claude-code`, six content flags `"0"` | B9 per-call detail only | Read against the binary: `SFo` drops `none`; `Yt` true only for 1/true/yes/on; `olu` triBool fallback; `yes()` `??` | `test_the_env_is_per_call_logs_only_pinned_by_equality` (:129) | yes — MT01 drop prompts flag 9F · MT02 tool details `1` 8F · MT03 metrics `otlp` 8F · MT04 drop beta-detailed 8F · MT07 assistant `""` 8F | — | 2 | F1 | SETTLED |
| CLI-02 | copilot-mro | `tests/unit/agent_claude/test_claude_cli_telemetry_env.py:183-214` | The content-flag family is re-derived from the bundled binary (`OTEL_LOG_*`) plus two named beta gates | A CLI upgrade that adds a flag fails instead of shipping it unset | Binary lists exactly the five `OTEL_LOG_*` flags; beta gates named; `BETA_TRACING_ENDPOINT` unpinned but inert while `ENABLE_BETA_TRACING_DETAILED=0` | same | yes — MT01, MT04 fail this test among others | — | 2 | F1 | SETTLED (prefix-scoped: a gate under another prefix is hand-listed) |
| CLI-03 | copilot-mro | `claude_cli_telemetry.py:91-103` | `OTEL_SDK_DISABLED=true` → CLI telemetry off, content still pinned | The CLI does not read it | Same parse as `flynapse_otel/bootstrap.py:191` | `test_a_process_with_telemetry_disabled…` (:143), `test_any_other_disabled_value…` (:159) | yes — MT06 (`== "1"`) 3F | — | 1 | F1 | SETTLED |
| CLI-04 | copilot-mro | `claude_cli_telemetry.py:106-108`; `orchestrator.py:2408`; `sad_runner.py:367` | Same pins also as `ClaudeAgentOptions.settings` (`--settings`, the flag layer) | Settings-file `env` is laid over the process env at start | Binary `l9()`/`wT()` order read; SDK `_build_settings_value` passes JSON through; one `--settings` on argv | `test_the_flag_settings_carry_exactly_the_same_pins` (:166), `test_the_installed_sdk_hands_these_pins…` (:217), SAD `:196` | yes — MT05 settings `{}` 7F · MT13 SAD drops settings 4F · MT08 orchestrator drops settings 1F | — | 2 | F1 | SETTLED |
| CLI-05 | copilot-mro | `claude_cli_telemetry.py:24-30` | "Only managed policy outranks the flag layer" | Precedence of the CLI's settings loader | `V$`, `wT()`, `l9()` read @246905264 / @252854598; no policy file on box or image | none (vendor internals; cannot be pinned without launching the CLI) | not recorded | — | 2 | F1 | ASSERTED (read, not executed) |
| CLI-06 | copilot-mro | `copilot_mro/app/services/agent_claude/orchestrator.py:2360-2409` | The orchestrator's one options call carries both builders; nothing edits them afterwards | Every `/rag` turn's CLI | AST: one call, both keywords, no shadowing, no `options.env/settings` node | `test_the_orchestrator_passes_exactly_this_env…` (:281) | **partly** — MT08 1F, MT09 1F killed; **MT10 `dataclasses.replace`, MT11 `setattr`, MT15 a different options object to `query()` all SURVIVE** | 1 | 1 | F1 | **OPEN** — P1-2 |
| CLI-07 | copilot-mro | `copilot_mro/app/services/data_discovery/agent/sad_runner.py:361-367` | Pins laid LAST over the caller's Bedrock env; always set (env or no env) | All four SAD agents | Behavioural over a fake SDK, four real specs, hostile caller env | `test_every_real_agent_hands_the_cli…` (:196), `test_the_telemetry_pins_are_laid_over…` (:209) | yes — MT12 order reversed 1F · MT13 4F · MT14 env only if given 4F | — | 2 | F1 | SETTLED |
| CLI-08 | copilot-mro | `claude_cli_telemetry.py:32-37` | OTLP endpoint (and headers, resource attributes) inherited, not pinned | "the config the rest of copilot-mro uses" | Binary: settings-file `env` (global config, user, project, local) overwrites unpinned keys; signal-specific `…_LOGS_ENDPOINT` outranks the generic one the app reads; none set on this box today | none | not recorded | 2 | 2 | F1 | **OPEN** — P2-1 |
| CLI-09 | copilot-mro | `deployment/otel/base.yaml:157-164` | Fail-closed keep-pattern on the CLI's own scope | Vendor binary, attributes change per bump | Every content/identity key the 27 events can write is outside the pattern | `test_the_keep_pattern_keeps_per_call_detail…` (:147) | **partly** — MC01 `prompt`, MC02 `tool_parameters`, MC03 `user.email` each 1F; **MC04 `system_reminders`, MC05 `description` SURVIVE** | 2 | 2 | F1 | **PARTIAL** — P2-3 |
| CLI-10 | copilot-mro | `base.yaml:161-162`; `test_claude_code_log_allowlist.py:130-145` | Condition = `instrumentation_scope.name == "com.anthropic.claude_code.events"`, witnessed in the binary | A wrong scope keeps everything | Only scope the CLI uses (3 `getLogger` sites) | `test_the_allowlist_is_scoped…` (:130), `test_the_condition_names_the_scope…` (:138) | yes — MC06 wrong scope 1F | 2 | 2 | F1 | SETTLED for today's CLI; fail-OPEN on a scope rename (P2-3) |
| CLI-11 | copilot-mro | `base.yaml:165-166` | `error`/`error_message` deleted except on `api_error`/`api_retries_exhausted`; every value capped at 1024 | `tool_result`/`compaction`/`mcp_server_connection` text is not the provider's | Python model of the three YAML statements | `test_free_text_error_survives_only…` (:155) | yes — MC07 exempt `tool_result` 1F · MC08 cap 100000 1F · MC09 drop cap 2F | — | 2 | F1 | SETTLED (as a mechanism) |
| CLI-12 | copilot-mro | `base.yaml:165`; test `:155-164` | KEEP the provider's raw `error` text on `api_error`/`api_retries_exhausted` | Ruling says "errors" | CLI `u$y` = `e.error?.error?.message` or `e.message`, ungated by any flag; Bedrock 403 text carries principal ARN + account id; `redaction` masks neither | the same test asserts the text SURVIVES | n/a — the guard pins the behaviour in | 1 | 2 | F1 | **OPEN** — P1-1, owner ruling |
| CLI-13 | copilot-mro | `deployment/otel/backend-{aws,azure,newrelic,oss}.yaml` logs pipelines (`:102`/`:63`/`:49`/`:70`) | Allow-list first after `resourcedetection` on all four `logs` pipelines, nowhere else | CLI records land on `otlp` → `logs` | `logs/browser` is 4319-only; `content-phoenix` has traces only | `test_every_logs_pipeline_runs_the_allowlist…` (:177); `test_collector_profiles.py` | yes — MC11 1F · MC12 late placement 1F · MC13 second logs pipeline killed by `test_every_overlay_declares_the_complete_backend_half` | — | 2 | F1 | SETTLED |
| CLI-14 | copilot-mro | `base.yaml:105-118` | `genai_aliases` log clause matches bare `event.name == "api_request"` on the CLI scope; metric half deleted; off every metrics pipeline | The old `claude_code.api_request` clause never fired | Binary `Ac()`: `event.name` is bare, `claude_code.` is on the body | `test_the_genai_aliases_are_log_only…` (:193) | yes — MC14 prefixed condition 1F · MC15 back on oss metrics 1F | 3 | 1 | F1 | SETTLED; vocabulary drift P3-7 OPEN |
| CLI-15 | copilot-mro | `llm-agents.json`; `CATALOGUE.md`; `_emitted_series.py` | Remove the CLI tokens/cost panel, its catalogue row and the two inventory series | Ruling: duplicates the ledger | Board scan incl. dotted/quoted forms and rules | `test_cli_metrics_stay_off.py` (:49, :63, :74) | yes — MM1 UTF-8 selector 1F · MM2 inventory series 1F · MM3 alert rule 1F | — | 0 | F3 | SETTLED |
| CLI-16 | copilot-mro | `tests/integration/otel/test_cli_metrics_stay_off.py` (name); metrics pipelines | Metrics-off rests on the env pin only; no collector drop of `claude_code.*` | — | Nothing but `OTEL_METRICS_EXPORTER=none` stops the series | env test only (CLI-01) | MT03 kills the pin; nothing guards the collector side | 3 | 1 | F1 | **OPEN** — P3-2 |
| CLI-17 | copilot-mro | `CATALOGUE.md:178-182`; iac `dashboards/llm-agents.json.tftpl:7`, `tests/unit/observability/test_validate_metric_vocabulary.py:100-101` | Replacement documented as prose; iac still names the series | iac is another lane | grep | none | not recorded | 3 | 1 | F3 | **OPEN** — P3-3 (owed) |
| CLI-18 | copilot-mro | test sessions (all lanes, 45 mutants) | No test launches the Claude CLI, docker or otelcol | Implementer's sub-agent ran `claude --version` once | Refusing guard logged 0 CLI/otelcol launches; 20 docker launches refused (pre-existing compose tests) | the `sitecustomize` guard (review-side) | observed, not mutated | — | 1 | F3 | SETTLED (observed) |
| CLI-19 | copilot-mro | CLI child processes | Pins reach the CLI's children | — | Only child: `playwright` MCP (Node); SDK MCP servers and hooks are in-process | none | not recorded | 3 | 1 | F3 | ASSERTED; plan prose stale (P3-8) |
| CAP-01 | copilot-mro | `copilot_mro/app/db/postgres_table_definitions_modules/llm_turn_content.py:59-65`, `:114-140` | Delete `content_s3_key`, both CHECKs; keep `content` nullable | B8; nothing converges a NOT NULL on a live column | Registry emits `content jsonb,` and no spill column/prefix | `test_the_declaration_is_one_inline_store` (spill_retired :61), `test_content_is_always_stored_inline` | yes — MX04b declare NOT NULL 2F | — | 2 | F1 | SETTLED |
| CAP-02 | copilot-mro | same, `:59-65`; `scripts/drop_llm_turn_content_spill.sql:18-21` | Accept losing the DB-level non-null guarantee on `content` | Writer always sets it | Old either/or CHECK was the only enforcement; `converge_named_checks` (`migrate_tenancy_schema.py:2797-2829`) would add a named `content IS NOT NULL` CHECK to live tables | none | not recorded | 2 | 2 | F1 | **OPEN** — P2-2 |
| CAP-03 | copilot-mro | `copilot_mro/`, `scripts/` (AST) | No code path names the retired column | Old writer/DAO/purge named it | AST scan, docstrings excluded, 3 witnesses | `test_no_code_path_reads_or_writes_the_retired_column` (:97) | yes — MX01 DAO 3F · MX02 writer 3F · MX09 purge `RETURNING` 2F | — | 0 | F3 | SETTLED (copilot-mro only; other trees grep-clean) |
| CAP-04 | copilot-mro | `scripts/purge_llm_turn_content.py:57-70`, `:141-155` | Purge deletes rows only; returns `rowcount`; exit 0 | No object store | `RETURNING` gone; no S3 import | `test_purge_deletes_one_bounded_batch…`, `test_the_purge_has_no_object_store_branch` | yes — MX09 2F | — | 1 | F3 | SETTLED |
| CAP-05 | copilot-mro | `copilot_mro/app/config.py:1099-1104`; `llm_content_capture.py:1129`, `:1419-1460` | Truncate in place at 262 144 bytes; row keeps snapshot inline with `truncated=true` | B8 | >256 KB fixture → one row, inline, `truncated`, `content_bytes ≤ 262 144` | `test_an_oversized_turn_is_truncated_in_place_at_256_kb…` (:864) | yes — MX03 default 131 072 1F · MX12b never truncate 1F | — | 2 | F1 | SETTLED |
| CAP-06 | copilot-mro | registry `not_null_fields` | `truncated boolean DEFAULT false NOT NULL` stays | Readers need to know a snapshot is partial | Asserted in the declaration test | `test_the_declaration_is_one_inline_store` | yes — MX11 drop NOT NULL 2F | — | 2 | F1 | SETTLED |
| CAP-07 | copilot-mro | `scripts/migrate_tenancy_schema.py:1587-1592` + fake catalog | A live table still carrying the column and both CHECKs is tolerated: no writes, one "left in place" note, no finding | Order is code first, SQL later | Real phases driven over a pre-ruling catalog | `test_a_live_table_that_still_carries_the_spill_column…` (:165) | yes — MX13 migration drops undeclared 1F | — | 2 | F1 | SETTLED |
| CAP-08 | copilot-mro | `scripts/drop_llm_turn_content_spill.sql:88-148` | One transaction, `lock_timeout`, `row_security=off`, pinned `search_path`, refusal before drop, predicate read-back, no CASCADE, idempotent | Owner-run; nothing else can drop | Read in full | `test_the_owner_run_drop_is_transactional…` (:219) | **partly** — MX05 refusal after drop 1F · MX06 no row_security 1F · MX07 CASCADE 1F · MX10 read-back by name 1F; **MX08 no-op drop SURVIVES** | 3 | 2 | F1 | **PARTIAL** — P3-4 (execution OWED) |
| CAP-09 | copilot-mro | `drop_llm_turn_content_spill.sql:112-120` | Count under ACCESS SHARE, then ALTER upgrades | — | No writer sets the key, so no race today | none | not recorded | 3 | 2 | F1 | **OPEN** — P3-4 |
| CAP-10 | copilot-mro | `drop_llm_turn_content_spill.sql:31-43` | Deploy code first, then the SQL | Old INSERT names the column | New INSERT omits it; old CHECK holds; `SELECT *` readers use `.get` | none beyond CAP-03/CAP-07 | not recorded | — | 2 | F1 | ASSERTED |
| CAP-11 | copilot-mro | `test_phase1c_nonagent_scope_guard.py:335`; `test_llm_turn_content_spill_retired.py:222` | Prose says `content` NOT NULL | Left from `4c02a10e` | `5333e3cf` reversed it | none | n/a | 3 | 0 | F3 | **OPEN** — P3-1 |
| MRG-01 | copilot-mro | `tests/unit/observability/test_phase1c_nonagent_scope_guard.py:325-360` | Merge into `obs-merge 245e4d47` | Branch forked at `6aef26e3` | Textual conflict (both append); union resolution → merged lanes green-equivalent | scope guard (merged: 489 passed) | not recorded | 3 | 1 | F2 | ASSERTED (measured in scratch) — P3-5 |
| MRG-02 | copilot-mro | range `6aef26e3..7416d7a4` | Every commit green at its own SHA on the lanes it touches | — | See Lanes table | the lanes | n/a | — | 1 | F2 | ASSERTED (measured: no new red at any SHA; every red is the base's own, by test id) |
| MRG-03 | copilot-mro | `a18635e9` | Telemetry switched on before its second carrier and its collector line | Commit granularity | Allow-list at `4de21777`, `--settings` at `a32fd6fc` | none | n/a | 3 | 1 | F2 | **OPEN** — P3-6 (land as a unit) |
| DOC-01 | copilot-mro | `docs/plans/s4-browser-on-lang-slice.md:363` | "which the orchestrator leaves unset" | — | False since `a18635e9` | none | n/a | 3 | 0 | F3 | **OPEN** — P3-8 |

---

## Open claims, tier 2 first

**Tier 2 — open**

1. **CLI-12 (P1-1).** The raw provider `error` text, including the Bedrock principal ARN and account
   id, ships on `api_error` / `api_retries_exhausted` to every logs backend. The owner rules: drop it,
   categorise it, or accept it. Then the test at `test_claude_code_log_allowlist.py:155` is rewritten
   to assert the ruling.
2. **CLI-08 (P2-1).** The endpoint is not pinned, so a settings file (global config, user, project or
   local) or an inherited `…_LOGS_ENDPOINT` redirects the CLI's logs past the allow-list. Pin
   `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` in both carriers and correct the docstring.
3. **CAP-02 (P2-2).** `content` loses its only DB-level non-null guarantee at the DROP. Declare a named
   `content IS NOT NULL` CHECK; `converge_named_checks` carries it to live tables.
4. **CLI-09 / CLI-10 (P2-3).** The keep-pattern is not pinned by equality (MC04 and MC05 survive), and
   the processor fails open on a scope rename. Pin the pattern literally, and match on
   `service.name == "claude-code"` OR the scope.
5. **CAP-08 / CAP-09 (P3-4).** The DROP's shape test misses a no-op drop (execution OWED), and the
   refusal and the drop are not under one lock.

**Tier 1 — open**

6. **CLI-06 (P1-2).** The orchestrator guard is AST-only; MT10, MT11 and MT15 survive. Pin what reaches
   `query()`.
7. **CLI-16 (P3-2).** Metrics-off has one line only, and the test name overclaims.
8. **CLI-17 (P3-3).** The iac board and vocabulary test still name the retired series (owed).
9. **MRG-03 (P3-6).** Land the range as a unit.
10. **CLI-14 (P3-7).** Converge the `gen_ai.usage.cache_*` alias names with the gateway's.

**Tier 0 — open (docs)**

11. **CAP-11 (P3-1).** Stale NOT NULL prose in two places.
12. **DOC-01 (P3-8).** Stale spawn-env statement in the plan.

**Counts: 34 claims** — 17 SETTLED (one of them observed rather than mutated) · 5 ASSERTED · 10 OPEN ·
2 PARTIAL. Tier 0: CLI-15 and CAP-03 settled, CAP-11 and DOC-01 open.

**Mutants: 47 valid runs — 40 killed, 7 survived.** The survivors are MT10, MT11, MT15, MC04, MC05,
MC10 and MX08.
- MC10 changed `error_mode: ignore` to `silent`. It is not a finding: both modes continue past a
  failing statement and differ only in logging, and nothing pins `error_mode`.
- The other six survivors are the findings P1-2, P2-3 and P3-4.
