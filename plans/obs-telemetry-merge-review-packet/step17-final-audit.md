# Step 17 — FINAL REALITY AUDIT (obs-telemetry-merge, queue step e)

Fable 5 auditor, 2026-09-23. READ-ONLY on every code tree (spot runs used `-p no:cacheprovider` +
`PYTHONDONTWRITEBYTECODE=1`; every tree re-measured tracked-clean). Inputs: SDD ledger CHECKPOINT 43 +
Addenda 250–277, `FABLE-INDEX.md`, the nine `claims-prepush-*.md` files, the micro-batch lane's
`~/.claude/scratch/obs-merge/micro-batch/NOTES.md` + logs. This file synthesizes the nine 16b verdicts
plus the audited micro-batch delta — the last gate before the owner's Phase H push.

---

## 1. The nine verdicts, restated at their pinned SHAs

| # | repo | pinned (reviewed) SHA | final SHA | verdict (claims file) |
|---|---|---|---|---|
| 1 | flynapse-otel | `c93a9c9` (main) | `c93a9c9` — untouched | MERGE-CLEAN 0 P0 · 0 P1 · 0 P2 · 3 P3 (full 74 incl. the 42 already pushed at `850bb9d`) |
| 2 | shift-optimizer | `ec383cc` (main) | `f5f732c` | PUSH-CLEAN 0/0/0/2 |
| 3 | telegram-bot | `47a08b7` (main) | `47a08b7` — untouched | PUSH-CLEAN 0/0/0/4 |
| 4 | iac | `427fbbd` (obs-merge) | `011eb67` | PASS 0 P0 / 0 P1 · 1 P2 new (PP-04) + 1 P2 carried (PP-06) · 2 P3 |
| 5 | utils | `23e849c` (obs-merge) | `76d6a0b` | PUSH-CLEAN 0/0/1 P2 (PPU-08)/0 |
| 6 | api | `4bc2d4f` (obs-merge) | `4bc2d4f` — untouched | PUSH-CLEAN 0/0/0/2 (informational/pre-existing) |
| 7 | dashboard | `dd014fc` (obs-merge) | `ed7db1a` | PUSH-CLEAN 0/0/0/3 |
| 8 | core | `6899974` (obs-merge) | `c8c4fb3` | PUSH-CLEAN 0/0/0/1 (PPC-F1) |
| 9 | copilot-mro | `9debf188` (obs-merge) | `9debf188` — untouched | PUSH-CLEAN 0/0/0/3; `memory_items.user_id` judgement call CONFIRMED in-ruling |

Nine of nine clean at the P0/P1 push gate. Every P2/P3 that asked for code was paid by the estate
micro-batch (Add. 276 pool → Add. 277 delta) and is audited below.

## 2. Delta audit — every hunk read, every hunk mapped (Audit A)

All five deltas verified: **exactly one commit per repo, parent = the reviewed SHA, diffstat equal to
Add. 277's table.** Full diffs read hunk-by-hunk; every hunk maps to a pooled item from Add. 276 and
**nothing else rode along** — no secret/env edits, no test deletions, no new skips/xfails, no behavior
change outside the named seats.

