# Task R.4 — orphan analysis, re-derived from code (2026-09-21)

Read-only audit. This file is the only thing that was edited. Nothing was committed, staged or
stashed; no tree was modified.

**This is a full re-derivation, not an edit of the 2026-09-20 version.** The producer set was
rebuilt from instrument-creating code and collector config; no number was copied from
`_emitted_series.py`, from the R.3 coverage matrix, or from the previous R.4. Where a previous
figure survives, it survives because it was re-derived and matched, and that is said explicitly.

---

## 0. Lead — what changed against the 2026-09-20 version

The old numbers are cited elsewhere in the plan set, so the delta comes first.

| Figure | 2026-09-20 | Now | Why |
|---|---|---|---|
| Metric families the estate emits | **57** | **76** | +6 api registry instruments (queue, scheduler tick, lifecycle) · +2 auto-instrumentation body-size families the old pass missed · +11 collector-derived browser metrics |
| Orphaned metric families (emitted, unconsumed) | **28** | **47** | all 19 new families above are unconsumed; the previous 28 are unchanged and were re-verified one by one |
| Orphaned browser **events** | 7 events + 1 span | **7 events + 1 span** | unchanged, re-derived against the now-committed `contracts/browser-signals.json` |
| Consumed-but-unemitted | 2 `claude_code.*` + 2 `automation-worker` surfaces; the 4 CloudWatch browser alarms were "possibly unemitted, unverified" | **same 4, plus the 4 CloudWatch browser alarms, now DEAD by `iac/alarms.tf`'s own statement** | `alarms.tf:100-137` (committed at `f85284e`) says the four metric-filter patterns name a key that "does not exist" and "cannot match under ANY reading", and says: read them "as DEAD, not as quiet". The previous version had them as unverified. The file has settled that they match nothing; it has not settled what the right pattern is (§4.5) |
| `_emitted_series.py` inventory size | 14 Series + 5 SpanSignal | **14 + 5, unchanged** | the inventory did not grow while the estate gained 19 families; the gap widened from 14-of-57 to **14-of-76** |
| Backend profiles shipped | 2 ("both shipped profiles") | **4** (oss, aws, azure, newrelic) | **the previous version was already wrong here.** `backend-azure.yaml` and `backend-newrelic.yaml` both exist at its own read HEAD `d8d2570c` (checked with `git cat-file -e`). This was not a change made tonight |
| Prometheus alert rules | 12 | **14** | **the previous version miscounted.** The four files have 6 + 2 + 4 + 2 at the current tree **and** at `d8d2570c` (`grep -c 'alert:'` on `git show`) |
| Grafana panels | 85 | **85** | re-derived by `grep -c '"gridPos"'`; identical |

**Two claims in the brief that drove this re-derivation are wrong, and the corrections matter
more than the new totals.** Both are stated in §8.

1. **R.4's producer side was not short by fifteen Document Hub names.** The 2026-09-20 §1a-bis
   already listed **all fourteen** `document_hub_*` families as orphans. It derived them from
   code, not from `_emitted_series.py`, so the conditional in R.3 §"If R.4's orphan analysis was
   run against that inventory" did not apply to it.
2. **There are fourteen Document Hub families, not fifteen.** Two independent sources agree:
   `utils-obsm/utils/observability/legacy_families.py` declares 14, and
   `copilot-mro-obsm/copilot_mro/app/services/document_hub/operations.py` defines 14 name
   constants, each with at least one call site. R.3's own prose says "fifteen" while listing
   fourteen, and says "18 families" while listing seventeen.

**The producer side really was short — by nineteen names, in places nobody was looking:** the api
gateway's six new instruments, two HTTP body-size families created by contrib under the new
semantic conventions, and eleven metrics that exist only as collector config.

**One more change matters to anyone arming aws.** The four CloudWatch browser alarms were
"possibly unemitted, unverified" in the previous version. They are now **dead by their own file's
statement** (§4.1, §4.5). Each treats missing data as OK, so each reports green forever.

**On the rule (§7):** counting every unconsumed family as an orphan turns tonight's work into
"28 → 47". Splitting unconsumed families into `on-call` (a purpose is stated; provisional until a
runbook line exists) and `orphan` (no purpose anywhere) gives **28 → 30**. Under the split, the
number of families that can be removed today is **18**.

---

## 1. Method

### 1.1 Counting rule (stated so the next re-derivation is comparable)

A **metric family** is one instrument name, counted once regardless of how many Prometheus series
it expands to and regardless of how many construction paths create it. `agent.turn.calls` is one
family whether it is built by `meter.create_counter` or by `registry.counter` — both paths exist
in the same file and both are counted once.

A **producer** is code or configuration that *creates the instrument*. An instrument created and
never recorded still counts as emitted if any call site exists; an instrument whose only call
site is a test does not.

A **consumer** is a surface that reads the family *by name to answer an operational question*:

| Tier | What it is | Counted as consumption? |
|---|---|---|
| **1 — operational** | a Grafana panel target, a Prometheus/Loki rule `expr`, a CloudWatch alarm or widget query, a runbook query an operator pastes | **yes** |
| **2 — guard** | a test, a lint inventory, a generated contract, a vocabulary validator | **no** — recorded separately |
| **3 — prose** | a name in a docstring, a CATALOGUE mapping table, a panel description saying the family is *not* charted | **no** |

Tier 2 is separated on the estate's own precedent, not on my taste:
`legacy_families.py` gives every family a `consumer` field — `None` for all 27 — and keeps
`TEST_CONSUMERS` as a distinct dict naming the 11 with test consumers. That file's own comment
says a test "is a consumer in the way that matters here". It is a different way, and §7 argues the
split should be promoted from one file's convention to the rule.

**Worked application of tier 3:** `gen_ai.client.operation.duration` appears in the estate exactly
once outside its emitter — `deployment/otel/dashboards/CATALOGUE.md:161`, inside a
dotted-name → Prometheus-name mapping table. That is not a query. It stays an orphan.

### 1.2 Search spellings actually used

The brief's warning is a real one — a literal grep for `record_exception=False` misses
`flynapse-otel`, which splats a `_WITHHOLD` dict. I assumed the same class of miss for instrument
creation and searched these spellings:

| # | Spelling | What it is for | Result |
|---|---|---|---|
| 1 | `create_counter\|create_histogram\|create_up_down_counter\|create_observable_(counter\|gauge\|up_down_counter)\|create_gauge` | raw OTel Meter API | 12 production sites, all in `copilot-mro-obsm/.../agent_shared/telemetry.py:1362-1396`, plus `flynapse-otel`'s own registry internals and 2 hits in a test docstring |
| 2 | `\b(registry\|_registry\|metric_registry\|otel_registry)\.(counter\|up_down_counter\|histogram\|observable_gauge)\s*\(` | the estate's registry facade, incl. plausible aliases | 8 production files across 5 repos (api ×4, copilot-mro, utils shim, shift-optimizer, telegram-bot) |
| 3 | `from (flynapse_otel\|utils\.observability\|\.\.?…) import .*(counter\|histogram\|observable_gauge)` | a factory imported bare and called unqualified | zero hits — no repo does this |
| 4 | `increment_counter(\|record_histogram(\|set_gauge(\|observe_summary(` | the legacy `MetricsService` shim's whole public surface (derived by listing its `def`s, not guessed) | 19 call sites in 2 repos |
| 5 | `record_document_hub_metric(` | the one domain wrapper over spelling 4 | 14 distinct constants, 17 call sites |
| 6 | `registry\.[a-z_]+\(f"` and `count\(\s*([A-Z_]+)` (multiline) | **name assembled from an f-string or a constant** | one real hit — see §1.3 |
| 7 | `prometheus_client\|from prometheus\|statsd\|StatsD\|put_metric_data\|MeterProvider\|getMeter\|createCounter\|createHistogram` | a second metrics library, or a browser-side MeterProvider | zero outside `flynapse-otel`'s own SDK bootstrap; the dashboard has no MeterProvider and `base.yaml:217` says so |
| 8 | `connectors:`, `signaltometrics`, `spanmetrics`, `metrics_generator` | families minted by the collector or by Tempo, which no Python grep can see | 11 + the Tempo generator |
| 9 | `metric_transformation\|metric_name\|namespace` in `iac/alarms.tf` | families minted by CloudWatch log-metric filters | 6 `Flynapse/*` families |
| 10 | `View(\|views=\|drop_aggregation\|DropAggregation` | an SDK view that would suppress a created instrument | zero — nothing created is dropped |
| 11 | `api/v1/query\|query_range\|get_metric_data\|GetMetricStatistics` | code that queries a family by name | tests only; no production reader |

**Spelling 6 found the trap the brief predicted.** `telegram-bot/telegram_bot/telemetry.py:896`:

```python
def counted(name: str, fields: Mapping[str, object]) -> None:
    handle = _COUNTERS.get(name)
    if handle is None:
        handle = _COUNTERS[name] = registry.counter(
            f"telegram.{name}", "1", f"`{name}` events, as the bot counts them"
        )
```

A grep for `registry.counter("telegram` finds six of telegram-bot's ten families and misses the
mechanism entirely. The family name is `f"telegram.{name}"`, where `name` is the first argument of
`observability.count()`. I censused that argument with a multiline regex over every `count(` call
site: it is always one of four module constants (`TURNS`, `UPLOADS`, `PROVISIONINGS`, `REFUSALS`,
declared at `observability.py:76-79`). **So no undeclared telegram family exists today** — but any
future `count("X")` mints `telegram.X` as a live metric with no code review of the name, and
nothing anywhere would notice.

The legacy shim has the same shape: `metrics.py:267-272` auto-registers any name not in
`legacy_families.BY_NAME` with unit `"1"` and the description `"legacy auto-registered counter"`.
I cross-checked every call site's name against the declared 27 — all match, so there is no
undeclared legacy family today either.

### 1.3 The false-positive the brief warned about, checked

`ad_notification_dispatcher.py` has plain dataclass fields named `*_created`. It matched none of
spellings 1-5 (they all require a call), and `copilot-mro`'s only metric instruments are the 13 in
`telemetry.py` and the shim emissions. No false positive reached the census.

### 1.4 Trees read — every repo by absolute path, never by name

Resolved by path because a pre-merge sibling sits beside every merged worktree
(`/home/aditya/Code/dashboard` is the **pre-merge** checkout; `/home/aditya/Code/dashboard-obsm` is
the merged one, and the 2026-09-20 coverage matrix measured the wrong one).

| Repo | Absolute path | Branch | HEAD at start (2026-09-20 23:58) | HEAD at end (2026-09-21 00:09) | Moved? |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `b6471c8`, dirty 19 | **`1b1d088`, dirty 0** | **yes — a commit landed mid-audit** |
| core | `/home/aditya/Code/core-obsm` | `obs-merge` | `af6adce`, dirty 3 | **`0ea20d3`, dirty 0** (00:15) | **yes. The tree grew to dirty 7, then a commit landed** (backfill subtransaction work, analytics-only) |
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `fffa470`, dirty 13 | `fffa470`, **dirty 17** (00:15) | working tree grew twice |
| copilot-mro | `/home/aditya/Code/copilot-mro-obsm` | `obs-merge` | `6058e662`, dirty 64 | `6058e662`, **dirty 65** | working tree grew |
| dashboard | `/home/aditya/Code/dashboard-obsm` | `obs-merge` | `004a809`, dirty 0 | `004a809`, dirty 0 | no |
| flynapse-otel | `/home/aditya/Code/flynapse-otel` | `main` | `f6bd5c0`, dirty 6 | **`af40bbe`, dirty 0** | **yes — a commit landed mid-audit** |
| iac | `/home/aditya/Code/iac` | `obs-merge` | `f85284e`, dirty 7 | `f85284e`, dirty 7 | no (all 7 are `__pycache__` + one POC shell script) |
| shift-optimizer | `/home/aditya/Code/shift-optimizer` | `main` | `1ba897e`, dirty 0 | `1ba897e`, dirty 0 | no |
| telegram-bot | `/home/aditya/Code/telegram-bot` | `main` | `3102fcc`, dirty 0 | `3102fcc`, dirty 0 | no |

**Three trees committed while I was reading them.** I re-ran the producer census against each new
HEAD:

