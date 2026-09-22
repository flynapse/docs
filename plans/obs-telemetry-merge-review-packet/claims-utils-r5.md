# Claims packet — utils review round 5 (`10651dc..8572635`)

Independent adversarial review (Opus), 2026-09-21. Read-only against every real tree. Each commit was
`git archive`d into the private scratch `scratchpad/utils-review-r5/`, and every mutation ran against a
scratch copy. Each copy was restored and md5-checked against the HEAD blob after each run. The range grew
from `10651dc..1ca934f` (15 commits) to `10651dc..8572635` (18 commits) mid-review, on the controller's
instruction.

| repo | worktree | branch | range | commits | flynapse-otel under test |
|---|---|---|---|---|---|
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `10651dc..8572635` | 604a061, a0eae53, 0b94aef, 7b0a72c, a97f867, 38aba9d, e0f73de, 5f3dbe3, e4637d4, 3b535da, 6a17811, 02a0646, 80dc186, 91fcea8, d7e1541, 1ca934f, 255848e, 26e7126, 8572635 | archive of `96edc86` (HEAD at review time). `1ca934f` was also run against `cfed17d` and `0dc80c5`. |

**How it was run.**

- Lane: `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider`.
- Environment: `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`, with `LOGURU_DIAGNOSE`/`LOGURU_BACKTRACE` unset.
- Paths: `PYTHONPATH=<archive>:<flynapse-otel archive>`, cwd = the archive root, and a fresh `PYTHONPYCACHEPREFIX` for every run.
- Reporting: a session plugin printed `rootdir`, `utils.__file__` and `flynapse_otel.__file__` for every run, and every exit status is pytest's own.
- Deselected in the archive sweep: two tests that need the real workspace. They were then run separately in a posed workspace (a scratch clone of utils-obsm on branch `obs-merge`, with the real siblings symlinked read-only):
  - `test_cross_repo_reads_name_their_checkout.py`;
  - one `test_root_anchoring` case.

**Each commit is green at its own HEAD** (full suite, exit 0, `utils.__file__` = that archive):

| commit | passed | skipped | commit | passed | skipped |
|---|---|---|---|---|---|
| 10651dc (base) | 1726 | 10 | 6a17811 | 1747 | 11 |
| 604a061 | 1726 | 10 | 02a0646 | 1748 | 11 |
| a0eae53 | 1730 | 10 | 80dc186 | 1755 | 11 |
| 0b94aef | 1730 | 11 | 91fcea8 | 1755 | 11 |
| 7b0a72c | 1730 | 11 | d7e1541 | 1756 | 11 |
| a97f867 | 1735 | 11 | 1ca934f | 1758 | 11 |
| 38aba9d | 1736 | 11 | 1ca934f vs fo `cfed17d` / `0dc80c5` | 1758 / 1758 | 11 / 11 |
| e0f73de | 1739 | 11 | 255848e | 1758 | 11 |
| 5f3dbe3 | 1739 | 11 | 26e7126 | 1757 | 11 |
| e4637d4 | 1739 | 11 | 8572635 | 1760 | 12 |
| 3b535da | 1743 | 11 | | | |

The skips are sibling-dependent: 8 or 9 inventory cases and 3 `test_root_anchoring` cases. With an
archive of copilot-mro-obsm `ffc49de9`'s `copilot_mro/` beside it, the inventory file ran 16 passed and 0
skipped at `8572635`.

