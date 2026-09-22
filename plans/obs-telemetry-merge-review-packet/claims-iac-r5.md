# Claims packet: iac r5 (the post-r4 fix batch `74346bb..d1ebeb1`, plus `234603b`, `013dc89`, `9fda3db`, `5e476e0`) — PARTIAL

**PARTIAL (second version — lane 1 reviewer killed, lane 2 reviewer PAUSED by the owner mid-round at the agent-cap cut).**
Independent adversarial review (Opus), 2026-09-22, read-only throughout. No tree was edited, checked out, stashed or
committed; no terraform init/plan/apply against real state, no AWS, no docker, no network, no sub-agent. `iac` is still at
`d1ebeb1` on `obs-merge`; its untracked files (`poc_ec2_setup_ubuntu.sh` and six `__pycache__/` dirs) are pre-existing and
were not touched. Durable notes, every log, the clones and the mutation harness:
`~/.claude/scratch/obs-merge/iac-review-r5/` (`NOTES.md`, `PAUSED.md`, `lanes.tsv`, `logs/lane-*.log`, `mutants.tsv`,
`logs/m-*.log`, `m/*.prep`, `redbefore.tsv`, `tfparse/`, `probes/`).

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `74346bb..d1ebeb1` | iac | `/home/aditya/Code/iac` | `obs-merge` | 15: `d76c439` P2-1 · `f5b73f3` P3-A · `17a65c1` P3-B · `bac0f33` P3-C · `ac5ab23` P3-D · `6615cb0` P3-E · `0963a3e` P3-F · `a04b9c0` CLI flip · `d417b1a` P3-G · `61c5297` C2 ruling · `4e2a936` IR-25 · `ca095c8` IR-12 · `2965526` IB-03 · `0dda33a` IS-12 · `d1ebeb1` P3-B limit pin |
| extra | iac | same | same | `9fda3db`, `234603b`, `5e476e0`, `013dc89` (never independently reviewed) |

## Verdict (provisional — the round was paused before the four extra commits' diffs were read end to end)

- **Part 1, the fix batch `74346bb..d1ebeb1`: MERGE-CLEAN, provisionally P0 0 / P1 0 / P2 5 / P3 3.** Nothing ships broken.
  All 15 commits are green at their own HEAD, every count in every message is exact, and all four "red before" claims that
  name a prior sha were re-proved red at that sha. Each r4 finding the batch names is settled by a guard I saw fail. The
  five P2s are latent coverage gaps in the NEW guards — each one fails OPEN, and each is a shape no tracked file uses today.
- **Part 2, the four extra commits: PROVISIONAL MERGE-CLEAN, P2 0 / P3 2** on the evidence gathered so far (lanes green,
  17 of 19 aimed mutants red). Two survivors are settled by later commits in part 1. **Not final**: the diffs of
  `9fda3db`, `013dc89` and `5e476e0` were not read end to end before the pause.

## How it was run

Every SHA was cloned (`git clone --no-hardlinks /home/aditya/Code/iac`, checked out inside the clone) under
`~/.claude/scratch/obs-merge/iac-review-r5/clone-<sha>/` — 20 tests need `.git`. Lane, from the clone root:
`DEBUG=false PYTHONPYCACHEPREFIX=<private> pytest-slot.sh -- api/.venv/bin/python -m pytest -q -p no:cacheprovider -n 2`,
then the three validators that `guards.yaml` runs. One pytest at a time, behind a load(<14)/RAM(>=4G) gate.
rootdir captured with `--co` per clone: the clone itself in all 22. Every clone `git status --porcelain --ignored` empty
after its lane.

## Lanes (measured)

