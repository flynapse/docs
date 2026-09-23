# FABLE-INDEX — the Fable reviewers' index (queue step 16d)

Built 2026-09-23 by the controller (Fable 5), after all nine step-16b pre-push verdicts. This file
**replaces the README's totals and row-count column** (owner-ratified, ledger Add. 213 owner sheet).
It is a MAP, never evidence: every number here is recomputed from the named claims file, and the claims
files themselves are indexes over diffs and executed proofs — the diffs and proofs are the evidence.

## The gate statement

**All nine repos are Fable-covered end to end at their pinned pre-push SHAs: nine FULL-DIFF reviews,
nine PUSH-CLEAN verdicts, zero P0/P1 estate-wide.** Under the review-trust rule (Add. 228d) Opus-authored
ABSENCE claims (MERGE-CLEAN verdicts, severity downgrades) counted as unverified until Fable-covered; the
16b sweep closes that gap for every repo's entire unpushed range. Earlier round files below therefore stand
as FINDING indexes and history; as *absence* evidence they are superseded by their repo's prepush file.

## Table 1 — the nine pre-push verdicts (step 16b)

| repo | claims file | pinned SHA | range reviewed | verdict | open items → disposition |
|---|---|---|---|---|---|
| flynapse-otel | claims-prepush-flynapse-otel.md | `c93a9c9` (main) | full 74 commits incl. the 42 already pushed at `850bb9d` (owner's own pre-gate push, Add. 261) | PUSH-CLEAN 0/0/0/3 | PP-21ab record-only |
| shift-optimizer | claims-prepush-shift-optimizer.md | `ec383cc` (main) | full unpushed range | PUSH-CLEAN 0/0/0/2 | PP-01 witness + PP-02 note → micro-batch |
| telegram-bot | claims-prepush-telegram-bot.md | `47a08b7` (main) | `3102fcc..47a08b7` (31 commits) | PUSH-CLEAN 0/0/0/4 | PP-TG-14 re-triage at adoption; PP-TG-15 record-only; PP-TG-16 push order (rides with otel); PP-TG-17 FIXED docs `5c158c0` |
| iac | claims-prepush-iac.md | `427fbbd` (obs-merge) | `f35ec202..427fbbd` | PUSH-CLEAN 0 P0/0 P1; 1 P2 new (PP-04) + 1 P2 carried (PP-06, stays P2 by scope ruling) | PP-04 + PP-06 → micro-batch; PP-14 mask reorder (owner-sanctioned) → micro-batch |
| utils | claims-prepush-utils.md | `23e849c` | full range vs mainline-of-record `langgraph-merge` `289ba71` (main stale since 08-17; owner maps branch at push) | PUSH-CLEAN 0/0/1/0 | PPU-08 (`metrics.py:169`) + KNOWN_GAPS/backlog → micro-batch |
| api | claims-prepush-api.md | `4bc2d4f` | full range from colleague anchor `44bd8d1` (Add. 271 by-construction pattern); colleague source branch = `origin/obs-telemetry-merge` | PUSH-CLEAN 0/0/0/2 (both informational/pre-existing) | none |
| dashboard | claims-prepush-dashboard.md | `dd014fc` | full unpushed range (masking claim held adversarially) | PUSH-CLEAN 0/0/0/3 | PP-10/11/12 → micro-batch |
| core | claims-prepush-core.md | `6899974` | `e10a9ce..6899974` (168 commits; pushed `origin/master` IS the merge-base — excluded set empty) | PUSH-CLEAN 0/0/0/1 | PPC-F1 (C15 findings-gate widen) → micro-batch; C15 db-test re-run rides with it (Add. 275 request) |
| copilot-mro | claims-prepush-copilot-mro.md | `9debf188` | `417df303..9debf188` (327 commits; `380601ee..417df303` = 2,231 commits excluded as the R12–R21/R22-gated rebuild push) | PUSH-CLEAN 0/0/0/3 | PP-MRO-1 → owner sheet (future user-erasure flow); PP-MRO-2/3 record-only. Judgement call `memory_items.user_id` CONFIRMED in-ruling |

Push gate = P0/P1 only. Every P2/P3 above pools into the ONE estate micro-batch (Add. 276) — the only
post-verdict commits, audited as an exact delta at step 17.

## Table 2 — the round files (history + finding indexes)

Phase-era packets (pre-rounds): `claims-C1-utils-B1-core.md` · `claims-B2-dashboard.md` · `claims-C2-api.md` ·
`claims-D-copilot-mro-app.md` · `claims-E-deployment-and-iac.md` · `claims-G5-chat-turn-facts.md` ·
`claims-G10-weaviate-spans.md` · `claims-phase6-dashboards.md` · `claims-phase6-fixpass.md` ·
`claims-phase6-iac-fixpass.md` · `F3-phase0-and-residual.md`.

Round packets, by repo (each file carries its own range, verdict and flip records):

- **utils:** `claims-utils-rounds.md` (post-C1 rounds) → r5 `10651dc..8572635` → r6 → r7 → r8 → r9 `179cc6d..fe45c35`.
- **core:** `claims-core-rounds.md` (post-B1) → r7 `625c0d3..dc41caa` → r8 → r9 `376ae7b..16cd1ae` (15 rows flipped FIXED by the r9 batch, flip record in-file; r9-28 flipped after the anon-copies extension, Add. 274) → r10 NARROW `16cd1ae..19403fa`.
- **api:** `claims-api-rounds.md` → r6 → r7 → r8 → r9 (the r8 batch + eight never-reviewed commits).
- **copilot-mro:** `claims-copilot-mro-rounds.md` → r7 → r7b (+ r7b-r2, r7b-r3) → r8 (P2-5 refuted-then-fixed `0e32212c`, copies half BUILT `34bab392` — updates in-file) → r9 → cli r1/r2 → tb-AB-r1 · tb-CD-r1.
- **dashboard:** r1 → r2 → r3 (FINAL review) → r4 (FINAL, fix batch).
- **iac:** r3 → r4 (`d52e8b8..74346bb`) → r5.
- **flynapse-otel:** `claims-flynapse-otel-rounds.md` → detector r5/r6/r7 → r8 CLOSING. `claims-flynapse-otel-netguard-r1.md` = OUT of this project (Add. 215; netguard is its own later plan).
- **telegram-bot:** r3 → r4 → r5 (detector triage line).
- **shift-optimizer:** r1 → r2 CLOSING (fail-closed reader redesign).
- **cross-repo:** `claims-satellites-rounds.md` (transcript-only satellite rounds, recovered to durable form; r5 fix-batch range corrected per PP-TG-17).

## Open pool at index time

- **Estate micro-batch (live, Opus 5.5, Add. 276):** iac PP-04 + PP-06 + PP-14 reorder · utils PPU-08 + KNOWN_GAPS/backlog · shift PP-01/02 · dashboard PP-10/11/12 · core PPC-F1 + the C15 db-test re-run.
- **Record-only:** otel PP-21ab · telegram PP-TG-15 · mro PP-MRO-2/3 · the Add. 274 residuals (ungated write windows, substring over-scrub by design).
- **Owner sheet:** PP-MRO-1 (a future user-erasure flow needs its own ruling) · PP-14 secret rotation at push · C2 post-deploy trio · C5/C6/C13/C15/C7/C8/C4 · B14 post-push plan · utils branch mapping · Phase H push order (core before dashboard; telegram rides with otel).

## Micro-batch delta (landed 2026-09-23, ledger Add. 277)

The only post-verdict commits. Reviewed SHA → FINAL SHA, one commit per repo, controller-measured:

| repo | reviewed | final | what rode |
|---|---|---|---|
| iac | `427fbbd` | `011eb67` | PP-04 equality pin (closes PP-05 too) · PP-06 command-position terraform detection · PP-14 mask reorder (2 files, +62/−2) |
| utils | `23e849c` | `76d6a0b` | PPU-08 class-name-only log + tests + KNOWN_GAPS (3 files, +30/−3) |
| shift-optimizer | `ec383cc` | `f5f732c` | PP-01 kw-splat witness · PP-02 note (2 files, +13) |
| dashboard | `dd014fc` | `ed7db1a` | PP-11 scoped seed parser + witness · PP-10 comment · PP-12 placement (4 files, +36/−9) |
| core | `6899974` | `c8c4fb3` | PPC-F1 findings-gate widen + STOP test; the C15 db re-run rode with it — 7 passed, Add. 275 request closed (2 files, +44/−5) |

flynapse-otel `c93a9c9` · api `4bc2d4f` · telegram-bot `47a08b7` · copilot-mro `9debf188` are UNTOUCHED —
reviewed SHA == final SHA. Step 17 (final reality audit) synthesizes the nine verdicts plus this delta.
