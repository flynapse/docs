# Claims packet — copilot-mro r7b r2: the fix batch for review r7b

**Verdict: MERGE-CLEAN — P0 0 · P1 0 · P2 1 · P3 6.** The one P2 (R7B2-12, the bedrock endpoint suffix)
is owed as a fix-forward, not a merge blocker: r7b strictly improves on its base, which had no endpoint
check at all. The trial merge onto `obs-merge` `557a178f` has one trivial conflict (resolution in §Merge).

Independent adversarial review (Opus), 2026-09-22, second reviewer of this range. The first was killed by
a machine restart and filed nothing. This one was paused once by the owner and resumed. Read-only
against every code tree. Each of the 12 SHAs (the base plus 11 commits), `obs-merge` `557a178f` and the
trial merge were copied or cloned under
`~/.claude/scratch/obs-merge/r7b-review-r2/{ws,merge}/`. Each copy has the real history through
`objects/info/alternates`, so `HEAD` is the reviewed SHA and `git status` is clean. The five siblings are
**pinned archives with history** (`sib/SHAS.txt`: core-obsm `b730a95`, utils-obsm `179cc6d`, api-obsm
`2d49c3f`, flynapse-otel `df503c2`, dashboard-obsm `4a7714a`; three of them moved during the pause, so
every post-resume run uses these).

A `sitecustomize` (`site/`) guards every lane:

- It strips the api venv's primary-checkout `.pth` paths. Printed per lane:
  - `copilot_mro.__path__` is the copy only;
  - `copilot_mro.app.__file__`, `core`, `utils` and `flynapse_otel` all resolve inside the copy or the
    pinned archives;
  - psycopg2 is 2.9.12, libpq 170009.
- It refuses every non-loopback DNS lookup and connect, and every `docker`/`psql`/`pg_*`/`aws` exec.
  Each refusal is logged in `lanes/guard-*.log`, e.g. HEAD lane T: 805 DNS lookups for
  `oidc.ap-south-1.amazonaws.com` and IMDS, and 4 `which docker`.

No docker, DB write, network, AWS or Cognito call was made. Every test run went through `pytest-slot.sh`,
one at a time, at `-n 2` or less.

| range | commits |
|---|---|
| `67006780..afe79dbb` on `obs-merge-r7b` (11) | `8be6f663` P1-1 · `1c7db875` P3-1 · `81bd0942` P2-1+P3-2 · `e4d263d2` P3-6 · `298b8fb5` P3-5 · `63cd01d7` P2-3+P2-4 · `1f705234` P2-6 · `300a6fb2` P3-3 · `b63a03fd` P2-5 · `3ec66117` P2-2 · `afe79dbb` R7B-41 |

**Lane recipe** (`lane.sh`), from the copy's root:

- env: `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`;
- `PYTHONPATH=site:<copy>:sib/core-obsm:sib/utils-obsm:sib/api-obsm:sib/flynapse-otel`;
- command: `pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider --rootdir=<copy> -c <copy>/pyproject.toml`.

`rootdir` is the copy in every log.

---

## Lanes

**Lane T** = the 8 dirs holding the 19 touched test files: `tests/agent_sdk/core`, `tests/integration/otel`
and `tests/unit/{ad,agent_shared,data_discovery,lang_agent,metering,observability}`.

**Lane R** = the 19 touched test files plus `test_ad_notification_payload_contract`,
`test_sad_socket_auth_downgrade` and `test_langchain_ambient_surface_policy`, each only where it exists at
that SHA.

| lane | tree | result |
|---|---|---|
| **T**, `-n 2` | base `67006780` | 5332 passed, **12 failed**, 49 skipped |
| **T**, `-n 2` | HEAD `afe79dbb` | 5437 passed, **11 failed**, 49 skipped |
| HEAD T reds, serial | HEAD | the 11 ids: **11 passed**; their three whole files: **84 passed** — every HEAD red is xdist isolation |
| T red-set diff | base → HEAD | **gone:** `test_usage_ledger_write_guards::test_a_raising_write…` (R7B-41) and one `[deadline]` timing case. **New:** `test_lang_pilot_tool_runtime::test_the_assembly_reads_the_table_registry_three_times_not_eleven`, `assert 0 == 3` — the registry read went uncounted in that worker, i.e. a polluter swapped the registry module; green serially; absent on the merged tree (R7B2-27). **Common:** `test_debug_dumps` ×9 + `test_lang_sad_activation` ×1 |
| **R** per SHA, `-n 2` | base → `8be6f663` → `1c7db875` → `81bd0942` → `e4d263d2` → `298b8fb5` → `63cd01d7` → `1f705234` → `300a6fb2` → `b63a03fd` → `3ec66117` → `afe79dbb` | passed **546 → 553 → 554 → 570 → 570 → 570 → 585 → 608 → 609 → 637 → 650 → 651** (below) |
| **U** = union extras `tests/architecture`, `tests/unit/{infra,agent_claude,memory,scripts}` | base and HEAD | **identical: 666 passed, 7 failed** (below); r7b touches nothing here |
| **T**, `-n 2` | `obs-merge` alone `557a178f` | 5460 passed, 11 failed: the pre-existing 10 plus one `[deadline]` timing case |
| **R** | **merged `a041b82c`** | **661 passed, 0 failed** |
| **T**, `-n 2` | **merged `a041b82c`** | **5565 passed, 10 failed**: exactly the pre-existing xdist 10. Its reds are a subset of `557a178f`'s, and it passes +105. **The merge adds no red** |

