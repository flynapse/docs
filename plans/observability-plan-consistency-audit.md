# Plan-consistency audit — `/home/aditya/Code/docs/plans/` @ `main` `fa24dda`

Read-only. Nothing outside this scratchpad was written. Trees read at:
`core-obsm` `d7f7b54` (clean) · `utils-obsm` `e6b464e` (clean) · `copilot-mro-obsm` `d8d2570c`
(**22 modified + 1 untracked — implementer in flight**) · `api-obsm` `66868f85` (**one commit past
the `9812f44` the corpus records**) · `dashboard-obsm` `3afd524` (clean) · `iac` `obs-merge` `2d493c8`
(**two commits past the `3068b47` the corpus records**) · `telegram-bot` / `shift-optimizer` /
`flynapse-otel` on `main`.

Where a claim describes a commit the corpus names, I verified it **at that commit**, not at the
moving HEAD. Those cases are marked.

---

## Findings, most dangerous first

### P0

**F1 — The judge-side residency allowlist is owned by no phase in either plan, and the exporter-side
half is claimed by both. The merged tree ships the eval suite with neither.**

| | |
|---|---|
| Document:line | `agent-evaluation-completion.md:107-120` ("**The owner ruled that residency enforcement lands in the CURRENT merge, not here.** This project therefore treats it as a precondition and does not implement it"), `:149` ("The exporter-side refusal is **unclaimed by any phase** and is inherited here — Phase 8"), `:552-554` ("It does not implement the judge-side provider allowlist / residency. That is the current merge's deliverable and this project's precondition") |
| The claim | The merge owns the judge-side allowlist; no phase owns the exporter-side refusal. |
| What is actually true | **No merge-plan phase item implements the judge-side allowlist.** `observability-telemetry-merge-and-completion.md:600-601` (G.8) names only *"residency enforcement in overlay validation"* — the **exporter** half, i.e. exactly the half the evals plan says nobody owns. The merge plan's own unticked owner decision at `:928-936` states it plainly: *"M-EVALS' 'the rest does not merge' never happened, and no phase owns it … **M-RESIDENCY is unenforced**: grep for an allowlist across the runner and the CLI returns nothing."* Verified in the tree: `grep -riE "allowlist\|residency\|in-account"` over `/home/aditya/Code/copilot-mro-obsm/copilot_mro/app/services/agent_evaluation/` returns **zero hits**; `provider` is a free-form string passed straight through at `/home/aditya/Code/copilot-mro-obsm/copilot_mro/app/services/agent_evaluation/phoenix_adapter.py:289` and `:399` (`LLM(provider=self._provider, model=self._model)`); and `/home/aditya/Code/copilot-mro-obsm/docs/runbooks/observability/phoenix-evaluations.md:121` and `:137` document `--provider openai`. The whole suite (4 modules + the `evaluation` poetry group) is in the merged tree. |
| What someone would build wrong | An implementer closing Phase G executes G.8's overlay half and ships. The evals project then starts on its stated precondition (§2.2) and runs Phases 3/5/9 against real traces — sending the user's question, the model's answer and retrieved manual text to OpenAI. That is precisely what spec §6.5 / ruling 11 forbid, and the ruling that was supposed to prevent it ("no eval run touches real traces until it is enforced") is recorded in a document neither implementer owns. Meanwhile the *exporter* half is double-claimed, so it gets built twice or, if each side assumes the other, not at all. |
| Severity | **P0** |

*Mitigating, and worth stating:* the evals plan hedges at `:531-535` (Q3 records the merge plan's
"unenforced" note and makes P0.2 re-check it). The defect is that §2.2 and §8 are written as
settled fact and are what an implementer reads first.

---

### P1

**F2 — R.3's coverage matrix marks a provably dark boundary as fully covered, contradicting the
tree's own inventory and three other documents in the corpus.**

| | |
|---|---|
| Document:line | `observability-coverage-matrix.md:147` — `\| Agent subagent calls \| copilot-mro \| telemetry.py:1447,1452 \| yes \| **yes** — agent.subagent.calls, agent.subagent.duration_seconds \| yes \| — \|` (gap column empty) |
| The claim | The subagent boundary emits a span, both metrics, and a correlated log. No gap. |
| What is actually true | At `copilot-mro-obsm` **`ea0ac559`** — the exact HEAD this document records reading (`:16`) — `record_subagent` has **no production caller**. `git grep record_subagent ea0ac559` returns the definition (`copilot_mro/app/services/agent_shared/telemetry.py:1899`) and one unrelated `lang_agent/backend.py:948` `_record_subagent_runs` helper; nothing calls the facade. Lines `1447` and `1452` are the *instrument declarations* (`registry.counter("agent.subagent.calls")` / `registry.histogram("agent.subagent.duration_seconds")`), not call sites. The repo's own inventory at `ea0ac559:tests/integration/otel/_emitted_series.py:115-125` marks both **`"dark"`** with the comment *"The instruments exist and the facade records them, but NOTHING calls record_subagent."* Three corpus documents agree with the tree and against the matrix: `observability-telemetry-merge-and-completion.md:1018-1023` ("`record_subagent` has no production call site anywhere … the `fn-llm-agents` 'Subagent rate and p95 duration' panel is therefore permanently empty"), `obs-telemetry-merge-review-packet/claims-phase6-dashboards.md` row 8, and `observability-close-out-gate.md:154` ("5 `dark` … the two subagent instruments"). |
| What someone would build wrong | R.3 is the gap table that Task R / G.1 produces and that R.4's orphan analysis consumes. An implementer reconciling R.3 against G.6 ("subagent span and metric call sites", still `[ ]` at `:596`) would close G.6 as already covered, leave the two instruments dead, and hand R.4 a producer inventory that lists a series nothing emits — so a permanently-empty panel and any alert on it read as legitimate. The summary count at `:280` and `:286` is also affected: §C "fully covered" is 15, not 16, and the estate total is 45, not 46. |
| Severity | **P1** |

