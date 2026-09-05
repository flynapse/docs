# Frontend surface inventory and draft event catalogue — `dashboard/` (2026-09-05)

Research deliverable for the observability rebuild, Phase 4 (design §7.4). Read-only pass over
`/home/aditya/Code/dashboard` (`node_modules/` and `.next/` excluded). Every claim carries a
`path:line`. "not found" means a search was run and returned nothing.

Written to answer the owner's instruction verbatim: *"dashboard has evolved and added multiple pages
and features since we last added FE events. so we need to scope out properly for gaps and add
appropriately."* — so the catalogue in Part 3 is scoped from **this** inventory, not from the old
24-event / 32-custom-metric list (which research file 02 §1.1–1.2 enumerates).

Companion documents:
- `docs/plans/observability-rebuild-research/02-frontend-and-deployment-inventory.md` — the OLD event
  inventory (§1.1), the `custom_metric` family (§1.2), delivery being off (§1.4), and the analytics
  read contract (Part 2).
- `docs/superpowers/specs/2026-09-05-observability-rebuild-design.md` — §7.2 `product_events`,
  §7.3 the v1 product views, §7.4 the curated-catalogue ruling, §9.2 the ops panels.

**Scale of the app today.** `app/` holds **46 `page.tsx`**, **4 `layout.tsx`**, **13 `route.ts`**,
1 `template.tsx`, 4 `loading.tsx`, 10 `error.tsx` (`find app -name …`). The old telemetry layer was
written against a much smaller app: outside `lib/logging/` itself it is reached from only **15 files**
— 7 that import `feature-metrics` (`LoginView`, `pdf-viewer-main`, `LoggingProvider`,
`useDepartmentMessageStream`, `fetch-utils`, `settings-api`, `lib/api/utils`) and 9 that call
`reportCustomMetric` directly (`ChatSidebar`, `RouteGuard`, `AuthGuard`, `pdf-toc`, `pdf-comments`,
`pdf-document-header`, `CopilotsPageContent`, `useDepartmentChatHistory`, `useDepartmentMessageStream`).

---

## PART 1 — SURFACE INVENTORY OF THE CURRENT APP

### 1.0 How to read the "old telemetry" column

The whole legacy layer is mounted globally — `components/providers/AppProviders.tsx:24` wraps the
tree in `<LoggingProvider>`, which calls `initializeLogging()` and `initializeFrontendTracing()`
(`components/providers/LoggingProvider.tsx:13-18`). So three things are true on **every** route and
are therefore NOT repeated per row below:

| Global signal | Emitter | Note |
|---|---|---|
| `page_view` / `page_exit` / `page_bounce` | `lib/logging/page-tracking.ts:62,80,153` via `components/logging/PageTracker.tsx` | `pageName` is always `undefined` — `<PageTracker>` is mounted once with no props (`LoggingProvider.tsx:22`) |
| `user_interaction` (every click / submit / SPA nav), `scroll_milestone`, `window_state_change`, `window_resize` | `page-tracking.ts:365-430`, `:124`, `:137`, `:321` | untargeted; `window_resize` unthrottled |
| Web Vitals ×5, `long_task`, `memory_usage`, `navigation_timing`, `custom_metric` | `lib/logging/vitals.ts:34-200` | `custom_metric` is the single carrier for all 32 named metrics |
| `api_request_ms` + a feature metric per call | `lib/logging/feature-metrics.ts:177,182` via `fetchWithAuth`/`fetchStreamWithAuth` (`lib/api/fetch-utils.ts:135,189`) and `apiRequest` (`lib/api/utils.ts:297`) | fires for any API client built on those three; **not** for `authenticatedApiRequest` (`utils.ts:400`), `rawApiRequest` (`:546`) or the PDF request helper (`:514`), none of which start a timer |
| Browser OTel fetch/XHR spans | `lib/observability/otel.ts:59-78` | exported to `http://localhost:4318/v1/traces` from the user's own machine → always fails (02 §1.5) |

**And none of it is delivered.** Both `fetch` calls in `lib/logging/logger.ts:233-242` and `:257-266`
are commented out. Everything below is therefore *potential*, not *observed*, telemetry.

The per-route column names only **route-specific** instrumentation, i.e. a hook a developer added for
that surface.

### 1.1 Public / auth (`app/(auth)/*`, 5 pages)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(auth)/layout.tsx` | Centred card shell for all auth pages | — | — | none |
| `app/(auth)/login/page.tsx` | Cognito sign-in (+ SSO entry) | `components/features/auth/LoginView.tsx` | submit credentials, SSO redirect, forgot-password link | **`startLoginTimer()`** at `LoginView.tsx:162` → `login_submit_to_auth_ms`, `login_to_ready_ms` (`feature-metrics.ts:209,213`); `login_request_ms` from the API timer's feature inference (`feature-metrics.ts:91-92`) |
| `app/(auth)/login/loading.tsx` | Suspense fallback | — | — | none |
| `app/(auth)/register/page.tsx` | Self-serve signup (Turnstile-gated) | `components/features/auth` → `RegisterView` | submit registration, solve captcha | none |
| `app/(auth)/forgot-password/page.tsx` | Request reset code | `ForgotPasswordView` | submit email | none |
| `app/(auth)/new-password/page.tsx` | Set new password / forced change | `NewPasswordView` | submit new password | none |
| `app/(auth)/invite/page.tsx` | Accept a tenant invitation | `InviteAcceptView`, `hooks/auth/useInvitationPreview.ts` | preview invite, accept, decline | none |

All of these are `isPublicPage` (`lib/auth/public-paths.ts:26-40`) so their events route to the
anonymous ingest endpoint.

### 1.2 Shell, landing and misc

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/layout.tsx` | Root shell; injects `window.__RUNTIME_CONFIG__` (`:60`); mounts `AppProviders` | `components/providers/AppProviders.tsx` | — | mounts the entire legacy layer (§1.0) |
| `app/page.tsx` | `redirect('/copilots')` (server) | — | — | none |
| `app/(dashboard)/layout.tsx` | `AuthGuard` + title manager for every authenticated route | `components/features/auth/AuthGuard.tsx` | — | **`auth_guard_check_ms`** (`AuthGuard.tsx:67,78`) |
| `app/(dashboard)/template.tsx` | Page-enter animation wrapper | — | — | none |
| `app/(dashboard)/copilots/page.tsx` | Product landing: the copilot tile grid (MRO / Pilot / Crew / Optimizer / Rostering / Data Discovery, per entitlement) | `components/features/copilots/CopilotsPageContent.tsx`, `copilot-config.ts`, `hooks/copilots/useCopilotAccess.ts` | choose a copilot (navigation), see locked tiles | **`copilots_page_render_ms`** (`CopilotsPageContent.tsx:52`) |
| `app/(dashboard)/help/page.tsx` | Static help / release notes, 7 sections | `components/features/help/HelpPageShell` + `help-sections` | expand a section, in-page nav | none |
| `app/chart-card-visual-test/page.tsx` | Dev-only visual harness for `ChartCard` | `components/features/chat/ChartCard.tsx` | — | none — **should be excluded from telemetry and probably from the production build** |
| `app/health/route.ts` | Amplify/ALB liveness JSON | — | — | none |
| 10 × `error.tsx` (copilots, crew, mro, mro/document/[id], pilot, data-discovery, help, optimizer, rostering, settings) | Next error boundaries | — | "try again" | none — **these are separate from `lib/logging/ErrorBoundary.tsx`, which is only mounted by `LoggingProvider`**; a segment error renders `error.tsx` and the React boundary never sees it |

`RouteGuard` (`components/features/auth/RouteGuard.tsx:133,171`) emits **`route_guard_check_ms`** and
is mounted by ~20 of the authenticated pages individually.

### 1.3 Chat — MRO / Pilot / Crew (3 pages, the product's core)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/mro/page.tsx` (440 lines) | MRO copilot chat workspace | `components/features/chat/CopilotChatLayout.tsx` (→ `ChatHeader`, `ChatMessages`, `ChatInput`, `ChatSidebar`, `MessageBubble`, `MessageActions`, `DocumentCard`, `MessageProgressTrace`, `FiltersPanel`, `WorkOrderCarousel`, `ChartCard`, `DataViewModal`, `ReportPreviewModal`, `FeedbackDialog`, `ShareDialog`, `FileAttachmentCard`), `DocumentHubChatControls.tsx`, `TenantAllChatsPanel.tsx` | send message (SSE), stop generation, new chat, open past chat, open citation, thumbs up/down + comment, share chat, attach file, set filters, choose Document-Hub scope, view work-order carousel, open data view, preview report, answer a clarification | **`chat_request_ms`** via `startChatTimer` (`hooks/chat/useDepartmentMessageStream.ts:236`, stopped `:347`); **`chat_messages_render_ms`** (`:402`, `hooks/chat/useDepartmentChatHistory.ts:248,278`); **`chat_history_render_ms`** (`components/features/chat/ChatSidebar.tsx:115`) |
| `app/(dashboard)/pilot/page.tsx` (280 lines) | Pilot copilot chat | same `CopilotChatLayout`; `hooks/chat/usePilotMessageStream.ts`, `usePilotChatHistory.ts` | as above minus work orders / Document-Hub scope | same three metrics (shared hooks) |
| `app/(dashboard)/crew/page.tsx` (280 lines) | Crew copilot chat | same; `hooks/chat/useCrewMessageStream.ts`, `useCrewChatHistory.ts` | as above | same |