**The G.53 register (posed workspace, today's sibling HEADs).** The register pins drift in both
directions, so its result depends on the siblings' state at the time of the run:

- `7b0a72c`, `e4637d4` and `1ca934f` are red today on the debt test and the witness equality, because the siblings paid their debt later;
- `255848e` and `8572635` are 19 passed;
- judged against the sibling commit times, each commit was green when it landed, except in two windows: `5f3dbe3` between 08:29 and 08:37, and `1ca934f` between 09:11 and 09:16.

---

## Findings, ranked

**No P0. No P1.** Every r4 probe re-run clean at `1ca934f`: `p_crash`, `p_thread`, `p_safe_lines`,
`p_asyncio_cb`, `p_url` and `p_stdlib`, and the r4 `p_sinks` cases 1, 2, 4, 5, 6 and 7. The three
residuals that remain are all declared:

- `p_script_pattern` configures loguru before `import utils`;
- `p_utils_then_add` adds its own `logger.add(sys.stderr)`;
- `p_sinks` case 3 is a partial quote (see P2-3).

### P2-1 — The "no file reads at log time" half of M-STACK-HEADERS is guarded by content only (severity 1)

This is a survived mutant. At `utils/_exception_text.py:44`, MA23 changes `frame_headers` to
`traceback.extract_tb(tb)`, which reads every frame's source line through `linecache` and then emits
the same headers. The FULL suite stays green: **1758 passed, exit 0**, restored and md5-checked.

The guards are `test_a_frame_compiled_under_another_files_name_does_not_read_that_file`
(`test_failure_fields.py:172`) and `test_no_file_a_frame_or_a_forged_header_names_is_read_onto_stdout`.
Both assert only that the named file's CONTENT is absent from the output. They do not assert that the
file is never opened, which is what the name and the ruling promise.

The behaviour is right today: an audit-hook probe saw **zero** `open` events from `frame_headers`,
`rendered_failure` and `failure_fields` across a cause-and-context chain, an ExceptionGroup and a
1000-frame RecursionError.

The fix is to install a `sys.addaudithook`, or to patch `linecache.getline`/`updatecache`, in the test,
and to assert zero reads.

### P2-2 — An exception captured as a keyword is withheld from the extra and not from the message its own placeholder built (severity 2)

`utils/observability/log_bridge.py:159`, with the safe sink at `_loguru_default.py:75`. The call is
`logger.error("failed: {err}", err=exc)`. The JSON line carries `"message": "failed: S_A1 kwarg-format"`
beside `"err": "ValueError"`. The OTLP in-memory exporter shows the same body, and the safe sink and the
human sink write it too.

The patcher holds the object in `record["extra"]` yet never applies `withheld_exception_text` for it.
This is the exact shape P2-5 targeted, and it is not in the declared residuals (those name only
caller-written `{e}` without the object). `rg` found no such call in any obsm tree today.

The fix: for each exception found in extras, run `withheld_exception_text(message, obj)`.

### P2-3 — Extras-as-types covers `list`/`tuple`/`dict` values only (severity 2)

Probed on JSON, human and OTLP, with each value going out through `flatten`'s `str(value)` at
`log_bridge.py:135`:

- a `set`/`frozenset` of exceptions;
- a `deque`;
- an exception used as a dict KEY;
- a dataclass holding one;
- a finished `asyncio.Task` or a `concurrent.futures.Future` — `<Task finished ... exception=ValueError('S_B6 ...')>`.

Each wrote the exception's message. Only depth over 3 is declared.

### P3 findings

- **P3-1 — A partial quote of a carried exception ships on every sink, including OTLP (severity 2).** Covers the first line of a multi-line `str`, `exc.args[0]` of a multi-arg exception, and a botocore-shaped `response["Error"]["Message"]`. Also a quote of a `raise … from None` suppressed `__context__`, which `_links` skips. The docstring lists what counts as a quote, so this is declared by omission only. Short (<8 char) secrets survive next to `&`, `@` or letters (`hunter2s`); the test pins that on purpose.
- **P3-2 — A crash after `import utils; logger.remove()` is silent (severity 3, new in a97f867).** The crash exits with rc=1 and zero bytes of output. The hook routes into a loguru that has no sinks. Before the range the interpreter printed the traceback. There is no such call site in the estate (lambdas' cognito app re-adds a sink).
- **P3-3 — `multiprocessing.Process` child crash prints message and source (severity 2).** `BaseProcess._bootstrap` calls `traceback.print_exc()` directly, bypassing `sys.excepthook`. Probed under both spawn and fork, with the child importing utils: `MPSECRET` was printed. `socketserver.handle_error` has the same shape. No `Process(` site exists in any obsm tree. The Pool path is safe.
- **P3-4 — `warnings.showwarning` is unrouted (severity 2, pre-existing, outside the diff).** It prints the message plus a `linecache` source line to stderr in every mode. pydantic 2.12's serializer warning carries `input_value=12345678`. No live trigger was found.
- **P3-5 — The reader-sanction revocation (80dc186) has five undeclared static bypasses (severity 1).** They are listed in claim U5-21. `importlib.import_module(...)` is covered by the declared "runtime-built".
- **P3-6 — The M-LEGACY-TENANT excuse logic is unpinned (severity 1).**
  - What holds: a planted NEW undeclared key (`user_id`) on an excused family at a copilot-mro site IS red at HEAD.
  - What is unpinned: MB3 (excuse by family, ignoring the key) and MB2 (excuse at utils call sites too) both survive the inventory file with the sibling present (16 passed). MB3 also passes the planted `user_id`.
- **P3-7 — An UNDECLARED histogram through the shim carries `tenant_id` (severity 2).** The auto-registered branch of `metrics.py:274` filters no keys, so `some_new_latency_seconds{tenant_id="t-leak"}` was exported. "A histogram never carries tenant_id" holds for declared families only. The AST inventory catches a new emission only with the sibling beside it: the check skips in standalone utils CI.
- **P3-8 — The inventory's utils limb is skipped standalone (severity 2).** Tests that iterate `[*_UTILS_EMISSIONS, *_sibling_emissions()]` skip WHOLE when copilot-mro-obsm is absent (9 skipped at `8572635`). That includes the utils half of `test_the_retired_families_stay_deleted` and `test_every_emitted_family_is_declared`. The docstring says the utils limb "ALWAYS runs … can never become a skip", but only the count floor does. The retired families stay behaviourally pinned by the metering tests (MB7 red).
- **P3-9 — Recursion output grew (severity 2, new in 1ca934f).** `frame_headers` does not collapse repeats, so a RecursionError's `failure_fields()["stack"]` is 1000 lines (~140 KB). `format_tb` collapsed it to about 4 lines plus `[Previous line repeated …]`. flynapse-otel's M-FAILURE-HOME copy is identical.
- **P3-10 — Files are still read at log time outside utils' helpers (severity 3; nothing ships).**
  - loguru's own ExceptionFormatter renders every exception record for every handler. A probe of the safe sink and the JSON sink saw `/etc/hostname` and `/etc/os-release` opened (frames compiled under those names).
  - The OTel SDK `LoggingHandler` in `_otlp_sink` runs `format_exception`.
  - 33 `traceback.format_exc()` sites remain: `dynamodb_service.py` has 32 (in `LEAK_BACKLOG`) and `migrate_weaviate_collection.py` has 1.
  - Content is withheld or stripped on every sink. The ruling's "no file reads at log time" holds only for `failure_fields`.
- **P3-11 — Per-tenant incompleteness term B cannot be rebuilt (severity 3, routed).** After `8572635`, `embedding_cost_usd_count` has no tenant, and the spend counter sums dollars, not calls. So "billed calls with no recorded price" per tenant cannot be derived (`llm-agents.json:353,358`, copilot-mro). The panel's A and B must both be repointed, and B only works fleet-wide.
- **P3-12 — A 3-line hunk blesses a drifted sibling in the G.53 register (severity 1).** Demonstrated in the posed workspace: a drifted core-obsm was flagged red. One `_ROOT_PY_DEBT` line plus dropping core-obsm from the witness set cleared both core-obsm failures. There is no merge-base ratchet, although flynapse-otel now has one. A debt entry for an absent checkout is never checked.
- **P3-13 — Worst case of the quote-withholding bound (severity 3).** 255 linked exceptions (group members or a context chain) against a 140 KB message containing `...` take **2.2–2.4 s** in the logging call. That is bounded, and down from r4's 12.8 s.
- **P3-14 — asyncio "Exception in callback" carries callback-argument reprs (severity 2).** A non-URL argument like `'password=S_H4pw'` ships. It is not exception text and not declared.
- **P3-15 — `import utils` loads no OTel, but the first record does (severity 3).** The pin is literally true: 0 OTel modules after `import utils`. The first log record imports 112 modules and takes 0.65 s, and a record whose import fails (at shutdown) is dropped.
- **P3-16 — False claim in 26e7126's commit message (severity 3).** It says copilot-mro "nothing there breaks first". It was red 09:21–09:35 until `a9149afb`; the controller already recorded this in Addendum 96.
- **P3-17 — URL rule gaps (severity 2, cross-repo: flynapse-otel `withholding.py`, not in this range).** The query keys `pass`, `otp`, `ticket`, `invite`, `email`, `t` are kept. So are path params (`;jsessionid=`), percent-encoded URLs, and `file://` queries.

---

## What I tried to break and could not

- **Hooks.**
  - `sys.excepthook`, `threading.excepthook` (including a chained `__cause__`) and `sys.unraisablehook` (`__del__`) all go through the safe sink as types and frame headers. The same holds after `setup_logging`.
  - A foreign hook is kept and runs after ours (MA3 and MA4 red).
  - A thread ending in `SystemExit` stays silent.
- **stdlib.**
  - `logging.lastResort` → loguru, with `exc_info` rendered as types and frames. `stack_info` and stdlib extras are dropped, not printed.
  - `basicConfig` still configures.
  - `InterceptHandler`: a carried `%s` quote is replaced; `stack_info` is not forwarded.
- **asyncio.** Neither "Task exception was never retrieved" (a 200-character message) nor a custom `call_exception_handler` message leaks. The reprlib `<Future finis...ValueError>` tail is covered.
- **ExceptionGroup.** Nested members quoted by `str` and by `repr` are replaced. The group message, member messages, `__notes__` and SyntaxError text never render.
- **URLs.** Userinfo is withheld for `redis://:pw@`, `amqp`, `mongodb+srv`, `postgresql+psycopg2`, IPv6 hosts and upper-case schemes. Secret-named query and fragment keys (`#access_token=`, `#token=`) are withheld, as are keys in extras.
- **`import utils` pulls in no OTel.** MA8 (an eager import) is red. No global tracer provider or logger provider is set by the first record.
- **M-LAZY-DYNAMODB consumer shapes.** Probed:
  - `from utils import dynamodb` (core `core/services/__init__.py:6`);
  - `from utils.dynamodb_service import dynamodb` (copilot-mro `amos_parser.py:2567`, inside its try);
  - the smoke test's `dynamodb.create_table = …`.

  All three resolve to the same object with 0 boto3 calls at import and one at first use. No `isinstance` or identity use was found.
- **Float spend counter.** `embedding_spend_usd_total` exports as OTLP `as_double` even after an int add. The unit `{USD}` is braced, so the Prometheus family name is unchanged. The estate has no CloudWatch EMF path (AWS metrics go OTLP → `otlphttp/cwmetrics`). MB4 (`int(value)`) is red.
- **Family tenant invariant.** MB6 is red. A call-site `tenant_id` on a declared histogram is dropped with one warning, and so is a `tenant.id` spelling.
- **Deleted families.** No emitter of `llm_tokens_per_request` or `embedding_request_duration` remains in any obsm tree.
- **Other histograms.** No remaining declared histogram, and none in api, shift-optimizer or telegram-bot, carries a tenant key. copilot-mro withholds `tenant.id` via `_HISTOGRAM_WITHHELD_KEYS`.
- **M-EMBED-INTERNAL.** MB5 (back to CLIENT) is red. No dashboard or iac file keys on the `azure_openai.*` span name or kind.

## What I did not test

- Any live collector, Prometheus, CloudWatch or AWS path. The Prometheus name translation is reasoned from the translator's rules, not run.
- Whether the httpx instrumentor is applied in every process that embeds. M-EMBED-INTERNAL's board count rests on it. It is declared in utils' `INSTRUMENTATIONS`; I did not check processes that bootstrap via flynapse-otel directly.
- The implementer's own claimed mutants that I did not re-run. Those rows say "implementer-claimed".
- `_core` fingerprinting (G.92, declared), and the hook installed between `import utils` and `setup_logging` logging twice (declared).
- A realistic `utils` primary in the posed workspace. The posing drops it, so three workspace-shape tests were excluded as artifacts of the posing.

---

## Claims table

Severity (this reviewer's scale): 0 = a content leak that ships, 1 = guard or lock integrity, 2 = a coverage gap, 3 = docs or process, — = nothing owed.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U5-01 | utils | `utils/embedding_service.py:188` | Embedding round-trip span is INTERNAL (M-EMBED-INTERNAL) | the httpx CLIENT child already counts the call; a CLIENT wrapper double-counted on the board | panel queries filter `SPAN_KIND_CLIENT` (`dependencies.json:25,41`); no consumer keys on the span name or kind | `test_the_azure_openai_round_trip_opens_an_internal_span`, `test_one_vector_search_is_one_client_span_from_utils_and_the_embedding_is_internal` | **yes** — MB5 (back to CLIENT): 3 failed | — | 2 | F1 | SETTLED (implementation); the board premise that httpx is instrumented everywhere is unverified |
| U5-02 | utils | `utils/dynamodb_service.py:312` | Lazy `.dynamodb` property, double-checked under `_init_lock` (M-LAZY-DYNAMODB) | import blocked about 2 s on IMDS | consumer probe: 0 boto3 calls at import, 1 at first use, same object for the core and copilot-mro import shapes | `test_importing_the_module_makes_no_boto3_call_and_first_use_makes_one`, `test_a_new_instance_constructs_on_first_access_exactly_once` | **yes** — MA19 (no second check): 1 failed | 3 (a failed init now surfaces at first use; `:355` still logs `format_exc`, in the backlog) | 0 | F2 | SETTLED |
| U5-03 | utils | `utils/llm.py:1265-1275`, `utils/observability/legacy_families.py` | `llm_tokens_per_request` and `embedding_request_duration` deleted, call site and declaration (M-LEGACY-DELETE, utils half) | the owner ruled delete | `rg` finds no emitter in any obsm tree | `test_the_tenant_comes_from_the_binding_not_from_a_parameter` (behavioural); `test_the_retired_families_stay_deleted` (`test_legacy_family_inventory.py:491`, skips without the sibling) | **yes** — MB7 (re-emit `embedding_request_duration`): 1 failed | — | 2 | F1 | SETTLED |
| U5-04 | utils | `tests/unit/observability/test_legacy_family_inventory.py:342` | The declared families are pinned by equality, and the `retire` set equals `_RETIRING_IN_COPILOT_MRO` | a count lock lets a swap through | 16 passed with the sibling present; 9 skipped without it | same file | implementer-claimed (not re-run) | 2 (the utils limb skips standalone) | 1 | F3 | PARTIAL — skipped in standalone CI (P3-8) |
| U5-05 | utils | `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py:594`, `:772` | `_ROOT_PY_DEBT` emptied of G.53 entries; witness set {api-obsm, core-obsm, copilot-mro-obsm} by equality (255848e) | a debt entry must go the day it is paid | posed workspace: 255848e and 8572635 are 19 passed; a posed core-obsm drift is red | `test_every_root_py_copy_is_either_identical_to_ours_or_recorded_as_owing`, `test_the_recorded_debt_is_still_owed`, `test_the_ported_trees_really_are_identical_to_ours` | **yes** — posed drift: red. A bless hunk (1 debt line plus a witness edit) turns it green, with no ratchet | 1 | 1 | F2 | PARTIAL — P3-12 |
| U5-06 | utils | `utils/_loguru_default.py:165`, `utils/_interpreter_hooks.py:50-63` | The safe default routes `sys.excepthook`, `threading.excepthook` and `sys.unraisablehook` through loguru (r4 P1-A) | the interpreter printed the message and source lines | r4 `p_crash` and `p_thread` are clean; new probe: a chained thread crash and a `__del__` are clean | `test_an_exception_nothing_caught_goes_through_the_safe_sink[main,thread,unraisable]`, `test_the_interpreters_hooks_go_through_the_sinks` | **yes** — MA1 (no routing): 3 failed; MA2 (threading dropped): 2 failed; MA21: 2 failed | — | 0 | F1 | SETTLED |
| U5-07 | utils | `utils/_interpreter_hooks.py:91` | A foreign hook is kept and runs after ours | an error reporter must still fire | chained and chained-before-utils cases | `test_the_interpreters_hooks_go_through_the_sinks[chained*]` | **yes** — MA3 (order reversed): 2 failed; MA4 (foreign hook dropped): 2 failed | — | 0 | F1 | SETTLED |
| U5-08 | utils | `utils/_interpreter_hooks.py:26` | Uncaught exceptions go only to loguru | — | `import utils; logger.remove(); raise` gives rc=1 and zero output; before, the interpreter printed | **none** | not recorded | 3 | 1 | F3 | OPEN — P3-2 |
| U5-09 | utils | (stdlib) `multiprocessing/process.py:330` | **Not taken:** a `Process` child crash is not routed | outside the three hooks | spawn and fork children that import utils print `MPSECRET` | **none** | not recorded | 2 | 1 | F3 | OPEN — P3-3 |
| U5-10 | utils | `tests/unit/observability/_subprocess_utils.py:24` | The subprocess runner strips `LOGURU_*` (r4 P2-7) | an exported `LOGURU_DIAGNOSE=NO` would satisfy the pin from outside | — | `test_the_runner_hands_no_loguru_setting_to_a_case` | **yes** — MA18: 1 failed | — | 0 | F2 | SETTLED |
| U5-11 | utils | `utils/_loguru_default.py:75`, `:89` | The safe sink applies the rules to the MESSAGE alone, URL rule included (r4 P2-1, P2-2) | the whole-line rules ate timestamps, levels and newlines | `p_url` and `p_safe_lines` are clean | `test_the_rules_read_the_message_and_never_the_rest_of_the_line` | **yes** — MA7 (no URL rule): 1 failed; MA9 (whole line): 1 failed | — | 0 | F1 | SETTLED |
| U5-12 | utils | `utils/_loguru_default.py:80` | `import utils` loads neither flynapse_otel nor OTel; the URL rule is imported at the first record | the package import builds the OTel stack | probe: 0 modules at import; 112 modules and 0.65 s at the first record; no provider is set | `test_importing_utils_does_not_import_the_telemetry_stack` | **yes** — MA8 (eager import): 1 failed | 3 (the cost moves to the first record) | 0 | F2 | SETTLED |
| U5-13 | utils | `utils/observability/intercept.py:85` | The stderr formatter's rules read `record.message` only | the whole-line rules rewrote the level and the name | — | `test_the_stderr_handler_applies_its_rules_to_the_message_alone` | **yes** — MA17: 1 failed | — | 0 | F1 | SETTLED |
| U5-14 | utils | `utils/_exception_text.py:107`, `:156` | `repr` quotes are replaced anywhere; a `str` of 8 or more characters anywhere; a shorter one only between delimiters (r4 P2-3) | `KeyError(1)` rewrote paths and numbers | `hunter2s` and `pw=hunter2&` survive by design | `test_a_short_str_is_a_quote_only_between_delimiters` | **yes** — MA15 (min 1): 1 failed | 2 (short secrets, partial quotes) | 0 | F1 | SETTLED; residual P3-1 |
| U5-15 | utils | `utils/_exception_text.py:205` | reprlib head and tail fragments of 4 to 32 characters beside `...` are replaced (r4 P2-4) | asyncio's callback body kept the message tail | r4 `p_asyncio_cb` is clean | `test_reprlib_truncations_of_a_quote_are_replaced`, `test_asyncios_callback_body_loses_the_truncated_tail_of_the_quote` | **yes** — MA14: 2 failed | 2 (other truncations declared; fragments over 32 characters) | 0 | F1 | SETTLED |
| U5-16 | utils | `utils/_exception_text.py:175` | Past 256 links the message is withheld whole | bounded work | worst case measured at 2.2–2.4 s in-call | `test_the_work_is_bounded_and_fails_closed` | **yes** — MA16 (no cap): 1 failed | 3 | 0 | F1 | SETTLED |
| U5-17 | utils | `utils/observability/log_bridge.py:159`, `:181`, `:184` | An exception extra becomes its class name, in list/tuple/dict up to depth 3 (r4 P2-5) | every sink wrote its `str` or `repr` | set/frozenset/deque/dict key/dataclass/Task/Future still leak on JSON, human and OTLP | `test_an_exception_passed_as_an_extra_is_written_as_its_type`, `test_the_human_sink_writes_an_exception_extra_as_its_type` | **yes** — MA12 (depth 0): 1 failed; MA20 (loop removed): 2 failed | 2 | 1 | F1 | PARTIAL — P2-3 |
| U5-18 | utils | `utils/observability/log_bridge.py:159` | **Not taken:** the message's quote of a kwarg-captured exception is not withheld | — | `logger.error("failed: {err}", err=exc)` gives the message leaking beside `"err": "ValueError"`, OTLP body included | **none** | not recorded | 2 | 1 | F1 | OPEN — P2-2 |
| U5-19 | utils | `utils/observability/log_bridge.py:121` (`flatten`) | Extra keys are URL-withheld (r4 P2-6) | a presigned URL used as a key went out verbatim | — | `test_a_url_in_an_extras_key_is_withheld` | **yes** — MA13: 1 failed | — | 0 | F1 | SETTLED |
| U5-20 | utils | `utils/_loguru_default.py:107`, `:166` | `logging.lastResort` → loguru; the root logger gets no handler (r4 P2-9) | a library's `logger.exception` printed message and traceback | `p_stdlib` is clean; stdlib extras and `stack_info` are dropped | `test_a_stdlib_record_with_no_handler_goes_through_the_safe_sink` | **yes** — MA5 (not replaced): 1 failed; MA6 (`exc_info` dropped): 1 failed | — | 0 | F1 | SETTLED |
| U5-21 | utils | `tests/unit/observability/test_utils_spans_withhold_exception_text.py:321` | Reader-sanction revocation resolves callees and targets by identity (r4 P2-10) | six spellings kept the sanction | reviewer plants that KEEP the sanction: `reader_module.__setattr__(...)`, `object.__setattr__(mod,…)`, `types.ModuleType.__setattr__(mod,…)`, `operator.setitem(mod.__dict__,…)`, `__builtins__['exec'](...)` | `test_the_reader_sanction_needs_every_binding_to_be_the_resolved_reader` | implementer-claimed (5 mutants); the reviewer's 5 new plants are not flagged | 1 | 1 | F1 | PARTIAL — P3-5 |
| U5-22 | utils | `docs/plans/g92-private-global-guard.md`, `tests/_foreign_global_seat.py` | G.92 loguru coverage stated as module globals, not `logger._core` (r4 P2-11) | wording | read | **none** | n/a | 3 | 1 | F3 | OPEN (docs; `_core` unfingerprinted, declared) |
| U5-23 | utils | `utils/weaviate_service.py` (class removed); `tests/unit/observability/test_weaviate_client_spans.py:991` | `WeaviateProvisioningError` deleted, never raised (26e7126; supersedes d7e1541's order pin) | no provisioning seat in utils | copilot-mro door test red 09:21–09:35 until `a9149afb` | `test_there_is_no_utils_private_provisioning_type`, `test_a_tenancy_refusal_is_quiet_and_a_provisioning_failure_counts` | **yes** — MB8 (class re-added): 1 failed | 3 (the commit message's "nothing breaks first" is false) | 0 | F2 | SETTLED |
| U5-24 | utils | `utils/_exception_text.py:44`, `utils/observability/failure.py:80` | `failure_fields()["stack"]` = `frame_headers(tb)`, headers only (M-STACK-HEADERS) | `linecache` reads whatever file a code object names | audit hook: 0 opens across chain, group and recursion | `test_the_stack_is_frame_headers_and_never_a_source_line`, `test_a_frame_compiled_under_another_files_name_does_not_read_that_file` (`test_failure_fields.py:172`) | **yes** for content — MA10: 3 failed; MA11: 2 failed. **NO** for reads — MA23 (`extract_tb`, reads every file) passes the FULL suite, 1758 passed | 1 | 1 | F1 | PARTIAL — P2-1 |
| U5-25 | utils | `utils/observability/log_bridge.py:252`; loguru handler; `utils/dynamodb_service.py` (32 sites); `utils/migrate_weaviate_collection.py:384` | Files are still read and full tracebacks still rendered at log time outside the helpers | out of the ruling's `failure_fields` scope | probe: `/etc/hostname` and `/etc/os-release` opened by `logger.opt(exception=…)` on the safe and JSON sinks; nothing ships | **none** for the reads; `LEAK_BACKLOG` for the 33 sites | not recorded | 3 | 1 | F3 | OPEN — P3-10 |
| U5-26 | utils | `utils/_exception_text.py:44` | Frames are not collapsed | — | RecursionError stack is 1000 lines (~140 KB); `format_tb` gave about 4; the flynapse-otel copy is identical | **none** | not recorded | 2 | 1 | F3 | OPEN — P3-9 |
| U5-27 | utils | `utils/observability/legacy_families.py:94` | `Family` refuses `tenant_id` on a histogram (M-LEGACY-TENANT) | a tenant label multiplies every bucket | the undeclared-histogram path still passes it (`metrics.py:274`, probe `some_new_latency_seconds{tenant_id="t-leak"}`) | `test_no_histogram_declares_tenant_id_and_the_family_type_refuses_one` | **yes** — MB6: 1 failed | 2 | 2 | F1 | SETTLED for declared families; PARTIAL overall (P3-7) |
| U5-28 | utils | `utils/observability/legacy_families.py:299`, `utils/llm.py:1272`, `utils/observability/metrics.py` | New `embedding_spend_usd_total{tenant_id,model}` counter, float, `{USD}`; shim value annotated float | the per-tenant cost must stay visible | OTLP `as_double` (probe); braced unit, so no Prometheus suffix; no EMF path in the estate | `test_per_tenant_embedding_spend_is_a_dollar_counter`, embedding metering tests | **yes** — MB4 (`int(value)`): 1 failed | 3 (per-tenant B term lost, P3-11) | 2 | F1 | SETTLED (float); panel repoint OPEN (copilot-mro) |
| U5-29 | utils | `tests/unit/observability/test_legacy_family_inventory.py:122`, `:553` | `_UNDECLARED_KEYS_OWED_BY_COPILOT_MRO` excuses three exact (family, `tenant_id`) pairs at sibling sites | copilot-mro still passes them until its lane lands | a planted NEW `user_id` key is red at HEAD | `test_every_emitted_attribute_key_is_declared`, `test_the_owed_keys_are_still_passed_and_still_undeclared` | **partly** — the plant is red, but MB3 (excuse by family) and MB2 (utils sites excused) survive | 1 | 1 | F1 | PARTIAL — P3-6 |
| U5-30 | copilot-mro | `deployment/observability-local/grafana/provisioning/dashboards/flynapse/llm-agents.json:353,358` | (consequence of U5-28) the panel still reads `embedding_cost_usd_sum` and `_count` by `tenant_id` | — | both lost `tenant_id` at 8572635; B per tenant cannot be derived | **none** | not recorded | 3 | 2 | F1 | OPEN — routed to copilot-mro (repoint) |
| U5-31 | estate | stdlib `warnings.showwarning` | **Not taken:** warnings are not routed | outside the ruling | pydantic 2.12 serializer warning prints `input_value=12345678` plus a source line in every mode | **none** | not recorded | 2 | 1 | F3 | OPEN — P3-4 |
| U5-32 | utils | `utils/_exception_text.py:107` | **Not taken:** partial and suppressed-context quotes | the docstring enumerates quote shapes | first line, `args[0]`, `Error.Message` and a `from None` context all ship (JSON, human, OTLP) | **none** | not recorded | 2 | 1 | F1 | OPEN — P3-1 |
| U5-33 | flynapse-otel | `flynapse_otel/withholding.py` (`withhold_url_secrets`) | Secret-name query-key rule (not in this range) | — | `pass`, `otp`, `ticket`, `invite`, `email`, `t`, `;jsessionid=`, percent-encoded and `file://` queries are kept | flynapse-otel's own | not re-run | 2 | 1 | F1 | OPEN — P3-17, cross-repo |
| U5-34 | utils | `tests/unit/observability/test_utils_logs_no_exception_text.py:76`, `:100` | `LEAK_BACKLOG` and `EXCEPTION_SEATS` are membership registers with no equality or merge-base ratchet | pre-existing design | adding a backlog module or a `(module, function)` seat is a one-line bless; a stale seat IS caught | `test_every_exception_seat_is_a_live_attachment_and_nothing_else_is_excused`, `test_the_backlog_names_only_modules_that_still_leak` | implementer-claimed | 1 | 1 | F3 | ASSERTED |

**Totals: 34 claims — 16 SETTLED (13 of them tier 0), 1 ASSERTED, 7 PARTIAL (U5-27 counted here), 10 OPEN.** I ran 30 mutants
and 2 plants myself:

- 29 went red: MA1–MA22, MB4–MB8, the posed register drift, and the new-key plant;
- 3 mutants survived: MA23 (full suite, 1758 passed), MB2 and MB3.

Every mutant was restored and md5-checked against its HEAD blob.

---

## Open claims, tier 2 first

**Tier 2**

- **U5-30** — the embedding-spend panel's A and B terms read histogram series that lost `tenant_id` at 8572635. The per-tenant B (billed calls without a price) can no longer be derived from any series. Owner-visible: "cost stays visible" holds for A only. Routed to copilot-mro.
- **U5-27 (partial)** — "a histogram never carries tenant_id" holds only for declared families. The shim's undeclared-histogram branch passes every key.
- **U5-01 (premise)** — M-EMBED-INTERNAL's board arithmetic assumes the httpx instrumentor is applied in every process that embeds.

**Tier 1**

- **U5-24** (P2-1: the file-read half of M-STACK-HEADERS is unguarded).
- **U5-18** (P2-2: a kwarg-captured exception is quoted in the message).
- **U5-17** (P2-3: set, deque, dict key, dataclass and Task extras).
- **U5-21** (five revocation bypasses).
- **U5-29** (the excuse logic is unpinned).
- **U5-05** (the register bless hunk, no ratchet).
- **U5-32** (partial and suppressed-context quotes).
- **U5-31** (warnings).
- **U5-09** (multiprocessing child crash).
- **U5-26** (recursion volume).
- **U5-25** (loguru and OTel still read files; 33 `format_exc` sites).
- **U5-08** (silent crash after `logger.remove()`).
- **U5-33** (URL key list, flynapse-otel).
- **U5-34** (membership registers).
- **U5-22** (docs).
