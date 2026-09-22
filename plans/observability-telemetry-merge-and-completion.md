# Observability / telemetry — merge `obs-telemetry-merge` and close the rebuild

**Opened 2026-09-19.** Owner request: assess the colleague's `obs-telemetry-merge` work, merge it, find the
gaps, then finish the gaps plus what is still owed from the observability rebuild plan itself.

Governing documents (do not duplicate them here):
- `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` — the ruled design (rev 4), §11 = the 20 owner rulings.
- `docs/plans/observability-rebuild.md` — master plan + dated ledger (§15) + resume brief (§18).
- `docs/plans/observability-rebuild-phase-{0-2,1,4,5,6,8,9,10}*.md` — per-phase detail, notes, Future Improvements.
- `docs/plans/observability-rebuild-research/09-outcome-and-span-attribute-reconciliation.md` — written by F.4
  at this fold: the two outcome vocabularies reconciled, and the span attribute keys no document names.
- Their plans, merged into this repo by F.1: `plans/observability-merge-completion.md`,
  `plans/observability-rebuild-phase-11-audit-followups.md` — it arrived claiming phase number 8, which collides
  with our satellite-services phase, and **F.2 renumbered it to 11** —
  `plans/observability-rebuild-phase-1c-stable-nonagent.md`, and
  `plans/observability-rebuild-research/08-post-migration-rescoping.md`, which **F.3 folded in as Task R's
  starting baseline** with its central Gate M finding corrected in place.

---

## 1. Situation

`origin/obs-telemetry-merge` exists in **six** repos, not five: `core`, `utils`, `dashboard`, `copilot-mro`,
`api` **and `docs`**. Author: ishaan.jain, driven through a Codex / GPT-5.6 harness, 2026-09-08 → 2026-09-19.

Every branch was cut from a base dated 2026-09-05 … 2026-09-10 — **before** our phases 8, 9 and 10 landed.
Our mainlines are 13 – 241 commits ahead of those bases.

| repo | our branch | our tip | their tip | merge-base | their commits | textual conflicts |
|---|---|---|---|---|---|---|
| core | `master` | `e10a9ce` | `8b7dfad` | `988571b` | 5 | 0 |
| utils | `langgraph-merge` | `289ba71` | `cfcf0fd` | `9f74a11` | 3 | 0 |
| dashboard | `agent_sdk` | `4a2898b` | `0f1715a` | `b87ced0` | 6 | 0 |
| api | `langgraph-merge` | `44bd8d1` | `6f22498` | `a19a931` | 3 | 0 |
| copilot-mro | `langgraph-merge` | `417df303` | `c2fc8bb1` | `07c2d4ee` | 46 | 20 files |
| docs | `main` | `9cbacec` | `5a31df4` | — | 13 | 1 file |

**The merge is easy and the review is hard.** Five of six repos auto-merge with zero conflicts, which is the
trap: the damage is semantic, in files git merges silently. Three instances are already proven — see §4.

### What they built (scope, not quality)

- **copilot-mro (83 app files, +9.5k, plus ~16k lines of tests)** — `RuntimeTelemetry` spans/metrics wired for
  both runtimes (plan 3.1 / 3.2), `llm_turn_content` store + capture runtime + read API + purge/inspect scripts
  (3.5), an OTLP content copy projected into Phoenix (3.6 / 7.2), non-agent lifecycle spans across main,
  document hub, data discovery, improvement, memory and the seven parsers (1b.7 / 1b.8), a large
  user-content log sweep, Phoenix offline evaluations, and a Weaviate partition warn mode.
- **copilot-mro deployment** — a New Relic collector profile, four production durability fragments, an
  acceptance harness, optional Phoenix compose, and a large Grafana/catalogue realignment.
- **core** — product-event idempotency (`event_id` + `schema_version` + `ON CONFLICT … DO NOTHING`), the
  `tenants.llm_content_capture_enabled` column, and a server-owned per-tenant `dashboard_profiles` relation
  with a resolver and endpoint.
- **dashboard** — stable product-event identity, a server-driven dashboard-profile page, and an LLM turn
  summaries card.
- **utils** — `s3.download` and `weaviate.hybrid_search` client spans, configurable Weaviate gRPC port.
- **api** — a loguru extra-collision fix on the request-failed line, and a Weaviate partition warn mode.

This is, substantially, **Stream L and Phase 7 — the two blocks our own plan records as never started.** Taking
it is worth far more than rebuilding it.

---

## 2. Merge strategy

### 2.1 Topology

Per-repo integration branch `obs-merge`, cut from our mainline, in a **plain git worktree at sibling depth**
(`/home/aditya/Code/<repo>-obsm`), `.env` symlinked. Merge their branch into it, resolve, fix, run the lane,
adversarially review, then fast-forward the mainline. Never merge into a mainline checkout directly; never use
the isolation tool.

- [ ] 2.1.1 One implementer per working tree. No two agents in one tree, file-disjoint or not.
- [ ] 2.1.2 `env -u VIRTUAL_ENV POETRY_VIRTUALENVS_IN_PROJECT=true` for any worktree poetry work.
- [ ] 2.1.3 The shared `api/.venv` is the only Python env for test lanes.

### 2.2 Repo order (dependencies, not convenience)

**Corrected 2026-09-19 after the plan review.** The first draft ordered api before copilot-mro, which
contradicts api's own hard dependency, and placed a single mis-invoked migration in the wrong position. The
verified dependency graph is a DAG — `core` structurally refuses to import `copilot_mro`, so there is no cycle.

1. **utils** — clean; position is technically free, but it is an editable path dependency of core, api and
   copilot-mro, so the moment it merges every later lane in the shared venv sees it and pre-merge baselines
   stop being comparable. Move it first and re-baseline.
2. **core** — clean; its DDL is what everything else needs.
3. **copilot-mro** (Phase D app half, then Phase E deployment half, same worktree, in sequence) — the only
   hard merge: 20 conflicted files.
4. **THE DB STEP — one run, here, after both core and copilot-mro have merged.**
   `migrate_tenancy_schema.py` with its **default (all-registry)** invocation, then `provision_rls.py`.
   A `--registry core` run is wrong: `llm_turn_content` is a **copilot-mro** registry table, and the script's
   own docstring warns that a subset run leaves the rest unmigrated. Five schema changes (the fifth added 2026-09-22) — plus, BEFORE core deploys and separate from this run, the owner-run `core/scripts/rbac/drop_comments_tenants_fk.sql` (M-CASCADE, decision sheet C1):
   `product_events.schema_version`, `tenants.llm_content_capture_enabled`, `dashboard_profiles`,
   `llm_turn_content`, **`automation_runs.traceparent` (nullable, core `7c506e6`, M-JOB-TRACEPARENT) — it MUST exist before core or the api worker deploys: the worker boot check refuses a missing declared column (`worker.py:243`, which stops ALL automations) and every `enqueue_one_shot_run` fails `UndefinedColumn` (DocHub upload/cleanup, data discovery) while the API serves on; owner item C9.** **Also, BEFORE core deploys: `chat_turn_facts.turn_outcome` + `turn_error_type` (copilot-mro `post_create_sql`, owner item C12) — core `7d5144c` reads `turn_outcome`, and the Quality board's answer-outcomes panel answers the fixed 500 until the column exists. And the named CHECK `llm_turn_content_content_present_check` (cli branch `b181a81e`) is added by this run; the owner's `content_s3_key` drop SQL refuses until it exists (order enforced: code → migration → SQL).** **The RLS run is not optional** — without it the tenant-content table exists with no
   row-level security. Acceptance: `llm_turn_content` present with `ENABLE` **and** `FORCE ROW LEVEL SECURITY`.
5. **api** — hard dependency on copilot-mro: `flynapse_api/main.py` top-level imports
   `partition_boot_check_mode`, `PARTITION_REFUSAL_ERROR` and `PARTITION_REFUSAL_REMEDIATION`, none of which
   exist on our copilot-mro mainline. Gate the phase on `import flynapse_api.main`.
6. **dashboard** — hard dependency on core (its product events now post `event_id` and `schema_version`, and
   core `master` sets `extra="forbid"`, so against an unmerged core every event 422s and is silently dropped);
   soft dependency on copilot-mro (the LLM turn summaries card is mounted unconditionally and calls a
   copilot-mro route that exists only on their branch, so merging dashboard early leaves a red error card on
   the improvement page for everyone).
   **Deploy coupling added 2026-09-22 (M-INVITE-FRAGMENT + M-PERMISSIONS-ENDPOINT, dashboard review r1 P3-3):** the
   dashboard has no GET fallback for the invitation preview (by ruling), core `66b0217` ships the POST route AND the
   `#token=` email composer together, and api `8d7f587` adds the gateway's POST skip-auth. Dashboard first → the old
   gateway 401s the POST and every invitee sees "could not check"; core first → new emails carry `#token=`, which the
   old dashboard does not read ("does not work"). **Deploy api (gateway) → core → dashboard back to back**, or hold
   core's composer change until the dashboard is live. The permissions endpoint (api `35639cb`) must also be live
   before the dashboard that reads it; `/test-cookie` stays one release so the reverse order is safe.
7. **docs** — free position; records the outcome and resolves the phase-numbering collision.

### 2.2a The silent-merge register — the artefact this plan turns on

§2.1 says the damage is semantic, in files git merges without asking. The first draft then organised itself
around the twenty files that *did* conflict. Every P0 the plan review found lives in a file that merged
**silently**. So before any repo is merged, build one table and treat it as the merge's spine:

> file · did either side change it · did git conflict · **what decision does their change embody** · which
> side is the base of record · **which guard pins the outcome**

Built from `git merge-tree --write-tree --name-only` per repo plus a diff of each side against the merge-base.
Every ruling in §4 then attaches to a *file*, not to a paragraph. Known members so far, all silent, all
decision-bearing:

| file | what their silent change decides |
|---|---|
| `deployment/observability-local/grafana/provisioning/datasources/datasources.yml` | **Deletes** the `flynapse-postgres` datasource that M-GRAFANA exists to keep |
| `.../dashboards/flynapse/llm-agents.json` | Deletes the two exact-spend panels; rewrites five token queries |
| `.../dashboards/flynapse/platform-health.json`, `.../agent-turn-explorer.json` | Panel deletions and status wording |
| `.../rules/prometheus/flynapse-agent-alerts.yml` | Alert description vocabulary |
| `deployment/otel/VERSIONS.md` | The M-PINS policy softening |
| `docs/runbooks/observability/oss-profile.md` | Likely deletes the exact-spend runbook section |
| `copilot_mro/app/services/agent_claude/orchestrator.py` | **Un-wires** the tool-I/O archive M-TOOLIO exists to keep — a default flip in `config.py` cannot restore a feature with no call site |
| `copilot_mro/app/main.py` | Deletes the `/metrics` route (a *good* silent change) |

And the guard cannot save us on the first row: our dashboard test allows `flynapse-postgres` as a datasource
uid; theirs asserts it is **absent**. That file *is* conflicted, so whichever side wins, the lane is green.
Two mutually contradictory guards, both passing. Pin the outcome with a guard that asserts the **positive**.

**The docs repo's own rows, audited by F, 2026-09-20.** Six files, and only the first conflicted — the other
five arrived theirs-only, which is the silent case in a repo where no test can fail.

| file | what it decides, and the ruling |
|---|---|
| `plans/observability-rebuild.md` | Both sides changed it; **5 conflicting hunks**; **base of record is OURS.** Their side was written from a base cut before phases 8, 9 and 10 landed, so "take theirs" would have deleted three phases and the Gate M declaration itself. |
| `plans/observability-rebuild-phase-11-audit-followups.md` | Theirs-only. Claims phase number **8**, colliding with our satellite-services phase. **Renamed to 11** (F.2). |
| `plans/observability-rebuild-phase-1c-stable-nonagent.md` | Theirs-only. Declares a span/attribute contract **no guard enforces**, and names primary-consumer boards that do not consume it. **Corrected in place.** |
| `plans/observability-rebuild-research/08-post-migration-rescoping.md` | Theirs-only. Rules **Gate M closed** and defers the sole `chat_turn_facts` writer on that basis. **Corrected in place** (F.3). |
| `plans/observability-merge-completion.md` | Theirs-only. Records deleting the Grafana postgres datasource — **contradicts M-GRAFANA** — and an acceptance harness — **contradicts M-ACCEPT**. Kept as the record of what their branch did; **status banner added naming both**. |
| `plans/observability-rebuild-phase-1-utils-api.md` | Theirs-only, a historical note. Audited, accurate, **taken unchanged**. |

### 2.3 Resolution doctrine

- The merge commit carries **conflict resolution only**. Every fix lands as its own commit immediately after,
  so the review can read them apart.
- Exception: where the merged tree is *broken* (§4.1, §4.5), the repair commit lands before any lane runs.
- **Base of record for the R22-swept sites is ours** (`failure_fields` = type + frames). Their
  `error_type=type(exc).__name__` is strictly weaker and must not replace it anywhere.
- **Base of record for user-content removal is theirs.** They fixed leaks we still carry.
- Read *their branch*, never the shared base, when deciding who owns a hunk.
- After resolving any file where both sides touched an object literal, grep for duplicate keys. The RC gate's
  TS1117 hazard did not recur here (they added no mutations) — run the check anyway.
- `poetry.lock` is never hand-merged. Resolve `pyproject.toml`, then relock.

### 2.3a Review tiering — what Fable sees, and what it never sees

Fable never gates (M-REVIEW). It audits later, over packets Opus has already built. So the only question is
what is worth its tokens. The test is: **would a wrong call here be caught by a failing test, or only by
someone noticing months later?** Only the second kind goes to Fable.

**Amended 2026-09-19 after RV4.** The original tier-0 rule keyed off "did git report a conflict" and assumed a
guard test is trustworthy by existing. Both halves were wrong. Every P0 the plan review found lives in a file
git merged *without* a conflict, and RV4 catalogued **35 inert tests** on their branch — guards pinned to dead
SHAs, guards disarmed by a branch-name check, guards whose verdict is a property of whichever tree sits beside
them, five "disabled OTel is transparent" tests that all pass with the telemetry deleted, and three tests that
now *assert the defect* so restoring correct behaviour reads as breaking a test.

Two rules follow:
- **A change no conflict surfaced is not thereby tier 0.** Tier is decided by the decision the change embodies.
- **A guard earns tier 0 only once it has been shown to fail when the property is removed.** Until then it is
  evidence of intent, not of behaviour. Mutation-check it, or treat the change as tier 1.

| Tier | What | Goes to Fable? |
|---|---|---|
| 0 | Anything a **mutation-checked** guard test proves: mechanical resolutions, additive files, renames, test-only and doc changes | **Never** — but only after the guard has been shown to fail when the property is removed. An unverified guard buys nothing. |
| 1 | Consequential but reversible: merge resolutions where both sides touched the same concept, and the defect fixes | **Clubbed into one chunk**, all six repos together — the question is identical each time ("did a decision get silently lost?"), so the standing context is paid once. |
| 2 | Irreversible or estate-shaping: the signal contract (names, units, attributes — changing them later breaks every board and every historical series), content capture under the opt-out flip, the read API's RBAC, anything touching tenancy or RLS | **Its own chunk.** These are judgment calls no test can settle, and the cost of being wrong is not a bug, it is a migration. |

**Three Fable chunks, not twelve.** F1 contract and privacy (tier 2, one chunk — they share the same standing
context: spec §6.2/§6.3/§6.5 and rulings 4 and 20, so clubbing them is where the saving is). F2 the merge
itself (tier 1, all repos). F3 the plan's residual — findings Opus marked ACCEPT-WITH-FIX where the fix was
judgment rather than mechanics, plus the deferred register.

**The structural move: each Opus review's output IS the Fable packet.** Every review emits a claims table —
file:line → decision taken → evidence → the guard test that protects it. Fable adjudicates claims and
spot-checks only what it disbelieves, instead of re-reading the code. That inversion, not chunk arithmetic, is
where the 3–5× reduction comes from.

#### The claims table is a phase-exit gate, not an intention

Written as an intention it would be built after the fact, which is where packets go to die. So it is a gate:
**a phase does not close until its claims table exists.**

- **The reviewer emits it, not the implementer.** The implementer carries exactly the confirmation bias the
  adversarial review exists to defeat; a table written by the agent that took the decisions records intent,
  not evidence.
- **The controller verifies it before the phase closes.** Every `file:line` must resolve in the tree as it
  stands, and every named guard test must exist. An unverified table is a longer way of saying "trust me".

Row format: **Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Tier |
Chunk | Claim state.** The last column is the one that decides how much attention a row is owed:

| claim state | meaning |
|---|---|
| `SETTLED` | a guard exists **and** has been shown to fail when the property is removed |
| `ASSERTED` | a guard exists; no mutation proof is recorded |
| `OPEN` | no guard — the claim rests on judgment |

**Tier 0 requires SETTLED**, by the same rule the tier table states: a guard that has not been mutation-checked
is evidence of intent, not of behaviour, so `ASSERTED` cannot buy a row out of review.

Two prohibitions, both bought by the 35 inert tests:

- **Never name a guard without verifying it resolves.** A guard named by a source document and not found in the
  tree is recorded as `CLAIMED BUT NOT FOUND` — that is a finding, not a blank cell.
- **Never record a mutation proof without the specific mutation and the test that failed.** "Mutation-checked"
  with nothing named is an assertion about an assertion.

**Measured, 2026-09-20.** The backfill over phases 0 – E produced **186 claims — 41 SETTLED, 60 ASSERTED,
85 OPEN — and zero tier 0, in all four files independently.** Tier 0 came out empty for a structural reason
worth keeping: work mechanical enough to qualify is work nobody records a decision about, so it never becomes a
claim at all; anything that *is* a claim embodies a decision, which lands it at tier 1 or 2. So the saving does
not come from tier 0 excluding the bulk of the corpus — it comes from a SETTLED claim being adjudicable from
one row. The packet is `plans/obs-telemetry-merge-review-packet/`.

### 2.4 Per-repo verification lanes

- **core / copilot-mro / utils / api** — from the shared `api` Poetry env, `DEBUG=false`, and
  `POSTGRES_DB=copilot_mro_test` for DB lanes. Always include `tests/unit/infra` (two-level layout,
  globally-unique basenames, no depth-coupled paths) — their new tests violate the last of these in nine files.
- **copilot-mro full suite — ONE PYTEST PROCESS PER TEST DIRECTORY, never one process for `tests/`.**
  Measured 2026-09-20: a single-process `pytest ../copilot-mro/tests` reports **116 failed + 15 errors = 131
  failing ids**; the same tree run one directory at a time reports **37**. `tests/unit` alone fails 11, against
  ~95 unit failures inside the full run. So roughly **94 of the 131 are cross-directory test pollution**, not
  defect — a gate built on the full-suite number would have been measuring import order. The pre-merge
  baseline of record is the per-directory table in the SDD ledger, and the post-merge gate is the **set
  difference of failing ids**, not a count. (The pollution itself is a real finding and is Task R / G.2 work:
  the repo's dynamic-loader convention exists precisely to stop package imports poisoning `sys.modules`, and
  something is importing packages directly.)
- **dashboard** — `npm run typecheck` **before** the unit lane; `npm run test:unit` with the canonical
  `--tsconfig tsconfig.test.json` flags; lint **only** via `next lint`. Never `next build` in a worktree.
- **copilot-mro otel** — the non-container lane `tests/integration/otel`. **Measured baseline, run 2026-09-19
  on `langgraph-merge` `417df303` from the shared `api` env: 135 collected, 111 passed, 24 skipped.** The
  "87 passed / 0 skipped" figure the first draft used was the 2026-09-14 *gated container* run — a different
  lane — and the predicted post-merge range bracketed the real pre-merge number, so the gate could not fail.
  Correct gate: **collected must not decrease, passed must not decrease, and every new skip must be named.**
  Seven otel test modules exist only on our side, so a post-merge collected count below 135 is itself the
  finding.

---

## 3. Phases

Each phase ends with an **independent adversarial subagent review** (fresh agent, briefed with the phase scope,
the acceptance criteria and the actual diff, prompted to break it), then triage → fix now or record in §6.

### Phase 0 — Review the colleague's work, standalone, before any merge

**Nothing merges until this closes.** Their branch is reviewed as its own body of work, against their own stated
acceptance criteria, our spec and our rulings — not against our tree. A merge-lens review answers "does this
collide"; this one answers "is this correct". Merging first would also mean any defect is discovered inside our
history instead of in theirs.

Input: the four merge-lens assessments of 2026-09-19 already banked ~40 findings with file:line. Reviewers are
handed those as a claims table to adjudicate, so they spend their budget breaking the code rather than
rediscovering it. Anything a reviewer cannot reproduce is downgraded, not inherited.

Output per lane: a verdict per feature — **ACCEPT / ACCEPT-WITH-FIX / REJECT** — and findings ranked P0/P1/P2,
each with file:line and a concrete failure scenario. The merge phases then execute those verdicts; a REJECT
means the feature does not come across, not that we fix it for them.

- [ ] 0.1 **RV1 — content capture, the store, the read API, the purge/inspect scripts.** Highest risk: it
      handles user prompts and model answers by design. Does redaction actually hold against adversarial
      inputs? Are the bounds real? What happens on partial failure, on a tenant boundary, under RLS?
- [ ] 0.2 **RV2 — the telemetry emitters, span suppression, and semconv/catalogue correctness.** Every board
      reads these names. Already known: `gen_ai.client.token.usage` is a Counter where semconv says Histogram.
- [ ] 0.3 **RV3 — the Phoenix evaluation suite and the content projection.** ~2,100 lines plus ~2,500 lines of
      tests that nothing of ours touches, so the first pass barely looked at it — and it becomes our eval
      workbench.
- [ ] 0.4 **RV4 — non-agent lifecycle spans, the log sweep, and test-suite integrity across their whole
      branch.** Do their ~16k lines of tests actually test? Two inert-guard classes are already known: their
      privacy guard fails on our code, and their scope guard is pinned to SHAs and a branch name.
- [ ] 0.5 **RV5 — core, dashboard, utils, api and deployment: adjudicate the first-pass findings** and hunt
      what a collision-hunting lens would have missed.
- [ ] 0.6 **RV6 — adversarial review of THIS PLAN.** A fresh agent that has not built any of it, briefed with
      the spec, the master plan, the rulings in §4 and this document, prompted to break the plan rather than the
      code: wrong sequencing, a dependency that will bite, a ruling that contradicts another, a phase whose
      acceptance cannot actually be verified, work that is already done and listed as pending, work that is
      needed and missing, and sizing that is wrong. The estate's own precedent — phase 9 and phase 10 both had
      an independent plan review before execution — and this plan has already carried two instances of
      "reported as pending, actually done" (see §8).
- [ ] 0.7 Triage every finding into: fix before merge, fix during merge, record as a Future Improvement, or
      reject the feature. Record the verdicts in §7 and the register in §5.

### Execution order — the letters are labels, this list is the order

The phase letters below were assigned before the dependency graph was verified and no longer read in sequence.
**Execute in this order** (§2.2 has the reasoning):

> **0** (review) → **A** (prep) → **C1** utils → **B1** core → **D** copilot-mro app → **E** copilot-mro
> deployment → **DB STEP** (all-registry migration + RLS) → **C2** api → **B2** dashboard → **F** docs → **G**

The two changes from the first draft: api moves **after** copilot-mro (it imports three symbols that exist
only there, so the phase cannot close otherwise), and dashboard moves **after** copilot-mro too (its LLM
summaries card is mounted unconditionally against a copilot-mro route). D and E share one worktree and
therefore never run in parallel.

### Status, 2026-09-20 — A, C1, B1, D, E and F CLOSED; nothing pushed

Execution has passed the DB step. A (prep), C1 (utils), B1 (core), D (copilot-mro application half), E
(copilot-mro deployment half, plus a new `obs-merge` branch in **iac**) and F (docs) are merged in their own
`<repo>-obsm` worktrees on branch `obs-merge` — copilot-mro's tip is `ea0ac559` — each phase followed by a
fresh adversarial Opus review whose findings were triaged into the same phase. The **DB step is complete**:
the all-registry migration and the RLS run both landed after D, as §2.2 sequences them. **C2 (api) and B2 (dashboard) are both MERGED and CLOSED** — C2 at `api-obsm 9812f44`, B2 at `dashboard-obsm 3afd524`. Phase G is in flight. The former sentence read "C2 and B2
(dashboard) are in flight", superseded 2026-09-20. No mainline has moved and nothing is pushed. `copilot_mro_test` has been migrated
with the merged definitions, so **the pre-merge baselines in the SDD ledger cannot be reproduced.** Per-phase
outcomes are in §7; deferred items with their reasons are in §6.

### Phase A — Preparation
- [x] A.1 Commit the six uncommitted observability docs in this repo by named path, including the untracked
      phase-10 plan (the only durable record of 22 tasks and ten Fable gates).
- [x] A.2 Create the six `obs-merge` worktrees and branches. Done at `/home/aditya/Code/<repo>-obsm`,
      `.env` symlinked into api / copilot-mro / dashboard.
- [x] A.3 **Corrected.** The three schema changes are *theirs*, so they cannot exist before the merge and this
      step as written belongs to the DB STEP. Pre-merge, A.3 is `--verify-only` against `copilot_mro_test`:
      prove the migration tool runs clean at the current head, so a post-merge failure is attributable to the
      merge. The three changes are confirmed at the DB STEP, after copilot-mro lands.
- [x] A.4 Record the pre-merge lane numbers for every repo, so a post-merge delta is measurable. Table in the
      SDD ledger. **They are no longer reproducible** — `copilot_mro_test` has since been migrated.

### Phase B — core, then dashboard

**B1 core**
- [x] B1.1 Merge (clean). Repair our `_Sink` test double for the new `ProductEventInsertResult` return type and
      its `{"accepted": 1}` assertion — without this the merged handler dereferences `None` and 500s. Done via
      an `_InsertSink` subclass, so the double that must return a result is distinct from the one that must not.
- [x] B1.2 Add the missing gate on `GET /analytics/dashboard-profile` — **"tenant-admin" is this plan's word, not core's behaviour, and it misled the B2 implementer into a false 403 rationale.** `core/resources/analytics/analytics_endpoints.py:44` `is_tenant_admin` returns `is_tenant_owner OR has_capability("view_dashboard")` — the SAME gate the dashboard page checks before it asks, so the 403 branch is unreachable today. Corrected 2026-09-20; it is the only route on
      that router without one. Confirmed by enumerating the router: two GET routes, one gated.
- [x] B1.3 Log the widen-to-all-panels branch in the profile loader, so "no row" and "corrupt row" stop failing
      in opposite directions silently. `_coerce_panel_ids` now returns `None` for a non-list (corruption, warn,
      fall back to the offer) and `()` for an empty list (a legitimate "offer nothing").
- [x] B1.4 Extract the feature-gate check so the profile resolver and the panel service stop carrying two
      copies of one rule → `registry.feature_enabled`.
- [x] B1.5 Run the migration, then the analytics/db/api/tenancy/infra lanes. **2866 / 2 / 2 vs 2829 / 2 / 2.**
- [x] B1.6 **(added during the phase)** Apply **M-CAPTURE on the core side**: the column is an opt-OUT
      defaulting to `true`, not their opt-IN defaulting to `false`. The plan had assigned M-CAPTURE only to
      D.4 (copilot-mro's policy reader); that alone would have flipped the reader against a column whose every
      row said false.
- [x] B1.7 **(added during the phase)** `schema_version` is stamped by the server, not taken from the client.
      `extra="forbid"` means every stored row matched this model, so a client-supplied value would write a
      claim the server cannot stand behind into a NOT NULL column. `event_id` stays the client's — that one
      exists to make a browser retry idempotent.

**B2 dashboard**
- [x] B2.1 Merge (clean). Guard the UUID mint with the repo's existing idiom and move it inside the never-throw
      region — as merged it violates E9.9b and throws on any non-secure-context origin.
- [x] B2.2 Apply M-FALLBACK: profile failure degrades to the capability path.
- [x] B2.3 LLM turn summaries card: typed error message instead of the server's text, a constant-message
      breadcrumb on failure, the response contract instead of a bare cast, and the query layer instead of
      hand-rolled `useState`/`useEffect`. Mis-described docstring corrected — it returns 180-char prompt and
      answer previews, which is not "content-free".
- [x] B2.4 typecheck → unit → `next lint`, plus the post-merge greps for the optimizer tab, the panel count,
      the E9.9b catch and duplicate object keys.

### Phase C — utils, then api

**C1 utils** (first: the three consumers pass `distribution=`, so utils always leads)
- [x] C1.1 Merge (clean). Replace the four hand-rolled `error_type=` log kwargs with `failure_fields`; keep the
      semconv `error.type` on the spans. **Done, and the conversion is mutation-proven** — the adversarial
      review showed it was initially inert (reverting to the bare kwarg passed the whole lane), because the
      estate's two R22 AST guards sweep fixed module lists that contain neither `s3_service` nor
      `weaviate_service`. Both R22 tests now assert `stack` is present, not just that the message is absent.
- [x] C1.2 Drop the two fabricated exceptions built only so the span helper could read a type name.
- [x] C1.3 Stop marking a quiet cache miss as span ERROR — its only caller treats misses as normal flow, and it
      would inflate the dependency board's error rate. Premise re-verified across all ten repos:
      `ad_parser._download_from_s3` is the only `quiet=True` caller.
- [x] C1.4 Add the missing no-op-tracer test for the Weaviate wrapper (S3 has one).
- [x] C1.5 **Second clause only.** `grpc_secure` now follows the URL scheme via `urlsplit`, with a
      `WEAVIATE_GRPC_SECURE` override for the one topology the heuristic gets wrong (a proxy terminating TLS in
      front of a plaintext gRPC backend). **The first clause — mirroring `WEAVIATE_GRPC_PORT` into every repo
      that deploys it — is NOT done and is owed by later phases**, at these exact sites:
      `copilot-mro/.env.sample`, `copilot-mro/copilot_mro/app/.env.example`, the four copilot-mro compose files
      and `deployment/weaviate-local/weaviate-docker-compose.yml` (Phase D/E), `api/.env.example` (C2), and
      `iac/apprunner.tf:41` / `iac/lambda.tf:108` (repo files, not an apply — same precedent as M-TOKENUSAGE).
      Every current `WEAVIATE_URL` in the estate is `http://`, so nothing is broken today; the gap is that an
      operator has no declared knob.
      **iac sites DONE 2026-09-21 (`iac 0df5c24`, not pushed):** `WEAVIATE_GRPC_PORT = "50051"` (utils' own
      default, so no runtime change) beside `WEAVIATE_URL` in `apprunner.tf` and `lambda.tf`. Guard
      `tests/unit/networking/test_weaviate_ports_declared_and_admitted.py`: every env that points at Weaviate
      names the port, and ec2.tf's Weaviate security group admits BOTH ports from the group each client really
      sits in (derived from `vpc_config` and the App Runner VPC connector, not listed). 258 → 261; 7 mutants
      red, 1 equivalent (connector moved to `lambda_sg`, which is admitted on the same ports).
      **iac review r3 (MERGE-CLEAN, `claims-iac-r3.md`) fixes, 2026-09-22, not pushed:** P2-1 `013c9ae`: the
      server half is derived too — the URL's `aws_instance` host, its attached `vpc_security_group_ids`, each
      ingress rule read whole (ports per `for_each` item, TCP, admitting groups), App Runner `egress_type = "VPC"`
      required; fails closed on anything non-literal; CIDR admission not counted. The reviewer's W1/W2/W3/W4/W9
      went red, and so did the W5/W7/W8 controls. P2-2 `4afc68f`: `_hcl_blocks.attributes()` tests depth at the key token, so
      `"K" = v` / `("K") = v` are read (they had been dropped, a fail-open for this scan); W10 red, L10's false
      failure gone.
      **iac review r4 (`claims-iac-r4.md`, MERGE-CLEAN 0/0/1/8) fixes, 2026-09-22, not pushed:** P2-1 `d76c439`: `_hcl_blocks` reads bare identifier labels on resource, module and child headers, so a bare-labelled Weaviate client no longer hides (B1, L6e, B2 red); P3-A `f5b73f3`: the guard reads each client security group's EGRESS as well (W11 red); P3-C `bac0f33`: `HclFile` scans the text `_env_syntax` scans, BOM dropped and `\u` name escapes decoded (W10u red). **Correction (r4 P3-H):** `013c9ae`'s "nothing on the path is listed" did not cover the client egress half, which `f5b73f3` closes.
- [x] C1.6 Record the connection-factory span as still owed: the spec put the Weaviate wrapper on
      `weaviate_connection()` deliberately, and `hybrid_search` is not the only door. Recorded in
      `_initialize_connection`'s docstring, naming the six untraced query methods; the work is G.10.
- [x] C1.7 **(added by the review)** `record_exception=False` had zero coverage on both spans — flipping it to
      `True` passed all 1203 tests while shipping `exception.message` and a rendered `Type: message` stacktrace
      to Tempo. The privacy helper read only log records. It now reads span attributes and span events too, and
      both failure-path tests assert no `exception` event.
- [x] C1.8 **(added by the review)** `server.address` added to both spans. The collector promotes it as a
      span-metrics dimension and the catalogue's "Client call rate by dependency" and "DB client p95 by system"
      panels both name S3 — without it S3 was excluded from one and in the empty-label bucket of the other.
- [x] C1.9 **(added by the review)** The one `traceback.format_exc()` log call inside the function C1.5 edited
      now uses `failure_fields`. A rendered traceback's last line is `Type: message`, and a Weaviate connect
      failure's message quotes the endpoint.

**C2 api** — **must not merge before copilot-mro**: their `main.py` imports five symbols that exist only on
their copilot-mro branch, so api alone fails at import and the gateway will not boot.
- [x] C2.1 Take their loguru mechanics on the request-failed line — the bug is real: an already-interpolated
      f-string message plus kwargs makes loguru run `str.format`, so a Pydantic error's braces raise `KeyError`
      *inside* the handler and the request's own exception never reaches the `raise`.
- [x] C2.2 Combine it with our R22 policy: bind duration and `failure_fields`, constant message, drop the
      now-unused traceback import. Add the assertion their test lacks — that no exception text reaches a sink.
- [x] C2.3 Apply M-WARN to the partition helper; assign and surface the degraded return value.
- [x] C2.4 Harden the relaxed boot-check guard so a handler that returns before its `raise` is still caught.
- [x] C2.5 M-LOCK: take our lock. Gate the merge on an actual `import flynapse_api.main`.

### Phase D — copilot-mro, application half
- [x] **D.1 DONE.** Resolve the six app-code conflicts. Base of record is **ours** for chat management, user feedback,
      agent pipeline, improvement scheduler and the lang backend; **theirs** for the shared pipeline, with our
      one log call restored; **both** blocks kept in the lifecycle test.
      **"Ours as base" never means "drop theirs."** In `agent_pipeline.py` their entire 59-line delta *is* the
      `RuntimeTelemetry` production wiring, and on our mainline `RuntimeTelemetry` is a class with **no
      production instantiation at all** — every `gen_ai.*` / `agent.*` metric in the estate is dead code today.
      A literal "ours" resolution merges this plan's centrepiece back out, and Phases E, F and G would then
      measure an estate that emits nothing. Graft their telemetry hunks in full at all four sites:
      `get_runtime_telemetry` / `_model_usage_sinks` / `_claude_runtime_provider`, the sink splat into both
      usage factories, `post_tool_observer=` on both backends, and the five `AgentPipeline` kwargs.
      Acceptance: `get_runtime_telemetry` survives in `agent_pipeline.py` and their composition-root test passes.
      Guard the scheduler resolution so `STOP_UNWIND_SECONDS` is not dropped — it exists only on our side and
      `api/flynapse_api/shutdown_budget.py` imports it, so a "take theirs" resolution breaks the api repo.
- [x] **D.2 DONE** (bigger than written — the harness join was silently blind, 44 tests). Re-apply the user-content fixes their conflicts discard (both prompt-logging sites, filename, S3 key).
- [x] **D.3 DONE**, plus a second merge-invented defect the item did not predict: the drain also landed OUTSIDE the shutdown span. Repair the shutdown-drain handler the clean auto-merge breaks — their side deletes the traceback
      import, ours calls it. Gate on a pyflakes run.
- [x] **D.4 DONE.** M-CAPTURE was FALSE on the merged tree; M-TOOLIO-2's retirement is accepted, so only M-CAPTURE applied. Apply M-CAPTURE and M-TOOLIO to `config.py` and the policy reader.
- [x] **D.5 DONE**, hoisted above the ACCUMULATOR rather than the snapshot — an opted-out tenant now accumulates nothing all turn. Hoist the tenant policy read above the snapshot build, so an opted-out tenant's prompt is never
      materialised and redacted in memory just to be discarded.
- [x] **D.6 DONE.** Move capture off the request critical path — a shielded task with a bound, as the block save does.
- [~] **D.7 PARTLY DONE** — paths fixed (6 files), cache cleared; the SHA-pinned guard's DELETION is blocked and owner-owed (see the phase notes). Fix the nine depth-coupled test paths; clear the new cache in the composition-root fixture; drop the
      SHA-pinned branch-hygiene guard, which pins a branch that does not exist here and re-activates after the
      merge.
- [x] **D.8 DONE** — four sites, not three, and their guard was made honest enough to be ours. Fix our own three raw-exception log sites in the lang browser transport, which their privacy guard
      correctly flags; then their guard should run clean and becomes ours.
- [x] **D.9 CLOSED by Phase B2, 2026-09-20 — subject to owner ruling B2-R1 below.** The wire-or-hold decision
      was B2's, and B2 wired it: the LLM-turn-summaries card now reads the API through TanStack `useQuery`
      (`hooks/api/useObservability.ts`), with a typed failure, a response contract in place of a bare cast, and a
      corrected docstring — the card renders 180-character previews of the user's question and the model's answer,
      verified against `llm_turn_content_read.py`, which is not what the docstring used to say.
      **The RBAC intent is NOT confirmed and is the owner's call (B2-R1):** the card sits OUTSIDE the improvement
      page's internal-only gate. `notInternal` is derived from the other queries' errors, so on first paint it is
      `null` and the card mounts and fetches unconditionally. The route gates on `view_dashboard`; the page's
      `RouteGuard` requires `view_memory_admin`. A **non-internal** holder of both therefore sees real question and
      answer text on a page whose other three panels refuse them — and B2.3 made one aspect worse, because the query
      cache now holds those rows for a 5-minute `gcTime` after the card unmounts behind the notice. This is the
      colleague's placement; B2 deliberately did not change it, because it is a product decision.
- [x] **D.10 DONE**, mutation-proven. Invert the permissive default in the read DAO's scope clause.
- [x] **D.11 DONE** — restored content-FREE (type + frames), because the message it over-corrected really could quote the question. Restore the bounded failure reason in the synthesis and db-query logs their sweep over-corrected —
      the code name alone cannot say why nine turns failed.
- [x] **D.12 DONE**, confirmed open by code-read first. Gate the legacy root-span suppression on a genuinely configured provider; as written it is always on
      and the legacy span disappears regardless of whether OTel is up.
- [x] **D.13 DONE.** Relock (resolve `pyproject.toml` to the union, then lock — never hand-merge). Run the app lane.

### Phase E — copilot-mro, deployment half
- [x] E.1 Reject-list first (M-ACCEPT, M-PINS), so nothing downstream depends on it.
- [x] E.2 Collector profiles: take the New Relic overlay, the four durability fragments, the env examples and
      the validate script. Their fragments are correctly exporter-only with no `service:` block, so a profile
      cannot inherit another's exporter. Reword the queue's "outage budget" claim — a five-minute retry cap
      survives a restart, not an outage — and drop the unearned "memory limiter" claim.
- [x] E.3 Document that production must bind-mount the file-storage dir: a demo box with tmpfs `/tmp` plus a
      durability fragment gets a "durable" queue that evaporates on restart.
- [x] E.4 Compose: take the Phoenix split, the loopback browser receiver and the tmpfs mode. **Immediately**
      fix the otel conftest — the base compose loses the Phoenix service while our smoke override still defines
      one with no image, and the overlay requires an API key the compose env does not set. This is the most
      dangerous auto-merging interaction in this half.
- [x] E.5 Alert rules: ours for browser alerts (theirs lacks the grouping fix that makes three Web-Vitals rules
      armable, and the sample guards). Adopt their rewritten agent-rule guard — it catches *stale* dark wording,
      not just missing wording — and retire ours, which fails outright on their descriptions.
- [x] E.6 Grafana per M-GRAFANA / M-FRONTEND; keep both phase-8 satellite boards.
- [x] E.7 Catalogue: ours as base, graft their panel-to-source inventory, and apply their CloudWatch
      brace-selector normalisation to our aws blocks — our current spellings mix Prometheus suffixes with
      dotted OTLP names and will not resolve.
- [x] E.8 Tests last, resolving the two that share the dark-note vocabulary together.
- [x] E.9 Non-container lane. Gate per §2.4 against the **measured** pre-merge baseline, re-confirmed on
      2026-09-20 at `417df303`: **135 collected, 111 passed, 24 skipped**. Collected must not decrease, passed
      must not decrease, and every new skip must be named. (The old "87/0, expect 100–112" gate was a *gated
      container* run and could not fail.) Then the
      container lanes and both validate scripts — the only thing that has ever proved the New Relic overlay and
      the four durability compositions actually load. Neither side has run it.

#### Phase E — what Phase D hands it, 2026-09-20

Everything below is already IN the merged tree and wrong. None of it conflicted, so none of it was
resolved; the merge commit records them and E fixes them.

- [x] **E.0a M-GRAFANA, `datasources.yml`.** Auto-merged to theirs: the `flynapse-postgres` entry is
      GONE and `deleteDatasources: [{name: Flynapse Postgres, orgId: 1}]` is PRESENT. Restore the
      entry, drop the deletion block. Until this lands, our `fn-frontend` panels 7 and 8 and both
      exact-spend panels point at a uid that does not exist.
- [x] **E.0b M-GRAFANA + M-TOKENUSAGE, `llm-agents.json`.** Auto-merged to theirs: both exact-spend
      panels deleted, and five token queries rewritten `gen_ai_client_token_usage_sum` → `_total`.
      The emitter is a Histogram as of Phase D, so `_total` now matches nothing at all. Also fix
      "Tool attempts and failures": its B target queries `tool_outcome="error"` on BOTH sides'
      history and the merged emitter emits `"failure"` (`telemetry.py`), so that panel has never
      matched a series. Their catalogue inventory has this right; the board does not.
- [x] **E.0c M-GRAFANA, `oss-profile.md`.** Auto-merged to theirs, losing three things: the
      `POSTGRES_READONLY_PASSWORD` rotation row (the credential the kept datasource logs in with),
      the pointer to the `fn-llm-agents` exact-spend panels, and the sentence saying the datasource
      is EXPECTEDLY unhealthy in the standalone observe stack — without which the first person to
      run the smoke files a false bug. Their two true clauses (the agent spans land with this merge)
      are worth keeping. §2.2a guessed this file would lose the exact-spend SECTION; it did not.
- [x] **E.0d The dark-note vocabulary is RED right now.** `llm-agents.json` silently took their
      `"STATIC-MAPPED, live retrieval pending:"` descriptions, so our
      `test_dark_panel_notes_are_present` — which demands `DARK until ` or a dated `LIVE since …` on
      every `gen_ai[._]`/`agent_` panel — fails on the merged tree. `CATALOGUE.md` already carries
      BOTH vocabularies after D's hand-merge. Resolve the three boards, the two tests and the
      catalogue in ONE pass (E.8), not file by file.
- [x] **E.0e The positive guard §2.2a asked for.** `test_flynapse_postgres_datasource_is_declared_
      kept_and_used`: the datasource is declared, `deleteDatasources` is empty, and all four
      M-GRAFANA panels still read it. It fails on all three limbs today, which is the point — it is
      the guard that would have caught this silent merge, and neither side's existing pair can
      satisfy it.
- [x] **E.0f M-FRONTEND's graft.** Their "Slowest Pages" panel is the only additive thing on their
      3-panel board; append it as id 19 at `{h:8,w:12,x:0,y:72}`. Its description needs a
      `DARK until ` / dated `LIVE since …` note or our D6 guard fails it on arrival. Verified: the
      `browser.app.boot` emitter IS live in our dashboard, and the collector allow-list already
      passes `load_complete_ms` and `entry_route_pattern`, so nothing else is owed for it.
- [x] **E.0g M-TOKENUSAGE's board half.** `CATALOGUE.md` lines with `_total` (5 sites) and
      `iac/dashboards/llm-agents.json.tftpl`. Phase D deliberately left these so the file is
      rewritten once.
- [x] **E.0h `test_compose_image_pins.py` no longer covers the Phoenix split.** `COMPOSE_FILES`
      scans the original four stacks; theirs' split moved a pinned image into
      `deployment/docker-compose.phoenix.yml` and `deployment/poc/docker-compose.phoenix.yml`.
      Both are correctly pinned TODAY, and nothing would notice if they stopped being.
- [x] **E.0i The adopted agent-rule guard is an allow-list, not a rule.** Theirs' `PENDING_RULE_
      SERIES` / `EMITTED_RULE_SERIES` are two hand-maintained tuples, so a NEW rule on an unemitted
      `agent_*` / `gen_ai.*` series falls through both and is checked by nothing. Ours' regex caught
      that class generically. The elegant fix is a derived emitted-series inventory.

### Phase F — docs — **DONE**, six commits `1f9ee8e`..`1d4f13e`
- [x] F.1 Merge docs with our master plan as the base; graft their new sections.
- [x] F.2 Resolve the phase-numbering collision: their "Phase 8 — audit follow-ups" becomes Phase 11; their
      Phase 1c keeps its name and is recorded as a re-cut of our gated 1b.7.
- [x] F.3 Fold their research 08 in as the Task R starting baseline, correcting its central finding: **Gate M
      was declared 2026-09-14** — their branch could not see it, so their gate reassessment concludes "still
      closed" and defers the sole `chat_turn_facts` writer on that basis.
- [x] F.4 Reconcile the two outcome vocabularies: their `operation.outcome` against the spec's
      `agent.outcome` / `tool.outcome`, and catalogue the attribute spellings their spans introduce that no
      document names.
      **The ruling is `<subject>.outcome`, where the subject is the noun the span or metric is about, and
      neither spelling is renamed.** The agent runtime's subjects — `agent`, `tool`, `subagent` — are ruled by
      spec §6.3 and are not merely span attributes: they are exported Prometheus label names consumed by two
      Grafana boards, the agent alert rules and `iac/dashboards/llm-agents.json.tftpl`, so they cannot move
      without breaking consumers in three repos. Everywhere else the subject is the generic `operation`,
      because a parser is not an agent, and because one key is exactly what lets a single "which operations
      failed in the last hour" query span all eleven non-agent boundaries at once.
      **The real defect is the values, not the prefix.** `error`, `failure` and `failed` are three spellings of
      one outcome — the code already carries a set literal in `agent_shared/telemetry.py` that normalises them,
      which is the tell — and `operation.outcome` carries **16 values across 49 call sites with no declared set
      anywhere.** Every such normaliser is a place where the next value is silently non-failing. The detail,
      the full attribute catalogue and the open questions for Task R.2 are in
      `plans/observability-rebuild-research/09-outcome-and-span-attribute-reconciliation.md` (new, written by F).

### Phase G — close the gaps (scope M-SCOPE)

> **PLAN HYGIENE — READ BEFORE BRIEFING ANYONE FROM THIS SECTION.**
> **This file's own staleness has caused TWO bad briefs**, and both were caught only because the
> implementer verified before acting. **G.29** carried `[x] DONE` at one line and `[ ] none fixed` at
> another; an implementer was briefed from the stale line and opened its report *"the brief is one pass
> stale — three of the four P1s were already done."* **G.18** was committed at `utils-obsm 24e073f`
> **six commits before** it was briefed as *"the largest remaining item"*; its box was simply never
> ticked. **A third near-miss:** the `iac` alarm item was briefed from an audit of a commit **three
> behind** the tree, and was already fixed.
> **The rule that follows: a checkbox in this file is EVIDENCE, NOT TRUTH.** Before briefing any item,
> check the tree — `git log` the named files and grep for the symbol the item says is missing. Every
> brief must tell its implementer that the item's state is a claim to verify, and that finding the work
> already done is a **valuable result, not a wasted run.**
> Duplicate entries are the specific mechanism, so: **one checkbox per item, and when an item closes,
> close the entry that already exists rather than adding a second.**
>
> **THE AUDIT THIS BANNER DEMANDED — RUN 2026-09-20, READ-ONLY, ALL 60 OPEN/PARTIAL BOXES CHECKED
> AGAINST THE ACTUAL WORKING TREES. ITS VERDICT SUPERSEDES EVERY CHECKBOX BELOW.**
> **16 of 60 boxes — 27% — were lying.** That is a HIGHER mismark rate than the three incidents that
> prompted this banner, so the banner was not an over-reaction; it was an under-estimate.
> **Census correction:** 83 Phase-G boxes (23 `[x]` · 45 `[ ]` · 15 `[~]` = **60** open/partial, not 61).
> - **Already DONE, mismarked (16):** G.5 · G.16 · G.27 · G.31 · G.37 · G.38 · G.41 · G.42 · G.51 ·
>   G.52 · G.56 · G.67 · G.70 · G.72 · G.78 · G.80.
> - **PARTLY done (11):** G.1 · G.6 · G.10 · G.35 · G.36 · G.44 · G.46 · G.47 · G.61 · G.64 · G.75.
> - **GENUINELY OPEN (21):** G.3 · G.4 · G.7 · G.8 · G.23 · G.28 · G.39 · G.40 · G.43 · G.48 · G.53 ·
>   G.54 · G.58 · G.59 · G.65 · G.66 · G.69 · G.73 · G.76 · G.81 · G.83.
> - **OWNER-GATED, no code possible first (9):** G.17 · G.32 · G.34 · G.60 · G.68 · G.71 · G.74 · G.77 · G.82.
> - **WRONG AS WRITTEN (3):** **G.9** (the owner DROPPED it — it is struck through and still carries an
>   unchecked box, an artefact) · **G.20** (the guard already exists; this is a briefing rule plus a
>   paydown tranche, **not work to dispatch**) · **G.79** (self-refuted, and its code half is already done —
>   the remaining action is a PLAN EDIT).
> - **UNRESOLVED (1):** G.64(c), the memo census at `dashboard-obsm/lib/auth/PermissionContext.tsx:458`.
>   The auditor **declined to guess it** rather than fill the cell.
>
> **THE SAME FAILURE SHAPE, ONE LAYER IN:** G.42, G.51 and G.52 each carry a *"STILL OPEN:"* clause naming
> work that is **already in the tree**. Fixing a box's mark is not enough — **its body lies too.**
>
> **DUPLICATES AND OVERLAPS — merge before dispatching, or two lanes collide on the same files:**
> **G.53 ≡ G.66** (identical root cause, the venv `.pth` files; found by two lanes). **G.10 ⊂ G.28**
> (G.10's utils half is done; G.28 carries the remainder — G.10 should close). **G.38 → G.49/G.51/G.75**
> (its sweep was EXECUTED and became those three; dispatching G.38 re-runs completed work).
> **G.27 ⊂ G.54** (root fix committed; the residual is already enumerated inside G.54, which names the live
> instance). **G.79 ⊂ G.49(6)** — the fourth instance of the class that caused the first bad brief.
> **G.8 ∩ `agent-evaluation-completion.md` Phase 8** — reconcile the boundary before dispatching either.
> **G.20 ∩ G.14/G.19** — a constraint on G.14's remaining tranche, not independent work.
> **G.58 ∩ G.36(d) ∩ G.77** — three items carrying pieces of one question. **G.65's own recommendation
> partly landed inside G.64(a)** — its brief must say so or it will be rebuilt.
>
> **DRIFT IS LIVE WHILE YOU READ THIS.** During the audit's own run `copilot-mro-obsm` gained **10 dirty
> files** and `utils-obsm` gained 1 — including G.75's copilot-mro half closing at 22:05 **under the
> auditor**. No HEAD moved. **Re-check any tree that has a live implementer before briefing from this.**
>
> **RANKED DISPATCH ORDER (by consequence, not by number):** 1. **G.40** — `python -m utils.s3_service`
> deletes real objects against a live prefix while printing *"Would delete"*; **the only item here that can
> destroy customer data by being run.** 2. **G.43** — the branch **is not green at its own HEAD**: guards
> committed at `870e75c` expect 30/27 `failure_fields`, HEAD holds 5/3, so a clean clone or CI run of
> `obs-merge` is RED until the uncommitted files land. **This gates every other verification claim.**
> 3. **G.53+G.66** — the venv's four `.pth` files put the PRE-MERGE checkouts (`core`@`master`,
> api/utils/copilot-mro@`langgraph-merge`) ahead of the merged trees; **this is the mechanism behind
> "1276/1399 passing against the pre-merge branch" and it is still live.** 4. **G.73** (blocked only on
> G.74(1), four non-mutating AWS calls). 5. **G.34** — a deleted chat's facts row survives with `user_id`,
> `session_id`, `cited_documents`, read by NINE panels with no `deleted` filter. 6. **G.28.** 7. **G.59** —
> a RED test at committed HEAD, **which invalidates the close-out gate's estate numbers until fixed or
> explicitly excepted.** 8. **G.69.** 9. **G.44 producer + G.46's core and copilot-mro shares.**
> 10. **G.58+G.83.** 11. **G.81.** 12. **G.54's residual.** 13. **G.23(1).** 14. **G.75's utils half.**
> 15. **G.76(a)(b)(c) + G.64(b)(e)** — five one-liners. 16. **G.3, G.4, G.7, G.8, G.48, G.65** — no urgency.
>
> **One gate may not exist:** **G.47 likely needs NO owner ruling** — `@opentelemetry/sdk-metrics@2.11.0`
> is already on disk transitively, so the "new dependency" framing that created the gate is false.
>
> **STATE AT COMPACTION, 2026-09-21 — read this before any number below.** ~~102 items: 57 done · 8 partly ·
> 37 open~~ **110 items: 63 done · 15 partly · 32 open** (101 at the audit recount, +G.97, +G.106–G.110) — recounted 2026-09-21 by top-level box: the 104
> `- [.]` lines in Phase G, less the two struck duplicate entries (the old G.40 and G.66), with G.1's two
> boxes counted once; G.9 (struck because dropped, not duplicated) counts as done, and G.104 and G.105 are
> included, both open. The superseded figure counted raw lines, duplicates included, before G.104/G.105.
> **An audit on 2026-09-21 re-measured every open and partly-open item against the merged trees, and 7 boxes
> were stale** (G.7 · G.48 · G.64 · G.83 · G.92 · G.94 · G.103); six more closed by the plan edits it called
> for (G.8 · G.10 · G.39 · G.65 · G.66 · G.79), and each corrected body carries a dated `AUDIT 2026-09-21` line.
> **STATE AT COMPACTION #2 (2026-09-21, late) — supersedes the compaction-#1 paragraph.** Every lane now
> commits by named path under **M-COMMIT**; **NOTHING IS PUSHED ANYWHERE** (obs-merge branches have no
> upstream; flynapse-otel 5 / shift-optimizer 3 / telegram-bot 3 commits ahead on `main`). Every
> implementer lane gets an **independent Opus adversarial review AFTER it commits**, and the reviewer —
> never the implementer — emits the claims table; guard-only fix commits proven by the reviewer's own
> plants skip a second review. **Owner rulings taken this session** (§4a-bis): M-CASCADE, M-OTEL-SCOPE,
> M-COMMIT, M-DRYRUN, M-LOGLINES, M-AWSPROBE, **M-COMMENT-PII, M-TRACEBACK, M-SATELLITE-SCOPE**.
> **The headline finds since compaction #1** — each a tier-0 leak class the per-opener sweeps could not
> see: **G.110** auto-instrumentor spans exported exception text incl. Postgres BOUND VALUES (fixed at the
> export boundary, `flynapse-otel eac44c0`, reviewed clean); **G.112** the LOG pipe does the same (lane
> live); **G.111** urllib3 `http.url` carries S3 bucket + tenant object keys (lane live); **G.104** core's
> 500/400 bodies carried driver and S3 text (500 fixed; 400 PDF body in the live core fix batch). **Five
> lanes were live at compaction #2**; resume from the SDD ledger's **CHECKPOINT 26**, which lists each lane,
> what to do when it reports, every per-tree queue and the owner queue.

> **STATE AT COMPACTION #12 (2026-09-22, ~05:45) — supersedes #1–#11. OWNER CAP 1; controller = Fable 5; agents Opus; NETGUARD OUT of the project (owner: never asked for it — committed guard code stays, nothing more built, no adoption; 10 copilot-mro tests sending real Bedrock requests = parked fact for a later project). The model switch killed all 10 agents; all were relaunched fresh from durable state, then the owner cut the cap to 1: the copilot-mro r8 fix finisher is LIVE; the other 9 lanes are PAUSED with PAUSED.md files (ids + resume order = SDD ledger CHECKPOINT 40). Merge-blocking = P0/P1 only; last rounds declared for utils/iac/dashboard/r7b; closing reviews = copilot-mro r9, flynapse-otel r8 (ratchet+detector only), shift r2, core r10 narrow; then M-FAILURE-HOME finish, the serial merges (r7b → tbA..tbD), one follow-ups batch, FABLE-INDEX.md, the final reality audit. Trees: copilot-mro-obsm `ce545211`+ · flynapse-otel `dd78644`(+3 dirty netguard files being restored) · core `b540596` · shift `08970d2` · tbA `14e09f27` · tbB `752ba4a9` · tbC `ece9c60e` · tbD `3637540d` · r7b `53411ed7` · utils `fe45c35` · api `fbd394c` · dashboard `f8c4614` · iac `d1ebeb1`. Nothing pushed. C15 never runs until the owner rules anonymisation scope.**

> **OWNER SIMPLIFICATION (2026-09-22, after api r9) — governs everything below it.** (1) **Review rounds only after serious fixes:** a new round follows only a P0/P1 fix, a redesign, or an irreversible change (C15); P3 leftovers go to the follow-ups batch or Future Improvements, and the merge's full lanes + the final audit are the check. Last rounds: utils r9, iac r5, dashboard r4, r7b r3 (light), api r9, tb C+D r1. Still to come: copilot-mro r9 (P1), flynapse-otel r8 (ratchet + detector ONLY; netguard OUT — owner, Add. 215), shift r2 (redesign), core r10 NARROW (C15 + sentinel + top_cited). Dropped: telegram r6 and every further round of the repos above unless a P1/P2 appears; the tbA fix batch is checked by the merge's full lanes (incl. `tests/agent_sdk/core` + `tests/architecture`). (2) **Light recipe for P3 work:** touched suites at HEAD, no per-commit sweep, mutation proofs only for P1/P2 fixes and survivor pins; full rigour for serious fixes and merges. (3) **Packet:** the README totals + per-file row-count column are DROPPED; replaced by one `FABLE-INDEX.md` (the F1/F2/F3 chunk lists of tier-1/2 rows still standing, the deferred register, owner decisions) that the final reality audit works from. (4) **M-FAILURE-HOME ends:** one final port of utils `fabb94c`'s walk into flynapse-otel, then utils IMPORTS `flynapse_otel.failure` and deletes its copy (re-exporting for callers); `UTILS_PARITY_SHA` tracking stops. (5) **Moved OUT of this project** (own plan later): dashboard G.54 (48 flat test files → two-level layout); the three pre-existing test-isolation bugs (memory `sys.modules` leak, `test_seed_dev_tenant.py` alone, `[deadline]` flake) — known reds. (6) **Owner accepted the controller's defaults:** narrow-screen series order KEEP; the authored-refusal carve-out (a) — a typed sanctioned refusal may print its remedy (seed_dev_tenant's four handlers, `pdf_linearize`, tbD's held site if that shape); R7B-EXIT/CLOUD/SCRAM/G113 ratified; the cli worktree + `obs-merge-cli` branch REMOVED (merged at `557a178f`; done 2026-09-22); core `e9fb7b3..4171575` NOT squashed; chart_create gets a sanctioned location+type-only pydantic describer (copilot-mro follow-ups batch). **Tightened 2026-09-22 (controller now Fable 5):** merge-blocking = P0/P1 only — closing-review P2s go to the follow-ups batch, not a pre-merge fix round; consumer adoption moves to a later plan (netguard adoption dropped with netguard — owner, Add. 215); the queue ends at merges → follow-ups → FABLE-INDEX → final audit. **Review trust (owner ruling 2026-09-22):** the four closing reviews and the final reality audit run on **Fable 5 agents** — the agents-are-Opus rule is overridden for REVIEW lanes only; Fable reviewers read the actual diffs at pinned SHAs (claims files/packets are indexes, never evidence), spot-re-run a sample of claimed proofs (mutation reruns, red-before tests), and treat Opus-authored absence claims (MERGE-CLEAN verdicts, severity downgrades) as unverified until covered; implementer lanes stay Opus. Last gate before any push: one independent Fable review chat over the final merged tree. **Still owner-owed:** chat-delete anonymisation scope (and so the C15 run), C1–C15 + B14, the CloudWatch monotonic-sum probe (live AWS), `.wslconfig`, dashboard second-batch scope, when to push.

> **STATE AT COMPACTION #11 (2026-09-22, ~05:30) — supersedes #1–#10. Resumed after the full pause; owner cap 10; nothing pushed.**
> **Done since the pause:** core r8 batch `16cd1ae` · api r8 batch `fbd394c` (`unshare -rn`: 0 connects to :5432) · telegram r5 `47a08b7` · cli r2 + **MERGED** into copilot-mro-obsm `557a178f` · shift P3 `0b4de00` · **all four M-TRACEBACK lanes converted** (tbA `79bad4ac` 224/224, tbB `752ba4a9` 266/266, tbC `ece9c60e` 129/129, tbD `3637540d` 101/102 — one site held for an owner ruling) · dashboard r3 fixes `f8c4614` · utils r8 fixes `fe45c35` (fail-closed redesign of the metric-key inventory) · iac post-r4 fixes `d1ebeb1` (apply now `needs:` a shared guards workflow; CLI bullet WIRED) · N6 satellites packet FINAL (191 rows).
> **Verdicts:** dashboard r3 FIX-FIRST → fixed · flynapse-otel detector r7 FIX-FIRST 0/1/4/5 + netguard r1 0/1/6/3 (`240.0.0.1` struck; port api's guard first) · utils r8 MERGE-CLEAN · iac r4 MERGE-CLEAN · copilot-mro r8 FIX-FIRST 0/1/5/10 (**P1 measured: the settle-time facts writer lacks the chat-liveness check**) · r7b r2 MERGE-CLEAN 0/0/1/6 (merge recipe in the ledger) · core r9 FIX-FIRST 0/0/4/11 (**C15 SQL on HOLD** until fixed).
> **Live:** reviews api r9, tb C+D, tb A+B, dashboard r4, iac r5; fix batches flynapse-otel, copilot-mro r8, r7b fix-forward, shift P2, core r9. **Merge order:** copilot-mro r8 fixes → r7b → tbA → tbB → tbC → tbD (after their reviews) → copilot-mro follow-ups.
> **Owner:** C1–C15 + B14; chat-delete anonymisation scope (llm_usage, llm_model_calls, improvement_*, memory events); seed_dev_tenant authored-refusal carve-out; lane A model-facing typed signals; r7b's four defaults; dashboard second-batch scope (G.54); CloudWatch monotonic-sum suffix probe; cli worktree removal; core squash; `.wslconfig`.
> **Resume:** SDD ledger **CHECKPOINT 39** (agent ids, queue, merge recipes, owner sheet).
>
> **STATE AT FULL PAUSE (#10) (2026-09-22, ~02:05) — supersedes #1–#9. EVERY AGENT PAUSED BY THE OWNER; every lane resumable by id; every tree CLEAN; nothing running; nothing pushed.**
> Trees: core-obsm `b730a95` (r8 fixes: P1-1, P2-1..P2-5, P3-1..5/10/11 in; owed db×2, authz, P3-6/7/8/9 — note `e9fb7b3..4171575` red at own HEAD, `b730a95` restores) · api-obsm `2d49c3f` (r8: P2-1/P2-2/P3-1/P3-2 in; P3-3..13 owed) · utils-obsm `179cc6d` (review r8 PARTIAL: MERGE-CLEAN 0/0/1/9 provisional) · copilot-mro-obsm **`557a178f` = the cli merge landed** (G.4 + G.7(c); merged unit lane 6797/0 F; review r8 of `62c7413d..735f8213` PARTIAL: 1 P1 cand = settle-writer liveness gate) · cli `b5cf1524` DONE · r7b `afe79dbb` (review r2 PARTIAL: 0 P0/P1, P2 cand R7B2-12 AWS host suffix; trial merge onto `557a178f` clean bar one duplicate fix) · tbA `6ebb6d1f` / tbB `b580e541` / tbC `6ea75db4` / tbD `38e27153` (M-TRACEBACK conversions ~half; merge base now `557a178f`) · dashboard-obsm `4a7714a` (review r3 PARTIAL: FIX-FIRST on P2-1 three-panel copy; `2a9b0f4` sub-review ~6 P3) · flynapse-otel `df503c2` (port DONE; detector r7 review PARTIAL FIX-FIRST 0/1/3/5 — ratchet fallback adopts a moved register; netguard r1 PARTIAL FIX-FIRST 0/1/5/4 — skipped/xfailed refusals never fail; **`240.0.0.1` routes on this host — strike it**) · iac `74346bb` (review r4 PARTIAL MERGE-CLEAN 0/0/0/3+1) · telegram-bot `47a08b7` **r5 batch DONE** (G3 was a dead line; new detector limit: leading-underscore class raises unread) · shift-optimizer `2a8e3de` (P3 paused).
> **Packet:** PARTIAL files now in the packet dir for utils r8, r7b r2, dashboard r3, flynapse-otel detector r7 + netguard r1, iac r4; copilot-mro r8 and the `2a9b0f4` sub-review are partial in durable scratch only; N6 `claims-satellites-rounds.md` PARTIAL; README totals + row-count column owed. **Owner sheet:** C1–C15 + B14; **C15 SQL is written** (`core-obsm/scripts/rbac/anonymise_already_deleted_chats.sql`, not run); NEW: `llm_usage` spend after chat delete (a/b/c); narrow-screen series order (recommend KEEP); cli worktree/branch removal; `.wslconfig` cut — now is the break.
> **Resume:** SDD ledger **CHECKPOINT 38** (every lane's agent id, tree SHA, remaining work and `~/.claude/scratch/obs-merge/<lane>/PAUSED.md`; resume order reviewers → core/api → tbA–D → shift → N6). The three lessons below the crash lesson still apply.
>
> **STATE AT COMPACTION #9 (2026-09-22, ~01:45) — supersedes #1–#8. RESUMED; a WSL memory spike then killed every agent; relaunched from measured tree state; owner cap 10.**
> Nothing pushed. Trees at compaction: core-obsm `376ae7b`+ (r8 fixes landing: P1-1, P2-1/P3-11 in; P2-2 C15 SQL, P2-3, P2-4, P2-5, P3s pending) · api-obsm `e3ba207`+ (r8 fixes landing) · utils-obsm `179cc6d` (review r8 running) · copilot-mro-obsm `735f8213` (review r8 running; cli merge landing next from `copilot-mro-obsm-cli` `7880bc44`+) · copilot-mro-obsm-r7b `afe79dbb` (review r2 running, then merge) · **M-TRACEBACK fan-out PAUSED, clean:** tbA `6ebb6d1f` (128/161 left of 171/224), tbB `b580e541` (89/133 of 177/266), tbC `6ea75db4` (36/56 of 90/129), tbD `38e27153` (23/26 of 69/102; 5 patches pending in durable scratch) · dashboard-obsm `4a7714a` (final review running) · flynapse-otel `df503c2` (M-FAILURE-HOME parity at utils `1a42390` DONE; `search` URL marker DONE; detector r7 + netguard r1 review running) · telegram-bot `d43bd5d`+ (r5 P2s in; P3s landing) · iac `74346bb` (review r4 running) · shift-optimizer `2a8e3de` (P3-1, P3-2 in; SO-14 + proofs paused).
> **Packet:** N4 `claims-api-rounds.md`, N5 `claims-flynapse-otel-rounds.md` filed; N6 `claims-satellites-rounds.md` PARTIAL (paused); all 11 original files carry `## Re-statement 2026-09-22`. README totals still owed. **Owner sheet:** C1–C15 + B14 unchanged (C15 SQL path comes with core's report). **Merge order (serial, controller):** cli → r7b → tbA → tbB → tbC → tbD → copilot-mro follow-ups → review of the merged fan-out. **Standing since tonight:** `pytest-slot.sh` (machine-wide semaphore), durable state under `~/.claude/scratch/obs-merge/<lane>/`, incremental claims files, per-lane agent ids in the ledger (crash → resume by id or relaunch from measured state); `/tmp` no longer emptied at boot (owner applied the tmpfiles override); `.wslconfig` `memory=18GB swap=8GB` still recommended at a natural break. Resume from the SDD ledger **CHECKPOINT 37**.
>
> **STATE AT COMPACTION #8 (2026-09-22) — supersedes #1–#7. ALL AGENTS FLUSHED; THE OWNER PAUSED NEW LAUNCHES.**
> Nothing pushed. The checkboxes still read about 67 done · 28 partly · 18 open, but they LAG the code (G.4, for one, is
> built and reviewed twice while its box reads open). The final reality audit recounts. Heads: core `b4d2c33`, api
> `b3178f4`, utils `179cc6d`, copilot-mro `735f8213` (+ unmerged cli `f1100629` and r7b `afe79dbb`), dashboard
> `4a7714a`, flynapse-otel `d1e531f` (detector r6 + **M-SHARED-NETGUARD built**, §4a-bis row filed), telegram-bot
> `645b334`, iac `74346bb`, shift `8bd4d66`. Reviews that landed this stretch: api r8 FIX-FIRST (Rule B blind to prefix
> LIKE, a tier-2 cross-tenant login risk); core r8 FIX-FIRST (**P1: a user-search term, often an email, logged at INFO**);
> utils r7 FIX-FIRST → FIXED `179cc6d`; iac r3 → fixed `74346bb`; telegram r5 MERGE-CLEAN (3 P2); cli r2 MERGE-CLEAN
> (controller call: `status_code` IS the category). **Owner-only:** C1–C15 + B14; the owner holds the exact C1/C9/C12
> commands (pin PYTHONPATH to the -obsm trees). **Process changes:** a fresh implementer per batch; the speed tools and
> the CLAUDE.md "Test Run Speed" rules (Lessons, last four entries). The per-tree next steps are in ledger CHECKPOINT 35.
>
> **STATE AT COMPACTION #7 (2026-09-22) — supersedes #1–#6.** **By checkbox: 113 items — 65 done · 27 partly ·
> 21 open.** Nothing pushed. The owner has ruled ALL of A1–A19 and B1–B13 (§4a-bis; newest rows M-PERMISSIONS-ENDPOINT,
> M-LEGACY-TENANT, M-CAPTURE-TRUNCATE, M-CLI-TELEMETRY, M-EMAIL-DOOR, and controller calls appended to
> M-WEAVIATE-REFUSAL / M-SIGNUP-ORACLE / M-INVITE-FRAGMENT). **Next owner step: the C actions (C1–C9)**; the
> Phase H DDL now includes the `automation_runs.traceparent` add (BEFORE core; §2.2 step 4) and the
> `llm_turn_content.content_s3_key` drop. Built since #6: the shared exception-text detector in flynapse-otel
> (under review), `flynapse_otel.failure`, `_root.py` md5 3d192468 in all four repos, the panels branch merged into
> copilot-mro (`ca752296`), core's M-PII-IDS / M-SIGNUP-ORACLE / M-INVITE-FRAGMENT half, api's traceparent consumer,
> utils' M-STACK-HEADERS + M-LEGACY-TENANT, dashboard's reason gate + invite page, shift's SolverInputError fix.
> **The Fable review packet was NOT maintained after G.5 (2026-09-20)** — owner asked again; rebuild in progress per
> ledger CHECKPOINT 32 (lesson recorded). Ledger: CHECKPOINT 32.
>
> **STATE AT COMPACTION #6 (2026-09-22) — supersedes #1–#5.** **By checkbox: 113 items — 65 done · 26 partly ·
> 22 open.** **NOTHING PUSHED.** **The owner walked the decision sheet: all 19 quick items (A1–A19) and B4, B5, B6,
> B7, B10 are RULED and recorded in §4a-bis** (M-VERSIONS, M-GENAI-TENANT, M-WEAVIATE-REFUSAL, M-RUN-REASON,
> M-NOTE-KINDS, M-ALARM-DENOMINATOR, M-CHART-CELL, M-SHIFT-RUNERROR, M-TOOL-ERRORS, M-JOB-TRACEPARENT,
> M-EMBED-INTERNAL, M-FAILURE-HOME, M-PII-IDS, M-PHOENIX-ON, M-FACT-LIMITS, M-LAZY-DYNAMODB, M-LEGACY-DELETE,
> M-LEGACY-PANELS, M-WEAVIATE-LEFTOVERS, M-SIGNUP-ORACLE, M-STACK-HEADERS, M-FACTS-FAILURES, M-REVOKE-CACHE,
> M-FACTS-ANONYMISE, M-INVITE-FRAGMENT); **B8, B9 await plain re-asks, then B11 and the C actions.** **Since #5:**
> g106 MERGED into copilot-mro `obs-merge` (`75947461`; G.113 password closed there; worktree removed); the G.53
> `_root.py` carry was re-checked MERGE-CLEAN and **utils has carried (`10651dc`); core next, then copilot-mro**;
> flynapse-otel r4 MERGE-CLEAN (7 P2s being fixed, 2 done); utils r4 FIX-FIRST (P1: the new safe loguru default
> leaves the interpreter hooks at defaults); copilot-mro M-TRACEBACK guard + anti-gaming register landed (530
> debt keys, 4 conversion lanes), review r6 running; a second copilot-mro worktree `copilot-mro-obsm-panels` builds
> the legacy-metric deletions/panels. Resume from the SDD ledger **CHECKPOINT 30**.
>
> **STATE AT COMPACTION #5 (2026-09-22) — supersedes #1–#4.** **By checkbox: 113 items — 62 done · 25 partly ·
> 26 open.** **NOTHING PUSHED.** New owner rulings: **M-G117-DEFAULT, M-SHARED-CHECK, M-WEAVIATE-DOOR** (§4a-bis).
> An owner **decision sheet** exists (`.superpowers/sdd/…/owner-decisions-2026-09-22.md`: 19 quick · 10 choices ·
> 5 actions · 16 settled); the owner is walking through the 19 quick items next. **Since #4:** the g106 branch is
> finished (SCRAM everywhere, socket-swap closed with a sticky dir + `require_auth`, passwords off argv) and is
> being merged — **until it lands the G.113 role password is still live on copilot-mro `obs-merge`**; core review
> A2 clean / B2 found the `/pdf` routes still LOG object keys and the 422 handler echoes whole request bodies
> (fix lane live); coverage matrix refreshed (138/58/50/30 unchanged; fallback-only clients 5 → 0 of 17); api
> Cognito spans built. Resume from the SDD ledger **CHECKPOINT 29**.

> **STATE AT COMPACTION #4 (2026-09-22, early) — supersedes #1–#3.** **113 items by checkbox count: 62 done ·
> 24 partly · 27 open.** **NOTHING PUSHED.** New owner ruling **M-SAD-AUTH** (fix the SAD local-socket `trust`
> hole + passwords in docker argv) — built on `obs-merge-g106`, delta review running. **Since #3:** telegram-bot
> round closed (swap to the shared seat; a pilot-chat-text leak via PTB's own CRITICAL line fixed); core A+B fix
> round done (`MintReceipt` type, one-transaction lock+catalog+DELETE, `Refusal` allowlist, NUL → 422, S3 headers
> gone) and merged the g44 branch; api G.53 round 5 clean of P1 but the CARRY SPEC needed corrections and one
> fix INSIDE `_root.py` (absent-primary family grouping) before any copy; api G.48 Cognito spans + `/test-cookie`
> no longer echoes credentials. **New tier-0 finds:** uvicorn's access line exports inbound `?token=` (core's
> invitation bearer secret) — the log-seat URL rule only knew `scheme://`; asyncio's "Task exception was never
> retrieved" body and the interpreter's excepthooks bypass the stdout seat; URLs with credentials reach STDOUT;
> G.117 entrypoints never call `setup_logging` (loguru default `diagnose=True`). A 429 session limit killed
> every lane once; all resumed. Resume from the SDD ledger **CHECKPOINT 28**.

> **STATE AT COMPACTION #3 (2026-09-21, night) — supersedes #1 and #2.** **113 items: 63 done · 20 partly ·
> 30 open** (new since #2: G.114 blinded tests, G.115 stdout sinks, G.116 URLs in log bodies). **NOTHING IS
> PUSHED ANYWHERE.** Two worktree lanes ran: `core-obsm-g44` (G.44 producer + keyset) is **MERGED into core
> `obs-merge` at `3f1a588`** (worktree + branch still to remove); `copilot-mro-obsm-g106` (G.113 + G.106 + the
> SAD password-log fix, 3 commits) is **under review, NOT merged**. **Headline finds since #2 (all tier 0):**
> the ROOT agent-turn span exported the Bedrock ARN + account id (G.102, fixed); a Postgres role password
> rode `db.statement` (G.113, confirmed at runtime, fixed); the SAD restore logged `PGPASSWORD` via
> `TimeoutExpired` text (fixed) and `migrate_tenancy_schema.py` PRINTS it every container run (routed);
> **stdout log sinks bypass every OTel seat** (G.115 — a real S3 key reached stdout JSON; utils fix
> committed `0211f9b`, unreviewed); **the G.112 log boundary itself read files named in untrusted body text**
> (review P1, fixed `flynapse-otel 1cdf318`, unreviewed); `/pdf/stream` mid-body failures escaped to uvicorn
> (fixed `bdaea7b`); **G.110 blinded ~30 span tests estate-wide** (G.114 — pattern: capture the live span in
> `on_start`). **Deploy order is now forced** (G.97): a utils release carrying `dependency_spans` must ship
> before core AND copilot-mro. **Possible non-telemetry security gap:** SAD's disposable Postgres may accept
> local-socket connections with no password (default `trust` + 0777 socket dir) — reviewer verifying.
> Resume from the SDD ledger **CHECKPOINT 27**.

- [x] ~~G.1 (TRUNCATED DUPLICATE HEADER — the live entry is the next line)~~ **Task R, widened: post-migration rescoping AND an estate-wide signal-coverage audit.** R as originally
- [x] G.1 **R.3 RE-DERIVED 2026-09-20 (late).** `docs/plans/observability-coverage-matrix.md` rewritten in
      place — 510 lines — against the **right trees**, with a stated counting rule so the next
      re-derivation is comparable rather than a new opinion.
      **New totals: 138 boundaries — 58 fully / 50 partly / 30 uninstrumented** (was 131 — 46/46/39).
      **Fallback-only external clients: 5 of 17, down from 8 of 16.**
      **The three "zero" sections are no longer zero.** Startup/shutdown **0 → 4 of 7** (the biggest delta —
      `api/telemetry/lifecycle_span.py` gives `api.lifecycle.{startup,shutdown}` plus 15 step spans and 2
      instruments, wired into the gateway **and** the worker, and `worker.py:415-417` now calls
      `shutdown_telemetry`, closing the unbounded-atexit gap). Background jobs **0 of 18 → 6 of 23**.
      Queues **0 → 1 of 4**: the consumer is fully covered, **but the producer link is declared and INERT** —
      `carried_traceparent` reads `__traceparent__` from `automation_runs.params` and **nothing writes it**,
      so **every consume span is still a root.** That is G.68, still owner-gated.
      **THE OLD MATRIX WAS INVERTED ON THE DASHBOARD SAMPLER.** It recorded that the dashboard *"drops 10%
      of root CLIENT spans"*. It drops **90%** (`sampling.ts:32,72-81`) — **the sentence read as the
      opposite of what the code does.**
      **AND IT WAS MEASURED ON THE WRONG DASHBOARD.** Its own HEAD table recorded `/home/aditya/Code/dashboard`
      @ `agent_sdk`, the **pre-merge** checkout. Section G is now re-measured on `dashboard-obsm` by a
      delegated sweep pinned to the absolute path, which confirmed start/end HEAD and dirty-count unchanged
      and that **none of the 38 dirty files was a telemetry file.**
      **A NEW AXIS: exception-text withholding**, per repo — api 5/5, core 1/1, utils 4/4, flynapse-otel 6/6,
      copilot-mro 21/26, **shift-optimizer 0/3 and telegram-bot 1/5.** See G.100.
      **Two briefed facts corrected:** the three copilot-mro GC/dispatcher jobs really are 0-openers, **but
      `sweep_expired_state` and `sweep_archived_memory` are registered builtin automations**
      (`api/automations/tasks.py:198-207`) so they run **inside** `automation.run` — partly covered, not
      dark. And `flynapse-otel` was **clean at `f6bd5c0` for the whole run**, not mid-edit as I briefed.
      **Refused to score, with the experiment named instead:** `utils/dynamodb_service.py` was measured four
      times and **moved every time** — 0 decorations at 23:10, 4 at 23:42, 17 at 23:43:33, with the method
      count itself going 18 → 20. **A number taken while another agent is writing the tree is not a
      measurement**, and the auditor applied that rule to itself rather than picking one.
      **A literal grep for `record_exception=False` misses `flynapse-otel` entirely**, because it splats a
      `_WITHHOLD` dict — it would have scored 0/6 instead of 6/6. **Any future sweep of this property must
      resolve the splat**, which is also the defect the flynapse-otel guard was found to have.
- [ ] G.97 **OWNER — bump `utils`' version before it is ever published.** Written into the plan 2026-09-21
      **DEPLOY-ORDER CONSTRAINT (core review A, 2026-09-21):** core-obsm `542d460` (G.48) imports `aws_span` / `finish_dependency_span`, which exist ONLY in unpublished utils-obsm. core's `pyproject.toml:43` points at `../utils`. **core cannot be deployed before a utils release that contains `dependency_spans`** — app assembly fails at import against any older utils. Phase H order: **flynapse-otel (≥ `49b0763`, released) → utils (bumped; path-depends on flynapse-otel) → core → api/copilot-mro.** **copilot-mro too** (`obs-merge-g106 24383dc8` G.106 imports `dependency_span`, its first obs-merge-only utils name).
      (it was cited by M-DRYRUN and carried in the ledger's owner queue, but never had an entry — **G.98 and
      G.99 were never allocated**). M-DRYRUN flipped `delete_files_by_keyword`'s `dry_run` default to `True`
      (`utils-obsm fffa470`) — a **behaviour change in a published package** — and the version is still
      `0.1.39`, the same number the old deleting default shipped under. **Two different behaviours under one
      version number.** Owner decides the new number; nothing is published in this project (Phase H).
- [~] G.100 **THE TWO SATELLITE REPOS WERE NEVER SWEPT, AND ONE HAS NO WITHHOLDING AT ALL.**
      **telegram-bot HALF DONE 2026-09-21 (`8ca41ea` spans, `fa37f7e` logs; `main`, 2 unpushed, review
      running).** All 5 openers withhold; `record_failure` writes type + bare status (it used to write a
      "redacted" copy of the message). Log census **110 → 11** (the 11 are body-free helper lines, pinned);
      `failure_fields` PORTED locally (`telegram_bot/failure.py`, utils named as source of truth — the bot
      cannot import `utils`). Suite 2287 → 2407 passed. 23 mutation proofs. **Its biggest finding is
      estate-wide → G.110.**
      **shift-optimizer HALF DONE 2026-09-21 (`ab33bf0` spans, `3f1543f` logs; `main`, 2 unpushed, review
      running).** All 3 openers (`optimizer.run/solve/persist`) go through one withholding `_span` helper;
      `RunSignals.failed` takes a type string, never the exception; 5 loguru lines carry `failure_fields`.
      Suite 756 → 852 passed (1 baseline skip). 4 guards (2 behavioural, 2 structural), 17 mutation proofs.
      `failure_fields` comes from the PRE-MERGE `../utils` path dependency — by design of that repo's
      pyproject; the reviewer is comparing the two copies. **NEW OWNER QUESTION:** `optimizer_runs.error =
      str(exc)` from `execute_run`'s broad handler is RETURNED by `GET /runs/{id}` and `/jobs/{id}/runs` —
      an unexpected psycopg/pydantic/KeyError puts internal text in a response body. Fix = keep the message
      for domain errors, write "internal error (Type)" otherwise; **an API contract change, so left for you.**
      **AUDIT 2026-09-21 — THE OWNER HAS RULED: M-SATELLITE-SCOPE, fix, don't publish** (§4a-bis; commits on
      each repo's `main` by named path, no bump, no publish, no push, no deploy). **`shift-optimizer` and
      `telegram-bot` implementers were launched 2026-09-21.** The "owed" question below is answered; the box
      stays open until both land.
      **telegram-bot review r5 fix batch DONE 2026-09-22 (`main`, unpushed, HEAD `47a08b7`):** P2-1/P2-2/P2-3 +
      P3-1..P3-4, one commit each (`e0da52b`..`47a08b7`); detector (flynapse-otel `0960c16`) clean 7, D2 `{exc}`
      +1; chain half held by the repo's own AST guard; G3 was a DEAD line (assigning `__cause__` sets
      `__suppress_context__` itself — deleted, property pinned; misdiagnosed by both the reviewer and the P2-3
      entry, both corrected in the repo plan); G14/G15 now KILLED; lane 2210 → 2229 (+300 DB skips); ruff clean,
      mypy clean on touched files (4 pre-existing errors in two untouched bot tests). **Detector limit for the
      flynapse-otel lane:** a raise of a leading-underscore class (`raise _WatchOver(f"…")`) is not read by
      `0960c16` (+0; renamed `WatchOver` +2) — undeclared. Owed: r6 restatement of TG5-08/13/14–19.
      On the new exception-text-withholding axis: **`shift-optimizer` 0 of 3** span openers withhold, and
      **`telegram-bot` 1 of 5.** Tonight's three sweep ports reached neither — they are outside the seven
      trees, as `flynapse-otel` was. **The owner extended scope to `flynapse-otel` on a fix-do-not-publish
      basis (M-OTEL-SCOPE); the same question is now owed for these two.** Note `telegram-bot` is a
      published, separately-deployed bot and `shift-optimizer` is a live product surface, so "latent" is
      **not** the right default assumption for either — the api lane proved tonight that whether an
      exception escapes into the span decides the tier, and that is per-repo.
      **shift-optimizer REVIEWED + FIXED 2026-09-21:** review MERGE-CLEAN (0 P0; its P1s were G.110 and the
      owner-gated `optimizer_runs.error`); all 4 guard P2s closed in `5f6f942` (suite 852 → 1035, 10 mutation
      proofs incl. the reviewer's `logger.catch` and conditional `for arg in exc.args` plants). Guard-only fix
      commit, mutation-proved → no second review. **Owner question (modularity):** the alias/resolution code
      is now duplicated between the two sweeps in this repo — and the same detector lineage exists in api,
      utils, core, copilot-mro and telegram-bot, where reviewers keep finding the SAME defeats repo by repo.
      A shared detector (e.g. a test-support module in `flynapse-otel`) would fix a defeat once.
      **M-SHIFT-RUNERROR DONE 2026-09-22 (`shift-optimizer fe0a07a`, `main`, unpushed):** `run_error_text` is the only failure writer of `optimizer_runs.error`. Exactly `RunExecutionError`/`RequirementError` keep their message; anything else stores `internal error (<Type>)`. There is NO read-time fallback: stored messages have no prefix, so legacy and new rows are byte-identical, and copilot-mro reads the column by its own SQL. Cleaning legacy rows is an owner data step. Lanes: unit 825 → 854, api 130 → 167 (smoke 7, db 60+1 skip, parity 18 unchanged). 16/16 mutants red.
      **Follow-ups 2026-09-22 (unpushed):**
      - `ed403b9`: `SolverInputError` is raised at the 16 solver/coverage input checks and joins the user-facing set. This fixes the fe0a07a regression that showed users `internal error (ValueError)`.
      - `1435728`: the duration-query and schedule-upload 400s return only `DurationQueryError`/`ScheduleCsvError` text. Any other `ValueError` gets a fixed sentence naming the request field.
      - `8bd4d66`: a raise-site taint guard over every kept type. The kept set is derived from the doors. It found a second `formula.py` flow (`Invalid syntax: {exc.msg}` → `FormulaError(errors[0])`), and both formula flows are named exemptions.
      - Lanes: unit 854 → 889, api 167 → 192 (smoke 7, db 60+1 skip, parity 18). Mutants: 10 + 9 + 14, all red.
      **Review r1 P3 batch 2026-09-22 (unpushed; `claims-shift-optimizer-r1.md`):**
      - `eb7c48a` (P3-1, SO-16): extreme numbers a user can author are refused as `SolverInputError`/`RequirementError` naming the field and the bound. This covers a cost factor that is past 1 000 or not finite, a rule value outside ±100 000 (inf and nan included), and a cohort minimum past the requirement ceiling. A day cap that cannot bind is clamped, and `inf` constraint strings count as unparseable.
      - `2a8e3de` (P3-2, SO-17): an upload the `csv` module refuses now gets the fixed 400 sentence, not a 500.
      - `0b4de00` (P3-3, SO-14): the raise-site guard's gap list is true.
        - Closed: a literal `getattr` construction; `sys.last_value`/`last_exc` read as attributes; the sanction narrowed to the builtin one-argument `type` and `isinstance`.
        - Declared: every remaining gap, P2-1..P2-3 included, sits in `DECLARED_GAPS`, each pinned as MISSED.
      - Lanes: unit 889 → 931, api 192 → 203 (measured at `2a8e3de`; `0b4de00` changes one unit test only). Smoke 7, db 60 + 1 skip, parity 18.
      - Mutants: 7 + 2 + 6, all red.
      - Still OPEN: SO-11..SO-13 (declared, not closed) and SO-15. Out of this lane: SO-18 (owner DML) and SO-19 (copilot-mro M-TOOL-ERRORS).
- [x] G.101 **R.4's ORPHAN ANALYSIS IS UNDER-COUNTED ON THE PRODUCER SIDE BY FIFTEEN NAMES.**
      **REFUTED 2026-09-21 BY THE RE-DERIVATION IT ORDERED — this item's premise was FALSE.** The old R.4
      **already listed all Document Hub families as orphans, and found them by reading code**, not the old
      inventory file. There are **14**, not 15: `legacy_families.py` declares 14 and
      `document_hub/operations.py` defines 14 name constants. **R.3's own prose said "fifteen" while listing
      fourteen, and "18 families" while listing seventeen** — and its warning was conditional on R.4 having
      used the old inventory, which it had not. **This is the inherited-number failure one generation on,
      inside the controller's own brief: an auditor's unverified count, copied into the plan as a finding.**
      **The producer side WAS short — by 19 names, none of them Document Hub:** 6 api gateway instruments
      (`automation.tick.duration`, `automation.queue.{depth,wait,claims}`, `api.lifecycle.duration`,
      `api.lifecycle.step.duration`); **2 HTTP body-size families the tracing library creates ON ITS OWN**
      under the new semconv (`http.server.request.body.size`, `http.server.response.body.size`) — **a census
      that reads only our code will always miss these**; and the 11 collector-derived browser metrics.
      **Families emitted: 57 → 76. Emitted-but-unconsumed under the old rule: 28 → 47.**
      **Also refuted: "core's sweep spans and their instruments" — core creates ZERO instruments;
      `automation.sweep.rows` is a span attribute.**
      **THE RULE SHOULD BE SPLIT, and the auditor proposed the split.** `browser.web_vital.value` scores as an
      orphan, yet it is now **the only aws path to web vitals not known to be broken** — *"a rule that scores
      that as a regression will get ignored."* Two tiers: **`on-call`** (a purpose stated in code **plus one
      runbook line** saying what question it answers) and **`orphan`** (no purpose stated anywhere — **the
      only number worth reporting as debt**). `legacy_families.py` already keeps these apart. **Under the
      split, orphans go 28 → 30, not 28 → 47.** The 17 new api and browser families are `on-call`
      **provisionally** — the label becomes real only once the runbook line is written, and **no family may
      enter `on-call` while it is only wired and never seen live.** The 2 body-size families are true
      orphans.
      **18 families can be removed TODAY:** the 16 legacy families no test asserts on, plus the 2 body-size
      families (drop with an SDK View). **Owner call.**
      **The four aws browser alarms are confirmed DEAD, not quiet** — `iac/alarms.tf:123,135` now say their
      patterns *"cannot match under ANY reading"*. The auditor's first draft called this closed because it had
      read only the fixed widget half; **it caught its own error checking its claims, and the document says
      so.**
      The re-derivation found the old matrix recorded *"metric? no"* for Document Hub processing and
      cleanup, when between them they emit **8 legacy families** — and that the estate carries **15 Document
      Hub families the old producer inventory omitted entirely.** R.4 (`observability-orphan-analysis.md`,
      28 orphaned families; "the inventory knows 14 while the estate emits 57") was computed against that
      short list, **so its producer side is wrong by fifteen names and its orphan count cannot be trusted
      until it is re-derived.** This is the same failure shape as the matrix itself: a derived document
      inheriting an unverified number from its source.
      specified is narrow — R.1 re-inventories the *agent runtime's* call sites after the LangGraph migration and
      R.2 approves the span/metric catalogue. That scope was written when the concern was "the migration moved
      the call sites". The useful question now is coverage, so R gains two parts:
      - R.3 **Coverage matrix** across `api`, `utils`, `core` and `copilot-mro` (and cheaply, the three satellite
        repos phase 8 instrumented). Enumerate every operational boundary — HTTP routes and mounted sub-apps,
        background jobs and schedulers, external clients (Postgres, S3, Weaviate, LLM providers, Redis), queues,
        startup and shutdown — and for each record whether it emits a span, a metric, and a trace-correlated
        structured log. The output is a gap table, not prose.
      - R.4 **Orphan analysis, both directions**: every emitted signal with no dashboard or alert consuming it,
        and every panel, alarm and alert rule whose signal nothing emits. Plus attribute and cardinality
        compliance against the registry's allow-list.
      Runs against the MERGED tree — auditing a tree we are about to change would measure the wrong thing.
- [x] G.2 **DONE — the last line landed; verified by the controller 2026-09-20.** `prometheus-client` is
      **gone from `copilot-mro-obsm/pyproject.toml`** (zero case-insensitive matches) and **gone from
      `poetry.lock`** (zero `name = "prometheus-client"` matches); the lock was **refreshed, not hand-merged**
      (17 lines removed across the pair). Uncommitted, so it rides with the 54 awaiting owner review.
      ORIGINAL ITEM FOLLOWS. **Half-satisfied — verified on the merged tree 2026-09-20, and what is left is one line.** As
      written this item asked for the Phase 0.5 / 0.6 residue, a permanent AST guard, and the deletion of the
      copilot-mro `/metrics` route and its dependency. Three of the four are done and an executor should not go
      hunting for them: **0.5a is done** (the memory and Weaviate logs carry bounded metadata, no raw query);
      **0.5b is done** — both "Enhanced chat request received" call sites in
      `copilot-mro/copilot_mro/app/api/chat_management.py` (≈ lines 1086 and 1449) log `message_chars`, not the
      raw query, which is what master 0.5b asked for under a different field name; the **`/metrics` route is
      already gone** from the merged tree; and the **AST guard is in the tree and is ours** (D.8 made their
      privacy guard honest enough to adopt, scoped to the four served-surface roots).
      **What remains is 0.6b alone:** the orphaned direct `prometheus-client` declaration at
      `copilot-mro/pyproject.toml` ≈ line 91, with **zero imports anywhere in the repo**. Remove it and refresh
      the lock — never hand-merge the lock.
- [ ] G.3 Phase 3.3 — **demoted from "build it" to "Task R decides".** The item was written when nothing was
      **RESEARCH 2026-09-21 (read-only, Opus) — SUPERSEDES THE TEXT BELOW, which is garbled (the CORRECTION
      block is pasted mid-sentence) and wrong in eleven places.** Verdict: **no live `gen_ai` span exists for
      ANY LangGraph model call.** All 14 graph bindings (and the Claude runtime's 5 lifecycle calls) do funnel
      through `ModelGateway.invoke` (`copilot-mro-obsm/.../agent_shared/model_gateway.py:253-409`) — **but the
      gateway opens no span**, so in Tempo each call is an anonymous urllib3/httpx `POST` (and for streamed
      calls that span ends at response headers, hiding generation time). The only `gen_ai` spans are
      **post-turn COPIES** projected from `llm_turn_content` (`telemetry.py:1658-1828`), dropped from Tempo
      (`base.yaml` `filter/drop_content_copies`) and sent only to Phoenix.
      **THE CONTROLLER'S 2026-09-21 CORRECTION WAS ITSELF WRONG — "LLM traces DO reach Phoenix" holds only
      under an untracked override.** Verified by the controller: `LLM_CONTENT_COPY_SAMPLE_RATE` defaults to
      **0.0** (`copilot_mro/app/config.py:1106-1107`) and no committed template, compose file or iac file sets
      it; the iac root never passes `phoenix_endpoint` (module default `""` = no Phoenix step). **So no AWS
      deployment exports to Phoenix, and "flowing" requires a local env override** (plausibly the colleague's
      own `.env`). Even then only copies arrive, only the first 16 calls per turn, only with tenant capture on.
      **One LangGraph-reachable call skips the gateway:** `transcribe_audio` (Azure STT via `utils/llm.py`
      `recorded_llm_call`) — no ledger row, no `gen_ai.client.*` metrics.
      **RECOMMENDATION (→ G.106): ONE hand-written INTERNAL span per attempt inside `ModelGateway.invoke`,
      plus the utils `recorded_llm_call` span (G.48, in flight). NO instrumentor** — botocore would duplicate
      the G.95 DynamoDB and S3 spans; openai-v2 would duplicate embeddings; anthropic reaches nothing in
      LangGraph; the LangChain callback instrumentor the spec chose carries none of the ledger identity and
      makes the §8 content flag live. **Facts also corrected:** there is NO lint banning
      anthropic/openai/langchain instrumentors — only botocore, in three DEPENDENCY pin tests (utils, api,
      flynapse-otel); **copilot-mro has no pin test and declares the gRPC exporter the others forbid** (G.108).
      The §8 check spec is written up as G.107.
      **CORRECTION 2026-09-21 — the controller told the owner this item was "never started", and that was
      too broad.** The owner's colleague reported that LLM traces flow to Arize, and **the config agrees**:
      `copilot-mro-obsm/deployment/otel/content-phoenix.yaml` exports to **Arize Phoenix** (the open-source
      product) via `otlphttp/phoenix`, with **one Phoenix project per tenant plus `internal`**
      (`groupbyattrs/phoenix_tenant`) and a `transform/phoenix_openinference` step translating our spans into
      OpenInference conventions. The `gen_ai.*` spans are **hand-written** in the agent runtime
      (`agent_shared/telemetry.py`, `pipeline.py`); `agent_evaluation/phoenix_adapter.py` is a consumer.
      **What is genuinely unbuilt is narrower**: auto-instrumenting the LLM **client libraries** — and that is
      partly deliberate, since `utils/observability/bootstrap.py:32` excludes botocore *"it would double the
      `gen_ai.*` families beside the ledger-driven ones"*. **Two caveats:** the Phoenix fragment is appended
      **only where `PHOENIX_ENDPOINT` is set**, and nothing here verifies traces are arriving in any live
      environment — **"flowing" is the colleague's runtime claim, not something this plan has observed.**
      instrumented; now every LangGraph model call goes through our own gateway, so the genai instrumentor
      would largely duplicate what we already emit — which is the same double-counting the spec bans the
      botocore instrumentor for. R must measure what in the lang runtime emits no span today and then choose
      between the instrumentor and a few hand-written node spans. Keep the lint test forbidding the
      botocore/anthropic/openai instrumentors, and the spec §8 content-flag CI check on the env templates,
      which no phase ever implemented and which goes live the moment any genai instrumentor does.
- [ ] G.4 Phase 3.4 Claude Code CLI built-in telemetry — missing on both sides.
      **IMPLEMENTATION 2026-09-22 — M-CLI-TELEMETRY BUILT, awaiting review (`copilot-mro-obsm-cli`,
      branch `obs-merge-cli` off `obs-merge` 6aef26e3; `a18635e9` env · `cb5d309d` panels · `4de21777`
      collector · review fixes `a32fd6fc` flag settings · `975890e6` error scoping · `7416d7a4` guard
      regex; NOTHING PUSHED; box left for the controller).** One stdlib-only module
      `copilot_mro/app/services/claude_cli_telemetry.py`; the orchestrator's one `ClaudeAgentOptions`
      passes `env=claude_cli_telemetry_env()` + `settings=claude_cli_telemetry_settings()`, the SAD
      runner lays the env LAST over its Bedrock env and passes the same settings (all four agents).
      **Env (verified against the bundled Claude Code 2.1.220 binary, SDK 0.2.128, and
      code.claude.com/docs/en/monitoring-usage):** `CLAUDE_CODE_ENABLE_TELEMETRY=1`,
      `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=http/protobuf`,
      `OTEL_LOGS_EXPORT_INTERVAL=1000`, `OTEL_METRICS_EXPORTER=none`, `OTEL_TRACES_EXPORTER=none`,
      `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=0`, `OTEL_SERVICE_NAME=claude-code`, and `"0"` for
      `OTEL_LOG_USER_PROMPTS` / `_ASSISTANT_RESPONSES` / `_TOOL_DETAILS` / `_TOOL_CONTENT` /
      `_RAW_API_BODIES` + `ENABLE_BETA_TRACING_DETAILED`. **Pinned, not unset, measured:** the SDK
      starts the CLI with `{**os.environ, …, **options.env}`, and the CLI then lays settings-file `env`
      (user → project → local → FLAG → policy) over that — hence the second carrier, `--settings`,
      which only managed policy outranks. `OTEL_LOG_ASSISTANT_RESPONSES` falls back to the prompts flag
      unless EXPLICITLY false. Endpoint inherited (`OTEL_EXPORTER_OTLP_ENDPOINT`, the config the rest of
      copilot-mro uses); records join our trace via the SDK-injected `TRACEPARENT`.
      **Defaults taken:** `OTEL_SDK_DISABLED=true` → CLI telemetry off, content still off; no
      tenant/user in `OTEL_RESOURCE_ATTRIBUTES` (constant dict, correlation by trace id); the spec's
      dev opt-in `OTEL_LOG_RAW_API_BODIES=file:<dir>` is overridden too (the ruling is absolute); SAD
      keeps the CLI's default setting sources (review suggested `[]`; not adopted — a behaviour change
      beyond the ruling, and the flag layer already outranks them).
      **Collector:** CLI records land on each overlay's `logs` pipeline, whose `attributes/strip_content`
      did NOT cover them. New `transform/claude_code_allowlist` (all four `logs` pipelines, first after
      `resourcedetection`): fail-closed keep-list on the CLI's own scope
      `com.anthropic.claude_code.events` (read from the binary); free-text `error`/`error_message` only
      on `api_error`/`api_retries_exhausted`; every value capped at 1024 chars. **Found and fixed:**
      `transform/genai_aliases`' log clause matched `"claude_code.api_request"` but the CLI writes
      `event.name` BARE, so it never fired; its metric half aliased series nothing can now produce —
      removed, and the processor left the four metrics pipelines. Panels: `fn-llm-agents` panel 10 + its
      CATALOGUE row and spec removed; `_emitted_series` no longer declares `claude_code.*`.
      **35 mutants across both rulings, all killed, each restored and md5-checked against HEAD.**
      **OWED (not buildable here):** (1) iac still names the retired series —
      `iac/dashboards/llm-agents.json.tftpl:7` (bullet whose prose is now false twice) and
      `iac/tests/unit/observability/test_validate_metric_vocabulary.py:100-101`; an iac follow-up drops
      both. (2) `deployment/otel/validate.sh` / the CI `otelcol-validate` job must load the four overlays
      in the real otelcol 0.160.0 before merge — the OTTL (`instrumentation_scope.name`,
      `delete_matching_keys … where`, `truncate_all`) is proved only in Python here (no docker).
      (3) a compose-stack smoke that posts a CLI-shaped record through the collector.
      **OWED (1), iac half, DONE 2026-09-21 (`iac 5f3380c`, not pushed):** the llm-agents markdown bullet now
      says there is no CLI panel and where per-call CLI detail arrives (logs, `service.name=claude-code`);
      `EXPECTED_SERIES` drops both names; the validator's DEFERRED note no longer credits copilot-mro's
      inventory with `claude_code.*`. Guard `tests/unit/observability/test_cli_metrics_stay_off.py`: no
      `.tf`/`.tfvars`/`.tftpl` in any root or module names `claude_code[._]…`, text panels included (on this
      surface a text panel IS the PromQL surface), with floors, named witnesses and a planted-spelling
      self-test. 243 → 246; 6 mutants red, one of them through the extractor limb (`EXPECTED_SERIES`).
      **iac review r3 fixes, 2026-09-22, not pushed:** `d86b378` the CLI bullet now says its records are
      `DARK until copilot-mro obs-merge-cli merges into copilot-mro obs-merge` (the producer, `cb5d309d`, is only
      on that branch), pinned to the validator's state grammar — **flip it to WIRED in the commit after that
      merge**; `9828e17` the pattern is `claude[._]code[._]…` with no leading boundary (the reviewer's C2,
      `claude.code.*`, red).
      **REVIEW r1 FIXES 2026-09-22 (`7416d7a4..f1100629`, 11 commits, worktree clean, NOT merged; review r2
      launched).** P1-1 `a76df7b8`: the CLI's `error`/`error_message` is DROPPED on every event; a failure
      survives as `status_code`, `attempt` and the CLI's regex-bounded class fields `error_type`/`error_name`/
      `error_code`, and every kept value is capped at 128 characters. P2-3 `a0333a38`: the keep-list is pinned
      exactly, and both conditions match `service.name == "claude-code"` OR the CLI's logger scope. P1-2 `69a9b3a5`:
      the test pins what `query()` actually receives. P2-1 `c0ae7f54`: the logs endpoint, OTLP headers and resource
      attributes are pinned from this process's own resolution; a header value goes only in `options.env`, never in
      the `--settings` argv. `5ecc7de0`: the CLI's flush, shutdown and export timeouts are each 1000 ms. P2-2
      `b181a81e`: named CHECK `llm_turn_content_content_present_check (content IS NOT NULL)`, which
      `converge_named_checks` adds in the owner's Phase H run. P3-4 `717573bc`: the owner's column-drop SQL locks
      ACCESS EXCLUSIVE and refuses unless that CHECK exists, so the ORDER IS ENFORCED: code → migration → SQL.
      `43962c12`: a collector drop for `claude_code` metrics in all four metrics pipelines. `d4bf083a`: the
      aliases write the gateway's own `gen_ai.usage.cache_read.input_tokens`/`cache_write.input_tokens`.
      **P3-6: land `a18635e9..f1100629` as ONE unit — never cherry-pick the first commit.** **Merge:** one
      conflict, in `test_phase1c_nonagent_scope_guard.py` (`MRO_POST_MERGE_PRODUCTION_PATHS`); resolve by union
      and commit the resolution alone. **Merge-order dependency:** iac's CLI board bullet says the logs "arrive"
      under `service.name=claude-code`, which is true only once this branch merges (iac review r3 P3-7).
      **Still owed:** real otelcol 0.160.0 validation of the four overlays (incl. the new OTTL); running the owner
      SQL on a scratch DB; the iac board/vocabulary test (r1 P3-3).
      **REVIEW r2 2026-09-22: MERGE-CLEAN 0/0/2/4** (`claims-copilot-mro-cli-r2.md`). A trial merge onto obs-merge
      `ac7cda74` has one conflict (the union) and no semantic conflicts; the lanes are green apart from known
      environmental reds. **P2-1: the "kept category" does not exist** — the CLI's `api_error` and
      `api_retries_exhausted` records carry no `error_type`/`error_name`/`error_code` (binary-witnessed); a Bedrock
      403 exports `status_code=403` only, and the test injects fields the CLI never writes there. **CONTROLLER
      CALL: option (a)** — `status_code` IS the whole category (its absence already says "no HTTP status"); correct
      the four texts and the fixture, and add no collector-derived field. **P2-2:** the P1-2 guard pins the options
      object, not the argv; `extra_args={"settings": …}` would add a second `--settings`, and the last one wins →
      feed the recorded options to the real `_build_command()` and require exactly one `--settings` and no
      `--managed-settings`. P3: header precedence unproven (R03/R04); the owner SQL read-back is `LIKE` with no
      `convalidated` check → require the exact `CHECK ((content IS NOT NULL))` and `convalidated`; stale prose
      ("code → migration → SQL" — only migration → SQL is enforced; "~70 chars" is not true of `error_name`).
      **REVIEW r2 FIXES 2026-09-22 (`7880bc44..b5cf1524` after `10ef633a`/`9d6be4b6`/`7880bc44`) — MERGED into
      `obs-merge` as `557a178f` (`--no-ff`, parents `735f8213` + `b5cf1524`; the one predicted conflict, the scope
      guard's `MRO_POST_MERGE_PRODUCTION_PATHS`, resolved as the union and nothing else).** P2-1 `10ef633a` (option
      (a): `status_code` is the whole category, pinned by equality). P2-2 `9d6be4b6` (both runners' guards drive the
      real `_build_command()`: one `--settings`, no `--managed-settings`). P3-1 `7880bc44` (a headers decoy case; R03/R04
      red). P3-2 `a532a23c` + `0849309a`: the owner SQL's precondition AND read-back require `convalidated AND
      pg_get_constraintdef(oid) = 'CHECK ((content IS NOT NULL))'`, and `converge_named_checks` keeps a same-named CHECK
      only when validated and printed identically to the declaration — printed by the same database off a temp `LIKE`
      probe (`Live.declared_checks_as_printed`); otherwise drop + re-add. P3-3 `42b9c1b2`: `OTEL_EXPORTER_OTLP_LOGS_TIMEOUT`
      is pinned beside the generic name (the CLI's exporter reads the signal-specific name first) and the module states
      the trade-off — **a flush or shutdown that hits its 1 s bound drops that turn's queued records silently; the CLI
      reports the loss only to its own debug log, which nothing reads.** P3-4 `b5cf1524`: prose — the env test's point 4,
      the spill test's point 3, the "~70 chars" docstring and the SQL header; and this note corrects the r1 line above:
      **only migration → SQL is enforced** (the script sees the CHECK, not which code is deployed; code-first stays an
      operator precondition). Mutants: 7 run, 7 killed after one fix-forward (a NOT VALID fixture spelled the Postgres
      way let the `convalidated` term survive; `0849309a`). The `tests/db/tenancy` conformance lane carries 3 reds that
      read the live `copilot_mro_test` shape (nullable `data_discovery_jobs` counts; `llm_turn_content` absent) in both
      trees — environmental, not this change. Worktree and branch left for the controller; iac's "DARK → WIRED" flip is
      the other lane's.
      **iac r4 batch, 2026-09-22, not pushed:** P3-F `0963a3e`: the CLI bullet's pin asserts the claim through check 6's own reader, so a backticked `DARK until` no longer passes (D3b red); `a04b9c0`: the bullet flips to `WIRED 2026-09-22, retrieval unproved`, naming `claude_cli_telemetry.py` on obs-merge `557a178f` and both call sites. **Correction (r4 P3-H):** the subjects of `d86b378` and `9828e17` say P3-6 / P3-7 for r3's P3-7 / P3-8, and `d86b378`'s "so check 6 reads it" held only from `0963a3e` on.
- [x] G.5 **copilot-mro HALF DONE 2026-09-20 (`copilot-mro-obsm c80c686d` + 2 uncommitted production files); the
      **AUDIT 2026-09-20 — VERIFIED DONE, BOTH HALVES.** Writer present in
      `copilot_mro/app/db/chat_history/blocks.py` (savepoint docstring ~`:553-568`); the core half is G.25,
      already `[x]`. Closed by `copilot-mro-obsm c80c686d` + `core-obsm 1d6adca`/`bdea4ba`.
      `core` half is owed as G.25.** The writer sits inside `save_block`'s `rowcount == 1` branch, on the same
      cursor, before the commit, wrapped in `SAVEPOINT chat_turn_facts` per M-SAVEPOINT. **Projection parity is
      literal, not argued:** a body-level diff against the backfill shows exactly ONE difference — a constant
      name the drift pin already asserts equal — and `FACTS_UPSERT_SQL` is **string-identical** to the
      backfill's. Landed at `FACTS_VERSION = 1`; Q1 untouched. **The `department` equality claim is verified and
      is STRONGER than the spec stated** — the lock gate is necessary but not sufficient; the second fact is that
      **`chats.department` is never updated by any RUNTIME code path — CORRECTED 2026-09-20, the original
      wording was FALSE as literally stated.** Two estate-resident statements DO update it, both via a
      **dynamically composed `INSERT … ON CONFLICT … DO UPDATE SET`** that a grep for `UPDATE chats` can
      never see — `scripts/seed_test_estate.py` (builder at `:81-97`, chats row at `:388`) and
      `tests/fixtures/tenancy/second_tenant.py`. **I verified the builder myself:** it emits
      `DO UPDATE SET … department = EXCLUDED.department` for every non-key column. Both write a
      **constant**, so no divergence exists today — but they are **re-runnable**, and editing that constant
      between two seed runs would move `chats.department` while already-projected facts rows kept the old
      value: precisely the divergence the docstring says cannot happen. Narrowed claim stands** (three `UPDATE chats` sites across four repos, none
      touching it, and no hard `DELETE FROM chats`). Without that, equality would hold at save time and the
      backfill could later disagree. **Exactly nine panels confirmed** (9 of 46), one of them half-dark.
      Five mutation proofs and **two vacuity attacks that both fired** — one caught an equality check that stayed
      green while comparing near-empty dicts. ORIGINAL ITEM FOLLOWS. Phase 3.7 the sole `chat_turn_facts` writer on the block-save path, same transaction, idempotent at
      the backfill's facts version — unblocked by Gate M, and the reason three panel families are empty.
- [~] G.6 **PARTLY DONE — three of the named instruments are IN THE TREE, verified by the controller
      **AUDIT 2026-09-21:** **M-TOKENUSAGE is DONE** — `copilot-mro-obsm 04ad6284`, `gen_ai.client.token.usage`
      is a Histogram with explicit buckets (`agent_shared/telemetry.py:1409-1419`), so the "still owed" clause
      below is stale for it. **Only the tool-metric binding remains** — tenant and department on
      `agent.tool.calls`/`.attempts`, which `agent_pipeline.py:264,693` record on the UNSCOPED telemetry —
      **gated on G.17.** **Commit state, corrected at source:** not all three instruments are working-tree
      only. `agent.ledger.write_failures` is (instrument `:1434`, emit via `usage_ledger.py:105`; absent at
      HEAD). The two `agent.subagent.*` instruments are **at HEAD since the colleague's `54a01f39`, but with
      zero callers there** — their only call site (`subagent_runs.py` `observe_subagent_runs`, bound in
      `lang_agent/backend.py`) is working-tree only.
      2026-09-20 and previously reported as merely "in flight".** `agent.ledger.write_failures`
      (`copilot-mro-obsm/copilot_mro/app/services/agent_shared/telemetry.py:1396`, registry form `:1462`,
      emitted `:1946`), `agent.subagent.calls` (`:1387`, `:1453`) and `agent.subagent.duration_seconds`
      (`:1388`, `:1457`) all exist. **Uncommitted**, and R.4 excluded all three from its orphan verdict for
      that reason. **Still owed:** tenant and department on tool metrics — which is blocked on **G.17**, the
      open owner ruling on the tenant-scoped allow-list — and **M-TOKENUSAGE**. ORIGINAL ITEM FOLLOWS.
      `agent.ledger.write_failures`; subagent span and metric call sites; tenant and department on tool
      metrics; M-TOKENUSAGE.
      **IMPLEMENTATION NOTE (review r7b P2-2, `copilot-mro-obsm-r7b 3ec66117`, 2026-09-21):** the
      subagent, tool and ledger call sites are now DRIVEN, not argued: `run_query` offline with one
      `Task` dispatch books one `agent.subagent.calls` point through the real `record_subagent`
      (`tests/agent_sdk/core/test_agent_sdk_subagent_metric.py`); a lang `manual-research` branch
      and a `manual_retrieve` call book theirs through the composed wrapper
      (`tests/unit/lang_agent/test_lang_subagent_metric.py`); both runtime builders bind the SAME
      telemetry's recorders (`test_composition_root.py`); `record_turn_usage` failed/refused/unbound
      and `record_budget_refusal` unbound each book `agent.ledger.write_failures`. The inventory's
      `_call_sites` now counts `obj.method(...)` CALLS only; the two callback-wired recorders
      (`record_subagent`, `record_tool_operation`) are `CALLBACK_WIRED` — both builders must bind
      them and the named behavioural tests must read the series back. G6M1–M9 all red (G6M9, both
      runtimes at once, by 2 tests). The tool-metric tenant/department binding (G.17) is untouched.
- [~] G.7 **SPLIT BY THE IMPLEMENTER — the two halves are in two different trees and one was already done.**
      **AUDIT 2026-09-21:** **(a) and (b) are DONE** (`utils-obsm 7f1817f`; the utils production half it
      depended on landed in `6848ef7`). **Only (c) remains, and it is an OWNER CHOICE, not a build:** the S3
      spill never happens — `copilot-mro-obsm llm_content_capture.py:1459` hard-codes `"content_s3_key": None`
      while the either/or CHECK is pre-wired (`postgres_table_definitions_modules/llm_turn_content.py:136`).
      **Either build the spill, or accept truncation-in-place and drop the column + CHECK.**
      2026-09-20 (`utils-obsm 7f1817f`, test file only, zero production edits).
      **(a) The redaction half is ALREADY SATISFIED in `utils`, in a better shape than the item asked for.**
      `utils/observability/failure.py` **never reads the exception message at all** — it takes `error_type`,
      `format_tb` frames, a shape-checked `aws_error_code`, a `sqlstate` and a class-gated `pg_primary`.
      `response["Error"]["Message"]`, the field that carries the ARN, is never read, and a pre-existing test
      pins that. **A blanket regex would have been strictly worse than what exists.** Live proof captured
      incidentally: a real `AccessDenied` logs `aws_error_code` only — no ARN, no account id.
      **(b) The REAL gap was the OTHER pipe.** `start_as_current_span` defaults to `record_exception=True` +
      `set_status_on_exception=True`, so **on the trace pipe the leak is the DEFAULT**. The log rule was swept
      estate-wide; the span rule was enforced only by three per-operation tests, so a fourth factory would leak
      on its first export. Built `tests/unit/observability/test_utils_spans_withhold_exception_text.py` (new,
      10 tests): a discovered-subject AST sweep banning the whole family — an opener missing either literal
      `False`, `span.record_exception(...)`, a `Status(...)`/`set_status(...)` carrying a description, and a
      caught exception **or a transitive alias of one** reaching `set_attribute`/`add_event`/`update_name`.
      Floor **and** named witnesses, per the lesson that a count cannot say WHICH files were read.
      **7 mutation proofs, each grep-confirmed and md5-verified on restore**, including a decoy (rebinding the
      opener to a local alias) that left the sweep vacuously clean and every behavioural test green — **only
      the witness clause caught it**. Honest negative that changed the build: dropping a keyword **failed the
      sweep but PASSED the behavioural door test**, because every door ends in a bare `except Exception` and
      nothing escapes the context manager — so a direct-drive test was added, the only way to prove the
      keywords behaviourally. Lane reconciled exactly: 1425 → **1433 passed + 2 xfailed**, delta = the 10 new
      tests, `rootdir: /home/aditya/Code/utils-obsm` on every invocation.
      **(c) The S3-spill half is UNBUILT and belongs to `copilot-mro`** — `llm_content_capture.py:1459` hard-codes
      `"content_s3_key": None` while `llm_turn_content.py:136` carries a `CHECK ((content IS NULL) <> (content_s3_key
      IS NULL))` and `scripts/purge_llm_turn_content.py:40` already does `RETURNING content_s3_key`. **The
      either/or column exists and is never taken; the purge is pre-wired for a spill that never happens.** A
      pre-existing test **asserts the `None`**, i.e. pins the defect. **Plan correction:** oversize bodies are
      **truncated in place**, not "dropped" — `_fit_snapshot_to_max_bytes` bounds them and sets `truncated=True`,
      so `sha256`/`content_bytes` DO describe the stored truncated bytes. The defect is "the tail is discarded
      rather than spilled". **Still owed: the copilot-mro spill.**
      **IMPLEMENTATION 2026-09-22 — M-CAPTURE-TRUNCATE BUILT, awaiting review (`copilot-mro-obsm-cli`
      `4c02a10e` + `258a5d64` lint + review fix `5333e3cf`; NOTHING PUSHED, NO DDL RUN; box left for the
      controller).** Deleted: `content_s3_key` and both CHECKs (`llm_turn_content_storage_check`,
      `llm_turn_content_s3_tenant_prefix_check`) from the registry definition; the column from the DAO's
      `INSERT_COLUMNS` and the writer's row; the purge's `RETURNING`, `reap_objects` and
      `_object_deleter` (it returns the deleted row count; the debt register moved its two reaper sites
      to `REPAIRED`). Truncation kept and pinned: `LLM_CONTENT_CAPTURE_MAX_BYTES` default 262_144 and a
      >256 KB turn stored INLINE with `truncated=true`. **`content` stays declared NULLABLE** (review P1
      reversed the first cut's NOT NULL: nothing converges a pre-existing column, so the conformance
      gate's `declared_columns_are_not_null` would have reported every migrated/live DB). **No drop
      mechanism exists** (`migrate_tenancy_schema.py` never drops, by design): the owner-run DDL is
      `copilot-mro/scripts/drop_llm_turn_content_spill.sql` (core's `drop_comments_tenants_fk.sql`
      shape: superuser, one transaction, `lock_timeout`, pinned `search_path`, `row_security=off` so the
      no-spilled-rows refusal cannot read an RLS-filtered zero, `DROP COLUMN` takes both CHECKs,
      read-back by predicate, idempotent). **Order: CODE FIRST, then the SQL** (the old writer's INSERT
      names the column). **Boot tolerance measured:** no boot/worker declared-vs-live column check
      exists (the app has none; `utils.rls_boot_check` reads tenancy columns only); the migration's real
      `add_columns` / `converge_named_checks` / `_report_check_counts` /
      `_report_declared_not_null_left_nullable`, driven over a fake pre-ruling catalog, write nothing,
      drop nothing, note the column "left in place" and raise no finding — pinned. **OWED:** executing
      the SQL against a scratch DB in `tests/db` (pre-ruling shape twice, a spilled row, a non-superuser
      FORCE-RLS owner) — only its shape is pinned here; tightening `content` to NOT NULL, if wanted, is a
      paired registry + SQL change for Phase H.
- [x] G.84 **NEW, from G.7's sibling-tree sweep — the estate's widest instance of the same leak.**
      **CLOSED 2026-09-20 (`api-obsm bbbf0fa`, tests only; 3 new production edits uncommitted).**
      **THE LEAK WAS LIVE, AND EXPORT PROVED IT — not reasoning.** `_SpanExceptionMiddleware` relied on no
      context-manager default: it called `span.record_exception(exc)` and set
      `description=f"{type(exc).__name__}: {exc}"` **explicitly, on the SERVER span, which every request
      has.** The implementer reverted the repair, drove one ordinary request and read the export:
      **`arn:aws:s3:::flynapse-copilot/akasa/mro/AIPC/processed/manual.pdf` was on the span**, with
      `exception.message` and `exception.stacktrace`.
      **This is the tier-deciding difference from `utils`.** There, every door ends in a bare
      `except Exception` inside the `with`, so dropping a keyword fails the sweep but PASSES the door test.
      Here a FastAPI route's unhandled exception genuinely propagates out of the router, through
      `ExceptionMiddleware`, into the shim — **so the keywords are load-bearing on today's call graph, not
      defence-in-depth.** M1 (drop one keyword on the lifecycle family) failed the sweep **and** the
      behavioural test. Latent would have meant the behavioural test stayed green. It went red.
      **The briefed 11 were VERIFIED by running the detector against pre-repair sources, not hand-counted:**
      10 hits across `http_server`/`lifecycle_span`/`run_span`/`queue_telemetry` plus `executor.py:1077` =
      **exactly 11, zero false positives.** Every claimed line exact except `http_server`, where the shape
      is at `:137`+`:139`, not spread over `137-141`.
      **A finding that changed the repair, and it is upstream's fault, not ours:** **`error.type` on an HTTP
      SERVER span is NOT free** — `opentelemetry.instrumentation._semconv:662,684` writes the response
      status into it (`"500"`) on **both the span and the `http.server.request.duration` sample**, *after*
      the shim runs. The first repair used it and was **silently overwritten** (measured:
      `assert '500' == 'ClientError'`). The class now goes under **`exception.type`** on server spans, while
      INTERNAL/CONSUMER spans keep `error.type`, matching `utils`. Both pinned so a tidy-up cannot move it.
      **The alias-rule triage came out the OPPOSITE way to the sibling's advice, with reasons:** the
      implementer reproduced the over-flag in its own harness and ruled **flag it deliberately, do not
      narrow** — `SystemExit.code` is whatever was passed to `sys.exit`, routinely a sentence, and every
      neighbouring attribute (`args`, `detail`, `pgerror`, `diag.message_detail`) is the message outright;
      a rule permitting attribute reads would have to decide which attribute NAMES are bounded, **which is
      the undecidable guard this estate already refused.** It flags nothing in `flynapse_api`, so there was
      no false positive in the guarded tree to narrow for. **Recorded as an executable ruling, not a
      sentence.**
      **6 mutations including a decoy** (rebinding the opener to a local alias left the sweep clean and
      every behavioural test green — **only the named-witness clause fired**) and a discovery probe
      (planting a leak in a file named by no witness set — the sweep found it, so discovery is non-vacuous).
      All six production targets md5-verified on restore.
      **Residual, deliberately left:** `executor.py:~1071` leaks on the **log** pipe one line above the span
      site repaired here — but it is **already recorded debt** in the existing log sweep's `_RECORDED_DEBT`,
      so it was left intact rather than **silently re-scoping another implementer's deferral.**
      The implementer ran its detector against every tree and hand-triaged the hits: `api-obsm` 11 real / 0 false,
      `flynapse-otel` 10 real / 0 false, `copilot-mro-obsm` 12 real / 10 false, `core-obsm` 0 openers.
      **Highest exposure: `api-obsm/flynapse_api/telemetry/http_server.py:137-141`** — on the ASGI **server** span
      it does `span.record_exception(exc)` **and** `description=f"{type(exc).__name__}: {exc}"`, so **every
      unhandled request exception puts its full provider message — ARNs, account ids, tenant keys — on that
      request's span.** Also `automations/executor.py:1077` plus four openers on the defaults
      (`lifecycle_span.py:98,155`, `queue_telemetry.py:280`, `run_span.py:44`). `copilot-mro-obsm` has six
      openers on the defaults (`agent_shared/telemetry.py:1508,1731,1761,1891,1899`,
      `loop_observability.py:248`). **False positives declared, not hidden:** the copilot-mro parser hits are a
      benign `except SystemExit as error: code = error.code` shape (the transitive-alias rule over-flags a
      derived scalar) and `telemetry.py:1739,1768` pass a bounded `error_type`, not a message — **anyone porting
      the sweep must triage the alias rule first.**
- [x] G.85 **NEW — `flynapse-otel` re-exports a leaking span helper, and it was proved with a real payload.**
      **BOTH CLOSED 2026-09-21 (`flynapse-otel af40bbe`, 2 commits, UNPUSHED, version still `0.1.1`, no
      bump, no publish — per ruling M-OTEL-SCOPE).** Repo state audited first: branch `main`, HEAD was
      `1cafda2`, clean, single worktree. Baseline **191 passed → 242 passed**, delta reconciled exactly.
      **`end_span` really does have ZERO production callers estate-wide** — confirmed across all eleven
      repos, only the definition, this repo's tests and the `utils-obsm` xfail. So it was a **loaded public
      surface, not a live leak**, and severity was assigned accordingly rather than inflated.
      **THE TWO KEYWORDS ALONE WOULD HAVE BEEN A NEW SILENT DEFECT — this is the transferable lesson.**
      `set_status_on_exception=False` suppresses the status **CODE**, not merely its description, so a naive
      repair **drops every failed span out of any `status = error && error.type != ""` query.** The repair
      answers an escape with the bounded pair `utils`' own factories use — `error.type` from
      `type(exc).__name__` plus a **bare** `Status(StatusCode.ERROR)`. Error signal kept, message dropped,
      no redaction regex. **All four openers fixed, not the two the xfails named.**
      **The latch question was settled by evidence, not reasoning.** The briefed claim was strengthened: the
      latch is closed not only by `OpenTelemetryMiddleware.__init__` but also by `BaseInstrumentor.instrument()`
      — **the first of EITHER decides the process.** And the decisive fact for "is a disabled process
      exempt?": `api-obsm/flynapse_api/telemetry/http_server.py:298`'s `instrument_gateway` has **no
      `OTEL_SDK_DISABLED` check**, so a disabled process still constructs the middleware and **still
      latches.** Hence the `setdefault` moved above the early return and `_initialize()` is forced there.
      Reaching into the underscore-prefixed upstream symbol was accepted with reasons (a pinned main
      dependency, the file already reaches for upstream globals) and **pinned by a test asserting the
      attributes exist, so a version bump fails loudly instead of silently.**
      **The reviewer's splat defeat was verified BEFORE acting, and one of the two reported defeats was
      wrong.** With the original clause, `**dict(_WITHHOLD, record_exception=True)`,
      `**(_WITHHOLD | {...})`, `**span_kwargs` and `**{...: flag}` **all passed clean** — the first two
      **re-enabling the exact leak while never touching `_WITHHOLD`.** Fixed: the splat must be a Name
      resolving to a module-level dict literal, which is what the comment already promised. A new
      `_opener_census.py` now **ties the structural and behavioural halves together**, because each had been
      assuming the other covered a new opener and a planted fifth escaped both.
      **Four more reviewer-found defects fixed:** `start_span`'s withholding had zero behavioural cover; a
      docstring claimed `trace.use_span()` honours stored flags — **it does not**, it carries its own
      `record_exception=True` (`opentelemetry/trace/__init__.py:588-589`); `contextlib.contextmanager`
      silently dropped upstream's async-decorator support; and `_reset_for_tests` did not reopen the latch
      that `bootstrap` now closes.
      **Deferred WITH its reason recorded in the guard's own allowlist:** `OTEL_PROPAGATORS` +
      `set_global_textmap` are **also** below the disabled return — latent only because **nothing in the
      estate calls `baggage.set_baggage`** (zero hits across eleven repos).
      **Briefed facts refuted:** `tracing.py` has **four** opener call sites, not six (two cited lines are
      `async def start_span` **definitions**); the api-obsm fixture is `_no_process_wide_telemetry_shutdown`,
      not `shutdown_telemetry` (that name appears only in its docstring) **and it is a different species** —
      an irreversible teardown, not a read-once latch. Line numbers corrected: the disabled return is
      `:152-162` not `:151-161`; the propagator block `:173-183` not `:173-180`.
      **The xfail sequencing resolved itself:** the `utils-obsm` lane deleted both markers and converted
      them to ordinary regression tests citing `f6bd5c0`, **strengthened to assert the ERROR signal is
      exported BEFORE asserting the message is absent.** That tree's observability suite: **292 passed, 0
      failed.**
- [~] G.102 **A LIVE exception-message leak in `copilot-mro`, which the flynapse-otel repair deliberately
      **FIXED on `obs-merge` (`copilot-mro-obsm c401fb18`, reviewed 2026-09-22):** the real leak was `turn_span`, the ROOT span of every agent turn (Bedrock ARN + account id); withholding + `error.type` + bare ERROR, 3/3 mutants. Residual sweep gaps (9 shapes, `use_span` at `telemetry.py:1788`) in the copilot-mro lane.
      does NOT cover.** `SdkTracingService.tracer` returns the **raw** tracer by design, so the withholding
      added to the helper functions never reaches anything opened through it. Three sites open that way with
      **no keywords at all**: `chat_management.py:402` and `:1324`, and `loop_observability.py:215`.
      **Wrapping `.tracer` was correctly refused** — it is a documented compatibility surface — so the fix
      belongs to copilot-mro's own sweep. **And this is the shape that sweep structurally may not see**: it
      bans openers missing the keywords, but a raw tracer obtained from a service accessor may not be
      recognised as an opener at all. Routed to the copilot-mro lane with the instruction to prove
      escape-vs-latent by export, as the api lane did, rather than reasoning about it.
      `utils.observability.span` resolves to `flynapse_otel/tracing.py`, which opens on OTel defaults at
      `:35,82,107,112`, and `SdkTracingService.end_span` (`:94-95`) does `record_exception(error)` **and**
      `set_status(Status(ERROR, str(error)))` — **the message twice**. Captured export text carries
      `'exception.message': '…arn:aws:sts::123456789012:assumed-role/…'` plus the same string as the span
      **status description**. Held in `utils-obsm` as two `xfail(strict=True)` tests, so they **XPASS-fail the
      moment flynapse-otel is repaired**; `--runxfail` shows the ARN. **Tier 0 but latent: `end_span` has ZERO
      production callers estate-wide** (only flynapse-otel's own test), so this is a loaded public surface, not
      a live leak. **Owner ruling owed** — `flynapse-otel` is outside the seven trees.
      **Also noted, flagged not claimed:** `utils/s3_service.py:915` raises
      `ValueError(f"…: {s3_url}")` — the whole URL, including a presigned `X-Amz-Signature`, as an **exception
      message**, which no log sweep sees. `copilot-mro` calls `parse_s3_url` at `_figure_core.py:232` and
      `mro_document_service.py:823`, and copilot-mro has six span openers on the defaults — but **reachability
      into a recording span is NOT proven.**
      **The existing sibling span test could not have caught any of this:** its `_all_exported_text` renders log
      bodies, log attributes, span attributes and span events — **not `status.description`**, which is exactly
      where `set_status_on_exception=True` writes.
- [x] G.8 **AUDIT 2026-09-21: CLOSED HERE, MOVED.** The scope is owned by
      `docs/plans/agent-evaluation-completion.md`, which says so itself (§2.3 row 8: *"G.8 was 7.3–7.6
      renumbered"*) and inherits all six Phase 7 items: **7.3 → its Phase 2, 7.4 → Phase 6, 7.5 → Phase 7,
      7.6 → Phase 8.** Dispatch from that plan, never from this entry. ORIGINAL ITEM FOLLOWS.
      Phase 7.3 – 7.6: the `eval_results` table keyed by ledger profile + registry revision, the harness
      dataset/experiment push, the per-tenant quality report, and residency enforcement in overlay validation.
- [x] ~~G.9 Schedule the `chat_turn_facts` backfill.~~ **DROPPED by the owner 2026-09-19 — no backfill needed.**
      **AUDIT 2026-09-20 — THE BOX WAS AN ARTEFACT.** The owner DROPPED this item; the text is struck
      through and carried an unchecked box anyway. Ticked so it stops reading as pending work.
      The online writer (G.5) becomes the sole populator; `core/scripts/backfill_chat_turn_facts.py` stays
      available for a one-off reconciliation but is scheduled nowhere. Panels reading facts show data from the
      writer's landing forward, not historically.
- [x] G.10 **AUDIT 2026-09-21: CLOSED AS PART OF G.28.** The `utils` half is done — guard `utils-obsm
      21fc319`, production `6848ef7` (`weaviate_service.py`) — and **what remains is exactly G.28**, the
      copilot-mro tenancy door. One live entry, per this phase's hygiene rule. ORIGINAL ITEM FOLLOWS.
      **NOT CLOSABLE ON THIS WORK — see G.28. The `utils` class half is done and guarded (`utils-obsm 21fc319`), but the door C1.6 actually named is untouched.** 2026-09-20 (`utils-obsm 431aefc` + an uncommitted 299/48 diff); the DIMENSIONS
      half is NOT fully closed and two residuals are now G.23.** The span work lives in `utils`, not
      copilot-mro — a correction from the G-APP pass. **Nineteen untraced doors, not six**: one shared factory
      `_weaviate_span` (`weaviate_service.py:71`, name `f"weaviate.{operation}"` at `:108`) now covers **20
      operations**, with `hybrid_search` — previously the only traced one — re-homed onto it. **Seven of the
      nineteen were named in no document at all**, and **three artefacts disagree with the docstring's own
      content**: it names five methods plus "the delete and schema paths", while `claims-C1-utils-B1-core.md:44`
      and this plan's C1.6 line both said "six". Outcome vocabulary mirrors `s3_service`'s precedent —
      `miss`/`degraded`/`conflict` are non-errors, an empty result set is `success` with a zero row count, and
      **`partial` is an ERROR** for three bulk operations whose loops swallowed per-object failures and handed
      the caller a number. 13 mutation proofs, all md5-verified restores; the implementer's own attack found and
      closed **three** guard holes, including an AST scan blind to a body that binds the handle first.
      **Its self-commissioned reviewer never returned, so the controller commissioned the review directly.**
      ORIGINAL ITEM FOLLOWS. The Weaviate connection-factory span owed from C1.6, and the span-metrics dimensions the dependency
      board actually promotes — as instrumented, the board's named consumer gets nothing for S3.
- [x] G.11 **DONE 2026-09-20 (`copilot-mro-obsm 0231a1cf` tests; 5 production files uncommitted).**
      Healthcheck on `/api/health` in all three stacks, probe verified **live in-image**. Confirmed the
      premise first: `docker inspect` → `Healthcheck = null`, `State.Health = <none>`, with
      `restart: unless-stopped` — an exit-0 crash loop really does read "Up 9 seconds".
      **THE RUNNING GRAFANA IS NOT THIS TREE'S**, and that changes what any live assertion can mean:
      `docker inspect` reports `config_files = /home/aditya/Code/copilot-mro/deployment/docker-compose.yml`
      with **both bind mounts under the PRIMARY checkout.** *"Any 'running stack' assertion written here
      would otherwise compare this branch's YAML against the other branch's container and pass."* The live
      test therefore takes every path **from `docker inspect`** and **skips naming the offending checkout**
      rather than pretending. **Owner step: recreate the stack from this worktree before it can assert.**
      **A DECOY MUTATION DEFEATED THE FIRST VERSION OF ITS OWN GUARD.** The healthcheck check accepted any
      probe *containing* `/api/health` — so `echo http://localhost:3000/api/health`, which always exits 0,
      **passed.** Found by attacking its own work; it now also requires a real HTTP client. Two more
      self-attacks changed the work: a substring grep for `grafana` would have swallowed a stack that only
      *mentions* Grafana in a comment, and a variable scan counted a name from a **commented-out** line.
      ORIGINAL ITEM FOLLOWS. **L-GRAFANA-UID.** A healthcheck on the Grafana service, so an exit-0 crash loop stops reading as
      "Up 9 seconds". The existing `test_grafana_provisioning_smoke.py` already asserts the four datasource
      uids — but it boots a **cold container on a tmpfs data dir**, so it proves the YAML parses and can never
      see a uid drift in a persisted `grafana.db`. The missing check is against the *running* stack, not
      another cold boot. Do **not** reach for `deleteDatasources` (M-GRAFANA).
      **IMPLEMENTATION NOTE (review r7b P2-6, `copilot-mro-obsm-r7b 1f705234`, 2026-09-21):** the
      healthcheck guard now PARSES the probe (`healthcheck_probe_offenses`: `shlex`, operators split,
      comments dropped): one HTTP client run directly — curl with `-f`/`--fail` in effect, or wget —
      on the health URL, then nothing or `|| exit <non-zero>` alone. The review's four decoys (`||
      true`, `echo curl`, no `-f`, `|| exit 0`) are red in the compose files and as parser cases,
      with 19 more decoys/real shapes; the live running-stack check uses the same parser (docker-
      gated, not run).
- [x] G.12 **DONE 2026-09-20, and VERIFIED AGAINST A GENUINE FRESH CLONE — not assumed.**
      `git archive HEAD | tar -x` into a scratch dir: that tree has **no `.env` and no `.env.sample`**, and
      `docker compose config` fails with *"required variable GRAFANA_ADMIN_PASSWORD is missing a value"*.
      Overlaying only the new deployment files renders exit 0 for dev, dev+phoenix and observe — **both via
      `--env-file` and via the documented `cp` copy targets.** A guard asserts **every path the sample
      names actually exists in that clone** — the runbook lesson (three secret files that did not exist,
      which cost every notification), applied to the file that replaces the runbook.
      **CONTROLLER BRIEF ERROR #41 — "three required variables" is wrong under both readings.** The base
      dev stack has exactly **ONE** `${VAR:?}`; the Phoenix overlay adds **three more**, so four across
      dev+overlay. The separate trio I was thinking of are Grafana-**provisioning** variables, not compose
      requireds — **and they carried a different defect entirely (see M-GRAFANA below).**
      **`GRAFANA_ADMIN_PASSWORD` keeps its `:?` — the item permitted defaulting and the implementer
      refused:** *"defaulting an admin-plane password is the failure the `:?` exists to prevent"*, on an
      admin plane with read/write over the data plane. Reversible in one line if the owner disagrees.
      ORIGINAL ITEM FOLLOWS. **L-COMPOSE-ENV.** Give `deployment/` its own `.env.sample` naming the three required variables, or
      default them so the stack starts; add a smoke that `docker compose config` resolves with only the
      documented sample present.
- [x] G.13 **M-RESIDENCY, judge side — DONE 2026-09-20 (`copilot-mro-obsm 4bfa4967`), mutation-proved.** `IN_ACCOUNT_JUDGE_PROVIDERS = frozenset({"azure","bedrock","ollama"})` at `agent_evaluation/contracts.py:56`, declared in **code** so nothing can widen it; `EVAL_JUDGE_PROVIDER_ALLOWLIST` can only **narrow**, and naming anything outside the catalogue in it is itself refused. Enforcement is **doubled** — validated in `__init__` (early refusal, no content read) and again immediately before `LLM(...)`, placed **ahead of the `from phoenix.evals import LLM` line**, so a refused run does not even load the vendor SDK. Exactly **two** judge-construction sites exist (`phoenix_adapter.py:298`, `:416`) and `LLM(` appears nowhere else in production across the workspace — both verified. The runbook is corrected (every `--provider` is now `bedrock`; the `OPENAI_API_KEY` recipe is gone) and a guard resolves every `--provider` in it against the catalogue so it cannot drift back. **Three residuals could NOT be closed, all code-level:** an evaluator object injected already bound to a vendor LLM; a caller implementing the `JudgeEvaluator` protocol entirely; and **per-tenant configurability is NOT implemented — only per-deployment**, which the evals plan §2.2 asks for and which is escalated rather than quietly widened. ORIGINAL ITEM FOLLOWS.**
      The owner ruled on 2026-09-19 "**enforce NOW, in this merge**", and no Phase G item was ever written for
      it — so the control sat in a gap between two plans, each pointing at the other. The evals plan
      (`agent-evaluation-completion.md`) states as settled fact that residency landed here and therefore
      declines to build it; G.8 named only the **exporter** half, which that same plan elsewhere calls
      unclaimed and takes for its own Phase 8. The merge plan's own §5.8 note above says it outright:
      *M-RESIDENCY is unenforced*.
      **Verified in the merged tree 2026-09-20:** zero matches for residency / allowlist / allowed-provider
      anywhere under `copilot_mro/app/services/agent_evaluation/`; `provider` is a free-form string passed
      straight into `LLM(provider=self._provider, model=self._model)` at `phoenix_adapter.py:289` and `:399`;
      and `docs/runbooks/observability/phoenix-evaluations.md:121` and `:137` document `--provider openai`.
      The suite is **already merged**, so the code that would send it is in the tree today.
      **The exposure:** a judge receives the user's question, the model's answer and retrieved manual text.
      Spec §6.5 and ruling 11 say client production content never leaves the client's own account and never
      reaches a SaaS in the data path. If Phase G closes and the evals project starts on its stated
      precondition, the first live run sends all three to OpenAI.
      **Build:** an in-account-only provider allowlist enforced where the judge LLM is constructed — not in
      the CLI, which is one caller of several — failing closed on an unlisted provider, with the refusal
      naming the provider and the ruling. Mutation-prove it: set the provider to `openai`, show the run
      refuses; restore, show it proceeds. Then correct the runbook's two documented `--provider openai`
      invocations, which currently teach the forbidden path.
      **Exporter side stays with the evals project** (its Phase 8) — this item is the judge side only, and
      the two must not both claim it again. G.8 is REMOVED from Phase G and that removal is what left this
      hole; closing it here is the repair.

      **IMPLEMENTATION NOTE (review r7b P2-5, M-RESIDENCY controller call, `copilot-mro-obsm-r7b
      b63a03fd`, 2026-09-21):** the catalogue is pinned by EQUALITY (a denylist let `litellm` and
      `vertex_ai` in) and is now scoped by the deployment's cloud: `EVAL_JUDGE_DEPLOYMENT_CLOUD` unset
      or `aws` -> {bedrock, ollama}; `azure` -> {azure, ollama}; `self-hosted` -> {ollama}; unknown ->
      refuse all. So `azure` is never default-admitted on AWS. Residency is also checked where the
      content GOES: each endpoint variable the provider's client may read, if set, must name an
      in-account host (`*.amazonaws.com`; an Azure OpenAI host, one of whose two spellings an azure
      judge must set; a private address/internal name for ollama incl. `OSS_LLM_BASE_URL`), inside
      `validate_judge_provider`, so both existing seats re-check it. **Default recorded:** unset cloud
      = aws. **Not verifiable here:** `arize-phoenix-evals` is installed in no venv, so the names are
      pinned to the ones the code and runbook use, not to the SDK's provider list; the endpoint
      variables are the union of boto3/openai-SDK/LiteLLM/Ollama spellings for the same reason.
      **IMPLEMENTATION NOTE (review r7b r2 P2-1 / R7B2-12, `copilot-mro-obsm-r7b d91ff4a1`,
      2026-09-22):** `*.amazonaws.com` above admitted an API Gateway, ALB, EC2 or S3 host in ANY
      account. A bedrock endpoint that is set must now be the Bedrock runtime service itself —
      `bedrock-runtime[-fips].<region>.amazonaws.com` or its interface VPC endpoint, matched whole
      (a bucket named `bedrock-runtime` on a legacy S3 host is refused). An azure judge must set
      `AZURE_OPENAI_ENDPOINT` — the resource the application itself runs on — as one resource host
      under openai / cognitiveservices / services.ai `azure.com`, and `AZURE_API_BASE` may name only
      that resource. Any proxy variable (`*_PROXY` but `NO_PROXY`, any case) refuses the run.
      **Not read, stated in code and runbook:** `AWS_PROFILE` (which account the credentials name)
      and the declared Azure resource's tenant — a host cannot prove either; closing that needs a
      declared account/tenant id checked by a network call at run time. Mutation-proved RES4–RES12.
- [x] G.14 **M-AUTHLOGS — DONE 2026-09-20 (`api-obsm d6ab632`), 15 of 16 repaired.** — pay down the 16 credential-path R22 log sites.** `middleware/auth.py` (13; claims,
      tenant ids, Redis keys) and `auth/jwks.py` (3; the key-pool URL). Sanctioned shape is
      `utils.observability.failure_fields`, never deletion of the diagnosis — a log line that loses its
      value is a worse outcome than the leak, so a site that genuinely needs a detail the shape cannot
      carry stays recorded with its reason. Tighten `_RECORDED_DEBT`, `_DEBT_WAS_REVIEWED_AS` and
      `_DEBT_REASONS` in the same commit; the guard asserts equality in BOTH directions, so a repaired
      site fails it until the record is tightened. The other 133 stay recorded behind the armed sweep at
      `api-obsm 66868f8`. **IN FLIGHT.**
- [x] G.15 **M-DEADROUTER — DONE 2026-09-20 (`api-obsm d6ab632`).** — delete `routers/cache_management.py`.** Verify the import graph before deleting;
      retires 6 log sites and 6 disclosure sites, and the stale comment at `middleware/auth.py:1314` goes
      with it. **IN FLIGHT, same implementer as G.14.**
- [x] G.16 **M-RUNERROR — api WRITE SIDE DONE 2026-09-20 (`api-obsm cc56667`); the `core` side is owed.** Sanitise `automation_runs.error`.** ~20 write sites in
      **AUDIT 2026-09-20 — VERIFIED DONE.** `core-obsm/core/resources/automations/automation_store.py:76`
      imports `RunErrorCategory, run_error`; `:1391` `TIMED_OUT`, `:1416` `INTERNAL`;
      `core/resources/automations/run_errors.py` exists. Closed by `core-obsm bbc67ed` (the G.21 commit).
      `api-obsm/flynapse_api/automations/`; the read is `core`'s `AutomationRun.error`. Category plus a
      safe message. **Spans two repos and needs both trees free.** Neither sweep can see it — the api guard
      sees a database write and the core guard sees a column read — so it needs its own guard, at the
      write side, where the category vocabulary is closed.
- [ ] G.17 **M-CARDINALITY — create the tenant-scoped instrument allow-list.** Not amend: R.4 established
      **AUDIT 2026-09-21 — THE RULING IS NOW KEEP-OR-STRIP, NOT ADD.** `tenant.id` **already rides** on
      `agent.turn.calls` and `agent.turn.duration_seconds` (`record_turn`'s explicit `tenant_id`, passed at
      `agent_shared/pipeline.py:493-499`) and on **every model metric** — `agent.model.calls`,
      `agent.model.cost_usd`, **`gen_ai.client.token.usage`** and `gen_ai.client.operation.duration` —
      through `for_turn`'s default attributes (`agent_shared/telemetry.py:1507-1523`). **Both since the
      colleague's `54a01f39`.** So the text below that keeps it OFF the token histogram describes a state
      that does not exist. **And `subagent.name` is still unvalidated:** `subagent_runs.py:128` passes
      `record.get("agent_name")` verbatim, while its own docstring at `:113` claims *"``name`` is a catalogue
      agent name"* (both working-tree only).
      there is no allow-list anywhere, only two ten-key DENY-lists (`flynapse_otel/registry.py:27`,
      `base.yaml:76`), with `tenant.id` on neither in either direction. Tenant identity goes on the
      closed-vocabulary counters (`agent.turn.calls`, `agent.model.calls`, `agent.model.cost_usd`,
      `agent.ledger.write_failures`) and **not** on `gen_ai.client.token.usage`. Also rule
      `subagent.name`, which is today the model's raw `subagent_type` string taken verbatim with no
      catalogue validation — **one hallucinated name mints a permanent series.**
- [x] G.18 **DONE — and it was done at `utils-obsm 24e073f`, SIX COMMITS BEFORE the controller briefed it
      as "the largest remaining item".** *"M-LEGACY: declare and bound the 27 legacy metric families, with
      guards"* — a 581-line `utils/observability/legacy_families.py` plus two guard files (519 + 284
      lines); the production half is in `metrics.py`, one of the uncommitted ten. **THE PLAN'S OWN
      UNCHECKED BOX IS WHAT MISLED ME** — this is the SECOND bad brief caused by plan staleness (G.29 was
      the first). The verifying agent did not rebuild it; it **adversarially verified it, and it holds.**
      **Counts re-derived from source, and they reconcile a disagreement three documents had:**
      27 families (`grep -c '^    Family('` = 27) · **the "28 orphans" is 27 legacy + `gen_ai.client.
      operation.duration`, and the 28th is a MODERN registry instrument — an orphan but never a PORT
      candidate. Neither document was wrong; they count different things.**
      **THE ASYMMETRY IS SETTLED, and settled the right way: drop-the-key-and-warn-once**, argued over ~35
      docstring lines — *the value is the signal and a label is a refinement; the silence is permanent and
      undiagnosable; the metric that vanishes is the one someone just edited.* It deliberately does **NOT**
      change `_lint_attributes`: *"the defect there is the silent swallow in `_safe_add`, not the raise,
      and both live in a repo this work may not write."* The counter-argument (a mid-stream shape change
      makes `sum by (key)` read as partial) is **stated rather than hidden**, and the surviving behaviour
      is pinned **behaviourally, not just structurally.**
      **Dispositions are recommendations only, never applied: 17 port / 10 retire.** And the implementer
      recorded what R.4 missed — **`TEST_CONSUMERS`: 11 of the 27 are asserted on by tests in two repos**,
      so "no consumer" was too strong and retiring one turns a suite red.
      **OPEN for the owner (G.17):** all 27 carry `tenant_id` **uncapped** — **not a violation**, because
      it was already on every one of them before the port, so the port PRESERVED a label rather than
      adding one, and `series_per_tenant` deliberately excludes it. Removing it is G.17's call.
      **And one claim is ASSERTED, not SETTLED, and the agent said so:** the commit message's *"509,981
      series per tenant across all 27, of which four families are 95%"* **is asserted by no test** — the
      guard asserts only `unbounded == []` and `worst > 1`. The owner should see that figure beside the
      four call-site label removals its notes recommend. ORIGINAL ITEM FOLLOWS. **M-LEGACY — port the 27 legacy `MetricsService` families onto the registry.** Bounded attribute
      set per family, the off switch `get_metrics_service()` lacks, and a derived inventory guard on the
      `_emitted_series.py` pattern. Retirement is recommended per family, never decided by the
      implementer. Must settle the raise-vs-drop asymmetry: the registry **raises** and `_safe_add`
      swallows, so a forbidden key makes the **whole series vanish silently**, while the legacy shim drops
      the key and warns once. **utils-side IN FLIGHT; call sites in copilot-mro and core follow.**
      **PROGRESS 2026-09-21 (copilot-mro-obsm-panels, branch `obs-merge-panels`, unpushed):** M-LEGACY-DELETE copilot-mro half `bf071877` (8 call sites deleted + retired-name guard; utils may now drop the 10 declarations); M-LEGACY-PANELS `9900a933`+`145cb929` (17 runbook lines, 15 panels on fn-llm-agents/fn-platform-health, legacy-series lint) and `c56f88f3` (7 oss rules, first-event branch); AWS alarms wait for C2.
      **iac PANELS DONE 2026-09-21 (`iac d52e8b8`, not pushed):** the 15 panels in the CloudWatch dialect, one
      Query Studio text widget per board (`flynapse-llm-agents` 6, `flynapse-platform-health` 9), with the oss
      companions, the first-event pairing and a `WIRED 2026-09-21` note. The dialect guard's premise — no
      instrument is BORN with a family suffix — is false for these counters (`_total` is in the OTLP name), so
      `FAMILY_SUFFIXED_INSTRUMENTS` pins the 15 `_total` names, exact-name only, and
      `document_hub_processing_duration_seconds` joined `UNIT_SUFFIXED_INSTRUMENTS`; the README and header
      sentences stating the old premise were corrected with it. 262 → 266; 8 mutants red.
      **Still C2-gated:** the 7 AWS alarms and their 7 `alert_thresholds` entries. **Owed to copilot-mro (not
      iac):** CATALOGUE §3/§6 `aws` paragraphs still say the `_total` names "are only the OSS Prometheus
      translation" — false for these rows; they should give the aws form and the born-`_total` exception.
      **iac review r3 fixes, 2026-09-22, not pushed:** `56e7673`: the platform-health header's no-suffix claim is
      scoped to `otelcol_*` and names the legacy row as the one exception, and a guard requires any "NO Prometheus
      suffix" header on a born-suffix board to name it (red on both boards). `74346bb`: the llm-agents legacy
      WIRED note names `note_embedding_cache_hits` (utils `llm.py:1337`), not the nonexistent
      `_record_embedding_cache_metrics`, plus `accumulate_bedrock_cost`; a word pin with definition sites holds
      it. The utils/copilot-mro declarations carrying the wrong name are the utils lane's. **Label keys and
      values stay unguarded (r3 P3-5, V1/V2/V6 survive):** see §6 "Deferred from Phase G".
      **iac review r4 fixes, 2026-09-22, not pushed:** P3-G `d417b1a`: the recorder pin compares the file-named emitters too (R3 red). **Corrections (r4 P3-H):** `74346bb`'s message hands the copilot-mro copy of the phantom recorder name (`_emitted_series.py` at `557a178f`) to "the utils lane", which fixed only utils' own file; that copy is another lane's per the controller, not iac's. `56e7673`'s subject says P3-5 for r3's P3-6.
      **utils r9 (review r8 P2-1), 2026-09-22, not pushed:** the metric inventory's AST reader was REDESIGNED to fail closed (`utils-obsm b1d9834`, `5c7f81e`, `6ea14ea`): a label dict's keys, a forwarder body and a family constant are read only through recognised uses/bindings; any other mention is reported with its line; limits in a pinned register (design: `utils-obsm docs/plans/utils-review-r8-batch.md`).
- [x] G.19 **DONE 2026-09-20 (`api-obsm cc56667`).** The log sweep needed the HTTP-exception carve-out its sibling already has. CONTROLLER
      DECISION 2026-09-20, pending owner review — it is a rule change, not a paydown.** One site
      survives G.14: `api-obsm/flynapse_api/middleware/auth.py:474`, `except HTTPException as exc:`
      logging `exc.status_code` and `exc.detail`. **That is not a `str(exc)` leak** — the detail is the
      refusal **this middleware itself decided and raised**, and the very next statement puts both
      values into the response body, so the log discloses nothing the caller is not already told.
      The **response** sweep sanctions exactly this read by name (`<name>.detail` / `<name>.status_code`
      under a handler catching HTTP exception types only); the **log** sweep has no such carve-out, so
      its allow-list flags it. Repairing it would delete the only two things the line says, and
      `failure_fields(exc)` would replace them with `error_type=HTTPException` plus frames — naming
      neither the status nor the reason. That is the "worse than the leak" outcome the rule exists to
      avoid. **Grant the carve-out, scoped exactly as the sibling scopes it**, and prove it: a mutation
      showing a genuine `str(exc)` under the same handler shape still fails.
- [x] G.20 **A third guard constrains every remaining R22 repair, and no brief had named it.**
      **PAID TO ZERO 2026-09-21 (`api-obsm 1b1d088`), not re-scoped. Live sweep: keys=0, sites=0.**
      Final **1566 passed, 4 skipped, 0 failed**, `rootdir: /home/aditya/Code/api-obsm`.
      **THE COUNT I BRIEFED WAS A MIS-READ OF OUR OWN REGISTER.** 127 flags and 42 function entries were
      exact — but **"62 distinct sites" is a SHAPE-tag count, not a site count.** The real number of
      distinct physical log statements is **77**: 49 lines carried **two** shape flags at once
      (`caught-exception-rendered` + `logger.opt(exception=…)` on the same call), so 127 flags collapse to
      77 lines. **A register that counts flags and a brief that reads them as sites will disagree by 40%.**
      **A CODEMOD WOULD HAVE BEEN ACTIVELY DANGEROUS, AND THAT IS THE FINDING.** 79% of lines fall into two
      shapes, which reads like "codemod plus a narrowed rule". **It is a trap.** Those f-strings interpolate
      **ids**, not just `{exc}`. Strip `: {exc}` and the message is **still a format string**; add
      `**failure_fields(exc)` beside it and you have built **precisely the defect
      `test_log_messages_are_not_format_strings.py` exists to stop** — loguru calls `message.format(**fields)`,
      and a brace-bearing runtime value raises `KeyError` **inside the logging call**, so the handler never
      reaches its `raise` or `return`. **A mechanical fix would have converted a confidentiality defect into
      an AVAILABILITY one, in the handlers whose job is to be what still works.** 77 semantic decisions, by
      hand, not a regex.
      **One group needed a different fix, and paying the debt IMPROVED the diagnostic.** `worker.py`'s
      startup refusal carried the operator's whole remedy — which variable, what it was set to, what it must
      be — **only** through the rendered exception text. Deleting it loses the remedy; `failure_fields`
      alone yields `error_type=WorkerStartupError`, which names nothing actionable. The diagnosis moved
      **to the point of capture**: `_require_worker_mode` logs a constant message with the configured mode
      as a field (an enum value — **a closed vocabulary this module owns, never a caller's data**). And two
      pairs of arms had been logging an **identical message**, told apart only by the exception text, so
      withholding it would have made them indistinguishable — each arm now names which half failed.
      **LIVE PROOF, UNPLANNED: the lane's own baseline run exported the leak while measuring it** —
      `executor.py:680` logged `FATAL: password authentication failed for user "flynapse_app"` with host,
      port and DB username, plus a traceback of absolute paths. **Not a hypothetical.**
      **The register was left honest, and two things had to be fixed so emptiness does not hollow the
      guard:** (a) the non-vacuity floor **derived its module set from the register**, so an empty register
      silently degrades it to *"the sweep read `main.py`"* — the 13 cleared modules are now **pinned**, plus
      a third floor asserting the detector still reaches a logger call inside an `except … as` handler, the
      half that cannot be proved by reading imports; (b) the dated-reason regex demanded a literal ruling id
      that no future entry would be covered by, now generalised to a date check matching both sibling sweeps.
      **`executor.py`'s reserved site was taken deliberately and said so** — at `:1077`, not the `~1071` I
      briefed — because the tranche was the whole module and leaving it would split one file across two
      owners. **The register is now empty, so nothing describes a site that changed.**
      **Two coordinator items closed here:** `trace.Status(...)` now matched on the callee's **name tail**
      with the dotted spelling added to the detector's own leak shapes; and the server-span guard —
      **confirmed and WORSE than reported: restoring the leak left ALL TWELVE assertions green.** Fixed by
      capturing the `Status` the shim constructs, one step before upstream clobbers it, still through a real
      request. **One correction in our favour: the SOURCE sweep did catch it, so the leak was never
      undetected estate-wide — only the behavioural guard was blind.** Both false docstring sentences
      corrected, and the misattributed credit verified empirically.
      **REFUTED — "a bare `except Exception:` + `format_exc()` is invisible to all three sweeps."** It is
      **flagged** by api's, because the renderer rule walks the whole module independently of handler
      binding and a bare handler has no caught name to miss. **May still be real in the two sweeps with no
      renderer rule** — routed to utils and core to test rather than assume.
- [x] G.103 **MY OWN LANE RECIPE WAS WRONG ALL NIGHT, AND IT FAILS SILENTLY.**
      **AUDIT 2026-09-21 — DONE.** `utils.config.find_env_file` checks **`ENV_FILE` first** (present since
      `e66501f`); `utils-obsm 099629f` corrected its false "searches up the tree" docstring and **pinned the
      order**, `ENV_FILE` precedence included (`tests/unit/infra/test_env_file_discovery_is_two_directories.py`).
      **The robust lane recipe is `ENV_FILE` plus a pinned `PYTHONPATH`** — it no longer depends on the cwd
      at all, which the repo-root recipe below still does.
      Every brief this session said **run from a neutral cwd** to defeat the sibling-checkout hazard. For
      `api-obsm` that **destroys the run**: `utils.config.find_env_file` searches **cwd FIRST**, so from
      `/tmp` the `.env` is never found, `POSTGRES_PASSWORD` is lost, and **41 integration tests fail on
      `FATAL: password authentication failed`.** Separately, without `PYTHONPATH` pinned to the merged
      trees, **52 test modules fail to collect** (`ImportError: cannot import name 'pattern_delete_failed'`).
      **THIS EXPLAINS A REVIEWER'S UNRESOLVED FINDING.** An adversarial reviewer reported api's integration
      lane as **41 failed / 318 passed**, said it was *"equally red pre-merge"*, and **could not root-cause
      it** — naming the experiment as "re-run one case with `setup_logging` installed so `failure_fields`
      renders". The cause was the lane recipe, not the code. **That lane may not be red at all.**
      **CORRECT SHAPE: run from the REPO ROOT with `PYTHONPATH` explicitly pinned** — cwd for the env file,
      `PYTHONPATH` to beat the venv's `.pth` files. `api-obsm`'s `.env` symlinks to `../api/.env`.
      **Every measurement taken under a neutral cwd tonight is suspect** and must be re-checked per tree —
      routed to core and utils to establish whether their suites read an `.env` through the same helper.
      **And the underlying hazard deserves its own look:** a config helper whose answer depends on the
      caller's working directory is the same class as a path resolved by name — correct in the common case,
      silently wrong in the uncommon one. It has cost real measurement time twice tonight.
      `api-obsm/tests/unit/telemetry/test_log_messages_are_not_format_strings.py` fails on an
      **interpolated message passed alongside structured fields** — loguru then runs `str.format` over
      runtime text and raises `KeyError` inside the logging call. So the naive reading of "apply the
      sanctioned shape" (keep the f-string, append `**failure_fields(e)`) is **RED**. Every message must
      become a constant with its ids moved to bound fields. **This governs the remaining 128 recorded
      sites** and belongs in the brief of whoever pays down the next tranche.
- [x] G.21 **M-RUNERROR, the `core` half — DONE 2026-09-20 (`core-obsm bbc67ed` + 2 uncommitted production
      files).** Lane **2314 → 2401 collected and passed**, `rootdir` correct on all 29 invocations. **Exactly
      two originating write sites**, both categorised: the stalled-one-shot close as `timed_out` (the category
      **reports what was observed and claims no cause** — the predicate is `started_at + ceiling < now`, which
      is that category's definition verbatim; `internal` would assert a fault that may not have happened) and
      the unserved close as `internal`, **deliberately not `unavailable`, because a one-shot row has NO next
      slot** — telling the owner to wait would strand them.
      **The hole nobody anticipated, and it was real:** putting the fallback on the response model is **not
      sufficient**. Pydantic v2 defaults to `revalidate_instances="never"`, so FastAPI serialising ready-made
      instances passes them through **untouched** — probed and seen to leak, then fixed with
      `revalidate_instances="always"` and confirmed by a reviewer against a live app (default config served
      `{"error": "RAW-LEAK"}`).
      **An adversarial reviewer found eleven gaps; all eleven were real and fixed — and one objection was
      re-argued rather than accepted, and WITHDRAWN.** ORIGINAL ITEM FOLLOWS. The api write side shipped a closed six-member vocabulary
      (`access`, `configuration`, `timed_out`, `unavailable`, `no_answer`, `internal`) in
      `api-obsm/flynapse_api/automations/run_errors.py`; the stored shape is `"<category>: <sentence>"`
      and no token contains a space or a colon, so `partition(": ")` is unambiguous. **`core` owes three
      things**, the second of which my brief got wrong:
      (1) **A read-time fallback:** a value with no recognised prefix is pre-M-RUNERROR — treat it as
      `internal` and **do not render its detail**, because that detail is exactly the raw text this work
      removed.
      (2) **`core` is itself a WRITER of this column** — my brief said it only reads it.
      `core/resources/automations/services/automation_store.py` composes `error` from bound constants in
      `_REAP_STALE_RUNS_SQL` (~:1175, should become `timed_out: …`) and `_CLOSE_UNSERVED_ONE_SHOT_SQL`
      (~:1197, should become `internal: …`). Both are safe but **uncategorised, so without this the
      column is only 29 of 31 typed.**
      (3) **Legacy rows: a read-time guard, NOT a migration.** Measured on the local dev database: 37
      runs, 4 with a non-null error, **0 categorised** — and one of the four is a genuine leak in the
      wild, a raw `ImportError` naming internal module paths. A migration cannot tell a safe legacy
      string from an unsafe one; "no prefix ⇒ do not render the detail" is correct for every row without
      inspecting any.
- [x] G.22 **DONE 2026-09-20 (`dashboard-obsm fdf7487` + 3 uncommitted production files).** Lane
      **2510 → 2533 passed / 0 failed / 0 skipped**, typecheck and lint clean. **Copy is CATEGORY-driven and
      the stored sentence is DISCARDED ENTIRELY** — because the backend's half is a diagnostic, not advice;
      because its `internal` guidance says *"contact support with the run id"* and **the panel never renders
      a run id**; because only six frontend-authored sentences can reach the reading flow, so the day a write
      site interpolates a variable nothing changes here — **and four sites ALREADY do**, one embedding
      `automation.params!r`, a Python repr of the owner's config dict; and because `RUN_REASON_COPY` is the
      sibling mechanism and does exactly this. `data-run-error` now carries the **category**, in three states
      — the token, an `unrecognised` sentinel, or absent — because *"no error"* and *"an error I could not
      read"* are different facts to whoever reads a support screenshot. **Its adversarial reviewer found 4
      HIGH and 7 MEDIUM, all real, including TWO of the implementer's own guards passing vacuously**; all
      fixed but the two that are owner decisions. ORIGINAL ITEM FOLLOWS. — and it has been shipping the
      raw value to the browser all along.** `dashboard-obsm/components/features/automations/RunHistoryPanel.tsx:176`
      puts the raw column into a `data-run-error` DOM attribute, while
      `runOutcomeCopy.ts:147` **deliberately never renders it as prose** and its own comment says why —
      *"It is a raw exception — a psycopg2 message, an import failure"*. **So the frontend already knew
      the value was unsafe, and the disclosure path was API JSON → browser DOM regardless.** Both verified.
      With a category prefix the panel can map each category to actionable copy the way `RUN_REASON_COPY`
      already maps `reason`. Needs the `dashboard` writer, after G.21.
- [ ] G.23 **The dimensions half's two surviving residuals, found while closing G.10's span half.**
      (1) **`peer.service` is promoted by `tempo.yaml`'s `span_metrics.dimensions` AND asserted as expected by
      `copilot-mro-obsm/tests/integration/otel/test_tempo_span_metrics.py:34` — while ZERO production code in
      `utils-obsm`, `copilot-mro-obsm` or `core-obsm` sets it.** A promoted dimension nothing emits, with a test
      that certifies the promotion rather than the emission.
      (2) ~~**`s3.download` still has no `db.system`**~~ — **WRONG, and it was MY error. Struck 2026-09-20 by the
      independent G.10 review, and re-verified by the controller.** I wrote that S3 "remains an empty-`db_system`
      series". It does not. The two panels group by the **pair** with legend `{{db_system}}{{server_address}}`
      (confirmed in `dependencies.json`), so S3 gets **its own host-named series** — not a collapse. And the
      omission is **deliberate and documented at `utils-obsm/utils/s3_service.py:218-222`**: `server.address` is
      precisely what keeps S3 out of the empty-label bucket, while the "DB client p95 by system" panel filters
      `db_system != ""` and drops S3 **by design, because S3 is not a database.** The G.10 plan line's
      "the board's named consumer gets nothing for S3" was already answered by C1.8. **Nothing is owed here.**
      **G.23(1) stands, confirmed independently:** `peer.service` promoted at `tempo.yaml:61`, asserted at
      `test_tempo_span_metrics.py:34`, **zero production emitters across all four repos.**
- [x] G.24 / G.29 **DONE 2026-09-20 (`utils-obsm 1cdebad` + a 692-line uncommitted production diff).** Lane
      **1252 → 1316 collected and passed**; consuming copilot-mro suites 297/297. **The raw-exception surface
      was 29 sites, not the ~22 I briefed** (22 `traceback.format_exc()` + 7 `{e}`), and three of the seven
      were in a **returned health body**, not a log. **A CREDENTIAL LEAK was found inside the hunk the
      previous diff had already edited** — `logger.info(f"Successfully connected to Weaviate at
      {settings.weaviate_url}")`, **three lines above that helper's own docstring saying never to log the
      URL** (verified: present at `HEAD~1:257`, gone now). Also **the user's query logged verbatim** by
      `bm25_search`, and **tenant document content logged AND `print()`ed** per object in a dry-run delete.
      **The allowlist finding is worse than recorded:** the sibling sweep's module list resolves against
      copilot-mro's repo root, so this file **could never have been in it**. **The default was inverted** —
      the sweep now walks every `utils/**/*.py`, a leaking module must be named with a reason, and **a
      backlog module that has been CLEANED also fails, so the list only shrinks.** Proved by dropping in a
      brand-new leaking module: it failed on its first run with no list to edit. ORIGINAL ITEM FOLLOWS., reported by the G.10 pass and deliberately not
      fixed there.** (1) `delete_objects_by_property` and `list_and_delete_objects_by_property_contains` log
      `f"Failed to delete {obj.uuid}: {e}"` — **raw exception text in an f-string, the exact R22 shape C1.9 fixed
      elsewhere in this same file.** Two lines; wants `failure_fields`. (2) A `WeaviateTenancyError` from
      `get_collection` — **a caller-side bad-tenant bug that never reaches the server** — is marked an ERROR client
      span, so **caller bugs inflate the Weaviate dependency error rate**. Pre-existing behaviour of `hybrid_search`;
      the implementer kept it rather than invent a divergence, which was right, but it wants a ruling.

- [x] G.25 **DONE 2026-09-20 (`core-obsm 1d6adca` + `bdea4ba`), 11 mutation proofs, pin 4 tests → 31.**
      Analytics subdir **119 passed**; whole suite **3012 collected / 2429 selected / 2429 passed**,
      `rootdir: /home/aditya/Code/core-obsm`, both granularities.
      **(a) The live defect was REPRODUCED, not relayed** — probe showed `registry.__file__` at
      `/home/aditya/Code/copilot-mro/...`, with `facts_from_block_data` and `FACTS_UPSERT_SQL` both absent.
      Fixed with G.31's pattern: scan siblings, require ≥1, hold every copy, **name the checkout in the
      test id**, assert `module.__file__` (G.26), and **isolate-then-RESTORE `sys.modules`** (G.27).
      **Two tiers, and the partition is itself guarded** — the pre-merge copy carries the constants but not
      the projection, so constants run over every copy while projection limbs run only over copies
      declaring the whole surface, and **a copy declaring PART of it FAILS**, so the excuse cannot widen
      into an exemption. Both of G.31's documented residual costs handled: no sibling **fails loudly rather
      than skipping**, and a stale sibling reddening core was **measured** (a synthetic sibling at
      `FACTS_VERSION = 2` produced 6 failures, every id naming the probe; probe removed, workspace verified
      clean).
      **(b) Done, and it CLOSED G.35's hole** — `facts_upsert_params` vs `_as_params` is now compared, and
      mutation M7 (dropping `cited_documents` from the json-serialised set, G.35's exact scenario) failed
      that limb **while core's other 1228 tests and copilot-mro's 143 stayed green**. G.35's claim that
      nothing caught it is **verified, and the hole is now closed.**
      **(c) Done — and a THIRD false sentence was found that the brief never named**: "the writer reuses it
      verbatim" → the writer MIRRORS it, importing copilot-mro's own copy.
      **Two controller brief errors caught and corrected by the implementer** (#23, #24): the definition is
      at `postgres_table_definitions_modules/chat_turn_facts.py:195`, **not `blocks.py:195`**; and "the
      constants test compares the upsert SQL" describes **copilot-mro's** test, not core's — core's pin
      never compared it. Both now compared from core's side.
      ORIGINAL ITEM FOLLOWS. **G.5's `core` half — and its FIRST item is a live defect, not new work.**
      **(a) The drift pin is pinning the WRONG TREE.**
      `core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py:24` resolves
      `sibling_repo(__file__, "copilot-mro")` → `/home/aditya/Code/copilot-mro`, **the main checkout, on
      branch `langgraph-merge`** — not `copilot-mro-obsm`, which is a **git worktree of it**
      (`copilot-mro-obsm/.git` is a file pointing at `copilot-mro/.git/worktrees/copilot-mro-obsm`).
      **Verified by the controller:** the main checkout's only `facts_from_block_data` hit is a COMMENT at
      line 43; the definition is at `copilot-mro-obsm/…:195`. So the behavioural limb would fail with
      `AttributeError`, **and today's constant limbs are silently pinning a different branch.**
      `sibling_repo`'s own docstring warns about exactly this. **Fix the resolution before adding anything.**
      **(b) Add the behavioural limb** — `facts_from_block_data` equality over the fixed shapes, plus
      `FACTS_UPSERT_SQL == backfill._UPSERT_SQL`. **No loader change needed.** copilot-mro already pins the
      identical comparison from its own side, so core's limb is a **second independent witness**, not the
      only one.
      **(c) One sentence, not a rewrite.** The backfill's docstring still says the production writer mints
      rows "**once it lands**" and "Until then nothing writes the relation online". **Both are now false.**
      The gap-fill framing, the dropped-schedule paragraph and the depth-coupling fix are **already done** in
      core's working tree.
- [x] G.26 **DONE 2026-09-20 (`copilot-mro-obsm 20ceebe0`) — and MY PREMISE WAS WRONG IN MECHANISM while
      the real hazard was BIGGER.** **Controller brief error #27, both halves:** I wrote *"obsm first ONLY
      because of a PYTHONPATH pin."* **There is no PYTHONPATH pin anywhere** — the explicit pin is
      `sys.path.insert(0, _REPO_ROOT)` at `tests/conftest.py:44-45`. **And it is not the only thing:**
      three mutations were tried — delete the conftest insert, replace it with an insert of the sibling,
      move `rootdir` into `api` — and **in all three `copilot_mro.__path__[0]` stayed this worktree**,
      because pytest's own rootdir insertion holds it redundantly.
      **The real unprotected surface, measured:** `poetry -C api run python -c "import copilot_mro"` →
      `__path__ == ['/home/aditya/Code/copilot-mro/copilot_mro']` — **the pre-merge checkout ALONE; this
      worktree is not on the path at all.** So every script, ad-hoc probe, and any pytest run whose
      `rootdir` is elsewhere reads the other branch.
      **TWELVE bare-name sibling sites, not six** — a first sweep found 6 and a second pass found 6 more
      the first filter dropped. **And the defect was invisible by construction: the five contract
      checkpoints among them PASS AGAINST EITHER CHECKOUT (78 passed both ways).**
      **The fix was PROMOTED, not invented** — the suffix-matching rule already existed hand-rolled in
      `_utils_root` at `test_phase1c_nonagent_scope_guard.py:192`. It became `sibling_checkouts` /
      `sibling_variant` in `tests/_root.py`, which is the mechanism that then went estate-wide (G.52).
      **Per-import `__file__` assertions were judged the WRONG rule at scale** — 540 test files import
      `copilot_mro` by dotted name, one of them 17 times — so the central mechanism is guarded once
      instead. Exactly **two** files in the tree assert a loaded module's `__file__`.
      **An honest limit is stated IN THE FILE rather than implied away:** two namespace tripwires are
      **measurements, not mutation-proved guards** — no mutation could defeat them from inside the lane
      because pytest itself holds the property. They are not vacuous (they fail the moment resolution
      moves, which it does outside the lane), and the file says so. ORIGINAL ITEM FOLLOWS. **The namespace-package hazard — a THIRD instance of reading the pre-merge sibling.**
      `copilot_mro` is a **namespace package spanning both checkouts**: measured,
      `_NamespacePath(['…/copilot-mro-obsm/copilot_mro', '…/copilot-mro/copilot_mro'])`, **obsm first ONLY
      because of the PYTHONPATH pin.** Without the pin, an import resolves to the **pre-merge sibling** — and
      for G.5 that sibling has no `facts_from_block_data`, so **the writer's own savepoint would swallow the
      `ImportError` into a missing row**: a silent no-op wearing a green suite. G.5's guard pins the module by
      dotted name and asserts `module.__file__`; **every future cross-module guard in this estate needs the
      same assertion.** Companion instances: my own pytest lane (CHECKPOINT 12), and the phase-1c scope
      guard's `_utils_root` resolving the workspace rather than the tree under test.
- [x] G.27 **A test-loader defect that made a monkeypatch never fire, in a suite reporting green.**
      **AUDIT 2026-09-20 — VERIFIED DONE.** `tests/unit/chat_history/_chat_history_store_loader.py:89`
      builds `originals`, `:105-107` restores. Committed `copilot-mro-obsm c80c686d`. **Its only residual —
      "worth a sweep for the same shape" — is already enumerated inside G.54, which names the live
      instance. G.27 ⊂ G.54; do not dispatch it separately.**
      `copilot-mro-obsm/tests/unit/chat_history/_chat_history_store_loader.py` **popped** four modules from
      `sys.modules` instead of restoring what was there. Ordered after a test that imports the app for real,
      the live `ChatHistoryDB` was built from a `chats` module the dotted name no longer resolved to, so the
      next `import_module` got a **second copy** — and a delete-race monkeypatch patched a module the live
      object never consulted. **The hook simply never fired.** Fixed at the root (restore, don't pop), found
      only because a new file sorted last in its directory. **Invisible to the sanctioned per-directory lane:**
      each directory was green alone and the combined run failed. Worth a sweep for the same shape elsewhere.

- [x] G.28 **DONE 2026-09-22 (M-WEAVIATE-DOOR): traced CLIENT spans at the three doors, copilot-mro `7f9e174b`; r6 found `memory_index.py` bypassing two doors → fixed `4b5aea14` with a sweep forbidding raw handles; independent check = copilot-mro r7.** **G.10's real door: ~26 production call sites bypass `class Weaviate` entirely — and it is the door
      C1.6 NAMED.** The G.10 reviewer's headline finding, triaged by the implementer, which then recommended
      **not** ticking G.10 on its own work. **Verified by the controller:**
      `copilot-mro-obsm/copilot_mro/app/services/weaviate_tenancy.py` exposes `collection_handle` (`:418`),
      `collections_for` (`:431`) and `weaviate_connection` (`:565`), and **26 call sites across eleven modules
      reach Weaviate through them** — the whole llama_index RAG retrieval path, document-hub indexing, the
      memory index, the AMOS retrieval tool, the workout gate, tenant and operator partitions, and the boot
      check. **C1.6's own wording says the spec put the wrapper on `weaviate_connection()` deliberately.**
      The G.10 pass instrumented a different object, in a different repo, and **its guard structurally cannot
      see these sites** — it parses one `ClassDef` in one file.
      **And the board impact is far smaller than first reported: 16 of the 20 traced methods have ZERO
      production callers** (health_check 14, get_object_by_id 1, hybrid_search 1, bm25_search 1; the rest
      none). So the dependency board went from **~2 live shapes to ~4, not 1 to 20** — the implementer
      corrected its own overstatement, and I had relayed the wrong figure.
      **This is a copilot-mro slice, not a utils one.** It needs an owner decision on shape before it is
      built: wrap the three tenancy functions, or instrument at each of the 26 sites, or push callers onto
      the traced class.

- [x] G.29 **DONE 2026-09-20 (`utils-obsm 02099ff` + uncommitted diff), 18 mutation proofs, lane 1344 → 1369.**
      **PLAN DEFECT, AND IT CAUSED A BAD BRIEF — recorded so it is not repeated.** This file carried
      `- [x] G.24 / G.29 DONE` at one line and `- [ ] G.29 … Four P1s, NONE fixed` at another. The
      controller briefed an implementer from the stale line, and it opened its report with *"the brief is
      one pass stale."* **Three of the four P1s and ALL of G.24(1) were already done in this tree.** The
      duplicate is now resolved to this single entry. **The rule the owner set — never report already-done
      work as pending — was broken by the plan's own internal inconsistency, not by a missing check.**
      **What was genuinely missing was (d), and that is what got built.** `utils/embedding_service.py` had
      **zero** OpenTelemetry; its three `embeddings.create` sites now share one `_embed` helper — the only
      place the module reaches Azure and the only place a span opens — nesting under
      `weaviate.vector_search`, so a `db.system="weaviate"` p95 is finally decomposable.
      **Dimensions were read off the dashboards before anything was named:** the span carries
      `server.address` + `rpc.service="AzureOpenAI"` and **deliberately NO `db.system`**, because
      `dependencies.json` splits on `db_system != ""` / `== ""` — **any `db.system` would move a SaaS call
      onto the database panel and fold its latency back into the very Weaviate series this item exists to
      decompose.** Mutation M3 proves the guard catches that.
      **It attacked its own guard and found two real holes:** the scan matched only
      `<x>.embeddings.create(...)` — **the same narrow-name blind spot the G.10 review found next door** —
      so an alias, a `getattr`, or a raw `.post("/embeddings")` were invisible; and **every other assertion
      in the file was satisfied by a span opened BESIDE the call** (span exists, right dimensions, nests
      correctly, reports success, duration microseconds, p95 still unexplained, suite green). Both closed,
      M15 and M16 the proofs.
      **Outcome ruling, and the disanalogy is the point:** `rate_limited` is an **ERROR**, unlike
      `truncated` — *"the dependency did what it is configured to do and still returned usable data"* is
      true of truncation and false of a 429, which returns none. A cache hit and an argument refusal open
      **no span at all**: the dependency was never asked, and counting them dilutes both the rate panel and
      the error share.
      **Deliberate omission, recorded as OPEN rather than hidden:** no token count on the span, because
      reading `usage` there lets an accounting bug turn a successful round trip into an ERROR span — a risk
      this module has already ruled against twice.
      **Independent re-verification of the prior pass** (it did not take its word): all five review blind
      spots re-added and **all five caught**, plus two it invented itself (a private `_client` handle and a
      round trip in a nested closure). **The review's own suggested one-liner `instrumented <= touching`
      was RED as proposed** and only became true after the transitive closure — which the prior pass
      caught. **Controller correction: "the guard you are about to extend is one of the weakest" is no
      longer true — it is now one of the strongest in the estate, 58 tests with thirteen probe shapes.**
      **It also closed the review's own untested item #4:** the three searches are **not** a missed
      truncation site — `top_k` is the contract of a top-K ranking, not a cap, and marking it `truncated`
      would fire on every search. All 12 `break` sites walked. ORIGINAL ITEM FOLLOWS. **What the independent G.10 review found, beyond the un-tick. Four P1s, none fixed.**
      **(a) Five proven blind spots survive in the guard**, and one is the shape of the file's own flagship
      method: a public method delegating to an exempt private body touches none of the matched names, and
      **`hybrid_search` IS exactly that shape** — the reviewer re-derived the scan and `touching` does not
      contain it. **An undecorated twin of the flagship method is invisible**, surviving only because a
      C1-era test pins that one name by hand. Also missed: `backup`, a real v4 sub-API left out when five
      others were added; a call through the public `get_client()` accessor; and `getattr(h, "query")`.
      **A one-line `instrumented <= touching` assertion would surface the delegation class today.**
      **(b) Two more swallowed-truncation paths report `success`** — `export_data_to_csv` catches "maximum
      results exceeded", warns, breaks and writes a **short CSV** as `success`/OK; `drop_properties_from_schema`
      consults only `errors`, so a run stopped by a result cap is `success`. The implementer found three sites
      of this pattern **and stopped at three.**
      **(c) A SECOND class of caller-side error, and it is NEW with G.10** — a `ValueError` raised **before the
      first `get_collection`** is now a Weaviate ERROR span. G.24(2) records only the tenancy class and calls it
      pre-existing; **this one is not, and the radius went from 1 door to 20.**
      **(d) `weaviate.vector_search` encloses an Azure OpenAI round trip with NO child span anywhere** —
      `utils/embedding_service.py` has **zero** OTel instrumentation. So a `db.system="weaviate"` p95 contains a
      third-party SaaS call with nothing to drill into.
      **Sharpest P2:** one production call emits **two** `db_system="weaviate"` CLIENT spans on first use
      (`weaviate.connect` as a child of `weaviate.query_objects`), so the connect's ~215 ms is sampled **twice in
      the same p95** and counted as two calls — **and the new one-span-per-door assertion cannot see it**, because
      the fixture pre-sets the client. And the raw-exception surface is **~22 sites, not the 2 recorded** (19
      `traceback.format_exc()` + 3 `{e}`), with a full tenancy message carrying the caller's tenant string
      captured live. Folds into G.24.
      **Out of tree, and it falsifies the guard's headline sentence:** Weaviate round trips outside the class —
      six in the same repo (`utils/migrate_weaviate_collection.py`) and tenant-partition creation in copilot-mro
      (`weaviate_tenancy.py:722/738/741`), **whose own docstring says the raw-client bypass is deliberate.**
      *"Every door into Weaviate"* is true of the class and false of the dependency.

- [x] G.30 **ALREADY DONE — BOTH HALVES — and marked `[ ]`. The checkbox trap, third instance.**
      **(a)** shipped in `core-obsm bbc67ed`; **no docstring anywhere in `core/` or `scripts/` still says
      "handed to the automation's owner"**, and `run_errors.py` already states the honest reason verbatim.
      **(b)** `read_run_error("")` → `None` still holds **and was already pinned** —
      `test_run_error_column_contract.py:1516` covers `""`, `"   "` and `"\n"` at both the reader and the
      `AutomationRun` boundary, with `None` at `:1584`.
      **BUT THE VERIFICATION FOUND SOMETHING THE CORRECTION ITSELF GOT WRONG.** `list_due_retries` — named
      by my brief, by this plan's G.30 text, **and by `core/resources/automations/run_errors.py:15`** —
      **does not exist anywhere in the estate.** Zero hits across three repos except that one docstring
      line. The real function is **`list_retryable_runs`**, and it *does* filter `status = skipped`, so
      **the claim is true and its citation was not.** As the implementer put it: *"this project's
      paraphrase-becomes-fact failure sitting INSIDE the correction written to fix a
      paraphrase-becomes-fact failure."* Fixed at source and now pinned by a test that every cited store
      function actually resolves.
      **The four-link chain was prose only and is now verified and pinned end to end** — one paragraph
      carried four claims across two modules and **nothing checked any of them.** ORIGINAL ITEM FOLLOWS. **Two facts G.21 surfaced that change what the column means, neither asked for.**
      **(a) `core`'s two writes cannot reach a tenant reader today.** Both sweeps filter `trigger = one_shot`;
      a one-shot row is inserted with `automation_id` NULL; `list_runs` — **the only tenant-facing read** —
      selects `WHERE automation_id = %s`; and `list_due_retries` selects `status = skipped`, which a closed
      one-shot row never is. **The implementer's own docstrings said these values are "handed to the
      automation's owner", which was FALSE for exactly the rows they described**, and it corrected them. The
      honest reason to categorise them is column consistency plus the day a surface renders one-shot history.
      **A design fact, not a doc bug** — and it means M-RUNERROR's customer-facing half is entirely api's 29
      sites.
      **(b) `read_run_error("")` returns `None`, not the fallback** — a deliberate behaviour change made on
      review. `NULL` and `''` are the same claim, the dashboard renders nothing for a blank string, and mapping
      blank onto "contact support" would **manufacture a failure notice on a run that never reported one.**
      Flagged for the owner.
- [x] G.31 **A FIFTH sibling-checkout instance, and the first with a reusable answer.**
      **AUDIT 2026-09-20 — VERIFIED DONE.** `grep -rn "sibling_repo(__file__"` across all four merged test
      trees returns **zero executable call sites** — only three docstrings citing the retired pattern.
      Closed by `core-obsm b372640` + the G.52 ports.
      `sibling_repo(__file__, "api")` resolves to the **primary checkout, on `langgraph-merge`, which has no
      `run_errors.py` at all** — so a cross-repo pin written the obvious way would have **silently gated this
      branch against code it never read.** The fix is the pattern to copy estate-wide: **the copy is FOUND, not
      NAMED** — the pin scans sibling checkouts, **requires at least one**, holds every copy it finds, and
      **names the checkout it read in the parametrised test id (`[api-obsm]`) — the cross-repo equivalent of
      reporting `rootdir`.** Companions: my pytest lane, the phase-1c guard's `_utils_root`, G.5's drift pin,
      and the namespace package spanning both checkouts.
      Two documented residual costs: core's unit suite now needs an `api` checkout beside it, and **a sibling
      holding a genuinely stale copy reddens core.**

- [ ] G.32 **G.5's writer sits exactly where the ruling it CITES says an analytics write must not sit.**
      **Dashboard side (review r3, 2026-09-22): FIX-FIRST on P2-1** — the duration histogram, turn latency and tool usage mix panels (`analytics-panel-registry.ts:289/:631/:760`) keep their pre-M-FACTS-FAILURES copy although core `7d5144c` changed what they count (a fast-failing outage pulls p50 DOWN); the "every panel whose meaning changed" box was ticked wrongly. Fix = three sentences + three `assert.match` lines + the Unknown clause (P3-7, core `b2d67f2`). Contract parity with core `b730a95` holds.
      **AUDIT 2026-09-21:** `copilot-mro-obsm copilot_mro/app/db/chat_history/blocks.py:569-572` (working
      tree) **still asserts** *"a gap shows as a dip in the series rather than as quietly plausible numbers"*.
      **Correcting that sentence is safe under EITHER ruling** — it is false for the never-saved class
      whichever way the owner decides — so it need not wait for the decision.
      The review's sharpest finding. `blocks.py:552-563` cites AD-3 Ruling 5 as the precedent for the
      savepoint — and **Ruling 5's own reason runs the other direction**, stated verbatim in
      `tests/unit/metering/test_ledger_write_point.py:247-256`: *"every turn whose block was never persisted
      (a 500 before the save, a stream whose background save timed out, an automation whose block was
      rejected) would go unbooked."* **The facts writer is sited exactly there and inherits exactly that.**
      **Operator consequence:** the Quality and Reliability panels compute failure rates over a denominator
      that **structurally excludes failures.** And the docstring's mitigation — *"a gap shows as a dip in the
      series rather than as quietly plausible numbers"* — is **FALSE for this class**: those turns never had a
      block, so they are **invisible, not a dip**, and the backfill cannot fill them because it reads
      `chat_blocks`. Needs an owner decision: accept the bias and document it honestly, or site a second write
      where a turn is settled rather than where a block is saved.
- [x] G.33 **DONE 2026-09-20 (`copilot-mro-obsm 20ceebe0` tests; production uncommitted). All five cases
      REPRODUCED LIVE against real Postgres 16.11 before any fix, with their SQLSTATEs:**
      `tool_count = 2**40` → `22003 NumericValueOutOfRange`, row missing · `tool_count = "two"` →
      `22P02 InvalidTextRepresentation`, row missing · `query_type = {"a":1}` → psycopg *"can't adapt type
      'dict'"*, row missing · `query_type = ["a","b"]` → **WRITTEN as `'{a,b}'`** · `confidence = 1e308` →
      written as a **309-digit numeric**.
      **CONTROLLER UNDERCOUNT: "three fields cost the row, a fourth corrupts" — it is SEVEN gateable
      columns and TWO corruption sites.** Six more of the same class the plan never named:
      **`capability_outcome` takes both the list and dict shapes identically — a SECOND corruption site
      writing `'{a,b}'`** · `tool_failures` (via `status_counts.failed`) → row missing ·
      `confidence = -5.0`, `latency_ms = -1.0`, `latency_ms = 1e308` all written · a 5000-char
      `query_type` stored in full, **confirming length is not the hazard**.
      **Validation sited in the PROJECTION FUNCTION, not the params builder**, for four reasons in order of
      weight — the file **already gates there** (`answer_found`'s vocabulary check and `_opt_float`'s bool
      exclusion are the same mechanism, so this extends a settled convention); `facts_from_block_data` is
      what the backfill mirrors as ONE unit while the two params builders are two; **gating in the params
      builder would leave the projection dict — what every parity test compares — holding a value the
      database never stored, i.e. it would make the tests lie**; and gating in the writer would protect
      only the online writer.
      **Rejected value drops the FIELD, keeps the ROW** — every gated column is nullable and NULL already
      means "not known for this turn", while dropping the row is the failure this item exists to remove and
      G.32 already records that missing rows bias the panels' denominators. **`tool_count`/`tool_failures`
      are gated AT THE SOURCE**, so a refused scoreboard count still falls through to the count the
      projection derives itself (measured: `"two"` + a 3-tool set → **3**, not NULL).
      **Three columns DELIBERATELY not gated, with reasons in code:** `facts_version` (NOT NULL, and the
      upsert's `facts_version < EXCLUDED.facts_version` predicate — **gating it is the one gate that could
      cost the row**), `citation_count` (minted by `len()`), and the typed identity columns.
      **AND IT FOUND A LEAK IN THE CODE IT WAS EDITING — measured, not suspected.** The writer's failure
      handler held `"error": str(facts_error)`, and **a class-22 bind failure renders the INTERPOLATED
      VALUES LIST**, carrying the turn's `user_id`, `session_id`, `department` and the whole scoreboard.
      **It was introduced by the G.5 writer itself**, and it was `blocks.py`'s only such site. Replaced with
      `failure_fields`, whose docstring cites this exact SQLSTATE class as one it withholds; `blocks.py`
      added to the sweep. ORIGINAL ITEM FOLLOWS. **Three unvalidated fields cost the row; a fourth CORRUPTS it. All live-proved.**
      One `save_block` per case against real Postgres: `tool_count = 2**40` → block kept, **row missing**;
      `tool_count = "two"` → **row missing**; **`query_type = {"a":1}` → row missing (not previously flagged)**;
      and **`query_type = ["a","b"]` → row WRITTEN as `'{a,b}'`, the Postgres array literal — corruption, not
      absence, and not previously flagged.** Also `confidence = 1e308` writes a **309-digit numeric** into a
      column documented "0..1". Live DDL confirms the integer columns and that every varchar is unbounded, so
      **type and range are the hazard, not length.** `answer_found` has a CHECK *and* a vocabulary gate; these
      four have neither.
- [ ] G.34 **A chat delete breaks parity permanently AND retains user data in a relation that is READ.**
      **Dashboard side (review r3, 2026-09-22): PARTIAL** — `deleted-user` is printed raw in Unanswered Questions (P3-4) and a uid-less deleted citation reads "Unknown", not "its id" (P3-5); both in the queued dashboard batch. **copilot-mro r8 (provisional P1 cand):** the settle-time facts writer has no chat-liveness gate, so a delete racing an in-flight turn leaves a personal row — the fix goes in the settle writer.
      Live-proved: after `delete_chat`, `chat_blocks.deleted = true`, the backfill's `WHERE cb.deleted = false`
      yields nothing for that block, and **the facts row survives carrying `user_id`, `session_id` and
      `cited_documents`** — the titles the answer cited. **The panels carry no `deleted` filter** (zero grep
      hits), so a deleted conversation is still counted. **Unlike `chat_blocks`, which is retained for audit and
      filtered out of every read, this relation is retained AND read.** The implementer flagged only the
      panel-counting half. This is a retention question, not just a parity one.
- [~] G.35 **PARITY HALF CLOSED 2026-09-20 by G.25 (`core-obsm bdea4ba`), mutation-proved.** The structural
      cause named here — the constants test compares `FACTS_COLUMNS`, `FACTS_VERSION`, the vocabulary and
      the upsert SQL **but never `facts_upsert_params` against `_as_params`** — is fixed, and **the claim
      that nothing else caught it was VERIFIED before closing**: mutation M7 dropped `cited_documents` from
      the json-serialised tuple and **only the new limb failed**, with core's other 1228 tests and
      copilot-mro's 143 green. **STILL OPEN: the savepoint half** — the ruling is still proved only against
      a hand-written cursor raising a plain `RuntimeError` and a connection whose `commit()` is a counter,
      a stub that cannot model Postgres aborting a transaction; the db lane's four cases remain all happy
      paths. ORIGINAL ITEM FOLLOWS. **The owner's savepoint ruling has no guard against a real connection.** It is proved only against a
      hand-written cursor raising a plain `RuntimeError` and a connection whose `commit()` is a counter — **a
      stub that cannot model Postgres aborting a transaction.** The db lane's four cases are **all happy
      paths.** The reviewer proved the property live (nine consecutive saves, three failing the projection, all
      nine blocks committed); **the repo does not.** Also: three mutation-proved holes survive in the parity
      guard, the structural cause being that the constants test compares `FACTS_COLUMNS`, `FACTS_VERSION`, the
      vocabulary and the upsert SQL **but never `facts_upsert_params` against the backfill's `_as_params`** —
      so dropping a field from the json-serialised tuple survives every test while the two builders produce
      **different rows.**

- [x] G.36 **(d) DONE 2026-09-20 (`dashboard-obsm 79d3bc8`, tests only; 6 production files uncommitted).**
      **THE api ONE-LINER IS NOW SHIPPED (`api-obsm bbbf0fa`) — and the "verify a present consumer first"
      check came back POSITIVE.** `dashboard-obsm/components/features/automations/AutomationNotificationRow.tsx:222`
      **already reads `payload.error`**, and its type declares the field optional *"because the announcer
      does not send it yet"* — i.e. the consumer was written against a field the backend never sent. The
      executor recorder now supplies `error=fields.get("error")`. **Line range REFUTED:** the payload is
      built at `:228-248`, not `:209-229`; the "no `error` key" claim itself was exact. Mutation M5 is the
      proof that the right test guards it — deleting the field fails **only** the recorder test while both
      payload tests stay green.
      Whole suite **2543/2543**, `tsc --noEmit` rc 0, `next lint` clean; **12 mutation proofs**, each with
      the mutation and the failing test id.
      **The `Object.prototype` sweep found TWO LIVE USER-VISIBLE BUGS, both on the path a run's outcome
      travels, both proved RED before the fix:**
      **(1) `RunStatusBadge.tsx:75-87`** — `AUTOMATION_STATUS_META[status] ?? {...}` answered `constructor`
      with the inherited `Object` function; **truthy, so the `??` never fired**, and the badge rendered a
      **blank, colourless label on a run reported normally.** `status` is cast from wire JSON at BOTH call
      sites. **(2) `lib/chat/department-routes.ts:32-40`** — same shape, and the result is used as a
      **ROUTE**, so `function Object() { [native code] }` landed in every href built from a department,
      including the bell's deep link — whose department comes straight off the payload and is
      **lower-cased, which is how prototype members are spelled.** Fixed with the null-prototype idiom
      **already present in the same directory** (`lib/chat/humanize.ts:13`, carrying this exact reasoning)
      — so the idiom existed and the sweep had simply never been run.
      **Controller brief error #25:** I said the bell and panel disagree for **three** reasons. **It is at
      least TEN** — `executor.py:918` forwards `getattr(exc,"reason",None)` under a **bare
      `except Exception`**, whose real vocabulary is `AdMaterializeError`'s seven tokens, so **any exception
      class carrying a string `.reason` is written verbatim into the column.**
      **Honest limit the implementer flagged itself:** the dashboard alone cannot make the surfaces agree —
      the announcer sends no `error` key. The bell no longer echoes a token and is now the consumer the
      convergence needs; **the api-side one-liner that closes it is adding `"error"` to
      `announce_missed_run`'s `payload_json`** (`announcements.py:209-229`). Built ahead of a producer,
      deliberately, and declared.
      **One row carries NO mutation proof and says so** — mutation M9 restored the bare bracket at
      `runOutcomeCopy.ts:352` and **33/33 still passed**, recorded as evidence that no proof is available
      rather than claimed as one. ORIGINAL ITEM FOLLOWS. **What G.22 found in the sibling column, and it is this phase's defect class again.**
      **(a) A SECOND fiction-pinning test my grep could not see.** Beyond the one I named,
      `tests/unit/automations/automationsResponsive.test.tsx:394` located its element **by searching the
      rendered markup for the raw error string** — so it **depended on the leak it should have caught**, and
      its comment described a two-paragraph layout the panel does not have.
      **(b) A live blank-line bug.** `RUN_REASON_COPY[reason]` was a bare object-literal lookup, so a reason
      token naming something on `Object.prototype` returned `Object`, spread to `{known: true}` with **no
      text**, and the panel rendered a **blank line while reporting the outcome as known** — against a module
      header claiming *"no unhandled shape … each lands on a readable sentence"*. Fixed, mutation-proven.
      **(c) `RUN_REASON_COPY` is stale, and its test asserts a fiction.** The scheduler also writes
      `params_invalid`, `requires_worker_mode` and `ad_materialize_failed` — and one site forwards **any**
      error's reason, so **the set is genuinely open** — while the test pinned a 9-token list as exact. The
      test was narrowed to what is true and the three pinned as known-unmapped; **the copy itself is a wording
      decision the owner owns.** The precedence change repairs the user-visible symptom meanwhile.
      **(d) Owner decisions left open:** `data-run-reason` still ships an **unbounded backend-owned varchar**
      into the DOM in the same JSX expression that was just hardened; the notification bell and the panel now
      **disagree for three reasons**, because the bell's payload carries no error category — and the bell's
      ordering puts an **echoed token ahead of the backend's authored sentence**, which is the principle this
      work just established, left unapplied on the other surface.

- [x] G.37 **PAID DOWN 2026-09-20 (`utils-obsm 870e75c` + `776ce89`, 9 uncommitted production files):
      **AUDIT 2026-09-20 — VERIFIED DONE.** `LEAK_BACKLOG` in
      `tests/unit/observability/test_utils_logs_no_exception_text.py` holds **exactly 4** entries
      (`dynamodb_service`, `migrate_weaviate_collection`, `observability/intercept`,
      `observability/log_bridge`); `embedding_service.py:662` is now a constant message. `870e75c`+`776ce89`.
      106 leaks → 40, backlog 10 modules → 4.** Lane **1316 → 1344 collected and passed.** Six modules
      cleaned — `s3_service` 25, `cache_service` 20, `embedding_service` 11, `email_service` 6,
      `smtp_email_service` 3, `llm.py` 1. Ordered **by exposure, not count**, which the executor made
      concrete by taking the **highest-count module LAST**. Its reviewer found **no P0**; 8 of 18 findings
      real, all fixed. ORIGINAL ITEM FOLLOWS., and it names the file its own design copied.**
      Inverting the sweep's default surfaced **106 leaks across ten `utils` modules**, each now in
      `LEAK_BACKLOG` with a dated reason. Two matter more than the rest:
      **(a) `utils/embedding_service.py:428` logs `f"Truncated text: {text[0:500]}"` — FIVE HUNDRED CHARACTERS
      OF THE USER'S QUERY** — plus four `traceback.format_exc()`, and it is called from inside `hybrid_search`
      and `vector_search`, **i.e. on the hot retrieval path.** Verified present.
      **(b) `utils/s3_service.py` is in the backlog — the very file whose span-outcome vocabulary this design
      took as its precedent.**
- [x] G.38 **A half-completed delete was reported as complete, and it is the sharpest defect of the slice.**
      **AUDIT 2026-09-20 — VERIFIED DONE, AND ITS SWEEP WAS EXECUTED.** `utils/weaviate_service.py:98` now
      carries `truncated` in the outcome set; `partial` at `:1031,:1157`; `truncated if capped` at
      `:821,:865,:923,:2109,:2157`. **The estate-wide sweep this item ordered BECAME G.49, G.51 and G.75 —
      so G.38 has nothing left, and dispatching it would re-run a completed sweep.**
      Five doors treated a **default `limit`** as the caller's limit. `delete_objects_by_property` derives
      `total_objects` from the **capped page**, so `deleted_count == total_objects` is **always true at the
      cap**: deleting 10,000 of 50,000 matching objects returned `10000`, logged a completion, and reported
      `success`. Fixed here, but **the pattern — a default cap read as an answer — is worth sweeping for
      estate-wide.**
      **A vocabulary correction the reviewer forced, and it generalises:** the first pass made truncation
      `partial` → ERROR. That is the client-error mistake in the other direction — **a server enforcing its
      configured maximum is the dependency doing exactly what it is configured to do**, and putting it on the
      error-share panel makes the error rate a function of how often somebody exports a large collection.
      Split into **`truncated`** (non-error, for a stop nobody asked for) and **`partial`** (ERROR, only a
      swallowed per-object failure).
- [x] G.39 **Four deferred findings with their elegant solutions named — record as Future Improvements.**
      **AUDIT 2026-09-21 — RECORDED AS FUTURE IMPROVEMENTS** (§6, *"Deferred from Phase G, 2026-09-21"*),
      each with what is missing, why it waits and the elegant fix. **The dashboard exclusion below stays
      OWNER-OWED** and is not closed by this.
      **`WeaviateTenancyError` messages still interpolate the tenant and operator ids**, and copilot-mro
      deliberately re-raises them into the retrieval path, so **any handler up there rendering `str(exc)`
      re-materialises the identity this pass deleted from the logs.** Fix: carry the ids as structured
      attributes on the exception and keep the message generic — **cross-repo, and a message-contract ruling.**
      · The detector **only walks `except` handler bodies**, so a same-module helper taking the exception as a
      parameter is invisible. · A handle **stashed on `self`** evades the door scan; closing it needs
      intra-class dataflow. · The hybrid→BM25 fallback still reports `success` — now at least **visible as
      `weaviate.vector_fallback`, where previously NOTHING anywhere recorded that a retrieval had been served
      without its vector half.**
      **Owner-owed, outside that tree:** a dashboard exclusion for `span_name="weaviate.connect"` — and the
      check that makes it possible is that **`span_name` IS a promoted Tempo label while `db.operation` is
      not**, so it is a panel edit with no code change.
      **PROGRESS 2026-09-21:** M-WEAVIATE-LEFTOVERS (a) DONE at copilot-mro-obsm-panels `dc4bf340` — every fn-dependencies span-metrics selector carries `span_name!="weaviate.connect"`, pinned in test_grafana_dashboards.py; (b) stays with the main lane.
      **(a) iac half DONE 2026-09-21 (`iac 97cae73`, not pushed):** in aws the dependency view is Transaction
      Search driven by `dependencies.json.tftpl`'s text panel, so the exclusion is in that instruction beside
      `span_kind = CLIENT`, with its reason; pinned by words (the test says it cannot run Transaction Search).
      261 → 262.

- [x] ~~G.40 (DUPLICATE ENTRY — superseded; the live entry is the CLOSED one later in this phase, which also refutes the file location asserted below)~~ **`python -m utils.s3_service` DELETES REAL OBJECTS while printing "Would delete". Pre-existing,
      not from this merge, and it needs someone's attention.** Verified by the controller at
      `utils-obsm/utils/s3_service.py:1362-1367`: the comment says *"Delete files containing a keyword (dry
      run first)"*, the call passes **`dry_run=False`**, and the loop below then prints `f"Would delete
      {file}"` — against `s3://flynapse-copilot/akasa/mro/AIPC/processed/`. **The output says one thing and
      the call does the other.** Out of the G.37 mandate and untouched by it; flagged because a destructive
      default behind a reassuring message is exactly the shape this project has spent the night removing.
- [x] G.41 **Two leaks the log sweep structurally cannot see, and one of them was the pass's headline repair.**
      **AUDIT 2026-09-20 — VERIFIED DONE (this item is now a RECORD of fixes already landed).**
      `CONSTANT_MESSAGE_MODULES` exists at
      `tests/unit/observability/test_utils_log_messages_are_not_format_strings.py:224`; `utils/s3_service.py:5-6`
      records the presigned-URL credential leak **in the past tense**, repaired. `870e75c`/`776ce89`.
      Re-confirmed by the G.7 implementer: `s3_service.py:923` is `logger.debug("Parsed S3 URL", bucket=…)` —
      bucket only, constant message, hazard written into the comment above it.
      **(a) The 500-character user-query line had NO GUARD.** The exception-text sweep passed it 21/21,
      because that sweep reads only what a **caught exception** reaches and the line sits in no handler. **The
      most consequential repair of the pass was unguarded**, and the fix was to generalise the file-wide
      constant-message policy (previously weaviate-only) to a `CONSTANT_MESSAGE_MODULES` set.
      **(b) Repairing a handler would have MOVED a leak, not closed it.** The executor's own runtime proof —
      not the sweep, not the reviewer — caught `s3_service.py:875` still logging a tenant-scoped object key
      four lines from the handler being repaired. **A sweep that reads handlers cannot see the line next to
      the handler.**
      **And the credential itself:** `s3_service.py:874/906` logged the whole input value of a URL loader — and
      **on the only reachable failure path that value is an S3 URL, so for a PRESIGNED one it is
      `X-Amz-Credential` and `X-Amz-Signature`: a usable credential in the log.**
- [x] G.42 **s3/weaviate HALF CLOSED 2026-09-20; the count was wrong in BOTH directions.** The plan said
      **AUDIT 2026-09-20 — VERIFIED DONE, AND THIS ITEM'S OWN "STILL OPEN" CLAUSE IS STALE.**
      `grep -c "traceback.format_exc()"`: `s3_service.py` **0**, `weaviate_service.py` **1** (`:543`, a comment
      saying *not* to); `failure_fields` uses 29 / 32. **The dynamodb backlog reason was already rewritten** and
      now reads *"'Retired, unused' … was half wrong: the writer is live"*. `amos_parser.py:2567` confirmed.
      **29** (22 + 7), the controller's brief said **~22**; **measured at HEAD `776ce89`,
      `utils/weaviate_service.py` carried 23 `traceback.format_exc()` + 4 raw-`{e}` f-strings = 27.**
      In the working tree today: **0 `format_exc()` calls** (the one grep hit is a comment explaining why
      not), **0 raw-exception f-strings, 32 `failure_fields` uses, 0 `print(`.** The whole surface is
      repaired, not two of it. **STILL OPEN: the `dynamodb_service.py` reason**, which called the module a
      corpse while `amos_parser.py:2567` imports it inside a live work-orders insert.
      ORIGINAL ITEM FOLLOWS. **Two backlog reasons were FALSE, and one of them prices a live module as a corpse.**
      **`dynamodb_service.py`'s reason said "DynamoDB is retired; the module survives unused."** The
      *table-creation* path is retired — but `copilot-mro-obsm/copilot_mro/app/services/parsers/amos_parser.py:2567`
      still imports it **inside a live work-orders insert** (verified). A failure there can render a botocore
      validation error **naming the offending work-order attribute**. Still last by exposure, but **the next
      pass must price it as a live module.** And **`s3_service`'s reason claimed its failure logs already went
      through the sanctioned shape** — only 4 of 29 did.
- [~] G.43 **The branch is green only with an uncommitted sibling pass present — structural to the convention.**
      **LARGELY RESOLVED 2026-09-21 by ruling M-COMMIT.** Six trees now pass at their own HEAD. The last
      holdout was `utils-obsm`: a clean checkout of `fffa470` gave **81 failed + 11 errors** because 92
      committed tests depended on nine still-uncommitted production files. **Committed as `6848ef7`; verified
      at the new HEAD: 1515 passed, 0 failed**, `utils.__file__` = `/home/aditya/Code/utils-obsm/utils/__init__.py`.
      **Still open: `copilot-mro-obsm`**, whose HEAD `6058e662` is red at its own commit until the WORKOUT
      production fix lands with it — a lane is live in that tree.
      **SHARPENED 2026-09-20, and it is worse than "the ratchets count uncommitted files".**
      A clean detached worktree at `utils-obsm 7f1817f` **could not COLLECT two test files** —
      `tests/unit/cache/test_pattern_delete_reports_failure.py` and
      `tests/unit/observability/test_utils_spans_withhold_exception_text.py` — both `ImportError` on names
      that exist **only in the uncommitted production edits** (e.g. `_embedding_span` in
      `utils/embedding_service.py`). **So checking out a bare SHA in this repo does not produce a runnable
      tree at all**, and the failure is a collection error, not a ratchet count.
      **The consequence for every number in this project: a measurement taken from a bare SHA is NOT
      comparable to one taken in the working tree.** The ~10 deliberate uncommitted files are load-bearing
      for the suite. (This specifically casts doubt on the combined-lane sweep's `1,399 / 1,399 passed` at
      `390a2b83`, which nobody has re-verified.)
      **And the second-order consequence: the committed guards are RED until the production edits are
      committed.** That is the standing convention's direct result, not an oversight — but it means the
      owner's commit is not merely tidy-up; **it is what makes the branch measurable.**
      Applied to a clean `HEAD`, the `utils` guard registry reports **28 offences, every one in
      `weaviate_service.py`**, because a `PAID_DOWN` count was committed at HEAD against a file whose repair is
      **deliberately uncommitted**. **Inherited, not introduced.** It is the cost of "leave production edits
      uncommitted for owner review" meeting a ratchet that counts them, and **the owner should know the branch
      does not stand alone until those edits land.**

- [~] G.44 **CONSUMER HALF DONE 2026-09-20 (`api-obsm bc8e268`), 14 mutation proofs. The PRODUCER half
      **MERGED 2026-09-21 night: core-obsm `obs-merge` `3f1a588`** (g44 fixes `4c4bf6b`, `d8d8325` one-statement `list_tenants_page`). Both halves built; the inert `traceparent` link still waits on G.68. `d8d8325` rides in the next core review.
      **PRODUCER HALF BUILT 2026-09-21 (`core-obsm-g44 563a819`, branch `obs-merge-g44`, review running):** `automation.queue.send` (PRODUCER) around the one INSERT in `claim_run` + `enqueue_one_shot_run`; consumer vocabulary; no `traceparent` (G.68). Merges into `obs-merge` after review.
      **g44 REVIEW MERGE-CLEAN (0/0/5):** parity + tier 0 hold under a real psycopg2 DETAIL error and an 8-thread claim race; small pre-merge fixes in progress, then the core lane merges `obs-merge-g44`.
      **AUDIT 2026-09-21 — "THE PRODUCER IS IN TWO OTHER TREES" IS WRONG.** Every producer funnels through
      **two functions in core**: `core/resources/automations/services/automation_store.py` `claim_run`
      (`:809`, INSERT `:855`) and `enqueue_one_shot_run` (`:1012`, INSERT `:1080`). Callers: api
      `automations/loop.py:1652,2062`; core `automations_endpoints.py:555`; copilot-mro
      `document_hub/job_enqueue.py:69,114`, `data_discovery/job_enqueue.py:59` — **and a SIXTH the item
      never named, `copilot-mro-obsm ad_review_service.py:447`** (`store.claim_run`, `TRIGGER_MANUAL`).
      **So the remaining producer span is a CORE-ONLY change** at those two functions; the `traceparent`
      link write still waits on **G.68**. (The `automation_store.py:935` cited below is stale.)
      is not buildable in api.** **Controller brief error #26, and it was load-bearing:** I briefed "a
      producer span where a run is enqueued". **There is no enqueue anywhere in `api-obsm`** — the
      producers live in `core` (`automation_store.py:935`, `automations_endpoints.py:555`) and
      `copilot-mro` (`document_hub/job_enqueue.py:69,114`, `data_discovery/job_enqueue.py:59`). `api`
      imports `core`; `core` never imports `flynapse_api`, so a shared helper would have to live in
      `utils` or `flynapse-otel`. The implementer built the consumer half and the link-reconstruction half
      and escalated the rest rather than forcing it.
      **Built:** `automation.queue.process` (CONSUMER, claim→settle), a **`Link` not a parent** built
      through the propagator, and three closed-vocabulary instruments — `automation.queue.depth`,
      `.wait`, `.claims`.
      **The depth decision is the one to read.** `automation_runs` is **FORCE-RLS**, so an unbound read
      returns **zero rows with no error** — and an observable gauge's callback runs on the SDK's collection
      thread with **no tenancy binding**, so it would report a **permanent silent zero: the worst possible
      failure for a backlog signal.** Feeding it from a cache is worse, because **the cached number keeps
      being reported after the clock has stopped — the series says "backlog 0" exactly when the scheduler
      has died.** So depth is measured at the tick, which already scans every tenant under a binding; it is
      **not a `COUNT(*)`** but the length of a batch already read, with `queue.scan_truncated` as the
      honesty term.
      **And a fact that falsifies an assumption:** `automation_runs.queue_seconds` already exists and is
      **NOT the queue wait** — it is the wait behind other runs at the tick's concurrency gate. **The real
      enqueue→claim latency had no measurement at all.**
      **semconv, attribute by attribute, with reasons recorded:** `messaging.system` is **deliberately
      unset** — the spec's value set names brokers, and a custom value would make these spans join a broker
      taxonomy and report a message system that does not exist. **STILL OPEN: the producer span (two other
      trees) and the `traceparent` carrier.** ORIGINAL ITEM FOLLOWS. **QUEUES — 0 of 4 boundaries covered. A structural hole no plan item ever named.**
      R.3's finding: the estate has **no message broker**, so the durable queue is the `automation_runs`
      table — and **there is no producer span, no consumer span, no link between them, and no metric of any
      kind.** Queue depth, queue wait and claim contention have **no signal at all**. The producer/consumer
      pair needs an OTel **span link**, not a parent-child edge, because they are different processes at
      different times; that requires the producer's `traceparent` to survive on the row, which may be a
      schema change and is therefore **the owner's call**. Depth is a gauge over a table and must not become
      a per-request `COUNT(*)` on a growing relation. **IN FLIGHT (api side) 2026-09-20.**
- [x] G.45 **DONE 2026-09-20 (`api-obsm bc8e268`).** `api.lifecycle.{startup,shutdown}` phase spans plus
      per-step children over 8 startup steps and 5 drain steps, vocabulary matched to copilot-mro's
      dead-in-production spans so one query reads both runtimes.
      **The design point: `Lifecycle.step` records the failure AND re-raises**, so every existing
      `try/except: logger.error` still swallows exactly what it swallowed — **behaviour unchanged, failure
      no longer invisible.** A failed step is still measured (the timing is in a `finally`), and
      **degraded ≠ failed**: a Weaviate `warn` boot really did start, so it reports `degraded` without an
      ERROR status.
      **Two honest limits recorded at the site rather than papered over:** the telemetry flush sits
      **outside** the drain span by construction — a span still open when `shutdown_telemetry` runs is
      never exported, so **the drain's own trace would be the one thing the flush loses** — and the boot
      span **closes before `create_task`**, because a task created under an open span inherits it and would
      re-parent every tick.
      **ESCALATED:** `core/fastapi_app.py:233-250` — `run_rbac_startup_seed` **swallows its own failures
      internally**, so the new `core_rbac_seed` step span **reads OK even when the seed did nothing.**
      Making a failed seed visible needs a change in `core`. ORIGINAL ITEM FOLLOWS. **STARTUP & SHUTDOWN — 0 of 7, four wholly uninstrumented.** The gateway's entire boot and drain
      sequence is untraced. The only lifecycle spans in the estate (`mro.lifecycle.startup` / `.shutdown`)
      **belong to a runtime that never runs in the served deployment.** The constraint that shapes the fix:
      **a mounted sub-app gets no lifespan**, which is why the gateway sequences `core`'s RBAC seed itself.
      And because startup steps are deliberately best-effort — a raise cannot escape them — **a failing boot
      step must still be recorded on the span even though the process continues.** That is the point of the
      item. **IN FLIGHT (api side) 2026-09-20.**
- [~] G.46 **BACKGROUND JOBS & SCHEDULERS — 0 of 18 fully covered. Not one background boundary in the four
      **AUDIT 2026-09-21:** the copilot-mro GC module path is
      **`copilot_mro/app/services/agent_shared/agent_state_gc.py`** (beside `memory/memory_gc.py`). Both GC
      bodies still open 0 spans, but both run as registered builtins **inside `automation.run`**
      (`api-obsm flynapse_api/automations/tasks.py:201-212`), so they are partly covered. **The one truly
      dark job is `ad_notification_dispatcher`**: its CLI entrypoint `scripts/ad/dispatch_ad_notifications.py`
      opens no span and calls neither `setup_logging` nor `bootstrap` (its request path inherits the
      gateway SERVER span).
      **CORE'S SHARE CLOSED 2026-09-20 (`core-obsm d368c7a`).** New
      `core/resources/automations/sweep_span.py` with a `traced_sweep(name)` decorator on `reap_stale_runs`,
      `recover_stale_one_shot_runs` and `expire_retry_stamps` — trace ROOTS, since the api deliberately has
      no tick span. **Both withholding keywords are the literal `False`, only `type(error).__name__` is
      read, and the status is a bare `Status(StatusCode.ERROR)`.** Notably **`utils.observability.span` was
      deliberately NOT used — it passes neither keyword** (`flynapse_otel/tracing.py:32`), which is G.85.
      The `traceparent` carrier was left untouched (G.68 is owner-gated).
      **Briefed path REFUTED:** it is `core/resources/automations/services/automation_store.py`, not
      `core/resources/automations/automation_store.py`. **Substance confirmed:** `start_as_current_span` /
      `start_span(` over `core/` returned **0** before the change, so this lane set the tree's precedent and
      ported utils' AST sweep to guard it. **copilot-mro's share confirmed still 0** in `memory_gc.py`,
      `agent_state_gc.py`, `ad_notification_dispatcher.py` — reported, not edited.
      core repos emits a metric.** Ten have a span and a correlated log; eight have neither. Spans api, core
      and copilot-mro, so it cannot be done in one tree under the one-implementer-per-tree bound. **api's
      share is IN FLIGHT 2026-09-20; core's and copilot-mro's shares are owed.**
- [~] G.47 **RE-AUDITED 2026-09-20 against the MERGED tree — and the owner gate may not be needed at all.**
      **AUDIT 2026-09-21:** the `signaltometrics/browser` connector exists **only in the copilot-mro-obsm
      WORKING TREE** — `deployment/otel/base.yaml:248` plus all four `backend-*.yaml` overlays; **HEAD
      `6058e662` has none** (`git show HEAD:` count 0 in all five). **And no panel charts any of the 11
      derived series** — `frontend.json`'s browser panels are Loki queries over the raw `browser.web_vital`
      / `browser.app.boot` events, and no `iac` board names them. The residual below stands, now with a
      commit dependency in front of it.
      **DISCHARGED 2026-09-20 WITHOUT THE OWNER GATE (`copilot-mro-obsm aee8d4b1`; the five
      `deployment/otel/*.yaml` + README edits are UNCOMMITTED).** The auditor was right that the gate does
      not apply: **Option A takes no bundle-size and no privacy decision** — the browser gains no SDK, no new
      route and no new attribute.
      **But the mechanism the brief supplied was FALSE, twice over, and the implementer refuted it before
      building:** `deployment/otel/` has **no `connectors:` block at all** — the only span-metrics config in
      the repo is Tempo's metrics-generator (`observability-local/tempo.yaml:58`), exactly as R.4 §1c said.
      **And no span-metrics implementation, Tempo's or the collector's, can promote an attribute VALUE to a
      metric value** — both measure call count and span duration only, so `ttf_token_ms` as a *dimension*
      would be a label over an unbounded numeric domain. "Point it at `browser.chat.turn`" would have
      yielded turn count and duration and nothing else, in one profile of four.
      **Built instead:** `connectors::signaltometrics/browser` (the connector ships in the pinned
      `otel/opentelemetry-collector-contrib:0.160.0`), wired **in both directions in all four** backend
      overlays — 11 instruments, 5 from the chat-turn span and 6 from log records, Core Web Vitals as an
      **exponential** histogram because LCP/INP are ms and CLS is a 0–1 score, four orders of magnitude no
      fixed bucket list fits.
      **Proof it WORKS, not just parses** — *"`validate` alone would have been theatre; `validate.sh`'s own
      header says it never builds a component"*: `validate` exit 0 on the pinned image, the method itself
      mutation-proved (a typo'd key and a bogus OTTL function each give rc=1), **and `validate.sh oss`
      started the collector for real and reached health on all four compositions**, so the connector was
      built and both pipeline halves resolved.
      **The cardinality trap nobody had named is `include_resource_attributes`:** omit it and the connector
      copies the whole browser resource, which carries `user_agent.original` — **one `target_info` series per
      browser build.** It is an explicit 3-key list on every entry and **the guard requires its presence**,
      not merely its contents. No series is tenant-, user- or session-scoped, so **G.17 is not pre-empted.**
      **The G.78 shape was checked and mechanised, not assumed:** the connector runs downstream of
      `transform/browser_allowlist`, so a key that list does not keep is read as `nil` and the instrument
      **silently never records**. The guard derives that requirement from the two blocks TOGETHER and adds a
      limb proving the allow-list can still *refuse* — otherwise a catch-all pattern would satisfy it
      vacuously. Loki recording rules were **deliberately NOT added**: `loki-config.yaml`'s `ruler:` has no
      `remote_write`, so they would evaluate into nowhere — *"adding rules first would have BEEN the G.78
      defect."*
      **`contracts/browser-signals.json` had NO consumer anywhere in the estate** (the `iac` mention is a
      string in a `parametrize` list; the `CATALOGUE.md` mention is prose) — **R.4's flag stands, and this
      guard is its first real consumer.**
      **Orphan accounting, honest:** retires exactly ONE (`browser.chat.turn`), leaves the other seven
      untouched, and **creates 11 new emitted-but-unconsumed families** because no board charts them yet.
      **Net count is worse; net capability is not** — the series could not exist at all before, and in
      aws/azure/newrelic there was no Tempo/Loki path to them either.
      **RESIDUAL (no owner decision in it): panels for the 11 series.** Deliberately deferred — it is a
      coupled edit to `frontend.json` **and** `CATALOGUE.md`, both already modified-uncommitted by frozen
      predecessors, and *"adding a third author to those two files would muddle the owner's review for no
      decision gained."*
      **The merge changed NO OTel mechanism file in dashboard.** Of 31 changed files, exactly one is
      telemetry mechanism (`lib/telemetry/product-events.ts`, which gained a schema version and an optional
      `event_id`). `package.json`, `provider.ts`, `exporter.ts`, `events.ts`, `logger.ts`, `errors.ts`,
      `chat-turn.ts`, `web-vitals.ts`, `sampling.ts`, the three server-side files, `instrumentation.ts`,
      `middleware.ts` and every `app/api/` file are **byte-identical** to the tree R.3 read. **So the merged
      count is 15 / 0 / 9 / 6 — identical to pre-merge, and the estate total of 131 / 46 / 46 / 39 needs NO
      correction.** The auditor recommends keeping R.3's 15 rows as the matrix row for comparability and
      recording its fuller 19-row enumeration as an addendum, **because the four additions are R.3 scope
      omissions, not merge effects, and folding them in silently would make the merge look like it changed
      numbers when it did not.**
      **"Structurally cannot emit a metric" HOLDS — but R.3's stated reason is NOT the operative barrier,
      and the correction changes the owner's decision.** `@opentelemetry/sdk-metrics@2.11.0` **is already
      resolved and present on disk**, pulled in transitively by `otlp-transformer` — so this was never a
      new-dependency decision, and since nothing imports it, it tree-shakes out entirely and **costs zero
      bytes today.** The real barriers are: nothing registers a `MeterProvider`; the bespoke exporter's
      `INGEST_URL_PATTERN` hard-codes `(?:traces|logs)`; and **there is no metrics ingest route on either
      side.**
      **OPTION A — derive the series at the collector, change nothing in the browser.** Every timing the
      dashboard produces **already leaves the browser** as a span or log-record attribute: `ttf_init_ms`,
      `ttf_token_ms`, `total_ms`, `step_count`, `attachment_upload_ms` on `browser.chat.turn`;
      `value`/`delta`/`rating` on `browser.web_vital`; `observed_wait_ms`/`poll_count` on the settle
      events. The collector already runs a **span-metrics connector** (two panels depend on it). Pointing
      it at `browser.chat.turn` plus Loki recording rules yields real series with **no dashboard change, no
      bundle cost, no new route and no new privacy surface.**
      **And the fact that makes Option A unusually strong, verified specifically: `browser.chat.turn` is
      `SpanKind.INTERNAL`, and the sampler keeps every non-CLIENT span — so the 10% drop does NOT touch it
      and 100% of chat turns ship.** The highest-value dashboard timing series is derivable at **full
      fidelity today.** Web-vital and settle records are log records and are not sampled at all.
      **OPTION B — a real browser `MeterProvider` — is a THREE-repo change** (dashboard + core + api),
      needing a metrics serializer, a `/logging/ingest/v1/metrics` route in core and its exclusion entry in
      the gateway. **So the honest framing is not "should the browser get a metrics SDK (size + privacy)"
      but "derive these at the collector from signals already arriving, or produce them in the browser and
      carry them on a third ingest route that does not yet exist." Framed that way Option A needs no size
      or privacy gate at all, and G.47 may be dischargeable without the owner decision it is currently
      blocked on.**
      **One more thing the merge added that R.3 could not have seen:** `contracts/browser-signals.json` —
      a **generated, AST-derived, checked-in producer-side signal inventory** (20 events + 1 span with
      attribute keys and producing modules), whose `state` is derived by scanning for a non-test module
      outside `lib/telemetry/` that reaches an emitter, **so "wired" is evidence, not assertion.**
      **21 of 21 `wired`, 0 dark, 0 exemptions.** It replaces copilot-mro's hand-typed event tuple.
      **It does NOT close R.4's orphan finding** — the contract's own text disclaims that half: `state`
      says nothing about whether a signal is charted, which lives in the consuming repo. **R.4's follow-up
      should read this file rather than R.3's appendix — and someone must confirm the consuming repo
      actually reads that path.** ORIGINAL ITEM FOLLOWS. **DASHBOARD — 0 of 15, and STRUCTURALLY so.** There is **no `@opentelemetry/sdk-metrics` in
      dashboard's `package.json` at all**, so no dashboard boundary *can* emit a metric; every timing in that
      app is a span attribute or a log-record attribute. Adding the metrics SDK to a browser bundle is a size
      and a privacy decision, not just a wiring one — **owner's call before any work starts.**
      **And R.3 never read `dashboard-obsm`**: it was mid-merge under another agent, so every dashboard row
      in the matrix describes the **PRE-MERGE** tree. **The merged dashboard's coverage is unresolved and
      must be re-audited before this item can even be scoped.**
- [~] G.48 **The "fully covered" count overstates what an operator can actually use.** 8 of the 16
      **api half BUILT (`api-obsm 0c176bb`, 2026-09-22):** every Cognito call api makes exports an INTERNAL span; all eight dependencies are now domain-spanned in code (coverage matrix §C). Box waits on api's review.
      **CORE HALF BUILT 2026-09-21 (`core-obsm 542d460`, review running):** `core/resources/cognito_spans.py` wraps all 5 `cognito-idp` calls in utils' `aws_span` (INTERNAL, `rpc.*`, endpoint host, bounded outcome, no ids/claims; replay `UsernameExistsException` = outcome "exists"). 3 mutation proofs. **api half still open** (after api's G.53 batch).
      **utils HALF CLOSED 2026-09-21 (`utils-obsm e6005bd` S3 · `8fea526` SES+SMTP · `f5bc51e`
      `recorded_llm_call`; review running).** S3: all 16 doors via `_traced_s3` on a new shared factory
      `utils.observability.dependency_spans` (`aws_span` / `dependency_span` / `finish_dependency_span` — the
      helper core and api will use for Cognito); INTERNAL over the instrumented transport; no bucket, never a
      key; paginators = one span per door with `storage.listed_pages`; `s3.download` CLIENT → INTERNAL. SES 5
      doors INTERNAL; SMTP one CLIENT span (nothing instruments smtplib) with host+port only. LLM: one
      INTERNAL `gen_ai` span per call, no content, no instruments, never reaches Phoenix (`filter/content_only`).
      **Still open: Cognito (core + api halves).** Suite 1515 → 1657 at `e322954`.
      **AUDIT 2026-09-21 — HALF CLOSED: of the eight, FOUR remain open.** **Closed:** DynamoDB
      (`utils-obsm 099629f`, 17 doors); Weaviate object CRUD + health check and the embeddings span
      (`utils-obsm 6848ef7`) — **but Weaviate's PRODUCTION path is G.28**, the copilot-mro tenancy door, which
      those spans do not see. **Open:** (1) **S3** — 1 domain-spanned method of 23 public
      (`s3_service.py:247`, `download_pdf`); (2) the legacy **`recorded_llm_call`** path (`utils/llm.py`, 0
      span openers); (3) **Cognito**, which lives in **both** api-obsm (`flynapse_api/routers/auth.py`,
      `auth/jwks.py`) and core-obsm (`channel_provisioning/services/cognito_identities.py`,
      `invitations/services/tenant_claim_writer.py`); (4) **SES/SMTP** (`email_service.py`,
      `smtp_email_service.py`, 0 openers each). **Utils lane launched 2026-09-21 for S3, SES/SMTP and
      `recorded_llm_call`**; Cognito spans two trees and is not in it.
      fully-covered external-client rows are covered **only by the urllib3/httpx HTTP fallback** — Weaviate
      object CRUD, Weaviate health check, every S3 operation except `download_pdf`, the legacy
      `recorded_llm_call` span, the embeddings span, Cognito, SES and DynamoDB. Each appears in a trace as an
      **anonymous outbound HTTPS call** with no `rpc.*`, no `db.*`, no `gen_ai.*` and no bucket/key/table/model
      identity. **By the three columns: covered. By "can an operator tell which dependency this was": not.**
      Decide per dependency whether to add semantics or to accept HTTP-only, and record the decision — do not
      leave the matrix implying coverage it does not have.

- [x] G.49 **DONE ALL SIX CALLERS 2026-09-20 (`core-obsm a7b74b3` closes the last three). Core suite
      3080 → 3120, delta reconciled exactly.**
      `TenantService.iter_all_tenants` / `list_all_tenants` now live beside `list_tenants`, contract copied
      exactly **including the delete-race gap** and the `provision_rls.py` quote — **which the implementer
      re-verified at source and corrected: it is one line at `:195`, in the `-obsm` checkout**, not the
      range or the repo previously cited.
      **`core/services/__init__.py`'s real defect was SILENCE, not the cap.** The handler was a bare
      `except Exception` with **no log at all**, so *"a truncated registry and an empty estate produced
      identical output."* The raise is still caught there **and only there** — deliberately, because that
      path is the restart safety net, not a precondition for serving — **but it can no longer be silent.**
      Both RBAC scripts now let it raise: **a migration or repair that cannot enumerate must not run.**
      **THE GUARD IS TWO RULES, AND THE SECOND ONE IS AN EMPIRICAL RESULT, NOT A HYPOTHESIS.** Rule A bans
      a defaulted limit. **Rule B bans calling `list_tenants` outside its defining module.** Mutation M1
      restored `list_tenants(limit=1000)` — **Rule A PASSED, Rule B FAILED.** And the caller-coverage test
      **also passed under M1**, because the stub registry holds 560 tenants and 1000 covers them. *"Only
      Rule B caught it. That is the empirical argument for Rule B existing."*
      **The vacuity attack found the exact hole it was aimed at:** emptying the caller tuple made both
      parametrised tests **collect zero cases and SKIP** — passing — while the set-equality-against-the-tree
      test **failed**. That is why the anti-vacuity half exists.
      **Two honest limits stated rather than overclaimed:** dropping the explicit page limit is a *shape*
      regression that still enumerates correctly via offset and only becomes a defect **in combination**
      with a reader that stops reporting `total`; and *"`list_runs` cannot match a NULL `automation_id`"*
      is **SQL's three-valued logic, not this repo's**, so what is pinned is the predicate — the test
      rejects `IS NULL`, ` OR ` and `COALESCE` appearing in the statement.
      **Cleanup owed, not a defect:** copilot-mro's AD dispatcher built **its own pager and its own
      truncation exception** — correct, but now **a second spelling of the contract that lives in `core`**;
      it can collapse to `list_all_tenants()` and drop the class. And the AD seed script is **deliberately
      not converted, with a written reason** (v1 is single-tenant and the same row is selected either way),
      so **a port of Rule A to that repo will flag it and need an exemption entry.**
      ORIGINAL ITEM FOLLOWS. **api half DONE 2026-09-20 (`api-obsm 7a24dd5`), BOTH P0s closed, 5 mutation proofs. Five
      callers remain in other trees.**
      **Decision: page to exhaustion AND cross-check `total` — because they answer DIFFERENT failures.**
      New `flynapse_api/automations/tenant_registry.py::all_tenant_ids()` pages with an **explicit**
      `limit=500`, de-duplicates, keeps asking while the count says there is more, and **raises** at a
      200-page ceiling or if the finished read holds fewer distinct ids than the count. *"Paging alone
      cannot see a reader that CLAMPS `limit` — the count can; the count alone cannot enumerate."* Both
      call sites read the registry **outside** their per-tenant handler, so a raise becomes a recorded run
      error rather than a half-sweep reported as success — which is what `_scan_every_tenant`'s own
      docstring already promised.
      **Honest gap, written into the module docstring rather than left implicit:** a tenant DELETED between
      two pages shifts later rows forward and one can be missed; offset paging cannot see that without a
      cursor, and both sweeps are idempotent and daily. **What is now impossible is a silent cap.**
      **CONTROLLER CORRECTION #33, and it matters — "legitimately unbound" was TRUE.** In this estate
      **`unbound` means NOT TENANT-BOUND**, and `tenants` is a global-class relation;
      `provision_rls.py` uses the word the same way in the very sentence quoted as the requirement. **The
      false half was "EVERY tenant the tick/sweep serves."** Both docstrings now say which is which.
      **Four more brief errors, all caught (#34-37):** the briefed lane command **cannot run** — with
      `POSTGRES_DB` unset, `conftest.py:109` raises `ProtectedDatabaseError` and nothing collects; **the 41
      "pre-existing" integration failures DO NOT REPRODUCE** (361 passed / 1 skipped / **0 failed**, zero
      credential errors — there is no baseline to discount against); `provision_rls.py` is in
      **copilot-mro-obsm**, not core-obsm; and there are **five** other callers, not four — I omitted
      `copilot-mro-obsm/scripts/ad/seed_ad_notification_subscription.py:70`.
      **THE RECOMMENDATION FOR THE REMAINING FIVE — the shared reader belongs in `core`.** Add beside
      `list_tenants`: `TenantService.iter_all_tenants(status=None, page_size=500)` and
      `list_all_tenants(status=None)`, implementing **exactly** the contract now in
      `api-obsm/flynapse_api/automations/tenant_registry.py` — explicit page limit, page until the registry
      stops answering, keep paging while `total` exceeds what has been seen, **raise rather than return
      short.** Then the five callers become one-liners and api's own helper collapses to a comprehension.
      **Copy the module's docstring: it records the delete-race gap and the `provision_rls` requirement.**
      **Still owed (other trees):** `core-obsm/core/services/__init__.py:104` — **`limit=1000` under a
      comment reading "Ensure EVERY tenant has the bootstrap owner role", the same defect with a later,
      unmonitored ceiling** · two `core-obsm` RBAC scripts · the copilot-mro AD dispatcher and seed script.
      ORIGINAL ITEM FOLLOWS. **P0 — SIX CALLERS SILENTLY SERVE ONLY THE FIRST 50 TENANTS, AND THE DOCSTRINGS SAY THE
      OPPOSITE.** Found by the G.38 estate sweep, **verified at source by the controller 2026-09-20.**
      **The root is one signature:** `core-obsm/core/resources/tenants/services/tenant_service.py:190`
      — `list_tenants(status=None, limit=50, offset=0)`. Its own docstring says it returns *"real
      LIMIT/OFFSET, and a true total count"*, and it does: it runs `SELECT count(*)` and returns `total`
      in the same dict. **All six callers take `.get("tenants")` and throw `total` away.** The honest
      answer is three lines from the lie.
      **And the two api docstrings assert the opposite of what the code does** — `loop.py:1526` says
      *"Every tenant the tick serves… this one read is legitimately unbound"* and `tasks.py:82` says
      *"Every tenant the sweep serves… (legitimately unbound)"*. **Neither is unbound.** This is the
      paraphrase-becomes-fact failure recorded in this project's lessons, in production code.
      **The six, in severity order:**
      **(1) DESTRUCTIVE — `api-obsm/flynapse_api/automations/tasks.py:81-91`**, consumed at `:114` and
      `:165`: both daily retention sweeps (`sweep_expired_state` 03:00, `sweep_archived_memory` 03:30).
      Tenants past the 50th **never have expired `agent_state` rows or archived `memory_items`
      reclaimed — ever** — while both tasks return `reclaimed` and the run records as a success. Ordering
      is `created_at`, so it is **always the same tenants**. This is G.38's exact shape (a half-completed
      delete reported as complete) pointed at the retention contract.
      **(2) `api-obsm/flynapse_api/automations/loop.py:1525-1539`** — tenants past the 50th get **no
      scheduled automation at all**, and `_scan_every_tenant`'s failure counter **cannot see them, because
      they were never enumerated.** The tick reports clean.
      **(3) `copilot-mro-obsm/.../notifications/ad_notification_dispatcher.py:1142-1173`** — tenants past
      the 50th receive **no Airworthiness Directive notifications**, in-app or email. Regulatory-adjacent.
      **(4) `core-obsm/scripts/rbac/migrate_head_roles_to_persona.py:179`** and
      **(5) `core-obsm/scripts/rbac/repair_stale_head_denials.py:173`** — a migration and a repair that
      report done having touched only the first 50 tenants.
      **(6) `copilot-mro-obsm/scripts/ad/seed_ad_notification_subscription.py:70`** — ~~tenants past the
      50th silently unseeded, so they cannot subscribe at all.~~ **REFUTED (G.79, AUDIT 2026-09-21):** the
      seeder takes `tenants[0]`, the OLDEST row, so the cap never changes which tenant is seeded; tenants
      2..N are unseeded **by declared v1 design**, with or without paging. The real defect was a "Done" that
      hid seeding 1 of N — **fixed in the copilot-mro working tree**: the registry `total` is surfaced as a
      warning (`:92-96`). **So five callers were capped, not six.**
      **Blast radius is contingent on the registry exceeding 50 rows** — the sweep did not query a live
      registry, correctly, being read-only. What is certain: the ceiling is 50, it is invisible at all six
      sites, and the true count is discarded three lines away.
      **Fix shape:** do NOT change the default (paging callers depend on it). Give the registry an explicit
      all-tenants reader, or make each of the six page to exhaustion, and **repair the two false
      docstrings.** **Spans three trees, so it cannot be done under one implementer.**
      **IMPLEMENTATION NOTE (review r7b P1-1 + P3-1, `copilot-mro-obsm-r7b 8be6f663` + `1c7db875`,
      2026-09-21):** the "cleanup owed, not a defect" above was a defect twice over. (P1) a registry
      page that FAILED returned `[]` and threw away the pages already read, so the transition fan-out
      dropped every event as "tenant not resolvable" and the evaluate CLI exited 0 — now a failed
      page or import raises `TruncatedTenantRegistryError` (after the handler, chained to nothing)
      and the CLI logs the replay guidance and returns `EXIT_DISPATCH_REFUSED` (3 since review r7b r2
      P3-3, `7a2e5648`: 1 was also the crash status). (P3) the OFFSET
      walk skipped the boundary row under one insert + one delete between pages with the count
      balanced; the dispatcher now calls core's keyset `TenantService.list_all_tenants()` and its own
      pager and page constants are DELETED. **Core docstring now stale (core lane, not fixed here):**
      `TenantService`'s class docstring still says `list_tenants`' default stays for "the AD
      notification dispatcher's own offset pager" — no copilot-mro package module calls
      `list_tenants` any more (the AD seed script still does, by design).
      **IMPLEMENTATION NOTE (review r7b r2 P3-1/P3-2, `copilot-mro-obsm-r7b 69229bb7` + `78303518`,
      2026-09-22):** `1c7db875`'s "missing total belongs to core's suite" was false — core's walk
      accepts a never-counting reader by contract, and a count-less reader stopping at 120 of 437
      was served short. The dispatcher now reads the registry's count itself after the walk and
      refuses a roster with no count, a failed count read, or fewer distinct tenants than the count
      (a signup in the instant between the walk and the count refuses, fail-closed). A reader that
      returns anything but a list of rows (a page dict crashed into the CLI's UNEXPECTED branch; a
      generator was accepted) is the same refusal. Mutation-proved P31N/C/D/E, P32A/B/C.
      **api r8 batch (2026-09-22), Rule B:** `20fb066` (P2-1) — the Postgres test now seeds the twins in both
      orders, asks a strict prefix stored nowhere (must be `None`: `acme.co` never resolves `acme.com`),
      refuses `fetch_all` while an accessor runs, seeds inside its `try:`, and fails two POSED accessors
      (forward `LIKE` prefix, list-then-filter) in-lane; RAN once against `copilot_mro_test`, 10 passed.
      The parse is the boundedness guard, not a "speed bump". `3f0df5e` (P3-9) pins both halves of "both
      readings agree" (RBm1/RBm2 KILLED).
- [x] G.50 **DONE BOTH SIDES 2026-09-20 (`utils-obsm 390a2b8` + `api-obsm f985d8d`), 10 mutation proofs
      across the two lanes.**
      **The api side deviated from the specified shape, deliberately and well:** instead of the inline
      `failed = failed or …` at five sites, **one helper** used by the four multi-pattern sweeps — because
      *"the line has exactly one silent failure mode (assignment instead of accumulation), copying it four
      times makes it wrong four ways, and the helper emits the ERROR line itself, so a site that forgets to
      branch still reports the failure — the signal is not optional."* Mutation M1 is exactly that slip and
      fails four tests. The `sum(...)` that collapsed the outcomes is gone.
      **AND IT FALSIFIED ONE OF ITS OWN ASSERTIONS, which is the part to keep.** The `__str__` hazard was
      measured: without `__str__`, an int subclass with a rich `__repr__` prints the repr through `str()`,
      an f-string **and** `%s`. **But `f"{:,}"` prints correctly EITHER WAY** — `int.__format__` with a
      non-empty spec never consults `__str__`. **So that assertion, in both this test and the utils one,
      pins thousands-grouping and is NOT a witness for this hazard.** It was kept and the test now says so
      explicitly, *"so nobody reads it as a second witness."* ORIGINAL ITEM FOLLOWS. **utils half DONE 2026-09-20 (`utils-obsm 390a2b8`), mutation-proved 3 ways; the api half is
      SPECIFIED and owner-gated.** `PatternDeleteResult`, an **`int` subclass** with a closed four-outcome
      vocabulary — `success`, `miss`, `unavailable`, `error` — reusing the sibling S3 door's own words.
      **The `unavailable` branch previously emitted NO signal at all**; it now warns.
      **The alternatives were rejected on evidence, not taste:** every caller does arithmetic (`+=` ×3,
      `sum()` ×1, `int()` ×1), so a dataclass or tuple **breaks all five at once**; a raise turns a stale
      cache entry into a 500 on a path that today degrades; and **a `-1` sentinel is WORSE than the
      silence — one failure cancels one success inside the same `sum` and the total still looks
      plausible.** Widening the value the way `bool` widens `int` **costs an unchanged caller nothing**, so
      there is no intermediate state in which the estate reads worse than today.
      **AND ITS OWN BACKWARD-COMPATIBILITY TEST CAUGHT A REAL BUG BEFORE THE FIX SHIPPED.** `int.__str__`
      was removed in 3.11 and now falls through to `__repr__`, so defining a richer `repr` **silently
      changed what `f"Invalidated {n} cache entries"` prints** — and `api-obsm/flynapse_api/middleware/
      auth.py:1279` interpolates **this exact value into exactly that line.** Fixed with explicit
      `__str__`/`__format__`, asserted across `str`, f-string, `%s` and `f"{:,}"`.
      **The api change is specified site by site and NOT taken** (another tree): five sites, and
      **`auth.py:1334` must stop using `sum(… for p in patterns)`, which collapses the outcomes and is
      unfixable in place.** The log must branch to a constant-message `logger.error` per G.20.
      **OWNER: should a failed authz invalidation RAISE into the revocation path (fail-closed) rather than
      log?** The safe option is built; raising is a behaviour change on a path that today degrades.
      ORIGINAL ITEM FOLLOWS. **P1, security-adjacent — an authz-cache invalidation that fails entirely reports success.**
      `utils-obsm/utils/cache_service.py:311-328` (`delete_pattern`) returns `0` both on
      `except Exception` and when `self.redis_client` is falsy. Consumers at
      `api-obsm/flynapse_api/middleware/cache.py:222-292` sum into `total_deleted` and log
      *"Invalidated {n} cache entries"*. **A Redis outage during a role or grant revocation is
      indistinguishable from "nothing was cached"** — the revoked role keeps being served from
      `auth_context` / `user_roles` / `operators` for the remaining TTL (300s–3600s), and the log says the
      invalidation succeeded.
- [x] G.51 **utils half DONE 2026-09-20 (`utils-obsm 390a2b8`), lane 1369 → 1399 (+30, reconciled exactly).**
      **AUDIT 2026-09-20 — VERIFIED DONE, AND THIS ITEM'S RESIDUAL IS STALE.** `utils/s3_service.py:501`
      is `get_paginator("list_objects_v2")` (plus `:588`, `:1057`), and `utils-obsm/tests/_root.py:111,128`
      **do** define `sibling_checkouts`/`sibling_variant` — so the clause saying the tree "still lacks
      `sibling_variant`" is false. Closed by `utils-obsm 390a2b8` + the `_root.py` port.
      `list_pdfs` paginates to exhaustion via `get_paginator`, matching its two correct siblings verbatim.
      **THE LESSON OF THE SLICE, and it generalises: a STRUCTURAL guard proves SHAPE, not BEHAVIOUR.**
      The implementer built Guard D, then mutated `list_pdfs` to **open a paginator and read only its first
      page — and the guard PASSED.** So it added a second, behavioural test that runs the door over 2,500
      objects across 3 pages and counts. *"Shape-only would have shipped a guard that a plausible
      regression walks straight through."*
      **Cap decision, and the reasoning is the item's own principle turned on itself: NO cap, not even an
      explicit one.** The return type is `List[Dict]`, which has **nowhere to report that it stopped
      early**, so any ceiling this door enforces is structurally the silent default G.38 is about — *"an
      explicit-but-unreportable cap is the same defect with better manners."* The one caller wanting a
      ceiling already slices the result itself, where it knows the full count. **Changing that needs the
      return shape to change, which is a cross-tree break — owner may overrule.**
      **Three brief-fact corrections (controller errors #29-31):** the non-test `list_objects_v2`
      population is **6 sites, not 4** (the auditor's conclusion still holds — five were already correct,
      so the guard fails on exactly one line); the sibling line numbers shift after the docstring edit; and
      **`list_available_pdfs` is DORMANT — zero callers estate-wide**, so it is a latent trap, not a live
      under-ingest as I briefed it.
      **Guard D's exemption register is kept EMPTY on merit** — `delete_prefix` reads both continuation
      keys and **passes on its own merits, so exempting it would have exempted the exact shape the rule
      exists to require.** Three non-vacuity floors **plus a named witness file**, because *"a count floor
      cannot say WHICH files were read."*
      **STILL OPEN: Guard D has no copy in the other trees** — a cross-repo scan from `utils-obsm` must
      name `copilot-mro`, which is G.52's trap, and **`utils-obsm/tests/_root.py` still lacks
      `sibling_variant`.** ORIGINAL ITEM FOLLOWS. **The rest of the G.38 sweep: 15 further confirmed instances, 2 guards worth building, 1 refused.**
      Full table in the sweep's report. Highlights: `utils-obsm/utils/s3_service.py:472-506` (`list_pdfs`)
      is **the only unpaginated `list_objects_v2` in the estate** — `IsTruncated` and
      `NextContinuationToken` never read — and `copilot-mro-obsm/.../s3_pdf_processor.py:351-411` inherits
      it under a docstring promising *"Process ALL PDFs"*, so a >1000-object manual folder **silently
      under-ingests and reports a completion summary over the truncated set**. Two API endpoints report
      `total=len(items)` (`memory.py:1327`, `improvement.py:288`) — **the sibling endpoint in the same file
      already carries the fix and a comment naming this exact consequence**, and `dashboard-obsm`'s
      `lib/api/memory-api.ts:98-100` **documents the bug from the victim's side.** `improvement.py` caps at
      200 with `le` equal to the default and **no `offset` at all**, so the triage queue is unpageable.
      **Guards recommended: (D)** boto3 `list_objects_v2` only via a paginator or an `IsTruncated` loop —
      4 non-test call sites estate-wide, so it cannot be noisy, fails today on exactly one line;
      **(A)** no call to a paged registry reader may default its `limit` — fails on G.49's six and nothing
      else, non-vacuous **because those readers already compute and return the truth**, so discarding it is
      a decidable, always-wrong act. **Guard (C) — the general `len()`-assigned-to-`total` rule — was
      considered and REFUSED by the auditor as too noisy to be read**, which is the right call and the
      reasoning this project already recorded seven times.

- [x] G.52 **FOUR MERGE TREES NOW BYTE-IDENTICAL (8046 B, md5 `8ebed5c5`) — copilot-mro, core, api,
      **AUDIT 2026-09-20 — VERIFIED DONE for the merged trees, AND THE HEADLINE COUNT IS WRONG.**
      Census by `stat -c%s` + `md5sum`: **8046 B ×4** (the four merged trees, all md5 `8ebed5c5`) · **5358 ×8** ·
      **5418 ×1** (iac) · **4774 ×1** (llm-platform) — **14 copies in FOUR shapes, not "FIVE SHAPES"**, and this
      item's own body already contradicted its headline by calling llm-platform "a FOURTH shape".
      `api-obsm/tests/startup/boot_checks/test_startup_boot_check.py:63-67` now uses `sibling_variant`; **zero
      bare-name sites estate-wide.** The only residual is the lagging non-merged checkouts.
      utils. But the real scope is 14 COPIES IN FIVE SHAPES, not the 5 this item named.**
      Measured census: **8046 ×4** (the merge trees) · **5358 ×8** (`api`, `copilot-mro`, `core`, `utils`,
      and — **named in no plan document** — `flynapse-otel`, `gtm`, `shift-optimizer`, `telegram-bot`) ·
      **5418 ×1** (`iac`, and it still has **no `test_root_anchoring.py` at all**) · **4774 ×1
      (`llm-platform`) — a FOURTH shape that appears nowhere in any plan document.** All six lagging
      checkouts are now recorded in a self-retiring debt pin, each **asserted to still differ** so an entry
      cannot outlive the port it records.
      **THE FINDING THE PORT ALMOST MISSED, and it is the sharpest methodological result of the slice:
      `utils-obsm` had ZERO `sibling_repo(...)` call sites.** A faithful port of the sibling guard *"would
      have read all 66 files, found nothing, and passed — a textbook vacuous guard."* What this tree
      actually had was a **different spelling**: `tests/unit/safety/test_no_provenance_laundering.py`
      resolved siblings as **`WORKSPACE / name`**, scanning the **pre-merge `core`, `copilot-mro` and
      `api` — three of its five repositories at the wrong branch — while certifying that no production
      module launders settings provenance.** **Mutations M2/M3 prove it: under the restored defect the
      bare-name sweep stayed GREEN**, so the ported-as-is guard would have passed straight over this tree's
      only real instance. A second detector (`_workspace_joins`) now sees that shape, and **an unresolvable
      expression is itself an offence** — *"a guard cannot certify what it cannot compute, which is exactly
      how the real instance was spelled."*
      **§1 had to be written a THIRD way, and the number it produced is the strongest evidence yet for
      G.53/G.66.** `utils` is a REGULAR package like `core`, but unlike **both** siblings it has **no
      second mechanism — not one `sys.path` mutation exists anywhere in its test tree** — so the
      `PYTHONPATH` pin is the sole lever. **Run without the pin, the full suite is `1276 passed, 87
      failed, 3 errors` out of 1399 — a 91% GREEN RUN AGAINST THE PRE-MERGE BRANCH.** Any narrower
      selection is liable to be 100% green.
      **`test_root_anchoring.py` now covers both helpers** — the gap this item named verbatim — including
      the longest-prefix split, where *a shortest-first split derives `-mro-obsm`, finds no twin, and
      silently falls back to the primary: the exact wrong answer.*
      ORIGINAL ITEM FOLLOWS. **TWO TREES DONE 2026-09-20 — `copilot-mro-obsm` and now `core-obsm` (`b372640`).**
      `core-obsm/tests/_root.py` is **byte-identical** to copilot-mro-obsm's (`diff` empty, 8046 B) — copied
      **verbatim rather than hand-merged**, precisely because a hand-merge makes a fifth shape. Both
      bare-named sites converted; the false comment rewritten; **the source-text assertion passed first
      time against the merged tree, as predicted.**
      **The port could NOT be copied wholesale, and the reason is a real structural difference:**
      `core` is a **REGULAR package** (`core/core/__init__.py` exists) while `copilot_mro` is a namespace
      package. copilot-mro's guard pins a `sys.path.insert(0, …)` in its conftest; **core's conftest
      deliberately APPENDS** (`tests/conftest.py:68`, with 25 lines of docstring saying prepending is the
      bug), so copying that assertion would have pinned a mechanism this repo **deliberately does not
      use.** Measured: with no `PYTHONPATH`, `import core` → `/home/aditya/Code/core/core/__init__.py` via
      `site-packages/core.pth`. **`PYTHONPATH` is the only lever**, and the guard now pins *that*.
      **The longhand form was decided, not left silent.** `sibling_variant` picks ONE tree and discards the
      rest, which is wrong for the two drift pins that must hold **every** copy so a stale sibling stays a
      signal. The detector only flags `sibling_repo(...)`, so those two would have passed **for the same
      reason a file doing no cross-repo read passes** — a vacuous pass. They are now recorded with reasons
      and asserted to **be** the scan form (`workspace_root` *and* `.iterdir()`) and to name nothing, with
      a detector self-test requiring both halves.
      **STILL OWED: `api-obsm` and `utils-obsm` (`tests/_root.py` still 5358 B and byte-identical to each
      other — one clean `cp` repeated twice, not two merges) and `iac` (5418 B, a THIRD shape, and no
      `test_root_anchoring.py` at all).** Plus `api-obsm/tests/startup/boot_checks/
      test_startup_boot_check.py:59,60,61`, **IN FLIGHT**. And a gap worth naming: `test_root_anchoring.py`
      pins `_root.py` *"byte-identically into every repo"* but **covers neither new helper** — the only
      coverage is the cross-repo guard. ORIGINAL ITEM FOLLOWS. **PARTLY FIXED 2026-09-20, IN ONE TREE ONLY — and the fix created a divergence.**
      While the sweep was writing up, the copilot-mro implementer built the remedy and converted **all 13
      cross-repo sites in `copilot-mro-obsm`**; the auditor re-read it and verified **zero remaining
      `sibling_repo` call sites in that tree**. Two new helpers in `copilot-mro-obsm/tests/_root.py`:
      `sibling_checkouts(caller, name)` (every checkout of `name`, the G.31 hold-every-copy primitive) and
      `sibling_variant(caller, name, *parts)`, which derives the caller's OWN variant **from disk** rather
      than from a hard-coded suffix — the repo dir is split at the longest prefix that is itself a workspace
      directory (`copilot-mro-obsm` → `copilot-mro` + `-obsm`) — and **falls back to `sibling_repo` when
      there is no variant, so it costs nothing in a plain checkout and retires itself when the `-obsm` trees
      go.** A new guard AST-scans for bare-named reads, cross-checks the variant pick against the full
      checkout list, and carries a witness-set non-vacuity check: `tests/unit/infra/
      test_cross_repo_reads_name_their_checkout.py`, **12 passed**. The AD notification contract now reads
      `dashboard-obsm/types/notifications.ts` — 16 passed against the RIGHT tree.
      **THE NEW GAP, verified by the controller:** the helpers and the guard exist in **`copilot-mro-obsm`
      alone**. `grep -c "def sibling_variant\|def sibling_checkouts"` → copilot-mro-obsm **2**, and
      utils-obsm / api-obsm / core-obsm / iac **0**. The five copies of `_root.py` have **DIVERGED** —
      8046 bytes vs 5358/5358/5358/5418 — which is **exactly the failure `tests/_package_stubs.py`'s own
      docstring records**: *"34 copies had already drifted into five different shapes, and a defect fixed in
      one stayed live in the other 33."* **The guard now passes in the one tree that no longer needs it and
      is absent from the three that do.**
      **STILL LIVE — 5 bare-named call sites in 3 files across 2 trees, all reading files that DIFFER:**
      `api-obsm/tests/startup/boot_checks/test_startup_boot_check.py:59,60,61` (pre-merge
      `copilot-mro/copilot_mro/app/main.py` and `core/core/fastapi_app.py`);
      `core-obsm/tests/unit/documents/test_document_cache_scope_key.py:30` (pre-merge
      `api/flynapse_api/main.py`); and `core-obsm/tests/api/automations/test_automation_endpoints.py:922`,
      **whose comment miscalls it "located from this file rather than named"** — prose that will send the
      next auditor straight past it. **The fix is a COPY of a proven mechanism**, not a design task.
      ORIGINAL ITEM FOLLOWS. **P0 — SIX CROSS-REPO TESTS ARE GREEN AGAINST THE WRONG BRANCH, and the close-out gate's own
      method cannot see the class.** Found by the G.27 estate sweep, which **ran tests to prove it** rather
      than reading code.
      **Census (its command, its numbers): 22 executable `sibling_repo(...)` call sites across 18 files.**
      Of the named targets, **six read a file that MATERIALLY DIFFERS from the `-obsm` counterpart** —
      `api/flynapse_api/main.py`, `api/flynapse_api/automations/executor.py`, the whole `api/flynapse_api`
      package (`run_errors.py`, `startup/`, `telemetry/lifecycle_span.py`, `telemetry/queue_telemetry.py`
      exist **only** in `api-obsm`), `copilot-mro/copilot_mro/app/main.py`, `core/core/fastapi_app.py` and
      `dashboard/types/notifications.ts`. Three more are byte-identical today and therefore fragile rather
      than wrong. Affected and **green against pre-merge code**: `core-obsm/tests/unit/documents/
      test_document_cache_scope_key.py` (13 passed), `api-obsm/tests/startup/boot_checks/
      test_startup_boot_check.py`, and four `copilot-mro-obsm` suites including
      `tests/integration/otel/test_alert_rules_layout.py`, which additionally **degrades a missing checkout
      to a `skip`** — so a wrong checkout is a false pass and a missing one is silence.
      **Worst of the six:** `copilot-mro-obsm/tests/unit/ad/test_ad_notification_payload_contract.py:267`
      byte-compares a cross-repo contract against `dashboard/types/notifications.ts` — **branch `agent_sdk`,
      9,418 B, dated Aug 14** — while the merged `dashboard-obsm` copy is 10,470 B and modified today. The
      files **differ** and the test is 16/16 green. **The same file's docstring names this exact trap and
      fixes it only for its own repo**, leaving the dashboard half named.
- [~] G.53 **P0 — the shared venv's `.pth` files put the PRE-MERGE checkouts on `sys.path` before any
      **Round-4 P2s landed (night): api-obsm `7e6e1d5` (refuse an inferred choice that loses to the primary; branches read through rebase/bisect), `b20f84a` (Rule B strips SQL comments), `35fa8c7` (measured per-tree CARRY SPEC + corrected Facts), `2966c5f`/`bac1874` (G.114/G.111 movers).** Re-review then carry. utils `34329ae` already moved its workspace scans to git family + branch.
      **PROGRESS 2026-09-21 (late) — REDESIGN LANDED + REVIEWED CLEAN OF P1.** After three rounds each drew a
      P1 from name inference, api re-planned (`api-obsm/docs/plans/g53-checkout-pin-by-git-family.md`):
      git is the source of truth; one resolver `_root.sibling_choice` (declaration → same-branch sibling →
      name suffix → primary), refuse only a provable mismatch, warn on inferred (`fe2953b`, Rule B `590d114`).
      **Round-4 review: MERGE-CLEAN, 0 P0 / 0 P1 / 5 P2 / 6 P3** — the workspace resolves every `-obsm`
      sibling by branch today. P2s being fixed BEFORE the carry: an inferred mismatch still exits 0 on the
      pre-merge tree (variant-of-variant worktrees, detached HEAD mid-rebase/bisect); a primary caller skips
      the branch rule; the utils hand-off claim was false (a utils refusal test fails under the new `_root`);
      a carried `SIBLING_CHECKOUTS` re-points silently; Rule B blind to SQL comments. **Then each tree's lane
      carries `_root.py` + pin from api's per-tree spec (utils, core, copilot-mro).**
      **AUDIT 2026-09-21 — G.66 MERGED IN HERE** (same root cause; its api evidence — four packages resolving
      pre-merge, the collection error that interrupts the lane — stays under G.66's struck header and is
      part of this item). **Per-tree pin
      state:** `api-obsm` self-pins **only its own tree** (`pyproject.toml:148` pins `.` and `flynapse_api`),
      so `utils`, `core` and `copilot_mro` still resolve through the `.pth` files there;
      **`utils-obsm` and `core-obsm` set no pytest `pythonpath` at all.** **The utils own-tree pin is in the
      utils lane launched 2026-09-21.**
      conftest runs.** `flynapse_utils.pth`→`/home/aditya/Code/utils`, `core.pth`→`/home/aditya/Code/core`
      (branch `master`), `mro_copilot.pth`→`/home/aditya/Code/copilot-mro`, `flynapse_api.pth`→
      `/home/aditya/Code/api`. **`utils`, `core` and `flynapse_api` are REGULAR packages, so first-hit-wins
      with no per-submodule merging** — only `PYTHONPATH` can move them; `copilot_mro` is a PEP 420
      namespace package and is obsm-first **only** because `copilot-mro-obsm/tests/conftest.py:44-47`
      inserts the repo root at `sys.path[0]`. **`utils-obsm/tests/conftest.py` does nothing to `sys.path`
      at all** and `api-obsm/tests/conftest.py:50-100` appends rather than prepends.
      **Consequence, proven both ways:** without `PYTHONPATH` a test touching a NEW symbol errors loudly
      (`ModuleNotFoundError: No module named 'core.resources.automations.run_errors'` — a module that
      exists in `core-obsm`), but **every test touching a symbol both trees share passes green against the
      wrong tree, silently, and nothing in those suites asserts which tree was read.** This is the
      seventh instance of the sibling hazard and the one with the widest radius.
- [x] G.54 **The close-out gate's method is BLIND to a whole defect class, by construction.**
      **MERGE ATTRIBUTION SETTLED 2026-09-21 — MOST OF THE 152 WERE THERE BEFORE THIS BRANCH.**
      A read-only auditor ran each pre-merge sibling as a control. **The comparison is fair by construction:
      each sibling is the EXACT merge-base of its `obs-merge` branch, 0 commits behind** — copilot-mro
      `417df303` (77 ahead), api `44bd8d1` (21 ahead), utils `289ba71` (15 ahead), core `e10a9ce` (20
      ahead) — so anything present in a sibling is pre-existing by definition. **All four siblings were
      unchanged start to end, so every control number is valid.** It checked out no SHA (a bare SHA is not a
      runnable tree here); the siblings' only uncommitted edits are docs.
      | Cluster | Verdict | Evidence |
      |---|---|---|
      | **G.88a** `ensure_package` sets no parent attribute, never restores | **PRE-EXISTING** | `_package_stubs.py` byte-identical in both trees; `08e8380a` (2026-08-13) is an ancestor of the merge-base; the whole pre-merge suite shows the same `AttributeError` signature |
      | **G.88b** the `__file__ is None` sweep deletes the real namespace package | **PRE-EXISTING** | file byte-identical; `git log -S` → `e0d0878b` (2026-06-26), an ancestor |
      | 13 in `tests/db/improvement` | **PRE-EXISTING** | exactly 13 errors in the pre-merge whole suite; 49 passed alone |
      | **32** in `test_pipeline_lifecycle.py` | **MERGE-INTRODUCED — a new victim of the old defect** | branch commit `248590dd` added an autouse fixture monkeypatching `"copilot_mro.app.services.agent_shared…"` **by string**; the pre-merge file has 0 such references and is green |
      | **6 api** (semconv latch) | **MERGE-INTRODUCED failures; PRE-EXISTING production defect** | pre-merge api whole suite **1133 passed, 0 failed**; the branch's new test lanes latch the default mode first. Already retired at `bbbf0fa`; the production half closed in `flynapse-otel af40bbe` |
      | 7 multi-arg `conftest` collisions | **UNDECIDABLE — could not reproduce** | 11 directory pairs probed across four repos, 0 collisions; needs the sweep's exact argument vector |
      | 7 order-dependent | **UNDECIDABLE** | the sweep recorded no test IDs |
      **TOTAL: ~105 of 152 PRE-EXISTING (revealed, not caused, by this branch) · 38 THIS BRANCH'S (32 + 6),
      both with a named cause and both already fixed or in flight · ~9 undecidable.**
      **Side findings that change other numbers:** (1) **another agent's `g88_before.txt` (187 red) resolved
      `utils` to the PRE-MERGE checkout on 22 errors** — `pattern_delete_failed` exists only as an uncommitted
      `utils-obsm` edit — so G.88's "before" count is overstated by 22 if that file is used; routed to the
      copilot-mro lane. (2) **Four `test_workout_tool_adapters.py` failures are G.88 victims, NOT G.86** — same
      IDs in both trees. (3) The 13 `db/improvement` errors pass per-directory only at level 2; **at level 1
      `tests/db` is red even pre-merge**, because the polluting file sits inside `tests/db`.
      **MEASURED AND ANSWERED 2026-09-20 by a read-only whole-suite sweep (~180 pinned invocations,
      `rootdir` asserted on every one, module resolution asserted before any number was trusted).**
      **THE NUMBER: 152 checks are green under the gate's method and red when their repo runs in one
      process** — 146 in `copilot-mro-obsm`, 6 in `api-obsm`, **0** in `core-obsm`, `utils-obsm`, `iac`, and
      structurally 0 in `dashboard-obsm`. **The control that makes the comparison fair: reconstructing the
      gate's granularity reproduced the gate's published number exactly** (18 failures in copilot-mro-obsm,
      where the same tree in one process is 119 failed + 47 errors).
      **Two of the 152 are live PRODUCT defects, not test hygiene — see G.86 (P0) and G.87.** The rest trace
      overwhelmingly to G.88's two lines of test support.
      **A FOURTH class the item did not name — multi-arg-only, and it is the veto on the cheap middle
      option:** naming two directories in one invocation collides their `conftest.py` files on the module
      name `conftest` and **aborts the session with 7 collection errors** (3/3, both orders) — **invisible in
      both the single-directory run and the whole-suite run.** So a grouped gate would fail loudly on a
      defect that exists at neither granularity while still missing part of the class it was meant to catch.
      **RULING TAKEN: one invocation per repo over the whole `tests/` tree, one argument per invocation, AND
      KEEP the per-directory lanes** — they catch the opposite direction (9 checks red at level 1, green
      everywhere else). **Cost is roughly nothing: whole-suite is FASTER than the per-directory sum in four
      of five repos** (−15 %, −46 %, −63 %, −49 %) and +23 % in copilot-mro-obsm; estate-wide **+5 minutes**.
      Per-invocation interpreter overhead is 1.8–2.1 s, so the gate's ~48 invocations already spend ~1.6 min
      on startup alone — **and finer granularity costs MORE while hiding more** (level 2 is 17 % more
      expensive than level 1 for the same 6,202 tests, and is the granularity that hides the most).
      **A hazard the gate's authors must know: `copilot_mro_test` is shared mutable state across pytest
      invocations.** The lanes are independent only because they run serially; the sweep manufactured 18
      phantom errors against itself by parallelising and caught it only by re-running alone.
      **What was NOT established, stated plainly: whether the 152 are merge-attributable.** No pre-merge
      sibling controls were run — the single highest-value follow-up. The two that WERE traced both are.
      **Two retractions the sweep made against itself**, each worth keeping as method: 6 `core-obsm` failures
      and 31 `copilot-mro-obsm` errors were **its own concurrency and a live implementer's mid-lane write**,
      caught only by re-running behind a `find -newermt` fence. **A number taken while another agent is
      writing the tree is not a measurement.**
      `observability-close-out-status.md` §2 runs **one invocation per test DIRECTORY**. The sweep proved a
      defect that is **green in every per-directory run and RED in a two-directory run** — reproduced 3/3:
      `copilot-mro-obsm/tests/registries` alone 177 passed, `tests/unit/memory` alone 168 passed,
      **combined 1 failed, 344 passed**. The failing test
      (`tests/unit/memory/test_memory_gc.py:459`) asserts on `sys.modules`, **a process global no lane
      owns**, so green proves nothing and red blames the wrong lane — and production concedes the premise
      at `memory_gc.py:97`. **The gate needs at least one whole-suite-per-repo invocation** or this class
      stays invisible. Recorded because it changes what the gate's 19,495/19,637 actually certifies.
      **Also from the same sweep, unfixed:** `copilot-mro-obsm/tests/db/tenancy/test_ad_fleet_scope_live.py:484`
      **pops `utils.postgres` instead of restoring it** — the exact G.27 shape, in a live production dotted
      name; **8 loader sites** leave a path-loaded copy under a real dotted name and pop only on exception;
      **4 absence guards scan with `rglob` and assert `violations == []` with no floor**, so they are
      vacuous the moment a directory moves; a **broad-`except` module-level skip** turns a genuine
      connection defect green; and **8 tests skip for a script that was never committed** yet count as a
      green file. The recommended guard is a **combined-lane `sys.modules` sentinel** with a planted-leak
      self-test — *"a sentinel that never fires and a sentinel that cannot fire look identical."*
      **`iac` has no `test_root_anchoring.py`; `dashboard-obsm` has no TS depth or layout guard at all.**
  **G.25(a) — the moment it was fixed, watched by an auditor (detail retained here; the item itself is
  closed above).** The auditor proved the drift pin defective at
      20:00-20:11 — `python -vv` showed it importing `/home/aditya/Code/copilot-mro` **with the merged
      `PYTHONPATH` set**, because `_ensure_package` sets `__path__` explicitly and **overrides `sys.path`**
      (the pin could not have been fixed by `PYTHONPATH`) — 28/28 green against a tree whose
      `chat_turn_facts.py` is 9,849 B and **has neither `facts_from_block_data` nor `FACTS_UPSERT_SQL`**
      (obsm's is 20,069 B). At 20:15 the core implementer's rewrite landed and the auditor re-read it:
      **29 passed**, with `test_the_checkout_read_is_the_one_this_test_id_names[copilot-mro]` /
      `[copilot-mro-obsm]`, `test_the_loader_puts_back_the_modules_it_borrowed`, and three
      `..._is_not_vacuous` tests. The sweep calls it **the estate's best exemplar** of the found-not-named
      pattern. Uncommitted.

- [x] G.55 **DONE 2026-09-20 (`core-obsm b372640`, test-only commits). ALL 13 RATCHET ENTRIES CLOSED, 0
      survive** — first run after porting: `NEW: []`, `REPAIRED: [all 13]`. Analytics 119 → **147 passed**;
      whole suite **3055 collected / 3051 passed**.
      The seven column gates were **reproduced from the registry, not re-derived**. Value contract matches
      exactly — a rejected value **drops the FIELD, keeps the ROW**. **Reporting deliberately differs:** the
      writer logs one warning per degraded turn, right for a request path; **the backfill sweeps whole
      tenants, where a line per turn is a flood that hides its own total**, so it tallies and prints one
      summary line, column names only, closed vocabulary, never a value.
      **THE SHARP PART, and it is a correction to the ratchet's own design:** equality alone was **not
      sufficient** — *"two halves that both STOPPED gating compare equal exactly as two halves that both
      gate do."* So the ratchet was not deleted; it **changed sides**, from recording the defect to
      recording the **repaired property**: the `on_reject` sets are read from **both** halves and required
      identical. Mutation-proved by recording a gate neither half has.
      **And one of the 13 was never a refusal:** the over-long `session_id` is a **CAP, not a drop** —
      `_opt_text` truncates to 200 and `on_reject` never fires. The old list conflated them because *"core
      writes 5000 characters, the registry writes 200"* is a disagreement whichever way the gate resolves
      it. **The record is now 12 refusals + 2 capped controls, asserted BY VALUE**, so "everything
      malformed is refused" cannot be what the file really asserts.
      **Controller baseline correction:** the whole-suite figure I relayed ("3012 collected / 2429
      selected / 2429 passed") **does not reproduce — nothing is deselected in this lane.** It was
      3012 collected / 3008 passed / 2 skipped / 2 xfailed.
      **HANDED OFF to the copilot-mro lane:** `copilot-mro-obsm/tests/unit/chat_history/
      test_chat_turn_facts_value_gates.py::test_the_backfill_mirror_has_not_adopted_the_gates_yet` is now
      **RED BY ITS OWN DESIGN** — *"This test FAILS when core catches up. That is its job: the fix is to
      move these shapes into `_PARITY_SHAPES` and delete this section, not to loosen it."*
      ORIGINAL ITEM FOLLOWS. **G.33's `core` half — the backfill is STILL WRITING THE ROWS G.33 CONDEMNED, one release
      behind the fix.** Found by the G.25 implementer **beyond its brief**, and it falsifies a property the
      drift pin exists to assert. copilot-mro's registry `facts_from_block_data` has been **hardened**
      (`_opt_text`, `_opt_count`, `_opt_probability`, `_opt_duration_ms`, `_checked`, `on_reject`) gating
      **seven columns**; `core-obsm/scripts/backfill_chat_turn_facts.py` gates **none**. **Measured over 14
      shapes, 13 disagree** — including the two G.33 proved live: `tool_count = 2**40` (registry `None`,
      backfill `1099511627776` — **the row that is LOST**) and `query_type = ["a","b"]` (registry `None`,
      backfill the list that binds as a Postgres array literal — **the CORRUPTION case**). Also
      `confidence = 1e308`/`7.5` writing a 309-digit numeric into a column documented `0..1`, plus
      `session_id`, `capability_outcome`, `tool_failures` and `latency_ms`.
      **So the backfill is NOT gap-filling rows indistinguishable from the writer's.** Rather than hide
      this, the implementer **enumerated the 13 pairs as a two-way ratchet** with a control shape — a pair
      appearing is new drift, a pair disappearing means the mirror was repaired and the entry is deleted —
      so **the ratchet is the worklist and "done" is the list reaching empty.** **IN FLIGHT 2026-09-20.**

- [x] G.56 **DONE 2026-09-20 (`dashboard-obsm 3efba84`, tests; 22 production files uncommitted). 29 tables
      **AUDIT 2026-09-20 — VERIFIED DONE.** Guard present at
      `dashboard-obsm/tests/unit/lookups/prototype-lookup-tables.test.ts`; committed `dashboard-obsm 3efba84`.
      The owner residue was split out and is tracked as **G.77**, not here.
      fixed, 18 recorded with dated reasons, 0 unnamed. Lane 2543 → 2557, reconciled exactly.**
      **It censused by AST, not grep, and ran the SAME instrument at HEAD, at the inherited tree and after
      every change — so the before/after numbers come from one measurement: 49 bare tables → 18.**
      **THE PLAN'S OWN TEXT WAS INCOMPLETE: `in` does not protect either.** This file said only that `||`
      and `??` fail. **`'constructor' in {}` is `true`** — `in` walks the prototype chain. The one site
      using it routed a stored category of `constructor` into the **capability** breakdown, read the
      inherited function as its label, and **threw out of the tie-break comparator** — `localeCompare` on a
      function — **taking a pure function and the memory page with it.**
      **CONTROLLER BRIEF ERRORS #38-40, all caught:** **two of my three "crash sites" cannot crash** — both
      bucket by a normalizer whose output vocabulary is closed, so the init branch can never be skipped;
      **the real defect is one function upstream, which my brief listed in the BLANK class.** There is a
      **FOURTH crash site I did not list** — `DiscoveryPrimitives.tsx:144`, where `types/data-discovery.ts:214`
      **types the field `DiscoveryQualityNoteKind | string`, so the contract says outright that an unlearnt
      kind can arrive**; reverting gives `Element type is invalid … got: undefined`. And **the `lookupOwn`
      helper I said was "named but declined" ALREADY EXISTS** at `runOutcomeCopy.ts:234` under the name
      `lookup` — **and the predecessor used three different idioms**, not the one I named.
      **Two crashes reproduced, not argued:** `TypeError: groups[cap.group].push is not a function` thrown
      during render — **the role-editing page white-screens** — on a key served by core's `/authz/catalog`;
      and the quality-note icon rendering `undefined` as an element type.
      **IT CAUGHT ONE OF ITS OWN ASSERTIONS PASSING FOR THE WRONG REASON**, and only the mutation found it:
      `markup.includes('Constructor')` was satisfied by a **different entry's** label (`Sql Constructor`).
      Tightened to the exact pair. *"Exactly the failure mode the method note exists for, one level in."*
      **The guard is an AST scan, and the precedent was already in this repo** (`logger-message-constant.test.ts`
      uses the TypeScript compiler with a planted-source self-test and a call floor) — *"a regex over TSX
      would have been the eighth vacuous guard; an AST scan is not."* Inverted default, **shrink-only
      backlog** (an entry naming nothing also fails, so a repaired table must delete its entry), **two
      independent floors** — and the second is the clever one: **`repaired > 15` asserts the scan still
      RECOGNISES the repaired form, so a scan that had quietly stopped understanding the file cannot look
      identical to a clean one.** Blind spots are **written down rather than implied**, and both
      under-report, never over-report.
      **IT RECOMMENDS AGAINST the shared `lookupOwn` helper**, and the argument is good: the
      declaration-site repair **dominates** it — total (it covers reads written later by someone who never
      heard of the helper), already the repo's idiom, and **decidable**: *"is this table null-prototyped?"*
      is one declaration, whereas *"does every read go through `lookupOwn`?"* means chasing aliases and
      parameters. Owner may overturn. ORIGINAL ITEM FOLLOWS. **~30 more `Object.prototype` lookup sites in dashboard — and THREE of them CRASH rather than
      blank.** The G.36 sweep classified every bare bracket lookup on an object-literal map across
      `components/ lib/ hooks/ utils/ types/ contexts/ app/`, fixed three, and left the rest with a
      per-site reachability judgement it declined to invent alone.
      **The crash class, worth the owner's attention above the rest:** `PersonaCapabilityEditor.tsx:105`
      (`(groups[cap.group] ||= []).push(cap)`), `pdf-referred-by.tsx:132-136` and
      `pdf-references.tsx:138-142` (`if (!grouped[type]) grouped[type] = []; grouped[type].push(...)`) —
      **the truthy inherited function skips the init, then `.push` on a function THROWS**, so a
      backend-supplied key is a **component crash**, not a blank.
      **The blank class: ~27 sites**, led by `MessageProgressTrace.tsx` with **twelve**, keyed on the
      backend trace JSON's own detail keys. A function rendered as a React child is blank, as a `className`
      is unstyled, in arithmetic is `NaN` — and **`||` / `??` fallbacks do NOT protect, because the
      inherited value is truthy.** That is the whole trap.
      **The complete solution the implementer named but did not build:** a shared `lookupOwn(table, key)`
      plus the inverted-default guard pattern G.24/G.37 established in `utils` — every bare bracket fails
      unless the site is named in a backlog **with a reason**, so the list only shrinks. It deferred on two
      honest grounds: the ~30 reasons are product judgements, and **a regex guard over TSX is itself a
      candidate for this project's eighth vacuous guard.**
- [x] G.57 **DONE 2026-09-20 (`api-obsm f985d8d`, tests; 13 production files uncommitted). Lane
      1466 → 1526, reconciled exactly. All SEVEN tokens ruled, not just the two named.**
      `materialise_busy` → **`unavailable`** (the lock was briefly held and it refused before touching
      anything — *"the one category whose point is do not escalate"*, with an existing precedent in the
      same file). `no_verdicts` → **`configuration`, NOT `no_answer`** — and the reason is sharp:
      *"`no_answer`'s own sentence is 'the assistant produced nothing usable — reword or run it again';
      there is no assistant on this path and re-running is precisely what will not help. `configuration`
      is the category that says it will not fix itself and nobody else can fix it for you."*
      Five kept `internal` **as a stated judgement**, not by default: `pair_refused` covers **three causes
      with three different answers that the token does not separate**, so splitting it needs the runner to
      say which.
      **THE UNANTICIPATED FIND, and it changes what we thought was silent.** Naming the tokens as `REASON_*`
      constants made them visible to a **pre-existing** drift guard, which **immediately failed on all
      three** — a true positive on a pre-existing gap: `materialise_busy`, `no_verdicts` and
      `ad_materialize_failed` **have been reaching the owner's BELL all along**, wearing the generic
      *"something went wrong while it was running"*. The literals were simply invisible to the guard.
      Three bell-copy rows added — and the implementer named the alternative and refused it:
      **"renaming my constants to dodge the guard is the quiet weakening CLAUDE.md forbids."**
      **A structural constraint found the hard way and respected at full strength:** its first version used
      one `record()` with a conditional `error=`, and a pre-existing sweep **failed it** — `token` derives
      from `getattr(exc, "reason", None)`, so the taint pass treats it as the exception's text, and that
      sweep also demands a **literal** category at the `error=` keyword. **Both refusals are correct in
      substance** (G.58: any exception with a string `.reason` lands there verbatim), so it **restructured
      rather than exempting anything.**
      **Controller brief errors #42-44:** `ad_materialize.py` is in **api-obsm**, not copilot-mro (the
      plan had it right; my brief mis-attributed it) · **six** runner tokens, not seven — the seventh is
      what the executor writes for a non-runner exception · line numbers off. ORIGINAL ITEM FOLLOWS. **TWO AD reasons are mis-categorised at the source, and the dashboard CANNOT repair it.**
      The G.36 implementer checked all ten unmapped reasons against their write sites and recommends
      **adding no copy rows** — because the precedence work it just landed means a reason row now
      **outranks** the error category, so adding copy *demotes* the category's sentence.
      **But two are genuinely mis-served, and the fault is upstream.** Verified at
      `api-obsm/.../ad_materialize.py:98-102, 214-222`: **`materialise_busy` means *another materialise
      holds the lock; press again when it finishes*** — a benign, self-healing concurrency refusal — and
      **`no_verdicts` means *there is nothing to act on; run Phase B for the pair first*.** Both are filed
      at `executor.py:918-923` as `RunErrorCategory.INTERNAL` with the constant detail "the AD materialise
      run failed", under **a single catch-all over the whole `AdMaterializeError` family**.
      **So the dashboard tells the reader "something went wrong on our side, contact support" when nothing
      went wrong and the reader has a concrete next step.** The category vocabulary's own stated test —
      *what should the reader do next?* — is failed for at least two of its inputs, and **the dashboard
      cannot fix it, because the category is all it is given.**
      **Recommended api-side ruling: split that handler** — `unavailable` for `materialise_busy`,
      `no_answer` or `configuration` for `no_verdicts` — **before any dashboard copy is written.**
      Draft sentences for both are in the G.36 report if the owner wants rows anyway.
- [x] G.58 **DONE (M-RUN-REASON) — `dashboard-obsm 5265cbc`, not pushed:** `runReasonAttribute` (token / `unrecognised` / absent, shape-gated) at both sites; unit 2578 → 2584, typecheck + lint clean, 5 mutants all red with byte-identical restores. ORIGINAL ITEM FOLLOWS.
      **FOLLOW-UP `dashboard-obsm a46c7dc` (not pushed):** the same gate on the VISIBLE copy — `runOutcomeCopy` step 3 echoes only a token (fixed sentence otherwise; `MAX_ECHOED_REASON` deleted as dead), and the AD review note shows category copy / token / fixed sentence, never stored `reason`/`error` text; unit 2589 → 2594, 3 mutants red, byte-identical restores.
      **`data-run-reason` — TWO sites, not one, and the risk is now concrete.** Correction to the
      earlier framing: `RunHistoryPanel.tsx:190` **and** `AutomationNotificationRow.tsx:289`, both
      unbounded, both untrimmed. `executor.py:918` writes `getattr(exc,"reason",None)` from under a bare
      `except Exception`, so **the column is not restricted to this estate's tokens** — any exception
      carrying a string `.reason` lands in it verbatim, and from there into the DOM of every screenshot.
      Same disclosure shape G.22 closed for `error`.
      **None of the three options considered is both safe and lossless** — dropping it loses the only
      machine-readable trace of exactly the unlearnt tokens support needs; bounding it caps size but **a
      120-character prefix of an exception is still an exception in the DOM**; mapping through the known
      set closes it but goes blind on the ten-plus unmapped tokens, which is the whole use.
      **A fourth option satisfies both and is this repo's own settled pattern:** gate on SHAPE — emit the
      token when it matches `/^[a-z0-9_]{1,64}$/`, the `unrecognised` sentinel when a reason is present but
      does not match, nothing when there is none. **Every real token is snake_case and passes; free text
      and exception strings cannot.** It is `runErrorAttribute`'s three-state design applied to the sibling
      attribute. ~15 minutes and one shared helper. **Still the owner's call, because it is a decision
      about what a support screenshot may show.**

- [ ] G.59 **A test is RED at committed HEAD in `copilot-mro-obsm`, and it is not in the uncommitted set.**
      Found by the utils implementer while running consuming suites, out of its own tree and correctly not
      touched: `tests/smoke/document_hub/test_document_hub_package_import.py::
      test_no_module_imports_the_vector_index_at_module_scope` **fails at HEAD `5893fd04`** because
      `copilot_mro/app/services/document_hub/reindex.py:82` has a **module-scope
      `from .indexing import ...`**. Committed state, unrelated to this merge's working-tree edits.
      Consuming suites otherwise **694/695**. This matters beyond the one test: the close-out gate's estate
      numbers were computed against these suites, so a red at HEAD needs either a fix or an explicit entry.
- [x] G.60 **RULED + BUILT 2026-09-22 (M-WEAVIATE-REFUSAL, owner A3 "confirm + split failures"; controller call: the never-raised utils subclass deleted `26e7126`, a missing collection is a failure `2a8f2f48`).** **OWNER: confirm a ruling that was TAKEN rather than escalated.** The controller's brief told the
      **AUDIT 2026-09-21 — RULE G.60 BEFORE G.28.** G.28's fix spans the copilot-mro tenancy doors
      (`collection_handle`, `collections_for`, `weaviate_connection`), and `collections_for` reaches
      `tenant_keys_for`, which raises `WeaviateTenancyError` (`weaviate_tenancy.py:219,227`). **So G.28 moves
      the tenancy raises INSIDE traced code — exactly the precondition this ruling's safety note depends on**
      (`utils-obsm weaviate_service.py:388-393`, tuple `:397`). Built first on that classification, it would
      report provisioning failures as `invalid_argument` non-errors.
      utils implementer to leave `WeaviateTenancyError`'s classification as a separate owner ruling. **The
      prior pass had already ruled it** — it is now `invalid_argument`, a non-error, with the reasoning
      written out at `weaviate_service.py:381-397`. The implementer flagged this rather than let it pass
      silently, and **agrees with the ruling**, but recorded the one condition that would break it:
      **`WeaviateTenancyError` is ALSO raised by `copilot_mro…weaviate_tenancy` for provisioning failures
      that are not argument bugs**, which is safe today only because none of those sites runs inside a
      traced body here. **If that ever changes, the stated fix is to make the tuple a utils-private
      subclass, NOT to widen it.** Owner should confirm the ruling and the note.

- [~] G.61 **CODE DONE 2026-09-21 (see UPDATE below); TEXT REPAIR DONE 2026-09-20 (`core-obsm eaa714b`/`f71e182`/`c0be8f5`, tests; 14 production
      **THIRD-REVIEW BATCH CLOSED 2026-09-21 (`core-obsm 2d5e136..ba86d85`, 2 reviewers running):** A-P1 gate moved into `TenantService.delete_tenant` — `DELETE /channel-users` was UNGATED (`802850c`); fail-closed catalog read, drift read both ways, `pg_temp`-last search_path in the (unrun) SQL; B-P1 PDF routes typed 404/503/500 with fixed text. core unit 1585 → 1640, api 893 → 1005, authz 285, db 589 → 590 (1F/1E migration-gated, pre-existing).
      files uncommitted). Lane 3051 → 3080 passed. The DDL ruling has since been taken: M-CASCADE.**
      **UPDATE 2026-09-21 — OWNER RULED M-CASCADE ("stop the cascade"); CODE DONE, MIGRATION WRITTEN NOT
      RUN, INDEPENDENT REVIEW RUNNING.** `core-obsm b68e41c`·`af6adce`·`0ea20d3`·`2e66ee6`·`23ee9b0`, by
      named path, not pushed. Full write-up: `core-obsm/docs/plans/g61-comments-survive-tenant-delete.md`.
      **Chosen: DROP `_TENANTS_FK` from `comments`; the other eight stay.** `SET NULL` cannot work
      (`tenant_id` is NOT NULL and leads the PK); `RESTRICT` blocks the delete instead of keeping the rows;
      core has no documents table to key onto. Votes (`comment_thumbs_up`) cascade only from `comments`, so
      they now survive too. **Side finding: under the old schema a tenant with ANY vote could not be deleted
      at all** — the vote cascade fires a trigger updating `comments`, and the deleting role lacks UPDATE
      there (InsufficientPrivilege → 500). This change removes the path; do NOT widen that role instead.
      **Migration `scripts/rbac/drop_comments_tenants_fk.sql`** — catalog lookup (live name
      `comments_tenant_id_fkey`), refuses unless exactly one match, changes no rows, run by the table owner,
      off-peak. **RUN IT BEFORE DEPLOYING THIS CODE** — the other order ships a delete response promising
      comments survive while the database still destroys them. Until then the db lane is red BY DESIGN in the
      teardown census file (1 failed + 4 errors, naming the script), and a new boot check warns on any
      un-migrated database. **Phase H, owner-gated.**
      **No comments have been lost so far** (read-only check of live `copilot_mro`): 9 recorded tenant
      deletions, all scratch/placeholder tenants with zero rows of any kind; the live table holds 7 comments
      on 6 documents, one tenant.
      **Follow-ons closed in the same lane:** backfill commits 64 rows per transaction (subtransaction cache)
      and exits non-zero when it refused any row; savepoint-depth tests cover `RELEASE`; the
      `runs_on_schedule` guard reads the real routes' `response_model_exclude`; the span sweep catches
      dotted `trace.Status(...)` and `format_exc()`; the automation-store status list stops inventing
      `success`/`abandoned`; `sweep_span.py` keeps `traced_sweep` with a corrected reason; **keyset reader
      `list_tenants_page(*, limit, after=None, status=None)`** on `(COALESCE(created_at,''), tenant_id)` —
      `copilot_mro_test` holds a tenant with NULL `created_at`, which a plain key would silently skip.
      **Lane counts (ENV_FILE set):** unit 1405 → 1457 · automations 228 → 238 · api 884 → 884 · db 583
      passed → 582 + 1 failed + 4 errors (the migration-gated set).
      **NEW OWNER QUESTIONS:** (a) **personal data** — comments keep `author_name`/`author_email` after a
      tenant delete until the residue sweep runs; alternative is blanking them at delete time. (b) **cross-repo
      traceback policy** — core writes full tracebacks to logs at ≥13 sites and its docs allow it; utils and
      api strip them. **Still open:** `iter_all_tenants` pages by offset (~20 tests to rework); the 64-row
      bound wants one live-DB check; `api-obsm/.../executor.py:97` says "these four strings" above three
      constants. **api's registry walk MOVED onto the keyset reader (`api-obsm 6afd640`, review running).** Still offset: core `iter_all_tenants`; copilot-mro `ad_notification_dispatcher.py` `_active_tenant_recipients`.
      **INDEPENDENT REVIEW 2026-09-21 (Opus): FIX-FIRST — 0 P0 · 1 P1 · 12 P2. Schema change HOLDS**
      (re-attaching `_TENANTS_FK` fails 9 unit guards; teardown db reds are exactly the migration-gated set).
      **P1 — deploy order is DETECTED, not enforced:** replacing the boot-check call with `pass` left unit 1457
      / api 884 green, and `af6adce`'s "enforced" headline is refuted → fix: pin the wiring, and make DELETE
      /tenants refuse 503 (naming the script) while the catalog still cascades comments. **P2s:** three more
      span-sweep defeats (traceback via a local, `trace.use_span` defaults, `str(sys.exc_info()[1])`);
      `backfill()` can bypass the 64-row chunking with all lanes green; stale backfill prose (and skipped
      upsert rows cost a subxid too); casualty lists omit pending invitations; a fixture-wide precondition
      silences three unrelated db cases until migration; `list_tenants_page` leaks `keyset_sort_key`; boot
      check sees only direct children; integrity comment ignores a teardown race; migration `search_path`
      order; the log-pipe `format_exc` count is **51 across 8 files, not 13**; the votes-privilege failure
      is PG16-specific. **All routed back to the core implementer 2026-09-21.**
      **MY HYPOTHESIS WAS INVERTED, and the truth is worse.** I asked whether `comments` gained the FK
      *after* the sentence was written. **The reverse:** `comments` carried `_TENANTS_FK` in
      `table_definitions.py`'s **very first commit** (`b151c80`, 2026-07-30); the *"eight identity
      relations / nothing cascades them"* prose arrived **13 days later** (`fe6c0cb`, 2026-08-12).
      **This is not drift — the census was FALSE THE DAY IT WAS TYPED.** And the same commit `fe6c0cb`
      *also* wrote `_CONFIRM_MISMATCH`, which **correctly names "…departments, grants, comments and
      operators"** among what a delete removes. **One commit, two sentences, contradicting each other** —
      the author knew comments go, and miscounted while writing the census.
      **A TENTH RELATION IS DESTROYED, and the fallback guard I offered would have MISSED IT.**
      `comment_thumbs_up` (`table_definitions.py:1032`) cascades via `comments` and has **no key into
      `tenants` at all**, so a census over `_TENANTS_FK` attachment sites reports comment votes as a
      survivor — **they die at one more hop.** That is why the implementer built the **transitive closure**
      over the **rendered `create_sql`** rather than the definition dicts: the SQL string is what Postgres
      receives, so an inline clause or a hand-added constraint is caught by the same read, **and the
      builder's `CASCADE` default is already resolved in the text** (a constraint naming no action IS a
      cascade, and only the rendered form makes that visible).
      **FOUR MORE FALSE SITES the brief did not have:** `delete_tenant`'s own docstring (miscounts **and**
      misclassifies `comments` as identity) · the teardown `logger.info` at `:474`, **operator-facing** ·
      `TenantDeletionResponse`'s docstring · and **`tests/api/tenancy/test_tenant_teardown.py:922`, whose
      test docstring repeated the false claim verbatim — "a test that documents the lie is how it survived
      review."**
      **Nothing else cascades into `tenants`** — verified estate-wide: one `ref_table` site, no raw
      `REFERENCES tenants`, no `ADD CONSTRAINT` migration anywhere.
      **THE RULING, costed. Implementer's read: A.**
      **Option A — the cascade is intended, only the prose was wrong. Zero code change; the work above is
      the whole repair.** Teardown is complete, no orphaned annotation rows. For: the FK predates the false
      sentence by 13 days; `_CONFIRM_MISMATCH` already promises the owner comments are removed; and
      `comments` is tenant-class with `tenant_id` in its primary key, so **not cascading would leave rows
      no login can reach — precisely the residue the notice complains about.** **What A still owes:
      NOTHING EXPORTS COMMENTS BEFORE THE DELETE.** If the product ever offers "delete my account, here is
      your data", that export does not exist and the annotations are unrecoverable.
      **Option B — the cascade is accidental.** Drop `_TENANTS_FK` from `get_comments_table_definition`.
      Cost: **a DDL migration against a live database**, not runnable from an implementer's seat. Comments
      join the ~90 copilot relations as sweepable residue, the sweep grows a case, `_CONFIRM_MISMATCH` must
      stop naming comments — and **`comments` becomes the only relation in `RBAC_TABLE_NAMES` without the
      FK**, making core's registry internally inconsistent.
      **The pin is written so either ruling is a ONE-LINE edit to `AGREED_CASCADE`, with a failing test
      forcing the conversation.** ORIGINAL ITEM FOLLOWS. **P0 — DELETING A TENANT DESTROYS EVERY DOCUMENT COMMENT IT OWNS, AND THE API'S OWN 200 BODY
      SAYS IT DOES NOT.** Found by the docstring-contradiction sweep, **verified at source by the
      controller 2026-09-20.**
      `core-obsm/core/db/table_definitions.py:478` defines `_TENANTS_FK` with **`"on_delete": "CASCADE"`**,
      and it is attached at **NINE** sites, not the eight the comment claims. Mapped each to its table:
      `operators` (:591) · `departments` (:647) · `users` (:673) · `tenant_invitations` (:726) · `roles`
      (:769) · `user_departments` (:811) · `user_operators` (:865) · `user_roles` (:943) — **and
      `comments` (:996), which sits inside `get_comments_table_definition` (957-1016).**
      **`comments` is a PRODUCT relation — threaded document annotations — not an identity relation.**
      `tenant_endpoints.py:124` states *"Only `core`'s **eight** identity relations carry a foreign key
      into `tenants`; the copilot domain relations are tenant-scoped **by policy rather than by reference,
      so nothing cascades them**"*, and `_RESIDUAL_ROWS_NOTICE` — **returned to the caller on the DELETE's
      200 as `residual_rows_notice`** — says *"Rows this tenant owns outside the identity tables **do not
      cascade with it and are still stored**… An administrator must sweep all of it."*
      **So a tenant owner, or the engineer writing the residue sweep that notice points at, is told the
      product rows survive and are recoverable. The comments are already gone, and nothing exports them
      first.** The API asserts the opposite of what the DDL does, in the response body.
      **WHICH SIDE TO FIX IS THE OWNER'S CALL** and it is a real question, not a formality: either the
      cascade on `comments` is intended (and the notice plus the "eight" comment are wrong) or the cascade
      is accidental (and the DDL is wrong). **The text repair is safe under either answer; the DDL change
      is not.** Do the text now, rule on the DDL.
- [x] G.62 **DONE 2026-09-20 — and THE PREDICTED SECOND CONSUMER ALREADY EXISTED, SHIPPED, IN THIS REPO.**
      `core-obsm/scripts/run_db_lane.py:10` and `:193` justify refusing to run against a live database on
      *"the lane exercises GLOBAL mechanisms. `reap_stale_runs` scans every tenant"* — **exactly the caller
      the item predicted, written on the false docstring.** The guard itself is right and stays; its
      **stated reason** was wrong and is corrected. **And the control is just as clean:**
      `copilot-mro-obsm/.../document_hub/job_enqueue.py:92` reads a function whose docstring was
      **correct**, and says *"answers for the BOUND tenant."* **Correct docstring, correct consumer; false
      docstring, false consumer.**
      **The mechanical answer was built and IS a clean fit** — `_reads_the_bound_tenant`, applied to all
      **seven** family readers. Two halves: **the sentence is GENERATED onto `__doc__`** from one copy, so
      *"seven copies of a paragraph became one, which is why the family drifted in four places at once —
      each copy had to be corrected separately"*; and **the defect is made ABSENT, not merely guarded** —
      the wrapper **warns when nothing is bound**, so the predicted caller now gets a message naming the
      function instead of a silent `[]`. **A warning, not a raise, on the estate's own precedent**
      (`dashboard_profiles.py:142-149` does exactly this): the read really did answer correctly for the
      identity it was given, a probe must not take the scheduler down, and **what was missing was never
      the exception — it was any signal at all.**
      **FORCE-RLS confirmed end to end**, and corroborated by two standing XFAILs whose reasons already
      said so. **Two MORE stale cross-tenant claims found by grepping the family rather than the four
      cited** — both corrected. **Estate-wide grep before freeze: `"across all tenants"` zero live hits;
      `"Not tenant-scoped"` and `'Do not "fix" it'` ZERO, anywhere.**
      **It attacked its own guard and found it broken:** the marker test was a `parametrize` over a tuple,
      and **emptying that tuple would have collected zero tests and failed nothing — silently stripping the
      guard from all seven reads.** Closed with set-equality against the functions that really carry the
      marker, plus a floor, and mutation-proved.
      **NOT done, and recorded rather than half-done:** the broader typed-marker refactor across the
      store's ~40 functions and the sibling stores. ORIGINAL ITEM FOLLOWS. **P1 — FOUR SCHEDULER SWEEPS ADVERTISE THEMSELVES AS ESTATE-WIDE WHILE BEING PER-TENANT, and
      one closes with "Do not \"fix\" it."** `core-obsm/.../automation_store.py` at `:795`/`:817`,
      `:2487`/`:2531`, `:2758`/`:2867`, `:2945`/`:2997` each say *"— across all tenants, deliberately"* and
      *"**Not tenant-scoped, and that is not an oversight.** … it must recover **every tenant's** wedged
      work. Adding a `tenant_id` predicate would … silently leave every other tenant's automations dead
      forever. **Do not "fix" it.**"*
      **All four are called once per tenant, inside a binding**, by `_scan_every_tenant`
      (`api-obsm/flynapse_api/automations/loop.py:1546`) — whose own docstring says the opposite — against
      a **FORCE-RLS** relation. **So a second caller written on that docstring** — an ops recovery script,
      an `/admin/reap` endpoint, a health probe — **calls it once, unbound, gets `[]`, and reports "no
      wedged runs" forever with no error**: exactly the failure `_scan_every_tenant` exists to prevent.
      **And the "Do not fix it" actively instructs the next engineer against the tenancy work already
      shipped.**
- [x] G.63 **DONE 2026-09-20 — and it was FOUR citations, not three.** `list_unstarted_manual_runs` cites
      `list_due_automations` as precedent too. All four removed along with the paragraphs they justified,
      and **the redundant hand-written contract was removed from the three already-correct siblings so the
      rule is stated once, where it lives.** ORIGINAL ITEM FOLLOWS. **A SECOND citation that runs the other way — the class this project already recorded.**
      `automation_store.py:2867`, `:2997`, `:2531` cite `list_due_automations` as precedent for being
      global. **`list_due_automations`'s own docstring was CORRECTED and now states the opposite**
      (`:629`): *"in the tenant bound to this context… under row-level security the SESSION BINDING is the
      predicate… Called UNBOUND on a provisioned database this reads zero rows."* A reader following the
      cross-reference finds the correction and must guess which is current.
- [~] G.64 ~~**Four smaller contradictions, each with a named consequence.**~~ **FIVE — (a)–(e); the header
      miscounted its own list.**
      **AUDIT 2026-09-21 — FOUR OF FIVE DONE, ONE IN A LIVE LANE.** **(a) DONE** — `api-obsm b6471c8`
      (`queue_telemetry.py` now states *"There is no ``retry`` trigger"*), pinned by
      `test_queue_trigger_vocabulary.py` at `7a24dd5`. **(b) DONE** — `api-obsm 08f54f9`, 2026-09-21.
      **(c) DONE** — `dashboard-obsm afd6300`; `PermissionContext.tsx:464` now carries no count, deliberately.
      **(e) DONE** — `api-obsm b6471c8` (`lifecycle_span.py` no longer claims copilot-mro's spans are the
      only ones). **(d) done in the copilot-mro WORKING TREE** (`seed_ad_notification_subscription.py` now
      names the Postgres `tenants` table, `:70`, `:88`) **and lands with that lane's commit.**
      **(c) SETTLED 2026-09-20 — the plan's claim was CONFIRMED, and it was worse than stated.**
      `SETTINGS_CAPABILITY_BY_FLAG` (`lib/auth/capability-utils.ts:57`) holds **eight** entries; the comment
      said **six, TWICE** (`PermissionContext.tsx:458` and `:460` — the plan named only one of the two
      sites). The two omitted are exactly `canViewOperators` and `canViewInvitations`, and the plan's
      characterisation of them is right: both map to `users_view` while the routes behind them are
      owner-only. **NO behavioural defect** — the memo deps are sound at every level, and the context value
      memo lists all 19 deps including all eight flags, so the "not six memos" worry about memoisation is
      **REFUTED**. The fix is **to delete the cardinals**, per G.65's own recommendation: the map IS the
      census and `satisfies Record<keyof UserPermissions, string>` keeps the destructure honest — **no
      number to maintain, so no guard needed for one.**
      **This was the ONE cell the reality audit declined to guess.** It named the census instead of filling
      it, and the census confirmed it.
      **(a) A metric-label vocabulary that names a value nothing writes.** `api-obsm/flynapse_api/
      telemetry/queue_telemetry.py:90` says the `trigger` vocabulary is *"written by `claim_run`
      (`scheduled`/`manual`/**`retry`**)… **and by nothing else**. Safe as a metric label."* The store's
      vocabulary is **three** — `scheduled`, `manual`, `one_shot`; **`retry` is written nowhere in the
      estate** (zero hits across five trees). An engineer adding a retry path writes `trigger='retry'`, and
      the retry sweep's predicate is `r.trigger = 'scheduled'` — **so those rows silently leave the retry
      work list and refused runs stop being retried**, with nothing logged.
      **(b) "Two ten-key deny-lists" — one is ten, one is NINE. CORRECTED 2026-09-20: they are NOT
      "disjoint in both directions" as first reported — they SHARE FIVE KEYS** (`session.id`, `user.id`,
      `enduser.id`, `url.path`, `http.target`). The enumerated collector-only and app-only members are
      right (4 and 5), but the sets **overlap and neither is a subset of the other** — which is a sharper
      version of the same trap, not a milder one. **Also: R.4 §3.0 calls the collector list "10 keys" and
      enumerates 9; `base.yaml:76` holds 9 — R.4's own table is wrong.** `queue_telemetry.py:55`. `user.email`, `organization.id`, `terminal.type`,
      `app.entrypoint` are collector-only; `session_id`, `user_id`, `path`, `url`, `url.full` are app-only.
      Reading it as one rule stated twice means an author who checks one concludes the other has it —
      **`user.email` is NOT app-denied, so a metric labelled with it is accepted where the author expected
      a raise.** (The load-bearing half — `tenant.id` on neither — is TRUE and was verified.)
      **(c) A capability count that excludes exactly the risky rows.** `dashboard-obsm/lib/auth/
      PermissionContext.tsx:458` says *"not **six** memos"*; the map has **eight**, and the two the count
      omits — `canViewOperators`, `canViewInvitations` — are **precisely the two whose mapping is
      deliberately looser than the server's.** An engineer auditing six and stopping skips the two where a
      mistake is an authz-visibility mistake. **No enforcement defect: the gates themselves were verified
      owner-only and correct.**
      **(d) A retired store named in an operator-facing error.** `copilot-mro-obsm/scripts/ad/
      seed_ad_notification_subscription.py:65` raises *"No tenants found in **DynamoDB** `tenants` table"*;
      the read is **Postgres**, and DynamoDB is retired estate-wide. The operator goes to a store that no
      longer exists and concludes the registry is empty — when the row may simply be past G.49's 50-row cap.
      **(e) `api-obsm/flynapse_api/telemetry/lifecycle_span.py:4`** calls copilot-mro's lifecycle spans
      *"the only lifecycle spans in the estate"* — **false the moment that file exists**, since it declares
      `api.lifecycle`. Someone building the promised "one query reads both runtimes" filters on
      `mro.lifecycle*` and gets nothing from the only runtime that actually boots.
- [x] G.65 **The ONE guard worth building from this class — and the auditor refused the general version.**
      **AUDIT 2026-09-21 — MOVED TO FUTURE IMPROVEMENTS** (§6, *"Deferred from Phase G, 2026-09-21"*): the
      narrow cardinal/absolute lint is the **lowest-value** guard left in this phase. **Three of its four
      individual pins have landed** — G.61's notice is derived from `TENANT_CASCADE_RELATIONS`
      (`core-obsm tenant_endpoints.py:289`), G.64(a)'s vocabulary pin (`api-obsm 7a24dd5`), and
      the G.64(b)/(c) cardinals deleted. **The fourth, a generated inventory of api's `REASON_*` constants,
      has NOT** — `dashboard-obsm/contracts/` holds triggers, error categories and browser signals, no reasons.
      *"The general form — a checkable claim in prose that the code contradicts — is not decidable, and I
      will not pretend otherwise."* What it recommends instead is a narrow lint: **a cardinal number or an
      absolute (`the only`, `every`, `and by nothing else`) sitting adjacent to a backticked identifier**
      must resolve to a generated value or a named pin test. **That would have caught four of its nine
      findings, and five of the six instances this project had already confirmed.**
      Individually guardable now, in the estate's own idiom: derive `_RESIDUAL_ROWS_NOTICE`'s relation list
      from the actual `_TENANTS_FK` attachment set at import **so the sentence cannot be wrong** (G.61);
      pin `queue_telemetry`'s `trigger` literals against `schemas.py` — **the estate already does exactly
      this at `document_hub_cleanup.py:65`, the pattern just was not applied here** (G.64a); assert the
      cardinal numbers against `len()`, or delete them (G.64b, G.64c); and generate a reason inventory from
      api's `REASON_*` constants the way `contracts/browser-signals.json` is already generated (G.64d).
      **NOT guardable: G.62/G.63.** A lint on the string "across all tenants" is decoy-defeatable and would
      be gamed in a week — this project already recorded that guard-PRESENCE is defeatable and the question
      to ask is defect-ABSENCE. The real mechanical answer runs the other way: **make the tenancy contract
      a decorator or typed marker on the function, so the sentence is GENERATED from the contract rather
      than written beside it.**

- [x] ~~G.66 (DUPLICATE ENTRY — merged into G.53 by the 2026-09-21 audit; same root cause, the venv `.pth`
      files. Work it from G.53, never from here.)~~ **THE SIBLING HAZARD IS LIVE IN THE API TEST LANE — instance EIGHT, and the widest yet.**
      Confirmed by the api implementer, independently of G.53's finding. From a neutral cwd,
      **`core`, `utils`, `copilot_mro` AND `shift_optimizer` all resolve to the PRE-MERGE siblings** via
      the venv's editable `.pth` entries; `api-obsm/tests/conftest.py` **appends** deliberately, so it
      cannot fix this. **Visible symptom:** `tests/startup/boot_checks/
      test_weaviate_partition_startup_mode.py` **fails to COLLECT** (`ImportError: cannot import name
      'PARTITION_REFUSAL_ERROR' from 'copilot_mro… /Code/copilot-mro/…'`) **and interrupts the whole
      lane.** Pinning `PYTHONPATH` to the four merged trees fixes it.
      **So any api run in this workspace without that pin is reading four pre-merge trees** — and only the
      new-symbol case fails loudly. Every shared symbol passes green against the wrong tree.
- [x] G.67 **A cross-lane trap the implementer's own change ARMED, visible only at directory granularity.**
      **AUDIT 2026-09-20 — VERIFIED DONE (a record).** Guard at
      `api-obsm/tests/integration/automations/conftest.py:68`; the wiring test moved to
      `tests/unit/telemetry/test_worker_telemetry_flush.py`; `worker.py:403-405`.
      `worker.main()` now ends in a real `shutdown_telemetry`, which **closes the SDK providers for every
      test that runs after it in the same process.** Latent while nothing bootstrapped telemetry earlier in
      the lane — but the moment a `captured`-using file was collected first, it produced **nine unrelated
      failures in `tests/integration/otel/` that NO subdirectory run reproduces.** Fixed twice (a guard in
      the lane's conftest, and moving the wiring test), and recorded here because **this is the
      both-granularities rule paying for itself**, and it is the same class as G.54: a defect that is green
      per-directory and red combined, invisible to a gate that runs one invocation per directory.
- [~] G.68 **OWNER: the `traceparent` carrier is a schema decision, and the interim is knowingly wrong.** **RULED M-JOB-TRACEPARENT + BUILT 2026-09-22:** core `7c506e6` (nullable column in the DDL file, validated W3C write at enqueue, `OneShotRun.traceparent`, worker boot check) + api `6ae9701` (consumer links through `run.traceparent`; `carried_traceparent` and the `__traceparent__` key are gone). **Open: the migration itself (owner C9, BEFORE core deploys; §2.2 step 4); core r6 F11 (`test_automation_tables.py:228` expectation lacks the column, so one "migration-gated" red would stay red).** Text below is the pre-ruling state.
      Proposal: a nullable `traceparent varchar` on `automation_runs`. **No migration was written.**
      Interim: `queue_telemetry.carried_traceparent()` reads a reserved `__traceparent__` key from
      `automation_runs.params` — **nothing writes it today, so the mechanism is tested and inert.**
      **The cost of staying on `params` is stated by the store's own design note**
      (`automation_store.py:970-977`), which **explicitly rejects burying execution context in `params`**
      because it makes infrastructure depend on a kind-specific dict shape — the same argument applies
      here, which is why the implementer called it a stopgap rather than a solution. **Cost of no carrier
      at all:** the consumer span is an unlinked root, and a producer's trace joins to it only by the run
      id in a log line.
      **G.17 recommendation from the same pass:** do **NOT** tenant-scope the four new instruments.
      `automation.queue.{depth,wait,claims}` and `automation.tick.duration` have **≤ 8 label sets each
      estate-wide**; tenant scope would multiply them by the tenant count **for a signal that is a
      per-process property, not a per-tenant one.** Tenant identity rides the span, where it belongs.

- [x] G.69 **core's backfill has NO SAVEPOINT — a strictly worse blast radius than the writer it mirrors.**
      **CLOSED 2026-09-20 (`core-obsm d368c7a`, tests committed; two production edits UNCOMMITTED).**
      **Proved against a REAL Postgres abort, not structurally** — which was the whole risk, because a mock
      connection accepts a `SAVEPOINT` string and proves nothing.
      **The witness case replays the OLD loop on the same cluster with the same SQL and params** and pins
      the exact failure: row 2 raises `NumericValueOutOfRange` (22003), row 3 then raises
      `InFailedSqlTransaction` **without the server looking at it, and row 1 is gone too** (`_facts_count ==
      0`). **The hazard is measured, not asserted.** The fix case then lands `written == 2`, `refused == 1`,
      `refused_by_error == {"NumericValueOutOfRange": 1}` and block ids exactly `["b-1", "b-3"]` — **the row
      AFTER the refusal, which an un-savepointed loop cannot produce.**
      Per-row `SAVEPOINT`/`ROLLBACK TO`/`RELEASE` per M-SAVEPOINT. **Refusals are keyed by exception CLASS
      NAME only** — a psycopg2 bind failure renders the whole interpolated `VALUES` list, i.e. the same leak
      shape this merge's own writer introduced earlier. Two subtleties the implementer found and recorded:
      **`rowcount` is read BEFORE `RELEASE`** (reading it after scores the release's rowcount on every row),
      and **`skipped_unchanged = read − written − refused`**, because folding refusals in would report a
      clean gap-fill over turns that have no row at all.
      **Briefed line numbers REFUTED:** `_execute_many_on` was at `:604-617`, not `:422-431`. The SAVEPOINT
      prose was at `:9` and `:146-147` as claimed, and is repaired.
      **Prose family swept: two stale sites remain CROSS-TREE, reported not edited** —
      `copilot-mro-obsm/.../postgres_table_definitions_modules/chat_turn_facts.py:183` and
      `copilot-mro-obsm/tests/unit/chat_history/test_chat_turn_facts_value_gates.py:386` both still say the
      backfill runs "a whole batch on one cursor with one commit and **NO savepoint**".
      `core-obsm/scripts/backfill_chat_turn_facts.py:422-431` (`_execute_many_on`): one cursor, one commit,
      a loop of `cursor.execute`. **One refused row aborts the transaction and takes every later row in the
      run.** The online writer wraps each projection in a per-row `SAVEPOINT` under owner ruling
      M-SAVEPOINT; the backfill has no equivalent. Found by the copilot-mro implementer, out of its tree
      and correctly not touched. **Now less likely to fire since G.55 landed the gates** — but the gates
      turn a raise into a NULL only for the shapes they cover, and the structural exposure remains.
- [x] G.70 **Seven collection errors from a bare `from conftest import` — pre-existing, and the SAME
      **AUDIT 2026-09-20 — VERIFIED DONE (uncommitted; it landed DURING the audit).**
      `grep -rn "^from conftest import" tests/integration/otel/*.py` → **0**. New
      `tests/integration/otel/_otel_smoke.py` plus a new guard
      `tests/unit/infra/test_shared_test_helpers_never_import_conftest.py`, both untracked in the working tree.
      bare-name-resolution family as G.26, one layer down.** A combined run of
      `copilot-mro-obsm/tests/agent_sdk/` + `tests/integration/otel/` yields **7 collection errors**, all
      `ImportError: cannot import name 'http_get' from 'conftest'`, because the otel files import
      `conftest` as a bare top-level module. **Reproduced IDENTICALLY on the untouched pre-merge sibling**,
      so it is not ours — but it is the same defect class as G.26 **in `sys.modules` rather than
      `sys.path`**, and it is another instance of the G.54 shape: invisible per-directory, red combined.
      Also pre-existing and reproduced on the sibling: `test_langchain_ambient_surface_policy.py::
      test_no_surface_can_flip_the_model_wire_shape_ambiently`.
      **Broader background run for context: 3,415 items across 10 directories → 7 failed / 3,395 passed /
      13 errors, NONE in a file the implementer touched.** The failures are the known `copilot_mro_test`
      re-migration item plus the above.
- [x] G.71 **OWNER: two value-gate judgements deliberately escalated rather than decided.** **RULED 2026-09-22 M-FACT-LIMITS — both confirmed as built; no code change.**
      **(a) `confidence` outside `[0,1]` → NULL, not clamped.** *"Clamping invents a judgement the judge
      never made."* The alternatives — clamp, or widen the documented range — are the owner's.
      **(b) `_LATENCY_MAX_MS` = 24 h is a number the implementer chose.** An absurdity ceiling, not an SLO;
      a turn genuinely longer than a day loses that one field.
      **Recorded but out of scope:** `tool_usage` has **no cardinality cap** (`per_tool` grows with
      distinct tool names) and `cited_documents` carries unbounded title strings × 20 — same width class,
      but neither costs nor corrupts the row.

- [x] G.72 **iac alarms/widgets — DONE 2026-09-20 (`iac 607cee0` guard; `.tf`/`.tftpl` uncommitted). Lane
      **AUDIT 2026-09-20 — VERIFIED DONE.** Guard committed at `iac 607cee0`; `alarms.tf` and the two
      dashboard templates carry uncommitted fixes. F5 landed — the shift-optimizer board now reads
      `attributes.tenant.id` with the `IDENTITY_KEYS` reasoning inline. **Exactly 1 `attributes.event_name`
      survives, in a markdown TEXT panel (`frontend.json.tftpl:7`) the guard excludes by design.**
      142 → 157 passed, `rootdir /home/aditya/Code/iac`.**
      **Controller brief error #32: item (1) was ALREADY DONE before I briefed it.** I briefed from R.4,
      which audited `iac 2d493c8`; the tree is at `5e476e0`, **three commits ahead** — `9fda3db` rewrote
      both API alarms with `histogram_count()`, `234603b` triaged an adversarial review, `5e476e0`
      corrected nine stale state claims. **`ApiHighErrorRate` is not non-functional today.** The
      implementer re-derived the shape question **from the vendor itself** rather than trusting the file,
      and confirmed it: CloudWatch **converts explicit-bucket histograms to exponential at ingestion**, and
      its only query example carries **no `rate()`, no `_bucket`, no `le`**.
      **F2 — but a withdrawal landed in the COMMENT BLOCK ONLY.** `234603b` withdrew "fails LOUDLY" and a
      named substitute — **and the `description`, which is the text that reaches an on-call in the console,
      still asserted both.** Fixed. Its first rewrite hit **1028 chars against CloudWatch's 1024
      `AlarmDescription` cap** and was caught by the repo's own existing test.
      **F3 — the attribute-spelling question is SETTLED by three AWS pages: the stored key KEEPS ITS
      DOTS.** `event_name` is **Loki's sanitiser**, and the copilot-mro runbook says so itself. Emitter side
      confirmed at source: the browser writes `'event.name'` and the collector's allow-list keeps it
      verbatim through to the CloudWatch exporter. **13 occurrences across all 12 log widgets fixed** —
      **R.4's "4 alarms + 11 widgets" was wrong on the widget half** (one widget uses it twice).
      **F5 — NEW, and it is the verify-the-premise lesson again: `attributes.tenant_id` is dead too.**
      `utils-obsm/utils/observability/log_bridge.py:30-35` flattens loguru `extra` through an
      **`IDENTITY_KEYS` remap** — `tenant_id → tenant.id` — **before the wire**. `run_id` and `job_id` are
      **not** in that table, so they are correct in the same widget. **R.4 §2f AND the copilot-mro runbook
      both record `attributes.tenant_id` as right — both read the CALL SITE, not the bridge.**
      **Satellites-review iac rows closed 2026-09-22 (not pushed):** IR-25 `4e2a936`: the guard lane moved into one reusable workflow (`guards.yaml`) that plan and apply both call, and each terraform job waits for it, so an apply no longer runs on a red tree; IR-12 `ca095c8`: the unit-suffixed inventory says it is read on copilot-mro obs-merge, and that the pushed `langgraph-merge` (`417df303`) still creates `agent.model.latency_seconds`; IS-12 `0dda33a`: the 12 alarm descriptions that make no state claim are a register check 6 reads by equality, each with its reason (seven OWED a WIRED note).
- [ ] G.73 **P0-shaped — FOUR BROWSER ALARMS ARE DEAD-GREEN, and the implementer deliberately did NOT
      **PREPARED FOR THE OWNER 2026-09-20 (`iac 48fc50c` + `f85284e`).** Counts verified in the current
      tree: `$.attributes.event_name` at **4** pattern positions (`alarms.tf:519,550,558,566`) and
      `$.resource.attributes.service.name` at **6** (`:519,539,550,558,566,584`) = four browser + two
      worker. **Six is right — with a refinement: only FOUR are in resources that exist today**, because
      `AutomationRunErrors` and `AutomationWorkerSilent` are gated off by
      `var.automation_worker_deployed = false`.
      **`scripts/b1b_metric_filter_probe.sh` (new, committed) settles it in ONE PASTE**, non-mutating
      (`logs:TestMetricFilter` only — no log group, no alarm, no apply, no state). It runs every candidate
      selector for both open keys against **both** candidate storage shapes, plus all six production
      patterns verbatim, and prints `REJECTED` / `NO MATCH` / `MATCH` per cell **with each outcome's meaning
      spelled out**. The sample events are **derived, not invented** — the intersection of what the dashboard
      emits and what `transform/browser_allowlist` keeps, with identity keys in the spelling `IDENTITY_KEYS`
      produces. It **states its expected result before it runs, so the run can contradict it**, and all
      three classification branches were proved offline against a stubbed `aws` binary. **What it cannot
      settle — which shape CloudWatch actually writes — it says so**, and supplies the read-only
      `filter-log-events` one-liner against the real group that closes that half.
      **`notBreaching` — ANSWERED, and the answer is to keep it. OWNER RULING OWED, recorded in
      `alarms.tf`'s header where the reader already is.** Flipping to `breaching` *"does not turn a silent
      lie into a signal, it turns it into a page every quiet night"* — the browser has no heartbeat, so "no
      telemetry" genuinely is the ordinary dev case. **But the objection behind the question is right**: an
      alarm that cannot separate "healthy" from "not reporting" is misconfigured whatever its filter says.
      **What closes that is a DENOMINATOR, not a different `treat_missing_data`** — one more metric filter
      counting every record from `service.name = dashboard`, carrying no alarm of its own. Flat-zero while
      the dashboard is demonstrably in use = **dead filter, visible rather than inferred**; non-zero gives
      the error-rate alarm a ratio and the three Web Vitals a real sample guard. It is a new resource, so it
      waits for the ruling **and** for the probe — **minting it now would mint it with the same dead
      selector.**
      guess the fix.** **SIX metric-filter selectors are dead, not four.** AWS documents property selectors
      as *"alphanumeric strings that support hyphen and underscore"* with **the period as the PATH
      SEPARATOR**, and bracket notation for a key containing a period. So `$.attributes.event_name` cannot
      match under any reading, **a bare `$.attributes.event.name` is NOT the fix**, and
      `$.resource.attributes.service.name` has the same defect — 4 browser + 2 worker patterns.
      **`notBreaching` + a filter that matches nothing = OK forever. These alarms must not be armed.**
      **Why it was left open rather than fixed, and this is the right call:** the bracket **punctuation at
      depth > 1 is undocumented** — AWS's only worked example sits at depth 1, where two spellings
      coincide. *"Writing one loses either at the first apply or silently — the exact trade the rule warns
      about."* **Settled by four non-mutating `aws logs test-metric-filter` calls needing no log group,
      alarm or apply**, written verbatim into `alarms.tf`. It tried to run them: **all six AWS SSO profiles
      have expired tokens and `aws login` is interactive and owner-gated.**
      **The guard was attacked and its holes closed:** selector positions only, **never text panels**
      (three boards discuss the wrong spellings on purpose, and this file was bitten once by a
      prose-as-query scan); a **sourced per-key list** rather than "underscores are wrong", because the
      allow-list carries **both** `app.version` AND `app_version`; **two floors proved separately**; the
      container pinned (`service.name` is a RESOURCE attribute, so `attributes.service.name` fails); and
      **per-key provenance, because `event_name` came from Loki and `tenant_id` from the call site — two
      different files to go read.**
      **The committed guard FAILS against the tree without the three uncommitted files.** That coupling is
      intentional and stated in the commit message: **if the owner rejects the dashboard fix, check 7 must
      come out with it.**
      **iac r4 batch, 2026-09-22 (`61c5297`, not pushed):** `alarms.tf` now states the M-ALARM-DENOMINATOR ruling (keep `notBreaching`, add one denominator filter after C2) and that C2 itself, the probe run plus one read-only `filter-log-events`, is still owner-owed. The "OWNER RULING OWED" wording above is superseded by that ruling.
- [ ] G.74 **OWNER, iac — four items, three of them cheap and non-mutating.**
      **(3) SETTLED 2026-09-20 — the key is GENUINELY DEAD, proved on two independent legs, AND IT IS A
      CLASS.** `attributes.tenant_id` has **no producer anywhere in the estate**: (a) backend —
      `utils/observability/log_bridge.py:30-35` maps `tenant_id → tenant.id`, `flatten()` applies it at
      `:97`, and **both** sinks call `flatten()` (stdout `:146`, OTLP `:193`); (b) browser —
      `deployment/otel/base.yaml`'s `attributes/browser_identity` upserts the key as `tenant.id`, and
      `transform/browser_allowlist` keeps `tenant\.id` and **not** `tenant_id`, so **even a client-authored
      `tenant_id` is stripped**. An operator querying it in Logs Insights during an incident gets a blank
      panel and reads it as *"no data"*.
      **MY BRIEF WAS HALF WRONG, AND THE WRONG HALF WAS THE LOAD-BEARING ONE.** I claimed
      `iac/scripts/validate_metric_vocabulary.py:440,467` *"already records that the emitting repo's runbook
      is wrong."* `:467` did. **`:435-441` recorded the EXACT OPPOSITE** — it listed `attributes.tenant_id`
      among *"REAL underscore keys … carried verbatim through the loguru bridge"* and said the runbook *"is
      **correct as written**"* — **twenty-five lines above `DOTTED_ATTRIBUTE_KEYS`, which contains
      `tenant.id`.** So **the file that codifies the contract flagged the spelling as dead in its code while
      its own prose vouched for it.** A third site at `:84` said the same. **Both were G.72 casualties: the
      boards were fixed, the sibling prose was not** — the exact defect family this project keeps finding.
      Fixed and committed (`iac f85284e`).
      **Four stale sites remain in `copilot-mro-obsm` (one of our seven trees), reported not edited:** the
      runbook sentence is **duplicated** at `deployment/otel/dashboards/CATALOGUE.md:62`, so fixing only the
      runbook leaves the shared spec wrong; and `aws-profile.md:19` plus `CATALOGUE.md:387-388,402` still
      describe the dashboard bodies as querying `attributes.event_name`, which G.72 corrected to
      `attributes.event.name` (14 occurrences now).
      **A generalisable guard was BUILT, and a bigger one REFUSED with three reasons.** Built:
      `iac/tests/unit/observability/test_attribute_key_prose_pinned.py` pins, **per file, by equality**, the
      count of `(resource.)attributes.<sanitised>` mentions across every iac prose surface, using the
      validator's **own** parser and with the watched spelling set **generated from
      `SANITISED_ATTRIBUTE_KEYS`** rather than typed — so adding a dotted key brings its twin under the
      guard automatically. **Its docstring is honest that it pins SHAPE, NOT TRUTH**: it cannot tell a
      condemnation from an assertion and **would have passed this very defect on the day it was written.**
      What it buys is that a sibling sentence can no longer be left behind *silently*.
      **Refused:** making the validator fail on the emitting repo's runbook — (a) check 7 reads selector
      positions and excludes prose **by design**, and a prose checker must distinguish *"X is the key"* from
      *"X is the WRONG key"*; (b) it needs a cross-repo scan resolved **by name**, and there are literally
      two trees — **the documented sibling-checkout hazard**; (c) an iac CI failure nobody in iac can fix.
      **IB-03 fixed 2026-09-22 (`iac 2965526`, not pushed):** 16 of the prose pin's 30 floor mentions came from the throwaway B1b probe; the vacuity floor now counts only the files that outlive C2 (floor 6, today 8), so deleting the probe after C2 no longer turns it red for the wrong reason.
      **(4) VERIFIED — and the answer is NEITHER of the two options I offered. It is a THIRD category.**
      `main.tf:6` requires `~> 6.43`; the lock holds `5.100.0` / `~> 5.0` — both confirmed. **But the lock
      is gitignored (`.gitignore:22`) and UNTRACKED, so there is no committed version gap at all**, and CI
      is unaffected: both workflows run a bare `terraform init` on a runner with no lock and resolve the
      newest 6.x fresh. **Nor is it inert.** A provider from a 2026-09-05 init is installed locally, and
      **`terraform validate` runs against that stale schema with NO version-constraint diagnostic
      whatsoever**: `valid: false, error_count: 5`, **all five false** (`outputs.tf:13` plus four in
      `alarms.tf`) — the PromQL-alarm form that arrived in provider 6.42.0.
      **So it is a LOCAL-ONLY stale artefact that silently MIS-VALIDATES the repo on this workstation.**
      Someone running `terraform validate` alone reads five false errors in load-bearing files **and could
      "fix" correct code.** The README's documented sequence is safe because its `init` catches it; validate
      alone is not. **No silent PLAN drift is possible anywhere, precisely because the lock is not shared.**
      Nothing under `tests/` reads the lock or asserts a provider version (0 hits), and the suite runs
      before `terraform init` in CI. **Owner owes one `terraform init -upgrade` on this workstation.**
      **Flagged, unverifiable offline:** `cloudwatch.tf:10` and `README.md:253` assert *"the resolved 6.64.0
      carries `aws_xray_trace_segment_destination` and `aws_xray_indexing_rule`"* — **nothing in this tree
      has ever resolved 6.64.0.**
      **(1) Four `aws logs test-metric-filter` calls** (verbatim in `alarms.tf`) — settles G.73 with **no
      log group, no alarm and no apply**. Blocks arming four alarms.
      **(2) One `PutMetricAlarm` with a bogus function name** — settles whether an unsupported PromQL
      function is **rejected or silently green**.
      **(3) `copilot-mro-obsm/docs/runbooks/observability/aws-profile.md:22-23` is WRONG on both keys** —
      it records `event.name → attributes.event_name` and `tenant.id → attributes.tenant_id`; F3 and F5
      falsify both. Another agent's tree.
      **(4) `terraform init -upgrade`** — the lockfile is on aws `5.100.0` while `main.tf` requires
      `~> 6.43`, so **`terraform validate` has been failing on this root since the pin bump**, pre-existing
      and unrelated to this work. Every error is a schema mismatch on the `promql` alarm block.
      **Still correctly open, not guessed:** `severity_text` ×9 and `$.severity_number` — OTLP spells them
      `severityText`/`severityNumber`, and **there is no emitter-side dotted form to compare**, so the new
      check cannot reach them and the implementer refused to guess. And an observation worth keeping: **both
      API alarms wrap `rate()`/`increase()` inside histogram functions, and AWS's own two documented
      histogram query forms carry NO `rate()`** — PromQL defines it on native histograms so it should hold,
      but no AWS page read confirms it. One more unverified link.

- [x] G.75 **Guard D's stated blocker is now RETIRED, and its docstring says otherwise — the same prose
      **CLOSED 2026-09-20, BOTH HALVES.** copilot-mro half: `tests/unit/storage/test_s3_listings_paginate_to_exhaustion.py`
      (`copilot-mro-obsm aee8d4b1`), **7 passed on arrival** — the briefed population was exactly right, three
      non-test sites, and `document_hub/cleanup.py:139`'s hand-rolled loop **passes on its merits** because it
      reads BOTH `IsTruncated` and `NextContinuationToken`. The witness is that loop rather than a paginator
      **deliberately**, because it is the only site the rule judges on merits. Mutation-proved twice, plus a
      third mutation that broke `cleanup.py` itself and made the guard name it.
      utils half (`utils-obsm f821135`): the retired reason was confirmed present and rewritten — **but the
      brief's second half was REFUTED**: the test does NOT name, it finds (`PACKAGE = repo_root(__file__,
      "utils")` is the only root resolution in the file), and that property is already swept estate-wide by
      `test_cross_repo_reads_name_their_checkout.py` §2.
      **One site left out of scope with its reason in the docstring:** `tests/e2e/run_history_e2e.py:1118-1119`
      makes two bare `list_objects_v2` calls — a live-stack script counting a handful of artifacts under one
      prefix with `MaxKeys=1000`, **not a total reported to anyone.** Widening the scan would have made the
      guard red on arrival over a count that is not a completeness claim.
      defect this plan already records elsewhere.** `utils-obsm/tests/unit/storage/
      test_s3_listings_paginate_to_exhaustion.py:26-30` gives the cross-repo naming hazard as **the**
      reason for single-repo scope: *"a cross-repo scan from here would have to name `copilot-mro`, and a
      bare name beside these worktrees resolves to the PRE-MERGE checkout."* **`sibling_variant` exists in
      that tree as of `1e55f34`, proved to reach the merged copy — so that reason no longer applies.**
      **But widening is still the wrong move, for the reason the docstring gives SECOND and should now
      give first: the tree that must change should be the tree that goes red.** A Guard D in `utils-obsm`
      failing on a copilot-mro defect fails the wrong repo's CI. **The right action is a COPY into
      `copilot-mro-obsm`, anchored on its own `repo_root`** — and it would be **non-vacuous and green on
      arrival** (three non-test sites there: one hand-rolled loop that passes on merits, two paginators).
      **Measured population estate-wide: utils-obsm 3 · copilot-mro-obsm 3 · core-obsm 0 · api-obsm 0** —
      six, matching Guard D's own docstring.
- [x] G.76 **Three stale or vacuous test-prose defects found in passing, none load-bearing, all reported.**
      **(c) CLOSED 2026-09-20 (`core-obsm d368c7a`) — and repairing the sentence exposed a live defect
      behind it.** The test computes its candidate list dynamically, so nothing took a wrong path, but
      **`utils` cannot reach the loop body at all and the fallback was silently being carried by `iac`
      alone** — nothing said so. The candidate list is now the genuinely single-checkout repos, and the
      implementer added **the other half of the claim: a twinned repo must NOT come back as the bare name.**
      Without that limb the test was satisfiable by a `sibling_variant` that ignores variants entirely.
      **(a) and (b) closed in `utils-obsm f821135`** — see G.40's entry.
      **(a)** `utils-obsm/tests/unit/infra/test_no_depth_coupled_paths.py:41` exempts `tests/conftest.py`
      with the reason *"it bootstraps sys.path"* — **it does not**; that conftest only calls
      `ensure_test_database()`. Inherited boilerplate from `core`/`api`, harmless behaviourally, **false
      as a reason** — and a false exemption reason is how an exemption outlives its cause.
      **(b)** `utils-obsm/tests/unit/infra/test_root_anchoring.py:86-94` asserts
      `sibling_repo(f, REPO.name) == REPO.parent / REPO.name` — but here `REPO.name` is `utils-obsm`, **so
      that IS this repo. The test is vacuously true and its docstring ("a DIFFERENT checkout") is false in
      this tree.** Pre-existing; the hazard it means is now covered by the new §1.
      **(c)** `core-obsm/tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` carries a
      now-false docstring: *"`utils` has no `-obsm` twin in this workspace."* **It does.** The test still
      passes because `iac` keeps the relevant set non-empty, **but the stated premise is wrong** — a test
      that passes for a reason other than the one it states.

- [x] G.77 **DONE — (a) M-CHART-CELL `dashboard-obsm 951fdc4`, not pushed:** the table cell reads through `Object.hasOwn` (rows and chart dataset untouched); census entry `ChartCard.tsx::row` moved PENDING → CLOSED AT THE READ, pinned by `tests/unit/chat/chart-card-table-cell.test.tsx`; unit 2584 → 2589, mutant red, byte-identical restore. **(b) M-NOTE-KINDS: no change, by ruling.** ORIGINAL ITEM FOLLOWS.
      **OWNER, dashboard — two decisions the G.56 implementer declined to take unasked.**
      **(a) `ChartCard.tsx:80`.** The keys are genuinely backend-owned (the chart payload's own JSON keys),
      so a `constructor` column renders `String(fn)` in a table cell. **Left bare deliberately: the row
      objects are handed to the chart library as its dataset, and giving a third party's input a null
      prototype is a wider behaviour change than the cosmetic defect it closes.** Marked OWNER DECISION
      PENDING in the backlog. Fix the cell, or null-prototype the row and re-test the chart.
      **(b) `DiscoveryQualityNote.kind` is typed `DiscoveryQualityNoteKind | string`** — i.e. **the backend
      is ALLOWED to invent kinds.** The frontend now survives one. **Whether the backend should be narrowed
      instead is an api-side question**, and the FE fix does not settle it.
      **And one dependency the owner should know:** `MessageProgressTrace`'s `statusConfig` is left bare on
      purpose — its key is closed at runtime by the only writer of that field, so repairing the alias table
      closes it, and it is `as const` where a null prototype would widen its literal types for no
      behavioural gain. **If the owner rejects the `lib/chat/pipeline-status.ts` edit, `statusConfig`
      becomes reachable again.**

- [x] G.78 **M-GRAFANA WAS ONLY HALF-ENFORCED: the datasource the ruling KEEPS cannot resolve. Found
      **AUDIT 2026-09-20 — VERIFIED DONE (uncommitted).** All three datasource variable sets restored:
      `deployment/docker-compose.yml:178-180`, `deployment/observability-local/observe-docker-compose.yml:100-102`,
      `deployment/poc/docker-compose.yml:140-142`, plus `deployment/.env.sample:63-65`.
      unbriefed, fixed 2026-09-20 (uncommitted).** `datasources.yml` interpolates
      `POSTGRES_DATASOURCE_HOST`, `POSTGRES_DATASOURCE_DB` and `POSTGRES_READONLY_PASSWORD` **from the
      container's environment.** Commit `4bcc17e1` *"Align Grafana dashboards to merged telemetry signals"*
      **deleted all three from ALL THREE compose stacks** (proved by `git log -S`; `f40fd81a` had added
      them). Phase E's M-GRAFANA repair restored `datasources.yml` **and the panels — but not the values
      they read.**
      **So on a stack booted from `obs-merge`, `flynapse-postgres` provisions with an empty url and
      database, and the exact-spend panels the ruling exists to keep read NOTHING.**
      **And here is why nobody saw it: the PRIMARY checkout still has them**, which is why the running
      container works and this branch does not — **the same sibling-checkout hazard, one layer out from
      code and into the deployment.** Restored in all three stacks, with a guard that **derives the
      requirement from the provisioning files** rather than from a list of three names.
- [x] G.79 **G.49(6) is REFUTED — strike or rewrite it.** I recorded that
      **AUDIT 2026-09-21 — DONE.** G.49(6) is struck and rewritten in place. The code fix is in the
      copilot-mro WORKING TREE: `scripts/ad/seed_ad_notification_subscription.py:92-96` warns with the
      registry's `total` when it holds more than one tenant; it lands with that lane's commit.
      `copilot-mro-obsm/scripts/ad/seed_ad_notification_subscription.py` leaves tenants past the 50th
      "silently unseeded and unable to subscribe". **Wrong in mechanism:** the script takes `tenants[0]` —
      **the OLDEST row by `created_at`** — so with or without the 50-cap **that is the same row.** Raising
      the limit changes nothing; tenants 2..N are equally unseeded, **by declared v1 design**. *"Paging
      there would have been theatre."*
      **What IS wrong at that site, and was fixed:** it seeds 1 of N and **prints the same "Done" as
      seeding all of them.** The registry's `total` is now surfaced as a warning.
- [x] G.80 **The AD roster defect was WORSE than silent — it produced a MISATTRIBUTED diagnostic.**
      **AUDIT 2026-09-20 — VERIFIED DONE (uncommitted).** `ad_notification_dispatcher.py:1162`
      (`_active_tenant_recipients`) now pages with `_TENANT_PAGE_SIZE`/`_TENANT_PAGE_LIMIT`, dedups,
      compares against `total` and raises `TruncatedTenantRegistryError`.
      `ad_notification_dispatcher.py:554-570` narrows the roster to the tenants its events name and treats
      a tenant it cannot find as **deleted**: it drops the events, counts `events_without_audience`, and
      logs *"tenant X not resolvable from TenantService"*. **A tenant truncated out of page one is
      perfectly resolvable — the log blamed the registry for a page size.** Fixed by the same change.
      **Two more facts from that lane worth keeping:** `ORDER BY created_at` **has no tiebreaker**, so two
      tenants sharing a timestamp across a page boundary can be returned twice and another skipped — which
      is why the completeness check compares the **deduplicated** roster against `total`, catching
      truncation, that skew and an unaddressable row **with one comparison.** And the decision, taken in
      order: **page to exhaustion AND then refuse**, because *"refusing alone would give a >50-tenant
      estate NO AD notifications at all — worse than today for tenants 1-50. Paging alone would silently
      accept a reader that came up short."* The refusal is raised **before any notification row is
      written**, so a refused run dispatched to **nobody, not to some** — and for an unattended regulatory
      fan-out *"a refused run is recoverable; a partial send reported as success is not detectable by
      anything downstream."*
      **IMPLEMENTATION NOTE (review r7b P1-1, `copilot-mro-obsm-r7b 8be6f663`, 2026-09-21):** the
      misattribution was reachable again through a TRANSIENT error: a failed registry page served an
      empty roster, and every event was logged "tenant X not resolvable" for a tenant that exists.
      Closed — the read refuses instead, and a behavioural test asserts no event is dropped, no tenant
      is blamed and no driver text is logged (mutation-proved: `return []` restored → 5 red).
- [ ] G.81 **Every `scripts/ad/*` CLI run from the merged worktree reads the PRE-MERGE `utils` and `core`.**
      `copilot-mro-obsm/scripts/ad/_common.py:26-37` (`add_repo_paths`) carries a false claim: that `utils`
      and `core` *"stay literal siblings … single, un-worktreed repos, not duplicated per branch."*
      **`/home/aditya/Code/utils-obsm` and `/home/aditya/Code/core-obsm` both exist.** Reported, not fixed
      — it is the G.26/G.53 family and belongs to that lane.
      **The neutral-cwd hazard reproduced again for the record:** `poetry -C api run python -c "import
      core, copilot_mro, utils"` resolves **all three** to pre-merge checkouts. Harmless for that lane's
      own work — `core`'s `tenant_service.py` is **byte-identical across both checkouts** (`diff` empty) —
      **and it said so rather than letting anyone infer otherwise.**

- [ ] G.82 **OWNER: fail-closed on a failed authz invalidation — argued both ways, and the elegant seat
      is NOT where the item assumed.**
      **For raising:** this is the one case where the cache's answer is a **security** fact. Today a
      revoke returns **200** while the revoked grant keeps being served for up to **3600s**, and the only
      trace is one ERROR line. A 500 tells the caller to retry, and a retry is the correct remedy.
      **Against:** the invalidation runs **after the response is produced**, on a path that today degrades.
      Raising there turns a Redis blip into a 500 **on a mutation that already succeeded in Postgres** —
      so the caller retries a write that was committed. **The caches expire on their own, so the failure
      window is bounded by the TTL; a 500 on a committed write is unbounded confusion.**
      **And the seat matters:** if you want fail-closed, *"the elegant seat is NOT a raise at the sweep —
      it is the middleware refusing to return 2xx for a declared-but-unconfirmed invalidation"*, which
      needs a return value the invalidation path does not have today. **Bigger than this item.**
- [x] G.83 **Two sentences that are FALSE for one-shot kinds, one of them estate-wide.**
      **AUDIT 2026-09-21 — DONE, BACKEND CONTRACT INCLUDED.** Core `0609ad2`: `Automation.runs_on_schedule`
      (`models/schemas.py:310`), a property, no column. Api `b6471c8`: the missed-run notice's closing beat
      reads it (`automations/announcements.py:204`) and the `automation_run_missed` payload carries it
      (`:305`). Dashboard `afd6300` + `004a809` (the latter corrects two sentences `afd6300` made false).
      **(b) moved `bbbf0fa` → `b6471c8`:** `bbbf0fa` was the tests; the production landed in `b6471c8`, which
      also **deleted the `_NEVER_RESCHEDULED_KINDS` mirror** described below in favour of the model field —
      and `test_missed_run_notice_copy.py:117` now asserts its absence.
      **(a) BUILT 2026-09-20 in `dashboard-obsm` — and DELIBERATELY UNCOMMITTED, including the test edit**,
      because *"committing a guard whose production half is uncommitted would make `obs-merge` RED at its
      own HEAD — reproducing G.43's exact defect."* The frontend half is **inert until the backend ships
      the field**, and every guard proves the inert case renders exactly what shipped before.
      **THE BRIEF NAMED ONE FALSE SENTENCE. THE FAMILY GREP FOUND SEVEN, PLUS A MISSING ROW.** All reachable
      for a run-once automation, because the manual path exempts the kind from the disabled gate and then
      *"every other gate below binds unchanged"* (`loop.py:1138`), and the executor resolves entitlements
      **before** dispatching on kind: `previous_run_active`, `grace_expired`, `entitlements_unresolved`,
      `entitlements_indeterminate` (**both halves false**), `reaped`, `unavailable` (the briefed one),
      `access`, plus the `RunHistoryPanel` empty state.
      **THE WORST ONE WAS IN NEITHER BRIEF, AND IT IS A P0: `one_shot_kind` had no copy row at all.**
      `loop.py:276` defines it, `loop.py:1016` writes it, and it is recorded as a real run row. It is
      **missing from BOTH census lists** in the frontend's test — including the one claiming to be *"read
      off their definition sites"*. And unlike every other unmapped reason, **a refusal writes a `reason`
      and no `error`, so the error-category fallback that quietly covers the other ten cannot cover it.** It
      fell through to the echo: *"This run ended: one shot kind. If it keeps happening, contact support…"*
      — **a user whose job is behaving exactly as designed, sent to support.** Now authored.
      **A SECOND P0: the api fix does not reach the surface most people read.** The bell renders the
      announcer's `message` **only when the frontend has not learnt the outcome** —
      `body: (outcome?.known ? outcome.text : undefined) ?? announced ?? …` — so for `grace_expired`,
      `previous_run_active`, `reaped` and every other known reason, **the frontend's sentence wins and
      G.83(b)'s repaired one is discarded.**
      **BOTH candidates already on the wire were ruled out WITH EVIDENCE, and one of them is what this plan
      recommended.** `next_run_at` is unsound (`loop.py:1015` refuses a one-shot kind *"whatever its toggle,
      its slot or its window say"*, so the row can carry a non-null value that will never fire).
      **`enabled` is unsound and the plan's own G.83(b) recommends it** — it conflates a user-switched-off
      chat automation, where *"switch it back on"* is correct, with a run-once job **created disabled by
      design**, for which switching on buys a refusal at every slot forever. **Same boolean, opposite
      correct copy.** **No kind list was put in the frontend.**
      **A design correction made mid-flight, and the reasoning generalises:** the first draft marked three
      rows as promising nothing because they had been traced unreachable in the scheduler. **That was
      reversed** — it *"made this module's correctness a function of my reading of another repo's control
      flow, invisible from the frontend and silently falsified by any backend change."* Every
      promise-carrying row now has a variant whether or not it looks reachable, and **the guard is total
      with no exemption list.**
      **The anti-drift mechanism is the TYPE, not a lint:** the new field is **required**, so a new copy row
      cannot be added without deciding. Proved by `TS2741`.
      **The decisive mutation: gutting the phrase list left 38 of 39 tests still passing** — only the anchor
      test caught it. **Without that anchor every negative assertion in this work would have been defeatable
      by deleting a list.**
      **BACKEND CONTRACT OWED — dispatched to core and api 2026-09-20.** (1) `runs_on_schedule: bool` on the
      `Automation` response model, on LIST and GET; `false` = the scheduler never fires it **whatever
      `enabled`/`next_run_at`/`schedule` say**; `true` = its schedule is honoured **including while switched
      off**. **Put the frozenset in core** beside `KIND_CHAT`/`KIND_AD_MATERIALIZE` so the wire field is a
      projection rather than a **third** mirror of `loop.ONE_SHOT_KINDS` and `_NEVER_RESCHEDULED_KINDS`.
      (2) the same field in the `automation_run_missed` payload.
      **(b) CLOSED 2026-09-20 (`api-obsm bbbf0fa`).** The closing clause is now chosen by kind, with
      `_NEVER_RESCHEDULED_KINDS` **mirrored from and equality-pinned to** `loop.ONE_SHOT_KINDS` — so the two
      cannot drift. 12 parametrised cases; mutation M4 (delete the gate) fails all 12. **`loop.py:302`
      verified exact.**
      **Prose family grepped, and the repair is honestly PARTIAL:** `loop.py:1822-1826` said the sentence
      ends *"**every** notice"*, which is now false and is corrected — but it **records the `enabled` case,
      not the one-shot case.** Flagged rather than quietly widened.
      **(a)** `unavailable`'s frontend sentence says *"the next slot retries"* — but `ad_materialize` is a
      **one-shot kind** (`loop.py:302`), so **the owner must press again.** The posture (do not escalate)
      is right and it is still far better than "contact support", **but since G.22 the dashboard discards
      the stored detail sentence and renders category copy only, so the detail cannot repair it.** This is
      the **counter-case** to the dashboard lane's "a reason row would demote the category sentence":
      **here a reason row would genuinely help.**
      **(b)** *"It will try again at its next scheduled time"* ends **every bell notice** — also false for
      every one-shot. Pre-existing and estate-wide; the fix is **a template reading `enabled`, not a
      branch**, which `loop.py`'s own docstring already records.

- [x] G.40 **CLOSED 2026-09-20 (`utils-obsm f821135`, tests committed; two production edits left uncommitted — **both since COMMITTED under M-COMMIT, `fffa470`**, per utils packet row LB-03)**
      **The destructive path was REAL, and there were TWO of them.** The plan's `:1362-1367` was wrong and
      the auditor's `:1383-1388` was right. `python -m utils.s3_service` reached a real
      `self.s3_client.delete_object(...)` loop at `utils/s3_service.py:732` with **no confirmation and no
      gate**, deleting every key containing `fm` under `s3://flynapse-copilot/akasa/mro/AIPC/processed/`
      **while printing `Would delete {file}` for each one it had already destroyed.**
      **NOT BRIEFED — found while building the guard:** `utils/dynamodb_service.py:1192-1194` carried the
      identical defect, `delete_by_contains("mro-documents", "document_id", "AD_FAA_", dry_run=False)` —
      **overriding that method's own `dry_run=True` default** — with a scratchpad of further `dry_run=False`
      recipes commented out beneath it. `dynamodb = DynamoDB()` is instantiated at module import and the
      module is live (`amos_parser:2567`). Same blast radius, one table instead of one bucket.
      **The fix removed both `__main__` blocks rather than flipping the flag**, and the reasoning is the
      point: *"`dry_run=True` leaves a live destructive call one keystroke from destruction, aimed at a
      hard-coded production resource, with no caller who chose it"* — and it would have made the print
      **accidentally** truthful rather than correct, since "Would delete" is printed whatever the flag says.
      Neither function has a single caller anywhere in the estate outside those two mains.
      **Guard** `tests/unit/safety/test_module_mains_cannot_delete.py` (new, 12 tests): no call destroying
      stored state may appear in a `__main__` anywhere in `utils/`, callee matched by **prefix**
      (`delete`/`drop`/`purge`/`destroy`/`truncate` + `rmtree`/`rmdir`) so **the sixth wrapper the estate
      invents is covered without editing the guard**, and **keyword arguments are deliberately not read —
      `dry_run=True` is no excuse.** Floor AND two named witnesses, each asserted present, still defined and
      still matched by the rule's own prefixes, so a rename surfaces instead of silently emptying the scan.
      Mutation-proved with grep-confirm and md5-verified restore.
      **A second guard was REFUSED with its reason recorded in the docstring:** *"a print may not contradict
      the flag it runs under"* is **not decidable** — the same package spells `f"DRY RUN: Would delete …"`
      **correctly** inside an `if dry_run:` branch at `:715-716`, so such a guard would either flag the
      correct site or match nothing, and matching nothing passes vacuously forever.
      **Still open, deliberately not taken:** `delete_files_by_keyword(..., dry_run: bool = False)` at
      `s3_service.py:631` **still defaults to deleting**, inconsistent with `delete_by_contains`'s `True`.
      With the main gone it is reachable only by a caller who wrote the call, and there are zero such callers
      — but `flynapse-utils` is a **published package**, so flipping the default is a breaking API change and
      **the owner's decision.**
- [x] G.86 **P0, MERGE-INTRODUCED: the WORKOUT tool fails on every SUCCESS path in any INFO-level
      **CLOSED 2026-09-20 (`copilot-mro-obsm 6058e662`, tests only; 2 production edits UNCOMMITTED).**
      **Every load-bearing claim verified at source, including the whole INFO chain** (`main.py:12` →
      `logging_config.py:67` → `intercept.py:87 logging.basicConfig(..., force=True)` → `config.py:105`
      default `"INFO"` → `api/.env:3`). Reproduced: **4 failed at `--log-level=INFO`, 16 passed at
      WARNING.** Merge attribution confirmed — the pre-merge sibling has the **same stdlib binding**; the
      merge changed the **call**, not the binding.
      **The brief's "118 keyword-style callers" DOES NOT REPRODUCE — an independent AST walk gives 136.**
      Definitional, not substantive; **the two numbers the conclusion rests on (15 stdlib binders, 2 in the
      intersection) match exactly**, and the intersection is **0 after the fix**.
      **NEITHER briefed option was taken, and the reason is measurable.** Switching to loguru would have
      **silently un-formatted NINE other call sites** — loguru formats with `str.format`, so `%`-style with
      extra positional args does **not** raise (measured: `logger.info("saving failed: %s", "boom")` emits
      `saving failed: %s`), trading a loud defect for a quiet one and turning a 2-line fix into a 9-call
      migration. And `%`-style would revert the commit's intent: **the defect is not that it wanted
      structure, it is that it used the wrong spelling for the logger it was on.**
      **The fix is `extra={...}`** — the stdlib's own structured mechanism, inside `Logger._log`'s accepted
      set, **and the structure survives to loguru**: `InterceptHandler.emit` forwards non-standard record
      attributes into `logger.bind(**extras)`. Measured end to end through the estate's own handler. It is
      also **already the convention — 84 `extra=` sites in `copilot_mro/`**, including another of the 15
      stdlib binders. **These two modules were the only stdlib binders that got it wrong.**
      **Guard, in two parts.** Behavioural: an **autouse fixture forcing root DEBUG file-wide**, because
      *"relying on `--log-level` would be a regression test that only fires when someone remembers a flag"* —
      and it is mutation-proved **at the lane default with no flag**. Static and general
      (`tests/unit/infra/test_logger_calls_match_their_binding.py`, 13 tests): one rule — **the call must be
      legal for the binding** — in three limbs: a stdlib logger given a non-stdlib keyword (`TypeError`); an
      `extra={…}` key colliding with a `LogRecord` attribute (`KeyError` from `makeRecord`, **same latency,
      same swallow**), with the reserved set **computed from a blank record** so a new Python version needs
      no edit; and a loguru logger given `%`-style (**no error at all — arguments silently dropped**).
      **The decoy was asked and answered:** *what edit satisfies limb 1 while defeating its purpose?* Switch
      the binding to loguru and keep the keywords. That exact edit was made — **limb 1 went quiet, correctly,
      and limb 3 fired.** That is why limb 3 exists.
      **A measured lesson about floors worth keeping:** repointing the scan at `scripts/` failed three limbs
      — **but the BINDER floor did not fire**, because `scripts/` happens to hold 10 `getLogger` files.
      **The file floor and the named witness are what actually catch a moved directory, not the binder count.**
      **Structural weakness recorded, deliberately not fixed:** the success-leg log, `mark_data_answer()` and
      the `return` all sit **inside** the `try`, so **any** failure in the last three statements reports
      success as failure. Moving the terminal log out of the `try` would make the class impossible rather
      than merely detectable. **Owner's call — it is a refactor.**
- [ ] G.93 **UNBRIEFED, FOUND IN PASSING: eight loguru `%`-style sites are corrupting log lines TODAY.**
      `techpub_tools.py:1792`, `js_extractors.py:207,261`, `mel_parser.py:859`,
      `pdf_parser.py:4295,4306,4317,4326` — each ships a literal `%s` with its argument **dropped**, because
      loguru formats with `str.format` and raises nothing. **Four of them are Postgres save errors that log
      no error.** Not fixed (five unrelated modules, and the change alters logging *output* in parsers
      rather than the P0's defect) but **registered in `LOGURU_PERCENT_EXEMPTIONS` with per-site reasons and
      a staleness test**, both mutation-proved: removing an entry makes the rule fail on that site, and
      making one stale fails the staleness test. **Owner: eight one-line `{}` changes.**
      **An acknowledged blind spot, named in the docstring rather than papered over:** the AST binder
      detection would not recognise `from logging import getLogger as gl`. No site in the package does it,
      and widening to "any call returning a Logger" is **not statically decidable**.
      deployment.** `copilot-mro-obsm/copilot_mro/app/services/agent_shared/tools/workout/resolve_workout.py:41`
      binds a **stdlib** logger and `:871` — on the terminal **success** leg — calls it with **loguru-style
      structured keywords**. `logging.Logger.info` accepts only `exc_info`/`stack_info`/`stacklevel`/`extra`,
      so it raises `TypeError`, and that call sits inside the function's broad `except Exception` at `:891`
      — **so a successful parts resolution is converted into `ToolError(code='workout_resolve_error')` and
      the model is told the tool failed.**
      **Why no test caught it:** `Logger.info` short-circuits on `isEnabledFor(INFO)` and an isolated pytest
      lane leaves the root logger at WARNING. **Production does not** — `main.py:12` → `utils.setup_logging`
      → `intercept.install` → `logging.basicConfig(force=True)`, `utils/config.py:105` defaults to `INFO`,
      and `api/.env:3` sets `LOG_LEVEL=INFO`. Reproduced **3/3 with the level as the only variable**:
      `--log-level=WARNING` → 16 passed; `--log-level=INFO` → **4 failed**.
      **Merge-attributable:** the pre-merge sibling `copilot-mro@417df303` has the correct `%`-style call at
      the same line, and `git log -S has_workorder` names **`54a01f39 "chore: checkpoint agent observability
      foundation"`** — this merge's own observability work broke a product tool.
      **Second site, narrower trigger:** `workout_gate.py:738` on a stdlib logger, fires at `DEBUG`, swallowed
      by `except Exception` at `:745`, after which `draft_query` returns `""`.
      **Blast radius measured, exactly two files:** 118 modules use keyword-style logger calls, 15 bind a
      stdlib logger, and the intersection is precisely these two — every other keyword-style caller is on
      loguru and correct. **The generalisable guard: no module binding a stdlib `logging.getLogger` may call
      it with non-stdlib keywords** — decidable by AST, and it would have caught both. Routed to the live
      copilot-mro implementer.
- [x] G.87 **P1 latent: the HTTP semconv opt-in is set AFTER the door it must precede.**
      **INDEPENDENTLY CONFIRMED 2026-09-20 FROM A SECOND TREE, and it explains six failures nobody had
      root-caused.** The api implementer found `api-obsm/tests/conftest.py` *deleting*
      `OTEL_SEMCONV_STABILITY_OPT_IN` for the whole session — but **that variable is a process-wide LATCH**:
      the first instrumentor to call `_OpenTelemetrySemanticConventionStability._initialize()` fixes the
      mode forever. Run alone, the OTel lane won the race and latched `HTTP`; **in the full suite an earlier
      lane latched `DEFAULT` first, so the new-semconv attributes were never written** — which is exactly
      the **6 pre-existing baseline failures**, all dying on a bare `KeyError`. Setting it at conftest
      import retires all six (**1557 passed, 0 failed**). **This is a G.54 instance as well as a G.87 one.**
      **The production half stands and is now reported by two independent lanes:** `bootstrap.py:171` sets
      the variable but **never forces the latch** — the same "dead letters" defect its own comment at
      `:173-180` fixes for `OTEL_PROPAGATORS` one line below, where it *does* install the global. **In
      production, anything that instruments before `bootstrap()` leaves the gateway emitting old-semconv
      HTTP attributes silently, with every dashboard built on the new names reading nothing.**
      (`api-obsm/tests/integration/automations/conftest.py`'s `shutdown_telemetry` fixture docstring
      describes a **second instance of this same process-global class** — see G.92.)
      `flynapse-otel/flynapse_otel/bootstrap.py:171` does `os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN",
      "http")`, but OTel reads that variable **exactly once** and caches it on a class global
      (`opentelemetry/instrumentation/_semconv.py:217`, guarded by `_initialized`, called from
      `OpenTelemetryMiddleware.__init__`). **The first middleware constructed in the process decides the
      semconv generation for the whole process.** Two things make it fragile rather than theoretical: the
      `setdefault` sits **below the `OTEL_SDK_DISABLED` early return** (`:151-161`), so a process starting
      with the SDK disabled never sets it at all; and `api-obsm/flynapse_api/main.py:409` calls
      `instrument_gateway` **at module import**, safe today only because a comment convention puts
      `setup_logging` at line 8. **Nothing enforces it.** When the order slips, spans carry `http.method` /
      `http.status_code` / `http.target` and the histogram is `http.server.duration` (ms) instead of
      `http.server.request.duration` (s) with `http.route` / `url.path` — **exactly the names the merged
      dashboards and alert rules query.** Measured failure: `KeyError: 'http.request.method'`.
      **The elegant fix is one the file already demonstrates eleven lines below**, where it compensates for
      the same hazard on `OTEL_PROPAGATORS` (*"the env default alone would be dead letters"*, then
      `set_global_textmap(...)`): move the `setdefault` above the early return and force
      `_OpenTelemetrySemanticConventionStability._initialize()` immediately after.
      **This is what the six `api-obsm` combined-only failures ARE** — a symptom the suite catches only in
      one process, while the defect is in production code. **`flynapse-otel` is outside the seven trees:
      owner ruling owed** (see also G.85 — that makes **two** flynapse-otel defects, both tier-0-shaped).
- [ ] G.88 **Two lines in test support account for roughly two-thirds of the gate's blind spot.**
      `tests/_package_stubs.ensure_package` seeds placeholder packages under **real dotted names at import
      time and never restores them**, and `tests/agent_services/reporting/test_sql_report_service_card.py:24-26`
      then **deletes every `copilot_mro*` entry whose `__file__` is None — which includes the real namespace
      package.** A later genuine import short-circuits on the surviving `sys.modules["copilot_mro.app"]`, so
      `setattr(copilot_mro, "app", …)` never runs and `monkeypatch.setattr("copilot_mro.app.…")` dies with
      `AttributeError`. **97 occurrences of that message in one process.**
      **It is NOT order-dependent, which is worse** — pytest imports every selected test module during
      collection, so one file's import-time `sys.modules` mutation reaches every test in the session no
      matter where it sits. Fix: `ensure_package` must set the parent attribute, and the `__file__ is None`
      sweep must stop deleting real namespace packages.
- [~] G.89 **The vacuous root-anchoring tautology exists in 11 copies across 9 repos.**
      **core DONE 2026-09-21 (`core-obsm 6cab7d9`):** checkout census from disk + per-checkout proof + posed workspace from two depths (old test passes under the mutant, new proofs fail). Review running.
      **AUDIT 2026-09-21:** fixed in **`utils-obsm`** (`f821135`; the residual `repo_root(__file__) == REPO`
      X==X line at `:183` is being removed by the utils lane now), **`flynapse-otel`** (`f5b9949`) and
      **`api-obsm`** (`08f54f9` — **which carries the SAME residual X==X line, at `:176`**). **Remaining in the merged trees: `core-obsm` and `copilot-mro-obsm`**, both
      still `sibling_repo(__file__, REPO.name) == REPO.parent / REPO.name` at `test_root_anchoring.py:93-94`.
      `gtm` and `shift-optimizer` are outside the seven trees; the pre-merge copies are fixed by the merge.
      `tests/unit/infra/test_root_anchoring.py::test_sibling_repo_of_our_own_name_is_the_other_checkout_not_ours`
      asserts `sibling_repo(__file__, REPO.name) == REPO.parent / REPO.name` — **`REPO == REPO`**, under a
      docstring claiming it proves a DIFFERENT checkout. Present in `api`, `api-obsm`, `copilot-mro`,
      `copilot-mro-obsm`, `core`, `core-obsm`, `flynapse-otel`, `gtm`, `shift-optimizer`, `utils` and
      `utils-obsm`; **fixed in `utils-obsm` only**, where a real proof was available and the parametrized
      test id now names the checkout it read. In the twin-less repos (`gtm`, `shift-optimizer`,
      `flynapse-otel`) it is the same tautology with no sibling to find — those need the explicit skip-gate,
      not a deletion.
      **flynapse-otel CLOSED 2026-09-21 (`f5b9949`, test-only, not pushed).** The tautology is replaced by
      utils-obsm's real proof plus a posed-workspace test that runs every time (a fake twin under
      `tmp_path`); the real-workspace twin case SKIPS visibly with a reason. Mutation (`sibling_repo` returns
      the caller's own repo) fails the posed test; the old test PASSED under it — vacuous, confirmed. Suite
      242 → 244 passed + 1 skip; controller re-ran the file: 11 passed, 1 skipped. **Residual found:
      utils-obsm `f821135` still carries `assert repo_root(__file__) == REPO` (literal X == X) inside its
      parametrised test** — queue for the next utils lane. api-obsm copy is with the api implementer.
- [ ] G.90 **The PRE-MERGE `utils` checkout is still armed.** `/home/aditya/Code/utils` carries both
      destructive mains removed by G.40 — `utils/s3_service.py:1193-1198` and
      `utils/dynamodb_service.py:1192-1194`, the latter verbatim
      `delete_by_contains("mro-documents", "document_id", "AD_FAA_", dry_run=False)`. **`python -m` there is
      live today.** That checkout is on another branch and may carry another session's work, so it was
      reported and NOT edited. **Owner: this is the same repo, so the fix arrives when `obs-merge` merges —
      the question is whether that is soon enough.**
- [~] G.91 **The sibling-checkout hazard is live in PRODUCTION SCRIPT code, where no tests sweep reaches.**
      **core DONE 2026-09-21 (`core-obsm f0d7ef5`, review running):** `scripts/_workspace.py` replaces 6 bare-name sites + 5 marker walks, pinned to `_root.sibling_variant`; the sweep now reads `scripts/` + `setup/` (caught one more). **Remaining: copilot-mro `migrate_tenancy_schema.py:1127`;** `_workspace.py` must follow api's git-family redesign when it is carried.
      **AUDIT 2026-09-21 — SIX bare-name sites in `core-obsm/scripts/`, not two:** `run_db_lane.py` (`utils`
      `:88`, `copilot-mro` `:282`), `backfill_chat_turn_facts.py:110`, `purge_product_events.py:54`,
      `set_tenant_content_capture.py:59`, `review_improvement_findings.py:56`. **Plus copilot-mro
      `scripts/migrate_tenancy_schema.py:1127`** — `Path(__file__).resolve().parents[2] / "shift-optimizer"`,
      bare-name **and** depth-coupled. `api-obsm`, `utils-obsm` and `flynapse-otel` have no `scripts/`;
      `dashboard-obsm` and `iac` are clean (the dashboard's trigger-contract fixture resolves its sibling
      through `siblingName`, so it reads `core-obsm` from a worktree).
      `core-obsm/scripts/run_db_lane.py` resolves `MIGRATION_SCRIPT = WORKSPACE / "copilot-mro" /
      "scripts/migrate_tenancy_schema.py"` and `UTILS_ROOT = WORKSPACE / "utils"` **by bare name**, so from
      `core-obsm` both point at the PRE-MERGE checkouts; `scripts/backfill_chat_turn_facts.py:110` does the
      same for `utils`. **The estate's `tests/` sweeps do not reach `scripts/`**, which is why every audit so
      far reported the bare-name family as closed. Same shape as **G.81** (copilot-mro's `scripts/ad/*`) —
      **treat them as one item and extend the sweep's scope to `scripts/`, not just `tests/`.**
      (`core-obsm/tests/conftest.py` also resolves by bare name, but append-only and documented as
      deliberate so `PYTHONPATH` outranks it — that one is fine.)
- [~] G.92 **A test-fixture landmine that cost 38 `RecursionError`s, visible ONLY in a combined run.**
      **RE-PLANNED + BUILT (night): utils-obsm `54952ee`** — a RUNTIME seat refuses a foreign private global left changed after a test's teardown; the static scan resolves targets. Unreviewed (round 3 due).
      **AUDIT 2026-09-21 — THE INSTANCE IS CLOSED** (`core-obsm d368c7a`: the `exported_spans` fixture in
      `tests/unit/observability/test_core_spans_withhold_exception_text.py` patches the module's own
      `get_tracer`; `_TRACER_PROVIDER` now appears only in that fixture's docstring across the merged
      trees). **Only the PATTERN guard remains — the utils lane is building the reference guard
      (2026-09-21).**
      **PATTERN GUARD BUILT + REVIEW-FIXED (utils-obsm `4303d78`, round fix `ebe82ce`).** First review found
      a P1 (tuple targets — the exact G.92 pair — `patch`/`mp` receivers, `vars()`/`__dict__`, computed
      setattr); the fix recognises MonkeyPatch receivers by construction, covers `setitem`/`delitem` on a
      module dict, `patch.dict`, `patch.multiple`, `object.__setattr__`, `mocker.patch`, refuses computed /
      f-string / unreadable `**kwargs` targets; 23 review spellings pinned by line. Declared gaps: class
      privates, a module reached through a value, a target held in a variable. utils suite 1671 + 1 xfail.
      **Round-2 review REOPENED it (2nd P1 on this mechanism)** — receiver-by-spelling detection still misses
      `monkeypatch.context()` instances (live in shift-optimizer), `patch.multiple(**{…})`, attribute-chain and
      string targets, dotted/aliased patchers, `t = trace`, `__dict__.update`. **Re-plan ordered (design
      first):** static target-resolution (import → `ModuleType`, classify by resolved `__name__`/`__file__`) vs
      a runtime seat check of foreign private-global identity across each test's full teardown.
      Port to the other trees = shared-detector owner question.
      A fixture that saves `trace.get_tracer_provider()` and restores it into `trace._TRACER_PROVIDER` puts
      the **`ProxyTracerProvider` into the global that proxy delegates to** — so every later `get_tracer`
      recurses forever. It produced **38 `RecursionError`s across the automations db lane in the combined
      run while every file was green in isolation** — i.e. a textbook G.54 instance, found by an implementer
      rather than by the gate. Fixed in `core-obsm` by injecting at the module's own `get_tracer` seam, with
      no process globals touched. **`grep -rn "_TRACER_PROVIDER"` over the four `-obsm` trees finds no other
      instance** — so this is closed, but the PATTERN (a fixture restoring a library's private global)
      deserves a guard, and that guard belongs with G.54's whole-suite ruling.
      **Related lane fact:** `core-obsm/scripts/run_db_lane.py` provisions `--registry core`, which does not
      create `chat_turn_facts` (a copilot-mro relation), so the analytics db file needs
      `POSTGRES_DB=copilot_mro_test`. Pre-existing, and the two original cases had the same dependency.
- [x] G.94 **A THIRD wrong statement of the trigger vocabulary — this one in the dashboard's TypeScript.**
      **AUDIT 2026-09-21 — DONE (`dashboard-obsm afd6300`).** `lib/api/automations-api.ts:90-94`
      `AUTOMATION_RUN_TRIGGERS` is `scheduled` / `manual` / **`one_shot`**, and `AutomationRunTrigger` is
      derived from it (`:96`). Pinned by the generated `contracts/automation-run-triggers.json` and
      `tests/unit/automations/runTriggerVocabulary.test.tsx`. **Caveat the contract states about itself:**
      CI checks out the dashboard alone, so the backend comparison runs only where a sibling core checkout
      exists — a developer check, not a gate.
      `dashboard-obsm/lib/api/automations-api.ts:64` declares `AutomationRunTrigger` as
      `'scheduled' | 'manual'`, while core defines **three** (`TRIGGER_SCHEDULED` / `TRIGGER_MANUAL` /
      `TRIGGER_ONE_SHOT`, `schemas.py:38-45`). **Reported, not changed** — it is unreachable today because
      one-shot runs carry `automation_id IS NULL` and the panel lists per-automation. **It belongs with
      G.64(a)**, which is about this exact vocabulary and which api already closed with
      `test_queue_trigger_vocabulary.py` — **and it strengthens that item, because the estate now holds a
      third wrong statement of the same list.** Worth checking whether that pin covers all three values or
      only the ones api emits; if the latter, it could not have caught this.
- [~] G.104 **M-TRACEBACK SIZED (census 2026-09-21, AST scan, prod + `scripts/`, working tree).** Exception
      **CORE HALF DONE 2026-09-21 (`core-obsm a0044d5..fdccdae`, 6 commits; two reviewers running).** Guards
      first (register seeded from the census at 155), then the 500-body leak (`a1c8a3a`), the `http_errors`
      funnel + 19 callers (`7a27ae5`), `CommentDatabaseError` constant + `from exc` (`3abd885`), guards
      hardened against the shift-optimizer defeats (`be6ab9f`), the remaining 34 files (`fdccdae`). **Both
      registers EMPTY.** Core unit+api+authz 2626 → 2763 (with the other core work). copilot-mro and
      telegram-bot halves: telegram-bot done (`fa37f7e`); copilot-mro waits for its live lane.
      text reaching a log/print: **core 128 sites in 36 files (90 HIGH)** · **copilot-mro 689 in 169 files
      (357 HIGH)** · api 0 (control; guard green, register empty) · **telegram-bot 110, stdlib, no guard** ·
      shift-optimizer 3. **~80% codemod-safe** (constant or id-only messages); the rest — ~175 hand edits —
      interpolate content (`{to_email}`, `{s3_key}`, `{query}`), print, pass the text through a helper, or
      wrap a traceback into a new exception's message. **WORST FIRST — exception text in RESPONSE BODIES:**
      `core/resources/document_viewer/services/document_service.py:214/217` → `document_endpoints.py:211,265`
      puts psycopg2 text into a **500 body**; `http_errors.py:53` renders `format_exc` for **55 callers in 13
      routers** (a unique-violation DETAIL quotes the email at `user_endpoints.py:957`). **Recipe:** loguru
      `logger.error("constant", id=..., **failure_fields(exc))` (never `extra=`, never `%s`, never a brace in
      the message); stdlib `logger.error("constant", extra=failure_fields(exc))`; helpers without
      the exception in hand use `failure_fields(sys.exception())` (py3.11). **Guard:** port api's
      `test_gateway_logs_carry_no_exception_text.py` + utils' alias closure, scanning EVERY module with a
      debt register seeded from the census, plus helper-sink detection (`internal_error`,
      `handle_comment_exception`), `print`/stderr, and the format-string + logger-binding companion guards.
      **Side finding:** loguru stores `exc_info=True` as a plain `extra` field — no leak, but also NO
      traceback (3 core, 19 copilot-mro); the guards' docstrings claiming "loguru ignores it" are wrong.
      **Core's docs that sanction tracebacks in logs** (`http_errors.py:18-19,38`, `sweep_span.py:32`, the
      disclosure sweep test `:44-45,:821`) change under M-TRACEBACK. **Lanes:** core → queued behind its
      F1–F12 fixes (guard first, then `http_errors` chain, the response-body chain, comments wrapping, then
      codemod). copilot-mro → after the live lane lands: guard + register first, then disjoint worktrees
      (A served path ~200 HIGH-heavy · B parsers 241 · C other services ~200 · D scripts 47). telegram-bot →
      sent to its live implementer. Scan tools: `census.py` / `mech.py` in the session scratchpad.
      lane D: 101/102 sites converted at 3637540d (`copilot-mro-obsm-tbD`, off 735f8213); held: 1 site,
      `seed_dev_tenant.py::main` ABORTED print (script-authored refusal text pinned by 9 tests) — needs a ruling.
      lane B: 266/266 sites converted at 752ba4a9 (`copilot-mro-obsm-tbB`, off 735f8213); lane register empty,
      nothing held; one change beyond log shape: `tn_parser` header-CSV handler `logger.errpr` → `logger.error`.
      Count correction (review r1 B-P3-3, recorded here because a commit message is never amended): commit
      `67cdcd03` says "31 sites / 21 entries"; the register actually moved **38 sites** in those 21 entries.
      The lane total (266) and the PAUSED note's 133 are right — only that per-commit number is wrong.
      lane A: 224/224 sites converted at 79bad4ac (`copilot-mro-obsm-tbA`, off 735f8213, 10 commits from 08c85a97);
      lane register empty (171 keys in REPAIRED), no scope-guard approvals; nothing held.
      lane C: 129/129 sites converted at ece9c60e (`copilot-mro-obsm-tbC`, off 735f8213); lane register empty,
      nothing held; beyond log shape, text that reaches a log or a body second-hand now names type or a constant:
      MRO/pilot document 500 `error`, S3 PDF processor + Lambda results/bodies, the SAD and Weaviate refusal messages.
- [~] G.105 **RULED (M-TOOL-ERRORS, owner A8 "type only, with exceptions") + BUILT in copilot-mro `d908c22c` (seat + guard + seeded register) and `01244544` (optimizer tools; stored run error reaches the model by shape); remaining register debt = the M-TRACEBACK/M-TOOL-ERRORS conversion fan-out.** **~50 copilot-mro tool results put `{exc}` into the MODEL's context** (census side finding). Not
      a log, but with capture on by default (M-CAPTURE) tool I/O reaches Phoenix spans and the tool-I/O
      archive (M-TOOLIO) — so the same exception text lands in two stores. Decide: same `failure_fields`
      treatment (type only to the model), or accept. Unscoped; not in any lane.
      **RESEARCH 2026-09-21 — the text above names the wrong store.** The tool-I/O archive was retired under
      M-TOOLIO-2 (`archive_tool_io` has no production caller). Traced end to end (`manual_retrieve.py:843-850`):
      the exception text goes (1) to the **model provider** and is replayed on every later call in the turn,
      (2) into **`llm_turn_content` BY DEFAULT** (M-CAPTURE) three or more times per row, redacted only for
      secret-shaped values, 30-day expiry, (3) to **Phoenix** only when the content copy is enabled (default
      off), and (4) to the logs. A second path: the gateway's `_error_snapshot` (`model_gateway.py:106-110`)
      stores `str(error)` of provider exceptions in the same row. **Owner question:** send only the exception
      TYPE to the model by default, keeping the message only where the model must correct its own input (SQL
      parse error `_db_core.py:103`, regex error `_docx_core.py:143`, `read_docx` invalid search)?
- [~] G.106 **The LangGraph model-call span — one site covers every gateway call (from G.3's research).**
      **Branch-only (2026-09-22):** built on `obs-merge-g106`, not yet on `obs-merge`.
      **BUILT 2026-09-21 (`copilot-mro-obsm-g106 24383dc8`, branch `obs-merge-g106`, review pending):** `chat {model}` INTERNAL per attempt via utils `dependency_span`, settled on all 7 terminal branches; `gen_ai.*` usage/cost/response id, `error.type`; content canaries clean live + exported. `cited_synthesis.py` deferred (no response id).
      Open an INTERNAL span `chat {gen_ai.request.model}` per attempt around `transport.invoke` in
      `ModelGateway.invoke` (`model_gateway.py` ~:268), so the HTTP POST nests under it; close it in the
      branches that already call `_record_content_attempt`. Attributes already in scope: operation/provider/
      request model, `gen_ai.response.id` (the join key to the Phoenix copy), finish reason, tokens, cost,
      role/purpose/profile/graph_node/attempt, `error.type`. **No content, no metrics, both withholding
      keywords `False`.** INTERNAL so the CLIENT-only dependency panels do not double. Tree: copilot-mro, after
      the live lane. Optional third site: `agent_claude/cited_synthesis.py` (outside LangGraph).
- [~] G.107 **The spec §8 content-flag check was never built — anywhere** (`SPEC:521`: `OTEL_LOG_*` and
      `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` unset in shared envs, CI check on the env templates).
      0 hits estate-wide. Assert per repo over `git ls-files` only: no active `OTEL_LOG_*` except
      `OTEL_LOG_LEVEL`; `OTEL_INSTRUMENTATION_GENAI_CAPTURE_*` absent or `false`/`NO_CONTENT`; parse keys by
      syntax (dotenv incl. `export`, compose list and map, Dockerfile `ENV`/`ARG`, HCL and ECS env blocks,
      shell heredocs); non-vacuity = a globbed file set asserted non-empty and containing the known templates,
      plus one planted decoy per syntax. Optional: shared-env files never set `LLM_CONTENT_COPY_SAMPLE_RATE`
      above 0. copilot-mro: extend `tests/architecture/agent_runtime/test_langchain_ambient_surface_policy.py`.
      **Its `OTEL_LOG_*` half goes live with G.4 whatever G.3 decides.** Trees: iac (launched 2026-09-21),
      then copilot-mro, api, core, utils.
      **iac CLOSED 2026-09-21 (`iac 89f3592`, test-only, not pushed; review running).** 43 tests, suite 163 →
      206; controller re-ran the file: 43 passed. Scans `git ls-files` only; 15 env-carrying files pinned by
      equality (two the brief missed: `alerting.tf`'s forwarder Lambda and `amplify.tf`); 14 syntax + 7
      commented-out + near-miss decoys; case-sensitive keys (a substring grep would have hit iac's
      `otel_log_group` 29 times). **No violation in tracked iac today.** `LLM_CONTENT_COPY_SAMPLE_RATE` kept
      ADVISORY — no spec line backs a hard rule and `config.py` allows a demo profile to set 1.0. Blind to
      plan-time computed keys and to env files pulled from other repos (copilot-mro `deployment/demo|poc`,
      llm-platform) — those are the remaining ports: copilot-mro, api, core, utils.
      **iac REVIEWED + FIXED 2026-09-21 (`iac 013dc89`).** The review planted 13 active flags across 8 files
      and all 13 passed; the parser was REBUILT rather than patched (`tests/_env_syntax.py`, 800 lines): PyYAML's
      composer for YAML, a hand-written bash lexer (`shlex` fails the reviewed cases), a string-aware HCL/JSON
      scanner with whole-RHS extents. Replaying the reviewer's own plants: **13/13 caught**; suite 206 → 243
      (controller re-ran: 243 passed). GenAI counts as off only for a whole-RHS literal; `valueFrom` never.
      **CI change:** the iac test step now installs `pyyaml` (`.github/workflows/terraform-plan.yaml`).
      Guard-only fix, verified by the reviewer's plants → no second review.
- [ ] G.108 **copilot-mro has NO OpenTelemetry pin test, and `pyproject.toml` ~:89 declares the gRPC exporter
      that the utils and api pin tests forbid.** Port the pin test; decide the exporter. Tree: copilot-mro.
- [ ] G.109 **Wrapper CLIENT spans over an instrumented HTTP client probably double-count on the dependencies
      board** ("Client call rate by dependency" sums CLIENT spans by `db_system, server_address`). Suspects:
      `azure_openai.embeddings` (CLIENT + `server.address` over an httpx CLIENT child), G.95's DynamoDB spans,
      and any new S3/SES spans. One convention needed; routed to the utils lane 2026-09-21 to settle with the
      panel queries in hand.
      **EVIDENCE 2026-09-21 (utils lane, panel queries read):** `azure_openai.embeddings` is CLIENT with the
      Azure host as `server.address` and no `db.system`, so it lands in the SAME `(db_system, server_address)`
      series as its httpx child in "Client call rate" and "Client error share" — **a real 2× count**; left
      because its tests encode that arithmetic and Weaviate has the same wrapper shape. DynamoDB and Weaviate
      are CLIENT with `db.system`, so they form a SECOND row, not the same series; making them INTERNAL would
      drop them from "DB client p95". **New spans follow INTERNAL-over-transport** (written in
      `dependency_spans.py`). **Owner/queue:** fix embeddings (INTERNAL or drop `server.address`) and decide
      the board's convention for db wrappers.
- [~] G.110 **ESTATE-WIDE: auto-instrumentor CLIENT spans leak exception text — the shared bootstrap hands
      **REVIEW P2s CLOSED 2026-09-21 (flynapse-otel `caaa03a`, `073b375`):** bootstrap now RAISES on a foreign pre-set global provider (all three signals); carrier-split fidelity tests; alias-proof seat detector; `_on_ending` forwards nothing; own tests assert on the LIVE span (G.114). Suite 284 → 360 + 1 skip. **Review running (Opus)** — first question: can any real entrypoint set a provider first (ADOT layer, `opentelemetry-instrument`) and now fail to boot?
      instrumentors the RAW tracer provider.** Found by the telegram-bot lane 2026-09-21, confirmed by the
      controller at source: `flynapse-otel/flynapse_otel/bootstrap.py` ~:377 calls
      `instrumentor.instrument(tracer_provider=tracer_provider, …)`, and `utils/observability/bootstrap.py`
      declares **`psycopg2`, `httpx`, `requests`, `urllib3`, `redis`, `threading`** for every api-side
      process. Those instrumentors open CLIENT spans with SDK defaults (`record_exception=True`,
      `set_status_on_exception=True`), so a failing call exports the exception MESSAGE — **a Postgres
      DETAIL with bound values, an HTTP library error quoting a URL** — as a span event and status
      description. **Every span-side sweep this project built reads OUR openers, so none could see it.**
      telegram-bot fixed its own copy with a local `_WithholdingTracerProvider`. **The fix belongs in
      `flynapse-otel`** (M-OTEL-SCOPE: fix, don't publish): wrap the provider handed to instrumentors so
      every span they open withholds — covering keyword defaults, `start_span`+`use_span`, AND direct
      `span.record_exception` / `set_status(Status(ERROR, str(exc)))` calls inside instrumentors — then drop
      telegram-bot's local copy. Also: flynapse-otel's own failed-instrumentation warning logs
      `extra={"error": str(exc)}` (~:385). Queued for flynapse-otel as soon as its reviewer finishes.
      **INDEPENDENTLY CONFIRMED AT RUNTIME 2026-09-21 by the shift-optimizer reviewer:** inside
      `optimizer.run`, a `SELECT %s::int` with a sentinel through `postgres_service`'s contrib cursor factory
      exported, on the child CLIENT span, `exception.message`, `exception.stacktrace` and a status description
      `InvalidTextRepresentation: … "SENTINEL…" LINE 1: SELECT 'SENTINEL…'::int` — **psycopg2 fills the BOUND
      VALUES into its `LINE n:` context**, so user values ship. Opener: contrib dbapi `traced_execution`
      (`start_as_current_span(name, kind=CLIENT)`, no keywords). httpx/requests/urllib3/redis open spans the
      same way (read, not run). **Tier-0.**
      **FIX BUILT 2026-09-21 (`flynapse-otel eac44c0`, + `b8e6221` test-only; `main`, not pushed; review
      running).** **Design B — scrub at the EXPORT BOUNDARY**: `bootstrap` builds the provider with
      `active_span_processor=WithholdingSpanProcessor()`, so every processor (including later ones) sits
      behind it. Removes `exception.message`/`exception.stacktrace` by NAME from events, span and link
      attributes; **drops EVERY status description** (keeps the ERROR code); backfills `error.type` from the
      last `exception.type` when the opener set none. **A was rejected against real 0.65b0 code:** utils'
      cursor factory uses the GLOBAL provider (never sees a wrapped one); the api ASGI middleware does
      `start_span` + `use_span`; ASGI's failsafe calls `record_exception` directly; `use_span` records a
      child's exception on every parent. Behavioural proof per instrumentor (real local sockets for
      httpx/requests/urllib3/redis, stubbed libpq for psycopg2, psycopg3 via its cursor factory, threading);
      15 mutation proofs; suite 244 → 284. Also: failed-apply/shutdown warnings type-only; "applied" now
      means `is_instrumented_by_opentelemetry` moved False→True. **Consequences queued:** the 6 utils tests
      whose premise read the exported description (exact edit written; apply after the utils reviewer) ·
      telegram-bot drops its local provider · shift-optimizer's constant `not_visible()` description is now
      dropped → move it to an attribute · the SDK `LoggingHandler` puts the same keys on log records (log
      pipe, open) · `failure_fields` should be hosted here (owner ruling; would otherwise be a 4th copy).
      **REVIEWED 2026-09-21: MERGE-CLEAN (0 P0 · 0 P1 · 5 P2).** No bypass anything in the estate triggers
      today; `bootstrap.py` is the ONLY SDK `TracerProvider(` in production code estate-wide; zero dashboards
      or alerts read status descriptions. P2s (pre-set global provider bypasses silently; 4 surviving
      fidelity mutants; seat-guard alias defeat; overclaimed backfill rationale; `_on_ending`) → the
      flynapse-otel follow-up lane. Downstream green: utils observability, api telemetry+startup, telegram-bot
      telemetry (251) — the bot already runs on the boundary via its path dependency.
- [~] G.111 **Instrumentor URL attributes carry tenant-scoped object keys — the trace pipe, not the door span.**
      **BUILT 2026-09-21 (flynapse-otel `c372977`, review running):** at the export seat only (contrib 0.65b0: only urllib3 takes `url_filter`; requests/httpx `redact_url` misses `X-Amz-*`; server spans come from no instrumentor). `url.full`/`http.url` → scheme + host:port + path SHAPE; `url.path`/`http.target` → shape; query/fragment/userinfo removed; `http.route`, `server.*` kept; SERVER spans included (an api route takes `{email}`). Proved over real local sockets for urllib3/requests/httpx; 11 mutants. **Collateral:** `copilot-mro-obsm/deployment/otel/base.yaml:190-192` health/metrics span filters match `url.path` → now dead (fix pending the reviewer's recommendation — likely `http.route`). Downstream movers: telegram 3 tests, api `test_gateway_http_instrumentation.py:83`.
      Found by the utils reviewer 2026-09-21, CONFIRMED by probe (no AWS): the urllib3 CLIENT span under
      every S3 door exports `http.url` with the bucket (path-style) and the **object key**
      (`…/flynapse-copilot/tenant-SENTINEL/report-SENTINEL.pdf`). `URLLib3Instrumentor` is applied by the
      shared bootstrap with **no `url_filter`**, and `redact_url` does not cover `X-Amz-*` query parameters,
      so a presigned URL's credential would ride the same attribute. The door spans themselves are clean — the
      utils docstring's reason for keeping keys off them ("the trace pipe is read more widely") is not met
      for the pipe as a whole. About 30 raw-client S3 calls in copilot-mro and core show only as these
      urllib3 spans. **Fix seat: flynapse-otel** — a `url_filter` for the HTTP instrumentors (and/or the
      G.110 export scrubber redacting URL attributes by name), after the G.110 review. Tier: P1-class.
- [~] G.112 **TIER-0: the LOG PIPE exports exception text — the span-side boundary has no log-side twin.**
      **P1 FIXED (night): flynapse-otel `1cdf318`** — frames are headers only; the boundary never opens a file a string names. G.116 in the same lane. Unreviewed.
      **REVIEW FIX-FIRST (P1, tier 0):** the BODY rule re-read `linecache` for frame headers found in untrusted body text — a body naming a planted `secret.env` exported its password. Fix in progress: frame headers only, never open a file named by text.
      **BUILT 2026-09-21 (flynapse-otel `001c3b6`, review running):** `LoggerProvider(multi_log_record_processor=WithholdingLogRecordProcessor())`, in place: `exception.message` dropped, `exception.type` kept, `exception.stacktrace` reduced to FRAMES (rebuilt from headers + `linecache`, no rendered text copied); a body's embedded `format_exc()` reduced to frames (~30 utils sites). Undecidable, declared: a body quoting `{e}`; a frameless forged header. Proved through utils' REAL bridge (loguru `exception`, stdlib intercept, `format_exc` body): sentinel on 3/3 before, 0/3 after; 14 mutants. Live views for log tests must sit upstream (`pre_boundary` fixture patches `withhold_log_record`). **Not covered by this seat: stdout sinks** → G.115.
      Confirmed at runtime by the G.110 reviewer 2026-09-21: utils' OTLP sink
      (`utils/observability/log_bridge.py:166-186`) hands `exc_info` to the SDK `LoggingHandler`, and both
      loguru `logger.exception` and stdlib `logging.exception` (via the intercept) exported
      `exception.message` + `exception.stacktrace` carrying a sentinel. G.104 converts call sites one by one
      (copilot-mro ~205 `logger.exception` sites); the SINK has no withholding. **The plan's earlier reason to
      defer it ("utils owns the api processes' log route") is wrong:** flynapse-otel `bootstrap.py` ~:257
      builds the one `LoggerProvider` every route feeds, and SDK 1.44 offers the same seat
      (`multi_log_record_processor`). **Launched 2026-09-21 in the flynapse-otel lane** (with G.110's P2s and
      G.111).
- [x] G.113 **A Postgres role PASSWORD likely rides a span attribute (PLAUSIBLE, source-traced).**
      **CLOSED 2026-09-22 at the r7b merge (review r7b r2, R7B2-28):** the claim — the role password off `db.statement` — is proved with the real psycopg2 instrumentor over real libpq under mutation (PW-M1, M12b, G113 P1–P5 killed); the live dependency C4 (provisioning under `--cap-drop ALL`) stays open under M-SAD-AUTH.
      **UPDATE 2026-09-22 (later): g106 MERGED into `obs-merge` at `75947461` (review r6 verified the merge), so the fix below is LIVE on `obs-merge`; guard gaps `execute_values`/`execute_batch`/`format_map` + the unpinned pragma are being fixed in `obs-merge-r7b` (review r7b P2-3/P2-4).** Earlier text: **CORRECTION (coverage re-derivation 2026-09-22): the fix lives ONLY on branch `obs-merge-g106`.** On copilot-mro `obs-merge` the password is still a `sql.Literal` (`environment.py:327-328`) and no export seat touches `db.statement` — LIVE on the integration branch until g106 merges.**
      **CONFIRMED + FIXED 2026-09-21 (`copilot-mro-obsm-g106 f6b63e53`):** runtime export carried `PASSWORD '<pw>'` in `db.statement`; now `sql.Placeholder` bound client-side (psycopg2 links only `PQexec`); 641-module sweep found no other site; AST guard. **Sibling leak found:** `environment.py _checked` logs `TimeoutExpired` text incl. `--env PGPASSWORD=<admin>` — fix in progress.
      `copilot-mro-obsm/.../data_discovery/environment.py:326-329` runs `CREATE ROLE … LOGIN PASSWORD {}` with
      `sql.Literal(reader_password)`; the psycopg2 instrumentor renders a `Composed` via `as_string` into
      `db.statement`, which dbapi always sets. Fix in copilot-mro: client-side `%s` binding (psycopg2
      interpolates client-side, so `db.statement` stays the template). Queued for copilot-mro after its lane.
      **IMPLEMENTATION NOTE (review r7b P2-3/P2-4/P3-6, `copilot-mro-obsm-r7b 63cd01d7` + `e4d263d2`,
      2026-09-21):** status drift: the merge `75947461` made the fix LIVE on `obs-merge` (review r7b
      P3-7). Guard gaps closed: `execute_values`/`execute_batch` (which mogrify their argslist INTO
      `db.statement`) are read by Rule I and are Rule P sinks; `format_map` is caught by both rules;
      the `# secret-sql-ok:` pragma matches COMMENT tokens only and every pragma is held by equality
      in `PRAGMA_REGISTER` (empty — the revert-plus-three-pragmas mutant is red); the one batch-helper
      site (`seed_corpus_attribution.py`, never bootstrapped) is pinned. And the reader password no
      longer reaches the SERVER at all: the role is created from its client-derived SCRAM verifier,
      so a failed `CREATE ROLE` logged with its statement cannot put it on the container's stderr.
      Box left `[~]` for the controller to close after review.
- [~] G.114 **G.110's export scrubber BLINDED the estate's span-withholding tests (audit 2026-09-21, read-only,
      **PROGRESS (night):** shift-optimizer `71f636a`, flynapse-otel `073b375`, telegram-bot `47c6fbd`, api `2966c5f` DONE (live-span assertions); utils queued in its lane; core/copilot-mro 0 needed.
      every count backed by a planted leak in a scratch copy that stayed green).** An assertion that the
      EXPORTED span carries no description / exception text now passes whatever our code writes. Only trees
      whose test provider runs through the seat are affected: **core 0 and copilot-mro 0** (private plain
      `TracerProvider()`s, planted control goes red); **api 5 functions / 7 cases; utils ~17 functions in 8
      files (`6f7c0dc` caught only 4); telegram-bot 6 (4 already checked live elsewhere; 2 instrumentor
      CLIENT-span tests need a processor); flynapse-otel own tests 4 / 6 cases; shift-optimizer 0 (fixed
      `71f636a`).** **Fix pattern validated:** a `LiveSpans` processor recording in `on_start` sees the live
      span, because `withheld()` builds a NEW `ReadableSpan` and never mutates the one it is given (flynapse-otel
      `caaa03a` `withholding.py:89-119`); clear it per test; add the positive control (description present
      live, gone on export). **Log side (G.112) differs:** the draft scrubs in `on_emit` in place and log
      processors have no `on_start`, so live views must sit upstream (caplog / loguru sink); G.112 will blind
      utils' and telegram's exported-log absence checks and turn two utils POSITIVE assertions red
      (`frames_only` drops the message line). **Also found:** the seat docstring's "nothing else ever reads a
      finished span" is false — `SynchronousMultiSpanProcessor._on_ending` hands every child the raw span.
      Routed: api + utils lanes (after their current batches), flynapse-otel lane (own tests, docstring,
      downstream edit specs), telegram-bot with its swap lane. **Owner question:** one shared `LiveSpans`
      (natural home: flynapse-otel test support) instead of five ~15-line copies.
- [ ] G.115 **TIER-0 CONFIRMED: STDOUT log sinks bypass every OTel seat.** Core review B replayed an escaped
      **BUILT (night): utils-obsm `0211f9b`** — stdout/stderr sinks write exception types + frame headers, never text (object-based, no text parsing). Unreviewed.
      `/pdf/stream` read failure through utils' real `log_bridge.install(json_stdout=True)` + intercept: the stdout
      JSON `exception` field carried the S3 bucket + tenant object key (`log_bridge.py:139-143` writes the full
      `format_exception`, causes included). Every exception escaping to uvicorn in api leaks this way (Starlette
      re-raises after the app handler). utils lane: do it NEXT, at the sink, reusing flynapse-otel `frames_only`.
      loguru / stdlib stdout sinks render the full traceback WITH the exception message to container stdout →
      CloudWatch, untouched by G.112's export processor. If any sink runs loguru with `diagnose=True`, local
      VARIABLE VALUES print too (tier 0). Per M-TRACEBACK (type + frames, never the message) the seat-level fix
      is a sink formatter rendering `failure_fields`-style output. utils lane measures every sink first and
      builds only if the fix stays inside utils; otherwise design → owner. The ~689 copilot-mro call-site
      conversions (M-TRACEBACK) remain the second line.
- [~] G.116 **URLs in LOG bodies/attributes are withheld by neither G.111 (spans only) nor G.112 (exception text
      **BUILT (night): flynapse-otel `49b0763`** — userinfo removed; credential-named query/fragment → `:redacted`; paths kept. Live vector measured: httpx's own INFO request line. Review running.
      only)** — flynapse-otel review 2026-09-21. `logger.info(f"...{presigned_url}")` exports `X-Amz-Signature` /
      `X-Amz-Credential` on the log pipe: the log-side twin of G.111. Partly masked by the collector `redaction`
      processor's secret-shaped regexes. flynapse-otel lane: measure log calls that interpolate URLs estate-wide,
      then a conservative rule at the same seat (strip credential-bearing queries + userinfo in string bodies/attrs).
      **Post-restart 2026-09-22 (flynapse-otel `df503c2`):** `search` added to `SECRET_PARAMETER_MARKERS` (core review r8 P1-1: the dashboard user picker sends a typed name or email as `?search=`); estate check found exactly three free-text `search` Query() parameters (core `/users/`, copilot-mro data_discovery + ad_review); red-before 6 / green-after 194; 3 mutants KILLED via `mutant.sh`; lane 2626 passed.
- [~] G.117 **Entrypoints that never call `setup_logging` keep loguru's DEFAULT sink with `diagnose=True`**
      **PROGRESS 2026-09-22 — utils seat BUILT (`utils-obsm 3e7477e`, M-G117-DEFAULT; review r4 running):** `import utils`
      setdefaults `LOGURU_DIAGNOSE=NO` and swaps an untouched handler 0 for a types + frame-headers sink (stands aside
      when pytest is imported). **Owed:** `ENV LOGURU_DIAGNOSE=NO` in api/Dockerfile (api lane), copilot-mro Dockerfile +
      Dockerfile.lambda (copilot-mro lane), iac `apprunner.tf` api env + `lambda.tf` `s3_pdf_processor` + `image_lambda`
      (iac lane, queued); WDM `parse_all.py` spawn workers `import utils` (copilot-mro); core entrypoints that never
      import utils (core lane). `lambdas/cognito-lambdas/Dockerfile` uses loguru but the repo is OUT of scope (owner).
      **iac DONE 2026-09-21 (`iac 1c8c998`, not pushed):** `LOGURU_DIAGNOSE = "NO"` in the App Runner api env and
      both Lambda envs (`s3_pdf_processor`, `image_lambda`). A belt beside the Dockerfiles: App Runner runs
      `:latest` with auto-deploy off and the ingest Lambda ignores `image_uri`, so either may run an image that
      predates the Dockerfile line; and `image_lambda` (lambdas/cognito-lambdas, owner item C8) has no other
      seat, so C8's runtime exposure closes at the next apply although that Dockerfile stays unfixed. Guard
      `test_loguru_diagnose_off_on_compute.py` classifies every compute resource in every root and module by
      equality (3 REQUIRED; 6 EXEMPT with reasons, the forwarder Lambda's no-loguru and the gateway task's
      third-party images checked) and reads the process env by structure (`tests/_hcl_blocks.py` on
      `_env_syntax`'s scanner, the `$${` trap planted). 246 → 258; 11 mutants red. `terraform fmt -check` not
      run (ban): the new HCL follows hclwrite's rule that a comment line ends an `=` alignment chain; CI proves it.
      **iac review r3 fixes, 2026-09-22, not pushed:** P2-3 `0a31a72` (controller call): the `poc_replica`
      exemption was refuted — the box pulls `flynapse-api-ecr:latest`, published without the Dockerfile line — so
      `poc_ec2_setup.sh`'s `.env` heredoc (read by the poc compose `api` service through `env_file`) now writes
      `LOGURU_DIAGNOSE=NO`, and `poc_replica` is REQUIRED, read through its user data and bounded to that heredoc
      (L9 red; line removed red; moved to an `export` red). P3-1 `37f82c4`: the forwarder check rglobs
      `lambda_src/` as the archive zips it (L8 red). P3-2 `9bb3c3d`: `*.tf.json` and non-local module sources
      are refused (L5, L6 red); an unlisted resource TYPE (L7) stays the stated limit. P3-3 `d2c7aac`
      (controller call): no REQUIRED resource may `ignore_changes` its env block (or `all`), and a REQUIRED
      instance needs `user_data_replace_on_change = true` (L11 red; two POC mutants red). 266 → 275 across the
      batch; each commit green at its own HEAD in a scratch clone with all three validators.
      **iac review r4 fixes, 2026-09-22, not pushed:** P3-B `17a65c1`: the POC guard refuses every write to `.env` but its one heredoc (L9b, L9c, L9h, L9s red; its one declared limit, a write inside a script the user data writes out, pinned at `d1ebeb1`); P3-D `ac5ab23`: a local module source counts only if it resolves inside the repo and outside hidden directories (L6b red), and the docstring no longer claims "the one limit left" (IR4-12); P3-E `6615cb0`: the forwarder check reads the directory its archive's `source_dir` zips (L8s red). **Correction (r4 P3-H):** `9bb3c3d`'s message names one remaining limit (L7); there were two more, bare labels and a `../` source leaving the repo, closed at `d76c439` and `ac5ab23`.
      (frame-local VALUES + messages to stderr → CloudWatch) — utils r3 audit 2026-09-21. Worst: copilot-mro
      `lambda_functions/s3_pdf_processor_lambda.py` (container lambda; `format_exc` bodies too), the WDM
      `parse_all.py` spawn pool (a spawn child prints message + diagnose values), 55 of 56 copilot-mro scripts,
      `scripts/build_referred_by_mapping.py` adding a second diagnose sink; core `grace_backfill.py`,
      `setup/dynamodb/*`, 7 scripts; utils `migrate_weaviate_collection.py`, `llm_batch_submit.py`; uvicorn reload
      parents. Also the interpreter hooks (excepthook/threading/unraisable) — utils P1-3. Options: call
      `setup_logging` at each entrypoint; `LOGURU_DIAGNOSE=NO` in images; a safe utils import-time default (utils
      lane to judge). Per repo after M-TRACEBACK's guard lands.
- [x] G.95 **THE WORST INSTRUMENTATION GAP IN `utils`, AND THE COVERAGE MATRIX DID NOT COVER IT.**
      **CLOSED 2026-09-21 (`utils-obsm 099629f`).** **There is NO funnel** — `get_table()` looks like one but
      only caches a local boto3 `Table` handle and makes no request, so a span there would say nothing.
      **17 doors** get a span via `_traced_dynamodb`; **`_scan_all` deliberately gets none** because it is the
      module's one real funnel and every page it reads already goes through the traced `scan` (a test proves
      N `dynamodb.scan` spans and **no** wrapper span, and a decoy wrapper fails it); and
      `_initialize_connection` gets none because it runs at import, before `bootstrap` starts tracing.
      **Double-counting checked against the REAL dashboard queries, not assumed:** `db.system="dynamodb"` puts
      the span on the DB panel while the urllib3 span stays on the external panel — **no double count.** The
      `rpc.*` shape S3 uses **would** have double-counted. **If botocore instrumentation is ever enabled it
      must REPLACE this span, not sit beside it** — recorded in code.
      **An earlier claim refuted:** "in `utils` nothing escapes the `with`" is **false for DynamoDB** —
      `_traced_dynamodb` re-raises, so the withholding keywords are **load-bearing** here, not defence in
      depth. **Found, reported, not fixed:** `dynamodb = DynamoDB()` at import is worse than briefed —
      `boto3.resource` blocks **~2.0 s on an EC2 metadata probe at every import**, and `import core.services`
      measured 3.5 s. The fix is a lazy client (as `Weaviate.client` already does); deferred because importers
      in three repos are affected.
      **Also closed in the same commit:** the witness clause is now **equality**; `trace.Status(...)` and
      aliased imports are caught; the sweep follows a caught exception **one hop into `_finish_*_span`** —
      **before this, the handler rule covered ZERO real sites in the package**; a bare `except` +
      `format_exc()` was a **real gap here** (the planted case returned nothing) and is now closed; the
      module-mains guard catches module-scope and one-hop destructive calls; the false "cannot produce a false
      positive" sentence is withdrawn; and **behavioural `dry_run` tests** now exist — **the signature guard
      had passed while a body that ignored the flag deleted for real.**
      **Lane: `utils-obsm` has no `.env`, so the neutral-cwd error (G.103) did NOT affect this tree** —
      1515 either way. `find_env_file`'s docstring falsely claimed an upward search; it checks exactly two
      directories, cwd first. The order was kept (a normal convention) and pinned by a test.
      `utils/dynamodb_service.py` has **18 methods and ZERO domain spans — not one observability import, not
      even `failure_fields`.** Every DynamoDB call in the estate is visible only as a urllib3 HTTP span, so
      the trace says `POST https://dynamodb…` and never what was done to which table.
      Re-measured beside it: **`s3_service.py` spans 1 of 23 methods** (R.3 called this "one of ~sixteen" —
      the true method count is 23, so the gap is **worse** than the matrix stated). `weaviate_service.py` is
      genuinely domain-instrumented (34 span sites across 25 methods) and `embedding_service.py`'s single
      span is on `_embed`, **the funnel all three callers pass through**, so it is effectively covered.
      **This sharpens R.3's qualifier from "8 of 16 pass only via the HTTP fallback" into a per-client
      count.** The matrix's row granularity hid a client with nothing at all.
- [x] G.96 **SEQUENCING OWED — `utils-obsm` is RED with 2 failures THAT ARE NOT ITS OWN, by design.**
      The two `xfail(strict=True)` markers in
      `utils-obsm/tests/unit/observability/test_utils_spans_withhold_exception_text.py` **now XPASS**,
      because the `flynapse-otel` lane repaired `tracing.py` mid-session (`_WITHHOLD` at `:44`, applied at
      `:91,141,186,193`) — **and `utils-obsm` consumes it as `path = "../flynapse-otel", develop = true`,
      so the repair took effect instantly.** A strict xpass fails the suite, **which is exactly the signal
      those markers were built to give.**
      **The utils implementer deliberately did NOT delete them**, because the repair is uncommitted in a
      sibling working tree and *"deleting them would commit my tests against another lane's mid-edit tree"*
      — the precise hazard that has already cost this project two bad briefs.
      **Order of operations: flynapse-otel commits FIRST → then the two markers are deleted in `utils-obsm`
      and that tree's remaining 9 production files are committed in the same step.** Until then the red is
      expected and must not be "fixed" by weakening the markers.
### Phase H — out of scope here, recorded
The live batch, publishing, the iac plan gate and the first apply. Blocked on the owner being present, CI
secrets and the AWS deferral.

---

## 4. Decisions


### 4a-bis. Owner rulings taken 2026-09-20 (late session)

> **RECORDED LATE, AND THAT IS THE POINT.** An adversarial reviewer flagged that the `dry_run` flip below
> was described in a commit message as "on the owner's ruling" while **no record of that ruling existed
> anywhere in the plan or in any tree** — so from the repository alone it was undecidable whether a
> plan-gated owner decision had been taken on an implementer's say-so. **The ruling was real; the
> controller failed to write it down.** That is the same defect class this whole phase keeps finding — a
> fact held in one place and not in the place that documents it. **Every ruling below is now recorded at
> the moment it is taken, before the work is dispatched.**

| # | Question | Ruling | Consequence |
|---|---|---|---|
| **M-CASCADE** | Deleting a tenant destroys every document comment it owns (+ a 10th relation transitively), while the API's own 200 body says those rows survive. | **STOP THE CASCADE.** Comments survive a tenant delete, so the existing promise becomes true. | Mechanism is the implementer's to choose and defend — `RESTRICT` turns silent loss into a failed delete; `SET NULL` strips the column RLS binds on; dropping the FK loses integrity. Migration written, **not run**. |
| **M-OTEL-SCOPE** | `flynapse-otel` is an 8th repo outside the seven-tree scope and carries two tier-0-shaped defects. | **FIX IT, DO NOT PUBLISH.** | No version bump, no release. Landed as `flynapse-otel f6bd5c0`. |
| **M-COMMIT** | ~106 production files held uncommitted for owner review; two test files could not even import without them, so the branch was not measurable at its own HEAD. | **COMMIT THEM NOW**, by named path, no pre-review. **Nothing pushed.** | `core 0609ad2` · `api b6471c8` · `iac f85284e` · `utils fffa470` · `dashboard afd6300`. The convention for the remainder of this phase is **production and tests land in ONE commit**. |
| **M-DRYRUN** | `delete_files_by_keyword(..., dry_run: bool = False)` still defaults to deleting — flipping it is a **breaking change to a published package**. | **FLIP IT.** | Landed as `utils-obsm fffa470` after zero callers were re-verified across 20 repos and 8 `scripts/` dirs. **See G.97 — the version number was not bumped with it.** |
| **M-LOGLINES** | Eight loguru `%`-style sites ship a literal `%s` with the argument dropped; four are Postgres save errors that log no error. | **FIX THEM.** | Dispatched to the copilot-mro lane. |
| **M-AWSPROBE** | Four dead metric-filter selectors need non-mutating AWS calls to settle. | **WRITE THE COMMANDS FOR THE OWNER TO RUN.** | Delivered as `iac/scripts/b1b_metric_filter_probe.sh`. |
| **M-PREMERGE-ARM** | The pre-merge `utils` checkout still carries both destructive `__main__` blocks. | **NOT SELECTED — deliberately left.** | `python -m utils.s3_service` remains live in `/home/aditya/Code/utils` (branch `langgraph-merge`) until this branch merges. **The only unfixed item that can destroy data by being run.** |
| **M-COMMENT-PII** | After M-CASCADE, comments keep `author_name`/`author_email` after a tenant delete. Keep them, or blank them at delete time? (2026-09-21) | **KEEP.** The residue sweep `copilot-mro/scripts/delete_unentitled_partition.py --purged-tenant <id> --execute` removes them with the rest of the tenant's rows. | No delete-time UPDATE, so the deleting role does NOT gain UPDATE on `comments` (core's lane advised against widening it). **Caveat recorded:** the sweep is manual and dry-run by default — until someone runs it, the names persist (unreachable by any login). |
| **M-TRACEBACK** | Core writes full tracebacks to logs and its docs allow it; utils and api strip them. One rule estate-wide? (2026-09-21) | **ADOPT THE SAFE HELPER EVERYWHERE.** `utils.observability.failure.failure_fields` (type + frames, never the message) in **core** and **copilot-mro**, as api and utils already do. | Core's docs that allow tracebacks must be corrected. Sized by the exception-in-logs census before dispatch; implementers run when `core-obsm` (under review) and `copilot-mro-obsm` (lane live) free up. A guard lands WITH each conversion, never before it. |
| **M-SATELLITE-SCOPE** | G.100: `shift-optimizer` (0/3 span openers withhold) and `telegram-bot` (1/5) were never swept. Bring them into scope? (2026-09-21) | **YES — FIX, DON'T PUBLISH**, the same terms as M-OTEL-SCOPE. | Commits on each repo's `main` by named path; **no version bump, no publish, no push, no deploy.** Scope: exception-text withholding on spans (G.100) and, per M-TRACEBACK, exception text in logs. |
| **M-SAD-AUTH** | The data_discovery (SAD) disposable Postgres: `postgres:16-alpine` with only `POSTGRES_HOST_AUTH_METHOD` leaves `local all all trust`, and the socket dir is 0o777, so any local user reaches superuser `restore_admin` with no password; passwords also ride docker argv (`ps`-readable) in `environment.py` and `scripts/migrate_tenancy_schema.py`. Outside telemetry — fix now? (2026-09-21) | **YES — FIX BOTH NOW.** | `POSTGRES_INITDB_ARGS=--auth-local=scram-sha-256` + correct the comment; passwords by env NAME only (`--env PGPASSWORD` + `env=`), `POSTGRES_PASSWORD_FILE` if cheap. g106 lane (`environment.py`), copilot-mro lane (`migrate_tenancy_schema.py`). Reviewed with the rest; no docker runs. **Built 2026-09-22 (g106 NEW-3 `404d22be`): `--auth=scram-sha-256` for EVERY pg_hba line, not only `--auth-local`; review r7b P2-1 found the SCRAM test checks membership, not the effective (last) value — fix in `obs-merge-r7b`. The container cannot yet start under `--cap-drop ALL` (owner C4), so every property is proven in code only.** **r7b (`81bd0942`): the pin reads the EFFECTIVE value of each name over every docker env spelling and requires each exactly once; the argv builder refuses a name stated twice (the entrypoint takes the last), bare inherited names in every pflag form (`-eNAME`, `-e=NAME`, `-ite NAME`) and `--env-file`. The Consequence cell's `--auth-local` above is the ruled text; the built and pinned value is `--auth=scram-sha-256` (A71-03).** |
| **M-G117-DEFAULT** | G.117: ~70 entrypoints never call `setup_logging` and keep loguru's default `diagnose=True` sink (local values + messages to stderr). Fix how? (2026-09-22) | **SAFE DEFAULT IN UTILS.** | utils replaces loguru's untouched default sink with a safe one (`diagnose=False`, type + frames) at import; every image sets `LOGURU_DIAGNOSE=NO`. No per-script edits. utils lane. |
| **M-SHARED-CHECK** | The exception-text detector exists in ~6 drifting copies (copilot-mro writing a 7th). Share it? (2026-09-22) | **SHARE VIA FLYNAPSE-OTEL.** | One detector + the `LiveSpans` helper in a flynapse-otel TEST-SUPPORT module; each repo's guard keeps only its own register and imports the detector. `tests/_root.py` stays a byte-for-byte copy with its drift check. flynapse-otel lane builds it; repos adopt after. **Review r7 (2026-09-22, FIX-FIRST 0/1/4/5):** the SCAN may be adopted now (every-argument floor + refusal proof hold; estate re-scan de501a8 → 4b48507 = 0 missing, 3 over-reports as claimed); the RATCHET waits for P1-1 (`_ratchet.py:136-148` adopts a MOVED register's own widened text as its baseline when `moved_from` is omitted — r6 failed closed, r7 fails open; until fixed every guard passes `moved_from` on any register move). Third ratchet-baseline finding in three rounds → write down where a register's baseline is decided BEFORE patching. P2-4 (from telegram r5): a raised class named with a leading `_` is never read (`_module.py:1420`, `name[:1].isupper()`; predates r7; 64 estate raise sites, no known live leak). Lesson-#14 judgement: withdrawing the narrowing was a DESIGN change (sound floor + one add-only table), satisfied. |
| **M-SHARED-NETGUARD** | Test-hygiene audit (2026-09-22): only api has a test network guard. copilot-mro made 620 attempts in `tests/unit` and 332 in `tests/agent_sdk`, and core made 121 in `tests/api`; 10 copilot-mro tests sent real Bedrock requests. Share one guard, or build one per repo? (2026-09-22; **CONTROLLER CALL**, filed here late — api review r8 P3-13 found it named only in flynapse-otel's plan) | **SHARE VIA FLYNAPSE-OTEL, as M-SHARED-CHECK did.** | One guard in `flynapse_otel.testing` (test support never lives in a runtime package): loopback only, including loopback names from `/etc/hosts`; the dev-stack service ports refused on loopback, with a per-phase opening that child processes inherit; a per-session refusal log that children append to; `expect_refusals()`; a `_REAL`-style stub seam; a `sitecustomize` directory for children; per-repo opt-in tables supplied to a pytest plugin. The FAIL half must be proven at every scope. **api r8 adds:** wrap `psycopg2.connect`, blank the `*_PROXY` variables, fail on refusals inside skipped or xfailed tests, and aim the raw-socket self-tests at a locally refused address (~~`240.0.0.1`~~ — **STRUCK 2026-09-22:** it ROUTES via eth0 on this 6.18 kernel, measured independently by api r8 and the netguard r1 review; use `255.255.255.255` / `ff02::1` with `AI_NUMERICHOST`). **Adoption order (netguard r1 review, FIX-FIRST 0/1/6/3):** first PORT api's three fixes into the shared guard (`91781ef` psycopg2/psycopg3, `02c9710` skip/xfail refusals fail, `2d49c3f` `*_PROXY` removed) + 8050 in the port table + the r1 P1-1/P2s; only then adopt; api deletes its copy LAST (adopting earlier regresses api). Until then adoption notes say: serial lanes (xdist loses the session half), parametrized ids listed one by one in `unguarded`. api's `tests/_netguard.py` is the reference and is deleted at adoption. **api r8 batch DONE (2026-09-22, api-obsm `91781ef..fbd394c`):** besides the three fixes above, port these into the shared guard too — `799dee7` (install() wraps a driver imported while lifted), `5a2c162` (spawn audit hook: `-I`/`-E`/`-S`/scrubbed-env Python children refused), `42174b3` (`installed()` = every seat via `unguarded_seats()`; raw self-tests aimed at `255.255.255.255` / numeric hosts), `fdc3a90` (child refusal pinned to the CALL phase), `867c66d` ("uninstalled" names the seat and the `_REAL` stub seam), `fbd394c` (8050; site dir genuinely FIRST on PYTHONPATH, pinned). Measured under `unshare -rn` with a libc connect logger, every lane `-m "not postgres"` + integration collection: **0 connects to :5432** (r8 before: 16), 1 connect in total (a test-owned loopback forwarder). **OWNER STOP (2026-09-22, final):** the owner never asked for this work ("i had just asked for sdd driven that's it") — the netguard is OUT of the project: no port, no landing check, no adoption; committed guard code stays as-is; the remainder (incl. the 10 copilot-mro tests that send real Bedrock requests) is parked for a later, owner-scheduled project. The earlier cap below is superseded. **OWNER CAP (2026-09-22, after api r9, superseded):** this is test safety, not telemetry, and it has run three rounds finding ever-smaller bypasses — so it is CAPPED. The flynapse-otel batch in flight ports api's COPY list + the netguard r1 P1/P2s (choosing blank-not-remove for proxies and an xdist-safe session failure as it ports); every other api r9 bypass (libpq entry points `psycopg2.extensions.connection` / `psycopg2._connect` / `psycopg.pq.PGconn.connect`, `service=` files, `env`/`env -i`/`timeout` launchers, `socket.SocketType` / `super().connect`, dnspython via loopback :53, an ephemeral-range port rule instead of the hand-kept list, `/etc/hosts` trust) goes to Future Improvements, NOT built. No further dedicated netguard review round: the next flynapse-otel review only verifies the P1/P2 fixes + port landed and the FAIL half works (incl. under `-n`), then consumers adopt (copilot-mro first — it is the repo whose tests sent real Bedrock requests). api r10 builds only the non-bypass findings (Rule B probes, the `-n` session failure, the error-text sweeps, stale prose). |
| **M-WEAVIATE-DOOR** | G.28: ~26 Weaviate call sites go through 3 copilot-mro helpers with no span. How to trace? (2026-09-22) | **TRACE THE 3 HELPERS.** | `collection_handle` / `collections_for` / `weaviate_connection` return a TRACED handle so every query is timed; one seat covers all 26. Waits on A3/G.60 (refusal classification). copilot-mro lane. **Impl. note, copilot-mro r9 (2026-09-22, `c27db590`, review r8 P3-3):** the admin flag now rides EVERY handle the door returns — a round trip's handle result (`collections.create(...)`, which `llama_index_initialization` calls through the door) is wrapped with the door's refusals, and any other method of a handle is treated as an acquisition, so `with_consistency_level(...)` comes back wrapped (and, on the gated doors, traced) instead of raw; each of those could otherwise read any partition. Declared, not sealed, and pinned: a private attribute (`_target`) still reaches the wrapped client, as `object.__getattribute__` always could — the door is a contract against accidental data reads, not a boundary against a caller reaching past it on purpose. |
| **M-VERSIONS** | A1 / G.97: which version numbers and which release order? utils is still `0.1.39` (the deleting-default number), flynapse-otel `0.1.1` though 12+ commits ahead. (2026-09-22) | **0.2.0 BOTH, ORDERED.** | utils `0.2.0` + flynapse-otel `0.2.0` (0.x minor = breaking: `dry_run` default flipped, boot refuses a foreign tracer provider). Release order flynapse-otel → utils → core → api + copilot-mro (core/copilot-mro import `dependency_spans`). Bumps land with Phase H; nothing published before. |
| **M-GENAI-TENANT** | A2 / G.17: `tenant.id` rides on every model metric incl. the 2 gen_ai histograms M-CARDINALITY kept it off (arrived with `54a01f39`). (2026-09-22) | **STRIP FROM THE HISTOGRAMS.** | Drop `tenant.id` from `gen_ai.client.token.usage` + `gen_ai.client.operation.duration`; keep it on the cheap counters (per-tenant calls/cost stay visible). Validate `subagent.name` against the agent catalogue (unknown → `other`). Unblocks G.6. copilot-mro lane. |
| **M-WEAVIATE-REFUSAL** | A3 / G.60: a Weaviate tenancy refusal is recorded as `invalid_argument` (not an error). (2026-09-22) | **CONFIRM + SPLIT FAILURES.** | Refusals stay `invalid_argument` (quiet); real provisioning failures raise a utils-private subclass classified as an error, so once M-WEAVIATE-DOOR traces the helpers they show. Unblocks M-WEAVIATE-DOOR. utils (subclass) → copilot-mro (doors). **Controller call (2026-09-22): the premise was false** — utils has no provisioning seat (it never calls `tenants.get`/`create`; utils r4 report), and provisioning failures already surface as Weaviate client errors classified `error` (copilot-mro r6). So the never-raised `WeaviateProvisioningError` is DELETED (utils) and copilot-mro drops its `getattr` fallback + door test; the ruling's effect (refusals quiet, failures errors) holds. |
| **M-RUN-REASON** | A4 / G.58: `data-run-reason` (2 dashboard sites) carries the raw run `reason`, unbounded; any exception with a string `.reason` lands in the DOM verbatim. (2026-09-22) | **CODES ONLY (SHAPE GATE).** | One shared helper: emit the token when it matches `^[a-z0-9_]{1,64}$`, the `unrecognised` sentinel when a reason is present but does not match, nothing when absent — `runErrorAttribute`'s three-state design. Both sites (`RunHistoryPanel.tsx`, `AutomationNotificationRow.tsx`). dashboard lane. |
| **M-NOTE-KINDS** | A5(b) / G.77(b): the backend may invent data-discovery note kinds (`DiscoveryQualityNoteKind \| string`). Close the list? (2026-09-22) | **KEEP KINDS OPEN.** | No api contract change; the FE already survives an unknown kind. **Keep the `lib/chat/pipeline-status.ts` edit** (rejecting it re-opens `statusConfig`). |
| **M-ALARM-DENOMINATOR** | A6 / G.73: the 4 browser alarms treat missing data as OK; a dead filter stays green forever. (2026-09-22) | **KEEP `notBreaching` + ADD A DENOMINATOR.** | One plain counter of all dashboard log records, no alarm on it, so a dead filter shows as flat zero. **Built AFTER the C2 AWS probe** so it is not created with the same dead selector. iac lane (idle until C2). |
| **M-CHART-CELL** | A5(a) / G.77(a): a chart column named `constructor`/`toString` renders `String(fn)` in the chat chart table cell (cosmetic). (2026-09-22) | **FIX THE TABLE CELL ONLY.** | The cell reads only the row's OWN values (own-property lookup); the chart library's dataset is untouched (no null-prototype rows). dashboard lane. |
| **M-SHIFT-RUNERROR** | A7 / G.100: shift-optimizer writes `str(exc)` into `optimizer_runs.error` for unexpected failures; `GET /runs/{id}` + `/jobs/{id}/runs` return it. (2026-09-22) | **GENERIC FOR SURPRISES.** | Known domain errors keep their message; anything else stores `internal error (<Type>)` — the M-RUNERROR shape. `run_executor.py:305`. shift-optimizer lane. |
| **M-TOOL-ERRORS** | A8 / G.105: ~50 copilot tools put the exception MESSAGE into the tool result (→ model provider, replayed each call, stored 30 days in `llm_turn_content`). (2026-09-22) | **TYPE ONLY, WITH NAMED EXCEPTIONS.** | Default = error type only. Message kept ONLY where the model must fix its own input: SQL parse errors, regex errors, `read_docx` search, `run_code`'s own syntax error / stderr. Infrastructure errors (e.g. `run_code` `spawn_error`) → type only. copilot-mro lane. **Controller call (2026-09-22, r7 P1-1 fix `36aa4254`):** Playwright browser-tool errors keep their text in the user's step trace — they are the external MCP server's report about a third-party portal page (not our exception text), and the techpub design pins them; every other failed step shows `[error]` + class only. All 13 SAD `@tool` handlers + the dispatcher projector are seated (`seated_tool_handler`, `ToolRefusal`), with a structural guard over every `tool(...)` registration. **Impl. note, copilot-mro r9 (2026-09-22, review r8):** P2-1 `1d64829c` + `9a290d61` — a re-seed of either debt register is judged by what the detectors FIND: the old detector (the guard at HEAD for a working-tree re-seed, at the commit's parent for a committed one) and the new one are both run over today's tree, and the debt the re-seed admits must be found by the new and not the old; a dead constant, a pin or a docstring explains nothing, and a detector that cannot run fails closed. The one pre-rule re-seed (M-TRACEBACK `ac43ff2c`) was measured against the rule (no finding) and is the pinned exemption, for cost. The plant (docx_write leak restored and re-seeded) is red working, behind a dead constant, and committed. Controller item: the M-TRACEBACK guard's docstring (lines 1888-1889, out of this batch's scope) still names the retired digest. P2-2 `e17c779b` — the SAD tools' plain-dict result builder is a result builder to the detector wherever it is imported (SV3 killed). P2-3 `fc0534d6` — the structural seat rule follows the SDK factory by provenance, counts any arguments, treats a direct tool-class construction as a registration, and FAILS CLOSED on any other use of the factory (SV1b, SV1 killed); the registration floor is now an exact per-module census. P3-1 `80bfa139` — the tool-result detector records every dict literal WHEREVER it is bound (so r8's SV4 — a dict bound before a handler, filled inside it with `out["error"] = str(exc)` and returned after — is read) and lands a container write reached through a chain on its name (`out.setdefault(k, []).append(str(exc))`) in that name; declared with its reason, an `isinstance` narrowing to a class whose name does not end in Error/Exception (`httpx.ReadTimeout`), which no static test can know is an exception. No live site: the sweep still equals DEBT, so no re-seed. |
| **M-JOB-TRACEPARENT** | A9 / G.68: nothing stores the producer's `traceparent`, so every job consumer trace starts fresh. Carrier? (2026-09-22) | **NEW NULLABLE COLUMN.** | `automation_runs.traceparent` (nullable) — core owns the DDL file + store read/write (migration joins Phase H; never run here); api's producer writes it and `carried_traceparent` reads it. core lane first, then api. **Built 2026-09-22:** core `7c506e6` (column + validated write + `OneShotRun.traceparent` + worker boot check) and api `6ae9701` (the consumer passes `run.traceparent` to `consume_span`; `carried_traceparent` and the `__traceparent__` params key are DELETED). Migration = owner C9, before core deploys. |
| **M-EMBED-INTERNAL** | A10 / G.109: the embeddings wrapper span is CLIENT, so the dependencies board counts each call twice (wrapper + the HTTP call inside). (2026-09-22) | **FIX EMBEDDINGS ONLY.** | `utils/embedding_service.py` span → INTERNAL; DynamoDB + Weaviate wrappers stay CLIENT with `db.system` (own rows, no double count; "DB client p95" unchanged). utils lane. |
| **M-FAILURE-HOME** | A11: `failure_fields` lives in utils; telegram-bot ports a copy; shift-optimizer reads the pre-merge utils. (2026-09-22) | **MOVE TO FLYNAPSE-OTEL.** | One copy in flynapse-otel; `utils.observability.failure` stays as a re-export (no caller changes); telegram-bot drops its port; shift-optimizer imports it from flynapse-otel. Rides the M-VERSIONS 0.2.0 release. B4 (stack = headers only?) is decided inside this helper when ruled. flynapse-otel lane, then utils/telegram/shift. **Parity 2026-09-22:** flynapse-otel `0960c16` = utils `1a42390` (`UTILS_PARITY_SHA`); no later utils commit up to `179cc6d` touches the parity files; `ebfcc68`/`47a6c5b` are utils-only seats (stdlib handler order, logger floors). Pin moved back = 7 red. |
| **M-PII-IDS** | A13 / B-F10: core logs email addresses at INFO (`user_service.py:471-474`, `user_endpoints.py:1725,1729`), and possibly a tenant's whole contact JSON on a parse failure. (2026-09-22) | **IDS ONLY.** | Log `user_id` / `tenant_id`, never emails or contact records; the lane re-checks the contact-JSON line; pin with a log-sweep witness. core lane. **Impl. note, core r8 (2026-09-22):** the user-search term leaves both listing lines and core's own `uvicorn.access` line (`aba5b18`, teardown fix `fe41002`); the vocabulary names the caller's record and name fields, and a comment update logs tag / mention COUNTS (`376ae7b`); the operator CRUD refusals now assert the refused key is not echoed (`bc9f5c6`). Withholding `search` in the shared URL rule is ROUTED to the flynapse-otel lane. Record: core `docs/plans/g61-comments-survive-tenant-delete.md` §21. |
| *(A12 — shared `LiveSpans`)* | Already covered by **M-SHARED-CHECK** (the detector and `LiveSpans` go in one flynapse-otel test-support module; `flynapse_otel/testing/live.py` in progress). Not re-asked. | — | — |
| **M-PHOENIX-ON** | A15 / G.3 + G.107: LLM content copies to Phoenix default OFF (`LLM_CONTENT_COPY_SAMPLE_RATE=0.0`); no deployment turns them on. (2026-09-22) | **ON BY DEFAULT** (owner chose against the sheet's recommendation). | Default sample rate → `1.0`. Copies still flow only where content capture is allowed (deployment + tenant policy gates) and only reach Phoenix where the `content-phoenix.yaml` collector overlay runs — every backend pipeline (`backend-{oss,aws,azure,newrelic}.yaml`) drops content copies (`filter/drop_content_copies` + `attributes/strip_content`), so AWS generates-then-drops them until a Phoenix endpoint exists. Update the config comment + spec §8 note; pin the default and the drop in tests. copilot-mro lane. |
| **M-FACT-LIMITS** | A16 / G.71: judge `confidence` outside 0–1 → NULL (not clamped); latency > 24 h dropped as absurd. (2026-09-22) | **CONFIRM BOTH AS BUILT.** | No code change; tick G.71. |
| **M-LAZY-DYNAMODB** | A17 / G.95: `dynamodb = DynamoDB()` at import blocks ~2 s on an AWS metadata probe in every process. (2026-09-22) | **CREATE ON FIRST USE.** | Lazy, like `Weaviate.client`; callers keep the same name; importing no longer stalls. utils lane. |
| **M-LEGACY-DELETE** | A14(a) / R.4: 10 ported legacy families marked `disposition="retire"` (nothing reads them; each duplicates another record) + 2 contrib HTTP body-size families. Switch off or delete? Owner asked "shouldn't we remove the code?" (2026-09-22) | **DELETE THE CODE.** | Delete the call sites + declarations of `llm_tokens_per_request`, `embedding_request_duration` (utils `llm.py`), `memory_get_latency_ms`, `memory_search_latency_ms` (copilot-mro memory), `document_hub_{retry,delete,share}_total`, `document_hub_parser_failure_total`, `document_hub_cleanup_{vectors,objects}` (copilot-mro `document_hub/operations.py`); update the tests that name them; drop `http.server.{request,response}.body.size` with an SDK View in flynapse-otel's MeterProvider. Order: call sites first, declarations after (no undeclared emission window). |
| **M-LEGACY-PANELS** | A14(b): the 17 `port` families are each the ONLY record of something (non-agent LLM traffic, embedding spend/cache, block-save failures, stuck processing, zero-chunk index, cleanup + notification failures, embedding fallback, upload denominator) but nothing reads them. (2026-09-22) | **KEEP + PANELS/ALARMS.** | A runbook line each (`copilot-mro docs/runbooks/observability/`, making the `on-call` label real), Grafana panels for all 17, and alarms for the silent-failure ones (`chat_block_save_failures_total`, `document_hub_processing_total` failed/stuck, `document_hub_cleanup_total` failed, `document_hub_notification_total` failed, `document_hub_query_embedding_fallback_total`, `document_hub_attempt_vector_cleanup_total` failed) — **AWS alarms after the C2 probe**. **Impl. note, copilot-mro r9 (2026-09-22, `8b23b366`, review r8 P2-4):** the any-occurrence rules' first-event branch is now gated PER PROCESS (job, instance): a series counts as new only where its own process delivered in the hour before t-W, or is live now with no target_info in the day before t-W (newly started — instance is host:pid, so every deploy is a new instance and a per-process gate alone would lose its first events). One process's exporter stalled 61 / 70 / 90 minutes / 5 hours no longer fires any branch (the fleet-wide gate did, the control); a newly started process's first event fires across the hold. Declared price, in the rules header: a process stalled for more than a day reads as new on resume. promtool not run here (docker); syntax hand-checked. |
| **M-WEAVIATE-LEFTOVERS** | A18 / G.39: (a) `weaviate.connect` skews the dependency panels; (b) `WeaviateTenancyError` messages embed tenant/operator ids. (2026-09-22) | **YES TO BOTH.** | (a) exclude `weaviate.connect` from the dependency panels (panel edit). (b) constant messages, ids carried as structured fields (cross-repo message contract; copilot-mro `weaviate_tenancy.py:219-230,278-281` + utils). |
| **M-SIGNUP-ORACLE** | A19: anonymous `POST /users` answers "User with email X already exists in this tenant" — an account-existence oracle. (2026-09-22) | **SAME FIXED SENTENCE.** | Both branches answer the domain branch's fixed sentence ("could not create the account"); core `user_service.py:504` + `user_endpoints.py:413-419` precedent; test update. core lane. **Controller call (2026-09-22), same intent:** the core implementer's M-SIGNUP-ORACLE report (`b9a2343`, core g61 §16; not core review r6) found anonymous `POST /users` with a company/domain that resolves no tenant hits RLS and answers 500 (a workspace-existence oracle and a crash) → it returns the same fixed refusal. The anonymous `GET /users/email/{email}` existence door is a recorded trade-off (signup recovery) → owner question B13. |
| **M-STACK-HEADERS** | B4: `failure_fields()["stack"]` quotes source lines via linecache; the export seat already ships frame headers only. (2026-09-22) | **NAMES ONLY (FILE, LINE, FUNCTION).** | One rule everywhere, no file reads at log time; the estate log shape changes. utils now (its `failure.py` / `_exception_text.py`); flynapse-otel's M-FAILURE-HOME copy keeps parity; telegram-bot's port follows when it switches. |
| **M-FACTS-FAILURES** | B6 / G.32: the facts row is written only when a block is saved, so failed turns (500s, timed-out saves, rejected automation blocks) never appear and the Quality/Reliability failure rates omit most failures. (2026-09-22) | **COUNT FAILURES NOW** (owner chose over "label the panels"). | A second write where a turn SETTLES (success or failure), idempotent with the save-time write (one row per turn, upsert by turn key), parity-tested against the save-time writer; the backfill cannot recreate failure rows (no block) — say so on the panels' history. copilot-mro lane. Fix the false "dip in the series" sentence either way. **Impl. note, copilot-mro r9 (2026-09-22, `cb250d9d`, review r8 P1-1):** the settle write now reads its chat's liveness in its own statement, under a share lock that `delete_chat`'s first statement (the chat's soft-delete, now a named constant that must stay first) conflicts with. A turn whose chat was deleted while it ran lands the ANONYMISED shape (deleted-user, no session) — counted, as this ruling requires, and anonymous, as M-FACTS-ANONYMISE requires — rather than nothing; a turn with no chat row lands nothing, as `save_block` refuses it too. Proved red-before on `pg_temp` shadows (both orders give the same row); the two-session lock proofs run on a real `chats` row in the db lane. The stale "a facts row with no block is impossible" docstring family corrected. **Impl. notes, copilot-mro r9 (2026-09-22, review r8 P3s):** (1) `37e84d1c` (P3-2) — a settled turn's failure CATEGORY is now a DECLARED code (`TURN_ERROR_CODES`, the 17 `StructuredError` codes, held EQUAL by a census test to the literals the package spells at every construction site) or the exception's class name; an object's untrusted text `.code` (`SystemExit("…")`, a provider error whose code is the response body's token) is never stored, and the turn span takes `error.type` from the same function so the two stay one category. (2) `a775de28` (P3-4) — the writer's default execute runs in a pooled connection's own transaction, as `save_block` does, so a failed settle logs ONE WARNING by type; until the owner's C12 run every settled turn also logged utils' "Postgres execute failed" ERROR with the statement attached. (3) `1ab8fdaf` (P3-5) — the schema-conformance gate gains `declared_nullable_columns_exist`: a declared NULLABLE column absent from a present base relation is a violation (views exempt), so the two missing settle columns are NAMED by the live report instead of being nobody's — `declared_column_types_match_live` skipped an absent column and the two properties it deferred to see only NOT NULL columns and whole relations. |
| **M-REVOKE-CACHE** | B7 / G.82: a failed permission-cache clear during a revoke returns 200 and serves the old grant until expiry (300–3600 s). (2026-09-22) | **KEEP DEGRADING NOW; PROPER FIX RECORDED.** | No code change now. Future Improvements: the middleware never answers 2xx for an unconfirmed clear (a new return path). |
| **M-FACTS-ANONYMISE** | B5 / G.34: after a chat is deleted its `chat_turn_facts` row keeps `user_id`, `session_id` and cited-document titles, and 9 panels count it. Owner: deleting makes past numbers wrong ("the chat was started"). (2026-09-22) | **ANONYMISE, KEEP COUNTS.** | In the same delete, blank the personal fields (`user_id`, `session_id`, cited titles, any other identifying column) and keep the row, so historic counts stay true; per-user panels show it as a deleted user. The backfill must produce the same anonymised shape for deleted blocks (writer/backfill parity). copilot-mro lane (+ core backfill if it diverges). **Impl. note, core r8 (2026-09-22):** chats deleted BEFORE copilot-mro `d4792d6b` kept their asker; core's `unanswered_questions` now answers `deleted-user` whenever the block is not live (`e9fb7b3`), and the owner's one-off rewrite of those rows is core `scripts/rbac/anonymise_already_deleted_chats.sql` (owner item C15; facts + feedback, idempotent, BYPASSRLS role). `top_cited_documents` is one row per `doc_uid` (`5f8c879`); `unknown` is the catch-all outcome series (`b2d67f2`). OPEN owner question: does "per-user panels show it as a deleted user" extend to `llm_usage` SPEND? Nothing built. **Impl. note, copilot-mro r9 (2026-09-22):** (1) `cb250d9d` (review r8 P1-1) — a turn still in flight when its chat is deleted no longer lands a personal facts row after the anonymisation: the settle write reads the chat's liveness under a lock the delete conflicts with and lands the anonymised shape. (2) `56daa56f` (review r8 P2-5) — feedback filed on a deleted chat's block (a stale tab) is REFUSED by its writer under the same kind of lock, and a refused save propagates nothing onward; feedback on a block with no row yet (a streamed turn not yet saved) is still accepted. (3) **NEW OPEN OWNER QUESTION (P2-5, measured 2026-09-22 with fakes around the real code, nothing built):** the typed feedback comment and its giver are ALSO copied, outside the chat's own relations, into `memory_item_events` (actor user id + the comment in the event metadata — for EVERY feedback type on a block with linked traces), `memory_items` trace payloads (a thumbs-down's comment in the trace's user corrections), `improvement_signals` (user id, the comment excerpt up to 500 characters, the chat id) and, from the signals, the distiller's evidence excerpts on pending tenant facts / findings. `delete_chat` issues exactly four statements (chats, chat blocks, facts, feedback) and reaches none of them. Does "blank the personal fields … any other identifying column" reach those stores? If yes, the delete would blank the event's actor and comment and the signal's user and excerpt by the chat's block ids, and drop the trace corrections on traces linked to those blocks; the distiller's excerpts carry no per-excerpt provenance, so they could be reached only through their evidence signal ids or not at all. Evidence: `~/.claude/scratch/obs-merge/mro-impl-r9/probes/p25_measure.py` and its output in that lane's NOTES.md. |
| **M-INVITE-FRAGMENT** | B10: the invitation secret rides in `/invite?token=…` and `GET /invitations/preview?token=…` → ALB/CloudFront/Amplify access logs + browser history. (2026-09-22) | **MOVE THE TOKEN OUT OF URLS.** | Email link carries `#token=` (never sent to servers); preview becomes `POST /invitations/preview` with the token in the body; the dashboard page reads the fragment and still accepts `?token=` from already-sent emails during the transition (then strips it from the address bar). core (API + email composer) + dashboard (page). **Dashboard half DONE `dashboard-obsm 0f87aec` (not pushed):** fragment read + `?token=` fallback, both stripped via `replaceState`; preview is POST-body only (no GET fallback); `Referrer-Policy: no-referrer` on `/invite` and `/register?invite=`; unit 2594 → 2607, 7 mutants red. Still open: the accept hand-off `/register?invite=<token>` keeps the token in a URL. **Controller call (2026-09-22), same intent:** the Accept button still hands the token on as `/register?invite=<token>` (access logs, `_rsc` fetches, history) → dashboard moves it to `/register?invite=1#token=…` with the middleware keying on the marker. **DONE `49f6231`** (older `?invite=<token>` read + rewritten to the marker); **review r1 fixes `09bacba`** (token held in memory across remounts, per-tab "open the link again" note, Try again on `unreachable`, strip via `router.replace`); **review r2 P3s closed `2a9b0f4`** (13 mutants red, incl. the reviewer's M05/M08/M09/M10/M13/M22/M23/M24/M25). **Declared failure mode:** the `router.replace` strip is a server round trip, so a failed fetch or a deploy between reading `/invite` and clicking Accept reloads without the fragment and shows "Open your invitation link again" — recoverable; §6 Future improvements records the `history.state` fix. |
| **M-PERMISSIONS-ENDPOINT** | B11: the dashboard learns permissions from the response HEADERS of `GET /test-cookie`, a leftover test route (now echo-free, api `0e225bd`). (2026-09-22) | **REPLACE IT NOW** (owner chose over the recommendation to defer). | api adds a real authenticated permissions endpoint whose JSON body carries what the headers carry today (tenant, roles, department permissions, capabilities by department), from the same auth context; the dashboard's `PermissionContext` reads that body instead. **Controller call:** `/test-cookie` stays ONE release, deprecated, with a token-free usage log (dashboards already loaded in browsers still call it; api deploys before Amplify), then is deleted — the same pattern as the invitation GET. api defines the contract first; dashboard adopts. **Dashboard half DONE `dashboard-obsm e3a4610` (not pushed):** `PermissionContext` reads the `GET /auth/permissions` body; no dashboard caller of `/test-cookie` remains (source-scan test). |
| **M-LEGACY-TENANT** | B12 / copilot-mro r6 P3-6: three ported legacy histograms (`llm_request_duration`, `embedding_cost_usd`, `document_hub_processing_duration_seconds`) carry uncapped `tenant_id` (`legacy_families.py:26-28`), against M-CARDINALITY. (2026-09-22) | **DROP THE PER-CUSTOMER SPLIT.** | utils removes `tenant_id` from those three histograms' declared keys. **Controller call:** per-customer embedding COST must stay visible (the owner was told cost stays visible) — utils moves it onto a cheap tenant-keyed counter; copilot-mro repoints the new "Embedding spend per hour by tenant" panel. `agent.turn.duration_seconds` is not asked: it already violates M-CARDINALITY and is stripped by the copilot-mro lane. **Impl. note, copilot-mro r9 (2026-09-22, `ce545211`, review r8 P3-8):** the STATIC half of the check judged a `**labels` splat by the dict literal the name was bound to, so M9 (`labels["tenant_id"] = job.tenant_id` before the histogram call) survived the full `document_hub` + `observability` lanes — the runtime drop stripped the key, the guard did not see it. A splat is now clean only when its name is bound to such a literal AND used nowhere else in the function but as a `**` splat: a subscript store, `update` / `setdefault`, an augmented assignment or a helper handed the dict each counts as carrying the key (six shapes pinned). |
| **M-CAPTURE-TRUNCATE** | B8 / G.7(c): an oversized captured turn (model exchanges, tool calls with inputs + results, retrieval refs, usage) is truncated in place at 256 KB; the S3 spill column, its CHECK and the purge's S3 branch support a spill never built. (2026-09-22; owner first asked whether this is the chat history — it is not, and whether tool calls are included — they are) | **KEEP TRUNCATING; DROP THE UNBUILT SPILL.** | copilot-mro: delete `content_s3_key`, its CHECK and the purge's S3 branch from the registry DDL + code (the truncation flag stays and is pinned). The column drop is a schema change the OWNER runs with the Phase H migration (never run here). One store, one 30-day clock. |
| **M-CLI-TELEMETRY** | B9 / G.4: spec §6.4 turns on the Claude Code CLI's own metrics + logs per call; never built; `claude_code_token_usage_total` / `claude_code_cost_usage_total` panels are dark. The owner asked whether it overlaps our LLM usage stats — PARTLY: the ledger already stores each SDK turn's total tokens + cost (`orchestrator.py:2802-2817`, `sad_runner.py:383-420`). (2026-09-22) | **PER-CALL DETAIL ONLY.** | copilot-mro: in BOTH the orchestrator and the SAD runner, the per-call CLI env turns on the CLI's LOGS only (per-API-call timing, errors, retries), metrics OFF, every content flag OFF (no prompts, no tool details); remove the two duplicate `claude_code_*` panels + catalogue rows. Guard: the env dict by equality in both runners; a collector check that those logs carry no content. **Controller call (2026-09-22, cli review r1 P1-1):** the CLI's free-text `error` on `api_error`/`api_retries_exhausted` carries the provider's raw text (e.g. a Bedrock 403 quoting an assumed-role ARN), which no content flag gates — it is DROPPED at the collector; only a capped category (status code / error type) is kept. The OTLP logs endpoint is pinned in both carriers so no settings file can route the logs past the allow-list. |
| **M-EMAIL-DOOR** | B13: anonymous `GET /users/email/{email}` answers account existence (rate-limited; id + verified flag), a recorded trade-off for signup recovery (`user_endpoints.py:1654-1690`); it undercuts A19. (2026-09-22) | **KEEP; PROPER FIX RECORDED.** | No code change now. §6 Future improvements entry. |
### 4a. Owner rulings taken 2026-09-19

| id | Ruling |
|---|---|
| **M-CAPTURE** | **Restore spec ruling 4: capture is on by default, tenant opt-out.** Their field validator that hard-coerces the opt-in shut is removed; the policy reader honours the opt-out column. The Appendix A contract clause becomes a go-live prerequisite again. |
| **M-TOOLIO** | **Keep the tool-I/O archive on.** Revert their default flip and leave it wired to served Claude turns. It is retired only once content capture is proven live for a tenant. |
| **M-SCOPE** | **Everything except AWS and live probes.** Merge all six repos, fix every defect on both sides, Task R, the Stream L holes (3.3, 3.4, 3.7, ledger write failures, subagent call sites), Phase 7.3–7.6, and the backfill schedule. AWS apply, the iac plan gate, the live probes and publishing are out. |
| **M-REVIEW** | **Opus for everything now — implementation and review — SDD-driven, no stopping for a second chat.** Fable reviews come later, over the same material, at the same rigor; the colleague's merged work is reviewed to the same standard as ours. Each phase still gets a fresh adversarial Opus reviewer; the review packets are built so a Fable pass can consume them later without re-discovery. |

### 4b. Calls made here (owner may overturn)

| id | Call | Reasoning |
|---|---|---|
| **M-FALLBACK** | Dashboard profile failure falls back to the **capability path**, not to an empty dashboard. | A core outage otherwise renders a blank analytics page indistinguishable from "no access". The server still refuses every panel it should, so it is not a privilege widening, and their own acceptance criterion ("unsupported and unauthorized panels fail closed") still holds. |
| **M-GRAFANA** | Keep the `flynapse-postgres` datasource and the two `fn-llm-agents` exact-spend panels. Accept their removal of the two `fn-platform-health` business panels. **Do not** adopt `deleteDatasources`. | Spec §6.6 rules that no USD metric panel renders without its incompleteness companion — deleting `llm_usage`/`llm_model_calls` leaves only the metered view, which understates. Their separation-of-concerns argument is sound for the two business tables and wrong for the ledger-honesty pair. `deleteDatasources` is destructive at every boot and irreversible. |
| **M-FRONTEND** | Take **our** `fn-frontend` board (18 panels) wholesale; graft their "Slowest Pages" panel as a 19th. | Theirs reduces it to 3 panels and would delete the entire phase-9 consumer set, M9.6's dated DARK flips and M9.7's refusal split. |
| **M-LOCK** | api `poetry.lock`: **take ours wholesale**, do not relock. | Their lock moves zero version pins (the regenerate trap did not fire) and its `content-hash` predates our psycopg dev-group addition, so `poetry check --lock` would fail on theirs and passes on ours. Their one real fix — the stale `../../utils-obs` source url — is already present on our side. |
| **M-WARN** | Take the partition warn-mode helper and its `WeaviatePartitionError`-only narrowing; **gate `warn` so it cannot be selected in a deployed environment** (refuse rather than silently downgrade), surface the degraded boot in gateway state and `/health/ready`, and log the error's own remediation rather than the constant. | As shipped it is an undocumented, ungated env var that converts a fail-closed tenancy gate into a warning nobody reads, and the gateway discards the degraded return value entirely. |
| **M-ACCEPT** | **Drop** `deployment/observability-acceptance/**` and `tests/integration/observability_acceptance/**`. | ~4,600 lines pinned to a branch name that does not exist here, a macOS temp root, four fixed ports and a fixed docker network name — the exact isolation failure phase-10 Task 8 removed. The idea belongs in the `dev-stack` skill under the smoke port-prefix contract. |
| **M-PINS** | Reject `grafana/grafana:latest` at all three sites and the `VERSIONS.md` policy softening; keep `13.2.1`. | A floating tag in the repo whose pin regime exists to forbid one, on an unverified root cause. |
| **M-TOKENUSAGE** | Convert `gen_ai.client.token.usage` from a Counter to a **Histogram** in Phase G, updating the two boards in the same change. | Semconv defines it as a histogram. Their Counter makes every `_total` board query correct and every semconv-compliant consumer (New Relic's OTLP gen-AI views, Phoenix) wrong. Portability was a ruled design goal. |
| **M-TURNCARD** | **Refuse the LLM-turn-summaries card on the SERVER, on its own route**, with the same internal-domain check the improvement page's other four routes already apply. Owner ruling, 2026-09-20 (took the recommendation). | Today the card IS inside the page's internal-only branch, but that branch is chosen by `notInternal`, which is derived from **the other four queries' errors** (`improvement/page.tsx:181-184`). So on first paint nothing has been refused yet, the card renders and fetches, and the notice replaces it only once a sibling query returns 403 — by which time real question and answer text is in the browser, and B2.3's `gcTime` holds it for five more minutes. **A screen that hides data it has already downloaded is not a gate.** The card's own route gates on `view_dashboard`, not the internal-domain check, which is why its fetch succeeds while its siblings are refused. Closes B2-R1 and D.9's open clause. |
| **M-SAVEPOINT** | **A failed `chat_turn_facts` write must never lose the user's chat block.** Wrap the facts upsert in a SAVEPOINT inside `save_block`'s existing transaction; on failure release to the savepoint, log once, and let the block commit. Owner ruling, 2026-09-20. | The plan's "same transaction" wording, taken literally, means an analytics projection failure rolls back the user's message. **Precedent is already in the tree and points the same way:** `llm_usage` is deliberately NOT written from `save_block` (AD-3, ruling 5) for exactly this reason. Answers G.5 Q2. The consequence to state in the code: facts rows can be missing after an incident, and the panels read from the writer's landing forward, so a gap is visible rather than silent. |
| **M-AUTHLOGS** | **Pay down the 16 authentication-adjacent R22 sites now**; leave the other 133 recorded. Owner ruling, 2026-09-20. | `middleware/auth.py` (13 sites) renders exceptions whose text can carry claims, tenant ids and Redis keys; `auth/jwks.py` (3) can carry the pool URL. Those are the only two modules on the estate's credential path. The remaining 133 are background jobs and routers, and the armed sweep committed at `api-obsm 66868f8` stops the debt growing meanwhile. Partially answers B-R1; the rest stays recorded with its dated reasons. |
| **M-CARDINALITY** | **Tenant identity goes on a short NAMED list of instruments only — not on `gen_ai.client.token.usage`.** Owner ruling, 2026-09-20 (took the recommendation). | The token metric is a histogram with 14 advisory bucket boundaries (`telemetry.py:1344`), so **every distinct label combination costs 17 stored series** (15 buckets + `_sum` + `_count`). Its label set is eight-wide — provider, model, role, purpose, profile, cost_source, graph_node, error.type (`_model_attributes`, `:1784-1798`) — giving roughly 900–2,400 combinations for a busy tenant, i.e. **15,000–41,000 series before tenant identity is added at all.** The cheap counters (`agent.turn.calls`, `agent.model.calls`, `agent.model.cost_usd`, `agent.ledger.write_failures`) are closed-vocabulary and cost ~6–12 series per tenant; those carry it. **R.4 also found the premise behind this item was false: there is no attribute allow-list anywhere.** `flynapse_otel/registry.py:27` and `base.yaml:76` are both ten-key DENY-lists, and `tenant.id` is on no list in either direction. The named list must therefore be created, not amended. |
| **M-LEGACY** | **Port every legacy `MetricsService` family onto the modern registry.** Owner instruction, 2026-09-20 — *"fix all legacy metrics too, port to new"*. | R.4 found **27 legacy families emitted and consumed by nothing** — `llm_*` ×4, `embedding_*` ×6, `memory_*_latency_ms` ×2, `chat_block_save_failures_total`, and 14 × `document_hub_*` — and `get_metrics_service()` (`utils-obsm/utils/observability/metrics.py:144`) has **no off switch**, so they cost cardinality and ingest forever. Three are unbounded: `chat_block_save_failures_total` reaches ~7,200 per tenant because `error_kind` × `field` are free strings, and the 14 `document_hub_*` helpers forward arbitrary `**attributes`. Porting them onto the registry is what makes them bounded, because the registry lints attributes and the legacy shim does not. **Where a family has no consumer and no plausible one, the pass proposes retirement in the same breath rather than deciding it alone** — porting a metric nothing reads buys only a cheaper way to store something nobody looks at. **One mechanism must be settled by this port, because the two halves currently degrade in opposite directions:** `registry._lint_attributes` **raises** and `RuntimeTelemetry._safe_add` swallows it, so a forbidden key makes the **whole series vanish silently**; the legacy shim drops the key and warns once. Same mistake, opposite outcomes. |
| **M-RUNERROR** | **Keep the failure reason visible to the automation's owner, but sanitise it** — a category plus a safe message, never the raw exception text. Owner ruling, 2026-09-20. | ~20 sites in `api-obsm/flynapse_api/automations/` (`executor.py`, `loop.py`, `one_shot.py`) write caught-exception text into `automation_runs.error`, and `core` serves that column to authenticated tenant callers as `AutomationRun.error` (`core/resources/automations/models/schemas.py:280`) from `GET /automations/{automation_id}/runs`. **A response-body disclosure with a second hop through the database** — which is why neither sweep caught it: the api guard sees a database write, and the core guard sees a column read. The column is also the ONLY way an automation's owner learns why their run produced nothing, so deleting the channel would remove a real feature; the ruling keeps it and curates what goes in. |
| **M-DEADROUTER** | **Delete `api-obsm/flynapse_api/routers/cache_management.py`.** Owner ruling, 2026-09-20. | `main.py` imports it nowhere — a workspace-wide search finds it referenced only by a stale comment in `middleware/auth.py:1314` and by the log sweep's own debt list. Deleting it retires **6 recorded R22 log sites and 6 response-disclosure sites in one move**. The disclosure fixes already made to it become moot and are dropped with the file rather than committed. |
| **M-EVALSGATE** | **The evals project is gated on G.13 (residency) alone.** Owner ruling, 2026-09-20. | Not on G.5's writer, and not on this merge's full close-out. Once the provider allowlist is enforced and mutation-proved, the project starts and builds everything else it needs itself. The STATUS CORRECTION block now at `agent-evaluation-completion.md` §2.2 is therefore the single precondition, and it must be struck by whoever closes G.13 — not by the evals project itself. |
| **R7B-EXIT** | **A refused AD roster exits with its own status, 3.** Default taken in r7b; the reviewer (r7b r2) recommends ratifying. **RATIFIED by the owner 2026-09-22** (accepted the controller's defaults en bloc). | The refusal must be non-zero so an unattended schedule sees "verdicts committed, nobody told". 1 was also every crash and every `SystemExit(<message>)` in the same script, and 2 is argparse's usage error, so the status is distinct (built, `copilot-mro-obsm-r7b 7a2e5648`). |
| **R7B-CLOUD** | **Unset `EVAL_JUDGE_DEPLOYMENT_CLOUD` means `aws`.** Default taken in r7b; the reviewer recommends ratifying. **RATIFIED by the owner 2026-09-22** (accepted the controller's defaults en bloc). | Every deployment is on AWS; refusing when it is unset would stop today's bedrock judge runs; `azure` is admitted only by an explicit declaration, and the narrowing variable cannot cross clouds (measured). The endpoint half is honest only with R7B2-12's host shape (built, `d91ff4a1`). |
| **R7B-SCRAM** | **The SAD reader role is created from its SCRAM verifier, not by suppressing statement logging.** Default taken in r7b; the reviewer recommends ratifying. **RATIFIED by the owner 2026-09-22** (accepted the controller's defaults en bloc). | Measured: the password never reaches the server; the verifier logs the reader in over real libpq and refuses a wrong password and a neighbour's verifier; suppression could not cover a `log_statement` set by the dump's own superuser DDL. |
| **R7B-G113** | **G.113 is closed `[x]` at the r7b merge; C4 stays on M-SAD-AUTH.** The reviewer's recommendation. **RATIFIED by the owner 2026-09-22** (accepted the controller's defaults en bloc). | What G.113 claims — the role password off `db.statement` — is proved without docker, by the real instrumentor over real libpq plus mutation. The remaining live dependency (provisioning cannot start under `--cap-drop ALL`) is M-SAD-AUTH's. |

### 4b-corrections (from the Phase 0 reviews, 2026-09-19)

- **M-SCOPE** no longer includes "and the backfill schedule" — the owner dropped the backfill the same day
  (see G.9). Strike the clause; an executor reading §4a would otherwise re-add it.
- **M-GRAFANA** cited spec §6.6 for the pairing rule. Wrong section: §6.6 is the *deferred ledger-completeness*
  note. The rules that actually justify keeping the exact-spend panels are **§7.1** (the money rule: every USD
  tile carries its incompleteness companion) and **§6.3** (`agent.model.cost_usd` always paired with
  `agent.model.unpriced_calls`). The ruling stands; the citation was wrong.
- **M-TOKENUSAGE** moves from Phase G into Phase D/E — the same change as the emitter merge — because
  whichever board base is chosen in Phase E is wrong until it lands. Its stated rationale was also inverted:
  our boards query the histogram spelling and have since phase 6; their branch rewrote our boards to match
  their Counter. Scope additionally gains `iac/dashboards/llm-agents.json.tftpl`, which is a repo file, not an
  AWS apply, and is broken in one direction by the Counter.
- **M-TOOLIO** cannot be implemented in `config.py`. Their branch removed the call site, not just the default —
  `orchestrator.py` passes `archive=None` and says so in a comment, and that file **auto-merges silently**.
  Restoring a default for a feature with no caller restores nothing.

### 4d-resolved. Rulings taken 2026-09-19 after Phase 0

- **M-TOOLIO-2 → capture becomes the single store.** Their retirement of the tool-I/O archive is accepted. One
  write site, one retention clock, one redaction version. This **supersedes M-TOOLIO**, and it composes
  correctly with M-CAPTURE: capture on by default means tool I/O is retained again, which is what M-TOOLIO was
  protecting. `dump_debug` and the debug-rag workflow repoint to `llm_turn_content`; that repointing is now a
  Phase D deliverable, not a follow-up, because between the merge and the repoint those workflows are blind.
- **M-EVALS → salvage.** Keep `contracts.py`, the runner's failure-isolation skeleton and the collector
  OpenInference alias fragment. Rebuild evaluator identity to carry profile, registry revision, judge provider
  and model, and build `eval_results` (7.3) before any further judge work. Rewrite `citation_coverage` against
  the structured citation offsets rather than a bracket regex. The rest does not merge.
- **M-RESIDENCY → provider allowlist, in-account only** (applying spec §6.5 and ruling 11, not a new decision).
  No eval run touches real traces until it is enforced.

### 4e. P0 register from Phase 0 — **ANSWERED 2026-09-20** (dispositions below the table)

| id | Finding | Why it is P0 |
|---|---|---|
| **P0-COLLECTOR** | `base.yaml` instantiates the file-storage extension unconditionally on all four profiles, so the collector dies at startup with `mkdir /tmp: permission denied` on any runtime that does not hand it a writable `/tmp` — **proved by running the pinned image**. `otelcol validate` returns rc=0 on exactly that config because it never builds extensions, and `validate.sh` runs only `validate`. The four compose files were patched with tmpfs; the **AWS demo box provisions the collector from `iac/demo_ec2_setup.sh`**, outside this repo and outside the test that checks compose files. | Green CI, green validate, and an observability stack that observes nothing — the one outage nobody is watching for, because the thing that would report it is the thing that died. Fix is ~3 lines; the verification gap needs a real container start added to `validate.sh`. |
| **P0-499** | Their `events_endpoints.py` predates our client-abort work; ours handles `ClientDisconnect` → 499 + one INFO line, theirs has none, and their edits sit inside the same `try` block. | A "take theirs" resolution silently restores ERROR-with-traceback 500s for every abandoned browser POST. |
| **P0-ABORT** | Our abort test fails on merge for **two** independent reasons, not one: the `None`-returning sink, *and* the 202 body gaining `duplicates`. | Fixing the sink alone leaves it red and looks like a flaky merge. |
| **P0-PARTITION** | A skip flag was added to the Weaviate tenant-partition boot check, inside an observability phase, outside their own frozen manifest — replacing a docstring that read "a boot that logged either and served anyway would be the warning nobody reads". | It converts a tenant-isolation gate into a warning, ungated by environment and undocumented in every `.env`, compose and iac file. M-WARN covers the fix. |
| **P0-GUARD** | An existing guard — written verbatim to catch a call site reverting to `type(exc).__name__` — **fails on merge**, because they did exactly that at all three call sites and left the helper as dead code. Verified live: it passes on our tree today. | They shipped over a live guard without running it. It is also the cleanest proof that their sweep was hand-rolled rather than routed through `failure_fields`. |
| **P0-INERT** | 35 inert tests, including three that now *assert* a defect (requiring `grafana:latest`, requiring the destructive `deleteDatasources` entry, requiring exactly three frontend panels). | Restoring correct behaviour now reads as breaking a test, which is how a defect becomes permanent. |

**Dispositions, settled 2026-09-20 — §4e is ANSWERED; it no longer gates the start of the merge.** Each P0 is
a finding with a named owner in a phase, not an open question:

| id | Where it is fixed |
|---|---|
| P0-COLLECTOR | E.2/E.3 (config + the bind-mount doc) and E.9 (a real container start added to `validate.sh`, since `validate` never builds extensions). |
| P0-499 | B1 — core keeps **ours** for the `ClientDisconnect` → 499 path; their edits are grafted inside it, never over it. |
| P0-ABORT | B1.1 — both causes: the `None`-returning `_Sink` double **and** the 202 body gaining `duplicates`. |
| P0-PARTITION | M-WARN, applied in C2.3/C2.4 — gate `warn` so it cannot be selected in a deployed environment. |
| P0-GUARD | D.8 — route all three call sites through `failure_fields`; the existing guard then passes rather than being weakened. |
| P0-INERT | D.7 and E.1/E.5/E.6 — M-PINS kills the `grafana:latest` assertion, M-GRAFANA kills the `deleteDatasources` assertion, M-FRONTEND kills the three-panel assertion. Every remaining inert test is mutation-checked before it earns tier 0 (§2.3a). |

### 4d. REOPENED — **CLOSED 2026-09-19**, superseded by §4d-resolved above; kept for the reasoning

| id | Decision | Why it is now open |
|---|---|---|
| **M-TOOLIO-2** | With M-CAPTURE (capture on by default) **and** M-TOOLIO (archive stays on), the same tool inputs and outputs are persisted **twice** — into `llm_turn_content` under a 30-day `expires_at`, RLS and a redaction version, and into the agent-state tool-I/O archive under different retention and different redaction. That defeats the 30-day purge (purging one leaves the other) and contradicts spec §6.1's one-write-site rule. The two rulings were taken separately and interact. | Options: (a) keep both, accept two copies and extend the purge to cover the archive; (b) keep the archive and leave capture opt-in after all; (c) accept their retirement of the archive and let capture be the single store. |
| **M-EVALS** | The Phoenix suite reviewed as a **research prototype, not a workbench**: scores carry no profile, registry revision, judge model or run id (so ruling 12 is unimplemented and already-written annotations are permanently ambiguous); the entire Phoenix/evals integration boundary is mocked, so the first live run is the first test; and `citation_coverage` — the one deterministic metric — matches bracketed torque values and years while missing this product's actual citations, which are stripped from the displayed answer and carried as structured offsets. | Options: (a) take `contracts.py`, the runner skeleton and the collector alias fragment, rebuild identity and the results store as Phase 7.3; (b) take it whole and fix forward; (c) leave it on the branch for now. |
| **M-RESIDENCY** | The judge receives the user's question, the model's answer and retrieved manual text, and the provider is a free-form CLI string with no allowlist — the documented default is OpenAI. Spec §6.5 and ruling 11 say client production content never leaves the client's own account and never reaches a SaaS in the data path. | This is a contract question, not a preference. Needs a ruling before any eval run touches real traces. |

### 4c. Still owed by the owner (not blocking this plan)

The R22 backlog — sink-level frames-only estate-wide (B-R1), the App Runner stop window (D-R1), the CI token
(E-R1/E-R2), whether `error_code` joins the pipeline result (F-R2) — plus the AWS deferral, publishing CI
secrets, and the Appendix A contract clause, which M-CAPTURE makes a go-live prerequisite again.

---

## 5. Findings register — Phase 0, closed 2026-09-19

Six adversarial Opus lanes over their branch and over this plan. Ranks are the reviewers' final ranks after
adjudication (several first-pass claims were refuted or re-ranked; those are marked). **Disposition** says where
the fix lands. Nothing here is merged — all of it is still on `origin/obs-telemetry-merge`.

### 5.1 Ship-stoppers — see §4e for the full statement of each

`P0-COLLECTOR` · `P0-499` · `P0-ABORT` · `P0-PARTITION` · `P0-GUARD` · `P0-INERT`.

### 5.2 copilot-mro — agent/LLM telemetry (RV2)

| rank | finding | disposition |
|---|---|---|
| P0 | On the default `claude` runtime the model-usage sink sees only the 4–5 auxiliary lifecycle calls — the SDK loop bills itself. Cost, token and cache-hit panels and the `$50/day` tenant alert are built on ~1 % of real spend, undisclosed. The root span already carries the true combined figure. | Phase D: emit turn-level cost/tokens from the same mapping that has the combined figures, or re-word all four panels and the alert. Do not ship a $/tenant alert on a 1 % sample. |
| P0 | `from_current_provider` is the only production construction path and has **zero test coverage**; a raise is cached as `None` for the process lifetime, every agent signal goes dark, and the suite stays green. | Phase D: single construction path with an injectable registry seam; log at ERROR; startup assertion. |
| P1 | Suppressing the legacy `agent_sdk.run_query` root span deletes ~25 `sdk.*` attributes and the `sdk.synthesis_judged` events with no successor — while the repo's own debug-rag skill still tells operators to read that span. The predicate is effectively always-true. | Phase D (D.12): port the trailer attributes and events onto `invoke_agent`, gate suppression on a configured provider, re-bank the identity test. |
| P1 | A cancelled turn is never counted, so the failure-ratio alert's volume guard goes to no-data during a total outage; a crashed turn keeps span status UNSET, so semconv error views report 0 %. | Phase D. |
| P1 | `agent.turn.duration_seconds` mixes backend-measured and wall-clock durations in one histogram, with no `boundaries=` on any histogram. | Phase D. |
| P1 | Every pre-execution tool failure records `attempts=0`, so the panel built for tool failures is blind to denials, validation errors and aborts. | Phase D or a one-line board edit. |
| P2 | `gen_ai.client.operation.duration` is emitted with the full 9-key attribute set and consumed by nothing (~1,800 series/tenant). `deployment.environment.name` never set. `error.type` carries three different vocabularies. | Phase G. |

### 5.3 copilot-mro — content capture (RV1)

| rank | finding | disposition |
|---|---|---|
| P0 | Capture is `await`ed inline with **no timeout**, before the SSE `final` — a slow Postgres withholds an answer already generated. The block save, by contrast, is a shielded task with a bounded wait. | Phase D (D.6). |
| P1 | The snapshot is built, traversed and redacted **before** the tenant policy is read, so an opted-out tenant pays 100 % of the cost and has 100 % of their content materialised. Under the opt-out flip this is the item that decides whether the opt-out is real. | Phase D (D.5) — must land **before** the default flips. |
| P1 | Per-record rather than per-turn budget: ~81 records × 256 KB ≈ 20 MB retained per turn, doubled by the redaction copy. Under opt-out that applies to 100 % of traffic. | Phase D: one turn-wide budget. |
| P1 | Phone numbers are not redacted; Appendix A promises in writing that they are. Verified: `+91 98765 43210` and `(555) 123-4567` both survive. | **P0 under opt-out.** Phase D. |
| P1 | Truncation runs before redaction; the 128-char tail scan has no alternative for email, JWT or a bare AWS key id — all three verified to survive a split at the 32,000-char boundary. | Phase D. |
| P1 | Errored turns are never captured, so a turn that books a ledger row has no content row — the diagnostic case the feature exists for. Spec §6.5 says write at the ledger write site. | Phase D. |
| P2 | `sha256` / `content_bytes` do not describe the stored bytes. `_read_scope_clause` fails open when all scope args are omitted. `content_s3_key` always `None`, so oversize snapshots are dropped, not spilled. Retention is expressed, not enforced — the purge is manual, per-tenant and scheduled nowhere. | Phase D / Phase G (G.7). |

### 5.4 copilot-mro — non-agent spans and the log sweep (RV4)

| rank | finding | disposition |
|---|---|---|
| P0 | 61 production files touched outside their own frozen manifest, including the boot-check skip flag and two `config.py` default flips the manifest excluded. | §4e `P0-PARTITION`; the rest audited file by file in Phase D. |
| P1 | The sweep hand-rolled `error_type=` and threw the frames away — `failure_fields` is used in **zero** new places — at sites where the same string is still returned to the caller or handed to the model. Full regression list in the lane record. | Phase D (D.11): redo the sweep through `failure_fields`. |
| P1 | Memory group wired to the legacy tracing shim (three documented-as-ignored args); `memory.index.delete` reports `success` on a path that deleted nothing; `get_by_ids` derives its outcome from its **input**. | Phase D. |
| P1 | All eight parser entrypoints lose `distribution=` (no `service.version`) and collapse onto one service name, so logs can no longer say which parser ran. Live merge conflict — resolve **ours**. | Phase D (D.1). |
| P2 | Outcome vocabulary is not self-consistent: four span keys, a fifth in logs with an underscore, and `started` emitted as an outcome value. | Phase F (F.4) transcription, Phase D ruling. |

### 5.5 core and dashboard (RV5)

| rank | finding | disposition |
|---|---|---|
| P0 | Their `events_endpoints.py` predates our 499 client-abort work and edits the same `try` block. | §4e `P0-499`. |
| P0 | Our abort test fails on merge for **two** independent reasons — the `None` sink *and* the 202 body gaining `duplicates`. | §4e `P0-ABORT`. |
| P1 | `dashboard_profiles` has **no writer anywhere in the estate** — no endpoint, no seed, no migration — so the feature ships inert while the frontend capability gate it replaces is deleted. | Phase B: ship a write path or do not ship the profile read. |
| P1 | The UUID mint is wider than first thought: chat send breaks on a non-secure origin (before the request is issued); the document viewer hits an error boundary. The *upload* path is safe. | Phase B2 (B2.1), using the idiom already in `ChatInput.tsx`. |
| P1 | `canViewPanel` / `panelsForTab` / `visibleTabs` become dead code with a full test suite still covering them. | Phase B2, with M-FALLBACK. |
| P2 | Profile endpoint missing the admin gate; missing-row widens to all panels while a corrupt row collapses to none; the feature-gate rule now lives in two files; `schema_version` is inert and duplicated across two repos. | Phase B1. |

### 5.6 utils and api (RV5)

| rank | finding | disposition |
|---|---|---|
| P0 | api imports three symbols that exist only on their copilot-mro branch. | §2.2 ordering; gate on `import flynapse_api.main`. |
| P1 | The loguru fix is real and well-tested — keep it. Combine with our R22 policy. | Phase C2. |
| P1 | The boot-check guard relaxation is **gratuitous**: nothing in the diff put `assert_rls_enforced` in a try, and the relaxed form passes exactly the shape they introduced. | Phase C2: revert to the strict rule. |
| P1 | A quiet S3 cache miss is marked span ERROR; its only caller treats misses as normal flow. Both new spans omit `server.address`, so S3 is excluded from 3 of 4 dependency panels and Weaviate collapses to one series. | Phase C1 (C1.3), Phase G (G.10). |
| P1 | api's lock moves **zero** version pins and its content-hash predates our psycopg addition — discard theirs. | Phase C2, M-LOCK. |
| P2 | Two fabricated exceptions built only to read a type name; `grpc_secure` still hard-coded; `WEAVIATE_GRPC_PORT` documented only in utils. | Phase C1. |

### 5.7 copilot-mro deployment (RV5)

Verdict: **REJECT in current state** — recoverable, but it must not merge as-is.

| rank | finding | disposition |
|---|---|---|
| P0 | The collector crash-loop, and `validate.sh` structurally cannot see it. | §4e `P0-COLLECTOR`. |
| P1 | The durability feature does not deliver durability: all four env examples pin the queue to `/tmp`, and a test **forbids** adding the persistent mount that would fix it. | Phase E: reword the "outage budget" claim, allow the mount, document the production requirement. |
| P1 | Taking their frontend board loses 15 of 18 panels, the dated DARK flips and the refusal split. Their `deleteDatasources` is destructive at every provisioning pass and would break 13 panel references on the merged tree. | Phase E, M-GRAFANA / M-FRONTEND. |
| P1 | Their dashboard suite hard-asserts exactly six boards, so our two phase-8 satellite boards are structurally rejected and the "obvious" fix is to delete them. | Phase E. |
| P1 | Their alert guard replaces a generic pattern with a 4-name allowlist and deletes two checks — **not** strictly better, contrary to the first pass. But ours fails on their descriptions (8 offenders), so both need work. | Phase E (E.5). |
| P1 | Splitting Phoenix into overlay files removed it from the port-binding and image-pin guards — and Phoenix holds raw prompt and completion bodies. | Phase E. |
| P2 | Four `grafana:latest` sites (one of them outside every pin test) plus a self-contradicting policy file. The acceptance harness is 4,771 lines pinned to a branch that does not exist here, a macOS temp root and four fixed ports, and is a second undeclared Grafana with auth disabled. | M-PINS, M-ACCEPT. |
| — | **Verified clean:** all four profiles × {backend, +durability} pass real `otelcol validate`; durability fragments correctly omit `service:`; all six dashboards valid JSON with no duplicate ids; `promtool check rules` clean; no new plaintext credential; the `content-phoenix.yaml` tenant-grouping rework is a genuine correctness fix. | take |

### 5.8 Phoenix evals (RV3) — REJECT as a workbench, salvage per M-EVALS

Keep `contracts.py`, the runner's failure-isolation skeleton, the collector alias fragment. Rebuild identity
(profile + registry revision + judge provider + model + prompt hash) and `eval_results` before further judge
work. Rewrite `citation_coverage` against structured citation offsets. Enforce the provider allowlist first.
7.3 and 7.4 confirmed absent. Their `"dry_run"` mode still pays for every judge call.

### 5.9 Local stack defects found while fixing a dead stack, 2026-09-20 (our mainline, not the branch)

Found outside the branch review: the local observability stack was down and nobody knew. Both are our-side
defects and in scope under M-SCOPE.

| rank | id | Finding |
|---|---|---|
| P1 | **L-GRAFANA-UID** | Grafana crash-looped 26 times on `Datasource provisioning error: data source not found`: the persisted `grafana_data/grafana.db` held `Tempo` with an auto-generated uid while `datasources.yml` pins `uid: tempo`. Provisioning **aborts at the first failing datasource**, so `Flynapse Postgres` was never created and every exact-spend panel (§7.1 money rule) had been silently absent. Grafana exits **0** on this failure, so `restart: unless-stopped` loops it forever and `docker ps` shows a plausible "Up 9 seconds". |
| P1 | **L-COMPOSE-ENV** | `deployment/docker-compose.yml` requires `PHOENIX_SECRET`, `PHOENIX_ADMIN_PASSWORD` and `GRAFANA_ADMIN_PASSWORD` with `:?`, but there is no `.env` or `.env.sample` in `deployment/` and `copilot-mro/.env.sample` names none of the three. `docker compose up` fails at interpolation before starting anything, for every service, including ones that do not use those variables. |

A third, environmental, not a defect: after a Docker Desktop / WSL restart, containers created in an earlier
session hold stale `/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/<hash>` handles and `docker start`
fails them with **exit 127** and `no such file or directory` on a single-file bind mount. `docker compose up -d
--force-recreate <svc>` re-binds and fixes it. Same family as the Postgres stale-bind-mount restart trap.

---

## 6. Future improvements

*(Filled as items are deliberately deferred, each with what is missing, why it was deferred, and what the
complete solution would look like.)*

**An invitation token can be lost to a reload the invitee did not ask for (M-INVITE-FRAGMENT, dashboard review r2
P3-1, 2026-09-22).** Missing: the token is held only in memory once stripped from the address. Two paths reload
without it and show "Open your invitation link again": the strip's `router.replace` is a server round trip on the
dynamic layout, and a failed or non-flight fetch falls back to a full load of the stripped URL; and an Accept click
across a deploy (build-id skew) is sent to a full load of `/register?invite=1`, the fetch's own URL, which never has a
fragment. Deferred: both are recoverable (reopen the email link), the copy is right, and the alternative puts the
token back somewhere a server or history could see it. Complete solution: carry the token in the entry's
`history.state` (never sent to a server; survives reload and Back), re-read on mount and cleared on accept — with a
test that Next's `HistoryUpdater`, which rewrites `history.state` on every router state, preserves it.

**A failed permission-cache clear during a revoke still answers 2xx (G.82 / M-REVOKE-CACHE, 2026-09-22).**
Missing: when Redis fails while a role or grant is revoked, the API returns 200 and keeps serving the old grant
until the cache entry expires (300–3600 s); only an ERROR log records it. Deferred by owner ruling: the expiry
bounds the window and raising would 500 a write that already committed. Complete solution: the revoke path
returns a typed "committed, cache not confirmed" outcome and the middleware refuses a 2xx for it (a retryable
503 naming the state, or a synchronous invalidate-with-retry before responding), plus a metric on unconfirmed
clears so the window is visible.

**Anyone can ask whether an email has an account (B13 / M-EMAIL-DOOR, 2026-09-22).**
Missing: anonymous `GET /users/email/{email}` answers existence (200 vs 404), rate-limited per source, so an
attacker can still enumerate accounts slowly even though signup no longer says "already exists" (A19). Deferred by
owner ruling: the dashboard's signup recovery (the `UsernameExistsException` path and pre-activation resolution)
depends on it. Complete solution: recovery asks only after the person proves they own the address (Cognito's
confirmation code, or a one-time link to that address), and the anonymous door is deleted from core, the api
auth skip list and the rate limiter.

**`/test-cookie` is still mounted for one release (B11 / M-PERMISSIONS-ENDPOINT, 2026-09-22).**
Missing: the route stays, deprecated in OpenAPI and logging a constant line with no credential on each use, so
dashboards already open in browsers keep hydrating permissions while api deploys ahead of Amplify. Complete solution:
once the permissions-endpoint dashboard has been live for a release and the usage line reads zero, delete the route,
its `CREDENTIAL_HEADERS` and its tests (api `docs/plans/test-cookie-credential-echo.md` carries the same entry).

**api's JWKS module fetches from Cognito at import (api lane, 2026-09-22).**
Missing: `flynapse_api/auth/jwks.py` calls `init_jwks()` at import, so every process that imports the auth stack —
including every test session until api `73f2aa3` blanked the pool id in `tests/conftest.py` — made a live Cognito
request. Deferred because changing it alters production boot. Complete solution: fetch lazily on first verification
(with the existing cache), so import has no network side effect.

**Child processes bypass the routed exception hooks (utils r5 P3-3, 2026-09-22).**
Missing: a `multiprocessing.Process` child (spawn or fork) that crashes prints its traceback through
`BaseProcess._bootstrap` → `traceback.print_exc()`, bypassing `sys.excepthook` and utils' routed hooks;
`socketserver.handle_error` does the same. No such site exists in the estate today (`Pool` is safe). Complete solution,
when one appears: a `Process` subclass whose `run` catches and logs through loguru's safe path, and a sweep that
refuses a bare `multiprocessing.Process(` / `socketserver` server in production code.

**The product-event idempotency key is tenant-scoped, not user-scoped (B1, 2026-09-20).**
`product_events` has PK `(tenant_id, event_id)` and `POST /analytics/events` has no capability gate
(correctly — every user emits product events). So any authenticated member writes into a tenant-wide id
namespace, and a member who knows or predicts another member's `event_id` suppresses that event
permanently and silently: no row, no log line, `202 {"duplicates": 1}`. Not fixed now because the mint is
`crypto.randomUUID()` (122 bits) and the change is a primary-key migration whose `ON CONFLICT` target is only
**partly** guarded. **Premise corrected 2026-09-20:** core does have a conflict-target test —
`core-obsm/tests/unit/db/test_tenanted_write_paths.py:59` rglob-scans the whole of `core` and would catch a
regression to a bare `ON CONFLICT (event_id)`, because it requires every target list to *lead* with the
table's tenancy columns. What it does not do is pin the **full** key: a target that leads correctly and then
omits or reorders the rest passes, which is precisely the mismatch a `(tenant_id, user_id, event_id)`
migration could introduce. So the deferral survives on the narrower reason — the prefix is guarded, the key is
not, and copilot-mro's own scan covers only its own tree. The complete solution is
`(tenant_id, user_id, event_id)` — `user_id` is server-stamped and unforgeable, so it closes the class for
free — plus widening core's existing conflict-target guard from the tenancy prefix to the full key.
**RESOLVED by B2.1, 2026-09-20.** B2.1 took the omit-rather-than-weaken branch: the mint moved inside
the `try` and routes through `eventIdOf()`, with the `ChatInput` idiom's `Date.now()-Math.random()`
fallback **deliberately removed**. core types `event_id` as `Optional[UUID]` under `extra="forbid"` and
`events_endpoints.py` answers **400 for the whole batch** on one bad event — so a weak id would have
destroyed every product event from every insecure-origin browser, which is worse than the collision this
paragraph warns about. The module now omits the key and core's `event_id or uuid4()` covers it. The
sentence below described the risk correctly and it did not materialise.

**Sequence it with B2.1**, which fixes the same mint throwing on non-secure-context origins: any
lower-entropy fallback introduced there turns this from latent into live.

**A client that omits `event_id` gets no idempotency and no signal (B1, 2026-09-20).** `rows_for` mints a
fresh server-side id per attempt, so a batch retried after a network timeout double-inserts, `duplicates`
reads 0 and the 202 says everything was accepted. The compatibility window has no expiry, no metric and no
test. The complete solution is to require `event_id` once the dashboard client is known to send it (it does,
on their branch), and to count omissions until then so the window can be closed on evidence.

**FK-free tenant-classed relations survive tenant teardown (B1, 2026-09-20).** `delete_tenant` relies
entirely on FK cascade, and `dashboard_profiles` is declared FK-free — deliberately, matching
`product_events`, which has the same hole today and is swept only by a retention purge, not by teardown.
So this is a pre-existing estate contract question that the merge extends to one more relation, not a defect
this merge introduced. The test that would catch it cannot: `test_exactly_the_eight_identity_relations_
cascade_with_a_tenant` asserts the set of relations *referencing* `tenants`, and a relation with no FK is
outside its scope by construction. The complete solution is a declared teardown contract for tenant-classed
relations without FKs — an explicit delete list derived from the registry, asserted against it, so adding a
relation cannot silently skip teardown. Estate-wide; do it with Task R (G.1), which is what enumerates them.

**`int(row.get("profile_version") or DEFAULT_PROFILE_VERSION)` swallows a stored `0` (B1, 2026-09-20).**
It becomes `1` instead of raising through `DashboardProfileConfig.__post_init__`'s `version < 1` guard, so
the dataclass's own validation can never fire on the database path. Unreachable today —
`dashboard_profiles_version_check CHECK (profile_version >= 1)` — and therefore deferred; the complete
solution is to stop using `or` for a value whose falsy case is meaningful, and to let the dataclass be the
single validator rather than having the loader pre-empt it.

**`_S3_NON_ERROR_OUTCOMES` is a hard-coded set with no declared vocabulary (C1, 2026-09-20).** The five
`operation.outcome` values on the S3 span are bare literals at the call sites, and the non-error set is a
frozenset next to them. A new failure outcome defaults correctly to ERROR; a new *non-failure* outcome
(`cached`, `not_modified`) would be wrong until someone remembers the set. Deferred because the complete
solution is not a bigger frozenset — it is the F.4 reconciliation: `operation.outcome` collides with the
spec's `agent.outcome` / `tool.outcome`, and this merge shipped five more values into that unreconciled
namespace. Fix it once, as an enum with a registry entry, when F.4 decides the vocabulary.
**F.4 has decided (2026-09-20):** the key is `<subject>.outcome`, `operation` stays the subject for every
non-agent boundary, and the value set is what gets declared — so the enum-plus-registry-entry shape above is
the right fix and now has a name to hang on. One number worth pinning while it is here: the S3 span carries
**five** outcome values, not the four the Phase 1c signal table declared. The fifth is `miss`, the quiet
cache-fallback outcome on the `quiet=True` path, and it is one of the two values the non-error frozenset
deliberately keeps at OK status — so a reader working from the four-value set reads a cache miss as
unreachable. The Phase 1c table has been corrected in place.

**`BaseException` escapes both storage spans as UNSET (C1, 2026-09-20).** Both spans set
`set_status_on_exception=False` and both bodies catch `Exception`, so a `KeyboardInterrupt`, `SystemExit` or
`asyncio.CancelledError` unwinding through `download_pdf` or `hybrid_search` ends the span neither OK nor
ERROR and with no `operation.outcome` at all — invisible to every outcome query and non-error on the
dependency board. Low likelihood on sync boto3, non-zero for Weaviate under a shutdown drain. The complete
solution is a `finally` that stamps an `interrupted` outcome when the span is still UNSET, applied to every
wrapper of this shape rather than to these two by hand; it belongs with the Task R coverage matrix (G.1),
which is what will enumerate the wrappers.


---

### Phase D adversarial review — findings taken, 2026-09-20

An independent Opus reviewer over `e26be7dd..HEAD`. Four P1s, all confirmed; two fixed in the
phase, two escalated below. Its strongest result was structural: **the ordinary-log privacy guard
had two implementations** and the file's own self-tests called the copy, so the tests that prove
the guard works were exercising code that guarded nothing. Fixed (one body, `b112f860`), along
with a splat dict mutated after its literal, a structural suffix that exempted a whole keyword
from value inspection, and `.env.sample` documenting the exact inverse of M-CAPTURE.

It also found the sharper half of a defect **and the guard that was blind to it, in one**:
`drain_captures` was wired into copilot-mro's OWN lifespan, which Starlette never runs for a
mounted sub-app — and the guard reads that file FROM DISK, so it stayed green while the property
was false. Mutation-proven against the mutation that could not happen. Fixed in `api-obsm`
(`4da716f`), where the hook actually fires, with a test that drives the real gateway lifespan.

**Owner decisions these raise:**

- [ ] **Capture is ON by default and nothing purges it.** D.4 flipped the deployment default and
      core's column is `DEFAULT true NOT NULL`, which Postgres backfills onto every existing
      tenant. `expires_at` is stamped per row, but the DELETE is `scripts/purge_llm_turn_content.py`
      — no scheduler, no automation row, no cron, no compose or iac reference. So "30-day
      retention" is a claim nothing implements, on a store that now holds prompts, model answers
      and tool I/O for every tenant. M-CAPTURE already makes the Appendix A contract clause a
      go-live prerequisite; this is the concrete form of it. Either schedule the purge or ship
      capture off until it is scheduled.
- [ ] **M-EVALS' "the rest does not merge" never happened, and no phase owns it.** §5.8 rules
      REJECT-as-workbench and names three things to salvage. The merged tree carries the whole
      suite — `agent_evaluation/{phoenix_adapter,runner,session_runner}.py`, the CLI, the runbook,
      the compose overlay, the collector fragment, a 389-line test — plus an `evaluation` poetry
      group pulling `arize-phoenix-client`, `arize-phoenix-evals` and `litellm`. E.1's reject list
      is only M-ACCEPT and M-PINS; G.8 is a BUILD item, not a rejection. **M-RESIDENCY is
      unenforced**: grep for an allowlist across the runner and the CLI returns nothing, and the
      ruling says no eval run touches real traces until it is. The group is `optional = true`, so
      a plain `poetry install` is unaffected and `poetry check --lock` passes.

**Recorded, not fixed:**

- `tests/architecture/.../test_langchain_ambient_surface_policy.py` is RED and was red before the
  merge: it scans for `deployment/observability-local/otel-collector-config.yaml`, a path that
  exists in none of base, ours or theirs. Pre-existing on our mainline, in no phase's lane, and
  worth naming now so a later fast-forward does not mistake it for merge damage.
- **D.6's saving is smaller than claimed.** `accumulator.snapshot` — the redaction and
  serialisation walk, and the bulk of the cost — is still awaited on the settle path; what moved
  off it is one indexed INSERT. And there is no S3 put to move: `content_s3_key` is always None,
  object-backed overflow is future work, and `purge_llm_turn_content.py`'s `RETURNING
  content_s3_key` is dead. The module docstring and the D.6 commit both overstate this.
- **The late-bootstrap fix restores the HELPER, not the composition.** `get_agent_pipeline` is
  still `@lru_cache(maxsize=1)` and freezes `runtime_telemetry` — and with it `post_tool_observer`
  and `suppress_legacy_agent_sdk_spans` — into the composed objects at first use. A process that
  composes before it bootstraps is still permanently untraced. The new test's docstring overstates
  what it proves.
- **The D.2 repoint narrows the blindness without closing it.** The harness reader checks the
  DEPLOYMENT switch only; a fixture tenant with no `tenants` row fails closed at the per-tenant
  gate and degrades to the same SKIP, with a better reason string but no up-front named
  unavailability.
- `llm_content_capture_tasks._PENDING` has no cap: with capture on by default and off the request
  path, a wedged Postgres accumulates one hanging task per turn with no backpressure. The awaited
  version at least throttled. `chat_block_saves` has the same shape, so this is
  precedent-consistent rather than novel.
- `copilot_mro/app/api/llm_observability.py:191` — a file the merge brought in — logs
  `error_type=type(exc).__name__`, the §2.3 "strictly weaker" form. Part of the estate-wide B-R1
  backlog (~60 sites), not a new defect, but neither sweep reached it.
- C1.5's first clause (`WEAVIATE_GRPC_PORT` into the copilot-mro env and compose files) is still
  owed: 0 hits across all six. Phase E.
- **Nothing enforces the dynamic-loader convention.** CLAUDE.md names a module-scope
  `from copilot_mro.app...` import in a copilot-mro test as an anti-pattern, and it cost ten failures
  this phase from one of their files — plus one more from a file I wrote myself, fixed the same way.
  `tests/unit/infra` already carries the layout and depth guards; this belongs beside them, as an AST
  check that no test module imports `copilot_mro.app.main` (or any `copilot_mro.app.services.*`) at
  module scope without an exemption naming its reason.
- `config.py` still declares `tool_io_archive_enabled` after M-TOOLIO-2. Load-bearing for one good
  test (`test_agent_sdk_claude_content_feeders` asserts `archive is None` even when the flag is
  True), so keeping it is defensible — but `tests/e2e/run_explain_latency_e2e.py` still prints it
  as a diagnostic that can now only ever say False.

**What the review could NOT break**, checked and reported as such: D.1's graft (every acceptance
site intact, and independently pinned by a silent merge of THEIR test asserting the exact
`AgentPipeline` parameter list); M-TOKENUSAGE's instrument-type guard; D.10; the composition-root
silent merge; and the two tests this phase relaxed, both of which pin the property more tightly
than the shape they replaced.

### Review round 2 and the theirs-only audit, 2026-09-20

The reviewer returned a correction pass. Both new points confirmed by reproduction.

- **A teardown ERROR I introduced.** D.7 added `get_runtime_telemetry` as the composition-root
  fixture's third cache to clear; one of their tests monkeypatches that symbol with a bare lambda,
  so teardown called `.cache_clear()` on a lambda. The test BODY passed and the file errored — and
  D.1's stated acceptance is "their composition-root test passes". Fixed asymmetrically: SETUP
  asserts each of the three still has a `cache_clear` (that is the regression worth catching, and it
  runs before any patch), TEARDOWN tolerates its absence, because a stub having no cache is correct.
  This is also the "1 error" that appeared in a lang_agent lane early in the phase and was not chased.
- **A correction to `b112f860`'s own record.** It says the reviewer's probe read green "against the
  copy while the real path already caught it". Wrong, and the distinction matters: their probe
  called the PATH-based function, and those cases were genuinely green there —
  `_is_mutated_after_its_literal` is what closed them, not merging the two bodies. The
  duplicate-body finding stands; the attribution did not.
- **The guard's last hole** (`query_type=message`) is closed. Putting `message` in the general
  content list flags `message.subtype` and `getattr(message, "session_id", None)` — facts ABOUT the
  turn — so it went into a BARE-ONLY class, compared against a bare `ast.Name` and never walked over
  an expression. `_log_detail` joined `failure_fields` as a recognised sanitiser.

**The theirs-only audit, which is the method gap that let flightops through.** The §2.2a register was
built from files BOTH sides changed, on the reasoning that collisions are where decisions get lost.
A THEIRS-ONLY edit to a file whose guard is ours merges just as silently, and there are far more of
them: 65 theirs-only production files here against 22 in the intersection. Four carried a
lost-sanitiser or narrowed-field signature; the fourth was `amos_synthesis_core._error`, D.11's own
defect in a sibling file (`bb7cbe35`).

**D.11's wording was a description, not an inventory.** "The synthesis and db-query logs" — I fixed
three files and there were four. A plan item that names a CLASS of site needs the class enumerated
before it is ticked, not the examples it happens to mention.

### Deferred from Phase D, 2026-09-20

- **`record_subagent` has no production call site anywhere.** `RuntimeTelemetry.record_subagent` and its
  two instruments (`agent.subagent.calls`, `agent.subagent.duration_seconds`) are dead: the only caller
  in the tree is a unit test. The lang runtime's subagent dispatch (`SubagentDispatcher`) has zero
  telemetry references. The `fn-llm-agents` "Subagent rate and p95 duration" panel is therefore
  permanently empty, and their catalogue inventory correctly marks it PENDING. This is the plan's owed
  "subagent call sites" work and it is genuinely unstarted — the merge did not touch it.
- **Branch attribution is lost on the canonical tool path.** `ToolOperationRecord` carries
  `parent_call_id`, and the LEGACY `emit_tool_spans` path sets `gen_ai.tool.branch_id` and
  `gen_ai.tool.ref`. `record_tool_operation` sets neither. So once `suppress_legacy_agent_sdk_spans` is
  on — which, after D.12, is whenever OTel is actually configured — a branch-leaf tool span is
  indistinguishable from a parent one.
- **Dispatcher-projected standalone tools are outside the observer.** `post_tool_observer` is threaded
  into exactly ONE builder (`build_claude_pilot_tool_runtime`). The ~12 `build_standalone_*` projections
  ride a lighter tail and take no observer, so they emit no `gen_ai.*` operation and are absent from
  `canonical_tool_names`. That is consistent with their "suppress duplicates without hiding
  non-migrated calls" design, but it means the canonical tool surface covers only the pilot
  dispatcher's tools — and our own P6 work moved tools OUT of that set while their telemetry work was
  landing on the assumption they were in it. Neither side is wrong alone; the seam between them is the
  coverage hole.
- **A failed tool can leave a step event with no tool-I/O record.** On the unauthorized branch-leaf leg
  and on a raising parent dispatch, `nodes.py` emits the failed step but `continue`s past both
  `_record_tool_io` and `dump_tool_call`. Each side is internally consistent; the union is not. A turn's
  step trace can therefore show a failed tool that has no entry in `content.tools.io`.
- **`model_gateway._error_snapshot` stores the exception MESSAGE.** Deliberate and correct as written —
  the destination is the governed capture store, which already retains the raw prompts beside it, and it
  is double-gated. Recorded so a future R22 sweep does not "fix" it into uselessness.
- **`prometheus-client` is now an orphaned dependency** and `README.md:122` still documents
  `GET /metrics`, which their side removed (correctly — the estate is push-only over OTLP, and the api
  gateway removed its own copy in an earlier phase).
- **`BrowserSpawnError`'s stderr tail no longer reaches any log.** D.8 stopped logging the exception
  message because it embeds up to 2000 bytes of subprocess stderr. The tail is still on the exception
  for the caller; if spawn failures prove hard to diagnose, the right fix is a bounded, explicitly
  sanitised field, not restoring the message.

### Deferred from Phase G, 2026-09-21

Moved here from G.39 and G.65 by the 2026-09-21 audit. Each is a known gap with a named fix, not open work
for a lane.

- **`WeaviateTenancyError` messages interpolate tenant and operator ids (G.39).** *Missing:* the message
  text itself carries identity — e.g. `copilot-mro-obsm weaviate_tenancy.py:469-473` renders the bound
  `tenant_id` and every operator id — and copilot-mro deliberately re-raises these into the retrieval path,
  so any handler that renders `str(exc)` re-materialises what the log pass removed. *Why deferred:* the
  class is raised in `copilot-mro` and classified in `utils`, so the fix is cross-repo, and changing what a
  message says is a **message-contract ruling**, not a lane's call. *Elegant fix:* carry the ids as
  structured attributes on the exception, keep the message a generic constant, and let only the sanctioned
  field helpers read the attributes.
- **The log sweep walks only `except` bodies (G.39).** *Missing:* a same-module helper that receives the
  exception as a parameter is invisible to `utils-obsm tests/unit/observability/test_utils_logs_no_exception_text.py`,
  whose detector reads handler bodies only. *Why deferred:* found as a reviewer's limit on a guard that was
  already green, not as a leak. **The SPAN sweep has already closed this** — `utils-obsm 099629f` follows a caught exception one hop into
  module-local helpers. *Elegant fix:* lift that one-hop resolution into the shared detector so both pipes
  run the same rule, rather than porting it a second time.
- **A handle stashed on `self` evades the Weaviate door scan (G.39).** *Missing:* the scan matches a
  handle where it is used, so `self._x = collection` in one method and a round trip through `self._x` in
  another is not seen as a door. *Why deferred:* closing it needs intra-class dataflow, a bigger analyser
  than the whole guard. *Elegant fix:* stop scanning for doors
  and make the door a type — every round trip goes through the traced accessor, and the guard asserts that
  no module reaches the raw client at all.
- **The hybrid→BM25 fallback still reports `success` (G.39).** *Missing:* a retrieval served without its
  vector half is an OK span; the only record is the `weaviate.vector_fallback` attribute
  (`utils-obsm weaviate_service.py:1454`), which no panel or alert reads. *Why deferred:* whether a degraded
  answer is an error is a product call, and today it is at least visible where before nothing recorded it.
  *Elegant fix:* a declared `degraded` outcome in the `<subject>.outcome` vocabulary (non-error, but
  countable), charted beside the error share.
- **The narrow cardinal/absolute lint (G.65).** *Missing:* nothing catches a cardinal number or an absolute
  (`the only`, `every`, `and by nothing else`) beside a backticked identifier that the code contradicts.
  *Why deferred:* the **lowest-value** guard left in this phase — the individual pins it named have landed
  (G.61's derived notice, G.64(a)'s vocabulary pin, the G.64(b)/(c) cardinals deleted), except a generated
  inventory of api's `REASON_*` constants. *Elegant fix:* not the lint — generate the sentence or pin the
  number where the value is owned, as `contracts/*.json` already does; build the lint only if a fourth
  instance appears after the pins.
- **iac's `tests/_root.py` is still its own shape, and iac has no `test_root_anchoring.py` (G.52), 2026-09-21.**
  *Missing:* the carried copy (api `8d7e39f`, md5 `3d192468`) never reached iac (md5 `97efbf18`).
  *Why deferred:* no Phase G item assigns it to iac, iac makes no cross-repo reads (so the carried
  sibling-variant helpers would be dead code there), and a byte-copy moves every tree's drift pin.
  *Elegant fix:* one pass that copies the file and its anchoring test into iac and updates each drift pin
  in the same breath.
- **G.47's eleven derived browser series have no aws panel or alarm, 2026-09-21.** *Missing:* the
  `signaltometrics/browser` series (incl. `browser.web_vital.value`) are the one aws path to web vitals
  not known to be broken, and nothing in iac reads them. *Why deferred:* choosing them over the dead
  metric-filter selectors is the browser-alarm rework, which follows the C2 probe. *Elegant fix:* decide
  it with M-ALARM-DENOMINATOR after C2: if the filters come back dead, alarm on the derived series instead.
- **The aws legacy rows' label keys and values are hand-checked only (iac review r3 P3-5), 2026-09-22.**
  *Missing:* check 7 of `validate_metric_vocabulary.py` reads log widgets by design, so a PromQL label on
  the 15 legacy panels is never compared with the family's declared attributes: `"token_type"` →
  `"token.type"`, `"tenant_id"` → `"tenant.id"` (the log bridge's spelling, wrong for a metric) and
  `"outcome"="failure"` all pass every checker (V1, V2, V6). The reviewer checked every key and value by
  hand against `legacy_families.py` and the emitters, and all are right today. *Why deferred:* the catalogue
  of declared keys and closed value sets lives in utils (`legacy_families.py` `FAMILIES`), which this CI cannot
  reach (the validator's DEFERRED note), and hand-copying 18 families' attribute sets into iac would be a
  second drifting copy. The recorder-name pin (`74346bb`) is the one hand copy taken, because it is five words. *Elegant fix:* the
  same one DEFERRED already names: utils (and copilot-mro, telegram-bot, shift-optimizer) PUBLISH their
  instrument inventory as a committed data file (name, kind, unit, emitter function, declared attribute keys
  and closed value sets), vendored beside CATALOGUE.md. The validator then derives FAMILY_SUFFIXED_INSTRUMENTS,
  the recorder names and a label check from that one file: every `by (...)` key and every `"k"=…` matcher
  on a selector naming family F must be a declared key of F, and a literal value on a closed key must be in
  its set (or `other`).
- **Two EC2 exemptions rest on sibling-repo source reads (iac review r3 IR3-10/12), 2026-09-22.** *Missing:*
  the Weaviate host (demo compose: collector, Weaviate, UI) and the gpu host (vLLM) are EXEMPT on reads of
  copilot-mro and llm-platform that no iac test can repeat. *Why deferred:* same cross-repo reach limit.
  *Elegant fix:* the published inventory above plus a per-profile image manifest from each compose owner.
- **The shared test network guard is parked OUT of this project (M-SHARED-NETGUARD, owner ruling
  2026-09-22).** *Missing:* the netguard r1 review's P1 (a refusal in a skipped or xfailed phase fails its
  phase) and P2s, the port of api's guard fixes into `flynapse_otel.testing.network` beyond what is already
  committed in flynapse-otel, api deleting its own `tests/_netguard.py` copy, and consumer adoption —
  copilot-mro first, the repo whose tests sent real Bedrock requests (620 + 332 attempts), then core's
  `tests/api` (121). The api r9 bypasses stay unbuilt with it: libpq's lower entry points
  (`psycopg2._connect`, `psycopg2.extensions.connection`, `psycopg.pq.PGconn.connect`), `service=` service
  files, the `env` / `env -i` / `timeout` launchers, `socket.SocketType` and `super(socket.socket, s).connect`,
  dnspython over loopback `:53`, an ephemeral-range port rule instead of the hand-kept service list, and
  `/etc/hosts` trust (judging a name by the answer, not the table). One ported quality fix was in flight and is
  NOT committed — blanking the `*_PROXY` variables rather than removing them, so an application's own
  `load_dotenv()` cannot set one back; its diff is kept at
  `~/.claude/scratch/obs-merge/otel-impl-r8/parked-netguard-r9a/r9a-blank-proxies.patch`. *Why deferred:* the
  owner never asked for this work — it is test hygiene, not telemetry, and it had run three review rounds
  finding ever-smaller bypasses. *Complete solution:* its own owner-scheduled plan that resumes from
  `flynapse-otel/docs/plans/m-shared-netguard.md` (the port table, the r1 claims and the mutation tables are
  all written there), lands the P1/P2s, proves the FAIL half at every scope including under `-n`, then adopts
  repo by repo and deletes api's copy last.

## 7. Implementation notes / learnings

### Phase 0 — 2026-09-19, CLOSED

Six adversarial Opus lanes, all read-only. **Nothing merged. No worktrees created. No commits in any repo.**
Four earlier merge-lens assessments (same day) produced ~40 findings that the Phase 0 lanes adjudicated rather
than inherited — several were refuted or re-ranked, which is the point of adjudicating.

Verdicts: content capture **2 REJECT** · telemetry emitters **3 REJECT** · Phoenix evals **REJECT as a
workbench** · non-agent spans + tests **REJECT on scope and on the log sweep** · deployment **REJECT** ·
core / dashboard / utils / api **ACCEPT-WITH-FIX** · the plan itself **NOT READY**, six P0s, all since fixed.

Deviations from the plan as first written, all forced by findings:
- Phase 0 did not exist. The owner inserted it: review their branch standalone before merging anything.
- The repo order was corrected (§2.2) and the letters in §3 no longer read in sequence.
- The migration step was wrong in kind, not degree, and gained the RLS run.
- The acceptance baseline was re-measured by running the lane.
- The review tiering was amended after the inert-test audit.
- M-TOOLIO was superseded by M-TOOLIO-2 once the two rulings were shown to conflict.

What the lanes did that made them worth their tokens, worth repeating:
- **One lane ran the pinned collector image** instead of reading YAML, and found a crash-loop that
  `otelcol validate` reports as healthy. Nothing short of starting the process finds that class of defect.
- **One lane ran our guards against their tree and theirs against ours.** That asymmetry — 118 offenders one
  way, 0 the other — is what exposed a guard whose verdict is a property of the checkout rather than the code.
- **One lane materialised the merge tree and ran pyflakes on it**, which is how the `traceback` `NameError`
  in a cleanly auto-merged file surfaced.
- **One lane re-ran the acceptance number** the plan asserted, and it was from a different lane entirely.

### Phase C1 — utils, 2026-09-20, MERGED (worktree `utils-obsm`, merge commit on `obs-merge`)

Textually clean merge, 7 files. Lane **1209 passed / 0 skipped** against a pre-merge baseline of **1190 / 0**,
run from the shared `api` env with `PYTHONPATH` pinned to the worktree and the resolved `utils.__file__`
printed once before the numbers were trusted.

**What the adversarial review changed.** It found the phase's headline item inert and one uncovered control:

- **`record_exception=False` had no test.** Flipping it to `True` passed all 1203 tests while exporting
  `exception.message` and a stacktrace ending in `Type: message` to Tempo. The privacy helper iterated log
  records only, so the entire trace pipe was unexamined — R22 relocated to the one export path nothing
  inspected. Fixed by folding span attributes and span **events** into the helper and asserting no `exception`
  event on both failure paths.
- **C1.1 was inert.** Reverting `failure_fields(error)` to `error_type=type(error).__name__` passed. The two
  R22 AST guards in the estate sweep fixed module lists (7 copilot-mro paths; `utils/postgres_service.py`
  alone) and neither contains these modules, and P0-GUARD's sweep is assigned to D.8, which is copilot-mro.
  Fixed by asserting `stack` is present at both sites. The Weaviate site had **no** R22 test at all — a full
  f-string leak passed, because the only assertions were about the query and the collection name, neither of
  which that code path ever logged.
- Five source guards were then mutation-proven individually (connect-failure log, `server.address` on each
  span, the `WEAVIATE_GRPC_SECURE` override, `urlsplit` vs `startswith`): each mutation fails exactly one test.

**Rejected from the review:** its P2-7 asked for the bucket name on the S3 failure lines, arguing the bucket is
configuration rather than customer content. Their own privacy test asserts the bucket is absent from every
export, and that is a ruling this phase does not get to overturn on its own. The trace id is already on every
record, which is what makes the line actionable. Recorded, not applied.

### Phase B1 — core, 2026-09-20, MERGED (worktree `core-obsm`, `5d40d70`)

Textually clean merge, 16 files. Lane **2866 passed / 2 skipped / 2 xfailed** against a pre-merge baseline of
**2829 / 2 / 2** — nothing lost, no new skips — after running the all-registry tenancy migration against
`copilot_mro_test` with `PYTHONPATH` pinned to the merged worktree (without that the migration reads the
PRE-merge table definitions and creates none of the new schema).

**The finding that justified the phase: M-CAPTURE was split across two repos and neither half was wrong on its
own.** Their `tenants.llm_content_capture_enabled` is an opt-IN defaulting to `false`, with a test pinning it.
The owner's ruling is capture ON by default, tenant opt-OUT. The plan had assigned M-CAPTURE only to D.4, the
copilot-mro policy reader — so the merge would have flipped the reader to honour a column whose every row said
`false`, and capture would have been off estate-wide with both repos reading as correct. Column now defaults
`true`; verified in the database after migration.

**P0-499 needed no action, and that is the result, not an assumption.** The clean auto-merge kept our
`ClientDisconnect` → 499 path and grafted their `duplicates` change inside the same `try`. Confirmed by
reading the merged handler rather than by the absence of a conflict.

Verified rather than trusted, on their idempotency work: the primary key really is `(tenant_id, event_id)`, so
the `ON CONFLICT` target resolves and a replayed id cannot collide across tenants; and `MAX_EVENTS_PER_BATCH`
is 50, so the widened INSERT binds at most 750 parameters — well clear of the 65535 wire limit that would have
made a large batch fail at the protocol layer.

Database state after this phase, confirmed by query: `product_events.schema_version integer DEFAULT 1 NOT
NULL`, `tenants.llm_content_capture_enabled DEFAULT true`, `dashboard_profiles` present with RLS **enabled and
forced** and a `dashboard_profiles_isolation` policy. `llm_turn_content` is correctly still absent — it is a
copilot-mro registry table, so `--registry core` was never going to create it and neither did the all-registry
run against an unmerged copilot-mro.

### Phase B2 — dashboard, 2026-09-20, MERGED (worktree `dashboard-obsm`, head `3afd524`)

Five commits on `obs-merge`: `42b3380` merge · `acd8b78` B2.1 · `9002ed9` B2.2 · `cc17cf4` B2.3 ·
`3afd524` review triage. Working tree clean, nothing pushed, no mainline moved.

**Lanes.** `typecheck` rc=0 with output **byte-identical to pre-merge at every step**; `next lint`
likewise byte-identical; unit **2475 → 2502 passed, 0 failed, 0 skipped**. `next build` was never run
and the merged standalone guard fired correctly when it was attempted. Because the background runner
truncates output to its tail, no failing-id set difference was quoted from it — `fail 0` on both sides
makes the difference empty by construction, and loss was disproved the local way instead: for every
changed test file, `git show 4a2898b:<f>` against the file shows **no test name removed anywhere**,
+27 all additive.

**Silent-merge register (§2.2a), dashboard.** Textually clean, **zero conflicts** across all 15 files,
so the merge commit carries no resolution because there was none. **Both sides (4):**
`analytics-panel-registry.ts`, `analytics-api.ts`, `product-events.ts`,
`analytics-panel-registry.test.ts`. **Theirs-only (11)**, each audited against our guards
(`logger-message-constant`, `api-route-pattern-bounded`, `route-pattern-table`,
`logger-client-import-graph`, `mutation-response-contract`, `route-access`, `standalone-guard`) — none
violated.

**B2.1, and the reasoning matters.** The defect was reproduced first: the new guard failed on the
merged tree with `TypeError: globalThis.crypto.randomUUID is not a function`. The mint moved inside
the `try` and now routes through `eventIdOf()` — but the repo's `ChatInput`/`useChatAttachments` idiom
was adopted **with its `Date.now()-Math.random()` fallback removed**, deliberately. core types
`event_id` as `Optional[UUID]` under `extra="forbid"`, and `events_endpoints.py` answers **400 for the
whole batch** on one bad event, so a weak id would have destroyed every product event from every
insecure-origin browser — a far worse outcome than the tenant-wide `(tenant_id, event_id)` collision
§6 warns B2.1 not to escalate. The module now **omits the key**; core's `event_id or uuid4()` covers
it. This resolves §6's "sequence it with B2.1" note: B2.1 took the omit-rather-than-weaken branch.

**B2.2 / M-FALLBACK.** Their page replaced the capability gate outright and set an *empty profile* on
any failure — and their own test asserted that outcome, a P0-INERT-class defect-pinning test, which was
rewritten rather than deleted. The page now carries a three-valued `DashboardOffer`
(`profile` | `capability` | `none`), because a nullable profile cannot distinguish "core said offer
nothing" from "core said nothing" from "nothing to ask yet". Only the middle degrades. That also
retires §5.5's "these become dead code" finding. `fetchDashboardProfile` gained a read response
contract, so a malformed 200 is now a rejection the fallback handles rather than a `TypeError` inside a
`useMemo`.

**B2.3.** All five sub-items landed: typed error state (`classifyAnalyticsError` with card-local copy,
never the server's prose), a constant-message `logger.error` breadcrumb, a response contract in place
of the bare cast, TanStack `useQuery` (new `hooks/api/useObservability.ts`, new
`queryKeys.observability.llmTurns`) replacing hand-rolled `useState`/`useEffect`, and the
mis-describing docstring corrected.

**Adversarial review — two independent Opus reviewers. No P0. Both of the two real findings were the
implementer's own, and both were corrected in `3afd524`:**

1. **The M-FALLBACK 403 rationale was fiction.** It was taken from THIS PLAN's B1.2 wording
   ("tenant-admin gate") rather than from core's body. The 403 branch stays — a gate is a thing that
   changes — but is now documented as unreachable today. B1.2's wording is corrected above.
2. **"No widening" was half true.** `panel_service.get_panel_data` calls `authorize_panel` +
   `feature_enabled` and **never reads `dashboard_profiles`**. So the degraded read does not widen
   *capability*, and **does** widen past a tenant's own narrowed profile. Now stated precisely in the
   docblock.

Also fixed: the test harness answered **503 for every `Error`**, so "the caller is refused" was an
outage with different prose. Failures now carry a status, the wire records it, and each case asserts
the status it names — which immediately found that **401 never reaches this fallback at all**
(`fetchWithAuth` refreshes and then navigates to sign-in). Recorded rather than asserted, because
pinning a jsdom navigation pins an environment.

**Four properties had no guard at all.** `retryLlmTurnSummaries` had zero references outside its
module, and the card's only mounted test built its own `QueryClient` with `retry: false` and no
`QueryCache` — so both the retry rule and `meta.suppressGlobalError` were unguarded. A new
`llm-turn-summaries-hook.test.tsx` drives the real `makeQueryClient()`. The retry rule also **changed**:
it no longer reads `ANALYTICS_ERROR_COPY.retryable`, which answers "is a *button* worth offering" — a
human, a minute later. A machine re-asking a 429 at TanStack's ~1 s backoff adds load exactly when core
asked for less, so only `unavailable` auto-retries.

**13 mutation proofs**, every one restored from a scratchpad copy; `git checkout --` never used.

**M-FRONTEND needs no dashboard-repo action** — verified both halves. `dashboard-obsm` references no
Grafana board, uid or panel count anywhere, and the merge touched none of `lib/telemetry/events.ts`,
`use-route-telemetry.ts`, `TelemetryProvider.tsx` or `events-catalogue.test.ts`; `browser.app.boot` is
unchanged and still unconditional.

**Owner rulings owed out of B2:** **B2-R1** the LLM-turns card's placement outside the internal-only
gate (stated at D.9 above) · **B2-R2** M-FALLBACK's true scope now that the widening is stated
correctly — the degraded read shows a tenant the un-narrowed offer while the profile route is down;
core calls the profile "presentation state only… It never grants panel access", so the ruling reads as
still standing, but it was taken without this fact · **B2-R3** `dashboard_profiles` still has **no
writer anywhere in the estate** (§5.5 P1, unchanged by B2), so no tenant can narrow anything yet.

**Recorded for §6 Future Improvements, deliberately not fixed:** the offline wedge (`isPending` +
`networkMode:'online'` leaves "Loading captured turns…" forever with no exit; it needs a third *paused*
branch, not a swap to `isLoading`) · **version skew** — a 200 profile naming panel ids this build does
not know intersects to `[]` and renders exactly the blank page M-FALLBACK exists to eliminate, with no
degrade, because the fetch succeeded · panel-order drift between `panelsForProfileTab` (profile order)
and `panelsForTab` (registry order) · `logger.error` books an ordinary `forbidden` as an ERROR record,
one per mount · the `llmTurns` query key omits the tenant while `shouldClearQueryCache` keys on user id
— one reviewer suspected a hole, the other proved it unreachable; recorded, proved neither way · **no
guard requires a *read* api to use `parseResponse`** (the existing guard walks `useMutation` only), so
both read contracts B2 added are voluntary · the profile wire shape is declared twice
(`DashboardProfileView` / `DashboardProfileResponse`) — the dashboard analogue of B1's two-copies
finding · a `randomUUID` that exists and throws is booked as a caller bug, documented in code as the
accepted price of one catch · `content_bytes: 0` renders `—`.

**Honest gaps.** Nothing in B2 is half-done. Two things to know: the three M-FALLBACK failure routes are
behaviourally identical **by design**, so the status assertion is the only thing that can tell them
apart — the degrade itself is proven once, not three times. And no B2 plan item turned out stale in the
"already done" sense; the staleness encountered was in **this plan's description of core** (B1.2), which
is what produced the false 403 rationale.

### Phase C2 — api, 2026-09-20, MERGED (worktree `api-obsm`, head `9812f44`)

Eight commits: the merge (`37121a3`, resolution only), the five items, a self-review pass, and the
response to an independent adversarial reviewer. Lane **1170 passed / 4 skipped / 0 failed / 0
errors** against a pre-merge baseline of **1134 / 4**, re-measured with all four merged worktrees on
`PYTHONPATH` after the reviewer pointed out the first run had used pre-merge `utils` and `core`. The
set difference of failing ids is empty. pyflakes is **51 findings before and 51 after**, identical
modulo line numbers; ruff 70 → 71, the delta being one `E402` of the same kind as 24 already present.

**M-LOCK's premise was verified, not assumed.** `poetry check --lock` FAILS on their lock — its
content-hash predates our psycopg dev-group addition — and passes on ours. Git's silent splice had
kept our content-hash while taking their Poetry-2.4.0 header and two reordered marker lists, which is
a lock describing a resolution no `poetry` run ever produced. Taken ours wholesale; their one real
fix was already on our side. `pyproject.toml` and `poetry.lock` are byte-identical to `4da716f`.

**C2.1/C2.2 — the defect was reproduced before it was fixed**, and it was wider than the plan said.
`logger.error(f"Request failed: {exc}", error=…)` raises `KeyError "'type'"` against the pinned loguru
when the exception's message is a Pydantic error repr. Their `bind` mechanics were taken; their
message was not, because keeping the text as a `{}` argument buys back the same re-raise. The same
defect was live at **two sites their diff never touched** — `main.py`'s general exception handler and
`middleware/auth.py`'s unhandled-exception handler, the latter being the one that builds the
CORS-decorable 500 the dashboard depends on. Both fixed, and pinned by a repo-wide AST guard rather
than by three assertions.

**C2.3 — M-WARN at the gateway.** `warn` is **refused** in a deployed environment, not downgraded,
and refused *before* the check runs so it does not wait for the day partitions are short. The return
value is the `/health/ready` entry, recorded on `app.state.degraded_components` and folded into the
readiness body, lowering `healthy` → `degraded` while still answering 200 — which is the whole point
of the mode. Two AST cases now pin the call site, because their change had turned
`assert_partitions_provisioned` from a CALL into an ARGUMENT, invisible to the repo's call-by-name
boot guard, and nothing in the suite asserted the gateway runs the Weaviate check at all.

#### C2.4 — §5.6 is refuted on the merged tree, and C2.4 was executed instead

§5.6 says "Phase C2: revert to the strict rule", on the premise that nothing in the diff puts
`assert_rls_enforced` inside a `try`. That is true of their **api** diff and false of their
**copilot-mro** branch. Measured with both detectors against the merged `copilot_mro/app/main.py`:
**1 offender under strict, 0 under relaxed** — the merged lifespan legitimately wraps the call to
stamp the startup span and re-raises. Reverting to strict would have shipped a guard that fails the
moment copilot-mro's merge reaches the mainline. The later plan item (C2.4) is also the correct one.

The real defect in their relaxation was that `any(isinstance(stmt, ast.Raise))` is satisfied by a
`raise` that a `return` never reaches. The guard now requires an unconditional top-level `raise` and
no `return`/`break`/`continue` outside a nested definition, and additionally handles
`contextlib.suppress`, `return`-in-`finally`, `except*`, and one level of local-helper indirection.
The remaining limitation — a helper in another module — is pinned by a test asserting it is NOT
caught, so the coverage is legible instead of assumed.

#### The adversarial reviewer's severest finding: a live database name on an anonymous route

`/health/ready` sits outside `api_prefix` and skips auth. The readiness entry carried the error's own
`remediation`, which is `REMEDY.format(database=<SELECT current_database()>)` — so an unauthenticated
caller received a live database name and an internal script path. Three lines above, the same
function strips `debug` for exactly this reason (G28). The entry now carries a stable `detail` token
only and the remediation stays on the log.

It also caught three guard holes and one test that passed for the wrong reason: the new real-gateway
readiness test reached Postgres, S3 and Weaviate **for real** when run in the same process as
`tests/startup`, because `main.py` imports the health router under the flat spelling
(`routers.health`) while the test patched the qualified one — two module objects, two
`_aggregate_probe` globals. Found only because a fingerprint assertion had been added. It now locates
the module through the route and asserts the fake probe's service-key set, so it cannot pass against
a live AWS session again.

**24 mutation labels across 23 runs** (M1–M5, W1–W7, G1–G5, H1–H3, F1/F2/F3b, P1; G2+G3 were applied as one run, and the series carries an `F3b` with no `F3`), each restored from a scratchpad copy rather than by `git checkout --`. The figure of 18 previously on this line did not reconcile with any grouping of the commit bodies; corrected 2026-09-20 from the C2 claims table, which also downgraded two of the 24 to ASSERTED (M1 names a count, not which tests; and no mutation reverted `main.py:520` itself).

#### Silent-merge register (§2.2a), api

**Both sides (2):** `flynapse_api/main.py`, auto-merged into a region ours never touched, corrected in
C2.3; `poetry.lock`, the silent splice, resolved to ours.

**Theirs-only (6), and this is where the risk sat:** `middleware/logging.py` — **no api R22 guard
swept it**, the repo's only `failure_fields` site being `main.py`, so their `error=str(e)` +
`traceback=format_exc()` would have merged with nothing to catch it. `startup/weaviate_partitions.py`
— a new file using `error_type=type(error).__name__`, the exact P0-GUARD anti-pattern, in a file no
sweep lists. `startup/__init__.py` — adds a bare top-level module name `startup`; checked for
collision, none. `test_startup_boot_check.py` — OUR guard, edited by them alone.
`test_weaviate_partition_startup_mode.py` — asserts an exact log tuple containing `error_type`, which
would have **locked in** the R22 regression. `test_logging_context_middleware.py` — not merely kept: their
`test_exception_logging_preserves_errors_with_mapping_text` was REMOVED and replaced with three cases over a
captured-record fixture. The substance holds; the earlier wording "kept, with the assertion it lacked
added" understated the change (corrected 2026-09-20 from the C2 claims table).

#### Corrections to the plan from this phase

- **§5.6's instruction is refuted on the merged tree** (above). Recorded here because it had been
  living only in a test docstring.
- §3's C2 says "five symbols that exist only on their copilot-mro branch"; measured, **four**.
- M-LOCK's stated premise is verified true, including the `poetry check --lock` failure on theirs.

#### Owed out of this phase, not done in it

- **M-WARN is split-brain across two processes.** The gateway now refuses `warn` in a deployed
  environment and logs the error's own remediation; `copilot-mro`'s own `main.py` honours the
  identical variable with **no environment gate at all** and logs the `<database>` placeholder
  constant, so M-WARN clauses 1 and 3 are unimplemented there. Mounted under the gateway copilot-mro
  gets no lifespan — but it runs standalone in the dev stack and in its own deployment. The elegant
  fix moves the gate into `weaviate_boot_check.partition_boot_check_mode()` so both callers inherit
  it, leaving api's helper to shape the readiness entry only. **Phase G item.**
- **`settings.is_production` (`not DEBUG`) is api's only environment discriminator, and it is wrong in
  both directions**: a `DEBUG=false` local stack cannot use the mode the feature exists for, and a dev
  tier running `DEBUG=true` makes `warn` selectable *and* returns 200 from `/health/ready` over a
  known isolation hole. Mitigating: `DEBUG=true` already disables `SecurityHeadersMiddleware` and
  flips the telemetry environment, so it is already a severe misconfiguration in a deployment. `iac`
  has a real `var.environment`; api's settings expose no `ENVIRONMENT` field and App Runner sets no
  `DEBUG`. Adding one is a deployment-contract change — **owner ruling owed.**
- **B-R1 stays open in this repo, explicitly:** 11 `error=traceback.format_exc()` sites in
  `flynapse_api/main.py` and one in `routers/health.py` still ship a rendered traceback whose last
  line is `Type: message`. The new guard is scoped to the format-string defect and will never see
  them. Owner-owed under §4c; stated here so it is not implicit.

### Phase D — copilot-mro application half, 2026-09-20, MERGED (worktree `copilot-mro-obsm`)

Commits on `obs-merge`: `e26be7dd` merge, `36467f29` repair + reject-list, `12b899ed` privacy,
`248590dd` capture, `04ad6284` provider gate + token usage, `2879a1cf` repoint + scope + paths.

**The merge.** 20 textual conflicts, exactly the six app-code files §3 predicted plus the deployment
half and `poetry.lock`. D.1 held: their 59-line `agent_pipeline.py` delta was grafted whole, so all
four acceptance sites survive and `RuntimeTelemetry` has a production wiring for the first time.
`agent_shared/pipeline.py` took THEIRS as base (their 341-line delta is the turn telemetry) with our
`failure_fields(exc)` restored at the execute-failed site plus the import theirs lacked.
`chat_management.py` and `user_feedback.py` took OURS at every hunk — theirs is weaker throughout AND
leaks user content twice, into the client's 500 detail and over the SSE error frame.
`improvement/scheduler.py` took OURS (its messages are asserted verbatim by an ours-only test) with
their `operation_outcome` dimensions grafted in. `poetry.lock` was relocked, never hand-merged: 0
packages removed, 12 added, 1 version move.

**Three rulings were reversed by SILENT merges** — no conflict, no marker, no failing test, which is
§2.2a's whole thesis firing:
- `datasources.yml` lost `flynapse-postgres` and GAINED `deleteDatasources` (M-GRAFANA forbids both);
- `llm-agents.json` lost both exact-spend panels and moved five queries to the Counter spelling;
- `oss-profile.md` lost the readonly-role rotation row, the board pointer and the "expectedly
  unhealthy" note that stops an operator filing a false bug.
All three are Phase E fixes. §2.2a also guessed that `oss-profile.md` would delete the exact-spend
SECTION; it did not — the heading and the §6.6 companion paragraph survive verbatim. The guess was
wrong in the specific and right in the general.

**Two defects the MERGE created**, neither side's decision:
- `main.py` — their R22 sweep deleted `import traceback` while ours added the only remaining caller,
  so the shutdown drain carried an undefined name. A save drain that failed at exit would have
  raised NameError out of the lifespan. `py_compile` passes; only pyflakes sees it. Fixed as
  `**failure_fields(exc)`, NOT by restoring the import — `format_exc()` ends in a `Type: message`
  line, so restoring it re-introduces the leak the sweep existed to remove.
- The drain also landed OUTSIDE their new `mro.lifecycle.shutdown` span, so a failed drain never
  marked the span and "MRO shutdown completed" was written BEFORE the saves were drained.

**A defect their branch shipped**, found by our tests, not by reading: `forecast.py`'s privacy fix
replaced `forecast=result.forecast` with `forecast_points=len(result.forecast or [])`. That value is
a SCALAR — the same function unpacks it as `low, high = (rng + [result.forecast, result.forecast])[:2]`
— so `len()` raised on every successful forecast and the tool returned `forecast_error`. A privacy fix
that turned a working tool off.

**M-CAPTURE was FALSE on the merged tree.** Capture defaulted off *and* a validator hard-coerced the
opt-in shut; composed with B1's core column (default true, opt-OUT), a stock deployment retained tool
I/O NOWHERE. So M-TOOLIO-2's "capture becomes the single store" had been accepted against a store that
never ran. D.4 flips the default, deletes the `require_tenant_opt_in` shim and its argument (one legal
value is not a setting, and a name that reads as a bypass invites being used as one), D.5 hoists the
tenant read above the accumulator so an opted-out tenant's content is never materialised, and D.6 moves
capture off the request path into a held, bounded, drained task registry.

**D.12 confirmed and closed.** `get_runtime_telemetry`'s `try/except` gated nothing:
`from_current_provider` calls the OTel API's `get_tracer`/`get_meter`, neither of which raises without
an SDK, so the facade was always constructible and the function never returned None in its life.
`suppress_legacy_agent_sdk_spans` was therefore unconditionally true — a process with no collector lost
its legacy span and emitted nothing in its place. Gated on the bootstrap state instead.

**M-TOKENUSAGE landed for the EMITTER only.** Counter → Histogram at both constructors and the record
site, with the semconv bucket ladder, because the SDK default tops out at 10,000 — below an ordinary
prompt — and a histogram with the wrong buckets is as unreadable as a Counter with the wrong name. The
`_total` spellings in `llm-agents.json`, `CATALOGUE.md` and `iac/dashboards/llm-agents.json.tftpl` are
deliberately untouched: Phase E rewrites those same files for M-GRAFANA, and editing them twice invites
one pass being lost.

**The D.2 repoint was a silent blindness, not a documentation chore.** The harness join reads its
availability off `settings.tool_io_archive_enabled`, whose default their branch flipped — so every
argument-level check across four E2E suites degraded to SKIP. 44 tests against a zero baseline, and a
harness reporting SKIP looks like a harness with nothing to say. Also corrected: nothing ever READ the
archive from code; `dump_debug` is a sibling sink, so the repoint is "the documented surface points at
a store with no writer", not "swap a reader".

**D.10.** The read DAO failed OPEN for the caller it knew least about — no identity and no capability
returned NO predicate, while an identity without a capability correctly returned `AND FALSE`.

**Guards fixed, not just used.** Their ordinary-log privacy guard flagged 15 sites that were the
estate's own R22 form (`**failure_fields(exc)` names `exc`, which is in its content list) and could not
see through ANY `**` splat — 24 log calls in the retrieval and synthesis tools splat a dict it never
inspected. It now resolves a splat three ways, including one hop through a parameter to its call sites.

**Everything was mutation-proven, and two guards were inert on the first try:**
- my own D.5 assertion `"llm_content_capture_enabled" in source` is satisfied by
  `settings.llm_content_capture_enabled`, the DEPLOYMENT switch in the same function, so deleting the
  per-tenant read entirely still passed;
- the privacy guard's content-name list knew `query` but not `queries`, so a planted
  `"first_query": queries[0]` went through untouched.

#### D.13 — the gate, measured

Per-directory lanes over both trees, set-differenced on failing IDs (§2.4). Final state after the
phase's fixes:

**CORRECTED 2026-09-20.** The first reading of this table said 2 new ids. It was taken while
`tests/unit` — the largest directory, 22 minutes — was still running on BOTH trees, and the number
was reported before the lane that produced it had finished. The completed count is **20**.

| | |
|---|---|
| pre-merge failing ids | 32 |
| merged failing ids | 41 |
| **new on the merged tree** | **20** |

Of the 20: **4 were real defects**, all fixed in-phase; 2 are Phase E work (E.0a, E.0d); 2 are the
owner-blocked branch-hygiene guard; 1 is an ERROR id the FAILED-only filter never counted; and the
remaining **10 were import pollution from ONE merge-added file** —
`tests/unit/observability/test_nonagent_lifecycle_spans.py` did `import copilot_mro.app.main` at
module scope, which runs during COLLECTION and lands the real `copilot_mro.app.services.*` packages
in `sys.modules`, so every test that loads its subject by path binds the real module instead of its
fake. Fixed (`6dc3160e`): `main` is a fixture. Found in 19 s rather than 22 minutes by collecting all
of `tests/unit` and RUNNING only the ten — and the fact that deselecting every test in the offending
file still broke them is what proved it was import-time rather than state.

**All 20 are now accounted for; only the 2 Phase E items and the 2 owner-blocked ones remain open.**

The four real ones, none visible to any targeted run this phase made:
- the tenancy route sweep did not list the 12th router their merge mounts (`e3e31e14`);
- D.11's `reason` -> `reason_code` rename reached an assertion in a file named for stream
  persistence rather than block saves (`e3e31e14`);
- `_error_kinds` passed a whole error entry through when it carried no colon (`e09f7ac0`);
- flightops lost `_log_detail` at three sites (`e09f7ac0`).

**Two lane rules, both learned by getting it wrong here:** never read a set difference before every
directory has finished on both trees, and filter for `^ERROR <path>::` as well as `^FAILED` — an
ERROR id is a failing id, and a loguru `ERROR` log line is not.

**A lane rule learned the hard way: never run two per-directory lanes concurrently against the
same test database.** Both lanes hit `copilot_mro_test`, and the DB-backed directories reported 34
errors on one tree and 15 on the other — `tests/db/tenancy/test_writer_paths_land_tenanted_rows.py`
passes 19/19 run on its own. The errors were contention, and the set difference over them was
meaningless; five ids read as "fixed by the merge" that nothing had fixed. Re-run DB-backed
directories serially, or give each lane its own database.

### Phase E — copilot-mro deployment half, 2026-09-20, DONE (worktree `copilot-mro-obsm`)

Commits `2e965ea0`, `2e4bbeb8`, `0d0b752d`, `1eec7c49`, `438c6a5d`, plus `35c7e87` on a NEW
`obs-merge` branch in the **iac** repo (that repo had no branch for this work; `main` is untouched).

**The gate, re-measured after the review response.** `tests/integration/otel` went **135 collected
/ 111 passed / 24 skipped** (pre-merge baseline at `417df303`) → **156 / 130 / 26** on the merged
tree with Phase E applied, 0 failed. Collected and passed both rose, so §2.4's gate holds. With
`OTEL_RULES_CHECK=1` (promtool): 143 passed / 13 skipped. With `OTEL_COMPOSE_SMOKE=1`:
`test_oss_profile_smoke` 8 passed, `test_grafana_provisioning_smoke` 2 passed — the container lanes
this plan had declared not done. The merged tree BEFORE Phase E was 145 / 119 / 25 with one failure,
`test_dark_panel_notes_are_present`, naming 13 panels across three boards, which is E.0d exactly.

Every new skip is named: they are all compose-gated (`OTEL_COMPOSE_SMOKE=1`), and the newest is
`test_prometheus_serves_the_exact_names_the_inventory_computes`, added in the review response.

**A number correction.** An earlier draft of this section recorded the gate as 151/126/25. That was
measured before the E.0e guard and the review-response tests were added, and it was off by one pass
even then — the reviewer measured 152/127/25 against the same tree. The figures above are the
post-response measurement. The §8 rule about never quoting a gate from a partial file has a sibling:
a gate quoted before the phase finished is also a gate quoted early.

**What the plan got wrong, and where the work actually was.**

- **E.0b's `tool_outcome` half was already fixed.** The plan says the B target queries
  `tool_outcome="error"` and the emitter emits `"failure"`. Ours had `"error"`, theirs had
  `"failure"`, and the merge took theirs — correctly. Nothing was owed. What WAS owed is the
  histogram family: the merge rewrote five token-usage sites `_sum` → `_total`, and under
  M-TOKENUSAGE `_total` matches nothing at all.
- **E.2's "memory limiter" claim does not exist.** Not in the merged tree, not in either parent,
  not in any of the colleague's otel commits. The phrase occurs only in this plan. No-op. The
  "outage budget" half was real and is reworded against the `max_elapsed_time: 5m` the fragments set.
- **E.4's conftest was already correct.** It layers the Phoenix overlay between base and smoke
  (`conftest.py:89-91`) and supplies `PHOENIX_API_KEY` (`:32`). The plan calls this "the most
  dangerous auto-merging interaction in this half"; it had already been handled. What IS stale is
  `smoke/docker-compose.smoke.yml`'s own header, which still documents the pre-split two-file
  invocation — run as written, compose refuses the project.
- **M-FRONTEND's "take ours wholesale" was already satisfied.** `frontend.json` is byte-identical to
  `417df303`. And the P0-INERT "exactly three panels" test never reached the merged tree at all —
  it, and two sibling tests that depend on the same constant, exist only on `c2fc8bb1`. The correct
  action was to NOT port them. Only the graft was owed.
- **E.5's "adopt their rewritten agent-rule guard" is superseded by E.0i.** Adopting a guard whose
  known defect is the next plan item is the wrong order. Their two tuples were replaced outright.
  Their browser half never won the merge: ours kept the grouping fix and the sample guards.
- **E.0d's stated contract was imprecise.** It says the test "demands `DARK until ` or a dated
  `LIVE since …`". On the Stream-L half the code demanded the fixed substring `DARK until Stream L`
  with no LIVE alternative at all. The `DARK until `/`LIVE since` pair is the BROWSER half (M9.6).

**The design decision E.0d needed and the plan did not anticipate.** Nine of the thirteen offending
panels are emitted by the merged tree; four are not, for three different reasons. So restoring
`DARK until Stream L` would have been a lie on nine panels, and adopting their "STATIC-MAPPED, live
retrieval pending" would have kept a third vocabulary no test enforced. Neither vocabulary could
express the state the merge created. There are **three** states:

| state | meaning | grammar |
|---|---|---|
| `dark` | nothing emits it | `DARK until <what would arm it>` |
| `wired` | a production call site reaches the recorder; no probe has confirmed retrieval | `WIRED <YYYY-MM-DD>, retrieval unproved: <what emits it>` |
| `live` | a probe saw the data | `LIVE since <probe> (<YYYY-MM-DD>)` |

`DARK until ` and the dated `LIVE since …` are M9.6's, unchanged, so the browser panels keep passing
the contract they always did. `WIRED` is what M9.6 never needed.

**The mechanism, and why it is not a third allow-list.** `tests/integration/otel/_emitted_series.py`
holds ONE inventory; the board lint and the alert lint both classify against it; and
`test_emitted_series_inventory.py` proves it against `agent_shared/telemetry.py` by AST — the
instrument exists in BOTH construction paths, its kind matches its constructor, its unit matches
(the unit is part of the exported NAME: `s` → `_seconds`), it is handed to `_safe_add`/`_safe_record`,
and its public recorder has a production call site **exactly when** the inventory says the series is
not dark. That last limb is the only thing that separates `agent.subagent.*` from the rest: those
instruments are declared, AND recorded inside the facade, and `record_subagent` has no caller
anywhere — so a reader who greps for the instrument name concludes the opposite of the truth.

E.0i closes generically as a side effect: a panel or rule naming a series the inventory has never
heard of now FAILS. The old tuples named four series between them, so a rule on any fifth was
checked by nothing — the allow-list *was* the hole.

**Mutation proofs (§2.3a) — twelve, each caught by the right test.** Counter/Histogram flip in one
construction path and in both; a new instrument nobody inventoried; `record_subagent` wired, making
a dark series live; a WIRED panel described as DARK; the `_total` regression put back; a panel on an
uninventoried series; a DARK rule described as WIRED; the datasource entry deleted; `deleteDatasources`
re-added; the exact-spend panels deleted again; and — against the real pinned image — a
`compaction.directory` on the read-only mount, where `validate` answers **ok** and the start fails
with `failed to build extensions … mkdir …: read-only file system`. That last one is the
P0-COLLECTOR signature, and only the new start pass sees it.

**E.9, the half nobody had ever run.** `validate.sh` now STARTS each profile on the pinned image and
polls `health_check`, in both compositions, with the queue directory bind-mounted so the run also
proves `create_directory: true` creates the COMPACTION directory (a README claim nothing checked).
Result after the review response: **9 validates and 18 container starts** — 4 profiles × 2
compositions = 8 validates, × **2 start modes** = 16 starts, plus the aws+phoenix composition's
own 1 validate + 2 starts. All 18 healthy, and all
creating both storage directories where the mounted mode checks. The first run of the New Relic
overlay and of all four durability fragments. A ninth composition was added: **aws+phoenix**,
which `iac/demo_ec2_setup.sh` layers on the demo box and which `validate.sh` never built, because it
appends the fragment only for profiles whose own env example sets `PHOENIX_ENDPOINT` and
`env/aws.env.example` names no `PHOENIX_*` at all. It loads and starts; it was unproven, not broken.

**Found in Phase E, not named by the plan.**

1. `test_compose_port_bindings.py` carried the SAME stale four-file tuple as
   `test_compose_image_pins.py`. Both widened; Phoenix publishes loopback-only in both overlays.
2. The shipped default is a durable-looking queue on a RAM disk: every stack tmpfs-mounts `/tmp`
   and every env example pins `OTEL_FILE_STORAGE_DIR` inside it. Documented (E.3), and the doc names
   the guard that blocks fixing it in the four in-repo composes (`test_collector_profiles.py`
   forbids a collector volume naming `otelcol-storage` there) — a production compose is a NEW file.
3. The README implied backend overlays need not name the storage extension; every one of them does,
   which is why it starts on every profile and why `otelcol validate` cannot see P0-COLLECTOR.
4. `CATALOGUE.md` carried a third, orphaned vocabulary — `DARK-L` — in the alarm table, whose
   defining bullet the merge had deleted; and a stale "fn-frontend three-panel layout" paragraph
   that contradicted §5. Both retired.
5. Fourteen `aws` selectors in OUR §7/§8/alarm sections still mixed a dotted OTLP name in plain
   quotes with a Prometheus suffix. CloudWatch keeps the dotted name and appends nothing, so not one
   of them resolved. All fourteen normalised (E.7).
6. `tests/unit/observability/test_phase1c_nonagent_scope_guard.py` names four paths that do not
   exist (`docker-compose.phoenix-smoke.yml`, `oss-phoenix.env.example`, `*-production.env.example`,
   `production-queue-*.yaml` — the real files are `durability-production-*.yaml`) and its two tests
   are RED on the merged tree. It is a branch-diff guard scoped to the colleague's branch, now
   pointed at our whole merged tree. **This is the file whose deletion the auto-mode classifier
   refused as a "Security Test Removal" — still owner-owed, and still red.**

#### Phase E adversarial review — findings taken, 2026-09-20

An independent Opus reviewer re-ran every lane (including both container-gated smokes), ran
`validate.sh` against the real image, and mutation-tested the new guards in a throwaway `git
archive` copy. Thirteen CONFIRMED findings. Eleven were fixed in this phase; two are recorded below.
It found nothing in M-GRAFANA's restoration, the Slowest Pages graft, the in-repo M-TOKENUSAGE
sweep, E.0h, E.1, or collateral damage — and it independently verified all four "stale plan item"
claims and ran the container lanes this plan had declared not done (7 + 2 passed, no leftovers).

**The severe one, and it was mine.** `validate.sh`'s start pass passed `-e OTEL_FILE_STORAGE_DIR=…`
on top of `--env-file`, so it never exercised the value every `env/*.env.example` pins
(`/tmp/otelcol-storage`) — *the exact variable whose value caused P0-COLLECTOR*. The check written
to prove P0-COLLECTOR could not have seen P0-COLLECTOR. There are two start passes now: **shipped**
(`--tmpfs /tmp:mode=1777`, nothing else overridden — the shape every compose stack provides) and
**mounted** (bind-mounted dirs, which is the only way to prove the compaction directory is created).
Mutation-proved: drop the tmpfs from the shipped pass and it fails with
`failed to build extensions … mkdir /tmp: permission denied`. 18 healthy starts across the four
profiles and the aws+phoenix composition.

**The inventory was half derived.** `SPAN_SIGNALS` had no mechanical backing at all — deleting
`span.set_attribute("agent.outcome", outcome)`, the selector the "Failed agent turns" panel depends
on, left every lane green. And `_call_sites()` was a *substring* grep, so
`# TODO: re-enable telemetry.record_turn` satisfied the reachability limb that the whole WIRED claim
rests on. Both fixed: span attribute keys, span-name prefixes and `attributes=` dict keys are now
read from the package AST, and call sites are AST `Attribute` nodes rather than text.

**`KNOWN_LABELS` was an unguarded third allow-list** — exactly what E.0i abolished. One line added
there disarmed the lint for any series, and nothing checked it. It cannot now shadow an inventoried
signal.

**Label VALUES were outside the inventory's reach**, so `tool_outcome="error"` — the defect that
shipped once — could be reintroduced green. There is a check against the dispatcher's own
`Literal["success", "failure"]` annotation, read by AST rather than copied.

**A mixed-state panel was unsatisfiable**: any other state's grammar in a description was an
offence, so a panel reading one wired and one dark series had no legal description and the only
exit was the escape hatch above. Fixed — every state the query touches needs its note; a note for a
state it does not touch is the offence.

**Four more:** the `meter` construction path's `unit=` was never compared (the unit is part of the
exported NAME); the runbook `alerts.md` still carried both retired vocabularies at the on-call
surface, which E.8 missed; `iac`'s `alarms.tf` and `agent-turn-explorer.json.tftpl` kept both the
`_total`-on-a-dotted-name dialect and "DARK until Stream L" — and the reviewer was right that the
scope line was drawn inconsistently, since §4b-corrections pulled the sibling template in with an
argument that covers these identically; and "DARK" meant two things at once, so the grafted Slowest
Pages panel now reads WIRED and the browser state note accepts all three states.

**One check I wrote was inert, and only a mutation showed it.** The "the prose must vouch for a
signal the query actually reads" check sat behind an early return that fired precisely in the
repointed-panel case it existed to catch. This is the third time in this plan that a guard passed
on first write and failed its own mutation; the rule in §8 holds.

**Both lint bodies are one body now.** `signal_state_offenders()` in `_emitted_series.py` — the
board lint and the alert lint call it. They were two copies for one review round, which is the
shape §8's "a guard with two bodies is a guard with none" lesson names.

#### Phase E — recorded, not fixed

- **The lint's scope is three metric prefixes.** `FAMILY_TOKEN` matches `agent_`, `gen_ai_` and
  `claude_code_`, so repointing a panel at a name outside them (the reviewer used
  `llm_model_calls_total`, which is a real table in this product) is not caught as an unknown
  series. Partially mitigated: the prose check now fails a panel whose description names an
  inventory series while its query reads none. The complete solution is an inventory of EVERY
  metric family the boards may name — `otelcol_*`, `loki_*`, `tempo_*`, `prometheus_*`,
  `traces_spanmetrics_*`, `telegram_*`, `optimizer_*`, `http_*` — most of which are third-party
  self-telemetry whose names this repo does not own and cannot derive. That is a different contract
  (pin third-party spellings against a live scrape) and belongs with the B1a/B1b re-verification
  work, not here.
- **`validate.sh` leaks a temp directory on the success path.** Once the durability fragment is
  layered the collector writes queue files as uid 10001 into 0700 subdirectories the runner cannot
  unlink, so `/tmp/tmp.*/queue` accumulates. Cleanup is best-effort by design and prints a note.
  Removing it properly needs a second image with a shell, which is a dependency the pinned-image
  script deliberately does not have.
- **PLAUSIBLE, not reproduced:** `up_down_counter` instruments are invisible to the AST scan
  (`registry.py` exports one; `_declarations()` matches counter/histogram only). The failure mode is
  loud — a panel on such a series reports as unknown — so it is a gap, not a hole. And `docker port`
  is queried once in `start_check`; an empty answer at that instant burns the deadline and reports
  `state: timeout`, which reads as a config failure. A flake, never a false pass.

### Phase E — not done, and why

- ~~**The `oss_profile_smoke` container lane** (`OTEL_COMPOSE_SMOKE=1`, 8 tests) was not run to
  completion here.~~ **Stale — struck 2026-09-20.** It contradicted this file's own gate paragraph
  two sections up: `test_oss_profile_smoke` **8 passed** and `test_grafana_provisioning_smoke`
  **2 passed**, both run explicitly under `OTEL_COMPOSE_SMOKE=1`, and the adversarial reviewer
  re-ran both independently. Nothing is owed here.
- **`iac` is on a branch, unpushed, and holds two commits** — `35c7e87` and `3068b47`, not the one
  this line first claimed. `cloudwatch_dashboards.tf` and
  `alarms.tf` carry the aws dialect of everything renamed here; only `llm-agents.json.tftpl` was in
  M-SCOPE. The rest of the aws parity is the deferred follow-up §5 already names.
- **`gen_ai.client.operation.duration` is emitted and charted by nothing.** Inventoried, noted in
  the catalogue's signals list, no panel authored. Phase G if the owner wants one.

### Phase D — not done, and why

- **D.7's third clause is BLOCKED.** `tests/unit/observability/test_phase1c_nonagent_scope_guard.py`
  must be deleted and the deletion was refused as a security-test removal — the right automated rule
  and the wrong outcome here, so it is the owner's call. It is a branch-scoped CHANGE-CONTROL guard: it
  diffs against four hard-coded SHAs and asserts the changed production paths are a subset of one
  branch review's agreed scope, disarming itself when the branch is named `obs-telemetry-merge`. Ours
  is `obs-merge`, so it is ARMED and fails naming ~100 legitimately-changed paths. It cannot be
  repaired into something meaningful: widening the allow-list makes it assert that the files that
  changed are the files that changed, and always-skipping makes it inert, which §2.3a rates worse than
  absent. A branch-name check is also decoy-defeatable — renaming the branch disarms it.
- **D.9 is deferred to Phase E/G by its own terms.** "Either wire the dashboard card to it or hold it
  — no speculative backend ahead of a consumer." The read API exists and is RBAC-correct (D.10 closed
  the one real defect in it); the dashboard consumer is Phase B2's question, so the wire-or-hold
  decision belongs where the consumer is.
- **E.1 was pulled FORWARD into D**, out of phase order: the restored M-PINS guard fails while the
  floating tag is in the tree, and the M-ACCEPT suite would otherwise be collected by D's own lane.

### Phase F — the reconciliation against the original rebuild plan, 2026-09-20

F's last act was to walk the master plan's own checkboxes against the merged tree, because a plan that records
work as open after it has landed is a plan nobody can resume from. **181 open checkboxes**, dispositioned:
**119 DONE-UNTICKED** (the work exists in the tree; the box was never ticked), **41 already covered** by a live
plan item here, **18 owed-and-uncovered**, **2 superseded**, **1 unresolved**.

The 18 fall into four groups, and each one is a hole rather than a backlog item:

1. **Phase 11.6's cross-phase acceptance matrix — 16 boxes, and it is the designated close-out gate for the
   whole rebuild.** Tenant isolation, the dashboard-profile matrix, runtime parity, the Docker resource budget
   and the destination swap, each closable only on runtime evidence. **No live plan owns it** — not this one,
   which stops at the merge, and not the phase plans, which are each scoped to their own slice. Two of its
   checks are additionally blocked on a fixture grant (`permission denied for table tenants` on the
   product-event replay lane, and the same blocker on the facts-backfill lane).
2. **The Azure production-support go/no-go.** The master plan carried it as settled — "Azure is marked
   production `NO-GO`". **No `NO-GO` marker exists anywhere in the merged tree.** What exists is
   `deployment/otel/README.md` recording `backend-azure.yaml` as "authored + validated, not deployed", which is
   a BUILD status, not a support ruling. Corrected in the master plan; the gate itself is still owed.
3. **Phase 6 never received its independent adversarial review.** Six Grafana boards, 15 alert rules, six
   CloudWatch bodies and three runbooks closed without one, because that implementer's session brief forbade
   spawning subagents — recorded honestly in its own T13 checkbox, and never picked up since. Master §12 states
   that every phase closes with an independent adversarial review, so this is the estate's largest single
   unreviewed surface, and it is the one that decides what every operator sees.
4. **`copilot-mro/.env.sample:11` still declares the legacy `OTEL_ENDPOINT`** — dead since A14 retired the
   `utils.config` indirection; nothing reads `settings.otel_endpoint` anywhere in the estate. (Line 12's
   `OTEL_SERVICE_NAME` is **not** dead: it is read at boot and by every `get_tracing_service` call site, so
   only the one line is owed here.)

**And 16 further pieces of owed work exist in the tree with no checkbox anywhere.** That is the finding worth
keeping, because it is structural rather than clerical: **a deferral recorded only as prose in a phase note is
a sentence someone has to re-read, not tracked work.** Every one of the 16 was written down honestly, in the
right file, by an agent doing the right thing — and none of them can be counted, sequenced or resumed, because
a paragraph has no state. The full list is in the SDD ledger.

**A path drift found in the same pass.** Master 6.5 places the runbooks at `docs/runbooks/observability/`.
They are at **`copilot-mro/docs/runbooks/observability/`** — there is no `runbooks/` directory in this repo at
all. Anyone following the master plan to the on-call surface finds nothing.

### Environment rules confirmed this phase
- **Worktree lanes MUST set `PYTHONPATH`, or they test the wrong tree (found 2026-09-20).** The shared `api`
  Poetry env installs `core`, `utils`, `copilot-mro`, `flynapse-otel` and `shift-optimizer` as develop/path
  dependencies, and the `.pth` files name the **main checkouts** absolutely. So
  `poetry run pytest ../utils-obsm/tests` collects the worktree's *tests* and imports the **pre-merge**
  package — a green lane that proves nothing about the merge. Verified both directions:
  `PYTHONPATH=/home/aditya/Code/<repo>-obsm` wins over the `.pth` entry (`utils.__file__` moves to the
  worktree). Every merge-phase lane therefore runs as
  `cd api && DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=/home/aditya/Code/<repo>-obsm poetry run
  pytest -q /home/aditya/Code/<repo>-obsm/tests/...`, and each phase asserts the resolved module path once
  before trusting its numbers. copilot-mro's dynamic-loader tests are path-addressed and already correct;
  everything that imports a package normally is not.
- The otel non-container lane: `DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest -q
  ../copilot-mro/tests/integration/otel` from `/home/aditya/Code/api`. **135 collected, 111 passed, 24 skipped,
  ~5 s** on `langgraph-merge` `417df303`.
- Container lanes need `OTEL_COMPOSE_SMOKE=1` / `OTEL_RULES_CHECK=1`; without them the smokes are **collected
  and reported SKIPPED**, so a "no failures" reading is reading a skip. Treat a skip there as a failure.
- `otelcol validate` does not build extensions. A real container start is the only proof a profile loads.

---

### DB step — 2026-09-20, COMPLETE against the dev database `copilot_mro`

Run after Phase E, with `PYTHONPATH` naming the three merged worktrees. A schema-only `pg_dump` was
taken before anything; the migration took its own full data+schema snapshot before writing.

**Acceptance, proved by query with a negative control each** — the identical query returned NULL or
`(0 rows)` before the run:

| object | state after |
|---|---|
| `llm_turn_content` | present, RLS **enabled and forced**, `llm_turn_content_isolation` policy, 0 rows |
| `dashboard_profiles` | present, RLS enabled and forced, isolation policy |
| `product_events.schema_version` | `integer NOT NULL DEFAULT 1` |
| `tenants.llm_content_capture_enabled` | `boolean NOT NULL DEFAULT true` |

Applied `1487 statements, committed` — the same count as the rehearsal. The pre→post schema diff is
100% additive (106 added lines, no real removals; public tables 111 → 113), `backfill: 0 rows`, and
the statement audit contains no `DROP TABLE`, `TRUNCATE`, `DELETE FROM` or `DROP COLUMN`.

**`--verify-only` is not an acceptance signal for a missing object, and now we know why.** It reports
"schema properties hold (0 statements)" on a database missing all four of the above, because it calls
`verify()` and returns 57 lines before `create_missing_tables()` ever runs. It sees the absences only
in passive counts (109 relations against 114 declared; one index, two NOT NULLs and two column types
"declared but not present"). Acceptance is proved by query, not by exit code.

**The RLS pass was load-bearing.** `provision_rls.py --verify-only`, run straight after the
migration, FAILED rc=1: `flynapse_app holds UPDATE, DELETE on llm_turn_content, which is
append-only.` This is the `ALTER DEFAULT PRIVILEGES` hazard its own docstring names — defaults from an
earlier run granted the application role full DML on a table the instant the migration created it.
Skipping the RLS step as a formality would have shipped the tenant-content audit table writable and
erasable by the application role. The apply run revoked it; `has_table_privilege` now reads
`SELECT t | INSERT t | UPDATE f | DELETE f | TRUNCATE f`. Both re-verifies are clean.

**Tenant isolation proved behaviourally, not just in the catalogue.** `chunks` holds 475,277 rows
across two tenants; as `flynapse_app` bound to tenant A, exactly A's 165,413 are visible and B's
309,864 are denied.

**M-CAPTURE landed on data here.** `ADD COLUMN ... DEFAULT true NOT NULL` backfilled all six existing
tenant rows to `true`, so capture is ON for every tenant from this run. The store exists, is
enforced, and is empty — which is what makes the retention ruling (90 days, M-PURGE) live work rather
than a hypothetical.

**Carried forward:** `data_discovery_jobs` has three columns nullable against a NOT NULL declaration.
Genuinely pre-existing and structurally unconvergeable by this script, since `add_columns` skips an
existing column so `enforce_not_null` never sees it. Needs a manual `SET NOT NULL` once the columns
hold no NULLs.

**A correction to the spec this step ran under.** It told the executor to record the `product_events`
CHECK mismatch as pre-existing and not ours. It was ours — `product_events_schema_version_check`, the
named CHECK on this plan's own new column, reported only because the column was absent. Findings went
2 before → 1 after. **Do not pre-dispose a finding in a spec; state it as a question for the executor
to resolve.**

## 8. Lessons

**Review their branch before merging it, not phase by phase afterwards (2026-09-19).** The first draft of this
plan opened with merge preparation and put an adversarial review at the end of each merge phase. The owner
corrected it: the starting point is a standalone review of the colleague's work, before any merge. A
merge-lens review conflates two questions — "is this correct" and "does this collide" — and systematically
under-covers whatever touches nothing of ours, which here is the largest and riskiest part of their work
(content capture, the Phoenix eval suite, their test suite's own integrity). Merging first also means a defect
is discovered inside our history instead of in theirs, where rejecting it is still cheap. **Rule: when
integrating someone else's branch, review it as its own body of work first, and let the merge execute
verdicts rather than discover them.**

**A plan item written before the work existed may be obsolete rather than pending (2026-09-19).** Phase 3.3
(LangGraph genai instrumentation) was reported as a gap because no phase had implemented it. The owner asked
why it was needed given the runtime telemetry the colleague had wired — and the honest answer is that it
largely is not: the item was specified when nothing was instrumented, and our own gateway now covers the model
calls it would have caught, so installing it would double-count exactly as the spec's botocore ban predicts.
**Rule: before reporting an unimplemented plan item as owed, check whether later work made it redundant. "No
one built it" is not the same as "it is still needed."**

**Audit what only ONE side changed, too (2026-09-20).** §2.2a's silent-merge register was built
from the intersection — files both sides touched — because that is where decisions collide. But a
theirs-only edit to a file whose guard is ours merges with no conflict and no marker either, and
there are three times as many of them. `flightops_brief.py` lost `_log_detail` at three sites that
way, and our own test had predicted that exact regression in its docstring. **Rule: the register
covers every file the incoming branch changed, partitioned into "both sides" and "theirs only" —
the second set is audited for what OUR guards and OUR sanitisers expect of it, not for collisions.**

**Never read a set difference before the lane finishes (2026-09-20).** I reported the D.13 gate at
2 new ids while `tests/unit` — 22 minutes, the largest directory — was still running on both trees.
The real number was 20, and three were real defects. The same reading also filtered `^FAILED` only,
so an ERROR id went uncounted, while `^ERROR` on its own matched loguru log lines and produced a
contention story that was half wrong. **Rule: wait for the sentinel the script writes, count
`^FAILED` and `^ERROR <path>::` together, and never quote a gate from a partial file.**

**A guard with two bodies is a guard with none (2026-09-20).** The ordinary-log privacy guard
had a file-walking implementation and a tree-walking copy, and the file's own self-tests called
the copy. They drifted: D.8's splat resolution landed in one of them, so the tests that prove
that guard works were exercising code that guarded nothing, and an adversarial probe measured
the copy and reported a hole the real path had already closed. Both directions of the same
error, in one file. **Rule: a guard has exactly one body. If a test needs to drive it over
synthetic source, the file-walking entry point becomes a wrapper over the tree-walking one —
never a second implementation that happens to agree today.**

**A green lane after a merge measures the tests, not the merge (2026-09-20).** Phase D's three
worst findings were all invisible to the suite. `main.py` carried an undefined name that only
pyflakes sees and `py_compile` accepts. `forecast.py` called `len()` on a scalar, so every successful
forecast returned an error — caught only because an unrelated directory's tests were run. And the E2E
harness's argument-level checks all degraded to SKIP, which reads as "nothing to say" rather than as
failure. **Rule: after a merge, run a linter over the merged tree and diff its output against the
pre-merge tree, run every directory rather than the ones you touched, and treat a jump in SKIPs as a
failure signal, not a quiet lane.**

**An assertion that names a constant can be satisfied by a different constant (2026-09-20).** Two
guards written in this phase were inert on the first try for the same reason. My D.5 test asserted
`"llm_content_capture_enabled" in source` — satisfied by `settings.llm_content_capture_enabled`, the
DEPLOYMENT switch, which lives in the same function, so deleting the per-tenant read entirely still
passed. Their privacy guard's content-name list held `query` but not `queries`, so a planted
`queries[0]` went straight through. **Rule: assert the thing that can only be true one way — an
import line, a call, a type — not a substring that a sibling name also satisfies. And mutate every
guard you write, including the ones you wrote to catch someone else's mistake.**

**"Base of record is ours" is a rule about hunks, not about files (2026-09-20).** Taking ours for the
conflicted hunks of `user_feedback.py` left `failure_fields(e)` against an `except ... as exc` that
their side had renamed in a NON-conflicted region three lines up. Git resolved the file; the file did
not work. **Rule: after every "take ours" on a file the other side also edited, run a linter over that
file specifically — the failure is a name, and names are exactly what a textual merge cannot see.**

**A plan item can be stale in the direction of MORE work, not just less (2026-09-20).** Four Phase E
items described work that was already done or had never existed: the `tool_outcome` fix (the merge
took theirs, correctly), the otel conftest (already layering the overlay and supplying the key), the
frontend board (byte-identical to ours), and a "memory limiter" claim present in no tree at all. The
existing rule says to check whether later work made an item redundant. This is the mirror: an item
written from a REVIEW of someone else's branch describes that branch, and the merge may already have
resolved it in our favour. **Rule: before executing a plan item that describes a defect, reproduce
the defect on the tree you are about to edit. "The plan says it is broken" is a hypothesis.**

**When two plan items disagree, execute the later one (2026-09-20).** E.5 said to adopt their
rewritten agent-rule guard; E.0i said that guard is an allow-list with a generic hole. Adopting it
first and fixing it second would have produced one commit that installs a known defect and another
that removes it. **Rule: read the whole phase before starting it, and when a later item names the
defect in what an earlier item tells you to adopt, skip the adoption.**

**A vocabulary argument is usually a missing state (2026-09-20).** Ours said DARK, theirs said
"STATIC-MAPPED, live retrieval pending", and the merge left the guard from one side over the
descriptions from the other. Both sides were right about different things: the emitter IS real and
retrieval IS unproven. Picking a winner would have shipped a lie either way. **Rule: when two sides
have incompatible wording for the same fact, check whether they are describing two different states
that one vocabulary cannot hold — and if so, add the state rather than choosing a side.**

**Verify on the real input, not on a convenient one (2026-09-20).** `validate.sh`'s start pass
overrode `OTEL_FILE_STORAGE_DIR` with a bind-mounted path so the test could inspect the directories
from the host. That override silently replaced the one variable whose real value — the
`/tmp/otelcol-storage` every env example pins — caused P0-COLLECTOR, so the check built to prove
P0-COLLECTOR ran on inputs where P0-COLLECTOR cannot occur. The convenience that made the assertion
easy is what removed its subject. **Rule: when a check needs to alter its input to make an
assertion possible, keep a second pass on the unaltered input, and make the unaltered pass the one
that must hold.**

**Half a guard is the half nobody adversarially read (2026-09-20).** The emitted-series inventory
was proved against the emitter by AST for its metrics and not at all for its spans, and its
reachability limb — the sentence the whole design rests on — was a *substring* grep, so
`# TODO: re-enable telemetry.record_turn` satisfied it. Both halves were written in the same sitting
by someone who had just argued that hand-maintained lists are the problem. **Rule: after building a
mechanism to replace a hand-maintained list, enumerate every field the mechanism declares and ask of
each one, separately, what proves it. A field nothing checks is the old list wearing the new name.**

**A check that cannot fail is not a check, and `rc=0` is not evidence (2026-09-20).** `otelcol
validate` returns 0 on a config whose collector dies at startup, because it never builds a
component; CI had been green over that for the whole phase-8 work. The proof is not reading the
subcommand's docs — it is mutating the config so the two disagree and watching `validate` say "ok"
while the start says `failed to build extensions`. **Rule: for any verification step, construct the
defect it exists to catch and confirm it fails. If you cannot make it fail, it is not verifying.**

**Never `git checkout --` to undo a mutation test (2026-09-20).** During C1's mutation checks I restored each
mutated file with `git checkout -- <file>`. That restores the **committed** state, so it silently discarded
every *uncommitted* edit in the same file — three source fixes from the review triage vanished, and the only
symptom was five tests failing for reasons that made no sense until `git status` showed the source files
unmodified. CLAUDE.md already forbids the command; this is the failure mode it forbids it for. **Rule: copy
the file to the scratchpad first and restore from the copy. Then `git status` after every mutation round, and
treat "the file I just edited is unmodified" as the alarm it is.**

- **Committed before the independent review, 2026-09-20.** The owner ruled "commit them now" and the
  controller committed five trees on implementer-only claims tables — then launched two adversarial reviewers
  only when the owner asked *"are we doing a review?"*. This plan's own gate says the claims table is emitted
  by a **reviewer, never the implementer**. The reviews found nothing that broke a consumer, and did find a
  live observability defect plus two commits red at their own HEAD. **Rule: an owner's "commit now" releases
  the commit; it does not waive the review. Run the adversarial review first, or at minimum in the same
  breath, and say which order was used.**

- **Took an owner ruling and did not write it down, 2026-09-20.** Four rulings came back from a question
  prompt and were dispatched immediately. A reviewer then found a commit citing "the owner's ruling" with **no
  record anywhere in the plan or any tree** — from the repository alone, a plan-gated decision was
  indistinguishable from an implementer's say-so. **Rule: write the ruling into §4a-bis BEFORE dispatching
  the work it authorises, including the options the owner did NOT select.**

- **Briefed a lane recipe that silently destroys the run, all night, 2026-09-20.** Every brief said *run from
  a neutral cwd* to defeat the sibling-checkout hazard. `utils.config.find_env_file` searches **cwd first**,
  so from `/tmp` the `.env` is never found and 41 api integration tests fail on a password error — which a
  reviewer then reported as an unexplained red lane "equally red pre-merge". **Rule: the fix for one
  resolution hazard can create another. Run from the REPO ROOT with `PYTHONPATH` pinned — cwd for the env
  file, `PYTHONPATH` to beat the venv's `.pth` files — and never generalise a lane recipe across repos
  without one run proving it in each.**

- **Copied an auditor's unverified count into the plan as a finding, 2026-09-21.** R.3's re-derivation
  reported "15 Document Hub families the producer inventory omitted"; the controller wrote G.101 asserting
  R.4 was wrong by fifteen names and dispatched a re-derivation. **That re-derivation refuted G.101**: R.4
  had already found all 14 from code, and R.3's prose said "fifteen" while listing fourteen. **Rule: a
  number from an auditor is a claim until a second derivation agrees. Record it as "reported by", never as a
  finding, and never build a new item on it alone.**

- **Relayed a measurement into another agent's tree without its provenance, 2026-09-20.** The controller
  forwarded "1 failed at HEAD" to an implementer as a live red. It was not — the sweep had read that
  implementer's own working tree mid-edit, and **the receiver proved it because the collected count (1451)
  equalled HEAD's 1435 plus exactly the 16 tests it had just written.** **Rule: when relaying a measurement,
  forward its timestamp and collected count with it, so the receiver can fingerprint what was actually read.**

- **The obvious fix was wrong three times in one night, 2026-09-20.** Switching the WORKOUT logger to loguru
  would have silently un-formatted nine other call sites; writing the server span's exception class to
  `error.type` was silently overwritten by upstream; and `set_status_on_exception=False` alone suppresses the
  status **code**, dropping every failed span out of `status = error` queries. A fourth — a codemod over the
  api log debt — would have turned a confidentiality defect into an availability one. **Each was caught by an
  implementer measuring rather than reasoning. Rule: for any repair that changes what an observability
  signal carries, prove the repaired signal still answers the query it exists for, not merely that the
  defect is gone.**
- **A resumed lane ran a local DB MCP query nobody asked for (2026-09-21).** The core implementer, resumed
  by message for review fixes, ran one read-only count through the local Postgres MCP — which is
  manual-invoke only — and self-reported it. The original brief's ban did not travel with the follow-up
  messages. **Rule: every brief AND every resume message restates the standing bans (local DB MCPs, DDL,
  AWS, destructive git) — a resumed agent's attention is on the new message, not the old brief.**

- **Told the owner "LLM traces DO reach Phoenix" after reading the exporter config but not its defaults,
  2026-09-21.** The first correction ("never started" → "flows") read `content-phoenix.yaml` and stopped.
  The G.3 research then showed the export is **off in every committed config**: `LLM_CONTENT_COPY_SAMPLE_RATE`
  defaults to 0.0 and no deployment sets it or `phoenix_endpoint`. The claim was wrong twice. **Rule: "data
  flows to X" needs three facts — the pipeline exists, the enabling flag's DEFAULT, and every deployment's
  value for it. A config file that could export is not evidence that anything does.**

- **The per-opener sweeps were structurally blind to the worst leak, 2026-09-21.** Every span-side guard
  this project built read OUR `start_as_current_span` calls; the auto-instrumentors (psycopg2, httpx,
  urllib3, redis, ASGI) open spans in library code on SDK defaults, and psycopg2 put **bound values** into
  the exported status description (G.110). The same was true of the log pipe (G.112). Found only because a
  satellite-repo implementer ran a real failing query through the real bootstrap. **Rule: for any "X never
  leaves the process" property, find the ONE seat every instance passes through (the provider's active
  processor, the logger provider) and prove it behaviourally there; call-site sweeps are a second line,
  never the proof.**

- **A guard patched three times, with a P1 in every review round, was a design problem, 2026-09-21.** The
  G.53 checkout pin inferred a checkout's family from its directory NAME; round 1 blessed the pre-merge trees
  for a worktree of a variant, round 2's fix was carried imperfectly, round 3 refused a primary's worktree
  and the override could not rescue it. **Rule: a second P1 in the same mechanism stops the patching — write
  the design (what "right" means, where it is decided once, when to refuse vs warn) before touching code.**

- **Plan boxes went stale again within hours, and an implementer misreported another tree's state,
  2026-09-21.** A spot-check before launching found G.94, G.64 and most of G.48 already done in code; later
  an implementer reported utils' `_root.py` as the old copy when its md5 already matched api's final one.
  **Rule: re-audit open items against code before dispatching builders off the checkbox list, and measure
  any cross-tree claim (md5, `git log`) before routing work on it.**

- **The lane recipe, refined.** `utils.config.find_env_file` checks `ENV_FILE` FIRST, then cwd. So the
  robust recipe is `ENV_FILE=<absolute .env>` plus `PYTHONPATH` pinned to the merged trees, from any cwd;
  a worktree with no `.env` of its own (core-obsm) needs `ENV_FILE` whatever the cwd (its api lane read
  794/2/21 without, 884/0/0 with).

- **Shared scratchpad = shared namespace (2026-09-21).** Briefs pointed every lane at the one session
  scratchpad; two lanes each wrote `mut.sh` with different argument orders, and one ran the other's script,
  which copied a stray file into a live worktree (caught, deleted, md5-verified). **Rule:** every brief names
  a PRIVATE scratch subdirectory (`scratchpad/<lane>/`) and forbids generic script names at the root.

- **Running tallies drift; count the boxes (2026-09-22).** The ledger's hand-maintained "N done · N partly · N
  open" drifted by 3 across ~15 addenda (items added, flipped, merged). **Rule:** at every compaction point,
  derive the totals from the plan's checkboxes with a single count and write that number, not an increment.
- **A review that verifies a "copy this file to N trees" spec must run the copy.** api's carry spec claimed
  per-tree counts measured against stale heads; only a reviewer who applied it to real-git clones of every tree
  found a red test, a missing helper and a defect INSIDE the carried file. **Rule:** a carry spec is accepted
  only after a dry run in clones at the target heads, and the file is fixed before it fans out.
- **"No direct DB queries" must also cover app-driving probes (2026-09-22).** A reviewer's standalone probe script
  drove a TestClient route whose handler read the local test DB through the app's own pool — no MCP, no psql,
  yet a DB touch outside pytest. **Rule:** probes that drive the app stub the DB (or run as pytest tests with the
  suite's fixtures); say so in every brief alongside the MCP ban.
- **"No history rewrites" must name `--amend` and the pipe's exit status (2026-09-22).** The utils lane committed a
  red `62d2cc2` because its `pytest … | tail && git commit` chain tested `tail`'s exit code, then amended the
  commit to fix it — a rewrite the briefs banned only as "rebase/reset". **Rule:** every brief says "never amend;
  fix forward" and "check pytest's own exit status (`set -o pipefail` / `${PIPESTATUS[0]}`)".
- **A decision question the owner cannot parse is a question-writing defect (2026-09-22).** A4 (`data-run-reason`)
  and A5a (`constructor` cell) came back "didn't understand" — both named code artefacts before saying what a
  user sees. **Rule:** open each owner question with the observable effect in plain words (what lands where, who
  sees it), then the options; code names go in the option descriptions only.
- **A commit subject names every plan item whose production code it carries (2026-09-22, copilot-mro P2-6).** `f5b3d580`
  carried the G.5 facts writer and `c401fb18` carried G.6's counter with no caller until `3978073b`, so the
  plan read "not built" for code that had landed. **Rule:** name every carried plan item in the subject; a
  mis-landed piece is recorded in the next commit (fix forward), never by rewriting.
- **A merge commit carries the conflict resolution only (2026-09-22, copilot-mro r6 P3-8).** `75947461` also held a
  detector change and a register edit, which `git log -p` hides by default, so a reader of the history cannot see them.
  **Rule:** resolve and commit the merge; any edit the merge makes necessary lands in its own commit right after.
- **The review packet is updated as each review lands, not at the end (2026-09-22, owner asked a second time).**
  The owner asked for it at CHECKPOINT 11 ("keep creating updating the fable review packets"). After G.5 on
  2026-09-20 no review was filed into `obs-telemetry-merge-review-packet/`, although ~30 review rounds ran since, each
  with a claims table that now lives only in transcripts. Reviewers also drifted to their own "Tier" scale
  (0 = content leak that ships … 3 = docs), which is a SEVERITY scale and inverts §2.3a's tier (0 = settled by a
  mutation-checked guard, never goes to Fable). **Rule:** every reviewer brief tells it to write its claims table to
  a file in the packet directory in §2.3a's columns, with severity as its own column; the controller's "on report"
  step includes updating the packet README totals; and superseded rows are re-stated, never silently left OPEN.
- **An env pin passed to a subprocess is not final when the subprocess re-applies its own settings (2026-09-22, M-CLI-TELEMETRY).**
  The Agent SDK starts the Claude CLI with `{**os.environ, **options.env}`, and the CLI then layers user → project →
  local → flag → policy settings-file `env` blocks on top, so an `options.env` pin alone could be overridden and an
  unset key inherits the parent's value. **Rule:** pin every key explicitly (never rely on "unset"), pass the same dict
  through the highest layer the caller controls (`--settings`), and name the one layer that still outranks it.
- **A linter piped into `tail` has the same exit-status hole as pytest (2026-09-22, utils `ec0629e`).** Three ruff
  warnings shipped because `ruff | tail` reported `tail`'s status. **Rule:** `set -o pipefail` / `PIPESTATUS[0]` for
  every checker whose result gates a commit, not only pytest.
- **A mutation script piped into `head` never restores (2026-09-21, copilot-mro r7b).** `mutn.sh … | head -3` closed the
  pipe on the first traceback; the script's next `echo` took SIGPIPE and died BEFORE its `cp <backup>` restore, leaving
  a mutated CATALOGUE.md in the worktree (caught by the md5 check, restored from the backup, re-verified against the HEAD
  blob). **Rule:** never pipe a script that restores state; read its log file afterwards, and md5 every mutated file
  against the HEAD blob before the next step.
- **A long-lived implementer is slow, and it gets sloppy (2026-09-22, owner).** Sending each new batch to the same
  agent made its whole transcript ride along: runs cost 585k–925k tokens and 40–230 minutes each, and the breaches of
  this stretch (ungated ruff commits, a DB-writing test, a live JWKS fetch) all came from long-running lanes. **The
  owner's main complaint was SPEED.** **Rule:** use a FRESH implementer per batch, briefed from the claims file, the plan
  section, the lane recipe and the tree's HEAD. Resume an old agent only to finish a batch a 429/529 kill interrupted.
  Reviewers were always fresh.
- **Serial reruns were most of the wall-clock (2026-09-22, owner).** Reviewers re-ran full lanes at every commit
  (core r8: 48 lane runs, over an hour) and whole lanes per mutant. **Rule (now in the workspace CLAUDE.md "Test Run
  Speed"):** `pytest -n 4` for non-DB lanes (pytest-xdist in the api venv; core unit 60 s → 26 s); commits side by side
  with `parallel-commits.sh` (workspace root) (4 commits in 52 s vs about 4 min); aimed mutation proofs with
  `mutant.sh` (workspace root) (5 s vs about 60 s per kill). A survivor is confirmed on the full lane before it is
  reported.
- **A red baseline makes every mutant look KILLED (2026-09-22, core r8).** In a symlinked scratch workspace the unit
  lane always exits 1 on two artefact tests, so the reviewer's first six "kills" were that artefact, not the pin.
  **Rule:** a mutation run first runs its command on the unmutated file and refuses a red baseline. `mutant.sh` does this
  (BASELINE-RED, exit 4); on its first trial it caught a mis-set env that would otherwise have counted as a kill.
- **xdist silently drops a session-end exit check (2026-09-22, core r8 P2-5).** A worker's exit status is copied
  before the conftest sentinel runs, so core's tenant-leak check deletes the leak but the run exits 0. **Rule:** a lane
  that writes the shared DB, or whose session-end check sets the exit status, stays serial until that check reports
  through `workeroutput`.
- **`sed -i` replaces a symlink with a regular file (2026-09-22, workspace CLAUDE.md).** `/home/aditya/Code/CLAUDE.md`
  links to `utils/utils/dev/.claude/CLAUDE.md`; an in-place sed edit silently turned the link into a copy, so the
  versioned file never got the change. **Rule:** check `ls -l` before editing any workspace-root file; edit a
  symlink's target or use `sed --follow-symlinks`.
- **An owner interrupt during a launch turn cancels every agent launched in that turn, unrecoverably (2026-09-22).**
  Seven freshly launched lanes died three minutes in and the client refused to resume them. **Rule:** launch, then
  reply; if the owner has instructions mid-launch, they go in the next turn.
- **A machine crash loses in-process agents, never their transcripts; `/tmp` was the real loss (2026-09-22, WSL memory
  spike with ~20 lanes).** Transcripts persist on the home disk and a crashed agent resumes by SendMessage to its id
  (tested); the harness scratchpad under `/tmp` was emptied at boot, taking every extract, census and mutation log.
  Commits per finding made the implementers' recovery cheap (21 commits survived); reviewers, who commit nothing,
  lost ~50 minutes each. **Rules:** record each lane's agent id in the ledger at launch; reviewers file their claims
  table incrementally; durable artefacts go to `~/.claude/scratch/<project>/<lane>/` or a commit; every test run
  goes through `pytest-slot.sh` (machine-wide semaphore + free-RAM gate) so agent count cannot become a memory spike;
  the owner's `/etc/tmpfiles.d/tmp.conf` override (`d`, not `D`) stops the boot purge on this box.
- **The machine is the cap, not the agent count (2026-09-22).** With no cap, 20 Opus lanes each running pytest at
  `-n 4` on a 12-core / 24 GB VM exceeded the host. **Rule:** one pytest process per lane, `-n 2`, the slot
  semaphore, and a load/RAM gate before any full lane; raise parallelism only by measuring `free -g` first.
- **A full pause is cheap when every lane already keeps durable state (2026-09-22, 11 agents).** One PAUSE message per
  agent (finish the tool call → commit only if green → `PAUSED.md` with DONE-by-SHA / IN FLIGHT / REMAINING / RECIPE /
  controller items → hand back) stopped 11 lanes in ~6 minutes with every tree clean and nothing running; two lanes
  turned out to be finished and said so instead. **Rule:** brief the pause protocol at launch, not at pause time; the
  resume is a message to the same id, and the `PAUSED.md` is what a fresh agent gets if the transcript is gone.
- **Never stage per-finding commits from a `-U0` diff (core r8, 2026-09-22).** `git apply --cached --unidiff-zero`
  on zero-context hunks MISPLACED pure-insertion hunks, so five commits are red at their own HEAD although the working
  tree was green; a fix-forward commit restored the measured tree. **Rule:** split with `git add -p` / by file, and
  run the lane at each commit (`parallel-commits.sh`) before calling the split done.
- **When the same guard mechanism has holes found a third round running, stop patching and redesign it to fail
  closed, design section first (2026-09-22).** utils' metric-key inventory had alias/closure/helper decoys found in
  r6, r7 and r8; the r8 batch wrote the design before code (read only positively recognised shapes, report every
  other mention by line, pin what it cannot see as a register mirrored in the docstring) and came back with every
  decoy red and 34/34 mutants killed, with the live estate's view byte-identical. **Rule:** a third-round finding
  against the same reader is briefed as a fail-closed redesign, not a case list (applied to shift SO-11..13 and the
  flynapse-otel ratchet baseline the same day).
- **Cap test-hygiene side work that keeps finding smaller holes (owner, 2026-09-22).** The test network guard entered this plan from one api review finding (a smoke test probing AWS metadata) and grew through three review rounds and a shared port, each round finding narrower bypasses; the owner asked what it had to do with telemetry. **Rule:** when a supporting mechanism (not the deliverable) keeps producing P3-only bypasses, fix its P1/P2s, park the bypasses in Future Improvements with the complete fix, and stop dedicated review rounds — say so to the owner before the second extra round, not after the fourth.
