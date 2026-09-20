# Observability Rebuild — Outcome vocabularies and the span attributes nothing names

**Written 2026-09-20 at the `obs-telemetry-merge` fold, as item F.4 of
`docs/plans/observability-telemetry-merge-and-completion.md`.** It exists because the merge brought in a third
way of saying "how did this end" and about thirty span attribute keys that no catalogue, spec section, plan or
guard mentions. It is an **input to Task R.2** (approve the span/metric catalogue) and to **R.4** (orphan
analysis, merge plan G.1) — not a substitute for either.

Everything below was measured on the merged trees — `copilot-mro-obsm`, `utils-obsm`, `core-obsm` — on
2026-09-20, not read out of a plan. Where a document and the code disagree, the code is what is recorded here
and the document is corrected where it lives.

---

## 1. The two vocabularies, as they actually stand

| | agent runtime | non-agent operations |
|---|---|---|
| key | `agent.outcome`, `tool.outcome`, `subagent.outcome` | `operation.outcome` |
| where it is set | `agent_shared/pipeline.py` (turn span), `agent_shared/telemetry.py` (content-copy spans, metric attributes) | 46 call sites in 15 `copilot-mro` modules + 3 in `utils` |
| who ruled it | spec `2026-09-05-observability-rebuild-design.md` §6.3 — the metric attribute list | their Phase 1c signal table (`observability-rebuild-phase-1c-stable-nonagent.md` §2) |
| also a metric label | **yes** — exported as `agent_outcome`, `tool_outcome`, `tool_error_code` and queried by `fn-llm-agents`, `fn-agent-turn-explorer` and the agent alert rules | **no** — Phase 1c adds no instrument; these keys live on spans only |
| span status | **not set** for a handled failed turn, which is exactly why the attribute exists (`tests/integration/otel/_emitted_series.py`: a TraceQL `status = error` selector finds nothing) | **set explicitly**, OK or ERROR, at every terminal site |
| semconv | none of these are semconv keys | none, but the same spans also set semconv `error.type` |

They do not collide on a single span: no span carries both. What collides is the *reader's* expectation. An
engineer who has seen `agent.outcome` and then opens a parser span has no way to guess `operation.outcome`,
and the reverse is worse — `operation.outcome` looks generic enough to be the estate-wide key, and adopting it
on the agent spans would rename three live Prometheus labels.

### 1a. The values, which is where the real damage is

