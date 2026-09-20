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
| Seven measures, each with a **closed label set** plus `not_evaluated` | `copilot_mro/app/services/agent_evaluation/contracts.py:17` | The vocabulary is the product. `not_evaluated` separates "judged and passed" from "never judged" — the distinction whose absence makes most eval data useless. |
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

### 2.2 Precondition inherited from the merge — the provider allowlist / residency

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

---

## 3. Phases

Each phase ships something provable and is reviewed before the next starts. Estimates are **AI-assistant
execution time**; wall-clock is dominated by owner review between phases, which is stated separately.

### Phase 0 — Inventory, preconditions, and the baseline nobody has

**Goal:** start from measured facts, not from this document's snapshot.

- [ ] P0.1 Confirm the merge closed and identify the mainline branch and commit the evals code now sits on;
      re-verify every path and claim in §1.1 / §1.3 against it and correct this plan where it drifted.
- [ ] P0.2 Walk §2.2's five bullets against the residency enforcement the merge actually shipped. Record each
      as met / partial / absent with the evidence checked. Anything short of met becomes an owner item in §7.
- [ ] P0.3 Time the existing evaluation test files as they stand. Record the per-file wall time. This is the
      baseline for the repo's "<2s per file, >5s means package init is firing" rule, and it decides whether
      converting them to the dynamic-loader pattern is a real win or bookkeeping.
- [ ] P0.4 Confirm `eval_results` is still absent, and confirm whether the per-turn analytics projection has
      gained a production writer yet (it had none at merge time — only an owner-run backfill). Phase 4's
      design choice depends on the answer.
- [ ] P0.5 Establish whether any annotation has **already been written** to a live Phoenix project by the
      colleague's runs. If so, those annotations carry no identity and cannot be disambiguated; record the
      count and the projects, and raise the disposition (purge vs quarantine vs leave) as an owner item.
- [ ] P0.6 Record the measured defects found while writing this plan (§6) as confirmed or refuted.

**Acceptance:** a written inventory in this file's §7 and §8 in which every claim in §1.1, §1.3 and §2.2 is
either confirmed with the evidence checked, or corrected. No code changes.
**Lane:** unit (timing only) + read-only inspection. **Estimate:** 20–30 min execution.

---

### Phase 1 — Score identity

**Goal:** a score says what produced it. Nothing downstream is worth building on an unidentified score.

- [ ] P1.1 Define the identity a score carries, in two parts that are never merged into one string:
      **subject identity** — what answered (tenant, department, model profile and its revision, registry
      revision, the trace and span the score is about, and the turn / session / block correlation ids the
      content copy already carries) — and **judge identity** — what scored (annotation name, evaluator
      version, annotator kind, judge provider, judge model, and a stable hash of the judge prompt actually
      used). Plus a **run id** shared by every score in one invocation.
- [ ] P1.2 Make the judge-prompt hash a property of the evaluator, derived from the prompt text the evaluator
      will actually send, so editing a prompt changes the identity without anyone remembering to bump a
      version string. Record explicitly what the hash does **not** cover (judge provider defaults,
      temperature, library version) and whether those belong in identity — a decision for §5, not a silent
      omission.
- [ ] P1.3 Widen the **already-evaluated skip key to the full judge identity**, so a re-run with a different
      judge model is a new evaluation rather than a skip. This is the same tuple as 1.1, used twice; a score
      whose identity differs from a stored score's is by definition not the same score. Today's key is
      `annotation_name:evaluator_version`.
- [ ] P1.4 Extend the same identity to the **session** path, which today has no skip check at all (§6.2) — so
      session judges re-pay on every run and would keep doing so after 1.3.
- [ ] P1.5 Carry the identity through the run report, so a report is self-describing rather than needing the
      invocation's shell history to interpret.
- [ ] P1.6 Logging coverage for the modules touched, per the rebuild's standing rule: every failure path logs
      at the right level with bound context, no user content in log fields, one line per run lifecycle
      boundary.