Shared chat hooks (all three departments): `hooks/chat/useChatState.ts`, `useSidebar.ts`,
`useChatCapabilities.ts`, `useChatAttachments.ts`, `useChatFeedbackHandlers.ts`, `useFeedback.ts`,
`useShare.ts`, `useDataView.ts`, `useDocumentNames.ts`, `useStickToBottom.ts`, `abortUtils.ts`,
`streamingHelpers.ts`. `components/features/chat/CopilotDock.tsx` + `hooks/chat/useCopilotDockChat.ts`
put the same chat inside the Optimizer page (§1.8).

**Defect found while reading:** on the failure path the code creates a *new* `startChatTimer()` and
stops it immediately (`useDepartmentMessageStream.ts:459-462`), so every failed turn reports
`chat_request_ms ≈ 0 ms`. Failed turns are therefore invisible in the latency distribution *and*
drag the mean down. Any rebuilt chat timing must stop the original timer, not mint a new one.

### 1.4 Document viewer (per department, 3 routes)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/mro/document/[id]/page.tsx` (208) | PDF viewer for a catalog manual, opened from chat or search | `components/features/pdf-viewer/*` (`pdf-viewer-main.tsx`, `pdf-document-header.tsx`, `pdf-toc.tsx`, `pdf-comments.tsx`), `hooks/pdf-viewer/*`, `RouteGuard` | scroll/paginate, jump to cited page, search in document, open TOC, add/edit/delete a comment, thumbs-up a comment, print, download (signed URL), sign out | **`pdf_open_first_render_ms`** (`pdf-viewer-main.tsx:96` → `feature-metrics.ts:240`); **`pdf_page_switch_ms`** (`pdf-viewer-main.tsx:168`); **`pdf_metadata_render_ms`** (`pdf-document-header.tsx:146`); **`pdf_toc_render_ms`** (`pdf-toc.tsx:80`); **`comments_render_ms`** (`pdf-comments.tsx:65`); `pdf_api_ms` from URL inference (`feature-metrics.ts:85-87`) |
| `app/(dashboard)/pilot/document/[id]/page.tsx` (133) | same viewer, Pilot department | same | same | same (shared components) |
| `app/(dashboard)/crew/document/[id]/page.tsx` (132) | same viewer, Crew department | same | same | same |
| `app/(dashboard)/mro/document/[id]/{loading,error}.tsx` | Suspense + error states | — | — | none |

**No document id is attached to any of these metrics** — `startPdfOpenTimer()` takes no arguments
(`feature-metrics.ts:235`). The id lives in `use(params)` at the page (`mro/document/[id]/page.tsx:27`)
and in `DocumentCard.handleOpenDocument` (`components/features/chat/DocumentCard.tsx:96-127`), which
is the richest point in the app: it distinguishes a **catalog** open (`buildDocumentViewerUrl`, `:114`)
from a **Document-Hub library** open (`libraryRef` → `onDocumentHubReferenceClick`, `:100-107`) from
an **upload/attachment** open (`attachmentId` → `onUploadReferenceClick`, `:109-112`). That three-way
split is exactly the `document_kind` enum design §7.2 asks for.

### 1.5 Document Hub (1 page + preview dialog + 1 Next proxy route)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/mro/document-hub/page.tsx` (24) | Tenant document library: browse, upload, curate, retry processing | `components/features/document-hub/DocumentHubPageContent.tsx`, `DocumentHubGroupBrowser.tsx`, `DocumentHubGroupingControl.tsx`, `DocumentHubPreviewDialog.tsx`, `RouteGuard` | **upload a file** (`handleUpload`, `DocumentHubPageContent.tsx:643-679`), change grouping, browse a group, open a document preview, edit metadata / sharing scope, retry processing (`lib/api/client.ts:965-975`), delete | none beyond `api_request_ms` (upload goes through `fetchWithAuth`, `client.ts:1009-1016`) |
| `app/api/document-hub/documents/[id]/content-stream/route.ts` | SSR proxy for in-browser preview bytes | — | — | none |

The upload is a single multipart POST to `/document-hub/documents/upload`
(`lib/config.ts:119`, `lib/api/client.ts:979-1017`) — no presign, no chunking — and the UI treats it
as fire-and-queue ("Upload queued", `DocumentHubPageContent.tsx:668-671`). Processing outcome is only
visible by refetching the row. So **upload started / completed / failed are three distinct
client-observable moments**, and the *processing* outcome is a backend fact (§7.3 Operations tab),
not a browser one.

### 1.6 Automations (3 routes, one per department)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/mro/automations/page.tsx` (11) | Scheduled/manual automations for MRO | `components/features/automations/AutomationsManager.tsx` (`AutomationsSurface`) → `AutomationsTable.tsx`, `ScheduleDialog.tsx`, `RecurrencePicker.tsx`, `RunHistoryPanel.tsx`, `RunStatusBadge.tsx` | create automation, edit, delete, **run now**, open run history, open a run's answer, toggle enabled | none beyond `api_request_ms` |
| `app/(dashboard)/pilot/automations/page.tsx` (7) | same, Pilot | same | same | same |
| `app/(dashboard)/crew/automations/page.tsx` (7) | same, Crew | same | same | same |

Mutations run through `hooks/api/useAutomations.ts` (`useCreateAutomation:145`, `useUpdateAutomation:158`,
`useDeleteAutomation:177`, `useRunAutomationNow:195`) over `lib/api/automations-api.ts:224-297`.
`AutomationChatBanner.tsx` and `AutomationsHeaderLink.tsx` surface automations inside the chat pages.

### 1.7 Airworthiness / AD review (1 page)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/mro/airworthiness/page.tsx` (526) | AD applicability review queue: triage each AD against the fleet | `components/features/mro/ad-review/AdReviewTable.tsx`, `DispositionDialog.tsx`, `PreflightBanner.tsx`, `adReviewPresentation.ts`, `hooks/mro/useAdReview.ts`, `RouteGuard` | filter/search the queue, switch tab, **set a disposition** (triage), clear a disposition, recompute applicability, materialize the AD corpus, poll materialize status | none beyond `api_request_ms` |

API: `lib/api/ad-review-api.ts:274` list, `:298` set disposition, `:328` clear, `:346` recompute,
`:367` materialize, `:380` status poll.

### 1.8 Data Discovery (3 pages + guard layout)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/data-discovery/layout.tsx` | Entitlement gate | `components/features/data-discovery/DataDiscoveryGuard.tsx` | — | none |
| `app/(dashboard)/data-discovery/page.tsx` (594) | Register data sources, launch discovery jobs, list jobs | `DiscoveryPrimitives.tsx`, `ConfirmDialog`, `hooks/data-discovery/useDataDiscoveryCapabilities.ts` | **register a Postgres source** (`submitDatabaseSource:175`), archive a source, **start a discovery job**, open a job, page the lists | none beyond `api_request_ms` |
| `app/(dashboard)/data-discovery/jobs/[jobId]/page.tsx` (981) | One job: progress, schemas, takeaways, Level-2 runs | `DiscoveryTakeaways.tsx`, `DiscoveryPrimitives.tsx`, tabs | watch job progress (**polling**), **start a Level-2 run**, filter tables, open a table, cancel/confirm dialogs | none |
| `app/(dashboard)/data-discovery/jobs/[jobId]/tables/[tableId]/page.tsx` (378) | One table's facts | `DatabaseFactsTabs.tsx` | switch fact tab, expand accordions | none |

API surface: `lib/api/data-discovery.ts:89-140` (`capabilities`, `createPostgresSource`, `sources`,
`jobs`, `job`, `level2Runs`, `createLevel2Run`, `tables`, `archiveSource`).

### 1.9 Optimizer and Rostering (2 pages, large feature trees)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `app/(dashboard)/optimizer/page.tsx` (564) | Shift-optimizer workspace: schedules, activities, roles, config, jobs, runs, network view, outputs; first-plan wizard; embedded copilot dock | `components/features/optimizer/{ActivitySetupPanel,GlobalConfigPanel,GlobalConstraintsPanel,OutputsPanel,ResourceConfigPanel,RoleSetupPanel,RunsPanel,ScheduleSetupPanel}.tsx`, `network/*`, `outputs/*`, `wizard/*`, `askCopilot.ts`, `components/features/chat/CopilotDock.tsx`, `RouteGuard` | upload schedule CSV, process schedule, edit expansion, create/edit activity + preview rule, create/edit role, save settings, preflight a job, **run a job (solve)**, poll run status, open run outputs, **export a run** (blob download), ask the copilot dock, walk the wizard | none beyond `api_request_ms` |
| `app/(dashboard)/rostering/page.tsx` (174) | Rostering workspace: sidebar sections over roster, headcount, preassignment, operations, analytics, audit, export | `components/features/rostering/{roster,headcount,preassignment,operations,analytics,audit,export,configuration,shared}/*`, `hooks/*` | switch section, edit contracts/headcount, run scenarios, **export a roster**, read the audit log | none |

