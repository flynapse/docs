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

**ALL SEVEN RULED AS RECOMMENDED (owner, 2026-09-24: "agree on all"). Launch authorized.**

- [x] **R-1 — lambdas in scope?** `lambdas/cognito-lambdas/app.py` (the **auth** lambda) logs full
  tracebacks with loguru `diagnose` ON — that prints **local variable values** on every exception in
  the sign-in path. Recommend: **IN** (worst finding of the batch).
- [x] **R-2 — phone redaction scope.** Today only `phone:`/`tel=`-labelled numbers are redacted; even
  "Phone number: …" passes. Matching bare digit runs would also eat ATA refs/part numbers. Recommend:
  **widen labels + separator-formatted numbers, never bare digits** (task P1 below).
- [x] **R-3 — Phoenix scrub mechanism.** Deleted chats' traces stay in Phoenix and get re-annotated on
  every later eval run. Recommend: **delete the Phoenix session (= chat id) on chat delete, best-effort
  inline, plus a replayable script over the deleted-chat copies** for misses and pre-scheme traces.
- [x] **R-4 — `not_evaluated` exemption from the explanation scrub.** There are exactly 12 fixed
  template strings (counts only, no content). Recommend: **EXEMPT** (keep them readable post-delete).
- [x] **R-5 — E-R1 disposition.** The `WORKSPACE_READ_TOKEN` steps in `otel-tests.yml:42-55` reference
  a secret that was **never stored**; nothing to rotate. Recommend: **DELETE the two steps** (re-add
  behind a protected environment if ever needed).
- [x] **R-6 — telegram-bot `FailureFormatter`** prints third-party tracebacks in full. Recommend:
  **DEFER** — parked under your PP-TG-14 "re-triage at detector adoption" ruling; not folded in silently.
- [x] **R-7 — `persist-credentials: false`** on the 17 self-checkouts. Adjacent hardening beyond the
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
   estate-wide full lanes at the end on the merged trees. **Lane S (utils) must land as a true
   MERGE — never rebase or squash it**: the S5 ratchet anchors on the adoption commit, and a
   rewritten history turns the guard red (fails closed, measured) until its anchor is updated.
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
- basicConfig census remainder from S4, if any. *(Measured by lane S: zero uncovered in-scope
  scripts — all 10 copilot-mro basicConfig scripts import utils and are covered by the
  record-factory fix; telegram-bot stays with R-6.)*

*From the lane S review (P2/P3, recorded not blocking; evidence under
`~/.claude/scratch/privacy-hygiene-batch/S/review/`):*
- **Estate-wide loguru pre-sink leak (P2):** loguru formats the exception before any sink runs;
  if that formatting raises (measured with a SyntaxError carrying a non-integer offset), loguru's
  own error handler prints the whole record — exception text included — to stderr, through both
  the lambda sink and utils' default sink. Predates the lane. Fix sketch: a patcher moves the
  record's exception into an extra so loguru never formats it and sinks render from the extra.
- dynamodb health bodies still carry raw `Error.Code` unchecked at :1667/:1717-1718;
  `aws_error_code()` exists and would close it (P2).
- Stale prose: `log_bridge.py:58` ("33 format_exc sites left"), the stdout-sinks test :128
  ("still writes 32 times"), spans guard :156 ("sibling LOG sweep" — deleted) (P3).
- The S1 mutant script targets the deleted old guard; superseded by S5's L1–L6 (P3).
- dynamodb `delete_by_prefix`/`delete_by_contains` dry-run lines log prefix values and sample
  item keys/values — predates the lane, outside S1's named sites (P3).
- flynapse-otel's stderr handler silently drops a record whose format fails where utils writes a
  constant + template — no leak, but the failure goes invisible (P3).
- The Lambda runtime's stdlib root handler would render third-party library records in full; no
  live site today, no declared limit (P3).
- Cognito PostConfirmation still logs the opaque `userAttributes.sub` (P3; not a name/email/phone).

*From the lane S implementer:*
- utils' `intercept._TypesAndFramesFormatter` duplicates `flynapse_otel.logging.TypesAndFramesFormatter`;
  utils should import the otel copy once both lanes are merged (deferred: the symbol exists only
  on hyg-sink until then).
- dynamodb debug lines still log key VALUES (get/update/delete_item, put_item id) — identifiers,
  not payloads.
