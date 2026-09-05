# Postgres product-data inventory — what a client-facing dashboard could be rebuilt on

Research note, 2026-09-05. Lens: **durable data**. Companion to
`docs/plans/observability-rebuild-audit.md` (§2 ledgers, §5 the 10 live panels).

Scope rule: every factual claim carries a `path:line`. Repos are siblings under `/home/aditya/Code`;
paths below are workspace-relative. **READ-ONLY research — no DB was queried**, so every row-count
statement is "no sizing note found" rather than a measurement.

## 0. Orientation — where table definitions live

| Repo | Registry entry point | Notes |
|---|---|---|
| copilot-mro | `copilot-mro/copilot_mro/app/db/postgres_table_definitions.py:1-120` | Aggregates 22 modules under `postgres_table_definitions_modules/` (`:47-110` import block, `_DEFINITION_SOURCES` at `:113+`) |
| copilot-mro (legacy/db_query catalog) | `copilot-mro/copilot_mro/app/db/table_definitions.py` (389 L) | db_query schema-registry view, not DDL |
| core | `core/core/db/table_definitions.py` (1620 L) | Identity/RBAC/comments/notifications/automations |
| shift-optimizer | `shift-optimizer/shift_optimizer/app/db/table_definitions.py` (438 L) | 7 optimizer tables |
| shared DDL builder | `utils/utils/table_builder.py:620` `build_create_table_sql` | One implementation for all three repos (`postgres_table_definitions.py:17-31` re-exports it) |

**Tenancy vocabulary** (`utils/utils/table_builder.py:75-82`): `global` | `tenant` | `tenant+operator`.
The builder *injects* the tenancy columns; a definition never declares them
(`table_builder.py:148-160`: `tenant_id TEXT NOT NULL`, `operator_id TEXT NOT NULL DEFAULT '__ALL__'`)
and leads the primary key and every declared index with them (`table_builder.py:163-170`, index names
gain `_tnt` / `_tnt_op`). Policies compare against two session GUCs, `app.tenant_id` and
`app.operator_ids` (`table_builder.py:96-104`), always read as `current_setting(name, true)`.

---

# Part 1 — Table inventory (product-usage facts)

Every table below is `tenant`-class unless stated. "Private" means the definition declares no
`manual_type_scope`, so `table_business_function` returns `None` and the relation is never disclosed
to `database_reference` nor enters the `db_query` execution allowlist — a property every ledger and
chat table deliberately holds.

## 1.1 The LLM ledgers (copilot-mro) — the strongest analytics substrate that exists

### `llm_usage` — one row per orchestrator turn
`copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/llm_usage.py:73-191`

