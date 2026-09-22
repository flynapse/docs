# Claims packet: iac r4 (the r3 fix pass, `d52e8b8..74346bb`)

This is an independent adversarial review (Opus), done 2026-09-22. It was read-only throughout and was paused once at the owner's
request, then resumed. Each commit was taken with `git archive <sha>` into `scratchpad/iac-review-r4/at-<sha>/`. 20 tests
need `.git`, so each commit also ran as a `git clone --no-hardlinks` of `/home/aditya/Code/iac` checked out at that sha
(`clone-<sha>/`). The HEAD clone matched its archive byte for byte, `__pycache__` aside. Mutation proofs ran against separate
clones at `74346bb`: `scratchpad/…/mut/` before the pause, and after it `~/.claude/scratch/obs-merge/iac-review-r4/mut/`, per
the updated workspace rule. No code tree was edited, checked out, stashed or committed. There was no terraform, AWS, docker
or live run, and no sub-agent. `iac` is still at `74346bb`, and its only untracked file is the pre-existing
`poc_ec2_setup_ubuntu.sh`. The working notes and every log are in `~/.claude/scratch/obs-merge/iac-review-r4/`: `lanes.tsv`,
`lane-*.log`, `mutants.tsv`, `m-*.log`, `py-*.log`, the probes, and `PAUSED.md`.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `d52e8b8..74346bb` | iac | `/home/aditya/Code/iac` | `obs-merge` | `4afc68f` r3 P2-2 · `013c9ae` P2-1 · `0a31a72` P2-3 · `37f82c4` P3-1 · `9bb3c3d` P3-2 · `d2c7aac` P3-3 · `56e7673` P3-6 · `d86b378` P3-7 · `9828e17` P3-8 · `74346bb` P3-4 |

## Verdict

**MERGE-CLEAN, with P0 0 / P1 0 / P2 1 / P3 8.** Nothing ships broken. Every property the new guards name holds against
today's HCL, and all ten commits are green at their own HEAD. Every red proof named in the ten messages (24) was re-proved.
r3's P2-1..P2-3 and P3-1..P3-4, P3-6..P3-8 are each settled by a guard I saw fail. r3's P3-5 is deliberately DEFERRED:
plan §6 "Deferred from Phase G" records it with its fix, and V1/V2/V6 still survive, as the plan says. The one P2 (bare
block labels) and the eight P3s are all latent coverage gaps or wording. They belong in the post-r4 iac batch.

## How it was run

- **Lane:** `DEBUG=false PYTHONPYCACHEPREFIX=<fresh> /home/aditya/Code/pytest-slot.sh -- /home/aditya/Code/api/.venv/bin/python -m pytest -q -p no:cacheprovider -n 2`,
  from each clone's root. rootdir = the clone (`pytest.ini` at its root; confirmed with `--co` at HEAD). One pytest
  process at a time.
- **Validators:** `bash scripts/validate_dashboards.sh`, `python scripts/validate_alarms.py`,
  `python scripts/validate_metric_vocabulary.py`, which are the three CI steps in `.github/workflows/terraform-plan.yaml`.
  Each one's own exit status was captured.

| commit | pytest | exit | dashboards | alarms | vocabulary |
|---|---|---|---|---|---|
| `d52e8b8` (base) | 266 passed | 0 | 0 | 0 | 0 |
| `4afc68f` | 266 passed | 0 | 0 | 0 | 0 |
| `013c9ae` | 266 passed | 0 | 0 | 0 | 0 |
| `0a31a72` | 267 passed | 0 | 0 | 0 | 0 |
| `37f82c4` | 267 passed | 0 | 0 | 0 | 0 |
| `9bb3c3d` | 268 passed | 0 | 0 | 0 | 0 |
| `d2c7aac` | 272 passed | 0 | 0 | 0 | 0 |
| `56e7673` | 273 passed | 0 | 0 | 0 | 0 |
| `d86b378` | 274 passed | 0 | 0 | 0 | 0 |
| `9828e17` | 274 passed | 0 | 0 | 0 | 0 |
| `74346bb` | 275 passed | 0 | 0 | 0 | 0 |

Every count matches its commit message (266 → 275). In the bare `git archive` copies, 5 tests fail and 15 error at every
commit, because those tests need `.git`. They are not regressions.

**Mutation harness.** I used two runners:
- `/home/aditya/Code/mutant.sh` for single-file edits. It runs a baseline, starts cold, and md5-verifies the restore.
- `runmut.sh` for mutants that create files. It refuses to start on a dirty tree. It restores with `git checkout -- . &&
  git clean -fdx` and proves `git status --porcelain --ignored` is empty.

Each survivor I report was re-run against the FULL lane (`-n 2 tests`) with the mutant applied, and passed there as well.
From the resume on, each FULL run waited for the 1-minute load average to be ≤ 14.

