# Claims packet — copilot-mro r7b r2: the fix batch for review r7b — PARTIAL — in progress

**STATUS: PARTIAL — in progress.** Paused on the owner's request 2026-09-22 ~01:57 PDT, mid-batch.
Rows marked **VERIFIED** were measured; rows marked **TODO** were not yet examined or were examined
statically only. The resume notes are in `~/.claude/scratch/obs-merge/r7b-review-r2/PAUSED.md`.

Independent adversarial review (Opus), 2026-09-22, second reviewer of this range (the first was killed
by a machine restart ~50 min in and filed nothing; no extracts of its survived, so everything below is
re-extracted). Read-only against every code tree: each of the 12 SHAs (base + 11) was copied with
`git archive` into `scratchpad/r7b-review-r2/ws/<sha>/copilot-mro-obsm`, given the real history through
a read-only `objects/info/alternates` link to `/home/aditya/Code/copilot-mro/.git/objects` (so `HEAD`
equals the reviewed SHA and `git status` is clean, verified for all 12), and given the five sibling
checkouts as symlinks beside it. No docker, DB write, network, AWS or Cognito call was made.

| range | commits |
|---|---|
| `67006780..afe79dbb` on `obs-merge-r7b` (11) | `8be6f663` P1-1 · `1c7db875` P3-1 · `81bd0942` P2-1+P3-2 · `e4d263d2` P3-6 · `298b8fb5` P3-5 · `63cd01d7` P2-3+P2-4 · `1f705234` P2-6 · `300a6fb2` P3-3 · `b63a03fd` P2-5 · `3ec66117` P2-2 · `afe79dbb` R7B-41 |

Siblings (as they stood): core-obsm `fe41002`, utils-obsm `179cc6d`, api-obsm `e3ba207`, flynapse-otel
`0960c16`. `obs-merge` moved from `735f8213` (launch) to `557a178f` (the cli lane merged) while this ran;
the trial merge used `557a178f`.

Lane recipe, per copy, from its root, every run through `pytest-slot.sh`:
`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=<copy>:core-obsm:utils-obsm:api-obsm:flynapse-otel /home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider --rootdir=<copy> -c <copy>/pyproject.toml …`
(`scratchpad/r7b-review-r2/lane.sh`, mirrored under `~/.claude/scratch/obs-merge/r7b-review-r2/`).

## Lanes run so far

| lane | copy | result |
|---|---|---|
| **T** = the 8 dirs holding the 19 touched test files (`tests/agent_sdk/core`, `tests/integration/otel`, `tests/unit/{ad,agent_shared,data_discovery,lang_agent,metering,observability}`), `-n 2` | HEAD `afe79dbb`, **bare archive (no `.git`, no siblings)** | 5417 passed, **17 failed, 4 errors**, 44 skipped, 11m47s |
| the 19 red ids alone, `-n 0` | HEAD, **with `.git` + siblings** | **36 passed, 0 failed** — every red was a harness artefact (git history, `git ls-files`, sibling resolution, or xdist order) |
| T again with `.git` + siblings, `-n 2` | HEAD | **KILLED at 73% by the pause** — must be re-run (`lanes/T-HEAD-git.log`) |
| per-SHA T lanes (11 SHAs + base) | — | **TODO** |
| the merged tree (`merge/copilot-mro-obsm` at `a041b82c`) | — | **TODO** |

The bare-archive reds (all cleared with history present): `test_phase1c_nonagent_scope_guard` ×3 (git
diffs), `test_the_register_never_regrows_across_its_history` ×2 (git log), `test_alertmanager_secrets_dir`
+ `test_alertmanager_config` (git ls-files), `test_debug_dumps.py` ×9 + `test_lang_sad_activation` ×1
(pass serially; xdist/order — pre-existing, outside the range), `test_retired_legacy_metrics_stay_deleted`
×2 and `test_ad_notification_payload_contract` ×2 (errors; pass with history).

---

## Findings, ranked (so far)

### P2-1 (candidate, static only — probe written, not run) — the bedrock endpoint check admits any AWS-hosted proxy in ANY account (P2-5 / M-RESIDENCY)

