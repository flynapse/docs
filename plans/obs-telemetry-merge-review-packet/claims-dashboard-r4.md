# Claims packet: dashboard r4 (the review r3 fix batch) — FINAL

Independent adversarial review (Opus), 2026-09-22, read-only throughout. **Complete: every check ran, every claim row has a
state, and the mutation ledger has no pending entry.**

> **Two pauses, one packet.** The first reviewer was killed; a second (this one) resumed from the durable notes, spot-checked
> the settled rows against the sources again — the three P2-1 sentences at core `7d5144c`, the table-column census, `M21`,
> the contract fixture, F5/F6, and the range's own diffstat against `claims-dashboard-r3.md` — and **confirmed every one**,
> was paused in turn (owner cut the agent cap to 1), and finished on resume. Nothing was weakened along the way; P3-4
> gained a second half and the ledger gained its last two full-lane confirmations. Working notes and recipe:
> `~/.claude/scratch/obs-merge/dash-review-r4/` (`NOTES.md`, `PAUSED.md`, `mutants/`, `mutants.log`, `logs/`).
> No real tree was ever edited, checked out, committed or pushed; the scratch copy ends content-clean at `f8c4614`.
>
> **Core moved three times under this review** — `16cd1ae` (the commit the batch read) → `8d0df97` (r9) → `b540596` →
> `19403fa` (HEAD as this closed). Each delta was measured, not assumed: `8d0df97` genuinely changed
> `top_cited_documents` (that is P3-2), and after it `git diff --stat 8d0df97 b540596` and
> `git diff --stat b540596 19403fa` over `core/resources/analytics` + `core/services/analytics` are both **EMPTY**
> (`b540596..19403fa` is one file, `docs/plans/g61-comments-survive-tenant-delete.md`). So every core-dependent row below
> reads the same at core HEAD as it does here.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `4a7714a..f8c4614` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | 16: `e79e987` P2-1 · `a7fdc5f` P3-7 · `69a5bb2` P3-1 · `cdb9f89` P3-5 · `ce3548f` P3-4 · `562bb5c` M21 · `4044656` P3-6 · `469f8e9` P3-2 · `dddf887` P3-3 · `a7a9a4d` F4 · `3c2b34e` F3 · `e4e0a8f` F1 · `f7947f4` F2 · `c7a3310` F6 · `433b135` F5 · `f8c4614` plan (docs only over `433b135`) |

Copies (durable, `~/.claude/scratch/obs-merge/dash-review-r4/`): `dashboard-obsm` = `git archive f8c4614` (`node_modules`
symlinked from `dashboard/node_modules`, never installed) beside `core-obsm` = `git archive core-obsm 16cd1ae` and `api-obsm` =
`git archive api-obsm fbd394c -- flynapse_api/automations`, so every `siblingName` read resolves inside the scratch dir. core
`8d0df97` (core-obsm HEAD by the end of this review) was archived separately and swapped in under the sibling name for one
run. No real tree was edited, checked out or committed; `dashboard-obsm` is clean at `f8c4614`. No `next build`, no browser,
no live stack. Notes `NOTES.md`, mutant texts `mutants/`, ledger `mutants.log`, every log `logs/`.

## How it was run

node `--test` via tsx, `--test-concurrency=2`, every run through `/home/aditya/Code/pytest-slot.sh`, one runner at a time,
own exit status captured; exit 1 was read against the log for the aimed `✖` (a load crash also exits 1).

