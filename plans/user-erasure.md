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
- **R-WINDOW:** one-shot runs have no not-before (`automation_store.py:1036-1060`) and the scheduler defaults OFF (api
  `automations/settings.py:42-43`): the window lives in the ledger (`erase_after`); a daily global builtin enqueues a
  `user_erasure` one-shot per due row; immediate requests enqueue after the freeze commits; an owner-run CLI in the api
  environment (it needs the seam wiring; core imports no service) covers scheduler-off with `--run-due` (amended
  2026-09-27, P1 review COMP I-2).
- **R-FREEZE:** `users.status = erasure_pending` (prior value in the ledger), refused explicitly by the gateway and the
  automations identity check (status is otherwise deliberately unconsulted, `auth.py:587`); memberships untouched.
- **R-DOOR:** no platform-operator HTTP identity exists, so the platform door is an owner-run CLI: core's CLI may only
  request, cancel and list; running an erasure (run one, `--run-due`) is the api-side CLI's
  (amended 2026-09-27, P1 review COMP I-2). `DELETE /users/{id}` (no caller in the tree) becomes an erasure request
  under its `users_modify` gate. Every request path refuses (fixed 503) in a process whose seams are not registered, so
  nobody is frozen where no erasure can finish (P1 review CORR I-1).
- **R-DOCHUB-REKEY:** shared docs de-attribute copy-then-delete — read paths re-derive object keys from
  `owner_user_id` (`document_hub/keys.py:1-15`), so a row rewrite alone breaks the document.
- **R-PLACEMENTS (research gaps):** `comments.mentions` → remove the id; other recipients' notification payloads
  naming the user → de-attribute; invitations addressed to the user → delete, `invited_by`/`accepted_by` elsewhere →
  `deleted-user`; RBAC provenance (`departments`/`roles.created_by`, `user_departments.joined_by`,
  `user_operators.granted_by` — non-updatable by design, `user_roles.assigned_by`) → KEEP under D9;
  `ad_compliance.complied_by` → keep (customer record); `improvement_findings.reviewer` → `deleted-user`.
- **R-GUARDS:** each repo's line + drift guard covers its own registry (copilot-mro incl. Weaviate properties);
  telegram-bot's `_ACCOUNT_SWEEP` guard stands. Cross-repo pins only in Task 17.
- **R-ORDER (copilot-mro):** chat ids → user-grain rows (definer keyed by user AND chat ids) → per chat: reap
  row-derived objects, one txn scrub + purge, post-commit reaps → DocHub → user prefixes.
- **R-VERIFY:** each seam registers `erase` + `residue` (read-only counts of the ids in every non-keep placement,
  re-derived from the stores); completion needs all-zero residue (bounded re-erase, else the step fails and retries),
  which also closes the in-flight-turn race for immediate requests.

## Phases

| Phase | Tasks | Lanes (worktree → mainline) | Ships |
|---|---|---|---|
| P1 foundations | 1–5 | C `core-erase`→master (1→2) · A `api-erase`→langgraph-merge (3, after 1) · M1 `copilot-mro-erase` (4) · M2 `copilot-mro-erase-b` (5) | ledger, registry, freeze/cancel, refactor, definer — nothing erases yet |
| P2 seams | 6–10 | M1 (6, then 8) · M2 (7) · C (9) · S `shift-optimizer-erase`→main (10) | every store's erase + residue + line + drift guard |
| P3 orchestration | 11–14 | C (11→13) · A (12, after 8–11) · D `dashboard-erase` (14) | the flow end to end, Cognito delete, receipt, D11, UI |
| P4 telemetry/iac | 15–16 | M1 (15) · I `iac-erase`→obs-merge (16) | Phoenix user sweep, S3 lifecycle, Cognito IAM |
| P5 proof | 17–18 | A (17) · controller + owner (18) | census, cross-repo pins, live E2E |

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
Owned: new `copilot_mro/app/db/chat_history/erased_user_copies.py`; `tests/unit/chat_history/`, `tests/db/user_erasure/`.
- [ ] `ERASED_USER_COPIES` places every user-keyed registry column and Weaviate property delete / scrub /
  de-attribute / keep with a reason (research §1a + R-PLACEMENTS), plus a residue query per placement.
