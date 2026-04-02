# Data Access Control for Role-Based Management

## Problem Statement

Different engineering roles (avionics engineers, structural engineers, etc.) need scoped access to:
1. **Manual access** - control which OEM manual types a role can query (AMM, FIM, SRM, IPC, MEL, CMM, WDM, TN)
2. **Data source access** - control which data sources a role can use (defect/AMOS data, inventory data, planning/forecasting data)

Currently, roles have feature-level permissions (can_chat, docs_view, etc.) but no data-level access control. An avionics engineer and a structural engineer both get unrestricted access to all manuals and all data sources when using the copilot.

## Current Architecture Summary

### Core repo (permission backbone)
- **Roles**: `role_id`, `role_name`, `role_type`, `tenant_id`, `department_id` (DynamoDB)
- **Permissions**: `permission_id`, `permission_name`, `category`, `status` (DynamoDB)
- **Role-Permission mappings**: `role_id` + `permission_id` composite key (DynamoDB)
- **Permission checker**: resolves user -> user_roles -> role_permissions -> permission check
- Existing permissions are feature-level: `can_chat`, `docs_view`, `roles_manage`, etc.

### Copilot-MRO (agentic workflow)
- **PipelineContext**: carries `tenant_id`, `user_id`, `session_id` but no role/permission info
- **Tool registry**: `manual_search`, `amos_query`, `inventory_query`, `planning_query`, `history_answer`
- **Planner**: LLM selects tools to build execution plan; no access gating exists
- **Manual search**: extracts `manual_type` from query (AMM/FIM/SRM/IPC/MEL/CMM/WDM/TN), runs retrieval + generation
- **AMOS query**: queries work-order history for defects, recurrence, trends
- **Inventory query**: stock levels, locations, consumption, repair pipeline
- **Planning query**: stockout probability, reorder suggestions
- Manual retrieval filters by `manual_type` already exist in the extractor flow

### Dashboard (frontend)
- **EditRoleDialog**: checkbox grid of permissions, grouped by category
- **PERMISSION_NAMES**: flat constants (`can_chat`, `docs_view`, `roles_manage`, etc.)
- **PERMISSION_GROUPS**: logical groupings (DOCUMENT_ACCESS, CHAT_ACCESS, etc.)
- **RouteGuard**: blocks pages based on permission; no data-level scoping

---

## Design

### Two new permission categories

Introduce two new categories in the permissions system. These are NOT new DynamoDB tables -- they are new permission records in the existing `permissions` table with a new `category` value.

#### Category 1: Manual Access Permissions

| permission_name       | description                          |
|-----------------------|--------------------------------------|
| `manual_amm`          | Aircraft Maintenance Manual          |
| `manual_fim`          | Fault Isolation Manual               |
| `manual_srm`          | Structural Repair Manual             |
| `manual_ipc`          | Illustrated Parts Catalog            |
| `manual_mel`          | Minimum Equipment List               |
| `manual_cmm`          | Component Maintenance Manual         |
| `manual_wdm`          | Wiring Diagram Manual                |
| `manual_tn`           | Technical Notes                      |
| `manual_all`          | All manuals (superuser shortcut)     |

#### Category 2: Data Source Access Permissions

| permission_name         | description                           |
|-------------------------|---------------------------------------|
| `data_defects`          | AMOS defect/work-order history        |
| `data_inventory`        | Inventory stock and locations          |
| `data_planning`         | Inventory planning and forecasting     |
| `data_all`              | All data sources (superuser shortcut)  |

### Enforcement approach: two layers (planner-aware + execution gate)

**Layer 1 -- Planner-aware filtering (optimization):**
- The planner prompt already receives the tool registry as a JSON payload via `ToolRegistry.to_prompt_payload()`
- At pipeline init, build a **filtered tool registry** that only includes tools the user has access to
- If the user has no `data_defects` permission, omit `amos_query` from the registry entirely
- If the user has no `data_inventory` permission, omit `inventory_query`
- If the user has no `data_planning` permission, omit `planning_query`
- For `manual_search`, always include it but inject `allowed_manual_types` into the tool descriptor's metadata so the planner can reference it
- This avoids wasted LLM planning + tool execution for tools the user can't use

**Layer 2 -- Execution gate (safety net):**
- Even with planner filtering, enforce access checks at the tool handler layer as defense in depth
- If a user lacks a manual permission, the `manual_search` tool handler filters out disallowed manual types before retrieval and returns a "no access" message for blocked types
- If a user lacks a data source permission, the `amos_query` / `inventory_query` / `planning_query` tool handler short-circuits with an access-denied response
- This guards against prompt-injection bypass or bugs in the planner filtering

