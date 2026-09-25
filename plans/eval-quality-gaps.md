# Eval quality gaps — full groundedness evidence, trace-carried citation state, SDK-loop profile, honest report

> **SDD-driven.** Controller: the owner's Opus session. **Model policy:** implementers and reviewers are Opus 5.5,
> with a fresh agent per task, one implementer per working tree, and at most 2 running at once (the owner may raise it).
> **Ledger:** `/home/aditya/Code/.superpowers/sdd/eval-quality-gaps/progress.md`.
> **Scratch:** `~/.claude/scratch/eval-quality-gaps/<lane>/`.

**Goal.** Fix the four defects the first governed eval run (TF, 2026-09-24) measured, then prove fixes 1–3 in one
governed live run before the TF golden row expires (~2026-10-24):
1. `groundedness` judged only 6 of the answer's 54 cited quotes.
2. `citation_coverage` cannot resolve a turn that skipped a chat door, and the settle writer calls such a turn `WRITTEN`.
3. The SDK loop has no certified profile.
4. The quality report prices from a ledger that misses in-loop synthesis, and divides its answer rate by unknown turns.

**Owner rulings (2026-09-25, as researched)**
- **D1:** the judge reads every distinct cited quote, and "retriever span" means distinct quotes.
- **D2:** citation state travels on the content copy, and the measure reads it there. **This amends Q2 /
  ratification item 2** ("citations counted from `chat_turn_facts`"). A missing chat row settles as `NO_CHAT`.
- **D3:** the SDK loop gets its own certified profile id.
- **D4:** cost comes from `llm_usage.total_cost_usd`, with a separate post-turn memory column. The answer rate excludes
  unknown turns and says how many there were.
- **Proof run APPROVED:** about $0.62, for one paid turn plus judges.

**Evidence.**
- Research: `~/.claude/scratch/eval-quality-gaps/research/R1-eval-gaps.md` (spot-verified; corrections are listed
  under Controller rulings).
- Parent plan: `docs/plans/agent-evaluation-completion.md` (§9 TF record, §10).
- TF artefacts: `~/.claude/scratch/copilot-mro/agent-evals-tf/`.
- Base: copilot-mro `langgraph-merge` @ `e0cdea42`.

**Push rule.** Claude may push to origin `langgraph-merge` after the protocol below. Never rebase, squash, amend or
force-push: the exception-text register's ratchet compares against the merge-base copy.

## Global constraints

- **Worktrees.** One implementer per plain `git worktree` at `/home/aditya/Code/copilot-mro-eqg<N>`, on branch `eqg-t<N>`
  cut from the integration branch `eval-quality-gaps`. Each worktree has `.env` symlinked, its path in
  `.git/info/exclude`, and private scratch.
- **Commits.** Commit by pathspec (`git commit -- <paths>`), never with `git add -A`. Never stage the primary
  checkout's owner WIP (`deployment/otel/VERSIONS.md`, `docs/plans/open-items.md`).
- **Running tests.** Every run goes through `/home/aditya/Code/pytest-slot.sh -- <cmd>`, on
  `/home/aditya/Code/api/.venv`, from the worktree root, with `DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=<worktree>`.
  - The first run records pytest's `rootdir` and one module's `__file__`.
  - Full lanes run with `-n 2`; db and register lanes run serially.
  - Read pytest's own exit status.
- **Red-before and mutation.** Every behaviour change is red-before: the test fails on the base commit, and the report
  quotes the failing line. Mutation targets run through `/home/aditya/Code/mutant.sh`. A mutant counts as a survivor
  only once the full lane also passes with it applied.
- **Test style.** Use the dynamic loader (`tests/_agent_evaluation_loader.py` for eval modules, `tests/_package_stubs.py`
  otherwise), under 2s per file. Follow the two-level layout with unique basenames, take paths from `tests/_root.py`,
  and run the `tests/unit/infra` guards in every lane.
- **Exception-text register.** `tests/unit/observability/exception_text_register.json` must equal the scan, and its
  floors must hold. `telemetry.py`, `llm_content_capture.py`, `turn_facts.py` and the eval modules are all scanned. No
  task grows the register, and new log lines carry ids and counts only.