| repo | delta | hunk map (all hunks accounted) |
|---|---|---|
| iac | `427fbbd..011eb67` (2 files, +62/−2) | `terraform-apply.yaml`: **exactly the one-line `::stop-commands::hide` move BELOW the two `::add-mask::` lines** (PP-14, owner-sanctioned; secret value/name/env untouched — verified, the diff touches no other line). Test file: docstring extension + `LANE_STEPS` ordered `(name, uses, run)` equality pin + `test_the_guard_lane_runs_exactly_its_steps_in_order` (PP-04; the equality pin also closes PP-05's case-spelled second checkout) + `_TERRAFORM_COMMAND` regex / `_runs_terraform` + 7 disguise + 3 negative parametrized cases + the predicate swap inside `test_every_terraform_job_waits_for_the_guard_lane` (PP-06 — strictly WIDER detection, so more jobs demand `needs`, never fewer). |
| utils | `23e849c..76d6a0b` (3 files, +30/−3) | `metrics.py:169` `reason=str(exc)` → `reason=type(exc).__name__` (PPU-08, the row's first option). Compat test file: new sentinel test `test_a_dropped_emission_logs_the_exception_class_never_its_text` + the kind-conflict pin STRENGTHENED (`"histogram" in reason` → `== "RegistryError"`, required by the fix — substring read the message text). Sweep file: KNOWN_GAPS widened with the same-module-helper gap (plant + docstring bullet naming `metrics._dropped`). |
| shift-optimizer | `ec383cc..f5f732c` (2 files, +13) | One LEAKING witness dict entry "an exception reached through a keyword-splat call" (`refuse(**parts)`, tainted `parts`, expected `{"leak"}`) — PP-01's prescribed fix, NO reader change. Plan Future Improvements entry recording the deferred-then-closed kw-twin — PP-02. |
| dashboard | `dd014fc..ed7db1a` (4 files, +36/−9) | `PermissionContext.tsx`: the `PERMISSIONS_RESPONSE_REFUSED` docblock+const moved ABOVE `permissionsFromBody`'s docblock — **text byte-identical, placement only** (PP-12; no TDZ/behavior hazard, the const only moved earlier). `core-quality-panels.ts` (test fixture): `parseSeedKeys` bounds the `{` search to the `seed_buckets(` call's parens, fail-loud with the named-constant message (PP-11). Contract test: the named-constant-plus-outside-dict witness (PP-11). Registry test: two docblock lines noting the label-STRING pin (PP-10, comment only — the row asked no code). |
| core | `6899974..c8c4fb3` (2 files, +44/−5) | SQL header STOP list now declares findings; the read-back gate gains the non-array disjunct (`texts IS NOT NULL AND jsonb_typeof <> 'array' AND` linked via `signal_ids ?| [signal_id, signature]` to a deleted chat's same-tenant signal, mirroring the array branch's chat linkage); comment updated; **the rewrite guard is unchanged** (the diff never touches the `rewritten` CTE — confirmed at both SHAs). Test file: new pg_temp STOP test + one docstring sentence (PPC-F1). |

**The four untouched repos, rev-parsed:** flynapse-otel `c93a9c9` · api `4bc2d4f` · telegram-bot
`47a08b7` · copilot-mro `9debf188` — reviewed SHA == final SHA, all tracked-clean. ✓

**Add. 277 deviations, all triaged real-and-reasonable:**
1. utils LEAK_BACKLOG/paydown entry — **structurally impossible, verified in the tree**:
   `test_the_backlog_names_only_modules_that_still_leak` is a ratchet that refuses a clean module, and
   PAID_DOWN counts `failure_fields`-in-`except` sites only (metrics has 0 after the fix). The record
   lives in the KNOWN_GAPS docstring bullet ("paid down, and pinned by its own test") + the commit message.
2. dashboard PP-10/11 rows said "no action required for this push"; the lane took Add. 276's pool as
   the mandate and kept the changes minimal (comment; scoped fixture parser + witness). Consistent.
3. core STOP-test red-before — **verified by reading both SQL versions** (§4 below).

## 3. Push truth — re-verified by `ls-remote`, nothing moved (Audit B)

| repo | remote ref of record | expected (CP 43 / claims) | measured now | verdict |
|---|---|---|---|---|
| flynapse-otel | origin/main | `850bb9d` (owner's own pre-gate push) | `850bb9d` | unmoved |
| shift-optimizer | remote **`main`**/main (the remote is NAMED `main`, not `origin` — a `git ls-remote origin` errors here; runner note) | `1ba897e` (batch-2 anchor) | `1ba897e` | unmoved |
| telegram-bot | origin/main | `3102fcc` | `3102fcc` | unmoved |
| iac | origin/main | `f35ec202` | `f35ec202` | unmoved |
| utils | origin/langgraph-merge (mainline-of-record) | `289ba71` | `289ba71`; origin/main `e13e0ab` stale as recorded | unmoved |
| api | origin/langgraph-merge | `44bd8d1` | `44bd8d1`; origin/obs-telemetry-merge `6f22498` (colleague source tip, as filed) | unmoved |
| dashboard | origin/agent_sdk | `4a2898bd` | `4a2898bd` | unmoved |
| core | origin/master | `e10a9ce` | `e10a9ce`; origin/obs-telemetry-merge `8b7dfad` (colleague source, as filed) | unmoved |
| copilot-mro | origin/main | `380601ee` | `380601ee`; origin/langgraph-merge `417df303`, origin/obs-telemetry-merge `c2fc8bb1` — both as filed | unmoved |

**No origin moved since CHECKPOINT 43. No blocker.** Reviewed SHA == pushed candidate except the five
audited micro-batch deltas, exactly as the rule requires.

## 4. Spot re-execution (Audit C — unit only; the db budget stayed closed)

Every run from the repo root via `pytest-slot.sh` (no exit-75), `DEBUG=false`, plain pytest/`-rA`,
serial, no-cache flags so the real trees stayed byte-untouched; rootdir line checked on every run.

| run | where | result |
|---|---|---|
| iac guard file (`test_workflows_gate_on_the_guards.py`) | rootdir `/home/aditya/Code/iac` | **15 passed, rc 0** — the 11 new tests all visible by id (1 equality-pin + 7 disguise + 3 negative) |
| utils compat file (`test_legacy_metrics_service_compat.py`) | utils-obsm root, PYTHONPATH pinned utils-obsm + flynapse-otel | **10 passed, rc 0** — the sentinel test's captured stdout shows `reason: "RuntimeError"` with the sentinel ABSENT, and the kind-conflict pin `reason: "RegistryError"`; green is itself provenance proof (only `76d6a0b`'s seat logs the class name) |
| shift raise-sites file (`test_kept_error_raise_sites.py`) | rootdir `/home/aditya/Code/shift-optimizer` | **111 passed, rc 0** — `[an exception reached through a keyword-splat call]` PASSED by id |
| dashboard contract test (`analytics-core-quality-contract.test.ts`, tsx `--test`) | dashboard-obsm root, real workspace siblings | **5/5 pass, rc 0** — the PP-11 named-constant witness runs inside "the registration reader refuses what it cannot read" |

Micro-batch proof logs verified in `~/.claude/scratch/obs-merge/micro-batch/`: shift NEW3 mutant
**KILLED rc=1 failing on exactly the new witness (1 failed / 127 passed** — `shift-NEW3.log`,
`shift-mutants.txt`); iac 3 mutants KILLED incl. the red-before of the old prefix predicate
(`iac-mutants.txt`); core db run **7 passed rc=0** = the 6 C15 tests + the new STOP test
(`core-db-run.log`) — **Add. 275's queued db re-execution request is CLOSED** (its ask was satisfied
by this run; no further db run owed or taken).

**The core red-before derivation (Add. 277 deviation 3), verified by reading both SQL versions**
(`git show 6899974:scripts/rbac/anonymise_already_deleted_chats.sql` vs `c8c4fb3`): at `6899974` the
findings read-back's ONLY clause is `jsonb_typeof(f.evidence -> 'texts') = 'array' AND EXISTS(...)`,
so the STOP test's string-valued `texts` counts 0 → `finding_texts_left` = 0 → the gate's
`IF … + finding_texts_left + … > 0 THEN RAISE` does not fire → `pytest.raises` finds no exception →
the test would have failed RED. At `c8c4fb3` the new disjunct counts it → "1 finding(s) with a copied
text" raises → green. The rewrite guard (`WHERE jsonb_typeof(...) = 'array'` in the `rewritten` CTE)
is byte-identical across the two SHAs. **Derivation CONFIRMED.**

## 5. Residual ledger check (Audit D)

- **otel PP-21ab** — recorded: `claims-prepush-flynapse-otel.md` row PP-21 (a) bare-attribute
  submodule reach, (b) `delattr` on the data descriptor; both P3, consumerless, record-only. ✓
- **telegram PP-TG-15** (contrived guard-shadow, P3 record-only) and **PP-TG-16** (push order: the
  bot's `pyproject.toml:65` path-depends on flynapse-otel — the push wave must carry both) —
  recorded in `claims-prepush-telegram-bot.md`. ✓
- **PP-TG-14** — recorded with the explicit deferral "Fix at adoption: re-measure and re-triage
  against that day's otel HEAD"; not owed now. ✓
- **PP-MRO-1/2/3** — recorded in `claims-prepush-copilot-mro.md` Findings: 1 = chat-delete ≠
  user-erasure (→ OWNER SHEET, future ruling); 2 = the two ungated write windows (deliberate
  Add. 274 residual 2, confirmed by reading); 3 = runner traps (siblings for the db roundtrip; git
  clone not archive for the scope guard). ✓
- **Add. 274 residuals** — all three recorded: over-scrub-by-substring (design, C15 header + PPC-02),
  ungated windows (PP-MRO-2 + C15 header STOP prose), `memory_items.user_id` judgement call
  (CONFIRMED by the ninth verdict, its own claims row). ✓
- **PP-TG-17** — FIXED at docs `5c158c0`, verified: the commit exists and
  `claims-satellites-rounds.md` line 52 now reads "`645b334..47a08b7` = the r5 fix batch (7 commits;
  `e0da52b` is its first)". ✓
- **OPEN P0/P1 sweep over the whole packet:** the nine prepush files carry ZERO open P0/P1. The
  historical round files retain OPEN P0/P1 **cells** as designed history (the packet keeps the
  original row and records the fix beside it); every one traced has a later disposition:
  `claims-G10-weaviate-spans.md` carries its own in-file flip table (G10-02/06/07/08 FIXED-AT /
  SUPERSEDED-BY); cli-r1's CLI-06/CLI-12 are SETTLED in `claims-copilot-mro-cli-r2.md`
  (CLI-R2-06/CLI-R2-01, mutation-proved); core r8-08 is FIXED in the r9 batch (r9-22, re-run green by
  the core prepush); detector-r5's R5-02 is closed by the r6–r8 chain (r8 R8-08 SETTLED + R8-15
  estate `refusal_types` exposure measured 0); the phase-era `claims-D` / `F3` / `phase6-iac-fixpass`
  rows map to M-items, in-file IF-flip records, or owner-sheet items (C2). Under the FABLE-INDEX
  supersession rule the prepush files are the absence evidence for every repo. **No live open P0/P1
  anywhere.** ✓
