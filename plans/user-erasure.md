# User Erasure (PP-MRO-1) — Implementation Plan

> **For agentic workers:** SDD-driven. Controller = the owner's session; **implementers AND reviewers = Opus**
> (fresh agent per task, one implementer per working tree, concurrency cap 2 unless the owner raises it).
> Ledger: `/home/aditya/Code/.superpowers/sdd/user-erasure/progress.md`. Durable scratch:
> `~/.claude/scratch/user-erasure/<lane>/`. **Push rule:** Claude may push a repo's mainline after the phase review
> closes; never rebase, squash, amend or force-push. Executors do not edit this plan; they report exact text.

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
at once, erase after 7 days (immediately for a legal RTBF request); audit = one `authorization_events` row + a small
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
| P4 telemetry/iac | 15–16 | M1 (15) · I `iac-erase`→obs-merge (16) | Phoenix user sweep, S3 lifecycle, Cognito IAM |
| P5 proof | 17–18 | A (17) · controller + owner (18) | census, cross-repo pins, live E2E |

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

- [ ] Each phase: all tasks reviewed and merged → phase-level adversarial review (P2/P3: three Opus lenses —
  correctness, plan-completeness, simplicity) → triage → owner review pause before the next phase.
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
  enable, sign-out, delete, exists — configured pool only, no attribute reads.
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
- [ ] `run_erasure(*, tenant_id, request_id, one_shot_grace_seconds)` (C-16). Ledger reads are tenant-keyed under
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
     - the `authorization_events` row (delete / `user`, subject = surrogate, change = request id + counts, the
       request's via);
     - ledger completed.
- [ ] P2 carry-ins (ledger rulings; each is owed here):
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
- [ ] Repeat requests: an immediate/RTBF request over an open windowed one escalates it or refuses with its own 409,
  never silently returns the weaker row (CORR M-3).
- [ ] The teardown-only request (D11, COMP I-1; P3 plan review IM-1). Task 11 builds its entry and its guard; Task 13
  builds its caller and its step.
  - One core constant, `CHANNEL_TEARDOWN` (`ledger.py`), is its `requested_by`, the ledger's only durable
    discriminator.
  - Only the teardown-only entry in `freeze.py` writes it (`request_erasure` refuses the token), and only that entry
    skips the last-active-owner refusal: the channel user is the personal tenant's sole Tenant Owner.
  - Until Task 13 lands, `run_erasure` refuses such a request at step 6: the step is recorded `failed`, the request
    moves to `failed`, and it never completes.
- [ ] The due-row query (C-26; Task 12 owns the loop): bound to one tenant, it returns `frozen` rows past
  `erase_after` and `erasing` rows, never `failed` ones. A missing `users` row is tolerated; a deleted tenant's rows
  are unreachable, which CORR N-4 accepts.
  - Both arms skip a request with a `user_erasure` run in flight (P3 plan review IM-3, IM-4).
  - In flight is built from the drain's own fragments: a `running` row inside its ceiling, or a `claimed` row not yet
    past its `scheduled_for` plus the start grace. So a retry nothing serves (scheduler off) stops counting once it is
    overdue, and the next `--run-due` picks the request up.
- [ ] Receipt (C-17): identifier keys and non-negative integers only. The key set is declared once, as one literal
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
- [ ] `GET /users/erasures` (C-9): the tenant's ledger rows — ids, state, timestamps, `cancellable`, receipt — so a
  receipt stays reachable after the `users` row is gone (COMP I-6).
  - Gated by `users_modify` without a target id: a variant of `_require_user_delete_allowed`.
  - `user_router` owns `GET /users/{user_id}`, so `user_erasure_router` is mounted BEFORE it, with the load-bearing
    comment (`user_operator_router` is the precedent; `GET /users/status` is the live collision the sweep records in
    `KNOWN_SHADOWED`; P3 plan review MI-1). The dispatch-order sweep pins it.
- [ ] The fold (SIMP M-6, C-10): `erasure_http.py` goes into `erasure_endpoints.py`. `DELETE /users/{user_id}` (the
  route is literally the POST) moves there, and `USER_FROZEN` moves beside `UserErasurePending`, so the fold creates
  no import cycle. Fallback: keep `erasure_http.py` and correct its docstring.
- [ ] Proofs, each with its mutant (C-25):
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

- [ ] Owner rulings (2026-09-29):
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
    - Scheduler off (every deployment today): an immediate erasure runs at the owner's next `--run-due`, the existing
      owner item. A lost enqueue waits for the daily sweep, up to 24 hours.
    - For the wait to be a real bound, Task 11b bounds every interactive turn and the detached chat-file upload
      under it.
  - **A cancel restores the person and touches no automation (C-5; decision 32's mechanism, not its outcome).** The
    freeze disables nothing: a frozen owner's runs are recorded `skipped` (Task 12). A cancel restores the status and
    the Cognito state and has nothing else to restore; the erasure deletes the automations in core's step. This closes
    T3-C2. It replaces "a cancel re-enables exactly the automations the freeze disabled, their ids recorded in the
    ledger's steps", which could not be built: `record_step` writes only while `erasing`, and the steps hold
    identifier keys and integers, never an automation's UUID.

### Task 11b: copilot-mro — open turns and uploads bounded under the delay; the refusal marker (P3, lane M1)
May start once Task 11 has committed `IMMEDIATE_ERASURE_DELAY`, its tests pinning `PYTHONPATH` to `core-erase`; merges
only after Task 11 merges (owner question 5's copilot-mro half, C-22; the marker, C-14; P3 plan review MI-6).
Owned (P3 plan review IM-5), all under `copilot_mro/app/services/`:
- the turn construction: `agent_shared/pipeline.py` (`build_prepared_turn`) and `agent_claude/legacy_adapter.py`;
- the Claude SDK orchestrator's loop, `agent_claude/orchestrator.py`;
- `chat_file_service.py`;
- the refusal types in `user_erasure.py` and in `copilot_mro/app/db/chat_history/erased_user_copies.py`;
- tests in their domain folders.
- [ ] Every interactive turn gets a hard deadline.
  - The field is `PreparedTurn.deadline` (`agent_shared/contracts/turn.py`). `copilot_mro/app/config.py`'s comment
    calls it `TurnContext.deadline`; no such type exists.
  - Neither builder assigns it today: `build_prepared_turn`, called from the composed pipeline and from the SDK
    legacy adapter.
  - Only the LangGraph backend (`lang_agent/backend.py`, `lang_agent/controls.py`) and the tool dispatcher enforce
    it. The Claude SDK orchestrator never reads it, so assigning it alone does not stop an SDK turn's model loop.
  - Every backend that serves an interactive turn enforces it, the Claude SDK orchestrator's loop included. An
    automation run keeps its own runtime ceiling; Task 11's drain waits for it.
- [ ] The detached chat-file upload task (up to 4 attempts) gets a total budget.
- [ ] Both bounds derive from core's `IMMEDIATE_ERASURE_DELAY` with a margin: the turn deadline, the upload budget and
  the margin together stay under the delay, pinned against the constant (copilot-mro imports core).
- [ ] The refusal marker: `erasure_refused = True` on `UserErasureRefused` and `ErasedUserCopiesRefused`; no
  incomplete carries it. Document Hub has had no refusal of its own since the P2 simplification batch (its subject
  check moved into `ErasureSubject`).
- [ ] Proofs: a turn past its deadline stops, on each serving backend (LangGraph and the Claude SDK); an upload past
  its budget stops retrying; the pin fails once the sum reaches the delay; each refusal type carries the marker and
  each incomplete does not. Mutants: leave the deadline unassigned; drop the SDK backend's enforcement; drop the
  upload budget; drop the marker from one refusal type.
- [ ] **Carry-ins from Task 11's build and review (2026-09-30).** Core reads a seam's exception by its type and frames
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

### Task 12: api — wiring, the job kind, the due sweep, the owner CLI (P3, lane A, after Task 11 merges)
Merges only after Task 19's copilot-mro half has merged and the owner has run the orphan script on dev (Deploy/rollout
step 2; P3 plan review MI-6).
Owned (C-23): new `api/flynapse_api/user_erasure_wiring.py` + its call in `routers/users.py` beside the partition
wiring; new `flynapse_api/user_erasure_cli.py`; new `automations/user_erasure_job.py`; `automations/tasks.py`;
`automations/loop.py` (the kind site, `ONE_SHOT_FEATURE_WIRING`); `automations/executor.py` (C-5); api tests.
- [ ] Register the copilot-mro and shift-optimizer seams all-or-nothing (RuntimeError at assembly, as
  `partition_wiring`). The `user_erasure` one-shot kind calls `run_erasure` with the run row's tenant, the params'
  `request_id` and the deployment's grace (C-16). When the outcome carries `rerun_at`, the kind enqueues one
  `user_erasure` one-shot with `not_before = rerun_at`; otherwise it enqueues nothing. It is the only caller that acts
  on `rerun_at` (P3 plan review IM-4, controller ruling on the plan fix).
- [ ] Every process that serves the kind wires the seams itself (C-2). The scheduler worker mounts no core and never
  imports `routers/users.py` (`main.py` is its only importer), yet it serves every wired one-shot kind.
  - The kind's registration function calls `partition_wiring.wire()` and `user_erasure_wiring.wire()` first, and
    registers the kind only if both succeed. Otherwise the rows stay `claimed` and the recovery census logs them.
  - The partition hooks are needed because Task 13's teardown step checks both partition registries and calls
    `remove_partitions`, which raise when unregistered, and only `routers/users.py` wires them today (P3 plan review
    IM-2).
  - `routers/users.py` keeps its call for the request doors. The CLI calls both `wire()`s too, since it runs
    `run_erasure` in-process.
- [ ] The due sweep (C-26), a daily global builtin. A global builtin runs bound to `__SYSTEM__` and `user_erasures`
  is tenant-RLS, so it iterates `tenant_registry.all_tenant_ids()` and binds each tenant (the `tasks.py` precedent),
  runs Task 11's due-row query, and enqueues one `user_erasure` one-shot per due row.
- [ ] A frozen owner's automations are skipped, never disabled (owner, C-5).
  - When the identity check raises `OWNER_ERASURE_PENDING` (`identity.py`), the executor records the run `skipped`
    with that reason. Nothing is disabled and no bell row is written. This closes T3-C1 and T3-M4.
  - Where the silence and the no-retry live (P3 plan review MI-5): `owner_erasure_pending` joins `SILENT_REASONS`
    (`loop.py`) and the executor recorder's no-announce exclusion (today it spares only `entitlements_unresolved`
    from `announce_missed_run`). It gets no entry in `RETRY_BACKOFF_BY_REASON`: a reason absent there is never
    retried.
  - `AUTOMATION_SCHEDULER_MODE` is unset in every deployment (it defaults to off, `automations/settings.py`), so no
    stand-down can have fired over a freeze, and nothing needs migrating. Verify that on dev before relying on it.
- [ ] P2 carry-ins:
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
- [ ] The owner CLI, the platform door (R-DOOR, C-1): `python -m flynapse_api.user_erasure_cli`.
  - request: `via = script`, `requested_by = platform-cli`, with immediate and RTBF flags;
  - cancel, under the platform door's rule in `_CANCELS_FROM`;
  - list;
  - run one (also the owner path for a `failed` request, once its data is fixed);
  - `--run-due` (covers scheduler-off). No `--replay-completed` (owner decision 31).
  - The CLI never enqueues. `--run-due` runs each due request in-process, and neither it nor run one acts on
    `rerun_at`: the due sweep or the next `--run-due` picks the request up. With the scheduler off, nothing would
    serve a one-shot the CLI enqueued (P3 plan review IM-4).
- [ ] Proofs (worktree-pinned):
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
- [ ] **Carry-ins from Task 11's build and review (2026-09-30).**
  - Import `core.resources.user_erasure.service` and `freeze` directly: the package does not re-export `service`
    (an import cycle through `user_service`).
  - The job skips a `failed` request before calling `run_erasure` (a stale queued retry must not resume a refused
    request). Mutant: the job runs a `failed` request.
  - The job catches `enqueue_erasure_run`'s `ValueError` (a `not_before` more than 30 minutes ahead), logs it and leaves
    the request to the daily sweep. Mutant: the job lets it raise.
  - The CLI help and the runbook say that with the scheduler off, `--run-due` sees an immediate request only from
    `erase_after` plus the 10-minute start grace, because the freeze itself enqueues the request's one-shot.

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
- [ ] Owner ruling (2026-09-29, C-4): `/goodbye` takes the job path like every immediate erasure — lock, reply, erase
  30 minutes later. A synchronous erasure could neither wait out open turns (owner question 5) nor fit Task 11's
  retries in one request (DocHub's 30-minute hold).
- [ ] The door opens the request through Task 11's teardown-only entry (`requested_by = CHANNEL_TEARDOWN`, an opaque
  token, so no DDL; `via = api`, mode immediate, rtbf false; P1 review COMP I-1) and answers 202. It deletes nothing.
- [ ] The door's new contract is the 202 body: the request id, its state and `erase_after`, and no personal data. A
  repeat call answers the open request's body until the tenant is gone, then 404.
- [ ] Step 6 (P3 plan review IM-1): Task 13 replaces Task 11's refusal with a direct call to the teardown body. No
  hook registry.
  - The body moves from the endpoint into `channel_provisioning_service.py`: its two preconditions (both partition
    registries, the cascade check), `delete_tenant`, then the partitions. The door no longer runs it.
  - The completion transaction follows (Task 11, step 7). The ledger and the event have no FK, so they survive the
    tenant.
- [ ] Failures (P3 plan review MI-16):
  - a failure before the tenant delete commits leaves the tenant intact, and the retry converges;
  - a partition failure after it is logged with the finisher named (below), and the step counts done. The operator
    ids are enumerated before the delete and are gone after it, so a retry could not redo them.
- [ ] The teardown step's partition-failure log names `delete_unentitled_partition.py --purged-tenant` plus direct
  partition removal, never the bare script: its `--tenant` mode deletes the torn-down tenant's ledger rows (P1 fix M2
  re-review).
