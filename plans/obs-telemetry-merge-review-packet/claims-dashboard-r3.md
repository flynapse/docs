# Claims packet: dashboard r3 (Quality facts panels after M-FACTS-FAILURES / M-FACTS-ANONYMISE; r2 P3 fixes) — PARTIAL — in progress (PAUSED 2026-09-22 ~02:00 by owner request)

**PARTIAL — in progress.** Written incrementally per the coordinator's rule; paused mid-review on the owner's order. Rows
marked **VERIFIED** were established by a run or a read recorded below; rows marked **TODO** were not examined. Resume
notes: `~/.claude/scratch/obs-merge/dash-review-r3/PAUSED.md`.

Independent adversarial review (Opus), 2026-09-22, read-only throughout. Each commit was taken with `git archive <sha>` into
the private scratch directory `scratchpad/dash-review-r3/` (`09bacba/`, `65f588d/`, `4a7714a/`, and `mut/` = `4a7714a` for
mutants), `node_modules` symlinked from `dashboard/node_modules` (Next `15.2.4`). Durable notes and logs under
`~/.claude/scratch/obs-merge/dash-review-r3/`. No real tree was edited, checked out or committed; `dashboard-obsm` is clean
at `4a7714a`. No `next build`, no browser, no live stack. core-obsm and copilot-mro-obsm were read by `git show` at commit
SHAs only (live implementers commit there).

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `09bacba..4a7714a` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | `2a9b0f4` r2 P3 fixes (never independently reviewed — delegated to a second Opus reader, `sub-2a9b0f4-notes.md`; PAUSED with it) · `65f588d` Quality facts panels (registry + test) · `4a7714a` plan `docs/plans/obs-merge-quality-facts-panels.md` |

`4a7714a` differs from `65f588d` by the plan file only (`git diff --stat`), so one code run covers both.

## How it was run

Every runner after the coordinator's 01:30 rule went through `/home/aditya/Code/pytest-slot.sh --` (machine-wide semaphore,
exit status passed through); the three short runs before it (analytics lane, tsc, lint) ran bare and are marked. Own exit
status captured via `PIPESTATUS[0]`.

| check | commit | result | exit | slot? |
|---|---|---|---|---|
| analytics lane `tests/unit/analytics/*.test.ts?(x)` | `4a7714a` | 66 tests / 66 pass / 0 fail | 0 | no (pre-rule) — TODO re-run under slot; TODO the 63 count at `09bacba` |
| `tsc --noEmit` | `4a7714a` | clean | 0 | no (pre-rule) — TODO re-run under slot |
| `next lint --file` (both touched files) | `4a7714a` | "No ESLint warnings or errors" | 0 | no (pre-rule) — TODO re-run under slot |
| full unit `tests/unit/**/*.test.ts?(x)` (`--test-concurrency=2`) | `4a7714a` | 2656 tests / **2654 pass / 0 fail / 2 skipped** (860 s) | 0 | yes (`full-unit-4a7714a.log`; a first bare attempt was stopped at ~250 tests when the rule arrived) |

The implementer's "2656/2656" counts the two skipped tests as passes (r2's convention too: 2640/2638/0/2).

## Mutation ledger (facts-panels batch, `65f588d` code) — VERIFIED

Runner: node's `--test` via tsx, one file aimed unless stated; **exit 1 counted as a kill only when the log names the aimed
test's own `✖` line** (node's runner also exits 1 on a file that fails to load, which would be BROKE). Every mutant was
applied by `mutant.sh`, restored by it and md5-checked against the archived blob (`53f42c3c…` registry, `fc9e001a…` utils,
`65afb496…` page, `5c2c0528…` ChartCard). Baseline green (27/27 on the registry file; 122/122 on analytics+chat). Mutant
texts: `~/.claude/scratch/obs-merge/dash-review-r3/mutants/M*.a|b`; per-run logs `mut-M*.out`; `mutants.log` is the ledger.

