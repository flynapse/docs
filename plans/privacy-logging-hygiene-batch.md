# Privacy & Logging Hygiene Batch — Implementation Plan

> **For agentic workers:** SDD-driven. Controller = the owner's Fable session; implementers and lane
> reviewers = Opus 5.5 subagents, one implementer per working tree, fresh agent per batch. Ledger:
> `.superpowers/sdd/privacy-logging-hygiene-batch/progress.md`. Checkbox syntax tracks progress.

**Goal:** close the approved post-observability residuals — B-R1 exception-text leftovers, the F3
#34/#35 redaction gaps, the chat-delete eval loopholes (liveness gate + Phoenix scrub), F-R2
`error_code`, E-R1/E-R2 CI hygiene, the Weaviate pin, dashboard G.54 layout, and the three
test-isolation bugs — with self-enforcing guards, Opus-only build/review, and **one** final Fable pass
over the privacy-relevant diff.

**Model policy (owner ruling, 2026-09-24):** implementers Opus 5.5; lane reviewers Opus 5.5 (fresh,
adversarial, required to re-run proofs, never self-review); exactly **one Fable 5 review** at the end,
scoped to the combined privacy diff (lanes S + P + T5). Merge-blocking = P0/P1 only; P2/P3 go to
Future Improvements. Concurrency cap 4 (owner, 2026-09-24).

**Evidence base (verified 2026-09-24 against the pushed trees; trust these over plan prose):**
`~/.claude/scratch/privacy-hygiene-batch/research/R1-sink-br1.md` (sinks/census),
`R2-mro-privacy.md` (redaction/delete-path/PipelineResult), `R3-g54-isolation.md` (layout census +
three diagnosed bugs), `R4-ci-weaviate.md` (workflow census, E-R1, Weaviate refs). Trees: copilot-mro
`629a5aa2` · utils `f1d490b` · flynapse-otel `c93a9c9` · dashboard `ed7db1a` · api `a615740` · iac
`011eb67` · core `c8c4fb3`.

## Global constraints

- No exception **message** text in any log record, span attribute, health body or persisted summary —
  type + frame headers only, via `flynapse_otel.failure.failure_fields` / `rendered_failure`.
- No user content (queries, manual text, phone/email) in logs, spans, or unredacted captures.
- Every test run through `pytest-slot.sh -- <cmd>`; Python lanes from the shared `api/.venv`
  (`DEBUG=false`, `POSTGRES_DB=copilot_mro_test` for DB lanes); dashboard unit lane with the canonical
  `--tsconfig tsconfig.test.json` flags; lint via `next lint` only; **never** `next build` in a worktree.
- Mutation proofs (`mutant.sh`, cold bytecode) for every leak-class fix and every new guard; a red
  baseline is refused by the script — fix the baseline first.
- Sibling worktrees under `/home/aditya/Code/<repo>-hyg*`, `.env` symlinked, PYTHONPATH pinned to the
  worktree first; **commit early and often by named pathspec** (new files + test edits; never `git add -A`).
- Nothing merges before its lane review closes; nothing is pushed — the owner pushes.
- No plan-file code snippets (workspace rule); implementers get exact file:line targets instead.

## Rulings needed from the owner (each one word; recommendation first)

- [ ] **R-1 — lambdas in scope?** `lambdas/cognito-lambdas/app.py` (the **auth** lambda) logs full
  tracebacks with loguru `diagnose` ON — that prints **local variable values** on every exception in
  the sign-in path. Recommend: **IN** (worst finding of the batch).
- [ ] **R-2 — phone redaction scope.** Today only `phone:`/`tel=`-labelled numbers are redacted; even
  "Phone number: …" passes. Matching bare digit runs would also eat ATA refs/part numbers. Recommend:
  **widen labels + separator-formatted numbers, never bare digits** (task P1 below).
- [ ] **R-3 — Phoenix scrub mechanism.** Deleted chats' traces stay in Phoenix and get re-annotated on
  every later eval run. Recommend: **delete the Phoenix session (= chat id) on chat delete, best-effort
  inline, plus a replayable script over the deleted-chat copies** for misses and pre-scheme traces.
