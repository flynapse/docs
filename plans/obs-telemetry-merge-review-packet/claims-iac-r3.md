# Claims packet: iac r3 (M-CLI-TELEMETRY, G.117 / M-G117-DEFAULT, C1.5, M-WEAVIATE-LEFTOVERS (a), M-LEGACY-PANELS)

This is an independent adversarial review (Opus), done 2026-09-21/22. It is read-only throughout. Each commit was taken
with `git archive <sha>` into the private scratch directory `scratchpad/iac-review-r3/at-<sha>/`. Four tests need a
git repo (they check tracked files and history), so the suite also ran in local `git clone --no-hardlinks` copies
(`clone-<sha>/`). Those copies matched their archive byte for byte, apart from `__pycache__`. Every mutation ran against
a separate clone at `d52e8b8` (`mut/`) through a runner that applies the edit, confirms it by grep, runs the suite
with a fresh `PYTHONPYCACHEPREFIX`, reverses the edit and md5-checks the file against `git show d52e8b8:<path>`. A file
the mutant created is checked for absence instead. After the last run, `git archive d52e8b8 | tar -d -C mut/` reported no
content difference, and `mut/`'s `git status` was clean. No real tree was edited, checked out or committed: `iac` is
still at `d52e8b8`, and its only untracked file is the pre-existing `poc_ec2_setup_ubuntu.sh`. No terraform, no AWS
call, no docker, no live stack.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `013dc89..d52e8b8` | iac | `/home/aditya/Code/iac` | `obs-merge` | `5f3380c` M-CLI-TELEMETRY iac half · `1c8c998` G.117 / M-G117-DEFAULT · `0df5c24` C1.5 iac sites · `97cae73` M-WEAVIATE-LEFTOVERS (a) aws half · `d52e8b8` M-LEGACY-PANELS aws panels |

## How it was run

- **Lane:** `DEBUG=false PYTHONPYCACHEPREFIX=<fresh> /home/aditya/Code/api/.venv/bin/python -m pytest -q -p no:cacheprovider`,
  from each clone's root.
- **Validators:** `bash scripts/validate_dashboards.sh`, `python scripts/validate_alarms.py` and
  `python scripts/validate_metric_vocabulary.py`, the three CI steps in `.github/workflows/terraform-plan.yaml`.
  Each one's own exit status was captured.

| commit | pytest | pytest exit | dashboards | alarms | vocabulary | rootdir |
|---|---|---|---|---|---|---|
| `013dc89` (base) | 243 passed | 0 | 0 | 0 | 0 | `…/iac-review-r3/clone-013dc89` |
| `5f3380c` | 246 passed | 0 | 0 | 0 | 0 | `…/clone-5f3380c` |
| `1c8c998` | 258 passed | 0 | 0 | 0 | 0 | `…/clone-1c8c998` |
| `0df5c24` | 261 passed | 0 | 0 | 0 | 0 | `…/clone-0df5c24` |
| `97cae73` | 262 passed | 0 | 0 | 0 | 0 | `…/clone-97cae73` |
| `d52e8b8` | 266 passed | 0 | 0 | 0 | 0 | `…/clone-d52e8b8` |

All five commits are green at their own HEAD, and the counts match the commit messages (243 → 246 → 258 → 261 → 262 →
266). (A run in the bare `git archive` copies gives 5 failed and 15 errors at every commit, the base included. Those are
the tests that need `.git`, not regressions.)

**Mutation harness.** 37 runs: 35 valid mutants, 1 control and 1 invalid run. The control (`W10b`) went red, as
designed. The invalid run (`L3`) was killed by the unbalanced `merge(` it introduced, not by the property; `L3b`, the
balanced version, replaces it. Of the 35, **18 went red and 17 survived.** The survivors are C2, D2, L5, L6, L7, L8, L9,
L11, V1, V2, V6, W1, W2, W3, W4, W9 and W10. Each one is mapped to a finding or a stated limit below. There were also 11
planted HCL traps, run directly against `tests/_hcl_blocks.py` (a probe, not mutants): 8 read correctly, 1 raised and so
fails closed (CRLF), and 2 read wrongly (T7, T8 → P2-2). The implementer's own 34 mutants were not re-run.

**Tier 0 is not empty in this file: 11 rows.** Under §2.3a, tier 0 is "anything a mutation-checked guard proves", and
these rows are additive config lines or scanner mechanics, each with a guard I saw go red. The decisions that rest on
judgment (the exemptions, the dialect premise, the panel label keys) are tier 1. Nothing in this range changes the
signal contract, so there is no tier 2.

