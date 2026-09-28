# Eval quality gaps — full groundedness evidence, trace-carried citation state, SDK-loop profile, honest report

> **SDD-driven.** Controller: the owner's Opus session. **Model policy:** implementers and reviewers are Opus 5.5,
> with a fresh agent per task, one implementer per working tree, and at most 2 running at once (the owner raised it to 6, shared across the three follow-up programs, for this batch).
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
- The judge reads every distinct quote. The copy keys a sourced ref on its source and its quote (a source-less badge on
  its whole self), and the harness hands each distinct quote text to the judge once. Badge refs (DATA, export, upload)
  are never judge evidence.
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
- [x] Cut `eval-quality-gaps` at `e0cdea42`. Baseline the lanes, and write the red set and the fixed interface to the
      ledger.
- [x] In the parent plan, add the D2 amendment on §7 Q2 and on §10 item 2. Point TF's three §10 items (truncated
      evidence, headless `citation_coverage`, report cost) and TM claim-4 at this plan. Commit that with this plan.

## Tasks

### Task 1: The content copy carries every distinct quote and the turn's citation state
**Owns:** `copilot_mro/app/services/agent_shared/{telemetry,llm_content_capture}.py`,
`tests/unit/agent_shared/test_telemetry.py`, `tests/unit/agent_shared/test_llm_content_capture*.py`, and a new
`tests/unit/agent_shared/test_content_copy_citation_state.py`. `test_llm_content_capture.py:232` pins the exact `outcome`
dict and must be updated. Grep for any other test that pins the `outcome` shape or a copy span's exact attribute set,
and list each one in the report.
- [x] `_deduped_evidence_refs` (telemetry.py:1298-1314) also keys on `cited_text`, or on `text` where a ref has one.
      That is the harvest's own identity (`_cited_core.py:495`). `evidence_count` then counts the refs kept.
- [x] `_retriever_span_specs` stamps `evidence_complete`, true only if the child was not shortened for projection,
      `limits` has no `omitted_evidence_refs` and no `evidence_refs_truncated` (ruling E1-M1), and no retained ref
      carries `_truncated_items`.
- [x] The `outcome` of `_build_v2_snapshot` (llm_content_capture.py:1425) gains two fields:
  - `citation_count`: the length of the list `AgentPipeline._pipeline_result` hands on (the backend's
    `metadata.citations`, else `evidence_refs`), counted before any capture bound.
  - `needs_clarification`: from the finalized outcome's `metadata["needs_clarification"]`, else `post_turn_signals`,
    else false. Amended by ruling E1-C1, because finalize clears the signals.

  Both survive every fit step, including `minimal` (:1300). The v1 builder is left alone: it runs only without an
  accumulator, and its copies abstain.
- [x] The root span stamps both scalars when the row carries them (telemetry.py ~:1777-1792), and neither otherwise.
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

**Post-review change (owner decision 34, 2026-09-28; found by the Task 6 proof run):**
- **What the proof run found.** The retriever child projects each ref whole. On a real turn about 70% of a ref's bytes
  are `viewer_reference`, the chat viewer's click-to-open payload, which no judge reads.
  - TF M01 has 52 distinct refs: 132,222 B, against quotes of about 14 KB.
  - The 64 KiB child therefore overflows at about 26–28 refs, and the marker reads false on an ordinary cited answer.
- **The change.** The retriever child projects each ref as its judge-relevant fields only. The fields kept are those
  the evaluators and the adapter actually read, derived from those consumers rather than assumed: the source identity
  and the quoted text.
- **What stays the same.**
  - The row keeps the whole refs.
  - The marker's rule is unchanged: a slim copy that still overflows reads false.
  - Dedup identity is unchanged.
- [ ] Slim projection built, reviewed and merged on `eval-quality-gaps`; then the Task 6 paid turn is re-run.

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
- [x] `EvaluationCandidate` (contracts.py:615) gains the three fields, type-checked. A non-bool or non-integral value
      reads as None and is never coerced, except that an integral float widened by the dataframe reads as its integer.
