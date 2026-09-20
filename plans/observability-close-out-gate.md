# Phase 11.6 — the close-out gate, made runnable

Prepared 2026-09-20. Read-only investigation. No plan, code or configuration was edited; three throwaway
databases were created and dropped, and no other state changed.

**The subject of this gate is the merged tree, not the mainline.** A, C1, B1, D, E and F are merged on branch
`obs-merge` inside the `<repo>-obsm` worktrees; every mainline checkout is still pre-merge (`core` on
`master`, `dashboard` on `agent_sdk`, `api`/`utils`/`copilot-mro` on `langgraph-merge`). Features this gate is
supposed to measure — `dashboard_profiles`, `product_events.schema_version`, the emitted-series inventory, the
New Relic profile, the Phoenix compose overlay — exist **only** in the `-obsm` worktrees. A lane run against a
mainline checkout measures a tree that does not have the feature and reports a false negative.

The environment rule from the merge plan therefore binds every row below: the shared `api` Poetry env installs
the five sibling packages by `.pth` files naming the **main** checkouts, so `PYTHONPATH` must name the merged
worktrees or the lane imports pre-merge code. Verified in this session: with
`PYTHONPATH=/home/aditya/Code/core-obsm:/home/aditya/Code/utils-obsm:/home/aditya/Code/copilot-mro-obsm`,
`core.__file__` resolves to `/home/aditya/Code/core-obsm/core/__init__.py` and `utils.__file__` to
`/home/aditya/Code/utils-obsm/utils/__init__.py`.

Two trees are being written in right now — `api-obsm` (C2) and `dashboard-obsm` (B2). Nothing below runs a
lane inside either; rows that depend on them are classified accordingly.

---

## Part 1 — The fixture-grant blocker

### What was reported

Two Task 11.6 lanes — the product-event replay and the `chat_turn_facts` backfill idempotency — were recorded
on 2026-09-17 as blocked before assertions by
`psycopg2.errors.InsufficientPrivilege: permission denied for table tenants`, with the note that the direct
`copilot_mro_test` retry "found no database".

### Reproduced

`cd /home/aditya/Code/api && DEBUG=false poetry run python ../core/scripts/run_db_lane.py
tests/db/analytics/test_product_events_store_db.py tests/db/analytics/test_chat_turn_facts_backfill_db.py`
→ **5 errors, `permission denied for table tenants`**, raised out of each file's `tenant`/`tenants` fixture.

### The precise cause

- **Which role.** `flynapse_grant`. Both fixtures create their tenant rows through `get_grant_service()`, the
  second pool in `utils/utils/postgres_service.py`, whose user comes from `Settings.postgres_grant_user`
  (`POSTGRES_GRANT_USER`, default `flynapse_grant`). It is not the app role and not the owner.
- **Which object.** `public.tenants` inside the throwaway database `core_dblane_*` that
  `core/scripts/run_db_lane.py` creates for the run.
- **Which grant.** All of them. Inspecting a retained scratch database: 17 tables, **every one owned by
  `flynapse_app`**, `tenants` with an empty ACL, RLS not enabled on it, and `flynapse_grant` not appearing as a
  grantee on any relation in the database. The role holds nothing there, so the first statement it issues fails.
- **Why.** `core/core/db/table_definitions.py` declares the canonical provisioning sequence in
  `PROVISION_SEQUENCE` — the migration **and then** `provision_rls.py` — and says in the same place that "every
  grant in the estate comes from `provision_rls.py`" and that the second half "is not optional for anything
  that READS through the app role". `run_db_lane.py` runs only the first half. It also deviates from
  `PROVISION_COMMAND` in two further ways: it creates the scratch database owned by `flynapse_app` and runs the
  migration as that role (the sequence says `--user postgres`), and it passes `--registry core` where the
  migration script's own docstring says a test database takes the default registries.

**The blocker is not the absence of a GRANT statement.** `GRANT_ROLE_PRIVILEGES` in
`copilot-mro/scripts/provision_rls.py` already names `"tenants": "SELECT, INSERT, UPDATE, DELETE"`, and the
live `copilot_mro_test` proves the script issues it — `flynapse_grant` holds exactly those four privileges on
`tenants` there today. A hand-issued `GRANT` at a psql prompt would be both redundant and reverted. The defect
is a caller that never invokes the owner of grants.