| commit | pytest | exit | dashboards | alarms | vocabulary | message says |
|---|---|---|---|---|---|---|
| `74346bb` (base) | 275 passed | 0 | 0 | 0 | 0 | — |
| `d76c439` | 277 passed | 0 | 0 | 0 | 0 | 275 → 277 |
| `f5b73f3` | 277 passed | 0 | 0 | 0 | 0 | 277 → 277 |
| `17a65c1` | 285 passed | 0 | 0 | 0 | 0 | 277 → 285 |
| `bac0f33` | 286 passed | 0 | 0 | 0 | 0 | 285 → 286 |
| `ac5ab23` | 293 passed | 0 | 0 | 0 | 0 | 286 → 293 |
| `6615cb0` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `0963a3e` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `a04b9c0` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `d417b1a` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `61c5297` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `4e2a936` | 296 passed | 0 | 0 | 0 | 0 | 293 → 296 |
| `ca095c8` | 296 passed | 0 | 0 | 0 | 0 | 296 → 296 |
| `2965526` | 296 passed | 0 | 0 | 0 | 0 | 296 → 296 |
| `0dda33a` | 301 passed | 0 | 0 | 0 | 0 | 296 → 301 |
| `d1ebeb1` (HEAD) | 302 passed | 0 | 0 | 0 | 0 | 301 → 302 |
| `2d493c8` (base of `9fda3db`) | 83 passed | 0 | 0 | 0 | 0 | — |
| `9fda3db` | 91 passed | 0 | 0 | 0 | 0 | 91 |
| `234603b` | 101 passed | 0 | 0 | 0 | 0 | "101 passed (91 at 9fda3db)" |
| `5e476e0` | 142 passed | 0 | 0 | 0 | 0 | 131 → 142 (CP 15b) |
| `89f3592` (base of `013dc89`) | 206 passed | 0 | 0 | 0 | 0 | — |
| `013dc89` | 243 passed | 0 | 0 | 0 | 0 | — |

Every count matches its message. **Red-before re-proof** (each new test run at its PARENT sha, `redbefore.tsv`): `d76c439`
2 failed, `bac0f33` 1 failed, `4e2a936` 3 failed, `0dda33a` 5 failed — exactly the counts the four messages claim.

## Mutation totals

**82 runs, 81 valid: 53 KILLED, 28 SURVIVED.** One invalid: **I-IB03** (delete `scripts/b1b_metric_filter_probe.sh` and its
pin entry) exits 1 with *15 errors*, not failures — a collection error is BROKE, not a kill, so IB-03's floor claim is
**unproved either way** and is listed as REMAINING. Every survivor below was run against the **FULL lane** with the mutant
applied and passed there. 58 runs were at HEAD `d1ebeb1`; 19 at the four extra commits; 5 are r4 survivors re-run at HEAD.
Harness: `runmut2.sh` — refuses a dirty tree (`git status --porcelain --ignored`, which sees `*_override.tf`), applies the
prep, waits on the load/RAM gate, runs cold under `pytest-slot.sh` with a private `PYTHONPYCACHEPREFIX`, restores with
`git checkout -- . && git clean -fdx` inside the mutation clone only, and proves the restore empty. Only exit 1 is a kill.

Of the 28 survivors: 6 are controls or stated design; 5 are r4 survivors left open on purpose (I-X-V1/V2/V6 = r4 IR4-21,
DEFERRED in plan §6; I-X-C6 and I-X-L8i = r4's contrived residuals); 4 are settled by a later commit in this same range;
13 map to the findings below.

---

## Findings, ranked (part 1: the fix batch)

### No P0, no P1

Nothing leaks and no lock breaks. Every property the 15 commits name holds against today's tree, and the HEAD lane plus all
three validators are green (302 passed; `validate_alarms` "19 §2.1 alerts … hold"; `validate_metric_vocabulary` full line).

### P2-1: `d76c439`'s "no resource or module hides" is still false for two legal label spellings

`tests/_hcl_blocks.py:44` — `_LABEL_TOKEN = r'(?:[ \t]*"[^"\n]*"|[ \t]+[A-Za-z_][A-Za-z0-9_-]*)'`. A bare label must be
preceded by whitespace and may hold ASCII only, so two headers terraform accepts are not headers to `resources()`:

| mutant | edit | result |
|---|---|---|
| **A1** | `resource "aws_lambda_function"reindexer {` — quoted TYPE, bare NAME, no space between — with `WEAVIATE_URL` set, **no** gRPC port, **no** `vpc_config`, **no** `LOGURU_DIAGNOSE` | **FULL 302 passed** |
| **A2** | `resource aws_lambda_function réindexer {` — a bare label with a non-ASCII letter, same body | **FULL 302 passed** |
| A1c (control) | the same resource, `resource aws_lambda_function reindexer {` | **KILLED**, 3 failed (both Weaviate checks + the classification equality) |
| A3 (control) | `module "reindexer"{` (no space before the brace) | **KILLED** |

**Parser oracle (re-verified this round).** `terraform fmt -check -diff` 1.12.2 on synthetic scratch files — a pure parse,
no state, no provider, no network (`tfparse/`): t02 (`"t"n`) and t14 (unicode bare) both PARSE and are rewritten to the
quoted form; t01 (bare) parses; t07 (a newline between labels) is the control — `Error: Invalid block definition`.

Same failure scenario as r4's P2-1: one resource escapes the G.117 classification equality, both Weaviate checks and the
module-source refusal at once, because a missing resource reads as "nothing to decide". **Mitigation:** `terraform fmt
-check` rewrites both shapes, so a push or PR that reaches `terraform-plan.yaml` fails there — but that step does **not**
run in `terraform-apply.yaml`, and the guard lane that both workflows do share cannot see it. **Latent:** no tracked `.tf`
file uses either shape (checked across all 42).
**Fix:** drop the `[ \t]+` requirement for a bare label (HCL needs no separator after a string token) and widen the class to
HCL's unicode ID_Start/ID_Continue (`str.isidentifier()` on the captured run, or `\w` with `re.UNICODE` minus digits at the
head). Add both shapes to `TRAPS` in `tests/unit/infra/test_hcl_blocks.py:14-89`, which today pins bare, mixed and
all-quoted-unspaced but not these two.

