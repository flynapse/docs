# Claims — Phase E: copilot-mro deployment half, plus the iac half of the same work

**Scope.** Everything the deployment half of the copilot-mro merge decided, plus the CloudWatch
templates and alarms in `iac` that carry the same decisions. Phase D (the application half) is a
different packet; anything at or before `6dc3160e` belongs there.

| repo | worktree | branch | range | commits |
|---|---|---|---|---|
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `6dc3160e..ea0ac559` | `2e965ea0`, `2e4bbeb8`, `0d0b752d`, `1eec7c49`, `438c6a5d`, `ea0ac559` |
| iac | `/home/aditya/Code/iac` | `obs-merge` (new branch, `main` untouched) | `f35ec20..3068b47` | `35c7e87`, `3068b47` |

**The recorded gate.** `tests/integration/otel`: **156 collected / 130 passed / 26 skipped / 0
failed**, against a measured pre-merge baseline of **135 / 111 / 24** at `langgraph-merge`
`417df303`. `OTEL_RULES_CHECK=1`: 143 passed / 13 skipped. Both container smokes run explicitly with
`OTEL_COMPOSE_SMOKE=1`: `test_oss_profile_smoke` 8 passed, `test_grafana_provisioning_smoke` 2
passed. `deployment/otel/validate.sh`: **8 validates + 18 real container starts**, all healthy.
`tests/unit/observability` + `tests/unit/infra`: 237 passed, 2 failed — both the owner-blocked
phase1c guard (row E33), unchanged.

*Arithmetic note for the auditor:* "8 validates" counts 4 profiles × 2 compositions. The
aws+phoenix composition adds a ninth validate and the last 2 of the 18 starts; the plan states it
that way in §7 and abbreviates it to "8 validates" in the summary line. 18 starts = 4 × 2 × 2 + 2.

**The central design decision.** The three-state signal vocabulary —
`DARK until <reason>` / `WIRED <YYYY-MM-DD>, retrieval unproved: <what emits it>` /
`LIVE since <probe> (<YYYY-MM-DD>)` — and the derived emitted-series inventory
(`tests/integration/otel/_emitted_series.py`) that the board lint and the alert lint both read,
proved against `copilot_mro/app/services/agent_shared/telemetry.py` by AST. Rows E1–E8 and E16,
E18, E20 are that contract; rows I1–I6 are its CloudWatch dialect.

Every `File:line` below was resolved in the tree as it stands today.

---

## copilot-mro — `copilot-mro-obsm`, `6dc3160e..ea0ac559`