| check | commit | result | exit |
|---|---|---|---|
| full unit `tests/unit/**/*.test.ts?(x)` (core sibling only) | `f8c4614` | 2676 / 2675 pass / 1 fail — the one red is `runErrorVocabulary` "the snapshot matches the backend", `$captured_from` `[core]` ≠ `[api, core]`: LAYOUT (api sibling absent), not code | 1 |
| the automation vocabulary files, api + core siblings beside | `f8c4614` | 15 / 15 | 0 |
| analytics lane `tests/unit/analytics/*.test.ts?(x)` | `f8c4614` | 77 / 77; the core-contract test RAN (not skipped) | 0 |
| core-contract test, core sibling moved away | `f8c4614` | FAILS: "…is not checked out beside this repo…" | 1 |
| same, `GITHUB_ACTIONS=true` | `f8c4614` | SKIPPED, same message + "(GitHub Actions checks out this repo alone.)" | 0 |
| same, `GITHUB_ACTIONS=1` | `f8c4614` | FAILS (only the exact string `true` skips) | 1 |
| same, an EMPTY `core-obsm` dir | `f8c4614` | FAILS: "…checked out, but on a branch without the module…" | 1 |
| core-contract test against core `8d0df97` | `f8c4614` | 3 / 3 (outcomes SQL and sentinel unchanged since `16cd1ae`) | 0 |
| survivors lane A (D1 + D6 + C-rewire + C-aggrename, all applied) | `f8c4614` | 2668 / 2667 / 1 fail — a FILE-level runner IPC error ("Unable to deserialize cloned data") in `tenancy/operator-write-mutations.test.tsx`, which re-run alone WITH the mutants applied is 19 / 19, exit 0 → all four survive the full lane | 1 / 0 |
| survivors lane B (D6c + M12b, both applied) | `f8c4614` | 2676 / 2676 pass / 0 fail, 680 s — no `✖` and no IPC flake → **both survive the full lane** | 0 |
| `tsc --noEmit` | `f8c4614` | clean — not one diagnostic | 0 |
| `next lint --file` on the 20 touched source files | `f8c4614` | "✔ No ESLint warnings or errors" | 0 |

CI shape (read): `.github/workflows/quality.yml` runs `npm run test:unit` on GitHub (so `GITHUB_ACTIONS=true`); `amplify.yml`
and the `Dockerfile` run no tests. So the core-contract test is a developer-workspace gate and a loud skip in CI — as ruled.

## Mutation ledger — 34: 27 KILLED, 7 SURVIVED (**all seven confirmed on the FULL lane**), 0 BROKE

Each through `mutant.sh` (baseline green, restored, md5-checked) or, for the full lanes, applied together and reverted
(`git archive … | tar -d` content-clean afterwards for dashboard and core).

| id | where | mutant | result | what went red |
|---|---|---|---|---|
| C-add | core `quality.py` | a seventh `AS partial` column | **KILLED** | contract test |
| C-rename | core | `AS not_answered` → `AS unanswered` | **KILLED** | contract test |
| C-reorder | core | `unsure` / `not_answered` swapped | **KILLED** | contract test |
| C-sentinel | core | `DELETED_USER_ID = "deleted_user"` | **KILLED** | contract test |
| C-annot | core | `DELETED_USER_ID: str = "deleted-user"` (same value, annotated) | **KILLED** — a loud false red (the reader's regex) | contract test |
| C-rewire | core | the panel registered to a NEW builder that adds `AS partial`; `_outcomes_sql` untouched | **SURVIVED (full lane)** | — |
| C-aggrename | core | `_outcome_rows` serves `failed` as `errored` | **SURVIVED (full lane)** | — |
| M19 (impl) | registry | Failed sentence inverted | **KILLED** | sentence pin |
| D1 | registry | "Failed turns are left out of every outcome." ADDED after the unchanged sentences | **SURVIVED (full lane)** — the declared limit | — |
| M21 (impl) | utils | builder throws on a missing key | **KILLED** | missing-key test |
| M12 (impl) | page | all series on narrow screens up to 6 | **KILLED** | narrow-screen Answer Outcomes |
| M12b | page | threshold `<= 3` → `<= 4` | **SURVIVED (full lane)** — the 4-series panel nobody pins | — |
| M14 (impl) | ChartCard | colour by reversed position | **KILLED** | series-colour test |
| P34-sentinel (impl) | builders | sentinel line deleted | **KILLED** | user-column test |
| D5 | builders | demo check moved before the sentinel check | **KILLED** | user-column test (demo on) |
| P32-seventh-series (impl) | registry | a seventh series | **KILLED** | contract test |
| F5-silent (impl) | PermissionContext | refusal → silent `return` | **KILLED** | both refusal tests |
| D6 | PermissionContext | refused-load catch no longer clears `capabilitiesByDepartment` | **SURVIVED (full lane)** | — |
| D6c | PermissionContext | refused-load catch no longer clears `departmentPermissions` | **SURVIVED (full lane)** | — |
| R3M-mts (impl) | `scripts/*.mts` | `/test-cookie` planted in an `.mts` | **KILLED** | `/test-cookie` scan |
| D20 | scan | `mts` dropped from the extension list | **KILLED** | the scan's reach check |
| F6-register-unkeyed (impl) | RegisterView | key removed | **KILLED** | 3 paste tests |
| F6-invite-unkeyed (impl) | InviteAcceptView | key removed | **KILLED** | 3 paste tests |
| R3M-hashraw (impl) | useHeldInviteToken | paste stripped by raw `replaceState` | **KILLED** | paste test's router assertion (+ the 3 F6 tests) |
| R3M-funnel-every-run (impl) | useInvitationPreview | per-attempt dedupe removed | **KILLED** | both Strict Mode tests |
| R3M-internal-reworded (impl) | runOutcomeCopy | cleared `internal` sentence gains "use Run now" | **KILLED** | cleared-text test |

The implementer's other seven (P21 ×3, P37, P35, P34-usercol, R3M-hashraw's sibling set) were not re-run; the 13 sampled all
reproduce its ledger.