| id | mutant | aimed at | result | what went red |
|---|---|---|---|---|
| M01 | drop `{failed}` from the outcomes series | registry test | **KILLED** | both new series tests |
| M02 | `failed` moved last (before `avg_confidence`) | registry test | **KILLED** | both (deepEqual + legend order) |
| M03 | key `not_answered` → `unanswered`, label kept | registry test | **KILLED** | deepEqual, and the sum test (8 ≠ 10 — the builder read 0) |
| M04 | label `Failed` → `Failures` | registry test | **KILLED** | both |
| M05 | swap `answered` / `unsure` | registry test | **KILLED** | both |
| M06 | builder `getSeriesValue` returns 0 for `failed` | registry test | **KILLED** | the sum test ONLY — the pin does exercise the builder |
| M08 | outcomes copy loses "exactly one" | registry test | **KILLED** | copy test |
| M09 | intent copy "Not Recorded" → "Unrecorded" | registry test | **KILLED** | copy test |
| M10 | outcomes table copy loses the history caveat | registry test | **KILLED** | copy test |
| M11 | drilldown copy loses "deleted chat" | registry test | **KILLED** | copy test |
| M13 | `failed` listed twice | registry test | **KILLED** | both |
| M15 | drop `avg_confidence` | registry test | **KILLED** | both |
| M17 | unanswered-questions table copy loses "deleted chat" | registry test | **KILLED** | copy test |
| M18 | cited copy loses "one row per document" | registry test | **KILLED** | copy test |
| M20 | builder legend reversed | registry test | **KILLED** | sum test (legend assertion) |
| M19 | outcomes copy says the OPPOSITE ("Failed turns are left out of every outcome") | registry test | **SURVIVED (aimed)** 27/27 | — word-presence pin (`/\bfail/i`) |
| M21 | builder throws on a bucket lacking a series key | registry test | **SURVIVED (aimed)** 27/27 | — the pin's bucket carries every key |
| M12 | page: mobile table shows all series when `<= 6` (was `<= 3`) | analytics + chat lanes (122) | **SURVIVED (aimed)** | — the mobile rule is unpinned |
| M14 | ChartCard colours series by reversed index | analytics + chat lanes (122) | **SURVIVED (aimed)** | — colour-by-index is unpinned |

**Survivor confirmation NOT complete:** the full lane with M12+M14+M19+M21 applied at once was STOPPED at 628 green tests
by the pause (`full-unit-survivors-M12-M14-M19-M21.log`, no `✖` before the stop — not evidence). Until it finishes, the
four are reported as *survived the aimed lanes*, not as survivors.

---

## Findings, ranked (provisional — the 2a9b0f4 sub-review and the survivor run are outstanding)

### No P0, no P1 found so far in `65f588d` / `4a7714a`.

### P2-1: Three panels whose counting changed under M-FACTS-FAILURES keep their old copy — VERIFIED (read)

