# Frontend telemetry, product-analytics contract and deployment wiring — inventory (2026-09-05)

Research deliverable for the observability rebuild. Read-only ground-truth pass over
`dashboard/`, `core/`, `copilot-mro/deployment/`, `api/` and `iac/`.
Every claim carries a `path:line`. "not found" means a search was run and returned nothing.

Companion documents: `docs/plans/observability-rebuild-audit.md` (current-state audit, G1..G17),
`docs/plans/observability-rebuild-research/` (sibling research files).

---

## PART 1 — FRONTEND TELEMETRY INVENTORY (`/home/aditya/Code/dashboard`)

### 1.0 Layer map

| File | LOC | Role |
|---|---|---|
| `dashboard/lib/logging/logger.ts` | 384 | Queue, batching, redaction, dedupe, delivery (**both sends commented out**) |
| `dashboard/lib/logging/page-tracking.ts` | 443 | page_view / page_exit / interaction / scroll / window-state / bounce |
| `dashboard/lib/logging/vitals.ts` | 233 | Web Vitals, long tasks, memory, navigation timing, `custom_metric` |
| `dashboard/lib/logging/feature-metrics.ts` | 292 | Named latency metrics on top of `reportCustomMetric` |
| `dashboard/lib/logging/ErrorBoundary.tsx` | 159 | React boundary + `window` global error handlers |
| `dashboard/lib/logging/setup.ts` | 32 | `initializeLogging()` — wires the three above |
| `dashboard/lib/logging/index.ts` | 10 | Barrel |
| `dashboard/components/providers/LoggingProvider.tsx` | 27 | Calls `initializeLogging()` + `initializeFrontendTracing()` in a `useEffect` |
| `dashboard/components/logging/PageTracker.tsx` | 41 | Mounts `usePageTracking`, publishes `window.__pageTracker` |
| `dashboard/lib/observability/otel.ts` | 93 | Browser OTel WebTracerProvider + fetch/XHR instrumentation |

Mount point: `dashboard/components/providers/AppProviders.tsx:24` wraps the whole tree in
`<LoggingProvider>`; `LoggingProvider.tsx:13-18` runs `initializeLogging()` then
`initializeFrontendTracing()` once on mount. So the telemetry layer is **active on every route**,
public and authenticated alike.

### 1.1 Every event the layer can emit today

All events are `logger.info|warn|error` calls, i.e. they all become the same `LogEvent` shape
(`logger.ts:13-28`) — `msg` is the event name, everything specific rides in `data`.

**Common envelope for every event** (`logger.ts:119-128`, `baseContext()`):
`ts` (ISO), `env` (`RUNTIME.ENV`), `appVersion` (`RUNTIME.APP_VERSION`), `browser`
(`navigator.userAgent`), `os` (`navigator.platform`), `viewport {w,h}`,
`route` (= `cleanRoute(location.pathname + location.search)`), `isPublicPage`.
Deliberately **no tenant and no user id** — `logger.ts:115-118` documents that attribution is
server-side and that an extra field would 400 the whole batch. `setUserId()` (`logger.ts:361-363`)
sets a module-level `userId` that **is never read** — dead code.

| # | Event (`msg`) | Level | Emitter | `data` fields | Trigger |
|---|---|---|---|---|---|
| 1 | `app_startup` | info | `setup.ts:25-29` | `userAgent`, `timestamp`, `url` | once per mount of `LoggingProvider` |
| 2 | `page_tracking_initialized` | info | `page-tracking.ts:432-434` | `timestamp` | end of `initializePageTracking()` |
| 3 | `page_view` | info | `page-tracking.ts:62-68` | `pageId`, `pageViewCount`, `sessionDuration`, `timestamp`, + caller `metadata` — but `<PageTracker>` is mounted exactly once, with no props (`LoggingProvider.tsx:22`), so `pageName` is always `undefined` | `usePageTracking` effect on pathname change (`:171-176`) |
| 4 | `page_exit` | info | `page-tracking.ts:80-86` | `pageId`, `dwellTime`, `interactionCount`, `maxScrollDepth`, `timestamp` | new page view, hook unmount, or `beforeunload` with dwell ≥ 30 s |
| 5 | `page_bounce` | info | `page-tracking.ts:153-158` | `pageId`, `dwellTime`, `interactionCount`, `timestamp` | unmount within 30 s, or `beforeunload` with dwell < 30 s (`:334-338`). Calls `flushLogs()` (`:159`) |
| 6 | `user_interaction` | info | `page-tracking.ts:99-105` | `pageId`, `interactionType`, `interactionCount`, `timestamp`, + per-type payload | global capture-phase `click` (`:382`), `submit` (`:397`), history `pushState`/`replaceState`/`popstate` (`:412-430`) |
| 6a | ↳ click payload | | `page-tracking.ts:365-378` | `element`, `tagName`, `id`, `role`, `name`, `ariaLabel`, `text` (≤80 ch), `href`, `dataset`, `buttonName` | every click anywhere in the app |
| 6b | ↳ form_submit payload | | `page-tracking.ts:391-395` | `formName`, `method`, `action` | every form submit |
| 6c | ↳ navigation payload | | `page-tracking.ts:403` | `from`, `to` (both `cleanRoute`d) | SPA nav |
| 7 | `scroll_milestone` | info | `page-tracking.ts:124-129` | `pageId`, `milestone` (0.25/0.5/0.75/1.0), `scrollDepth`, `timestamp` | scroll listener (`:258`) |
| 8 | `window_state_change` | info | `page-tracking.ts:137-141` | `state` (`maximize`\|`minimize`\|`focus`\|`blur`), `pageId`, `timestamp` | `visibilitychange`, `focus`, `blur`, `resize` (`:306-320`) |
| 9 | `window_resize` | info | `page-tracking.ts:321-326` | `width`, `height`, `pageId`, `timestamp` | every `resize` event — **unthrottled** |
| 10 | `web_vital_lcp` | info | `vitals.ts:34-42` | `value`, `id`, `delta`, `rating`, `context_action='render'`, `interaction_type='paint'`, `interaction_target` | `onLCP` |
| 11 | `web_vital_inp` | info | `vitals.ts:50-58` | same shape; `context_action` from first entry name / interaction type | `onINP` |
| 12 | `web_vital_cls` | info | `vitals.ts:63-71` | same shape; `interaction_target = largestShiftTarget` | `onCLS` |
| 13 | `web_vital_fcp` | info | `vitals.ts:75-84` | same shape | `onFCP` |
| 14 | `web_vital_ttfb` | info | `vitals.ts:89-97` | same shape; target = navigation entry name | `onTTFB` |
| 15 | `web_vitals_import_failed` | warn | `vitals.ts:100-103` | `error`, `message` | dynamic `import('web-vitals')` rejects |
| 16 | `custom_metric` | info | `vitals.ts:132-137` | `name`, `value`, `context`, `timestamp` | **the single carrier for all 32 named metrics** (see 1.2) |
| 17 | `long_task` | warn | `vitals.ts:150-154` | `duration`, `startTime`, `name` | `PerformanceObserver` `longtask` > 50 ms |
| 18 | `long_task_observer_failed` | warn | `vitals.ts:161` | `error` | observer construction throws |
| 19 | `memory_usage` | info | `vitals.ts:173-178` | `used`, `total`, `limit`, `usage` (%) | on init + `setInterval` every 5 min (`:223`) |
| 20 | `navigation_timing` | info | `vitals.ts:190-200` | `domContentLoaded`, `loadComplete`, `domInteractive`, `redirect`, `dns`, `tcp`, `request`, `response`, `processing` | once at init |
| 21 | `react_error_boundary` | error | `ErrorBoundary.tsx:33-38` | `error`, `stack`, `componentStack`, `errorBoundary=true` | `componentDidCatch` |
| 22 | `window_error` | error | `ErrorBoundary.tsx:130-136` | `message`, `source`, `lineno`, `colno`, `stack` | `window.addEventListener('error')` |
| 23 | `unhandled_promise_rejection` | error | `ErrorBoundary.tsx:141-144` | `reason`, `stack` | `unhandledrejection` |
| 24 | `resource_load_error` | warn | `ErrorBoundary.tsx:150-154` | `type`, `src`, `href` | capture-phase `error` where target ≠ window |

Plus **free-text application logs**: `logger.info/warn/error(<prose>, …)` is called
**336 times across 79 files** (excluding `tests/`; `rg -c 'logger\.(debug|info|warn|error|fatal)\('`)
— route handlers under `app/api/*`, hooks, components. These are not named events;
they are English sentences with an arbitrary `data` object. Examples:
`app/api/documents/[id]/route.ts:113`, `app/api/tenant/route.ts:89` (`'🔐 Using JWT authentication…'`),
`app/api/comments/route.ts:106`.
**These `app/api/*` calls run on the Next SSR server**, where `baseContext()` takes the
`typeof window === 'undefined'` branch (`logger.ts:103-113`) → `browser='server'`, `os='server'`,
no `route`, and `isPublicPage: true` — i.e. server-side Next logs would be posted to the **public**
ingest endpoint and stamped with the anonymous tenant sentinel. There is no `fetch` on the server
side of the queue either way, and the timer is `setTimeout` in Node, so these accumulate in a
per-process array that is never drained.