**Acceptance (measurable):** given a fixed candidate, two evaluation runs that differ **only** in judge model
produce two results with **different** identities, and the second is **not** skipped as already-evaluated; a
third run with an identical tuple **is** skipped. The same holds on the session path. Proved by a unit test
that is **mutation-checked**: removing any single field from the identity must make that test fail. Full
`tests/unit/observability/` stays green.
**Lane:** unit. **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 2 — `eval_results` (7.3)

**Goal:** scores persist somewhere a report can read them, tenant-scoped, keyed by Phase 1's identity.

- [ ] P2.1 Declare the relation in the table registry: tenant-scoped, private by construction (never disclosed
      by the catalog reference, never in the query allowlist), following the existing per-turn-facts and
      model-calls relations as the pattern rather than inventing one.
- [ ] P2.2 Columns carry Phase 1's identity in full, plus the measure, the label, the optional numeric score,
      the bounded explanation, the golden-set id where a run came from a curated set, and the row timestamp.
      7.3's original list is the floor (§2.3 row 1).
- [ ] P2.3 Row-level security and the read grant for the reporting role, matching the existing analytics
      relations. Reports read through the read-only role; the harness writes as the owner.
- [ ] P2.4 Upsert semantics on the identity: a re-run with the same identity replaces, a re-run with a
      different identity appends. State what "the same score twice" means before any writer exists.
- [ ] P2.5 The runner writes to it. The write must not be able to stop a batch, same doctrine as the judge
      call — a failed persist is a counted failure, not an aborted run.
- [ ] P2.6 Logging coverage for the writer.

**Acceptance (measurable):** DDL and tenancy-classification tests pass in the registry lane; a seeded
two-tenant database test shows tenant A's rows invisible to tenant B under the request binding; and the
"v2 vs v1" query named in 7.3 returns the expected per-measure comparison from seeded rows differing only in
registry revision. A persist failure in a batch of N yields N−1 stored scores and one counted failure.
**Lane:** registry + db. **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 3 — Phoenix runs, and our spans render in it (7.1 + 7.2)

**Goal:** you cannot judge traces the tool cannot read. Close 7.1 and 7.2 with evidence, not configuration.

- [ ] P3.1 Close 7.1 by verification: confirm the optional-overlay shape, the image pin, auth, retention,
      loopback binding, one project per tenant plus `internal`, and that the base stack is Phoenix-free.
      Fix only what is actually missing. Confirm whether rebuild task 11.4's compose decoupling is already
      satisfied and mark it so in the rebuild plan's ledger rather than leaving it dangling.
- [ ] P3.2 Confirm the compose environment can actually start — the merge found the stack demanding Phoenix
      secrets with no sample env to supply them, and a stack that cannot boot cannot be smoke-tested.
- [ ] P3.3 **7.2, the attribute-mapping probe:** send one real agent trace through the content pipeline into a
      live Phoenix and record, per attribute, what Phoenix renders: model, provider, token counts, cost,
      tool name and id, span kind, input and output bodies, session grouping. The output is a table of
      *expected vs rendered*, not a pass/fail claim.
- [ ] P3.4 Fix the mapping gaps the probe finds by adding or correcting aliases in the collector fragment.
      Two are suspect on reading and must be confirmed or refuted by the probe rather than assumed: the
      invocation-parameters alias is fed from the prompt attribute, and the output-messages alias from the
      completion attribute — both are plausible mis-mappings that would render as wrong panels rather than
      as missing ones. Also check whether a total-token attribute is expected and unset.
- [ ] P3.5 Extend the compose smoke so the assertion is **"Phoenix stored and returned it"**, not "the
      collector accepted it": read the trace back out of Phoenix and assert the rendered attributes and the
      tenant project routing.
- [ ] P3.6 Record the probe table in this plan. It is the reference for every later "why does this panel look
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

- [ ] P4.1 Decide the source of truth for a turn's citations and record why. The two candidates: the
      **structured citation spans** produced with the answer (each carrying the source pointer, the
      document, the page, and character offsets into the final answer string), or the **per-turn analytics
      projection**, which already stores a citation count and the cited documents per turn and needs no new
      telemetry. The projection is cheaper but had **no production writer** at merge time (P0.4), which would
      make it empty in production; the spans are authoritative but are not on the trace today.