---

## Findings, ranked

### No P0, no P1

Nothing ships broken. I checked each property the new guards name against today's HCL and the sibling trees, and each
holds:
- `LOGURU_DIAGNOSE = "NO"` is present, literal and applied on all three REQUIRED resources.
- The Weaviate security group really is attached to the Weaviate instance (`ec2.tf:6`). It admits 8080 and 50051 over
  TCP from `apprunner_sg` and `lambda_sg` (`ec2.tf:115-123`). App Runner egresses through the VPC connector
  (`apprunner.tf:115`). The demo compose publishes `50051:50051`. Both client groups allow all egress.
- The 15 panels are faithful CloudWatch-dialect translations of the oss queries.

The findings are guards that hold less than their docstrings and commit messages claim, plus one exemption whose
reasoning contradicts the rule that made its sibling REQUIRED.

---

### P2-1: The Weaviate reachability guard derives the client half and hardcodes the server half. Five shapes that produce exactly the connect timeout it is named for leave it green.

`tests/unit/networking/test_weaviate_ports_declared_and_admitted.py:22`, `:50-67`, `:70-84`. The commit message says the
security group each client "really sits in" is "derived … not listed". That is true of the client side: the Lambda's
`vpc_config` and App Runner's connector. The server side is a constant, `WEAVIATE_SG`. The admitted ports come from the
dynamic block's `for_each` list alone; the `content` block's `from_port` / `to_port` / `protocol` are never read.

| mutant | edit | result |
|---|---|---|
| W1 | Weaviate ingress `content`: `from_port = 8080`, `to_port = 8080` (so `for_each` still lists 50051, but only 8080 is ever opened) | **266 passed** |
| W2 | the same `content`: `protocol = "udp"` | **266 passed** |
| W3 | `aws_instance.weaviate_observability.vpc_security_group_ids = [aws_security_group.poc_replica.id]` | **266 passed** |
| W4 | App Runner `WEAVIATE_URL` host → `aws_instance.poc_replica.private_ip` | **266 passed** |
| W9 | App Runner `egress_type = "DEFAULT"`: the connector is unused, so the private IP is unreachable | **266 passed** |

Controls: W5 (gRPC port 50052), W6 (Lambda's gRPC key renamed), W7 (50051 dropped from `for_each`) and W8 (URL port
8081) each go red. The guard works on the half it derives.

**What an operator sees:** a green CI run, then a Weaviate connect timeout in production. That is the failure mode the
guard's own docstring names.

**Fix (small):**
- In `content`, require `from_port`/`to_port` to be `ingress.value` (or equal to the item) and `protocol` to be `tcp` or
  `-1`.
- Derive the host instance from the URL's `aws_instance.<X>.private_ip` interpolation, and assert that its
  `vpc_security_group_ids` names the security group being read.
- For App Runner, require `egress_type = "VPC"`.

---

### P2-2: `_hcl_blocks.Block.attributes()` drops quoted and parenthesised keys, so the Weaviate client scan fails open on a legal HCL spelling

`tests/_hcl_blocks.py:155-163`. `_named(match)` returns the offset of the key NAME (`match.start(group)`):
- For `"K" = v`, that offset is inside the string literal.
- For `("K") = v`, it is inside the parentheses.

`_top` (`:102-116`) never adds an offset that lies inside a string or at depth > 0, so both forms are silently
discarded. `_env_syntax`, whose "one lexical body" this module claims to share, reads all three key forms. For the same
text, `env_assignments` reports `WEAVIATE_URL` and `process_env` does not.

| probe / mutant | result |
|---|---|
| T7: `"QUOTED" = "1"`, `("PAREN") = "2"`, `COLON: "3"` in one `variables` map | only `COLON` is reported |
| W10: a new Lambda `reindexer` (added to REQUIRED, as a developer would) with `"WEAVIATE_URL" = …`, **no** `WEAVIATE_GRPC_PORT`, **no** `vpc_config` | **267 passed** |
| W10b: the same Lambda with the key unquoted (control) | 2 failed: both Weaviate checks |
| L10: `"LOGURU_DIAGNOSE" = "NO"` on App Runner | red. The loguru rule fails closed (a false failure) |

No `.tf` file quotes an env key today, so the gap is latent. Its direction depends on the guard: it fails **closed** for
LOGURU (a missing key is a failure) and **open** for the Weaviate scan (a missing key means "not a client").