*Live note:* the in-flight implementer in `copilot-mro-obsm` is wiring this right now —
`agent_pipeline.py:272,688`, `orchestrator.py:3560`, `lang_agent/backend.py:955` and a new
`agent_shared/subagent_runs.py` are **uncommitted**, and the working-tree `_emitted_series.py` now
says `"wired"`. So the matrix will become accidentally true. It was false at the commit it cites,
and the merge plan's `:1018` deferral ("genuinely unstarted — the merge did not touch it") is about
to go stale in the other direction.

---

**F3 — The master plan records the rebuild's final integration gate as complete; its own detail plan
says "partial" and forbids exactly that claim.**

| | |
|---|---|
| Document:line | `observability-rebuild.md:1345` — "**Task 11.6 is complete** within the bounded non-container review scope: the product-event replay scratch DB lane still blocks…" |
| What is actually true | The detail record this sentence summarises is titled "**Task 11.6 partial backend acceptance refresh**" (`observability-rebuild-phase-11-audit-followups.md:384`) and ends *"do not claim product-event database replay or backfill idempotency from this run. Live UI, Grafana, Prometheus/Tempo retrieval, Phoenix traces/evaluations, pinned Collector Docker validation, single-host Docker runs, provider canaries/field paths, Azure support refresh and production queue restart proof remain owner-run."* Item 11.6 itself is unticked at `observability-rebuild.md:655`. `observability-telemetry-merge-and-completion.md:1723-1728` calls 11.6 the designated close-out gate with "**No live plan owns it**", and `observability-close-out-gate.md:136-163` enumerates **15 open items**, four of which it classifies "needs something we do not have". |
| What someone would build wrong | A reader resuming from the governing master plan skips the estate's final acceptance gate. The paragraph is not stale-by-neglect: it was edited on 2026-09-20 and two adjacent clauses in it carry explicit `**Corrected 2026-09-20:**` banners (`:1335`, `:1352`), so everything uncorrected in it reads as audited. |
| Severity | **P1** |

---

**F4 — Three rulings are recorded as "not yet executed" in one packet file and as executed-and-guarded
in another, with no banner on either.**

| | |
|---|---|
| Document:line | `obs-telemetry-merge-review-packet/F3-phase0-and-residual.md` row 6 (M-FALLBACK — "Not yet implemented — `dashboard-obsm` is at `4a2898b`, unmerged"), row 9 (M-LOCK — "Not yet executed — C2 in flight"), row 10 (M-WARN — "Not yet executed — C2 in flight"); provenance block at `:19-21` ("`api-obsm` `37121a3` (C2 executor in flight) · `dashboard-obsm` `4a2898b` (**not merged**, B2 in flight)") |
| What is actually true | Both phases closed. `dashboard-obsm` is at `3afd524` (verified, clean working tree) and `api-obsm` at `9812f44`+1. The same packet's `claims-C2-api.md` records M-LOCK as executed and verified (row C2-2: "`git diff 4da716f..9812f44 -- poetry.lock pyproject.toml` is **empty**") and M-WARN as **SETTLED** with named mutation proofs (rows C2-18, C2-19, C2-20). M-FALLBACK landed as B2.2 (`observability-telemetry-merge-and-completion.md:1168-1175`). The packet `README.md` lists all six files with no staleness note. |
| What someone would build wrong | The packet is explicitly the evidence base — "adjudicate the claims, not the code" — and F3's "Start here" section is the tier-2 OPEN list. An auditor working it would re-open three rulings that are settled, and could conclude the tenant-isolation warn-mode gate (M-WARN, tier 2) was never applied. |
| Severity | **P1** |

---

**F5 — The close-out gate's preconditions and sequencing are built on B2/C2 being in flight; both
closed three minutes after it was written.**

| | |
|---|---|
| Document:line | `observability-close-out-gate.md:6` (lists merged phases as "A, C1, B1, D, E and F" only), `:20-21` ("Two trees are being written in right now — `api-obsm` (C2) and `dashboard-obsm` (B2). Nothing below runs a lane inside either"), `:149` (C2 row: "dashboard half after B2"), `:156` (I1 row: "dashboard half after B2"), `:181` (Lane D: "**blocked until B2 lands**"), `:183-184` (Lane E: "the gate should re-run them once C2 closes") |
| What is actually true | `observability-telemetry-merge-and-completion.md:314-317` records **C2 and B2 as MERGED and CLOSED** (`api-obsm 9812f44`, `dashboard-obsm 3afd524`) — verified in both trees. File mtimes: close-out gate 09:02, merge plan 09:05. |
| What someone would build wrong | Whoever runs the gate holds back Lane D and Lane E for a blocker that is gone, and reports two of the fifteen items as blocked when they are runnable today. `dashboard-obsm` is clean and `npm run test:unit` is the stated command. |
| Severity | **P1** — timing, not error; but it is the operative sequencing document. |

