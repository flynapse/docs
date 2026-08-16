# Tenancy root fixes — binding-preferred `_tenant_id` + superuser-pool closure

Owner-approved systemic follow-ups from the AD Phase D reviews
(`copilot-mro/docs/plans/ad-phase-d-notifications.md`, "ROOT CAUSE — PROVEN" step 6 and
"Final review + fix round" → "What the owner should know"). Two working trees:
`/home/aditya/Code/utils` and `/home/aditya/Code/copilot-mro`.

## Spec

### Fix 1 — `RowTenancy._tenant_id` prefers the in-force binding (utils)

`utils/utils/row_tenancy.py::RowTenancy._tenant_id(None)` today falls straight back to
`self._settings().tenant_id`. Change: when no explicit `tenant_id=` is passed, prefer
`utils.tenancy_context.current_db_tenancy().tenant_id` when a binding is in force; fall
back to settings only when unbound. Explicit argument always wins (unchanged). Rationale
(proven in Phase D): any writer that binds a non-settings tenant and calls
`tenancy_values` composes a row its own session cannot insert (RLS-refused on the app
pool) — or, on a superuser pool, silently writes it to the WRONG tenant.

- [x] Audit every caller of the `_tenant_id(None)` path (classes a/b/c below).
- [x] Implement the binding preference in `utils/utils/row_tenancy.py`.
- [x] Decide `_operator_id` treatment (investigate, reason, do not change blind).
- [x] Unit tests beside `utils/tests/unit/tenancy/test_row_tenancy.py`.
- [x] Mutation proof: revert the preference → new unit test red.

### Fix 2 — close the superuser-pool exposure (both repos)

