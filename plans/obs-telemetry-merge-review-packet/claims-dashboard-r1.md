# Claims packet: dashboard r1 (G.58, G.58 follow-up, G.77(a), M-INVITE-FRAGMENT dashboard half)

This is an independent adversarial review (Opus), done 2026-09-21. It is read-only throughout. Each
commit was taken with `git archive <sha>` into the private scratch directory
`scratchpad/dash-review-r1/`, with `node_modules` symlinked from `dashboard-obsm`. Every mutation ran
against a second archived copy (`m-<sha>/`). After each run the file was restored from a backup copy
and md5-checked against the committed blob; all 37 runs came back identical. No real tree was edited,
checked out or committed. There was no `next build`, no e2e run, no browser and no live stack.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `5265cbc~1..0f87aec` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | `5265cbc` G.58 / M-RUN-REASON · `951fdc4` G.77(a) / M-CHART-CELL · `a46c7dc` G.58 follow-up · `0f87aec` M-INVITE-FRAGMENT (dashboard half) |

The implementer kept committing during this review. HEAD moved to `49f6231`, then to `6c1ad81`, and
both are outside the range. Everything below is measured at the four SHAs above.

## How it was run

- **Lane:** `tsx --tsconfig tsconfig.test.json --test --test-concurrency=2 "tests/unit/**/*.test.ts?(x)"`, with `NODE_OPTIONS=--max-old-space-size=2048`, run at each commit's own tree.
- **Typecheck:** `tsc --noEmit`.
- **Lint:** `next lint --file <each touched .ts/.tsx>`. `next lint` only.
- **Exit status:** each runner's own exit status was captured (`pipefail`).

| commit | unit (tests / pass / fail / skipped) | unit exit | tsc exit | next lint (touched files) |
|---|---|---|---|---|
| `5265cbc` | 2584 / 2582 / 0 / 2 | 0 | 0 | clean |
| `951fdc4` | 2589 / 2587 / 0 / 2 | 0 | 0 | clean |
| `a46c7dc` | 2594 / 2592 / 0 / 2 | 0 | 0 | clean |
| `0f87aec` | 2607 / 2605 / 0 / 2 | 0 | 0 | clean |

All four commits are green at their own HEAD, and the counts match the commit messages' test counts.

**Mutation harness.** Each run follows the same steps:

1. Apply a `perl -0pi` edit.
2. Confirm it with a grep and an md5 change.
3. Run the domain test set.
4. Restore from the backup copy.
5. md5-check against `git show <sha>:<path>`.

There were 37 runs in total: 33 mutants, 1 equivalence control, and 3 baselines. **Of the 33 mutants, 30 went red and 3 survived** (A11, D7, D13).

---

## Findings, ranked

### No P0. Nothing ships server text into the DOM or a secret into a URL that this range claims to close.

All four surfaces were traced end to end:

- the run history's line and attribute;
- the bell's missed-run row, including the announcer's `message`;
- the AD review note;
- the chart table cell;
- the invite page's reads and writes.

Also traced were the telemetry exit scrub (`lib/telemetry/scrub.ts` removes the query and fragment of
every first-party URL at the exporter), product events (route pattern only, and anonymous events are
dropped), error boundaries (message shown in development only), and production console
(`removeConsole`). There was no leak on any path the range touches.

### No P1.

---

### P2-1: After the strip, reload and Back on `/invite` show "This invitation link does not work"; the `unreachable` notice's own remedy now leads there

- **Where:** `components/features/auth/InviteAcceptView.tsx:87-99`, `lib/auth/invite-status.ts:79-82`, `0f87aec`.
- **What changed:** after the strip, the token lives only in React state. Any fresh mount of the view
  reads the stripped address, so `token === ''` and it renders the `invalid` notice (`:188-191`).
  Before this commit, the token stayed in the bar and a remount re-read it.
