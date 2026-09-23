# Claims packet: iac pre-push FULL-DIFF review (queue step 16b)

**FINAL.** Pre-push colleague-scope review (Fable), 2026-09-22, read-only on the real tree throughout. No
terraform commands of any kind, no AWS calls, no network beyond `git ls-remote origin`. No subagents. Re-execution
ran on scratch clones under `~/.claude/scratch/obs-merge/prepush-iac/` (`clone-427fbbd/`, `clone-d1ebeb1/`,
`NOTES.md`, `mutants.tsv`, `m/*.old|new`, `lane-head-*.log`, `vocab-at-607cee0.log`). Both clones verified
restored clean after every mutant; the real tree is unmoved at `427fbbd`, tracked-clean.

## Anchor and range (verified)

| item | value | how verified |
|---|---|---|
| repo | `/home/aditya/Code/iac`, branch `obs-merge` | `git branch --show-current` |
| HEAD | `427fbbd59e1fe91df1f485108b3c379966eb41b3` | `git rev-parse HEAD`; tracked-clean (untracked = the known `__pycache__/` dirs + pre-existing `poc_ec2_setup_ubuntu.sh` only) |
| origin/main | `f35ec202bf6de6f60598a9a68a276c1205fcf539` | `git ls-remote origin refs/heads/main` — unmoved |
| merge-base | `f35ec202` (= origin/main itself; a clean fast-forward range) | `git merge-base origin/main HEAD` |
| range | `f35ec202..427fbbd` — **42 commits**, 2026-09-20 → 2026-09-22 (colleague era confirmed: first commit `35c7e87` E.0g, 2026-09-20 06:19) | `git log --format='%h %ad'` |
| range shape | 33 files, +7213/−174: 3 workflow files, `alarms.tf`, 8 dashboards, `validate_alarms.py` (+110), `validate_metric_vocabulary.py` (new, 1675), `_env_syntax.py`/`_hcl_blocks.py`, 9 test files, README, `poc_ec2_setup.sh`, `b1b_metric_filter_probe.sh`, `apprunner.tf`/`lambda.tf`/`dev.tfvars` | `git diff --stat` |

## Index coverage map (indexes reconciled, never used as evidence)

- `claims-iac-r5.md` (FINAL, 84 mutation runs): `74346bb..d1ebeb1` + extras `9fda3db`, `234603b`, `5e476e0`, `013dc89`.
- `claims-iac-r4.md`: `d52e8b8..74346bb`. `claims-iac-r3.md`: `013dc89..d52e8b8`.
- `claims-satellites-rounds.md` IP/IR/IS/IB/IC: the pre-`2d493c8` fix pass, `9fda3db`, `5e476e0`, R0a/R0b iac halves (`607cee0`/`48fc50c`/`f85284e`), `89f3592`.
- `claims-phase6-iac-fixpass.md`: `2d493c8`. `claims-E-deployment-and-iac.md`: `35c7e87`, `3068b47` (rows I1–I6).
- **Uncovered by any claims file: `427fbbd` (ledger Addendum 262 only) — given first-review rigour here.**

## Reproduced at HEAD (recomputed, not quoted)

| proof | result | log |
|---|---|---|
| full pytest lane, scratch clone at `427fbbd`: `pytest-slot.sh -- api/.venv/bin/python -m pytest -q -p no:cacheprovider -n 2` | **303 passed**, exit 0 | `lane-head-pytest.log` |
| `bash scripts/validate_dashboards.sh` / `python scripts/validate_alarms.py` / `python scripts/validate_metric_vocabulary.py` | exit 0 / 0 / 0 | `lane-head-validators.log` |

## Mutation re-execution (11 runs via `mutant.sh`, every pytest under `pytest-slot.sh`; `mutants.tsv`)

| run | edit | where | expected | got |
|---|---|---|---|---|
| M1 | `if: ${{ always() }}` on `terraform_apply` (Add. 262 battery sample) | clone-427fbbd | KILLED | **KILLED** rc=1 |
| M2 | `continue-on-error: true` on the `guards` job | clone-427fbbd | KILLED | **KILLED** rc=1 |
| M3 | `ref: main` on the lane's checkout `with` | clone-427fbbd | KILLED | **KILLED** rc=1 |
| M4 | `if:` on the guard-lane CALL job (`terraform-plan.yaml`) | clone-427fbbd | KILLED | **KILLED** rc=1 |
| M5 | NEW: an added step `run: git checkout -f origin/main` after the lane's checkout in `guards.yaml` | clone-427fbbd | — | **SURVIVED** aimed (4 passed) |
| M5-FULL | same mutant, FULL lane `-n 2` + all three validators | clone-427fbbd | — | **SURVIVED**: 303 passed + 3× exit 0 |
| M6 | `MINIMUM_DURABLE_MENTIONS = 6` → `9` (IB-03 bracket, upper) | clone-427fbbd | KILLED | **KILLED** rc=1 |
| M7 | `= 6` → `= 8` (IB-03 bracket, lower) | clone-427fbbd | SURVIVED | **SURVIVED** aimed |
| M7-FULL | same, FULL lane | clone-427fbbd | SURVIVED | **SURVIVED**: 303 passed |
| RB-M1 | M1's edit at parent `d1ebeb1` (red-before sample) | clone-d1ebeb1 | SURVIVED | **SURVIVED** (3 passed) |
| RB-M3 | M3's edit at parent `d1ebeb1` | clone-d1ebeb1 | SURVIVED | **SURVIVED** (3 passed) |