| key | values found in the merged tree |
|---|---|
| `agent.outcome` | `success`, `error` |
| `tool.outcome` | `success`, `failure` (the dispatcher's own literals) |
| `subagent.outcome` | dispatcher literals, same shape |
| `operation.outcome` | `success`, `error`, `skipped`, `partial`, `degraded`, `stale`, `needs_attention`, `miss`, `not_found`, `unavailable`, `completed`, `failed`, `exhausted`, `already_terminal`, `not_visible`, `refused` |

**The same event is spelled three ways across the estate: `error`, `failure`, `failed`.** This is not a
theoretical tidiness point — the code already carries a normaliser for it. `agent_shared/telemetry.py:1194`
computes `is_error` from `{"error", "failure", "failed"}`, and `_emitted_series.py` records that the failed-tool
panel must filter `tool_outcome="failure"` because `"error"` matches nothing. Every such normaliser is a place
where the next value is silently non-failing.

`operation.outcome`'s sixteen values are bare string literals at the call sites with no declared set anywhere.
The nearest thing to a registry is `utils/utils/s3_service.py`'s `_S3_NON_ERROR_OUTCOMES = {"success", "miss"}`,
a frozenset of the two values that must not set ERROR status — so a *new failure* value defaults correctly and a
new *non-failure* value (`cached`, `not_modified`) is wrong until somebody remembers the set. The merge plan
already records this as a Future Improvement (C1, 2026-09-20) and defers the fix to this reconciliation.

---

## 2. The call: `<subject>.outcome`, and the subject is what the span is about

**Both spellings stay. Neither is renamed.** The rule that makes them one vocabulary rather than two:

> The outcome key is `<subject>.outcome`, where `<subject>` is the noun the span or metric is about. The agent
> runtime's subjects are ruled by spec §6.3 and are `agent`, `tool`, `subagent`. Every other operation
> boundary uses the generic subject `operation`.

Why this way round, rather than picking a winner:

- **`operation.outcome` cannot take the agent spans.** `agent.outcome`, `tool.outcome` and `tool.error_code`
  are not just span attributes; they are exported Prometheus label names (`agent_outcome`, `tool_outcome`,
  `tool_error_code`) named in the spec's ruled metric list, queried by two Grafana boards, the agent alert
  rules and `iac/dashboards/llm-agents.json.tftpl`, and pinned by `_emitted_series.py`'s `KNOWN_LABELS`.
  Renaming them is a breaking change to consumers in three repos, bought for nothing.
- **`agent.outcome` cannot take the non-agent spans.** A parser command, an S3 download and a Document Hub
  sweep are not agents. Forcing the prefix would make `agent_*` mean "anything", which is precisely what
  `_emitted_series.py` exists to prevent — a board query selecting `agent_` tokens would start matching the
  ingest pipeline.
- **A single generic key is right for the eleven non-agent boundaries and wrong across the split.** One key is
  what lets a single query ask "which operations failed in the last hour" across S3, Weaviate, memory,
  Document Hub, Data Discovery, improvement and the parsers. The agent half does not want to be in that
  query: its failures are already a first-class metric with its own boards.

**Consequences that are part of the call, not follow-ups:**

1. **Declare the value set for each subject.** `success` for the good case; `error` for a failure, estate-wide,
   in every subject — which means `tool.outcome`'s `failure` and Data Discovery's `failed` are the two
   spellings that have to converge, not `error`. Anything else is a *named non-failure* (`skipped`,
   `partial`, `degraded`, `miss`, `refused`, `already_terminal`, …) and must be declared with the span, not
   invented at a call site.
2. **The declaration lives in code, not in a plan.** An enum or frozenset per subject, beside the recorder,
   checked by the same guard that checks the span/metric inventory. A value nothing checks is a hand-maintained
   list wearing a new name.
3. **`error.type` stays semconv and stays independent.** `<subject>.outcome` answers "what kind of ending";
   `error.type` answers "what went wrong". The non-agent spans already set both; the agent metrics set
   `error.type` from `tool.error_code` only on failure. That split is correct and should be stated rather than
   re-litigated.
4. **A new subject needs a consumer.** No new `<x>.outcome` without a catalogue row naming the panel, alert or
   query that reads it — see §4.

**This is a call, not an owner ruling.** It is recorded here for R.2's approval, in the style of the merge
plan's §4b. The owner may overturn it; what should not survive is the current state, where three spellings of
"failed" coexist and one of them is already known to match nothing.

---

## 3. Attribute spellings the merge introduced that no document names

Every key below is set on a span in the merged tree. None of them appears in the design spec, in
`deployment/otel/dashboards/CATALOGUE.md`, in any Grafana board or alert rule, in `base.yaml`, or in
`tests/integration/otel/_emitted_series.py`. Their only description anywhere is the Phase 1c signal table,
which is a plan, not a contract, and which is incomplete in at least one place (see §3a).

**Span names** (eleven, plus two in `utils`):
`mro.lifecycle.startup`, `mro.lifecycle.shutdown`, `memory.collection.ensure`, `memory.index.upsert`,
`memory.index.delete`, `memory.search`, `memory.reindex`, `memory.items.get_by_ids`, `document_hub.process`,
`document_hub.cleanup`, `data_discovery.job.run`, `improvement.run`, `improvement.stage`, `ingest.parse`;
`s3.download` and `weaviate.hybrid_search` in `utils`.

**Attribute keys**, grouped by what they are:

| group | keys | notes |
|---|---|---|
| outcome | `operation.outcome` | §1, §2 |
| semconv, correctly used | `error.type`, `db.system`, `db.operation`, `rpc.system`, `rpc.service`, `rpc.method`, `server.address`, `tenant.id` | the only keys here an outside reader can already interpret |
| lifecycle | `lifecycle.phase`, `lifecycle.failed_component`, `lifecycle.degraded_components`, `lifecycle.weaviate_partition_check_mode` | `lifecycle.degraded_components` is a **tuple**, so its cardinality is the power set of the component list |
| memory | `memory.type`, `memory.scope`, `memory.batch_size`, `memory.requested_count`, `memory.result_count`, `memory.processed_count` | counts on spans, deliberately not metric labels — this is what replaced the `item_count` metric label |
| search | `search.type`, `search.mode`, `search.requested_count`, `search.result_count` | `search.mode` is `utils`-side, `search.type` is memory-side: two keys, one idea |
| document hub | `document.kind`, `document.result_status`, `document.processing_attempt`, `document_hub.cleanup.scanned_count`, `.reconciled_count`, `.deleted_count`, `.retired_count`, `.error_count` | the cleanup counters are the only place a `<span>.<field>` prefix is used instead of a bare noun |
| data discovery | `job.id`, `job.status`, `job.attempt_number`, `data_discovery.level` | **`job.id` is unbounded** — harmless on a span, fatal if it ever becomes a metric label or a span-metrics dimension |
| improvement | `improvement.trigger`, `improvement.run.status`, `improvement.stage.name`, `improvement.stage.status`, `improvement.stage_count`, `improvement.error_count` | `improvement.run.status` and `operation.outcome` are set on the same span and can disagree |
| ingest | `parser.kind` | bounded by the eight approved commands |
| storage | `storage.downloaded_bytes` | success only |

Three things in that table are worth a decision rather than a note:

- **`job.id` and `lifecycle.degraded_components`** are the two unbounded-ish keys. Both are span-only today and
  the metric registry's `FORBIDDEN_ATTRIBUTE_KEYS` does not reach spans, so nothing stops either from being
  promoted later by a Tempo span-metrics dimension change. R.2 should mark them span-only explicitly.
- **`document.result_status` / `improvement.run.status` / `job.status` are a second outcome vocabulary** living
  beside `operation.outcome` on the same spans. They are domain statuses, not span outcomes, and the two can
  disagree; that is legitimate, but it needs saying once.
- **`search.type` vs `search.mode`** is the same concept named twice across a repo boundary.

### 3a. Where the Phase 1c signal table contradicts the code

`observability-rebuild-phase-1c-stable-nonagent.md` §2 declares the S3 outcome set as
`success, not_found, unavailable, error`. The code emits a fifth value, **`miss`** — `utils/utils/s3_service.py`
returns `miss` instead of `not_found` on the `quiet=True` cache-fallback path, and `miss` is one of the two
values that deliberately keep the span OK. A reader working from the plan would treat a cache miss as
unreachable. Corrected in that file at the fold.

---

## 4. Nothing consumes any of it

Measured on the merged tree: `grep -rl` over the whole of `copilot-mro/deployment/` for `operation.outcome`,
`operation_outcome`, and each of the sixteen span names returns **zero files**. No Grafana panel, no alert rule,
no recording rule, no collector transform, no catalogue row.

The Phase 1c signal table names `fn-dependencies` and `fn-platform-health` as the "primary consumer" of most of
these spans. Neither board mentions them. What the dependency board actually consumes is Tempo span-metrics,
whose promoted dimensions are fixed in `deployment/observability-local/tempo.yaml` as `db.system`,
`peer.service`, `server.address`, `rpc.service`, `url.template` plus the intrinsics. So:

- `weaviate.hybrid_search` sets `db.system=weaviate` and **does** reach the board's `db_system` panels.
- `s3.download` sets `rpc.service` and `server.address`, so it reaches the latency panel that groups by
  `(server_address, rpc_service)` — but the calls and error-rate panels group by `(db_system, server_address)`,
  and an S3 span has no `db.system`, so it lands in an empty-`db_system` series rather than a named one. This
  is the substance of merge plan **G.10**.
- The other fourteen span names reach nothing at all. They are searchable in Tempo and invisible everywhere
  else.

This is one half of the orphan analysis **R.4** owes (merge plan G.1): emitted signals with no consumer. It is
recorded here so R.4 starts from a measurement rather than re-deriving it.

---

## 5. What Task R.2 has to decide

1. Ratify or overturn the `<subject>.outcome` call in §2, and with it the convergence of `failure` and `failed`
   onto `error`.
2. Approve a declared value set per subject, and say where it lives in code and which guard proves it.
3. Rule `job.id` and `lifecycle.degraded_components` span-only, or bound them.
4. Decide whether the eleven non-agent span names earn catalogue rows and board panels, or are accepted as
   trace-search-only signals. "Trace-search-only" is a legitimate answer; leaving the Phase 1c table claiming
   board consumers that do not exist is not.
5. Fold `search.type` / `search.mode` into one key, or say why two.

Nothing here blocks the merge. All of it blocks calling the signal catalogue approved.