**Fix:** test top-level membership at `match.start()` of the key token (the quote or the paren), not at the group
start. Add the two key forms to `test_hcl_blocks.py`'s `TRAPS`.

---

### P2-3: The `poc_replica` exemption rests on the image, which is the reasoning the App Runner REQUIRED entry rejects. Its ".env does not override it" half is unguarded.

`tests/unit/observability/test_loguru_diagnose_off_on_compute.py:93-97`. App Runner is REQUIRED because "this service runs
`:latest` with auto-deploy off, so an image built before that Dockerfile line keeps it on" (`apprunner.tf:81-83`). The
POC box has the same exposure, and it is exempted on the strength of the image:
- Its user data pulls `flynapse-api-ecr:latest` at boot (`poc_ec2_setup.sh:161`).
- The api Dockerfile line exists only on `api-obsm` (`obs-merge`, `Dockerfile:94`). The api checkout on `langgraph-merge`
  has no `LOGURU` line at all, and api publishes only from main/develop. So today's `:latest` lacks it.
- This repo owns a seat that would close it: the `.env` heredoc at `poc_ec2_setup.sh:191-214`, which the compose `api`
  service reads through `env_file`. KNOWN_ASSIGNMENTS in `test_shared_env_content_flags.py` already parses that
  heredoc.

L9 adds `LOGURU_DIAGNOSE=YES` to that heredoc, the one thing the exemption says does not happen, and gets **266
passed**.

**Exposure:** container stderr on the POC host (`docker logs`), not CloudWatch, and only while the POC box is up.
**Fix:** write `LOGURU_DIAGNOSE=NO` into the heredoc, and move `poc_replica` to a REQUIRED-by-user-data check read
through `env_assignments`.

---

### P3-1: The forwarder check reads `lambda_src/*.py` at the top level only, while the archive zips the whole directory

`test_loguru_diagnose_off_on_compute.py:141` uses `glob("*.py")`, but `alerting.tf:105` sets `source_dir = lambda_src`. L8
(`lambda_src/helpers/__init__.py` with `from loguru import logger`) → 266 passed. The exemption is true today: one file,
stdlib only, `python3.12`, no layers. Fix: `rglob`.

### P3-2: Classification blind spots beyond the one the docstring states

The docstring names one limit, "a type outside this list is invisible". The other two are not stated:
- `terraform_files` (`_hcl_blocks.py:180-187`) reads `*.tf` only. L5 (an ECS task definition in `*.tf.json`) → 266
  passed.
- A registry-sourced module creates resources this scan never sees. L6 (`source = "terraform-aws-modules/lambda/aws"`)
  → 266 passed.
- L7 (`aws_mwaa_environment`, which runs Python DAGs) is the stated limit, and it survives as stated.
- L4 (an ECS task in a local module) goes red, correctly.

Fix: read `*.tf.json` too, and fail on any `module` block with a non-local `source`.

### P3-3: The guard proves the configured env, not the applied one

L11 (`ignore_changes = [image_uri, environment]` on `s3_pdf_processor`, `lambda.tf:138-140`) → 266 passed: the new value
would never reach the existing function. No REQUIRED resource ignores its env today. Fix: forbid `environment` /
`source_configuration` in `ignore_changes` on a REQUIRED resource.

### P3-4: A WIRED note names a function that never existed

`dashboards/llm-agents.json.tftpl:39` names `_record_embedding_cache_metrics` as an emitter. utils' emitter is
`note_embedding_cache_hits` (`utils-obsm/utils/llm.py:1337`), and `git log -S` finds no commit that ever added the other
name to `utils/llm.py`. The name was copied from utils' own declaration (`legacy_families.py:310,319`) and copilot-mro's
`_emitted_series.py:186,188`, so the fix belongs upstream as well as here. `check_state_notes` checks that an emitter is
named, not that it exists.

### P3-5: The legacy rows' label keys and values are unguarded

Check 7 reads log widgets only, and deliberately (`validate_metric_vocabulary.py:1352-1360`). Three mutants pass all four
checkers: V1 (`"token_type"` → `"token.type"`), V2 (`"tenant_id"` → `"tenant.id"`, the log-bridge spelling, which is wrong
for a metric) and V6 (`"outcome"="failed"` → `"failure"`).

I checked every key and value by hand, and all are right:
- `model`, `status` (success|error), `token_type` (input|output|total) and `tenant_id`, per `legacy_families.py`.
- `reason`, `error_kind`, `failure_code`, `parser_route`, `file_kind`, `source_scope` and `notification_type`.
- The literals `failed` / `succeeded` (`processing.py:544-552`, `cleanup.py:450-472`) and `created` / `failed`
  (`notifications.py:113,128`).
