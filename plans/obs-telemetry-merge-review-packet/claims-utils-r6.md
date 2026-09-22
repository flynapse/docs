# Claims packet — utils review round 6 (`8572635..594327e`)

Independent adversarial review (Opus), 2026-09-21. It answers the implementer's response to review r5
(`claims-utils-r5.md`). Read-only against every real tree:

- each commit was `git archive`d into the private scratch `scratchpad/utils-review-r6/trees/`;
- every mutation ran against a scratch copy (`mut/`, or the posed workspace `ws/`);
- each copy was restored after each run and md5-checked against the HEAD blob;
- at the end, `diff -r` showed both copies byte-identical to the `594327e` archive, and `utils-obsm` and `copilot-mro-obsm` were clean.

| repo | worktree | branch | range | commits | flynapse-otel under test |
|---|---|---|---|---|---|
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `8572635..594327e` | 9999a17, ec0629e, 1ca0268, 8a55ca1, 3d6d3b1, 945101f, f1ef9b9, 71826b3, c47caba, 31d8afd, 16fde67, 1290f27, 5685348, 594327e | archive of `34c814a` (another lane is editing it live) |

**How it was run.**

- **Lane:** `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider`, run from the archive root. `LOGURU_DIAGNOSE` and `LOGURU_BACKTRACE` were unset.
- **Environment:** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`.
- **Paths:** `PYTHONPATH=<guard>:<archive>:<fo-34c814a archive>`, with a fresh `PYTHONPYCACHEPREFIX` for every run.
- **Network guard:** a `sitecustomize` refused every non-loopback connect, every non-loopback name lookup, and loopback service ports (5432, 6379, 8080, 4317/4318 and others), and logged every attempt. Across all 15 sweeps it logged 0 refusals, only 7 ephemeral loopback connects per run (the tests' own local servers).
- **Reporting:** a plugin printed `rootdir`, `utils.__file__`, `flynapse_otel.__file__` and `sitecustomize.__file__` for every run. Every exit status below is pytest's or ruff's own.
- **Deselected in the archive sweep:** `test_cross_repo_reads_name_their_checkout.py` and one `test_root_anchoring` case, as in r5. They need the real workspace (see P3-7).

**Every commit is green at its own HEAD.** Each full suite exited 0, with `utils.__file__` pointing at that archive.

| commit | passed | skipped | commit | passed | skipped |
|---|---|---|---|---|---|
| 8572635 (base) | 1760 | 12 | 71826b3 | 1778 | 11 |
| 9999a17 | 1760 | 11 | c47caba | 1779 | 11 |
| ec0629e | 1761 | 11 | 31d8afd | 1788 | 11 |
| 1ca0268 | 1765 | 11 | 16fde67 | 1789 | 11 |
| 8a55ca1 | 1766 | 11 | 1290f27 | 1791 | 11 |
| 3d6d3b1 | 1769 | 11 | 5685348 | 1792 | 11 |
| 945101f | 1770 | 11 | 594327e | 1792 | 11 |
| f1ef9b9 | 1775 | 11 | | | |

Each run also deselected 24 tests.

- **The skips at HEAD:** 8 are the inventory's `[copilot-mro]` limb (plus the sibling floor), and 3 are `test_root_anchoring`.
- **With the sibling present:** with an archive of copilot-mro-obsm `245e4d47` posed beside it, the inventory file plus the bounding file ran 39 passed and 0 skipped.
- **Warnings:** the "14 warnings" (the OTel `LoggingHandler` DeprecationWarning) vanish from pytest's summary from `71826b3` on. This is the declared effect of routing `showwarning`.

**Ruff at each HEAD.** No HEAD is ruff-clean: every one, the base included, carries 1144 pre-existing diagnostics, and `ruff check` exits 1.

- **Per-commit delta, by (file, code):** zero, except that `ec0629e`, `1ca0268`, `8a55ca1`, `3d6d3b1`, `945101f`, `f1ef9b9`, `71826b3`, `c47caba` and `31d8afd` each carry 3 × B023 in `tests/unit/observability/test_failure_fields.py`. They are fixed forward in `16fde67`, as the brief states.
- **Files the range touched:** they have identical diagnostic sets at base and HEAD.

---

## Findings, ranked

**No P0.** Every r5 plant is now clean on the safe, JSON and human sinks and on OTLP: A1, B1–B4, B6, B7, C1–C3 and D2. Only the declared ones remain: A2 (positional), B5 (depth 4), H4 (asyncio callback argument), I1 (`print`) and J2 (Unicode ellipsis). MA23 is now red. **One P1: a regression the range introduced into the privacy layer.**

### P1-1 — Extras-as-types exposes the fields a dataclass hid: `field(repr=False)` and a custom `__repr__` (new in 8a55ca1; the test pins the leaking shape)

When a dataclass extra holds an exception, it is rebuilt as a dict of **every** field (`utils/_exception_text.py:342-346`), including fields whose `repr=False` or whose class-level `__repr__` exists precisely to keep them out of logs.

| plant | 8572635 / 1ca0268 | 8a55ca1 / 594327e (JSON, human and OTLP alike) |
|---|---|---|
| `Outcome(token=field(repr=False), err=exc)` | `Outcome(err=ValueError('x6'))` — the token is hidden | `{'token': 'SEC_X6 hidden-token', 'err': 'ValueError'}` |
| `Creds` whose `__repr__` masks `password`, plus an exception field | `Creds(user='u', password=***)` — nothing leaks | `{'user': 'u', 'password': 'SEC_X6b pw', 'err': 'ValueError'}` |
| the same, with no exception (control) | `Outcome(err=None)` | `Outcome(err=None)` — only the exception triggers the rebuild |

**Why it matters.** The estate uses `repr=False` as its *type-level* log guard:

- core-obsm `core/resources/document_viewer/services/pdf_object_resolver.py:84-96` protects `s3_key` and `url`, and says so: "review r6-F1: a type, not only a scan";
- copilot-mro `data_discovery/connectors/base.py:31` protects `password`;
- telegram-bot has three credential fields.

None of the 12 `repr=False` sites holds an exception today, so nothing ships yet. But the next `@dataclass` that pairs a hidden field with an `error` field ships the hidden field on every sink.

`test_stdout_sinks_withhold_exception_text.py:556` asserts `"{'error': 'ValueError', 'count': 1}"`, so the dict-of-all-fields shape is pinned.

**Fix.** When an exception is found inside a dataclass, render only the fields with `f.repr`, and only when the class's `__repr__` is the dataclass-generated one. Otherwise write the type name alone. Pin both hidden-field shapes.

### P2-1 — The patcher can now raise into the caller's log call, and all sinks lose the record (new in 8a55ca1)

`withheld_extra` now reads dataclass fields with `getattr(value, name, None)`, which absorbs only `AttributeError`. It also iterates sets and deques. It runs in the loguru core patcher (`log_bridge.py:177-194`), before any handler's `try`.

Probe: a dataclass whose field descriptor raises `RuntimeError`, then `logger.info("saved row", row=Row(1))`:

- **at 8572635:** `log_bridge stdout sink failed: RuntimeError` and `... otlp sink failed: RuntimeError`, and the call returns;
- **at HEAD:** **the log call raises `RuntimeError`**.

`InterceptHandler.emit` (`intercept.py:51-75`) has no `try`, so a stdlib `extra={...}` raises into the stdlib caller the same way. A stdlib `%s` argument of the same object already raised before the range, because the repr touches the same fields.

The realistic triggers are ORM-style dataclass descriptors and a set mutated by another thread during the log call. None was found in the estate (no `MappedAsDataclass`).

**Fix.** Make the patcher fail closed: on any exception, replace the extra with its type name and never raise.

### P2-2 — `WeaviateTenancyError` can no longer be pickled or deep-copied (new in f1ef9b9)

`error.tenancy_ids = MappingProxyType(...)` (`weaviate_service.py:380`) breaks both:

- `pickle.dumps(exc)` and `copy.deepcopy(exc)` raise `TypeError: cannot pickle 'mappingproxy' object`;
- in a `ProcessPoolExecutor` the parent receives a `TypeError` instead of the refusal, so an `except WeaviateTenancyError` misses it.

This was probed at HEAD; at 8572635 all three operations are fine. The estate's process pools (`ifim_parser.py:2337`, `amos_parser.py:4186`) do not reach a tenancy refusal in their workers today, so this is latent.

MG2 (a plain mutable dict) survives the suite, so the "read-only mapping" property the change was made for is unpinned anyway.

**Fix.** Use a plain dict or a tuple of pairs, or give the exception a `__reduce__`, and pin pickling.

### P2-3 — The stdlib twin misses the most common shape: the record's `msg` IS the exception

`withheld_stdlib_message` (`_exception_text.py:392-402`) searches `exc_info` and `args` only. `logging.getLogger(x).error(exc)` carries the object in `record.msg`, and its text ships everywhere:

- JSON, human and OTLP: `'SEC_S3 msg-is-exc'`;
- the safe default through `_LastResort`;
- the OTel stderr handler (`ERROR opentelemetry.probe: SEC_S8 ...`).

Third-party code does exactly this: uvicorn `server.py:172` and `config.py:508,535`, and langsmith `run_helpers.py:2208`.

Separately, on the safe default `_LastResort` ignores a stdlib `extra={"err": exc}`. So `std.error("failed: " + str(e), extra={"err": e})` ships (S5). Under `setup_logging` the same line is withheld.

**Fix.** Add `record.msg` when it is a `BaseException`, and run the extras through `withheld_extra` in `_LastResort`.

### P2-4 — "A finished future's exception joins `found`" is unguarded (M23f survives, behaviour-proven)

Mutant M23f removes `found.append(held)` (`_exception_text.py:316`). The observability and weaviate suites stay green: 658 passed.

The mutant changes behaviour. With it, `logger.error("task ended: {t}", t=task)` writes `... exception=ValueError('SEC_M23F future message')>` into the message. At HEAD it writes `exception=ValueError>`.

The P2-3 test logs the task only as an extra, never quoted in the message.

### P2-5 — The urllib3 floor stops one line; the pool id reaches the sinks by three others

1290f27 floors `urllib3.connectionpool` at INFO (`intercept.py:37`, `:159-161`). MU1 and MU2 are red, so the floor itself holds. A local fake server (loopback, no AWS) showed three other paths:

- **At `LOG_LEVEL=INFO`,** urllib3's real WARNING `Retrying (Retry(...)) after connection broken by 'RemoteDisconnected': /ap-south-1_SECPOOLB/.well-known/jwks.json` passes the floor. The test's synthetic warning (`test_stdout_sinks_withhold_exception_text.py:603`) carries no path, which is why it never saw this.
- **At DEBUG,** `urllib3.util.retry` (not floored) logs `Incremented Retry for (url='/ap-south-1_SECPOOLA/...')`.
- **At DEBUG,** `botocore.endpoint` logs `Making request ... 'body': b'{"UserPoolId": "ap-south-1_SECPOOLC", "Username": "SEC_user@example.com"}'`. core calls `admin_*` with both (`cognito_identities.py:136,156,190`, `tenant_claim_writer.py:107,162`).

The api's own JWKS fetch (`requests.get`, zero retries) reaches only the connectionpool DEBUG line, which is now floored.

**A deliberate DEBUG session is broken:** `urllib3.connectionpool` (or `urllib3`) set to DEBUG before `setup_logging` comes back floored to INFO, silently, with no opt-out.

**Complete fix.** Reduce urllib3's lines to method and host with a filter, which was the api lane's second option. Floor or filter `botocore` bodies too.

### P2-6 — Q6: an undeclared key still reaches an export — through an emission shape the inventory silently skips (pre-existing)

Deleting the excuse mechanism is complete. `_UNDECLARED_KEYS_OWED_BY_COPILOT_MRO` and `_RETIRING_IN_COPILOT_MRO` are gone, and planting a new key at a copilot-mro site is red (MC1, posed workspace).

At runtime, a declared family drops an undeclared key. An **undeclared** family, however, exports every key not on the deny-list. Probe: `llm_probe_leak_total{tenant_id="t1", email="SEC_a@b.c"}`.

The AST inventory is the only guard, and four shapes pass it green (39 passed, sibling present):

| mutant | shape | where the visitor lets it through |
|---|---|---|
| MI1 | `increment_counter(name="…", user_id=…)` | `if not node.args: return`, `test_legacy_family_inventory.py:236-237` |
| MI2 | an f-string family name | `else: return`, `:263-264` |
| MI4 | a generic `_emit(name, **labels)` forwarder | `:254` treats any forwarder as benign and never follows its callers |
| MI5 | an attribute-named family | `else: return`, `:263-264` |

The file's docstring promises the opposite: "A call shape this file cannot resolve is a FAILURE, never a skip". Two of those branches return silently and never append to `_unresolved`.

### P3 findings

- **P3-1 — The recursion collapse is exact, but the volume claim holds for DIRECT recursion only (severity 3).**
  - **What holds:** `frame_headers` is byte-identical to `format_tb`'s first lines in 9 shapes, with 0 opens: direct, mutual, a three-function cycle, alternating lines, recursion then a raise, runs of exactly 3, 4 and 5, and recursion inside recursion.
  - **What is false:** mutual recursion, a three-function cycle and a function recursing from two lines are still 1000 lines and about 140 KB, because `traceback` does not collapse them either. The docstring's "a `RecursionError` is a handful of lines, not a thousand" (`_exception_text.py:63-65`) is therefore false for them.
  - **What is unpinned:** the parity test covers direct recursion only. MR3 (collapse ignoring the line: 6 lines against `format_tb`'s 1000 on alternating recursion) and MR5 (always "times") survive the observability suite (537 passed).
  - **`sys.tracebacklimit` is ignored:** 6 lines against 3.
  - **Drift:** flynapse-otel's M-FAILURE-HOME copy (`34c814a` and `e56005b`) has no collapse, no partial quotes, no suppressed-context walk and no `withheld_extra`, and no test compares the two bodies. That is routed to the fo lane.
- **P3-2 — The declared work bound is per exception; through extras it multiplies (severity 3).**
  - `withheld_quotes` neither dedupes `found` nor bounds links × exceptions.
  - Measured: 16 × a 250-member group plus a 50 KB message takes **5.2 s** in one `logger.error`, linear in the count, so about 80 s at the 256 cap. 200 three-link exceptions plus 50 KB take 0.8 s.
  - The patcher itself costs 4–16× more on big containers: a 200k list went from 143 to 639 ms, and a 200k set from 40 to 663 ms.
  - The docstring states "about two seconds".
- **P3-3 — Warnings routing: declared trade-offs, measured (severity 3).**
  - **Still works:** `-W error`, `-W error::UserWarning`, ini `filterwarnings` (error and ignore) and `catch_warnings(record=True)`.
  - **Lost:**
    - a developer never sees a warning's text, and there is no opt-in;
    - `python -W error` turns a warning into a type-only crash (`DeprecationWarning` plus frames);
    - pytest's summary loses every warning raised after `setup_logging` in a test, including the OTel SDK's own deprecation of `LoggingHandler`, which `log_bridge` depends on (14 → 0).
  - **Leaks:**
    - `logging.captureWarnings(True)`, called before or after, ships the message and a linecache source line via `py.warnings` under `setup_logging`. No estate caller does this;
    - a foreign `showwarning` installed earlier still prints the message, by design.
- **P3-4 — Quotes of a CARRIED exception that still ship (severity 2, mostly declared as "other fragments").**
  - `{err.args}` when the message contains a tab, a backslash or a newline: repr escaping means neither `str` nor `repr` matches, and `repr(str)` is consulted only when the text has `...`.
  - `KeyError`'s bare `{e.args[0]}`, 8 or more characters: the single-argument exclusion is broader than the path concern it answers.
  - `OSError.filename`, `__notes__` and a format-spec prefix.
  - **Declared-class extras:** a pydantic model, `__slots__`, `MappingProxyType`, `UserList`, `ChainMap`, `functools.partial`, depth 4, and a finished gather future whose RESULT holds exceptions (`<_GatheringFuture finished result=[ValueError('…')]>`).
- **P3-5 — G24-01's contract stops at Weaviate; three other utils refusals quote tenant identities (severity 2).**
  - `TenancyBindingError`, `tenancy_context.py:184-221`: 7 raises, quoting `tenant_id` and operator ids.
  - `CacheKeyError`, `cache_keys.py:195` (a valid `tenant_id`) and `:271-326`.
  - The S3 URL `ValueError`s, `s3_service.py:1127,1137`, which quote a bucket host.
- **P3-6 — Ruff is not clean at any HEAD (severity 3).** There are 1144 pre-existing diagnostics. The range adds nothing except the B023 window noted above.
- **P3-7 — Posed-workspace G.53 register (severity 3, not the range's).**
  - `test_cross_repo_reads_name_their_checkout.py` is 6 failed, 17 passed and 1 skipped, **identically at base and HEAD**, in a posed workspace (a scratch clone plus read-only symlinks).
  - Most failures are posing artifacts: symlinks resolve to `/home/aditya/Code`.
  - One cause is live: the worktree `copilot-mro-obsm-cli` (branch `obs-merge-cli`, committed 11:44 today) holds a `_root.py` byte-identical to ours and is not in the witness set.
  - The controller should run this file in the real workspace.

---

## What I tried to break and could not

- **P2-1 (reads).** MA23 (`extract_tb`) is now red: `test_rendering_a_failure_opens_no_file_at_all`.
  - An audit hook saw 0 `open` events from `frame_headers`, `failure_fields` and `rendered_failure` across 9 recursion shapes, a chain, a frame compiled under another file's name, and a group.
  - The hook is robust to `os.open`, `io.open_code` and `pathlib` (all audit `open`), and the test proves the recorder is live.
- **P2-2 variants that are withheld on every sink.**
  - loguru calls: `{err!r}`, `{err.args}` (plain), `opt(lazy=True)`, `opt(colors=True)`, `{errs}` and `{errs[0]}` of a list extra, `bind`, and `contextualize`.
  - stdlib calls: `%r`, `%(err)s` with a dict argument, a list argument, and `%s` of a chained cause with `exc_info`.
  - the OTel stderr handler with a `%s` argument.
  - The seven mutants M22a–g are red.
- **P2-3 variants that are withheld.** A namedtuple (becomes a tuple of type names), a `slots=True` dataclass, a set in a dict in a list at depth 3, `gather(return_exceptions=True)` results, an `exc_info` tuple, and a finished `Task` read without marking it retrieved. M23a–e are red.
- **P3-1 partial quotes.** M31a (no partial quotes) and M31b (suppressed context skipped) are red.
- **P3-2 no-sink crash.** M32a (a sink always assumed) and M32b (the fallback writes `repr`) are red.
- **P3-4 warnings.** M34a (not routed), M34b (always chained to the printing default) and M34c (the message on the no-sink path) are red. A pydantic `input_value` never shows.
- **P3-7 undeclared histogram.** M37a is red. An undeclared counter keeps its tenant. `user_id` is dropped by the deny-list.
- **P3-8 standalone limb.** MI3 (the retired `embedding_request_duration` re-emitted in `utils/llm.py`) is red **standalone** (2 failed) and with the sibling present. The 8 standalone skips are only the copilot-mro limb.
- **M-LEGACY-DELETE step 2.** MF2 (a port family relabelled `retire`) is red. MC1 (a new key at a copilot-mro site) is red. No emitter of the ten retired names exists at copilot-mro-obsm `245e4d47`.
- **G24-01.** MG3 (ids not set as attributes) is red: 7 failed. `str` and `repr` of each refusal carry no id.
- **945101f.** MX1 (dropped from `__all__`) is red. `import utils` still loads no OTel.
- **1290f27.** The floor keeps a higher pre-set level, reset restores it, and another library's DEBUG still flows. MU1 and MU2 are red. In the WARNING probe, `withheld_stdlib_message` reduced `RemoteDisconnected('Remote end closed…')` to its type.

## What I did not test

- Any live collector, Cognito, AWS or Postgres path. The Cognito and JWKS probes hit a local fake server on loopback with fake credentials.
- `test_cross_repo_reads_name_their_checkout.py` in the real workspace. It ran only in a posed workspace, where it was red identically at base and HEAD (P3-7).
- The implementer's own mutants that I did not re-run, beyond those named above: the three bounding re-homes of 9999a17, and G24-01's interpolation plants.
- flynapse-otel's `withholding` rules, and anything in fo beyond the parity read (P3-1).
- Behaviour under Python 3.12+, where `traceback` and warnings internals differ.

---

## Claims table

Severity (this reviewer's scale): 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process, — = nothing owed. Tier (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U6-01 | utils | `utils/_exception_text.py:55-79` | M-STACK-HEADERS' "no file reads" is counted by an audit hook (r5 P2-1) | the content-only guards let `extract_tb` through | 0 opens across chain, compiled, group and 9 recursion shapes | `test_failure_fields.py::test_rendering_a_failure_opens_no_file_at_all` | **yes** — MA23: 1 failed | — | 0 | F1 | SETTLED |
| U6-02 | utils | `utils/_exception_text.py:50-87` | Repeated frames collapse as `traceback` collapses them (r5 P3-9) | 1000-line stacks | identical to `format_tb`'s first lines in 9 shapes; mutual, cycle and alternating recursion are still 1000 lines | `test_a_recursion_collapses_as_traceback_collapses_it` | **partly** — MR4 (cutoff 4) red; **MR3** (lineno ignored) and **MR5** (plural) **survive** (537 passed) | 3 | 1 | F3 | PARTIAL — P3-1 |
| U6-03 | flynapse-otel | `flynapse_otel/failure.py:57-69` (`34c814a`) | The M-FAILURE-HOME copy keeps parity | ruling M-STACK-HEADERS | no collapse, no partial quotes, no suppressed context, no `withheld_extra`; no parity test | **none** | not recorded | 2 | 1 | F3 | OPEN — routed to fo |
| U6-04 | utils | `utils/observability/log_bridge.py:177-194` | The patcher withholds the message's quotes of every exception found in extras (r5 P2-2) | `"failed: {err}", err=exc` | r5 A1 clean on JSON, human and OTLP | `test_the_message_loses_its_quotes_of_an_exception_passed_beside_it` | **yes** — M22a: 1 failed | — | 0 | F1 | SETTLED |
| U6-05 | utils | `utils/_loguru_default.py:82-96` | The safe sink searches extras | same, without `setup_logging` | safe-mode probe clean | `test_the_safe_sink_withholds_an_exception_quoted_beside_the_message` | **yes** — M22b: 1 failed | — | 0 | F1 | SETTLED |
| U6-06 | utils | `intercept.py:75`, `:99`; `_loguru_default.py:138-140` | The stdlib `%s`-args twin is withheld in InterceptHandler, the OTel stderr formatter and `_LastResort` | `warning("retrying after %s", exc)` | `%s`, `%r`, dict and list arguments clean | the P2-2 tests plus `test_the_stderr_handler_withholds_an_exception_quoted_through_its_args` | **yes** — M22c: 1, M22d: 2, M22e: 1, M22f: 3 failed | 2 | 1 | F1 | PARTIAL — P2-3 (`record.msg`, `_LastResort` extras) |
| U6-07 | utils | `utils/_exception_text.py:380-389` | More than `_MAX_LINKS` exceptions fails closed | bounded work | per exception only; 16 × 250-member group = 5.2 s | `test_quotes_of_too_many_exceptions_fail_closed` | **yes** — M22g: 1 failed | 3 | 1 | F3 | PARTIAL — P3-2 |
| U6-08 | utils | `utils/_exception_text.py:293-347` | Extras reach sets, frozensets, deques, dict keys, dataclasses and finished futures (r5 P2-3) | each wrote the message | r5 B1–B4, B6, B7 clean | `test_exceptions_inside_every_reached_shape_are_written_as_types` | **yes** — M23a–e: 1 failed each | — | 0 | F1 | SETTLED |
| U6-09 | utils | `utils/_exception_text.py:316` | A finished future's exception joins `found`, so the message's quotes of it go too | commit 8a55ca1 says so | with M23f the message leaks `exception=ValueError('SEC…')` | **none effective** | **M23f survives** (658 passed) | 1 | 1 | F1 | OPEN — P2-4 |
| U6-10 | utils | `utils/_exception_text.py:342-346`; pin at `test_stdout_sinks_withhold_exception_text.py:556` | A dataclass holding an exception becomes a dict of ALL its fields | "a dict of its fields" | `repr=False` token and masked password ship on JSON, human and OTLP; did not at 8572635 | pinned the leaking way | n/a (behaviour probe at 3 commits) | 1 (latent content leak; defeats a type guard) | 2 | F1 | REFUTED — P1-1 |
| U6-11 | utils | `log_bridge.py:177-194`; `intercept.py:51-75` | The patcher never raises into the caller | a sink failure was type-only | a raising dataclass field: the log call raises at HEAD and returned at base | **none** | not recorded | 2 | 1 | F2 | REFUTED — P2-1 |
| U6-12 | utils | `utils/_interpreter_hooks.py:44-121` | With no loguru sink, the hooks write the constant message plus types and frames (r5 P3-2) | a crash was silent | the r5 `np_silent` shape is clean | `test_with_no_loguru_sink_left_an_uncaught_exception_is_still_written[*]` | **yes** — M32a: 4 failed; M32b: 3 failed | — | 0 | F1 | SETTLED |
| U6-13 | utils | `utils/observability/__init__.py:10`, `:34` | `withhold_url_secrets` is re-exported (the same object) | copilot-mro declares only flynapse-utils | `import utils` loads no OTel | `test_the_url_rule_is_re_exported_from_utils_observability` | **yes** — MX1: 1 failed | — | 0 | F2 | SETTLED |
| U6-14 | utils | `utils/weaviate_service.py:371-381`, `:448-456`, `:607-630` | Tenancy refusals are constant sentences with ids as attributes (G24-01) | M-WEAVIATE-LEFTOVERS (b) | `str` and `repr` carry no sentinel | `test_a_refusal_is_a_constant_sentence_and_carries_its_ids_as_attributes[*]` | **yes** — MG3: 7 failed | — | 0 | F1 | SETTLED |
| U6-15 | utils | `utils/weaviate_service.py:380` | `tenancy_ids` is a read-only `MappingProxyType` | "read-only mapping" | unpicklable and un-deepcopyable; a process pool delivers `TypeError` | **none** | **MG2** (plain dict) **survives** | 2 | 1 | F2 | REFUTED — P2-2 |
| U6-16 | utils | `utils/_interpreter_hooks.py:81-98`, `:130` | `warnings.showwarning` is routed; a warning is its category and location (r5 P3-4) | pydantic's `input_value` | r5 G1/G2 clean; `-W error`, ini filters and `catch_warnings(record=True)` intact | `test_a_warning_is_its_category_and_location_only[*]`, `test_a_warning_goes_through_the_sinks_as_its_category_and_location` | **yes** — M34a: 3, M34b: 3, M34c: 1 failed | 3 (developer and pytest trade-offs; `captureWarnings`) | 0 | F1 | SETTLED; residual P3-3 |
| U6-17 | utils | `utils/observability/metrics.py:99-101`, `:237-248` | An undeclared histogram drops `tenant_id` and `tenant.id` (r5 P3-7) | M-CARDINALITY | an undeclared counter keeps its tenant | `test_an_undeclared_histogram_drops_a_tenant_too` | **yes** — M37a: 1 failed | — | 0 | F1 | SETTLED |
| U6-18 | utils | `tests/unit/observability/test_legacy_family_inventory.py:333-347` | Every emitter check runs per limb; the utils limb runs standalone (r5 P3-8) | 9 tests skipped whole | 8 standalone skips, copilot-mro limb only | `test_no_call_site_emits_a_retired_family[utils]`, `test_every_emitted_family_is_declared[utils]` | **yes** — MI3: 2 failed, standalone and posed | — | 0 | F3 | SETTLED |
| U6-19 | utils | `utils/observability/legacy_families.py` (9999a17); the inventory test | The eight copilot-mro retire declarations are deleted; the excuse mechanism is deleted (M-LEGACY-DELETE step 2) | call sites went first (`ca752296`) | no retired emitter at copilot-mro-obsm `245e4d47`; `git grep` finds no excuse | `test_the_retired_families_stay_deleted`, `test_every_emitted_attribute_key_is_declared[copilot-mro]` | **yes** — MF2: 1 failed; MC1 (new key at a copilot-mro site): 1 failed | — | 0 | F1 | SETTLED (r5 P3-6 moot) |
| U6-20 | utils | `test_legacy_family_inventory.py:20-23`, `:236-237`, `:254`, `:263-264` | "A call shape this file cannot resolve is a FAILURE, never a skip" | the guard's own premise | an undeclared family exports `email=`; four shapes pass | the inventory | **MI1, MI2, MI4, MI5 survive** (39 passed) | 1 | 1 | F1 | REFUTED — P2-6 (pre-existing) |
| U6-21 | utils | `utils/observability/intercept.py:32-37`, `:159-161` | `urllib3.connectionpool` floored at INFO (api lane §3) | the DEBUG request line carries the pool id | the pool id ships via the connectionpool WARNING at INFO, `urllib3.util.retry` at DEBUG and botocore at DEBUG | `test_urllib3s_debug_request_line_never_reaches_the_sinks`, `test_a_floored_logger_keeps_a_higher_level_and_reset_restores_it` | **yes** for the floor — MU1: 2, MU2: 1 failed | 2 | 1 | F1 | PARTIAL — P2-5 |
| U6-22 | utils | `utils/_exception_text.py:162-170`, `:217-263` | Partial quotes and suppressed-context quotes withheld (r5 P3-1) | they shipped on every sink | r5 C1–C3 and D2 clean; `{err.args}` with escapes, KeyError `args[0]`, `.filename` and `__notes__` still ship | `test_the_parts_of_a_message_a_caller_quotes_are_quotes_too` | **yes** — M31a: 1, M31b: 1 failed | 2 | 1 | F1 | PARTIAL — P3-4 |
| U6-23 | utils | `utils/tenancy_context.py:184-221`, `utils/cache_keys.py:195`, `:271-326`, `utils/s3_service.py:1127`, `:1137` | **Not taken:** G24-01's contract for other utils refusals | outside the ruling's letter | messages quote `tenant_id`, operator ids and a bucket host | **none** | not recorded | 2 | 1 | F1 | OPEN — P3-5 |
| U6-24 | utils | whole range | Each commit is green at its own HEAD; ruff adds nothing but the B023 window | lane rules | 15 full suites exit 0; ruff delta by (file, code) as stated | the suite | n/a (measurement) | 3 (1144 pre-existing ruff diagnostics) | 0 | F2 | SETTLED (measured) |
| U6-25 | utils | `_interpreter_hooks.py:22-27`; `log_bridge.py:50-64`; `_loguru_default.py:44-47`; `test_cross_repo_reads_name_their_checkout.py:594-601`; `test_utils_logs_no_exception_text.py:76-80`; `test_utils_spans_withhold_exception_text.py:333-339` | r5's P3-3, P3-5, P3-10, P3-12, P3-14, P3-15 and U5-34 declared where they live (594327e) | declare, do not fix | each text matches the r5 finding it names | **none** (docs) | n/a | 3 | 1 | F3 | ASSERTED |
| U6-26 | utils | `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` | The G.53 register in the real workspace | depends on sibling state | posed: 6 failed, identical at base and HEAD; the new `copilot-mro-obsm-cli` worktree is identical and outside the witness set | the file itself | not re-run | 3 | 1 | F3 | OPEN — P3-7 |

**Totals: 26 claims.** By state:

- 12 SETTLED (all tier 0; U6-24 is a measurement, not a guard);
- 1 ASSERTED;
- 5 PARTIAL;
- 4 REFUTED;
- 4 OPEN.

I ran 37 distinct mutants and plants, MI3 twice (standalone and posed), and re-ran r5's probe set. Every one was restored and md5-checked against its HEAD blob.

- **29 went red:** MA23, MR4, M22a–g, M23a–e, M31a–b, M32a–b, M34a–c, M37a, MG3, MU1–2, MX1, MF2, MI3 and MC1.
- **8 survived:** MR3 and M23f (both behaviour-proven), MR5, MG2, and MI1, MI2, MI4, MI5.

---

## Open claims, tier 2 first

**Tier 2**

- **U6-10 (P1-1)** — extras-as-types rebuilds a dataclass as a dict of every field, so `field(repr=False)` and a masking `__repr__` stop protecting anything. That type-level guard is the one core chose over a scan (r6-F1). The shape is pinned by the test. Latent today, but a FIX-FIRST item: the range introduced it.

**Tier 1**

- **U6-11** (P2-1: the patcher raises into the caller).
- **U6-15** (P2-2: an unpicklable refusal; MG2 survives).
- **U6-06** (P2-3: `record.msg` is the exception; `_LastResort` ignores extras).
- **U6-09** (P2-4: M23f survives).
- **U6-21** (P2-5: the urllib3 WARNING and retry lines, and botocore bodies, carry the pool id and usernames).
- **U6-20** (P2-6: the inventory's silent shapes; the undeclared family exports `email=`).
- **U6-22** (P3-4: residual carried quotes).
- **U6-23** (P3-5: other id-bearing refusals).
- **U6-02 and U6-03** (P3-1: recursion volume and the fo drift).
- **U6-07** (P3-2: the multiplied work bound).
- **U6-26** (P3-7: the G.53 register in the real workspace).
- **U6-25** (docs).