**Lane R, red ids.** Each SHA shows the same two pre-existing ids, and only the first remains at
`afe79dbb`:

- the R7B-41 test, which `afe79dbb` fixes;
- `test_langchain_ambient_surface_policy`, red at the base and fixed on `obs-merge` by `16d5d1d1`.

**No commit turns anything red.**

**Lane U, red ids:**

- `test_cross_repo_reads_name_their_checkout` ×5 and `test_root_anchoring::test_sibling_repo_reaches…`.
  These are scratch-layout artefacts: the tests read the real workspace listing.
- The ambient policy.

**Union claim (6072 → 6179 passed; 5F+10E → 4F+8E, all pre-existing).** The implementer's 13-dir set is
recorded nowhere I could find. My 13-dir union (T + U) reads **5998 → 6103 passed (+105; theirs +107)**,
with 19 → 18 failed. HEAD's reds are a subset of the base's, plus the registry victim above. Every red
is pre-existing, a harness artefact or xdist isolation. **The "all pre-existing" half is SETTLED. Their exact
counts are ASSERTED.**

## Mutation proofs

Method: `mutant.sh` for every mutant, with:

- a green baseline first;
- a cold bytecode cache;
- one mutant at a time through the slot;
- every restore md5-checked against `git show <sha>:<path>` — **all MATCH**.

Log: `~/.claude/scratch/obs-merge/r7b-review-r2/mut/results.txt`, plus `batch1.log`, `batch2.log` and
`batch_merged.log`. The old/new text pairs sit beside it.

| group | mutants (at HEAD unless marked) | result |
|---|---|---|
| P3-6 password | PW-M1 bind the plaintext (via the probe, and via the committed test alone) · PW-M2 `md5` verifier · PW-M3 another user name | **KILLED ×3**. PW-M3 survives and is **equivalent**: a SCRAM verifier does not bind the user |
| P2-1 SCRAM pin | SCM2 a second `--env POSTGRES_INITDB_ARGS=--auth=trust` · SCM1 a later `-e POSTGRES_HOST_AUTH_METHOD=trust` · SCM1b `-itePOSTGRES_HOST_AUTH_METHOD=trust` · **PINALONE**: the duplicate refusal removed AND a second `--auth=trust`, aimed at the pin test only | **KILLED ×4**. The pin alone catches the review's M2 |
| P3-2 argv reader | ARM1 `--env-file` allowed · ARM2 duplicate check off · ARM3 short-group parsing off · ARM4 `-e=X` unstripped | **KILLED ×4** |
| P2-3/P2-4 G.113, production plants in `_grant_reader` | P1 `execute_values(…, [(reader_password,)])` · P2 `.format_map({"k": reader_password})` · P3 an f-string with the pragma inside the string · P4 an f-string plus a real reasoned pragma · P5 `execute_batch` · **M12b**: the full revert to `sql.Literal(reader_password)` plus three reasoned pragmas, aimed at the guard, and separately at the SAD reader test alone | **KILLED ×7** |
| G.113 guard-self | G1 pragmas read from raw lines · G2 `execute_values` dropped from `_BATCH_HELPERS` · G3 `format_map` dropped from `_STRINGIFYING` | **KILLED ×3** |
| P1-1/P3-1 roster | P11 a failed read returns `[]` · P11i a failed import returns `[]` · P31 the offset reader back | **KILLED ×3** |
| P2-5 residency | RES1 endpoint check removed · RES2 `azure` back on the aws catalogue · RES3 `_AWS_HOST_SUFFIXES = (".com",)` | **KILLED ×3**. RES3 dies only because `.com` admits `api.openai.com`: the committed cases hold the vendor-domain line, not the account line (R7B2-12) |
| P2-6 healthcheck | HC1 `\|\| true` · HC2 `echo curl …` · HC3 `-f` dropped · HC4 `\|\| exit 0` · HC6 `; exit 0` · **HC5 `\|\| exit 256`** | **KILLED ×5**. **HC5 SURVIVES, including the full `tests/integration/otel` lane (P3-4)** |
| P2-2 G.6 call sites | G6M1 orchestrator · G6M3 Claude composition `None` · G6M3l lang composition `None` · G6M4 lang backend `None` · G6M5/6/7 `llm_usage` unbound/failed/refused · G6M8 budget-refusal unbound | **KILLED ×8**. All nine of the review's G6M1–M9 are dead: G6M2 by the committed adapter test; G6M9 = G6M1 + G6M4, each killed by an independent file |
| G.6 inventory | CWM1 `record_subagent` dropped from `CALLBACK_WIRED` · CWM2 `_bound_in` always True | CWM1 **KILLED**. **CWM2 SURVIVES, including the full otel lane plus `test_composition_root.py`.** The static "both builders bind it" limb is redundant with the behavioural composition test, which kills G6M3/G6M3l. Defence in depth, not a gap |
| P3-5 order | P35: `main`'s teardown uninstruments nothing, with the lifecycle file run BEFORE the SAD reader file | **KILLED** |
| **merged `a041b82c`**, obs-merge's `OTEL_SDK_DISABLED=true` session pin in force | G6M1, G6M3, G6M4, G6M5, G6M8, SCM2, P11, PW-M1 | **KILLED ×8**. The pin does not blind the four new metric tests: each patches the switch off around provider construction |