- [x] Adapter. `evidence_complete` is true only when every retriever row says true. The count and the flag come from the
      root. Both shapes real Phoenix returns are read: nested `attributes.flynapse` on the root, flat dotted keys on
      children.
- [x] `runner._missing_judge_inputs` (:335-360): groundedness whose evidence is present but incomplete returns "Evidence
      is incomplete in the content copy." That is a free `not_evaluated`, and plan mode (`planner.py`) counts no judge
      call for it.
- [x] `citation_coverage` v3 takes the candidate only and keeps v2's label table. Either field absent →
      `not_evaluated` ("The content copy carries no citation state."). Version `citation-coverage-v3`, so every v2
      verdict is re-evaluated.
- [x] Retire `CitationFacts`, `CitationFactsLookup`, `PostgresCitationFacts`, `CITATION_FACTS_SQL`, the runner's
      `citation_facts` parameter, and `run_phoenix_evals._citation_facts` (:180, :378-385). Grep every docstring that
      names them, e.g. `results_store.py:120`.
- [x] Runbook notes: groundedness judges distinct quotes and abstains on incomplete or old copies; `citation_coverage`
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
- [x] `record_settled_turn_facts` (:112-160) stops ignoring `_default_execute`'s rowcount (:87-109):
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
- [x] `COST_SQL` (:109-119) prices each scored turn from `llm_usage.total_cost_usd` on `(tenant_id, block_id)`. It reports
      turns with a ledger row, turns with `cost_complete = false`, and the complete-cost sum. Cost per query divides by
      the complete-cost turns and says so. The reporting role already has the grant (`provision_rls.py:269-275`).
- [x] A separate upkeep column: `llm_model_calls` rows with role `memory` and origin ≠ `sdk_loop`, never added to the
      headline. First prove from both runtimes' writers that no memory call is already folded into `llm_usage`. If one
      is, stop and report.
- [x] Answer rate (:485-490): answered ÷ (turns − unknown), with the unknown count stated. With nothing classified,
      print "no scored turn has a known outcome" and no percentage.
- [x] Hand the controller the runbook's report sentence (:536-541) as exact text.

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
- [x] Append `ModelRole.SDK_LOOP = "sdk_loop"`, and extend the vocabulary pin (:162) with a comment like `DECISION`'s.
- [x] `profiles.py` gets one public loop-profile builder. It goes through `_claude_profile` and stamps the registry's own
      revision literal, so the revision has a single source. The literal becomes `pilot-r4`, with an r3→r4 history
      line. `ACTIVATIONS_BY_REVISION` gains `pilot-r4`, activating nothing.
- [x] `_build_claude_pipeline` (agent_pipeline.py:238-293) builds the profile from `settings.agent_sdk_model or
      DEFAULT_MODEL`, on `aws_bedrock` only; a non-Claude model refuses to compose. It passes the id and revision into
      `AgentPipeline` beside provider and model. `agent_claude` still never imports `lang_agent`.
