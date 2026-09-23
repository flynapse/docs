# Claims packet: dashboard PRE-PUSH full-diff review (queue step 16b) — FINAL

Fable pre-push reviewer, 2026-09-22, READ-ONLY on the real tree throughout (clean at `dd014fc` before and after;
core-obsm and api-obsm untouched). Durable notes and every log: `~/.claude/scratch/obs-merge/prepush-dashboard/`.

## Anchors and range

| item | value |
|---|---|
| repo / branch | `/home/aditya/Code/dashboard-obsm` · `obs-merge` |
| HEAD | `dd014fc7348ba692df93bd4dab8507a569da266b` (clean tree, verified) |
| pushed mainline | `origin/agent_sdk` = `4a2898bd6559294926a8e5c67dbe82218fa562b8` (ls-remote verified, unmoved) |
| merge-base | `4a2898bd` — the origin/agent_sdk tip itself; HEAD is a strict descendant |
| range | `4a2898bd..dd014fc7` — **51 commits**, 132 files, +13245/−646 |
| authors | 45 aditya.goel, 6 ishaan.jain (the colleague's imported branch, merged via `42b3380` 2026-09-20) |
| era check | merge + all fix rounds are 2026-09-20 → 2026-09-22; the six pre-09-20 author dates are the colleague's branch commits imported by the `42b3380` merge — colleague-era work, consistent. |
| unreviewed sub-range | `f8c4614..dd014fc7` — 5 commits (batch-2: demo-mode name masking + the 7 r4 P3 closures, ledger Add. 269): FIRST-REVIEW rigour |
| indexes (never evidence) | `claims-B2-dashboard.md`, `claims-dashboard-r1..r4.md` (same dir) |
| scratch | `~/.claude/scratch/obs-merge/prepush-dashboard/` |

Known + RULED, not findings here: settings/admin pages NOT masked in demo mode (owner question recorded, controller reco
defer) — flagged only if batch-2 made one WORSE; the G.54 test-layout rework is deliberately out.

## Coverage map (index reconciliation)

Every commit in the range was read from its ACTUAL DIFF here. Earlier rounds tile the pre-batch-2 span with no gap:

| span | commits | index that reviewed it |
|---|---|---|
| `4a2898b..3afd524` | merge `42b3380` + colleague branch (6) + B2.1–3 + triage | `claims-B2-dashboard.md` |
| `3afd524..004a809` | `5011f4f` browser-contract · `fdf7487` G.22 · `79d3bc8` G.36(d) · `3efba84` G.56 · `afd6300` M-COMMIT · `004a809` docs | G-lane rows in `claims-copilot-mro-rounds.md` (G22-01..12 FIXED-AT confirmations); no dashboard-round file — full diffs re-read HERE |
| `004a809..0f87aec` | G.58 ×2, G.77(a), M-INVITE-FRAGMENT half | `claims-dashboard-r1.md` |
| `0f87aec..09bacba` | B10 hand-off, AD copy, B11, r1 fixes | `claims-dashboard-r2.md` |
| `09bacba..4a7714a` | r2 P3s, Quality facts panels, plan | `claims-dashboard-r3.md` |
| `4a7714a..f8c4614` | the 16-commit r3 fix batch | `claims-dashboard-r4.md` |
| `f8c4614..dd014fc` | **batch-2 (5 commits) — NO prior review; first-review rigour here** | this file |

Test-deletion absence check: the only two >30-line test deletions in the range are `69a5bb2` (−49,
`analytics-panel-registry.test.ts` — replaced by the whole-sentence pin, r4 DR4-04 SETTLED with M19/D1 proofs) and
`fdf7487` (−31, `runOutcomeCopy.test.tsx` — the tautological pin G22-02 replaced by per-category must/mustNot +
cross-product, G-lane FIXED-AT). No silently weakened guard.

## Batch-2 first review (f8c4614..dd014fc) — diff findings

### The demo-mask privacy claim, probed adversarially

- **Surfaces claimed masked:** Top Spenders (`spend_by_user`), AD review table `reviewed_by`, PDF comment `author`,
  AD bell row (already masked; helper extracted verbatim into `lib/demo.ts` `displayPersonIdentity` — logic preserved
  line for line).
- **`userLabelledCategoryRows`** rewrites `label` once, BEFORE chart/table/footnote are built; the page's
  `categories` case consumes only the rewritten rows (`page.tsx:295-323` — chart, `tableData`, `tableColumns`,
  footnote all read `categoryRows`). `buildCategoriesColumns`' label column renders and SORTS `row.label` (masked);
  the optional columns are numeric only (`failures`/`unpriced_count`/`turns`/`calls`) — no raw `user_id` or name
  column exists. `buildCategoriesChart` embeds only `label` + `value` (no tooltip meta carrying raw fields).
- **Keying:** core `_spend_by_user_rows` answers `user_id` on every row (`cost.py:209-220`, `user_id IS NOT NULL`
  in SQL), so the pseudonym is keyed by id — stable across tabs; non-demo passthrough is exact (`label ?? user_id`).
  Sentinel `deleted-user` → "Deleted chat" first, demo too. Empty-string `user_id` degrades to label-keyed pseudonym
  (no leak).
- **Census for a bypass:** all 12 `categories` panels' labels = Department ×2, Query Type, User, Model, Outcome,
  Status ×2, Failure Code, Tool, Source, Theme — only `spend_by_user` is people-labelled and only it declares
  `categoryUser`. All 8 `table` panels' declared columns re-censused: the only person-bearing keys are the two
  `user_id` columns (both `user: true`, masked since r3); `name`/`target_name`/`job_name` are automation/improvement
  names, not people. Repo-wide grep for other renders of `reviewed_by` / `.author`: the three
  `displayPersonIdentity` seats are the ONLY ones. No CSV/export/tooltip path for these tables (r4 census re-confirmed).
- **`renderCell` reorder** (user before number): closes r4's noted unreachable hazard; numeric id now reaches
  `formatUserLabel`.
- **Tests carry control assertions** (name RENDERS with demo off, absent with demo on) — self-proving against
  runtime-config caching; fragment-level absence asserts (`'Priya'`, `'sam@'`) cover partial leaks.
- **Nothing RULED made worse:** batch-2 touches no settings/admin page (diffstat: analytics, ad-review,
  notifications, pdf-viewer, lib/demo, tests, plan only).

### Other batch-2 commits

- `62a6db9` closes r4 P3-1 exactly as prescribed: probe now prints `cap=` (`hasCapability('chat.use')`) and `depts=`
  (`departmentPermissions.length`), asserted in BOTH refusal tests — D6 and D6c each turn one field.
- `2f3a2c6` closes P3-2 (copy: "one row per document kind") + P3-5 (history caveat on histogram + turn latency,
  pinned as sentences); the drawn-rows test now uses two kinds. Verified against core HEAD: core-obsm moved to
  `df6a352`, but `git diff 8d0df97..HEAD -- core/resources/analytics core/services/analytics` is EMPTY, so the
  copy is true at core HEAD.
- `5a87789` closes P3-3 as prescribed: `parseRegisteredPanel` reads the `register(PanelSpec(panel_id=…))` block's
  `sql_builder=`/`aggregator=` names (throws on 0 or >1 blocks, on a lambda, on a dotted callee — fail-loud);
  `parseOutcomeColumns` parses THAT builder; `parseSeedKeys` reads the aggregator's `seed_buckets` dict literal keys;
  the contract test requires registry series == SELECT columns AND == seed keys.
- `dd014fc` plan: deploy step (settle writer `d4792d6b` as its own step), reviewer advice (link core AND api),
  P3-4 note corrected, FI (admin pages census with owner question), lesson ("census claims: grep before writing").

## Claims table

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PP-01 | repo/branch/HEAD/remote | anchors as briefed | `git status` clean, `rev-parse` = `dd014fc7…`, `ls-remote` agent_sdk = `4a2898bd…` | SETTLED |
| PP-02 | range | 51 commits, colleague era | merge-base = mainline tip; author/date census; six pre-09-20 dates are the imported colleague branch | SETTLED |
| PP-03 | `lib/demo.ts:75-90`, builders `:81-89`, page `:295-323` | demo mode: no real name on the four claimed surfaces, incl. sort/tooltip/axis | full probe above; census of category labels, table columns, author/reviewer renders | SETTLED (code); see PP-10/PP-11 shape notes |
| PP-04 | `permissions-endpoint.test.tsx` probe | refusal probe reads capabilities and membership on their own | diff read; D6/D6c re-executed below | SETTLED pending mutant re-run |
| PP-05 | registry `:298`, `:428`, `:646`; registry test | P3-2/P3-5 copy true at core HEAD | core diff `8d0df97..df6a352` over analytics dirs EMPTY | SETTLED |
| PP-06 | `core-quality-panels.ts` | contract pin follows registered builder + aggregator, fail-loud | diff read; refusal matrix in test; C-rewire/C-aggrename re-executed below | SETTLED pending mutant re-run |
| PP-07 | pre-batch-2 production diffs | match the settled index claims (invite/permission family, G.56 class, observability, vocab fixes) | full diffs read: middleware, invite-token{,-hold}, useHeldInviteToken, PermissionContext, RegisterView, InviteAcceptView, useInvitationPreview, invitations-api (GET→POST), B2.3 family, memory/chat/pdf null-proto family, runOutcomeCopy family | SETTLED |

## Checks executed (scratch copy `~/.claude/scratch/obs-merge/prepush-dashboard/`, real tree untouched)

Copy recipe: `git archive dd014fc` as `dashboard-obsm/` (node_modules symlinked from `dashboard/node_modules`, never
installed), beside `core-obsm/` = archive of core-obsm HEAD `df6a352` and `api-obsm/` = archive of api-obsm `4bc2d4f`
`-- flynapse_api/automations` (core AND api, per r4 P3-7's corrected advice). Every run through `pytest-slot.sh`.
No `next build`, no browser, no live stack.

| check | result | exit |
|---|---|---|
| `tsc --noEmit` at `dd014fc` | clean, zero diagnostics | 0 |
| `next lint --file` × the 16 batch-2 touched files | "✔ No ESLint warnings or errors" | 0 |
| full unit lane `npm run test:unit` at `dd014fc` | **2685 / 2685 pass, 0 fail, 0 skipped** (recomputed here, not quoted; core AND api siblings beside the copy — zero layout reds) | 0 |

## Mutation re-execution — 7 run here: 6 of batch-2's 12 + r4's banked C-sentinel

Separate mutation copies under `mut/` (dashboard + core + api archives). Green BASELINE first (the four aimed test
files, 60/60, rc=0), each mutant applied as banked (`dashboard-b2/mutants/*.a/.b`; C-rewire reconstructed with the
full v2-builder clone that reproduces the banked `rewire.out` failure), aimed test run, the FAILURE LINE verified
against the banked/expected one, file restored, restore md5-checked against the pristine archive, and a final
restore-green run (60/60, rc=0). Logs: `prepush-dashboard/logs/mut-*.log`.

| mutant | where | aimed test | failure line verified | result |
|---|---|---|---|---|
| flag | registry `:510` `categoryUser: true` removed | registry user-panels pin | `deepEqual` "the categories panels that rank users, and only those…" | KILLED rc=1 |
| order | builders `renderCell` number-before-user | numeric-id user-column test | "a user column renders a numeric id through the user label" strictEqual | KILLED rc=1 |
| D6 | PermissionContext catch keeps `capabilitiesByDepartment` | refusal-on-refresh test | probe `cap=true` ≠ `cap=false` — the exact P3-1 seam | KILLED rc=1 |
| D6c | catch keeps `departmentPermissions` | same | probe `depts=1` ≠ `depts=0` | KILLED rc=1 |
| C-rewire | core registration re-pointed at `_outcomes_v2_sql` (+`AS partial`), `_outcomes_sql` left | core-contract test | "…not the columns …quality.py serves, in its order" with `partial` in the PARSED columns — the pin followed the registration | KILLED rc=1 (r4 survivor now dead) |
| C-aggrename | core seed dict `"failed"` → `"errored"` | core-contract test | "…not the keys …'s aggregator seeds every bucket with" with `errored` parsed | KILLED rc=1 (r4 survivor now dead) |
| C-sentinel (r4 banked) | core `DELETED_USER_ID` respelled `deleted_user` | core-contract test | "the deleted-chat sentinel is not the one …quality.py answers" | KILLED rc=1 (matches r4's ledger) |

## Findings (new, this review)

### PP-10 · P3 (guard shape): the people-panel pin catalogues by the label string 'User'
`analytics-panel-registry.test.ts` pins `categoryLabel === 'User'` ⇔ `categoryUser`. A FUTURE categories panel whose
categories are people but whose label is another word ("Reviewer", "Member") bypasses both the flag and the pin
silently. Same class as the registry pins r4 accepted; the census note in the plan is the mitigation. No action
required for this push.

### PP-11 · P3 (guard shape): `parseSeedKeys` reads the first `{` after `seed_buckets(`
If core ever passes the seed as a NAMED constant, `body.indexOf('{', call)` finds whatever dict literal comes next in
the body (or none). Wrong-dict reads would fail the equality assertion loudly (mismatch), and a missing `{` throws —
fail-loud either way, but the throw message would misname the cause. Cosmetic robustness; no action for this push.

### PP-12 · P3 (cosmetic): `permissionsFromBody`'s doc comment is orphaned
In `lib/auth/PermissionContext.tsx` the long "checked all the way down" docblock is followed immediately by the
`PERMISSIONS_RESPONSE_REFUSED` docblock + const, so the function's own doc attaches to nothing (IDE hover on the
function shows none). Content is accurate; placement only.

## r4 P3 closure reconciliation

Every r4 OPEN/PARTIAL row is answered: DR4-02/DR4-05 by `2f3a2c6` (caveats + per-kind copy, both pinned; verified
true at core HEAD `df6a352`), DR4-07 by `39b626a` (Top Spenders masked; note corrected), DR4-09's threshold half by
`39b626a` (4-series narrow case; M12b banked KILLED), DR4-11 by `5a87789` (C-rewire AND C-aggrename re-executed
KILLED here), DR4-12's missing step by `dd014fc` (settle writer as its own deploy step), DR4-20 by `62a6db9` (D6 AND
D6c re-executed KILLED here), DR4-22's advice + merge-order halves by `dd014fc` (workspace plan rows stay
controller-owned, stated), DR4-25 by owner ruling 6 (question/comment/department text may stay). Nothing was
quietly dropped: `git diff --stat f8c4614..dd014fc` = 17 files, exactly one of them the plan `.md`.

---

## Verdict

**PUSH-CLEAN — P0 0 · P1 0 · P2 0 · P3 3 (PP-10, PP-11, PP-12 — guard-shape and cosmetic notes, none blocking).**

- Anchors held: HEAD `dd014fc7`, origin/agent_sdk `4a2898bd`, merge-base = the mainline tip, 51 colleague-era commits.
- Batch-2 (`f8c4614..dd014fc`, first review): the demo-mask privacy claim probed adversarially and HOLDS — no real
  name reaches a masked surface through any panel, sort, tooltip, axis, or category-label path found; the census
  of category labels, table columns and author/reviewer renders is exhaustive as of this tree.
- All checks recomputed on a scratch archive: tsc 0 diagnostics, lint clean, unit 2685/2685/0 skipped.
- 7 mutants re-executed (6 batch-2 + r4's banked C-sentinel): all KILLED on their aimed failure LINE, restores
  md5-verified, baseline and restore-green both 60/60.
- The two r4 full-lane survivors this batch claimed to kill (C-rewire, C-aggrename, D6, D6c — four, in fact) are
  all dead, verified by re-execution.

The push gate (P0/P1) is clear.