---

**F6 — `observability-coverage-matrix.md` describes the pre-merge `dashboard` tree, and its own
disclaimer is now the stale part.**

| | |
|---|---|
| Document:line | `:22` ("**`dashboard-obsm` was NOT read.** It is mid-merge under another agent right now… the merged dashboard state is unresolved"), `:189-212` (§G, all 15 rows from `/home/aditya/Code/dashboard` @ `4a2898bd`), `:283` (the §G summary row) |
| What is actually true | `dashboard-obsm` is merged and clean at `3afd524`. The merge plan's B2 notes (`:1210-1213`) already establish that `M-FRONTEND needs no dashboard-repo action` and that the merge touched none of `lib/telemetry/events.ts`, `use-route-telemetry.ts`, `TelemetryProvider.tsx` or `events-catalogue.test.ts` — so most of §G is probably still correct, but **nothing in the corpus says which rows**, and §G is 15 of the 131 boundaries and 9 of the 46 "partly covered". |
| What someone would build wrong | R.4 (orphan analysis) is explicitly deferred to consume R.3's producer inventory. Running it against a §G that nobody has re-read against the merged tree produces orphan verdicts for the browser signal set that may not hold. Cheap to close — re-read §G against `3afd524`. |
| Severity | **P1** |

---

### P2

**F7 — `G.5` in the merge plan still carries the panel-scope paraphrase its own spec document was
written to correct.**

`observability-telemetry-merge-and-completion.md:595` — "the reason **three panel families** are
empty". `observability-g5-and-core-instrumentation-scope.md:234` and `:568-571` correct this
explicitly: it is **9 panels of 46**, in three panel *modules* — 7 of 9 in `quality`, 1 of 4 in
`reliability`, 1 of 7 in `operations` — and one of the nine (`clarification_rate_over_time`) is only
half dark. Verified in `/home/aditya/Code/core-obsm/core/resources/analytics/panels/`. An implementer
sizing G.5 from the merge plan budgets three whole tabs' worth of verification and looks for Grafana
boards; §1.8 records that **zero** Grafana panels read `chat_turn_facts`. **P2**

**F8 — Four different counts of the same fact: how many copilot-mro symbols api's `main.py` imports.**

- `:96` (§2.2) — "`flynapse_api/main.py` **top-level imports** `partition_boot_check_mode`, `PARTITION_REFUSAL_ERROR` and `PARTITION_REFUSAL_REMEDIATION`"
- `:306` and `:776` (§5.6) — "**three** symbols"
- `:404` (§3, Phase C2) — "**five** symbols that exist only on their copilot-mro branch"
- `:1329` (§7 correction) — "§3's C2 says 'five symbols'; measured, **four**"

Measured on `origin/obs-telemetry-merge` in `/home/aditya/Code/api-obsm`:
`flynapse_api/main.py:26-29` imports **two** symbols (`assert_partitions_provisioned`,
`partition_boot_check_mode`); the other two new symbols are imported by
`flynapse_api/startup/weaviate_partitions.py:8-12` (`PARTITION_REFUSAL_ERROR`,
`PARTITION_REFUSAL_REMEDIATION`, `WeaviatePartitionError`). Against copilot-mro mainline
(`/home/aditya/Code/copilot-mro/copilot_mro/app/services/weaviate_boot_check.py`), exactly **three**
of the five are new. The "four" at `:1329` is the merged tree's count — `weaviate_partitions.py:36-41`
gained `WEAVIATE_PARTITION_BOOT_CHECK_MODE_ENV` after the merge — so it is right about a different
tree and wrong as a correction of §3. §2.2's list of three names is right; its attribution of all
three to `main.py` is wrong. The phase gate (`import flynapse_api.main`) covers all of them
transitively, so nothing ships broken; the cost is a reader who cannot find two of the named symbols.
**P2**

**F9 — "nine depth-coupled test paths" is not reproducible; the measured figure is seven files, and
six of the seven were fixed — the seventh was deleted by M-ACCEPT.**

