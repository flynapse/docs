# Review packet — observability & telemetry merge

Built 2026-09-20 by four independent Opus assemblers, one per slice, read-only against the merged
worktrees. Governing plan: `../observability-telemetry-merge-and-completion.md` (§2.3a defines the
tiering this packet implements).

> **STATUS 2026-09-22 ~05:30 (COMPACTION #11): FINAL since the pause — `claims-dashboard-r3.md` (FIX-FIRST 0/0/1/13 → fixed at dashboard `f8c4614`), `claims-flynapse-otel-detector-r7.md` (FIX-FIRST 0/1/4/5) + `claims-flynapse-otel-netguard-r1.md` (FIX-FIRST 0/1/6/3), `claims-utils-r8.md` (MERGE-CLEAN 0/0/1/10 → fixed `fe45c35`), `claims-iac-r4.md` (MERGE-CLEAN 0/0/1/8 → fixed `d1ebeb1`), `claims-copilot-mro-r8.md` (FIX-FIRST 0/1/5/10, P1 measured), `claims-copilot-mro-r7b-r2.md` (MERGE-CLEAN 0/0/1/6), `claims-core-r9.md` (FIX-FIRST 0/0/4/11; C15 on hold), `claims-satellites-rounds.md` (N6, 191 rows). In flight (will file here): `claims-api-r9.md`, `claims-copilot-mro-tb-CD-r1.md`, `claims-copilot-mro-tb-AB-r1.md`, `claims-dashboard-r4.md`, `claims-iac-r5.md`. Still owed: README totals across every file and a per-file row-count column. Agent ids and queue: SDD ledger CHECKPOINT 39.**
>
> **STATUS 2026-09-22 ~02:05 (FULL PAUSE #10): every reviewer is PAUSED with a PARTIAL file in this directory — `claims-utils-r8.md` (**FINAL: MERGE-CLEAN 0/0/1/10**), `claims-copilot-mro-r7b-r2.md` (**FINAL: MERGE-CLEAN 0/0/1/6**, 28 rows), `claims-dashboard-r3.md` (**FINAL 02:40: FIX-FIRST 0/0/1/13**; `2a9b0f4` sub-review MERGE-CLEAN 0/0/0/6 inside it), `claims-flynapse-otel-detector-r7.md` (**FINAL: FIX-FIRST 0/1/4/5**) + `claims-flynapse-otel-netguard-r1.md` (**FINAL: FIX-FIRST 0/1/6/3**), `claims-iac-r4.md` (**FINAL: MERGE-CLEAN 0/0/1/8**); `claims-copilot-mro-r8.md` (**FINAL: FIX-FIRST 0/1/5/10; P1-1 measured**); N6 `claims-satellites-rounds.md` **FINAL: 191 rows (15 tier 0 / 130 tier 1 / 46 tier 2; 4 STILL OPEN); IR-12 corrects the ledger — the "fabricated citation" is real on the deployed branch**. Every PARTIAL header comes off only when its reviewer resumes and finalises (agent ids in the SDD ledger CHECKPOINT 38). Totals below and the row-count column are still owed. 44 slice files + this README.**
>
> **STATUS 2026-09-22 (compaction #9): 38 slice files + N6 partial; every one of the 11 original files now carries a `## Re-statement 2026-09-22` section (R1/R2 done — row states as of the HEADs named in each section; phase6-iac-fixpass holds 25 rows, not 22).** Filed since compaction #8: `claims-api-rounds.md` (N4, 95 rows), `claims-flynapse-otel-rounds.md` (N5), `claims-satellites-rounds.md` (N6, PARTIAL: telegram/shift + G.110/core rows; iac rows, rounds table and totals still to come). Reviews in flight that will file here: utils-r8, copilot-mro-r8, copilot-mro-r7b-r2, dashboard-r3, flynapse-otel-detector-r7, flynapse-otel-netguard-r1, iac-r4. **Still owed:** N6 completion; the totals below (they still describe only the original nine files); a per-file row-count column that matches the files (E: 25 for phase6-iac-fixpass).
>
> *(compaction #8 text follows for history)* **STATUS 2026-09-22 (compaction #8): 35 slice files; reviews now file straight into this directory.** Filed
> since the rebuild began: shift-optimizer-r1; utils-r5, r6, r7 and utils-rounds; dashboard-r1, r2; api-r6, r7, r8;
> flynapse-otel-detector-r5, r6; copilot-mro-rounds, r7, r7b, cli-r1, cli-r2; core-rounds, r7, r8; telegram-bot-r3,
> r4, r5; iac-r3; plus G5 and G10. **Still to do** (N4 api-rounds FILED 2026-09-22, 95 rows): N5
> (flynapse-otel rounds, Add. 20, 50, 62, 79); N6 (satellites: telegram 21/59, shift 18, iac 20, G.110 33, core
> sweeps G.46 + G.61 text repairs); R1/R2 (re-state the original 11 files against later fixes and rulings, incl.
> cross-file staleness such as copilot-mro-rounds G24-01); then the totals below. **Until then the totals section
> describes only the original nine files**, and any OPEN or ASSERTED row in those files is unverified against today's
> tree. **Tier vs severity:** the packet's Tier is §2.3a's (0 = settled by a mutation-checked guard an INDEPENDENT
> reviewer saw red; never sent to Fable). Reviewers' own severity (0 = a content leak that ships … 3 = docs) sits in its
> own column in every file filed since the rebuild.

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