**Totals:** 76 valid mutants. **52 went red** (48 on the aimed file, 4 only on the full lane) and **24 survived**:
- 6 are controls or stated design, which should survive.
- 18 are real survivors, each mapped to a finding below.

The count leaves out one invalid run and one contaminated run:
- **D3 (invalid):** `DARK until` followed by a backtick does not satisfy `DARK until \S`. D3b replaces it.
- **B1's first run (contaminated):** the OV mutant's `lambda_override.tf` matches iac's `.gitignore` (`*_override.tf`). The
  old `git clean -fd` and `git status --porcelain` could not see it, so it stayed in the clone and B1's first run failed on
  it. The harness was hardened, and OV, B1 and B2 were re-run on a tree proven clean. No earlier file-creating mutant
  wrote an ignored path.

**Process slips of my own:**
- Before the resume, the full-lane batch for L6b/L6e/B1/B2 started at a load of 15.07, over the gate. `pytest-slot.sh`
  gates on memory only. I added an explicit load gate for every later run.
- A read-only probe left a `scripts/__pycache__/` in the mutation clone. I found it with `--ignored`, removed it, and ran
  nothing on that tree in between.

---

## Findings, ranked

### No P0, no P1

Nothing leaks and no lock breaks. I checked each property against today's tree:
- `LOGURU_DIAGNOSE=NO` is written on all four REQUIRED seats: `apprunner.tf:84`, `lambda.tf:61`, `lambda.tf:126`, and
  the `.env` heredoc at `poc_ec2_setup.sh:203`.
- No REQUIRED resource ignores its env, and `ec2_poc.tf:120` has `user_data_replace_on_change = true`.
- The Weaviate path is open end to end. `apprunner_sg` and `lambda_sg` both allow all egress.
- Both no-suffix headers are true, and the legacy WIRED note names real recorders.
- The POC seat is real. The poc compose `api` service on copilot-mro `main` reads `./.env` through `env_file`, and its
  `environment:` list sets no `LOGURU_*`, which would otherwise override the file.

---

### P2-1: Bare (identifier) block labels hide a resource or a module from every per-resource guard in this range

`tests/_hcl_blocks.py:38-39`. `_RESOURCE` requires `resource "T" "N" {` and `_MODULE` requires `module "N" {`, both with
quoted labels. HCL's native syntax also allows identifier labels: `Block = Identifier (StringLit|Identifier)* "{" …`, in
the HCL native-syntax spec. So `resource aws_lambda_function reindexer {` is a legal block that `resources()` never
returns. That legality rests on the grammar only. No terraform ran to confirm it, since terraform is banned in this review.

| mutant / probe | edit | result |
|---|---|---|
| B1 | a new `resource aws_lambda_function reindexer { … }` in `lambda.tf`: `WEAVIATE_URL` set, **no** `WEAVIATE_GRPC_PORT`, **no** `vpc_config`, **no** `LOGURU_DIAGNOSE` | **FULL 275 passed** |
| L6e | `module reindexer { source = "terraform-aws-modules/lambda/aws" }` | **FULL 275 passed** (the P3-2 remote-module refusal is bypassed) |
| B2 | `lambda_override.tf` re-opening `s3_pdf_processor` with bare labels and `LOGURU_DIAGNOSE = "YES"` | **FULL 275 passed** |
| T9 / T9b (probe) | a bare-label resource or module in a planted file | `resources()` → `[]`, `modules()` → `0` |
| OV (control) | the same override with quoted labels | red: it is keyed by its own file, so it shows up unclassified |

B1 is one resource that escapes all three guards at once: the G.117 "every compute resource is classified" equality, both
Weaviate checks, and the module-source refusal.

The docstring's "the one limit left is a resource TYPE missing from COMPUTE_TYPES", and `9bb3c3d`'s "anything that would
put a resource outside them is refused outright", are therefore false. The pattern is the same one r3 P2-2 found for keys:
a legal spelling fails the guard open.

**Latent:** no tracked `.tf` file uses a bare label today (checked across all 42).

**Direction:** it fails OPEN. A missing resource is "nothing to decide", and a missing module is "no remote source".

**Fix (small):** in `_RESOURCE` and `_MODULE`, accept `"[^"\n]+"|[A-Za-z_][A-Za-z0-9_-]*` per label. Add both forms to
`test_hcl_blocks.py`'s `TRAPS`. `validate_alarms.py` and `validate_metric_vocabulary.py` should be checked for the same
quoted-label assumption. Both are outside this range and I did not test them.

---

### P3-A: The Weaviate guard never reads the client security groups' EGRESS

`tests/unit/networking/test_weaviate_ports_declared_and_admitted.py:1-21`, `:116-133`. The docstring says the whole path is
derived and names the client as "the security groups the process egresses from", but no egress rule is ever read. W11 cuts
`lambda_sg`'s egress to 443/tcp and gets **FULL 275 passed**. The result is the same connect timeout this guard is named
for. `013c9ae`'s "nothing on the path is listed" is true; the egress half is simply not on the path it reads.