---

## Findings, ranked

**Verdict: MERGE-CLEAN — P0 0 / P1 0 / P2 0 / P3 7.** Every r3 finding is closed in code, each r3 survivor is now
killed, and the rulings are implemented as ruled. The P3s are guard shape (three), copy that lags a core that moved after the
brief (two), one pre-existing demo-mode gap the batch's own note mis-describes, and process.

### P3-1 (tier 2): F5's refusal pin cannot see half of what it claims — D6 survives the full lane

- **Where:** `permissions-endpoint.test.tsx` probe prints `tenant | roles | hasCapabilityInDepartment('chat.use','dept-mro') |
  loading` and the error. `hasCapabilityInDepartment` needs BOTH the membership row and the capability, so either field left
  stale on its own still reads `false`.
- **Seam it misses:** `routeAccess.hasRouteAccess` admits a capability-only route through `hasCapability(requiredPermission)`,
  which reads `capabilitiesByDepartment` directly (`resolveCapability`); `computeSettingsPermissions` does the same.
- **Failure scenario:** a later edit drops `setCapabilitiesByDepartment({})` from the load's `catch` (D6). A refresh whose body
  is refused then keeps the last load's capabilities: `/settings/department/roles/add` (`ROLES_MODIFY`), `team/add`
  (`USERS_MODIFY`), `tenant/add-department` (`MANAGE_DEPARTMENTS`) and `mro/document-hub` stay open on a snapshot the
  server just failed to vouch for — exactly what F5 exists to prevent — and the whole lane stays green. (The code today is
  right; the server enforces regardless.) D6c (membership kept) is the same blind spot and **also passes the whole 2676-test
  lane**; alone it opens no route (every route that names departments also names a capability), only the stale membership
  list — so the probe is blind to BOTH single-field regressions, not just one.
- **Fix:** add `hasCapability('chat.use')` and `departmentPermissions.length` to the probe, asserted in both refusal tests.

### P3-2: Most Cited Documents' copy is false against core HEAD — core moved after the brief

- core `8d0df97` (r9 `62c2d59`, `398b19a`, both after the `16cd1ae` this batch read) keys a uid-less citation on its KIND and
  title, so deleted chats' id-less citations are **one row per kind**, each with no id and no label. `formatDocumentLabel`
  reads every one of them as "Unknown" (it ignores `document_kind`), so the chart can show several "Unknown" bars while the
  copy says they "share a single row labelled Unknown". Pinned only against a 16cd1ae-shaped row
  (`analytics-panel-registry.test.ts`, the drawn-rows test); no cross-repo pin covers this panel.
