# Claims packet — utils review round 8 (`4d86ae9..179cc6d`)

> **PARTIAL — PAUSED 2026-09-22 on the owner's request** (all lanes paused). Rows marked **verified** below were
> proved by this reviewer; rows marked **TODO** were not yet examined. Working notes, the pause record and the
> resume recipe are in `~/.claude/scratch/obs-merge/utils-review-r8/` (`PAUSED.md`, `notes.md`).

Independent adversarial review (Opus), 2026-09-22. It answers the implementer's response to review r7
(`claims-utils-r7.md`) and the packet-rounds open list (`claims-utils-rounds.md`: G10R-08, G10R-11/27,
G10R-19/20/23, R2-07, LA-01, LB-05, G18-04, G24-F12). Read-only against every real tree:

- each of the 19 commits (the base `4d86ae9` and the 18 in range) was `git archive`d into the private scratch
  `scratchpad/utils-review-r8/trees/<sha>/`, with flynapse-otel as an archive of `0960c16` (the real tree's HEAD;
  its one dirty file is a test);
- every probe and mutation ran against a scratch copy (`probe/`, `inv/{A..E}/`, `mut/`), never against
  `/home/aditya/Code/utils-obsm`; `mut/` was `diff -r` byte-identical to the `179cc6d` archive after every
  mutation, including the two interrupted at the pause (M7, M8 had already completed).

| repo | worktree | branch | range | commits | flynapse-otel under test |
|---|---|---|---|---|---|
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `4d86ae9..179cc6d` | 1a2680e, 5bb5ecb, f8e31ee, 8552ef2, 0e9b2a8, 0e93618, e991bb7, ebfcc68, 47a6c5b, 3269ce0, ac703e5, 1a42390, 380db38, 0aa29b1, 7e49946, ed1cd7d, 84502f1, 179cc6d | archive of `0960c16` (the -L sweep used the real tree at the same SHA) |

**How it was run.**

- **Lane:** `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider`,
  from the archive root; from 01:30 on, wrapped in `/home/aditya/Code/pytest-slot.sh --` (the standing rule).