- The shim writes metric attributes verbatim. The `tenant_id` → `tenant.id` remap is the log bridge's, not the
  registry's.

This is the same limit the agent row lives with (its "`\"error\"` matches nothing" line is hand-checked too).

### P3-6: The platform-health header now contradicts its own foot row

`platform-health.json.tftpl:7` still says "the selectors below carry NO Prometheus suffix" and "the widgets below read the
estate's OTLP log group". The new row at `:51` is a metric panel whose selectors carry `_total`. The llm-agents header
gained the "legacy row … is the one exception" sentence; its sibling did not. (The docstring-family pattern again.)

### P3-7: The CLI bullet states a producer from another branch in the present tense

`llm-agents.json.tftpl:7` says the CLI's per-call detail "arrives as log records under `service.name=claude-code`". The
producer (`claude_cli_telemetry.py:92`, copilot-mro `cb5d309d`) exists only on copilot-mro `obs-merge-cli`; `cb5d309d` is
not on copilot-mro `obs-merge`. The bullet carries no state marker, so the validator's grammar check does not engage.
Merge the cli branch first or with this range, or mark the bullet WIRED with "retrieval unproved".

### P3-8: The CLI pattern misses two spellings

`test_cli_metrics_stay_off.py:37` misses:
- a regex matcher that spells the family with `.` for `_` (C2, `{__name__=~"claude.code.*"}` → 266 passed);
- a prefixed exported name (`\b` needs a word boundary before `claude`).

Both are contrived. It is noted for completeness, not worth code on its own.

---

## What I tried to break and could not

- **A double suffix under `FAMILY_SUFFIXED_INSTRUMENTS`.** All 15 names are declared WITH `_total` in utils'
  `FAMILIES`, and `flynapse_otel.registry.counter` → `_register_full` (`registry.py:159-160`, `:210-236`) registers the
  name verbatim. So `_total` is part of the OTLP instrument name: no suffix is added on top, and none is stripped.
  copilot-mro's `LEGACY_SERIES` holds the same 18 names. The exemption is exact:
  - V4 (the `_total` stripped from a board) red;
  - V5 (an entry the surface never addresses) red;
  - V3 (the oss `embedding_cost_usd_count`) red;
  - V7 (the `_seconds` unit entry dropped) red;
  - the suite's own `_total_total` case red.
- **The CloudWatch dialect of the 15 panels.** Each is the `9900a933` oss query with the Prometheus family spellings
  translated to native-histogram form:
  - `…_seconds_bucket` → `histogram_quantile` over `{"llm_request_duration"}` /
    `{"document_hub_processing_duration_seconds"}`;
  - `embedding_cost_usd_count` → `histogram_count(increase({"embedding_cost_usd"}[1h]))`.

  "Retrieval unproved" and "no CloudWatch canary (gate B1a)" are stated on both rows. The "seven" oss alerts are seven
  (counted in `flynapse-pipeline-alerts.yml`). The 900-second ceiling is `DOCUMENT_HUB_PROCESS_MAX_RUNTIME_SECONDS`.
- **The unpriced-embedding companion.** `embedding_requests_total` is always written with `status=success`, and
  `embedding_cost_usd` only when a price exists (`llm.py:1260-1273`). So requests minus `histogram_count(cost)` is exactly
  "billed calls with no recorded price".
- **LOGURU REQUIRED fails closed.** All of these went red or read empty:
  - L1 (lowercase `no`), L2 (from a variable), L3b (`merge(...)`) and L10 (quoted key);
  - T10 (a dynamic `environment` block);
  - G1 (the gateway task running the api ECR image);
  - L4 (a new ECS task in a local module).
- **The exemptions, checked against the sibling trees:**
  - forwarder: one stdlib file, no layers;
  - gateway: pinned collector and Phoenix tags. The root never instantiates the module; only `examples/basic` does;
  - Weaviate EC2: collector, Weaviate and its UI, plus the Phoenix override. No host Python runs from the service unit
    or the restart script;
  - gpu host: `vllm/vllm-openai`, digest-pinned, the only image.

  The Cognito Lambda claim is true: `lambdas/cognito-lambdas/app.py` uses loguru, and its Dockerfile sets no `LOGURU_*`.
- **An override of the env value.** Every value is a literal, with no tfvars path, and no `ignore_changes` on env
  anywhere today.