- [ ] One txn under the tenant's full roster: delete `user_preference` and `scope='user'` memory; tenant-scope notes and
  facts keep payload, ids → `deleted-user`/NULL (D1); events by `actor_user_id` scrubbed; findings' evidence texts of
  the user's signals removed BEFORE the signals scrub; signals, facts and feedback by user id (not only per chat);
  data-discovery ids and findings `reviewer` → `deleted-user`; then `ERASE_USER_LLM_RECORDS_SQL` on the grant pool
  inside `db_tenancy(<erased tenant>, …)` (an unbound or other-tenant session is refused with 22023; a NULL argument
  returns no row, which is a refusal and never zero). The residue is read bound to the tenant's FULL roster (P1
  review CORR M-4).
  Post-commit: MemoryItemMT docs removed / re-upserted (orphans counted).
- [ ] Drift guard (unit, registry-derived): an unplaced column matching user_id, `*_user_id`, `*_by`, `actor*`,
  `author*`, `reviewer*`, `owner_user_id`, `*email`, `mentions`, `recipient*` (or such a Weaviate property) fails; a
  placement naming a vanished column fails.
- [ ] Proofs: db — sentinel user + sibling + a second tenant under the SAME user id; knowledge text kept verbatim with
  no id; rerun 0 rows. Mutants: drop the roster rebind; signals before findings; keep `user_preference`.

### Task 7: copilot-mro — Document Hub at user grain (P2, lane M2)
Owned: new `copilot_mro/app/services/document_hub/user_erasure.py`; `tests/{unit,db}/document_hub/`.
- [ ] Private + chat-scoped docs deleted through DocHub's own delete/purge with BOTH prefixes (raw backup included,
  the `tenant_object_prefixes` semantics) and their index docs and chunks. Shared docs (R-DOCHUB-REKEY): copy to the
  `deleted-user` owner path, rewrite the row's owner and any stored key, update the Weaviate owner, delete the old
  objects; the doc still opens, searches, and can be deleted by a tenant admin.
- [ ] Parse sidecars via the user's aliases; a content record goes only when no other alias references it. Residue:
  rows owned by either id, objects under `document-hub/{raw,artifacts}/{t}/{id}/`, index docs by owner.
- [ ] Proofs: fake S3 + Weaviate unit lane, db rows; a crash after the copy and after the rewrite each converges on
  rerun. Mutants: re-key without copy (shared doc unreadable); backup kept on a private delete.

### Task 8: copilot-mro — chats, chat objects and the seam composer (P2, lane M1, after Tasks 6–7)
Owned: new `copilot_mro/app/services/user_erasure.py` (`erase_user`, `user_residue`); `tests/{unit,db}/user_erasure/`.
- [ ] R-ORDER: chat ids (both ids, every department, any deleted state) → Task 6 → per chat: reap
  `dataviews/{t}/{chat}/`, its attachment objects + sidecar aliases and spills → one txn `scrub_chat_copies` + hard
  purge of `chats`/`chat_blocks` → `reap_chat_copies` → Task 7 → sweep `chat-files|chat-images|chat-audio/{t}/{id}/`.
  The report carries counts and orphan counts only.
- [ ] Proofs: db — a chat deleted BEFORE the erasure is scrubbed and purged; sibling and second tenant untouched; a
  crash after chat k's purge then rerun ends at zero residue; unit — order pinned by a spy. Mutants: purge before
  scrub; skip already-deleted chats; keep a department filter.

### Task 9: core — core-local rows, core line and drift guard (P2, lane C)
Owned: new `core/core/resources/user_erasure/core_copies.py`; `core/tests/{unit,db}/user_erasure/`.
- [ ] One tenant-bound txn: the user's automations deleted, their runs and attributed one-shots → `deleted-user`;
  `product_events` user id → `deleted-user`, session NULL; comments, mentions, notifications, subscriptions, thumbs,
  invitations per D10/R-PLACEMENTS; RBAC provenance and `authorization_events` untouched (D9); the `users` row is NOT
  deleted here (Task 11). Residue query; drift guard over core's registry as in Task 6.
- [ ] Proofs: db with sibling + second tenant; the thumbs trigger leaves counts right; rerun 0 rows. Mutants:
  delete comments instead of anonymising; leave mentions.

### Task 10: shift-optimizer — attribution seam (P2, lane S)
Owned: new `shift_optimizer/app/services/user_erasure.py`; unit + db tests in their domain folders.
- [ ] `optimizer_jobs.created_by`, `optimizer_runs.launched_by` → `deleted-user` for the tenant and both ids; residue
  query; line + drift guard. Proofs: db (`shift_optimizer_test`) with sibling + second tenant; mutant: drop the tenant
  predicate (record whether RLS or the test catches it).