- `api-obsm` at `1b1d088` still declares exactly the seven instruments listed in §2.2.
- `flynapse-otel`'s registry at `af40bbe` still exposes exactly `counter`, `up_down_counter`,
  `histogram` and `observable_gauge`.
- `core-obsm` at `0ea20d3` still has zero instrument sites and still has three `traced_sweep(`
  decorations.

None of the three commits changed a family name. `utils-obsm` was still growing at the last read
(dirty 17). I checked its diff for new literal-named instruments twice and found none either time.
Every count in this document is as of the **end** state.

**I read working trees, not `git log`.** That is load-bearing here: at `copilot-mro-obsm`
`6058e662` the connector does not exist. `git diff` shows `deployment/otel/base.yaml` **+183
lines** and `agent_shared/telemetry.py` **+36** uncommitted. So **eleven of the 47 orphans and one
of the twelve agent families exist only in an uncommitted working tree right now.** A reader
working from `HEAD` will not find them.

**One library read, declared as such.** The auto-instrumentation families in §2.6 come from
reading the installed contrib package at
`/home/aditya/Code/api/.venv/lib/python3.11/site-packages/opentelemetry/instrumentation/`. That
venv belongs to the **pre-merge** `api` sibling — I used it because `copilot-mro-obsm/.venv` has no
`opentelemetry` installed and `api-obsm` has no venv at all. It is legitimate only because its
`instrumentation/version.py` reads `0.65b0`, which is exactly the `CONTRIB_VERSION` pin declared in
`flynapse-otel/flynapse_otel/__init__.py`. This is a read of a pinned third-party library, not of a
repo.

---

## 2. The producer set — 76 metric families, by construction class

### 2.1 copilot-mro agent runtime — 12 families

`copilot-mro-obsm/copilot_mro/app/services/agent_shared/telemetry.py`. **Two construction paths,
same twelve names:** `RuntimeTelemetry.__init__` (`:1362-1396`, raw `meter.create_*`) and
`RuntimeTelemetry.from_current_provider` (`:1406-1462`, `registry.*`). Counted once each.

`agent.turn.calls` · `agent.turn.duration_seconds` · `gen_ai.client.operation.duration` ·
`gen_ai.client.token.usage` · `agent.model.calls` · `agent.model.cost_usd` ·
`agent.model.unpriced_calls` · `agent.tool.calls` · `agent.tool.attempts` ·
`agent.subagent.calls` · `agent.subagent.duration_seconds` · `agent.ledger.write_failures`

`agent.ledger.write_failures` is **still uncommitted** (it appears as `+` in `git diff` against
`6058e662`, 36 lines across both constructors). The previous R.4 excluded it and the two subagent
families as "in-flight"; the subagent pair has since committed, the ledger counter has not.

### 2.2 api gateway registry instruments — 7 families

| Family | File:line | Kind |
|---|---|---|
| `auth.rejections` | `api-obsm/flynapse_api/middleware/telemetry.py:34` | counter |
| `automation.tick.duration` | `api-obsm/flynapse_api/telemetry/scheduler_telemetry.py:30` | histogram |
| `automation.queue.depth` | `api-obsm/flynapse_api/telemetry/queue_telemetry.py:150` | histogram |
| `automation.queue.wait` | `queue_telemetry.py:162` | histogram |
| `automation.queue.claims` | `queue_telemetry.py:170` | counter |
| `api.lifecycle.duration` | `api-obsm/flynapse_api/telemetry/lifecycle_span.py:60` | histogram |
| `api.lifecycle.step.duration` | `lifecycle_span.py:68` | histogram |

**Six of these seven are new since the previous R.4**, which knew only `auth.rejections`.

### 2.3 shift-optimizer — 4 families
`optimizer.runs` · `optimizer.run.duration` · `optimizer.solve.duration` · `optimizer.runs.active`
(`shift-optimizer/shift_optimizer/app/services/run_telemetry.py:51-66`).

### 2.4 telegram-bot — 10 families
`telegram.updates` · `.updates.active` · `.turn.duration` · `.turn.phase.duration` · `.turn.cost` ·
`.jobs` · `.turns` · `.uploads` · `.provisionings` · `.refusals`
(`telegram-bot/telegram_bot/telemetry.py:856-891`, plus the f-string path at `:900`, §1.2).

### 2.5 Legacy `MetricsService` shim — 27 families, all declared

`utils-obsm/utils/observability/legacy_families.py` declares exactly 27 `Family(` entries, which is
also the number the previous R.4 derived independently from call sites. Emission still routes
through `registry`, so these are real OTel instruments, not a parallel system.

- **`utils/llm.py` (10):** `llm_requests_total`, `llm_request_duration`, `llm_tokens_total`,
  `llm_tokens_per_request`, `embedding_requests_total`, `embedding_tokens_total`,
  `embedding_cost_usd`, `embedding_request_duration`, `embedding_cache_hits_total`,
  `embedding_cache_tokens_avoided_total`
- **copilot-mro, non-Document-Hub (3):** `chat_block_save_failures_total`
  (`chat_management.py:379`), `memory_get_latency_ms` (`memory_db.py:880`),
  `memory_search_latency_ms` (`memory_index.py:636`)
- **copilot-mro Document Hub (14, not 15):** `document_hub_upload_total`, `_retry_total`,
  `_delete_total`, `_share_total`, `_processing_total`, `_processing_duration_seconds`,
  `_parser_failure_total`, `_index_upsert_total`, `_cleanup_total`, `_cleanup_vectors`,
  `_cleanup_objects`, `_notification_total`, `_attempt_vector_cleanup_total`,
  `_query_embedding_fallback_total` — constants at `document_hub/operations.py:20-41`, every one
  with at least one `record_document_hub_metric` call site outside that file

`legacy_families.py` is an improvement the previous R.4 could not have seen: it replaces
auto-registration (unit `"1"`, deny-list only) with declared kinds, units, buckets and a **bounded
attribute set**, which is the fix for the `chat_block_save_failures_total` cardinality exposure
§3.2 of the previous version called the worst in the estate. It also renames some exported series
by giving them honest units, and records that in each family's `unit_note`.

### 2.6 Auto-instrumentation — 5 families

