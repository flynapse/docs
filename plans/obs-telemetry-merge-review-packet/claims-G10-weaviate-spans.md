# Claims packet — Phase G item G.10, span half (utils)

Independent adversarial review, 2026-09-20. The implementer's own self-commissioned reviewer never
returned and nothing from it reached anyone, so this pass assumes **no prior review exists** and
re-derives everything from the source. Read-only throughout: the working tree was never modified, and
every mutation ran against a copy in the session scratchpad, restored and md5-verified after each run.

| phase | repo | worktree | branch | commit | uncommitted |
|---|---|---|---|---|---|
| G.10 (span half) | utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `21fc319` (guard, 18 tests) | `utils/weaviate_service.py`, md5 `48a04069690fb513d3fe3d03be32c9ad` |

**The subject changed on disk during this review.** The brief named commit `431aefc` and a 299/48 diff.
While mutation-testing was in flight the implementer amended the commit to `21fc319` (the guard file
gained 121 lines: an `interrupted` outcome, a `Counter`-based one-span-per-door assertion, an
assertions-performed counter, three new floors, a `len(_UNTRACED_BY_DESIGN) == 8` pin, and five more
sub-API names in the AST scan) and grew `weaviate_service.py` to 371 changed lines (the `finally`
stamp, and `db.response.affected_rows` renamed to `weaviate.affected_objects`). **Every finding below
is measured against the post-amendment state named in the table above.** Several holes this pass would
otherwise have reported were closed by that amendment; they are recorded in "What I tried to break and
could not" rather than as findings. The five that survive it are P1-1.

Lane, as run:

```
PYTHONPATH=/home/aditya/Code/utils-obsm:/home/aditya/Code/copilot-mro-obsm:/home/aditya/Code/core-obsm \
POSTGRES_DB=copilot_mro_test DEBUG=false \
poetry -C /home/aditya/Code/api run pytest -o addopts="-ra --strict-markers" \
  /home/aditya/Code/utils-obsm/tests
```

| scope | result | rootdir |
|---|---|---|
| `tests/unit/observability` | 133 passed | `/home/aditya/Code/utils-obsm` |
| `tests/` (whole repo) | **1252 passed** | `/home/aditya/Code/utils-obsm` |

1252, not the brief's 1249: the amendment added three tests. `rootdir` confirms the merged tree ran,
not the pre-merge sibling at `/home/aditya/Code/utils/tests`.

`utils/observability/metrics.py` was confirmed **out of scope and untouched by this work**:
`weaviate_service.py` imports `csv`, `hashlib`, `json`, `re`, `threading`, `traceback`, `contextlib`,
`functools`, `typing`, `urllib.parse`, `weaviate`, `loguru`, `opentelemetry.trace`, `.config`,
`.embedding_service`, `.observability` and `.tenancy_context` — nothing from `metrics`. The guard file
contains zero occurrences of the string `metrics`. It is a separate uncommitted pass awaiting its own
review and nothing here touches it.

**Tier 0 is empty**, tenth file running. §2.3a's tier-0 category is "mechanical, additive, doc-only
**and** mutation-proved". Every mutation-proved row here protects a consequential decision — an error
classification an operator pages on, a privacy property, a dashboard dimension — so none qualifies; and
every mechanical row (the attribute renames, the dead parameter) has no guard of its own.

---

## Findings, ranked

### No P0

I looked for one and did not find one. The twenty spans that exist today are correct: every `return` in
all twenty traced methods is preceded by a `_finish_weaviate_span` (all 34 call sites checked against
the return map), no span attribute carries content, and `record_exception=False` holds under mutation.
The serious findings are all either (a) a guard that cannot hold the property it is named for, or (b) a
*missing* classification that makes a real failure read as a success — consequential, but not a present
break.

---

### P1-1 — The "no untraced door" guard has five proven blind spots, and one of them is the shape of the file's own flagship method

`tests/unit/observability/test_weaviate_client_spans.py:604-650`. The scan matches an `ast.Attribute`
whose own `attr`, or whose parent's `attr`, is one of ten names. Five constructions of a *new untraced
Weaviate door*, added as a method on `class Weaviate`, leave the entire 31-test suite green:

| mutation | new method body | result |
|---|---|---|
| `MD_backup` | `h = self.get_collection(n, tenant=tenant)` → `h.backup.create(backup_id=…, backend=…)` | **31 passed** |
| `MF_delegate` | `return self._hybrid_search(collection_name=n, query=q, tenant=tenant)` | **31 passed** |
| `MF_patchwrap` | `return self._patch_objects_remove_properties(n, props, tenant=tenant)` | **31 passed** |
| `MF_getclient` | `return self.get_client().collections.delete(n)` | **31 passed** |
| `MF_getattr` | `return getattr(h, "query").fetch_objects(limit=1)` | **31 passed** |

Controls: `ME_query` (`h.query.fetch_objects`) and `MD_aggregate` (`h.aggregate.over_all`) each fail
`test_no_untraced_door_into_weaviate`, so the scan is working — it is the coverage that is short.

Three of these are not hypothetical shapes:

1. **`backup` is a real weaviate-v4 collection sub-API** — `weaviate/collections/collection/sync.py:89`,
   `self.backup: _CollectionBackup`. The amendment widened the scan from four sub-APIs to nine plus
   `iterator`; v4 exposes **eight** collection sub-APIs (`aggregate`, `backup`, `batch`, `config`,
   `data`, `generate`, `query`, `tenants`) and `backup` is the one left out.
2. **`hybrid_search` is itself a pure delegating wrapper.** Its body (`:1240-1275`) calls
   `_describe_weaviate_search`, `self._hybrid_search(...)` and `_finish_weaviate_span` — and touches
   none of the ten names. I re-implemented the scan independently: `touching` has 27 members and
   `hybrid_search` is **not** one of them. So an *undecorated twin of the file's flagship method* is
   invisible to the guard; it survives only because the C1-era
   `test_weaviate_hybrid_search_emits_a_content_free_client_child_span`
   (`test_nonagent_storage_client_spans.py:162`) pins that one name by hand.
3. **`get_client` (`:438`) is a public accessor whose entire job is handing out the raw client.**
   Exempting it is correct for the method, but it means any future method that reaches Weaviate
   *through* it rather than through `self.client` is unseeable.

The scan also never leaves `class Weaviate` in one file, which matters because the estate has
production Weaviate round trips outside it: `utils-obsm/utils/migrate_weaviate_collection.py` has six
in the **same repo and package** (`:90` `collections.create`, `:134` `query.fetch_objects`, `:171`
`data.insert_many`, `:178` `data.insert`, `:221` `collections.exists`), and
`copilot-mro-obsm/copilot_mro/app/services/weaviate_tenancy.py:722/738/741` creates and lists tenant
partitions on the raw client, with a docstring stating that bypass is deliberate. The guard file's
first line says "every door into Weaviate opens a client span". That is true of `class Weaviate` and
false of Weaviate; the sentence should say which.

