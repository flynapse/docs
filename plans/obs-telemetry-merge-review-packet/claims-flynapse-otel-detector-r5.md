# Claims packet: flynapse-otel review r5 (shared exception-text detector, URL withholding, failure home, drop views)

Independent adversarial review by Opus, 2026-09-21. It was read-only throughout. No code tree was edited, checked out or committed. Every mutation ran in a private scratch copy, was restored from a backup, and was md5-checked against the `git show 34c814a:<path>` blob after each run; every restore matched.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` (clean, HEAD `34c814a`) | `main` | `e8d1df1..34c814a` | `23c9344` `5df2269` `73ed641` `cfed17d` `d15350a` `de501a8` `0dc80c5` `f1bd35b` `a52a872` `96edc86` `be3964f` `34c814a` |

**How I ran it.**
- Each commit was extracted with `git archive <sha>` into `scratchpad/otel-review-r5/c/<sha>`, with the sibling repos (`utils`, `core`, `dashboard`) symlinked beside it.
- The command, from the tree root, was: `DEBUG=false PYTHONPYCACHEPREFIX=<fresh dir> PYTHONPATH=<tree> /home/aditya/Code/flynapse-otel/.venv/bin/python -m pytest -p no:cacheprovider`. Every `__pycache__` was cleared first.
- I checked pytest's own exit status (`set -o pipefail`) on every run.
- `flynapse_otel.__file__` pointed into the scratch tree on every run, and `rootdir` was `…/otel-review-r5/c/<sha>`.

**Every commit is green at its own HEAD.** The one skip is environmental: `test_root_anchoring`'s "other checkout" proof finds no sibling checkout in scratch.

| commit | result |
|---|---|
| e8d1df1 (base) | 414 passed, 1 skipped, 1 xfailed |
| 23c9344 | 437 passed |
| 5df2269 | 442 passed |
| 73ed641 | 452 passed |
| cfed17d | 452 passed |
| d15350a | 1554 passed |
| de501a8 | 1620 passed |
| 0dc80c5 | 1653 passed |
| f1bd35b | 1653 passed |
| a52a872 | 1659 passed |
| 96edc86 | 1767 passed |
| be3964f | 1769 passed |
| 34c814a | 1832 passed |

Each commit after the base also had 1 skipped and 1 xfailed, the same as the base.

**Estate scans** were read-only. Each repo's source roots were extracted with `git archive HEAD` from `utils-obsm`, `core-obsm`, `api-obsm`, `copilot-mro-obsm`, `telegram-bot` and `shift-optimizer`. Each snapshot was scanned by the `de501a8` detector and by the `34c814a` detector, under one policy: `failure_fields` only.

**Verdict: FIX-FIRST.** No content leak ships today. Two things stop a clean pass:
- The `34c814a` precision change narrows what counts as a leak on a resolution that is not a proof.
- The per-repo `Policy` is an unvalidated, unratcheted way to bless a leak.

---

## Findings, ranked

### No P0

I measured every live call site where the new return-slot rule drops an argument that carries exception text:
- utils: 2 sites.
- telegram-bot: 10 sites.
- copilot-mro: 12 sites.
- core, api and shift-optimizer: none.

All 24 resolve completely: no decorator, no partially followed binding, no `self.` dispatch. Compared with `de501a8`, the precision change removed exactly 8 finding keys from the estate. I read each one, and all 8 are over-reports removed:
- 7 are `copilot_mro/app/api/health_check.py` calling `unhealthy_body(e)`. That function returns only `type(exc).__name__` and `**fields`.
- 1 is `scripts/certify_model_profile.py::main`. `report_facts` builds its facts from `probe.passed` and `probe.raw`, never from `probe.detail`.

The new rules added no finding to any of the six repos.

### P1-1: return slots trust a resolution that is not a proof (34c814a)

**Where.**
- `flynapse_otel/testing/exception_text/_scan.py:155-171`, `returned_slots`.
- It gets its callees from `resolve(..., precise=True)` at `_scan.py:95-132`.
- They are used at `_module.py:678-690`.

The docstring says a call's value "carries only the arguments landing in parameters some provably reached function returns". In fact, "precise" resolution is the union of the bindings the resolver *can* follow. Every binding it cannot follow is silently dropped:
- an import of a module outside the scan;
- a parameter, `for` or `with` target of the same name;
- `name = wrapper(name)`, or a rebinding to an imported external;
- a decorator (all of them are ignored);
- `self.x`, which resolves to every function named `x` in the *module* and never to an override in another module;
- `_lookup`, which returns the first `def` by name and ignores a later rebinding in that module;
- `staticmethod`, recognised only by its literal name;
- a positional-only parameter, matched by keyword.

Before `34c814a`, those same partial resolutions only mattered for callees that returned *nothing* (the old text-free rule). Now they matter for every callee that returns *any* other parameter.

**Measured.** These 12 plants are caught by `de501a8` and missed by `34c814a` (the ids are the plant names in the list below):

| id | plant |
|---|---|
| A20 | a decorator that appends `args!r` to the return |
| A21 | `try: from vendor import describe` / `except ImportError: def describe(label, exc): return label` |
| A22 | a def rebound to an imported external |
| A23 | `describe = instrument(describe)` |
| A24 | `def run(describe=describe)` |
| A25 | `for describe in (external,)` |
| A26 | `self.describe_failure(...)` overridden in a subclass in another scanned module |
| A28 | a cross-module def rebound after its definition |
| A30 | a positional-only parameter and `**kw` with the same name |
| A31 | `static = staticmethod` |
| A32 | a lambda rebound conditionally to an external |
| A34 | `functools.singledispatch` with a registered overload |

**Operator view.** Nothing appears. A leak added behind a decorator, an import fallback or a subclass override reconciles clean in all six repos.

**Fix.** Sanction a narrowing only when every binding of the callee name is a def, a lambda or an import that resolves into the scan. Also require that:
- the def has no decorator outside a transparent allowlist (`staticmethod`, `classmethod`, `functools.wraps`/`cache`/`lru_cache`);
- `self.`/`cls.` dispatch takes the union over every same-named method in the whole scan, or refuses;
- `_lookup` refuses a module that rebinds the name.

In every other case, return `None`, which means every argument is read.

### P1-2: `Policy` is an unvalidated bless channel, and nothing ratchets it

**Where.** `_model.py:101-122`. `BoundedReader` and `Policy` have no validation. The register ratchet (`_ratchet.py`) covers `Accepted` entries only.

**Measured.** Under the base policy, 8 of the 9 attacks below produce findings. Under the attack policy, every one of those 8 is silent. P9 is a no-op, because an empty `column_recorders` is already the default.

| attack | policy |
|---|---|
| P1 / P8 | `refusal_types={"Exception"}` blesses every `HTTPException(detail=str(exc))` and every echo of a parameter |
| P2 | `refusal_types={"BaseException"}` |
| P3 | a reader declared with sinks `{log, output, span, body, raise, column}` |
| P4 | a reader named `str` from `builtins` |
| P5 | a reader named `format_exception` from `traceback` (the log finding goes; the source finding stays) |
| P6 | any repo-local module declared as a reader's source |
| P7 | `exception_parameter_names=frozenset()` |

A repo-local reader's body is never checked for being bounded. `block_save_failure_fields` returns pydantic `loc` paths, which can include keys of a user dict.

This is the lever the register ratchet was built to remove (core F3's bless hunk, r6 M1 and M4), but it has more power and one line changes it.

**Fix.**
- Add a `Policy.__post_init__` that refuses:
  - broad refusal types (builtin exception bases);
  - reader sinks outside `{log, output}`, unless a reader appears in an explicit span allowlist;
  - builtin or renderer names as readers;
  - an `exception_parameter_names` that is not a superset of the default.
- Add a `policy_problems(policy, baseline)` ratchet next to `ratchet_problems`.
- Optionally, verify declared readers by their own return slots.

### P2-1: the corpus does not pin the precision boundaries or the sanction widenings

Each of these one-line mutants of `34c814a` leaves `tests/unit/testing` and `tests/unit/packaging` green (1282 passed):

| mutant | what it breaks |
|---|---|
| MU03 | an unknown keyword never lands in `**kw` |
| MU04 | a surplus positional argument never lands in `*args` |
| MU05 | `reaches` needs *all* resolved functions, not any |
| MU06 | a `**mapping` lands nowhere |
| MB01 | generator callees are treated as returning nothing |
| MB05 | "precise" is ignored, so a unique-tail resolution can sanction |
| MU12 | `isinstance(e, <any type>)` narrowing blesses a body |
| MU13 | a handler naming *any* refusal type blesses (`except (Refusal, Exception)`) |
| MU14 | a *mutated* opener-kwargs constant still resolves |
| MU48 | `strerror`/`filename` are sanctioned as numeric |
| MU70 | a positional `{"error": …}` dict to a column recorder is ignored, although the plan claims that rule |

At HEAD, plants E02 to E07, A09 and A10 all pass and would fail under these mutants, so they are ready-made corpus rows. A "must stay a leak" row is also needed for:
- a mixed refusal and non-refusal handler;
- non-refusal `isinstance` narrowing;
- `exc.strerror` in a log line.

### P2-2: the ratchet is a no-op on the base branch, and part of its git failure path is unpinned

**Where.** `_ratchet.py:58-80`, run in synthetic scratch repositories.

**Passes that should not:**
- Growth committed on `main` with `against="main"` passes (R1). This estate commits directly on `main` and `obs-merge`.
- A branch fast-forwarded into local `main` passes (R2b).
- `against="HEAD"` or the branch's own name passes (R9).
- A renamed register returns `None` (R4), which the caller may treat as "no baseline".

**Unpinned.** Mutants MU60 (`ls-tree` failure returns `None`) and MU61 (`show` failure returns `None`) both survive. Only a failing `merge-base` is pinned (K08).

**Undeclared.** Key granularity: fixing one leak and adding another under the same `(path, qualname, rule)` passes at the same count (R3).

**Date check.** The word-boundary regex skips `9999-12-31Z`, `v9999-12-31` and `2026-09-21x`.

**Correctly refused:**
- r6 M1 (a repaired key re-added, with or without removing it from REPAIRED);
- r6 M4 (a key swap);
- core F3's bless (any new key, whatever plan file it cites);
- `9999-99-99`;
- `2026-13-01`;
- a shallow depth-1 clone;
- a detached HEAD.

**Fix.**
- Refuse when the merge-base equals HEAD while `against` names a local ref, or require a remote-tracking ref.
- Pin the `ls-tree`/`show` raise.
- Make `None` an explicit opt-in.
- Declare the key-granularity limit.

### P2-3: realistic shapes missed at HEAD that no declared limit covers

- **`raise type(exc)(f"sync failed: {exc}") from exc`** and **`raise exc.__class__(...)`** (D01, D02). The raise rule sees only uppercase construction names (`_module.py:1276-1301`). It is a common Python idiom; the estate has 0 sites today.
- **A door chosen by a conditional**, `emit = logger.error if bad else logger.warning`, then `emit(..., exc)` (D03). `_classify_value` (`_module.py:927`) ignores `IfExp`/`BoolOp`, and `_escapes` does not count them, so neither `log.caught-text` nor `log.door-as-value` fires. **The shape exists in the estate** at `utils/utils/llm.py:339`; its payload is not exception text today.
- **Cross-module stashes** (S01, S02, S04):
  - `ContextVar` set in module A and read in module B;
  - a module list mutated from another module;
  - an attribute stored on an imported module.

  The package docstring says "a ContextVar.set and a mutation of a name another scope binds are followed", with no "within one module". That is an overclaim, and the realistic usage is cross-module.
- **Routes and handlers not seen:**
  - `add_api_route` (C40);
  - `add_exception_handler(X, module.handler)` (C41);
  - `FastAPI(exception_handlers={…})` (C42);
  - response `headers=` (C38, C39).
- **A record-typed parameter whose exception class lacks the Error, Exception, Exc, Failure or Warning suffix** (`t: ReadTimeout`, C46). Its field reads are sanctioned (`_facts.py:116-125`, `_module.py:613-620`).
- **Vocabulary with no estate use today:**
  - structlog `aerror`/`ainfo`/`msg`;
  - `logger._log`;
  - rich `Console().print_exception()`;
  - `LoggerAdapter(logger, {"err": str(exc)})`;
  - `os.fdopen(2).write`;
  - `warnings.showwarning`;
  - `partial(logger.error, …)(exc)`;
  - a walrus-bound door;
  - `operator.methodcaller("error", …)`.

### P2-4: URL withholding residuals (0dc80c5)

`flynapse_otel/withholding.py:216` and `:518-566`.

- **Whitespace inside a query ends the run.** In `https://h/p?q=a b&token=S3CR3T`, everything after the space is unanchored and ships (U40). This happens when app code builds a URL with an f-string from user text.
- **A password whose part before the first `/` or `?` is all digits** is read as a port: `postgres://admin:2024/S3CR3T@db` (U04, U05).
- **Secret names not in the vocabulary:** `pass`, `ticket`, `assertion`, `SAMLResponse`, `otp`, `code_verifier` (U28 to U32, U17).
- **Double encoding** (U21, U23) and **scheme-relative userinfo** (U11).
- **11 of the 14 `SECRET_PARAMETER_MARKERS` can each be deleted with every test green.** Only `sig`, `token` and `key` are pinned; `amz`, `goog`, `credential`, `secret`, `password`, `passwd`, `pwd`, `auth`, `session`, `jwt` and `hmac` are not.

