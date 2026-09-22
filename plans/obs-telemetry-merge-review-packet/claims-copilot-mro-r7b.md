# Claims packet — copilot-mro r7b: the two ranges no round covered

Independent adversarial review (Opus), 2026-09-21. Read-only against every code tree: each commit was
copied with `git archive` into a private scratch workspace
(`scratchpad/mro-review-r7b/ws/<sha>/copilot-mro-obsm`), given the real history through a read-only
`objects/info/alternates` link so `HEAD` equals the reviewed SHA and `git status` is clean, and run
there. Every mutation ran against a scratch copy of HEAD (`ws/HEADm`), was grep-confirmed, run, reversed
and md5-checked against the HEAD blob — **all 41 file restorations (40 mutants; one touched two files) MATCH**. No docker, DB, network, AWS or
Cognito call was made: a `sitecustomize` refused every INET connect outside loopback ephemeral ports,
every non-local DNS lookup (3,960 refused IMDS probes, `169.254.169.254`) and every `docker`/`psql`/
`pg_restore` exec (36 refused, all from compose/running-stack tests). It also stripped the api venv's
primary-checkout `.pth` paths.

| range | commits | subject |
|---|---|---|
| **A** `1d1d2dc8..0d9ecf0b` | `3978073b` G.6 · `a4d83100` G.13 · `9f44382e` Phase 6 review fixes · `45bda258` G.49 · `f7d32b97` G.64(d)+G.79 · `0d9ecf0b` G.11+G.78 | the 24 leftovers committed after their tests |
| **B** `8824a6d2..77fbf8ba` | `404d22be` NEW-3 · `4493f1df` 5b · `c86cef8e` NEW-4 · `e283a7c8` NEW-1 · `e34fe3f6` NEW-2 · `77fbf8ba` docs | the last g106 round (merged at `75947461`) |

Siblings: utils-obsm `594327e`, core-obsm `dc41caa`, flynapse-otel `34c814a` (as briefed), plus api-obsm
`847c34c` and dashboard-obsm `09bacba` for the tests that read them. All are archives, not checkouts.

Lane recipe, per SHA, from the tree root:
`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=<site-guard>:<tree>:<utils>:<core>:<flynapse-otel> /home/aditya/Code/api/.venv/bin/python -m pytest … -p no:randomly -p no:cacheprovider --continue-on-collection-errors -o addopts="-ra --strict-markers"`.
Each run used a fresh `PYTHONPYCACHEPREFIX`, and the exit code is pytest's own (`PIPESTATUS[0]`).
Every run printed `rootdir: …/ws/<sha>/copilot-mro-obsm`,
`copilot_mro.__path__ == ['…/ws/<sha>/copilot-mro-obsm/copilot_mro']` (one entry, so the namespace package
merged nothing from `/home/aditya/Code/copilot-mro`), `copilot_mro.app.__file__` in the same tree, and
psycopg2 2.9.12 with libpq 170009.

| lane | SHAs | result |
|---|---|---|
| **B** = `tests/unit/data_discovery` + the G.113 guard + the phase1c scope guard | `8824a6d2` · `404d22be` · `4493f1df` · `c86cef8e` · `e283a7c8` · `e34fe3f6` · `77fbf8ba` · HEAD | **403 · 403 · 411 · 419 · 427 · 440 · 440 · 441 passed, 0 failed, 1 skipped at every SHA** |
| **A** = the G.6 / G.13 / AD / `tests/integration/otel` files (18 paths) | `1d1d2dc8` → `3978073b` → `a4d83100` → `9f44382e` → `45bda258` → `f7d32b97` → `0d9ecf0b` → HEAD | failed+errors, excluding the 10 docker-refused harness ids: **17+11 → 14+10 → 14+9 → 10+9 → 10+8 → 4+8 → 2+8 → 3+8**, and the remainder at `0d9ecf0b` is harness only. Passed: 1015 → 1080 (HEAD 1094) |
| union (13 dirs) | HEAD | 6029 passed, 10 failed, 45 skipped, 10 errors in 27m48s. Every red id is either a harness artefact or pre-existing and outside these ranges (below) |
| `tests/unit/infra` | `8824a6d2`, `4493f1df`, `77fbf8ba` | 90 passed, 2 failed at all three: the same two, pre-existing at the base (a scratch-layout sibling pick, and the workout `logger` binding) |

**Range A was never green at its own SHAs, by construction.** The tests landed first (`60f40a9f`,
`4bfa4967`, `0231a1cf`, `d8d2570c`), and each commit's message says so. Measured: every commit turns its
own pre-landed tests green, and no commit turns anything red. **Range B is green at every SHA.**

---

## Findings, ranked

### P1-1 — A registry read that fails on ANY page makes the AD transition fan-out drop every event as "tenant not resolvable", and exit 0 (G.49/G.80)

`ad_notification_dispatcher.py:1224`: when `list_tenants` raises on page *k* of the walk (a pool blip, a
statement timeout), `_active_tenant_recipients` logs a warning and `return []`. It discards pages 1..k−1
too. It neither pages "to exhaustion" nor "refuses", which is what the commit subject promises.