**What an operator sees:** nothing — that is the point. On the next incident the dependency board's
Weaviate row under-counts calls and is missing whichever operation was added since, and CI is green.

---

### P1-2 — Two swallowed-truncation paths report `success`; one is a fourth instance of the pattern the implementer catalogued as three

The `partial` vocabulary exists because "a self-detected failure that never sets the outcome is worse
than no outcome at all". Three sites were found and closed. Two more were not:

1. **`export_data_to_csv` (`:1926-1941`)** catches `"maximum results exceeded"` / `"pagination params"`,
   logs four `WARNING` lines, `break`s the pagination loop, and writes a short CSV. Probe result:
   `operation.outcome = success`, `status = StatusCode.OK`, `db.response.returned_rows = 1` for an
   export the server truncated. Structurally identical to the bulk deletes: the failure is detected,
   swallowed, and the caller is handed a number.
2. **`drop_properties_from_schema` (`:2304`)** consults only `errors`. `_patch_objects_remove_properties`
   also stops early on `hit_limit` and on the `max_total_results = 10000` guard (`:2137-2145`), both
   with only a `logger.warning` and neither reaching `errors`. Probe result with `hit_limit=True` and
   `errors=[]`: `operation.outcome = success`.

**What an operator sees:** a green span for a data export or a schema drop that silently processed a
fraction of the collection — and, because `db.response.returned_rows` reports what was *fetched*, a row
count that corroborates the lie.

---

### P1-3 — Caller-side bugs that never reach Weaviate are ERROR client spans, now on twenty doors instead of one, and there is a second class the record does not mention

The decorator's `except Exception` (`:183-185`) cannot distinguish a failure of the dependency from a
failure to call it. Two probes, both confirmed:

- `svc.query_objects("SomeMTCollection", tenant="not a legal tenant name!!")` →
  `weaviate.query_objects`, `operation.outcome=error`, `StatusCode.ERROR`,
  `error.type=WeaviateTenancyError`. Raised at `get_collection:495`, before any socket.
- `svc.drop_properties_from_schema("c", tenant="t")` with neither `properties_to_drop` nor
  `keep_properties` → `weaviate.drop_properties_from_schema`, `operation.outcome=error`,
  `StatusCode.ERROR`, `error.type=ValueError`. Raised at `:2229/:2233`, **before the first
  `get_collection` call**, so not one byte leaves the process.

G.24(2) records only the tenancy case, and describes it as "pre-existing behaviour of `hybrid_search`;
the implementer kept it rather than invent a divergence, which was right". The first half is right and
the framing understates twice: the **`ValueError` argument-validation class is new with G.10** (the
method was untraced before), and the blast radius went from one door to twenty.

**What an operator sees:** the dependency board's Weaviate error-share panel goes red during a rollout
of *application* code, and they page the infrastructure team about a healthy cluster.

---

### P1-4 — `weaviate.vector_search` encloses an Azure OpenAI round trip and there is no child span anywhere to attribute it

`vector_search:1592` calls `embedding_service.generate_embedding(query)` inside the span, after
`_describe_weaviate_search` and `get_collection`. `_hybrid_search:1327` does the same.
`utils/embedding_service.py` has **zero** OpenTelemetry instrumentation — no `get_tracer`, no
`start_as_current_span`, no `tracing.span` — and its round trip is `self.client.embeddings.create` to
**Azure OpenAI** (`:183`, `:312`, `:499`). So a `db.system="weaviate"` CLIENT span's duration includes
a third-party SaaS call, and the trace offers nothing beneath it to drill into.

This was inherited from `hybrid_search`, which is why the implementer propagated rather than diverged —
defensible. But it was propagated to the operation that generates an embedding most often, and recorded
nowhere.

**What an operator sees:** "Weaviate p95 = 2.4 s". They open the trace, find one span, investigate the
Weaviate cluster, find it healthy, and never learn the time was Azure's.

---

### P2-1 — One production call emits two `db_system="weaviate"` CLIENT spans on first use, and the connect latency lands twice in the same series

Probe: one `query_objects` on a fresh `Weaviate` with `_client is None` emits
`['weaviate.connect', 'weaviate.query_objects']`, connect parented to `query_objects`. The
`_initialize_connection` docstring defends the parent *containing* connect time — "That is the honest
reading: the caller waited for it" — and that is right. It does not address the consequence on the
board: `dependencies.json:73` counts calls with
`sum by (db_system, server_address) (rate(traces_spanmetrics_calls_total{span_kind="SPAN_KIND_CLIENT"}[5m]))`,
so one operation is two calls; `:57` makes a connect failure two errors; and `:25`
(`histogram_quantile(0.95, sum by (le, db_system) …)`) takes the ~215 ms connect as its own sample *and*
again inside the parent's duration, in the same `weaviate` bucket. The amendment's new
`assert set(emitted.values()) == {1}` cannot see this: `_service()` pre-sets `_client`, so the census
never triggers a lazy connect.

### P2-2 — The `db_system="weaviate"` series' meaning changed and no consumer was updated

The series went from one query shape to twenty. Nothing on the board breaks Weaviate down by
`db.operation`, so one p95 now mixes a by-id get, a hybrid search, a once-per-process connect and two
CSV exports whose span duration includes local file writing. The panel descriptions are already wrong
in both directions: `dependencies.json:18` still says the DB-p95 panel covers "(postgresql, redis)"
while Weaviate has been in it since C1, and `:34` says the non-DB panel covers "Weaviate, S3, Bedrock
endpoints" while its `db_system=""` filter **excludes every Weaviate span**. Dashboards are another
repo and out of this slice's tree; the claim belongs on the record either way. (Cosmetic, same file:
`legendFormat` `{{db_system}}{{server_address}}` concatenates with no separator, so Weaviate renders as
`weaviatelocalhost`.)

### P2-3 — Three vocabularies for "how many things"

`db.response.returned_rows` (6 operations), `search.result_count` (3 search operations), and
`weaviate.affected_objects` / `weaviate.schema_property_count` / `weaviate.requested_property_drops`
(4 operations). The mid-review rename off `db.response.affected_rows` improved semantic precision —
schema properties are genuinely not returned rows — but an operator asking "how many rows did Weaviate
return" must now union three names and know which belongs to which door. `update_object_property`
(`:1108-1113`) now carries no count at all, deliberately and correctly, so the answer for it is "there
isn't one".

### P2-4 — `_finish_weaviate_span` writes to `get_current_span()`, so a misplaced call stamps someone else's span

Pre-G.10 `hybrid_search` held its span as `with … as operation` and wrote to that handle. The refactor
traded that for an ambient lookup (`:132`, `:148`) at 34 call sites across 20 method bodies. Nothing
fails if one ever escapes its decorator — it silently sets `operation.outcome` and, for anything outside
`_WEAVIATE_NON_ERROR_OUTCOMES`, `StatusCode.ERROR` on whatever span is current, which under
`/rag/stream` is an agent or HTTP server span. Correct today (verified at all 34 sites); no guard
covers the property.

### P2-5 — The raw-exception-text surface in this file is about twenty-two sites, not the two recorded