- [ ] **R-4 — `not_evaluated` exemption from the explanation scrub.** There are exactly 12 fixed
  template strings (counts only, no content). Recommend: **EXEMPT** (keep them readable post-delete).
- [ ] **R-5 — E-R1 disposition.** The `WORKSPACE_READ_TOKEN` steps in `otel-tests.yml:42-55` reference
  a secret that was **never stored**; nothing to rotate. Recommend: **DELETE the two steps** (re-add
  behind a protected environment if ever needed).
- [ ] **R-6 — telegram-bot `FailureFormatter`** prints third-party tracebacks in full. Recommend:
  **DEFER** — parked under your PP-TG-14 "re-triage at detector adoption" ruling; not folded in silently.
- [ ] **R-7 — `persist-credentials: false`** on the 17 self-checkouts. Adjacent hardening beyond the
  E-R2 wording. Recommend: **DEFER** (record here; revisit with B14).

## Lanes

Wave 1 (cap 4): S, P, D, I. Wave 2: T (+ lane reviews as slots free). Lanes are repo-disjoint except
P/I/T touching copilot-mro — three **separate worktrees on file-disjoint branches** (`hyg-privacy`,
`hyg-isolation`, `hyg-tiny`); merge order P → I → T with a full lane rerun after each merge.

### Lane S — B-R1 residuals (worktrees: `utils-hyg`, `flynapse-otel-hyg`, `lambdas-hyg`)

Research correction the implementer must know: the sink layer is **already frames-only**
(`utils/utils/observability/log_bridge.py` — patcher `_withhold_record` :176-210, JSON sink :242-269,
human sink :328-340, OTLP withholding in flynapse-otel `withholding.py:563`). What remains is text the
sink cannot identify (no exception object) and processes that never reach these sinks.

- [ ] **S1 — utils message-embedded sites.** `dynamodb_service.py` :747, :1645 (`{e}`/`Error.Message`
  in the message), :1373/:1378 (`{kwargs}` payloads — request payloads in a log body);
  `scripts/migrate_weaviate_collection.py` :124, :176 (and the text preceding the baked traceback at
  :388). Replace with constant messages + `failure_fields`; kwargs become key-names-only. Red-before
  guard extension in `tests/unit/observability/test_utils_logs_no_exception_text.py`; mutation proof
  per site (`mutant.sh` aimed at the guard).
- [ ] **S2 — cognito lambda (gated on R-1).** `lambdas/cognito-lambdas/app.py`: its own sink at :24-25
  (string format, `diagnose` default ON), `logger.exception` at :426/:465, `str(e)` at :63/:124/:136.
  Reconfigure the sink `diagnose=False, backtrace=False` with a frames-only format; replace the three
  message-embedded sites with type names. Self-contained (no new dependency on utils/otel unless one
  already exists). Add the lambda's first log-privacy test; note the repo's own test layout must follow
  the two-level rule from day one.
- [ ] **S3 — flynapse-otel stderr router.** `flynapse_otel/logging.py:87-89` routes the
  `opentelemetry` logger through a plain formatter — swap to the frames-only rendering already in
  `failure.py`; pin with a planted-exception test.
- [ ] **S4 — `basicConfig` entrypoints (bounded).** Census scripts that configure stdlib logging
  without `setup_logging` (the G.117 class) in utils + copilot-mro `scripts/`; adopt `setup_logging`
  (or the `ExtrasInMessageRecord` factory where a root handler is forbidden — constraint: utils must
  NOT install a root handler on this path or `basicConfig(level=)` breaks). Cap: fix what the census
  finds, list the remainder in Future Improvements with counts.
- [ ] **S5 — adopt the shared detector in utils.** Replace utils' own guard (membership backlog +
  floor, no merge-base ratchet) with `flynapse_otel.testing` exception-text detector (corpus 1617
  rows) + ratchet register, per the merge plan's adoption order (utils first; **no other repo adopts in
  this batch**). Acceptance: ratchet green at HEAD, one seeded regression is caught (mutation-style
  proof), old guard deleted in the same commit.