- **Environment:** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`.
- **Paths:** `PYTHONPATH=<plugin dir>:<archive>:/home/aditya/Code/core-obsm:<fo-0960c16 archive>`; a private
  `PYTHONPYCACHEPREFIX` per run. A plugin (`r8report`) printed `rootdir`, `utils.__file__`, `flynapse_otel.__file__`.
- **Bare-archive full lane at HEAD `179cc6d` (`-n 2`):** 1914 passed, 13 skipped, 6 failed in 57 s, `rootdir` and
  `utils.__file__` in the archive. The 6 reds are `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py`
  (5) and `test_root_anchoring.py::test_sibling_repo_reaches_a_sibling_and_refuses_a_missing_one`, all of which
  need the real workspace (44/44 green when those two files are run read-only in the real tree). The 13 skips are
  the inventory's 9 `[copilot-mro]` cases (no sibling beside a bare archive), 3 `test_root_anchoring`, 1 cross-repo.
  1914 + 13 + 6 = 1933, the implementer's total.

**Every commit is green at its own HEAD, 0 skipped** (verified). `parallel-commits.sh -L -j 2`, serial pytest per
commit, `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` deselected (23 tests; symlink artefact,
44/44 in the real tree). Every commit carried exactly ONE red, the same test, a known `-L` symlink artefact:
`tests/unit/safety/test_no_provenance_laundering.py::test_the_scan_reaches_the_code_it_is_defending`
("scanned core-obsm (resolved) while core-obsm matches this worktree (symlink)") — 4/4 green read-only in the real
tree. `utils.__file__` was inside `ws-<sha>/utils-obsm/` at all 19 commits; `flynapse_otel` from `/home/aditya/Code/flynapse-otel` (= `0960c16`).

| commit | passed | skipped | commit | passed | skipped |
|---|---|---|---|---|---|
| 4d86ae9 (base) | 1834 | 0 | 1a42390 | 1886 | 0 |
| 1a2680e | 1841 | 0 | 380db38 | 1886 | 0 |
| 5bb5ecb | 1846 | 0 | 0aa29b1 | 1890 | 0 |
| f8e31ee | 1852 | 0 | 7e49946 | 1904 | 0 |
| 8552ef2 | 1856 | 0 | ed1cd7d | 1905 | 0 |
| 0e9b2a8 | 1858 | 0 | 84502f1 | 1908 | 0 |
| 0e93618 | 1869 | 0 | 179cc6d | 1909 | 0 |
| e991bb7 | 1872 | 0 | | | |
| ebfcc68 | 1873 | 0 | | | |
| 47a6c5b | 1876 | 0 | | | |
| 3269ce0 | 1877 | 0 | | | |
| ac703e5 | 1884 | 0 | | | |

(+1 artefact red +23 deselected each: base 1858, HEAD 1933 — the implementer's "1858 → 1933, 0 skipped" holds.)

**Ruff at each HEAD:** TODO (not run before the pause).

---

## Findings, ranked (so far)

**No P0, no P1 found so far.** The withholding layer holds against every spent-budget shape I planted, on every
sink; the renames hold inside utils; the estate list of undeclared families is EMPTY by my own census. The one
mechanism that gave way again is the AST inventory's label-key reader (P2-1: the third round of holes in the same
guard, the r6/r7 P2-6 class). Provisional verdict at the pause: **MERGE-CLEAN on what was examined**, pending the
TODO rows (mutation re-proofs M9–M28, ruff, the human-sink probe).

### P2-1 — The inventory's "every write that adds a key" is not every write: an alias, a closure or a helper adds a label the guard never checks (7e49946; r7 P2-6 residual, third round)

`_label_dicts` (`tests/unit/observability/test_legacy_family_inventory.py:203-268`) reads a name's keys from its
literal and from writes spelled on THAT name in THAT scope (`labels["k"] = v`, `.update`, `.setdefault`, `|=`).
Three decoys planted in `utils/llm.py` (scratch copies `inv/A`, `inv/B`, `inv/C`) each add `email` to a declared
family's labels and leave the inventory and bounding files GREEN (53 passed, 9 skipped); the control (`inv/E`, an
undeclared family emitted directly) is red:

| plant | inventory |
|---|---|
| A: `alias = labels; alias["email"] = email; svc.increment_counter("llm_requests_total", **labels)` | **silent** |
| B: `def add(): labels["email"] = email` (a closure), then `**labels` | **silent** (`_own_nodes` does not descend) |
| C: `_enrich(labels, email)` (a helper that mutates it), then `**labels` | **silent** |
| D: `getattr(svc, "increment_" + "counter")("llm_probe_leak_total", email=e)` | silent, declared (`_NOT_SEEN_BY_DESIGN`: a computed name) |
| E (control): `svc.increment_counter("llm_probe_leak_total", email=e)` | red (`test_every_emitted_family_is_declared[utils]`) |

The runtime shim drops an undeclared key on a declared family, so nothing exports — the consequence is exactly the
failure mode the file's docstring says it exists to catch (`:4-6`: "the shim drops it, the series silently loses a
dimension, and nothing says so"). Severity 2 (coverage), tier 1. Lesson "a second P1 in the same mechanism is a
design problem" applies in P2 form: an AST reader cannot enumerate every write to a dict OBJECT. **Fix (design, not
another patch):** read a name's keys from its literal only, and make ANY other mention of the name outside a
recognised read, a recognised write or the emission splat (an alias binding, a call argument, a nested-scope
reference) mark it unreadable — fail closed, reported.

### P3 findings (verified)

- **P3-1 — An exception held in another exception's `args` is not a chain link (pre-existing; severity 2).**
  `outer = RuntimeError("wrapped", inner); logger.error(f"failed: {outer.args[1]}", err=outer)` ships `inner`'s
  message on the JSON line and the OTLP body (exported and pre-boundary). `_every_link` walks `__cause__`,
  `__context__` and group members, never `args`; `_partial_quotes` quotes only STRING args. urllib3's
  `ProtocolError('Connection aborted.', RemoteDisconnected(...))` is this shape, though its own log lines quote the
  whole repr, which IS withheld. Declared only as "any other fragment". Fix: `_every_link` extends `pending` with
  `BaseException` instances found in `link.args`.
- **P3-2 — `_finish_weaviate_span` on another thread INSIDE a door writes nothing, and the door then reads
  `interrupted`/ERROR (5bb5ecb; severity 3).** Probed through a decorated door whose body does
  `executor.submit(_finish_weaviate_span, "success")`: the helper is a no-op on the worker (fresh context), the
  wrapper's `finally` stamps `interrupted`. `copy_context().run` and `asyncio.to_thread` carry it (outcome
  `success`). No regression (before the range the worker wrote to `INVALID_SPAN`), and no door does this today, but
  the docstring's "Outside a door, nothing" should say "or on another thread inside one, and the door then reads
  interrupted". Also: `_WEAVIATE_SPAN.reset(token)` RAISES `ValueError` when a door is exited in a different
  context than it was entered (OTel's own `detach` only logs) — no such site exists.
- **P3-3 — R2-07's per-test check cannot see a swap made in FIXTURE SETUP followed by a skip in setup (8552ef2;
  severity 3).** Probe: a fixture does `monkeypatch.setitem(sys.modules, "utils.async_utils", foreign)` then
  `pytest.skip()` → 1 skipped, exit 0; the same fixture with the body running → `CheckoutMismatch` (caught). Harmless
  in effect (a skipped test asserts nothing), worth one line in the conftest docstring.
- **P3-4 — `test_every_attribute_a_live_log_record_carries_is_reserved` cannot tell a derived set from a
  hand-typed one on the Python it runs on (ed1cd7d, LB-05; severity 3).** The lane runs Python 3.11.15, where
  `taskName` does not exist; a hand-typed set omitting it is equivalent there (mutation M24 prepared, not yet run).
  A source-level pin (`_RESERVED_LOG_RECORD_ATTRIBUTES is STANDARD_RECORD_ATTRIBUTES`) would pin "derived".
- **P3-5 — The module-mains guard's unseen register omits spellings the estate uses (0e93618, LA-01;
  severity 3).** `_NOT_SEEN_BY_DESIGN` names five shapes; not named: a SQL payload in text
  (`execute("DROP TABLE …")`, `TRUNCATE`, `DELETE FROM` — `utils/document_catalogs.py:160` builds a `DROP TABLE`
  statement), `remove` spellings that destroy remote state (Weaviate `collection.tenants.remove([...])` drops a
  tenant's partition; the prose excludes `remove` for `list.remove`), and `flushdb`/`flushall`. No live offender:
  the two `__main__` blocks delegate to argparse `main()`s.
- **P3-6 — `84502f1`'s "pinned both ways" pins the two registers (`KNOWN_GAPS`, `WIDENED_LEAK_SHAPES`), not the
  docstring prose (severity 3).** A prose mutation (M25, prepared) would survive by construction; harmless.
- **P3-7 — M-FAILURE-HOME parity, stated (1a42390; severity 3).** `utils/_exception_text.py` is byte-identical at
  1a42390, HEAD and the real tree (md5 `4c3c243779442e3b7732ae9a5ef0ef7d`, 618 lines); `utils/observability/failure.py`
  at 1a42390 is 133 lines: a re-export of every `_exception_text` name plus `failure_fields`, `aws_error_code`,
  `AWS_ERROR_CODE_SHAPE`, `PRIMARY_MESSAGE_SAFE_CLASSES`. flynapse-otel `0960c16`'s `flynapse_otel/failure.py` (718
  lines) carries every code line of both, with one cosmetic inlining (`reversed(_links(exc))`); every def/class/
  constant name matches. utils does NOT yet import from `flynapse_otel.failure` (no such import at HEAD): two live
  copies until adoption, the drift hazard the ruling names.
- **P3-8 — The renamed limit changed TYPE (f8e31ee; tier 2, signal contract; severity 3).** `search.requested_count`
  was an int (`== 5`); `db.query.parameter.limit` is `str(limit)` (`"3"`, `"1000"`), per the semconv's string rule
  (`weaviate_service.py:76-83`). No board, alert or reader of either name exists outside utils and copilot-mro's
  memory span (below), so nothing breaks today; a numeric comparison on the new key needs a cast.
- **P3-9 — "One name per concept" is utils-local (f8e31ee; severity 3).** copilot-mro's `memory.search` span writes
  `search.type` for the mode (`memory_index.py:463`), a third spelling beside utils' `search.mode` and the retired
  names; `memory_db.py:65,86` write `memory.requested_count`/`memory.result_count`. Routed with the rename residual.

## Rename site list (attack 2, verified — every tree read-only)

| tree | file:line | name | reader/writer |
|---|---|---|---|
| utils-obsm | `utils/weaviate_service.py:83` | `db.query.parameter.limit` (`_WEAVIATE_LIMIT_ATTRIBUTE`) | writer (every cap-taking door, via `_traced_weaviate`) |
| utils-obsm | `utils/weaviate_service.py:105,891,904,938,948,1006,1081,1118,1179,1244,1458,1729,1863,2189,2237` | `db.response.returned_rows` | writer (declared `:105`, 14 door sites) |
| utils-obsm | `utils/weaviate_service.py:113,1427,1634,1737` | `search.mode` | writer (declared `:113`; decorator attribute on the three searches) |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:1421` | `search.result_count`, `search.requested_count` | reader — `_RETIRED_ATTRIBUTE_KEYS`, asserted ABSENT from the module's dotted literals |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:404,419,1074,1356,1370,1376` | `db.response.returned_rows` | reader (guards) |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:1508,1523,1538` | `db.query.parameter.limit` | reader (guards; `_CENSUS_LIMITS` are strings) |
| utils-obsm | `tests/unit/observability/test_nonagent_storage_client_spans.py:208-210` | `search.mode`, `db.query.parameter.limit` (`"3"`), `db.response.returned_rows` | reader (exact-dict pin of the hybrid-search span) |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:468` | `search.requested_count` | **writer of the OLD name** (`memory.search` span) |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:470` | `search.result_count` | **writer of the OLD name** |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:463` | `search.type` | writer (a third spelling of the mode concept) |
| copilot-mro-obsm | `tests/unit/memory/test_memory_operation_telemetry.py:170-171` | `search.requested_count` (`== 5`), `search.result_count` (`== 1`) | reader of the OLD names (int-typed) |
| copilot-mro-obsm-{cli,r7b,tbA,tbB,tbC,tbD} | `copilot_mro/app/services/memory/memory_index.py:467-470` | `search.requested_count`, `search.result_count` | writers (same code in every variant checkout) |
| core-obsm, api-obsm, dashboard-obsm, iac, flynapse-otel, shift-optimizer, telegram-bot | — | any of the five names | **none** (dashboard's `result_count` at `lib/memory/navigation-trace.ts:30` is a recipe-signal key, not a span attribute) |

## What I tried to break and could not (verified)

- **Withholding with the budget spent (e991bb7, ebfcc68).** Ten shapes, each spending the 10,000-node budget on a
  20,000-item list BEFORE the exception, with a message quoting the exception, checked on stdout (JSON), stderr,
  the exported OTLP body+attributes AND the pre-boundary OTLP record (before flynapse-otel's G.112 processor):
  `__cause__`, `__context__`, `OSError` args + `filename`, `__notes__`, a finished `Future` as an extra (its repr
  quoted), a `Future` as a stdlib `%r` arg, urllib3's retry WARNING with the exception AFTER the spend and a path
  after it, stdlib dict-args (`%(err)s`), an `ExceptionGroup` member, a suppressed `__context__` (`from None`).
  **All clean**: `[message withheld: too much to check for exception text]`, no sentinel on any sink.
- **The reduction cannot re-expose (ebfcc68).** A botocore ERROR whose exception's TEXT is a URL, beside a URL:
  withheld then reduced, clean on every sink.
- **The floor (47a6c5b).** A child `httpx.child.created.late` set to DEBUG after install, `openai._base_client` set
  to DEBUG, the `httpx` family logger itself lowered to DEBUG after install (openai's own `setup_logging` does this),
  an `anthropic` INFO line with a URL, `httpcore.http11` DEBUG: every sub-INFO line dropped, the INFO URL reduced to
  its host. Escape is by construction only (a family logger with `propagate=False` and its own handler; a later
  `basicConfig(force=True)` by another component) — no estate production code does either (searched: telegram-bot's
  `app.py:474-476` configures BEFORE, copilot-mro scripts use `basicConfig` without `force`).
- **`UNFLOORED_LOGGERS` (47a6c5b).** Covers exactly what it claims (`EXPLICIT_LOGGERS` minus families) and is
  pinned both ways (`test_every_explicitly_intercepted_logger_is_floored_or_named_with_its_reason`). A library
  outside the eight families passes whole by design; the estate's other loggers (weaviate-client, langsmith,
  sqlalchemy) either use `warnings.warn` (declared at 4d86ae9) or are not on the runtime path.
- **P3-3's EMPTY list (380db38).** My own census of every `increment_counter`/`record_histogram`/`set_gauge`/
  `record_document_hub_metric` caller in core-obsm, api-obsm, copilot-mro-obsm, shift-optimizer, telegram-bot,
  lambdas and utils (production code): `utils/llm.py` 9 names, `chat_management.py:379` 1, `document_hub/`
  8 through `operations.py`'s wrapper = 18 names = the 18 declared families. No other `MetricsService` consumer
  exists. EMPTY confirmed.
- **The ContextVar door (5bb5ecb).** Nesting, a raising door, a child span, another thread, `asyncio.create_task` +
  `to_thread`: each writes to the right span or nothing. `_WEAVIATE_SPAN` is `None` after every exit.
- **The renames (f8e31ee).** The source scan (`_DOTTED_LITERAL` over the module) plus the runtime census hold the
  module to `_WEAVIATE_SPAN_ATTRIBUTES` in both directions; every cap-taking door records its default as a string.
- **The pin (179cc6d).** `487_939` is the sum of the 18 declared products; a single cap change moves it (M26
  prepared). It is a totals lock plus two per-family figures; only a compensating pair in two places could hide.
- **Mutations re-proved KILLED (mutant.sh, cold cache, restore md5-checked):** M1 `withheld_quotes` ignores the
  budget; M2 `spent` never set; M3 the patcher drops the budget; M4 the safe sink drops it; M5 the stdlib twin drops
  it; M6 no primitive pass-through; M7 reduce BEFORE withholding in `InterceptHandler`; M8 no reduction in the
  handler — each exit 1 against `test_stdout_sinks_withhold_exception_text.py` (M4: `test_safe_loguru_default.py`).

## What I did not test (paused before)

- Mutations M9–M28 (prepared in `scratchpad/utils-review-r8/m/`, runner `run_mutants.sh` from line `run M9`):
  the httpx family drop, the `uvicorn.access` exemption, the P2-2/P2-3 rebuild rules, the failed-format template,
  the undeclared-family allowlist (tenant_id, department), the inventory's three new mechanisms, the outcome
  vocabulary's overflow and error rules, the door span's ambient-span revert and missing reset, the limit never
  recorded, the R2-07 `finally`, the REMOVE payload rule, an emitter string, LB-05 (M24 equivalent on 3.11, M24b the
  3.11-visible omission), the G18-04 cap, `_carried`, the migration script's quote, and the r7 survivors MD3, MS3,
  ME3, MRe, MRf.
- Ruff at each HEAD.
- The human sink (`log_bridge.install(json_stdout=False)`) with the budget spent, in a subprocess.
- Any live collector, Weaviate, Cognito, AWS or Postgres path; Python 3.12+.
- The full suite with the copilot-mro sibling posed beyond what `-L` links (it links every checkout).

---

## Claims table

**Severity**: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process.
**Tier** (§2.3a): 0 = settled by a guard I SAW fail, 1 = consequential but reversible, 2 = irreversible or
estate-shaping. **Chunk**: F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U8-01 | utils | `utils/_exception_text.py:345-364`, `:537-564`; `log_bridge.py:201-204`; `_loguru_default.py:98-101`; `_exception_text.py:582-591` | A spent `ExtraBudget` records `spent`; `withheld_quotes` takes the budget and writes `WITHHELD_MESSAGE`; all three seats pass it (e991bb7) | r7 P1-1 | 10 spent shapes clean on JSON, stderr, OTLP exported and pre-boundary (verified) | `test_a_spent_budget_withholds_the_message_on_every_path`, `test_the_work_bound_is_per_record_not_per_exception`, `test_a_spent_budget_withholds_the_message_on_the_safe_default` | **yes** — M1, M2, M3, M4, M5: 1 failed each | — | 0 | F1 | SETTLED (verified) |
| U8-02 | utils | `utils/_exception_text.py:337-338`, `:422-423` | `str`/`int`/`float`/`bool`/`None` pass through without spending (e991bb7) | r7 P2-4 | `tenant.id` survives a spend | `test_a_spent_budget_leaves_a_primitive_extra_as_it_is` | **yes** — M6: 1 failed | — | 0 | F1 | SETTLED (verified) |
| U8-03 | utils | `utils/_library_lines.py:81-95`, `:98-110`; `intercept.py:90-100`; `_loguru_default.py:146-151` | The filter never rewrites; both handlers reduce AFTER withholding (ebfcc68) | r7 P2-1 | a URL-valued exception beside a URL: clean; urllib3's real retry line names `'RemoteDisconnected'` only | `test_a_library_line_loses_its_exception_text_before_its_urls_are_reduced`, `test_the_client_libraries_lines_carry_no_path_body_or_username` | **yes** — M7, M8: 1 failed each | — | 0 | F1 | SETTLED (verified) |
| U8-04 | utils | `utils/_library_lines.py:45-54`; `intercept.py:37,47,51-58` | httpx, httpcore, openai, anthropic join the families; `UNFLOORED_LOGGERS` names every explicit non-family logger with its reason (47a6c5b) | r7 P2-5 | late children, lowered levels, propagate: all dropped/reduced (verified) | `test_the_http_client_and_model_sdk_lines_are_floored_and_reduced`, `test_the_library_families_are_pinned`, `test_every_explicitly_intercepted_logger_is_floored_or_named_with_its_reason` | TODO — M9, M10 prepared | — | 1 | F1 | ASSERTED (behaviour verified; mutation TODO) |
| U8-05 | utils | `utils/_exception_text.py:448-470`, `:476-504` | Only EXACT containers are rebuilt; a dataclass with its own `__str__` becomes its class name (3269ce0) | r7 P2-2, P2-3 | code read; the r7 plants are pinned by the new tests | `test_a_container_subclass_holding_an_exception_is_its_class_name`, `test_a_dataclass_is_rebuilt_within_its_own_repr_contract` | TODO — M11, M12, M13 prepared | — | 1 | F1 | ASSERTED (mutation TODO) |
| U8-06 | utils | `tests/unit/observability/test_stdout_sinks_withhold_exception_text.py` (+85), `test_failure_fields.py` (+39), `test_safe_loguru_default.py` (+20) | The r7 survivors MD3, MS3, ME3, MRe, MRf, ML2, MC2, ME2 each have a behavioural pin (ac703e5) | r7 P2-7, P3-6 | tests read; implementer replayed the r7 files red | the eight named tests | TODO — M28a–e prepared | — | 1 | F1 | ASSERTED (mutation TODO) |
| U8-07 | utils | `utils/_exception_text.py:594-609`; `intercept.py:94-98,158-161`; `_loguru_default.py:146-149`; `log_bridge.py:190-195` | A failed `%`-format keeps its template; `BaseException` propagation is declared (1a42390) | r7 P3-2, ME7 | code read; `_exception_text.py` byte-identical 1a42390→HEAD (md5 `4c3c2437…`) | `test_a_stdlib_record_whose_format_fails_is_a_constant_never_its_arguments`, `test_a_failed_format_on_the_safe_default_is_a_constant_and_its_template`, `test_a_base_exception_from_a_getter_propagates_into_the_log_call` | TODO — M14 prepared | 3 (P3-7: two live copies until adoption) | 1 | F2 | ASSERTED (mutation TODO) |
| U8-08 | utils | `utils/observability/metrics.py:234-245` | An undeclared family exports NO attribute, `tenant_id` included (380db38) | r7 P3-3 (controller call) | my census: 18 emitted names = 18 declared; the estate list is EMPTY (verified) | `test_an_undeclared_family_exports_nothing_but_its_tenant` (renamed), the histogram+counter test | TODO — M15, M16 prepared | — | 1 | F1 | ASSERTED (census verified; mutation TODO) |
| U8-09 | utils | `utils/_refusals.py:52-67`; `migrate_weaviate_collection.py:228-231`; `document_catalogs.py:101,108` | G24-01 residuals: constant messages, `_carried` types for non-plain values (0aa29b1) | r7 P3-1 | code read | `test_a_refusal_of_an_unpicklable_value_still_crosses_a_process_boundary`, `test_the_migration_scripts_missing_target_refusal_quotes_no_collection`, `test_a_catalog_refusal_names_the_setting_not_its_value` | TODO — M27a, M27b prepared | — | 1 | F2 | ASSERTED |
| U8-10 | utils | `tests/unit/observability/test_legacy_family_inventory.py:203-268`, `:434-503`, `:505-536` | Every write that adds a key is read; silent call shapes reported; constants per module; MV2 pinned (7e49946) | r7 P2-6 | decoys A, B, C (alias, closure, helper) GREEN; control E red (verified) | `test_every_emission_shape_is_resolved_or_reported[*]`, `test_no_emission_shape_went_unresolved[*]` | TODO — M17a/b/c prepared | 2 | 1 | F1 | **REFUTED — P2-1** (the "every write" claim) |
| U8-11 | utils | `utils/observability/outcomes.py:27-58`, `:111-117`; `weaviate_service.py:29,203-213` | `WEAVIATE_OUTCOMES` is a declared closed vocabulary; an undeclared value is `other` + ERROR (1a2680e, G10R-08) | F.4 | code read; copilot-mro's memory spans write their own `operation.outcome` values (`skipped`) outside any vocabulary (routed) | `test_outcome_vocabularies.py` (139 lines) | TODO — M18a, M18b prepared | — | 2 | F1 | ASSERTED |
| U8-12 | utils | `utils/weaviate_service.py:58-75`, `:163-168`, `:171-179`, `:182-213` | The helpers write to `_WEAVIATE_SPAN` (a ContextVar), nothing outside a door; the span variable is `span` (5bb5ecb, G10R-11/27) | correctness not a property of call position | nesting, raising, child span, thread, asyncio task, `to_thread`, `copy_context` verified; `executor.submit` → `interrupted` (P3-2) | the five G10R-11 tests (`:1352-1401`) | TODO — M19a, M19b prepared | 3 | 1 | F2 | ASSERTED (behaviour verified) |
| U8-13 | utils | `utils/weaviate_service.py:76-119`, `:243-260`, `:263-343` | One name per concept: `db.response.returned_rows`, `db.query.parameter.limit` (a STRING, default applied), `search.mode` on the decorator; the attribute set declared with its dialect (f8e31ee, G10R-19/20/23) | packet rounds | rename site list above (verified); type changed int→str (P3-8); copilot-mro still writes the old names at `memory_index.py:468,470` and `search.type` at `:463` (P3-9) | `test_every_attribute_key_the_module_writes_is_declared_and_every_declared_key_is_written`, `test_every_door_that_takes_a_row_cap_records_it`, `test_a_cap_the_caller_passed_is_the_one_recorded` | TODO — M20a prepared | 3 | 2 | F1 | ASSERTED (sites verified) |
| U8-14 | utils | `tests/conftest.py:44-71` | The per-test `sys.modules` check runs in a `finally`; a `tryfirst` makereport wrapper defeats an `xfail` marker (8552ef2, R2-07) | round-1 P2-6 | setup-swap + body caught; setup-swap + setup-skip invisible (P3-3, verified) | `test_a_sys_modules_swap_fails_the_test_whatever_its_body_did_next[*]` | TODO — M21 prepared | 3 | 1 | F2 | ASSERTED |
| U8-15 | utils | `tests/unit/safety/test_module_mains_cannot_delete.py:175-197`, `:640-658` | Destruction without a destructive callee is caught (DeleteRequest, Expiration, REMOVE); the rest is named (0e93618, LA-01) | packet rounds | the register omits SQL-text payloads, remote `remove` spellings, `flush*` (P3-5); no live offender | `test_destruction_without_a_destructive_callee_is_still_caught`, `test_the_destruction_this_rule_cannot_see_is_named` | TODO — M22 prepared | 3 | 1 | F3 | ASSERTED |
| U8-16 | utils | `utils/observability/legacy_families.py:241-449` (emitter strings) | Every family's emitter points where it is emitted, pinned (0e9b2a8) | iac r3 P3-4 | code read | `test_every_family_is_emitted_where_its_emitter_says[*]` | TODO — M23 prepared | — | 1 | F3 | ASSERTED |
| U8-17 | utils | `utils/observability/log_bridge.py:95-99` | The reserved-name set is `STANDARD_RECORD_ATTRIBUTES`, derived from a live record (ed1cd7d, LB-05) | packet rounds | on 3.11 the guard cannot distinguish derived from hand-typed (P3-4) | `test_every_attribute_a_live_log_record_carries_is_reserved` | TODO — M24 (expected equivalent on 3.11), M24b prepared | 3 | 1 | F3 | ASSERTED |
| U8-18 | utils | `tests/unit/observability/test_utils_logs_no_exception_text.py:28-36`, `:663-675` | The "Known gaps" list is two real gaps, each pinned as NOT flagged; the mutated-`failure_fields` shape joins the flagged set (84502f1, G24-F12) | stale prose | the prose itself is unpinned (P3-6) | `test_the_known_gaps_are_still_gaps[*]` | TODO — M25 prepared (expected to survive: prose) | 3 | 1 | F3 | ASSERTED |
| U8-19 | utils | `tests/unit/observability/test_legacy_family_inventory.py:760-793` | The quoted figures are recomputed from the caps; the total is pinned at 487,939 (179cc6d, G18-04) | packet rounds | a totals lock + two per-family figures; one cap change moves it | `test_the_series_figures_the_declarations_quote_are_the_declared_bounds` | TODO — M26 prepared | — | 1 | F3 | ASSERTED |
| U8-20 | utils | whole range | Each commit green at its own HEAD, 0 skipped; `utils.__file__` in the extract | lane rules | 19 posed sweeps: 1834 → 1909 passed, 0 skipped, one identical symlink-artefact red (4/4 green in the real tree); the bare archive at HEAD 1914/13/6 | the suite | n/a (measurement) | — | 0 | F2 | SETTLED (measured); ruff TODO |
| U8-21 | utils | `utils/_exception_text.py:234-255`, `:260-302` | Chain links are `__cause__`/`__context__`/group members; args are quoted only as strings (unchanged in range) | pre-existing | an exception in another's `args` ships (P3-1, verified on JSON + OTLP) | none | n/a — behaviour probe | 2 | 1 | F1 | OPEN — P3-1 |

**Totals so far: 21 claims** — 4 SETTLED (3 verified by mutation, 1 measured), 15 ASSERTED (mutations prepared,
not run), 1 REFUTED (U8-10, P2-1), 1 OPEN (U8-21, P3-1).

---

## Open claims, tier 2 first

**Tier 2**

- **U8-11** (G10R-08) — the Weaviate vocabulary is declared; copilot-mro's memory spans write their own outcome
  values (`skipped`) under the same key with no vocabulary. Adoption is the copilot-mro lane's.
- **U8-13** (G10R-19/20/23) — the renames hold in utils; `db.query.parameter.limit` is now a string; copilot-mro
  still writes `search.requested_count`/`search.result_count` (`memory_index.py:468,470`) and `search.type`.

**Tier 1**

- **U8-10 (P2-1)** — the label-key reader misses an alias, a closure and a helper write; design the reader to fail
  closed on any unrecognised mention rather than enumerate writes.
- **U8-04 … U8-09, U8-12, U8-14 … U8-19** — asserted pending the prepared mutations (TODO at the pause).
- **U8-21 (P3-1)** — an exception in `args` is not a link.