G.24(1) names the two `f"Failed to delete {obj.uuid}: {e}"` lines (`:907`, `:1023`). The file also
carries **nineteen** `logger.*(f"…: {traceback.format_exc()}")` sites, plus `{e}` at `:456` and `:1595`.
The file's own comment at `:430` states exactly why `traceback.format_exc()` is the same leak: *"a
rendered traceback's last line is `Type: message`"*. Captured live during a probe: `query_objects`
logged the full `WeaviateTenancyError` message, including the caller's tenant string and absolute
module paths, at ERROR. Leaving them unfixed here was right — out of the span half's scope, and G.20
constrains how they must be repaired. Recording the count as "two" is not.

### P2-6 — `_weaviate_span`'s `attributes` parameter is dead

`:74-78` accepts `attributes` and documents its merge behaviour; all twenty decorator sites call
`_weaviate_span(operation, tenant=…)` and none passes it. Documented behaviour nothing exercises.

### P2-7 — The floors are honest now, but they are close to decorative for their stated job

The brief asked what happens if five decorators are removed. Answer: it fails, and not because of the
floor. `_drive_every_operation` asserts `set(calls) == set(instrumented)`, and
`test_no_untraced_door_into_weaviate` asserts `touching - instrumented - _UNTRACED_BY_DESIGN == set()`;
between them 19 of 20 are caught regardless of any threshold. The exception is `hybrid_search`, which
the scan cannot see (P1-1). So `_MINIMUM_INSTRUMENTED_OPERATIONS = 18` earns its keep only against the
failure it was written for — a helper that returns `[]` — which it does do. The amendment's
`_MINIMUM_SCANNED_METHODS = 24` (actual 27) and `_MINIMUM_TENANT_BEARING_OPERATIONS = 18` (actual 18)
are both well set.

### P2-8 — G.23(2)'s premise does not survive reading the expressions

G.23(2) says `s3.download` without `db.system` "remains an empty-`db_system` series" on the two panels
grouping by `(db_system, server_address)`, and calls that "the literal complaint in G.10's own plan
line". Measured from `dependencies.json:57` and `:73`: those panels group by the **pair**, with
`legendFormat` `{{db_system}}{{server_address}}`, so S3 gets its own named series keyed by its endpoint
host — not an empty-label collapse. And `s3_service.py:222` already documents the omission as
deliberate: the DB-p95 panel "filters `db_system != ""`" and so "drops S3 entirely", which is correct —
S3 is not a database, and it is present in the non-DB panel where it belongs, carrying
`rpc.service="S3"` (`:217`) and `server.address` (`:223`). Adding `db.system` to `s3.download` would be
a semconv abuse adopted to satisfy a misreading. **G.23(2) should be re-scoped or dropped; G.23(1) is
exactly right** — `peer.service` is promoted at `tempo.yaml:61` and asserted at
`copilot-mro-obsm/tests/integration/otel/test_tempo_span_metrics.py:34`, and a search of every `.py` in
`utils-obsm`, `copilot-mro-obsm`, `core-obsm` and `api-obsm` finds **zero** production emitters.

---

## What I tried to break and could not

Kept separate from what I did not test.

- **The exemption set, all eight entries.** Every one verified, and one against the vendor's own
  source. `get_collection` is right because `collections.get()` and `with_tenant()` both carry the
  docstring *"This method does not send a request to Weaviate"*
  (`weaviate/collections/collections/base.py:37`, `weaviate/collections/collection/sync.py:154`) — the
  only round trip it can trigger is the lazy connect, which has its own span.
  `__init__`/`_ensure_connection`/`client`/`get_client` touch `_client` for bookkeeping and delegate the
  one round trip to the traced `_initialize_connection`. `close()` tears down sockets this process
  already owns. `_hybrid_search` and `_patch_objects_remove_properties` do round-trip, but only under a
  traced parent. **No exemption is wrong.** The escape hatch two of them create is P1-1, which is a
  different claim.
- **A twenty-first door among the class's members.** I enumerated all thirty members of `class Weaviate`
  independently before looking at theirs and found none missed. The two members in neither set —
  `get_embedding_service` (constructs the Azure client; no Weaviate) and `_build_hybrid_search_filters`
  (pure `Filter` construction) — are correctly neither traced nor exempt.
- **A traced method with a return path that never finishes its span.** All 34 `_finish_weaviate_span`
  call sites checked against every `return` in all twenty methods. None escapes.
- **The `miss` / `not_found` asymmetry.** Real, and reusing `miss` is consistent rather than convenient:
  `s3_service.py:28` is `frozenset({"success", "miss"})` and `:275` is
  `outcome = "miss" if quiet else "not_found"`, so `not_found` genuinely IS an error there. Weaviate's
  by-id lookups have no quiet/loud caller distinction — they always return `None` — so `miss` is the
  only classification that maps.
- **Privacy on the trace pipe.** The complete exported attribute set is `db.system`, `db.operation`,
  `server.address`, `tenant.id`, `search.mode`, `search.requested_count`, `search.result_count`,
  `operation.outcome`, `error.type`, `db.response.returned_rows`, `weaviate.affected_objects`,
  `weaviate.schema_property_count`, `weaviate.requested_property_drops`. No collection name, object id,
  query text, property name or value, output path, or exception message. `tenant.id` is **not** in
  `tempo.yaml:59-64`'s promoted dimensions, so twenty doors carrying it mint no Prometheus series.
- **`record_exception=False` / `set_status_on_exception=False`.** Flipping `record_exception` to `True`
  fails four tests and, as the failure output shows, puts both `exception.message`
  (`auth failed for https://weaviate.internal:8080 key=AKIAEXAMPLE`) and `exception.stacktrace` on the
  span. The pin is load-bearing.
- **Every other classification in the vocabulary.** `degraded`, `conflict`, `miss`, empty-is-success,
  and `partial` at all three catalogued sites are each reachable and each mutation-proved (below).
- **A nested or delegating call producing a duplicate span, or `_finish_weaviate_span` landing on the
  wrong span.** Neither occurs today; `weaviate.connect` under `weaviate.query_objects` behaves exactly
  as documented.

## What I did not test

- **Anything live.** No Weaviate, Tempo, Prometheus or Grafana was contacted. Every dashboard judgment
  is read from the PromQL in
  `copilot-mro-obsm/deployment/observability-local/grafana/provisioning/dashboards/flynapse/dependencies.json`
  and from `tempo.yaml`.
- **`utils/observability/metrics.py`**, out of scope by instruction; confirmed untouched and not
  imported by this work.
- **Concurrency.** The `_init_lock` / span-parenting interaction under genuinely simultaneous first
  callers is reasoned from the code, not exercised.
- **Whether `bm25_search` / `vector_search` / `hybrid_search` can be truncated by
  `QUERY_MAXIMUM_RESULTS`** the way `export_data_to_csv` is. If they can, P1-2 has a third and fourth
  site; I did not trace their pagination.