**Tally: 55 runs — 50 KILLED, 5 SURVIVED, which are 3 distinct mutants** (PW-M3 equivalent; HC5 = P3-4 and CWM2 = a redundant limb, each also re-run against its full lane).
They cover every family the implementer names: G6M1–M9, SCRAM M1/M2/M2b, G11M1–M4, the G13M1/M2 class,
M12b and the G49M4 class. Their own list of 52 was recorded nowhere, so this is a re-proof **by family,
not by id**.

---

## Findings, ranked

### P2-1 — The bedrock endpoint check admits any AWS-hosted endpoint in ANY account, which is exactly the "pointed at a proxy" case it names (P2-5 / M-RESIDENCY) — R7B2-12

`contracts.py:121` `_AWS_HOST_SUFFIXES = (".amazonaws.com",)`, and `:202-208` `_is_in_account_host("bedrock", h)`
is `h.endswith(".amazonaws.com")`. `require_in_account_endpoint`'s docstring names its target:
*"`AWS_ENDPOINT_URL` pointed at a proxy … sends the judge's input there under an in-account name"*. An
AWS-hosted proxy is the one proxy the suffix cannot see.

**Measured** (`probes/test_r2_probe_residency.py`, 21/21 at HEAD). `validate_judge_provider("bedrock")`
**admits** each of these; none is Bedrock, and none is shown to be in the deployment's account:

- `AWS_ENDPOINT_URL_BEDROCK_RUNTIME=https://abc123.execute-api.us-east-1.amazonaws.com/prod`, an API Gateway
  in any account that forwards to any SaaS;
- `AWS_ENDPOINT_URL=https://exfil-alb-1234.us-east-1.elb.amazonaws.com`, an ALB;
- `http://ec2-3-4-5-6.compute-1.amazonaws.com:8080`, an EC2 public name;
- `https://s3.amazonaws.com`.

The committed negative cases (`test_an_endpoint_outside_the_account_is_refused`, 8 cases) hold only the
vendor-domain line (`bedrock.amazonaws.com.evil.example`, `api.openai.com`), and RES3 shows that.

The same probe also shows the check's reach:

- **Admitted:** an Azure OpenAI resource in any tenant (`*.openai.azure.com` names a resource, not an
  owner); a single-label or `.internal` name, which a resolver can CNAME anywhere.
- **Not read:** `HTTPS_PROXY` (with `AWS_CA_BUNDLE`, a MITM) and `AWS_PROFILE`, which can name another
  account.
- **Falsely refused:** a trailing-dot FQDN, and `100.64.0.1` (CGNAT/Tailscale).

**Scenario.** An operator points the judge at a "Bedrock-compatible" gateway on API Gateway, which is a
common vendor pattern. The run passes both residency seats, and client production content leaves the
account. That is ruling 11 broken, with the refusal machinery claiming otherwise.

**Why P2, not P1.** It is not a regression (the base had no endpoint check). It needs an operator to set
an override (no deployment sets one today, and the runbook invokes the default endpoint). The commit and
the runbook are honest about the check being `*.amazonaws.com`, though the headline says "in-account".

**Fix (small).**

- For bedrock, require `^bedrock-runtime(-fips)?\.[a-z0-9-]+\.amazonaws\.com$`, or a
  `*.bedrock-runtime.<region>.vpce.amazonaws.com` interface-endpoint host, and refuse the global
  `AWS_ENDPOINT_URL` unless it has that shape.
- Refuse a set `HTTPS_PROXY`/`HTTP_PROXY` for the judge process, or name it in the docstring as out of
  scope.
- For azure, the host cannot prove the tenant. Require the resource name to match a deployment-declared
  value, or say so.
- Add the four AWS-hosted cases above as refusals.

Tier 1, severity 1 (guard integrity).

### P3-1 — Collapsing onto core's walk dropped the "no `total` = unverifiable" refusal; the commit says the case moved to core's suite, where core pins the OPPOSITE — R7B2-07

The base `_active_tenant_recipients` refused a reader that reported no `total`
(`test_a_reader_that_reports_no_total_is_refused_as_unverifiable`; mutant G49M3 was red in review r7b).
`1c7db875` deleted that test with the words *"the offset-only cases (… missing total) belong to core's
suite now"*. Core's `iter_all_tenants` **accepts** a never-counting reader by contract
(`core tests/unit/db/test_tenant_registry_enumeration.py::test_a_reader_that_never_counts_degrades_to_cursor_semantics`).