Prong 1 — config default: `utils/utils/config.py:124` `postgres_user` default
`"postgres"` → `"flynapse_app"`. The default is live in any context whose env discovery
misses a `.env` (CWD-dependent; both repo `.env`s set `flynapse_app`, but
`utils/utils/.env` carries **no POSTGRES_\* lines at all** — verified — which is exactly
how the AD CLI's pool ran as superuser). **The failure direction of this change is loud
(password/permission failure) rather than silent cross-tenant reads — that is the
point**: `flynapse_app` + the default password `"postgres"` refuses to authenticate,
where `postgres` + `"postgres"` silently authenticated as a BYPASSRLS superuser. No
`.env` file is edited.

- [x] Flip the default.
- [x] Blast-radius audit: code relying on the settings pool having owner powers (DDL,
      bootstrap, migrations through `utils.postgres`) — findings below.
- [x] Owner-connection fixtures verified flip-safe (see audit).

Prong 2 — belt-and-braces predicates on the two RLS-reliant AD gate queries:

- `_APPLICABLE_TO_FLEET_SQL` in
  `copilot_mro/app/services/notifications/ad_notification_dispatcher.py`: gains
  `AND afa.tenant_id = %s` in the constant; the per-operator execution path appends
  `AND afa.operator_id = %s`. Threaded from `_fleet_scope_under_current_binding`, which
  already knows both. `__ALL__` union case: `_fleet_scope` passes `operator_id=None`
  for the sentinel (the union across the tenant's operators is its honest scope), so
  that path gets the tenant predicate only — mirroring how `_fleet_scope` binds.
- `_APPLIES_TO_FLEET` in `scripts/ad/dispatch_ad_notifications.py`: the EXISTS clause
  gains `AND afa.tenant_id = %s`. The CLI runs under `script_tenancy()` — the tenant's
  FULL operator entitlement, i.e. exactly the union case — so tenant-only is the honest
  explicit scope; the bound tenant is threaded from `main()`'s binding into the three
  loaders as a parameter.
- RLS stays in force underneath: the predicate is a second belt for superuser pools,
  not a replacement — an unbound app-role session still reads zero rows.

- [x] Dispatcher predicate + param threading.
- [x] Retry-CLI predicate + tenant threading.
- [x] Update the SQL pins: `tests/unit/ad/test_ad_dispatch_operator_grain.py`
      (including inverting `test_it_writes_no_tenant_or_operator_predicate`),
      `tests/unit/ad/test_ad_query_contract.py` (`_assert_fleet_scoped` + loader
      signatures), `tests/db/ad/test_ad_effective_state_gate.py` (gate now takes a
      param), `tests/db/tenancy/test_ad_dispatch_grain_live.py` (fixture + per-call
      params).
- [x] NEW db test: the gate returns nothing for a foreign tenant even on a superuser
      (BYPASSRLS-asserted) connection — two-tenant `copilot_mro_test` estate; covers
      both the dispatcher gate and the retry CLI's EXISTS.
- [x] Mutation proof: revert a gate predicate → foreign-tenant db test red.

### Verification (mandatory)

- `tests/unit/ad tests/db/ad` — baseline 532; end ≥ baseline + additions.
- `tests/db/tenancy` — baseline 388 passed / 17 skipped.
- utils' own suite (`utils/tests`), seeds lane (`tests/seeds`, part of 76).
- AD live smoke re-run on `copilot_mro_test`: flip FAA 2023-04-17 → unknown for
  (t1-primary-estate-0000, t1-operator-alpha), sweep `--notify --no-notify-email`,
  expect pairs=24 tenant-correct + idempotent re-run — now with a non-superuser pool.
- `__pycache__` cleared before trusting surprises; exit codes never masked.

House rule: new files + test-file edits committable by name; production edits
(`row_tenancy.py`, `config.py`, dispatcher, retry CLI) stay uncommitted.

## Caller audit — the `_tenant_id(None)` path

Entry points that reach `_tenant_id(None)`: `tenancy_values`, `with_tenancy`,
`scope_clause`, `scope_clause_for_rows` — whenever called without `tenant_id=`.
Instantiation sites in live repos: `copilot-mro/copilot_mro/app/db/row_tenancy.py` and
`shift-optimizer/shift_optimizer/app/db/row_tenancy.py` (nothing in core/api/gtm/
lambdas). Sibling branch worktrees (`copilot-mro-fbloop`, `-adapplic`, `-bypassctl`,
`wt-*`) import the same `utils` checkout and inherit the change; their call sites are
copies of the ones below.

Class (a) — passes explicit tenant → unaffected:
- `copilot_mro/app/services/doc_catalog.py:321`, `services/memory/memory_db.py:209`,
  `scripts/migrate_ifim_dynamodb.py:352`,
  `services/parsers/ad_compliance_seeder.py:434` (post Phase-D fix pass, passes
  `tenant_id` through from every multi-tenant caller — this is the AD seeder path the
  regression pin covers).

Class (b) — runs under `script_tenancy()` where bound tenant == settings tenant →
behaviourally identical (the binding IS `settings.tenant_id`):
- All parser mains and seed scripts: `tn_parser`, `wdm_parser`, `crew_manual_parser`,
  `ad_parser:2265`, `ifim_parser`, `ftd_parser`, `task_card_parser`, `mel_parser`,
  `pdf_parser`, `amos_parser` (when run as parser CLIs), and
  `scripts/{workforce/seed_workforce, aog/seed_aog, production/seed_production,
  populate_inventory_sample_data, ad/populate_ad_compliance_sample_data,
  build_referred_by_mapping, load_task_hierarchy_locations}.py`.
- shift-optimizer (`app/db/repository.py`, `seed_task_history.py`): its service-side
  `_settings()` shim ALREADY prefers `current_db_tenancy()` for the tenant axis (the
  in-house precedent for this exact change). The utils-level preference now fires first
  with the same value — behaviourally identical in every state (bound → same bound
  tenant; unbound → settings). The shim is left in place (harmless; removing it is not
  this task).

Class (c) — can run under a non-settings binding with no explicit tenant. TODAY these
compose settings-tenant rows (RLS-refused on the app pool, so nothing can rely on that
succeeding; silently wrong-tenant on a superuser pool). AFTER the change they compose
the bound tenant. Judgement per caller:

- `copilot_mro/app/services/workorder_tree.py` (:434/:445/:458/:511/:518) — work-order
  tree writes, reached from the request path (AMOS work-order upload / re-open) under
  the auth middleware's binding = the REQUESTER's tenant. New behaviour composes the
  requester's tenant — correct: the rows belong to the tenant whose request produced
  them, and the WITH CHECK the write must pass evaluates exactly that binding.
- `services/parsers/amos_parser.py` (:2815/:2904) — same writes when driven by the
  upload path rather than the CLI. Same judgement as workorder_tree.
- `services/llama_index/llama_index_ingestion.py:937` (chunks) and
  `services/s3_pdf_processor.py` fan-outs — ingest triggered under a request binding
  writes chunks to the requester's tenant. Correct for the same reason.
- `services/weaviate_tenancy.py:382` (corpus-attribution rows) — written during
  collection attribution under whatever identity drives it; the attribution must match
  the identity RLS evaluates. Correct.
- `app/db/fleet_repository.py` (:96 read scope, :144 write) — fleet reads/writes under
  a request or automation binding scope to the bound tenant. Correct: a fleet repoint
  or read for tenant T must land/see T's rows.
- Scheduled automations / `SYSTEM_TENANT_ID` binds: an automation bound to a customer
  tenant that reaches any of the writers above now composes that tenant — the whole
  point of per-tenant automations. Correct.

**No caller was found where the new behaviour is wrong.** The pattern that would be
wrong — bind tenant A for a read while deliberately composing rows for settings tenant
B — does not exist; every found bind-then-write site either passes explicit tenant
(class a) or means its writes to belong to the bound identity.

### `_operator_id` — investigated, deliberately unchanged

`_operator_id(None)` falls back to `settings.operator_id`, resolving unset/blank to the
`__ALL__` sentinel. The binding does NOT carry an equivalent scalar: `DbTenancy.
operator_ids` is the *entitlement set* the session may touch (0, 1, or many operators;
`script_tenancy()` binds the FULL set), not the operator a row is attributed to — the
two answer different questions. Preferring "the" bound operator would be well-defined
only for singleton sets, and even there it would silently change behaviour: under
`script_tenancy()` on a single-operator tenant, rows that today correctly resolve to
`__ALL__` (tenant-wide) would get stamped to that one operator, shrinking their
visibility. shift-optimizer's shim states the same reasoning and also leaves operator
on settings. The prescription covered the tenant axis; the operator axis stays as is,
and the deliberate asymmetry is pinned by a unit test.

## Blast radius — `postgres_user` default flip

- `utils/utils/db_guard.py::owner_credentials` — flip-anticipating by design: the owner
  ROLE is pinned `"postgres"` (never read from settings), and the owner password is
  `POSTGRES_OWNER_PASSWORD` → `settings.postgres_password` only while
  `postgres_user == "postgres"` → literal `"postgres"` otherwise. The db-lane fixtures
  (`tests/fixtures/tenancy/rls_connections.py`) delegate to it, and their docstring
  names this exact flip ("Task 5 Step 6"). With the repo `.env`s in place (how every
  lane runs) `postgres_user` is already `flynapse_app`, so owner resolution is
  UNCHANGED by the flip.
- DDL: `flynapse_app` deliberately holds no CREATE (provisioning is the only creator —
  `ensure_compliance_table` asserts rather than creates). Anything needing owner powers
  already states the owner role explicitly via `owner_credentials`/dedicated
  connections.
- The one behaviour that changes: a no-`.env` context that previously got a silently
  working superuser pool (`postgres`/`postgres`) now fails authentication loudly
  (`flynapse_app` + default password `"postgres"` is not a valid pair). Loud is the
  design goal.

Full sweep (adversarial subagent audit, 2026-08-15). The single resolution point of the
default is `utils/utils/postgres_service.py:110-126` (`_credentials()`; the app pool
passes `user=None`). Only `api/.env` and `copilot-mro/.env` exist — core, shift-optimizer
and utils have NO `.env`, so "invoked without a .env" is the normal case there.

Breaks outright on a no-`.env` invocation (loud, by design):
- `core/scripts/run_db_lane.py:102-107` — CREATE/DROP DATABASE as the settings role.
- `api/flynapse_api/automations/ad_materialize.py:186-196` — settings creds behind a
  hard owner/BYPASSRLS assertion; ALREADY broken today whenever `api/.env` loads
  (`flynapse_app` fails the assertion) — the flip only makes it uniform. Pre-existing
  defect, owner's queue.
- `api/flynapse_api/automations/worker.py:173-179` — automations bootstrap returns
  `False` on an unprovisioned DB → `WorkerBootstrapError` (fatal, loud). Guarded.

Degrades silently (log-and-swallow, both off the boot path): `core/core/resources/
rbac/postgres_init.py:94-109` and `notifications/postgres_init.py:52-62` — ungated DDL
through the settings pool inside `except: logger.error`. Pre-existing shape; the flip
converts "silently succeeds as superuser" into "logged permission error".

The flip FIXES two things: `utils/utils/rls_boot_check.py::assert_rls_enforced`
(refuses SUPERUSER/BYPASSRLS) no longer refuses no-`.env` standalone boots, and the app
-password branch in `tests/fixtures/tenancy/rls_connections.py:198` starts resolving.

Watch items (recorded, not changed here):
- `assert_lane_role("flynapse_app")` in core's and shift-optimizer's db-lane conftests
  loses its power to DETECT a missing-`.env` invocation (the default now satisfies it).
- `db_guard.owner_credentials`: after the flip, `POSTGRES_PASSWORD=<owner secret>`
  without `POSTGRES_USER=postgres` falls to the literal `"postgres"` password (same
  value on this dev cluster; its docstring argues from the old default).
- Hardcoded-owner argparse defaults and direct `os.environ` readers in copilot-mro
  scripts, the grant pool, and core/shift-optimizer test schema fixtures: all explicit
  — unaffected.
- `initialize_postgres_tables` (copilot-mro `postgres_table_definitions.py:730`,
  shift-optimizer `app/db/postgres.py:134`): settings-pool DDL but NO production
  caller (runtime uses `assert_tables_present` / `assert_rls_enforced`); scripts and
  tests that still call it must run with a `.env` or owner env override — unchanged
  expectation.

## Implementation notes

### Fix 1 (landed)

- `utils/utils/row_tenancy.py`: `_tenant_id` now resolves explicit → `current_db_tenancy()`
  → settings; docstring states the precedence and why `_operator_id` deliberately does not
  mirror it. Module docstring's `settings()` paragraph updated. Import of
  `current_db_tenancy` at module top (no cycle: `tenancy_context` is stdlib-only).
- Tests: 5 new in `utils/tests/unit/tenancy/test_row_tenancy.py` — binding-outranks-
  settings, explicit-outranks-binding (the AD-seeder regression pin, explicit ≠ bound),
  unbound-falls-back, scope_clause-follows, operator-axis-ignores-binding.
- utils suite: **854 passed** (was 849).
- Mutation proof 1: binding preference reverted → 3 red
  (`test_an_in_force_binding_outranks_settings`,
  `test_the_scope_clause_confines_to_the_bound_tenant_too`,
  `test_the_operator_axis_deliberately_ignores_the_binding`); restored → 27/27 green.

### Fix 2 (landed)

- `utils/utils/config.py`: `postgres_user` default → `"flynapse_app"` with a comment
  stating the loud-failure intent. No `.env` touched.
- Dispatcher: `_APPLICABLE_TO_FLEET_SQL` now ends `AND afa.tenant_id = %s`; new
  `_GATE_OPERATOR_PREDICATE` (`AND afa.operator_id = %s`) appended only on the
  per-operator path in `_fleet_scope_under_current_binding`, which now binds
  `(tenant,)` or `(tenant, operator)`. `__ALL__` keeps tenant-only — mirrors
  `_fleet_scope`'s binding grain. Constant's design comment rewritten (belt-and-braces
  rationale, both directions).
- Retry CLI: `_APPLIES_TO_FLEET` EXISTS gains `AND afa.tenant_id = %s`; the three
  loaders take `tenant_id` and `main()` threads `script_tenancy()`'s binding tenant.
  No operator predicate — the full-entitlement bind IS the tenant union (documented).
- Test pins updated: `test_ad_dispatch_operator_grain.py` (inverted the no-predicate
  pin into `test_it_names_its_tenant_as_a_bound_parameter`; per-operator statement =
  constant + suffix with params; new tenant-wide-params test; recorder docstring),
  `test_ad_query_contract.py` (`_assert_fleet_scoped` requires the tenant predicate;
  loader calls/params updated; no-predicate pin inverted to name-tenant-never-operator),
  `test_ad_effective_state_gate.py` (gate executed with `(tenant,)`),
  `test_ad_dispatch_grain_live.py` (all four executes parameterised; unbound test now
  passes a REAL tenant param and pins that RLS alone still refuses).
- NEW db test `tests/db/ad/test_ad_gate_superuser_tenant_scope.py`: on an asserted
  BYPASSRLS owner connection, each gate returns exactly the named tenant's applicable
  set, empty for a no-rows foreign tenant (clone-estate-proof assertion), operator
  predicate composes rather than replaces, and the CLI EXISTS gets the same four
  assertions. Skips when <2 tenants carry applicable rows.
- Lane 1 (`tests/unit/ad tests/db/ad`): **534 passed** = baseline 532 + 2.
- Deviation from the brief: the prescription named three pin sites; the loader signature
  change surfaced a FOURTH — `tests/db/tenancy/test_ad_fleet_scope_live.py`, which
  captures the retry CLI's `--since` statement once at module scope and replays it under
  every pair's binding (3 errors on first lane run). Redesigned rather than patched: the
  fixture captures with a sentinel tenant, asserts the tenant is the trailing bind
  parameter, strips it, and every executing test appends the tenant it runs AS — a
  baked-in capture tenant would have zeroed every other pair by predicate and quietly
  stopped measuring RLS. Its unbound test now asserts the strongest form (real tenant
  named, unbound session, zero rows). File: 10 passed.

## Verification record (2026-08-15)

- `tests/unit/ad tests/db/ad` → **534 passed** (baseline 532 + 2 new; re-run green after
  mutation restores).
- `tests/db/tenancy` → **388 passed / 17 skipped** (baseline exact; first run showed 3
  errors from the fourth pin site, fixed above, re-run clean).
- `tests/seeds` → 62 passed; `tests/unit/tenancy/test_operator_corpus_seed.py` +
  `tests/unit/fleet/test_fleet_repoint.py` → 14 passed (the 76-lane); `tests/smoke` →
  25 passed.
- utils suite → **854 passed** (849 + 5 new).
- pyflakes clean on all five touched production/test files.
- **Live smoke** (`copilot_mro_test`, settings pool = `flynapse_app` via
  `copilot-mro/.env` — non-superuser, RLS live end to end): flipped FAA 2023-04-17 →
  unknown for (t1-primary-estate-0000, t1-operator-alpha); sweep `--notify
  --no-notify-email` → `transitions: became_applicable=1`, post-commit `seeded
  {'pairs': 24, 'written': 24, 'ads_seen': 1, 'ads_missing': 0}`, dispatch
  `notifications_created=2, create_failures=0, tenants_failed=0,
  events_without_audience=0, became_gate_dropped=0`. All 24 `ad_compliance_status`
  rows under the bound pair; `NOT EXISTS(fleet)` trespass probe = **0**. Immediate
  re-run: zero events, `post-commit side effects : none to run` — idempotent.
- **Mutation proofs** (`__pycache__` cleared around each):
  1. `_tenant_id` binding preference reverted → 3 utils tests red; restored → green.
  2. Dispatcher gate tenant predicate neutered (`%s IS NOT NULL`) → foreign-tenant db
     test red at the dispatcher assertions; restored → green.
  3. Retry-CLI EXISTS tenant predicate neutered → same db test red at the CLI-leg
     assertions (dispatcher leg green — the test discriminates the two); restored →
     green, full pin set 64/64.

## Lessons

(none — no user corrections during this run)

## Adversarial review + cleanup round (2026-08-15)

Spec: the adversarial review of the two root fixes above. One implementer, four working
trees (utils, copilot-mro, core, shift-optimizer). Git history untouched everywhere.

### Triage and outcomes

1. **Split-brain in copilot-mro's `_check_against_registry` — FIXED.** The check now
   resolves its tenant exactly as `tenancy_values` does (in-force binding, settings
   fallback) via `current_db_tenancy()`; docstring states why the two must agree. Module
   header (:14-17) rewritten for the new precedence and the deliberate operator-axis
   asymmetry. Tests: 2 new in `tests/unit/ingest/test_document_writers_name_their_operator.py`
   using a bound-tenant-aware registry stub (settings A + binding B → validated against B;
   unbound → settings A, refusal names A). **Mutation proof:** settings-only revert →
   `test_the_registry_check_validates_against_the_bound_tenant` red (1 failed / 44 passed);
   restored → 45/45. `__pycache__` cleared both directions.
2. **Dead guards / inverted comments — FIXED.**
   - `weaviate_tenancy.py`: the `bound_tenant != tenant_id` branch deleted (unreachable —
     the attribution's tenant IS the binding, and unbound is refused above); the comment now
     states the by-construction agreement, why the branch was deleted rather than kept, and
     that the operator axis (still settings-sourced) keeps the sentinel gate. **The
     unreachability was empirically confirmed before the edit**: the pin
     `test_a_binding_that_disagrees_with_the_attribution_is_refused`
     (`tests/ingestion/test_ingest_row_object_agreement.py`, outside the previous round's
     verified lanes) was already red. Rewritten as
     `test_the_binding_decides_the_attribution_whatever_settings_say` (bound A + settings B
     → A's partition); module docstring bullet updated.
   - `materialize_ad_corpus.py::assert_can_attribute`: two-axis gate restored — the
     original `resolved != partition_key` check kept first (still a real gate on the
     settings-sourced operator axis and on caller-passed mismatches, and the existing
     mutation pin in `test_ad_materialize_gate.py` targets it), plus a new direct check of
     `weaviate_tenant_key(current_db_tenancy().tenant_id, operator_id)` against the
     partition key — catches a regression that drops/reorders the `db_tenancy` bind, which
     the tenancy_values-derived tenant can no longer see. `attributed_to` docstring (:340-353)
     corrected: tenant axis follows the contextvar; the settings mutation stays load-bearing
     for the operator axis.
   - Stale settings-only prose fixed: `operator_corpus_seed.py` (module docstring
     parenthetical + the :122-131 refusal now name the OPERATOR axis as the settings-global
     hazard), `shift-optimizer .../row_tenancy.py` (module §"Where the value comes from" +
     `_settings` docstring now say the mechanism lives in utils and the shim is a
     compatibility passthrough whose tenant branch no longer decides anything; kept as the
     operator-axis injection point). Stale docstrings in
     `tests/unit/ad/test_ad_materialize_gate.py` (2 sites) updated to match.
3. **`core/scripts/run_db_lane.py` — working invocation RESTORED.** Four pieces, three of
   them surfaced by actually running it:
   - `_connect(..., owner=True)` resolves the admin (CREATE/DROP DATABASE,
     `pg_terminate_backend`) through `utils.db_guard.owner_credentials`, with the why in
     the docstring; call site in `main()` updated (the new unit pin caught that the first
     edit missed it).
   - `CREATE DATABASE ... OWNER <app role>` — PG16 grants PUBLIC no CREATE on `public`, so
     a scratch owned by the creator would refuse the app role's own bootstrap DDL.
   - `_child_env` states `POSTGRES_USER`/`POSTGRES_PASSWORD` (the parent's resolved app
     creds — the child's CWD has no `.env`, and the fix-4 canary refuses a defaulted role)
     **and** `ENV_FILE` at the parent's resolved env file (lane fixtures need more than the
     app pair — the grant-role credentials among them); `POSTGRES_DB` stays an env var,
     which outranks the file.
   - Credential-source pins: NEW `core/tests/unit/db/test_run_db_lane_credentials.py`, 5/5.
   Proof: full end-to-end scratch runs (create → bootstrap 8 tables as app role → lane →
   drop) on `tests/db/automations`: **185 passed, 2 failed — both `xfail(strict)` → XPASS**
   (`test_automation_claim.py` span-tenants pair). Those two are the known no-RLS canaries:
   the scratch bootstrap has never applied `provision_rls.py`, so no policies exist and the
   strict pins XPASS — identical outcome under the historical all-superuser lane (RLS
   bypassed), i.e. pre-existing, not a regression. Likewise pre-existing: the rest of
   `tests/db` (rbac/authorization/invitations/notifications) has grown estate dependencies
   a bare scratch cannot satisfy (`operators` relation, grant-role table grants, seeded
   head roles, RLS policies) — 18F/126E on the default paths, dominated by
   `relation "operators" does not exist` (swallowed inside `bootstrap_rbac_tables`'s
   log-and-swallow, the exact shape §Blast-radius already records) and
   `permission denied for table tenants` (grant role holds no grants in a fresh DB).
   **Owner's queue / follow-up option:** have the bootstrap child apply `provision_rls.py`
   (the app role owns the scratch tables, so it may create policies + FORCE) and decide
   whether the estate-dependent domains belong in this runner at all, or pin its default
   paths back to the automations lane it was built for.
4. **Missing-`.env` canary in `assert_lane_role` — RESTORED.** After the value check, the
   guard now requires `"postgres_user" in settings.model_fields_set` (the
   `database_provenance` trick): a run whose env discovery missed the `.env` resolves the
   expected name *by default* and previously sailed through. Distinct refusal message with
   the remedy. Tests both directions + fail-closed no-`model_fields_set` + real-object
   interface check: NEW `utils/tests/unit/safety/test_lane_role.py`, 5/5.
5. **Two binding-read policies in utils — DOCUMENTED, no behavior change.**
   `embedding_service._current_tenant_id` (unbound → None: spend must never be attributed
   by fallback) and `RowTenancy._tenant_id` (unbound → settings: a composed row must carry
   some tenant) now cross-reference each other and state why the difference is deliberate.

### Record-only dispositions

- **Owner note:** utils commit `231517c` (owner-side) bundles the tenancy production edits
  with unrelated LLM-metering work (+758 `llm.py`) — not separately revertible; the owner
  may split it if desired. It was committed AFTER our test commit, by the owner's side; the
  house rule (production edits uncommitted by agents) was followed by the agents.
- **Latent, recorded not fixed:** `_operator_id` composes `__ALL__` under full-entitlement
  non-settings binds where the tenant clause now passes — converting fail-closed into
  tenant-wide-visibility writes; no live writer hits the precondition today.
- **Pre-existing, owner's queue:** the api worker boots with a bare
  `bootstrap_notifications_tables()` (log-and-swallow on the boot path, `worker.py:184`)
  while its sibling is checked — announcements silently vanish on a partially provisioned
  DB; and `ad_materialize.py`'s superuser assertion under app creds.
- **Accepted:** live AD tests no longer discriminate tenant-axis RLS (coverage survives in
  `tests/db/tenancy` generics; non-vacuity guards kept); the retry CLI's candidate pool
  narrows to the settings tenant on any pool (documented under-delivery).

### Verification record (cleanup round)

- copilot-mro `tests/unit/ad tests/db/ad` → **534 passed** (baseline exact; this round's
  additions live outside these lanes).
- copilot-mro `tests/db/tenancy` → **388 passed / 17 skipped** (baseline exact).
- Touched copilot-mro files (`test_document_writers_name_their_operator.py` +2 new,
  `test_ingest_row_object_agreement.py` rewritten pin, `test_ad_materialize_gate.py`) →
  114 passed; `test_weaviate_tenant_fanout.py` → 44 passed.
- utils suite → **859 passed** (854 + 5 new), pytest exit 0.
- core `tests/unit/db/test_run_db_lane_credentials.py` → 5 passed; end-to-end scratch lane
  as recorded under fix 3.
- shift-optimizer `tests/unit/persistence/test_request_identity_wins.py` → 7 passed
  (docstring-only change).
- pyflakes over all nine touched production files: only pre-existing findings (unused
  `_common` import, `e` locals in embedding_service, one old f-string in run_db_lane).
- Mutation proof (fix 1) as recorded above; `__pycache__` cleared around it.

## Checked notifications bootstrap on worker boot (api) — DONE 2026-08-15

Owner approved 2026-08-15, implemented + adversarially reviewed the same day (implementation
notes, verification, and review triage at the end of this section). The defect was found by
this plan's adversarial review (recorded above under the record-only dispositions) and the
owner promoted it to a fix.

**Defect.** `api/flynapse_api/automations/worker.py:184` calls
`bootstrap_notifications_tables()` bare on the worker boot path. That function
(`core/core/resources/notifications/postgres_init.py:39`) logs-and-swallows every error and
returns `None` — its own docstring says it must not sit on a boot path. The sibling
`bootstrap_automations_tables()` at `worker.py:173` IS checked (returns bool → raises
`WorkerBootstrapError`). And `RUN_TABLES = ("chats", "chat_blocks", "memory_items")`
(`worker.py:114`) omits the notifications tables, so `_require_run_tables()` (`:187`, also
`assert_tables_present(RUN_TABLES)` at `:230`) never covers them. Consequence: on a
partially provisioned database the worker boots green and every notification it produces —
automation run-completed / disabled / run-missed announcements, and now the AD transition
classes — silently vanishes (no table, no row, no error). The current in-code comment
("a missing bell row is never worth refusing to run scheduled work over", `:182-183`) is
the design decision the owner is overruling: announcements are load-bearing (stand-down
notices are the worker telling humans it stopped).

**Fix shape (verify against code before editing; two options, pick with reasoning):**
- (a) Minimal, api-only, matches `_require_run_tables`'s philosophy (presence, not DDL
  authority): add the notifications relations (`notifications`, and check whether
  `notification_subscriptions` is written by the worker path too — the dispatcher reads it;
  reads also fail on absence) to the presence assertion — either into `RUN_TABLES` (note
  BOTH use sites, `:187` area and `:230`) or as a separate named tuple if the "run tables"
  name would lie. Keep `bootstrap_notifications_tables()` as best-effort convergence
  BEFORE the presence check — bootstrap-then-verify, refusal via `WorkerBootstrapError`.
- (b) Core-side: make `bootstrap_notifications_tables()` return bool like its automations
  sibling and check it in the worker. Touches core's public surface + its callers
  (`rg -n "bootstrap_notifications_tables" /home/aditya/Code/core /home/aditya/Code/api`)
  — heavier; only if (a) proves insufficient.

**House rules for the session that picks this up:** api repo carries large parallel WIP —
pathspec commits only, NEVER `git add -A`; test files committable by name, production edits
(`worker.py`, any core edit) stay uncommitted. api tests run from the api repo's own env
(check `api/tests/` layout — smoke/unit lanes exist, e.g.
`tests/smoke/automations/test_ad_materialize_loader.py`); the automations worker tests are
the natural home for the new pin (find them via
`rg -n "WorkerBootstrapError|_require_run_tables" /home/aditya/Code/api/tests`).
Tests to add: boot refuses when the notifications relation is absent (and the refusal names
it); boot proceeds when present; the existing automations-bootstrap refusal still holds.
Update the comment at `worker.py:182-183` to state the new contract. Record implementation
notes + verification here when done.

### Implementation notes — DONE 2026-08-15

Fix shape **(a)** as preferred, with the spec's "separate named tuple" variant: the
notifications relations did NOT go into `RUN_TABLES`, because both halves of that name would
have lied — they have their own bootstrap step directly above the check, they are declared in
**core's** registry (`core.db.table_definitions.NOTIFICATION_TABLE_NAMES`), not copilot-mro's
(the existing run-table test pins `RUN_TABLES` names into the MRO registry), and their remedy
is different (`migrate_tenancy_schema.py` only *attributes* them in its `_TENANT_WIDE` map;
the creator is core's owner-run `bootstrap_notifications_tables`).

`api/flynapse_api/automations/worker.py` (production, UNCOMMITTED):
- New constants `NOTIFICATION_TABLES = ("notifications", "notification_subscriptions")` and
  `NOTIFICATIONS_BOOTSTRAP` (the dotted path named in the refusal). `notification_subscriptions`
  is included even though the worker's announcement path only writes `notifications`
  (`NotificationService.create` is a bare INSERT; no subscription read on this path — verified)
  because the two are one module with one creator: verify what the bootstrap owns.
- `bootstrap_tables`: bare call → bootstrap-then-verify (`bootstrap_notifications_tables()`
  then new `_require_notification_tables()`), before `_require_run_tables()`. The overruled
  ":182-183" comment replaced with the new contract ("the presence check that follows is what
  decides").
- New `_require_notification_tables()`: mirrors `_require_run_tables`'s seam exactly
  (call-time MRO import degrades to warning; `assert_tables_present` absence-`RuntimeError` →
  `WorkerBootstrapError` carrying the owner-bootstrap remedy; other exceptions degrade).
  Kept as a sibling, not extracted into a shared helper — two call sites, heavily divergent
  docstrings/remedies; rule of three.
- Module docstring + `bootstrap_tables` docstring updated (fatal now; announcements are
  load-bearing — the stand-down notice is the worker telling a human it stopped).

`api/tests/integration/automations/test_worker_entrypoint.py` (test edits, committable):
- `_patched_ddl` gained `notification_tables: bool = True` stubbing the new check
  ("notifications-present" journal entry); ordering test renamed →
  `test_bootstrap_runs_the_ddl_calls_then_requires_the_tables`, asserts
  `["automations", "notifications", "notifications-present", "run-tables"]`; run-table travel
  test's `called` assertion extended.
- Four new tests: present-check-by-name (real `assert_tables_present` over `FakePostgres`,
  information_schema reads only, zero writes, and the worker tuple pinned equal to core's
  `NOTIFICATION_TABLE_NAMES` so it cannot drift from what the bootstrap creates);
  missing-`notifications` refusal names the table and `NOTIFICATIONS_BOOTSTRAP` and does not
  blame the present sibling; travel test (`notification_tables=False`, empty fake) proves the
  refusal exits `bootstrap_tables` BEFORE the run-table check; parametrized
  could-not-check degrade (unimportable MRO package / check raised `OSError`) must not raise.

**Verification:** `tests/integration/automations/test_worker_entrypoint.py` 33/33 green;
`tests/startup/test_startup_boot_check.py` (parses worker.py) 20/20 green. Mutation proof:
removing the `_require_notification_tables()` call fails 2 tests (ordering + travel), restore
→ green. Adversarial subagent review run post-implementation; triage below. Post-triage
re-run: both files 53/53 green; `live_arc.py`/`live_retry.py` compile-checked.

### Adversarial review triage (2026-08-15)

Reviewer found spec compliance complete, exception-arm correctness byte-for-byte the
sibling's, no DDL reachable from any test, and no blast-radius breakage. Eight findings:

- **FIXED (real gap): the "both core bootstraps run at `core.fastapi_app` module scope"
  claim is dead** — `fastapi_app` no longer touches the notifications bootstrap at all, and
  the automations one runs inside the lifespan startup seed (`run_rbac_startup_seed`,
  `fastapi_app.py:207`), not module scope. My edits had re-blessed the stale sentence in
  worker.py's module docstring, the test file's header bullet, and the ordering test's
  docstring — all three reworded to the true mechanism ("neither reaches a bare worker on
  its own").
- **FIXED (nit): core docstring contradiction** — `postgres_init.py`'s "must not be on the
  boot path" now reads "must never be the *decision* on a boot path" and names the worker's
  bootstrap-then-verify usage. Also softened the worker's overstatements ("DDL cannot
  succeed" → converges where the connection holds DDL rights, e.g. a dev clone; refusal
  message reworded likewise).
- **FIXED (nit): cosmetic cross-repo pin** — the refusal test asserted copilot-mro's exact
  "not provisioned: X." prose; now asserts the absent name on `refusal.value.__cause__`
  (the checker's own message, where "notifications" cannot be vacuously present via the
  remedy), dropping the cosmetics coupling while staying non-vacuous.
- **FIXED (nit): test-name overclaim** — the notifications travel test now carries the same
  not-issubclass assertion as its run-table sibling, so "reaches the exit code" is proven,
  not implied.
- **FIXED (pre-existing prose): e2e harness comments** in `live_arc.py`/`live_retry.py`
  claimed the module-scope mechanism and named a `_bootstrap()` that is `bootstrap_tables`;
  reworded (the import blocker itself is unchanged — still correct as defense in depth).
- **FIXED (re-blessed sentence): `bootstrap_tables` docstring** claimed every call-time
  import degrades to a warning; only the MRO checker import does — the core imports are
  load-bearing and crash the boot. Docstring now says exactly that.
- **INTENTIONAL (recorded, no change): the degrade arm** — a worker whose MRO package is
  absent/broken still boots with an unverified bell. Spec-sanctioned (same seam as
  `_require_run_tables`, same reasoning: an import layout must not stop the clock).
  *Future improvement:* the asymmetry is real — these are core-owned tables verified via
  copilot-mro's checker; a core-local presence probe (~15 lines over `utils.postgres`,
  core already carries a copy in `core/tests/_schema.py`) would close the hole without
  touching the convention. Deferred: new core surface for a corner whose practical cost is
  low (a worker without copilot_mro fails loudly on its first dispatched run anyway).
- **OBSERVATION (resolved by this section): ledger header** said "not started" while the
  notes said DONE — header updated.