### 1.2 The `custom_metric` family (all ride event #16)

| Metric `name` | Value | Emitted at |
|---|---|---|
| `route_change_ms` | ms from `history.pushState` to page-view registration | `page-tracking.ts:189` |
| `route_ready_ms` | ms to 2× rAF after route change | `page-tracking.ts:216` |
| `api_request_ms` | duration of any `fetchWithAuth`/`fetchStreamWithAuth` call | `feature-metrics.ts:177` |
| `login_request_ms` / `login_submit_to_auth_ms` | | `feature-metrics.ts:94`, `:209` |
| `login_to_ready_ms` | | `feature-metrics.ts:213` |
| `chat_request_ms` | | `feature-metrics.ts:96`, `:230` |
| `comments_list_ms`, `comment_create_ms`, `comment_update_ms`, `comment_delete_ms`, `comments_request_ms` | | `feature-metrics.ts:98-102`, `:260-265` |
| `pdf_api_ms` | any URL containing `document` or `pdf` (`:85-87`) | `feature-metrics.ts:103` |
| `pdf_open_first_render_ms` | PDF first render | `feature-metrics.ts:240` |
| `pdf_page_switch_ms` | PDF page switch | `feature-metrics.ts:250` |
| `settings_department_create_ms` / `_update_ms` / `_action_ms` | | `feature-metrics.ts:274` |
| `settings_role_create_ms` / `_update_ms` / `_action_ms` | | `feature-metrics.ts:276` |
| `settings_member_add_ms` / `_update_ms` / `_action_ms` | | `feature-metrics.ts:277` |

Eight more `reportCustomMetric` names live outside `feature-metrics.ts`:

| Metric `name` | Emitted at |
|---|---|
| `chat_messages_render_ms` | `hooks/chat/useDepartmentChatHistory.ts:248,278`; `hooks/chat/useDepartmentMessageStream.ts:402` |
| `chat_history_render_ms` | `components/features/chat/ChatSidebar.tsx:115` |
| `pdf_metadata_render_ms` | `components/features/pdf-viewer/pdf-document-header.tsx:146` |
| `pdf_toc_render_ms` | `components/features/pdf-viewer/pdf-toc.tsx:80` |
| `comments_render_ms` | `components/features/pdf-viewer/pdf-comments.tsx:65` |
| `copilots_page_render_ms` | `components/features/copilots/CopilotsPageContent.tsx:52` |
| `route_guard_check_ms` | `components/features/auth/RouteGuard.tsx:133,171` |
| `auth_guard_check_ms` | `components/features/auth/AuthGuard.tsx:67,78` |

**32 distinct metric names in total**, every one of them delivered as an `info`-level
`custom_metric` log line rather than as a metric.

`context` on an API-timer metric (`feature-metrics.ts:160-174`) carries `feature`, `action`,
`success`, `method`, `url`, `routePattern` (ids collapsed to `:id`, `:53-67`), `status`,
`requestId` (from `x-request-id` / `x-amzn-requestid` / `x-amz-request-id` / `x-correlation-id`,
`:112-126`), `bytes` (`content-length`), `network` (`effectiveType`, `downlink`, `rtt`),
`device.deviceMemory`, `extra`.
`requestId` is the **only** existing FE↔BE correlation key, and it is nested three levels deep
inside `data.context.requestId`.

Self-loop guard: `feature-metrics.ts:128-138,150-152` skips timing for
`/logging/ingest` and `/logging/public/ingest`.

### 1.3 Sampling, dedupe, batching

| Rule | Where | Effect |
|---|---|---|
| Sampling | `logger.ts:97-99` | `shouldSample()` **always returns `true`** — no sampling at all |
| Dedupe | `logger.ts:330-336` | for `warn`/`error`/`fatal` only: identical `level:msg` within **15 s** is dropped. `info` (i.e. every product event above) is never deduped |
| Redaction | `logger.ts:79-94` | key-name regex `pass(word)?\|token\|authorization\|email\|phone\|card\|secret\|key\|password` → `[REDACTED]`, recursive. Values are never scanned, so an email inside `text`/`href`/`msg` survives |
| Batch size | `logger.ts:36` | `MAX_BATCH = 20`; flush when queue ≥ 20 (`:301-303`) |
| Flush interval | `logger.ts:37` | `FLUSH_MS = 5000` — a one-shot `setTimeout` armed on the first enqueue (`:294-299`) |
| Single-flight | `logger.ts:200-202` | `inFlight` guard; queue is unbounded — **no max queue length, no eviction** |
| Console | `logger.ts:339-346` | dev only; `next.config.mjs:22` `removeConsole` strips console in production |

### 1.4 Delivery path — and why nothing reaches the backend

```
enqueue → QUEUE → flush() (logger.ts:199)
        → split by `isPublicPage`
        → public  → buildCoreApiUrl('/logging/public/ingest')   [fetch COMMENTED OUT :233-242]
        → private → buildCoreApiUrl('/logging/ingest')          [fetchWithAuth COMMENTED OUT :257-266]
```

| Aspect | Ground truth |
|---|---|
| Endpoints | `PUBLIC_ENDPOINT='/logging/public/ingest'`, `AUTHENTICATED_ENDPOINT='/logging/ingest'` (`logger.ts:38-39`) |
| URL build | `buildCoreApiUrl` → `API_BASE_URL + API_PREFIX + CORE_PREFIX + endpoint` (`lib/config.ts:23-60`) |
| Auth | private half via `fetchWithAuth` (`lib/api/fetch-utils.ts:133`) → `getAuthHeaders()` Cognito idToken, single-flight refresh on 401/419 (`:156-165`) |
| Gate before send | `isUserAuthenticated()` = `getToken() !== null` (`logger.ts:60-62`); if false the private half is **re-queued to the front** (`:253`) and retried on every later flush — it is never dropped and never expires |
| Split rule | `isPublicPage` captured at log-creation time (`logger.ts:209-210`), from `isPublicPageForLogging(location.pathname)` (`lib/auth/public-paths.ts:91-98` — `PUBLIC_PAGE_PATHS` `/login`, `/register`, `/forgot-password`, `/new-password`, `/loginwithsso`, `/invite` (`:26-40`), **plus `/auth`**), matched on segment boundaries (`:73-79`) |
| Payload | `{"logs": [...]}` built **before** the guards (`logger.ts:221-224`) so a `JSON.stringify` throw drops both halves instead of wedging |
| `keepalive` | present only inside the commented-out blocks (`logger.ts:237`, `:261`) |
| `sendBeacon` | **not found anywhere in `dashboard/`** — grep for `sendBeacon` returns zero hits |
| Page unload | `beforeunload` (`page-tracking.ts:329-340`) emits `page_bounce` or `page_exit`; `page_bounce` calls `flushLogs()` (`:159`) which is `async` and unawaited. With delivery restored, an unload flush would depend entirely on `keepalive:true`; there is no `visibilitychange`-based flush and no `pagehide` handler — the two events Chrome actually guarantees on mobile/bfcache |
| Retry classification | `LogDeliveryError` (`logger.ts:140-148`) carries the HTTP status; `isRetryableLogFailure` (`:163-166`) returns `true` for anything that is **not** a `LogDeliveryError`, and for status <400 or ≥500. `handleFailedLogBatch` (`:172-189`) `unshift`s a retryable batch back to the FRONT of the queue |
| The wedge | Documented at `logger.ts:229-232` and `:255-256`: if the restored call throws a plain `Error` instead of a `LogDeliveryError`, a permanently-rejected batch is classified transient and re-queued to the front **forever**, so no later log ever ships. The wedge fix (the error class + classifier + `reportLogDeliveryFailure` test seam at `:288-289`) is fully written and unit-testable; only the two `fetch` calls are disabled |

**Would events reach the backend if the two `fetch` calls were uncommented?** Analysis per surface:

| Surface | Verdict |
|---|---|
| Public pages (`/login`, `/register`, `/invite`, …) | **Yes.** `fetch(publicUrl, {keepalive:true})`, no auth header needed; `core` accepts anonymously (see §7) |
| Authenticated browser pages | **Yes, once a token exists.** Anything logged before login is held in the queue (`logger.ts:251-253`) and delivered on the first post-login flush — but stamped with the *then-current* session, so pre-login events are attributed to whoever eventually signs in |
| Next SSR route handlers (`app/api/*`) | **No.** `isPublicPage:true` on the server branch routes them to the public endpoint, but nothing ever triggers a flush in a request-scoped server invocation and the queue is per-Lambda-process. In practice these lines vanish |
| Batch size vs server cap | Safe: `MAX_BATCH=20` < server `MAX_PUBLIC_BATCH=50` (`logger.ts:32-35` documents this) |
| Volume risk | **Real.** No sampling, `user_interaction` on *every* click and `window_resize` unthrottled ⇒ a resize drag alone produces dozens of events/second. At 20/batch with a 5 s timer and a single in-flight request, a busy session generates a continuous POST stream. This is very likely why delivery was switched off |