- **50051.** It is utils' default (`config.py:190`). utils dials gRPC on the host of `WEAVIATE_URL`
  (`ConnectionParams.from_url`, `weaviate_service.py:517-521`). The demo compose publishes `50051:50051`.
- **`weaviate.connect`.** It is a `SpanKind.CLIENT` span named `weaviate.{operation}` (`weaviate_service.py:140-141`,
  `:500`).
- **HCL traps against `_hcl_blocks`.** These all read correctly:
  - an indented heredoc whose body holds quotes and braces;
  - `jsonencode({ a = "}", … "${var.x}}" })` inside an env map;
  - `%{ if }…%{ endif }` directives with a nested quoted `"}"`;
  - block and line comments holding quotes, braces, `${` and `$${`;
  - `"$${"` at a string's end, `$$$${`, and `%%{`;
  - one-line nested blocks with comma-separated keys;
  - a heredoc terminator lookalike.

  Scanner mutants H1 (the depth filter removed) and H2 (`closing()` ignoring strings) went red.
- **`terraform fmt` alignment, reasoned only (terraform is banned).** hclwrite closes an alignment chain at a
  comment-only line. Each new `LOGURU_DIAGNOSE` line is a single attribute after a comment, and the two `WEAVIATE_*`
  lines are aligned as a pair.

## What I did not test

- Any terraform (`fmt`, `validate`, `plan`): banned. So I did not check whether a `runtime_environment_variables` change
  redeploys App Runner's `:latest` at apply.
- Live CloudWatch. Whether Query Studio accepts `unless … offset`, native-histogram functions on these names, and the
  stored temporality (B1a) are all unverified.
- Label VALUE stringification for copilot-mro's `(str, Enum)` statuses on their way through the utils shim. The
  `status="failed"` matches depend on it. This belongs to the copilot-mro/utils side, and the oss panels share it.
- Whether the POC box is deployed today.
- CRLF files (T9): the scanner raises "never closes", which fails closed. Not a finding.
- Compute deployed from other repos. The `lambdas` repo has no Terraform, and C8 is out of scope.
- The implementer's 34 mutants.

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process. A
functional regression takes the nearest slot.

**Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or
estate-shaping (the signal contract, content capture, RBAC, tenancy).