`:233` ("their new tests violate the last of these in **nine files**"), `:436` (D.7, "Fix the **nine**
depth-coupled test paths" against "paths fixed (**6 files**)"), and
`obs-telemetry-merge-review-packet/claims-D-copilot-mro-app.md` row 35 ("violated the repo's own
depth-coupling rule in nine files"). Measured in `copilot-mro-obsm` across the merge commit
`e26be7dd` vs its first parent: the merge introduced `Path(__file__)…parents[N]` into **seven** test
files — `tests/agent_sdk/core/test_agent_sdk_claude_log_privacy.py`,
`.../test_agent_sdk_ordinary_log_privacy.py`, `tests/api/observability/test_llm_turn_content_api.py`,
`tests/integration/observability_acceptance/test_acceptance_manager.py`,
`tests/unit/document_hub/test_document_hub_operation_telemetry.py`,
`tests/unit/observability/test_phase1c_nonagent_scope_guard.py`,
`tests/unit/observability/test_phoenix_evaluation_dependencies.py` — one occurrence each. Six survive
at HEAD with the pattern gone; the seventh (`test_acceptance_manager.py`) was dropped by M-ACCEPT.
The one merge-touched file still carrying a dirname chain
(`tests/agent_sdk/core/test_agent_sdk_tool_io_capture_sink.py:17`) derives from `agent_sdk_path()`,
not from `__file__`, so the guard at `tests/unit/infra/test_no_depth_coupled_paths.py` does not taint
it. An implementer reading D.7 as `[~]` goes hunting for three unfixed files that do not exist. **P2**

**F10 — §2.3a's packet totals are superseded by the packet's own README.**

`:222-228` — "**186 claims — 41 SETTLED, 60 ASSERTED, 85 OPEN** — and zero tier 0, **in all four
files** independently." `obs-telemetry-merge-review-packet/README.md` — "**269 claims. 64 SETTLED ·
85 ASSERTED · 120 OPEN.** **0 tier 0.** Tier 0 is empty in **all six** files." I recounted every row:
both are arithmetically correct, 186 being the first four files and 269 the six that now exist (see
the recount table below). The plan paragraph is dated the same day as the README and is not marked
superseded, so a reader of the plan gets a corpus two files smaller than it is. **P2**

**F11 — F3 packet is the "start here" file and its provenance block names three trees at commits
that have moved.**

`F3-phase0-and-residual.md:19-21` names `api-obsm 37121a3`, `dashboard-obsm 4a2898b (not merged)`,
`docs main (F executor in flight)`. Same root cause as F4; recorded separately because the
provenance block is what an auditor uses to decide whether a row is still current. **P2**

**F12 — D.9 is ticked `[x]` as CLOSED and recorded as deferred in the same file.**

`:441` — "`[x]` **D.9 CLOSED by Phase B2, 2026-09-20**". `:1707-1710` (§7 "Phase D — not done, and
why") — "**D.9 is deferred to Phase E/G by its own terms.**" The first is the later truth (B2 wired
the card, verified at `dashboard-obsm:app/(dashboard)/settings/department/dashboard/page.tsx` and
`lib/api/llm-observability-api.ts`); the "not done" entry is a Phase-D-era record that was never
struck the way the stale `oss_profile_smoke` entry above it was (`:1684-1688` carries a `~~struck~~`
+ "**Stale — struck 2026-09-20**"). **P2**

**F13 — D.13's breakdown of the 20 new failing ids accounts for 19.**

`:1452-1462` — "Of the 20: **4 were real defects** …; 2 are Phase E work (E.0a, E.0d); 2 are the
owner-blocked branch-hygiene guard; 1 is an ERROR id the FAILED-only filter never counted; and the
remaining **10 were import pollution** … **All 20 are now accounted for**." 4+2+2+1+10 = **19**. The
four "real ones" are enumerated and there are four, so the missing id is in one of the other
buckets. **P2**

**F14 — The coverage matrix promises three orphan-shaped observations and lists five.**

`observability-coverage-matrix.md:303` and `:333` both say "**three** things that looked
orphan-shaped"; the list at `:335-339` is numbered **1–5**. The two uncounted items (telegram-bot's
open-ended counter namespace; shift-optimizer's deliberately-absent stuck-run counter and its
post-`yield` solve histogram) are substantive R.4 inputs, so an R.4 executor working from the
sentence rather than the list drops two. **P2**

**F15 — Four `core/fastapi_app.py` line references in the corpus do not resolve, including two the
G.5 document introduced while correcting a third.**

Measured in `/home/aditya/Code/core-obsm` at `d7f7b54` (clean, the commit G.5 names):

| citation | says | actually |
|---|---|---|
| `observability-coverage-matrix.md:104` | `core/fastapi_app.py:148` = standalone core app | `:145-150` is the authorization-middleware comment block. G.5 `:354` flags exactly this as "FALSE as located" — and the matrix repeats it |
| `observability-coverage-matrix.md:175` | `core/fastapi_app.py:96` = core standalone startup | `:96` is the closing `]` of the OpenAPI tag list; `lifespan` is at `:100` |
| `observability-g5-and-core-instrumentation-scope.md:354`, `:583` | `app = FastAPI(...)` at **116** | `:117` |
| `observability-g5-and-core-instrumentation-scope.md:354`, `:583` | `if __name__ == "__main__"` at **263** (uvicorn "263–266") | `if __name__` at `:257`; `uvicorn.run(` at `:264` |

G.5's substantive point stands (line 148 is a comment; the standalone entry points are `lifespan`,
the module-level `app`, and `__main__`), but its replacement coordinates are off by 1 and 6.
`observability-coverage-matrix.md:89` cites `:118` for the same `app = FastAPI(` (`:117`). **P2**

**F16 — The G.5 document cites two different line numbers for one constant, one of them wrong.**

`observability-g5-and-core-instrumentation-scope.md:22` — "`PRIVATE_RELATIONS`" at
`copilot-mro-obsm/tests/registries/tables/test_postgres_table_definitions.py:833`.
`:620` (its own "Minor, but worth recording") — the same constant at `:790`. Measured: `:790`. **P2**

