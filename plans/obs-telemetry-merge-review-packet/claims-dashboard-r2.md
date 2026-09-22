# Claims packet: dashboard r2 (M-INVITE-FRAGMENT hand-off, AD page copy, M-PERMISSIONS-ENDPOINT, review r1 fixes)

This is an independent adversarial review (Opus), done 2026-09-21. It is read-only throughout. Each
commit was taken with `git archive <sha>` into the private scratch directory
`scratchpad/dash-review-r2/`, with `node_modules` symlinked from `dashboard-obsm` (itself a link to
`dashboard/node_modules`, Next `15.2.4`). Every mutation ran against a separate archived copy of
`09bacba` (`mut/`) through a runner that applies the edit, confirms it, runs the named test files,
restores the file and md5-checks it against `git show 09bacba:<path>` (a file the mutant created is
checked for absence). After the last run, `git archive 09bacba | tar -d -C mut/` reported no content
difference. No real tree was edited, checked out or committed; `dashboard-obsm` is still clean at
`09bacba`. There was no `next build`, no e2e run, no browser and no live stack.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `0f87aec..09bacba` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | `49f6231` M-INVITE-FRAGMENT hand-off (B10) · `6c1ad81` AD page copy · `e3a4610` M-PERMISSIONS-ENDPOINT dashboard half (B11) · `09bacba` review r1 fixes |

## How it was run

- **Lane:** `tsx --tsconfig tsconfig.test.json --test --test-concurrency=2 "tests/unit/**/*.test.ts?(x)"`, at each commit's own tree.
- **Typecheck:** `tsc --noEmit`.
- **Lint:** `next lint --file <each .ts/.tsx the commit touched>`. `next lint` only.
- **Exit status:** each runner's own exit status was captured (`pipefail`, `PIPESTATUS`).

| commit | unit (tests / pass / fail / skipped) | unit exit | tsc exit | next lint (touched files) |
|---|---|---|---|---|
| `49f6231` | 2617 / 2615 / 0 / 2 | 0 | 0 | clean |
| `6c1ad81` | 2620 / 2618 / 0 / 2 | 0 | 0 | clean |
| `e3a4610` | 2628 / 2626 / 0 / 2 | 0 | 0 | clean |
| `09bacba` | 2640 / 2638 / 0 / 2 | 0 | 0 | clean |

All four commits are green at their own HEAD, and the counts match the commit messages
(2607 → 2617 → 2620 → 2628 → 2640).

**Mutation harness.** 44 runs: 1 baseline over the eight domain files (174/174 green), 2 probes that
pass only if the defect they probe is real (both passed), and 41 mutant runs over 35 distinct mutants
(four survivors re-run on the 258-test auth lane, and three variants of the new-category mutant). Of
the 35, **26 went red and 9 survived**: M05, M08, M09, M10, M13, M22, M23, M25 and M35. Each survivor
is in the claims table with what it means; M35 is a stated blind spot of the prototype census and is
not a finding.

---

## Findings, ranked

### No P0. No token reaches a server, a header, storage, telemetry or product events on the new links.

What was traced, for `/invite#token=…` and the hand-off `/register?invite=1#token=…`:

- **Request URLs.** The Accept href's query is the marker (`invite-token.ts:72`); every `fetch` drops
  the fragment on the wire. The mounted register test asserts no request URL carries the token, and
  M06 (token back in the query) turns three tests red.
- **Next's RSC requests.** `Next-Router-State-Tree` is the router tree the SERVER built
  (`walk-tree-with-flight-router-state.js:38`, `addSearchParamsIfPageSegment`), and the server never
  sees a fragment: the tree holds `__PAGE__` on `/invite` and `__PAGE__?{"invite":"1"}` on
  `/register`. `Next-Url` is path-only. `_rsc` is a hash of those headers. So the implementer's
  statement holds and is **confined to legacy links**: a `?token=` or `?invite=<token>` address puts
  the token in the tree's page segment, and every RSC request made before `router.replace` commits
  carries it in `Next-Router-State-Tree`. That server already received the same token in the
  document URL, so it adds no new party.
- **Telemetry.** `decorateHttpSpan` rewrites `url.full` to origin+path (`provider.ts:197-208`); the
  exporter scrubs every string attribute of every span and log (`exporter.ts:382-420`,
  `scrub.ts:44-67`, first-party query AND fragment cut). The Link prefetch and navigation do hand
  `fetch` a URL object that still has `#token=`, so the fetch span sees it before the scrub; the
  scrub is the only seat, and it covers `#`.