| # | Repo | File:line | Decision taken | Why | Evidence it is right | Guard test | Mutation-proved? | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | copilot-mro | `tests/integration/otel/_emitted_series.py:195-206` | Three states with one regex grammar each replace the two-state DARK/LIVE wording | 9 of the 13 red panels ARE emitted, 4 are not; neither side's vocabulary could hold both | Merged tree was RED on 13 panels across 3 boards before; green after, same lint | `test_dark_panel_notes_are_present` (`test_grafana_dashboards.py:228`); `test_pending_rule_notes_are_present_only_for_unemitted_series` (`test_alert_rules_layout.py:216`) | partially recorded — "a WIRED panel described as DARK", "a DARK rule described as WIRED"; failing test not named | 2 | F1 | SETTLED |
| E2 | copilot-mro | `_emitted_series.py:65-140` (14 `Series` entries) | One derived inventory replaces two hand-maintained allow-lists | The tuples named 4 series between them, so a 5th was checked by nothing (E.0i) | Proved against `telemetry.py` by AST on six limbs | `test_emitted_series_inventory.py:188,207,232,255,268,281` | partially recorded — Counter/Histogram flip in one path and in both; an uninventoried instrument | 2 | F1 | SETTLED |
| E3 | copilot-mro | `_emitted_series.py:155-180` (5 `SpanSignal` entries) | Span names and span attributes are inventoried contract, not prose | The turn-explorer board rests entirely on span names/attributes | AST evidence: `span.set_attribute` keys, span-name literals, `attributes=` dict keys | `test_every_span_signal_is_backed_by_a_span_the_code_really_opens` (`test_emitted_series_inventory.py:309`) | **no post-fix mutation named.** Pre-fix: deleting `span.set_attribute("agent.outcome", outcome)` left every lane green — that is what proved the gap, not the fix | 2 | F1 | ASSERTED |
| E4 | copilot-mro | `_emitted_series.py:221` (`_UNIT_SUFFIX`), `:224` (`base_name`) | The declared unit is part of the exported Prometheus NAME (`s`→`_seconds`; `1` and braced units append nothing) | A wrong unit silently renames the series and every board on it | MEASURED, not only derived: one synthetic datapoint per instrument through the pinned collector | `test_prometheus_serves_the_exact_names_the_inventory_computes` (`test_oss_profile_smoke.py:851`, `OTEL_COMPOSE_SMOKE=1`) | **yes** — corrupt `s -> _seconds` to `_secs`; the smoke named all nine dead series | 2 | F1 | SETTLED |
| E5 | copilot-mro | `_emitted_series.py:208-209`, `:233-240` | counter → `_total`; histogram → `_sum`/`_count`/`_bucket`; a wrong-family reference is a lint failure | A Counter/Histogram flip empties a panel in total silence | Same measured smoke; `Reference.wrong_family` offender in the shared lint | board + rule lints (E1) and the measured smoke (E4) | partially recorded — "the `_total` regression put back"; failing test not named | 2 | F1 | SETTLED |
| E6 | copilot-mro | `test_emitted_series_inventory.py:281` | A recorder has a production call site **exactly when** the inventory says the series is not dark | The only limb that tells `agent.subagent.*` (declared, recorded in the facade, called by nothing) from the rest | `record_subagent` has no caller anywhere in `copilot_mro/` | `test_a_recorder_has_a_production_call_site_exactly_when_the_series_is_not_dark` | partially recorded — "`record_subagent` wired, making a dark series live"; failing test not named | 2 | F1 | SETTLED |
| E7 | copilot-mro | `test_emitted_series_inventory.py:117-140` | `_call_sites()` reads AST `Attribute` nodes, not a substring grep | `# TODO: re-enable telemetry.record_turn` satisfied the substring form — the reachability limb the whole WIRED claim rests on | Review finding, fixed in `ea0ac559` | same test as E6 | no post-fix mutation named; the pre-fix defect was demonstrated | 1 | F3 | ASSERTED |
| E8 | copilot-mro | `test_emitted_series_inventory.py:369-412` | Label VALUES checked against the dispatcher's own `Literal["success","failure"]`, read by AST | `tool_outcome="error"` shipped once and matched nothing; label values are outside `classify()`'s reach | Annotation read from `agent_shared/dispatcher.py`, never copied | `test_tool_outcome_filters_use_the_dispatchers_own_literals` (`:390`) | partially recorded — ledger CHECKPOINT 7 says this batch was "all mutation-proved"; no test named | 2 | F1 | SETTLED |
| E9 | copilot-mro | `_emitted_series.py:185-192`; `test_emitted_series_inventory.py:344` | `KNOWN_LABELS` cannot shadow an inventoried signal | One line in that frozenset disarmed the lint for any series — the third allow-list, exactly what E.0i abolished | Review finding | `test_known_labels_cannot_shadow_a_series` | partially recorded — same "all mutation-proved" batch; no test named | 1 | F3 | SETTLED |
| E10 | copilot-mro | `_emitted_series.py:302-365` | `signal_state_offenders()` is ONE body; both lints call it | §8: "a guard with two bodies is a guard with none" — they were two copies for one review round | Both import it: `test_grafana_dashboards.py:32`, `test_alert_rules_layout.py:48` | n/a — structural property of the import graph | no | 1 | F3 | ASSERTED |
| E11 | copilot-mro | `_emitted_series.py:337-347` | Every state the query touches needs its note; a note for a state it does NOT touch is the offence | The old "any other state's grammar is an offence" rule made a mixed-state panel unsatisfiable | Review finding | board + rule lints | partially recorded — same batch; no test named | 1 | F3 | SETTLED |
| E12 | copilot-mro | `_emitted_series.py:352-365` | The prose-vouch check runs even when the query reads nothing inventoried | An early return made it inert in precisely the repointed-panel case it existed to catch | "One check I wrote was inert, and only a mutation showed it" | board + rule lints | partially recorded — mutation (repoint the panel, leave the prose) recorded; failing test not named | 1 | F3 | SETTLED |
| E13 | copilot-mro | `deployment/observability-local/grafana/provisioning/datasources/datasources.yml:41-58` | `Flynapse Postgres` / uid `flynapse-postgres` restored, `user: flynapse_readonly` | M-GRAFANA keeps it; four panels read the uid and none of them conflicted | Container smoke lists all four uids on a cold Grafana | `test_flynapse_postgres_datasource_is_declared_kept_and_used` (`test_grafana_dashboards.py:284`) + `test_grafana_provisioning_smoke` (2 passed) | **yes** — limb 1: delete the entry | 1 | F2 | SETTLED |
| E14 | copilot-mro | same file, `deleteDatasources` block absent (was lines 3-8 pre-merge) | The incoming `deleteDatasources: [{name: Flynapse Postgres, orgId: 1}]` is dropped | It is destructive at EVERY Grafana boot and cleans persisted Grafana DBs, so re-adding the file later does not undo it | Positive guard, per §2.2a | same test, limb 2 | **yes** — limb 2: re-add `deleteDatasources` | 1 | F2 | SETTLED |
| E15 | copilot-mro | `.../dashboards/flynapse/llm-agents.json:200-243` | Exact-spend panels restored as ids 11 and 12 on `flynapse-postgres` | Spec §7.1: a USD tile renders only beside its incompleteness companion, which the metered counters have not got | Guard pins the four readers by board uid + panel id | same test, limb 3 (`M_GRAFANA_POSTGRES_PANELS`, `:278`) | **yes** — limb 3: delete panels 11+12, the move that makes deleting the datasource stop looking like a regression | 1 | F2 | SETTLED |
| E16 | copilot-mro | `llm-agents.json:25,94`; `deployment/otel/dashboards/CATALOGUE.md:149,170,174,221,241` | Token-usage queries return to the `_sum` family | `gen_ai.client.token.usage` is a Histogram (M-TOKENUSAGE); the merge's `_total` rewrite matches nothing at all | Inventory declares `kind=histogram`; measured smoke serves `_sum`/`_count`/`_bucket` | board lint `wrong_family` (E5) + measured smoke (E4) | partially recorded — "the `_total` regression put back"; failing test not named | 2 | F1 | SETTLED |
| E17 | copilot-mro | `.../dashboards/flynapse/frontend.json:356-371` | "Slowest Pages" grafted as id 19 at `{h:8,w:12,x:0,y:72}`, described **WIRED**, not LIVE and not DARK | The only additive panel on their 3-panel board; our 18-panel board was byte-identical to ours and won the merge | `browser.app.boot` emitter is unconditional; the collector allow-list already passes `load_complete_ms` and `entry_route_pattern`; no probe window has confirmed the Loki record | `test_dark_panel_notes_are_present` browser half (`BROWSER_STATE_NOTE`, `test_grafana_dashboards.py:102`) | no | 1 | F2 | ASSERTED |
| E18 | copilot-mro | `deployment/observability-local/rules/prometheus/flynapse-agent-alerts.yml:1-7,22-72` | Four agent rule descriptions moved to the three-state grammar; file header states the lint decides the state from the emitter | An operator who reads "DARK" on a wired series dismisses a real alert; `STATIC-MAPPED` / `PENDING` retired | Classified against the inventory, not a tuple | `test_pending_rule_notes_are_present_only_for_unemitted_series` (`:216`) | partially recorded — "a DARK rule described as WIRED"; failing test not named | 2 | F1 | SETTLED |
| E19 | copilot-mro | `test_alert_rules_layout.py:216` (and `:103` note) | `PENDING_RULE_SERIES` / `EMITTED_RULE_SERIES` deleted outright, not adopted then fixed | E.5 said adopt their guard; E.0i named its defect — §8: when two plan items disagree, execute the later one | The allow-list WAS the hole: a rule on any fifth series fell through both tuples | same test | partially recorded — "a panel/rule on an uninventoried series"; failing test not named | 1 | F2 | SETTLED |
| E20 | copilot-mro | `.../dashboards/flynapse/agent-turn-explorer.json:4,18,36,53` | Board + three panels to WIRED; the failed-turn selector is documented as the `agent.outcome` ATTRIBUTE, not TraceQL `status = error` | The runtime sets no intrinsic span status for a handled failed turn, so a status selector finds nothing | Same fact carried by the `agent.outcome` SPAN_SIGNALS note | board lint (E1) | partially recorded — WIRED/DARK panel mutations; failing test not named | 2 | F1 | SETTLED |
| E21 | copilot-mro | `.../dashboards/flynapse/platform-health.json:4,72` | "Ledger write failures" = `DARK until Task R …` ("an absent instrument, not an unreached recorder"); board description records which panels left Grafana and which stay | The two business panels stay deleted (M-GRAFANA accepts that half); the exact-spend pair and the two fn-frontend document panels stay | Inventory entry `agent.ledger.write_failures` has `instrument_attr=None` | board lint + `test_entries_without_an_instrument_really_have_none` (`:255`) | partially recorded | 1 | F2 | SETTLED |
| E22 | copilot-mro | `deployment/otel/validate.sh:54-133,182-183,201-202` | `validate.sh` STARTS every profile on the pinned image and polls `health_check`, in both compositions | `otelcol validate` never builds a component: rc=0 over a collector that dies at boot — the P0-COLLECTOR signature | First ever run of the New Relic overlay and of all four durability fragments; 8 validates + 18 healthy starts | none in pytest — the script itself is the check | **yes** — point `compaction.directory` at the read-only config mount: `validate` answers `ok oss`, the start fails `failed to build extensions: failed to create extension "file_storage/production_queue": mkdir …: read-only file system` | 1 | F2 | SETTLED |
| E23 | copilot-mro | `validate.sh:22-30,66-76` | TWO start passes: `shipped` (`--tmpfs /tmp:mode=1777`, nothing else overridden) and `mounted` (bind mounts) | The first version passed `-e OTEL_FILE_STORAGE_DIR=…` on both passes, replacing the one variable whose real value caused P0-COLLECTOR | The review's severest finding, and it was the implementer's own work | the script | **yes** — drop the tmpfs from the shipped pass and it fails `failed to build extensions … mkdir /tmp: permission denied` | 1 | F3 | SETTLED |
| E24 | copilot-mro | `validate.sh:124-126` | The mounted pass asserts both the queue AND the compaction directory exist | `create_directory: true` creating the COMPACTION directory was a README claim nothing checked | Both directories created on every mounted start | the script | shares E22's mutation; no separate mutation for the compaction assertion | 1 | F2 | SETTLED |
| E25 | copilot-mro | `validate.sh:207-236` | A ninth composition, **aws+phoenix**, is built and started | `iac/demo_ec2_setup.sh` layers `content-phoenix.yaml` onto `backend-aws.yaml`, but the loop appended the fragment only for profiles whose own env example sets `PHOENIX_ENDPOINT`, and `env/aws.env.example` names no `PHOENIX_*` | "It loads and starts; it was unproven, not broken" — `content-phoenix.yaml` reads `${env:PHOENIX_ENDPOINT}` with no default, which fails at build, not at parse | the script | no | 1 | F2 | ASSERTED |
| E26 | copilot-mro | `deployment/otel/README.md:107-108,130-166` | Documented: the storage extension is instantiated on EVERY profile; production must bind-mount outside the tmpfs; the queue is not an outage budget (`max_elapsed_time: 5m`); the POC "can boot without a host-mounted volume" claim is withdrawn; `PHOENIX_*` scope is oss **and** aws | E.2/E.3 plus findings 1 and 3; the shipped default is a durable-looking queue on a RAM disk | The doc names the guard that blocks fixing the four in-repo composes: `test_collector_profiles.py:688` forbids a collector volume naming `otelcol-storage` there, so a production compose is a NEW file | none — prose | no | 1 | F3 | **OPEN** |
| E27 | copilot-mro | `test_compose_image_pins.py:20-28`; `test_compose_port_bindings.py:20-27,45-49` | Both stale four-file tuples widened to six; the two Phoenix overlays publish loopback-only (`set()`) | E.0h: the Phoenix split moved a PINNED image into two files neither guard scanned — and `test_compose_port_bindings.py` carried the same tuple, which the plan did not name | Both overlays are correctly pinned today and nothing would have noticed if they stopped being | `test_no_floating_tag_in_any_compose_file`, `test_observability_images_match_the_pins`, `test_every_public_port_is_on_the_allow_list` | no | 1 | F2 | ASSERTED |
| E28 | copilot-mro | `deployment/otel/smoke/docker-compose.smoke.yml:1-13` | Header documents the three-file invocation and says the Phoenix overlay is not optional | E.4's conftest was already correct; the stale thing was the file's own header — run as written, compose refuses the project | `conftest.py:90` layers the overlay between base and smoke; `conftest.py:32` supplies `PHOENIX_API_KEY` | none — comment | no | 1 | F3 | **OPEN** |
| E29 | copilot-mro | `CATALOGUE.md:28-44` | One conventions block defines the single grammar; the orphaned `DARK-L` tag and the stale "fn-frontend three-panel layout" paragraph are retired | The merged catalogue carried THREE vocabularies plus an orphan whose defining bullet the merge had deleted | E.7/E.0g; a §5 row was added for the grafted Slowest Pages panel | `test_catalogue_and_dashboards_agree` (`:263`) covers **board uids only**; the prose is unguarded | no | 1 | F2 | **OPEN** |
| E30 | copilot-mro | `CATALOGUE.md` — §7/§8 and the alarm table, 14 selectors normalised to brace form | CloudWatch selectors become brace selectors over the ORIGINAL dotted names | CloudWatch keeps the dotted name and appends nothing, so not one of the fourteen mixed-dialect spellings resolved | E.7; their convention had been grafted into §1/§3 only | none | no | 2 | F1 | **OPEN** |
| E31 | copilot-mro | `CATALOGUE.md:151` | `gen_ai.client.operation.duration` added to the signals list; emitted and charted by nothing | Inventoried as `wired`, no panel authored | Deferred to Phase G "if the owner wants one" | `test_emitted_series_inventory.py` proves the instrument; nothing requires a panel | no | 1 | F3 | **OPEN** |
| E32 | copilot-mro | `docs/runbooks/observability/alerts.md:171,184,197,210`; `aws-profile.md:13`; `oss-profile.md:28,52,192-198` | On-call surface converted to the three-state grammar; `POSTGRES_READONLY_PASSWORD` rotation row restored; the "EXPECTEDLY unhealthy in the standalone observe stack" sentence restored | E.0c (silent merge losses) plus the review finding that E.8 missed `alerts.md` — the retired vocabularies survived at the on-call surface | Without the unhealthy-datasource sentence the first person to run the smoke files a bug that is not one | none — runbook prose is not linted | no | 1 | F2 | **OPEN** |
| E33 | copilot-mro | `tests/unit/observability/test_phase1c_nonagent_scope_guard.py:60-67` | Left in place, still RED; deletion refused by the auto-mode classifier as "Security Test Removal" | Branch-diff change-control guard pinned to four SHAs and disarmed by a branch-name check; ours is `obs-merge`, so it is ARMED over our whole merged tree | Names four paths that do not exist (`docker-compose.phoenix-smoke.yml`, `oss-phoenix.env.example`, `*-production.env.example`, `production-queue-*.yaml`); real files are `durability-production-*.yaml` | itself — it is the 2 failed in the 237/2 unit lane | n/a | 1 | F3 | **OPEN (owner-owed)** |