### P3 (docs, process and defence in depth)

- **Drop views (`bootstrap.py:86-95`) name only the new-semconv histograms.** Under the `http/dup` override, which `bootstrap.py:70` explicitly supports, urllib3 (`instrumentation/urllib3/__init__.py:335-345`) and ASGI also export `http.{client,server}.{request,response}.size`. No deployment sets `http/dup` today. The view set is pinned by equality, and MV01 (views removed) turns 5 tests red.
- **Isolation guard gaps.** Three changes all leave `tests/unit/packaging` green:
  - MB02: `live.py` importing the dev-only `opentelemetry.test`;
  - MB03: `importlib.import_module("." + name, __name__)` inside a module `__getattr__` in `flynapse_otel/__init__`;
  - MB04: `importlib.import_module(".testing.live", "flynapse_otel")` in a runtime module.

  No consumer repo has a guard against its own production code importing `flynapse_otel.testing`.
- **Rescan claim undercount (plan step 2c).** The plan says the precision change dropped "health_check's seven". It dropped eight. The eighth is `scripts/certify_model_profile.py::main` `helper.caught-text`, a **registered** copilot-mro DEBT key (`tests/unit/observability/_mro_exception_text_debt.py:502`), so it goes stale on adoption.

  The same flow really does print `probe.detail`, which holds exception text: from `Report.add` and from `print_record`'s observations. The shared detector cannot see that print, because of the record-parameter field sanction and a non-unique `add` tail. The conversion will therefore delete a register entry whose leak is still live.