- **Scenario A, a failed preview:**
  1. The preview hits a transient failure (5xx, 429, or a dropped connection).
  2. The page shows `unreachable`: *"This is a problem on our side, not with your link — try again in
     a moment."*
  3. `InviteMessage` offers no retry button, so the invitee's only "try again" is F5.
  4. After F5 the page says *"This invitation link does not work … ask whoever invited you to send a
     new one."* That is the exact misdirection the `unreachable` copy was written to prevent
     (`invite-status.ts:36-40`).
- **Scenario B, Back from signup:** the invitee clicks Accept, lands on `/register`, and presses Back.
  The popstate remount lands on the stripped `/invite`, which renders the same dead-link verdict.
- **Scenario C:** the error boundary's "Try again" also remounts the view, with the same result.
- **Evidence:** the commit's own test (`invite-accept-retry-hydrated.test.ts`, "an absent or blank
  token shows the dead-link message") mounts `/invite` and asserts the `invalid` title. `/invite` is
  exactly the post-strip address.
- **Fix, smallest first:**
  - Give the `unreachable` state a Try again button that re-runs the preview from the in-memory token,
    and change its copy to "open the link from your email again" for the reload case.
  - Or carry the token in the entry's `history.state`. That is never sent to a server and survives
    reload and Back, but Next's `HistoryUpdater` rewrites `history.state` on every router state, so it
    needs a test.
- The owner's ruling mandates the strip. It does not mandate the dead end.

### P3-1: The pass-through `history.state` opts out of Next's router sync, so the router keeps the token in memory

- **Where:** `InviteAcceptView.tsx:95`, `0f87aec`.
- **What happens:**
  - `window.history.state` carries `__NA: true`, written by Next's `HistoryUpdater`
    (`node_modules/next/dist/client/components/app-router.js:92-99`).
  - Next 15.2.4's patched `replaceState` treats `__NA` as its own internal call and returns before
    `applyUrlFromHistoryPushReplace` (`app-router.js:435-439`).
  - The router's `canonicalUrl` was read from `location` *including the hash*
    (`router-reducer/create-initial-router-state.js:41-43`).
  - So after the strip, the router still holds `/invite#token=…` (or `?token=…`) in memory.
- **Today it is latent:** nothing on `/invite` dispatches a state-changing router action. The
  prefetch reducer returns the same state.
- **If a later change adds an action on `/invite`:**
  - `HistoryUpdater`'s insertion effect writes `canonicalUrl` back into the address bar and history (`app-router.js:101-110`).
  - For a legacy link, a `router.refresh()` would also fetch `?token=` in an `_rsc` URL.
  - A `useSearchParams()` consumer on the page would still see `token`.
- **Why passing `null` is not a safe swap:** Next's documented form `replaceState(null, '', url)`
  would sync, because the patch copies `__NA` and the tree itself
  (`copyNextJsInternalHistoryState`, `:173-186`). But the patch is installed by a *parent* effect. If
  the view's effect ever runs first, a `null` state loses `__NA`, and popstate then does nothing
  (`:452-454`).
- **Neither choice is pinned:** mutant D7 (`window.history.state` → `null`) survives the whole auth
  lane.
- Source-read against the installed Next; not run in a browser.

### P3-2: Three guards do not hold the property they sit beside (surviving mutants)

- **D7:** covered in P3-1. The `history.state` decision is unguarded in both directions.
- **D13:** `if (token === '')` → `if (!token)` passes all 244 auth-lane tests.
  - Effect: the server HTML and the first paint (`token === null`) would show *"This invitation link
    does not work"* to every invitee until the effect runs.
  - No test asserts that the pre-read render is the "Checking your invitation…" state. That split
    between "no token yet" and "no token" is the design point the view's doc comment makes
    (`InviteAcceptView.tsx:78-86`).
- **A11:** loosening `RUN_REASON_TOKEN` to `/^[\p{Ll}\p{Nd}_]{1,64}$/u` passes all 328
  automations/notifications tests.
  - The shared fixture (`tests/fixtures/automations/run-reason-attribute.ts`) has no non-ASCII row.
  - The committed ASCII gate is correct. A probe confirms it: Cyrillic `с`, fullwidth `ｇ`, ZWSP,
    U+2028 and NUL all give the sentinel and the fixed sentence.
  - But the lock does not pin it. One lookalike row would.