- [x] `_resolve_runtime_identity` (pipeline.py:362-384) returns all four fields on the fixed-model path; the lang path is
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
- **Readout (content-free).** Span attributes are read read-only through Phoenix REST (`GET
  $PHOENIX_ENDPOINT/v1/projects/internal/spans`, paged, with the runbook's auth header where Phoenix needs one), piped
  straight into a short Python filter that prints, per span, only its id, parent id, kind and whichever of these it
  carries: `gen_ai.retrieval.evidence_count`, `flynapse.content_copy.evidence_complete`,
  `flynapse.content_copy.truncated`, `flynapse.citation_count`, `flynapse.needs_clarification`, `gen_ai.model.profile`,
  `gen_ai.model.registry_revision`. The filter reads both the nested `attributes.flynapse` shape and flat dotted keys.
  The response body is never written anywhere; only the filter's output goes to `proof/`. Plan mode's identity joins
  every LLM span's profile and revision, so it cannot stand in for the SDK-turn child's own attributes (final review
  H-1).
- **Time windows (final review CORR I-1).** A re-projected copy's root takes its time from the row's
  `outcome.completed_at_unix_nano`, so the TF M01 re-projection is dated 2026-09-23, not the proof day. `--since <proof
  start>` therefore sees only the new turn. The re-projection is located for the readout by the trace/span id the
  re-projection step reports, never by `--since`, and it is not judged: widening `--since` would pull in the original
  TF root and a two-turn session and reach the judge-call cap.

- [ ] **Preconditions (free).**
  - The owner has run `aws sso login --profile bedrock`.
  - `phoenix.evals` and `litellm` import.
  - `eval_results` exists, and the collector and Phoenix are up.
  - The TF M01 row has not expired (tenant `17be5d65-…`, block `golden-mro-tf1-M01-blk`, 54 refs).
  - The reporting role authenticates: `generate_quality_report.py --tenant 17be5d65-… --database copilot_mro --out
    <proof>/report-pre` prints its JSON line. Task 4 measured `password authentication failed for user
    "flynapse_readonly"` on this cluster (ruling E4-C1). If it fails, stop for the owner before the paid turn.
- [ ] **Gap 1 on the copy, $0.** Re-project M01 under tag `tf1` from a scratch COPY of `agent-evals-tf/golden-bank.jsonl`
      that carries one superseding M01 record with `projected: false`. The original bank is never edited.
  - **Expect (readout, by the re-projection's own ids):** a new `internal` root whose retriever span has more than 6
    and at most 54 quotes, the marker true, and no root citation attributes (the row predates the change).
  - **If the marker is false:** record which of the four conditions tripped it (`telemetry._evidence_complete`): the
    retriever span's own `flynapse.content_copy.truncated`; the row's `content.limits` keys `omitted_evidence_refs` or
    `evidence_refs_truncated`; or a retained ref carrying `_truncated_items`. Key names and counts only. This is honest
    abstention, not a defect.
- [ ] **Gaps 1–3 on a new turn, one paid turn (≈ $0.58).** Run `--dry-run` first, then the driver with `--golden-set mro
      --examples M01 --tenant-id 17be5d65-… --run-tag eqg1` and its own bank.
  - **Expect:** the log shows exactly one WARNING `chat_turn_facts: settled turn not recorded — no chat row`, carrying
    the run tenant and `golden-mro-eqg1-M01-blk`. That is the settle writer's `NO_CHAT`; the token itself is returned,
    never logged.
  - **Expect (readout):** the root's `flynapse.citation_count` equals the bank's `evidence_refs`, and
    `needs_clarification=false`; the retriever span carries the marker true and the turn's full distinct-quote count.
  - **Expect (readout):** the SDK-turn child carries `gen_ai.model.profile=bedrock-sdk_loop` and
    `gen_ai.model.registry_revision=pilot-r4`.
  - **Stop:** before judging if the banked cost exceeds $0.90.
- [ ] **Plan mode (free).** `--golden-set mro --since <proof start> --limit 50 --provider bedrock --model
      global.anthropic.claude-haiku-4-5-20251001-v1:0` should match 1 root (the new turn) with at most 8 judge calls
      (stop if more). The new turn's identity `profile` should include `bedrock-sdk_loop` (the token joins every LLM
      span's profile, e.g. `bedrock-classification,bedrock-memory,bedrock-sdk_loop`) and its `registry_revision` should
      read `pilot-r4`. The readout, not plan mode, proves the SDK-turn child's own revision.
- [ ] **Run, then an identical re-run.** Judge calls equal plan mode's count, then 0 on the re-run.
  - **Groundedness:** judged on the new turn's full distinct-quote set (Gap 1's judge path); record the label as it
    comes.
  - **`citation_coverage` v3:** `pass` on the new turn (under `__SYSTEM__`, with no facts source).
  - **CloudWatch:** invocations equal judge calls. Compare the run minute's input tokens against TF's 12,897. That
    figure was the whole TF golden-run minute: 3 calls on one root (relevance, groundedness, trajectory); CloudWatch
    cannot split tokens by measure. Expect roughly one TF-sized minute plus about 4–5K tokens for groundedness now
    reading M01's full quote set (≈ 19.6K chars, against TF's 2,179).