- **Where:** `analytics-panel-registry.ts` `chat_time_duration_histogram` (`:290` "Shows the distribution of chat response
  durations."), `turn_latency_over_time` (`:631` "End-to-end turn latency percentiles per bucket."), `tool_usage_mix`
  (`:760` "Which tools turns called, and how often each one failed.").
- **Why it is a gap:** core `7d5144c` (its own commit message and the notes it added to `quality.py`, `reliability.py`,
  `operations.py`) states for each: histogram and latency now count *every settled turn — a failed turn at its time to
  failure, a never-saved turn at its time to settle, so a fast-failing outage pulls p50 DOWN*; tool usage mix is *saved
  turns only — the tool calls of a turn that failed before its save are not here*. The dashboard batch's own scope box
  ("Descriptions for every panel whose meaning changed") is ticked, and the copy test covers none of the three.
- **Failure scenario:** an outage that fails every turn in 300 ms moves the "Chat Time Duration Histogram" mass to its
  leftmost bucket and drops the Reliability p50; the operator reads faster answers. Same class the batch exists to close.
- **Fix:** three sentences from core's notes plus three `assert.match` lines in the copy test.

### P3-1: The copy pin is word-presence, not meaning — VERIFIED (M19)

- `analytics-panel-registry.test.ts:410-446` matches `/\bfail/i`, `/exactly one/i`, `/deleted chat/i`, etc. **M19**
  ("Failed turns are left out of every outcome") passes 27/27. A future edit can invert a sentence's meaning and keep the
  guard green. Recorded as guard shape; the copy today is right (checked sentence by sentence against core's notes).

### P3-2: The "sum to turns" pin is self-referential; the drift it cannot see is a core rename — VERIFIED (read + M03/M06)

- The test authors both the bucket and the expected 10; it proves the registry keys match the test's own keys through the
  real builder (M03, M06 show that half is real). It cannot see core renaming or adding a column: `getSeriesValue`
  (`chat-quality-panel-utils.tsx:82-85`) turns a missing key into a flat 0 line and an extra column into nothing.
- The implementer records this as Future Improvement #1 and calls the sibling reader "several hundred lines". The 275-line
  precedent (`tests/fixtures/automations/run-trigger-vocabulary.ts`) is the SNAPSHOT machinery; a skip-when-absent reader
  that regexes the `AS <key>` columns of `_outcomes_sql` from a sibling `core-obsm` via the existing `siblingName` helper is
  ~40 lines. Deferral fair, size claim overstated.

### P3-3: Version-skew rendering, and no deploy order recorded for the dashboard half — VERIFIED (read)

- Old core + new dashboard: the chart draws a **"Failed" line at flat 0** while the description says failures are counted
  (failures sit in `unknown` on old core). New core + old dashboard: the failed line is absent, the five no longer sum.
  Core's `quality.py` docstring records its own deploy order (owner provisioning run → core); the dashboard plan
  `obs-merge-quality-facts-panels.md` records none. Nearest precedent: plan §2.2 item 6 (api → dashboard for permissions).

### P3-4: A deleted chat's turn renders the sentinel `deleted-user` raw, and nothing says what it means — VERIFIED (read)

- copilot-mro `chat_turn_facts.py:685` `DELETED_USER_ID = "deleted-user"`; core `unanswered_questions` LEFT-joins live
  blocks so the row survives with `user_id = 'deleted-user'`, `question_excerpt = NULL`. Dashboard `table` variant
  (`analytics-panel-builders.tsx:282-287` `renderCell` → `String(value)`) prints the literal token in the "User" column
  and `—` for the question. The new table copy says "A deleted chat's turn keeps its place, with no question text" and
  nothing about the User column. Also pre-existing: the `table` variant never goes through `formatUserLabel`, so demo-mode
  anonymisation does not apply to these two tables (out of range; recorded).

### P3-5: "shows its id instead of a title" is false for a uid-less citation from a deleted chat — VERIFIED (read)

- `doc_uid` can be absent (`chat_turn_facts.py:479`, `:496`); after anonymisation such a citation has neither uid nor
  title, core groups every such citation into one row per kind with `document_id` and `label` both NULL, and
  `formatDocumentLabel` (`chat-quality-panel-utils.tsx:107-121`) prints **"Unknown"**. Edge case; one clause of copy.

### P3-6: The two rules the batch leans on — colour by index, first-series-on-mobile — are unpinned — VERIFIED (M12, M14 aimed)

- `ChartCard.tsx:517` `color: series[idx]?.color || getBrandColor(idx)` and `page.tsx:233` `series.length <= 3` have no
  test (M14, M12 pass 122/122 analytics+chat). The commit message's "matching core's order is what matches colour and
  legend" is a source-read claim. Whatever the narrow-screen decision, it should land with a pin.

### Narrow-screen change (attack 6) — observable effect and recommendation

- **Effect, plainly:** below Tailwind's default `lg` (1024 px — tablets in portrait and narrow laptop windows, not only
  phones), the "Answer Outcomes (Table)" shows two columns, Day/Hour and **Failed**; Answered, Unsure, Not answered,
  Unknown and Avg confidence are not reachable in the table (no row expand: `form_components.tsx:356-361`, `canExpand`
  false). Before `65f588d` that lone column was Answered. The chart above still draws all six lines with a tappable
  legend (`ChartCard` `toggleLegendItem`), so the data is on the screen, only the table is narrowed.
- **Recommendation: KEEP the order; do not reorder the display.** (1) A display-only reorder decouples the table's column
  order from the chart's legend and colour order on the same screen, which is the one convention the batch just
  re-anchored to core. (2) "Failed per bucket" is the most actionable single series for the reader this table serves on a
  small screen (an ops glance), and it is the series M-FACTS-FAILURES was ruled to surface. (3) The real defect is the
  rule "index 0 carries the story" for a six-series panel, not which series is index 0; the elegant fix is a per-panel
  `mobileSeriesKeys` in the registry (defaulting to today's rule), pinned — a Future Improvement, not this batch.

---

## What I tried to break and could not — VERIFIED

- **Contract parity.** core `fe41002` `_outcomes_sql` columns, in order: `failed, answered, unsure, not_answered, unknown,
  avg_confidence`; `_outcome_rows` seeds the same six. The registry lists exactly that (M01–M05, M13, M15 red).
- **A `turn_outcome` the dashboard does not know.** Cannot reach it: the vocabulary is `success | error`
  (copilot-mro `TURN_OUTCOMES`), and only the aggregate reaches the browser. `router_intent_distribution`'s new
  `not_recorded` renders "Not Recorded" via `formatIntentLabel` (underscore → space, title case) — matches the copy.
- **Colour shift.** Nothing else names the outcome series (repo grep: the registry, its test, the id constant); six series
  now fill the six-colour palette exactly, no wrap.
- **The pin through `buildTimeSeriesChart`.** A missing series or a wrong key is read as 0 and the sum trips (M03); a
  builder that drops a key trips it (M06); a reversed legend trips it (M20). A null count would also read 0 (core's
  `count(*) FILTER` never yields NULL; `avg_confidence` NULL → 0 on the line is pre-existing).
- **422 `loc` census.** Core's `request_validation_refused` (`http_errors.py`) emits `{loc, msg, type}` with
  `loc[-1] = "(extra field)"` on `extra_forbidden` and always a `msg` (`caller_safe_message` returns a string). Every
  dashboard reader of a list-shaped `detail` reads `msg`/`message` first (`fetch-utils.ts:89-104`,
  `improvement-api.ts:390-399`) or refuses non-strings (`signupRefusal.ts:61-62`, `lib/api/utils.ts:286-296`,
  `optimizer-api.ts:866-875`, the Next server routes — pinned by `server-route-error-bodies.test.ts:113-140`). The
  repo-wide word search for `loc` finds the two fixtures only. The implementer's leftover (`describeErrorDetailItem`
  `JSON.stringify` for a message-less element) is real and unreachable from core.
- **The copy, sentence by sentence,** against core's notes (`quality.py` at `fe41002`): outcomes, intent, clarification
  (incl. "a failed turn that was saved still counts"), drilldown, unanswered questions, top cited — all true (P3-5's edge
  aside). `description` reaches the screen (`page.tsx:858`), `tableDescription` too (`AnalyticsPanelSection.tsx:142`).
- **Anonymised row across the Quality panels.** Drilldown INNER-joins live blocks (never lists it); unanswered questions
  keeps it (P3-4); top cited joins its document's row; every count panel counts it. No per-user Quality panel exists other
  than those two tables.

## What I did not test

- The four aimed-lane survivors against the full lane (stopped by the pause).
- `2a9b0f4` at all, in this file — delegated (see `sub-2a9b0f4-notes.md`), paused with the rest.
- Any browser or Next runtime; the narrow-screen effect is read from `form_components.tsx` and Tailwind defaults.
- The `pytest-slot.sh` re-runs of analytics/tsc/lint (pre-rule runs stand as evidence; re-run owed for compliance).

---

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process.
**Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping.
**Chunk:** F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR3-01 | dashboard | `analytics-panel-registry.ts:310-317` | The outcomes series are core's five exclusive series in core's order, then `avg_confidence` | The registry is core's client half | core `fe41002` `_outcomes_sql` AS columns + `_outcome_rows` seeds, same six in the same order | `analytics-panel-registry.test.ts:376` (deepEqual) | **yes.** M01–M05, M13, M15 red | 1 | 0 | F1 | **SETTLED** (VERIFIED) |
| DR3-02 | dashboard | `analytics-panel-registry.test.ts:382-405` | One core-shaped bucket through the real builder sums to its turns, legend in core's order | The builder is exercised, not just the list | M06 (builder zeroes `failed`) red on this test alone; M20 (legend reversed) red | same | **yes.** M03, M06, M20 | 1 | 0 | F2 | **SETTLED** for what it pins; see DR3-08 for what it cannot |
| DR3-03 | dashboard | `analytics-panel-registry.test.ts:410-446` | Each changed panel's copy carries the fact it exists for | Copy drift fails here | 8 copy reverts red (M08–M11, M17, M18 + the implementer's own) | same | **yes, and one survives.** M19 (opposite meaning) passes 27/27 | 1 | 1 | F1 | **PARTIAL.** Word-presence pin (P3-1) |
| DR3-04 | dashboard | `analytics-panel-registry.ts:290`, `:631`, `:760` | Histogram, turn-latency and tool-usage copy left as before | (not a decision — an omission) | core `7d5144c` notes for all three say which turns count now | none | n/a | 2 | 1 | F1 | **OPEN.** P2-1 (VERIFIED) |
| DR3-05 | dashboard | `analytics-panel-registry.ts:305-307`, `:318-320`; core `quality.py` outcomes note | Outcomes copy: exclusive, failed = error saved or not, unknown = no verdict, history caveat | From core's notes | read against core at `fe41002`, sentence by sentence | copy test | M08, M10 red | 3 | 0 | F1 | **SETTLED** (VERIFIED) |
| DR3-06 | dashboard | `:273-274` intent; `:329-331` clarification; `:369-370` drilldown; `:416-417` unanswered; `:426-427` cited | The other five copies | From core's notes | read against core; `formatIntentLabel('not_recorded')` → "Not Recorded" | copy test | M09, M11, M17, M18 red | 3 | 0 | F1 | **SETTLED** (VERIFIED); DR3-09/10 carry the two edges |
| DR3-07 | dashboard | `ChartCard.tsx:512-517`; `buildTimeSeriesChart` legend | Colour and legend follow series index; matching core's order matches both | Existing convention, no panel declares colours | source-read; no other file names the series | none | **M14 survives** 122/122 (aimed) | 1 | 1 | F2 | **ASSERTED.** True today, unpinned (P3-6) |
| DR3-08 | dashboard / core | registry ↔ core `_outcomes_sql` | No cross-repo pin; transcription only | Precedent reader is a 275-line snapshot | a core rename reaches the chart as a flat-0 line (`getSeriesValue`) | none | n/a | 2 | 1 | F3 | **OPEN.** Recorded by the implementer (FI #1); size claim overstated (P3-2) |
| DR3-09 | dashboard | `analytics-panel-builders.tsx:282-287`; copilot-mro `chat_turn_facts.py:685` | A deleted chat's turn shows `deleted-user` verbatim in the User column | (the sentinel is copilot-mro's; the dashboard renders it raw) | LEFT JOIN keeps the row; `renderCell` → `String(value)` | none | n/a | 3 | 1 | F1 | **OPEN.** P3-4 |
| DR3-10 | dashboard / core | `chat-quality-panel-utils.tsx:107-121`; core `_cited_documents_sql` | "shows its id instead of a title" | — | uid-less + deleted → both NULL → "Unknown", one row per kind | none | n/a | 3 | 1 | F3 | **PARTIAL.** Edge unstated (P3-5) |
| DR3-11 | dashboard | `page.tsx:230-236`; `form_components.tsx:356-361` | Mobile table shows series index 0 only when > 3 series; now Failed | Existing rule | read; `lg` = 1024 px default | none | **M12 survives** 122/122 (aimed) | 2 | 1 | F3 | **OPEN.** Recommendation: keep; pin it (P3-6) |
| DR3-12 | dashboard | `fetch-utils.ts:35-56`, `:83-104`; core `http_errors.py:187-206` | No dashboard consumer reads `loc`; core's `(extra field)` breaks nothing | Census | every list-shaped reader reads `msg`/`message` or refuses; two fixtures only | `server-route-error-bodies.test.ts:113`, `signup-refusal.test.ts:65` (pre-existing) | not re-run here (read) | 3 | 1 | F1 | **ASSERTED**, confirmed by read (VERIFIED) |
| DR3-13 | dashboard | `fetch-utils.ts:97-104` | A message-less list element is `JSON.stringify`'d into the toast | Leftover, recorded (FI #2) | unreachable from core (`msg` always set) | none | n/a | 3 | 1 | F3 | **OPEN.** Recorded |
| DR3-14 | dashboard / core | dashboard plan (no deploy note); core `quality.py` docstring "Deploy order" | Dashboard half deploys after core's provisioning run | (unstated) | old core + new dashboard → "Failed" flat 0 under copy that says failures count | none | n/a | 3 | 1 | F3 | **OPEN.** P3-3 |
| DR3-15 | dashboard | the two code commits | Green at their own HEAD | — | table above (full lane 2654/0/2, tsc 0, lint clean) | the lane | n/a | 3 | 0 | F2 | **SETTLED** (VERIFIED; slot re-runs of the three short checks owed) |
| DR3-16 | dashboard | `2a9b0f4` (14 files, 612+/158−) | Seven r2 P3s closed | — | sub-review (Opus) PAUSED mid-way; provisional MERGE-CLEAN, P3 ×~6; 23 mutants planted so far: 18 KILLED, 5 SURVIVED aimed (R3M-hashraw, R3M-mts, allowlist-lie-verbless, internal-reworded, funnel-every-run) — full auth-lane confirmation of the five, P3-4 mutant, prose checks, tsc/lint on its 14 files all TODO | — | — | — | — | — | **PARTIAL — see the sub-review section below** |
| DR3-17 | dashboard | `4a7714a` plan file claims: "13 mutants all red", "Prettier not clean on either file nor the HEAD blob", "analytics 63 → 66" | — | — | 63-at-`09bacba` and the prettier claim not yet checked | — | — | 3 | 1 | F3 | **TODO** |

