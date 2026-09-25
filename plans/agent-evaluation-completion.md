# Agent evaluation / quality scoring — finish Phase 7

**Opened 2026-09-20.** Owner ruling: this is **its own project, starting immediately after the
observability merge closes**. It is **not optional and not new scope** — it is Phase 7 of the original
observability rebuild, unfinished. It inherits **all six** of that phase's items, not just the ones a
later renumbering (G.8) happened to name.

Governing documents (do not duplicate them here):
- `docs/plans/observability-rebuild.md` §11 — **Phase 7, items 7.1–7.6**, all unticked. The source of scope.
- `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` — the ruled design; §6.5 (residency,
  one Phoenix project per tenant), §12 (attribute mapping), §11 = the 20 owner rulings (11 = residency,
  12 = score identity).
- `docs/plans/observability-telemetry-merge-and-completion.md` — §5.8 (the RV3 rejection), §4d-resolved
  (M-EVALS, M-RESIDENCY), §4e dispositions. **Residency is that plan's deliverable, not this one's.**
- `.superpowers/sdd/observability-telemetry-merge-and-completion/progress.md` — the 2026-09-20 correction
  ("the evals rejection was about plumbing, not about the measures") and the scope note
  ("evals were never new scope").
- `copilot-mro/docs/superpowers/plans/2026-09-17-phoenix-trace-evaluations.md` and
  `copilot-mro/docs/runbooks/observability/phoenix-evaluations.md` — the colleague's own plan and runbook
  for the code being salvaged. Read as evidence of intent, not as a contract.

All paths below are relative to `copilot-mro/` unless stated. They were verified in the merge worktree
`copilot-mro-obsm` on 2026-09-20; **Phase 0 re-verifies them on whatever mainline the merge lands on.**

---

## 1. Situation

The colleague's branch shipped a Phoenix-based offline trace evaluation suite. RV3 reviewed it and
**rejected it as a workbench while keeping it as a measure set**. Those are two different verdicts and the
distinction is the whole shape of this project: what was wrong is the plumbing around the scores — identity,
persistence, the citation computation, the integration boundary, and what a "dry run" costs. What was right
is the measurement design, and that is the expensive part to invent.

### 1.1 What exists and is kept (verified in the tree)

| thing | where | why it is kept |
|---|---|---|
| Seven measures, each with a **closed label set** plus `not_evaluated` | `copilot_mro/app/services/agent_evaluation/contracts.py:21-37` *(P0.1: was `:17`; the file gained ~340 lines of G.13 residency machinery)* | The vocabulary is the product. `not_evaluated` separates "judged and passed" from "never judged" — the distinction whose absence makes most eval data useless. |
| Six LLM-judged, one code-computed | same file, `ANNOTATOR_LLM` / `ANNOTATOR_CODE` | A deterministic measure that needs no judge call is worth having; this one is simply computed wrong today. |
| Two **session-level** measures with their own candidate / turn / result types | `contracts.py` (`SessionEvaluationCandidate`, `SessionTurn`), `session_runner.py` | A conversation-grain judgement is a deliberate design, not a prototype accident. |
| Judge-contamination guard | `phoenix_adapter.py`, in the `agent_trajectory_quality` classifier prompt | Evidence someone thought about one judge's score leaking into another's. |
| Runner failure isolation | `runner.py` — per-work-item try/except, failure id `span:annotation:ExcType`, bounded concurrency 1..16 | One evaluator must not stop a batch. Correct as written. |
| Collector OpenInference alias fragment | `deployment/otel/content-phoenix.yaml` | Already routes one Phoenix project per tenant plus `internal`. |

The seven measures, for the record: `citation_coverage` (pass/fail, code-computed), `answer_relevance`
(pass/fail), `groundedness` (faithful/unfaithful), `agent_trajectory_quality` (good/inefficient/poor),
`failure_recovery_quality` (recovered/degraded/unrecovered), `session_resolution`
(resolved/partially_resolved/unresolved), `session_coherence` (coherent/partially_coherent/incoherent).

### 1.2 What is rebuilt (the project's substance)

1. **Score identity — the root item.** Nothing recorded on a score says which system version, model profile,
   registry revision, judge provider, judge model or judge prompt produced it, nor which run it belongs to.
   Today's identity is `annotation_name:evaluator_version`, a two-field string that is also the
   already-evaluated skip key. Consequence: **no two runs are comparable, and every annotation already
   written is permanently ambiguous.** Most other items depend on this.
2. **`eval_results`** (7.3) — tenant-scoped, keyed by that identity. **Confirmed absent** from the tree
   (no reference in any `.py`, `.sql` or `.md`).
3. **`citation_coverage` rewritten** against this product's real citations. It currently passes a turn whose
   answer contains any bracketed integer or `[source…]` token — so a torque value or a year reads as a
   citation — while this product's citations are *stripped from the displayed answer* and carried as
   structured spans with character offsets into the final answer string.
4. **A real integration test.** The entire Phoenix boundary is mocked (~2,800 lines of unit tests across five
   files, every one against a double). The first live run would be the first test.
5. **The `"dry_run"` cost defect.** The CLI's `--publish` flag gates only the annotation *write*. Every judge
   call is made and paid for either way, and the run report calls the mode `dry_run`.
6. **The inherited residency precondition** — see §2.2. Not built here; **verified here, and its gaps named.**

### 1.3 What the merge already delivered against Phase 7

Verify, do not rebuild:
- **7.1 is substantially done.** Phoenix is an optional overlay (`deployment/docker-compose.phoenix.yml`),
  image-pinned, auth on, retention via env, UI bound to loopback, one project per tenant plus `internal`
  via the collector's group-by-tenant and project-name transform. The main `deployment/docker-compose.yml`
  carries **no Phoenix reference at all**, so the "mandatory compose coupling" that rebuild task 11.4 was
  meant to remove appears already gone.
- **The 7.1 acceptance test partly exists.** The compose smoke lists `phoenix` among its services and already
  posts a `phoenix-connected-smoke` trace and a two-tenant `phoenix-routing-smoke` payload, gated by the
  `compose_stack` marker and `OTEL_COMPOSE_SMOKE=1`.
- **7.6's sampling and opt-out halves exist.** A per-row deterministic sample rate and the per-tenant
  `tenants.llm_content_capture_enabled` policy both gate the content copy; the collector keeps only spans the
  application marked as content copies. What 7.6 still wants is the **same-account refusal**.
- **An identity vocabulary already exists and is proven.** `llm_model_calls` carries `profile`,
  `profile_revision`, `registry_revision`, `provider`, `model`; spans carry the registry revision as a
  `gen_ai.model.*` attribute; content copies carry tenant, session, turn and **block** correlation ids.
  `eval_results` should reuse that vocabulary rather than invent a parallel one.

---

## 2. Contracts this project works under

### 2.1 Verification lanes

| lane | what it is | when a phase may cite it |
|---|---|---|
| **unit** | `DEBUG=false poetry run pytest tests/unit/observability/ -q`, run from the shared `api` Poetry environment | Pure contract / computation / orchestration behaviour. |
| **registry** | `tests/registries/tables/` — DDL shape, tenancy classification, RLS declaration | The `eval_results` relation. |
| **db** | marker-gated live-Postgres tests | Isolation and the seeded "v2 vs v1" query. |
| **compose** | `compose_stack` marker **and** `OTEL_COMPOSE_SMOKE=1` **and** a reachable docker daemon | Anything that must prove Phoenix actually received, stored and rendered something. |
| **live run** | An operator-driven run against a real Phoenix project with a real judge provider | Anything a fixture cannot prove. **Named as such, never faked with a mock.** |

Test authoring follows the repo's rules: two-level layout, globally unique basenames, and the dynamic-loader
pattern for anything that would otherwise trigger full package init. See §6 — the existing eval tests do not
follow the loader rule, and Phase 0 measures whether that costs anything.

**Where NEW tests land (added 2026-09-23, plan-review S11 — settled once so four phases don't each
improvise):** new eval tests go in new **loader-pattern** files under `tests/unit/observability/` (domain
subfolder as the layout rule requires), built on `tests/_package_stubs.py` — never a hand-rolled stub
helper. Extend one of the five existing package-importing files only when the behavior under test already
lives there, converting that file to the loader pattern opportunistically in the same change (P0.3's
standing decision). Registry/db/compose lanes follow their existing homes.

### 2.2 Precondition inherited from the merge — the provider allowlist / residency


> **BLOCK LIFTED 2026-09-20 — G.13 is closed and mutation-proved.** `copilot-mro-obsm 4bfa4967`.
> The judge provider is now validated against `IN_ACCOUNT_JUDGE_PROVIDERS` (`azure`, `bedrock`,
> `ollama`) declared in code at `agent_evaluation/contracts.py:56` *(P0.2 correction: sits at
> `contracts.py:64` on the pushed mainline `9debf188`)*, enforced twice — in `__init__`
> and again immediately before `LLM(...)`, ahead of the vendor SDK import — with a fail-closed refusal
> that cites this spec. The runbook no longer teaches `--provider openai` anywhere, and a guard
> resolves every `--provider` in it against the catalogue. **Per M-EVALSGATE this project is now
> unblocked and may start.**
>
> **Two things it INHERITS rather than finds solved, and neither is a reason to wait:**
> 1. **Configurability is per-DEPLOYMENT, not per-tenant.** §2.2 below asks for both. The narrowing was
>    escalated rather than quietly widened, and building the per-tenant half is this project's work.
> 2. **Two residuals cannot be closed in-process:** an `evaluator=` object injected already bound to a
>    vendor LLM carries its own client, and a caller implementing the `JudgeEvaluator` protocol
>    entirely sits outside the adapter's reach. Both are code-level, not config-level — a reviewer, not
>    a runtime check, is what catches them.
>
> The exporter-side residency question remains this project's Phase 8 and was deliberately untouched.

> **STATUS CORRECTION, 2026-09-20 — read this before relying on the paragraph below.**
> The owner's ruling is real and unchanged: residency enforcement lands in the merge, not here. **But no
> Phase G item existed for it until today**, so the ruling had no owner and nothing was built. The control
> sat in a gap between the two plans, each of which pointed at the other. Verified in the merged tree on
> 2026-09-20: **zero** matches for residency / allowlist / allowed-provider anywhere under
> `copilot_mro/app/services/agent_evaluation/`; `provider` is a free-form string passed straight into
> `LLM(provider=self._provider, model=self._model)` at `phoenix_adapter.py:289` and `:399`; and the runbook
> documents `--provider openai` at `phoenix-evaluations.md:121` and `:137`. The merge plan now carries
> **G.13** for exactly this, and **this project must not start until G.13 is closed and mutation-proved.**
> Treating the sentence below as already true is what would send a user's question, the model's answer and
> retrieved manual text to a third-party vendor on the first live run.

**The owner ruled that residency enforcement lands in the CURRENT merge, not here.** This project therefore
treats it as a precondition and does not implement it. It does, however, depend on it completely: the ruling
is that **no eval run touches real traces until it is enforced**, and every phase of this project past the
Phoenix probe wants to run against real traces.

What the precondition must guarantee, stated plainly so the gap is checkable:
What the precondition must guarantee, stated plainly so the gap is checkable:

- The judge receives **the user's question, the model's answer, and retrieved manual text**. That is customer
  content, in full, by design — the measures cannot work on less.
- The provider is today a **free-form string** supplied per run, whose documented default is **OpenAI**.
- **Customer content must never leave the customer's own account and must never reach an outside vendor in
  the data path.** That is spec §6.5 and ruling 11, applied — not a new decision.

What this project needs from it, beyond "an allowlist exists":

- [ ] The refusal is **fail-closed** — an unset, unknown or misspelled provider is refused, not defaulted.
- [ ] The refusal happens **before any candidate is fetched**, so a rejected run costs nothing and reads no
      content.
- [ ] It covers the **library entry points**, not only the CLI. A harness or report generator that calls the
      runner directly must hit the same gate.
- [ ] It covers the **session judge path**, which is a separate class from the per-turn judge path.
- [ ] It is **configurable per deployment / per tenant**, because "the customer's own account" differs per
      customer — a single global allowlist cannot express it.

**If the merge's version lands narrower than this, that is a gap for this project to name and escalate, not to
quietly widen.** Phase 0 checks each bullet and records the result in §7; anything missing is an owner item,
and the phases that need real traces stop at their fixture-level acceptance until it is answered.

### 2.3 Where the six original items and the RV3 rebuild list conflict or overlap

This matters because the two lists were written a year apart in project time and use the same words for
different things. Resolved in §5; recorded here so the overlap is not rediscovered mid-build.

| # | Overlap or conflict | Reading taken |
|---|---|---|
| 1 | **7.3's column list is narrower than RV3's identity.** 7.3 names `judge_version`; RV3 requires judge **provider**, **model** and **prompt hash**. A `judge_version` string cannot distinguish two runs of the same evaluator code against different judge models. | Take RV3's identity; 7.3's list is a floor, not a ceiling. |
| 2 | **`profile` is ambiguous.** In 7.3 it sits beside `registry_revision`, which reads as the **model-profile** id. Elsewhere in the same spec "profile" means the **observability backend profile** (oss / aws / azure / newrelic). | Owner question — §7. Working assumption: model profile, matching the existing `llm_model_calls` vocabulary. |
| 3 | **Subject identity and judge identity are conflated.** A score has two versioned parties: the system that produced the answer, and the judge that scored it. 7.3's single flat row does not separate them. | Separate them explicitly. Both belong on the row; neither substitutes for the other. |
| 4 | **Two different things are called "dry run".** 7.4's is a *push* dry-run (produce the Phoenix payload with no Phoenix endpoint). The CLI's is a *publish* dry-run (judge everything, write nothing). RV3 rejects the second as a cost defect. | Keep both, **name them differently**, and make the no-cost mode the default-safe one. |
| 5 | **7.4's acceptance is the pattern RV3 rejected.** "Dry-run mode produces the payload without a Phoenix endpoint" is a mock-boundary test — exactly the shape that left the first live run as the first test. | 7.4's dry-run test is kept as a *fast* check and is **not sufficient** acceptance. Phase 5 supplies the real one. |
| 6 | **Two residency surfaces share one word.** 7.6's is the **exporter** side — a cross-account exporter config must be refused. M-RESIDENCY's is the **judge** side — which vendor the judge calls. | The merge owns the judge side (§2.2). **The exporter-side refusal is unclaimed by any phase and is inherited here** — Phase 8. |
| 7 | **7.1 / 7.2 are partly satisfied already** by the merge's deployment half (§1.3). | Phase 3 is verify-and-close plus a live probe, not a build. |
| 8 | **G.8 was 7.3–7.6 renumbered.** It is not additional scope, and it omitted 7.1 and 7.2. | Ignore the G.8 numbering; work the original six. |
| 9 | **(added 2026-09-23, plan-review C3)** 7.4's datasets/experiments vs spec §6.5's project topology: synthetic sets belong in the `internal` project, but the shipped validator accepts only `tenant-<id>`, and tenant-scoped `eval_results` has no home for a no-tenant row. | P6.7 + owner Q10. A genuine 7.3-vs-§6.5 overlap the original table missed. |
| 10 | **(added 2026-09-23, plan-review C7)** The merge plan's unticked owner item — M-EVALS ruled "the rest does not merge", yet session types, `session_runner`, the adapter and the CLI are all in the tree and this plan reworks them in place. | **Claimed here: fix-forward supersedes "the rest does not merge", per the merge ledger's 2026-09-20 correction** ("the evals rejection was about plumbing, not about the measures"; "evals were never new scope"). The merge-plan checkbox now points at this row. If the owner did NOT intend to bless keeping the session/adapter/CLI surfaces, say so at the TA+TB review — §7. |