- stdlib `Handler.handleError` still prints the template + args on a failed %-format (declared in
  the `_stdlib_records` docstring).
- lambdas repo has no `tests/_root.py` and no layout/depth guards; its smoke test uses `parents[2]`.
- telegram-bot's telemetry test docstring names the deleted utils guard path (out of lane S's trees).
- utils' span sweep overlaps the shared detector's span rules; retire in a later adoption pass.
- The `_root.py` debt register could adopt the same merge-base ratchet.

*From the lane I review (P2/P3, recorded not blocking; evidence under
`~/.claude/scratch/privacy-hygiene-batch/I/review/`):*
- **F-1 (P2):** the work_orders load-time registration leaves `copilot_mro.app.db.row_tenancy`
  and `.postgres_table_definitions` in `sys.modules` without attaching them to the real
  `copilot_mro.app.db` package, so a later file's string-target
  `monkeypatch.setattr("copilot_mro.app.db.row_tenancy…")` raises AttributeError (measured:
  work_orders + chunking's test_chunk_id_derivation = 3 failed / 13 passed). A plain real-package
  import in that file (as tests/db/improvement already does) gives 16/16 and 55/55 — the cleaner
  future shape. No current lane runs the failing pair together.
- **N-3 (P2):** the work_orders fix is only protected by a selective run (improvement +
  work_orders without chat_history); the full tests/db lane masks both the original bug and any
  regression. The collection-finish placeholder check (test-hygiene audit §6 item 7) closes this.
- **N-1 (P3):** the I3 test's "window spent only in flight" claim holds only because
  `ModelGateway.invoke` has no await before `transport.invoke`; a 200 ms await there would
  reintroduce a 10 s timeout failure. The docstring overstates slightly.
- **N-2 (P3):** on a start-wait timeout the backend task is left uncancelled for loop teardown.

*From the lane I implementer (`~/.claude/scratch/privacy-hygiene-batch/I/NOTES.md`):*
- `tests/db/chat_history/test_chat_history_roundtrip.py:33-65` has the same collection-time-stub
  /teardown-restore flaw as work_orders had; masked today by agent_state's concrete-import workaround.
- 43 of 63 `ensure_package` caller files have no restoring helper (grep heuristic; census in
  `I/ensure-package-no-restore-census.txt`). Self-enforcing fix = the collection-finish placeholder
  check from the test-hygiene audit (§6 item 7, never landed); `_sdk_loader.repair_stubbed_copilot_packages`
  skips anything with a `__path__` so it never repairs these.
- A production clock seam in `lang_agent/controls.py` would let the I3 test stop patching a module
  global.
- tests/db/tenancy/test_data_discovery_rls_isolation.py: 12 pre-existing errors — test-DB schema
  drift (`data_discovery_jobs.object_count` NOT NULL) — needs its own triage.

*From the lane D review (P2/P3, recorded not blocking; evidence under
`~/.claude/scratch/privacy-hygiene-batch/D/review/`):*
- The depth guard misses 4 uncommon spellings (a variable holding a `'../../..'` string, an
  array-join of `'..'` segments, spread arguments, a default parameter aliasing `__dirname`) —
  the Python original misses the same 4, so this is an inherited limit; the guard docstring
  slightly overstates what intermediate-variable tracking catches (anchors are tracked, `'..'`
  strings are not).
- An exemption's reason is only required by the type, so an empty string would compile (same in
  the Python original).
- `runErrorVocabulary.test.ts` hard-fails rather than reporting partial coverage when only one
  of its two backend sibling checkouts exists (not lane D's file; surfaced by the new sibling
  worktrees).
- **Operational note:** the dashboard unit lane's result depends on which sibling checkouts
  exist beside the repo (`core`/`api` by name suffix): with both present two formerly-skipped
  tests run. On the primary checkout the siblings are the primary repos — the production shape.

*From the lane P implementer (`~/.claude/scratch/privacy-hygiene-batch/P/NOTES.md`):*
- The inline Phoenix reap runs synchronously inside the async `delete_chat` handler (as the S3
  and Weaviate reaps already do). After fix P-R1 the cost of a silent Phoenix is ONE ~5 s bound
  (every request rides a 5 s httpx timeout and the first failure ends the reap; a slow-drip
  server is capped per read, not in total), and the reap runs last, after cache invalidation —
  but it still blocks the event loop for that window. Move to a thread or background task.