### One stale premise in the tree, and one in a plan

- `run_db_lane._provision`'s comment states that `provision_rls.py` "cannot run here: it refuses a core-only
  schema outright, because its write phases require `llm_usage`". `docs/plans/boot-ddl-endgame-and-resolver-collision.md`
  records the same as a deferral and proposes, as the complete fix, "teach `provision_rls.py` to operate on one
  registry's relations". **It has already been taught.** `verify_declared_relations_exist` skips a guarded
  relation that the selected `--registry` does not declare, with a notice rather than a finding. Measured:
  `provision_rls.py --registry core` against a core-only database ran to completion — `llm_usage is absent; no
  privileges to verify`, `llm_model_calls is absent; no privileges to verify`, `grants applied=19 … statements=111,
  committed`, exit 0. Both statements are now false.
- The 2026-09-17 note's fallback premise is also stale: `copilot_mro_test` exists, carries 112 public tables,
  and `flynapse_grant` holds its `tenants` privileges there.

### Proposed fix — location and shape

**Nothing changes in `provision_rls.py`.** It already owns and already issues the grant. The change belongs
entirely in **`/home/aditya/Code/core/scripts/run_db_lane.py`**, and it is to make the lane build its scratch
database the way the estate's own `PROVISION_SEQUENCE` says a database is built:

1. Create the scratch database owned by the **cluster owner** rather than the app role, and run the migration
   as the owner (`_create_scratch`, `_provision` — the owner credentials already resolve there through
   `utils.db_guard.owner_credentials()` for the admin connection).
2. Drop the `--registry core` narrowing and take the migration script's default registry selection.
3. Add the second half of the sequence: invoke `copilot-mro/scripts/provision_rls.py` against the scratch
   database, as the owner, with the same registry selection, and fail the lane if it exits non-zero.

The objection recorded in the script — that an owner-owned schema reads as EMPTY to the app role, because
`information_schema` is privilege-filtered — is exactly what step 3 removes, and `PROVISION_SEQUENCE`'s own
commentary says so. Two consequential documentation corrections travel with the change: the stale comment in
`_provision`, and the deferral paragraph in `boot-ddl-endgame-and-resolver-collision.md`.

### Proven, not proposed

| run | build | result |
|---|---|---|
| baseline, lane as it stands today | app-owned, `--registry core`, no `provision_rls` | **7 failed, 325 passed, 8 skipped, 2 xfailed, 232 errors**; causes: 116 × `permission denied for table tenants`, 118 × `Analytics relation(s) not provisioned`, plus two tests asserting that `flynapse_app` holds no writes on `tenants` (it owns the table there, so it does) |
| owner-owned + `--registry core` + `provision_rls --registry core` | — | product-event lane **3 passed**; backfill lane still fails — `relation "chats" does not exist` |
| owner-owned + `--registry core,copilot-mro` + matching `provision_rls` | — | both gate lanes **5 passed** |
| owner-owned + default registries + `provision_rls` (the proposal) | — | `tests/db` = **577 collected, 3 failed**, and those 3 are `test_seeded_head_role_dispatch_grant.py`, which states in its own assertion message that it requires a seeded estate; it fails on the current lane too |

Two things that matter beyond the grant:

- **The grant alone does not unblock the backfill lane.** `chat_turn_facts`, `chats` and `chat_blocks` are
  declared by the **copilot-mro** registry, and the analytics panel lanes additionally need `optimizer_jobs` /
  `optimizer_runs` from **shift-optimizer**. A `--registry core` scratch database cannot host either lane at any
  privilege level. This is why step 2 is part of the fix and not a nicety.
- **The reported blocker understates the damage.** It was written up as two blocked gate checks. It is in fact
  the whole of core's scratch `tests/db` lane — 232 errors and 7 failures, of which 116 errors are the grant and
  118 are the missing registries.

### And the gate does not have to wait for any of it

Both blocked lanes pass **today, with no code change**, against `copilot_mro_test`:

- pre-merge mainline: `tests/db/analytics/{test_product_events_store_db,test_chat_turn_facts_backfill_db,test_product_events_purge_db}.py` → **9 passed**
- merged tree (`core-obsm`, with `PYTHONPATH` naming the three merged worktrees): the same three files →
  **12 passed**; widened to `tests/db/analytics tests/api/analytics tests/unit/analytics` → **269 passed, 0
  failed, exit 0**

So the scratch-lane repair is a real defect worth fixing on its own merits, and it is **not** on the critical
path to running the gate.

### One database gap found while proving this

`copilot_mro_test` is one table behind the dev database: it carries 112 public tables and **lacks
`llm_turn_content`**, which `copilot_mro` (113 tables) has. Any lane exercising M-CAPTURE content capture
against the test database needs a re-migration first.

---

## Part 2 — The fifteen items

Task 11.6 carries eight checkboxes, one already ticked → **seven open checks (C1–C8, C6 ticked)**. The §6
review checklist carries nine, one already ticked → **eight open invariants (I1–I8)**. Fifteen open items. (The
merge plan's Phase F reconciliation calls this "16 boxes"; the count of *open* boxes is 15 — it appears to
include the ticked cardinality check.)

Commands are written relative to these constants:
`VENV=/home/aditya/Code/api/.venv/bin/python`,
`MERGED=/home/aditya/Code/core-obsm:/home/aditya/Code/utils-obsm:/home/aditya/Code/copilot-mro-obsm`,
and every pytest invocation carries `DEBUG=false POSTGRES_DB=copilot_mro_test ENV_FILE=/home/aditya/Code/api/.env`.