### P2-2: the new CI gate reads `run:` strings and `needs:`, and none of the four fields that neutralise them

`tests/unit/ci/test_workflows_gate_on_the_guards.py:40-65`. Five one-line edits leave the lane "present" and "needed" while
making it decide nothing. All **FULL 302 passed**:

| mutant | edit | what it does on GitHub |
|---|---|---|
| **G5** | `if: ${{ always() }}` on `terraform_apply` (which keeps `needs: guards`) | apply runs even when the guard lane is RED — the exact hole IR-25 closed |
| **G8** | `continue-on-error: true` on the `guards` job | the lane can never fail the caller |
| **G6** | `continue-on-error: true` on the Pytest step | the suite can never fail the lane |
| **G9** | `shell: bash {0}` + `continue-on-error` on the Validate-alarms step | same, per validator |
| **G7** | `ref: main` on the guard lane's checkout | the lane validates a different tree than the one being planned/applied |

`test_the_guard_lane_is_one_reusable_workflow_running_every_check` asserts `run` strings ⊇ `LANE` and `fetch-depth == 0`;
`test_every_terraform_job_waits_for_the_guard_lane` asserts membership in `needs`. Neither reads `if`, `continue-on-error`
(job or step), or `with.ref`. The commit message's "neither runs terraform on a red tree" is therefore a property of
today's YAML, not one the guard holds. **Fix:** assert no `if`/`continue-on-error` on the guard job, its steps, or any
terraform job (or allow only an `if` that is an explicit allowlist), and that no checkout in `guards.yaml` sets `ref`.

### P2-3: a terraform job whose `run` does not literally begin `terraform ` is not a terraform job

Same file, `:55-59` — `str(step.get("run","")).lstrip().startswith("terraform ")`.

| mutant | edit | result |
|---|---|---|
| **G11b** | append a `drift_apply` job to `terraform-plan.yaml` whose step is `run: TF_IN_AUTOMATION=1 terraform apply -auto-approve -var-file="dev.tfvars"`, with **no** `needs:` | **FULL 302 passed** |
| G11 (near-miss control) | the same job, appended without the leading blank line | **KILLED** |
| G10 (control) | strip `needs: guards` from `terraform-apply.yaml` AND prefix both steps with `cd . && ` | **KILLED** — by the non-vacuity `assert terraform`, not by the rule |

An env-var prefix, `cd x && terraform …`, `sudo terraform`, `bash -c "terraform …"`, or terraform on the second line of a
`run: |` block all read as "not a terraform job", and the job is then never required to wait. G10 shows the non-vacuity
assert only fires when EVERY terraform step is disguised; one honest job keeps it quiet while a second job hides.
**Fix:** search each step's whole `run` for a `terraform` word at a command position (line start, after `&&`/`;`/`|`, after
`env`-style `K=V` prefixes), not a prefix test on the first line.

### P2-4: the `.env` one-write rule does not look inside a quoted command string

`tests/unit/observability/test_loguru_diagnose_off_on_compute.py:141` (`_DOTENV_WORD = r"(?:^|[/=:])\.env$"`) and `:150`,
which matches that regex against the shell **words** `_ShellLexer` yields. A word that IS a command string holds `.env` in
its middle, preceded by a space, so it never matches:

| mutant | edit to `poc_ec2_setup.sh` after `chmod 600 ./.env` | result |
|---|---|---|
| **F1** | `sudo -u ec2-user bash -c "echo LOGURU_DIAGNOSE=YES >> .env"` | **FULL 302 passed** |
| **F2** | `eval 'echo LOGURU_DIAGNOSE=YES >> .env'` | **FULL 302 passed** |
| F1c (control) | the same append written as plain code | **KILLED** |

`17a65c1`'s message says the rule refuses any other site "whatever its verb", and `d1ebeb1` pins the one limit the
docstring declares (a `.env` write inside a heredoc body that becomes another script). Neither `bash -c` nor `eval` is that
limit: both are the script's own code, run by the script, and both change the file compose hands the `api` container —
the LOGURU_DIAGNOSE content-capture seat. **Fix:** re-lex the body of any word that is an argument to `bash -c`, `sh -c`,
`eval` or `su -c`, or (blunter and safer) fail on any word that merely CONTAINS `.env` outside the heredoc line and the
`chmod`.

### P2-5: the Weaviate egress reader counts `0.0.0.0/0` as a substring of an unevaluated expression

`tests/unit/networking/test_weaviate_ports_declared_and_admitted.py:184` — `ANYWHERE in cidrs` (`ANYWHERE = '"0.0.0.0/0"'`,
`:51`) over `cidr_blocks` **as written**.

| mutant | edit | result |
|---|---|---|
| **E1** | `lambda_sg` egress `cidr_blocks = var.lock_lambda_egress ? ["10.99.0.0/32"] : ["0.0.0.0/0"]`, with the variable defaulting to `true` | **FULL 302 passed** |
| E2–E5 (controls) | egress moved to a separate `aws_vpc_security_group_egress_rule`; IPv6-only; a prefix list; the rule commented out | all **KILLED** — fail closed, exactly as the docstring says |

The applied value is the /32; the guard reads the losing branch of the ternary and calls the port open. Every other
unreadable egress shape in this guard fails CLOSED (E2–E5), so this is the one direction that inverts. **Fix:** treat a
`cidr_blocks` value that is not a literal list as unreadable (fail closed), as `_hcl_blocks` already does for `merge(...)`.

### P3-1: the alarm surface is two files, so an alarm declared anywhere else is invisible to every alarm guard

`scripts/validate_metric_vocabulary.py:1070-1090` (`alarm_descriptions` parses `ALARMS_FILE` only, `:132`) and
`scripts/validate_alarms.py:42` (`ALERT_SURFACE = ("alerting.tf", "alarms.tf")`, consumed at `:854`).

- **N6:** a new `aws_cloudwatch_metric_alarm "reindex_backlog"` in **`cloudwatch.tf`** — no state note, `notBreaching`, an
  estate namespace nothing mints — **FULL 302 passed**, and `validate_alarms`/`validate_metric_vocabulary` both exit 0.

`0dda33a`'s set-equality is real and well built (its four planted defects are red, and the register's constant comment
correctly says "pinned by EQUALITY **against alarms.tf**"), but the message's "a new alarm carries a note or is listed with
a reason" is true only of alarms written in `alarms.tf`. `validate_alarms`'s own "is not covered by this validator" limb
(`:603-606`) has the same blind spot, so a stray alarm escapes the register, the actions/`ok_actions` parity check and the
namespace/mint check together. **Latent:** all 6 alarm resources and both alarm maps live in `alarms.tf` today.
**Fix:** derive the alarm set from every `terraform_files(root)` file (or add a guard that no `.tf` outside `ALERT_SURFACE`
declares `aws_cloudwatch_metric_alarm`).

### P3-2: two dashboard/alarm PromQL edits that change what is charted are unguarded

- **H1:** `histogram_sum(rate({"gen_ai.client.token.usage"}[5m]))` → `rate(...)` in `dashboards/llm-agents.json.tftpl`.
- **H2:** both `histogram_count(rate(...))` wrappers dropped from the ApiHighErrorRate query in `alarms.tf` (numerator and
  the gated denominator).

Both **FULL 302 passed**, all three validators exit 0. The vocabulary validator reads metric NAMES, dialect and state
notes; nothing reads the aggregation an expression applies to a histogram, so a board or an alarm can silently start
charting a series count instead of a sum/rate. Same family as r4's V1/V2/V6 (IR4-21) and, like them, the plan's recorded
elegant fix (a published instrument inventory, with its type) is what closes it. Not claimed by any commit in this range.

### P3-3: three more unguarded knobs, named for completeness