---

## Changes by Repo

### Phase 1: Core repo (backend permission definitions + API)

#### 1.1 Seed new permission records
**File:** `core/core/services/__init__.py`

- Add 13 new permission records to the `permissions` list in `_bootstrap_rbac_tables_and_seed()`
- Manual access (category `manual_access`): `manual_amm`, `manual_fim`, `manual_srm`, `manual_ipc`, `manual_mel`, `manual_cmm`, `manual_wdm`, `manual_tn`, `manual_all`
- Data source access (category `data_source_access`): `data_defects`, `data_inventory`, `data_planning`, `data_all`
- Same seeding pattern as existing permissions — create if not exists

#### 1.2 Add data access resolution endpoint
**File:** `core/core/resources/permissions/permission_checker_endpoints.py`

- New endpoint: `GET /permissions/users/{user_id}/data-access`
  - Query params: `tenant_id` (required), `department_id` (optional)
  - Uses existing `PermissionChecker.get_user_permissions()` to get all permissions
  - Filters to `manual_*` and `data_*` permissions
  - Handles `manual_all` / `data_all` as wildcards
  - Returns: `{ "manual_types": ["AMM", "FIM", ...], "data_sources": ["defects", "inventory", ...] }`

#### 1.3 Permission service
**File:** `core/core/resources/permissions/services/permission_service.py`

- `PermissionService.get_permissions_by_category(category: str)` already exists — no changes needed

### Phase 2: Copilot-MRO (enforcement in agent pipeline)

#### 2.1 Extend PipelineContext
**File:** `copilot-mro/copilot_mro/app/services/agents/steps/base.py`

- Add two optional fields to `PipelineContext`: `allowed_manual_types` and `allowed_data_sources` (both `Optional[List[str]]`, default `None`)
- Also add them to `to_dict()`

#### 2.2 Populate at pipeline init
**File:** `copilot-mro/copilot_mro/app/services/agents/pipeline.py`

- Add `allowed_manual_types` and `allowed_data_sources` params to `RAGPipeline.execute()`
- Pass them into the `PipelineContext` constructor
- **DONE** -- already implemented

#### 2.2b API-layer wiring (chat_management.py)
**File:** `copilot-mro/copilot_mro/app/api/chat_management.py`

- Add `_resolve_data_access(api_request)` helper that:
  - Reads `request.state.user_permissions` (set by permission middleware) and `request.state.is_tenant_owner`
  - Tenant owners get `None` (unrestricted) for both
  - If no `manual_*` or `data_*` permissions exist in the list, returns `None` for both (backward compat / legacy users)
  - Otherwise, filters permissions by prefix and strips the prefix (e.g. `manual_amm` -> `amm`)
  - Handles `manual_all` / `data_all` wildcards -> returns `None` (unrestricted)
- Call `_resolve_data_access()` in both `enhanced_chat` and `enhanced_chat_stream` before `pipeline.execute()`
- Pass `allowed_manual_types` and `allowed_data_sources` to `pipeline.execute()`
- **DONE** -- already implemented

#### 2.3 Planner-aware tool filtering
**File:** `copilot-mro/copilot_mro/app/services/agents/planner/tool_registry.py`

- New function: `build_user_tool_registry(allowed_manual_types, allowed_data_sources)` that:
  - Starts from `DEFAULT_TOOL_DESCRIPTORS`
  - Removes `amos_query` if `"defects"` not in `allowed_data_sources`
  - Removes `inventory_query` if `"inventory"` not in `allowed_data_sources`
  - Removes `planning_query` if `"planning"` not in `allowed_data_sources`
  - Keeps `manual_search` but appends allowed manual types to its description metadata
  - If both are `None` (legacy), returns the full default registry

**File:** `copilot-mro/copilot_mro/app/services/agents/main_agent/main_agent_runner_planner.py`

- Replace `build_default_tool_registry()` call with `build_user_tool_registry(context.allowed_manual_types, context.allowed_data_sources)`

#### 2.4 Manual access enforcement in RetrievalStep
**File:** `copilot-mro/copilot_mro/app/services/agents/manuals/retrieval.py`

**`_build_metadata_filters()`:** After normalizing `documentTypes`, intersect with `context.allowed_manual_types` (normalized). If no types remain, return a sentinel (`__ACCESS_DENIED__`) that short-circuits retrieval. If `allowed_manual_types` is `None`, allow all (backward compatible). If no explicit `documentTypes` filter but `allowed_manual_types` is set, inject as filter.