One `OpenTelemetryMiddleware` exists in the whole estate, at the gateway
(`api-obsm/flynapse_api/telemetry/http_server.py`). `OTEL_SEMCONV_STABILITY_OPT_IN` is defaulted to
`http` and **latched** at `flynapse-otel/flynapse_otel/bootstrap.py:187`, so only the new-semconv
branch of the contrib constructor runs.

| Family | Created at | In the previous R.4? |
|---|---|---|
| `http.server.request.duration` | contrib `asgi/__init__.py:632` under `_report_new` | yes |
| `http.server.active_requests` | `asgi/__init__.py:661`, **created unconditionally** — not gated on the stability mode | yes |
| **`http.server.request.body.size`** | `asgi/__init__.py:659` under `_report_new`, recorded at `:872` | **no — missed** |
| **`http.server.response.body.size`** | `asgi/__init__.py:647` under `_report_new`, recorded at `:852` | **no — missed** |
| `http.client.request.duration` | httpx instrumentor under `_report_new` (`httpx/__init__.py:793` and three sibling sites); requests and urllib3 use the same semconv constant — I did not read them separately | yes |

The two body-size families are named in
`opentelemetry/semconv/_incubating/metrics/http_metrics.py:128,161`. They are not hypothetical:
`asgi/__init__.py` calls `.record()` on both, and the gateway's `_ResponseEndOtelMiddleware` wraps
only the duration histograms and the active-requests counter — it leaves the body-size instruments
untouched. **This is the class of miss the brief predicted, found in a different place than
expected: not a repo, a library.** A producer census that reads only first-party code misses them.

### 2.7 Collector-derived browser metrics — 11 families

`connectors::signaltometrics/browser` in `copilot-mro-obsm/deployment/otel/base.yaml:248-395`
(**uncommitted**). Five built from `browser.chat.turn` span attributes, six from `browser.*` log
record attributes:

| # | Family | Derived from | Value |
|---|---|---|---|
| 1 | `browser.chat.turn.duration` | span `browser.chat.turn` | `total_ms / 1000` |
| 2 | `browser.chat.turn.time_to_init` | same | `ttf_init_ms / 1000` |
| 3 | `browser.chat.turn.time_to_first_token` | same | `ttf_token_ms / 1000` |
| 4 | `browser.chat.turn.attachment_upload.duration` | same | `attachment_upload_ms / 1000` |
| 5 | `browser.chat.turn.steps` | same | `step_count` |
| 6 | `browser.web_vital.value` | log `browser.web_vital` | `value`, exponential histogram |
| 7 | `browser.app.boot.ttfb` | log `browser.app.boot` | `ttfb_ms / 1000` |
| 8 | `browser.app.boot.dom_interactive` | same | `dom_interactive_ms / 1000` |
| 9 | `browser.app.boot.load_complete` | same | `load_complete_ms / 1000` |
| 10 | `browser.long_running.observed_wait` | logs `browser.automation.run_settled` **or** `browser.discovery.job_settled` | `observed_wait_ms / 1000` |
| 11 | `browser.long_running.polls` | same two events | `poll_count` |

Wired as an exporter on `traces/browser` and `logs/browser` and as the sole receiver of
`metrics/browser` in **all four** overlays — `backend-oss.yaml:85,97,107`,
`backend-aws.yaml:119,131,141`, `backend-azure.yaml:80,92,102`,
`backend-newrelic.yaml:66,78,88`. **No repo's code creates any of these.** A census that reads only
Python scores them zero.

### 2.8 Not counted in the 76, but named so the boundary is explicit

- **Tempo metrics-generator, oss only** — `traces_spanmetrics_calls_total`,
  `traces_spanmetrics_latency_*`, `traces_service_graph_*`, from
  `deployment/observability-local/tempo.yaml:76-77` (`processors: [service-graphs, span-metrics]`).
  Emitted by Tempo, not by the estate; consumed by 9 panels. **No such family exists in aws, azure
  or newrelic** — there is no Tempo there.
- **CloudWatch log-metric filters, aws only — 6 `Flynapse/*` families** *declared* by
  `iac/alarms.tf`: `Flynapse/Browser` → `BrowserErrors`, `WebVitalLcp`, `WebVitalInp`,
  `WebVitalCls`; `Flynapse/Automation` → `AutomationWorkerErrorRecords`,
  `AutomationWorkerLogRecords`. **Declared is not the same as produced.** The two Automation filters
  are gated off by `var.automation_worker_deployed = false`, so they are neither created nor
  consumed. The four Browser filters are created, and by `alarms.tf:123`'s own statement their
  patterns "cannot match under ANY reading", so they never produce a datapoint. That puts them in
  §4.1 as consumed-but-unemitted, not in the producer set.
- **Platform self-telemetry** — `otelcol_*`, `prometheus_*`, `loki_*`, `tempo_*`,
  `alertmanager_*`. Emitted by the infrastructure, scraped by the five jobs in
  `prometheus.yml:24-48`, consumed by fn-platform-health and three platform rules.

---

## 3. Emitted-but-unconsumed — 47 metric families

Consumer surfaces searched, in full: 8 Grafana boards (**85 panels**, re-derived by
`grep -c '"gridPos"'`: agent-turn-explorer 3 · dependencies 5 · frontend 19 · llm-agents 12 ·
platform-health 9 · service-overview 7 · shift-optimizer 12 · telegram-bot 18) · 4 Prometheus rule
files (**14 alerts**) · 1 Loki rule file (5 alerts) · `iac/alarms.tf` (7 `aws_cloudwatch_*`
resources over gated maps) · 8 CloudWatch dashboard templates · 4 runbooks ·
`deployment/otel/dashboards/CATALOGUE.md`.

### 3.1 New this pass — 19 families (the whole delta)

