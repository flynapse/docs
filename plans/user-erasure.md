# User Erasure (PP-MRO-1) — Implementation Plan

> **For agentic workers:** SDD-driven. Controller = the owner's session; **implementers AND reviewers = Opus**
> (fresh agent per task, one implementer per working tree; concurrency cap 4, the owner's since 2026-10-01).
> Ledger: `/home/aditya/Code/.superpowers/sdd/user-erasure/progress.md`. Durable scratch:
> `~/.claude/scratch/user-erasure/<lane>/`. **Push rule (in force since P3; the owner: Claude may push this program's
> work):** each lane's merge is pushed once its own post-merge gate passes, before its phase review; a phase review's
> findings land as a fix round, merged, gated and pushed the same way. Never rebase, squash, amend or force-push.
> Executors do not edit this plan; they report exact text.

**Goal:** a real erasure of one person from one tenant: freeze at once, erase after a 7-day cancellable window
(immediately for a legal right-to-be-forgotten request), with the person's own trail deleted, tenant knowledge
kept but de-attributed, the Cognito identity removed, and a receipt that states what remains and for how long.

**Evidence base (spot-checked 2026-09-25; trust over plan prose):** `~/.claude/scratch/user-erasure/research/R1-user-erasure.md`
(inventory §1, chat-delete reuse §2, decisions §3). Precedents: `copilot-mro/docs/plans/eval-explanation-scrub-on-chat-delete.md`
(the brief's workspace path does not exist), `deleted_chat_copies.py`, core `tenant_lifecycle.py`, `TenantService.delete_tenant`
(records itself in `authorization_events`), B14 research `~/.claude/scratch/b14-tenant-delete/research/R1-b14.md`.
Trees: core `17699d9` master · copilot-mro `e0cdea42` / api `f616c3b` / utils `4b67458` langgraph-merge · shift-optimizer
`f86c6c5` / telegram-bot `bff16ea` main · iac `fb2d2f4` obs-merge · dashboard `0918191` agent_sdk (confirm at lane start).

**Owner rulings (2026-09-25):** **D1** same line as chat delete — own settings, personal memory and feedback trail
GO; contributed tenant knowledge (corrections, example queries, findings) STAYS verbatim, DE-ATTRIBUTED. **D2** scrub
each chat's copies (chat delete's scrub, factored for already-deleted chats), then HARD-purge chat + block rows.
**D3** ledgers/analytics keep rows, user id → `deleted-user`. **D4** `llm_turn_content` targeted delete now via a
`postgres`-owned definer function. **D5** trigger = a tenant user holding `users_modify` or a platform operator; freeze
at once, erase after 7 days (immediately for a legal RTBF request); audit = one `authorization_events` row at completion (plus one per escalation of an open
request, Task 20 F3; both seen in a person's history only by `users_modify`) + a small
`user_erasures` ledger with NO name/email. **D6** Cognito disabled at freeze, deleted at completion. **D8** Phoenix
actively deleted (per-chat sessions + a `user.id` span sweep per tenant project); Loki/Tempo/CloudWatch by retention
(bound in the receipt); `iac/s3.tf` gains a 30-day NoncurrentVersionExpiration rule (applied at the first iac apply —
AWS deploy deferred). **D9** airworthiness `reviewed_by` and `authorization_events` actor/subject KEPT verbatim; legal
opinion owed (not a blocker). **Controller (research recs, owner may overrule):** **D7** private/chat-scoped DocHub docs
incl. raw backups, chat attachments, `dataviews/{t}/{chat}` and parse sidecars (via aliases) deleted; shared docs
kept, de-attributed. **D10** the user's automations deleted (runs kept, D3); comments kept with author anonymised (id
→ `deleted-user`, name "Deleted user", email NULL); thumbs, notifications, subscriptions, pending invitations deleted;
SAD sources kept, de-attributed. **D11** `/goodbye`'s channel teardown runs the same erase + Cognito delete. **D12**
state the backup bound; replay completed erasures from the ledger after any restore. **Amended by the owner
(2026-09-28, decision 31): no replay is built — no backups are configured, and a restore is disaster recovery only;
the receipt states the backup bound.**

## Global constraints

- Worktrees at sibling depth `/home/aditya/Code/<repo>-erase[-b]`, one implementer per worktree, private scratch per
  lane, `.env` symlinked, `PYTHONPATH` pinned to the worktree first. **Sibling-checkout hazard:** a test importing
  another repo pins `PYTHONPATH`/`SIBLING_CHECKOUTS` to the lane worktrees (api `tests/_checkout_pin.py`) and proves it
  by `rootdir` + `module.__file__` in the report.
- Every run via `/home/aditya/Code/pytest-slot.sh -- …` from the shared `/home/aditya/Code/api` env, `DEBUG=false`;
  `-n 4` for big non-DB lanes, `-n 0` for DB lanes. Red-before for every new behaviour test; `mutant.sh` for every
  guard and named mutant (full lane re-run before calling one SURVIVED).
- Two-level test layout, unique basenames, `tests/_root.py` helpers; copilot-mro unit tests use the dynamic loader
  (`tests/_package_stubs.py`), <2 s per file. DB tests only on `copilot_mro_test` / `shift_optimizer_test`.
- Commit early by named pathspec, never `git add -A`. Each touched repo's exception-text register still equals its scan.
- No personal data in any log, span, ledger or receipt: request id, step names and counts only.
- Every erase statement is keyed on the not-yet-erased shape (the chat-delete convention): a rerun changes 0 rows.

## Controller rulings

- **R-IDS:** carry both `user_id` and `external_id` from the `users` row to every seam (core now mints one value for
  both, `user_service.py:504-507`; the api `auth.py:76-79` "divergence" docstring is stale; both is still free).
- **R-LLM-DEFINER:** ONE postgres-owned definer serves D4 AND D3: deletes `llm_turn_content` rows and rewrites
  `user_id` on `llm_usage` / `llm_model_calls` — both append-only for the app AND grant roles (`provision_rls.py:250-255,
  849-856`), so a plain UPDATE is refused. EXECUTE to `flynapse_grant` only (`db_query` runs LLM SQL as the app role
  with no gate on select-list function calls, `provision_rls.py:205-212`). **B14 collision:** both build definer
  provisioning in `provision_rls.py`; whichever lands first builds it, the other reuses — never concurrently.
- **R-WINDOW:** the window lives in the ledger (`erase_after`): `requested_at` + 7 days for a windowed request, +
  `IMMEDIATE_ERASURE_DELAY` (30 minutes, owner question 5) for an immediate one. How a one-shot waits for it is
  ruled in Task 11's owner-rulings box ("Immediate requests wait out open turns"); the daily due sweep is Task 12's.
  The scheduler defaults OFF (api `automations/settings.py:42-43`), so the owner-run CLI in the api environment (it
  needs the seam wiring; core imports no service) covers scheduler-off with `--run-due` (amended 2026-09-27, P1
  review COMP I-2; 2026-09-29, P3 pre-flight C-3, C-26, and P3 plan review MI-14).
- **R-FREEZE:** `users.status = erasure_pending` (prior value in the ledger), refused explicitly by the gateway and the
  automations identity check (status is otherwise deliberately unconsulted, `auth.py:587`); memberships untouched.
- **R-DOOR:** no platform-operator HTTP identity exists, so the platform door is ONE owner-run CLI in the api
  environment, `python -m flynapse_api.user_erasure_cli`; its commands are Task 12's ("The owner CLI"). Core has no
  CLI: every request path refuses (fixed 503) in a process whose seams are not registered, so nobody is
  frozen where no erasure can finish (P1 review CORR I-1), and only the api registers seams (amended 2026-09-27, P1
  review COMP I-2; 2026-09-29, P3 pre-flight C-1). `DELETE /users/{id}` (no caller in the tree) becomes an erasure
  request under its `users_modify` gate.
- **R-DOCHUB-REKEY:** shared docs de-attribute copy-then-delete — read paths re-derive object keys from
  `owner_user_id` (`document_hub/keys.py:1-15`), so a row rewrite alone breaks the document.
- **R-PLACEMENTS (research gaps):** `comments.mentions` → remove the id; other recipients' notification payloads
  naming the user → de-attribute; invitations addressed to the user → delete, `invited_by`/`accepted_by` elsewhere →
  `deleted-user`; RBAC provenance (`departments`/`roles.created_by`, `user_departments.joined_by`,
  `user_operators.granted_by` — non-updatable by design, `user_roles.assigned_by`) → KEEP under D9;
  `ad_compliance.complied_by` → keep (customer record); `improvement_findings.reviewer` → `deleted-user`.
- **R-GUARDS:** each repo's line + drift guard covers its own registry (copilot-mro incl. Weaviate properties);
  telegram-bot's `_ACCOUNT_SWEEP` guard stands. Cross-repo pins only in Task 17.
- **R-ORDER (copilot-mro):** chat and attachment ids gathered first → user-grain rows (definer keyed by user AND chat
  ids) → per chat: reap row-derived objects, scrub in its own txn, post-commit reaps → DocHub → residue with the same
  ids → purge chats + blocks → user prefixes (R-LINKS-LAST, P2). One pass: a non-zero residue raises an incomplete and
  never purges (FI-S1; Task 11 owns the drain and the retry).
- **R-VERIFY:** each seam registers `erase` + `residue` (read-only counts of the ids in every non-keep placement,
  re-derived from the stores); completion needs all-zero residue (else the step fails and Task 11 retries it), which
  closes the race for in-flight RUNS (Task 11 drains them first).
  - It does not close it for an interactive stream open at the freeze: no durable marker exists, and a chat-keyed copy
    the stream lands after the seam's last residue read is invisible once the chat ids are purged (Task 8 review,
    Concern 1).
  - A chat-file upload's durable S3 object is written by a detached background task that retries up to 4 times, so it
    too can land after the sweep, and a turn deadline alone does not bound it (P2 correctness, Q5 evidence).
  - Owner question 5's answer: an immediate erasure waits 30 minutes after the freeze (Task 11), and every interactive
    turn and chat-file upload is bounded under that wait (Task 11b).

## Phases

| Phase | Tasks | Lanes (worktree → mainline) | Ships |
|---|---|---|---|
| P1 foundations | 1–5 | C `core-erase`→master (1→2) · A `api-erase`→langgraph-merge (3, after 1) · M1 `copilot-mro-erase` (4) · M2 `copilot-mro-erase-b` (5) | ledger, registry, freeze/cancel, refactor, definer — nothing erases yet |
| P2 seams | 6–10 | M1 (6, then 8) · M2 (7) · C (9) · S `shift-optimizer-erase`→main (10) | every store's erase + residue + line + drift guard |
| P3 orchestration | 11, 11b, 12–14, 19 | C (11 → 13) · C-b `core-erase-b` (19 core) · M1 (19 copilot-mro → 11b) · A (12 → 19's registration) · D `dashboard-erase` (14 + 19's copy) · T `telegram-bot-erase`→main (the bot's teardown client, `/goodbye` flow and provisioning answer, Task 13) — order below | the flow end to end, Cognito delete, receipt, D11 on the job path, UI; operator delete deletes its own rows |
| P4 telemetry/iac | 15–16 | M1 (15) · I `iac-erase`→main (16) | Phoenix user sweep, S3 lifecycle, Cognito IAM |
| P5 proof | 17–18 | P (17's pins) · D (17's drift list) · C (17's census, after D) · controller + owner (18) | census, cross-repo pins, live E2E |

**P3 dispatch and merge order (P3 plan review, recommended order and MI-6).** One implementer per worktree, at most
three running at once; each lane is serial inside itself.
- Wave 1 (2 running): C-b = Task 19's core half ‖ C = Task 11. The two share no file, provided the self-bound core
  step stays in `operator_copies.py` and neither lane adds a session-wide fixture to a shared conftest. C-b merges
  first.
- Wave 2: once C-b merges, M1 = Task 19's copilot-mro half (the seam, Document Hub's operator check and the orphan
  script). As soon as it merges, the owner runs the orphan script on dev `copilot_mro`: the dry run, then `--execute
  --expect-rows N` (Deploy/rollout step 2).
- Wave 3, after Task 11 merges: A = Task 12 ‖ D = Task 14 + Task 19's dashboard copy ‖ M1 continues (Task 19's
  copilot-mro half, then Task 11b against the merged core).
- Wave 4, after Task 12 merges: C = Task 13 ‖ T = the bot's side of Task 13, built from the 202 and 409 contracts
  Task 13 states ‖ A = Task 19's api registration. If M1 (11b) or D is still running, it takes the third slot before
  A's registration.
- Ordering rules the waves rest on:
  - Task 11b may start once Task 11 has committed `IMMEDIATE_ERASURE_DELAY`, its tests pinning `PYTHONPATH` to
    `core-erase`; it merges only after Task 11 merges (its pin imports core's constant, so copilot-mro's mainline
    would go red otherwise).
  - Task 12 merges only after Task 19's copilot-mro half has merged and the owner has run the orphan script on dev:
    the erasure doors serve on dev once Task 12 registers the seams (Deploy/rollout step 2).
  - Task 13 waits for Tasks 11 and 12, and merges after lane T.
  - Task 14 waits for Task 11 and Task 19's core half (it reads `GET /users/erasures`, generates its contract from
    core's receipt declaration and renders `cleanup_warning`).
  - Task 19's api registration waits for Task 12 and Task 19's copilot-mro half (it imports `operator_teardown`).
- Merge order: 19 core → 11 → 19 copilot-mro (then the dev orphan script) → 12 → 11b → 14 (with 19's dashboard
  copy) → 19 api registration → telegram-bot (T) → 13.

- [ ] Each phase: all tasks reviewed and merged → phase-level adversarial review (P2: three Opus lenses —
  correctness, plan-completeness, simplicity; P3: five Opus reviewers, one per area plus the whole phase) → triage →
  owner review pause before the next phase.
- [x] `copilot_mro_test` migrated + provisioned from the erasure branches (owner decision 27, 2026-09-27),
  re-provisioned for `NO_DELETE_RELATIONS`.

## Tasks

### Task 1: core — erasure ledger, seam registry, vocabulary (P1, lane C)
Owned: `core/core/db/table_definitions.py` (`user_erasures` + registry entry); new `core/core/resources/user_erasure/`
(`__init__`, `ledger.py`, `lifecycle.py`); `core/core/db/authorization_events.py` (`ENTITY_KINDS` + `user`); tests.
- [x] `user_erasures`: tenant-classed, NO FK to `tenants`/`users` (outlives both, like `authorization_events`); request
  id, tenant, surrogate id, sub, requested_by (opaque), via, mode, RTBF flag, state (requested → frozen → erasing →
  completed | cancelled | failed), prior user status, `erase_after`, per-step state/counts/orphans + receipt (numbers
  and step names only), timestamps. No name, email or free text. One open request per (tenant, user), partial index.
  Also `prior_cognito_enabled` (T2-M1); DELETE revoked from the app and grant roles (`NO_DELETE_RELATIONS`, T5 fix
  round 2).
- [x] Ledger store with guarded transitions (terminal rows never move), the `erasure_pending` literal and the 7-day
  constant; `lifecycle.py`, the twin of `tenant_lifecycle.py`: named seams register `erase` + `residue`, a declared
  required set, unregistered or partial → a RuntimeError subclass (never ValueError), reset for tests.
- [x] Proofs: unit — registry fail-closed, transitions exhaustive, `record_event` takes `user` and still refuses
  near-misses; db — RLS isolates tenants, the row survives its tenant's and user's deletion, a second open request is
  refused. Mutants: drop the index predicate; allow completed → erasing; registry skips instead of raising.

### Task 2: core — request, freeze, cancel, Cognito (P1, lane C, after Task 1)
Owned: new `user_erasure/{freeze,cognito_accounts,erasure_endpoints}.py`; `core/core/resources/user/user_endpoints.py`;
core's router mount site; tests (incl. edits to `tests/api/tenancy/test_user_update_ownership.py`).
- [x] Request = ledger row + freeze: refuse the tenant's last active owner; status → `erasure_pending`; Cognito
  AdminDisableUser + AdminUserGlobalSignOut; auth-context cache invalidation (as `delete_user` declares it). A Cognito
  failure refuses the request with no ledger row (fail closed, as `cognito_identities.py`). Cancel within the window
  (same gate): prior status restored, AdminEnableUser, ledger cancelled.
