# Claims — phase 6 dashboards/alerts/runbooks fix pass (adversarial review)

Repo under review: `copilot-mro-obsm` @ `obs-merge`.
Frozen diff: 7 uncommitted production files + commit `d8d2570c` (two new guard tests).
Baseline lane: `DEBUG=false POSTGRES_DB=copilot_mro_test poetry run pytest tests/integration/otel/ -q`
→ **132 passed / 26 skipped**. With `OTEL_RULES_CHECK=1` the promtool lanes also pass (31 passed / 2 skipped).

Verification scripts (scratchpad, nothing written to the tree):
`../attack_guard1.py`, `../attack_guard1b.py`, `../attack_guard2.py`, `../attack_guard2b.py`.

| Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|
| copilot-mro-obsm | `docs/runbooks/observability/oss-profile.md:102-109` | Query 3 filters `status = 'failed' OR late_run` | Presented as "what failed or fired late, with the stored diagnostic" | Real status vocabulary is `claimed/running/completed/failed/skipped/timed_out/awaiting_input/abandoned` — `core-obsm/core/resources/automations/services/automation_store.py:96` (`STATUS_TIMED_OUT`, written by `reap_stale_runs` :3068 and `recover_stale_one_shot_runs` :1300/:1324), :118 (`_STATUS_SKIPPED`), :84 (the executor-owned words, incl. `abandoned`). `timed_out` and `skipped` are never returned. | none | not recorded | 1 | P0-1 | OPEN |
| copilot-mro-obsm | `docs/runbooks/observability/oss-profile.md:102-104` | "whether a retry is pending (`attempts`, `retry_after`)" on query-3 rows | Tells the operator to read retryability off a `failed` row | Retry stamps exist only on `status='skipped'` rows — `automation_store.py:2476` (`list_retryable_runs` predicate) and :2533 (stamp cleared on retry). `retry_after` on a `failed` row is structurally NULL. | none | not recorded | 1 | P0-1 | OPEN |
| copilot-mro-obsm | `docs/runbooks/observability/oss-profile.md:88,99,109` | Three `created_at`/`now()` comparisons | Windows the three new queries | `automation_runs.created_at` is `timestamp` written from Python `_utcnow()` (naive UTC) — `core-obsm/core/db/table_definitions.py:1197`, `automation_store.py:225-227,784,997`. The module's own docstring (`automation_store.py:45-48`) names the trap: "`now()` is `timestamptz` and … silently converts through whatever the session's `TimeZone` happens to be". Correct form: `now() AT TIME ZONE 'UTC'`. | none | not recorded | 1 | P1-1 | OPEN |
| copilot-mro-obsm | `tests/integration/otel/test_alertmanager_secrets_dir.py:132-177` | New guard `test_the_runbook_does_not_describe_the_secret_files_as_already_there` | Claimed: limb 1 is *derived*, not a word list | DEFEATED. Two rewordings of the identical false claim pass all three limbs (`attack_guard1.py`: mutation A "All three files are already present in any checkout … each holding a single REPLACE-ME line"; mutation B "normally all three are already there … just open each and swap its dummy line"). Limb 1 only bites on a *backticked UPPER_SNAKE* literal; limb 2 is the word list the commit message says limb 1 replaces. | itself | **partially recorded** — the claimed proof against the *verbatim* old wording reproduces (limb1 `['REPLACE_THIS_LINE_WITH']`, limb2 3 hits, `attack_guard1b.py`); it does not generalise | 1 | P1-2 | ASSERTED |
| copilot-mro-obsm | `tests/integration/otel/test_grafana_dashboards.py:231-276` | New guard `test_catalogue_and_dashboards_agree_on_each_browser_signal_state` | Claimed to close the panel-grain hole | DEFEATED three ways (`attack_guard2.py`): (a) renaming the catalogue table header drops **all** catalogue rows to zero and the test still PASSES — `assert claims` is satisfied by the board side alone, so its "this test now passes by seeing nothing" message is not what it enforces; (b) flipping the Slowest Pages row to DARK *and* misspelling the event (`browser.page.boot`) restores the exact defect and PASSES; (c) `_BROWSER_EVENT` needs three dot-segments, so 10 of 21 declared events are never compared — incl. `browser.error`, `browser.web_vital`, `browser.auth.login`, and **`browser.telemetry.dropped`**, whose catalogue row (`CATALOGUE.md:369`) never spells the event name. | itself | **partially recorded** — the claimed proof (same-signal DARK restore) reproduces: state-agreement FAILS while `test_catalogue_and_dashboards_agree` PASSES (`attack_guard2b.py`) | 1 | P1-3 | ASSERTED |
| copilot-mro-obsm | `flynapse-agent-alerts.yml:33-42` + `alerts.md:194-198` | Kept `for: 30m` on `increase(...[30m])` and added the argument | Argument's closing clause: "leave the window, which is what makes a sparse-traffic gap visible" | WRONG. Window == hold means the expression must be >0 for a full 30 min, which needs an increment in *every* 30-minute sub-window across 60 minutes. A model called less often than ~2×/h that is unpriced on **every** call never fires. Sparse traffic is precisely the case the pairing makes invisible. The runbook's "one unpriced call keeps the window above zero for very nearly the hold on its own" is true but sets the expectation that a single bad model id pages in ~30 min; it never does. | promtool lint only (syntax) | not recorded | 1 | P1-4 | OPEN |
| copilot-mro-obsm | `oss-profile.md:205` | "every notification is lost with nothing in the logs to say so"; "Loud is the designed outcome; the missing file is the one that hides" | The load-bearing contrast of the rewritten step 1 | CONTRADICTED by the sibling runbook. `alerts.md:134-136` lists "The Alertmanager container's logs. `Notify for alerts failed` … each retry logs `Notify attempt failed, will retry later`" as a first check, and :139-141 lists "the `ALERTMANAGER_*_FILE` path … exists" as a known cause. `alertmanager.yml:46,59,77` uses `api_url_file`/`auth_password_file`, read at notify time — a directory at that path errors there like any other unreadable secret, so BOTH paths log, increment `alertmanager_notifications_failed_total` and fire `AlertmanagerNotificationsFailing`. Only *container start* is silent. | `test_alertmanager_delivery_failures.py` (exists; exercises a webhook nobody answers, not a missing secret file) | not recorded | 1 | P1-5 | OPEN |
| copilot-mro-obsm | `CATALOGUE.md:369`, `frontend.json` panel 18 | `browser.telemetry.dropped` flipped DARK → WIRED (controller's change) | Production call site reaches the recorder | **COULD NOT BREAK.** `boot.ts:35` calls `startTelemetry()` with no options → `provider.ts:286` `options.exporters ?? defaultExporters()` → :158-159 `onDropped: reportDropped` → :149 `emitTelemetryDropped` → `events.ts:321` → `emitRecord` → `logs.getLogger(SCOPE).emit`. All eight keys (`batches items rejected exhausted evicted serialize closed last_status`) are on the collector browser log allow-list, `deployment/otel/base.yaml:146`. | `BROWSER_STATE_NOTE` (grammar only) + the new state-agreement guard, which **does not see this event** (no event name in the catalogue row) | not recorded | 1 | P1-3 | OPEN |
| copilot-mro-obsm | `CATALOGUE.md:370`, `frontend.json` panel 12 | `browser.settings.mutation` DARK → WIRED | TanStack conversion merged | **COULD NOT BREAK.** Eight `dashboard/hooks/settings/*.ts` files carry `meta.telemetry: { event: 'browser.settings.mutation', … }` (e.g. `useInvitations.ts:288-296`); consumed by `lib/telemetry/mutation-meta.ts:117-152` `onMutationSettled`, wired into the production `MutationCache` in `lib/query/query-client.ts:13`. | state-agreement guard (compares, agrees) | not recorded | 0→1 (see note) | P2 | ASSERTED |
| copilot-mro-obsm | `CATALOGUE.md:374`, `frontend.json` panel 14 | `browser.optimizer.run_triggered` DARK → WIRED | Emitter reached from production | **COULD NOT BREAK.** `dashboard/hooks/api/useOptimizer.ts:551` (preflight) and :576 (solve) → `optimizerRunTelemetry` (`mutation-meta.ts:184`) → same settle path. | state-agreement guard | not recorded | 1 | P2 | ASSERTED |
| copilot-mro-obsm | `CATALOGUE.md:377`, `frontend.json` panel 19 | `browser.app.boot` DARK → WIRED | Emitter unconditional | **COULD NOT BREAK.** `components/providers/TelemetryProvider.tsx:28` `emitAppBoot()` in a mount effect; `use-route-telemetry.ts:108-135` guards only on `window`/`bootEmitted`/missing nav entry. Allow-list passes `load_complete_ms`, `entry_route_pattern`. | state-agreement guard | not recorded | 1 | P2 | ASSERTED |
| copilot-mro-obsm | `frontend.json` panels 7/8, `llm-agents.json` panels 11/12, `CATALOGUE.md:180-181,209,374` | Four Postgres panels "live (Phase 5 grants)" → WIRED | Grants are code-reading, not looking | Correct call, and the downgrade is consistent everywhere (`grep` for "LIVE at Phase 5 / live (Phase 5 / Phase 5 grants" returns nothing). Writers exist: `document_opened` from `dashboard/lib/telemetry/use-document-view.ts:73` + `DocumentCard.tsx:114`; `llm_usage`/`llm_model_calls` from the ledger. | **none** — these panels carry no `browser.*` event, so the new state-agreement guard skips them entirely | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `oss-profile.md:171-183` vs `deployment/observability-local/alertmanager/slack_webhook_url.placeholder` | "The secret files BELONG in the checkout" | Two committed artifacts disagree | The placeholder's own text: "The real prod and dev webhook files live outside the repo (docs/runbooks/observability/oss-profile.md)." | `test_alertmanager_secrets_dir.py` (never reads the placeholder) | not recorded | 2 | P2 | OPEN |
| copilot-mro-obsm | `CATALOGUE.md:369` | Cross-repo line citation `dashboard lib/telemetry/provider.ts:147` | Cites the doc comment; the `onDropped:` wiring is :158-159 | Read of `provider.ts:147-159` | none | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `alerts.md:321` | `the "Run failures" log stream` | Actual panel title is `Run failures (api log stream, run_id / job_id bound, WARN+)` | `shift-optimizer.json` title list | none — the pass declined to guard runbook-quoted titles | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `oss-profile.md:56` | Ledger query promoted to "the **runbook SQL ledger check** — this query" | `WHERE tenant_id = :tenant` is not runnable as pasted in `psql` (needs `:'tenant'` + `\set`) | Read | `test_oss_profile_smoke.py` (compose-gated, skipped by default) | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `oss-profile.md:250-253` | "The provisioning smoke proves the EIGHT boards LOAD" | `EXPECTED_UIDS` does hold 8 — but that smoke is `OTEL_COMPOSE_SMOKE=1`-gated and skipped by default | `pytest -rs`: `test_grafana_provisioning_smoke.py:124,139 SKIPPED (compose smoke disabled)` | the smoke itself, skipped | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `frontend.json` board description | Defines `DARK until <what would arm it>` "on this board" | `fn-frontend` now has **zero** DARK panels, so the browser limb of `test_dark_panel_notes_are_present` no longer exercises a DARK note | Panel-state dump of `frontend.json` | `test_dark_panel_notes_are_present` (passes, nothing to check) | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `alerts.md:226-228` | "A 24h lookback moves slowly, so the hold … drops a single scrape-boundary spike" | A 24h `increase` stays above the threshold for ~24h once crossed; the 30m hold de-bounces an evaluation blip, not a spike | Rule text `flynapse-agent-alerts.yml:69-71` | promtool lint only | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `flynapse-agent-alerts.yml:69` | `sum by (tenant_id)` resolves | **COULD NOT BREAK.** `RuntimeTelemetry.for_turn` sets `tenant.id` (`telemetry.py:1473`) and `_model_attributes` sets `model.profile` (:1792); the OTLP→Prometheus mapping underscores both, and `llm-agents.json` "Metered cost per hour by tenant / profile" already groups on the same two labels. | Read | `test_emitted_series_inventory.py` (series/kind, not labels) | not recorded | 1 | — | OPEN |
| copilot-mro-obsm | `oss-profile.md:74-113` | Column/role correctness of the three new queries | **COULD NOT BREAK.** Every column exists in `AUTOMATION_RUNS_FIELDS` (`core-obsm/core/db/table_definitions.py:1169-1252`); `tenant_id` is injected by `tenancy="tenant"`; `trigger` is a non-reserved PostgreSQL keyword so it parses unquoted; `automation_runs` is in `READONLY_SELECT_RELATIONS` (`scripts/provision_rls.py:278`) and `flynapse_readonly` is `BYPASSRLS` by design (:862). | Read | none | not recorded | 1 | — | OPEN |
| copilot-mro-obsm | `alerts.md:16,28,40,50,61,91,182,199,214,240,299,301,304,319` | Quoted panel titles | All resolve against the eight boards **except** `"Run failures"` (row above) | Title dump of all 8 dashboards | none | not recorded | 1 | P2 | OPEN |
| copilot-mro-obsm | `alerts.md:36-39,57-60,211-213` | Rewritten CollectorExporterFailures / CollectorReceiverRefusing / LedgerWriteFailures windows and holds | **COULD NOT BREAK.** `5m` rate + `for: 10m`, `5m` rate + `for: 10m`, `[10m]` increase + `for: 5m` — all match `flynapse-platform-alerts.yml` and `flynapse-agent-alerts.yml` exactly; the lazy-counter claim matches the platform file's own header. | Read + `test_alert_rules_layout.py` (passes with `OTEL_RULES_CHECK=1`) | not recorded | 1 | — | ASSERTED |
| copilot-mro-obsm | `oss-profile.md:186-195` | Placeholder defaults "one directory up", "every compose file names as its default" | **COULD NOT BREAK.** `alertmanager/slack_webhook_url.placeholder` + `smtp_password.placeholder` are tracked; all three compose files name them as `${…:-default}` (`observe-docker-compose.yml:58-60`, `docker-compose.yml:138-140`, `poc/docker-compose.yml:98-100`). `secrets/` holds only `.gitignore`. | `test_only_the_inner_gitignore_is_tracked_under_the_secrets_dir` | not recorded (pre-existing test, unchanged) | 1 | F3 | **ASSERTED** — downgraded by the controller 2026-09-20: the gate says tier 0 REQUIRES `SETTLED`, and `SETTLED` requires a guard shown to fail when the property is removed. This row records `not recorded`, so it was neither. It is the only tier-0 claim ever filed across nine slices, and it did not meet the bar |

**Tier note.** No row in this table qualifies for tier 0 on the work this pass added: the two new
guards are both defeatable, so neither "mutation-checked guard proves it" in the sense tier 0
requires. The single SETTLED row is the pre-existing git-tracking guard, which this pass did not
change.

## Open claims, tier 2 first

**Tier 2**

1. `oss-profile.md` vs the committed `slack_webhook_url.placeholder`: the runbook says the three
   secret files BELONG in the checkout; the placeholder file, which is what an operator sees
   mounted in the container, says the real files "live outside the repo". Estate-shaping because it
   decides where every deployment's secrets are kept and nothing reconciles the two.

**Tier 1 — no guard, resting on judgment**

2. Query 3's status filter (`failed OR late_run`) misses `timed_out`, `skipped` and `abandoned`.
3. `retry_after` on a `failed` row can never answer "is a retry pending".
4. The three `now()` comparisons against naive-UTC `timestamp` columns.
5. `UnpricedModelCalls`: the kept `for: 30m` makes sparse unpriced traffic permanently silent; the
   new argument asserts the opposite.
6. `oss-profile.md:205` "nothing in the logs to say so" contradicts `alerts.md:134-141` and the
   `AlertmanagerNotificationsFailing` rule description.
7. The four Postgres panels' WIRED state is compared by nothing — the new guard keys on `browser.*`
   events and these panels have none.
8. `browser.telemetry.dropped` — the note the controller changed — is likewise compared by nothing,
   because the catalogue row never spells the event name.
9. Ten of twenty-one declared browser events are outside the new guard's regex.
10. The new guard passes vacuously if the catalogue's panel tables change shape.
11. Guard 1 passes on any reworded restatement of the defect it was built for.
12. `"Run failures"` quoted title; `:tenant` in the ledger check; the "EIGHT boards LOAD" claim
    resting on a default-skipped smoke; `provider.ts:147`; `fn-frontend` having no DARK panel left
    to exercise; the TenantDailySpendHigh "drops a spike" rationale.

## Explicitly not tested

- Alertmanager was **not run** with a missing secret file. The "nothing in the logs" finding rests
  on `alertmanager.yml` using `api_url_file`/`auth_password_file`, on the upstream read-at-notify
  path, and on this repo's own sibling runbook describing the log lines — not on execution.
- No live Postgres session was opened, so the timezone shift is argued from the column types, the
  writer, and `automation_store.py`'s own docstring rather than demonstrated.
- The compose-gated smokes (`OTEL_COMPOSE_SMOKE=1`) were not run; no board was loaded in Grafana.
- No browser was driven, so no P9-dated `LIVE` claim on `fn-frontend` was independently confirmed.

---

## Re-statement 2026-09-22

Appended by the R2 packet re-stater (Opus), read-only, nothing committed; the table above is left as
filed. **HEADs read:** copilot-mro-obsm `735f8213` (obs-merge, clean) · copilot-mro-obsm-r7b
`afe79dbb` (branch `obs-merge-r7b`, NOT merged; lane #6 reviewing it) · core-obsm `b4d2c33`.
**Column note:** the table has no `#` column; rows are numbered F-1..F-24 below in file order and
identified by their `File:line` cell. Its `Tier` column is §2.3a's; the `Chunk` column carries the
reviewer's severity ids (P0-1, P1-2, …) rather than F1/F2/F3, and the one `0→1` cell is the
controller's 2026-09-20 downgrade recorded in the row itself.

**What happened to the fix pass after this review.** The seven uncommitted production edits this
review read were committed at `9f44382e` (2026-09-21 04:19) TOGETHER with the fixes answering this
review's P0-1, P1-1, P1-4, P1-5, the quoted titles and the "EIGHT boards" count (its message names
them; ledger CHECKPOINT 13 records the responses — "every Phase 6 defect worked, and one of my
claims was FALSE"). The two defeated guards were hardened at `4bfa4967` (2026-09-20 10:55, after this
review): guard 1 gained unbackticked/hyphenated/derived-verb limbs with three mutations; guard 2 lost
its one-sided `assert claims` (defeat a) and its three-segment regex (defeat c). Independent check:
copilot-mro r7b (`claims-copilot-mro-r7b.md`, "`9f44382e` vs `claims-phase6-fixpass.md`: PARTLY
covered … I re-checked them": its fixes hold; R7B-34/35/36/37). r7b's own leftovers then landed as
`300a6fb2` on `obs-merge-r7b` — placeholder vs runbook, `provider.ts:158-159` on the board, a runnable
ledger query, guard 2's defeat (b) — **unmerged at the HEADs above**, so several rows below are true
on one branch and false on the other; each says which.

| row # | File:line (as filed) | claim state at filing | state now | evidence | source |
|---|---|---|---|---|---|
| F-1 | `oss-profile.md:102-109` query 3 status filter | OPEN (P0-1) | FIXED-AT `9f44382e` (implementer): `status IN ('failed','timed_out','skipped') OR late_run`, with prose on why `late_run` cannot substitute. The `abandoned` clause of this row is REFUTED by r7b R7B-34 (independent): core `dc41caa` never writes `abandoned` (`automation_store.py:161-163`), so query 3 is complete. Still prose, no guard | `9f44382e` message; ledger CP 13; r7b R7B-34 | tree; r7b |
| F-2 | `oss-profile.md:102-104` `retry_after` on a `failed` row | OPEN (P0-1) | FIXED-AT `9f44382e`: `skipped` joined the filter precisely because non-NULL `retry_after` is written only alongside `skipped` (the implementer traced both writers; ledger CP 13 "the comment's promise was structurally unkeepable"). No guard | ledger CP 13 | tree |
| F-3 | `oss-profile.md:88,99,109` `now()` vs naive `timestamp` | OPEN (P1-1) | FIXED-AT `9f44382e`: every comparison is `now() AT TIME ZONE 'UTC'`; the implementer confirmed both INSERT paths supply `_utcnow()` so the DDL default never fires; r7b R7B-34 confirmed the columns are naive `timestamp` (`table_definitions.py:1231ff`) — ASSERTED by r7b's reading, no guard | ledger CP 13; r7b R7B-34 | tree; r7b |
| F-4 | `test_alertmanager_secrets_dir.py:132-177` guard 1 | ASSERTED (DEFEATED) | FIXED-AT `4bfa4967` (implementer): limb 1 matches any capitalised run joined by `_`/`-`, unbackticked; limb 2 gained two DERIVED patterns (an edit-in-place verb within a sentence's reach of the three filenames; `create`/`write` excluded because the section must instruct them); three mutations (unbackticked token, hyphenated token, restatement). r7b R7B-37 recorded the defeats as "not re-run"; r7b's implementer then re-ran mutations A and B "against this tree and both FAIL the guard now" (`300a6fb2` message) — implementer proof both times, no independent red. `300a6fb2` also adds a test holding the placeholder to the same secrets directory (unmerged) | `4bfa4967`, `300a6fb2` messages; r7b R7B-37 | tree; r7b |
| F-5 | `test_grafana_dashboards.py:231-276` guard 2 | ASSERTED (DEFEATED ×3) | PARTLY FIXED on obs-merge, FULLY on r7b: (a) the vacuous pass — `4bfa4967` asserts each side separately and then their overlap ("proved by renaming the header against both versions: the old assert passes, the new one fails"); (c) the regex — trailing segment optional, so `browser.error`/`browser.web_vital` are compared; the implementer REFUTED this row's count ("10 of 21, including `browser.telemetry.dropped`" → the regex missed 3, only 2 of them named by both documents; `telemetry.dropped` IS matched — uncompared because the catalogue names it in prose, not a panel row); (b) flip-and-misspell — closed only by `300a6fb2` (the catalogue's and the boards' event sets must be EQUAL; the two prose-only rows now spell their event), UNMERGED. Now at `test_grafana_dashboards.py:318` | `4bfa4967`, `300a6fb2` messages; ledger CP 13 | tree |
| F-6 | `flynapse-agent-alerts.yml:33-42` + `alerts.md:194-198` `for: 30m` on `[30m]` | OPEN (P1-4) | FIXED-AT `9f44382e` ("the rule was fixed, not the claim": lookback `[30m]` → `[1h]`, hold kept; the runbook states the pairing) with a guard from `4bfa4967`, `test_an_any_occurrence_rule_looks_back_further_than_it_holds` (deliberately narrowed to the alerts nothing retries after its first version flagged 14 correct rules). Then SUPERSEDED AGAIN: `57f486c6` added the first-event `count(x unless last_over_time(x[1h] offset 1h))` branch (a lazily created series is born at 1 — r7b R7B-23 REFUTED `9f44382e`'s "fires after the first call" at that SHA, fixed at HEAD) and `7130d4d0` (r7 P3-1) stopped it false-firing on a scrape gap (`test_every_any_occurrence_rule_sees_the_first_event_of_a_label_set`). Independent: r7 P3-1, r7b R7B-23 | `flynapse-agent-alerts.yml:35-63`; r7b R7B-23; copilot-mro-rounds FX-08 | tree; r7b |
| F-7 | `oss-profile.md:205` "nothing in the logs" | OPEN (P1-5) | FIXED-AT `9f44382e`: "both failure modes are LOGGED, not silent" and the rewrite adds what was missing — that the alert routes through the broken integration, so read Prometheus `/alerts`, the Alertmanager UI or the container log (ledger CP 13 "FALSE, and now corrected"). r7b P3-3 re-checked. Alertmanager was still never run with a missing file | ledger CP 13; r7b | tree |
| F-8 | `CATALOGUE.md:369`, panel 18 `browser.telemetry.dropped` DARK → WIRED | OPEN (could not break) | STATE HOLDS (WIRED; iac `5e476e0` independently records "the drop counter's onDropped was always wired — P9 simply dropped no batch"). The COMPARISON gap: on obs-merge the catalogue row still names the event only in prose, so guard 2 skips it; `300a6fb2` (unmerged) makes the row spell `browser.telemetry.dropped` and requires set equality | tree; `300a6fb2`; iac `5e476e0` | tree |
| F-9 | `CATALOGUE.md:370`, panel 12 `browser.settings.mutation` | ASSERTED (tier 0→1) | UNCHANGED (checked); the iac twin `5e476e0` re-derived the same fact ("ten hooks/settings/ producers in the generated browser-signals.json") | tree; iac `5e476e0` | tree |
| F-10 | `CATALOGUE.md:374`, panel 14 `browser.optimizer.run_triggered` | ASSERTED | UNCHANGED (checked) | tree | tree |
| F-11 | `CATALOGUE.md:377`, panel 19 `browser.app.boot` | ASSERTED | UNCHANGED (checked); SEE `claims-E-deployment-and-iac.md` E17 | tree | tree |
| F-12 | frontend 7/8 + llm-agents 11/12 Postgres panels → WIRED | OPEN | STILL OPEN: correct and consistent (`9f44382e`), still compared by nothing — no `browser.*` event, no inventoried metric, so both lints and guard 2 skip them (the `KNOWN_RELATIONS` hatch, `9900a933`, only stops `llm_usage`/`llm_model_calls` reading as unknown series) | tree | tree |
| F-13 | `oss-profile.md:171-183` vs `slack_webhook_url.placeholder` | OPEN, **tier 2** | SPLIT BY BRANCH: on obs-merge STILL OPEN and STRONGER — `oss-profile.md:196` "The secret files BELONG in the checkout" vs the placeholder's "live outside the repo" (both verified at HEAD; r7b R7B-35 OPEN); FIXED on `obs-merge-r7b` `300a6fb2` (both say "in the checkout, never in the repo"; the placeholder names the git-ignored `alertmanager/secrets/` directory; a new test holds it to the same directory the runbook table and the git-ignore tests use) — UNMERGED, implementer proof | tree; r7b R7B-35; `300a6fb2` | tree; r7b |
| F-14 | `CATALOGUE.md:369` cites `provider.ts:147` | OPEN | PARTLY FIXED: the catalogue says `provider.ts:158-159` at HEAD (`9f44382e`); the BOARD (`frontend.json:313`, panel 18) still says `:147` on obs-merge; fixed on r7b `300a6fb2` (unmerged). r7b R7B-36 | tree; r7b R7B-36 | tree |
| F-15 | `alerts.md:321` `"Run failures"` | OPEN | FIXED-AT `9f44382e` (quoted titles match the real titles) and GUARDED since `4bfa4967`: `test_runbook_panel_quotes_match_the_real_panel_titles` (quoted strings following a board uid resolve against that board's titles; ~40 lines because a naive extractor false-positives on backticked label matchers). Implementer proof; r7b re-checked "the panel titles" | `4bfa4967` message; r7b | tree |
| F-16 | `oss-profile.md:56` `:tenant` | OPEN | SPLIT BY BRANCH: obs-merge `oss-profile.md:61` still `WHERE tenant_id = :tenant` (r7b R7B-36 OPEN, and `9f44382e` promoted it to "the runbook SQL ledger check"); r7b `300a6fb2` sets it with `\set tenant '<tenant id>'` and reads `:'tenant'` — UNMERGED | tree; r7b R7B-36 | tree |
| F-17 | `oss-profile.md:250-253` "EIGHT boards LOAD" on a default-skipped smoke | OPEN | STILL OPEN as a measurement: the count is right (`9f44382e`) and the smoke is still `OTEL_COMPOSE_SMOKE=1`-gated; no later lane ran it (every reviewer refused docker). r7b R7B-32 found the compose healthcheck guard shape-only (G11M1–M4 decoys pass) → r7b `1f705234` parses the probe (unmerged) | tree; r7b R7B-32 | tree |
| F-18 | `frontend.json` description defines `DARK until` with zero DARK panels | OPEN | UNCHANGED (checked): the description still defines the DARK form and the board has 0 `DARK until` panels, so the browser limb of `test_dark_panel_notes_are_present` still exercises no DARK note | tree | tree |
| F-19 | `alerts.md:226-228` "24h lookback … drops a single scrape-boundary spike" | OPEN | UNCHANGED (checked): the sentence is at `alerts.md:244-245` verbatim; `TenantDailySpendHigh` rule unchanged (`[24h]`, `for: 30m`) | tree | tree |
| F-20 | `flynapse-agent-alerts.yml:69` `sum by (tenant_id)` | OPEN (could not break) | UNCHANGED (checked): now `:97`; still no label guard (the inventory pins series/kind) | tree | tree |
| F-21 | `oss-profile.md:74-113` column/role correctness | OPEN (could not break) | UNCHANGED (checked) for the columns and the `BYPASSRLS` reader; the queries themselves changed per F-1..F-3 | tree | tree |
| F-22 | `alerts.md:16,28,…` quoted panel titles | OPEN | FIXED-AT `9f44382e` + guarded (F-15's test covers every quoted title after a board uid) | tree | tree |
| F-23 | `alerts.md:36-39,57-60,211-213` rewritten windows/holds | ASSERTED | UNCHANGED (checked) for the three rules (5m/10m, 5m/10m, `[10m]`/`for: 5m` at `:79-83`); `LedgerWriteFailures` additionally gained the first-event branch (`57f486c6`) and its runbook row was rewritten with it | tree | tree |
| F-24 | `oss-profile.md:186-195` placeholder defaults | ASSERTED (downgraded from tier 0) | UNCHANGED (checked) on obs-merge: both `.placeholder` files tracked, the three compose files name them as `${…:-default}`, `secrets/` holds only `.gitignore`; `test_only_the_inner_gitignore_is_tracked_under_the_secrets_dir` unchanged. The placeholder's TEXT changes on r7b `300a6fb2` (unmerged) | tree | tree |

### Open claims now, tier 2 first

1. **F-13 (tier 2)** — the runbook/placeholder contradiction on where secrets live is still live on
   obs-merge; its fix and its test are on `obs-merge-r7b` only (lane #6 review, then merge).
2. **F-5 (b) / F-8 / F-14 / F-16** — the same branch split: defeat (b) of guard 2, the event set
   equality, the board's `provider.ts:147`, the `\set tenant` query. Until `300a6fb2` merges, this
   file's rows are the truth of obs-merge.
3. **F-12** — the four Postgres panels' WIRED state is still compared by nothing (tier 1, OPEN).
4. **F-17** — the provisioning smoke has still not been run by anyone since the fix pass; the count is
   right, the proof is skipped (tier 1, OPEN).
5. **F-18, F-19** — untouched prose/vacuity items (tier 1, OPEN).
6. **F-4** — guard 1's hardening and the re-run of defeats A/B are implementer-proved on both
   occasions; no independent reviewer has seen guard 1 go red since this file's defeat.

**Closed since filing (obs-merge):** F-1, F-2, F-3, F-6 (superseded twice), F-7, F-15, F-22; F-5
(a)+(c).

### Cross-file staleness (listed, not fixed)

1. `claims-phase6-dashboards.md` rows 44, 45, 46, 48 record the runbook defects this fix pass
   answered as "OPEN — and wrong"; all four are fixed at `9f44382e` (re-stated there today).
2. `claims-copilot-mro-r7b.md` R7B-37 says guard 1's file "has had no change since" the fix pass —
   `git log` shows `4bfa4967` (2026-09-20 10:55, the hardening) touched
   `test_alertmanager_secrets_dir.py` after `d8d2570c` and before r7b ran. R7B-37's "defeats stand"
   was therefore an untested assumption at its own date; `300a6fb2`'s re-run of A/B (both caught) is
   the later reading. Neither cell was re-run by an independent reviewer.
3. `claims-copilot-mro-rounds.md` row "`1d1d2dc8..0d9ecf0b` … `9f44382e` may be the fix pass already
   filed in claims-phase6-fixpass.md — not verified" — now verified by r7b: it is that fix pass PLUS
   the responses to this review.
4. The ledger's CHECKPOINT 13 and `4bfa4967`'s message both refute this file's "10 of 21 declared
   browser events" count (3 missed by the regex, 2 in both documents); the row text above is left as
   filed.

### Could not trace

- Whether `300a6fb2`'s guard-1 re-run (mutations A and B) used this file's exact wordings: the
  commit message says "the two recorded defeats (A, B)"; the scratch scripts `attack_guard1.py` etc.
  were session-scratch and are gone.
- The r7b r2 review (lane #6) verdict on `300a6fb2`: `claims-copilot-mro-r7b-r2.md` did not exist
  at the HEADs above.