## Sub-review of `2a9b0f4` (r2 P3 fixes) — PROVISIONAL, paused; full detail in `~/.claude/scratch/obs-merge/dash-review-r3/sub-2a9b0f4-notes.md`

Rows below are the sub-reviewer's, copied as handed back (its numbering DR3-2a-xx). **Its five survivors are aimed-lane
only; its verdict is provisional.** Its provisional findings (all P3): F1 the `hashchange` re-strip is not pinned to the
router (a raw `replaceState` there survives, and `router.replace` on the paste path re-exposes r2 P3-1's MPA fallback);
F2 the AD clearance is by NAME with a verb-list backstop (a verbless control sentence survives); F3 the Strict-Mode funnel
guard is a decoy (`previewRecordedFor` dead in practice); F4 the `/test-cookie` scan skips `.mts`/`.cts`; F5 a refused
permissions body is silent to the UI (`error` stays null) — deep validation does match core's wire shape; F6 `retry`
state is not reset over a newly pasted token; F7 (out of range) `capabilitiesByDepartment[name]` on a plain object throws
for a department named `constructor`.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR3-2a-01 | dashboard | `InviteAcceptView.tsx:209-221`; test `invite-accept-retry-hydrated.test.ts:397-413` | Try again only for `unreachable`, guard drives expired/revoked/invalid/accepted with a real token | P3-2 | preview read asserted per status | same | **yes.** M13 red | 1 | 0 | F1 | **SETTLED** (closes DR2-11) |
| DR3-2a-02 | dashboard | `invite-token-hold.ts:49-57`; `invite-token-hold.test.ts:37-47`; accept test `:415-428` | A token in the address wins over the held one | P3-3 | unit + mounted remount onto a newer token | both | **yes.** M09 red, 3 tests | 2 | 0 | F1 | **SETTLED** (closes DR2-09) |
| DR3-2a-03 | dashboard | `hooks/auth/useHeldInviteToken.ts:56-62` | `hashchange` re-reads, re-holds and re-strips a pasted `#token=` | DR2-31 | router ignores null-state popstate (app-router.js:451); no leak seat found (memory + POST body; '1' to sessionStorage) | accept test `:430-450` | **partly.** listener removal red, no-strip red; raw-strip SURVIVES (R3M-hashraw, aimed) | 2 | 1 | F1 | **PARTIAL** (closes DR2-31 behaviour; new coverage gap F1) |
| DR3-2a-04 | dashboard | `lib/auth/PermissionContext.tsx:95-152` | Body validated all the way down; refused as a whole | P3-4 | 12 probes + mounted refusal; wire shape matches core DDL | `permissions-endpoint.test.tsx:137-216` | not yet planted | 2 | 2 | F1 | **ASSERTED → TODO** (would close DR2-26; F5 silent refusal noted) |
| DR3-2a-05 | dashboard | `permissions-endpoint.test.tsx:291-350` | `/test-cookie` scan walks the repo root minus 9 dirs, proves it reached `middleware.ts` and `constants/index.ts` | P3-5 | — | same | **yes.** M22, M23 red; `.mts` SURVIVES (R3M-mts, aimed) | 2 | 0 | F1 | **SETTLED** for ts/tsx/js/jsx/mjs/cjs/json (closes DR2-27); .mts gap F4 |
| DR3-2a-06 | dashboard | `adReviewPresentation.ts:325-329`; `ad-review-materialize.test.ts:867-925` | Every shared category has a page row or is on `MATERIALIZE_SHARED_COPY_NAMES_NO_CONTROL`; instructions derived from the shared tables | P3-5 | — | same | **yes/partly.** M25, M25r, allowlist-lie-open red; verbless lie + reworded `internal` SURVIVE (aimed) | 1 | 1 | F1 | **PARTIAL** (structural half closes DR2-19's new-category gap; clearance-by-name gap F2 remains) |
| DR3-2a-07 | dashboard | accept test `:367-370` | Storage scan covers cookies | P3-6 | — | same | **yes.** M08 red | 2 | 0 | F1 | **SETTLED** (closes DR2-08) |
| DR3-2a-08 | dashboard | `placementOutcome.ts:108-111` | Forget on APPLIED in the shared decision | P3-6 | mounted /invite + seam unit; register path = visible delegation, un-mountable | `invite-token-hold.test.ts:69-99`, accept test `:452-470` | **yes.** M10 red, 2 tests | 3 | 0 | F1 | **SETTLED** at the seam; **ASSERTED** for the mounted /register path (closes DR2-10) |
| DR3-2a-09 | dashboard | `useInvitationPreview.ts:70-75` | One funnel record per token per attempt | P3-6 | failure then success recorded | `auth-flow-sites.test.tsx:367-388` | **yes.** token-only key red; every-run SURVIVES (Strict guard decoy, F3) | 2 | 0 | F3 | **SETTLED** for the retry (closes DR2-13); Strict-Mode claim **REFUTED as tested** |
| DR3-2a-10 | dashboard | `RegisterView.tsx:561-593` | `reopen` no longer offers the uninvited signup; dead links keep it | P3-6 | — | `invite-register-hydrated.test.ts:381,432` | **yes.** restore red | 2 | 0 | F1 | **SETTLED** (closes DR2-14) |
| DR3-2a-11 | dashboard | `useHeldInviteToken.ts:49` | `scroll:false` pinned on both pages | P3-6 | — | both "strip goes through the router" tests | **yes.** M05 red ×2 | 3 | 0 | F1 | **SETTLED** |
| DR3-2a-12 | dashboard | the refactor into `useHeldInviteToken` | Read→hold→strip order, Strict Mode ref, router options preserved | — | M01, M02, M06, M07, M16, M17 all red | r2 guards | **yes** | 0 | 0 | F2 | **SETTLED** (DR2-01/04/05/06/08 still hold); M14/M18/M32/M33/M11/M12 TODO |
| DR3-2a-13 | dashboard | `RegisterView.tsx:100-104`; test rename; `invite-token-hold.ts:16-23` | P3-7 / P3-1 prose corrections | — | not yet checked vs Next source | n/a | n/a | 3 | 1 | F3 | **TODO** |
| DR3-2a-14 | dashboard | `InviteAcceptView.tsx:93,230,385` | `retry` state not reset on a hash paste | new seat | source-read | none | not planted | 2 (functional) | 1 | F3 | **OPEN** (F6) |

## Final sweep (attack 7) — dashboard side of every plan item naming it, from the code at `4a7714a`

Line numbers in the plan are unstable (it is edited live); items are cited by id. **VERIFIED by grep/read** unless marked.

| item | dashboard side | state | evidence |
|---|---|---|---|
| G.22 (M-RUNERROR copy) | `runErrorAttribute` + category copy | DONE | present in `runOutcomeCopy.ts`, `RunHistoryPanel.tsx`, `AutomationNotificationRow.tsx`, `adReviewPresentation.ts` |
| G.36(d) | bell reads `payload.error`; null-prototype badge/routes | DONE | `AutomationNotificationRow.tsx:247` `readText(payload,'error')`; `department-routes.ts:33` `Object.create(null)`; `RunStatusBadge.tsx:77-80` reads `AUTOMATION_STATUS_META` (TODO: confirm its null-prototype form) |
| G.56 | prototype-lookup census guard | DONE | `tests/unit/lookups/prototype-lookup-tables.test.ts` |
| G.58 / M-RUN-REASON | `runReasonAttribute` at both DOM sites + visible copy | DONE | `RunHistoryPanel.tsx:210`, `AutomationNotificationRow.tsx:277`, `adReviewPresentation.ts:370` |
| G.77(a) / M-CHART-CELL | table cell via `Object.hasOwn` | DONE | `ChartCard.tsx:895`; `tests/unit/chat/chart-card-table-cell.test.tsx` |
| G.94 / G.64(a) | trigger vocabulary incl. `one_shot` + contract | DONE | `automations-api.ts:93`; `contracts/automation-run-triggers.json` |
| G.64(c) | capability sentence carries no count | DONE | `PermissionContext.tsx:484` |
| G.32 / M-FACTS-FAILURES | series + copy (this range) | **PARTIAL** | `65f588d`; three panels' copy missing (P2-1); no deploy note (P3-3) |
| G.34 / M-FACTS-ANONYMISE | copy for the panels core changed | **PARTIAL** | `65f588d`; `deleted-user` sentinel unexplained (P3-4); "Unknown" edge (P3-5) |
| M-FACT-LIMITS | none ("no code change") | N/A | — |
| M-INVITE-FRAGMENT | fragment link, marker hand-off, hold, strip | DONE (pending `2a9b0f4` sub-review) | `0f87aec`, `49f6231`, `09bacba`, `2a9b0f4` |
| M-PERMISSIONS-ENDPOINT | `PermissionContext` reads `GET /auth/permissions` body, deep-validated | DONE (pending `2a9b0f4` sub-review) | `e3a4610`, `2a9b0f4` |
| M-FALLBACK | three-valued `DashboardOffer` | DONE; residues B2-36..38 owner-owed | B2 re-statement |
| M-TURNCARD | server-side refusal is copilot-mro's; dashboard: none briefed | **OPEN, no dashboard batch ever briefed** — the ruling needs no dashboard change strictly, but B2-35's residue (first-paint fetch, `gcTime` 5 min in `query-client.ts:26`) stands until the server refuses | `improvement/page.tsx:181` `notInternal` unchanged |
| M-COMMIT | dashboard production files committed | DONE | `afd6300` |
| G.54 | "`dashboard-obsm` has no TS depth or layout guard at all" | **OPEN, never briefed** (TODO: confirm whether the item assigns dashboard work) | no `tests/unit/infra/` layout guard exists (`tests/unit/build/standalone-guard.test.ts` only) |
| G.83(a) | one-shot sentences | DONE | `runOutcomeCopy.ts:250` `one_shot_kind` |
| G.52, G.65, G.91, G.1, G.47, G.73 | mention the dashboard as a cross-repo reference or a Grafana `service.name`; no dashboard-repo work named | N/A | read |
| B2 re-statement rows that are dashboard work no batch was briefed for | B2-4/B2-21 (ungated profile arm + widening untested), B2-12 (`event_id` omitter uncounted), B2-17 (`canViewDashboard === false` case), B2-20 (two-sided `view_dashboard` invariant), B2-29 (identity-change eviction of `llmTurns`), B2-30 (privacy docstrings unguarded), B2-38 (all-unknown profile → blank page), B2-39 (`networkMode`), B2-40 (panel order drift), B2-41 (read contracts voluntary), B2-42 (profile shape declared twice), B2-43 (tenant-less `llmTurns` key), B2-44 (`content_bytes: 0` → `—`), B2-45 (`logger.error` on `forbidden`) | **OPEN, none briefed**; this range touched none of their files (`git log 09bacba..4a7714a` — only the registry, its test, auth/invite files, AD presentation) | B2 re-statement + `git log` |

## Open claims, tier 2 first

**Tier 2:** none opened by this range. (B2-35 M-TURNCARD and B2-43 remain the dashboard's tier-2 residue, unchanged.)

**Tier 1, open:** DR3-04 (P2-1, three copies), DR3-03 (P3-1, word-presence pin), DR3-08 (P3-2), DR3-14 (P3-3), DR3-09 (P3-4),
DR3-10 (P3-5), DR3-07 / DR3-11 (P3-6; narrow-screen: keep, pin), DR3-13 (recorded).

**Tier 0, settled:** DR3-01, DR3-02, DR3-05, DR3-06, DR3-15.

**TODO before the verdict:** DR3-16 (the `2a9b0f4` sub-review), DR3-17, the survivor full-lane run, the slot re-runs.
Provisional verdict for `65f588d`+`4a7714a` alone: **FIX-FIRST on P2-1** (three sentences + three asserts), else clean.