**Chunk:** F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IR3-01 | iac | `dashboards/llm-agents.json.tftpl:7` | The two `claude_code.*` selectors and the DARK note are gone; the bullet says there is no CLI panel | M-CLI-TELEMETRY turns the CLI metrics exporter off; a selector would read a series that cannot exist | copilot-mro `cb5d309d` removes its own rows | `test_cli_metrics_stay_off.py::test_no_board_or_alarm_reads_a_claude_code_metric`; `EXPECTED_SERIES` equality | **yes.** C1 (dotted name planted in `alarms.tf`) red | 2 | 0 | F2 | **SETTLED** |
| IR3-02 | iac | `tests/unit/observability/test_cli_metrics_stay_off.py:37` | One pattern covers dotted, underscore and `claude_code.*` spellings; floors + named witnesses | a pattern matching nothing must not pass | planted-line self-test | same file, 3 tests | partial: C1 red; C2 (`claude.code.*` regex) survives | 1 | 1 | F2 | **PARTIAL** (P3-8) |
| IR3-03 | iac | `dashboards/llm-agents.json.tftpl:7` (CLI bullet) | CLI per-call detail "arrives as log records under `service.name=claude-code`" | the ruling turns CLI logs on | producer `claude_cli_telemetry.py:92` is on copilot-mro `obs-merge-cli` only; `cb5d309d` not on `obs-merge` | none | no | 3 | 1 | F3 | **OPEN** (P3-7) |
| IR3-04 | iac | `apprunner.tf:84` | `LOGURU_DIAGNOSE = "NO"` in `runtime_environment_variables` | the service runs `:latest` with auto-deploy off, so a pre-G.117 image keeps diagnose on | `api-obsm/Dockerfile:94` has the line; api's `langgraph-merge` checkout has none | `test_loguru_diagnose_off_on_compute.py::test_required_resources_turn_loguru_diagnose_off[api]` | **yes.** L1 (`"no"`) red; L10 (quoted key) red, fails closed | 0 | 0 | F1 | **SETTLED** |
| IR3-05 | iac | `lambda.tf:126` | The same on `s3_pdf_processor` | `ignore_changes = [image_uri]` keeps the last-deployed image | `copilot-mro-obsm/Dockerfile.lambda:76` | same, `[s3_pdf_processor]` | **yes.** L2 (value from a variable) red | 0 | 0 | F1 | **SETTLED** |
| IR3-06 | iac | `lambda.tf:61` | The same on `image_lambda` (Cognito signup) | the only seat: `lambdas/cognito-lambdas` uses loguru and sets nothing (C8) | `lambdas` `c5a29d8`: `app.py` imports loguru; Dockerfile has no `LOGURU_*` | same, `[image_lambda]` | **yes.** L3b (`merge(...)`) red | 0 | 0 | F1 | **SETTLED** |
| IR3-07 | iac | `test_loguru_diagnose_off_on_compute.py:47-65`; `tests/_hcl_blocks.py:180-187` | Every compute resource in every root/module is REQUIRED or EXEMPT, by equality | a new compute resource must be decided | 9 today (3 + 6) | `::test_every_compute_resource_is_classified` | partial: L4 (local module) red; L5 (`.tf.json`), L6 (registry module), L7 (unlisted type) survive | 2 | 1 | F1 | **PARTIAL** (P3-2) |
| IR3-08 | iac | `test_loguru_diagnose_off_on_compute.py:82-85`, `:136-151` | `sns_to_slack` EXEMPT: python runtime, no layers, package imports no loguru | stdlib-only forwarder | `lambda_src/` = one file; `alerting.tf:172` `python3.12` | `::test_the_forwarder_lambda_really_has_no_loguru` | partial: L8 (subpackage import) survives; implementer c2m6 (not re-run) | 2 | 1 | F1 | **PARTIAL** (P3-1) |
| IR3-09 | iac | `test_loguru_diagnose_off_on_compute.py:86-88`, `:154-162` | The gateway task is EXEMPT: third-party images only | Go collector + Phoenix | `modules/otel-gateway/main.tf:16,51`; only `examples/basic` instantiates the module | `::test_the_gateway_task_runs_only_third_party_images` | **yes.** G1 (api ECR image) red | 2 | 0 | F1 | **SETTLED** |
| IR3-10 | iac | `test_loguru_diagnose_off_on_compute.py:89-92` | The Weaviate EC2 is EXEMPT | user data starts the demo compose, none of it our Python | copilot-mro-obsm `deployment/demo/docker-compose.yml` (collector, Weaviate, UI) + Phoenix override; no host Python | none | no | 2 | 1 | F1 | **OPEN** (source-read true) |
| IR3-11 | iac | `test_loguru_diagnose_off_on_compute.py:93-97`; `poc_ec2_setup.sh:161`, `:191-214` | `poc_replica` is EXEMPT: the api image sets it and the `.env` does not override it | — | the box pulls `:latest`; the Dockerfile line is only on unpublished `api-obsm`; the `.env` heredoc is this repo's seat | none | no: L9 (the heredoc gains `LOGURU_DIAGNOSE=YES`) survives | 2 | 1 | F1 | **REFUTED** (P2-3) |
| IR3-12 | iac | `test_loguru_diagnose_off_on_compute.py:98-101` | The gpu host and its launch template are EXEMPT | vLLM, third-party | llm-platform `profiles/gpu-prod/docker-compose.yml`: `vllm/vllm-openai@sha256:…`, the only image | none | no | 2 | 1 | F1 | **OPEN** (source-read true) |
| IR3-13 | iac | `tests/_hcl_blocks.py:1-163` | Resources, children and depth-0 attributes on top of `_env_syntax`'s scanner | a hand-rolled brace counter desyncs on `$${` (review of `89f3592`) | 11 planted traps: 8 correct, T9 fails closed, T7/T8 wrong (IR3-14) | `tests/unit/infra/test_hcl_blocks.py` (6 tests) | **yes.** H1 (depth filter off) red; H2 (`closing()` ignores strings) red | 1 | 0 | F2 | **SETTLED** (block boundaries) |
| IR3-14 | iac | `tests/_hcl_blocks.py:155-163` | `attributes()` reports every literal `KEY = value` at depth 0 | the docstring: the lexical rules "have ONE body" with `_env_syntax` | T7: `"K" = v` and `("K") = v` dropped, `K: v` kept; `_env_syntax` reads all three | none for these key forms | no: W10 survives (267 passed); W10b control red | 1 | 1 | F2 | **REFUTED** (P2-2) |
| IR3-15 | iac | `tests/_hcl_blocks.py` docstring; `process_env` | A key from `merge()`, a variable, a `for` or a dynamic block counts as NOT set: the rule fails closed | a refactor must not pass on a value it cannot see | T10: dynamic `environment` → `{}` | the REQUIRED test | **yes.** L2, L3b red | 1 | 0 | F1 | **SETTLED** |
| IR3-16 | iac | `apprunner.tf:43-44`; `lambda.tf:114-115` | `WEAVIATE_GRPC_PORT = "50051"` beside `WEAVIATE_URL` | C1.5 first clause at the iac sites; the knob sits beside the URL | utils `config.py:190` default 50051; gRPC host from the URL (`weaviate_service.py:517-521`); the demo compose publishes 50051 | `test_weaviate_ports_declared_and_admitted.py::test_every_weaviate_environment_names_the_grpc_port` | **yes.** W6 red; W5 red | 2 | 0 | F2 | **SETTLED** |
| IR3-17 | iac | `test_weaviate_ports_declared_and_admitted.py:22`, `:50-84` | The Weaviate SG admits both ports from each client's SG, derived from the resource | a non-admitted port is a connect timeout, not a Terraform error | client half derived; server half hardcoded (the SG by name, ports from `for_each` only) | `::test_the_weaviate_security_group_admits_both_ports_from_each_client` | partial: W5, W7, W8 red; W1, W2, W3, W4, W9 survive | 1 | 1 | F2 | **PARTIAL** (P2-1) |
| IR3-18 | iac | `dashboards/dependencies.json.tftpl:7` | The Transaction Search step excludes span `weaviate.connect`, after the CLIENT filter | the lazy connect double-counts Weaviate time and calls | utils `weaviate_service.py:140-141` (`weaviate.{op}`, CLIENT), `:500`; oss `dc4bf340` | `test_dependency_view_excludes_weaviate_connect.py` | **yes.** D1 red; D2 (a negated sentence) survives: a pin on words, stated in its docstring | 2 | 0 | F2 | **SETTLED** (presence) |
| IR3-19 | iac | `scripts/validate_metric_vocabulary.py:254-273`, `:878` | `FAMILY_SUFFIXED_INSTRUMENTS`: 15 exact `_total` names are exempt from the family rule, and nothing more | the legacy counters are born with `_total`; CloudWatch stores names as sent | utils `legacy_families.py` (15 counters declared with `_total`); `flynapse_otel/registry.py:159-160`, `:210-236` register verbatim; copilot-mro `LEGACY_SERIES` = the same 18 | `test_validate_metric_vocabulary.py` (`::test_every_born_suffix_entry_is_a_real_suffix_and_is_addressed`, `legacy-*` MUTATIONS, `EXPECTED_SERIES`) | **yes.** V4 (strip) red; V5 (an unaddressed entry) red; V3 (oss `_count`) red | 1 | 0 | F1 | **SETTLED** (exactness). The pin is hand-copied; drift from utils is unguarded (DEFERRED, stated) |
| IR3-20 | iac | `validate_metric_vocabulary.py:221-233` | `document_hub_processing_duration_seconds` joins `UNIT_SUFFIXED_INSTRUMENTS` | born with `_seconds` | `legacy_families.py` declares that exact name, unit `s` | same | **yes.** V7 (the entry dropped) red | 1 | 0 | F1 | **SETTLED** |
| IR3-21 | iac | `dashboards/llm-agents.json.tftpl:39` | Six non-agent LLM/embedding panels in the CloudWatch dialect | M-LEGACY-PANELS, aws half | each is the oss `9900a933` query translated (`_bucket` → native `histogram_quantile`; `_count` → `histogram_count`); labels match `legacy_families.py`; the companion holds (`llm.py:1260-1273`) | the vocabulary validator + `EXPECTED_SERIES` (names only) | names yes (V3, V4 red); labels no: V1, V2 survive | 2 | 1 | F1 | **PARTIAL** (P3-5) |
| IR3-22 | iac | `dashboards/platform-health.json.tftpl:51` | Nine chat-persistence and Document Hub panels with first-event pairing | M-LEGACY-PANELS, aws half | label values match the emitters (`processing.py:544-552`, `notifications.py:113,128`, `cleanup.py:450-472`); 900 s = `jobs.py:108`; "seven" alerts = 7 | same | names yes; values no: V6 (`outcome="failure"`) survives | 2 | 1 | F1 | **PARTIAL** (P3-5) |
| IR3-23 | iac | `llm-agents.json.tftpl:39` (signal-state line) | WIRED 2026-09-21 names the emitters | the validator requires an emitter on WIRED | `_record_embedding_cache_metrics` does not exist; the emitter is `note_embedding_cache_hits` (`utils/llm.py:1337`); inherited from `legacy_families.py:310,319` | `check_state_notes` (presence, not truth) | implementer c5m7 (not re-run) | 3 | 1 | F3 | **REFUTED in part** (P3-4) |
| IR3-24 | iac | both legacy rows | "retrieval unproved"; no AWS alarm until the C2 probe | no canary has confirmed names, labels or temporality | present on both rows; 7 oss alerts counted | `check_state_notes` grammar | implementer c5m7 (not re-run) | 3 | 1 | F3 | **ASSERTED** |
| IR3-25 | iac | `platform-health.json.tftpl:7` | Header: "the selectors below carry NO Prometheus suffix"; "the widgets below read the estate's OTLP log group" | written before the foot row | the foot row carries `_total` and is a metric panel; the llm-agents header got its exception sentence, this one did not | none | no | 3 | 1 | F3 | **OPEN** (P3-6) |
| IR3-26 | iac | `lambda.tf:138-140` | The env value is what the function actually runs with | — | no `ignore_changes` names env today | none | no: L11 (`ignore_changes = [image_uri, environment]`) survives | 2 | 1 | F1 | **OPEN** (P3-3) |
| IR3-27 | iac | all five commits | Each commit is green at its own HEAD: suite + three validators | CI `terraform-plan.yaml` runs all four | 243/246/258/261/262/266 passed; every checker exit 0; rootdir = each clone | the CI steps themselves | n/a (measured) | 1 | 1 | F2 | **SETTLED** (measured) |
| IR3-28 | iac | the `apprunner.tf` and `lambda.tf` edits | HCL aligned by hand; `terraform fmt -check` not run (ban) | — | hclwrite closes an alignment chain at a comment-only line; the new lines are single attributes after comments, or an aligned pair | none offline | no | 3 | 1 | F2 | **OPEN** (reasoned) |
| IR3-29 | iac | `README.md:291-297`; `validate_metric_vocabulary.py:21-31`, `:134-166` | The premise is corrected: each suffix half carries a small, sourced allow-list | the old "a family suffix is a property of the ENDPOINT" was false | read against utils | none | no | 3 | 1 | F3 | **ASSERTED** (true as written) |

