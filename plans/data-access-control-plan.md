# Data Access Control for Role-Based Management

## Status: IMPLEMENTED

All changes across core, copilot-mro, and dashboard repos are complete.

## Problem Statement

Different engineering roles (avionics engineers, structural engineers, etc.) need scoped access to:
1. **Manual access** - control which OEM manual types a role can query (AMM, FIM, SRM, IPC, MEL, CMM, WDM, TN)
2. **Data source access** - control which data sources a role can use (defect/AMOS data, inventory data, planning/forecasting data)

Previously, roles had feature-level permissions (can_chat, docs_view, etc.) but no data-level access control.

## Design

### Two new permission categories

New permission records in the existing `permissions` table (no new DynamoDB tables).

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

### Enforcement: three layers

**Layer 1 -- Planner-aware filtering (optimization):**
- `build_user_tool_registry()` builds a filtered tool registry excluding tools the user can't access
- The planner LLM never sees tools the user lacks permissions for, avoiding wasted planning + execution

**Layer 2 -- RetrievalStep filtering (manual types):**
- `_build_metadata_filters()` intersects requested manual types with `context.allowed_manual_types`
- `_retrieve_deterministic_reference_docs()` skips lookup blocks for disallowed manual types
- Prevents unauthorized content from being fetched from the vector DB

**Layer 3 -- Tool handler pre-checks (defense in depth):**
- `_check_manual_access()` and `_check_data_source_access()` at the top of tool handlers
- Returns consistent `_build_node_result()` payloads with `access_denied: true`
- Guards against prompt-injection bypass or planner bugs

---

## Implementation Details

### Phase 1: Core repo

#### 1.1 Seed new permission records -- DONE
**File:** `core/core/services/__init__.py`

- 13 new permission records in `_bootstrap_rbac_tables_and_seed()`
- 9 manual access (category `manual_access`) + 4 data source access (category `data_source_access`)

#### 1.2 Data access resolution endpoint -- DONE
**File:** `core/core/resources/permissions/permission_checker_endpoints.py`

- `GET /permissions/users/{user_id}/data-access?tenant_id=...&department_id=...`
- Resolves user permissions, filters to `manual_*` and `data_*`, handles wildcards

### Phase 2: Copilot-MRO

#### 2.1 PipelineContext fields -- DONE
**File:** `copilot-mro/copilot_mro/app/services/agents/steps/base.py`

- Added `allowed_manual_types: Optional[List[str]]` and `allowed_data_sources: Optional[List[str]]` (default `None`)

#### 2.2 Pipeline execute() params -- DONE
**File:** `copilot-mro/copilot_mro/app/services/agents/pipeline.py`

- `RAGPipeline.execute()` accepts both params and passes to `PipelineContext` constructor

#### 2.3 API-layer wiring -- DONE
**File:** `copilot-mro/copilot_mro/app/api/chat_management_helper.py`

- `resolve_data_access(api_request)` extracts permissions from `request.state.user_permissions`
- Tenant owners -> `None` (unrestricted)
- No `manual_*`/`data_*` permissions in list -> `None` (backward compat for legacy users)
- `manual_all`/`data_all` wildcards -> `None` (unrestricted)
- Otherwise strips prefix and returns allowed list (e.g. `manual_amm` -> `amm`)

**File:** `copilot-mro/copilot_mro/app/api/chat_management.py`

- Both `enhanced_chat` and `enhanced_chat_stream` call `resolve_data_access()` and pass results to `pipeline.execute()`

#### 2.4 Planner-aware tool filtering -- DONE
**File:** `copilot-mro/copilot_mro/app/services/agents/planner/tool_registry.py`

- `build_user_tool_registry(allowed_manual_types, allowed_data_sources)`:
  - Removes `amos_query` if `"defects"` not in `allowed_data_sources`
  - Removes `inventory_query` if `"inventory"` not in `allowed_data_sources`
  - Removes `planning_query` if `"planning"` not in `allowed_data_sources`
  - Keeps `manual_search` but injects allowed types into descriptor metadata
  - `None` values = unrestricted (full default registry)