**Fix:** for each client group, require an egress rule that covers both ports, or `-1`, to any destination.

### P3-B: The POC `.env` guard reads the FIRST `cat > ./.env` heredoc, not what the container gets

`tests/unit/observability/test_loguru_diagnose_off_on_compute.py:125-141` (`user_data_dotenv`). Four shapes change the
file compose hands the `api` container, and each gets **FULL 275 passed**:
- **L9b:** a second `cat >> ./.env << EOF2` appending `LOGURU_DIAGNOSE=YES`.
- **L9c:** `echo "LOGURU_DIAGNOSE=YES" >> ./.env`.
- **L9h:** a second, TRUNCATING `cat > ./.env << EOF2`. It wins at runtime.
- **L9s:** `sed -i` rewriting the line.

`0a31a72`'s "bounded to the `.env` heredoc body" describes this accurately; the bound is the gap. The claim "an `export`
elsewhere never reaches a compose container" is true: L9x survives, correctly.

**Fix:** fail when the script writes `.env` at more than one site, counting `>`, `>>`, `tee` and `sed -i`. Otherwise read
all of them in order.

### P3-C: The second "one lexical body" asymmetry: name escapes and a BOM

`tests/_hcl_blocks.py:56-61` (`HclFile.__init__`). `_env_syntax` runs `_decode_name_escapes` (`_structured_file`) and
strips a leading BOM (`env_assignments`). `HclFile` does neither.
- **W10u:** a Lambda with `"WEAVIATE_URL" = …`, no gRPC port and no `vpc_config`, classified REQUIRED with a literal
  `LOGURU_DIAGNOSE`, gets **FULL 277 passed**.
- **T22 (probe):** the escaped key is dropped.
- **T10 (probe):** a BOM before the first `resource` hides it. That fails open only if terraform accepts a BOM, which I did
  not verify.

`4afc68f` closed one asymmetry: quoted and parenthesised keys. This is the next one, and it is contrived.

**Fix:** run `HclFile` on the same prepared text `_structured_file` uses.

### P3-D: A `../` module source that leaves the repo counts as local

`test_loguru_diagnose_off_on_compute.py:185-190`. L6b sets `module "reindexer" { source = "../lambdas/terraform/reindexer" }`
and gets **FULL 275 passed**. The assertion message says "modules sourced from outside this repo". The check tests a
string prefix, and in this estate `lambdas` is a sibling repo.

**Fix:** resolve the source against the calling file's directory and require the result to be under `repo_root`.

### P3-E: The forwarder check reads a hardcoded `lambda_src`, not the directory the archive zips

`test_loguru_diagnose_off_on_compute.py:241`. L8s repoints `alerting.tf`'s `source_dir` at `${path.module}/forwarder_src`,
where `forwarder_src/sns_to_slack.py` imports loguru. It gets **FULL 275 passed**. `37f82c4` fixed the depth (L8, L8n, L8r
and L8l are red) and kept the directory as a constant.

**Fix:** read `source_dir` from the `archive_file` data block and fail on anything that is not `${path.module}/<dir>`.

### P3-F: The CLI-bullet guard accepts a mention that check 6 does not read as a claim

`tests/unit/observability/test_cli_metrics_stay_off.py:92-112`. The test strips emphasis, then runs `STATE_GRAMMAR` over
the raw bullet. It skips the validator's claim/mention rule, `_blank_backticked`. D3b writes the phrase as
`` `DARK until copilot-mro` ``, which is a mention, not a claim. Results:
- **FULL 275 passed.**
- `validate_metric_vocabulary.py` exits 0.

The bullet then carries no claim that check 6 reads, yet the guard whose message says "so check 6 reads it" stays green.
D1 (the sentence removed) and D2 (lowercased) are red.

**Fix:** assert through `validator.state_notes(root, failures)` that a note sits on the CLI bullet's line, or blank the
backticked spans first.

### P3-G: The recorder pin reads backticked identifiers only, so platform-health's file-named emitters are unpinned

`tests/unit/observability/test_validate_metric_vocabulary.py:252-283`. R3 changes `document_hub/indexing.py` to
`document_hub/index.py` in the platform-health WIRED note and gets **FULL 275 passed**. Apart from
`_record_block_save_failure`, that note's emitter list is five FILE names. All five are right today; each emits a family
in copilot-mro-obsm:
- `service.py:1032`
- `processing.py:292`, `:542`, `:549`, `:570`, `:577`
- `cleanup.py:448`, `:469`
- `notifications.py:110`, `:125`
- `indexing.py:756`

R1 (the old name put back), R2 (a recorder dropped) and R5 (an extra identifier) are red.

**Fix:** the plan already records it: emitters published as data by the emitting repos.

### P3-H: Process. Three messages overclaim, one fix is orphaned, and three subjects carry the wrong r3 number