- [ ] P4.2 Whichever source wins, establish the **correlation path from a Phoenix trace to it**. The content
      copy already carries the block, turn, session and chat ids as span attributes — that is the join, and
      it should be used rather than re-derived.
- [ ] P4.3 If the answer is "put it on the trace", emit the citation *structure* only — counts, offsets,
      source and document pointers — and **not** cited source text, which would put manual content on a
      second surface with its own retention. Note the redaction and retention consequence explicitly.
- [ ] P4.4 Define what the measure now means, in the labels it already has: a turn that cites nothing but
      needed to cite, a turn that legitimately needed no citation, and a turn with retrieval evidence but no
      citation are three different outcomes and only one is `fail` — the third label `not_evaluated` exists
      for exactly this.
- [ ] P4.5 Delete the bracket-marker heuristic and the assumption that a displayed answer contains markers.
- [ ] P4.6 Fixtures drawn from **real persisted turns**, including the adversarial ones: an answer containing
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

- [ ] P5.1 Fix or remove the `"dry_run"` mode. Today it judges everything and writes nothing, so "dry" costs
      full price. At minimum the mode names must stop colliding: a **no-cost plan** mode (select candidates,
      resolve identities, report what *would* be judged and roughly what it would cost, make no provider
      call) is a different thing from a **judge-but-do-not-publish** mode, and both are useful. Whichever
      survives, the cheap one is the default and the expensive one is opted into.
- [ ] P5.2 Surface the cost of a run: candidates selected, judge calls made, calls skipped by identity,
      tokens where the provider reports them. A run whose cost is invisible is a run nobody will repeat.
- [ ] P5.3 Fix the judge-factory fallthrough (§6.1): an unrecognised measure name currently receives an
      answer-relevance classifier and is scored under the requested name. An unknown measure must be refused.
- [ ] P5.4 Build the **real integration test**: a run against a live Phoenix with a stub judge — a judge that
      returns fixed labels and makes no provider call. This exercises every part of the boundary that was
      mocked (candidate fetch from real spans, the annotation write, the read-back, the identity round-trip)
      without paying a vendor. **This is the point of the phase: the mocked part was never the judge, it was
      Phoenix.**
- [ ] P5.5 Assert idempotency across the real boundary: run twice, and the second run skips on identity rather
      than double-annotating.
- [ ] P5.6 Bank a real judge-provider run as an **operator-run** step with a recorded result, explicitly not
      as a test. It is the only way to learn what the judge does with real manual text, and it cannot be a CI
      lane.

**Acceptance (measurable):** against a live Phoenix, a run with a stub judge fetches candidates from real
spans, writes annotations, and a read-back returns them with their identity intact; the second identical run
makes zero new annotations. The no-cost mode makes **zero** provider calls, proved by a judge double that
raises if called. An unknown measure name is refused rather than scored.
**Lane:** compose (live Phoenix, stub judge) + unit for the refusal and the no-cost mode. The real-provider
step is a **live run**, recorded, not a test. **Estimate:** 90–120 min execution; +1 owner review cycle.

---

### Phase 6 — Harness → Phoenix datasets and experiments (7.4)

**Goal:** the department evaluation sets become Phoenix datasets, and a scored run becomes a comparable
experiment.

- [ ] P6.1 Inventory what the existing end-to-end evaluation harness already produces — curated per-department
      sets and gold fixtures exist in the e2e tree — and map those to the dataset shape rather than authoring
      a second corpus.
- [ ] P6.2 Push datasets keyed so that the same set pushed twice is the same dataset, not a duplicate.
- [ ] P6.3 Push experiment runs carrying Phase 1's identity, so an experiment in Phoenix and a row in
      `eval_results` are **the same score seen from two sides** — the run id is what ties them.
- [ ] P6.4 Keep 7.4's payload-without-an-endpoint check as a fast test, explicitly labelled as a *shape* check
      and not as integration acceptance (§2.3 row 5).
- [ ] P6.5 Write the same scores to `eval_results` in the same run. Phoenix is the workbench; the table is the
      record of account. Neither is derived from the other after the fact.
- [ ] P6.6 Logging coverage for the push path, including one lifecycle line per dataset and per experiment.