**File:** `copilot-mro/copilot_mro/app/services/agents/main_agent/main_agent_runner_planner.py`

- Uses `build_user_tool_registry(context.allowed_manual_types, context.allowed_data_sources)` instead of default

#### 2.5 Manual access enforcement in RetrievalStep -- DONE
**File:** `copilot-mro/copilot_mro/app/services/agents/manuals/retrieval.py`

- `_build_metadata_filters()` intersects `documentTypes` with `context.allowed_manual_types`
- `_retrieve_deterministic_reference_docs()` skips blocks for disallowed manual types via `_is_manual_allowed()` helper
- `None` = all allowed (backward compatible)
- No changes to `manual_step.py` (AgentStep) -- retrieval step handles it

#### 2.6 Tool handler pre-checks -- DONE
**File:** `copilot-mro/copilot_mro/app/services/agents/main_agent/main_agent_planner_tool_handlers.py`

- `_DATA_SOURCE_TOOL_GATE = {"amos_query": "defects", "inventory_query": "inventory", "planning_query": "planning"}`
- `_check_manual_access(context)` -- returns access-denied if `allowed_manual_types` is empty list
- `_check_data_source_access(context, tool_name)` -- returns access-denied if mapped source not in allowed list
- Access-denied paths use `_build_node_result()` for consistent output format:
  - Manual: `{"manual_answer": "", "answer_found": "no", "access_denied": true, ...}`
  - Structured tools: `{answer_key: "", "answer_found": "no", "access_denied": true, ...}`
- Same envelope keys as normal responses: `tool_name`, `status`, `error`, `output`, `injection`, `block`, `references`

#### 2.7 Access-denied logging -- DONE
- `logger.warning()` with structured fields: `user_id`, `tenant_id`, `session_id`, `denied_tool`, `denied_data_source`/`denied_manual_types`
- Flows to existing log pipeline (CloudWatch / configured aggregator)

#### 2.8 Access-denied UX in chat
- When a tool returns `access_denied: true`, the output composer renders the user-facing `message` field
- Partial results from allowed tools are still composed normally

### Phase 3: Dashboard

#### 3.1 Permission types and groups -- DONE
**File:** `dashboard/types/permissions.ts`

- `PERMISSION_NAMES`: `MANUAL_AMM` through `MANUAL_ALL`, `DATA_DEFECTS` through `DATA_ALL`
- `PERMISSION_GROUPS`: `MANUAL_ACCESS` and `DATA_SOURCE_ACCESS` arrays

#### 3.2 Shared permission section components -- DONE
**File:** `dashboard/components/features/settings/roles/RolePermissionSections.tsx`

- Exports `MANUAL_PERMISSIONS`, `DATA_SOURCE_PERMISSIONS` constants
- `usePermissionGroups(availablePermissions)` hook splits into feature/manual/data-source groups
- `FeaturePermissionsCard` -- single-column checkbox grid with descriptions
- `DataAccessCard` -- compact inline checkboxes for manual types (3-col) and data sources, with `manual_all`/`data_all` select-all behavior

#### 3.3 EditRoleDialog -- DONE
**File:** `dashboard/components/features/settings/roles/EditRoleDialog.tsx`

- Uses `usePermissionGroups()` to split `availablePermissions`
- Three sections: Basic Information card, `FeaturePermissionsCard`, `DataAccessCard`

#### 3.4 Add custom role page -- DONE
**File:** `dashboard/app/(dashboard)/settings/department/roles/add/page.tsx`

- `DATA_ACCESS_PERMISSIONS` constant with all `manual_*` and `data_*` names
- `allowedPermissionNames` includes them so they appear in the permission list
- Uses same `RolePermissionSections` components as EditRoleDialog

#### 3.5 Roles page table columns -- DONE
**File:** `dashboard/app/(dashboard)/settings/department/roles/page.tsx`

