# Observability rebuild — Phase 9: dashboard telemetry completion

**Status:** OPENED 2026-09-11. Plan v1 by the session lead (Opus 5); an independent Opus 5 plan review runs
before any build (owner instruction). Build + Opus adversarial review = Phase A; the Fable gate (design + code) =
Phase B when the Fable limit returns — **no merge before that gate** (the phase-8 rule). Master plan:
`docs/plans/observability-rebuild.md` §11c (this phase) and §15 (ledger).

**Owner request (2026-09-11),** after the audit answer to "is the dashboard repo complete from a metrics,
tracing, and logging perspective?" (no — the pipeline is sound, the gaps below remain): "please create a plan to
address these. Add it as another phase. Get this plan reviewed by another agent, and then let's implement. only
thing to skip is the rostering bit. that is just for demo right now. All the work will eventually be reviewed by
Fable as well, both the design and the implementation, once limits are back."

**Owner rulings (this phase):**
1. Every gap in the 2026-09-11 dashboard audit is addressed — built, or dispositioned with a reason in §0 —
   except **Rostering** (a demo prototype: no network calls, a stub payroll export). Rostering gets no events, no
   export event, and keeps its console calls behind a lint override.
2. The plan is reviewed by an independent agent before implementation starts.
3. Fable reviews the design (chunk R6) and every stream's code (R7–R10) when its limit returns; merges wait for it.

**Goal.** Close the distance between the phase-4 browser stack as merged (dashboard `agent_sdk` @ `b87ced0`) and a
complete tracing/logging/metrics story: no URL query, token or email leaves the browser; every user-visible failure
carries a support reference that opens its trace; the first requests of a page load are traced; the Next.js server
hop is correlated and structured; every product area outside Rostering emits a catalogued signal or is
dispositioned as covered by a generic one; both dashboard dialects chart the new signals — proven by a live probe
that also retires the frontend board's DARK labels.