Optimizer API is `lib/api/optimizer-api.ts` — **38 `fetchWithAuth` call sites**, incl. `runJob:703`,
`preflightJob:666`, `getRun:719`, `getRunOutput:725`, `fetchRunExport:797` (blob),
`uploadScheduleCsv:452`. All are covered by `api_request_ms` and by nothing else.

### 1.10 Settings — tenant scope (`settings/tenant/*`, 11 pages)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `settings/page.tsx` (113) | Redirect hub by permission | — | — | none |
| `settings/tenant/page.tsx` (72) | Redirect hub for tenant admins | — | — | none; **17 emoji `logger.info` debug lines (`:28-49`)** |
| `settings/tenant/general/page.tsx` (182) | Tenant overview + per-department user stats | `components/features/settings` | view stats | none |
| `settings/tenant/organization/page.tsx` (448) | Organization profile edit | `settings/organization/organizationSave.ts` | **save organization** | none |
| `settings/tenant/departments/page.tsx` (911) | Department list / edit / delete | `DataTable`, dialogs | edit, delete a department | **`settings_department_update_ms`** via `lib/api/settings-api.ts:1601`; delete has **no timer** |
| `settings/tenant/add-department/page.tsx` (511) | Create a department + assign users | form components | **create department** | **`settings_department_create_ms`** (`settings-api.ts:1538`) |
| `settings/tenant/roles/page.tsx` (893) | Tenant role list / edit / delete / capabilities | `RoleAccessBadges`, `PersonaCapabilityEditor`, dialogs | edit role, edit capabilities, delete role | **`settings_role_create_ms`/`_update_ms`** (`settings-api.ts:1866,1888`); delete has none |
| `settings/tenant/add-role/page.tsx` (334) | Create a tenant role | `PersonaCapabilityEditor` | **create role** | as above |
| `settings/tenant/invitations/page.tsx` (201) | Invite users, resend, revoke | `settings/invitations/{InviteFormDialog,InvitationList,InvitationActionDialog}.tsx` | **send invite**, resend, revoke | none (`lib/api/invitations-api.ts`) |
| `settings/tenant/operators/page.tsx` (201) | Grant / revoke operator entitlements | `settings/operators/{GrantOperatorDialog,OperatorGrantList}.tsx` | **grant**, **revoke** | none |
| `settings/tenant/operator-registry/page.tsx` (190) | CRUD the operator registry | `settings/operators/{OperatorFormDialog,OperatorRegistryList,DeleteOperatorDialog}.tsx` | create, edit, delete operator | none |
| `settings/tenant/account/page.tsx` (103) | Own account + output preferences | `output-preferences-card.tsx` | save preferences | none |
| `settings/tenant/improvement/page.tsx` (274) | **Internal-only** improvement findings queue + run history | `components/features/improvement/{FindingsQueue,FindingDetailDrawer,ImprovementRunHistory,InternalOnlyNotice}.tsx` | **trigger an improvement run**, open a finding, **triage a finding** | none; uses a bespoke `improvementFetch` (`lib/api/improvement-api.ts:313`) that **bypasses `fetchWithAuth` entirely**, so not even `api_request_ms` fires here |

### 1.11 Settings — department scope (`settings/department/*`, 7 pages)

| Route | Purpose | Feature components | Key user actions | Route-specific old telemetry |
|---|---|---|---|---|
| `settings/department/page.tsx` (19) | Redirect → team | — | — | none |
| `settings/department/team/page.tsx` (398) | Department members list / edit / remove | `settings/team/{AddTeamMemberDialog,EditTeamMemberDialog}.tsx`, `DataTable` | edit member, remove member | **`settings_member_add_ms`** only (`settings-api.ts:1930`); update/remove have **no timer** |
| `settings/department/team/add/page.tsx` (386) | Add a member | form components | **add member** | as above |
| `settings/department/roles/page.tsx` (350) | Department roles list / edit / delete | `settings/roles/{RoleAccessBadges,EditRoleDialog,DeleteRoleAlert}.tsx` | edit, delete role | **`settings_role_update_ms`** (`settings-api.ts:1402`) |
| `settings/department/roles/add/page.tsx` (303) | Create a department role | `PersonaCapabilityEditor` | **create role** | **`settings_role_create_ms`** (`settings-api.ts:1377`) |
| `settings/department/account/page.tsx` (189) | Account + output preferences | `output-preferences-card.tsx` | save preferences | none |
| `settings/department/memory/page.tsx` (**2,181 lines** — the largest page in the app) | Memory catalogue: tenant facts, user preferences, memory items, badges | `components/features/settings`, `output-preferences-card.tsx`, tabs/tables | switch tab, search, edit/delete a memory item, edit tenant facts, edit output preferences | none |
| `settings/department/dashboard/page.tsx` (631) | **The product-analytics dashboard being rebuilt** — 10 Loki-derived panels | `components/features/analytics/{AnalyticsPanelSection,AnalyticsPanelToolbar,chat-quality-panel-utils}.tsx`, `RouteGuard` | switch panel tab, change time range, change model filter | none (its own load failures go to `logger.error`, which is undelivered — 02 §2.4) |
| `settings/department/loading.tsx` | Suspense fallback | — | — | none |

### 1.12 Cross-cutting surfaces mounted on many routes

| Surface | Component | Actions | Old telemetry |
|---|---|---|---|
| Notification bell | `components/features/notifications/NotificationBell.tsx` + 4 row types (`AutomationNotificationRow`, `NewAdNotificationRow`, `AdRulingInvalidatedNotificationRow`, `AdNoLongerApplicableNotificationRow`) | open panel, mark read, bulk mark read, click through | none (`lib/api/notifications-api.ts:26,41,52`) |
| Page header / user menu | `components/shared/PageHeader.tsx` | sign out, navigate | none |
| Comments (inside the viewer) | `components/features/pdf-viewer/pdf-comments.tsx`, `hooks/api/useComments.ts`, `app/api/comments/**` | list, create, update, delete, thumbs-up a comment | `comments_render_ms` (`pdf-comments.tsx:65`) + the URL-inferred `comments_*_ms` family |
| Work-order export | `app/api/workorders/export/route.ts` | export selected work orders (CSV/XLSX) | none |

### 1.13 SSE / streaming and long-running flows (need explicit start/end events)

| Flow | Client entry | Transport | Observable milestones today | Gap |
|---|---|---|---|---|
| **Chat answer stream** | `lib/api/client.ts:208-300` `sendMessageStream` → `fetchStreamWithAuth` (`lib/api/fetch-utils.ts:187`) | `POST …/chats/rag/stream`, `Accept: text/event-stream`, manual `ReadableStream` + `TextDecoder` reader loop (`client.ts:242-300`) | SSE event types parsed: `init`, `step`, `synthesis_started`, `synthesis_chunk`, `synthesis_completed`, `thinking`, `narration`, `final`, `error` (`client.ts:294-300`) | **Only one timer exists** (`chat_request_ms`, whole-turn) and the failure path mis-times it (§1.3). No send→first-token, no time-to-first-synthesis-chunk, no stream-abort event, no per-step timing |
| **Report preview stream** | `components/features/chat/ReportPreviewModal.tsx:87` `fetchStreamWithAuth` | streamed artifact bytes | `api_request_ms` only (timer stops when headers arrive, not when the body finishes) | no start/end pair |
| **Document Hub content stream** | `lib/chat/document-hub.ts` → `app/api/document-hub/documents/[id]/content-stream/route.ts` | SSR proxy → `copilot-mro` | `api_request_ms` (URL contains `document` ⇒ mis-labelled `pdf_api_ms`) | no open/close pair |
| **PDF byte stream** | `app/api/documents/[id]/stream/route.ts` → `core GET /pdf/stream` | HTTP Range requests, **one per chunk from PDF.js** | `pdf_api_ms` per range request | request count ≫ documents opened; a per-open fact must be minted client-side (02 §1.6) |
| **Data-discovery job progress** | `hooks/data-discovery/useDiscoveryPolling.ts` | **polling, not SSE** — TanStack `refetchInterval` backing off 5 s → 60 s (`:44-61`) | every poll is an `api_request_ms` | no job-started / job-reached-terminal-state pair; the polls themselves are noise |
| **Automation run** | `hooks/api/useAutomations.ts:195` `useRunAutomationNow` → `POST /automations/{id}/run` | fire-and-forget; outcome arrives via `useAutomationRuns` refetch (`:110`) | `api_request_ms` on the trigger only | no run-started/run-observed-complete pair from the UI |
| **Optimizer solve** | `lib/api/optimizer-api.ts:703` `runJob` + `getRun:719` polling | polling | `api_request_ms` | same gap |
| **AD corpus materialize** | `ad-review-api.ts:367` + `getAdMaterializeStatus:380` | polling | `api_request_ms` | same gap |
| **Document Hub upload** | `lib/api/client.ts:979-1017` multipart POST | single request, no progress events | `api_request_ms` | no started/completed/failed triple; processing outcome is backend-side |