- **Product events.** `route` is a pattern and refuses `?`; no invite field exists.
- **Storage.** `sessionStorage` holds the constant `'1'`; the token is module memory plus React state.
  M07 (token into `sessionStorage`) goes red. See P3-6 for the unscanned stores.
- **Referer.** A fragment is never part of a Referer, and the document's policy is `no-referrer`
  (set on `/invite` and on `/register?invite=…`; M15 red).
- **Session history.** Both entries are replaced through the router (`/invite`, `/register?invite=1`).
  The browser's GLOBAL history still records `/invite#token=…` (the email hop, accepted by B10) and
  the pushed `/register?invite=1#token=…`; that second copy is new in `49f6231` but is the same token
  in the same local store.
- **Console.** Only Next's own `console.error("Failed to fetch RSC payload for " + url)` on a failed
  RSC fetch can print the fragment, and only in the user's own devtools.

### No P1.

---

### P3-1: The strip now needs a server round trip, and any fall-back to a full page load drops the token

- **Where:** `InviteAcceptView.tsx:107-109`, `RegisterView.tsx:115-117` (`09bacba`); the Accept link,
  `InviteAcceptView.tsx` `acceptHref` (`49f6231`).
- **Why a round trip:** `app/layout.tsx:8` is `force-dynamic`, and Next 15's `staleTimes.dynamic` is
  `0` (`config-shared.js:198`). The prefetch entry seeded from the first load (and the temporary one a
  navigation creates) is stale at once (`prefetch-cache-utils.js:277-309`), so `router.replace` to the
  stripped URL triggers a lazy RSC fetch. The r1-era raw `replaceState` needed no network.
- **Failure path:** if that fetch fails, or is not a flight response, Next falls back to a browser
  navigation to the stripped URL (`fetch-server-response.js:143-147`, `:170-177`). The reload has no
  token, and the page says "Open your invitation link again".
- **The more likely trigger is the Accept click itself.** When the build id of the RSC response
  differs from the page's (a deploy landed while the invitee read `/invite`), Next navigates to
  `res.url` (`fetch-server-response.js:158-159`). That URL comes from the fetch, which never has a
  fragment, so `/register?invite=1` loads bare and shows `reopen`. Only the `!res.ok` branch keeps the
  hash (`:143`). The old `/register?invite=<token>` survived this.
- **Impact:** recoverable (reopen the email), and the copy is right. It is a new failure mode, not a
  leak.
- **Fix, if wanted:** for the deploy-skew case, nothing on this side short of keeping the token in
  `history.state`; for the strip, the router change could be kept and the reload case accepted. Worth
  a Future Improvements line.
- Source-read against the installed Next; not driven in a browser.

### P3-2: The "only unreachable offers Try again" guard never reaches the branch it names

- **Where:** test `invite-accept-retry-hydrated.test.ts:387-394`; code `InviteAcceptView.tsx:238-251`.
- The test mounts `/invite` with no token, so it renders the `token === ''` branch
  (`InviteAcceptView.tsx:209-219`), which never passes `onRetry`. It never renders an `expired`,
  `revoked`, `invalid` or `accepted` preview.
- **M13** (`onRetry` on every non-actionable preview) passes the auth file and the whole 258-test auth
  lane. The code is correct today; the guard is a decoy for its own title.
- **Fix:** mount with a fragment token and a preview answering `expired` (and `revoked`), and assert
  no "Try again".

### P3-3: "A token in the address always wins" is unpinned

- **Where:** `lib/auth/invite-token-hold.ts:37-44`.
- This rule is the only thing that stops a token held from an earlier link in the same document from
  answering for a newer one. **M09** (held token first) passes the whole auth lane.
- Reachability is narrow: the same document must hold A and then load B's address. Note that a
  same-path fragment change (pasting `/invite#token=B` over `/invite`) does not reach this code at
  all: it is a same-document navigation, its `popstate` has `null` state, and Next ignores it
  (`app-router.js:451-454`). The page keeps showing A. That part predates this range (`0f87aec`).
- **Fix:** a unit test on `holdInviteToken` (hold A, then read B from the address → B), plus the
  mounted remount case.

### P3-4: The permissions body is narrowed one level deep; "a malformed map degrades to empty" is not true of its values

