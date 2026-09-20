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