**Measured** (`probes/test_r2_probe_registry.py`, 9/9):

- A 437-tenant registry whose reader reports no count AND truncates at 120 is **served as 120 with no
  refusal**.
- A row without a `tenant_id` under the same reader is dropped silently. With a count, it is refused.

Core's real `list_tenants_page` computes the count in the same statement, so the exposure needs a
non-core reader (a double, a future variant, a monkeypatch). **Fix:** a `require_count=True` on
`list_all_tenants` that the dispatcher passes, or the commit/docstring claim withdrawn.

### P3-2 — A reader that returns the wrong TYPE crashes instead of refusing — R7B2-08

`ad_notification_dispatcher.py:1233-1241` checks only `tenants is None`. A `list_all_tenants()` that
returns a dict raises `AttributeError` from `tenant.get` (measured). That lands in the evaluate CLI's
UNEXPECTED branch (a traceback and exit 1), not the REFUSED path. It is fail-closed, and a generator is
accepted.

### P3-3 — `EXIT_DISPATCH_REFUSED = 1` is also the crash status — R7B2-04

`evaluate_ad_applicability.py:713`. An uncaught exception, the `SystemExit(str)` at `:112`/`:615` and a
refusal all exit 1. An unattended schedule cannot tell "verdicts committed, nobody told" from "crashed".
A distinct code (3) costs one constant.

### P3-4 — The healthcheck parser accepts `|| exit 256`, which the shell exits 0 — R7B2-18

`test_grafana_service_health_and_env.py:139-144` accepts `|| exit <digits>` when `int(...) != 0`.
Planting HC5 in `deployment/docker-compose.yml` **survives the full otel lane**. Fix:
`int(tail[2]) % 256 != 0`.

The other five decoys (HC1–4, HC6) are red. Statically, a probe with a redirect such as `2>/dev/null` is
falsely refused, which is safe.

### P3-5 — The dispatch-failure site was converted to class-only, below the ruled M-TRACEBACK shape — R7B2-25

`evaluate_ad_applicability.py:931-937` logs `"… failed (%s) …", type(exc).__name__`: the class without
the frame headers. The ruled shape is `failure_fields` (class plus frames). The M-TRACEBACK lane tbD
(`38e27153`) converts the SAME site to `extra=failure_fields(exc)`, so this resolves at the tbD merge if
that side is taken there (§Merge).

### P3-6 — Merge process: `afe79dbb` duplicates `obs-merge`'s `ea55eb55` (the one conflict), and r7b pre-conflicts tbD — R7B2-21/26

- `afe79dbb` (R7B-41) and `ea55eb55` (test hygiene 5.7) rewrote the same test to the same five assertions.
  The only difference is the leak check's scope: the whole record here, message plus extra there. Both
  also assert `exception is None`.
- A git-only trial merge of tbD `38e27153` onto `a041b82c` conflicts in 3 files. Resolution is below.

---

## Merge-time resolution (for the controller)

**r7b into `obs-merge` (tested at `557a178f`).** `git merge --no-ff obs-merge-r7b`. There is **one**
textual conflict, `tests/unit/metering/test_usage_ledger_write_guards.py`. Take **obs-merge's side
whole**:

`git checkout --ours tests/unit/metering/test_usage_ledger_write_guards.py && git add tests/unit/metering/test_usage_ledger_write_guards.py`.

`afe79dbb` is that file's only r7b change and is a duplicate of `ea55eb55`. The other 5 double-touched
files auto-merge:

- `CATALOGUE.md`
- `test_grafana_dashboards.py`
- `test_sad_reader_password_off_spans.py`
- `_mro_exception_text_debt.py`
- `test_phase1c_nonagent_scope_guard.py`

My merge commit is `a041b82c` (parents `557a178f`, `afe79dbb`), **tree `a70f7b04db97ccc762ba58b9fb438a805588740f`**.
If `obs-merge` is still at `557a178f`, the controller's merge must produce that same tree. Merged lanes:
R 661/0, T 5565/10 (pre-existing), 8/8 merged mutants killed.

**Later, when tbD merges (advisory; measured git-only).** Three conflicts:

1. **`scripts/ad/evaluate_ad_applicability.py` `_post_commit_side_effects`.**
   - Keep r7b's `except roster_refusal:` block whole.
   - In `except expected_dispatch_failures as exc:`, keep r7b's message: `"transition notification dispatch failed. " + _NO_CLEAN_REPLAY + " Re-running it also DUPLICATES any rows this dispatch already wrote before failing."`.
     Drop the `(%s)`/`type(exc).__name__` argument and add tbD's `extra=failure_fields(exc)`.
   - Keep `dispatch_line = f"FAILED ({type(exc).__name__}) — see log"`.
   - The `-> int` signature and `return EXIT_DISPATCH_REFUSED if dispatch_refused else 0` auto-merge.
2. **`tests/unit/observability/_mro_exception_text_debt.py`:** take tbD's side. The row is deleted:
   with tbD's four conversions and r7b's one, all five `logger.exception` sites and both printed-text
   sites are paid.