| # | Family | Class | Consumers found |
|---|---|---|---|
| 1 | `automation.tick.duration` | api registry | **none** — not in any board, rule, alarm, widget, runbook or CATALOGUE |
| 2 | `automation.queue.depth` | api registry | **none** |
| 3 | `automation.queue.wait` | api registry | **none** |
| 4 | `automation.queue.claims` | api registry | **none** |
| 5 | `api.lifecycle.duration` | api registry | **none** |
| 6 | `api.lifecycle.step.duration` | api registry | **none** |
| 7 | `http.server.request.body.size` | auto-instr | **none** |
| 8 | `http.server.response.body.size` | auto-instr | **none** |
| 9-13 | the five `browser.chat.turn.*` derived metrics | collector | **none** — `browser.chat.turn` is named once in `CATALOGUE.md:365`, as a span, about its attributes |
| 14 | `browser.web_vital.value` | collector | **none** — every web-vital consumer reads the **log** (LogQL `unwrap` in oss, CloudWatch metric filters in aws), not this metric |
| 15-17 | `browser.app.boot.{ttfb,dom_interactive,load_complete}` | collector | **none** — fn-frontend p19 reads the **log** (`unwrap load_complete_ms`), not the derived family |
| 18-19 | `browser.long_running.{observed_wait,polls}` | collector | **none** — the two settle **events** are charted; these derived metrics are not |

Tier-2 (guard) consumers exist for #9-19 and only for those:
`copilot-mro-obsm/tests/integration/otel/test_browser_derived_metrics.py` checks all eleven against
`base.yaml`, the browser allow-list, all four overlays, and
`dashboard-obsm/contracts/browser-signals.json`. Families #1-8 have unit tests on their recorders
(`api-obsm/tests/unit/telemetry/`, `tests/integration/otel/test_one_shot_queue_signals.py`) but no
inventory or vocabulary guard of any kind.

**Rows 14-17 are the most interesting shape in the whole document, and §7 turns on them.** The
*signal* is consumed; the *derived family built from the same signal* is not. `browser.app.boot`
and `browser.web_vital` are charted and alerted on — as logs. Counting their derived metric
siblings as orphans is arithmetically correct and operationally misleading.

### 3.2 Carried forward, each re-derived — 28 families

**`gen_ai.client.operation.duration`** (1). Re-derived: zero panel targets, zero rule exprs, zero
alarm or widget selectors, zero runbook queries. Its only estate mention outside its emitter is the
name-mapping table at `CATALOGUE.md:161` — tier 3. **Still an orphan.** Unchanged except the line
number (was `:151`).

**The 27 legacy families** (§2.5). Re-derived by grepping all consumer surfaces for
`llm_*`, `embedding_*`, `memory_*_latency_ms`, `chat_block_save_failures*` and `document_hub_*`:
**zero hits across every surface.** The only `document_hub_*` strings anywhere in the consumer set
are `document_hub_documents` — a Postgres table — and `document_hub_process`, a span. Their own
declaration file agrees: `consumer` is `None` for all 27.

**11 of the 27 have tier-2 consumers**, listed by name in `legacy_families.TEST_CONSUMERS`:
the four `llm_*`, five of the six `embedding_*`, `chat_block_save_failures_total`, and
`document_hub_query_embedding_fallback_total`. Renaming or retiring any of those eleven turns a
suite red. **The other sixteen can be deleted today with nothing anywhere noticing** — that, not
the orphan count, is the actionable number in this section.

### 3.3 Browser log events — 7 events + 1 span, unchanged

`dashboard-obsm/lib/telemetry/events.ts:29-51` declares 20 event names plus the `browser.chat.turn`
span at `:55`. Producers re-derived from `contracts/browser-signals.json`, which is
**generated, AST-derived from the emitter** by `scripts/generate-browser-signal-contract.mts` and
checked by `tests/unit/telemetry/browser-signal-contract.test.ts` — 21 of 21 `wired`, each with a
`producers` list. I treated that as a derivation from code, not as a hand list, and spot-checked
three orphans' producer lists.

Consumption re-derived by grepping all consumer surfaces for `browser.*`:

| Orphan | Note |
|---|---|
| `browser.auth.login` | mentioned once, at `frontend.json:228`, in a panel description that says it is **not** charted — tier 3, not consumption |
| `browser.pdf.render` | zero mentions |
| `browser.upload.started` | zero mentions |
| `browser.automation.run_triggered` | zero — only the `run_settled` sibling is charted |
| `browser.discovery.job_started` | zero — only `job_settled` is charted |
| `browser.chat.feedback_submitted` | zero mentions |
| `browser.log` | zero mentions — log-search-only |
| `browser.chat.turn` (span) | zero panel, zero rule. It now *also* feeds five derived metrics that nothing reads, so the span is upstream of orphans rather than being one alone |

The other 13 events are consumed: `web_vital`, `error`, `telemetry.dropped`, `feature.mutation`,
`settings.mutation`, `route.change`, `optimizer.run_triggered`, `export.requested`,
`discovery.job_settled`, `automation.run_settled`, `auth.flow`, `ad_review.disposition_set`, and
`app.boot` (fn-frontend p19, `unwrap load_complete_ms`).

### 3.4 Spans

No span is an orphan merely for lacking a panel — INTERNAL work spans are trace-search-reachable by
design, and in oss every span also mints `traces_spanmetrics_*`. Two additions since the previous
version:

- **`core`'s three sweep spans** — `automation.sweep.reap_stale_runs`,
  `automation.sweep.recover_stale_one_shot_runs`, `automation.sweep.expire_retry_stamps`, from
  `core-obsm/core/resources/automations/sweep_span.py:97` decorating `automation_store.py:1296`,
  `:2835`, `:3022`. No consumer names them; that is the expected shape.
- **`api.lifecycle.*` spans** alongside the two lifecycle histograms.

**Correction to the brief:** it says "core's three sweep spans **and their instruments**". `core`
creates **no metric instrument at all** — spellings 1, 2 and 4 return zero hits across
`core-obsm/core`. `automation.sweep.rows` is a **span attribute** set by `span.set_attribute`, not
a histogram. The sweep work added three spans and zero families.

---

## 4. Consumed-but-unemitted

### 4.1 Genuinely dead — re-derived, unchanged