---

## iac — `obs-merge`, `f35ec20..3068b47`

The scope argument: §4b-corrections pulled `llm-agents.json.tftpl` into M-SCOPE as "a repo file, not
an AWS apply". `3068b47` records that the same argument covers `alarms.tf` and the sibling template
identically, and that drawing the line between them left this repo holding exactly the two defects
the previous commit had removed from one file. **`3068b47`'s own commit message states: "No test in
any repo reaches this one, so all of it was unguarded in both directions."**

| # | Repo | File:line | Decision taken | Why | Evidence it is right | Guard test | Mutation-proved? | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|
| I1 | iac | `alarms.tf:160-191` | Four agent alarm selectors normalised: `{"agent.turn.calls_total"}` → `{"agent.turn.calls"}`, and the same for `agent.model.unpriced_calls`, `agent.model.cost_usd`, `agent.ledger.write_failures` | CloudWatch keeps the dotted OTLP name and appends nothing, so a glued-on Prometheus family suffix resolves to nothing — none of the four alarms could ever have fired | The convention the sibling template and `CATALOGUE.md:28-44` now both state | none. `scripts/validate_alarms.py` checks thresholds, comparison operators and query structure (`_query_failures`, `:510`) — never the metric spelling | no | 2 | F1 | **OPEN** |
| I2 | iac | `alarms.tf:161,172,186` | Three descriptions `DARK until Stream L (… has no emitter yet)` → `WIRED 2026-09-20, retrieval unproved (…)`, each naming the recorder and the call site | The emitters landed with the 2026-09-20 merge; the alarms were asserting the opposite at the on-call surface | copilot-mro's inventory states `wired` for all three, proved by AST (E2/E6) | none | no | 2 | F1 | **OPEN** |
| I3 | iac | `alarms.tf:179` | `LedgerWriteFailures` stays DARK, reworded to "cannot fire for any reason — it is inert, not quiet" | The distinction an operator reading a silent alarm needs | No instrument for `agent.ledger.write_failures` exists anywhere in the estate (`_emitted_series.py:127-132`, `instrument_attr=None`) | none | no | 1 | F3 | **OPEN** |
| I4 | iac | `alarms.tf:193,205` | Two satellite alarms normalised: `telegram.turns_total` → `{"telegram.turns"}`, `optimizer.runs_total` → `{"optimizer.runs"}` | Same dialect defect on signals owned by other services | Same CloudWatch convention | none — and these series are outside copilot-mro's inventory entirely (see the FAMILY_TOKEN scope limit, "Recorded, not fixed" #1) | no | 2 | F1 | **OPEN** |
| I5 | iac | `dashboards/llm-agents.json.tftpl:7` | Header rewritten: brace selectors with no Prometheus suffix; token usage marked a HISTOGRAM; subagents and CLI DARK with the reason; exact spend is "no CloudWatch counterpart" pointing at the oss `fn-llm-agents` panels | It opened with the retired "ALL metric queries below are DARK until Stream L" and every selector mixed dialects | Matches the copilot-mro inventory row for row | none | no | 2 | F1 | **OPEN** |
| I6 | iac | `dashboards/agent-turn-explorer.json.tftpl:7,15,17` | "WHOLE VIEW DARK until Stream L" → WIRED, retrieval unproved; the failed-turn filter becomes `agent.outcome = "error"`, not error status; the Logs Insights widget loses its DARK annotation | Flatly contradicted by the span inventory landed in the same merge; and an error-status filter finds nothing because the runtime sets no intrinsic status for a handled failed turn | `SPAN_SIGNALS`' `agent.outcome` note (`_emitted_series.py:175-180`) carries the same fact, AST-backed | none | no | 2 | F1 | **OPEN** |