### 1.5 Browser OTel (`dashboard/lib/observability/otel.ts`)

| Aspect | Ground truth |
|---|---|
| Entry | `initializeFrontendTracing()` called once from `LoggingProvider.tsx:17` |
| SDK | `@opentelemetry/sdk-trace-web` `WebTracerProvider` + `BatchSpanProcessor` + `exporter-trace-otlp-http` (`otel.ts:17-27`), all `require`d lazily inside a `try` |
| Instrumentation | `FetchInstrumentation` (`otel.ts:59-68`) and `XMLHttpRequestInstrumentation` (`:70-78`). **Nothing else** — no document-load, no user-interaction, no long-task instrumentation, and no manual spans anywhere in the app |
| Custom span attrs | `component='fetch'` / `component='xhr'` only (`otel.ts:65`, `:75`) |
| Resource attributes | `service.name='flynapse-dashboard'` (hardcoded, `otel.ts:39`), `service.version=runtime.APP_VERSION\|\|'local'`, `deployment.environment=runtime.ENV\|\|'development'`, merged onto `Resource.default()` (`:43-49`). **No tenant, no user, no session, no browser/OS attributes** |
| Exporter endpoint | `otel.ts:37`: `runtime.OTEL_EXPORTER_OTLP_ENDPOINT \|\| '/otlp/v1/traces'` |
| Endpoint resolution | `lib/runtime-config.ts:90-93` defaults `OTEL_EXPORTER_OTLP_ENDPOINT` to **`http://localhost:4318/v1/traces`**. It is in `PUBLIC_RUNTIME_KEYS` (`:155`) so `getPublicRuntimeConfig` copies it into `window.__RUNTIME_CONFIG__` (injected at `app/layout.tsx:60`). Because the default is non-empty, the value is *always* present ⇒ **the `/otlp/v1/traces` relative fallback in `otel.ts:37` is unreachable dead code** |
| CORS / propagation | `propagateTraceHeaderCorsUrls: [/.*/]` on both instrumentations (`otel.ts:60`, `:71`) — `traceparent` is injected on **every** cross-origin request, including Cognito, S3 signed URLs and any third party. `ignoreUrls: [otlpUrl]` avoids self-tracing |
| Failure mode | whole init wrapped in `try/catch` → `console.warn` (`otel.ts:86-90`), and `removeConsole` strips that in production. Export failures are swallowed by the BatchSpanProcessor. **Silent** |
| Marker | sets `window.__OTEL_ACTIVE__ = true` (`otel.ts:82`) |

**Can the endpoint be reached in production (Amplify SSR)?** No. Three independent blocks:

1. `dashboard/next.config.mjs` (26 lines, read in full) has **no `rewrites`, no `headers`, no
   `redirects`** — there is no `/otlp` proxy path in the Next app.
2. `dashboard/app/api/` contains exactly 5 route groups — `comments`, `document-hub`, `documents`,
   `tenant`, `workorders` — and **no telemetry route** (`ls -R app/api`). Nothing proxies OTLP.
3. `dashboard/amplify.yml:10` writes `.env.production` from
   `env | grep -e ENV -e APP_VERSION -e API_BASE_URL -e API_PREFIX -e MRO_PREFIX -e CORE_PREFIX -e COGNITO_USER_POOL_ID -e COGNITO_APP_CLIENT_ID -e COGNITO_DOMAIN -e COGNITO_REGION -e COGNITO_IDENTITY_POOL_ID -e COMPANY`.
   `OTEL_EXPORTER_OTLP_ENDPOINT` contains no `ENV` substring and is not listed ⇒ **it can never be
   set on Amplify** unless prefixed `NEXT_PUBLIC_` (line 11 also greps `NEXT_PUBLIC_`, and
   `readEnv` falls back to `NEXT_PUBLIC_<NAME>` at `runtime-config.ts:62`). That `NEXT_PUBLIC_`
   escape hatch is the only currently-possible way to set it, and it would still have to name a
   **publicly reachable, CORS-enabled** collector — the deployed collector sits on a private EC2 IP
   (see Part 3).
   Also missing from the allowlist and therefore stuck on their defaults in Amplify:
   `OPTIMIZER_PREFIX`, `DEMO_MODE`, `DOMAIN_SIGNUP_ENABLED`, `TURNSTILE_SITE_KEY`,
   `DISPLAY_TIMEZONE`.

Net: every browser span is exported to `http://localhost:4318/v1/traces` from the *user's own
machine*, fails, and is dropped silently. Confirms audit **G2**.

### 1.6 Where "documents opened" is observable today

**Front end.** No document-open event exists. The three viewer routes —
`dashboard/app/(dashboard)/mro/document/[id]/page.tsx`,
`.../crew/document/[id]/page.tsx`, `.../pilot/document/[id]/page.tsx` — import `logger`
(`:17`, `:15`, `:16` respectively) and use it for exactly one thing: `logger.error('Sign out error', …)`
(`mro:96`, `crew:78`, `pilot:79`). Nothing else.

What *is* emitted when a user opens a document:

| Signal | Where | Fitness as a "document opened" fact |
|---|---|---|
| `page_view` with `pageId` | `page-tracking.ts:62-68` via the global `PageTracker` | The only candidate today, and the one `chat_quality_service` selects on. But `logger.ts:65-75` `cleanRoute()` **collapses `/mro/document/<id>` to `/mro/document`** before `route` is stamped — and it does *not* touch `/crew/document/...` or `/pilot/document/...`. Meanwhile `pageId` comes from `generatePageId(pathname, new URLSearchParams())` (`page-tracking.ts:34-37,172`), which is the raw pathname **including the id** and always drops the query string. So the document id survives only in `data.pageId`, in an inconsistent form across departments |
| `user_interaction` (`navigation`) | `page-tracking.ts:403` | `from`/`to` are `cleanRoute`d ⇒ MRO document ids are erased here |
| `pdf_open_first_render_ms` | `components/features/pdf-viewer/pdf-viewer-main.tsx:96` (`startPdfOpenTimer`), stopped on first render | A real "document rendered" event. Its `context` carries `feature:'pdf'`, `action:'open'`, `success`, `bytes` — but **no document id** (`feature-metrics.ts:235-243`) |
| `pdf_page_switch_ms` | `pdf-viewer-main.tsx:168` | page-level interaction, no id |
| `pdf_metadata_render_ms`, `pdf_toc_render_ms` | `components/features/pdf-viewer/pdf-document-header.tsx:146`, `pdf-toc.tsx:80` | render timings, no id |
| `api_request_ms` / `pdf_api_ms` | `feature-metrics.ts:177,182` on every `fetchWithAuth` whose URL contains `document` or `pdf` (`:85-87`) | `context.url` and `context.routePattern` are present, but `buildRoutePattern` (`:53-67`) collapses any segment matching `^[0-9a-fA-F-]{10,}$` to `:id` |

**FE hooks where a "document opened" fact could be emitted** (all client-side, all already have the
document id in hand):

| Hook | File:line | What it knows |
|---|---|---|
| Viewer page mount | `app/(dashboard)/{mro,crew,pilot}/document/[id]/page.tsx` — `const { id } = use(params)` (`mro:27`) | documentId, department, `chatId`/`chatUserId`/`chatSource`/`page`/`pageNumbers` query params (`mro:38-53`) |
| PDF first render | `components/features/pdf-viewer/pdf-viewer-main.tsx:93-96` | the existing `startPdfOpenTimer` — only needs the id added to its context |
| Chat citation click | `components/features/chat/DocumentCard.tsx:95-127` `handleOpenDocument` | `doc.documentId`, `pageNumber`, `pages`, `chatId`, `chatUserId`, `department` — the richest single point, and it distinguishes a **catalog** open from a `libraryRef` (Document Hub) open and an `attachmentId` (upload) open (`:101-112`) |
| URL builder | `lib/pdf/document-urls.ts:64-92` (`documentStreamPath`, `documentPrintPath`, `documentSignedUrlPath`) | the id, pre-encoding — a single choke point for every proxy call |
| Document Hub preview | `lib/chat/document-hub.ts:139-160` (`documentHubContentStreamUrl` / `documentHubInlinePreviewUrl`) | Document-Hub document id and `fileKind` |

**Backend routes hit when a document is opened:**