---

## 3. Phases

Each phase ships something provable and is reviewed before the next starts. Estimates are **AI-assistant
execution time**; wall-clock is dominated by owner review between phases, which is stated separately.

> **EXECUTION RE-PHASING, 2026-09-23 (owner: SDD-driven, cap 4, minimize Fable; plan-review verdicts
> TRIM-FIRST + FIX-FIRST triaged in `.superpowers/sdd/agent-evaluation-completion/`).** The phase
> CONTENT below stands as amended in place; the EXECUTION grouping is now six tasks, SDD continuous
> mode replacing the per-phase owner pauses:
> **TA** = Phases 1+2 (identity + `eval_results`; P1.4 moves out, see below) · **TB** = Phase 4 ·
> **TC1** = Phase 3's real delta (probe + aliases; P3.1/P3.2/P3.5 are verify-or-delta only) ·
> **TC2** = Phase 5 (gains P1.4, P5.7, session-path acceptance, runbook updates) · **TD** = Phases 6+7 ·
> **TE** = Phase 8 (per-tenant allowlist OUT → §10) · **TF** = Phase 9 + close-out.
> Fable review batches: TA+TB · TC1+TC2 · TD · TE · final whole-branch. Implementers Opus 5.5.

### Phase 0 — Inventory, preconditions, and the baseline nobody has

**Goal:** start from measured facts, not from this document's snapshot.

- [x] P0.1 Confirm the merge closed and identify the mainline branch and commit the evals code now sits on;
      re-verify every path and claim in §1.1 / §1.3 against it and correct this plan where it drifted.
      *(Done 2026-09-23 — §9 Phase 0; mainline `langgraph-merge` @ `9debf188`; every §1.1/§1.3 claim
      CONFIRMED, two line-number drifts corrected in place.)*
- [x] P0.2 Walk §2.2's five bullets against the residency enforcement the merge actually shipped. Record each
      as met / partial / absent with the evidence checked. Anything short of met becomes an owner item in §7.
      *(Done 2026-09-23 — §9 Phase 0; verdicts 1/2/4 MET, 3/5 PARTIAL, both partials banner-admitted.)*
- [x] P0.3 Time the existing evaluation test files as they stand. Record the per-file wall time. This is the
      baseline for the repo's "<2s per file, >5s means package init is firing" rule, and it decides whether
      converting them to the dynamic-loader pattern is a real win or bookkeeping.
      *(Done 2026-09-23 — §9 Phase 0; all five files breach 2s, package init confirmed firing.)*