- [ ] **Reports (free).** Regenerate the dev-tenant and `__SYSTEM__` reports. Cost comes from `llm_usage` plus the
      upkeep column, and the answer rate states its unknowns instead of showing "0.0%". The `__SYSTEM__` report's
      revision comparison sets TF's M01 (`pilot-r3`, TF's biased `unfaithful` included) against the new M01
      (`pilot-r4`); the difference is the evidence fix plus the relabel, not a model change, and the proof notes say so.

**Bounds.** One paid turn, never retried without the owner. At most 8 judge calls. All-in cap $1.00.

**Must NOT:**
- run under any tenant but the dev default (dev, demo or platform only, never a customer's);
- change collector, capture-policy, Phoenix or DB config;
- delete Phoenix or `eval_results` data;
- hard-code a judge provider or model (per-run flags only);
- drop `global.` from a Bedrock id;
- ask another example, run a tenant-project eval, or push.

## Review & merge protocol

- [x] **Per task.** A fresh adversarial Opus reviewer gets the task section, the interface and the diff.
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
- **Too many quotes → abstain.** Past the 64 KiB child cap, the copy reads as incomplete. The "~85" estimate was wrong:
  with whole refs the measured cap was about 26–28 refs (Task 6 proof run, 2026-09-28), which is why decision 34 slims
  the projection. After slimming, the cap is set by the quote bytes alone. That is honest, and rare. Complete fix: split the refs across several retriever spans, each with its own marker, rather than raising
  the cap. The interface ("every retriever copy span"), R-D1 ("every retriever span says true") and the adapter's
  `_extract_evidence` already read N retriever spans, so the split is a projection change only
  (`telemetry._retriever_span_specs`) (ruling E1-M5).
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

Recorded at the final review (2026-09-28); detail in `.superpowers/sdd/eval-quality-gaps/final-review-completeness.md`
§5:
- **`citation_coverage` cannot label `fail` on the Claude SDK path (E2-m1; absorbs parent §10's TB-filed item).**
  - *What is missing:* the copy carries no count of evidence a turn *retrieved*. On the SDK path `evidence_refs` IS the
    citation list (`query_adapter.py:395`), so an uncited turn has no retriever span and scores `pass`.
  - *Why deferred:* it predates this plan (v2 read the same list). The persisted explanation was corrected in the fix
    wave so the record stays honest.
  - *Complete fix:* stamp a content-free `flynapse.retrieved_evidence_count` on the copy root, counted from the
    retrieval tools' results. A `citation-coverage-v4` reads it for the `fail` row. Alternatively, the owner relabels
    the measure "did the turn cite anything".
- **Lang-runtime turns show no headline cost (E4-C2).**
  - *What is missing:* a lang turn writes no `llm_usage` row, so it counts under "no ledger row".
  - *Complete fix:* the lang runtime writes the same turn-ledger row at settle. Failing that, the report adds a
    separately labelled per-call fallback column, never mixed into the complete cost.
- **Upkeep columns count attempts that moved no money (T4-m2).**
  - *What is missing:* failed and budget-refused gateway attempts are NULL-cost memory rows, which inflate the upkeep
    and unpriced counts. It never reaches the headline.
  - *Complete fix:* count a row as unpriced only with tokens or `outcome='success'`, or split the column into calls and
    attempts.
- **`_truncated_items` is projected as a ref (T1-C2).**
  - *What is missing:* 120 citations read `evidence_count` 101, and the fit arithmetic ignores the entry. The marker is
    false in exactly that case, so the judge abstains.
  - *Complete fix:* `_deduped_evidence_refs` drops the entry from the projected refs and the count.
- **One badge predicate, owned by its producer (T2-i1).**
  - *What is missing:* the production grounding judge (`_judge_core.py:73`) skips DATA/export refs but not
    `upload_ref`, and its comment mis-states the export text. Telemetry, the adapter and the judge each define "badge"
    differently.
  - *Complete fix:* `is_badge_citation` plus `BADGE_REF_KEYS` in `_cited_core`, used by the judge and telemetry,
    mirrored by the adapter under a parity test.
- **A copy whose fit dropped every ref gets the wrong reason (final review CORR M-1, T2 review i3).**
  - *What is missing:* under the `minimal`/`tiny` fits no retriever span is emitted, so groundedness reads "Missing
    retrieval evidence." rather than "Evidence is incomplete". Both are free abstentions.
  - *Complete fix:* emit an evidence-less retriever span with the marker false when refs were omitted and none survived.
- **No compose case posts `evidence_complete=false` (T2 review i4).** *Complete fix:* one posted marker-false turn in
  `test_phoenix_evaluation_boundary.py`, asserting a free `not_evaluated`.
- **Nothing pins memory spend outside the `llm_usage` snapshot (T4 review I-2).**
  - *What is missing:* disjointness rests on ordering, so a reorder would double-price silently.
  - *Complete fix:* a Claude-runtime unit test that the memory hooks run only after `run_query` returns and never fold
    into the accumulator snapshot.
- **The planner restates the runner's selection (final review m-4).** *Complete fix:* one runner function yields the
  planned work items, and `plan_candidates` calls it; the drift test then goes.
- **The capture mirrors `_pipeline_result`'s citation rule (final review m-2).** *Complete fix:* one
  `handed_on_citations(outcome)` helper beside `RuntimeOutcome`, called by both; the parity test becomes a unit test.
- **Plan mode as the proof's readout (final review H-1, optional).** *Complete fix:* the plan payload gains a
  content-free per-candidate block (root span id, evidence count, marker, citation count, needs_clarification), so
  future proofs need no Phoenix REST read for the copy's statements.

## Lessons

## Implementation notes

**Status at compaction checkpoint 1 (2026-09-27):** integration branch `eval-quality-gaps` (worktree
`copilot-mro-eqg`) carries Tasks 5 and 1 (`2102a74b`, `d947e90b`); Task 2 and Task 4 building, Task 3 in review. Env
red set empty (the one baseline red needed the database); compose boundary test green at `d947e90b`. Ledger
`/home/aditya/Code/.superpowers/sdd/eval-quality-gaps/progress.md`.

#### Notes: Task 5 — SDK-loop profile: DONE + MERGED (`2102a74b`; review APPROVED)
- `bedrock-sdk_loop` @ `pilot-r4` on Bedrock only; a non-Claude `AGENT_SDK_MODEL` refuses at composition (on Bedrock,
  a model the rate card cannot match stops the Claude runtime — fail-closed per R-D3; nothing deployed sets the
  variable). Tests prove the revision is single-sourced (registry probe) and drive a real Bedrock composition through
  capture to the SDK-turn span.

#### Notes: Task 1 — content copy: DONE + MERGED (`d947e90b`; review APPROVED after one fix round)
- **Plan amendment (controller ruling E1-C1, from a Critical review finding):** `needs_clarification` reads the
  finalized outcome's `metadata["needs_clarification"]` first, then `post_turn_signals`, then false — the capture only
  ever sees the FINALIZED outcome, whose `post_turn_signals` the lifecycle nulls, so the plan's "from
  `post_turn_signals`" would have been false on every production turn (a clarification turn would score FAIL under v3).
- Also: a stale first-fit `omitted_evidence_refs` is dropped on rebuild (kept, b80caf90); `limits.evidence_refs_truncated`
  (one quote over the per-string cap) makes the marker false; source-less badge refs keep whole-dict identity; the row
  pass no longer re-captures input it already holds.
- Future Improvement wording to correct at close-out (E1-M5): several retriever spans are already allowed by the
  interface, R-D1 and `_extract_evidence`; splitting refs across spans is a projection change only.
- Learning: a plan that names a field's SOURCE must be checked against the object the reader actually sees (finalized
  vs in-flight) — seam tests on hand-built objects hid it.

**Status at compaction checkpoint 2 (2026-09-27, later):** `eval-quality-gaps` @ `9a7cb05a` carries Tasks 5, 1, 3;
Tasks 2 and 4 in task review. Then: merges, final review, one fix wave, the governed proof run (Task 6), mainline merge
after the OD-5 push.

#### Notes: Task 3 — settle writer: DONE + MERGED (`9a7cb05a`; review APPROVED after one test-only round)
- `WRITTEN` only when a row landed; `NO_CHAT` (one ids-only WARNING) when no chat row exists; `ALREADY_SETTLED` for a
  repeat settle; a failing presence read is `FAILED` (pinned in the fix round). Every headless turn now logs one
  `NO_CHAT` WARNING — the intended signal; Task 6 will show it.

#### Notes: Task 2 — harness: DONE + MERGED (`ebec8197`; review APPROVED, 0 Critical / 0 Important)
- Groundedness is judged only when every retriever span vouches `evidence_complete=true`; an unmarked (pre-batch) copy
  abstains for free. `citation_coverage` v3 reads the copy's root and nothing else. The v2 facts path is retired end to
  end.
- Beyond the task text: badge refs (no `source_id` plus a `data_view_ref`/`export_ref`/`upload_ref`) are never judge
  evidence, but still count as citations. `deleted_chat_copies.NOT_EVALUATED_REASONS` gains the two new reasons and
  drops the four v2 ones (E2-C1). Three unowned fixtures gained `evidence_complete=True` (E2-C3). The compose helper
  stamps the marker (E2-C2).
- Learning: on the Claude SDK path the retriever span IS the citation list (`query_adapter.py:395`), so
  `citation_coverage`'s `fail` row cannot fire there (E2-m1; see Future Improvements).
- Merge note: no textual conflict with the erasure branches (they do not touch `deleted_chat_copies.py`); this branch's
  10-reason list goes in as is, and the AST guard enforces it.

#### Notes: Task 4 — quality report: DONE + MERGED (`4c8dfced`, runbook sentence `d661c599`; review APPROVED after one test + wording round)
- The headline is `llm_usage.total_cost_usd` summed over the cost-complete turns and divided by their count, with the
  ledger-row and incomplete counts beside it. Upkeep is `llm_model_calls` rows with role `memory` and origin ≠
  `sdk_loop`, in its own column and never added. The answer rate is over known outcomes, with the unknown count stated,
  and there is no rate when none is known.
- Pre-check proven by both the implementer and the reviewer: no memory call reaches `llm_usage` on either runtime.
  Claude writes the row inside `run_query` and memory runs after it; lang writes none.
- The `flynapse_readonly` path was not exercised on this machine (E4-C1); a superuser read-only run of the same SQL
  stands in. Task 6 now checks the role before the paid turn.

**Status at the final review (2026-09-28):** `eval-quality-gaps` @ `d661c599` carries Tasks 5, 1, 3, 2 and 4.
Post-merge: unit 7545 passed, with one known lang_agent load flake; db 66 passed. Final review: two Opus lenses, both
with no code-level Critical or Important finding. Three Important Task 6 procedure gaps (the readout, the NO_CHAT log
text, the reporting-role precondition) and the time-window correction are written into Task 6 above. One fix wave
(test, prose and one persisted explanation string) is in flight, then a scoped re-review, Task 6, and the mainline
merge after OD-5's push.

**Status at compaction checkpoint 3 (2026-09-28):** `eval-quality-gaps` @ `7f97250a` carries Tasks 5, 1, 3, 2 and 4, plus the
final fix wave. The persisted explanation now reads "No citation needed: the content copy carries no retrieved
evidence."; the rest of the wave is prose, a `sys.modules` snapshot and the upkeep-role pin. The scoped re-review was
clean. The owner has logged in to Bedrock, and Task 6 (the governed proof run) is in flight. Then: merge into
`langgraph-merge`, push, clean up, and close out.
