# Claims packet: dashboard r4 (review r3 fix batch) — PARTIAL (lanes still running)

Independent adversarial review (Opus), 2026-09-22, read-only. **PARTIAL — written after the first aimed lanes; the full
unit lane and the survivors' full lane are in flight. Rows marked (pending) are not final.**

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `4a7714a..f8c4614` | dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | 16: `e79e987` P2-1 · `a7fdc5f` P3-7 · `69a5bb2` P3-1 · `cdb9f89` P3-5 · `ce3548f` P3-4 · `562bb5c` M21 · `4044656` P3-6 · `469f8e9` P3-2 · `dddf887` P3-3 · `a7a9a4d` F4 · `3c2b34e` F3 · `e4e0a8f` F1 · `f7947f4` F2 · `c7a3310` F6 · `433b135` F5 · `f8c4614` plan |

Copies: `~/.claude/scratch/obs-merge/dash-review-r4/dashboard-obsm` (`git archive f8c4614`, `node_modules` symlinked) beside
`~/.claude/scratch/obs-merge/dash-review-r4/core-obsm` (`git archive core-obsm 16cd1ae`), so `siblingName('core')` resolves to
the core copy. Notes, mutant texts and logs beside them.

## Aimed lanes so far

| check | result | exit |
|---|---|---|
| analytics lane `tests/unit/analytics/*.test.ts?(x)` @ `f8c4614`, core copy beside | 77 / 77 / 0 (contract test RAN, not skipped) | 0 |
| contract test, core copy moved away | FAILS naming the path, "not checked out beside this repo" | 1 |
| same, `GITHUB_ACTIONS=true` | SKIPPED with the same message | 0 |
| same, `GITHUB_ACTIONS=1` | FAILS (only the exact string `true` skips) | 1 |
| same, empty `core-obsm` dir | FAILS, "checked out, but on a branch without the module" | 1 |

## Mutation ledger so far — 25: 20 KILLED, 5 SURVIVED (aimed), 0 BROKE

Core-copy mutants (aimed at `analytics-core-quality-contract.test.ts`): C-add (7th column) KILLED · C-rename
(`not_answered`→`unanswered`) KILLED · C-reorder KILLED · C-sentinel (respelt) KILLED · C-annot (`DELETED_USER_ID: str = …`,
a throw — loud false-red) KILLED · **C-rewire** (panel registered to a new builder with an extra column, `_outcomes_sql` left
as is) **SURVIVED** · **C-aggrename** (`_outcome_rows` serves `failed` as `errored`) **SURVIVED**.

Implementer's mutants re-run (13): M19, M21, M12, M14, P34-sentinel, F5-silent, R3M-mts, F6-register-unkeyed,
F6-invite-unkeyed, R3M-hashraw, R3M-funnel-every-run, R3M-internal-reworded, P32-seventh-series — all KILLED on their aimed
file, each on the aimed test's own `✖`.

Own dashboard plants: D5 (demo check before the sentinel) KILLED · D20 (drop `mts` from the scan) KILLED on the reach check ·
**D1** (contradicting sentence ADDED to Answer Outcomes) **SURVIVED** (declared limit) · **D6** (refused-load catch keeps
`capabilitiesByDepartment`) **SURVIVED** · **D6c** (catch keeps `departmentPermissions`) **SURVIVED**.

## Findings so far (pending the full lanes)

- **(pending) P3 — F5's refresh pin never observes the capability map.** D6/D6c pass `permissions-endpoint.test.tsx`: the probe
  prints tenant, roles, `hasCapabilityInDepartment` (which reads the cleared membership first) and loading — never
  `hasCapability`, which reads `capabilitiesByDepartment` directly and feeds `computeSettingsPermissions`.
- **(pending) P3 — the core-contract pin reads `_outcomes_sql` by NAME and its SELECT only.** C-rewire and C-aggrename stay green.
- **P3 — Top Spenders names real users in demo mode** (pre-existing, out of range): `categories` variant renders core's
  `label` (name/email) with no anonymisation; the P3-4 plan note "like every other place the page names a user" is false.
- **P3 — histogram and turn-latency copy omit core's history caveat** (core `reliability.py` turn-latency note).
- **P3 — the "Unknown" cited row also collects LIVE id-less, title-less citations** (copilot-mro keeps a `manual_type`-only entry).
- **P3 — merge order**: the contract test fails in the primary `dashboard` checkout until core's obs-merge is merged into primary
  `core` (`e10a9ce` has no `DELETED_USER_ID`).