- **The log boundary (`withhold_log_record`, `withholding.py:481`) withholds a rendered traceback only in a `str` body.** In an attribute value, a dict body or a list body, the message ships (B2, B3, B6). The docstring says "exception text"; it should say "the body's".
- **Other small items:**
  - `frame_headers` renders all 1000 frames of a `RecursionError` and never collapses repeats (size only);
  - `format_last` is dead vocabulary, because `traceback` has no such function;
  - `withhold_url_secrets` is linear, but about 1.8 µs per character on dense ` ?a=` text (2 MB takes 3.7 s).

---

## What I tried to break and could not

- **`failure.py` reads no source.**
  - Setup: `linecache.getline/getlines/updatecache/checkcache/lazycache` and `builtins.open` were spied, and `<planted>` was planted in `linecache.cache`.
  - Shapes: exec-compiled, chained, `ExceptionGroup`, `RecursionError`, and code compiled under a real file path.
  - Calls: `failure_fields`, `rendered_failure`, `frame_headers` and `withheld_exception_text`.
  - Result: zero reads and no planted text on any shape.
- **The parity test is real equality** at `be3964f`.
  - `_same` compares every field, `stack` included, every renderer and the text withholder with `==`.
  - utils `1ca934f` is standalone (it does not import flynapse_otel), so the test is not vacuous.
  - These mutants each turn it red: MB06 (`format_tb` source lines, 50 red), MB07 (`_MIN_FREE_QUOTE` 9, 1 red), MB08 (`_MAX_TRUNCATED` 16, 20 red) and MB09 (`__context__` dropped, 1 red).