- **Known env reds.** Before dispatch, the controller baselines these lanes at `e0cdea42` and ledgers the red set;
  only that set counts as environmental:
  - `tests/unit/{agent_shared,agent_claude,observability,chat_history,lang_agent,infra}`;
  - `tests/db/{evaluation,chat_history}`.

  One red is already known: `test_nonagent_lifecycle_spans` goes red under xdist because a placeholder
  `copilot_mro.app.services.memory` leaks. Confirm it serially and keep `-n`. The only compose-lane test in scope is
  Task 2's `tests/integration/otel/test_phoenix_evaluation_boundary.py` (`compose_stack` + `OTEL_COMPOSE_SMOKE=1`), run
  by file; the controller baselines it too, so the known compose reds (env-sample ×2, stale Grafana healthcheck) stay
  out of its verdict.
- **Limits.** No DB writes outside the test DB, and no paid call before Task 6. Executors report exact text; only the
  controller edits this plan.

## Controller rulings

**Fixed interface** (every parallel task builds to exactly these names; changing one needs a controller ruling):
- **v2 snapshot `outcome`:** `citation_count` (int ≥ 0) and `needs_clarification` (bool). Both are content-free.
- **Root copy span:** `flynapse.citation_count` (int) and `flynapse.needs_clarification` (bool). They are stamped
  together, only when the row carries them, and never defaulted.
- **Every retriever copy span:** `flynapse.content_copy.evidence_complete` (bool), always stamped. It is absent only on
  copies older than this batch, which read as incomplete.
- **`EvaluationCandidate`:** optional fields `evidence_complete`, `citation_count` and `needs_clarification`, default None.
- **Identifiers:**
  - judge version `citation-coverage-v3`;
  - tokens `NO_CHAT = "no_chat"` and `ALREADY_SETTLED = "already_settled"`;
  - profile `bedrock-sdk_loop`, role `sdk_loop`, revision `pilot-r4`.

**R-D1 (owner) — groundedness input.**
- The judge reads every distinct quote; only identical refs collapse.
- It judges only when every retriever span says `evidence_complete=true`; otherwise the result is a free
  `not_evaluated`.
- The gate never uses the root's `flynapse.content_copy.truncated`. That flag also fires on tool-I/O truncation, so it
  would abstain on the TF turn even after the fix.
- Judge identity is unchanged. Pre-fix copies abstain, and no existing score is re-judged.

**R-D2 (owner; amends Q2) — citation state from the copy.**
- `citation_coverage` v3 reads the candidate: no DB read, no tenant binding. Headless, `__SYSTEM__` and
  failed-before-save turns resolve alike. This also removes the golden tenant-join defect (R2c).
- `PostgresCitationFacts` and its wiring are retired; `chat_turn_facts` stays as the analytics projection.

**R-NOCHAT (controller; completes D2's writer clause).** A settle can land zero rows for two reasons. One is an absent
chat row. The other is a repeat settle, which the upsert's `WHERE chat_turn_facts.turn_outcome IS NULL` declines by
design (`chat_turn_facts.py:674-682`); the research missed it. So `NO_CHAT` requires the chat row to be absent, a
repeat settle is `ALREADY_SETTLED`, and neither is `WRITTEN`.

**R-D3 (naming left to this plan).**
- **Name.** `bedrock-sdk_loop`, built through `profiles._claude_profile` (rate-card Claude-family check) from a new
  `ModelRole` value `sdk_loop`, appended as `DECISION` was.
- **Why a new role.** D-07 allows one profile per role, and `bedrock-orchestration` is lang's Sonnet profile while the
  loop runs Opus. `sdk_loop` is already the ledger's word for these calls (`record_sdk_model_usage`).
- **Why `pilot-r3` → `pilot-r4`.** The revision literal names the certified set, and adding a profile changes the set;
  the r2→r3 bump for additive bindings is the precedent. Without a bump, r3 would name two different sets.
- **Accepted cost.** Lang turns relabel r3→r4 with no model change, and r3 battery banks can't be reused (none is
  committed).