---

## Mutation evidence, cited

Recorded as **twelve** pre-review mutations plus the review-response batch. Precision varies, and
the table above grades each row on that. Precisely cited (mutation **and** the thing that failed):

1. `compaction.directory` pointed at the read-only config mount → `otelcol validate` answers `ok oss`;
   the container start fails `failed to build extensions: failed to create extension
   "file_storage/production_queue": mkdir …: read-only file system`. **The P0-COLLECTOR signature.**
   (E22)
2. The tmpfs dropped from `validate.sh`'s **shipped** start pass → `failed to build extensions …
   mkdir /tmp: permission denied`. (E23)
3. `s -> _seconds` corrupted to `_secs` in `_UNIT_SUFFIX` → the measured smoke
   `test_prometheus_serves_the_exact_names_the_inventory_computes` names all nine dead series. (E4)
4. Three separate limb mutations against `test_flynapse_postgres_datasource_is_declared_kept_and_used`:
   delete the datasource entry; re-add `deleteDatasources`; delete exact-spend panels 11+12. (E13/E14/E15)

Recorded as a mutation but with **no failing test named** — graded `partially recorded`:
Counter/Histogram flip in one construction path; the same flip in both; an instrument nobody
inventoried; `record_subagent` wired so a dark series reads live; a WIRED panel described as DARK; a
DARK rule described as WIRED; the `_total` regression put back; a panel on an uninventoried series;
the `KNOWN_LABELS` / label-value / mixed-state batch (ledger: "All fixed, all mutation-proved"); the
repointed-panel mutation that exposed the inert prose-vouch check.

A **bad** mutation, recorded as such: flipping `create_directory` to `false` does **not** prove the
gap — collector 0.160.0 checks directory existence at config-validation time, so `validate` catches
it unaided. The read-only-mount mutation is the one that separates the two checks.

Two mutations that proved an **absence of guard** rather than a guard: deleting
`span.set_attribute("agent.outcome", outcome)` left every lane green (E3), and
`# TODO: re-enable telemetry.record_turn` satisfied the substring reachability limb (E7). Both
defects were fixed; **no post-fix mutation is recorded for either**, which is why E3 and E7 are
ASSERTED, not SETTLED.

---

## Open claims, tier 2 first

**Tier 2, OPEN — no guard, judgment only:**

- **E30 — the CATALOGUE's 14 CloudWatch brace selectors.** Nothing lints `CATALOGUE.md`'s metric
  spellings; `test_catalogue_and_dashboards_agree` checks board uids only.
- **I1 — the four agent alarm selectors in `alarms.tf`.** No test in any repo reaches this file's
  metric names; the iac validator checks thresholds and query structure only.
- **I2 — the three `WIRED 2026-09-20` alarm descriptions.** Unguarded in both directions: nothing
  fails if they go back to saying DARK, and nothing fails if a genuinely dark alarm claims WIRED.
- **I4 — `telegram.turns` / `optimizer.runs` selector normalisation.** Unguarded, and these families
  are outside copilot-mro's inventory scope by design (see "Recorded, not fixed" #1).
- **I5 — the `llm-agents.json.tftpl` header.** Unguarded prose.
- **I6 — the `agent-turn-explorer.json.tftpl` header and the `agent.outcome` failed-turn filter.**
  Unguarded prose; the same fact IS AST-backed on the copilot-mro side, so the two can drift.

**Tier 2, ASSERTED (guard exists, no post-fix mutation recorded):**

- **E3 — `SPAN_SIGNALS` backing.** The span half of the inventory is now AST-proved, but the only
  recorded mutation is the pre-fix one that showed the gap.