### P3-3: No deploy order for M-INVITE-FRAGMENT is gap-free as the three halves are cut

- The dashboard has no GET fallback, by ruling.
- Core `66b0217` ships the POST route **and** the `#token=` email composer in one commit.
- The gateway's POST skip-auth is api `8d7f587`.
- **Dashboard first:** the old gateway 401s the POST, so every invitee sees "We could not check this
  invitation".
- **Core first:** invitations minted before the dashboard lands carry `#token=`. The old dashboard
  reads only `useSearchParams().get('token')`, so they read "does not work".
- **So:** gateway, then core, then dashboard must land back to back, or the composer change must be
  held until the dashboard is live. This belongs in the deploy runbook. It is not a code defect in
  this range.

### P3-4: Out of range, and pre-existing. The AD review note still carries server-written text on two paths the commit did not touch

- **Where:** `adReviewPresentation.ts:455-459` and `:507`.
- **The `unreadable` note:** it renders `asSentence(outcome.reason)`, where `reason` is the status
  route's transport message (`useAdReview.ts:557/573`). That message is the server's `detail` up to
  300 characters (`lib/api/fetch-utils.ts:35-38`).
- **The `default:` ending:** it quotes `runStatus` verbatim.
- Neither is a run `reason`/`error` column, so G.58's claim ("never either value as text") holds as
  written. But this is server text in the same note. Whether a 5xx `detail` can carry exception text
  is a backend question for the status route.

### Context for the known-open item (not a finding)

The Accept `<Link href="/register?invite=<token>">` (`InviteAcceptView.tsx:354, 450`) uses the
default App Router prefetch. In production it is prefetched on **viewport**, so
`/register?invite=<token>&_rsc=…` is requested when the page is **viewed**, not only when Accept is
clicked. The controller's `/register?invite=1#token=…` plan closes that too, because fetches never
carry a fragment.

---

## What I tried to break and could not

- **Server text into the DOM, run history and bell.**
  - Every row of the shared fixture, plus these probes, gives either the token itself or the
    `unrecognised` sentinel on the attribute, and a token echo or the fixed sentence in the prose:
    Cyrillic/fullwidth lookalikes, ZWSP, U+2028, NUL, `psycopg2.errors.UndefinedTable`, 64/65
    characters, uppercase, `___`, `__proto__`, `constructor`, the sentinel itself, and NBSP/BOM around
    a token.
  - Adding the `m` flag (A4) goes red, because the inner-newline row catches `^…$` matching line by
    line.
  - The bell's `announced` sentence comes from `missed_run_message`
    (`api-obsm/flynapse_api/automations/announcements.py:168-205`), which is built only from closed
    tables plus the automation's name.
  - The `disabled` body is `_disabled_message` (`executor.py:182`), which is also closed.
- **AD review materialise note.** An exception in either column, across four statuses, never reaches
  the note. Three bypass mutants (B2 raw error, B3 raw reason, B4 any reason) each go red, and the
  test anchors its negatives to positive "does not recognise" / "could not read" sentences.
- **Other run surfaces.** `AutomationsTable` renders no reason. `ImprovementRunHistory` renders
  `stage.error` / `errors`, but copilot-mro writes those as `type(exc).__name__` only
  (`improvement/runner.py:639/703/737/766/811`). Telemetry `run_settled` carries `terminal_status` only.
- **Chart cell.** No other row's or series' value can render in a cell:
  - `cellText` gates on `Object.hasOwn`, which also blocks values inherited through a row whose own
    `__proto__` was assigned.
  - The series and categorical builders write own properties only, and the heatmap grid uses a `Map`.
  - C1 (bare read) and C2 (`in`) go red. C3 (`hasOwnProperty.call`, the equivalent) stays green, as a
    control should.
- **Where the invite token can travel.**
  - The preview is POST-body only, with no GET: D9 and D10 go red.
  - The telemetry exit scrub strips query and fragment from every span/log string. The page test
    asserts no request URL carries the token.
  - `logger.warn` carries only a status or a fetch error.
  - `Referrer-Policy` has no competing setter: none in `next.config.mjs`, a root layout `<meta>`,
    `amplify.yml` or `iac`.