- **Where:** `lib/auth/PermissionContext.tsx:105-118`.
- `capabilitiesByDepartment` must be a record, but its VALUES are not checked; list ELEMENTS
  (`userRoles`, `departmentPermissions`) are not checked.
- **Probe M24 (passes, so the defect is real):** `{mro: 'users_view_all,roles_manage'}` survives as a
  string, and `resolveCapability(…, 'users_view')` is `true`, because `capability-utils.ts:22-24`
  calls `.includes` on it. A `userRoles: [null]` survives and would throw in `hasTenantOwnerRole`
  (`role-utils.ts:88-90`).
- api's `PermissionsResponse` types the map as `Dict[str, Any]` (api-obsm `35639cb`
  `routers/auth.py`), so the schema does not close it either. The server enforces every write, so
  this is a client-gate hardening gap, not an authorization hole.
- **Fix:** keep only `string[]` values of string elements, drop non-object roles, and test both.

### P3-5: The two new guards cover today's inputs, not tomorrow's

- **`/test-cookie` source scan** (`permissions-endpoint.test.tsx:221-249`) reads `app, components,
  hooks, lib, types, utils`. It skips `constants/` (which holds an `API_ENDPOINTS` table,
  `constants/index.ts:90`), `contracts/`, and root files such as `middleware.ts`. **M22** (a
  `/test-cookie` path in `constants/`) and **M23** (one in `middleware.ts`) survive. Today there is no
  consumer anywhere: a repo-wide search (tests, e2e, perf and scripts included) finds only the scan
  and one doc comment.