- Also true at `16cd1ae` and still at `8d0df97`: the lump is not deleted chats only. copilot-mro keeps a citation unless ALL
  of `doc_uid`/`document`/`manual_type` are None (`chat_turn_facts.py:476-477`), so a LIVE `manual_type`-only citation lands in
  the same row.
- **Fix (dashboard):** say "…share one row per manual type, labelled Unknown" (or label such a row by its kind, e.g. "Unknown
  AMM document") and re-draw the test's rows from core's current statement.

### P3-3: The core-contract pin reads `_outcomes_sql` by NAME, and its SELECT only (C-rewire, C-aggrename survive)

- `tests/fixtures/analytics/core-quality-panels.ts` finds `^def _outcomes_sql(` and parses its string literals. It never
  checks that `_outcomes_sql` is the `sql_builder` registered for `answer_outcomes_over_time`, and never reads the aggregator,
  which can add or rename keys (`_outcome_rows` rewrites `avg_confidence` and seeds every key today). The fixture's own
  docstring says it compares the registry "with what core actually serves"; it compares with one function's SELECT.
- **Failure scenario:** core points the panel at a new builder (or renames a key in `_outcome_rows`) and leaves the old function
  in place: the contract test stays green and the dashboard draws Failed flat at 0 — the exact flat-line case P3-2 was built to
  catch.
- **Fix:** locate the `register(PanelSpec(panel_id="answer_outcomes_over_time", …))` block, read its `sql_builder=` and
  `aggregator=` names, parse THAT builder, and require the aggregator's seed-dict keys to equal the SELECT's columns (minus
  `bucket_start`) — a throw when any of these cannot be read, as the fixture already does.

### P3-4: Top Spenders names real people in demo mode — and the P3-4 note says no such place exists

- Pre-existing, out of range. `spend_by_user` is a `categories` panel: `buildCategoriesChart`/`buildCategoriesColumns` render
  core's `label` (`users.name` or `email`, `cost.py` `_spend_by_user_rows`) as-is, and `ChartCard`'s demo pass
  (`anonymizeMessageContent`) rewrites tails, stations and client names, not people. So in demo mode the Cost tab shows real
  names while every Quality/Usage per-user surface is pseudonymised.
- The P3-4 commit and plan note ("anonymised in demo mode like every other place the page names a user"; "the page's one
  user-naming helper") are false: `buildTopUsersChart`/`buildTopUsersColumns` call `anonymizeUserLabel` directly and Top
  Spenders anonymises nothing. The `deleted-user` sentinel cannot reach Top Spenders today (`llm_usage` is not anonymised on
  delete — the M-FACTS-ANONYMISE open owner question), so P3-4's own scope is right.
- **Fix:** give `spend_by_user` a user-labelled category (route its label through `formatUserLabel(user_id, label)`), with a
  demo-mode case; correct the note.

**Second half (found on the resume): demo mode anonymises the User column of the two Quality tables and nothing else in them.**
`AnalyticsPanelSection.tsx` and `app/(dashboard)/settings/department/dashboard/page.tsx` carry no `demo` / `anonymiz`
reference at all — the analytics page has no content-level demo pass. `anonymizeMessageContent` (tails, stations, client
names) is `ChartCard`'s, over a CHART's title, axes, series and points; a `variant: 'table'` panel is drawn by
`buildTableColumns` → `renderCell`, which never reaches it. So in demo mode Negative Feedback and Unanswered Questions show
`user_id` as "User 4821" and, beside it, `question_excerpt`, `comment` and `department` **verbatim** — real operator
questions, which in this product carry tail numbers, station codes and work-order ids, i.e. exactly what
`anonymizeMessageContent` exists to scrub two components away. Pre-existing (both columns predate this batch; only
`user: true` is new), out of range, and the same root as Top Spenders: user-label anonymisation exists on this page,
content anonymisation does not. **Fix:** route a table panel's cells through the demo pass (a `content: true` column kind
beside `user`/`money`), or say in the panel's copy that demo mode does not scrub question text.

Also noted, ordering inside `renderCell` (`analytics-panel-builders.tsx:282-289`): `typeof value === 'number'` is answered
BEFORE `column.user`, so a user column whose value arrived as a number would render through `formatCount`, never
`formatUserLabel`. Unreachable today (core answers `user_id` as text, and the sentinel is a string), but the `user` branch
is the one the sentinel and the demo pseudonym both live behind, and nothing pins that it is reached for a non-string.

### P3-5: The history caveat and one deploy step are missing

- Core's turn-latency note says "history before the settle writer is saved turns only"; the new histogram and turn-latency
  sentences state the every-settled-turn rule for the whole range, so p50 stepping DOWN at the settle writer's deploy reads as
  a speed-up. Answer Outcomes carries the caveat (its table description); these two do not.
- The plan's "Deploy order … In full" lists provisioning → core → dashboard but not copilot-mro's settle writer
  (`d4792d6b`): until it runs, Failed is 0 and the outage sentences describe nothing. The outcomes history caveat covers that
  window; the latency/histogram copy does not.

### P3-6: The narrow-screen pin brackets the threshold between 3 and 6 only — M12b survives the full lane

- The page test holds a 6-series panel to "first only" and a 3-series panel to "all". A threshold moved to 4 or 5 (M12b,
  `page.tsx:236`) changes Automation Runs Over Time (4 series) on narrow screens and nothing reads it: **M12b passes the
  whole 2676-test lane**. Add the 4-series panel as a third case.

### P3-7: Process

- **Reviewer-copy advice reddens another guard.** The plan tells a reviewer to link core beside a scratch copy; with core but
  not api beside it, `runErrorVocabulary` "snapshot matches the backend" goes red (`$captured_from` differs) — this review's
  baseline did exactly that. Say "link core AND api".
- **Merge order in the primary checkouts.** Primary `core` (`e10a9ce`) has no `DELETED_USER_ID` and no `failed` column, so the
  moment `obs-merge` lands in primary `dashboard` before core's lands in primary `core`, the dashboard unit lane is red there
  (by design, but unrecorded): merge core first.
- **Workspace plan rows are stale.** G.32 and G.34 still read r3's "FIX-FIRST on P2-1" / "PARTIAL"; M-INVITE-FRAGMENT stops at
  "review r2 P3s closed `2a9b0f4`"; M-PERMISSIONS-ENDPOINT at `e3a4610`. None records the r3 batch (controller-owned).

---

## What I tried to break and could not

- **The three P2-1 sentences against core's SQL** at `7d5144c`, `16cd1ae` and `8d0df97` (histogram, reliability and operations
  statements unchanged across all three): histogram = every row with `latency_ms IS NOT NULL` ("where it was timed");
  latency percentiles ignore NULLs while `turns = count(*)` (hence "timed"); tool usage expands `tool_usage`, which a
  placeholder lacks ("saved turns only"). All three TRUE, each pinned whole (`assert.equal`).