| Browser call | Next proxy | Backend route | Backend telemetry |
|---|---|---|---|
| `/api/documents/{id}/stream?chat_id=` | `dashboard/app/api/documents/[id]/stream/route.ts:47` → `buildCoreApiUrl(PDF_STREAM)` | `core` **`GET /pdf/stream`** — `core/core/resources/document_viewer/pdf_page_endpoints.py:142` | one loguru line `f"Streaming - document: {document_id}, key: {…}, range: {…}"` (`:169-172`). No metric, no span |
| `/api/documents/{id}/signed-url` | `dashboard/app/api/documents/[id]/signed-url/route.ts` | `core` **`GET /pdf/download-url`** — `pdf_page_endpoints.py:102` | one loguru line `f"Download URL - document: {document_id}, key: {…}"` (`:124-126`) |
| `/api/documents/{id}/print` | `dashboard/app/api/documents/[id]/print/route.ts:42` | `core` **`GET /pdf/stream`** (same route) | as above |
| `/api/documents/{id}` (metadata) | `dashboard/app/api/documents/[id]/route.ts` | `core` **`GET /documents/document`** — `core/core/resources/document_viewer/document_endpoints.py:173` | free-text loguru only |
| `/api/document-hub/documents/{id}/content-stream` | `dashboard/app/api/document-hub/documents/[id]/content-stream/route.ts:63-66` | `copilot-mro` **`GET /document-hub/documents/{id}/content`** | the document-hub counters in `copilot-mro/.../document_hub/operations.py:20-42` |

Critical caveat for any "documents opened" metric built on `/pdf/stream`: **PDF.js issues one range
request per chunk**, so `stream` call count is an order of magnitude above documents opened. The
route is reached via `range_header` (`pdf_page_endpoints.py:150-153`) and the proxy forwards the
browser's `Range` header (`stream/route.ts:23-24,57-59`). A per-open fact has to be minted at the
open, not counted at the byte layer.

### 1.7 Other client-visible usage / quality surfaces

| Surface | Route / file | Data shown | API it calls | Gate |
|---|---|---|---|---|
| Chat-quality dashboard | `app/(dashboard)/settings/department/dashboard/page.tsx` | 10 Loki-derived panels (Part 2 §6) | `GET {CORE}/analytics/chat-quality` via `lib/api/analytics-api.ts` | `RouteGuard` `VIEW_DASHBOARD` + backend `is_tenant_admin` |
| Improvement / triage queue | `app/(dashboard)/settings/tenant/improvement/page.tsx` | findings queue + run history; a finding's bag carries `total_cost_usd` and `latency_ms` (`lib/api/improvement-api.ts:109-111`), a run carries `llm_spend` (`:217`) | `POST /improvement/run` (`improvement-api.ts:431`), `GET /improvement/runs` (`:439`), `GET /improvement/findings` (`:461`), `POST /improvement/findings/{id}` triage (`:483`) — all core, via a bespoke `improvementFetch` (`:313`) rather than `fetchWithAuth`, because the 403-internal-only distinction has to survive (`:262`) | `RouteGuard` (coarse) + server-side internal-email-domain check; **the server is authoritative** (page docstring `:38-60`). Deliberately absent from the settings rail |
| Memory | `app/(dashboard)/settings/department/memory/page.tsx` | memory items, badges | `GET {CORE}/memories/catalog`, `/memories`, `/memories/tenant/facts`, `/memories/user/preferences/output` (`lib/api/memory-api.ts:57,70,93,110`) | `RouteGuard` + permissions |
| Automations | automations settings pages | run history incl. `automation_runs.cost_usd` | `GET/POST {CORE}/automations`, `/automations/{id}/run`, `/automations/{id}/runs` (`lib/api/automations-api.ts:227-297`, endpoints declared `lib/config.ts:143-149`) | permissions |

This is the complete set of surfaces that show backend-captured usage/quality data. **The two
Postgres LLM ledgers (`llm_usage`, `llm_model_calls`) have no frontend surface at all** — confirmed
by grepping `dashboard/` for `llm_usage` / `llm_model_calls` (zero hits). Improvement findings and
automation runs expose *derived* cost only, per finding / per run.

---

## PART 2 — PRODUCT ANALYTICS CONTRACT

### 2.1 The endpoint

`core/core/resources/analytics/analytics_endpoints.py:43` —
**`GET {CORE_PREFIX}/analytics/chat-quality`**, `response_model=ChatQualityPanelResponse`.
The router prefix is `/analytics` (`:27`). **This is the only analytics route in `core`.**

| Request param | Type / default | Notes |
|---|---|---|
| `panel_id` | str, default `top_users_by_message_count` (`:46-49`) | must be a key of `PANEL_DEFINITIONS` or **400** (`chat_quality_service.py:760-761`) |
| `time_range` | str, default `"1h"` (`:50`) | one of `1h`/`1d`/`1w`/`1m` (`chat_quality_service.py:40-45`) else **400** |
| `panel_filters` | JSON string, optional (`:51-54`) | must parse to a JSON **object** or **400** (`:80-91`). Only `model_name` is honoured, and only by the LLM-tokens aggregator (`chat_quality_service.py:511-514`) |

Response (`core/core/resources/analytics/schemas.py:19-26`):
`{panel_id, range, last_updated (datetime), available_filters: Dict[str, List[str]], data: List[Dict[str, Any]]}`.
`data` is **untyped** at the API boundary — the row shape is per-panel and only the client's
TypeScript encodes it.

**Gate** (`analytics_endpoints.py:57-75`): 401 with no `request.state.auth_context`; 400 with no
`tenant_id` on it; 403 unless `is_tenant_admin` — which is `auth_context["is_tenant_owner"]` **or**
`authz_context.has_capability(auth_context, "view_dashboard")` (`:31-40`). Deliberately coarse:
"any department", because a dashboard is not department-scoped (`:36`).

**Error map**: `RateLimitError` → 429 (`:106-110`), `ValueError` (bad panel/range) → 400
(`:111-115`), everything else → 500 with a fixed body (`:116-121`).

### 2.2 Panels, LogQL and response shapes

`PANEL_DEFINITIONS` at `chat_quality_service.py:696-737` maps each panel id to
`{query, aggregator}`. All ten queries hardcode `{service_name="copilots"}` (audit **G12**).

| Panel id | LogQL (`chat_quality_service.py` line) | Aggregator | Row shape |
|---|---|---|---|
| `top_users_by_message_count` | `:58-61` `{service_name="copilots"} \|~ "^Enhanced chat request received$" \| line_format "user_id:{{.user_id}},department:{{.department}},tenant_id:{{.tenant_id}}"` | `aggregate_top_users` `:137` | `{user_id, user_name?, department, tenant_id, message_count}` (schema-validated via `TopUserMessageCount`, `:175-183`) |
| `message_volume_over_time` | **same query as above** (`:701-704`) | `aggregate_message_volume` `:267` | `{bucket_start (ISO), message_count}` |
| `active_users_over_time` | `:88-91` `… \|~ "^Enhanced chat request received$" \| line_format "user_id:{{.user_id}},tenant_id:{{.tenant_id}}"` | `aggregate_active_users` `:299` | `{bucket_start, distinct_users}` |
| `llm_tokens_over_time` | `:92-95` `… \|= "LLM request completed" \| line_format "total_tokens:{{.total_tokens}},prompt_tokens:{{.prompt_tokens}},completion_tokens:{{.completion_tokens}},request_id:{{.request_id}},tenant_id:{{.tenant_id}},model:{{.model}}"` | `aggregate_llm_tokens` `:503` | `{bucket_start, total_tokens, prompt_tokens, completion_tokens, distinct_messages, total_llm_calls, estimated_cost}` |
| `chat_time_duration_histogram` | `:77-82` `… \|= "Chat response generated successfully" \| path =~ ".*/chats/rag(/stream)?$" \| line_format "{{.execution_time}}"` | `aggregate_chat_time_duration_histogram` `:634` | `{bucket_start (float s), bucket_end, bucket_label "N-Ms", count}` |
| `router_intent_distribution` | `:66-69` `… \|~ "^Tool Routing Decision$" \| line_format "intent:{{.intent}},tenant_id:{{.tenant_id}}"` | `aggregate_router_intent_distribution` `:382` | `{intent, count}` — **DEAD**, the string `Tool Routing Decision` exists nowhere but this query (audit G7) |
| `most_accessed_pages` | `:70-76` `{service_name="copilots"} \|= "page_view" \| line_format "{{.data}}" \| json \| pageId=~"^/(mro\|pilot)/document/.*" \| line_format "page_id:{{.pageId}},user_id:{{.user_id}},tenant_id:{{.tenant_id}}"` | `aggregate_most_accessed_pages` `:405` | `{page_id, distinct_users}` — **DEAD** (audit G1: the only `page_view` emitter is `page-tracking.ts:62` and delivery is off) |
| `feedback_received_over_time` | `:62-65` `… \|~ "^Response feedback saved successfully$" \| line_format "feedback_type:{{.feedback_type}},department:{{.department}},tenant_id:{{.tenant_id}}"` | `aggregate_feedback_volume` `:337` | `{bucket_start, thumbs_up, thumbs_down, null_feedback}` |
| `top_users_by_comment_count` | `:83-87` `… \|~ "^Successfully created comment$" \| path =~ ".*comments.*" \| line_format "user_id:{{.user_id}},department:{{.department}},tenant_id:{{.tenant_id}}"` | `aggregate_top_users` | same as panel 1 (`message_count` counts comments) |
| `comments_created_over_time` | **same query as above** (`:721-724`) | `aggregate_message_volume` | `{bucket_start, message_count}` |