**F17 — `observability-close-out-gate.md:149` points at a "Part 5" that does not exist.**

The document has Parts 1–4 and then an unnumbered `### Where the source documents disagree with the
tree`. The content the pointer means is Part 4 item 3 (`:227-231`). **P2**

**F18 — Two figures for the same acceptance harness.**

`:643` (M-ACCEPT) — "~**4,600** lines"; `:795` (§5.7) — "the acceptance harness is **4,771** lines";
`F3-phase0-and-residual.md` row 11 — "~4,600 lines". The tree cannot settle it (the directories were
dropped by M-ACCEPT and are absent from `copilot-mro-obsm`); the branch could. No build impact. **P2**

**F19 — "Phase 11.6 is 16 boxes" is wrong, and so is the correction's explanation of where 16 came
from.**

`:1723` says 16 boxes. `observability-close-out-gate.md:136-139` corrects it to 15 open and guesses
the sixteenth is "the ticked cardinality check". Measured in
`observability-rebuild-phase-11-audit-followups.md`: Task 11.6 carries **8** checkboxes, 1 ticked
(`:294`, metric cardinality) → 7 open; §6 Review checklist carries **9**, 1 ticked (`:319`) → 8 open.
So **15 open, 17 total** — neither 16 nor "15 + the one ticked box". The close-out gate's operative
number (15) is right. **P2**

---

## Numbers I recounted

Every count in the corpus I could re-derive. Matches are listed too.

| Where | Stated | Counted | Match |
|---|---|---|---|
| `merge:222` packet totals | 186 claims / 41 S / 60 A / 85 OPEN, "four files" | 186 / 41 / 60 / 85 over F3+C1B1+D+E | ✅ arithmetic, ❌ superseded (F10) |
| `packet/README.md` totals | 269 claims / 64 S / 85 A / 120 OPEN, 6 files, 0 tier 0 | rows 66+36+45+39+35+48 = **269**; S 5+4+22+12+20+1 = **64**; A 16+23+4+15+6+21 = **85**; O 45+9+9+18+13+26 = **120** | ✅ exact |
| `packet/README.md` "45% OPEN" | 45% | 120/269 = 44.6% | ✅ |
| `packet/README.md` per-file rows | 66/36/45/39/35/48 | 66/36/45/39/35/48 | ✅ exact |
| `merge:1717` master-plan walk | **181 open checkboxes** | `[ ]` across `observability-rebuild.md` (75) + the 10 phase plans + `observability-merge-completion.md` = **181** | ✅ exact — but the sentence says "the master plan's own checkboxes", and that file alone has 75 |
| `merge:1717` disposition split | 119 + 41 + 18 + 2 + 1 | = 181 | ✅ |
| `merge:1723` 11.6 | "16 boxes" | 17 total, **15 open** (8 boxes/1 ticked + 9 boxes/1 ticked) | ❌ (F19) |
| `close-out:136` 11.6 | "seven open checks (C1–C8, C6 ticked)" + "eight open invariants (I1–I8)" = 15 | 7 + 8 = 15 | ✅ exact |
| `merge:233`, `:436` depth-coupled | nine files | **seven** introduced by the merge, one occurrence each; 6 fixed, 1 (`test_acceptance_manager.py`) dropped by M-ACCEPT | ❌ (F9) |
| `merge:1306` C2 mutations | 24 labels across 23 runs (M1–M5, W1–W7, G1–G5, H1–H3, F1/F2/F3b, P1) | 5+7+5+3+3+1 = **24**; minus the G2+G3 joint run = **23** | ✅ exact |
| `merge:1008` silent-merge register | 65 theirs-only production files | `copilot_mro/**.py` changed by theirs but not ours across the merge base = **65** | ✅ exact |
| `merge:1008` | 22 in the intersection | same scope = **14**; whole-repo intersection = 42; non-test = 32 | ❌ not reproducible at any scope I tried |
| `merge:1850` | "three times as many" theirs-only | 65/14 = 4.6×; 65/22 = 3× | follows from the above |
| `merge:2.2` repo table (core/utils/api) | our tips `e10a9ce`/`289ba71`/`44bd8d1`; their tips `8b7dfad`/`cfcf0fd`/`6f22498`; bases `988571b`/`9f74a11`/`a19a931`; 5/3/3 commits | all six SHAs and all three commit counts reproduce exactly | ✅ exact |
| `merge:2.4` otel modules | "seven otel test modules exist only on our side" | 7 files present at `e26be7dd^1` and absent at `^2` (6 are `test_*.py`, one is the `_versions_md.py` helper) | ✅ (wording: 7 files / 6 test modules) |
| `merge:2.4` full-suite pollution | 116 failed + 15 errors = 131; per-directory 37; "roughly 94 … pollution" | 116+15 = 131 ✅; 131−37 = 94 ✅ | ✅ internally consistent (not re-run) |
| `merge:1452` D.13 breakdown | "Of the 20: 4 + 2 + 2 + 1 + 10" | = **19** | ❌ (F13) |
| `merge:1488` Phase E otel gate | 135 = 111 + 24; 156 = 130 + 26 | both add up | ✅ |
| `merge:1572` validate.sh | 9 validates, 18 starts (4×2=8 validates ×2 modes=16 starts, +1 validate +2 starts) | 8+1 = 9 ✅; 16+2 = 18 ✅ | ✅ |
| `merge:347`, `:1110` B1 lane | 2866 / 2 / 2 vs 2829 / 2 / 2 | consistent across both mentions | ✅ (not re-run) |
| `merge:643` vs `:795` M-ACCEPT size | ~4,600 vs 4,771 | unresolvable in the merged tree | ❌ (F18) |
| `close-out:154` C7 inventory | 14 declared series — 9 wired, 5 dark, 0 live; 5 span signals all wired | at `ea0ac559`: `SERIES` = 14 entries, **9 wired / 5 dark / 0 live**; `SPAN_SIGNALS` = **5**, all wired | ✅ exact |
| `close-out:154` dark set | the 5 dark are G.6's three + G.4's two | `agent.subagent.calls`, `agent.subagent.duration_seconds`, `agent.ledger.write_failures`, `claude_code.token.usage`, `claude_code.cost.usage` | ✅ exact |
| `coverage-matrix:286` totals | 131 boundaries / 46 / 46 / 39 | every section sums correctly, and every section's boundary count matches its table rows minus the stated `n/a` exclusions (A 23−2, D 5−1, E 9−2, G 18−3, H-tg 29−1, H-so 16−1) | ✅ arithmetic exact — but see F2, which moves §C to 15 and the total to 45 |
| `coverage-matrix:333` | "three things that looked orphan-shaped" | 5 numbered items | ❌ (F14) |
| `coverage-matrix:288` | "8 of the 16" §C rows covered only by the HTTP fallback | 8 named, and §C fully-covered is 16 as stated | ✅ internally |
| `g5:236` panels | 9 of 46 registered panels, 3 of 7 modules; 7 quality / 1 reliability / 1 operations | table lists 7+1+1 = 9 ✅ | ✅ internally |
| `g5:357` core size | 86 routes vs copilot_mro 85; 138 files / 30,896 lines vs 573 / 245,487 | not recounted | — |
| `evals:1.1` measures | "Seven measures … six LLM-judged, one code-computed" | 7 listed at `:47-51`; `_KNOWN_LABELS_BY_ANNOTATION` at `contracts.py:17` | ✅ |

