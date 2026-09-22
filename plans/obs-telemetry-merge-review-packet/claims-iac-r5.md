# Claims packet: iac r5 (the post-r4 fix batch `74346bb..d1ebeb1`, plus `234603b`, `013dc89`, `9fda3db`, `5e476e0`)

**FINAL.** Independent adversarial review (Opus), 2026-09-22, read-only throughout. The round ran in three legs — a first
reviewer killed mid-lane, a second paused by the owner at the agent-cap cut, and this finish — over one shared durable
harness; every number below is measured, none is remembered. No tree was edited, checked out, stashed or
committed; no terraform init/plan/apply against real state, no AWS, no docker, no network, no sub-agent. `iac` is still at
`d1ebeb1` on `obs-merge`; its untracked files (`poc_ec2_setup_ubuntu.sh` and six `__pycache__/` dirs) are pre-existing and
were not touched. Durable notes, every log, the clones and the mutation harness:
`~/.claude/scratch/obs-merge/iac-review-r5/` (`NOTES.md`, `PAUSED.md`, `lanes.tsv`, `logs/lane-*.log`, `mutants.tsv`,
`logs/m-*.log`, `m/*.prep`, `redbefore.tsv`, `tfparse/`, `probes/`).

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `74346bb..d1ebeb1` | iac | `/home/aditya/Code/iac` | `obs-merge` | 15: `d76c439` P2-1 · `f5b73f3` P3-A · `17a65c1` P3-B · `bac0f33` P3-C · `ac5ab23` P3-D · `6615cb0` P3-E · `0963a3e` P3-F · `a04b9c0` CLI flip · `d417b1a` P3-G · `61c5297` C2 ruling · `4e2a936` IR-25 · `ca095c8` IR-12 · `2965526` IB-03 · `0dda33a` IS-12 · `d1ebeb1` P3-B limit pin |
| extra | iac | same | same | `9fda3db`, `234603b`, `5e476e0`, `013dc89` (never independently reviewed) |

## Verdict

- **Part 1, the fix batch `74346bb..d1ebeb1` (15 commits): MERGE-CLEAN — P0 0 / P1 0 / P2 5 / P3 3.** Nothing ships
  broken. All 15 commits are green at their own HEAD, every count in every message is exact, and all four "red before"
  claims that name a prior sha were re-proved red at that sha. Every r4 finding the batch names is settled by a guard I
  saw fail. The five P2s are latent fail-OPEN coverage gaps in the NEW guards — each one a shape no tracked file uses
  today, none a defect in the HCL or YAML that ships.
- **Part 2, the four extra commits `9fda3db` / `234603b` / `5e476e0` / `013dc89`: MERGE-CLEAN — P0 0 / P1 0 / P2 0 /
  P3 4.** All four diffs read end to end. `5e476e0`'s "no behavioural terraform change" is exact (16 changed lines in
  `alarms.tf`, all of them 8 description pairs; the dashboards change only `markdown` and `title`). `9fda3db`'s PromQL
  repair is correct and complete on both API alarms. The four P3s are truth-and-process items, all already true or
  already corrected in the tree; none blocks the merge.

**Controller rulings applied (2026-09-22):** all five fail-OPEN P2s and the P3s go to **Future Improvements** in the iac
plan, with **P2-2** flagged to the owner as the one worth a ~30-minute test-only fix. The two r4 residuals re-run at HEAD
(I-X-C6, I-X-L8i) are **closed as contrived**. This is the last iac round.

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

**84 runs, 83 valid: 54 KILLED, 29 SURVIVED.** Every survivor below was run against the **FULL lane** with the mutant
applied and passed there. 60 runs were at HEAD `d1ebeb1`; 19 at the four extra commits; 5 are r4 survivors re-run at HEAD.
Harness: `runmut2.sh` — refuses a dirty tree (`git status --porcelain --ignored`, which sees `*_override.tf`), applies the
prep, waits on the load/RAM gate, runs cold under `pytest-slot.sh` with a private `PYTHONPYCACHEPREFIX`, restores with
`git checkout -- . && git clean -fdx` inside the mutation clone only, and proves the restore empty. Only exit 1 is a kill.

