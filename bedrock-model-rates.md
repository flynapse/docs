# Bedrock Claude Rates & Access — Reference

**Captured: 2026-08-07** · Account `183784237171` · Region `ap-south-1` (Mumbai, dimension prefix `APS1`)

Rates below are **not** from the public pricing page — they were read from this account's own AWS
Marketplace agreement rate cards, which is what actually gets billed. Re-derive them any time with the
commands in [Re-deriving these numbers](#re-deriving-these-numbers).

---

## 1. Rate card — per 1M tokens, USD

Global inference profile (`global.*`), Standard tier. This is the tier we run on.

| Model | Input | Output | Cache read | Cache write 5m | Cache write 1h |
|---|---|---|---|---|---|
| Fable 5 | $10.00 | $50.00 | $1.00 | $12.50 | $20.00 |
| Opus 5 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| Opus 4.8 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| Opus 4.7 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| Opus 4.6 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| Opus 4.5 | $5.00 | $25.00 | $0.50 | $6.25 | $10.00 |
| **Sonnet 5** | **$2.00** ⚠️ | **$10.00** ⚠️ | $0.20 | $2.50 | $4.00 |
| Sonnet 4.6 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 |
| Sonnet 4.5 | $3.00 | $15.00 | $0.30 | $3.75 | $6.00 |
| Sonnet 3.5 / 3.5v2 / 3.7 (apac) | $3.00 | $15.00 | — | — | — |
| Haiku 4.5 | $1.00 | $5.00 | $0.10 | $1.25 | $2.00 |
| Haiku 3 (legacy, apac) | $0.25 | $1.25 | — | — | — |

⚠️ **Sonnet 5 is on introductory pricing that ends 2026-08-31.** From 2026-09-01 it reverts to
**$3.00 / $15.00** — i.e. parity with Sonnet 4.6. Anything sized against $2/$10 must be re-costed then.

### Modifiers

| Modifier | Effect |
|---|---|
| Batch tier | **−50%** on input and output (e.g. Opus $2.50 / $12.50) |
| Regional endpoint instead of global | **+10%** on everything (Opus becomes $5.50 / $27.50, cache read $0.55) |
| Cache read | 0.1× input rate |
| Cache write, 5-minute TTL | 1.25× input rate |
| Cache write, 1-hour TTL | 2× input rate |

**Always prefer `global.*`.** It is 10% cheaper than the regional endpoint, and in ap-south-1 it is the
only option for the current-generation models anyway (no in-region, no APAC geo profile).

Fable 5 has **no regional dimension at all** — global only.

### Tier availability

Opus 5 supports **Standard + Batch only**. No Priority, Flex, or Reserved. Older models (Opus 4.5/4.6,
Sonnet 4.5/4.6, Haiku 4.5) do carry Reserved TPM dimensions, e.g. Opus 4.6 at $0.30/TPM/month input
(1-month commit, global) and $0.27 (3-month).

---

## 2. Model IDs — the `-v1` suffix is inconsistent

There is no rule here; copy the exact string. Getting it wrong yields Bedrock
`400 "invalid model identifier"`, which in an agent loop surfaces as a silent capability failure rather
than a crash.

| Model | Exact Bedrock ID |
|---|---|
| Opus 5 | `global.anthropic.claude-opus-5` |
| Opus 4.8 | `global.anthropic.claude-opus-4-8` |
| Opus 4.7 | `global.anthropic.claude-opus-4-7` |
| Opus 4.6 | `global.anthropic.claude-opus-4-6-v1` |
| Opus 4.5 | `global.anthropic.claude-opus-4-5-20251101-v1:0` |
| Fable 5 | `global.anthropic.claude-fable-5` |
| Sonnet 5 | `global.anthropic.claude-sonnet-5` |
| Sonnet 4.6 | `global.anthropic.claude-sonnet-4-6` |
| Sonnet 4.5 | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Haiku 4.5 | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |

Note the trap: Opus 4.6 keeps `-v1`, Opus 4.7 onward drops it; Sonnet 4.5 keeps the dated `-v1:0` form,
Sonnet 4.6 drops it entirely. A previously-recorded bug in the workout resolver came from assuming
`global.anthropic.claude-sonnet-4-6-v1` existed — it does not.

Get the live list rather than guessing:

```sh
AWS_PROFILE=bedrock AWS_REGION=ap-south-1 aws bedrock list-inference-profiles --max-results 200 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId,'anthropic')].[inferenceProfileId,status]" \
  --output text | sort
```

---

## 3. Access is gated by a Marketplace agreement, not by IAM

A model can be `ACTIVE` in `list-inference-profiles` and still refuse to invoke. That listing is the
**global catalog**, not your account's entitlement — do not use it as an access check.

The real check is `get-foundation-model-availability`:

```sh
AWS_PROFILE=bedrock AWS_REGION=ap-south-1 \
  aws bedrock get-foundation-model-availability --model-id anthropic.claude-opus-5
```

```
agreementAvailability.status  ← the one that gates access
authorizationStatus           ← IAM
entitlementAvailability
regionAvailability
```

`agreement=NOT_AVAILABLE` with everything else `AVAILABLE`/`AUTHORIZED` means the AWS Marketplace
agreement was never accepted. Invoking then returns
`AccessDeniedException: <model> is not available for this account` — which reads like an IAM or region
problem and is neither.

**To enable a model** (pay-per-token, no commitment):

```sh
TOKEN=$(aws bedrock list-foundation-model-agreement-offers --model-id anthropic.claude-opus-5 \
          --query 'offers[0].offerToken' --output text)
aws bedrock create-foundation-model-agreement --model-id anthropic.claude-opus-5 --offer-token "$TOKEN"
```

Accepted 2026-08-07 for: Opus 5, Opus 4.8, Opus 4.7, Sonnet 5, Fable 5.
Already held before that: Opus 4.6, Opus 4.5, Sonnet 4.6, Sonnet 4.5, Haiku 4.5, Haiku 3, Sonnet 3.x.

### The agreement is necessary but NOT sufficient — check the TPM quota

This is the trap that cost the most time on 2026-08-07. After accepting the agreement, **every**
control-plane signal reported success:

```
agreementAvailability = AVAILABLE      authorizationStatus  = AUTHORIZED
entitlementAvailability = AVAILABLE    regionAvailability   = AVAILABLE
marketplace agreement   = ACTIVE       modelLifecycle       = ACTIVE
```

…and `converse` still returned `AccessDeniedException: <model> is not available for this account`, in
both `ap-south-1` and `us-east-1`, across the global / geo / base model-ID forms, for 75+ minutes.

The actual cause was a **Service Quotas throughput limit of 0 TPM** on the newly-subscribed models:

| Quota | Value | Code |
|---|---|---|
| Global cross-region TPM — Opus 4.6 (working) | 3,000,000 | `L-3DCCFAA4` |
| Global cross-region TPM — Opus 5 | **0** | `L-D73B1244` |
| Global cross-region TPM — Opus 4.8 | **0** | `L-4FCE27C7` |
| Global cross-region TPM — Opus 4.7 | **0** | `L-34152C1D` |
| Global cross-region TPM — Sonnet 5 | **0** | `L-DD84E5CA` |
| Global cross-region TPM — Fable 5 | **0** | `L-D06938E7` |

A zero TPM quota surfaces as **`AccessDeniedException`, not `ThrottlingException`** — which is why it
reads as an entitlement problem and sends you down the wrong path. All of these are `Adjustable: true`,
so the fix is a Service Quotas increase request, not a Marketplace or IAM change.

```sh
# Diagnose — always run this before concluding a model is "not enabled"
AWS_PROFILE=bedrock AWS_REGION=ap-south-1 aws service-quotas list-service-quotas \
  --service-code bedrock --max-items 400 \
  --query "Quotas[?contains(QuotaName,'tokens per minute')].[QuotaName,Value,Adjustable,QuotaCode]" \
  --output text | sort

# Request an increase
aws service-quotas request-service-quota-increase \
  --service-code bedrock --quota-code L-D73B1244 --desired-value 3000000
```

**Enabling a new Bedrock model is therefore a two-step process:** accept the Marketplace agreement, then
raise the TPM quota off zero. Verify with a real `converse` call — no control-plane status is sufficient
evidence on its own.

---

## 4. Re-deriving these numbers

The AWS Pricing API (`aws pricing get-products --service-code AmazonBedrock`) only carries first-party
AWS models plus legacy Claude 3 — Anthropic's current models bill through Marketplace and are absent
from it. Use one of these instead.

**Model not yet subscribed** — the offer carries the full rate card:

```sh
AWS_PROFILE=bedrock AWS_REGION=ap-south-1 \
aws bedrock list-foundation-model-agreement-offers --model-id anthropic.claude-opus-5 \
  --query 'offers[0].termDetails.usageBasedPricingTerm.rateCard[].[dimension,price]' --output text | sort
```

**Model already subscribed** — the offers list comes back empty; read the accepted agreement instead:

```sh
AWS_PROFILE=bedrock aws marketplace-agreement search-agreements --catalog AWSMarketplace --region us-east-1 \
  --filters '[{"name":"PartyType","values":["Acceptor"]},{"name":"AgreementType","values":["PurchaseAgreement"]}]' \
  --query 'agreementViewSummaries[].[agreementId,proposalSummary.resources[0].id,startTime]' --output text

AWS_PROFILE=bedrock aws marketplace-agreement get-agreement-terms --agreement-id <agmt-...> --region us-east-1 \
  --query "acceptedTerms[].usageBasedPricingTerm.rateCards[].rateCard[?starts_with(dimensionKey,'APS1_')].[dimensionKey,price]" \
  --output text | sort
```

Two dimension-naming conventions exist and both appear in this account:

- newer: `APS1_input_tokens_global_standard`
- older: `APS1_InputTokenCount_Global`

Filter on both. `marketplace-agreement` has **no ap-south-1 endpoint** — call it in `us-east-1`.
Marketplace product IDs (`prod-*`) do not resolve to titles via `marketplace-catalog describe-entity`
under our permissions; map an agreement to a model by its acceptance date and price shape, or read the
product ID off the model's AWS doc page (Opus 5 = `prod-if5d653ow7ehg`).

---

## 5. Known issues in our code as of this date

### 5a. `utils/utils/llm.py` priced all Opus at legacy rates — FIXED 2026-08-07

`BEDROCK_PRICING["opus"]` was `{input: 15.0, output: 75.0, cache_write: 18.75, cache_read: 1.50}` —
Opus 4.1/Opus 3 rates — and `resolve_bedrock_pricing` matched on the bare substring `opus`, so every
current Opus resolved to it. **Every Opus cost figure this module emitted before this date is 3× too
high**, including the measured run costs recorded in plan files. Treat historical Opus cost numbers in
`docs/plans/*` as inflated; divide by 3 for a current-tier comparison.

Fixed by making the resolver version-aware: current Opus (4.5–5) → $5/$25, legacy (`opus-4-1`,
`opus-4-0`, `3-opus`) → the old $15/$75, plus new entries for Fable ($10/$50), Sonnet 5 (intro
$2/$10) and Haiku 3 ($0.25/$1.25). Sonnet 5 previously had no entry and fell through to the generic
$3/$15. `utils/tests/test_llm_usage_totals.py` updated to match, with a new regression test
(`test_resolve_bedrock_pricing_separates_current_from_legacy_generations`) pinning each generation
boundary — including that `sonnet-5` must not swallow `sonnet-4-5`. 14/14 pass.

**Diary note:** the `sonnet-5` intro rate is hardcoded and expires 2026-08-31. On 2026-09-01 delete the
`sonnet-5` entry so it falls through to `sonnet` ($3/$15).

### 5b. Sonnet 5 migration is blocked on more than the model string

Sonnet 5 removes `budget_tokens`, rejects non-default `temperature`/`top_p`/`top_k` with a 400, and
turns **adaptive thinking on by default** where Sonnet 4.6 ran with thinking off. Consequences for our
call sites:

| Site | Issue |
|---|---|
| `copilot-mro/copilot_mro/app/services/parsers/image_transcription.py:73,421` | Classifier calls with `max_tokens=8` and no `thinking` param. On Sonnet 5 thinking is on by default and would consume the entire budget — the classification comes back empty, every image falls through to `_CLASSIFY_FALLBACK_KIND="text"`, and all images route to the Opus transcriber. That silently discards the measured 69% Opus-call saving. Needs `thinking={"type": "disabled"}` (legal on Sonnet 5 at effort ≤ `high`) or a much larger `max_tokens`. **Silent cost regression, not a crash.** |
| `copilot-mro/copilot_mro/app/config.py:425,428,438` | Plain default model strings (techpub sweeper, techpub assessor, workout resolver). Swap is mechanical, but the ~30% tokenizer increase means token budgets and compaction triggers need re-baselining. |

### 5c. Any Opus 4.6 → Opus 5/4.8/4.7 migration is blocked by `temperature=0`

`copilot-mro/copilot_mro/app/services/agent_sdk/tools/workout/workout_gate.py:394,519` pass
`temperature=0` to `_GATE_MODEL = "global.anthropic.claude-opus-4-6-v1"`. Non-default sampling
parameters are **removed** from Opus 4.7 onward and return a 400. The parameter must be deleted (not
set to a different value) before that gate can move off 4.6.

---

## 6. Cost-relevant behaviour changes worth knowing

- **Prompt-cache minimum drops to 512 tokens on Opus 5**, from 4,096 on Opus 4.6. Our agent_sdk prompts
  mostly sit under the 4,096 floor, so caching silently no-ops today. At identical $5/$25 per-token
  rates, this is the single largest available cost reduction from an Opus 5 move — the model swap is
  free, the caching is what pays.
- **New tokenizer** on Opus 4.7+ / Sonnet 5: the same text yields roughly 1×–1.35× the token count of
  Opus 4.6. Per-token price is unchanged, so re-baseline `max_tokens`, compaction triggers, and cost
  dashboards with `count_tokens` rather than applying a flat multiplier.
- **Fast mode and task budgets do not exist on Bedrock.** Both are Claude-API-only.
- Opus 5 on Bedrock is **zero-data-retention by default**.
