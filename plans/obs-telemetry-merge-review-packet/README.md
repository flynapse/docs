# Review packet — observability & telemetry merge

Built 2026-09-20 by four independent Opus assemblers, one per slice, read-only against the merged
worktrees. Governing plan: `../observability-telemetry-merge-and-completion.md` (§2.3a defines the
tiering this packet implements).

## What this is for

An auditor adjudicates **claims**, not code. Each row states a decision that was taken, why, the
evidence behind it, and the guard test that would catch a regression. Spot-check what you disbelieve;
do not re-read the tree. That inversion is the whole point — without it, a later reviewer repeats the
discovery the Opus reviewers already paid for.

## The files

| file | slice | rows |
|---|---|---|
| `F3-phase0-and-residual.md` | Phase 0 review + owner rulings + the deferred register | 66 |
| `claims-C1-utils-B1-core.md` | utils `289ba71..e6b464e`, core `8b7dfad..d7f7b54` | 36 |
| `claims-D-copilot-mro-app.md` | copilot-mro application half, `e26be7dd..6dc3160e` | 45 |
| `claims-E-deployment-and-iac.md` | copilot-mro deployment `6dc3160e..ea0ac559` + iac `f35ec20..3068b47` | 39 |
| `claims-C2-api.md` | api `4da716f..9812f44` — the gateway merge, 8 commits | 35 |
| `claims-phase6-dashboards.md` | Phase 6 — Grafana boards, Prometheus/Loki rules, runbooks, `iac` boards + `alarms.tf` | 48 |
| `claims-B2-dashboard.md` | dashboard `42b3380..3afd524` — the merge, B2.1-B2.4 | 45 |
| `claims-phase6-fixpass.md` | independent review of the Phase 6 fix pass, copilot-mro half | 24 |
| `claims-phase6-iac-fixpass.md` | independent review of the Phase 6 fix pass, `iac` half | 22 |

## How to read a row

- **Tier** — 0: a mutation-checked guard proves it. 1: consequential but reversible. 2: irreversible
  or estate-shaping (the signal contract, content capture under the opt-out flip, the read API's
  RBAC, tenancy and RLS).
- **Chunk** — F1 contract + privacy, F2 the merge itself, F3 the residual.
- **Claim state** — the column that matters:
  - `SETTLED` — a guard exists **and** has been shown to fail when the property is removed.
  - `ASSERTED` — a guard exists; no mutation proof is recorded.
  - `OPEN` — no guard. It rests on judgment.

`none` in a guard cell is a real answer, not a gap in the assembly. `CLAIMED BUT NOT FOUND` means a
source document named a guard that does not resolve in the tree — read those first.

## Totals, and the result worth knowing

360 claims across **nine** slices. **84 SETTLED · 99 ASSERTED · 177 OPEN.** **0 tier 0.**

Tier 0 is empty in all nine files. Exactly one tier-0 claim was ever filed, in the Phase 6 fix-pass review, and the controller **downgraded it to ASSERTED on 2026-09-20**: the gate says tier 0 requires `SETTLED`, `SETTLED` requires a guard shown to fail when the property is removed, and that row recorded `not recorded`. The bar held. Work mechanical enough to qualify is work nobody
records a decision about, so it never becomes a claim; everything that *is* a claim embodies a
decision, which puts it at tier 1 or 2. So the cost saving does not come from tier 0 excluding most
of the corpus — it comes from a SETTLED claim being adjudicable from one row.

**49% of the corpus is OPEN** — and the share ROSE as the packet grew, from 45% at six slices to 49% at nine. The three slices added last are the two independent fix-pass reviews and the dashboard merge, and reviews surface judgment calls faster than they surface guards. That number is the packet's real output. It was invisible while the
same evidence sat in narrative prose, and it is the map of where judgment, not testing, is holding
this work up.

## Start here

Each file ends with **"Open claims, tier 2 first"**. Those are the estate-shaping decisions no test
settles. Read them before anything else.