The messages were written before the proofs ran, as the brief says. All 24 red proofs they name hold, and every suite
count is exact. The prose overreaches in four places (see the audit table):
- `9bb3c3d` claims one remaining limit. There are two more: P2-1 and P3-D.
- `013c9ae`'s "nothing on the path is listed" is read as the whole path. The egress half is unread (P3-A).
- `d86b378`'s "so check 6 reads it" is not what its guard proves (P3-F).
- `74346bb` hands the copilot-mro copy of the phantom name to "the utils lane". copilot-mro-obsm `557a178f`
  `tests/integration/otel/_emitted_series.py:181,183` still names `_record_embedding_cache_metrics`, and utils `0e9b2a8`
  fixed only utils' own `legacy_families.py`. No lane owns it.

The subjects of `56e7673` / `d86b378` / `9828e17` say P3-5 / P3-6 / P3-7 for r3's P3-6 / P3-7 / P3-8. The bodies
disambiguate.

---

## Commit-message audit

| sha | claim | verdict |
|---|---|---|
| `4afc68f` | Depth is tested at the key TOKEN. Traps gain `"K"`, `("K")` and a nested quoted key. Red: the traps test against the old offset, and W10 (both Weaviate checks). 266 → 266 | **TRUE.** H1 red (`test_escapes_comments_and_heredocs_do_not_move_a_boundary`). W10 and W10p red, 2 failed. 266 measured. The "one lexical body" still differs on name escapes and BOM (P3-C); that is not claimed either way |
| `013c9ae` | The server half is derived: URL host → instance → its SGs → each ingress rule whole (ports per `for_each` item, TCP, admitting SGs). App Runner must egress through VPC. Unreadable shapes fail closed; CIDR admission is not counted. Red: W1, W2, W3, W4, W9; controls W5, W7, W8. 266 → 266 | **TRUE, with one overclaim.** All eight named reds re-proved. W12 (CIDR), W14 (`toset`) and W16 (`public_ip`) fail closed as stated, and W13 (a custom `iterator`) reads correctly. "Nothing on the path is listed" does not cover client-SG egress (W11 survives, P3-A) |
| `0a31a72` | The heredoc writes `LOGURU_DIAGNOSE=NO`. `poc_replica` is REQUIRED. Env is read through the templatefile'd script, bounded to the `.env` heredoc. Exactly one value, `NO`. Red: L9 (two values); line removed. 266 → 267 | **TRUE.** L9, L9rm and L9g (a variable value) red. The premise "`:latest` is published from api main/develop, which lack the line" holds for api `main` (Dockerfile, 94 lines, no `LOGURU_DIAGNOSE`). api has no local `develop` branch to check. The one-heredoc bound is P3-B |
| `37f82c4` | It rglobs `lambda_src/`. Red: L8. 267 → 267 | **TRUE.** L8, L8n, L8r and L8l red. The directory is still hardcoded (P3-E, not claimed) |
| `9bb3c3d` | Refuses `*.tf.json` and non-local module sources, with a non-vacuity pin. "The remaining limit … L7 … stays named." Red: L5, L6; L4 still red. 267 → 268 | **OVERCLAIMS.** L5, L6, L6c, L6f and L4 red. There is not one remaining limit: bare labels (P2-1) and `../` out of the repo (P3-D) both pass the full lane |
| `d2c7aac` | Refuses an `ignore_changes` entry covering the env block (the block, a parent, a key inside it, `all`). The POC needs `user_data_replace_on_change = true` (it has it, `ec2_poc.tf:120`). Red: L11; replace-on-change false; `user_data` ignored. 268 → 272 | **TRUE.** L11, L11b (multi-line list), L11c (a key inside), L11d (`all`), L11e (a parent path on App Runner), P1, P2 and P3 (the line removed) red. L11t and L11f (unrelated paths) survive correctly. `:120` verified |
| `56e7673` | The platform-health no-suffix claim is scoped to `otelcol_*`, log widgets are named as such, and the legacy row is named as the one exception. The guard reaches both boards. Red: each exception sentence removed. 272 → 273 | **TRUE.** X1 and X2 red. The `>= 2` floor also kills the lowercase bypass on one board (X3) and on both (X3b). Subject says "P3-5" for r3 P3-6 |
| `d86b378` | The CLI bullet carries `DARK until copilot-mro obs-merge-cli merges into copilot-mro obs-merge` "so check 6 reads it"; it flips to WIRED after the merge. The guard requires a claim in `STATE_GRAMMAR`. Red: DARK sentence removed. 273 → 274 | **True at commit, superseded by `557a178f`.** The CLI bullet can flip DARK→WIRED in the post-r4 batch. At `735f8213`, `cb5d309d` was not on copilot-mro `obs-merge` and `claude_cli_telemetry.py` was absent; `557a178f` merged it. D1 and D2 red. The guard sentence **overclaims**: a backticked mention passes (D3b, P3-F). Subject says "P3-6" for r3 P3-7 |
| `9828e17` | Pattern `claude[._]code[._]…` with no leading boundary and case-sensitive, so `CLAUDE_CODE_*` and `claude-code` stay writable. Self-test gains both spellings. Red: C2. 274 → 274 | **TRUE.** C2, C3 (prefixed) and C4 (old pattern back → self-test red) red. C5 and C8 are caught by the `EXPECTED_SERIES` limb. C6 (`claude.?code.*`) is a contrived residual. Subject says "P3-7" for r3 P3-8 |
| `74346bb` | The note names `note_embedding_cache_hits` (utils `llm.py:1337`) and `accumulate_bedrock_cost`. A word pin with definition sites; "the utils lane fixes upstream". Red: the old name back. 274 → 275 | **TRUE for iac; overclaims across repos.** All five recorders are defined at the cited lines at utils-obsm `f8e31ee` and HEAD `179cc6d` (359/425/831/1233/1337), each emitting its family in its own body. R1, R2 and R5 red. "The utils lane fixes it upstream" is true for utils only: copilot-mro-obsm `_emitted_series.py:181,183` still carries the phantom (P3-H) |

