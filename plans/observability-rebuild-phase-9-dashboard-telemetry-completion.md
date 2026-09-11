# Observability rebuild — Phase 9: dashboard telemetry completion

**Status:** OPENED 2026-09-11. **Plan v2** — revised after the independent Opus 5 plan review (verdict READY AFTER
CHANGES: 6 P1, 9 P2, P3s; triage in §10a). Build + Opus adversarial review = Phase A; the Fable gate (design + code) =
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
2. The plan is reviewed by an independent agent before implementation starts (done: §10a).
3. Fable reviews the design (chunk R6) and every stream's code (R7–R10) when its limit returns; merges wait for it.

**Owner look requested, non-blocking:** spec §7.4 makes the event catalogue owner-reviewed, and phase 4 ruled the
five LATER rows out of v1. The §2.1 delta (two new names, the five LATER rows built, two extensions) is put to the
owner alongside the build; E9 proceeds on the owner's "then let's implement", and a veto becomes a fix pass before the
(already held) merge.

**Goal.** Close the distance between the phase-4 browser stack as merged (dashboard `agent_sdk` @ `b87ced0`) and a
complete tracing/logging/metrics story: no URL query, object path, token or email leaves the browser; every failure
shown through the shared error handler or an error boundary carries a support reference that opens its trace; the
first requests of a page load are traced; the Next.js server hop is correlated and structured; every product area
outside Rostering emits a catalogued signal or is dispositioned as covered by a generic one; both dashboard dialects
chart the new signals — proven by a live probe that also retires the frontend board's DARK labels.

