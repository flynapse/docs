# Observability / telemetry — merge `obs-telemetry-merge` and close the rebuild

**Opened 2026-09-19.** Owner request: assess the colleague's `obs-telemetry-merge` work, merge it, find the
gaps, then finish the gaps plus what is still owed from the observability rebuild plan itself.

Governing documents (do not duplicate them here):
- `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` — the ruled design (rev 4), §11 = the 20 owner rulings.
- `docs/plans/observability-rebuild.md` — master plan + dated ledger (§15) + resume brief (§18).
- `docs/plans/observability-rebuild-phase-{0-2,1,4,5,6,8,9,10}*.md` — per-phase detail, notes, Future Improvements.
- Their plans, on `origin/obs-telemetry-merge` in this repo: `plans/observability-merge-completion.md`,
  `plans/observability-rebuild-phase-8-audit-followups.md`, `plans/observability-rebuild-phase-1c-stable-nonagent.md`,
  `plans/observability-rebuild-research/08-post-migration-rescoping.md`.

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
   own docstring warns that a subset run leaves the rest unmigrated. Four schema changes, not three:
   `product_events.schema_version`, `tenants.llm_content_capture_enabled`, `dashboard_profiles`,
   `llm_turn_content`. **The RLS run is not optional** — without it the tenant-content table exists with no
   row-level security. Acceptance: `llm_turn_content` present with `ENABLE` **and** `FORCE ROW LEVEL SECURITY`.
5. **api** — hard dependency on copilot-mro: `flynapse_api/main.py` top-level imports
   `partition_boot_check_mode`, `PARTITION_REFUSAL_ERROR` and `PARTITION_REFUSAL_REMEDIATION`, none of which
   exist on our copilot-mro mainline. Gate the phase on `import flynapse_api.main`.
6. **dashboard** — hard dependency on core (its product events now post `event_id` and `schema_version`, and
   core `master` sets `extra="forbid"`, so against an unmerged core every event 422s and is silently dropped);
   soft dependency on copilot-mro (the LLM turn summaries card is mounted unconditionally and calls a
   copilot-mro route that exists only on their branch, so merging dashboard early leaves a red error card on
   the improvement page for everyone).
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

### 2.4 Per-repo verification lanes

- **core / copilot-mro / utils / api** — from the shared `api` Poetry env, `DEBUG=false`, and
  `POSTGRES_DB=copilot_mro_test` for DB lanes. Always include `tests/unit/infra` (two-level layout,
  globally-unique basenames, no depth-coupled paths) — their new tests violate the last of these in nine files.
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

### Phase A — Preparation
- [ ] A.1 Commit the six uncommitted observability docs in this repo by named path, including the untracked
      phase-10 plan (the only durable record of 22 tasks and ten Fable gates).
- [ ] A.2 Create the six `obs-merge` worktrees and branches.
- [ ] A.3 Run the tenancy migration against `copilot_mro_test`; confirm the three schema changes.
- [ ] A.4 Record the pre-merge lane numbers for every repo, so a post-merge delta is measurable.

### Phase B — core, then dashboard

**B1 core**
- [ ] B1.1 Merge (clean). Repair our `_Sink` test double for the new `ProductEventInsertResult` return type and
      its `{"accepted": 1}` assertion — without this the merged handler dereferences `None` and 500s.
- [ ] B1.2 Add the missing tenant-admin gate on `GET /analytics/dashboard-profile`; it is the only route on
      that router without one.
- [ ] B1.3 Log the widen-to-all-panels branch in the profile loader, so "no row" and "corrupt row" stop failing
      in opposite directions silently.
- [ ] B1.4 Extract the feature-gate check so the profile resolver and the panel service stop carrying two
      copies of one rule.
- [ ] B1.5 Run the migration, then the analytics/db/api/tenancy/infra lanes.

**B2 dashboard**
- [ ] B2.1 Merge (clean). Guard the UUID mint with the repo's existing idiom and move it inside the never-throw
      region — as merged it violates E9.9b and throws on any non-secure-context origin.
- [ ] B2.2 Apply M-FALLBACK: profile failure degrades to the capability path.
- [ ] B2.3 LLM turn summaries card: typed error message instead of the server's text, a constant-message
      breadcrumb on failure, the response contract instead of a bare cast, and the query layer instead of
      hand-rolled `useState`/`useEffect`. Mis-described docstring corrected — it returns 180-char prompt and
      answer previews, which is not "content-free".