3. **`test_phase1c_nonagent_scope_guard.py`:** the union of both lists. This conflict comes from the cli
   merge, not from r7b.

---

## What I tried to break and could not

**The reader password (P3-6), with real libpq against the fake wire server** (probe 6/6, plus PW-M1/M2):

- A raw-byte tap on everything the client sent shows neither password on the wire. There is no `SHOW`
  round-trip, and `scram_iterations` from `ParameterStatus` (8192) is honoured.
- A CREATE ROLE that fails (`DuplicateObject`) leaks the password nowhere: not in the exception's
  text/args/`pgerror`/`diag`/`cursor.query`, the rendered traceback, the loguru sink, or the live and
  exported spans (class name only).
- A server holding ONLY the verifier logs the reader in over real SCRAM. It refuses a wrong password,
  and a neighbour's verifier refuses the right one.

**The roster refusal:**

- A page-2 failure, a page raising mid-iteration, a failed import and `None` all refuse, chained to
  nothing and without driver text.
- A genuinely empty registry yields `[]` and a clean batch (by design).
- Nothing upstream catches the refusal: two operator-run CLIs are the only callers, and no scheduler
  invokes them.

**The SCRAM pin:** the pin alone, with the production duplicate refusal removed, is red on a planted
`--auth=trust`. The oracle is independent of `_env_flag_values`.

**The argv reader:**

- Checked statically: a value containing a newline or `--` is consumed as a value; a case-different
  name is correctly not a duplicate; `--env --env-file` lands as a bare name and is refused.
- A valued letter before `e` errs to refusing.

**G.113:**

- Every rule the batch added is mutation-proved from the production side and from the guard side,
  including the review's surviving M12b.
- The one batch-helper site (`seed_corpus_attribution.py`) imports only `psycopg2`, `_common` and
  `fixtures.tenancy.rls_connections`, so no bootstrap.

**G.6:**

- Each runtime's tests run the real call site with the real `RuntimeTelemetry`/`InMemoryMetricReader`,
  and G6M1–M8 are killed at HEAD and again on the merged tree.
- `_call_sites` counts `ast.Call` only.

**Residency:**

- `EVAL_JUDGE_DEPLOYMENT_CLOUD` is `.strip().lower()`, so `AWS` and ` aws ` both mean aws. `self_hosted`,
  `selfhosted`, `on-prem` and `aws,azure` refuse.
- A userinfo trick (`…amazonaws.com@evil.example`) is refused.
- `https://evil.example\@bedrock-runtime…` parses to the Bedrock host in `urlsplit`, as it does in
  urllib3, so there is no client differential there.

**Runbooks:**

- `phoenix-evaluations.md`'s cloud table equals `IN_ACCOUNT_JUDGE_PROVIDERS_BY_CLOUD`, and it documents the
  `*.amazonaws.com` rule honestly.
- `oss-profile.md`'s `\set tenant '…'` plus `:'tenant'` is valid psql.
- The placeholder and runbook agree on `alertmanager/secrets/`.

**The trial merge:** the `OTEL_SDK_DISABLED=true` session pin does not blind the r7b metric tests (8
merged mutants killed).

## What I did not test

- **No docker**, so the container side of M-SAD-AUTH is still live-unproven (C4, R7B-43):
  - SCRAM on the written `pg_hba`;
  - postgres starting under `--cap-drop ALL`;
  - `PGREQUIREAUTH` in the image's libpq;
  - docker's duplicate-`-e` handling.

  `pg_hba`/initdb semantics were reasoned from source.
- `arize-phoenix-evals` is installed in no venv here, so which endpoint variables its bedrock, azure and
  ollama clients actually read is unverified. The code reads the union of the conventional spellings.
- The implementer's exact 13-dir union and their 52 mutant ids were not recorded, so I re-proved by
  family.
- `tests/db`, `tests/e2e` and `tests/api` (bans and scope), and the docker-gated `TestTheRunningStack`
  cases (skipped under the guard).
- tbD's merge was trialled git-only, with no lanes. tbA/tbB/tbC were not trialled.

---

## Claims table

Severity: 0 = a content leak that ships · 1 = guard or lock integrity · 2 = a coverage gap · 3 = docs or
process.

Tier (§2.3a): 0 = settled by a guard I SAW fail · 1 = consequential, reversible · 2 = irreversible or
estate-shaping.