- **`utils/migrate_weaviate_collection.py`'s six round trips** beyond confirming they exist and are
  untraced. Whether a migration CLI should appear on the dependency board is a judgment I leave to the
  owner.

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence it is right | Guard test | Mutation-proved? | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|
| G10-01 | utils | `utils/weaviate_service.py:156-204` | One shared `_traced_weaviate` decorator over twenty operations, name `f"weaviate.{operation}"` at `:111` | Nineteen doors emitted nothing; nineteen wrapper/private-body pairs would drift | Census drives all twenty and asserts the emitted name set equals the declared set, one span each | `test_every_weaviate_door_emits_one_client_span` | **yes** — `MF_delegate` / `MF_patchwrap` add an undecorated delegating door and the suite stays green (31 passed), so the census holds the twenty but not the twenty-first | 2 | G.10 | **OPEN** — census SETTLED, the "no new door" property is not (see G10-02) |
| G10-02 | utils | `tests/unit/observability/test_weaviate_client_spans.py:604-650` | AST source scan over `class Weaviate`, ten sub-API names, plus an 8-member exemption set with its size pinned | A hand-maintained list is what went stale and left nineteen doors untraced | Controls fire: `ME_query` and `MD_aggregate` each fail the guard | `test_no_untraced_door_into_weaviate` | **yes, and it fails the property** — five new untraced doors pass: `MD_backup` (`h.backup.create`), `MF_delegate` (`self._hybrid_search`), `MF_patchwrap` (`self._patch_objects_remove_properties`), `MF_getclient` (`self.get_client().collections.delete`), `MF_getattr` (`getattr(h,"query")`) — all 31 passed | 2 | G.10 | **OPEN** — P1-1 |
| G10-03 | utils | `utils/weaviate_service.py:102`, `:111-116` | `db.system`, `db.operation`, `server.address`, `tenant.id`; empty strings dropped alongside `None` | `server.address` is what gives Weaviate a named series; `""` would mint the empty-label series the attribute exists to prevent | Deleting `server.address` fails 3 tests; keeping `""` fails 1; changing `kind` to INTERNAL fails 3; renaming `tenant.id` fails 1 | `test_every_weaviate_span_carries_the_board_dimensions`, `test_connection_factory_opens_its_own_span`, `test_the_span_omits_the_host_when_there_is_none`, `test_weaviate_hybrid_search_emits_a_content_free_client_child_span` | **yes** — `MA` 3 failed / `MI` 1 failed / `MO` 3 failed / `MN` 1 failed | 1 | G.10 | **SETTLED** |
| G10-04 | utils | `utils/weaviate_service.py:71`, `:119-141` | `_WEAVIATE_NON_ERROR_OUTCOMES = {success, miss, degraded, conflict}`; outcome decides status, not the presence of an exception | Modelled on `s3_service.py:28`; a quiet miss marked ERROR once made the S3 error rate a function of cache hit rate | `s3_service.py:275` `"miss" if quiet else "not_found"` confirms the asymmetry; Weaviate has no quiet/loud distinction so `miss` is the only mapping | `test_an_absent_object_is_a_miss_not_an_error`, `test_a_degraded_health_check_is_not_an_error_span`, `test_an_unreachable_health_check_is_an_error_span`, `test_a_property_that_already_exists_is_not_an_error_span` | **yes** — `MH_miss` (miss→success) 1 failed | 1 | G.10 | **SETTLED** |
| G10-05 | utils | `utils/weaviate_service.py:917`, `:1054`, `:2304` | `partial` → ERROR for three bulk operations whose loops swallow per-object failures | A self-detected failure that never sets the outcome is worse than no outcome | All three reachable and each independently driven | `test_a_partial_bulk_delete_is_an_error_span`, `test_a_partial_drop_of_schema_properties_is_an_error_span`, `test_a_partial_contains_delete_is_an_error_span_but_a_dry_run_is_not` | **yes** — `MB` (add `partial` to the non-error set) 3 failed; `MJ_partial` (force `success`) 1 failed | 1 | G.10 | **SETTLED** for the three sites; see G10-06 for the two missed |
| G10-06 | utils | `utils/weaviate_service.py:1926-1941`, `:2137-2145` + `:2304` | **Not taken.** A server-truncated `export_data_to_csv`, and a `drop_properties_from_schema` stopped by `hit_limit` / `max_total_results`, both report `success` | — | Probe: truncated export → `outcome=success`, `StatusCode.OK`, `returned_rows=1`; limit-truncated drop → `outcome=success` | **none** | not recorded | 2 | G.10 | **OPEN** — P1-2 |
| G10-07 | utils | `utils/weaviate_service.py:183-185` vs `:495`, `:2229`, `:2233` | Pre-existing: any exception leaving the body is an ERROR client span, including caller-side errors raised before the socket | Divergence was not invented, which was right | Probe: bad tenant → `weaviate.query_objects` ERROR `WeaviateTenancyError`; bad arguments → `weaviate.drop_properties_from_schema` ERROR `ValueError`, before the first `get_collection` | **none** | not recorded | 2 | G.10 → G.24(2) | **OPEN** — P1-3; G.24(2) records only the tenancy class and omits that the ValueError class is new and the radius went 1 → 20 |
| G10-08 | utils | `utils/weaviate_service.py:1592`, `:1327`; `utils/embedding_service.py:183/312/499` | Inherited: the search span encloses query-embedding generation | `hybrid_search` already did this; diverging for one of three searches would be worse | `embedding_service.py` has zero `get_tracer` / `start_as_current_span` / `tracing.span`, and its round trip is Azure OpenAI | **none** | not recorded | 2 | G.10 | **OPEN** — P1-4 |
| G10-09 | utils | `utils/weaviate_service.py:186-201` | `finally` stamps `interrupted` + ERROR on a span left UNSET by a `BaseException` | `except Exception` misses `KeyboardInterrupt` / `SystemExit` / `CancelledError`; UNSET reads as neither success nor failure | The same `finally` would let a body that forgot to finish satisfy the UNSET assertion — closed in the same pass by asserting no census span carries `interrupted` | `test_a_baseexception_leaves_no_span_unset`, `test_every_weaviate_span_carries_the_board_dimensions` | **yes** — `MM_nofinally` (delete the `finally`) 1 failed | 1 | G.10 | **SETTLED** |
| G10-10 | utils | `utils/weaviate_service.py:114-115` | `record_exception=False`, `set_status_on_exception=False`; `error` read only for `error.type` | Exception text never reaches a span; type and frames only | Flipping it puts `exception.message` (`…key=AKIAEXAMPLE`) and `exception.stacktrace` on the span | `test_connection_failure_is_an_error_span_without_the_message`, `test_weaviate_hybrid_search_marks_and_reraises_failure`, `test_weaviate_failure_log_carries_frames_not_the_exception_text`, `test_weaviate_connect_failure_log_carries_frames_not_the_exception_text` | **yes** — `MC` 4 failed | 1 | G.10 | **SETTLED** |
| G10-11 | utils | `utils/weaviate_service.py` (span attribute set) | No collection name, object id, query text, property name/value or output path on any span | The trace pipe is read more widely than the caller's logs; a collection name is a tenant's identity here | Census asserts the exported attribute text contains none of the private collection, uuid, query or collection-list values | `test_no_weaviate_span_carries_tenant_content` | partially recorded — the guard is present and the property held under every mutation run, but no mutation targeted it directly | 1 | G.10 | **ASSERTED** |
| G10-12 | utils | `utils/weaviate_service.py:363-381` (traced `connect`) | The connection factory gets its own span, as a child of whichever operation triggered the lazy connect | The one door every operation passes through once; a slow-to-accept cluster should show here | Probe: one `query_objects` on a fresh client emits `['weaviate.connect','weaviate.query_objects']`, connect parented to the operation — so the board counts two calls and samples the ~215 ms twice in one series | `test_connection_factory_opens_its_own_span` | partially recorded — the span's existence and parentage are proved; the double-count is measured but unguarded, and the census cannot reach it (the fixture pre-sets `_client`) | 2 | G.10 | **OPEN** — P2-1 |
| G10-13 | utils | `dependencies.json:18/25/34/41/57/73` (consumer, other repo) | Unchanged: the `db_system="weaviate"` series now aggregates twenty query shapes where it measured one | Out of the span half's tree | Panel `:18` still says "(postgresql, redis)"; panel `:34` claims to cover Weaviate while `db_system=""` excludes it; no panel breaks Weaviate down by `db.operation` | **none** | not recorded | 2 | G.10 | **OPEN** — P2-2 |
| G10-14 | utils | `utils/weaviate_service.py:714/757/814/891/917/977/1054/1972/2012` vs `:1272/1527/1655` vs `:1828/2012/2307` | Three count vocabularies: `db.response.returned_rows`, `search.result_count`, `weaviate.*` | The mid-review rename off `db.response.affected_rows` was semantically right | An operator asking "rows Weaviate returned" must union three attribute names | **none** for the vocabulary as a whole; the zero-count case is guarded | `test_an_empty_result_set_is_a_success_with_a_zero_count` (resolves; covers `list_all_objects` and `query_objects` only) | not recorded | 2 | G.10 | **OPEN** — P2-3 |
| G10-15 | utils | `utils/weaviate_service.py:132`, `:148` (34 call sites) | `_finish_weaviate_span` / `_describe_weaviate_search` write to `get_current_span()` rather than a handle | A decorator cannot hand the body a span without changing twenty signatures | Correct at all 34 sites today; pre-G.10 `hybrid_search` used `as operation` and the refactor dropped that safety | **none** | not recorded | 2 | G.10 | **OPEN** — P2-4 |
| G10-16 | utils | `utils/weaviate_service.py:907`, `:1023`, plus 19 `traceback.format_exc()` sites and `:456`, `:1595` | Reported, deliberately not fixed | Out of the span half's scope; G.20 constrains the repair shape | The file's own `:430` comment states the leak; a probe captured `query_objects` logging a full `WeaviateTenancyError` message with the caller's tenant string and absolute paths | **none** | not recorded | 2 | G.10 → G.24(1) | **OPEN** — P2-5; G.24(1) records two of about twenty-two |
| G10-17 | utils | `utils/weaviate_service.py:74-78` | `_weaviate_span(attributes=…)` accepted and documented; no caller passes it | — | All twenty decorator sites call `_weaviate_span(operation, tenant=…)` | **none** | not recorded | 2 | G.10 | **OPEN** — P2-6 |
| G10-18 | utils | `tests/unit/observability/test_weaviate_client_spans.py:31/36/37`, `:581`, `:648` | Floors at 18 / 24 / 18 against actuals 20 / 27 / 18, and `len(_UNTRACED_BY_DESIGN) == 8` pinned | A helper returning `[]` would satisfy every per-span assertion by never running one | Removing decorators is caught by `set(calls) == set(instrumented)` and by the scan residue, not by the floor — except for `hybrid_search`, which the scan cannot see | `test_every_traced_weaviate_method_keeps_tenant_keyword_only`, `test_no_untraced_door_into_weaviate` | partially recorded — `@wraps` removal and the empty-set case are reasoned from the new assertions, not mutated | 2 | G.10 | **ASSERTED** |
| G10-19 | copilot-mro / utils | `tempo.yaml:61`; `copilot-mro-obsm/tests/integration/otel/test_tempo_span_metrics.py:34` | Reported as G.23(1): `peer.service` promoted and asserted, emitted by nothing | — | Zero matches for `peer.service` in any `.py` across `utils-obsm`, `copilot-mro-obsm`, `core-obsm`, `api-obsm` | `test_tempo_span_metrics.py` — **resolves, and certifies the promotion, not the emission** | not recorded | 2 | G.23(1) | **OPEN** — confirmed exactly as reported |
| G10-20 | utils | `utils/s3_service.py:217-227`; `dependencies.json:25/41/57/73` | Reported as G.23(2): `s3.download` has no `db.system` | — | **The premise is wrong.** Panels `:57`/`:73` group by the *pair* with legend `{{db_system}}{{server_address}}`, so S3 gets its own host-named series, not an empty-label collapse; `s3_service.py:222` documents the omission as deliberate and S3 is present in panel `:41` where it belongs | **none** | not recorded | 2 | G.23(2) | **OPEN** — P2-8; re-scope or drop |
| G10-21 | utils / copilot-mro | `utils/migrate_weaviate_collection.py:90/134/171/178/221`; `copilot-mro-obsm/.../weaviate_tenancy.py:722/738/741`, `tenant_partitions.py:153/155`, `operator_partitions.py:141/143`, `weaviate_boot_check.py:461` | Out of scope: Weaviate round trips outside `class Weaviate` emit no client span | The span half is scoped to `utils/weaviate_service.py` | `weaviate_tenancy.py:718-720` states the raw-client bypass is deliberate, so the guard's "every door into Weaviate" is true of the class and false of the dependency | **none** — the scan never leaves `class Weaviate` in one file | not recorded | 2 | G.10 | **OPEN** — tenant-partition creation is on the provisioning path and invisible to the board |