- [x] Routes POST / GET (status + receipt) / DELETE (cancel) on `/users/{id}/erasure`, gated exactly as
  `_require_user_delete_allowed`; bare `DELETE /users/{id}` answers 202 as a request. `cognito_accounts.py`: disable,
  enable, sign-out, delete, exists — configured pool only, no attribute reads. (Task 11 later added one: the
  completion reads the account's tenant claim, `account_tenant_claim`; P4 review C M-9.)
- [x] Proofs (fake Cognito): 403 without `users_modify` (self included), last-owner refusal, Cognito failure leaves
  status and ledger untouched, cancel restores exactly, a repeat request returns the open one. Mutants: skip the
  last-owner check; freeze without sign-out; cancel without restoring status.

### Task 3: api — a frozen user reaches nothing (P1, lane A, after Task 1 merges)
Owned: `api/flynapse_api/middleware/auth.py`, `api/flynapse_api/automations/identity.py`; api unit tests.
- [x] Gateway identity resolution refuses exactly `erasure_pending` (403, fixed text naming no one); `pending` and
  every other value behave as today; correct the stale divergence sentence at `auth.py:76-79`. The automations
  identity check stands a frozen user's definitions down at next fire with a reason token.
- [x] Proofs: red-before for both; `pending` signup activation still passes. Mutants: refuse every non-active status
  (the pending test must go red); drop the automations check.

### Task 4: copilot-mro — `scrub_chat_copies`, behaviour-preserving (P1, lane M1)
Owned: `copilot_mro/app/db/chat_history/chats.py`, `postgres_table_definitions_modules/chat_turn_facts.py` (the two
ANONYMISE statements, ruling T4-C2); `tests/{unit,db}/chat_history/`. `deleted_chat_copies.py` unchanged.
- [x] Factor `delete_chat`'s transaction body into `scrub_chat_copies(cur, *, tenant_id, chat_id, user_id, department,
  now)` (the caller bound to the chat's tenant, else `ScrubTenancyMismatch`): roster rebind; the chat-row soft-delete
  stays the FIRST write (race-gate lock order, `chats.py:22-33`), keyed on tenant + chat + the chat row's owner and
  department (`IS NOT DISTINCT FROM`) at any deleted state, never overwriting an existing `deleted_at`; blocks; facts + feedback; `anonymise_copies` —
  returning counts and reap keys. Plus `reap_chat_copies` (spills, compaction docs, generation + caches, Phoenix
  session). `delete_chat` keeps its ownership read, return values and log fields, and calls both.
- [x] Proofs: every existing chat_history unit + db test passes UNMODIFIED (list them); new db cases — a chat
  soft-deleted with unscrubbed copies is fully scrubbed while `delete_chat` still returns False for it; counts [n, 0]
  on rerun; `deleted_at` preserved. Mutants: soft-delete moved after the anonymisation (add a race test if none goes
  red); the `deleted = false` guard reinstated on the scrub path.

### Task 5: copilot-mro — the postgres-owned definer for the append-only LLM records (P1, lane M2)
Owned: the DDL constant beside `postgres_table_definitions_modules/llm_turn_content.py`; `scripts/provision_rls.py`;
`tests/unit/db/`, `tests/db/tenancy/`.
- [x] One SECURITY DEFINER function (R-LLM-DEFINER) taking tenant, user ids, chat ids, returning three counts; static
  schema-qualified statements, pinned search_path with `pg_temp` last, STRICT; refuses a blank tenant, empty ids and
  `deleted-user` as an input id. Phase 2b applies it with REVOKE ALL FROM PUBLIC + GRANT EXECUTE to `flynapse_grant`
  in one transaction; `--verify-only` reports it missing, not `prosecdef`, unpinned, owner ≠ `postgres`, or any other
  EXECUTE holder; the append-only verification of the three relations is unchanged.
- [x] Proofs: unit on the DDL text and verify findings (fake catalog rows); db probe after the owner provisions — app
  and readonly EXECUTE → 42501; grant EXECUTE touches only the named tenant (a second tenant under the same user id
  untouched); app-role UPDATE/DELETE on the three still 42501. Mutants: drop REVOKE FROM PUBLIC; drop the tenant
  predicate; grant EXECUTE to the app role.

### Task 6: copilot-mro — user-grain rows, the erased-user line and its drift guard (P2, lane M1)
Owned: new `copilot_mro/app/db/chat_history/erased_user_copies.py`; `copilot_mro/app/services/memory/memory_index.py`
(the index naming read and the stored-vector re-upsert, pre-review ruling on concern 1); `tests/unit/chat_history/`,
`tests/unit/memory/`, `tests/db/user_erasure/`; the scope-guard approval.
- [x] `ERASED_USER_COPIES` places every user-keyed registry column and Weaviate property delete / scrub /
  de-attribute / keep with a reason (research §1a + R-PLACEMENTS), plus a residue query per placement. Document Hub
  and chat columns are placed `delegated` to Tasks 7 and 8, which count them (R-DELEGATE); every key is
  `<table>__<column>` (R-LEDGER-KEYS).
- [x] One txn under the tenant's full roster: delete `user_preference`, `scope='user'` memory and every compaction
  digest of the person's chats, by chat (T6 review I-1); tenant-scope notes and facts keep payload, ids →
  `deleted-user`/NULL (D1); events by `actor_user_id` scrubbed; findings' evidence texts of the user's signals removed
  BEFORE the signals scrub; signals, facts and feedback by user id (not only per chat); data-discovery ids and findings
  `reviewer` → `deleted-user`; a colleague's share addressed TO the person loses `share_data.email` (T6 review I-4);
  every transaction held to the pool's own statement ceiling; then `ERASE_USER_LLM_RECORDS_SQL` on the grant pool
  inside `db_tenancy(<erased tenant>, …)` (an unbound or other-tenant session is refused with 22023; a NULL argument
  returns no row, which is a refusal and never zero). The residue is read bound to the tenant's FULL roster (P1
  review CORR M-4).
  Post-commit: the memory index is brought into line from its own naming read — documents removed, or re-upserted
  with the stored vector (orphans counted). An exception after a commit carries `partial` (R-PARTIAL-COUNTS).
- [x] Drift guard (unit, registry-derived): an unplaced column matching user_id, `*_user_id`, `*_by`, `actor*`,
  `author*`, `reviewer*`, `owner_user_id`, `*email`, `mentions`, `recipient*` (or such a Weaviate property) fails; a
  placement naming a vanished column fails.
- [x] Proofs: db — sentinel user + sibling + a second tenant under the SAME user id; knowledge text kept verbatim with
  no id; rerun 0 rows. Mutants: drop the roster rebind; signals before findings; keep `user_preference`.

### Task 7: copilot-mro — Document Hub at user grain (P2, lane M2)
Owned: new `copilot_mro/app/services/document_hub/user_erasure.py`; `tests/{unit,db}/document_hub/`;
`document_hub/{cleanup,indexing,keys}.py` and `file_readers/_parse_sidecar.py` (factored primitives and optional
per-page `on_page` callbacks; ledger rulings at Task 7 and T7 I-6).
- [x] Private + chat-scoped docs deleted through DocHub's own doors, then hard-deleted, with BOTH prefixes (raw backup
  included, the `tenant_object_prefixes` semantics) and their index docs and chunks. Shared docs (R-DOCHUB-REKEY): copy
  to the `deleted-user` owner path, rewrite the row's owner and any stored key, update the Weaviate owner, delete the
  old objects; the doc still opens, searches, and can be deleted by a tenant admin. A document whose attempt may still
  be live (DocHub's `abandonment_cutoff`, about 30 minutes) is held: a private one is purged with its row kept as an
  orphan until past the cutoff (T7 I-3); a shared one is left alone, then settled with
  `mark_processing_failed(PROCESSING_ABANDONED)` for the attempt it judged, and re-keyed (T7 I-4, N-1).
- [x] Parse sidecars via the user's aliases; a content record goes only when no other alias references it. Residue:
  rows owned by either id, objects under `document-hub/{raw,artifacts}/{t}/{id}/`, index docs by owner.
- [x] Proofs: fake S3 + Weaviate unit lane, db rows; a crash after the copy and after the rewrite each converges on
  rerun. Mutants: re-key without copy (shared doc unreadable); backup kept on a private delete.

### Task 8: copilot-mro — chats, chat objects and the seam composer (P2, lane M1, after Tasks 6–7)
Owned: new `copilot_mro/app/services/user_erasure.py` (`erase_user`, `user_residue`); `tests/{unit,db}/user_erasure/`.
`tests/unit/user_erasure/` includes the seam's key and scrub-pin files.
- [x] R-ORDER as amended by R-LINKS-LAST: gather the chat ids (both ids, every department, any deleted state) and the
  chat-file attachment ids (the turns' `s3_key`s under the person's own prefixes ∪ the `chat-files/{t}/{id}/` listing,
  both ids) → Task 6 → per chat: reap `dataviews/{t}/{chat}/`, its attachment objects + sidecar aliases and
  `agent-state/{t}/{chat}/`, then `scrub_chat_copies` in its own txn, then `reap_chat_copies` → Task 7 → drain the
  person's in-flight runs (60 s, fails the step) → residue with the SAME gathered ids, re-erased up to twice until zero
  → hard purge of the verified, soft-deleted `chats` and their `chat_blocks` in one txn → sweep
  `chat-files|chat-images|chat-audio/{t}/{id}/` under both ids → the whole residue once more. The report carries counts
  and orphan counts only; any exception carries `partial`.
- [x] Proofs: db — a chat deleted BEFORE the erasure is scrubbed and purged; sibling and second tenant untouched; a
  crash after chat k's scrub, after the purge, and at a drain timeout each converge on the rerun (partial + rerun = one
  clean pass); unit — order pinned by a spy. Mutants: purge before scrub; skip already-deleted chats; keep a department
  filter.

### Task 9: core — core-local rows, core line and drift guard (P2, lane C)
Owned: new `core/core/resources/user_erasure/core_copies.py`; `core/tests/{unit,db}/user_erasure/`;
`core/resources/analytics/panels/quality.py` (imports the moved `DELETED_USER_ID`).
- [x] One tenant-bound txn: the user's automations deleted; attributed one-shots → `deleted-user`, and the person's id
  in any run's `entitlements_used` → `deleted-user` (definition-backed runs carry no `user_id`); `product_events` user
  id → `deleted-user`, session NULL; comments, mentions, notifications, subscriptions, thumbs, invitations per
  D10/R-PLACEMENTS (addressed to the person: deleted, redeemed ones included — T9 concern 2; the ones they sent: kept,
  `invited_by` → `deleted-user`, pending ones still redeemable — owner question 6); RBAC provenance and
  `authorization_events` untouched (D9); the `users` row is NOT deleted here (Task 11). Residue query; drift guard over
  core's registry as in Task 6.
- [x] Proofs: db with sibling + second tenant; the thumbs trigger leaves counts right; rerun 0 rows. Mutants:
  delete comments instead of anonymising; leave mentions.

### Task 10: shift-optimizer — attribution seam (P2, lane S)
Owned: new `shift_optimizer/app/services/user_erasure.py`; unit + db tests in their domain folders.
- [x] `optimizer_jobs.created_by`, `optimizer_runs.launched_by` → `deleted-user` for the tenant and both ids; residue
  query; line + drift guard. Proofs: db (`shift_optimizer_test`) with sibling + second tenant; mutant: drop the tenant
  predicate (record whether RLS or the test catches it). `erase` / `residue` take a structural subject (no core
  import) and return `Dict[str, int]` keyed `optimizer_jobs__created_by` / `optimizer_runs__launched_by`; one
  transaction; the pool's statement timeout set explicitly. Task 12 adapts `erase` to `SeamErasure`.

### Task 11: core — the orchestrator, completion and receipt (P3, lane C)
Owned (widened at the P3 pre-flight, C-8; core has no CLI, C-1):
- `core/core/resources/user_erasure/`:
  - new `service.py`;
  - `freeze.py`: the immediate enqueue after the freeze commits (P1 review COMP I-5); the platform door's rule in
    `_CANCELS_FROM`; the teardown-only entry D11 needs (COMP I-1);
  - `erasure_endpoints.py`: `GET /users/erasures`, and the fold of `erasure_http.py` (SIMP M-6, C-10);
  - `ledger.py`: the delay and the guard (C-3), the due-row query (C-26), the tenant listing, the escalation move
    (CORR M-3), `CHANNEL_TEARDOWN`, the one-shot's runtime ceiling and the receipt declaration;
  - `__init__.py`: the names the api imports from the package;
  - `lifecycle.py`: `SeamRefused` and the refusal marker (C-14), the `ErasureIncomplete(partial=)` base (S-M3), the
    answer check (FI-B);
  - `core_copies.py`: the step on the caller's cursor;
  - `cognito_accounts.py`: one `custom:company` read (C-12).
- `core/core/resources/automations/services/automation_store.py`: the drain (C-6); `not_before` on the one-shot
  enqueue and scan (C-3).
- `core/core/resources/user/services/user_service.py` (COMP M-3); `core/core/resources/user/user_endpoints.py`
  (C-10); `core/core/fastapi_app.py` (C-9).
- Tests, including `core/tests/api/routing/test_core_route_dispatch_order.py`.
- [x] `run_erasure(*, tenant_id, request_id, one_shot_grace_seconds)` (C-16). Ledger reads are tenant-keyed under
  RLS, so the tenant is an argument, never looked up from the request id.
  - When to run again (P3 plan review IM-4, controller ruling on the plan fix): `run_erasure` never enqueues. Its
    outcome carries `rerun_at`:
    - `erase_after`, when a behind-clock run finds nothing to move on a still-`frozen` request (step 1);
    - now + 10 minutes, when a run ends incomplete with tries left (Retries, below);
    - none otherwise: completed, refused, cancelled, or out of tries.

    The api job enqueues for it; the owner CLI ignores it (Task 12). The caller decides the side effect, so no boolean
    argument changes what the function does, and C-16's signature stands.
  - One run per request (P3 plan review IM-3): `run_erasure` holds a per-request advisory lock, keyed on the request
    id, for its whole run. A run that cannot take it returns at once, with no `rerun_at`. Two runs of one request can
    otherwise meet: the freeze's one-shot and the due sweep, a recovery re-queue beside its zombie
    (`recover_stale_one_shot_runs` says the consumer must tolerate it), and the CLI beside a scheduled run.
  1. `frozen → erasing`, held until `erase_after` in both modes (owner question 5, below). A run whose clock is
     behind the requester's finds nothing to move, and returns its `rerun_at`.
  2. The drain (below).
  3. Each registered seam's `erase` in declared order (copilot-mro, shift-optimizer), then core's own `core_copies`
     erase (a recorded step, not a registered seam — P1 review SIMP M-2). Step state is persisted after each.
  4. Cognito AdminDeleteUser, the last step before the residue (not-found = success, so a retry converges;
     `account_exists` joins the residue — COMP I-3). `users` is tenant-RLS, so whose account it is comes from the
     account's `custom:company` claim, the estate's one-tenant-per-sub authority. The claim holds a tenant NAME,
     matched against `tenants.tenant_name` (`tenant_claim_writer.py`; CORR N-3, C-12, P3 plan review MI-2):
     - the claim names this tenant's `tenant_name`, or is absent → delete the account;
     - it names another tenant → no delete, `prior_cognito_enabled` restored, `cognito_account_kept` counted in the
       receipt, and the kept account is not residue;
     - the pool no longer holds the account (the retry after a landed delete) → the step is done.

     The read is one new non-personal attribute read in `cognito_accounts`, amending Task 2's "no attribute reads".
     It does not reuse `existing_tenant_claim`, which raises `ClaimReadUnavailable` for a user the pool cannot find
     and would fail the retry forever; `cognito_accounts` already answers a missing account as a fact.
  5. All-zero residue (R-VERIFY).
  6. The channel teardown, for a `CHANNEL_TEARDOWN` request only (D11; "The teardown-only request", below). Every
     other request skips it.
  7. ONE completion transaction, `transaction.bound_transaction(tenant, roster, read_only=False)` (C-15):
     - core's residue predicates re-run on this cursor, and the commit is refused unless they read zero (P2
       correctness FI-2);
     - `DELETE FROM users` (cascade; `UserService.delete_user` opens its own connection, so it becomes this cursor's
       helper — COMP M-3). After a teardown it may find 0 rows: `users` cascades with the tenant, and the roster
       reads empty (P3 plan review MI-11);
     - the `authorization_events` row (delete / `user`, subject = surrogate, change = request id + counts + `rtbf`
       (Task 20 F3 fix round 2, read from the row this transaction locks) + the request's via);
     - ledger completed.
- [x] P2 carry-ins (ledger rulings; each is owed here):
  - **The drain, after the freeze and before the first seam (FI-S1, C-6):** wait — bounded; a timeout fails the step,
    which is then retried — until no `claimed`/`running` run of the person's automations and no one-shot attributed
    to either id remains (`record_run_result` writes `entitlements_used`, naming the owner, at close).
    - It is a function in `automation_store.py`, built from the reapers' and the recovery's own predicate fragments,
      so it cannot drift from them: no restated copy, and no pin against one.
    - Count only runs that can still write: `running` inside its runtime ceiling, `claimed` inside its start grace. A
      stale row never holds the drain, because in the scheduler-off deployment nothing reaps it (P2 correctness I-1).
    - Both families count: the automation arms and the one-shot arms (one-shots attributed to either id). A one-shot
      `running` past its ceiling but inside the unserved grace window holds the drain, because the recovery
      re-queues it and it can still write. The grace is `run_erasure`'s `one_shot_grace_seconds`, the deployment's own
      `AUTOMATION_ONE_SHOT_UNSERVED_GRACE_SECONDS` (Task 12): a deployment window LONGER than the one passed lets the
      drain release while a re-queueable run can still write (a shorter one only waits longer).
    - The query keeps a top-level status clause over every status any arm accepts, so the active-runs partial index
      serves it (P2 fix F-1: 1,912 ms against 2 ms at 200k runs in one tenant).
    - This is the only drain: the copilot-mro seam's own drain was removed by the P2 simplification batch (FI-S1).
  - **Never keep a seam's exception text:** the orchestrator prints and stores only the seam exception's
    `failure_fields`, never its message or traceback (the P2 fix gave `PrefixNotDeleted` fixed text; others need not).
  - **Record core's step on its own transaction:** a process death after a seam's commit but before the ledger
    records the step would under-report. `erase_core_copies` opens and commits its own transaction today, so it takes
    the caller's cursor, or runs the ledger step write before its own commit: the step's work and its ledger step
    commit together (P2 correctness M-4, C-8).
  - **A freeze queued behind another in the same tenant** is cancelled at the 15 s statement ceiling (the freeze runs
    in `bound_transaction` since the core follow-up round). The door answers it with a fixed, retryable 503, as it
    answers `ACCOUNT_UNAVAILABLE`, never a 500 (p2c2 review m-6).
  - **Counts and orphans:** a step's counts are summed across attempts, adding each failed attempt's `exc.partial` (a
    core `SeamErasure`). Orphans are the latest value per orphan key, never a sum: a source that stops reporting (a
    chat gone before the last attempt) keeps its last value (P2 fix re-review 2, R2-1). In dev without
    `PHOENIX_ENDPOINT` every chat's session is one.
  - **What residue proves:** copilot-mro's `user_residue` after its own purge gathers no chat ids, so its chat-keyed
    placements read zero by construction; their proof is the seam's own final read inside `erase_user`. Three
    placements are statement-proven, not residue-proven, and the receipt says so: `improvement_signals__detail`,
    `memory_item_events__metadata`, `improvement_findings__evidence` (and the findings chat arm).
  - **Retries (C-13; no DDL, no new state):** an incomplete leaves the request `erasing` and its step `failed`, with
    that step's `attempts` in `steps` + 1 (the ledger has no request-level count; P3 plan review MI-12). The retry
    policy stays in core: the run's `rerun_at` is now + 10 minutes while the failed step's `attempts` is under six,
    and none after. Six tries outlast DocHub's fixed 30-minute hold from an attempt's start, and allow six passes of
    Task 6's index naming read (`ceil(N / 10 000)`). After the sixth, the daily due sweep picks the row up.
  - **The one-shot's runtime ceiling (P3 plan review MI-4):** one core constant beside `USER_ERASURE_KIND`, passed as
    `max_runtime_seconds` by every `user_erasure` enqueue (the freeze's, Task 12's job and its due sweep). Size it
    against one attempt over the person's chat count (every attempt re-scrubs and re-reaps every chat, up to 5 s per
    Phoenix request), or skip the reap for a chat whose scrub counted 0 and whose last reap left no orphan.
  - **Refused vs incomplete (C-14):** a refusal is permanent; an incomplete is retried.
    - The seams share no taxonomy, so core defines `lifecycle.SeamRefused` and a structural marker attribute,
      `erasure_refused = True`. Task 11b sets it on copilot-mro's refusals; Task 12's adapter maps shift-optimizer's.
    - A step that raises with the marker, or a subject that fails construction (`ErasureSubject` validates itself),
      is a refusal: the request moves to `failed`, which the due sweep never selects. The owner path is the CLI's run
      one, after the data is fixed. A malformed legacy chat id (`REFUSED_CHAT_ID`) is one such refusal.
    - Everything else is incomplete.
    - `lifecycle` also declares the one `partial` carrier, an `ErasureIncomplete(partial=)` base (P2 simplicity
      S-M3).
  - **The answer check (FI-B):** an `erase` answer that is not a `SeamErasure` fails the step with fixed text, before
    it is recorded.
  - **The job (C-16):** the `user_erasure` one-shot's params are exactly `{"request_id": …}`; the tenant comes from
    the run row; `user_id=None` on every enqueue. Task 12 pins the consumer side.
- [x] Repeat requests: an immediate/RTBF request over an open windowed one escalates it or refuses with its own 409,
  never silently returns the weaker row (CORR M-3).
- [x] The teardown-only request (D11, COMP I-1; P3 plan review IM-1). Task 11 builds its entry and its guard; Task 13
  builds its caller and its step.
  - One core constant, `CHANNEL_TEARDOWN` (`ledger.py`), is its `requested_by`, the ledger's only durable
    discriminator.
  - Only the teardown-only entry in `freeze.py` writes it (`request_erasure` refuses the token), and only that entry
    skips the last-active-owner refusal: the channel user is the personal tenant's sole Tenant Owner.
  - Until Task 13 lands, `run_erasure` refuses such a request at step 6: the step is recorded `failed`, the request
    moves to `failed`, and it never completes.
- [x] The due-row query (C-26; Task 12 owns the loop): bound to one tenant, it returns `frozen` rows past
  `erase_after` and `erasing` rows, never `failed` ones. A missing `users` row is tolerated; a deleted tenant's rows
  are unreachable, which CORR N-4 accepts.
  - Both arms skip a request with a `user_erasure` run in flight (P3 plan review IM-3, IM-4).
  - In flight is built from the drain's own fragments: a `running` row inside its ceiling, or a `claimed` row not yet
    past its `scheduled_for` plus the start grace. So a retry nothing serves (scheduler off) stops counting once it is
    overdue, and the next `--run-due` picks the request up.
- [x] Receipt (C-17): identifier keys and non-negative integers only. The key set is declared once, as one literal
  mapping in `user_erasure/ledger.py`, which Task 14's generator parses textually (the run-trigger generator's
  precedent; P3 plan review MI-10). The dashboard renders the receipt from that generated contract (Task 14).
  - Bounds, as `<store>_days`: Loki 14, Tempo 3, CloudWatch 30, Phoenix 30, S3 noncurrent 30 after deletion.
  - Limits, each a key valued 1: downloaded exports and optimizer workbooks; inline or zombie DocHub executors past
    the declared bound; an `updated_at` PATCH extending a queued shared attempt's hold; the attempt-start window; text
    naming the person with no id (owner question 3); backups and host SDK transcripts (owner items); the three
    statement-proven placements.
  - Counts: `cognito_account_kept` (step 4).
  - No orphan-operator key: Task 19 lands in P3, and the rollout clears existing orphans before the routes serve
    (C-18). No replay record (owner decision 31).
- [x] `GET /users/erasures` (C-9): the tenant's ledger rows — ids, state, timestamps, `cancellable`, receipt — so a
  receipt stays reachable after the `users` row is gone (COMP I-6).
  - Gated by `users_modify` without a target id: a variant of `_require_user_delete_allowed`.
  - `user_router` owns `GET /users/{user_id}`, so `user_erasure_router` is mounted BEFORE it, with the load-bearing
    comment (`user_operator_router` is the precedent; `GET /users/status` is the live collision the sweep records in
    `KNOWN_SHADOWED`; P3 plan review MI-1). The dispatch-order sweep pins it.
- [x] The fold (SIMP M-6, C-10): `erasure_http.py` goes into `erasure_endpoints.py`. `DELETE /users/{user_id}` (the
  route is literally the POST) moves there, and `USER_FROZEN` moves beside `UserErasurePending`, so the fold creates
  no import cycle. Fallback: keep `erasure_http.py` and correct its docstring.
- [x] Proofs, each with its mutant (C-25):
  - unit with fake seams: order, resume from each failed step, a completed request answers done, non-zero residue
    blocks the users delete; db: the event survives, the ledger has no name/email column. Mutants: users delete
    before the residue check; the event written outside the txn.
  - The drain: a stale row releases, a live row holds, a one-shot inside its grace holds, and the top-level status
    clause is present. Mutant: drop the grace arm.
  - The scan: a one-shot enqueued with a not-before is not served before it, and one without is served at once.
    Mutant: drop the `scheduled_for` predicate.
  - The 30-minute delay. Mutant: never hold an immediate request.
  - `failure_fields` only. Mutant: log `str(exc)`.
  - Core's step and its ledger step commit together. Mutant: record the step after the commit.
  - Counts summed with `partial`; orphans the latest per key (one chat vanishes before the last attempt). Mutant: sum
    the orphans.
  - Refused versus incomplete: a marked refusal and a malformed subject move to `failed`; any other exception leaves
    the request `erasing`, its failed step's `attempts` counted. Mutant: classify by exception type.
  - The escalation. Mutant: return the weaker row.
  - `GET /users/erasures` is reachable, by the dispatch sweep. Mutant: mount `user_erasure_router` after
    `user_router`.
  - The completion-cursor residue recheck (FI-2). Mutant: skip it.
  - The Cognito claim check: this tenant's name or no claim deletes; another tenant keeps and restores; a missing
    account is done. Mutants: delete regardless; fail the step on a missing account.
  - A seam answer that is not a `SeamErasure` fails the step (FI-B). Mutant: record the answer unchecked.
  - A cancel restores the person with no automation touched (C-5). Mutant: restore a disabled automation on cancel.
  - A freeze queued behind another answers the fixed, retryable 503 (m-6). Mutant: answer it with a 500.
  - The one-shot's params are exactly `{request_id}` with `user_id=None` (C-16, producer side). Mutant: put the
    person's id in `params`.
  - The due-row query returns `frozen` rows past `erase_after` and `erasing` rows with no run in flight, never a
    `failed` row, and a stale `claimed` retry does not hide a request. Mutants: select `failed`; count every
    `claimed` row as in flight.
  - One run per request: of two concurrent runs of one request, one runs the seams and the other returns with no
    `rerun_at`. Mutant: drop the lock.
  - The outcome's `rerun_at`: `erase_after` for a behind-clock run on a still-`frozen` request; now + 10 minutes for
    an incomplete whose failed step's `attempts` is under six; none for a completed, refused or cancelled request, or
    after the sixth try. Mutants: `rerun_at` for a cancelled request; `rerun_at` past the sixth try.
  - The teardown-only entry alone writes `CHANNEL_TEARDOWN` and alone skips the last-owner refusal. Mutants: skip the
    refusal for every request; let `request_erasure` write the token.
  - A `CHANNEL_TEARDOWN` request is refused at step 6 and never completes; a request with any other `requested_by`
    never reaches step 6. Mutants: complete it without step 6; run step 6 for every request.
  - A platform request is cancellable only by the platform door. Mutant: let the tenant door cancel it.
  - The receipt carries only the declared keys, each with a non-negative integer. Mutant: write an undeclared key.
  - The fold: `DELETE /users/{user_id}` still answers 202 from its new home, and a fresh interpreter imports either
    module first (no cycle). Mutants: leave the moved route unmounted; import `USER_FROZEN` into `user_endpoints.py`
    from `erasure_endpoints.py`.

- [x] Owner rulings (2026-09-29):
  - **One drain, one re-erase loop, here (FI-S1, adopted).** Task 11 alone waits for the person's in-flight runs and
    alone retries a seam. copilot-mro's seam runs one pass: it raises an incomplete, and never purges, while its own
    residue is not zero (built in the P2 simplification batch).
  - **Immediate requests wait out open turns (owner question 5, C-3).** An immediate erasure runs 30 minutes after the
    freeze commits, not at once. The account is locked meanwhile, and the request stays uncancellable (by mode).
    - One core constant, `IMMEDIATE_ERASURE_DELAY = 30 min`, beside `ERASURE_WINDOW`. An immediate request's
      `erase_after = requested_at + IMMEDIATE_ERASURE_DELAY`, and the `frozen → erasing` guard holds both modes on
      `erase_after <= now` (the ledger's case for never holding an immediate request assumed a zero margin).
    - `enqueue_one_shot_run(…, not_before=)` writes `scheduled_for`, and the one-shot scan
      (`list_claimed_one_shot_runs`, which takes no clock today) takes the tick's `now` and selects only
      `scheduled_for <= now`. Existing callers pass nothing, so their behaviour is unchanged. The freeze enqueues with
      `not_before = erase_after`; Task 12's job enqueues for `rerun_at` with the same parameter.
    - A `not_before` is never more than the unserved grace ahead (30 minutes and 10 minutes, against a day). The
      unserved close measures from `created_at`, not `scheduled_for` (`_CLOSE_UNSERVED_ONE_SHOT_SQL`), so a longer
      wait could close a row before it may run (P3 plan review MI-3).
    - The scheduler defaults off (api `automations/settings.py`). Where it is off, an immediate erasure runs at the
      owner's next `--run-due`, the existing owner item. Where it runs, the freeze's one-shot serves it, and a lost
      enqueue waits for the daily due sweep, up to 24 hours. Dev runs it `embedded` (iac and iac-roles `dev.tfvars`,
      found by Task 12's build).
    - For the wait to be a real bound, Task 11b bounds every interactive turn and the detached chat-file upload
      under it.
  - **A cancel restores the person and touches no automation (C-5; decision 32's mechanism, not its outcome).** The
    freeze disables nothing: a frozen owner's runs are recorded `skipped` (Task 12). A cancel restores the status and
    the Cognito state and has nothing else to restore; the erasure deletes the automations in core's step. This closes
    T3-C2. It replaces "a cancel re-enables exactly the automations the freeze disabled, their ids recorded in the
    ledger's steps", which could not be built: `record_step` writes only while `erasing`, and the steps hold
    identifier keys and integers, never an automation's UUID.

#### Notes: Task 11 — the orchestrator: DONE (core `ue-t11` `bcdccb3..69884eb`, merged `2ec64b5`, pushed; two-lens review, 2 fix rounds, a scoped re-review)
- Built as specified: `service.run_erasure` and its `rerun_at`, the per-request lock, the drain in
  `automation_store.py`, `not_before` on the one-shot enqueue and scan, the due-row query, the teardown-only entry, the
  receipt declaration (`ledger.RECEIPT_KEYS`), `GET /users/erasures` and the fold. Every `user_erasure` enqueue goes
  through one producer, `service.enqueue_erasure_run` (the freeze, Task 12's job and its due sweep).
- Rulings at the build:
  - The refusal marker is a class attribute, read through `lifecycle.MarkedRefusal`. A seam hands its partial over
    through `lifecycle.carry_partial`, collected by `collecting_partials()`. Core's exception-text register refuses
    new entries, so core reads a seam's exception by type only; Task 11b followed.
  - Orphans are a `{source: n}` mapping, merged latest per source.
  - The receipt's log bound is `logs_days`, vendor-neutral (was `loki_days`).
  - `service` is not re-exported from the package (an import cycle through `user_service`); the api imports it
    directly.
- Review fixes:
  - The Cognito keep rule was corrected (review A I-1): the account is kept only when its claim names an EXISTING
    tenant other than this one. A claim naming no existing tenant counts as absent, and the account is deleted. The
    claim's tenant-name read now runs against Postgres in a db test (review B I-1).
  - The lock key is per request, and completion re-asserts the lock before its transaction (`LOCK_LOST`). Fix round 2
    pinned the real lock's joint (re-review N-1).
  - `enqueue_erasure_run` raises `ValueError` for a `not_before` more than 30 minutes ahead.
  - Only the owner's explicit run resumes a `failed` request; Task 12's job skips one.
  - The erasure's own three provenance entries are keyed on qualified names (`_STATES_A_CONSTANT_AT`), so a decoy
    method sharing a bare name is not admitted for them.
  - Three stale "at once" sentences in `table_definitions.py` were corrected.
  - Also fixed: the `scratch_tenants` fixture's missing `functools.wraps` (a pre-existing xdist-only red).
- Step 6 refused a `CHANNEL_TEARDOWN` request until Task 13 replaced it.
- Left as Future Improvements: the lock-check window and the remaining bare-keyed provenance entries (both recorded at
  the P3 phase review), and the keep rule's trust in the claim (re-review O-2).
- P3 phase review: `ledger.py`'s comment that the job resumes a refused request is stale (review E M-6, fixed in the
  core batch). Orphans "latest per source" hold in core but not end to end, because copilot-mro reports one integer
  (review A M-1 = E M-3, a Future Improvement).
- Learning: a hand-off between two tasks needs one test that runs both halves together. Core's per-source proof drove
  a fake seam answering a mapping; the real seam answers one integer, and no reviewer saw the two side by side.

### Task 11b: copilot-mro — open turns and uploads bounded under the delay; the refusal marker (P3, lane M1)
May start once Task 11 has committed `IMMEDIATE_ERASURE_DELAY`, its tests pinning `PYTHONPATH` to `core-erase`; merges
only after Task 11 merges (owner question 5's copilot-mro half, C-22; the marker, C-14; P3 plan review MI-6).
Owned (P3 plan review IM-5), all under `copilot_mro/app/services/`:
- the turn construction: `agent_shared/pipeline.py` (`build_prepared_turn`) and `agent_claude/legacy_adapter.py`;
- the Claude SDK orchestrator's loop, `agent_claude/orchestrator.py`;
- `chat_file_service.py`;
- the refusal types in `user_erasure.py` and in `copilot_mro/app/db/chat_history/erased_user_copies.py`;
- tests in their domain folders.
- [x] Every interactive turn gets a hard deadline.
  - The field is `PreparedTurn.deadline` (`agent_shared/contracts/turn.py`). `copilot_mro/app/config.py`'s comment
    calls it `TurnContext.deadline`; no such type exists.
  - Neither builder assigns it today: `build_prepared_turn`, called from the composed pipeline and from the SDK
    legacy adapter.
  - Only the LangGraph backend (`lang_agent/backend.py`, `lang_agent/controls.py`) and the tool dispatcher enforce
    it. The Claude SDK orchestrator never reads it, so assigning it alone does not stop an SDK turn's model loop.
  - Every backend that serves an interactive turn enforces it, the Claude SDK orchestrator's loop included. An
    automation run keeps its own runtime ceiling; Task 11's drain waits for it.
- [x] The detached chat-file upload task (up to 4 attempts) gets a total budget.
- [x] Both bounds derive from core's `IMMEDIATE_ERASURE_DELAY` with a margin: the turn deadline, the upload budget and
  the margin together stay under the delay, pinned against the constant (copilot-mro imports core).
- [x] The refusal marker: `erasure_refused = True` on `UserErasureRefused` and `ErasedUserCopiesRefused`; no
  incomplete carries it. Document Hub has had no refusal of its own since the P2 simplification batch (its subject
  check moved into `ErasureSubject`).
- [x] Proofs: a turn past its deadline stops, on each serving backend (LangGraph and the Claude SDK); an upload past
  its budget stops retrying; the pin fails once the sum reaches the delay; each refusal type carries the marker and
  each incomplete does not. Mutants: leave the deadline unassigned; drop the SDK backend's enforcement; drop the
  upload budget; drop the marker from one refusal type.
- [x] **Carry-ins from Task 11's build and review (2026-09-30).** Core reads a seam's exception by its type and frames
  only (core's exception-text register refuses new entries), so copilot-mro must hand over through core's helpers:
  - `UserErasureRefused` declares `erasure_refused = True` in its class body (or derives from `lifecycle.SeamRefused`),
    so `isinstance(exc, lifecycle.MarkedRefusal)` holds. Unmarked, a refusal is retried six times, then by the daily
    sweep, forever.
  - The whole attempt's partial is raised through `lifecycle.carry_partial(exc, tally.erasure())`, replacing the bare
    `exc.partial = …` in `user_erasure.py`; `UserErasureIncomplete` subclasses `lifecycle.ErasureIncomplete`.
  - `carry_partial` runs inside `run_erasure`'s context (`asyncio.to_thread` keeps it; a bare executor worker drops the
    partial silently).
  - Proofs: `isinstance(UserErasureRefused(...), lifecycle.MarkedRefusal)`; a seam raising mid-way leaves the whole
    attempt's partial in `collecting_partials()`. Optional: orphans keyed per source (`{source: n}`).
  - Lands no later than Task 12's seam registration.

#### Notes: Task 11b — open turns, uploads, the marker: DONE (copilot-mro `ue-t11b` `5f98c9d3..7cad1c49`, merged `d3301c3a`, pushed; 1 review, 1 fix round accepted on the diff)
- Built: `erasure_delay_bounds.py` derives the three spans as fractions of core's `IMMEDIATE_ERASURE_DELAY`: the turn
  deadline a half (15 minutes), the upload budget a quarter (7.5 minutes), the margin a sixth (5 minutes); 27.5
  minutes together.
- `PreparedTurn.deadline` is assigned for an interactive turn: a new `interactive` keyword on `build_prepared_turn`
  and on both `execute` surfaces, which both `/rag` doors pass as `True` (`copilot_mro/app/api/chat_management.py`,
  outside Owned). Keying on the session prefix was rejected: the client sets `X-Session-ID`. Telegram's turns use
  the stream door, so they are bounded too.
- The Claude SDK loop runs under `asyncio.timeout`. After review I-1, its post-loop fuse, judge and settle run under
  what is left of the deadline too, with the caller's settle tasks shielded.
- The chat-file upload task has a total budget. A retry needs its back-off plus a tenth of the budget, checked before
  and after the wait (review M-1, M-2).
- Both refusal types carry `erasure_refused = True`; `UserErasureIncomplete` subclasses `lifecycle.ErasureIncomplete`
  and raises through `carry_partial`. The seam's own refusal check is `isinstance(exc, lifecycle.MarkedRefusal)`
  (review M-3).
- Merged before Task 12, which the plan allowed ("no later than").
- Not built: the optional per-source orphans.
- Recorded as a Future Improvement at its review: the late-anchored bounds, `TimeoutError` against
  `deadline_exceeded`, the `interactive` default, the unmeasured writers and the classifier awaits.
- P3 phase review: the bounds pin cannot fail for a change on core's side, because it pins only the fractions
  (reviews C M-5, E M-5: core's delay at 5 minutes survived every copilot-mro file that uses the bounds). Its fix is a
  Task 17 pin. The missing per-source orphans let a retry's 0 overwrite an attempt's orphans (a Future Improvement).

### Task 12: api — wiring, the job kind, the due sweep, the owner CLI (P3, lane A, after Task 11 merges)
Merges only after Task 19's copilot-mro half has merged and the owner has run the orphan script on dev (Deploy/rollout
step 2; P3 plan review MI-6).
Owned (C-23): new `api/flynapse_api/user_erasure_wiring.py` + its call in `routers/users.py` beside the partition
wiring; new `flynapse_api/user_erasure_cli.py`; new `automations/user_erasure_job.py`; `automations/tasks.py`;
`automations/loop.py` (the kind site, `ONE_SHOT_FEATURE_WIRING`); `automations/executor.py` (C-5); api tests.
- [x] Register the copilot-mro and shift-optimizer seams all-or-nothing (RuntimeError at assembly, as
  `partition_wiring`). The `user_erasure` one-shot kind calls `run_erasure` with the run row's tenant, the params'
  `request_id` and the deployment's grace (C-16). When the outcome carries `rerun_at`, the kind enqueues one
  `user_erasure` one-shot with `not_before = rerun_at`; otherwise it enqueues nothing. It is the only caller that acts
  on `rerun_at` (P3 plan review IM-4, controller ruling on the plan fix).
- [x] Every process that serves the kind wires the seams itself (C-2). The scheduler worker mounts no core and never
  imports `routers/users.py` (`main.py` is its only importer), yet it serves every wired one-shot kind.
  - The kind's registration function calls `partition_wiring.wire()` and `user_erasure_wiring.wire()` first, and
    registers the kind only if both succeed. Otherwise the rows stay `claimed` and the recovery census logs them.
  - The partition hooks are needed because Task 13's teardown step checks both partition registries and calls
    `remove_partitions`, which raise when unregistered, and only `routers/users.py` wires them today (P3 plan review
    IM-2).
  - `routers/users.py` keeps its call for the request doors. The CLI calls both `wire()`s too, since it runs
    `run_erasure` in-process.
- [x] The due sweep (C-26), a daily global builtin. A global builtin runs bound to `__SYSTEM__` and `user_erasures`
  is tenant-RLS, so it iterates `tenant_registry.all_tenant_ids()` and binds each tenant (the `tasks.py` precedent),
  runs Task 11's due-row query, and enqueues one `user_erasure` one-shot per due row.
- [x] A frozen owner's automations are skipped, never disabled (owner, C-5).
  - When the identity check raises `OWNER_ERASURE_PENDING` (`identity.py`), the executor records the run `skipped`
    with that reason. Nothing is disabled and no bell row is written. This closes T3-C1 and T3-M4.
  - Where the silence and the no-retry live (P3 plan review MI-5): `owner_erasure_pending` joins `SILENT_REASONS`
    (`loop.py`) and the executor recorder's no-announce exclusion (today it spares only `entitlements_unresolved`
    from `announce_missed_run`). It gets no entry in `RETRY_BACKOFF_BY_REASON`: a reason absent there is never
    retried.
  - `AUTOMATION_SCHEDULER_MODE` defaults to off (`automations/settings.py`), but dev runs it `embedded` (iac and
    iac-roles `dev.tfvars`, found by Task 12's build), so the old stand-down could have disabled a frozen owner's
    automations. The owner's read-only check on dev `copilot_mro` found none (0 rows, 2026-09-30), so nothing needed
    re-enabling. A database where a freeze ran under a running scheduler gets the same check
    (`t12-owner-standdown-check.sql` in the SDD directory) before Task 12's code serves it.
- [x] P2 carry-ins:
  - shift-optimizer's `erase` returns `Dict[str, int]` (it imports no core). Register it through an adapter whose
    `erase` answers a `SeamErasure` holding those counts and zero orphans, and which maps the seam's
    `ErasureSubjectRefused` (a `ValueError`) to `SeamRefused` (C-14). Its `residue` is registered as is. copilot-mro's
    pair is `copilot_mro.app.services.user_erasure.erase_user` / `user_residue`, as is.
  - The api imports `shift_optimizer` optionally (`routers/optimizer.py` swallows `ImportError`): the wiring imports it
    inside the all-or-nothing block, so a missing package registers nothing and every request door answers 503.
  - Every `user_erasure` enqueue — the due sweep's and the kind's included — carries `user_id=None` (Task 11's drain
    counts runs attributed to the person, so an attributed erasure run would wait on itself), params exactly
    `{"request_id": …}` (C-16), and core's one-shot runtime ceiling constant (Task 11, MI-4).
  - Pass the deployment's `AUTOMATION_ONE_SHOT_UNSERVED_GRACE_SECONDS` to `run_erasure` (default 86 400, matching the
    recovery's default), which hands it to the drain (C-7; why, Task 11's drain bullet).
  - Never log or store a seam exception's message or traceback, only its `failure_fields`.
- [x] The owner CLI, the platform door (R-DOOR, C-1): `python -m flynapse_api.user_erasure_cli`.
  - request: `via = script`, `requested_by = platform-cli`, with immediate and RTBF flags;
  - cancel, under the platform door's rule in `_CANCELS_FROM`;
  - list;
  - run one (also the owner path for a `failed` request, once its data is fixed);
  - `--run-due` (covers scheduler-off). No `--replay-completed` (owner decision 31).
  - The CLI never enqueues. `--run-due` runs each due request in-process, and neither it nor run one acts on
    `rerun_at`: the due sweep or the next `--run-due` picks the request up. With the scheduler off, nothing would
    serve a one-shot the CLI enqueued (P3 plan review IM-4).
- [x] Proofs (worktree-pinned):
  - all seams registered, and each registered seam's `erase` returns a `SeamErasure`;
  - a worker-shaped process (no core router imported) serves the kind with the seams AND the partition hooks
    registered, and a failed wiring leaves the kind unregistered. Mutants: register the kind without wiring; wire the
    seams only;
  - the kind runs a fake erasure with the run row's tenant and params exactly `{request_id}` (C-16, consumer side),
    and enqueues one `user_erasure` one-shot for `rerun_at` exactly when the outcome carries one. Mutant: the job
    ignores `rerun_at`;
  - the due sweep binds each tenant and enqueues each due row once. Mutant: bind the sweep to `__SYSTEM__` only (zero
    rows enqueued);
  - the adapter maps the seam's refusal to `SeamRefused` and passes every other exception through. Mutant: map every
    exception to `SeamRefused`;
  - a frozen owner's run is recorded `skipped` with `owner_erasure_pending`; its definition stays enabled, no
    notification is written and no retry is stamped. Mutant: disable the definition (the old stand-down);
  - the CLI wires the seams and the partition hooks before it requests or runs. Mutant: request before wiring;
  - the CLI never enqueues: `--run-due` runs each due request in-process, and neither it nor run one enqueues for an
    outcome's `rerun_at`. Mutant: the CLI enqueues for `rerun_at`.
- [x] **Carry-ins from Task 11's build and review (2026-09-30).**
  - Import `core.resources.user_erasure.service` and `freeze` directly: the package does not re-export `service`
    (an import cycle through `user_service`).
  - The job skips a `failed` request before calling `run_erasure` (a stale queued retry must not resume a refused
    request). Mutant: the job runs a `failed` request.
  - The job catches `enqueue_erasure_run`'s `ValueError` (a `not_before` more than 30 minutes ahead), logs it and leaves
    the request to the daily sweep. Mutant: the job lets it raise.
  - The CLI help and the runbook say that with the scheduler off, `--run-due` sees an immediate request only from
    `erase_after` plus the 10-minute start grace, because the freeze itself enqueues the request's one-shot.

#### Notes: Task 12 — api wiring, job, due sweep, owner CLI: DONE (api `ue-t12` `e449c7d..bd06a46`, merged `9a15ecb`, pushed; 1 review, 1 fix round accepted on the diff)
- Built: `user_erasure_wiring.wire()` registers both seams, all or nothing. shift-optimizer goes through an adapter
  that answers a `SeamErasure` and maps `ErasureSubjectRefused` to `SeamRefused`.
- The `user_erasure` kind (`automations/user_erasure_job.py`) skips a `failed` request, catches core's `ValueError`,
  and enqueues once for `rerun_at`. Every serving process wires both registries before registering it (`loop.py`).
- The due sweep is a built-in, `sweep_due_user_erasures`, daily at 04:00 UTC, binding each tenant in turn.
- A frozen owner's run: `OwnerErasurePending(EntitlementsUnresolved)` in api `automations/identity.py` (outside
  Owned). The executor records it `skipped` with `owner_erasure_pending`, silently, with no retry.
- The CLI's module docstring is the runbook: the scheduler-off timing of an immediate request, and the rollback order.
- Deviation: the plan's premise that the scheduler is unset in every deployment was false; dev runs it `embedded`.
  Before the merge the owner ran a read-only check on dev `copilot_mro` for automations the old stand-down had
  disabled over a freeze: 0 rows. The controller corrected that check's SQL first (review I-1: a uuid/varchar join,
  row security hiding every row from a non-superuser, a naive time window).
- Merged after the owner's dev orphan-script run (Deploy/rollout 2) and that check.
- Review fixes: the runbook's scheduler premise (M-1); tests for three failure paths (M-2); the rollback cancels first
  (M-4, Deploy/rollout 5). M-3, the failed check outside the lock, is a Future Improvement.
- P3 phase review: the dashboard has no copy for `owner_erasure_pending` (review E M-4, fixed in the dashboard batch);
  a Task 17 pin keeps the two in step.
- Learning: verify a plan's deployment premise before building on it. "Unset everywhere" came from the code default;
  dev's tfvars said otherwise.

### Task 13: core + telegram-bot — `/goodbye` erases the person too, on the job path, D11 (P3, lanes C and T, after Tasks 11 and 12)
Core's half merges after lane T's (P3 plan review CR-1, MI-6).
Owned:
- core (lane C):
  - `core/core/resources/channel_provisioning/channel_provisioning_endpoints.py`: the door's 202, and the
    provisioning POST's 409;
  - `core/core/resources/channel_provisioning/services/channel_provisioning_service.py`: the teardown body, moved from
    the endpoint, and the open-request check the POST reads;
  - `core/core/resources/user_erasure/service.py`: step 6;
  - core channel tests (they register fake seams, C-24) and the `user_erasure` tests for step 6.
- telegram-bot (lane T, `telegram-bot-erase`; P3 plan review CR-1, IM-6): the teardown client and the `/goodbye` flow,
  and their tests. Today the client parses the door's answer strictly as the 200 envelope, so a 202 would read as
  "malformed teardown", and the bot would tell a frozen pilot that nothing was deleted, on every repeat.
  - `flynapse_client/provisioning.py`: `teardown_channel_user` accepts both shapes, today's 200 envelope and the 202
    request body, and still refuses a foreign envelope; the 404 is unchanged;
  - `telegram_bot/handlers/goodbye.py`: after a 202, purge the bot's rows, then send the new farewell; the
    `partition_warning` branch serves the 200 shape only;
  - `telegram_bot/handlers/invites.py`: the bot's answer to the provisioning POST's deletion-in-progress 409
    (`_apology` words every provisioning refusal).
- [x] Owner ruling (2026-09-29, C-4): `/goodbye` takes the job path like every immediate erasure — lock, reply, erase
  30 minutes later. A synchronous erasure could neither wait out open turns (owner question 5) nor fit Task 11's
  retries in one request (DocHub's 30-minute hold).
- [x] The door opens the request through Task 11's teardown-only entry (`requested_by = CHANNEL_TEARDOWN`, an opaque
  token, so no DDL; `via = api`, mode immediate, rtbf false; P1 review COMP I-1) and answers 202. It deletes nothing.
- [x] The door's new contract is the 202 body: the request id, its state and `erase_after`, and no personal data. A
  repeat call answers the open request's body until the tenant is gone, then 404.
- [x] Step 6 (P3 plan review IM-1): Task 13 replaces Task 11's refusal with a direct call to the teardown body. No
  hook registry.
  - The body moves from the endpoint into `channel_provisioning_service.py`: its two preconditions (both partition
    registries, the cascade check), `delete_tenant`, then the partitions. The door no longer runs it.
  - The completion transaction follows (Task 11, step 7). The ledger and the event have no FK, so they survive the
    tenant.
- [x] Failures (P3 plan review MI-16):
  - a failure before the tenant delete commits leaves the tenant intact, and the retry converges;
  - a partition failure after it is logged with the finisher named (below), and the step counts done. The operator
    ids are enumerated before the delete and are gone after it, so a retry could not redo them.
- [x] The teardown step's partition-failure log names `delete_unentitled_partition.py --purged-tenant` plus direct
  partition removal, never the bare script: its `--tenant` mode deletes the torn-down tenant's ledger rows (P1 fix M2
  re-review).
- [x] While the channel user's teardown request is open, the provisioning POST answers a fixed 409 (deletion in
  progress) and creates nothing (P3 plan review IM-6).
  - Its detail differs from the namespace-conflict 409's, so the bot can tell the two apart.
  - Why: the bot purges its rows as soon as the door answers, so `/start` can reach the POST at once. The POST's
    idempotent replay would find the frozen tenant. Before step 4 it re-sets the frozen account's password. After
    step 4 it mints a new identity and an active `users` row in the tenant the job is about to delete, which leaves a
    live Cognito account naming a deleted tenant.
- [x] The bot's side (lane T):
  - on a 200 (a core without Task 13), today's flow and farewell; on a 202, purge, then the new farewell;
  - the new farewell says the account is locked now and erased later, and promises no time: in a scheduler-off
    deployment the erasure waits for the owner's `--run-due` (today's door deletes the tenant at once);
  - it says `/start` works again once the deletion completes, and no longer says the sign-in record stays (step 4
    deletes it);
  - the answer to the 409 says the deletion is still in progress and `/start` works again once it completes.
- [x] Proofs:
  - core (fake seams, fake Cognito): the door answers 202 with the request body, writes the `CHANNEL_TEARDOWN`
    request and deletes nothing; the job's run deletes the Cognito account, then tears the tenant down, then
    completes the ledger, and the tenant event is still written; a `CHANNEL_TEARDOWN` request completes only after
    its teardown step; a failure before the tenant delete leaves the tenant intact and a rerun converges; a partition
    failure after it counts the step done; a repeat call returns the open request's body, then 404 once the tenant is
    gone; while the request is open, the provisioning POST answers the fixed 409 and writes nothing. Mutants: delete
    the tenant in the door; run the teardown before the residue check; skip the teardown step; fail the step on a
    post-delete partition failure; replay the frozen account (drop the POST's open-request check).
  - lane T: the client parses the 202 body and the 200 envelope, and still refuses a foreign envelope; on a 202 the
    handler purges, then sends the new farewell; the 409 gets its own answer. Mutants: parse the 202 as the old
    envelope; answer the 409 as the generic provisioning refusal.

#### Notes: Task 13 — `/goodbye` on the job path: lane T DONE (telegram-bot `ue-t13-bot` `95dc9f7..6085886`, merged `8865fb3`, pushed); lane C DONE (core `ue-t13-core` `2ec64b5..52fb9da`, merged `522773c`, pushed)
- Lane T, built: the client reads the shape by status, a 202 request body or the 200 envelope, and still refuses a
  foreign envelope; a 404 stays "done". The deletion-in-progress 409 is typed (`ChannelUserDeletionInProgress`) and
  matched on the whole sentence (a prefix match would add false positives).
- `/goodbye`: on a 202 the bot purges its rows, then says the account is locked now and erased later; on a 404 its
  farewell names no sign-in record; on a 200, today's flow.
- Lane T review fixes (copy): every pilot-facing sentence is true on both cores. A bare `/start` works at once; only an
  invite redemption waits for the deletion, so the plan's "`/start` works again once the deletion completes" was
  over-cautious. The abort message claims nothing about the platform side, and `/help`'s deletion clause holds on
  both cores.
- Lane T merged ahead of Task 19's api registration and lane C (ruling: it works against either core). The live bot
  was restarted on `8865fb3` on 2026-09-30, before lane C serves (Deploy/rollout 3).
- Lane C, built: the door answers 202 `{request_id, state, erase_after}` (UTC) through a new
  `ChannelUserDeletionRequest`, which replaced the 200 model in `models.py`, and deletes nothing.
- The teardown body is `channel_provisioning_service.teardown_channel_tenant`, called by step 6. Its preconditions
  moved into `tenant_service`, raising `TenantTeardownRefused`, which the tenant route maps to the same 503.
- Deviation: the provisioning POST answers the ruled 409 while ANY erasure request of the channel tenant's person is
  open, not only the teardown request; a plain request's frozen account must not be replayed either. It reads one
  per-user ledger row (`ledger.open_request_for`, review M-4).
- Lane C review ruling 3: a request can strand once its tenant is gone (a Future Improvement). The fix round logs
  `STRANDED_AFTER_TEARDOWN`, one fixed ERROR naming the owner CLI's `run` as the finisher, on every exit short of
  completed after the teardown. Task 19's api lane put the line in the CLI help.
- Lane C review fixes under the Global constraints: `delete_tenant` returns the tenant type, and a personal tenant's
  delete event carries `{"via": "api"}` with no name, its log line no name (M-2); the door's 500 no longer logs the
  channel user id (M-1). The service no longer imports router helpers (M-3). Three guard lists gained the new names.
- Lane C review concerns 3 (an account-less channel tenant) and 4 (the 409 for a platform-opened request) are Future
  Improvements, recorded at the P3 phase review.
- P3 phase review: a new bot log line ties the Telegram id to the request id (review C M-2, fixed in the bot batch).
  After lane C merges, the core batch makes step 6's partition-failure line name the Document Hub bucket and
  credential sweep (C M-1), logs a refused `/goodbye` at ERROR (C M-3), and re-checks a personal channel tenant before
  the delete (C M-4). The owner cannot erase a pilot who cannot send `/goodbye` (C I-1, owner question O2).

### Task 14: dashboard — erase action and status (P3, lane D, after Task 11 and Task 19's core half merge)
Owned: a new component under `components/features/settings/team/` (beside `EditTeamMemberDialog.tsx`); the team page
`app/(dashboard)/settings/department/team/page.tsx` (there is no per-member page); `lib/api/settings-api.ts`
additions; new `contracts/user-erasure-receipt.json` and its generator in `scripts/`; tests. Lane D also carries Task
19's operator-delete copy.
- [x] Shown only with `users_modify`; the confirmation states the window, what goes and stays (D1 in plain words) and
  cancel; a status + receipt view.
- [x] The receipt is identifier keys and integers only (C-17). The dashboard owns one sentence per key, from
  `contracts/user-erasure-receipt.json`, generated from core's declaration (the literal mapping in
  `user_erasure/ledger.py`, Task 11) by a script that refuses without a core checkout (the
  `automation-run-triggers.json` precedent, `scripts/generate-run-trigger-contract.mts`). An unknown key is rendered
  generically, never dropped.
- [x] The status list reads `GET /users/erasures` (Task 11), so a receipt stays reachable after the person's row is
  gone.
- [x] The doors answer three 503s (P3 plan review MI-13). `ERASURE_UNAVAILABLE` (no seams registered) is shown as
  unavailable. The retryable ones, `ACCOUNT_UNAVAILABLE` (Cognito) and the queued freeze's refusal (Task 11, m-6),
  are shown as "try again".
- [x] Proofs: unit tests asserting booleans (never retained jsdom nodes) — the action hidden without `users_modify`,
  a sentence for every contract key, an unknown key rendered generically, `ERASURE_UNAVAILABLE` shown as unavailable
  and a retryable 503 as "try again"; the contract guard compares the snapshot with core's declaration; `next lint`
  only. Mutant: show every 503 as unavailable.

#### Notes: Task 14 — the dashboard: DONE (dashboard `ue-t14` `0918191..6f9652f`, merged `3f5fa51`, pushed; 1 review, 1 fix round accepted on the diff)
- Built: Erase on the team page; a confirmation stating the window, what goes and stays, and the cancel; an Erasure
  requests panel with each request's state and receipt; `contracts/user-erasure-receipt.json` and
  `scripts/generate-user-erasure-receipt-contract.mts`. Task 19's operator-delete copy rode with it.
- Deviations: the three 503s are told apart by their `detail` sentence, because core sends no code; the contract also
  carries the window and the 503 sentences; `cleanup_warning` shows as a toast that stays until dismissed. Files
  beyond Owned: `hooks/settings/useUserErasures.ts`, the query keys, the telemetry events, the browser-signal
  contract, and five existing tests' pins.
- Review: 8 Minors, all fixed in one round.
- The harness refused the gate mutant (show the action without `users_modify`), so the gate is proved by a positive
  control, not a mutant.
- Known red: the analytics quality-contract test, pre-existing since Task 9. The closed states are copied by hand.
  Both are Future Improvements.
- The contract guard compares with core only where a core checkout sits beside the dashboard (its own words: "a
  developer check rather than a gate"). Task 17's pins make it a gate.
- The receipt wording table from the review waits for the owner's wording pass (owner question O9).
- P3 phase review, fixed in the dashboard batch: the operators list re-read after a refused delete (review B M-3); a
  repeat request over an `erasing` or `failed` request (D M-1); a `frozen` request past its date (D M-2); the receipt
  lines in the contract's order, not `jsonb`'s (D M-4, probe P-1 confirmed); copy for `owner_erasure_pending` (E M-4);
  the confirmation states the ruled keep rule, not "also belongs to another organisation". Erase on your own row is
  owner question O4.

### Task 15: copilot-mro — Phoenix user sweep (P4, lane M1)
Owned: `copilot_mro/app/services/agent_evaluation/phoenix_session_scrub.py`; new
`scripts/observability/scrub_erased_user_spans.py`; one call in `copilot_mro/app/services/user_erasure.py`; tests.
- [x] In the tenant's project, spans with `user.id` in the ids → their traces' spans deleted (the
  `pre_scheme_span_ids` pattern) after the per-chat session deletes; bounded, best-effort, counted; residue =
  `get_spans(user.id)`; the internal/golden project refused. Proofs:
  fake-client unit lane (live check in Task 18).
  The purge deletes the soft-deleted `chats` rows that `scrub_deleted_chat_sessions.py` draws its ids from, so a
  per-chat session the reap orphaned can no longer be replayed. The sweep runs inside `CopilotUserErasure.erase`
  BEFORE the purge, with the gathered chat ids: it retries each chat's session delete, then sweeps `user.id` spans.
  Verify the content-copy sessions' spans carry `user.id`; if not, the sweep needs the chat ids. Its residue joins the
  seam's composed residue under a disjoint key. The receipt's Phoenix 30 d bound is the backstop.
- [x] **Carry-ins from P3 (phase review E, 2026-09-30).**
  - A Phoenix leftover blocks completion (owner, 2026-10-01, O5: yes). As written: the copilot-mro seam raises an
    incomplete and never purges while any residue reads non-zero, and core retries six times, then daily. A failure the
    seam's own reads see (a Phoenix outage at the seam, a span still there at its last read) holds the erasure
    `erasing`, the person frozen and the Cognito account disabled, not deleted (step 4 comes after the seams). One
    first seen at core's residue step (step 5: a span ingested after the seam's last read, or a Phoenix that fails only
    there) holds the request `erasing` and the person frozen with the account already deleted (P4 review A M-1; pinned
    by `test_a_span_exported_after_the_seams_step_holds_the_residue_step_after_the_account_went`).
  - Orphans per source (Future Improvement "Core keeps orphans per source, but copilot-mro reports one integer"):
    this task builds its complete fix, since it edits the seam (controller ruling, 2026-10-01).
  - Starts after Task 20's F1 merges: both edit copilot-mro's user-erasure seam.
  - `USER_ERASURE_MAX_RUNTIME_SECONDS` (7200) was sized against one attempt at up to 5 s a Phoenix request. Re-check it
    against the per-chat retries and the span sweep this task adds.

#### Notes: Task 15 — the Phoenix user sweep: DONE (copilot-mro `ue-t15` `4894d0a1..1e4c2c79`, merged `a0d71393` with test-lane FI-4 after it, gate green but for the census reds, pushed `96ab4f6d`; one review)
- Built by two agents: the first built and proved it (`ee7cabbe..b910f501`) and retired past the context cap at the
  WSL crash; a continuation merged F1's fix round 1, fixed one test and one comment, and ran the hand-back.
- What landed:
  - the primitives in `phoenix_session_scrub.py`: `user_sweep_target` holds every id to `scrub_target`'s guard
    (internal tenant, foreign project, blank or golden-set id refused);
  - the seam retries each gathered chat's session delete, then sweeps the person's `user.id` spans (at most 200 an
    attempt, `PHOENIX_SPAN_LIMIT`), before the purge;
  - the residue `get_spans(user.id)` under its own key, failing closed (`INCOMPLETE_PHOENIX`) on any read failure;
  - orphans per source, as core keeps them, so a retry's 0 no longer overwrites an attempt's orphans;
  - the owner's replay `scripts/observability/scrub_erased_user_spans.py` (dry run by default, `--apply`);
  - the runtime cap of 7200 s is unchanged, with the arithmetic in the report.
- Content-copy spans carry `user.id` since 2026-09-17; the 09-14..09-17 copies carry `enduser.id` only and age out
  under Phoenix's 30-day retention (FI below).
- Task review (2026-10-01): APPROVE, 0 Critical, 0 Important, 5 Minor.
  - The fake matches `arize-phoenix-client` 3.5.0 in every signature, return shape, the `user.id` filter, the
    pagination and the 404 handling.
  - A read-only probe of the local Phoenix (20.8.0, auth on) answered 401 without a key; the real client then fails
    the residue closed.
  - The trial merge onto `5c2bf7f4` was clean, and the lanes passed on it with `PHOENIX_ENDPOINT` unset and dead
    alike.
  - M-1 (an HTTP error other than 404 is unproven as fail-closed) and M-2 (the session retry for a chat no reap ran
    for) are one test each; M-5 (= FI-E: the reap's WARNING logs `chat_id`) and FI-C (core's runtime-cap comment
    should count up to four Phoenix requests a chat) are one line each. All four ride in the P4 phase review's fix
    round (M-1, M-2, M-5 in part M; FI-C in part R; P4 review C M-3). M-3 is the deploy text below (step 6). M-4 is a
    Future Improvement (FI-H).
- Owner question O10: ruled (c) on 2026-10-01, "block unless declared"; built in the P4 fix round, part M (below,
  Owner / legal items).

### Task 16: iac — S3 noncurrent-version expiry and the Cognito erasure policy (P4, lane I)
Owned: `iac/s3.tf`, `iac/apprunner_iam.tf`; iac unit tests.
- [x] Bucket lifecycle: whole-bucket NoncurrentVersionExpiration 30 days, expired-delete-marker cleanup, abort
  incomplete multipart, depending on the versioning resource. A stand-alone `apprunner_cognito_user_erasure` policy:
  AdminDisableUser, AdminEnableUser, AdminUserGlobalSignOut, AdminDeleteUser, AdminGetUser, configured pool only.
- [x] Proofs: HCL block tests (`test_hcl_blocks.py` pattern) pin 30 days and the exact actions; `terraform fmt -check`
  / `validate` if available. NOT applied.
- **Built (2026-10-01):** iac `ue-t16` `ff1cb5c..70de725`, merged into iac `main` `34e2345` and pushed. NOT applied.
  - `s3.tf`: the copilot bucket's only lifecycle configuration (none existed anywhere): one enabled rule over the
    whole bucket (`filter {}`), noncurrent versions expire after 30 days, expired delete markers are removed,
    incomplete multipart uploads abort after 7 days (the plan gives no number), `depends_on` the bucket's versioning
    resource. No repo deletes S3 objects by version id, so every erasure delete leaves a noncurrent version for it.
  - `apprunner_iam.tf`: the stand-alone policy on the App Runner instance role, one Allow statement with exactly the
    five actions core's `cognito_accounts.py` calls, on `aws_cognito_user_pool.clients["default"].arn`.
  - Proofs: 9 HCL tests red before, the iac suite 335 passed; 25 mutants killed, plus the review's four survivors
    (a `count`/`for_each` on either resource, a `Condition` key, an inline-policy name shared on the role) killed by
    fix round 1. `terraform fmt -check` passes. `validate` against the pinned 6.x provider was thought not to run
    offline; a scratch copy validated against the cached 5.100.0 provider. It can: P4 review C's probe V-1 validated
    against 6.66.0 from `~/.claude/scratch/db-roles/tf/plugin-cache`, 0 warnings. CI's plan workflow is the real gate.
  - Deploy notes for the owner's apply (Deploy/rollout step 4): the rule covers the whole bucket, so any deleted or
    overwritten object, not only an erased person's, is unrecoverable after 30 days (no backups, D12); the first apply
    expires every existing noncurrent version older than 30 days at once. S3 rounds the 30 days to the next midnight
    UTC, deletes asynchronously and removes the delete marker (which carries the key) in a later pass: the receipt's
    "30 days" goes to the owner's wording pass (O9). A later `parse-sidecars/` expiry must be a second rule inside this
    configuration, never a second resource (one configuration per bucket; a test fails on a second).
  - Task 17: iac's 30 days against core's `s3_noncurrent_days` is a cross-repo pin.

### Task 17: planted-sentinel census + cross-repo pins (P5; three lanes: P, D, C)
Lanes (2026-10-01; P4 review C M-5):
- **P, the cross-repo pins** (api `ue-t17-pins` in `api-t17`; dashboard `ue-t17-pins` in `dashboard-t17`; copilot-mro
  `ue-t17-pins` in `copilot-mro-t17` for row 5h's constants). Owns `api/tests/unit/user_erasure/test_user_erasure_cross_repo_pins.py`
  and the dashboard receipt guard's gate. Built: 13 pins (api `edab081`, `85ac132`; dashboard `644ceaf`); task review
  0C/2I/7M. Its fix round adds: the POC host's Loki and Tempo retention (I-1); `cloudwatch_days` against every log
  group's retention (I-2); core's Cognito calls against iac's erasure policy, equal both ways; row 5h; the request
  response's fields against the dashboard's `UserErasure` (review B M-3); the CLI help's timing, the purge command's
  argument and the bot README's tenant name (review B M-4); one missing sibling fails only its own pin (M-1); the
  finishers bound by name (M-2). Its narrowings, ruled right by the review: run reasons are pinned by category, not
  literally; shift-optimizer's kinds are a subset; row 7 pins nothing (no reader outside core; `via` is a change
  key); the iac row reads the checkout like every other pin (the iac primary is on `main`). Rows beyond the table:
  F2's runbooks (help ↔ bot, README ↔ CLI) and the analytics contract.
- **D, the drift shape list** (core, copilot-mro, shift-optimizer; `ue-t17-drift`). Owns the three drift guards and
  the placements they force. The list as ruled (controller, 2026-10-01): today's shapes plus `assignee`, `approver`,
  `requester`, `owner` (whole or a `_`-delimited part), `user_name`, `username`, `creator`; one list, shared or
  pinned equal by lane P; the jsonb rule (every json/jsonb column of a relation holding a placed column is itself
  placed, `automation_runs.params` first); new placements by R-PLACEMENTS and D9; a column that fits no rule is placed
  provisionally `keep` with "owner question: …" and listed for the owner.
  Built, merged and pushed 2026-10-01 (core `3092d78`, copilot-mro `94d0b59f`, shift-optimizer `70a7a39`; gate green
  but the census family):
  - 18 shapes, matched as whole names;
  - the jsonb rule, read literally (a relation holding any placement, keep included);
  - 64 new placements (core 15, copilot-mro 43, shift-optimizer 6), with no statement changed;
  - copilot-mro's two index checks run the real writer code.

  Task review: MERGE-READY, 0C/0I/6M. Its fix round runs in two parts:
  - **Part B** (`ue-t17d-fix-b`): the `no-person` kind (below, under C), m-1 (copilot-mro's kinds held to its
    statements, as core's are), m-2 (one reason's text) and m-5 (the type reading proven by plants).
  - **Part A** (`ue-t17d-fix-a`, test-only): m-3 and m-4 (the index readers read every upsert path, and what the
    Document Hub indexer writes as well as what it declares), m-6 (the readers' restores proven), and lane P's row
    holding the three `DRIFT_SHAPES`/`DOCUMENT_TYPES`/`DECOYS` literals equal.

    **Merged and pushed (2026-10-02):** copilot-mro `0a3771a7`, api `728d0ec`. The memory reader runs four paths of
    the upsert (insert, update, embed, and the reuse path that the erasure's own re-upsert takes) under a check that
    fails if the upsert stops taking one. The Document Hub reader adds the keys `_chunk_properties` writes; today
    those equal the declared 22. 18 mutants were killed. The full gate was green apart from the census family and one
    order-dependent red in part D's door-check test, recorded with D2.
- **C, the census** (`api/tests/integration/user_erasure/`, where F2's db test already lives), after D and after the
  P4 fix round's part M: the first two checkboxes below. Besides the seeds they list:
  - a P sentinel under a deleted operator (rows, plus a chunk in a kept pair partition), with a Weaviate fake that
    answers the presence read;
  - Phoenix spans for P, the sibling and the second tenant under the SAME id (in its own project);
  - one recording Phoenix fake injected at the seam's door, reusing copilot-mro's
    `tests/unit/user_erasure/_fake_phoenix.py` (matched to client 3.5.0): the api's `main` exports `api/.env`'s keys
    into the test process, so an un-faked census builds a real client;
  - the S3 fake answering both `s3_client` and `get_client()`; the memory index's presence cache reset; the Document
    Hub fake index named as one of `mt_collection_names()` (review A's P5 notes);
  - both wirings, and the request's `erase_after` in the past (the carry-ins below);
  - the I-2 probe: plant a surviving Phoenix copy, run the evaluation store after the erasure, and see nothing
    derived.
  - Controller ruling (2026-10-01; lane D review concern 7): a `keep` today means "the person's id may stay here", but
    most of lane D's jsonb keeps say the column names no person. The census must not read those as allowed places.
    - The vocabulary gains a kind, `no-person`, in all three erased-user lines. It is a kind rather than a field, so
      every placement must choose, and the tuple lines keep their shape. It is built in lane D's fix round, part B.
    - `keep` then means only that the person's ID may remain by ruling: D9 provenance and the ledger's ids.
    - `no-person` is a column where no writer puts the person's ID: one a guard rule forced into the line, or kept
      text such as D1 knowledge and D10 comments. The erasure treats it as it treats `keep`. Words are not part of
      the kind; the census's seeding handles them. P's sentinel goes where the erasure removes, and K's where text is
      kept (D1, D10). (Refined 2026-10-02 at part B's hand-back. Part B's review then moved the five word-only keeps
      to `no-person`: comment text and tags, an airline's details, memory payloads and the level-2 safe summary.)
    - The census asserts the person's ids ABSENT from every `no-person` placement, and a planted id there turns it
      red.

    Cost if wrong: one kind across three lines.
- [ ] Seed through the REAL writers into `copilot_mro_test` a personal sentinel (P) and a knowledge sentinel (K) in
  every store of Tasks 6–9 (turns incl. a chat deleted beforehand, feedback, share, preference, curated example, tenant
  fact, correction, signal, finding, eval explanation, agent state, the three LLM relations, automation + run, comment
  + thumbs + a sibling's mention, notifications both ways, product event, invitation, private + shared DocHub rows, a
  data-discovery source); a sibling user; a second tenant holding rows under the SAME user id. Run the real
  orchestrator (fake Cognito, recording fakes for S3/Weaviate/Phoenix).
- [ ] Registry-derived census over every core + copilot-mro relation (owner connection, test DB only): P in no
  text/varchar/jsonb column; the ids only in declared keep places; K exactly in its kept rows, with no id; sibling and
  second-tenant rows byte-identical (full-row comparison); rerun changes 0 rows; the fakes saw every expected delete.
- [ ] Cross-repo pins (checkouts pinned): the three `deleted-user` literals equal; each receipt bound ≥ its configured
  retention (iac, Loki/Tempo configs, Phoenix); shift-optimizer's two unit-file copies of the ledger-key literal equal
  core's `IDENTIFIER_PATTERN`; rule the estate-wide drift shape list (`assignee`, `approver`, `requester`, `owner`,
  `user_name`, `creator`, and person-bearing jsonb such as `automation_runs.params`) and apply it in all three repos.
  Proofs: remove one placement's statement per repo → census red.
- [ ] The wire contracts P3 created (P3 phase review E I-1). Each is a literal in two repos, pinned today only against
  its own copy. One pin per row, against pinned checkouts; a pin may live beside either side, and Task 17 owns that
  test file.

  | Contract | One side | The other side | The pin compares |
  |---|---|---|---|
  | The deletion-in-progress 409 sentence | core `core/resources/channel_provisioning/channel_provisioning_endpoints.py` (`_DELETION_IN_PROGRESS_DETAIL`) | telegram-bot `flynapse_client/provisioning.py` (`DELETION_IN_PROGRESS_DETAIL`) | the two sentences are equal, and differ from the namespace-conflict 409's |
  | The channel door's 202 body | core `core/resources/channel_provisioning/models.py` (`ChannelUserDeletionRequest`) | telegram-bot `flynapse_client/provisioning.py` (`_erasure_request`) | the key set is exactly `request_id`, `state`, `erase_after`; a body core's model serialises parses in the bot, `erase_after` with its offset |
  | The dashboard's receipt contract | core `core/resources/user_erasure/ledger.py` (`RECEIPT_KEYS`) and `erasure_endpoints.py` (the window, the three 503 sentences) | dashboard `contracts/user-erasure-receipt.json` | the dashboard's own contract guard, run with `USER_ERASURE_CONTRACT_REQUIRE_BACKEND=1`, so a missing core checkout fails instead of skipping |
  | The operator-delete response | core `core/resources/identity/operator_endpoints.py` (the 200 body) | dashboard `lib/api/settings-api.ts` (`OperatorDeleteResult`) | the field names, and which may be null (`partition_warning`, `cleanup_warning`) |
  | The stranded-request line and the command it names | core `core/resources/user_erasure/service.py` (`STRANDED_AFTER_TEARDOWN`) | api `flynapse_api/user_erasure_cli.py` (its help's log lines) | the help quotes the line's fixed text, read from core's constant; the command the line names parses under the CLI's own arguments |
  | The finishers core's logs name | core `channel_provisioning/services/channel_provisioning_service.py` (`_STORAGE_LEFT`), `tenants/tenant_endpoints.py` and `identity/operator_endpoints.py` (their warnings) | copilot-mro `scripts/delete_unentitled_partition.py`, `scripts/delete_orphaned_operator_rows.py`, and the removals `_STORAGE_LEFT` names (`operator_partitions.remove_operator_partitions`, `tenant_teardown.remove_tenant_storage`) | every script path named exists, every flag named (`--purged-tenant`) is one its parser accepts, and every function named is importable with the arguments the line gives it |
  | The run reason `owner_erasure_pending` | api `flynapse_api/automations/identity.py` (`OWNER_ERASURE_PENDING`) and `executor.py` (the reasons a run records) | dashboard `components/features/automations/runOutcomeCopy.ts` (`RUN_REASON_COPY`) | every reason the executor can record has a row in the copy |
  | Task 11b's bounds and core's delay | core `core/resources/user_erasure/ledger.py` (`IMMEDIATE_ERASURE_DELAY`) | copilot-mro `copilot_mro/app/services/erasure_delay_bounds.py` and its pin, `tests/unit/user_erasure/test_erasure_delay_bounds.py` | the delay the bounds were judged against (30 minutes) equals core's, so any change to it goes red for a re-judgement (today's pin holds for every delay); absolute floors hold: the turn deadline at least a stated minimum, and the margin at least the sum of the stream block save's wait, the statement ceiling, the freeze's commit gap (about 75 s), the S3 client's timeouts and a clock-skew allowance. The bounds module's docstring says what the pin judges |

  Proofs: change one side of each row alone → its pin red.
- [ ] **Carry-ins from P3 (phase review E, 2026-09-30).** An immediate request now waits `IMMEDIATE_ERASURE_DELAY`, so
  the census builds its request with `erase_after` in the past. The orchestrator runs with BOTH
  `partition_wiring.wire()` and `user_erasure_wiring.wire()`: step 6 and the operator row seams need the hooks.

### Task 18: live end-to-end on the dev stack (P5, controller-run on the owner's go)
Owned: new `copilot-mro/tests/e2e/user_erasure/user_erasure_e2e.py` (collects zero tests; layout exemption with reason).
- [ ] A throwaway dev-pool user in a dev tenant: real turns with uploads + a DocHub upload → immediate erasure →
  no current S3 objects under the user prefixes (noncurrent versions reported until the lifecycle applies), Weaviate
  filter counts 0, Phoenix `get_spans(user.id)` empty, Cognito admin-get → not found, receipt present. Dev tenants
  only; never the golden/internal project. Read the memory index after the erasure (Task 6 clears `user_id` by PATCH
  with a null; the fakes cannot prove the server unsets it), and check that a re-keyed DocHub chunk kept its vector
  (T7 FI-3).
- [ ] **Carry-ins from P3 (phase review E, 2026-09-30).** An immediate erasure runs 30 minutes after the freeze: on dev,
  where the scheduler runs `embedded`, the freeze's own one-shot serves it; elsewhere, the CLI's `run` once
  `erase_after` has passed.
- [ ] **Three more live legs (owner, 2026-10-01, O7: record all three for the live testing).**
  - The dashboard door: an admin requests, cancels, requests again and completes an erasure, then reads the receipt on
    the page. The tenant door opens only a windowed (7-day) request (`erasure_endpoints.py`), so "completes" is the
    platform CLI's `request --immediate` over it (F3's escalation event, proven live too), then the 30 minutes (P4
    review C I-3).
  - The channel door: a test pilot sends `/goodbye`; the bot, core and storage are checked end to end.
  - The operator delete: delete an operator; its rows, Document Hub objects and partitions are gone.
- [ ] **A fifth live leg: the owner path (owner, 2026-10-01, P4 review B OQ-B1).** A throwaway test pilot erased the way
  the owner erases a pilot who cannot send `/goodbye`: `user_erasure_cli request --channel-teardown --tenant <t>
  --user <u> --rtbf` on the api, then `python -m telegram_bot.purge_account` on the bot. The ledger and every view say
  legal, the bot's `tg_*` rows are gone, and storage is clean.
- [ ] **Prerequisites (owner; one list, P4 review C I-3).** The script's `prereqs` step checks each it can and names
  the first missing one.
  - The P4 phase review's fix round has landed: before it, the owner CLI and a worker do not see a Phoenix named only
    in `api/.env` (review A I-1), and the evaluation gate reads a purged chat as live (I-2).
  - Phoenix: both keys, the key allowed to delete spans and sessions, visible to every process that runs an erasure
    (dev's `api/.env` has both: added and verified 2026-10-01, values never read); the dev collector's Phoenix fragment
    on, or no content span reaches Phoenix.
  - The api's grant-pool credentials (`POSTGRES_GRANT_USER` / `POSTGRES_GRANT_PASSWORD`).
  - Where the erasure runs: the api's embedded scheduler, or the CLI run from `api/` (or with
    `ENV_FILE=api/.env`). Since the P4 fix round, copilot-mro's settings read the Phoenix keys: the process
    environment first, then `ENV_FILE`, then `<cwd>/.env`. A CLI run elsewhere names no Phoenix, and its erasure
    holds under O10.
  - The api runs the merged code: the dev container rebuilt (the owner's db-roles 4c), or the api run from the
    checkouts.
  - Dev `copilot_mro` migrated and provisioned (Deploy/rollout 1), and Weaviate's schema present (the restart trap).
  - Cognito: a throwaway dev-pool user per leg, and credentials allowed `AdminGetUser`. S3: credentials to list the
    user prefixes.
  - The dashboard leg: an admin who is not the person (F4), the dashboard, and the platform CLI for the escalation.
  - The channel leg: a test Telegram account the owner controls, through the live bot, never a real pilot.
  - The operator leg: a throwaway operator with rows, Document Hub objects and pair partitions.
  - Dev tenants only; never the internal or golden project.
- [ ] **Every "gone" check reads non-zero first (P4 review C I-3, review A's P5 notes).** Before each erasure, the leg
  reads a non-zero count in every store it later checks: spans by `user.id`, one Phoenix session per chat, S3 objects
  under the user prefixes, Weaviate filter counts, the rows. A store that reads zero before fails the leg as vacuous.
  After the erasure, besides `get_spans(user.id)` empty: `sessions.get(<chat id>)` answers 404 for every chat (an
  empty span read passes even when every session delete was refused), every `chat_<digest>` orphan source in the
  ledger reads 0, and the returned span shape carries `user.id` in its attributes (Task 15 FI-F's confirmation).

### Task 19: core + copilot-mro — deleting an operator deletes its own rows (P3; lanes C-b, M1, A, D; owner question 4)
Ruled by the owner on 2026-09-29: owner question 4 (the root fix), then Task 19 Q1–Q6, all yes.
- Its core half merges before Task 11, so the erasure receipt carries no orphan-operator key (C-18).
- Its copilot-mro half starts after the core half merges, and merges before Task 12; the owner runs its orphan script
  on dev before Task 12 merges (Deploy/rollout step 2).
- Its api registration comes after Task 12 and the copilot-mro half.
- Between the core half's merge and the api registration, every `DELETE /operators/{id}` on the dev stack answers
  503, because the row seams are not registered yet. That is accepted in dev (P3 plan review MI-9).

Owned:
- core (lane C-b, `core-erase-b`): `core/core/resources/identity/operator_lifecycle.py` (the row-seam registry); new
  `core/core/resources/identity/operator_copies.py` (core's own step, both entries);
  `core/core/resources/identity/services/operator_service.py` (the step on the delete's cursor, counts in the event);
  `core/core/resources/identity/operator_endpoints.py` (order, refusal, response fields); tests in
  `core/tests/{unit,db,api}/identity/`, plus `core/tests/api/authorization/test_operator_crud.py`, whose existing
  operator-delete tests answer 503 once the row-seam gate lands (P3 plan review MI-8), and
  `core/tests/unit/db/test_operator_service.py`, the service's own unit tests (added after the fact, Task 19 core
  review).
- copilot-mro (lane M1): new `copilot_mro/app/services/operator_teardown.py` (erase + residue); the Document Hub and
  memory-index primitives it reuses (a public per-document purge in `document_hub/cleanup.py` if none fits); new
  `scripts/delete_orphaned_operator_rows.py`; the scope-guard approval for the new production files; tests in
  `tests/{unit,db}/operator_teardown/`. Document Hub's operator check (controller ruling on the plan fix):
  `copilot_mro/app/services/document_hub/indexing.py` (the check before `ensure_tenant`) and
  `copilot_mro/app/services/document_hub/processing.py` (the attempt it stops ends abandoned), with their tests in
  `tests/unit/document_hub/`. Also (P3 plan review IM-7):
  - a new shared helper module in `copilot-mro/scripts/` for the superuser/`BYPASSRLS` assertion and the refusal exit
    codes. `scripts/` is not a package, and the assertion is a private function of one script today;
  - `scripts/delete_unentitled_partition.py`, whose `_assert_owner_bypasses_rls` and exit codes move into that module
    (moved, not copied). The module's name must not collide with a core `scripts/` module (the `_workspace` collision
    behind the copilot-mro full-suite collection errors).
- api (lane A, after Task 12; C-19): the registration in `flynapse_api/partition_wiring.py`, all-or-nothing with the
  partition hooks; one api test. Task 12's kind calls `partition_wiring.wire()` first, so a failed
  `operator_teardown` import also leaves the `user_erasure` kind unregistered (accepted, C-19).
- dashboard (lane D, with Task 14; C-21): `components/features/settings/operators/operatorDelete.ts`;
  `hooks/settings/useOperators.ts` (`operatorDeletedMessage` reads the delete's warning) and
  `lib/api/settings-api.ts` (`OperatorDeleteResult`), for `cleanup_warning` (P3 plan review MI-8).

Why: `DELETE /operators/{id}` deletes the `operators` row, its `user_operators` grants (FK cascade) and, through the
partition hook, the pair partition on every operator-keyed Weaviate collection. Every row of every `tenant+operator`
relation stays, and so do the `MemoryItemMT` documents of the operator's memory items and the S3 objects and parse
sidecars of its Document Hub documents. RLS reads such a row only when its `operator_id` is in the bound set, and no
binding the product builds names a deleted operator. An explicit `db_tenancy(tenant, (operator,))` on the app pool does
reach them: a superuser is needed only to FIND orphan pairs (every table is `FORCE ROW LEVEL SECURITY`), never to
delete them. So one clean-up path serves the route and the orphan script (P3 prep, evidence 1–2).

- [x] **The placements (Q1: every operator-keyed table, derived from the registries).** 57 `tenant+operator` base
  tables (core 2, copilot-mro 55), plus core's `user_operators`, which the FK already cascades, and one view. The
  registries are core's `ALL_TABLES` and copilot-mro's `get_all_postgres_table_definitions()`, which holds none of
  core's tables; copilot-mro's modules are under `copilot_mro/app/db/postgres_table_definitions_modules/`. Every
  relation below is orphaned by an operator delete today.

  | Repo | Relations | Registry module | Task 19 deletes them by |
  |---|---|---|---|
  | core | `notifications`, `notification_subscriptions` | `core/db/table_definitions.py` | core's step |
  | core | `user_operators` | `core/db/table_definitions.py` | the FK cascade, as today |
  | copilot-mro | `document_hub_documents` | `document_hub.py` | the seam: both S3 prefixes and the sidecars, then the row; chunks go with the partition |
  | copilot-mro | `memory_items`, `memory_item_events` (operator-scoped rows only, e.g. `tenant_fact`) | `memory.py` | the seam: the `MemoryItemMT` documents by id, then the rows |
  | copilot-mro | `chunks` | `chunks.py` | the seam |
  | copilot-mro | `mro_documents`, `pilot_documents`, `crew_documents` | `documents.py` (helper-built) | the seam |
  | copilot-mro | `crew_manual_sections` | `crew.py` | the seam |
  | copilot-mro | `fleet` | `fleet.py` | the seam |
  | copilot-mro | `ad_compliance_status`, `ad_fleet_applicability` | `ad_compliance.py`, `ad_fleet_applicability.py` | the seam |
  | copilot-mro | `work_orders`, `work_order_parts`, `work_order_defects`, `work_order_actions`, `work_order_references` | `amos_work_orders.py` | the seam, children first (FKs) |
  | copilot-mro | `own_inventory_availability`, `flight_schedule`, `fleet_component_donors` | `aog.py` | the seam |
  | copilot-mro | `part_master`, `part_families`, `stock_balance`, `serial_tracking`, `repair_orders`, `consumption_history`, `planning_parameters`, `part_financials` | `inventory.py` | the seam |
  | copilot-mro | `mel_items`, `manual_task_cards`, `manual_tasks`, `manual_subtasks`, `manual_task_references`, `manual_task_location_zones`, `manual_task_tools_equipment`, `manual_task_consumable_materials`, `manual_task_expendables_parts`, `manual_task_access_panels`, `ipc_parts`, `ifim_tasks`, `ifim_fault_codes`, `ifim_mmsg_codes`, `tn_documents`, `ftd_documents` | `manual.py` | the seam |
  | copilot-mro | `production_aircraft_status`, `production_ground_windows`, `production_candidate_tasks`, `production_staged_parts` | `production_planning.py` (helper-built) | the seam |
  | copilot-mro | `production_shift_roster` (a view) | `production_planning.py` | nothing: a view holds no rows (excluded) |
  | copilot-mro | `wdm_nodes`, `wdm_edges`, `wdm_source_docs`, `wdm_diagram_index`, `wdm_mates`, `wdm_boundaries`, `wdm_lookups` | `wdm.py` | the seam |
  | copilot-mro | `engineer_authorizations` | `workforce.py` | the seam |
  | shift-optimizer | none: every relation is `tenant` class | `shift_optimizer/app/db/row_tenancy.py` | — |
  | telegram-bot | none ("operator" there is the bot's human operator) | — | — |
  | api | none (no registry of its own) | — | — |

  Outside Postgres: the pair partitions on the six operator-keyed collections (`ManualsMT`, `AmosWorkOrdersMT`,
  `PilotManualsMT`, `CrewManualsMT`, `LocationMT`, `DocumentHubDocuments`), already removed by the hook; the
  `MemoryItemMT` documents of the operator's memory items; the S3 objects and parse sidecars of its Document Hub
  documents. No S3 prefix is keyed by operator. Kept as history in tenant-visible rows: `automation_runs.operator_ids`,
  and the `operator_id` in `ad_materialize`'s `automations.params` / `automation_runs.params`. Legacy non-MT Weaviate
  collections hold every operator undivided and have no partition to remove.
- [x] **The seam (C-20).** `operator_lifecycle` gains the operator-axis twin of the erasure registry:
  - `REQUIRED_OPERATOR_ROW_SEAMS = ("copilot_mro",)`, declared in core; a frozen `OperatorRowSeam(erase, residue)`.
  - `erase(tenant_id, operator_id)` answers `{placement: rows or objects removed}`; `residue(tenant_id, operator_id)`
    answers `{placement: rows still held}`, read-only. Placement keys fullmatch the ledger identifier pattern
    (`<table>` for a relation, a snake name otherwise).
  - One residue key is declared in core beside `REQUIRED_OPERATOR_ROW_SEAMS`: `held_documents`, the rows a seam keeps
    on purpose while a live attempt may still write them (P3 plan review IM-8). The route reads it at step 6.
  - `register_operator_row_seams(mapping)` installs exactly the declared names with both halves callable, or raises
    `OperatorRowSeamsUnavailable(RuntimeError)` and installs nothing. `operator_row_seams_registered()` is the
    route's pre-write check; `ordered_operator_row_seams()` raises when unregistered; `reset_operator_row_seams()` is
    for tests.
  - `remove_partitions` is unchanged, so the tenant-delete paths (the channel door, `DELETE /tenants`) do not start
    sweeping rows operator by operator; the tenant axis leaves that to `--purged-tenant`.
- [x] **Core's own step (not a seam).** `operator_copies` derives its relations from core's registry (`tenancy ==
  tenant+operator`: `notifications`, `notification_subscriptions` today) and deletes the operator's rows — never the
  `__ALL__` rows — on the delete transaction's own cursor, rebound to `(tenant, (operator,))`. Its residue reads the
  same relations under the same binding, read-only.
  - Two entries share the statements (P3 plan review IM-7): the step on a caller's cursor (the route's delete
    transaction), and a self-bound entry for one pair that opens its own `(tenant, (operator,))`-bound transaction
    (the orphan script: an orphan pair has no `operators` row and no delete transaction). Both live in
    `operator_copies.py`, which keeps lanes C and C-b disjoint.
- [x] **copilot-mro's seam.** `operator_teardown.erase_operator_data` / `operator_data_residue`:
  - The relation set is derived from the registry: every `tenant+operator` definition that is not a view (55 today),
    ordered children-first by the registry's foreign keys (the work-order family). Nothing is listed by hand; an
    exclusion needs a named reason in one declared tuple (empty today).
  - Every statement binds `db_tenancy(tenant, (operator,))`, keys on `tenant_id` AND `operator_id`, never matches
    `__ALL__`, and deletes in pages (Q2): each page is its own transaction under the pool's statement ceiling, and
    each page is counted as it commits.
  - Links last (R-LINKS-LAST). Document Hub: for every document row of the operator (any scope, any deleted state),
    its objects under both prefixes and its parse sidecars are deleted, then the row; chunks go with the pair
    partition. Both prefixes means the raw backup too (`document_object_prefixes`; Q5: no row remains to restore a
    backup to, the D7 precedent). A sidecar's content goes only when no other alias references it (Task 7's rule). A
    document whose attempt may still be live (DocHub's `abandonment_cutoff`) is held: its row stays, it is counted as
    an orphan, and the residue reports it under `held_documents`, not under `document_hub_documents` (P3 plan review
    IM-8).
  - The seam makes no Weaviate call for a Document Hub row: its chunks go with the pair partition. So a held row can
    be cleared later, after the partition is gone, without error.
  - Memory: the `MemoryItemMT` documents of the operator's memory items are deleted by id (the collection has no
    operator property), then the items and their events.
  - The residue counts each relation's rows for the pair; it is zero only when every link is gone.
- [x] **Document Hub writes nothing for a deleted operator (controller ruling on the plan fix).** DocHub's indexing
  calls `ensure_tenant` before every vector write, so a held attempt that completes after the route removed the
  partitions would re-create its pair partition.
  - Before `ensure_tenant` and the vector write, the indexing checks that the pair still has an `operators` row.
  - When it does not, the attempt ends as abandoned (`processing_abandoned`, DocHub's own terminal code) and writes
    nothing: no partition, no vector. That code is not one of the failures that clean vectors, so the ending makes no
    Weaviate call. The row stays held for the orphan script.
- [x] **The route's order** (`DELETE /operators/{id}`; Q2: the clean-up runs inside the request):
  1. Admin gate; 503 unless the partition hooks AND the row seams are registered (one fixed sentence under 300
     characters, the existing wire-sweep bound); name echo (409).
  2. Pre-pass: each registered seam's `erase`. A failure answers a fixed 5xx and changes nothing in core: the
     operator still exists, so the same request can be retried.
  3. The delete transaction: row lock, grant count, core's step, `DELETE FROM operators`, the event with
     `grants_cascaded` and the per-placement counts — one commit.
  4. `declare_cache_invalidation(full_tenant)`, where it is today.
  5. Post-pass: each seam's `erase` again (rows written in the gap by holders of the now-cascaded grants), then every
     residue (core's and the seams').
  6. The residue decides (P3 plan review IM-8, option (a)):
     - all zero → `remove_partitions`, and the response carries the counts;
     - non-zero only under `held_documents` → `remove_partitions` still runs, the held rows stay for the finisher, and
       the 200 carries the fixed `cleanup_warning`;
     - any other non-zero residue, or a post-pass failure → the partitions are LEFT, so the boot check refuses loudly
       (the `tenant_teardown` precedent), and the 200 carries the fixed `cleanup_warning`.

     Every warning's log names `scripts/delete_orphaned_operator_rows.py` as the finisher.
     - Why held rows do not keep the partitions: the boot check refuses any partition no operator row names
       (`weaviate_boot_check`), and a hold is DocHub's 30-minute `abandonment_cutoff`. Keeping the old rule would turn
       any operator with an upload in the last 30 minutes into a stack that cannot restart.
     - Who finishes held rows: not Document Hub's own maintenance sweep, which binds the tenant's current roster
       (`operator_ids_for_tenant`) and never sees a deleted operator's rows. The orphan script is the net: once the
       hold lapses it clears them through the row seam, and `remove_partitions` on a pair already removed is a no-op
       (`operator_partitions`).
     - A held attempt that completes after the removal: Document Hub's operator check stops it before it re-creates
       its pair partition. Only the race between the check and the write remains, and the orphan script is its net:
       the next boot refuses until the script runs, and its census counts that partition and removes it with the rows.
- [x] **How residue proves the delete.** Zero on every placement of every registered seam plus core's step, read
  under the one binding that reaches the operator's rows. The placement set is derived from the registries, so a new
  `tenant+operator` table is in the erase and the residue the day it is declared. The drift guard asserts the derived
  set equals the registry's, and fails on a stale exclusion.
- [x] **The orphan census and clean-up (Q3, Q4, Q6).** `copilot-mro/scripts/delete_orphaned_operator_rows.py`, run by
  the owner from the api environment: once per database before the erasure routes serve (Deploy/rollout), then kept
  as the route's finisher.
  - Discovery as the owner, deletion through the registered clean-up (Q4). It connects twice: `--user postgres` for
    the census, reusing (not copying) the superuser/`BYPASSRLS` assertion and the refusal exit codes of
    `delete_unentitled_partition.py`; and the app pool for the clean-up. A raw superuser `DELETE` would strand the
    Document Hub objects, sidecars and memory index documents.
  - Databases (Q3): `copilot_mro_test` and `copilot_mro` only. It refuses any other database, and an app pool whose
    database is not `--database`.
  - Census (catalog-derived, like `_tenanted_tables`): every base table with both `tenant_id` and `operator_id`; rows
    whose `operator_id <> '__ALL__'` and whose `(tenant_id, operator_id)` has no `operators` row, split by whether the
    tenant still exists (a gone tenant is `--purged-tenant`'s, reported and never touched here). Also counted: the
    `MemoryItemMT` documents of orphan memory rows, the Document Hub objects under orphan document rows, and the pair
    partitions of orphan pairs.
  - Dry run by default: per-table counts, per-pair totals and the grand total. Nothing is written.
  - `--execute` runs only with `--expect-rows N`, where N equals the grand total of the census it runs first, so the
    run deletes exactly what the owner read; any other N is refused. The script registers the row seams AND the
    operator partition hooks itself, from copilot-mro's own modules, as the api's wiring does: `remove_partitions`
    raises when the hooks are unregistered (P3 plan review IM-7). For each orphan pair it re-checks that no
    `operators` row exists (an operator re-created under the same id is skipped), runs core's self-bound step and
    every row seam bound to the pair, then the residue, then `remove_partitions` when it reads zero.
  - Audit (Q6): one `authorization_events` row per pair it clears (actor `owner-script`, via `script`, counts only).
  - It re-runs the census and prints before and after per table. Exit 0 clean, 2 refused, 1 anything left.
- [x] **Proofs.**
  - core unit: the row-seam registry is fail-closed (unregistered, partial, a non-callable half); the route answers
    503 before any write when either registry is missing; the route order by a spy (pre-pass → transaction → eviction
    → post-pass → residue → partitions); partitions skipped when any residue other than `held_documents` is non-zero,
    and removed with `cleanup_warning` when only `held_documents` is; core's relation set equals its registry's
    `tenant+operator` set.
  - core db (`copilot_mro_test`): an operator holding a notification and a subscription, beside an `__ALL__`
    notification, a sibling operator's rows and a second tenant using the same operator id: the operator's rows go,
    the rest is byte-identical, the event carries the counts, a rerun of the step changes 0 rows; the self-bound entry
    clears the same rows for a pair with no `operators` row.
  - copilot-mro unit: the derived set equals the registry's non-view `tenant+operator` definitions (a planted table
    joins it, the view stays out); children-first order from the FKs; Document Hub objects under both prefixes before
    the row (a failing object delete keeps the row); memory index documents before the rows; a live attempt is held
    and read by the residue under `held_documents`; an indexing attempt whose pair has no `operators` row ends
    `processing_abandoned`, and the fake Weaviate sees no `ensure_tenant`, no write and no delete.
  - copilot-mro db: one row per relation family for operator X (a private and a shared Document Hub document, a
    memory item and event, a work order with a defect and an action, a manual task, a fleet row), beside operator Y,
    `__ALL__` rows and a second tenant with the same operator id: X reads zero, the rest is byte-identical, a rerun
    changes 0 rows.
  - script db: a planted orphan (rows for an operator id with no `operators` row) is counted per table by the dry
    run, which deletes nothing; `--execute` with the dry run's total leaves zero, removes the cleared pair's
    partitions and writes one audit event per pair; a live operator's rows are never counted; the app role for the
    census, a database off the allowlist, a pool/`--database` mismatch and a missing or wrong `--expect-rows` are each
    refused.
  - script db, the held-row finisher (IM-8): a held Document Hub row of an already-deleted operator whose pair
    partition is gone is cleared by `--execute` once its hold lapses, without error (the fake Weaviate raises on a
    missing partition).
  - api: `wire()` registers the row seam with the partition hooks, all or nothing.
  - dashboard: the confirmation says the delete removes all of the operator's data in this tenant ("…and deletes all
    of its data in this tenant", replacing "deletes its indexed content"), and a `cleanup_warning` is shown
    (booleans; `next lint`).
- [x] **Mutants** (each killed by the file named): drop the `operator_id` predicate from one relation's delete
  (copilot-mro db, in a tenant whose only operator is X, or on a `tenant_grain_sentinel` table: the `__ALL__` rows
  go. Under the `(t, (X,))` binding row security never lets a sibling Y's rows be deleted, so "Y's rows go" cannot be
  observed; Task 19 core review, claim 5); match `__ALL__` rows (core db: the tenant-wide notification goes); add a relation to
  the exclusion tuple with no reason (drift guard); remove partitions before the residue check (core route spy);
  delete a document row before its objects (copilot-mro unit); keep the raw backup prefix (copilot-mro unit); skip
  the memory index delete (copilot-mro unit); register skips instead of raising (core unit); census without the `NOT
  EXISTS operators` predicate (script db: the live operator's rows counted); accept the app role for the census
  (script db); execute without checking `--expect-rows` (script db); skip the audit event (script db); the self-bound
  entry binds the tenant alone (core db: the pair's rows are invisible, so none go); the script registers the row
  seams only (script db: the pair's partitions stay); remove the partitions when a residue other than
  `held_documents` is non-zero (core route spy); the per-document purge also deletes the document's vectors (script
  db, the held-row finisher: the missing partition raises); skip Document Hub's operator check (copilot-mro unit: the
  held attempt re-creates the partition).
- [x] **Receipt.** No erasure receipt key for orphan operators (C-18): Task 19 lands in P3 before any live erasure,
  and the rollout clears existing orphans before the erasure routes serve.
  - The P3 phase review refuted the premise (review B I-1; probe P-B1 confirmed it on `copilot_mro_test`). Task 19
    leaves orphan rows by design: held Document Hub rows, a failed post-pass, and the residue's eviction window. A user
    erasure binds the tenant's live roster, so it can neither erase nor count its person's rows under a deleted
    operator, and it completes with residue 0. Owner question O1 is open.

#### Notes: Task 19 — deleting an operator deletes its rows: core, copilot-mro, dashboard, api DONE (all pushed)
- Ranges and merges:
  - core `ue-t19-core` `bcdccb3..738c9f3`, merged `33293ed` (the first P3 merge); one review, 2 fix rounds, a
    re-review;
  - copilot-mro `ue-t19-mro` `973200cb..1a307d84`, merged `5f98c9d3`; reviewed by area (the seam with Document Hub,
    the orphan script), one fix round, a re-review;
  - dashboard: with Task 14 (`3f5fa51`);
  - api `ue-t19-api` `bd06a46..458bbfe`, built on `ue-t12`; one review, one fix round accepted on the diff; merged
    `f229ce1` (gated together with Task 13 lane C), pushed.
- Core, built: the row-seam registry, `operator_copies.py` (both entries), core's step on the delete's cursor with the
  counts in the event, the route order, the response fields (`data_removed`, `partitions_removed`,
  `partition_warning`, `cleanup_warning`) and a fixed 502 for a pre-pass failure. No DDL.
- Core review I-1: the route ran the seams under the owner's full-roster binding, where a seam statement missing its
  own binding would delete tenant-wide. Every seam call is now bound to the pair `(t, (o,))` and refuses `__ALL__`;
  the binding's restore on a raise is pinned per caller (re-review N-1).
- `cleanup_warning` asks the person to contact the platform owner (support); only the logs name the script.
- The plan's mutant "drop the `operator_id` predicate: Y's rows go" cannot be observed under the pair binding, so its
  text now observes `__ALL__` rows going.
- copilot-mro, built: `operator_teardown` over 55 registry-derived relations (`EXCLUDED_RELATIONS` empty); Document
  Hub's liveness shared as `cleanup.attempt_may_be_live`; `indexing.operator_still_exists` before `ensure_tenant`,
  which ends the attempt abandoned through a `DocumentHubOperatorDeleted` type, with no notification (it would land
  under the deleted operator); `scripts/_mro_owner_guards.py` (moved, not copied); the orphan script, with a
  repeatable `--tenant` filter for the shared test database.
- copilot-mro review fixes: a Document Hub failure no longer passes silently. The seam continues across documents,
  then raises `OperatorTeardownIncomplete` once, so the route's pre-pass answers 502 (review A I-1). The script shows
  every pair, a partitions-only pair included (found through the operator-delete event), tells held rows from failed
  ones, refuses an unknown `--tenant`, and records a failed partition removal in its audit event
  (`partitions_removal_failed`).
- copilot-mro deviations:
  - the script writes one audit event per pair it processes, with `rows_left`, not only per pair it clears;
  - it removes a pair's partitions only when the whole residue, held rows included, reads zero;
  - files outside Owned: `operator_partitions.py`, `memory_index.py`, `document_hub/user_erasure.py`, a docstring in
    `scripts/ad/materialize_ad_corpus.py`, and their tests;
  - it edited the live Weaviate isolation test, which first ran at the P3 phase review (8 passed).
- api: `wire()` registers the row seam first, all or nothing with the partition hooks, binding every name into a
  partial before the first registration (review M-1). `erase` is registered unwrapped, because it may raise
  `OperatorTeardownIncomplete`. The lane also carried two hand-offs: the automation executor passes
  `interactive=False` (Task 11b), and the CLI help names `STRANDED_AFTER_TEARDOWN` and its finisher (Task 13).
- api review M-3: a test fixture now restores core's erasure seams. Only a scratch leak probe can see that regression
  (a Future Improvement).
- Dashboard: the confirmation says the delete "…deletes all of its data in this tenant", and `cleanup_warning` shows
  as a toast that stays.
- The owner's Deploy/rollout step 2 on dev `copilot_mro` (2026-09-30): the dry run read 59 tables, 0 rows and 0
  partitions, so no `--execute` was needed.
- P3 phase review:
  - a user erasure cannot see rows under a deleted operator (B I-1, owner question O1);
  - two contradictory warnings on one 200 when a held-only residue's partition removal fails (B M-1, fixed in the
    core batch);
  - the operators list is not re-read after a refused delete (B M-3, fixed in the dashboard batch);
  - B M-2 and FI-B1 … FI-B3 are Future Improvements.

### Task 20: the owner's P3 rulings — four follow-ups (P3b, 2026-10-01; lanes M1, A+C, T, D; in parallel with P4)
The owner ruled the P3 pause's questions on 2026-10-01 (the status block lists every ruling). Four rulings need code.
Each lane: a fresh Opus implementer, a task review, a `--no-ff` merge, the full post-merge gate, a push.
- [x] **F1 (O1): the erasure reaches the person's rows under the tenant's deleted operators (copilot-mro).**
  - copilot-mro's user erasure binds the tenant's live roster (`operator_ids_for_tenant`, in `user_erasure.py` and
    `document_hub/user_erasure.py`), so row security hides every row under an operator that no longer exists, from
    both the erase and the residue (review B I-1, probe P-B1). Task 19 leaves such rows on purpose.
  - The Postgres binding of the erase AND the residue adds the tenant's deleted operators, read with the orphan
    script's own predicate (`_DELETED_OPERATORS_SQL`, one definition, imported, never copied). Every Weaviate call
    binds the live roster plus each deleted operator whose pair partition that collection still holds (Task 19
    keeps a deleted operator's partitions when its clean-up fails, until the finisher runs; controller ruling on
    the task review); the memory index is keyed by tenant alone and keeps the live roster.
  - Task 19's receipt rule (no orphan-operator key, C-18) holds again once this lands.
  - Proofs: P-B1 inverted in `tests/db/operator_teardown/` (the person's document under a deleted operator is seen
    by the residue before, and gone after); the mutant that binds the live roster only is killed.
  - Controller ruling on the task review (2026-10-01): "a deleted operator's partitions are already removed" is false
    when Task 19 keeps them (a failed post-pass, rows left that are not held, a failed partition removal). The
    erasure then completed and issued its receipt while the kept partition held the person's chunks (the review's
    probe), and the boot refusal does not stop a running process or the owner CLI. The index side therefore also
    reaches each deleted operator whose pair partition is still present (Task 19's own reader), in the erase and the
    residue. Built in F1's fix round, then a fresh scoped re-review.
  - Built (2026-10-01): copilot-mro `ue-f1` `58f05103..c1e060f1` (one review, two fix rounds, one scoped re-review:
    merge-ready, OPEN 0), merged `c5fee4fe`, pushed with the batch (estate gate green but for the known census reds).
    `row_tenancy.DELETED_OPERATORS_SQL` is the one definition; the orphan script imports it. Each deleted operator's
    kept pair partition is judged on its own (`present_operator_partitions`, narrowed to the index's collection); a
    failed presence read fails the pass with an all-zero `partial`. Bindings are compared as sets (`db_tenancy`
    sorts). Two accepted FIs (Future Improvements): an operator deleted with no audit row, and a renamed Document Hub
    class.
- [x] **F2 (O2): the owner can erase a Telegram pilot who cannot send `/goodbye` (api, telegram-bot; core only if the
  entry needs it).**
  - api: `user_erasure_cli request --channel-teardown --tenant <id> --user <id>`. The tenant must pass core's
    `is_channel_tenant`; the command calls core's teardown entry `freeze.request_channel_teardown` with the platform
    door as `via`. Immediate and uncancellable, like `/goodbye`. Never a plain request: a plain one would make lane
    C's concerns 3 and 4 real.
  - telegram-bot: an owner command that runs `/goodbye`'s own purge of the pilot's `tg_*` rows for one Telegram id,
    idempotent, documented in the README beside `/goodbye`. The api CLI's help names it, so the owner runs both.
  - Proofs: the CLI accepts a channel tenant and calls the teardown entry with the platform `via`; refuses a
    non-channel tenant and writes nothing; the bot command purges exactly what `/goodbye` purges and a second run is
    a no-op; a mutant per refusal is killed.
  - Owner rulings on the built lane (2026-10-01):
    - A legal pilot erasure is recorded as legal. Core's `request_channel_teardown` takes `rtbf` (default false; the
      request is immediate already, so the ledger's `rtbf ⇒ immediate` holds), and the CLI accepts `--rtbf` with
      `--channel-teardown`. The ledger row says legal; every view of the receipt (core's erasure reads, the
      CLI) shows the row's `rtbf` beside it; the completion's audit event carries `rtbf` for every erasure
      (F3 fix round 2, controller ruling: before it, a request opened legal left no event that said so).
    - When the owner's legal teardown strengthens a pilot's open `/goodbye`, F3's escalation event names the
      platform (`platform-cli`, `via = script`), as the plain `request --rtbf` does: one act, one actor
      (controller ruling 2026-10-01, P4 review B M-2; it supersedes the earlier "teardown token as actor" ruling for
      the event's actor only; built in the P4 fix round, part R). The request keeps the token as its requester,
      because step 6 recognises a teardown by it; core's `request_channel_teardown` takes the event's actor as
      `escalated_by`. The teardown's own tenant event now names the request's door: `script` for the owner CLI,
      `api` for `/goodbye` (B M-1).
    - The bot's purge command cancels a still-running renewal itself, as `/goodbye` does (one Telegram call with the
      bot token, then the cancel mark), and only then deletes. If Telegram refuses, it deletes nothing and says so;
      the README says what to do then.
    - Both go into F2's fix round. The core half builds on F3's core branch (F3 renames `freeze._request`).
  - Built (2026-10-01): api `ue-f2-api` `f229ce1..970e476`, merged `4ec77c5`, pushed with the batch; telegram-bot
    `ue-f2-bot` `7233180..4ceea73` (two fix rounds, one scoped re-review), merged `a3a253d`, gate 2547 passed, pushed,
    and the live bot restarted on it. The bot's purge reuses `/goodbye`'s own renewal switch (`switch_renewal_off`).
    Three FIs (Future Improvements): the new-subscription window, `/goodbye`'s five loose log pins, and the command's
    whole-bot import.
- [x] **F3 (O3): a platform legal (RTBF) upgrade of an open request writes its own audit event (core).**
  - Today the upgrade (`freeze.py`, the stronger request over an open windowed one) keeps `requested_by` and `via`, so
    the one permanent audit event at completion names the tenant admin and `api` for a legal erasure (review A M-2).
  - The upgrade writes its own audit event at the moment it happens: the platform as actor, the platform door as
    `via`, `rtbf`, the request id; ids only. The admin's original request stays as recorded.
  - Proofs: review A's probe PR1 inverted (the upgrade's event exists, names the platform, carries no personal
    data); the mutant that drops the event is killed.
  - Controller ruling (2026-10-01): every platform upgrade writes the event, not only a legal one (a non-legal
    `--immediate` over a windowed request has the same gap); its `change` carries `rtbf` true or false.
  - Owner ruling on the task review (2026-10-01, review M-5): a person's history route
    (`GET /users/{id}/operators/history`, gated own / owner / `users_view`) no longer shows the erasure's own events
    (the completion event and the upgrade event) to callers without `users_modify`, as every other erasure read
    requires. Built in F3's fix round, with the review's two small fixes and F2's core `rtbf` keyword.
  - Built (2026-10-01): core `ue-f3` `7c8c9a9..ff55703` (one review, three fix rounds, one scoped re-review), merged
    `abc9fd9`, pushed with the batch. `ledger.is_erasure_event` (kind `user` and a `request_id` in the change) is the
    one test the history route uses; the completion change is `{request_id, counts, rtbf, via}`.
- [x] **F4 (O4): no Erase on your own row (dashboard).**
  - The team page hides Erase on the signed-in admin's own row; another admin or the platform owner erases them.
  - Proofs: a unit test asserting booleans: the own row has no Erase, another row with `users_modify` does.
  - Built (2026-10-01): dashboard `ue-f4` `6e11bef..63d2cdc`, merged into `agent_sdk` `f398f62` and pushed.
    `offersErase` in `useUserErasures.ts`: a row offers Erase when the caller holds `users_modify`, their id is known,
    and the row is not their own (`useAuth().user.id`, the Cognito `sub`, against the row's `users.user_id`, which
    core sets to the `sub`). The desktop row and the mobile card both ask it; the requests panel and the confirmation
    are unchanged. Until the caller's id has loaded, no row offers Erase (a request could not be sent then).
    Proofs: the predicate's four cases; the mounted page with the caller on the roster; red-before "Erase on:
    Alice,Bob,Carol"; 9 mutants killed. Task review: 0/0/0. Core still accepts a self-erasure, as ruled.

## Review & merge protocol

1. Per task: fresh Opus implementer → fresh Opus adversarial reviewer (brief + report + diff + the phase scope) who
   RE-RUNS the named red-befores and mutants and emits a claims table; P0/P1 block, P2/P3 → Future Improvements.
2. Controller merges each task locally `--no-ff` into its mainline, runs the full post-merge gate there, and pushes
   once it passes (known reds excepted, named in the ledger). Once Task 17's pins merge, every merge of a repo they
   read (core, copilot-mro, shift-optimizer, iac, telegram-bot, the dashboard) also runs the api pin file from the
   api primary, and a core merge also runs the dashboard's `test:unit` (lane P review M-7): the pins fire only when
   they run.
3. Phase review (independent, adversarial) → triage → a fix round, merged, gated and pushed the same way. The owner
   waived the pause between phases on 2026-10-01; owner questions go to the owner as they arise.

## Deploy/rollout

1. Per database (`copilot_mro_test` → dev `copilot_mro` → prod), owner-run: `migrate_tenancy_schema.py`
   (`user_erasures`) → `provision_rls.py` (definer, EXECUTE, ledger grants) → `--verify-only` clean. Optimizer DB: none.
   Dev `copilot_mro`: run it when core merges — the dev stack runs from the merged checkouts, and the erasure routes
   500 until the table exists.
2. Orphan operators, per database, after Task 19's core and copilot-mro halves merge and before the erasure routes
   serve there (C-18, Task 19 Q3): the owner runs `copilot-mro/scripts/delete_orphaned_operator_rows.py` — the dry
   run, then `--execute --expect-rows N` with the dry run's total. Dev `copilot_mro` first, once, before Task 12
   merges: the dev stack runs from the merged checkouts, and the erasure doors serve there once Task 12 registers the
   seams (P3 plan review MI-6).
3. Merge/deploy order: core → copilot-mro, shift-optimizer → api → dashboard → iac (measured at the P1 review:
   copilot-mro's provisioning and `test_grant_role_privileges.py` read core's registry; the api imports core's
   `user_erasure`). telegram-bot (P3 plan review CR-1): its teardown client accepts both the 200 envelope and the 202
   body, so the bot's release depends on nothing in core and can go at any time. It must be live before core's Task
   13 serves: an older bot reads the 202 as a failure, keeps its rows and tells a frozen pilot that nothing was
   deleted.
4. AWS (deferred until implementation is done): iac apply (Cognito policy + S3 lifecycle) BEFORE the routes are used
   on AWS — without the IAM grant every request fails closed at the Cognito disable. Read Task 16's deploy notes
   first: the lifecycle rule covers the whole bucket, and the first apply expires every existing noncurrent version
   older than 30 days at once. The api process also needs the grant-pool credentials (`POSTGRES_GRANT_USER` /
   `POSTGRES_GRANT_PASSWORD`, owner decision 26): the copilot-mro seam runs the LLM-records definer on the grant pool,
   so without them the api registers no erasure seam and every erasure door answers 503, with one boot line naming
   the missing setting (the door check, P4 fix round part D; since part D2 it reads the pool's own user and password,
   so a blank value in either, or only the deprecated `GRANT_POSTGRES_PASSWORD`, is refused).
   Before the door check, such a host froze the person and then failed at that step on every retry. iac `main` declares
   both (`apprunner.tf`): the user by default, the password from the owner's hand-made secret
   `api/postgres/passwords`, which must exist with both JSON keys before any plan (P4 review C M-1). The apply is iac
   `main`'s whole apply: its other owner steps come first, in iac `README.md` (B4's log-group imports, B5) and the
   db-roles plan.
   **AWS deploy blockers, decided at deploy time (owner, 2026-10-01; P4 review C I-4 and I-1):**
   - Where the platform CLI runs. App Runner has no shell, the database and Weaviate are private to the VPC, and Task
     16 grants the Cognito actions to App Runner's role only. Until decided, legal (RTBF) requests, F2's owner erasure
     of a pilot, platform cancels and resumes cannot be made on AWS. Options: a one-off ECS task from the api image in
     the VPC, an SSM-managed admin box, or a platform-owner HTTP route.
   - Phoenix under O10 (c). App Runner's env (Terraform-managed) names no Phoenix and no "no Phoenix here" setting, so
     once O10 is built every AWS erasure would freeze its person. Either iac declares "no Phoenix here"
     (`PHOENIX_ENDPOINT=none`) there, or AWS gets a Phoenix with endpoint and key. The POC replica box runs a Phoenix
     but gives its api neither key. Under the door ruling (Owner / legal items, O10), a host with neither refuses
     every erasure request at the door (503) instead of freezing anyone (built in the P4 fix round, part D).
   - **A third, at the same time: X-Ray's `aws/spans` (P4 review C M-6).** With Transaction Search on (the owner's B5
     toggle), browser spans carrying `enduser.id` are kept in `aws/spans`, which never expires, while the receipt says
     `cloudwatch_days: 30`. Either set its retention right after the toggle (the Future Improvement "`aws/spans`
     retention" says how), or the receipt gains a limit key for it.
5. Owner-run: prod migrations/provisioning, the iac apply, the Cognito proof user, `AUTOMATION_SCHEDULER_MODE` (the
   owner's choice on 2026-10-01: the scheduler runs on AWS, so erasures and `/goodbye` finish on their own).
   Rollback: cancel open requests via the CLI, then redeploy the previous image. Cancel first: the previous image
   stands down (disables) the automations of anyone still frozen, and a later cancel does not re-enable them (Task 12
   review M-4). A request that can no longer be cancelled (immediate, or past its `erase_after`) keeps
   its person frozen: finish it with `--run-due` first, or re-enable those automations afterwards.
6. Phoenix (Task 15, review M-3): the api host needs BOTH `PHOENIX_ENDPOINT` and `PHOENIX_API_KEY`, and the key must be
   allowed to delete spans and sessions (the collector README's system API key). The local Phoenix has auth on: with
   the endpoint alone, every erasure fails closed (`INCOMPLETE_PHOENIX`) and stays `erasing`, the person frozen and
   the account kept, 6 tries then daily; a key that cannot delete holds every request at its first span delete.
   Owner, 2026-10-01 (O10): a host that names no Phoenix fails closed unless it declares "no Phoenix here"
   (`PHOENIX_ENDPOINT=none`), so name both keys (or the declaration) before a host's first erasure. The owner added
   both keys to dev's `api/.env` on 2026-10-01. Since the P4 fix round the keys come through copilot-mro's settings
   (the process environment, else `ENV_FILE`, else the working directory's `.env`): the api run from `api/` and the
   owner CLI run there both read `api/.env`. Declare `none` only in the environment of the processes that erase (the
   api, the CLI, a worker), never the collector's: the collector's Phoenix fragment and the evaluation script read
   `PHOENIX_ENDPOINT` as a URL (part M re-review M-4).
   **The replay** (`copilot-mro/scripts/observability/scrub_erased_user_spans.py`, P4 review C M-7) sweeps a completed
   erasure's Phoenix spans by `user.id`. Run it for a span exported after an erasure completed, and once on dev for the
   erasures completed before the P4 fix round, which ran with Phoenix unread (the CLI never loaded `api/.env`; review A
   I-1). Its docstring and `--help` follow O10, and the owner CLI's help names it and when to run it (P4 fix round,
   part D).

## Owner / legal items

- [x] **D9 legal opinion** (owner, 2026-10-01: the current keep list is accepted without a legal review):
  airworthiness `reviewed_by`/`review_note`, `authorization_events` actor/subject (incl. the
  erasure's own events: its completion's and an escalation's, each carrying `rtbf`), RBAC provenance columns, the ledger's opaque ids, and free-text knowledge kept under D1.
- [x] **D12 backup bound:** no backup/snapshot config exists in iac or deployment; the receipt states the bound. No
  replay is built (owner decision 31, 2026-09-28: a restore is disaster recovery only); see Future Improvements.
- [ ] SDK/CLI transcripts under `~/.claude/projects` on the API host: confirm retention or disable persistence.
  **Owner, 2026-10-01: turn saving off.** To build after P5's lanes: the api's Agent SDK sessions save no
  transcript (prove no file appears under `~/.claude/projects` for an api turn); then the receipt's
  `limit_host_sdk_transcripts` caveat goes, with core `RECEIPT_KEYS`, the dashboard contract and copy, and Task 17's
  receipt pin moving together. Existing api transcripts on dev: a one-time delete, on the owner's word.
- [x] Scheduler: the delayed half runs only where the scheduler is embedded/worker; otherwise a daily `--run-due`.
  Immediate requests and `/goodbye` then also wait for the owner's next `--run-due`, not 30 minutes (C-3, C-4).
  **Owner, 2026-10-01: run the scheduler on AWS** (`AUTOMATION_SCHEDULER_MODE` set there; Deploy/rollout 5).
- [x] D2 side question: should ordinary chat delete also hard-purge after N days (today it retains forever)?
  **Owner, 2026-10-01: keep forever** (no purge job).
- [x] **I-2 (P4 review A, 2026-10-01): the evaluation gate reads a purged chat as live.** **Owner, 2026-10-01: (a)**
  — in a tenant-project run, a judged chat with no `chats` row reads as deleted (golden-set runs unaffected; headless
  tenant turns stop being judged). Built in the P4 phase review's fix round, with one runner case.
- [x] **O10 (Task 15 review, 2026-10-01): a host that names no Phoenix.** **Owner, 2026-10-01: (c), block unless
  declared** — unset fails closed (the erasure retries); an explicit "no Phoenix here" setting skips and records the
  skip. Built in the P4 phase review's fix round, part M. Controller ruling (2026-10-01): the declaration is
  `PHOENIX_ENDPOINT=none` (OpenTelemetry's `none` convention: one key, no new flag); declared, the seam skips Phoenix,
  records the skip as a `phoenix` source in its orphans per source, and completes. It closes both skip branches of
  `user_erasure.py` (P4 review A M-4); chat delete's reap keeps today's behaviour for an unnamed host and reads
  `none` as no Phoenix. Before the fix, the seam skipped Phoenix, warned once and completed, so dev erasures run with
  Phoenix unread may keep spans (Deploy/rollout 6: the replay). Options as asked: (a) keep it; (b) unset fails closed;
  (c) the above; (d) record the skip only.
  - Controller ruling on P4 review C's consequence question (2026-10-01): a host that names neither a Phoenix nor the
    declaration refuses at the door, as R-DOOR does for a missing seam: `user_erasure_wiring.wire()` registers nothing
    and every door answers the existing 503 (`ERASURE_UNAVAILABLE`), so nobody is frozen by a misconfigured host; the
    seam's fail-closed stays for a Phoenix that goes away later. Why: under (c) alone such a host freezes the person
    and disables the account before the seam fails, and an immediate or legal request cannot be cancelled. Built in
    the P4 fix round, part D (api `62dc14b`, merged `5caa9fb`, pushed): the door reads the Phoenix keys through
    copilot-mro's own accessor, and checks the grant-pool credentials of the Future Improvement "A gateway without the
    grant-pool credentials…". Cost if wrong: one boot check, reverted.

## Future Improvements

- **One DocHub index fake for the unit and db erasure tests (p2simp review m-3).**
  - *What is duplicated:* two fakes of the same four `DocumentHubIndexService` methods, about 75 lines each:
    - the unit `_Index` in `tests/unit/document_hub/test_document_hub_user_erasure.py`;
    - the db `_Index` in `tests/db/document_hub/test_document_hub_user_erasure_db.py`.

    They differ only in dict key names and binding capture.
  - *Why deferred:* the simplification batch's S-M9 kept them apart as "different slices", which holds for
    `_Collection` and the Task 8 `_Chunks`, but not for these two. Folding them was left out of the fix round to keep
    it small.
  - *Complete fix:* one `tests/fixtures/document_hub/index_stub.py` both files import, so a change to the service's
    erasure surface is mirrored once.
- **The Document Hub drift reader reads `_chunk_properties`, not all of `index_artifact` (lane D fix part A,
  concern 2).**
  - *What is missing:* a key added to an object's properties inside `index_artifact`, after `_chunk_properties`
    returns, would not be read. So a user-keyed property written there would pass the line guard unplaced. None is
    today: `index_artifact` hands `_chunk_properties`' dict to `DataObject` unchanged, and the only other writer,
    `_drain_reassign`, writes the declared `owner_user_id`.
  - *Why deferred:* the round was scoped to `_chunk_properties`, and running `index_artifact` needs four stand-ins.
  - *Complete fix:* run `index_artifact` against a recording collection, with stand-ins for:
    - the partition key and `ensure_tenant`;
    - the embedder;
    - the `DataObject` import;
    - the drain and its filter.

    Then read the keys of every object it inserts.
- **The api's remaining auth-cache lines name roles, departments and tenants (P4 fix round part D2, concern 2; its
  review's M3 ruling).**
  - *What is missing:* the eviction lines (D2) and the cache-write WARNINGs and their DEBUG twins (part D3) name
    nobody. These lines still carry ids in their text:
    - the role and tenant sweeps' INFO lines (`flynapse_api/middleware/cache.py` around :328 and :353; `auth.py`
      around :1358);
    - the department lines (`auth.py` around :1299 and :1313; the ERROR also carries `department_id` and
      `tenant_id`);
    - the role-holder line (`auth.py` around :1267).

    A channel user's personal tenant id identifies a person, so a tenant sweep of a personal tenant names one.
  - *Why deferred:* none is on the erasure's path. The erasure declares user-scope evictions only, and its teardown
    runs in core, not through this middleware. The review scoped the round to the lines on every request's path.
  - *Complete fix:* give the whole module the eviction lines' treatment: a constant message, the sweep's type and
    counts as fields, and one pinned list that turns red on any new line naming an id.
- Self-serve erasure (D5 option c); telegram pilots already self-serve.
- Automate the channel-tenant residue sweep after teardown (today owner-run `delete_unentitled_partition.py`).
- Loki delete requests, once structured-metadata filtering is verified on 3.7.7.
- One shared `deleted-user` constant in utils instead of three pinned literals.
- Current-version expiry for `parse-sidecars/` (its docstring promises a lifecycle iac never declared).

Recorded at the P1 phase review (2026-09-27); each was deferred by a ledger ruling:
- **Terminal ledger rows are immutable only in Python (P1 review CORR M-2, COMP M-5).**
  - *What is missing:* the app role keeps UPDATE on every column of `user_erasures`, because the transitions need it. So a
    completed row can be rewritten (to `cancelled`, receipt NULL, another `user_id`), which hides it from a replay just as a
    DELETE would. The state machine is enforced only by the ledger store.
  - *Why deferred:* there is no live path. `db_query` runs read-only behind a table allowlist, and the revoke of DELETE
    already covers removal.
  - *Complete fix:* a BEFORE UPDATE trigger that refuses any change to a row whose old state is terminal, and any change
    to the identity columns (request id, tenant, user ids, requested_by, via, mode, rtbf, prior status, prior Cognito
    state, requested_at). It is provisioned beside the no-DELETE revoke and verified by `--verify-only`.
- **DB CHECK on `users.status` (T2-M6).**
  - *What is missing:* the status vocabulary, including `erasure_pending`, is enforced by the app only.
  - *Why deferred:* a CHECK needs a data migration of legacy values first.
  - *Complete fix:* migrate legacy values, then add the CHECK from the one vocabulary constant.
- **A Cognito account left disabled with no open request (T2-FC3, widened by P1 review CORR N-2).**
  - *What is missing:* two paths reach this state, and nothing re-enables the account:
    - a double failure (a lost disable answer plus a failed undo);
    - a single process death between AdminDisableUser and the freeze's COMMIT (e.g. a deploy draining the worker).
    A retry then records `prior_cognito_enabled = false`, so a later cancel will not re-enable.
  - *Why not a reconcile (P3 pre-flight C-11, dropped from Task 11):* it is unsafe and unbuildable. Nothing tells a
    failed freeze's disable from an administrator's (a death before COMMIT leaves no ledger row), so it would re-enable
    deliberate lockouts; mapping a pool account to its `users` row is a cross-tenant read the app role cannot make; and
    `cognito_accounts` has no list call.
  - *Complete fix:* commit the `requested` row before the Cognito writes, so a death leaves evidence to act on. That
    also gives the `requested` state (P1 review SIMP M-3, below) a use.
- **The boto3 Cognito client may be built from two threads on first use (T2-R2), the estate has three copies of the
  client factory, and `cognito_accounts.py` repeats one admin-write wrapper four times (P1 review SIMP M-4).** The
  wrapper fold was not made: core's `test_cognito_calls_are_spanned` requires each Cognito call inside its own
  `with cognito_span(...)` with a literal operation name, so a generic `_admin_write(operation, …)` fails it and a
  compliant fold is larger, not smaller.
  - *Complete fix:* one shared, lock-guarded, bounded (5 s) factory in core, used by `cognito_accounts.py`,
    `cognito_identities.py` and `tenant_claim_writer.py`. Open the Cognito span from botocore's own call events
    (`before-call` / `after-call`) inside that factory, so every wrapper — including a single folded admin-write
    helper — is spanned by construction and the per-call span test can check the factory instead.
- **The stand-down reason and notifications for a frozen owner (T3-C1, T3-M4).**
  - *What is missing:* the specific token `owner_erasure_pending` rides only on the exception. The run row records the
    generic `entitlements_unresolved`, and each stood-down automation still writes a bell row for the frozen owner.
  - *Why deferred:* surfacing it touches the executor, recorder, loop and dashboard.
  - *Complete fix:* the run row carries the specific reason, and a frozen owner gets no notification. Scheduled in Task
    12 (C-5): the run is recorded `skipped` with that reason, and nothing is disabled.
- **xdist + `SIBLING_CHECKOUTS` warning-serialisation crash (T3-C4).** It is pre-existing, and the api lanes pass with
  `-W ignore::UserWarning:_scripts_workspace_root_impl`. *Complete fix:* make the warning picklable, or emit it once
  in the controller process.
- **Definer hardening (T5-C4).**
  - A dedicated NOLOGIN owner role holding only the column UPDATE the rewrite needs, instead of `postgres`.
  - `--verify-only` compares the function body's hash with the DDL constant.
  - A retire step for an old definer signature when the signature changes.
- **The residue sweep's `--tenant` mode deletes the erasure ledger (P1 fix M2 re-review).**
  - *Current behaviour:* `delete_unentitled_partition.py --tenant` deletes every `tenant_id` table's rows for an id
    missing from `tenants`, `user_erasures` included. Only `--purged-tenant` keeps `NO_DELETE_RELATIONS`. That bites a
    registered-then-torn-down tenant, which after Task 13 is every `/goodbye` personal tenant.
  - *Why deferred:* the script connects only to `copilot_mro_test`, and it sweeps `authorization_events` the same way
    under an existing ruling.
  - *Complete fix (required before `ALLOWED_DATABASES` widens or the channel residue sweep is automated):* `--tenant`
    refuses an id that holds retained-table rows or has a tenant-delete event.
- **Replay completed erasures after a backup restore (D12, dropped by owner decision 31).**
  - *What is missing:* a restore to a snapshot older than an erasure brings the person's data back, and the ledger row
    recording the erasure is rolled back with it.
  - *Why not built:* no backups or snapshots are configured, and a restore is disaster recovery only.
  - *Complete fix, if backups are introduced:* an append-only off-database record (request id, tenant, completed_at)
    written at each completion, and an api-side `--replay-completed` that re-runs those erasures after a restore.
    One-off migration snapshots also hold later-erased people, so they are deleted once the migration is proven
    (about a week).
- **The `requested` state no committed row can hold (P1 review SIMP M-3).**
  - *Current state:* `open_request` inserts `requested` and the same transaction moves it to `frozen`. The state carries
    edges, stamps, CHECK entries and test rows for nothing.
  - *Why kept:* it is plan-prescribed (Task 1), and removing it needs a CHECK re-migration.
  - *Complete fix:* insert `frozen` directly and drop `requested` from the transitions and the CHECK.
- **Small simplifications left (P1 review SIMP M-11a, M-11c).**
  - `freeze._CANCELS_FROM` stays a one-entry map until the platform cancel exists (Task 11 fills it).
  - `update_user`'s pre-read freeze raise duplicates the guarded UPDATE's re-read. It is harmless, and removable when
    that function is next touched.
- **The copilot-mro Phase-1c scope guard re-arms at every `--no-ff` merge (P1 review COMP §3.6).** It anchors on the
  newest first-parent merge, so on the mainline its post-merge limb measures only work after the latest feature merge.
  This belongs to the observability program's guard and is routed to its ledger.

Recorded at the P2 phase review (2026-09-28); each was deferred by a ledger ruling or the P2 triage:
- **A re-key retried after a part-way delete splits its counts differently (Task 7 M-5).**
  - *What is missing:* the retry no longer finds the row, which is now `deleted-user`'s, so the unowned sweep deletes
    the remaining old objects under `document_hub_unowned_objects_deleted`. A clean pass counts them under
    `document_hub_objects_deleted`. The totals are exact and the residue is zero.
  - *Why deferred:* only the split between two keys differs; the sum is exact.
  - *Complete fix:* the receipt carries no per-placement counts (Task 11), so the split shows only in the ledger's
    step counts for the copilot-mro step. The seam counts both deletes under one key (P3 plan review MI-7).
- **An attempt claimed long ago can begin between the listing and the read, and the erase then settles it (Task 7
  M-7).**
  - *What is missing:* the verdict sees the same attempt and falls back to `updated_at`, which `mark_attempt_started`
    never bumps, so the attempt is judged abandoned and settled.
  - *Why deferred:* the executor's post-parse re-read then sees `needs_attention` and writes nothing, and DocHub's own
    reconciliation has the same single-row race. Task 11's receipt names the window.
  - *Complete fix:* the time predicate rides inside the settle's `WHERE` (an erasure-owned statement or a
    `mark_processing_failed` variant), so the judgement and the write are one statement.
- **No residue read for the owner id in the re-keyed copies' S3 object metadata (Task 7 M-3, FI-6).**
  - *What is missing:* a check that no re-keyed copy under `document-hub/raw/{t}/deleted-user/` still carries the
    person's id in its object metadata.
  - *Why deferred:* no store links a `deleted-user` object to the person after the re-key; a residue would HEAD every
    such object on every call and still could not attribute a hit. The copy uses `MetadataDirective=REPLACE`, and a
    unit pin (m07) kills the regression.
  - *Complete fix:* a residue read over the re-keyed copies' metadata, scoped to the keys the step re-keyed.
- **Two raises after Task 6's `partial` guard (Task 6 N-3).**
  - *What is missing:* a malformed definer row (`int(answer[name])`) or a naming-read document with no `memory_id`
    would raise a `KeyError` without `partial`.
  - *Why deferred:* both are unreachable with today's fixed shapes.
  - *Complete fix:* read both inside the guard, so every raise after a commit carries `partial`.
- **Schema conformance and the tenancy migrator ignore column DEFAULTs.**
  - *What is missing:* `data_discovery_jobs`' counters drifted to NOT NULL with no default on the test and dev
    databases while the registry says DEFAULT 0. Neither the migrator nor `test_schema_conformance.py` compares
    defaults, so the drift surfaced only as a fixture failure.
  - *Why deferred:* the owner fixed the drift by hand on both databases, and it is not erasure code.
  - *Complete fix:* conformance and `--verify-only` compare each column's default with the registry, and the migrator
    emits the `SET DEFAULT` for a mismatch.
- **Core's sibling-variant and variant-hazard infra tests depend on workspace state.**
  - *What is missing:* `test_cross_repo_reads_name_their_checkout.py` has two reds on the primary checkout: the
    sibling-variant case (the suffix is empty there, so every candidate is its own twin), and the variant-hazard case
    (it asserts that an api variant checkout exists, false once `api-erase` was removed).
  - *Why deferred:* pre-existing, and owned by the phase-7 infra guard.
  - *Complete fix:* both tests build their own fixture workspace instead of reading the real one. Routed to the
    phase-7 guard owner.
- **Task 6's Minors (m-1 … m-3, m-5 … m-12).** Each is non-blocking: every transaction is bounded and the erasure
  is correct without them. N-1 and N-2 were pinned in fix round 2.
  - m-1: the unit tenant-scope guard is a substring check that a subquery satisfies. Fix: assert the predicate in the
    statement's outermost `WHERE`.
  - m-2: the drift guard's reach. Fix: widen the pattern (Task 17 rules the estate-wide list); read DocHub's
    properties from `indexing.collection_properties()`; read every key the memory upsert writes; state in the line's
    docstring that person-bearing jsonb keys are out of any name-based guard's reach.
  - m-3: the index re-upsert can still embed (changed search text, a failed read, no stored vector) and, being
    insert-first, can re-create a document deleted after the naming read. Fix: a property-only PATCH helper in
    `memory_index` that never inserts and never embeds, the shape of Task 7's in-place chunk re-own.
  - m-5: the scope-guard comment names the old order (the definer now runs before the index). Fix: reword it.
  - m-6: the five data-discovery pairs are listed twice. Fix: one tuple of name, relation, column and verb.
  - m-7: `Placement.residue` is a string or a callable, dispatched by type. Fix: two named fields.
  - m-8: three residues cannot read non-zero once the id is scrubbed (`improvement_signals__detail`,
    `memory_item_events__metadata`, `improvement_findings__evidence`). This is inherent; Task 11's receipt says they
    are statement-proven.
  - m-9: the delegated placements name their owner in two forms (prose, a module path) and list only part of chat
    delete's line. Fix: one form, and either all of chat delete's line or only the user-keyed columns.
  - m-10: the naming read sends one OR clause per chat id. Fix: one `contains_any` clause.
  - m-11: the naming read caps at 10,000 documents. Convergence holds over passes (Task 11 allows `ceil(N / 10 000)`).
    Fix: page the naming read, so one pass sees every document.
  - m-12: `tests/db/improvement` errors 13 times when collected with the `tests/db/chat_history` files that install a
    bare `copilot_mro.app.db` stub (Task 6 adds a sixth copy). Pre-existing. Fix: a shared db-lane loader that
    registers the stub only for its own import and restores it, as the unit lane's `repo_modules_restored` does.
- **A reviewer email edited before the freeze escapes the match (Task 6).**
  - *What is missing:* `improvement_findings.reviewer` stores an email, matched through the `users` row's current
    address. Findings reviewed under an earlier address keep it.
  - *Why deferred:* no address history exists to match against.
  - *Complete fix:* record the reviewer by user id, so the erasure never depends on a mutable address.
- **Task 7's other Future Improvements (FI-1 … FI-5, FI-7; FI-6 is above) and N-2, N-3.**
  - FI-1: the sidecar reference scan lists the tenant's whole sidecar subtree and GETs every small object once per
    call that reaches content. Task 8's per-chat call multiplies it (P2 correctness, T8 m-6 evidence). Fix: a
    reference lookup that does not scan (content ids keyed by checksum from the attachment refs), if tenants grow.
  - FI-2: DocHub notifications addressed to `deleted-user` are inert rows. Fix: skip them.
  - FI-3: a PATCH of `owner_user_id` keeping the stored vector is unproven on the server. Carried to Task 18.
  - FI-4: the per-chunk PATCH in `_drain_reassign` is one call per chunk. Fix: batch it if a document ever holds tens
    of thousands of chunks.
  - FI-5: a re-key refused after its copy, then deleted by an admin before any rerun, leaves `deleted-user` copies
    nothing reaps (storage only, no personal id). Fix: the admin delete also reaps `deleted-user` objects no row
    references.
  - FI-7: `parse-sidecars/` has no lifecycle rule; listed above as current-version expiry.
  - N-2: inline or zombie DocHub executors can outlive the declared bound (inline processing has no ceiling; a
    thread-blocking zombie cannot be cancelled). Task 11's receipt names it. Fix: inline processing runs under the
    same ceiling, so the cutoff is a real bound.
  - N-3: a claimed-but-never-begun attempt is measured from `updated_at`, which a colleague's title or sharing PATCH
    bumps, extending a shared document's hold by up to 30 minutes each time. Task 11's receipt names it. Fix: measure
    it from a claim stamp that a PATCH does not touch.
- **The db statement-capture recorder wraps only part of the pool (Task 8 n-4).**
  - *What is missing:* it wraps `connection`, `fetch_all`, `fetch_one` and `execute` on the app pool, not
    `execute_returning_*`, `execute_many` or the grant pool, and its docstring claims more.
  - *Why deferred:* no unrecorded path carries the person's words today, and a fourth fix round cost more than it
    bought.
  - *Complete fix:* the recorder wraps the pool class (every method, both pools), or its docstring narrows to what it
    records.
- **Task 9's Minors (M-2 … M-7; M-1 is owner question 6).**
  - M-2, orphan operators (owner question 4): `DELETE /operators/{id}` leaves that operator's tenant+operator rows
    invisible to every binding: core's notifications and subscriptions, and copilot-mro's private Document Hub rows,
    memory items and events, and their index chunks (P2 correctness). The erase misses them and the residue reads 0.
    Deferred because it needs DDL. Fix: `delete_operator` sweeps its own rows (the root fix), or a postgres-owned
    definer erases by tenant and user across operators; the owner-run `delete_unentitled_partition.py` closes the rows
    meanwhile. Scheduled as Task 19 (the root fix, owner 2026-09-29).
  - M-3: the text-level payload de-attribution renames an object KEY equal to an id (duplicate keys then collapse), and
    rewrites a string that ends in an escaped quote followed by the id. Contrived for today's writers. Fix: state both
    edges in the docstring, or a recursive rewrite in a definer once one exists.
  - M-4: the drift guard matches column names only (a decoy `comments.assignee` survives; `automation_runs.params`,
    `notification_subscriptions.filters_json` and `tenants.primary_contact` are outside it). Task 17's census is the
    backstop. Fix: place every jsonb column of a relation that already holds a placed column, as KEEP with its reason,
    starting with `automation_runs.params`.
  - M-5: `DELETED_USER_ID` lives in the `core_copies` step module, so `quality.py` imports an erase module. Fix: move
    it into the package vocabulary (`ledger`, re-exported by `__init__`).
  - M-6: `core_copies` imports the private `ledger._require_opaque`, and `OPERATOR_ROSTER_SQL` is core's third
    spelling of the roster read (justified: it runs on the erase's own cursor). Fix: a public name.
  - M-7: the db proofs seed by direct SQL, not the real writers. Task 17's real-writer census covers it; no action.
- **Task 10's leftovers.**
  - m-1: the drift shapes miss `owner`, `user_name`, `creator`, `assignee`, `approver`, `requester`. Routed to Task 17.
  - A negative `POSTGRES_STATEMENT_TIMEOUT_MS` fails the seam loudly on every erase, while the pool silently runs with
    no ceiling. Fix: mirror the pool's greater-than-zero guard, or refuse the setting at startup.
  - The pre-existing wall-clock perf test `test_full_week_solve_completes_within_budget` fails under heavy machine
    load. Fix: a budget relative to a calibration run, or run it only in a perf lane.
- **One refusal type for every seam (P2 completeness M-3 = correctness M-5). SCHEDULED in P3: Tasks 11, 11b and 12
  (C-14; P3 plan review MI-7).**
  - *What was missing:* one core refusal that every seam's permanent refusal maps to, so Task 11 can tell a refusal
    from an incomplete.
  - *How P3 builds it:* Task 11 declares `lifecycle.SeamRefused` and the structural marker `erasure_refused = True`,
    and classifies a marked refusal as `failed` (the owner path) and everything else as incomplete (retried). Task
    11b sets the marker on copilot-mro's two refusal types. shift-optimizer imports no core, so Task 12's adapter maps
    its `ErasureSubjectRefused` to `SeamRefused`.
- **Nothing checks a seam's answer type before use (P2 completeness FI-B).**
  - *What is missing:* `register_seams` accepts any callable, and an `erase` answer's type is first touched when Task
    11 reads its counts.
  - *Why deferred:* Task 12's proof catches the one mis-registration P2 can produce; an annotation check would prove
    shape only.
  - *Complete fix:* Task 11 treats an `erase` answer that is not a `SeamErasure` as a fixed-text failure of the step,
    before recording it, so a mis-assembled deployment fails its first erasure with a clear reason.
- **The window between the final residue read and the completion commit (P2 correctness FI-2).**
  - *What is missing:* a colleague's mention or notification naming the person can land after Task 11's last residue
    read and before the `users` DELETE commits. Core's mention validator checks only format.
  - *Why deferred:* it is Task 11's design, and the window is small.
  - *Complete fix:* Task 11 re-runs `core_copies_residue`'s predicates on the completion cursor and refuses the commit
    unless they are zero. Core's relations share the ledger's database.
- **`agent_state` rows outlive the hard purge (P2 correctness FI-3).**
  - *What is missing:* the per-chat scrub empties `payload`, `label` and the pointer but keeps `namespace`, `key` and
    `status`. After the purge these rows are keyed by a chat id that no longer exists, live forever where `expires_at`
    is NULL, and `key` is caller-supplied (DataView names, run ids).
  - *Why deferred:* this is chat delete's line, and nothing names the person once the chat is gone.
  - *Complete fix:* the purge also deletes the verified chats' `agent_state` rows, in the same transaction.
- **P1's `freeze._transaction` has no statement ceiling (P2 correctness FI-4).**
  - *What is missing:* the same raw-connection shape as core's step had, on the request, cancel and completion paths.
  - *Why deferred:* it is P1 code, and its statements are single-row and keyed by primary key.
  - *Complete fix:* the same `SET LOCAL` from the pool setting. Closed by the core follow-up round: the freeze runs in
    `transaction.bound_transaction`.
- **Task 8 re-spells Task 6's SQL fragments (P2 simplicity S-M1).**
  - *What is missing:* the person, chats and blocks predicates, the count wrapper and the finding-copies predicate are
    byte-identical copies of Task 6's, and a fix to one would silently miss the other.
  - *Why deferred:* cheap, but it touches two approved modules.
  - *Complete fix:* Task 6 makes the five fragments public and Task 8 imports them.
- **The bound, ceilinged transaction block is written five times in copilot-mro (P2 simplicity S-M2).**
  - *What is missing:* each copy repeats rollback, cursor, optional read-only, the ceiling and the tenancy bind; utils
    already owns the ceiling and bind as the private `_apply_transaction_context`. Core's step was the copy that
    missed the ceiling.
  - *Why deferred:* it touches utils (the estate shared-helper rule needs the owner's confirmation).
  - *Complete fix:* a public utils `apply_transaction_context` and one `bound_transaction` context manager per repo;
    the per-seam ceiling tests collapse to one test of the helper.
- **`partial` is carried three ways, one with a dead branch (P2 simplicity S-M3).**
  - *What is missing:* Task 6 raises a typed carrier, Task 7 sets the attribute and swallows `AttributeError`, and
    Task 8 wraps on a False return. No exception this code can meet refuses the attribute, so Task 8's wrapper branch,
    `INCOMPLETE_STEP` and Task 7's `except` are unreachable; the "after committing" log line also fires for a refusal.
  - *Why deferred:* Task 11 formalises `partial`.
  - *Complete fix:* one core helper or `ErasureIncomplete(partial=)` base that all three use; drop the dead branch,
    `INCOMPLETE_STEP` and its contrived test; log the refusal separately.
- **The subject validators disagree on stripping (P2 simplicity S-M4).**
  - *What is missing:* five subject-to-ids validators; in copilot-mro Task 7 strips whitespace while Tasks 6 and 8
    match the raw value, so a subject built from anything but a ledger row could erase different rows per sub-seam.
  - *Why deferred:* unreachable today: the ledger bounds ids at request time.
  - *Complete fix:* `ErasureSubject` validates itself (the opaque rule, the marker refused); shift-optimizer keeps its
    own copy under its Protocol. The per-sub-seam refusal tests collapse to one.
- **Task 8's per-chat attachment and sidecar reap is redundant (P2 simplicity S-M6).**
  - *What is missing:* under R-LINKS-LAST the final sweep deletes every attachment object and Task 7 reaps every
    attachment's sidecars, so the per-chat pass does the same work early under a second set of count names (MR7b: with
    both removed, residue zero and siblings untouched all held).
  - *Why deferred:* the plan's Task 8 text prescribed the per-chat reap; removing it needs a confirmed plan change.
  - *Complete fix:* the per-chat reap covers only the chat-keyed prefixes (DataViews, agent state); the gather keeps
    only the file attachment ids.
- **Five hand-rolled fake S3 buckets (P2 simplicity S-M9).**
  - *What is missing:* five fake buckets (about 300 lines), three DocHub index fakes, two near-identical two-tenant db
    worlds, and repeated small doubles; the shared `tests/fixtures/s3/stub.py` lacks listing, delete and copy.
  - *Why deferred:* a shared-helper proposal, not a defect.
  - *Complete fix:* extend the shared stub with paged listing, `delete_objects` with a fault hook, `copy_object` and
    head metadata, and add a `tests/db/user_erasure/conftest.py` for the two-tenant world (about 350 fewer lines).
- **The placement lines' key forms and verbs differ (P2 simplicity S-M10). Keys and verbs CLOSED by the core
  follow-up round (p2c2, C-15; P3 plan review MI-7).**
  - *What was missing:* core keyed its line `relation.column`, called id-to-marker `scrub` and keyed its residue by
    step, while copilot-mro and shift-optimizer used `<table>__<column>` and `de-attribute`.
  - *Now:* core's `core_copies` keys its line and its residue `<table>__<column>` and uses the same kind vocabulary
    as copilot-mro (`delete`, `scrub`, `de-attribute`, `keep`, `delegated`).
  - *Still open:* no cross-repo pin holds the kind vocabularies equal. Task 17's pin list does not name one yet.
- **A missing count row reads 0 in three seams and raises in the fourth (P2 simplicity S-M11).**
  - *What is missing:* Tasks 6, 8 and 9 read no row as 0; Task 10 raises. Both branches are unreachable, since a
    count always answers one row. Task 10 alone reads its residue in REPEATABLE READ.
  - *Why deferred:* no behaviour differs today.
  - *Complete fix:* take the first column of the one row everywhere (it raises naturally), drop Task 10's special
    case and its test, and pick one isolation level for every residue.
- **Test-only surface in production code (P2 simplicity S-M12).**
  - *What is missing:* the composer's `deleted_user_id=` option (every caller passes the constant), a second
    declaration of the residue keys read only by tests, a repeated collision check, and a tuple whose second slot is
    unused.
  - *Why deferred:* harmless, and it touches an approved module.
  - *Complete fix:* import the constant, derive the placements from the residue declaration if a test needs them, and
    check the keys once.
- **Provenance comments, private cross-module imports and a source-format pin (P2 simplicity S-M13).**
  - *What is missing:* production docstrings cite plan task numbers and review ids, several shared fragments are
    reached through private names, and one Task 6 test pins an import's source text.
  - *Why deferred:* no behaviour is affected.
  - *Complete fix:* name the module and state the reason instead of the history; make the shared fragments public; pin
    the index helpers by identity.
- **About 1,000 redundant test lines (P2 simplicity §1 table, S-M5, S-M7, S-M8).**
  - *What is missing:* nothing; the tests over-prove. The ledger-identifier property is asserted eight times in
    copilot-mro; Task 8's order spy subsumes two unit tests and two more mostly prove the fakes; Task 7's unit and db
    lanes prove about eight scenarios twice over a fat unit fake. The review's §1 table names each one.
  - *Why deferred:* redundant, not wrong.
  - *Complete fix:* keep Task 8's static keys file as the one identifier test; fold the spy's missing assertion in and
    delete the four Task 8 tests; thin Task 7's unit store to a recorder and keep only what the db lane cannot reach.
- **An abandoned DocHub copy's write-back has no `updated_at` check (P2 fix concern 4).**
  - *What is missing:* `_settle_abandoned` writes back through `mark_processing_failed` without the compare-and-set the
    re-key now uses. If a document goes private or is deleted between a lost re-key race and the rerun, its copies
    under `deleted-user/{doc}/` are left behind.
  - *Why deferred:* it needs a lost race plus a visibility change inside the same window, and the residue does not
    read that prefix.
  - *Complete fix:* give the write-back the same `updated_at` compare-and-set, and on a lost race delete the copies
    under `deleted-user/{doc}/` before returning.
- **The core address lookup's tenant key is proven by its text only (P2 core fix review m-2).**
  - *What is missing:* no behaviour test fails if `PERSON_EMAIL_SQL` loses its tenant key. Row security on `users`
    applies even to the table owner and `flynapse_app` cannot bypass it, so production is safe; the test world also
    gives tenant B's person A's address, so it could not tell the mutant apart even under a bypassing role.
  - *Why deferred:* the database already enforces it for every role the service uses.
  - *Complete fix:* seed a person whose address is not shared across tenants and run the probe as a role that bypasses
    row security (a test-only role on `copilot_mro_test`).

Recorded at the P3 plan review (2026-09-29):
- **The bot keeps today's 200 teardown path beside the 202 (P3 plan review CR-1).**
  - *What is kept:* the bot's teardown client parses both the 200 envelope and the 202 request body, and `/goodbye`
    keeps its 200 flow, `partition_warning` branch included.
  - *Why:* so the bot can ship before core's Task 13 without breaking today's door.
  - *Complete fix:* once every core the bot talks to serves Task 13, drop the 200 envelope, its flow and the
    `partition_warning` branch.
- **Held Document Hub rows of a deleted operator wait for the owner's script (P3 plan review IM-8).**
  - *What is missing:* nothing clears them automatically. Document Hub's maintenance sweep binds the tenant's current
    roster, so it never sees them; they wait for `scripts/delete_orphaned_operator_rows.py`. (Task 19's Document Hub
    operator check stops a held attempt re-creating the partition; the script is the net for the race it leaves.)
  - *Why deferred:* the window is DocHub's 30-minute hold, and the route's `cleanup_warning` and log name the script.
  - *Complete fix:* a scheduled pass runs the row seam for every orphan pair: held rows whose hold has lapsed, and the
    rows a failed post-pass or the residue's eviction window leaves. The P3 phase review (review B I-1) widened it from
    held rows to every orphan pair, whichever way owner question O1 goes.
- **An operator delete's residue is read before the eviction applies (Task 19 core review P-1; P3 phase review B,
  FI-B1).**
  - *What is missing:* the route declares the grant eviction inside its transaction, and the api applies it after the
    response. A request still holding the deleted operator's grant can write a row after the residue read; that row
    is an orphan nothing reports.
  - The window is longer than one request. An automation run binds the operator ids it resolved at dispatch
    (`automations/identity.py`, bound by the executor) for up to its `max_runtime_seconds`, an hour by default. A run
    dispatched before the delete can write the operator's rows afterwards (an AD-compliance notification in core's
    `notifications`, a memory item): silent orphans, with no warning and, the partitions being gone, no boot refusal.
  - *Why deferred:* the orphan script's census finds such rows, and dev has few such runs.
  - *Complete fix:* a scheduled pass that runs the row seam for every orphan pair closes it. Short of that,
    the route re-reads the residue once the eviction has applied and in-flight runs naming the pair have ended (or
    applies the eviction before the post-pass), and carries a non-zero result as `cleanup_warning`.
- **The Cognito keep rule trusts the claim, not membership (Task 11 re-review O-2).**
  - *What is missing:* the account is kept when its `custom:company` claim names another existing tenant, whether or
    not the person was ever placed in that tenant. And a deployment that pins `TENANT_ID` places every account in its
    own tenant whatever the claim says (`api/flynapse_api/middleware/auth.py`), so in such a deployment a claim naming
    another tenant in the same database does not mean the account serves it: the erased person's account survives.
  - *Why deferred:* it is the owner's C-12 rule as ruled. A pinned deployment has its own database with one tenant, so
    the claim names no other existing tenant and the account is deleted; the gap needs a pinned deployment sharing a
    database with other tenants. A membership check needs a read bound to the other tenant, which the pair-bound
    erasure does not hold.
  - *Complete fix:* when the deployment pins its tenant, never keep; otherwise keep only when the person has a `users`
    row in the named tenant, read through a binding to that tenant.
  - *The same rule at the freeze (P3 phase review A, FI 3):*
    - The freeze signs out and disables the Cognito account whatever its claim says. If the person has a dormant
      `users` row in tenant B while their claim names live tenant A, B's admin locks them out of A for the whole
      window; a completion then keeps the account and re-enables it.
    - Low reach: invitation redemption now refuses before any row when the claim names another tenant, so only legacy
      rows or a renamed tenant get here.
    - Complete fix: the freeze applies the completion's keep rule. When the claim names another existing tenant, it
      records `prior_cognito_enabled = None` and leaves the account alone; the gateway's status read already locks
      the person out of this tenant.
- **The orphan census asks Weaviate once per deleted pair (Task 19 copilot-mro review B, M-4).**
  - *What is missing:* every census asks the memory index about each gone pair separately, and `--execute` runs the
    census twice. `copilot_mro_test` holds 1,154 such pairs.
  - *Why deferred:* it is an owner-run script; dev and production hold few deleted operators, and the cost is time,
    not correctness.
  - *Complete fix:* one index query per tenant for all its gone pairs, and `--execute` reuses the dry census it just
    verified against `--expect-rows`.
- **A queued run can resume a refused request once (Task 12 review M-3).**
  - *What is missing:* the api job skips a `failed` request before calling `run_erasure`, outside the per-request
    lock. A stale queued run that races the refusal can resume the request once.
  - *Why deferred:* every step is idempotent and the unchanged data refuses again, so the cost is one wasted run.
  - *Complete fix:* core's `run_erasure(..., resume_failed=False)`, checked under the lock; the job passes it.
- **The orphan script records no audit event for a pair whose Document Hub document fails (Task 19 re-review N-1).**
  - *What is missing:* the seam raises `OperatorTeardownIncomplete` after the whole pass, so core's step and every
    other relation's deletions have already committed, but the script writes no `authorization_events` row for that
    pair; the deletions show only as one summed count in the teardown's warning line.
  - *Why deferred:* the pair stays findable through the kept Document Hub row, and the next run finishes it and writes
    the event.
  - *Complete fix:* the exception carries the pass's per-relation counts, and the script writes the event with
    `rows_left` from them before re-raising.
- **The census-tables test reds other lanes when a branch pre-migrates a table (Task 19 re-review N-2).**
  - *What is missing:* the db test compares `copilot_mro_test`'s catalog with the registries both ways. Its
    "census minus erased" half turns red in every lane once any branch migrates a new operator-keyed table into the
    shared test database ahead of its merge.
  - *Why deferred:* no branch in flight adds an operator-keyed table; the red names the table.
  - *Complete fix:* keep "erased minus census" in the db test with a remedy message; move the extra-table check into
    the script at run time (the dry run names any such table, `--execute` refuses with exit 2), pinned by a unit test
    on made-up table sets.
- **The dashboard's analytics quality-contract test is red since Task 9 (found in Task 14's build, confirmed by its
  review).**
  - *What is missing:* Task 9 moved `DELETED_USER_ID` into core's `user_erasure/core_copies.py`, and `quality.py` now
    imports it. The dashboard's `tests/unit/analytics/analytics-core-quality-contract.test.ts` reads that constant as a
    module-level literal in `quality.py`, finds none, and fails on the dashboard base `0918191` against core `2ec64b5`
    as it does on Task 14's branch.
  - *Why deferred:* not Task 14's code; the value is unchanged, so the dashboard's analytics behave the same.
  - *Complete fix:* the test's reader follows `quality.py`'s import to the defining module and reads the literal
    there (or Task 17's pins name the new home); one change in the dashboard test, no core change.
- **The dashboard copies core's closed erasure states without a contract pin (Task 14 fix round 1).**
  - *What is missing:* the erase dialog treats a request as open unless its state is `completed` or `cancelled`, a
    list copied from core by hand; the receipt keys, the window and the 503 sentences are pinned by the generated
    contract, the states are not.
  - *Why deferred:* an unknown state counts as open, so a new core state makes the dialog state the request rather
    than promise a window: the safe side.
  - *Complete fix:* the contract generator also emits core's closed states, and the dialog reads them from it.
- **Task 11b's bounds start late, and some writers outlast the margin (Task 11b review I-2, M-4, concerns 2 and 4).**
  - *What is missing:*
    - The upload budget and the turn deadline start once the request body has arrived, but the freeze check runs at
      request start. A slow client can hold a large upload open for many minutes first (a 250 MB PDF on a
      ~1.2 Mbit/s uplink takes about 28 minutes) and then get a fresh 7.5-minute budget.
    - An SDK turn stopped at its deadline is recorded as `TimeoutError`; LangGraph records `deadline_exceeded`.
    - `interactive` defaults to `False`, so a new door a person drives is unbounded unless it passes `True`.
    - An S3 upload thread already sending when the budget ends runs to botocore's own timeouts. Memory curation and
      Document Hub's deferred processing after a turn were not measured against the 5-minute margin.
    - `finalize_turn`'s topic-classifier and query-type awaits (`agent_shared/lifecycle.py`, both engines) are not
      under the deadline; Task 11b's fix bounds and shields them only inside the SDK's `run_query` (fix round 1).
    - A judge or fuse call given up at the deadline leaves its Bedrock thread running; its usage lands after the
      cost snapshot, so that turn's `llm_usage` row under-counts.
  - *Why deferred:* anchoring at admission crosses into api; the other items fail safe or are unmeasured rather than
    known to exceed.
  - *Complete fix:*
    - The api gateway stamps `request.state.admitted_at` at request start; the turn deadline and the upload budget are
      measured from it.
    - One mapping in `ClaudeQueryAdapter` records `deadline_exceeded`.
    - The api automation executor passes `interactive=False` explicitly (`executor.py`, beside the `execute` call;
      built by Task 19's api lane); then copilot-mro makes `interactive` a required keyword on the builder and both
      `execute` surfaces.
    - Bound the S3 client's connect and read timeouts; measure memory curation and deferred processing against the
      margin.
    - `finalize_turn` bounds both classifier awaits by `execution.turn.deadline`, falling back to
      `history_relevant=True` and no query type.
- **A `/goodbye` request can be stranded once its tenant is gone (Task 13 lane C review, ruling 3).**
  - *What is missing:* step 6 deletes the channel tenant on the grant pool and commits; the completion is a later,
    separate transaction on the app pool. Every driver finds work by walking live tenants (`all_tenant_ids()`: Task 12's
    due sweep, `--run-due`, the scheduler's one-shot scan and recovery). So a request whose completion fails, whose
    step-6 ledger write fails, or whose process dies between the two commits stays `erasing` with no receipt and no
    completion event. A retry Task 12's job queues is inserted (no FK to `tenants`) but never served. No personal data
    survives; the erasure's evidence is what is lost. Only the owner's `run --tenant T --request R` reaches it, and it
    converges.
  - *Why deferred:* completing in the delete's transaction needs a privilege widening (the grant role owns `tenants`
    writes and has nothing on `user_erasures`), an owner design question; the discoverable-requests fix touches
    `provision_rls.py`'s definers, which DB-roles step 6 is rolling out now (never concurrently, R-LLM-DEFINER). Task 13's
    fix round logs one fixed ERROR line naming the finisher command for each such failure.
  - *Complete fix:* core adds one read, the `(tenant_id, request_id)` pairs of open requests whose tenant is gone,
    through a grant-role-only definer declared in copilot-mro's `provision_rls.definer_functions()` (the LLM-records
    definer's pattern); Task 12's due sweep and `--run-due` walk those pairs, running them inline under the scheduler
    (a queued run for a gone tenant is never served). About 40–60 production lines across core, copilot-mro and api;
    after DB-roles step 6 merges. The api CLI runbook names the ERROR line and the finisher.
- **Channel provisioning's own log lines still name the pilot (Task 13 lane C fix round, concern 3).**
  - *What is missing:* the provisioning POST's success line, its namespace refusal, its 500 and `_unmint_tenant`'s
    fields carry the channel user id or the tenant name (`telegram-<id>`, the pilot's Telegram id). Task 13 removed
    them from the door's 500 and from the tenant-delete event and log; these predate it.
  - *Why deferred:* outside Task 13's Owned lines; the ids are opaque outside Telegram.
  - *Complete fix:* those lines carry the tenant id only; the exception-text and privacy guards pin it.
- **Proposals, pending the owner's confirmation.**
  - **FI-S1, one drain and one re-erase loop, owned by Task 11. ADOPTED by the owner 2026-09-29; built in the P2
    simplification batch and Task 11.** Task 8 drains the person's runs itself, with SQL
    over core's tables, and runs its own bounded re-erase inside Task 11's. Task 11 drains once, after the freeze and
    before the first seam, in core beside `automation_store`; Task 8 becomes a single pass (gather → erase → residue;
    a non-zero residue raises with `partial` and does not purge, so Task 11's retry re-gathers). That removes the
    drain, the pass loop and cross-pass merging, and leaves the one-shot's ceiling arithmetic with one term.
  - **FI-S2, shared pieces for chat delete's finding-matching rule. ADOPTED by the owner 2026-09-29 ("do now and
    simplify"); built in the P2 simplification batch, together with every simplicity-review Minor above and the
    redundant-test inventory.** The rule is spelled five times (chat delete
    twice, Task 6 twice, Task 8 once), each pinned. Chat delete exports its finding-texts statement and the two
    matching predicates, Task 6 composes them behind its own CTE, and Task 8's gather imports them; the byte-identity
    pins go, and the residue-arm pins that widen a chat id to a set stay.

Recorded at the P3 phase review (2026-09-30); each was triaged as a Future Improvement:
- **BUILT in Task 15 (`ue-t15`, merged `a0d71393`; P4 review C M-2): core keeps orphans per source, but copilot-mro
  reports one integer (P3 phase review A M-1 = E M-3).** `user_erasure.py` `chat_orphan_source` and `_Tally.erasure`;
  P-1's sequence pinned by `test_the_ledger_keeps_each_chats_orphans_after_a_purge_and_a_failed_prefix_delete`.
  - *What is missing:* copilot-mro's `_Tally.orphans` (`user_erasure.py`) is one summed integer, and core's `_latest`
    replaces an integer report with the next one. An attempt that reaps every chat with 3 Phoenix sessions left,
    purges the chats, then fails at the prefix delete, records 3. The retry gathers no chats and reports 0, so the
    ledger ends with no orphans. Review E's probe P-1 reproduced it: `ledger-after-fold= 0` against
    `clean.orphans= 3`.
  - Core's own proof drives a fake seam answering a mapping. Task 11b made the per-source form optional and did not
    build it.
  - *Why deferred:* ledger only. The receipt carries no orphan key, and Phoenix's 30-day bound plus Task 15's
    `user.id` sweep backstop the sessions.
  - *Complete fix:* copilot-mro reports orphans per chat, keyed `chat_` plus the first 32 hex characters of a digest
    of the chat id, which fullmatches `IDENTIFIER_PATTERN` whatever the chat id (legacy ids need not be UUIDs). Core's
    merge already keeps a vanished source's last count. A copilot-mro unit case runs P-1's sequence (purge, a failed
    prefix delete, a clean retry) and asserts the ledger keeps 3. Natural home: Task 15, which edits this seam.
- **A gateway without the grant-pool credentials freezes people it can never erase (P3 phase review A, FI 1).**
  **BUILT** in the P4 fix round, part D (api `62dc14b`, `d7d4416`; merged `5caa9fb`, pushed 2026-10-02), with the
  controller's door ruling under O10.
  - `user_erasure_wiring.wire()` checks the grant password, and also a Phoenix or the `none` declaration, through
    copilot-mro's own accessor.
  - Without them it registers nothing, logs one fixed line naming the missing settings (never a value), and raises
    `ErasureSettingsMissing`. `routers/users.py` treats that as a sibling of the `ImportError` branch, so the boot
    succeeds and every request door answers the existing 503.
  - The owner CLI's `request`, `run` and `--run-due` are refused the same way, and the worker does not serve the kind.
  - Proven at both request doors and at the CLI; mutants that drop either check are KILLED.
  - Part D2 (api `9ca88a5`, `ecc0109`; merged `65f95f0`, pushed 2026-10-02) makes the check read the pair
    `get_grant_service()` connects with (`utils.config.settings.postgres_grant_user` / `postgres_grant_password`), not
    `grant_credentials()`. A blank value in either is missing, and the line names `POSTGRES_GRANT_USER` or
    `POSTGRES_GRANT_PASSWORD`. A conflict between the two password names no longer stops the boot. A host holding
    only the deprecated name is refused, and a renamed grant role passes.

  The original entry:
  - *What is missing:* "nobody is frozen where no erasure can finish" (R-DOOR) stops at seam registration. A gateway
    whose seams register but which lacks `POSTGRES_GRANT_USER` / `POSTGRES_GRANT_PASSWORD` accepts a request and
    freezes the person. The copilot-mro seam then fails at `get_grant_service()` on every try: six, then daily,
    forever. A windowed request can be cancelled for 7 days; after that the person stays frozen until the credentials
    are supplied.
  - *Why deferred:* dev's `.env` names both keys, the AWS deploy is deferred, and Deploy/rollout 4 states the
    prerequisite.
  - *Complete fix:* `user_erasure_wiring.wire()` checks `db_guard.grant_credentials()` for a password and registers
    nothing without one, so every door answers 503 as for a missing service. The gateway's `ImportError` branch gains
    a sibling "feature unavailable" class, so the boot still succeeds.
- **Running out of tries is silent (P3 phase review A, FI 2).**
  - *What is missing:* after the sixth failed try, a request that was not refused is retried once a day forever, and
    every failure logs at WARNING. Nothing reaches an ERROR alarm, so a legal (RTBF) request can sit `erasing`
    indefinitely while only the dashboard's state shows it.
  - *Why deferred:* nothing is lost: the request keeps retrying, and its state shows on the dashboard and in the
    CLI's `list`.
  - *Complete fix:* one fixed ERROR line (tenant id, request id, step, `failure_fields`) the first time a step's
    `attempts` reaches the sixth try, as `STRANDED_AFTER_TEARDOWN` does; the CLI help's log lines name it.
- **The per-request run lock can be lost mid-run (Task 11 review A M-5's residual; P3 phase review A FI 4, E M-1).**
  - *What is missing:*
    - The lock is a session lock on a pooled connection left idle for the whole run, up to 2 hours. Completion
      re-asserts it (`LOCK_LOST`), which narrows the window but cannot close it: a session lost between that check and
      the completion's commit still lets a second run overlap.
    - The lock relies on the app role having no `idle_session_timeout`. None is set today (only the query role gets
      role settings in `provision_rls.py`), so it fails safe. A future DB-roles step that sets one shorter than a long
      run would fail every such run at completion, on every retry, forever.
  - *Why deferred:* the seams are idempotent and the terminal moves are state-guarded, so an overlap costs
    double-counted partials at most; no timeout is configured.
  - *Complete fix:* `SET idle_session_timeout = 0` on the lock's session when it is taken (or a guard test over the app
    role's `pg_db_role_setting`). And the completion commits on the lock's own connection, or each run fences its
    ledger writes with a token stamped when it takes the lock, so a run whose session was lost cannot commit.
- **The remaining provenance allowances are keyed on bare method names (Task 11 review B M-3's residual; P3 phase
  review E M-1).**
  - *What is missing:* core's `test_provenance_argument_contract.py` classifies the methods that reach the audited
    writer by bare name in `_STATES_A_CONSTANT`, so a decoy method of the same name anywhere in `core/resources` is
    admitted (review B's decoy `advance` survived). Task 11's fix keyed the erasure's own three entries on qualified
    names (`_STATES_A_CONSTANT_AT`); the other entries keep the bare-name semantics.
  - *Why deferred:* outside that finding's scope; the guard is no weaker than before Task 11.
  - *Complete fix:* re-key every `_STATES_A_CONSTANT` entry `module:Qual` and drop the bare dict. The three
    `RoleService` entries name their class, and `provision_channel_user` gets a second entry (its handler in
    `channel_provisioning_endpoints` shares the name).
- **An operator delete racing a user erasure's Document Hub re-key strands the re-keyed copies (P3 phase review B
  M-2).**
  - *What is missing:* the teardown deletes a document's prefixes from the `owner_user_id` it listed, and keys the
    row's delete on the attempt, which a re-key does not move. When the person's shared document under the operator
    is re-keyed during the delete, in either order, the copies under `…/<tenant>/deleted-user/<doc>/` stay. Nothing
    counts them: the teardown's residue is row-based, the orphan census counts objects under orphan rows only, and the
    erasure's sweep covers the person's prefixes only. The operator's document content outlives its delete.
  - *Why deferred:* it needs a user erasure and an operator delete overlapping in one tenant.
  - *Complete fix:* `_purge_document` deletes `document_object_prefixes` for both the row's `owner_user_id` and
    `deleted_user_id()` (the document id keeps both to this document alone), with one unit case on a fake store
    holding objects under both owners.
- **Only Document Hub checks that the operator still exists before `ensure_tenant` (P3 phase review B, FI-B2).**
  - *What is missing:* `llama_index_ingestion` calls `ensure_tenant` per partition, and `ad_materialize` drives it on
    an owner-bypass connection. A materialise in flight during the delete re-creates the removed pair partition and
    commits `mro_documents` rows after the residue read. The boot check then refuses until the orphan script runs.
  - *Why deferred:* owner or manual runs, a rare overlap, and a loud failure with a known finisher.
  - *Complete fix:* the check moves into `weaviate_tenancy.ensure_tenant` for operator-keyed partition keys, one typed
    refusal for every writer, and Document Hub's check reuses it.
- **The operator delete's in-request clean-up can outlast App Runner's request ceiling (P3 phase review B, FI-B3).**
  - *What is missing:* the api runs on App Runner (`iac/apprunner.tf`), which cuts a request at 120 s. A large
    operator (thousands of memory items deleted one index document at a time, hundreds of Document Hub documents, two
    passes) outlives its request. The dashboard then shows a generic failure for a delete that succeeded, and
    `cleanup_warning`, "the next boot will refuse" included, reaches only the server log. The handler is not cancelled,
    so nothing is half-done, only unreported.
  - *Why deferred:* the AWS deploy is deferred, and the dev stack has no such ceiling.
  - *Complete fix:* answer 202 with a job id and run the pre-pass, transaction, post-pass and residue as a one-shot (the
    user erasure's pattern). Or measure the teardown on the largest dev operator first, and decide before the AWS
    deploy whether Task 19 Q2 (clean-up inside the request) stands.
- **A channel tenant with no account is never torn down (Task 13 lane C review concern 3; P3 phase review E M-2).**
  - *What is missing:* the channel door answers 404 for a channel tenant with no `users` row, and nothing removes the
    tenant unless the pilot returns (the next `/start` replays into it and heals it). Its name still carries the
    Telegram id (`telegram-<id>`), and its partitions stay. The lasting case is a completed platform (non-teardown)
    erasure of a channel user.
  - *Why deferred:* unreachable while the last-active-owner refusal holds. The channel user is the personal tenant's
    sole Tenant Owner, so every non-teardown request for one is refused. It becomes live if a plain request is ever
    allowed for a channel user. Owner, 2026-10-01 (O6): recorded for later.
  - *Complete fix (an owner choice):* a platform erasure of a channel user also tears the channel down, or the door
    tears down an account-less channel tenant directly (no person, so no erasure).
- **The channel door answers a platform-opened erasure with the tenant door's 409 (Task 13 lane C review concern 4; P3
  phase review E M-2).**
  - *What is missing:* while a non-teardown request is open for the channel user, the door answers
    `OPEN_REQUEST_CONFLICT`, the tenant door's sentence. The bot's client handles 200, 202 and 404, so this 409
    surfaces as a generic failure. The refusal itself is right: a platform request never tears the channel down, and
    the person is frozen by it anyway.
  - *Why deferred:* unreachable for the same reason as the account-less tenant; only the bot's wording is at stake.
    Owner, 2026-10-01 (O6): recorded for later.
  - *Complete fix:* the door answers a platform-opened request with its own fixed sentence, pinned across both repos
    like the deletion-in-progress 409, and the bot words it as a deletion the platform started.
- **A frozen person who is still signed in gets no account-level answer from the dashboard (P3 phase review D, FI 1).**
  - *What is missing:* the gateway answers every call they make with 403 "This account is scheduled for erasure and
    can no longer be used." The dashboard shows it as one error per call, wherever the call surfaces, until the access
    token expires; nothing handles that sentence.
  - *Why deferred:* nothing is reachable, because the gateway refuses every call; the freeze's global sign-out revoked
    the refresh token, so it ends at the access token's expiry; Task 14's spec does not ask for it.
  - *Complete fix:* `fetchWithAuth` recognises that exact 403 sentence and signs the session out to a page that states
    it. The sentence is pinned to api's `ERASURE_PENDING_DETAIL` by a generated contract, as the receipt is.
- **The erase confirmation promises a window before the erasure list is read (P3 phase review D, FI 2).**
  - *What is missing:* while the list is loading, or after it failed, the dialog still promises a 7-day window and a
    cancel, though the person may already hold an immediate request.
  - *Why deferred:* the success line states the answered request's own `cancellable` (Task 14 fix round 1), and a
    repeat request changes nothing.
  - *Complete fix:* until the list is ready, the dialog says "Whether a request is already open could not be read." in
    place of the window line.
- **One four-way control switch is written twice in the dashboard (P3 phase review D, simplicity).**
  - *What is missing:* `cancelControl` (`ErasureRequestsPanel.tsx`) and `eraseConfirmControl`
    (`EraseTeamMemberDialog.tsx`) are the same four-way switch with different labels.
  - *Why deferred:* cosmetic, and not worth a round on its own.
  - *Complete fix:* one helper taking the four labels, when either file is next touched.
- **"Teardown" names three acts (P3 phase review E, F-3).**
  - *What is missing:* copilot-mro's `tenant_teardown` removes a tenant's storage and partitions; copilot-mro's
    `operator_teardown` deletes an operator's ROWS (core calls the same act a row seam, and its own half
    `operator_copies`); the channel teardown deletes a tenant.
  - *Why deferred:* cosmetic; the rename touches the api wiring, the orphan script and the tests.
  - *Complete fix:* rename `operator_teardown` to the user axis's shape (for example `erased_operator_copies`, beside
    core's `operator_copies`), so "teardown" means storage and partitions only. Do it with other changes there.
- **The api suite cannot see a registry leak between test files (Task 19 api fix round 1, concern 1).**
  - *What is missing:* `test_partition_wiring`'s fixture now restores core's user-erasure seams, but dropping that
    restore again passes every repo test. Only a scratch leak probe, running the three registry files in both orders,
    catches it (mutant M10).
  - *Why deferred:* the brief fixed the proof as order runs, and the fix itself is in.
  - *Complete fix:* a module-scoped autouse check in each of the three registry-restoring files, comparing every
    registry global by identity at module start and end. A failure in a fixture's teardown reports as an error, which
    survives xdist; a session-end conftest sentinel would not, because its exit status is lost under `-n`.

Recorded at the P3 review fixes' core batch (2026-09-30, `ue-p3fix-core`, concerns 1–4):
- **Step 6's personal-tenant re-check is the tenant type, not the door's full check (core fix concern 1).**
  - *What is missing:* step 6 refuses a tenant whose `tenant_type` is not `individual` (`NOT_A_CHANNEL_TENANT`), but
    the door's `find_channel_tenant` also derives the tenant from the channel ids. A platform-created `individual`
    tenant that is not a channel tenant would still pass.
  - *Why deferred:* only the channel door writes a `CHANNEL_TEARDOWN` request, after its own full check; step 6 does
    not carry the channel ids, so the type is the strongest predicate it can read today.
  - *Complete fix:* the teardown request records the channel identity it was opened for (ids only), and step 6
    re-runs the door's own predicate against it.
- **A refused step 6 leaves an erased person in a `failed` request (core fix concern 2).**
  - *What is missing:* the re-check runs at step 6, after steps 1–5 have erased the person (Cognito included). A
    refused request is `failed` with the tenant standing; finishing it needs the owner to correct `requested_by`
    first, and no runbook line says so.
  - *Why deferred:* reachable only through a `CHANNEL_TEARDOWN` request written some other way than the door.
  - *Complete fix:* run the re-check before step 1 as well (refuse before anything is erased), and give the owner CLI
    the correction as a named, audited action.
- **`DELETE /tenants`'s partition-failure line has the channel teardown's old gap (core fix concern 3).**
  - *What is missing:* `tenant_endpoints.py` ~523 names the bare script, not the store sweep (credentials, Document
    Hub objects, partitions), and carries no operator ids.
  - *Why deferred:* it predates P3 and sits outside the review's finding.
  - *Complete fix:* share `_STORAGE_LEFT`'s wording and its operator-id fields with that route; its Task 17 pin row
    then covers both.
- **A dashboard test carries the old held-rows sentence as sample text (core fix concern 4).**
  - *What is missing:* `operator-write-mutations.test.tsx` ~847 still quotes "with its partitions"; it pins nothing.
  - *Why deferred:* cosmetic.
  - *Complete fix:* update the sample to core's current `_CLEANUP_HELD_WARNING` with the next dashboard change there.

Recorded at the Task 20 and Task 16 task reviews (2026-10-01):
- **The dashboard's "this row is you" rests on core's `user_id` = `sub` rule, unpinned (F4 review FI-1).**
  - *What is missing:* `offersErase` compares the row's `users.user_id` with the caller's Cognito `sub`. Core's
    `create_user` makes them equal today, but core's docstrings expect surrogate ids distinct from the `sub` later;
    then the admin's own row would offer Erase again, with no signal.
  - *Why deferred:* the premise holds for every row core writes, and the dashboard has no surrogate id to compare.
  - *Complete fix:* `/auth/permissions` returns the caller's internal user id, and the page compares rows against it.
- **The team page's hooks run without `react-hooks/exhaustive-deps` (F4 review FI-2).** Dropping `offersErase` from the
  `columns` memo's dependencies passes every test (another dependency rebuilds the memo today). *Complete fix:* a
  per-file lint override enabling the rule for `page.tsx` and `useUserErasures.ts`.
- **An exclusive-policies resource on the instance role would delete the erasure grant unseen (T16 fix round 1).**
  An `aws_iam_role_policies_exclusive` added later without the erasure policy's name removes it at every apply, and
  every test passes. *Complete fix:* a pin that any such resource on the role names every inline policy on it.
- **The provenance contract cannot follow a function passed by reference (F3 review M-3, older than F3).** The tenant
  door's `answer_erasure_request` calls the freeze through `asyncio.to_thread`, so a defaulted `via` there goes
  unrefused. *Complete fix:* the contract also resolves callables passed as arguments to the known dispatchers.
- **The provenance contract matches its audited writers by bare name (F3 review M-4, older than F3).** A function of
  the same name elsewhere in core (`request_erasure`, `revoke`) passes unchecked. *Complete fix:* key the list by
  module and name.
- **The owner's bot scripts require every bot setting, though the purge reads only the database URL (F2 bot review
  M-1).** A host holding `BOT_DB_URL` alone is refused. *Complete fix:* a narrower settings read for owner scripts
  (they share the convention with `mint_invites` and `seed_salary`).
- **The two F2 runbooks name each other's commands and columns as plain text (F2 report Concern 5).** The api help
  names `python -m telegram_bot.purge_account` and `tg_users`' columns; the bot README names the CLI's
  `request --channel-teardown` line. *Complete fix:* Task 17 pins both (the bot module exists; the CLI's parser
  accepts the README's line).
- **An operator deleted with no audit row is not reached (F1 concern 2).** A deleted operator is one an
  `authorization_events` operator delete names (the census's definition). An operator removed by hand, or before the
  route wrote its event, leaves rows no app-pool read can name, so the erasure neither erases nor counts them.
  *Deferred:* finding them needs the owner (BYPASSRLS) census, which then records the pair's audit row and makes it a
  deleted operator for every later erasure; dev's census read 0 rows (2026-09-30). *Complete fix:* none unless such
  deletes recur; then the census runs before the erasure's residue.
- **A Document Hub class renamed outside the lifecycle registry (F1 re-review FI-A).**
  `present_operator_partitions(…, collection_name=X)` answers `[]` for any `X` outside `mt_collection_names()`. With
  `WEAVIATE_DOCUMENT_HUB_CLASS_NAME` set to another name, the erasure binds no deleted operator for the index (the
  pre-F1 gap, silently), and Task 19's hooks never create or remove that collection's pair partitions. *Deferred:* no
  deployment sets the variable (none of iac, deployment, `.github`, the Dockerfiles, `.env.sample`, api or lambdas
  names it), and the strict boot check refuses a cluster without the literal collection. *Complete fix:* either the
  narrowed reader raises on a collection that is neither a registry member nor tenant-keyed, or the registry reads the
  Document Hub name from settings, so every reader follows a rename together.
- **The new-subscription window (F2 bot re-review FI-1).** A pilot's NEW subscription bought between the purge
  command's read and its renewal switch (possible only in the grace after a failed renewal) keeps renewing with no
  row. `/goodbye` has the same window, wider between its mark and its purge. *Deferred:* it needs a failed renewal and
  a re-purchase within seconds, and Money operations §4's orphan query catches its next charge (probe P4f). *Complete
  fix:* the one shared `switch_renewal_off` re-reads the handle after the switch and switches any new one before the
  sweep, so both doors close it together.
- **`/goodbye`'s five other log lines are pinned loosely (F2 bot fix round 2, concern 3).** Each is asserted only as
  "a record at that level mentions the id": the teardown-failure ERROR (`test_account_deletion.py:553`), the partition
  WARNING (`:618`), the refused-202 ERROR (`:721`), the read-failure WARNING (`:918`), the purge-failure ERROR (`:976`,
  level only). *Deferred:* outside F2's brief, which pinned the refusal line and the shared switch's line; these are
  read, not mutation-tested. *Complete fix:* pin each by level, template, args and `error_type`, as
  `test_purge_account.py` pins the switch's.
- **The bot's purge command imports the whole bot (F2 bot fix round 1, concern 2).** It imports `telegram_bot.app` to
  reuse `configure_logging` and its token pins: about 1 s more to start (`--help` 2.8–3.1 s → 4.0–4.1 s under a load
  of about 16). *Deferred:* a copy of the pins would be worse (two copies of the token redaction), and the cost is one
  owner command's start. *Complete fix:* `configure_logging` and `LOG_FORMAT` move into a light module that `app` and
  the owner commands both import.
- **Task 15: copies exported 2026-09-14..09-17 carry `enduser.id`, not `user.id` (report concern 2, review FI-A).**
  Neither the reap, the retry nor the sweep reaches them, and no residue sees them. *Deferred:* they age out under
  Phoenix's 30-day retention by about 2026-10-17, the bound the receipt states, and closing the window would cost
  every attempt from now on (1–2 requests per chat, or 4 pages per sweep). *Complete fix, if wanted sooner:* a replay
  flag that also reads `enduser.id`.
- **Task 15: span deletes leave a session's row and its session-level annotations (report concern 3, review FI-B).**
  Sessions are deleted only through the gathered chat ids; a session keyed otherwise (before 2026-09-23 the content
  pipeline sessioned by browser) keeps its row and annotations until retention, and the replay sweeps spans only.
  *Complete fix:* delete the sessions the swept spans name (`session.id`, by GlobalID, guarded to the tenant's
  project) before the span sweep, in the seam and the replay.
- **Task 15: a large backlog drains 200 spans an attempt (report concern 5, review FI-D).** A person whose sessions
  did not take most of their spans needs ⌈N/200⌉ attempts and stays frozen meanwhile. *Complete fix, if a backlog ever
  matters:* drain by sessions (above) or by trace (`DELETE /v1/traces/{id}`, not in client 3.5.0); never raise the
  span limit.
- **Task 15: the span sweep trusts the server's attribute filter (review FI-F, defence in depth).** A server or proxy
  that ignored the `user.id` filter would answer the whole tenant project, and up to 200 other people's spans an
  attempt would be deleted. The version guard (≥ 14.9.0) and the pinned 20.8.0 server prevent it today. *Complete
  fix:* before expanding traces, keep only spans whose returned attributes carry one of the ids; the returned shape is
  confirmed in Task 18's live run.
- **Task 15: the replay reads twice and does not say when it was capped (review FI-G).** *Complete fix:* read once,
  delete from that read, and report `capped: [request ids]` when a person's spans reach `--span-limit`.
- **Task 15: the retry-then-sweep policy lives in the composer (review M-4, FI-H).** `user_erasure.py` grew +209/−23
  where the plan owned one call. *Complete fix:* `_sweep_phoenix`'s two rules move into `phoenix_session_scrub.py` as
  one function with two callbacks; the tally and the residue part stay in the seam.
- **Task 15: a limited sweep can strand an untagged span (review FI-I).** Truncating at 200 by sorted GlobalID across
  traces can delete a trace's tagged spans and leave its untagged child, which no residue counts (the review's probe:
  150 traces, limit 150 → 2 traces keep only their child). Unreachable with today's data (every content-copy span is
  tagged since 09-17). *Complete fix:* delete each trace's untagged spans before its tagged ones, or truncate at trace
  boundaries.
- **Env samples (owner request 2026-10-01): the api image carries the SMTP password.** api's `deploy.yml` passes
  `SMTP_USER` and `SMTP_PASSWORD` from GitHub secrets as build args, and the `Dockerfile` copies both into `ENV`, so
  anyone who can pull the ECR image, or read its build cache, reads the password. *Deferred:* AWS deploy work, owner-run.
  *Complete fix:* App Runner takes both as runtime secrets (Secrets Manager); the Dockerfile and the workflow drop
  them; the SMTP password is rotated, because every image built so far carries it.
- **Env samples: App Runner's api names no Claude transport.** `agent_pipeline._claude_runtime_provider` reads
  `CLAUDE_CODE_USE_BEDROCK` from the process environment; unset, the Agent SDK goes to the Anthropic API. App Runner's
  env (`iac/apprunner.tf`), the Dockerfile and the deploy workflow set neither it nor an Anthropic key, so wherever the
  SDK path serves on AWS it has no working transport. *Complete fix:* App Runner's env sets
  `CLAUDE_CODE_USE_BEDROCK=1`, and its instance role can invoke the Bedrock models.
- **Env samples: two dead knobs.** copilot-mro `config.py` keeps `otel_endpoint` (`OTEL_ENDPOINT`), which nothing reads
  (the OTel SDK takes the standard `OTEL_EXPORTER_OTLP_*` contract); `api/build.sh` passes a `GIT_TOKEN` build arg the
  Dockerfile never declares. *Complete fix:* delete both.
- **`aws/spans` retention: the receipt's 30-day CloudWatch bound does not cover X-Ray's span group (P4 review C M-6;
  P4 fix round part R, item 7).**
  - *What is missing:* with Transaction Search on, X-Ray writes 100% of spans into the `aws/spans` log group; browser
    spans carry `enduser.id`, which the collector upserts from the gateway header. The group never expires: iac
    declares only its resource policy (`cloudwatch.tf` B5). The receipt states `cloudwatch_days: 30`.
  - *Why deferred:* CloudWatch Logs reserves the `aws/` prefix (`CreateLogGroup`: "Log group names can't start with
    the string aws/"), so Terraform cannot create the group; only X-Ray can, when the owner enables Transaction
    Search. iac can hold its retention only by importing it after that toggle, and no other resource sets a log
    group's retention. The toggle and the AWS deploy are both still the owner's.
  - *Complete fix:* in the owner's B5 step, right after the toggle, `terraform import
    aws_cloudwatch_log_group.transaction_search_spans aws/spans` against a new `cloudwatch.tf` block (`name =
    "aws/spans"`, `retention_in_days = var.log_retention_days`, the usual tags, `lifecycle { prevent_destroy = true }`)
    with an HCL block test; or, without an import, `aws logs put-retention-policy --log-group-name aws/spans
    --retention-in-days 30`. Task 17's cloudwatch pin then covers it. The same applies to
    `/aws/application-signals/data` if the service created it first. If the owner rules the receipt need not cover
    `aws/spans`, the receipt gains a limit key instead. Not verifiable offline: that `PutRetentionPolicy` is accepted
    on the service-created group.
- **`request_channel_teardown`'s `escalated_by` defaults to the teardown token (P4 fix round part R, concern 2).** The
  default keeps the channel door's call (it never escalates) and the unmerged branches' calls working; a future caller
  passing `rtbf=True` without it would record the token as the escalation's actor again. Today only the owner CLI
  states `rtbf`, and api tests pin the keyword on every teardown call. *Complete fix:* make it a required keyword
  once the db-roles step 7 branch has merged.
- **The S3 writes the erasure-delay margin covers are bounded by one attempt only (Task 17 lane P fix round, concern
  4).** utils' `S3Service` client sets no retry policy, so botocore's legacy mode applies: up to 5 attempts at 60 s
  connect plus 60 s read each, about 600 s, twice the 300 s margin. Row 5h's pin counts one attempt; the bounds
  module's docstring says retries are not covered. *Complete fix:* give the S3 client the margin's writes use an
  explicit timeout and retry policy whose whole budget fits the margin, and pin the whole budget instead of one
  attempt. Row 5h also assumes the statement ceiling is the code default; a deployment that sets
  `POSTGRES_STATEMENT_TIMEOUT_MS` re-opens the judgement.
- **A tenant whose Phoenix project the guard refuses holds its erasure forever (P4 fix part M concern 5, re-review
  M-3).** Today unreachable: core mints uuid4 tenant ids, and no person is erased from `__SYSTEM__`. *Complete fix:*
  raise `UserErasureRefused` there instead of the incomplete, so the request goes `failed` for the owner to see, as
  core's taxonomy treats a condition no retry can fix.
- **The compaction reap's WARNING logs `memory_id` (P4 fix part M concern 3).** An opaque digest id, not a person or
  chat id, once per failed document per attempt. *Complete fix:* drop it, as the reap's chat id was dropped.
- **The bot purge command's `--help` and docstring name `request --channel-teardown` unpinned (P4 review B M-4, its
  third bullet).** *Complete fix:* the cross-repo pin file parses the bot's help text for the api command it names.
- **Task 17 lane P review (2026-10-01), five leftovers.**
  - *M-3:* the finishers pin skips a string that names two or more scripts (none does today). *Complete fix:* check
    every named script exists, and attribute each flag to the nearest preceding script mention.
  - *M-5:* the dashboard has two rules for "no core beside" (the analytics contract skips only under
    `GITHUB_ACTIONS`; the receipt guard defaults `REQUIRE_BACKEND` to 1 in `package.json`, POSIX-only; the run-error
    and run-trigger guards still skip). *Complete fix:* one helper for the four sibling-reading guards.
  - *M-6:* the pin file is the api suite's third AST module-literal reader. *Complete fix:* one shared
    `tests/_ast_literals.py` before the next copy.
  - *FI-1:* the operator-delete reader is heuristic (nullable means "bound to `None` in the route"; capitalised or
    digit names are dropped). *Complete fix:* read the route's `response_model` once it has one.
  - *FI-2:* the analytics failure message names `quality.py` where the literal was read from the defining module.
    *Complete fix:* carry `resolveDeletedUserId(...).where` into the message.
- **The out-of-band pilot erasure is two owner commands that nothing reconciles (controller ruling 2026-10-01: "an
  automatic reconcile stays an FI"; F2 report concern 7; P4 review C M-4).** `request --channel-teardown` (api host)
  and `python -m telegram_bot.purge_account` (bot host) are separate. A completed platform erasure whose bot purge
  never ran leaves `tg_users` (the Telegram id, the gone tenant and user ids), subscriptions and history; the reverse
  leaves a frozen pilot with no bot row. *Deferred:* owner-run and rare; the README orders the steps and says why, and
  `list --tenant` tells completed from wrong-pair. *Complete fix:* the bot's daily job, or its startup, lists
  `tg_users` rows whose backend tenant no longer exists (the provisioning door answers 404), runs the same purge, and
  logs the counts.
- **P4 review A M-3: orphans per source keep a zero entry for every chat the person ever had.** Ledger size only; no
  reader is wrong. *Complete fix:* core `_latest` drops a source whose latest count is 0, with one unit case.
- **P4 review A M-5: the replay's owner-connection helpers are the third verbatim copy in `scripts/observability/`.**
  Each copy is tested. *Complete fix:* `_owner_db.py` with `owner_connection(database, application_name)`, the
  argument types and `_BIND_TENANT_SQL`; three imports.
- **P4 review A M-6: "the rows binding" is read three ways, about seven times an attempt.** One predicate, so the
  reads agree. *Complete fix:* the composer hands its binding to the parts (`Part.erase(subject, roster=…, **ids)`,
  `Part.residue(…)`), each part keeping its own read for standalone callers.
- **P4 review A: chat delete's reap builds a Phoenix client per chat** (one version check each), though inside an
  erasure the composer already holds one. Cost only, counted in FI-C's arithmetic. *Complete fix:*
  `reap_chat_copies(scrubbed, phoenix=None)` uses a passed client; the seam passes its own, chat delete keeps
  building one.
- **P4 review A M-7: `phoenix_sessions_deleted` counts the seam's retries only, never the reaps' deletes.** The
  ledger's numbers only; the receipt carries no Phoenix count. *Complete fix:* one key in the reap's answer, summed.
- **P4 review C M-11: one HCL helper is written three times.** `attributes(block)` in iac's
  `test_s3_noncurrent_version_expiry.py`, `test_cognito_user_erasure_policy.py` and
  `test_apprunner_postgres_passwords_by_reference.py`. *Complete fix:* one helper in `tests/_hcl_blocks.py` beside
  `process_env`.
- **Task 17 lane D concern 1: names the shape list leaves out.** No column of the three registries or the two index
  schemas carries one today (scanned twice). The candidates for a future ruling:
  - `assigned_to` and `sub`;
  - `*_user_ids` (for example `mentioned_user_ids`);
  - plurals such as `members`, `participants`, `watchers` and `assignees`;
  - `email_address` and `emails`, which `.*email` misses;
  - `sender*`;
  - `contact*`, which would also force a decision on `tenants`' two contacts (owner question 3).

  *Complete fix:* rule the additions once, in all three lists together. Lane P's row holds them equal.
- **Task 17 lane D concern 5: `chat_feedback__feedback_data`'s residue counts a sibling's effect.** Its residue is
  proven by the statement (like P2's m-8): it counts what the row's id column says, not what the payload holds.
  *Complete fix:* a payload-keyed residue (`feedback_data->>'user_id' = ANY(the person's ids)`), so the count proves
  the scrub's own effect; one db case.
- **The receipt does not name the row-keyed, statement-proven class (lane D fix part B3, concern 4).**
  - Three placements count their residue by the row's id column, which the same statement rewrites:
    `chat_turn_facts__cited_documents`, `chat_feedback__feedback_data`, and since B3 `chat_turn_facts__session_id`.
    So the count cannot see a scrub the statement missed.
  - The receipt names three statement-proven limits (`ledger.py:192-194`), but not this class.
  - *Complete fix:* the receipt names the class in the same change that adds the SDK-transcripts caveat, so core's
    `RECEIPT_KEYS`, the dashboard's contract and copy, and lane P's receipt pin change once. A payload-keyed residue
    (as for `feedback_data` above) removes a placement from the class.
- **The parse-sidecar residue cannot see the content records (Task 18 fix round 2b's review, I-1).**
  - A PDF's parsed text lives in its content record, `parse-sidecars/<tenant>/sha256/<digest>/`, which the upload's
    alias points to. `reap_parse_sidecars` deletes the content records no other alias references, and keeps shared
    ones.
  - `count_parse_sidecars`, the residue, counts only the objects under the person's attachment ids. Once the aliases
    are gone it cannot tell which content records they reached. So a content record the reap missed reads as a zero
    residue, and nothing expires it.
  - The Task 18 script reads the content prefix itself on its live run.
  - *Complete fix:* the reap records the content ids it targets in the ledger before deleting, and the residue
    counts what is left under them, less the shared ones. Or the receipt names it as statement-proven, with the
    class above.
- **A connection string still holds the test database's password (P4 fix round parts D5 and D6).**
  - pytest's default traceback printed `psycopg2.connect`'s `dsn`, password included. D6 set `--tb=short` in every
    repo's `addopts`, pinned. But a command line's own `--tb`, an `-o addopts=…` that drops it, or `-l` still prints
    it.
  - *Complete fix:* a libpq password file (`PGPASSFILE`), so no connection string the estate builds holds a
    password.
- **Settings objects still name secrets in their repr (P4 fix round part D6, concern 3).**
  - utils' seven password fields are `repr=False`. Its AWS secret key, Weaviate key and Azure OpenAI key are not.
    core's and copilot-mro's settings still show their SMTP and cache passwords.
  - *Complete fix:* every secret field in every settings class is `repr=False` (or a `SecretStr`), pinned per repo.
- **Core lines on routes other than the erasure doors name people (P4 fix round part D4, concern 6).** `PUT /users`
  and the role removal log the person's id. *Complete fix:* constant messages with the ids as bound fields, as the
  erasure doors now have.
- **`span_details` resolves routes for traced URLs with no belt of its own (P4 fix round part D5, concern 5).** No
  request can make it raise today. *Complete fix:* the same "any error → the path's shape" belt as
  `RequestRouteMiddleware`.
- **uvicorn's access line names the raw request target in every service but the api gateway (P4 fix round part D3,
  concern 1).**
  - utils' intercept forwards `uvicorn.access` with only URL credentials withheld. The gateway now shapes it with its
    own filter, and deployed, core's and copilot-mro's routes are served through the gateway's mounts.
  - A process that runs uvicorn on its own (core's `python -m core.fastapi_app`, copilot-mro's own app,
    shift-optimizer) still writes raw targets.
  - *Complete fix:* the intercept reduces the target to a route template the app registers a resolver for, or to
    `/:redacted`.

## Lessons

- The post-merge gate must be the whole suite of each repo the batch can affect, not the folders the batch touched.
  P1 added a core router, and copilot-mro's route-table test (its list of core routers) went red. The copilot-mro
  post-merge api lane ran only `tests/api/document_hub`, so the red was pushed twice (P1 and P2) and the router sweep
  never covered the erasure endpoints. The DB-roles review found it. Rule: at a merge, run each affected repo's full
  lanes, including its `tests/api`.
- A bounded wait on a marker that nothing clears is an unbounded erasure: in the scheduler-off deployment a stale
  `claimed` row never closes, so a drain must count only work that can still write (P2 correctness I-1).
- Publishing is not owed while the work is dev-only (P3, owner correction 2026-09-30). The controller kept "publish
  utils 0.1.40, then 0.1.41, before the core and shift-optimizer wheels" on the owner's list. The owner corrected it:
  everything runs from the dev checkouts, and publishing happens once, after all code changes are final. Rule: do not
  list package publishing as owed during the phases; raise it once, when the code is final.
- Seven agents and their lanes at once took the WSL VM down (P3b, 2026-10-01 ~07:06): every lane died, Postgres came
  back on a fresh cluster and Weaviate on an empty schema (the known restart traps), and the owner capped agents at
  4. Rule: at most 4 agents at a time; implementers commit early, because uncommitted work and running lanes die with
  the VM.
- A seam test must not take Phoenix from the environment (Task 15 `45e99261`: the seam's DB and exception-text tests
  now name no Phoenix, whatever the shell exports). The shell may export the keys, and the api's `main` exports
  `api/.env` into the test process on import (P4 review C M-5), so a test that leaves the client to the environment
  builds a real one, and its result depends on the shell and on test order. Rule: every test that reaches a
  Phoenix-reading seam passes its fake in, or declares no Phoenix (`PHOENIX_ENDPOINT=none` under O10); Task 17's census
  too. Since the P4 fix round's part D, both conftests (copilot-mro and api) declare `none` for the whole session; a
  test that needs a Phoenix names one through copilot-mro's settings object.
- A mutant ran on a tree while that tree's full suite was collecting (lane D fix round part B, 2026-10-02): the suite
  failed one test with the mutant's exact signature, and only a re-run alone was green. Rule: never run `mutant.sh` on
  a tree while that tree's suite runs; mutate a scratch extract, or wait for the suite. Every brief says so.

## Implementation notes

**Status at compaction checkpoint 1 (2026-09-27):** P1 in flight, SDD with Opus agents; nothing merged or pushed
(erasure tasks merge into the shared mainlines only after the P1 phase review — the copilot-mro mainline carries the
OD-5 push first). Ledger `/home/aditya/Code/.superpowers/sdd/user-erasure/progress.md` holds every ruling (prefix
`Ruling:`), agent ids and the P1 close sequence. Owner decision 27 (migrate + provision `copilot_mro_test`) blocks the
Task 1/2/5 db proofs.

#### Notes: Task 1 — ledger, registry, vocabulary: CODE-COMPLETE (core `ue-core` `17699d9..9ff3daf`, review APPROVED)
- Rulings that refine the task text: `mode` ∈ {windowed, immediate} + `rtbf` (CHECK rtbf ⇒ immediate; immediate
  without rtbf is the `/goodbye` case); `failed` is resumable (failed → erasing), terminal = {completed, cancelled},
  `failed` stays open in the one-open-request index; `REQUIRED_SEAMS = (copilot_mro, shift_optimizer)` (ruling T1-Q3 reversed at the P1 review: core's own relations are core's step, not a seam);
  steps/receipt jsonb with identifier-pattern keys and int values only; ids and `requested_by` are opaque tokens
  `[A-Za-z0-9_:-]{1,128}`; `prior_status` is an identifier token; `external_id` nullable; the window is enforced in
  the guarded UPDATE (immediate requests never held); `finished_at` only on completed/cancelled.
- Learning: `users.status` is free text a user can write on their own row — anything copied from it into a record
  that outlives the person is a personal-data channel. Root fix routed to Task 2.
- Pending: 14 db proofs (RLS isolation, survival past tenant + user deletion, one open request).

#### Notes: Task 2 — request, freeze, cancel, Cognito: IN REVIEW (same branch `9ff3daf..0365624`)
- Built: routes, freeze/cancel, `cognito_accounts.py`, `users.status` vocabulary {pending, active, inactive} +
  `erasure_pending` written by the erasure service only; a frozen row refuses every PUT.
- Review fix round 1 (rulings T2-I1/M1–M4): cancel only for a windowed request inside its window and only from the
  door that opened it (`via='api'`), one predicate for the ledger guard and the `cancellable` flag; the account's prior
  Cognito state recorded (`prior_cognito_enabled`) so a cancel never revives a pre-disabled account; bounded Cognito
  calls (5 s, 2 attempts) off the event loop; cross-tenant proofs.
- Owed to Task 3 (api): the api applies auth-cache evictions only on 200/201/204 — a 202 eviction is dropped.

#### Notes: Task 4 — `scrub_chat_copies`: DONE (copilot-mro `ue-m1` `e0cdea42..acd32b42`; review APPROVED; db proofs green)
- Behaviour-preserving factor of chat delete's transaction; the only visible change: `delete_chat` answers False when
  the row vanished between the ownership read and the transaction. The facts/feedback anonymisations now key on the
  not-yet-anonymised shape (a rerun changes 0 rows; first-run results byte-identical). The scrub refuses a caller bound
  to another tenant; the reap derives every tenant-scoped key from the scrubbed chat, never the ambient binding.
- Learning: a reap that reads the AMBIENT tenant binding silently reports "0 left" when called under the wrong tenant —
  derive tenancy from the record being erased.

#### Notes: Task 5 — LLM-records definer: CODE-COMPLETE (copilot-mro `ue-m2` `e0cdea42..f5d82ae4`, review APPROVED)
- One postgres-owned SECURITY DEFINER function + a reusable "declared definer" path in `provision_rls.py` (applied in
  phase 2b with owner set, REVOKE ALL FROM PUBLIC and GRANT EXECUTE to `flynapse_grant` in one transaction;
  `--verify-only` reports missing / not definer / unpinned search_path / wrong owner / any extra EXECUTE holder incl.
  WITH GRANT OPTION). The function refuses unless the session's tenant binding equals its tenant argument — callers
  (Task 6) run it on the grant pool inside `db_tenancy(<erased tenant>, …)`. B14 reuses this path.
- Owed: the grant round (no DELETE on `user_erasures` for the app and grant roles) once Task 1's table is on the path;
  the db probe after provisioning.

**Status at compaction checkpoint 2 (2026-09-27, later):** P1 Tasks 1, 2, 4, 5 COMPLETE (db proofs green on the
provisioned `copilot_mro_test`); Task 3 in task review. Then: the P1 phase review (three Opus lenses) → owner pause →
merges → push. Owner decision 27 was taken (yes): the test DB is migrated + provisioned from the erasure branches,
including `REVOKE DELETE ON user_erasures` from the app and grant roles. Known side effect: on branches without the
erasure registry, `tests/db/tenancy/test_schema_conformance.py` shows 4 reds (only `user_erasures` undeclared).

#### Notes: Task 5 addendum — the ledger is never deleted (fix round 2, `2b128dfb`)
- `NO_DELETE_RELATIONS = ("user_erasures",)`: DELETE revoked from the app and grant roles; the app role keeps
  SELECT/INSERT/UPDATE (state transitions); the grant role holds nothing on the ledger; `--verify-only` reports any
  DELETE or a missing app privilege. Core's db tests now clean up as the owner (core `3183c69`).
- Carry into Tasks 11/12: the due sweep and the D12 replay cannot read the ledger through the grant role — decide the
  read path then (owner-run CLI or a scoped grant).

#### Notes: Task 3 — api: DONE (`ue-api` `f616c3b..0d0c626`; review APPROVED; fix round 1 test-only + core prose `05e1e9d`)
- Gateway refuses exactly `erasure_pending` (fixed 403); `pending` unchanged; every 2xx applies its declared auth-cache
  eviction (so core's 202 request evicts); a frozen owner's automations stand down at next fire. Accepted gaps →
  Future Improvements: the run row shows the generic `entitlements_unresolved`; automations stood down during a freeze
  stay off after a cancel.
- Fix round 1 (review M1/M5/M2): prefix-sharing values pinned in both status lists (a `startswith("erasure")` gate now
  goes red); a bind spy proves the refusal precedes the tenancy bind; a tenant-pinned door test; a pin that core's user
  read selects `status`; core's two stale "ignores users.status" sentences reworded. Merge gate: api merges only after
  core (it imports `core.resources.user_erasure`).

**Status at the P1 phase review (2026-09-27):** Tasks 1–5 COMPLETE. Three Opus lenses reviewed all four branches:
correctness 0/1/5, plan-completeness 0/6/8, simplicity 0/0/11 (Critical/Important/Minor). Triage is in the ledger's
"P1 TRIAGE" block. A fix wave with one fresh implementer per lane (core, copilot-mro M1, copilot-mro M2) closes: the
unguarded request doors (a person frozen where no erasure can finish); cancel compensation on a lost enable; the
scrub's session-binding dependency; the scope-guard approval; the third-role census; the sweep keeping the ledger;
`core_local` no longer a seam; and the test-double and vocabulary simplifications. The hand-off gaps (D11 teardown path,
the api-side executing CLI, Cognito delete as the last erasing step, enqueue after commit, the tenant erasure list,
the completion delete on one cursor) are written into Tasks 11–13 above. The D12 off-database replay record needs an
owner ruling. Merges wait for the owner.

**Status at P1 close (2026-09-28):** the P1 fix wave is COMPLETE, and every lane's scoped re-review is clean (0 OPEN).
- core `ue-core` `0d3811d`: seams guard; `REQUIRED_SEAMS` = copilot-mro and shift-optimizer; cancel compensation;
  ledger doubles by function; one vocabulary (DDL byte-identical). The Cognito wrapper fold is deferred (see Future
  Improvements).
- copilot-mro `ue-m1` `834c1653`: the scrub binds its own session; one spelling of `deleted-user`.
- copilot-mro `ue-m2` `6625d70c`: scope-guard approval; third-role census; the sweep keeps the ledger; shared RLS test
  helpers.
- api `ue-api` `0d0c626`: unchanged since its task review.
Merge order is core → copilot-mro (ue-m1, ue-m2) → api. Merges and the push wait for the owner's review.

**Owner review of P1 (2026-09-28):** 29 approve and merge/push; 30 migrate and provision dev `copilot_mro` (done:
snapshot `copilot_mro_20260928T084630Z.dump`, provision and verify clean); 31 no D12 replay, and nothing built for it
(a Future Improvement if backups are introduced; one-off migration snapshots deleted about a week after the migration
is proven); 32 a cancel re-enables the automations the freeze disabled (moved into Task 11); 33 keep `requested` for
now. The owner confirmed that the dashboard (Task 14) is the primary door and the CLI covers only the back office.

**Status at compaction checkpoint 3 (2026-09-28):** P1 is merged locally: core `master` `3f05e5f`, copilot-mro
`langgraph-merge` `82c504e2`, api `langgraph-merge` `8949109`. The push waits for the last post-merge lane
(copilot-mro db). Dev `copilot_mro` is migrated and provisioned. Next: push, clean up the P1 worktrees and branches,
then Phase 2 (Tasks 6–10).

**Status at compaction checkpoint 4 (2026-09-28).**

*Phase 1.* P1 is pushed: core `3f05e5f`, copilot-mro `82c504e2`, api `8949109`. The P1 worktrees are removed.

*Phase 2 (started on the owner's word).*
- **Closed and merged locally, unpushed:**
  - Task 9, core `master` `ae33072`.
  - Task 10, shift-optimizer `main` `ba3c070`.
  - Post-merge lanes are green for both, apart from core's two known environment reds in
    `test_cross_repo_reads_name_their_checkout.py`.
- **In review:**
  - Task 6 (`ue-t6` `12a43886`), in task review.
  - Task 7 (`ue-t7` `db0f2bb4`), where fix round 1 is in scoped re-review.
- **Task 8:** the brief is prepared, and it is dispatched once Tasks 6 and 7 are merged.

*P2 controller rulings, all recorded in the ledger.*
- **R-DELEGATE.** Task 6 places Document Hub and chat columns as delegated to Tasks 7 and 8.
- **R-LEDGER-KEYS.** Every count or residue key a seam or core step emits must fullmatch core's ledger identifier
  pattern. Column placements are spelled `<table>__<column>`, and each seam has a test for this. The Task 10 review
  found dotted keys that the ledger would refuse; Tasks 6 and 7 had the same defect.
- **R-LINKS-LAST (Task 8).**
  - Chat ids and attachment ids are gathered first.
  - The chats are scrubbed one by one.
  - In-flight work is drained, bounded, and fails the step on timeout.
  - The residue is read until zero with the same gathered sets.
  - Only then are `chats` / `chat_blocks` purged and the user prefixes swept.
  - This splits D2's "scrub and purge in one transaction" into a scrub per chat now and a purge at the end.
- **Task 7's fixes.**
  - A private document still mid-processing stays an orphan until DocHub's abandonment cutoff passes, then is purged
    again.
  - A shared document stuck in processing is settled with DocHub's own `mark_processing_failed`.
  - Together these bound the processing hold at about 30 minutes.
- **Task 10's fixes.**
  - The erase is one transaction.
  - The residue is one read-only snapshot.
  - The pool's statement timeout is set explicitly.

*Carried into Task 11.*
- Drain the person's automation runs before core's own step: after the freeze, covering claimed and running runs,
  bounded, and failing the step on timeout.
- Read every residue before the `users` row is deleted.
- Make the re-erase window outlast DocHub's 30-minute hold.
- Put no person id in the one-shot's params.
- Have the receipt name downloaded exports as out of reach.

*Carried into Task 18.* Read the memory index after a live erasure, because clearing a Weaviate property with a null is
unproven by the fakes.

*Owner questions for the P2 phase review (six; wording from the P2 plan-completeness review).*
1. **Private comments.** A private comment is readable only by its author and by tenant admins
   (`core/resources/comments/services/comment_service.py:807-813`). The erasure keeps its text and sets the author to
   `deleted-user`, "Deleted user", no email, so afterwards only admins can read it. Private Document Hub documents, the
   nearest case, are deleted (D7). Keep as built, or delete private comments too (one predicate in the
   `comment_authors` step, plus a pin)?
2. **Optimizer job name and notes.** `optimizer_jobs.name` and `notes` are what the person typed when creating the job.
   They stay with the job; only `created_by` / `launched_by` become `deleted-user`. No other optimizer field names the
   person (the configs come from settings documents, and `error` is solver or fixed text). Keep as built?
3. **Text that names the person without an id.** The erasure finds a person only by their ids, so these stay and are
   not counted: `tenants.primary_contact` / `secondary_contact` (jsonb, set by tenant admins) when the person is the
   contact; a colleague's comment "@Ada"; another member's automation prompt; memory notes and facts (kept verbatim
   under D1); optimizer job notes; `ad_fleet_applicability.review_note` (D9). Accept as a limit stated in the receipt?
   (A contact scrub would match the `users` row's email inside SQL, as Task 6 does for reviewers.)
4. **Orphan-operator rows.** When an operator is deleted (`DELETE /operators/{id}`), its notification and subscription
   rows stay behind, invisible to every app-role binding. So do copilot-mro's tenant+operator relations: private
   Document Hub rows, memory items and events, and their index chunks. The erasure cannot delete or count them, so the
   residue reads 0 over them. Closing it needs DDL: a postgres-owned definer that erases by (tenant, user) across
   operators, or `delete_operator` sweeping its own rows (the root fix). Name it in the receipt now, and put the fix in
   Future Improvements?
5. **A chat stream open at the freeze.** The freeze refuses new requests only. A stream already open runs on with no
   deadline (`TurnContext.deadline` is never assigned; about 19 minutes worst case per governed call). Chat-keyed
   copies it writes after the seam's last check (agent state, DataViews, parse sidecars, owner-less digests, user-less
   turn content) cannot be found afterwards, because the purge removed the chat ids. Only immediate requests are
   exposed — RTBF requests and every `/goodbye` (Task 13 runs the channel user's erasure immediately); the 7-day
   window outlasts any stream. A chat-file upload's durable S3 object is also written by a detached background task
   (up to 4 retries) under the person's own prefix, so it too can land after the sweep, and a turn deadline alone
   does not bound it. Recommended: a hard interactive-turn deadline plus a bound on that upload task, and immediate
   requests erase after freeze + the larger bound ("immediately" becomes "after the bound"). Alternatives: gate the
   chat-keyed writers on chat liveness (rows only, not S3 objects), or a durable open-turn row (DDL).
6. **Invitations the person sent.** A pending invitation the erased person sent stays redeemable until it expires
   (7 days by default; a resend renews it), with the inviter shown as `deleted-user`. D10 says "pending invitations
   deleted"; R-PLACEMENTS says the inviter becomes `deleted-user`, which is what was built. Should an invitation an
   erased admin minted survive the erasure? Recommended (controller): revoke the pending, unaccepted invitations the
   erased person sent. That is one predicate in the delete step (a pending invitation whose `invited_by` is either
   id), the pin, and one fixture assertion.

*Owner answers (2026-09-29).*
1. Private comments: keep as built.
2. Optimizer job name and notes: keep as built.
3. Text naming the person without an id: a limit stated in the receipt. (Task 17 lane D review, 2026-10-01:
   `operators.airline_details`, admin-typed free JSON from a raw textarea, is of the same class as `tenants`' contacts;
   the receipt's limit covers it.)
4. Orphan-operator rows: the root fix — Task 19 (deleting an operator deletes its rows, plus a one-off owner-run
   clean-up of existing orphans); the receipt names the gap until it lands.
5. A stream open at the freeze: the cheap version, in Task 11 — immediate erasures run 30 minutes after the freeze,
   interactive turns get a hard deadline under that, and the detached chat-file upload a bound under it.
6. Invitations the person sent: revoke the pending, unaccepted ones (built in the core P2 follow-up round).
- Proposals: FI-S1 adopted (Task 11 owns the only drain and re-erase loop); FI-S2 adopted, with every simplicity
  Minor and the redundant tests, as a P2 simplification batch built now.

**Status at compaction checkpoint 5 (2026-09-28, late).**

*Phase 2: all done except Task 8. Everything is merged LOCALLY and nothing from P2 is pushed.*
- **Task 9:** core `master` `ae33072`.
- **Task 10:** shift-optimizer `main` `ba3c070`.
- **Task 6:** copilot-mro `langgraph-merge` `7eff5fac` (branch tip `01aa8145`). Approved after 2 fix rounds.
- **Task 7:** `21ff2d66` (branch tip `14618f67`). Approved after 3 fix rounds.
- **Post-merge at `21ff2d66`:** unit 7961 passed, 0 failed; db `user_erasure` + `chat_history` + `document_hub` 94
  passed; api `document_hub` 273 passed.
- **Task 8** is in flight on `ue-t8`, cut at `21ff2d66`.
- The copilot-mro mainline's pushed tip is the eval batch's `925c716d`. The two P2 merges sit on top of it, locally only.

*Rulings added since checkpoint 4 (the ledger and `p2-context.md` hold the detail).*
- **R-PARTIAL-COUNTS.**
  - Core's ledger replaces a step's counts, and a rerun is keyed on the not-yet-erased shape.
  - So any exception a seam raises after a commit carries `partial`: a `SeamErasure` holding what that attempt committed.
  - Composers sum their parts' partials and re-raise with the sum. Task 11 sums a step's counts across attempts.
  - **Addendum:** the counts are exact at page grain. Paginated helpers take an optional per-page callback, which
    defaults to off, so their other callers are unchanged.
- **Task 7's liveness is bound to the attempt it judged.** A document whose attempt changed during the pass is held,
  counted as an orphan, and left to the rerun.
- **Task 6.**
  - Compaction digests of the person's chats are deleted by chat.
  - A chat-share recipient's email is scrubbed.
  - The statement ceiling comes from the pool setting.
- **Test-run economy** (owner). Implementers run targeted tests while they work and each full lane once per round.
  Baselines come from the controller's post-merge logs (see `test-lane-speed.md`).

*New Future Improvements, to write into the section above at P2 close.*
- **Task 7 M-5:** after a failure part-way through a re-key, the retry splits its counts differently; the total stays
  exact.
- **Task 7 M-7:** an attempt that was queued long ago and begins between the listing and the read gets settled. The
  executor's re-read fences it.
- **Task 6 N-3:** two raises after the guard can never be reached.
- **Task 7 M-3** (FI-6): the owner id in the re-keyed copies' object metadata.

*Carried into Task 11, in addition to checkpoint 4's list.*
- Sum each step's counts across attempts, including every failed attempt's `partial`.
- The receipt's "what may remain" names these:
  - inline or zombie DocHub executors that can outlive the declared bound (Task 7 N-2);
  - an `updated_at` PATCH extending the hold on a queued shared attempt (Task 7 N-3);
  - the attempt-start window (Task 7 M-7).

*Next.* Task 8's report, then its task review and fix loop, then its merge and post-merge lanes. Then the P2 phase
review (three Opus lenses), triage, and the OWNER PAUSE with the six questions above. Then push core, shift-optimizer
and copilot-mro P2, and remove the P2 worktrees and branches. Then P3.

#### Notes: Task 6 — user-grain rows: DONE (copilot-mro `ue-t6` `9402ab66..01aa8145`, merged `7eff5fac`; review APPROVED after 2 fix rounds)
- `erase_user_copies(subject, *, chat_ids) -> SeamErasure` and `user_copies_residue(subject, *, chat_ids)`. 46
  placements (42 Postgres, 4 Weaviate). One txn under the full roster, then the definer on the grant pool, then the
  memory index brought into line from its own naming read.
- Rulings: R-DELEGATE; R-LEDGER-KEYS; R-PARTIAL-COUNTS; compaction digests of the person's chats deleted by chat (I-1);
  a colleague's share addressed to the person loses `share_data.email` (I-4); the ceiling comes from
  `POSTGRES_STATEMENT_TIMEOUT_MS`.
- Learning: an owner-keyed DELETE misses rows whose owner is optional; key the erase on what chat delete keys on.

#### Notes: Task 7 — Document Hub: DONE (`ue-t7` `9402ab66..14618f67`, merged `21ff2d66`; APPROVED after 3 fix rounds)
- `erase_document_hub_user` / `document_hub_user_residue` (`*, attachment_ids=()`), `reap_parse_sidecars`,
  `count_parse_sidecars`. Rows hard-deleted; shared documents re-keyed copy → re-own chunks → rewrite row → delete old;
  the user-prefix sweep runs only once no row is owned.
- Rulings: liveness is DocHub's `abandonment_cutoff`, bound to the attempt judged (N-1); a live private doc is purged
  and its row held as an orphan; a stuck shared doc is settled with `mark_processing_failed`; page-grain partial
  counts via optional `on_page` callbacks on the existing helpers (I-6).
- Learning: a hold with no bound is not a hold; bind it to DocHub's own cutoff.

#### Notes: Task 8 — the seam composer: DONE (`ue-t8` `21ff2d66..493d06fe`, merged `65aadf0a`; APPROVED after 3 fix rounds)
- `erase_user(subject) -> SeamErasure` and `user_residue(subject) -> Dict[str, int]`: Task 12 registers them as the
  `copilot_mro` seam. R-LINKS-LAST: gather → Task 6 → per chat → Task 7 → drain (60 s) → residue loop (2 re-erases)
  → purge → sweep → residue.
- Fixes: the purge guards pinned (I-1); the chat-grain residue arms restated from chat delete's statements and pinned
  per statement (m-3, n-1); the findings arm reads `(finding id, md5(entry))` computed in SQL, so the person's words
  never leave Postgres (n-3).
- Learning: a residue re-derived from links sees nothing once the links are gone; read it before the purge, with the
  same gathered ids.

#### Notes: Task 9 — core's own rows: DONE (core `ue-t9` `3f05e5f..4acddc3`, merged `ae33072`; APPROVED after 1 test-only fix round)
- `core_copies.erase_core_copies(subject) -> SeamErasure` and `core_copies_residue(subject) -> {step: n}`, over 13
  steps. They are bound to the tenant's full roster, match both ids, and run in one transaction. The residue runs READ
  ONLY and is rolled back. Nothing is registered.
- The line places 40 columns: 7 delete, 12 scrub, 14 keep, 7 delegated. The drift guard is registry-derived, with
  core's `external_id` added to the pattern.
- Rulings:
  - redeemed invitations are deleted (redemption requires the invited address);
  - "their runs" are de-attributed through `entitlements_used.user_id`;
  - payload de-attribution is generic, matching any JSON string equal to an id;
  - `DELETED_USER_ID` moved into `user_erasure`, and `quality.py` imports it.
- Owed to the owner: private comments are kept (D10 literal); tenant contact jsonb and free text are not id-keyed.
- Owed to Task 11: drain the person's in-flight automation runs before this step; run the residue before the `users`
  delete; keep ids out of the job's params.
- Sent pending invitations stay redeemable: owner question 6.

#### Notes: Task 10 — shift-optimizer: DONE (`ue-t10` `f86c6c5..02e3fdd`, merged `ba3c070`; APPROVED after 2 fix rounds)
- `erase(subject) -> Dict[str, int]` and `residue(subject) -> Dict[str, int]`, structural subject, keys
  `optimizer_jobs__created_by` / `optimizer_runs__launched_by`; one transaction; a REPEATABLE READ READ ONLY residue
  snapshot; `SET LOCAL statement_timeout` from the pool setting.
- Rulings: dotted keys refused by core's ledger → R-LEDGER-KEYS (I-1); one transaction (I-2); free-text name/notes/error
  kept (owner question 2); downloaded workbooks are out of reach (receipt).

**Status at the P2 phase review (2026-09-28, night).** P2 Tasks 6–10 are COMPLETE and merged locally; nothing from P2
is pushed.
- core `master` `ae33072` (T9); pushed tip `3f05e5f`.
- shift-optimizer `main` `ba3c070` (T10); pushed tip `f86c6c5` (the remote is named `main`: push with
  `git push main main`).
- copilot-mro `langgraph-merge` `65aadf0a`: T6 `7eff5fac`, T7 `21ff2d66`, the lang_agent flake fix `81a4b93a`
  (test-only, rides with the push), T8 `65aadf0a`; pushed tip `925c716d`.
- Post-merge lanes at those tips: copilot-mro unit 7995 passed / 10 skipped, db 103 passed, api 273 passed; core db
  exit 0, unit+api exit 1 (only the two known environment reds); shift-optimizer non-db 1091 passed, db 157 passed /
  1 skipped.
- Worktrees still present: `copilot-mro-erase` (now `ue-p2fix`, the P2 fix batch), `copilot-mro-erase-b` (`ue-t7`),
  `core-erase` (now `ue-p2fix`), `shift-optimizer-erase` (`ue-t10`); branches `ue-t6` … `ue-t10` and the two
  `ue-p2fix` to delete with `-d` at P2 close.
- P2 phase review (three Opus lenses, 2026-09-28): correctness 0C/1I/7M, plan-completeness 0C/2I/6M, simplicity
  0C/1I/13M. Being fixed before the push (two batches in flight): correctness I-1 (the drain waits only for runs that can still write), M-3 (no key
  or prefix text in exceptions), M-6 (the re-key's metadata write is compare-and-set), M-7 (latest-orphans pinned) in
  copilot-mro; simplicity S-I1 / correctness M-1 (statement ceiling) and correctness M-2 (the email stays in SQL) in
  core. Carried into P3's task text: completeness I-2 (Task 12 adapter), M-1, M-3, M-4; correctness M-4, M-5.
  Fix-batch SHAs to be added at merge.
- Next: the two P2 fix batches' reviews and merges → the owner pause (six questions, plus proposals FI-S1 and FI-S2)
  → push → P3. The P2 Future Improvements are written into the section above.

**Status at compaction checkpoint 6 (2026-09-29).** The owner answered the P2 pause (answers above). Nothing from P2 is
pushed yet.
- Fix batches built, in review: core `core-erase` `ue-p2fix` `ae33072..07c9dbe` (statement ceiling; the person's email
  stays in SQL); copilot-mro `copilot-mro-erase` `ue-p2fix` `65aadf0a..af579223` (drain counts only runs that can
  still write; no key or id text in exceptions; compare-and-set re-key; latest-orphans pinned).
- copilot-mro `langgraph-merge` is now `289ac1d6` (the owner-approved `open-items.md` commit on top of `65aadf0a`).
- Next, in order:
  1. each fix batch's review → fix loop → merge `--no-ff` → post-merge lanes;
  2. the P2 push (core `master`, shift-optimizer `main` via `git push main main`, copilot-mro `langgraph-merge`,
     with utils `47b125f`) — the owner pause is answered, so the push follows the two merges;
  3. a core follow-up round (owner question 6 plus the core and shift-optimizer consistency Minors), and the
     copilot-mro simplification batch (FI-S1, FI-S2, every simplicity Minor, the redundant tests), each reviewed and
     merged;
  4. P2 close: remove `copilot-mro-erase-b` and `shift-optimizer-erase`, delete `ue-t6` … `ue-t10` with `-d`;
  5. the DB-roles batch (owner decisions 22–26, all yes: `docs/plans/db-roles-consolidation.md`), then P3.

**P2 PUSHED (2026-09-29).** Both fix batches were reviewed, merged and gated post-merge, then pushed:
- **core `master` `3f05e5f..1fedf7e`:** fix merge `1fedf7e` (fix round 1 added the sibling-own-address pin and a
  one-row `=` address lookup).
  - Post-merge: unit+api 3887 passed, 1 environmental red; db 93 passed.
- **shift-optimizer `main` `f86c6c5..ba3c070`.**
- **copilot-mro `langgraph-merge` `925c716d..fccd7b6f`:** fix merge `fccd7b6f` after 2 fix rounds. Round 1 restored
  the drain query's index (1.9 s → 2 ms at 200k runs) and made the compare-and-set and latest-orphans tests prove
  behaviour. Round 2 tightened both.
  - Post-merge: unit 8004 passed, db 105, api 273.
- **utils `langgraph-merge` `57c913a`,** pushed with the owner's CLAUDE.md commits.

Carried from the fix reviews: Task 11 gets "latest orphans per source, not only the last pass" (re-review 2 R2-1).

In flight, all branched after the push:
- the core follow-up round `ue-p2c2` (core, shift-optimizer, utils; in review);
- the copilot-mro simplification batch `ue-p2simp`, built on `ue-p2c2`. `ErasureSubject` now validates itself, which
  breaks three copilot-mro tests that the batch rewrites, so the two merge together.
- P3 prep is done: 26 plan conflicts with proposed rulings, and a Task 19 spec with 6 owner questions (workspace
  `p3-prep.md`). They are written into Tasks 11–14 and 19 after the owner answers.

**Status at compaction checkpoint 7 (2026-09-29, paused for the owner's WSL restart).**
- **Core follow-up round `ue-p2c2`: APPROVED** (review, one fix round, re-review OPEN 0), held unmerged.
  - Tips: core-erase `c9035f3`, utils-erase `d2b3f35` (utils 0.1.40), shift-optimizer-erase `15f811d`.
  - Contents:
    - owner question 6: pending invitations the person sent are deleted, expired ones included;
    - one `bound_transaction` per repo over a public utils `apply_transaction_context`;
    - `ErasureSubject` validates itself;
    - `<table>__<column>` keys with every split half suffixed, and `de-attribute`;
    - READ COMMITTED residue with `fetchone`;
    - the end-to-end lock-wait ceiling test kept;
    - the freeze binds its own tenant, pinned;
    - a utils `>=0.1.40` floor on core and shift-optimizer.
  - Carried to Task 11: a freeze queued behind another in the same tenant is cancelled at the 15 s ceiling, and Task
    11 answers that cleanly (m-6).
- **copilot-mro simplification batch `ue-p2simp` @ `f06ddd18`: built, review to restart.**
  - Size: production net −346 lines, tests net −1,184.
  - FI-S1: one pass, no drain or re-erase; a non-zero residue raises and never purges.
  - FI-S2, and every copilot-mro simplicity Minor except S-M9's remaining fakes.
  - The route-table fix: the erasure router has joined the sweep, which found nothing on the erasure endpoints.
  - Merge plan once its review passes:
    1. `--no-ff` merges, in order: utils → core → shift-optimizer → copilot-mro.
    2. A metadata-only `poetry.lock` refresh in api and copilot-mro.
    3. The post-merge gate on the full suites (definition pending with the owner; `test-lane-speed.md`).
    4. The push.
    5. P2 close: remove the P2 worktrees; delete `ue-t6` … `ue-t10`, `ue-p2fix`, `ue-p2c2` and `ue-p2simp` with `-d`.
- **Owner questions from P3 prep (open):**
  - **C-4:** `/goodbye` takes the job path (lock, reply, erase 30 minutes later). Recommended yes. **Owner: yes
    (2026-09-29).**
  - **C-5:** cancel restores nothing, because a frozen owner's automation runs are recorded skipped and nothing is
    disabled. Recommended yes. **Owner: yes (2026-09-29): simpler, nothing to record or restore.**
  - **Task 19 Q1:** all 57 operator-keyed tables, derived from the registries. Recommended. **Owner: yes.**
  - **Task 19 Q2:** clean-up inside the request, paged. Recommended. **Owner: yes.**
  - **Task 19 Q3:** the orphan script runs on `copilot_mro_test` and `copilot_mro`, dry run by default, and executes
    only with the dry run's `--expect-rows`. Recommended. **Owner: yes.**
  - **Task 19 Q4:** find the orphans as the owner, delete them through the registered clean-up. Recommended. **Owner:
    yes.**
  - **Task 19 Q5:** the operator's DocHub raw backups are deleted too. Recommended. **Owner: yes.**
  - **Task 19 Q6:** one audit event per orphan pair. Recommended. **Owner: yes.**
  - **All eight answered (2026-09-29).** Next: a plan-update agent writes `p3-prep.md`'s rulings and these answers
    into Tasks 11–14 and 19; then P3.
- **Found in pushed code:** four copilot-mro api tests error only under xdist
  (`tests/api/tenancy/test_operator_grain_isolation.py`; they pass serially). This is pre-existing. The open-items
  register entry is pending the owner's yes.

**P2 CLOSED: follow-up round and simplification batch PUSHED (2026-09-29).**
- **The simplification batch's review:**
  - The review found one Important issue: dropping a byte-identity pin had also dropped the only pin on Task 6's own
    person signal set.
  - Fix round 1 pinned it by behaviour: the person's feedback on a colleague's chat. It also added the key-check and
    index read-back pins.
  - The re-review found one pre-existing Minor: the two signal residue arms were unpinned for "any chat". Fix round 2
    pinned both at their exact count.
  - The fix rounds went to fresh implementers under the 500k-token cap.
- **Merged `--no-ff` and pushed:**

  | Repo | Branch | Range | Merge commit |
  |---|---|---|---|
  | utils | `langgraph-merge` | `57c913a..508a3ea` | `ue-p2c2` (0.1.40) |
  | core | `master` | `1fedf7e..efb8e8f` | `ue-p2c2` |
  | shift-optimizer | `main` | `ba3c070..9d53254` | `ue-p2c2` |
  | copilot-mro | `langgraph-merge` | `fccd7b6f..4518c642` | `ue-p2simp`, plus the lock refresh |
  | api | `langgraph-merge` | `8949109..fd8e35f` | the lock refresh only |

  - api's lock changed by hand, the utils version line only. A full `poetry lock` also dropped an unrelated
    `prometheus-client` entry; that is existing drift, left out.
- **Post-merge gate: the first real full suites.** Every test folder ran except e2e and the live-service markers. db
  lanes ran serially, and each copilot-mro `tests/db` subfolder ran on its own. The merge added no red.
  - utils: 2036 passed, plus 6 sibling-worktree census reds (environmental).
  - core: 4003 passed, plus 1 census red; db and authz 997 passed.
  - shift-optimizer: 1089 non-db passed, db 157 passed. The solver performance test failed at load around 30; the
    solver is untouched by the merge.
  - copilot-mro: 14891 non-db passed, and every db subfolder passed. There were 14 failures and 4 errors, all
    pre-existing:
    - `tests/config/settings/test_config.py` (3) and `tests/parsers/pilot/test_parser_metadata_sidecars.py` (1) fail
      at the pushed base too. They sit in folders that no earlier gate ran.
    - `test_debug_dumps.py` (10), `test_lang_sad_activation.py` (1) and the two `test_chat_turn_facts_*` collection
      errors pass when run alone. They are cross-test pollution in a whole-tree run. The collection errors come from
      a `_workspace` module-name collision between copilot-mro's and core's `scripts/`.
    - The route-table red is gone.
- **P2 close:** the five P2 worktrees are removed, and `ue-t6` … `ue-t10`, `ue-p2fix`, `ue-p2c2` and `ue-p2simp` are
  deleted with `-d`.
- `core_copies.py:9` (a 125-character docstring line) is left for the next core change.
- **Release note for the owner:** publish utils 0.1.40 before any core or shift-optimizer wheel. Their `>=0.1.40`
  floor sits on the commented codeartifact line.
- **Next:** P3 waits on the owner's answers to C-4, C-5 and Task 19 Q1–Q6, above.
- **P3 plan updated (2026-09-29).** The eight owner answers (C-4, C-5, Task 19 Q1–Q6) and the 24 adopted P3-prep
  rulings are in the task text: Tasks 11, 11b (new, copilot-mro), 12, 13, 14 and 19; R-WINDOW, R-DOOR and R-VERIFY;
  the Phases table; Deploy/rollout. A `C-n` in the task text names `p3-prep.md`'s conflict register; where each one
  landed is in `p3-plan-update-report.md` (both in the SDD directory). P3 is ready to start.
- **P3 plan review applied (2026-09-29).** The adversarial plan review (`p3-plan-review.md`: CR-1, IM-1 … IM-9, 16
  Minors, the pre-flight tables and the recommended order) is in the task text, under the controller's rulings. A
  "P3 plan review X" tag names its finding; where each one landed is in `p3-plan-fix-report.md` (both in the SDD
  directory). The dispatch and merge order is under Phases.

**Status at compaction checkpoint 9 (2026-09-30): P3 in progress.**
- **Task 19, core half: MERGED and PUSHED** (core `master` `33293ed`; the reds batch's `badd671` sits on top). The row
  seams run under the deleted operator's own `(t, (o,))` binding; core's step is on the delete's cursor and self-bound
  for the script; residue non-zero only under `held_documents` still removes the partitions. One review, two fix
  rounds, a re-review. Until Task 19's api registration, `DELETE /operators/{id}` answers 503 on dev (accepted, MI-9).
- **Task 11: built, reviewed by two lenses, one fix round done; scoped re-review in flight** (branch `ue-t11` in
  `core-erase`, tip `9dc0466`). The Cognito rule was corrected: keep the account only when its claim names an existing
  tenant other than this one. `loki_days` became `logs_days`. Its hand-offs to Tasks 11b and 12 are in their task text.
- **Task 19, copilot-mro half (lane M1): building** (branch `ue-t19-mro` in `copilot-mro-erase`). After it merges, the
  owner runs the orphan script on dev `copilot_mro` (dry run, then `--execute --expect-rows N`) before Task 12 merges.
- Next: merge Task 11 → wave 3 (Task 12 in lane A, Task 14 + Task 19's dashboard copy in lane D, Task 11b in lane M1).

**Status at compaction checkpoint 10 (2026-09-30, late): P3 wave 3 in progress.**
- **Task 11: MERGED and PUSHED** (core `master` `2ec64b5`). A re-review, then a second small fix round (a test of the
  real per-request lock, the freeze's narrowed flag, the lookup-failure direction, a pinned clock). The full
  post-merge gate showed nothing caused by Task 11.
- **Task 19, copilot-mro half: reviewed by area, one fix round, re-reviewed; MERGED locally** (copilot-mro
  `5f98c9d3`), full gate running, pushed when green. A Document Hub failure fails the pre-pass again (502, operator
  kept); the orphan script shows every pair (a partitions-only pair included), tells held from failed, refuses an
  unknown `--tenant`, and records a failed partition removal. Then the owner runs the orphan script on dev.
- **Task 12: reviewed, one fix round; ready.** It merges after the owner's dev orphan run and the owner's read-only
  stand-down check (dev's scheduler runs `embedded`, so the plan's "unset everywhere" premise was false). Whether it
  waits for Task 11b's refusal marker is ruled at its merge.
- **Task 11b (lane M1) and Task 14 with Task 19's dashboard copy (lane D): building.**
- Next: wave 4 — Task 13 (core + telegram-bot), Task 19's api registration.

**Status at compaction checkpoint 11 (2026-09-30, night): P3 fully built; the merge queue is running.**
- **Pushed:** Task 19's core half, Task 11, Task 19's copilot-mro half (copilot-mro `5f98c9d3`), Task 11b (`d3301c3a`;
  interactive turns and uploads bounded under the 30-minute delay; the SDK's post-loop fuse, judge and settle under the
  deadline too; copilot-mro refusals carry core's marker). Task 11b merged BEFORE Task 12 (the plan only requires it
  to land no later).
- **The owner's dev steps are done:** the orphan-operator census on `copilot_mro` found 0 rows (59 tables, no
  `--execute` needed), and the Task 12 stand-down check returned 0 rows.
- **Merged locally, gates running:** Task 12 (api `9a15ecb`, full estate gate) and Task 14 with Task 19's dashboard copy
  (dashboard `3f5fa51`; typecheck and lint pass, unit suite running). Each is pushed when its gate shows only the known
  reds.
- **Ready, in merge order:** Task 19's api registration (`api-erase-b`, `ue-t19-api` `458bbfe`, built on `ue-t12`; it
  also passes `interactive=False` from the automation executor and names Task 13's stranded-request log line in the
  CLI help) → Task 13's bot side (`telegram-bot-erase`, `ue-t13-bot` `6085886`; every pilot-facing sentence true on
  both cores) → Task 13's core side (`core-erase`, `ue-t13-core` `52fb9da`; the door answers 202 and step 6 tears the
  channel tenant down; a stranded request logs one fixed ERROR naming its finisher).
- **Rulings since checkpoint 10:** Task 14's eight Minors fixed; Task 11b's SDK tail bounded; Task 13's interface
  pinned between the lanes (the 202 body `{request_id, state, erase_after}` and the deletion-in-progress 409 sentence);
  the tenant-delete event of a personal tenant carries no name (Global constraints). New Future Improvements: the
  stranded `/goodbye` request's root fix (after DB-roles step 6), Task 11b's late-anchored bounds, the dashboard's
  closed states, channel provisioning's log lines, the analytics quality-contract test.
- **Next:** finish the queue (each merge gated, then pushed), then the P3 phase-level review (three Opus lenses:
  correctness, plan-completeness, simplicity) → triage → the owner's review pause → P4 (Tasks 15, 16).

**P3 phase review (2026-09-30).** P3 was too big for three whole-diff lenses, so five Opus reviewers, read-only, took
one area each. It started before the last two merges: Task 19's api registration and Task 13's core side are reviewed
and accepted, and wait in the merge queue. The reviews are `p3-review-A.md` … `p3-review-E.md`, triaged in
`p3-triage.md` (both in the SDD directory).

| Review | Area | Critical / Important / Minor |
|---|---|---|
| A | the erasure run end to end (Tasks 11, 12) | 0 / 0 / 2 |
| B | the operator delete (Task 19, every half) | 0 / 1 / 3 |
| C | `/goodbye` and the bounded turns (Tasks 13, 11b) | 0 / 1 / 5 |
| D | the dashboard (Task 14) | 0 / 0 / 5 |
| E | the phase as a whole (plan-completeness, simplicity) | 0 / 1 / 7 |
| | **Total** | **0 / 3 / 22** |

- *Controller probes.*
  - P-1 (review D M-4), on `copilot_mro_test`: `jsonb` does not keep the receipt's key order. CONFIRMED.
  - P-B1 (review B I-1), in a detached copilot-mro worktree at `58f05103`: under the user erasure's live roster, the
    person's document under a deleted operator counts 0, while the owner connection counts 1. CONFIRMED.
  - C-2, the live Weaviate Document Hub isolation test that Task 19's copilot-mro half edited and nobody had run: 8
    passed.
  - C-1, Task 19's api registration with Task 13's core side on the database: covered by their merge gates.
  - C-3, real turn lengths against the 15-minute deadline on dev `copilot_mro`: the owner's to run (the protected
    database).
  - Review C's hand-over check, the live bot running lane T before lane C serves, was already met: the bot was
    restarted on `8865fb3`.
- *Being fixed now, by fresh Opus implementers, one per repo.*
  - telegram-bot: the new log line that ties the Telegram id to the request id (C M-2), and a check of every log line
    lane T added for personal data.
  - dashboard: the operators list re-read after a 404 or 409 on delete (B M-3); a repeat request over an `erasing` or
    `failed` one says where it stands, not a past date (D M-1); a `frozen` request past its date no longer reads
    "begins after <past date>" (D M-2); receipt lines in the contract's fixed order, not `jsonb`'s (D M-4); copy for
    `owner_erasure_pending` (E M-4); the confirmation states the ruled keep rule (the account's company claim names
    another existing tenant), not "also belongs to another organisation".
  - core, after Task 13's core side merges: one coherent answer when a held-only residue's partition removal fails,
    not two contradictory warnings (B M-1); step 6's partition-failure line names the Document Hub bucket and stored
    credentials sweep and their remedy (C M-1); a refused `/goodbye` logs at ERROR (C M-3); step 6 re-checks a
    personal channel tenant before the delete (C M-4); the stale `ledger.py` comment that the job resumes a refused
    request (E M-6).
  - This plan: Task 17's wire-contract pins (E I-1, with C M-5 and E M-5); Task 11's two residuals and lane C's
    concerns 3 and 4 as Future Improvements (E M-1, E M-2); P3 recorded as built (E M-7); every other finding the
    triage deferred, as a Future Improvement.
- *Owner questions, OPEN (asked at the P3 pause; none is decided).*

  | # | Question | Options | Recommended |
  |---|---|---|---|
  | O1 | A user erasure cannot see its person's rows under a DELETED operator (review B I-1, probe P-B1): held Document Hub rows, a failed post-pass, the eviction window. It completes with residue 0, and the receipt says nothing. | (a) the erasure's Postgres binding adds the tenant's deleted operators (the orphan script's predicate), while Weaviate stays on the live roster; (b) restore a receipt limit key for orphan-operator rows. Either way, the scheduled orphan pass widens to every orphan pair. | (a) |
  | O2 | No supported way to erase a Telegram pilot who cannot send `/goodbye` (review C I-1): the CLI refuses the personal tenant's last owner and cannot write the teardown token, and a hand-made door call leaves the bot's `tg_*` rows. | (a) a CLI `request --channel-teardown` through the teardown entry, which checks for a channel tenant, with the bot's `tg_*` rows purged on the job path; (b) a documented manual call to the channel door. | (a) |
  | O3 | A platform legal (RTBF) escalation of a tenant-opened request is audited as the tenant admin's: the completion event names their requester and `via = api` (review A M-2). | (a) the escalation writes its own audit event, a second row beside D5's one; (b) a cross-door escalation is refused with its own 409. | (a) |
  | O4 | Erase is offered on the admin's own row: they are locked out at once, and the promised cancel is someone else's (review D M-3). | (a) hide it on your own row; (b) keep it, and the confirmation says another administrator or the owner can cancel. | (a) |
  | O5 | May a Phoenix leftover block completion? Task 15's text implies it does: its residue joins the seam's (review E). | (a) yes, Task 15's sweep joins the residue; (b) no, a receipt limit, with the 30-day bound as the backstop. | (a), as Task 15 reads |
  | O6 | The account-less channel tenant (lane C review concern 3) and the 409 wording for a platform-opened erasure (concern 4) (reviews E M-2, C). | record both as Future Improvements, since both are unreachable while the last-owner refusal holds | record them (written as Future Improvements, pending this answer) |
  | O7 | Task 18's live legs (review E, D M-5): only the CLI's immediate path is driven live. | add a dashboard leg (request, cancel, complete, read the receipt), a channel-door leg and an operator-delete leg | add all three |
  | O8 | A `/goodbye` pilot cannot reach their receipt: the channel tenant and its admins are gone at completion, and only the owner's CLI `list` reads it (review E). | (a) accept as a stated limit (the receipt is the owner's, on request); (b) the bot says so | (a) |
  | O9 | Receipt wording (Task 14 review, ledger): `limit_dochub_attempt_start_window` describes a side effect; "its servers" in `limit_host_sdk_transcripts` can read as a vendor's; the "Kept" line has no D3 clause; `s3_noncurrent_days` holds only once Task 16's lifecycle rule is applied. | bring to the owner's wording pass | the owner's wording pass |

- **Next:** merge Task 19's api registration, then Task 13's core side (each gated, then pushed); land the three fix
  batches; then the owner's review pause with O1–O9; then P4 (Tasks 15, 16).

**Owner rulings on the P3 pause (2026-10-01).** P3 is merged and pushed with every review fix (core `7c8c9a9`, api
`f229ce1`, copilot-mro `58f05103`, dashboard `6e11bef`, telegram-bot `7233180`).
- O1: (a), the erasure reaches the person's rows under the tenant's deleted operators (Task 20 F1).
- O2: (a), an owner-CLI channel-teardown request, plus a bot owner command for the pilot's own rows (Task 20 F2).
- O3: (a), a platform legal upgrade writes its own audit event (Task 20 F3).
- O4: hide Erase on your own row (Task 20 F4).
- O5: yes, a Phoenix leftover blocks completion (Task 15).
- O6: record both for later (they stay unreachable while a pilot can only be erased through the teardown, which F2 keeps). The delay stays a code constant (owner, 2026-10-01).
- O7: record all three live legs for the live testing (Task 18).
- O8: accepted as a stated limit: a `/goodbye` pilot's receipt is the owner's, sent on request.
- O9: keep the agent-drafted wording.
- The bot keeps logging pilots by Telegram id; log retention bounds it (no change).
- P4 runs in parallel with Task 20. Task 15 starts after F1 merges.
- The 15-minute turn deadline is half of core's `IMMEDIATE_ERASURE_DELAY` (30 minutes, a constant in `ledger.py`). It
  is not an environment setting: one constant moves every bound together. The owner skipped the turn-length query.

**Status at compaction checkpoint 12 (2026-10-01): P3 complete; Task 20 and P4's Task 16 in progress.**
- P3 is merged and pushed with every phase-review fix, and the owner ruled every question of the P3 pause (the block
  above). The live Telegram bot runs `7233180`.
- In progress, six fresh Opus implementers, one worktree each: Task 20 F1 (copilot-mro), F2 (api and telegram-bot), F3
  (core), F4 (dashboard); Task 16 (iac, not applied); the test-lane-speed plan's FI-8 (copilot-mro). The ledger's
  checkpoint 12 holds the agent ids, worktrees, bases, briefs and the merge procedure.
- Next: a task review per lane, then merges batched so that one estate gate runs at a time; Task 15 after F1 merges;
  then the P4 phase review and the owner's pause before P5 (Tasks 17, 18).
- The owner owes: database users step 6's 4c (rebuild the api container, two checks), and the AWS secret
  `api/postgres/passwords` before iac `main`'s plan check can pass.

**Status at compaction checkpoint 13 (2026-10-01): Task 16 and F4 done; F1, F2, F3 in fix rounds; Task 15 building.**
- Done, merged and pushed: Task 16 (iac `main` `34e2345`, NOT applied; deploy notes in its section) and Task 20 F4
  (dashboard `agent_sdk` `f398f62`).
- F3 (core): reviewed (0/0/5 Minor); fix round 1 built the review's two fixes, the owner's history ruling (review
  M-5) and F2's core `rtbf` keyword; fix round 2 adds `rtbf` to the completion's audit event (controller ruling).
  Next: one fresh scoped re-review of both rounds.
- F1 (copilot-mro): reviewed (0/0/2 Minor, concern 1 graded real); fix round 1 reaches a deleted operator's
  still-present partitions (controller ruling). Next: a fresh scoped re-review.
- F2: the api half is accepted after its fix round (it merges after F3: it calls core's new keyword); the bot half's
  fix round (the owner's renewal ruling) is in a scoped re-review, because `/goodbye`'s renewal leg was refactored.
  Its next round adds README §13 step 3's `--rtbf` line and a docstring.
- Task 15 is building on F1's committed tip; it merges F1's fix round into its branch at hand-back.
- Merge order: core (F3, then test-lane FI-8's core half), copilot-mro (F1, FI-8's half), api (F2), one estate gate,
  push; the bot (F2) with its own gate and a restart of the live bot; then Task 15; then the P4 phase review and the
  owner's pause before P5.
- Owner rulings this stretch (2026-10-01): a legal pilot erasure is recorded as legal; the bot's purge command
  cancels a running renewal itself; a person's history hides the erasure's events from readers without
  `users_modify`.
- The owner owes: database users step 6's 4c, and the AWS secret `api/postgres/passwords`.

**Status at compaction checkpoint 14 (2026-10-01): every Task 20 lane through its fix rounds; final re-reviews running.**
- F3: fix round 2 done (the completion's audit event carries `rtbf`, read from the row the completion locks). One
  scoped re-review of both rounds is running.
- F1: fix round 1 done (the kept-partition gap is closed: the review's probe now fails, the inverted test passes). A
  scoped re-review is running.
- F2 bot: the re-review cleared the merge (`/goodbye` unchanged on every path); a last small round (README step 3's
  `--rtbf`, two docstrings, a test of Money operations §4's backstop query, one log-line pin) is running. Then the bot
  merges, its gate runs, and the live bot restarts. F2 api: accepted, merges after F3.
- Still building: Task 15, database users step 7, test-lane-speed FI-2 and FI-4. FI-8 waits for the batch.
- The merge order and the owner's items are unchanged from checkpoint 13.

**Status at compaction checkpoint 15 (2026-10-01): the WSL crash recovered; F2's bot half live; the Task 20 batch merged
locally, its gate running; Task 15 built.**
- **The crash, about 07:06.** Postgres came back on a fresh cluster and Weaviate on an empty schema, the known restart
  traps. On the owner's word both containers were restarted, and the real data is back. The live bot was restarted.
  A test world left by a killed run was swept from `copilot_mro_test`, on the owner's word. The owner set a cap of 4
  agents at a time.
- **F2's bot half:** fix round 2 (README step 3's `--rtbf`, two docstrings, the §4 backstop query tested, `/goodbye`'s
  refusal warning pinned) was accepted. Merged as telegram-bot `a3a253d`, gate 2547 passed, pushed, and the live bot
  restarted on it.
- **F3:** the re-review approved it. Fix round 3 pinned the "kind is `user`" half of `is_erasure_event` with one row.
- **F1:** the re-review found it merge-ready; the kept partition is now reached. Fix round 2 pinned two properties the
  code already had: each deleted operator's partition is judged on its own, and a failed presence read fails the
  pass.
- **The batch, merged locally:**
  - core `c6f6e2e` (F3, then test-lane FI-8);
  - copilot-mro `5c2bf7f4` (F1, then FI-8);
  - api `4ec77c5` (F2's api half).

  The estate gate is running. On green: push, remove the worktrees, and tick F1, F2 and F3 here with their FIs.
- **Task 15:** built, with F1 merged in (`ue-t15` `1e4c2c79`). Its first implementer retired past the context cap at
  the crash, and a fresh agent finished the hand-back. Next: the task review, after the gate. One owner item comes from
  it: on a host that names no Phoenix (`PHOENIX_ENDPOINT` unset, as on dev today), the erasure sweeps no Phoenix,
  warns once, and completes with one orphan recorded per chat. Task 18's live check needs Phoenix named on the api host.
- **Then:** the P4 phase review (Tasks 15, 16 and 20), the owner's pause, and P5.

**Status at compaction checkpoint 16 (2026-10-01, evening): P4 built and pushed; the P4 phase review two-thirds in;
Task 17's pins in review.**
- **Pushed:** core `c6f6e2e`, copilot-mro `96ab4f6d` (Task 15 `a0d71393`, then test-lane FI-4), api `4ec77c5`,
  telegram-bot `a3a253d` (live), dashboard `f398f62`, iac `main` `34e2345` (the owner switched the iac checkout to
  `main`). Task 15's gate: green but for the census reds.
- **The owner's rulings today:** O10 (c); I-2 (a); the RDS creator edge kept as a named accepted line; D2 keep
  forever; D9's keep list accepted; SDK transcripts off on the API host (a build after P5); the scheduler runs on AWS;
  a fifth Task 18 leg (the owner path). The Phoenix keys are in dev's `api/.env` and verified.
- **The P4 phase review:** A 0 Critical, 2 Important (I-1: the CLI and a worker do not see `api/.env`'s Phoenix; I-2:
  the evaluation gate), 7 Minor; B 0 Critical, 0 Important, 6 Minor; C running. One fix round follows C, with Task
  15's M-1, M-2 and M-5, its core comment, and O10 (c) and I-2 (a) built.
- **Task 17** runs as three lanes:
  - P, the cross-repo pins: built, in review; its fix round adds row 5h, review B's M-3 and M-4, and re-checks row 7
    with `via` as a change key;
  - D, the drift shape list: brief ready, with the controller's ruling on the list;
  - C, the census: after D.
- **Task 18:** the script is built next, with five legs. The live run waits for the owner's go, after the fix round.
- **Also running:** the sample env files refreshed estate-wide (owner request); database users step 7's fix round
  (its own ledger).
- **P4 review C (after the checkpoint):** 0 Critical, 4 Important, 11 Minor.
  - I-1, O10 on AWS, and I-4, no platform CLI on AWS: both are deploy blockers the owner decides at deploy time
    (Deploy/rollout 4).
  - I-2 is review A's I-1, and one fix covers both.
  - I-3: Task 18 needs one prerequisite list, a non-zero reading before every "gone" check, and the dashboard leg
    finished through the CLI's `--immediate`.

  Its Minors go to the fix round or the plan text.


**Status at compaction checkpoint 17 (2026-10-01, night): the P4 fix round's parts R and M merged; Task 17 lane P
merged; lane D in review; part D, the Task 18 script and the census next.**
- **Pushed:** core `72a24ff` (P4 fix part R), api `37e3f67` (part R), dashboard `64cc6e1` (part R), telegram-bot
  `c48fbdf` (part R, README), utils `ce99f3b` and lambdas `ee2ac6b` (env samples). Each behind a full post-merge gate,
  green but for the known reds.
- **Merged locally, waiting to push (in this order):**
  - copilot-mro `af45ced8`: the env samples, lane P's row 5h constants, part M (re-review: ready to merge, 0 Critical,
    0 Important, 4 Minor), and the samples' Phoenix comments. Its full gate is running.
  - api `adddeef`: lane P's pins (20) and the api sample's Phoenix comment.
  - dashboard `f3cc2bd`: the receipt guard as a gate in `test:unit`.

  api and dashboard passed their gates; they wait for copilot-mro, whose constants the pins read.
- **Built and merged:**
  - **Part R:** the teardown's tenant event takes the request's door; the legal mark over an open `/goodbye` records
    `platform-cli` as its actor; the stranded request's refusal names its finisher; the badge and `list` tests.
  - **Part M:** the Phoenix keys come through copilot-mro's settings; O10 (c) holds an erasure on a host that names no
    Phoenix, and `PHOENIX_ENDPOINT=none` skips and records it; the evaluation gate reads a purged chat as deleted in a
    tenant run; Task 15's minors.
  - **Lane P:** the pins, including the POC retention, every CloudWatch group, Cognito calls against the iac policy,
    and row 5h (15 s to spare today).
- **Running:**
  - **Part D:** the door check (a host that cannot finish an erasure refuses at the door); test sessions pinned to
    `none`; core's Cognito client back to 2 attempts; the eval script's `none`; the replay's runbook home; utils' cache
    keys out of the logs.
  - **Lane D's task review:** 64 placements, no owner question.
  - **The Task 18 script**, built and proved on fakes only.
- **Next:**
  - lane D's merge, plus a pin holding the three shape lists equal;
  - Task 17's census (lane C);
  - Task 18's review, then its live run on the owner's go;
  - SDK transcripts off on the API host.
- **Owner:**
  - step 6's 4c: restart the shell-run api on the merged code, then step 6's two checks;
  - the Task 18 go, once the census lands;
  - the AWS items, at deploy: the platform CLI's host, Phoenix or `none` in App Runner's env, X-Ray's `aws/spans`
    retention, the SMTP password out of the image and rotated.

**Status at compaction checkpoint 18 (2026-10-01, late night): every mainline pushed.** copilot-mro `af45ced8` (the env
samples, lane P's row 5h, P4 fix part M), api `adddeef` (lane P's pins), dashboard `f3cc2bd` (the receipt gate), core
`72a24ff`, telegram-bot `c48fbdf`, utils `ce99f3b`, lambdas `ee2ac6b`; each behind a full post-merge gate. Running:
P4 fix part D, lane D's task review, the Task 18 script. Next: lane D's merge with its pin row, then the census;
part D's merge; Task 18's review, then its live run on the owner's go.

**Status at compaction checkpoint 19 (2026-10-02, early).**
- **Pushed, each behind a full post-merge gate** (the only reds were the known census family):
  - Task 17 lane D: core `3092d78`, copilot-mro `94d0b59f`, shift-optimizer `70a7a39`;
  - the P4 fix round's part D: utils `ce25e60`, core `a6f3a8c`, copilot-mro `95412291`, api `5caa9fb`. The door check
    is built.
- **The owner ruled step 7's RDS question** (db-roles plan): accept `rds_superuser` on one narrowly pinned line.

**Status at compaction checkpoint 20 (2026-10-02).**
- **Pushed behind a full post-merge gate:** lane D fix part A, copilot-mro `0a3771a7` and api `728d0ec`.
- **One new known red:** part D's `test_the_owner_cli_refuses_a_request_on_such_a_host_and_freezes_nobody` (api).
  - It fails whenever an earlier test in the same worker booted the session telemetry fixture. That fixture leaves a
    JSON stdout sink, so the partition wiring's INFO line lands in the test's captured stdout.
  - It reproduces serially in two files that part A did not touch.
  - It is two cases on the mainline and six on D2's branch. D2's fix round fixes it.
- **Lane D fix part B's review: FIX FIRST, 0C/1I/3M.** All 64 moves are right.
  - The five word-only keeps become `no-person`. The two owner-pinned ones are confirmed by D1's and D10's own
    words.
  - Each guard pins its line's keep set.
  - copilot-mro's statement reader sees a CTE's write.
  - shift-optimizer drops `keep`.
- **Part D2 is built:** the door reads the grant pool's own user and password, the api's auth-cache eviction lines
  name no one, and part D's Minors are closed. Its review is running.

**Status at compaction checkpoint 21 (2026-10-02).**
- **P4 fix round part D2: merged and pushed behind a full post-merge gate.** utils `dfd7a17`, copilot-mro
  `b1883d85`, api `65f95f0`. The only reds were known ones: the census family, and the door-check red above, now six
  cases.
  - Its review was MERGE-READY, 0C/0I/4M. It found that the 503 door holds, that the door and the grant pool read the
    same pair, and that `delete_patterns` has exactly its four api callers.
  - **M1:** the door-check red has a second cause. copilot-mro's settings module prints "Found .env file at" to
    stdout when first imported, so the case that imports it first goes red. The same line breaks the owner CLI's
    "one JSON object a line" in production. The api's and core's settings modules print the same way.
  - **M2:** the eviction pin never drives a person with nothing cached.
  - **M3:** four cache-write WARNINGs (and their DEBUG twins) name the caller and tenant.
  - **M4:** the request log binds the raw URL path, so the erasure's own doors (freeze, cancel, status) write the
    person's internal id into two INFO lines each.
    - **Owner ruling (2026-10-02): no URL id in any request line, on every route.**
    - Request lines carry the route template, the one the server span carries as `http.route`. An unmatched path is
      reduced to `/:redacted`, as G.111 does for spans.
- **Part D3 (D2's fix round) is ruled, and waits for the owner to allow new agents.** It covers:
  - the door-check red, both causes: the test discards what setup printed, then accepts only log records; the three
    settings modules log the line at DEBUG, as utils already does;
  - M2's empty-cache case;
  - M3's eight lines, given the eviction lines' treatment;
  - M4 per the ruling.
  - The cache lines naming roles, departments and tenants go to the Future Improvements below.
- **Lane D fix part B2 is built.** All five word-only keeps are now `no-person`, since no writer puts the person's id
  there.
  - Each line's keep set is pinned: core 12, copilot-mro one, shift-optimizer none.
  - copilot-mro's guard refuses a write inside a CTE, and gains core's two whole-relation checks.
  - All 16 mutants are killed.
  - Its scoped re-review found two Minors, so part B3 comes first. B3 waits for the owner to allow new agents.
    - One sentence in core's line and one in copilot-mro's still give the old `no-person` reason.
    - copilot-mro's statement reader misreads a bracketed SET target list, so such a write to a held column passes
      every check. B3 makes the reader refuse any assignment it cannot read, and the same in core's guard.
    - B3 also adds a check that every column a statement assigns is placed. Today only
      `chat_turn_facts.session_id` fails it; it becomes a `scrub` (the browser session id, never the person's id).
- **Task 18 fix part 1 is built.** Every after-check is now armed by its own before, a redo resets the later steps,
  no check is excused by the product's own receipt, and the script never runs the due queue.
  - Its scoped re-review found the behaviour closed, with one Important and seven Minors. The Important: the per-read
    tests are built from the very lists they should pin, so a read can be dropped with every test green.
  - Part 2 is split in two, since part 1 outgrew one agent:
    - **Part 2a** fixes the re-review's eight findings. The planted reads become a literal table. `after` reads every
      part again, and residue in a part `before` found empty fails. The kept fact is proven unchanged as well as
      unlinked. The account-claim check predicts exactly what the erasure decides.
    - **Part 2b** takes the original review's remaining Minors and the run sheet's prerequisites. It adds two items:
      a harmless pre-flight proving the api's identity may make the erasure's Cognito admin calls, and a leg that
      reads the agent-state store's Postgres rows.
- **Queued, once agents are allowed again:**
  - part D3;
  - lane D fix part B3, then the merge of lane D's fix round B;
  - census part 1 (C1), after that merge;
  - Task 18 fix parts 2a, then 2b;
  - census part 2 (C2);
  - the P5 phase review;
  - SDK transcripts off on the API host;
  - Task 18's live run, on the owner's go.

**Status 2026-10-04 (the owner lifted the hold on new agents).**
- **The dev stack's Docker Desktop is stopped** since the host restarted. The shared Postgres is down, so no
  database lane and no post-merge gate can run, and nothing merges until it is back.
- **Lane D fix part B3 is built and re-reviewed.**
  - Both statement readers refuse an assignment they cannot read, and each guard (core's too) checks that every
    column a statement assigns is placed.
  - `chat_turn_facts.session_id` is placed `scrub`. All 21 mutants are killed by the guard files alone.
  - Its re-review found one Minor: the readers lose their place on text they cannot delimit (comments, dollar
    quotes, quoted identifiers, escape strings). No statement the erasure runs holds such text. Part B4, a
    tests-only round, makes both readers refuse it; it is running.
  - The database lanes of B2 and B3 are owed; they run before the merge, and again in the merge gate.
- **P4 fix round part D3 is built; its review is running.**
  - The door-check red is fixed: the test reads only what the CLI printed. The three settings modules log instead of
    printing.
  - The cache-write lines name no one.
  - Per the owner's ruling, every request line, uvicorn's access line included, names the route template, or
    `/:redacted` when no route matches.
  - Two core lines on the erasure doors' failure paths still name the person; the next round fixes them.
- **Task 18 fix part 2a is built.** The planted reads are a literal table, `after` reads every part again, the kept
  fact is proven verbatim, and the claim check predicts the erasure exactly. All 23 mutants are killed.
  - Part 2b is running on top: the parse sidecars and the agent-state Postgres rows read, all kept tenant knowledge
    held verbatim (D1), a harmless Cognito pre-flight, and the remaining Minors and prerequisites. One review then
    covers parts 2a and 2b.
- **Queued:** the merge of lane D's fix round B (after B4 and Postgres); census part 1 (C1); D3's fix round, if its
  review finds any; census part 2; the P5 phase review; SDK transcripts off on the API host; Task 18's live run, on
  the owner's go.

**Status at compaction checkpoint 22 (2026-10-04).** The owner lifted the hold.
- **Three rounds are built, reviewed and accepted, and wait to merge:**
  - **Lane D's fix round B** (parts B2, B3 and B4). Both statement readers refuse what they cannot read, every
    assigned column is placed, and `chat_turn_facts.session_id` is a `scrub`. Its database lanes run first.
  - **The P4 fix round, parts D3 to D6.**
    - The door-check red is fixed, and the settings modules log instead of printing.
    - Every request line, uvicorn's access and WebSocket lines included, names the route template.
    - The gateway serves no WebSockets. The websockets package's and `uvicorn.asgi`'s records never reach a sink.
    - The last lines naming the person on the erasure doors are gone, and so are the auth-cache lines naming roles,
      departments and tenants.
    - pytest's tracebacks are short in every repo, so a failed connection prints no password.
  - **The Task 18 script** (fix rounds 2a, 2b, 3 and 4).
    - It reads the parsed PDF text, the agent-state rows and every chat of the person.
    - It holds all kept tenant knowledge to verbatim, and runs a harmless Cognito pre-flight.
    - It fixes a leg's person once planted.
    - Its SQL ran against a database built from code: 42 checks, 0 bad.
- **Next:**
  - the three merges, each behind its full gate;
  - census part 1 (C1), then C2;
  - the P5 phase review;
  - SDK transcripts off. That change also makes the receipt name the statement-proven class and the parse-sidecar
    content records.
  - Task 18's live run, on the owner's go.