- **H3 / P2-7:** deleting the `pull_request:` trigger from `terraform-plan.yaml` — the very thing its `:7-9` comment says
  makes the guards worth anything on a branch — **FULL 302 passed**. `test_the_guard_lane_is_one_reusable_workflow…`
  pins triggers on `guards.yaml` only (`== {"workflow_call"}`), never on the callers.
- **H4 / P2-6:** `validate_metric_vocabulary.py`'s `if "examples" not in p.parts` → `if True` — **FULL 302 passed**.
- **I-W11c:** (r5 implementer's own mutant, re-run at HEAD) survives as it did for them.

---

## Findings (part 2: the four extra commits) — PROVISIONAL

- **`234603b` — the "fabricated citation" verdict is FALSE, and this round re-confirms it.** Primary copilot-mro
  (`langgraph-merge` `417df303`, HEAD unmoved since 2026-09-15 per reflog) `agent_shared/telemetry.py:38-41` creates
  `agent.model.latency_seconds` with `unit="s"`. The obsm checkout at triage time (`1a4791d8`) had 0 hits because
  `54a01f39` (2026-09-14) deleted it **on obs-merge**, and that commit is not an ancestor of `417df303`. The iac tree at
  HEAD no longer repeats the error (`ca095c8` rewrote the constant's comment to name the branch each entry is read on).
  The claim is still repeated in two immutable places: `234603b`'s own message, and the SDD ledger `progress.md:3949-3958`
  (CP 11b), corrected only by an appended line at `:8139`. **P3, process.**
- **`5e476e0` — a WIRED citation that was not yet true when it was written.** It cites copilot-mro G.6 emitters
  (`agent.ledger.write_failures`, the `record_subagent` binding) that were committed only at copilot-mro `3978073b`
  (2026-09-21 04:19); at `5e476e0`'s time obs-merge `c80c686d` had 0 hits. It is true at `557a178f`. **P3, process** — the
  note is correct today, and the six mutants aimed at its check-6 grammar are all red (P5-1…P5-6).
- **`9fda3db` — two survivors, both settled downstream in part 1.** P9-4 (`_word(service).search(text)` → `service in
  text`) survives at `9fda3db` and is killed at `234603b` by
  `test_a_gated_service_name_is_matched_as_a_word_not_a_substring`. P9-7 (delete the Pytest step from
  `terraform-plan.yaml`) survives at `9fda3db` and is killed at HEAD by `4e2a936`'s `LANE` assertion. Five of seven aimed
  mutants red.
- **`013dc89` — one survivor, self-test strictness.** P0-3 loosens the test's own membership test
  (`value not in GENAI_CAPTURE_OFF` → `not value.startswith(("false","no_content"))`) and passes the full 243: the
  content-flag test's accepted-value SET is not itself pinned, so a later hand could widen it unnoticed. **P3.** P0-1 and
  P0-2 (the escape-syntax planting) are red.

---

## Commit-message audit (part 1) — 15 of 15 read, 4 of 4 red-before claims re-proved

| sha | claim | verdict |
|---|---|---|
| `d76c439` | one label token, quoted (no space needed) or bare (space needed); TRAPS gain bare/mixed/unspaced; the two validators do not share the flaw | **TRUE in its mechanics, OVERCLAIMS in its subject.** Red-before re-proved (2 failed). `validate_alarms.py` tokenises and reads a bare-labelled alarm (pinned, `tests/unit/alerting/test_validate_alarms.py:72-77`). But "so no resource or module hides" is false for `"t"n` (A1) and for a unicode bare label (A2) — see P2-1 |
| `f5b73f3` | both directions read by one rule reader; a narrower CIDR, a prefix list and separate rule resources are NOT counted, i.e. fail here | **TRUE for every shape it names** (E2–E5 red), **with one inverted case**: a ternary holding `"0.0.0.0/0"` in its losing branch reads as open (E1) — see P2-5 |
| `17a65c1` | any `.env` site but the heredoc line and a `chmod` fails, whatever its verb; the docstring states the one limit | **TRUE for eight planted shapes** (the parametrised test), **FALSE for `bash -c` / `eval`** (F1, F2) — see P2-4 |
| `bac0f33` | one prepared text (`hcl_source`) for both readers; BOM + `\u` name escapes | **TRUE.** Red-before re-proved (1 failed); I-U1/I-U2 red |
| `ac5ab23` | a local source must resolve inside the repo and outside hidden dirs; the false "one limit left" docstring is rewritten | **TRUE.** I-L6b and I-L6e red; the docstring now says outright it is not claimed to be the only limit |
| `6615cb0` | the forwarder directory is derived: `filename` → an `archive_file` in the same module dir → its literal `${path.module}/<dir>`; anything else fails closed | **TRUE, and the fail-closed half is proved.** L8f (`filename` → a static prebuilt zip) and L8g (`source_dir` → `source_file`) both **KILLED**; I-L8s and I-L8x red |
| `0963a3e` | the test now asserts through `validator.state_notes`, check 6's own reader | **TRUE.** I-D5 red |
| `a04b9c0` | the CLI bullet flips to `WIRED 2026-09-22, retrieval unproved`, producer merged at copilot-mro `557a178f` | **TRUE** (settles r4 IR4-15). Not independently re-read against `557a178f` this round — carried from the r4 reading |
| `d417b1a` | the pin reads backticked identifiers AND `.py` paths; both boards' files listed | **TRUE.** I-R3 red |
| `61c5297` | comment only, states the M-ALARM-DENOMINATOR ruling and what the owner still owes | **TRUE.** 293 → 293, comment-only |
| `4e2a936` | ONE reusable lane both workflows call; every terraform job `needs` it; the test reads YAML and cannot run Actions | **TRUE as YAML, and the YAML is right** (plan `:22-27`, apply `:18-23`, `guards.yaml` `on: workflow_call`, `fetch-depth: 0`). Red-before re-proved (3 failed). The TEST is defeatable — see P2-2 and P2-3 |
| `ca095c8` | names the branch UNIT_SUFFIXED_INSTRUMENTS is read on and the third instrument on the pushed line | **TRUE** — and it is the correction of the false "fabricated citation" verdict |
| `2965526` | the floor counts durable files only; MINIMUM_DURABLE_MENTIONS = 6, today 8 | **UNPROVED.** The mutant that would settle it (delete the probe + its pin entry, I-IB03) exits with 15 ERRORS, not failures — BROKE, not a kill. Re-run needed |
| `0dda33a` | the unclaimed set must EQUAL ALARMS_WITHOUT_STATE_NOTE, in both directions | **TRUE for `alarms.tf`.** Red-before re-proved (5 failed); I-N1 (74 failed) and I-N2 (4 failed) red. Blind to an alarm in any other file — see P3-1 |
| `d1ebeb1` | a test pins the declared limit: a `.env` write inside a heredoc body yields no site | **TRUE, and correctly framed as a limit.** It does not cover `bash -c`/`eval`, which are not that limit — see P2-4 |

---

## What I tried to break and could not (part 1)

- **The bare-label fix, all the spellings it names:** bare resource (A1c), `module "x"{` (A3), bare dynamic child, bare
  `data`, bare module — red or correctly read. I-B1 and I-B2 (the implementer's own P2-1 mutants) are red.
- **The forwarder directory derivation, in both halves:** a `filename` that is not an `archive_file` output (L8f) and a
  `source_file` instead of a `source_dir` (L8g) both fail CLOSED.
- **The Weaviate egress reader:** a separate-resource rule, IPv6-only, a prefix list and a commented-out rule all fail
  closed (E2–E5); I-W10uR, I-W11, I-W11b red.
- **The `.env` one-write rule:** the eight planted shapes, plus `chmod`-chained (I-S2), are red.
- **The state-note register:** a dropped note, a backticked state word, and a note GAINED by a registered map alarm and by
  a literal one are all red (I-N2); blinding the description reader kills 74 tests (I-N1).
- **`_hcl_blocks` one-body:** the BOM and `\u` name-escape shapes (I-U1, I-U2) are red.
- **The CI gate, honest edits:** removing `needs: guards` (I-G1), and changing the lane's step list (I-G3), are red.

## REMAINING (see `~/.claude/scratch/obs-merge/iac-review-r5/PAUSED.md` for the ordered list and the recipe)

1. Re-run **IB-03** (`2965526`) with a valid mutant — the current one BROKE the collection.
2. Read the diffs of `9fda3db`, `013dc89`, `5e476e0` end to end (only `234603b` was read closely) and finalise part 2.
3. Decide **I-X-C6 / I-X-L8i** (r4 residuals, re-run at HEAD and still surviving): Future-Improvements or closed.
4. Finish the claims table (rows IR5-01…) and the tier columns, then strip PARTIAL.