**`_retrieve_deterministic_reference_docs()`:** Before each manual-type-specific lookup block (AMM, SRM, IPC, IFIM, MEL), check if that type is in `context.allowed_manual_types` via `_is_manual_allowed()` helper. Skip if not allowed. `None` = all allowed.

Pass `context` into `_build_metadata_filters()` (currently only receives `current_filters`).

**No changes needed to `manual_step.py` (AgentStep)** -- it orchestrates retrieval -> generation -> validation and doesn't need access awareness since the retrieval step handles it.

#### 2.5 Tool handler pre-checks (defense in depth)
**File:** `copilot-mro/copilot_mro/app/services/agents/main_agent/main_agent_planner_tool_handlers.py`

- Module-level gate map: `_DATA_SOURCE_TOOL_GATE = {"amos_query": "defects", "inventory_query": "inventory", "planning_query": "planning"}`
- `_check_manual_access(context)`: if `allowed_manual_types` is an empty list, return access-denied payload
- `_check_data_source_access(context, tool_name)`: if `allowed_data_sources` is not `None` and the mapped source not in it, return access-denied payload
- Guard at top of `_planner_tool_manual_search()` calling `_check_manual_access()`
- Guard at top of `_planner_tool_structured_query()` calling `_check_data_source_access()` (gates amos_query, inventory_query, planning_query)
- Access-denied payload: `{ "answer_found": "no", "access_denied": True, "message": "..." }`

#### 2.6 Access-denied logging
- In the same pre-check methods, log via `logger.warning()` with structured fields: `user_id`, `tenant_id`, `session_id`, `denied_tool`, `denied_manual_types` or `denied_data_source`
- These flow into the existing log pipeline (CloudWatch / configured aggregator) -- no new infrastructure needed

#### 2.7 Access-denied UX in chat
- When a tool returns `access_denied: true`, the output composer should render a user-friendly message explaining what access is missing and who to contact
- The response should still be usable (partial results from allowed tools should still be composed)

### Phase 3: Dashboard (frontend UI for managing data access)

#### 3.1 Update permission types
**File:** `dashboard/types/permissions.ts`

- Add to `PERMISSION_NAMES`: `MANUAL_AMM` through `MANUAL_ALL`, `DATA_DEFECTS` through `DATA_ALL`
- Add to `PERMISSION_GROUPS`: `MANUAL_ACCESS` and `DATA_SOURCE_ACCESS` arrays

#### 3.2 Update permission display names
**File:** `dashboard/utils/permission-mappings.ts`

- Add display name mappings (e.g., `manual_amm` -> "Aircraft Maintenance Manual (AMM)", `data_defects` -> "Defect History", `manual_all` -> "All Manuals", `data_all` -> "All Data Sources")
- Add category mappings in `getPermissionCategory()`: `manual_*` -> "Manual Access", `data_*` -> "Data Source Access"

**File:** `dashboard/components/ui/permission-badge.tsx`

- Add badge colors: "Manual Access" -> teal (`bg-teal-100 text-teal-800`), "Data Source Access" -> amber (`bg-amber-100 text-amber-800`)

#### 3.3 Update EditRoleDialog
**File:** `dashboard/components/features/settings/roles/EditRoleDialog.tsx`

- Split `availablePermissions` into `featurePermissions`, `manualPermissions`, `dataSourcePermissions`
- Group into three Card sections: "Feature Permissions", "Manual Access", "Data Source Access"
- `PermissionCheckboxGrid` component with `allPermissionName` prop for select-all behavior
- When `manual_all` is checked, individual manual checkboxes appear checked and disabled. Same for `data_all`.

#### 3.4 Update roles page table
**File:** `dashboard/app/(dashboard)/settings/department/roles/page.tsx`

- Add two new columns after "Permissions": "Manuals" (teal badges) and "Data Sources" (amber badges)
- Both `mobilePriority: false`. Show "None" in muted text when empty.

**File:** `dashboard/utils/permission-utils.tsx`

- Add `MANUAL_BADGE_LABELS` and `DATA_SOURCE_BADGE_LABELS` maps
- Update `loadRolePermissions` to separate permissions into `featureNames`, `manualLabels`, `dataSourceLabels` and return as separate fields (`permissions`, `manual_access`, `data_source_access`)

#### 3.5 Show data access on Department Account page
**File:** `dashboard/app/(dashboard)/settings/department/account/page.tsx`

- Separate feature, manual, and data-source permissions in the existing "Departments, Roles & Permissions" card
- Show teal badges for manuals ("All Manuals" if `manual_all`), amber badges for data sources ("All Data Sources" if `data_all`)