- **Reading the token.** Fragment-wins, strip-both, trim, encoded values, a blank token, and other
  parameters being preserved are all mutation-proved (D1–D6). D8 (no ref guard) goes red through the
  Strict Mode telemetry test. React keeps refs across Strict Mode's simulated remount, so the design
  holds there.
- **`Referrer-Policy`.** It is set on `/invite` and on `/register?invite=` both signed in and out, and
  not on `/login` or `/register` (D11, D12). For a `#token=` link no Referer can carry it anyway,
  because browsers strip fragments from referrers.
- **Edge inputs, all benign or contrived:**
  - `?token=A#token=` gives an empty token, so the blank fragment beats a valid query.
  - `#section` is rewritten to `#section=`.
  - `?utm=a%20b` is re-encoded as `a+b`.
  - `#Token=` is neither read nor stripped.

## What I did not test

- **Any browser, Next runtime or live stack.** P3-1's router retention is read from the installed
  `next@15.2.4` source, not observed. The P2-1 scenarios are reasoned from the view's code plus the
  committed `/invite` → `invalid` test, not driven in a browser.
- **Chat SSE/stream error rendering, and every `unavailable` panel** that renders the transport's
  `detail`. Outside G.58's scope.
- **Core `66b0217` and api `8d7f587`,** beyond reading them for the deploy-coupling question.
- **The implementer's follow-up commits** after `0f87aec` (`49f6231`, `6c1ad81`).
- **The e2e spec change** (`tests/e2e/playwright/invite_accept.spec.ts`), which was not run, by ban.

---

## Claims table

**Severity** is this reviewer's scale: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process. A functional regression has no slot, so it takes the nearest one and is marked.