---

## What I tried to break and could not

- **HCL traps against `_hcl_blocks` (18-case probe at HEAD, `probe_hcl.py`).** 15 read correctly, and T23 (a duplicate
  `environment` block) raises, which fails closed. The correct readings:
  - a heredoc holding a `resource` header and unbalanced braces;
  - `$${` at a string's end, with a nested string inside an interpolation holding `"}"`;
  - block and line comments holding headers;
  - a nested `dynamic` inside a `dynamic`'s `content`, which stays nested;
  - `jsonencode({ WEAVIATE_URL = "}" … "${var.x}}" })`: its keys are not block keys, and the env after it is intact;
  - a `for_each` resource;
  - an indented heredoc with terminator lookalikes (`not EOT here`, `EOTX {`);
  - a heredoc env VALUE: the key is kept and the value is unreadable, so the URL check fails closed;
  - header spellings with a trailing comment, tabs, or no space before `{`;
  - an escaped quote followed by braces;
  - a `%{ if }` directive with a quoted `}`;
  - `merge(...)` hiding keys, which fails closed for REQUIRED resources;
  - one-line triple nesting.

  The three wrong readings are T9/T9b (P2-1), T10 and T22 (P3-C).
- **Key spellings (the r3 P2-2 fix).** Quoted (W10) and parenthesised (W10p) keys on a Weaviate client are red. The
  nested quoted key stays out.
- **The server half of the Weaviate path.** Every r3 survivor is now red: W1, W2, W3, W4 and W9. W12 (CIDR), W14
  (`toset`), W16 (`public_ip`) and W20 (one client SG dropped from admission) are red, or fail closed as the docstring
  says.
- **A non-literal Weaviate client env.** W18 (`dynamic "environment"`) and W19 (`variables = merge(...)`) pass the
  Weaviate test alone, but the full lane kills both (W18R, W19R). The LOGURU REQUIRED rule fails closed on the same
  block, and every Weaviate client must be classified. So they are closed by coupling, not by the Weaviate guard.
- **`ignore_changes` shapes:** the block itself, a parent path, a key inside it, a multi-line list, `all`, and a
  `user_data` ignore on the POC are all red. Unrelated paths stay green.
- **An override file with quoted labels (OV)** is red, because it is keyed by its own file and shows up unclassified.
- **The P3-6 word pin.** Lowercasing the claim and dropping the exception, on one board or both, is red through the `>= 2`
  floor.
- **The CLI pattern.** The pre-fix pattern put back is red (the self-test). The dotted, prefixed and `claude[._]code`
  regex spellings, and `(?i)` regex matchers, are red through one limb or the other.
- **Forwarder imports:** subpackage, function-level, dotted `import loguru.logger`, and a `layers` attribute are all red.
- **Header truth.** platform-health has no suffixed selector outside its legacy row. Its six `otelcol_*` names carry
  none, and widgets 2-4 are log widgets.
- **The recorder lines at the pinned sha**, and the POC compose `env_file` seat.

## What I did not test

- **Any terraform run** (banned). Unverified as a result:
  - whether terraform accepts bare labels (P2-1 rests on the HCL grammar) or a leading BOM (T10);
  - `terraform fmt -check` on the new heredoc line;
  - whether a `runtime_environment_variables` change redeploys App Runner's `:latest`.
- **Live AWS, CloudWatch, docker and the POC box.**
- **api's `develop` branch** (not present locally).
- **copilot-mro's POC `restart-services.sh`.** When `.env` is missing, it writes a fresh `.env` with only three keys and no
  `LOGURU_DIAGNOSE` (copilot-mro-obsm `deployment/poc/restart-services.sh:55-61`). This only happens when the user-data
  file is gone, and the script is copilot-mro's seat, not iac's. It is noted for that lane.