- **One record-only observation (not a blocker, pre-range):** F3 residuals #34/#35 (bare phone
  numbers unredacted — `_PHONE_LABEL_RE` is still the only phone rule at mro HEAD, from the
  colleague's `54a01f39`; truncation precedes redaction) remain open phase-0 residuals recorded only
  in `F3-phase0-and-residual.md`. Pre-existing on the colleague's input, outside every reviewed
  range's P0/P1 set, and the capture seat sits under the standing M-CAPTURE (tenant opt-out) / B8
  rulings. Recommend the owner sheet carry a line for them beside PP-MRO-1 so the register is not
  F3-only.

---

## 6. VERDICT

**READY-FOR-PUSH.**

Nine of nine pre-push reviews PUSH-CLEAN at their pinned SHAs; the micro-batch delta is exactly the
pooled P2/P3 fixes and nothing else (hunk-by-hunk); every origin is unmoved (`ls-remote`, nine of
nine); the spot re-executions are green with the new guards visible by id; the core red-before
derivation holds by reading; every residual is recorded where the index says. Zero P0/P1 estate-wide.

## 7. The owner's Phase H checklist (restated from CHECKPOINT 43 / FABLE-INDEX / Add. 276–277)

**Final SHAs to push:** iac `011eb67` · utils `76d6a0b` · shift-optimizer `f5f732c` · dashboard
`ed7db1a` · core `c8c4fb3` · flynapse-otel `c93a9c9` · api `4bc2d4f` · telegram-bot `47a08b7` ·
copilot-mro `9debf188`.