- **The ratchet** holds against r6 M1 and M4, core F3's bless, `9999-99-99`, `2026-13-01`, a shallow depth-1 clone and a detached HEAD, where `against` is a real base. These mutants are red:
  - MB16 (RE-ADDED only when absent from the baseline);
  - MB17 (date regex);
  - MB18 (partial-stale);
  - MU59 (future date).
- **The corpus.**
  - It asserts both ways, and clean rows are held to an exact rule set.
  - No row is unparseable.
  - 43 of my 70 batch-A mutants turn it red, including every log level, the binder, record door, opener and writer removals, `HTTP_EXCEPTIONS`, the body and debug switches, the stream alias chain and the splat checks.
  - All 47 copilot-mro r6 plants and all 52 core r6 F7 plants are rows, and all pass. The latter are 47 leak, 2 clean stash and 3 declared-limit rows.
- **Estate shapes the precision change keeps.** A01 to A15 are caught: f-string, `.args`, list, dict, `str(p)[:50]`, a local container, a `self` field, `*args`, `**kwargs`, a keyword-only template, recursion, a `self` method, a callee that logs the parameter itself, and a cross-module callee.
- **URL withholding holds for:**
  - userinfo with `@` or `/`;
  - IPv6, IDN and uppercase schemes;
  - fragment tokens;
  - `code`, `X-Amz-*` and Azure `sig`;
  - a nested encoded `redirect_uri`;
  - glued JSON;
  - tab and NBSP separators;
  - multi-host MongoDB, `git+ssh` and AMQP;
  - bytes;
  - `;`-separated parameters.

  Pathological 1 to 2 MB inputs stay linear.