**Acceptance (measurable):** pushing the same dataset twice yields one dataset; an experiment run appears in
Phoenix with its identity attached and produces the matching rows in `eval_results` under the same run id,
with the row count equal to candidates × measures minus identity-skips. Re-running with a changed registry
revision produces a **second** experiment, not an overwrite.
**Lane:** compose (live Phoenix) + db. **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 7 — Per-tenant quality report (7.5)

**Goal:** the client-review artefact — what a customer is shown when they ask "is it getting better".

- [ ] P7.1 Define the report's content: per-measure accuracy, answer rate, **regressions across versions**
      (which is why identity had to come first), and cost per query. Cost joins the existing per-call usage
      ledger; the report must not re-derive pricing.
- [ ] P7.2 Reads happen through the read-only reporting role, per the rebuild's data-access rule.
- [ ] P7.3 Render through the **existing document-render helper**, not a new one.
- [ ] P7.4 The report states its own scope: which runs, which registry revisions, which judge, and what was
      `not_evaluated` and why. A quality report that hides its denominator is worse than none.
- [ ] P7.5 One tenant per report, and a test that proves a report for tenant A contains no row belonging to
      tenant B.
- [ ] P7.6 Logging coverage for the generator.

**Acceptance (measurable):** a fixture result set produces a **byte-identical** report on two runs
(deterministic ordering, no wall-clock in the body); a two-tenant fixture set produces two reports with no
cross-tenant content; and every number in the report is traceable to rows the read-only role can select.
**Lane:** unit (fixtures) + db (isolation). **Estimate:** 60–90 min execution; +1 owner review cycle.

---

### Phase 8 — Sampled production copy, same account only (7.6)

**Goal:** close the exporter-side residency item that no phase of the merge claimed (§2.3 row 6).

- [ ] P8.1 Confirm the sampling and opt-out halves behave as documented: the per-tenant capture policy and the
      sample rate both gate the copy, and a tenant that opted out produces no content copy at any sample rate.
- [ ] P8.2 Define what "same account" means as a checkable property of the exporter configuration for each
      deployment profile, so it can be refused rather than reviewed.
- [ ] P8.3 Make the overlay validation **refuse** a cross-account exporter configuration — 7.6's stated test,
      and the thing that turns the residency ruling from a policy into a mechanism.
- [ ] P8.4 Confirm the collector-level guarantee composes with the judge-level allowlist inherited from the
      merge (§2.2). Two surfaces, one rule; a gap in either defeats both.
- [ ] P8.5 Record the residency story end to end in the observability runbook: where content goes, who may
      judge it, what refuses what, and how an operator proves it.

**Acceptance (measurable):** a deliberately cross-account exporter configuration is **refused by validation**
with a message naming the offending endpoint; an opted-out tenant produces zero content copies across a
seeded batch at sample rate 1.0; and the profile validation still passes for every legitimate profile.
**Lane:** compose / configuration validation + unit. **Estimate:** 45–75 min execution; +1 owner review cycle.

---

### Phase 9 — First governed live run, and close-out

**Goal:** prove the workbench on real traffic once, then write down what it cost and what it said.

- [ ] P9.1 Run the full set against a real tenant project with a real judge provider, within the residency
      allowlist, at a bounded candidate limit.
- [ ] P9.2 Record the run: identity, candidate count, judge calls, cost, per-measure label distribution, and
      the `not_evaluated` reasons. The `not_evaluated` distribution is the most informative output of a first
      run — it says which measures cannot see their inputs.
- [ ] P9.3 Generate one per-tenant report from that run and read it as a customer would.
- [ ] P9.4 Tick items 7.1–7.6 in `docs/plans/observability-rebuild.md` with the evidence for each, and append
      the review section there. Phase 7 of the rebuild closes here or not at all.
- [ ] P9.5 File everything deferred into §6 Future Improvements of this file, each with what is missing, why it
      was deferred, and what the complete solution looks like.

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
5. **The idempotency key is the identity.** One tuple, used to name a score and to decide whether it already
   exists. Two keys would drift, and the drift would look like a skipped run.
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

Each was read in the tree on 2026-09-20 and is confirmed or refuted in P0.6.