- "Manuals" column: teal badges (`bg-teal-100 text-teal-800`), shows "All" for `manual_all`, "None" if empty
- "Data Sources" column: amber badges (`bg-amber-100 text-amber-800`), shows "All" for `data_all`, "None" if empty
- Both derive badges from `role.permissions` string by filtering for `manual_*`/`data_*` prefixes

#### 3.6 Department account page -- DONE
**File:** `dashboard/app/(dashboard)/settings/department/account/page.tsx`

- Separates feature, manual, and data-source permissions in the "Departments, Roles & Permissions" card

#### 3.7 useDepartmentRoles basic permissions -- DONE
**File:** `dashboard/hooks/settings/useDepartmentRoles.ts`

- All `manual_*` and `data_*` permission names added to `BASIC_DEPARTMENT_PERMISSIONS`
- Any department manager can assign data access permissions (not head-only)

#### 3.8 Settings API
- No new API calls needed -- frontend toggles new permission names through existing `assign_permission_to_role` / `revoke_permission_from_role` flow

---

## Migration / Rollout

1. **Core**: seed permissions first (backward compatible -- no existing roles have these permissions, no behavior changes)
2. **Copilot-MRO**: deploy with `allowed_manual_types: None` default (all allowed) -- no behavior change until permissions are assigned
3. **Dashboard**: deploy UI changes -- admins can start assigning data access permissions to roles
4. **Copilot-MRO**: once admins have configured roles, flip the default to require explicit permissions (or keep permissive default per tenant config)

## Design Decisions

- **Planner awareness**: Build a filtered tool registry per user so the planner doesn't plan nodes for inaccessible tools. Execution-layer gate as defense in depth.
- **Audit logging**: Access-denied events logged via existing `loguru` pipeline with structured fields. Flows to CloudWatch. No new infrastructure.
- **User visibility**: Data access badges shown on the Department Account page alongside existing permissions.
- **Permission assignability**: Basic permissions -- any manager can assign them, not head-only.
- **Access-denied output format**: Uses `_build_node_result()` for consistent shape with normal responses. Downstream consumers (output composer, section selector) handle the `access_denied` flag without special-casing.
- **Backward compatibility**: `None` means unrestricted everywhere. No `manual_*`/`data_*` permissions in the user's list = `None` (legacy fallback).

## File Change Summary

| Repo | File | Change |
|------|------|--------|
| core | `core/services/__init__.py` | 13 permission seeds |
| core | `core/resources/permissions/permission_checker_endpoints.py` | Data-access endpoint |
| copilot-mro | `app/services/agents/steps/base.py` | 2 fields on PipelineContext |
| copilot-mro | `app/services/agents/pipeline.py` | Pass access fields into context |
| copilot-mro | `app/api/chat_management_helper.py` | `resolve_data_access()` helper |
| copilot-mro | `app/api/chat_management.py` | Call resolve + pass to pipeline |
| copilot-mro | `app/services/agents/planner/tool_registry.py` | `build_user_tool_registry()` |
| copilot-mro | `app/services/agents/main_agent/main_agent_runner_planner.py` | Use user tool registry |
| copilot-mro | `app/services/agents/manuals/retrieval.py` | Intersect manual types, gate deterministic refs |
| copilot-mro | `app/services/agents/main_agent/main_agent_planner_tool_handlers.py` | Access pre-checks with consistent output format |
| dashboard | `types/permissions.ts` | Permission constants + groups |
| dashboard | `components/features/settings/roles/RolePermissionSections.tsx` | Shared permission section components |
| dashboard | `components/features/settings/roles/EditRoleDialog.tsx` | Grouped permission sections |
| dashboard | `app/(dashboard)/settings/department/roles/page.tsx` | Manuals + Data Sources columns |
| dashboard | `app/(dashboard)/settings/department/roles/add/page.tsx` | Include data access permissions |
| dashboard | `app/(dashboard)/settings/department/account/page.tsx` | Data access badges |
| dashboard | `hooks/settings/useDepartmentRoles.ts` | Add to basic permissions |