- Out of scope, recorded: telegram formatter (R-6), the string-extra stdout/OTLP pipe disagreement
  (`failure.py:539` — no live site; Future Improvements).

### Lane P — copilot-mro privacy (worktree `copilot-mro-hyg`, branch `hyg-privacy`)

All in `copilot_mro/app/services/agent_shared/llm_content_capture.py` unless noted; capture code is
colleague-era (`54a01f39`).

- [ ] **P1 — #34 phone redaction (gated on R-2).** Widen `_PHONE_LABEL_RE` (:102-105): label set
  (phone/ph/mob/mobile/telephone/tel/contact/whatsapp + "phone number"), optional filler words before
  the separator, and separator-formatted international forms adjacent to a label. Never bare digit
  runs. New tests: labelled/prose-labelled/formatted numbers redacted; ATA refs, dates, part numbers
  UNTOUCHED (the over-redaction guard the file lacks). Patterns must survive unicode separators —
  U+00AD soft hyphens and en-dashes appear inside AMM-derived text and have broken regexes here
  before; one test plants each. Bump `LLM_TURN_CONTENT_REDACTION_VERSION` (:25) to v2 in the same
  commit as the pattern change.
- [ ] **P2 — #35 truncate-before-redact.** `_redact_and_bound_text` (:537-553) cuts at :545 then
  redacts at :546. Fix shape: cut with a bounded margin, redact, re-cut to budget — the DoS guard
  (`test_llm_content_capture_privacy_red.py:494-527`, redactor input ≤ 4× budget, monkeypatches
  `_redact_generic_text` by name) must stay green. Extend or retire the 128-char tail compensator
  (:556-562) — it has no email/JWT/AWS-key/phone clause; its pinning tests (:260-361) update with it.
  Mutation proof: a secret straddling the old cut boundary is now caught.
- [ ] **P3 — eval-writer liveness gate.** Two seats: (i) runner-side — skip judging (and therefore the
  Phoenix annotation, which `runner.py:126-140` writes BEFORE Postgres) for chats with `deleted=true`;
  (ii) write-side — `results_store.py:68-77` refuses when the chats row exists and is deleted. **The
  gate must treat a missing chats row as live** (golden-set/harness/db rows have none — the join-gate
  pattern silently drops them; follow the `signals.py:35-50` pattern). Tests: deleted chat → no new
  annotation, no new row; golden-set row still lands; the `not_evaluated` path per R-4.
- [ ] **P4 — Phoenix scrub on delete (gated on R-3).** On `delete_chat` (single transaction,
  `chats.py:372-431`), best-effort scrub of the Phoenix session (session id = chat id on current
  traces) — failure never fails the delete, and the miss is replayable: a script sweeping the
  deleted-chat copies (`deleted_chat_copies.py`) deletes their sessions in bulk and finds pre-scheme
  traces by chat-id metadata search. The pinned client (3.5.0) has no annotation delete;
  `sessions.delete`/`bulk_delete` is the mechanism and matches the anonymisation ruling (chat
  artifacts GO). **The scrub must be unable to touch golden/internal sessions** (`golden-set/<set>`
  keys, `internal` project, `__SYSTEM__` tenant): it operates only on ids drawn from the deleted-chat
  copies, and a test proves a golden session id passed by mistake is refused. Tests with a faked
  client: inline scrub called with the right id; failure path logged frames-only; script idempotent.