- [ ] B2.4 typecheck → unit → `next lint`, plus the post-merge greps for the optimizer tab, the panel count,
      the E9.9b catch and duplicate object keys.

### Phase C — utils, then api

**C1 utils** (first: the three consumers pass `distribution=`, so utils always leads)
- [ ] C1.1 Merge (clean). Replace the four hand-rolled `error_type=` log kwargs with `failure_fields`; keep the
      semconv `error.type` on the spans.
- [ ] C1.2 Drop the two fabricated exceptions built only so the span helper could read a type name.
- [ ] C1.3 Stop marking a quiet cache miss as span ERROR — its only caller treats misses as normal flow, and it
      would inflate the dependency board's error rate.
- [ ] C1.4 Add the missing no-op-tracer test for the Weaviate wrapper (S3 has one).
- [ ] C1.5 Mirror `WEAVIATE_GRPC_PORT` into every repo that deploys it; make `grpc_secure` follow the URL
      scheme rather than staying hard-coded false.
- [ ] C1.6 Record the connection-factory span as still owed: the spec put the Weaviate wrapper on
      `weaviate_connection()` deliberately, and `hybrid_search` is not the only door.

**C2 api** — **must not merge before copilot-mro**: their `main.py` imports five symbols that exist only on
their copilot-mro branch, so api alone fails at import and the gateway will not boot.
- [ ] C2.1 Take their loguru mechanics on the request-failed line — the bug is real: an already-interpolated
      f-string message plus kwargs makes loguru run `str.format`, so a Pydantic error's braces raise `KeyError`
      *inside* the handler and the request's own exception never reaches the `raise`.
- [ ] C2.2 Combine it with our R22 policy: bind duration and `failure_fields`, constant message, drop the
      now-unused traceback import. Add the assertion their test lacks — that no exception text reaches a sink.
- [ ] C2.3 Apply M-WARN to the partition helper; assign and surface the degraded return value.
- [ ] C2.4 Harden the relaxed boot-check guard so a handler that returns before its `raise` is still caught.
- [ ] C2.5 M-LOCK: take our lock. Gate the merge on an actual `import flynapse_api.main`.

### Phase D — copilot-mro, application half
- [ ] D.1 Resolve the six app-code conflicts. Base of record is **ours** for chat management, user feedback,
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
- [ ] D.2 Re-apply the user-content fixes their conflicts discard (both prompt-logging sites, filename, S3 key).
- [ ] D.3 Repair the shutdown-drain handler the clean auto-merge breaks — their side deletes the traceback
      import, ours calls it. Gate on a pyflakes run.
- [ ] D.4 Apply M-CAPTURE and M-TOOLIO to `config.py` and the policy reader.
- [ ] D.5 Hoist the tenant policy read above the snapshot build, so an opted-out tenant's prompt is never
      materialised and redacted in memory just to be discarded.
- [ ] D.6 Move capture off the request critical path — a shielded task with a bound, as the block save does.
- [ ] D.7 Fix the nine depth-coupled test paths; clear the new cache in the composition-root fixture; drop the
      SHA-pinned branch-hygiene guard, which pins a branch that does not exist here and re-activates after the
      merge.
- [ ] D.8 Fix our own three raw-exception log sites in the lang browser transport, which their privacy guard
      correctly flags; then their guard should run clean and becomes ours.
- [ ] D.9 Their read API: correct the docstring, confirm the RBAC intent, and either wire the dashboard card to
      it or hold it — no speculative backend ahead of a consumer.
- [ ] D.10 Invert the permissive default in the read DAO's scope clause.
- [ ] D.11 Restore the bounded failure reason in the synthesis and db-query logs their sweep over-corrected —
      the code name alone cannot say why nine turns failed.
- [ ] D.12 Gate the legacy root-span suppression on a genuinely configured provider; as written it is always on
      and the legacy span disappears regardless of whether OTel is up.
- [ ] D.13 Relock (resolve `pyproject.toml` to the union, then lock — never hand-merge). Run the app lane.