| Consumer | Signal | Verdict |
|---|---|---|
| fn-llm-agents p10 targets A and B; `iac/dashboards/llm-agents.json.tftpl` markdown | `claude_code_token_usage_total` / `claude_code.token.usage`, `claude_code_cost_usage_total` / `claude_code.cost.usage` | **SUPERSEDED 2026-09-22 by M-CLI-TELEMETRY (owner B9): the CLI now emits LOGS only, metrics off; both `claude_code_*` targets are REMOVED from the board and CATALOGUE (copilot-mro `obs-merge-cli` `cb5d309d`); iac's template still names them (owed).** Was: **DEAD, correctly declared** `dark` in `_emitted_series.py` and CATALOGUE. Nothing sets `CLAUDE_CODE_ENABLE_TELEMETRY`; the collector's `transform/genai_aliases` (`base.yaml:101`) would relabel these families if they ever arrived, and relabels nothing today |
| `flynapse-platform-alerts.yml:61` `AutomationWorkerSilent` — `absent(target_info{job="flynapse/automation-worker"})` | `target_info` for `service.name=automation-worker` | **PERMANENTLY FIRING in any oss deployment.** Re-verified: `api-obsm/flynapse_api/automations/worker.py:117` sets that service name, and neither `deployment/docker-compose.yml` (12 services) nor `observability-local/observe-docker-compose.yml` (6 services) runs it. The AWS twin is gated by `var.automation_worker_deployed=false` (`alarms.tf:195`) and is not created; **the oss twin has no gate** |
| fn-platform-health p6 "Automation worker heartbeat" | same | reads "worker absent = 1" forever |
| `rules/loki/flynapse/browser-alerts.yml:100` `AutomationRunErrors` — `{service_name="automation-worker"}` | that log stream | **NEVER FIRES** — the inverse failure. Its own annotation calls it a transitional proxy that "arms as soon as worker logs flow"; nothing makes them flow |
| **`iac/alarms.tf` — the four browser alarms** (`BrowserErrorRateHigh`, `WebVitalLcpP75Poor`, `WebVitalInpP75Poor`, `WebVitalClsP75Poor`), over the metric filters at `:519`, `:550`, `:558`, `:566` | `Flynapse/Browser` `BrowserErrors`, `WebVitalLcp`, `WebVitalInp`, `WebVitalCls`, minted from `$.attributes.event_name` | **DEAD, and the file says so.** `alarms.tf:123`: "`$.attributes.event_name` names a key that does not exist. It cannot match under ANY reading." `:135`: "READ THE FOUR BROWSER ALARMS AS DEAD, NOT AS QUIET". Each has `treat_missing_data = "notBreaching"`, so each one reports OK forever. **The emitter is fine**: `browser.error` and `browser.web_vital` are both produced and both work in oss. What is dead is the aws read path. `:127-130` adds that `$.resource.attributes.service.name` has the same defect, which makes it six dead patterns: these four, plus the two worker patterns, which are gated off anyway |

### 4.2 Stale assertions in `iac` — now resolved

The previous version recorded two false statements in `iac` at `2d493c8`: the `LedgerWriteFailures`
alarm description claiming no ledger instrument exists anywhere, and the llm-agents markdown
claiming nothing calls `record_subagent`. At `f85284e` neither string survives: `alarms.tf` names
`{"agent.ledger.write_failures"}` as a live selector, and `llm-agents.json.tftpl` names
`agent.subagent.calls` and `agent.subagent.duration_seconds`. **Both stale assertions are gone.**

### 4.3 Every dotted selector in `iac`, re-checked against emitters

29 distinct dotted names across `alarms.tf` and `dashboards/*.tftpl`: 28 in the templates, plus
`agent.ledger.write_failures`, which only `alarms.tf` names. All 29 are names the estate emits,
**except** the two `claude_code.*`, which are declared dead. So the metric-name conversion is
correct. The dead alarms in §4.1 fail at the **log-attribute** level, not on a metric name.

Three things `iac` does **not** name, which is where the asymmetry now sits:
`agent.model.calls` and `agent.tool.calls` are charted in oss and have **no AWS consumer**
(unchanged); and **none of the 19 new families in §3.1 appears anywhere in `iac`.**

### 4.4 `ApiHighErrorRate` — carried, not re-derived

`iac/alarms.tf` still writes both sides of a ratio as bare histogram selectors with no
`histogram_count`, no `le="+Inf"` and no `_count` suffix. **I am carrying the previous version's
verdict — non-functional under both candidate storage shapes — rather than re-deriving it**,
because settling it needs a fact about what CloudWatch stores for an OTLP histogram that no file in
the estate contains. The estate's own note at `alarms.tf:107-114` says the same. The oss twin
(`flynapse-api-alerts.yml:11`) names `http_server_request_duration_seconds_count` explicitly and is
correct. **Treat this as an open probe, not as a settled finding.**

### 4.5 The CloudWatch attribute-path spelling — fixed on the widgets, deliberately left broken on the alarms

The previous version flagged 4 alarms and 10 widgets that select `attributes.event_name`
(underscore) while the browser emits `event.name` (dotted). **The two halves have separated.**

- **Widgets — fixed.** `iac/dashboards/frontend.json.tftpl` now selects `attributes.event.name`.
  The one `attributes.event_name` left in that file is inside its markdown, explaining the old
  spelling. `iac/scripts/validate_metric_vocabulary.py` check 7 pins the dotted form, through
  `DOTTED_ATTRIBUTE_KEYS` and `SANITISED_PROVENANCE`.
- **Alarms — not fixed, on purpose.** The four live patterns at `alarms.tf:519,550,558,566` still
  read `$.attributes.event_name`. `alarms.tf:116-134` says why. Metric filters use a different
  grammar from Logs Insights: in a metric filter the period is the path separator, so
  `$.attributes.event.name` would be wrong as well. The correct form is bracket notation, and AWS
  documents two possible spellings of it without saying which one applies. The file declines to
  guess, and it keeps a spelling that it calls "at least HONESTLY dead". §4.1 lists these alarms as
  dead.

**My first draft of this section said the defect was closed.** I wrote that after reading only the
widget markdown. The alarm patterns proved it wrong when I checked the claim against `alarms.tf`.
I note the mistake here because it has the same shape as the one this document is about: I read
the fixed half and assumed the other half was fixed too.

**The experiment that settles it is already written:** `iac/scripts/b1b_metric_filter_probe.sh
[region]`. It needs only `logs:TestMetricFilter`, it runs every candidate selector against both
possible storage shapes, and it prints MATCH / NO MATCH / REJECTED for each. `alarms.tf:138-150`
states what it predicts before it runs.

---

## 5. What I could not settle