- **Weaviate clients of other compute kinds.** `PROCESS_ENV_PATH` covers App Runner and Lambda only, so an ECS task or an
  EC2 user-data client pointing at Weaviate is invisible to the Weaviate scan. None exists today. An ECS client would still
  have to be classified for LOGURU, where it would fail as REQUIRED or pass as EXEMPT.
- **The quoted-label assumption in `scripts/validate_alarms.py` and `scripts/validate_metric_vocabulary.py`.** Both are
  unchanged in this range and may share P2-1's root.
- **Contrived residuals, run but not worth code:** C6 (`{__name__=~"claude.?code.*"}`: no `_`, so `_is_series_shaped`
  drops it) and L8i (`importlib.import_module("loguru")`). Both pass the full lane.
- **r3's W6** (the Lambda's gRPC key renamed) was not re-run. It is not named in any of these messages.

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process.
**Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or
estate-shaping. **Chunk:** F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IR4-01 | iac | `tests/_hcl_blocks.py:163-180` | `attributes()` tests depth where the key TOKEN starts, so `K`, `"K"` and `("K")` are all read | r3 P2-2: quoted and parenthesised keys were dropped, and the Weaviate scan failed open | trap test grew; T-probe | `tests/unit/infra/test_hcl_blocks.py`; both Weaviate checks | **yes.** H1 (the old offset back) red; W10, W10p red | 1 | 0 | F2 | **SETTLED** |
| IR4-02 | iac | `tests/_hcl_blocks.py:1-10`, `:56-61` | "the lexical rules have ONE body" with `_env_syntax` | a second scanner would desync | `_structured_file` decodes `\u` name escapes, and `env_assignments` strips a BOM; `HclFile` does neither | none for these shapes | no: W10u survives (FULL 277); T10 and T22 read wrongly | 2 | 1 | F2 | **REFUTED in part** (P3-C) |
| IR4-03 | iac | `tests/_hcl_blocks.py:38-39` | resource and module headers are found by quoted labels | the header regexes were written for the house style | HCL allows identifier labels; no tracked `.tf` file uses them today | none | no: B1, L6e and B2 survive (FULL 275 each); T9, T9b | 2 | 1 | F1 | **REFUTED** (P2-1) |
| IR4-04 | iac | `test_weaviate_ports_declared_and_admitted.py:68-175` | Server half derived: URL host → instance → attached SGs → whole ingress rules (ports, TCP, admitting SGs); App Runner `egress_type = VPC`; unreadable shapes fail closed | r3 P2-1: five connect-timeout shapes passed | `ec2.tf:6`, `:115-123`; `apprunner.tf:114-117` | `::test_the_weaviate_host_admits_both_ports_from_each_client` | **yes.** W1, W2, W3, W4, W5, W7, W8, W9, W12, W14, W16, W20 red; W13 control green | 1 | 0 | F2 | **SETTLED** |
| IR4-05 | iac | same file, `:1-21`, `:116-133` | "the whole path is derived" | — | the client SGs' egress rules are never read | none | no: W11 (`lambda_sg` egress 443 only) survives, FULL 275 | 2 | 1 | F2 | **PARTIAL** (P3-A) |
| IR4-06 | iac | `poc_ec2_setup.sh:203`; `test_loguru_diagnose_off_on_compute.py:94-97`, `:144-146` | `LOGURU_DIAGNOSE=NO` in the `.env` heredoc; `poc_replica` REQUIRED, read through its user data | r3 P2-3: the exemption trusted the `:latest` image that App Runner's entry distrusts | api `main` Dockerfile has no line; copilot-mro `main` poc compose `api` reads `./.env` via `env_file` | `::test_required_resources_turn_loguru_diagnose_off[aws_instance.poc_replica]` | **yes.** L9 (a second value), L9rm, L9g (a variable) red; L9q, L9x correctly green | 0 | 0 | F1 | **SETTLED** (first heredoc) |
| IR4-07 | iac | `test_loguru_diagnose_off_on_compute.py:125-141` | the instance env is the FIRST `cat > ./.env` heredoc's body | "an export elsewhere never reaches a container" | the container reads the final file | none | no: L9b, L9c, L9h and L9s survive (FULL 275 each) | 2 | 1 | F1 | **PARTIAL** (P3-B) |
| IR4-08 | iac | `test_loguru_diagnose_off_on_compute.py:234-250` | the forwarder exemption rglobs `lambda_src/` | r3 P3-1: the archive zips the whole dir | `alerting.tf:105` | `::test_the_forwarder_lambda_really_has_no_loguru` | **yes.** L8, L8n, L8r, L8l red | 2 | 0 | F1 | **SETTLED** (depth) |
| IR4-09 | iac | `test_loguru_diagnose_off_on_compute.py:241` | the directory checked is the constant `lambda_src` | — | `source_dir` is not read | none | no: L8s survives, FULL 275 | 2 | 1 | F1 | **OPEN** (P3-E) |
| IR4-10 | iac | `test_loguru_diagnose_off_on_compute.py:168-194` | refuses `*.tf.json` and non-`./`/`../` module sources; non-vacuity pin on the one local call | r3 P3-2: L5, L6 passed | the gateway example's `../..` call is reached | `::test_nothing_hides_a_resource_from_the_classification` | **yes.** L5, L6, L6c, L6f red; L4 red via classification | 2 | 0 | F1 | **SETTLED** (the shapes named) |
| IR4-11 | iac | same, `:185-190` | a `../` source counts as local, i.e. in the repo | the message says "outside this repo" | a prefix test, not a path test | none | no: L6b (`../lambdas/…`) survives, FULL 275 | 2 | 1 | F1 | **REFUTED** (P3-D) |
| IR4-12 | iac | same, docstring `:26-33` | "The one limit left is a resource TYPE missing from COMPUTE_TYPES" | — | bare labels and `../` sources also escape | none | n/a | 3 | 1 | F3 | **REFUTED** (P2-1, P3-D) |
| IR4-13 | iac | `test_loguru_diagnose_off_on_compute.py:204-222`; `ec2_poc.tf:120` | a REQUIRED resource may not ignore its env block (the block, a parent, a key, `all`); the POC needs `user_data_replace_on_change = true` | r3 P3-3: configured ≠ applied | no REQUIRED resource ignores env today | `::test_required_resources_apply_the_env_they_configure` | **yes.** L11, L11b, L11c, L11d, L11e, P1, P2, P3 red; L11t, L11f correctly green | 1 | 0 | F1 | **SETTLED** |
| IR4-14 | iac | `dashboards/platform-health.json.tftpl:7`; `test_validate_metric_vocabulary.py:222-244` | the no-suffix claim is scoped to `otelcol_*`; the legacy row is named as the one exception; a guard with a `>= 2` floor | r3 P3-6 | the only suffixed selectors are in widget 5 | `::test_a_no_suffix_claim_names_the_born_suffix_exception` | **yes.** X1, X2, X3, X3b red | 3 | 0 | F3 | **SETTLED** |
| IR4-15 | iac | `dashboards/llm-agents.json.tftpl:7` (CLI bullet) | "Those records are DARK until copilot-mro `obs-merge-cli` merges into `obs-merge`" | r3 P3-7: the producer was on another branch | true at `d86b378` (`cb5d309d` not on `735f8213`); **superseded** by copilot-mro-obsm `557a178f`, which merged it | `test_cli_metrics_stay_off.py::test_the_cli_bullet_states_its_producer_in_the_state_grammar` | **yes.** D1, D2 red; D4 (a premature WIRED) passes by design | 3 | 1 | F3 | **SETTLED at commit; STALE since `557a178f`.** The DARK→WIRED flip is owed by the post-r4 batch |
| IR4-16 | iac | `test_cli_metrics_stay_off.py:92-112` | "the bullet must make a DARK/WIRED/LIVE claim … so check 6 reads it" | — | the raw-text search skips `_blank_backticked` | the same test | no: D3b survives (FULL 275; validator exit 0) | 1 | 1 | F3 | **PARTIAL** (P3-F) |
| IR4-17 | iac | `test_cli_metrics_stay_off.py:41` | `claude[._]code[._]…`, no leading boundary, case-sensitive | r3 P3-8 | the self-test pins dotted, underscore, regex, `.`-for-`_` and prefixed forms | `::test_no_board_or_alarm_reads_a_claude_code_metric`, `::test_the_pattern_finds_every_spelling_a_query_can_use`; `EXPECTED_SERIES` | **yes.** C2, C3, C4 red; C5, C8 red via `EXPECTED_SERIES`; C6 a contrived residual | 1 | 0 | F2 | **SETTLED** (the spellings named) |
| IR4-18 | iac | `dashboards/llm-agents.json.tftpl:39` | the WIRED note names `recorded_llm_call`, `accumulate_bedrock_cost`, `_record_token_metrics`, `_record_embedding_metrics`, `note_embedding_cache_hits` | r3 P3-4: a phantom recorder | utils-obsm `f8e31ee` and `179cc6d` `llm.py:359/425/831/1233/1337`, each emitting its family in its body | `test_validate_metric_vocabulary.py::test_the_legacy_rows_name_the_recorders_that_exist` | **yes.** R1, R2, R5 red | 3 | 0 | F3 | **SETTLED** |
| IR4-19 | iac | `test_validate_metric_vocabulary.py:252-283` | the pin compares backticked identifiers | "a pin on words", stated | platform-health's emitters are five file names plus one function | the same test | no: R3 (`indexing.py` → `index.py`) survives, FULL 275 | 3 | 1 | F3 | **PARTIAL** (P3-G) |
| IR4-20 | copilot-mro | `copilot-mro-obsm tests/integration/otel/_emitted_series.py:181,183` (at `557a178f`) | `74346bb`: "the utils lane fixes it upstream" | — | utils `0e9b2a8` fixed utils' own file only; the copilot-mro copy still names `_record_embedding_cache_metrics` | none | n/a | 3 | 1 | F3 | **OPEN** (unowned; P3-H) |
| IR4-21 | iac | both legacy rows | label keys and values hand-checked only | r3 P3-5, DEFERRED in plan §6 with its elegant fix (a published instrument inventory) | V1 (`token.type`), V2 (`tenant.id`), V6 (`outcome="failure"`) | none | no: V1, V2, V6 still survive, FULL 275 each | 2 | 1 | F1 | **OPEN** (DEFERRED, recorded) |
| IR4-22 | iac | the Weaviate client scan with a `dynamic`/`merge()` env | closed by coupling: the LOGURU REQUIRED rule fails closed on the same block | — | W18 and W19 pass the Weaviate file alone | the LOGURU REQUIRED test | **yes.** W18R, W19R red on the full lane | 2 | 1 | F2 | **SETTLED** (by coupling; the Weaviate guard alone fails open) |
| IR4-23 | iac | all ten commits | each commit is green at its own HEAD: the suite plus three validators | CI `terraform-plan.yaml` runs all four | 266/266/266/267/267/268/272/273/274/274/275; every checker exit 0; rootdir = each clone | the CI steps | n/a (measured) | 1 | 1 | F2 | **SETTLED** (measured) |
| IR4-24 | iac | the commit messages | messages were written before the proofs | process slip, per the brief | all 24 named red proofs re-proved; counts exact; overclaims in `013c9ae`, `9bb3c3d`, `d86b378`, `74346bb`; three subjects off by one | none | n/a | 3 | 1 | F3 | **PARTIAL** (P3-H) |
| IR4-25 | iac | `0a31a72` message | "`:latest` is published from api main/develop, which lack the Dockerfile line" | the reason `poc_replica` became REQUIRED | api `main` Dockerfile (94 lines) has no `LOGURU_DIAGNOSE`; no local `develop` | none | n/a | 3 | 1 | F1 | **ASSERTED** (`main` verified) |