Notes that matter for a rebuild:

- **Four of the ten panels are duplicate queries** (`top_users`/`message_volume` share
  `LOGQL_TOP_USERS`; `top_comment_users`/`comment_volume` share `LOGQL_COMMENTS_CREATED`). They are
  fetched and cached separately, so the same Loki scan runs twice.
- **`most_accessed_pages` only matches `/mro/` and `/pilot/`** (`:74`) — a `/crew/document/…`
  `pageId` is excluded by the regex, and the strip list at `:427-430` likewise omits `crew`.
- **Even if `page_view` shipped, the MRO half would be broken**: `cleanRoute` collapses
  `/mro/document/<id>` before the `route` field is stamped, but the query reads `pageId` out of
  `data`, which keeps the id — so MRO works and crew does not, for two unrelated reasons.
- **`estimated_cost` is a hardcoded price** — `$1.25 / 1M` input, `$10 / 1M` output
  (`chat_quality_service.py:566-570`), applied to every model regardless of which one emitted the
  tokens. The real per-call cost is already in `llm_model_calls`.
- **`distinct_messages`** = count of distinct `request_id` values in the bucket (`:557,573`).
- The bucket unit is `hour` for `1h`/`1d` and `day` for `1w`/`1m` (`:189-190`), and empty buckets
  are pre-seeded (`:219-230`) so a series has continuous x-values; an all-empty result returns `[]`
  (`:259-260`).
- `available_filters` is populated only for `llm_tokens_over_time` (`:787-791`) by
  `extract_llm_models`, which scans the *unfiltered* entries for distinct `model` values (`:485`).

### 2.3 Cache, rate limit, Loki fetch

| Rule | Value | Where |
|---|---|---|
| Cache key | `analytics:chat_quality:{panel_id}:{tenant_id}:{time_range}:{filters-json\|"none"}` | `chat_quality_service.py:769-775` |
| Cache TTL | `settings.analytics_cache_ttl_seconds`, default **300 s** | `:808`, `core/core/config.py:74-76` |
| Cache backend | `utils.cache_service.get_cache_service()` | `:738` |
| Rate limit | fixed window, key `analytics:rate_limit:{tenant_id}:{now//window}`; **60 requests / 60 s per tenant** | `:812-828`, `core/core/config.py:77-82` |
| Loki URL | `settings.loki_base_url` + `/loki/api/v1/query_range`, default **`http://localhost:3100`** | `:832-833`, `core/core/config.py:73` |
| Loki auth | **none** — plain `httpx.AsyncClient().get(url, params=…)`, no headers, no `X-Scope-OrgID` | `:846-848` |
| Loki params | `query`, `start`/`end` (ns), `limit=settings.analytics_loki_query_limit` (**5000**), `direction="forward"` | `:838-844`, config `:83-85` |
| Timeout | `settings.analytics_loki_timeout_seconds`, default **10 s** | `:845`, config `:86-88` |
| Truncation | at `len(entries) >= limit` it logs `"Loki query hit limit; results may be truncated"` and returns anyway | `:884-888` |
| Tenant filter | **not in the LogQL**; every aggregator drops non-matching rows in Python (`:150-152`, `:250-252`, `:388-390`, `:411-413`, `:494-496`, `:653-655`) — audit **G10** |
| Failure | any httpx error / non-200 / `status != success` → `RuntimeError("Failed to query Loki")` → the endpoint's blanket `except` → **500 "Failed to fetch chat quality panel"** | `:849-864`, `analytics_endpoints.py:116-121` |

`direction="forward"` + `limit=5000` means the window is truncated from the **oldest** end forward,
so on a busy tenant the panel silently shows only the beginning of the range.

### 2.4 Frontend consumption

`dashboard/lib/api/analytics-api.ts` (107 lines) is a thin typed client: `CHAT_QUALITY_PANEL_IDS`
(`:4-15`) mirrors the ten backend ids, `fetchChatQualityPanel` (`:93-107`) builds
`buildCoreApiUrl('/analytics/chat-quality', {panel_id, time_range, panel_filters?})` and calls
`fetchWithAuth`. Row interfaces at `:23-83`.

`dashboard/app/(dashboard)/settings/department/dashboard/page.tsx` (631 lines,
`DepartmentChatQualityPage`) holds `PANEL_REGISTRY` (`:58-197`) — the chart mapping:

| Panel id | Title | `variant` | Series / axis |
|---|---|---|---|
| `top_users_by_message_count` | Top 10 Users by Message Count | `top-users` | metric `Messages` |
| `active_users_over_time` | Active Users Over Time | `time-series` | `distinct_users` |
| `message_volume_over_time` | Message Volume Over Time | `time-series` | `message_count` |
| `llm_tokens_over_time` | LLM Token Consumption | `time-series` | `prompt_tokens`, `completion_tokens`, `total_tokens`; y-unit `M`, format `millions`; filter `model_name` (`:112-122`) |
| `chat_time_duration_histogram` | Chat Time Duration Histogram | `histogram` | metric `Requests` |
| `router_intent_distribution` | Query Type Distribution | `pie` | — |
| `most_accessed_pages` | Most Accessed Documents | `ranked-pages` | metric `Distinct Users` |
| `feedback_received_over_time` | Feedback Received Over Time | `time-series` | `thumbs_up`, `thumbs_down`, `null_feedback` |
| `top_users_by_comment_count` | Top 10 Users by Comment Count | `top-users` | metric `Comments` |
| `comments_created_over_time` | Comments Created Over Time | `time-series` | `message_count` |

The five variants are rendered by `components/features/analytics/chat-quality-panel-utils.tsx`
(402 lines) with the config type in `chat-quality-panel-types.ts:29-46`; chrome lives in
`AnalyticsPanelSection.tsx` (116) and `AnalyticsPanelToolbar.tsx` (122).

**Fetched but never rendered — CONFIRMED.** Grepping `dashboard/` for each LLM-token field:
`estimated_cost`, `distinct_messages` and `total_llm_calls` appear **only** in the type declaration
(`lib/api/analytics-api.ts:70-72`) and at **no** render site. `prompt_tokens`, `completion_tokens`
and `total_tokens` each appear once more, as `timeSeriesSeries` keys (`page.tsx:108-110`).
So the panel throws away the call count, the distinct-message count and the only cost number the
whole product surface ever computes.

**Fetch behaviour** (`page.tsx:342-431`): one request for the **active panel only**
(`loadPanelData`), re-run by a `useEffect` on `[loadPanelData]` (`:432-434`) whose deps are
`activePanel`, `activePanelRequestFilters`, `permissionsLoading`, `canViewDashboard`,
`setTabTransitioning`, `timeRange` (`:424-431`) — i.e. it refetches on panel switch, time-range
change or filter change, and **never on a timer**. There is no refresh button and no auto-refresh.

**Error handling** (`page.tsx:405-419`): every failure — 429, 403, Loki timeout, Loki down — is
caught in one block, logged via `logger.error('Failed to load chat quality panel', …)` (which goes
nowhere, see §1.4) and collapsed into the single string
`'Failed to load chat quality data.'`. Rate-limit and backend-outage are indistinguishable to the
user, and the server-side truncation warning is never surfaced.

**Filter reconciliation** (`page.tsx:366-397`): a selected `model_name` that is absent from the
freshly returned `available_filters` is reset to `__all__` (`ALL_PANEL_FILTER_VALUE`, `:198`).

**Permissions**: `RouteGuard` + `usePermissions().hasCapability(PERMISSION_NAMES.VIEW_DASHBOARD)`
(`page.tsx:249-252`); when false, `loadPanelData` returns early without a request (`:343-347`).
The comment at `:249-251` records that this is a **capability** check, not a legacy permission row,
because the tenant owner holds no rows.

### 2.5 Log-ingest contract (`core/core/resources/logging/logging_endpoints.py`, 372 LOC)

Three routes only — asserted by test `tests/api/logging/test_logging_attribution.py:37`
(`test_the_remaining_routes_are_exactly_three`):