- **Scope.** Bedrock transport only. On Foundry or Anthropic-direct, no profile is claimed and the span keeps
  `claude_sdk_turn`. No plan entry and no gateway binding: the loop bills natively.

**R-D4 (owner) — report cost and answer rate.**
- **Headline:** `llm_usage.total_cost_usd` per scored turn, with the count of `cost_complete = false` turns beside it.
- **Upkeep:** a separate column of `llm_model_calls` rows with role `memory` and origin ≠ `sdk_loop`. It is never added
  to the headline.
- **Answer rate:** answered ÷ (turns − unknown), with the unknown count stated. If nothing is classified, print "no
  scored turn has a known outcome".

**R-ORDER.** Tasks 1, 3, 4 and 5 own disjoint files and can run in any order. Task 2 starts after Task 1 merges,
because its cross-seam test runs Task 1's projection. Waves: {1, 5} → {2, 3} → {4}.

**R-RUNBOOK.** Task 2 owns `docs/runbooks/observability/phoenix-evaluations.md`. Task 4 hands its report sentence to the
controller as exact text, and the controller applies it at Task 4's merge.

**R-PROOF-ORDER.** Task 6 runs from the integration branch before the mainline merge, so what is pushed is what was
proven.

**Research corrections (checked at `e0cdea42`).**
- The three `tests/e2e/agent_runtime/*` `pilot-r3` sites are stub strings, not pins. Do not flip them.
- The real revision pin is `test_model_certification_matrix.py`, via `ACTIVATIONS_BY_REVISION` at
  `model_certifications.py:760`.
- The research missed the role-vocabulary pin at `tests/unit/agent_shared/test_model_plan_and_usage.py:162`.
- Real Phoenix returns the root's `flynapse.*` attributes as one nested dict under `attributes.flynapse`, and child
  attributes as flat dotted keys (`test_phoenix_real_span_shapes.py`).

**Pre-flight (controller).**
- [ ] Cut `eval-quality-gaps` at `e0cdea42`. Baseline the lanes, and write the red set and the fixed interface to the
      ledger.
- [ ] In the parent plan, add the D2 amendment on §7 Q2 and on §10 item 2. Point TF's three §10 items (truncated
      evidence, headless `citation_coverage`, report cost) and TM claim-4 at this plan. Commit that with this plan.

## Tasks

### Task 1: The content copy carries every distinct quote and the turn's citation state
**Owns:** `copilot_mro/app/services/agent_shared/{telemetry,llm_content_capture}.py`,
`tests/unit/agent_shared/test_telemetry.py`, `tests/unit/agent_shared/test_llm_content_capture*.py`, and a new
`tests/unit/agent_shared/test_content_copy_citation_state.py`. `test_llm_content_capture.py:232` pins the exact `outcome`
dict and must be updated. Grep for any other test that pins the `outcome` shape or a copy span's exact attribute set,
and list each one in the report.
- [ ] `_deduped_evidence_refs` (telemetry.py:1298-1314) also keys on `cited_text`, or on `text` where a ref has one.
      That is the harvest's own identity (`_cited_core.py:495`). `evidence_count` then counts the refs kept.
- [ ] `_retriever_span_specs` stamps `evidence_complete`, true only if the child was not shortened for projection,
      `limits` has no `omitted_evidence_refs`, and no ref sequence has `_truncated_items`.
- [ ] The `outcome` of `_build_v2_snapshot` (llm_content_capture.py:1425) gains two fields:
  - `citation_count`: the length of the list `AgentPipeline._pipeline_result` hands on (the backend's
    `metadata.citations`, else `evidence_refs`), counted before any capture bound.
  - `needs_clarification`: from `post_turn_signals`, false if those are absent.

  Both survive every fit step, including `minimal` (:1300). The v1 builder is left alone: it runs only without an
  accumulator, and its copies abstain.
- [ ] The root span stamps both scalars when the row carries them (telemetry.py ~:1777-1792), and neither otherwise.
      The root `truncated` flag keeps its meaning.