- **AD foreign-control guard** (`ad-review-materialize.test.ts:862-886`) renders every category the
  shared table has, which does reach later categories, but it judges them against a five-phrase
  blocklist. **M25** adds a seventh category to `RUN_ERROR_CATEGORY_COPY` ("Open the automation and
  lower how often it runs.") and passes the AD file. **M25r** adds it to the contract JSON as well:
  `runOutcomeCopy.test.tsx` goes red on its literal category list (one of the "four places a new
  category has to land"), but the AD file alone stays green (M25r3). So an author who finishes the
  four-place edit ships a foreign-control sentence to the AD page. The half that matters for content
  (no stored detail) is structural and does hold; the claim "a category added later cannot reach
  this page naming a foreign control" does not.
- **Fix:** scan the repo root minus `node_modules`/`tests`; for AD, require every shared category to
  have a page row or sit on an explicit "names no control" allowlist, so a new one fails until someone
  decides.

### P3-6: Smaller gaps

- **Storage scan covers two stores** (`invite-accept-retry-hydrated.test.ts:346-362`). **M08** (the
  token written to `document.cookie`, which would ride to the server on every request) passes the auth
  lane. `invite-token-hold.ts` is 59 lines and writes nothing else today.
- **"Spent" is only the `/invite` retry.** `forgetInviteToken` runs on `proceed` there
  (`InviteAcceptView.tsx:170`), never on the `/register` path, which is how most invitees finish. The
  tab note outlives a completed signup, so a later bad link in that tab reads "open it again". **M10**
  (no forget at all) passes the auth lane.
- **Retry drops the funnel outcome.** `useInvitationPreview.ts:64-68` records one preview per token per
  view, so after `unreachable` then Try again → success, the funnel keeps `failure`. Source-read.
- **`reopen` on `/register` offers "Create an account without an invitation"** (`RegisterView.tsx:599-606`),
  to an invitee whose link is fine. That is the outcome the marker-with-no-token notice exists to
  prevent (`49f6231`'s own reasoning). `/invite`'s `reopen` offers only "Back to sign in".
- **`scroll: false` is unpinned** (M05 survives). Harmless on a mount.

### P3-7: A false premise in the r1-fix commit, a source comment and a test name

- `09bacba`'s message, `RegisterView.tsx:111` and the test at `invite-register-hydrated.test.ts:395-397`
  say that `?invite=<token>` → `?invite=1` "remounts the page in Next". It does not: the React key of
  a segment is its `stateKey`, built WITHOUT search params (`layout-router.js:394-406`,
  `create-router-cache-key.js:20-22`: "search params do not cause state to be lost"). The component
  keeps its state and its ref, so the legacy path works either way. The test is still worth having
  (Back and a boundary reset do remount); its name and comment should say so.

### Outside this range (recorded, not scored)

- api-obsm `35639cb` `routers/auth.py`, `PermissionsResponse.capabilitiesByDepartment`: the docstring
  says "Department id →"; the resolver keys by lowercased department NAME
  (core-obsm `core/authz/resolver.py:175-177`), which is what the dashboard reads.
- The deploy coupling (the dashboard has no fallback if `/auth/permissions` 404s, so every gate closes)
  is recorded in the plan, §2.2 item 6.

---

## What I tried to break and could not

- **The marker and the fragment.** `registerInviteHref` round-trips `+`, `/`, `=` and a space; the
  fragment beats a legacy query token; a legacy query is rewritten to the marker, not dropped (M18
  red); a blank `?invite=` and plain `/register` are left alone.
- **The middleware.** The marker alone exempts a signed-in visitor and gets `no-referrer` (M15 red).
  RSC requests for `/register?invite=1&_rsc=…` pass the same arm. (`?invite=%20` is exempt at the edge
  but reads as an ordinary signup in the form, because only the form trims. Harmless, and it predates
  this range.)
- **The pre-read render.** "Checking your invitation", never the dead-link title and never a form, on
  `/invite` (M17 red) and `/register` (M16 red). r1's D13 is closed.
- **The strip.** Both raw `replaceState` forms, with and without Next's state, go red on both pages
  (M01–M04). r1's D7 is closed.
- **The hold across remounts.** Bypassing the hold on either page turns the remount and reload tests
  red (M32, M33). `forgetInviteToken` leaving the note behind turns three tests red (M11). The reload
  reads `reopen`, not `invalid` (M12 red). The Try-again re-read is pinned (M14 red).
- **Cross-tab.** The hold is module memory, so nothing crosses documents. The note is copied into a
  tab opened from this one (`sessionStorage` semantics); it is the constant `'1'`.
- **Sign-out.** `logout` ends in `window.location.href = '/login'`, a new document, so the hold dies with it
  (`AuthContext.tsx:133-175`). `LoginView` also hard-navigates.
- **Permissions endpoint.** One `GET` to `{BASE_URL}{API_PREFIX}/auth/permissions`, none to
  `/test-cookie` (M21 red); `tenantId` must be a string (M19 red); `isTenantOwner` is not carried
  (M20 red). api derives `is_tenant_owner` from the same roles (`resolver.is_tenant_owner(user_roles)`,
  and clears both together on failure), so ignoring it cannot disagree with the api in practice.
- **Stale cache.** Header-era `localStorage` entries have the same four fields and, with api pinning
  body == header, the same values; the TTL is 60 s. No new stale path.
- **401 and error UI.** A 401 goes through `fetchWithAuth`'s refresh-and-retry, then the provider's
  catch clears the lists. Nothing renders `usePermissions().error`. A 200 that is not the endpoint's
  shape leaves state as it was, with loading false, the same as a missing header did.
- **Remaining `/test-cookie` consumers.** None: not in app code, tests, fixtures, e2e, perf or scripts.
- **AD copy.** Dropping the page's `access` row (M26), ranking the category above the reason (M27),
  quoting the transport message (M28) or the unknown `runStatus` (M29) all go red. r1's P3-4 is
  closed. A bare-literal reason table is caught by the prototype census (M37 red).
- **A11.** Widening the reason gate to `[\p{Ll}\p{Nd}_]/u` (M30) or admitting ZWSP (M31) goes red in
  both the run history and the bell. r1's A11 is closed.

## What I did not test

- **Any browser, Next runtime or live stack.** P3-1, the Next-header analysis and P3-7 are read from
  the installed `next@15.2.4` source, not observed.
- **Chrome's global-history behaviour** for `pushState`/`replaceState` URLs, which is from memory.
- **api-obsm `35639cb` itself**, beyond reading the route, the payload function and its model.
- **The Suspense boundary on `/register`** under a production build (build banned).
- **e2e** (`tests/e2e/playwright/invite_accept.spec.ts`), by ban.

---

## Claims table

**Severity:** 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs
or process. A functional regression takes the nearest slot and is marked.

**Tier** (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 =
irreversible or estate-shaping (RBAC, the signal contract, content capture, tenancy).

**Chunk:** F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR2-01 | dashboard | `lib/auth/invite-token.ts:69-74` | The Accept href is `/register?invite=1#token=<enc>`; the query holds only the marker | B10: the token leaves every URL a server sees | round-trip tests; no request URL carries the token | `invite-token.test.ts`, `invite-accept-retry-hydrated.test.ts` ("Accept hands the token on in the fragment") | **yes.** M06 (token in query) red, 3 tests | 0 | 0 | F1 | **SETTLED** |
| DR2-02 | dashboard | `lib/auth/invite-token.ts:84-100` | `/register` reads `#token=` first, else a legacy `?invite=<token>`; strips the fragment key; rewrites the legacy query to the marker | Links in flight before the marker | 6 reader tests + mounted legacy test | `invite-token.test.ts`, `invite-register-hydrated.test.ts` | **yes.** M18 (drop instead of rewrite) red, 4 tests | 0 | 0 | F1 | **SETTLED** |
| DR2-03 | dashboard | `middleware.ts:75-76`, `:105-106` | The signed-in exemption and `no-referrer` key on `?invite=` present, marker included | The server never sees the token now | marker exempt signed in; no-referrer both ways | `invite-middleware-bounce.test.ts` | **yes.** M15 (marker not exempt) red, 2 tests | 0 | 0 | F1 | **SETTLED** |
| DR2-04 | dashboard | `components/features/auth/RegisterView.tsx:89`, `:563-573` | The invitee is known at render from the marker; "Checking your invitation" until the token is read; never the ordinary form | No frame of an ordinary signup; the company effect never fires for an invitee | server-render text asserted | `invite-register-hydrated.test.ts:429` | **yes.** M16 red | 0 | 0 | F1 | **SETTLED** |
| DR2-05 | dashboard | `components/features/auth/InviteAcceptView.tsx:209-231` | Pre-read (`null`) renders "Checking", `''` renders the notice | r1 D13 | server-render text asserted | `invite-accept-retry-hydrated.test.ts` ("the pre-read render…") | **yes.** M17 (`null` as dead) red | 0 | 0 | F1 | **SETTLED** (closes DR1-12) |
| DR2-06 | dashboard | `InviteAcceptView.tsx:107-109`; `RegisterView.tsx:115-117` | Strip through `router.replace(url, {scroll:false})`, never raw `replaceState` | r1 P3-1: the router's canonical URL | router replaces recorded apart from raw ones | both hydrated test files ("the strip goes through the router") | **yes.** M01–M04 (both raw forms, both pages) red; M05 (`scroll:false` dropped) survives, harmless | 1 | 0 | F1 | **SETTLED** (closes DR1-11) |
| DR2-07 | dashboard | same as DR2-06; Accept link | The strip and the hand-off depend on the SPA surviving | — | `force-dynamic` + `staleTimes.dynamic` 0 → lazy RSC fetch; MPA fallback drops the fragment (`fetch-server-response.js:143,158-159,170-177`) | none | not recorded (source-read) | 2 (functional; nearest slot) | 1 | F1 | **OPEN.** P3-1 |
| DR2-08 | dashboard | `lib/auth/invite-token-hold.ts:17-51` | The token is held in module memory; only the constant `'1'` goes to `sessionStorage` | r1 P2-1 without storing the secret | session + local storage scanned for the token | `invite-accept-retry-hydrated.test.ts:346` | **yes, partly.** M07 (token into `sessionStorage`) red; M08 (token into a cookie) survives the auth lane | 2 | 1 | F1 | **PARTIAL.** P3-6 |
| DR2-09 | dashboard | `invite-token-hold.ts:37-44` | A token in the address beats the held one | A newer link must not be answered by an older token | none | none | **yes, and it survives.** M09 passes 258/258 | 2 | 1 | F1 | **ASSERTED.** Code right, unpinned (P3-3) |
| DR2-10 | dashboard | `InviteAcceptView.tsx:170` | Forget the token and note once the `/invite` retry lands | "Nothing should answer for it again" | none | none | **yes, and it survives.** M10 passes the auth lane | 3 | 1 | F1 | **PARTIAL.** Not done on the `/register` path (P3-6) |
| DR2-11 | dashboard | `InviteAcceptView.tsx:238-251`; test `:387-394` | Try again only for `unreachable` | Dead links would only fail again | test mounts a tokenless `/invite` | `invite-accept-retry-hydrated.test.ts:387` | **yes, and it survives.** M13 passes 258/258 | 1 | 1 | F1 | **PARTIAL.** Guard never reaches the branch (P3-2) |
| DR2-12 | dashboard | `hooks/auth/useInvitationPreview.ts:37-76` | `attempt` re-reads the same token's preview | Reload can no longer retry | two previews, second has the token in the body | `invite-accept-retry-hydrated.test.ts` ("an unreachable preview offers Try again") | **yes.** M14 (deps ignore `attempt`) red | 0 | 0 | F1 | **SETTLED** |
| DR2-13 | dashboard | `useInvitationPreview.ts:64-68` | One funnel record per token per view | Strict Mode | a retried success keeps the first `failure` | none | not recorded | 2 | 1 | F3 | **OPEN.** P3-6 |
| DR2-14 | dashboard | `RegisterView.tsx:575-608` | Every dead notice, `reopen` included, offers "Create an account without an invitation" | The way out for a dead link | `reopen` means the link is fine | none | not recorded | 2 (functional; nearest slot) | 1 | F1 | **OPEN.** P3-6 |
| DR2-15 | dashboard | `09bacba` message; `RegisterView.tsx:111`; `invite-register-hydrated.test.ts:395-397` | "A query change remounts the page in Next" | — | `layout-router.js:394-406`: `stateKey` excludes search params | n/a | n/a | 3 | 1 | F3 | **REFUTED.** Behaviour is still correct (P3-7) |
| DR2-16 | dashboard | Next `fetch-server-response.js:83-97`; `walk-tree-with-flight-router-state.js:38` | New links put no token in `Next-Router-State-Tree`, `Next-Url` or `_rsc`; legacy links do until the replace commits | The tree is server-built and fragment-free | source-read, three sites | none (no browser) | n/a | 0 | 1 | F1 | **ASSERTED.** Confined to legacy links |
| DR2-17 | dashboard | `lib/telemetry/provider.ts:197-208`; `exporter.ts:382-420`; `scrub.ts:44-67` | Fetch spans see `#token=` from Next's prefetch/navigation URL objects; the exit scrub cuts query and fragment | Pre-existing seat, now load-bearing for the fragment | source-read; scrub tested in r1's range | telemetry scrub tests (pre-existing) | not re-run here | 0 | 1 | F1 | **ASSERTED** |
| DR2-18 | dashboard | `components/features/mro/ad-review/adReviewPresentation.ts:302-335`, `:357-389` | Page reason copy, then page category copy, then shared copy, then token, then fixed sentence | The shared copy names automations-screen controls | busy, `no_verdicts`, `params_invalid` cases | `tests/unit/mro/ad-review-materialize.test.ts` | **yes.** M26 (drop `access` row) and M27 (category above reason) red | 0 | 0 | F1 | **SETTLED** |
| DR2-19 | dashboard | `ad-review-materialize.test.ts:862-886` | A later category cannot reach the page naming a foreign control | Guard over every shared category | five-phrase blocklist | same | **yes, and it survives.** M25 passes; M25r (contract + table) is caught only by `runOutcomeCopy.test.tsx`'s literal list, the AD file alone stays green (M25r3) | 1 | 1 | F1 | **PARTIAL.** Content half (no stored detail) holds; control half is a blocklist (P3-5) |
| DR2-20 | dashboard | `adReviewPresentation.ts:302`, `:329` | Both tables null-prototyped | A `constructor` reason is token-shaped | probe M36: under an `Object.assign({}, …)` mutant, the note renders native code | `tests/unit/lookups/prototype-lookup-tables.test.ts` | **yes.** M37 (bare literal) red; M35 (`Object.assign({}, …)`) survives, a stated census blind spot | 1 | 0 | F2 | **SETTLED** for the realistic edit |
| DR2-21 | dashboard | `adReviewPresentation.ts:515-521`, `:563-570` | `unreadable` and unknown endings are fixed sentences | r1 P3-4: server text | transport text and `runStatus` absent | `ad-review-materialize.test.ts` | **yes.** M28, M29 red | 0 | 0 | F1 | **SETTLED** (closes DR1-06) |
| DR2-22 | dashboard | `tests/fixtures/automations/run-reason-attribute.ts:81-112` | Six non-ASCII lookalike rows | r1 A11 | both surfaces | `runOutcomeCopy.test.tsx`, `automationMissedNotificationRow.test.tsx` | **yes.** M30 (`\p{Ll}\p{Nd}`), M31 (ZWSP) red, 4 tests each | 0 | 0 | F1 | **SETTLED** (closes DR1-03) |
| DR2-23 | dashboard | `lib/auth/PermissionContext.tsx:77`, `:291-294` | One `GET {BASE_URL}{API_PREFIX}/auth/permissions`, body read | B11 | exactly one call, full URL, GET; none to `/test-cookie` | `tests/unit/auth/permissions-endpoint.test.tsx:179` | **yes.** M21 (old route) red | 0 | 0 | F1 | **SETTLED** |
| DR2-24 | dashboard | `PermissionContext.tsx:105-106` | No string `tenantId` → `null` → state untouched | The endpoint always sends a string | 8 non-endpoint shapes | same, `:118` | **yes.** M19 red | 1 | 0 | F1 | **SETTLED** |
| DR2-25 | dashboard | `PermissionContext.tsx:107-118`, `:394` | `isTenantOwner` not read; ownership from `userRoles` | One source inside the provider | api derives it from the same roles | same, `:81` (key set) | **yes.** M20 red | 1 | 0 | F1 | **SETTLED** |
| DR2-26 | dashboard | `PermissionContext.tsx:108-116` | "A malformed list or map degrades to empty" | Gates must not crash | probe M24: a string capability list substring-matches; a `null` role passes | `permissions-endpoint.test.tsx:137` (one level only) | probe passes (defect real) | 2 | 2 | F1 | **PARTIAL.** P3-4 |
| DR2-27 | dashboard | `permissions-endpoint.test.tsx:221-249` | No source file calls `/test-cookie` | The route is deleted next release | repo-wide search: none today | same | **yes, and it survives.** M22 (`constants/`), M23 (`middleware.ts`) pass | 1 | 1 | F1 | **PARTIAL.** P3-5 |
| DR2-28 | dashboard | `PermissionContext.tsx:237-278` | The cache path is unchanged | Same shape, same values, 60 s TTL | source-read | none | n/a | 3 | 2 | F1 | **ASSERTED** |
| DR2-29 | dashboard / api | `PermissionContext.tsx:291-294`; plan §2.2 item 6 | No fallback if `/auth/permissions` is missing | By design (the scan) | 404 → catch → every gate closed | none | n/a | 3 | 1 | F3 | **OPEN.** Deploy order api → dashboard, recorded (§2.2 item 6) |
| DR2-30 | api | api-obsm `35639cb` `flynapse_api/routers/auth.py` (`PermissionsResponse`) | Docstring: capabilities keyed by department id | — | resolver keys by lowercased NAME (core-obsm `core/authz/resolver.py:175-177`) | none | n/a | 3 | 1 | F3 | **OPEN.** Out of range |
| DR2-31 | dashboard | `InviteAcceptView.tsx:103-112`; Next `app-router.js:451-454` | Same-path fragment change is not re-read | Next ignores `popstate` with `null` state | pasted `#token=B` over `/invite` keeps A | none | n/a | 2 | 1 | F3 | **OPEN.** Predates the range (`0f87aec`) |
| DR2-32 | dashboard | the four commits | Each is green at its own HEAD | — | table above | the lane | n/a | 3 | 0 | F2 | **SETTLED** |

---

## Open claims, tier 2 first

**Tier 2**

1. **DR2-26 (P3-4).** The permissions body is narrowed one level deep. A string capability list
   substring-matches and a `null` role throws. Client gates only; api's model is `Dict[str, Any]`.
2. **DR2-28.** The cache path is unchanged (asserted, source-read).

**Tier 1, open**

1. **DR2-07 (P3-1).** The strip needs an RSC round trip; a failed fetch or a deploy-skew Accept click
   reloads without the token and shows `reopen`.
2. **DR2-11 (P3-2).** The Try-again guard never reaches the branch it names (M13 survives).
3. **DR2-19 / DR2-27 (P3-5).** Both new guards are shaped to today's inputs (M25, M25r3, M22, M23 survive).
4. **DR2-09 (P3-3).** Address-wins is unpinned (M09 survives).
5. **DR2-08, DR2-10, DR2-13, DR2-14 (P3-6).** Cookie store unscanned; no forget on `/register`;
   retry drops the funnel outcome; `reopen` offers the uninvited signup.
6. **DR2-15 (P3-7).** The "query change remounts" premise is false.
7. **DR2-31.** A pasted same-path fragment is not re-read (predates the range).
8. **DR2-29, DR2-30.** Deploy order (recorded) and api's docstring (out of range).

**Tier 0, settled:** DR2-01 to 06, 12, 18, 20 to 25, and 32 (every commit green).