---

## References I resolved

`✅` = resolves exactly · `≈` = within a line or two of the construct named · `❌` = does not resolve.

**Verified, resolves:**

- ✅ `core-obsm/core/resources/analytics/analytics_endpoints.py:44` — `def is_tenant_admin(...)`, body is `is_tenant_owner` → `has_capability(auth_context, "view_dashboard")`. B1.2 (`merge:340`) is **correct**, including the follow-on claim that the dashboard checks the same gate before asking: `dashboard-obsm/app/(dashboard)/settings/department/dashboard/page.tsx:405` reads `hasCapability(PERMISSION_NAMES.VIEW_DASHBOARD)` and `lib/auth/PermissionContext.tsx:430` short-circuits `if (isTenantOwner) return true`. The 403 branch is unreachable today, as stated.
- ✅ `core-obsm/tests/unit/db/test_tenanted_write_paths.py:59` — `test_on_conflict_targets_lead_with_the_tenancy_columns` (merge `:834`).
- ✅ `core-obsm/core/resources/analytics/events_endpoints.py:67` — `@router.post("/events")`.
- ✅ `core-obsm/core/resources/logging/logging_endpoints.py` — `:105` rate-limit warning, `:118` `_require_json_content_type`, `:325/:331/:337/:343` the four ingest routes, `:350` health. `≈` `:238` drop-on-unset, `:250/:261/:269` the three collector-failure lines (G.5 cites ranges, the matrix cites `:249,258,271`).
- ✅ `copilot-mro-obsm/copilot_mro/app/db/chat_history/blocks.py` — `save_block` `:540`, `with postgres.connection()` `:577`, `SET LOCAL statement_timeout` `:581`, `apply_session_tenancy` `:585`, `_LOCK_CHAT_FOR_SAVE_SQL` `:589`, `_INSERT_BLOCK_SQL` `:615`, `if cur.rowcount == 1` `:634`, `conn.commit()` `:656`. G.5 §1.2's whole line table checks out.
- ✅ `copilot-mro-obsm/copilot_mro/app/api/chat_management.py` — `:1086` and `:1449` are the two "Enhanced chat request received" sites, both binding `message_chars` (merge `:578-581`, G.2); `:1339` and `:1713` the two `save_block` call sites (G.5); `≈` `:1212/:1222/:1332/:1576/:1586/:1734` the span opens (the string literal sits one line below the `start_as_current_span(` the matrix cites).
- ✅ `copilot-mro-obsm/copilot_mro/app/api/llm_observability.py:191` — `error_type=type(exc).__name__` (merge `:962`).
- ✅ `copilot-mro-obsm/README.md:122` — "- Metrics: `GET /metrics`" (merge `:1044`).
- ✅ `copilot-mro-obsm/.env.sample:11` `OTEL_ENDPOINT=…`, `:12` `OTEL_SERVICE_NAME=…` (merge `:1738-1741`).
- ✅ `copilot-mro-obsm/tests/unit/observability/test_phase1c_nonagent_scope_guard.py` — four SHA anchors at `:61,:62,:65,:67` and the `obs-telemetry-merge` branch-name disarm at `:234` (merge `:1698-1706`). Two of the four paths Phase E names as non-existent confirmed missing: `deployment/docker-compose.phoenix-smoke.yml`, `deployment/otel/env/oss-phoenix.env.example`; the `durability-production-*.yaml` rename confirmed. *The file is modified in the working tree right now and its own comment has been rewritten to "ten of its thirty-one entries no longer exist".*
- ✅ `utils-obsm/utils/s3_service.py:226` (`s3.download` span open), `utils/weaviate_service.py:1011` (`weaviate.hybrid_search`), `utils/observability/bootstrap.py:33-42` (the six instrumentors + the botocore/fastapi exclusion comment), `utils/observability/log_bridge.py:206-209` (idempotent-by-module-flag).
- ✅ `api-obsm/flynapse_api/telemetry/http_server.py:56` (health exclusions), `:64` (`INGEST_EXCLUDED_URLS`), `:67` (`DEFAULT_EXCLUDED_URLS`); `flynapse_api/main.py:352` (`instrument_gateway(app, excluded_urls=…)`), `:398/:411/:424` (the three mounts), `:520` (`logger.bind(**failure_fields(exc)).error("Unhandled exception")`); `flynapse_api/telemetry/run_span.py:8-10` (the "no Link, scheduler not instrumented until Stream L" comment, quoted verbatim).
- ✅ `iac/apprunner.tf:41` and `iac/lambda.tf:108` — both `WEAVIATE_URL = "http://…:8080"`, the two sites C1.5 names as owing a `WEAVIATE_GRPC_PORT` knob (merge `:387`). Both still `http://`, as the item says.
- ✅ `copilot-mro-obsm/copilot_mro/app/services/agent_evaluation/contracts.py:17` — `_KNOWN_LABELS_BY_ANNOTATION` (evals `:38`).
- ✅ `copilot-mro/pyproject.toml:91` — `prometheus-client = "*"` (G.2, `merge:584`). Zero `prometheus_client` imports in the repo, as claimed. *Already removed in the `copilot-mro-obsm` working tree by the in-flight implementer; the item is being worked.*
- ✅ `copilot-mro-obsm/copilot_mro/app/services/agent_shared/telemetry.py:1447,1452` at `ea0ac559` — the two subagent instrument **declarations** (see F2; the matrix reads them as call sites).
- ✅ `dashboard_profiles` has no writer anywhere — the only statement in the estate is `SELECT` at `core-obsm/core/resources/analytics/dashboard_profiles.py:132`. §5.5's P1 and B2-R3 (`merge:1219-1220`) are **correct**.