| Route | Auth | Caps |
|---|---|---|
| `POST /logging/ingest` (`:292`) | `resolve_request_identity(request)` (`:314`) — fails **closed**: 401 with no auth context, 409 for an unfinished registration, 403 for an unresolvable tenant (`core/core/authz/request_identity.py:102-122`) | none beyond the client's own `MAX_BATCH=20` |
| `POST /logging/public/ingest` (`:329`) | none; tenant stamped `ANONYMOUS_TENANT_SENTINEL = "__anonymous__"` (`:26`), `user_id=None` (`:358-359`) | body ≤ **64 KiB** → 413 (`:30`, `:348-353`); batch ≤ **50** events → 413 (`:31`, `:204-213`); **60 req/min per client IP** → 429 (`:32`, `:83-107`) |
| `GET /logging/health` (`:323`) | none | — |

**Schemas** (`:110-149`): `LogEvent` requires `level`, `msg`, `ts`; optional
`route`/`component`/`traceId`/`spanId` (typed `Any`), `env`/`appVersion`/`browser`/`os`
(str, default `"unknown"`), `viewport: Dict[str, Any]`, `data: Any`, `isPublicPage: Optional[bool]`.
**`model_config = ConfigDict(extra="forbid")`** on both `LogEvent` (`:135`) and `LogBatch` (`:149`)
— a client-authored `tenant_id` is a **400 for the whole batch**, never a silently dropped field
(`:131-134`, test `test_a_payload_carrying_a_tenant_id_is_a_400_over_the_handler`
`test_logging_attribution.py:130`).

**Quarantine / attribution rules**, from `core/tests/api/logging/`:
- `test_logging_attribution.py:43` — ingest stamps the **authenticated** tenant, not the payload.
- `:64` — an absent auth context is a **401**, not an unattributed batch.
- `:88` — the live client payload shape (`baseContext()` + `isPublicPage`) still validates.
- `:113` — malformed JSON is a **400**, not a 200 carrying `{"error": …}` (the old shape made a
  permanently-bad batch indistinguishable from success).
- `test_public_ingest_quarantine.py:42` — the sentinel is not a valid tenant id.
- `:47`, `:86` — public events are stamped anonymous and a client **cannot name a real tenant**.
- `:105`, `:128` — neither the pydantic report nor an unexpected exception is echoed to an
  anonymous caller.
- `:155` — one flooding client does not silence another (per-key windows).

**What the endpoint DOES with an accepted event** (`:234-271`): it **re-logs through loguru** —
level-mapped `debug/info/warning/error/critical` (`fatal`→`critical`, unknown→`info`), with
message `f"[{log_event.env}] {log_event.msg}"` (`:239`) and these kwargs (`:242-256`):

| kwarg | Source |
|---|---|
| `tenant_id` | **server-decided** (session or sentinel) |
| `user_id` | **server-decided** |
| `route`, `component`, `traceId`, `spanId`, `appVersion`, `browser`, `os`, `viewport` | from the event |
| `data` | `safe_json_dumps(log_event.data)` (`:365-372`) — a JSON **string** |

**Dropped on the floor**: the client's `ts` (the server-receive time is used instead), `level` as a
field (only the loguru level), `isPublicPage`, and `env` (folded into the message prefix).

**Survival into Loki**: the loguru record then hits the OTLP sink at
`utils/utils/logging_config.py:178-232`. Every `extra` key is `setattr` onto a stdlib `LogRecord`
and **stringified** (`:222-228`), then emitted through the OTel `LoggingHandler` → OTLP → collector
→ Loki. `otelTraceID`/`otelSpanID` are attached only when a span is active (`:209-211`) — for a
log-ingest POST that is the gateway's server span, which is *the ingest request's* trace, not the
browser's. The record timestamp is `time.time()` plus a nanosecond jitter (`:194-204`), so
**event-time is lost twice**: once by dropping the client `ts`, once by re-stamping at emit.

Consequence for the LogQL in §2.2: `most_accessed_pages` works because the message is
`[production] page_view` (matched with `|= "page_view"`) and `data` is a JSON string that
`| line_format "{{.data}}" | json` can re-parse. Any rebuild that changes the message prefix, the
`data` serialisation, or `OTEL_SERVICE_NAME` breaks that panel silently.

---

## PART 3 — DEPLOYMENT WIRING

### 3.1 Compose stacks

All four compose files pin **`:latest`** for every observability image — no version is pinned
anywhere in the estate.

| Service | Image | `observability-local/observe-docker-compose.yml` | `deployment/docker-compose.yml` | `deployment/poc/docker-compose.yml` | `deployment/demo/docker-compose.yml` |
|---|---|---|---|---|---|
| otel-collector | `otel/opentelemetry-collector:latest` | `:5-21` — 4317, 4318, 9464, 13133, 1777 | `:86-102` — same | `:44-…` — same | `:4-…` — same |
| prometheus | `prom/prometheus:latest` | `:24-41` — 9090, 200 h retention, remote-write receiver on | `:104-121` | `:63-…` | `:23-…` |
| loki | `grafana/loki:latest` | `:44-54` — 3100 | `:123-133` | `:83-…` | `:43-…` |
| grafana | `grafana/grafana:latest` | `:57-76` — **`127.0.0.1:3000:3000`**, `admin/admin` | `:135-155` — same | `:96-…` — **`127.0.0.1:3001:3000`** | `:56-…` — `127.0.0.1:3000:3000` |
| tempo | `grafana/tempo:latest` | `:79-91` — 3200, 14250, 14268 | `:157-169` | `:119-…` | `:79-…` |
| weaviate | `semitechnologies/weaviate:latest` | — | `:172-192` | `:135-…` | `:95-…` |
| **api** | `${API_ECR_IMAGE}` | — | — | **`poc:172-199`** | — |
| **dashboard** | `${DASHBOARD_ECR_IMAGE}` | — | — | **`poc:202-222`** | — |

Grafana is `GF_SECURITY_ADMIN_USER=admin` / `GF_SECURITY_ADMIN_PASSWORD=admin` in all four
(`observe-docker-compose.yml:64-65` and the equivalents). The port comments in every file record
the deliberate `127.0.0.1` binding for admin UIs.

**`deployment/docker-compose.yml` and `deployment/demo/docker-compose.yml` contain no `api` and no
`dashboard` service** — they are infra-only stacks. `deployment/poc/docker-compose.yml` is the only
compose file that runs the application containers.

**OTEL_* / LOG_* env handed to application containers:**

| Container | Variable | Value | Where |
|---|---|---|---|
| poc `api` | `OTEL_ENDPOINT` | `http://otel-collector:4317` | `poc/docker-compose.yml:178` |
| poc `dashboard` | `OTEL_EXPORTER_OTLP_ENDPOINT` | `${OTEL_CROSS_ORIGIN}:4318/v1/traces` | `poc/docker-compose.yml:213` |
| poc `dashboard` | `ENV`, `APP_VERSION`, `API_PREFIX`, `MRO_PREFIX`, `CORE_PREFIX`, `COGNITO_REGION`, `COMPANY` | literals | `poc/docker-compose.yml:206-212` |
| poc collector | `OTEL_CORS_ORIGIN_1` / `_2` | `http://localhost:3001` / `${OTEL_CROSS_ORIGIN}` | `poc/docker-compose.yml:57-58` |
| local collector | `OTEL_CORS_ORIGIN_1` / `_2` | `http://localhost:3001` / `http://127.0.0.1:3001` | `deployment/docker-compose.yml:100-101` |
| demo & observability-local collector | `OTEL_CORS_ORIGIN_1` / `_2` | `http://localhost:3001` / `https://demo.app.flynapse.ai` | `demo/docker-compose.yml:17-18`, `observe-docker-compose.yml:19-20` |

**`OTEL_CROSS_ORIGIN` is set by the setup/restart scripts** to `http://<EC2 public IP>`:
`iac/poc_ec2_setup.sh:172` (from IMDSv2 at `:169`) and
`copilot-mro/deployment/poc/restart-services.sh:23` (hardcoded to `172.24.240.21` at `:21`, with
the IMDS lookup commented out at `:19-20`). Both write it into `deployment/poc/.env`
(`poc_ec2_setup.sh:193`, `restart-services.sh:37-41`).
So **the POC is the one deployment where browser OTel actually works**: the dashboard's exporter
URL points at `http://<public-ip>:4318/v1/traces` and the collector's CORS allowlist names the
same origin. The demo stack's collector allows `https://demo.app.flynapse.ai` but the demo compose
runs no dashboard container, so there is no place that sets the browser's exporter URL to match.

**`api` Dockerfile env** (`api/Dockerfile`): `LOG_LEVEL` from `ARG LOG_LEVEL=INFO` (`:37,:67`),
`LOG_DIR="/tmp/logs"` (`:68`), `OUTPUT_DIR="/tmp/outputs"` (`:66`), **`OTEL_SERVICE_NAME="copilots"`**
(`:88`) — the single line the whole dashboard/analytics `{service_name="copilots"}` selector rests
on (audit G12). `api/Dockerfile.local` sets the same three (`:73-74`, `:85`).
**Neither Dockerfile sets `OTEL_ENDPOINT`, `OTEL_ENABLED` or `LOKI_BASE_URL`.**
`api/compose.yaml:9` and `api/compose.local.yaml:9` pass only `LOG_LEVEL` as a build arg; both take
the rest from a `./.env` that is not in the repo.

