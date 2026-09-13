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
- [ ] F9 — built 2026-09-11 (dashboard `ee68a7a` → `b9ba515`, 11 commits; api `46a86fc`; unit 1815/1815, tsc, eslint, api middleware + infra 322; F9.5 PROVED both first-load gaps on the real tree → `lib/telemetry/boot.ts`); review MERGE-READY AFTER FIXES (1 P1 — api error text in browser.log and browser.error; 6 P2; 6 P3 — incl. the six queued cross-stream items, several widened); fix pass done (dashboard `af9f307`, 10 commits on `b9ba515`; api `72df51a`; unit 1841/1841, tsc, eslint, api 322); re-verified MERGE-READY (14 reviewer mutations all caught; 2 new P3 → §9). **F9 Phase A done** (tips `af9f307` / `72df51a`); F9.9 post-close 2026-09-11 from the TanStack session's report — one precedence for the server's sentence, reviewed MERGE-READY, fix pass `279df2f` re-verified MERGE-READY (unit 1852/1852; the old-vs-new classifier matrix changes 72 rows, all improvements, none at 401/429/5xx) — F9 tip now `279df2f`
- [ ] E9 — built 2026-09-11 (`f697919` → `3a2610a`, 9 commits: E9.1–E9.3, the `useAppMutation` follow-up `0b236a5`, E9.5 `286f5a3`, E9.8 `0a85834`, E9.6 `65929a0`, E9.7 `c2d05c6`, close `3a2610a` — no pending exemptions left; E9.4 withdrawn to the TanStack conversion; unit 1838/1838, typecheck, eslint); review MERGE-READY AFTER FIXES (1 P1 — Run now outcome words; 2 P2 — the useShare email, the AD page wiring untested; 5 P3); fix pass done (`a708d49` → `08b7650`, 6 commits; unit 1845/1845 in 606 s, typecheck, eslint); re-verified MERGE-READY (10 reviewer mutations all caught). **E9 Phase A done** (tip `08b7650`)
- [ ] N9 — built 2026-09-11 (`81b1ea9` → `f3d7d21`; unit 1851/1851, typecheck, eslint, `next build` clean; `removeConsole` settled: literal `console.x` calls are stripped server-side, computed calls survive); review MERGE-READY AFTER FIXES (3 P1: api error text in route log lines and in 5xx bodies, the NODE_ENV-keyed format; 4 P3); fix pass done (`3784b13` → `00c9763`, 7 items; unit 1874/1874, typecheck, eslint); re-verified MERGE-READY (2 new P3 — a list-`detail` 422 relayed as "[object Object]", the literal-body rule's scope — landed in the mini pass `cc193eb` + `c52f034`; unit 1877/1877). **N9 Phase A done** (tip `c52f034`)
- [ ] M9 — built 2026-09-11 (copilot-mro-obs9 `07f22475` → `c3faabf1`, iac-obs9 `1eb8c6c`; otel lane 80 passed incl. both compose smokes); review MERGE-READY AFTER FIXES (the pre-ruled drop-keys P1, 3 P2, P3s); fix pass done (copilot-mro-obs9 `6984d47b`, iac-obs9 `ad4e431`; otel lane 83 passed incl. both smokes; Tempo `max_active_series` cap 100000); re-verified MERGE-READY (4 P3 nits: `__error__` in the parity guard, a cap alert + test ceiling, the iac drops-widget title — landed in the mini pass `28973020`, `7d453a6d`, `31526d64` + iac `bd7992a`, incl. a new warning alert `TempoGeneratorSeriesNearCap` at 80% of the cap; the "fetch network failures once F9's fix lands" wording rides on F9's fix pass). **M9 Phase A done** (tips `31526d64` / `bd7992a`); M9.6 done after P9 (tips `90a60040` / `1d2b400`)
- [x] P9 — live probe 2026-09-11 (checks 1–9 PASS with the gaps named in §7 "P9 results"; evidence `copilot-mro/.dev_runs/obs9-probe-20260911/`); stack torn down
- [x] M9.6 — DARK flip done 2026-09-11 (copilot-mro-obs9 `e3f55d65` + `90a60040`, iac-obs9 `092fcf5` + `1d2b400`). Changes:
  - Panels 1–6, 9, 10, 11, 13, 15, 16 and 17 A now read "LIVE since the P9 probe (2026-09-11)".
  - Panels 12, 14, 17 B and 18 keep DARK, each with a dated reason.
  - The four Loki browser rules are LIVE.
  - The failure ratio leaves `MutationRefusedError` out of both the failures and the attempts, and charts refusals as a
    series of their own.
  - The guards accept either a DARK note or a dated LIVE note, and three mutations fail them.

- [x] M9.7 — the settings-side refusal split, after RC's invitations conversion produced the shape: done 2026-09-12 (`0259fd8d` / iac `a0059f9`; static + rules 78 passed, 8 skipped; the new guard mutation-checked by the session lead)
  Evidence: the static otel lane with the rules check passed 77, skipped 8; `validate-rules.sh` passed; `terraform
  validate` passed; the session lead's rerun of the two guard files passed 25/25.
- [ ] C9 — core ingest: a client disconnect answers 499 with one INFO line, not a 500 + ERROR traceback (P9 finding (a); `/home/aditya/Code/core-obs9` → `obs9-core` off `master` `988571b`); built 2026-09-11 (`88bbca5`; fail-before 4 failed, after 9/9; lanes 203 passed); Opus review MERGE-READY (6 P3: 4 in a mini pass, including the sibling product-events route; 2 recorded); mini pass landed (tip `bd18984`: both disconnect shapes, and the same fix on `POST /analytics/events`); re-verified MERGE-READY (11/11 mutations); C9.2 landed `7264e2e` — the analytics contract test's seed-date time-bomb, red on core `master` since about 2026-09-08, fixed by pinning the service's existing `now` to the seed's time; 20/20 at the real clock, +30 and +366 days; re-verified MERGE-READY; N3 `8e3c3ce` adds a unit test for the real-clock default (four mutants fail it). **C9 Phase A done** (tip `8e3c3ce`)
- [x] Phase A closed 2026-09-11 — §8b gate agenda with every branch tip; merges held for Fable
- [ ] Post-close additions (2026-09-12, each reviewed): F9.9 one precedence for the server's sentence (done, tip `279df2f`); M9.7 the settings-side refusal split (done, tips `0259fd8d` / `a0059f9`); M9.8 the refusal wording done (tips `83f4a8f7` / `b72307b`; a new guard fails on all five false claims); E9.9 done (tip `c2f2025`: the throw goes out of band, and one settle record per mutation); E9.9b done (`64a6fa0`: all five timing wrappers emitted their success record inside the try they catch) and E9.10 done (`bc9fbcc`: the guards, and 18 files moved off literal event names); F9.10 done (tip `01a3882`; every rewritten test shown catching a breakage its original passed); N9.6 done (tip `7fc2bcc`; four of its seven breakages passed at the old tip, two of them fully green); an E9 guard batch after E9.9
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
Merge notes from code-26 (2026-09-11, TanStack phase 2–3 prep; acknowledged, nothing needed from either side before
the merge):
- **`useOptimizer.ts`.**
  - All seven D9 hooks carry an inline `meta` literal whose `suppressGlobalError` is true only when the caller passes
    `callerShowsErrors`. E9's `telemetry` key is combined into each one.
  - `CallerErrorOptions` moves to just above `useUploadScheduleCsv`.
  - The new `mutationKey` lines in `useRunJob`, `useProcessActivity` and `useDeleteSchedule` are kept; they are separate
    from meta and serve the per-row locks and a wizard navigation gate.
  - The optimizer.jobs invalidations in `useRunJob` and the `useRuns` terminal check use exact matching, and are kept.
- **`usePreflightJob`** should merge clean. RC copies E9's `mutationFn` lines verbatim, and base already has
  `suppressGlobalError`. If git flags the meta lines anyway, E9's literal wins; it is the superset.
- **Data Discovery `jobs/[jobId]/page.tsx` rerun.** Expect a trivial adjacent-hunk conflict. Keep both sides: E9's meta
  line and RC's `onSuccess` body.
- **`useFeedback`** does not overlap.
- **`useShare.ts:57`.** code-26 reported the logged recipient email as a privacy item. It is already fixed on
  `obs9-events` (E9 fix pass `08b7650`, a constant message with only `block_id`). RC leaves that line alone.
Further notes from code-26 (2026-09-12):
- **`lib/api/client.ts`.** RC deletes the hand-rolled chat listing and history caches. F9.8 deleted a dead `sendMessage`
  in the same file. The deletions look disjoint, but both sides rewrote inside `listChats` and `getChatHistory`, so the
  merge re-reads those two bodies rather than trusting a clean result.
- **`tests/unit/telemetry/chat-turn-hook-outcomes.test.tsx`.** RC wraps it in a `QueryClientProvider`, because the stream
  now reads the query client. Additive, with every existing assertion unchanged; phase 9's guards read the hook's
  emissions, not its wrapper.
- **A refusal now reaches a site with telemetry.** RC's invitations conversion is the first place where the helper's
  permission gate meets `meta.telemetry`, so a non-owner's Resend emits a `browser.settings.mutation` record with
  outcome `error`, `error_type` `MutationRefusedError` and a near-zero duration, having sent no request. The same shape
  follows on the department-roles, team, tenant-departments and operator surfaces.
  - **Ruling (2026-09-12): the records stay.** They are the signal for permission friction per surface. M9.7 extends
    M9.6's split to the settings panels, so refusals never sit in an error bucket.
  - No alert can fire on one: no rule reads mutation outcomes, and the helper only toasts on a refusal, so there is no
    `browser.error` record either.
  - The near-zero duration stays honest. No panel reads mutation duration, and a refusal makes no span, so it cannot
    reach the span-metrics latency views. A later latency view over mutation records reads successes only, which M9.7
    writes into the catalogue conventions.
- **A composite write can report a false success (code-26, 2026-09-12; review asked for before RC's gate).** On a couple
  of RC's composite writes the API primitive wraps only the first request, so a failure in the second step emits
  `outcome: success` while the user is told it failed. RC's telemetry swap removes the primitive's wrapper as it adds the
  call-site literal, which fixes the divergence rather than doubling the record. The session lead asked to see that
  change before RC merges, because a false success is the one shape the panels cannot detect and it deflates every
  failure ratio it lands in. What phase 9 checks when it arrives: one record per user-visible write (D9-17); the outcome
  describes the whole composite, so any failed step makes it an error; `error_type` comes from the step that failed;
  `duration_ms` spans the whole sequence; and a partial failure is still one record unless phase 9 rules otherwise.
  - **Correction to this section's own instruction (measured 2026-09-12): "the call-site wrappers give way to the hook
    path" silences counted actions if taken literally.** On `obs9-events`, `ReviewStep.tsx` counts its actions with
    `withFeatureMutation` (`:181`, `:193`, `:200`, `:210`) and `withOptimizerRunTriggered` (`:220`), and `CanvasHeader.tsx`
    with `withExportRequested` (`:188`). On `tanstack-conversion` those components call RC's hooks instead
    (`useCreateJob`, `useProcessActivity`, `useRunJob` at `:125-128`), and those hooks' meta carries only
    `suppressGlobalError` (`useOptimizer.ts:304`, `:438`, `:505`). Dropping the wrapper with nothing added turns the
    wizard's activity create, activity process, role create, job create and RUN TRIGGER, plus the CanvasHeader export
    path, from counted into silent — and neither branch is wrong on its own.
    **The rule: anything counted on either branch stays counted across the merge.** Where RC's hook path supersedes a
    phase-9 call-site wrapper, the telemetry MOVES into that hook's existing meta literal — combined with RC's
    `suppressGlobalError`, one literal — and the wrapper goes in the same change, so the double-emission guard proves it
    was a move and not an addition. The attributes come from the closed word maps and E9's existing optimizer-run helper,
    not from new words. This is what separates these five from the 43 bare feature writes: those were never counted, so
    deferring them changes no data.
    **Why the metas cannot be carried on RC's branch (code-26 measured it, 2026-09-12):** `EVENT_NAMES` on
    `tanstack-conversion` has 13 entries and none of the six sites' events is among them — no feature-mutation event, no
    optimizer run-triggered event (its automations entry is a different event), no export-requested event — and the three
    wrapper helpers are absent too. Declaring those metas there would mean adding entries to `lib/telemetry/events.ts`,
    which breaks the no-new-events rule, the `lib/telemetry/**` fence and RC's own exact-list pin at once, and
    `EVENT_ATTRIBUTE_KEYS` is keyed by event name so each entry needs its attribute list beside it — three coupled edits
    in phase 9's file to make their branch mechanical. So the move belongs in the merge, where the wrapper and the meta
    change together and the double-emission guard proves it was a move. Shape they asked for, and §1b already requires:
    the `telemetry` key goes INSIDE the existing meta literal (several of which carry a computed `suppressGlobalError`),
    one literal per call.
    **And how the finding was reached, recorded because the failure was this session's own:** the session lead named this
    class to code-26 as "a settings write", having measured the class and inferred the domain. They traced all thirteen
    previously-wrapped settings primitives, found every app call site declaring telemetry, and asked for the instance to
    be named rather than accepting the class — which is the request that catches exactly that error. No settings write
    goes silent; the class is real in the feature domain.
  - **Two sweep boundaries measured before the trial merge ran (code-26, 2026-09-12), both worth stating once:**
    - **The wrapped upload is instrumented and invisible.** `hooks/document-hub/useDocumentHubMutations.ts:83` emits
      through `withUploadTelemetry` called inside its `mutationFn`, not through a `meta.telemetry` literal. The coverage
      sweep reads the declaration as literal syntax and its exemption map is empty, so it reports that site as bare when
      it is fully instrumented. The resolution is an EXEMPT entry with its reason, never a literal: `withUploadTelemetry`
      is in the double-emission guard's emitter list, so a `meta.telemetry` there would be a real double count and that
      guard would fail it. The two guards disagree about the same site for opposite reasons, and the exemption is where
      that is stated once — with the reason attached, so the next reader does not "fix" it. The file's other three writes
      are genuinely bare. This is the cost of the inline-literal rule (D9-17) stated plainly: it makes the common case
      visible at the price of making a structurally-correct wrapped case invisible.
    - **The bare feature writes are a scope boundary, not a gap.** Their branch carries 27 settings writes, all 27
      declaring telemetry, and 48 feature writes of which 4 declare it plus the wrapped upload. The other 43 — 22 of them
      in `useOptimizer.ts`, whose `meta` carries only `suppressGlobalError` — are bare by phase 9's own ruling: a
      converted feature write keeps its logger call until phase 9's later follow-up adds its meta and removes that call in
      the same change. The trial merge therefore instruments only two classes — a settings write whose previous emission
      the merge itself removes, and the invite retry named above — and LISTS the rest with its reason. Their counts are
      file-granularity arithmetic, stated as such; the sweep's per-call analysis is authoritative and the trial reports
      where the two differ.
  - **Merge facts measured by code-26 against E9.9b (2026-09-12), by taking our files into a scratch copy of their trunk
    rather than reasoning about it:**
    - **The telemetry fix drags in a third module.** `lib/telemetry/events.ts` and `lib/telemetry/product-events.ts` both
      import `lib/telemetry/report-bug.ts`, which exists only on `obs9-events`. Anyone moving those two files without it
      gets a tree that does not compile.
    - **Their whole Document Hub suite passes 58 of 58 with our fix in their tree**, in development mode — which is the
      only form of that check that means anything, since running it against the old wrapper proves only that their tests
      send no stray attribute.
    - **Two of their guards go red at the merge, both theirs to fix.** One asserts the contract E9.9b deliberately
      removed (that an off-list attribute throws in development); they are rewriting it against the new contract — the
      record survives with the key stripped and the complaint arrives out of band — rather than deleting it, since the
      property is still worth holding. The other pins `EVENT_NAMES` as an exact list, which our branch extends.
    - **Both sides edit `tests/unit/telemetry/events-envelope.test.ts`**, so expect a conflict there: E9.9's version is
      the contract, and any assertion their rewrite adds is re-applied on top of it.
    - **Ruling (2026-09-12): one exact pin, in the list's owner; consumers pin subsets.** A consumer test that pins the
      whole catalogue goes red every time phase 9 adds an event, which trains its owner to loosen it under time
      pressure. The catalogue's own definition test holds the exact list — that is where a literal belongs and where a
      rename must be noticed — and a consumer asserts only the entries its own code emits.
  - **RC's composite-write swap delivered for phase 9's look (2026-09-12):** `/home/aditya/Code/dashboard-t13`,
    `tanstack-t13` @ `06f6aa3`, report at `.superpowers/sdd/tanstack-mutation-conversion/task-13-report.md`. An Opus
    reviewer is checking it against §1b's five checks and the rollback ruling. Thirteen call-site literals in, thirteen
    wrappers out.
    - **Volume changes our panels will see at the merge:** the organization update and the department delete gain records
      (neither was ever wrapped); every gate refusal, still-held role and unreadable scan now emits where it emitted
      nothing; a department create whose head step fails moves from `success` to `error`, which is check 2 working but a
      step change on a live surface; and three triples go to zero volume app-wide — `member/grant/tenant`,
      `member/grant/department` and `member/revoke/tenant` — because the department composites emitted them too.
    - **Correction from code-26, worth keeping for how it was found:** a team removal was ALWAYS two records
      (`member/revoke/tenant` then `member/delete/department`), so the delete triple is not new on that surface; what
      disappears beside it is the revoke. Their earlier framing ("the word changes to delete") would read to a panel
      reader as a missing migration. Their reviewer caught it by reconstructing the pre-swap world and running it.
    - **`withSettingsMutation` has no app caller after the swap**, so phase 9's post-merge follow-up deletes it — together
      with its remaining TEST caller at `events-catalogue.test.ts:139-145`, in the same change, or the lane reds.
    - **The `browser.settings.mutation` census is nineteen emitters, all accounted for on our side:** thirteen are RC's,
      and the other six — `useMemoryMutations` (memory: approve / archive / reject / supersede) and
      `useOutputPreferencesQuery` (output_preferences: update / delete) — already carry `meta.telemetry` from phase 4
      (`e998911`), so they emit through the settle hook and our coverage guard counts them. They are outside RC's task,
      not outside our catalogue.
    - **Exposure tracks the await, not the guard.** Those six call `invalidateQueries` unguarded but do NOT await it
      (`useOutputPreferencesQuery.ts:37`, `:51`), so a rejected refresh is an unhandled rejection rather than a throw in
      `onSuccess`, and cannot flip a landed write. RC's helper awaits its invalidation deliberately, which is why it needs
      the try/catch it has. Unguarded-and-not-awaited is noisy but safe; awaited-and-unguarded is the dangerous shape.
      Closing the noise belongs with whoever converts those two hooks.
    - **Verdict (Opus reviewer, 2026-09-12): `tanstack-t13` `06f6aa3` merges into phase 9's contract cleanly.** All five
      checks and the rollback ruling hold, verified in an isolated copy: thirteen wrappers at the parent commit and zero
      at HEAD, with the only surviving references the definition, our guard and the test caller; every primitive reached
      only from a meta-declaring mutation or from inside a composite, so no surface went dark; all thirteen `mutationFn`s
      await the whole composite, so the duration spans the sequence but not the refresh; their suite re-run unmodified
      23 of 23, and three of their twelve breaks reproduced verbatim.
    - **Ours, opened as M9.8: the refusal label is now false for one population.** `useTenantRoleMutations.ts:157-168`
      throws `MutationRefusedError` only after `deleteRole` has run an N+1 holder scan (one GET per tenant user), so that
      refusal sends many requests and can take seconds. Our panels, the aws widget titles and the catalogue say
      "MutationRefusedError: no request sent", and M9.7's conventions bullet claims a near-zero duration. The arithmetic
      is unaffected — refusals are still counted apart — but the wording is wrong and a later latency view would inherit
      it. M9.8 says "refused before the write was attempted", which is true of both populations, and records that a gate
      may query before refusing.
    - **Ours, for E9.10:** `entity: memory` (`useMemoryMutations.ts`) and `entity: output_preferences`
      (`useOutputPreferencesQuery.ts`) emit `browser.settings.mutation` with entity words absent from §2.1's settings
      list — both predate phase 9, and the panel groups by entity, so the catalogue must name them or say why not. Also
      for E9.10's inventory: `RunsPanel.tsx:913` does a JSON round-trip inside a per-call `mutate(vars, { onSuccess })`,
      a reachable instance of the callback hazard — the dedupe keeps the record right, but the user still gets a failure
      toast for a write that landed.
    - **Volume correction (code-26, 2026-09-12): the refusal shape is not new and the count is not three.** Fifteen
      mutations across seven hook files pair a permission gate with `meta.telemetry` post-merge — tenant roles, tenant
      departments, department roles and team landed in their Phases 4 and 5, so refusals have been emitting on
      `browser.settings.mutation` since then on their branch, not only from the invitations work. The shape is unchanged
      (`outcome: error`, `error_type: MutationRefusedError`, and our split handles it); what changes is the settings
      panels' first live hours — the step change is larger and arrives all at once rather than trailing their remaining
      tasks. Verified here: on `tanstack-t13`, four hook files pair a mutation gate with telemetry (team, department
      roles, tenant roles, tenant departments), consistent with their count.
      A near-miss while checking it, recorded because it is the same failure in our own hands: a grep first counted
      `hooks/settings/useOperatorGrants.ts` as a gated write with NO telemetry — which would have been a real defect,
      since a gated write that emits nothing is invisible in both directions. Opening the file showed its `gate:` is
      prose in a comment about a query's `open` flag. A word counted is not a fact measured. If a converted write ever
      does carry a gate and no `meta.telemetry`, E9's coverage sweep lists it at the merge.
    - **Ruling on the refusal class (code-26, agreed 2026-09-12): it stays ONE class.** Our corrected wording — refused
      before the write was attempted — is true of both populations, and that is the property the discriminator carries. A
      second class would be another thing to keep in sync across their helper, every consumer and our catalogue, for a
      distinction nothing consumes. Their reframing is the better shape and is theirs to fix: the gate is carrying two
      different KINDS of question — "may this user delete roles" is a permission check, "is anybody still holding this
      role" is a precondition check — and the N+1 scan's duration is the visible edge of that. **Revisit if** a second
      gate starts querying before refusing, or anyone builds a view that aggregates refusal DURATION rather than counting
      refusals.
    - **`RunsPanel.tsx`'s per-call `onSuccess` clone is CLEARED** (checked in our tree, fifth pass overall):
      `cloneSnapshot` (`:191`) is a JSON round-trip, and both callers (`:786` and the `onSuccess` at `:893`) pass
      `job.configSnapshot`, a value parsed from a server body — a cycle or a BigInt cannot survive that, so the throw is
      unreachable. The condition that would flip it, recorded rather than the verdict alone: the client-edited
      `snapshotDraft` is never the clone's input, so if any path ever assembles a snapshot client-side and then clones
      it, the line becomes reachable. The SHAPE stays in E9.10's sweep; the site goes in its cleared column with this
      reason attached.
    - **Ours, merge hygiene:** when the post-merge follow-up deletes `withSettingsMutation`, the first half of
      `tests/unit/telemetry/settings-mutation-meta-guard.test.ts:77-99` becomes a vacuous absence assertion — it scans one
      file for a string that can never appear again (§8c shapes 1 and 4). Delete it with the function or repoint it at
      direct `emitSettingsMutation` calls. Its second half is sound; it carries a 13-action presence control.
    - **Theirs, reported back:** the generic-`error_type` exception is five paths, not the ruled three
      (`settings-api.ts:1851` and `:1958` re-wrap for the same "say what half-landed" reason), and one volume claim is
      incomplete — `member/delete/department` loses its head-handover volume app-wide, because `updateDepartment` calls
      the removal primitive that carried that triple pre-swap.
  - **Ruling (2026-09-12): a compensating or rollback request is not a user action and emits nothing**, whatever its own
    outcome. The user did one thing, and the flow's record says what happened to it. Today RC's team add proves the
    point: its compensating revoke calls a still-wrapped primitive, so a FAILED add emits two records — the rollback's
    `member/revoke/tenant` as a success, landing first because the wrapper emits when its callback completes, then the
    flow's `member/create/department` as an error. Read on a panel that pair says "the write succeeded, then something
    else failed", which is why the class is invisible from a dashboard. The assertion is that the count is exactly one
    and that it is the flow's, not merely that the second record is gone — only the former catches a third emitter.
  - E9's double-emission guard is the backstop at the merge: it resolves by the TypeScript checker and fails any
    mutation declaring `meta.telemetry` whose `mutationFn` transitively reaches an action emitter through app code,
    including a rollback branch. `lib/telemetry/**` is opaque to it, so a `logger.warn` is not a double count.
  - **Three surfaces gain records at the merge, not one** (code-26, 2026-09-12). The organization update and the
    department delete both go from silent to recorded, and every gate refusal, still-held role and unreadable scan now
    arrives as `MutationRefusedError` where those paths emitted nothing before, because the old wrapper spanned only the
    inner request. The settings panels are DARK until the merge, so the step change is expected rather than alarming.
  - **The off-list attribute mechanic, measured (2026-09-12).** In production `emitRecord` strips a stray key and KEEPS
    the record; in development it THROWS, and in the settle path that throw is outside the try (only the attrs builder is
    guarded), so a caller bug surfaces loudly. The risk to guard against is therefore not "the record is deleted" but "a
    caller swallowed the throw". The wider rule, from code-26 hitting this class six times: check what the broken code
    actually does before choosing what to assert, because "nothing wrong appeared" and "nothing appeared" are
    indistinguishable to a negative assertion. Assert a key set positively; give every absence assertion a positive
    control in the same test.
  - **Measured 2026-09-12 — the development throw travels through TanStack and flips the write's outcome (E9.9, opened).**
    `lib/query/query-client.ts:13-18` wires the settle hook through `MutationCache({ onSuccess, onError })`, and
    query-core awaits those callbacks inside the same `try` whose `catch` runs the failure path
    (`@tanstack/query-core/build/modern/mutation.js:103,110,122`). So in development a successful write carrying an
    off-list attribute loses its record, is re-reported as an error — a failure toast for a write that succeeded — and
    the error path throws again on the same key, rejecting out of `mutateAsync`. This is what code-26 measured as "the
    record is deleted"; their shared helper is innocent. Production is unaffected: the stray key is stripped and the
    record kept. The discriminator between the two modes is whether a record exists at all.
    **E9.9:** the development-mode catalogue throw must surface out of band, as an unhandled error the console and the
    test lane see, so a caller bug can never change a mutation's outcome or what the user is told. Production behaviour
    unchanged. Anything handed to `MutationCache` config callbacks sits in that same swallow-and-reclassify position, so
    the sweep covers every emitter reached from one.
    **E9.9 extension (2026-09-12, from code-26's 78-handler sweep): the settle hook emits AT MOST ONCE per mutation,**
    keyed on `mutationId`. Their probe found a path that produces two records with OPPOSITE outcomes for one user action
    and no wrapper involved: a per-call `mutate(vars, { onSuccess })` callback that throws escapes the success dispatch
    AFTER the hook-level `onSuccess` and `onSettled` have run, so the success record is already emitted, and then the
    library's error path emits a second record as an error. The AST double-emission guard cannot see it, because both
    records come from the same correct call site, and no panel can tell it from one success plus one unrelated failure.
    The first record wins: it describes what actually happened to the write. Two mechanism facts for the write-up:
    `onSettled` sits inside the same `try`, so moving work there relocates the bug rather than fixing it; and the error
    reducer wipes `state.data`, so an attrs builder reading the response loses it as well as the outcome. Also named in
    the fix: the emit at `mutation-meta.ts:58` is unguarded while the `attrs` builder one line above is guarded, an
    asymmetry that reads as a decision, which is why it survived review.
    **E9.9b widened (2026-09-12, measured by code-26 on their branch).** The condition E9.9's sweep called future is
    already live: their Document Hub conversion put the upload wrapper inside a `mutationFn`. Reading the wrapper
    (`lib/telemetry/events.ts` ~:442-468), the success-side `finish` is called INSIDE the `try` whose `catch` calls
    `finish` again and rethrows. So in development, for an upload that SUCCEEDED and whose telemetry carries an off-list
    key: the success finish throws, its own catch emits a SECOND `upload_finished` whose outcome is derived from the
    telemetry error rather than from the upload, and the telemetry error is rethrown as the upload's — which inside a
    `mutationFn` is the write genuinely failing. The user is told an uploaded file failed, and the surviving record
    describes the wrong outcome.
    E9.9b therefore has two halves: the product-event queue reports out of band, AND the wrapper's structure is fixed on
    its own terms — exactly one `upload_finished` per attempt, its outcome from the upload and never from a telemetry
    failure, and the run's own error rethrown. That second half is a defect with no telemetry involved: any throw from
    the success-side finish becomes a wrong-outcome event plus a wrong error. The sweep looks for the shape — any wrapper
    that emits inside a `try` it also catches — not just this instance. Tests run in development mode specifically, since
    a dev-only throw is invisible to a production-mode lane, which is why neither side's suite caught it.
    Note on the dedupe: keeping the FIRST record is correct here only because the first one happens to be the true one.
    The structural fix is what makes it right; the dedupe is a backstop.
    Their own call sites came back clear today — eleven read response fields unguarded, but every route behind them
    declares a non-optional response model — held closed entirely by backend discipline that nothing on their side
    asserts. They are recording that as its own work.

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
from one closed map in code; E9 records the final (feature, entity, action) table in its notes. Settings `entity` additionally carries `memory` and `output_preferences` (E9.10, 2026-09-12): both predate phase 9, both emit `browser.settings.mutation`, and both are now catalogued through the settings-entity list and its typed helper rather than excluded. The limit is named in code — the emitter checks attribute KEYS, never values, so a raw `meta` literal can still sidestep the word map, as it can the feature action map. `flow` ∈ {`register`,
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

### F9.9 — One precedence for the server's own sentence (post-close, 2026-09-11; reported by the owner's TanStack session)
A failed write through a Next proxy showed the user "HTTP error! status: 500" instead of the server's sentence.
`apiRequest` read only a `message` key, while the proxy routes refuse with an `error` key, and the repo carried four
different orders across the throwers and the classifier.
- **Files:** `lib/api/utils.ts` (`serverErrorText`, `statusFallbackMessage`, `isStatusReadout`, `MAX_SERVER_SENTENCE`, and
  the three live throwers), `lib/api/error-handler.ts` (the explanation reader), `tests/unit/api/server-error-text.test.ts`.
- **One order everywhere:** `message`, then `detail`, then `error`. A value is a sentence only if it is a non-blank
  string within the 300-character cap; anything else falls through to the next key and then to the status fallback.
  Neither leg is truncated.
- **A bare status readout is not an explanation**, in either spelling the repo produces, so an unexplained 4xx shows its
  canned sentence instead of the raw readout. The check is anchored, so a sentence that merely contains a status line is
  still the server's words.
- **Unchanged:** the classifier's per-status behaviour. 401, 429 and every 5xx are byte-identical, so a server error
  still shows its canned sentence and no upstream text can reach a user through a proxy 5xx.
- **Not touched:** the proxy routes (N9's files) and every feature call site.

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

### M9.7 — Refusals kept apart on the settings side (post-close, 2026-09-12)
M9.6 split client-side refusals out of the feature failure ratio. The settings panels had not met the shape yet. Now
that RC's invitations conversion emits it, the "Settings changes by entity" panel and its aws twin would report a
refusal as an error, so the same split applies there: the failure stream excludes `error_type="MutationRefusedError"`
and a second target counts refusals. The catalogue row and aws bullet follow, the M9.6 guard grows a sibling for the
settings breakdown, and both surfaces keep their DARK note until the conversion merges. The catalogue conventions also
gain the rule that a later latency view over mutation records reads successes only.

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

### P9 results — 2026-09-11 (session lead; evidence in `copilot-mro/.dev_runs/obs9-probe-20260911/`)
**Set-up.** Integration tree `obs9-probe` = `agent_sdk` + `obs9-browser` `af9f307` + `obs9-events` `08b7650` + `obs9-server`
`c52f034` (0 merge conflicts; `logger.ts`, `events.ts` and `mutation-meta-emitters.test.tsx` auto-merged; the merged tree's
guard and shared-file tests 46/46) + one probe-only commit (sampling ratio 1, the `/probe` forcing page, root-layout and
SSR error toggles); `next build` clean (type check + lint), served by `next start`. api `api-obs9` `46a86fc` run on the
CURRENT checkouts — the pinned bundle env's editable installs still point at 2026-09-05 copies in `wt-obs-u/*`, so
`PYTHONPATH` put `api-obs9`, `utils`, `core`, `copilot-mro` and `shift-optimizer` first. The `oss` stack from
`copilot-mro-obs9` at port prefix 3 (project `flynapse-otel-p9`); Grafana started as the M9 smoke starts it and attached
to the P9 network. Logged in as the e2e owner through CDP Chrome (credentials read by a script, never printed).
**Checks.** 1 PASS — Loki carries `browser.web_vital`, `browser.app.boot`, `browser.auth.login`, `browser.error`,
`browser.log` and, new, `browser.feature.mutation` (automation create + delete), `browser.auth.flow`
(forgot_password/code_request), `browser.automation.run_triggered` (manual, `mro`, `accepted`) and `run_settled`
(`failed`, observed wait 27 s), `browser.export.requested` (optimizer run, xlsx), `browser.ad_review.disposition_set`
(confirmed_applicable from the dialog, cleared from the table) — one record per action; not exercised: optimizer
run triggers (they would solve the owner's pinned plan-of-record jobs), Data Discovery (not open to this account), the
settings and Document Hub writes (the TanStack conversion's now), comments and the work-order export (they need
S3/Bedrock). 2 PASS — the documentLoad/documentFetch/resourceFetch spans for `/help?invite=probe-token&chatUserId=…#frag`
exist with query-less URLs, and nothing in Tempo or Loki carries `probe-token`, `chatUserId`, `frag-probe` or `X-Amz-`;
the S3 presigned-preview half was blocked by an expired AWS SSO token. 3 PASS — browser body `probe warn body [email]
https://probe-bucket.s3.ap-south-1.amazonaws.com`, backend body `… for **** with token ****`. 4 PASS for the render error
(`react_boundary`), `global-error` (`global`) and a network failure (reference → an ERROR span with status 0) — each
on-screen reference equals its record's trace id; a real server-500 toast was not observable (the 500s met are handled
inline, D9-9), though the chat failure's `browser.log` record shares the failed request's trace id and carries
`url.template` and the status but no server text; the SSR error wrote one `onRequestError` JSON line. 5 PASS — the Next
route `/api/tenant/organization` → the api SERVER span's parent is the browser fetch span. 6 PASS — the first request of
each cold load is traced. 7 PASS — both upload spans are children of `browser.chat.turn` (attachment_count 1,
attachment_upload_ms 472). 8 PASS — `url_template` series for the dashboard; Tempo demand 1,910 ≪ 100,000. 9 PASS — all
8 boards and 4 datasources provisioned and healthy; panels with data 1–6, 9–11, 13, 15, 16, 17A; empty for known
reasons 12, 14, 17B, 18.
**Findings.** (a) core's ingest `_pass_through` turns a client disconnect (`starlette.requests.ClientDisconnect`, the
browser abandoning an in-flight export on a full-page navigation) into an ERROR with a traceback and a 500 — 12 of 52
ingest requests in the probe; the routes are excluded from request metrics, so it is log noise, not an alert → stream
C9. (b) The owner's local `api/.env` sets `OTEL_SERVICE_NAME=copilots` (plus the dead `OTEL_ENABLED` / `OTEL_ENDPOINT`), so
locally the api reports as `copilots`; App Runner sets `api` — an owner item (the probe ran with `OTEL_SERVICE_NAME=api`).
(c) The automations failed-run panel says "contact support with the time of this run" rather than showing a reference —
§9. (d) Probe-set-up slips, no app defect: the first Grafana picked up the legacy provisioning path; an AD clear first
missed its `role="alertdialog"` confirm (then cleared properly — the dev data is restored); the owner's `deployment`
Loki/Tempo crash-loop and the leftover `flynapse-otel-probe` collector are untouched.

## 8. Review design — two phases

**Phase A (now, Opus 5):** one fresh adversarial reviewer per stream (F9 includes the api change), briefed with the
stream's section + §0 + §2 + §8a + the diff, running the suites itself and trying to break the work — defect absence,
not guard presence; every test must fail without its fix. Triage, fix pass, re-verification, brief into §10.

**Phase B (Fable, when the limit returns; after the phase-8 chunks R0–R5):** five bounded chunks, one fresh Fable agent
each, in merge order — R6 **design** (§0, §2, §8a, the stream split and file ownership) → RC the owner's TanStack conversion (design + code, from its own plan; merged into `agent_sdk` first, after which each obs9 dashboard branch merges `agent_sdk` and re-runs its lanes) → R7 F9 (dashboard + api) → R8
E9 → R9 N9 → R10 M9 (copilot-mro `deployment/**` + iac). A tiny core chunk R11 (C9, the P9 finding) follows R10; it merges into core `master`. A chunk's merge follows its verdict: dashboard branches
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
| D9-17 | One emission per user action: TanStack mutations via `meta.telemetry`; a direct write once — in the API-layer method when every caller is direct, else at the call site; an AST guard proves no `meta.telemetry` mutation calls a self-emitting method; E9 converts no direct write to `useMutation` | (a) E9 converts the TanStack audit's 34 writes itself; (b) call-site wrappers everywhere | (a) brings pending-state, invalidation and cascade behaviour changes that are that audit's scope and the owner's call; (b) leaves every later conversion to remember to remove a wrapper; the rule keeps counts right whichever way each site ends up. The `meta.telemetry` literal is written INLINE at the call site, and that is not a style preference: the guard reads it as syntax, so a meta hoisted for tidiness reports as missing — inline is the difference between a write being counted and being invisible |
| D9-18 | M9's branches are stacked on the phase-8 D8 branches (merges `9976fa7c`, `9231863`) | branch from the mainlines and rebase after R5 | M9 edits the same catalogue, guard and runbook files and extends their fixture lists; stacking removes the conflict and R10 already follows R5 |
| D9-19 | Server log lines go through `process.stdout/stderr.write` via a sink and a request-context store on `globalThis`, registered by the server-only modules; `logger.ts` never imports a server module | import a server-log module from `logger.ts`'s server branch; `console` output | `logger.ts` is in ~71 client modules (a server import breaks or bloats the client bundle); separate server bundles would each get their own module singleton; production builds strip `console.*` |

### 8b. Phase A close — gate agenda (drafted 2026-09-11; all tips filled)

Branch tips the Fable chunks review — each chunk's reviewer starts from its §10 brief plus this table:

| Chunk | Tree → branch @ tip | Base | Suite evidence (last run) |
|---|---|---|---|
| R6 | this plan: §0, §2, §8a (D9-1…D9-19), §1b (stream split, file ownership, the TanStack coordination and merge rules), §7 "P9 results" | spec §3.3, §3.4, §7.4, §9 | — (design review) |
| RC | the owner's TanStack conversion — `/home/aditya/Code/dashboard-tanstack` `tanstack-conversion` @ `c68b869` for the gate (measured: three commits above the pin, one file, +4 lines, nothing a test reads) — the trial merge is pinned at `b728d33` because every commit between touches only their plan document, so the merge surface is identical (101 commits off the base at `b728d33`; verified to contain all twelve task branches `tanstack-t11`…`t18`, `tanstack-guard`, `tanstack-phase3-fix`), plus core `/home/aditya/Code/core-tanstack` `tanstack-dept-delete` @ `401c2a6`; reviewed from its own plan | `agent_sdk` `b87ced0`; core `master` | its own |
| R7 | `/home/aditya/Code/dashboard-obs9` `obs9-browser` @ `01a3882` (includes the post-close F9.9 and F9.10); `/home/aditya/Code/api-obs9` `obs9-api` @ `72df51a` | `agent_sdk` `b87ced0`; api `langgraph-merge` `a19a931` | unit 1853/1853, `tsc`, eslint; api middleware + infra 322 |
| R8 | `/home/aditya/Code/dashboard-obs9e` `obs9-events` @ `bc9fbcc` (includes the post-close E9.9, E9.9b and E9.10) | `agent_sdk` `b87ced0` | unit 1866/1866, typecheck, eslint |
| R9 | `/home/aditya/Code/dashboard-obs9n` `obs9-server` @ `7fc2bcc` (includes the post-close N9.6) | `agent_sdk` `b87ced0` | unit 1877/1877, typecheck, eslint; `next build` clean |
| R10 | `/home/aditya/Code/copilot-mro-obs9` `obs9-deploy` @ `83f4a8f7` (deployment, the otel tests and the observability runbooks — no conflict-zone path; stacked on `obs8-dashboards`); `/home/aditya/Code/iac-obs9` `obs9-iac` @ `b72307b` (stacked on `obs8-iac`) | `langgraph-merge` `bc0e3858` + `9976fa7c`; `main` `5996e5a` + `9231863` | full otel lane 83 incl. both smokes (before M9.6); after M9.6, M9.7 and M9.8 static + rules 79 passed / 8 skipped, `validate-rules.sh`, `terraform validate` |
| R11 | `/home/aditya/Code/core-obs9` `obs9-core` @ `8e3c3ce` (telemetry ingest and product events: one clause each, plus two test files; C9.2 fixes a phase-5 test's seed-date time-bomb; N3 adds a unit test for the real-clock default) | core `master` `988571b` | `tests/api/logging` 47, the error-disclosure sweep 113, `tests/unit/infra` 47, `tests/api/analytics` 32, `tests/db/analytics` 98, `tests/unit/analytics` 70 |

The three dashboard branches were merged together once already, on P9's throwaway tree: 0 conflicts, and the shared-file and
guard tests passed 46/46 there.

**Merge mechanics per chunk (session lead, after each Fable verdict):**
- **RC's own chunking, for the gate (code-26, 2026-09-12).** One branch, so phase 9's integration has no ordering
  problem, but the gate reviews it in nine chunks in this order: **RC-D, then RC-1 through RC-8.** RC-D is first because
  its rulings bind every later chunk; RC-1 is second because it owns `lib/query/query-keys.ts`, which five of the eight
  chunks touch and which is the branch's real cross-chunk surface. Three chunks are non-contiguous in history (RC-1's
  guard merge landed after five later merges, and RC-3's fix pass landed inside RC-4's territory and splits it), and
  RC-5's Task 10 is the core commit, which never appears in a dashboard diff. Per-chunk ranges and file ownership:
  `.superpowers/sdd/tanstack-mutation-conversion/rc-chunk-ranges.md` on their branch, cross-checked both directions
  against the changed-file list (158 = 158, no file in zero chunks).
- **Do not merge the task branches.** `tanstack-t11`…`t18`, `tanstack-guard` and `tanstack-phase3-fix` are all absorbed
  into `tanstack-conversion` — verified independently on both sides with `git merge-base --is-ancestor`. Each keeps a
  local ref and a tip of its own, which is exactly what makes them look live; merging one on top would be a no-op at
  best and would resurrect a pre-fix state at worst.
- **Lane figures to treat carefully.** Their dashboard lane is 2118 of 2118 measured at `f2bfbbf`, one commit below the
  tip, and the tip commit touches only a plan document — so the tip's lane state is INHERITED, not re-run, and they said
  so rather than quoting it as measured. Their core figure (197 passed) is a scoped run, not core's full lane. The trial
  integration's own lane runs are therefore the first measurement of either side on a merged tree.
- **Both of their guards are still owed at the merge, deliberately:** the `events-envelope` test still asserts the throw
  E9.9b removed, and the `EVENT_NAMES` exact-list pin is not yet loosened. They left both for the merge because E9.9's
  version is the contract and their rewrite goes on top of it; doing it early would have meant rewriting against a
  contract they would then re-resolve. The trial merge fixes both and reports which.
- **RC first.** The owner's conversion merges into `agent_sdk` (its core branch into core `master`). Each obs9 dashboard
  branch then merges the post-RC `agent_sdk` and re-runs its full lane and `tsc` before its own chunk, applying the §1b
  merge rules. In `useOptimizer.ts` the two `meta` edits are combined. The settings-api department blocks come from RC.
  The `ReviewStep` and `CanvasHeader` call-site wrappers give way to the hook path. E9's coverage sweep will list the
  converted mutations that lack `meta.telemetry`, and they get `browser.feature.mutation` meta. `withSettingsMutation` is
  deleted if it is dead, and the guard's pin is updated. `useAppMutation`'s inner `useMutation` gets its exemption.
- **R7, R8, R9.** `obs9-browser`, then `obs9-events`, then `obs9-server` merge `--no-ff` into `agent_sdk`, with the full unit
  lane and `tsc` after each. `obs9-api` merges into api `langgraph-merge`.
  Ordering note (F9.9 review): between R7 and R9 the Next proxies still answer a 5xx with the upstream error's text, and
  F9.9 now carries that text into the browser's thrown message. Nothing renders it and every 5xx still classifies to its
  canned sentence, so there is no leak in the gap; N9's constant-body route error response closes it at R9.
- **R10, after phase-8 R5 has merged D8.** `obs9-deploy` merges into `langgraph-merge` (it touches no conflict-zone path) and `obs9-iac`
  into `main`. If Fable changed D8 at R5, merge the new D8 tips into the obs9 branches first. Then run the otel lane and
  `terraform validate`.
- **R11.** `obs9-core` merges into core `master`, then the core logging lane runs. The trial merge showed this may run BEFORE RC's core commit at no cost, and doing so cures the 9 contract failures core `master` carries today instead of leaving them red for the whole window.
- **After R11.** Re-run P9 checks 2, 4 and 5 on the merged mainlines, as a short re-probe.
- **A trial integration merge runs before the gate (2026-09-12).** The owner's conversion finished, so a throwaway tree
  merges RC then F9, E9 and N9 on top (and, in core, C9 then `tanstack-dept-delete`), applying the §1b rules and doing
  the post-merge work, so the gate sees measured conflicts, red guards and re-checked counts instead of predictions.
  Trial branches: `obs9-trial-merge` in both repos, worktrees `dashboard-obs9x` and `core-obs9x`; nothing pushed and no
  existing branch touched. Reports: `scratchpad/phase9-trial-merge-{dashboard,core}.md`.
- **Core trial merge result (2026-09-12; `obs9-trial-merge` @ `694113a` in `core-obs9x`, kept for inspection; re-pinned to their `401c2a6` and re-measured).**
  - **Zero conflicts at both merges.** C9 and `tanstack-dept-delete` are file-disjoint, and the merge was proved to
    invent nothing: the diff from each parent to the merged tree is byte-identical to the other parent's own diff from
    `master`. `tanstack-dept-delete` is based on `988571b`, one commit on top.
  - **Every R11 count re-checks exact on the merged tree:** logging 47, analytics 32, the disclosure sweep 113, infra 47,
    unit analytics 70, db analytics 98, plus the department-delete lane 8 (5 before their new guard) and authz departments 23. Whole-suite collection
    2795, exit 0. A scratch provenance plugin reported one checkout root for every imported module in every lane, so the
    counts are the merged tree's and not another checkout's.
  - **C9.2's clock pin is load-bearing now, not merely present:** the run was 12 days past the seed's date and the
    contract file passes 20 of 20 at the real clock.
  - **Nothing is red on the merged tree; the red is on the parents.** `tests/api/analytics` fails the same 9 contract
    tests on core `master` alone AND on `tanstack-dept-delete` alone — the time-bomb C9.2 cures.
  - **Sequencing gain, adopted: R11 may merge into core `master` BEFORE RC's core commit, at no cost.** §8b's order put
    R11 last, which would leave core mainline 9-red for the whole RC→R11 window. C9.2 is tests-only and provably disjoint
    from RC's two files, so merging R11 first cures the red immediately and changes nothing else. Fable still reviews in
    the agreed chunk order; only the core merge moves.
  - **Item 1 fixed on their side (core tip now `401c2a6`, verified: one commit above `7288d06`, tests-only, +64 lines,
    two commits off `988571b`).** The new guard is parametrized over all three services, because the second and third run
    inside a comprehension over the first's result, so a guard on one is not a guard on the sequence. Their measurement
    of the gap is the part worth keeping: the realistic future break is not moving the call — the docstring's reason makes
    that look impossible — but making the gathering RESILIENT, a `try/except` carrying on with an empty list, which would
    delete the department and silently under-evict with no error anywhere. That break fails all three new
    parametrizations while leaving the five original tests green. Confirmed independently on the merged tree: the break fails all three new parametrizations and leaves all five
    originals green — including the one whose name sounds like it would catch this and does not, which is the finding more
    than the red is. The file was restored byte-identically, sha256 checked both ways.
  - **Item 2 recorded by them as a Future Improvement, with a caveat that generalises:** their Task 10 review cleared the
    eviction by READING the api middleware rather than measuring it, so the clearance rests on a premise — that the
    middleware honours the declared user list without a role lookup — and expires if that key's handling changes. They
    wrote it with the condition attached. The complete fix is one api-repo test driving such a declaration through the
    real middleware; it is outside their fence, and outside phase 9's scope, so it is an owner item rather than work
    either side takes now.
  - **Two items for RC's own review, not for this merge:** their `_affected_user_ids` runs inside the try BEFORE the
    delete, so a fault in the three services now returns a 500 and leaves the department undeleted where it previously
    deleted — fail-closed and defensible, but an unpinned behaviour change in the delete's error path; and the eviction
    half of `role_user_ids` lives in the api middleware, so no core lane can prove the per-user eviction happens.
- **Every count in this plan is branch-relative.** The censuses, coverage floors and entity lists were measured on
  worktrees cut from `b87ced0`. After each chunk merges, re-run that branch's full lane and re-check the numbers this
  plan quotes against the merged tree: a figure that was true when written can be false after a merge that touched
  nothing it names.

### 8c. Guard audit — absence assertions that could pass for the wrong reason (2026-09-12)
Prompted by code-26 hitting this class six times: a test asserting "nothing bad appeared" also passes when nothing
appeared at all. An Explore agent audited every absence assertion in the three dashboard trees. **Rule adopted (D9-20):
every absence assertion carries a positive control in the same test run** — assert the key set positively, assert the
sibling path still fires, assert the sweep scanned something — and a rewritten guard is not done until it is shown
catching the breakage it is meant to catch.

The shapes found, most deceptive first:
1. **The emit path is dead by construction.** The test never triggers what it says must not settle, so a renamed event, a
   drifted stub URL or an unwired effect all read as a pass.
2. **Records filtered by a string literal rather than the catalogue constant.** A rename empties the filter: positives
   fail loudly, negatives pass silently. Structural, so it multiplies every other shape.
3. **A render proved to exist but not to have run.** "The button rendered" proves a click, not that the handler did
   anything.
4. **A static sweep with no presence control.** `deepEqual(offenders, [])` over a scan that returns early on a missing
   path and never counts what it read.
5. **A capture not proved live in the same test.** An empty array of posts cannot distinguish "nothing posted" from
   "nothing was wired".
6. **A regex that does not match empty output.** An absence claim over HTML that is empty because the component threw.
7. **A presence control in a sibling test only.** Later tests iterate the same helper with nothing proving it returned
   anything.

Also found, the production-side version of the same class: the session watcher wraps its whole fact-emitting block in a
catch, so a bug there becomes no session fact, silently, and every absence assertion downstream of it is suspect. Handled
with E9.9's out-of-band rule rather than by removing the catch.

Fixes: **F9.10** (done — `legacy-module-absent`, `global-error-page`, `support-reference`), **N9.6** (done — `server-routes-wrapped`, `instrumentation-hook`), and **E9.10** (done — `long-running-settles`, plus the pre-existing `document-card-open`,
`logger-wrapper-browser` and `events-envelope`, which no stream had modified). Judged sound, with a positive control
already in the same run: the provider propagation, catalogue, product-events, document-view, hub-preview, logger
warn-path, mutation-meta, optimizer canvas, session lifecycle, network-failure, api-error-text, log-body, export-url,
server-log-sink and every N9 server-route sweep.

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
- **Automation failed-run reference (P9 finding (c)).** The automations run panel tells the user to "contact support with the time of this run". Complete solution: show the run's trace reference (its root span's trace id) with a Copy button, as the error boundaries now do. Outside phase 9's files.
- **aws browser alarms (D9-11)** — author the documented filters and alarms once the owner rules on the alarm dialect
  and B1b verifies the stored field paths.
- **Call-site wrappers inside a future `useMutation`.** D9-17's AST guard covers API-layer emitters; a later conversion
  that moves a call-site-wrapped write into a `mutationFn` and also adds `meta.telemetry` would double-count until a
  site test catches it. Complete solution: the conversion removes the wrapper in the same change (named in the TanStack
  audit's checklist when it is executed).
- **Core's shared 500 funnel breaks the constant-message rule (C9 review).** Two sites:
  - `core/resources/http_errors.py` `internal_error` logs the caller's context, with its interpolated ids, together with
    the traceback as one message.
  - The "collector forward failed" line in `logging_endpoints.py` binds the exception's text.

  Complete solution: `internal_error` takes a constant event name plus bound fields, and attaches the exception through
  loguru's exception option. The forward failure binds the exception's type name, not its text. Deferred because every
  core router shares the funnel, which puts it outside C9's one-clause fix.
- **Composite writes report a coarse `error_type` (ruled 2026-09-12; RC's swap lands with it).** Three of RC's composite
  failures report `Error` instead of the failing step's class, for two reasons in the API layer rather than in the
  mutations: the role delete's scan returns a message string instead of throwing, so the class is gone by the time the
  mutation rejects; and the department create/update head step is deliberately re-wrapped to say "created, but the head
  could not be assigned", which replaces the class along with the message. Accepted for now: the outcome and the duration
  are correct in all three, nothing phase 9 charts keys on those classes, and reshaping user-facing failure text inside a
  telemetry change is the mixing this phase has refused elsewhere. Complete solution, as its own task with its own
  review: the head case keeps its sentence and gains a NAMED error class of its own (`error_type` is a class, never a
  message), and the scan throws a typed error instead of reporting failure in its return value — a step that reports
  failure in a return value cannot be seen by anything downstream, telemetry included.
- **The classifier's two branches disagree about a sentence containing a readout (F9.9 re-verification).** The
  plain-`Error` branch (`error-handler.ts:159`) still makes its readout decision with an unanchored pattern, so a server
  sentence that contains a status line keeps its explanation inside an `ApiError` and loses it as a plain `Error`.
  Complete solution: that branch asks `isStatusReadout` for the decision and keeps its own pattern only for extracting
  the status. Deferred: low impact, since a server would have to echo the literal.
- **Four error readers still read `detail` first (F9.9 review).** `fetch-utils.ts` `describeApiError`,
  `improvement-api.ts` `describeFailure`, `optimizer-api.ts` `optimizerErrorDetail` and `client.ts:52`
  `fetchJsonWithStatus` keep their own order, and the last reads `detail` only, applies no cap, and throws an error
  whose message IS rendered raw (`TenantAllChatsPanel.tsx:237`, `DataViewModal`). Complete solution: one ruling on the
  array and object legs those richer readers parse, then the shared `serverErrorText` everywhere, with the cap.
  Deferred because the ruling is bigger than the bug F9.9 fixed.
- **A timer flake under load (F9.10, 2026-09-12).** `tests/unit/mro/ad-review-materialize-hook.test.ts` failed once on a
  poll-timing assertion during a lane run with five full suites running concurrently on the box, and passed 7 of 7 in
  isolation and on the clean lane. The file is E9-adjacent and F9.10 does not touch it. Complete solution: drive the
  poll with a fake clock rather than wall-clock waits, so the assertion cannot depend on scheduler latency. Watch for
  recurrence under load before spending the change.
- **Three per-call callbacks dereference a response field, so an absent field reports a landed write as failed (E9.10
  sweep, 2026-09-12).** `OutputsPanel.tsx:122` reads `run.id`, `ActivitySetupPanel.tsx:932,935` read `saved.id`, and
  `UploadStep.tsx:81` reads `created.id`, each inside a per-call success callback — the position where a throw escapes
  after the write has landed, so the user is told a successful write failed. They are unreachable today only because
  every route behind them declares a non-optional response model; nothing on the client asserts that, and the API layer
  casts bodies rather than validating them (28 such casts in the optimizer api alone). Complete solution: response
  validation at the API layer, so a missing field is a typed failure at the boundary instead of a throw inside a
  callback. Deferred because it is a product decision about where validation lives, not a per-site guard — and guarding
  three sites would leave the class open. The owner's TanStack session reports the same class on its side: eleven
  unguarded reads held closed by backend discipline alone.
- **A past-dated invitation stub (C9.2 sweep).** `tests/api/invitations/test_invitation_endpoints.py:58` stubs an
  invitation whose expiry, 2026-08-20, is already in the past. So the resend email's "expires in N days" value now
  clamps to 1. No test asserts that value today, but a future one would fail. Complete solution: build the stub's expiry
  relative to the test's clock.
- **The product-events 429 is silent (C9 mini pass).** When `POST /analytics/events` refuses a flooding caller with a
  429, it logs nothing. The telemetry ingest module logs its rate-limit refusals at WARNING, as an operator-actionable
  signal. Complete solution: one constant WARNING per window per caller on both surfaces, bound to tenant and user.
  Deferred because it was outside the disconnect fix.
- **Browser batches in flight during a full-page navigation are lost and never counted (C9 review residual; for R7).**
  The exporter's force-flush re-sends only batches still in its queue. A plain POST already in flight when a full-page
  navigation starts is cancelled with the page and never counted as dropped. So each core 499 probably means one lost
  batch, and core's INFO line is its only record.

  Measure this on real use first. P9's 23% rate is inflated by CDP-driven full-page loads, and SPA route changes do not
  cancel fetches. Complete solution: send every export whose body fits the browser's 64 KiB keepalive budget with
  keepalive, tracking the in-flight total, so a navigation no longer cancels it. Larger batches stay plain and keep
  today's behaviour.

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

### F9.9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY**; four P2 and two P3, two of them fixed in a fix pass)
Scope: `dashboard-obs9` `af9f307..4df943f`, then the fix pass to `279df2f`.
- **Behaviour proved by matrix.** The reviewer compared the classifier old against new over 7 statuses × 11 payload
  shapes × 2 constructor messages. 32 rows change, all in the 400, 404, 409 and 422 arms, and every one is an
  improvement. 401, 429 and 5xx show zero deltas, so no upstream text can reach a user through a proxy 5xx.
- **Tests honest.** With the production files reverted, the new file is 6 red of 9. The reviewer re-proved four
  mutations itself, restoring byte-identically.
- **Consumers walked.** `apiRequest`'s only client consumer swallows its mutation errors and renders a constant, so the
  reported symptom lands at the classifier and at the TanStack session's converted call sites, not in this tree's panel.
- **Telemetry contract intact.** The logger already refuses a status-carrying error's message, `error_type` stays the
  error's name, and both F9 guards cover these files and pass.
- **Import graph verified:** the helper lives in `utils.ts` because the alternative home imports a toast package and
  `utils.ts` is imported by eleven server route handlers. The change adds no import.
- **Findings:** the readout rule matched only one of the two spellings the repo produces, and the cap did not cover the
  constructor-message leg — both fixed in the fix pass, with the readout check deliberately shape-only rather than
  status-matched. The plan update and the deferral inventory (§9, four readers) were the other two P2s. Two P3s: the
  headline wording, corrected in the notes, and the N9 merge-order coupling, recorded in §8b.
- **Lanes:** unit 1850 of 1850 at `4df943f` and 1852 of 1852 after the fix pass, `tsc` clean, eslint clean.

**Re-verification of the fix pass (`4df943f..279df2f`) — MERGE-READY, one new P3.**
- The shape-only readout check is right, and better than the status-matched one the reviewer first suggested. Over 18
  message shapes: both literals are swallowed; the anchors hold, so a sentence that merely contains a status line keeps
  its words; whitespace and digit-count variants behave; and a readout naming a status the proxy converted is swallowed,
  where a status-equality test would have shown it. The only sentence the rule can lose is a body that is exactly a bare
  readout, which is noise by definition. Recognising both spellings also beats repointing, because a third producer
  exists and the classifier's other branch reads that literal to refuse the same shape.
- Readout-then-cap is observationally equivalent in both orders, and neither leg truncates. A message at exactly the cap
  is shown whole; one character more is canned.
- The matrix re-ran at 7 statuses × 11 payload shapes × 4 constructor messages: 72 rows change, none at 401, 429 or 500,
  and every change falls into one of four improvement classes. No row loses a sentence a user should see, and none gains
  one it should not.
- Test honesty re-proved: exactly the two new cases are red at the previous tip, and all three mutations were caught and
  restored.
- **New P3 → §9:** the classifier's two branches now disagree about a sentence that contains a readout. The
  plain-`Error` branch still decides with its own unanchored pattern, so the same string keeps its explanation inside an
  `ApiError` and loses it arriving as a plain `Error`.

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


### Stream C9 — review brief (reviewer Opus 5, 2026-09-11; verdict **MERGE-READY**; six P3s — four landed in a mini pass, two recorded)
**Scope:** core-obs9 `988571b..88bbca5` (two files).

**What the reviewer checked:**
- The module under test loads from core-obs9. This matters because the bundle venv's editable installs point elsewhere.
- Lanes: 203 passed.
- Fail-before reproduced: 4 of 9 tests fail on the base module.
- Mutations: 12 of 12 caught — the clause removed, a 500 or 204 instead of 499, WARNING or ERROR level, an
  interpolated or placeholder message, a traceback attached, a forward inside the clause, an extra log key, a body on the
  499, the clause widened to other errors, and `public` made constant.
- A real-server probe: uvicorn under both h11 and httptools, behind a gateway-shaped middleware chain that includes the
  api's real logging middleware. Two shapes were tried: half a body then close, and the full body then close during a
  slow auth hop.
  - The base logs one ERROR plus a WARNING 500 line. The tip logs one INFO plus an INFO 499 line. Nothing is forwarded.
  - uvicorn never writes to a client that has gone, and a connected client reads a clean 499 under both parsers.

**Lens conclusions:**
- Nothing reads the body before the pipe.
- A disconnect always surfaces as starlette's `ClientDisconnect`, because BaseHTTPMiddleware passes it on as a
  disconnect message.
- Both rate limiters run before the read.
- No span, metric, counter or alert counts a 499 as a failure. The ingest routes are excluded from the api's OTel server
  instrumentation, the api alert keys on 5xx, and the auth-rejection counter counts only 401 and 403.
- loguru 0.7.3 puts the kwargs into `extra` and leaves a message with no braces unchanged.
- INFO lines ship: the level defaults to INFO and iac does not override it.
- The three deviations are accepted.

**Findings and triage:**
1. The notes claimed a gateway server span that does not exist. Corrected in §11 and in the notes.
2. The notes' reason for returning a bare `Response` was only half right. A starlette `HTTPException` can carry 499 when
   given a detail, but FastAPI would then send a JSON body. Corrected in the notes.
3. The test covered the rarer shape. The more common one — the full body arrives and the client leaves during the auth
   hop, so uvicorn delivers the disconnect first — joins the parametrization as a zero-chunk case. "Mid-body" becomes
   "before the handler read the body". Mini pass.
4. The sibling route `POST /analytics/events` has the identical defect. R11 is widened with the same clause, test-first.
   Mini pass.
5. The shared 500 funnel's interpolated message and the forward failure's exception text go to §9.
6. The 413, 415 and 400 refusals log nothing. Disposition: no change.
   - The browser already counts them, as `rejected` with `last_status` in `browser.telemetry.dropped`.
   - A server line per refusal on an anonymous route would give callers a way to inflate log volume.

**Residual risks:**
- In-flight browser batches are lost during a full-page navigation (→ §9, for R7).
- The App Runner / Envoy proxy path was not tested. Either way it produces no ERROR.
- The probe used stand-ins for four gateway middlewares. A source search confirmed that none of them reads the body.

**Re-verification of mini pass `88bbca5..bd18984` — MERGE-READY.**
- Lane counts match the implementer's.
- Fail-before confirmed: 8 of 13 on the ingest test, 2 of 4 on the events test.
- Mutations on the new events clause: 11 of 11 caught.
- The events route's server span records 499 with status UNSET. Every panel and alert keys on `5..`, so nothing counts
  these as failures.
- The widened return annotation is ignored, because `response_model` is explicit.
- On the events route, the INFO line's volume is bounded by authentication, which fails closed before the read, and by
  the gateway's global per-IP limiter (500 per minute per replica). That limiter does not exempt the route, so it is not
  bounded by authentication alone.

**New P3s:**
1. The notes understated that bound. Corrected.
2. The 9 `tests/api/analytics` failures are a date time-bomb in our phase-5 test, not an environment gap.
   - The seed fixture pins its clock to 2026-09-01, while the panel route reads the real clock.
   - The test asks for a one-week window, so the seed rows fell out of it around 2026-09-08. Those tests have been red on
     core `master` since then.
   - A tests-only fix is running as C9.2.

**C9.2 re-verification (`bd18984..7264e2e`) — MERGE-READY.**
- The pin reaches the route: the route imports the service module and looks the function up at call time.
- The pin replaces only the clock input. No analytics SQL reads the database clock, so queries, windows and row shapes
  still run for real.
- The reviewer repeated the proof with the scratch plugin at +30 days: the old file failed 9 of 20, the new file passed
  20 of 20. `tests/api/analytics` passed 32 of 32 at the real clock.
- New P3 (N3): after the pin, no test covered the service's real-clock default. It landed as `8e3c3ce`: a unit test of the real-clock
  default, which four mutants fail. The session lead reran unit analytics and infra: 117 of 117.

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

**F9.9 (post-close, `4df943f` + fix pass `279df2f`) — one precedence for the server's own sentence.** Origin: the owner's
TanStack session reported that a failed comment write showed "HTTP error! status: 500".
- Root cause: `apiRequest` read only a `message` key, the Next proxies refuse with an `error` key, and four different
  orders existed across the throwers and the classifier.
- Fix: `serverErrorText`, `statusFallbackMessage`, `isStatusReadout` and an exported cap in `utils.ts`, used by the three
  live throwers and by the classifier's explanation reader.
- Deviation, accepted: the helper lives in `utils.ts`, not in `server-error-message.ts`, because that module imports a
  toast package and `utils.ts` is imported by eleven server route handlers. The readout check takes no status argument;
  a readout naming a status the proxy has since converted is the same noise to a user.
- Also better for users: a validation payload no longer renders as "[object Object]", an over-long body no longer rides
  into a toast, and an unexplained 4xx shows its canned sentence.
- Tests: 11 cases in a new file; 8 of them were red before their fix, and 11 mutations were each caught and restored.
- Lanes: unit 1852 of 1852, `tsc` clean, eslint clean.
- Learning: a shared classifier can normalise a payload and still leave the thrown message generic. Anything a call site
  reads directly needs the sentence in the message itself.

**F9.10 (post-close, 2026-09-12) — the guard audit's F9 fixes.** `01a3882`, three test files, no production code.
- `legacy-module-absent.test.ts`: the sweep's walk returns early on a missing path and counted nothing, so a wrong root
  read as a pass. The walk is enumerated once, and a new sibling test holds per-root floors (against today's counts) plus
  a spot check that the walk reaches that very file; a file read as empty is now refused. The shape was copied from an
  existing sweep in the repo rather than invented.
- `global-error-page.test.tsx`: one real post must land in the capture before its emptiness counts.
- `support-reference.test.tsx`: the fallback's own copy is asserted before the absence of the reference, so an empty
  render can no longer pass.
- **Each rewritten test was shown catching its breakage, and in every case the original passed under the same mutation:**
  a renamed `hooks/` directory (the old absence test passed with that root unread), an extension filter that matched
  nothing (the old test passed in 2.2 ms having read zero files), an unwired post capture, and a fallback component
  short-circuited to an empty element.
- **What that sweep can and cannot guarantee**, now recorded because its docstring reads as a total guarantee: it covers
  13 substrings over five roots and five extensions plus the root example env files, and nothing else — not `scripts/`,
  `types/` or root config, not other extensions, not a reference spelled differently, and nothing about runtime
  behaviour.
- The sibling test asserting the deleted directories do not exist is sound and was left alone: a positive claim about a
  named path, with a root finder that throws rather than resolving silently. A drafted control on it was reverted
  byte-identically.
- No fourth defective absence assertion in those files; each remaining one already has a positive claim in its own test.
- Lanes: unit 1853 of 1853, typecheck and eslint clean.

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

**N9.6 (post-close, 2026-09-12) — the guard audit's N9 fixes.** `7fc2bcc`, two test files, no production code.
- `server-routes-wrapped.test.ts`: the floor on how many route files the sweep found lived only in the first test. Test 2
  had no control at all and test 3 only a partial one. A shared helper now asserts the floor and returns the files, so
  every test runs it; test 2 counts imports that actually resolved into the api layer, and test 3 asserts its
  third-party hops equal the listed exemptions — a key set asserted positively.
- `instrumentation-hook.test.ts`: the two edge-runtime "writes nothing" tests had their controls in sibling tests. Each
  now proves the machinery in its own run — the register test flips to Node and asserts the sink IS installed, and the
  error test keeps ONE capture across both calls, so the capture that saw nothing is shown seeing something.
- **Each fix was shown catching its breakage, run at both the old tip and the new one.** Four of the seven breakages
  passed at the old tip, two of them 3 of 3 green: a renamed api-layer prefix, so the rule read nothing, and a stale
  exemption entry for a call that no longer exists. Those two were inert guards in the strict sense.
- Judged sound and left alone, with reasons recorded: the secret sweep and the trace-id absence check (both preceded by
  presence and content assertions on the same line) and the first route sweep, which fails closed rather than open.
- Lanes: unit 1877 of 1877, unchanged in count because the controls went inside existing tests; typecheck and eslint
  clean.

### Stream M9 — landed 2026-09-11 (implementer Opus 5; copilot-mro-obs9 `07f22475` → `6984d47b` on the stacked base `9976fa7c`; iac-obs9 `1eb8c6c` → `ad4e431` on `9231863`; final mini pass and M9.6 landed — tips `90a60040` / `1d2b400`)
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
M9.6 (after P9):
- **Refusals ruling — `e3f55d65` + iac `092fcf5`.**
  - Panel 11's failure ratio leaves the TanStack helper's client-side refusals out of both the failures and the attempts.
    These are `MutationRefusedError`, and they send no request.
  - A second series charts the refusal share.
  - The CloudWatch widget counts refusals separately.
  - A new guard, written test-first, pins that every stream in the ratio excludes refusals.
- **Flip — `90a60040` + iac `1d2b400`.**
  - The observed panels now say "LIVE since the P9 probe (2026-09-11)", in the same style as the existing "LIVE at
    Phase 5" notes.
  - Three panels keep a dated DARK note:
    - 12, settings: emitted once the TanStack conversion merges;
    - 14, optimizer triggers: not exercised;
    - 18: no drops happened in the window.
  - Panel 17 notes that its discovery target could not be observed.
  - The same flip reaches the Loki browser rules, `alerts.md`, the catalogue conventions, the §5 rows, the alarm-table
    labels and the aws "Blocked on" data gate (catalogue and `aws-profile.md`).
  - Nine CloudWatch widgets drop DARK and three keep a dated DARK title. Every query keeps its RE-VERIFY flag.
  - Guard grammar, test-first: the old guards failed on the flipped content. Now every `browser.*` panel or rule must
    state either "DARK until …" or a dated "LIVE since … (YYYY-MM-DD)". Three mutations fail it: no note, an undated
    LIVE, and a rule without a note.
- **Lanes:**
  - static otel lane with the rules check: 77 passed, 8 skipped;
  - `validate-rules.sh` passed;
  - `terraform validate` passed, and all 8 bodies parse;
  - the pinned Loki 3.7.7 accepted all 23 LogQL targets.

  The compose smoke was not re-run, because only board text and queries changed.
- **Learning:** panel 15 had data only in the final panel check (the optimizer-run export), not the interim one. Read
  the last evidence file, not the first.

**M9.7 (post-close, 2026-09-12) — the settings side keeps refusals apart.** `0259fd8d` + iac `a0059f9`.
- Panel 12 now counts by entity and outcome with refusals excluded, and a second target counts refusals by entity,
  legended "refused (no request sent)" — the same shape as panel 11.
- The aws settings widget counts refusals as their own column and says so in its title.
- Catalogue: the §5 settings row, the aws bullet, and a new conventions bullet — a refusal is not a failure, and its
  near-zero duration stays out of any latency view added later, which reads successful settles only.
- Guard `test_settings_outcome_breakdown_keeps_client_side_refusals_apart`, failing first on the unfiltered target. Both
  refusal guards now share one expression helper.
- Both panels keep their DARK note; the refusal shape is what will light them up.
- Two premises re-checked per target, not by grep: no rule reads mutation outcomes (the `outcome` matches in the agent
  and satellite rule files are backend labels), and no board target reads `duration_ms` (its one occurrence is prose in
  panel 12's description).
- Lanes: static with the rules check 78 passed, 8 skipped; `validate-rules.sh` passed; 24 LogQL targets accepted by a
  pinned Loki 3.7.7; `terraform validate` passed with all 8 bodies parsing. The session lead reran the dashboard guards
  (14 passed) and mutation-checked the new one: removing the filter from panel 12 fails it, and the board was restored
  byte-identical.

**M9.8 (post-close, 2026-09-12) — the refusal wording stops promising a request-free refusal.** `84809362` + `83f4a8f7`,
iac `b72307b`. Filters and counts are byte-identical; only prose changed.
- Verified first in the conversion branch: the role delete's refusal is thrown after an N+1 holder scan, one GET per
  tenant user, so it sends many requests and its duration spans the scan.
- **Nuance found while fixing it:** that refusal comes from the CALLER's own precondition inside the `mutationFn`, not
  from the helper's permission gate — the hook also takes the helper's documented reporting escape hatch, because a held
  role has a dialog of its own. The wording therefore says "the helper's permission gate, or a caller's own
  precondition". This matches code-26's own reframing: their gate carries a permission question and a precondition
  question, and the scan's duration is the visible edge of that.
- Legends read "refused (write not attempted)"; panels 11 and 12, both aws widget titles, the §5 rows and the aws bullet
  say the write was refused before it was attempted; the near-zero-duration claim is gone, replaced by a statement that
  the duration covers whatever the gate itself did; the conventions bullet names the scan as the example and keeps a
  later latency view reading successful settles only.
- **Guard:** a new test scans every board description, legend and catalogue block that speaks about refusals for the five
  false claims. It failed first on all five sites and passes now, with both refusal-split guards still green. No existing
  test pinned the old wording.
- Lanes: static with the rules check 79 passed, 8 skipped; `validate-rules.sh`; `terraform validate` with all 8 bodies
  parsing. No occurrence of the old phrase remains in either tree.
- **Process slip, recorded by the implementer:** a scripted edit anchored on a table header that matches all seven view
  tables. The count assertion aborted the script, but earlier swaps had already written to disk, so the first commit
  landed without the §5 paragraph; it was added as a second commit rather than an amend. Lesson: anchor a catalogue
  insert on text unique to its view, and re-read the script's output before committing when a step fails.

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

**E9.9 (post-close, 2026-09-12) — a telemetry bug can no longer change a write's outcome.** `c2f2025`, five files.
- **Measured first, through the app's own query client:** a successful write carrying an off-list attribute threw inside
  the settle hook, the library caught it, and the write was re-reported as a failure — the run even printed the shared
  handler toasting the telemetry bug to the user as the write's own error. The record was lost. Query-core's success
  dispatch sits at the end of the same `try`, so everything before it, both cache and hook callbacks, is inside.
- **Fix:** a stray key is stripped and the record kept in every mode, so a record's shape no longer depends on the mode,
  and the caller bug is reported out of band in development — a microtask throw the console, `window.onerror` and the
  test lane all see, never on the caller's stack.
- **At most one settle record per mutation, first one wins.** Deviation, proved rather than argued: keyed on a weak set
  of the mutation objects, not on `mutationId`, because that counter lives on each cache and restarts at 1 per client —
  with the id, later writes lost their records entirely (5 of 10 tests red, including "exactly one settle record,
  saw 0"). This also closes the duplicate-with-opposite-outcomes path, where a per-call success callback throws after the
  success record was already emitted.
- The guarded-`attrs` / unguarded-emit asymmetry is removed rather than explained: the settle hook is a boundary a
  library reads a throw from as the write's failure, so it is guarded end to end, and the attrs catch reports out of band
  instead of swallowing.
- **Sweep, eleven paths.** Only the settle hook sits in a mutation-cache callback and nothing in a hook-level handler
  today. Also covered: the long-running settle helpers — the discovery tracker deleted its row BEFORE emitting, so a
  development throw lost that settle permanently — and every direct-write wrapper, which emits after the write landed.
  The query cache wires only an error path with no emitter. Flagged and taken as E9.9b: `enqueueProductEvent` still
  throws synchronously, and its call sites are one conversion away from a `mutationFn`, where a throw IS the write
  failing.
- **Contract change:** the envelope guard no longer asserts a throw; it asserts the out-of-band report, that the record
  survived with the key stripped, and a positive control on the key that rode. Load-bearing: silencing the report turns
  6 of 10 tests red.
- Lanes: unit 1855 of 1855 (ten new tests), typecheck and eslint clean.

**E9.9b `64a6fa0` — the product-event throw, and a defect with no telemetry in it.**
- `enqueueProductEvent` threw the validator's error in development; it now drops the fact, counts it `invalid` in every
  mode, and reports out of band. It DROPS where `emitRecord` strips and keeps, deliberately: the schema judges the whole
  event, so a body naming a tenant id is a 400 for the entire batch.
- **All five timing wrappers emitted their SUCCESS record inside the `try` whose `catch` emits the failure record and
  rethrows** — not just the upload path code-26 measured. Red before the fix: an upload whose success reporting throws
  failed the upload; an upload that failed while its fact was malformed rethrew the telemetry error instead of its own;
  a preflight whose result could not be read was reported as a rejected run. All five now report from outside that
  `try` through one helper.
- **On "make `finish` at-most-once":** the implementer checked the control flow first and did NOT add a flag. With the
  success call moved out, the two calls are mutually exclusive by structure, and a flag could only fire for a third
  caller that does not exist — while silently swallowing it if one were added. `startAuthFlowTiming` keeps its flag,
  because it hands `finish` to a caller who may call it twice.
- Lane 1864 of 1864, typecheck and eslint clean.

**E9.10 `bc9fbcc` — the guard audit's E9 batch.**
- Each rewritten guard was shown catching its breakage with the original green under the same breakage: the settle
  unwired, the document handler returning early, the logger not emitting, and the allow-list table emptied (the old test
  passed in 1.4 ms).
- **The structural fix, proven both ways.** Renaming an event on the literal code left the presence test red and the
  absence test GREEN — the guard went quiet, exactly the shape the audit predicted. After migrating 18 files onto the
  catalogue constants, the same rename leaves the settle guard measuring the real emitter and is noticed in exactly one
  place: the catalogue's own definition tests. Definition tables, the schema, the case-expectation table and the
  double-emission fixture keep their literals, each with its reason recorded.
- `memory` and `output_preferences` are catalogued rather than excluded, through a settings-entity list and a typed
  helper pinned by the catalogue test. **The limit is named in code:** the map binds only through the helper, because the
  emitter checks attribute KEYS and never values, so a raw `meta` literal still sidesteps it — as it does the feature
  action map.
- The clone site is in the cleared column with its reason and its re-check condition. The sweep found the risky sites are
  one class: the optimizer api casts bodies (28 sites) and four per-call callbacks dereference the result. Only the one
  whose sibling handler already states a fail-open policy was fixed; its test asserts the toast.
- Lane 1866 of 1866, typecheck clean, eslint clean on all 27 files.

### Stream C9 — landed 2026-09-11 (implementer Opus 5; core-obs9 `88bbca5` on `master` `988571b`; reviewed MERGE-READY; mini pass `bd18984` and C9.2 `7264e2e` re-verified MERGE-READY; N3 `8e3c3ce` — tip `8e3c3ce`)
**C9.1 `88bbca5` — the fix.** `_pass_through` in `core/resources/logging/logging_endpoints.py` gains one clause for
starlette's `ClientDisconnect`, placed between the `HTTPException` passthrough and the 500 funnel.
- It answers 499 with no body and forwards nothing.
- It logs one constant INFO line, bound with `signal`, `public` and `tenant_id`.
- The module docstring's list of client answers gains the 499.
- All four ingest routes share this helper.

**Deviations (accepted pending review):**
- The fix is a clause on the existing try, not a nested try around the read. Only the body read touches the receive
  channel in this pipe.
- `public` is derived from the anonymous-tenant sentinel, not passed as a new parameter.
- Two lines that black would already reformat before this change are left alone.

**Why INFO:** in this module, WARNING marks events an operator can act on. A cancelled fetch is ordinary browser
behaviour — 23% of ingest posts in the probe. The rate limit runs before the read, so the line's volume is bounded.

**Test — new `tests/api/logging/test_ingest_client_abort.py`.** It drives the real router over raw ASGI, across all four
routes, with a receive channel that yields half a body and then a disconnect. It asserts:
- a 499 with an empty body, and nothing forwarded;
- no ERROR record or traceback from any module;
- exactly one INFO record, carrying the three bound keys.

Two controls: a complete body still answers 200 and forwards the exact bytes; any other failure still answers 500 with
one ERROR.

**Results.**
- Fail-before on `988571b`: 4 failed (500 instead of 499), and the probe's traceback reproduced.
- After the fix: 9 of 9 passed.
- Lanes: `tests/api/logging`, the router error-disclosure sweep and `tests/unit/infra` — 203 passed.
- Side effect: the ingest routes are excluded from the api's OTel server instrumentation, so no span or metric sees
  them. The api's "Request processed" log line moves from WARNING with 500 to INFO with 499 (corrected after review).

**Left for review (dispositions in §10 Stream C9: the refusals stay silent; the funnel goes to §9):**
- The 413, 415 and 400 refusals log nothing.
- The shared 500 funnel in `core/resources/http_errors.py` interpolates values into its message.

**Learnings:**
- Core's pytest `addopts` already has `-q`, so an extra `-q` hides the stats line. Read the counts from junit.
- A disconnect only reproduces through a real request over a receive channel. The module's fakes always return a body,
  which is why no earlier test reached this path.

Mini pass after review — `0368671` and `bd18984`, tip `bd18984`:
- **Ingest test.** It now covers both disconnect shapes, zero-chunk and half-body, on all four routes, and "mid-body" is
  gone from the wording.
- **The sibling `POST /analytics/events` gets the same fix.** A single clause returns a bodiless 499 and one constant
  INFO line bound with `tenant_id` and `user_id`; nothing is stored or re-logged. A new
  `tests/api/analytics/test_events_client_abort.py` covers both shapes plus two controls: a complete batch answers 202,
  and a store failure answers 500 with one ERROR.
- **Fail-before.** The ingest test failed 8 of 13 against a scratch copy of the base module. The events test failed 2 of
  4 with the route unchanged, reproducing the same ERROR and traceback. After the fix: 13 of 13 and 4 of 4.
- **Lanes:**

  | Lane | Result |
  |---|---|
  | `tests/api/logging` | 47 passed |
  | error-disclosure sweep | 113 passed |
  | `tests/unit/infra` | 47 passed |
  | `tests/api/analytics` | 23 passed, 9 failed |

  The 9 failures are all in `test_chat_quality_endpoint_contract.py`, and the same 9 fail on the base package. At first
  they were put down to missing seed rows; re-verification found the real cause, a date time-bomb (C9.2).
- **Findings recorded in the notes:**
  - `/analytics/events` is not in the api's ingest exclusion list. Its server span now records 499 with status UNSET,
    where before it recorded 500 with ERROR.
  - On this route the rate limiter runs after the body read, so the INFO line is bounded by authentication and by
    the gateway's global per-IP limiter, not by the route's own limiter. The limiter was not reordered.
  - The return annotation names both return types.
  - Pre-existing and left alone: an unused-import lint warning, and older lines that black would reformat.

**C9.2 `7264e2e` — the analytics seed-date time-bomb (tests only).**
- **Root cause.** The analytics seed derives every timestamp from a fixed `NOW` of 2026-09-01, and the 7 db-lane panel
  tests pass that `NOW` to the service. The chat-quality contract test drives the HTTP route instead, and the route
  passes no `now`. So the service read the real clock, and from about 2026-09-08 the one-week window slid off the seed:
  9 of the file's 20 tests have been red on core `master` since then. No panel SQL reads the database clock.
- **Fix.** An autouse fixture pins the service's existing `now` parameter to the seed's `NOW`. No production code or
  assertion changed.
- **Why not re-anchor the seed to the real clock.** The seed is shared by 8 consumers, and a real-clock anchor would make
  its day buckets depend on the time of day the tests run.
- **Proof.** A scratch clock-shift plugin, not committed, since no new dependency was allowed:
  - the old file failed 9 at the real clock, passed 20 at the seed's time, and failed 9 at +30 and +366 days;
  - the new file passed 20 at the real clock, at +30 days and at +366 days.
- **Sweep.** Every seed consumer already pins `now`. The fixed-date unit tests (253) and api tests (144) pass at all three
  clocks. The fixed-date db files were read, not run shifted.
- **Lanes:**

  | Lane | Result |
  |---|---|
  | `tests/api/analytics` | 32 passed |
  | `tests/api/logging` | 47 passed |
  | `tests/unit/infra` | 47 passed |
  | `tests/db/analytics` | 98 passed |

  The session lead independently ran analytics and logging: 79 of 79.
- **Learning.** A shared fixed-clock seed binds every consumer to pass that clock. A route-level test must pin the
  service's clock too, or it silently becomes a date time-bomb.

**N3 `8e3c3ce` — a unit test for the service's real-clock default.** This follows the C9.2 re-verification.
- **What the test does.** New `tests/unit/analytics/test_panel_service_clock_default.py` replaces the service module's
  clock with a fixed UTC time and stubs the cache, the limiter and the repository. It then calls the service with no
  `now` and asserts that the window end the repository receives and `last_updated` both equal the fixed time.
- **Mutation proof.** Four mutants fail it: a fixed offset on each default site, and a real-clock read that ignores the
  stub on each site.
- **Lanes.** `tests/unit/analytics` passed 70, `tests/unit/infra` passed 47. The session lead's rerun passed 117 of 117.



## 12. Lessons
- **Adjacent owner work that shares the effort's files is Fable-gated too (2026-09-11).** Tried: telling the owner's
  parallel TanStack conversion session it could land on `agent_sdk` first because it "is not Fable-gated", with phase 9
  absorbing it later. Owner corrected: "i will want to fable review that work too eventually." Rule: under a
  stronger-model gate, treat any parallel work that shares the effort's files as gated too unless the owner says
  otherwise — give it its own gate chunk (here RC), fix its merge order against the effort's chunks, and say so in the
  first coordination message.
- **A measured half lends its credibility to an unmeasured half (2026-09-12, from code-26).** They verified a count —
  nineteen emitters of `browser.settings.mutation`, thirteen in their account — and in the same sentence characterised
  the other six as "unconverted, uncensused, outside the guard", which was reasoning from the fact that those six sat
  outside THEIR guard. Two of the three words were wrong: the six already carried `meta.telemetry` from phase 4 and were
  already in phase 9's coverage. Their own implementer had predicted one turn earlier that the next instance would be "a
  sentence accurate about the thirteen and silent about the nineteen"; it arrived as a sentence accurate about the
  thirteen and wrong about the six. Rule: when a sentence carries a measured claim and an inferred one, split them —
  the reader cannot tell which half was checked, and the checked half vouches for the other. Corollary, applied here:
  check a peer's characterisation in your own tree before acting on it, because taking "uncensused" at face value would
  have sent someone hunting for panel volume that is already charted.
- **This failure shrinks under care; it does not stop (2026-09-12, with code-26).** Across seven instances on this plan
  the sentence shape stayed identical while the stakes fell: a whole census characterised wrongly, then a domain inferred
  beside a measured class, then a commit count remembered beside a checked claim about what those commits touched. Each
  time the checked half carried the remembered half. So a clean review round is not evidence the habit is gone — expect
  the next instance smaller, in a clause small enough that nothing seems to depend on it, and keep asking for instances
  anyway. Of the countermeasures, the reader's is the one to keep if only one survives: watching one's own articles is a
  discipline that cannot be run, a quantifier hunt is runnable but passes a sentence that names a scope with an article,
  and asking the writer to name an instance costs one message and holds against a writer being as careful as they know
  how.
- **An indefinite article introducing a category is a quantifier in disguise (2026-09-12, with code-26).** "A settings
  write that goes from counted to silent" used no quantifier, so a reader watching for *every* and *all* had nothing to
  catch — while the article asserted the domain just as hard, dressed as a modest single-instance claim. The countermeasure
  that resolved it in one round: **ask for an instance, not a re-confirmation.** "Name it" cannot be satisfied by
  restating the class, so an inferred scope has nowhere to hide, and unlike a quantifier hunt it works on clauses that
  name a scope without using one. Watch the articles, not only the quantifiers.
- **A branch-local measurement is a claim about the branch, not about the world (2026-09-12, from code-26).** Their
  grep for a gated write without telemetry hit twice on unmerged branches and was clean on the trunk. Both hits were
  stale views: those branches were cut before the telemetry swap landed and neither touches that file, so the merge takes
  the trunk's version and the defect exists in no tree anyone will run. Their red lane is the same phenomenon with the
  opposite sign — a coverage floor the trunk gained after the branch point, invisible to both parents and failing only on
  the merged tree. Rule for this plan: every census and floor quoted here was measured on a phase-9 worktree cut from
  `b87ced0`, so each is branch-relative. After each gate chunk merges, re-run that branch's full lane AND re-check any
  count this plan quotes (the emitter censuses, the coverage floors, the entity lists) against the merged tree, because a
  number that was true when written can be false after a merge that touched nothing it names.
- **A search result measures the search, not the thing (2026-09-12).** A grep that counts a word, in a file that uses the
  word for something else, is the same failure as a measured clause with an unmeasured characterisation attached. The
  example is this plan's own near-miss: `hooks/settings/useOperatorGrants.ts` counted as a gated write emitting nothing,
  where the `gate:` was prose in a comment about a query's open flag. Open the file before the finding leaves the desk.
- **Ask what is awaited, not what is guarded (2026-09-12).** A callback that calls a refresh without awaiting it cannot
  fail the write around it — a rejection surfaces as an unhandled rejection instead. The same call awaited inside a
  handler that a library reads for the write's outcome CAN fail it, which is why the shared helper that awaits its
  invalidation needs its try/catch and the two hooks that do not await are safe without one. "Is this callback guarded?"
  is the question that comes to mind and it is the wrong one; unguarded-and-not-awaited is noisy but safe, and
  awaited-and-unguarded is the dangerous shape.