**Failed to resolve:**

- ❌ `observability-coverage-matrix.md:104` → `core/fastapi_app.py:148` (F15)
- ❌ `observability-coverage-matrix.md:175` → `core/fastapi_app.py:96` (F15)
- ❌ `observability-coverage-matrix.md:42` → `utils-obsm/utils/observability/log_bridge.py:194` for `install()`; `def install(` is at `:203`, and `:194` is `setattr(log_record, key, value)`
- ❌ `observability-coverage-matrix.md:47` → `utils/observability/intercept.py:70` for `install()`; actually `:74`
- ❌ `observability-coverage-matrix.md:49` → `utils/logging_config.py:47` for `setup_logging()`; actually `:48`
- ❌ `observability-g5-and-core-instrumentation-scope.md:22` → `test_postgres_table_definitions.py:833` for `PRIVATE_RELATIONS`; actually `:790`, which the same document gets right at `:620` (F16)
- ❌ `observability-g5-and-core-instrumentation-scope.md:354`, `:583` → `app = FastAPI` at 116 (actually 117) and `if __name__` at 263 (actually 257) (F15)
- ❌ `observability-coverage-matrix.md:89` → `core/fastapi_app.py:118` (actually `:117`) — off by one, listed for completeness
- ❌ `observability-close-out-gate.md:149` → "see Part 5"; no Part 5 exists (F17)

Not checked (out of the sampled set, and no reason to doubt them): the ~90 further `file:line`
citations in `observability-coverage-matrix.md` §§B, G and H (telegram-bot and shift-optimizer),
and the per-row citations in `claims-D`, `claims-E` and `claims-phase6`.

---

## What I could not verify, and what would settle it