**`LOKI_BASE_URL` is set by no deployment artifact in the workspace.** A repo-wide grep finds it in
exactly two places: `core/core/config.py:73` (the default `http://localhost:3100`) and
`core/README.md:88`. It is absent from every compose file, every Dockerfile, `apprunner.tf`,
`lambda.tf`, `amplify.tf`, `secrets.tf`, `variables.tf` and both EC2 setup scripts. Unless an
operator hand-edited a deployment `.env`, `core` resolves Loki to **its own container's
`localhost:3100`** in POC, in demo and on App Runner — and the customer-facing analytics page
answers 500 on every panel there (§2.3 failure path). This is a deployment-side sibling to
audit **G11**, and it is worth verifying live before the rebuild assumes the panels work.

**Collector pipeline config** (`observability-local/otel-collector-config.yaml`, shared by all four
stacks via a volume mount): OTLP gRPC `0.0.0.0:4317` + HTTP `0.0.0.0:4318` with CORS from the two
`OTEL_CORS_ORIGIN_*` env vars (`:3-15`); traces → `otlp/traces` to `tempo:4317` (`:52-55`);
metrics split into `metrics/llm` (regexp `llm_.*`, plus a `service_type=llm` resource attribute) and
`metrics/default`, both → the `prometheus` exporter on `0.0.0.0:9464` (`:27-49`, `:85-94`);
logs → `otlphttp/logs` at `http://loki:3100/otlp` (`:58-59`). `service.telemetry.logs.level: debug`
(`:74-76`) and a `debug` exporter with `verbosity: detailed` on **all four pipelines**
(`:82,88,94,100`) — audit **G17**.

`prometheus.yml` scrapes only `localhost:9090` (itself) and `otel-collector:9464` (`:9-18`) —
it does **not** scrape the api's `/metrics`, confirming audit G3. No `rule_files` (`:5-7`), so no
alerting rules.

Grafana datasources (`grafana/provisioning/datasources/datasources.yml`): Prometheus
`http://prometheus:9090` (default, uid `prometheus`), Loki `http://loki:3100` (uid `loki`), Tempo
`http://tempo:3200` with `serviceMap`/`spanMetrics` pointed at the Prometheus uid.
**No Postgres datasource** — so the `llm_usage` / `llm_model_calls` ledgers are unreachable from
Grafana (audit G8).

### 3.2 Terraform (`iac/*.tf`)