- Live Phoenix 20.8 was never exercised: whether `sessions.get` resolves a user session id
  uniquely across projects, and `bulk_delete` behavior with GlobalIDs, are unverified. The code
  refuses a project mismatch, so a collision is a MISS, never a wrong deletion.
- The sweep runs one tenant at a time (no all-tenant mode); ~12 lines of owner-connection code
  duplicated from `run_phoenix_evals`; traces over 1000 spans need a second (idempotent) pass.
- P3 residual gaps: a delete landing between the pre-publish check and the Phoenix publish still
  leaves an annotation (the P4 sweep covers it); the plan-mode cost report counts deleted chats'
  judges.
- P1 unmatched by design: unlabelled `98765 43210` / `555-123-4567` / "call me on …" (no `+`, no
  label — part/work-order ambiguity); a `+37.774929` coordinate is over-redacted; soft hyphens
  INSIDE label words are partially handled — the review corrected the implementer's note:
  "Tele­phone" IS caught (via the `phone` substring); the real misses are "Mo­bile",
  "What­sApp", "Con­tact" and "Ph­one".
- P2 cosmetic: a kept string can end with a partial marker (`***REDAC…[truncated]`).
- P5's `error_code` is an open vocabulary on crashes (exception class name fallback — matches
  span `error.type` behavior).
- The `tests/api` xdist-order flakes (business-rule entitlement 200-vs-403; "No module named
  'auth'" in tenancy tests) flake on BASE too — a further isolation bug in Lane I's family,
  beyond I1–I3's scope.

*From the lane P review (P2/P3, recorded not blocking; evidence under
`~/.claude/scratch/privacy-hygiene-batch/P/review/`):*
- **F3 (P2):** `_TRUNCATED_LONG_SECRET_RE` scans the whole kept text with quadratic worst case
  (3.75 s on one 32k `eyJ-` string; base already took 4.7 s — 1.35–1.8× worse on an existing
  weakness; the 4× DoS metric is unaffected). Anchor the scan at the last `eyJ` /
  `-----BEGIN`.
- **F4 (P2) over-redaction:** tolerance pairs (`+0.005 -0.002`), dates after MOB/Tel labels,
  `contact 21-51-00-800-801` (ATA refs), `(737) 800-2000` and `P/N (123) 456-7890` are
  redacted; the benign corpus dodges the tolerance form by writing `/`.
- **F6 (P3):** the static log guard does not catch `error_code=<result>.error`; both endpoints
  are behaviorally pinned instead.
- **P3 (P3):** a failing liveness check at selection aborts the whole eval run rather than
  failing per item — fails closed, nothing written.

*From the lane T implementer (`~/.claude/scratch/privacy-hygiene-batch/T/NOTES.md`):*
- The 8 otel-tests excluded from CI never run there. Full fix: a protected-environment path that
  can install `utils` (OIDC → CodeArtifact) plus loguru and claude-agent-sdk, or a guard
  asserting the exclusion list equals the set of tests that need the workspace env. The lane was
  red for 3 pushes before anyone noticed — a lane-health alert would have caught it.
- The `chat-eval.yml` Weaviate fallback is the one pinned ref no test reads (the plan scoped the
  test extension to the standalone file). Also from R4: dead named-volume declarations, and the
  demo service's ExecStop points at the POC compose file.
- After P5, T5's `error_type` becomes redundant beside `error_code`; the root fix is to stop
  writing `str(exc)` into `PipelineResult.error` at the two adapter seats (Lane P territory).
- The iac `guards.yaml` cap is not self-enforcing: nothing asserts every caller declares
  top-level `permissions`. Estate-wide, no test requires a new workflow to declare
  `permissions:` at all — a new file silently falls back to the repository default.
- The api checkout-pin helper prefers the same-NAME sibling over the same-BRANCH sibling, which
  misfires under multi-lane worktrees (the two environmental api unit failures).

*From the lane T review (P2/P3, recorded not blocking; evidence under
`~/.claude/scratch/privacy-hygiene-batch/T/review/`):*
- The chat-eval `WEAVIATE_IMAGE` fallback is unread by any test: reverting it to `latest`
  survived the full local otel lane (the plan scoped the test extension to the standalone file).
- T4 deploy note additions: the dev Weaviate container WILL be recreated on the next
  `compose up` (the image string changed; the digest is identical and the bind mount persists);
  and demo/POC boxes may have pulled a newer `:latest`, making 1.34.8 a downgrade Weaviate can
  refuse — read `/v1/meta` per box before recreating.
- The T5 guard's log sink listens at DEBUG, so a TRACE-level or stdlib-`logging` leak at that
  site would pass unseen.
- A deselected T1 test that later stops needing the workspace env stays silently deselected
  (every other drift direction fails loudly in CI).
- The data-plane pin test would read a stricter digest pin (`1.34.8@sha256:…`) as drift.

*From the lane D implementer (`~/.claude/scratch/privacy-hygiene-batch/D/NOTES.md`):*
- 29 of the 48 moved files fail Prettier — identically at base; no CI Prettier gate, so not reformatted.
- The depth guard cannot see paths Playwright resolves against the CONFIG file's directory
  (the `outputDir` kind); the one live site was fixed by hand.
- The depth guard tracks variables per name across the whole file, not per scope (can over-report,
  like the Python original).
- `tests/fixtures/` holds 14 flat support files outside the layout rule (not test files).
- Nested tests' remaining `../../../X` relative imports fail loudly but could move to `@/`.
- `lib/api/invitations-api.ts:36` names a test file that does not exist (research side-finding).

## Lessons

_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule next time)_