1. **The otel lane's current numbers.** `merge:1488` records `156 collected / 130 passed / 26
   skipped` for `tests/integration/otel` after Phase E; `close-out:152` and `:179` record
   `132 passed / 26 skipped` (= 158 collected) for the same lane the same day. The most likely
   explanation is that the gate measured `d8d2570c` ("Guards for the two defects the vocabulary
   checks could not see", +2 tests) while the plan measured `ea0ac559` — but neither document names
   its commit. *Settled by:* one run of
   `cd /home/aditya/Code/api && DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=/home/aditya/Code/copilot-mro-obsm poetry run pytest -q ../copilot-mro-obsm/tests/integration/otel`
   with the commit recorded beside the number. I did not run it — the tree has an implementer in it
   and I am read-only.
2. **Every other lane number** (B1 2866/2/2, C1 1209/1190, C2 1170/1134, B2 2502/2475, D.13's 32/41/20,
   the 131-vs-37 pollution figures, `close-out:99-102`'s scratch-lane table). All are internally
   consistent and none is reproducible without running suites against a shared test database that
   two implementers are using. *Settled by:* re-running each after the phases hand their trees back.
3. **Database facts.** `close-out:128-130` ("`copilot_mro_test` carries 112 public tables and lacks
   `llm_turn_content`, which `copilot_mro` (113) has") and the DB-step acceptance table at
   `merge:1782-1814` (RLS enabled+forced, `1487 statements`, `chunks` 475,277 rows across two
   tenants). Consistent with each other and with B1's note that `llm_turn_content` is a copilot-mro
   registry table, so the test DB legitimately lacks it — but I did not query Postgres (the local DB
   MCPs are manual-invoke only). *Settled by:* the four catalogue queries the DB-step section already
   names.
4. **The acceptance-harness line count** (~4,600 vs 4,771). The directories were dropped by M-ACCEPT
   and are absent from the merged tree. *Settled by:*
   `git -C /home/aditya/Code/copilot-mro-obsm ls-tree -r origin/obs-telemetry-merge -- deployment/observability-acceptance tests/integration/observability_acceptance`
   piped through a line count.
5. **"22 in the intersection"** (`merge:1008`). I could not find a scope that yields 22: the same
   scope that yields the exactly-correct 65 yields 14, and the whole-repo intersection is 42. The
   number may have been taken over a different file set. *Settled by:* the author restating the
   scope, or recomputing with `git diff --name-only <base> <side>` over the stated one.
6. **Whether §G of the coverage matrix still holds against merged `dashboard`** (F6). *Settled by:*
   re-reading the 15 rows against `dashboard-obsm` `3afd524`; the B2 notes suggest most survive.
7. **`g5:357`'s size comparison** (86 vs 85 routes; 138/30,896 vs 573/245,487 lines). Not recounted;
   the claim is hedged ("largest route surface, by one route") and nothing is built on it.
8. **Whether the in-flight `copilot-mro-obsm` subagent wiring is intended to close G.6.** The
   uncommitted diff wires `record_subagent` on both runtimes and flips the inventory to `"wired"`,
   which is exactly G.6's first clause — but no plan item is ticked and no phase note mentions it.
   *Settled by:* the implementer's phase record when it lands.

---

## Summary

**Counts:** 1 × P0 · 5 × P1 · 13 × P2.

**The five worst:**

1. **P0 (F1)** — The judge-side residency allowlist belongs to no phase. The evals plan states as
   settled fact that "the merge owns it" and refuses to build it; no merge-plan item does, and the
   merge plan's own unticked owner decision says so. The merged tree ships the Phoenix eval suite
   with a free-form `provider` string and a runbook documenting `--provider openai`. The exporter
   half is simultaneously claimed by merge-plan G.8 and declared "unclaimed by any phase" by the
   evals plan.
2. **P1 (F2)** — `observability-coverage-matrix.md:147` marks the subagent boundary fully covered
   with no gap. At the commit it cites, `record_subagent` has no caller and the repo's own inventory
   marks both instruments `"dark"`. R.3 is the gap table G.6 and R.4 are meant to be planned from.
3. **P1 (F3)** — `observability-rebuild.md:1345` records "Task 11.6 is complete" — the rebuild's
   final integration gate — where its own detail plan says "partial" and explicitly forbids the
   claim, and where a separate document enumerates 15 open items.
4. **P1 (F4/F11)** — The review packet's "start here" file records M-FALLBACK, M-LOCK and M-WARN as
   "not yet executed" while a sibling file in the same packet records two of them SETTLED with named
   mutation proofs. An auditor would re-open a tier-2 tenancy ruling that is closed.
5. **P1 (F5)** — The close-out gate's preconditions, its "two trees being written in right now"
   banner, and Lane D's "blocked until B2 lands" were overtaken three minutes after it was written.

**Is this corpus safe to hand to a new implementer?** **Conditionally — with one blocker.**

The quality is high and unusually well self-corrected: the §2.2 repo table, the mutation-label
arithmetic, the 181-checkbox walk, the 269-claim packet totals, the 65 theirs-only files, the
close-out gate's 15 items and its C7 inventory all reproduce **exactly** against the trees and the
code, and the G.5 document exists specifically to correct a brief's paraphrases — which is the
discipline this audit was commissioned to check for. Most of what I found is staleness introduced by
three phases closing inside a single morning, not fabrication.

But **F1 must be resolved before anyone executes Phase G or starts the evals project**, because both
documents point at each other for the one control that keeps customer manual text out of a third-party
vendor, and the code that would send it is already merged. Fix that, ratify F2 (a one-line correction
plus the two summary counts), strike F3's "complete", and put a dated staleness banner on
`observability-close-out-gate.md` and `obs-telemetry-merge-review-packet/F3-phase0-and-residual.md`.
The remaining P2s are clerical and would not change what gets built.

One structural note the corpus itself half-states: **every finding above that had teeth came from a
document paraphrasing a *second* document rather than the code.** F2 read an instrument declaration
as a call site; F3 compressed "partial" to "complete"; F8 restated a symbol list four ways; F1 is two
plans each citing the other's ruling. The documents that went to the tree first — the G.5 spec, the
close-out gate, the C2 claims file — are the ones that hold up.