**Note:** `grep -rn "EventSource" dashboard/` returns **zero hits** — the only true server-push flow is
the chat `fetch`+reader loop. Everything else labelled "streaming" in the product is polling.

---

## PART 2 — GAP ANALYSIS

### 2.1 The shape of the gap

The instrumented feature vocabulary is frozen at **five buckets** —
`'login' | 'chat' | 'pdf' | 'comments' | 'api' | 'route'` (`lib/logging/feature-metrics.ts:8`) — and
`inferFeatureFromUrl` (`:69-88`) classifies purely by substring on the URL. Every product area shipped
since then falls through to the `api` default and is indistinguishable in the data.

File mtimes make the drift concrete: the whole instrumentation layer is dated **2026-03-10**
(`feature-metrics.ts`, `vitals.ts`, `ErrorBoundary.tsx`, `setup.ts`, `otel.ts`), with only `logger.ts`
(2026-08-13) and `page-tracking.ts` (2026-08-10) touched since. The feature directories it is meant
to cover are dated 2026-07 → 2026-08: `document-hub` (08-17), `data-discovery` (08-16), `copilots`
(08-16), `mro/ad-review` (08-16), `automations` and `improvement` (08-15), `notifications` (08-14),
`optimizer` (08-11), `help` (07-09).

### 2.2 Product areas with NO route-specific telemetry hook at all

| Product area | Routes | User actions invisible today | What exists instead |
|---|---|---|---|
| **Document Hub** | `mro/document-hub` | upload started/completed/failed, preview opened, metadata edit, sharing-scope change, retry processing, delete | `api_request_ms` — and **mis-labelled `pdf_api_ms`**, because the URL contains `document` (`feature-metrics.ts:85-87`) |
| **Automations** | `mro|pilot|crew/automations` (3) | automation created/updated/deleted, **run-now triggered**, run outcome observed, schedule changed | `api_request_ms` only |
| **Airworthiness / AD review** | `mro/airworthiness` | disposition set / cleared (**the triage action**), recompute, corpus materialize, filter/tab switches | `api_request_ms` only |
| **Data Discovery** | `data-discovery`, `…/jobs/[jobId]`, `…/tables/[tableId]` | source registered, **job started**, job reached a terminal state, Level-2 run started, table opened | `api_request_ms` per poll — and the backoff poller (`useDiscoveryPolling.ts:44-61`) makes poll count a function of *wedge duration*, not of usage |
| **Optimizer** | `optimizer` | schedule CSV upload, process, **solve run started/finished**, run export, wizard step progression, copilot-dock question | `api_request_ms` across 38 call sites, all bucketed `api` |
| **Rostering** | `rostering` | section switch, scenario run, **roster export**, audit-log read | nothing (no `RouteGuard` metric either) |
| **Memory** | `settings/department/memory` (2,181 lines) | memory item edited/deleted, tenant fact edited, output preferences saved | nothing |
| **Improvement queue** | `settings/tenant/improvement` | run triggered, finding opened, **finding triaged** | **nothing at all** — `improvementFetch` (`lib/api/improvement-api.ts:313`) bypasses `fetchWithAuth`, so not even `api_request_ms` fires |
| **Invitations / operators / operator registry** | `settings/tenant/{invitations,operators,operator-registry}` | invite sent / resent / revoked, operator granted / revoked, registry CRUD | nothing (`lib/api/invitations-api.ts` uses `fetchWithAuth` so `api_request_ms` fires, but with no action semantics) |
| **Notifications** | `NotificationBell` on every page | panel opened, notification read, click-through | nothing |
| **Analytics dashboard itself** | `settings/department/dashboard` | panel switched, range changed, filter changed, load failed | nothing; its own `logger.error` on failure is undelivered (02 §2.4) |
| **Work-order export** | `app/api/workorders/export/route.ts` | export requested / size / failure | nothing (SSR route; server-side logger lines never flush — 02 §1.1) |
| **Chat sub-actions** | all 3 chat routes | **thumbs up/down**, feedback comment, **citation opened**, clarification answered, share, stop-generation, attachment added, filter applied, data-view opened, report previewed | only whole-turn `chat_request_ms` |
| **Session lifecycle** | app-wide | `session_started` / `session_ended` (design §7.2 product facts) | nothing — `page_view`/`page_exit` are per-page, not per-session |
| **Document open/close** | 3 viewer routes + `DocumentCard` | `document_opened` / `document_closed` with dwell (design §7.2) | nothing with a document id (02 §1.6) |

### 2.3 Existing hooks that are stale, mis-targeted or dead

| # | Item | Evidence | Why it is stale |
|---|---|---|---|
| 1 | `startCommentsTimer()` | `feature-metrics.ts:255-268`; **zero call sites** outside its own definition | Dead function. Its five metric names survive only because `metricNameForFeature` (`:90-107`) re-derives them from any URL containing `comment` |
| 2 | `reportFeatureCount()` | `feature-metrics.ts:188-194`, re-exported at `lib/logging/index.ts:10`; **zero call sites** | The only counter primitive in the layer was never adopted — which is why every product action is a latency metric or nothing |
| 3 | `FeatureName` member `'route'` | `feature-metrics.ts:8` | `inferFeatureFromUrl` never returns it and `metricNameForFeature` returns `null` for it (`:105`). Dead enum member |
| 4 | `setUserId()` | `logger.ts:361-363`, exported `index.ts:5` | Sets a module-level `userId` that is never read (02 §1.0). Dead |
| 5 | `window.__pageTracker` | `components/logging/PageTracker.tsx:28`; **zero consumers** | Published debug handle nothing reads |
| 6 | `cleanRoute()` only knows `/mro/document/*` | `logger.ts:65-75` — regex `^\/mro\/document\/[^?]+(\?.*)?$` | Written when MRO was the only viewer. `/pilot/document/<id>`, `/crew/document/<id>`, `/data-discovery/jobs/<jobId>`, `/data-discovery/jobs/<jobId>/tables/<tableId>` all keep their raw ids in the `route` field ⇒ **unbounded route cardinality** and an inconsistent `route` label per department |
| 7 | `/loginwithsso` in `PUBLIC_PAGE_PATHS` | `lib/auth/public-paths.ts:31`; `find app -ipath '*sso*'` returns **nothing** | Allowlist entry for a route that does not exist in `app/`. Harmless but load-bearing in two tests (`tests/unit/auth/public-paths-single-source.test.ts:99`, `invite-middleware-bounce.test.ts:109`), so it must be retired deliberately, not incidentally |
| 8 | `login_request_ms` measures the wrong thing | `inferFeatureFromUrl:70-72` matches `/auth` as a substring; the only such URL in the app is `buildCoreApiUrl('/authz/catalog')` (`lib/api/authz-api.ts:29`) | The actual sign-in is `signIn()` from `aws-amplify/auth` (`components/features/auth/LoginView.tsx:6,170`) and never passes through `fetchWithAuth`. So `login_request_ms` is **100% authz-catalog latency mislabelled as login latency** |
| 9 | `pdf_api_ms` over-matches | `inferFeatureFromUrl:85-87` — any URL containing `document` **or** `pdf` | Sweeps in `/documents` metadata, `/document-hub/*` (upload, listing, taxonomy, navigation, content-stream) and `/mro-documents/workorders/export`. Document-Hub traffic is reported as PDF-viewer traffic |
| 10 | Chat failure timing | `hooks/chat/useDepartmentMessageStream.ts:459-462` | Mints a **new** timer on the error path and stops it immediately ⇒ every failed turn reports `chat_request_ms ≈ 0`. Failures are both invisible and mean-lowering |
| 11 | `most_accessed_pages` cannot see Crew | `core/.../chat_quality_service.py:70-76` regex `^/(mro|pilot)/document/.*` (02 §2.2) | Written before the Crew department existed. The panel is dead anyway (delivery off), but the *rebuild* must not inherit a department allowlist |
| 12 | Next `error.tsx` segments are unreported | 10 files under `app/(dashboard)/**/error.tsx`; `lib/logging/ErrorBoundary.tsx` is mounted only by `LoggingProvider` | A route-segment render error renders `error.tsx` and the React boundary never fires ⇒ the app's most user-visible failures produce **no** error event |
| 13 | `chart-card-visual-test` is a product route | `app/chart-card-visual-test/page.tsx` | A dev harness sitting in the production route table; it will produce `page_view`s indistinguishable from product usage |

