# Observability close-out gate — status, measured

Run 2026-09-20, unattended. **Read-only**: no tree was edited, no branch moved, no commit or stash was
made. The only write is this file. Everything below is a command that was run and its output, or a file
that was read; nothing is asserted from a previous document.

Subject: the six `obs-merge` worktrees **as working trees** (uncommitted production edits included —
that is the project's convention and the guards below judge the working tree, not HEAD).

| tree | branch | head at run time | dirty files |
|---|---|---|---|
| `copilot-mro-obsm` | `obs-merge` | `c80c686d` | 25 |
| `api-obsm` | `obs-merge` | `cc56667` | 7 |
| `core-obsm` | `obs-merge` | `bbc67ed` | 10 |
| `utils-obsm` | `obs-merge` | `1cdebad` | 2 |
| `dashboard-obsm` | `obs-merge` | `fdf7487` | 3 |
| `iac` | `obs-merge` | `5e476e0` | 7 |
| `docs` | `main` | `d33998f` | 12 |

Pre-merge controls used to tell a merge defect from a pre-existing one: `copilot-mro@417df303`
(`langgraph-merge`), `core@e10a9ce` (`master`), `utils@289ba71`, `api@44bd8d1`.

**Three trees moved under this run.** `utils-obsm` gained `1cdebad` (G.24 + G.29 guards) after its first
lane; `core-obsm` and `api-obsm` each gained a dirty `run_errors.py`; `dashboard-obsm` went
`5011f4f` → `fdf7487` (G.22). Every affected lane was re-run at the later head and the later number is
the one reported.

---

## 1. The headline

**Of the fifteen open items, six are proven, four are unproven-and-unprovable-by-testing, and five are
partly proven with a named blocker.**

| | count | items |
|---|---|---|
| **Proven by a command run tonight** | **6** | C1, I1, I2, I5, I7, I8 |
| **Partly proven — one limb measured, one limb blocked** | **5** | C2, C4, C5, C7, I4 |
| **Not proven at all** | **4** | C3, C8, I3, I6 |

**The number the owner most needs: seven of the fifteen cannot be closed by any test run in this
workspace — C2, C3, C4, C5, C7, I3, I4 — and C8 is definitionally last, so the honest figure is eight
rows that no amount of testing will close.** They split by what each actually needs:

- **Three need only an owner decision, no external service at all** — C4's resource-budget *number*,
  I4/C6's approved tenant-scoped instrument *list* (G.17 / Task R.2), C2's third *role* ("restricted
  administrator" does not exist in the estate).
- **Three need a driven application or third-party credentials** — C5's aws/azure/newrelic canaries,
  C7's `wired` → `live` promotions, I3's canaries plus a collector-restart proof.
- **One needs a schema decision before any of that** — C3's runtime-parity axis.
- **I6 is different and it is not owner-blocked: it needs a code fix** (see §3, I6 — the pin that
  carries the invariant is reading the wrong checkout).

Four of the fifteen are **better** than the spec recorded, on evidence gathered tonight: C4, C5, C7 and
I3 all moved, because the spec was written before it was known that this host has a working Docker
daemon and that the estate's own compose smoke runs clean here. See §7.

**Estate-wide test result: 19,637 Python checks collected, 19,495 passed, 18 failed, 23 errors, 98
skipped, 3 xfailed; plus 2,533 dashboard checks, all passing.** Of the 18 failures, **17 reproduce
identically on the pre-merge sibling** — exactly one is attributable to the merged tree, and it is a
guard doing its job (§5).

---

## 2. How every number below was produced

```
cd /tmp && PYTHONPATH=/home/aditya/Code/core-obsm:/home/aditya/Code/utils-obsm:\
/home/aditya/Code/copilot-mro-obsm:/home/aditya/Code/api-obsm \
POSTGRES_DB=copilot_mro_test DEBUG=false ENV_FILE=/home/aditya/Code/api/.env \
/home/aditya/Code/api/.venv/bin/pytest -o addopts="-ra --strict-markers" \
-p no:cacheprovider <ABSOLUTE PATH TO ONE TEST DIRECTORY>
```

Deliberate choices, each defeating a named trap:

- **`cd /tmp`, absolute paths, and the venv's `pytest` console script directly** instead of
  `poetry -C api run pytest <relative path>`. Two reasons. The relative-path trap is real — every merged
  repo has a pre-merge sibling. And a second one the brief did not name: **`poetry -C /home/aditya/Code/api`
  puts `api/` on `sys.path[0]` for anything that adds cwd, and `flynapse_api` then resolves to the
  PRE-MERGE checkout.** Measured: from `cwd=/home/aditya/Code/api`, `flynapse_api.__file__` is
  `/home/aditya/Code/api/flynapse_api/__init__.py` even with `api-obsm` first on `PYTHONPATH`; from a
  neutral cwd it is `/home/aditya/Code/api-obsm/flynapse_api/__init__.py`. pytest's console script does
  not add cwd, so this is not a live defect for the sanctioned lane — but it is one line away from being
  one, and it is a sixth instance of the session's signature failure.
- **Module resolution asserted once before trusting any number**, from a neutral cwd:
  `core` → `core-obsm`, `utils` → `utils-obsm`, `copilot_mro.__path__` →
  `['…/copilot-mro-obsm/copilot_mro', '…/copilot-mro/copilot_mro']` (obsm first, **only** because of the
  `PYTHONPATH` pin), `flynapse_api` → `api-obsm`.
- **`-o addopts="-ra --strict-markers"`** on every invocation. `core-obsm` and `utils-obsm` bake `-q`;
  **`api-obsm` bakes `-v --tb=short`** — the override is needed in all three, not two.
- **`-p no:cacheprovider`** so no lane writes `.pytest_cache` into a tree under review.
- **`rootdir` is reported for every lane** and was correct on all 48 invocations.
- One invocation per test **directory**. Where a level-1 directory produced errors that a level-2
  directory did not, both numbers are given — that difference is itself a finding (§5.3).

---

## 3. The fifteen items, one row each

C6 is the already-ticked cardinality check; it is not one of the fifteen but its second limb feeds I4, so
it is carried at the end as an appendix row.

### C1 — two-tenant product-event replay · **PROVEN**

```
pytest core-obsm/tests/db/analytics core-obsm/tests/api/analytics core-obsm/tests/unit/analytics
rootdir: /home/aditya/Code/core-obsm   collected 269   →  269 passed, 0 failed, 0 skipped
```
Every named acceptance test exists and is inside that 269 — verified by name, not by count:
`test_replaying_an_event_is_a_duplicate_and_does_not_add_a_row` and
`test_an_unbound_insert_is_refused_not_silently_dropped` and
`test_the_same_event_id_is_independent_in_two_tenants`
(`tests/db/analytics/test_product_events_store_db.py`),
`test_a_retried_event_is_reported_as_duplicate_and_only_logged_once`
(`tests/api/analytics/test_events_endpoint.py`),
`test_schema_version_is_the_servers_claim_not_the_clients`
(`tests/unit/analytics/test_product_events_schema.py`). The lane has **zero skips**, so nothing in it is
green by not running.

The three files the 2026-09-17 note recorded as blocked were run on their own as well:
`test_product_events_store_db.py test_chat_turn_facts_backfill_db.py test_product_events_purge_db.py`
→ **12 collected, 12 passed**. **The scratch-DB blocker does not touch the close-out — confirmed, not
relayed.**

### C2 — two-tenant dashboard-profile matrix · **PARTLY PROVEN; the remainder is not a test**

- **Core half: proven** — inside the same 269. `test_dashboard_profiles_db.py`,
  `test_dashboard_profile_endpoint.py`, `test_dashboard_profiles.py` all green.
- **Dashboard half: now runnable, and green.** `cd dashboard-obsm && npm run test:unit` →
  **tests 2533, pass 2533, fail 0, skipped 0** (at `fdf7487` + 3 dirty production files, i.e. with G.22
  landed). The spec classed this "after B2"; B2 and G.22 have both landed.
- **Blocked, and not by a test:** the check names a third caller class, "restricted administrator".
  A case-insensitive sweep of every `.py`/`.ts`/`.tsx`/`.sql`/`.json` under `/home/aditya/Code`
  (excluding `node_modules`) returns **nothing**. The role does not exist.
- **A second blocker the spec did not carry:** the criterion says "one tenant cannot **read or alter**
  another's profile row". There is **no writer for `dashboard_profiles` anywhere in the estate** — the
  only reference in production code is a `SELECT` at
  `core-obsm/core/resources/analytics/dashboard_profiles.py:132`. The read half is proven; **the alter
  half has no code path to test and cannot be falsified.** (This is B2-R3, still open.)

### C3 — dual-runtime turn matrix and reconciliation · **NOT PROVEN — and it is a schema decision**

Verified from the tree, independently of the plan:

- **No Postgres relation in the estate carries a runtime.** `grep '"runtime'` and `grep 'agent_runtime'`
  across every module in `copilot_mro/app/db/postgres_table_definitions_modules/` return **zero column
  declarations**. `llm_model_calls` has 38 columns and none attributes a row to a runtime; `chat_turn_facts`
  — the per-turn analytics projection — has 20 columns and none either. The only `runtime` key anywhere
  near the ledger is inside the **content-capture** payload (`llm_turn_content`, `schema_version: 2`),
  which is a different relation and is **absent from `copilot_mro_test` altogether**.
- **The trace side carries it**, as `gen_ai.agent.name` on the turn span
  (`agent_shared/telemetry.py:1513`, `:1672`).
- **THE BRIEF IS WRONG THAT NO METRIC CARRIES IT.** `RuntimeTelemetry.record_turn`
  (`telemetry.py:1829-1840`) puts `"gen_ai.agent.name": runtime` into the attribute set of **both**
  `agent.turn.calls` and `agent.turn.duration_seconds`, and the collector's
  `attributes/metric_cardinality` processor (`deployment/otel/base.yaml:76-95`) deletes **nine** keys —
  `session.id`, `user.id`, `user.email`, `enduser.id`, `organization.id`, `terminal.type`,
  `app.entrypoint`, `url.path`, `http.target` — and `gen_ai.agent.name` is **not** among them. Runtime
  reaches Prometheus as a label on the turn metrics.
  The *model* metrics genuinely do not carry it: `_model_attributes` (`telemetry.py:1784-1798`) has
  provider, model, role, purpose, profile, cost_source, graph_node, error.type and no runtime.

**The accurate statement, which the plan should carry:** *the trace side and the turn-metric side both
group by runtime; the Postgres side cannot group by it at all, on any relation.* The reconciliation the
criterion asks for therefore still cannot be expressed — but the fix is narrower than recorded (a runtime
column on the ledger, or promoting the parity battery's manifest attribution), and the metric half of the
axis already exists.

Nothing was run: the battery needs a full stack, live Bedrock credentials and both runtimes bootable.

### C4 — single-host Docker POC, with and without Phoenix · **PARTLY PROVEN, and far further than recorded**

**Docker is present and working on this host** (server 29.1.3, 12 containers up). The spec was written
without that fact.

- **The stack boots, for real, and every service becomes healthy.** With
  `OTEL_COMPOSE_SMOKE=1 OTEL_RULES_CHECK=1`, the otel lane is
  `rootdir: /home/aditya/Code/copilot-mro-obsm  collected 160  →  160 passed, 0 skipped, 0 failed`
  in 174 s. The thirteen `compose_stack` tests each bring up a real compose project —
  `deployment/docker-compose.yml` + `deployment/docker-compose.phoenix.yml` +
  `deployment/otel/smoke/docker-compose.smoke.yml`, services `otel-collector loki prometheus tempo
  phoenix` — wait on readiness, assert, and tear down with `down -v`. **Teardown verified clean:**
  `docker ps -a | grep smoke` and `docker network ls | grep smoke` are both empty afterwards.
- **Every collector profile also starts healthy on the pinned image.**
  `bash copilot-mro-obsm/deployment/otel/validate.sh` → **exit 0**, covering `aws`, `azure`, `newrelic`,
  `oss`, `aws+phoenix`, each twice (shipped storage default and bind-mounted), and each of the four
  `production-durability` compositions likewise.
- **The Phoenix-less limb is proven statically, not by a second boot.** The smoke composition *requires*
  the Phoenix overlay (the base stack owns no `image:` for the service, so compose refuses the project
  without it). That the base stack emits no Phoenix-bound pipeline is covered by
  `test_collector_profiles.py`, which is inside the 160.
- **BLOCKED, and it is a ruling, not a run: there is no budget.** No compose file under
  `copilot-mro-obsm/deployment` declares `mem_limit`, `cpus`, `deploy.resources` or `pids_limit` — the
  grep returns nothing. The phrase "resource budget" occurs in exactly four places in the whole estate
  and **all four are plan lines asking for one.** The check has no pass condition. The measurement is now
  cheap (`docker stats` against the smoke project, which is proven to come up); only the number is
  missing.

### C5 — destination swap on identical images · **PARTLY PROVEN; the `oss` destination is proven END TO END**

- **Static, complete:** the otel lane at 160/160 (above) covers `test_collector_profiles.py` (per-overlay
  specifics for oss/aws/azure/newrelic, complete-pipeline restatement,
  `test_every_log_pipeline_ends_with_redaction_before_batch`), `test_profile_env_documented.py`,
  `test_collector_base_config.py`, `test_collector_self_telemetry.py`, `test_emitted_series_inventory.py`.
- **`deployment/otel/validate.sh` exit 0** — see C4. This is stronger than "the config parses": the script
  *starts* each composition and polls its health endpoint, precisely because `validate` never builds a
  component.
- **The `oss` destination has a real, retrieved canary — through the pinned collector.**
  `tests/integration/otel/test_oss_profile_smoke.py` posts OTLP/JSON to a live collector and then
  retrieves: a span from **Tempo**, a DELTA monotonic sum from **Prometheus** (whose mere existence proves
  `delta_to_cumulative` ran, since `prometheusremotewrite` drops unconverted delta sums), a log from
  **Loki** under the tenant with an untenanted read refused, health-route spans dropped,
  `gen_ai.input.messages` stripped before Tempo, log bodies masked, browser-record keys pruned, and
  `test_prometheus_serves_the_exact_names_the_inventory_computes` pushing **one synthetic datapoint per
  inventoried instrument** and asserting Prometheus serves exactly the names `prometheus_names()`
  predicts. All thirteen passed.
- **Trace propagation into the estate:** `api-obsm/tests/integration` → **354 collected, 353 passed, 1
  skipped**, which includes the gateway-hop instrumentation tests. Still hop-by-hop; see §6.
- **BLOCKED:** `aws`, `azure` and `newrelic` need client credentials this workspace does not have. The
  identical-image property across destinations is asserted statically and proven live for one
  destination only.

### C7 — refresh the catalogue's live/dark markers · **PARTLY PROVEN; zero promotions are possible**

- **Grammar and agreement: proven** — inside the 160. `_emitted_series.py` is the single inventory;
  `test_emitted_series_inventory.py` proves each entry against `agent_shared/telemetry.py` (instrument
  exists, kind matches the constructor, it is recorded, its public recorder does or does not have a
  production call site); `test_grafana_dashboards.py` and `test_alert_rules_layout.py` consume it.
- **The state has MOVED since the spec was written.** Counted from
  `copilot-mro-obsm/tests/integration/otel/_emitted_series.py` directly: **14 `Series` — 12 `wired`,
  2 `dark`, 0 `live`** — plus **5 `SpanSignal`, all `wired`**. The spec recorded 9 wired / 5 dark. The
  three that moved are exactly merge-plan **G.6**: `agent.ledger.write_failures`, `agent.subagent.calls`,
  `agent.subagent.duration_seconds`. The two remaining dark are both **G.4** (`claude_code.token.usage`,
  `claude_code.cost.usage`), whose producer is the CLI, outside this repo.
- **BLOCKED, and now measured rather than assumed.** A `wired` → `live` flip requires a probe to have seen
  *the application's own emitter* produce the series. The dev observability stack is up (loki,
  alertmanager, prometheus, grafana, tempo, otel-collector, 13–14 h uptime) **and it has received nothing**:
  - `otelcol_receiver_accepted_spans_total` → empty result set
  - `otelcol_receiver_accepted_metric_points_total` → empty result set
  - Tempo `/api/search/tag/service.name/values` → `{"tagValues":[]}`
  - Prometheus `__name__` label: 1,189 series names, **zero** matching `agent_*`, `gen_ai_*` or
    `claude_code_*` (the only `*agent*` hits are Prometheus's own `prometheus_agent_*`).
  - **And the running stack was started from
    `/home/aditya/Code/copilot-mro/deployment/docker-compose.yml` — the PRE-MERGE checkout** (read from
    the container's own compose labels). Even a canary taken from it would measure the wrong tree.
- **A ruling is owed on whether the smoke counts.** `test_prometheus_serves_the_exact_names_the_inventory_computes`
  retrieves every built instrument's name from a real Prometheus, and its own docstring calls itself "the
  first real step of the WIRED-to-LIVE probe". But the producer is the test, not `RuntimeTelemetry`, and
  the inventory's definition of `live` is "a probe saw the data … never claimed on the strength of code
  reading". **Recommendation: this proves the name/unit/exporter contract and should be recorded as such;
  it is not sufficient for `live`, because `wired` already means "an emitter exists and is reached from
  production" and the smoke does not exercise that emitter.** Do not promote on it without the owner
  saying so.

### C8 — close the documents · **NOT DONE, and currently false**

Nothing was ticked (per the brief). Three concrete document/tree disagreements were found tonight and are
listed in §7; the spec's own list of six is partly stale as well. C8 is last by definition.

### I1 — operational and product-event contracts stay separate · **PROVEN in substance**

All three halves are green in one night for the first time:
- product side — the 269 (C1 lane), including
  `core-obsm/tests/unit/analytics/test_no_loki_references.py`;
- collector side — the 160 (otel lane);
- browser side — `dashboard-obsm` 2533/2533, which contains
  `tests/unit/telemetry/exporter-ingest-routing.test.ts`, `ingest-contract.test.ts`,
  `exporter-wire-shape.test.ts`, `exporter-retry-classes.test.ts`, `route-telemetry.test.tsx`,
  `mutation-telemetry-coverage.test.ts`;
- forwarder side — `core-obsm/tests/api` 884/884, which contains `tests/api/logging/`.

**Caveat unchanged from the spec and still true:** no single test states the invariant; it is assembled
from four suites, and a future change that violated it would have to break one of them to be noticed.

### I2 — the profile exposes no vendor config and weakens no authorization · **PROVEN**

Inside the 269. `test_profile_response_contains_no_vendor_or_destination_metadata` and
`test_profile_hidden_panel_is_still_refused_by_direct_panel_endpoint` both verified present in
`core-obsm/tests/api/analytics/test_dashboard_profile_endpoint.py` and both green.

### I3 — no provider is called production-supported from configuration alone · **NOT PROVEN — but the evidence improved**

- **Corrected upward:** the spec says the four `durability-production-*.yaml` overlays "are statically
  asserted and have never been restarted". They are no longer only statically asserted —
  `validate.sh` **starts** each of them on the pinned contrib image, twice, and each reports healthy with
  its file-storage directories created. That is a boot proof, not a restart proof.
- **Still absent, and I looked:** no test anywhere in `copilot-mro-obsm/tests/integration/otel` restarts a
  collector or asserts the sending queue survives one — the grep for a restart assertion returns nothing.
- **Still absent:** a retrieved canary for any provider but `oss` (C5), and the Azure go/no-go. No `NO-GO`
  marker exists in the tree in either direction.

### I4 — no metric gains an unbounded identifier · **PARTLY PROVEN; one limb is unfalsifiable**

- **Bounded-set limb: proven** — inside the 160.
  `test_collector_base_config.py::test_metric_cardinality_deletes_identity_and_path_keys` (nine keys,
  read and confirmed at `deployment/otel/base.yaml:76-95`),
  `test_tempo_span_metrics.py::test_no_per_span_or_identity_attribute_is_a_dimension`,
  `test_alert_environment_routing.py::test_remote_write_never_promotes_resource_attributes_to_series_labels`,
  plus `test_emitted_series_inventory.py`'s `KNOWN_LABELS`.
- **`tenant.id` limb: cannot be evaluated.** The approved tenant-scoped instrument list does not exist —
  grep for `TENANT_SCOPED_INSTRUMENT` / `tenant_scoped_instruments` / `APPROVED_TENANT` returns only
  `approved_tenant_classes`, which is model-governance and unrelated. **G.17 is unticked and the list it
  would create is the missing pass condition.** Note that `record_turn` *does* attach `tenant.id` to
  `agent.turn.calls` and `agent.turn.duration_seconds` today (`telemetry.py:1835`), so there is a live
  instrument waiting to be judged against a list that does not exist.

### I5 — no product total treats sampled or expired telemetry as authoritative · **PROVEN, with the scope caveat**

`core-obsm/tests/unit/analytics/test_no_loki_references.py` is inside the 269 and green. Verified
independently: a case-insensitive sweep of `core-obsm/core/resources/analytics/` for
`loki|prometheus|tempo` returns **one** hit and it is the string `"Analytics are temporarily
unavailable"` in an error message. **Caveat unchanged:** the guard is repo-scoped to `core`; `dashboard`
and `api` have no equivalent.

### I6 — no duplicate writer or projection for `chat_turn_facts` · **NOT PROVEN — THIS ROW CHANGED TONIGHT**

The spec says "**No online writer exists**, so the invariant is trivially satisfied and becomes
meaningful only when G.5 lands". **G.5 landed.** There are now two writers:

1. `core-obsm/scripts/backfill_chat_turn_facts.py:323` — the offline backfill;
2. `copilot-mro-obsm/copilot_mro/app/db/chat_history/blocks.py:541` `_write_chat_turn_facts`, called at
   `:748`, using `FACTS_UPSERT_SQL` from
   `copilot-mro-obsm/copilot_mro/app/db/postgres_table_definitions_modules/chat_turn_facts.py:347`.

That is by design (ruling M-SAVEPOINT), so "exactly one code path writes the relation" is now false as
written and needs restating. What was supposed to make two writers safe is the projection parity test plus
the drift pin — **and the drift pin is reading the wrong checkout.** Verified myself, not relayed:

```
core-obsm/tests/unit/analytics/test_chat_turn_facts_drift_pin.py:24
    _MRO_ROOT = sibling_repo(__file__, "copilot-mro")
resolved  →  /home/aditya/Code/copilot-mro          (the PRE-MERGE checkout, branch langgraph-merge)
and       →  that file has NO `facts_from_block_data` (its only hit is a comment at line 43);
             the definition is at copilot-mro-obsm/…/chat_turn_facts.py:195
```
`copilot-mro-obsm` is a git worktree **of** `copilot-mro`, so resolving the sibling **by name** finds the
primary checkout. The pin is green today only because the constants it compares happen to be equal across
the two branches. **The mechanism that carries I6 is certifying a tree that is not under test.** This is
G.25(a), open, and it is the correct first item of core's G.5 pass.

Estate-wide sweep otherwise holds: `api`, `api-obsm`, `dashboard`, `dashboard-obsm`, `utils`,
`utils-obsm`, `shift-optimizer` and `telegram-bot` contain no reference to the relation at all.

### I7 — Docker-only and single-host stay explicit · **PROVEN today, by grep, with no guard**

Estate-wide sweep of `.py`/`.ts`/`.tsx`/`.yml`/`.yaml`/`.tf` (excluding `node_modules`, `.git`) for
`kubernetes|helm`: the only genuine hits are **one explanatory comment** in
`api/flynapse_api/config/config.py:105` (and its `api-obsm` mirror) and **two test docstrings**. No
manifest, no chart, no operator. Compose shape is covered by `test_compose_port_bindings.py` and
`test_smoke_network_scoping.py` inside the 160. **No test enforces the absence** — it remains a grep.

### I8 — `otel-lgtm` remains deferred · **PROVEN today, by grep, with no guard**

Every hit in the estate is plan or spec markdown:
`copilot-mro-obsm/docs/superpowers/specs/2026-09-09-…-design.md`,
`docs/plans/observability-rebuild-phase-11-audit-followups.md`,
`docs/plans/observability-merge-completion.md`, `docs/plans/observability-rebuild.md`,
`docs/plans/observability-close-out-gate.md`,
`docs/plans/observability-rebuild-research/08-post-migration-rescoping.md`.
No compose service, image pin, overlay or code path. **No test enforces the absence.**

### Appendix row — C6 (already ticked) — metric cardinality

First limb proven (identical evidence to I4's bounded-set limb, inside the 160). Second limb — `tenant.id`
only on approved instruments — unfalsifiable for the same reason as I4. **The tick covers half a check,
and it was ticked before the other half had a pass condition.**

---

## 4. Full-estate lane table

One invocation per test directory. `rootdir` printed and checked on all 48 invocations. Every merged-tree
lane used the merged `PYTHONPATH`; pre-merge control lanes used the mainline one.

### `copilot-mro-obsm` — `rootdir: /home/aditya/Code/copilot-mro-obsm`

| lane | collected | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests/agent_sdk` | 4182 | 4174 | 2 | 0 | 6 |
| `tests/agent_services` | 44 | 44 | 0 | 0 | 0 |
| `tests/api` | 790 | 790 | 0 | 0 | 0 |
| `tests/architecture` | 69 | 68 | 1 | 0 | 0 |
| `tests/chat` | 95 | 95 | 0 | 0 | 0 |
| `tests/config` | 22 | 19 | 3 | 0 | 0 |
| `tests/data_views` | 9 | 9 | 0 | 0 | 0 |
| `tests/db` | 694 | 659 | 3 | **13** | 18 (+1 xfail) |
| `tests/demo` | 122 | 121 | 1 | 0 | 0 |
| `tests/documents` | 9 | 9 | 0 | 0 | 0 |
| `tests/e2e` | 595 | 594 | 0 | 0 | 1 |
| `tests/file_readers` | 80 | 79 | 0 | 0 | 1 |
| `tests/fixtures` | 0 | — | — | — | — |
| `tests/ingestion` | 42 | 41 | 0 | 1 | 0 |
| `tests/integration` (flags off) | 314 | 288 | 0 | 0 | 26 |
| ↳ `tests/integration/otel` alone, flags off | 160 | 134 | 0 | 0 | 26 |
| ↳ `tests/integration/otel`, `OTEL_RULES_CHECK=1` | 160 | 147 | 0 | 0 | 13 |
| ↳ `tests/integration/otel`, **both flags** | 160 | **160** | 0 | 0 | **0** |
| `tests/parsers` | 303 | 270 | 1 | 1 | 31 |
| `tests/registries` | 177 | 177 | 0 | 0 | 0 |
| `tests/sandbox` | 26 | 26 | 0 | 0 | 0 |
| `tests/seeds` | 62 | 62 | 0 | 0 | 0 |
| `tests/smoke` | 52 | 51 | 1 | 0 | 0 |
| `tests/unit` (excluding `lang_agent`) | 4964 | 4941 | 6 | **8** | 9 |
| `tests/unit/lang_agent` | 1152 | 1152 | 0 | 0 | 0 |
| **repo total** | **13803** | **13669** | **18** | **23** | **92** (+1 xfail) |

`tests/unit/lang_agent` took **10 min 19 s**, not the 14–17 the brief budgeted.

### `api-obsm` — `rootdir: /home/aditya/Code/api-obsm`

| lane | collected | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests/api` | 14 | 14 | 0 | 0 | 0 |
| `tests/e2e` | 0 | — | — | — | — |
| `tests/integration` | 354 | 353 | 0 | 0 | 1 |
| `tests/middleware` | 280 | 280 | 0 | 0 | 0 |
| `tests/smoke` | 24 | 21 | 0 | 0 | 3 |
| `tests/startup` | 69 | 69 | 0 | 0 | 0 |
| `tests/unit` | 650 | 650 | 0 | 0 | 0 |
| **repo total** | **1391** | **1387** | **0** | **0** | **4** |

### `core-obsm` — `rootdir: /home/aditya/Code/core-obsm`

| lane | collected | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests/api` | 884 | 884 | 0 | 0 | 0 |
| `tests/authz` | 285 | 285 | 0 | 0 | 0 |
| `tests/db` | 584 | 580 | 0 | 0 | 2 (+2 xfail) |
| `tests/e2e` | 0 | — | — | — | — |
| `tests/fixtures` | 0 | — | — | — | — |
| `tests/unit` | 1232 | 1232 | 0 | 0 | 0 |
| **repo total** | **2985** | **2981** | **0** | **0** | **2** (+2 xfail) |

### `utils-obsm` — `rootdir: /home/aditya/Code/utils-obsm`

| lane | collected | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests/unit` (at `1cdebad`) | 1316 | 1316 | 0 | 0 | 0 |

(1252/1252 at `21fc319` earlier in the run; G.24 + G.29 added 64 tests, all green.)

### `iac` — `rootdir: /home/aditya/Code/iac`

| lane | collected | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests/unit` | 142 | 142 | 0 | 0 | 0 |

### `dashboard-obsm` — node test runner, cwd `/home/aditya/Code/dashboard-obsm`, head `fdf7487`

| lane | tests | pass | fail | skipped |
|---|---:|---:|---:|---:|
| `npm run test:unit` | 2533 | 2533 | 0 | 0 |

### Non-pytest validators, all run tonight

| validator | result |
|---|---|
| `copilot-mro-obsm/deployment/otel/validate.sh` | **exit 0** — aws, azure, newrelic, oss, aws+phoenix, plus all four `production-durability` compositions; each validated, then STARTED and polled healthy twice (shipped storage default, then bind-mounted) |
| `copilot-mro-obsm/deployment/observability-local/validate-rules.sh` | **exit 0** — promtool on every Prometheus rule file, amtool on both alertmanager configs, all eight environment-routing cases, Loki ruler YAML shape |
| `iac/scripts/validate_alarms.py` | **exit 0** — 19 §2.1 alerts with an aws form + 2 oss-only with a reason |
| `iac/scripts/validate_metric_vocabulary.py` | **exit 0** — dialect, dimensions, gating, and the three-state signal grammar incl. the "no LIVE without a probe this root ran" rule |
| `iac/scripts/validate_dashboards.sh` | **exit 0** — 4 templates parse |
| `terraform fmt -check -recursive` (in `iac`) | **exit 0** |

### Estate roll-up

**19,637 Python checks collected · 19,495 passed · 18 failed · 23 errors · 98 skipped · 3 xfailed**,
plus **2,533 dashboard checks, 2,533 passing**. With the two otel env gates set, the copilot-mro
integration lane's 26 skips become passes, so the best achievable figure is **19,521 passed / 72 skipped**.

---

## 5. Failure triage — what is pre-existing and what the merge caused

Method: every failing file was re-run against the **pre-merge sibling** with the mainline `PYTHONPATH`,
same database, same flags. That is the only discriminator that survives the identical-count trap.

### 5.1 Pre-existing on both branches — 17 failures, 1 error. **Do not read these as merge defects.**

| test | merged | pre-merge | note |
|---|---|---|---|
| `tests/agent_sdk/tools/database/test_agent_sdk_sql_examples_live.py` (2 params: `engineer_shifts`, `flight_schedule`) | 2 F | 2 F | data-dependent "live" SQL examples |
| `tests/architecture/agent_runtime/test_langchain_ambient_surface_policy.py::test_no_surface_can_flip_the_model_wire_shape_ambiently` | 1 F | 1 F | |
| `tests/config/settings/test_config.py` (3) | 3 F | 3 F | asserts `Settings.followup_max_additional_attempts` and `.sandbox_max_concurrent`, **which no production config module in either checkout defines** — the field names occur only in the test file |
| `tests/db/tenancy/test_schema_conformance.py` (3) | 3 F | **5 F** | **the merge IMPROVES this file**; see 5.2 |
| `tests/demo/techpub/test_techpub_fixtures.py::test_twice_monthly_sources_are_not_due_today` | 1 F | 1 F | date-dependent |
| `tests/parsers/base/test_pdf_parser.py::test_with_pdf_file` | 1 E | 1 E | |
| `tests/parsers/pilot/test_parser_metadata_sidecars.py::test_ftd_insert_to_postgres_ensures_standalone_tables` | 1 F | 1 F | |
| `tests/smoke/document_hub/test_document_hub_package_import.py::test_no_module_imports_the_vector_index_at_module_scope` | 1 F | 1 F | the one the brief named |
| `tests/unit/db/test_documented_database_names.py` + `test_migration_snapshot.py` | 2 F | 2 F | |
| `tests/unit/improvement/test_attribution_candidates.py` + `test_target_registry.py` (2) | 3 F | 3 F | |

**The brief's "two in `core-obsm`" is stale: `core-obsm` has ZERO failures and ZERO errors** across 2,985
collected checks. The pre-existing failure population lives entirely in `copilot-mro`.

**Two failures the merge FIXED:** `tests/unit/observability/test_bedrock_call_sites_name_a_tenant.py`
(`test_no_call_bedrock_messages_site_omits_the_tenant`,
`test_streaming_synthesis_folds_its_cost_under_a_tenant`) fail on the pre-merge sibling and pass on the
merged tree.

### 5.2 The test database is stale, and it is the cause of three of those failures

`tests/db/tenancy/test_schema_conformance.py::test_the_live_database_conforms` names it exactly:

```
copilot_mro_test has been migrated: all 111 declared relation(s) present carry their injected
tenancy columns, and it does not conform:
  [declared_columns_are_not_null] 3 violation(s):
    data_discovery_jobs.object_count  is declared NOT NULL by copilot-mro and is nullable
    data_discovery_jobs.table_count   is declared NOT NULL by copilot-mro and is nullable
    data_discovery_jobs.column_count  is declared NOT NULL by copilot-mro and is nullable
  [every_declared_relation_exists] 1 violation(s):
    llm_turn_content is declared 'tenant' by copilot-mro and is not present in copilot_mro_test
```

Two facts the spec did not carry:

- **`llm_turn_content` is NEW with the merge** — the module does not exist in the pre-merge checkout at
  all (`copilot-mro/copilot_mro/app/db/postgres_table_definitions_modules/llm_turn_content.py`: no such
  file). So this is not merely "the test DB is one table behind the dev DB"; it is the merged tree
  declaring a relation the test database has never been migrated for.
- **The `data_discovery_jobs` NOT NULL trio is a separate, second defect** — the failure text names the
  cause: a two-phase migration that strips NOT NULL from a declared column with no DEFAULT and restores
  it after the backfill, with a run committed between the two halves.

**A re-migration of `copilot_mro_test` is owed before this file can be green, and it is environment work,
not merge work.**

### 5.3 Twenty-one "errors" that are an artefact of lane granularity, not of code

| lane | at level 1 | at level 2 |
|---|---|---|
| `copilot-mro-obsm/tests/db/improvement` | **13 errors** (inside `pytest tests/db`) | **49 collected, 49 passed** alone |
| `copilot-mro-obsm/tests/unit/observability/test_nonagent_lifecycle_spans.py` | **8 errors** (inside `pytest tests/unit`) | gone — `tests/unit/observability` alone is 211 collected, 1 failed |

The error is always the same and it is the namespace-package signature:

```
ImportError: cannot import name 'initialize_postgres_tables' from 'copilot_mro.app.db' (unknown location)
```

`(unknown location)` means an earlier test in the same session left `copilot_mro.app.db` in `sys.modules`
as a namespace placeholder. **This is exactly the G.26 / G.27 class the ledger recorded, and it is live in
`tests/db` and `tests/unit` today.** Pre-existing: the pre-merge sibling's `pytest tests/db` produces
**the same 13 errors** (and 6 failures where the merged tree has 3).

**The operational lesson for whoever runs this gate next:** the per-directory rule is not neutral. Running
level 1 manufactures 21 errors that level 2 does not show; running level 2 conceals a real cross-file
defect that only the combined run exposes (CHECKPOINT 14's G.27). **Both granularities have to be run, and
the difference between them is data, not noise.**

### 5.4 The one merge-attributable failure — and it is a guard working correctly

```
copilot-mro-obsm/tests/unit/observability/test_phase1c_nonagent_scope_guard.py
    ::test_post_merge_diff_uses_only_approved_production_paths                      FAILED

AssertionError: Post-merge observability work changed an unapproved MRO production path:
  ['copilot_mro/app/db/chat_history/blocks.py',
   'copilot_mro/app/db/postgres_table_definitions_modules/chat_turn_facts.py']
```

This test does not exist on the pre-merge sibling (whose `tests/unit/observability` fails two entirely
different tests). It reaches the **working tree, not HEAD**, deliberately — "the only way a scope guard can
speak about work that is still being reviewed".

**Cause: G.5's writer landed two production edits tonight and nobody extended the guard's approved-path
set.** The guard is right and the allow-list is stale. It is red in the merged working tree right now, it
is not recorded anywhere in the ledger or the plan, and **it is the only thing in this entire sweep that a
reviewer could legitimately call a merge defect.** It is a one-line list edit plus the judgement that G.5's
two paths are in scope — which the M-SAVEPOINT ruling already implies.

---

## 6. What cannot be proven without the owner — itemised, with what each needs

| # | what | which rows | what it needs |
|---|---|---|---|
| 1 | **A resource budget number.** No compose file declares any limit; the phrase occurs only in plan lines asking for it. | C4 | **A ruling: one number.** The measurement is then a `docker stats` capture against the smoke project, which is proven to come up and tear down cleanly. Minutes. |
| 2 | **The approved tenant-scoped instrument list and its cardinality bound.** G.17 / Task R.2. Meanwhile `agent.turn.calls` and `agent.turn.duration_seconds` already carry `tenant.id`. | I4, and half of the already-ticked C6 | **A ruling, then a list in code.** Until then half a ticked check is unfalsifiable. |
| 3 | **"Restricted administrator" does not exist.** The estate's authorization axis is tenant owner vs capability holder. | C2 | **A ruling:** rewrite the check to the roles that exist, or build the role. |
| 4 | **`dashboard_profiles` has no writer.** The "one tenant cannot **alter** another's profile row" limb has no code path. | C2 | **A ruling** (B2-R3): is a writer in scope, or is the criterion narrowed to reads? |
| 5 | **Client credentials for aws / azure / newrelic.** `oss` is proven end to end; the other three are config-only. | C5, I3 | **Credentials + a provider call per destination**, each on the same image as the run before it. |
| 6 | **A collector restart with a populated file-backed queue.** The four durability overlays now boot healthy but have never been restarted. | I3 | **A live run** — bring a profile up, fill the queue, kill the collector, restart, prove the queue drained. |
| 7 | **The Azure go/no-go.** No `NO-GO` marker exists in the tree in either direction. | I3 | **A ruling.** |
| 8 | **An application driven against a collector**, so the runtime's own instruments emit. Measured tonight: the running stack has accepted **zero** spans and **zero** metric points, and it was started from the pre-merge checkout. | C7 (all promotions), and the honest half of C5 | **A live stack running the MERGED tree**, plus a retrieval per series. |
| 9 | **Does the compose smoke's synthetic retrieval count as a `live` probe?** It retrieves every built instrument's name from a real Prometheus but the producer is the test, not `RuntimeTelemetry`. | C7 | **A ruling.** Recommendation in §3: no — record it as a name/unit/exporter proof, keep `wired`. |
| 10 | **A runtime axis that Postgres and telemetry share.** No relation carries a runtime; the turn span and the turn metrics both do. | C3 | **A schema decision** (a runtime column on the ledger, or promoting the parity battery's manifest attribution), *then* a live stack with Bedrock credentials and both runtimes. |
| 11 | **Two writers for `chat_turn_facts` is now the design.** The criterion still says "exactly one". | I6 | **A ruling restating the criterion** — and separately a **code fix** (G.25(a)) so the drift pin reads the tree under test. |
| 12 | **G.5's two production paths are not on the phase-1c scope guard's approved list**, so that guard is red in the working tree. | none directly; it is a red lane | **Not owner-blocked** — a list edit, once the owner confirms G.5's scope, which M-SAVEPOINT already implies. |
| 13 | **`copilot_mro_test` has never been migrated for the merged tree** (`llm_turn_content` absent; `data_discovery_jobs` NOT NULL trio half-applied). | C1/C2's DB lanes are unaffected; `tests/db/tenancy` is red | **Environment work**, owner-run: re-migrate the test database. |

---

## 7. Everything in the spec or the brief that was wrong

### The close-out-gate spec (`observability-close-out-gate.md`)

| claim | what is true tonight |
|---|---|
| Lane B "Green today, **132 passed / 26 skipped**" | **160 collected.** 134/26 with no flags, **147/13** with `OTEL_RULES_CHECK=1`, **160/0** with both gates set. |
| "Treat a skip in Lane B as a failure: **the 26 skips are the container-gated tests**, and a run that reports them as skips has not measured them." | Half right and wholly actionable. The 26 are **two different gates** — 13 on `OTEL_RULES_CHECK=1` (promtool / amtool in `docker run --rm`, no ports, no effect on a running stack) and 13 on `OTEL_COMPOSE_SMOKE=1`. **Docker is present on this host and all 26 pass.** They were never unrunnable; they were unrun. |
| C4 live half: "**needs something we do not have**" | The stack boots and every service becomes healthy — 13 compose-smoke tests green, teardown verified clean. Only the **budget number** is missing. |
| C5 live half: "**Live retrieval exists for no provider**" | **False for `oss`.** `test_oss_profile_smoke.py` retrieves a span from Tempo, a delta sum from Prometheus, a log from Loki under a tenant with untenanted reads refused, and every inventoried instrument's Prometheus name — all through the pinned collector. |
| C7 "**14 declared series — 9 `wired`, 5 `dark`**, 0 `live`" | **12 `wired`, 2 `dark`, 0 `live`.** G.6 wired `agent.ledger.write_failures`, `agent.subagent.calls` and `agent.subagent.duration_seconds` tonight. The 2 remaining dark are both G.4 `claude_code.*`. |
| I3 "the four `durability-production-*.yaml` overlays are **statically asserted**" | They are **booted**. `validate.sh` starts each composition on the pinned image and polls it healthy, twice. Still no restart proof. |
| I6 "**No online writer exists**, so the invariant is trivially satisfied" | **Stale.** G.5's writer is at `copilot-mro-obsm/copilot_mro/app/db/chat_history/blocks.py:541`. And the drift pin that was supposed to make the mirror safe resolves the **pre-merge** checkout. |
| "Two trees are being written in right now — `api-obsm` (C2) and `dashboard-obsm` (B2)" | Both landed. `api-obsm@cc56667`, `dashboard-obsm@fdf7487` (G.22 as well). C2's dashboard half and I1's browser half are runnable now, and green. |
| C2 "**Gaps:** … no test crosses two tenants with the role axis" | Still true, and there is a **second** gap the spec did not name: `dashboard_profiles` has **no writer at all**, so the "cannot alter another tenant's row" limb has nothing to test. |
| `VENV -m pytest` with `cd <repo>` | Works, but note that `python -m pytest` puts cwd on `sys.path` and a `poetry -C api run` shell resolves `flynapse_api` to the **pre-merge** checkout. Use the console script from a neutral cwd with absolute paths. |

### This brief

| claim | what is true |
|---|---|
| "Known pre-existing failures … one in `copilot-mro-obsm/tests/smoke/document_hub`, **two in `core-obsm`**" | The `document_hub` one is confirmed. **`core-obsm` has zero failures and zero errors** across 2,985 checks. The pre-existing population is **17 failures + 1 error, all in `copilot-mro`**, plus 21 errors that appear only at level-1 lane granularity. |
| "the database records no runtime while the trace records it under a different name and **no metric carries it**" | The first two clauses are correct and I verified them column by column. **The third is false:** `agent.turn.calls` and `agent.turn.duration_seconds` carry `gen_ai.agent.name`, and the collector's nine-key cardinality processor does not delete it. The model metrics and the ledger genuinely do not carry it. |
| "`core-obsm` and `utils-obsm` bake `-q` into `addopts`" | True — and **`api-obsm` bakes `-v --tb=short`**, so the `-o addopts=` override is needed in three repos, not two. |
| "`tests/unit/lang_agent` … takes **14–17 minutes**" | **10 min 19 s**, 1152 collected, 1152 passed. |
| The scratch-DB lane diagnosis | **Confirmed, and still unfixed.** `core-obsm/scripts/run_db_lane.py` *has* an uncommitted change tonight — but it replaces a depth-coupled `parents[1]` with a marker walk (a sixth sibling-checkout instance), **not** the missing `provision_rls.py` half. The deferral is now written into the file at `:297-307`. And the claim that the close-out does not depend on it is **confirmed**: both named lanes pass against `copilot_mro_test` (12/12), and the whole Lane A is 269/269. |

---

## 8. What I could not run, and why

Stated plainly, because an unrun check reported as passing is the defect this phase exists to prevent.

1. **Any canary for `aws`, `azure` or `newrelic`.** No client credentials in this workspace. C5's
   identical-image property is therefore proven live for **one** destination.
2. **Any promotion of a series from `wired` to `live`.** This needs the merged application emitting into a
   collector. It was not run, and I measured why it could not be faked: the dev stack has accepted zero
   spans and zero metric points, and it is the **pre-merge** compose project anyway.
3. **The dual-runtime parity battery** (`tests/e2e/agent_runtime/run_runtime_parity_e2e.py`). Needs a full
   stack, live Bedrock credentials and both runtimes bootable — and the reconciliation it is supposed to
   feed cannot be expressed against Postgres at all.
4. **A collector restart / queue-durability proof.** No such test exists to run; building one is work, not
   a lane.
5. **A `docker stats` budget capture.** There is no budget to compare a capture against, so a number
   captured now would be a number with no verdict attached.
6. **`core/scripts/run_db_lane.py`'s scratch lane.** I deliberately did not create a throwaway database. I
   confirmed the diagnosis by reading the script instead, and confirmed by running that the close-out does
   not depend on it.
7. **`dashboard-obsm`'s Playwright e2e specs and `next build`.** Eleven specs, none telemetry; `next build`
   is refused in a worktree by an existing guard. The dashboard evidence here is the 2,533-check unit
   suite.
8. **An end-to-end browser → Next route → api → core forwarder → collector trace.** Each hop is unit-tested
   in isolation and all hops are green; nothing exercises them as one trace, and nothing in the estate can.
9. **Anything that would have written to a tree.** No plan box was ticked, no guard allow-list was
   extended, no test database was re-migrated, and the one red guard in §5.4 was left red.

Two side effects to declare, neither in a repository: the compose smoke created and destroyed an ephemeral
`flynapse-otel-smoke-p1` project (teardown verified), and `deployment/otel/validate.sh` left four
`/tmp/tmp.*` directories holding queue files owned by uid 10001 — the script announces this itself
(`note: left /tmp/tmp.… (queue files owned by uid 10001)`), it is its normal behaviour, and it is outside
every repository.

---

## THE GATE'S METHOD WAS MEASURED, AND THE NUMBERS BELOW ARE NOW QUALIFIED — 2026-09-20

A read-only sweep ran **~180 pinned invocations** across six trees, asserting module resolution before
trusting any number and reporting `rootdir` on every one. **Its control reproduced this gate's published
copilot-mro figure exactly (18 failures)**, which is what makes the comparison fair.

**152 checks are green under this gate's method and red when their repo runs in one process:**
146 in `copilot-mro-obsm`, 6 in `api-obsm`, **0** in `core-obsm`, `utils-obsm`, `iac`. `dashboard-obsm` is
**structurally immune** — `package.json:17` runs node's built-in test runner, which forks **one child
process per test FILE** (proven with a two-file pid probe, not assumed), so the class cannot exist there.
The converse is also true and worth knowing: **that runner can never CATCH a cross-file process-global
defect either.**

**In the other direction, 9 checks are red per-directory and green everywhere else** — all in
`copilot-mro-obsm/tests/unit` at level 1. **So neither granularity dominates: run both and treat the
difference as data.** That rule was already reached here; the evidence for it is now much stronger.

**A fourth class nobody had named — multi-arg-only.** Naming two directories in one invocation collides
their `conftest.py` files on the module name `conftest` and **aborts the session with 7 collection errors**,
reproduced 3/3 in both orders, and **absent from both the single-directory run and the whole-suite run**.
This is the veto on the cheap middle option: a grouped gate would fail loudly on a defect that exists at
neither granularity while still missing part of the class it was meant to catch.

**RULING: one invocation per repo over the whole `tests/` tree, one argument per invocation, and KEEP the
per-directory lanes.** Cost is roughly nothing — whole-suite is **faster** than the per-directory sum in
four of five repos (−15 %, −46 %, −63 %, −49 %) and +23 % in copilot-mro-obsm. **Estate-wide: +5 minutes.**
Per-invocation interpreter overhead is 1.8–2.1 s, so the current ~48 invocations already spend ~1.6 min on
startup, and **finer granularity costs more while hiding more** — level 2 is 17 % more expensive than
level 1 for the same 6,202 tests and is the granularity that hides the most.

**Two of the 152 are live PRODUCT defects, not test hygiene:** a **P0** that breaks the WORKOUT tool on
every success path in any INFO-level deployment (plan item G.86, merge-introduced, traced by `git log -S`
to a named commit), and an HTTP-semconv initialisation-order defect that silently reverts spans to legacy
attribute names — **the exact names the merged dashboards and alert rules query** (G.87). Roughly two-thirds
of the remaining 146 trace to **two lines of test support** (G.88).

**A hazard for whoever parallelises this gate: `copilot_mro_test` is shared mutable state across pytest
invocations.** The lanes are independent only because they run serially. The sweep manufactured 18 phantom
errors against itself this way and caught it only by re-running the lane alone.

**Not established, stated plainly: whether the 152 are merge-attributable.** No pre-merge sibling controls
were run — the single highest-value follow-up. The two that WERE traced both are.

**Method note that applies to every number in this file:** the sweep retracted two of its own findings —
6 `core-obsm` failures and 31 `copilot-mro-obsm` errors — after establishing they were a live implementer's
mid-lane write and its own concurrency, caught behind a `find -newermt` fence. **A number taken while
another agent is writing the tree is not a measurement.**