### Task 11: core — the orchestrator, completion and receipt (P3, lane C)
Owned: new `user_erasure/service.py`; `user_erasure/freeze.py` (immediate enqueue AFTER the freeze commits,
`user_id=None` — P1 review COMP I-5; the platform door's rule in `_CANCELS_FROM`; the teardown-only request path D11
needs — COMP I-1); `user_erasure/erasure_endpoints.py` (+ `GET /users/erasures`; fold `erasure_http.py` in — SIMP M-6);
new `core/scripts/erase_user.py` (request, cancel, list only — R-DOOR amended); tests.
- [ ] `run_erasure(request id)`: erasing → each registered seam's `erase` in declared order (copilot-mro,
  shift-optimizer), then core's own `core_copies` erase (a recorded step, not a registered seam — P1 review SIMP M-2),
  step state persisted after each → Cognito AdminDeleteUser as the LAST `erasing` step (not-found = success, so a
  retry converges; `account_exists` joins the residue — COMP I-3), after checking no other tenant holds the sub (CORR
  N-3) → all-zero residue (R-VERIFY) → ONE txn on the completion cursor: `DELETE FROM users` (cascade; `UserService.
  delete_user` opens its own connection — remove it or make it this cursor's helper, COMP M-3) + the
  `authorization_events` row (delete / `user`, subject = surrogate, change = request id + counts, the request's via) +
  ledger completed. Immediate requests enqueue the one-shot after the freeze commits (a lost enqueue is caught by the
  due sweep: `erase_after = requested_at`).
- [ ] Repeat requests: an immediate/RTBF request over an open windowed one escalates it or refuses with its own 409,
  never silently returns the weaker row (CORR M-3). The due sweep tolerates a missing tenant and a missing
  `users` row (CORR N-4). Reconcile Cognito accounts left disabled with no open request (CORR N-2, widens T2-FC3).
- [ ] Receipt: per-store disposition + bounds (Loki 14 d, Tempo 72 h, CloudWatch 30 d, Phoenix 30 d, S3 noncurrent 30 d
  after deletion, backups and host SDK transcripts per the owner items). `GET /users/erasures` (gated by
  `users_modify`): the tenant's ledger rows — ids, state, timestamps, `cancellable`, receipt — so a receipt stays
  reachable after the `users` row is gone (COMP I-6). No replay record (owner decision 31).
- [ ] A cancel re-enables exactly the automations the freeze disabled (their ids recorded in the ledger's steps when the
  stand-down disables them), and no others (owner decision 32, closes T3-C2).
- [ ] Proofs: unit with fake seams — order, resume from each failed step, a completed request answers done, non-zero
  residue blocks the users delete; db — the event survives, the ledger has no name/email column. Mutants: users
  delete before the residue check; the event written outside the txn.

### Task 12: api — wiring, the job kind, the due sweep (P3, lane A, after Tasks 8–11 merge)
Owned: new `api/flynapse_api/user_erasure_wiring.py` + its call in `routers/users.py` beside the partition wiring; new
`automations/user_erasure_job.py`; `automations/tasks.py`; the kind registration site; api tests.
- [ ] Register the copilot-mro and shift-optimizer seams all-or-nothing (RuntimeError at assembly, as
  `partition_wiring`); `user_erasure` one-shot kind → `run_erasure` under the row's binding; a daily global builtin
  enqueues due rows (window passed, no run in flight).
- [ ] The executing CLI lives here (R-DOOR amended, P1 review COMP I-2 — it needs the seam wiring; core imports no
  service): an owner-run `python -m flynapse_api.user_erasure_cli` — run one, `--run-due` (covers scheduler-off),
  (no `--replay-completed`: owner decision 31).
- [ ] Proofs (worktree-pinned): all seams registered; the kind runs a fake erasure; each due row enqueued once.

### Task 13: core — the channel door erases the person too, D11 (P3, lane C, after Task 11)
Owned: `core/core/resources/channel_provisioning/channel_provisioning_endpoints.py`; core channel tests.
- [ ] Before `delete_tenant`: run the channel user's erasure immediately and synchronously (`requested_by='system'`,
  `via='api'`, mode immediate, rtbf false) through T11's teardown-only request path — the channel user is the personal
  tenant's sole Tenant Owner, whom `request_erasure` otherwise refuses as the last active owner (P1 review COMP I-1).
  A new `via` value needs an ALTER migration: the CHECK is baked in at CREATE (CORR N-4). The door's
  partition-failure log names `delete_unentitled_partition.py --purged-tenant` plus direct partition removal, never
  the bare script: its `--tenant` mode deletes the torn-down tenant's ledger rows (P1 fix M2 re-review). Cognito
  delete included, then the existing teardown; a failed erasure aborts before the tenant delete (retryable,
  404-on-repeat kept). Check the bot's `/goodbye` prose; a needed text change goes to a telegram-bot lane.
- [ ] Proofs: Cognito delete called, ledger completed, the tenant event still written; failure leaves the tenant intact.

### Task 14: dashboard — erase action and status (P3, lane D)
Owned: a new component under `components/features/settings/`, `lib/api/settings-api.ts` additions, the team member page.
- [ ] Shown only with `users_modify`; the confirmation states the window, what goes and stays (D1 in plain words) and
  cancel; a status + receipt view. Proofs: unit tests asserting booleans (never retained jsdom nodes); `next lint` only.

### Task 15: copilot-mro — Phoenix user sweep (P4, lane M1)
Owned: `copilot_mro/app/services/agent_evaluation/phoenix_session_scrub.py`; new
`scripts/observability/scrub_erased_user_spans.py`; one call in `copilot_mro/app/services/user_erasure.py`; tests.
- [ ] In the tenant's project, spans with `user.id` in the ids → their traces' spans deleted (the
  `pre_scheme_span_ids` pattern) after the per-chat session deletes; bounded, best-effort, counted; residue =
  `get_spans(user.id)`; the internal/golden project refused. Proofs:
  fake-client unit lane (live check in Task 18).

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
  retention (iac, Loki/Tempo configs, Phoenix). Proofs: remove one placement's statement per repo → census red.

### Task 18: live end-to-end on the dev stack (P5, controller-run on the owner's go)
Owned: new `copilot-mro/tests/e2e/user_erasure/user_erasure_e2e.py` (collects zero tests; layout exemption with reason).
- [ ] A throwaway dev-pool user in a dev tenant: real turns with uploads + a DocHub upload → immediate erasure →
  no current S3 objects under the user prefixes (noncurrent versions reported until the lifecycle applies), Weaviate
  filter counts 0, Phoenix `get_spans(user.id)` empty, Cognito admin-get → not found, receipt present. Dev tenants
  only; never the golden/internal project.

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
2. Merge/deploy order: core → copilot-mro, shift-optimizer → api → dashboard → iac (measured at the P1 review:
   copilot-mro's provisioning and `test_grant_role_privileges.py` read core's registry; the api imports core's
   `user_erasure`).
3. AWS (deferred until implementation is done): iac apply (Cognito policy + S3 lifecycle) BEFORE the routes are used
   on AWS — without the IAM grant every request fails closed at the Cognito disable.
4. Owner-run: prod migrations/provisioning, the iac apply, the Cognito proof user, `AUTOMATION_SCHEDULER_MODE` or a
   daily `--run-due`. Rollback: cancel open requests via the CLI, then redeploy the previous image.

## Owner / legal items

- [ ] **D9 legal opinion:** airworthiness `reviewed_by`/`review_note`, `authorization_events` actor/subject (incl. the
  erasure's own event), RBAC provenance columns, the ledger's opaque ids, and free-text knowledge kept under D1.
- [x] **D12 backup bound:** no backup/snapshot config exists in iac or deployment; the receipt states the bound. No
  replay is built (owner decision 31, 2026-09-28: a restore is disaster recovery only); see Future Improvements.
- [ ] SDK/CLI transcripts under `~/.claude/projects` on the API host: confirm retention or disable persistence.
- [ ] Scheduler: the delayed half runs only where the scheduler is embedded/worker; otherwise a daily `--run-due`.
- [ ] D2 side question: should ordinary chat delete also hard-purge after N days (today it retains forever)?

## Future Improvements

- Self-serve erasure (D5 option c); telegram pilots already self-serve.
- Automate the channel-tenant residue sweep after teardown (today owner-run `delete_unentitled_partition.py`).
- The channel door erases synchronously; move it to the job if personal tenants grow.
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
  - *Complete fix:* a reconcile pass (part of the due sweep) that lists disabled pool accounts whose users row has no open
    request and status is not `erasure_pending`, and re-enables them with an ops event. It is carried into Task 11's brief.
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
  - *Complete fix:* the run row carries the specific reason, and a frozen owner gets no notification.
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

## Lessons

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
  - Post-merge lanes are green for both.
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

*Owner questions for the P2 phase review.*
- Should private comments be deleted rather than anonymised?
- Should optimizer job notes be kept as they are?
- Should free text or contact JSON that names the person, but carries no id, stay unplaced as a receipt limit?
- Orphan-operator notifications need DDL to close. Do they go in the receipt and Future Improvements?

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
review (three Opus lenses), triage, and the OWNER PAUSE with the four questions above. Then push core, shift-optimizer
and copilot-mro P2, and remove the P2 worktrees and branches. Then P3.