**Tier 0: empty.** Nothing here is mechanical, additive **and** doc-only while also being
mutation-proved.

---

## Open claims, tier 2 first

**Tier 2 — open**

1. **G10-02 (P1-1)** — five proven blind spots in `test_no_untraced_door_into_weaviate`. Add `backup`
   to the sub-API set; decide what to do about delegation through an exempt private body, which is the
   shape `hybrid_search` itself has (an `instrumented ⊆ touching` assertion would surface it today);
   and either scope the guard's first line to `class Weaviate` or extend the scan past it.
2. **G10-06 (P1-2)** — `export_data_to_csv` and `drop_properties_from_schema` report `success` for a
   truncated run. Two more `partial` sites, same pattern as the three already closed.
3. **G10-07 (P1-3)** — caller-side `WeaviateTenancyError` and `ValueError` are Weaviate ERROR spans on
   twenty doors. Needs the ruling G.24(2) asks for, with the ValueError class and the 1 → 20 radius
   added to the record.
4. **G10-08 (P1-4)** — `weaviate.vector_search` and `weaviate.hybrid_search` enclose an unspanned Azure
   OpenAI call. Either a child span in `embedding_service` or the generation moved outside the Weaviate
   span.
5. **G10-12 (P2-1)** — two `db_system="weaviate"` CLIENT spans per first call; connect sampled twice in
   one p95.