**Totals:** 29 claims. **12 SETTLED · 6 PARTIAL · 3 REFUTED · 6 OPEN · 2 ASSERTED.** 11 tier 0, 18 tier 1, 0 tier 2.

## Open claims, tier 2 first

**Tier 2:** none. Nothing in this range changes a name, unit or attribute of the signal contract; the dialect change
recognises names utils already emits.

**Tier 1, refuted or partial (fix pass)**

1. **IR3-11 (P2-3).** The `poc_replica` exemption trusts the `:latest` image that App Runner's REQUIRED entry distrusts.
   The `.env` heredoc is the iac seat (L9 survives).
2. **IR3-17 (P2-1).** The Weaviate guard's server half is a constant: content ports, protocol, instance attachment, URL
   host and App Runner egress are unread (W1, W2, W3, W4, W9 survive).
3. **IR3-14 (P2-2).** `_hcl_blocks.attributes()` drops quoted and parenthesised keys, so the Weaviate client scan fails
   open (W10 survives, W10b control red).
4. **IR3-07 (P3-2).** `.tf.json` files and registry modules are invisible to the compute classification (L5, L6).
5. **IR3-08 (P3-1).** The forwarder check reads the top level only (L8).
6. **IR3-21 / IR3-22 (P3-5).** Legacy-row label keys and values are hand-verified only (V1, V2, V6).
7. **IR3-23 (P3-4).** A WIRED note names a nonexistent function; fix upstream in utils and copilot-mro too.
8. **IR3-02 (P3-8).** The CLI pattern misses a `claude.code.*` regex spelling (contrived).

**Tier 1, open**

1. **IR3-26 (P3-3).** The applied env is not proven (`ignore_changes`).
2. **IR3-03 (P3-7).** The CLI bullet asserts a producer that is not yet on copilot-mro `obs-merge`; this is a merge-order
   dependency.
3. **IR3-25 (P3-6).** The platform-health header contradicts the new foot row.
4. **IR3-10 / IR3-12.** The Weaviate EC2 and gpu-host exemptions rest on source reads of sibling repos; no guard.
5. **IR3-28.** `terraform fmt -check` has not run on these edits.
