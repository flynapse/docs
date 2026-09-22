# Claims packet: dashboard r3 (Quality facts panels after M-FACTS-FAILURES / M-FACTS-ANONYMISE; r2 P3 fixes) — FINAL dashboard review

Independent adversarial review (Opus), 2026-09-22, read-only throughout. Paused once by the owner (~02:00) and resumed; the
partial file was replaced by this one. Each commit was taken with `git archive <sha>`: first into the session scratchpad
(`scratchpad/dash-review-r3/`), then — after the workspace rule moved mutation copies out of `/tmp` — into
`~/.claude/scratch/obs-merge/dash-review-r3/{mut,base-09bacba}` (durable notes, mutant texts, every log). `node_modules`
symlinked from `dashboard/node_modules` (Next `15.2.4`), never installed. No real tree was edited, checked out or committed;
`dashboard-obsm` is clean at `4a7714a`. No `next build`, no browser, no live stack. core-obsm and copilot-mro-obsm were read
by `git show <sha>:<path>` only (live implementers commit there): core at `fe41002`, re-checked at `b730a95`.

`2a9b0f4` had never had an independent review, so it was delegated to a second Opus reader (one agent, briefed with r2's
packet); its rows are DR3-2a-xx below and its notes are `~/.claude/scratch/obs-merge/dash-review-r3/sub-2a9b0f4-notes.md`.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `09bacba..4a7714a` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | `2a9b0f4` r2 P3 fixes (14 files, 612+/158−) · `65f588d` Quality facts panels (registry + test) · `4a7714a` plan `docs/plans/obs-merge-quality-facts-panels.md` |

`4a7714a` differs from `65f588d` by the plan file only (`git diff --stat`), so one code run covers both.

## How it was run

Runner: node's `--test` via tsx (npm repo; `package-lock.json`), `--test-concurrency=2`. Every run below went through
`/home/aditya/Code/pytest-slot.sh --`, one runner at a time from this lane; own exit status captured. (Three early short
runs went bare before the slot rule reached this lane; each was re-run under the slot, same result.)

| check | commit | result | exit |
|---|---|---|---|
| full unit `tests/unit/**/*.test.ts?(x)` | `4a7714a` | 2656 tests / **2654 pass / 0 fail / 2 skipped** (860 s) | 0 |
| analytics lane `tests/unit/analytics/*.test.ts?(x)` | `4a7714a` | 66 / 66 / 0 | 0 |
| analytics lane | `09bacba` | 63 / 63 / 0 — the implementer's "63 → 66" holds (static `test(` count 61 → 64, the three new tests) | 0 |
| `tsc --noEmit` | `4a7714a` | clean | 0 |
| `next lint --file` (registry + its test) | `4a7714a` | "No ESLint warnings or errors" | 0 |
| `prettier --check` (same two files) | `09bacba` and `4a7714a` | unclean at BOTH — the plan's "neither was the HEAD blob" holds | 1 / 1 |
| sub-review (`2a9b0f4`) | `2a9b0f4` | domain lane 306/306; `tsc` exit 0; `next lint` clean on its 14 files | 0 |

The implementer's "2656/2656" counts the two skipped tests as passes (r2's convention too).

## Mutation ledger (facts-panels code) — 19 mutants: 15 KILLED, 4 SURVIVED (full lane), 0 BROKE

Aimed at `tests/unit/analytics/analytics-panel-registry.test.ts` unless stated. Exit 1 was counted as a kill only when the
log shows the aimed test's own `✖` line (node's runner also exits 1 when a file fails to load, which would be BROKE).
`mutant.sh` applied, restored and md5-checked each (`53f42c3c…` registry, `fc9e001a…` utils, `65afb496…` page,
`5c2c0528…` ChartCard); baselines green (27/27 file; 122/122 analytics+chat). Texts `mutants/M*.a|b`, ledger
`mutants.log`, per-run `mut-M*.out`.

| id | mutant | result | what went red |
|---|---|---|---|
| M01 | drop `{failed}` | **KILLED** | both new series tests |
| M02 | `failed` moved last | **KILLED** | both |
| M03 | key `not_answered` → `unanswered`, label kept | **KILLED** | deepEqual, and the sum test (8 ≠ 10: the builder read 0) |
| M04 | label `Failed` → `Failures` | **KILLED** | both |
| M05 | swap `answered` / `unsure` | **KILLED** | both |
| M06 | builder `getSeriesValue` returns 0 for `failed` | **KILLED** | the sum test ONLY — that pin does exercise the builder |
| M08 | outcomes copy loses "exactly one" | **KILLED** | copy test |
| M09 | "Not Recorded" → "Unrecorded" | **KILLED** | copy test |
| M10 | outcomes history caveat dropped | **KILLED** | copy test |
| M11 | drilldown loses "deleted chat" | **KILLED** | copy test |
| M13 | `failed` listed twice | **KILLED** | both |
| M15 | drop `avg_confidence` | **KILLED** | both |
| M17 | unanswered-questions loses "deleted chat" | **KILLED** | copy test |
| M18 | cited loses "one row per document" | **KILLED** | copy test |
| M20 | builder legend reversed | **KILLED** | sum test (legend assertion) |
| M19 | outcomes copy says the OPPOSITE: "Failed turns are left out of every outcome" | **SURVIVED** | — |
| M21 | builder throws on a bucket lacking a series key | **SURVIVED** | — |
| M12 | page: all series on mobile when `<= 6` (was `<= 3`) | **SURVIVED** | — |
| M14 | ChartCard colours by reversed index | **SURVIVED** | — |