**Totals:** 25 claims. **12 SETTLED · 5 PARTIAL · 4 REFUTED · 3 OPEN · 1 ASSERTED.** The SETTLED count includes IR4-15,
which is settled at commit but stale since `557a178f`. 9 are tier 0 and 16 tier 1; none is tier 2.

## Open claims, tier 2 first

**Tier 2:** none. Nothing in this range changes a name, unit or attribute of the signal contract, content capture, RBAC or
tenancy.

**Tier 1, refuted or partial (the post-r4 iac batch):**

1. **IR4-03 / IR4-12 (P2-1).** Bare block labels hide a resource or module from the classification, from both Weaviate
   checks and from the module-source refusal. B1, L6e and B2 each pass the full lane. Accept identifier labels in
   `_RESOURCE`/`_MODULE` and add both forms to `TRAPS`. Check the two validators' own header regexes too.
2. **IR4-07 (P3-B).** The POC `.env` guard reads one heredoc. Fail on more than one write to `.env`.
3. **IR4-05 (P3-A).** The Weaviate guard reads no client-SG egress.
4. **IR4-16 (P3-F).** The CLI-bullet guard accepts a backticked mention. Assert through `state_notes`.
5. **IR4-11 (P3-D).** `../` module sources leaving the repo. Resolve the path against `repo_root`.
6. **IR4-02 (P3-C).** `HclFile` skips name-escape decoding and BOM stripping.
7. **IR4-19 (P3-G).** The recorder pin does not reach file-named emitters.
8. **IR4-24 (P3-H).** Message overclaims and subject numbering. This is process only; no code.

**Tier 1, open:**

1. **IR4-15.** The CLI bullet's DARK claim is stale since copilot-mro-obsm `557a178f`. The flip to `WIRED <date>,
   retrieval unproved: claude_cli_telemetry.py …` belongs to the post-r4 batch, not this review.
2. **IR4-09 (P3-E).** The forwarder check hardcodes `lambda_src`. Read `source_dir`.
3. **IR4-20.** copilot-mro-obsm `_emitted_series.py:181,183` still names the phantom recorder, and no lane owns it.
4. **IR4-21.** r3 P3-5, the legacy label keys and values. It is DEFERRED with its fix recorded in plan §6.
5. **IR4-25.** Whether api `develop` also lacks the Dockerfile line. Only `main` could be read.

Items the brief says the post-r4 iac batch already carries: `alarms.tf:155-167` stale "OWNER RULING OWED", and the
ungated `terraform-apply.yaml`.