One run was **invalid and has been replaced**: the first IB-03 mutant (`rm scripts/b1b_metric_filter_probe.sh` + drop its
pin entry) exited 1 with **15 errors**, not failures — a collection error is BROKE, not a kill. The cause is an overreach,
not the guard: `tests/unit/observability/test_shared_env_content_flags.py` pins that same file by NAME in its
env-carrying set, so deleting it raises `FileNotFoundError` in that other guard's fixture before the floor is ever
evaluated. See **IB-03, settled** below for the valid pair that replaces it.

Of the 29 survivors: 7 are controls or stated design; 5 are r4 survivors left open on purpose (I-X-V1/V2/V6 = r4 IR4-21,
DEFERRED in plan §6; I-X-C6 and I-X-L8i = r4's contrived residuals, closed by controller ruling); 4 are settled by a later
commit in this same range; 13 map to the findings below.

### IB-03, settled (`2965526`)

The claim is that the vacuity floor is funded by durable files only — `MINIMUM_DURABLE_MENTIONS = 6`, and "today that
total is 8". Bracketing the floor settles it in two runs, neither of which touches a file another guard pins:

| mutant | edit | result |
|---|---|---|
| **IB03-f9** | `MINIMUM_DURABLE_MENTIONS = 6` → `9` | **KILLED** — `test_the_scan_is_not_vacuous`, `AssertionError: the prose scan found 8 … below the floor of 9`; `assert 8 >= 9` |
| **IB03-f8** | `MINIMUM_DURABLE_MENTIONS = 6` → `8` | **SURVIVED**, FULL 302 passed |

Together they pin the counted total at **exactly 8**, which is the arithmetic the pin dict states: 30 mentions total, less
the 22 in `C2_SCOPED_FILES` (`alarms.tf` 6 + the probe 16), leaves 8. The exclusion really excludes. **The message's
arithmetic is TRUE and the floor still bites.** Worth recording for the C2 lane: of those 8, two are the validator's own
C2-scoped mentions (the B1b carve-out reasoning and `B1B_OPEN_METRIC_FILTER_SELECTORS`), so when C2 lands the count falls
to **exactly 6 — the floor itself, with zero slack**. That is by design and the constant's comment says so, but it means
the next durable mention deleted after C2 turns the floor red, which is the direction a vacuity floor should fail.

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

## Findings (part 2: the four extra commits) — all four diffs read end to end

**No P0, no P1, no P2.** Four P3s, every one of them a truth-or-process item that the tree has already absorbed.

### What the diffs actually do (read, not inferred)

- **`9fda3db`** (10 files, +740/-104). The substantive change is the PromQL repair of both API alarms, and it is
  **correct and complete**. `ApiHighErrorRate` now takes its count through `histogram_count()` applied INNERMOST on both
  limbs (`alarms.tf:291`, `:293`), so nothing above it carries a histogram operand. `ApiP95LatencyHigh` (`:307-320`) is
  right in the subtler way: the LEFT limb keeps the bare family under `rate()` **inside** `histogram_quantile(0.95, sum
  by (…) (rate(…)))`, which is the documented native form and needs no `histogram_count()`, while the `and on(…)` RIGHT
  limb — which must be a float — takes `histogram_count(increase(…))`. `le` is gone from the left limb's grouping. I
  found no remaining site where a histogram operand sits under arithmetic or a comparison.
- **`5e476e0`** (8 files, +866/-40). **"No behavioural terraform change: 9 description strings, 0
  query/threshold/pattern/gate" is exact.** In `alarms.tf` every changed non-comment line is a `description` — 16 lines,
  8 pairs — and there is not one changed `query`, `threshold`, `pattern`, `treat_missing_data` or gate line. In
  `dashboards/` only `markdown` (10) and `title` (8) change; no `metrics`, no `query`, no selector. The 595-char widget
  titles CloudWatch truncates did move into the boards' text panels, as claimed.
- **`013dc89`** (3 files, +1190/-394). A parser rebuild into `tests/_env_syntax.py` with a planted-defect matrix
  (`DECOYS`, ~300 lines) far larger than the 13 evasions that prompted it. Two of three aimed mutants are red on that
  matrix (P0-1 the HCL `$${`/`%%{` escape family, P0-2 the `\uXXXX` escaped key in HCL and JSON). CI's pyyaml install is
  present and has since moved with the lane into `guards.yaml:36`.
- **`234603b`** was read closely in an earlier leg; its verdict is below.

### P3-4: `5e476e0` cites emitters that did not exist for another sixteen hours

This is the one finding of substance in part 2. `5e476e0` (2026-09-20 12:00:38 -0700) asserts that copilot-mro's G.6
"created the counter" for `agent.ledger.write_failures` and "bound `RuntimeTelemetry.record_subagent` as the subagent
observer on BOTH runtimes", and rewrites nine state notes on that basis. The emitters first land at copilot-mro
`3978073b`, authored **2026-09-21 04:19:12 -0700** — sixteen hours later. At `5e476e0`'s time the obs-merge tip
(`c80c686d`) had zero hits for the binding.

The claim is **true today** (verified this round: `557a178f` carries it at `agent_pipeline.py:273` and `:691`, and
`agent_shared/subagent_runs.py:125`), so the tree at HEAD is correct and nothing needs changing. What makes it worth
recording is *which* commit it is: `5e476e0` is the commit that BUILDS check 6, the guard whose whole job is to require
"a code artifact named where it says WIRED". Check 6 passed on an artifact that did not yet exist, because it cannot read
another repo — a limit the commit message itself states plainly ("What it CANNOT do is stated in the code, in the README,
and in a test that asserts it… Proving that needs the cross-repo emitter inventory already designed under DEFERRED").
The declared limit is not theoretical: it was exercised by the commit that declared it. This is the same unowned gap as
r4's IR4-20, and the same fix closes both — the published emitter inventory.

### P3-5: `9fda3db`'s failure-mode claim was an overclaim, and the tree has already retracted it

`9fda3db`'s message says of the `histogram_count()` bet: "It fails LOUDLY if wrong, and the one edit that flips it is
written next to it." Neither half survives in the tree. `alarms.tf:288` at HEAD now reads "Whether an unsupported
function is rejected at PutMetricAlarm or just returns nothing is unestablished, and a query returning nothing sits GREEN
here, so read this alarm's OK as 'no breaching contributor', never as 'observed healthy'… there is no prepared
substitute", and the comment at `:274-281` records why the prepared substitute does not work (`histogram_sum()` is from
the same Prometheus 2.40 cohort as `histogram_count()`, so a subset lacking one lacks the other, and it returns NaN where
`histogram_count()` returns 0). A later commit outside this range caught it. **No action** — recorded so the correction
is not lost, since the commit message is immutable and still carries the stronger claim.

### P3-6: `013dc89`'s accepted-value set is not itself pinned

`tests/unit/observability/test_shared_env_content_flags.py:93`, `:108`. **P0-3** loosens the guard's own comparison —
`item.value.strip().lower() not in GENAI_CAPTURE_OFF` → `not …startswith(("false", "no_content"))` — and passes the full
243. No decoy carries a value that merely STARTS with an accepted word, so a later hand can widen the gate from equality
to prefix and nothing says so. Contrived (it needs an edit to the guard itself, and a real value like `false-ish` is
unlikely), hence P3. One decoy closes it.

### P3-7: the "fabricated citation" verdict on `234603b` is FALSE, and the ledger still says otherwise

Confirmed, with the evidence re-read this round. Primary copilot-mro (`langgraph-merge` `417df303`, HEAD unmoved since
2026-09-15 per reflog) `agent_shared/telemetry.py:38-41` creates `agent.model.latency_seconds` with `unit="s"`. The obsm
checkout at triage time (`1a4791d8`) had zero hits because `54a01f39` (2026-09-14) deleted it **on obs-merge**, and that
commit is not an ancestor of `417df303`. The iac tree no longer repeats the error — `ca095c8` rewrote the constant's
comment to name the branch each entry is read on. It survives in two immutable places: `234603b`'s own message, and the
SDD ledger `progress.md:3949-3958` (CP 11b), corrected only by an appended line at `:8139`. **Owner-facing.**

### Two survivors that are settled downstream, not findings

**P9-4** (`_word(service).search(text)` → `service in text`) survives at `9fda3db` and is killed at `234603b` by
`test_a_gated_service_name_is_matched_as_a_word_not_a_substring`. **P9-7** (delete the Pytest step from
`terraform-plan.yaml`) survives at `9fda3db` and is killed at HEAD by `4e2a936`'s `LANE` assertion. Both are the ordinary
shape of a series of commits, not gaps.

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

## Claims table

**Severity:** 0 = a content leak that ships · 1 = guard or lock integrity · 2 = a coverage gap · 3 = docs or process.
**Tier** (§2.3a): 0 = settled by a guard I SAW fail · 1 = consequential but reversible · 2 = irreversible or
estate-shaping. **Chunk:** F1 contract + privacy · F2 the merge itself · F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Sev | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IR5-01 | iac | `tests/_hcl_blocks.py:44`, `:50-58` | `_LABEL_TOKEN` accepts a quoted label or a bare identifier, so both header forms are read | r4 P2-1 / IR4-03: a bare-labelled resource escaped every per-resource rule | `TRAPS` gain a bare, a mixed, an all-quoted-unspaced resource, a bare `dynamic`, a bare `data` and a bare module | `tests/unit/infra/test_hcl_blocks.py::test_resources_are_found_and_a_commented_one_is_not`, `::test_bare_and_quoted_labels_are_the_same_block` | **yes.** Red-before at `74346bb` (2 failed); A1c, A3, I-B1, I-B2, I-L6e red | 2 | 0 | F1 | **SETTLED for the spellings it names** |
| IR5-02 | iac | same, `:44` | a bare label needs a preceding space and ASCII only | the house style has no other form | terraform 1.12.2 parses `resource "t"n {` and a unicode bare label; `fmt` rewrites both | none | no: **A1**, **A2** survive, FULL 302 each | 2 | 1 | F1 | **REFUTED in part** (P2-1) |
| IR5-03 | iac | `test_weaviate_ports_declared_and_admitted.py:178-191` | each client SG's EGRESS is read: a port leaves via `0.0.0.0/0` or a server group, by one rule reader | r4 P3-A / IR4-05: the egress half was named and never read | `lambda.tf` egress; the docstring lists what is NOT counted | `::test_the_weaviate_host_admits_both_ports_from_each_client` | **yes.** E2, E3, E4, E5, I-W10uR, I-W11, I-W11b red | 2 | 0 | F2 | **SETTLED** |
| IR5-04 | iac | same, `:51`, `:184` | `ANYWHERE in cidrs` — a substring test on `cidr_blocks` as written | the other unreadable shapes fail closed | a ternary's losing branch is still a substring | none | no: **E1** survives, FULL 302 | 2 | 1 | F2 | **REFUTED** (P2-5) — the one direction that inverts |
| IR5-05 | iac | `test_loguru_diagnose_off_on_compute.py:139-151`, `:330-356` | the script may name `.env` only on the heredoc line and in a `chmod`; any other site fails whatever its verb | r4 P3-B / IR4-07: the guard read one heredoc while compose reads the final file | eight planted shapes (`>>`, `>`, `tee`, `sed -i`, `cp`, a variable path, chmod-chained) | `::test_a_second_write_to_the_dotenv_is_refused` | **yes.** Eight parametrised shapes + I-S2 red | 2 | 0 | F1 | **SETTLED for the verbs it names** |
| IR5-06 | iac | same, `:141` (`_DOTENV_WORD`), `:150` | the match runs against lexed WORDS | a word is the unit the lexer yields | a quoted command string is ONE word, with `.env` in its middle | none | no: **F1** (`bash -c "… >> .env"`), **F2** (`eval`) survive, FULL 302 each | 2 | 1 | F1 | **REFUTED** (P2-4) |
| IR5-07 | iac | `tests/_hcl_blocks.py:1-12`, `_env_syntax.hcl_source` | ONE prepared text for both readers: BOM dropped, `\uXXXX` name escapes decoded | r4 P3-C / IR4-02 | `test_a_bom_and_escaped_names_read_as_the_env_scanner_reads_them` | that test | **yes.** Red-before at `17a65c1` (1 failed); I-U1, I-U2 red | 2 | 0 | F2 | **SETTLED** |
| IR5-08 | iac | `test_loguru_diagnose_off_on_compute.py:228-243` | a local module source must RESOLVE inside the repo and outside any hidden directory | r4 P3-D / IR4-11: `../lambdas/…` is a sibling repo | seven parametrised sources, the real `../..` call included | `::test_nothing_hides_a_resource_from_the_classification` | **yes.** I-L6b, I-L6e red | 2 | 0 | F1 | **SETTLED** |
| IR5-09 | iac | same, `:286-300` (`forwarder_package`) | the shipped directory is DERIVED: `filename` → an `archive_file` in the same module dir → its literal `${path.module}/<dir>`; anything else fails closed | r4 P3-E / IR4-09: a hardcoded `lambda_src` stayed green | `alerting.tf` `filename` / `source_dir` | `::test_the_forwarder_lambda_really_has_no_loguru` | **yes, both halves.** L8f (`filename` → a static prebuilt zip) and L8g (`source_dir` → `source_file`) KILLED; I-L8s, I-L8x red | 2 | 0 | F1 | **SETTLED** |
| IR5-10 | iac | `test_cli_metrics_stay_off.py` (the bullet assertion) | the claim is asserted THROUGH `validator.state_notes`, check 6's own reader | r4 P3-F / IR4-16: a backticked mention passed | exactly one note on the bullet | the same test | **yes.** I-D5 red | 1 | 0 | F3 | **SETTLED** |
| IR5-11 | iac | `dashboards/llm-agents.json.tftpl` (CLI bullet) | flipped `DARK` → `WIRED 2026-09-22, retrieval unproved`, naming the module and both call sites | r4 IR4-15: stale since copilot-mro `557a178f` | `claude_cli_telemetry.py` + two call sites at `557a178f` | the bullet's pin, now through check 6 | n/a (a content flip) | 3 | 1 | F3 | **SETTLED** (r4's owed flip is paid) |
| IR5-12 | iac | `test_validate_metric_vocabulary.py` (recorder pin) | the pin reads backticked identifiers AND `.py` paths; both boards' files are listed | r4 P3-G / IR4-19: five emitters named by FILE were unpinned | each file-named emitter's emitting line at `557a178f` | `::test_the_legacy_rows_name_the_recorders_that_exist` | **yes.** I-R3 red | 3 | 0 | F3 | **SETTLED** (still a pin on words; the published inventory stays the elegant fix) |
| IR5-13 | iac | `.github/workflows/guards.yaml`; `terraform-plan.yaml:22-27`; `terraform-apply.yaml:18-23` | ONE reusable guard lane (`on: workflow_call`) that both workflows call, with every terraform job `needs:`-ing it | IR-25: apply ran none of the guards | read at YAML level: both `uses: ./.github/workflows/guards.yaml`, both `needs: guards`, `fetch-depth: 0` | `tests/unit/ci/test_workflows_gate_on_the_guards.py` | **yes.** Red-before at `61c5297` (3 failed); I-G1, I-G3, G10 red | 1 | 0 | F2 | **SETTLED** (the YAML is right) |
| IR5-14 | iac | `test_workflows_gate_on_the_guards.py:40-65` | presence of the lane's `run` strings + membership in `needs` is the gate | those are the two things the YAML says | neither `if`, nor `continue-on-error` (job or step), nor `with.ref` is read | none | no: **G5** (`if: always()`), **G6**, **G8**, **G9** (`continue-on-error`), **G7** (`ref: main`) all survive, FULL 302 each | 2 | 1 | F2 | **REFUTED** (P2-2) — the owner's flagged fix |
| IR5-15 | iac | same, `:55-59` | a terraform job is one whose step `run` starts with `terraform ` | the house style writes it first | an env prefix, `cd x && `, `sudo`, or terraform on line 2 of a `run: \|` block all read as "not terraform" | the non-vacuity `assert terraform` | no: **G11b** (a `drift_apply` job, `run: TF_IN_AUTOMATION=1 terraform apply …`, no `needs:`) survives, FULL 302; G10 killed only by the non-vacuity limb | 2 | 1 | F2 | **REFUTED** (P2-3) |
| IR5-16 | iac | `scripts/validate_metric_vocabulary.py:485-505`, `:1404-1427` | the alarms making no state claim must EQUAL `ALARMS_WITHOUT_STATE_NOTE`, in both directions | IS-12: 11 of 19 alarms made no claim and nothing could tell | the 12 registered sites, each with its reason | `::test_an_alarm_without_a_state_claim_must_be_registered`, `::test_the_unnoted_register_reads_every_alarm_description` | **yes.** Red-before at `2965526` (5 failed); I-N1 (74 failed), I-N2 red | 2 | 0 | F3 | **SETTLED for `alarms.tf`** |
| IR5-17 | iac | same, `:132` (`ALARMS_FILE`); `scripts/validate_alarms.py:42` (`ALERT_SURFACE`) | the alarm surface is `alarms.tf` (+ `alerting.tf`) | every alarm lives there today (6 resources + 2 maps, verified across all 25 `.tf`) | an alarm in any other `.tf` is read by neither validator | none | no: **N6** (an unnoted alarm in `cloudwatch.tf`) survives, FULL 302, both validators exit 0 | 3 | 1 | F3 | **PARTIAL** (P3-1) — latent; the constant's own comment scopes itself correctly, only the message over-reads |
| IR5-18 | iac | `tests/unit/observability/test_attribute_key_prose_pinned.py:76`, `:84`, `:144-152` | the vacuity floor counts DURABLE files only; `MINIMUM_DURABLE_MENTIONS = 6`, today 8 | IB-03: 16 of 30 mentions came from a probe deleted when C2 settles, so the C2 cleanup would have reddened the floor for a non-vacuity reason | 30 total − 22 C2-scoped = 8 | `::test_the_scan_is_not_vacuous` | **yes, bracketed.** IB03-f9 (floor 9) KILLED with `assert 8 >= 9`; IB03-f8 (floor 8) SURVIVED, FULL 302 | 3 | 0 | F3 | **SETTLED** (arithmetic TRUE; post-C2 the margin is exactly zero, by design) |
| IR5-19 | iac | `scripts/validate_metric_vocabulary.py` (`UNIT_SUFFIXED_INSTRUMENTS` comment) | the constant names the copilot-mro BRANCH its entries are read on, and the third instrument on the pushed line | IR-12: the claim was true of `obs-merge` and false of `langgraph-merge` | `417df303` `telemetry.py:38-41` creates `agent.model.latency_seconds`; `54a01f39` deleted it on obs-merge and is not an ancestor | none (a comment) | n/a | 3 | 1 | F3 | **SETTLED** — and it is the in-tree correction of the false "fabricated citation" verdict |
| IR5-20 | iac | `alarms.tf` B1b block | states the M-ALARM-DENOMINATOR ruling (keep `notBreaching`, add one denominator metric filter) and what stays owner-owed | the block still read "OWNER RULING OWED" after the 2026-09-22 ruling | comment only, 293 → 293 | none | n/a | 3 | 1 | F3 | **SETTLED** |
| IR5-21 | iac | `dashboards/llm-agents.json.tftpl`; `alarms.tf` ApiHighErrorRate | a board or alarm may change which AGGREGATION it applies to a histogram with no guard | the validators read names, dialect and state notes, never the expression | — | none | no: **H1** (`histogram_sum` → `rate`), **H2** (both `histogram_count` wrappers dropped) survive, FULL 302, all three validators exit 0 | 3 | 1 | F3 | **OPEN** (P3-2) — same family as r4 IR4-21; the published instrument inventory closes both |
| IR5-22 | iac | `terraform-plan.yaml:3-11`; `validate_metric_vocabulary.py` (`"examples" not in p.parts`) | the `pull_request:` trigger and the examples exclusion | the plan comment says the PR trigger is what makes the guards bite on a branch | triggers are pinned on `guards.yaml` only; the exclusion is unpinned | none | no: **H3**/P2-7 and **H4**/P2-6 survive, FULL 302 | 3 | 1 | F3 | **OPEN** (P3-3) |
| IR5-23 | iac | `alarms.tf:288`, `:291-320` | both API alarms take their count through `histogram_count()` INNERMOST; `le` leaves the quantile grouping | `9fda3db` P0-A: both alarms were inert — `histogram / histogram` and `histogram >= float` are undefined, so the samples dropped | read end to end this round: left limb `histogram_quantile(0.95, sum by (…) (rate(…)))` (native form, correctly no `histogram_count`), right limb `histogram_count(increase(…))` | none | no (P3-2 covers it) | 1 | 1 | F2 | **SETTLED as a repair** (correct and complete; unguarded) |
| IR5-24 | iac | `9fda3db` message | "It fails LOUDLY if wrong, and the one edit that flips it is written next to it" | the `histogram_count()` subset bet | `alarms.tf:288` now says the failure mode "is unestablished" and `:274-281` says there is no working substitute | none | n/a | 3 | 1 | F3 | **REFUTED, already corrected in-tree** (P3-5) |
| IR5-25 | iac | `5e476e0` (9 state notes) | 0 behavioural terraform change | the commit rewrites truth claims only | **exact:** `alarms.tf` changes 16 non-comment lines, all 8 `description` pairs, 0 query/threshold/pattern/gate; `dashboards/` changes only `markdown` (10) and `title` (8) | check 6 | **yes.** P5-1…P5-6 all red | 1 | 0 | F3 | **SETTLED** (verified line by line) |
| IR5-26 | copilot-mro / iac | `5e476e0` vs copilot-mro `3978073b` | the WIRED notes name G.6's emitters | check 6 requires a code artifact where a note says WIRED | `5e476e0` is 2026-09-20 12:00:38; `3978073b` is authored 2026-09-21 04:19:12 — sixteen hours later. True today at `557a178f` (`agent_pipeline.py:273`, `:691`) | check 6 (cannot read another repo — a limit the commit states) | n/a | 3 | 1 | F3 | **PARTIAL** (P3-4) — the declared cross-repo limit, exercised by the commit that declared it |
| IR5-27 | iac | `test_shared_env_content_flags.py:93`, `:108` | GenAI capture counts as off only for a whole-RHS literal `false` / `NO_CONTENT` | `013dc89`: 13 planted evasions had stayed green | the `DECOYS` matrix (~300 lines) | `::test_a_planted_violation_is_caught_in_every_syntax` | **yes for the parser** (P0-1, P0-2 red); **no for the set** — P0-3 (equality → prefix) survives, FULL 243 | 3 | 1 | F1 | **PARTIAL** (P3-6) |
| IR5-28 | SDD ledger | `progress.md:3949-3958` (CP 11b) | the "fabricated citation" verdict on `234603b` | it is FALSE, re-verified this round | `417df303` `telemetry.py:38-41`; `54a01f39` is not an ancestor of it | none | n/a | 3 | 1 | F3 | **OPEN, owner-facing** (P3-7) — corrected only by an appended line at `:8139` |
| IR5-29 | iac | all 22 SHAs | each commit is green at its own HEAD: the suite plus the three validators | the guard lane runs all four | 275 → 302 across the range, every count matching its message; all validators exit 0; rootdir = each clone; every clone clean after its lane | the guard lane | n/a (measured) | 1 | 1 | F2 | **SETTLED** (measured) |
| IR5-30 | copilot-mro | `_emitted_series.py:181,183` | r4 IR4-20, carried forward | the phantom recorder name survives in copilot-mro-obsm | nothing in this range touches it | none | n/a | 3 | 1 | F3 | **OPEN, unowned** (unchanged from r4) |