`contracts.py` `_AWS_HOST_SUFFIXES = (".amazonaws.com",)` and `_is_in_account_host("bedrock", host)` is
`host.endswith(".amazonaws.com")`. The docstring of `require_in_account_endpoint` names its own target —
*"`AWS_ENDPOINT_URL` pointed at a proxy … sends the judge's input there under an in-account name"* — and
an AWS-hosted proxy is exactly what the suffix cannot see:

- `AWS_ENDPOINT_URL_BEDROCK_RUNTIME=https://abc123.execute-api.us-east-1.amazonaws.com/prod` (an API
  Gateway in any account, forwarding to any SaaS) → **admitted**;
- `AWS_ENDPOINT_URL=https://x.us-east-1.elb.amazonaws.com` (an ALB in any account) → admitted;
- `http://ec2-3-4-5-6.compute-1.amazonaws.com:8080` (an EC2 public name) → admitted;
- `https://s3.amazonaws.com` (not even the bedrock service) → admitted.

The check proves "the vendor's domain", not "the deployment's account" (the module's own comment on
`_AWS_HOST_SUFFIXES` concedes the account is what the credentials name). **Fix:** for bedrock require
`bedrock-runtime(-fips)?\.<region>\.amazonaws\.com` or a `*.bedrock-runtime.<region>.vpce.amazonaws.com`
VPC endpoint host; the same shape for azure (`<resource>.openai.azure.com` is any tenant's resource).
Severity 1, tier 1. **TODO: run `probes/test_r2_probe_residency.py` to turn this from reasoned into measured.**

### P3-1 (VERIFIED) — collapsing to core's walk dropped the dispatcher's "no `total` = unverifiable" refusal, and the commit says the case moved to core's suite, where core pins the OPPOSITE (P3-1 / G.49)

Base `_active_tenant_recipients` refused a reader that reported no `total` (*"its absence means the reader
is not the one this function was written against"*; test `test_a_reader_that_reports_no_total_is_refused_as_unverifiable`,
mutant G49M3 red in review r7b). `1c7db875` deleted that test — *"the offset-only cases (seam duplicate,
page ceiling, missing total) belong to core's suite now"* — but core's `iter_all_tenants` **accepts** a
never-counting reader ("degrades to plain cursor semantics",
core `tests/unit/db/test_tenant_registry_enumeration.py::test_a_reader_that_never_counts_degrades_to_cursor_semantics`).

**Measured** (`probes/test_r2_probe_registry.py`, 9/9 green at HEAD): a 437-tenant registry whose reader
reports no count on any page AND truncates at 120 is **served as 120 with no refusal**; a row without a
`tenant_id` under the same reader is silently dropped. With core's real `list_tenants_page` (count in the
same statement) neither can happen, so the exposure needs a non-core reader (a double, a future reader
variant, a monkeypatch). Severity 2 (coverage), tier 1. **Fix:** either a `require_count=True` on
core's `list_all_tenants` that the dispatcher passes, or the dispatcher's docstring drops the claim.

### P3-2 (VERIFIED) — a reader that returns the wrong TYPE crashes rather than refuses (P1-1)

`_active_tenant_recipients` checks only `tenants is None`. `list_all_tenants()` returning a dict
(`{"tenants": […]}`) raises `AttributeError` from `tenant.get` — an unchained crash that reaches the
evaluate CLI's UNEXPECTED branch (traceback to stderr, exit 1) instead of the REFUSED branch. Fail-closed,
so P3. A generator is accepted and consumed. Measured in the same probe.

### P3-3 (VERIFIED, reasoned) — `EXIT_DISPATCH_REFUSED = 1` collides with every other failure exit

`evaluate_ad_applicability.py` exits 1 for `SystemExit(str)` (psycopg2 missing, `:615`) and for the
UNEXPECTED re-raise as well, so an unattended schedule cannot tell "refused, nothing dispatched, verdicts
committed" from "crashed". A distinct code (e.g. 3) costs one constant. Severity 3.

### P3-4 (static, TODO to measure) — the healthcheck parser accepts `|| exit 256`