- [ ] **P5 — F-R2 `error_code`.** Add an optional bounded `error_code` to `PipelineResult`
  (`_result.py:15-40`): populate at `pipeline.py:866` from the `StructuredError` code **already in
  hand and dropped today**, and at `pipeline.py:840` via `turn_facts.turn_error_type` (the existing
  17-code vocabulary — reuse, don't invent); thread through `legacy_adapter.py:407/:543`. Log it at
  the two constant-message sites (`chat_management.py:1260-1264`, :1641-1646). Update
  `integration-contract.md` §2. Tests: code present on failed results, absent on success; the
  log-privacy guard (`test_agent_sdk_ordinary_log_privacy.py:642/661`) and lifecycle pins stay green.
- [ ] **P6 — scrub exemption (after R-4).** Apply the ruled treatment of the 12 `not_evaluated`
  templates (`runner.py:266-291`, `citation_coverage.py:167-190`, `session_runner.py:321-328`) in
  `SCRUB_EVAL_EXPLANATIONS_SQL` (`deleted_chat_copies.py:218-225`); pin with a prefix-id control test
  as the scrub plan did.

### Lane I — isolation bugs (worktree `copilot-mro-hyg-iso`, branch `hyg-isolation`)

- [ ] **I1 — memory `sys.modules` leak (reproduced: 62 passed / 8 errors).** The `memory_db` fixture
  (`tests/unit/memory/test_memory_operator_attribution.py:409-418`, real-name copy :57-63) leaves a
  stand-in package behind; `test_nonagent_lifecycle_spans.py` then errors on `app/api/memory.py:35`.
  Fix: save/restore `sys.modules` in the fixture's teardown. Same flaw fixed in
  `tests/db/work_orders/test_work_order_tree_roundtrip.py:33-50,70` (latent twin). Proof: the R3 repro
  command flips to 70 passed / 0 errors; each file still green alone.
- [ ] **I2 — `test_seed_dev_tenant.py` alone (reproduced).** Its stand-in `copilot_mro.app.services`
  (:301-317) is not a package, so `scripts/seed_dev_tenant.py:1052` → `:319` can't import
  `weaviate_boot_check`. Fix: make the stand-in a real package (set `__path__`, or stub via
  `tests/_package_stubs.ensure_package` — reuse, don't hand-roll). Proof: the file passes ALONE and in
  its lane.
- [ ] **I3 — `[deadline]` flake.** `test_backend_lifecycle_and_failures.py:806-845`: the 50 ms
  deadline (:822) can expire under xdist before the model call starts; the :826 wait then times out.
  Fix: a deadline generous under load with the :831 wait kept strictly larger; assert the mechanism
  (deadline observed) not the timing. Proof: 20 consecutive runs green under `-n 4` (one slot-gated
  loop run by the implementer, logged).

### Lane D — dashboard G.54 (worktree `dashboard-hyg`)

- [ ] **D1 — move the 48 flat files** into `tests/unit/{chat(25), optimizer(15), auth(4), memory(3),
  security(1)}` (per-file table in R3's report; six files have a recorded second choice — take the
  first). Fix the 83 `'../../X'` imports (prefer the `@/` alias, which the runner resolves), **no
  blind replace** (`optimizer-wizard-state.test.ts:752` holds a path-like string as test data);
  update the six stale path comments. Acceptance: unit lane 2533+/0 with canonical flags, `npm run
  typecheck` clean, `npx next lint --file` over moved files clean.
- [ ] **D2 — layout guards (the rule becomes self-enforcing).** New `tests/unit/infra/` node:test
  guards: two-level layout + globally-unique basenames (TS port of `test_test_layout_rules.py`), and
  the depth-coupled-path guard — fixing the five existing depth-coupled sites it flags (e.g.
  `auth/public-paths-single-source.test.ts:37`, `automations/deepLinkConsumption.test.ts:178`).
  Mutation-style proof: a planted flat file / colliding basename / `parents`-style path turns each
  guard red.

### Lane T — tiny estate items (worktrees `copilot-mro-hyg-t` branch `hyg-tiny`, `api-hyg`, `iac-hyg`, + one-file edits in utils/core/dashboard/flynapse-otel workflows)

- [ ] **T1 — fix the red `otel-tests` CI lane first** (red on the last 3 pushes: 3 collection errors —
  the lane installs only pytest+pyyaml but now collects tests importing `loguru`/`utils`). Diagnose,
  then either scope collection to the otel statics or install the two deps; acceptance = a green run
  reachable from the workflow's own steps executed locally.
- [ ] **T2 — E-R2 `permissions: contents: read`**, top-level, in all 16 workflow files (7 repos; plus
  lambdas + llm-platform per the estate-wide wording). iac: top-level in `terraform-plan.yaml` /
  `terraform-apply.yaml` ONLY — the guard-lane test (`test_workflows_gate_on_the_guards.py:44-47,145`)
  whitelists `guards.yaml` keys, and a called workflow inherits its caller's cap. The approval flow
  (secret comparison + stored `GIT_TOKEN`) is untouched by `contents: read`.
- [ ] **T3 — E-R1 (gated on R-5).** Delete `otel-tests.yml:42-55` (the never-stored
  `WORKSPACE_READ_TOKEN` steps), or move per the owner's alternative.
- [ ] **T4 — Weaviate pin.** Pin `semitechnologies/weaviate:1.34.8` (live dev digest-verified) at:
  `deployment/docker-compose.yml:222`, `deployment/demo/docker-compose.yml:35`,
  `deployment/poc/docker-compose.yml:187`, `deployment/weaviate-local/weaviate-docker-compose.yml:4`,
  and the `chat-eval.yml:37` fallback; correct the stale `1.22.4` doc snippet. Extend the existing
  image-pin test to cover the standalone file it misses. **Deploy note for the owner:** demo/POC boxes
  are unmeasured — recreating their containers on the pin may upgrade them in place; bind mounts
  persist data, and the restart trap (stop/start, never re-provision) applies.
- [ ] **T5 — api executor log site.** `api/flynapse_api/automations/executor.py:1416-1420` logs
  `result.error` in an f-string — constant message + `error_type` (+ `error_code` once P5 is merged;
  T5 merges after P5). Guard test in api's suite; joins the Fable-pass scope.

## Review & merge protocol

1. Per lane: implementer (Opus) → fresh adversarial Opus reviewer briefed with this plan section + the
   actual diff, **required to re-run** the named proofs (mutation runs, red-befores, repro commands) —
   claims files are indexes, never evidence. Verdict-gated: P0/P1 fix rounds only; P2/P3 → Future
   Improvements. Reviewer writes an incremental claims file under
   `~/.claude/scratch/privacy-hygiene-batch/<lane>/`.
2. Merge per lane after its verdict (copilot-mro order P → I → T, full lane rerun after each);
   estate-wide full lanes at the end on the merged trees.
3. **Single Fable 5 pass** over the combined privacy diff only (lanes S + P + T5, pinned SHAs) —
   the pre-push gate. P0/P1 fixed before push; everything else recorded.
4. Owner pushes; nothing is published.

## Decision packets (controller-authored appendices, no agents)

- [ ] **G.17 packet:** the current census (27 instruments carry `tenant_id` uncapped — deliberate, not
  a violation; merge-pass recommendation: do NOT tenant-scope the four new instruments; histograms
  already stripped per M-GENAI-TENANT) → a one-page allow-list table with per-instrument recommendation
  for the owner to tick.
- [ ] **C4 packet:** measurement recipe (docker stats against the compose smoke, which boots and tears
  down cleanly) + a recommended budget from the captured numbers; the owner picks the number.
- [ ] **B14 packet:** condense the decision sheet's recommendation (1) (DB-enforced tenant-delete
  authorization) into a mini-plan skeleton for its own later project.

## Future Improvements

- String extras on stdout (`failure.py:539`): the JSON/human sinks pass string extras unchanged while
  the OTLP pipe reduces them — the two pipes disagree; no live site today.
- `persist-credentials: false` estate-wide (R-7, if deferred).
- telegram-bot `FailureFormatter` + PP-TG-14 re-triage (R-6, if deferred).
- Detector adoption beyond utils (core → api → copilot-mro → telegram → shift, the merge plan's order).
- basicConfig census remainder from S4, if any.

## Lessons

_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule next time)_

## Implementation notes

_(per lane, filled as work lands)_
