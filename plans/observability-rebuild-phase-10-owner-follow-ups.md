# Observability rebuild — Phase 10: owner follow-ups

**Status:** OPENED 2026-09-14. **Plan v5** (2026-09-15). v2 revised the design after the independent Opus 5 plan review
(READY AFTER CHANGES: 4 P1, 11 P2, 6 P3; triage in §10a). v3 re-laid execution for subagent-driven development (SDD) with
maximum parallelism, on the owner's approach ruling (5 below). v4 folds in the owner's Fable 5 plan review of v2 (READY
AFTER CHANGES: 1 P1, 5 P2, P3 notes; triage in §10b) — its one design change: the provider raise leaves `user_data`
untouched (Task 14). v5 folds in the Fable chat's scoped re-verify of v4 (READY AFTER CHANGES: 0 P1, 2 P2, 6 P3 — pins
and wording only; triage in §10c). The owner's go was conditional on that verdict being clean; its findings carry no
design change and were folded before any dispatch, and chunk R15's Fable review re-checks the §2.4 pins in code.
**EXECUTING** (SDD ledger: `.superpowers/sdd/observability-rebuild-phase-10-owner-follow-ups/progress.md`). Master plan:
`docs/plans/observability-rebuild.md` §11d (this phase), §15 (ledger), §18 (resume).

**Owner request (2026-09-14),** picking nine items from the post-gate "what's left" answer: "can we pick this please?
design and plan them. we build and review using opus and post that fable reviews".

**Owner rulings (2026-09-14/15, in-session):**
1. **Response validation** lives at the dashboard API layer as narrow zod contracts on the write responses whose
   fields callers read — not every response, not OpenAPI codegen.
2. **Gate M DECLARED:** "langraph migration is done. so we can build and moerge now." The `/rag/stream` persistence
   fix is built AND merged in this phase; the master §1 conflict-zone freeze is lifted. Task R and Stream L are
   unblocked but are NOT part of this phase (they need their own go).
3. **Alerts get real Slack and email targets now:** prod and dev Slack channels, email for prod `critical` only, the
   platform's SMTP relay (values in §2.2).
4. **CloudWatch alarm dialect:** raise `hashicorp/aws` in the iac root (ruled `~> 6.42`; pinned `~> 6.43` in Task 14 —
   6.42.0 carries a metric-alarm validation bug the metric-filter alarms would hit); PromQL alarms for metric alerts,
   metric-filter alarms for log-derived alerts.
5. **Execution approach (2026-09-15):** "sdd driven. implementation + review on opus here. main controller is opus. the
   other fable 5 reviews will be on another chat with fable 5 controller. i want as much parallelism as possible too".