- [ ] While the channel user's teardown request is open, the provisioning POST answers a fixed 409 (deletion in
  progress) and creates nothing (P3 plan review IM-6).
  - Its detail differs from the namespace-conflict 409's, so the bot can tell the two apart.
  - Why: the bot purges its rows as soon as the door answers, so `/start` can reach the POST at once. The POST's
    idempotent replay would find the frozen tenant. Before step 4 it re-sets the frozen account's password. After
    step 4 it mints a new identity and an active `users` row in the tenant the job is about to delete, which leaves a
    live Cognito account naming a deleted tenant.
- [ ] The bot's side (lane T):
  - on a 200 (a core without Task 13), today's flow and farewell; on a 202, purge, then the new farewell;
  - the new farewell says the account is locked now and erased later, and promises no time: in a scheduler-off
    deployment the erasure waits for the owner's `--run-due` (today's door deletes the tenant at once);
  - it says `/start` works again once the deletion completes, and no longer says the sign-in record stays (step 4
    deletes it);
  - the answer to the 409 says the deletion is still in progress and `/start` works again once it completes.
- [ ] Proofs:
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

### Task 14: dashboard — erase action and status (P3, lane D, after Task 11 and Task 19's core half merge)
Owned: a new component under `components/features/settings/team/` (beside `EditTeamMemberDialog.tsx`); the team page
`app/(dashboard)/settings/department/team/page.tsx` (there is no per-member page); `lib/api/settings-api.ts`
additions; new `contracts/user-erasure-receipt.json` and its generator in `scripts/`; tests. Lane D also carries Task
19's operator-delete copy.
- [ ] Shown only with `users_modify`; the confirmation states the window, what goes and stays (D1 in plain words) and
  cancel; a status + receipt view.