- **Drop views:** MV01 (views removed) turns 5 red, and **live views:** MV02 (`LiveSpans` in `on_end`) turns 5 red. Both reproduce the implementer's L1 and LV1.
- **No inline-suppression mechanism exists** in the detector. `# noqa` and `# pragma` bless nothing.

## What I did not test

- The live bootstrap under `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup`. The old-semconv export claim is read from the pinned instrumentor source; I did not measure it.
- ASGI's metrics, because the instrumentor is not installed in this venv.
- Any consumer repo's adoption: no repo imports the detector yet.
- The implementer's own 90 + 16 + 10 mutation tables, row by row. I spot-checked with independent mutants instead.
- `pre_boundary`'s `deepcopy` failure path.
- `withheld_exception_text` beyond the parity shapes.
- P2-5's key-collision merge. It is covered by the implementer's mutants; I did not re-mutate it.

## Plants (162), at HEAD 34c814a

**Precision.** A01 to A15 are caught.

| id | at HEAD | at `de501a8` |
|---|---|---|
| A20, A21, A22, A23, A24, A25, A26, A28, A30, A31, A32, A34 | **missed** | caught |
| A08 (store on `self`, returned via another method) | missed | missed |
| A29 (a closure factory) | missed | missed |
| A27, A33 | caught | caught |

A40 (`failure_text(label, exc)`) is clean, and correctly so. A missed plant is a regression only when `de501a8` caught it.

**General (80 plants).** 64 are caught. The 16 misses are:
- C08, C09, C10: structlog `aerror`, structlog `msg`, `logger._log`;
- C38, C39: response headers;
- C40, C41, C42: `add_api_route`, a handler registered by attribute, `exception_handlers=`;
- C43: `add_note`;
- C44, C45: a lowercase class alias and `self.error_type`, both declared;
- C46: a suffix-less exception type used as a record;
- C53: `os.fdopen`;
- C55: LoggerAdapter extra;
- C61: metric attributes, declared;
- C65: rich `print_exception`.

The caught plants include:
- loguru `opt`/`bind`/`patch`/`contextualize`/`lazy`;
- structlog keyword arguments;
- `exception`/`exc_info` variants;
- `!r:>40.200`, `%r` and `str.join`;
- `json.dumps(exc.__dict__)`, `vars(exc)`, `__cause__` and `__context__`;
- `except*`, `TracebackException` and `exc_info()` unpacking;
- walrus, comprehension and `match`;
- decorators and async-generator SSE;
- `suppress` followed by a later use;
- `__str__` delegation and dataclass `repr`;
- cross-function helpers, the global dict stash and hooks;
- `future.exception()` and `gather(return_exceptions=True)`.