#### 3.6 Update useDepartmentRoles basic permissions
**File:** `dashboard/hooks/settings/useDepartmentRoles.ts`

- Add all `manual_*` and `data_*` permission names to `BASIC_DEPARTMENT_PERMISSIONS` so any department manager can assign them

#### 3.7 Settings API
- The existing role update flow already handles permission assignment via the core API
- No new API calls needed -- the frontend just toggles the new permission names through the same `assign_permission_to_role` / `revoke_permission_from_role` flow

---

## Migration / Rollout

1. **Core**: seed permissions first (backward compatible -- no existing roles have these permissions, so no behavior changes)
2. **Copilot-MRO**: deploy with `allowed_manual_types: None` default (all allowed) -- no behavior change until permissions are assigned
3. **Dashboard**: deploy UI changes -- admins can start assigning data access permissions to roles
4. **Copilot-MRO**: once admins have configured roles, flip the default to require explicit permissions (or keep permissive default per tenant config)

## Role Hierarchy Consideration

The dashboard enforces a permission assignment hierarchy:
- **Department managers** can only assign `BASIC_DEPARTMENT_PERMISSIONS` (docs_view, can_chat, can_comment)
- **Department heads** can assign additional permissions (users_view, users_modify, roles_*, etc.)

The new data access permissions (manual_* and data_*) should be classified as **basic permissions** -- any manager can assign them. This keeps data access configuration lightweight and doesn't require escalation to a department head for routine role setup.

Update `useDepartmentRoles.ts` to include the new permission names in the basic permissions set (alongside `docs_view`, `can_chat`, `can_comment`).

## Resolved Questions

- **Planner awareness**: Yes -- build a filtered tool registry per user so the planner doesn't plan nodes for tools the user can't access. Keep execution-layer gate as defense in depth.
- **Audit logging**: Access-denied events logged via existing `loguru` pipeline with structured fields (`user_id`, `tenant_id`, `denied_tool`, etc.). Flows to CloudWatch / configured aggregator. No new infrastructure.
- **User visibility**: Show data access badges on the existing Department Account page (`settings/department/account`) alongside the existing permissions display.
- **Data access permissions assignability**: Basic permissions -- any manager can assign them, not head-only.

## Verification

1. **Core:** Run the seeder — verify new permissions appear in DynamoDB. Hit `GET /permissions/users/{user_id}/data-access` and confirm correct `manual_types` / `data_sources` response.
2. **Copilot-MRO:** Unit test `build_user_tool_registry` — verify tools are excluded/included correctly. Test that `RetrievalStep._build_metadata_filters` intersects with allowed types. Test access-denied payloads in tool handlers.
3. **Dashboard:** Verify EditRoleDialog renders three sections. Verify roles table shows new columns. Verify account page shows data access badges. Verify `manual_all`/`data_all` toggle behavior.

## File Change Summary

| Repo | File | Change |
|------|------|--------|
| core | `core/services/__init__.py` | Add 13 permission seeds |
| core | `core/resources/permissions/permission_checker_endpoints.py` | Add data-access endpoint |
| copilot-mro | `app/services/agents/steps/base.py` | Add 2 fields to PipelineContext |
| copilot-mro | `app/services/agents/pipeline.py` | Pass access fields into context |
| copilot-mro | `app/services/agents/planner/tool_registry.py` | Add `build_user_tool_registry()` |
| copilot-mro | `app/services/agents/planner/__init__.py` | Export new function |
| copilot-mro | `app/services/agents/main_agent/main_agent_runner_planner.py` | Use user tool registry |
| copilot-mro | `app/services/agents/manuals/retrieval.py` | Intersect manual types, gate deterministic refs |
| copilot-mro | `app/services/agents/main_agent/main_agent_planner_tool_handlers.py` | Add access pre-checks + logging |
| dashboard | `types/permissions.ts` | Add permission constants + groups |
| dashboard | `utils/permission-mappings.ts` | Add display names & categories |
| dashboard | `components/ui/permission-badge.tsx` | Add badge colors for new categories |
| dashboard | `components/features/settings/roles/EditRoleDialog.tsx` | Grouped permission sections |
| dashboard | `app/(dashboard)/settings/department/roles/page.tsx` | New table columns |
| dashboard | `utils/permission-utils.tsx` | Separate manual/data-source badge labels |
| dashboard | `app/(dashboard)/settings/department/account/page.tsx` | Data access badges per department |
| dashboard | `hooks/settings/useDepartmentRoles.ts` | Add to basic permissions |

## Open Questions

- Should the `manual_all` / `data_all` wildcard permissions be reserved for admin roles only, or should any role be assignable?