M6+M7 re-pin the durable-mention count at **exactly 8** at HEAD, replicating r5's IB03-f9/f8 bracket after
`427fbbd` — the fresh commit adds no durable attribute-key mention, as expected.

## Claims rows

Severity per the estate scale: 0 = a content leak that ships · 1 = guard/lock integrity broken · 2 = a coverage
gap · 3 = docs or process. The push gate is P0/P1.

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PP-01 | repo/remote | HEAD `427fbbd` on `obs-merge`, tracked-clean; origin/main `f35ec20` unmoved; range = fast-forward `f35ec202..427fbbd`, 42 commits, colleague-era | `git rev-parse` / `status --porcelain` / `ls-remote` / `merge-base` / `log`, all recomputed | **VERIFIED** |
| PP-02 | whole tree | the branch tip is green: suite + all three validators | full lane in scratch clone: 303 passed exit 0; validators 0/0/0 | **VERIFIED** (matches the recorded 303, recomputed) |
| PP-03 | `tests/unit/ci/test_workflows_gate_on_the_guards.py` (`427fbbd`, +37) | the commit's claims: key allowlists on the lane's workflow/job/steps/checkout-`with`, call job = `{uses}` only, no `if`/`continue-on-error` on terraform jobs; 9 mutants red-before at `d1ebeb1`, killed now; lane 303 | full diff read line by line; battery sampled 4/9 killed at HEAD (M1–M4) + 2/9 survived at parent (RB-M1, RB-M3); lane recomputed 303 | **TRUE as written** — every stated property holds; the message claims key-pinning, not step-content pinning, so PP-04 is a residual, not a false claim |
| PP-04 | `test_workflows_gate_on_the_guards.py:59-60`, `:72-74` | **NEW FINDING (P2, latent):** the lane's STEP CONTENT is unpinned — `LANE <= runs` is a superset check and `{name, run}` is an allowed step shape, so an ADDED step `run: git checkout -f origin/main` after the lane's checkout re-points the validated tree exactly as `ref: main` (M3, killed) did, and nothing objects. G7's twin through a run step | M5 SURVIVED the aimed file (4 passed) and the FULL lane + all three validators (M5-FULL: 303 passed, 0/0/0) | **REFUTED coverage** — the gate does not yet hold the lane's steps to a closed set. Fix (~15 min, test-only): pin the lane job's step list by equality (ordered `(name, uses, run)` tuples), or refuse any `run` step whose text is outside `LANE ∪ {the pip install line}`. Latent: no such step exists in tracked YAML |
| PP-05 | same, `:61`, `:75` | contrived variant, noted not run: GitHub matches `uses:` owner/repo case-insensitively, the test's `startswith("actions/checkout@")` is case-sensitive — a SECOND checkout spelled `Actions/checkout@v3` with `ref: main` slips both the `with`-pin and the checkout census | code read only; same family as PP-04 and closed by the same step-list equality fix | **P3** (a spelling no human writes; the honest spelling is caught — M3) |
| PP-06 | `test_workflows_gate_on_the_guards.py:91` | **r5 P2-3 weighed, as the brief orders:** a terraform step disguised by an env-var/`cd`/`sudo`/`bash -c` prefix (or on line 2 of a `run: \|` block) is not classified as a terraform job, so it is neither `needs`-checked nor `if`-checked | site re-read at HEAD (`.lstrip().startswith("terraform ")` unchanged); r5's G11b evidence reconciled | **STAYS P2, not P1.** The gate's integrity for every job that exists is mutation-proved (M1/M4 + Add. 262 battery); the escape needs a FUTURE workflow edit adding a new, differently-spelled terraform job — visible in that PR's diff — and wholesale disguise of the existing jobs trips the non-vacuity assert. It does not defeat protection that exists; it fails to auto-extend to a job not yet written. Worth the r5-recorded fix (command-position search) in the same test-only pass as PP-04 |
| PP-07 | `test_attribute_key_prose_pinned.py:76` | IB-03's floor still bites at HEAD and the count is still exactly 8 | M6 (floor 9) KILLED; M7 (floor 8) SURVIVED aimed + FULL 303 | **VERIFIED** (r5 bracket replicated post-`427fbbd`) |
| PP-08 | `apprunner.tf:38-48,78-84`; `lambda.tf:55-62,108-127`; `poc_ec2_setup.sh:183-203`; `dev.tfvars:123-130` | the shipping env edits are exactly the recorded chunks: `WEAVIATE_GRPC_PORT=50051` beside both URLs (C1.5), `LOGURU_DIAGNOSE=NO` on all three compute seats + the POC `.env` line (G.117), the two-alert gate comment | full range diff of all four files read | **VERIFIED** — matches r3's reviewed commits, nothing beyond them |
| PP-09 | `alarms.tf` (832 lines at HEAD) | the alarm surface is internally consistent: both API alarms take counts through `histogram_count()` INNERMOST with the bet + failure-mode + no-substitute record beside them; the four browser alarms carry the KNOWN-NOT-TO-MATCH B1b disclosure in-file (`:489-495`) and say WIRED, never LIVE; both worker alerts reach resources only through `var.automation_worker_deployed` (`:592-593`); delivery alarms cross-route (`:597-600`, `:798`) | file read end to end at HEAD; resource blocks `:605-832` checked against the descriptions and the r5 rows | **VERIFIED** — the recorded facts (dead-by-construction browser alarms pending the stored-shape probe; Add. 256) are stated in the file itself; **no commit in the range worsens them** |
| PP-10 | `scripts/b1b_metric_filter_probe.sh` | "NON-MUTATING, `logs:TestMetricFilter` only" | every `aws` invocation grepped: one executed call, `aws logs test-metric-filter`; the read-only `filter-log-events` appears only as owner instructions in comments | **TRUE** (not executed here — AWS fence) |
| PP-11 | `607cee0` → `f85284e` | `607cee0`'s message discloses an intra-range red: its check 7 fails until `f85284e` lands the production half ("the intended coupling") | recomputed: `validate_metric_vocabulary.py` at `607cee0` exits 1 with 16 failures (`vocab-at-607cee0.log`); at `f85284e` exits 0 | **VERIFIED, P3 observation** — a disclosed two-commit landing before the guard lane existed in CI; the tip is what CI gates |
| PP-12 | `dashboards/*.tftpl`, `README.md` | the dashboard churn is the recorded state-note/dialect work (M-LEGACY-PANELS text panel, Bedrock SEARCH-by-ModelId, `event_name`→`event.name` in Logs Insights selectors, worker-panel caveats, log→text panel conversions); README documents exactly the contracts the validators enforce | every changed line of `dashboards/` and `README.md` in the range read (markdown truncated to selector-bearing prefixes where >300 chars) | **VERIFIED** — reconciles with r3/r5 and claims-E rows I1–I6; no selector contradicts the vocabulary validator, which exits 0 |
| PP-13 | `tests/`, `scripts/validate_*.py` | CI's guard lane is purely static: no terraform, no AWS, no network from tests or validators | grep over `subprocess|socket|urllib|requests|boto3|Popen`: git-only subprocess (ls-files + tmp-path fixtures), `urlopen` monkeypatched in the forwarder test | **VERIFIED** |
| PP-14 | `.github/workflows/terraform-apply.yaml` "Validate approval code securely" step | **OUT-OF-RANGE observation (pre-existing on origin/main `f35ec20`; the range adds only the `guards` job + `needs`):** the step echoes `::add-mask::${{ github.event.inputs.approval_code }}` AFTER `::stop-commands::hide`, and while commands are stopped the runner treats those lines as plain log text — so the mask never registers AND the raw approval code (a workflow_dispatch INPUT, which unlike a secret is not auto-redacted) is printed into the step log. On a successful apply the typed code equals `APPROVED_SECRET`, so the log of every legitimate apply effectively discloses the apply-approval secret to anyone with Actions log read access | YAML read; command-ordering semantics per GitHub's stop-commands contract; NOT a range defect and NOT counted in the verdict | **OWNER-FACING** — flagged for the owner's live batch; the fix is to register the masks BEFORE `::stop-commands::`, or drop the inert lines and compare hashes without echoing |

## Verdict

**PASS — P0 0 / P1 0 / P2 1 new (PP-04) + 1 carried OPEN by scope ruling (r5 P2-3, weighed at PP-06: stays P2) /
P3 2 (PP-05, PP-11), plus one out-of-range owner-facing observation (PP-14).**

Nothing in `f35ec202..427fbbd` ships a P0 or P1: the branch tip is green (303 + 3×0, recomputed), every
production edit matches its recorded review, the fresh `427fbbd` gate does exactly what its message claims
(sampled battery re-killed at HEAD, red-before re-proved at the parent), and the known recorded facts (the four
dead-pending-B1b browser alarms, the stale local provider lock owed to C3) are disclosed in-tree and worsened by
nothing. PP-04 and PP-06 belong in the same ~30-minute test-only follow-up the r5 controller already flagged
(IR5-14's lineage): pin the lane's step list by equality and detect `terraform` at command position. **The push
gate is clear.**