| # | Question | Why code reading cannot answer it, and the experiment that would |
|---|---|---|
| 1 | **Does any of this arrive?** Every "consumed" verdict proves a *reference*, never a *retrieval*. `_emitted_series.py` says so itself: the agent half is `wired`, not `live`. | Run `test_oss_profile_smoke.py::…inventory…` against a booted oss stack — it already pushes one synthetic datapoint per inventoried instrument and asserts Prometheus serves the predicted names. It covers 12 of 76 families. Extending it to the other 64 is the experiment |
| 2 | **`ApiHighErrorRate`'s real behaviour.** §4.4. | One `aws cloudwatch get-metric-data` PromQL call against a deployed environment, asking for `histogram_count(rate({"http.server.request.duration"}[5m]))` and for the bare form; whichever errors tells you the stored shape |
| 3 | **`traces_spanmetrics_*` family names** against the `grafana/tempo:3.0.3` pin. Nine panels depend on the spelling and no file in the estate proves it. | Boot the oss stack, send one span, `GET /api/v1/label/__name__/values` on Prometheus, grep for `traces_` |
| 4 | **`otelcol_*` spelling on the aws path.** They reach CloudWatch through the periodic OTLP reader in `backend-aws.yaml`, and the aws runbook records a 2026-09-15 capture-exporter observation for `otelcol_process_uptime` **only**. The other seven names on fn-platform-health are unverified there | Repeat that capture-exporter run and list every `otelcol_*` name it emits |
| 5 | **Whether the 11 derived browser metrics are produced at all.** The connector is uncommitted config; no probe has seen `browser_chat_turn_duration_seconds_bucket` in any backend | Boot oss, drive one chat turn in a real browser, query Prometheus for `browser_chat_turn_duration_seconds_count` |
| 6 | **The exported Prometheus name of the 27 legacy families after `legacy_families.py`.** Declaring honest units *renames* the exported series (`embedding_cost_usd` is now `{USD}`, `document_hub_processing_duration_seconds` is now `s`). The file's `unit_note` records the disagreements, but no probe has confirmed what the exporter actually emits | Push one synthetic datapoint per declared family through the pinned collector and read the served names back — the §1 experiment, applied to this class |
| 7 | **Whether `http.server.{request,response}.body.size` survive to a backend.** I proved the instruments are created and recorded. I did not prove the collector exports them (nothing filters metrics by name, so they should, but "should" is not a measurement) | Same probe as #5, asking for `http_server_request_body_size_bytes_count` |
| 8 | **What the four CloudWatch browser metric-filter patterns should say** (§4.5). The file has settled that the current patterns match nothing. It has not settled what the right pattern is | `iac/scripts/b1b_metric_filter_probe.sh [region]` — read-only, needs only `logs:TestMetricFilter`, and states its predicted result before it runs |

**One thing I deliberately declined to score.** `copilot-mro-obsm` moved from dirty 64 to dirty 65
during the audit and `deployment/otel/base.yaml`, `CATALOGUE.md`, all three edited boards, two rule
files and four runbooks are in that set. I did **not** attempt a per-panel or per-rule consumption
verdict at panel granularity for those files, because the panel bodies are being rewritten under
me. Every verdict in §3 and §4 is at **family granularity**, where a name either appears in the
file or does not — a property that survived every re-read I did. Where I needed a count that could
move (panels, alerts), I re-derived it mechanically and said which command produced it.

---

## 6. The inventory gap

`copilot-mro-obsm/tests/integration/otel/_emitted_series.py` holds **14 `Series(` and 5
`SpanSignal(`** — identical to the previous version's count, re-derived by `grep -c`. Its
`FAMILY_TOKEN` regex at `:218` is also unchanged:

```
\b(?:agent|gen_ai|claude_code)[._][A-Za-z0-9_.]*|\b(?:invoke_agent|execute_tool)\b
```

So the inventory can still resolve or contradict only `agent.*`, `gen_ai.*`, `claude_code.*` and
two span tokens. **Nothing named `automation_*`, `api_lifecycle_*`, `browser_*`, `http_*`,
`telegram_*`, `optimizer_*`, `otelcol_*`, `traces_spanmetrics_*`, `document_hub_*`, `llm_*` or
`embedding_*` can ever be flagged by it.** The gap it leaves went from 43 families (57 − 14) to
**62 (76 − 14)** in one night.

Three partial inventories now exist and none of them meets the others:

| Inventory | Covers | Blind to |
|---|---|---|
| `_emitted_series.py` (copilot-mro) | 12 agent families + 2 dark + 5 spans | the other 62 families |
| `legacy_families.py` (utils) | the 27 legacy families, with declared bounds and a `consumer` field | everything modern |
| `contracts/browser-signals.json` (dashboard, generated) | 20 browser events + 1 span, with producers | all metrics, including the 11 derived from its own signals |

`iac/scripts/validate_metric_vocabulary.py` is **not** a fourth inventory: its own docstring
(`:1488`, `:1519`) says `{"telegram.turnz"}` and `{"agent.turn.callz"}` pass every check it makes.
It pins dialect, form, AWS namespaces and deployment gating — not existence. It holds two emitter
names (`UNIT_SUFFIXED_INSTRUMENTS` at `:221`) and that is the whole of its name knowledge.

---

## 7. The rule — and why it should be split

**The question.** Tonight's collector work created 11 emitted-but-unconsumed families, so by R.4's
own rule tonight's work is a 39% regression in the orphan count. Is that rule still right?

**No. It is measuring the wrong thing, and the evidence is in this document.**

Take rows 14-17 of §3.1. `browser.web_vital.value` counts as "unconsumed". The web-vital log it is
derived from feeds **two fn-frontend panels and three Loki alert rules**. Before tonight, a p75
web-vital query worked only where Loki runs. Now there is a metric carrying the same reading in all
four profiles. **In aws that matters more than a new capability usually does:** the three
CloudWatch web-vital alarms that were supposed to cover aws are dead (§4.1). Today
`browser.web_vital.value` is the only aws path to web vitals that is not known to be broken. A rule
that counts this family and the three `app.boot.*` families as four new orphans is not describing
a defect. It is describing a portability gain in the language of debt.