**Tier 1, OPEN:**

- **E26** — README production-bind-mount / outage-budget / tmpfs prose: unguarded.
- **E28** — the smoke compose header comment: unguarded.
- **E29** — the CATALOGUE conventions block, the retired `DARK-L`, the stale three-panel paragraph:
  unguarded prose.
- **E31** — `gen_ai.client.operation.duration` emitted and charted by nothing; deferred to Phase G.
- **E32** — the three runbooks: unguarded prose, and the review found E.8 had missed `alerts.md`
  entirely, which is what an unguarded surface looks like.
- **E33** — `test_phase1c_nonagent_scope_guard.py`: still RED, owner-owed, deletion refused.
- **I3** — the `LedgerWriteFailures` "inert, not quiet" rewording: unguarded.

---

## Recorded, not fixed

Two Phase E review findings were CONFIRMED, recorded, and deliberately not fixed. Both are OPEN
claims.

**1. The lint's scope is three metric prefixes.** `FAMILY_TOKEN` (`_emitted_series.py:213-216`)
matches `agent_`, `gen_ai_` and `claude_code_` only, so repointing a panel at a name outside them —
the reviewer used `llm_model_calls_total`, a real table in this product — is **not** caught as an
unknown series. *Partially mitigated:* the prose check (E12) now fails a panel whose description
names an inventory series while its query reads none. *Recorded reason for deferral:* the complete
solution is an inventory of every metric family the boards may name (`otelcol_*`, `loki_*`,
`tempo_*`, `prometheus_*`, `traces_spanmetrics_*`, `telegram_*`, `optimizer_*`, `http_*`), most of
them third-party self-telemetry whose names this repo does not own and cannot derive. That is a
different contract — pin third-party spellings against a live scrape — and belongs with the
B1a/B1b re-verification work. **Tier 2, chunk F1, OPEN.** Note the interaction with I4: the two
satellite alarm series this phase renamed in `alarms.tf` sit in exactly that uncovered space.

**2. `validate.sh` leaks a temp directory on the success path.** Once the durability fragment is
layered the collector writes queue files as uid 10001 into 0700 subdirectories the runner cannot
unlink, so `/tmp/tmp.*/queue` accumulates. Cleanup is best-effort by design (`cleanup_work`,
`validate.sh:63`) and prints a note. *Recorded reason for deferral:* removing it properly needs a
second image with a shell, a dependency the pinned-image script deliberately does not have.
**Tier 1, chunk F3, OPEN.**

**A third bullet, recorded as PLAUSIBLE and not reproduced** (the plan does not count it among the
two): `up_down_counter` instruments are invisible to the AST scan — `flynapse-otel`'s `registry.py`
exports one and `_declarations()` (`test_emitted_series_inventory.py:40-77`) matches
counter/histogram only. The failure mode is loud (a panel on such a series reports as unknown), so
it is a gap, not a hole. And `docker port` is queried once in `start_check` (`validate.sh:89`); an
empty answer at that instant burns the deadline and reports `state: timeout`, which reads as a
config failure. A flake, never a false pass. **Tier 1, chunk F3, OPEN.**

---

## Re-statement 2026-09-22

Appended by the R2 packet re-stater (Opus), read-only against every tree, nothing committed. Every
row above is left as filed; this section says what is true TODAY. **HEADs read:** copilot-mro-obsm
`735f8213` (obs-merge, clean) · iac `74346bb` (obs-merge; the 7 "dirty" paths are `__pycache__` plus
the pre-existing untracked `poc_ec2_setup_ubuntu.sh`) · utils-obsm `179cc6d` · core-obsm `b4d2c33` ·
dashboard-obsm `4a7714a` · copilot-mro-obsm-cli `f1100629` (branch `obs-merge-cli`, NOT merged) ·
copilot-mro-obsm-r7b `afe79dbb` (branch `obs-merge-r7b`, NOT merged). **Column note:** this file's
`Tier` column is §2.3a's tier and it carries no reviewer-severity column; nothing below rewrites it.
"Implementer" in an evidence cell means the proof is the committing lane's own; only an independent
reviewer's red earns a settled reading.

**What moved the ground under this file since 2026-09-20:** G.6 wired `agent.subagent.*` and
`agent.ledger.write_failures` (`3978073b`, inventory `60f40a9f`); M-LEGACY-PANELS added 17 legacy
families and widened `FAMILY_TOKEN` (`9900a933`, `145cb929`); M-GRAFANA's datasource VALUES were
restored in all three compose stacks (G.78, `0d9ecf0b`, r7b R7B-33 SETTLED); the phase-1c guard was
repointed (`60f40a9f`); iac's `alarms.tf` was rewritten five times (`2d493c8` → `9fda3db` → `234603b`
→ `5e476e0` → `607cee0`/`f85284e`, then `97cae73`, `d52e8b8`, iac r3 `d86b378..74346bb`) and gained
`scripts/validate_metric_vocabulary.py`, which now runs in `terraform-plan.yaml` CI; M-CLI-TELEMETRY
(G.4) retires `claude_code.*` — on `obs-merge-cli` only (copilot-mro half) and at iac `5f3380c`;
M-GENAI-TENANT (`93d2a581`) stripped `tenant.id` from the two `gen_ai` histograms.