Chunk: F1 contract + privacy · F2 the merge · F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R7B2-01 | copilot-mro | `data_discovery/environment.py:534-543` (`e4d263d2`) | reader role created from a client-derived SCRAM verifier (`encrypt_password(…, "scram-sha-256")`), bound | a failed CREATE ROLE is logged with its statement | raw-byte tap: password never on the wire; no SHOW; the verifier logs the reader in via real libpq; wrong/neighbour refused; `scram_iterations` honoured | `test_the_role_is_created_with_the_verifier_of_its_password_and_never_the_password` | **yes**: PW-M1 (committed test alone) and PW-M2 KILLED, also on the merged tree; PW-M3 equivalent | 0 | 0 | F1 | SETTLED |
| R7B2-02 | copilot-mro | same, failure path | a failed CREATE ROLE leaks nothing | — | `DuplicateObject`: exception text/args/pgerror/diag/cursor.query/traceback/loguru/spans are all password-free; the span carries the class only | my probe (no committed failure-path test) | n/a | 0 | 1 | F1 | SETTLED (probe) |
| R7B2-03 | copilot-mro | `ad_notification_dispatcher.py:1200-1231` (`8be6f663`) | a failed page or import raises `TruncatedTenantRegistryError` after the handler, class name only | `[]` was permanent loss blamed on the tenant | page-2, mid-iteration, import and `None` all refuse, chained to nothing | `TestRefusals`, `TestTheRefusalReachesTheCaller`, `TestTheEvaluateCliSeesTheRefusal` | **yes**: P11, P11i KILLED (P11 also merged) | 1 | 0 | F3 | SETTLED |
| R7B2-04 | copilot-mro | `scripts/ad/evaluate_ad_applicability.py:713,893-928` | `except roster_refusal` → REFUSED, `EXIT_DISPATCH_REFUSED = 1`; `except ()` until imported | non-zero for an unattended schedule | committed CLI tests with the real dispatcher plus a planted one; P11 red | same | yes (P11) | 1 | 0 | F3 | SETTLED · **P3-3: code 1 collides with the crash status** |
| R7B2-05 | copilot-mro | `scripts/ad/dispatch_ad_notifications.py:310-314` | the batch CLI's blanket catch exits 1 on the refusal | — | read: `except Exception` → `format_exc()` (the refusal is unchained, so class and frames only) → `return 1` | `test_a_page_two_failure_refuses_the_batch…` (raises through `process_batch`) | n/a | 1 | 1 | F3 | ASSERTED (read) |
| R7B2-06 | copilot-mro | `ad_notification_dispatcher.py:1216-1241` (`1c7db875`) | the roster = core's keyset `list_all_tenants()`; offset pager deleted | insert+delete skew | core's walk runs for real over a one-page double; the insert+delete probe is a committed test | `test_an_insert_and_a_delete_between_pages_skip_nobody`, `TestNoCallerReadsTheRegistryByOffset` | **yes**: P31 KILLED | 2 | 0 | F3 | SETTLED |
| R7B2-07 | copilot-mro | same | "missing total belongs to core's suite" | — | **REFUTED**: core accepts a never-counting reader; no-total plus truncation served 120/437 with no refusal (probe) | none (the base test was deleted) | n/a | 2 | 1 | F3 | REFUTED — **P3-1** |
| R7B2-08 | copilot-mro | same `:1233-1241` | `tenants is None` is the only type check | — | a dict raises AttributeError (the UNEXPECTED branch); a generator is accepted (probe) | none | n/a | 3 | 1 | F3 | OPEN — **P3-2** |
| R7B2-09 | copilot-mro | `environment.py:64-98` (`81bd0942`) | `_env_flag_values` reads every pflag spelling; `--env-file` refused; duplicates refused | P2-1/P3-2 | every spelling traced; newline/`--` values consumed as values | `test_an_env_file_is_refused…`, `test_a_name_stated_twice…`, the 7-spelling bare-name cases | **yes**: ARM1–4 KILLED | 1 | 0 | F1 | SETTLED |
| R7B2-10 | copilot-mro | `test_sad_environment_failures_withhold_secrets.py:418-443` | the SCRAM pin reads the EFFECTIVE value through its own oracle, each name once | membership let `trust` back | the oracle is independent of production | `test_the_container_is_initialised_with_scram_on_every_line` | **yes**: SCM1, SCM1b, SCM2, **PINALONE** KILLED (SCM2 also merged) | 1 | 0 | F1 | SETTLED |
| R7B2-11 | copilot-mro | `agent_evaluation/contracts.py:64-97` (`b63a03fd`) | catalogue and per-cloud map pinned by equality; union == catalogue; unset cloud = `aws` | `litellm` passed the denylist | read and run | `test_the_in_account_catalogue_is_pinned_by_equality` | **yes**: RES2 KILLED | 1 | 0 | F1 | SETTLED |
| R7B2-12 | copilot-mro | `contracts.py:121,202-208` | endpoint variables that are SET must name an in-account host | residency = where the content goes | **MEASURED** (probe 21/21): ADMITS API Gateway / ALB / EC2 / S3 hosts under `.amazonaws.com` in any account, and an Azure resource in any tenant; `HTTPS_PROXY`/`AWS_PROFILE` unread; trailing dot and `100.64.0.1` falsely refused | `test_an_endpoint_outside_the_account_is_refused` (8 cases, none AWS-hosted) | RES1/RES3 killed, but no case covers another-account AWS hosts | 1 | 1 | F1 | OPEN — **P2-1** |
| R7B2-13 | copilot-mro | `contracts.py:117-128` | `EVAL_JUDGE_DEPLOYMENT_CLOUD` normalised; an unknown value refuses every provider | — | probe: `AWS`/` aws ` → aws; `self_hosted`, `on-prem`, `aws,azure` refuse | `test_an_unknown_deployment_cloud_refuses_every_provider` | n/a | 1 | 1 | F1 | SETTLED (probe) |
| R7B2-14 | copilot-mro | `tests/integration/otel/test_emitted_series_inventory.py:126-216` (`3ec66117`) | `_call_sites` = `ast.Call` only; `CALLBACK_WIRED` defers to 3 behavioural files plus both builders binding | a bound reference counted as WIRED | read and run | itself | CWM1 KILLED; **CWM2 survives the full lane**: the static binding limb is redundant with `test_composition_root.py` (which kills G6M3/G6M3l) | 1 | 0 | F1 | SETTLED (CWM2 = redundant limb) |
| R7B2-15 | copilot-mro | `tests/agent_sdk/core/test_agent_sdk_subagent_metric.py`, `tests/unit/lang_agent/test_lang_subagent_metric.py`, `test_composition_root.py:940-996` | real `RuntimeTelemetry` + `InMemoryMetricReader` on both runtimes and the composition | G6M1-M4 and M9 survived | Claude drives `orchestrator.py:3563`; lang drives `backend.py:978` | themselves | **yes**: G6M1, G6M3, G6M3l, G6M4 KILLED at HEAD; G6M1/3/4 on the merged tree under the session pin | 1 | 0 | F1 | SETTLED |
| R7B2-16 | copilot-mro | `tests/unit/agent_shared/test_ledger_and_subagent_metric_wiring.py` | failed/refused/unbound `llm_usage` and unbound budget refusal book `agent.ledger.write_failures` | G6M5-M8 | 5 new tests | themselves | **yes**: G6M5–8 KILLED (G6M5/8 also merged) | 2 | 0 | F1 | SETTLED |
| R7B2-17 | copilot-mro | `tests/unit/observability/test_no_secret_in_sql_text.py` (`63cd01d7`) | Rule I reads `execute_values`/`execute_batch` query+argslist+template; `format_map` caught; pragmas = COMMENT tokens; `PRAGMA_REGISTER` empty by equality; the batch site pinned | P2-3/P2-4 | read and run | itself | **yes**: G113 P1–P5, M12b (twice), G1–G3 KILLED | 1 | 0 | F1 | SETTLED |
| R7B2-18 | copilot-mro | `tests/integration/otel/test_grafana_service_health_and_env.py:60-165` (`1f705234`) | the probe is lexed and judged | four decoys passed before | HC1–4 and HC6 red; **HC5 `\|\| exit 256` survives the full otel lane** | 23 parametrised cases | partial (5/6) | 2 | 0 | F3 | PARTIAL — **P3-4** |
| R7B2-19 | copilot-mro | `tests/unit/observability/test_nonagent_lifecycle_spans.py:26-64` (`298b8fb5`) | `main` uninstruments what its import newly instrumented | order fragility | the pair in explicit order is green at HEAD | itself + `test_sad_reader_password_off_spans.py` | **yes**: P35 KILLED | 2 | 0 | F1 | SETTLED |
| R7B2-20 | copilot-mro | placeholder, `frontend.json` panel 18, `oss-profile.md`, `test_grafana_dashboards.py` (`300a6fb2`) | placeholder names the git-ignored secrets dir; `:158-159`; `\set tenant`; catalogue == board browser signals | fix-pass leftovers | read; `\set`/`:'tenant'` valid psql; runbook and placeholder agree | `test_the_webhook_placeholder_sends_the_owner_where_the_runbook_does`, the equality in guard 2 | not mutated | 3 | 1 | F3 | ASSERTED (read) |
| R7B2-21 | copilot-mro | `tests/unit/metering/test_usage_ledger_write_guards.py` (`afe79dbb`) | R7B-41 test pins the M-TRACEBACK shape | stale red | the same fix is on obs-merge as `ea55eb55`; five identical assertions; the trial merge's ONE conflict | itself | n/a | 3 | 1 | F2 | SETTLED — redundant (**P3-6**); take `--ours` |
| R7B2-22 | copilot-mro | trial merge of `afe79dbb` onto `557a178f` → `a041b82c`, tree `a70f7b04…` | — | — | one conflict (R7B2-21); merged R 661/0; merged T 5565/10 (reds ⊆ `557a178f`'s); 8 merged mutants KILLED | the merged lanes | yes (8/8) | 1 | 0 | F2 | SETTLED |
| R7B2-23 | copilot-mro | each SHA; the union claim | green at each SHA; 6072 → 6179, all reds pre-existing | — | R monotone 546 → 651, the same two pre-existing reds; union (my 13 dirs) 5998 → 6103 (+105 vs their +107); HEAD reds ⊆ base reds + one xdist victim | lanes R, T, U | n/a | 3 | 1 | F3 | SETTLED (green, pre-existing) · counts ASSERTED (their dir set unrecorded) |
| R7B2-24 | copilot-mro | the implementer's 52 mutants | killed | — | re-proved by family: 55 runs, 50 KILLED, 3 distinct survivors (1 equivalent, HC5, CWM2) | — | — | 3 | 1 | F3 | SETTLED (by family) |
| R7B2-25 | copilot-mro | `evaluate_ad_applicability.py:931-937` + `_mro_exception_text_debt.py` 5 → 4 | the failed-dispatch log names the class only | M-TRACEBACK | class WITHOUT frames, below the ruled shape; tbD `38e27153` converts the same site to `extra=failure_fields(exc)` | `test_no_exception_text_in_logs` (counts units, not shape) | n/a | 3 | 1 | F3 | OPEN — **P3-5** (resolves at the tbD merge) |
| R7B2-26 | copilot-mro | evaluate script, debt register, scope guard | (forward) merge order cli → r7b → tbA..D | — | git-only: tbD onto `a041b82c` conflicts in 3 files; resolution in §Merge | none | n/a | 3 | 1 | F2 | OPEN — **P3-6** (resolution recorded) |
| R7B2-27 | copilot-mro | `tests/unit/lang_agent/test_lang_pilot_tool_runtime.py:1352-1368` | counts registry reads | — | red once under `-n 2` at HEAD (`0 == 3`: a polluter swapped the registry module in the worker); green serially; absent at base, at `557a178f` and on the merged tree | itself | n/a | 3 | 1 | F3 | ASSERTED — pre-existing isolation class (census `b61d8400`), not r7b's |
| R7B2-28 | docs | plan G.113 box `[~]`; §4a-bis M-SAD-AUTH row | status | — | G.113's claim (the password off `db.statement`) is proved with the real instrumentor + real libpq and mutation (PW-M1, M12b, G113 P1–P5); the live dependency C4 belongs to M-SAD-AUTH; the §4a-bis row now states the built `--auth` value | none | n/a | 3 | 1 | F3 | OPEN — recommend **close G.113 `[x]` at the r7b merge**; keep C4 on M-SAD-AUTH |

**Totals: 28 rows.**

- **State:** SETTLED 18 (tier 0: 13) · PARTIAL 1 · ASSERTED 3 · OPEN 5 · REFUTED 1. R7B2-23 counts as
  SETTLED, with its numeric half asserted.
- **Mutants:** 55 runs, 50 KILLED, 5 SURVIVED (3 distinct; HC5 and CWM2 re-run on their full lane).
  - **KILLED 50:** PW ×3, SCM ×3 + PINALONE, ARM ×4, G113 ×10 (P1–P5, M12b ×2, G1–G3), P11/P11i/P31,
    RES ×3, HC ×5, G6M ×8, CWM1, P35, and 8 on the merged tree.
  - **SURVIVED 3:** PW-M3 (equivalent), HC5 and CWM2 (each also survives the full lane).

## Open claims, tier 2 first

**Tier 2:** none in this range. The standing tier-2 rows from review r7b that this batch does not touch
are R7B-06 and R7B-43, M-SAD-AUTH live-unproven (C4).

**Tier 1**

1. **R7B2-12 (P2-1).** The bedrock endpoint suffix admits another account's AWS hosts; proxies and the
   profile are unread. Fix-forward (small), before any deployment sets an endpoint override.
2. **R7B2-07 (P3-1).** The no-`total` refusal is gone and the commit's claim is refuted. Add a
   `require_count` on core's walk, or withdraw the claim.
3. **R7B2-18 (P3-4).** `|| exit 256`. A one-token fix: `% 256`.
4. **R7B2-08 (P3-2) and R7B2-04 (P3-3).** The wrong-type crash, and the colliding exit code.
5. **R7B2-25 / R7B2-26 (P3-5/P3-6).** Take tbD's `extra=failure_fields(exc)` at the tbD merge, per
   §Merge.
6. **R7B2-27.** An xdist registry-counting victim, pre-existing, fixed on obs-merge.

## The four defaults — recommendations

1. **Roster refusal exits 1.** Ratify the non-zero exit. Recommend a distinct code (e.g. `3`):
   `1` is also every crash and `SystemExit(str)` in the same script (P3-3). It is one constant, and the
   CLI tests pin `EXIT_DISPATCH_REFUSED` by name, so nothing else moves.
2. **Unset `EVAL_JUDGE_DEPLOYMENT_CLOUD` = `aws`.** Ratify:
   - every deployment is AWS;
   - an unset-refuses default would stop today's bedrock judge runs;
   - `azure` can only be admitted by an explicit declaration;
   - the narrowing variable cannot cross clouds (measured).

   The endpoint half needs R7B2-12 before the residency claim is fully honest.
3. **SCRAM verifier over log suppression.** Ratify, measured:
   - the password never reaches the server;
   - the verifier logs the reader in and refuses others;
   - suppression could not cover a `log_statement` set by the dump's own superuser DDL.
4. **G.113 left `[~]`.** Close it **`[x]` at the r7b merge**. What G.113 claims (the role password off
   `db.statement`) is proved without docker, by the real instrumentor over real libpq plus mutation. The
   remaining live dependency (C4: provisioning cannot start under `--cap-drop ALL`) is M-SAD-AUTH's,
   and stays open there.