Survival confirmed on the FULL lane with M12+M14+M19+M21 applied together: 2656 / 2654 pass / 0 fail / 2 skipped, exit 0
(`full-unit-survivors-r2.log`); copy restored and `git archive 4a7714a | tar -d` content-clean afterwards. The sub-review's
33 mutants on `2a9b0f4` (28 killed, 5 survived on the full auth lane, 0 broke) are in its section below.

---

## Findings, ranked

**Verdict: FIX-FIRST — P0 0 / P1 0 / P2 1 / P3 13** (`65f588d`/`4a7714a`: P2 ×1, P3 ×7; `2a9b0f4`: P3 ×6, its own verdict
MERGE-CLEAN). The one P2 is three sentences of copy plus three assertions; with it (and P3-7's clause) landed, the range is
MERGE-CLEAN. No leak was found anywhere in the range.

### No P0, no P1.

### P2-1: Three panels whose counting changed under M-FACTS-FAILURES keep their old copy

- **Where:** `analytics-panel-registry.ts:289` `chat_time_duration_histogram` ("Shows the distribution of chat response
  durations."), `:631` `turn_latency_over_time` ("End-to-end turn latency percentiles per bucket."), `:760`
  `tool_usage_mix` ("Which tools turns called, and how often each one failed.").
- **Why:** core `7d5144c` — its commit message and the notes it added to `quality.py`, `reliability.py`,
  `operations.py` — states for each: histogram and latency count *every settled turn, a failed turn at its time to
  failure, a never-saved turn at its time to settle, so a fast-failing outage pulls p50 DOWN*; tool usage mix is *saved
  turns only*. The batch's scope box "Descriptions for every panel whose meaning changed" is ticked; the copy test covers
  none of the three.
- **Failure scenario:** an outage that fails every turn in 300 ms moves the duration histogram's mass to its leftmost
  bucket and drops the Reliability p50; an operator reads faster answers — the misreading this batch exists to prevent.
- **Fix:** one sentence each from core's notes, plus three `assert.match` lines in the copy test.

### P3-1: The copy pin is word-presence, not meaning (M19 survives the full lane)

- `analytics-panel-registry.test.ts:414-453` matches `/\bfail/i`, `/exactly one/i`, `/deleted chat/i`, … — an edit that
  inverts a sentence ("Failed turns are left out of every outcome") keeps it green. The copy today is right, checked
  sentence by sentence against core's notes. A meaning-level pin is not cheap for prose; recorded as guard shape.

### P3-2: The "sum to turns" pin is self-referential; a core rename reaches the chart as a flat-0 line

- The test authors both the bucket and the expected 10. It proves the registry keys match the test's keys through the real
  builder (M03, M06, M20 red), but it cannot see core renaming or adding a column: `getSeriesValue`
  (`chat-quality-panel-utils.tsx:82-85`) draws a missing key as 0 and ignores an extra one (M21 survives: nothing
  depends on the 0 fallback being there).
- The implementer records this as Future Improvement #1 and sizes the sibling reader at "several hundred lines". The
  275-line precedent (`tests/fixtures/automations/run-trigger-vocabulary.ts`) is the SNAPSHOT machinery; a
  skip-when-absent reader of `_outcomes_sql`'s `AS <key>` columns through the existing `siblingName` helper is tens of
  lines. The deferral is fair; the size is overstated.

### P3-3: Version skew, and no deploy order on the dashboard side

- Old core + new dashboard draws a "Failed" line at flat 0 under a description that says failures are counted (old core
  files failures in `unknown`). New core + old dashboard drops the failed series, and the five no longer sum. Core records
  its own order (provisioning run → core) in `quality.py`; `obs-merge-quality-facts-panels.md` records none. Precedent:
  plan §2.2 item 6 (api → dashboard).

### P3-4: A deleted chat's turn shows the raw sentinel `deleted-user`, and nothing says what it means

- core `b730a95` (`e9fb7b3`) answers `unanswered_questions.user_id` as `DELETED_USER_ID` whenever the live block is
  missing, so EVERY deleted chat's row — including chats deleted before the anonymising writer — reads `deleted-user`.
  The `table` variant (`analytics-panel-builders.tsx:282-287`, `renderCell` → `String(value)`) prints it verbatim in the
  User column, `—` for the question. The new copy explains the empty question, not the user. (Pre-existing, out of range:
  the `table` variant bypasses `formatUserLabel`, so demo-mode anonymisation does not apply to these two tables.)

### P3-5: "shows its id instead of a title" is false for a uid-less citation from a deleted chat

- `doc_uid` can be absent (copilot-mro `chat_turn_facts.py:479`, `:496`). At core `b730a95` (`5f8c879`) the group key is
  `COALESCE(doc_uid, 'title:' || document)`, NULL for such a citation, so all of them land in ONE row with id and label
  NULL; `formatDocumentLabel` (`chat-quality-panel-utils.tsx:107-121`) prints "Unknown". Edge; one clause.

### P3-6: The two rules the batch leans on — colour by index, first series on mobile — are unpinned (M12, M14 survive the full lane)

- `ChartCard.tsx:517` `color: series[idx]?.color || getBrandColor(idx)` and `page.tsx:236` `series.length <= 3`. The
  commit's "matching core's order is what matches colour and legend" is true by source-read and guarded by nothing.

### P3-7: The outcomes copy's "Unknown" lags core `b2d67f2`

- After this batch, core made `unknown` the catch-all (`answer_found IS NULL OR <> ALL(<mirrored vocabulary>)`: "or a
  verdict this mirror does not know"). `analytics-panel-registry.ts:305` still defines Unknown as "no verdict (the judge
  did not run, or the turn was never saved)". Unreachable today (copilot-mro's CHECK admits Yes/Unsure/No only); true
  the day the writer's vocabulary grows first. Fold into P2-1's fix.

### `2a9b0f4` — the sub-review's six P3s (verified against its ledger; F4 and F6 spot-checked here in the code)

- **F1** `hooks/auth/useHeldInviteToken.ts:56-62` — the hashchange re-strip is not pinned to the router (R3M-hashraw, a raw
  `replaceState(null)`, passes the full lane); and on this path `router.replace` is a server round trip whose failure
  full-loads `/invite` without the pasted token (`fetch-server-response.js:163-176`), where a raw replace would be absorbed
  by Next's restore reducer. Future Improvements.
- **F2** `adReviewPresentation.ts:329`, test `:890-898` — a category is cleared by NAME with a fixed control-verb backstop;
  a verbless control sentence ("Turn the automation off … use Run now") on the clearance list, or the cleared `internal`
  sentence reworded to add one, passes the full lane. Fix: store the cleared sentence itself, `{category: exact text}`.
- **F3** `useInvitationPreview.ts:57,70-75`, test `auth-flow-sites.test.tsx:390` — the "Strict Mode records once" guard is a
  decoy: the mount run has token `''`, the token run is a single update, so `previewRecordedFor` never fires (removing it
  passes the full lane).
- **F4** `permissions-endpoint.test.tsx:311` — the `/test-cookie` scan's extensions omit `.mts`/`.cts`; `scripts/` holds
  three `.mts` generators (confirmed here).
- **F5** `PermissionContext.tsx:136-154,331-333` — one malformed department refuses the whole body: on first load every gate
  is closed with `error` null and `loading` false (indistinguishable from a caller with no tenant; only a constant
  `logger.warn`); on a later refresh the previous permissions stay. Fail-closed and server-enforced, but unexplained.
- **F6** `InviteAcceptView.tsx:93,230,385`; `RegisterView.tsx:105,940` — a pasted link does not reset per-invitation state:
  A's "could not be applied" alert or "You're in" persists over B (two probes pass, so the defect is real); on `/register`
  a paste during confirmation switches the activation token from A to B after the account POST carried A (source-read;
  `inviteToken` from the hook reaches the confirmation view at `:940`, confirmed here). Before `2a9b0f4` a paste was
  ignored entirely.

### Narrow-screen change — observable effect and recommendation

- **Effect:** below Tailwind's default `lg` (1024 px — tablets in portrait and narrow laptop windows, not only phones),
  "Answer Outcomes (Table)" shows two columns, Day/Hour and **Failed**. Answered, Unsure, Not answered, Unknown and Avg
  confidence cannot be reached in the table (no row expand: `form_components.tsx:356-361`). Before `65f588d` the lone
  column was Answered. The chart above still draws all six lines with a tappable legend.
- **Recommendation: KEEP the order; do not reorder the display only.** (1) A display-only reorder splits the table's column
  order from the chart's legend and colour order on the same screen, the one convention this batch re-anchored to core.
  (2) Failed per bucket is the most actionable lone series on a small screen, and it is the series M-FACTS-FAILURES was
  ruled to surface. (3) The real defect is "index 0 carries the story" for a six-series panel, whichever series is index
  0; the elegant fix is a per-panel `mobileSeriesKeys` in the registry (defaulting to today's rule) with a pin (M12 shows
  there is none) — a Future Improvement.

---

## What I tried to break and could not

- **Contract parity.** core `fe41002` `_outcomes_sql` AS-columns, in order: `failed, answered, unsure, not_answered,
  unknown, avg_confidence`; `_outcome_rows` seeds the same six; the registry matches (M01–M05, M13, M15 red).
  **Re-verified at core `b730a95`** (r8 fixes incl. `b2d67f2`, `e9fb7b3`, `5f8c879`): same six, same order, same seeds;
  `b2d67f2` changed only which rows `unknown` counts (P3-7). **The parity row holds.**
- **A `turn_outcome` the dashboard does not know.** Cannot reach it: `success | error` (copilot-mro `TURN_OUTCOMES`) is
  aggregated server-side. `not_recorded` renders "Not Recorded" via `formatIntentLabel`, matching the copy.
- **Colour shift.** Nothing else names the outcome series (repo grep: registry, its test, the id constant); no panel
  declares colours; six series fill the six-colour palette exactly.
- **The pin through `buildTimeSeriesChart`.** A wrong key reads 0 and trips the sum (M03); a builder dropping a key trips it
  (M06); a reversed legend trips it (M20). A NULL count cannot come from `count(*) FILTER`.
- **422 `loc`.** Core's `request_validation_refused` emits `{loc, msg, type}`, `loc[-1] = "(extra field)"` on
  `extra_forbidden`, and always a `msg`. Every list-shaped `detail` reader takes `msg`/`message` (`fetch-utils.ts:89-104`,
  `improvement-api.ts:390-399`) or refuses non-strings (`signupRefusal.ts:61-62`, `lib/api/utils.ts:286-296`,
  `optimizer-api.ts:866-875`, the Next routes — pinned by `server-route-error-bodies.test.ts:113-140`). `loc` appears in two
  fixtures only. The `JSON.stringify` leftover is real and unreachable from core.
- **The copy, sentence by sentence,** against core's notes: outcomes, intent, clarification (incl. "a failed turn that was
  saved still counts"), drilldown, unanswered questions, top cited — true, P3-5/P3-7 aside. Both `description`
  (`page.tsx:858`) and `tableDescription` (`AnalyticsPanelSection.tsx:142`) reach the screen.
- **The anonymised row across Quality.** The drilldown inner-joins live blocks (never lists it); unanswered questions keeps
  it as `deleted-user` (P3-4); top cited joins its document's row; every count panel counts it. No other per-user Quality
  panel exists.
- **The plan file's claims.** 63 → 66 (runtime, both commits), Prettier unclean at both, 422 census — all hold. Its "13
  mutants, all red" was not re-run as such; this lane's 15 kills on the same guards are consistent with it.
- **`2a9b0f4`**: all seven r2 P3s close (DR2-08, 09, 10, 11, 13, 14, 15, 26, 27 closed; DR2-31's behaviour closed; DR2-19
  half closed); the refactor keeps DR2-01, 02, 04, 05, 06, 08, 12 red under their mutants; no leak seat in the new
  `hashchange` handler (memory + POST body only, pathname-only telemetry, `'1'` in `sessionStorage`).

## What I did not test

- Any browser or Next runtime: the narrow-screen effect is read from `form_components.tsx` and Tailwind's default `lg`; F1's
  and r2 P3-1's round-trip analysis is read from the installed `next@15.2.4`.
- The full 2656-test lane at `2a9b0f4` itself (its domain lanes, `tsc` and `lint` were run; the full lane ran at `4a7714a`,
  which contains it).
- core's own db lane for the new panel statements (read, not run); the owner's provisioning order.
- The `/register` activation path of the token forget (F6's register half and DR3-2a-12): Amplify is sealed, source-read.

---

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process. A
functional regression takes the nearest slot and is marked. **Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 =
consequential but reversible; 2 = irreversible or estate-shaping. **Chunk:** F1 contract + privacy, F2 the merge itself,
F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR3-01 | dashboard | `analytics-panel-registry.ts:310-317` | The outcomes series are core's five exclusive series in core's order, then `avg_confidence` | The registry is core's client half | core `_outcomes_sql` AS-columns + `_outcome_rows` seeds at `fe41002`, **re-verified at `b730a95`** | `analytics-panel-registry.test.ts:376` | **yes.** M01–M05, M13, M15 red | 1 | 0 | F1 | **SETTLED** |
| DR3-02 | dashboard | `analytics-panel-registry.test.ts:383-407` | One core-shaped bucket through the real builder sums to its turns, legend in core's order | The builder is exercised, not just the list | M06 red on this test alone; M20 red | same | **yes.** M03, M06, M20 | 1 | 0 | F2 | **SETTLED** for what it pins (DR3-08 for what it cannot) |
| DR3-03 | dashboard | `analytics-panel-registry.test.ts:414-453` | Each changed panel's copy carries the fact it exists for | Copy drift fails here | 6 copy reverts red | same | **yes, and one survives the full lane.** M19 (opposite meaning) | 1 | 1 | F1 | **PARTIAL.** P3-1 |
| DR3-04 | dashboard | `analytics-panel-registry.ts:289`, `:631`, `:760` | Histogram, turn-latency and tool-usage copy left as before | (omission) | core `7d5144c` notes for all three | none | n/a | 2 | 1 | F1 | **OPEN.** P2-1 |
| DR3-05 | dashboard | `analytics-panel-registry.ts:305`, `:318-320` | Outcomes copy: exclusive, failed = error saved or not, unknown = no verdict, history caveat | core's notes | read against core, sentence by sentence | copy test | M08, M10 red | 3 | 0 | F1 | **SETTLED** at `fe41002`; see DR3-18 for `b2d67f2` |
| DR3-06 | dashboard | `:273-274` intent; `:329-331` clarification; `:369-370` drilldown; `:416-417` unanswered; `:426-427` cited | The other five copies | core's notes | read against core; `formatIntentLabel('not_recorded')` → "Not Recorded" | copy test | M09, M11, M17, M18 red | 3 | 0 | F1 | **SETTLED**; DR3-09/10 carry the edges |
| DR3-07 | dashboard | `ChartCard.tsx:512-517`; builder legend | Colour and legend follow series index | Existing convention, no panel declares colours | source-read; nothing else names the series | none | **no — M14 survives the full lane** | 1 | 1 | F2 | **ASSERTED.** True today, unpinned (P3-6) |
| DR3-08 | dashboard / core | registry ↔ core `_outcomes_sql` | Transcription only; no cross-repo pin | Precedent is a 275-line snapshot | a core rename draws flat 0 (`getSeriesValue`, `:82-85`); M21 survives the full lane | none | n/a | 2 | 1 | F3 | **OPEN.** Implementer's FI #1; size overstated (P3-2) |
| DR3-09 | dashboard / core | `analytics-panel-builders.tsx:282-287`; core `b730a95` `unanswered_questions` CASE | A deleted chat's turn shows `deleted-user` verbatim | The sentinel is copilot-mro's; core now answers it for every non-live block | read at `b730a95` (`e9fb7b3`) | none | n/a | 3 | 1 | F1 | **OPEN.** P3-4 |
| DR3-10 | dashboard / core | `chat-quality-panel-utils.tsx:107-121`; core `_cited_documents_sql` at `b730a95` | "shows its id instead of a title" | — | uid-less + deleted → NULL key → one row, "Unknown" | none | n/a | 3 | 1 | F3 | **PARTIAL.** P3-5 |
| DR3-11 | dashboard | `page.tsx:233-237`; `form_components.tsx:356-361` | Mobile table shows series 0 only when > 3 series — now Failed | Existing rule | read; `lg` = 1024 px | none | **no — M12 survives the full lane** | 2 | 1 | F3 | **OPEN.** Recommend keep + `mobileSeriesKeys` pin |
| DR3-12 | dashboard | `fetch-utils.ts:35-56`, `:83-104`; core `http_errors.py` `request_validation_refused` | No dashboard consumer reads `loc`; `(extra field)` breaks nothing | Census | every list-shaped reader takes `msg`/`message` or refuses; two fixtures only | `server-route-error-bodies.test.ts:113`, `signup-refusal.test.ts:65` (pre-existing) | read | 3 | 1 | F1 | **SETTLED by read** (confirms the implementer's census) |
| DR3-13 | dashboard | `fetch-utils.ts:97-104` | A message-less list element is `JSON.stringify`'d into the toast | Leftover (FI #2) | unreachable from core | none | n/a | 3 | 1 | F3 | **OPEN.** Recorded |
| DR3-14 | dashboard / core | dashboard plan (no deploy note); core `quality.py` "Deploy order" | Dashboard half deploys after core's provisioning run | (unstated) | old core + new dashboard → "Failed" flat 0 under copy that says failures count | none | n/a | 3 | 1 | F3 | **OPEN.** P3-3 |
| DR3-15 | dashboard | `65f588d`, `4a7714a` | Green at their own HEAD | — | full lane 2654/0/2; analytics 66; `tsc` 0; lint clean | the lane | n/a | 3 | 0 | F2 | **SETTLED** |
| DR3-16 | dashboard | `2a9b0f4` | Seven r2 P3s closed | r2 packet | sub-review: 33 mutants, 28 killed, 5 survived (full auth lane), 0 broke; `tsc` 0; lint clean on 14 files | r2 guards + new ones | see DR3-2a | 3 | 0 | F2 | **SETTLED** as a closure (rows DR3-2a-01..21) |
| DR3-17 | dashboard | `4a7714a` plan file | "63 → 66", "Prettier unclean at HEAD too", 422 census | — | 63 at `09bacba` and 66 at `4a7714a` (runtime); `prettier --check` exit 1 at both | n/a | n/a | 3 | 0 | F3 | **SETTLED** ("13 mutants all red" consistent, not re-run) |
| DR3-18 | dashboard / core | `analytics-panel-registry.ts:305`; core `b2d67f2` | Unknown defined as "no verdict" | copy predates `b2d67f2` | core's `unknown` now also counts an out-of-vocabulary verdict | none | n/a | 3 | 1 | F3 | **OPEN.** P3-7 |

### Sub-review of `2a9b0f4` (Opus; final)

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR3-2a-01 | dashboard | `InviteAcceptView.tsx:209-221`; test `invite-accept-retry-hydrated.test.ts:397-413` | Try again only for `unreachable`; the guard reads a real token and drives expired/revoked/invalid/accepted | P3-2 | preview read asserted per status | same | **yes.** M13 red | 1 | 0 | F1 | **SETTLED** (closes DR2-11) |
| DR3-2a-02 | dashboard | `lib/auth/invite-token-hold.ts:49-57`; `invite-token-hold.test.ts:37-47`; accept test `:415-428` | A token in the address wins over the held one | P3-3 | unit test + mounted remount onto a newer token | both | **yes.** M09 red, 3 tests | 2 | 0 | F1 | **SETTLED** (closes DR2-09) |
| DR3-2a-03 | dashboard | `hooks/auth/useHeldInviteToken.ts:56-62` | `hashchange` re-reads, re-holds and re-strips a pasted `#token=` | DR2-31: the router ignores a null-state popstate (`app-router.js:451`) | listener removal and no-strip both red | accept test `:430-450` | **partly.** R3M-hashraw SURVIVES the full lane | 2 | 1 | F1 | **PARTIAL** (closes DR2-31's behaviour; F1 open) |
| DR3-2a-04 | dashboard | same hook; `use-route-telemetry.ts:30-60` | The re-held token reaches no URL, storage, telemetry, product event, console or server | new seat | memory + POST body only; router strip; pathname-only telemetry | accept test `:448`, storage/cookie scan `:352-372` | M08, M07 red; no leak mutant survives | 0 | 1 | F1 | **ASSERTED** (source-read + address-bar test) |
| DR3-2a-05 | dashboard | `lib/auth/PermissionContext.tsx:102-154` | Body validated all the way down; refused as a whole | P3-4 | 12 probes + mounted refusal; matches core DDL | `permissions-endpoint.test.tsx:137-216` | **yes.** P4a (string list), P4b (any record as role), P4c (elements unchecked) red | 2 | 0 | F1 | **SETTLED** (closes DR2-26) |
| DR3-2a-06 | dashboard | `PermissionContext.tsx:331-333`, `:356-362` | A refusal is silent to the UI; a later malformed refresh keeps the previous permissions | fail-closed | `error` null, `loading` false, `tenantId ''` on first load; stale state kept on refresh | mounted refusal test `:204` (first load only) | n/a | 3 | 2 | F1 | **OPEN** (F5) |
| DR3-2a-07 | dashboard | `permissions-endpoint.test.tsx:292-351` | The /test-cookie scan walks the repo root minus 9 non-source dirs and proves it reached `middleware.ts` and `constants/index.ts` | P3-5 | pruned dirs hold no shipped source | same | **yes.** M22, M23 red | 1 | 0 | F1 | **SETTLED** for ts/tsx/js/jsx/mjs/cjs/json (closes DR2-27) |
| DR3-2a-08 | dashboard | `permissions-endpoint.test.tsx:311` | Extension list omits `.mts`/`.cts` | — | 3 `.mts` scripts in `scripts/` (confirmed) | same | **yes, and it survives.** R3M-mts passes the full lane | 2 | 1 | F1 | **OPEN** (F4) |
| DR3-2a-09 | dashboard | `adReviewPresentation.ts:305,329`; test `:867-887` | Every shared category has a page row or is on `MATERIALIZE_SHARED_COPY_NAMES_NO_CONTROL` | P3-5 | a new category fails until decided | `ad-review-materialize.test.ts:867` | **yes.** M25, M25r red (AD file alone) | 1 | 0 | F1 | **SETTLED** (closes DR2-19's new-category half) |
| DR3-2a-10 | dashboard | `adReviewPresentation.ts:329`; test `:890-935` | A cleared category's copy is trusted by name; the backstop matches a fixed verb list | P3-5 | "Turn … off / use Run now" not derived | same | **yes, and they survive.** allowlist-lie-verbless, internal-reworded pass the full lane; allowlist-lie-open red | 1 | 1 | F1 | **PARTIAL** (F2) |
| DR3-2a-11 | dashboard | accept test `:367-370` | Storage scan covers cookies | P3-6 | — | same | **yes.** M08 red | 2 | 0 | F1 | **SETTLED** (closes DR2-08) |
| DR3-2a-12 | dashboard | `placementOutcome.ts:108-111` | Forget the token and note on APPLIED, in the decision both surfaces share | P3-6 | seam unit + mounted `/invite`; `/register` activation cannot be mounted | `invite-token-hold.test.ts:69-99`, accept test `:452-470` | **yes.** M10 red (2); M11 red (5) | 3 | 0 | F1 | **SETTLED** at the seam; **ASSERTED** for mounted `/register` (closes DR2-10) |
| DR3-2a-13 | dashboard | `useInvitationPreview.ts:70-75` | One funnel record per token per attempt | P3-6 | failure then success recorded | `auth-flow-sites.test.tsx:367-388` | **yes.** token-only key red; M14 red | 2 | 0 | F3 | **SETTLED** (closes DR2-13) |
| DR3-2a-14 | dashboard | `useInvitationPreview.ts:57,72`; test `auth-flow-sites.test.tsx:390-400` | "Strict Mode's second run records nothing" | — | mount runs with token `''`; the token run is a single update | same | **yes, and it survives.** R3M-funnel-every-run passes the full lane | 2 | 1 | F3 | **REFUTED** as tested (F3) |
| DR3-2a-15 | dashboard | `RegisterView.tsx:564,584` | `reopen` no longer offers the uninvited signup; dead links keep it | P3-6 | — | `invite-register-hydrated.test.ts:381,432` | **yes.** restoring it goes red | 2 | 0 | F1 | **SETTLED** (closes DR2-14) |
| DR3-2a-16 | dashboard | `useHeldInviteToken.ts:49` | `scroll:false` pinned on both pages | P3-6 | — | both "strip goes through the router" tests | **yes.** M05 red ×2 | 3 | 0 | F1 | **SETTLED** |
| DR3-2a-17 | dashboard | `RegisterView.tsx:100-104`; `invite-register-hydrated.test.ts:401-404` | A query rewrite does NOT remount; Back and a boundary reset do | P3-7 | `layout-router.js:396-405,472`; `create-router-cache-key.js:20-22` | n/a | n/a | 3 | 1 | F3 | **SETTLED** by source-read (closes DR2-15) |
| DR3-2a-18 | dashboard | `invite-token-hold.ts:16-23`; hook doc | P3-1 declared, not fixed; `history.state` recorded as a future improvement | P3-1 | `fetch-server-response.js:139-146,156-157,163-176` match the prose | none (no browser) | n/a | 2 (functional) | 1 | F1 | **OPEN by design** (DR2-07 stays open; declaration accurate) |
| DR3-2a-19 | dashboard | `useHeldInviteToken.ts`; both pages | Refactor preserves read→hold→strip order, the Strict Mode ref and the router options | — | M01, M02, M06, M07, M14, M16, M17, M18, M32/M33, M11, M12 all red | r2 guards | **yes** | 0 | 0 | F2 | **SETTLED** (DR2-01, 02, 04, 05, 06, 08, 12 still hold) |
| DR3-2a-20 | dashboard | `InviteAcceptView.tsx:93,230,385`; `RegisterView.tsx:105,940` | A pasted link does not reset per-invitation state | new seat | probes: A's refusal and "You're in" persist over B; `/register` confirmation switches the activation token (source-read, confirmed here) | none | probe passes (defect real) | 2 (functional) | 1 | F3 | **OPEN** (F6) |
| DR3-2a-21 | dashboard | `2a9b0f4` | Green at HEAD | — | domain lane 306/306; `tsc` exit 0; `next lint` clean on 14 files | lane | n/a | 3 | 0 | F2 | **SETTLED** for the domain lanes (full lane at `4a7714a`, which contains it) |

**r2 rows after this range:** closed DR2-08, 09, 10, 11, 13, 14, 15, 26, 27 and DR2-31 (behaviour); partial DR2-19 (F2);
open by design DR2-07; re-confirmed settled DR2-01, 02, 04, 05, 06, 12.

---

## Open claims, tier 2 first

**Tier 2:** DR3-2a-06 (F5 — a refused permissions body is silent and a malformed refresh keeps stale permissions; RBAC
surface, fail-closed). Carried, unchanged by this range: B2-35 (M-TURNCARD unbuilt) and B2-43 (tenant-less `llmTurns` key).

**Tier 1, open:** DR3-04 (**P2-1**) · DR3-03 (P3-1) · DR3-08 (P3-2) · DR3-14 (P3-3) · DR3-09 (P3-4) · DR3-10 (P3-5) ·
DR3-07 / DR3-11 (P3-6; narrow screen: keep + pin) · DR3-18 (P3-7) · DR3-13 (recorded) · DR3-2a-03 (F1) · DR3-2a-08 (F4) ·
DR3-2a-10 (F2) · DR3-2a-14 (F3) · DR3-2a-18 (DR2-07 by design) · DR3-2a-20 (F6).

**Tier 0, settled:** DR3-01, 02, 05, 06, 15, 16, 17; DR3-2a-01, 02, 05, 07, 09, 11, 12, 13, 15, 16, 19, 21.

---

## Final sweep — the dashboard side of every plan item that names it, from the code at `4a7714a`

The master plan is edited live; items are cited by id, not line.

| item | dashboard side | state | evidence |
|---|---|---|---|
| G.22 (M-RUNERROR copy) | `runErrorAttribute` + category copy | DONE | `runOutcomeCopy.ts`, `RunHistoryPanel.tsx`, `AutomationNotificationRow.tsx`, `adReviewPresentation.ts` |
| G.36(d) | bell reads `payload.error`; prototype-safe badge and routes | DONE | `AutomationNotificationRow.tsx:247`; `department-routes.ts:33` `Object.create(null)`; `RunStatusBadge.tsx:77-83` `metaFor` reads via `hasOwnProperty` (read-side guard) |
| G.56 | prototype-lookup census guard | DONE | `tests/unit/lookups/prototype-lookup-tables.test.ts` |
| G.58 / M-RUN-REASON | `runReasonAttribute` at both DOM sites + visible copy | DONE | `RunHistoryPanel.tsx:210`, `AutomationNotificationRow.tsx:277`, `adReviewPresentation.ts:370` |
| G.77(a) / M-CHART-CELL | table cell via `Object.hasOwn` | DONE | `ChartCard.tsx:895`; `chart-card-table-cell.test.tsx` |
| G.94 / G.64(a) | trigger vocabulary incl. `one_shot` + contract | DONE | `automations-api.ts:93`; `contracts/automation-run-triggers.json` |
| G.64(c) | capability sentence carries no count | DONE | `PermissionContext.tsx:484` |
| G.83(a) | one-shot sentences | DONE | `runOutcomeCopy.ts:250` |
| G.32 / M-FACTS-FAILURES | series + copy | **PARTIAL** | `65f588d`; P2-1 (three copies), P3-3 (deploy order), P3-7 |
| G.34 / M-FACTS-ANONYMISE | copy for the changed panels | **PARTIAL** | `65f588d`; P3-4 (`deleted-user` raw), P3-5 |
| M-FACT-LIMITS | none ("no code change") | N/A | — |
| M-INVITE-FRAGMENT | fragment link, marker hand-off, hold, strip, hashchange | DONE; residues F1, F6, DR2-07 | `0f87aec`, `49f6231`, `09bacba`, `2a9b0f4` |
| M-PERMISSIONS-ENDPOINT | `GET /auth/permissions` body, deep-validated | DONE; residues F4, F5 | `e3a4610`, `2a9b0f4` |
| M-FALLBACK | three-valued `DashboardOffer` | DONE; B2-36..38 owner-owed | B2 re-statement |
| M-COMMIT | dashboard production files committed | DONE | `afd6300` |
| M-TURNCARD | server refusal is copilot-mro's | **OPEN — no batch ever briefed**; B2-35's dashboard residue stands (`notInternal` at `improvement/page.tsx:181` unchanged, `gcTime` 5 min at `query-client.ts:26`) | read |
| G.54 (closed `[x]`) | records "`dashboard-obsm` has no TS depth or layout guard at all" as an unfixed side finding; assigns no work | **OPEN — never briefed** | 48 test files flat in `tests/unit/`; no `tests/unit/infra/` layout guard or `_root` helper, contrary to the workspace CLAUDE.md's "every repo carries `test_test_layout_rules.py`" |
| G.1, G.47, G.52, G.65, G.73, G.91 | cite the dashboard as a cross-repo reference or a Grafana `service.name`; no dashboard-repo work | N/A | read |
| B2 re-statement rows that are dashboard work no batch was briefed for | B2-4/21, 12, 17, 20, 29, 30, 38, 39, 40, 41, 42, 43, 44, 45 | **OPEN — none briefed**; this range touched none of their files | B2 re-statement + `git diff --stat 09bacba..4a7714a` |