| id | Acceptance criterion (measurable) | Lane / command | Preconditions | Class | Existing coverage |
|---|---|---|---|---|---|
| **C1** two-tenant product-event replay | For two tenants: posting the same client `event_id` twice yields `accepted=1` then `duplicates=1` and exactly one row; the same `event_id` in two tenants yields two independent rows; a read bound to tenant B returns none of A's rows; an unbound insert raises rather than writing zero rows; the duplicate emits no second business log line | `cd core-obsm && PYTHONPATH=$MERGED $VENV -m pytest -q tests/db/analytics tests/api/analytics tests/unit/analytics` | Postgres container up; `copilot_mro_test` migrated with merged definitions | **runnable now** | **Fully covered and green (269 passed, verified today).** `test_replaying_an_event_is_a_duplicate_and_does_not_add_a_row`, `test_one_batch_carrying_the_same_event_id_twice_accepts_it_once`, `test_the_same_event_id_is_independent_in_two_tenants`, `test_bound_inserts_land_and_are_readable_only_under_their_tenant`, `test_an_unbound_insert_is_refused_not_silently_dropped`, `test_a_retried_event_is_reported_as_duplicate_and_only_logged_once`, `test_schema_version_is_the_servers_claim_not_the_clients` |
| **C2** two-tenant dashboard-profile matrix | For two tenants × each caller class: the effective panel set equals configured ∩ registered ∩ feature-enabled ∩ authorized, in registry order; an unknown panel fails closed; a panel hidden by profile is still refused by the panel endpoint; one tenant cannot read or alter another's profile row | core half: the C1 command (same lanes). Dashboard half: `cd dashboard-obsm && npm run test:unit` | Postgres; **B2 landed** for the render half | **split: core half runnable now; dashboard half after B2; third role needs something we do not have** | Core, all green today: `test_dashboard_profiles_db.py` (`test_one_tenant_cannot_read_another_tenants_profile`, safe-default, explicit-empty), `test_dashboard_profile_endpoint.py` (`test_profile_refuses_a_caller_without_dashboard_access`, `test_profile_derives_tenant_from_auth_context_not_query_params`), `test_dashboard_profiles.py` (11 resolver tests incl. capability intersection, owner-only, fail-closed, corrupt-column fallback). **Gaps:** no test crosses two tenants with the role axis, and "restricted administrator" is not a role that exists — see Part 5 |
| **C3** dual-runtime turn matrix and reconciliation | For `AGENT_RUNTIME=claude` and `=lang`, four turn classes (success, model error, tool error, unpriced usage): each turn produces a ledger row, a turn span and the turn/model metric points; the per-runtime counts agree between Postgres and traces without demanding one-to-one durability | `copilot-mro-obsm/tests/e2e/agent_runtime/run_runtime_parity_e2e.py`, run twice; plus a Postgres↔trace reconciliation that does not exist | Full stack, live Bedrock credentials, a collector with retrievable Tempo/Prometheus, both runtimes bootable | **needs something we do not have** | Behavioural only: 11 `test_cross_runtime_*_conformance.py` files and `test_cross_runtime_rehydration.py` in copilot-mro. **No telemetry or ledger parity test exists in core, dashboard, api, utils or copilot-mro.** The battery's own docstring refuses to attribute runtime from the ledger |
| **C4** single-host Docker POC, with and without Phoenix | The stack starts from `deployment/docker-compose.yml` alone and again with `-f docker-compose.phoenix.yml`; every service becomes healthy; peak container memory and CPU stay under a stated budget; the Phoenix-less run emits no Phoenix-bound pipeline | static half: the otel lane below. Live half: `OTEL_COMPOSE_SMOKE=1` with the otel lane, plus a manual `docker stats` capture | Docker; ports free; **an agreed budget number** | **split: shape runnable now; budget needs something we do not have** | Shape is covered: `test_compose_image_pins.py`, `test_compose_port_bindings.py`, `test_collector_profiles.py::test_every_collector_service_mounts_base_plus_overlay`, `test_smoke_network_scoping.py`, and `conftest.oss_smoke_stack`. Phoenix is a separate overlay in the merged tree (base compose has no `phoenix` service). **No resource limit exists in any compose file and no budget figure exists anywhere in the tree** |
| **C5** destination swap on identical images | For each supported profile, the same application image produces: identical required resource attributes; identical metric unit suffixes; an inbound `traceparent` continued end-to-end; redaction as the last step before `batch` on both log pipelines — and the destination differs only in the overlay | static: `cd api && PYTHONPATH=$MERGED poetry run pytest -q /home/aditya/Code/copilot-mro-obsm/tests/integration/otel`; then `bash copilot-mro-obsm/deployment/otel/validate.sh`; live: one retrieved canary per provider | Docker for `validate.sh`; **client credentials** for aws / azure / newrelic | **split: static runnable now (verified 132 passed, 26 skipped); live needs something we do not have** | Static, strong: `test_collector_profiles.py` (per-overlay specifics for oss/aws/azure/**newrelic**, complete-pipeline restatement, `test_every_log_pipeline_ends_with_redaction_before_batch`), `test_profile_env_documented.py`, `test_collector_base_config.py`, `test_collector_self_telemetry.py`. Units are pinned by the merged tree's new `test_emitted_series_inventory.py`. **Live retrieval exists for no provider** |
| **C6** metric cardinality *(already ticked)* | No user, session, chat, document or request identifier appears as a metric label or a span-metrics dimension; `tenant.id` appears only on approved tenant-scoped instruments | the otel lane above | none beyond Python | **runnable now for one limb; the other cannot be evaluated** | `test_collector_base_config.py::test_metric_cardinality_deletes_identity_and_path_keys` (nine keys), `test_tempo_span_metrics.py::test_no_per_span_or_identity_attribute_is_a_dimension` (`tenant.id` among the forbidden dimensions), `test_alert_environment_routing.py::test_remote_write_never_promotes_resource_attributes_to_series_labels`. **The approved tenant-scoped instrument list does not exist** — the master plan says so itself and assigns it to Task R.2. The tick covers the first limb only |
| **C7** refresh the catalogue's live/dark markers | Every series a canary retrieved is promoted from `wired` to `live` with a dated note in the grammar the lint enforces; nothing is promoted without a retrieval; no stale phase label survives; the board and rule lints pass against the refreshed inventory | the otel lane (grammar + agreement); the promotions themselves come from C4/C5 canaries | C4 and C5 live halves | **runnable after the canaries** | Mechanised in the merged tree: `_emitted_series.py` holds the one inventory in three states (`dark` / `wired` / `live`) with a per-state description grammar, `test_emitted_series_inventory.py` checks it against the emitter, and both `test_grafana_dashboards.py` and `test_alert_rules_layout.py` consume it. Current state: **14 declared series — 9 `wired`, 5 `dark`, 0 `live`**; 5 span signals, all `wired`. The 5 dark ones are exactly merge-plan G.6 (`agent.ledger.write_failures`, the two subagent instruments) and G.4 (two `claude_code.*`) |
| **C8** close the documents | Every master-plan checkbox matches the tree; the provider support matrix names only providers with a retrieved canary; residual risks and owner-run steps are current; unexecuted live checks remain visibly pending | documentation edit, then re-read | every other item resolved | **runnable now, meaningful last** | Nothing proves it. The merge plan's Phase F walk is the precedent: 181 open boxes, 119 of them already done in the tree |
| **I1** operational and product-event contracts stay separate | Product events reach Postgres through the authenticated API and never through the Collector; operational telemetry reaches the Collector and never the product tables; neither path reads the other's store | the C1 command + the otel lane + `cd dashboard-obsm && npm run test:unit` | B2 for the dashboard half | **runnable now (core + collector); dashboard half after B2** | Partial and indirect: `core-obsm/tests/unit/analytics/test_no_loki_references.py` (the product side reads no log store — **scoped to the `core` package only**), `exporter-ingest-routing.test.ts` / `ingest-contract.test.ts` (the browser posts product events to the API route, spans to the ingest route), the core forwarder suite under `tests/api/logging/`. **No single test states the invariant**; it is assembled from four |
| **I2** the profile exposes no vendor config and weakens no authorization | The profile response carries no exporter, endpoint, credential or vendor field; a panel absent from the profile is still refused by the panel endpoint for a caller who lacks it | the C1 command | Postgres | **runnable now — verified green** | Directly covered: `test_profile_response_contains_no_vendor_or_destination_metadata`, `test_profile_hidden_panel_is_still_refused_by_direct_panel_endpoint`, `test_profile_filtering_does_not_bypass_direct_panel_authorization`, `test_profile_allow_list_controls_sensitive_presentation_without_widening_access` |
| **I3** no provider is called production-supported from configuration alone | Every provider the documents mark supported has a retrieved trace, metric and log canary on file, dated; Azure carries an explicit go/no-go; the file-backed queue survives a collector restart | document review, gated on C5's live half and an 11.5 durability run | provider credentials; a restartable collector | **needs something we do not have** | Config is well covered (`test_collector_profiles.py`, `test_profile_env_documented.py`, the four `durability-production-*.yaml` overlays are statically asserted). **No canary, no restart proof, and no Azure ruling exist.** The master plan's claim that "Azure is marked production `NO-GO`" has no counterpart in the tree — corrected already in the plan, the gate itself still owed |
| **I4** no metric gains an unbounded identifier | The collector deletes the nine identity/path keys on every metrics pipeline in every profile; no identity attribute is a span-metrics dimension; remote-write does not promote resource attributes to series labels; every instrument's labels are declared | the otel lane | none | **runnable now for the bounded-set limb; the `tenant.id` limb cannot be evaluated** | Same tests as C6, plus the merged `test_emitted_series_inventory.py`, whose `KNOWN_LABELS` is `{agent_outcome, agent_department, gen_ai_request_model, gen_ai_token_type, gen_ai_provider_name}`. **The approved tenant-scoped instrument list and its cardinality bound do not exist** (Task R.2) |
| **I5** no product total treats sampled or expired telemetry as authoritative | Every analytics panel's data source is a Postgres relation; no analytics code path queries Loki, Prometheus or Tempo; retention/expiry of telemetry cannot change a reported product total | the C1 command | Postgres | **runnable now** | `core-obsm/tests/unit/analytics/test_no_loki_references.py` sweeps the whole `core` package for Loki fingerprints. Verified independently: no module under `core-obsm/core/resources/analytics/` references a telemetry store, and `dashboard-obsm/lib/api/analytics-api.ts` mentions Loki only in a retirement comment. **The guard is repo-scoped to `core`** — there is no equivalent in `dashboard` or `api` |
| **I6** no duplicate writer or projection for `chat_turn_facts` | Exactly one code path writes the relation; the projection is declared once and mirrored by a drift pin; adding a second writer fails a test | the C1 command, plus an estate-wide writer sweep | Postgres | **runnable now, and currently true; final evaluation waits on G.5** | Verified estate-wide (every `.py`/`.ts`/`.tsx`/`.sql` under `/home/aditya/Code` excluding `node_modules` and `.git`): the only non-test writer is `core*/scripts/backfill_chat_turn_facts.py`. `api`, `api-obsm`, `dashboard`, `dashboard-obsm`, `utils`, `utils-obsm`, `shift-optimizer` and `telegram-bot` contain no reference at all. Projection pinned by `test_chat_turn_facts_projection.py` and `test_chat_turn_facts_drift_pin.py`. **No online writer exists**, so the invariant is trivially satisfied and becomes meaningful only when G.5 lands |
| **I7** Docker-only and single-host stay explicit | No Kubernetes manifest, operator or Helm chart exists in the estate; no compose file declares a multi-host topology; the constraint is stated in the deployment documents | estate-wide sweep + the otel lane | none | **runnable now — passes** | Verified estate-wide: the only `kubernetes`/`helm` hits under `/home/aditya/Code` (excluding `node_modules`, `.git`) are one explanatory comment in `api/flynapse_api/config/config.py` and one line of a spec document. Compose shape is covered by `test_compose_port_bindings.py` and `test_smoke_network_scoping.py`. **No test enforces the absence** — it is a grep, not a guard |
| **I8** `otel-lgtm` remains deferred | No compose service, image pin, overlay or code path references `otel-lgtm` | estate-wide sweep | none | **runnable now — passes** | Verified estate-wide: every hit is in plan or spec markdown (`observability-rebuild.md`, the Phase 11 plan, `observability-merge-completion.md`, research 08, and one copilot-mro spec). **No test enforces the absence** |

---

## Part 3 — Sequencing

**Stage 0 — make the subject legible (must precede everything).**
Decide and record which tree the gate measures. Today that is the six `obs-merge` worktrees; if the intent is
to gate after a mainline merge, every command below changes its `PYTHONPATH` and nothing else. Assert the
resolved module path once, before trusting any number. Re-migrate `copilot_mro_test` so it carries
`llm_turn_content`.

**Stage 1 — everything static and everything Postgres, in parallel.** No ordering between these.

- Lane A (Postgres): C1, C2-core, I2, I5, I6 — one command, `core-obsm` analytics lanes. Green today, 269 tests.
- Lane B (static collector/boards): C5-static, C6, I4, and the grammar half of C7 — one command, the
  `copilot-mro-obsm` otel lane. Green today, 132 passed / 26 skipped.
- Lane C (sweeps): I7, I8 — two greps.
- Lane D (dashboard): the render half of C2 and the browser half of I1 — **blocked until B2 lands**.
- Lane E (api): nothing in the gate depends on C2-api directly, but the gateway hop tests under
  `api-obsm/tests/integration/otel` are the only evidence for trace propagation into the estate, so the gate
  should re-run them once C2 closes.

Treat a skip in Lane B as a failure: the 26 skips are the container-gated tests, and a run that reports them as
skips has not measured them.

**Stage 2 — the live stack, strictly ordered.**

1. C4 without Phoenix, then C4 with the Phoenix overlay. This is the first thing that produces retrievable
   signal, so nothing downstream can start before it.
2. C5 live, one destination at a time, each on the *same* image as the run before it — that identity is the
   property under test, so a rebuild between destinations voids the comparison. `oss` first (it is the only
   destination that needs no client credentials); the rest wait on credentials.
3. C3 last among the live checks. It needs a working stack *and* both runtimes *and* a reconciliation the
   estate cannot currently express.

**Stage 3 — the two items that can only close when everything else is green.**

- C7's promotions. A `wired` → `live` flip is a claim that a named probe retrieved the series on a named date;
  it is only truthful after Stage 2, and the lint will enforce the grammar but cannot enforce the truth.
- I3. A provider is production-supported when its canary is on file, which is Stage 2's output, plus the Azure
  ruling and the queue-restart proof, neither of which exists yet.

**Stage 4 — C8.** The documentation pass is last by definition: it records what the previous stages proved and
leaves visibly pending what they did not.

**What the gate must not rebuild.** C1, C2-core, C6, I2, I4-bounded, I5 and I6 are already measured by
per-phase tests that resolve and pass today. The gate's job for those rows is to run the existing lane against
the merged tree and record the number, not to write a second assertion of the same property.

---

## Part 4 — What cannot be proved, and why

1. **C3, runtime parity against the ledger.** `llm_model_calls` has no runtime column. Its 38 columns include
   `origin` (documented as "chat | automation", the AD-4 de-dup discriminator) and `graph_node` ("call-site
   label, when the request named one") — neither attributes a row to a runtime. The turn span *does* carry the
   runtime, as `gen_ai.agent.name`, and no metric carries it at all. So a reconciliation can group by runtime on
   the trace side and cannot on the Postgres side. Closing this needs either a runtime column on the ledger or
   the parity battery's manifest-based attribution promoted into the gate — a decision, not a test run.
2. **C4's resource budget.** There is no budget. No compose file in `copilot-mro-obsm/deployment` declares
   `mem_limit`, `cpus`, or a `deploy.resources` block, and the phrase "resource budget" appears in exactly two
   places in the estate, both of them the plan lines asking for it. The check has no pass condition until the
   owner states a number.
3. **C2's third role.** "Restricted administrator" does not exist. A case-insensitive search across every
   `.py`, `.ts` and `.tsx` file under `/home/aditya/Code` (excluding `node_modules` and `.git`) returns nothing.
   The estate's authorization axis is tenant owner versus capability holder, and that is what both the core
   registry tests and the dashboard registry tests exercise. Either the check is rewritten to the roles that
   exist, or a role has to be built first.
4. **C6 and I4's `tenant.id` limb.** The check asks that `tenant.id` appear only on "the explicitly approved
   tenant-scoped instruments". No such list exists — the master plan says so in its own constraints section and
   assigns it to Task R.2. Until R.2 produces the list and its cardinality bound, half of a ticked check and
   half of an invariant are unfalsifiable.
5. **I3, and C5's live half.** Every provider beyond `oss` needs client credentials the gate does not have, and
   the collector's file-backed queue has four `durability-production-*.yaml` overlays that are statically
   asserted and have never been restarted. The Azure go/no-go is an owner ruling with no evidence behind it in
   either direction.
6. **End-to-end browser trace.** `dashboard-obsm/tests/e2e/playwright/` holds eleven specs, none of them
   telemetry. Nothing anywhere exercises browser → Next route → api → core forwarder → collector as one trace;
   each hop is unit-tested in isolation. C5's "trace propagation" limb is therefore proved hop by hop and never
   end to end.
7. **I7 and I8 have no guard.** Both pass today and both are proved by a grep that nothing re-runs. A compose
   file adding `otel-lgtm` tomorrow breaks neither a test nor a lint.
8. **There is no acceptance harness.** `deployment/observability-acceptance/**` was dropped by ruling M-ACCEPT
   and does not exist anywhere under `/home/aditya/Code`. The gate is fifteen rows assembled from four existing
   entry points — the core analytics lanes, the copilot-mro otel lane, `deployment/otel/validate.sh` and
   `deployment/observability-local/validate-rules.sh` — plus a live stack. Whoever runs it is the harness.

### Where the source documents disagree with the tree

| claim | where | what the tree says |
|---|---|---|
| `provision_rls.py` "will not write against a core-only schema" / "cannot run here" | `run_db_lane._provision` comment; `boot-ddl-endgame-and-resolver-collision.md` deferral | It runs and commits. `--registry core` → grants applied=19, statements=111, exit 0 |
| "the direct `copilot_mro_test` retry found no database" | Phase 11 plan, Task 4 note 2026-09-17 | `copilot_mro_test` exists, 112 tables; both blocked lanes pass against it today |
| "Two of its checks are additionally blocked on a fixture grant" | merge plan §Phase F, item 1 | True but understated: the same two causes account for 232 errors and 7 failures across the whole scratch `tests/db` lane |
| "Azure is marked production `NO-GO`" | master plan §11.5 summary | No `NO-GO` marker in the tree; already corrected in the plan, the ruling is still owed |
| Phase 11.6 is "16 boxes" | merge plan §Phase F | 15 boxes are open; the sixteenth is the ticked cardinality check |
| Runbooks at `docs/runbooks/observability/` | master 6.5 | They are at `copilot-mro/docs/runbooks/observability/`; already recorded in the merge plan |
| "no test asserts instrument units" | true of the mainline checkout | False of the merged tree: `test_emitted_series_inventory.py` proves each instrument's declared unit against the emitter, because the unit is part of the exported name |