**Audit inputs.** Two read-only audits at `agent_sdk` `b87ced0` (plumbing: tracing, logging, metrics; coverage: the
25-event catalogue against research 07's areas), top claims spot-verified by the session lead on 2026-09-11. Their
findings are the gap register (§0); every file:line below is at `b87ced0`.

**Spec sections:** §3.3 (signals), §3.4 (browser via the gateway; SSR deferral), §7.4 (frontend rebuild and
catalogue discipline), §8 (hygiene), §9.2–§9.4 (boards, alerts, `aws`).

**Inherited constraints (master §1, §11a, §12; phase-8 practice):** branch from the current mainlines
(`dashboard` = `agent_sdk`, `api`/`copilot-mro` = `langgraph-merge`, `iac` = `main`); nothing in the migration
conflict zone (this phase needs none of it); commits on this phase's own worktree branches by pathspec
(`git commit -- <paths>`), never `git add -A` — the branches carry no owner WIP, which is why production edits are
committed there, as in phase 8; no credentials in output, commits or screenshots; no user content in any log body,
log attribute or span attribute; the browser never sees a collector URL; plan files carry no code; Terraform
validated, never applied; nothing pushed. Phase-9 specific: **no new npm or Python dependency** (a stream that needs
one stops and reports); dashboard worktrees symlink `node_modules` to the main checkout's; **every `logger` message
is a constant string** (F9 adds the guard; E9 and N9 obey it from the start); ≤5 agents at once (owner cap this
session); every agent is reported as `name — model`; all Phase-A agents are Opus 5.

---

## 0. Gap register (audit 2026-09-11 → task or disposition)

| ID | Gap (evidence at `b87ced0`) | Disposition |
|---|---|---|
| G9-01 | Document-load, document-fetch and resource-fetch spans carry the full page/resource URL with query and fragment: `lib/telemetry/provider.ts:241` builds `DocumentLoadInstrumentation` with no config and the library writes `location.href` / `resource.name`; these INTERNAL spans are never ratio-dropped and the collector keeps `url.*` — invite/registration tokens (`?invite=`, `?token=`), `chatUserId`, presigned S3 queries reach Tempo/X-Ray | F9.1 |
| G9-02 | Log bodies are not scrubbed: `lib/api/settings-api.ts:595` ships an email in a production warn body; five more warn bodies interpolate ids or tenant-authored names (`:545`, `:1022`, `:1514`, `:1802`, `:1832`) | F9.2 |
| G9-03 | The collector's `redaction` processor masks attribute values only; log bodies pass every pipeline untouched | M9.1 |
| G9-04 | `X-Request-ID` and `X-Trace-Id` are missing from the api's CORS `expose_headers` (`api/flynapse_api/middleware/cors.py`), so the browser span's `request_id` attribute (`provider.ts:74-79,165-176`) is never set | F9.4 |
| G9-05 | No support reference anywhere in the UI (`lib/api/error-handler.ts` toast, `lib/telemetry/ErrorBoundary.tsx`, `components/shared/FeatureErrorFallback.tsx`) | F9.4 |
| G9-06 | The api mints its own request id and ignores an inbound `X-Request-ID` (`api/flynapse_api/middleware/request_id.py:36-41`) | disposition: by design (D9-5) |
| G9-07 | No `app/global-error.tsx`: root-layout and provider-level errors go unreported | F9.6 |
| G9-08 | Telemetry and the global error handlers start in the outermost provider's `useEffect` (`components/providers/TelemetryProvider.tsx:24`), which React runs after every descendant's effects — the first auth/bootstrap requests and errors look untraced (inferred; F9.5's first test proves or disproves it) | F9.5 |
| G9-09 | `'API error:'` records collapse: the logger dedupes on `level:msg` for 15 s and the record carries no `url.template` or status (`lib/telemetry/logger.ts:78-83`, `lib/api/error-handler.ts:165`) | F9.3 |
| G9-10 | The 43 `suppressGlobalError: true` queries/mutations log nothing | disposition D9-9, plus M9.3 (their failures are always-kept ERROR fetch spans, charted by endpoint and status) |
| G9-11 | Chat attachment uploads run before `turn.runInContext` (`hooks/chat/useMroMessageStream.ts:285,313,348`; pilot/crew equivalents): unlinked root spans, 90% dropped, no attachment time on the turn | F9.7 |
| G9-12 | No `no-console` rule (`.eslintrc.json`), so the five `eslint-disable no-console` comments are inert; 15 raw `console.*` calls in 9 files (4 in Rostering) | F9.2 (Rostering exempt), N9.5 (the one under `app/api/`) |
| G9-13 | `.env.example:11` still sets `OTEL_EXPORTER_OTLP_ENDPOINT`, outside the legacy guard's roots | F9.8 |
| G9-14 | Dead hand-rolled traceparent generator, `lib/api/utils.ts:51-86` | F9.8 |
| G9-15 | `lib/api/client.ts:186,226` `logger.info` lines carry full request URLs (phase-4 Future Improvement, "when next touched") | F9.3 |
| G9-16 | The 12 Next.js route handlers log to the console only and forward `X-Session-ID` but not `traceparent`; there is no `instrumentation.ts` / `onRequestError` | N9.1–N9.4 |
| G9-17 | `app/api/document-hub/documents/[id]/content-stream/route.ts:80-84,108-112` log raw upstream bodies (the api's detail; S3 XML naming buckets and keys) | N9.5 |
| G9-18 | SSR spans and logs are not exported over OTLP | disposition: deferred by spec §3.4 to the Amplify private-reachability probe; N9 builds the seam (§9) |
| G9-19 | `browser.settings.mutation` (#19) misses invitations, operators, operator grants, the operator registry, organization, `deleteDepartment` (`settings-api.ts:1728`), `deleteOperator` (`:1359`) | E9.4 |
| G9-20 | AD review emits nothing (`hooks/mro/useAdReview.ts`) | E9.3 |
| G9-21 | Optimizer: 22 mutations with no telemetry (`hooks/api/useOptimizer.ts`), including solve and export | E9.2 |
| G9-22 | LATER rows #16, #18, #22, #23, #24 are unbuilt and tracked only in the phase-4 appendix | E9.2, E9.3, E9.6, E9.8 (roster export excluded) |
| G9-23 | Areas with no specific event: automations CRUD, comments, improvement, notifications, chat share, Document Hub metadata/sharing/retry/delete, data-discovery sources and jobs, the four non-login auth pages | E9.5, E9.7; the rest dispositioned in §2.3 |
| G9-24 | `aws`: no browser metric filters or alarms | M9.5 (a gated-off seam, D9-11) |
| G9-25 | Grafana `fn-frontend` panels 1–6, the four Loki browser rules and the CloudWatch frontend widgets still say DARK, pending the POC acceptance run | P9, then M9.6 |
| G9-26 | Browser API latency has no per-endpoint dimension (Tempo `span_metrics` dimensions are db/peer/server/rpc only) | M9.3 |
| G9-27 | No collector test exercises the browser allow-list or body masking end to end | M9.2 |
| G9-28 | Rostering: no network calls, payroll export is a `setTimeout` stub, 4 console calls | EXCLUDED (owner ruling 1) |
| G9-29 | 8 `window.open` and 4 `<iframe>` loads are untraced | disposition: top-level navigations cannot carry `traceparent`; the same-origin ones land on a Next route that mints a trace (N9.1); iframes load S3 directly — resource timing only, URL scrubbed by F9.1 |
| G9-30 | Raw `fetch(` calls that bypass `fetchWithAuth` (no `X-Session-ID`) | Future Improvement (§9): not a ranked gap, and it changes the auth transport |
| G9-31 | `browser.telemetry.dropped` ships but is not in the catalogue | listed in §2.1; E9.1 pins it in the catalogue test |
| G9-32 | Stale items #7 (`/loginwithsso`) and #13 (`chart-card-visual-test`) | kept by earlier owner rulings — no action |

## 1. Streams, worktrees, waves

| Stream | Scope | Worktree → branch (base) | Depends on | Wave |
|---|---|---|---|---|
| **F9 — browser correctness + correlation** | URL scrub at the exporter, log-body hygiene + guards, API-error records, support references (+ api CORS), first-load start, global error page, chat attachments inside the turn, hygiene leftovers | `/home/aditya/Code/dashboard-obs9` → `obs9-browser` (off `agent_sdk` `b87ced0`); `/home/aditya/Code/api-obs9` → `obs9-api` (off `langgraph-merge` `a19a931`) | nothing | 1 |
| **E9 — event coverage** | the §2 catalogue additions at their choke points | `/home/aditya/Code/dashboard-obs9e` → `obs9-events` (off `agent_sdk` `b87ced0`) | the §2 pins | 1 |
| **N9 — Next.js server side** | request context + trace forwarding, structured server log lines, `instrumentation.ts`, upstream-body hygiene | `/home/aditya/Code/dashboard-obs9n` → `obs9-server` (off `agent_sdk` `b87ced0`) | nothing | 1 |
| **M9 — collector, boards, alarms** | allow-list + body masking in every profile, Tempo dimensions, `fn-frontend` panels in both dialects, the gated aws browser alarms, catalogue and runbook text | `/home/aditya/Code/copilot-mro-obs9` → `obs9-deploy` (off `langgraph-merge` `bc0e3858`; `deployment/**`, `tests/integration/otel/**`, `docs/runbooks/observability/**` only); `/home/aditya/Code/iac-obs9` → `obs9-iac` (off `main` `5996e5a`) | the §2 pins | 1 |
| **P9 — live probe + DARK flip** | one probe over all four streams; then the DARK labels come off what it saw | throwaway `/home/aditya/Code/dashboard-obs9-probe` → `obs9-probe` (the three dashboard branches merged locally, never merged anywhere) + the other obs9 trees | F9, E9, N9, M9 reviewed | 2 |

The four build streams start together (four implementers); each stream's reviewer starts when its implementer
finishes (≤5 agents at once). Reviewer = a fresh Opus 5 agent per stream, briefed with that stream's section + §0 +
§2 + the diff, running the suites itself; triage by the session lead (real gap → fix pass by the same implementer →
re-verification by the same reviewer; intentional → §9); the reviewer writes the stream's brief into §10.

### 1a. Progress
- [ ] Plan v1 (this file) + master §11c
- [ ] Independent plan review (Opus 5) → triage → plan v2
- [ ] F9 — built, reviewed, fixed, re-verified
- [ ] E9 — built, reviewed, fixed, re-verified
- [ ] N9 — built, reviewed, fixed, re-verified
- [ ] M9 — built, reviewed, fixed, re-verified
- [ ] P9 — live probe on the integration tree; DARK flip (M9.6)
- [ ] Phase A closed — §8b gate agenda with branch tips
- [ ] Fable R6 (design) → R7 F9 → R8 E9 → R9 N9 → R10 M9, merge after each

### 1b. Files more than one dashboard stream touches (each stream owns one hunk)

| File | F9 owns | E9 owns | N9 owns |
|---|---|---|---|
| `lib/telemetry/events.ts` | `emitLog` (body scrub) and `emitRecord`'s optional trace-context parameter | new names, allow-lists, emitters, timing wrappers | — |
| `lib/telemetry/logger.ts` | `ship` (dedupe key, trace linkage) | — | the server branch of `log` (one call into the new server log module) |
| `lib/telemetry/errors.ts` | all of it | — | — |
| `lib/api/settings-api.ts` | the six warn sites (G9-02) | the two unwrapped deletes and any new wraps | — |
| `lib/api/utils.ts`, `lib/api/fetch-utils.ts`, `lib/api/error-handler.ts`, `lib/api/client.ts` | all of them | — | — |
| `.eslintrc.json` | all of it | — | — |
| `app/api/**` | — | — | all of it (including `documents/[id]/route.ts:269`) |
| `hooks/chat/**` | all except `useShare.ts` | `useShare.ts` | — |

Gate merge order: F9 → E9 → N9, each `--no-ff` into `agent_sdk`; conflicts are expected only at the boundaries above,
and the full unit lane + `tsc` re-run after each merge. A stream that finds it must edit another stream's hunk stops
and reports instead.

### 1c. Test environments
- **Dashboard (all three trees):** `npm run test:unit` scoped to the stream's test files while building, the full unit
  lane before review; `npm run typecheck`; `npx eslint` on every touched file. Tests use the phase-4 harnesses
  (`tests/fixtures/telemetry-harness`, `tests/fixtures/dom-harness`) and the two-level layout
  (`tests/unit/<domain>/…`). WSL rule: assert booleans, never hold jsdom nodes in assertion messages.
- **api-obs9:** the `wt-obs-u` bundle env with `PYTHONPATH` pinned to `api-obs9` and the main `utils` checkout (the
  phase-8 stream-S recipe), `DEBUG=false`.
- **copilot-mro-obs9:** the `tests/integration/otel/` lane from the shared api env with the worktree as rootdir —
  static guards always, `OTEL_COMPOSE_SMOKE=1` for M9.2's real-container smoke, `OTEL_RULES_CHECK=1` for rules.
- **iac-obs9:** `terraform fmt -check` + `terraform validate`; every `dashboards/*.json.tftpl` body parses after
  substitution (the phase-6 check).

## 2. Pinned catalogue additions (E9 builds them; M9 allow-lists and charts them in parallel)

### 2.1 New and extended signals

Signal: **L** = OTel log record through the existing `emitRecord` envelope; **S** = span. Every new row is 100%
(records are never sampled), severity INFO (failure rides in `outcome`).

| Name | Tier | Signal | Trigger / choke point | Attributes (beside the envelope) | Consumer |
|---|---|---|---|---|---|
| `browser.feature.mutation` (new) | SHOULD | L | every feature action in §2.2 — TanStack `meta.telemetry`, or a `withFeatureMutation` wrapper for direct calls | `feature`, `entity`, `action`, `outcome`, `duration_ms`, `error_type` | `fn-frontend` "Feature actions", "Feature action failure ratio" |
| `browser.auth.flow` (new) | SHOULD | L | register submit, signup-code confirm, forgot-password code request and confirm, new-password (challenge) submit, invite preview and accept | `flow`, `step`, `outcome`, `duration_ms`, `error_type` | "Auth flows" |
| `browser.automation.run_settled` (#16) | LATER → built | L | `useAutomationRuns` first observes a terminal status for a run this session triggered | `automation_id`, `run_id`, `terminal_status`, `observed_wait_ms` | "Long-running flows: observed wait p75" |
| `browser.discovery.job_settled` (#18) | LATER → built | L | the discovery poll where in-progress first turns false for a job this page polled | `job_kind`, `job_id`, `terminal_status`, `observed_wait_ms`, `poll_count` | same |
| `browser.export.requested` (#22) | LATER → built | L | optimizer run export, work-order export (roster export excluded) | `export_kind` ∈ {`optimizer_run`, `work_orders`}, `format`, `row_count_bucket`, `duration_ms`, `outcome` | "Exports" |
| `browser.optimizer.run_triggered` (#23) | LATER → built | L | preflight and run through the hooks and the wizard's direct call | `job_id`, `phase` ∈ {`preflight`, `solve`}, `outcome` ∈ {`accepted`, `rejected`}, `preflight_warning_kind`, `duration_ms`, `error_type` | "Optimizer runs triggered" |
| `browser.ad_review.disposition_set` (#24) | LATER → built | L | disposition write and clear | `disposition` ∈ {`confirmed_applicable`, `ruled_not_applicable`, `cleared`}, `had_prior_disposition`, `source` ∈ {`table`, `dialog`}, `outcome`, `duration_ms`, `error_type` | "AD dispositions" |
| `browser.settings.mutation` (extended) | SHOULD | L | new entities `invitation`, `operator`, `operator_grant`, `operator_registry`, `organization`, `department` (delete) | unchanged | existing + "Settings changes by entity" |
| `browser.chat.turn` (extended) | MUST | S | uploads run inside the turn (F9.7) | + `attachment_count`, `attachment_upload_ms` | Tempo trace view |
| `browser.error` (extended) | MUST | L | `app/global-error.tsx` (F9.6) | `error_kind` gains the value `global` (no new key) | existing error panels |
| `browser.telemetry.dropped` (catalogued) | baseline | L | the exporter's drop counter (already shipping) | unchanged | "Telemetry drops" (existing data, new panel optional) |

**Vocabulary rules.** Every attribute is an opaque id, a closed enum, a boolean, a bucket or a millisecond count.
`error_type` is an error class or exception name (`ApiError`, `TypeError`, a Cognito exception name) — never a
message. Nothing a user typed rides: no names, emails, filenames, comment text, search terms or tokens.

**Collector allow-list delta for M9:** `feature`, `flow`, `step`, `attachment_count`, `attachment_upload_ms`. Every
other key above is already in `base.yaml`'s browser list (checked 2026-09-11).

### 2.2 Coverage map (area → calls → event)

| Area | Calls | Event |
|---|---|---|
| Optimizer | the 22 mutations in `hooks/api/useOptimizer.ts` (schedules, CSV upload, process, expansion save, activities and rule preview, roles, settings, jobs, config-snapshot refresh) | `browser.feature.mutation` (`feature=optimizer`) — except `usePreflightJob`, `useRunJob` and the wizard's direct `runJob` (`components/features/optimizer/wizard/steps/ReviewStep.tsx:196`) → `browser.optimizer.run_triggered`, and `fetchRunExport` (`components/features/optimizer/outputs/CanvasHeader.tsx:183`) → `browser.export.requested` |
| AD review | `hooks/mro/useAdReview.ts`: `useAdDispositionWrite`, `useClearAdDisposition` → `browser.ad_review.disposition_set`; `useRecomputeAdApplicability`, `useMaterializeAdCorpus` → `feature=ad_review` | as named |
| Automations | `useCreateAutomation`, `useUpdateAutomation`, `useDeleteAutomation` → `feature=automations`; `useRunAutomationNow` stays `browser.automation.run_triggered`; `useAutomationRuns` → `run_settled` | as named |
| Comments | `hooks/api/useComments.ts` create / update / delete / vote | `feature=comments` |
| Improvement | `useRunImprovementNow`, `useTriageFinding` | `feature=improvement` |
| Notifications | `components/features/notifications/NotificationBell.tsx:149` bulk mark-read (a direct call) | `feature=notifications` via the direct-call wrapper |
| Chat | `hooks/chat/useShare.ts` | `feature=chat` (`entity=chat`, `action=share`) |
| Document Hub | metadata edit, sharing-scope change, retry, delete (in `DocumentHubPageContent` and its dialogs) | `feature=document_hub` |
| Data discovery | `data-discovery/page.tsx` source create and archive; `jobs/[jobId]/page.tsx` rerun, retry failed batches, archive (level-1/level-2 starts stay `browser.discovery.job_started`); the discovery polling hook → `job_settled` | `feature=data_discovery` |
| Settings (#19 completion) | invitations (`hooks/settings/useInvitations.ts`), operators and the operator registry (`useOperators.ts`), operator grants (`useOperatorGrants.ts`, `GrantOperatorDialog.tsx`), organization (`components/features/settings/organization/organizationSave.ts`), `deleteDepartment`, `deleteOperator` | `browser.settings.mutation` |
| Auth | `RegisterView`, `ConfirmationCodeView`, `ForgotPasswordView`, `NewPasswordView`, `InviteAcceptView` | `browser.auth.flow` |
| Work orders | `components/features/chat/WorkOrderCarousel.tsx:110` export | `browser.export.requested` (`export_kind=work_orders`) |

`feature` ∈ {`optimizer`, `ad_review`, `automations`, `comments`, `improvement`, `notifications`, `chat`,
`document_hub`, `data_discovery`}. `entity` is the resource noun and `action` the verb (`create`, `update`,
`delete`, `upload`, `process`, `save`, `preview`, `refresh`, `archive`, `rerun`, `retry`, `share`, `vote`,
`mark_read`, `trigger`, `triage`, `recompute`, `materialize`, `grant`, `revoke`, `resend`, `accept`), snake_case,
from one closed map in code; E9 records the final (feature, entity, action) table in §11. `flow` ∈ {`register`,
`confirm_signup`, `forgot_password`, `new_password`, `invite_accept`}; `step` ∈ {`submit`, `code_request`,
`code_confirm`, `preview`, `accept`}; auth `outcome` ∈ {`success`, `failure`, `challenge`}.

### 2.3 Areas covered by an existing signal (no new event; D9-13)

| Area | Why nothing new |
|---|---|
| Copilots landing tile choice | `browser.route.change` (`route_pattern_from=/copilots` → the chosen copilot) already records it |
| Help | route changes are the whole story (static content) |
| Analytics dashboard tabs, ranges, filters | each view fetches its panels; the fetch spans' `url.template` shows which panels are read — no panel asks for more |
| Notification bell open / click-through | open is UI state with no consumer; click-through is a route change; mark-read is a feature action (§2.2) |
| Chat UI state (filters, data view, report preview, new/past chat) | spec §7.4 drops click-level interaction; a new chat is the first turn with `is_followup=false` |
| Data-discovery table open | a route change |
| `window.open` / `<iframe>` loads | G9-29 |
| Rostering | owner ruling 1 |

## 3. Stream F9 — browser correctness + correlation

Each task: write the test first and watch it fail on `b87ced0` for the stated reason, implement, re-run, commit by
pathspec. Every task carries the master §11a logging-coverage checkbox: the touched modules' failure paths log at
the right level, with constant messages and bounded kwargs, and no silent swallow outside the telemetry modules'
own never-throw rule.

### F9.1 — No URL query or fragment leaves the browser (G9-01)
- **Files:** `lib/telemetry/exporter.ts` (the trace and log serializers are the single exit), `lib/telemetry/errors.ts`
  (`scrubMessage`), new test `tests/unit/telemetry/export-url-scrub.test.ts`.
- **Design (D9-7):** the pinned `@opentelemetry/sdk-trace-base` 2.11.0 has no `onEnding` hook (checked 2026-09-11), so
  a span cannot be rewritten by a processor after its instrumentation finishes; the exporter is the one place that
  sees every span and record from every instrumentation. Before serialization, every string attribute on spans,
  span events and log records whose value is a URL (absolute `http(s)://…` or root-relative) loses its query and
  fragment; non-URL strings are untouched. `scrubMessage` also strips the query and fragment from URLs embedded in
  free text (error messages, log bodies). The fetch/XHR hooks keep producing `url.template`.
- **Test (defect-absence, not guard-presence):** start telemetry with the REAL exporters over a fake transport (the
  `PostFn` seam), a jsdom `location.href` carrying `?invite=probe-token#frag`, a fake navigation entry and a fake
  resource entry whose URL carries an `X-Amz-Signature` query; issue one fetch to a URL with a query; flush; decode
  every posted OTLP/JSON body and sweep ALL attribute values, event attributes and log bodies — no `probe-token`, no
  `X-Amz-`, no URL-shaped value with a `?`/`#` suffix; `url.template` still present on the fetch span. It must fail
  on `b87ced0` (the document-load spans carry the query).
- **Acceptance:** the sweep passes; the existing propagation, sampling and wire-shape tests still pass.

### F9.2 — Log bodies carry no user data, and a guard keeps it that way (G9-02, G9-12)
- **Files:** `lib/telemetry/events.ts` (`emitLog` passes the body through `scrubMessage`); `lib/api/settings-api.ts`
  (the six interpolated warn sites become constant messages; the email and the tenant-authored role names are
  dropped outright, the error rides as the kwarg it already is); `.eslintrc.json` (`no-console` at error; a
  `no-restricted-syntax` rule rejecting a template literal with expressions, or a string concatenation, as the first
  argument of `logger.warn` / `logger.error` / `logger.fatal`; an override turning `no-console` off for
  `components/features/rostering/**` with ruling 1 in a comment); the non-Rostering console sites outside `app/api/`
  (`components/features/pdf-viewer/pdf-toc.tsx:172` → the logger; the debug prints at `lib/pdf/pdfjs.ts:230,261` and
  `hooks/pdf-viewer/use-pdf-navigation.ts:55` → deleted or `logger.debug`; the dev-gated sites in
  `lib/telemetry/provider.ts:150,326` and `lib/telemetry/product-events.ts:173` keep their disable comments, which now
  mean something).
- **Tests:** `tests/unit/telemetry/log-body-scrub.test.ts` (a warn whose body holds an email and a presigned URL ships
  masked); a source-sweep guard in the repo's infra test folder, because `npm run lint` lints changed files only: no
  shipped-level `logger` call under `app/`, `components/`, `hooks/`, `lib/` takes an interpolated or concatenated first
  argument (Rostering exempt by path) — it must fail on `b87ced0` (six sites) and pass after.

### F9.3 — API-error records are distinct and linked to their trace (G9-09, G9-15)
- **Files:** `lib/api/utils.ts` (`ApiError` gains optional `traceId`, `requestId`, `urlTemplate`); one shared
  "error from a failed response" helper used by every `new ApiError(` site in `lib/api/utils.ts` and the two
  `apiError(…)` sites in `lib/api/fetch-utils.ts` (`:188`, `:235`), reading `X-Trace-Id` and `X-Request-ID` off the
  response (readable once F9.4's CORS change lands; absent headers are normal) and the `url.template` of the request;
  `lib/api/error-handler.ts` (`handleApiError` logs one constant message with `url.template`,
  `http.response.status_code` and the error); `lib/telemetry/logger.ts` (`ship`: the dedupe key adds `url.template` and
  status when present; a record about an error that carries a trace id is emitted in that trace's context — through
  the optional context parameter F9 adds to `emitRecord` — so the Loki record and the Tempo trace share the id);
  `lib/api/client.ts` (drop the two URL `info` lines).
- **Tests:** two failing endpoints within 15 s ship two records; the same endpoint and status twice ships one; the
  record carries `url.template`, status and the failed response's trace id.

### F9.4 — A support reference on every user-visible failure (G9-04, G9-05)
- **api-obs9:** `flynapse_api/middleware/cors.py` adds `X-Request-ID` and `X-Trace-Id` to `expose_headers`; new test
  `tests/middleware/cors/test_cors_exposes_correlation_headers.py` — a request from an allowed origin through the
  real CORS setup function carries both names in `Access-Control-Expose-Headers`, and (through the gateway's real
  middleware order where the app factory imports cheaply, else a minimal app wired with the same setup functions) the
  two headers are present on the response.
- **dashboard:** `lib/telemetry/errors.ts` — `reportError` returns the trace id its record was emitted under: the
  active span's when valid (a failure inside a chat turn links to that turn), else a fresh random non-recording span
  context created for the record. `lib/telemetry/ErrorBoundary.tsx` and `components/shared/FeatureErrorFallback.tsx`
  show "Reference" with the id and a copy button, only while telemetry is running (the honest-copy rule).
  `lib/api/error-handler.ts` — toasts for the server, network and unknown classes carry the reference (the error's
  `traceId`) with a copy action; 4xx validation/permission toasts are unchanged. The provider's existing
  request-id read now populates `request_id` (extend `tests/unit/telemetry/provider-propagation.test.ts` with a
  response carrying `X-Request-ID`).
- **Tests:** the fallback's reference equals the exported record's trace id (fake exporter); a 500's toast carries
  the response's trace id; no reference renders when telemetry is not started.

### F9.5 — Telemetry is running before the first request (G9-08)
- **Test first:** render the provider tree (`TelemetryProvider` around a child whose mount effect issues a fetch and
  one whose mount effect throws) over the fake transport. On `b87ced0` the child's fetch should produce no span and
  the throw no `browser.error`; if both ARE captured, G9-08 is disproved — record that in §11 and skip the change.
- **Files (if proved):** a side-effect boot module under `lib/telemetry/` imported FIRST by
  `components/providers/AppProviders.tsx`: in the browser it starts the provider and installs the global error
  handlers and Web Vitals at module evaluation, idempotently; `TelemetryProvider`'s effect keeps route telemetry,
  unload/history handlers and the app-boot record, and calls start again as a no-op fallback. Verify that the runtime
  config the provider reads (`window.__RUNTIME_CONFIG__`, set by an inline script at the top of `<body>` in
  `app/layout.tsx`) and `API_CONFIG.BASE_URL` resolve at module evaluation; where they may not, boot defers to the
  effect and §11 says so.
- **Acceptance:** the test passes after the change; the idempotency and strict-mode tests still pass.

### F9.6 — A root error page that reports (G9-07)
- **Files:** `app/global-error.tsx` (its own `<html>`/`<body>`; reports through `reportError` with `error_kind=global`,
  flushes telemetry, shows the reference and a Reload button, no raw message outside development); `lib/telemetry/errors.ts`
  (`ErrorKind` gains `global`).
- **Test:** rendering the page with an Error emits one `browser.error` with `error_kind=global` and shows its reference.
  Next renders `global-error` in production builds only; P9 forces it once against `next start`.

### F9.7 — Chat attachment uploads belong to their turn (G9-11; D9-14)
- **Files:** `hooks/chat/useMroMessageStream.ts`, `usePilotMessageStream.ts`, `useCrewMessageStream.ts` (and
  `useCopilotDockChat.ts` if it uploads); `lib/telemetry/chat-turn.ts` (the handle records `attachment_count` and
  `attachment_upload_ms`).
- **Constraint:** the web SDK's default context manager does not carry context across `await`s, so each upload must run
  inside `turn.runInContext` at the call closest to its `fetch` — inside the api-client method if that method awaits
  before fetching — exactly as D8 of the phase-4 plan did for the stream call. An upload failure ends the turn with
  `outcome=error` and `error_type`.
- **Test:** a turn with one image and one file attachment exports both upload CLIENT spans as children of
  `browser.chat.turn` (same trace, parent = the turn span) and the turn carries both new attributes; a failing upload
  ends the turn as `error`. Proved through the real fetch path, not a mocked context.

### F9.8 — Hygiene leftovers (G9-13, G9-14)
- **Files:** `.env.example` (drop the stale line); `lib/api/utils.ts` (delete the dead generator);
  `tests/unit/telemetry/legacy-module-absent.test.ts` (the roots gain the repo's env example files; the forbidden list
  gains the generator's function names).

### F9 close
Full unit lane, `tsc`, eslint on touched files; implementation notes in §11; the reviewer's brief in §10.

## 4. Stream E9 — event coverage

Same task discipline as F9. Every emitter gets a SITE-level test through the real hook or method against a stubbed
transport (the `tests/unit/telemetry/settings-mutation-sites.test.ts` pattern): one success record and one failure
record with the right attributes and no off-list key.

### E9.1 — Catalogue members
- **Files:** `lib/telemetry/events.ts` (the §2.1 names, allow-lists, typed emitters, and timing wrappers for direct
  calls — `withFeatureMutation` mirrors `withSettingsMutation`; an auth-flow timer mirrors `startLoginTiming`);
  `lib/telemetry/mutation-meta.ts` (the `MutationTelemetryEvent` union gains `browser.feature.mutation`,
  `browser.optimizer.run_triggered`, `browser.ad_review.disposition_set`); `tests/unit/telemetry/events-catalogue.test.ts`
  (the name → keys table equals §2.1, `browser.telemetry.dropped` included).
- **Sweep test:** every `useMutation` in the §2.2 files carries `meta.telemetry`, or is named in the test's exemption
  list with its reason — so a new mutation cannot ship dark.

### E9.2 — Optimizer (G9-21, #22 optimizer, #23)
The 22 hooks get `meta.telemetry` with the closed (entity, action) pairs; preflight and run emit
`browser.optimizer.run_triggered` (`phase`, `job_id`, `accepted`/`rejected`, `preflight_warning_kind` from the
preflight response); the wizard's direct `runJob` call is wrapped too, so wizard runs count; the `fetchRunExport`
caller emits `browser.export.requested` (`export_kind=optimizer_run`, `format`, `row_count_bucket` when the response
says, duration, outcome).

### E9.3 — AD review (G9-20, #24)
Disposition write and clear emit `browser.ad_review.disposition_set` (`cleared` for the clear path;
`had_prior_disposition` from the row the user acted on; `source` from the calling surface — the hook takes it as a
variable, the table and the dialog pass theirs); recompute and materialize → `feature=ad_review`.

### E9.4 — Settings (#19 completion, G9-19)
Invitations (create, revoke, resend), operators (create, update, delete), operator grants (grant, revoke), the
operator registry, organization save, `deleteDepartment`, `deleteOperator` → `browser.settings.mutation` (TanStack meta
or `withSettingsMutation`, whichever the call site already uses).

### E9.5 — Other feature actions (G9-23)
Automations CRUD, comments, improvement, notifications bulk mark-read, chat share, Document Hub metadata/sharing/retry/
delete, data-discovery source create/archive and job rerun/retry/archive → `browser.feature.mutation`.

### E9.6 — Long-running settles (#16, #18)
- `browser.automation.run_settled`: only for runs this session triggered — the run-triggered path records run id and
  trigger time in a session-scoped registry; `useAutomationRuns` emits once per run on the first terminal status it
  observes; `observed_wait_ms` = observed − triggered.
- `browser.discovery.job_settled`: the discovery polling hook emits once when in-progress first turns false for a job
  this page polled (`poll_count`, `observed_wait_ms` from the first poll).
- **Tests:** a run triggered then polled to `succeeded` emits exactly one record; a run this session did not trigger
  emits none; a remount does not double-emit.

### E9.7 — Auth flows (G9-23)
`browser.auth.flow` at the five views with the §2.2 flow/step vocabulary; `error_type` is the Cognito/api exception
name; nothing user-entered (email, username, code, token) rides. The public pages ship through the public ingest
(anonymous sentinel) as today.

### E9.8 — Work-order export (#22 work orders)
`WorkOrderCarousel`'s export emits `browser.export.requested` (`export_kind=work_orders`, `format`, duration, outcome).

### E9 close
As F9.

## 5. Stream N9 — Next.js server side (D9-10)

### N9.1 — Request context
- **Files:** new server-only `lib/telemetry/server-context.ts`: an AsyncLocalStorage store {trace id, `traceparent`,
  `tracestate`, route template, method}; a strictly validated W3C `traceparent` (version `00`, non-zero ids) is taken
  from the inbound request, otherwise a new one is minted (random ids, sampled flag) so every hop has a trace id; a
  helper returns the headers to forward upstream.
- **Tests:** a valid inbound header is kept verbatim; malformed and all-zero ones are replaced by a valid minted one.

### N9.2 — Route wrapper and trace forwarding (G9-16)
- **Files:** a `withRoute(routeTemplate, handler)` wrapper applied to every exported method of the 12 route files under
  `app/api/`; the handler runs inside the context; every upstream `fetch` forwards the trace headers (beside the
  existing `X-Session-ID`); an uncaught error becomes one structured error line and a generic 500 JSON body (no
  internals).
- **Tests:** a fake upstream `fetch` receives the inbound `traceparent` (or the minted one when none came); a throwing
  handler answers 500 and writes one error line carrying the trace id and route. **Sweep test:** every exported HTTP
  method in `app/api/**/route.ts` is wrapped — a new route cannot ship dark.

### N9.3 — Structured server log lines
- **Files:** new `lib/telemetry/server-log.ts`: outside development, one JSON object per line — `ts`, `level`, `msg`
  (through `scrubMessage`), `service` = `dashboard-server`, `route`, `method`, `trace_id` from the context when present,
  plus the bounded kwargs under the logger's rules (sensitive keys redacted by name, strings capped, no nested
  objects); development keeps the readable console echo; `info`/`debug` stay suppressed in production.
  `lib/telemetry/logger.ts`'s server branch calls it (one hunk, §1b).
- **Tests:** in production mode the captured console output is one parseable JSON line per call with the trace id and
  redaction applied; in development it is the plain echo.

### N9.4 — `instrumentation.ts`
- **Files:** `instrumentation.ts` at the repo root: `register()` present as the documented seam (no SDK — G9-18);
  `onRequestError` writes one structured error line (`routePath`, `routeType`, method, digest, error type, scrubbed
  message, trace id parsed from the request's headers). Verify the Next 15.2.4 signature in
  `node_modules/next/dist/server/instrumentation/types.d.ts` before writing it.
- **Test:** calling the exported hook directly writes the expected line; a malformed header does not throw.

### N9.5 — Upstream-body and route-log hygiene (G9-17)
- **Files:** content-stream logs the status plus a bounded upstream error code (the S3 `<Code>` element or the api's
  error code) instead of raw bodies; the other 11 routes' log kwargs are reviewed — comment routes must not log comment
  text, tenant routes must not log organization fields — and fixed; the commented-out console line at
  `app/api/documents/[id]/route.ts:269` is deleted.
- **Test:** content-stream with a fake S3 error body naming a bucket and key logs neither string.

### N9 close
As F9.

## 6. Stream M9 — collector, boards, alarms

### M9.1 — Collector allow-list and body masking (G9-03)
- **Files:** `deployment/otel/base.yaml` — the browser allow-list (trace and log statements) gains the five §2.1 keys; a
  log-body masking step (the `redaction.blocked_values` patterns: email, bearer, JWT, AWS access key id) is added to
  the browser AND backend log pipelines of every profile (`backend-oss.yaml`, `backend-aws.yaml`, `backend-azure.yaml`
  each list their pipelines' processors — the step goes after the allow-list, before `redaction`; D9-8). Use the pinned
  collector 0.160.0 `redaction` processor's own body support if it has any; otherwise a `transform` processor with
  `replace_pattern` on the log body. `deployment/otel/validate.sh` passes for every profile.

### M9.2 — Collector tests (G9-27)
- `tests/integration/otel/test_collector_base_config.py` and the profile test pin the five keys and the masking step in
  every log pipeline of every profile.
- The `OTEL_COMPOSE_SMOKE=1` smoke posts one browser log record (an email and a presigned URL in the body, a stray
  attribute key) and one backend record (an email in the body) through the `oss` collector and asserts what reaches the
  sink: body masked, stray key gone, allow-listed keys kept. If the smoke cannot read Loki, assert through a file/debug
  exporter in the smoke overlay.

### M9.3 — Endpoint dimension for browser API latency and failures (G9-26; D9-9, D9-15)
- `deployment/observability-local/tempo.yaml` `span_metrics.dimensions` gains `url.template` and
  `http.response.status_code` (bounded: templates come from the route-pattern table with an `/unmatched` fallback;
  backend spans leave them empty); README note on cardinality.
- `fn-frontend` panel "API latency as the browser sees it" gains a per-template breakdown; a new "Browser API failures
  by endpoint and status" panel (errors are always kept, so failure counts are exact; 2xx spans are sampled at 10%, so
  success counts are not — the panel says so).

### M9.4 — Grafana `fn-frontend` panels (both dialects' shared spec first)
- `deployment/observability-local/grafana/provisioning/dashboards/flynapse/frontend.json` gains LogQL panels over
  `{service_name="dashboard"}`: Feature actions (feature × action × outcome); Feature action failure ratio by feature;
  Auth flows (flow × step × outcome); Optimizer runs triggered (phase × outcome); Exports (export_kind × outcome); AD
  dispositions (disposition × outcome); Long-running observed wait p75 (automation and discovery); Settings changes by
  entity. New panels carry the phase-6 DARK marker until P9 sees them (the `test_grafana_dashboards.py` marker grammar).
- `deployment/otel/dashboards/CATALOGUE.md` §5: signals, panels and the `aws` Logs Insights equivalents.

### M9.5 — `aws` dialect (G9-24; D9-11)
- `iac-obs9`: `dashboards/frontend.json.tftpl` gains the same panels as Logs Insights widgets (RE-VERIFY field paths
  after probe B1b, like every `aws` widget).
- Browser alarms as a gated seam: a new `.tf` file with CloudWatch Logs metric filters (the `browser.error` count; the
  web-vital LCP/INP/CLS values) and classic metric alarms (BrowserErrorRateHigh, WebVital LCP/INP/CLS p75 poor —
  thresholds copied from the Loki rules) targeting `aws_sns_topic.observability_alerts`, all behind one variable that
  defaults OFF, with RE-VERIFY markers; the flip step (verify the stored field paths at B1b, then set the variable) is
  named in the catalogue's alarm translation table and `docs/runbooks/observability/aws-profile.md`.
- `terraform fmt -check`, `terraform validate`, every body parses.

### M9.6 — DARK flip (after P9)
Remove "DARK until …" from the `fn-frontend` panels, the four Loki browser rule descriptions, the CloudWatch widget
titles and CATALOGUE §5 — **only for signals P9 observed**; anything P9 could not see keeps its marker with a dated
note. The guards in `test_grafana_dashboards.py` / `test_alert_rules_layout.py` pass either way.

### M9 close
Full `tests/integration/otel/` lane (static + both smokes + rules check), `validate.sh`, `terraform validate`.

## 7. P9 — live probe (session lead, after all four streams pass Opus review)
Integration tree `/home/aditya/Code/dashboard-obs9-probe` = `agent_sdk` + `obs9-browser` + `obs9-events` +
`obs9-server` merged locally (it also rehearses the gate's merge conflicts; it is deleted afterwards and never merged);
api from `api-obs9` via the bundle env; the `oss` collector + LGTM stack from `copilot-mro-obs9` (the dev-stack skill
and the 2026-09-05 probe recipe; loopback-remapped ports). `next build` + `next start` (production mode, so
`global-error` and the production log paths are the real ones). Checks, each with evidence banked in
`.dev_runs/obs9-probe-<date>/`:
1. Loki carries `browser.web_vital`, `browser.error`, `browser.route.change`, `browser.app.boot`, and at least one of
   each new §2.1 event from exercised flows (an optimizer job create + run + export, an AD disposition, a settings
   invitation, a comment, a register attempt, a work-order export).
2. A page opened with `?invite=probe-token#frag` and a presigned S3 preview: no browser span or record anywhere in
   Tempo/Loki contains `probe-token`, `X-Amz-` or a queried URL.
3. A deliberate warn with an email in its body arrives masked; a backend log line with an email arrives masked.
4. A forced api 500 shows a toast whose Reference opens the server trace in Tempo; a forced render error's fallback
   Reference finds its `browser.error` record in Loki; `global-error` reports once.
5. A Next route call (content-stream or tenant) → the api SERVER span is a child of the browser fetch span; the
   `next start` stdout carries one JSON line with the same trace id for a forced route failure.
6. The first auth/bootstrap request of a cold load has a span (F9.5).
7. Prometheus has span metrics with `url_template` and `http_response_status_code` for `service="dashboard"`.
8. `fn-frontend` renders every panel; then M9.6 flips what was seen.
Teardown by port and `compose down -v`; results and any fix passes recorded in §11.

## 8. Review design — two phases

**Phase A (now, Opus 5):** one fresh adversarial reviewer per stream (F9 includes the api CORS change), briefed with
the stream's section + §0 + §2 + §8a + the diff, running the suites itself and trying to break the work — defect
absence, not guard presence; every test must fail without its fix. Triage, fix pass, re-verification, brief into §10.

**Phase B (Fable, when the limit returns; after the phase-8 chunks R0–R5):** five bounded chunks, one fresh Fable agent
each, in merge order — R6 **design** (§0, §2, §8a, the stream split and file ownership) → R7 F9 (dashboard + api) →
R8 E9 → R9 N9 → R10 M9 (copilot-mro `deployment/**` + iac). A chunk's merge follows its verdict: dashboard branches
`--no-ff` into `agent_sdk` (F9, E9, N9 in that order, full unit lane + `tsc` after each), api into `langgraph-merge`,
copilot-mro `deployment/**` into `langgraph-merge`, iac into `main`. Nothing merges on an Opus-only verdict; a design
change at R6 rescopes the affected stream (fix pass on whatever model is available) before its code chunk runs. After
R10: a short re-probe of P9 checks 2, 4 and 5 on the merged mainlines.

### 8a. Design decisions for R6 (Fable rules keep / change / reject on each)

| # | Decision (as planned) | Alternatives considered | Why this one |
|---|---|---|---|
| D9-1 | One generic `browser.feature.mutation` (feature, entity, action, outcome) for every non-settings feature action; specific events only where research 07 defined richer attributes (#16, #18, #22, #23, #24) | (a) one event name per area (≈10 new names); (b) no events where no panel reads them | one name keeps the catalogue small and every action countable on one panel; the specific names stay where their attributes answer questions the generic one cannot (wait time, disposition, export kind) |
| D9-2 | `browser.auth.flow` for the five non-login auth steps; `browser.auth.login` unchanged | (a) widen `browser.auth.login` with a `flow` attribute; (b) nothing — the public-route fetch spans show failures | (a) changes an existing event's meaning mid-series; (b) cannot tell "user gave up" from "server refused", which is the signup-funnel question |
| D9-3 | The five LATER rows are built now (roster export excluded), superseding the phase-4 v1 deferral on the owner's 2026-09-11 request | keep them deferred and only record them in Future Improvements | the owner asked for every gap except Rostering; three of the five are the Optimizer/AD coverage the audit ranked |
| D9-4 | The support reference is the W3C trace id: API failures show the failing response's `X-Trace-Id`; render errors show the trace id their `browser.error` record was emitted under (the active span's, else a fresh one) | (a) the request id; (b) a short random code stored as a new attribute; (c) show nothing, rely on timestamps | the trace id opens Tempo (server trace + the kept browser span) and Loki (records carry it); a request id finds server logs only; a new attribute needs another allow-list key and a second lookup |
| D9-5 | The api keeps minting `X-Request-ID` and ignores an inbound one; the browser only reads it back | honour a well-formed inbound id | `traceparent` is the correlation channel; an honoured client id would let a caller choose server log keys, and nothing needs it |
| D9-6 | Telemetry starts at module evaluation of a boot module imported first by the client providers; the effect stays as the fallback — only if F9.5's first test proves the gap | (a) upgrade Next to ≥ 15.3 for `instrumentation-client.ts`; (b) an inline boot script in the layout | (a) is a framework upgrade outside this phase; (b) runs before the bundle exists; module evaluation precedes every component effect |
| D9-7 | URL queries and fragments are stripped at the exporter (the single exit) for every span and log attribute | per-instrumentation `applyCustomAttributesOnSpan` hooks; a span processor (`onEnding` does not exist in the pinned 2.11.0) | the exit sees every instrumentation, including ones added later; per-hook fixes miss the next instrumentation |
| D9-8 | Log bodies: scrubbed in the browser (`scrubMessage`), a constant-message guard (lint + source sweep), and masked again in the collector on the browser AND backend log pipelines of every profile | (a) browser only; (b) collector only; (c) collector browser pipeline only | two independent lines of defence, as spec §3.3 promises; the backend pipeline gets the same mask because its bodies have the same exposure — Fable may narrow it to (c) |
| D9-9 | Handled-inline API failures (`suppressGlobalError`) stay unlogged; their signal is the always-kept ERROR fetch span, charted by endpoint and status via Tempo span metrics | log each at warn | many handled failures are expected states (not-found-yet, polling); a record per occurrence is noise, and the span already carries template + status |
| D9-10 | Next server side: trace forwarding + request context + JSON log lines + `onRequestError` now; OTLP export (Node SDK) waits for the Amplify reachability probe | ship a Node OTel SDK now | spec §3.4 defers SSR export until Amplify can reach a private endpoint; forwarding restores the browser → api trace without it; no new dependency |
| D9-11 | `aws` browser alarms = log metric filters + classic metric alarms behind a variable defaulting OFF, flipped after probe B1b verifies the stored field paths | documentation only (the phase-6 T12 precedent) | classic log-metric alarms do not need the PromQL dialect ruling (T12's first gate) — only B1b's field paths block them, so the seam is built and switched off; the owner may prefer documentation only |
| D9-12 | Rostering excluded; its console calls exempted by an ESLint override | fix them anyway | owner ruling 1: demo code, not instrumented |
| D9-13 | The §2.3 areas get no new event | an event per UI gesture | spec §7.4 drops click-level interaction; each area's question is already answered by route changes, fetch spans or a feature action |
| D9-14 | Chat attachment uploads run inside the turn span; the turn records `attachment_count` and `attachment_upload_ms`; no separate upload event | emit `browser.upload.started` + `upload_finished` for attachments | the `upload_finished` product fact means Document Hub uploads in the product views; mixing chat attachments would change its meaning, and the turn is where attachment time matters |
| D9-15 | Tempo span metrics gain `url.template` and `http.response.status_code` dimensions | a browser metrics pipeline (MeterProvider + exporter) | no new browser dependency; bounded by the route table; backend series unchanged (empty label) |
| D9-16 | Three dashboard streams in parallel on separate branches with per-hunk file ownership (§1b), merged in a fixed order | one sequential dashboard stream | reviewable per concern and about three times faster; conflicts are confined to named hunk boundaries and rehearsed by P9's integration tree |

### 8b. Phase A close — gate agenda
_(filled at Phase-A close: branch tips, suite evidence, merge mechanics per chunk)_

## 9. Future Improvements
- **SSR OTLP export (G9-18).** Missing: route-handler spans and server logs in Tempo/Loki. Deferred by spec §3.4
  until Amplify WEB_COMPUTE can reach a private endpoint (master §13 probe). Complete solution: `instrumentation.ts`
  `register()` starts a Node OTel SDK exporting to the api's authenticated ingest with a service credential (or a
  private collector if Amplify gains VPC reach); N9's request context becomes the span parent.
- **Raw `fetch` without `X-Session-ID` (G9-30).** Authenticated raw calls (`optimizer-api.ts:760`,
  `improvement-api.ts:333`, `lib/api/utils.ts` helpers) skip `fetchWithAuth`, so server logs lack the session binding
  for them. Complete solution: route every authenticated call through `fetchWithAuth`; the public-page calls stay
  session-less by design. Deferred: it changes the auth transport (token refresh) outside telemetry.
- **App ↔ collector allow-list parity guard.** The browser keys live in `events.ts` and in `base.yaml`'s regex, kept in
  step by hand ("never unilaterally"). Complete solution: a generated shared key list or a cross-repo parity test.
  Deferred: cross-repo test plumbing across worktrees; P9 check 1 is this phase's proof.
- **Span-metric success counts are sampled.** 2xx browser spans are kept at 10%, so per-endpoint success rates from
  span metrics are biased; exact server-side rates already exist from the api's `http.server.request.duration`.
- **aws browser alarms stay off until B1b** (D9-11) — flip after the field-path probe.

## 10. Review briefs (Phase A output; input to Phase B)
_(one per stream, written by its reviewer)_

## 11. Implementation notes / Learnings (per stream, as work lands)
_(filled by implementers and the session lead)_

## 12. Lessons
_(plan-scoped; append after any owner correction)_