| Aspect | Fact |
|---|---|
| Grain | One row per orchestrator turn, PK `(tenant_id, block_id)` (`:132-138`) |
| Written | Inline at end of turn where `summarize_usage` produces the usage dict — **not** from `save_block`, so a turn that never persisted a block still books its spend (`:1-7`) |
| Tenant / dept / user | `tenant_id` (injected NOT NULL), `user_id`, `department` (MRO/PILOT/CREW), `chat_id` — all three nullable by design (`:76-78`, `:139-150`) |
| Timestamps | `started_at` (turn start, naive UTC, drives the day bucket), `created_at` (`timestamp DEFAULT now()`), both NOT NULL (`:116-117`) |
| Money | `sdk_cost_usd`, `direct_cost_usd`, `embedding_cost_usd`, `total_cost_usd` — all `numeric`, all nullable; **NULL = "not measured", never zero** (`:83-87`) |
| Completeness | `direct_unpriced_calls integer`, `cost_complete boolean NOT NULL` + CHECK `cost_complete=false OR (total_cost_usd IS NOT NULL AND direct_unpriced_calls = 0)` (`:88-90`, `:162-166`) |
| Tokens | `num_turns`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_hit_rate numeric` 0..1 (`:92-97`) |
| Direct-LLM volume | `direct_metered_input_tokens/output/cached`, `direct_metered_duration_s numeric` — explicitly **volume only, never a $/token denominator** (mixed token kinds, ~2.4× rate spread) (`:99-105`) |
| Embeddings | `embedding_tokens`, `embedding_calls` (API *requests*, not texts), `embedding_cache_hits`, `embedding_cache_tokens_avoided` (a LOWER BOUND), `embedding_cache_hits_unmeasured` (`:107-111`) |
| Outcome | `loop_error varchar` (max_turns / max_budget / exec outage / `exception:<Type>`; NULL on a clean turn), `is_error boolean NOT NULL` (`:113-114`) |
| Attribution | `origin varchar NOT NULL` CHECK `IN ('chat','automation')`, `automation_run_id` set iff origin=automation (`:67-68`, `:154-173`), `model varchar` = the SDK loop's model id (`:81`) |
| RLS | `tenancy: "tenant"` (`:131`); listed in `provision_rls.APPEND_ONLY_RELATIONS` — no role but the owner may UPDATE/DELETE (`copilot-mro/scripts/provision_rls.py:233-237`) |
| Indexes | `llm_usage_tenant_spend_day_idx ON llm_usage (tenant_id, (COALESCE(started_at, created_at)))` — the per-tenant daily spend sum; **must be spelled exactly as the aggregation predicate** or it silently falls back to a scan (`:178-189`) |
| Retention/GC | None found. No TTL column, no sweeper. |

**Aggregation rule (load-bearing, `:15-21`)**: `SUM(total_cost_usd)` silently skips NULL rows, so
every sum must carry `COUNT(*) FILTER (WHERE NOT cost_complete)` beside it. Any dashboard tile that
shows a dollar figure without a completeness co-metric reproduces, at the aggregate, the silent-$0
defect the per-call NULL policy exists to prevent.

**De-dup rule (`:34-45`)**: the tenant total is `SUM(total_cost_usd)` over `llm_usage` alone, every
origin — it counts each execution exactly once and never reads `automation_runs`. Reconciling
against `automation_runs` must key on `run_id` (not `block_id`, which is NULL on every failed run)
and must **aggregate `llm_usage` by `automation_run_id` first** — a retry re-opens the run row while
minting a fresh `block_id`, so an un-aggregated join multiplies that run's cost by its attempt count.

### `llm_model_calls` — one row per governed model attempt
`copilot-mro/.../postgres_table_definitions_modules/llm_model_calls.py:64-193`

| Aspect | Fact |
|---|---|
| Grain | One row per governed model attempt, PK `(tenant_id, call_id)` — surrogate, because `(turn, binding, attempt)` legitimately repeats within one turn (`:12-17`, `:126-128`) |
| Join back | `(tenant_id, turn_id)`; `turn_id` equals `block_id` whenever the turn had a block (`:67-68`) |
| Attribution | `chat_id`, `user_id`, `department`, `origin` (`chat`/`automation`/`sdk_loop`), `automation_run_id` — captured on the request path and passed as arguments, never read from ambient context (`:19-24`, `:69-73`) |
| Model dimensions | `binding` (role.purpose), `role`, `purpose`, `profile`, `profile_revision`, `registry_revision`, `provider`, `model`, `deployment` (for OSS rows = llm-platform serving tier), `region`, `account`, `attempt` (`:75-86`) |
| Tokens | `input_tokens`, `output_tokens`, `reasoning_tokens`, `cache_read_tokens`, `cache_write_tokens`, `tool_search_overhead_tokens` (`:88-93`) |
| Latency | `latency_seconds numeric` — provider-observed; NULL when unmeasured (`:95`) |
| Money | `cost_usd numeric` (NULL = unpriced), `cost_source` CHECK `IN ('provider_reported','versioned_pricing','unavailable')`, `cost_estimated boolean NOT NULL`, `usage_estimated boolean` (nullable — NULL on rows predating the column), `pricing_version` (`:96-103`, `:153-170`) |
| Outcome | `outcome varchar NOT NULL` — `success \| transient_error \| cancelled \| error \| budget_refused \| *_normalization_error`; **open vocabulary, the gateway owns it** (`:105`) |
| Placement | `graph_node`, `branch_id`, `provider_call_id` (`:106-108`) |
| Timestamps | `created_at timestamp DEFAULT now()` NOT NULL — the only time column (`:110`). **No `started_at`**, so time-of-call is the commit time. |
| RLS | `tenancy: "tenant"` (`:121`); `APPEND_ONLY_RELATIONS` (`provision_rls.py:233-237`) |
| Indexes | `llm_model_calls_tenant_turn_idx (tenant_id, turn_id)`; `llm_model_calls_tenant_day_idx (tenant_id, created_at)` (`:183-191`) |
| Post-create | `ALTER TABLE … ADD COLUMN IF NOT EXISTS usage_estimated boolean` (`:179-182`) |
| Retention/GC | None found. |

This is the table that makes **cost-per-model, cost-per-binding, latency percentiles, error-rate and
cache economics** answerable without touching a log store.

## 1.2 Chat cluster (copilot-mro) — the volume/adoption substrate
`copilot-mro/.../postgres_table_definitions_modules/chat.py`

| Table | Grain | Tenant/user/dept | Timestamps | Analytics columns | Indexes |
|---|---|---|---|---|---|
| `chats` (`:74-109`) | one chat | `tenant_id`, `user_id`, `department` (nullable) (`:26-28`) | `created_at`, `updated_at`, `last_activity`, `deleted_at` (`:30-35`) | `title text`, `total_blocks integer NOT NULL`, `deleted boolean NOT NULL`, `chat_data jsonb` (whole ChatInfo) | `chats_user_idx (tenant_id, user_id, department, last_activity DESC) WHERE deleted=false` (`:105-107`) |
| `chat_blocks` (`:112-142`) | one turn | `tenant_id`, `user_id` (no `department`) (`:42-43`) | `block_timestamp` (sort key), `created_at`, `updated_at`, `deleted_at` (`:44-49`) | `topic_segment_id`, `deleted`, **`block_data jsonb` (TOAST-backed) — the whole ChatBlock payload** (`:45-50`) | `chat_blocks_chat_idx (chat_id, block_timestamp) WHERE deleted=false` (`:138-140`) |
| `chat_feedback` (`:145-175`) | one thumbs event | `tenant_id`, `user_id` (`:56-57`) | `created_at` (`:59`) | `feedback_type varchar` = `up`/`down`, nullable; `block_id`; `feedback_data jsonb`; `deleted` (`:55-61`) | `chat_feedback_block_idx (block_id, tenant_id, user_id, created_at DESC, feedback_id DESC) WHERE deleted=false` (`:171-173`) |
| `chat_shares` (`:178-202`) | one share | `tenant_id`, `user_id` | `created_at` | `block_id`, `share_data jsonb` | **none** — "write-only cluster today (no read path)" (`:200-201`) |

All four `tenancy: "tenant"` (`:84`, `:118`, `:151`, `:184`) — deliberately not `tenant+operator`,
because one session legitimately traverses several operators (`:80-83`). All private (`:1-7`).
No retention/GC found; `deleted`/`deleted_at` are soft-delete flags and the payload is *retained*
on soft-delete (`:36`, `:50`).

> **The critical structural fact for a dashboard rebuild.** Route, intent, agent, tool calls,
> citations, latency and status are *not columns* — they live inside `chat_blocks.block_data` jsonb,
> which is TOASTed with **no expression index** (`llm_usage.py:9-13` says exactly this about the
> sibling usage blob: "summing a tenant's month is a full scan-and-detoast"). Any panel that needs
> those facts either needs a jsonb expression index, a generated column, or a new fact table.

## 1.3 Document Hub (copilot-mro)
`copilot-mro/.../postgres_table_definitions_modules/document_hub.py:79-395`

| Aspect | Fact |
|---|---|
| Table | `document_hub_documents` — one row per user-uploaded document; bytes in S3, chunks in Weaviate, **this row is the authority on who may see it** (`:1-8`) |
| Tenancy | **`tenant+operator`** (`:307`) — the only analytics-relevant table here with the operator axis. Four policies (SELECT/INSERT/UPDATE/DELETE); `__ALL__` rows are *shared*, so writing one needs the tenant's **full** operator entitlement (`:9-24`) |
| Department | `department_ids jsonb` NOT NULL + `sharing_scope` CHECK `IN ('private','tenant','department')` — an **app-level filter inside** the RLS envelope, not a second boundary (`:33-38`, `:66`, `:136-149`) |
| Lifecycle | `status` CHECK `IN ('processing','ready','needs_attention','deleted')` (`:55-60`, `:129-135`) |
| Processing facts | `processing_attempt integer NOT NULL >= 0`, `processing_started_at timestamp` (NULL = claimed but not begun; the stall fence reads `COALESCE(processing_started_at, updated_at)`) (`:234-252`), `failure_code varchar`, `failure_message text` (`:253-266`) |
| Content dims | `file_kind` CHECK `IN ('pdf','excel','csv','docx','image')`, `mime_type`, `size_bytes bigint >= 0`, `checksum_sha256`, `manufacturer`, `aircraft_family`, `document_type`, `account_context` (`:164-219`) |
| Source split | `source_scope` CHECK `IN ('library','chat_scoped')` + `source_chat_id` / `source_attachment_id` / `source_block_id` / `source_kind` — chat attachments have durable rows but never appear in the library listing (`:62-64`, `:94-128`) |
| Owner | `owner_user_id varchar NOT NULL` (`:87-93`) |
| Timestamps | `created_at`, `updated_at` (both NOT NULL), `deleted_at`, `processing_started_at` (`:267-287`, `:346-351`) |
| Indexes | 10 declared (`:358-393`) — including `document_hub_documents_status_list_idx (tenant_id, status, deleted_at, updated_at)` (directly serves a processing-throughput panel), owner-list, sharing-list, source-scope, taxonomy, manufacturer, aircraft-family, checksum, chat-scoped-attachment, and a GIN on `department_ids` |
| Retention/GC | Soft-delete only (`deleted_at`). No sweeper found. |
| Missing for analytics | **No open/view/download event.** There is no `document_hub_document_views` table anywhere in the registry. |

## 1.4 Automations (core) — scheduled runs and their settled spend
`core/core/db/table_definitions.py:1097-1338`

| Table | Grain | Analytics columns | Indexes |
|---|---|---|---|
| `automations` (`:1238-1277`) | one definition | `user_id`, `department`, `name`, `enabled`, `schedule jsonb`, `timezone`, `next_run_at`, `grace_seconds`, `max_runtime_seconds`, `max_budget_usd numeric`, denormalised `last_run_at` / `last_status`, `kind` (`chat` \| `ad_materialize`), `params jsonb` (`:1097-1141`) | `automations_tenant_user_next_run_idx (tenant_id, user_id, next_run_at)`; `automations_enabled_next_run_idx (next_run_at) WHERE enabled` (`:1264-1275`) |
| `automation_runs` (`:1280-1337`) | one attempted execution — "the spend audit trail" (`:1284`) | `scheduled_for`, `trigger` (`scheduled\|manual\|retry`), `started_at`, `finished_at`, **`duration_seconds integer`**, **`status`** (`claimed\|running\|completed\|failed\|…`), `reason`, `retry_after`, `attempts`, `late_run boolean`, **`queue_seconds integer`** (NULL = unmeasured), `chat_id`, `block_id`, `entitlements_used jsonb`, **`cost_usd numeric`**, `reserved_usd numeric DEFAULT 0`, `turns_used integer`, `error text`, `created_at`, plus one-shot columns `kind`/`params`/`user_id`/`max_runtime_seconds`/`operator_ids jsonb`/`result jsonb` (`:1152-1229`) | `automation_runs_claim_unique_idx (automation_id, scheduled_for)` UNIQUE; `automation_runs_active_status_idx (status) WHERE status IN ('claimed','running')`; **`automation_runs_tenant_spend_day_idx (tenant_id, (COALESCE(started_at, created_at)))`**; `automation_runs_open_reservation_idx`; `automation_runs_retry_due_idx` (`:1310-1335`) |

Both `tenancy: "tenant"` (`:1245`, `:1289`). Built-in system runs claim under a reserved
`__SYSTEM__` tenant, so they stay out of every real tenant's history and spend (`:1286-1288`).

**What `automation_runs.cost_usd` aggregates from**: it is the *settled spend for the run*
(`:1177`), and per `llm_usage.py:34-45` it books **the identical SDK cost a second time under the
same `block_id`** as the `llm_usage` row whose `origin='automation'`. It is therefore a
**duplicate**, not an independent term — a tenant total that summed both would double-count every
scheduled run. `reserved_usd` is the in-flight hold, nonzero iff `claimed`/`running` (`:1178`); the
day index is described as the "EXPOSURE sum (settled + reserved)".

## 1.5 Improvement loop (copilot-mro)
`copilot-mro/.../postgres_table_definitions_modules/improvement.py:28-184`

| Table | Grain | Analytics columns | Indexes |
|---|---|---|---|
| `improvement_signals` (`:81-109`) | one atomic evidence item | `source` CHECK `IN ('explicit','implicit','telemetry')`, `block_id`, `chat_id`, `user_id`, `user_kind` (`external`/`internal`), `candidate_targets jsonb`, `resolved_target`, `polarity`, `theme`, `detail jsonb`, `signature`, `batch_run_id`, `created_at` (`:28-44`) | `improvement_signals_run_idx (tenant_id, batch_run_id)`; UNIQUE `(tenant_id, signature)` (`:101-107`) |
| `improvement_findings` (`:112-148`) | one distilled work item | `kind` (`change_recommendation`/`orchestration_finding`), `target_kind`, `target_name`, `title`, `body`, `evidence jsonb`, `pattern_signature`, `recurrence integer >= 1`, `status` CHECK `IN ('open','triaged','fixed','dismissed')`, `reviewer`, `review_note`, `created_at`, `updated_at` (`:46-63`) | UNIQUE `(tenant_id, kind, target_name, pattern_signature)` (`:145-146`) |
| `improvement_runs` (`:151-175`) | one batch execution | `trigger` (`manual`/`scheduled`), `stage_outcomes jsonb`, `watermarks jsonb`, `signals_count`, `clusters_count`, `proposals_count`, `findings_count`, **`llm_spend numeric`**, `created_at`, `finished_at` (`:65-78`) | `improvement_runs_created_idx (tenant_id, created_at DESC)` (`:172-173`) |

All three `tenancy: "tenant"`, all private (`:7-15`). No retention/GC found.

**What `improvement_runs.llm_spend` aggregates from**: the definition says only "LLM cost (USD)
attributed to this run" (`:75`). Unlike `automation_runs.cost_usd`, `llm_usage`'s `origin` CHECK
admits **only** `chat` and `automation` (`llm_usage.py:154-157`), so improvement-loop spend has no
`origin` of its own in the per-turn ledger; `llm_model_calls` likewise admits only
`chat|automation|sdk_loop` (`llm_model_calls.py:149-151`). **`improvement_runs.llm_spend` is
therefore not reconcilable against either ledger by origin** — flag it as an open question rather
than a summable dimension.

## 1.6 Memory (copilot-mro)
`copilot-mro/.../postgres_table_definitions_modules/memory.py`

| Table | Grain | Tenancy | Analytics-relevant columns | Indexes |
|---|---|---|---|---|
| `memory_items` (`:316-435`) | one memory item | **`tenant+operator`** (`:335`) | `scope` (session/user/tenant), `type`, `category`, `department`, `user_id`, `chat_id`, `chat_block_id`, `topic_segment_id`, `signature`, `title`, `summary`, `payload jsonb`, `payload_version`, `status`, `created_at`, `updated_at`, `created_by`, `source` (user/manual/derived), `supersedes`, `last_verified_at`, `verification_status`, `effective_from`, `effective_to`, `success_score double precision`, `uses_count integer`, `last_used_at` (`:54-250`) | `memory_items_tenant_type_category_status_idx`; `memory_items_tenant_updated_at_idx`; `memory_items_user_pref_idx`; `memory_items_chat_segment_idx`; UNIQUE signature idx; `memory_items_block_id_idx`; two conditional UNIQUE idxs (user-pref-active, compaction) (`:398-430`) |
| `memory_item_events` (`:453-490`) | one lifecycle event | `tenant+operator` (`:456`) | `memory_item_id`, `event_type`, `actor_user_id`, `actor_source`, `metadata jsonb`, `created_at` (`:253-306`) | `memory_item_events_memory_item_idx`; `memory_item_events_tenant_idx`; `memory_item_events_event_type_idx` (`:483-488`) |

`memory_items` declares `tenant_grain_sentinel` — its `__ALL__` rows are tenant-grain (a person's own
preference has no operator to be entitled to), so its write rule admits the sentinel to any member of
the tenant (`document_hub.py:20-24`).

## 1.7 Identity / RBAC (core) — the "active users" denominators
`core/core/db/table_definitions.py:85-350`, definitions `:473-1095`

| Table | Grain | Key columns | Note for analytics |
|---|---|---|---|
| `tenants` (`:473-519`) | one account | `tenant_id`, `tenant_name`, `status`, `tenant_type` (airline, mro, …), `domain`, `created_at **text (isoformat)**` (`:85-101`) | `global`-class; RLS deliberately OFF (`provision_rls.py:_MISSING_RELATION_CONSEQUENCE`) |
| `operators` (`:521-607`) | one airline inside a tenant | `operator_id` (**surrogate — never resolve by literal id**), `name`, `iata_code`, `icao_code`, `country`, `timezone`, `owner_code`, `created_at timestamptz` (`:105-142`) | The department/airline dimension for an MRO tenant |
| `departments` (`:609-645`) | one department | `department_id`, `department_name` (keyed as `.strip().lower()`), `status`, `created_by`, `created_at text` (`:151-164`) | The "per department" grouping key a client admin wants |
| `users` (`:647-670`) | one user | `user_id`, `external_id`, `name`, `email`, `status` (default `pending`), `preferences jsonb`, `created_at text`, `updated_at text` (`:166-180`) | **`created_at` is `text` isoformat, not a timestamp** — see §4 caveat |
| `roles` (`:736-776`) | one role | `role_name`, `role_type` (custom/system), `department_id`, `persona`, `capabilities_add/remove jsonb`, `status` (`:182-204`) | |
| `user_departments` (`:778-809`) | membership | `user_id`, `department_id`, `joined_at text`, `status` (`:206-213`) | The user→department join for per-department rollups |
| `user_operators` (`:811-866`) | entitlement | `user_id`, `operator_id`, `granted_at text` (`:215-221`) | The operator entitlement set; app role is read-only on it |
| `user_roles` (`:908-941`) | grant | `user_id`, `role_id`, `department_id` (assignment scope, default `'All'`), `assigned_at text`, `status` (`:279-292`) | |
| `authorization_events` (`:868-906`) | one access change | `occurred_at **timestamptz**`, `actor`, `action` (grant/revoke/create/update/delete), `entity_kind`, `entity_id`, `subject_user_id`, `change jsonb` (`:223-276`) | Append-only (`provision_rls.py:233-237`). A genuine admin-audit feed. |
| `tenant_invitations` (`:672-734`) | one invitation | `email`, `status` (pending/accepted/revoked), `expires_at`, `accepted_by`, `accepted_at`, `refused_attempts`, `last_refused_at`, `created_at`/`updated_at` — all `timestamptz` (`:314-370`) | Directly answers "onboarding funnel" |

> **`users` has no login/session table.** There is no `sessions` relation anywhere in the three
> registries. "Active users" today is derived from log lines (audit §5 panel 2), and in Postgres the
> nearest durable proxy is `chats.last_activity` / `chat_blocks.block_timestamp` / `llm_usage.started_at`.

## 1.8 Comments & notifications (core)

| Table | Grain | Analytics columns | Def |
|---|---|---|---|
| `comments` | one comment | `document_id`, `content`, `author_id`, `author_name`, `author_email`, `parent_id`, `is_resolved`, `tags jsonb`, `mentions jsonb`, `visibility`, `page_number`, `position_x/y`, `thumbs_up integer` (trigger-maintained), `created_at`/`updated_at` **timestamptz** | fields `core/core/db/table_definitions.py:373-398`, def `:943-998` |
| `comment_thumbs_up` | one vote | `comment_id`, `user_id`, `created_at timestamptz` | `:400-410`, `:1000-1022` |
| `notifications` | one notification | **`operator_id`** (`__ALL__` = tenant-wide), `user_id` (NULL = broadcast), `type`, `payload_json jsonb`, `channels text[]`, **`read_at timestamp` (NULL = unread)**, `created_at` | `:412-432`, `:1024-1056` |
| `notification_subscriptions` | one subscription | `operator_id`, `user_id`, `notification_type`, `channels text[]`, `filters_json jsonb`, `enabled`, `created_at`/`updated_at` | `:434-456`, `:1058-1095` |

`notifications.read_at` makes an **engagement / read-rate** metric available with no new fact.

## 1.9 Data discovery (copilot-mro)
`copilot-mro/.../postgres_table_definitions_modules/data_discovery.py:412-505`

`data_discovery_jobs`, `tenancy: "tenant"` (`:451`), one row per discovery run over a registered
source. Analytics columns: `source_id`, `requester_user_id`, `status`, `stage`, `warning_summary`,
`failure_code`, `failure_message`, `object_count`/`table_count`/`column_count` (all
`integer DEFAULT 0 NOT NULL`), `attempt_count`, `level1_batch_count` /
`level1_completed_batch_count` / `level1_failed_batch_count`, `archived_at`, `created_at`,
`updated_at`, `started_at`, `completed_at` — **all timestamps are `timestamptz` here**, unlike the
surrounding registry, and the module says so explicitly (`:105-109`). Index
`data_discovery_jobs_tenant_recent_idx (tenant_id, archived_at, created_at DESC, job_id)` (`:504-505`).
Siblings: `data_discovery_connection_profiles`, `data_discovery_sources`,
`data_discovery_manifest_versions`, `data_discovery_table_index`, `data_discovery_schema_batches`,
`data_discovery_evaluation_templates`, `data_discovery_level2_runs`,
`data_discovery_level2_context_packages`.

## 1.10 Agent state (copilot-mro)
`copilot-mro/.../postgres_table_definitions_modules/agent_state.py:16-70`. One row per
`(tenant_id, chat_id, namespace, key)`; `payload jsonb` XOR `payload_s3_key`; `payload_bytes`,
`content_type`, `label`, `status`, `version`, `created_at`, `updated_at`, **`expires_at`**.
`tenancy: "tenant"` (`:44`). **The only table in this inventory with an explicit GC**:
`agent_state_expiry_idx ON agent_state (expires_at) WHERE expires_at IS NOT NULL` "serves the GC
sweep" (`:66-68`).

## 1.11 Shift-optimizer
`shift-optimizer/shift_optimizer/app/db/table_definitions.py`. All seven `tenancy: "tenant"`.
Product-usage-relevant: `optimizer_jobs` (`:127-167`, def `:274`) — `id`, `name`, `schedule_id`,
`activity_ids jsonb`, `role_ids jsonb`, `config_snapshot jsonb`, `pinned`, `created_by`,
`created_at`, `updated_at`; and `optimizer_runs` (`:169-193`, def `:287`) — `job_id`, **`status`
(`pending\|running\|completed\|failed`)**, `started_at`, `finished_at`, **`duration_seconds numeric`**,
`error text`, `launched_by`, `output jsonb`, `config_used jsonb`. That is a ready-made
run-outcome/throughput panel for the optimizer product with zero new facts.

## 1.12 Tables checked for and NOT found

| Looked for | Result |
|---|---|
| `sessions` / login-session table | **Not found** in any of the three registries |
| document view / open / download event | **Not found** — no `*_views`, `*_opens`, `page_view` relation |
| route / intent / query-type fact table | **Not found** — the audit's panel 6 sourced it from a log line |
| a `messages` table distinct from `chat_blocks` | **Not found** — the turn *is* the block |
| processing-jobs table for Document Hub | **Not found as its own relation** — processing state is columns on `document_hub_documents` (`status`, `processing_attempt`, `processing_started_at`, `failure_code`), and the executor is `automation_runs` with `kind='document_hub_process'` (`core/core/db/table_definitions.py:1190-1193`) |
| Document-hub Q&A relation | **Not found** — Q&A runs through the chat cluster |
| materialized views / rollup tables | **Not found** in any registry (see §4) |

*Method*: enumerated by grepping `"table_name": "<literal>"` across all three registries — 98 distinct
literals, none of them a session, view-event, page-view or `product_events` relation. Two families are
named dynamically and so do not appear as literals: the per-department document catalogs
(`mro_documents` / `pilot_documents` / `crew_documents`, `copilot-mro/.../postgres_table_definitions_modules/documents.py:1-22`)
and several `production_*` tables (`production_planning.py:11-20`). Neither family carries product-usage facts.

---

# Part 2 — The 10 existing panels, mapped to Postgres

Panel definitions and their LogQL live in
`core/core/resources/analytics/services/chat_quality_service.py:48-97` (constants) and `:701-742`
(`PANEL_DEFINITIONS`); the API is `GET /analytics/chat-quality`
(`core/core/resources/analytics/analytics_endpoints.py:43-46`), gated on `is_tenant_admin`
(`:31-41`). Every panel today is a Loki `query_range` (`:832-880`) + a Python aggregator.

Legend for **Buildability**: **A** = pure column SQL today; **B** = SQL over an existing `jsonb`
column (works, but needs an expression index or a rollup to be fast); **C** = needs a new
persisted fact.

| # | Panel | Today's source | Postgres source | SQL sketch (grouping only) | Build |
|---|---|---|---|---|---|
| 1 | Top 10 Users by Message Count | LogQL `^Enhanced chat request received$` (`:59-62`), emitted at `copilot-mro/copilot_mro/app/api/chat_management.py:987-992` (`POST /rag`, `:972`) and `:1303-1308` (`POST /rag/stream`, `:1289`) | `chat_blocks` (`chat.py:39-51`) joined to `chats` for `department`; or `llm_usage` which carries `user_id` + `department` on the row | `SELECT user_id, count(*) FROM chat_blocks WHERE tenant_id=$1 AND deleted=false AND block_timestamp >= $2 GROUP BY user_id ORDER BY 2 DESC LIMIT 10` | **A** |
| 2 | Active Users Over Time | LogQL, same log line (`:89-92`) | same | `SELECT date_trunc($bucket, block_timestamp) b, count(DISTINCT user_id) FROM chat_blocks WHERE … GROUP BY b` | **A** |
| 3 | Message Volume Over Time | duplicate LogQL of #1 (`:706-709`) | same | `SELECT date_trunc($bucket, block_timestamp) b, count(*) FROM chat_blocks WHERE … GROUP BY b` | **A** |
| 4 | LLM Token Consumption (+ the unrendered `estimated_cost` / `distinct_messages` / `total_llm_calls`) | LogQL `LLM request completed` (`:93-96`), emitted at `utils/utils/llm.py:417` — **direct calls only, SDK-loop-blind (audit G8)** | **`llm_usage`** (all token columns + real `total_cost_usd`) and/or **`llm_model_calls`** (per-model) | `SELECT date_trunc($b, COALESCE(started_at, created_at)) b, sum(input_tokens+output_tokens), sum(total_cost_usd), count(*) FILTER (WHERE NOT cost_complete) FROM llm_usage WHERE tenant_id=$1 … GROUP BY b` (index `llm_usage_tenant_spend_day_idx`) | **A — and strictly better than today**: the ledger sees the SDK loop, which the log line does not, and carries real dollars instead of an estimate. The `model_name` filter maps to `llm_model_calls.model`. |
| 5 | Chat Time Duration Histogram | LogQL `Chat response generated successfully` + `execution_time` (`:78-83`), emitted at `chat_management.py:1249-1253` (non-stream) and `:1652` (stream) | `chat_blocks.block_data -> 'assistant_response' ->> 'execution_time'` (the field is `AssistantResponse.execution_time`, `copilot-mro/copilot_mro/app/schemas/rag.py:686`, persisted whole inside `ChatBlock`, `:691-745`). Alternatively `routing_scoreboard.latency_ms` (below) | `SELECT width_bucket((block_data#>>'{assistant_response,execution_time}')::float, …) GROUP BY 1` | **B** — needs `CREATE INDEX … ON chat_blocks (((block_data#>>'{assistant_response,execution_time}')::float))` or a generated column, else every read detoasts. |
| 6 | Query Type Distribution | LogQL `^Tool Routing Decision$` (`:67-70`) — **that string exists nowhere in the estate except this query** (verified: only hit is `chat_quality_service.py:68`). Confirms audit G7. | **Already durable, twice.** (a) per-turn: `chat_blocks.block_data->'metadata'->'routing_scoreboard'->>'query_type'` — built by `copilot-mro/copilot_mro/app/services/agent_shared/scoreboard.py:71-108`, lifted onto the block at `copilot-mro/copilot_mro/app/api/chat_management_helper.py:189-193`, gate `AGENT_SDK_ENABLE_SCOREBOARD` **default True** (`copilot-mro/copilot_mro/app/config.py:922`). (b) pre-aggregated: a `memory_items` row per `(query_type, department)`, `type='routing_scoreboard'`, written by `copilot-mro/copilot_mro/app/services/agent_shared/tools/synthesis/scoreboard_aggregate.py:1-16`, gate `AGENT_SDK_ENABLE_SCOREBOARD_AGGREGATE` **default True** (`config.py:937-939`) | (a) `SELECT block_data#>>'{metadata,routing_scoreboard,query_type}' qt, count(*) … GROUP BY qt`; (b) `SELECT payload->>'query_type', (payload->>'count')::int FROM memory_items WHERE tenant_id=$1 AND type='routing_scoreboard'` | **B → A.** The panel is not dead in the data, only in the query. Route (b) is already a rollup table and needs no scan at all — but it is **all-time cumulative, not windowed**, so a `1h/1d/1w` range needs route (a). |
| 7 | Most Accessed Documents | LogQL `page_view` (`:71-77`) — a **frontend** log emitted by `dashboard/lib/logging/page-tracking.ts:62-69`, whose delivery is commented out (audit G1), so the panel is dark | **Needs a new fact.** No `document_hub_document_views` / `page_view` relation exists in any registry. Two candidate substitutes, neither equivalent: (i) *cited* documents per turn from `chat_blocks.block_data->'document_batch'` / `->'citations'` (`rag.py:694-716`) — that is "documents the assistant used", not "documents a human opened"; (ii) nothing at all for a manual/doc viewer open. | new fact — see below | **C** |
| 8 | Feedback Received Over Time | LogQL `^Response feedback saved successfully$` (`:63-66`), emitted at `copilot-mro/copilot_mro/app/api/user_feedback.py:262-268` (`POST /response/feedback`, `:217`) | **`chat_feedback`** (`chat.py:53-62`) — the same handler already writes it via `chat_db.save_response_feedback` (`user_feedback.py:250-259`) | `SELECT date_trunc($b, created_at) b, feedback_type, count(*) FROM chat_feedback WHERE tenant_id=$1 AND deleted=false … GROUP BY b, feedback_type` | **A** — the durable row is written on the same code path as the log line, so this panel is a pure substitution. Note the log normalizes `thumbs_up`/`thumbs_down` (`chat_quality_service.py:339-350`) while the column stores `up`/`down` (`chat.py:58`). |
| 9 | Top 10 Users by Comment Count | LogQL `^Successfully created comment$` (`:84-88`), emitted at `core/core/resources/comments/comments_endpoints.py:312` | **`comments`** (`core/core/db/table_definitions.py:373-398`) | `SELECT author_id, count(*) FROM comments WHERE tenant_id=$1 AND created_at >= $2 GROUP BY 1 ORDER BY 2 DESC LIMIT 10` | **A** |
| 10 | Comments Created Over Time | duplicate LogQL of #9 (`:730-733`) | same | `SELECT date_trunc($b, created_at) b, count(*) FROM comments … GROUP BY b` | **A** |

**Score: 8 of 10 panels are computable from Postgres today** (6 pure-column A, plus #5 and #6 as
jsonb reads). Only panel 7 needs a genuinely new fact.

## 2.1 The one new fact panel 7 needs

| Question | Answer |
|---|---|
| What event | A **document open / view**: `(tenant_id, operator_id, user_id, department, document_id, document_kind, opened_at, source_surface)`. `document_kind` matters because the estate has two document populations — `document_hub_documents` uploads and the manual corpus addressed by the `*_documents` catalogs (`copilot-mro/.../postgres_table_definitions_modules/documents.py:1-22`) — and the dead LogQL matched both via `pageId=~"^/(mro\|pilot)/document/.*"` (`chat_quality_service.py:74`). |
| Who observes it today | **Only the browser.** `dashboard/lib/logging/page-tracking.ts:42-69` `trackPageView()` fires `logger.info('page_view', {pageId, pageViewCount, sessionDuration, …})`, and `trackPageExit()` (`:71-79`) already computes **dwell time** — a fact the current panel never used. There is no backend handler for a document open: no route in `copilot-mro/copilot_mro/app/api/` or `core/core/resources/` observes it. |
| Cheapest honest fix | Give the existing frontend ingest a durable sink. `core/core/resources/logging/logging_endpoints.py` already receives frontend logs (audit §1); a narrow `POST /analytics/events` writing a typed `product_events` row is a smaller change than restoring the whole log pipeline, and it survives the Loki retirement. Restoring `logger.flush()` alone (audit G1, `dashboard/lib/logging/logger.ts:233-243`, `:257-266`) fixes the panel **but leaves it Loki-bound**, which is the thing the owner is retiring. |
| Second new fact worth capturing at the same time | **Session duration** — `page-tracking.ts:64-66` already carries `sessionDuration`, and there is no `sessions` table anywhere (Part 1 §1.12). One `product_events` row type covers open, exit/dwell and session close. |

## 2.2 Facts the panels don't ask for but are already durable

| Fact | Where | Note |
|---|---|---|
| Real per-turn USD | `llm_usage.total_cost_usd` + `cost_complete` | Panel 4 shows an `estimated_cost` it never renders; the ledger has the settled figure |
| Loop/turn failure | `llm_usage.is_error`, `llm_usage.loop_error` | No panel shows error rate at all |
| Per-model / per-binding cost & latency | `llm_model_calls.model` / `.binding` / `.latency_seconds` / `.cost_usd` / `.outcome` | Whole dimension unused |
| Tool usage mix + per-tool failure | `block_data->'metadata'->'tool_call_log'` ({name,label,ref,is_error}, `chat_management_helper.py:141-149`); rolled up as `status_counts` (succeeded/failed/pending) in the scoreboard (`scoreboard.py:25-46`) | Persisted whole — the 50-entry cap was removed with the DynamoDB item limit |
| Answered / not-answered | `block_data->'metadata'->'answer_found'` + `confidence_probability` (`chat_management_helper.py:122-126`), and `routing_scoreboard.answer_found` / `.capability_outcome` | The strongest quality signal in the system, unrendered anywhere |
| Clarification rate | `block_data->'metadata'->'needs_clarification'` (`:131-133`) | |
| **Session id** | `block_data->'metadata'->>'session_id'` — stamped at save time by `copilot-mro/copilot_mro/app/db/chat_history/blocks.py:541-544` | The only durable session handle in the estate. With `block_timestamp` it yields turns-per-session and session span, which is the nearest thing to "session duration" without a new fact. |
| Cache economics | `llm_usage.cache_hit_rate`, `cache_read_input_tokens`, `embedding_cache_*` | |

**Serialization shape.** `block_data` is `ChatBlock.model_dump(mode="json")` (`copilot-mro/copilot_mro/app/db/chat_history/blocks.py:541`), so every jsonb path above is the pydantic field name verbatim (`rag.py:691-745`). There is already precedent for querying it in SQL rather than in Python: `blocks.py:205-212` runs `jsonb_path_query_first` / `jsonb_path_exists` against `block_data`.

---

# Part 3 — Candidate views for a CLIENT ADMIN (airline / MRO tenant admin)

Buildability legend as in Part 2 (**A** column SQL, **B** jsonb read, **C** new fact).
"Value" is judged for the tenant admin of an airline or MRO — the person who signs the invoice,
answers "is this being used", and has to justify the seat count.

## 3.1 Ranked candidates

| Rank | View | Backed by (exact) | Grain | Why a client admin cares | Build |
|---|---|---|---|---|---|
| 1 | **Spend by department / user / model** | `llm_usage` (`total_cost_usd`, `cost_complete`, `department`, `user_id`, `model`, `started_at`) + `llm_model_calls` (`model`, `provider`, `binding`, `cost_usd`, `cost_source`) | one turn / one attempt | The invoice line. Today nothing in the product shows a client what it spent, on what. | **A** |
| 2 | **Adoption — WAU / MAU, active users per department, new users** | `chat_blocks (tenant_id, user_id, block_timestamp)`; `users`; `user_departments`; `llm_usage.department` for the department axis (`chat_blocks` has no `department` column — `chat.py:39-51`) | day / week / month bucket | Seat-utilisation. Answers "who is actually using what we bought". | **A** |
| 3 | **Answer quality — answered / unsure / not-answered rate + confidence** | `chat_blocks.block_data->'metadata'->>'answer_found'` and `->>'confidence_probability'` (`chat_management_helper.py:122-126`); or `->'routing_scoreboard'->>'answer_found'` / `capability_outcome` (`scoreboard.py:96-99`) | one turn | The single most decision-relevant metric a client has: *is the copilot answering my people's questions?* Nothing renders it today. | **B** |
| 4 | **Feedback rate + negative drill-down** | `chat_feedback (feedback_type, block_id, user_id, created_at)` joined to `chat_blocks` for the question text (`block_data#>>'{user_message,content}'`, `rag.py:369-375`) and `feedback_data jsonb` for the free-text comment | one feedback event → one turn | Lets the admin read the actual complaints, not just a count. Today panel 8 shows only the count. | **A** (drill-down is **B**) |
| 5 | **Error & loop-failure rate** | `llm_usage.is_error` / `loop_error` (`llm_usage.py:113-114`); `llm_model_calls.outcome` (`success \| transient_error \| cancelled \| error \| budget_refused \| *_normalization_error`, `llm_model_calls.py:105`) | turn / attempt | Reliability SLO the client can hold us to. `loop_error` distinguishes `max_turns` / `max_budget` / outage. | **A** |
| 6 | **Latency percentiles per model / binding / route** | `llm_model_calls.latency_seconds` (`:95`), grouped by `model` / `binding` / `graph_node`; end-to-end from `block_data#>>'{assistant_response,execution_time}'` or `routing_scoreboard.latency_ms` | attempt / turn | "Is it fast enough?" — percentile, not mean, because `latency_seconds` is NULL when unmeasured and a mean hides the tail. | **A** (per-call) / **B** (end-to-end) |
| 7 | **Document Hub processing throughput & failure rate** | `document_hub_documents (status, failure_code, processing_attempt, processing_started_at, created_at, updated_at, file_kind, size_bytes)` — index `document_hub_documents_status_list_idx (tenant_id, status, deleted_at, updated_at)` already serves it; per-run detail from `automation_runs WHERE kind='document_hub_process'` (`copilot-mro/copilot_mro/app/services/document_hub/jobs.py:101`) with `duration_seconds`, `queue_seconds`, `attempts`, `status`, `error` | one document / one processing run | An admin who uploads 200 manuals wants to know how many are `ready`, how many `needs_attention`, and why. All four facts are columns. | **A** |
| 8 | **Automation run outcomes & spend** | `automation_runs (status, reason, trigger, late_run, duration_seconds, queue_seconds, attempts, turns_used, cost_usd, reserved_usd, error, scheduled_for, started_at, finished_at)` + `automations (name, enabled, department, max_budget_usd, next_run_at)` | one run | Scheduled work is invisible to the user by definition — this is the only place they see it ran, succeeded, and what it cost. `automations.max_budget_usd` gives a spend-vs-budget gauge for free. | **A** |
| 9 | **Cache-hit savings** | `llm_usage.cache_hit_rate`, `cache_read_input_tokens`, `cache_creation_input_tokens`; embeddings via `embedding_cache_hits`, `embedding_cache_tokens_avoided`, `embedding_cache_hits_unmeasured` (`llm_usage.py:92-111`) | one turn | A cost-reduction story told with our own numbers. **Caveat to render honestly**: `embedding_cache_tokens_avoided` is a documented **lower bound** whenever `embedding_cache_hits_unmeasured > 0` (`:110-111`), so the tile must show both. | **A** |
| 10 | **Tool-usage mix + per-tool failure** | `block_data->'metadata'->'tool_call_log'` ({name, label, ref, is_error}, `chat_management_helper.py:141-149`); pre-rolled per turn as `routing_scoreboard.tool_set` / `tool_sequence` / `tool_count` / `status_counts{succeeded,failed,pending}` (`scoreboard.py:88-95`, `:25-46`) | one turn | Shows which of the capabilities they paid for are actually exercised — and which tools fail. `pending` is a real third state (turn ended mid-flight), not a rounding error. | **B** |
| 11 | **Top questions / intents** | intent: `routing_scoreboard.query_type` (per-turn) or the cumulative `memory_items` aggregate (`type='routing_scoreboard'`, `payload->>'count'`); raw text: `block_data#>>'{user_message,content}'`; `chats.title` for a cheap human-readable proxy | turn / query_type | Content-gap discovery: the questions the corpus does not answer are the manuals they should buy or ingest next. Pair with #3 for "top *unanswered* questions". | **B** |
| 12 | **Source / document citation frequency** | `block_data->'citations'` → `Citation.document` / `doc_uid` / `manual_type` / `page` (`rag.py:403-423`), and `block_data->'document_batch'` (`DocumentCard`) | one citation | The honest replacement for the dead "Most Accessed Documents" panel: *which manuals the answers actually rest on*. Different question from "which documents a human opened" — say so on the tile. | **B** |
| 13 | **Onboarding funnel** | `tenant_invitations (status, created_at, accepted_at, accepted_by, expires_at, refused_attempts, last_refused_at)` — all `timestamptz` (`core/core/db/table_definitions.py:314-370`) | one invitation | Admin-owned workflow with an admin-owned failure mode: `refused_attempts > 0` exists precisely so the owner can see an invitation sent to the wrong address (`:355-366`). | **A** |
| 14 | **Collaboration — comments & resolution** | `comments (author_id, document_id, is_resolved, parent_id, thumbs_up, created_at)`, `comment_thumbs_up` | one comment | Extends the two existing comment panels into something actionable: unresolved threads, most-annotated documents. | **A** |
| 15 | **Memory growth & usefulness** | `memory_items (type, category, scope, status, created_at, uses_count, success_score, last_used_at)`; lifecycle from `memory_item_events (event_type, actor_user_id, created_at)` | one memory item / event | "The system is learning our fleet" is a retention argument; `uses_count` / `last_used_at` make it measurable rather than a claim. **Caveat**: `tenant+operator`, so a partially-entitled admin sees a partial count (see §4.4). | **A** |
| 16 | **Notification engagement** | `notifications (type, user_id, read_at, created_at, channels)` — `read_at IS NULL` = unread | one notification | Read-rate per notification type tells the admin whether AD/compliance alerts are landing. | **A** |
| 17 | **Retention cohort** | derived: `min(block_timestamp) OVER (PARTITION BY tenant_id, user_id)` from `chat_blocks` as first-activity, cohorted by month | one user | The classic cohort grid. **Do not use `users.created_at`** — it is `text` isoformat (`core/core/db/table_definitions.py:173`), so it neither ranges nor sorts correctly; the registry documents exactly this hazard for a sibling column (`:225-236`). | **A** (with the caveat) |
| 18 | **Access-change audit** | `authorization_events (occurred_at timestamptz, actor, action, entity_kind, entity_id, subject_user_id, change jsonb)` (`:223-276`) — append-only (`provision_rls.py:233-237`) | one access change | Compliance-grade "who granted whom what, when". An airline's quality department will ask for exactly this. `change` is `jsonb` specifically so "which role edits added capability X" is one containment predicate (`:263-268`). | **A** |
| 19 | **Data-discovery job health** | `data_discovery_jobs (status, stage, failure_code, warning_summary, object_count, table_count, column_count, attempt_count, level1_*_batch_count, started_at, completed_at)` — all `timestamptz` | one job | Only relevant to tenants who connected their own database; for those it is the whole onboarding status page. | **A** |
| 20 | **Improvement-loop transparency** | `improvement_findings (status, target_name, recurrence, updated_at)`, `improvement_signals (source, polarity, theme)`, `improvement_runs (signals_count, findings_count, llm_spend, created_at, finished_at)` | finding / signal / run | "Here is what your feedback changed." **Decide first whether this is client-facing at all** — `improvement_findings` is documented as "internal-only work items" (`improvement.py:117`). A count and a theme distribution can be shown; the bodies probably cannot. | **A**, but a product decision first |
| 21 | **Optimizer run outcomes** | `optimizer_runs (status, started_at, finished_at, duration_seconds, error, launched_by)` + `optimizer_jobs` (`shift-optimizer/.../table_definitions.py:127-193`) | one run | Same shape as #8, different product. Free if the tenant has the optimizer. | **A** |
| 22 | **Document opens, dwell time, session duration** | **needs new fact** — see Part 2 §2.1. Nothing durable exists. | one view / one session | The only genuinely missing pillar: everything above measures the *assistant*, nothing measures the *reading* product. | **C** |

## 3.2 What ranking 1-22 implies for sequencing

| Tranche | Contents | Why together |
|---|---|---|
| **T1 — ship first, zero new writes** | #1, #2, #4, #5, #7, #8 | Pure column SQL over already-indexed `(tenant_id, <time>)` prefixes. Replaces 8 of the 10 Loki panels and adds cost, errors and processing health. |
| **T2 — one jsonb accessor investment** | #3, #10, #11, #12, and panels 5 & 6 from Part 2 | All read `chat_blocks.block_data`. Do them as one piece of work — a single set of generated columns / expression indexes (or a `chat_turn_facts` projection table) unlocks all of them at once. |
| **T3 — new fact** | #22 | Needs a `product_events` sink and a frontend→backend contract. |

## 3.3 The one honest caveat to put on every money tile

`llm_usage.py:15-21` makes it a rule, not a preference: **`SUM(total_cost_usd)` skips NULL rows
silently.** Every dollar figure this dashboard renders must carry
`COUNT(*) FILTER (WHERE NOT cost_complete)` — as "£X across N turns, M of which are not fully
priced". A tile that omits it is wrong in the same way the per-call silent-$0 defect was.

---

# Part 4 — Aggregation design facts

## 4.1 Index rewriting — what the declared index actually becomes

`utils/utils/table_builder.py:736-774` (`prefix_index_statements`) rewrites every declared
`CREATE INDEX` to **lead with the tenancy columns**, under a new name (`_tnt` / `_tnt_op` suffix,
`:161-166`) plus a `DROP INDEX IF EXISTS` of the predecessor. `_rewrite_index` (`:995-1029`) strips
any tenancy column already present in the tail before prepending, so no column is duplicated. Two
exemptions returned verbatim: an index already led by the tenancy columns, and any non-btree access
method (`USING gin/gist/hash/brin`) — because `btree_gin` is not installed (`:751-757`).

So a definition's `indexes` list is a statement of *suffix* columns; the tenant prefix is free.

## 4.2 Existing `(tenant_id, <time>)`-shaped indexes — the ones an analytics API can lean on

| Index (effective shape) | Table | Serves |
|---|---|---|
| `llm_usage_tenant_spend_day_idx (tenant_id, (COALESCE(started_at, created_at)))` | `llm_usage` | per-tenant daily spend. **Must be spelled exactly as the aggregation predicate** or a hand-written variant silently falls back to a scan (`llm_usage.py:178-189`) |
| `llm_model_calls_tenant_day_idx (tenant_id, created_at)` | `llm_model_calls` | per-tenant daily per-call slice (`llm_model_calls.py:189-191`) |
| `llm_model_calls_tenant_turn_idx (tenant_id, turn_id)` | `llm_model_calls` | join back to the turn (`:186-187`) |
| `automation_runs_tenant_spend_day_idx (tenant_id, (COALESCE(started_at, created_at)))` | `automation_runs` | per-tenant daily exposure (settled + reserved), same expression discipline (`core/core/db/table_definitions.py:1323-1327`) |
| `improvement_runs_created_idx (tenant_id, created_at DESC)` | `improvement_runs` | run history (`improvement.py:172-173`) |
| `memory_items_tenant_updated_at_idx` | `memory_items` | recency scans (`memory.py:400-401`) |
| `data_discovery_jobs_tenant_recent_idx (tenant_id, archived_at, created_at DESC, job_id)` | `data_discovery_jobs` | recent jobs (`data_discovery.py:504-505`) |
| `document_hub_documents_status_list_idx (tenant_id, status, deleted_at, updated_at)` | `document_hub_documents` | status rollups (`document_hub.py:361-362`) |
| `chats_user_idx (tenant_id, user_id, department, last_activity DESC) WHERE deleted=false` | `chats` | per-user chat list, and (leading-prefix) per-user counts (`chat.py:105-107`) |

**The gap.** The chat cluster — the substrate for panels 1, 2, 3 and every adoption view — has
**no `(tenant_id, <time>)` index**:

| Table | Effective index | Missing for analytics |
|---|---|---|
| `chat_blocks` | `chat_blocks_chat_idx_tnt (tenant_id, chat_id, block_timestamp) WHERE deleted=false` (`chat.py:138-140`) | a `(tenant_id, block_timestamp)` (or `(tenant_id, block_timestamp, user_id)`) index. Without it, "message volume this month" scans every block of the tenant across every chat. |
| `chat_feedback` | `chat_feedback_block_idx_tnt (tenant_id, block_id, user_id, created_at DESC, feedback_id DESC)` (`:171-173`) | a `(tenant_id, created_at)` index for the time-bucketed feedback panel; the existing one is only usable with a `block_id`. |
| `chat_shares` | **none at all** — "write-only cluster today (no read path)" (`:200-201`) | everything, if shares ever become a metric |
| `comments` | `comments_doc_created_idx_tnt (tenant_id, document_id, created_at DESC)`, `…_doc_updated_idx`, `…_doc_thumbs_idx`, `comments_author_idx_tnt (tenant_id, author_id)`, `comments_parent_idx_tnt` (`core/core/db/table_definitions.py:988-995`) | panel 9 (top authors) is served by `comments_author_idx_tnt`; panel 10 (volume over time) has **no `(tenant_id, created_at)`** index — every time index here is `document_id`-led. |

Adding those indexes is a one-line change per table in the definition's `indexes` list; the builder
does the tenant prefixing.

## 4.3 Rollups and materialized views

| Question | Answer |
|---|---|
| Any materialized view? | **None** in any of the three registries. |
| Any rollup table? | **One, and it is not general-purpose**: the routing-scoreboard aggregate — a `memory_items` row per `(query_type, department)`, `type='routing_scoreboard'`, upserted off-path by `copilot-mro/copilot_mro/app/services/agent_shared/tools/synthesis/scoreboard_aggregate.py` (CAS on `payload_version`, `:1-16`), payload maintained by the pure `merge_scoreboard_payload` (`scoreboard.py:120-160`): `count`, Yes/Unsure/No `outcomes`, running means `avg_confidence` / `avg_retry` / `avg_latency_ms` each with its own `n_*`, and a `tool_sets` fingerprint histogram. **Cumulative, not windowed** — there is no time bucket in the key, so it cannot answer "last 7 days". |
| Any plain view? | One: `production_shift_roster` (`copilot-mro/.../production_planning.py:909-961`), a VIEW over the workforce tables. |
| **Can a materialized view be used for the new dashboard?** | **No.** `utils/utils/rls_boot_check.py:723-746` refuses one outright: *"materialized view … cannot be `security_invoker` — it holds rows computed once as its owner, so every tenant's rows are already stored in it… it cannot be made safe by an option."* Property 6 of `assert_rls_enforced` (`:442-465`) makes this a **boot refusal**, not a warning. |
| So what shape must a rollup take? | Either (a) an ordinary view with `security_invoker = true` — emitted by `table_builder.py:472-486` (`ALTER VIEW … SET (security_invoker = true)`), which every migration must re-emit because a `DROP VIEW` takes its reloptions with it (the F-30 defect, `copilot-mro/tests/unit/db/test_migration_view_security_invoker.py:1-27`); or (b) a **real tenant-columned table** written by a job, which then gets RLS like any other relation. (b) is the shape that actually reduces read cost. |

## 4.4 RLS on the read path — what the analytics API must bind

| Fact | Where |
|---|---|
| Role | `flynapse_app`, `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE INHERIT` — `NOBYPASSRLS` is the load-bearing attribute (`copilot-mro/scripts/provision_rls.py:161-166`) |
| Binding mechanism | One statement, `SELECT set_config('app.tenant_id', %s, true), set_config('app.operator_ids', %s, true)` — `is_local => true`, so it is **transaction-scoped**; the pool issues no `DISCARD ALL`, and a session-scoped variable would leak the previous caller's tenant to the next checkout (`utils/utils/postgres_service.py:22-34`) |
| Where it is set | `PostgresService._apply_transaction_context` → `apply_session_tenancy`, first statement inside each transaction; ten call sites take a raw `connection()` and must call it themselves or "those queries run unbound and read nothing, which is safe but useless" (`postgres_service.py:270-296`) |
| Where the identity comes from | `api/flynapse_api/middleware/auth.py:370-383` — `bind_db_tenancy(tenant_id, operator_ids)`, with `operator_ids` resolved **per user** from `user_operators`; a request that resolved a tenant but no user binds an **empty** operator list (fail-closed), not the tenant's whole list (`:375-380`) |
| Fail-closed default | An unbound context sets nothing; `current_setting(name, true)` reads NULL, every policy comparison is not-true, the query returns zero rows (`postgres_service.py:275-279`) |
| Policy shapes | `tenant`-class → exactly **one `FOR ALL`** policy; `tenant+operator` → exactly **four per-command** policies, set-equal to the emitter's declared shape, predicates included (`utils/utils/rls_boot_check.py:446-465`) |
| Statement timeout | `SET LOCAL statement_timeout` before the identity, default **15 000 ms** (`postgres_service.py:281-284`; `utils/utils/config.py:148-150`) |

**Two consequences the analytics API design must absorb:**

1. **The analytics API touches no database today.** `ChatQualityService` only calls Loki and the
   cache (`chat_quality_service.py:745-880`); `analytics_endpoints.py:43-46` never opens a
   connection. A Postgres rebuild is a new read path in `core` that must acquire a
   `PostgresService` and run under a bound `db_tenancy` — the binding comes free from the auth
   middleware for a normal request, but any background rollup job must bind it explicitly
   (`with db_tenancy(tenant_id, operator_ids)`, as `api/flynapse_api/automations/*.py` do).

2. **Operator entitlement silently narrows two of the candidate views.**
   `document_hub_documents` and `memory_items` are `tenant+operator`. A tenant admin bound to a
   subset of the tenant's operators reads only that subset — RLS returns fewer rows with no error.
   Every other analytics-relevant relation (`llm_usage`, `llm_model_calls`, the chat cluster,
   `automation_runs`, `comments`, `improvement_*`, `data_discovery_jobs`) is `tenant`-class and is
   therefore whole-tenant for any bound caller. **A "documents processed" tile and a
   "documents uploaded" tile can disagree between two admins of the same tenant, legitimately.**
   Either bind the analytics read to the tenant's full operator list (as
   `api/flynapse_api/automations/announcements.py:70` does with `_tenant_operator_ids(tenant_id)`)
   and say so, or label the tile as operator-scoped.

## 4.5 Row volumes

**No sizing note, row-count estimate or retention policy was found anywhere** in the three
registries or in `docs/plans/`. What the schema tells us about growth instead:

| Relation | Rows generated per… | Governing note |
|---|---|---|
| `chat_blocks` | 1 per turn, with a **TOAST-backed jsonb payload** carrying the whole `ChatBlock` — document batches, citations, `tool_call_log` **uncapped** (the 50-entry cap was removed with the DynamoDB item limit, `chat_management_helper.py:141-149`) | the widest row in the estate; any unindexed aggregate over it detoasts |
| `llm_usage` | 1 per turn | narrow, all-scalar — the right table to aggregate over |
| `llm_model_calls` | **n per turn** (one per governed model attempt, retries included) | the fastest-growing analytics relation |
| `chat_feedback` | 1 per thumbs event | sparse |
| `automation_runs` | 1 per attempted execution, retries re-open the row (`attempts + 1`) | bounded by schedule density |
| `memory_items` (`routing_scoreboard` rows) | bounded by `|query_type| × |department|` | genuinely small — this is why it works as a rollup |
| `document_hub_documents` | 1 per upload | bounded by client behaviour |
| `agent_state` | 1 per `(chat, namespace, key)` | **the only relation with a GC** — `agent_state_expiry_idx (expires_at) WHERE expires_at IS NOT NULL` "serves the GC sweep" (`agent_state.py:66-68`) |

Nothing else has a retention mechanism: no TTL column, no sweeper, no partitioning. `deleted` /
`deleted_at` are soft-delete flags and the payloads are explicitly **retained** (`chat.py:36`,
`:50`). For a ledger that is correct — `llm_usage` and `llm_model_calls` are append-only by
privilege (`provision_rls.py:233-237`) — but it means **the rebuild should decide retention
deliberately rather than inherit "forever" by omission.**

## 4.6 The truncation bug the current panels already have

`analytics_loki_query_limit` defaults to **5000** (`core/core/config.py:83-85`) and is passed
straight to Loki as `limit` (`chat_quality_service.py:841-847`). A tenant whose 1-month window
produces more than 5 000 matching log lines gets a **silently truncated** panel — no error, no
marker. Combined with the 300 s cache (`config.py:74-76`) and the 60-requests-per-60 s rate limit
(`:77-82`), and with every failure collapsing to one string in the UI (audit §5,
`dashboard/app/(dashboard)/settings/department/dashboard/page.tsx:381`), the current surface can
under-report without anyone noticing. A Postgres rebuild removes this class of defect entirely —
which is worth stating as a benefit of the migration, not just a side effect.

## 4.7 Open questions for the owner

| # | Question |
|---|---|
| 1 | `improvement_runs.llm_spend` reconciles against neither ledger — `llm_usage.origin` admits only `chat`/`automation` (`llm_usage.py:154-157`) and `llm_model_calls.origin` only `chat`/`automation`/`sdk_loop` (`llm_model_calls.py:149-151`). Is improvement-loop spend inside the tenant total or beside it? |
| 2 | Should the operator-scoped tiles (Document Hub, memory) be bound to the tenant's full operator list for admins, or stay entitlement-scoped and be labelled as such? |
| 3 | Retention: `llm_model_calls` grows per attempt with no GC. Rollup-then-prune, or keep forever? |
| 4 | Is `improvement_findings` client-visible at all (it is documented as internal-only, `improvement.py:117`)? |
| 5 | The document-open fact (Part 2 §2.1) — new `product_events` table, or restore frontend log delivery? Only the first survives the Loki retirement. |