- **`_process_transitions_async` (`:558-575`).** An empty roster makes every event's tenant
  "not resolvable from TenantService". The events are dropped and counted `events_without_audience`, and
  a normal `DispatchResult` comes back. `scripts/ad/evaluate_ad_applicability.py:863`'s failure handler
  (*"There is NO clean replay for what was lost"*) never runs, and the script exits 0. The verdicts are
  already committed, so these transition notifications are **permanently lost**, and the log blames the
  tenant. That is G.80's misattribution, reachable again through a transient error.
- **`_process_batch_async` (`:317-326`).** It logs "no tenants resolved … dispatch aborted" and returns a
  zero result, which `scripts/ad/dispatch_ad_notifications.py:316-317` reports as "Dispatch complete"
  with exit 0. By contrast, a *truncated* read raises and exits 1.

**Probe** (`probes/test_r7b_probe_g49.py`): a 437-tenant double raises on page 2. The roster comes back
`[]` with no exception, and `process_transitions(3 events)` returns `events_without_audience=3`.

**The test pins the defect.** `test_ad_dispatch_tenant_roster_completeness.py:252`
(`test_a_reader_that_raises_still_degrades_to_an_empty_roster`) asserts the `[]`, on the premise *"a
broken read is the callers' existing abort"*. That premise is true for only one of the two callers.
Mutant G49M4 turns the failure into a raise, and only that test goes red.

**Fix.** Raise `TruncatedTenantRegistryError` (chained to nothing) on a page failure. Add it to
`expected_dispatch_failures` in the evaluate script, and invert the pinned test.

### P2-1 — The NEW-3 SCRAM pin reads *membership*, so a second `POSTGRES_INITDB_ARGS` silently restores `trust` with the lane green (M-SAD-AUTH)

`test_sad_environment_failures_withhold_secrets.py:433-434` collects only `--env` values and asserts
`"POSTGRES_INITDB_ARGS=--auth=scram-sha-256" in settings`.

- **M2b.** A plausible edit adds a separate `--env POSTGRES_INITDB_ARGS=--data-checksums` entry. 149/149
  pass.
- **M2.** A later `--env POSTGRES_INITDB_ARGS=--auth=trust`: 149/149 pass.
- **M1.** A later `-e POSTGRES_HOST_AUTH_METHOD=trust`, a form the pin does not even read: 149/149 pass.

The docker CLI keeps both entries, and the image's bash entrypoint imports its environment in order, so
the last assignment wins. initdb then runs with its default, `trust` on the `local` lines. That is
exactly the owner-ruled P1 back, with every test green. (Docker's duplicate-env handling was reasoned
from its source, not run.)

The built value is right. **M11** (back to `--auth-local`) is red.

**Fix.** Assert the *effective* value per name over every env form (`--env`, `-e`, `--env=`, `-eNAME`),
and that each of the two names appears exactly once.

### P2-2 — The subagent-metric wire on the Claude runtime, and in fact on BOTH runtimes, can be deleted with every guard green (G.6)

All nine G.6 call-site mutants survived on the 234-test G.6 set (the only red was the known-stale metering
test, identical to baseline):