**Session-lead design rulings from the research and the plan review (the owner may override at plan review):** the
Document Hub fix (restores F10's "one gesture = one row" ruling for an opener that escaped it); a config guard for the
worktree build trap instead of `outputFileTracingRoot` (research showed it does not close the trap); project-scoped
smoke networks; the §2.3 version scheme; an RLS preflight that self-heals test databases only; removing the chat-blocks
cache rather than guarding its write-back (Task 7) — superseded 2026-09-15: its stop condition hit, so Task 7 now
versions the cache key by a per-chat generation token (D10-5b); no backend response models (Task 3 — they would recreate item 1's
failure on the server).

**Goal.** Close the nine items: a landed write is never reported as failed; a streamed turn is in history before the
client is told it finished; alerts reach real people with thresholds that do not page on laptop noise, in both
dialects; Document Hub opens are counted exactly once from every opener; a worktree build can never delete the shared
`node_modules`; smoke runs are network-isolated by construction; every service reports a real version; test databases'
RLS policies can no longer go silently stale.

**Research inputs (2026-09-14):** five read-only Opus 5 research agents, one per item group, then one independent
Opus 5 plan reviewer that spot-verified the load-bearing claims (§10a). Findings are summarized per task with file:line at
the base tips; each implementer re-locates lines on its own tree.

**Base tips (verified 2026-09-14).** Worktrees branch from these; other sessions' uncommitted files in the primaries
(copilot-mro `docs/plans/open-items.md`, two core plan docs, a utils `CLAUDE.md`, an iac setup script) are not carried
and must not be touched.

| Repo | Branch | Tip |
|---|---|---|
| dashboard | `agent_sdk` | `0a4dbec` |
| api | `langgraph-merge` | `fc35d08` |
| utils | `langgraph-merge` | `718db0a` |
| copilot-mro | `langgraph-merge` | `a24189ee` (S4 pushed at `4ba3c7f0`; one local ledger commit) |
| flynapse-otel | `main` | `25dc158` |
| shift-optimizer | `main` | `23d3f2e` |
| telegram-bot | `main` | `c6ee959` |
| iac | `main` | `3b5f414` |

**Inherited constraints (master §1/§11a/§12, phase-8/9 practice):** commits on this phase's own worktree branches by
pathspec, never `git add -A`, never bare `git stash`; **no new npm or Python dependency** (zod is already a direct
dashboard dependency); no credentials in output, commits, logs, argv or screenshots — the Slack webhook URLs and the
SMTP password never enter the repo, the chat or a log line (owner-written files for `oss`, SSM SecureString for `aws`);
no user content in any log body or attribute; the browser never sees a collector URL; plan files carry no code;
Terraform is validated, never applied, by agents (`init -upgrade -backend=false` downloads the provider and touches no
AWS — allowed; any backend `plan` is the owner's); nothing pushed without the owner's word; the concurrent-agent cap is
the owner's number (10 — owner raised it from 5 on 2026-09-15; reviewers share the slots); every agent reported as
`name — model`; every Phase-A agent is Opus 5; one implementer per worktree at a time; heavy commands only through the
§1c lane locks; dashboard lanes use the canonical `npm run test:unit` / `npm run typecheck` / `npm run lint:all`
(`next lint` only — bare `npx eslint` lints nothing); **never `next build` or `next dev` in a dashboard worktree** (the
Task 1 proof runs in a scratchpad app); CI workflows the touched trees own stay green (copilot-mro `rules-validate.yml`,
`otelcol-validate.yml`); test files follow the workspace two-level layout with globally unique basenames, and
copilot-mro tests use the dynamic-loader pattern.

---

## 0. Item register

| # | Item (as picked) | Research finding that shaped the design | Task(s) |
|---|---|---|---|
| 1 | Response validation at the API layer | 13 sites read a write's reply unchecked: two fail hard today (the schedule dialog's silent catch leaves the draft open, inviting a duplicate create; the AD recompute render throws), the rest let a missing field propagate as `undefined` (a navigation to `/jobs/undefined`, a permanently locked button, wrong UI); two AD-review routes and core `POST /operators` declare no response model (deliberately, in core's case); nothing parses any response today | 3 |
| 2 | `/rag/stream` final-before-save race | One save site for both engines; `final` queued before an unreferenced fire-and-forget save task; follow-up turns race too; the chat-blocks cache's miss-path write-back can pin a stale copy for 300 s; no out-of-zone fix closes it | 5, 6, 7 |
| 3 | Alert thresholds + real Slack/email targets | 18 rules, all plan defaults, one receiver; delivery failures are silent (Alertmanager unscraped); the rollout checklist as written turns `test_alertmanager_config.py` red; laptop stacks page on noise; placeholder targets would make a delivery-failure alert fire forever | 9–12 |
| 4 | Document Hub double `document_opened` | Already deduped by F10 `1f2aa95` ("one gesture = one row"); that fix left inline Hub chips emitting ZERO opened rows | 2 |
| 5 | CloudWatch alarm dialect | OTLP metrics are PromQL-only; provider 6.42.0 added PromQL alarm criteria (6.43 fixes a metric-alarm validation bug); the 5→6 raise with `user_data` untouched plans no replacement (6.0 suppresses the diff against the 5.x hash), while moving to `user_data_base64` would itself risk replacing both boxes; collector alarms have no data in `aws`; the topic split needs per-topic subscriptions and permissions | 13–16 |
| 6 | Worktree `next build` trap | `outputFileTracingRoot` does not close it: nft plants the symlinked `node_modules` into standalone output; the start-of-build `cleanDistDir` recursive delete and every `next dev` start follow it | 1 |
| 7 | Per-run compose smoke network | Two fixed-name smoke networks (the Grafana smoke too); nothing needs the names; smoke project names are constants; the Grafana smoke hard-codes a host port | 8 |
| 8 | `service.version` unknown | api / worker / copilot-mro report a fake `0.1.0` (settings default), the bot `unknown` (image never installs its metadata), copilot-mro standalone `unknown` (`poetry install --no-root`), the browser a hard-coded `1.0.0`; `OTEL_RESOURCE_ATTRIBUTES` is whole-variable-replaced | 4, 14 (Amplify literal), 17–19 |
| 9 | RLS re-run on `shift_optimizer_test` | Stale since utils `58e75c9` / copilot-mro `ef6e122e` (2026-08-17, sentinel write predicates); `copilot_mro_test` carries the same risk; nothing re-applies policies to test DBs; the provisioner takes no advisory lock | L10.0 (session lead), 20, 21 |

## 1. Lanes, worktrees, parallelism

A **lane** is one set of worktrees worked by one implementer at a time; its tasks run in order. **All lanes run in
parallel** — no lane waits on another, because every cross-lane interface is pinned in §2. Worktrees are plain
`git worktree` checkouts at sibling depth under `/home/aditya/Code/`, each on branch `obs10-<lane>` off the tip table
(dashboard trees symlink `node_modules` and `.env.local` to the primary's; Python trees symlink `.env`).

| Lane | Tasks | Worktrees (all → branch `obs10-<lane>`) | Fable chunk |
|---|---|---|---|
| `guard` | 1 | `dashboard-obs10-guard` | R12 |
| `hub` | 2 | `dashboard-obs10-hub` | R13 |
| `contracts` | 3 | `dashboard-obs10-contracts` | R14 |
| `webver` | 4 | `dashboard-obs10-webver` | R20 |
| `stream` | 5 | `copilot-mro-obs10-stream`, `api-obs10-stream` | R15 |
| `streamui` | 6 | `dashboard-obs10-streamui` | R15 |
| `cache` | 7 | `copilot-mro-obs10-cache` | R16 |
| `smoke` | 8 | `copilot-mro-obs10-smoke` | R17 |
| `alerting` | 9 → 10 → 11 → 12 | `copilot-mro-obs10-alerting` | R18 |
| `awsotel` | 13, 22 (separate worktrees; may run side by side) | `copilot-mro-obs10-awsotel`, `api-obs10-awsotel` | R19 |
| `iac` | 14 → 15 → 16 | `iac-obs10-iac` | R19 |
| `otelver` | 17 | `flynapse-otel-obs10-otelver` | R20 |
| `pyver` | 18 | `utils-obs10-pyver`, `api-obs10-pyver`, `copilot-mro-obs10-pyver`, `shift-optimizer-obs10-pyver` | R20 |
| `images` | 19 | `api-obs10-images`, `telegram-bot-obs10-images`, `copilot-mro-obs10-images` | R20 |
| `rls` | 20 → 21 | `utils-obs10-rls`, `copilot-mro-obs10-rls`, `shift-optimizer-obs10-rls` | R21 |

Fifteen lanes can run at once; the owner's agent cap decides how many actually do. When the cap is below the number of
live lanes, the controller fills free slots in this priority: `stream`, `contracts`, `iac`, `alerting`, `rls`, then the
rest — the longest lanes and the lanes with the most downstream review work first. Reviewers take slots too; a lane's
task reviewer starts the moment its implementer reports.

### 1a. Progress

**Phase A (this chat; Opus 5 controller; SDD — §9)**
- [x] Independent Opus 5 plan review + triage → v2 (§10a); v3 execution layout
- [x] §2.2 literal values supplied by the owner
- [x] Owner's Fable plan review (separate Fable chat; report at `copilot-mro/.dev_runs/obs10-fable-gate/plan-review.md`) triaged into v4 (§10b)
- [x] Fable scoped re-verify of the v4 triage + the v3 execution layout — READY AFTER CHANGES (0 P1, 2 P2, 6 P3), folded into v5 (§10c); verdict `copilot-mro/.dev_runs/obs10-fable-gate/plan-review-v4-verdict.md`
- [x] Owner go — given 2026-09-15 ("5 is fine. good to go once that's clean"), conditional on a clean Fable re-verify; agent cap 5
- [x] L10.0 session lead: RLS verify → apply → re-verify on `shift_optimizer_test`; optimizer `tests/api` setup errors 62 → 0 (130 passed); `copilot_mro_test` verify-only clean (§12)
- **Task status (2026-09-15, after checkpoint #4; the SDD ledger holds the per-task record, commits, fix bases, carries
  and resume map):** all 22 tasks built; complete — every task except 21 (fix round 2 running; then the rls lane review);
  lanes `hub`, `contracts`, `alerting`, `iac` closed (fix waves re-reviewed clean); R19's chunk composition review (awsotel
  + iac) running. Task 7 was re-planned
  (D10-5b, then T7-ABSENT); Task 18's review corrected a plan claim (merge order, §9); Task 15 surfaced the
  silent-idle-worker premise → Task 22; Task 22's review surfaced that `aws` deploys no worker → T22-NOWORKER; Task 16's
  review reshaped the arming design → T16-ARMED. Single-task lanes close on their task review (§12, LANECLOSE-SINGLE);
  R19/R20 get one chunk composition review. Phase B COMPLETE 2026-09-15: R12–R21 all MERGED (R19's iac half on the owner's word after a hold) and PUSHED
  the same day on the owner's word (all eight repos); all 24 obs10 worktrees and branches removed; NOT published
  (utils 0.1.39, flynapse-otel 0.1.1, api). Compaction checkpoint #5 (final) in the SDD ledger.
- [x] Lanes complete (all tasks reviewed clean + the lane's final review): `guard` · `hub` · `contracts` · `webver` · `stream` · `streamui` · `cache` · `smoke` · `alerting` · `awsotel` · `iac` · `otelver` · `pyver` · `images` · `rls` — all fifteen closed 2026-09-15 (Phase A done; every chunk requested)

**Phase B (separate Fable 5 chat with a Fable controller; §9 handoff; merges here after each verdict)**
- [x] R12 guard → dashboard — MERGED 2026-09-15 as `26a882c` on `agent_sdk` (verdict MERGE-READY AFTER FIXES → fix round 1 `798d821` → MERGE-READY; post-merge guard 12/12, typecheck, lint clean; phase-9 §1c rule text updated; `R12-merged.md`; not pushed)
- [x] R13 hub → dashboard — MERGED 2026-09-15 as `0bc5429` on `agent_sdk` (verdict MERGE-READY; post-merge 20/20, typecheck, lint clean; master §15 + phase-4 plan hub-citation records closed with the historical chip under-count note; `R13-merged.md`; not pushed)
- [x] R14 contracts → dashboard — MERGED 2026-09-15 as `4a2898b` on `agent_sdk` (verdict MERGE-READY AFTER FIXES → one-line fix `6a48cc3` → MERGE-READY; post-merge FULL unit suite 2475/2475 as the composition proof for all five dashboard chunks, typecheck, lint clean; `R14-merged.md`; not pushed)
- [x] R15 stream + streamui → copilot-mro, api, dashboard — MERGED 2026-09-15: copilot-mro `111db0b1`, api `f162bb7`,
      dashboard `67df720` (verdict MERGE-READY AFTER FIXES → fix round 1 → MERGE-READY; moved base fb276fd1 merged into
      the branch as 072d7548 and the lane re-run 1232 passed; post-merge lanes green; `R15-merged.md`; not pushed)
- [x] R16 cache → copilot-mro — MERGED 2026-09-15 as `3b251604` on `langgraph-merge` (verdict MERGE-READY AFTER FIXES →
      fix round 1 → MERGE-READY; post-merge lane 141 passed / 8 skipped; `R16-merged.md`; not pushed)
- [x] R17 smoke → copilot-mro — MERGED 2026-09-15 as `fb276fd1` on `langgraph-merge` (verdict MERGE-READY AFTER FIXES →
      fix round 1 → MERGE-READY; moved base 3b251604 merged into the branch as ad4496f0 and the lane re-run 146/146;
      post-merge lane 136 passed / 10 gated skips; `R17-merged.md`; not pushed)
- [x] R18 alerting → copilot-mro — MERGED 2026-09-15 as `f49670c7` on `langgraph-merge` (verdict MERGE-READY AFTER FIXES → fix round 1 → MERGE-READY; moved base 8da84ea8 merged into the branch as 11f76a08 and the lane re-run both gates 181/181; post-merge always-on 157 / 24 gated skips; `R18-merged.md`; not pushed)
- [x] R19 awsotel + iac → copilot-mro, api, iac — MERGED 2026-09-15: copilot-mro `e68558ba`, api `087e298` (moved base merged as c13e736d with the CATALOGUE hunk resolved; lane both gates 187/187), iac `main` `f35ec20` on the owner's word after the hold (verdict MERGE-READY; F-1/F-3 folded; the plan gate re-homed to step 1 of the apply with the control = `3b5f414` by SHA — valid under state drift per the Fable addendum; no init/plan/apply run; post-merge fmt/validators/61 green; `R19-merged.md`; not pushed)
- [x] R20 webver + otelver + pyver + images (the version scheme end to end; cross-checks Task 14's Amplify literal, which merges in R19) → dashboard, flynapse-otel, utils, api, copilot-mro, shift-optimizer, telegram-bot — MERGED 2026-09-15 in the corrected order (flynapse-otel `1cafda2`, utils `6ba3ab5`, copilot-mro `2bc60799` → `8da84ea8`, api `a0238e1` → `6672fc5` + lock refresh `a78306f`, shift-optimizer `7ef9588`, telegram-bot `3102fcc`, dashboard `0d55530`; verdict MERGE-READY; carries 2+3 landed pre-merge; the shared api env installs utils 0.1.39 / flynapse-otel 0.1.1; `R20-merged.md`; not pushed, not published)
- [x] R21 rls → utils, copilot-mro, shift-optimizer — MERGED 2026-09-15 in order: utils `a9ca707`, copilot-mro `81965357` (moved base e68558ba; tests/db through the preflight 655 passed + the recorded pre-existing 3+13), shift-optimizer `88e9803` (verdict MERGE-READY; post-merge optimizer `tests/api` 130 passed through the runner — the L10.0 symptom prevented; `R21-merged.md`; not pushed)

**Live batch (§10)**
- [ ] Alert delivery to the real targets (owner confirms receipt)
- [ ] One live `/rag/stream` turn + immediate reopen
- [ ] Rebuilt images report `service.version` (owner step first: delete `APP_VERSION` from the primary `dashboard/.env.local`,
      which otherwise overrides the build-computed value under compose `env_file` — Task 4, ruling T4-ENVLOCAL; the first
      real standalone build is also the proof that `.env.production` reaches the server). The api rebuild passes
      `API_VERSION` and `GIT_SHA` together; it confirms that `BUILD_GIT_SHA` is empty without `API_VERSION`, and that the
      health check tools the api image and compose call (`curl`, `wget`) exist in the image. If they are absent, `api`
      never turns healthy and the bot's `depends_on: service_healthy` never releases.
- [ ] The api's stop window on App Runner covers the chat-save drain (≤ 22 s after open streams close)
- [ ] Carried: phase-8 §10 probe and phase-9 re-probe F-R6-6

### 1b. Files more than one lane touches (each lane owns one hunk)

| File | Owners |
|---|---|
| api `flynapse_api/main.py` | `pyver`: the `setup_logging` call (distribution name). `stream`: the lifespan's shutdown drain call. |
| copilot-mro `copilot_mro/app/main.py` | `pyver`: the `setup_logging` call. `stream`: the lifespan's shutdown drain call. |
| dashboard `lib/api/client.ts` | `streamui` edits it (the stream reader). `contracts` never touches it — it holds no mutation producers. |
| dashboard chat surface | `streamui` raises the `persisted: false` notice from the stream hook; `hub` edits `ChatMessages.tsx`. Neither edits the other's files. |
| copilot-mro `tests/integration/otel/` | `smoke`: `conftest.py`, the Grafana smoke test, a new guard. `alerting`: the alert/alertmanager/scrape tests. `awsotel`: a new collector-profile test. No lane edits another's files; a fixture one lane needs from `conftest.py` is added by `smoke` only. |
| copilot-mro runbooks | `alerting`: `oss-profile.md`, `alerts.md`. `awsotel`: `aws-profile.md`. |
| shift-optimizer tests | `pyver`: `tests/unit/telemetry/conftest.py` (scrub list). `rls`: `tests/conftest.py` + README; `tests/_optimizer_schema.py` and the `--registry` remedy strings in `tests/unit/persistence/test_optimizer_rls_policies.py` / `test_view_bootstrap_refusal.py` (added at Task 21's review, ruling T21-REGISTRYFLAG). |
| shift-optimizer (non-test) | `rls`: the `--registry` remedy strings in `shift_optimizer/app/db/postgres.py` and `table_definitions.py` (ruling T21-REGISTRYFLAG). |
| utils | `pyver`: `logging_config.py` + observability tests. `rls`: the db-guard module + its tests, and the new RLS preflight runner module beside it + its tests (ruling T21-SHARED). |
| api | `pyver`: `main.py` hunk, `automations/worker.py`, `tests/conftest.py` scrub list. `images`: `Dockerfile`, `compose.yaml`, `.github/workflows/deploy.yml`. `stream`: `main.py` lifespan hunk. `awsotel`: `automations/loop.py` (the liveness log, Task 22). |
| copilot-mro (non-test) | `stream`: `app/api/chat_management.py`, the new save-task registry, `app/main.py` lifespan hunk. `cache`: `app/db/chat_history/{blocks,chats,base}.py`. `pyver`: `app/main.py` logging hunk. `images`: `Dockerfile`. `rls`: `scripts/provision_rls.py`, `tests/conftest.py`. `smoke`/`alerting`/`awsotel`: `deployment/**` per their tasks. |

Within a repo, merges are sequential in chunk-verdict order; a later merge takes the earlier one's base under the
moved-base rule (§9).

### 1c. Test environments and lane locks

- **Lane locks.** Every heavy command runs under a blocking `flock` on one of these files, so any number of agents can
  work at once while the box never runs two heavy jobs of a kind: `/tmp/obs10-locks/dashboard.lock` (full
  `npm run test:unit`, `npm run typecheck`, `npm run lint:all`, and every scratchpad `npm install` / `next build` /
  `next dev` — Task 1's proof), `/tmp/obs10-locks/compose.lock` (compose smokes, docker image pulls, `terraform init`,
  `amtool`/`promtool`/`otelcol` container runs), `/tmp/obs10-locks/db-<database>.lock` (any lane that touches that test
  database), `/tmp/obs10-locks/python-full.lock` (a repo's full Python suite; a full suite that touches a test database
  holds this lock AND that database's lock). Single test files and targeted runs need no
  lock. A lane's evidence names the lock it held.
- **Python:** lanes run from the shared `api/.venv` with `DEBUG=false`. The shared env resolves the PRIMARY checkouts, so a
  worktree lane puts its own package roots first on `PYTHONPATH` and prints each imported package's resolved file path at
  lane start as evidence. A lane without that evidence is not a pass.
- **Dashboard:** the phase-9 §1c rules, unchanged, plus the lane locks.

## 2. Pins (so lanes build in parallel)

### 2.1 Alert thresholds — one table, both dialects

`oss` rule files and the iac thresholds locals map carry exactly these numbers; a guard on each side pins them.

| Alert | Condition / window | Severity | Change from today | `aws` form |
|---|---|---|---|---|
| ApiHighErrorRate | 5xx share > 5% with > 0.1 rps volume guard, 10m | critical | none | PromQL alarm |
| ApiP95LatencyHigh | p95 per job×route > 5 s for 15m, counted only for routes with at least 20 requests over the last 15 minutes, **excluding streaming/agent routes** | warning | exclusion + volume guard; the exclusion list is guard-tested to name real routes | PromQL alarm |
| CollectorExporterFailures | failed sends > 0, 10m | critical | none | PromQL alarm on collector self-telemetry (Task 13) |
| CollectorExporterQueueNearFull | queue > 0.8 of capacity, 10m | warning | none | same |
| CollectorReceiverRefusing | refused > 0, 10m | warning | none | same |
| **CollectorTelemetryAbsent** (new, `aws` only) | the collector's own uptime series absent, 15m | critical | new: the self-telemetry rides the same exporter it watches, so an exporter outage silences the three alarms above | PromQL `absent()` alarm |
| AutomationWorkerSilent | worker series absent, 15m | warning | routed to `dev` on laptop stacks (§2.2) | metric-filter alarm on worker logs, missing data = breaching (relies on the worker's 5-minute liveness log, Task 22) |
| TempoGeneratorSeriesNearCap | > 0.8 × `max_active_series`, 15m | warning | none | `oss` only (no Tempo in `aws`) |
| AgentTurnFailureRatioHigh | > 10% with > 10 turns, 15m | critical | none (~~DARK until Stream L~~ → **WIRED 2026-09-20, retrieval unproved: `RuntimeTelemetry.record_turn`**) | PromQL alarm; the rule and `CATALOGUE.md` now carry the WIRED note |
| UnpricedModelCalls | increase > 0, 30m | warning | none (DARK) | same |
| LedgerWriteFailures | increase > 0, 5m | critical | none (DARK) | same |
| TenantDailySpendHigh | > $50 per tenant per 24h, 30m | warning | none — owner retunes later (DARK) | same |
| TelegramTurnFailureRate | > 20% with > 5 turns, 15m | **warning** | critical → warning until real volume exists | PromQL alarm |
| OptimizerRunFailureRate | > 30% with ≥ 3 runs, 30m | warning | none | PromQL alarm |
| BrowserErrorRateHigh | > 30 errors per 15m | warning | none (absolute count; recalibration is §13) | metric-filter alarm |
| WebVitalLCPPoor / INPPoor / CLSPoor | p75 > 4000 ms / > 500 ms / > 0.25 for 30m, **only with at least 20 samples in the window** | warning | sample guard added | metric-filter alarm: metric math combining the p75 statistic with `SampleCount` ≥ the locals-map minimum (RE-VERIFY after B1b) |
| AutomationRunErrors | worker error logs > 0, 15m | warning | none (transitional proxy) | metric-filter alarm |
| **AlertmanagerNotificationsFailing** (new, `oss`) | failed notifications > 0, 10m | critical | new; needs the Alertmanager scrape job; silent by construction on placeholder targets (§2.2) | — |
| **AlertDeliveryFailing** (new, `aws`) | SNS `NumberOfNotificationsFailed` > 0 on either topic; the Slack forwarder Lambda's `Errors` > 0 | critical | new | classic metric alarms, cross-routed: a topic's delivery-failure alarm publishes to the OTHER topic; the forwarder's alarm publishes to `critical` (whose email path does not use the Lambda) |

Severity label values stay `critical` / `warning`. Every new alert gets a runbook anchor (the existing guard enforces
it). Each `oss` threshold with a volume or sample guard states its guard in the rule's description. The `aws` metric
names for the collector alarms follow the series names the existing `oss` rules use, with RE-VERIFY markers for B1a.

### 2.2 Notification targets and routing

**Environment stamp.** Prometheus and the Loki ruler stamp a `deployment_environment` external label in the three stacks
that run them (`deployment/observability-local/observe-docker-compose.yml`, `deployment/docker-compose.yml`,
`deployment/poc/docker-compose.yml`; the demo stack has no Prometheus/Alertmanager). All three mount ONE
`deployment/observability-local/prometheus.yml`, so one edit serves them all and per-stack values come only from each
compose file's `environment:`. Prometheus 3.x expands environment variables in `external_labels` by default (Go
`os.Expand`: a `${VAR:-default}` form silently yields empty) while Loki's `-config.expand-env=true` honours defaults, so
both configs use bare `${DEPLOYMENT_ENVIRONMENT}` (the variable's name, pinned 2026-09-15 at Task 9) and compose
`environment:` supplies `dev` unless the stack's `.env` says otherwise; an empty
value would drop the label, so Alertmanager's ROOT receiver is the `dev` route (fail-safe), and a test proves an alert
without the label routes to `dev`. The `aws` deployment is `prod`. A box that should page as production (e.g. the POC box,
if the owner decides so) sets the variable in its own `.env` — documented in `oss-profile.md`.

**Routing (owner ruling, 2026-09-15):**
- `prod`: every alert → `#prod-alerts`; `critical` alerts ALSO → email.
- `dev`: every alert → `#dev-alerts`; never email.
- `oss` Alertmanager mounts two webhook files (one per channel) and one SMTP password file.
- `aws`: the alert SNS topic splits into `critical` and `warning` (Task 15); email subscribes to `critical` only; the
  Slack forwarder subscribes to both, posts to `#prod-alerts` and prefixes each message with its severity.

**Placeholder safety.** Until the owner has written the secret files, every stack loads a null-target Alertmanager
config: the same route tree as the real config, receivers with no integrations — so nothing is sent, nothing fails, and
AlertmanagerNotificationsFailing stays silent. The owner switches a stack to the real config by one variable in its
`.env` after writing the files. A guard asserts both configs' route trees are identical.

**Literal values (supplied by the owner, 2026-09-15):**

| Value | Literal |
|---|---|
| Prod Slack channel | `#prod-alerts` |
| Dev Slack channel | `#dev-alerts` |
| Email recipient (prod critical) | `aditya@flynapse.ai` (also the `aws` critical-topic email subscription, via an untracked var-file) |
| SMTP relay | `smtp.gmail.com:587` — the platform's effective setting (`api/.env` leaves `SMTP_SERVER`/`SMTP_PORT` unset, so the utils defaults apply) |
| SMTP username | `aditya@flynapse.ai` (`SMTP_USER` in `api/.env`; owner-approved to commit as a literal — Alertmanager has no username file field) |
| From address | `contact@flynapse.ai` (the utils `SMTP_SENDER_EMAIL` default the platform sends as) |

Owner-side, never in chat or the repo: the two Slack webhook URL files and the SMTP password file (the same account's
password the platform already uses), at the paths Task 12's runbook names; for `aws`, the webhook as an SSM SecureString.

### 2.3 Version scheme (estate-wide)

- **Precedence** (first present wins): `service.version` inside `OTEL_RESOURCE_ATTRIBUTES` → `SERVICE_VERSION` env →
  the code-derived version (the running distribution's own metadata, named by the caller) → `unknown`.
- **Format:** the code-derived version gains `+<sha7>` (semver build metadata) when `BUILD_GIT_SHA` is set. An
  operator-set value (either of the first two sources) is never modified. Composition happens once, in
  `flynapse_otel.resource`, whose builder accepts the code-derived version as an argument.
- **utils seam:** `setup_logging` takes an optional distribution name, resolves that distribution's version from its
  metadata, and passes it to the resource builder; no name → no code-derived version (never the `0.1.0` settings default).
- **Build plumbing:** every image takes a `GIT_SHA` build argument and exposes it as `BUILD_GIT_SHA`; compose passes it
  from an environment variable defaulting to empty (a local build honestly reports bare semver); CI passes the commit SHA.
  Every image that runs Python service code makes its own distribution metadata resolvable (installs its project without
  dependencies).
- **Dashboard:** `APP_VERSION` = `package.json` version plus `+<sha7>` from the Amplify commit id (or the Docker
  `GIT_SHA`), computed at build; a commit id that is not hex (Amplify reports `HEAD` for rebuilds) counts as absent; no
  hard-coded literal anywhere (iac included).
- Nothing charts or alerts on the version today; the value is for trace/log correlation.

### 2.4 Stream `final` contract

- Order on every engine path: content events → the block save settles (succeeds, fails, is refused, or times out) →
  `final` → stream end.
- `final` gains `persisted: boolean` — `true` only when the save confirmed. A client treats an ABSENT field as "unknown"
  (old server) and shows nothing.
- The save runs as its own task, held in a module-level registry until it settles, awaited by the stream through a
  shield (a client disconnect cancels only the waiting, never the save), and drained with a bound during the effective
  process lifespan's shutdown (the gateway's when mounted — a mounted sub-app gets no lifespan — and copilot-mro's own
  when standalone). The task itself records success, failure and the bounded reason (`exception` | `timeout` |
  `refused`), so a cancelled waiter never loses the count.
- Before its context read, the stream route awaits, with a bound, every registry-held save for the same `chat_id`, so a
  reload, retry or deep-link turn after a mid-save disconnect — which never saw `final` — cannot read history without the
  previous turn. Three pins keep this from re-creating the original bug:
  - **Multiplicity:** the registry holds EVERY pending save per chat (a set per chat); registering a save never displaces
    a pending one; the context-read wait and the shutdown drain await all of them.
  - **Cancellation safety:** the context-read wait never cancels a save when it expires (shielded, or a timeout-bounded
    wait that leaves the task running).
  - **Bound and expiry:** the bound is the save timeout (`STREAM_BLOCK_SAVE_TIMEOUT_SECONDS`, 20 s) plus 2 s, so it
    outlasts any settling save; on expiry the turn proceeds, logs one constant WARNING, and records the expiry as an event
    on the request span. Saves never await routes, so no cycle exists.
- A failed save still sends `final` (the answer did stream) with `persisted: false`. A timed-out save may still commit in
  its thread, so the one user-facing notice, raised by the dashboard's stream hook, is worded to be true in every case:
  "This answer may not have been saved to your chat history."
- The request's HTTP duration now includes the save (phase-8 D-11 unchanged: measured at the final body frame);
  documented, not compensated.

### 2.5 Response contract failure

- One error class, `ResponseContractError`, with its name set (so `error_type` telemetry records the class), a
  user-safe message, the validation issues on a separate field for logging (never rendered), a trace reference when one
  exists, and NO HTTP status.
- The parser validates, then returns the ORIGINAL object (zod 3's `z.object` strips undeclared keys, and the schemas
  cover only the fields callers read); a test proves an unread field survives.
- User copy when a write landed but its reply failed the contract: "Saved, but the response was unexpected. Refresh to
  see the latest." The affected lists are invalidated on this error, so the landed write appears.
- On `ResponseContractError` only, a flow that would re-create on retry (the optimizer wizard's Review step, the
  schedule dialog) stops and asks for a refresh instead of offering a retry; every other failure keeps today's retry
  behaviour (including the Review step's deliberate role re-create).

---

## 3. Dashboard correctness (lanes `guard`, `hub`, `contracts`, `webver`)

### Task 1 — Standalone build guard (item 6; lane `guard`)

**Finding.** `next.config.mjs` sets `output: "standalone"` unconditionally (Docker consumes it). In a worktree whose
`node_modules` is a symlink, nft records the link as a traced file and `copyTracedFiles` recreates it under
`.next/standalone/node_modules`, pointing at the shared tree. The destructive step is `cleanDistDir`'s
`recursiveDelete(distDir)` at the start of the NEXT build (`build/index.js:488`; it follows symlinked directories,
`lib/recursive-delete.js:57-68`), and the dev hot-reloader runs the same delete on every `next dev` start
(`hot-reloader-webpack.js:479`). The phase-9 §1c "rm before build" rule misses `next dev`. `outputFileTracingRoot`
defaults to the worktree already; a parent root still plants the link and moves `server.js`, breaking the Dockerfile.

Tests assert the true mechanism: the build delete spares `.next/cache` (`recursiveDelete(distDir, /^cache/)`); the dev
clean ignores `cleanDistDir` and always runs; `copyTracedFiles`' own `fs.rm` does not follow symlinks, so the danger is
only Next's `recursiveDelete` (stat, not lstat); `outputFileTracingRoot` defaults to the closest-lockfile directory (the
worktree, because the dashboard owns the only lockfile).

**Design (D10-7).** The config decides: if its own directory's `node_modules` is a symlink, standalone output is off
(one log line says why); if `.next/standalone/node_modules` is already a symlink, the config refuses to load with a
message naming the path and the safe removal. The config never deletes anything. Deploy builds (Amplify's fresh
install, Docker's deps layer) have a real `node_modules` and are unchanged.

**Files.** `next.config.mjs`; a small ESM predicate module it imports; `tests/unit/build/standalone-guard.test.ts`; the
phase-9 plan §1c rule text (session lead, at merge).

**Steps.**
- [ ] Failing unit tests on temporary directories: real `node_modules` → standalone on; symlinked → off with the log
      line; planted standalone link → refusal; nothing is ever deleted (a sentinel survives)
- [ ] Implement; tests green
- [ ] Scratchpad proof (never a worktree or the primary; every install, build and dev start under `dashboard.lock`): a tiny Next app pinned to the dashboard's Next version with its
      OWN install as the sacrificial shared tree, plus a sibling copy with an absolute `node_modules` symlink. Control
      without the guard reproduces the wipe; with the guard, two builds plus a dev start keep the sentinel; a hand-planted
      link makes build and dev refuse; the real-`node_modules` copy still emits `standalone/server.js`. Transcript to
      `copilot-mro/.dev_runs/obs10/task-1-build-guard-proof.md`
- [ ] Commit by pathspec

**Acceptance.** Unit tests green; the proof shows all four outcomes; the shared `node_modules` never touched; typecheck
and lint green under the dashboard lock.

### Task 2 — Document Hub: one `document_opened` per gesture, from every opener (item 4; lane `hub`)

**Finding.** F10 `1f2aa95` implemented "one gesture = one row" as: the citation card emits
`document_opened(document_hub, chat_citation)` and opens the preview; `ChatMessages` mounts `DocumentHubPreviewDialog`
with `arrivedFromChat` hard-coded (`ChatMessages.tsx:403`), so the dialog suppresses its own opened fact but still emits
`document_closed` with dwell. Inline Hub chips call the dialog setter directly (`markdown-renderer.tsx:514`), never the
card's emitter — so a chip open emits only a close, and skips the session's open counter. Core's `documents_opened` panel
and the Grafana frontend board undercount chip-opened Hub documents. Closes join by `document_id` only, so no option
orphans a close. Two plan records still list this as an open ruling (phase-4 Future Improvements; the master §15
owner-rulings line) — stale.

**Design (D10-6).** The preview dialog owns the fact for every opener: exactly one opened and one closed, with
`source_surface` supplied by its opener (`chat_citation` for both card and chip, `library` from the Hub page), and the
page number and department the card used to send passed through to the dialog. The card's Hub branch stops emitting
(its id check and drop counting move to the dialog path). Wire vocabulary and the owner ruling are unchanged. No
`markdown-renderer.tsx` edit is needed: the chip's `DocumentHubCitationRef` already carries the page
(`inline-content.ts:116-138`). Chip opens cannot reach the card's `doc.pageNumber` fallback (`DocumentCard.tsx:136,140`):
the dialog path preserves an equivalent fallback, or the report records the chip-side fidelity loss.

**Files.** `DocumentHubPreviewDialog.tsx`, `ChatMessages.tsx`, `DocumentCard.tsx`, `lib/telemetry/use-document-view.ts`;
tests `hub-preview-dedupe.test.tsx`, `document-card-open.test.tsx`, `document-view-hook.test.tsx`, plus a new wiring test:
one card click and one inline-chip click each yield exactly one `document_opened` with `chat_citation`, page number and
department (every absence assertion carries a presence control).

**Steps.**
- [ ] Failing tests (chat mode: exactly one opened + one closed with page and department; Hub card emits no opened while
      its callback still runs, the catalog card as control; the hook accepts `chat_citation`; the card/chip wiring test)
- [ ] Implement; tests green; canonical lanes under the dashboard lock
- [ ] Commit by pathspec (the session lead records the historical undercount — chip opens from `1f2aa95` to this merge
      are unrecoverable; card rows are correct — and closes the two stale ruling records at merge)

**Acceptance.** Card, chip and library opens each produce one opened + one closed with unchanged attributes; the session
open counter counts chip opens.

### Task 3 — Response contracts at the API layer (item 1; §2.5; lane `contracts`)

**Finding.** `fetchWithAuth` (`lib/api/fetch-utils.ts:166`) returns a bare `response.json()` and modules cast (optimizer
api 29 casts, client 27, …); zod is a direct dependency used for outgoing bodies only; the Document Hub mutations already
narrow their reply inside `mutationFn`, and `ReviewStep.tsx:284` already ships the same narrowing for one read (the in-repo
precedents). Sites that read a write's reply unchecked (12 of 13 verified by the Fable plan review; lines drift —
re-locate):

| Kind | Site (at `0a4dbec`) | Field read | Endpoint | Failure mode today when the field is missing |
|---|---|---|---|---|
| callback | `OutputsPanel.tsx:122` | `run.id` | optimizer POST jobs/{id}/run | `undefined` propagates silently |
| callback | `ActivitySetupPanel.tsx:943,960,961` | `saved.id` | optimizer POST/PUT activities | `undefined` propagates silently |
| callback | `UploadStep.tsx:86` (+`:91`) | `created.id` | optimizer POST schedules/upload | `undefined` propagates silently |
| callback | `ScheduleSetupPanel.tsx:295` | `created.id` | same | `undefined` propagates silently |
| callback (envelope only) | `RunsPanel.tsx:917-918` | `job.configSnapshot` | optimizer POST config-snapshot/refresh | fully `??`-guarded; only a non-object reply breaks it |
| callback | `data-discovery/jobs/[jobId]/page.tsx:715` | `run.level2_run_id` | data-discovery POST level2-runs | `undefined` propagates silently |
| callback | same file `:728` | `next.job_id` | data-discovery POST jobs/{id}/rerun | navigates to `/data-discovery/jobs/undefined` |
| callback | `data-discovery/page.tsx:189` | `job.job_id` | data-discovery POST data-sources/{id}/jobs | navigates to `/data-discovery/jobs/undefined` |
| callback read (low) | `ActivitySetupPanel.tsx:2375-2385` | `res.narrative` etc. | optimizer duration-query (not a write) | `undefined` renders |
| post-await | `ReviewStep.tsx:260`, `:290`, `:297/:299` | `created.id`, `run.id` | activity / job / run creates | `undefined` propagates (the role step at `:284` already throws) |
| post-await | `ScheduleDialog.tsx:707,722` (catch `:731-734`) | `automation.name` / `.automation_id` | automations create | **hard:** the silent catch keeps the dialog open on the draft → duplicate create |
| post-await | `useAdReview.ts:600-602` | `accepted.run_id` | AD review materialize (untyped route) | the button locks permanently |
| render-time | `airworthiness/page.tsx:194` → `adReviewPresentation.ts:188` | `result.states` | AD review recompute (untyped route) | **hard:** render-time TypeError |

The recorded "eleven unguarded reads" from the TanStack session were never enumerated; this table is a fresh superset.
The contract parser is the right fix for every mode — the loud ones and the silent ones.

**Design (D10-1, D10-2).** A shared contract parser in the API layer validates the reply of every API function whose
result fields are read after a write, before any callback runs; each schema covers only the fields callers read, is
type-tied to the existing TypeScript interface so `tsc` fails on drift, and the parser returns the original object
(§2.5). A guard test (reusing the mutation AST fixture) requires every API function called from a `mutationFn` to return
through the parser or appear in an exemption map with a written reason, with a presence floor and a vacuity check.
`lib/api/client.ts` holds no mutation producers, so the guard never needs it. **No backend response
models**: core's `POST /operators` deliberately declares none (an encode failure after commit would answer 500 for a
landed create), and the AD-review materialize reply has dynamic keys — FastAPI response validation runs after the handler
commits, so a server-side model would recreate item 1's failure on the server. The dashboard contract covers these
routes' read fields.

**Files.** New `lib/api/response-contract.ts` (+ unit test under `tests/unit/api/`); schemas in `optimizer-api.ts`,
`data-discovery.ts`, `automations-api.ts`, `ad-review-api.ts`; the error handling in `hooks/shared/useAppMutation.ts` and
the raw hooks behind the table's sites (invalidation on the contract error, the §2.5 retry rule); guard
`tests/unit/api/mutation-response-contract.test.ts`.

**Steps.**
- [ ] Failing helper tests (valid reply passes through untouched, unread fields intact; missing read field → the §2.5
      error with issues, no status, trace reference kept)
- [ ] Failing site tests: each row's test first reproduces that row's CURRENT failure mode (the table's last column), then
      asserts the §2.5 behaviour — the flow with a reply missing its field shows the §2.5 copy, keeps the landed
      write visible after invalidation, and never offers a duplicating retry on the contract error
- [ ] Failing guard (a new un-parsed mutation API function fails it; exemptions require reasons)
- [ ] Implement; canonical lanes under the dashboard lock; commit by pathspec

**Acceptance.** Every table row closed or exempted with a reason; guard green with its floor; a contract failure records
`error_type=ResponseContractError`; no backend change. Out of scope, recorded in §13: `SettingsAPI.makeRequest`'s 44
`any` callers; composite `mutationFn` intermediate reads; `useApiClient()` paths; server-side response models.

### Task 4 — Dashboard version (item 8, dashboard half; §2.3; lane `webver`)

**Finding.** The browser resource reads `APP_VERSION` (fallback `local`); iac hard-codes `"1.0.0"` and `amplify.yml`
copies it into `.env.production`; the Docker build passes nothing.

**Files.** `amplify.yml`, `Dockerfile`, the provider resource test (extend), a static test that the build derives
`APP_VERSION` rather than trusting a literal. (Task 14 removes the iac literal.)

**Steps.**
- [ ] Failing static + resource tests (present hex SHA; absent; non-hex such as `HEAD` treated as absent)
- [ ] Implement (Amplify: `package.json` version plus the first seven characters of `AWS_COMMIT_ID` when hex — `amplify.yml:10`'s env
      pass-through list must gain `AWS_COMMIT_ID`, unreferenced today; Docker: the
      `GIT_SHA` argument) → green → commit by pathspec

**Acceptance.** No literal version anywhere in the dashboard build path; all three SHA cases tested.

## 4. Chat write path (lanes `stream`, `streamui`, `cache`; §2.4)

### Task 5 — Persist the turn before `final`, never lose the save (item 2, server; lane `stream`)

**Finding.** Both engines reach one stream route in `copilot_mro/app/api/chat_management.py`: `final` is queued (`:1583`)
before `asyncio.create_task(save)` (`:1650`) with no reference held; the generator sends `final` and ends. On disconnect
the generator's `finally` cancels `run_pipeline` (`:1685-1692`). Timeout and `False` returns only warn; only exceptions
are counted. Memory writes are already fire-and-forget inside `execute`, and usage books in the orchestrator, so only the
block save moves. The next turn's server-side context read races the save too. The gateway mounts copilot-mro
in-process, and a mounted sub-app gets no lifespan — the gateway's lifespan (`api/flynapse_api/main.py:241`) is the one
that runs. The telegram bot's `FinalEvent` keeps the raw payload, so it tolerates the new field.

**Files.** `chat_management.py` (the stream route); a small save-task registry module beside it; the shutdown drain call
in copilot-mro `app/main.py`'s lifespan and in the gateway's lifespan (`api-obs10-stream`, one hunk — §1b); new API tests
in a two-level domain folder under copilot-mro `tests/api/`, including a raw-ASGI driver that injects `http.disconnect`
mid-stream (Starlette's TestClient cannot).

**Steps.**
- [ ] Failing API tests with a fake chat store whose save blocks on an event: no `final` frame until released; a
      disconnect (raw-ASGI driver) during the save still commits AND records its outcome; exception / timeout / `False`
      each yield `final` with `persisted: false` and exactly one counted failure with the matching reason; the registry
      empties when the save settles; shutdown drain awaits a pending save within its bound; a new turn for a chat whose
      previous save is still registered waits (bounded) for it before its context read; two pending saves on one chat are
      both awaited by the next turn's wait, both drained and both counted; a wait that expires leaves the save running and
      the save still records its outcome
- [ ] Implement per §2.4; the save span becomes a child of the request's span; extend the existing block-save failure
      counter with the bounded reason (a new metric name only if the existing one cannot carry it — show why)
- [ ] Consumer sweep with evidence per consumer: telegram-bot and any other in-estate `/rag/stream` client (e2e harnesses
      included) tolerates the field and a later `final` (the dashboard is Task 6)
- [ ] Commit by pathspec in each tree

**Acceptance.** No `final` before the save settles on any path; no save outcome lost to disconnect or shutdown; failures
counted with their reason; no turn's context read runs before the same chat's previous saves settle, connected client or
not, unless the bounded wait expires (logged, and the save keeps running); every non-dashboard consumer
verified.

### Task 6 — The dashboard honours `persisted` (item 2, client; lane `streamui`)

**Finding.** The dashboard reader cancels on `final` (`lib/api/client.ts:268-275`); the turn end unlocks sending,
refetches the chat list and marks history stale (`useDepartmentMessageStream.ts:473-500`); a comment near `:457-464`
describes the old ordering; reopen paths include the dock's "open in full view" deep link, sidebar selection, reload
restore and retry; Crew and Pilot share the hook.

**Files.** `lib/api/client.ts`, the streaming helper, `useDepartmentMessageStream.ts` + their tests.

**Steps.**
- [ ] Failing tests: `final` with `persisted: false` raises the §2.4 notice once from the stream hook; `persisted: true`
      and an ABSENT field raise nothing; the send lock still releases on `final`; all three departments covered through
      the shared hook
- [ ] Implement; correct the whole stale docblock — the ordering comment (`:460-463`) and the `refetchType: 'none'`
      rationale (`:466-471`), which also becomes wrong once the save precedes `final` (behaviour unchanged unless a test
      shows the old workaround now harms); canonical lanes under the dashboard lock; commit by pathspec

**Acceptance.** The notice appears only on `persisted: false`; old-server streams behave exactly as today.

### Task 7 — Version the chat-blocks cache key (D10-5b; item 2, stale history; lane `cache`)

**Finding.** `get_chat_history` (`chat_history/blocks.py:411-499`) is cache-first on a `blocks:` key (`base.py:43`)
with a 300 s write-back on a miss (`:480`); the save invalidates after commit (`:636-656`), and `chats.py` invalidates
too. A reader that misses, reads the database, then writes back after a concurrent save's invalidation leaves a stale
copy every reader sees for 300 s — Task 5 cannot close this, since the reader may be another client. Guarding the
write-back needs a compare-and-set primitive `utils.cache_service` does not have. The cache buys little: its hit path
already runs a Postgres compaction query whenever blocks carry segment ids, and it skips the ownership check the miss
path performs.

**Original design (D10-5), WITHDRAWN.** Remove the blocks cache, with a stop condition: if the uncached read of a
≥200-block chat on the test database exceeded p95 50 ms, stop and re-plan.

**Stop condition HIT (2026-09-15, implementer measurement on `copilot_mro_test`).** Uncached p95 27.7 ms for light blocks
(~1.2 KB each) but 390 ms for rich blocks (~54 KB each: document cards, citations, tool log); the cache saves 100–230 ms
per rich read. Inventory confirmed: one key builder (`base.py:42-43`), one read plus one write-back in `get_chat_history`,
two invalidations (`save_block`, `delete_chat`), three callers (`chat_management.py:622`, `:1080`, `:1380`), nothing else
estate-wide.

**Design (D10-5b, session-lead re-plan).** Version the cache key by a per-chat generation token instead of guarding the
write-back. No compare-and-set is needed, so `utils.cache_service`'s get/set/delete API suffices and utils is not changed.
- A per-chat generation key holds an opaque token. `save_block` (after its commit) and `delete_chat` set a FRESH token.
- Every history read first gets the current token and uses a blocks key that includes it. On a miss it reads the database
  and writes back under the key for the token it read BEFORE the database read.
- A stale write-back (a read that began before a save's commit) therefore lands under the old token's key, which no later
  read consults: unreachable by construction, expiring by its 300 s TTL.
- A read that finds no token (never set, expired, or a failed cache read) SETS a fresh token before its database read
  and uses it, so no entry is ever written under an "absent" key (amended 2026-09-15 at Task 7's review: the original
  "absent is a valid token value" rule let a stale absent-key entry be served after a transient token-read failure). This
  needs no compare-and-set: a read's token SET always precedes its snapshot, so any save committing after the snapshot
  renews the token later. The generation key's TTL (24 h) stays far above the blocks TTL (300 s).
- The existing invalidating deletes stay as belt-and-braces (they also cover a failed token write); the correctness
  argument does not rest on them. Ownership semantics on a hit are unchanged — the key stays scoped by tenant, user and
  department.

**Files.** `chat_history/blocks.py`, `chat_history/chats.py`, `chat_history/base.py` (the `blocks:` key paths and the
generation key); the chat-history tests.

**Steps.**
- [x] Rework the first attempt's uncommitted failing tests to this design (drop the removal-only guard that forbids any
      `blocks:` key): deterministic interleavings for both cache backends — a read that starts before a save's commit and
      writes back after it never serves that stale history to a later read; a read after a save sees the new block;
      `delete_chat` makes earlier entries unreachable; an absent or expired generation token never re-exposes a stale
      entry; a read never returns another user's chat
- [x] Implement; chat-history unit and DB suites green (db lock); record the hit-path cost of the extra generation lookup
- [x] Commit by pathspec

**Acceptance.** The stale write-back race is closed for both cache backends without a compare-and-set primitive; the
cache's latency benefit is preserved (one extra small cache GET per read); measurement and inventory recorded.

## 5. oss alerting + smoke isolation (lanes `smoke`, `alerting`, `awsotel`; §2.1, §2.2)

### Task 8 — Project-scoped smoke networks (item 7; lane `smoke`)

**Finding.** `deployment/otel/smoke/docker-compose.smoke.yml:79` and `docker-compose.grafana-smoke.yml:36` override
their networks with literal names (`copilot-network` in the OTel smoke, `observability` in the Grafana smoke); nothing
needs them (only the base `copilot-network` is joined externally, and the
overrides replace it). A render proved dropping `name:` yields `<project>_copilot-network`. Smoke project names are
constants, so two lanes with different port prefixes would still recreate each other's containers; the Grafana smoke
hard-codes host port 13000.

**Files.** Both smoke overrides (drop the literal names, correct the header comment, the Grafana host port honours
`OTEL_SMOKE_PORT_PREFIX`); `tests/integration/otel/conftest.py` and the Grafana smoke test (project names derived from the
port prefix); a new guard (no literal network name in any smoke override; at least two files scanned; a loader that
tolerates compose's `!override` tag); optionally a docker-gated render check that two project names give two networks.

**Steps.**
- [ ] Failing guard → change → otel lane with the smokes (`OTEL_COMPOSE_SMOKE=1`, under the compose lock) → commit by
      pathspec

**Acceptance.** Guard green; both smokes green; the render check (docker present) shows distinct networks.

### Task 9 — Environment stamp and routing (item 3; §2.2; lane `alerting`)

**Files.** The three stacks' compose files (environment default), the ONE shared `prometheus.yml` and `loki-config.yaml`
(bare `${VAR}` external
label), `alertmanager.yml` (root receiver `dev`, routes per §2.2), the Alertmanager config and routing tests.

**Steps.**
- [ ] Failing tests: an unlabeled alert routes to `dev`; `amtool` route tests for prod critical, prod warning and dev (under
      the compose lock)
- [ ] Implement → otel lane (`OTEL_RULES_CHECK=1`) → commit by pathspec

**Acceptance.** Every alert has exactly one environment route; unlabeled alerts land on `dev`.

### Task 10 — Threshold changes (item 3; §2.1; lane `alerting`)

**Files.** The Prometheus and Loki rule files; the rules layout test (thresholds pinned to §2.1).

**Steps.**
- [ ] Failing guard pinning §2.1's `oss` numbers, guards and severities
- [ ] Implement: the ApiP95LatencyHigh exclusion + volume guard (exclusion list tested against the gateway's real route
      names), TelegramTurnFailureRate → warning, the Web Vitals sample guards → `promtool` and the Loki structural checks
      green (compose lock) → commit by pathspec

**Acceptance.** Rule files match §2.1 exactly; each guarded threshold states its guard in its description. The
exclusion-list test is load-bearing, not cosmetic: saving before `final` (Task 5) lengthens streamed-route durations, and
only the exclusion keeps them un-paged.

### Task 11 — Delivery failures become visible (item 3; lane `alerting`)

**Files.** `prometheus.yml` (Alertmanager scrape job), the closed scrape-set test, the platform rule file
(AlertmanagerNotificationsFailing), `docs/runbooks/observability/alerts.md` (anchor).

**Steps.**
- [ ] Failing tests (scrape set includes Alertmanager; the rule exists with its runbook anchor) → implement → otel lane →
      commit by pathspec

**Acceptance.** A failing notification integration raises a critical alert; the runbook anchor guard is green.

### Task 12 — Real targets and the null-target config (item 3; §2.2; lane `alerting`)

**Files.** `alertmanager.yml` (the §2.2 literals, file fields for both webhooks and the SMTP password); a null-target
config with the identical route tree; the three stacks' compose files (config selection by one variable; both webhook
files and the password file mounted from env-selected host paths, placeholders by default); `test_alertmanager_config.py`;
`docs/runbooks/observability/oss-profile.md`.

**Steps.**
- [ ] Rewrite `test_alertmanager_config.py` to fail first on the real invariants — secrets only through file fields, no
      webhook URL literal anywhere in the scanned tree, identical route trees in both configs, null receivers carry no
      integrations — instead of asserting placeholder text, while keeping the file's compose-shape assertions (image equals
      `VERSIONS.md`, the exact loopback port list, the env-selected secret mounts) extended to the switch variable and the
      second webhook
- [ ] Implement; `amtool check-config` green on both configs (compose lock)
- [ ] `oss-profile.md` names, per stack, the exact gitignored `.env`, the three secret file paths and the switch variable
- [ ] Commit by pathspec

**Acceptance.** §2.2 literals present; nothing secret committed; placeholder stacks send nothing and fail nothing; laptop
stacks can never reach prod destinations.

### Task 13 — Collector self-telemetry for `aws` (item 5, feeds Task 15's collector alarms; lane `awsotel`)

**Files.** The `aws` collector overlay under `deployment/otel/`; a new collector-profile test under
`tests/integration/otel/`; `docs/runbooks/observability/aws-profile.md` (the added CloudWatch cost).

**Steps.**
- [ ] Failing test: the merged `aws` config contains both the base Prometheus reader and a new periodic OTLP reader
      exporting the collector's own metrics through its metrics pipeline (the overlay REPLACES the base `readers` list
      under the confmap list rule, so the overlay must restate the base reader); `oss` contains only the base reader
- [ ] Implement; `otelcol validate` per profile (compose lock); commit by pathspec

**Acceptance.** Only `aws` gains the reader; both profiles validate; cost documented.

### Task 22 — Worker liveness log (item 5, feeds Task 15's AutomationWorkerSilent; lane `awsotel`; added during execution)

**Finding (Task 15, 2026-09-15).** The `aws` AutomationWorkerSilent alarm (§2.1: zero worker log records in 15 minutes,
missing data = breaching) assumes a live worker logs. The api scheduler loop (`flynapse_api/automations/loop.py`,
`scheduler_loop`) logs only ticks with news, and the worker logs only at start and stop, so an idle, healthy worker is
silent and would page. The `oss` rule watches `target_info`, which an idle worker still exports; no worker metric is
exported unconditionally that an `aws` PromQL alarm could watch instead.

**Design (ruling T15-HEARTBEAT).** The scheduler loop emits one constant-body INFO liveness record at most once per
300 s, whether or not a tick had news. The record carries no user content and a constant key set; the cadence is a
module constant. 300 s gives three records per 15-minute window, so one lost record never pages. A loop hosted inside the
gateway emits it too — harmless, because the alarm filters on the worker's service name. The §2.1 pin is unchanged.

**Files.** api `flynapse_api/automations/loop.py`; a unit test under api `tests/unit/automations/` (two-level layout,
globally unique basename). Worktree `api-obs10-awsotel` (branch `obs10-awsotel`, off the api tip).

**Steps.**
- [ ] Failing test: an idle loop (a tick stub returning an empty summary, time driven without real sleeps) emits the
      liveness record once per 300 s window and never more often; a tick with news neither suppresses nor duplicates it;
      the record body is constant
- [ ] Implement → api automations unit tests green (full suite under the python-full lock) → commit by pathspec

**Acceptance.** An idle worker logs at least once every 5 minutes; a busy worker's log volume grows by at most one record
per 5 minutes; Task 15's alarm comment and the iac README point at this record (Task 15 fix round).

## 6. aws alarms (lane `iac`; §2.1, §2.2, §2.3)

### Task 14 — Provider raise with `user_data` untouched, and the Amplify literal (items 5, 8; lane `iac`)

**Finding.** The root pins `aws ~> 5.0` (resolves 5.100.0); both `aws_instance` resources pass `base64encode(...)` into
`user_data` with `user_data_replace_on_change = true`. Provider 6.0 removed 5.x's hashing `StateFunc` but added a
`DiffSuppressFunc` that treats a 5.x hash in state as equal to the equivalent cleartext (PR #42078, covered by
`TestAccEC2Instance_UserData_migrate`), so a pure version bump with unchanged content plans no `user_data` diff and no
replacement. Moving to `user_data_base64` instead would be a real config diff on exactly the attribute pair the replace flag
covers — the risky change — and `user_data_base64` under 6.x carries open issue #44506 (refresh writes raw binary into
`user_data` state). 6.x prints a plan-time warning that the base64 value is kept as cleartext in state, and from the first
6.x refresh the POC template's `user_data` (a GitHub token, a live IAM secret access key, the Azure OpenAI key) sits in
state that way. `outputs.tf` reads the bucket's `region` (`bucket_region` in 6.x). Provider issue #47624 — a 6.42.0
regression from the same PR that added `promql_criteria` (`metric_name` from an unknown reference fails validation) — is
fixed in 6.43.0, so the `~> 6.43` pin is load-bearing. The `archive` provider is unconstrained in `required_providers`
(lock-only); `modules/otel-gateway` is instantiated only by its own example root, outside the upgrade surface. `gpu-host`
is a separate root pinned exactly to 5.100.0. `amplify.tf:72` hard-codes `APP_VERSION = "1.0.0"` (Task 4 computes it at
build).

**Files.** `iac/main.tf` (constraint `~> 6.43`), `outputs.tf`, `amplify.tf` (remove the literal), the provider lock file
(regenerated by `init -upgrade`; committed if tracked); `README.md` owner steps. `ec2.tf` and `ec2_poc.tf` are NOT edited.
`gpu-host` untouched.

**Steps.**
- [ ] Inventory every resource and data-source type in the root against the 6.0 upgrade guide (prove completeness; record
      the `archive` constraint gap and the out-of-surface module)
- [ ] Edits → `terraform fmt -check`, `init -upgrade -backend=false`, `validate` → commit by pathspec
- [ ] README owner steps: (a) before the R19 merge, a read-only backend `terraform plan` — RELATIVE acceptance
      (ruling R19-GATE, R19 composition review): the branch plan shows the same replacement set as a 5.x control plan
      on `main` and no replacement or `user_data` change attributable to the provider raise (the absolute "zero
      replacements" form was unachievable: the unapplied 2026-09-05 setup-script change already replaces both
      instances, and `github_token` is sensitive so `user_data` prints `(sensitive value)`); (b) expect the
      base64-cleartext warning on both instances — accepted noise;
      (c) confirm the state bucket's encryption and access, since the POC `user_data` secrets sit in state from 6.x

**Acceptance.** Validate green on 6.x; `user_data` untouched; no literal version in iac; owner steps documented; the
`user_data_base64` move recorded in §13, not done.

### Task 15 — Two topics and `alarms.tf` (item 5; lane `iac`)

- **Topics:** the existing alert topic becomes `critical` through a `moved` block (only the Terraform address moves; the
  topic's `name` argument stays exactly as it is — `name` is ForceNew in the provider schema though the registry page does
  not say so, and a rename would replace the topic, orphan subscriptions and change the ARN; no email subscription exists
  today, since `alert_email_addresses` defaults empty and Task 16 creates the first, but any subscriptions
  survive); a new `warning` topic; email subscriptions on `critical` only; the Slack forwarder gets one subscription and
  one Lambda permission per topic; the forwarder (`lambda_src/sns_to_slack.py`) derives the severity from the source
  topic and prefixes the message.
- **Alarms:** PromQL alarms for the metric alerts (thresholds and minimums from ONE locals map mirroring §2.1), metric
  filters + alarms for the log-derived alerts (reconciled with the D9-11 filters the phase-9 docs describe), the collector
  alarms and CollectorTelemetryAbsent over Task 13's series, the cross-routed AlertDeliveryFailing alarms; each alarm's
  alarm and OK actions target the topic matching its severity.
- **RE-VERIFY markers** on every field that depends on probe B1a (delta temporality under `rate`/`increase`, histogram
  shape, label names) or B1b (log field paths, numeric `value`, p75 and `SampleCount` on filter metrics), naming the probe.
- **Metric math (Web Vitals sample guard):** set `TreatMissingData` deliberately (`IF()` yields missing, not 0, when there
  is no data); the metric filters carry no default value (default-0 points inflate `SampleCount` and drag p75);
  percentiles need non-negative values (Web Vitals are). The RE-VERIFY list gains one line for `promql_criteria`'s
  empty-result and `absent()` semantics, which neither B1a nor B1b covers.
- **Blind spot, documented:** SNS `NumberOfNotificationsFailed` sees email failures only at the SNS attempt; bounces after
  hand-off are invisible — a note in the iac README (not `aws-profile.md`, which lane `awsotel` owns); §10's receipt confirmation covers first delivery.
- **Validation:** a static validator script beside `scripts/validate_dashboards.sh` — every §2.1 alert has an `aws` form
  or a documented `oss`-only reason; thresholds equal the locals map; every alarm targets its severity's topic; the
  delivery-failure alarms cross-route. The forwarder change gets a Python unit test; iac has no test tree, so this task
  scaffolds one per the workspace rule (`tests/_root.py` plus the layout and depth guards copied from an existing repo;
  the test in `tests/unit/alerting/`), run from the shared api env. `terraform validate` green.

**Steps.**
- [ ] Failing validator + forwarder test → topics → alarms → validate → commit by pathspec

**Acceptance.** Every §2.1 alert accounted for with its severity's topic; the topic is never replaced (the address move preserves any subscriptions); validator and
validate green; nothing applied.

### Task 16 — Targets plumbing (item 3; lane `iac`)

**Files.** `README.md`, the variables file (descriptions only), an example untracked var-file name in `.gitignore` if not
already covered.

**Steps.**
- [ ] `alert_email_addresses` (`aditya@flynapse.ai`) and the Slack SSM parameter name documented through an untracked
      var-file or `TF_VAR_` (`dev.tfvars` is tracked, so no address goes there); the README notes this creates the estate's FIRST alert email subscription (AWS mails a confirmation link to
      the address at the owner's first apply); a check that no tracked file carries the
      address → commit by pathspec

**Acceptance.** The owner can supply both values without editing a tracked file; `terraform validate` green.

## 7. Service version, Python (lanes `otelver`, `pyver`, `images`; §2.3)

### Task 17 — Resource precedence in `flynapse_otel.resource` (item 8; lane `otelver`)

**Finding.** The builder lets the environment win per key and defaults to `unknown` (`resource.py:28-57`); the raw SDK
merge would let code win, so the filter is what gives env precedence. `OTEL_RESOURCE_ATTRIBUTES` is parsed as one
variable and whole-replaced by compose `env_file` and iac.

**Files.** `flynapse_otel/resource.py`, `tests/unit/.../test_resource_identity.py`, the flynapse-otel env-scrub conftest
(`SERVICE_VERSION`, `BUILD_GIT_SHA`).

**Steps.**
- [ ] Failing tests: `SERVICE_VERSION` used; `service.version` inside `OTEL_RESOURCE_ATTRIBUTES` wins; an
      `OTEL_RESOURCE_ATTRIBUTES` holding only `deployment.environment.name` still yields the code-derived version (the
      merge-seam proof); `+sha7` appended once to the code-derived version and never to an operator-set value
- [ ] Implement → green → commit by pathspec

**Acceptance.** §2.3 precedence and format hold; scrub list updated.

### Task 18 — The distribution-name seam; no fake version (item 8; lane `pyver`)

**Files.** utils `logging_config.py` + observability tests + its env-scrub conftest (and the legacy env-reader guard list
if it enumerates readers); api `flynapse_api/main.py` (the `setup_logging` hunk), `automations/worker.py`,
`tests/conftest.py` scrub list; copilot-mro `app/main.py` (the `setup_logging` hunk); shift-optimizer
`tests/unit/telemetry/conftest.py` scrub list.

**Steps.**
- [ ] Failing utils tests: the settings default (`0.1.0`) can no longer reach the resource; a named distribution's
      version is what utils passes to the resource builder (assert the seam, not the composed output — Task 17 owns
      composition)
- [ ] Implement the optional distribution name (§2.3); callers pass their own names: the gateway, the automation worker,
      copilot-mro standalone
- [ ] Scrub lists gain `SERVICE_VERSION` and `BUILD_GIT_SHA` in utils, api and shift-optimizer telemetry suites
- [ ] Lanes with the §1c import-path evidence → commit by pathspec in each tree

**Acceptance.** No caller can emit `0.1.0`. The kwarg is optional for callers that do not pass it, but the three callers
that DO pass `distribution=` raise `TypeError` against a utils without it (corrected 2026-09-15 at Task 18's review), so
utils merges — and publishes — before api and copilot-mro (§9 merge-order rules).

### Task 19 — Images carry the SHA and their own metadata (item 8; lane `images`)

**Files.** api `Dockerfile`, `compose.yaml` (both builds it owns), `.github/workflows/deploy.yml`; telegram-bot
`Dockerfile`, `.env.sample`, `tests/unit/telemetry/conftest.py` scrub list; copilot-mro `Dockerfile` (currently
`poetry install --no-root`); static tests in each repo's two-level layout.

**Steps.**
- [ ] Failing static tests: each Dockerfile declares `GIT_SHA` and exposes it as `BUILD_GIT_SHA`, and installs its own
      project without dependencies; each build passes the argument; the deploy workflow passes the commit SHA
- [ ] Implement → static tests green → commit by pathspec in each tree (image builds themselves run in the §10 live batch)

**Acceptance.** Every Python service image can report `<semver>+<sha7>` from its own metadata.

## 8. RLS lane (lane `rls`)

**L10.0 — one-off re-run (session lead, after the owner's go; not an SDD task).** From the shared api env as the database
owner, the password passed through the environment (never argv), under `/tmp/obs10-locks/db-shift_optimizer_test.lock`:
`provision_rls.py` against `shift_optimizer_test` with `--verify-only` (record violations), then applied
(`--enforce-undeclared` only if the verify output names undeclared tables), then verified again; the optimizer
`tests/api` lane's 62 setup errors must reach zero. `copilot_mro_test` gets a verify-only run, recorded.

### Task 20 — Provisioner lock + preflight decision helper (item 9; lane `rls`)

**Files.** copilot-mro `scripts/provision_rls.py`; utils db-guard module + a unit test in an existing utils domain folder.

**Steps.**
- [ ] Failing tests: the provisioner holds a session-level Postgres advisory lock for its whole run (a second run waits
      rather than interleaving — `ENABLE ROW LEVEL SECURITY` takes ACCESS EXCLUSIVE locks); the decision function, given
      the violations from `utils.rls_boot_check.rls_violations`, the target database, the suite's configured test
      database, the protected-database list and owner-credential availability, returns none / heal / stop-with-remedy —
      tested as a table: never heal a protected database, never heal without owner credentials, a clean database costs
      one read-only check
- [ ] Implement → green (db lock for the lock test) → commit by pathspec in each tree

**Acceptance.** The lock and the decision table are proven; no password in argv anywhere.

### Task 21 — Suite wiring (item 9; lane `rls`)

**Files.** shift-optimizer `tests/conftest.py` + README; copilot-mro `tests/conftest.py`.

**Steps.**
- [ ] Session-scoped preflight in shift-optimizer (db and api lanes) and copilot-mro (for `copilot_mro_test`), running
      ONLY when DB-marked tests are collected (unit lanes stay DB-less and fast)
- [ ] Heal = the provisioning script as a subprocess (copilot-mro's own via `repo_root`, the optimizer's via
      `sibling_repo`), never an import of the copilot-mro package; the owner password via the subprocess environment only;
      every heal logs loudly first (violation names, no data, and that a heal is running); stop = `pytest.exit` with the
      exact command, never the password
- [ ] shift-optimizer README drift (fixtures no longer build tables) corrected
- [ ] Mutation proof on the test database only (db lock): drop one policy → the preflight logs the violation, heals, and
      the lane passes
- [ ] Commit by pathspec in each tree

**Acceptance.** Stale policies heal loudly on test databases; protected-database and no-credential paths stop with the
remedy; unit lanes unaffected.

---

## 9. Review design and the Fable handoff

**Phase A — this chat, Opus 5 controller, subagent-driven development.**
- **Workspace:** the SDD ledger `progress.md` and every brief, report and review package live in
  `/home/aditya/Code/.superpowers/sdd/observability-rebuild-phase-10-owner-follow-ups/`; the ledger's first line names this
  plan; the ledger (and `git log`) is the recovery map after compaction. Lane-level lines record BASE per repo, task
  completion, fix rounds, deferred minors, parked findings and every `Ruling:`.
- **Per task:** a task brief (the task's section, extracted to a file) + a shared pins file (§1b, §1c, §2) + the constraints
  block → one Opus 5 implementer (no subagents of its own; writes its report file; returns status, commits, one-line tests,
  concerns) → one Opus 5 task reviewer (spec compliance + quality, from the brief, the report and the review package) →
  fix rounds (≤5: rounds 1–3 resume the implementer; 4–5 a fresh Opus 5 implementer at the highest effort) with a scoped
  re-review each → `Task N: complete` in the ledger.
- **Parallelism:** lanes run concurrently; within a lane, one implementer at a time and tasks in order (the SDD "never
  parallel implementers" rule is honoured per worktree, which is where its conflicts live).
- **Per lane close:** a fresh Opus 5 whole-lane reviewer over the lane's full range per repo, pointed at the lane's
  deferred-minor and parked lines → at most one fix wave + one scoped re-review → the lane's gate request (below).

**Phase B — a separate Fable 5 chat with its own Fable controller.** Handoff directory:
`copilot-mro/.dev_runs/obs10-fable-gate/`. Every file has exactly one writer.
- **This chat writes `R<nn>-request.md`** when a chunk's lanes close Phase A: the lanes and tasks, per repo the worktree
  path, branch, BASE (the mainline tip it branched from) and HEAD, the whole-lane review package paths, the task brief
  paths, the Phase-A ledger lines (rulings, parked, deferred minors), and the lane test evidence.
- **The Fable chat writes `R<nn>-verdict.md`:** MERGE-READY, MERGE-READY AFTER FIXES, or NOT READY, with findings.
- **Fixes:** this chat dispatches an Opus 5 fix wave in the same worktrees plus a scoped Opus re-review, then writes
  `R<nn>-fix-<k>.md` (the fix range's review package + evidence); the Fable chat re-verifies scoped and records the outcome in
  a new `R<nn>-verdict-<k>.md`.
- **Merge:** this chat merges only on a MERGE-READY verdict (or every Fable finding verified addressed), `--no-ff`, runs the
  chunk's post-merge lane, applies the moved-base rule (merge the moved base into the branch, re-run the lane, then merge),
  and writes `R<nn>-merged.md` (merge SHAs + post-merge lane evidence). Pushes on the owner's word.
- The Fable chat may review chunks in parallel as their requests land; this chat merges in verdict order per repo.
- **One cross-chunk order rule:** R19's iac merge lands after R20's dashboard merge, so the Amplify literal's removal never
  precedes the build-time computation.
- **R20 internal order (added during execution; refined by the R20 composition review and its fix-wave re-review):**
  1. flynapse-otel `obs10-otelver` merges first, and the primary flynapse-otel checkout is updated: utils' lock names
     its `../flynapse-otel` path dependency at the bumped `0.1.1`, which `poetry lock` reproduces only once otelver is
     in the primary (ruling R20-ORDER).
  2. utils `obs10-pyver`, and the primary utils checkout is updated. api and copilot-mro now pass `distribution=` to
     `setup_logging`, and the shared env resolves primaries.
  3. The api / copilot-mro / shift-optimizer `obs10-pyver` branches, into the primaries before any api or copilot-mro
     suite runs from the shared env.
  4. The api / telegram-bot / copilot-mro `obs10-images` branches (copilot-mro under the moved-base rule).
  5. dashboard `obs10-webver`, before R19's iac merge.

  Afterwards: `poetry install` in the shared api env (editable installs keep the old `.dist-info` versions until then);
  the consumer locks hold stale `flynapse-otel 0.1.0` / `flynapse-utils 0.1.38` entries until their next `poetry lock`.

  `pyver` never lands after `otelver` or `images`; otherwise a merged tree composes `0.1.0+<sha7>`. Publishing needs the
  utils and flynapse-otel patch bumps made in the R20 fix wave (ruling R20-BUMP): utils refuses to re-publish an
  existing version. The owner's iac apply follows the first Amplify deploy of the new `amplify.yml`.
- **R15 internal order:** copilot-mro `obs10-stream` merges before, or in the same step as, api `obs10-stream`. The
  primary copilot-mro checkout is updated first, because api's drain test drives the real lifespan, which imports
  copilot-mro's save registry (ruling R15-ORDER).
- **Shared box:** the Fable chat's Phase-B review lanes take the same §1c locks — both chats run on one machine.
- **Signalling:** the files are the record; cross-session messages are the doorbell. This chat is local session
  `code-2e`. When a request or fix file lands, this chat sends the Fable session (currently `code-a9`) one `SendMessage` naming the file (the
  first line says which chunk and what is asked). The Fable controller answers the same way when a verdict file lands
  (`to` = `code-2e`). A message never carries findings or code — only the file path — and neither side acts on a message
  whose file does not exist yet.

**Owner gates.** The Fable plan review; the go on this plan and the agent cap; the read-only backend `terraform plan`
before R19's merge (relative acceptance against a 5.x control plan on `main` — ruling R19-GATE, Task 14); receipt
confirmation in §10; the secret files whenever the owner switches a stack to real targets.

## 10. Live batch (after the merges; session lead runs it, owner present)

- The owner writes the three secret files and switches the `deployment` stack to the real config; recreate
  `alertmanager`, `prometheus` and `loki` from the merged spec; fire synthetic prod-critical, prod-warning and dev alerts
  through `amtool`; the owner confirms `#prod-alerts`, `#dev-alerts` and email receipt match §2.2;
  AlertmanagerNotificationsFailing's source series is present and quiet.
- One live `/rag/stream` turn, then immediate reopen through the dock's "open in full view": the turn is present; `final`
  carried `persisted: true`.
- Rebuild the api and bot images with a SHA: `service_version` on `target_info` reads `<semver>+<sha7>`.
- Carried from phases 8/9: the §10 Telegram probe and the F-R6-6 extended re-probe.

### 10a. Plan review triage (independent Opus 5, 2026-09-15; verdict READY AFTER CHANGES)

| Finding | Disposition (v2; task numbers per v3) |
|---|---|
| P1-1 The cache write-back guard needs a utils compare-and-set no lane owns; bump-before-commit re-opens the race; `chats.py` also invalidates | Design changed: remove the blocks cache (Task 7) with a measured stop condition; the guarded write-back is the fallback, re-planned if hit |
| P1-2 The alarms task contradicted the two-topic ruling (single Lambda permission, subscriptions, severity-less forwarder, failure alarm onto a failing topic) | Task 15 rewritten: `moved` block, per-topic subscription + permission, severity prefix, cross-routed delivery-failure alarms, validator per severity |
| P1-3 Backend response models recreate item 1's failure server-side | Dropped; recorded in Task 3 and §13 |
| P1-4 Disconnect cancels the awaiting generator; no shutdown drain | §2.4 + Task 5: registry-held save task, shield, self-recorded outcome, lifespan drain (the gateway's), raw-ASGI disconnect test |
| P2-5 A timed-out save may still commit | One notice worded true in every case (§2.4) |
| P2-6 zod 3 strips undeclared keys | Parser returns the original object; test (§2.5) |
| P2-7 Prometheus 3.x expands external labels by default, no default syntax; demo stack has no Prometheus | §2.2: compose supplies the default; root receiver `dev`; unlabeled-alert test; three named stacks |
| P2-8 Placeholder targets → permanent critical | Null-target config by default (§2.2, Task 12) |
| P2-9 Self-telemetry shares the exporter it watches; overlay replaces `readers` | CollectorTelemetryAbsent (§2.1); Task 13 asserts the merged readers |
| P2-10 `AWS_COMMIT_ID` is `HEAD` on rebuilds | Non-hex = absent, tested (§2.3, Task 4) |
| P2-11 utils cannot know the distribution; copilot-mro image `--no-root`; cross-repo import paths | Task 18 distribution-name seam; Task 19 copilot-mro Dockerfile; §1c import-path evidence |
| P2-12 Lock file; #47624; plan proof needs a backend; secrets in state | `~> 6.43`; lock regenerated; owner `plan` gate before R19; state-bucket confirmation + §13 |
| P2-13 Provisioner has no lock; password in argv; unit-lane cost; violation source | Task 20 advisory lock; env-only password; DB-marked-only preflight (Task 21); `rls_violations` named |
| P2-14 No shared-file table | §1b |
| P2-15 CloudWatch sample guard needs metric math | §2.1 `aws` form + locals minimum |
| P3 page number/department lost in the Hub fix; ReviewStep role re-create; "20 requests" wording; test locations; `+sha` on operator values; CI workflows | All folded in (Task 2, §2.5, §2.1, Tasks 15/20, §2.3, constraints) |

### 10b. Fable plan review triage (owner's Fable 5 chat, 2026-09-15, reviewed v2; verdict READY AFTER CHANGES)

Report: `copilot-mro/.dev_runs/obs10-fable-gate/plan-review.md` (three read-only Opus fact-checkers under a Fable lead).

| Finding | Disposition (v4) |
|---|---|
| P1-1 The provider-raise premise was inverted: 6.0's diff-suppress makes a pure bump plan no `user_data` diff; the planned `user_data_base64` move is the replacement risk (plus open issue #44506) | Task 14 rewritten: raise with `user_data` untouched; the encoded-content static check dropped; the base64-cleartext plan warning accepted as noise; the `user_data_base64` move → §13 beside the SSM secret removal; the owner `plan` gate stays (now also "no `user_data` diff") |
| P2-1 SNS topic `name` is ForceNew; a rename replaces the topic despite `moved` | Task 15 pins "only the Terraform address moves; `name` unchanged" |
| P2-2 A mid-save disconnect lets a reload/retry/deep-link turn's context read race the pending save | §2.4 + Task 5: the route awaits (bounded) any registry-held save for the same `chat_id` before its context read; test + acceptance reworded |
| P2-3 Most sites fail silently, not by a thrown callback; row 5 is envelope-only; `client.ts` has no mutation producers | Task 3 table gains a failure-mode column; site tests reproduce each row's current mode first; §0 wording corrected; §1b row corrected; `ReviewStep.tsx:284` named as precedent |
| P2-4 The Alertmanager test rewrite must keep the compose-shape guards | Task 12 keeps image/port/mount assertions, extended to the switch variable and second webhook |
| P2-5 Bare `${VAR}` in both configs; one shared `prometheus.yml`; stack path | §2.2 and Task 9 |
| P3 Build-trap mechanism precision; Hub fix needs no renderer edit but must keep the page fallback; Task 6 docblock incl. `refetchType: 'none'`; 18 rules; Grafana smoke network name; `fetchWithAuth` path + line drifts; metric-math caveats + a `promql_criteria` empty/`absent()` probe line; SNS email-bounce blind spot; `archive` constraint + out-of-surface module; `AWS_COMMIT_ID` pass-through | Task 1, Task 2, Task 6, §0, Task 8, Task 3, Task 15, Task 14, Task 4 |
| Ruling consequences: plan-warning noise + POC secrets in state; the first SNS email subscription is created here; SMTP username literal confirmed; the p95 exclusion test is load-bearing under save-before-`final` | Task 14 owner steps (b)(c); Tasks 15/16 (confirmation email); no change; Task 10 acceptance |
| Feasibility note "R12 before R14 closes the Amplify-literal window" (v2 numbering) — v3's renumbering put the literal removal (R19) and the build computation (R20) in separate chunks | §9 order rule: R19's iac merge lands after R20's dashboard merge |

### 10c. Fable scoped re-verify triage (owner's Fable 5 chat, 2026-09-15, reviewed v4; verdict READY AFTER CHANGES)

| Finding | Disposition (v5) |
|---|---|
| P2-A The §2.4 wait: a one-slot-per-chat registry drops a pending save's reference on the disconnect→retry path; a naive timeout wait cancels the save it protects | §2.4 pins multiplicity (a set per chat, never displaced; wait and drain await all) and cancellation safety; Task 5 gains both tests |
| P2-B Task 1's scratch install + two builds + a dev start sit outside every lock class | §1c: scratchpad installs/builds/dev under `dashboard.lock`; docker pulls and `terraform init` named under `compose.lock`; Task 1 step says so |
| P3-1 Pin the wait's bound and expiry behaviour; Task 5 acceptance overclaims | §2.4: save timeout + 2 s; proceed + one WARNING + a span event; acceptance appends the expiry case |
| P3-2 Task 15 acceptance said "survive the rename" though there is no rename | Reworded |
| P3-3 Lock classes don't compose: a full suite touching a test DB must hold both locks | §1c sentence added |
| P3-4 The Fable chat's review lanes must take the same locks | §9 "Shared box" bullet |
| P3-5 The SNS blind-spot note belongs in the iac README, not `aws-profile.md` (lane `awsotel`) | Task 15 bullet |
| P3-6 §1a's R20 line read as if the Amplify literal merges in R20 | Reworded: cross-checks; merges in R19 |

## 11. Review briefs (lane close reviews; Fable verdicts live in the handoff directory)

## 12. Implementation notes / Learnings (per lane, as work lands)

- **L10.0 (session lead, 2026-09-15).** The first attempt found `shift_optimizer_test` missing: the 02:30 Postgres restart
  had come up on a stale bind-mount view serving a fresh empty cluster; the owner restarted it and the real cluster
  returned. The verify then showed the 8 stale memory-item predicates plus two absent declared tables (which block every
  provisioning write phase) and two `tenants` privilege mismatches. The migrate dry-run forced the dev DB's documented
  pre-step (drop the drifted `automation_runs_retry_due_idx_tnt`); then migrate (1,511 statements, snapshot in
  `copilot-mro/.dev_runs/obs10/`), provision (109 policies replaced) and verify ran green. `copilot_mro_test` verified clean.
- **Task 7 (lane `cache`).** Removal's stop condition hit on rich block payloads (p95 390 ms uncached); the task was
  re-planned as D10-5b (a generation-versioned cache key) — no utils change, the cache's benefit kept. The lane-close
  review confirmed it composes with lane `stream`: the save renews the token inside `save_block`, so the stream's pre-read
  wait covers the renewal, and a save that times out and commits late still renews.
- **Task 15 → Task 22 (lanes `iac`, `awsotel`).** §2.1's log-silence form for AutomationWorkerSilent rested on an unchecked
  premise (a live worker logs); the worker is silent when idle. Rather than change the pin, the worker gains a 5-minute
  liveness log (Task 22). Learning: a "silence" alarm needs a proven unconditional emitter on the watched path — check it
  when the alarm is designed, not at apply. Task 22's review then showed the `aws` estate deploys no automation worker at
  all (only the App Runner `api` service, whose embedded scheduler logs as `api`), so the alarm would page permanently
  from the first apply: ruling T22-NOWORKER creates the alarm and its metric filter only when an iac variable declares a
  deployed worker (default off) — R19 fix wave.
- **Review shape (ruling LANECLOSE-SINGLE).** A single-task lane's fresh task review already covers its whole range, so it
  gets no second whole-lane review; the controller triages its deferred minors into at most one fix wave. Multi-lane
  chunks (R19, R20) still get one chunk-level composition review.
- **Lane `stream` close.** The whole-lane review found the sync `/rag` save path still exported exception text (span
  defaults and a `traceback.format_exc()` handler log) and that the store itself logs `str(e)`; both went into the lanes'
  fix waves (`stream` and `cache`, per §1b).

## 13. Future Improvements

- **`SettingsAPI.makeRequest`'s 44 callers return `any`; composite `mutationFn` intermediate reads; `useApiClient()`
  paths; the comments hook's generic transports `apiPost`/`apiPut`/`apiPatch`/`apiDelete` in `lib/api/utils.ts` (Task 3
  scope, exempted at implementation).** Same failure class in a different position. Complete solution: route those replies through the
  same contract parser, starting with composites whose intermediate result feeds a second write.
- **Server-side response models for the untyped write routes.** Declaring them makes FastAPI validate after commit, so a
  drift answers 500 for a landed write. Complete solution: a model with every field optional and extra keys allowed, plus
  a test that value drift still returns 2xx — only worth it once a consumer outside the dashboard needs the schema.
- **In `next dev`, React StrictMode doubles the Hub `document_opened` / `document_closed` rows** (Task 2 moved the
  emit into the preview dialog's effect, which StrictMode mounts twice in dev; the library and viewer paths already
  behaved this way; production builds are unaffected). Live acceptance checks of the one-per-gesture rule must use a
  production build or halve the counts. Complete solution: a StrictMode-idempotent guard in `use-document-view.ts`
  (emit once per enabled id across the dev double-mount).
- **The upload document card emits an opened fact with no close** (pre-existing). Complete solution: the upload preview
  emits its close through the same view hook.
- **The standalone build guard checks only a top-level planted link.** A real `node_modules` holding linked packages
  (`npm link`, `file:` or workspace dependencies) would still plant links deeper, at `.next/standalone/node_modules/<pkg>`,
  which a later `cleanDistDir` could follow. No such dependency exists in the dashboard today. Complete solution: the guard
  also refuses when any planted entry under the standalone `node_modules` is a link resolving outside the build output.
- **BrowserErrorRateHigh is an absolute count.** Complete solution: a per-session ratio or a threshold recalibrated from a
  production baseline once one exists.
- **Per-tenant spend budgets.** TenantDailySpendHigh is one flat number. Complete solution: a budget source (templated
  rules or a budget series) once the owner defines budgets.
- **utils `app_version` (default `0.1.0`) has no readers after Task 18.** A legacy guard still requires the field.
  Complete solution: delete it and list it among the guard's deleted fields, so nothing can wire the fake version back in.
- **The standalone copilot-mro image does not build** (pre-existing: the `flynapse-utils` `../utils` path dependency breaks
  `poetry install` inside the image). Task 19's metadata step cannot be proven there. Complete solution: build utils as a
  wheel into the image context (or publish it) before the copilot-mro install.
- **The api image installs the latest unpinned `flynapse-api` wheel** from an index both `main` and `develop` publish to,
  so an image's version and its stamped SHA can come from different branches. **Being fixed in the R20 fix wave (ruling
  R20-PIN):** the deploy job pins the wheel it just published, and the SHA is stamped only on a pinned install.
- **api's `flynapse-utils` has no version floor.** Complete solution: when api returns from its path dependency to the
  CodeArtifact source, add `flynapse-utils >=` the R20-bumped version, so an api wheel can never resolve a utils without
  `distribution=`.
- **copilot-mro `app/core/__init__.py:10` holds a dead, unnamed `setup_logging` call.** It is unreachable today, but the
  first import of `copilot_mro.app.core` ahead of `main.py` would bootstrap with no distribution. Complete solution: delete
  the call (the package holds nothing else).
- **api `Dockerfile.local` and `compose.local.yaml`** pass no `GIT_SHA` and set no stop grace, and both look unbuildable
  at base (no `flynapse-otel` copy for utils' path dependency; the local bot build lacks the `otel` context). Complete
  solution: add the plumbing when the files are repaired.
- ~~**The shared api venv lacks `opentelemetry-instrumentation-psycopg`**, so two flynapse-otel catalogue tests stay red
  there (an environment gap, not a code defect). Complete solution: add it to the shared env's dev group.~~ **CLOSED
  2026-09-15** (api `3c45dff`): added to api's dev group with `psycopg[binary]` (the instrumentor imports psycopg at
  module scope); flynapse-otel 191/191 in the shared env. The instrumentor lives in flynapse-otel's OWN dev group, which
  a path-dependency consumer never installs — so no re-resolution of api could have added it (see (b) below).
- **Secrets in the POC instance's `user_data`.** Visible to anyone with instance-metadata or state access, and stored in
  state from provider 6.x. Complete solution: the setup script reads them from SSM at boot, so `user_data` carries names
  only. The same owner-scheduled change is the place to move the instances to `user_data_base64` — a real diff on the
  replace-flag attribute pair under 6.x (check open issue #44506 first) — which Task 14 deliberately does not do.
- **Remaining exception-text logs in copilot-mro `chat_management.py`** (pre-existing; outside the save path lane `stream`
  fixed). **PARTLY CLOSED 2026-09-15 (owner ruling FU-SSEFRAME; copilot-mro `3b8652c3` + `070f72c3`):** the stream route's
  SSE `error` frame now carries `STREAM_ERROR_MESSAGE` plus the trace id (`"error": "<constant> Reference: <trace_id>"`,
  `"trace_id"`); the two one-line leftovers below (the `PIPELINE_STUB_ERROR` comment, the stream failure log's body
  `chat_id`) are fixed in the same commit; `docs/reference/integration-contract.md`'s `error` row updated (`c53e2067`).
  Adversarial review (Opus 5): 15 scratch mutants killed, the `except` sees the SERVER span's trace id under the real
  gateway stack. ~~Still open from this bullet: the upload/create/delete/history route logs, the data-view lookup
  traceback (`:862`), the orchestrator crash traceback (`pipeline.py:433-444`)~~ — all three CLOSED by batch 2
  (`a20bd009`/`ab3abbfb`; R22 F-1a). **Still open: `error_code` on `PipelineResult` (ruling R15-NOCODE) — deliberately
  open, re-confirmed at R22 (F-R2 pending the owner): the two unsuccessful-result log sites carry a constant message
  alone because the result contract has no code field.**
  Original record: the image/audio upload routes log `error=str(exc)` and `traceback.format_exc()`; the chat create, delete and
  history routes log full tracebacks (the store re-raises by design, so a Postgres DETAIL reaches them); and the stream
  route SENDS `str(e)` to the client in its SSE `error` frame (`chat_management.py` ~:1727 at `963b7095`). The R15 Fable
  verdict kept that frame here deliberately: it is client-facing contract, so changing what a client receives on a
  stream error is an OWNER design decision (constant user-safe text plus a trace reference is the likely answer). The
  pipeline spans' default exception recording, `/rag`'s `pipeline_result.error` in a log attribute and the HTTP 500
  detail, and the stream route's mirror log sites were fixed in R15's fix round (ruling R15-CARRY, extended by the
  verdict). Today's upload `ValueError`s carry constants or the client's MIME type, never file
  content. The R15 re-review named two more sites of the same class: the data-view ownership lookup logs
  `traceback.format_exc()` on a `psycopg2.Error` (`chat_management.py:862` at `3fd146db`), and the orchestrator logs the
  full traceback of a crashed turn (`agent_shared/pipeline.py:433-444`), whose comment ("the route above logs only the
  message") is stale now that the route logs no message. Two one-line leftovers ride the R15 merge (ruling R15-CARRY):
  the `PIPELINE_STUB_ERROR` comment in `tests/api/chat/test_chat_id_shape_gate.py:112-114` still describes the
  pre-fix echo, and the stream handler's failure log (`:1751`) carries the body-supplied `request.chat_id` rather than
  the resolved id. Complete solution: one sweep to constant messages plus `error_type`, with the exception text only
  in a span event that records the type; and a bounded `error_code` on `PipelineResult` (ruling R15-NOCODE: the two
  unsuccessful-result log sites carry a constant message alone today because the result contract has no code field —
  the orchestrator's own failure log keeps the path diagnosable).
- **CLOSED 2026-09-15 (ruling FU-LOGSHAPE A + FU-HEALTH; utils `c4c6cef`→`289ba71`, copilot-mro `a20bd009`→`2bd36558`):**
  `utils.observability.failure_fields(exc)` (type + frames, never the message; `sqlstate` always, `pg_primary` only for
  SQLSTATE classes 23/25/40/53/54/55/57 — ruling FU-PGPRIMARY, class 22/42/P0/0A primaries quote the input) now feeds
  `postgres_service.py` (8 sites), `chat_management.py` (list/delete/history/data-view/upload logs + the two `exc_info=True`
  no-ops + the sync door), `feedback.py`, `shares.py`, `health.py`, `pipeline.py:433`, the improvement `scheduler.py`;
  health bodies (`health_check.py` every leg, the chat-history mixin, utils' postgres/redis/cache probes, the llama-index
  producer) return status + `error_type`, never driver text. Guards: copilot-mro
  `tests/unit/observability/test_no_exception_text_in_logs.py` (50 shapes / 51 tests at `2bd36558`) and utils
  `test_postgres_service_logs_no_exception_text.py`. Two further utils findings fixed on the way: the loguru human sink had
  `diagnose` on (renders local values AND `os.environ`) → `diagnose=False`; the stdlib→loguru intercept dropped `extra=`
  → now bound, with the JSON line's own keys reserved. Still open from the bullets below: `runner.py`'s persisted
  `str(exc)` summaries (`report.errors`, pinned by `test_improvement_runner.py:196`) — a runner-contract question;
  `llama_index_initialization.py`'s other `format_exc()` sites; ~90 f-string `format_exc()` log bodies across utils'
  `email/embedding/dynamodb/s3/weaviate/cache_service`; configured endpoint URLs on the anonymous health route.
  Original records:
- **Exception-message logs elsewhere in copilot-mro's chat store and health route** (pre-existing, outside lane `cache`'s
  files): `feedback.py:95,127` and `shares.py:91` log `str(e)`, and `health.py:37-38` also RETURNS the exception message in
  the health response body, which can expose connection details to any caller. Complete solution: type-only logs as in
  `blocks.py`/`chats.py`, and a health response that reports a status and a constant reason, with details only in a
  type-recording span event. One layer down, `utils/postgres_service.py:443` logs `error=traceback.format_exc()` on a
  failed statement, which re-exposes the exception text the chat store now keeps out of its own logs (found at the R16
  Fable gate; utils is outside lane `cache` under §1b).
- **CLOSED 2026-09-15 (ruling FU-RAG; copilot-mro `778eede0`):** the sync door captures `save_block`'s bool, records
  `_record_block_save_failure("refused", …)` like the stream door, logs "saved" only on True, and `EnhancedChatResponse`
  gains `persisted: Optional[bool]`; the failure log names the resolved chat id (`resolved_chat_id` bound before the
  `try`). Original record:
- **`/rag` ignores `save_block`'s return value.** A refused save logs "saved" and counts nothing, while the stream door counts
  it. Complete solution: the sync route records the same failure outcome the stream route does.
- **A client that disconnects before the save starts loses the turn** (pre-existing): the pipeline keeps running and
  memory writes land with no block. Complete solution: the route owns the whole turn as a registered task, like the save.
- **A page reload right after a mid-save disconnect can briefly render the chat without the last turn.** Only turn
  context reads wait on pending saves; the next turn's context is still correct. The pending-save registry is also
  per process (recorded at the R15 Fable gate): on App Runner a retry or reload routed to a different instance sees an
  empty registry, so the pre-read wait is a per-instance guarantee, not a cross-instance one. The primary defect
  (`final` before the save) is fixed regardless, since ordering is per request. Complete solution: the history read
  endpoint waits on the chat's pending saves with the same bound.
- **Rolling deploy of the generation-versioned cache.** For up to 300 s after the last mixed-version save, an old
  instance's save does not renew the token and a new instance's save does not delete the legacy `blocks:` key. Complete
  solution (only if deploys ever overlap for long): for one release, new saves and deletes also delete the legacy key.
- **The delete-race output-safety of the tokenless read leans on `_query_chat_blocks`'s `deleted = false` filter**
  (`blocks.py:268`, recorded at the R16 Fable re-verify, wording per `R16-verdict-1.md`). The unit fake applies the
  filter itself, so only a DB-lane twin of the R16 FIX-3a test would pin it in production SQL. The other leg (the
  reader's token SET precedes its snapshot) is pinned by that unit test. A regression of the filter would be loud
  everywhere (deleted chats reappearing in every history read), with the race adding at most a 300 s cached echo.
  Complete solution: the DB-lane twin (a `cache.set` hook that runs `delete_chat` between the ownership read and the
  token SET, then asserts later reads return `([], None)`). Two nits ride this record: the FIX-3a assertion message
  claims more than its hook proves (assert one ownership query inside the hook), and the DB-lane `_get_chat_row` wrapper
  takes only `*args`.
- **A contract failure that lands after the optimizer wizard's Upload step unmounted records no "landed without reply"
  marker** (Task 3). This is the same gap that already loses a successful upload's `scheduleCreated` dispatch when the step
  unmounts mid-request. Complete solution: the upload request's outcome is recorded by the wizard (the draft owner), not
  by the step component.
- **A Redis that accepts connections but never answers** multiplies the history path's cache calls (each up to ~10 s),
  enough to push a committed save past the stream's 20 s bound. Complete solution: a circuit breaker in
  `utils.cache_service`.
- **No CI job runs the otel pytest lane** (copilot-mro `.github/workflows/` has only `rules-validate`, `otelcol-validate`,
  `chat-eval`, `deploy-lambda`, `package`). The always-on structural pins (thresholds, routing tree, secrets-via-file,
  scrape set, route exclusion derivation) run only when someone runs pytest locally; the promtool unit proofs and compose
  smokes are gated behind `OTEL_RULES_CHECK` / `OTEL_COMPOSE_SMOKE` and run at every SDD gate but nowhere automatic.
  Complete solution: an otel-structural pytest job in `rules-validate.yml` (pyyaml + git only; a sibling api checkout
  step for the route-exclusion test, which today skips without one), with the gated proofs behind a manual dispatch.
  **LANDED 2026-09-15** (copilot-mro `99e84464`, owner-approved as a separate workflow): `.github/workflows/otel-tests.yml`
  runs the lane on pull_request/push touching `deployment/**` or the lane, pytest + pyyaml only, the root conftest cut
  off (`--confcutdir=tests/integration/otel -o pythonpath=tests` — it imports `utils` for a DB guard the lane never
  needs); `workflow_dispatch` input `gated=true` runs the docker-backed proofs; the api-sibling test runs only when a
  `WORKSPACE_READ_TOKEN` secret (read access to the private api repo) exists — OWNER STEP if wanted. Clean-venv proof:
  107 passed / 24 gated skips; with `OTEL_RULES_CHECK=1` 120 / 11. First CI run (push of `070f72c3`, run 34982277163):
  SUCCESS in 24 s, 106 passed / 25 skipped — the extra skip is the api-sibling test without the token, as designed.
- **Alert targets through two input paths.** Under ruling T16-ARMED, a local apply reads the targets from an untracked var-file, while the workflows read them from GitHub secrets. Only a tracked arm switch plus fail-closed validations keep the two paths from diverging. Complete solution, if the owner reopens §2.2's "untracked var-file" pin: both paths read the same inputs from SSM.
  - The email list comes from an SSM String parameter, and the Slack parameter name is derived from `var.environment`. The SecureString itself is never read, so the webhook URL never lands in state.
  - The same tracked switch stays, because a data source on a missing parameter errors.
  - The IaC identity would need `ssm:GetParameter`.
- **CLOSED 2026-09-15 (api `bedd4ab`→`73da119`, copilot-mro `fe610ec9`/`0a3a45e4`):** `flynapse_api/shutdown_budget.py`
  holds every awaited step of `_shutdown_event` in order — uvicorn `--timeout-graceful-shutdown` 25 (Dockerfile,
  Dockerfile.local, run.py), scheduler stop 5 + unwind 5, improvement-timer stop 30 + unwind 5 (both post-cancel waits
  now bounded; the timer's in copilot-mro `STOP_UNWIND_SECONDS`), chat-save drain 22, upload drain 8 (new
  `asyncio.wait_for` bound, one warning), telemetry flush 5 (the bounded `flynapse_otel` shutdown, now called as the
  hook's last step — it never was before), slack 3 = **108 s**; `stop_grace_period: 110s` in api `compose.yaml`,
  `compose.local.yaml` and the POC compose, pinned by tests on both sides (copilot-mro's imports the budget, falls back to
  the api compose via `sibling_repo`). By design NOT bounded: exit-time joins of threads the bounded steps abandoned
  (chat-save thread, S3 PUT) on Python 3.11 — may end in SIGKILL after the drains and flush. OWNER: App Runner's stop
  window must be ≥ 110 s (§10). Original record:
- **The api's shutdown has no upper bound.** uvicorn runs without `--timeout-graceful-shutdown`, so it waits for every
  open stream before the lifespan drains start, and the S3-upload drain is unbounded; a stop during a long agent turn can
  still end in SIGKILL even with the 60 s compose grace (R20). Complete solution: a graceful-shutdown timeout on uvicorn
  and a bound on the upload drain, sized together with each orchestrator's stop window.
- **CLOSED** — 60 s at R18, 110 s at `0a3a45e4` (see the shutdown-budget record above). Original record:
- **The POC stack's `api` service keeps Docker's 10 s stop grace** (`copilot-mro/deployment/poc/docker-compose.yml`),
  shorter than the chat-save drain. Complete solution: the same `stop_grace_period` as api's `compose.yaml` (proposed for
  R20's Fable fix round, ruling R20-CARRY).
- **The copilot-mro Lambda image carries no `BUILD_GIT_SHA`** (`Dockerfile.lambda`, `deploy-lambda.yml`); its handler emits no
  telemetry today. Complete solution: pass the SHA when the handler gains telemetry. The copilot-mro image also installs an
  unpinned poetry.
- **`migrate_tenancy_schema.py` puts the owner password in `docker exec -e PGPASSWORD=…` argv**, visible in `ps` (pre-existing).
  Complete solution: pass it through the environment of the `docker` process (`-e PGPASSWORD` with no value).

- **Pre-existing failures and environment gaps surfaced by the R20 post-merge lanes** (none caused by phase 10; recorded so
  nobody re-diagnoses them): (a) copilot-mro `tests/unit/observability/test_bedrock_call_sites_name_a_tenant.py` fails
  2/3 — three direct-Bedrock call sites under `services/improvement/` (`clustering.py:528`, `collect_implicit.py:298`,
  `distiller.py:182`) emit `llm_requests_total` / `llm_tokens_total` with no tenant, and the streaming-synthesis fold
  count is 1 not 2; the test and those sources are untouched since `a24189ee`. Complete solution: bind the tenant at
  those sites (or fold their spend as the served path does) and fix the fold count. (b) flynapse-otel
  `tests/unit/bootstrap/test_instrumentation_catalogue.py` fails 2 in the shared api env because
  `opentelemetry-instrumentation-psycopg` is not installed there (flynapse-otel declares it; the api lock's flynapse-otel
  entry predates it and a metadata-only `poetry lock` did not add it). ~~Complete solution: `poetry lock --regenerate` for
  the path dep's full dependency list, then `poetry install`, on the owner's word (it re-resolves the whole env).~~
  **CORRECTED + CLOSED 2026-09-15:** that diagnosis was wrong — flynapse-otel declares the instrumentor in its DEV group
  (`flynapse-otel/pyproject.toml:42`), which a path-dependency consumer never installs, so `poetry lock --regenerate`
  (run on the owner's word; moved ~150 pins incl. fastapi 0.118→0.141, starlette 0.48→1.6, redis 6→8, uvicorn 0.37→0.53)
  still did not add it. The regenerated lock was NOT installed or committed (the phase-10 gates verified the env at those
  older pins; phase-8 D-6 reasoned from Starlette 0.48); the committed lock was restored and the fix landed as the dev-group
  addition above (api `3c45dff`). A full re-resolution of the shared env is a separate owner decision with its own lane run.
  (c) api `compose.yaml`'s `SMTP_USER` default carries a "fkynapse" typo (Fable R20 reviewer; pre-existing). (d) The
  copilot-mro `tests/smoke/document_hub` package-import failure (`reindex.py:82` imports the vector index at module
  scope), failing identically since before the phase.
- **RLS preflight handshake vs SSL-required servers** (lane `rls`, Task 21 round 2, record): the runner classifies a
  refused connection by a plaintext protocol-3.0 startup handshake reading the SQLSTATE structurally. A `hostssl`-only
  `pg_hba` answers 28000 to that plaintext attempt for every role, so on an SSL-required server a missing database gets
  the credentials remedy. The workspace's compose Postgres does not require SSL. Complete solution: send an SSLRequest
  first and wrap the socket in TLS on `S` before the StartupMessage.

- **Alerting lane leftovers (R18 fix round 1 re-review, ruling R18-CARRY-2):** the export-side pin in
  `tests/integration/otel/test_alert_environment_routing.py` reads `resource_to_telemetry_conversion` on the one named
  exporter (`prometheusremotewrite/prom`); a second `prometheusremotewrite/*` sink wired into the oss metrics pipeline
  with conversion on would not be caught. Complete solution: iterate every remote-write exporter, or additionally pin
  the oss `service.pipelines.metrics.exporters` list. Also: `oss-profile.md` step 2 (the silent `*_FILE` directory trap)
  lacks the `rmdir` recovery clause step 3 carries; and the guard's comment calls the `without` keyword
  case-insensitive "in both languages" — certain for PromQL, unverified for LogQL (an uppercase keyword there is a ruler
  parse error the gated check rejects, so the over-inclusive guard costs nothing).
- **Post-phase follow-ups landed 2026-09-15 (owner rulings taken in chat; records in the SDD ledger "Post-phase owner
  follow-ups"):** FU-GUARD — `shift_optimizer` joins shift-optimizer's guard list for every test kind (shift-optimizer
  `3660fb0`, `9fa4d3f`, `d01f6ca`, `5ee3f45`; adversarial review + two re-reviews, APPROVE); FU-SSEFRAME (above);
  FU-SSM — keep the two alert-target input paths; FU-SENDAS — `contact@flynapse.ai` is a configured send-as alias, the
  From stays; FU-MOVED — retiring the SNS `moved` blocks deferred to the first apply; FU-OTELCI — `otel-tests.yml`
  (above). Leftovers those reviews recorded, none blocking:
  - The shared refusal text in `utils/utils/db_guard.py::assert_not_protected_database` is copilot-mro-worded ("only copy
    of a real parsed and embedded corpus", suggests `copilot_mro_test`) even when the refused name is `shift_optimizer`.
    Complete solution: the helper takes the caller's `test_database` and names the protected database neutrally.
  - `shift-optimizer/tests/db/tenancy/test_repository_tenancy.py:132` opens one owner connection to `POSTGRES_TEST_DB`
    at collection, even under `--collect-only` (pre-existing). Complete solution: defer `_db_available()` to a fixture.
  - ~~The sync `/rag` door's failure log (`chat_management.py:1352`) carries the body's `chat_id` (None on a fresh chat)
    like the stream door did; NOT changed because the resolved `chat_id` local is first bound inside the `try` (`:1117`),
    so the one-token fix risks an `UnboundLocalError` when the failure precedes it. Complete solution: bind a
    `resolved_chat_id = None` before the `try` and log that.~~ DONE in batch 2 (`778eede0`, ruling FU-RAG-4; R22 F-1b).
  - Stream frame edge cases: (a) the standalone copilot-mro image serves the app with no `OpenTelemetryMiddleware`, so a
    failing turn's frame says `trace_id: null` while the pipeline spans carry a root of their own — not a served
    deployment today; (b) in the unsuccessful-result mode (`success=False`, no exception inside the pipeline) the
    referenced trace has a 200 SERVER span and UNSET pipeline spans, so the reference leads to a trace with no failure
    marker. Complete solution for (b): the route marks its own span ERROR with `error.type` before sending the frame.
  - `otel-tests.yml`: the `gated: true` dispatch path (compose smokes on the hosted runner) is unproven until someone
    dispatches it; `WORKSPACE_READ_TOKEN` (a fine-grained read token for `flynapse/api`) is an optional OWNER secret
    that lets the route-exclusion pin run on dispatch.
- **The chat routes still log the user's question** (`chat_management.py:1080` and `:1433` at `2bd36558`, `query=request.message` on the
  "Enhanced chat request received" lines; surfaced again by the SSE-frame review). This is the master plan's phase-0
  item 0.5 (with 0.6, the `/metrics` route) — the app half of Stream L, which waits on Task R and the owner's go and has
  NOT started. The master plan recommends 0.5 as an immediate hotfix: replace `query=` with `query_chars=len(...)` at
  both sites plus the two memory-search log calls in `memory_index.py`, pinned by an AST test
  (`tests/unit/observability/test_no_user_content_in_logs.py`).

- **FU-LOGSHAPE A scope (R22 F-2, provisional controller ruling pending the owner's B-R2/F-R1): a SWEPT-FILES fix, not
  yet a codebase policy.** Swept: utils `postgres_service.py` (+ the health probes, `cache_service.get_cache_stats`);
  copilot-mro `chat_management.py`, `user_feedback.py` (R22 B-1), `feedback.py`, `shares.py`, `health.py`,
  `health_check.py`, `llama_index_initialization.py` (health producer only), `agent_shared/pipeline.py:433`, improvement
  `scheduler.py`; api `main.py` shutdown hook (R22 fix 3). **Residual, counted at R22 and deferred:** copilot-mro ~187
  `format_exc` lines / 21 `exc_info=True` sites (14 files) / ~169 f-string `{e}` log bodies — incl. the served-turn family
  `agent_shared/lifecycle.py` (11 bare `logger.exception`), `_topic.py:89`, `_query_type.py:131`, `subagent_runs.py:155,203`
  (R22 B-2) and `runner.py`'s persisted `str(exc)` summaries; api (post-`44bd8d1` census, overlapping patterns, some
  `str(e)` are HTTP bodies): 15 `format_exc` (main.py 12 — incl. two inside `_shutdown_event` itself at `:221/:233`,
  routers/health.py 1, middleware/logging.py 1, middleware/auth.py 1) / 1 `logger.exception` / 51 `opt(exception=True)`
  (automations loop 29, executor 16, …) / 31 `str(e)` / 19 `str(exc)` / 73 f-string `{e}`; utils ~90
  (`email/embedding/dynamodb/s3/weaviate/cache_service`). Two ways to close the residual (owner ruling B-R1): a one-line
  sink-level rule in `log_bridge._json_stdout_sink` rendering frames-only + `error_type` for every record carrying an
  exception (closes everything wholesale, loses the message estate-wide), or a named sweep follow-up per family.
- **FU-SECRETSDIR (R22 F-5):** the three Alertmanager delivery secrets (two Slack webhook URLs, the SMTP password) live in
  the checkout at `copilot-mro/deployment/observability-local/alertmanager/secrets/` — ignored by the root `.gitignore`
  AND the directory's own (`test_alertmanager_secrets_dir.py` proves each rule alone), placeholder-lined files created
  for the owner, runbook `oss-profile.md` rewritten with per-stack relative `*_FILE` prefixes; `/etc/flynapse/alertmanager/`
  stays the shared-box alternative. §10's "write the three secret files" owner step means THIS location.
- **User content in log attributes — the pile (R22 B-5):** besides `query=request.message` on both chat doors (Stream L /
  phase-0 0.5), the feedback/share routes log `email=request.email` (`user_feedback.py:594,661` plus four further email
  attributes at `:494,:578,:591,:648`), the chat-history `shares.py` store mixin logs `"email": email` at three calls
  (`:35,:78,:91`), and `user_feedback.py:548` logs the chat title — the user's truncated first message — as
  `title=chat_title`; same ruling, same sweep.
- **api → `mro-copilot` version floor (R22 D-1/D-R2, provisional ruling: keep the runtime import + merge order):**
  `flynapse_api/shutdown_budget.py` imports `STOP_UNWIND_SECONDS` (and `STOP_GRACE_SECONDS`) from
  `copilot_mro.app.services.improvement.scheduler` at module scope, so an api at `73da119`+ against a copilot-mro
  predating `fe610ec9` fails at import (crash-loop, no fallback). Harmless under the path dependency (`develop=true`, one
  tree) and under the merge order utils → copilot-mro → api; the residual is the CodeArtifact spec variant
  (`api/pyproject.toml:45`, `mro-copilot ^0.2.0`), which has no floor. Complete solution when that spec is active: raise
  the floor to the first copilot-mro version carrying `STOP_UNWIND_SECONDS` — or carry the two timer terms as literals
  with a pin test, the budget's existing pattern for the automations loop.

## 14. Lessons
_(plan-scoped; append after any owner correction: what was tried, what was corrected, the rule for next time)_
