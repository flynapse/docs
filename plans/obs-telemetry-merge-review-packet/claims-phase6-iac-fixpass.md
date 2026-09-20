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