- **P3-7's Unknown sentence** matches core's catch-all (`answer_found IS NULL OR <> ALL(vocabulary)`).
- **The sentence pin.** Any edit inside a pinned sentence fails (M19 red); the one declared hole — a contradicting sentence
  ADDED beside unchanged ones — is real and exactly as declared (D1 survives the full lane). Over-constraint is by design and
  stated.
- **The contract reader.** Every shape it cannot read is a throw (docstring first, single-quoted or f-string items, a
  column-0 comment in the body, a missing alias, an annotated sentinel) — loud, never a partial list. Absence FAILS locally and
  SKIPS only under `GITHUB_ACTIONS=true`, exactly as ruled; nothing on this box sets it (only `act` would, which also checks out
  one repo).
- **User ids.** All eight `table` panels declare columns (no inferred `user_id` column); the only two with a user column
  declare `user: true`; top-users panels read live `chat_blocks` (no sentinel) and pseudonymise via `anonymizeUserLabel`; the
  drilldown joins live blocks INNER; there is no CSV/export or tooltip path for these tables. Demo mode anonymises real ids in
  both Quality tables (ruling 2) and the sentinel reads "Deleted chat" in demo mode too.
- **F5's code.** A refused body throws into the transport-failure `catch`: error set to a constant (no body content), all three
  fields cleared, `finally` ends loading — on first load and on refresh (via `refreshPermissions`, which drops both caches
  first; in production the refresh is the load effect re-running after the 60 s TTL). No consumer reads `error` (declared FI);
  `requiredIdentityOutcome` still redirects a tenant-less first load after 15 s as it did.