- G6M1: `orchestrator.py:3563` `observe_subagent_runs(...)` removed.
- G6M2: `query_adapter.py:254-255` stops threading `subagent_observer`.
- G6M3: `agent_pipeline.py:272` Claude composition binds `None`.
- G6M4: `lang_agent/backend.py:978-981` passes `None`.
- **G6M9: both runtime call sites removed at once.** This is the exact pre-G.6 state ("nothing in
  production reached `record_subagent`"). **272 passed**, including `test_emitted_series_inventory`,
  `test_alert_rules_layout` and `test_grafana_dashboards`.
- G6M5–M8: `usage_ledger.py:317,362,375` (every `llm_usage` loss path) and
  `model_call_ledger.py:280` (the budget-refusal unbound path) uncounted.

**Why.**

- `test_ledger_and_subagent_metric_wiring.py` drives the *helper* `observe_subagent_runs` and the
  `llm_model_calls` writer only. G6M10 (`_write_row`'s refused path) IS red.
- The inventory's reachability limb, `test_emitted_series_inventory.py:126-147` `_call_sites`, counts any
  `ast.Attribute` named `record_subagent`. That includes the composition root's *bound reference*
  (`:144`), so a binding whose observer is never invoked reads as WIRED.

The commit's own argument ("a one-runtime wire would under-report silently") names the failure nothing
guards.

**Fix.**

- One behavioural test per runtime that runs a turn with one Task/branch dispatch and reads
  `agent.subagent.calls`.
- Drive `record_turn_usage` failed/refused/unbound and `record_budget_refusal` unbound.
- Make `_call_sites` require an `ast.Call` on a path the runtime executes, not a reference.

### P2-3 — The G.113 guard's premise is false for `execute_values`/`execute_batch`, and `format_map` evades both Rule I and the "name-independent" Rule P

- **Measured with real psycopg2 + libpq + `Psycopg2Instrumentor`** against the repo's fake wire server
  (`probes/test_r7b_probe_execvalues.py`). A bound `cur.execute("UPDATE t SET k = %s", (S,))` exports
  `db.statement = "UPDATE t SET k = %s"`. But `execute_values(cur, "INSERT … VALUES %s", [(S,)])`
  exports `"INSERT INTO t (k) VALUES ('<S>')"`, and `execute_batch` exports `"UPDATE t SET k = '<S>'"`.
  psycopg2.extras mogrifies client-side and hands the *rendered* text to the instrumented `execute`.
- **The guard sees neither.** `_EXECUTE_METHODS` (`:90`) and `_RENDERERS` (`:101`) omit them, and its
  docstring says bound parameters are the sanctioned, unexported channel.
- **`format_map`.** `"SET k='{k}'".format_map({'k': password})` passes, and so does
  `"ALTER ROLE r PASSWORD '{p}'".format_map({'p': v})`. `_templates` (`:398`) handles `format` only.
- **No live instance.** The only `execute_values` is `scripts/seed_corpus_attribution.py:302`, whose
  process never bootstraps OTel.

The same `execute_values` path would also export *customer content* in `db.statement`, which is wider than
secrets.

**Fix.** Add both helpers to Rule I, reading their argslist as rendered text. Add `format_map` to
`_STRINGIFYING` and `_templates`.

### P2-4 — The `# secret-sql-ok:` escape hatch is unpinned, and it matches inside string literals

- **Zero production pragmas at HEAD**, and nothing pins that number or where pragmas may sit.
- **M12b.** The full G.113 revert (`sql.Literal(reader_password)`, no bound param) plus three reasoned
  pragmas passes all 149 SAD and guard tests. Without the pragmas (M12a) only the AST guard catches it.
  The behavioural reader test stays green because suppression now hides `db.statement`.
- **`_PRAGMA` (`:476`) reads raw lines.** `cur.execute(f"SET app.k = '{api_key}' -- # secret-sql-ok: x")`
  is accepted with no comment present.

**Fix.** Keep a register of pragma sites (file, line text, reason) held by equality, and match pragmas on
COMMENT tokens only (`tokenize`).

### P2-5 — The in-account judge catalogue has no equality pin, and residency is checked as a spelling, not an endpoint (G.13, M-RESIDENCY)

- **G13M1/G13M2.** Adding `"litellm"` or `"vertex_ai"` to `IN_ACCOUNT_JUDGE_PROVIDERS`
  (`contracts.py:56`) passes all tests (96). `test_the_in_account_catalogue_holds_no_vendor_api` is an
  eight-name *denylist* (`test_judge_provider_residency.py:42`), and `litellm` is a router to every SaaS.
- **The allowlist admits a spelling.** Where the content goes is set by environment the code never reads:
  - `AZURE_OPENAI_ENDPOINT` for `azure`;
  - the ollama base URL;
  - `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` / `AWS_PROFILE` for `bedrock`.
- **`azure` is admitted by default on an AWS deployment**, which has no Azure tenant of its own.
  `EVAL_JUDGE_PROVIDER_ALLOWLIST` can narrow, but its default is the whole catalogue.

**Owner call** (tier 2).

**Minimal fix.** Pin the catalogue by equality. Then either derive the default from the deployment's
cloud, or validate the endpoint host against an in-account allowlist.

### P2-6 — The Grafana healthcheck guard proves shape only: four decoys pass (G.11)

The probes as committed (`curl -fsS http://localhost:3000/api/health || exit 1`, in all three stacks) are
correct. The guard, `test_grafana_service_health_and_env.py:62,170-183`, accepts any probe containing the
URL plus the substring `curl`/`wget`. All four decoys pass (6/6 structural tests):

- `… || true`;
- `echo curl http://localhost:3000/api/health`;
- dropping `-f`, so a 503 from `/api/health` (Grafana's DB down) exits 0;
- a trailing `|| exit 0`.

`TestTheRunningStack` is the only behavioural half, and it skips unless the running container is this
tree's (G.11 notes that it is not).

The G.78 half *is* guarded: removing or commenting a datasource variable is red.

**Fix.** Parse the command: an HTTP client with `-f`/`--fail` (or wget's non-zero default), and a
failure branch that exits non-zero.

### P3-1 — The OFFSET walk still skips a tenant silently under one insert plus one delete between pages (G.49)

Probe `probes/test_r7b_probe_g49b.py`, on a 437-tenant registry: tenant 5 is deleted and a new tenant
signs up between page 1 and page 2. **437 served, 437 live, `tenant-00200` never served, no refusal.**
The count balances, so the completeness check is blind.

The plan's G.49 text calls the collapse to core's keyset `list_all_tenants()` *"cleanup owed, not a
defect"*. This probe says it is a (narrow, racy) defect. The fix is the same collapse.

### P3-2 — NEW-4's `_refuse_inherited_env` misses four bare-forwarding forms docker accepts

Probe: `-ePOSTGRES_PASSWORD`, `-e=POSTGRES_PASSWORD`, the combined shorthand `-ite POSTGRES_PASSWORD` and
`--env-file` all forward the inherited value, and are **not refused** (`environment.py:64-86`). No current
call site uses them, and all five real docker commands are correct.

### P3-3 — Phase 6 fix-pass rows `9f44382e` left open, still open at HEAD

- The fixpass tier-2 contradiction stands, and `9f44382e` strengthened it:
  `docs/runbooks/observability/oss-profile.md:196` says *"The secret files BELONG in the checkout"*, while
  `alertmanager/slack_webhook_url.placeholder` says *"live outside the repo"*.
- `frontend.json` panel 18 cites `provider.ts:147`, but the wiring is `:158-159`. `CATALOGUE.md` was
  corrected to `:158`; the board was not.
- `oss-profile.md:61`'s `:tenant` is still not runnable as pasted, and `9f44382e` promoted it to "the
  runbook SQL ledger check".
- The fixpass's two defeated guards are untouched: `test_alertmanager_secrets_dir.py` has had no change
  since, and `test_grafana_dashboards.py` only `dc4bf340`'s.

### P3-4 — At their own SHAs, `9f44382e` and `3978073b` over-claimed the alerts' first event (fixed at HEAD)

`9f44382e`'s rule comment and runbook said UnpricedModelCalls *"fires ~30m after the first unpriced call
and needs no second one"*. That is false for a new label set: the lazily created series is born at 1, and
`increase()` reads it as no change. LedgerWriteFailures had the same gap at `3978073b`. Both gained the
`unless … offset` branch in `57f486c6`, so they are closed at HEAD.

`3978073b`'s `subagent.name` label was model-chosen, unbounded, while the docstring claimed "a catalogue
agent name". It is now validated at HEAD (`subagent_metric_name`, M-GENAI-TENANT).

### P3-5 — The SAD span test is order-fragile, and its guard fires

Running `tests/unit/observability/test_nonagent_lifecycle_spans.py` before
`tests/unit/data_discovery/test_sad_reader_password_off_spans.py` leaves psycopg2 instrumented, so both
SAD span tests ERROR (*"psycopg2 is already instrumented in this session"*). Measured: 8 passed, 2 errors.
The canonical alphabetical `tests/unit` order is unaffected; explicit argument order or a randomizer is
not. The leaker should uninstrument.

### P3-6 — The Postgres server can log the reader password on a failed `CREATE ROLE` (reasoned, not run)

psycopg2 interpolates the bound value client-side, so the server receives
`CREATE ROLE "sad_reader" LOGIN PASSWORD '<pw>'`. An untrusted dump that pre-creates `sad_reader` makes it
fail, and `log_min_error_statement=error` then writes the full `STATEMENT:` to the container's stderr.
That reaches anything only through a shipping docker log driver (json-file dies with `--rm`). The
password is the disposable reader's.

### P3-7 — Plan drift

- G.113 is still `[~]`, with a CORRECTION reading *"LIVE on the integration branch until g106 merges"*,
  although `75947461` merged it.
- §4a-bis M-SAD-AUTH's Consequence still reads `--auth-local=scram-sha-256`; the built value is `--auth`
  (A71-03).
- The HEAD-red `tests/unit/metering/test_usage_ledger_write_guards.py::test_a_raising_write_is_logged_and_swallowed_never_reaching_the_turn`
  (stale since `ed1eeedb`'s M-TRACEBACK conversion, ledger Add. 129) is not from these ranges, and stays
  red.

**`9f44382e` vs `claims-phase6-fixpass.md`: PARTLY covered.** The fixpass reviewed the fix pass's
*uncommitted* production edits. `9f44382e` commits those edits PLUS the fixes answering that review:

- P0-1: query 3's `timed_out`/`skipped`;
- P1-1: `now() AT TIME ZONE 'UTC'`;
- P1-4: the UnpricedModelCalls lookback;
- P1-5: "both failure modes are LOGGED";
- the panel titles and the "EIGHT boards" count.

Those responses had no independent review before this one. I re-checked them:

- core `dc41caa` never writes `abandoned` (its own comment at `automation_store.py:161-163`), so the
  fixpass's `abandoned` clause is REFUTED and query 3 is complete.
- The `automation_runs` timestamp columns are naive `timestamp` (`table_definitions.py:1231ff`), so the
  cast is right.

The rows it did not answer are P3-3.

---

## What I tried to break and could not

- **Downgrade, swap or relay of the SAD socket, statically.**
  - initdb `--auth=scram-sha-256` plus the entrypoint's `host all all all scram-sha-256` makes every
    pg_hba line SCRAM. The temp server has no TCP listener and authenticates with the exported
    `PGPASSWORD`.
  - A socket or lock file planted before bind makes postgres FATAL ("could not create any Unix-domain
    sockets" / "could not remove old lock file"), because the sticky bit refuses its `unlink`. That is
    fail-closed: denial of service only.
  - After bind, only the owner uid (70), the dir owner or root can unlink, so a third uid cannot swap.
  - A relay needs a live server behind the impostor, and none can exist once postgres failed to bind.
    Every client refuses non-SCRAM (below).
  - In-container dump code (uid 70) *can* swap, but it is already superuser in the disposable DB and gains
    nothing.
- **Client pins, each red when removed:**
  - M3: the admin connection unpinned;
  - M8: the connector drops `require_auth`;
  - M9: the yielded details unpinned;
  - M4: `PGREQUIREAUTH` removed (11 red);
  - M5: the constant widened to `scram-sha-256,password`;
  - M6: the dir at `0o777`;
  - M11: `--auth-local`.
  The connector and admin tests run **real libpq** against trust/cleartext impostors and assert the
  password never reached them.
- **argv/env/log.**
  - M13 (`f"PGPASSWORD={admin_password}"` on `docker exec`) is red in two tests.
  - M10 (the `_run_step` refusal removed) is red in six.
  - `_run_step` logs step, timeout, exit code and `failure_fields` only.
  - `_refuse_inherited_env` names variables, never values.
- **G.113 on `db.statement`.** M7 (the `suppress_instrumentation` removed) is red in the real-instrumentor
  span test. The guard flagged every brief-named plant:
  - f-string, `%` tuple, `.format`, `sql.Literal`, `executemany`;
  - a password inside a DSN via f-string and via `%`;
  - bytes-`%`, `as_string`, and `'… PASSWORD {!r}'.format(v)`.
- **G.13.** Removing either re-check before `LLM(...)` (G13M3/M4) is red, and so is letting the env
  variable widen (G13M5).
- **G.49 arithmetic.** Removing the dedupe (G49M1) and accepting a missing `total` (G49M3) are both red.
  Core's reader now orders `created_at, tenant_id`, so a tie can no longer swap a pair.
- **G.79.** Removing the seeder's count warning (G79M1) is red. G.78: dropping or commenting a
  provisioning variable is red.
- **Metric names vs the boards.**
  - `agent.ledger.write_failures` becomes `agent_ledger_write_failures_total`.
  - `agent.subagent.calls` becomes `agent_subagent_calls_total`.
  - `agent.subagent.duration_seconds` becomes `agent_subagent_duration_seconds_bucket`.
  All go through `prometheusremotewrite`'s default suffixing, and each is exactly what
  `platform-health.json:83`, `llm-agents.json:168,173` and the rule read. `attributes/metric_cardinality`
  is a deny-list, so `ledger.*`/`subagent.*` labels survive.

## What I did not test

- **No docker, so nothing about the container ran.** Not SCRAM on the written `pg_hba`, not postgres
  starting with a `0o1733` dir, not the image's libpq 16 honouring `PGREQUIREAUTH`, and not docker's
  duplicate-`-e` resolution.
- **Nor 5a.** The g106 delta review confirmed from source that under `--cap-drop ALL` the official
  entrypoint cannot `chown`/`gosu`, so **SAD dump provisioning cannot start today**. All M-SAD-AUTH
  behaviour is therefore unexercised end to end (owner item C4).
- `arize-phoenix-evals` 3.8.0 is installed in no venv here. Whether `bedrock`/`ollama` are valid `LLM`
  providers at all, and how each resolves its endpoint, is unverified.
- The Grafana image's `curl` and `/api/health` semantics were not run.
- The docker-refused ids were not run: `test_compose_env_sample` (6), `TestTheRunningStack` (2) and
  `test_smoke_network_scoping` (2).
- Union-only reds at HEAD I did not attribute further. They are outside these ranges:
  - `test_agent_shared_pilot_contract_checkpoint`;
  - `test_langchain_ambient_surface_policy` (it reports `otel-collector-config.yaml` dropped from its
    scan);
  - three `test_cross_repo_reads_name_their_checkout` (scratch sibling layout, and exemptions naming
    primary paths);
  - two lang_agent timing tests run under 3-way load.
- `tests/db`, `tests/e2e` (bans), and every commit outside the two ranges except to check HEAD.

---

## Claims table

Severity: 0 = a content leak that ships · 1 = guard or lock integrity · 2 = a coverage gap · 3 = docs or
process.

Tier (§2.3a): 0 = settled by a guard I SAW fail · 1 = consequential, reversible · 2 = irreversible or
estate-shaping.

Chunk: F1 contract + privacy · F2 the merge · F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7B-01 | copilot-mro | `data_discovery/environment.py:270`; pin `test_sad_environment_failures_withhold_secrets.py:433-434` | initdb `--auth=scram-sha-256` (not the ruled `--auth-local`) | loopback `host` lines stay `trust` under `--auth-local` | M11 red; **M2, M2b, M1 green** (a second `POSTGRES_INITDB_ARGS` or later `-e …=trust` passes 149/149) | `test_the_container_is_initialised_with_scram_on_every_line` (membership) | partial (1 killed / 3 survive) | 1 | 2 | F1 | PARTIAL |
| R7B-02 | copilot-mro | `environment.py:219` | socket dir `0o1733` | stop a third uid swapping `.s.PGSQL.5432` | M6 red; pqcomm unlink/bind semantics read | `test_the_socket_directory_is_sticky_and_unlistable` | yes (mode) | 1 | 0 | F1 | SETTLED (mode) · postgres starting under it ASSERTED (C4) |
| R7B-03 | copilot-mro | `environment.py:472` | admin connection pins `require_auth=scram-sha-256` | refuse trust/cleartext impostors | M3 red: real libpq vs trust + cleartext impostors, password never sent | `test_the_admin_connection_refuses_a_server_that_does_not_run_scram` | yes | 1 | 0 | F1 | SETTLED |
| R7B-04 | copilot-mro | `environment.py:315`, `connectors/postgres.py:143`, `connectors/base.py:39` | connector pins via `ConnectionDetails.require_auth` | same, on the scan connection | M8, M9 red; customer default unchanged (test) | `test_the_connector_refuses_an_impostor_when_the_details_pin_scram` | yes | 1 | 0 | F1 | SETTLED |
| R7B-05 | copilot-mro | `environment.py:118-126` | `PGREQUIREAUTH` on every `docker exec` | in-container psql/pg_restore/pg_isready | M4 red (11), M5 red (3); image libpq 16 not run | exec env tests | yes (the env value) | 1 | 0 | F1 | SETTLED (code) · ASSERTED (in-image behaviour) |
| R7B-06 | copilot-mro | `environment.py:201-216` comment | pre-planted socket = fail-closed; no relay possible | sticky + SCRAM mutual | static analysis of the entrypoint + pqcomm; live check #3 owed | none | no | 1 | 2 | F1 | ASSERTED |
| R7B-07 | copilot-mro | `environment.py:64-86` | refuse bare `--env NAME` not in explicit `env` | `POSTGRES_PASSWORD` is also the platform secret | M10 red for the 3 parsed forms; probe: `-eNAME`, `-e=NAME`, `-ite NAME`, `--env-file` **not refused** | `test_a_bare_name_nobody_set_is_refused_before_anything_runs` | partial | 1 | 1 | F1 | PARTIAL |
| R7B-08 | copilot-mro | `environment.py:222-432` (the 5 provisioning docker commands) | passwords by env NAME only | argv is `ps`-readable | M13 red (2 tests); argv read | `test_no_command_line_handed_to_the_runner_holds_the_password` | yes | 0 | 0 | F1 | SETTLED |
| R7B-09 | copilot-mro | `environment.py:450` | reader grants under `suppress_instrumentation()` + one INTERNAL span | GRANT renders customer schema names into `db.statement` | M7 red (real instrumentor, live + exported) | `test_one_span_names_the_step_and_nothing_it_touched` | yes | 0 | 0 | F1 | SETTLED |
| R7B-10 | copilot-mro | `environment.py:483-489` | reader password bound (`sql.Placeholder`) | G.113 | M12a red (AST guard only); **M12b (+3 pragmas) green** | `test_no_module_renders_a_secret_into_sql_text` | partial | 1 | 1 | F1 | PARTIAL |
| R7B-11 | copilot-mro | `tests/unit/observability/test_no_secret_in_sql_text.py:476-500` | reasoned `# secret-sql-ok:` accepts a finding | NEW-2 false positives | 0 production pragmas, unpinned; the regex matches inside a string literal (probe) | none | no (M12b survives) | 1 | 1 | F1 | OPEN |
| R7B-12 | copilot-mro | same `:90-99,:101` | Rule I = execute family; bound params sanctioned | `capture_parameters` off | **real instrumentor: `execute_values`/`execute_batch` put bound values in `db.statement`**; guard silent; one use, `scripts/seed_corpus_attribution.py:302` (not bootstrapped) | none | n/a (probe) | 1 | 1 | F1 | OPEN |
| R7B-13 | copilot-mro | same `:103,:398` | Rule P "name-independent" | catch any PASSWORD slot | `format_map` passes both Rule I and Rule P (probe) | none | n/a (probe) | 1 | 1 | F1 | OPEN |
| R7B-14 | copilot-mro | same (detector) | the brief's plants | — | all 11 flagged: f-string, `%`, `.format`, Literal, executemany, DSN (2), bytes-`%`, `as_string`, `{!r}` password slot, `%` neutral slot | the parametrised detector | guard seen producing findings | 1 | 0 | F1 | SETTLED |
| R7B-15 | copilot-mro | same docstring "Not seen" | declared blind spots | — | confirmed: attribute/subscript stores, `dict.update`, `list.append`, `str.replace`, `dedent(f…)` | none | n/a | 2 | 1 | F1 | ASSERTED (declared) |
| R7B-16 | copilot-mro | `environment.py:483-489` + postgres logging | bound password reaches no log | — | reasoned: a dump pre-creating `sad_reader` fails our CREATE ROLE and the server logs the interpolated STATEMENT to container stderr | none | no | 0 (conditional: log driver ships it) | 1 | F1 | OPEN |
| R7B-17 | copilot-mro | `agent_claude/orchestrator.py:3563`, `query_adapter.py:254-255`, `agent_pipeline.py:272` | `agent.subagent.*` on the Claude runtime | "one-runtime wire under-reports silently" | G6M1, G6M2, G6M3 survive | none behavioural | no (3 survive) | 1 | 1 | F1 | OPEN |
| R7B-18 | copilot-mro | `lang_agent/backend.py:978-981` | same, lang runtime | — | G6M4 survives; **G6M9 (both runtimes) → 272 green** | none behavioural | no | 1 | 1 | F1 | OPEN |
| R7B-19 | copilot-mro | `tests/integration/otel/test_emitted_series_inventory.py:126-147` | "a production call site reaches the recorder" | AST, not substring | counts a bound reference (`:144`); G6M9 green | itself | no (defeated) | 1 | 1 | F1 | REFUTED (as a reachability proof) |
| R7B-20 | copilot-mro | `usage_ledger.py:317,362,375`; `model_call_ledger.py:280` | every non-landed write books `agent.ledger.write_failures` | billing loss must page | G6M5–M8 survive; G6M10 (`_write_row` refused) red | `test_ledger_and_subagent_metric_wiring.py` (llm_model_calls only) | 1 of 5 paths | 2 | 1 | F1 | PARTIAL |
| R7B-21 | copilot-mro | boards `platform-health.json:83`, `llm-agents.json:168,173`; rules `flynapse-agent-alerts.yml:74-78` | names the boards read | — | prometheusremotewrite default suffixing; the collector cardinality processor is a deny-list | `test_emitted_series_inventory` (names/kind) | not by me | 2 | 1 | F1 | ASSERTED |
| R7B-22 | copilot-mro | `3978073b` `subagent_runs.observe_subagent_runs` | `subagent.name` "a catalogue agent name" | — | at that SHA the label was the model's free text; HEAD validates (`subagent_metric_name`, `SUBAGENT_METRIC_NAMES`) | `test_every_branch_run_books_one_subagent_pair…` (`other`) | not by me | 1 | 1 | F1 | REFUTED at `3978073b` · fixed at HEAD |
| R7B-23 | copilot-mro | `9f44382e` rules + `alerts.md` | UnpricedModelCalls "fires after the first call" | lookback > hold | false for a new label set (born at 1); LedgerWriteFailures same at `3978073b`; both fixed by `57f486c6` | `test_alert_rules_layout` | not by me | 2 | 1 | F3 | REFUTED at SHA · fixed at HEAD |
| R7B-24 | copilot-mro | `agent_evaluation/contracts.py:56` | in-account catalogue `{azure,bedrock,ollama}` in code | no env can widen | **G13M1 (`litellm`), G13M2 (`vertex_ai`) survive**; the test is an 8-name denylist (`test_judge_provider_residency.py:42`) | `test_the_in_account_catalogue_holds_no_vendor_api` | no | 1 | 2 | F1 | OPEN |
| R7B-25 | copilot-mro | `contracts.py:56`, `phoenix_adapter.py:298,416` | provider spelling = residency | spec §6.5 / ruling 11 | endpoint env (Azure endpoint, ollama URL, `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`/profile) unchecked; `azure` default-admitted on AWS | none | n/a | 1 | 2 | F1 | OPEN (owner) |
| R7B-26 | copilot-mro | `phoenix_adapter.py:294,413` | re-validate before `LLM(...)` | env/attribute change after init | G13M3, G13M4 red | `test_every_judge_llm_construction_passes_through_the_allowlist` | yes | 1 | 0 | F1 | SETTLED |
| R7B-27 | copilot-mro | `contracts.py` `allowed_judge_providers` | env may only narrow | — | G13M5 red | `test_a_deployment_cannot_widen_the_catalogue` | yes | 1 | 0 | F1 | SETTLED |
| R7B-28 | copilot-mro | `notifications/ad_notification_dispatcher.py:1224` (+`:317-326`, `:558-575`) | a failed page read degrades to `[]` | "the callers' existing abort" | probe: page-2 failure → `[]` → 3 transition events dropped as "not resolvable", exit 0; G49M4 (raise) reds only the pinning test | `test_ad_dispatch_tenant_roster_completeness.py:252` (pins the defect) | yes (the test pins it) | 1 | 2 | F3 | OPEN — **P1** |
| R7B-29 | copilot-mro | same `:1177-1272` | OFFSET walk + dedupe + page-1 `total` | "pages to exhaustion or refuses" | probe: insert + delete between pages → `tenant-00200` unserved, 437/437, no refusal | none | n/a (probe) | 2 | 2 | F3 | OPEN |
| R7B-30 | copilot-mro | same | dedupe, then refuse short of `total`, or no `total` | tie skew / truncating reader | G49M1, G49M3 red | `TestRefusals` | yes | 1 | 0 | F3 | SETTLED |
| R7B-31 | copilot-mro | `scripts/ad/seed_ad_notification_subscription.py:66-99` | name Postgres + the DB; warn `total−1` left out | G.64(d), G.79 | G79M1 red | `test_ad_seed_subscription_registry_reads.py` | yes | 3 | 0 | F3 | SETTLED |
| R7B-32 | copilot-mro | `deployment/docker-compose.yml:194`, `observe-docker-compose.yml:116`, `poc/docker-compose.yml:158` | `curl -fsS …/api/health \|\| exit 1`, 30s start period | exit-0 crash loop read as "Up" | probe correct as written; **G11M1–M4 decoys pass** | `test_every_grafana_service_declares_a_healthcheck_on_api_health` | no (4 survive) | 1 | 1 | F3 | PARTIAL |
| R7B-33 | copilot-mro | same three stacks | restore `POSTGRES_DATASOURCE_{HOST,DB}` + readonly password (empty default) | M-GRAFANA datasource read nothing | G78M1, G78M2 red; no literal secret | `test_every_interpolated_provisioning_variable_reaches_the_container` | yes | 1 | 0 | F3 | SETTLED |
| R7B-34 | copilot-mro | `docs/runbooks/observability/oss-profile.md` query 3 + casts | `failed/timed_out/skipped OR late_run`; `now() AT TIME ZONE 'UTC'` | fixpass P0-1/P1-1 | core `dc41caa`: `abandoned` never written; columns naive `timestamp` | none | n/a | 3 | 1 | F3 | ASSERTED |
| R7B-35 | copilot-mro | `oss-profile.md:196` vs `alertmanager/slack_webhook_url.placeholder` | "BELONG in the checkout" | — | the placeholder says "outside the repo"; the fixpass tier-2 row, unchanged | none | n/a | 3 | 2 | F3 | OPEN |
| R7B-36 | copilot-mro | `frontend.json` panel 18; `oss-profile.md:61` | `provider.ts:147`; `:tenant` ledger check | — | wiring is `:158-159` (`CATALOGUE.md` says `:158`); `:tenant` not runnable as pasted | none | n/a | 3 | 1 | F3 | OPEN |
| R7B-37 | copilot-mro | `tests/integration/otel/test_alertmanager_secrets_dir.py`, `test_grafana_dashboards.py` | fixpass guards 1 & 2 | — | the fixpass defeats stand: files unchanged since (guard 2: `dc4bf340` only); not re-run | themselves | no | 1 | 1 | F3 | OPEN |
| R7B-38 | copilot-mro | `tests/unit/data_discovery/test_sad_reader_password_off_spans.py` | refuse to run on a pre-instrumented psycopg2 | read only its own spans | `test_nonagent_lifecycle_spans.py` first → 2 errors | itself | n/a | 2 | 1 | F1 | OPEN |
| R7B-39 | copilot-mro | range A, per SHA | tests landed before production | M-COMMIT era | lane A 17+11 → 2+8 (harness only) at `0d9ecf0b`; monotone; each commit greens its own | the per-item tests | n/a | 3 | 1 | F3 | SETTLED (measured) |
| R7B-40 | copilot-mro | range B, per SHA | each commit green at its own HEAD | — | lane B 403→440 passed, 0 failed, at all 7 SHAs + HEAD 441 | lane B | n/a | 3 | 1 | F1 | SETTLED (measured) |
| R7B-41 | copilot-mro | `tests/unit/metering/test_usage_ledger_write_guards.py:158` | "the traceback is kept" | — | red at HEAD since `ed1eeedb` (M-TRACEBACK), not from these ranges; known (Add. 129) | itself | n/a | 2 | 1 | F3 | OPEN |
| R7B-42 | docs | plan G.113 box; §4a-bis M-SAD-AUTH row | status text | — | G.113 `[~]` "LIVE until g106 merges" after `75947461`; ruling row says `--auth-local` | none | n/a | 3 | 1 | F3 | OPEN |
| R7B-43 | copilot-mro | `environment.py:222-276` (`--cap-drop ALL` + official entrypoint) | 5a | — | the g106 delta review, from source: the entrypoint cannot chown/gosu, so provisioning cannot start; every row above is code-true and live-unproven | none | n/a | 2 | 2 | F1 | ASSERTED (C4 owed) |

**Totals: 43 rows.**

- **State:** SETTLED 14 (tier 0: 12) · PARTIAL 5 · ASSERTED 5 · OPEN 16 · REFUTED 3.
- **Mutants:** 40, all restored and md5-MATCH. 21 killed, 19 survived: M1, M2, M2b, M12b, G6M1–M9,
  G11M1–M4, G13M1, G13M2. G49M4 is killed only by the test that pins the defect.

---

## Open claims, tier 2 first

**Tier 2**

1. **R7B-28 (P1).** A failed registry page silently empties the AD roster. The transition fan-out drops
   every event and exits 0, which is permanent loss. A test pins the behaviour.
2. **R7B-01.** The SCRAM pin reads membership. A second `POSTGRES_INITDB_ARGS` brings back `trust` with
   the lane green.
3. **R7B-24 / R7B-25.** The judge catalogue is unpinned (`litellm` passes), and residency is checked as a
   spelling, not an endpoint. `azure` is default-admitted on AWS (owner).
4. **R7B-29.** The OFFSET walk skips a tenant silently under insert + delete. Collapse to core's keyset
   `list_all_tenants()`.
5. **R7B-35.** The runbook and the committed placeholder disagree about where the Alertmanager secret
   files live.
6. **R7B-06, R7B-43.** Every M-SAD-AUTH property is code-true and live-unproven, and the container cannot
   start today (5a, C4).

**Tier 1**

7. **R7B-17/18/19/20.** Subagent and ledger metric call sites are unguarded on both runtimes, and the
   inventory's reachability limb counts a bound reference.
8. **R7B-12/13/11/10.** The G.113 guard:
   - `execute_values`/`execute_batch` put bound values in `db.statement` and the guard cannot see it;
   - `format_map` evades Rule I and Rule P;
   - the pragma escape hatch is unpinned and matches inside strings.
9. **R7B-32.** The healthcheck guard is shape-only.
10. **R7B-07.** NEW-4 misses `-eNAME`, `-e=NAME`, combined shorthands and `--env-file`.
11. **R7B-16, R7B-38, R7B-41, R7B-36, R7B-37, R7B-42.** The reader password can reach the container's
    stderr, the SAD span test is order-fragile, a metering test is stale-red at HEAD, a citation and the
    `:tenant` query are stale, the fixpass guards are still defeated, and the plan has drifted.