**Red-before:**
- **Dedup:** flip `test_telemetry.py:2151-2157` so two refs on c1 with different text give 2 (today 1); 3 distinct
  quotes plus 1 duplicate give 3.
- **Marker:** true for a clean copy. False for a child shortened past 64 KiB, for `omitted_evidence_refs`, and for
  `_truncated_items`.
- **Scalars:** exact with 120 citations, after the 4-ref cut, and in `minimal`.
- **Root attributes:** present on a post-change row, absent on a pre-change one.
- **Pipeline parity:** the count matches `_pipeline_result` for both citation sources.

**Mutation targets:** drop the quote from the key; force the marker true; count the bounded list; drop the scalars from
`minimal`; default the root attributes.

### Task 2: The harness gates groundedness on complete evidence and scores citations from the copy
**Owns (production):** `copilot_mro/app/services/agent_evaluation/{contracts,phoenix_adapter,runner,citation_coverage}.py`,
`results_store.py` (docstring only), `scripts/observability/run_phoenix_evals.py`, and
`docs/runbooks/observability/phoenix-evaluations.md`.

**Owns (tests):**
- `tests/fixtures/evaluation/citation_coverage_turns.json`, `tests/unit/observability/test_agent_evaluation_runner.py`,
  `tests/db/evaluation/test_eval_results_db.py`;
- `tests/unit/observability/evaluation/{test_citation_coverage_real_turns,test_phoenix_real_span_shapes,test_phoenix_score_identity,test_plan_mode_costs_nothing,test_golden_set_experiments}.py`;
- `tests/integration/otel/test_phoenix_evaluation_boundary.py` — its posted spans carry the new attributes, and it
  stops seeding `chat_turn_facts`;
- `tests/unit/observability/test_phase1c_nonagent_scope_guard.py` — the :233 comment only;
- deletes `.../evaluation/test_citation_facts_lookup.py` and `tests/db/evaluation/test_citation_facts_db.py`;
- adds `.../evaluation/{test_copy_evidence_gate,test_copy_to_candidate_seam}.py`.

Task 2 starts after Task 1 merges.
- [ ] `EvaluationCandidate` (contracts.py:615) gains the three fields, type-checked. A non-bool or non-integral value
      reads as None and is never coerced, except that an integral float widened by the dataframe reads as its integer.
- [ ] Adapter. `evidence_complete` is true only when every retriever row says true. The count and the flag come from the
      root. Both shapes real Phoenix returns are read: nested `attributes.flynapse` on the root, flat dotted keys on
      children.
- [ ] `runner._missing_judge_inputs` (:335-360): groundedness whose evidence is present but incomplete returns "Evidence
      is incomplete in the content copy." That is a free `not_evaluated`, and plan mode (`planner.py`) counts no judge
      call for it.
- [ ] `citation_coverage` v3 takes the candidate only and keeps v2's label table. Either field absent →
      `not_evaluated` ("The content copy carries no citation state."). Version `citation-coverage-v3`, so every v2
      verdict is re-evaluated.
- [ ] Retire `CitationFacts`, `CitationFactsLookup`, `PostgresCitationFacts`, `CITATION_FACTS_SQL`, the runner's
      `citation_facts` parameter, and `run_phoenix_evals._citation_facts` (:180, :378-385). Grep every docstring that
      names them, e.g. `results_store.py:120`.
- [ ] Runbook notes: groundedness judges distinct quotes and abstains on incomplete or old copies; `citation_coverage`
      v3 reads the copy.

**Red-before:**
- **Cross-seam:** a TF-shaped row (54 distinct quotes over 6 chunks), projected by Task 1's code, gives 54 evidence
  strings, the marker true and count 54. Today it gives 6 strings and neither field.
- **Gate:** evidence without the marker gives `not_evaluated` with judge_calls 0. Root `truncated=true` with a complete
  retriever span is still judged.
- **Scoring:** `__SYSTEM__` with count 54 and no facts source gives `pass` (today `not_evaluated`). Count 0 with evidence
  gives `fail`; count 0 with a clarification gives `pass`; no state gives `not_evaluated`.