| Item | Ground truth |
|---|---|
| Observability host | `aws_instance.weaviate_observability` — **`t2.large`**, AL2023, 30 GB gp3 root + a 10 GB gp3 data volume, in a **public** subnet ("to avoid NAT Gateway costs", `ec2.tf:5`), user-data = `demo_ec2_setup.sh` (`ec2.tf:2-36`, `:67-86`) |
| What runs on it | `demo_ec2_setup.sh:92-93` → `deployment/demo/docker-compose.yml up -d` = collector + Prometheus + Loki + Grafana + Tempo + Weaviate + Portainer (`:18`), all data under `/opt/persistent-data/observability-data/{prometheus,loki,grafana,tempo}` (`:43-46`, `chmod -R 777` at `:49`) |
| Security group | `ec2.tf:96-115` — two dynamic ingress blocks opening **22, 8080, 50051, 7777, 3000, 9090, 3100, 3200, 4317, 4318, 9464, 13133, 1777, 14250, 14268, 8000, 9443**, first from `var.allowed_ssh_ip`, second from the App Runner and Lambda SGs. Grafana (3000), Prometheus (9090), Loki (3100), Tempo (3200) and the collector's pprof (1777) are all reachable from `allowed_ssh_ip` on a public-subnet instance |
| App Runner | `apprunner.tf:31-101`. `OTEL_ENDPOINT = "http://<ec2 private ip>:4317"` (`:42`). No `LOKI_BASE_URL`, no `OTEL_ENABLED`, no `OTEL_SERVICE_NAME` (the image's `copilots` stands), no `LOG_LEVEL`. **No `observability_configuration_arn`** ⇒ App Runner X-Ray tracing is off |
| Lambda | `lambda.tf:105-112` — `OTEL_ENDPOINT = "http://<ec2 private ip>:4317"`, `WEAVIATE_URL`, `AZURE_OPENAI_API_KEY`. No `tracing_config` (X-Ray off), no `logging_config`, no `aws_cloudwatch_log_group` (so the log group is auto-created with **never-expire** retention) |
| Amplify | `amplify.tf:53-118`. `platform = "WEB_COMPUTE"`; an IAM role + policy granting `logs:CreateLogGroup/CreateLogStream/DescribeLogGroups/PutLogEvents` on `Resource="*"` (`:9-50`) wired as `iam_service_role_arn` (`:60`) — this is the **only CloudWatch wiring in the estate**, and it only enables Amplify's own compute logs. `environment_variables` (`:68-90`) sets `ENV`, `APP_VERSION`, `API_BASE_URL`, `API_PREFIX`, `MRO_PREFIX`, `CORE_PREFIX`, `OPTIMIZER_PREFIX`, the five `COGNITO_*`, `COMPANY`, `DOMAIN_SIGNUP_ENABLED`. **No `OTEL_EXPORTER_OTLP_ENDPOINT`** (audit G2 confirmed), no `TURNSTILE_SITE_KEY`, no `DISPLAY_TIMEZONE`, no `DEMO_MODE`. `aws_amplify_branch.main` (`:119-131`) sets no `environment_variables` of its own |
| Amplify runtime-env gap | Even the vars Terraform does set only reach the SSR runtime if `amplify.yml:10` greps them into `.env.production`. `OPTIMIZER_PREFIX` and `DOMAIN_SIGNUP_ENABLED` are set in Terraform but match neither `grep` pattern, so they fall back to their code defaults (`/optimizer/v1`, `'false'`) — which happen to be the same values today. A future divergence would be silent |
| POC EC2 | `ec2_poc.tf` — `t2.large` (`:78`), user-data `poc_ec2_setup.sh` (`:98`). SG `poc_replica` (`:163-203`): 22 from `allowed_ssh_ip`; **80, 443, 8000 and 4318 from `0.0.0.0/0`** (`:182-190`) — 4318 is open to the world precisely so the browser can post OTLP to the collector. Grafana/Prometheus/Loki/Tempo ports are **not** exposed on the POC box |
| WAF | `waf.tf` — rate-limit + three AWS managed rule groups, each with `cloudwatch_metrics_enabled = true` and `sampled_requests_enabled = true` (`:83-86`, `:103-106`, `:123-126`, `:143-146`, `:156-159`). **No `aws_wafv2_web_acl_logging_configuration`** — no request logs, only the metric counters. `waf.tf:150` notes association with Amplify is done through the Amplify UI, not Terraform |
| **CloudWatch resources** | `rg 'resource "aws_cloudwatch' iac/*.tf` → **NONE**. No log groups, no metric filters, no alarms, no dashboards, no Log Insights queries |
| **X-Ray / ADOT** | `rg -i 'xray\|x-ray\|tracing_config\|observability_configuration' iac/*.tf` → **NONE** |
| **Alerting** | No SNS topic, no Alertmanager, no Grafana alert rules anywhere (`rule_files` commented out in `prometheus.yml:5-7`) |

The only telemetry AWS itself collects today: App Runner / Lambda / Amplify default service logs
(never-expiring, unqueried), and the WAF rule counters. Nothing reads either.

### 3.3 Environments in practice

| Environment | How it is stood up | App containers | Observability backend | Browser OTel | Loki reachable by `core`? |
|---|---|---|---|---|---|
| **Local dev (infra only)** | `copilot-mro/deployment/docker-compose.yml` + api run from source or `api/compose.local.yaml` | api on the host or `flynapse-api:local` | collector/Prom/Loki/Grafana/Tempo on `copilot-network`; Grafana `127.0.0.1:3000` | yes — `runtime-config.ts:90-93` default `http://localhost:4318/v1/traces` matches the published collector port, and the collector's CORS allowlist `http://localhost:3001` matches the dev server, which `dashboard/package.json:7` runs as `next dev -p 3001` | only if the api runs on the host (`localhost:3100` is published); **not** from inside a container |
| **Observability-only local** | `observability-local/observe-docker-compose.yml` on its own `observability` bridge network | none | same five | n/a | n/a |
| **POC EC2** (`iac/ec2_poc.tf` → `poc_ec2_setup.sh` → `deployment/poc/docker-compose.yml`, restarted by `deployment/poc/restart-services.sh`) | api + dashboard from ECR | full OSS stack on the same box; Grafana on `127.0.0.1:3001` (SSH-tunnel only); collector 4318 open to `0.0.0.0/0` | **yes — the only working one.** `OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_CROSS_ORIGIN}:4318/v1/traces` + matching collector CORS | **no** — no `LOKI_BASE_URL` in the generated `.env`; `core` would call its own container's `localhost:3100` |
| **Demo EC2** (`iac/ec2.tf` → `demo_ec2_setup.sh` → `deployment/demo/docker-compose.yml`, restarted by `deployment/demo/restart-services.sh`, kept up by `weaviate-observability.service`) | **none** — Weaviate + observability only | full OSS stack; Grafana `127.0.0.1:3000`; ports 3000/9090/3100/3200/4317/4318 open to `allowed_ssh_ip` and to the App Runner/Lambda SGs | collector CORS allows `https://demo.app.flynapse.ai`, but nothing sets the browser exporter URL for that origin ⇒ dead | this is the box App Runner's `OTEL_ENDPOINT` points at, and its 3100 is open to the App Runner SG — but `core` never learns the address |
| **AWS dev** (`iac/apprunner.tf` + `amplify.tf` + `lambda.tf`) | api on **App Runner**, dashboard on **Amplify WEB_COMPUTE**, pdf-processor on **Lambda** | logs/metrics/traces → `OTEL_ENDPOINT` = the demo EC2's private IP:4317; nothing in CloudWatch beyond default service logs | **no** (audit G2 — no env var, no rewrite, no proxy route, private-IP collector) | **no** — `LOKI_BASE_URL` unset ⇒ the settings dashboard's Loki queries fail |
| **`docs/production-architecture.md`** | ECS-on-EC2 with a dedicated observability instance pool + shared 500 GB gp3 | — | — | — | not implemented anywhere in `iac/` |

Two facts the rebuild has to design around:

1. **The single `t2.large` `weaviate_observability` box is a shared, public-subnet host running
   Weaviate *and* Prometheus *and* Loki *and* Tempo *and* Grafana *and* Portainer**, with 10 GB of
   data volume, `chmod 777`, `admin/admin` Grafana, and 17 ports open. It is simultaneously the
   vector store for the RAG product and the whole telemetry backend for App Runner and Lambda.
2. **The application already reads its collector address from one env var per runtime**
   (`OTEL_ENDPOINT` for Python via `utils.config`, `OTEL_EXPORTER_OTLP_ENDPOINT` for the browser),
   which is exactly the seam Constraint 3 needs — except that `core`'s product analytics bypasses
   it entirely by talking LogQL to Loki directly (`LOKI_BASE_URL`), and that is the one dependency
   that cannot survive a backend swap.

---

## PART 4 — AUDIT CROSS-CHECK AND NEW FINDINGS

### 4.1 Audit gaps re-verified

| Gap | Verdict |
|---|---|
| **G1** frontend telemetry collected then discarded | **HOLDS.** Both `fetch` calls commented out (`logger.ts:233-242`, `:257-266`) with the `LogDeliveryError` NOTE intact. 24 named event types + 32 `custom_metric` names + ~100 free-text call sites all terminate in an in-memory array |
| **G2** browser OTel exports to localhost in prod | **HOLDS, with a correction.** `otel.ts:37`'s `'/otlp/v1/traces'` fallback is **unreachable** — `runtime-config.ts:90-93` always supplies `http://localhost:4318/v1/traces`, and `PUBLIC_RUNTIME_KEYS:155` ships it to the browser. Confirmed absent from `amplify.tf:68-90` **and** `amplify.yml:10`; no `rewrites` in `next.config.mjs`; no telemetry route under `app/api/`. But it **does work on POC** (`poc/docker-compose.yml:213` + `poc_ec2_setup.sh:172` + `ec2_poc.tf:183` opening 4318 to the world) |
| **G10** tenant filter after the Loki fetch | **HOLDS.** `limit=5000`, `direction="forward"`, no tenant selector (`chat_quality_service.py:838-844`); six aggregators drop rows in Python; the truncation warning at `:884-888` never reaches the UI, which shows only `'Failed to load chat quality data.'` |
| **G11** Loki is a hard runtime dependency of a product feature | **HOLDS AND IS WORSE THAN STATED** — see 4.2 |
| **G12** service-label fragmentation | **HOLDS.** All ten LogQL queries hardcode `{service_name="copilots"}` (`chat_quality_service.py:58-95`); the label's only source is `api/Dockerfile:88` |
| **§5** panel #4 fields fetched but never rendered | **CONFIRMED.** `estimated_cost`, `distinct_messages`, `total_llm_calls` appear only at `lib/api/analytics-api.ts:70-72` and at no render site |
| **§5** "every failure collapses to one string" | **CONFIRMED** at `page.tsx:405-419` |
| **§6** deployment reality | **CONFIRMED**, plus the specifics in 3.2/3.3 |

### 4.2 New findings not in the audit

1. **`LOKI_BASE_URL` is set by no deployment artifact.** Absent from all four compose files, both
   `api` Dockerfiles, `apprunner.tf`, `lambda.tf`, `amplify.tf`, `variables.tf`, `secrets.tf` and
   both EC2 setup scripts; the only occurrences workspace-wide are `core/core/config.py:73` and
   `core/README.md:88`. Every containerised deployment therefore resolves Loki to its own
   container's `localhost:3100`. If that holds live, the settings dashboard is 500-ing on **every**
   panel in POC, demo and AWS dev — not just the two panels the audit calls dead. **Verify against
   the live POC `.env` before designing on top of it.**
2. **`page_view` cannot answer "documents opened" even with delivery restored.** Three independent
   defects: `cleanRoute` (`logger.ts:65-75`) strips the id from `route` for `/mro/document/*` only;
   `pageId` keeps the id but the LogQL regex (`chat_quality_service.py:74`) matches only
   `^/(mro|pilot)/document/.*`, excluding **crew** entirely; and `generatePageId`
   (`page-tracking.ts:34-37,172`) always passes an empty `URLSearchParams`, so the chat/page context
   is dropped. A document-open fact should be minted explicitly (candidate sites listed in §1.6).
3. **No sampling and no queue bound.** `shouldSample()` returns `true` unconditionally
   (`logger.ts:97-99`), `info` events are exempt from the 15 s dedupe (`:330`), `user_interaction`
   fires on every click and `window_resize` on every resize event with no throttle
   (`page-tracking.ts:319-327`). Restoring delivery as-is would put a continuous POST stream on the
   ingest route. Whatever replaces this needs sampling, throttling and a bounded queue before the
   `fetch` calls come back.
4. **`X-Session-ID` already correlates browser to backend and the telemetry layer does not use it.**
   `lib/api/utils.ts:100-107,188-192` mints `session_<ts>_<rand>` and sends it on every API call;
   `api/flynapse_api/middleware/logging.py` binds `session_id` on every backend log line. The
   frontend `LogEvent` carries no session id at all — the two halves of a session are already
   joinable and nothing joins them.
5. **`traceId`/`spanId` are declared on both sides and never populated.** `LogEvent` has them
   (`logger.ts:19-20`, `logging_endpoints.py:118-119`) and the ingest handler forwards them
   (`:249-250`), but no emitter ever sets them, and browser OTel (`otel.ts`) shares no context with
   the logger. The FE log ↔ FE trace ↔ BE trace chain is broken at every link.
6. **The client's `ts` is discarded twice.** The ingest handler never forwards it
   (`logging_endpoints.py:242-256`) and the OTLP sink re-stamps `log_record.created` with
   `time.time()` plus jitter (`utils/utils/logging_config.py:194-204`). Event time in Loki is
   server-receive time, up to `FLUSH_MS = 5000` late plus batch delay.
7. **`setUserId()` is dead code** (`logger.ts:361-363`) — written, exported, never read.
8. **Four of ten analytics panels are duplicate Loki scans** (`chat_quality_service.py:698-704`,
   `:718-724`), fetched and cached under separate keys.
9. **`estimated_cost` is a single hardcoded price pair** ($1.25/$10 per 1M,
   `chat_quality_service.py:566-570`) applied to every model — and it is not even rendered.
10. **No WAF logging configuration** (`waf.tf` has metrics only), **no Lambda `tracing_config`**,
    **no App Runner `observability_configuration`**, **no `aws_cloudwatch_*` resource anywhere**.
    The only CloudWatch wiring in the estate is the Amplify compute-log IAM policy
    (`amplify.tf:27-50`).
11. **Every observability image is `:latest`** in all four compose files — the POC promise of "a
    reproducible OSS stack on one box" is not reproducible today.
12. **Amplify's runtime-env allowlist is a second, undocumented gate.** `amplify.yml:10` decides
    what reaches the SSR runtime, independently of what `amplify.tf` sets. `OPTIMIZER_PREFIX` and
    `DOMAIN_SIGNUP_ENABLED` are set in Terraform and silently do not reach the runtime; they work
    only because their code defaults coincide. Any new telemetry env var must be added in **both**
    places (or be `NEXT_PUBLIC_`-prefixed, which `amplify.yml:11` greps wholesale).