## Implementation notes

_(per lane, filled as work lands)_

### Lane S — built + reviewed MERGE-READY (0 P0/P1), 2026-09-24

Branch `hyg-sink`: utils `105edf5`/`27b19c8`/`e2591d0`/`87d46d1`/`3f78805`, flynapse-otel
`3d2605a`/`9b0ff9f`, lambdas `4e0a58d`/`606c1b0`. Full lanes green modulo 5 pre-existing
workspace-caused utils failures (cross-repo checkout census; also fail at base). Recipe
correction: utils tests need `POSTGRES_DB=copilot_mro_test` or the conftest db_guard refuses.
Notable deviations, all reviewed sound: S1 paid dynamodb+migrate down whole (old guard could only
excuse whole modules); S2 additionally removed the Cognito EVENT DUMP (email/phone/username/code
logged every invocation) in the separable commit `606c1b0` — reviewer verdict TAKE; S4 fixed the
RECORD factory instead of per-script edits (covers all 10 copilot-mro basicConfig scripts through
their utils import); S5 landed register+policy one commit before guard adoption to satisfy the
ratchet's no-deletion rule. The adversarial reviewer re-ran resolve proofs, full lanes,
red-befores, 14 mutants, planted 13 leak shapes (all caught), proved the ratchet fails closed
under squash/rebase, and confirmed the S2 `diagnose=True` equivalence from loguru 0.7.3 source.
Merge constraint: true merge only (see Review & merge protocol). Findings triage: P2/P3 →
Future Improvements above; nothing blocking. **MERGED 2026-09-24 (local, not pushed): utils
`28b87d8` (--no-ff), flynapse-otel `c8b6d92`, lambdas `c30549a` — each mainline tip sat exactly
at the lane base; the register/ratchet guard runs 7/7 green on the merged utils mainline.**

### Lane I — built + reviewed MERGE-READY (0 P0/P1), 2026-09-24; merges after lane P

Branch `hyg-isolation`: `7ac98ec4` (I1 + the measured work_orders twin, 13 collection errors → 0),
`29e9f416` (I2 — real-`__path__` stand-in + scoped restore; deliberately NOT ensure_package, which
reuses an already-imported real package and leaks with no undo), `6cb02b5c` (I3 — held-clock
seam; the deadline window is spent only while the call is in flight; `held_reads` pins the seam;
20/20 `-n 4` reruns; tolerates 150/1500 ms injected pre-start delay). All test-side. Full
tests/unit `-n 4`: 7310 passed / 11 skipped. 12 pre-existing data_discovery db errors recorded
under Future Improvements. The adversarial reviewer re-measured every claim (reversed run orders,
its own leak probes, a marker-file proof that I2's real-`__path__` stand-in cannot import the
cluster-writing modules, 12 further `-n 4` reruns under load, exact red-before reproduction via
mutants) and judged both deviations sound; its F-1/N-1/N-2/N-3 findings are recorded under
Future Improvements.

### Lane D — built + reviewed MERGE-READY (0 P0/P1) + MERGED, 2026-09-24