| row # | claim state at filing | state now | evidence | source |
|---|---|---|---|---|
| E1 | SETTLED | UNCHANGED (checked) | `STATE_NOTES` still the three regexes (`_emitted_series.py:268-272`); `test_dark_panel_notes_are_present` / `test_pending_rule_notes_are_present_only_for_unemitted_series` still resolve; the only later edits to the module are G.6 (`60f40a9f`) and the legacy series (`9900a933`, `145cb929`, `d091a372`), none touching the grammar | `git log ea0ac559..HEAD -- tests/integration/otel/_emitted_series.py` |
| E2 | SETTLED | UNCHANGED in mechanism; the inventory GREW: `SERIES` is still 14 entries but `agent.subagent.*` and `agent.ledger.write_failures` are now `wired` (were `dark`), and `LEGACY_SERIES` (17 entries) + `ALL_SERIES` were added | `_emitted_series.py:66-210`; `60f40a9f` message ("`_emitted_series.py` records what G.6 wired"); `9900a933` | tree; plan G.6 |
| E3 | ASSERTED | UNCHANGED (checked): `test_every_span_signal_is_backed_by_a_span_the_code_really_opens` (`test_emitted_series_inventory.py:318`) is unmodified since filing; no later round recorded a post-fix mutation on the span limb | `git diff ea0ac559..HEAD -- test_emitted_series_inventory.py` touches only the `ALL_SERIES`/`KNOWN_RELATIONS` imports | tree |
| E4 | SETTLED | UNCHANGED (checked); the measured smoke is still `OTEL_COMPOSE_SMOKE=1`-gated and no later round ran it | `_UNIT_SUFFIX` unchanged at `:297`; `test_oss_profile_smoke.py` not in any later commit | tree |
| E5 | SETTLED | UNCHANGED (checked); `145cb929` ADDED a stricter limb: a legacy name without its unit suffix is now a lint failure | `145cb929` "the series lint no longer accepts a legacy name without its unit suffix" (implementer) | tree |
| E6 | SETTLED | SUPERSEDED in substance — the property still holds but its witness moved: `record_subagent` NOW has a production call site (`agent_pipeline.py` binds it on both runtimes, `3978073b`), so the "declared, recorded in the facade, called by nothing" example that made this limb load-bearing no longer exists. The limb itself (`test_a_recorder_has_a_production_call_site_exactly_when_the_series_is_not_dark`, `:290`) is REFUTED as a reachability proof by r7b R7B-19 (see E7) | plan G.6 audit; `claims-copilot-mro-r7b.md` R7B-19 | tree; r7b |
| E7 | ASSERTED | REFUTED-BY `claims-copilot-mro-r7b.md` R7B-19 (independent): `_call_sites` counts ANY `ast.Attribute` named like the recorder — a bound reference (`observer=obj.method`) satisfies it — so mutant G6M9 (both runtimes' bindings removed) stayed green. The fix (`_call_sites` counts `obj.method(...)` CALLS only; callback-wired recorders declared `CALLBACK_WIRED` and driven behaviourally) is r7b `3ec66117` on `obs-merge-r7b`, **NOT merged**; obs-merge HEAD still carries the refuted body (`test_emitted_series_inventory.py:126-147`, verified) | r7b P2-2; plan G.6 IMPLEMENTATION NOTE | r7b; tree |
| E8 | SETTLED | UNCHANGED (checked): `test_tool_outcome_filters_use_the_dispatchers_own_literals` resolves at `:400` and is untouched | tree | tree |
| E9 | SETTLED | UNCHANGED in kind; the hatch WIDENED: `KNOWN_RELATIONS` (`llm_usage`, `llm_model_calls`) joined `KNOWN_LABELS` under the same shadow rule (`test_known_labels_cannot_shadow_a_series` now iterates `KNOWN_LABELS \| KNOWN_RELATIONS` over `ALL_SERIES`) | `git diff ea0ac559..HEAD -- test_emitted_series_inventory.py`; `_emitted_series.py:253-264` | tree |
| E10 | ASSERTED | UNCHANGED (checked): one body, both lints import it | `test_grafana_dashboards.py`, `test_alert_rules_layout.py` imports unchanged | tree |
| E11 | SETTLED | UNCHANGED (checked) | `signal_state_offenders` `:391-` | tree |
| E12 | SETTLED | UNCHANGED (checked) | same | tree |
| E13 | SETTLED | UNCHANGED at `datasources.yml` (no commit since filing) — and STRENGTHENED beside it: G.78 found the three compose stacks had lost the `POSTGRES_DATASOURCE_{HOST,DB}` / `POSTGRES_READONLY_PASSWORD` values the file interpolates (so the kept datasource provisioned EMPTY); restored in all three stacks + `.env.sample` at `0d9ecf0b`, reviewed r7b R7B-33 SETTLED (G78M1/M2 red, independent) | plan G.78; `claims-copilot-mro-r7b.md` R7B-33 | tree; r7b |
| E14 | SETTLED | UNCHANGED (checked) | `deleteDatasources` absent | tree |
| E15 | SETTLED | UNCHANGED as a guard; the PANEL NOTES changed: the exact-spend panels' state moved `LIVE (Phase 5 grants)` → `WIRED …, retrieval unproved` at `9f44382e` (a grant read is not a probe) | `9f44382e`; `claims-phase6-fixpass.md` row "Four Postgres panels" | tree |
| E16 | SETTLED | UNCHANGED (checked); still a histogram, still `_sum` | `_emitted_series.py:93-98`; `llm-agents.json` | tree |
| E17 | ASSERTED | UNCHANGED at the panel (WIRED); the emitter half was COULD-NOT-BREAK by the fix-pass reviewer (boot → `emitAppBoot()` unconditional, allow-list passes both keys) and iac `5e476e0` records "the drop counter's onDropped was always wired — P9 simply dropped no batch" for the sibling. No probe window has confirmed the Loki record, so WIRED is still the right state | `claims-phase6-fixpass.md` row `CATALOGUE.md:377` / panel 19 | fixpass |
| E18 | SETTLED | UNCHANGED grammar; the rule FILE changed three times since: `3978073b` (LedgerWriteFailures DARK → WIRED, since the instrument now exists), `9f44382e` (UnpricedModelCalls lookback 30m → 1h), `57f486c6` + `7130d4d0` (first-event `unless … offset` branch on both any-occurrence rules, then gated against scrape gaps after r7 P3-1). r7b R7B-23: the "fires after the first call" claim at `9f44382e` was REFUTED at that SHA and is fixed at HEAD | `git log -- flynapse-agent-alerts.yml`; r7b R7B-23; copilot-mro-rounds FX-08 | tree; r7b |
| E19 | SETTLED | UNCHANGED (checked) | the tuples are still absent | tree |
| E20 | SETTLED | UNCHANGED (checked): `agent-turn-explorer.json` has no commit since filing | tree | tree |
| E21 | SETTLED | SUPERSEDED in fact: "Ledger write failures = DARK until Task R" is no longer true — G.6 created the instrument and wired it (`3978073b`; inventory entry now `wired`, `instrument_attr="_ledger_write_failures"`), so `platform-health.json:72`'s note flipped to WIRED in the same commit and `test_entries_without_an_instrument_really_have_none` now has no agent entry to exercise (only `claude_code.*`). The board-description half (which panels left Grafana) still stands | `_emitted_series.py:130-137`; `3978073b`; iac `5e476e0` (the same flip on the aws side) | tree |
| E22 | SETTLED | UNCHANGED (checked): `deployment/otel/validate.sh` has NO commit since `ea0ac559`. A NEW obligation sits beside it: M-CLI-TELEMETRY's four collector overlays carry OTTL proved only in Python, and G.4 records "validate.sh / the CI otelcol-validate job must load the four overlays in the real otelcol 0.160.0 before merge" as OWED (cli branch, not merged) | plan G.4 "OWED (2)" | tree; plan |
| E23 | SETTLED | UNCHANGED (checked) | same file | tree |
| E24 | SETTLED | UNCHANGED (checked) | same file | tree |
| E25 | ASSERTED | UNCHANGED (checked). Context moved: M-PHOENIX-ON flipped `LLM_CONTENT_COPY_SAMPLE_RATE` to 1.0 (`2b6170b0`), which changes what the aws+phoenix composition would CARRY, not whether it builds | `deployment/otel/README.md:41-43` | tree |
| E26 | OPEN | STILL OPEN (prose, unguarded). Re-read at HEAD: the storage-extension / bind-mount / `max_elapsed_time: 5m` / `otelcol-storage`-forbidden paragraphs are intact (`README.md:147-168`); `PHOENIX_*` scope row intact (`:115-116`). `95ca0e29` and `2b6170b0` added text and contradicted none of it | tree | tree |
| E27 | ASSERTED | UNCHANGED (checked): neither tuple file has a commit since filing | tree | tree |
| E28 | OPEN | STILL OPEN (comment); unchanged text at `docker-compose.smoke.yml:1-13` | tree | tree |
| E29 | OPEN | STILL OPEN as prose, and still TRUE at HEAD: one conventions block (`CATALOGUE.md:28-44`), zero `DARK-L` occurrences, the three-panel paragraph retired (`:13` now calls it "a branch proposal"). Still guarded only at board-uid grain | tree | tree |
| E30 | OPEN | STILL OPEN — and the 14 selectors have DRIFTED from iac in the histogram forms: iac `9fda3db` settled the CloudWatch histogram shape as NATIVE (counts via `histogram_count()`, no `le` grouping), but `CATALOGUE.md:122, :559, :561, :609, :646` still spell `histogram_quantile(…, sum by (le…) (rate({"…duration"}[…])))` and `:645` still describes the 5xx ratio without `histogram_count()`. The counter/gauge selectors (`{"agent.turn.calls"}`, `{"telegram.turns"}`, `{"optimizer.runs"}`) agree with `alarms.tf`. See Cross-file staleness | `CATALOGUE.md` at HEAD vs iac `alarms.tf:296-322`; iac `9fda3db` message | tree |
| E31 | OPEN | STILL OPEN: `gen_ai.client.operation.duration` is inventoried `wired` with the note "Emitted, charted by no panel yet" (`_emitted_series.py:99-103`); zero occurrences in `llm-agents.json`, one prose mention in the catalogue. M-GENAI-TENANT (`93d2a581`) stripped `tenant.id` from it; no panel was authored | tree; §4a-bis M-GENAI-TENANT | tree |
| E32 | OPEN | STILL OPEN as a class (runbook prose unlinted), but the surface was re-edited: `9f44382e` (fix-pass findings), `3978073b`/`57f486c6`/`7130d4d0` (`alerts.md` alert rows), `9900a933` (legacy runbook lines), `95ca0e29` (`aws-profile.md` dead keys). Two prose guards now exist on parts of it: `test_runbook_panel_quotes_match_the_real_panel_titles` (`4bfa4967`) and `test_observability_prose_names_live_keys` (`95ca0e29`) | `git log -- docs/runbooks/observability/` | tree |
| E33 | OPEN (owner-owed) | FIXED-AT `60f40a9f` (implementer, mutation-proved two ways) — the guard was REPOINTED, not deleted: the `"obs-telemetry-merge"` branch-name disarm is gone, the track-merge boundary is derived from the graph, the stale four-path list was replaced by the post-merge approved surface, and the utils checkout resolves by directory suffix. It is now the "post-merge scope guard" that ~30 later commits extend by named path. Independent measure: r7b lane B ran it green at every SHA (403 → 441 passed, 0 failed) — a green measurement, not a mutation. No longer owner-owed | `60f40a9f` message; `claims-copilot-mro-r7b.md` lane B table; `git log -- test_phase1c_nonagent_scope_guard.py` (31 commits) | tree; r7b |
| I1 | OPEN | FIXED-AT iac `2d493c8` → `9fda3db` (implementer) and NOW GUARDED: `scripts/validate_metric_vocabulary.py` checks 1–7 read every selector on the aws surface (dotted brace form, no Prometheus suffix, unit suffixes, `FAMILY_SUFFIXED_INSTRUMENTS` for the born-`_total` legacy names) and runs in `terraform-plan.yaml` CI (`9fda3db`; `pull_request` trigger added `234603b`). Independent: the Phase-6 iac fix-pass reviewer ran 7 mutations against the `2d493c8` guard (`claims-phase6-iac-fixpass.md`), the `9fda3db` reviewer re-fetched the AWS pages (ledger CHECKPOINT 11b), and iac r3 ran 35 mutants (18 red) on `013dc89..d52e8b8`. The four agent selectors read `{"agent.turn.calls"}`, `{"agent.model.unpriced_calls"}`, `{"agent.ledger.write_failures"}`, `{"agent.model.cost_usd"}` at `alarms.tf:395-427` | iac tree; `claims-phase6-iac-fixpass.md`; `claims-iac-r3.md`; ledger CP 10b/11b | tree; packet |
| I2 | OPEN | FIXED-AT iac `5e476e0` (implementer; an adversarial review of that change found and fixed three guard defects, ledger CP 15b): check 6 (`check_state_notes` / `check_state_vocabulary`) holds every state note on the aws surface to the CATALOGUE's three-state grammar, dated, naming a code artefact for WIRED and a PROBES-register entry for LIVE. What it cannot do is stated in code and pinned: a well-formed "DARK until …" on an emitting series still passes (truth needs the deferred cross-repo inventory). The three descriptions read `WIRED 2026-09-20, retrieval unproved: …` at `alarms.tf:392/403/418` | `5e476e0` message; ledger CP 15b | tree |
| I3 | OPEN | SUPERSEDED-BY G.6: the wording "cannot fire for any reason — it is inert, not quiet" was DELETED at `5e476e0` because its premise (no instrument anywhere) stopped being true when `3978073b` created `agent.ledger.write_failures`; `LedgerWriteFailures` is now `WIRED 2026-09-20, retrieval unproved` (`alarms.tf:416-420`) and the "GREEN HERE MEANS NOTHING" paragraph was removed rather than reworded. `9fda3db` had meanwhile recorded the two-state PromQL alarm model (no INSUFFICIENT_DATA — a missing series sits GREEN), which is why that paragraph mattered while it lasted | `5e476e0`, `9fda3db` messages; `alarms.tf:408-420` | tree |
| I4 | OPEN | FIXED-AT `2d493c8` (selectors) and guarded by the same validator as I1 (`{"telegram.turns"}` `alarms.tf:446-448`, `{"optimizer.runs"}` `:458-460`). The "outside copilot-mro's inventory" limit stands: iac's validator pins these names by an EXPECTED_SERIES set, not by an emitter read; the iac fix-pass reviewer verified every converted name against its real emitter by hand (`claims-phase6-iac-fixpass.md` "could not break" #2). `9fda3db` marked `TelegramTurnFailureRate` GREEN-on-nothing in this root (no telegram-bot compute) and deliberately did not gate it | iac tree; iac fix-pass file | tree |
| I5 | OPEN | SUPERSEDED — the header was rewritten again at `5e476e0` (subagents: WIRED, `record_subagent` is bound on both runtimes), `5f3380c` (the `claude_code.*` bullet retired under M-CLI-TELEMETRY), `d52e8b8` (six legacy panels appended), iac r3 `d86b378` (the CLI bullet now `DARK until copilot-mro obs-merge-cli merges …`, pinned to the validator's state grammar — flip to WIRED after the cli merge) and `74346bb`. Check 6 now lints its state notes; the prose remains otherwise unguarded | `git log -- dashboards/llm-agents.json.tftpl`; `claims-iac-r3.md` | tree |
| I6 | OPEN | SUPERSEDED: `2d493c8` turned BOTH widgets into `type: "text"` (the Logs Insights `invoke_agent` widget could not return data — `invoke_agent` is a span name/attribute value, never a log body), so there is no failed-turn FILTER on the aws board any more; the `agent.outcome = "error"` fact survives as prose. The iac fix-pass reviewer verified the "dead widget" claim and filed the $3/month text-only dashboard as P2-L (still open). Check 6 lints the WIRED/DARK words; the `agent.outcome` fact is AST-backed only on the copilot-mro side, so the two can still drift | `claims-phase6-iac-fixpass.md` P2-L + table row; `dashboards/agent-turn-explorer.json.tftpl` (2 text widgets at HEAD) | tree; packet |
| Recorded-not-fixed #1 (FAMILY_TOKEN scope) | OPEN | PARTLY NARROWED, STILL OPEN: `FAMILY_TOKEN` now also matches the legacy prefixes `llm_`/`embedding_`/`chat_block_`/`document_hub_`/`memory_` (`_emitted_series.py:286-292`), so a legacy name not in `LEGACY_SERIES` fails; `otelcol_*`, `loki_*`, `tempo_*`, `prometheus_*`, `traces_spanmetrics_*`, `telegram_*`, `optimizer_*`, `http_*` remain outside the lint exactly as recorded. The iac side now has its own vocabulary guard (I1), which covers the two satellite families THERE | tree | tree |
| Recorded-not-fixed #2 (`validate.sh` temp leak) | OPEN | UNCHANGED (checked): file untouched | tree | tree |
| Recorded-not-fixed #3 (`up_down_counter` blind; `docker port` flake) | OPEN | UNCHANGED (checked): `_declarations()` still matches counter/histogram only; no later round touched it | tree | tree |

### Open claims now, tier 2 first

- **E30** — CATALOGUE's CloudWatch dialect selectors: still unguarded, and now DRIFTED from iac on the
  histogram forms (`le` grouping, no `histogram_count()`), while iac's validator cannot reach this
  file. Needs one pass over `CATALOGUE.md:122, :559, :561, :609, :645-646` (and the `sum by (le`
  forms at `:114`, `:291`, `:301`, `:340`, `:543`, `:599` are oss-dialect and correct).
- **E7 / E6 (tier 2 by E6's tier)** — the reachability limb is REFUTED (r7b R7B-19) and its fix sits
  on the unmerged `obs-merge-r7b` (`3ec66117`). Until that merge lands, every WIRED claim the
  inventory makes rests on an attribute-name match that a bound reference satisfies.
- **E3** — span-limb post-fix mutation still unrecorded (ASSERTED).
- **I6's residue (P2-L)** — a billable text-only dashboard; open in `claims-phase6-iac-fixpass.md`.
- **I4's scope limit** — the satellite families are pinned by an EXPECTED_SERIES set in iac, hand-verified
  against emitters, never derived; the published-inventory fix is in §6 ("Deferred from Phase G").
- **Tier 1, still open:** E26, E28, E29, E31 (no panel; owner never asked for one), E32 (class), the
  three "Recorded, not fixed" bullets, and E22's NEW owed item (real-otelcol validation of the four
  CLI overlays, cli branch).

**Closed since filing:** E33 (repointed, `60f40a9f`), I1, I2, I4 (guarded by iac's validator + CI),
I3 and I5/I6 (superseded by G.6 / the text-widget rewrite / iac r3).

### Cross-file staleness (rows in OTHER files that contradict this file's rows now; listed, not fixed)

1. `claims-phase6-dashboards.md` row 5 says `tool_outcome="failure"` is "value unguarded" — E8 named
   `test_tool_outcome_filters_use_the_dispatchers_own_literals` on 2026-09-20 and it resolves at
   `test_emitted_series_inventory.py:400` today. The two files disagreed AT FILING.
2. `claims-phase6-dashboards.md` row 8 lists five DARK inventory entries; three of them
   (`agent.ledger.write_failures`, `agent.subagent.calls`, `agent.subagent.duration_seconds`) are
   `wired` at HEAD (`3978073b`/`60f40a9f`), and the remaining two (`claude_code.*`) are deleted on
   `obs-merge-cli` (G.4), not yet merged.
3. `claims-phase6-dashboards.md` row 21 ("`LedgerWriteFailures` ships enabled on a series that cannot
   fire") and row 34 ("all 18 alarms agree with their oss rule on value, window…") — the series now
   emits, and the oss `UnpricedModelCalls` window is `[1h]` (`9f44382e`) while iac `alarms.tf:405`
   still reads `[30m]` and `validate_alarms.py:65` pins 1800 s; the oss first-event `unless … offset`
   branch (`57f486c6`) has no aws twin. Nothing in either repo compares the two.
4. `claims-phase6-iac-fixpass.md` cross-repo rows (`CATALOGUE.md:187` `ThrottledCount`,
   `aws-profile.md:11,13` `duration_count`/`ThrottledCount`) are FIXED at copilot-mro `95ca0e29`
   (`InvocationThrottles`, `histogram_count()`); the `aws-profile.md:56,183` + `CATALOGUE.md:588` "suffix
   is open (B1a)" rows are now CONSISTENT with iac again, because `9fda3db` restored the RE-VERIFY on
   `CollectorTelemetryAbsent`.
5. `claims-G10-weaviate-spans.md` G10-13 / `claims-utils-rounds.md` G10R-07: `dependencies.json:18`
   and `CATALOGUE.md:138` still say the `db_system` values are `postgresql, redis` — confirmed at
   HEAD; queued as a copilot-mro follow-up (ledger CHECKPOINT 35), not fixed by anything above.

### Could not trace

- Whether the `9fda3db` independent reviewer's claims table was ever filed as a packet file: the ledger
  (CHECKPOINT 10c/11b) records the review and its triage in prose; no `claims-iac-r1/r2` file exists.
  Packet N6 (satellites, lane #14) is the intended home.
- The copilot-mro half of G.4 (`_emitted_series` dropping `claude_code.*`, panel 10 removed) is read
  from the plan and the cli branch's messages; the merge into obs-merge (lane #5) had not landed at the
  HEADs above, so rows E2/E21's DARK census may change again within the day.