**Record (3 plants).** R02 is caught. R01 and R03 (a record-typed parameter's field returned) are missed at both commits.

**More (33 plants).** 23 are caught. The misses are:
- D01, D02: `raise type(exc)(…)` and `exc.__class__(…)`;
- D03: an `IfExp` door;
- D04: `partial(door)(…)`;
- D09: `showwarning`;
- D10: `methodcaller`;
- D12: a walrus-bound door;
- D21, D24, D25: a returned value, a class-name stash and a self-import stash, all declared.

**Stash (8 plants).** S03, S05, S06 and S07 are caught. S01, S02 and S04 (cross-module) and S08 (`threading.local`, declared) are missed.

**Precision, second set (7 plants).** E02 to E07 are caught; each is a missing corpus row. E01 (`return locals()`) is missed at both commits.

**URL (50 plus 10 timing).** The 15 leaking cases are:
- U04, U05: a digits-only password prefix;
- U11: scheme-relative userinfo;
- U12: no scheme, out of design;
- U15: a value-only fragment;
- U17, U28 to U32: names outside the vocabulary;
- U21, U23: double encoding;
- U27: fullwidth characters;
- U35: `;jsessionid=`;
- U36: a path token, which telegram-bot handles itself;
- U40: whitespace inside a query;
- U48: a Bearer header, out of scope.

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R5-01 | flynapse-otel | `_scan.py:155-171`, `:95-132`; `_module.py:678-690` | A call's value carries only the arguments landing in parameters a "provably reached" callee returns | copilot-mro's `failure_text(label, exc)` and `unhealthy_body(e)` were over-reports | 12 plants regress relative to `de501a8` (A20 to A26, A28, A30 to A32, A34); the 24 live estate sites resolve completely, so nothing leaks today | the corpus's 4 calibration rows | yes, and the property **fails**: 12 leak plants go silent; MU03, MU04, MU05, MU06, MB01 and MB05 survive the corpus | 1 | 1 | F1 | **REFUTED**: "provably reached" is not proven (P1-1) |
| R5-02 | flynapse-otel | `_model.py:101-122` | A repo passes `Policy` (readers, refusal types, recorders, parameter names), unvalidated | Each repo keeps its own inputs | 8 policy attacks silence real leaks (P1 to P8); a local reader's body is never checked | none | not applicable: no guard exists | 1 | 2 | F1 | **OPEN** (P1-2) |
| R5-03 | flynapse-otel | `_module.py:442-443`, `:463-489` | Refusal sanctions: a handler of refusal types only, and `isinstance` narrowing | Designed refusal channels are clean | Disabling them turns rows red (implementer S11/S12); widening them does not | corpus refusal rows | partial: MU12 and MU13 (widenings) survive | 1 | 1 | F1 | **PARTIAL** (P2-1) |
| R5-04 | flynapse-otel | `_module.py:1250-1259` | An opener splat resolves only to a module constant bound once and never mutated | A mutated constant may lose the literals | Mutation is not pinned | corpus splat rows | partial: MU14 survives | 1 | 1 | F1 | **PARTIAL** |
| R5-05 | flynapse-otel | `_vocabulary.py:93`, `_module.py:1102-1112` | Only `returncode`/`errno` are numeric; a positional `{"error": …}` dict is a column write | Fail closed on text attributes; the plan claims the dict rule | Neither is pinned | corpus | partial: MU48 and MU70 survive | 2 | 1 | F1 | **PARTIAL** |
| R5-06 | flynapse-otel | `_vocabulary.py` (whole) | The vocabulary drives the receiver-agnostic doors, sinks and sources | The union of six copies | 29 removals are red. These survive: ORJSONResponse, the websocket/head/options route methods, walk_stack/format_list/print_list, `__stdout__`, warn_explicit, `pprint.pp`, `exc_tb`, setdefault/insert/appendleft, threading hook calls, LoggerAdapter; `format_last` is dead | corpus | partial | 2 | 1 | F1 | **PARTIAL** |
| R5-07 | flynapse-otel | `_module.py:1276-1301` | The raise rule reads uppercase constructions only | A lowercase class alias is a declared limit | `raise type(exc)(f"…{exc}")` and `exc.__class__(…)` are missed; 0 estate sites | none | not applicable | 2 | 1 | F1 | **OPEN** (P2-3) |
| R5-08 | flynapse-otel | `_module.py:927-934`, `:1357-1368` | Doors are classified through Name, Attribute, getattr and partial values | Alias closure | An `IfExp` door is missed by both rules; the shape exists at `utils/utils/llm.py:339` | none | not applicable | 2 | 1 | F1 | **OPEN** (P2-3) |
| R5-09 | flynapse-otel | `_module.py:709-775`, `__init__.py` docstring | Step 2c follows global/nonlocal, mutated free names, `ContextVar.set`, literal `setattr`, hook calls and `.buffer` | core r6 F7 | Within one module these are caught; cross-module ContextVar, list and module-attribute stashes are missed; the docstring overclaims | corpus N1 to N10 rows | yes, for the in-module rules (implementer N1 to N10; my MU55 red); MU56 (threading hook calls) survives | 2 | 1 | F1 | **PARTIAL** |
| R5-10 | flynapse-otel | `_facts.py:116-125`, `_module.py:613-620` | A record-typed parameter's field reads make no slot | Avoid spreading field taint | A suffix-less exception type used as a record is missed (C46); certify's `probe.detail` print is invisible | implementer S14 | yes (S14, implementer-reported) | 2 | 1 | F1 | **PARTIAL** |
| R5-11 | flynapse-otel | `tests/unit/testing/test_exception_text_corpus.py:82-118` | Rows are asserted both ways; leak rows by sink family; floors by equality | Corpus as the table | 43 of 70 independent mutants red; 162 log rows pass via output, raise, helper or source (by design); no vacuous row found | the corpus test | yes | 1 | 1 | F1 | **PARTIAL**: real, with the holes in R5-01 to R5-06 |
| R5-12 | flynapse-otel | `_ratchet.py:23-55` | NEW, GREW, RE-ADDED, UN-REPAIRED; dates parse and are not in the future | The r6 defeats | M1, M4, F3's bless and `9999-99-99` refused | `test_exception_text_ratchet.py` | yes: MB16, MB17 and MU59 red (plus implementer K01 to K06) | 1 | 0 | F1 | **SETTLED** |
| R5-13 | flynapse-otel | `_ratchet.py:58-80` | The baseline is `merge-base HEAD <against>`; a git failure raises | A ratchet with no baseline proves nothing | Growth committed on the base branch passes (R1, R2b, R9); `None` for a renamed file; the `ls-tree`/`show` raises are unpinned; key granularity is undeclared; the date regex has word-boundary gaps | `test_no_merge_base_is_an_error_not_a_pass` | partial: MU60 and MU61 survive | 1 | 1 | F1 | **PARTIAL** (P2-2) |
| R5-14 | flynapse-otel | `withholding.py:216`, `:518-566` | Runs end at ASCII whitespace only (P2-1) | Quotes inside values were cutting judgement | The quote and backtick cases are fixed; whitespace inside a query leaks what follows it (U40) | `test_log_pipe_withholds_url_secrets.py` | yes for P2-1's cases (implementer); U40 has no guard | 0 | 2 | F1 | **PARTIAL** |
| R5-15 | flynapse-otel | `withholding.py:639-693` | Userinfo is removed after every scheme (P2-2) | Nested URLs | Holds for `@`, `/`, IPv6, IDN and lists; a digits-only password prefix leaks (U04, U05) | the same file | yes (implementer's 19 mutants) | 2 | 2 | F1 | **PARTIAL** |
| R5-16 | flynapse-otel | `withholding.py:264-292` | A denylist of secret-name markers, plus a whole-name `code` (P2-6) | Presign, OAuth and Azure keys | `code` is pinned (MB10 red 3); 11 of 14 markers are unpinned; `pass`, `ticket`, `assertion`, `SAMLResponse`, `otp` and `code_verifier` leak | the same file | partial: only `sig`, `token` and `key` are red | 2 | 2 | F1 | **PARTIAL** (P2-4) |
| R5-17 | flynapse-otel | `withholding.py:604-621` | Mapping keys are vetted as text; colliding keys become `<unvetted>` (P2-5) | A key is on the wire | not re-mutated | the same file | implementer only | 2 | 2 | F1 | **ASSERTED** |
| R5-18 | flynapse-otel | `withholding.py:481-505` | The log boundary withholds a rendering in a `str` body and in the two `exception.*` keys | The one seat on the log pipe | A rendering in an attribute value, a dict body or a list body ships (B2, B3, B6) | `test_log_pipe_withholds_exception_text.py` | not for these shapes | 2 | 2 | F1 | **OPEN** (P3) |
| R5-19 | flynapse-otel | `failure.py:57-69` | `frame_headers` renders from frame objects: no source line, no linecache | Owner ruling B4 | Zero linecache or `open` calls on 5 shapes, with a planted entry | `test_failure_fields.py` | yes: MB06 red 50 | 0 | 0 | F1 | **SETTLED** |
| R5-20 | flynapse-otel | `tests/unit/failure/test_failure_parity_with_utils.py` (be3964f) | Parity with utils `1ca934f`, by `==` on every field and renderer | utils becomes a re-export | utils at that SHA is standalone; the test is not vacuous | the parity test | yes: MB07, MB08 and MB09 red | 1 | 0 | F1 | **SETTLED** |
| R5-21 | flynapse-otel | `bootstrap.py:86-95`, `:278` | `Drop` views for the four new-semconv `http.*.body.size` names | Nothing reads them (M-LEGACY-DELETE A14a) | Holds under `http`; under `http/dup` (supported at `:70`) the old `.size` names export | `test_unread_http_body_sizes_are_dropped.py` | yes: MV01 red 5 | 3 | 1 | F3 | **SETTLED** for `http`; **OPEN** for `http/dup` |
| R5-22 | flynapse-otel | `tests/unit/packaging/test_testing_package_isolation.py:57-80` | No runtime module imports `testing`; testing imports stdlib, opentelemetry and itself only | Test support ships in the distribution | These pass: a dev-only `opentelemetry.test` import, a lazy `__getattr__`, and a relative `import_module` | the isolation file | partial: implementer ISO1/ISO2 red; MB02, MB03 and MB04 survive | 3 | 1 | F3 | **PARTIAL** |
| R5-23 | flynapse-otel | `flynapse_otel/testing/live.py:38-117` | `LiveSpans` records in `on_start`; `pre_boundary` is a restoring spy | Live views, with a positive control | reproduced | `test_live_views.py`, tracing live control | yes: MV02 red 5 | 1 | 0 | F1 | **SETTLED** |
| R5-24 | flynapse-otel | `docs/plans/shared-exception-text-detector.md` step 2c | The rescan drop is "health_check's seven" | Claim | Measured: 8 keys; the 8th is a registered copilot-mro DEBT key whose sibling leak lives | none | not applicable | 3 | 1 | F3 | **REFUTED** (P3) |

**Tier 0.** Four rows (R5-12, R5-19, R5-20, R5-23) are settled by guards I watched fail. Their properties do not go to Fable.

---

## Open claims, tier 2 first

**Tier 2: open or partial**

1. **R5-02 (P1-2): `Policy` is an unratcheted bless channel.** It is the contract six repos adopt; fix it before the first adoption (utils).
2. **R5-14 and R5-16 (P2-4): URL residuals.** They are whitespace inside a query, secret-name vocabulary gaps, and 11 unpinned markers.
3. **R5-15:** a digits-only password prefix.
4. **R5-18:** renderings outside the `str` body at the log boundary.
5. **R5-17:** key vetting, asserted by the implementer only.

**Tier 1: open, partial or refuted**

1. **R5-01 (P1-1):** return-slot precision on a resolution that is not a proof. There are 12 regression plants, and today's estate is not exposed.
2. **R5-03 to R5-06 and R5-11:** corpus rows for the precision boundaries and the sanction widenings.
3. **R5-13 (P2-2):** ratchet base-branch no-op and the unpinned git failure paths.
4. **R5-07, R5-08 and R5-09:** `raise type(exc)(…)`, the `IfExp` door and cross-module stashes (plus the docstring overclaim).
5. **R5-10:** a record-typed exception whose class lacks the suffix.
6. **R5-21 and R5-22:** `http/dup` drop views and the isolation-guard spellings.
7. **R5-24:** the rescan undercount, and the stale certify DEBT key.