- [ ] The receipt is identifier keys and integers only (C-17). The dashboard owns one sentence per key, from
  `contracts/user-erasure-receipt.json`, generated from core's declaration (the literal mapping in
  `user_erasure/ledger.py`, Task 11) by a script that refuses without a core checkout (the
  `automation-run-triggers.json` precedent, `scripts/generate-run-trigger-contract.mts`). An unknown key is rendered
  generically, never dropped.
- [ ] The status list reads `GET /users/erasures` (Task 11), so a receipt stays reachable after the person's row is
  gone.
- [ ] The doors answer three 503s (P3 plan review MI-13). `ERASURE_UNAVAILABLE` (no seams registered) is shown as
  unavailable. The retryable ones, `ACCOUNT_UNAVAILABLE` (Cognito) and the queued freeze's refusal (Task 11, m-6),
  are shown as "try again".
- [ ] Proofs: unit tests asserting booleans (never retained jsdom nodes) — the action hidden without `users_modify`,
  a sentence for every contract key, an unknown key rendered generically, `ERASURE_UNAVAILABLE` shown as unavailable
  and a retryable 503 as "try again"; the contract guard compares the snapshot with core's declaration; `next lint`
  only. Mutant: show every 503 as unavailable.

### Task 15: copilot-mro — Phoenix user sweep (P4, lane M1)
Owned: `copilot_mro/app/services/agent_evaluation/phoenix_session_scrub.py`; new
`scripts/observability/scrub_erased_user_spans.py`; one call in `copilot_mro/app/services/user_erasure.py`; tests.
- [ ] In the tenant's project, spans with `user.id` in the ids → their traces' spans deleted (the
  `pre_scheme_span_ids` pattern) after the per-chat session deletes; bounded, best-effort, counted; residue =
  `get_spans(user.id)`; the internal/golden project refused. Proofs:
  fake-client unit lane (live check in Task 18).
  The purge deletes the soft-deleted `chats` rows that `scrub_deleted_chat_sessions.py` draws its ids from, so a
  per-chat session the reap orphaned can no longer be replayed. The sweep runs inside `CopilotUserErasure.erase`
  BEFORE the purge, with the gathered chat ids: it retries each chat's session delete, then sweeps `user.id` spans.
  Verify the content-copy sessions' spans carry `user.id`; if not, the sweep needs the chat ids. Its residue joins the
  seam's composed residue under a disjoint key. The receipt's Phoenix 30 d bound is the backstop.

