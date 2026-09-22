# Claims packet — utils review round 8 (`4d86ae9..179cc6d`)

Independent adversarial review (Opus), 2026-09-22, paused once on the owner's request and resumed with the tree
unmoved (utils-obsm HEAD `179cc6d`, clean). It answers the implementer's response to review r7
(`claims-utils-r7.md`) and the packet-rounds open list (`claims-utils-rounds.md`: G10R-08, G10R-11/27,
G10R-19/20/23, R2-07, LA-01, LB-05, G18-04, G24-F12). Read-only against every real tree:

- each of the 19 commits (the base `4d86ae9` and the 18 in range) was `git archive`d into scratch, with flynapse-otel
  as an archive of `0960c16` (its HEAD when the review began; it has since moved to `df503c2`, a G.116 URL-rule change
  that touches neither `failure.py` nor anything this range imports beyond `withhold_url_secrets`);
- every probe and mutation ran against a scratch copy (`probe/`, `inv/*`, `mut/`), never against
  `/home/aditya/Code/utils-obsm`. After every mutation `mut/` was `diff -r` byte-identical to the `179cc6d` archive
  (the resumed batch ran in the durable copy `~/.claude/scratch/obs-merge/utils-review-r8/work/mut/`, md5-checked
  against `git show 179cc6d:…`).

| repo | worktree | branch | range | commits | flynapse-otel under test |
|---|---|---|---|---|---|
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `4d86ae9..179cc6d` | 1a2680e, 5bb5ecb, f8e31ee, 8552ef2, 0e9b2a8, 0e93618, e991bb7, ebfcc68, 47a6c5b, 3269ce0, ac703e5, 1a42390, 380db38, 0aa29b1, 7e49946, ed1cd7d, 84502f1, 179cc6d | archive of `0960c16` (the `-L` sweep used the real tree at the same SHA) |

**How it was run.**

- **Lane:** `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider`,
  from the copy's root; from 01:30 on every run went through `/home/aditya/Code/pytest-slot.sh --`, one at a time, `-n 2`
  at most, behind the load gate (1-min load ≤ 14, ≥ 4 GB available).