6. **G10-13 (P2-2)** — the series' meaning changed; two panel descriptions are already wrong and no
   panel breaks Weaviate down by operation.
7. **G10-14 (P2-3)** — three count vocabularies.
8. **G10-15 (P2-4)** — ambient `get_current_span()` at 34 sites, unguarded.
9. **G10-16 (P2-5)** — about twenty-two raw-exception-text sites recorded as two.
10. **G10-17 (P2-6)** — dead `attributes` parameter.
11. **G10-19** — `peer.service`: promoted, asserted, emitted by nothing. Confirmed as reported.
12. **G10-20 (P2-8)** — G.23(2)'s premise does not hold; re-scope or drop it.
13. **G10-21** — Weaviate round trips outside `class Weaviate`, including tenant-partition creation on
    the provisioning path.

**Tier 2 — asserted**

14. **G10-11** — content-free spans. Guard present, property held under every mutation run, no mutation
    aimed at it.
15. **G10-18** — floors and the `@wraps` reasoning, not mutated.

**Tier 1 — settled**

G10-03 (board dimensions), G10-04 (outcome vocabulary), G10-05 (`partial` at the three catalogued
sites), G10-09 (`interrupted`), G10-10 (`record_exception=False`).

**Tier 1 — open**

G10-01, whose census half is settled and whose "no new door" half depends on G10-02.

---

## Re-statement 2026-09-22