- **Shapes:** all three fields read correctly from real span shapes.

**Mutation targets:** ignore the marker; gate on the root flag; use `any` for `all`; read an absent flag as false; leave
the version at v2.

### Task 3: The settle writer reports when nothing landed
**Owns:** `copilot_mro/app/services/agent_shared/turn_facts.py`,
`tests/unit/chat_history/test_chat_turn_facts_settled.py`, `tests/db/chat_history/test_chat_turn_facts_db_roundtrip.py`.
- [ ] `record_settled_turn_facts` (:112-160) stops ignoring `_default_execute`'s rowcount (:87-109):
  - 1 → `WRITTEN`;
  - 0 with no chat row → `NO_CHAT`, plus one WARNING carrying the tenant and block ids;
  - 0 with a chat row → `ALREADY_SETTLED`, with no warning.

  The chat-presence read runs only on a zero-row result, in the same transaction and binding. `FAILED`, `UNBOUND` and
  `NO_KEY` are unchanged; the writer still never raises. Docstrings and `__all__` name the new tokens.

**Red-before:**
- **Unit seam:** 0 with no chat → `NO_CHAT`; 0 with a chat → `ALREADY_SETTLED`. Both are `WRITTEN` today.
- **DB lane (serial):** no chat row → `NO_CHAT` and no facts row. Settling twice → `WRITTEN`, then `ALREADY_SETTLED`, with
  the outcome unchanged.

**Mutation targets:** return `WRITTEN` always; skip the chat-presence read.

### Task 4: The quality report prices turns from the turn ledger and states unknown outcomes
**Owns:** `copilot_mro/app/services/agent_evaluation/quality_report.py`,
`tests/unit/observability/evaluation/test_quality_report.py`, `tests/db/evaluation/test_quality_report_db.py`.
- [ ] `COST_SQL` (:109-119) prices each scored turn from `llm_usage.total_cost_usd` on `(tenant_id, block_id)`. It reports
      turns with a ledger row, turns with `cost_complete = false`, and the complete-cost sum. Cost per query divides by
      the complete-cost turns and says so. The reporting role already has the grant (`provision_rls.py:269-275`).
- [ ] A separate upkeep column: `llm_model_calls` rows with role `memory` and origin ≠ `sdk_loop`, never added to the
      headline. First prove from both runtimes' writers that no memory call is already folded into `llm_usage`. If one
      is, stop and report.
- [ ] Answer rate (:485-490): answered ÷ (turns − unknown), with the unknown count stated. With nothing classified,
      print "no scored turn has a known outcome" and no percentage.
- [ ] Hand the controller the runbook's report sentence (:536-541) as exact text.

**Red-before:**
- **Cost source:** `llm_usage` at 0.5814 against ledger rows summing to 0.4163 gives a 0.5814 headline (today 0.4163).
  A memory call appears only in upkeep.
- **Answer rate:** two unknown turns no longer show "0.0%". One answered plus one unknown shows 100.0% of 1, with 1
  unknown.
- **DB lane (serial):** the same on real rows, with `sdk_loop` rows excluded from upkeep and a NULL total counted as
  incomplete.

**Mutation targets:** cost from `llm_model_calls`; all turns in the denominator; `sdk_loop` in upkeep; upkeep added to
the headline.

### Task 5: The SDK loop carries a certified profile
**Owns:** `copilot_mro/app/services/agent_shared/contracts/models.py`,
`copilot_mro/app/services/lang_agent/{profiles,model_certifications}.py`,
`copilot_mro/app/services/{agent_pipeline,agent_shared/pipeline}.py`, `tests/unit/agent_shared/test_model_plan_and_usage.py`,
and a new `tests/unit/agent_shared/test_sdk_loop_profile_identity.py`.
- [ ] Append `ModelRole.SDK_LOOP = "sdk_loop"`, and extend the vocabulary pin (:162) with a comment like `DECISION`'s.
- [ ] `profiles.py` gets one public loop-profile builder. It goes through `_claude_profile` and stamps the registry's own
      revision literal, so the revision has a single source. The literal becomes `pilot-r4`, with an r3→r4 history
      line. `ACTIVATIONS_BY_REVISION` gains `pilot-r4`, activating nothing.
