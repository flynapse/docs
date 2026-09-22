# Adversarial review — iac `2d493c8` (branch `obs-merge`), parent `3068b47`

Reviewer: independent, read-only. Nothing in `/home/aditya/Code/iac` or any sibling was modified.
All probes ran against copies under this scratchpad (`probe/`, `a1`–`a7`).

Commands run (all read-only):
- `git show 2d493c8`, `git diff 3068b47..2d493c8`, `git log -S …`
- `terraform fmt -check -recursive` → clean
- `bash scripts/validate_dashboards.sh` → all eight templates parse
- `python3 scripts/validate_metric_vocabulary.py` → 0 failures; `python3 scripts/validate_alarms.py` → 0 failures
- `cd /home/aditya/Code/api && DEBUG=false poetry run pytest ../iac/tests/unit/observability ../iac/tests/unit/alerting -q` → **65 passed in 1.69s**
- Seven hand-built mutations (`a1`–`a7`) against copies of the surface, run through the guard CLI with an explicit root.
- NOT run: `terraform init` / `validate` / `plan` (registry unreachable for `aws ~> 6.43`; local lock at 5.100.0). No AWS call.

---

## Defects, ranked

### P0-A — `ApiHighErrorRate` and `ApiP95LatencyHigh` are non-functional under BOTH candidate histogram shapes, and this commit made them strictly worse

`alarms.tf:114-145`. Both alarms now count requests by applying `rate()` / `increase()` directly to a
**histogram** family name carrying neither `_count` nor `histogram_count()`:

```
sum by ("@resource.service.name") (rate({"http.server.request.duration", "http.response.status_code"=~"5.."}[5m]))
/
(sum by ("@resource.service.name") (rate({"http.server.request.duration"}[5m])) > 0.05)
```

- **Native-histogram projection.** `rate(H[5m])` yields a native histogram; `sum by (…)` of native
  histograms yields a native histogram. PromQL supports `+` and `-` between two histograms and
  `*` / `/` only histogram-by-*float*. **histogram ÷ histogram is not a supported binary operation** —
  the sample is dropped. The volume guard is worse still: `histogram > float` is not a supported
  comparison either, so the denominator is empty before the division is even attempted. Result: the
  ratio never produces a value, so the alarm can never breach.
- **Classic bucket projection.** A classic histogram has **no series at the bare family name** — only
  `…_bucket` / `…_sum` / `…_count`. `{"http.server.request.duration"}` selects nothing. Empty again.

`ApiP95LatencyHigh` fails the same way and the pass did not say so: under native, the left limb
(`histogram_quantile` over a `sum by (le, …)`) actually works — the stray `le` grouping is harmless —
but the right limb of the `and on (…)` join is `sum by (…) (increase({"http.server.request.duration"}[15m])) >= 20`,
i.e. `histogram >= float`, which drops; an `and` with an empty right side is empty. Under classic, both
limbs select nothing.

**Correct expressions.**

| Shape | `ApiHighErrorRate` numerator/denominator | `ApiP95LatencyHigh` volume limb |
|---|---|---|
| native histogram | `sum by ("@resource.service.name") (histogram_count(rate({"http.server.request.duration", "http.response.status_code"=~"5.."}[5m])))` over `sum by ("@resource.service.name") (histogram_count(rate({"http.server.request.duration"}[5m])))` | `sum by (…) (histogram_count(increase({"http.server.request.duration"}[15m]))) >= 20`, and drop `le` from the quantile's `sum by` |
| classic buckets | `rate({"http.server.request.duration_count", …}[5m])` on both sides — **exactly the parent commit's text** | `increase({"http.server.request.duration_count"}[15m])`, quantile over `{"http.server.request.duration_bucket"}` |

**Was it previously functional?** Under classic projection, yes — `3068b47` spelled both alarms
`_count` / `_bucket`, which is correct under that hypothesis and wrong under the other. As of
`2d493c8` they are wrong under **both**. The commit moved a 50/50 bet to a 0/2. It did so on a premise
(no exporter-side suffixing) that answers a different question from the one the histogram spelling
turns on (storage/view-side projection) — a gap the commit itself records three lines above the code.

**How long dead?** `ApiHighErrorRate` was authored 2026-09-15 (`a0afd4f`) and changed 2026-09-20
(`2d493c8`). It has never been live-probed (B1a unresolved) and `alert_delivery_armed = false`, so it
has never been able to reach a human regardless. It is 5 days old and was never alive.

**On-call scenario.** The api starts answering 100 % 5xx. `ApiHighErrorRate` (severity **critical**) and
`ApiP95LatencyHigh` (warning) both sit in INSUFFICIENT_DATA and never transition. What the engineer
sees: no page, and a `flynapse-service-overview` dashboard whose PromQL text panel hands them the same
broken selectors to paste into Query Studio, where they also return nothing. What they miss: the
outage, and any hint that the alarm is the thing that is broken.

---

### P0-B — "the suffix question is SETTLED" is broader than its evidence, and it deleted the live RE-VERIFY from the one alarm that fires forever on a wrong name

`alarms.tf:27-51` (header) and `alarms.tf:174-185` (`CollectorTelemetryAbsent`).

I re-derived the premise independently and it holds *as far as it goes*:
`copilot-mro-obsm/deployment/otel/backend-aws.yaml:87-96` — the `metrics` pipeline is
`receivers: [otlp] → memory_limiter, resourcedetection, transform/genai_aliases,
attributes/metric_cardinality, redaction, batch → exporters: [otlphttp/cwmetrics]`. The only
`prometheus` token in `backend-aws.yaml` or `base.yaml` is the `:8888` **pull reader** for
self-telemetry (`backend-aws.yaml:64-67`, `base.yaml:244`), which nothing scrapes in aws. No
`prometheusremotewrite`. So **the collector appends nothing.**

That is not the claim the file now makes. It claims *CloudWatch* appends nothing. Suffixing is
equally a **receiving-side** normalization: Prometheus's own OTLP receiver applies
`UnderscoreEscapingWithSuffixes` by default, appending `_total` and unit suffixes to OTLP input. A
PromQL *view* over OTLP-ingested metrics is exactly the kind of layer that can do this, and both
documents the commit cites as closing the question still say, in as many words, that it is open:

- `copilot-mro-obsm/docs/runbooks/observability/aws-profile.md:183-184` — "Whether CloudWatch's PromQL
  view appends a `_total` or unit suffix to them is a B1a RE-VERIFY item".
- `copilot-mro-obsm/deployment/otel/dashboards/CATALOGUE.md:588` — the `CollectorTelemetryAbsent` row:
  "if CloudWatch appends `_total` (or a unit) to such names, `absent()` of the unsuffixed name fires
  permanently".

The "OBSERVED 2026-09-15" capture-exporter run cited in the header sat on the collector's **metrics
pipeline** (`aws-profile.md:170-178`) — it observed names *before* export. It is not evidence about
CloudWatch at all. The one thing genuinely settled by a fetched AWS doc is
`docs/plans/observability-rebuild-research/04-managed-backends-and-portability.md:91` (PromQL doc,
fetched 2026-09-05), whose worked example is `{"http.server.active_requests", "@resource.service.name"="myservice"}`
— a **gauge**, dotted and unsuffixed. That settles gauges. It does not settle monotonic sums (`_total`)
or histograms.

What the commit then did: **removed** the `RE-VERIFY (B1a)` on `CollectorTelemetryAbsent` that read
"a cumulative counter: if CloudWatch appends `_total`, absent() needs the suffixed name, or this alarm
fires forever", replacing it with "the suffix question is settled in the header".