**Audit inputs.** Two read-only audits at `agent_sdk` `b87ced0` (plumbing: tracing, logging, metrics; coverage: the
25-event catalogue against research 07's areas), top claims spot-verified by the session lead; plus the plan review's
code checks (§10a). Every file:line below is at `b87ced0` unless stated.

**Spec sections:** §3.3 (signals), §3.4 (browser via the gateway; SSR deferral), §7.4 (frontend rebuild and
catalogue discipline), §8 (hygiene), §9.2–§9.4 (boards, alerts, `aws`).

**Inherited constraints (master §1, §11a, §12; phase-8 practice):** branch from the current mainlines
(`dashboard` = `agent_sdk`, `api` = `langgraph-merge`; M9's two trees are stacked on the phase-8 D8 branches, §1);
nothing in the migration conflict zone (this phase needs none of it); commits on this phase's own worktree branches
by pathspec (`git commit -- <paths>`), never `git add -A` — the branches carry no owner WIP, which is why production
edits are committed there, as in phase 8; no credentials in output, commits or screenshots; no user content in any
log body, log attribute or span attribute; the browser never sees a collector URL; plan files carry no code;
Terraform validated, never applied; nothing pushed. Phase-9 specific: **no new npm or Python dependency** (a stream
that needs one stops and reports); dashboard worktrees symlink `node_modules` and `.env.local` to the main
checkout's; **every `logger` message is a constant string literal** (F9 adds the guard; E9 and N9 obey it from the
start); production builds strip `console.*` (`next.config.mjs` `compiler.removeConsole`), so nothing that must survive
production may rely on `console`; ≤5 agents at once (owner cap this session); every agent is reported as
`name — model`; all Phase-A agents are Opus 5.

---

## 0. Gap register (audit 2026-09-11 + plan review → task or disposition)

| ID | Gap (evidence at `b87ced0`) | Disposition |
|---|---|---|
| G9-01 | Document-load, document-fetch and resource-fetch spans carry the full page/resource URL with query and fragment: `lib/telemetry/provider.ts:241` builds `DocumentLoadInstrumentation` with no config and the library writes `location.href` / `resource.name`; these INTERNAL spans are never ratio-dropped and the collector keeps `url.*` — invite/registration tokens (`?invite=`, `?token=`), `chatUserId`, presigned S3 queries reach Tempo/X-Ray | F9.1 |
| G9-02 | Log bodies are not scrubbed, and 14 shipped-level `logger.warn` bodies in `lib/api/settings-api.ts` interpolate data: emails at `:595`, `:1796`, `:1819`; ids at `:545`, `:621`, `:752`, `:767`, `:835`, `:1022`, `:1514`; tenant-authored names at `:1652`, `:1712`, `:1802`, `:1832` (the multi-line calls put the template on the line after `logger.warn(`); plus `handleApiError`'s conditional template (`lib/api/error-handler.ts:164-167`) | F9.2 |
| G9-03 | The collector's `redaction` processor masks attribute values only; log bodies pass every pipeline untouched | M9.1 — premise DISPROVED at build: the pinned 0.160.0 `redaction` already masks string log bodies (probe on the pinned image + processor source); kept as a tested property instead (every log pipeline of every profile ends `redaction` → `batch`; the compose smoke reads masked bodies back from Loki) |
| G9-04 | `X-Request-ID` and `X-Trace-Id` are missing from the api's CORS `expose_headers` (`api/flynapse_api/middleware/cors.py`), so the browser span's `request_id` attribute (`provider.ts:74-79,165-176`) is never set | F9.4 |
| G9-05 | No support reference anywhere in the UI (`lib/api/error-handler.ts` toast, `lib/telemetry/ErrorBoundary.tsx`, `components/shared/FeatureErrorFallback.tsx`) | F9.4 |
| G9-06 | The api mints its own request id and ignores an inbound `X-Request-ID` (`api/flynapse_api/middleware/request_id.py:36-41`) | disposition: by design (D9-5) |
| G9-07 | No `app/global-error.tsx`: root-layout and provider-level errors go unreported | F9.6 (+ N9.4 for SSR root failures) |
| G9-08 | Telemetry and the global error handlers start in the outermost provider's `useEffect` (`components/providers/TelemetryProvider.tsx:24`), which React runs after every descendant's effects — the first bootstrap requests may be untraced (inferred; F9.5's first test, on the real provider tree, proves or disproves it) | F9.5 |
| G9-09 | `'API error:'` records collapse: the logger dedupes on `level:msg` for 15 s and the record carries no `url.template` or status (`lib/telemetry/logger.ts:78-83`, `lib/api/error-handler.ts:165`) | F9.3 |
| G9-10 | The 43 `suppressGlobalError: true` queries/mutations log nothing | disposition D9-9, plus M9.3 (their failures are always-kept ERROR fetch spans, charted by endpoint) |
| G9-11 | Chat attachment uploads run before `turn.runInContext` (`hooks/chat/useMroMessageStream.ts:285,313,348`; pilot/crew equivalents): unlinked root spans, 90% dropped, no attachment time on the turn | F9.7 |
| G9-12 | No `no-console` rule (`.eslintrc.json`), so the five `eslint-disable no-console` comments are inert; 15 raw `console.*` calls in 9 files — 7 in Rostering, 8 elsewhere (one under `app/api/`) | F9.2 (Rostering exempt), N9.5 (the `app/api/` one) |
| G9-13 | `.env.example:11` still sets `OTEL_EXPORTER_OTLP_ENDPOINT`, outside the legacy guard's roots | F9.8 |
| G9-14 | Dead hand-rolled traceparent generator, `lib/api/utils.ts:51-86` | F9.8 |
| G9-15 | `lib/api/client.ts:186,226` `logger.info` lines carry full request URLs (phase-4 Future Improvement, "when next touched") | F9.3 |
| G9-16 | The 12 Next.js route handlers log through `console` only — which `compiler.removeConsole` probably strips from production builds entirely — and forward `X-Session-ID` but not `traceparent`; there is no `instrumentation.ts` / `onRequestError` | N9.1–N9.4 |
| G9-17 | `app/api/document-hub/documents/[id]/content-stream/route.ts:80-84,108-112` log raw upstream bodies (the api's detail; S3 XML naming buckets and keys) | N9.5 |
| G9-18 | SSR spans and logs are not exported over OTLP | disposition: deferred by spec §3.4 to the Amplify private-reachability probe; N9 builds the seam (§9) |
| G9-19 | `browser.settings.mutation` (#19) misses invitations, operators, operator grants, the operator registry, organization, `deleteDepartment` (`settings-api.ts:1728`), `deleteOperator` (`:1359`) | E9.4 → withdrawn 2026-09-11: the owner's TanStack conversion session owns these call sites and adds `meta.telemetry` with `browser.settings.mutation` (§1b) |
| G9-20 | AD review emits nothing (`hooks/mro/useAdReview.ts`) | E9.3 |
| G9-21 | Optimizer: 22 mutations with no telemetry (`hooks/api/useOptimizer.ts`), including solve and export | E9.2 |
| G9-22 | LATER rows #16, #18, #22, #23, #24 are unbuilt and tracked only in the phase-4 appendix | E9.2, E9.3, E9.6, E9.8 (roster export excluded) |
| G9-23 | Areas with no specific event: automations CRUD, comments, improvement, notifications, chat share, Document Hub metadata/sharing/retry/delete, data-discovery sources and jobs, the four non-login auth pages | E9.5, E9.7; the rest dispositioned in §2.3 |
| G9-24 | `aws`: no browser metric filters or alarms | M9.5 documents the exact filters and alarms; the Terraform waits for the owner's CloudWatch alarm-dialect ruling (phase-6 T12, which includes "defer") and probe B1b's field paths (D9-11) |
| G9-25 | Grafana `fn-frontend` panels 1–6, the four Loki browser rules and the CloudWatch frontend widgets still say DARK, pending the POC acceptance run | P9, then M9.6 |
| G9-26 | Browser API latency has no per-endpoint dimension (Tempo `span_metrics` dimensions are db/peer/server/rpc only) | M9.3 |
| G9-27 | No collector test exercises the browser allow-list or body masking end to end | M9.2 |
| G9-28 | Rostering: no network calls, payroll export is a `setTimeout` stub, 7 console calls | EXCLUDED (owner ruling 1) |
| G9-29 | 8 `window.open` and 4 `<iframe>` loads are untraced | disposition: top-level navigations cannot carry `traceparent`; the same-origin ones land on a Next route that mints a trace (N9.1); iframes load S3 directly — resource timing only, URL reduced by F9.1 |
| G9-30 | Raw `fetch(` calls that bypass `fetchWithAuth` (no `X-Session-ID`) | Future Improvement (§9): not a ranked gap, and it changes the auth transport |
| G9-31 | `browser.telemetry.dropped` ships but is not in the catalogue | §2.1 lists it with a consumer panel (M9.4); E9.1 pins it in the catalogue test |
| G9-32 | Stale items #7 (`/loginwithsso`) and #13 (`chart-card-visual-test`) | kept by earlier owner rulings — no action |
| G9-33 | The collector allow-list strips free-form `browser.log` kwargs (`copilot-mro/deployment/otel/base.yaml:146`) | disposition: by design (spec §3.3 — client-authored keys never reach a backend); a kwarg that must reach Loki needs a catalogue key; F9.3's kwargs use the allow-listed `url.*` / `http.*` / `error.*` families |
| G9-34 | No settle signal for an optimizer solve or an AD corpus materialize (coverage audit §1.13) | disposition: completion truth is server-side — the phase-8 `optimizer.run` span and metrics; the AD materialize run status on the server — the browser records triggers only (D9-13) |
| G9-35 | The optimizer wizard's chained direct writes (`components/features/optimizer/wizard/steps/ReviewStep.tsx:174,181,186,191` — create/process activity, create role, create job) escape a `useMutation`-only sweep | E9.2 |
| G9-36 | Five chat display components have no event (`NotamCard`, `WeatherCard`, `FilePreviewModal`/`SignedFilePreviewContent`, `DocumentSearch`, `MobileChatNavigation`) | §2.3 |
| G9-37 | `browser.automation.run_triggered` allows `department` but never sets it | E9.5 |
| G9-38 | The member update in `hooks/settings/useTeamData.ts` (~`:380`) emits two `browser.settings.mutation` records per click (reported by the TanStack mutation audit, §1b) | withdrawn to the TanStack conversion session (§1b) |
| G9-39 | 79 direct `toast.error(` sites bypass `handleApiError` (e.g. `components/features/optimizer/outputs/CanvasHeader.tsx:193` toasts `err.message`), and `lib/api/optimizer-api.ts:803,820` build their own `ApiError` | F9.3 routes the two optimizer sites through the shared helper; the direct toast sites are a Future Improvement (§9) |
| G9-40 | The api's auth-layer 500s (and its 401/403/429) leave without `X-Trace-Id`: `setup_trace_id_header` is added inside `UniversalAuthMiddleware` (`api/flynapse_api/main.py:283-305`), and auth converts downstream exceptions into a `JSONResponse(500)` it returns itself (`middleware/auth.py:504-540`) | F9.4 |
| G9-41 | Cross-origin resource URLs (S3 previews, iframes, anything loaded before telemetry starts) keep bucket and object-key paths in `url.full` (`instrumentation-document-load/.../instrumentation.js:120`) | F9.1 |

## 1. Streams, worktrees, waves

| Stream | Scope | Worktree → branch (base) | Depends on | Wave |
|---|---|---|---|---|
| **F9 — browser correctness + correlation** | URL scrub at the exporter, log-body hygiene + guards, API-error records, support references (+ the api CORS and trace-id header changes), first-load start, global error page, chat attachments inside the turn, hygiene leftovers | `/home/aditya/Code/dashboard-obs9` → `obs9-browser` (off `agent_sdk` `b87ced0`); `/home/aditya/Code/api-obs9` → `obs9-api` (off `langgraph-merge` `a19a931`) | nothing | 1 |
| **E9 — event coverage** | the §2 catalogue additions at their choke points | `/home/aditya/Code/dashboard-obs9e` → `obs9-events` (off `agent_sdk` `b87ced0`) | the §2 pins | 1 |
| **N9 — Next.js server side** | request context + trace forwarding, structured server log lines, `instrumentation.ts`, upstream-body hygiene | `/home/aditya/Code/dashboard-obs9n` → `obs9-server` (off `agent_sdk` `b87ced0`) | nothing | 1 |
| **M9 — collector, boards, alarms** | allow-list + body masking in every profile, the Tempo endpoint dimension, `fn-frontend` panels in both dialects, the aws browser alarm definitions (documentation), catalogue and runbook text | `/home/aditya/Code/copilot-mro-obs9` → `obs9-deploy` (off `langgraph-merge` `bc0e3858` + a `--no-ff` merge of phase-8 `obs8-dashboards` @ `ba14daa3` = `9976fa7c`; `deployment/**`, `tests/integration/otel/**`, `docs/runbooks/observability/**` only); `/home/aditya/Code/iac-obs9` → `obs9-iac` (off `main` `5996e5a` + a merge of `obs8-iac` @ `094869d` = `9231863`) | the §2 pins | 1 |
| **P9 — live probe + DARK flip** | one probe over all four streams; then the DARK labels come off what it saw | throwaway `/home/aditya/Code/dashboard-obs9-probe` → `obs9-probe` (the three dashboard branches merged locally, never merged anywhere) + the other obs9 trees | F9, E9, N9, M9 reviewed | 2 |

M9 is **stacked on the phase-8 D8 branches** because it edits the same files (`deployment/otel/dashboards/CATALOGUE.md`,
`deployment/observability-local/README.md`, `tests/integration/otel/test_grafana_dashboards.py`,
`test_alert_rules_layout.py`, `docs/runbooks/observability/alerts.md`; iac `cloudwatch_dashboards.tf`) and extends their
guard fixture lists; R10 therefore merges after phase-8 R5. The four build streams start together (four
implementers); each stream's reviewer starts when its implementer finishes (≤5 agents at once). Reviewer = a fresh
Opus 5 agent per stream, briefed with that stream's section + §0 + §2 + §8a + the diff, running the suites itself;
triage by the session lead (real gap → fix pass by the same implementer → re-verification by the same reviewer;
intentional → §9); the reviewer writes the stream's brief into §10.

### 1a. Progress
- [x] Plan v1 (`e1845fd`) + master §11c
- [x] Independent plan review (Opus 5, READY AFTER CHANGES) → triage §10a → plan v2 (this file)
- [ ] F9 — built 2026-09-11 (dashboard `ee68a7a` → `b9ba515`, 11 commits; api `46a86fc`; unit 1815/1815, tsc, eslint, api middleware + infra 322; F9.5 PROVED both first-load gaps on the real tree → `lib/telemetry/boot.ts`); review MERGE-READY AFTER FIXES (1 P1 — api error text in browser.log and browser.error; 6 P2; 6 P3 — incl. the six queued cross-stream items, several widened); fix pass done (dashboard `af9f307`, 10 commits on `b9ba515`; api `72df51a`; unit 1841/1841, tsc, eslint, api 322); re-verified MERGE-READY (14 reviewer mutations all caught; 2 new P3 → §9). **F9 Phase A done** (tips `af9f307` / `72df51a`)
- [ ] E9 — built 2026-09-11 (`f697919` → `3a2610a`, 9 commits: E9.1–E9.3, the `useAppMutation` follow-up `0b236a5`, E9.5 `286f5a3`, E9.8 `0a85834`, E9.6 `65929a0`, E9.7 `c2d05c6`, close `3a2610a` — no pending exemptions left; E9.4 withdrawn to the TanStack conversion; unit 1838/1838, typecheck, eslint); review MERGE-READY AFTER FIXES (1 P1 — Run now outcome words; 2 P2 — the useShare email, the AD page wiring untested; 5 P3); fix pass done (`a708d49` → `08b7650`, 6 commits; unit 1845/1845 in 606 s, typecheck, eslint); re-verified MERGE-READY (10 reviewer mutations all caught). **E9 Phase A done** (tip `08b7650`)
- [ ] N9 — built 2026-09-11 (`81b1ea9` → `f3d7d21`; unit 1851/1851, typecheck, eslint, `next build` clean; `removeConsole` settled: literal `console.x` calls are stripped server-side, computed calls survive); review MERGE-READY AFTER FIXES (3 P1: api error text in route log lines and in 5xx bodies, the NODE_ENV-keyed format; 4 P3); fix pass done (`3784b13` → `00c9763`, 7 items; unit 1874/1874, typecheck, eslint); re-verified MERGE-READY (2 new P3 — a list-`detail` 422 relayed as "[object Object]", the literal-body rule's scope — landed in the mini pass `cc193eb` + `c52f034`; unit 1877/1877). **N9 Phase A done** (tip `c52f034`)
- [ ] M9 — built 2026-09-11 (copilot-mro-obs9 `07f22475` → `c3faabf1`, iac-obs9 `1eb8c6c`; otel lane 80 passed incl. both compose smokes); review MERGE-READY AFTER FIXES (the pre-ruled drop-keys P1, 3 P2, P3s); fix pass done (copilot-mro-obs9 `6984d47b`, iac-obs9 `ad4e431`; otel lane 83 passed incl. both smokes; Tempo `max_active_series` cap 100000); re-verified MERGE-READY (4 P3 nits: `__error__` in the parity guard, a cap alert + test ceiling, the iac drops-widget title — landed in the mini pass `28973020`, `7d453a6d`, `31526d64` + iac `bd7992a`, incl. a new warning alert `TempoGeneratorSeriesNearCap` at 80% of the cap; the "fetch network failures once F9's fix lands" wording rides on F9's fix pass). **M9 Phase A done** (tips `31526d64` / `bd7992a`); M9.6 waits for P9
- [ ] P9 — live probe on the integration tree; DARK flip (M9.6)
- [ ] Phase A closed — §8b gate agenda with branch tips
- [ ] Owner look at the §2.1 catalogue delta (non-blocking)
- [ ] Fable R6 (design) → RC (the owner's TanStack conversion, Fable-gated too; merged into `agent_sdk` first) → R7 F9 → R8 E9 → R9 N9 → R10 M9, merge after each

### 1b. Files more than one stream touches (each stream owns one hunk)

| File | F9 owns | E9 owns | N9 owns |
|---|---|---|---|
| `lib/telemetry/events.ts` | `emitLog` (body scrub) and `emitRecord`'s optional trace-context parameter | new names, allow-lists, emitters, timing wrappers | — |
| `lib/telemetry/logger.ts` | `ship` (dedupe key, trace linkage) | — | the server branch of `log` (one lookup of the global server sink, §5) |
| `lib/telemetry/errors.ts` | all of it | — | — |
| `lib/api/settings-api.ts` | the 14 warn sites (G9-02) | the two unwrapped deletes, the member-update double emission, any new wraps | — |
| `lib/api/utils.ts`, `lib/api/fetch-utils.ts`, `lib/api/error-handler.ts`, `lib/api/client.ts` | all of them | — | — |
| `lib/api/optimizer-api.ts` | the two `ApiError` sites (`:803`, `:820`) | any API-layer emission (D9-17) | — |
| `.eslintrc.json` | all of it | — | — |
| `app/api/**`, `instrumentation.ts` | — | — | all of it (including `documents/[id]/route.ts:269`) |
| `hooks/chat/**` | all except `useShare.ts` | `useShare.ts` | — |

Gate merge order: F9 → E9 → N9, each `--no-ff` into `agent_sdk`; conflicts are expected only at the boundaries above,
and the full unit lane + `tsc` re-run after each merge (P9's integration tree rehearses them first). A stream that
finds it must edit another stream's hunk stops and reports instead.

**Adjacent owner-side work.** `dashboard/docs/plans/tanstack-mutation-coverage-audit.md` (untracked, 2026-09-11, a
read-only audit at `b87ced0`) proposes converting 34 direct writes to `useMutation` — including E9's direct-call
targets (`NotificationBell.tsx:149`, the wizard chain, Document Hub writes, invitations, operators, organization, the
department cascade). E9 does **not** convert them (pending state, invalidation and cascade fixes are that audit's
scope); it emits so that telemetry stays correct whichever way those sites end up, and its double-emission guard
catches a later conversion that would count an action twice (D9-17).

**Coordination with the owner's TanStack conversion session (ruled 2026-09-11, after the owner launched it).** The
owner is now converting the audit's 34 direct writes to `useMutation` in a separate session. Split, to keep two
sessions off the same lines:
- **The conversion session owns** every call site on that audit's convert list — the settings writes (tenant and
  department roles, team add/update/remove, departments, invitations, operators and grants, organization, the
  invite-accept retry), Document Hub upload/metadata/retry/delete, notifications bulk mark-read, delete-chat, the
  optimizer wizard's direct writes and CanvasHeader's re-run preflight — and the mutation bugs it lists. For converted
  **settings** writes it swaps `withSettingsMutation` for `meta.telemetry` with the existing `browser.settings.mutation`
  (its own prerequisite #3), using the §2.1/§2.2 entity and action words. It adds **no new events** and does not change
  `MutationTelemetryEvent`. Converted **feature** writes get no `meta.telemetry` yet (their event exists only on
  `obs9-events`); the optimizer wizard should call the existing hooks, which E9 already instruments.
- **Phase 9 (E9) owns** the event catalogue and telemetry on mutations that already exist (optimizer hooks, AD review,
  automations CRUD, comments, improvement, chat share, the data-discovery page mutations), the settles, auth flows and
  exports. E9.4 is therefore withdrawn from E9 (G9-19, G9-38 move to the conversion session), and E9.5 drops the
  notifications and Document Hub writes.
- **At the merge:** the conversion is Fable-gated too (owner, 2026-09-11): it builds on its own branch off `agent_sdk`, and its Fable chunk (RC, after R6) is reviewed and merged into `agent_sdk` BEFORE phase 9's code chunks — so before R7 each obs9 dashboard
  branch merges the then-current `agent_sdk` and re-runs its lanes. E9's repo-wide coverage sweep then lists every
  converted mutation still without `meta.telemetry`; the follow-up adds `browser.feature.mutation` meta to those, and
  its double-emission guard rejects any mutation that declares meta while calling a still-wrapped primitive. E9's
  call-site wrappers in `ReviewStep.tsx` / `CanvasHeader.tsx` give way to the hook path (CanvasHeader's re-run passes
  `jobId` to `usePreflightJob` to keep `job_id`). Conflict-prone files between the two efforts: `settings-api.ts`,
  `lib/api/utils.ts`, `lib/api/client.ts`, `useOptimizer.ts`, `RunsPanel.tsx`, `ReviewStep.tsx`, `CanvasHeader.tsx`,
  `useComments.ts`, `useShare.ts`, `useAutomations.ts`, the data-discovery pages, `InviteAcceptView.tsx`.
- **Refinements agreed with the conversion session (code-26, 2026-09-11).** It builds on `/home/aditya/Code/dashboard-tanstack`
  off `agent_sdk` `b87ced0`. It also owns the read side of the pages it converts: `hooks/chat/useDepartmentChatHistory.ts`,
  the post-turn list refresh in `useDepartmentMessageStream.ts`, the throwaway list refresh in `useCopilotDockChat.ts`,
  `TenantAllChatsPanel.tsx`, the chat caches in `lib/api/client.ts` (~:114-145, ~:655-725, ~:1118-1124), the
  `NotificationBell` poll, the Document Hub list/navigation reads, the tenant settings pages' reads and new key families
  in `lib/query/query-keys.ts`; it leaves `useMro/Pilot/CrewMessageStream`, `fetch-utils`, `error-handler` and
  `lib/telemetry/**` alone. It deletes `lib/api/api-client.ts`, the `lib/api/index.ts` barrel and `markNotificationRead`
  (no phase-9 code imports the barrel). F9.8 deletes the dead `sendMessage` (`client.ts`), `rawApiRequest` and
  `handleApiResponse` (`utils.ts`); E9 deletes the uncalled `useCreateSchedule`, `useUpdateSchedule`, `useDeleteJob`. In
  `InviteAcceptView.tsx` the conversion owns only the signed-in "Finish joining" retry (left without `meta.telemetry`;
  phase 9 adds its record at the merge), E9.7 the preview/accept flow. RC also carries a small core change on its own core branch (the department-delete endpoint declares its members' and role holders' auth-cache invalidations, since the dashboard's cascade collapses into the single DELETE); no phase-9 stream touches core. The conversion moves the phase-4 proof
  `tests/unit/telemetry/settings-mutation-sites.test.ts` to its new hooks; after RC merges, E9 deletes the then-dead
  `withSettingsMutation` export and updates its guard's pinned list. **Merge rules where both touch the same code (phase 9 merges second; the session lead runs it):** in `useOptimizer.ts` the two `meta` edits are COMBINED — one meta object literal carrying RC's `suppressGlobalError` (its caller-shows-errors option on the wizard's hooks, the CSV upload and process) and E9's `telemetry` — never one side taken (RC's `optimizer.jobs` invalidation in `useRunJob` / `useRuns` is adjacent and kept); in `settings-api.ts` RC's version of the `createDepartment` / `updateDepartment` / `deleteDepartment` blocks (~:1585-1834, where RC removes the client cascade and rewrites the swallowed head-assignment catches) is taken over F9.2's warn fixes, and F9's AST guard verifies every surviving message is a literal. The conversion's plan: `dashboard/docs/plans/tanstack-mutation-conversion.md` (on branch `tanstack-conversion`), which copies this split under "Rulings and agreements". RC's shared `useAppMutation` helper (`hooks/shared/useAppMutation.ts`: call sites write `mutationFn` and `meta: { telemetry }` as literals; one internal `useMutation` with `meta = { suppressGlobalError: true, ...meta }`) is kept — E9's coverage sweep and double-emission guard treat `useAppMutation(` call sites as mutation sites (the callee is pre-wired in E9), the helper's own internal call is exempted at the merge (the stale-exemption check rejects it earlier), and after F9 merges the helper's single error toast gains the support reference. (As landed on `tanstack-conversion` `46208ee`: one internal `useMutation` with `meta: { suppressGlobalError: true, ...options.meta }` and one error toast; its optional permission gate runs inside the helper's `mutationFn`, so a refusal settles as outcome `error` with `error_type` `MutationRefusedError` and sends no request. Ruling 2026-09-11: the helper stays as is and the class name stays stable; a refusal is not a failure, so the failure-ratio panels exclude `error_type="MutationRefusedError"` and chart refusals as their own series — M9.6.) Logger calls in converted writes (ruled 2026-09-11 at code-26's request): converted SETTINGS writes drop their hand-rolled constant `logger.error`/`warn` — their counted signal is the settle record from `meta.telemetry` and their debug pivot the always-kept ERROR fetch span (D9-9), so a `browser.log` record would report the failure twice; converted FEATURE writes (today `NotificationBell.tsx:157`) keep their existing constant logger call unchanged in `onError` until phase 9's post-merge follow-up adds their `meta.telemetry` and removes that call in the same change.

### 1c. Test environments
- **Dashboard (all three trees):** `npx tsx --tsconfig tsconfig.test.json --test <files>` while building, the full unit
  lane (`npm run test:unit`) before review; `npm run typecheck`; `npx eslint` on every touched file. Tests use the
  phase-4 harnesses (`tests/fixtures/telemetry-harness`, `tests/fixtures/dom-harness`) and the two-level layout
  (`tests/unit/<domain>/…`; telemetry guards live in `tests/unit/telemetry/`). WSL rule: assert booleans, never hold
  jsdom nodes in assertion messages. N9 additionally runs `npm run build` once at close (the client-bundle proof).
- **api-obs9:** the `wt-obs-u` bundle env with `PYTHONPATH` pinned to `api-obs9` and the main `utils` checkout (the
  phase-8 stream-S recipe, `env -u VIRTUAL_ENV POETRY_VIRTUALENVS_IN_PROJECT=true`), `DEBUG=false`.
- **copilot-mro-obs9:** the `tests/integration/otel/` lane from the shared api env with the worktree as rootdir and
  `POSTGRES_DB=copilot_mro_test` — static guards always, `OTEL_COMPOSE_SMOKE=1` for M9.2's real-container smoke,
  `OTEL_RULES_CHECK=1` / `validate-rules.sh` for rules, `deployment/otel/validate.sh` for collector configs.
- **iac-obs9:** `terraform init -backend=false` once, `terraform fmt -check` + `terraform validate`; every
  `dashboards/*.json.tftpl` body parses after substitution (the phase-6 check).

## 2. Pinned catalogue additions (E9 builds them; M9 allow-lists and charts them in parallel)

### 2.1 New and extended signals

Signal: **L** = OTel log record through the existing `emitRecord` envelope; **S** = span. Every new row is 100%
(records are never sampled), severity INFO (failure rides in `outcome`).

| Name | Tier | Signal | Trigger / choke point | Attributes (beside the envelope) | Consumer |
|---|---|---|---|---|---|
| `browser.feature.mutation` (new) | SHOULD | L | every feature action in §2.2 — TanStack `meta.telemetry`, or one emission for a direct write (D9-17) | `feature`, `entity`, `action`, `outcome`, `duration_ms`, `error_type` | `fn-frontend` "Feature actions", "Feature action failure ratio" |
| `browser.auth.flow` (new) | SHOULD | L | register submit, signup-code confirm, forgot-password code request and confirm, new-password (challenge) submit, invite preview and accept | `flow`, `step`, `outcome`, `duration_ms`, `error_type` | "Auth flows" |
| `browser.automation.run_settled` (#16) | LATER → built | L | `useAutomationRuns` first observes a terminal status for a run this session triggered | `automation_id`, `run_id`, `terminal_status`, `observed_wait_ms` | "Long-running flows: observed wait p75" |
| `browser.discovery.job_settled` (#18) | LATER → built | L | the first observation that a job this page polled is no longer in progress | `job_kind`, `job_id`, `terminal_status`, `observed_wait_ms`, `poll_count` | same |
| `browser.export.requested` (#22) | LATER → built | L | optimizer run export, work-order export (roster export excluded) | `export_kind` ∈ {`optimizer_run`, `work_orders`}, `format`, `row_count_bucket`, `duration_ms`, `outcome` | "Exports" |
| `browser.optimizer.run_triggered` (#23) | LATER → built | L | preflight and run through the hooks and the wizard's direct call | `job_id`, `phase` ∈ {`preflight`, `solve`}, `outcome` ∈ {`accepted`, `rejected`}, `preflight_warning_kind`, `duration_ms`, `error_type` | "Optimizer runs triggered" |
| `browser.ad_review.disposition_set` (#24) | LATER → built | L | disposition write and clear | `disposition` ∈ {`confirmed_applicable`, `ruled_not_applicable`, `cleared`}, `had_prior_disposition`, `source` ∈ {`table`, `dialog`}, `outcome`, `duration_ms`, `error_type` | "AD dispositions" |
| `browser.settings.mutation` (extended) | SHOULD | L | new entities (agreed with the conversion session, which now builds them): `invitation` (create / revoke / resend), `operator` (create / update / delete — the operator identities the operator-registry page edits), `operator_grant` (grant / revoke), `organization` (update), `department` (create / update / delete); `member` and `role` unchanged | unchanged | existing + "Settings changes by entity" |
| `browser.chat.turn` (extended) | MUST | S | uploads run inside the turn (F9.7) | + `attachment_count`, `attachment_upload_ms` | Tempo trace view |
| `browser.error` (extended) | MUST | L | `app/global-error.tsx` (F9.6) | `error_kind` gains the value `global` (no new key) | existing error panels |
| `browser.telemetry.dropped` (catalogued) | baseline | L | the exporter's drop counter (already shipping) | unchanged | "Telemetry drops" (M9.4) |

**Vocabulary rules.** Every attribute is an opaque id, a closed enum, a boolean, a bucket or a millisecond count.
`error_type` is an error class or exception name (`ApiError`, `TypeError`, a Cognito exception name) — never a
message. Nothing a user typed rides: no names, emails, filenames, comment text, search terms or tokens.

**Collector allow-list delta for M9:** `feature`, `flow`, `step`, `attachment_count`, `attachment_upload_ms` — plus, by session-lead ruling after M9's build, the eight `browser.telemetry.dropped` count keys the browser already sends (`batches`, `items`, `rejected`, `exhausted`, `evicted`, `serialize`, `closed`, `last_status`), so the drops panel charts dropped items and reasons. Every
other key above is already in `base.yaml`'s browser list (confirmed by the plan review: all 21).

### 2.2 Coverage map (area → calls → event)

| Area | Calls | Event |
|---|---|---|
| Optimizer | the 22 mutations in `hooks/api/useOptimizer.ts` (schedules, CSV upload, process, expansion save, activities and rule preview, roles, settings, jobs, config-snapshot refresh) and the wizard's chained direct writes (`ReviewStep.tsx:174,181,186,191`: create + process activity, create role, create job) | `browser.feature.mutation` (`feature=optimizer`) — except `usePreflightJob`, `useRunJob` and the wizard's direct `runJob` (`ReviewStep.tsx:196`) → `browser.optimizer.run_triggered`, and the `fetchRunExport` caller (`components/features/optimizer/outputs/CanvasHeader.tsx:183`) → `browser.export.requested` |
| AD review | `hooks/mro/useAdReview.ts`: `useAdDispositionWrite`, `useClearAdDisposition` → `browser.ad_review.disposition_set`; `useRecomputeAdApplicability`, `useMaterializeAdCorpus` → `feature=ad_review` | as named |
| Automations | `useCreateAutomation`, `useUpdateAutomation`, `useDeleteAutomation` → `feature=automations`; `useRunAutomationNow` stays `browser.automation.run_triggered` (now with `department`); `useAutomationRuns` → `run_settled` | as named |
| Comments | `hooks/api/useComments.ts` create / update / delete / vote | `feature=comments` |
| Improvement | `useRunImprovementNow`, `useTriageFinding` | `feature=improvement` |
| Notifications | `components/features/notifications/NotificationBell.tsx:149` bulk mark-read (a direct call) | `feature=notifications` |
| Chat | `hooks/chat/useShare.ts` | `feature=chat` (`entity=chat`, `action=share`) |
| Document Hub | metadata edit, sharing-scope change, retry, delete (`DocumentHubPageContent` and its dialogs; the TanStack audit places the writes at `DocumentHubPageContent.tsx:758,798,827`) | `feature=document_hub` |
| Data discovery | `data-discovery/page.tsx` source create and archive; `jobs/[jobId]/page.tsx` rerun, retry failed batches, archive (level-1/level-2 starts stay `browser.discovery.job_started`); settles from a per-job status effect (E9.6) | `feature=data_discovery` |
| Settings (#19 completion) | invitations (`hooks/settings/useInvitations.ts`), operators and the operator registry (`useOperators.ts`), operator grants (`useOperatorGrants.ts`, `GrantOperatorDialog.tsx`), organization (`components/features/settings/organization/organizationSave.ts`), `deleteDepartment`, `deleteOperator`; the member update's double emission fixed | `browser.settings.mutation` |
| Auth | `RegisterView`, `ConfirmationCodeView`, `ForgotPasswordView`, `NewPasswordView`, `InviteAcceptView` | `browser.auth.flow` |
| Work orders | `components/features/chat/WorkOrderCarousel.tsx:110` export | `browser.export.requested` (`export_kind=work_orders`) |

`feature` ∈ {`optimizer`, `ad_review`, `automations`, `comments`, `improvement`, `notifications`, `chat`,
`document_hub`, `data_discovery`}. `entity` is the resource noun and `action` the verb (`create`, `update`,
`delete`, `upload`, `process`, `save`, `preview`, `refresh`, `archive`, `rerun`, `retry`, `share`, `vote`,
`mark_read`, `trigger`, `triage`, `recompute`, `materialize`, `grant`, `revoke`, `resend`, `accept`), snake_case,
from one closed map in code; E9 records the final (feature, entity, action) table in its notes. `flow` ∈ {`register`,
`confirm_signup`, `forgot_password`, `new_password`, `invite_accept`}; `step` ∈ {`submit`, `code_request`,
`code_confirm`, `preview`, `accept`}; auth `outcome` ∈ {`success`, `failure`, `challenge`}.

### 2.3 Areas covered by an existing signal (no new event; D9-13)

| Area | Why nothing new |
|---|---|
| Copilots landing tile choice | `browser.route.change` (`route_pattern_from=/copilots` → the chosen copilot) already records it |
| Help | route changes are the whole story (static content) |
| Analytics dashboard tabs, ranges, filters | each view fetches its panels; the fetch spans' `url.template` shows which panels are read — no panel asks for more |
| Notification bell open / click-through | open is UI state with no consumer; click-through is a route change; mark-read is a feature action (§2.2) |
| Chat UI state (filters, data view, report preview, new/past chat) and the display components (`NotamCard`, `WeatherCard`, `FilePreviewModal`/`SignedFilePreviewContent`, `DocumentSearch`, `MobileChatNavigation`) | spec §7.4 drops click-level interaction; their data arrives inside the traced turn and their fetches are traced; a new chat is the first turn with `is_followup=false` |
| Data-discovery table open | a route change |
| Optimizer solve / AD materialize completion | server-side truth (G9-34) |
| `window.open` / `<iframe>` loads | G9-29 |
| Rostering | owner ruling 1 |

## 3. Stream F9 — browser correctness + correlation

Each task: write the test first and watch it fail on `b87ced0` for the stated reason, implement, re-run, commit by
pathspec. Every task carries the master §11a logging-coverage checkbox: the touched modules' failure paths log at the
right level, with constant messages and bounded kwargs, and no silent swallow outside the telemetry modules' own
never-throw rule.

### F9.1 — No URL query, fragment or third-party path leaves the browser (G9-01, G9-41)
- **Files:** `lib/telemetry/exporter.ts` (the trace and log serializers are the single OTLP exit),
  `lib/telemetry/errors.ts` (`scrubMessage`), new test `tests/unit/telemetry/export-url-scrub.test.ts`.
- **Design (D9-7):** the pinned `@opentelemetry/sdk-trace-base` 2.11.0 has no `onEnding` hook (confirmed by the plan
  review), so a processor cannot rewrite a span after its instrumentation finishes; the exporter is the one place that
  sees every span and record from every instrumentation. Before serialization, every string attribute on spans, span
  events and log records whose value is a URL (absolute `http(s)://…` or root-relative) loses its query and fragment,
  and a URL whose origin is neither the page's nor the api's is reduced to scheme + host (S3 object keys and other
  third-party paths carry filenames and bucket layouts). Non-URL strings are untouched. `scrubMessage` also strips
  queries/fragments from URLs embedded in free text (error messages, log bodies). The fetch/XHR hooks keep producing
  `url.template`. The second exit — product facts to `/analytics/events` (`lib/telemetry/product-events.ts`) —
  carries templates and ids only by construction; the test asserts its posted bodies too.
- **Test (defect absence, not guard presence):** start telemetry with the REAL exporters over a fake transport (the
  `PostFn` seam), a jsdom `location.href` carrying `?invite=probe-token#frag`, a fake navigation entry and fake
  resource entries — one on the page origin with a query, one S3-shaped with a key path and an `X-Amz-Signature`
  query; issue one fetch to an api URL with a query; flush; decode every posted OTLP/JSON body (and any product-events
  body) and sweep ALL attribute values, event attributes and log bodies — no `probe-token`, no `X-Amz-`, no S3 key
  path, no URL-shaped value with a `?`/`#` suffix; `url.template` still present on the fetch span; the documentLoad
  and resourceFetch spans are PRESENT (the sweep must not pass by exporting nothing). Must fail on `b87ced0`.
- **Acceptance:** the sweep passes; the existing propagation, sampling and wire-shape tests still pass.

### F9.2 — Log bodies carry no user data, and a guard keeps it that way (G9-02, G9-12)
- **Files:** `lib/telemetry/events.ts` (`emitLog` passes the body through `scrubMessage`); `lib/api/settings-api.ts`
  (all 14 interpolated warn sites become constant messages — the emails and the tenant-authored department/role names
  are dropped outright, ids are dropped too (the settings record already carries entity/action), the error rides as
  the kwarg it already is); `.eslintrc.json` (`no-console` at error; a `no-restricted-syntax` rule requiring the first
  argument of `logger.warn` / `logger.error` / `logger.fatal` to be a string literal or an expression-free template —
  editor feedback; an override turning `no-console` off for `components/features/rostering/**` with ruling 1 in a
  comment); the non-Rostering console sites outside `app/api/` (`components/features/pdf-viewer/pdf-toc.tsx:172` → the
  logger; the debug prints at `lib/pdf/pdfjs.ts:230,261` and `hooks/pdf-viewer/use-pdf-navigation.ts:55` → deleted or
  `logger.debug`; the dev-gated sites in `lib/telemetry/provider.ts:150,326` and `lib/telemetry/product-events.ts:173`
  keep their disable comments, which now mean something). `handleApiError`'s conditional template is F9.3's.
- **Tests:** `tests/unit/telemetry/log-body-scrub.test.ts` (a warn whose body holds an email and a presigned URL ships
  masked); `tests/unit/telemetry/logger-message-constant.test.ts` — the guard that runs in every lane (`npm run lint`
  lints changed files only): an AST pass (the TypeScript compiler API — already a dev dependency) over `app/`,
  `components/`, `hooks/`, `lib/` asserting the first argument of every shipped-level `logger` call is a string
  literal or an expression-free template (an allow-form check: it also rejects variables, conditionals and
  concatenations, across line breaks); Rostering exempt by path. It must fail on `b87ced0` with exactly the 14
  settings sites + the `handleApiError` conditional, and pass after.

### F9.3 — API-error records are distinct and linked to their trace (G9-09, G9-15, G9-39)
- **Files:** `lib/api/utils.ts` (`ApiError` gains optional `traceId`, `requestId`, `urlTemplate`); one shared
  "error from a failed response" helper used by every `new ApiError(` site in `lib/api/utils.ts`, the two `apiError(…)`
  sites in `lib/api/fetch-utils.ts` (`:188`, `:235`) and the two in `lib/api/optimizer-api.ts` (`:803`, `:820`), filling
  the reference (F9.4's source order), `X-Request-ID` when exposed, and the request's `url.template`;
  `lib/api/error-handler.ts` (`handleApiError` logs ONE constant message with `url.template`,
  `http.response.status_code`, the error, and its optional `context` as a kwarg); `lib/telemetry/logger.ts` (`ship`:
  the dedupe key adds `url.template` and status when present; a record about an error that carries a trace id is
  emitted in that trace's context — a non-recording span context built from the trace id and a freshly minted span id,
  because the SDK only accepts a valid SpanContext — through the optional context parameter F9 adds to
  `emitRecord`); `lib/api/client.ts` (drop the two URL `info` lines).
- **Tests:** two failing endpoints within 15 s ship two records; the same endpoint and status twice ships one; the
  record carries `url.template`, status and the failed request's trace id; an optimizer-api failure carries the same
  fields.

### F9.4 — A support reference on every failure the shared handler or a boundary shows (G9-04, G9-05, G9-40)
- **api-obs9:** `flynapse_api/middleware/cors.py` adds `X-Request-ID` and `X-Trace-Id` to `expose_headers`;
  `flynapse_api/main.py` moves `setup_trace_id_header(app)` from inside the auth layer to just inside CORS (added after
  the request-id middleware, before CORS), so every response the gateway returns — auth's 401/403, the rate limiter's
  429 and auth's converted 500s included — carries `X-Trace-Id` (the gateway OTel middleware is outermost, so a span is
  active there); the order comments in `main.py` are updated. New test
  `tests/middleware/cors/test_correlation_headers_on_every_response.py`: through the REAL middleware order (the real
  app if it imports in the bundle env, else a minimal app wired by the same setup functions in the same order with the
  real `UniversalAuthMiddleware`), with an allowed `Origin`: a route that raises → 500 with the allow-origin header,
  `X-Trace-Id`, `X-Request-ID`, and both names in `Access-Control-Expose-Headers`; an auth-refused request → 401 with
  `X-Trace-Id`. It must fail on `a19a931` (no `X-Trace-Id` on the 500).
- **dashboard — the reference source (D9-4):** the trace id of the request's own trace: primarily the `traceparent`
  the fetch instrumentation injected — the pinned `instrumentation-fetch` 0.222.0 `_addHeaders` replaces the init
  object's `headers` with a `Headers` instance carrying it (`fetch.js:88-92`), so `fetchWithAuth` keeps its init
  object and reads it after `fetch` settles (verify the init object is the caller's, not a copy, and pin the behaviour
  with a test through the real instrumentation); fallback the response's `X-Trace-Id`. Network failures (no response)
  therefore get a reference too.
- **dashboard — where it shows:** `lib/telemetry/errors.ts` — `reportError` returns the trace id its record was
  emitted under (the active span's when valid — a failure inside a chat turn links to that turn — else a fresh random
  non-recording span context); a repeat suppressed by the 15 s fingerprint dedupe returns the trace id of the record
  that DID ship (the dedupe map keeps it), so a shown reference always has a record behind it.
  `lib/telemetry/ErrorBoundary.tsx`, `components/shared/FeatureErrorFallback.tsx` show "Reference" with the id and a
  copy button, only while telemetry is running (the honest-copy rule). `lib/api/error-handler.ts` — toasts for the
  server, network and unknown classes carry the reference with a copy action; 4xx validation/permission toasts are
  unchanged. The provider's existing request-id read now populates `request_id` (extend
  `tests/unit/telemetry/provider-propagation.test.ts` with a response carrying `X-Request-ID`).
- **Tests:** the fallback's reference equals the exported record's trace id (fake exporter), also for a deduped
  repeat; a 500's toast carries the request's trace id; a network failure's toast carries one; no reference renders
  when telemetry is not started.

### F9.5 — Telemetry is running before the first request (G9-08)
- **Test first, on the real tree:** render the real `AppProviders` with a session token present and the real
  boot-time query hooks (whatever `AuthContext` / `PermissionProvider` start on mount — `fetchWithAuth`'s
  `makeRequest` reaches `fetch` with no await, so a query started in a subscribe effect can fetch before
  `TelemetryProvider`'s effect), over the fake transport. Rule separately on (a) the first bootstrap fetch has a span
  and (b) an error thrown during the first mount reaches `browser.error`. Each that fails on `b87ced0` gets the fix;
  each that already passes is disproved — record it in the notes and do not change that path.
- **Files (for what is proved):** a side-effect boot module under `lib/telemetry/` imported FIRST by
  `components/providers/AppProviders.tsx`: in the browser it starts the provider and installs the global error handlers
  and Web Vitals at module evaluation, idempotently; `TelemetryProvider`'s effect keeps route telemetry, unload/history
  handlers and the app-boot record, and calls start again as a no-op fallback. Verify that `window.__RUNTIME_CONFIG__`
  (set by an inline script at the top of `<body>` in `app/layout.tsx`) and `API_CONFIG.BASE_URL` resolve at module
  evaluation; where they may not, boot defers to the effect and the notes say so.
- **Acceptance:** the proved cases pass after the change; the idempotency and strict-mode tests still pass.

### F9.6 — A root error page that reports (G9-07)
- **Files:** `app/global-error.tsx` (its own `<html>`/`<body>`; calls `startTelemetry()` — idempotent — BEFORE
  reporting through `reportError` with `error_kind=global`, flushes telemetry, shows the reference and a Reload button,
  no raw message outside development); `lib/telemetry/errors.ts` (`ErrorKind` gains `global`). A root layout that
  fails during SSR ships `global-error` without `__RUNTIME_CONFIG__`, so the client cannot reach the api — that case
  belongs to N9.4's `onRequestError` (`routeType: 'render'`); the page still renders and reports what it can.
- **Test:** render the page with an Error while telemetry is NOT started; assert exactly one exported `browser.error`
  with `error_kind=global` and that its reference is shown. Next renders `global-error` in production builds only; P9
  forces it once against `next start`.

### F9.7 — Chat attachment uploads belong to their turn (G9-11; D9-14)
- **Files:** `hooks/chat/useMroMessageStream.ts`, `usePilotMessageStream.ts`, `useCrewMessageStream.ts` (and
  `useCopilotDockChat.ts` if it uploads); `lib/telemetry/chat-turn.ts` (the handle records `attachment_count` and
  `attachment_upload_ms`); `lib/api/fetch-utils.ts` (`fetchWithAuth` captures the active context synchronously at
  entry and re-enters it for its post-refresh retry, `:179-184`, so a retried request keeps its parent — for every
  traced flow, not only uploads).
- **Constraint:** the web SDK's default `StackContextManager` does not carry context across `await`s (confirmed by the
  plan review), so each upload must run inside `turn.runInContext` at the call closest to its `fetch` — inside the
  api-client method if that method awaits before fetching — exactly as phase-4 D8 did for the stream call. An upload
  failure ends the turn with `outcome=error` and `error_type`.
- **Test:** a turn with one image and one file attachment exports both upload CLIENT spans as children of
  `browser.chat.turn` (same trace, parent = the turn span) and the turn carries both new attributes; a failing upload
  ends the turn as `error`; a 401-then-refresh upload keeps its parent. Proved through the real fetch path.

### F9.8 — Hygiene leftovers (G9-13, G9-14)
- **Files:** `.env.example` (drop the stale line); `lib/api/utils.ts` (delete the dead generator);
  `tests/unit/telemetry/legacy-module-absent.test.ts` (the roots gain the repo's env example files; the forbidden list
  gains the generator's function names).

### F9 close
Full unit lane, `tsc`, eslint on touched files, the api test lane for the touched middleware; notes; the reviewer's
brief in §10.

## 4. Stream E9 — event coverage

Same task discipline as F9. Every emitter gets a SITE-level test through the real hook or method against a stubbed
transport (the `tests/unit/telemetry/settings-mutation-sites.test.ts` pattern) asserting **exactly one** record per
user action with the right attributes and no off-list key — for success and for failure.

### E9.1 — Catalogue members and the one-emission rule (D9-17)
- **Files:** `lib/telemetry/events.ts` (the §2.1 names, allow-lists, typed emitters, and timing wrappers for direct
  writes — `withFeatureMutation` mirrors `withSettingsMutation`; an auth-flow timer mirrors `startLoginTiming`);
  `lib/telemetry/mutation-meta.ts` (the `MutationTelemetryEvent` union gains `browser.feature.mutation`,
  `browser.optimizer.run_triggered`, `browser.ad_review.disposition_set`); `tests/unit/telemetry/events-catalogue.test.ts`
  (the name → keys table equals §2.1, `browser.telemetry.dropped` included).
- **One emission per user action.** A TanStack mutation emits through `meta.telemetry` and its `mutationFn` calls
  only non-emitting functions. A direct write emits once: inside the API-layer method when every caller of that method
  is a direct write (the existing `settings-api` convention), otherwise through a wrapper at the call site (e.g. the
  wizard chain calls optimizer functions that hooks also call — those stay non-emitting). E9 does not convert direct
  writes to `useMutation` (§1b).
- **Guards (tests/unit/telemetry/):** a coverage sweep — every `useMutation` in the §2.2 files declares
  `meta.telemetry` or is named in the test's exemption list with its reason (e.g. its `mutationFn` calls a
  self-emitting API method); a double-emission guard — an AST pass (TypeScript compiler API) collecting the functions
  called inside each `mutationFn` of a mutation that declares `meta.telemetry` and asserting none is in the pinned set
  of self-emitting API methods.

### E9.2 — Optimizer (G9-21, G9-35, #22 optimizer, #23)
The 22 hooks get `meta.telemetry` with the closed (entity, action) pairs; preflight and run emit
`browser.optimizer.run_triggered` (`phase`, `job_id`, `accepted`/`rejected`, `preflight_warning_kind` from the
preflight response); the wizard chain's direct writes (create + process activity, create role, create job, run) are
wrapped at the call site — run as `run_triggered`, the rest as `feature=optimizer`; the `fetchRunExport` caller emits
`browser.export.requested` (`export_kind=optimizer_run`, `format`, `row_count_bucket` when the response says,
duration, outcome).

### E9.3 — AD review (G9-20, #24)
Disposition write and clear emit `browser.ad_review.disposition_set` (`cleared` for the clear path;
`had_prior_disposition` from the row the user acted on; `source` from the calling surface — the hook takes it as a
variable, the table and the dialog pass theirs); recompute and materialize → `feature=ad_review`.

### E9.4 — Settings (#19 completion, G9-19, G9-38)
Invitations (create, revoke, resend), operators (create, update, delete), operator grants (grant, revoke), the operator
registry, organization save, `deleteDepartment`, `deleteOperator` → `browser.settings.mutation` (TanStack meta or
`withSettingsMutation`, whichever the call site's path already uses, under the one-emission rule). The member update
in `hooks/settings/useTeamData.ts` emits one record per click, not two.

### E9.5 — Other feature actions (G9-23, G9-37)
Automations CRUD, comments, improvement, notifications bulk mark-read, chat share, Document Hub metadata/sharing/retry/
delete, data-discovery source create/archive and job rerun/retry/archive → `browser.feature.mutation`.
`useRunAutomationNow` sets `department` where the automation carries one.

### E9.6 — Long-running settles (#16, #18)
- `browser.automation.run_settled`: only for runs this session triggered — the run-triggered path records run id and
  trigger time in a session-scoped registry; `useAutomationRuns` emits once per run on the first terminal status it
  observes; `observed_wait_ms` = observed − triggered.
- `browser.discovery.job_settled`: an effect that tracks each polled job's status by job id and emits once per job when
  it first leaves in-progress (`poll_count`, `observed_wait_ms` from the first poll) — not the `refetchInterval`
  callback, which re-runs on every observer update and sees list-level state.
- **Tests:** a run triggered then polled to a terminal status emits exactly one record; a run this session did not
  trigger emits none; a remount does not double-emit; two jobs settling in one poll emit two records.

### E9.7 — Auth flows (G9-23)
`browser.auth.flow` at the five views with the §2.2 flow/step vocabulary; `error_type` is the Cognito/api exception
name; nothing user-entered (email, username, code, token) rides. The public pages ship through the public ingest
(anonymous sentinel) as today.

### E9.8 — Work-order export (#22 work orders)
`WorkOrderCarousel`'s export emits `browser.export.requested` (`export_kind=work_orders`, `format`, duration, outcome).

### E9 close
As F9; the final (feature, entity, action) table goes into the notes.

## 5. Stream N9 — Next.js server side (D9-10, D9-19)

**The seam (applies to N9.1–N9.4).** `lib/telemetry/logger.ts` is imported by ~71 client modules, so it must never
import a server module. The request-context store (Node `AsyncLocalStorage`, which Next 15.2.4 also exposes as
`globalThis.AsyncLocalStorage`) and the server log sink live on `globalThis`, created once: Next compiles
`instrumentation.ts` and the route handlers as separate bundles, so a module-level singleton would exist once per
bundle. The server-only modules register the sink when they load (the route-wrapper module and `instrumentation.ts`'s
`register()`, guarded to the Node.js runtime); `logger.ts`'s server branch only looks the global sink up and falls back
to today's behaviour when none is registered. Output goes through `process.stdout.write` / `process.stderr.write`,
never `console` (production builds strip `console.*`, `next.config.mjs:22`).

### N9.1 — Request context
- **Files:** new server-only `lib/telemetry/server-context.ts`: the global store {trace id, `traceparent`,
  `tracestate`, route template, method}; a strictly validated W3C `traceparent` (version `00`, non-zero ids) is taken
  from the inbound request, otherwise a new one is minted (random ids, sampled flag) so every hop has a trace id; a
  helper returns the headers to forward upstream.
- **Tests:** a valid inbound header is kept verbatim; malformed and all-zero ones are replaced by a valid minted one;
  two module instances (simulating two bundles) share one store.

### N9.2 — Route wrapper and trace forwarding (G9-16)
- **Files:** a `withRoute(routeTemplate, handler)` wrapper applied to every exported method of the 12 route files under
  `app/api/`; the handler runs inside the context; every upstream `fetch` forwards the trace headers (beside the
  existing `X-Session-ID`); an uncaught error becomes one structured error line and a generic 500 JSON body (no
  internals).
- **Tests:** a fake upstream `fetch` receives the inbound `traceparent` (or the minted one when none came); a throwing
  handler answers 500 and writes one error line carrying the trace id and route. **Sweep test:** every exported HTTP
  method in `app/api/**/route.ts` is wrapped — a new route cannot ship dark.

### N9.3 — Structured server log lines
- **Files:** new `lib/telemetry/server-log.ts` (the sink): outside development, one JSON object per line — `ts`,
  `level`, `msg` (through `scrubMessage`), `service` = `dashboard-server`, `route`, `method`, `trace_id` from the
  context when present, plus the bounded kwargs under the logger's rules (sensitive keys redacted by name, strings
  capped, no nested objects); development keeps a readable echo; `info`/`debug` stay suppressed in production.
  `lib/telemetry/logger.ts`'s server branch looks up the global sink (one hunk, §1b).
- **Tests:** with the sink registered and production mode, the captured stdout/stderr is one parseable JSON line per
  call with the trace id and redaction applied; without a registered sink the server branch behaves as today; the
  client-side path of `logger.ts` imports nothing server-only (a static import-graph assertion). N9 close runs
  `npm run build` once — the bundle proof a unit test cannot give.

### N9.4 — `instrumentation.ts`
- **Files:** `instrumentation.ts` at the repo root (no `src/`): `register()` registers the server sink on the Node.js
  runtime and is the documented seam for SSR export (G9-18); `onRequestError(error, request, context)` writes one
  structured error line (`routePath`, `routeType`, method, digest, error type, scrubbed message, trace id parsed from the
  request's headers) — the SSR root-layout failures F9.6 cannot report land here. The Next 15.2.4 signature is in
  `node_modules/next/dist/server/instrumentation/types.d.ts` (confirmed by the plan review).
- **Test:** calling the exported hook directly writes the expected line; a malformed header does not throw.

### N9.5 — Upstream-body and route-log hygiene (G9-17, G9-12)
- **Files:** content-stream logs the status plus a bounded upstream error code (the S3 `<Code>` element or the api's
  error code) instead of raw bodies; the other 11 routes' log kwargs are reviewed — comment routes must not log comment
  text, tenant routes must not log organization fields — and fixed; the commented-out console line at
  `app/api/documents/[id]/route.ts:269` is deleted.
- **Test:** content-stream with a fake S3 error body naming a bucket and key logs neither string.

### N9 close
As F9, plus `npm run build`.

## 6. Stream M9 — collector, boards, alarms (stacked on phase-8 D8, §1)

### M9.1 — Collector allow-list and body masking (G9-03; D9-8)
- **Superseded at build (2026-09-11):** M9 proved the pinned `redaction` processor already masks string log bodies, so no `transform` was added; the property is pinned by tests (G9-03). The telemetry-drop count keys join the allow-list (§2.1).
- **Files:** `deployment/otel/base.yaml` — the browser allow-list (trace and log statements) gains the five §2.1 keys; a
  log-body masking step with the `redaction.blocked_values` patterns (email, bearer, JWT, AWS access key id) is added
  to the browser AND backend log pipelines of every profile (`backend-oss.yaml`, `backend-aws.yaml`,
  `backend-azure.yaml` list their pipelines' processors — the step goes after the allow-list, before `redaction`). It is
  a `transform` processor with `replace_pattern` on the log body: the pinned 0.160.0 `redaction` processor documents
  body handling for map bodies only, and browser and loguru bodies are strings. `deployment/otel/validate.sh` passes
  for every profile.

### M9.2 — Collector tests (G9-27)
- `tests/integration/otel/test_collector_base_config.py` and the profile test pin the five keys and the masking step in
  every log pipeline of every profile.
- The `OTEL_COMPOSE_SMOKE=1` smoke posts one browser log record (an email and a presigned URL in the body, a stray
  attribute key) and one backend record (an email in the body) through the `oss` collector and asserts what reaches the
  sink: body masked, stray key gone, allow-listed keys kept. If the smoke cannot read Loki, assert through a file/debug
  exporter in the smoke overlay.

### M9.3 — Endpoint dimension for browser API latency and failures (G9-26; D9-9, D9-15)
- `deployment/observability-local/tempo.yaml` `span_metrics.dimensions` gains `url.template` only — a browser-only
  attribute (backend spans leave the label empty, so backend series do not multiply), bounded by the route-pattern
  table with its `/unmatched` fallback. HTTP status is NOT added as a dimension: the backend sets
  `http.response.status_code` on every span (new semconv), so it would multiply every backend series; failures come
  from the intrinsic span `status_code` (ERROR), and the HTTP status is a Tempo search drill-down. README note on
  cardinality.
- `fn-frontend` panel "API latency as the browser sees it" gains a per-template breakdown; a new "Browser API failures
  by endpoint" panel (errors are always kept, so failure counts are exact; 2xx spans are sampled at 10%, so success
  counts are not — the panel says so).

### M9.4 — Grafana `fn-frontend` panels
- `deployment/observability-local/grafana/provisioning/dashboards/flynapse/frontend.json` gains LogQL panels over
  `{service_name="dashboard"}`: Feature actions (feature × action × outcome); Feature action failure ratio by feature;
  Auth flows (flow × step × outcome); Optimizer runs triggered (phase × outcome); Exports (export_kind × outcome); AD
  dispositions (disposition × outcome); Long-running observed wait p75 (automation and discovery); Settings changes by
  entity; Telemetry drops (`browser.telemetry.dropped` — the catalogued event's consumer). New panels carry the phase-6
  DARK marker until P9 sees them (the `test_grafana_dashboards.py` marker grammar).
- `deployment/otel/dashboards/CATALOGUE.md` §5: signals, panels and the `aws` Logs Insights equivalents.

### M9.5 — `aws` dialect (G9-24; D9-11)
- `iac-obs9`: `dashboards/frontend.json.tftpl` gains the same panels as Logs Insights widgets (RE-VERIFY field paths
  after probe B1b, like every `aws` widget).
- Browser alarms are **documented, not authored**: the catalogue's alarm translation table and
  `docs/runbooks/observability/aws-profile.md` gain exact rows for BrowserErrorRateHigh and WebVital LCP/INP/CLS p75
  poor — the CloudWatch Logs metric-filter pattern each needs, its metric, statistic, threshold (the Loki rules'),
  period and the SNS target — marked blocked on the owner's alarm-dialect ruling (phase-6 T12) and probe B1b. No
  `aws_cloudwatch_metric_alarm` or metric filter lands in Terraform this phase.
- `terraform fmt -check`, `terraform validate`, every body parses.

### M9.6 — DARK flip (after P9)
In the same change, the failure-ratio panels (Grafana and CloudWatch) exclude `error_type="MutationRefusedError"` — the TanStack helper's client-side permission refusals, which send no request — and chart refusals as their own series. Remove "DARK until …" from the `fn-frontend` panels, the four Loki browser rule descriptions, the CloudWatch widget
titles and CATALOGUE §5 — **only for signals P9 observed**; anything P9 could not see keeps its marker with a dated
note. The guards in `test_grafana_dashboards.py` / `test_alert_rules_layout.py` pass either way.

### M9 close
Full `tests/integration/otel/` lane (static + both smokes + rules check), `validate.sh`, `terraform validate`; the guard
fixture lists extend phase-8's (stacked base).

## 7. P9 — live probe (session lead, after all four streams pass Opus review)
Integration tree `/home/aditya/Code/dashboard-obs9-probe` = `agent_sdk` + `obs9-browser` + `obs9-events` +
`obs9-server` merged locally (it also rehearses the gate's merge conflicts; it is deleted afterwards and never merged);
api from `api-obs9` via the bundle env; the `oss` collector + LGTM stack from `copilot-mro-obs9` (the dev-stack skill
and the 2026-09-05 probe recipe; loopback-remapped ports); `next build` + `next start` (production mode, so
`global-error`, `removeConsole` and the production log paths are the real ones). **Probe-tree-only edits, never
committed and listed in the results:** the export sampling ratio pinned to 1 (a 2xx root span is otherwise dropped
90% of the time, which would make checks 5 and 6 unable to tell "untraced" from "sampled out"); forcing hooks for a
warn with an email in its body, a render error, and a root-layout throw. Checks, each with evidence banked in
`.dev_runs/obs9-probe-<date>/`:
1. Loki carries `browser.web_vital`, `browser.error`, `browser.route.change`, `browser.app.boot`, and at least one of
   each new §2.1 event from exercised flows: an optimizer job create + run + export, an AD disposition, a settings
   invitation, a comment, a register attempt, a work-order export, a Document Hub action, a data-discovery archive, an
   automation run and a discovery job each driven to any terminal status (a failure counts).
2. A page opened with `?invite=probe-token#frag` and a presigned S3 preview: FIRST the documentLoad and resourceFetch
   spans for that load are present in Tempo with a clean `url.full`; THEN no browser span or record anywhere in
   Tempo/Loki contains `probe-token`, `X-Amz-`, an S3 object key or a queried URL.
3. The forced warn with an email arrives masked; a backend log line with an email arrives masked.
4. A forced api 500 shows a toast whose Reference opens the server trace in Tempo; a forced network failure's toast
   Reference opens the browser span; a forced render error's fallback Reference finds its `browser.error` record in
   Loki; the forced root-layout throw reports once from `global-error`.
5. A Next route call (content-stream or tenant) → the api SERVER span is a child of the browser fetch span; the
   `next start` stdout carries one JSON line with the same trace id for a forced route failure; a forced SSR render error writes one `onRequestError` line; a forced content-stream
   upstream failure's line carries a status and code, no body, bucket or key.
6. The first auth/bootstrap request of a cold load has a span (F9.5, for what it proved).
7. A chat turn with an image attachment (with Bedrock unavailable the turn ends as `error` — the upload spans'
   parentage is what is checked): both upload spans are children of `browser.chat.turn`.
8. Prometheus has span metrics with `url_template` for `service="dashboard"`, and Tempo's active-series demand stays well under the 100000 `max_active_series` cap (M9's 20–35k baseline is an estimate — read the generator's demand metric to confirm the headroom).
9. `fn-frontend` renders every panel; then M9.6 flips what was seen.
Teardown by port and `compose down -v`; results and any fix passes recorded in §11.

## 8. Review design — two phases

**Phase A (now, Opus 5):** one fresh adversarial reviewer per stream (F9 includes the api change), briefed with the
stream's section + §0 + §2 + §8a + the diff, running the suites itself and trying to break the work — defect absence,
not guard presence; every test must fail without its fix. Triage, fix pass, re-verification, brief into §10.

**Phase B (Fable, when the limit returns; after the phase-8 chunks R0–R5):** five bounded chunks, one fresh Fable agent
each, in merge order — R6 **design** (§0, §2, §8a, the stream split and file ownership) → RC the owner's TanStack conversion (design + code, from its own plan; merged into `agent_sdk` first, after which each obs9 dashboard branch merges `agent_sdk` and re-runs its lanes) → R7 F9 (dashboard + api) → R8
E9 → R9 N9 → R10 M9 (copilot-mro `deployment/**` + iac). A chunk's merge follows its verdict: dashboard branches
`--no-ff` into `agent_sdk` (F9, E9, N9 in that order, full unit lane + `tsc` after each), api into `langgraph-merge`,
copilot-mro `deployment/**` into `langgraph-merge`, iac into `main` — M9's two branches after phase-8 R5 has merged
their D8 bases (if Fable changed D8 at R5, merge the new D8 tips into the obs9 branches and re-run the lanes before
R10). Nothing merges on an Opus-only verdict; a design change at R6 rescopes the affected stream (fix pass on
whatever model is available) before its code chunk runs. After R10: a short re-probe of P9 checks 2, 4 and 5 on the
merged mainlines.

### 8a. Design decisions for R6 (Fable rules keep / change / reject on each)

| # | Decision (as planned) | Alternatives considered | Why this one |
|---|---|---|---|
| D9-1 | One generic `browser.feature.mutation` (feature, entity, action, outcome) for every non-settings feature action; specific events only where research 07 defined richer attributes (#16, #18, #22, #23, #24) | (a) one event name per area (≈10 new names); (b) no events where no panel reads them | one name keeps the catalogue small and every action countable on one panel; the specific names stay where their attributes answer questions the generic one cannot (wait time, disposition, export kind) |
| D9-2 | `browser.auth.flow` for the five non-login auth steps; `browser.auth.login` unchanged | (a) widen `browser.auth.login` with a `flow` attribute; (b) nothing — the public-route fetch spans show failures | (a) changes an existing event's meaning mid-series; (b) cannot tell "user gave up" from "server refused", which is the signup-funnel question |
| D9-3 | The five LATER rows are built now (roster export excluded), superseding the phase-4 v1 deferral on the owner's 2026-09-11 request; the delta is put to the owner non-blocking | keep them deferred and only record them in Future Improvements | the owner asked for every gap except Rostering; three of the five are the Optimizer/AD coverage the audit ranked |
| D9-4 | The support reference is the W3C trace id of the request's own trace — read from the `traceparent` the fetch instrumentation injected into the request init (pinned by a test), falling back to the response's `X-Trace-Id`; render errors show the trace id their `browser.error` record was emitted under | (a) the request id; (b) a short random code stored as a new attribute; (c) `X-Trace-Id` only; (d) show nothing | the trace id opens Tempo (server trace + the kept ERROR browser span) and Loki (records carry it); (c) cannot reference a network failure, which has no response; a request id finds server logs only; a new attribute needs another allow-list key |
| D9-5 | The api keeps minting `X-Request-ID` and ignores an inbound one; the browser only reads it back | honour a well-formed inbound id | `traceparent` is the correlation channel; an honoured client id would let a caller choose server log keys, and nothing needs it |
| D9-6 | Telemetry starts at module evaluation of a boot module imported first by the client providers, only for the cases F9.5's first test proves on the real provider tree; the effect stays as the fallback | (a) upgrade Next to ≥ 15.3 for `instrumentation-client.ts`; (b) an inline boot script in the layout; (c) change nothing | (a) is a framework upgrade outside this phase; (b) runs before the bundle exists; (c) is right for any case the real-tree test disproves |
| D9-7 | URL queries and fragments are stripped, and third-party URLs reduced to scheme + host, at the exporter (the single OTLP exit) for every span and log attribute | per-instrumentation `applyCustomAttributesOnSpan` hooks; a span processor (`onEnding` does not exist in the pinned 2.11.0) | the exit sees every instrumentation, including ones added later; per-hook fixes miss the next instrumentation |
| D9-8 | Log bodies: scrubbed in the browser (`scrubMessage`), a constant-message guard (AST test + lint), and masked again in the collector by the existing `redaction` processor (M9 proved it masks string bodies; no `transform` added) on the browser AND backend log pipelines of every profile | (a) browser only; (b) collector only; (c) collector browser pipeline only; (d) the `redaction` processor's body support | two independent lines of defence, as spec §3.3 promises; the backend gets the same mask because its bodies have the same exposure — Fable may narrow it to (c); (d) was first rejected on a wrong premise (map bodies only) — M9 disproved it, so (d) is what is built |
| D9-9 | Handled-inline API failures (`suppressGlobalError`) stay unlogged; their signal is the always-kept ERROR fetch span, charted by endpoint via Tempo span metrics | log each at warn | many handled failures are expected states (not-found-yet, polling); a record per occurrence is noise, and the span already carries the template |
| D9-10 | Next server side: trace forwarding + request context + JSON log lines + `onRequestError` now; OTLP export (Node SDK) waits for the Amplify reachability probe | ship a Node OTel SDK now | spec §3.4 defers SSR export until Amplify can reach a private endpoint; forwarding restores the browser → api trace without it; no new dependency |
| D9-11 | `aws` browser alarms are documented (exact filters, thresholds, SNS target) and blocked on the owner's alarm-dialect ruling and probe B1b; no Terraform alarms this phase | (v1 of this plan) author them behind a variable defaulting off | phase-6 T12 left a three-way owner ruling open whose third option is "defer aws alerting"; authoring alarms, even switched off, pre-empts it, and the field paths are unverified until B1b |
| D9-12 | Rostering excluded; its console calls exempted by an ESLint override | fix them anyway | owner ruling 1: demo code, not instrumented |
| D9-13 | The §2.3 areas get no new event | an event per UI gesture | spec §7.4 drops click-level interaction; each area's question is already answered by route changes, fetch spans, a feature action or server-side truth |
| D9-14 | Chat attachment uploads run inside the turn span; the turn records `attachment_count` and `attachment_upload_ms`; no separate upload event | emit `browser.upload.started` + `upload_finished` for attachments | the `upload_finished` product fact means Document Hub uploads in the product views; mixing chat attachments would change its meaning, and the turn is where attachment time matters |
| D9-15 | Tempo span metrics gain the `url.template` dimension only; failures use the intrinsic span status | (a) also `http.response.status_code`; (b) a browser metrics pipeline (MeterProvider + exporter) | (a) multiplies every backend series (the backend sets it on every span under new semconv); (b) is a new browser dependency; `url.template` is browser-only and — after the M9 review found it only id-collapsed (`lib/telemetry/route-pattern.ts` collapses uuid/hex/digit/session segments; AD numbers and table ids pass through) — bounded by F9's fix pass (a stricter id rule with tests) plus a Tempo `max_active_series` cap; an explicit API template table is the complete solution (§9) |
| D9-16 | Three dashboard streams in parallel on separate branches with per-hunk file ownership (§1b), merged in a fixed order | one sequential dashboard stream | reviewable per concern and about three times faster; conflicts are confined to named hunk boundaries and rehearsed by P9's integration tree |
| D9-17 | One emission per user action: TanStack mutations via `meta.telemetry`; a direct write once — in the API-layer method when every caller is direct, else at the call site; an AST guard proves no `meta.telemetry` mutation calls a self-emitting method; E9 converts no direct write to `useMutation` | (a) E9 converts the TanStack audit's 34 writes itself; (b) call-site wrappers everywhere | (a) brings pending-state, invalidation and cascade behaviour changes that are that audit's scope and the owner's call; (b) leaves every later conversion to remember to remove a wrapper; the rule keeps counts right whichever way each site ends up |
| D9-18 | M9's branches are stacked on the phase-8 D8 branches (merges `9976fa7c`, `9231863`) | branch from the mainlines and rebase after R5 | M9 edits the same catalogue, guard and runbook files and extends their fixture lists; stacking removes the conflict and R10 already follows R5 |
| D9-19 | Server log lines go through `process.stdout/stderr.write` via a sink and a request-context store on `globalThis`, registered by the server-only modules; `logger.ts` never imports a server module | import a server-log module from `logger.ts`'s server branch; `console` output | `logger.ts` is in ~71 client modules (a server import breaks or bloats the client bundle); separate server bundles would each get their own module singleton; production builds strip `console.*` |

### 8b. Phase A close — gate agenda
_(filled at Phase-A close: branch tips, suite evidence, merge mechanics per chunk)_

## 9. Future Improvements
- **SSR OTLP export (G9-18).** Missing: route-handler spans and server logs in Tempo/Loki. Deferred by spec §3.4 until
  Amplify WEB_COMPUTE can reach a private endpoint (master §13 probe). Complete solution: `instrumentation.ts`
  `register()` starts a Node OTel SDK exporting to the api's authenticated ingest with a service credential (or a
  private collector if Amplify gains VPC reach); N9's request context becomes the span parent. Until then, a trace the Next hop minted (no inbound `traceparent`) shows its api span with a parent Tempo never receives.
- **Raw `fetch` without `X-Session-ID` (G9-30).** Authenticated raw calls (`optimizer-api.ts:760`,
  `improvement-api.ts:333`, `lib/api/utils.ts` helpers) skip `fetchWithAuth`, so server logs lack the session binding
  for them. Complete solution: route every authenticated call through `fetchWithAuth`; the public-page calls stay
  session-less by design. Deferred: it changes the auth transport (token refresh) outside telemetry.
- **Direct `toast.error` sites carry no reference (G9-39).** 79 components toast failures themselves, bypassing
  `handleApiError`. Complete solution: one shared toast helper that renders the error's reference, and a sweep that
  moves those sites onto it (or onto `handleApiError`). Deferred: it touches most feature files, colliding with E9 and
  the TanStack audit's conversions; do it after both land.
- **App ↔ collector allow-list parity guard.** The browser keys live in `events.ts` and in `base.yaml`'s regex, kept in
  step by hand ("never unilaterally"). Complete solution: a generated shared key list or a cross-repo parity test.
  Deferred: cross-repo test plumbing across worktrees; P9 check 1 is this phase's proof.
- **Span-metric success counts are sampled.** 2xx browser spans are kept at 10%, so per-endpoint success rates from span
  metrics are biased; exact server-side rates already exist from the api's `http.server.request.duration`.
- **Exact telemetry-drop counts.** The exporter sends cumulative per-tab totals (`resetDropped` has no caller), the reason keys count batches not items, and the trace and log exporters share one event with no signal key — so the drops panel reads a per-session max (a lower bound). Complete solution: send deltas plus an allow-listed `signal` key, then sum per report.
- **Logger guard blind spots (F9 re-verification P3).** The constant-message guard and its ESLint rule miss a logger reached through dynamic `import()` (`(await import(…)).logger.error(…)`), through `require(…)` (`no-require-imports` is off) or from a `.js`/`.jsx`/`.mjs`/`.cjs` source (`allowJs` is on); none exists today. Complete solution: flag any `import()` or `require()` of `lib/telemetry/logger` and extend the scan to those extensions under `app`, `components`, `hooks`, `lib`.
- **An explicit API template table for `url.template`.** Id-collapsing (F9 fix pass) plus the Tempo series cap bound the dimension; the F9 re-verification showed letter-only values still pass as route words (`work_orders`, `akj`, `faa`, `tenant-akasa`, a bare table name in `/jobs/{id}/tables/`) — mixed values (`2024-12-05`, `A320`, `run-7`, `john.doe`) collapse correctly; a table built from the api's route catalogue, with an `/unmatched` fallback like the page table, would make it exact.
- **aws browser alarms (D9-11)** — author the documented filters and alarms once the owner rules on the alarm dialect
  and B1b verifies the stored field paths.
- **Call-site wrappers inside a future `useMutation`.** D9-17's AST guard covers API-layer emitters; a later conversion
  that moves a call-site-wrapped write into a `mutationFn` and also adds `meta.telemetry` would double-count until a
  site test catches it. Complete solution: the conversion removes the wrapper in the same change (named in the TanStack
  audit's checklist when it is executed).

## 10. Review briefs (Phase A output; input to Phase B)
### Stream M9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY** after one fix pass and re-verification; four P3 nits in a final mini pass)
Scope: copilot-mro-obs9 `9976fa7c..6984d47b` (11 commits, only `deployment/**`, `tests/integration/otel/**`,
`docs/runbooks/observability/**`) and iac-obs9 `9231863..ad4e431` (only `dashboards/frontend.json.tftpl`). Checked:
every §6 task; the claim that the pinned `redaction` masks string log bodies (v0.160.0 `processLogBody` source, and a
mutation removing `redaction` from the oss log pipelines left email, bearer, JWT and AKIA text verbatim in the smoke);
no log path bypasses it (every profile's log pipelines end `redaction` → `batch`; `content-phoenix.yaml` is
traces-only; no debug exporter); allow-list parity by word-diff; every board query accepted by the smoke's Loki 3.7.7
(malformed controls rejected); the parity guard (regex selector, comma chain, stream-selector label, `and`, `on()` and
`unwrap` mutations all caught); no alarm or metric-filter resource; `terraform validate`; all bodies parse. Findings
→ rulings: P1 drop-report keys + panel 18 as a per-session max (fixed); P2 `url.template` is only id-collapsed (wording
fixed, Tempo `max_active_series` 100000; the source bound rides F9's fix pass; an API template table is §9); P2 panel 9
network-failure wording (fixed; the fetch fix rides F9); P3 parity-guard breadth, dotted-key RE-VERIFY list,
`status_message`, a runtime-built fake key (fixed); re-verification P3s — LogQL's `__error__` labels, a cap alert and
a test ceiling, the iac drops-widget title (mini pass). Lanes: static 73 passed / 10 skipped; full with both compose
smokes + rules 83 passed; `validate.sh` ok for oss, aws, azure. Residual: panels on real records (P9 check 9),
`url_template` emission (P9 check 8), CloudWatch syntax and dotted keys (B1b), the series-cap baseline is an estimate.

### Stream N9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY AFTER FIXES**; fix pass running)
Scope: dashboard-obs9n `b87ced0..f3d7d21` (6 commits). Checked: unit 1851/1851, `tsc`, eslint on 28 files; three
mutations (trace headers removed from the work-orders fetch; `Authorization` dropped by the traced helper; a dynamic
server import in `logger.ts`) each caught; two canary probes against the real route handlers; the build output (no
server-only marker in any client chunk; the edge bundles carry no N9 code); the `removeConsole` finding; a 3-way merge
of `logger.ts` against F9's tip with no conflict. Findings → rulings: P1 the api's error text reaches route log lines
in 14 of 19 cases (→ `routeFailure`: status + bounded code, never the message; the canary sweep gains a failing-api
mode); P1 5xx bodies carry upstream text in 16 of 19 cases, plus network-error messages, work-orders `details` and
content-stream's 502 (→ `routeErrorResponse`: a 4xx reason is kept, 5xx gets a constant); P1 the JSON format keys on
`NODE_ENV`, levels stay on `ENV` (the Amplify default is `ENV=development`), tests set and restore both; P3 internal
api URL kwargs, sweep bypasses (import resolution, `*.fetch(`), the "4 KiB" read claim, commented-out logger lines.
Residual: a minted `traceparent` names a parent that is never exported (until G9-18); no real `next start` run yet
(P9 check 5); non-status errors still ride scrubbed messages under the phase-4 rule.
**Re-verification (2026-09-11): MERGE-READY.** Unit 1874/1874, typecheck, eslint on the 23 fix-pass files; two mutations of the reviewer's own caught (the content-stream 502 body back to `payload.error`; a relative-path `streamApiRequest` import in print); a canary api answering 422 and 500 with a person's name and a filename across all 19 cases in production, the Amplify default and development — the canary reached no log line and no 5xx body; `readBoundedText` survives 3- and 4-byte cuts and cancels the rest; the behaviour changes break no consumer (no client reads `details`; every 5xx check is by class). New P3s: a list-`detail` FastAPI 422 is relayed as "[object Object]" by four routes (a fix-2 regression) and the literal-body rule is scoped to every body — both in a last mini pass.

### Stream F9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY AFTER FIXES**; fix pass running)
Scope: dashboard-obs9 `b87ced0..b9ba515` (11 commits) and api-obs9 `a19a931..46a86fc`. Ran: unit 1815/1815, `tsc`, eslint
on 39 files, api middleware + infra 322; 21 mutation checks (19 caught, 2 exposed test gaps). Held: F9.1–F9.8 built and
their §0 gaps closed; the URL-scrub test is non-vacuous; the reference comes from the injected `traceparent` through the
real instrumentation; the api test fails with the trace-id middleware moved back inside auth; both first-load gaps
proved on the real `AppProviders` tree; the metric-test edit is legitimate (a session-cumulative reader); ownership
stays inside the §1b hunks; `logger.ts` and `events.ts` merge with 0 conflicts against N9 `00c9763` and E9 `972d532`.
Findings → rulings (all accepted into the fix pass): P1 api error text reaches `browser.log` AND `browser.error`
(`reportError`) through `error.message` — status-bearing errors ship type + status only; P2 fetch network failures
(status 0) are not ERROR, so their root span is ratio-dropped — ERROR unless `AbortError`, in the fetch and XHR hooks;
P2 bound `url.template` without collapsing real static segments (`level1`, `export.xlsx`) — an id rule plus a guard
over every literal segment in `lib/api/**` and `lib/config`; P2 five ways to reference the logger slip past the AST
guard (alias, element access, namespace import, destructuring, parentheses); P2 `no-console` off for `tests/**` and
`scripts/**`; P2 the header-spread defect exists in `apiRequest` too; P2 camelCase identity keys in `SENSITIVE_KEY`; P3
URL-scrub probes for status messages and links plus the api path kept; `global-error` starts telemetry only with a
runtime config; `reportError` prefers the error's own `traceId`; `fetchOptimizerRaw`'s retry keeps its context; an AST
check that every chat upload runs inside `uploadInTurn`; lint/guard alignment and a total-delta metric assertion.
Residual: no `next build` on this tree (P9 builds it); cross-origin header reads and pre-config start are reasoned,
not observed in a real browser (P9); the TanStack conversion's merge with this branch is not yet rehearsable.
**Re-verification (2026-09-11): MERGE-READY.** Unit 1841/1841 (run once, after the other trees' lanes), `tsc`, eslint 0 problems on all 48 F9 files plus the console-using tests, Playwright specs and `scripts/lint-changed.mjs`, api 322, the 36 new fix-pass tests; 14 mutations of the reviewer's own all caught (the server text back on `browser.error` or `browser.log`, the network-failure mark or its abort exclusion removed, the digit rule or the served-file exception dropped, caller headers replacing auth, `global-error` without a runtime config, `reportError` ignoring the error's trace id, the optimizer retry losing its context, identity keys back to snake_case only, an unwrapped Pilot upload, and the old status/link and api-origin gaps). All three deviations accepted. Merge safety: 0 conflicts against N9 `00c9763` and E9 `972d532`; the TanStack tree (`tanstack-conversion` @ `196a376`) shares no file with F9. New P3s, both to §9: letter-only id values survive `url.template`; the constant-message guard does not see a logger reached through dynamic `import()`, `require()` or a `.js` source.

### Stream E9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY AFTER FIXES**; fix pass running)
Scope: dashboard-obs9e `b87ced0..3a2610a` (9 commits). Ran: the E9 targeted set 52/52, the full unit lane 1838/1838
(964 s, alone), typecheck, eslint on 38 files. Held: the catalogue matches §2.1 and all 77 keys any event can emit are
on the collector's browser allow-list (0 off-list); the coverage sweep and the double-emission guard are non-vacuous
(a dropped `meta.telemetry`, a wrapper moved inside `mutationFn`, and a self-emitting optimizer method each caught);
every site test asserts exactly one record for success and failure; the settles (session-triggered only, once, remount
and two-jobs-per-poll cases) caught under mutation; the auth vocabulary and content rules; 19 optimizer mutations and
the `jobId` strip proved; ownership clean; 0 merge conflicts against F9 `af9f307`, no shared file with N9 `c52f034`, and
the conversion tip `46208ee` adds only `useAppMutation` (the planned exemption key is right); outcome words as M9's
panels assume, except Run now. Findings → rulings (all accepted into the fix pass): P1 `useRunAutomationNow` records
`success`/`error` against its typed `accepted`/`rejected` — outcome words move onto the EVENT (an event-keyed map read by
`onMutationSettled`), not each meta; P2 the recipient email in `useShare.ts`'s dev-only info message; P2 the AD
disposition page wiring (`source`, `had_prior_disposition`) is untested — a page-mounted test; P3 RunsPanel's `jobId`
untested; P3 guard gaps (destructured aliases, callbacks, element access, `.bind`, aliased or namespace hook imports);
P3 three test files wait out TanStack's 5-minute gc timers; P3 React Strict Mode dev duplicates
(`invite_accept/preview` twice, `poll_count` one high). Owner note, not an E9 defect: `NewPasswordView` always calls
`confirmResetPassword`, so a user arriving from the login NEW_PASSWORD_REQUIRED challenge cannot finish there without a
reset code — a product issue outside phase 9. Residual: nothing ran in a real browser (P9 check 1); the conversion's
conflict files can't be rehearsed yet; after the conversion merges, E9's sweep lists every converted mutation without
meta and the guard's pin derives to empty — the planned follow-up.
**Re-verification (2026-09-11): MERGE-READY.** Unit 1845/1845 (587 s, alone), typecheck, eslint on all 40 branch files; 10 mutations of the reviewer's own all caught (dropping the automation entry from `EVENT_OUTCOME_WORDS` fails typecheck with TS2741 and three tests; the email back in the share line; the old M12 and a hard-wired `hadPriorDisposition`; the old M18; ten guard-bypass shapes flagged with the two documented limits and two clean controls left alone; the three lingering files now finish together in 16 s; removing either Strict Mode guard fails). Notes: hook recognition does not follow a default import (the conversion's `useAppMutation` is a named export).


### 10a. Plan review — 2026-09-11 (reviewer Opus 5; verdict READY AFTER CHANGES) — triage

| # | Sev | Finding | Ruling |
|---|---|---|---|
| 1 | P1 | Auth-converted 500s (and 401/403/429) never pass the trace-id middleware, so the 500 toast has no `X-Trace-Id`; the planned CORS test would pass anyway | ACCEPTED — verified in `main.py:283-305` / `auth.py:504-540`: F9.4 moves the middleware just inside CORS and tests a raising route through the real order; D9-4 reads the injected `traceparent` first (network failures get a reference) |
| 2 | P1 | 14 interpolated shipped warn sites, not 6; a deny-list sweep would miss variables | ACCEPTED — verified (8 multi-line sites); F9.2 lists all 14 + the `handleApiError` conditional; the guard is an allow-form AST check |
| 3 | P1 | N9's server branch importing server modules from `logger.ts` breaks the client bundle; `removeConsole` may strip `console` | ACCEPTED — `next.config.mjs:22` sets `removeConsole` in production: §5 seam (globalThis sink + store, `process.stdout.write`), D9-19, `npm run build` at N9 close |
| 4 | P1 | An owner-side TanStack audit targets E9's direct-call sites | ACCEPTED — verified (untracked, read-only, 2026-09-11): §1b names it; D9-17 one-emission rule + AST guard; E9 converts nothing; the member-update double emission it reports is G9-38 |
| 5 | P1 | `global-error` cannot report without telemetry running; SSR root failures cannot reach the api | ACCEPTED — F9.6 starts telemetry first and tests with it NOT started; SSR root failures belong to N9.4 |
| 6 | P1 | P9: sampling hides checks 5/6; check 2 lacks a presence control; four gaps had no live proof; forcing hooks unstated | ACCEPTED — ratio pinned to 1 in the probe tree; presence-first check 2; checks for attachments, content-stream, settles, Document Hub and discovery actions; probe-only forcing hooks |
| 7 | P2 | F9.5's synthetic test proves the gap by construction | ACCEPTED — the real `AppProviders` tree with real boot-time hooks; fetch and error ruled separately |
| 8 | P2 | Cross-origin paths (S3 keys) survive query stripping; product events are a second exit | ACCEPTED — F9.1 reduces third-party URLs to scheme + host and sweeps the product-events bodies (G9-41) |
| 9 | P2 | "Every user-visible failure" is overclaimed (79 direct toasts; optimizer-api's own `ApiError`) | ACCEPTED — Goal narrowed; optimizer-api routed through F9.3's helper; direct toasts to §9 (G9-39) |
| 10 | P2 | Audit findings missing from §0 | ACCEPTED — G9-33 … G9-37 added (allow-list kwargs, settles, wizard writes, chat components, #15 `department`) |
| 11 | P2 | Overlap with the unmerged phase-8 D8 branches | ACCEPTED differently — M9 stacked on the D8 branches (D9-18) instead of rebasing later |
| 12 | P2 | D9-11 pre-empts the owner's open alarm-dialect ruling | ACCEPTED — documentation only; Terraform after the ruling and B1b |
| 13 | P2 | D9-15's "backend series unchanged" is false | ACCEPTED — `url.template` only; failures via the intrinsic span status |
| 14 | P2 | The pinned `redaction` processor handles map bodies only | ACCEPTED at plan time, SUPERSEDED at build — M9 proved the pinned `redaction` masks string bodies (G9-03); no `transform` added, the property is test-pinned |
| 15 | P2 | The catalogue delta needs an owner look before E9 builds; `browser.telemetry.dropped` needs a real consumer | PARTLY — the owner said "then let's implement": the delta goes to the owner non-blocking (merges are held anyway); the "Telemetry drops" panel is now required (M9.4) |
| 16 | P3 | Rostering console count 7; no `tests/unit/infra`; dedupe-suppressed references; discovery settle via an effect; 401 retry escapes `runInContext`; minted span id for trace linkage | ACCEPTED — all folded into G9-12/G9-28, F9.2, F9.4, E9.6, F9.7, F9.3 |

## 11. Implementation notes / Learnings (per stream, as work lands)
### Stream F9 — landed 2026-09-11 (implementer Opus 5; dashboard-obs9 `ee68a7a` → `b9ba515`, 11 commits; api-obs9 `46a86fc`)
F9.1 `81c1e9c`: the exporter serializes scrubbed copies (span attributes, event and link attributes, status message,
log attributes and body) — first-party URLs lose query and fragment, third-party URLs keep scheme and host;
`scrubMessage` applies the same rule inside free text; the provider registers the api origin (2 lines). F9.2 `3c729af`:
`emitLog` scrubs bodies; the 14 settings-api messages are constant; `.eslintrc.json` gains `no-console` (Rostering
exempt) and the constant-first-argument rule; the AST guard (string literal, expression-free template, or `+` of
literals only) runs in the unit lane; the masking rules moved to `lib/telemetry/scrub.ts` to break an import cycle.
F9.3 `13ec1dd`: every failed request's error carries `traceId`, `requestId` and `urlTemplate`; `handleApiError` logs one
constant message with the template, status and `request_id`; the dedupe key adds endpoint and status; the record is
emitted inside the failed request's trace through `context.with` (no `emitRecord` signature change); the two `client.ts`
URL lines are gone. F9.4 `bbf2d04` + api `46a86fc`: the reference is the trace id of the `traceparent` the instrumentation
injected (fallback `X-Trace-Id`), shown with a Copy button in both fallbacks and in server / network / unknown toasts;
a deduped repeat returns the id of the record that shipped; api: CORS exposes `X-Request-ID` and `X-Trace-Id`, the
trace-id middleware sits just inside CORS, and a test on the real app shows auth's 500 and 401 leaving without the
header on `a19a931`. F9.5 `cd4758b`: the first test PROVED both gaps on the real `AppProviders` tree (a page's first
query went out untraced; a first-render error was lost); `lib/telemetry/boot.ts` starts the stack at module load. F9.6
`e2cc258`: `app/global-error.tsx`. F9.7 `e0262a7`: `uploadInTurn` in the three stream hooks, `attachment_count` and
`attachment_upload_ms`, and `fetchWithAuth` / `fetchStreamWithAuth` re-enter the caller's context for the post-refresh
retry. F9.8 `ee68a7a`, `db880b6`, `b9ba515`: the stale env line, the dead traceparent generator, and the dead
`sendMessage`, `rawApiRequest` and `handleApiResponse` (a hand-off from the TanStack conversion). Logging coverage
`f60bc35`: a failed token refresh and its sign-out failure now warn. Lanes: unit 1815/1815, `tsc`, eslint (39 files and
`app components lib`), api middleware + infra 322 passed. Deviations accepted: the legacy guard bans the generator's
declarations, not its names (the SDK's `RandomIdGenerator` reuses them); `test_auth_rejection_metric.py` now measures
per-attribute-set deltas (its reader accumulates across the session); the api lane needs `POSTGRES_DB=copilot_mro_test`.
Queued for the fix pass with the review's findings: id-collapsing `url.template` at the source, fetch network failures
marked ERROR (not aborts), the `authenticatedApiRequest` header spread, `no-console` scope for test fixtures, no api
error text in status-bearing browser records, camelCase identity keys in `SENSITIVE_KEY`.
Fix pass (after review, 2026-09-11): `d5ac0c5` status-bearing errors ship type + status + `url.template` on `browser.log` and a fixed `HTTP <status> <template>` summary as `browser.error`'s `error_message` (never the server's text — `browser.error` has no status key and its names belong to E9), camelCase identity keys redacted, `reportError` prefers the error's own trace id; `304c985` fetch network failures (no response, not `AbortError`; `TimeoutError` counts) marked ERROR so the sampler keeps them (the XHR instrumentation already did); `a43dfeb` `apiRoutePattern` collapses id shapes, off-alphabet segments, digits except numbered words (`v1`, `level1`, `level2-runs`) and dots except served file names (`export.xlsx`), with a harvest guard over literal segments in `lib/api/**` and `lib/config`; `cd61c0b` both `apiRequest` and `authenticatedApiRequest` merge caller headers over the auth headers through `Headers`; `389d547` `global-error` starts telemetry only with a runtime config; `fec89ec` an AST pin that every chat upload runs inside `uploadInTurn`; `ce1e1c9` the logger guard closes the alias, element-access, namespace, destructuring, parenthesised and re-export bypasses; `9201d67` `fetchOptimizerRaw`'s retry keeps its context; `81f20ea` `no-console` off for `tests/**` and `scripts/**`, the lint selector matches the guard; `af9f307` status-message and link probes in the URL-scrub test plus the api path kept; api `72df51a` the metric test also asserts the total delta. Lanes: unit 1841/1841, tsc, eslint (F9 files + `app components lib`), api 322.

### Stream N9 — landed 2026-09-11 (implementer Opus 5; dashboard-obs9n `81b1ea9` → `f3d7d21`; fix pass `3784b13` → `00c9763` + mini pass `cc193eb`, `c52f034` done — tip `c52f034`)
N9.1 `81b1ea9`: the request context lives on `globalThis` under `Symbol.for` keys (a module-level store fails the
two-bundle test). N9.3 `c0b323a` + `f3d7d21`: the sink writes through `process.stdout/stderr.write`; `logger.ts` only looks
it up (import-graph guard). N9.4 `c2d324e`: `instrumentation.ts` — `register()` registers the sink under
`NEXT_RUNTIME === 'nodejs'`, `onRequestError` writes one line. N9.2 `26124e7`: `withRoute` on all 17 exported methods of
the 12 routes; `tracedApi*` helpers carry the full header set (because `authenticatedApiRequest` spreads
`{ headers, ...options }`); trace headers on every api call and none on the S3 hop; three sweep guards. N9.5
`a71907c`: upstream bodies, the token `sub`, organization contact, comment text and names are out of the logs (a
canary sweep), and two silent failure paths now warn. Lanes: unit 1851/1851, typecheck, eslint, `next build` clean, no
server-only marker in the client chunks. Finding: `removeConsole` strips literal `console.x` calls from server chunks
too while computed calls survive, so the base's route logs did reach production — unstructured and without trace ids.
Fix pass so far: fix-1 `8954733` route failures log status + code, not text; fix-2 `ab79ba1` 4xx reasons kept, constants
for everything else; fix-3 `6ca7fda` JSON lines follow `NODE_ENV`, levels follow `ENV`; fix-4 `ab723ec` no internal api
URL kwargs; fix-6 `49a3c68` upstream error bodies read to 4 KiB and the rest cancelled; fix-7 `3784b13` dead commented
logger lines deleted (and a static rule against them); fix-5 `00c9763` the route sweeps resolve import specifiers, allow only `ApiError` and types from `lib/api/**`, flag any `*.fetch(` and require `traceHeaders()` as the headers argument (print and stream moved to a `tracedStreamRequest` helper). Final lanes: unit 1874/1874, typecheck, eslint on 23 files. Behaviour changes to note for the gate: print, stream, signed-url and `documents/[id]` answer an api 4xx as `{ error: <api reason> }` (the reason used to ride in `details`); an upstream 5xx answers 502 on the 15 routes whose failures arrive as an `ApiError` (content-stream's two hops and work-orders pass the upstream status through with a constant body; the tenant route's identity-header path answers 500); with `ENV` unset, info/debug server lines ship as JSON.
Mini pass after re-verification: fix-8 `cc193eb` — a 4xx relays the api's `error`, else `detail`, only when it is a non-empty string (a FastAPI list `detail` answered `{"error":"[object Object]"}` on all 15 `ApiError` routes at `00c9763`), otherwise the route's constant with the same status; fix-9 `c52f034` — the literal-body rule checks only error bodies (a literal status ≥ 400 or a catch block), as a tested `bodyOffenders` function; the reviewer's m1 mutation still fails it. Final lanes: unit 1877/1877, typecheck, eslint.

### Stream M9 — landed 2026-09-11 (implementer Opus 5; copilot-mro-obs9 `07f22475` → `6984d47b` on the stacked base `9976fa7c`; iac-obs9 `1eb8c6c` → `ad4e431` on `9231863`; final mini pass landed — tips `31526d64` / `bd7992a`)
M9.1 `07f22475`: the five §2.1 keys in both allow-list statements. **Deviation, accepted:** no body-masking transform —
the pinned `redaction` already masks string bodies (a probe on the pinned image plus the processor source), so the
property is test-pinned instead (G9-03 disproved). M9.2: static pins plus a compose smoke through the real collector
into Loki; `OTEL_SMOKE_PORT_PREFIX` (default 1 = today's ports) because the leftover `flynapse-otel-probe` collector
holds 14318/14319/14313. M9.3 `44dcae10`: Tempo gains the `url.template` dimension only; panel 6 gains a per-template
p95 and a "Browser API failures by endpoint" panel is new. M9.4 `54ff6a19`: nine new `fn-frontend` panels (10–18) with
DARK markers, CATALOGUE §5, and guards that every §2.1 log event is charted and every label a browser LogQL panel or
Loki rule reads is delivered by the collector. M9.5 iac `1eb8c6c` + copilot-mro `c3faabf1`: nine Logs Insights widgets
(RE-VERIFY) and the browser alarms documented only (metric-filter patterns, `Flynapse/Browser` metrics, the Loki
thresholds, the SNS target; blocked on the alarm-dialect ruling, B1b and the cut-over). Fix pass: `661b3000` (+ iac
`dfe3d13`) drop-report keys and panel 18 as a per-session max; `eedfeb25` id-collapsed wording and a
`max_active_series` cap of 100000 (baseline 20–35k series, estimated — the dev Prometheus has no span metrics to measure);
`10f539fa` parity-guard breadth; `a9bc04d1` the dotted-key RE-VERIFY list; `2676be63` `status_message` dropped and the
fake key built at runtime; `6984d47b` (+ iac `ad4e431`) failure and sampling wording. Lanes: full otel lane 83 passed
(both smokes + rules), static 73 / 10 skipped, `validate.sh` for all three profiles, `terraform validate`, all 8 bodies
parse, 29 LogQL queries accepted by the pinned Loki. Pre-existing, left alone: `terraform fmt -check` flags `amplify.tf`
(main `02bb5cb`). Learnings: the otel lane needs `POSTGRES_DB=copilot_mro_test`; the browser's drop counts are
cumulative per tab and its reason keys count batches; Tempo 3 counts a series as active only if touched in the last
15 minutes.
Mini pass (after re-verification): `28973020` LogQL's `__error__` / `__error_details__` accepted by the parity guard (m4 now passes, m1 still fails); `7d453a6d` the oss-only alert `TempoGeneratorSeriesNearCap` (`max by (tenant)` of `tempo_metrics_generator_registry_active_series_demand_estimate` > 80000 for 15m, warning — the metric name read from a live Tempo 3.0.3, which also exported 19 series per label set; a plan-default threshold for the owner's alert review), its runbook section and catalogue lines, and a cap test bounded to [50000, 1000000); `31526d64` + iac `bd7992a` the drops widget retitled "top 50 tabs". Lanes: static + rules 76 passed / 8 skipped, `validate-rules.sh` (5 platform rules), `terraform validate`, bodies parse.

### Stream E9 — landed 2026-09-11 (implementer Opus 5; dashboard-obs9e `f697919` → `3a2610a`, 9 commits; review running)
E9.1 `f697919` (+ `0b236a5`): the seven §2.1 names, allow-lists and typed emitters; `withFeatureMutation`,
`startAuthFlowTiming`, `withExportRequested`, `withOptimizerRunTriggered`; closed `FEATURE_ACTIONS` and
`AUTH_FLOW_STEPS` maps (a pair outside them is a compile error); `errorTypeOf` (names only); a REPO-WIDE coverage sweep
(every mutation declares `meta.telemetry` or is exempt with a reason — zero exemptions at close) and a TypeScript-checker
double-emission guard (transitive and alias-aware; derived self-emitting methods compared to a pinned list — the 14
existing `SettingsAPI` methods plus `useDepartmentAPI`; E9 adds none); both read one `MUTATION_HOOKS` list
(`useMutation`, `useAppMutation`). E9.2 `ba0ba33`: optimizer hooks (19 after the three dead ones went in `286f5a3`), the
wizard chain and CanvasHeader's export and re-run preflight wrapped at the call site (`usePreflightJob`'s telemetry-only
`jobId` is stripped before the request). E9.3 `972d532`: AD dispositions (verb, prior ruling, surface) and corpus
actions. E9.4: WITHDRAWN to the TanStack conversion — the uncommitted work is saved as `phase9-E9.4-withdrawn.patch`
(in `copilot-mro/.dev_runs/obs9-phaseA/`), including nine site tests that document today's defects (a department
delete emits three records and never `department/delete`; a member role change two; a create-with-head three). E9.5
`286f5a3`: automations (Run now now carries `department`, G9-37), comments, improvement, chat share and both
data-discovery pages — meta only. E9.8 `0a85834`: the work-order "Download all" emits one export request (and the
upstream error body left that function's log attribute). E9.6 `65929a0`: automation runs settle only when this session
triggered them, once; discovery jobs from a per-job effect. E9.7 `c2d05c6`: register, signup confirm and resend,
forgot-password, new-password and the invitation preview (the "Finish joining" retry untouched). Close `3a2610a`.
Final `FEATURE_ACTIONS` (full table in the notes): optimizer — schedule, expansion, activity, activity_rule, duration,
role, settings, job, job_config_snapshot; ad_review — applicability, corpus; automations — automation; comments —
comment; improvement — improvement_run, finding; chat — chat; data_discovery — source, job, level1_batch; kept for the
post-RC follow-up with no emitter yet — notifications/notification/mark_read, document_hub/document
{update, retry, delete}, document_hub/document_sharing/update. Lanes: unit 1838/1838 (~20 min), typecheck, eslint on 38
files. Recorded, not defects: outcome `challenge` and `invite_accept/accept` are not emitted on this branch
(`NewPasswordView` can't tell forgot-password from the login challenge); the double-emission guard costs ~6 s and
~400 MB per lane. Pre-ruled for the fix pass: `useRunAutomationNow` records `accepted`/`rejected` (its typed contract;
never run in production), and the recipient email leaves `useShare.ts`'s dev-only info line. Learnings (dashboard
tests): a failing test must unmount in `afterEach` and clear the app query client, or its 5-minute timers keep the file
alive; jsdom lacks `FormData`-from-form and `createObjectURL`; typing must run inside `act`.
Fix pass (after review, 2026-09-11): `a708d49` outcome words live on the EVENT — `EVENT_OUTCOME_WORDS` in `mutation-meta.ts`, typed over every meta-declarable event and read by `onMutationSettled` (both run triggers `accepted`/`rejected`, everything else `success`/`error`; the per-meta field is gone), and `useShare`'s info line carries `block_id` only (the site test captures console output for typed content); `33713a6` the airworthiness page mounted behind its real `RouteGuard` and `PermissionProvider` pins `source` and `had_prior_disposition`; `ac77de8` a RunsPanel Run press records `job_id` on preflight and solve; `e99acc3` both guards count any reference to an emitter (callback, `.bind`, alias), resolve destructured aliases and literal element access, and recognise the hook through the file's own imports (alias, namespace, `useAppMutation`, local hooks) — the derived self-emitting list gained `useTenantAPI`; `ff9bf27` three files clear the query client (5–7 s instead of a 5-minute idle); `08b7650` React 19.1 dev double-runs mount effects only on client-side mounts, so `useInvitationPreview` records once per token per view and the discovery tracker once per completed fetch. Lanes: unit 1845/1845 (606 s, was ~20 min), typecheck, eslint on 17 files. Open guard limits (none present in the app): a function created by a call and passed on uncalled, a non-literal element key, values computed from an emitting call (deliberately unflagged).

## 12. Lessons
- **Adjacent owner work that shares the effort's files is Fable-gated too (2026-09-11).** Tried: telling the owner's
  parallel TanStack conversion session it could land on `agent_sdk` first because it "is not Fable-gated", with phase 9
  absorbing it later. Owner corrected: "i will want to fable review that work too eventually." Rule: under a
  stronger-model gate, treat any parallel work that shares the effort's files as gated too unless the owner says
  otherwise — give it its own gate chunk (here RC), fix its merge order against the effort's chunks, and say so in the
  first coordination message.