### Task 16: iac — S3 noncurrent-version expiry and the Cognito erasure policy (P4, lane I)
Owned: `iac/s3.tf`, `iac/apprunner_iam.tf`; iac unit tests.
- [ ] Bucket lifecycle: whole-bucket NoncurrentVersionExpiration 30 days, expired-delete-marker cleanup, abort
  incomplete multipart, depending on the versioning resource. A stand-alone `apprunner_cognito_user_erasure` policy:
  AdminDisableUser, AdminEnableUser, AdminUserGlobalSignOut, AdminDeleteUser, AdminGetUser, configured pool only.
- [ ] Proofs: HCL block tests (`test_hcl_blocks.py` pattern) pin 30 days and the exact actions; `terraform fmt -check`
  / `validate` if available. NOT applied.

### Task 17: planted-sentinel census + cross-repo pins (P5, lane A)
Owned: new `api/tests/integration/user_erasure/` (census + fixtures).
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

### Task 18: live end-to-end on the dev stack (P5, controller-run on the owner's go)
Owned: new `copilot-mro/tests/e2e/user_erasure/user_erasure_e2e.py` (collects zero tests; layout exemption with reason).
- [ ] A throwaway dev-pool user in a dev tenant: real turns with uploads + a DocHub upload → immediate erasure →
  no current S3 objects under the user prefixes (noncurrent versions reported until the lifecycle applies), Weaviate
  filter counts 0, Phoenix `get_spans(user.id)` empty, Cognito admin-get → not found, receipt present. Dev tenants
  only; never the golden/internal project. Read the memory index after the erasure (Task 6 clears `user_id` by PATCH
  with a null; the fakes cannot prove the server unsets it), and check that a re-keyed DocHub chunk kept its vector
  (T7 FI-3).

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