- **Environment:** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`.
- **Paths:** `PYTHONPATH=<plugin dir>:<copy>:/home/aditya/Code/core-obsm:<fo-0960c16 archive>`; a private
  `PYTHONPYCACHEPREFIX` per run. A plugin (`r8report`) printed `rootdir`, `utils.__file__`, `flynapse_otel.__file__`.
- **Mutations:** `/home/aditya/Code/mutant.sh` (cold cache, baseline first, restore verified), aimed at the file(s)
  meant to catch each; both survivors re-run against the FULL lane.
- **Bare-archive full lane at HEAD `179cc6d` (`-n 2`):** 1914 passed, 13 skipped, 6 failed in 57 s, `rootdir` and
  `utils.__file__` in the archive. The 6 reds are `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` (5) and
  `test_root_anchoring.py::test_sibling_repo_reaches_a_sibling_and_refuses_a_missing_one`, which need the real
  workspace (44/44 green read-only in the real tree). The 13 skips: the inventory's 9 `[copilot-mro]` cases (no
  sibling beside a bare archive), 3 `test_root_anchoring`, 1 cross-repo. 1914 + 13 + 6 = 1933, the implementer's total.

**Every commit is green at its own HEAD, 0 skipped.** `parallel-commits.sh -L -j 2`, serial pytest per commit,
`test_cross_repo_reads_name_their_checkout.py` deselected (23 tests; a symlink artefact, 44/44 in the real tree).
Every commit carried exactly ONE red, the same test, a known `-L` artefact:
`tests/unit/safety/test_no_provenance_laundering.py::test_the_scan_reaches_the_code_it_is_defending` ("scanned
core-obsm (resolved) while core-obsm matches this worktree (symlink)") — 4/4 green read-only in the real tree.
`utils.__file__` was inside `ws-<sha>/utils-obsm/` at all 19 commits.

| commit | passed | skipped | commit | passed | skipped |
|---|---|---|---|---|---|
| 4d86ae9 (base) | 1834 | 0 | 3269ce0 | 1877 | 0 |
| 1a2680e | 1841 | 0 | ac703e5 | 1884 | 0 |
| 5bb5ecb | 1846 | 0 | 1a42390 | 1886 | 0 |
| f8e31ee | 1852 | 0 | 380db38 | 1886 | 0 |
| 8552ef2 | 1856 | 0 | 0aa29b1 | 1890 | 0 |
| 0e9b2a8 | 1858 | 0 | 7e49946 | 1904 | 0 |
| 0e93618 | 1869 | 0 | ed1cd7d | 1905 | 0 |
| e991bb7 | 1872 | 0 | 84502f1 | 1908 | 0 |
| ebfcc68 | 1873 | 0 | 179cc6d | 1909 | 0 |
| 47a6c5b | 1876 | 0 | | | |

(+1 artefact red +23 deselected each: base 1858, HEAD 1933. The implementer's "1858 → 1933, 0 skipped" holds.)

**Ruff at each HEAD** (ruff 0.14.0, `ruff check . --no-cache`): 1144 diagnostics and exit 1 at all 19 HEADs, the base
included; the per-commit (file, code) delta is **zero at all 18 steps**. The new modules (`outcomes.py`,
`_loaded_module_outcome_probe.py`) carry none.

---

## Findings, ranked

**Verdict: MERGE-CLEAN — P0 0 · P1 0 · P2 1 · P3 10.**

Every r7 finding the range answers is closed at its named seat, and every r7 surviving mutant is now red (MD3, MS3,
ME3, MRe, MRf, ML2, MC2, ME2, ME7, MU2c, MV2, and the decoys MI6, MI7, MI8, MI10). The withholding layer held against
every spent-budget shape I planted, on every sink including the human line and the pre-boundary OTLP record. The
packet-rounds items are each closed and mutation-proved. **45 distinct mutants: 43 KILLED, 2 SURVIVED** (both
expected and confirmed against the full lane: M24 is equivalent on Python 3.11, M25 mutates prose). **9 decoys:**
MI6, MI7, MI8, MI10 and the control E red; A, B, C green (P2-1); D green and declared.

The one mechanism that gave way again is the AST inventory's label-key reader — the third round of holes in the
same guard. It is test-only, and the runtime shim bounds the consequence (a key the declaration lacks is dropped,
never exported), so it does not block the merge; but it meets the plan's Lesson ("a second P1 in the same mechanism
is a design problem", here in P2 form) and should be fixed by design, not by a fourth enumeration.

### P2-1 — The inventory's "every write that adds a key" is not every write: an alias, a closure or a helper adds a label the guard never checks (7e49946; r7 P2-6 residual, third round)

`_label_dicts` (`tests/unit/observability/test_legacy_family_inventory.py:203-268`) reads a name's keys from its
literal and from writes spelled on THAT name in THAT scope (`labels["k"] = v`, `.update`, `.setdefault`, `|=`). Three
decoys planted in `utils/llm.py` each add `email` to a declared family's labels and leave the inventory and bounding
files GREEN (53 passed, 9 skipped). The r7 decoy of the same kind written directly on the name (MI8) is red, and so
is the control:

| plant (appended to `utils/llm.py` in a scratch copy) | inventory |
|---|---|
| A: `alias = labels; alias["email"] = email; svc.increment_counter("llm_requests_total", **labels)` | **silent** |
| B: a closure `def add(): labels["email"] = email`, called, then `**labels` | **silent** (`_own_nodes` does not descend into nested functions) |
| C: a helper `_enrich(labels, email)` that mutates it, then `**labels` | **silent** |
| D: `getattr(svc, "increment_" + "counter")("llm_probe_leak_total", email=e)` | silent, and declared (`_NOT_SEEN_BY_DESIGN`: a computed name) |
| E (control): `svc.increment_counter("llm_probe_leak_total", email=e)` | red (`test_every_emitted_family_is_declared[utils]`) |
| MI8 (r7): `labels["email"] = e` on the literal's own name | red (`test_every_emitted_attribute_key_is_declared[utils]`) |

At runtime the shim drops an undeclared key on a declared family, so nothing exports. The consequence is exactly the
failure the file's docstring says it exists to catch (`:4-6`: "the shim drops it, the series silently loses a
dimension, and nothing says so"), and the docstring's "every write that adds one" (`:26-27`) overclaims. **Fix (by
design):** read a name's keys from its literal only, and make ANY other mention of the name — an alias binding, a
call argument, a reference from a nested scope — outside a recognised read, a recognised write or the emission splat
mark it unreadable, so its splat is reported. That fails closed instead of enumerating writes.

### P3 findings

- **P3-1 — An exception held in another exception's `args` is not a chain link (pre-existing; severity 2).**
  `outer = RuntimeError("wrapped", inner); logger.error(f"failed: {outer.args[1]}", err=outer)` ships `inner`'s
  message on the JSON line and the OTLP body (exported and pre-boundary). `_every_link`
  (`utils/_exception_text.py:234-255`) walks `__cause__`, `__context__` and group members, never `args`;
  `_partial_quotes` quotes STRING args only. urllib3's `ProtocolError('Connection aborted.', RemoteDisconnected(...))`
  has this shape, though its own log lines quote the whole repr, which IS withheld. Declared only as "any other
  fragment". Fix: `_every_link` also queues `BaseException` instances found in `link.args`.
- **P3-2 — On another thread INSIDE a door, `_finish_weaviate_span` writes nothing, and the door reads
  `interrupted`/ERROR (5bb5ecb; severity 3).** A decorated door whose body runs
  `executor.submit(_finish_weaviate_span, "success")` ends `interrupted`: the helper is a no-op on the worker (a fresh
  context) and the wrapper's `finally` stamps the unset span. `copy_context().run` and `asyncio.to_thread` carry the
  span (outcome `success`). No regression (before the range the worker wrote to `INVALID_SPAN`), and no door does this
  today. The docstring's "Outside a door, nothing" should add "or on another thread, and the door then reads
  interrupted". Also: `_WEAVIATE_SPAN.reset(token)` RAISES `ValueError` when a door is exited in a context other than
  the one it was entered in (OTel's own `detach` only logs); no such site exists.
- **P3-3 — R2-07's per-test check cannot see a swap made in FIXTURE SETUP followed by a skip in setup (8552ef2;
  severity 3).** A fixture that does `monkeypatch.setitem(sys.modules, "utils.async_utils", foreign)` and then
  `pytest.skip()` gives 1 skipped, exit 0; the same fixture with the body running raises `CheckoutMismatch`. Harmless
  in effect (a skipped test asserts nothing); one line in the conftest docstring.
- **P3-4 — The LB-05 guard cannot tell a derived set from a hand-typed one on the Python the lane runs (ed1cd7d;
  severity 3).** On Python 3.11.15 `taskName` does not exist, so a hand-typed set without it is equivalent: **M24
  SURVIVES** the aimed file and the full lane (1914 passed). A hand-typed set that also omits `processName` (M24b) is
  red. A source pin (`_RESERVED_LOG_RECORD_ATTRIBUTES is STANDARD_RECORD_ATTRIBUTES`) would pin "derived".
- **P3-5 — The module-mains guard's unseen register omits spellings the estate uses (0e93618, LA-01; severity 3).**
  `_NOT_SEEN_BY_DESIGN` names five shapes. Not named: a SQL payload in text (`execute("DROP TABLE …")`, `TRUNCATE`,
  `DELETE FROM` — `utils/document_catalogs.py:160` builds a `DROP TABLE` statement), a `remove` spelling that destroys
  remote state (Weaviate `collection.tenants.remove([...])` drops a tenant's partition; the prose excludes `remove` for
  `list.remove`), and `flushdb`/`flushall`. No live offender: the two `__main__` blocks delegate to argparse `main()`s.
- **P3-6 — 84502f1's "pinned both ways" pins the two registers, not the docstring prose (severity 3).** **M25**
  (the "Known gaps" prose restored to its stale form) **SURVIVES** the aimed file and the full lane (1914 passed).
  Prose cannot be pinned cheaply; the claim should say "the registers are pinned".
- **P3-7 — M-FAILURE-HOME parity, stated (1a42390; severity 3).** `utils/_exception_text.py` is byte-identical at
  `1a42390`, at `179cc6d` and in the real tree (md5 `4c3c243779442e3b7732ae9a5ef0ef7d`, 618 lines).
  `utils/observability/failure.py` at `1a42390` is 133 lines: a re-export of every `_exception_text` name plus
  `failure_fields`, `aws_error_code`, `AWS_ERROR_CODE_SHAPE` and `PRIMARY_MESSAGE_SAFE_CLASSES`, and unchanged to HEAD.
  flynapse-otel's `flynapse_otel/failure.py` (718 lines; identical at `0960c16` and `df503c2`) carries every code line
  of both, with one cosmetic inlining (`reversed(_links(exc))` in `rendered_failure`); every def, class and constant
  name matches. utils does NOT yet import from `flynapse_otel.failure`: two live copies until adoption, the drift
  hazard the ruling names. (Routed, not counted: flynapse-otel's `docs/plans/m-failure-home.md` post-restart note says
  "19 commits" for this 18-commit range and "the other thirteen" before listing twelve.)
- **P3-8 — The renamed limit changed TYPE (f8e31ee; tier 2, signal contract).** `search.requested_count` was an int
  (`== 5`); `db.query.parameter.limit` is `str(limit)` (`"3"`, `"1000"`), per the semconv's string rule
  (`utils/weaviate_service.py:76-83`). No board, alert or reader of either name exists outside utils and copilot-mro's
  memory span, so nothing breaks today; a numeric comparison on the new key needs a cast.
- **P3-9 — "One name per concept" is utils-local (f8e31ee).** copilot-mro's `memory.search` span still writes
  `search.requested_count` and `search.result_count` (`memory_index.py:468,470`, unchanged at copilot-mro-obsm
  `557a178f`) and `search.type` for the mode (`:463`), a third spelling beside utils' `search.mode`;
  `memory_db.py:65,86` write `memory.requested_count` and `memory.result_count`. Routed to copilot-mro.
- **P3-10 — 0e93618's message overcounts its mutations by one (known).** "Five mutations fail the new tests" lists, as
  its fourth, "an alias named with a destructive prefix, which passed vacuously until renamed" — a fixture correction,
  not a mutation of the guard. Four mutations. I re-proved the REMOVE payload rule independently (M22 red).

## Rename site list (every tree read-only)

| tree | file:line | name | reader/writer |
|---|---|---|---|
| utils-obsm | `utils/weaviate_service.py:83` | `db.query.parameter.limit` (`_WEAVIATE_LIMIT_ATTRIBUTE`) | writer (every cap-taking door, through `_traced_weaviate`) |
| utils-obsm | `utils/weaviate_service.py:105,891,904,938,948,1006,1081,1118,1179,1244,1458,1729,1863,2189,2237` | `db.response.returned_rows` | writer (declared at `:105`, 14 door sites) |
| utils-obsm | `utils/weaviate_service.py:113,1427,1634,1737` | `search.mode` | writer (declared at `:113`; decorator attribute on the three searches) |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:1421` | `search.result_count`, `search.requested_count` | reader: `_RETIRED_ATTRIBUTE_KEYS`, asserted ABSENT from the module's dotted literals |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:404,419,1074,1356,1370,1376` | `db.response.returned_rows` | reader (guards) |
| utils-obsm | `tests/unit/observability/test_weaviate_client_spans.py:1508,1523,1538` | `db.query.parameter.limit` | reader (guards; `_CENSUS_LIMITS` are strings) |
| utils-obsm | `tests/unit/observability/test_nonagent_storage_client_spans.py:208-210` | `search.mode`, `db.query.parameter.limit` (`"3"`), `db.response.returned_rows` | reader (exact-dict pin of the hybrid-search span) |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:468` | `search.requested_count` | **writer of the OLD name** (`memory.search` span) |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:470` | `search.result_count` | **writer of the OLD name** |
| copilot-mro-obsm | `copilot_mro/app/services/memory/memory_index.py:463` | `search.type` | writer (a third spelling of the mode concept) |
| copilot-mro-obsm | `tests/unit/memory/test_memory_operation_telemetry.py:170-171` | `search.requested_count` (`== 5`), `search.result_count` (`== 1`) | reader of the OLD names (int-typed) |
| copilot-mro-obsm-{cli,r7b,tbA,tbB,tbC,tbD} | `copilot_mro/app/services/memory/memory_index.py:467-470` | `search.requested_count`, `search.result_count` | writers (the same code in every variant checkout) |
| core-obsm, api-obsm, dashboard-obsm, iac, flynapse-otel, shift-optimizer, telegram-bot | — | any of the five names | **none** (dashboard's `result_count` at `lib/memory/navigation-trace.ts:30` is a recipe-signal key, not a span attribute) |

## What I tried to break and could not

- **Withholding with the budget spent (e991bb7, ebfcc68).** Ten shapes, each spending the 10,000-node budget on a
  20,000-item list BEFORE the exception, with a message quoting it, checked on stdout (JSON), stderr, the exported
  OTLP body and attributes AND the pre-boundary OTLP record (before flynapse-otel's G.112 processor): `__cause__`,
  `__context__`, `OSError` args + `filename`, `__notes__`, a finished `Future` as an extra (its repr quoted), a
  `Future` as a stdlib `%r` argument, urllib3's retry WARNING with the exception after the spend and a path after it,
  stdlib dict-args (`%(err)s`), an `ExceptionGroup` member, a suppressed `__context__`. **All clean.**
- **The human line and the JSON line in a fresh process** (`log_bridge.install(json_stdout=False|True)`): six spent
  shapes (loguru kwargs, `bind`, stdlib args, stdlib `extra=`, a `Future`, a dict extra holding the exception after
  the spend) each write `[message withheld: too much to check for exception text]`, and the human line's `{extra}`
  shows type names (`{'rows': 'list', 'box': 'dict'}`). The only lines carrying the sentinel were the two
  pre-existing, DECLARED shapes (r6's A2): a positional argument (`logger.error("failed: {}", exc)`) and
  `opt(capture=False)` — the record never carries the exception, so no runtime seat can see it; the static sweep bans
  it in utils, and no estate site uses `capture=False` (searched).
- **The reduction cannot re-expose (ebfcc68).** A botocore ERROR whose exception's TEXT is a URL, beside a URL:
  withheld, then reduced; clean on every sink.
- **The floor (47a6c5b).** A child `httpx.child.created.late` set to DEBUG after install, `openai._base_client` set to
  DEBUG, the `httpx` logger itself lowered to DEBUG after install (openai's own `setup_logging` does this), an
  `anthropic` INFO line with a URL, `httpcore.http11` DEBUG: every sub-INFO line dropped, the INFO URL reduced to its
  host. Escape is by construction only (a family logger with `propagate=False` and its own handler, or a later
  `basicConfig(force=True)` by another component); no estate production code does either (telegram-bot's
  `app.py:474-476` configures BEFORE; copilot-mro scripts use `basicConfig` without `force`).
- **`UNFLOORED_LOGGERS` (47a6c5b).** It covers exactly what it claims (`EXPLICIT_LOGGERS` minus the families) and is
  pinned both ways; M10 (the `uvicorn.access` exemption dropped) is red. A library outside the eight families passes
  whole by design; weaviate-client reports through `warnings.warn` (declared at 4d86ae9).
- **P3-3's EMPTY list (380db38).** My own census of every `increment_counter` / `record_histogram` / `set_gauge` /
  `record_document_hub_metric` caller in core-obsm, api-obsm, copilot-mro-obsm, shift-optimizer, telegram-bot,
  lambdas and utils (production code): `utils/llm.py` 9 names, `chat_management.py:379` 1, `document_hub/` 8 through
  `operations.py`'s wrapper — 18 names, the 18 declared families. No other `MetricsService` consumer exists. EMPTY
  confirmed; M15 (tenant_id re-allowed) and M16 (department allowed) are red.
- **The ContextVar door (5bb5ecb).** Nesting, a raising door, a child span, another thread, `asyncio.create_task` +
  `to_thread`, `copy_context`: each writes to the right span or nothing, and `_WEAVIATE_SPAN` is `None` after every
  exit. M19a (the ambient span restored) and M19b (the reset dropped) are red.
- **The renames (f8e31ee).** The source scan plus the runtime census hold the module to `_WEAVIATE_SPAN_ATTRIBUTES`
  both ways. M20a (no limit recorded) and M20b (a door writes `search.result_count` again) are red.
- **The pin (179cc6d).** `487_939` is the sum of the 18 declared products; M26 (one cap moved) is red. One hunk
  cannot move the pin: the pin is in the test file, the caps in `legacy_families.py`. Sixteen of the 18 families are
  held only through the sum (a totals lock); a redistribution between families would have to be arithmetically exact
  to hide, and I found no single-hunk shape that does it without also failing a per-family key check.

**Mutations (mutant.sh; all 45 in `~/.claude/scratch/obs-merge/utils-review-r8/logs/mutants.txt`):**

| mutant | what it removes | result |
|---|---|---|
| M1 / M2 | `withheld_quotes` ignores the budget / `spent` never set | KILLED / KILLED |
| M3 / M4 / M5 | the patcher / the safe sink / the stdlib twin drops the budget | KILLED ×3 |
| M6 | no primitive pass-through | KILLED |
| M7 / M8 | reduce BEFORE withholding in `InterceptHandler` / no reduction in the handler | KILLED ×2 |
| M9 / M10 | `httpx` dropped from the families / the `uvicorn.access` exemption dropped | KILLED ×2 |
| M11 / M12 / M13 | no `__str__` check / a dict subclass rebuilt / an isinstance container rebuild | KILLED ×3 |
| M14 | a failed `%`-format loses its template | KILLED |
| M15 / M16 | tenant_id re-allowed / department allowed on an undeclared family | KILLED ×2 |
| M17a / M17b / M17c / M17d | no per-function label scope / no reference check / no own-module constant / the forwarder fixpoint runs once (MV2) | KILLED ×4 |
| M18a / M18b | `bounded` never overflows / an undeclared outcome is not an error | KILLED ×2 |
| M19a / M19b | the helpers write to the ambient span / the ContextVar reset dropped | KILLED ×2 |
| M20a / M20b | the limit never recorded / a door writes the retired `search.result_count` | KILLED ×2 |
| M21 / M21b | the per-test check back after `yield` / the xfail report wrapper disarmed | KILLED ×2 |
| M22 | the REMOVE payload rule dropped | KILLED |
| M23 | an emitter string points at the wrong function | KILLED |
| M24 / M24b | a hand-typed reserved set without `taskName` / also without `processName` | **SURVIVED** (full lane too; equivalent on 3.11) / KILLED |
| M25 | the stale "Known gaps" prose restored | **SURVIVED** (full lane too; prose) |
| M26 | `failure_code` cap 16 → 17 | KILLED |
| M27a / M27b | `_carried` carries everything / the migration script quotes the collection again | KILLED ×2 |
| M28a–e (MD3, MS3, ME3, MRe, MRf) | a hidden field unsearched / stdlib extras at `EXTRA_DEPTH` / the net returns the message / `filename2` dropped / an argument's repr dropped | KILLED ×5 |
| ML2 / MC2 / ME2 / ME7 | URL reduction removed / N counts lines / a failed nested value blanks its extra / `_LastResort`'s inner net | KILLED ×4 |

## What I did not test

- Any live collector, Weaviate, Cognito, AWS or Postgres path; Python 3.12+ (where M24 would no longer be equivalent).
- The full suite with the copilot-mro sibling beyond what `-L` links (it links every checkout, and the inventory's
  copilot-mro limb ran green there at every commit).
- flynapse-otel's own copy of the renderers under mutation (the fo lane's parity test is its guard; I measured the
  code-line parity only).
- Whether any estate call site today nests an exception inside another's `args` and quotes it (P3-1 is latent on a
  pattern search).

---

## Claims table

**Severity**: 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process,
— = nothing owed. **Tier** (§2.3a): 0 = settled by a guard I SAW fail, 1 = consequential but reversible, 2 =
irreversible or estate-shaping. **Chunk**: F1 contract + privacy, F2 the merge itself, F3 the residual.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U8-01 | utils | `utils/_exception_text.py:345-364`, `:537-564`; `log_bridge.py:201-204`; `_loguru_default.py:98-101`; `_exception_text.py:582-591` | A spent `ExtraBudget` records `spent`; `withheld_quotes` takes the budget and writes `WITHHELD_MESSAGE`; all three seats pass it (e991bb7) | r7 P1-1 | 10 spent shapes clean on JSON, stderr, OTLP exported and pre-boundary; 6 on the human and JSON lines in a fresh process | `test_a_spent_budget_withholds_the_message_on_every_path`, `test_the_work_bound_is_per_record_not_per_exception`, `test_a_spent_budget_withholds_the_message_on_the_safe_default` | **yes** — M1, M2, M3, M4, M5 | — | 0 | F1 | SETTLED |
| U8-02 | utils | `utils/_exception_text.py:337-338`, `:422-423` | `str`/`int`/`float`/`bool`/`None` pass through without spending (e991bb7) | r7 P2-4 | `tenant.id` survives a spend | `test_a_spent_budget_leaves_a_primitive_extra_as_it_is` | **yes** — M6 | — | 0 | F1 | SETTLED |
| U8-03 | utils | `utils/_library_lines.py:81-110`; `intercept.py:90-100`; `_loguru_default.py:146-151` | The filter never rewrites; both handlers reduce AFTER withholding (ebfcc68) | r7 P2-1 | a URL-valued exception beside a URL: clean; urllib3's real retry line names `'RemoteDisconnected'` only | `test_a_library_line_loses_its_exception_text_before_its_urls_are_reduced`, `test_the_client_libraries_lines_carry_no_path_body_or_username` | **yes** — M7, M8, ML2 | — | 0 | F1 | SETTLED |
| U8-04 | utils | `utils/_library_lines.py:45-54`; `intercept.py:37,47,51-58` | httpx, httpcore, openai, anthropic join the families; `UNFLOORED_LOGGERS` names every explicit non-family logger with its reason (47a6c5b) | r7 P2-5 | late children, lowered levels, propagate: all dropped or reduced | `test_the_http_client_and_model_sdk_lines_are_floored_and_reduced`, `test_the_library_families_are_pinned`, `test_every_explicitly_intercepted_logger_is_floored_or_named_with_its_reason` | **yes** — M9, M10 | — | 0 | F1 | SETTLED |
| U8-05 | utils | `utils/_exception_text.py:448-470`, `:476-504` | Only EXACT containers are rebuilt; a dataclass with its own `__str__` becomes its class name (3269ce0) | r7 P2-2, P2-3 | the r7 plants are pinned | `test_a_container_subclass_holding_an_exception_is_its_class_name`, `test_a_dataclass_is_rebuilt_within_its_own_repr_contract` | **yes** — M11, M12, M13 | — | 0 | F1 | SETTLED |
| U8-06 | utils | `test_stdout_sinks_withhold_exception_text.py`, `test_failure_fields.py`, `test_safe_loguru_default.py` | The r7 survivors MD3, MS3, ME3, MRe, MRf, ML2, MC2, ME2 each have a behavioural pin (ac703e5) | r7 P2-7, P3-6 | every one re-planted | the eight named tests | **yes** — M28a–e, ML2, MC2, ME2 | — | 0 | F1 | SETTLED |
| U8-07 | utils | `utils/_exception_text.py:594-609`; `intercept.py:94-98,158-161`; `_loguru_default.py:146-149`; `log_bridge.py:190-195` | A failed `%`-format keeps its template; `BaseException` propagation is declared (1a42390) | r7 P3-2, ME7 | `_exception_text.py` byte-identical 1a42390 → HEAD (md5 `4c3c2437…`) | `test_a_stdlib_record_whose_format_fails_is_a_constant_never_its_arguments`, `test_a_failed_format_on_the_safe_default_is_a_constant_and_its_template`, `test_a_base_exception_from_a_getter_propagates_into_the_log_call` | **yes** — M14, ME7 | 3 (P3-7: two live copies until adoption) | 0 | F2 | SETTLED |
| U8-08 | utils | `utils/observability/metrics.py:234-245` | An undeclared family exports NO attribute, `tenant_id` included (380db38) | r7 P3-3 (controller call) | my census: 18 emitted names = 18 declared; the estate list is EMPTY | the undeclared-family sweep test, the histogram+counter test | **yes** — M15, M16 | — | 0 | F1 | SETTLED |
| U8-09 | utils | `utils/_refusals.py:52-67`; `migrate_weaviate_collection.py:228-231`; `document_catalogs.py:101,108` | G24-01 residuals: constant messages; a non-plain value is carried as its type (0aa29b1) | r7 P3-1 | code read | `test_a_refusal_of_an_unpicklable_value_still_crosses_a_process_boundary`, `test_the_migration_scripts_missing_target_refusal_quotes_no_collection`, `test_a_catalog_refusal_names_the_setting_not_its_value` | **yes** — M27a, M27b | — | 0 | F2 | SETTLED |
| U8-10 | utils | `tests/unit/observability/test_legacy_family_inventory.py:203-268`, `:434-503`, `:505-536`, `:331-377` | Every write that adds a key is read; silent call shapes reported; constants per module; MV2 pinned (7e49946) | r7 P2-6 | MI6, MI7, MI8, MI10 red; decoys A, B, C (alias, closure, helper) GREEN; control E red | `test_every_emission_shape_is_resolved_or_reported[*]`, `test_no_emission_shape_went_unresolved[*]`, `test_every_emitted_attribute_key_is_declared[*]` | **yes** for the mechanisms — M17a, M17b, M17c, M17d (MV2); the "every write" claim is refuted by decoys | 2 | 1 | F1 | **PARTIAL — P2-1** |
| U8-11 | utils | `utils/observability/outcomes.py:27-58`, `:111-117`; `weaviate_service.py:29,203-213` | `WEAVIATE_OUTCOMES` is a declared closed vocabulary; an undeclared value is `other` and ERROR (1a2680e, G10R-08) | F.4 | copilot-mro's memory spans write their own `operation.outcome` values (`skipped`) under the same key, in no vocabulary (routed) | `test_outcome_vocabularies.py` | **yes** — M18a, M18b | — | 2 | F1 | SETTLED (utils); adoption owed elsewhere |
| U8-12 | utils | `utils/weaviate_service.py:58-75`, `:163-168`, `:171-213` | The helpers write to `_WEAVIATE_SPAN` (a ContextVar) and to nothing outside a door; the span variable is `span` (5bb5ecb, G10R-11/27) | correctness no longer a property of call position | nesting, raising, child span, thread, asyncio task, `to_thread`, `copy_context` verified; `executor.submit` inside a door → `interrupted` (P3-2) | the five G10R-11 tests (`test_weaviate_client_spans.py:1352-1401`) | **yes** — M19a, M19b | 3 | 0 | F2 | SETTLED; residual P3-2 |
| U8-13 | utils | `utils/weaviate_service.py:76-119`, `:243-260`, `:263-343` | One name per concept: `db.response.returned_rows`, `db.query.parameter.limit` (a STRING, default applied), `search.mode` on the decorator; the attribute set declared with its dialect (f8e31ee, G10R-19/20/23) | packet rounds | rename site list above; the type changed int → str (P3-8); copilot-mro still writes the old names and `search.type` (P3-9) | `test_every_attribute_key_the_module_writes_is_declared_and_every_declared_key_is_written`, `test_every_door_that_takes_a_row_cap_records_it`, `test_a_cap_the_caller_passed_is_the_one_recorded` | **yes** — M20a, M20b | 3 | 2 | F1 | SETTLED (utils); residuals P3-8, P3-9 |
| U8-14 | utils | `tests/conftest.py:44-73` | The per-test `sys.modules` check runs in a `finally`; a `tryfirst` makereport wrapper defeats an `xfail` marker (8552ef2, R2-07) | round-1 P2-6 | setup swap + body caught; setup swap + setup skip invisible (P3-3) | `test_a_sys_modules_swap_fails_the_test_whatever_its_body_did_next[*]` | **yes** — M21, M21b | 3 | 0 | F2 | SETTLED; residual P3-3 |
| U8-15 | utils | `tests/unit/safety/test_module_mains_cannot_delete.py:175-197`, `:640-658` | Destruction without a destructive callee is caught (DeleteRequest, Expiration, REMOVE); the rest is named (0e93618, LA-01) | packet rounds | the register omits SQL-text payloads, remote `remove` spellings and `flush*` (P3-5); the message overcounts (P3-10) | `test_destruction_without_a_destructive_callee_is_still_caught`, `test_the_destruction_this_rule_cannot_see_is_named` | **yes** — M22 | 3 | 0 | F3 | SETTLED; residuals P3-5, P3-10 |
| U8-16 | utils | `utils/observability/legacy_families.py:241-449` (the emitter strings) | Every family's emitter points where it is emitted, pinned (0e9b2a8) | iac r3 P3-4 | — | `test_every_family_is_emitted_where_its_emitter_says[*]` | **yes** — M23 | — | 0 | F3 | SETTLED |
| U8-17 | utils | `utils/observability/log_bridge.py:95-99` | The reserved-name set is `STANDARD_RECORD_ATTRIBUTES`, derived from a live record (ed1cd7d, LB-05) | packet rounds | on 3.11 the guard cannot tell derived from hand-typed | `test_every_attribute_a_live_log_record_carries_is_reserved` | **partly** — M24b red; **M24 SURVIVES** (aimed and full lane) | 3 | 1 | F3 | PARTIAL — P3-4 |
| U8-18 | utils | `tests/unit/observability/test_utils_logs_no_exception_text.py:28-36`, `:663-675` | The "Known gaps" list is the two real gaps, each pinned as NOT flagged; the mutated-`failure_fields` shape joins the flagged set (84502f1, G24-F12) | stale prose | the registers are pinned; the prose is not | `test_the_known_gaps_are_still_gaps[*]` | **M25 SURVIVES** (aimed and full lane) — prose | 3 | 1 | F3 | ASSERTED — P3-6 |
| U8-19 | utils | `tests/unit/observability/test_legacy_family_inventory.py:760-793` | The quoted figures are recomputed from the caps; the total is pinned at 487,939 (179cc6d, G18-04) | packet rounds | a totals lock plus two per-family figures; one hunk cannot move both the caps and the pin | `test_the_series_figures_the_declarations_quote_are_the_declared_bounds` | **yes** — M26 | — | 0 | F3 | SETTLED |
| U8-20 | utils | whole range | Each commit green at its own HEAD, 0 skipped; ruff adds nothing | lane rules | 19 posed sweeps 1834 → 1909 passed, 0 skipped, one identical artefact red; bare HEAD 1914/13/6; ruff 1144 at every HEAD, delta 0 | the suite | n/a (measurement) | 3 (1144 pre-existing ruff diagnostics) | 0 | F2 | SETTLED (measured) |
| U8-21 | utils | `utils/_exception_text.py:234-255`, `:260-302` | Chain links are `__cause__`, `__context__` and group members; args are quoted only as strings (unchanged in range) | pre-existing | an exception in another's `args` ships on JSON and OTLP | none | n/a — behaviour probe | 2 | 1 | F1 | OPEN — P3-1 |
| U8-22 | utils ↔ flynapse-otel | `utils/_exception_text.py`, `utils/observability/failure.py` (at `1a42390`); `flynapse_otel/failure.py` (`0960c16` = `df503c2`) | `1a42390` is the parity base for the M-FAILURE-HOME port | M-FAILURE-HOME | byte-identical to HEAD; every code line present in the port (one cosmetic inlining); utils does not import the port yet | flynapse-otel's parity test (not run by me) | n/a — measured | 3 | 1 | F2 | ASSERTED — P3-7 |

**Totals: 22 claims** — 17 SETTLED (16 by a guard I saw fail, 1 measured), 2 ASSERTED (U8-18, U8-22), 2 PARTIAL
(U8-10, U8-17), 1 OPEN (U8-21).

---

## Open claims, tier 2 first

**Tier 2**

- **U8-13 (P3-8, P3-9)** — the renames hold in utils, but `db.query.parameter.limit` is now a string, and
  copilot-mro still writes `search.requested_count` / `search.result_count` (`memory_index.py:468,470`) and
  `search.type` (`:463`). Route to the copilot-mro lane.
- **U8-11** — the Weaviate vocabulary is declared; copilot-mro's memory spans write their own outcome values
  (`skipped`) under the same key, in no vocabulary. Adoption is the copilot-mro lane's.

**Tier 1**

- **U8-10 (P2-1)** — the label-key reader misses an alias, a closure and a helper write. Redesign the reader to fail
  closed on any unrecognised mention rather than enumerating writes.
- **U8-21 (P3-1)** — an exception in `args` is not a chain link.
- **U8-22 (P3-7)** — two live copies of the renderers until utils imports `flynapse_otel.failure`.
- **U8-17 (P3-4)** and **U8-18 (P3-6)** — equivalent or prose mutants; pin by source identity or accept.