Branch `hyg-g54`: `b1027c9` (48 pure renames, R100), `d4f5171` (83 specifiers → `@/`; six path
comments), `f5123a6` (depth fixes — **9 sites in 7 files, not the researched 5**, incl.
Playwright `outputDir`; `tests/fixtures/repo-root.ts` re-anchored to `__dirname` for Playwright
CJS compatibility), `6826483` (layout + AST depth guards; planted violations go red). Test
name-set identical to base; typecheck/lint clean; `next build` never run. The one failing test
needs a sibling `core-hyg` checkout by name (no fallback, fails at base too) — the controller
created `core-hyg` (core @ `c8c4fb3`) so the lane can run fully green; reviewer verified
2692/2692 pass exit 0 once both sibling worktrees existed. The adversarial reviewer confirmed
rename purity (48×R100, nothing else), 3 comment-only production lines, both guards failing on
archives of the OLD trees naming exactly the 48 flat files and the 9 depth sites, and its own
plants (including patterns the implementer didn't try) all caught; all three deviations judged
sound. **MERGED 2026-09-24 (local, not pushed): dashboard mainline `agent_sdk` @ `fbb4fc0`
(--no-ff; the tip sat exactly at the lane base, so the merged tree is byte-identical to the
reviewed HEAD).**

### Lane P — reviewed 2026-09-24: NOT MERGE-READY (1 P0 + 1 P1) → fix round P-R1 running

Branch `hyg-privacy`: `00a48807` (P1 — labels/fillers/connectors widened incl. soft hyphen and
unicode dashes, international `+` and parenthesised-area unlabelled shapes, digit class stopped
crossing newlines, redaction version → v2 in the same commit), `9fd65ec0` (P2 — redact the kept
text + a 512-char lookahead window, then cut back so a rule-untouched window tail is dropped;
budget charged on kept text only; tail backstop for secrets longer than the lookahead; the DoS
pin untouched and green), `716d88cc` (P3 — liveness gate at selection AND pre-publish, missing
chats row = LIVE, FOR SHARE races tested, harness/golden/`__SYSTEM__` rows proven landing),
`85fad314`/`28ef538a`/`03f5c662` (P4 — refusal-first scrub target, GlobalID-only deletion,
post-commit best-effort inline reap that can never fail the delete, per-tenant idempotent sweep;
one real bug found and fixed in review-by-self: the sweep no longer touches spans of a chat whose
session lookup failed), `a26c9ee1` (P5 — `error_code` from the declared vocabulary only,
class-name fallback, door logs carry the code and never the text, contract doc updated),
`60326067` (P6 — the 12 not_evaluated reason strings survive the scrub, list pinned by AST to
what the runners actually spell). 59 mutation runs: 57 killed outright, 2 first-time survivors
fixed by tightening tests then killed. Wide lane 12724 passed with 10 failures all verified
pre-existing or base-flaky; DB lane green but for the known data_discovery drift. Controller
ruling on the implementer's commit-policy question: production edits committed on the dedicated
lane branch by named pathspec are this batch's sanctioned design (the new-files+test-edits-only
rule governs primary trees outside SDD batches).

**Review (NOT merge-ready: one P0, one P1; fix round P-R1 running).** The reviewer confirmed
four of the five P0 constraints held — missing-row=live (with a cross-tenant same-id probe:
invisible under RLS, which is the safe direction), golden untouchable (case/spacing variants,
GlobalID-only, failed-lookup skip), the DoS bound (≤2×L+512 by construction, 2.00×L measured),
and proof reproducibility (49 of 59 mutants re-run, all killed; red-befores exact). P2's own
goal is proven closed: a sweep of every cut offset across 7 secret types gives 0 leaks on the
tip vs 88 on base. **The P0 (F1):** v2's label-to-number gap is ≤3 characters with no newline
where v1 accepted `\s*` — so `Phone:` followed by a newline, CRLF, or a run of spaces/tabs
leaks the number v1 redacted (840 of 960 differential shapes; proven end-to-end into the
persisted row and the Phoenix projection; exactly the layout PDF/form extraction produces; no
test pinned the shape either way). **The P1 (F2):** the inline reap's claimed 5 s/call bound is
false — the client's server-version check and `projects.get` ride the default 10 s/30 s
timeouts, a hanging endpoint held the reap 33.5 s synchronously inside the async delete
endpoint, and the reap runs before cache invalidation, so a stall keeps serving stale copies.
Fix round P-R1 (landed 2026-09-24: `ae99040e` F1, `31c75949` F2, `b410e13f` bearer-header pin):
the label-to-number gap is now `\s{0,16}` (v1's class, bounded; intra-number rules untouched;
version stays v2, which never shipped) — the reviewer's differential goes 840 → 0/960 and the
vendor-sheet numbers no longer reach the row or projection, with a v1-parity test block pinning
every gap class; every Phoenix client call now rides a 5 s httpx timeout (version check and
project lookup included — the Client ignores `api_key` once an `http_client` is passed, so the
bearer header became our code and is pinned), the reap runs last after cache invalidation, and
a silent-socket test pins the bound (measured 31.4 s → ~5-6 s). 32 mutants killed including
full re-runs of the original P1 and P4 sets; wide lane at the tip 12753 passed with only the
known date-relative pair failing. One deliberate widening beyond v1, pinned: a label alone on
its own line now redacts the following number. Scoped re-verify by the resumed reviewer is
running (F1/F2 + the three deviations only).