- **F6.** `/invite` and `/register` each key their per-invitation child by the held token; either key removed turns three paste
  tests red. A paste during confirmation returns to the form (ruling 3: typed fields reset, the first invitation's unconfirmed
  Cognito account left behind). The declared residue is accurate: an accept for A that succeeds after B is pasted runs
  `placementNext` from the unmounted page (hook-level `onSuccess`) and forgets B's hold; the page on screen keeps B.
- **F1–F4.** Every r3 survivor is now killed (R3M-hashraw, R3M-funnel-every-run, R3M-internal-reworded, R3M-mts), plus D20 on the
  scan's reach check; F2's test compares exactly what `materializeDetail` renders (`runOutcomeCopy({reason: null, error},
  {runsOnSchedule: false})`), and the implementer's AD lie probe logs match its declared limit.
- **CI-only skips.** The core-contract test is the only new test that depends on a sibling; every other new test (DOM, Amplify
  over `fetch`, Strict Mode) is self-contained.
- **The sentinel half of the contract pin, attacked the way P3-3 attacks the SELECT half** (resume): core does not merely
  DECLARE `DELETED_USER_ID` — `quality.py:63` defines it and `:443` passes that same constant as the statement's parameter,
  so the constant cannot drift from the SQL that uses it while the pin reads green. The `_outcomes_sql` half has no such
  tie (P3-3 stands): there the pin reads a function by NAME that nothing proves is the registered builder.
- **The range's own scope.** `git diff --stat 4a7714a..f8c4614` is 21 files, exactly one of them the plan `.md`; every r3 row
  marked OPEN or PARTIAL in `claims-dashboard-r3.md` is answered by a commit in the range except `DR3-13` (the
  `JSON.stringify`'d message-less list element) and `DR3-2a-18` (`history.state`), which r3 itself recorded as future
  improvements rather than as the 14 FIX-FIRST items. Nothing was quietly dropped and nothing extra rode along.

## What I did not test

- Any browser or Next runtime (narrow screens, the paste flows, the Amplify activation) — source-read and the repo's DOM harness.
- The implementer's seven un-sampled mutants; core's and copilot-mro's own lanes.
- Whether the server's activation self-heal accepts a token B against a user row a token-A POST created (the "account exists"
  recovery for two invitations to one address) — that is the pre-existing recovery path ruling 3 accepts; `/register`'s
  confirmation view no longer carries a pasted token.