1. **Push order:** core BEFORE dashboard. The push wave carrying telegram-bot MUST carry
   flynapse-otel (PP-TG-16 — path dependency on the shared export seat).
2. **Before core in PROD:** migrations C1/C9/C12 + `provision_rls` (same recipe as the test DB,
   Add. 152 command block). The test DB is already conformant 90/0/0 (owner ran them, Add. 256/257).
3. **utils branch mapping (owner decision at push):** mainline-of-record is `langgraph-merge`
   (`289ba71`); `origin/main` is stale at `e13e0ab` since 08-17 — push to langgraph-merge vs
   fast-forward main is the owner's call.
4. **Rotate the PP-14 approval secret (owner-side, at push):** the mask reorder is in
   (`011eb67`) so FUTURE applies mask correctly, but every PAST successful apply's Actions log
   effectively disclosed `APPROVED_SECRET` to log readers — rotate it.
5. **Owner actions (C-sheet):** C5 deploy order · C6 old `optimizer_runs.error` DML · C13 ·
   **C15 — run `anonymise_already_deleted_chats.sql` AFTER this push (it now includes the findings
   STOP), then reap BY HAND the two lists it reports: `spilled_objects_to_reap` (S3) and
   `compaction_index_docs_to_reap` (Weaviate) — the script cannot reach either** · C7
   `.env.sample:82` · C8 cognito Dockerfile · C4 SAD docker run.
6. **C2 post-deploy trio (once AMP/otelcol metrics exist):** stored-shape one-liner → fix the 6
   selectors per Add. 256's grammar table; `_total` suffix check → one `absent()` edit; the
   bogus-function alarm probe (one `PutMetricAlarm`).
7. **B14** = its own post-push plan (compat battery condition).
8. **Deploy notes:** copilot-mro settle writer `d4792d6b` rides in the deploy notes (dashboard plan
   `dd014fc` carries it as its own step).
9. **Owner sheet, standing:** PP-MRO-1 — a future user-erasure flow needs its own ruling ·
   the F3 #34/#35 capture residuals (§5 above) · demo settings-pages masking = deferred candidate
   batch · `.wslconfig` deferred · `migrate_ifim_dynamodb` cross-repo carve-out registration ruling
   (Add. 254 minor).

*Durable audit artifacts: this file; scratch `~/.claude/scratch/obs-merge/step17/` (empty of
run-state by design — every proof above is quoted from logs that live in the reviewers' and the
micro-batch's own scratch lanes, named in place).*