- [ ] `_build_claude_pipeline` (agent_pipeline.py:238-293) builds the profile from `settings.agent_sdk_model or
      DEFAULT_MODEL`, on `aws_bedrock` only; a non-Claude model refuses to compose. It passes the id and revision into
      `AgentPipeline` beside provider and model. `agent_claude` still never imports `lang_agent`.
- [ ] `_resolve_runtime_identity` (pipeline.py:362-384) returns all four fields on the fixed-model path; the lang path is
      unchanged. The accumulator's `runtime` block then carries the profile, and the SDK-turn span (telemetry.py:982)
      picks it up with no telemetry change. The TM seam test in `test_telemetry.py` pins this. Read it; don't edit it.

**Red-before:**
- Bedrock resolves `bedrock-sdk_loop` / `pilot-r4` into the accumulator (today None/None).
- Anthropic-direct and Foundry resolve nothing.
- A non-Claude `AGENT_SDK_MODEL` refuses at build.
- The matrix test passes unedited, and lang is unchanged.
- Two tests build the real `_build_claude_pipeline`:
  `tests/unit/agent_claude/{test_loop_model_propagation,test_served_path_streaming_and_accounting}.py`. Both stay
  green. If one needs an edit, Task 5 owns it and its report says why.

**Mutation targets:** drop the profile id; skip the Bedrock check; give the builder its own literal.

### Task 6: Governed live proof run
**Runner.** A fresh Opus agent, working from the integration worktree after the re-review, following the runbook's
golden-set section.
- **Environment:** api dir and venv, checkout first on PYTHONPATH, `CLAUDE_CODE_USE_BEDROCK=1`, OTLP 127.0.0.1:4318,
  Phoenix 127.0.0.1:6006, dev `copilot_mro`.
- **Evidence:** ids and counts only, written to `~/.claude/scratch/eval-quality-gaps/proof/`.

- [ ] **Preconditions (free).**
  - The owner has run `aws sso login --profile bedrock`.
  - `phoenix.evals` and `litellm` import.
  - `eval_results` exists, and the collector and Phoenix are up.
  - The TF M01 row has not expired (tenant `17be5d65-…`, block `golden-mro-tf1-M01-blk`, 54 refs).
- [ ] **Gap 1, same answer, $0.** Re-project M01 under tag `tf1` from a scratch COPY of `agent-evals-tf/golden-bank.jsonl`
      that carries one superseding M01 record with `projected: false`. The original bank is never edited.
  - **Expect:** a new `internal` root whose retriever span has more than 6 and at most 54 quotes, the marker true, and
    no root citation attributes (the row predates the change).
  - **If the marker is false:** record which condition tripped it.
- [ ] **Gaps 2 + 3, one paid turn (≈ $0.58).** Run `--dry-run` first, then the driver with `--golden-set mro --examples M01
      --tenant-id 17be5d65-… --run-tag eqg1` and its own bank.
  - **Expect:** the log shows `NO_CHAT`.
  - **Expect:** the root's `flynapse.citation_count` equals the bank's `evidence_refs`, and `needs_clarification=false`.
  - **Expect:** the SDK-turn child carries `gen_ai.model.profile=bedrock-sdk_loop` and `registry_revision=pilot-r4`.
  - **Stop:** before judging if the banked cost exceeds $0.90.
- [ ] **Plan mode (free).** `--golden-set mro --since <proof start> --limit 50 --provider bedrock --model
      global.anthropic.claude-haiku-4-5-20251001-v1:0` should match 2 roots with at most 8 judge calls (stop if more).
      The new turn's identity should show `bedrock-sdk_loop` and `pilot-r4`.