---

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process (a functional
regression takes the nearest slot, marked). **Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but
reversible; 2 = irreversible or estate-shaping (RBAC). **Chunk:** F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR4-01 | dashboard / core | `analytics-panel-registry.ts:289-290`, `:632-633`, `:762-763` | Histogram, turn latency, tool usage say which turns they count | r3 P2-1 | read against core SQL at `7d5144c`, `16cd1ae`, `8d0df97` | `analytics-panel-registry.test.ts` (whole-description `assert.equal`) | yes (impl P21 ×3) | 2 | 0 | F1 | **SETTLED** (closes DR3-04) |
| DR4-02 | dashboard / core | same | The latency/histogram copy carries no history caveat | (omission) | core `reliability.py` turn-latency note | none | n/a | 3 | 1 | F3 | **OPEN.** P3-5 |
| DR4-03 | dashboard / core | `:306` | Unknown = catch-all incl. an unrecognised verdict | r3 P3-7 | core `b2d67f2` statement | sentence pin | yes (impl P37) | 3 | 0 | F1 | **SETTLED** (closes DR3-18) |
| DR4-04 | dashboard | `analytics-panel-registry.test.ts` `COUNTING_SENTENCES` | Whole sentences, verbatim, per changed panel | r3 P3-1 | M19 red; D1 survives full lane = the declared limit | same | yes; limit confirmed | 1 | 0 | F1 | **SETTLED** (closes DR3-03; declaration honest) |
| DR4-05 | dashboard / core | `:428`; `chat-quality-panel-utils.tsx:109-121` | Id-less deleted citations "share a single row labelled Unknown" | r3 P3-5, read at core `16cd1ae` | core `8d0df97` groups them per kind → several "Unknown" rows; live `manual_type`-only citations join the lump at both commits | drawn-rows test (16cd1ae-shaped) | n/a | 3 | 1 | F3 | **OPEN.** P3-2 (DR3-10 closed at `16cd1ae`, re-opened by core r9) |
| DR4-06 | dashboard | `analytics-panel-builders.tsx:282-289`, `:334-356`; registry `:376`, `:411` | User cells through `formatUserLabel`; sentinel → "Deleted chat" first, demo too | r3 P3-4 + ruling 2 | census: 8 table panels, 2 user columns; no export path | builders + registry tests | yes: P34-sentinel, D5 (+ impl P34-usercol) | 1 | 0 | F1 | **SETTLED** (closes DR3-09) |
| DR4-07 | dashboard | registry `:500-514`; `analytics-panel-builders.tsx:55-100` | Top Spenders labels are core's names/emails, unanonymised | pre-existing | demo pass does not touch people; plan note claims otherwise | none | n/a | 3 (functional: demo mode) | 1 | F3 | **OPEN.** P3-4 |
| DR4-08 | dashboard | `chat-quality-panel-utils.tsx:82-85` | A missing key draws 0, never throws | r3 M21 | pre-M-FACTS-FAILURES bucket through the real builder | registry test | yes: M21 | 1 | 0 | F2 | **SETTLED** |
| DR4-09 | dashboard | `ChartCard.tsx:32-45`, `:522`; `page.tsx:236` | Colour by position; narrow screen "all when ≤ 3, else first" | r3 P3-6 | legend swatch = line stroke source (`seriesMeta`) | series-colour test; page narrow-screen tests | yes: M14, M12 killed; **M12b survives the full lane** | 1 | 0 | F2 | **SETTLED** for M12/M14; **OPEN** for thresholds 4–5 (P3-6) |
| DR4-10 | dashboard / core | `core-quality-panels.ts`; contract test | Absence FAILS; `GITHUB_ACTIONS=true` SKIPS; any unreadable shape throws | r3 P3-2 + ruling 1 | absence matrix above; C-add/rename/reorder/sentinel/annot red | contract test | yes: 5 core mutants + P32 ×2 | 1 | 0 | F1 | **SETTLED** (closes DR3-08's rename/add half) |
| DR4-11 | dashboard / core | same | The pin reads `_outcomes_sql` by name and its SELECT only | — | C-rewire, C-aggrename survive the full lane | contract test | **no — 2 survive** | 1 | 1 | F1 | **OPEN.** P3-3 |
| DR4-12 | dashboard | plan "Deploy order" | provisioning → core → dashboard, skew both ways | r3 P3-3 | omits copilot-mro's settle writer; names core "through `16cd1ae`" | none (the contract test is the local check) | n/a | 3 | 1 | F3 | **PARTIAL.** P3-5 (closes DR3-14's order half) |
| DR4-13 | dashboard | `permissions-endpoint.test.tsx:350-380` | Scan reads `.mts`/`.cts` and proves it reached a `.mts` | r3 F4 | — | same | yes: R3M-mts, D20 | 1 | 0 | F1 | **SETTLED** (closes DR3-2a-08) |
| DR4-14 | dashboard | `auth-flow-sites.test.tsx:390-445`; `useInvitationPreview.ts:52-75` | Strict Mode double run reached (reads counted = 2) at hook and page level | r3 F3 | — | both Strict tests | yes: R3M-funnel-every-run (both red) | 2 | 0 | F3 | **SETTLED** (closes DR3-2a-14) |
| DR4-15 | dashboard | `invite-accept-retry-hydrated.test.ts:433-455` | Paste stripped by exactly one router replace, no raw write | r3 F1 | round-trip trade recorded (FI) | same | yes: R3M-hashraw | 2 | 0 | F1 | **SETTLED** (closes DR3-2a-03's pin; FI stands) |
| DR4-16 | dashboard | `adReviewPresentation.ts:325-340`; test `:886-909` | Clearance by exact sentence read | r3 F2 | test compares what `materializeDetail` renders | cleared-text test | yes: R3M-internal-reworded; exact-text lie = declared limit | 1 | 0 | F1 | **SETTLED** (closes DR3-2a-10; limit declared) |
| DR4-17 | dashboard | `InviteAcceptView.tsx:85-112` | `/invite` page keyed by the held token | r3 F6 | late answer lands on an unmounted page; forget-by-value residue declared | 3 paste tests | yes: F6-invite-unkeyed, R3M-hashraw | 2 (functional) | 1 | F3 | **SETTLED**; declared residue **OPEN by design** (FI) |
| DR4-18 | dashboard | `RegisterView.tsx:76-118` | `/register` form keyed by the held token | r3 F6 + ruling 3 | typed fields reset; confirmation left for the form; Cognito account left behind | 3 paste tests | yes: F6-register-unkeyed | 2 (functional) | 1 | F3 | **SETTLED** as ruled; the same-address "account exists" recovery **ASSERTED** (pre-existing path) (closes DR3-2a-20) |
| DR4-19 | dashboard | `PermissionContext.tsx:130-145`, `:336-372` | A refused body is a failed load: error constant, three fields cleared, first load and refresh | r3 F5 | source-read; nothing renders `error` (FI) | both refusal tests | yes: F5-silent | 1 | 2 | F1 | **SETTLED** for the code (closes DR3-2a-06) |
| DR4-20 | dashboard | `permissions-endpoint.test.tsx:205-250` (probe `:258-277`) | The probe proves the clearing | r3 F5 | probe reads `hasCapabilityInDepartment` only; `hasRouteAccess` uses `hasCapability` | same | **no — D6 AND D6c both survive the full lane** | 1 | 2 | F1 | **OPEN.** P3-1 |
| DR4-21 | dashboard | `f8c4614` | Green at HEAD | — | full lane 2675/2676 (the one red is layout; 15/15 with api beside); analytics 77/77; `tsc --noEmit` exit 0, no diagnostic; `next lint --file` ×20 "No ESLint warnings or errors" exit 0 | the lane | n/a | 3 | 0 | F2 | **SETTLED** |
| DR4-22 | dashboard / workspace | plan r3 section; workspace plan G.32/G.34/M-* rows | Reviewer advice, merge order, plan rows | — | see P3-7 | none | n/a | 3 | 1 | F3 | **OPEN.** P3-7 |
| DR4-23 | dashboard | `f8c4614` plan "20 mutants, all KILLED" | Implementer's ledger | — | 13 re-run here: all KILLED on the aimed `✖` | — | yes | 3 | 0 | F3 | **SETTLED** |
| DR4-24 | dashboard | `analytics-panel-builders.tsx:343` | A deleted chat's user reads "Deleted chat" | the sentinel names no person | the M-FACTS-ANONYMISE ruling's words are "show it as a deleted user" | user-column test | yes | 3 | 0 | F1 | **SETTLED**, wording noted for the owner |
| DR4-25 | dashboard | `AnalyticsPanelSection.tsx`; `page.tsx`; `analytics-panel-builders.tsx:282-299` | Demo mode pseudonymises the User column only; a table's question / comment / department text is drawn verbatim | pre-existing | neither the section nor the page names `demo`; `anonymizeMessageContent` is `ChartCard`'s and no table panel reaches it | none | n/a | 3 (functional: demo mode) | 1 | F3 | **OPEN.** P3-4, second half (found on the resume) |
| DR4-26 | dashboard / core | core `quality.py:63`, `:443` | The pinned sentinel is the one core's statement actually uses | attacks the pin the way P3-3 does | the constant is the SQL's own parameter, not a second spelling | contract test | yes: C-sentinel, C-annot | 1 | 0 | F1 | **SETTLED** (this half has no P3-3 gap) |