Appended by the R2 packet re-stater (Opus), read-only, nothing committed. Rows above are as filed.
**HEADs read:** utils-obsm `179cc6d` (obs-merge, clean) · copilot-mro-obsm `735f8213` · core-obsm
`b4d2c33` · api-obsm `e3ba207` · iac `74346bb`. **Column note:** the `Tier` column is §2.3a's; the
`P1-n`/`P2-n` tags in the Claim-state column are the reviewer's severity ranking, not a tier. The
recovered (self-commissioned) G.10 review is a DIFFERENT review from this one; its 27 rows are filed
as `G10R-nn` in `claims-utils-rounds.md`, whose "State 2026-09-22" cells were re-checked at utils
`849ca21` (2026-09-21 13:31). Four commits landed AFTER that check and matter here — `1a2680e`
(G10R-08), `5bb5ecb` (G10R-11/27), `f8e31ee` (G10R-19/20/23), `0aa29b1` — all in `4d86ae9..179cc6d`,
which is utils **review r8, in flight (lane #3)**: implementer proof only today.

**Rulings that superseded rows here (§4a-bis):** M-WEAVIATE-DOOR (trace the three copilot-mro
helpers → G.28 DONE `7f9e174b` + `4b5aea14` + `7839f0b2`), M-WEAVIATE-LEFTOVERS (a: exclude
`weaviate.connect` from the dependency panels → `dc4bf340`, iac `97cae73`; b: constant refusal
messages, ids as attributes → utils `f1ef9b9`, copilot-mro `e15f5962`), M-WEAVIATE-REFUSAL (refusals
quiet as `invalid_argument`; provisioning failures are errors; the never-raised utils subclass
deleted `26e7126`; a missing multi-tenant collection is a failure `2a8f2f48`), M-EMBED-INTERNAL (the
embedding span is INTERNAL → `604a061`), M-TRACEBACK (`failure_fields` everywhere).

| row # | claim state at filing | state now | evidence | source |
|---|---|---|---|---|
| G10-01 | OPEN (census settled, "no new door" not) | FIXED-AT utils `1cdebad` (G.29, implementer, 18 mutation proofs): the scan now closes transitively over `self.<method>()` and module-level helpers, so a delegating twin is in `touching`; `test_every_instrumented_method_is_a_door_the_scan_can_see` (`instrumented <= touching`, `:835-852`) — the one-liner this file proposed — was RED as proposed and adopted only after the closure made it true. Independent, without mutation: the G.24/G.29 reviewer probed the door shapes and could not break them (`claims-utils-rounds.md` G10R-12). The census half is unchanged (`test_every_weaviate_door_emits_one_client_span`, `:254`) | `1cdebad` message; utils-rounds G10R-12/G24-F16/F18 | tree; utils-rounds |
| G10-02 | OPEN (P1-1) | FIXED-AT `1cdebad` (implementer): all five blind spots closed — `backup` (and every v4 collection sub-API plus the client's own round trips `is_ready`/`is_live`/`is_connected`/`get_meta`/`connect_to_*`) in `_WEAVIATE_SUB_APIS` (`:600-629`), delegation through `self.` and module helpers, `getattr(x, "query")`, `get_client()`; the scan takes a source string and thirteen probe shapes test it directly (`test_the_source_scan_sees_every_door_shape`, `:822`). The "scan never leaves `class Weaviate`" limb is addressed by G.28 on the copilot-mro side (see G10-21). Independent without mutation: G.24 reviewer (utils-rounds G10R-13, G24-F16/F18/F20). Two limits stay DEFERRED in §6: a handle stashed on `self` (G24-F17) | `1cdebad`; utils-rounds; plan §6 "Deferred from Phase G" | tree; utils-rounds |
| G10-03 | SETTLED | UNCHANGED in property, EXTENDED in mechanism: `_WEAVIATE_SPAN_ATTRIBUTES` (`weaviate_service.py:102-119`, `f8e31ee`) now DECLARES every key the span may carry and its vocabulary (`db.system`/`db.operation` kept on the deprecated names on purpose — span-metrics promotes `db_system`; the Postgres/Redis instrumentors still emit it); a source scan pins declared = written and the retired names absent (`test_every_attribute_key_the_module_writes_is_declared…`, `:1456`; `test_the_deprecated_semconv_names_are_exactly_the_two…`, `:1466`; runtime subset `:1476`). Six mutations, implementer (`f8e31ee`, unreviewed — r8 in flight) | `f8e31ee` message; tree | tree |
| G10-04 | SETTLED | SUPERSEDED in mechanism, property intact: the local `_WEAVIATE_NON_ERROR_OUTCOMES` frozenset is GONE; the vocabulary is `utils.observability.outcomes.WEAVIATE_OUTCOMES` (an `OutcomeVocabulary`: non-error {success, miss, degraded, conflict, invalid_argument, truncated}, error {error, interrupted, partial}); an undeclared outcome collapses to `other` with an ERROR span (`1a2680e`, G10R-08 — the controller call "declare the closed vocabulary", ledger Add. 141). `miss` stays non-error; the `not_found` asymmetry argument this row made was upheld against the recovered review (utils-rounds G10R-25 REFUTED-BY this file). Five mutations, implementer; r8 in flight | `1a2680e`; `weaviate_service.py:29,203-213`; utils-rounds G10R-08/G10R-25 | tree; utils-rounds |
| G10-05 | SETTLED (three sites) | UNCHANGED for the three catalogued sites (tests at `:407/:441/:463` resolve) — and the meaning NARROWED: `partial` is now ERROR "for the swallowed-failure case alone"; a server result cap or a module-default `limit` is the new NON-error `truncated` (G10-06). `error.type` on a self-detected error is the outcome keyword (G24-F11) | `1cdebad`; utils-rounds G24-F10/F11 | tree |
| G10-06 | OPEN (P1-2) | FIXED-AT `1cdebad` (tests) + `6848ef7` (production, M-COMMIT) — but NOT as this row proposed: the two sites became `truncated` (non-error, `weaviate.result_truncated=True`), not `partial`/ERROR, on the argument that "the Weaviate error share became a function of how often someone exports more than 10k objects" (utils-rounds G24-F10, filed OPEN as a design ruling; no §4a-bis row). Guards: `test_an_export_the_server_cut_short_is_a_truncated_span` (`:1043`), `…_hit_the_local_ceiling…` (`:1063`), `test_a_drop_cut_short_by_the_result_cap…` (`:1109`); a refused patch outranks a cap (`:1130`). G24-F21 extended it to the module-default limits on list/query/delete (`:1263-1330`). Implementer mutations (removing `truncated` from the non-error set → 6 red); G24 reviewer independent without mutation. Residual accepted as debt: an export of EXACTLY 10,000 reads as truncated (G24-F22) | `1cdebad` message; utils-rounds G24-F10/F21/F22 | tree; utils-rounds |
| G10-07 | OPEN (P1-3) | SUPERSEDED-BY M-WEAVIATE-REFUSAL: caller-side refusals are `invalid_argument` — OK status, `error.type` set (`1cdebad`/`6848ef7`; `WeaviateArgumentError(ValueError)`, G24-F9); tenancy refusals `test_a_tenancy_bug_is_not_a_weaviate_failure` (`:911`), argument refusals `test_refused_arguments_are_not_a_weaviate_failure` (`:946`); the refusal/failure split (`0c60ba4`), then the never-raised utils subclass DELETED (`26e7126`) once utils r4 showed utils has no provisioning seat; a real dependency failure stays ERROR (`:1005`), a malformed response is not a caller bug (`:1022`). Independent: utils r5 U5-23 SETTLED tier 0 (utils-rounds G10R-09). Documented limit: `vector_search` refuses AFTER `get_collection`, so the lazy connect may have dialled (G24-F7 comment corrected; no test pins that case) | utils-rounds G10R-09, G24-F7/F9; §4a-bis M-WEAVIATE-REFUSAL; plan G.60 | tree; utils-rounds |
| G10-08 | OPEN (P1-4) | PARTLY FIXED / SUPERSEDED-BY M-EMBED-INTERNAL: `embedding_service.py` now opens its own span (`start_as_current_span(…, kind=SpanKind.INTERNAL)`, `:186-188`, `604a061`), so the trace has a child to attribute the Azure round trip to, and the dependencies board counts each embedding call once. NOT changed: `vector_search`/`hybrid_search` still generate the embedding INSIDE the Weaviate CLIENT span, so the Weaviate p95 still includes Azure time — the ruling chose the span kind, not the nesting. `5bb5ecb` made that nesting safe (a child span can no longer take the door's result, `:1365`). No independent review of `604a061` filed beyond the utils rounds (r4/r5 range) | `604a061`; `5bb5ecb`; §4a-bis M-EMBED-INTERNAL | tree |
| G10-09 | SETTLED | UNCHANGED (checked): `interrupted` is now in `WEAVIATE_OUTCOMES`' error set; `test_a_baseexception_leaves_no_span_unset` at `:423` | tree | tree |
| G10-10 | SETTLED | UNCHANGED (checked): `record_exception=False`, `set_status_on_exception=False` at `weaviate_service.py:163-164`; the four tests resolve | tree | tree |
| G10-11 | ASSERTED | UNCHANGED as a guard (`test_no_weaviate_span_carries_tenant_content`, `:313`); STRENGTHENED beside it: the attribute set is now a declared closed set (G10-03) and `test_every_weaviate_span_carries_only_declared_attributes` (`:1476`) refuses an undeclared key at runtime. Still no mutation aimed at the content-free property itself | tree | tree |
| G10-12 | OPEN (P2-1) | SUPERSEDED-BY M-WEAVIATE-LEFTOVERS (a): the span is KEPT and pinned (`test_the_first_call_nests_the_connect_span_inside_the_operation` `:1177`, `…_once_per_client…` `:1220`, `test_closing_the_client_re_arms…` `:1243`); the double count is removed at the CONSUMER — every fn-dependencies span-metrics selector carries `span_name!="weaviate.connect"` (copilot-mro `dc4bf340`, pinned in `test_grafana_dashboards.py`; r7 held it) and the aws Transaction-Search instruction says the same (iac `97cae73`, iac r3 reviewed). The "same series twice" measurement therefore no longer reaches a panel | plan G.39 PROGRESS; utils-rounds G10R-10; `dependencies.json:25/41/57/73` at HEAD | tree; packet |
| G10-13 | OPEN (P2-2) | STILL OPEN: `dependencies.json:18` still says "(postgresql, redis)"; `:34` still says "(Weaviate, S3, Bedrock endpoints)" while its `db_system=""` filter excludes every Weaviate span; `legendFormat` `{{db_system}}{{server_address}}` still unseparated; `CATALOGUE.md:138` still lists the values as `postgresql`, `redis`. Recorded as the copilot-mro follow-up "CATALOGUE `db_system` += weaviate" (ledger CHECKPOINT 35 queue). Corrected figure: the board went from ~2 live shapes to ~4, not 1 → 20 (utils-rounds G10R-02) | tree at HEAD; utils-rounds G10R-07 | tree |
| G10-14 | OPEN (P2-3) | FIXED-AT `f8e31ee` (G10R-20/23, implementer, r8 in flight): `search.result_count` is GONE — rows returned is `db.response.returned_rows` on every door; `search.requested_count` became `db.query.parameter.limit`, recorded at open from the door's signature for every cap-taking door (`test_every_door_that_takes_a_row_cap_records_it`, `:1492`); `search.mode` moved onto the decorator. The `weaviate.*` names (`affected_objects`, `schema_property_count`, `requested_property_drops`, `result_truncated`, `vector_fallback`) remain, now DECLARED as a distinct non-row vocabulary — two declared vocabularies, not three undeclared ones | `f8e31ee` message; `weaviate_service.py:102-119` | tree |
| G10-15 | OPEN (P2-4) | FIXED-AT `5bb5ecb` (G10R-11, implementer, r8 in flight): `_weaviate_span` holds its span in a `ContextVar` (`_WEAVIATE_SPAN`, `:75`) while the door is open and restores the outer value on close; `_finish_weaviate_span`/`_annotate_weaviate_span` write ONLY to that span and do nothing outside a door. Five tests (`:1352-1401`: helper outside a door, child span inside, nested door, raising door, another thread); two mutations each fail two of them | `5bb5ecb` message; tree | tree |
| G10-16 | OPEN (P2-5) | FIXED-AT `1cdebad` (tests) + `6848ef7` (production): the count was 29 sites, not ~22 (22 `traceback.format_exc()` + 7 `{e}`), plus a credential leak (`settings.weaviate_url` logged three lines above the docstring forbidding it), the user's BM25 query, and tenant document content `print()`ed in a dry-run delete — all found inside the hunk. The sweep now walks every `utils/**/*.py` with a shrink-only `LEAK_BACKLOG`. Independent: the G.24 reviewer could not break the conversion (utils-rounds G24-F1..F4, G10R-06). Plan G.24 `[x]` | plan G.24/G.29; utils-rounds | tree; plan |
| G10-17 | OPEN (P2-6) | FIXED-AT `f8e31ee`: the `attributes` parameter is now USED — `@_traced_weaviate("hybrid_search", attributes={"search.mode": "hybrid"})` and the two sibling searches (`:1427/:1634/:1737`); `_describe_weaviate_search` is gone | tree | tree |
| G10-18 | ASSERTED | UNCHANGED in state; the floors were re-set to truth-minus-one at `1cdebad` (`_MINIMUM_SCANNED_METHODS = 27`; G24-F19), `len(_UNTRACED_BY_DESIGN) == 8` still pinned (`:869`), and the `@wraps` reasoning is now a counted-assertions floor (utils-rounds G10R-04). No independent mutation of the floors recorded | tree; utils-rounds G10R-04/G10R-26/G24-F19 | tree |
| G10-19 | OPEN (G.23(1)) | STILL OPEN, confirmed at HEAD: `tempo.yaml:61` promotes `peer.service`, `test_tempo_span_metrics.py:34` expects it, and a search of every production `.py` in utils-obsm, copilot-mro-obsm, core-obsm, api-obsm and flynapse-otel finds `peer.service` only in two utils DOCSTRINGS (`embedding_service.py:158`, `dynamodb_service.py:118`) — no emitter. Plan G.23 box still `[ ]` | tree | tree; plan |
| G10-20 | OPEN (P2-8) | REFUTED (upheld): G.23(2) was STRUCK by the controller on this file's argument and re-verified ("Nothing is owed here") — plan G.23 `(2) ~~…~~ WRONG, and it was MY error` | plan G.23 | plan |
| G10-21 | OPEN | SPLIT. copilot-mro half FIXED-AT `7f9e174b` (M-WEAVIATE-DOOR: `collection_handle`/`collections_for`/`weaviate_connection` hand out traced handles; one seat for ~26 sites), `4b5aea14` (r6 P2-2 found `memory_index.py` bypassing two doors; raw handles swept) and `7839f0b2` (r7 P3-3: the admin door refuses every data surface; the sweep sees the other raw clients); independent: copilot-mro r6 (found the bypass) and r7 (held "no live Weaviate bypass"). Plan G.28 `[x]`, G.10 closed into it. utils half (`migrate_weaviate_collection.py`'s five raw calls) is ACCEPTED-AS-DEBT by declaration: exempt in `test_network_doors_are_traced.py:260` as "a one-off, operator-run collection migration script on no request path" and in `LEAK_BACKLOG` (implementer decision, no ruling) | plan G.28; copilot-mro-rounds R6-04/R6-11; utils-rounds G10R-01/G10R-14; tree | tree; packet |

### Open claims now, tier 2 first

1. **G10-13 (P2-2)** — two panel descriptions and the catalogue still misdescribe the `db_system`
   series after Weaviate joined it; queued, not done. (tier 2, OPEN)
2. **G10-19** — `peer.service` promoted and asserted, emitted by nothing; G.23(1) box open. (tier 2, OPEN)
3. **G10-08 (P1-4) residue** — the embedding round trip now has its own INTERNAL span, but it is
   still generated inside the Weaviate CLIENT span, so "Weaviate p95" still contains Azure time.
   M-EMBED-INTERNAL ruled the kind, not the nesting; nobody has asked whether the nesting is a
   defect. (tier 2, judgment)
4. **G10-06 (P1-2) as re-decided** — `truncated` is a NON-error; this file wanted `partial`/ERROR.
   utils-rounds G24-F10 files it "OPEN (a design ruling)"; no §4a-bis row. (tier 2, judgment)
5. **G10-11, G10-18** — ASSERTED, no independent mutation aimed at the content-free property or the
   floors. (tier 2 / tier 2)
6. **Implementer-only fixes awaiting utils r8 (lane #3):** G10-03's declaration (`f8e31ee`),
   G10-04's vocabulary (`1a2680e`), G10-14, G10-15, G10-17 — every one a tier-2 signal-contract
   change proven by the committing lane alone today.
7. **Tier 1, still open:** the `self`-stashed-handle scan limit (§6), the hybrid→BM25 fallback
   reporting `success` (§6; visible only as `weaviate.vector_fallback`), the exact-10,000 export
   false positive (accepted debt).

**Closed since filing:** G10-01, G10-02, G10-07, G10-12 (at the consumer), G10-16, G10-20, G10-21
(copilot-mro half); G10-05/G10-09/G10-10 unchanged and settled.

### Cross-file staleness (listed, not fixed)

1. `claims-utils-rounds.md` G10R-08 ("STILL OPEN: no ruling traced … none in a shared registry"),
   G10R-11 ("STILL OPEN at `849ca21`"), G10R-19, G10R-20, G10R-23 ("STILL OPEN at `849ca21`") and
   G10R-27 ("the span variable is still `operation`") are all overtaken by `1a2680e`, `5bb5ecb` and
   `f8e31ee` (2026-09-21 19:39–20:04, after that file's `849ca21` check). Its "Cross-file staleness"
   note about `claims-copilot-mro-rounds.md` G24-01 still stands (fixed `f1ef9b9`, U6-14).
2. `claims-copilot-mro-rounds.md` G24-02 (the tenancy-refusal classification ruling) — superseded by
   M-WEAVIATE-REFUSAL and its controller call (`26e7126`, `2a8f2f48`, `a9149afb`); check its state cell.
3. `claims-E-deployment-and-iac.md` "Recorded, not fixed #1" names `FAMILY_TOKEN`'s three prefixes;
   it now also matches the legacy prefixes (`9900a933`) — still not `traces_spanmetrics_*`, so the
   dependency panels G10-13 describes stay outside that lint.
4. Plan G.10 body still says "**20 operations** … the board went 1 → 20"; the corrected figure
   (~2 → ~4 live shapes) is in G.28's text and utils-rounds G10R-02.

### Could not trace

- An owner or controller ruling on `truncated` being non-error (G10-06's re-decision): recorded only
  as the implementer's argument in `1cdebad`'s message and G24-F10's "OPEN (a design ruling)".
- Whether utils review r8 (`4d86ae9..179cc6d`) has landed: `claims-utils-r8.md` did not exist at
  the time of this re-statement; every `f8e31ee`/`5bb5ecb`/`1a2680e` cell above is implementer-proved.