**On-call scenario.** From the first apply after delivery is armed, `CollectorTelemetryAbsent`
(severity **critical**) pages continuously and cannot be cleared by anything the engineer does to the
collector — which is healthy. The correct diagnosis ("the name is right at the emitter and wrong at the
reader") is now actively contradicted by the file's own header, and the one comment that would have
pointed straight at it has been deleted. What they miss: that their critical pager is lying, and the
half-day of collector debugging that follows.

---

### P1-C — check #5 (state note) is circular: it can only recognise the one service that already has a gate

`scripts/validate_metric_vocabulary.py:470-509`. `gated_services` is built **from the patterns inside
the already-gated maps**. A service with no gate is, by construction, not "undeployed" as far as this
check is concerned.

**Proved (probe `a7`… no — probe `a2`).** I added a fresh entry to the **ungated** `log_count_alarms`:

```
DocHubWorkerErrors = { pattern = "{ ($.resource.attributes.service.name = \"doc-hub-worker\") && ($.severity_number >= 17) }"
                       namespace = "Flynapse/DocHub"  metric_name = "DocHubWorkerErrorRecords"  … }
```

— the original P0's exact shape: an ungated log-count alarm with `treat_missing_data = "notBreaching"`
on a service iac never deploys. `validate_metric_vocabulary.py` → **0 failures**. The only thing that
caught it was `validate_alarms.py` ("DocHubWorkerErrors has an alarm (local.log_count_alarms) but no
§2.1 aws form"), which is a **hand-maintained table**, not a derivation — and it would not have fired
had the author also added the row to `SECTION_2_1`.

A non-circular derivation is available and unused: this root declares exactly two OTel service names —
`apprunner.tf:47` `OTEL_SERVICE_NAME = "api"` and `lambda.tf:113` `OTEL_SERVICE_NAME = "ingest-parser"`.
Every `service.name` an alarm or widget selects could be checked against that set.

**Counter-evidence, in the guard's favour** (probe `a6`): gating the *wrong* map does **not** certify
itself. Adding `browser_alarms_gated = { for … in local.log_count_alarms … if var.automation_worker_deployed }`
produced **22 loud failures**. So "a wrong gate in alarms.tf certifies itself" is false in that
direction; the circularity is one-directional — the guard cannot learn about a service it was not
already told about.

---

### P1-D — the recorded B1a remediation is wrong in both directions, and its citation does not resolve

`scripts/validate_metric_vocabulary.py:68-81` (the note is correctly sited at the
`PROMETHEUS_SUFFIXES` definition, as claimed — verified) says: if B1a answers "classic projection",
"drop those five from this tuple, rerun the guard, and let the histogram families carry the suffix
again", calling it "one documented edit".

It is not one edit, and it is the wrong one:

1. **It fixes nothing in the surface.** Dropping suffixes from the tuple only stops the guard
   complaining. The histogram-family selectors would still have to be re-suffixed by hand:
   `http.server.request.duration` ×12 occurrences (alarms.tf, `service-overview`, `shift-optimizer`),
   `http.client.request.duration` ×1, `optimizer.run.duration` ×1, `optimizer.solve.duration` ×2,
   `telegram.turn.duration` ×1, `telegram.turn.phase.duration` ×1, `gen_ai.client.token.usage` ×1,
   `agent.turn.duration_seconds` ×1 — ~20 occurrences across 5 files. Nothing would tell you so; the
   guard would go green on the un-fixed surface.
2. **It over-corrects.** `_count` / `_sum` on a **counter** is always wrong on this endpoint. Dropping
   them from the tuple blinds the rule to `{"telegram.turns_count"}` forever after.
3. **Citation.** Both `alarms.tf:44-46` and this note cite `research 04, "Open questions"`. There is no
   such heading; the section is `## 10. Open probes / uncertainties` (line 459), and the sentence is at
   line 461. A reader grepping the cited string finds nothing.

---

### P1-E — the dialect rule omits the Prometheus **unit** suffixes it says it is enforcing

`scripts/validate_metric_vocabulary.py:81` —
`PROMETHEUS_SUFFIXES = ("_total", "_bucket", "_count", "_sum", "_created", "_gcount", "_gsum")`.
`add_metric_suffixes` appends **units** too (`s` → `_seconds`, `By` → `_bytes`), and both `alarms.tf:33-34`
and `README.md:291`-context prose say so ("mints `_total` / `_bucket` / `_count` / `_sum` **and the
unit suffixes**"). Those are not in the tuple.

**Proved (probe `a1`).** `{"optimizer.run.duration"}` → `{"optimizer.run.duration_seconds"}` in
`dashboards/shift-optimizer.json.tftpl`: guard **passes, 0 failures**. That is precisely the
half-converted spelling a human produces doing this by hand — strip `_bucket`, keep `_seconds` — and
it is the one the rule misses.

It cannot simply be added: `agent.turn.duration_seconds` is a **real instrument name**
(`copilot-mro-obsm/tests/integration/otel/_emitted_series.py`, histogram, unit `s`) and is charted
correctly in `dashboards/llm-agents.json.tftpl`. So the unit-suffix rule is undecidable without the
emitter inventory the script defers — which is the deferral arguing for its own urgency.

---

### P1-F — the browser alarms still assert health they cannot observe; the P0's shape recurs, untouched

`alarms.tf:256-311` + `:393-412` + `:423-432`. `BrowserErrorRateHigh`, `WebVitalLcpP75Poor`,
`WebVitalInpP75Poor`, `WebVitalClsP75Poor` are all `treat_missing_data = "notBreaching"` on
log-metric-filter metrics, and **there is no `BrowserTelemetryAbsent` companion** — `SECTION_2_1` in
`scripts/validate_alarms.py:82-100` contains exactly one silence alarm, `AutomationWorkerSilent`.

If the browser SDK, the gateway's browser OTLP receiver or the `otlp/browser` pipeline breaks, all four
sit **green forever**: "no matching record" read as a positive assertion of health — the literal
definition this commit gives for its own P0-2. The difference from the worker case is real: these are
LIVE-proven (P9 probe 2026-09-11), so data does flow today. But nothing in the estate distinguishes
"no browser errors" from "no browser telemetry".

**Full `treat_missing_data` audit** (every alarm in the file):

| Alarm(s) | Resource | Missing data | Asserts health it cannot observe? |
|---|---|---|---|
| 11 PromQL alarms | `promql` (`:349`) | no `treat_missing_data` — PromQL alarms go INSUFFICIENT_DATA | No (quiet, not green) — except `CollectorTelemetryAbsent`, which inverts to "fires forever" (P0-B) |
| `BrowserErrorRateHigh` | `log_count` (`:393`) | `notBreaching` | **Yes** — no silence companion (P1-F) |
| `AutomationRunErrors` | `log_count` (`:393`) | `notBreaching` | No — now gated (this commit's fix, and it is correct) |
| `WebVitalLcp/Inp/ClsP75Poor` | `web_vital_p75` (`:423`) | `notBreaching` | **Yes** — a thin, a quiet and a severed window are indistinguishable (P1-F) |
| `AutomationWorkerSilent` | `log_silence` (`:477`) | `breaching` | No — gated, and the inverse failure mode |
| `AlertDeliveryFailing-sns-*` | `alert_topic_delivery_failing` (`:504`) | `notBreaching` | **Marginally** — while `alert_delivery_armed = false` the topics have no subscribers, so SNS publishes no notifications, so no failures, so green: "delivery is healthy" asserted about a delivery path that is switched off |
| `AlertDeliveryFailing-forwarder` | `alert_forwarder_errors` (`:531`) | `notBreaching` | No — `count = var.alert_delivery_armed ? 1 : 0`, so it does not exist while disarmed |

---

### P1-G — the guard runs nowhere

`.github/workflows/terraform-plan.yaml` steps: `terraform version`, `configure-aws-credentials`,
`terraform init`, `terraform fmt -check`, `terraform validate`, `terraform plan`.
`.github/workflows/terraform-apply.yaml`: approval check, checkout, setup-terraform, credentials,
`terraform init`, `terraform apply`. **No Python setup, no pytest, no `validate_alarms.py`, no
`validate_dashboards.sh`, no `validate_metric_vocabulary.py`.**

Plainly: 601 lines of guard and 14 mutation proofs protect a rule that CI never evaluates. A defect
merged by anyone who does not type the README "Phase 6" line by hand is merged green, and the mutation
tests that prove the guard works are themselves never executed in CI. Every `SETTLED` in the table
below therefore means "settled against a human who chooses to run it", not "enforced". Adding a
`setup-python` + three-line step to `terraform-plan.yaml` would convert the whole set at once; it is the
highest value-per-line change available in this repo and the pass did not make it.

---

### P2-H — vacuous-pass surfaces

- **Sub-directory dashboards are invisible** (probe `a4`). `DASHBOARD_GLOB = "dashboards/*.json.tftpl"`
  (`:63`) is non-recursive. I added `dashboards/satellites/inventory.json.tftpl` containing
  `{"inventory.runs_total"}` (suffix), `rate("inventory.jobs"[5m])` (Grafana form) **and** an ungated
  `automation-worker` mention: guard → **0 failures**. `terraform` would happily render it if
  `cloudwatch_dashboards.tf` named that path.
- **A file off the glob is invisible** (probe `a3`): renaming `telegram-bot.json.tftpl` →
  `.json.tpl` with `_total` reintroduced → 0 failures. (Renaming an *existing* file would break
  `cloudwatch_dashboards.tf`; authoring a *new* one with another extension would not.)
- **The vacuous-pass defence pins six families and no more.**
  `test_the_guard_actually_reads_every_metric_family` asserts five metric names
  (`http.server.request.duration`, `agent.turn.calls`, `telegram.turns`, `optimizer.runs`,
  `otelcol_process_uptime`), one minted pair (`Flynapse/Browser`/`BrowserErrors`), and the exact
  `gated` dict. A seventh family — and any new dashboard — is unpinned, so the extractor can stop
  reaching it with nothing failing. `AWS/Bedrock` in particular is not pinned there (only in mutations).

### P2-I — the dialect rule only sees markdown **code spans**

`:449` reads `_CODE_SPAN.findall(properties["markdown"])`. Proved (probe `a5`): moving a selector out of
backticks into the surrounding prose —
`Request rate is sum(rate({"http.server.request.duration_count"}[5m])).` — passes with 0 failures.
Both the suffix rule and the brace-form rule are bypassed. A human reading the panel follows prose
exactly as readily as a code span; these dashboards are, by design, panels of instructions.

### P2-J — `service in text` is a bare substring match on a free-form service name

`:503`. Harmless today (only `automation-worker` is gated), but probe `a6` produced
"`dashboard`, which this root does not deploy" against prose merely containing the word "dashboard".
Gate any service named `api`, `core` or `dashboard` and the check becomes noise — which is how a rule
gets reworded around rather than obeyed.

### P2-K — `LedgerWriteFailures` is an alarm on a signal no instrument in the estate creates, documented but not gated

`alarms.tf:207-213`: "no instrument for agent.ledger.write_failures is created anywhere in the estate,
so this alarm cannot fire for any reason — it is inert, not quiet." Same family as the P0 the pass
fixed; the pass applied the gate pattern once and missed this instance too. Milder failure mode (a
PromQL comparison alarm sits INSUFFICIENT_DATA, not green), hence P2 — but there is no
`var.ledger_signal_wired` and nothing prevents a future reader treating a quiet critical alarm as health.

### P2-L — `agent-turn-explorer` is a billable dashboard of prose

Both widgets are now `type: "text"`. `cloudwatch_dashboards.tf:18-19` prices dashboards at
$3/dashboard-month past the first three. The content is *correct* — I verified `invoke_agent` exists
only as a span name / `gen_ai.operation.name` value — but a dashboard whose entire content is "go look
in Query Studio and Transaction Search" should be deleted (and its prose moved to the runbook), not
billed. `platform-health` retains data widgets, so it does not have this problem.

### P2-M — the Bedrock `SEARCH` schema is an **exact** dimension-set match, and the guard only checks presence

`dashboards/llm-agents.json.tftpl`: `SEARCH('{AWS/Bedrock,ModelId} MetricName="InvocationThrottles"', 'Sum', 300)`.
`InvocationThrottles` and `ModelId`-only are both correct against AWS's published Bedrock list — that
part of the fix is right. But a `SEARCH` schema matches only metrics published with *exactly* that
dimension set. iac declares no Bedrock wiring at all (`grep -rn bedrock *.tf` → nothing;
`aws_region = "ap-south-1"`), and the estate forces `global.*` cross-region inference profiles, so
whether Bedrock publishes those invocations under `ModelId` alone, under `ModelId` plus a profile
dimension, or in the profile's source region, is unprobed. `check_namespace_metric` verifies only that
`ModelId` is *present*. The widget can still draw nothing, certified correct.

### P2-N — citation drift

- `CATALOGUE.md:184` cited; the `ThrottledCount` text is at **:186-188** (`:187`).
- Commit message says "**Ten** mutation proofs"; `tests/unit/observability/test_validate_metric_vocabulary.py`
  carries **14** (`grep -c 'id="'` → 14).
- `research 04, "Open questions"` → `## 10. Open probes / uncertainties` (:459/:461).
- `alarms.tf` and the guard cite `docs/plans/observability-rebuild-research/04-…` with no repo prefix,
  from a root with no `docs/` directory. It resolves to the sibling `docs` repo only if you already know.

---

## Cross-repo contradictions — all four verified, plus two the pass did not name

| Claimed | Verified? | Actual |
|---|---|---|
| `CATALOGUE.md:184` still says `ThrottledCount` | **Yes**, at `:187` | "in `aws` this is the native `AWS/Bedrock` namespace (`ThrottledCount` / `Invocations` by `ModelId`)" |
| `aws-profile.md:13` still says `ThrottledCount` | **Yes** | "Bedrock throttles from the native `AWS/Bedrock` namespace (`ThrottledCount` by `ModelId`)" |
| `aws-profile.md:11` teaches `"http.server.request.duration_count"` | **Yes** | verbatim, in the "Is the API healthy" row |
| `aws-profile.md:56` + `:183` still call the suffix an open question | **Yes** | `:56` "check whether CloudWatch appends `_total` or a unit"; `:183-184` "…is a B1a RE-VERIFY item" |
| `CATALOGUE.md` `CollectorTelemetryAbsent` row still open | **Yes**, at `:588` | "if CloudWatch appends `_total` (or a unit)… `absent()` of the unsuffixed name fires permanently" |

**Missed by the pass, and worse than the instances it listed:**

1. `CATALOGUE.md:186-188` is the **shared view spec both dialects are authored from** (its own header,
   `:1-7`). Fixing the iac widget while leaving `ThrottledCount` in the spec means the next person
   authoring an aws Bedrock panel from the catalogue re-introduces the exact metric AWS does not
   publish. The pass fixed the instance and left the source.
2. `aws-profile.md:183-184` and `CATALOGUE.md:588` are not merely "still open" — they are the *only*
   two places in the estate that record the `CollectorTelemetryAbsent` fires-forever failure mode, and
   `alarms.tf` has just deleted its local copy of that warning while citing those files as evidence the
   question is closed (P0-B). The contradiction is load-bearing, not cosmetic.

---

## Gating fix — verdict

- **Same condition?** Yes, literally. `alarms.tf:336-337` — `worker_silence_alarms` and
  `worker_run_error_alarms` are both `{ for alert, entry in local.<map> : alert => entry if
  var.automation_worker_deployed }`, and `scripts/validate_alarms.py` now pins **both** through one
  format string (`WORKER_GATE`) over a `WORKER_GATED_MAPS` dict. One switch, one spelling, one pin.
  This is the cleanest part of the commit.
- **Transition (`true → false` on an existing alarm)?** Clean. The resource addresses are unchanged —
  `aws_cloudwatch_metric_alarm.log_count["AutomationRunErrors"]` and
  `aws_cloudwatch_log_metric_filter.alerts["AutomationRunErrors"]`. The key simply leaves the `for_each`
  map, so Terraform destroys both in place; no `moved` block is needed and no orphan is left, because
  neither the resource name nor the map key changes. Flipping back to `true` restores the same key at
  the same address with no diff. Read from the HCL; **not** confirmed by `terraform plan`.
- **Other ungated alarms on undeployed services?** Two:
  `TelegramTurnFailureRate` (`alarms.tf:222`) selects `"@resource.service.name"="telegram-bot"`, and iac
  declares no telegram-bot compute at all (`grep -rn telegram *.tf` hits only `alarms.tf` and
  `cloudwatch_dashboards.tf`; `CATALOGUE.md:497` says "the bot **will** run on AWS"). Same evidence class
  the pass used to gate `automation-worker`; benign failure mode (a ratio comparison stays
  INSUFFICIENT_DATA, never green), so P2 not P0 — but the pass asserted "which iac deploys none of" for
  one service and never ran the same test over the rest. `LedgerWriteFailures` is the second (P2-K).
- **`treat_missing_data` audit:** table under P1-F. Two findings: the four browser alarms, and the
  disarmed `AlertDeliveryFailing-sns-*` pair.

---

## `terraform validate` — what a compiler read finds

I read the diff as a type-checker would. **No new `validate`-class defect is introduced by this commit:**

- `local.worker_run_error_alarms` is defined (`:337`) and referenced only at `:378` and `:394`; locals
  are order-independent, so the forward reference is fine.
- `worker_log_count_alarms` entries carry **exactly** the same six attributes as `log_count_alarms`
  (`description`, `pattern`, `namespace`, `metric_name`, `value`, `unit`), so `merge()` yields a uniform
  object type and every `each.value.X` in both consuming resources resolves. Had the attribute sets
  differed, `merge` would still succeed and `each.value.unit` would fail at plan — this is the exact
  shape `validate` would have caught, and it is clean.
- `local.alert_thresholds["AutomationRunErrors"]` exists (`validate_alarms.py:100`), so `:399`/`:404`
  resolve for the newly-merged key.
- `agent-turn-explorer.json.tftpl` no longer references `${region}` or `${otel_log_group}`, but
  `templatefile()` permits unused vars — not an error.
- No new `${` or `%{` sequence was introduced into any `.tftpl`; all remaining interpolations
  (`${region}`, `${otel_log_group}`, `${apprunner_app_log_group}`) are supplied by
  `cloudwatch_dashboards.tf:24-35`.
- `terraform fmt -check -recursive` → clean. `scripts/validate_dashboards.sh` → all eight parse.

**What remains un-type-checked** is pre-existing, not from this commit: the whole
`evaluation_criteria { promql_criteria { … } }` block on `aws_cloudwatch_metric_alarm.promql` requires
provider ≥ 6.43 and has never been validated in this workspace. Since the 11 PromQL alarms are where
P0-A and P0-B live, "validate was skipped" is doubly unfortunate — but `validate` would not have caught
either defect anyway: both are semantic, inside an opaque query string the provider passes through.

---

## What I tried to break and could not

1. **The pipeline premise**, re-derived independently from `backend-aws.yaml:27-96` and `base.yaml:229-247`:
   the aws `metrics` pipeline exports only through `otlphttp/cwmetrics`; the only `prometheus` token
   anywhere is the `:8888` pull reader; no `prometheusremotewrite`. The collector appends nothing.
   Holds. (What does *not* follow from it is P0-B.)
2. **Every converted selector against a real emitter.** Not one is an invention:
   `optimizer.runs` / `.run.duration` / `.solve.duration` / `.runs.active` →
   `shift-optimizer/shift_optimizer/app/services/run_telemetry.py:52,55,61,67`;
   `telegram.updates(.active)` / `.turns` / `.turn.duration` / `.turn.phase.duration` / `.turn.cost` /
   `.jobs` / `.uploads` / `.provisionings` / `.refusals` → `telegram-bot/telegram_bot/telemetry.py:857-891`;
   `http.server.request.duration` / `http.server.active_requests` →
   `api/flynapse_api/telemetry/http_server.py:174,201`; `auth.rejections` →
   `api/flynapse_api/middleware/telemetry.py:34`;
   `http.client.request.duration` → the httpx instrumentor under stable semconv, guaranteed by
   `flynapse-otel/flynapse_otel/bootstrap.py:171` (`setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")`);
   `agent.turn.calls` / `agent.model.cost_usd` / `agent.model.unpriced_calls` /
   `gen_ai.client.token.usage` / `agent.turn.duration_seconds` →
   `copilot-mro-obsm/tests/integration/otel/_emitted_series.py`;
   `otelcol_process_uptime` / `otelcol_exporter_send_failed_*` / `otelcol_exporter_queue_{size,capacity}` /
   `otelcol_receiver_refused_*` → the observed table at `aws-profile.md:174-178`.
   **This is the strongest part of the commit.** The rename pass is right about *which* metric; it is
   only wrong about *what shape* the histograms are in.
3. **Check #4 is not harmfully circular.** Alarms that read a `Flynapse/*` metric do so via `for_each`,
   which `read_alarms` deliberately skips (`:420`), so the minted set is only ever used to judge
   *dashboards* — a genuine cross-file check, not self-certification.
4. **A wrong gate does not certify itself** (probe `a6`, 22 loud failures).
5. **A suffixed name hidden behind a label matcher, and a dotted name written bare**, are both caught —
   their own mutations 11-12, and the suite is green: 65 passed in 1.69 s.
6. **Both "dead widget" claims are true.** `base.yaml:229-236` sets only
   `service.telemetry.logs.level: info` — no log processors — so collector internal logs go to stderr;
   and no log group in `cloudwatch.tf` receives the demo box's container stdout, with
   `modules/otel-gateway` instantiated only from its own `examples/basic/main.tf`.
7. **The dashboards this pass did not touch are not hiding a dialect defect.**
   `frontend.json.tftpl` and `dependencies.json.tftpl` contain **zero** metric selectors
   (`grep -o '_total\|_bucket\|rate(\|increase(\|histogram_quantile'` → empty for both).
8. **No leftover oss-dialect spelling anywhere in iac.** A full sweep for `*_total|_bucket|_count|_sum`
   and unit suffixes returns only: prose deliberately naming the oss dialect, `agent.turn.duration_seconds`
   (a real instrument name), and HCL identifiers (`for_seconds`, `log_count`, `histogram_count`).

## What I simply did not test

- Anything live. No AWS call, no `terraform init/validate/plan` (registry unreachable for `aws ~> 6.43`;
  lock at 5.100.0), no CloudWatch query. **Every statement about what CloudWatch stores or projects —
  the pass's and mine — is reasoning from documentation, not observation.** P0-A and P0-B are arguments
  about the same unprobed endpoint; they are strong arguments, and they are not probes.
- Whether CloudWatch's PromQL implementation rejects `histogram / histogram` and `histogram > float`
  the way Prometheus does. I reason from PromQL semantics, which is the dialect AWS says it implements.
- Whether `alarms.tf` has ever been applied, so I cannot say whether an `AutomationRunErrors` alarm sits
  in the account today awaiting destruction.
- B1b (Logs Insights stored field paths) — untouched by this pass, unverified by me. Every `log` widget
  and every metric-filter `$.` selector is still unproved.
- The `oss` half of the merge, and `copilot-mro-obsm`'s own lints.
- `modules/otel-gateway` beyond confirming the root does not instantiate it.

---

## Claims table

Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Tier | Chunk | Claim state
---|---|---|---|---|---|---|---|---|---
iac | alarms.tf:114-127 | `ApiHighErrorRate` counts requests as bare `rate({"http.server.request.duration"…})` | pass held the name "settled" and left the COUNT form "written bare … until B1a says which" | histogram÷histogram unsupported (native); no bare-name series (classic); parent `3068b47` used `_count`, correct under classic | none — no guard checks whether a selector's instrument KIND fits its operator | not recorded | 2 | P0-A | OPEN
iac | alarms.tf:129-145 | `ApiP95LatencyHigh` volume limb is `increase({histogram}) >= 20` | same | `histogram >= float` unsupported → empty right limb of `and on()`; classic → no bare-name series | none | not recorded | 2 | P0-A | OPEN
iac | alarms.tf:27-51 | header declares the suffix question SETTLED, "no longer a B1a question" | no prometheus exporter on the aws metrics path | premise verified (`backend-aws.yaml:87-96`) but answers the emitter side only; `aws-profile.md:183-184` and `CATALOGUE.md:588` still say the VIEW side is open | `test_validate_metric_vocabulary.py` enforces the rule; nothing tests the rule's own premise | partially recorded — mutations prove the guard fires on a suffix, never that the rule is right | 2 | P0-B | OPEN
iac | alarms.tf:174-181 | deleted the `RE-VERIFY (B1a)` warning from `CollectorTelemetryAbsent` | header claims settled | the cited "OBSERVED 2026-09-15" capture sat on the collector's metrics pipeline — pre-export, not CloudWatch | none | not recorded | 2 | P0-B | OPEN
iac | scripts/validate_metric_vocabulary.py:470-509 | undeployed-service set derived from the existing gate set | "the gate set is read out of alarms.tf rather than listed" | probe `a2`: ungated `notBreaching` alarm on `doc-hub-worker` → 0 failures; the two service names iac actually declares (`apprunner.tf:47`, `lambda.tf:113`) are never read | `p0-2-the-run-error-alarm-loses-its-worker-gate` — **resolves**, but only for `automation-worker` | yes, for `automation-worker` only (gate removed → guard names it) | 1 | P1-C | ASSERTED
iac | scripts/validate_metric_vocabulary.py:68-81 | B1a remediation recorded as "one documented edit to PROMETHEUS_SUFFIXES" | keeps the fix in one place | ~20 histogram selectors across 5 files would still need re-suffixing; dropping `_count`/`_sum` also blinds the rule on counters; cited section `"Open questions"` does not exist (it is `## 10. Open probes / uncertainties`) | none | not recorded | 1 | P1-D | OPEN
iac | scripts/validate_metric_vocabulary.py:81 | `PROMETHEUS_SUFFIXES` omits unit suffixes | undecidable without an emitter inventory (`agent.turn.duration_seconds` is real) | probe `a1`: `{"optimizer.run.duration_seconds"}` → 0 failures, though `alarms.tf:33` and the README both say units are minted by the same translation | none for unit suffixes | yes — my mutation `a1` passes where it should fail | 1 | P1-E | OPEN
iac | alarms.tf:256-311, 423-432 | four browser alarms keep `notBreaching` with no silence companion | "no matching record publishes no data point: quiet is not an incident" | `SECTION_2_1` (validate_alarms.py:82-100) has exactly one silence alarm; a severed browser path reads as health | none | not recorded | 1 | P1-F | OPEN
iac | .github/workflows/terraform-plan.yaml, terraform-apply.yaml | no Python step in CI | README documents the validators as a manual "Phase 6" line | both workflows run only `version/init/fmt/validate/plan\|apply`; neither invokes pytest or any validator | n/a — this IS the finding | n/a | 1 | P1-G | OPEN
iac | scripts/validate_metric_vocabulary.py:63 | `DASHBOARD_GLOB` non-recursive | — | probe `a4`: `dashboards/satellites/inventory.json.tftpl` with `_total`, the Grafana form AND an ungated `automation-worker` → 0 failures | `test_the_guard_actually_reads_every_metric_family` pins 6 families; a 7th is unpinned | yes — probe `a4` | 2 | P2-H | OPEN
iac | scripts/validate_metric_vocabulary.py:449 | dialect rule reads markdown code spans only | prose must not be read as PromQL | probe `a5`: suffixed selector in prose → 0 failures | `test_prose_that_is_not_a_query_is_left_alone` — **resolves**, and pins the opposite property | yes — probe `a5` | 2 | P2-I | OPEN
iac | scripts/validate_metric_vocabulary.py:503 | `service in text` substring match | — | probe `a6`: fired on prose containing the word "dashboard" | none | yes — probe `a6` (as over-fire) | 2 | P2-J | OPEN
iac | alarms.tf:207-213 | `LedgerWriteFailures` left ungated with a prose note | signal is DARK estate-wide | same family as the gated P0; no `var.ledger_signal_wired`; PromQL alarm → INSUFFICIENT_DATA not green, hence milder | none | not recorded | 2 | P2-K | OPEN
iac | alarms.tf:222-231 | `TelegramTurnFailureRate` ungated on a service this root does not deploy | not examined by the pass | `grep -rn telegram *.tf` → only alarms.tf + cloudwatch_dashboards.tf; `CATALOGUE.md:497` "the bot **will** run on AWS" | `check_state_notes` cannot see it (P1-C) | not recorded | 2 | P2-K | OPEN
iac | dashboards/agent-turn-explorer.json.tftpl | both widgets now `type: "text"` | the log widget could not return data (true) | claim verified; but `cloudwatch_dashboards.tf:18-19` prices this at $3/month for prose | `validate_dashboards.sh` parses it | not recorded | 2 | P2-L | OPEN
iac | dashboards/llm-agents.json.tftpl | Bedrock `SEARCH('{AWS/Bedrock,ModelId} …')` | `InvocationThrottles` published, `ModelId` the only dimension | both correct; but SEARCH schema is an EXACT dimension-set match and the guard checks presence only; no Bedrock wiring in iac, `global.*` profiles forced | `p1-5-the-bedrock-widget-names-an-unpublished-metric`, `…-drops-the-only-dimension-bedrock-has` — both **resolve** | yes, for name + dimension presence; **no** for schema exactness | 2 | P2-M | ASSERTED
iac | alarms.tf:336-337 | both worker alerts gated on one switch | mirror of the existing silence gate | identical comprehension; `validate_alarms.py` pins both via one `WORKER_GATE` format string | `the-worker-run-error-gate-is-dropped`, `the-run-error-alarm-bypasses-the-worker-gate`, `the-run-error-filter-bypasses-the-worker-gate`, `the-worker-silence-gate-is-dropped` — all four **resolve** | yes — gate removed / for_each redirected → named failure | 1 | P0-2 fix | SETTLED
iac | alarms.tf:378, 394 | `AutomationRunErrors` destroys cleanly on a `true → false` flip | resource addresses and map keys unchanged | read from the HCL; `for_each` key leaves the map, Terraform destroys in place, no `moved` block needed | `LOG_FILTER_FOR_EACH` / `LOG_COUNT_FOR_EACH` pins in validate_alarms.py | yes (for_each mutations above) | 1 | P0-2 fix | SETTLED (structure) / OPEN (never planned)
iac | dashboards/{service-overview,telegram-bot,shift-optimizer}.json.tftpl | every selector converted to dotted brace form | the aws path applies no prometheus translation | every converted name resolves to a real emitter (8 source files checked); no leftover oss spelling in the repo | `p0-3-*` ×3, `p1-4-*`, `a-suffixed-name-hides-behind-a-label-matcher…`, `a-dotted-name-is-written-bare…` — all **resolve** | yes | 1 | P0-3/P1-4 | SETTLED for counters/gauges; OPEN for the 8 histogram families (P0-A/P0-B)
iac | dashboards/platform-health.json.tftpl | collector-log widget → text panel | collector logs never reach the OTLP log group | `base.yaml:229-236` sets only `logs.level`; no log group in `cloudwatch.tf` takes the box's stdout; `modules/otel-gateway` instantiated only in its own example root | `p1-7-a-worker-widget-loses-its-state-note` **resolves** (covers the sibling widgets) | yes, for the state note; **no** for the log-reachability claim | 1 | P1-6/P1-7 | ASSERTED
iac | scripts/validate_metric_vocabulary.py:435-465 | metric-widget `expression` fields now dialect-checked | previously blind at the planned live-PromQL upgrade | `expression` is the only widget field that can carry a metric query; `log.query` is deliberately Logs-Insights-only; `title`/`annotations` carry none. Coverage of query-bearing fields is complete | `a-live-promql-metric-widget-escapes-the-dialect-rule` **resolves** | yes | 1 | guard fix | SETTLED
copilot-mro-obsm | deployment/otel/dashboards/CATALOGUE.md:187 | left teaching `ThrottledCount` | out of iac's scope | verified verbatim; this is the SHARED SPEC both dialects are authored from, so the defect regenerates | none | not recorded | 1 | contradiction | OPEN
copilot-mro-obsm | docs/runbooks/observability/aws-profile.md:11,13 | left teaching `duration_count` and `ThrottledCount` | same | verified verbatim | none | not recorded | 1 | contradiction | OPEN
copilot-mro-obsm | docs/runbooks/observability/aws-profile.md:56,183 + CATALOGUE.md:588 | left calling the suffix an open B1a item | same | verified verbatim — and these are now the ONLY record of the `CollectorTelemetryAbsent` fires-forever mode, which alarms.tf deleted | none | not recorded | 2 | P0-B | OPEN
iac | commit message; alarms.tf:44; guard:75 | "Ten mutation proofs"; `research 04, "Open questions"`; `CATALOGUE.md:184` | — | 14 mutations present; section is `## 10. Open probes / uncertainties` (:459/:461); text is at `:187` | n/a | n/a | 2 | P2-N | OPEN

---

## Open claims, tier 2 first

**Tier 2 — irreversible or estate-shaping**

1. **P0-A — the estate's critical 5xx pager and its latency pager cannot fire.** `ApiHighErrorRate`
   and `ApiP95LatencyHigh` apply counter operators to a histogram family: invalid under native
   projection, empty under classic. Before this commit they were correct under classic. Decide the
   shape (probe B1a) or, failing that, revert to the `_count`/`_bucket` spelling — a 50 % chance beats
   a 0 % one — and in either case write the count with `histogram_count()` or the `_count` series
   rather than bare. **No guard covers operator-vs-instrument-kind.**
2. **P0-B — "SETTLED" outruns its evidence, and the warning that would have caught it was deleted.**
   The proof covers the collector, not CloudWatch's PromQL view; suffixing is equally a receiving-side
   normalization (Prometheus's own OTLP receiver defaults to it). Restore the `RE-VERIFY` on
   `CollectorTelemetryAbsent` — it is the one alarm that pages forever on a wrong name — and narrow the
   header to what the AWS doc actually shows: a **gauge** example. Counters and histograms stay open.
3. **P2-H / P2-I / P2-J — the guard's reach.** Sub-directory dashboards, prose-not-code-span queries and
   a substring service match are all demonstrated bypasses. Each is cheap to close
   (`rglob`, scan the whole markdown for `_LOOKS_LIKE_PROMQL` spans, match on a word boundary).
4. **P0-B contradictions (`aws-profile.md:56,183`, `CATALOGUE.md:588`).** These are not stale prose —
   they are the last surviving record of a failure mode `alarms.tf` just deleted. Reconcile by
   restoring the iac warning, not by editing them to agree.

**Tier 1 — consequential but reversible**

5. **P1-C — check #5's circularity.** It recognises only the service it was already told about. Derive
   the deployed set from `apprunner.tf` / `lambda.tf` `OTEL_SERVICE_NAME`, or say plainly in the
   docstring that check #5 is a *regression* guard for one known service, not a rule.
6. **P1-D — the recorded remediation is both insufficient and over-broad**, and cites a section that
   does not exist. Rewrite it as: "drop the three histogram-family suffixes *and* re-suffix these N
   named selectors", with the list.
7. **P1-E — unit suffixes.** The rule claims to enforce what `add_metric_suffixes` mints and enforces
   two-thirds of it. Closing this needs the deferred emitter inventory; until then, say so at the
   constant rather than implying coverage.
8. **P1-F — four browser alarms assert health they cannot observe**, with no `BrowserTelemetryAbsent`
   companion. Same shape as the P0 this commit fixed.
9. **P1-G — none of it runs in CI.** A `setup-python` + three-line step in `terraform-plan.yaml`
   converts every `SETTLED` in the table above from "settled against a human who remembers" to
   "enforced". Highest value-per-line change available in this repo.
10. **Cross-repo: `CATALOGUE.md:187` is the spec, not an instance.** Leaving `ThrottledCount` there
    regenerates the defect on the next aws panel authored from the catalogue.

**Tier 2 — smaller, still open**

11. P2-K — `LedgerWriteFailures` and `TelegramTurnFailureRate`: the gate pattern applied once, two
    instances missed.
12. P2-L — `agent-turn-explorer` bills $3/month for two paragraphs of prose.
13. P2-M — the Bedrock `SEARCH` schema is an exact dimension-set match on an unprobed, cross-region-
    inference-profile namespace; the guard certifies presence, not the schema.
14. P2-N — citation drift (ten vs fourteen mutations; "Open questions"; `:184` vs `:187`; repo-less
    `docs/` paths).

---

## Re-statement 2026-09-22

COMPLETE — all 25 rows re-stated (this section replaced the sixth file a machine restart cut short); iac r4
(`d52e8b8..74346bb`) is running and will file `claims-iac-r4.md` — pointed to as "pending r4" below.

Appended by the R2 packet re-stater (Opus), read-only against every tree, nothing committed, no test run,
no terraform, no AWS. The table above is left as filed. **HEADs read:** iac `74346bb` (obs-merge; the
only untracked paths are `__pycache__` dirs and the pre-existing `poc_ec2_setup_ubuntu.sh`) · copilot-mro-obsm
`735f8213` (obs-merge, clean) · utils-obsm `179cc6d` (obs-merge) · core-obsm `fe41002` (obs-merge; the
E-file's re-statement read `b4d2c33` earlier the same day) · dashboard-obsm `4a7714a` · copilot-mro-obsm-cli
`7880bc44` (branch `obs-merge-cli`, NOT merged; the E-file read `f1100629`). **Column note:** the table has
no `#` column, so rows are numbered IF-1..IF-25 below in file order and identified by their `File:line`
cell (the README lists this file at 22 rows; the table holds 25). Its `Tier` column is §2.3a's (1 or 2, no
0) and its `Chunk` column carries the reviewer's own severity ids (P0-A … P2-N) — there is no separate
severity column, and nothing below rewrites either. "Implementer" in an evidence cell means the proof is
the committing lane's own; the "`9fda3db` reviewer" is the read-only adversarial agent the iac implementer
spawned over its own diff (ledger CHECKPOINT 10c/11b) — separate from the implementer, but commissioned by
it, so the auditor may weigh it as less than a controller-launched review.

**What moved the ground under this file since 2026-09-20.** The review was filed against `2d493c8`; iac
then took `9fda3db` (the histogram shape was ANSWERABLE from the vendor page: CloudWatch converts
explicit-bucket histograms to exponential at ingestion, so the parent's `_count`/`_bucket` spelling was
wrong too — both API alarms now take their count through `histogram_count()`; the `CollectorTelemetryAbsent`
RE-VERIFY restored; header narrowed; all five guard-reach defects fixed; CI Python step added; B1a note
rewritten with the selector list), `234603b` (the `9fda3db` reviewer's triage: two dashboard queries the fix
had missed, two claims WITHDRAWN — "fails LOUDLY" had no source and "the one-line flip" does not flip — plus
four residual guard holes and `pull_request`/`fetch-depth: 0` in CI), `5e476e0` (nine stale state claims:
DARK→WIRED for signals G.6 wired, LIVE→WIRED for the browser four), `607cee0`/`48fc50c`/`f85284e` (G.72
attribute keys; `b1b_metric_filter_probe.sh`), `89f3592`/`013dc89` (G.107 content flags), then the
`013dc89..d52e8b8` range reviewed in `claims-iac-r3.md` (M-CLI-TELEMETRY, G.117, C1.5, M-WEAVIATE-LEFTOVERS,
M-LEGACY-PANELS) and its fix pass `d86b378..74346bb` (ledger Addendum 154). Owner rulings that bear on rows
here: **M-ALARM-DENOMINATOR** (keep `notBreaching` + a denominator counter, built after the C2 probe),
**M-LEGACY-PANELS** (15 born-`_total` legacy names now on the aws surface by design), **M-CLI-TELEMETRY**
(`claude_code.*` retired from the board), **M-G117-DEFAULT** and **M-WEAVIATE-LEFTOVERS** (no row here).
On the copilot-mro side, G.6 (`3978073b`) created and wired `agent.ledger.write_failures`, and `95ca0e29`
fixed the three cross-repo prose rows this file filed.

| row # | File:line (as filed) | claim state at filing | state now | evidence | source |
|---|---|---|---|---|---|
| IF-1 | `alarms.tf:114-127` `ApiHighErrorRate` bare `rate({histogram})` | OPEN (P0-A, tier 2) | FIXED-AT iac `9fda3db` (implementer): both limbs read `histogram_count(rate({"http.server.request.duration"…}[5m]))` innermost, float arithmetic above it (`alarms.tf:292-300` at HEAD). The `9fda3db` reviewer re-fetched the AWS pages and confirmed the exponential-histogram store and the two-state alarm model (ledger CP 11b), then found the same fix had MISSED two dashboard queries (fixed `234603b`). This row's remedy ("revert to `_count`/`_bucket` — 50 % beats 0 %") is REFUTED-BY `9fda3db`: the classic family is unrepresentable on that endpoint, so `3068b47` was wrong as well (CP 10b). Still no guard on operator-vs-instrument-kind (verified: no test id at HEAD plants a bare `rate({histogram})`). RESIDUAL BET, stated in the file: `histogram_count()` is not named on any AWS page; the "fails LOUDLY" sentence was WITHDRAWN at `234603b` — an unsupported function may sit GREEN. OWNER-OWED sheet **C2** (one `PutMetricAlarm` with a bogus function name) | `9fda3db`, `234603b` messages; ledger CP 10b/11b; `alarms.tf:251-300` | tree; ledger |
| IF-2 | `alarms.tf:129-145` `ApiP95LatencyHigh` volume limb | OPEN (P0-A, tier 2) | FIXED-AT `9fda3db`: right limb is `sum by (…) (histogram_count(increase({"http.server.request.duration"}[15m]))) >= 20`; `le` dropped from the quantile's grouping (`alarms.tf:312-323`; 0 selectors carry `sum by (le` at HEAD — the two remaining hits are comments). Same bet and same owner item as IF-1 | `alarms.tf:302-323` | tree |
| IF-3 | `alarms.tf:27-51` header "SETTLED, no longer a B1a question" | OPEN (P0-B, tier 2) | FIXED-AT `9fda3db` (+ `234603b`): the header now says the collector premise "answers a DIFFERENT question", that suffixing is equally receiving-side, that the 2026-09-15 capture sat on the collector pipeline; SHAPE settled from the vendor page, NAME "documented, NOT observed, so it stays a B1a item for the SUMS" (the one worked selector is a gauge); both contrary citations recorded, including the histograms page's own `http_request_duration_seconds` example (`alarms.tf:29-93`). Independent re-fetch by the `9fda3db` reviewer. The underlying question is OWNER-OWED (B1a canary; nearest sheet line C2) | `alarms.tf:29-93`; CP 10b/11b | tree; ledger |
| IF-4 | `alarms.tf:174-181` deleted `RE-VERIFY (B1a)` on `CollectorTelemetryAbsent` | OPEN (P0-B, tier 2) | FIXED-AT `9fda3db`: "RE-VERIFY (B1a) — RESTORED, because 2d493c8 deleted it on a premise that does not carry it", fires-forever consequence spelled out, the two copilot-mro documents cited by section + verbatim quote (not line), and the one edit named (`absent(otelcol_process_uptime_total)` + the three comparison alarms) (`alarms.tf:363-388`). Verified at HEAD. The condition itself is still open — see IF-24 | `alarms.tf:355-389` | tree |
| IF-5 | `validate_metric_vocabulary.py:470-509` check 5 circular | ASSERTED (P1-C, tier 1) | FIXED-AT `9fda3db`: `declared_services` derives the deployed set from `OTEL_SERVICE_NAME` literals in this root's `.tf` (`api`, `ingest-parser`; `:704-706`, `:736-770`) plus `SELF_NAMING_DEPLOYED_SERVICES = {"dashboard"}` (`:726-732`) — this row's own remedy ("derive from apprunner.tf/lambda.tf") is REFUTED in part: alone it would have failed all four browser alarms (CP 10b). Vacuity checked against the DERIVED half (`test_check_five_refuses_to_pass_when_it_can_derive_no_deployed_service` `:300`); `test_the_deployed_service_set_is_derived_from_the_root_not_from_the_gates` `:286`; mutation `an-ungated-notbreaching-log-count-alarm-on-a-service-that-is-not-the-gated-one` `:621` (this row's probe a2). Docstring NARROWED at `234603b`: it catches the undeployed-service variant only, not an ungated `notBreaching` alarm on a DEPLOYED service whose filter cannot match (DEFERRED, `:1536-`). Implementer-proved; iac r3 measured the suite green at six commits (a measurement); no independent red on check 5 recorded — pending r4 | `9fda3db`, `234603b`; validator at HEAD | tree |
| IF-6 | `validate_metric_vocabulary.py:68-81` B1a remediation "one documented edit" | OPEN (P1-D, tier 1) | FIXED-AT `9fda3db` → corrected `234603b`: the note is the two-step it is, with the table — 18 occurrences of 8 families across 5 files (the first version said 5 for `alarms.tf` and 7 families; both wrong, corrected with the counting method) (`:1496-1533`); step 1 keeps `_total`/`_created` so the "over-corrects" point is answered; citation reads `research 04 §10 "Open probes / uncertainties"` (`:143`; `alarms.tf:44-45`); paths marked workspace-relative (`:599`; `alarms.tf:21-22`). Prose, no guard | validator `:1496-1533` | tree |
| IF-7 | `validate_metric_vocabulary.py:81` no unit suffixes | OPEN (P1-E, tier 1) | FIXED-AT `9fda3db` (`UNIT_SUFFIXES` + a sourced `UNIT_SUFFIXED_INSTRUMENTS` allow-list, `agent.turn.duration_seconds` exempted by creation site) → `234603b` (the real OTel→Prometheus unit map after the `9fda3db` reviewer found nine unit suffixes scoring 0 failures; 8 parametrised proofs `test_every_real_unit_suffix_is_rejected_not_just_the_obvious_ones` `:349`); this row's probe a1 is mutation `the-half-conversion-a-human-makes-a-unit-suffix-with-no-family-suffix` `:614`. INDEPENDENT red: iac r3 V7 (the `_seconds` entry dropped) — `claims-iac-r3.md` IR3-20 SETTLED, tier 0. `document_hub_processing_duration_seconds` joined the exemption at `d52e8b8`. Contrary citation (b) on the AWS histograms page is recorded at `alarms.tf:83-92` as evidence AGAINST this rule — a stated bet, not closed | `:172-233`; `claims-iac-r3.md` IR3-20 | tree; packet |
| IF-8 | `alarms.tf:256-311, 423-432` four browser alarms, no silence companion | OPEN (P1-F, tier 1) | SUPERSEDED-BY **M-ALARM-DENOMINATOR** (§4a-bis, 2026-09-22): owner ruled KEEP `notBreaching` + ADD one denominator metric filter (every `service.name = dashboard` record, no alarm on it), built AFTER the C2 AWS probe — iac lane idle until C2. In tree: `9fda3db` deliberately added NO `BrowserTelemetryAbsent` (the browser has no heartbeat, so a companion pages every quiet night; `alarms.tf:475-494`), `5e476e0` downgraded the four from `LIVE` (an oss P9 probe) to `WIRED 2026-09-11, retrieval unproved`, and the `AlertDeliveryFailing-sns-*` marginal is stated at `:766-784`. WORSE than filed: the four `$.` patterns are KNOWN NOT TO MATCH (B1b, G.73 — `$.attributes.event_name` names a key that does not exist), so the alarms are dead, not quiet, and "must not be armed". Header `:155-167` still reads "OWNER RULING OWED" — stale prose against the ruling, unfixed. Plan G.73 box still `[ ]`. OWNER-OWED sheet **C2** (`b1b_metric_filter_probe.sh` + `filter-log-events`), then the iac build | §4a-bis M-ALARM-DENOMINATOR; sheet A6/C2; `alarms.tf:95-167, 475-516` | plan; tree |
| IF-9 | `.github/workflows/terraform-plan.yaml`, `terraform-apply.yaml` no Python step | OPEN (P1-G, tier 1) | FIXED-AT `9fda3db` for the plan workflow: `setup-python` → `pip install pytest pyyaml` → `validate_dashboards.sh` → `validate_alarms.py` → `validate_metric_vocabulary.py` → `pytest tests -q`, all BEFORE credentials/init; `234603b` added the `pull_request` trigger (the guards had run only on push to main, so nothing on this branch was gated) and `fetch-depth: 0` (the lineage scan in `test_alert_targets_untracked.py` was vacuous at depth 1 — a hole the pytest step itself created). Independent: iac r3 ran the same three validators + pytest per commit (IR3-27 SETTLED, measured). `terraform-apply.yaml` still runs NONE (verified: no python/pytest/validate step; last touched `6be3907`) — deliberate, reported as the owner's call; no decision-sheet line names it. Note: nothing is pushed (M-COMMIT), so CI has never actually executed these steps on this branch | `terraform-plan.yaml` at HEAD; CP 10b/11b; IR3-27 | tree; ledger |
| IF-10 | `validate_metric_vocabulary.py:63` non-recursive glob | OPEN (P2-H, tier 2) | FIXED-AT `9fda3db`: `DASHBOARD_GLOB = "dashboards/**/*.json.tftpl"` (`:129`), `test_a_dashboard_one_directory_down_is_read` (`:412`); the vacuity defence pins EXACT sets — `EXPECTED_DASHBOARDS`, `EXPECTED_SERIES` (all 38 metric-shaped references, delta named on failure) and the gate dict (`test_the_guard_actually_reads_every_metric_family` `:172-207`); `234603b` fixed the pin's own hole (an undotted family arrived with a delta of `set()`). Independent red on the exact-set pin: iac r3 V5 (an entry the surface never addresses) — IR3-19. The `.tpl`-off-the-glob sub-point (probe a3) is unchanged by design ("closes an authoring hole, not a deployment one": `cloudwatch_dashboards.tf` names all eight templates). Note: the row said "recursive glob is cheap"; the file says the same and did it | validator `:129`; test `:70-207` | tree |
| IF-11 | `validate_metric_vocabulary.py:449` markdown code spans only | OPEN (P2-I, tier 2) | FIXED-AT `9fda3db`: prose between code spans is scanned, gated on `_LOOKS_LIKE_PROMQL` (`:1041-1060`); `234603b` closed the false positive the first form had (the quoted-name pass ran ungated, so "llm_usage_total" in a sentence failed — found by the `9fda3db` reviewer; `test_ordinary_prose_in_a_text_widget_is_not_read_as_a_query` `:364`, `test_prose_that_is_not_a_query_is_left_alone` `:434`). This row's probe a5 is mutation `a-selector-moved-out-of-backticks-into-prose-bypasses-the-dialect-rule` (`:628`). Implementer-proved on the final form; no independent red recorded — pending r4 | validator `:1041-1060`; test ids | tree |
| IF-12 | `validate_metric_vocabulary.py:503` `service in text` substring | OPEN (P2-J, tier 2) | FIXED-AT `9fda3db`: `_word()` with look-arounds excluding `\w` and `-` (`:710-724`); `234603b` stopped excluding `.` (the first form hid a sentence-final "automation-worker." — found by the `9fda3db` reviewer). `test_a_gated_service_name_is_matched_as_a_word_not_a_substring` (`:321`). Implementer-proved; no independent red on the final form — pending r4 | validator `:710-724` | tree |
| IF-13 | `alarms.tf:207-213` `LedgerWriteFailures` ungated on a dark signal | OPEN (P2-K, tier 2) | SUPERSEDED-BY G.6: copilot-mro `3978073b` created and wired `agent.ledger.write_failures` (inventory `wired`, `_emitted_series.py:131`; `telemetry.py:1441` at `735f8213`), so iac `5e476e0` rewrote the alarm as `WIRED 2026-09-20, retrieval unproved` and DELETED the "inert, not quiet" paragraph rather than rewording it (`alarms.tf:408-421`). The row's "milder — INSUFFICIENT_DATA not green" premise is REFUTED-BY `9fda3db`: PromQL alarms have a two-state contributor model, a missing series sits GREEN (CP 10b "BENIGN WAS WRONG"; confirmed by the `9fda3db` reviewer's re-fetch). No `var.ledger_signal_wired` was built and none is needed now. SEE `claims-E-deployment-and-iac.md` I3 | `alarms.tf:408-421`; copilot-mro `3978073b` | tree |
| IF-14 | `alarms.tf:222-231` `TelegramTurnFailureRate` ungated, no bot in this root | OPEN (P2-K, tier 2) | REFUTED in premise / ACCEPTED-AS-DEBT: same two-state refutation as IF-13 (it sits GREEN, not INSUFFICIENT_DATA — severity is higher than filed, tier unchanged). `9fda3db` stated it at the definition ("GREEN HERE MEANS NOTHING IN THIS ROOT", and the description says so; `alarms.tf:432-450`) and DELIBERATELY left it ungated — a PromQL alarm has no `treat_missing_data` knob, so gating one unproved emitter means gating every one; the controller accepted that reasoning (CP 10b). Still ungated at HEAD; iac still deploys no telegram-bot (`grep telegram *.tf` → alarms.tf, cloudwatch_dashboards.tf only) | `alarms.tf:432-450`; CP 10b | tree; ledger |
| IF-15 | `dashboards/agent-turn-explorer.json.tftpl` two text widgets, billed | OPEN (P2-L, tier 2) | UNCHANGED (checked): both widgets still `type: "text"`; last commit `5e476e0` (state-note wording only); `cloudwatch_dashboards.tf:18` still prices $3/dashboard-month past the first three. STILL OPEN; no owner question was asked. SEE `claims-E-deployment-and-iac.md` I6 | tree | tree |
| IF-16 | `dashboards/llm-agents.json.tftpl` Bedrock `SEARCH` exact dimension-set | ASSERTED (P2-M, tier 2) | UNCHANGED (checked): widget identical (`:20-21`); `check_namespace_metric` (`:906-921`) still checks name membership and dimension PRESENCE only; no Bedrock wiring in any `.tf` (the one hit is a comment, `cloudwatch_dashboards.tf:12`); `global.*` inference-profile publication unprobed. The shared spec is now consistent (copilot-mro `95ca0e29`, `CATALOGUE.md:218-222`). STILL OPEN as filed | tree | tree |
| IF-17 | `alarms.tf:336-337` both worker alerts on one switch | SETTLED (P0-2 fix, tier 1) | UNCHANGED (checked): `alarms.tf:597-598` two comprehensions on `var.automation_worker_deployed`; `validate_alarms.py:99-119` `WORKER_GATED_MAPS` + `WORKER_GATE`; the four named mutations still in `test_validate_alarms.py`; iac r3 measured the suite green at six commits. SETTLED stands (implementer mutations; this file's probe a6 was the independent attack) | tree; IR3-27 | tree |
| IF-18 | `alarms.tf:378, 394` clean destroy on `true → false` | SETTLED (structure) / OPEN (never planned) | UNCHANGED (checked): `for_each = merge(local.log_count_alarms, local.worker_run_error_alarms)` at `:639`/`:655`, `LOG_COUNT_FOR_EACH`/`LOG_FILTER_FOR_EACH` pins at `validate_alarms.py:84,120`; `dev.tfvars:130` `automation_worker_deployed = false`. Still never planned: every later review banned terraform (r3: "no terraform"), sheet **C3** (`terraform init -upgrade`; the local lock is aws 5.100.0 against `~> 6.43`) is the workstation prerequisite, and nothing is pushed so CI's plan has never run on this branch | tree; sheet C3 | tree |
| IF-19 | `dashboards/{service-overview,telegram-bot,shift-optimizer}` every selector converted | SETTLED counters/gauges; OPEN 8 histogram families | SUPERSEDED in part: the counters/gauges half stands (validator + CI). The histogram half is FIXED-AT `9fda3db`/`234603b` for OPERATOR (`histogram_count`/`histogram_sum`/`histogram_quantile`; Route RED and Token throughput were the two the first fix missed; 0 `sum by (le` selectors at HEAD) and remains a documented bet for NAME (sums suffix, B1a — OWNER-OWED). The "no leftover oss-dialect spelling anywhere in iac" property CHANGED BY RULING: M-LEGACY-PANELS `d52e8b8` put 15 born-`_total` legacy names + `document_hub_processing_duration_seconds` on the aws surface by design, exempted exact-name only (`FAMILY_SUFFIXED_INSTRUMENTS` `:254`, `UNIT_SUFFIXED_INSTRUMENTS` `:221`) — iac r3 IR3-19/IR3-20 SETTLED tier 0 (V3, V4, V5, V7 red, independent). "Every converted name resolves to a real emitter" is still hand-pinned (`EXPECTED_SERIES`), the cross-repo derivation DEFERRED (§6 "Deferred from Phase G") | `9fda3db`, `234603b`, `d52e8b8`; `claims-iac-r3.md` IR3-19/20 | tree; packet |
| IF-20 | `dashboards/platform-health.json.tftpl` collector-log widget → text | ASSERTED (P1-6/P1-7, tier 1) | UNCHANGED (checked) for the claim: widgets 1, 2 and 6 are `text`, 3-5 `log`; the collector-log reachability half is still unmutated. The board since gained nine legacy panels in one text widget (`d52e8b8`, IR3-22) and its header was corrected at `56e7673` (r3 P3-6: the "NO Prometheus suffix" sentence now scoped to `otelcol_*` and naming the legacy row; a guard requires any such header on a born-suffix board to name the exception — `test_a_no_suffix_claim_names_the_born_suffix_exception` `:222`). `p1-7-a-worker-widget-loses-its-state-note` still at `:575` | tree; `claims-iac-r3.md` IR3-22/25 | tree |
| IF-21 | `validate_metric_vocabulary.py:435-465` `expression` fields dialect-checked | SETTLED (guard fix, tier 1) | UNCHANGED (checked): mutation `a-live-promql-metric-widget-escapes-the-dialect-rule` at `:597`; `check_dialect` `:870-904`. SETTLED stands (implementer mutation; this file's 65-green run was a measurement) | tree | tree |
| IF-22 | copilot-mro `CATALOGUE.md:187` `ThrottledCount` in the shared spec | OPEN (contradiction, tier 1) | FIXED-AT copilot-mro `95ca0e29` (implementer): `CATALOGUE.md:218-222` at `735f8213` reads "The metric is `InvocationThrottles`; AWS publishes no `ThrottledCount`", with the `SEARCH` form. Prose, no guard. SEE `claims-E-deployment-and-iac.md` cross-file #4 | copilot-mro tree; `git log -S'InvocationThrottles'` → `95ca0e29` | tree |
| IF-23 | copilot-mro `aws-profile.md:11,13` `duration_count` / `ThrottledCount` | OPEN (contradiction, tier 1) | FIXED-AT copilot-mro `95ca0e29`: `:11` teaches `{"http.server.request.duration"}` with `histogram_count()` and names `http.server.request.duration_count` as "a series the endpoint does not store"; `:13` `InvocationThrottles` by `ModelId`, "there is no `ThrottledCount`". Prose, no guard | copilot-mro tree | tree |
| IF-24 | copilot-mro `aws-profile.md:56,183` + `CATALOGUE.md:588` "suffix is an open B1a item" | OPEN (P0-B, tier 2) | FIXED-AT iac `9fda3db` for the CONTRADICTION, exactly as this row asked ("restore the iac warning, not edit them to agree"): iac restored the RE-VERIFY (IF-4) and the two documents were then NARROWED, not flipped, at copilot-mro `95ca0e29` — `aws-profile.md:74`, `:200-208` and `CATALOGUE.md:502`, `:650` now say "settled for histogram SHAPE only … the NAME question for monotonic sums is still genuinely open; the only worked AWS example is a gauge". The three files agree. The QUESTION (does CloudWatch suffix sums) is OWNER-OWED — B1a canary, nearest sheet line C2; until it runs `CollectorTelemetryAbsent` can still page forever from the first armed apply | copilot-mro tree at `735f8213`; `alarms.tf:363-383` | tree |
| IF-25 | commit message; `alarms.tf:44`; guard `:75` citation drift | OPEN (P2-N, tier 2) | FIXED-AT `9fda3db` for every in-tree cell: `research 04 §10 "Open probes / uncertainties"` (`alarms.tf:44-45`, validator `:143`); the `docs/plans/...` paths say "the docs repo … workspace-relative, iac has no docs/ tree" (`alarms.tf:21-22`, validator `:598-599`); README "six" → eight. "Ten mutation proofs" sits in `2d493c8`'s immutable message; `234603b`'s message records 14 → 17 (26 `id="` at HEAD). The `CATALOGUE.md:184` cell is REFUTED-BY the `9fda3db` message ("did not reproduce — no line-numbered citation of that file exists anywhere in iac"; verified: `git grep ':184' 2d493c8` and `'CATALOGUE.md:'` both empty — the citation lived in the fix pass's handback prose, not the tree) | `9fda3db` message; `git grep` at `2d493c8` and HEAD | tree |

**Counts by state now (25 rows):** FIXED-AT 15 (IF-1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 22, 23, 24, 25) ·
SUPERSEDED 3 (IF-8 by M-ALARM-DENOMINATOR, IF-13 by G.6, IF-19 in part by M-LEGACY-PANELS) · REFUTED in
premise / ACCEPTED-AS-DEBT 1 (IF-14) · UNCHANGED (checked) 6 (IF-15, 16, 17, 18, 20, 21). Of the 15 FIXED,
an INDEPENDENT red is recorded for IF-7 (r3 V7), IF-10 (r3 V5) and IF-19's legacy half (r3 V3/V4/V5/V7);
IF-9 is independently MEASURED (r3 IR3-27); the rest are implementer-proved, several after the `9fda3db`
reviewer's attack on the earlier form.

### Open claims now, tier 2 first

1. **IF-1 / IF-2 residue (tier 2, OWNER-OWED C2)** — the two API pagers are correct under the documented
   shape but rest on `histogram_count()` being in CloudWatch's PromQL subset, which no page names; the
   "fails LOUDLY" claim was withdrawn, so if it is not, both sit GREEN. One `PutMetricAlarm` with a bogus
   function settles it. No guard covers operator-vs-instrument-kind; a future bare `rate({histogram})`
   would pass the validator.
2. **IF-3 / IF-4 / IF-24 residue (tier 2, OWNER-OWED B1a)** — whether CloudWatch suffixes MONOTONIC SUMS
   is documented for gauges only. Every `otelcol_*` alarm and every `increase({counter})` rides that gap,
   and `CollectorTelemetryAbsent` (critical) pages forever from the first armed apply if the answer is yes.
   The warning is back in iac and the two copilot-mro documents agree; the probe has not run.
3. **IF-14 (tier 2, ACCEPTED-AS-DEBT)** — `TelegramTurnFailureRate` green-on-nothing in this root, ungated
   by accepted reasoning and stated at its definition.
4. **IF-16 (tier 2, OPEN)** — Bedrock `SEARCH` schema exactness on a `global.*` inference-profile namespace,
   guard checks presence only; unprobed.
5. **IF-15 (tier 2, OPEN)** — `agent-turn-explorer` is two paragraphs of prose billed at $3/month.
6. **IF-10 / IF-11 / IF-12 (tier 2, FIXED, implementer-proved on the final form)** — the reach fixes hold
   at HEAD with named mutations; the only independent attack was on the `9fda3db` form (which found
   residual holes, closed at `234603b`). Pending r4.
7. **IF-8 (tier 1, SUPERSEDED, build gated)** — ruled (denominator, keep `notBreaching`), but the four
   patterns are known-dead (B1b) and the denominator waits on C2 so it is not minted with the same dead
   selector; `alarms.tf:155` still says "OWNER RULING OWED".
8. **IF-9 residue (tier 1)** — `terraform-apply.yaml` runs no guard, no `fmt -check`, no `validate`; an
   apply dispatched without a preceding plan is ungated. Owner's call, on no sheet line. And CI has never
   actually run on this branch (nothing pushed).
9. **IF-18 (tier 1, OPEN)** — never planned; sheet C3 first.
10. **IF-19 residue (tier 1)** — `EXPECTED_SERIES` is a hand-pinned copy of the emitters; the published
    inventory that would derive it is §6 "Deferred from Phase G".
11. **IF-20 (tier 1, ASSERTED)** — the collector-log reachability claim behind the text panel is unmutated.
12. **IF-5 residual (tier 1, DEFERRED)** — an ungated `notBreaching` alarm on a DEPLOYED service whose
    filter can never match still passes check 5.

**Closed since filing:** IF-1..IF-7, IF-9..IF-13, IF-22..IF-25 (with the residues above).

### Cross-file staleness (rows in OTHER packet files that contradict this file's rows now; listed, not fixed)

1. `claims-E-deployment-and-iac.md` E30 (re-stated 2026-09-22) records copilot-mro `CATALOGUE.md:122, :559,
   :561, :609, :646` still teaching `histogram_quantile(…, sum by (le) (rate({"…duration"}[…])))` and a bare
   `rate({"http.server.request.duration"}[5m])` (`:79`, `:123`) in the AWS dialect — confirmed at `735f8213`.
   That is this file's P0-A shape, FIXED in iac and REGENERATING from the shared spec both dialects are
   authored from — the same "fixed the instance, left the source" defect this file filed for `ThrottledCount`.
   E30 is the only packet record of it; no row files it as an iac-side obligation, and iac's validator cannot
   reach that file.
2. `README.md` lists this file at 22 rows; the table carries 25. A count discrepancy at filing, not a
   contradiction of any row; the totals section will need the real number.
3. `claims-iac-r3.md`'s "Open claims" list (IR3-03, 07, 08, 11, 14, 17, 23, 25, 26) predates its own fix pass
   (`d86b378..74346bb`, ledger Addendum 154: `d86b378`, `9bb3c3d`, `37f82c4`, `0a31a72`, `4afc68f`, `013c9ae`,
   `74346bb`, `56e7673`, `d2c7aac`) and is stale in the FIXED direction; pending r4 re-states it. Same tree,
   not this file's rows.
4. `claims-phase6-dashboards.md` rows 39, 40, 41, 43 and row 21 — re-stated there 2026-09-22 to the same
   commits this section names (`9fda3db`, `2d493c8`, G.6); no contradiction, recorded so the auditor need not
   diff them.
5. The iac tree itself against the plan: `alarms.tf:155-167` "OWNER RULING OWED -- is `notBreaching` the
   right treatment" is stale against §4a-bis M-ALARM-DENOMINATOR (ruled 2026-09-22). Prose, unguarded;
   the lane that would fix it is idle until C2.

### Could not trace

- Whether the `9fda3db` reviewer's claims table was ever filed as a packet file: ledger CHECKPOINT 10c/11b
  hold the review and its triage in prose; no `claims-iac-r1`/`r2` exists (the E-file records the same gap).
- An independent red on the FINAL (`234603b`) form of check 5, the prose scan and `_word`: the `9fda3db`
  reviewer attacked the `9fda3db` form, iac r3 aimed at `013dc89..d52e8b8`, and r4 is running.
- A decision-sheet line for the ungated `terraform-apply.yaml`: `owner-decisions-2026-09-22.md` has none;
  the ledger (CP 10b/11b) says "Owner's call" and stops there.
- `claims-iac-r4.md` (`d52e8b8..74346bb`): did not exist at the HEADs above; nothing here depends on it.