### Lane T — reviewed (no P0, one P1), fix round R1 closed, non-gated repos MERGED 2026-09-24

Nine `hyg-tiny` worktrees off the pushed bases. T1: the red otel-tests lane reproduced under the
workflow's own conditions (fresh pytest+pyyaml venv, no siblings, no .env); the true need was
**eight** workspace-env tests, five hidden behind the three collection errors — fixed
workflow-side with ignore/deselect lists and an explanatory header rather than installing the
private `utils` package; the workflow's own steps now run green locally (353 passed at tip). T3
deleted the token steps separately. T2 census found **18 workflows in 9 repos** (the plan's 16
plus lambdas + llm-platform), none declaring `permissions:` before; 17 got the top-level block,
`guards.yaml` deliberately none (workflow_call-only, capped by its two callers); iac suite green,
block-in-guards mutant killed. T4 pinned the five Weaviate refs plus the standalone stack's UI
image, emptied `PIN_EXEMPT`, added `DATA_PLANE_PINS` + a test, and re-verified the 1.34.8 digest
live; deploy note extended: recreating a demo/POC box that ever pulled `:latest` ≥1.35 would be a
DOWNGRADE Weaviate may refuse — read `/v1/meta` per box first. T5 landed the constant +
`error_type` at `executor.py:1416` with its guard in the existing executor fake-harness file;
**`error_code` is a marked seam, not wired** (P5's shape hadn't landed) — post-P5 fix round owed:
one kwarg + test; T5 merges only after P5. api runs under multi-lane worktrees need
`PYTHONPATH=api-hyg:core-hyg-t:utils-hyg-t:copilot-mro-hyg-t:flynapse-otel-hyg-t` (the checkout
pin enforces it).

**Review (no P0, one P1).** The reviewer rebuilt the CI replay harness from scratch (the
implementer's clone carried a hand-edited workflow), matched CI's own failing log, proved the
exclusion list neither over- nor under-excludes, and confirmed the acceptance still holds on a
scratch P→I→T merge. The decisive T2 audit: **all 18 workflows use the GITHUB_TOKEN for checkout
read only** — no pushes, releases, comments, package publishes or OIDC anywhere — so
`contents: read` breaks nothing (per-file table in the review record). The one P1: the iac
caller-cap that `guards.yaml`'s blockless design depends on was unpinned — mutants dropping or
widening the callers' permissions blocks survived the full iac lane. Fix round R1 (fresh
implementer) added the caller-cap assertion to the existing guard-lane test (iac `9fe70c4`,
9 lines; both reviewer mutants re-killed, aimed AND against the full 316-test lane, then
re-verified by the controller's own mutant.sh runs) and wired T5's `error_code` (api `d814f6b`:
`getattr(result, "error_code", None)`; the test plants a code post-construction so the guard
passes both with and without P5's field; kwarg-dropped and raw-text mutants killed). T1/T3/T4
merge-ready as reviewed; review P2/P3s recorded below. **MERGED 2026-09-24 (local, not pushed)
into the seven non-gated repos: iac `fb2d2f4` · utils `4b67458` · core `21cd644` · dashboard
`0918191` · flynapse-otel `438d768` · lambdas `693a855` · llm-platform `ab3bcbb` — workflow-only
files, zero conflicts with the S/D merges already on those mainlines. copilot-mro `hyg-tiny`
merges after P → I; api `hyg-tiny` merges after P5.**