**Tier** is §2.3a's scale: 0 = a mutation-checked guard proves it; 1 = consequential but reversible; 2 = irreversible or estate-shaping.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR1-01 | dashboard | `components/features/automations/runOutcomeCopy.ts:455`, `:474-478` | `data-run-reason` carries the token when `/^[a-z0-9_]{1,64}$/` matches the TRIMMED reason, the `unrecognised` sentinel when a reason is present but does not match, and nothing when it is absent | Owner ruling M-RUN-REASON: the column is open to any exception's `.reason` | The fixture table (16 rows) runs through the helper, the run history and the bell; a probe covered lookalikes, ZWSP, U+2028, NUL and dotted exceptions | `runOutcomeCopy.test.tsx`, `automationMissedNotificationRow.test.tsx` (the `RUN_REASON_ATTRIBUTE_ROWS` table) | **yes.** A1 `{1,65}`, A2 no `^`, A3 no `$`, A4 `m` flag, A5 uppercase, A6 bypass, A9 untrimmed and A10 space/dot/colon class all go red | 0 | 0 | F1 | **SETTLED** |
| DR1-02 | dashboard | `RunHistoryPanel.tsx:210`; `AutomationNotificationRow.tsx:277` | Both attribute sites call the one helper | One gate, two views of one firing | Tests render both surfaces from the shared table | same | **yes.** A7 (panel raw) and A8 (bell raw) each go red | 0 | 0 | F1 | **SETTLED** |
| DR1-03 | dashboard | `runOutcomeCopy.ts:455` (fixture `tests/fixtures/automations/run-reason-attribute.ts`) | The gate is ASCII-only | Free text cannot be snake_case ASCII | The probe gives the sentinel for Cyrillic/fullwidth input | none for the non-ASCII edge | **yes, and it survives.** A11 `[\p{Ll}\p{Nd}_]/u` passes 328/328 | 2 | 1 | F1 | **PARTIAL.** The code is right; one lookalike row would pin it (P3-2) |
| DR1-04 | dashboard | `runOutcomeCopy.ts:499-500`, `:589-598` | Step 3 echoes only a token-shaped unknown reason. Anything else, including `___`, which humanises to nothing, gets a fixed sentence. `MAX_ECHOED_REASON` is deleted | A prefix of exception text is still exception text | "non-token reasons all give one identical sentence…", "the prose gate and the attribute gate agree" | `runOutcomeCopy.test.tsx` | **yes.** B1 (ungated echo), B7 (`___` echoes) and B9 (`\w` prose regex) all go red | 0 | 0 | F1 | **SETTLED** |
| DR1-05 | dashboard | `components/features/mro/ad-review/adReviewPresentation.ts:306-325` | The AD note uses category copy (scheduleless wording), then a token reason, then a fixed sentence, and never stored text; the timed-out note has no detail | Both columns can hold exception text | An exception in either column, across 4 statuses, is absent from the note, anchored to positive sentences | `tests/unit/mro/ad-review-materialize.test.ts` | **yes.** B2 raw error, B3 raw reason, B4 any reason and B6 schedule wording all go red | 0 | 0 | F1 | **SETTLED** |
| DR1-06 | dashboard | `adReviewPresentation.ts:455-459`, `:507` | Not taken (pre-existing): the `unreadable` note quotes the transport's `detail`, and the default ending quotes `runStatus` | Outside the run columns | `useAdReview.ts:557/573`; `fetch-utils.ts:35-38` (≤300-character server `detail`) | none | not recorded | 3 | 1 | F3 | **OPEN.** P3-4; the backend must say whether a 5xx `detail` can carry exception text |
| DR1-07 | dashboard | `components/features/chat/ChartCard.tsx:894-895`, `:920` | The table cell reads the row's OWN value via `Object.hasOwn`; rows and the chart dataset are untouched | Owner ruling M-CHART-CELL | `constructor`/`toString`/`__proto__`/`hasOwnProperty`, absent and present, from `JSON.parse` own keys | `tests/unit/chat/chart-card-table-cell.test.tsx` | **yes.** C1 (bare read) and C2 (`in`) go red; C3 (the equivalent `hasOwnProperty.call`) stays green, as a control should | 0 | 0 | F2 | **SETTLED** |
| DR1-08 | dashboard | `tests/unit/lookups/prototype-lookup-tables.test.ts:66-70` | The census entry `ChartCard.tsx::row` moves from PENDING to CLOSED AT THE READ | The scan cannot see a read-site gate | It names the ruling and the pinning test | the census itself | n/a (doc row) | 3 | 0 | F3 | **SETTLED** (doc) |
| DR1-09 | dashboard | `lib/auth/invite-token.ts:45-57` | Read `#token=`, falling back to `?token=`; the fragment wins; strip both, keep other parameters; decode once, then trim; return `strippedUrl: null` when there is no token key | M-INVITE-FRAGMENT: the secret leaves URLs | 7 reader tests | `tests/unit/auth/invite-token.test.ts` | **yes.** D1 (no fragment), D2 (order swap), D3 (no trim), D4 (keep query) and D5 (keep fragment) all go red | 0 | 0 | F1 | **SETTLED** |
| DR1-10 | dashboard | `components/features/auth/InviteAcceptView.tsx:87-99` | Read once in a mounted effect, strip with `replaceState`, and keep a ref guard for Strict Mode | The fragment exists only in the browser | The page tests cover the fragment and query paths, the bar being emptied, and Strict Mode giving one preview | `invite-accept-retry-hydrated.test.ts`, `auth-flow-sites.test.tsx` | **yes.** D6 (no strip) and D8 (no ref guard) go red | 0 | 0 | F1 | **SETTLED** |
| DR1-11 | dashboard | `InviteAcceptView.tsx:95` | `replaceState(window.history.state, …)`, the router's state passed through | "The router keeps its own entry there" | `__NA` makes Next's patch skip `applyUrlFromHistoryPushReplace` (`app-router.js:435-439`); `canonicalUrl` keeps `#token=` (`create-initial-router-state.js:41-43`) | none | **yes, and it survives.** D7 (`null` state) passes 244/244 | 1 | 1 | F1 | **OPEN.** P3-1: latent token in router memory; the choice is unpinned in both directions |
| DR1-12 | dashboard | `InviteAcceptView.tsx:188-204` | "No token yet" (`null`) renders "Checking…"; "no token" (`''`) renders the dead-link notice | The server renders without the fragment | Covered only after the effect has run | none for the pre-read render | **yes, and it survives.** D13 (`!token`) passes 244/244 | 2 | 1 | F1 | **OPEN.** P3-2: a mutation would flash "does not work" in the server HTML |
| DR1-13 | dashboard | `InviteAcceptView.tsx:87-99`; `lib/auth/invite-status.ts:79-82` | Not taken: the token survives only in React state, so reload, Back and error-boundary reset render `invalid` | Consequence of strip-once | The committed test mounts `/invite` and gets `invalid`; the `unreachable` copy says "try again in a moment" with no retry control | none | not recorded | 2 (functional regression; nearest slot) | 1 | F1 | **OPEN.** P2-1 |
| DR1-14 | dashboard | `lib/api/invitations-api.ts:254-264` | The preview is `POST /invitations/preview` with `{token}` in the body, at the exact path, with no GET fallback | The body never reaches access logs | The transport test covers the method, the exact URL, no `?`, and the body; the page test says no request URL carries the token | `tests/unit/tenancy/invitation-writes.test.ts`, `invite-accept-retry-hydrated.test.ts` | **yes.** D9 (revert to GET+query) and D10 (POST plus query) go red | 0 | 0 | F1 | **SETTLED** |
| DR1-15 | dashboard | `middleware.ts:92-105` | `Referrer-Policy: no-referrer` on `/invite` and `/register?invite=` (signed in or out), and nowhere else | The legacy `?token=` page's early subresources, and `/register?invite=` for the whole of signup | No competing setter in `next.config.mjs`, a layout `<meta>`, `amplify.yml` or `iac` | `tests/unit/auth/invite-middleware-bounce.test.ts` | **yes.** D11 (`/invite` only) and D12 (everywhere) go red | 0 | 0 | F1 | **SETTLED** |
| DR1-16 | dashboard / core / api | `invitations-api.ts:254-264`; core `66b0217` `invitation_email_composer.py`; api `8d7f587` `middleware/auth.py:754-757` | No GET fallback (ruled), while core ships the route and the `#token=` composer together | — | Either deploy order leaves a window of broken invitations | none | n/a | 3 | 1 | F3 | **OPEN.** P3-3: runbook order gateway → core → dashboard back to back, or hold the composer |
| DR1-17 | dashboard | `app/(auth)/invite/page.tsx:1-19` | The Suspense boundary is removed | `useSearchParams` is no longer called | `next lint` clean and `tsc` clean; `next build` was not run, by ban | none | not recorded | 2 | 1 | F2 | **ASSERTED.** The static-render claim is unverified without a build |

---

## Open claims, tier 2 first

**Tier 2:** none. None of the open rows changes a signal contract, content capture under the opt-out
flag, RBAC or tenancy.

**Tier 1, open**

1. **DR1-13 (P2-1).** Reload, Back and error-boundary reset on `/invite` render the dead-link verdict.
   The `unreachable` notice's only remedy (reload) now lands there. Fix it with a retry control on
   `unreachable` plus copy for the reload case, or by carrying the token in `history.state` under a
   test.
2. **DR1-11 (P3-1).** Passing `__NA` history state skips Next's router sync, so `canonicalUrl` keeps
   the token in memory. The decision is unpinned (D7 survives).
3. **DR1-12 (P3-2).** The pre-read render is unguarded (D13 survives).
4. **DR1-03 (P3-2).** Add one non-ASCII lookalike row to the shared run-reason fixture (A11 survives).
5. **DR1-06 (P3-4).** The AD `unreadable` note quotes the transport `detail`. Pre-existing and out of
   range.
6. **DR1-16 (P3-3).** The deploy order for the three halves.
7. **DR1-17.** The Suspense removal is unverified without a build.

**Tier 0, settled:** DR1-01, 02, 04, 05, 07, 08, 09, 10, 14 and 15.