### Phase E — copilot-mro, deployment half
- [ ] E.1 Reject-list first (M-ACCEPT, M-PINS), so nothing downstream depends on it.
- [ ] E.2 Collector profiles: take the New Relic overlay, the four durability fragments, the env examples and
      the validate script. Their fragments are correctly exporter-only with no `service:` block, so a profile
      cannot inherit another's exporter. Reword the queue's "outage budget" claim — a five-minute retry cap
      survives a restart, not an outage — and drop the unearned "memory limiter" claim.
- [ ] E.3 Document that production must bind-mount the file-storage dir: a demo box with tmpfs `/tmp` plus a
      durability fragment gets a "durable" queue that evaporates on restart.
- [ ] E.4 Compose: take the Phoenix split, the loopback browser receiver and the tmpfs mode. **Immediately**
      fix the otel conftest — the base compose loses the Phoenix service while our smoke override still defines
      one with no image, and the overlay requires an API key the compose env does not set. This is the most
      dangerous auto-merging interaction in this half.
- [ ] E.5 Alert rules: ours for browser alerts (theirs lacks the grouping fix that makes three Web-Vitals rules
      armable, and the sample guards). Adopt their rewritten agent-rule guard — it catches *stale* dark wording,
      not just missing wording — and retire ours, which fails outright on their descriptions.
- [ ] E.6 Grafana per M-GRAFANA / M-FRONTEND; keep both phase-8 satellite boards.
- [ ] E.7 Catalogue: ours as base, graft their panel-to-source inventory, and apply their CloudWatch
      brace-selector normalisation to our aws blocks — our current spellings mix Prometheus suffixes with
      dotted OTLP names and will not resolve.
- [ ] E.8 Tests last, resolving the two that share the dark-note vocabulary together.
- [ ] E.9 Non-container lane (baseline 87/0, expect ≈100–112; anything below 87 is a finding), then the
      container lanes and both validate scripts — the only thing that has ever proved the New Relic overlay and
      the four durability compositions actually load. Neither side has run it.

### Phase F — docs
- [ ] F.1 Merge docs with our master plan as the base; graft their new sections.
- [ ] F.2 Resolve the phase-numbering collision: their "Phase 8 — audit follow-ups" becomes Phase 11; their
      Phase 1c keeps its name and is recorded as a re-cut of our gated 1b.7.
- [ ] F.3 Fold their research 08 in as the Task R starting baseline, correcting its central finding: **Gate M
      was declared 2026-09-14** — their branch could not see it, so their gate reassessment concludes "still
      closed" and defers the sole `chat_turn_facts` writer on that basis.
- [ ] F.4 Reconcile the two outcome vocabularies: their `operation.outcome` against the spec's
      `agent.outcome` / `tool.outcome`, and catalogue the attribute spellings their spans introduce that no
      document names.

### Phase G — close the gaps (scope M-SCOPE)
- [ ] G.1 **Task R, widened: post-migration rescoping AND an estate-wide signal-coverage audit.** R as originally
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
- [ ] G.2 Phase 0.5 / 0.6 residue their sweep misses; the AST guard for user content in logs as a permanent
      rule; delete the copilot-mro `/metrics` route and its dependency.
- [ ] G.3 Phase 3.3 — **demoted from "build it" to "Task R decides".** The item was written when nothing was
      instrumented; now every LangGraph model call goes through our own gateway, so the genai instrumentor
      would largely duplicate what we already emit — which is the same double-counting the spec bans the
      botocore instrumentor for. R must measure what in the lang runtime emits no span today and then choose
      between the instrumentor and a few hand-written node spans. Keep the lint test forbidding the
      botocore/anthropic/openai instrumentors, and the spec §8 content-flag CI check on the env templates,
      which no phase ever implemented and which goes live the moment any genai instrumentor does.
- [ ] G.4 Phase 3.4 Claude Code CLI built-in telemetry — missing on both sides.
- [ ] G.5 Phase 3.7 the sole `chat_turn_facts` writer on the block-save path, same transaction, idempotent at
      the backfill's facts version — unblocked by Gate M, and the reason three panel families are empty.
- [ ] G.6 `agent.ledger.write_failures`; subagent span and metric call sites; tenant and department on tool
      metrics; M-TOKENUSAGE.
- [ ] G.7 Phase 3.5 residue: S3 spill for oversize bodies instead of dropping them; a redaction rule for
      provider error messages carrying account ids and ARNs.