**The failure mode is not hypothetical.** A metric that counts every new capability as a regression
gets ignored, and then the rule stops catching the thing it exists to catch — the sixteen legacy
families in §3.2 that nothing reads, no test asserts on, and that can be deleted today.

### 7.1 The split

Replace one verdict with two independent axes. Both are derivable from what is already in this
document; neither needs new tooling.

**Axis A — reachability.** Can an operator get at this family *at all*, during an incident, without
shipping code?

| Value | Meaning |
|---|---|
| `reachable` | exists as a series in at least one shipped profile's backend; an operator can query it ad hoc |
| `unreachable` | not exported on any shipped profile's path, or gated off |

**Axis B — intent.** Why does it exist?

| Value | Meaning | Action when unconsumed |
|---|---|---|
| `charted` | at least one tier-1 consumer names it | none |
| `on-call` | deliberately unconsumed: it exists so someone can query it during an incident. Requires a named owner and a runbook sentence saying which question it answers | none — this is the intended terminal state |
| `orphan` | no tier-1 consumer, no runbook sentence, and no one has claimed it | **this is the only number worth reporting as debt** |

An `on-call` claim is cheap to make and cheap to audit: one line in
`docs/runbooks/observability/`. That is the whole enforcement mechanism, and it is enough, because
the claim is what makes the difference auditable — a family with no consumer *and* no runbook line
is unowned by construction.

### 7.2 What the 47 become

| Bucket | Count | Families |
|---|---|---|
| `on-call`, **provisional** (a purpose is stated in code; the runbook line is not written yet) | **17** | the 11 derived browser metrics (`base.yaml:229-230` says `browser.chat.turn.duration` is "deliberately derived anyway so the turn's duration is one series with one name in every profile") + the 6 api queue/tick/lifecycle families (each docstring names the question the family answers — for example `queue_telemetry.py:168-169` on `automation.queue.claims`: "A rising `lost` rate is two schedulers reading one work list, which today is visible nowhere") |
| `orphan` (unowned debt) | **30** | `gen_ai.client.operation.duration` + the 27 legacy families + **the 2 HTTP body-size families**. The body-size pair is a side-effect of the contrib library, and nobody in the estate ever gave either family a purpose |
| of which **safe to remove today** | **18** | 16 legacy families (the 27, minus the 11 that have `TEST_CONSUMERS` entries) + the 2 body-size families. The body-size pair should be dropped with an SDK `View`; there is no call site to delete |

**All 17 new families that have a stated purpose land in `on-call`. The 2 that have none land in
`orphan`.** Under this rule the orphan count moves **28 → 30**, not 28 → 47. That describes the
night's work more accurately, and it is not a whitewash, for two reasons:

- **The `on-call` label is provisional for all 17.** By the rule's own terms, a family with no
  runbook line is `orphan`. Writing the 17 runbook sentences in `docs/runbooks/observability/` is
  what makes the label real. I have counted them as `on-call` and flagged that here.
- **The rule still charged tonight's work with 2 new orphans.** It separates stated intent from
  accident. It does not wave every new family through.

### 7.3 One thing the split does not fix

`on-call` is a claim about intent, and this document proves references, never retrievals (§5 #1).
A family can be `reachable` on paper and absent in practice — the 11 derived metrics are the live
example, since no probe has seen one. **`on-call` should not be grantable to a family in the
`wired` state.** The honest three-state chain is `wired` → `live` → `on-call`, and the estate
already has the first two words for exactly this reason.

---

## 8. Corrections to the brief and to R.3

| # | Claim | Verdict |
|---|---|---|
| 1 | "R.4's producer inventory is short by at least fifteen names" | **False as stated.** The 2026-09-20 §1a-bis listed all fourteen `document_hub_*` families, derived from code. The producer side *was* short — by **nineteen** names (6 api + 2 body-size + 11 derived), none of them Document Hub |
| 2 | "the estate carries 15 Document Hub families" (R.3 §"copilot-mro (legacy shim)") | **Fourteen.** `legacy_families.py` declares 14; `operations.py` defines 14 constants. R.3's own sentence lists fourteen while saying fifteen, and says "18 families" while listing seventeen |
| 3 | R.3: "if R.4 was run against that inventory it under-counted by fifteen" | **The premise did not hold.** R.4 was not run against `_emitted_series.py`. This is the exact failure the brief warns about — a derived document inheriting an unverified number — occurring *in the brief itself*, one generation on |
| 4 | "core's three sweep spans **and their instruments**" | **Half true.** The three spans exist. `core` creates **no metric instrument anywhere**; `automation.sweep.rows` is a span attribute |
| 5 | "api's lifecycle instruments" | **True**, and there are four more the brief did not name: the three `automation.queue.*` families and `automation.tick.duration` |
| 6 | "11 browser metrics derived at the collector, wired into all four backend overlays" | **True, verified name by name and overlay by overlay.** Also: the connector and its wiring are **uncommitted** at `6058e662` |
| 7 | "`contracts/browser-signals.json` was referenced in exactly two ways and read by nothing" | **Out of date.** `copilot-mro-obsm/tests/integration/otel/test_browser_derived_metrics.py:55` now loads and asserts on it cross-repo (via `sibling_variant`, explicitly so it cannot read the pre-merge `dashboard` checkout). It is a tier-2 consumer, which is why §1.1 makes the tier explicit rather than arguing about the word |
| 8 | "a family built from a constant, an f-string, a loop, or a name assembled from a prefix" | **Found one**, in telegram-bot: `registry.counter(f"telegram.{name}")` at `telemetry.py:900`, reached through four module constants. Today it mints no undeclared family; the mechanism means a future one would ship silently. The legacy shim has the same shape at `metrics.py:267` |
| 9 | "a dataclass field can look like an instrument" | **Confirmed as a non-issue here.** None of spellings 1-5 matches a bare field, and `ad_notification_dispatcher.py` produced no false positive |
| 10 | "the collector can create families no repo's code creates" | **True, and there is a second case the brief did not name:** `iac/alarms.tf` *declares* six `Flynapse/*` CloudWatch log-metric-filter families. None of them currently produces a datapoint. Two are gated off, and four sit on patterns the file itself calls dead. Declaring a family in config does not produce it — the same point this document makes about writing a name in prose |