### 2.4 Custom-metric names whose emitter is gone or was never wired

Of the 32 names in 02 §1.2:

| Metric name | Emitter status |
|---|---|
| `settings_department_action_ms` | **No emitter.** Requires `startSettingsTimer('department', 'delete'\|'assign')` (`feature-metrics.ts:271-273`); `settings-api.ts` only ever calls `'create'` (`:1538`) and `'update'` (`:1601`) |
| `settings_role_action_ms` | **No emitter.** Only `'create'`/`'update'` are called (`settings-api.ts:1377,1402,1866,1888`) |
| `settings_member_update_ms` | **No emitter.** Only `startSettingsTimer('member','create')` is called (`settings-api.ts:1930`) |
| `settings_member_action_ms` | **No emitter.** Same reason |
| `comments_list_ms`, `comment_create_ms`, `comment_update_ms`, `comment_delete_ms`, `comments_request_ms` | Emitter *exists but is not the intended one*: `startCommentsTimer` is dead (2.3 #1); the names are produced incidentally by `metricNameForFeature` for any URL containing `comment`. `hooks/api/useComments.ts:10` uses `apiGet/apiPost/apiPut/apiDelete` → `apiRequest` (`lib/api/utils.ts:297`), which *is* timed, so the names do appear — but they measure the Next SSR proxy hop (`/api/comments/*`), not the `core` call |
| `login_request_ms` | Emitter exists but measures `/authz/catalog` (2.3 #8) |
| the remaining 22 | Emitters present and correct |

**Net: 4 names with no emitter, 6 more whose emitter measures something other than the name.**

### 2.5 Structural gaps that any catalogue must fix

| Gap | Consequence |
|---|---|
| No counters — everything is a latency metric riding one `custom_metric` log line (`vitals.ts:131-137`) | "How many uploads happened" is unanswerable even in principle |
| No entity ids on any metric (`startPdfOpenTimer()` takes no args, `feature-metrics.ts:235`) | No document, chat, automation, job or run can be followed |
| No tenant/user on the envelope by design (`logger.ts:115-118`) | Attribution is entirely server-side; the browser cannot self-report a product fact |
| `X-Session-ID` exists and is well-designed (`lib/api/utils.ts:101-107`, owner-bound at `:135-158`) but **is never attached to any telemetry event** | The one ready-made correlation key is unused by the telemetry layer |
| `requestId` is buried at `data.context.requestId` (02 §1.2) | The only FE↔BE join key is three levels deep in an untyped blob |
| No sampling (`logger.ts:97-99` always returns `true`) + click/resize/scroll firehose | Why delivery was switched off in the first place (02 §1.4) |

---

## PART 3 — DRAFT EVENT CATALOGUE (curated set, 25 events)

### 3.0 Rules the catalogue obeys

| Rule | Statement |
|---|---|
| Naming | `browser.*` = an ops signal (how the app behaved). `product.*` = a product fact (what a person did) |
| Signal types | **P** = `product_events` row via `POST {api}/analytics/events` (design §7.2). **L** = OTel log record. **S** = OTel span |
| `product_events` allow-list | Design §7.2 allow-lists exactly four `event_name` values. **Only those four are P.** Every other product-ish event is an L until the owner extends the allow-list — the candidates are flagged in §3.4 |
| Attributes | Low-cardinality enums, numeric measures, and opaque ids only. **No free text ever** — no `text`, `ariaLabel`, `href`, question, filename, comment body, error message from user input |
| Route label | `route_pattern` = the Next route template (`/mro/document/[id]`), never the concrete path. A single `routePattern()` helper replaces `cleanRoute` (2.3 #6) |
| Identity envelope | Every event carries `session.id` (`X-Session-ID`, `lib/api/utils.ts:101-107`), `trace_id`/`span_id` from the active span, `route_pattern`, `app.version`, `deployment.environment`. `tenant_id`/`user_id` are stamped **server-side** at ingest, as today (`logger.ts:115-118`) |
| Ids that may ride | `document_id`, `chat_id`, `block_id`, `automation_id`, `run_id`, `job_id`, `document_hub_document_id`. These are tenant-scoped opaque ids, already present in URLs and payloads |

Consumer column: **§7.3 <tab>** = a v1 product view in the settings dashboard; **§9.2 #n** = the
numbered Grafana/CloudWatch ops panel.

### 3.1 Product facts — the four `product_events` rows (all MUST)

| # | `event.name` | Trigger (component + action) | Attributes | Sampling | Signal | Consumer |
|---|---|---|---|---|---|---|
| 1 | `product.document_opened` | Three emit points, one fact: (a) `components/features/chat/DocumentCard.tsx:96` `handleOpenDocument` — catalog branch `:114`, `libraryRef` branch `:100`, `attachmentId` branch `:109`; (b) viewer mount `app/(dashboard)/{mro,pilot,crew}/document/[id]/page.tsx` when arrived at directly; (c) `DocumentHubPreviewDialog` open | `document_id`, `document_kind` ∈ {`catalog`,`document_hub`,`upload`}, `source_surface` ∈ {`chat_citation`,`library`,`viewer`}, `page_number` (int\|null), `department` ∈ {mro,pilot,crew}, `route_pattern`, `session_id` | 100% | **P** | §7.3 Usage & adoption → "Documents opened / top documents by distinct users" (the rebuilt `most_accessed_pages`); §9.2 #5 |
| 2 | `product.document_closed` | Viewer unmount / `pagehide` on `app/(dashboard)/{mro,pilot,crew}/document/[id]/page.tsx`; preview-dialog close | `document_id`, `document_kind`, `dwell_ms` (int), `max_page_reached` (int\|null), `page_number` (entry page), `department`, `route_pattern`, `session_id` | 100%, **best-effort on unload** (design §7.4 accepts loss) | **P** | §7.3 Usage & adoption → "documents opened, dwell" |
| 3 | `product.session_started` | First authenticated mount after `bindSessionIdToUser()` assigns an owner (`lib/api/utils.ts:144-166`) — i.e. the moment the session id becomes attributable | `session_id`, `entry_route_pattern`, `referrer_kind` ∈ {`direct`,`internal`,`external`}, `viewport_bucket`, `device_kind` ∈ {`desktop`,`tablet`,`mobile`} (from `hooks/ui/use-mobile.ts`) | 100% | **P** | §7.3 Usage & adoption → "Sessions and session duration"; WAU/MAU cross-check |
| 4 | `product.session_ended` | `pagehide`/`visibilitychange:hidden` with no return within the idle window, **or** `clearSessionId()` (`lib/api/utils.ts:169-181`) on sign-out | `session_id`, `duration_ms`, `end_reason` ∈ {`signout`,`unload`,`idle`,`identity_change`}, `route_count`, `chat_turn_count`, `document_open_count` | 100%, best-effort on unload | **P** | §7.3 Usage & adoption → session duration |

**Citation opened is event #1 with `source_surface='chat_citation'`** — not a separate event. That is
the only way the three-way catalog / Document-Hub / upload split (`DocumentCard.tsx:100-112`) stays a
single comparable fact.

### 3.2 Ops events — `browser.*`

| # | `event.name` | Trigger | Attributes | Sampling | Signal | Tier | Consumer |
|---|---|---|---|---|---|---|---|
| 5 | `browser.web_vital` | `web-vitals` callbacks, `lib/logging/vitals.ts:34-97` | `metric` ∈ {LCP,INP,CLS,FCP,TTFB}, `value`, `rating` ∈ {good,needs-improvement,poor}, `route_pattern`, `navigation_type` | 100% (≤5/page-load) | L | **MUST** | §9.2 #5 "Web Vitals by route and rating"; the p75-regression alert (§9.4) |
| 6 | `browser.error` | Four sources folded into one name: `lib/logging/ErrorBoundary.tsx:33` (React boundary), `:130` (`window.error`), `:141` (`unhandledrejection`), `:150` (resource error) — **plus the 10 `app/**/error.tsx` segment boundaries, which report nothing today (2.3 #12)** | `error_kind` ∈ {`react_boundary`,`route_segment`,`window_error`,`unhandled_rejection`,`resource`}, `error_type` (constructor name), `component` (allow-listed), `route_pattern`, `resource_kind`, `fingerprint` (hash of type+top frame). **Message and stack are redacted to a bounded, PII-scrubbed form or omitted** | 100%, deduped 15 s per fingerprint | L | **MUST** | §9.2 #5 "browser errors"; browser-error-rate alert (§9.4) |
| 7 | `browser.api.request` | `FetchInstrumentation`/`XHRInstrumentation` (`lib/observability/otel.ts:59-78`) — **not** a hand-rolled timer | `http.request.method`, `url.template` (= `routePattern()`), `http.response.status_code`, `server.address`, `request_id` (response header, `feature-metrics.ts:112-126`) as a span attribute, `session.id` | **head-sampled 10%** (design §7.4); errors and status ≥ 500 forced to 100% | S | **MUST** | §9.2 #5 "API latency as seen from the browser"; #1 cross-check against server RED |
| 8 | `browser.chat.turn` | Span opened at `hooks/chat/useDepartmentMessageStream.ts:236` (send), closed at `:347` (success) / `:459` (failure — **stopping the original timer, fixing 2.3 #10**). Child measures come from the SSE reader loop `lib/api/client.ts:294-300` | `department`, `chat_id`, `block_id`, `outcome` ∈ {`completed`,`aborted`,`error`,`clarification`}, `ttf_init_ms` (`init` event), `ttf_token_ms` (first `synthesis_chunk`), `total_ms`, `step_count`, `has_documents` (bool), `has_attachments` (bool), `is_followup` (bool) | 100% (a few per session) | S | **MUST** | §9.2 #3/#4 (agent turn latency and outcomes, joined to the server span by `trace_id`); §7.3 Reliability latency percentiles as a client-side cross-check |
| 9 | `browser.route.change` | `history.pushState`/`popstate` hook, `lib/logging/page-tracking.ts:189` + `:216` | `route_pattern_from`, `route_pattern_to`, `change_ms`, `ready_ms`, `nav_kind` ∈ {`push`,`replace`,`pop`} | 100% | L | SHOULD | §9.2 #5 "route timings" |
| 10 | `browser.app.boot` | Once per document load, replacing `app_startup` + `navigation_timing` (`lib/logging/setup.ts:25`, `vitals.ts:190-200`) | `dom_interactive_ms`, `dom_content_loaded_ms`, `load_complete_ms`, `ttfb_ms`, `entry_route_pattern`, `app_version`, `is_public_page` | 100% | L | SHOULD | §9.2 #5; release-regression comparison by `app_version` |
| 11 | `browser.auth.login` | `components/features/auth/LoginView.tsx:162` start; `:177`/`:223` submit→auth; `:196`/`:259` auth→ready | `phase` ∈ {`submit_to_auth`,`to_ready`}, `duration_ms`, `outcome` ∈ {`success`,`challenge`,`failure`}, `challenge_kind` ∈ {`new_password`,`totp`,`none`} | 100% | L | SHOULD | §9.2 #5; login-funnel health. **Replaces `login_request_ms`, which measures `/authz/catalog` (2.3 #8)** |
| 12 | `browser.pdf.render` | `components/features/pdf-viewer/pdf-viewer-main.tsx:96` (open) and `:168` (page switch) | `phase` ∈ {`open`,`page_switch`}, `duration_ms`, `document_id`, `document_kind`, `page_count_bucket`, `bytes_bucket`, `outcome` | 100% | L | SHOULD | §9.2 #5 "PDF timings"; pairs with product fact #1 by `document_id` |
| 13 | `browser.upload.started` | `components/features/document-hub/DocumentHubPageContent.tsx:643-651` (form submit passes validation) | `file_kind` ∈ the `supported_file_kinds` enum, `size_bucket`, `sharing_scope`, `has_department_scope` (bool) | 100% | L | **MUST** | §7.3 Operations → Document Hub (the *attempt* half, which `document_hub_documents` cannot see); §9.2 #6 |
| 14 | `browser.upload.finished` | Same handler, `:664` success / `:672` catch | `file_kind`, `size_bucket`, `duration_ms`, `outcome` ∈ {`queued`,`rejected_policy`,`rejected_size`,`server_error`,`aborted`}, `document_hub_document_id` (on success) | 100% | L | **MUST** | as above; a `rejected_*` outcome is invisible server-side |
| 15 | `browser.automation.run_triggered` | `hooks/api/useAutomations.ts:195` `useRunAutomationNow` mutation start | `automation_id`, `department`, `trigger` = `manual`, `outcome` ∈ {`accepted`,`rejected`} | 100% | L | SHOULD | §7.3 Operations → Automation runs (distinguishes *manual* from *scheduled*, which `automation_runs.trigger` already records — this is the corroborating client fact) |
| 16 | `browser.automation.run_settled` | `hooks/api/useAutomations.ts:110` `useAutomationRuns` observing a terminal `RunStatusBadge` state for a run this session triggered | `automation_id`, `run_id`, `terminal_status`, `observed_wait_ms` | 100% | L | LATER | §7.3 Operations. **Authoritative completion is `automation_runs`; this only measures what the operator waited for** |
| 17 | `browser.discovery.job_started` | `app/(dashboard)/data-discovery/page.tsx` `runSource` mutation `onSuccess` (`:156-162`); Level-2 run from `dataDiscoveryApi.createLevel2Run` (`lib/api/data-discovery.ts:120`) | `job_kind` ∈ {`level1`,`level2`}, `source_kind` = `postgres`, `job_id` | 100% | L | SHOULD | §7.3 deferred "data-discovery run health"; §9.2 #6 |
| 18 | `browser.discovery.job_settled` | `hooks/data-discovery/useDiscoveryPolling.ts:53` — the poll where `isInProgress` first returns false | `job_kind`, `job_id`, `terminal_status`, `observed_wait_ms`, `poll_count` | 100% | L | LATER | as above; also retires the per-poll `api_request_ms` noise (2.2) |
| 19 | `browser.settings.mutation` | Counter at the API layer: `lib/api/settings-api.ts:1377,1402,1538,1601,1866,1888,1930` **plus the currently-untimed delete/assign paths and** `lib/api/invitations-api.ts`, the operator dialogs, `organizationSave.ts` | `entity` ∈ {`department`,`role`,`member`,`invitation`,`operator`,`operator_registry`,`organization`,`memory`,`output_preferences`}, `action` ∈ {`create`,`update`,`delete`,`grant`,`revoke`,`resend`}, `scope` ∈ {`tenant`,`department`}, `outcome`, `duration_ms` | 100% | L | SHOULD | §7.3 **deferred** Admin tab (access-change audit feed); §9.2 #6. **Replaces all 9 `settings_*_ms` names, 4 of which have no emitter (2.4)** |
| 20 | `browser.chat.feedback_submitted` | `components/features/chat/FeedbackDialog.tsx` submit via `hooks/chat/useFeedback.ts` → `lib/api/client.ts:1022` `sendFeedback` | `feedback_type` ∈ {`thumbs_up`,`thumbs_down`,`cleared`}, `has_comment` (bool — **never the comment text**), `department`, `block_id`, `outcome` | 100% | L | SHOULD | §7.3 Quality → "Feedback rate". **The counted fact stays `chat_feedback` (server); this event exists to catch writes that never landed and to measure dialog-open→submit** |
| 21 | `browser.chat.clarification_answered` | Next `sendMessage` on a turn whose predecessor had `needs_clarification` (`hooks/chat/{useMro,usePilot}MessageStream.ts:469,428`) | `department`, `chat_id`, `prior_block_id`, `answered_within_ms`, `answer_kind` ∈ {`typed`,`suggestion_chip`} | 100% | L | SHOULD | §7.3 Quality → "clarification rate" (the server knows a clarification was *asked*; only the browser knows it was *answered* rather than abandoned) |
| 22 | `browser.export.requested` | `lib/api/optimizer-api.ts:797` `fetchRunExport`; `app/api/workorders/export/route.ts`; the rostering export panel | `export_kind` ∈ {`optimizer_run`,`work_orders`,`roster`}, `format`, `row_count_bucket`, `duration_ms`, `outcome` | 100% | L | LATER | §7.3 deferred optimizer tab; §9.2 #6 |
| 23 | `browser.optimizer.run_triggered` | `lib/api/optimizer-api.ts:703` `runJob` (and `:666` `preflightJob`) | `job_id`, `phase` ∈ {`preflight`,`solve`}, `outcome`, `preflight_warning_kind` | 100% | L | LATER | §7.3 deferred "optimizer run health" |
| 24 | `browser.ad_review.disposition_set` | `lib/api/ad-review-api.ts:298` `setAdDisposition` / `:328` clear, from `components/features/mro/ad-review/DispositionDialog.tsx` | `disposition` ∈ the enum, `had_prior_disposition` (bool), `source` ∈ {`table`,`dialog`}, `outcome` | 100% | L | LATER | §7.3 deferred; the AD-review throughput view when a tenant needs it |
| 25 | `browser.log` | The thin wrapper replacing the 336 free-text `logger.*` calls across 79 files (02 §1.1) | `severity`, `component` (module name, allow-listed), `route_pattern`, `code` (a short stable slug per call site), bounded typed fields. **No interpolated prose** | `warn`/`error` 100%; `info` head-sampled 10% in production (design §7.4) | L | SHOULD | §9.2 #5/#6 triage; not a product view |

### 3.3 Tier summary

| Tier | Count | Events |
|---|---|---|
| **MUST** (feeds a ruled v1 §7.3 view) | 10 | #1–#8, #13, #14: `product.document_opened`, `product.document_closed`, `product.session_started`, `product.session_ended`, `browser.web_vital`, `browser.error`, `browser.api.request`, `browser.chat.turn`, `browser.upload.started`, `browser.upload.finished` |
| **SHOULD** (ops value, no v1 view depends on it) | 10 | #9–#12, #15, #17, #19–#21, #25: `browser.route.change`, `browser.app.boot`, `browser.auth.login`, `browser.pdf.render`, `browser.automation.run_triggered`, `browser.discovery.job_started`, `browser.settings.mutation`, `browser.chat.feedback_submitted`, `browser.chat.clarification_answered`, `browser.log` |
| **LATER** (a deferred §7.3 tab reads it) | 5 | #16, #18, #22–#24: `browser.automation.run_settled`, `browser.discovery.job_settled`, `browser.export.requested`, `browser.optimizer.run_triggered`, `browser.ad_review.disposition_set` |

Wire the MUST + SHOULD set in Phase 4 (20 events); the LATER five when their tab is built.

### 3.4 Two decisions this catalogue needs from the owner

| # | Decision |
|---|---|
| A | **Extend the `product_events` allow-list?** Design §7.2 fixes it at four names. `browser.chat.clarification_answered` (#21) and `browser.upload.finished` (#14) are genuine *product* facts a §7.3 tab wants to aggregate over 13 months, but as OTel log records they live under the 14 d / 30 d log retention. Either extend the allow-list to include them, or accept that those two panels read a shorter window than the rest |
| B | **`browser.log` info sampling.** At 10% head sampling an `info` line is no longer a reliable "did this happen" signal. Confirm that debugging is expected to lean on spans + errors, and that the ~17 emoji `logger.info` debug lines in `settings/tenant/page.tsx:28-49` and `add-department/page.tsx:109-112` are deleted rather than converted |

### 3.5 Every exclusion from the old 24 events, one line each

| Old event (02 §1.1) | Disposition |
|---|---|
| `app_startup` | **Folded** into `browser.app.boot` (#10) |
| `page_tracking_initialized` | **Dropped** — an init acknowledgement with no consumer |
| `page_view` | **Dropped as an event**; route identity now rides `browser.route.change` (#9) and, where it is a product fact, `product.document_opened` (#1) |
| `page_exit` | **Dropped** — per-page dwell is noise; dwell survives only where it means something (`product.document_closed`, #2) |
| `page_bounce` | **Dropped** — derivable from `product.session_ended.duration_ms` + `route_count` |
| `user_interaction` (click) | **Dropped** — ruled out in design §7.4; a click on every element in the app is the firehose that got delivery switched off |
| ↳ click payload (`text`, `ariaLabel`, `href`, `dataset`) | **Dropped** — free text and hrefs are exactly the PII surface the redactor cannot scan (02 §1.3) |
| ↳ `form_submit` payload | **Dropped** — the meaningful submits are now named events (#11, #13, #19) |
| ↳ `navigation` payload | **Folded** into `browser.route.change` (#9) |
| `scroll_milestone` | **Dropped** — ruled out in §7.4; reading depth inside a document is better served by `max_page_reached` on #2 |
| `window_state_change` | **Dropped** — the one useful transition (hidden → session over) is `product.session_ended` (#4) |
| `window_resize` | **Dropped** — unthrottled; `viewport_bucket` on `product.session_started` covers the analytic need |
| `web_vital_lcp` / `_inp` / `_cls` / `_fcp` / `_ttfb` | **Folded** — five names collapse into `browser.web_vital` with a `metric` attribute (#5) |
| `web_vitals_import_failed` | **Dropped** — a failed dynamic import surfaces as `browser.error` (#6) |
| `custom_metric` | **Dropped as a carrier** — each measure becomes a named event or a span attribute; nothing rides a generic envelope |
| `long_task` | **Dropped** — INP is the user-visible symptom and is already collected; long-task counts drove no decision |
| `long_task_observer_failed` | **Dropped** — observer-construction failure is a `browser.error` |
| `memory_usage` | **Dropped** — ruled out in §7.4; a 5-minute poll per tab for a Chrome-only heap number |
| `navigation_timing` | **Folded** into `browser.app.boot` (#10) |
| `react_error_boundary` | **Folded** into `browser.error`, `error_kind='react_boundary'` (#6) |
| `window_error` | **Folded** into `browser.error`, `error_kind='window_error'` |
| `unhandled_promise_rejection` | **Folded** into `browser.error`, `error_kind='unhandled_rejection'` |
| `resource_load_error` | **Folded** into `browser.error`, `error_kind='resource'` |

### 3.6 Every exclusion from the old 32 custom metrics, one line each

| Old metric (02 §1.2) | Disposition |
|---|---|
| `route_change_ms` | **Kept** as `browser.route.change.change_ms` (#9) |
| `route_ready_ms` | **Kept** as `browser.route.change.ready_ms` (#9) |
| `api_request_ms` | **Replaced** by the `browser.api.request` span (#7) — a span carries method/status/route natively and joins to the server trace |
| `login_request_ms` | **Dropped** — it measures `/authz/catalog`, not login (2.3 #8) |
| `login_submit_to_auth_ms` | **Kept** as `browser.auth.login` `phase='submit_to_auth'` (#11) |
| `login_to_ready_ms` | **Kept** as `browser.auth.login` `phase='to_ready'` (#11) |
| `chat_request_ms` | **Kept and fixed** as `browser.chat.turn.total_ms` (#8), with the failure-path bug (2.3 #10) corrected and first-token added |
| `comments_list_ms` | **Dropped** — the `browser.api.request` span covers it; the dedicated timer was already dead (2.3 #1) |
| `comment_create_ms` | **Dropped** — same |
| `comment_update_ms` | **Dropped** — same |
| `comment_delete_ms` | **Dropped** — same |
| `comments_request_ms` | **Dropped** — same |
| `pdf_api_ms` | **Dropped** — over-matched every `document`/`pdf` URL including all of Document Hub (2.3 #9); the span replaces it |
| `pdf_open_first_render_ms` | **Kept** as `browser.pdf.render` `phase='open'`, now carrying `document_id` (#12) |
| `pdf_page_switch_ms` | **Kept** as `browser.pdf.render` `phase='page_switch'` (#12) |
| `settings_department_create_ms` | **Folded** into `browser.settings.mutation` `entity='department' action='create'` (#19) |
| `settings_department_update_ms` | **Folded** — same, `action='update'` |
| `settings_department_action_ms` | **Dropped** — no emitter ever existed (2.4); the delete path is picked up by #19 |
| `settings_role_create_ms` | **Folded** into #19 |
| `settings_role_update_ms` | **Folded** into #19 |
| `settings_role_action_ms` | **Dropped** — no emitter (2.4) |
| `settings_member_add_ms` | **Folded** into #19 `entity='member' action='create'` |
| `settings_member_update_ms` | **Dropped** — no emitter (2.4); covered by #19 going forward |
| `settings_member_action_ms` | **Dropped** — no emitter (2.4) |
| `chat_messages_render_ms` | **Dropped** — a React render timing with no consumer; INP measures what the user feels |
| `chat_history_render_ms` | **Dropped** — same |
| `pdf_metadata_render_ms` | **Dropped** — same |
| `pdf_toc_render_ms` | **Dropped** — same |
| `comments_render_ms` | **Dropped** — same |
| `copilots_page_render_ms` | **Dropped** — `browser.route.change.ready_ms` (#9) measures the same thing uniformly for all 46 pages |
| `route_guard_check_ms` | **Dropped** — a permissions-cache lookup; a *denial* is the interesting event and belongs in `browser.error`/authz logs, not a latency metric |
| `auth_guard_check_ms` | **Dropped** — same |

---

## PART 4 — IMPLEMENTATION NOTES: WHERE THE EVENTS GET EMITTED

### 4.1 The seven choke points

All 25 events are reachable from **seven** places. Nothing in the catalogue requires touching a page
component, and only two feature components are edited.

| # | Choke point | File:line | Events it emits | Why it is the right seam |
|---|---|---|---|---|
| **C1** | **API client wrapper** | `lib/api/fetch-utils.ts:133` `fetchWithAuth`, `:187` `fetchStreamWithAuth`; `lib/api/utils.ts:297` `apiRequest` | #7 (as span attributes), #13/#14, #19, #22, #23, and the `request_id` correlation on everything | Already the single point where `startApiTimer` fires today; every typed client except four (see 4.3) funnels through it |
| **C2** | **Router / route pattern** | `lib/logging/page-tracking.ts:412-430` (history patch) + `:171-216` (change/ready timing); replace `cleanRoute` at `logger.ts:65-75` with a `routePattern()` helper | #9, #10, and the `route_pattern` field on the envelope of **every other event** | One helper fixes the `/mro/document` -only collapse (2.3 #6) for all 46 routes at once |
| **C3** | **Provider root** | `components/providers/LoggingProvider.tsx:13-18` + `components/providers/IdentityBoundary.tsx:41` (`bindSessionIdToUser`) | #3, #4, #5, #6, #10 | `IdentityBoundary` is *already* the one watcher on identity change and the owner of the session id — session start/end are the same transition it handles, so no new lifecycle logic is invented |
| **C4** | **TanStack mutation cache** | `lib/query/query-client.ts:12-18` `MutationCache` (add `onSuccess`/`onSettled` beside the existing `onError`), keyed off `mutation.meta` | #15, #16, #17, #18, #20, #23, #24, and the memory/output-preference half of #19 | 11 files already declare mutations (`hooks/api/{useAutomations,useComments,useImprovement,useOptimizer}.ts`, `hooks/mro/useAdReview.ts`, `hooks/chat/{useFeedback,useShare}.ts`, `hooks/settings/{useMemoryMutations,useOutputPreferencesQuery}.ts`, both data-discovery pages). A `meta: { telemetry: { event, attrs } }` convention wires all of them declaratively, mirroring the existing `meta.suppressGlobalError` pattern |
| **C5** | **Chat stream hooks** | `hooks/chat/useDepartmentMessageStream.ts:236` (start) / `:347` (success) / `:459` (failure), reading milestones from the SSE reader loop `lib/api/client.ts:294-300` | #8, #21 | One shared hook backs all three departments (`useMro/usePilot/useCrewMessageStream` wrap it), and the SSE event names are parsed in exactly one switch |
| **C6** | **`DocumentCard`** | `components/features/chat/DocumentCard.tsx:96-127` `handleOpenDocument` | #1 for `source_surface='chat_citation'`, all three `document_kind` values | The only place in the app where catalog / Document-Hub / upload opens are already distinguished (`:100`, `:109`, `:114`) |
| **C7** | **PDF viewer** | `components/features/pdf-viewer/pdf-viewer-main.tsx:93-96` (open), `:159-168` (page switch); viewer page mount/unmount `app/(dashboard)/{mro,pilot,crew}/document/[id]/page.tsx:27` (`use(params)`) | #1 for `source_surface='viewer'`, #2 (dwell + `max_page_reached`), #12 | The existing timers live here; they need the document id threaded in (they take no arguments today, `feature-metrics.ts:235`) |

Two components are edited outside the seams: `components/features/document-hub/DocumentHubPageContent.tsx:643-679`
(the upload handler is a bare `async` function, not a mutation — #13/#14) and a shared
`app/**/error.tsx` component so all 10 segment boundaries report (#6, 2.3 #12).

### 4.2 Identity and session fields available at each choke point

| Field | Where it comes from | Available at |
|---|---|---|
| `session.id` | `getSessionId()` — `lib/api/utils.ts:101-107`. A **module-level function, not a hook**, so it is callable from anywhere including non-React code; owner-bound and re-minted on identity change (`bindSessionIdToUser`, `:135-158`); persisted in `sessionStorage` under an unscoped key (`:31`) | **All of C1–C7.** This is the single cheapest identity field in the app and the telemetry layer does not use it today (2.5) |
| `trace_id` / `span_id` | `trace.getActiveSpan()?.spanContext()` from `@opentelemetry/api`, once the fetch/XHR instrumentations from `lib/observability/otel.ts:59-78` are active | C1, C5 reliably (inside a fetch); C2–C4, C6, C7 only when an operation is in flight — otherwise omitted |
| `route_pattern` | The new `routePattern()` helper (C2), from `usePathname()` in React code or `window.location.pathname` outside it | All of C1–C7 |
| `department` | The route's first segment (`/mro`, `/pilot`, `/crew`) — already parsed for chat (`useDepartmentMessageStream` `department` prop) and viewer pages | C2, C5, C6, C7; derived from `route_pattern` elsewhere |
| `tenant_id` / `user_id` | `useAuth()` (`lib/auth/AuthContext.tsx`) and `usePermissions()` — **but deliberately NOT sent** (`logger.ts:115-118`: a client-authored tenant id is a 400 for the whole batch, `core/.../logging_endpoints.py:135,149` `extra="forbid"`). The server stamps both at ingest | Nowhere — by design. Keep it that way |
| `app.version` / `deployment.environment` | `RUNTIME.APP_VERSION` / `RUNTIME.ENV` (`lib/runtime-config.ts`), already on the envelope (`logger.ts:119-128`) | All |
| `request_id` | Response headers `x-request-id` / `x-amzn-requestid` / `x-amz-request-id` / `x-correlation-id` (`feature-metrics.ts:112-126`) | C1 only — promote it from `data.context.requestId` to a first-class span/log attribute |

### 4.3 Clients that bypass C1 today and must be brought onto it

| Bypass | File:line | Consequence |
|---|---|---|
| `authenticatedApiRequest` | `lib/api/utils.ts:400` | No timer, no span attributes. Used by the `authenticatedApi{Get,Post,Put,Delete,Patch}` family (`:427-470`) |
| `rawApiRequest` | `lib/api/utils.ts:546` | File downloads and non-JSON responses are entirely untimed |
| the PDF request helper | `lib/api/utils.ts:514` | The `Accept: application/pdf` path is untimed |
| `improvementFetch` | `lib/api/improvement-api.ts:313` | The improvement queue produces **zero** telemetry of any kind (2.2). It is bespoke on purpose (the 403-internal-only distinction must survive, `:262`) — so it needs its own emit call rather than a rewrite onto `fetchWithAuth` |

`lib/api/invitations-api.ts:250` also has one raw `fetch(` outside the helper.

### 4.4 New modules the catalogue needs

| Module | Responsibility |
|---|---|
| `lib/telemetry/route-pattern.ts` | `routePattern(pathname)` → the Next route template. Replaces `cleanRoute` (`logger.ts:65-75`) and `buildRoutePattern` (`feature-metrics.ts:53-67`, which collapses only `^[0-9a-fA-F-]{10,}$` and therefore misses non-UUID ids). Must be derived from the actual `app/` route table, and guarded by a test that fails when a new dynamic segment is added without a pattern |
| `lib/telemetry/events.ts` | The typed catalogue: one exported function per event name, so an attribute typo is a compile error and the allow-list is enforceable by a lint test (design §8, G20 attribute lint) |
| `lib/telemetry/product-events.ts` | The `POST {api}/analytics/events` client for #1–#4: typed, batched at 50 (design §7.2), authenticated via `fetchWithAuth`, with a bounded queue and a `visibilitychange`/`pagehide` best-effort flush. **Must be excluded from C1's own instrumentation** the way `isLoggingIngestUrl` (`feature-metrics.ts:128-138`) already excludes the log-ingest path, or it will time itself |
| `lib/telemetry/otlp-exporter.ts` | The OTLP/JSON exporter over the authenticated fetch helper (design §7.4), replacing the `logger.ts` queue whose two `fetch` calls are commented out |

### 4.5 Deletions this catalogue authorises

| Delete | Lines | Reason |
|---|---|---|
| `lib/logging/page-tracking.ts` interaction/scroll/window half | ~250 of 443 (`:99-160`, `:258-340`, `:365-430` minus the history patch) | Click / scroll / resize / window-state events are all dropped (§3.5) |
| `lib/logging/feature-metrics.ts` | 292 | Every one of its 32 metric names is kept, folded or dropped by §3.6; the remaining timing lives in spans and named events |
| `lib/logging/vitals.ts` `reportCustomMetric` + `long_task` + `memory_usage` | `:131-137`, `:150-161`, `:173-178`, `:223` | Dropped carriers (§3.5) |
| `logger.setUserId` | `logger.ts:361-363` | Dead (2.3 #4) |
| `window.__pageTracker` | `components/logging/PageTracker.tsx:28` | Zero consumers (2.3 #5) |
| `app/chart-card-visual-test/page.tsx` | 145 | A dev harness in the production route table (2.3 #13) — exclude from the build, or at minimum from telemetry |

Net: the ~1,650-LOC layer (02 §1.0) is replaced by a catalogue module plus four thin emitters.

---

## Appendix — quick index of surfaces to instrumentation

| Product area | Routes | Old hooks | New events |
|---|---|---|---|
| Auth | 5 | `login_*_ms` (2 real, 1 mislabelled) | #11, #3 |
| Copilots landing | 1 | `copilots_page_render_ms` | #9 |
| Chat (mro/pilot/crew) | 3 | `chat_request_ms`, 2 render timings | #8, #20, #21, #1 |
| Document viewer | 3 | 5 pdf/comment timings | #1, #2, #12 |
| Document Hub | 1 (+1 proxy) | none | #13, #14, #1 |
| Automations | 3 | none | #15, #16 |
| Airworthiness | 1 | none | #24 |
| Data Discovery | 3 (+guard) | none | #17, #18 |
| Optimizer | 1 | none | #23, #22 |
| Rostering | 1 | none | #22 |
| Settings (tenant) | 11 | 4 timers, 3 dead names | #19 |
| Settings (department) | 7 | 3 timers, 2 dead names | #19 |
| Help | 1 | none | #9 only |
| App-wide | all | page/click/scroll firehose | #5, #6, #7, #9, #10, #25, #3, #4 |