1. **The judge factory falls through to an answer-relevance classifier.** `_build_evaluator` special-cases
   groundedness, trajectory and failure-recovery, then returns an answer-relevance classifier for
   *everything else*. A misspelled or unhandled measure name therefore gets scored by the wrong judge under
   the requested name. The contract's closed label sets catch some of these at construction, but not all.
   **Owned by P5.3.**
2. **Session evaluation has no idempotency check at all.** The per-turn path checks already-written evaluator
   identities before queuing work; the session path queues every judge for every candidate unconditionally.
   So session judges re-pay on every run today, and would continue to after the per-turn key is widened.
   **Owned by P1.4.**
3. **The evaluation tests import the package directly**, against the repo's dynamic-loader rule for tests
   touching service modules. Whether that actually costs anything is measured in P0.3 rather than assumed.
4. **The contamination guard is in the trajectory prompt, not the recovery prompt.** The SDD progress note
   describes it as instructing the judge not to re-score groundedness "when scoring the recovery outcome";
   the sentence is in the `agent_trajectory_quality` template. The guard is real and worth keeping — the
   note's placement is wrong, and the recovery prompt may want the same sentence.
5. **The per-turn analytics projection has no production writer.** Its own documentation says so: the writer
   is a pending rebuild task and until it lands the relation is filled only by an owner-run backfill. This
   is load-bearing for Phase 4's choice of citation source, which is why P0.4 checks it.

---

## 7. Open questions — owner-owed

Nothing here blocks Phases 0–2. Items 1 and 2 block Phase 4; items 3 and 4 block any live run.

- [ ] **Q1. What does `profile` mean in 7.3?** The model-profile id (matching `registry_revision` beside it and
      the existing per-call ledger vocabulary), or the observability backend profile (oss / aws / azure /
      newrelic)? *Checked:* the per-call ledger carries `profile`, `profile_revision` and `registry_revision`
      together, which makes the model-profile reading much more likely, but the spec uses the same word for
      the collector profile elsewhere. Working assumption: model profile. A wrong guess here is a column
      rename later, not a rebuild.
- [ ] **Q2. Where should citations come from for the rewritten measure** — the structured spans (authoritative,
      needs a new span attribute and a redaction decision) or the per-turn analytics projection (already
      stores citation count and cited documents, needs no telemetry, but has no production writer)?
      *Checked:* both exist in the tree; the projection's own documentation states the writer is still owed.
- [ ] **Q3. Does the merge's residency enforcement meet §2.2's five bullets?** *Checked at plan time:* the
      merge plan's own owner-decision list records residency as **unenforced** on the merged tree — a search
      for an allowlist across the runner and the CLI returned nothing — with the ruling that no eval run
      touches real traces until it is. So this is owed, and P0.2 re-checks it against whatever the merge
      finally shipped rather than against that snapshot.
- [ ] **Q4. What happens to annotations already written without identity?** If the colleague's runs wrote
      annotations into a live Phoenix project, they are permanently ambiguous — purge, quarantine into a
      separate project, or leave and never trust? P0.5 finds out whether any exist.
- [ ] **Q5. Which judge provider and model are approved** for a first live run, given the residency contract
      and the documented OpenAI default? The runbook documents both an OpenAI path and a Bedrock path; only
      the owner can say which is contractually usable against which tenant's content.
- [ ] **Q6. Does a customer ever see the per-tenant quality report unprompted**, or is it an on-request
      artefact? It changes whether 7.5 needs scheduling, and this plan assumes on-request.
- [ ] **Q7. Is a golden set per department expected to be curated for this project**, or do the existing
      end-to-end evaluation sets serve? This plan assumes the latter (Decision 10); curating new sets is
      explicitly out of scope (§8).

---

## 8. What this project deliberately does NOT do

- **It does not implement the judge-side provider allowlist / residency.** That is the current merge's
  deliverable and this project's precondition (§2.2). It verifies it and names gaps; it does not widen it and
  does not re-litigate the ruling.
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

---

## 10. Future improvements

*(Filled as items are deliberately deferred — each with what is missing or suboptimal, why it was deferred or
done this way, and what the complete solution would look like.)*

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