- [ ] G.8 Phase 7.3 – 7.6: the `eval_results` table keyed by ledger profile + registry revision, the harness
      dataset/experiment push, the per-tenant quality report, and residency enforcement in overlay validation.
- [ ] ~~G.9 Schedule the `chat_turn_facts` backfill.~~ **DROPPED by the owner 2026-09-19 — no backfill needed.**
      The online writer (G.5) becomes the sole populator; `core/scripts/backfill_chat_turn_facts.py` stays
      available for a one-off reconciliation but is scheduled nowhere. Panels reading facts show data from the
      writer's landing forward, not historically.
- [ ] G.10 The Weaviate connection-factory span owed from C1.6, and the span-metrics dimensions the dependency
      board actually promotes — as instrumented, the board's named consumer gets nothing for S3.

### Phase H — out of scope here, recorded
The live batch, publishing, the iac plan gate and the first apply. Blocked on the owner being present, CI
secrets and the AWS deferral.

---

## 4. Decisions

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

### 4e. P0 register from Phase 0 — the merge does not start until these are answered

| id | Finding | Why it is P0 |
|---|---|---|
| **P0-COLLECTOR** | `base.yaml` instantiates the file-storage extension unconditionally on all four profiles, so the collector dies at startup with `mkdir /tmp: permission denied` on any runtime that does not hand it a writable `/tmp` — **proved by running the pinned image**. `otelcol validate` returns rc=0 on exactly that config because it never builds extensions, and `validate.sh` runs only `validate`. The four compose files were patched with tmpfs; the **AWS demo box provisions the collector from `iac/demo_ec2_setup.sh`**, outside this repo and outside the test that checks compose files. | Green CI, green validate, and an observability stack that observes nothing — the one outage nobody is watching for, because the thing that would report it is the thing that died. Fix is ~3 lines; the verification gap needs a real container start added to `validate.sh`. |
| **P0-499** | Their `events_endpoints.py` predates our client-abort work; ours handles `ClientDisconnect` → 499 + one INFO line, theirs has none, and their edits sit inside the same `try` block. | A "take theirs" resolution silently restores ERROR-with-traceback 500s for every abandoned browser POST. |
| **P0-ABORT** | Our abort test fails on merge for **two** independent reasons, not one: the `None`-returning sink, *and* the 202 body gaining `duplicates`. | Fixing the sink alone leaves it red and looks like a flaky merge. |
| **P0-PARTITION** | A skip flag was added to the Weaviate tenant-partition boot check, inside an observability phase, outside their own frozen manifest — replacing a docstring that read "a boot that logged either and served anyway would be the warning nobody reads". | It converts a tenant-isolation gate into a warning, ungated by environment and undocumented in every `.env`, compose and iac file. M-WARN covers the fix. |
| **P0-GUARD** | An existing guard — written verbatim to catch a call site reverting to `type(exc).__name__` — **fails on merge**, because they did exactly that at all three call sites and left the helper as dead code. Verified live: it passes on our tree today. | They shipped over a live guard without running it. It is also the cleanest proof that their sweep was hand-rolled rather than routed through `failure_fields`. |
| **P0-INERT** | 35 inert tests, including three that now *assert* a defect (requiring `grafana:latest`, requiring the destructive `deleteDatasources` entry, requiring exactly three frontend panels). | Restoring correct behaviour now reads as breaking a test, which is how a defect becomes permanent. |

### 4d. REOPENED — owner decisions the Phase 0 reviews surfaced

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

---

## 6. Future improvements

*(Filled as items are deliberately deferred, each with what is missing, why it was deferred, and what the
complete solution would look like.)*

---

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

### Environment rules confirmed this phase
- The otel non-container lane: `DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest -q
  ../copilot-mro/tests/integration/otel` from `/home/aditya/Code/api`. **135 collected, 111 passed, 24 skipped,
  ~5 s** on `langgraph-merge` `417df303`.
- Container lanes need `OTEL_COMPOSE_SMOKE=1` / `OTEL_RULES_CHECK=1`; without them the smokes are **collected
  and reported SKIPPED**, so a "no failures" reading is reading a skip. Treat a skip there as a failure.
- `otelcol validate` does not build extensions. A real container start is the only proof a profile loads.

---

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
