# Claims packet: telegram-bot review r4 (delta review of the r3 answers)

This is an independent adversarial review by Opus, dated 2026-09-21. It was read-only throughout. No code tree was edited, checked out or committed, and `/home/aditya/Code/telegram-bot` is still clean at `0af46b1`. Every commit ran from a `git archive` copy in private scratch (`scratchpad/tg-review-r4/`). Every mutation ran in a separate archive copy (`ws-mut`). Each mutated file was restored from a pristine per-file backup and md5-checked against its `git show 0af46b1:<path>` blob. All 42 restores matched (38 targeted, 4 whole-suite), none mismatched, and no stray `__pycache__` appeared.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| telegram-bot | `/home/aditya/Code/telegram-bot` (clean, HEAD `0af46b1`, unpushed) | `main` | `cfb1d98..0af46b1` | `0551de6` P2-1/P2-2/P3-5 · `639f317` P3-1 · `516c7a9` P2-3 · `806ee74` P3-4 · `0af46b1` P3-2 + docs |

**How I ran it.**
- **Copies.** Each commit was extracted with `git archive <sha>` to `ws-<sha>/telegram-bot`. flynapse-otel `927a729` was extracted beside it as `ws-<sha>/flynapse-otel`.
- **Interpreter.** I used telegram-bot's own `.venv`: Python 3.11.15, PTB 22.8, httpx 0.28.1, cryptography 50.0.0. It ran from the copy's root with `VIRTUAL_ENV` unset and `PYTHONPATH=<copy>:<copy>/tests:<otel copy>:<guard dir>`.
- **Fresh bytecode.** Every run used a fresh `PYTHONPYCACHEPREFIX`. No `__pycache__` existed in any copy.
- **No network.** A `sitecustomize.py` network guard (r3's, re-verified here) refused and logged three planted connects: a direct connect, a DNS lookup and an asyncio `sock_connect`. Every test and probe run logged **0 refusals**.
- **No database.** `BOT_TEST_DB_URL=postgresql://127.0.0.1:1/none`, so the Postgres-backed tests skip through their own fixture. No `.env` was read. No docker, AWS, Cognito, Telegram or DB call was made, and no DB MCP was used.
- **Exit status.** pytest's own exit status was taken directly (`rc=$?`, no pipe).
- **Provenance.** `telegram_bot.__file__`, `flynapse_client.__file__` and `flynapse_otel.__file__` all resolved into the copy (`…/tg-review-r4/ws-0af46b1/…`).

**Every commit is green at its own HEAD.** Each step adds exactly the tests its commit adds (+0, +1, +1, +1, +0, for 3 in total). The commits that add none only rewrite or rename tests.

| commit | result (pytest rc) |
|---|---|
| cfb1d98 (base) | 2202 passed, 300 skipped (0) |
| 0551de6 | 2202 passed, 300 skipped (0) |
| 639f317 | 2203 passed, 300 skipped (0) |
| 516c7a9 | 2204 passed, 300 skipped (0) |
| 806ee74 | 2205 passed, 300 skipped (0) |
| 0af46b1 | 2205 passed, 300 skipped (0) |

The 300 skips are the Postgres-backed tests. None of the nine test files the range touches is among them. `ruff check` and `mypy` (with the repo's pydantic plugin config) are clean over all 20 touched `.py` files at each of the five commits.

**The new tests fail on the base code.** I ran HEAD's tests against `cfb1d98`'s source:
- **10 of 10 new or changed property tests go red.** The three D1/D4 transport tests fail on `format_exception`. The signed-leg and both crypto tests fail on the chain walk. The two 401 tests and the malformed-frame test fail on `str`.
- **The reply-sink test stays green**, as `516c7a9` declares: it adds a test and changes no code.

**The detector rescan still reproduces.** flynapse-otel `927a729`, run with r3's policy, reports exactly the 7 triaged over-reports at both `cfb1d98` and `0af46b1`. The same detector does not see a regression at any site the range moved behind `raise_unchained`: P1-1 below.

**Verdict: FIX-FIRST (0 P0 / 1 P1 / 0 P2 / 4 P3).** No content leak ships:
- At HEAD, every exception the range touched renders clean through every text renderer this process has. I checked 14 renderers per error. The only exception is frame locals, which predate the range and have no reader in this bot.
- Every site is held by a behavioural test that a mutation turns red.

The one P1 is a guard-integrity regression the range introduced. `raise_unchained` takes the raise out of the call site, and the estate's shared exception-text detector does not follow a raise through a helper. This detector is the tool that found D1-D4, and it is the planned closer for r3's P3-3. Every site written in the new idiom is invisible to it, D2's auth site included, which the detector could see before `0551de6`. The fix is small, and one version of it is prototyped below.

---

## Findings, ranked

### No P0

At HEAD I built each withheld failure through real code paths:
- `send_json` and `stream_turn` transport failures, carrying an h11-style sentinel;
- the DocHub signed leg, with the signed URL in the httpx message;
- `voice._download`, with a tokened file URL in PTB's `NetworkError`;
- `InvalidCredentialKey` and `CredentialDecryptionError`, with a planted library message;
- a 401 whose body quotes a sentinel;
- a malformed `synthesis_chunk` frame.

I rendered each one through 14 renderers (`scratchpad/tg-review-r4/renderprobe.py`, `logs/renderprobe-{head,base}.out`):
- the seven in `tests/_rendered.py`;
- a bot-logger `.exception()` through `FailureFormatter`;
- PTB's "No error handlers are registered" record;
- `sys.__excepthook__` to a captured stderr;
- asyncio's "Task exception was never retrieved" through the stdout formatter;
- the raw OTel SDK `LoggingHandler` (no flynapse boundary, which gives the maximum exposure);
- a 3-level `vars()` walk of every chain link;
- `pickle`.

The results:
- **At HEAD** nothing leaks through any text renderer. The two exceptions, below, are not text renderers.
- **At base**, the transport and voice errors leaked through `format_exception`, the stdout formatter, the chain walk and all four extra text renderers. The signed-leg and crypto errors leaked through the chain walk. The 401 and malformed-frame errors leaked everywhere, `str` included.

### P1-1: `raise_unchained` moves every raise it carries out of the shared detector's sight, including a site the detector covered before

**Where.** `flynapse_client/errors.py:40-66`. The callers are `_door.py:195`, `flynapse_client/chat.py:113`, `dochub.py:229`, `telegram_bot/handlers/voice.py:211`, `telegram_bot/crypto.py:78` and `:94`, and `auth.py:238` (through `_raise_unchained`).

**What changed.** Before `0551de6`, each of these sites raised with a syntactic `raise X(...)`. auth's `_raise_unchained(message)` built and raised its `AuthError` inside itself. Now every one is a CALL, `raise_unchained(X(...))`, and the only `raise` is `raise error` inside the helper, where `error` is a parameter. The detector (`flynapse_otel.testing.exception_text`, `927a729`) does not follow that:
- `_module.py:1333` `_raise_site` reads only a syntactic `ast.Raise`.
- `r.helpers` has no slot for `raise_unchained` or `_raise_unchained` (`detect_helpers.py`).
- `Policy` has no field for declaring a raise helper. Its fields are `bounded_readers`, `refusal_types`, `column_recorders`, `exception_parameter_names` and `seed_attributes`.
- The detector's "Declared limits" list does not name the case.

**Measured.** Each row below is the same text-carrying construction, placed once with a plain raise at `cfb1d98` and once inside `raise_unchained` at `0af46b1`. The policy is r3's. Every run logged 0 netguard refusals.

| mutant (the defect D1-D4 fixed) | plain `raise` at `cfb1d98` (control) | inside `raise_unchained` at `0af46b1` |
|---|---|---|
| M1: `transport_error` renders `{exc}` | **+2**: `_door.py:193`, `chat.py:112`, `raise.factory-text` | **+0** |
| M4: `stream_turn` builds `ApiError(f"…{exc}")` inline | **+1**: `chat.py:113`, `raise.caught-text` | **+0** |
| M8: `_failure_detail` returns `f"{type}: {exc}"` (D2's site) | **+1**: `auth.py:209`, `helper.caught-text … into _raise_unchained(message) → raise` | **+0** |
| M9: `InvalidCredentialKey` renders `{error}` | **+1**: `crypto.py:73`, `raise.caught-text` | **+0** |
| M11: `CarrierFailure` reason renders `{error}` | **+1**: `voice.py:208`, `raise.caught-text` | **+0** |

**Failure scenario.** The docstrings this range wrote (`errors.raise_unchained`, `_door`'s secrets paragraph, `crypto`'s module docstring) now steer every failure "whose CAUSE carries text this code did not write" to `raise_unchained`. So the next door or carrier that wraps an upstream exception is written as `raise_unchained(ApiError(f"… {exc}"))`. That is exactly the shape the detector cannot see. There is still no in-repo guard for a raised construction carrying text (r3 P3-3, TG3-15). The plan's route to one is adoption of this detector, and on the idiom that route now closes nothing. A reviewer's rescan reports "7, all triaged" over the leak, the same false all-clear the base rescan would have caught.

**Why this is not a leak today.** Each of the seven existing sites is held by a behavioural test that its mutation turns red (M1-M12 and N6-N19 below). The exposure is every future site, plus the rescan evidence every review round leans on.

**Fix. Either option closes it, and the plan must say which.**
- **(a) Keep a syntactic `raise` at every site.** A context manager has the unchained semantics and leaves the raise where the detector reads it:
  ```python
  with unchained():
      raise transport_error(method, path, exc)
  ```
  `__exit__` clears `__cause__` and `__context__` and sets `__suppress_context__`, then returns `False`. I prototyped it in scratch (`ws-det-cmproto`, `cmcheck.py`):
  - the detector flags M1 again (`_door.py:196 send_json [raise] raise.factory-text`);
  - raised from inside a caller's `except ValueError("…SENTINEL-amb")`, the error arrives with `__cause__ None` and `__context__ None`;
  - the traceback loses the extra `raise_unchained` frame;
  - it has no reference cycle (P3-2).
- **(b) Teach the detector that a parameter reaching `raise` makes a raise helper.** This is a flynapse-otel change in another lane. It would flag `raise_unchained(X(f"…{exc}"))` as `helper.caught-text`. Until it lands, the plan should record the limit here and route it to that lane, so the detector's declared-limits list gains the entry.

### P3-1: the one chain kept on purpose carries the whole frame, and the new render helper cannot see it; two field decoys survive for the same reason

**Where.** `flynapse_client/events.py:462-469` and `tests/_rendered.py:13-14, 28-41`.

**The JSON decoder's chain.** `806ee74` keeps the decoder's error chained on the argument that "its message is a parse position, never the document". That is true of the message. But `JSONDecodeError.doc` is the whole frame's data, and for a `synthesis_chunk` frame that is the pilot's answer (`docprobe.py`: `__cause__.doc == data`, `True`). `raise_unchained`'s own docstring rejects `from None` because the link stays "reachable for a logger, a debugger or a crash reporter". The same reasoning applies to `.doc` on a `__cause__` link.

**The helper cannot see it.** The helper's `chain` rendering is documented as "what a crash reporter or a debugger walks, whatever the printer hides", but it reads each link's class, `str` and `args`, not its attributes. Two decoys pass the whole targeted set:
- **N14** stores the frame on the raised error (`error.data = data`) and survives both the targeted set (503 passed) and the whole suite (2205 passed).
- **N15** puts the httpx text into `ApiError.body_snippet` on the transport path and survives. It also survives the whole suite (2205 passed). `body_snippet` is a field no consumer in `telegram_bot/` renders.

**Why this is not a leak today.** No text renderer prints an attribute. At HEAD, the `.doc` bytes reach only the attribute walk in my probe. They also reach a frame-locals renderer, but that one sees `data` in `_decode`'s own frame whether or not the chain is kept.

**Fix.** Either:
- raise `MalformedEventError` unchained as well (the parse position adds nothing an operator acts on), or
- narrow the helper's `chain` docstring to "class, `str` and `args`, not attributes or frame locals", state in the plan that `.doc` stays on the chain, and pin `body_snippet is None` in the two D1 tests.

### P3-2: `raise_unchained` makes a reference cycle that keeps every error, and the frames on its traceback, alive until the cyclic GC runs

**Where.** `flynapse_client/errors.py:61-66`.

**The cycle.** The error's `__traceback__` holds `raise_unchained`'s frame, and that frame's local `error` holds the error. I measured it with `cycleprobe.py`, with GC disabled:
- An `ApiError` raised through `raise_unchained` is still alive after its handler finishes, and is freed only by `gc.collect()`.
- The same error raised plainly is freed at once.

**What it keeps alive.** Everything else the traceback holds stays alive with it: `send_json`'s frame (the bearer `headers` and the request body) and `stream_turn`'s (the token and the pilot's message). Nothing is disclosed by this, so it is hygiene. The stdlib idiom that breaks exactly this cycle is `socket.create_connection`'s `finally: err = None`. `auth._raise_unchained` had the same cycle before the range; the range extends it to seven sites.

**Fix.** Add `del error` (or `error = None`) at the end of the `finally`, or take option (a) of P1-1, which has no cycle.

### P3-3: the plan says "Every finding is fixed", and r3's P3-3 is not mentioned anywhere

**Where.** `docs/plans/exception-text-withholding.md:461-512`.

The post-review section says "Every finding is fixed (the owner's instruction: finish everything)". It then lists P2-1, P2-2, P2-3, P3-1, P3-2, P3-4 and P3-5. **P3-3 is absent.** P3-3 is the finding that the repo has no in-repo guard against a raised construction carrying text, and that it closes at detector adoption. It is in neither the post-review list nor Future Improvements, and a grep for `P3-3` or `adoption` finds nothing in the plan. After P1-1, the stated route does not close it for the new idiom either.

**Fix.** Record P3-3 in Future Improvements. Say what closes it, which is adoption plus P1-1's fix, and which sites depend on it.

### P3-4: docstring-family drift: four places still describe `from None` as a break

The repo has repeated the docstring-family lesson here. The range made "`from None` only hides the link" the shared doctrine, and four places still say otherwise:
- **`tests/unit/sdk/test_dochub_client.py:399-402`** says "the transport branch breaks its chain (`from None`)".
- **`tests/unit/sdk/test_dochub_client.py:418-419`**, in `test_a_transport_failure_on_the_signed_leg_breaks_its_chain`, says it pins "The `from None` the module's docstring argues". `0551de6` rewrote that module docstring to argue the opposite.
- **`telegram_bot/config.py:66`** says every caller "breaks the exception chain at its raise site". Those callers are `app.py:1339` and `:1353`, and they use `from None`.
- **`app.py:1369-1371` and `:1377-1379`** raise `SystemExit(...) from None` over a psycopg error that, by their own comments and by `test_app_wiring.py:779`, can carry the DSN password. By this range's doctrine that link is hidden, not broken.

None of this is reachable: a `SystemExit` at exit prints its message and no traceback.

**Fix.** Reword the four docstrings, or route the four `SystemExit` raises through the same unchained shape.

---

## What I tried to break and could not

- **`raise_unchained`'s mechanics.**
  - It clears in a `finally` after `raise error`, which is the only order that also drops an AMBIENT context.
  - The three wrong shapes each turn 9 tests red. **N1** keeps `__context__`. **N2** is `raise error from None`. **N3** clears first and then raises, so the raise re-attaches the context. The 9 red tests span all four files, plus both auth ambient-context tests.
  - A raise from inside a caller's handler arrives with `__context__ None` (probe E9).
- **Frames operators need.**
  - At HEAD each traceback is the caller's frames plus one `raise_unchained` frame.
  - `failure_fields` never walked the chain (`failure.py:52`), so every stdout and OTLP `stack` field is unchanged apart from that one extra frame.
  - What is gone is the cause's own frames (httpx, h11, PTB, Fernet internals) from third-party tracebacks. The cause's CLASS is still in every message (`…: RemoteProtocolError`, `…: NetworkError`, `(ValueError: …)`).
- **Implicit or explicit chains left in an `except`.** An AST scan of `flynapse_client/` and `telegram_bot/` (`raisescan.py`) lists every raise lexically inside a handler:
  - 14 bare re-raises and 6 `raise_unchained` calls.
  - 4 `SystemExit … from None` (P3-4).
  - 6 explicit `from x`: `_door.py:205` (a non-JSON success body, which predates the range; the body is also on `body_snippet`), `events.py:467` (P3-1), and the four `document_watch._WatchOver … from error`. Those four chain `AuthError`/`ApiError`s whose messages are now class, status, door or length only.
  - **0 implicit chains.**
  - No door client is called from inside an `except` block (`awaitscan.py`), so the plain `raise error_for_status(...)`'s ambient-context exposure (E9) has no caller.
- **Re-raising an unchained object.** A later `raise obj` inside a different handler re-attaches `__context__`, which the leftover `__suppress_context__` then hides (E9). Every re-raise site I found is safe:
  - `_or_raise` (`handlers/chat.py:2523`) runs outside any handler.
  - `call_with_backoff` uses a bare `raise`.
  - An async context manager re-throwing the SAME object does not chain.
- **The render helper's text coverage.** At base, each of the four extra text renderers (bot `.exception()`, PTB's record, `sys.__excepthook__`, asyncio never-retrieved) leaked exactly when the helper's `format_exception` or `stdout-formatter` did. So for text, `_rendered.py` is complete for this process. Its gaps are attributes and frame locals (P3-1).
- **The r3 plants at HEAD.** All 16 were re-anchored (`M3r` is now the inverse: restore `from exc` at both D1 sites).
  - **r3's P2-2 decoy is caught now.** M5 turns 4 tests red: both D1 tests pin `path`, and the new reply test's `caplog` sees `door=` in the log line.
  - **M15, the reply quoting `error.__cause__`, survives, as it must.** There is no chain left to quote.
- **The reply-sink guard (`516c7a9`).**
  - It drives the real `FlynapseClient` through `httpx.MockTransport` (`_copilot_harness.py:446-466`) and the real `stream_turn`, and its planted exception is confirmed raised.
  - As the plan says, it kills the conjunction and not a reply-only mutant, because no channel from the error to the transport text remains. **P1** (M1 + reply quotes `{error}`) and **P2** (`from exc` restored + reply quotes `__cause__`) each turn it red. N16 (reply quotes `str(error)`) and M15 alone survive both the targeted set and the whole suite (2205 passed each).
- **806ee74's 401 and malformed-frame changes.**
  - Nothing branches on either message. The only `str(error)` predicate in the bot is `uploads._is_too_big`, over a Telegram `BadRequest`.
  - **N11** (snippet back) and **N12** (12 head bytes) turn both 401 tests red. **N13** (a 24-character tail) turns the frame test red.
  - `size` measures bytes on both 401 paths (`response.content`, `await response.aread()`).
- **Frame locals.** At base the transport text sat in the cause's frames. At HEAD it is in no frame's locals: the `except … as exc` name is deleted and no cause is linked. The bearer header in `send_json`'s locals, the signed URL in `content`'s, and the frame data in `_decode`'s predate the range and have no locals-rendering reader in this bot.
- **Cross-repo coupling.** flynapse-otel's `test_exception_text_corpus.py` counts telegram-bot rows from static fixtures. It does not scan this tree, so the range cannot change its floors.

## What I did not test

- **The 300 Postgres-backed tests.** They were skipped by design, and none exercises code in the range.
- **A live PTB transport failure, or a real crash reporter.** The attribute and frame-locals channels were measured with a `vars()` walk and `TracebackException(capture_locals=True)`, not with Sentry or a debugger.
- **The OTLP log route with flynapse-otel's boundary.** I rendered through the raw SDK `LoggingHandler` instead, which is a superset of what the boundary lets through, and it was clean at HEAD.
- **Option (b) of P1-1.** It is a detector change in another lane. Here the detector was only run, read-only.
- **Whether the owner wants `.doc` kept (P3-1).** That is a judgment call, and I recorded the facts only.

## Plants (35), at HEAD `0af46b1`

**How they ran.** The targeted set is `tests/unit/sdk`, `test_credential_crypto`, `test_voice_notes`, `test_door_failure_logging`, `test_progress_editing`, the two telemetry log sweeps and `test_app_wiring`. Unmutated, it gives 503 passed and 1 skipped. The four survivors were then run against the whole suite.

**HEAD blob md5s (first 8):**

| file | md5 |
|---|---|
| `errors.py` | `1f09e939` |
| `_door.py` | `c1f6e542` |
| `flynapse_client/chat.py` | `7c393816` |
| `auth.py` | `33f37112` |
| `dochub.py` | `2a489493` |
| `events.py` | `79009ac5` |
| `crypto.py` | `e394a3b1` |
| `voice.py` | `78d05c5b` |
| `handlers/chat.py` | `e251b3ae` |
| `config.py` | `1553c949` |

| # | plant | red (targeted) | reading |
|---|---|---|---|
| M1 | `transport_error` renders `{exc}` | 2 (both D1 tests) | sound |
| M2 | renders `{exc!r}` | 2 | sound |
| M3r | `from exc` restored at both D1 sites | 2 | chain guarded (r3 P2-1 closed) |
| M4 | `stream_turn` inlines `f"…{exc}"` | 3 | sound |
| M5 | httpx text into `path=` | 4 (both D1 tests, the older mid-stream pin, and the reply test's log check) | r3 P2-2 closed |
| M6 / M7 / M8 | `_failure_detail` reads `Code` / `Code: Message` / `{exc}` | 1 / 4 / 7 | sound |
| M9 | key error renders `{error}` | 2 | sound |
| M10r / M10b | key error back to `from None` / `from error` | 2 / 2 | r3 P3-1 closed |
| M11 / M12 | voice reason / apology renders `{error}` | 1 / 1 | sound |
| M13 / M14 | `%s` of the exception beside the D1 / D4 raise | 1 / 1 (log sweep) | sound |
| M15 | reply quotes `error.__cause__` | **0** | no channel remains (expected) |
| M16 | `configuration_error` appends `input` | 1 | sound |
| N1 | `raise_unchained` keeps `__context__` | 9 | sound |
| N2 | `raise_unchained` becomes `raise error from None` | 9 | sound |
| N3 | clear first, then raise | 9 | sound |
| N6 / N7 | `send_json` / `stream_turn` alone back to `from exc` | 1 / 1 | sound |
| N8 | signed leg back to `from None` | 1 | sound |
| N9 | voice back to `from error` | 1 | sound |
| N10 | decrypt back to `from None` | 1 | sound |
| N18 | key error with an implicit chain | 2 | sound |
| N19 | auth `_raise_unchained` becomes `raise … from None` | 2 (both ambient-context tests) | sound |
| N11 / N12 | 401 snippet back / 12 head bytes | 2 / 2 | sound |
| N13 | frame error quotes a 24-character tail | 1 | sound |
| N14 | frame data stashed on `error.data` | **0** | helper reads no attributes (P3-1) |
| N15 | httpx text into `body_snippet` | **0** | unpinned field, no consumer (P3-1) |
| N16 | reply quotes `str(error)` | **0** | clean `str`, nothing to quote (expected) |
| P1 | M1 + N16 | 3 (both D1 tests and the reply test) | reply guard sound as a conjunction |
| P2 | N7 + M15 | 2 (the stream D1 test and the reply test) | the same |

Whole-suite results for the four survivors: **M15, N14, N15 and N16 each give 2205 passed, 300 skipped, rc 0**, with 0 netguard refusals. Every restore was md5-equal to the HEAD blob.

Detector plants (not pytest): M1, M4, M8, M9 and M11 inside `raise_unchained` each give **+0** findings. M1, M4, M8, M9 and M11 with a plain `raise` at `cfb1d98` give +2, +1, +1, +1 and +1 (P1-1).

## Claims table

Severity on a SETTLED row is the class of the property the row holds: 0 means it would be a content leak if it regressed. On an OPEN, PARTIAL or REFUTED row, severity is the finding's own.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TG4-01 | telegram-bot | `flynapse_client/errors.py:40-66` | One shared `raise_unchained`: raise, then clear `__cause__`/`__context__` in a `finally` | `from None` only hides the link, and the ambient context attaches at the raise | Probe E1-E6, E9: `__cause__ None`, `__context__ None`, ambient context dropped | the 7 site tests and the auth ambient tests | **yes**: N1, N2, N3 each red 9 | 0 | 0 | F1 | **SETTLED** |
| TG4-02 | telegram-bot | `_door.py:195`, `flynapse_client/chat.py:113` | Transport `ApiError` raised unchained, named by class | r3 P2-1: the cause printed h11's bytes in every traceback renderer | 14 renderers clean at HEAD; base leaked through format_exception, stdout, chain and 4 extra renderers | `test_chat_client.py:337`, `test_provisioning_client.py:229` | **yes**: M1, M2, M3r, M4, N6, N7 red | 0 | 0 | F1 | **SETTLED** |
| TG4-03 | telegram-bot | the same two tests | Pin `path` exactly, read `headline_of`/`failure_fields` | r3 P2-2: a field decoy passed | M5 red on both D1 tests (and the reply test's log check) | the same | **yes**: M5 red 4 | 0 | 0 | F1 | **SETTLED** |
| TG4-04 | telegram-bot | `dochub.py:229` | Signed leg raised unchained (was `from None`) | r3 P3-1: `__context__` kept the signed URL | Chain walk leaked at base, clean at HEAD | `test_dochub_client.py:459` | **yes**: N8 red | 0 | 0 | F1 | **SETTLED** |
| TG4-05 | telegram-bot | `telegram_bot/handlers/voice.py:211` | `CarrierFailure` raised unchained | r3 P2-1: PTB's `NetworkError` quotes the tokened file URL | Leaked through format_exception and stdout at base, clean at HEAD | `test_voice_notes.py:469` | **yes**: M11, M12, N9 red | 0 | 0 | F1 | **SETTLED** |
| TG4-06 | telegram-bot | `telegram_bot/crypto.py:78`, `:94` | Both cipher errors raised unchained | r3 P3-1 | Chain walk leaked at base for both, clean at HEAD | `test_credential_crypto.py:129`, `:154` | **yes**: M9, M10r, M10b, N10, N18 red | 0 | 0 | F1 | **SETTLED** |
| TG4-07 | telegram-bot | `flynapse_client/auth.py:235-238` | `_raise_unchained` delegates to the shared helper | One mechanism | Ambient tests hold | `test_cognito_auth.py` ambient and chain tests | **yes**: N19 red 2, M6-M8 red 1/4/7 | 0 | 0 | F1 | **SETTLED** |
| TG4-08 | telegram-bot | `_door.py:69-73` | A 401 names door, status and body length, never the body | r3 P3-4: a gateway can echo the token | Leaked everywhere at base, clean at HEAD; no predicate reads the message | `test_chat_client.py:302`, `test_door_failure_logging.py:353` | **yes**: N11, N12 red 2 each | 0 | 0 | F1 | **SETTLED** |
| TG4-09 | telegram-bot | `flynapse_client/events.py:467-469` | `MalformedEventError` names type and length, never data | r3 P3-4: a `synthesis_chunk` is the answer | Message clean; `__cause__.doc` is the whole frame | `test_sse_events.py:530` | **yes** for the message (N13 red); **no** for the chain (N14 survives) | 3 | 1 | F1 | **PARTIAL**: P3-1 |
| TG4-10 | telegram-bot | `tests/_rendered.py` | Every renderer the process has, plus a chain-graph walk | r3: tests read `str()` only | Text coverage complete: every extra text renderer leaked exactly when the helper did (base) | used by 9 tests | **partly**: N14 and N15 survive; the `chain` docstring overclaims | 3 | 1 | F1 | **PARTIAL**: P3-1 |
| TG4-11 | telegram-bot | `tests/unit/bot/test_progress_editing.py:355` | A real copilot turn with an h11 failure; the sentinel is absent from replies and logs | r3 P2-3: the reply sink was unguarded | Real client through MockTransport; red-before is green by design (test-only) | itself | **yes, as a conjunction**: P1, P2 and M5 red; M15 and N16 alone survive (no channel) | 0 | 0 | F1 | **SETTLED** as a conjunction guard |
| TG4-12 | telegram-bot | the 7 `raise_unchained` sites | (implicit) the class stays detectable by the shared detector | The plan's route to r3's P3-3 is adoption | M1, M4, M8, M9, M11 inside `raise_unchained`: +0 findings each; the plain-`raise` controls at `cfb1d98` give +2, +1, +1, +1, +1 | none | **yes, and the property fails**: 5 treatment/control pairs | 1 | 1 | F1 | **REFUTED**: P1-1 |
| TG4-13 | telegram-bot | `flynapse_client/errors.py:61-66` | Clear in a `finally` over the error's own local | — | `cycleprobe.py`: alive after the handler until `gc.collect()`; a plain raise is freed at once | none | n/a | 3 | 1 | F1 | **OPEN**: P3-2 |
| TG4-14 | telegram-bot | `flynapse_client/`, `telegram_bot/` | No implicit chain inside an `except`; no door called from a handler | Ambient context is the other half of a chain | `raisescan.py`: 0 implicit; `awaitscan.py`: no door call inside a handler | none (scan) | n/a | 1 | 1 | F1 | **SETTLED by scan** |
| TG4-15 | telegram-bot | range `cfb1d98..0af46b1` | Every commit lands fix plus guard, green at its own HEAD; the new tests are red on the base code | The plan's lessons | 2202 → 2202 → 2203 → 2204 → 2205 → 2205, rc 0 each; ruff and mypy clean; 10/10 red-before | the suite | n/a | 3 | 0 | F3 | **SETTLED** (the DB-backed half is not measured) |
| TG4-16 | telegram-bot | detector rescan | 7 findings, all triaged over-reports | — | `927a729` gives the same 7 at base and HEAD | not adopted | n/a | 3 | 1 | F3 | **SETTLED**, but see TG4-12: silence is not proof here |
| TG4-17 | telegram-bot | `docs/plans/exception-text-withholding.md:461-512` | "Every finding is fixed" | Owner: finish everything | r3's P3-3 is in neither the list nor Future Improvements | none | n/a | 3 | 1 | F3 | **OPEN**: P3-3 |
| TG4-18 | telegram-bot | `test_dochub_client.py:399-402`, `:418-419`; `config.py:66`; `app.py:1369-1379` | Still say `from None` "breaks" the chain | — | Read at HEAD; `SystemExit` context unreachable | none | n/a | 3 | 1 | F3 | **OPEN**: P3-4 |
| TG4-19 | telegram-bot | `_door.py` `send_json`, `dochub.py` `content`, `events.py` `_decode` (predate the range) | Frame locals hold the bearer header, the signed URL and the frame data | — | `capture_locals` probe; no locals renderer in the bot; transport text left the locals at HEAD | none | n/a | 3 | 1 | F1 | **OPEN** (predates the range; no sink) |

## Open claims, tier 2 first

**Tier 2: none.** Nothing in this range is irreversible or estate-shaping. It is unpushed and adds no schema. `raise_unchained` is public in `flynapse_client.errors`, but no other repo imports `flynapse_client`.

**Tier 1: open, partial or refuted**

1. **TG4-12 (P1-1): the shared detector cannot see through `raise_unchained`.** This must be resolved before this phase closes and before detector adoption. Take either (a), a syntactic `raise` under a `with unchained():` (prototyped: the detector sees M1 again, the chain and ambient context are cleared, and there is no cycle), or (b), a raise-helper model in the detector (flynapse-otel lane), recorded in this plan and in the detector's declared limits until it lands.
2. **TG4-17 (P3-3):** record r3's P3-3 and its closing route, which now depends on item 1.
3. **TG4-09 and TG4-10 (P3-1):** either raise `MalformedEventError` unchained, or state in the plan that `.doc` stays on the chain. Narrow `_rendered.chain`'s docstring, and pin `body_snippet is None` in the D1 tests.
4. **TG4-13 (P3-2):** break the self-cycle (`del error` in the `finally`), or let option (a) remove it.
5. **TG4-18 (P3-4):** four stale "`from None` breaks the chain" statements. Do these in one pass with item 1.
6. **TG4-19:** frame locals. These predate the range and have no sink. They are recorded so a future locals-rendering reporter (Sentry's `include_local_variables`) is known to need a scrubber.