`healthcheck_probe_offenses` accepts a tail of `|| exit <digits>` when `int(tail[2]) != 0`; a shell
`exit 256` (or 512) exits **0**, so that decoy reads as healthy. `int(tail[2]) % 256 != 0` closes it.
Everything else I tried statically is refused (`|| exit 1 || true`, `; true`, `2>/dev/null` — false
refusal, `-so -f`, `--output -f`, `--fail --no-fail`, `$URL`, `sh -c`, `CMD` wrappers).

### P3-5 (VERIFIED) — `afe79dbb` (R7B-41) is already on `obs-merge` as `ea55eb55`, and is the trial merge's one conflict

Both sides rewrote `test_a_raising_write_is_logged_and_swallowed_never_reaching_the_turn` to the
M-TRACEBACK shape; the hunks differ only in wording and sentinel. Resolution: take either (I took
`obs-merge`'s). Nothing else conflicts.

### Residency residuals (static, not findings of this batch's claim): the check reads endpoint variables only

`HTTPS_PROXY` (+ `AWS_CA_BUNDLE`/`SSL_CERT_FILE` for a MITM), `AWS_PROFILE` naming another account, a
`.internal`/single-label name a resolver CNAMEs anywhere, and an Azure resource in another tenant are all
admitted; a trailing-dot FQDN is falsely refused. These are the limits of an offline, string-level check
and the commit does not claim them; recorded as ASSERTED rows.

---

## What I tried to break and could not (so far)

- **The reader password path (P3-6), measured with real libpq against the fake wire server**
  (`probes/test_r2_probe_password_path.py`, 6/6 at HEAD):
  - a raw-byte tap on every message the client sent (`_receive` teed): neither the reader nor the admin
    password is on the wire; no `SHOW` round-trip for the algorithm (`scram_iterations` is read from
    `ParameterStatus`, and 8192 is honoured);
  - a server whose CREATE ROLE fails (`DuplicateObject`, the pre-created-role case): the password is in
    none of `repr(exc)`, `str(exc)`, `exc.args`, `pgerror`, `diag.message_primary`, `cursor.query`, the
    rendered traceback, the loguru sink, the live or exported spans (the provision span carries
    `error.type=DuplicateObject` and no message);
  - a server holding ONLY the captured verifier (salt, iterations, StoredKey, ServerKey) logs the reader
    in through real libpq SCRAM with the password, refuses a wrong password, and a neighbour's verifier
    refuses the right password.
  - Mutants: PW-M1 (bind the plaintext again) **KILLED** by the committed test alone; PW-M2 (`md5`
    verifier) **KILLED**; PW-M3 (another user name in the verifier) survived = **equivalent** (SCRAM
    verifiers do not bind the user; only md5 does).
- **The registry refusal (P1-1/P3-1), measured:** page 1 read then page 2 raising → refusal chained to
  nothing, driver text absent; a page whose `tenants` raises mid-iteration → the same; a row without a
  `tenant_id` → refused via core's count; `list_all_tenants` returning `None` → refused; a genuinely empty
  registry → `[]` and the batch reports clean (by design); nothing upstream catches
  `TruncatedTenantRegistryError` and falls back — the two CLI callers are the only callers, the evaluate
  CLI's `except roster_refusal` precedes `expected_dispatch_failures`, and the batch CLI's blanket catch
  exits 1.
- **The SCRAM effective-value pin (P2-1), static:** `test_the_container_is_initialised_with_scram_on_every_line`
  reads the real `start_container` argv through its own oracle and requires each name exactly once at its
  value; the production refusal (`_refuse_unsafe_env`) fires before the runner on a duplicate, so a
  planted second entry is red twice. Mutants written, **not run**.
- **The argv reader (P3-2), static:** `--env-file` and `--env-file=` refused outright; `-e`, `-eX`, `-e=X`,
  `-ite X`, `-iteX` read; a valued letter before `e` errs to refusing; a value holding a newline or `--` is
  consumed as a value; a case-different name is (correctly) not a duplicate; `--env --env-file` lands as
  a bare name and is refused. Mutants written, **not run**.
- **G.6 (P2-2), static:** the Claude test drives `orchestrator.run_query` offline through the real
  `observe_subagent_runs` call; the lang test drives the composed wrapper through `backend.py:978`; the
  composition test binds both builders to one `RuntimeTelemetry` and books through the bound observers;
  `_call_sites` counts `ast.Call` only; `CALLBACK_WIRED` defers to the three named files (existence +
  method name + `InMemoryMetricReader` — a shape check; the behavioural files are the proof). All four
  new files patch `OTEL_SDK_DISABLED=false` around provider creation, so obs-merge's session pin
  (`614b95ee`) should not blind them. Mutants written, **not run**.
- **G.113 (P2-3/P2-4), static:** batch helpers read as SQL text (query, argslist, template, positional or
  keyword); `format_map` in `_STRINGIFYING` and `_templates`; pragmas on COMMENT tokens via `tokenize`;
  `PRAGMA_REGISTER` empty by equality; the one batch site pinned. The `bootstrap(` check on that site is
  a shape check (an import chain could bootstrap), but `seed_corpus_attribution.py` imports only
  `psycopg2`, `_common` and `fixtures.tenancy.rls_connections`.

## What I did not test (yet) — TODO in order

1. Lane T at HEAD with history (killed at 73%); then T at each of the 11 SHAs + base
   (`parallel-commits.sh -L -j 2` or the extracts, `-n 0`/`-n 2`); the union claim (6072 → 6179; 4F+8E
   pre-existing) — not verified at all.
2. Mutants written and not run: `mut/scm{1,1b,2}_*` (SCRAM pin), `mut/arm{1..4}_*` (argv reader),
   `mut/g6m{1,3,3l,4,5,6,7,8}_*` + `mut/cwm{1,2}_*` (G.6); a residency mutant set (drop
   `require_in_account_endpoint` from `validate_judge_provider`; widen `_AWS_HOST_SUFFIXES`); a G.113
   set (remove `execute_values` from `_BATCH_HELPERS`; `format_map` from `_STRINGIFYING`; `_comments`
   back to raw lines; `PRAGMA_REGISTER` non-empty); a healthcheck set (`|| true`, `echo curl`, drop `-f`,
   `|| exit 0`, `|| exit 256`); the P3-5 uninstrument; the P3-3 placeholder test.
3. `probes/test_r2_probe_residency.py` (written, not run).
4. Re-prove a sample of the implementer's 52 mutants (their list was not available; sample by finding).
5. The merged tree's lanes (`merge/copilot-mro-obsm` at `a041b82c`).
6. The evaluate CLI's `logger.error("… failed (%s) …", type(exc).__name__)` conversion: the debt register
   dropped `logger.exception` 5 → 4 — check the converted site is the ONLY change and that `failure_fields`
   (frames) was not owed there.
7. `docs/runbooks/observability/phoenix-evaluations.md` cloud table vs the code; `oss-profile.md` `\set`.

---

## Claims table (PARTIAL)

Severity: 0 = a content leak that ships · 1 = guard or lock integrity · 2 = a coverage gap · 3 = docs or
process. Tier (§2.3a): 0 = settled by a guard I SAW fail · 1 = consequential, reversible · 2 = irreversible
or estate-shaping. Chunk: F1 contract + privacy · F2 the merge · F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7B2-01 | copilot-mro | `data_discovery/environment.py:534-543` (`e4d263d2`) | the reader role is created from a client-derived SCRAM verifier (`encrypt_password(…, "scram-sha-256")`), bound | a failed CREATE ROLE is logged with its statement | **VERIFIED**: raw-byte tap — password never on the wire; no SHOW; verifier logs the reader in via real libpq; wrong/neighbour verifier refused; `scram_iterations` honoured | `test_the_role_is_created_with_the_verifier_of_its_password_and_never_the_password` | **yes**: PW-M1 (plaintext) KILLED by the committed test; PW-M2 (md5) KILLED; PW-M3 equivalent | 0 | 0 | F1 | SETTLED |
| R7B2-02 | copilot-mro | same, failure path | a failed CREATE ROLE leaks nothing | — | **VERIFIED**: DuplicateObject — exc text/args/pgerror/diag/cursor.query/traceback/loguru/spans all password-free; span = class name only | my probe (not committed) | n/a | 0 | 0 | F1 | SETTLED (probe) — no committed guard for the failure path (sev 2 gap, minor) |
| R7B2-03 | copilot-mro | `ad_notification_dispatcher.py:1200-1241` (`8be6f663`) | a failed page/import raises `TruncatedTenantRegistryError`, after the handler, class name only | `[]` was permanent loss blamed on the tenant | **VERIFIED**: page-2 failure, mid-iteration raise, import failure → refusal, chained to nothing, driver text absent | `TestRefusals`, `TestTheRefusalReachesTheCaller` | not yet (TODO: revert to `return []`) | 1 | 1 | F3 | SETTLED (behaviour) · mutation TODO |
| R7B2-04 | copilot-mro | `scripts/ad/evaluate_ad_applicability.py:893-928` | `except roster_refusal` → REFUSED, `EXIT_DISPATCH_REFUSED=1`; `except ()` until imported | non-zero for an unattended schedule | **VERIFIED** (committed CLI tests with the real dispatcher + a planted one; read) | `TestTheEvaluateCliSeesTheRefusal`, `test_a_refused_roster_exits_non_zero…` | not yet | 1 | 1 | F3 | SETTLED · **P3-3: code 1 collides with every other failure** |
| R7B2-05 | copilot-mro | `scripts/ad/dispatch_ad_notifications.py:310-314` | the batch CLI's blanket catch exits 1 on the refusal | — | read: `except Exception` → `traceback.format_exc()` (pre-existing debt) → `return 1`; the refusal is unchained so the rendered traceback carries the class only | none new | n/a | 1 | 1 | F3 | ASSERTED (read) |
| R7B2-06 | copilot-mro | `ad_notification_dispatcher.py:1216-1231` (`1c7db875`) | the roster = core's `list_all_tenants()` keyset walk; offset pager deleted | insert+delete skew | **VERIFIED**: insert+delete probe is a committed test; core's walk runs for real over a one-page double | `test_an_insert_and_a_delete_between_pages_skip_nobody` | not yet | 2 | 1 | F3 | SETTLED |
| R7B2-07 | copilot-mro | same | "missing total belongs to core's suite" | — | **REFUTED**: core ACCEPTS a never-counting reader; no-total + truncating reader → 120 of 437 served, no refusal (probe) | none (the base test was deleted) | n/a | 2 | 1 | F3 | REFUTED — **P3-1** |
| R7B2-08 | copilot-mro | same `:1233-1241` | `tenants is None` is the only type check | — | **VERIFIED**: a dict → AttributeError crash (fail-closed, UNEXPECTED branch); generator accepted | none | n/a | 3 | 1 | F3 | OPEN — **P3-2** |
| R7B2-09 | copilot-mro | `environment.py:64-98` (`81bd0942`) | `_env_flag_values` reads every pflag spelling; `--env-file` refused; duplicates refused | P2-1/P3-2 | static: every spelling traced; newline/`--` values consumed as values; case-different names not duplicates (correct) | `test_an_env_file_is_refused…`, `test_a_name_stated_twice…`, the 7-spelling bare-name cases | **TODO** (`mut/arm1-4`) | 1 | 1 | F1 | ASSERTED (static) — TODO |
| R7B2-10 | copilot-mro | `test_sad_environment_failures_withhold_secrets.py:418-443` | the SCRAM pin reads the EFFECTIVE value through its own oracle, each name once | membership let `trust` back | static: oracle independent of production; a planted duplicate is red twice (production refusal + pin) | itself | **TODO** (`mut/scm1,1b,2`) | 1 | 1 | F1 | ASSERTED (static) — TODO |
| R7B2-11 | copilot-mro | `agent_evaluation/contracts.py:64-97` (`b63a03fd`) | catalogue + per-cloud map pinned by equality; union == catalogue; unset cloud = `aws` | `litellm` passed the denylist | read: `test_the_in_account_catalogue_is_pinned_by_equality` pins both by equality and the union | itself | **TODO** (add `litellm` to the aws set only) | 1 | 1 | F1 | ASSERTED (read) — TODO |
| R7B2-12 | copilot-mro | `contracts.py:173-224` | endpoint variables that are SET must name an in-account host | residency = where the content goes | **static**: `.amazonaws.com` admits API Gateway / ALB / EC2 / S3 hosts in any account (**P2-1**); `HTTPS_PROXY`, `AWS_PROFILE`, CNAME-able private names unread; trailing dot falsely refused | `test_an_endpoint_outside_the_account_is_refused` (8 cases, none AWS-hosted) | **TODO** (probe written) | 1 | 1 | F1 | OPEN — **P2-1 candidate** |
| R7B2-13 | copilot-mro | `contracts.py:117-128` | `EVAL_JUDGE_DEPLOYMENT_CLOUD` normalised `.strip().lower()`; unknown refuses all | — | read: `AWS`/` aws ` → aws; `self_hosted`, `aws,azure` → refuse | `test_an_unknown_deployment_cloud_refuses_every_provider` | TODO | 1 | 1 | F1 | ASSERTED (read) |
| R7B2-14 | copilot-mro | `tests/integration/otel/test_emitted_series_inventory.py:126-216` (`3ec66117`) | `_call_sites` = `ast.Call` only; `CALLBACK_WIRED` defers to 3 named behavioural files + both builders binding | a bound reference counted as WIRED | read: the deferral is a shape check (file exists, names the method + `InMemoryMetricReader`) | itself | **TODO** (`mut/cwm1,2`) | 1 | 1 | F1 | ASSERTED (read) — TODO |
| R7B2-15 | copilot-mro | `tests/agent_sdk/core/test_agent_sdk_subagent_metric.py`, `tests/unit/lang_agent/test_lang_subagent_metric.py`, `test_composition_root.py:940-996` | behavioural: real `RuntimeTelemetry` + `InMemoryMetricReader` on both runtimes + the composition | G6M1-M4, M9 survived | read: Claude drives `run_query` through `orchestrator.py:3563`; lang through `backend.py:978` via `_run`'s new passthrough; composition binds both builders; tool half is a two-seam proof (forwarder called by hand) | themselves | **TODO** (`mut/g6m1,3,3l,4`) | 1 | 1 | F1 | ASSERTED (read) — TODO |
| R7B2-16 | copilot-mro | `tests/unit/agent_shared/test_ledger_and_subagent_metric_wiring.py` | `record_turn_usage` failed/refused/unbound + `record_budget_refusal` unbound book `agent.ledger.write_failures` | G6M5-M8 | read: 5 new tests | themselves | **TODO** (`mut/g6m5-8`) | 2 | 1 | F1 | ASSERTED — TODO |
| R7B2-17 | copilot-mro | `tests/unit/observability/test_no_secret_in_sql_text.py` (`63cd01d7`) | Rule I reads `execute_values`/`execute_batch` query+argslist+template; `format_map` stringifying + templated; pragmas = COMMENT tokens; `PRAGMA_REGISTER` empty by equality; `BATCH_HELPER_SITES` pinned | P2-3/P2-4 | read; 12 new plants | itself | **TODO** | 1 | 1 | F1 | ASSERTED (read) — TODO |
| R7B2-18 | copilot-mro | `tests/integration/otel/test_grafana_service_health_and_env.py:60-165` (`1f705234`) | the probe is lexed and judged: curl with `-f` in effect or wget, the health URL, then nothing or `\|\| exit <non-zero>` | four decoys passed | static: sound except **`\|\| exit 256` → shell exit 0 accepted (P3-4)** | 23 parametrised cases | **TODO** | 2 | 1 | F3 | PARTIAL |
| R7B2-19 | copilot-mro | `tests/unit/observability/test_nonagent_lifecycle_spans.py:26-64` (`298b8fb5`) | the `main` fixture uninstruments what its import newly instrumented | order fragility | read: scoped to its own delta (`before`); only unit importer of `app.main` | itself | TODO (the pair in order) | 2 | 1 | F1 | ASSERTED (read) |
| R7B2-20 | copilot-mro | `alertmanager/slack_webhook_url.placeholder`, `frontend.json` panel 18, `oss-profile.md`, `test_grafana_dashboards.py` (`300a6fb2`) | placeholder names the git-ignored secrets dir; `:158-159`; `\set tenant`; catalogue == board browser signals | P3-3 | read | `test_the_webhook_placeholder_sends_the_owner_where_the_runbook_does`, the equality in guard 2 | TODO | 3 | 1 | F3 | ASSERTED (read) |
| R7B2-21 | copilot-mro | `tests/unit/metering/test_usage_ledger_write_guards.py` (`afe79dbb`) | R7B-41 test pins the M-TRACEBACK shape | stale red | **VERIFIED**: the same fix is on `obs-merge` as `ea55eb55`; the trial merge's ONE conflict | itself | n/a | 3 | 1 | F2 | SETTLED — redundant (**P3-5**) |
| R7B2-22 | copilot-mro | trial merge of `afe79dbb` onto `obs-merge` **`557a178f`** | — | — | **VERIFIED**: one textual conflict (R7B2-21), resolved to `obs-merge`'s side; merged `a041b82c` in scratch; 6 files touched on both sides, the other 5 auto-merged; semantic candidate = `614b95ee`'s `OTEL_SDK_DISABLED=true` session pin vs the 4 new metric tests (each patches it false — statically fine) | the merged lanes | n/a | 1 | 1 | F2 | PARTIAL — **lanes on the merged tree TODO** |
| R7B2-23 | copilot-mro | lane T at each SHA; the union claim 6072→6179, 4F+8E pre-existing | green at every SHA | — | HEAD bare-archive 17F+4E all harness; **with history: killed at 73%**; per-SHA and union **not run** | — | n/a | 3 | 1 | F3 | **TODO** |
| R7B2-24 | copilot-mro | the implementer's 52 mutants | killed | — | list not available; **not re-proved** (3 of my own killed) | — | — | 3 | 1 | F3 | **TODO** |
| R7B2-25 | copilot-mro | `evaluate_ad_applicability.py:924-930` + `_mro_exception_text_debt.py` 5→4 | the failed-dispatch log names the class only, no `failure_fields` | M-TRACEBACK | read: `logger.error("… (%s) …", type(exc).__name__)` — class without frames; the register moved one unit | `test_no_exception_text_in_logs` | n/a | 3 | 1 | F3 | ASSERTED — TODO (is `failure_fields` owed there?) |

**Totals so far: 25 rows.** SETTLED 7 · REFUTED 1 · OPEN 2 · PARTIAL 2 · ASSERTED 10 · TODO 3.

## Open claims, tier 2 first (so far)

No tier-2 row yet. Tier 1: R7B2-12 (P2-1 candidate), R7B2-07 (P3-1), R7B2-08, R7B2-04's exit code,
R7B2-18's `exit 256`, and everything marked TODO above.

## The four defaults — provisional recommendations

1. **Roster refusal exits 1** — ratify the non-zero; recommend a distinct code (3) because 1 is also the
   crash and `SystemExit(str)` code (R7B2-04). Low cost, one constant.
2. **Unset `EVAL_JUDGE_DEPLOYMENT_CLOUD` = `aws`** — ratify: every deployment is AWS and unset-refuses
   would break today's bedrock judge runs; require the runbook to name the variable. The endpoint half
   needs R7B2-12 tightened before the residency claim is honest.
3. **SCRAM verifier over log suppression** — ratify, measured: the password never reaches the server,
   the verifier logs the reader in, and suppression would still have left `log_statement` from the dump's
   own DDL.
4. **G.113 left `[~]`** — keep `[~]` until C4 (the live SAD run under `--cap-drop ALL`, R7B-43) since
   every M-SAD-AUTH property is still live-unproven; but fix the box's CORRECTION text, which still says
   "LIVE until g106 merges" after `75947461`.

**Merge-readiness verdict so far: NOT YET CALLABLE.** No P0/P1 found; one P2 candidate (R7B2-12,
reasoned not measured) and four P3s. The per-SHA greens, the merged-tree lanes and the mutation set are
unrun, so neither MERGE-CLEAN nor FIX-FIRST is proven. If the remaining work stays as read, the likely
verdict is **FIX-FIRST on R7B2-12 (one-line suffix tightening + one test case) or MERGE-CLEAN with
R7B2-12 recorded as owed**, at the controller's choice.