- [x] P0.4 Confirm `eval_results` is still absent, and confirm whether the per-turn analytics projection has
      gained a production writer yet (it had none at merge time — only an owner-run backfill). Phase 4's
      design choice depends on the answer.
      *(Done 2026-09-23 — `eval_results` absent under any name; `chat_turn_facts` NOW HAS production
      writers incl. citation fields — Q2's premise updated. §9 Phase 0.)*
- [x] P0.5 Establish whether any annotation has **already been written** to a live Phoenix project by the
      colleague's runs. If so, those annotations carry no identity and cannot be disambiguated; record the
      count and the projects, and raise the disposition (purge vs quarantine vs leave) as an owner item.
      *(Done 2026-09-23 — none exist, with strong documentary evidence no live eval run ever happened
      anywhere; one 30-second owner spot-check named in §7 Q4. §9 Phase 0.)*
- [x] P0.6 Record the measured defects found while writing this plan (§6) as confirmed or refuted.
      *(Done 2026-09-23 — findings 1–4 CONFIRMED, finding 5 REFUTED as overtaken; marks recorded in §6.)*

**Acceptance:** a written inventory in this file's §7 and §8 in which every claim in §1.1, §1.3 and §2.2 is
either confirmed with the evidence checked, or corrected. No code changes.
**Lane:** unit (timing only) + read-only inspection. **Estimate:** 20–30 min execution.

---

### Phase 1 — Score identity

**Goal:** a score says what produced it. Nothing downstream is worth building on an unidentified score.

- [x] P1.1 Define, **as two named things that are never conflated** (plan-review C1, applying §11's own
      lesson): the **score identity** — everything a score carries: **subject identity** (tenant,
      department, model profile and its revision, registry revision, the trace and span the score is
      about, and the session / **block** correlation ids the content copy already carries — the "turn" id
      IS `block_id`, per P0.1; do not invent a turn id) + **judge identity** (annotation name, evaluator
      version, annotator kind, judge provider, judge model, a stable hash of the judge prompt actually
      used) + the **run id** shared by every score in one invocation — and the **idempotency key** — the
      score identity **minus the run id**, evaluated per subject span (or session): same key = same
      score, replace; different key = new score, append. The run id names *which invocation* produced a
      score; it never decides whether the score already exists.
- [x] P1.2 Make the judge-prompt hash a property of the evaluator, derived from the prompt text the evaluator
      will actually send, so editing a prompt changes the identity without anyone remembering to bump a
      version string. Judge provider defaults, temperature and library version are **excluded from
      identity by decision** (plan-review S12) — recorded in §10, not adjudicated further.
- [x] P1.3 Widen the **already-evaluated skip key to the idempotency key** (P1.1's second thing), so a
      re-run with a different judge model, prompt, provider, evaluator version or registry revision is a
      new evaluation rather than a skip — while an identical re-run (differing only in run id) IS skipped.
      Today's key is `annotation_name:evaluator_version`.
- [x] P1.4 **MOVED to Phase 5 (TC2)** — plan-review S9+C8: the session sink already upserts on a stable
      identifier (no double-annotation risk; the cost is judge re-payment, which cannot bite before the
      first live boundary work), and the session skip machinery should land where the live-Phoenix test
      proves it. The session path's skip uses the SAME idempotency key defined here.
- [x] P1.5 Carry the identity through the run report, so a report is self-describing rather than needing the
      invocation's shell history to interpret.
- [x] P1.6 Logging coverage for the modules touched, per the rebuild's standing rule: every failure path logs
      at the right level with bound context, no user content in log fields, one line per run lifecycle
      boundary.

**Acceptance (measurable, rewritten per plan-review C2 — per-field behavioral teeth, not a shape check):**
a **parameterized test over every field of the idempotency key**: for each field, a pair of runs on a
fixed candidate differing **only** in that field, where the second run is **NOT** skipped; plus one pair
differing only in run id, where the second **IS** skipped (and replaces, not appends). Removing any
single field from the key implementation must fail the corresponding parameter case — behaviorally, not
via an attribute-presence assert. The session-path equivalent runs when P1.4 lands in Phase 5 (TC2),
against the same key. Full `tests/unit/observability/` stays green.
**Lane:** unit. **Estimate:** 60–90 min execution.

---

### Phase 2 — `eval_results` (7.3)

**Goal:** scores persist somewhere a report can read them, tenant-scoped, keyed by Phase 1's identity.

- [x] P2.1 Declare the relation in the table registry: tenant-scoped, private by construction (never disclosed
      by the catalog reference, never in the query allowlist), following the existing per-turn-facts and
      model-calls relations as the pattern rather than inventing one.
- [x] P2.2 Columns carry Phase 1's identity in full, plus the measure, the label, the optional numeric score,
      the bounded explanation, the golden-set id where a run came from a curated set, and the row timestamp.
      7.3's original list is the floor (§2.3 row 1).
- [x] P2.3 Row-level security and the read grant for the reporting role, matching the existing analytics
      relations. Reports read through the read-only role; the harness writes as the owner.
- [x] P2.5 The runner writes to it, upserting on the **idempotency key** (P1.1): same key replaces —
      updating the stored run id to the latest invocation — different key appends. (P2.4 folded here,
      plan-review S10/C1; "the same score twice" is answered by the key definition.) The write must not
      be able to stop a batch, same doctrine as the judge call — a failed persist is a counted failure,
      not an aborted run.
- [x] P2.6 Logging coverage for the writer.

**Acceptance (measurable):** DDL and tenancy-classification tests pass in the registry lane; a seeded
two-tenant database test shows tenant A's rows invisible to tenant B under the request binding; and the
"v2 vs v1" query named in 7.3 returns the expected per-measure comparison from seeded rows differing only in
registry revision. A persist failure in a batch of N yields N−1 stored scores and one counted failure.
**Lane:** registry + db. **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 3 — Phoenix runs, and our spans render in it (7.1 + 7.2)

**Goal:** you cannot judge traces the tool cannot read. Close 7.1 and 7.2 with evidence, not configuration.

- [x] P3.1 **Verify-and-tick only (plan-review S8):** Phase 0 already confirmed every clause with
      file:line anchors (§9) — overlay shape, image pin, auth, retention, loopback, per-tenant +
      `internal` routing, Phoenix-free base — **plus 7.1's remaining clause the list omitted
      (plan-review C10): the `otel-gateway` client-account variant stays optional** (P0.5 verified it
      optional and never fed). Remaining work = re-diff against the mainline HEAD the task runs on, and
      tick rebuild task 11.4 in the rebuild plan's ledger citing §9. No build.
- [x] P3.2 **Folded into P3.3's stack boot (plan-review S8):** `deployment/.env.sample` now ships the
      Phoenix secrets (P0.5); the probe cannot run without a booted stack, so the boot IS the check.
- [x] P3.7 **(new, owner-ruled 2026-09-23: "it should always be up locally")** Make the LOCAL dev
      bring-up include the Phoenix overlay by default — set `COMPOSE_FILE=docker-compose.yml:docker-compose.phoenix.yml`
      in the local `deployment/.env`, document it in `deployment/.env.sample` and the dev-stack notes —
      while the base compose file itself stays Phoenix-free (the 11.4 decoupling holds for deployment
      profiles; this is a local-default, not a compose-file change).
- [x] P3.3 **7.2, the attribute-mapping probe:** send one **real agent trace** (the smoke posts synthetic
      payloads — the real-app emission is the novelty) through the content pipeline into a live Phoenix
      and record, per attribute, what Phoenix **renders in the UI surface** — each probe-table row names
      the panel or GraphQL field observed, not just the stored attribute (plan-review C9): model,
      provider, token counts, cost, tool name and id, span kind, input and output bodies, session
      grouping. The output is a table of *expected vs rendered*, not a pass/fail claim.
- [x] P3.4 Fix the mapping gaps the probe finds by adding or correcting aliases in the collector fragment.
      Two are suspect on reading and must be confirmed or refuted by the probe rather than assumed: the
      invocation-parameters alias is fed from the prompt attribute, and the output-messages alias from the
      completion attribute — both are plausible mis-mappings that would render as wrong panels rather than
      as missing ones. Also check whether a total-token attribute is expected and unset.
- [x] P3.5 **Delta only (plan-review S2 — the read-back half is SHIPPED):** the smoke already reads
      traces back from Phoenix and asserts input/output, model, provider, token counts, cost, tool
      name+id, span kinds, parent structure, tenant routing and `internal` isolation
      (`test_oss_profile_smoke.py:470-589`). Extend it only with the probe-table rows it does not cover
      (session grouping, invocation parameters, total tokens, whatever P3.4 changes), asserting the
      **aliased OpenInference names** where aliases exist, not only the `gen_ai.*` originals (C9).
- [x] P3.6 Record the probe table in this plan. It is the reference for every later "why does this panel look
      wrong" question, and re-running it is how a Phoenix version bump is validated.

**Acceptance (measurable):** the compose smoke, run with the stack up, posts a content-copy agent trace and
then **reads it back from Phoenix**, asserting the tenant project it landed in and each attribute the probe
table says should render. Every row in the probe table is either rendered correctly or has a named,
filed gap. **The probe itself can only be proved by a live stack run — stated, not simulated.**
**Lane:** compose (`OTEL_COMPOSE_SMOKE=1`) + one operator-driven live stack run. **Estimate:** 45–90 min
execution, plus stack start-up; +1 owner review cycle.

---

### Phase 4 — `citation_coverage` against real citations

**Goal:** the one deterministic measure measures the thing it is named after.

- [x] P4.1 **(Collapsed P4.1–P4.3, plan-review S4 + C5 — the premise flipped at P0.4.)** Source of truth
      = the **per-turn analytics projection `chat_turn_facts`**, which now HAS a production writer
      filling `citation_count` and `cited_documents` on every block save (§9 P0.4; the "no production
      writer" concern is dead). Correlation path: join a Phoenix trace to the projection on
      (`tenant.id`, `flynapse.block_id`) — the content copy already carries both as span attributes; use
      that join, never re-derive it. The structured-spans path (authoritative offsets, but needs new
      telemetry + a redaction decision no closed-set label requires) is **cut to §10 Future
      Improvements**. Per §7 Q2 this consciously amends M-EVALS' letter ("structured citation offsets")
      — the owner confirms at the TA+TB review or vetoes in-thread.
- [x] P4.4 Define what the measure now means, in the labels it already has: a turn that cites nothing but
      needed to cite, a turn that legitimately needed no citation, and a turn with retrieval evidence but no
      citation are three different outcomes and only one is `fail` — the third label `not_evaluated` exists
      for exactly this.
- [x] P4.5 Delete the bracket-marker heuristic and the assumption that a displayed answer contains markers.
- [x] P4.6 Fixtures drawn from **real persisted turns**, including the adversarial ones: an answer containing
      a bracketed torque value and a year with no citations (today: `pass`, correctly `fail`), and an answer
      with citations and no brackets at all (today: `fail`, correctly `pass`).

**Acceptance (measurable):** on a fixture set of real turns with known citation state, the measure's label
matches the known state for every turn, **including both adversarial cases, each of which must flip relative
to today's implementation.** Zero turns are scored from answer text alone.
**Lane:** unit, on fixtures captured from real persisted turns. **Estimate:** 60–90 min execution;
+1 owner review cycle.

---

### Phase 5 — The run boundary: an honest dry run, and a test that touches Phoenix

**Goal:** a run that costs what it says it costs, and a boundary that has been exercised before a customer
pays for it.

- [x] P5.1 Replace the `"dry_run"` mode with **exactly two modes (plan-review S5 — the middle mode has no
      consumer and contradicts Decision 7):** **plan** (default — select candidates, resolve identities,
      report what would be judged and roughly what it would cost, make ZERO provider calls) and **run**
      (judge + publish + persist, opted into). The judge-but-don't-publish mode and today's `--publish`
      flag are deleted: a mode that pays judges and records nothing produces scores that evaporate —
      the exact anti-pattern this project exists to kill. Label preview without recording = a bounded
      `--limit` run; republish is idempotent on the key.
- [x] P5.2 Surface the cost of a run: candidates selected, judge calls made, calls skipped by identity,
      tokens where the provider reports them. A run whose cost is invisible is a run nobody will repeat.
- [x] P5.3 Fix the judge-factory fallthrough (§6.1): an unrecognised measure name currently receives an
      answer-relevance classifier and is scored under the requested name. An unknown measure must be refused.
- [x] P5.4 Build the **real integration test**: a run against a live Phoenix with a stub judge — a judge that
      returns fixed labels and makes no provider call. This exercises every part of the boundary that was
      mocked (candidate fetch from real spans, the annotation write, the read-back, the identity round-trip)
      without paying a vendor. **This is the point of the phase: the mocked part was never the judge, it was
      Phoenix.**
- [x] P5.5 Assert idempotency across the real boundary: run twice, and the second run skips on identity rather
      than double-annotating.
- [x] P5.6 Bank a real judge-provider run as an **operator-run** step with a recorded result, explicitly not
      as a test. It is the only way to learn what the judge does with real manual text, and it cannot be a CI
      lane. **Gated by §7 Q5 (approved provider/model), not by the §7 intro's old sentence.**
      *(Done 2026-09-24 by TF's governed run — §9 TF; what the judge did with real manual text: groundedness
      judged a truncated evidence copy "unfaithful", §10 TF-filed.)*
- [x] P5.7 **(new, plan-review C6)** Add the contamination-guard sentence ("Do not re-score factual
      groundedness.") to the `failure_recovery_quality` prompt and both session prompts — it exists only
      in the trajectory prompt today (§6.4). Prompt-only change, covered by the existing prompt tests.
- [x] P5.8 **(new — P1.4 lands here, plan-review S9)** Session-path idempotency: give
      `SessionEvaluationCandidate` its existing-identities fetch and apply the SAME idempotency key as
      the per-turn path, so session judges stop re-paying on every run.
- [x] P5.9 **(new, plan-review C13)** Update `docs/runbooks/observability/phoenix-evaluations.md` in the
      same phase for everything this phase renames: the two modes and the new default, the report shape,
      the stable-identifier story. The runbook-parsing guard keeps covering providers/models.
- [x] P5.10 **(new, owner-ruled Q8 2026-09-23)** Close the two cheap residency seams: refuse an injected
      `evaluator=` object that arrives pre-bound to a vendor client (provenance check covering the
      post-construction `_evaluator` mutation variant too), and gate or drop
      `run_phoenix_evals.main(judge_factory=…, session_judge_factory=…)`. Keep the AST guard green;
      extend the residency test file with one refusal case per seam. The protocol-level residuals stay
      reviewer-caught by design.

**Acceptance (measurable, extended per plan-review C8):** against a live Phoenix, a run with a stub judge
fetches candidates from real spans, writes annotations, and a read-back returns them with their identity
intact; the second identical run makes zero new annotations. **The same boundary test covers one SESSION
(two completed roots, same session id): annotate, re-run, assert upsert-not-duplicate via the GlobalID
stable-identifier contract and skip via P5.8's key — the session publish path has never been exercised
against a real Phoenix and must not meet one for the first time in Phase 9.** One correlated
`chat_turn_facts` row is seeded so `citation_coverage` resolves a real candidate through the P4.1 join
once. The **plan** mode makes **zero** provider calls, proved by a judge double that raises if called. An
unknown measure name is refused rather than scored.
**Lane:** compose (live Phoenix, stub judge) + unit for the refusal and the plan mode. The real-provider
step is a **live run**, recorded, not a test. **Estimate:** 90–120 min execution.

---

### Phase 6 — Harness → Phoenix datasets and experiments (7.4)

**Goal:** the department evaluation sets become Phoenix datasets, and a scored run becomes a comparable
experiment.

- [x] P6.1 Inventory what the existing end-to-end evaluation harness already produces — curated per-department
      sets and gold fixtures exist in the e2e tree — and map those to the dataset shape rather than authoring
      a second corpus.
- [x] P6.2 Push datasets keyed so that the same set pushed twice is the same dataset, not a duplicate.
- [x] P6.3 Push experiment runs carrying Phase 1's identity, so an experiment in Phoenix and a row in
      `eval_results` are **the same score seen from two sides** — the run id is what ties them.
- [x] P6.4 Keep 7.4's payload-without-an-endpoint check as a fast test, explicitly labelled as a *shape* check
      and not as integration acceptance (§2.3 row 5).
- [x] P6.5 Write the same scores to `eval_results` in the same run. Phoenix is the workbench; the table is the
      record of account. Neither is derived from the other after the fact.
- [x] P6.6 Logging coverage for the push path, including one lifecycle line per dataset and per experiment.
- [x] P6.7 **(new, plan-review C3 — the §6.5 topology hole)** Decide and build where golden-set /
      synthetic runs live: they belong in the **`internal`** Phoenix project per spec §6.5 ("internal
      project for synthetic sets"), but `validate_tenant_project` accepts only `tenant-<id>` and the
      runbook forbids `internal` — so the harness path needs an explicit, narrowly-scoped relaxation.
      Their `eval_results` rows likewise belong to no tenant: the tenancy of synthetic rows (reserved
      internal tenant vs a nullable-tenant partition) is **owner-ruled — §7 Q10 — before this item is
      briefed.** Without this, Phase 6 would pollute a real customer's workbench with synthetic data or
      fabricate a tenant id under RLS.

**Acceptance (measurable):** pushing the same dataset twice yields one dataset; an experiment run appears in
Phoenix with its identity attached and produces the matching rows in `eval_results` under the same run id.
**Row-count formula per grain (plan-review C11): turn-grain rows = candidates × per-turn measures −
identity-skips; session-grain rows = sessions × session measures − identity-skips.** Re-running with a
changed registry revision produces a **second** experiment, not an overwrite. Synthetic rows land in the
`internal` project and under Q10's ruled tenancy, never in a customer project.
**Lane:** compose (live Phoenix) + db. **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 7 — Per-tenant quality report (7.5)

**Goal:** the client-review artefact — what a customer is shown when they ask "is it getting better".

- [x] P7.1 Define the report's content: per-measure accuracy, answer rate, **regressions across versions**
      (which is why identity had to come first), and cost per query. Cost joins the existing per-call usage
      ledger; the report must not re-derive pricing.
- [x] P7.2 Reads happen through the read-only reporting role, per the rebuild's data-access rule.
- [x] P7.3 Render through the **existing document-render helper**, not a new one.
- [x] P7.4 The report states its own scope: which runs, which registry revisions, which judge, and what was
      `not_evaluated` and why. A quality report that hides its denominator is worse than none.
- [x] P7.5 One tenant per report, and a test that proves a report for tenant A contains no row belonging to
      tenant B.
- [x] P7.6 Logging coverage for the generator.

**Acceptance (measurable, determinism defined per plan-review S6+C14):** a fixture result set produces a
**byte-identical markdown/structured intermediate** on two runs — deterministic ordering, **no
generation-time values; timestamps only where data-derived from the fixture rows** (P7.4's "which runs"
scope statement is data, not wall-clock). The PDF conversion stays the existing render helper's
already-tested concern and is NOT held to byte-identity. A two-tenant fixture set produces two reports
with no cross-tenant content (reusing Phase 2's isolation fixtures, proved once — plan-review S10); and
every number in the report is traceable to rows the read-only role can select.
**Lane:** unit (fixtures) + db (isolation). **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 8 — Sampled production copy, same account only (7.6)

**Goal:** close the exporter-side residency item that no phase of the merge claimed (§2.3 row 6).

- [x] P8.1 **Cite, don't re-test (plan-review S7):** the sampling and opt-out halves are shipped,
      merge-tested behavior (`test_llm_content_capture_policy.py`, `_lifecycle.py`, `_privacy_red.py`,
      the settings tests, and the compose smoke's content-copy gating). This item names those tests as
      the evidence; a NEW test is written only for a named gap, not as a confirmation lane.
      **The per-tenant JUDGE allowlist is OUT of this phase (plan-review S3, resolving §7 Q9 and the
      §8 contradiction): per-deployment enforcement is what operation uses; the per-tenant half has no
      consumer today and moves to §10 as an owner-decision Future Improvement.**
- [x] P8.2 Define what "same account" means as a checkable property of the exporter configuration for each
      deployment profile, so it can be refused rather than reviewed.
- [x] P8.3 Make the overlay validation **refuse** a cross-account exporter configuration — 7.6's stated test,
      and the thing that turns the residency ruling from a policy into a mechanism.
- [x] P8.4 Confirm the collector-level guarantee composes with the judge-level allowlist inherited from the
      merge (§2.2). Two surfaces, one rule; a gap in either defeats both.
- [x] P8.5 Record the residency story end to end in the observability runbook: where content goes, who may
      judge it, what refuses what, and how an operator proves it.

**Acceptance (measurable):** a deliberately cross-account exporter configuration is **refused by validation**
with a message naming the offending endpoint; an opted-out tenant produces zero content copies across a
seeded batch at sample rate 1.0; and the profile validation still passes for every legitimate profile.
**Lane:** compose / configuration validation + unit. **Estimate:** 45–75 min execution; +1 owner review cycle.

---

### Phase 9 — First governed live run, and close-out

**Goal:** prove the workbench on real traffic once, then write down what it cost and what it said.

- [x] P9.1 Run the full set against a real tenant project with a real judge provider, within the residency
      allowlist, at a bounded candidate limit. **Plus one bounded golden-set experiment with the real
      judge (plan-review C11): as written before this line, no real judge ever scored a golden-set
      experiment anywhere in the plan, so 7.4's product question ("did v2 beat v1 on the set") would only
      ever have been demonstrated with fixed-label stubs.**
      *(Done 2026-09-24 under the owner's proof-only bounds — §9 TF: 2 tenant turns + 1 session, 1 golden turn.)*
- [x] P9.2 Record the run: identity, candidate count, judge calls, cost, per-measure label distribution, and
      the `not_evaluated` reasons. The `not_evaluated` distribution is the most informative output of a first
      run — it says which measures cannot see their inputs. *(§9 TF.)*
- [x] P9.3 Generate one per-tenant report from that run and read it as a customer would. *(§9 TF.)*
- [x] P9.4 Tick items 7.1–7.6 in `docs/plans/observability-rebuild.md` with the evidence for each, and append
      the review section there. Phase 7 of the rebuild closes here or not at all. *(Done 2026-09-24.)*
- [x] P9.5 File everything deferred into §6 Future Improvements of this file, each with what is missing, why it
      was deferred, and what the complete solution looks like. *(§10 — "§6" is this section's old number; the
      TF-filed block.)*

**Acceptance:** **only provable by a live run** — a recorded run against real traces, inside the allowlist,
whose scores are in `eval_results` with full identity and whose report is readable. No test substitutes for
this and none is invented to pretend otherwise.
**Lane:** live run. **Estimate:** 30–45 min execution once the run is authorised; wall-clock is owner
availability and provider access.

---

### Estimate summary

| | execution |
|---|---|
| Phases 0–9, total AI execution | **~8–11 hours**, i.e. roughly a long working day of agent time |
| Wall clock | dominated by **eight owner review pauses** and by the three phases (3, 5, 9) that need a live stack or provider access. Expect days, not hours, and almost none of it is compute. |

The bottleneck is review and access, not implementation. Phases 1, 2, 4 and 7 could each be done inside an
hour and then wait a day.

---

## 4. Review protocol

Per the workspace rule: after each phase is finalized, an **independent adversarial subagent** — not
self-review — is briefed with the phase's scope, its acceptance criteria and the actual diff, and prompted to
break it. The implementer triages each finding as real gap or intentional deferral, fixes the real gaps, and
records the rest in §6 Future Improvements with reasoning. Phases 1, 3 and 5 are the risky ones and warrant
more than one reviewer, with different lenses (correctness, plan-completeness, simplicity).

Phase 3's reviewer gets a specific brief: **verify the probe table against the running tool, not against the
configuration file.** The whole failure mode of the work being rebuilt was configuration that looked right.

---

## 5. Decisions

1. **Identity before anything.** Nothing downstream is worth building on an unidentified score, and every
   score written before Phase 1 lands is ambiguous forever. This is the ordering the RV3 salvage ruling asks
   for and it is not negotiable for convenience.
2. **The measure set is the starting point, not the thing being thrown away.** The seven measures, their
   closed label sets, `not_evaluated`, the session grain and the contamination guard are kept as designed.
   This project adds no new measures.
3. **Subject identity and judge identity are separate.** Both live on a score; neither substitutes for the
   other. This resolves §2.3 row 3 against 7.3's flat column list.
4. **RV3's identity beats 7.3's column list** where they disagree; 7.3's list is a floor (§2.3 row 1).
5. **(Rewritten per plan-review C1 — the original sentence was self-contradictory once run id joined the
   tuple.)** Two named things, one derivation: the **score identity** (subject + judge + run id) names a
   score; the **idempotency key** is the score identity **minus the run id** and decides whether the
   score already exists. The key is derived from the identity by dropping exactly one field, so the two
   cannot drift; a re-run differing only in run id is the same score (replace), any other difference is a
   new score (append).
6. **Prompt identity is derived, not declared.** A hash of the prompt actually sent, so editing a judge prompt
   cannot silently reuse an old identity.
7. **Phoenix is the workbench; `eval_results` is the record of account.** Both are written by the same run,
   tied by run id. Neither is reconstructed from the other afterwards.
8. **Residency is inherited, not implemented** (§2.2) — except the exporter-side refusal in 7.6, which no
   merge phase claimed and which this project therefore owns.
9. **A mocked boundary is not acceptance.** Where only a live run can prove something, the plan says so and
   the phase carries a recorded operator step instead of a test that proves nothing.
10. **Reuse before authoring.** The identity vocabulary, the correlation ids, the citation structures, the
    read-only reporting role, the document renderer, the e2e evaluation sets and the compose smoke all exist.
    This project wires them together; it should be writing very little that is genuinely new.

---

## 6. Findings measured while writing this plan (not in the source documents)

Each was read in the tree on 2026-09-20; P0.6 verdicts recorded 2026-09-23 against `9debf188`.

1. **CONFIRMED — the judge factory falls through to an answer-relevance classifier.** `_build_evaluator`
   special-cases groundedness, trajectory and failure-recovery, then returns an answer-relevance classifier
   for *everything else* (`phoenix_adapter.py:347-358`), stamped under the **requested** name (`:275`). A
   misspelled or unhandled measure name therefore gets scored by the wrong judge under the requested name.
   The closed label sets backstop only KNOWN names — an arbitrary unknown name has no entry in the label
   map, so relevance labels pass validation. *P0.6 nuance: the **session** factory does NOT share the
   defect — it raises `ValueError` on an unsupported evaluator (`phoenix_adapter.py:443-444`); P5.3 is a
   per-turn fix.* **Owned by P5.3.**
2. **CONFIRMED — session evaluation has no idempotency check at all.** Per-turn skips on
   `evaluator_identity` ∈ `existing_evaluator_identities` (`runner.py:51-53`, `:66-72`; the key is still
   exactly `annotation_name:evaluator_version`, `contracts.py:371-375`); the session path queues every
   judge unconditionally (`session_runner.py:40-52`) and `SessionEvaluationCandidate` has no
   existing-identities field at all. *Nuance: the session sink publishes with a stable identifier so
   Phoenix upserts rather than duplicates — the judge is still re-paid every run.* **Owned by P1.4.**
3. **CONFIRMED — the evaluation tests import the package directly.** All five files (four pre-G.13 files
   sum to 2,754 lines ≈ the plan's ~2,800; the fifth is the merge-added residency test); none uses the
   dynamic loader. P0.3 measured the cost: ~1–4s/file over the 2s rule plus the `POSTGRES_DB` env-var
   friction — real but modest; conversion is opportunistic-when-touched, mandatory for new files.
4. **CONFIRMED — the contamination guard is in the trajectory prompt, not the recovery prompt.** The
   sentence "Do not re-score factual groundedness." sits only in the `agent_trajectory_quality` template
   (`phoenix_adapter.py:317`); the recovery prompt and both session prompts carry no equivalent. The SDD
   note's placement is wrong; the recovery prompt may want the same sentence.
5. **REFUTED — overtaken by the merge. The per-turn analytics projection now HAS production writers.**
   `chat_turn_facts` is written at block-save time — `ChatHistoryBlocksMixin.save_block →
   _write_chat_turn_facts` (`blocks.py:769-778`), full projection **including `citation_count` and
   `cited_documents`** (`chat_turn_facts.py:467-535`) — plus a settle-time placeholder writer
   (`turn_facts.py:112`, wired through the agent pipeline per M-FACTS-FAILURES), with the old backfill
   demoted to gap-fill (`chat_turn_facts.py:24-28`). Q2's premise is updated accordingly: the projection
   is no longer empty-in-production by construction.

---

## 7. Open questions — owner-owed

**Gating, corrected 2026-09-23 (plan-review C4 — the old sentence was wrong in both directions):**
**Q1 gates Phase 1/2 COLUMN SEMANTICS** — TA proceeds on the working assumption (model profile), accepted
as rename-risk **only if the owner confirms by the TA+TB review**; a late "backend profile" answer after
rows exist re-semantics judge-paid scores, not just a name. **Q2 blocks Phase 4** (default ruled, C12
clause below). **Q5 blocks P5.6 and Phase 9.** **Q10 blocks P6.7.** Q8 is advisory (patch declined by
default). Q3, Q4, Q9 are answered.

- [x] **Q1. What does `profile` mean in 7.3?** **OWNER RULED 2026-09-23: model profile** (matching the
      per-call ledger vocabulary). TA's columns are correct as briefed; the re-semantics risk is closed.
- [x] **Q2. OWNER RULED 2026-09-23: "simple table is fine for now" — the `chat_turn_facts` projection is
      the citation source, consciously superseding the M-EVALS wording ("structured citation offsets");
      the spans path stays in §10 for any future offsets-needing measure. TB is unblocked.**
      **AMENDED 2026-09-25 (owner D2, `docs/plans/eval-quality-gaps.md`):** citation state travels on the
      content copy and `citation_coverage` v3 reads it there; `chat_turn_facts` stays the analytics projection.
      *(Original question, kept for the record:)* Where should citations come from for the rewritten
      measure — the structured spans (authoritative,
      needs a new span attribute and a redaction decision) or the per-turn analytics projection (already
      stores citation count and cited documents, needs no telemetry, but has no production writer)?
      *Checked:* both exist in the tree; the projection's own documentation states the writer is still owed.
      **P0.4 UPDATE 2026-09-23: the premise flipped — `chat_turn_facts` now has a production writer that
      fills `citation_count`/`cited_documents` on every block save. The projection is now the cheap AND
      populated option; the spans remain more authoritative (offsets, per-citation structure) but need new
      telemetry plus a redaction decision. Recommendation at Phase 4 time: projection first, spans only if
      the measure needs offsets. CAVEAT (plan-review C12): taking the projection consciously AMENDS the
      ruled M-EVALS disposition's letter — "rewrite citation_coverage against the structured citation
      offsets" — it is not a neutral either/or. Controller default = projection (ledgered); the owner
      ratifies or vetoes this specific relaxation at the TA+TB review.**
- [x] **Q3. Does the merge's residency enforcement meet §2.2's five bullets?** **ANSWERED by P0.2
      (2026-09-23, §9):** bullets 1 (fail-closed), 2 (pre-fetch) and 4 (session path) **MET**; bullet 3
      **PARTIAL** — only the two banner-admitted code-level residuals (plus two same-class variants, see
      Q8); bullet 5 **PARTIAL** — per-deployment config is met and richer than the banner, **per-tenant is
      absent** and is this project's own build (see Q9). The shipped control is wider than the banner:
      per-cloud catalogues, a narrow-only env allowlist, endpoint-host pinning with proxy/TLS/userinfo
      refusals, an AST guard over `LLM(` sites, and a runbook-parsing guard test.
- [x] **Q4. What happens to annotations already written without identity?** **ANSWERED by P0.5
      (2026-09-23, §9): none exist.** No Phoenix ever ran on the dev box; no remote endpoint exists in any
      repo; the colleague's own plan records live-Phoenix compatibility as never verified, and the evals
      package was installed in no environment. No purge/quarantine decision is needed. *Optional
      belt-and-braces: a 30-second annotation-count check on the POC EC2 box's Phoenix, the one surface
      not visible from here.*
- [x] **Q5. Which judge provider and model are approved** for a first live run? **OWNER RULED 2026-09-23:
      Bedrock with the runbook's pinned Haiku judge — "fine for now but should be swappable easily."**
      The swappability condition is met by design and must stay that way: provider and model are per-run
      CLI parameters validated against the allowlist, with NO default hard-coded in code; swapping = a
      different flag value plus the runbook guard's catalogue check. Any task that would bake a provider
      or model constant into the eval code violates this ruling.
- [x] **Q6. Does a customer ever see the per-tenant quality report unprompted?** **OWNER RULED 2026-09-23:
      on-request.** No scheduling work in 7.5.
- [x] **Q7. Golden sets.** **OWNER RULED 2026-09-23: reuse the existing end-to-end evaluation sets** —
      "fine for now, we might change those later." Dataset push (P6.2) must key datasets stably so a
      later re-curated set replaces cleanly rather than duplicating.
- [x] **Q8 (new, from P0.2). Disposition of the bullet-3 residuals.** **OWNER RULED 2026-09-23: close the
      two cheap seams** (validate an injected evaluator's provenance so a pre-bound vendor object is
      refused — covering the post-construction `_evaluator` mutation variant too; gate or drop
      `run_phoenix_evals.main`'s factory kwargs). Owned by **P5.10** (TC2 — same files as the factory
      refusal work). The two protocol-level residuals the banner accepts (a caller implementing the
      judge protocol against the runners directly) remain reviewer-caught — they are the API's shape.
- [x] **Q9 (new, from P0.2). Which phase owns the per-tenant judge allowlist?** **ANSWERED 2026-09-23 —
      NEITHER (plan-review S3, reversing the controller's first recommendation to fold it into Phase 8):
      it is speculative — no consumer exists; eval runs are operator-driven per deployment and the
      shipped per-deployment control covers actual operation. Moved to §10 as an owner-decision Future
      Improvement; §8's "does not implement judge-side residency" sentence now carries the reconciling
      note. If a multi-account deployment materializes, the work resumes from §10.**
- [x] **Q10 (new, from plan-review C3). Tenancy of synthetic/golden-set eval rows.** **OWNER RULED
      2026-09-23: reserved internal tenant id** — one id, RLS machinery unchanged, no nullable-tenant
      special case in any reader. P6.7 is unblocked; synthetic rows carry the reserved id and land in
      the `internal` Phoenix project via the harness-path validator relaxation.

---

## 8. What this project deliberately does NOT do

- **It does not implement the judge-side provider allowlist / residency.** That is the current merge's
  deliverable and this project's precondition (§2.2). It verifies it and names gaps; it does not widen it and
  does not re-litigate the ruling. *(Reconciled 2026-09-23, plan-review S3: this sentence and §2.2's
  "building the per-tenant half is this project's work" contradicted each other. Resolution: THIS sentence
  wins — per-deployment enforcement stands, the per-tenant half is deferred to §10 as an owner decision,
  and Q9 records why.)*
- **It adds no new measures.** Seven exist, they are well chosen, and an eighth before the first seven are
  trustworthy would be scope disguised as progress.
- **It does not curate new golden sets or build a curation UI.** It reuses the department evaluation sets that
  already exist.
- **It does not judge anything in the request path.** Evaluation is offline, over traces, after the fact.
- **It does not replace the existing end-to-end harnesses or retrieval sweeps.** They answer different
  questions and keep answering them.
- **It builds no customer-facing evaluation UI.** Phoenix is the workbench, and the per-tenant report is the
  customer-facing artefact.
- **It does not rebuild what the merge already shipped** — the content copy, the sampling, the per-tenant
  capture policy, the collector alias fragment, the Phoenix overlay. Phase 3 verifies and closes; it does not
  re-implement.
- **It does not schedule the content-capture purge.** That is a named owner decision on the merge plan, and
  taking it here would split one decision across two projects.
- **It does not touch Rostering, or any product area outside agent answer quality.**
- **It does not chase the pre-existing red architecture test** noted on the merge plan as red before the
  merge and in no phase's lane.

---

## 9. Implementation notes

*(Written while implementing each phase, not after: what was actually done, deviations from this plan, and
why.)*

### Phase 0 (started 2026-09-23) — inventory results

**P0.1 (first half, controller-measured).** The merge closed and pushed 2026-09-23. The evals code sits on
the **primary checkout** `/home/aditya/Code/copilot-mro`, branch **`langgraph-merge`**, commit
**`9debf188`** — the certified push SHA; tree clean. All Phase 0 evidence below is pinned to that commit.
The §1.1 / §1.3 claim-by-claim walk ran as a separate read-only Fable lane (results below when filed).

**P0.2 — residency five-bullet walk (Fable audit lane, adversarial). Verdict: bullets 1, 2, 4 MET;
3 and 5 PARTIAL, both exactly the gaps the §2.2 banner already admits; no new hole class found.**
The shipped control is materially *wider* than the banner describes: besides `IN_ACCOUNT_JUDGE_PROVIDERS`
(`contracts.py:64`, frozenset azure/bedrock/ollama) there is a per-cloud catalogue
(`IN_ACCOUNT_JUDGE_PROVIDERS_BY_CLOUD`, `contracts.py:72-76`; cloud from `EVAL_JUDGE_DEPLOYMENT_CLOUD`,
default `aws`), a narrow-only deployment env `EVAL_JUDGE_PROVIDER_ALLOWLIST` (widening refused,
`contracts.py:159-182`), endpoint-host pinning per provider including botocore shared-config resolution,
TLS-scheme / userinfo / proxy-env refusals (`contracts.py:102-335`), and an AST guard failing any new
`LLM(` site in the package + `scripts/observability` whose provider is not validator-bound.

| bullet | verdict | evidence |
|---|---|---|
| 1 fail-closed | **MET** | `validate_judge_provider` `contracts.py:338-358` refuses None/blank/unknown; CLI `--provider` `required=True`, **no default** (`scripts/observability/run_phoenix_evals.py:132`); both judge `__init__`s gate (`phoenix_adapter.py:260`, `:378`) |
| 2 pre-fetch | **MET** | all four per-turn judges built before `fetch_candidates` (`run_phoenix_evals.py:58-81`); proved by `test_a_refused_run_fetches_no_candidates` (residency test `:567-604`, source called 0×). Session judges built post-fetch but from the same already-validated provider/env; the pre-`LLM` re-check (`phoenix_adapter.py:413`) still blocks a mid-run env mutation |
| 3 library entry points | **PARTIAL** | direct construction gated in `__init__` and re-gated in `_build_evaluator` ahead of the `phoenix.evals` import and `LLM(...)` — the only two `LLM(` sites repo-wide. Open residuals = exactly the banner's two, plus two same-class variants: post-hoc `judge._evaluator = <vendor-bound obj>` (gated for `_provider`, not `_evaluator`), and `run_phoenix_evals.main(judge_factory=…)` — a Python-only injection seam replacing the gated factories |
| 4 session path | **MET** | separate class `PhoenixSessionJudgeEvaluator` gates `__init__` `:378` + `_build_evaluator` `:413` before import/`LLM`; inside AST-guard coverage |
| 5 per-deployment / per-tenant | **PARTIAL** | per-deployment MET and richer than the banner (cloud env + narrow-only allowlist env + endpoint declaration). **Per-tenant ABSENT** — nothing tenant-scoped anywhere; the tenant project string is shape-validated only. Building the per-tenant half is this project's work, per the banner |

Adversarial call paths: CLI openai / unset provider / vendor-endpoint + proxy-env / http downgrade /
post-hoc `_provider` mutation — all BLOCKED pre-fetch or pre-SDK-import. Only the two admitted residual
shapes (injected pre-bound evaluator; protocol-implementing caller hitting the runners directly) reach a
vendor with content. `scripts/certify_model_profile.py --provider openai` is a different subsystem — no
`phoenix.evals` import, no judge content; not a residency path.
Runbook: **zero** `--provider openai`; every copyable invocation is `--provider bedrock`. The guard test
(`test_judge_provider_residency.py:703`) genuinely **parses** the runbook (regex over `--provider` values,
non-vacuity assert) and resolves them against the *default-cloud* sub-catalogue — stricter than the full
catalogue; a companion guard pins the runbook's `--model` values to the configured judge-model default.
One factual drift corrected in the §2.2 banner: the constant is at `contracts.py:64`, not `:56`.

**P0.3 — test timing baseline (controller-run, `pytest-slot.sh`, shared api env, `DEBUG=false
POSTGRES_DB=copilot_mro_test`).** All green; **every file breaches the 2s rule → package init is firing**,
confirming §6 finding 3. Collection even *refuses* without `POSTGRES_DB` named (the protected-database
guard fires during import), which is itself proof the settings/DB path initialises at import time.

| file | tests | pytest time |
|---|---|---|
| `test_phoenix_evaluation_adapter.py` (1555 ln) | 30 | 3.32s |
| `test_agent_evaluation_runner.py` (653 ln) | 25 | 3.05s |
| `test_agent_session_evaluation_runner.py` (157 ln) | 4 | 2.71s |
| `test_phoenix_evaluation_cli.py` (389 ln) | 5 | 2.90s |
| `test_judge_provider_residency.py` (758 ln, merge-added) | 104 | 6.46s |

Reading: overhead is ~1–4s/file plus the env-var friction — real but modest. Converting wholesale is
bookkeeping; the standing decision is that **new** eval test files follow the loader rule and existing
ones convert opportunistically when touched. (Revisit only if a phase's inner loop makes the 15s total
sting.)

**P0.5 (local half, controller-measured).** No Phoenix container (running or exited) and no Phoenix volume
has ever existed on this box; no live env file sets any `PHOENIX_*` or content-copy variable (the repo
`.env` carries neither; only `.env.sample`s do). So **no colleague annotations exist locally**. Note for
P3.2: `deployment/.env.sample` now ships the Phoenix secret placeholders with the ≥32-char warning — the
"stack demands secrets with no sample env" concern looks addressed, pending the actual boot check.
Remote-endpoint references were swept by the P0.1 lane (below).

**P0.1 (second half — §1.1/§1.3 claim walk, Fable verification lane). Every row and bullet CONFIRMED;
two line-number drifts corrected in place** (§1.1 row 1 `:17`→`:21-37`; §2.2 banner `:56`→`:64`; the
pre-G.13 `LLM(provider=...)` sites cited in the dated STATUS CORRECTION paragraph now sit at
`phoenix_adapter.py:298`/`:416` and are validator-preceded — left as history, superseded by the banner).
Highlights with evidence anchors: seven measures + `not_evaluated` (`contracts.py:21-37`, label
enforcement `:679-686`); `ANNOTATOR_CODE`/`ANNOTATOR_LLM` (`contracts.py:14-15`; citation is the code path,
`runner.py:199-224`); session types (`contracts.py:468-523`) + `session_runner.py` (186 ln); contamination
guard sentence confirmed **in the trajectory prompt** (`phoenix_adapter.py:317`) — §1.1's placement was
right, the SDD note's wrong (§6.4); failure isolation + failure id + 1..16 concurrency
(`runner.py:152-179`, `:299-313`), mirrored in the session runner; collector fragment routes
`tenant-<id>` + `internal` (`content-phoenix.yaml:23-31`); overlay image-pinned
`arizephoenix/phoenix:version-20.8.0`, auth on, retention env, UI loopback
(`docker-compose.phoenix.yml:18-27`); base compose has **zero** Phoenix references; the 7.1 acceptance
smoke exists at `tests/integration/otel/test_oss_profile_smoke.py` (posts `phoenix-connected-smoke` `:207`
and two-tenant `phoenix-routing-smoke` `:229`, **already reads spans back** via
`/v1/projects/<project>/spans` and checks `internal` isolation — a head start on P3.5), gated by
`compose_stack` + `OTEL_COMPOSE_SMOKE=1`; sampling (sha256 row-hash bucket) + per-tenant
`llm_content_capture_enabled` policy both gate the copy, collector keeps only app-marked copies
(`base.yaml:238-249`); identity vocabulary proven on `llm_model_calls`, spans and content copies. **One
naming note:** the "turn" correlation id IS `block_id` — the estate's turn key; there is no separate
turn-id attribute. Phase 1's subject identity should say `block_id` and not invent a turn id.

**P0.4 (Fable verification lane).** `eval_results`: **still absent** — repo-wide grep zero matches, no
evaluation relation under any name in the table-definition modules. The per-turn analytics projection is
`chat_turn_facts`, and it **gained production writers** (save-block full projection including
`citation_count`/`cited_documents` at `blocks.py:769-778` + settle-time placeholder writer; backfill
demoted to gap-fill). §6 finding 5 REFUTED as overtaken; Q2's premise updated.

**P0.5 (remote half — completion).** The repo contains **no concrete remote Phoenix endpoint anywhere**:
runbook uses placeholders only; env examples point at the in-stack `http://phoenix:6006`;
`iac/demo_ec2_setup.sh:75-76` explicitly leaves `PHOENIX_ENDPOINT` unset ("when the owner supplies one,
append it"); the otel-gateway module's Phoenix wiring is optional and never fed. Strong documentary
evidence no live eval run ever executed: the colleague's own plan records live Phoenix compatibility as
"unverified until a safe non-production Phoenix endpoint is available"
(`2026-09-17-phoenix-trace-evaluations.md:120`) and `contracts.py:61-63` records the evals package
"installed in no environment here". **Verdict: no identity-less annotations exist; Q4 answered.** The one
surface not checkable from this box: the POC EC2 setup does boot a Phoenix (it generates
`PHOENIX_SECRET`/admin password, `iac/poc_ec2_setup.sh:185-191`) — it may hold **traces**, but an
annotation would require an eval run no environment could have executed. A 30-second owner spot-check of
that box's Phoenix annotation count is optional belt-and-braces, not a blocker.

**Dry-run defect re-confirmed** (§1.2 item 5): `--publish` (`run_phoenix_evals.py:135`) gates only the
annotation write (`runner.py:282-283`); judges run unconditionally for every non-skipped item; the report
labels the full-cost mode `dry_run` (`:211`) and the runbook still calls dry-run the default. One
phrasing correction: identity-skips and `not_evaluated` short-circuits do avoid judge calls — but within
a fresh run, "dry" pays exactly what publish pays. P5.1 stands as written.

**Review protocol note for this phase:** Phase 0 produced no code — its deliverable IS the adversarial
verification, run as two independent read-only Fable audit lanes (per the standing review-trust ruling
that verdict lanes run on Fable). No separate post-phase reviewer was spawned; the phase-exit gate is the
owner reading this inventory.

### Phase 5 (task TC2) — implementation notes (landed 2026-09-23)

Landed on `agent-evals-tc2` (BASE e9b4a4ed, commits `5f583244`…`d89c68de`), merged at `665cb745` (one
union conflict, the shared test loader) with the controller integration commit `fdca9cb5` on top
(run mode wires `PostgresCitationFacts` over the run's owner connection + the two merge-seam test
updates). Full report: `.superpowers/sdd/agent-evaluation-completion/task-TC2-report.md`.

- P5.1/P5.2: CLI has exactly two modes — `plan` (default, zero provider calls, proved by a raising
  judge double) and `--mode run` (requires an explicit `--database`; judges + publishes + persists);
  `planner.py` added; reports carry `judge_calls` / `judge_calls_skipped`.
- P5.3 unknown-measure refusal before any identity is built; P5.7 contamination-guard sentence in the
  recovery + both session prompts; P5.9 runbook updated; P5.10 injected vendor-bound evaluators
  refused (build-time AND after-swap) and the `judge_factory`/`session_judge_factory` seam dropped
  from `main`; P5.11 (review scope-add) a `not_evaluated` annotation never suppresses re-evaluation,
  turn + session paths.
- P5.8/P1.4: the session path skips, publishes and persists on the idempotency key;
  `evaluator_identity()` retired. **Grown-session ruling (TC2, controller-ratified):** the sorted set
  of turn block ids is part of the session subject — a session that gained turns is scored again and
  the new score sits beside the old one.
- **The live boundary test (P5.4/P5.5) found five real Phoenix-boundary bugs the mocked suite could
  not see** — the phase's whole point, vindicated: real Phoenix nests root attributes as dicts (so
  every real candidate had block/chat/department = None — TB's citation join could never have matched
  before `420e7fb2`); evidence passages arrive as `cited_text` (groundedness was never judged on a
  real turn before `efe44e5d`); the session sink posted a GlobalID Phoenix 404s (now `session.id`);
  session listing paged oldest-first dropping recent sessions (now by-id lookup); clients are reused
  instead of rebuilt per call.
- Tests: 320 unit across touched files; compose lane 9/9 incl. the new live boundary test (eval rows
  cleaned up after); db+registry 11/11; 13/13 targeted mutants caught; broad lane clean but for TA's
  two known environment reds.
- Owner items from TC2: `cited_text` now counts as judge evidence (veto point — it is the cited
  passage already in the tenant's Phoenix project); whether the shared api env should carry the eval
  dependency group (`arize-phoenix-client` — the live test skips there today and names the fix; TC2
  ran it via a scratch-dir PYTHONPATH, shared env untouched).
- Controller ruling: the library-level `publish=False` parameter on `evaluate_candidates` STAYS (TC2
  proposed deleting it) — P5.1's letter targeted the CLI boundary, which now has exactly two honest
  modes; the library kwarg is the unit tests' seam for judging without a Phoenix double, and no
  operator path reaches the library except through the CLI. RB-B may challenge.

### Phases 1+2 (task TA) — implementation notes (landed 2026-09-23)

Landed on `agent-evals` (BASE 9debf188, commits `9f1e0fdf`…`dd78b53f`). Full report:
`.superpowers/sdd/agent-evaluation-completion/task-TA-report.md`. Mutation log:
`~/.claude/scratch/copilot-mro/agent-evals-TA/`.

- **Score identity** = `SubjectIdentity` (tenant, department, profile, profile_revision,
  registry_revision, trace, span, session, block, chat — reused vocabulary, no invented turn id) +
  `JudgeIdentity` (annotation name, evaluator version, annotator kind, judge provider, judge model,
  prompt hash) + `run_id`. **Idempotency key** = sha256 of the canonical field JSON with exactly
  `run_id` deleted — one derivation shared by runner, Phoenix sink (annotation `identifier`) and
  Postgres (PK `(tenant_id, idempotency_key)`), so the two things cannot drift.
- Skip decision widened to the key for every judge; legacy `name:version` read-back removed on the
  per-turn path (survives only as the session path's identifier until P5.8/TC2). Prompts declared once,
  hashed as sent (proved byte-identical to base). A judge without a declared identity fails before
  anything is paid.
- **`eval_results`**: tenant-classed, private, RLS + FORCE, readonly SELECT grant; identity
  field-by-field + digest key column (deviation 1: a UNIQUE over ~16 nullable columns silently admits
  NULL duplicates; the digest is the same Python derivation); upsert ON CONFLICT replaces non-key
  columns, run_id moves to the latest invocation; v2-vs-v1 per-measure comparison SQL banked. Failed
  persist = counted failure, never an abort; `copilot_mro_test` migrated + provisioned (dev
  `copilot_mro` deliberately NOT — owner-owed before live harness writes).
- Naming deviations from 7.3's letter: `metric`→`annotation_name`, `judge_version`→`evaluator_version`,
  `created_at`→`scored_at` (a replace re-scores, the timestamp moves with it).
- Acceptance held exactly as specified: per-field parameterized skip/no-skip pairs, 19/19 mutants
  killed (each dropped key field killed by its own case); eval files 258 passed; registry 208;
  db lane 4/4 incl. the v2-vs-v1 query run AS the readonly role. Broad unit lane 7302 passed with 3
  pre-existing environment reds (variant checkouts gone; a gitignored scratch file trips the
  M-TRACEBACK sweep — red at base). 12 SAD db setup errors = pre-existing test-DB drift
  (`data_discovery_jobs.object_count` NOT NULL without the registry's default), not this diff.
- Owner-queued at RB-A: Q1 ratify `profile` = model profile; **where `eval_results.explanation`
  (judge free text, can paraphrase user content, beside session/block/chat ids) sits on the
  M-FACTS-ANONYMISE line** — scrub, delete, or keep on chat delete (it is outside
  `DELETED_CHAT_COPIES` today). **RULED 2026-09-23: profile = the answering model's profile;
  explanation = SCRUB on chat delete (see the §10 bundle record).**

### Phase 4 (task TB) — implementation notes (landed 2026-09-23)

Landed on `agent-evals` (BASE e9b4a4ed, commits `b923256e`…`b546dd4d`), after one NEEDS_CONTEXT round
— the task brief had frozen `runner.py`, where the whole old measure lived; controller unfroze exactly
three hunks and ruled on labels/fixtures (rulings in the SDD ledger). Full report:
`.superpowers/sdd/agent-evaluation-completion/task-TB-report.md`; capture scripts under
`~/.claude/scratch/copilot-mro/agent-evals-TB/`.

- New `agent_evaluation/citation_coverage.py`: the constants (version bumped there — TA's single
  declaration moved with them, re-exported from `runner.py`), the facts-lookup protocol,
  `PostgresCitationFacts(connection)` (tenant bound per transaction under FORCE RLS, locked for the
  judge thread pool, autocommit refused — it would silently read every turn `not_evaluated`), and the
  evaluator. Bracket heuristic deleted; zero turns scored from answer text (answer-invariance tested).
- Source of truth = `chat_turn_facts` join on (`tenant_id`, `block_id`) per Q2; db test proves the
  join under FORCE RLS on a real cluster.
- **Labels (owner veto point at RB-A):** `fail` only for retrieved-evidence-and-cited-nothing; `pass`
  for cited turns and for no-citation turns that asked a clarifying question or retrieved nothing
  (this last replaces the old `not_evaluated` reading — revert = one line + one test row, mutant-
  proved); `not_evaluated` only for unresolvable state. Label table lives on the evaluator docstring.
- Fixtures: real chat blocks run through the production projection `facts_from_block_data` (dev
  `chat_turn_facts` measured EMPTY — P0.4's writers only fill blocks saved after they landed);
  adversarial case (a) uses a real citation-less facts row + a hand-written answer labelled synthetic
  in the fixture (the measure never reads answer text); case (b) real (63 such turns); 45 legacy
  inline-`[n]` blocks excluded with reason in the fixture `_provenance` (they predate the content
  copy and can never become candidates).
- Both adversarial flips proved and mutation-proofed (10/10 killed at HEAD); eval unit files 312,
  registries 192, db lane 8 — all green; broad-lane 3 reds = TA's known environment reds.
- Owed post-merge by the controller: the one CLI run-mode line
  (`citation_facts=PostgresCitationFacts(connection)` on the eval_results owner connection) — until
  it lands, real runs label citation_coverage `not_evaluated`.

### Phase 3 (task TC1) — implementation notes + probe table (landed 2026-09-23)

Landed on branch `agent-evals-probe` (BASE 9debf188, commits `eaaf3219`/`10a1de2d`/`4570aea9`/`e86c9338`),
pending merge into `agent-evals` once TA frees the primary tree. Full report incl. the exact env/command
re-run recipe for a Phoenix version bump: `.superpowers/sdd/agent-evaluation-completion/task-TC1-report.md`.
Evidence artifacts: `~/.claude/scratch/copilot-mro/tc1-phoenix-probe/`.

What the live probe (4 real agent turns, Bedrock, Phoenix 20.8.0, auth on, tenant project
`tenant-17be5d65-…`) established:

- **Phoenix ≥20.x converts `gen_ai.*` to OpenInference itself at ingest, with `setdefault` — the
  collector's aliases WIN.** Total tokens and cache-read tokens render natively with no alias; the smoke
  now guards them against an image bump.
- **Both P3.4 suspects CONFIRMED wrong and removed:** the invocation-parameters and output-messages
  aliases put v2 `content_ref` *pointers* under keys that mean request params / a message list — wrong
  panels, not missing ones. No source for either exists in a content copy, so absent is correct.
- **Three collector fixes added:** cache-write alias (app writes `cache_write`, semconv reads
  `cache_creation` — was null, now renders); `session.id ← gen_ai.conversation.id` (see ruling below);
  JSON mime type on JSON bodies (rendered as raw text before).
- **Session-grain ruling (controller, 2026-09-23; owner ratifies at RB-B):** a Phoenix session is now a
  *conversation*, not a browser correlation id. Measured before the fix: one browser session held two
  unrelated chats (firstInput from chat A, lastOutput from chat B). Plan §1.1's session measures are
  conversation-grain and Phoenix's own native conversion makes the same mapping. The browser id stays on
  `flynapse.session_id`. Downstream: the eval adapter's session extraction and TC2's session-path tests
  see chat ids. Revert cost if the owner overrules: one fragment statement + the smoke's session rows.
- **P3.7:** local `deployment/.env` (untracked, mode 600) sets
  `COMPOSE_FILE=docker-compose.yml:docker-compose.phoenix.yml`; the sample documents the line commented
  (observe/poc stacks copy the same sample); base compose stays Phoenix-free. The dev-stack SKILL.md half
  was skipped — it documents no compose bring-up command, so there was nothing to amend.
- **P3.1 discrepancy:** rebuild task 11.4 was already `[x]`; only the evidence line was added (uncommitted
  — the workspace `docs/` repo has no commits yet).
- Verification: compose smoke 8 passed; 4/4 fragment mutants killed; otel lane + layout guards 277
  passed / 27 skipped; `validate.sh oss` incl. the aws+phoenix composition passed.

**Probe table (P3.6)** — Phoenix `version-20.8.0`, collector-contrib `0.160.0`, measured 2026-09-23.
"Before" = fragment at 9debf188 (traces A1/B1); "After" = fragment at `10a1de2d` (traces C1/C2, one chat).
UI surface = the Phoenix GraphQL field backing the panel (browser evidence not captured; GraphQL allowed
by the brief).

| # | Attribute | Expected | Before | After | UI surface | Verdict |
|---|---|---|---|---|---|---|
| 1 | Span kind | AGENT root; LLM/TOOL/RETRIEVER children | correct | same | `Span.spanKind` | rendered |
| 2 | Span tree | children under `invoke_agent claude` root | yes; tool spans hang off the AGENT root, not the SDK LLM span that issued them | same | `Span.parentId`, `Trace.numSpans` | rendered (tree-shape note) |
| 3 | Model | `llm.model_name` | full Bedrock model ids on root + lifecycle spans | same | `Span.attributes.llm.model_name` | rendered |
| 4 | Provider | `llm.provider` | raw `aws_bedrock` (not an OpenInference well-known value) | same | `llm.provider`, `llm.system` | rendered, raw vocabulary → gap G4 |
| 5 | Tokens on LLM spans | prompt/completion per call | lifecycle spans yes; **`claude_sdk_turn` 0/0** — app emits no usage on the SDK-loop span | same | `Span.tokenCountPrompt/Completion` | partial → gap G1 (app) |
| 6 | Tokens on AGENT root | turn usage | attributes present; Phoenix sums LLM descendants only (`cumulativeTokenCountTotal`) | same | `Span.cumulativeTokenCountTotal` | Phoenix design |
| 7 | Total tokens | `llm.token_count.total` | Phoenix-native (input+output), no alias needed | same | `llm.token_count.total` | rendered (native at 20.8; smoke-guarded) |
| 8 | Cache-read tokens | prompt details | Phoenix-native from semconv name | same | `Span.tokenPromptDetails.cacheRead` | rendered (native) |
| 9 | Cache-write tokens | prompt details | **null** (app name `cache_write` vs semconv `cache_creation`) | **15,230** | `Span.tokenPromptDetails.cacheWrite` | **FIXED** (alias) |
| 10 | Cost per span | spend per call | Phoenix prices tokens × its own table, ignores `llm.cost.total`; lifecycle spans exact; `claude_sdk_turn` null | same | `Span.costSummary` | partial → G1 |
| 11 | Cost per trace/session | turn spend | **$0.0032 shown vs $0.2126 real (~1.5%)** — dominant spend is on the token-less SDK span | same | `Trace.costSummary`, `ProjectSession.costSummary` | under-reported ~98% → G1 |
| 12 | Tool name | `tool.name` | full MCP tool names; span name `execute_tool <name>` | same | `tool.name`, `Span.name` | rendered |
| 13 | Tool id | `tool.id` | `toolu_bdrk_…` on every tool span | same | `tool.id` | rendered |
| 14 | Tool error status | failed call marked | (no failure in A1/B1) | failed `db_query` → `ERROR` | `Span.statusCode` | rendered |
| 15 | Input body (root) | redacted turn input | JSON string, mime **text** | mime **json** | `Span.input{value,mimeType}` | **FIXED** (mime) |
| 16 | Output body (root) | redacted turn output | JSON string, mime **text** | mime **json** | `Span.output{value,mimeType}` | **FIXED** (mime) |
| 17 | Child bodies | per-call input/output | mixed text/json | all json | `Span.input/output` | **FIXED** |
| 18 | Invocation parameters | absent (content copies carry none) | **WRONG:** `content_ref` pointer rendered as request params | absent | `llm.invocation_parameters` | **FIXED**, suspect confirmed (G6: none captured anywhere) |
| 19 | Output messages | absent (body is `output.value`) | **WRONG:** `content_ref` pointer rendered as a message list | absent | `llm.output_messages` | **FIXED**, suspect confirmed |
| 20 | Session grouping | one Phoenix session per conversation | **WRONG grain:** session = browser `X-Session-ID`; one session held 2 unrelated chats | session = chat id, exactly its own traces; browser id kept on `flynapse.session_id` | `Trace.session`, `getProjectSessionById` | **FIXED** (ruling above) |
| 21 | User | `user.id` | rendered | same | `Span.userId`, `ProjectSession.userId` | rendered |
| 22 | Retriever documents | Documents panel with cited evidence | `numDocuments=0`, no query captured; evidence only as output JSON text | same | `Span.numDocuments`, `Span.input` | gap G3 (app) |
| 23 | Project routing | `tenant-<id>` | correct tenant project | same | `Trace.project.name` | rendered (`internal` isolation smoke-covered) |

Rows only the live run could prove (real app span shapes + real persisted content): 2, 5, 6, 10, 11, 14,
20, 22. The smoke asserts the collector-mapping rows (7–9, 15–20) against synthetic spans shaped like the
real ones.

### TE (Phase 8) — implementation notes (2026-09-23)

Head e821ca20 on `agent-evals-te` (base f6192987; commits 0c0be20c, 2a621355, 8af67f1f, 25aa4680,
e821ca20). "Same account" became a checkable property in `deployment/otel/check_residency.py`,
wired into `validate.sh` so every validated composition is residency-checked; a cross-account
content exporter is refused with a message naming the endpoint (decoy proof enforced on every
validate run), and an operator mode (`--residency-env`) checks a deployed box's env file — it
refuses a cross-account file and passed the running dev collector read-only. P8.4 held the
exporter rule and the frozen judge rule to identical verdicts via differential corpora
(30 endpoints + ~170-combination grid + proxy table); its one real gap (harness Phoenix client
never host-checked) is §10-deferred by ruling. P8.1 was cited, not re-tested (stateless gate
checked before sampling). Review RB-D lane 1: spec ✅, quality APPROVED, 0 MAJOR; fix round 1
(e821ca20) closed TE-1 (ipv4_mapped unwrap, old-interpreter behaviour reproduced in-test) and
TE-2 (refusal wording split); scoped Opus re-review: both ADDRESSED, no new findings, lane closed.
128 residency tests + 16/16 aimed mutants killed; scope-guard allowlist gained exactly the one
controller-unfrozen entry.

### TM (pre-TF micro-task, ratified item 5) — implementation notes (2026-09-23)

Head 7be5b2a2 on `agent-evals-tm` (base f6192987; commits 6ed94fa5, 7be5b2a2). The
`claude_sdk_turn` span now carries `gen_ai.usage.*` (input = uncached + cache_read + cache_write
per G2, cache buckets in the file's existing vocabulary) from the same `summarize_usage` mapping
its cost already came from — no counts rather than zeros when no ResultMessage was recorded — and
stamps `gen_ai.model.profile`/`registry_revision` from the turn's resolved runtime identity with
the `claude_sdk_turn` label as ruled fallback. The claim-4 residual (SDK loop rides no certified
profile by design, so the fallback shows in production until one is certified) is ruled and
§10-filed; the seam is test-pinned to pick a real profile up with no further telemetry change.
Review RB-D lane 2: spec ✅, quality APPROVED, 0 MAJOR/MINOR; 2092-test lane green, 8/8 mutants.

### TF (Phase 9) — governed live run: first attempt BLOCKED (2026-09-23), paid half DONE (2026-09-24, below)

Branch `agent-evals` from `d447d5e2`: `3283cf1a` (golden-set harness driver + unit test, scope-guard
entry), `7418f67b` (runbook sections), `5e41e91f` (driver/runbook: which tenant it may run under). Nothing was paid; no judge was called; nothing was written
to Phoenix or to any database. Full record: `.superpowers/sdd/agent-evaluation-completion/task-TF-report.md`.

**Subject chosen (P9.1a).** Dev Phoenix holds exactly one tenant project,
`tenant-17be5d65-6192-4ce5-b0db-c06ce577e2c1` (the dev default tenant), and in it exactly four
root turns, 09:26–09:46Z today — the TC1 probe's real turns through the served pipeline, the only
traffic the dev Phoenix has ever received. `default` is empty; `internal` does not exist yet.

**Plan mode, tenant target (free, recorded).** `--project tenant-17be5d65-… --since
2026-09-23T00:00:00Z --limit 50` (anchor absolute; limit above the 4 roots), judge flags `--provider
bedrock --model global.anthropic.claude-haiku-4-5-20251001-v1:0`: selected 4, skipped 0,
**judge_calls 10**, sessions selected 2, session judge_calls 4 → **14 paid judge calls, 24
candidate·measure pairs** (4×5 per-turn + 2×2 session; bound was ≤400). Free verdicts planned: 4
`citation_coverage` (CODE), 3 `groundedness` and 3 `failure_recovery_quality` with no judge call
(no evidence / no failure signal — they will record `not_evaluated`). Subject identity on every
turn: profile `bedrock-classification,bedrock-memory,claude_sdk_turn`, registry revision `pilot-r3`,
department MRO. **Session finding:** of the two sessions, `probe-chat-c-0923` is one conversation
(two turns) but `probe-browser-session-0923` groups two DIFFERENT conversations (A1, B1) — those
traces predate TC1's `session.id ← gen_ai.conversation.id` alias, so Phoenix still sessions them
by the browser id; the session judges would score two unrelated chats as one conversation.

**Plan mode, golden-set target (free, pre-flight).** `--golden-set mro --since
2026-09-23T00:00:00Z --limit 50`: 40 examples, matched 0, unmatched 0 — no harness turn exists yet;
a missing `internal` project plans cleanly to nothing.

**Why the paid runs did not happen — three environmental preconditions, each measured:**
1. **Bedrock credentials.** The app's AWS profile `bedrock` is SSO; its token expired 10:24Z and
   refresh fails. The api `.env`'s `AWS_ACCESS_KEY_ID`/`SECRET` are the `local` DynamoDB-local
   placeholders, not Bedrock credentials. Both the judge and the headless harness turns need a
   fresh `aws sso login --profile bedrock` — an owner action.
2. **The judge library is not in the api env.** The `evals` group carries `arize-phoenix-client` +
   two openinference packages; the model judge imports `phoenix.evals` (`arize-phoenix-evals`,
   locked 3.8.0 in copilot-mro's `evaluation` group) and, for bedrock, `litellm` (1.95.0) at its
   first call. Run mode from the api env would fail every model-judge call as a counted
   `ModuleNotFoundError`. Measured against the two packages' declared dependencies: missing from
   the api env are exactly `arize-phoenix-evals`, `litellm`, `fastuuid`, `jsonpath-ng`,
   `pystache`; every other one is installed inside its range.
3. **`eval_results` does not exist in dev `copilot_mro`.** The earlier `--verify-only` pass was
   true and not sufficient: verify checks the relations a database HAS and reports none it lacks.
   Measured read-only against all three registries: `core` 18/18 present, `shift-optimizer` 7/7,
   `copilot-mro` 89/90 — the one missing relation is `eval_results`. Run mode refuses before
   reading anything; the report script fails `UndefinedTable`. Owed: `migrate_tenancy_schema.py
   --database copilot_mro` (creates exactly that table) then `provision_rls.py --database
   copilot_mro --user postgres`.

**Golden-set path (P9.1b), built and staged.** `scripts/observability/run_golden_set_turns.py`:
each question one real turn through the served pipeline under a named tenant with the
content-copy sample rate forced to 0 (captured, projected nowhere), then the persisted row
projected through the app's own `record_content_copy_span` with the tenant removed — the
collector's own routing puts it in `internal`, the posting path TD's live test proved. No
collector or capture-policy change; ≤10 questions; free `--dry-run`; every paid turn banked before
projection, re-runs re-project without re-asking. 22 unit tests, 10/10 aimed mutants killed
(fix round R1 added the provisional-bank-on-payment property + 3 tests/mutants). Chosen
set and examples (dry-run recorded): `mro` — M01, M05, M09 (AMM), M12, M15, M33 (IPC), M19, M22
(task cards), M24, M27 (SRM), run tag `tf1`, tenant `17be5d65-…`.

**Runbook (P9, TD-filed item).** Sections added for `--golden-set`, the driver and the report
script; three misleading passages corrected (plan example's relative `--since`, the api env's
`evals` group carrying no judge, `--verify-only` not proving `eval_results` exists).

**Not done in the first attempt (all done 2026-09-24 — next subsection):** both paid runs + idempotent re-runs,
P9.2's label and `not_evaluated` distributions and measured cost, the `Trace.costSummary` vs
`llm_usage.sdk_cost_usd` comparison (no tenant-window turn post-dates the TM merge at 13:54:45Z —
the four are 09:26–09:46Z; the golden-set harness turns will be the first post-TM turns), P9.3's
report, P9.4's rebuild ticks.

**Controller status on the three preconditions (2026-09-23, same day):** (2) CLEARED — the api
`evals` group now also carries `arize-phoenix-evals==3.8.0` + `litellm==1.95.0` (installed clean,
same python marker; lock uncommitted for owner review); (3) CLEARED — dev `copilot_mro` really
migrated (1,491 statements committed, `eval_results` and its index now exist; snapshot
`copilot_mro_pre_eval_results.dump` at the workspace root) and provisioned (898 statements, 112
tenant-columned tables verified). (1) REMAINS — `aws sso login --profile bedrock` is interactive
and owner-only. TF resumes by message the moment it clears. The `--verify-only` misread that let
(3) masquerade as done is recorded in `## Lessons`.

### TF (Phase 9) — the paid half: run record (2026-09-24)

**Owner directive (task-TF-brief Amendment 1, binding): "this run is a PROOF, nothing else."** Golden
set: exactly one example (`mro` M01, run tag `tf1`). Tenant run: fewer judge calls by SHRINKING the
`--since` window — never by lowering `--limit` — to the smallest window holding a complete session.
All three preconditions re-verified by TF before any call: `aws configure export-credentials
--profile bedrock` succeeds; `import phoenix.evals, litellm` → 3.8.0 / 1.95.0 from the api env;
`to_regclass('public.eval_results')` non-null in dev (0 rows). Commits this half: `65ca5c95` (runbook).
Judge for every call: `--provider bedrock --model global.anthropic.claude-haiku-4-5-20251001-v1:0`
(per-run flags; nothing hard-coded). Every command ran from `/home/aditya/Code/api` with the primary
tree on `PYTHONPATH`; database `copilot_mro` (dev), Phoenix `http://127.0.0.1:6006` (dev).

**Tenant run (P9.1a).** Shrunk window: `--since 2026-09-23T09:40:00Z --limit 50` — a clean cut in the
11-minute gap between B1 (ends 09:32:36Z) and C1 (starts 09:44:01Z), so the window holds exactly the two
`probe-chat-c-0923` turns: one COMPLETE conversation (it has no other turns), and none of the two
browser-grouped pre-alias turns. Plan (free) `run-20260924T051749Z-660b50fc34d5`: selected 2, sessions 1,
**7 judge calls** (5 per-turn + 2 session), 12 candidate·measure pairs. Run `run-20260924T051828Z-
835a5d805950` (05:18:27–05:18:43Z): selected 2, evaluated 10, not_evaluated 5, **judge_calls 7**,
published 10 + 2 session, persisted 12, failed 0.

| measure | c1 | c2 | session |
|---|---|---|---|
| answer_relevance | pass | pass | |
| agent_trajectory_quality | inefficient | inefficient | |
| failure_recovery_quality | recovered | not_evaluated | |
| groundedness | not_evaluated | not_evaluated | |
| citation_coverage (CODE) | not_evaluated | not_evaluated | |
| session_resolution / session_coherence | | | resolved / coherent |

`not_evaluated` reasons (5): `citation_coverage` ×2 "chat_turn_facts has no row for this turn" (probe
turns never had a block saved); `groundedness` ×2 "Missing retrieval evidence" (both are catalogue
`db_query` turns — no retriever span); `failure_recovery_quality` ×1 "No failure or retry signal was
observed in the trace" (C2; C1 carried the failure signal and was judged `recovered`). Identical re-run
`run-20260924T051955Z-8909edfb9591`: **judge_calls 0**, 7 judge calls skipped by key, the 5 free
`not_evaluated` verdicts re-evaluated and replaced in place (P5.11) — `eval_results` holds 12 rows under
12 distinct keys, Phoenix 10 span + 2 session annotations (read back through REST, identity on every one).

**Golden-set experiment (P9.1b).** Driver: `--golden-set mro --examples M01 --tenant-id 17be5d65-…
--run-tag tf1` (05:20:11–05:22:37Z): one real headless turn (Opus 4.6 SDK loop, 6 tool calls incl.
`manual_retrieve` + `cited_synthesis`, 11,738-char answer, 54 citations), captured, projected; landed as
1 root + 10 children in `internal` (no `tenant.id`), and NOTHING in the tenant project (still 36 spans
/ 4 roots). Turn cost from the ledger: `llm_usage.sdk_cost_usd` $0.40942, `total_cost_usd` $0.58140.
Plan (free): matched 1, unmatched 0, sessions 0, **3 judge calls**. Run `run-20260924T052330Z-
a5ba9c6caa02` (05:23:28–05:23:38Z): judge_calls 3, persisted 5 under `__SYSTEM__` with `golden_set_id`
`golden-set/mro`; dataset `golden-set/mro` (40 examples, `RGF0YXNldDox`, version
`RGF0YXNldFZlcnNpb246MQ==`) and experiment `RXhwZXJpbWVudDox` (1 run, 5 evaluations, full identity on
each). Labels: answer_relevance **pass**, agent_trajectory_quality **good**, groundedness **unfaithful**,
citation_coverage `not_evaluated` ("chat_turn_facts has no row" — the driver saves no block),
failure_recovery_quality `not_evaluated` ("no failure or retry signal"). Identical re-run
`run-20260924T052449Z-ba54879b9f6b`: **judge_calls 0**, same dataset and version, the 2 free verdicts
re-recorded as a second experiment `RXhwZXJpbWVudDoy` (TD's design).

**Measured judge cost (CloudWatch `AWS/Bedrock`, ModelId `global.anthropic.claude-haiku-4-5-20251001-
v1:0`, ap-south-1, 1-minute sums; nothing in the hour before):**

| minute (UTC) | what ran | Invocations | input tok | output tok |
|---|---|---|---|---|
| 05:18 | tenant run | **7** (= judge_calls 7) | 6,529 | 967 |
| 05:19 | tenant re-run | **0** | — | — |
| 05:20, 05:22 | the harness turn's own Haiku calls (app, not judge) | 2 + 2 | 364 + 16,431 | 7 + 350 |
| 05:23 | golden run | **3** (= judge_calls 3) | 12,897 | 501 |
| 05:24 | golden re-run | **0** | — | — |

At Haiku 4.5's list rate ($1 / $5 per MTok; Bedrock bills its own rate — the Bedrock bill is
authoritative): tenant **$0.0114**, golden **$0.0154**, all judges **$0.0268** for 10 calls. The one
harness turn cost $0.5814 — twenty times its judging.

**Phoenix cost vs the ledger (post-TM turn — the golden M01 turn; no tenant-window turn post-dates the
TM merge).** The `claude_sdk_turn` span: Phoenix `costSummary` **$0.40576** vs `llm_usage.sdk_cost_usd`
**$0.40942** (−0.9%) over IDENTICAL tokens (24 uncached + 233,870 cache-read + 41,745 cache-write =
275,639 prompt; 1,112 completion) — the residual is price-table, not usage. G1 is fixed (was ~1.5% before
TM). The trace: Phoenix **$0.41269** vs `total_cost_usd` **$0.58140** — Phoenix shows 71%; the missing
$0.16871 reconciles exactly to the SDK delta ($0.00366) plus in-loop direct spend on no priced LLM span
($0.16506). TM's "small, not zero" residual is 28% of this turn.

**The report (P9.3), read as a customer.** Dev tenant: 4-page PDF (`quality-report-17be5d65-….pdf`, 12
scores, 2 runs). Clear: the scope-first layout, accuracy counting only judged verdicts with
`not_evaluated` beside it, the reasons table, the "cost is a floor if unpriced" caveat. Confusing: (a)
"an answer rate of 0.0%" headlines two turns whose outcome is UNKNOWN (no facts rows) — reads as "never
answers"; (b) the Judges table lists groundedness with a Haiku judge and 2 scores though it never judged
anything; (c) the Runs table shows the idempotent re-run as a second run of 5 "scores" (the re-recorded
`not_evaluated` verdicts); (d) registry revision `pilot-r3` on MRO turns means nothing to a customer; (e)
the title is the raw tenant UUID; (f) cost per query $0.1803 from `llm_model_calls` — which for the golden
turn would read $0.4163 against its real $0.5814 (the ledger misses in-loop synthesis; conversely
`llm_usage` misses the post-turn memory call). Reserved tenant: `--tenant __SYSTEM__` works (5 scores,
`golden-set/mro` as its set), cost section empty by design (the turn's ledger rows are the tenant's).

**What the run says (P9.2's point).** The `not_evaluated` distribution names three measures that cannot
see their inputs on real turns: `citation_coverage` found no facts row for any of the 3 turns scored —
dev `chat_turn_facts` holds 0 rows (`n_tup_ins` 0): the settle-time writer's upsert is `INSERT … SELECT
… FROM chats WHERE chat_id = …`, so a headless turn, which creates no `chats` row, writes nothing (and
says nothing — it returns `WRITTEN`), and no UI-saved block post-dates the writer on dev; `groundedness` has no evidence on catalogue turns
and, where it has evidence, judges a TRUNCATED copy (golden turn: the persisted row holds 54 evidence refs,
the Phoenix copy's retriever span 6, `flynapse.content_copy.truncated=true` — the judge called the answer
"unfaithful" because it "goes well beyond what is presented in the context"); `failure_recovery_quality`
correctly abstains when nothing failed. The tenant turns' `agent_trajectory_quality` "inefficient" ×2 is
the one substantive quality signal. Evidence: `~/.claude/scratch/copilot-mro/agent-evals-tf/`
(`tenant-plan-2`, `tenant-run-{1,2}`, `golden-plan-1`, `golden-run-{1,2}`, `golden-bank.jsonl`,
`report-tenant/`, `report-system/`).

### Execution handoff (2026-09-23) — SDD run live

The plan-as-plan review (two Fable lanes, TRIM-FIRST + FIX-FIRST, 26 findings all applied in place —
every amended site carries a `plan-review Cn/Sn` tag) closed the planning stage. Execution runs
SDD-driven under the owner's parameters (cap 4, implementers Opus 5.5, Fable only for review verdicts,
continuous mode superseding per-phase pauses). **The execution ledger and single resume point is
`.superpowers/sdd/agent-evaluation-completion/progress.md`** — now at **CHECKPOINT 2** (2026-09-23):
Phases 0–5 DONE on branch `agent-evals` @ f6192987 (TA, TB, TC1, TC2, integration, fix round 1 —
reviews RB-A and RB-B both PASSED and fully dispositioned, claims tables + controller triage in
`review-RB-A.md`/`review-RB-B.md`); **ALL SEVEN BUILD TASKS ARE CLOSED — every review 0 MAJOR** —
and merged: branch `agent-evals` @ **5e41e91f** (merge train 385caaaf/d447d5e2 + TF's free-half
commits). The seven-item ratification bundle is **RULED IN FULL** (consolidated in §10). Phases
0–8 ticked; Phase 9 (TF, the governed live run) is mid-flight: free half committed and banked at
$0, paid half blocked ONLY on the owner's `aws sso login --profile bedrock` (see the TF §9
subsection above). Resume point = the ledger's **CHECKPOINT 3**: SendMessage the TF agent after
SSO clears, then RB-E (Fable review of TF's whole diff — its free-half commits are unreviewed),
then the final whole-branch Fable review (9debf188..HEAD), then
superpowers:finishing-a-development-branch (owner decides merge/push). Per-task implementation
notes are consolidated in this section above; full detail in the ledger's `task-*-report.md` files.

**CLOSED (2026-09-24).** TF's paid half ran under owner-reduced bounds (Amendment 1: one golden
example, tenant window = one complete session) — 10 judge calls ≈ $0.027 total, both re-runs paid
zero, CloudWatch == judge_calls; the Phoenix-vs-ledger cost comparison verified TM's SDK-span
pricing to −0.9%. RB-E: PASS/PASS, 1 MINOR fixed in round R1 (provisional bank on payment,
9e08f99d) and re-review-verified with zero regressions; +793c0d67 (runbook re-ask escape hatch).
Final whole-branch Fable review 9debf188..793c0d67: **SHIP — 0 MAJOR, 0 MINOR, 6 NIT** (parked,
recorded in review-FINAL.md). **Merged fast-forward into `langgraph-merge` @ 793c0d67 (LOCAL —
not pushed; owner pushes)**; agent-evals* branches and the -tm/-te worktrees deleted. Merge-gate
test failures were all proven environmental (compose env-sample/Grafana-container staleness, the
dead doubled-checkout guard premise, untracked scratchpad dirt) — owner ruled proceed. Remaining
work lives on the owner sheet + §10 (first item due: ratification item 4, the
eval_results.explanation SCRUB on chat delete).

---

## 10. Future improvements

*(Filled as items are deliberately deferred — each with what is missing or suboptimal, why it was deferred or
done this way, and what the complete solution would look like.)*

- **Per-tenant judge-provider allowlist** (from §2.2 bullet 5 / Q9, deferred 2026-09-23 per plan-review
  S3). Missing: a tenant-scoped dimension on `allowed_judge_providers` — today the control is a code
  catalogue + per-deployment env (cloud selector, narrow-only allowlist, endpoint pinning). Why deferred:
  no consumer — eval runs are operator-driven per deployment, and no deployment is confirmed to host
  tenants needing different judge accounts; building it now is the no-speculative-work rule violated.
  Complete solution: a tenant-scoped setting (pattern: `tenants.llm_content_capture_enabled`) consulted
  by `validate_judge_provider` alongside the deployment env, narrowing-only, fail-closed, with the same
  pre-fetch ordering — an owner decision when a multi-account deployment materializes.
- **Structured-citation-spans source for `citation_coverage`** (from P4.1, cut 2026-09-23 per plan-review
  S4/C12). Missing: citation *structure* (counts, offsets, source/document pointers — never cited text)
  as span attributes, making the measure trace-self-contained. Why deferred: `chat_turn_facts` is now
  production-written with citation fields and no closed-set label needs character offsets; the spans path
  costs new request-path telemetry plus a redaction/retention decision. Complete solution: emit structure-
  only citation attributes on the content copy and re-point the measure's join; revisit if a measure ever
  needs offsets. Note: adopting the projection amends M-EVALS' "structured citation offsets" letter —
  owner ratifies at the TA+TB review.
- **Judge-but-do-not-publish mode** (from P5.1, deleted 2026-09-23 per plan-review S5). Missing: nothing
  with a consumer — previewing labels without recording them is served by bounded `--limit` runs plus
  key-idempotent republishing. Complete solution if ever wanted: one flag reintroducing the middle mode,
  with its cost surfaced by P5.2's accounting.
- **Identity knobs excluded by decision** (from P1.2, 2026-09-23 per plan-review S12): judge temperature,
  provider defaults, library version are NOT part of score identity. Cost: a same-prompt
  different-temperature re-run reads as the same score — true today of every other unhashed knob.
  Complete solution: fold them into the prompt-hash input if judge configs ever become per-run variable.
- ~~Bullet-3 injection-seam variants left reviewer-caught~~ **(superseded 2026-09-23: owner ruled to
  close the cheap pair — now P5.10, owned by TC2).** Only the protocol-level residuals (a caller
  implementing `JudgeEvaluator` against the runners directly) remain reviewer-caught, by design.
- **Probe-filed app-side telemetry gaps G1–G6** (measured live 2026-09-23, TC1 probe — see §9 probe
  table; all outside TC1's collector-fragment boundary, none fixable by alias):
  - **G1 — SDK-loop span has cost but no token counts** (`telemetry.py` `_llm_span_specs`,
    `claude_sdk_turn` branch). Phoenix 20.8 prices from tokens and ignores `llm.cost.total`, so the
    dominant spend (83–98% of a turn) renders as $0 — the UI shows ~1.5% of real cost. Fix: stamp the
    usage attributes from the result usage on that span (an OTTL alias cannot copy usage across sibling
    spans). **Recommended for pull-in before TF** — the governed live run's cost story is wrong without
    it; owner decides at RB-B. **RULED 2026-09-23: approved → task TM (landed on agent-evals-tm,
    6ed94fa5 + 7be5b2a2, review folds into the wave-3 round).**
  - **G2 — token semantics:** Anthropic-path `gen_ai.usage.input_tokens` excludes cached tokens; semconv
    counts them inside the prompt total. Harmless today; G1's fix must emit input = uncached +
    cache_read + cache_write or Phoenix's per-type pricing mis-splits.
  - **G3 — retriever span carries no query and no semconv documents**, so Phoenix's Documents panel is
    empty. Fix: emit `gen_ai.retrieval.query.text` + `gen_ai.retrieval.documents` (structure per the
    redaction policy); Phoenix renders them natively.
  - **G4 — provider vocabulary:** app emits `aws_bedrock`/`azure_foundry`, not semconv
    `aws.bedrock`/`azure.ai.inference`; Phoenix shows the raw string. Cost still matches by model name.
    Owner call: fix app-side or map three values in the fragment.
  - **G5 (cosmetic):** Sessions-view firstInput/lastOutput show the whole redacted JSON, not the
    question/answer text. The eval adapter parses `finalized_user_message` itself — UI-only.
  - **G6 (observation):** no invocation parameters (temperature, max_tokens) captured anywhere; if ever
    wanted, emit `gen_ai.request.*` on LLM exchange spans and Phoenix builds the panel natively.
- **TA-filed (2026-09-23, task-TA-report.md `## Future improvements` has the detail):**
  - `profile_revision` is on no span today → Phoenix-sourced subjects store NULL; fix = stamp
    `gen_ai.model.profile_revision` beside `gen_ai.model.profile` in the exchange snapshot, or resolve
    harness-side from `llm_model_calls` on `(tenant_id, block_id)`. Deferred: request-path telemetry
    change, outside the "reuse, don't invent" brief.
  - Groundedness prompt hash covers evaluator + input mapping only — the pinned library's template text
    is not installed anywhere readable; fold the real template in once `arize-phoenix-evals` is
    installed where the harness runs, or own the prompt as a classifier (measure-design change, owner's).
  - Multi-profile turns store one sorted comma-joined `profile`/`registry_revision` token — fine for
    grouping and v2-vs-v1; per-profile breakdown within a turn would read `llm_model_calls` instead.
- **TB-filed (2026-09-23):** citation_coverage's "retrieved evidence" signal comes from trace
  evidence — if evidence capture fails on a turn, an uncited turn reads `pass` instead of `fail`.
  Complete fix: a retrieval count column in `chat_turn_facts` filled by the projection (a projection
  change, drift-pinned with core's backfill), so the measure never depends on capture health.
- **RB-A-filed (2026-09-23, claim 4 — same seam as G1/G2):** on the production Claude-SDK path the
  LLM turn span stamps `gen_ai.model.profile = "claude_sdk_turn"` (a constant) and NO
  `gen_ai.model.registry_revision` — so subject `profile` identifies the pipeline, not a model
  profile, and the v2-vs-v1 comparison is blind to SDK turns (only gateway-path turns carry the
  axis). Complete fix: stamp the real model profile + registry revision (and G1's token counts) on
  the SDK-turn span in `_llm_span_specs` — **recommended as one pre-TF micro-task with G1/G2**;
  owner decides alongside Q1 ratification, since this is direct evidence on what "profile" can mean
  in production. **RULED 2026-09-23: approved → task TM; Q1 ratified (profile = the answering
  model's profile).** Residual (SDK loop rides no certified profile) → **`docs/plans/eval-quality-gaps.md`
  Task 5 (2026-09-25).**
- **Owner ratification bundle — RULED IN FULL (2026-09-23; full record in the SDD ledger):**
  1. Q1: `profile` = the ANSWERING model's profile; judge identity stays separate, per-run flags.
  2. Q2: citations counted from `chat_turn_facts` (amends M-EVALS' "structured citation offsets"
     letter) — ratified. **Amended 2026-09-25 by owner D2 → `docs/plans/eval-quality-gaps.md`** (citation
     state from the content copy).
  3. Retrieved-nothing → `pass` stands as shipped (capture-health complete fix stays TB-filed above).
  4. `eval_results.explanation` on chat delete = **SCRUB** — null the explanation, keep the score
     row. ~~Post-TF work item: wire the scrub into the chat-delete path (it sits outside
     `DELETED_CHAT_COPIES` today); until then deletion does not touch eval rows.~~ **SHIPPED
     2026-09-24** (`SCRUB_EVAL_EXPLANATIONS_SQL` on the `DELETED_CHAT_COPIES` line, same
     transaction as `delete_chat`; explanation EMPTIED not NULLed — the column is NOT NULL; own
     plan `copilot-mro/docs/plans/eval-explanation-scrub-on-chat-delete.md`, pushed `629a5aa2`).
     **Its residual pool moved 2026-09-24 to `docs/plans/privacy-logging-hygiene-batch.md`:**
     Phoenix-side annotation scrub (task P4, ruling R-3), eval-writer liveness gate (P3), and the
     `not_evaluated` exemption RULED EXEMPT (R-4 → task P6).
  5. Pre-TF micro-task approved → **task TM** (G1/G2 + RB-A claim 4, one telemetry seam).
  6. `cited_text` as judge evidence — ratified; no code owed (TC2's evidence path already lands it).
  7. api env gains the eval dependency group — ratified; **execute only after TD/TE land**
     (re-locking the shared env mid-lane could shift their test surface), then retire the
     locked-wheels PYTHONPATH recipe from the compose lane and the TF brief.
- **TM-filed (2026-09-23, task-TM-report.md §10 candidates has the detail):**
  - **Claim-4 residual (owner-level design, telemetry side complete):** the SDK loop rides no
    certified profile BY DESIGN (`record_sdk_model_usage` writes `sdk_loop` rows with NULL profile;
    `_resolve_runtime_identity` returns early on fixed provider/model; the Claude plan has no
    ORCHESTRATION binding). Complete fix = certify a profile for the SDK-loop model and let the
    runtime identity resolve it — the span then carries it with no further telemetry change (test
    pins this). Controller ruling for TF: the `claude_sdk_turn` fallback stands as the SDK path's
    profile token (dropping it would credit answers to `bedrock-classification`, worse under Q1).
  - **Per-model SDK usage:** the SDK span prices all loop tokens at the main model's rate; whether
    `ResultMessage.usage` includes subagent tokens is unverified (`total_cost_usd` does). Complete
    fix: capture `ResultMessage.model_usage` and emit one LLM child per model (feeder +
    orchestrator change). **TF must compare Phoenix `Trace.costSummary` against
    `llm_usage.sdk_cost_usd` to measure the residual gap.**
  - **G2 for the other spans:** `_usage_attributes` (exchange children) and `stamp_turn_usage`
    (root) still emit uncached input — harmless while lifecycle calls do no caching; apply the same
    prompt-total rule if gateway-binding caching is ever enabled.
  - **Residual under-report:** in-loop direct-Bedrock spend (`synthesis_*`, `direct_metered_*`)
    off the gateway sits on no LLM span Phoenix prices — small, not zero.
- **TE-filed (2026-09-23, task-TE-report.md §10 candidates has the detail):**
  - **P8.4 judge-side gap (deferred by controller ruling):** the harness's own Phoenix client
    (`phoenix_adapter._default_phoenix_client`, reads `PHOENIX_ENDPOINT`) is never host-checked —
    a harness run from outside a client's account against a publicly exposed Phoenix of that
    client would pull its content out; neither surface refuses it today. Exact fix:
    `contracts.require_in_account_phoenix(url)` on the existing private-host predicate, applied to
    the resolved base URL before `Client(base_url=url)`, + one loader-pattern test. Deferred
    because every shipped Phoenix is private by construction, TF's live run targets loopback
    (passes the check), and the runbook states the operator rule. Pull in if the wave-3 review
    rates it MAJOR.
  - **Account pinning for aws structure telemetry:** refuse `sigv4auth.assume_role.arn` and require
    every sigv4-signed exporter host to be `<service>.<region>.amazonaws.com` (~20 lines in
    `check_residency.py`). Deferred: structure not content, and only aws has a checkable account.
  - **Provisioning-time refusal:** Terraform `validation` block on the iac otel-gateway
    `phoenix_endpoint` variable + `demo_ec2_setup.sh` running `validate.sh --residency-env` before
    enabling the fragment. Outside this repo.
  - **One predicate module** shared by `contracts.py` and `check_residency.py` (differential test
    shrinks to a smoke). Coupling decision — app code imported into deployment tooling — owner's.
    **Must carry RB-D TE-1's `ipv4_mapped` unwrap** (public IPv4-mapped-IPv6 disguises admitted on
    interpreters older than CPython 3.11.10/3.12.4, gh-113171): the checker got the unwrap in TE's
    fix round; `contracts.py` inherits it only through this module (exposure there is nil today —
    the judge predicate runs in the pinned Poetry env).
  - **`--config` passthrough in operator mode** for layered-config deployments (ECS S3 URI lists);
    no consumer today.
  - **Literal seeded-batch opt-out test** — only if the owner wants the plan's letter over the
    stateless-gate argument in P8.1.
- **TD-filed (2026-09-23, task-TD-report.md §10 candidates has the detail):**
  - **TF-shaping — real harness turns cannot reach `internal` today:** the collector routes only
    NO-tenant spans to `internal`; a turn bound to the reserved tenant gets no content copy
    (capture fail-closed without a `tenants` row) and would route to `tenant-__SYSTEM__` anyway.
    In-band fix = one OTTL statement in `content-phoenix.yaml` (`tenant.id == "__SYSTEM__"` →
    `internal`) + a capture-policy rule admitting the reserved tenant on the deployment switch
    (owner decision) + a tenant-bound harness driver. Interim TF option: a driver that runs each
    golden question through the real orchestrator headless and posts the resulting turn to
    `internal` directly (no collector or capture change) — decided at TF-brief time.
  - **Runbook sections** for `--golden-set` and `generate_quality_report.py` (frozen for TD):
    targets, dataset key, experiments, `--limit` sizing, reporting-role password, run-from-api-dir.
  - **Promote `pdf_write`'s block renderer into `doc_render`** (`markdown_to_docx`), collapsing
    docx_write's duplicate — modularity, owner-confirm.
  - **Harness-stamped example id** (`flynapse.golden_example_id` on the content copy) to replace
    normalized-question-text matching; **session-grain golden datasets** if session measures should
    compare across versions; **report scope filters** (`--since`, `--run`) + per-judge accuracy
    split; **revision ordering** by the profile registry's certification time (today: earliest
    `scored_at`, which a full re-score can reorder); comma-joined session `registry_revision`
    appears as its own revision (data-honest, possibly confusing); capability-harness `CASES` as
    datasets if wanted.
  - **Known issue (pre-existing, surfaced by TD's broad lane):** placeholder
    `copilot_mro.app.services.memory` left registered by test_memory_operator_attribution.py
    breaks test_nonagent_lifecycle_spans.py under xdist — isolation bug, not TD's.
- **TF-filed (2026-09-23, surfaced by the first governed run's pre-flight; task-TF-report.md has
  the evidence):**
  - **`migrate_tenancy_schema.py --verify-only` cannot see a missing relation.** Its `verify()`
    asserts properties of the relations a database has; a declared relation the database lacks
    is neither a failure nor a finding, so dev `copilot_mro` "passed" while missing
    `eval_results`. Complete fix: a `_verify_declared_relations_exist` failure in `verify()`
    (every non-view target in the selected registries present in `Live.relations()`), plus one
    test on a database missing one table. Deferred: the tenancy script is outside this plan's
    boundary; the runbook now says a passing verify does not prove the table.
  - **The shared api env cannot run a model judge.** Its `evals` group (item-7 ruling) carries
    the Phoenix client only; `arize-phoenix-evals` and `litellm` — the judge — are in
    copilot-mro's own `evaluation` group and nowhere in the api env. Complete fix: add
    `arize-phoenix-evals = "3.8.0"` and `litellm = "1.95.0"` (copilot-mro's locked versions) to
    the api `evals` group; measured against the two packages' declared dependencies, the only
    others missing from the api env are `fastuuid`, `jsonpath-ng`, `pystache` — every other one
    is installed at a version inside its range (the re-lock itself is unrun, so a version bump
    elsewhere is not ruled out). Owner commits env files. Companion improvement: run mode should refuse
    BEFORE reading Phoenix when `phoenix.evals` is not importable (as it refuses a missing
    `eval_results`), instead of counting one `ModuleNotFoundError` failure per judge call — CLI
    change plus one CLI test.
  - **Traces ingested before TC1's session alias are sessioned by the browser id.** The four dev
    probe turns from 09:26Z group two unrelated conversations into one Phoenix session
    (`probe-browser-session-0923`); a session judge would score them as one conversation. Stored
    traces keep their ingest-time session. Complete fix: none retroactive; for session measures,
    anchor `--since` after the alias landed on the scored deployment (runbook-worthy once a real
    deployment has pre-alias history), or derive the session subject from
    `gen_ai.conversation.id` on the root rather than Phoenix's `session.id`.
  - **The interim harness driver copies its tenant's retrieved manual text into `internal`.**
    `run_golden_set_turns.py` runs each question under a real tenant (the only way it has
    manuals to retrieve from) and projects the copy tenant-less; `internal` is read by every
    platform operator. Mitigated by rule, not mechanism: the driver docstring and runbook say
    dev/demo/platform tenants only. Complete fix: TD's in-band path (a reserved-tenant-bound
    harness with the collector mapping `__SYSTEM__` → `internal`), whose retrieval scope would
    then have to be granted the golden sets' corpora explicitly — or a driver refusal for any
    tenant not flagged as non-customer, once `tenants` carries such a flag.
- **TF-filed from the paid run (2026-09-24, §9 TF run record has the numbers):**
  - **`groundedness` judges a truncated evidence copy — biased toward `unfaithful` on long answers.**
    The golden turn's persisted `llm_turn_content` row holds 54 evidence refs (214 KB, `truncated`);
    its Phoenix content copy's retriever span carries 6 (2,179 chars of `cited_text`), the root flagged
    `flynapse.content_copy.truncated=true`. The judge read those 6 against an 11,738-char, 54-citation
    answer and called it "unfaithful — goes well beyond what is presented in the context". A fixture
    could not show this; the measure is scoring the projection's bound, not the answer. Complete fix
    (either): the adapter returns `not_evaluated` ("evidence truncated in the copy") when the copy is
    truncated or its evidence count is below the turn's citation count — honest and free; or the
    harness reads the evidence from `llm_turn_content` by (tenant, block), as `citation_coverage` reads
    `chat_turn_facts`, so the judge sees what the answer cited. Deferred: app code, frozen for TF.
    → **Picked up 2026-09-25: `docs/plans/eval-quality-gaps.md` Tasks 1–2 (owner D1).**
  - **`citation_coverage` can never resolve a headless or harness turn.** The settle-time facts writer
    (M-FACTS-FAILURES) upserts `INSERT … SELECT … FROM chats WHERE chat_id = …`; a turn with no
    `chats` row inserts nothing and still returns `WRITTEN` (rowcount ignored), silently. Dev
    `chat_turn_facts` holds 0 rows. So every golden-set turn's `citation_coverage` is structurally
    `not_evaluated`. Complete fix: the harness driver saves the turn the way the chat route does
    (chat + `save_block`, which writes the full projection incl. `citation_count`) under its tenant —
    and the writer logs a zero-row settle rather than reporting it written.
    → **Picked up 2026-09-25: `docs/plans/eval-quality-gaps.md` Tasks 1–3 (owner D2: state on the copy).**
  - **The report's cost per query misses in-loop synthesis spend; the turn ledger misses post-turn
    memory calls.** Golden turn: `llm_model_calls` sums $0.4163 (SDK loop + two Haiku calls) against
    `llm_usage.total_cost_usd` $0.5814 — the $0.165 of in-loop direct Bedrock spend (`cited_synthesis`)
    is in `llm_usage.direct_cost_usd` and in no `llm_model_calls` row. Conversely the tenant turns'
    post-turn `bedrock-memory` calls are in `llm_model_calls` and not in `llm_usage`. The report reads
    `llm_model_calls` and says "a floor whenever any call is UNPRICED" — a MISSING call carries no such
    signal. Complete fix: price a turn from `llm_usage.total_cost_usd` (with its `cost_complete` flag)
    plus the `llm_model_calls` rows booked after it settled — or book in-loop direct calls into
    `llm_model_calls` so one ledger is whole.
    → **Picked up 2026-09-25: `docs/plans/eval-quality-gaps.md` Task 4 (owner D4), with readability (a).**
  - **Phoenix under-prices a synthesis-heavy turn by ~29%.** SDK span now within 0.9% of the ledger on
    identical tokens (G1 closed by TM); the trace total is 71% of the turn — the gap is exactly the
    in-loop direct spend on no priced LLM span. TM-filed "residual under-report … small, not zero" —
    measured, it is 28% of a manual-search answer. Complete fix: TM-filed per-model LLM children, plus
    an LLM child for each direct-metered call.
  - **Report readability, read as a customer:** (a) "answer rate of 0.0%" over turns whose outcome is
    UNKNOWN — the rate should be over classified turns, with "N unknown" stated; (b) the Judges table
    lists a judge for a measure none of whose scores it judged (all `not_evaluated`); (c) an idempotent
    re-run appears as a run of N "scores" — the re-recorded free verdicts; (d) the registry revision
    label (`pilot-r3`) and the raw tenant UUID title mean nothing to a customer. Complete fix: those four
    rendering rules in `quality_report.py` + fixture rows.
  - **An identical golden-set re-run adds an experiment of only re-recorded `not_evaluated` verdicts**
    (`RXhwZXJpbWVudDoy`) — TD's design, harmless, but every re-run of a set with an unresolvable measure
    grows the experiment list by one with nothing comparable in it. Complete fix: record no experiment
    whose evaluations are all re-evaluated `not_evaluated` verdicts (the rows still move run id).

---

## 11. Lessons

*(Plan-scoped. Appended after any correction from the owner during work on this plan: what was tried, what
the owner corrected, the rule to apply next time. Reviewed at the start of each phase.)*

- **Written at planning time, from the merge that produced this project:** a vocabulary argument is usually a
  missing state. "Dry run", "profile" and "residency" each mean two different things across the two source
  documents, and every one of those collisions hid a real design decision that nobody had taken. When two
  documents disagree about a word, the fix is to name the two things, not to pick a winner.
- **Written at planning time, from RV3:** a green validator that never builds the component it validates is
  not evidence. The evaluation suite had ~2,800 lines of passing tests and a boundary nobody had ever
  crossed. Acceptance must name what was actually exercised.

## Lessons

- **A passing `--verify-only` proves the relations a database HAS are conformant — it says nothing
  about relations the database LACKS.** The controller declared dev migrate+provision "already
  done" off two green verify-only runs while `eval_results` did not exist at all (89/90 registry
  relations present); TF caught it by comparing the registries against the live catalog. Rule:
  existence and conformance are separate checks — count live relations against the registry list
  before calling a database ready.
- **A first governed run is a proof, sized to the smallest input that crosses every path — not to the
  governance ceiling.** TF staged 10 golden questions and the whole 4-turn tenant window (14 judge calls)
  because both fit the ratified bounds; the owner cut it to ONE golden example and the one complete
  session (Amendment 1). One turn per target still exercised every boundary (plan, run, re-run, dataset,
  experiment, report, cost reconciliation) and surfaced every §10 finding. Rule: stage the minimal proof
  first; scale only when a finding needs more samples to be believed.