**Totals: 30 claims. 17 SETTLED · 5 PARTIAL · 5 REFUTED · 3 OPEN.** 13 are tier 0 and 17 tier 1; **none is tier 2** —
nothing in either range changes a name, unit or attribute of the signal contract, content capture, RBAC or tenancy.

## Open and refuted claims, for the plan's Future Improvements

Per the controller's ruling all of these are **Future Improvements**, not another round. In descending order of what they
would cost to close:

1. **IR5-14 (P2-2)** — the CI gate reads neither `if`, nor `continue-on-error`, nor `with.ref`. **Flagged to the owner as
   the one worth a ~30-minute test-only fix**, because it defeats the gate `4e2a936` exists to install: assert no
   `if`/`continue-on-error` on the guard job, its steps, or any terraform job, and no `ref:` on the lane's checkout.
2. **IR5-15 (P2-3)** — detect `terraform` at a command position in the whole `run`, not as a prefix of its first line.
3. **IR5-02 (P2-1)** — drop the `[ \t]+` requirement before a bare label and widen the class to HCL's unicode
   identifiers; add `resource "t"n {` and a unicode bare label to `TRAPS`.
4. **IR5-06 (P2-4)** — re-lex the body of a `bash -c` / `sh -c` / `eval` / `su -c` argument, or fail on any word that
   merely CONTAINS `.env` outside the heredoc line and the `chmod`.
5. **IR5-04 (P2-5)** — treat a non-literal `cidr_blocks` as unreadable and fail closed, as `_hcl_blocks` already does for
   `merge(...)`.
6. **IR5-17 (P3-1)** — derive the alarm set from every `terraform_files(root)` file, or guard that no `.tf` outside
   `ALERT_SURFACE` declares an alarm.
7. **IR5-21 (P3-2)** and **IR5-26 (P3-4)** — both close with the published cross-repo instrument/emitter inventory
   already designed under DEFERRED; so does r4's IR4-21 and the unowned IR5-30.
8. **IR5-22 (P3-3)**, **IR5-27 (P3-6)** — one assertion and one decoy respectively.

**Owner-facing, no code:** IR5-28 (the SDD ledger still carries the false "fabricated citation" verdict) and IR5-30 (r4's
IR4-20, still unowned).

## Closed by controller ruling, not by evidence

**I-X-C6** (`{__name__=~"claude.?code.*"}` — no `_`, so `_is_series_shaped` drops it) and **I-X-L8i**
(`importlib.import_module("loguru")`) were re-run at HEAD and survive, as they did at r4. Both are **closed as
contrived**: each needs a spelling no human writes to defeat a guard that already catches every spelling one does.