- [ ] **The placements (Q1: every operator-keyed table, derived from the registries).** 57 `tenant+operator` base
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
- [ ] **The seam (C-20).** `operator_lifecycle` gains the operator-axis twin of the erasure registry:
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
- [ ] **Core's own step (not a seam).** `operator_copies` derives its relations from core's registry (`tenancy ==
  tenant+operator`: `notifications`, `notification_subscriptions` today) and deletes the operator's rows — never the
  `__ALL__` rows — on the delete transaction's own cursor, rebound to `(tenant, (operator,))`. Its residue reads the
  same relations under the same binding, read-only.
  - Two entries share the statements (P3 plan review IM-7): the step on a caller's cursor (the route's delete
    transaction), and a self-bound entry for one pair that opens its own `(tenant, (operator,))`-bound transaction
    (the orphan script: an orphan pair has no `operators` row and no delete transaction). Both live in
    `operator_copies.py`, which keeps lanes C and C-b disjoint.
- [ ] **copilot-mro's seam.** `operator_teardown.erase_operator_data` / `operator_data_residue`:
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
- [ ] **Document Hub writes nothing for a deleted operator (controller ruling on the plan fix).** DocHub's indexing
  calls `ensure_tenant` before every vector write, so a held attempt that completes after the route removed the
  partitions would re-create its pair partition.
  - Before `ensure_tenant` and the vector write, the indexing checks that the pair still has an `operators` row.
  - When it does not, the attempt ends as abandoned (`processing_abandoned`, DocHub's own terminal code) and writes
    nothing: no partition, no vector. That code is not one of the failures that clean vectors, so the ending makes no
    Weaviate call. The row stays held for the orphan script.
- [ ] **The route's order** (`DELETE /operators/{id}`; Q2: the clean-up runs inside the request):
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
- [ ] **How residue proves the delete.** Zero on every placement of every registered seam plus core's step, read
  under the one binding that reaches the operator's rows. The placement set is derived from the registries, so a new
  `tenant+operator` table is in the erase and the residue the day it is declared. The drift guard asserts the derived
  set equals the registry's, and fails on a stale exclusion.
- [ ] **The orphan census and clean-up (Q3, Q4, Q6).** `copilot-mro/scripts/delete_orphaned_operator_rows.py`, run by
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
- [ ] **Proofs.**
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
- [ ] **Mutants** (each killed by the file named): drop the `operator_id` predicate from one relation's delete
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
- [ ] **Receipt.** No erasure receipt key for orphan operators (C-18): Task 19 lands in P3 before any live erasure,
  and the rollout clears existing orphans before the erasure routes serve.

## Review & merge protocol

1. Per task: fresh Opus implementer → fresh Opus adversarial reviewer (brief + report + diff + the phase scope) who
   RE-RUNS the named red-befores and mutants and emits a claims table; P0/P1 block, P2/P3 → Future Improvements.
2. Controller merges each task locally `--no-ff` into its mainline and re-runs the touched suites there.
3. Phase review (independent, adversarial) → triage → owner pause; then Claude may push the phase's repos.

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
   on AWS — without the IAM grant every request fails closed at the Cognito disable. The api process also needs the
   grant-pool credentials (`POSTGRES_GRANT_USER` / `POSTGRES_GRANT_PASSWORD`, owner decision 26): the copilot-mro seam
   runs the LLM-records definer on the grant pool, so without them every erasure freezes the person and then fails at
   that step on every retry. iac declares neither today.
5. Owner-run: prod migrations/provisioning, the iac apply, the Cognito proof user, `AUTOMATION_SCHEDULER_MODE` or a
   daily `--run-due`. Rollback: cancel open requests via the CLI, then redeploy the previous image.

## Owner / legal items

- [ ] **D9 legal opinion:** airworthiness `reviewed_by`/`review_note`, `authorization_events` actor/subject (incl. the
  erasure's own event), RBAC provenance columns, the ledger's opaque ids, and free-text knowledge kept under D1.
- [x] **D12 backup bound:** no backup/snapshot config exists in iac or deployment; the receipt states the bound. No
  replay is built (owner decision 31, 2026-09-28: a restore is disaster recovery only); see Future Improvements.
- [ ] SDK/CLI transcripts under `~/.claude/projects` on the API host: confirm retention or disable persistence.
- [ ] Scheduler: the delayed half runs only where the scheduler is embedded/worker; otherwise a daily `--run-due`.
  Immediate requests and `/goodbye` then also wait for the owner's next `--run-due`, not 30 minutes (C-3, C-4).
- [ ] D2 side question: should ordinary chat delete also hard-purge after N days (today it retains forever)?

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
  - *Complete fix:* a scheduled pass runs the row seam for orphan pairs whose hold has lapsed.
- **An operator delete's residue is read before the eviction applies (Task 19 core review P-1).**
  - *What is missing:* the route declares the grant eviction inside its transaction, and the api applies it after the
    response. A request still holding the deleted operator's grant can write a row after the residue read; that row
    is an orphan nothing reports.
  - *Why deferred:* the window is one in-flight request long, and the orphan script's census finds such rows.
  - *Complete fix:* re-read the residue once the eviction has applied (or apply the eviction before the post-pass), and
    carry a non-zero result as `cleanup_warning`.
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
- **The orphan census asks Weaviate once per deleted pair (Task 19 copilot-mro review B, M-4).**
  - *What is missing:* every census asks the memory index about each gone pair separately, and `--execute` runs the
    census twice. `copilot_mro_test` holds 1,154 such pairs.
  - *Why deferred:* it is an owner-run script; dev and production hold few deleted operators, and the cost is time,
    not correctness.
  - *Complete fix:* one index query per tenant for all its gone pairs, and `--execute` reuses the dry census it just
    verified against `--expect-rows`.
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

## Lessons

- The post-merge gate must be the whole suite of each repo the batch can affect, not the folders the batch touched.
  P1 added a core router, and copilot-mro's route-table test (its list of core routers) went red. The copilot-mro
  post-merge api lane ran only `tests/api/document_hub`, so the red was pushed twice (P1 and P2) and the router sweep
  never covered the erasure endpoints. The DB-roles review found it. Rule: at a merge, run each affected repo's full
  lanes, including its `tests/api`.
- A bounded wait on a marker that nothing clears is an unbounded erasure: in the scheduler-off deployment a stale
  `claimed` row never closes, so a drain must count only work that can still write (P2 correctness I-1).

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
3. Text naming the person without an id: a limit stated in the receipt.
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