- [ ] **Run, then an identical re-run.** Judge calls equal plan mode's count, then 0 on the re-run.
  - **Groundedness:** judged on both full quote sets; record the labels as they come.
  - **`citation_coverage` v3:** `pass` on the new turn (under `__SYSTEM__`, with no facts source), and `not_evaluated`
    on the re-projection.
  - **CloudWatch:** invocations equal judge calls. Compare groundedness input tokens against TF's 12,897.
- [ ] **Reports (free).** Regenerate the dev-tenant and `__SYSTEM__` reports. Cost comes from `llm_usage` plus the
      upkeep column, and the answer rate states its unknowns instead of showing "0.0%".

**Bounds.** One paid turn, never retried without the owner. At most 8 judge calls. All-in cap $1.00.

**Must NOT:**
- run under any tenant but the dev default (dev, demo or platform only, never a customer's);
- change collector, capture-policy, Phoenix or DB config;
- delete Phoenix or `eval_results` data;
- hard-code a judge provider or model (per-run flags only);
- drop `global.` from a Bedrock id;
- ask another example, run a tenant-project eval, or push.

## Review & merge protocol

- [ ] **Per task.** A fresh adversarial Opus reviewer gets the task section, the interface and the diff.
  - It re-runs the red-befores and mutants itself; reports are indexes, not evidence.
  - It returns a claims table with an OPEN count. Critical and Important findings block; Minor ones are fixed or filed.
  - Once cleared, the task merges `--no-ff` into `eval-quality-gaps`.
- [ ] **Final review.** Two fresh Opus reviewers read `e0cdea42..eval-quality-gaps`, with full unit and db lanes at the
      tip. One checks correctness (the Task 1↔2 contract; Task 5's identity → capture → span); the other checks
      completeness and simplicity.
- [ ] **One fix wave**, with a fresh implementer in one worktree, then a scoped re-review.
- [ ] **Task 6.** A defect it exposes stops the batch for the owner; no second fix wave unless the owner asks.
- [ ] **Merge.** Merge `--no-ff` into `langgraph-merge` in the primary checkout, leaving owner WIP untouched. Re-run the
      merged lanes, push, remove the worktrees, and delete branches with `-d`.
- [ ] **Close-out.** The controller writes the Implementation notes and closes the parent plan's covered §10 items.

## Future Improvements

- **Groundedness against the passages synthesis read (D1 option b).** A claim grounded only in an uncited passage reads
  as unfaithful. Deferred because it changes the measure's design, `tools.io` is capture-bounded, and Weaviate
  re-fetches drift. Complete fix: capture synthesis inputs as a bounded evidence set with its own marker, under a new
  measure version.
- **More than ~85 quotes → abstain.** Past that, the child exceeds 64 KiB and reads as incomplete. That is honest, and
  rare today. Complete fix: split the refs across several retriever spans, each with its own marker, and require all of
  them rather than raising the cap.
- **`sdk_loop` ledger rows keep NULL profile columns.** The rows aggregate per model, subagents included;
  `agent_claude` must not import `lang_agent`; and eval subjects read spans. Complete fix: thread the id into
  `record_sdk_model_usage` and stamp only the loop model's row, together with TM's per-model LLM children.
- **Foundry and Anthropic-direct SDK transports have no certified profile.** Complete fix: per-transport profiles
  (e.g. `azure-foundry-sdk_loop`) once those transports have rate cards.
- **`__SYSTEM__` reports keep empty cost and unknown answer sections.** The rows belong to the run tenant (R2c), and D2
  chose Option B. Complete fix: TD's in-band `__SYSTEM__` harness (parent §10), or a driver-declared source tenant for
  report joins.
- **TF readability items (b)–(e) are outside D4.** These are: judges that never judged, a re-run shown as "scores", the
  revision label, and the UUID title. Complete fix: four rendering rules plus fixture rows in `quality_report.py`.
- **Re-projection is manual**, done with a superseding bank record. Complete fix: a driver `--reproject` flag if
  projection changes recur.
- **TF's biased M01 `unfaithful` score stays in dev `eval_results`.** It keeps the same key, so it is skipped, never
  re-judged. Complete fix: an operator supersede path, if this matters beyond dev.

## Lessons

## Implementation notes
