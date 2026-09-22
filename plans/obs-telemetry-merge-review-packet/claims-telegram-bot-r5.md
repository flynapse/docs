# Claims packet: telegram-bot review r5 (delta review of the r4 answers)

This is an independent adversarial review by Opus, dated 2026-09-21. It was read-only throughout. No code tree was edited, checked out or committed, and `/home/aditya/Code/telegram-bot` is still clean at `645b334`. Every commit ran from a `git archive` copy in private scratch (`scratchpad/telegram-review-r5/`). Mutations ran in two separate archive copies (`ws-mut`, `ws-mut2`). Each mutated file was restored from a pristine per-file backup and md5-checked against its `git show 645b334:<path>` blob. All 40 restores matched (37 targeted, 3 whole-suite), none mismatched, and no `__pycache__` appeared in any copy.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| telegram-bot | `/home/aditya/Code/telegram-bot` (clean, HEAD `645b334`, unpushed) | `main` | `0af46b1..645b334` | `b30d0a3` P1-1/P3-2/P3-3 · `10e1c82` P3-1 · `645b334` P3-4 |

**How I ran it.**
- **Copies.** Each commit was extracted with `git archive <sha>` to `ws-<sha>/telegram-bot`, with flynapse-otel extracted beside it as `ws-<sha>/flynapse-otel` (the sibling path `test_import_provenance` requires).
- **flynapse-otel snapshot.** The live tree is dirty (another lane), so every run used a `git archive` of its committed **HEAD `56b1814`** (R6 P2-3). The detector was also run from a `927a729` archive, the pin the implementer and r4 used, so their numbers could be reproduced exactly.
- **Interpreter.** telegram-bot's own `.venv` (Python 3.11.15), from the copy's root, `VIRTUAL_ENV` unset, `PYTHONPATH=<otel copy>:<copy>:<copy>/tests:<netguard>`, `-p no:cacheprovider -o addopts="-ra --strict-markers"`, a fresh `PYTHONPYCACHEPREFIX` per run.
- **Provenance, from pytest's own output** (`test_import_provenance.py -s`, rc 0 at every SHA): `telegram_bot.__file__ = …/ws-<sha>/telegram-bot/telegram_bot/__init__.py` and `flynapse_otel.__file__ = …/ws-<sha>/flynapse-otel/flynapse_otel/__init__.py`, rootdir `…/ws-<sha>/telegram-bot`, for all four SHAs.
- **No network.** A `sitecustomize.py` network guard refused and logged three planted connects (direct connect, DNS, asyncio `sock_connect`). Every test, probe and detector run logged **0 refusals**.
- **No database.** `BOT_TEST_DB_URL=postgresql://127.0.0.1:1/none`; the Postgres-backed tests skip through their own fixture. No `.env`, docker, AWS, Cognito, Telegram, Bedrock or DB MCP.
- **Exit status.** pytest's own exit status was captured (`rc=$?` in the runner, written into the log as `RC=`), never a pipe's.
- **A process note.** My first full-suite loop pointed flynapse-otel at a non-sibling path (the provenance test failed, correctly), and editing the runner mid-run corrupted a second loop's logs. Both loops were killed and every full-suite number below comes from a clean third run (`fullB-*`).

**Every commit is green at its own HEAD** (flynapse-otel `56b1814`):

| commit | result (pytest rc) |
|---|---|
| 0af46b1 (base) | 2205 passed, 300 skipped (0) |
| b30d0a3 | 2208 passed, 300 skipped (0) — +3, `test_unchained_raise.py` |
| 10e1c82 | 2209 passed, 300 skipped (0) — +1, the past-the-cap provisioning test |
| 645b334 | 2210 passed, 300 skipped (0) — +1, the broken-environment `main` test |

`ruff check` is clean over the whole tree at all three commits. `mypy` (repo config, pydantic plugin) is clean over the 16 touched `.py` files at all three.

**The new tests fail on the parent's code.** Parent source + child tests: `10e1c82`'s two new or changed tests go red on the parent, both on `.doc` (`doc='{"text": "SENTINEL-answer-content" not json'`, and the body past the cap). `645b334`'s four go red on the parent: three on the chain walk (the DSN password, the environment sentinel) and one on `__context__ is None`. `b30d0a3`'s GC test, rewritten to use the old `raise_unchained` against `0af46b1`, goes red ("the error outlived its handler").

**Verdict: MERGE-CLEAN (0 P0 / 0 P1 / 3 P2 / 4 P3).** Every r4 finding is answered, and every answer is held by a guard I saw go red. No content leaks at `645b334` through any path the r4 packet measured. The three P2s are guard-integrity and scope claims, not leaks:
- the detector adoption will actually use (flynapse-otel `56b1814`) reports **8**, not 7, and cannot tell D2's regression from the clean code;
- the detector does not read the chain half of the idiom at all;
- `unchained`'s named ambient case does not hold across the package's own `asyncio.to_thread` seam.

Each P2 is small and should land before this phase closes, as the owner's "finish everything" asks.

---

## What reproduced

### The detector counts (the implementer's claims)

The r3 policy was used (`failure_fields`/`headline_of`/`configuration_error` bounded readers, `seed_attributes={"error"}`). One archive copy was made per mutant, and each was diffed against the unmutated scan at the same SHA.

| mutant | flynapse-otel `927a729` at b30d0a3 and 645b334 | flynapse-otel `56b1814` (HEAD) at b30d0a3 and 645b334 |
|---|---|---|
| M1 `transport_error` renders `{exc}` | **+2** (`_door.py` `send_json`, `chat.py` `stream_turn`, `raise.factory-text`) | **+2** |
| M4 `stream_turn` inlines `f"…{exc}"` | **+1** (`raise.caught-text`) | **+1** |
| M8 `_failure_detail` returns `f"{type}: {exc}"` (D2) | **+1** (`auth.py` `_initiate_auth`) | **+0** (P2-1) |
| M9 key error renders `{error}` | **+1** | **+1** |
| M11 voice reason renders `{error}` | **+1** | **+1** |
| unmutated | **7** at 0af46b1, b30d0a3, 10e1c82, 645b334 (the same 7 keys; `app.py:1339` → `:1343`) | **7** at 0af46b1; **8** at b30d0a3, 10e1c82, 645b334 |

The implementer's "+2/+1/+1/+1/+1" and "exactly 7" are **true at `927a729`**, the pin they declared. They are **stale at flynapse-otel HEAD**. `5c7e1dc` ("narrowing withdrawn — every argument to a helper counts") was committed 10 minutes before `b30d0a3`. From it on, `failure = _failure_detail(exc)` is text, so the now-literal auth raise is flagged clean (P2-1).

The 7 at `927a729` are honest. They are rows 4, 6–9, 11 and 12 of the plan's Phase D triage. `configuration_error` reads `loc` and `msg` only, and `BotSettings` has no custom validator (re-grepped at HEAD). Rows 6–9 are the declared flow-insensitivity over `_or_raise`.

### My own detector probes (both SHAs, at 645b334)

| probe | 927a729 | 56b1814 | reading |
|---|---|---|---|
| X1 `send_json` back to `from exc` (unchained kept out) | +0 | +0 | the chain half is invisible (P2-2) |
| X2 = F1d, `with unchained()` dropped, `from None` kept | +0 | +0 | the same |
| X3 the decoder's chain restored (`from exc`) | +0 | +0 | the same |
| X8 voice `from error` under `unchained` | +0 | +0 | equivalent at runtime (unchained clears it) |
| X4 = N15, httpx text into `body_snippet` | +2 | +2 | seen |
| X5 a module-level helper renders `{exc}` into the signed-leg message | +1 | +1 | seen |
| X6 `failure = f"{type(exc).__name__}: {exc}"` inline | +1 | **+0** | masked at HEAD (P2-1) |
| X7 `self._last_failure = exc`, raised from another method | +1 | +1 | seen (a `self` stash is followed module-wide) |
| PROTO auth raise inlined as `{type(exc).__name__}` inside the handler | 7 (clean) | **7** (the auth over-report is gone) | the P2-1 fix |
| PROTO + `{exc}` (M8's analogue) | +1 | **+1** | D2's site is genuinely visible |

The prototype also passes `test_cognito_auth.py` + `test_unchained_raise.py`: 36 passed, rc 0, ruff clean.

### Mutation proofs at HEAD `645b334`

**Targeted set.** `tests/unit/sdk`, `test_credential_crypto`, `test_voice_notes`, `test_door_failure_logging`, `test_progress_editing`, `test_app_wiring`, and the two telemetry log sweeps. Unmutated, it gives **508 passed, 1 skipped, rc 0** (r4's 503 plus the range's 5).

**HEAD blob md5s (first 8):**

| file | md5 |
|---|---|
| `errors.py` | `74e5f14f` |
| `_door.py` | `bfe74aee` |
| `flynapse_client/chat.py` | `aa777f46` |
| `auth.py` | `9213bca0` |
| `dochub.py` | `17d43672` |
| `events.py` | `19a02bdf` |
| `crypto.py` | `d9b0e73f` |
| `voice.py` | `7daea52d` |
| `app.py` | `d104c4e6` |
| `tests/_rendered.py` | `8a4c03d4` |

| # | plant | red (targeted) | reading |
|---|---|---|---|
| F1a | `__exit__` keeps `__context__` | 16 (every site test, both auth ambient tests, the mechanism test) | sound |
| F1b | `__exit__` clears nothing | 16 | sound |
| F1c | `__exit__` makes a cycle (`value.held = value`) | 1 (the GC test) | sound |
| F1d | `send_json` transport: `unchained` dropped, `from None` kept | 1 (`test_a_door_that_cannot_be_reached_is_named_by_the_failures_type_alone`) | sound |
| F2a | decoder: `unchained` dropped | 1 (the malformed-frame test) | sound |
| F2b | non-JSON body: `unchained` dropped | 1 (the past-the-cap test) | sound |
| F3a / F3b / F3c / F3d | each `SystemExit` without `unchained` | 1 / 1 / 1 / 1, each its own `test_app_wiring` test | sound |
| N14 | frame stashed on `error.data` | 1 (the malformed-frame test) | r4 decoy now caught |
| N15 | httpx text into `body_snippet` | 2 (both D1 tests) | r4 decoy now caught |
| G1 | `__exit__` keeps `__cause__` | 1 (the mechanism test; every site has `from None`) | sound |
| **G3** | `__exit__` does not set `__suppress_context__` | **0; whole suite 2210 passed** | **unguarded line (P3-3)** |
| G22 | `__exit__` returns `True` (swallows) | 51 | sound, and mypy's `exit-return` rejects the annotation |
| G13 | auth `_initiate_auth`: `unchained` dropped | 2 (both ambient tests) | sound |
| **G14** | auth `ensure_id_token` no-refresh raise: `unchained` dropped | **0; whole suite 2210 passed** | **unguarded site (P3-3)** |
| **G15** | auth `_token_set` no-ID-token raise: `unchained` dropped | **0; whole suite 2210 passed** | **unguarded site (P3-3)** |
| G16 | signed leg: `unchained` dropped | 1 | sound |
| G17 / G18 | decrypt / key error: `unchained` dropped | 1 / 2 | sound |
| G19 / G20 | voice / `stream_turn`: `unchained` dropped | 1 / 1 | sound |
| G5 | `ApiError` stops capping `body_snippet` | 1 (`test_api_error_caps_the_snippet_in_its_own_constructor`; `send_json` caps first too) | sound |
| G7 | `transport_error` stores `exc` as an attribute | 2 (both D1 tests, through `vars()`) | sound |
| G9 | `detail = str(exc)` left as a frame local in `send_json` | **0** | declared limit (`_rendered.py:17`), as expected |
| G23 | non-JSON snippet taken from the body's TAIL | 1 (the past-the-cap test) | the test is about the body, not only the chain |
| G25 | the environment refusal appends `{error}` | 2 (the new `main` test and the log sweep) | sound |
| G21a / G21b | the `vars()` line removed, + N14 / + N15 | **0 / 0** | attribution: that one line is what catches N14 and N15 |
| M1 / M4 / M8 / M9 / M11 | r4's message-half plants at HEAD | 2 / 3 / 7 / 2 / 1 | sound |

Every restore was md5-equal to the HEAD blob. Every run logged 0 netguard refusals.

### `unchained` under every raise shape (`shapes.py`, at HEAD)

| shape | after the block |
|---|---|
| nested `with unchained()` | cause None, context None |
| a raise of an EXISTING instance that carried a chain | cause None, context None |
| the error's own constructor raises (an `AttributeError` while building) | that error leaves with no context either (protective: its context was the leaky one) |
| a raise through a call inside the block (not literal) | cleared |
| async: a coroutine raising in the block, awaited directly from a caller's handler | cleared |
| async generator (the `stream_turn` shape) consumed inside a handler | cleared |
| `SystemExit` | cleared |
| `except*` + `unchained` | clean (sole member: the `ApiError` itself; mixed: a new group with no context) |
| a bare `raise` inside the block | re-raises the handled exception itself; the leak IS the error (no site does this) |
| **`ExceptionGroup` raised in the block** | the group is cleared, **its members keep their chains**; `format_exception` prints them (P3-2; no site raises a group, and no `except*` is used) |
| **the same object re-raised later inside a handler** (`raise held`, or a Task awaited in a handler) | a new `__context__` attached, hidden by the leftover `__suppress_context__` |
| **`FlynapseClient.ensure_id_token` (`asyncio.to_thread`) awaited inside `except ApiError:`** | **`__context__` = that `ApiError`, the sentinel reachable** (P2-3) |

`__exit__ -> Literal[False]` is correct in every shape: it never swallows. And it is load-bearing. With `-> bool`, mypy reports `exit-return` plus four reachability errors (`crypto.py:89` missing return, `auth.py:192` ×2, `voice.py:215`).

---

## Findings, ranked

### No P0, no P1

At HEAD every one of the 15 `with unchained():` blocks is exactly one literal `raise <Call>` (AST scan). There are no implicit chains. `raise_unchained` and `auth._raise_unchained` are gone, and no other repo imports `flynapse_client` (workspace search). The r4 P1-1 mechanism is settled by F1a/F1b/G1/G22. At the pin the controller's call was measured against, the detector sees every r4 mutant again.

### P2-1: at flynapse-otel HEAD the rescan is 8, not 7, and D2's regression hides under the eighth

**Where.** `flynapse_client/auth.py:203` (`failure = _failure_detail(exc)`) and `:210-211` (`with unchained(): raise AuthError(f"cognito {operation} failed: {failure}")`). Also `docs/plans/exception-text-withholding.md:531-535` ("Unmutated: the same 7 triaged over-reports") and `:577` ("with the seven over-reports registered").

**Measured.** flynapse-otel `56b1814` reports **8** at `b30d0a3`, `10e1c82` and `645b334`. Its narrowing was withdrawn in `5c7e1dc`, committed 10 minutes before `b30d0a3`. The eighth finding is `flynapse_client/auth.py:211 CognitoAuthenticator._initiate_auth [raise] raise.caught-text :: failure reaches raise`. It is D2's own site: the literal raise made it visible (the r4 fix works), but visible as an over-report, since `_failure_detail` returns `type(exc).__name__`. **M8 is +0 and X6 is +0 at `56b1814`.** The finding's key `(path, qualname, rule)` and its site text (the raise line) are identical clean and mutated. So registering it, even with `sites=`, makes the detector blind to exactly the regression D2 fixed.

**Failure scenario.** telegram-bot adopts the detector (Future Improvements) and registers the 8 findings it sees. Someone later "improves" `_failure_detail` to return `f"{type(exc).__name__}: {exc}"`. botocore's `ParamValidationError` then puts the password in the message. The adoption guard stays green. Only the behavioural Cognito tests (M8 red 7) stand between that and a leak. That is the situation r4 P1-1 existed to end.

**Fix.** Inline the class name at the raise, inside the handler, under `unchained`. The old "raise OUT HERE" rationale (drop the local context) is moot now that `unchained` clears it:
```python
try:
    return self.client.initiate_auth(**request)
except Exception as exc:
    with unchained():
        raise AuthError(f"cognito {operation} failed: {type(exc).__name__}") from None
```
Delete `_failure_detail` and keep its docstring as the comment. Prototyped: `56b1814` clean **7**, the `{exc}` analogue **+1** (at `927a729` too). The 36 Cognito and `unchained` tests pass, and ruff is clean. If the helper is kept instead, the plan must say the scan is 8 at `56b1814`+ and that D2's site is held by its behavioural test alone.

### P2-2: the detector does not read the chain half of the idiom, so "adoption covers every site written in this repo's idiom" is half true

**Where.** `docs/plans/exception-text-withholding.md:571-580` (Future Improvements, r3 P3-3's closing route).

**Measured.** The idiom has two halves: the message (the class, never the text) and the chain (`unchained`). The detector reads only the first:
- X1 (`from exc` restored), X2/F1d (`unchained` dropped) and X3 (the decoder's chain restored) are **+0 at both `927a729` and `56b1814`**;
- per-site behavioural tests hold every existing site (F1d, F2a, F2b, F3a–d, G13, G16–G20 red);
- a NEW site is held by nothing.

This is the defect class the last two rounds found by hand in this repo: r3 P2-1 (D1 kept `from exc`), and r3 P3-1 / r4 P3-4 (`from None` only hid the link). Today there are 0 bypasses (TG5-21), so nothing leaks.

**Failure scenario.** A new door, a new carrier failure or a new startup refusal is written `raise ApiError(f"… {type(exc).__name__}") from exc`. The message is clean, so the detector (adopted or not) is green, and no repo test reads the new site's chain. httpx's text rides `__cause__` into every traceback renderer.

**Fix.** A small in-repo AST guard (under `tests/unit/infra/` or beside the log sweep). Every constructed `raise` lexically inside an `except` in `flynapse_client/` and `telegram_bot/` must sit under `with unchained():`, or be named in an allow-list with its reason. Today that allow-list is the four `document_watch._WatchOver … from error`. It is decidable, and F1d/X1/X2 are its mutation proofs. Or, at minimum, rewrite the Future Improvements entry to say that adoption closes the message half only.

### P2-3: `unchained`'s named ambient case does not hold through the package's own async facade

**Where.** `flynapse_client/client.py:90` and `:99-101` (`asyncio.to_thread`). The claim sits in `flynapse_client/errors.py:56-63` and `auth.py:20-28`: "A door client retrying a 401 (`except ApiError: ... ensure_id_token(...)`) is exactly such a caller."

**Measured** (`tothread.py`, at HEAD):
- `CognitoAuthenticator.ensure_id_token` called directly inside `except ApiError:` gives `__context__ None`.
- The same call through `FlynapseClient.ensure_id_token`, the only way the bot reaches it, gives **`__context__ = the ApiError`, sentinel reachable**, `__suppress_context__` True. `unchained` runs in the worker thread, which holds no handled exception, and `Future.result()` re-raises the error on the loop inside the caller's handler, which attaches a new context.
- The same happens to any door coroutine run as a Task and awaited inside a handler (shape 7b).
- The auth ambient tests call only the sync authenticator, so they cannot see it.
- No caller does this today: no door or identity call sits inside an `except` (`awaitscan.py`; `page_photos._document` swallows every failure inside its own task).
- It predates the range, since `raise_unchained` behaved the same. r4's E9 listed re-raise seats but not `to_thread`.

**Failure scenario.** A handler written the way the docstring describes, for example a 401 retry: `except ApiError: token = await client.ensure_id_token(held, …)`. If the refresh fails, an `AuthError` arrives carrying the caller's exception on `__context__`. A crash reporter or chain walker reads it. And if G3 (TG5-13) ever lands, every traceback renderer prints it.

**Fix.** Either:
- clear on the loop side as well: in `FlynapseClient.login`/`ensure_id_token`, `except FlynapseClientError: with unchained(): raise`, with a test that awaits the facade inside a handler holding a sentinel and walks the chain (this also kills G3's survivor path); or
- narrow the docstrings to "as the error leaves the block; a later re-raise of the same object — `Future.result()` across `asyncio.to_thread`, a Task awaited in a handler — attaches a new context, hidden only", and record it as a limit.

### P3-1: what `unchained` costs an operator is not declared anywhere

`unchained` drops the cause's message and frames: which host or port refused, DNS versus refused (both `ConnectError`), the parse position of a malformed frame, and libpq's reason at startup. The class survives in the message at the transport, voice, key and auth sites. It does not survive at the decrypt site (`InvalidToken` versus `UnicodeDecodeError` versus `TypeError`), the malformed frame, the non-JSON body or the four `SystemExit`s. The only statement of the trade-off is in r4's packet ("the cause's CLASS is still in every message"), which is not true of those seven sites. The `unchained` docstring argues only the benefit. **Fix.** Add one paragraph to `unchained`'s docstring or the plan naming the cost and where an operator reads the rest (the backend's or libpq's own log). Optionally carry the root `OSError.errno`, an integer the detector sanctions, on transport failures.

### P3-2: two docstrings promise more than their mechanism does

- `errors.py:42`, "Whatever is raised inside the block leaves it with no chain at all": an `ExceptionGroup`'s members keep theirs (shape 4 leaks through `format_exception`). No site raises a group.
- `tests/_rendered.py:14` and `:33`, "the repr of every ATTRIBUTE it holds (`vars()`)" and "every attribute": this is `__dict__` only. A `__slots__` field or a property is invisible (`chainprobe.py`). No exception here uses either.

**Fix.** Narrow both sentences.

### P3-3: three lines of the mechanism are unguarded

- **G3.** `errors.py:85` (`value.__suppress_context__ = True`) survives the whole suite. `test_unchained_raise.py:41` asserts the flag, but `_raise_under` raises `from caught` (`:32`), which sets it by itself, and every in-handler site says `from None`. The line only matters on a later re-raise (P2-3). **Fix.** Assert it after a raise with no `from` (auth's shape), or through the P2-3 facade test.
- **G14 / G15.** Two of auth's three sites, `auth.py:187` (no refresh token, no password) and `:225` (no ID token), survive the whole suite with `unchained` dropped. Before the range, all three called `_raise_unchained`, and N19 on that one helper turned 2 red. Now each site regresses on its own, and only `:210` is held (G13). Exposure today is nil: in the worker thread the only ambient exception is the refresh `AuthError`, whose text is clean. **Fix.** Parametrize `test_login_from_inside_a_handler_does_not_pick_up_the_ambient_exception` over the three failure paths.

### P3-4: plan and doc hygiene

- `exception-text-withholding.md:579-580`, "Sites that depend on it until then: every `raise` inside an `except`": auth's three sites sit outside any `except`.
- `## Lessons` has no entry from r3 or r4. Two lessons are worth keeping: a helper that raises its argument takes the raise out of a syntactic detector's sight, and a chain view that reads no attributes cannot see `.doc`.
- `auth.py:235-238`: three blank lines where `_raise_unchained` was (E303, preview-only in ruff).
- `test_unchained_raise.py` names its context "ambient", but it is the local handler's exception. The true ambient case is covered by the auth tests (F1a red).

---

## What I tried to break and could not

- **A path carrying text at HEAD.** The only chained raises left are the four `_WatchOver … from error`. They chain `AuthError`/`ApiError`s whose messages are class, status or length. The `ApiError`'s capped `body_snippet` rides the cause by design, and `failure_fields` never walks the chain. `body_snippet` past its cap: G5 and G23 are red. The two JSON decode sites (`_door.py:203`, `events.py:462`) are the only ones in the package, and both are unchained. No log or span call was added or changed by the range.
- **A bypass of `unchained`.** Of 79 raises, 12 in-handler constructions and 3 out-of-handler auth raises are all under `unchained`. The other in-handler raises are 14 bare re-raises and the 4 deliberate `_WatchOver`s. There are 0 implicit chains.
- **The GC claim.** F1c is red, and the old helper is red on the same test. A real site's traceback frames hold no reference back to the error, because the `except … as` names are deleted.
- **B904.** Dropping `from None` at a site while keeping `unchained` is a runtime-equivalent mutant, and ruff's B904 flags it.
- **The red-before claims** of all three commits. Each failed on the right channel.

## What I did not test

- **The 300 Postgres-backed tests**, skipped by design. None exercises the range.
- **A live PTB or Cognito failure, or a real crash reporter.** Chains and attributes were measured with `vars()` walks and `format_exception`.
- **The detector as an adopted guard** (`reconcile`/`ratchet`). Only `scan` was run, read-only. The masking in P2-1 is argued from `Accepted.key` and `Finding.site`, not from a registered run.

## Claims table

Severity on a SETTLED row is the class of the property the row holds: 0 means it would be a content leak if it regressed. On an OPEN or PARTIAL row, severity is the finding's own.

| # | Repo | File:line | Claim (decision taken) | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state | Answers r4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TG5-01 | telegram-bot | `flynapse_client/errors.py:41-86` | `unchained` context manager: `__exit__` clears `__cause__`/`__context__`, sets suppress, returns `Literal[False]` | Keep the raise literal (the detector reads a syntactic `raise`); no cycle | `shapes.py` (every raise shape); mypy needs `Literal[False]` (5 errors with `bool`) | `test_unchained_raise.py` + the 15 site tests | **yes**: F1a 16, F1b 16, G1 1, G22 51 red; G3 survives (TG5-13) | 0 | 0 | F1 | **SETTLED** (bar line 85) | P1-1 mechanism: **CLOSED** |
| TG5-02 | telegram-bot | the 15 `with unchained():` blocks | Every site is one literal `raise <Call>`; `raise_unchained`/`_raise_unchained` deleted | r4 P1-1, option (a) | AST scan; at `927a729` M1/M4/M8/M9/M11 = +2/+1/+1/+1/+1 at b30d0a3 and 645b334 (r4's control) | the detector (not adopted; read-only) | **yes** (5 pairs at `927a729`) | 1 | 1 | F1 | **SETTLED** at `927a729`; **PARTIAL** at `56b1814` (M8 +0: TG5-14) | P1-1: **CLOSED** at the pin |
| TG5-03 | telegram-bot | `tests/unit/sdk/test_unchained_raise.py:63-76` | No reference cycle | r4 P3-2 | GC test red with the old helper at `0af46b1` | the GC test | **yes**: F1c red 1 | 3 | 0 | F1 | **SETTLED** | P3-2: **CLOSED** |
| TG5-04 | telegram-bot | `_door.py:196`, `flynapse_client/chat.py:113` | Transport `ApiError` unchained, named by class | r3 P2-1 | — | `test_provisioning_client.py` (unreachable door), `test_chat_client.py` (transport) | **yes**: F1d 1, G20 1, M1 2, M4 3, N15 2, G7 2 | 0 | 0 | F1 | **SETTLED** | TG4-02 held |
| TG5-05 | telegram-bot | `dochub.py:229` | Signed leg unchained | r3 P3-1 | — | `test_dochub_client.py` signed-leg URL test | **yes**: G16 red 1 | 0 | 0 | F1 | **SETTLED** | TG4-04 held |
| TG5-06 | telegram-bot | `telegram_bot/crypto.py:79`, `:94` | Both cipher errors unchained | r3 P3-1 | — | `test_credential_crypto.py` key and decrypt chain tests | **yes**: G17 1, G18 2, M9 2 | 0 | 0 | F1 | **SETTLED** | TG4-06 held |
| TG5-07 | telegram-bot | `telegram_bot/handlers/voice.py:211` | `CarrierFailure` unchained | r3 P2-1 | — | `test_voice_notes.py` fetch test | **yes**: G19 1, M11 1 | 0 | 0 | F1 | **SETTLED** | TG4-05 held |
| TG5-08 | telegram-bot | `flynapse_client/auth.py:187`, `:210`, `:225` | auth's three raises under `unchained` | ambient context (a caller's handler) | G13 red 2; **G14, G15 survive the whole suite (2210 passed)** | `test_cognito_auth.py:529`, `:551` (the `:210` path only) | **partly**: `:210` yes; `:187`, `:225` no | 3 | 1 | F1 | **SETTLED** `:210`; **ASSERTED** `:187`, `:225` | TG4-07: **PARTIAL** (P3-3) |
| TG5-09 | telegram-bot | `flynapse_client/events.py:467-470` | `MalformedEventError` unchained | r4 P3-1: `JSONDecodeError.doc` is the whole frame (the pilot's answer) | red-before on `.doc` | `test_sse_events.py` malformed-frame test | **yes**: F2a 1, N14 1 | 0 | 0 | F1 | **SETTLED** | TG4-09 / P3-1: **CLOSED** |
| TG5-10 | telegram-bot | `_door.py:209-215` | A non-JSON success body is unchained; the capped snippet is the only body copy | the same `.doc` shape one module over | red-before on `.doc` (body past the cap) | `test_provisioning_client.py` past-the-cap test; `test_api_error_caps_the_snippet_in_its_own_constructor` | **yes**: F2b 1, G23 1, G5 1 | 0 | 0 | F1 | **SETTLED** | P3-1 (extension): **CLOSED** |
| TG5-11 | telegram-bot | `tests/_rendered.py:43` | The chain view reads every link's `vars()` | r4 P3-1: N14/N15 survived | N14 and N15 red; with the line removed they survive (G21a/b), so it is the catching line | imported by 9 test files (25 call sites) | **yes** (plus attribution) | 3 | 0 | F1 | **SETTLED**; the docstring overclaims (P3-2) | TG4-10: **CLOSED** |
| TG5-12 | telegram-bot | `telegram_bot/app.py:1342`, `:1357`, `:1377`, `:1386` | `main`'s four `SystemExit`s inside `unchained` | r4 P3-4: context = a `ValidationError` (the environment) or a psycopg error (the DSN password) | red-before 4/4 | the four `test_app_wiring` `SystemExit` tests | **yes**: F3a–F3d 1 each, G25 2 | 0 | 0 | F1 | **SETTLED** | P3-4 code: **CLOSED** |
| TG5-13 | telegram-bot | `errors.py:85`; `test_unchained_raise.py:32`, `:41` | `__suppress_context__ = True` is asserted | "nothing for the default printer" | G3 survives the whole suite: `from caught` sets the flag itself | none effective | **no**: the assertion is vacuous | 3 | 1 | F1 | **ASSERTED** | — (new, P3-3) |
| TG5-14 | telegram-bot | `auth.py:203`, `:210-211`; plan `:531-535`, `:577` | "The final rescan is exactly 7 triaged over-reports" | — | 7 at `927a729` (reproduced at all 4 SHAs); **8 at `56b1814`** (b30d0a3+); M8 +0, X6 +0 at `56b1814`; the inline prototype gives 7 clean / +1 | none (not adopted) | **yes, and the property fails at HEAD otel** | 2 | 1 | F3 | **OPEN** (P2-1) | TG4-16: true at its pin, stale at HEAD |
| TG5-15 | telegram-bot | plan `:571-580` | Adoption "covers every site written in this repo's idiom" | r3 P3-3's closing route | X1, X2/F1d, X3 +0 at both detector SHAs | none | **yes, and the property fails** | 2 | 1 | F3 | **OPEN** (P2-2) | TG4-17 / P3-3: recorded (**CLOSED** as a record); the claim is overstated |
| TG5-16 | telegram-bot | `flynapse_client/client.py:90`, `:99-101`; `errors.py:56-63` | The ambient context is dropped for "a door client retrying a 401" | the docstring's own motivating case | `tothread.py`: through the facade `__context__` = the caller's `ApiError`; direct = None | none (the tests use the sync authenticator) | n/a (probe) | 2 | 1 | F1 | **OPEN** (P2-3) | — (new; predates the range) |
| TG5-17 | telegram-bot | `errors.py:41-71` | The trade-off of dropping the cause | — | the class is lost at decrypt, malformed frame, non-JSON body and 4 `SystemExit`s; DNS versus refused lost everywhere | none | n/a | 3 | 1 | F1 | **OPEN** (P3-1) | — (new) |
| TG5-18 | telegram-bot | `errors.py:42`; `tests/_rendered.py:14`, `:33` | "no chain at all"; "every attribute" | — | group members keep their chains; `__slots__` and properties invisible (`chainprobe.py`) | none | n/a | 3 | 1 | F1 | **OPEN** (P3-2) | — (new) |
| TG5-19 | telegram-bot | plan `:579-580`, `## Lessons`; `auth.py:235-238`; `test_unchained_raise.py:1-9` | Plan and doc hygiene | — | read at HEAD | none | n/a | 3 | 1 | F3 | **OPEN** (P3-4) | TG4-18 wording (`config.py:66-68`, `test_dochub_client.py:399-402`, `:418-421`): **CLOSED** |
| TG5-20 | telegram-bot | range `0af46b1..645b334` | Each commit lands fix plus guard, green at its own HEAD; new tests red on the parent | the plan's lessons | 2205 → 2208 → 2209 → 2210 (+300 skipped), rc 0; ruff and mypy clean; red-before 2/2, 4/4, and the GC test against the old helper | the suite | n/a | 3 | 0 | F3 | **SETTLED** (the DB-backed half is not measured) | TG4-15 held |
| TG5-21 | telegram-bot | `flynapse_client/`, `telegram_bot/` | No constructed raise in a handler bypasses `unchained`, bar the four `_WatchOver … from error` | the chain half | `raisescan.py`: 12 + 3 under `unchained`, 14 bare, 4 deliberate, 0 implicit; `awaitscan.py`: no door or identity call inside a handler | none (scan) | n/a | 1 | 1 | F1 | **OPEN** (scan only; P2-2 makes it a guard) | TG4-14 re-verified |
| TG5-22 | telegram-bot | `_door.py` `send_json`, `events.py` `_decode`, `auth.py` `_initiate_auth` | Frame locals hold the whole body, the frame, the password | predates; declared at `_rendered.py:17` | G9 survives (expected) | none | n/a | 3 | 1 | F1 | **OPEN** (predates; no sink) | TG4-19 carried |

## Open claims, tier 2 first

**Tier 2: none.** Nothing here is irreversible or estate-shaping: the range is unpushed and adds no schema. It removes the public `flynapse_client.errors.raise_unchained`, but no other repo imports `flynapse_client`.

**Tier 1: open, partial or asserted**

1. **TG5-14 (P2-1).** At flynapse-otel HEAD the scan is 8, and D2's regression (M8) is +0 under the eighth. Inline `type(exc).__name__` at the auth raise under `unchained` (prototyped: 7 clean, +1 mutated, 36 tests green) before adoption, or record 8 and that D2's site is held by its behavioural test alone.
2. **TG5-15 (P2-2).** The chain half is invisible to the detector. Add the in-repo AST guard (every constructed raise in a handler under `unchained` or allow-listed), or rewrite Future Improvements to claim the message half only.
3. **TG5-16 (P2-3).** The `to_thread` facade re-attaches a caller's handled exception. Clear it on the loop side, with a facade-in-a-handler test, or declare the limit in both docstrings.
4. **TG5-08 and TG5-13 (P3-3).** G14, G15 and G3 survive the whole suite. Parametrize the auth ambient test over the three paths, and assert the suppress flag on a raise with no `from`.
5. **TG5-17 (P3-1).** Declare what `unchained` costs an operator.
6. **TG5-18 (P3-2).** Narrow the "no chain at all" and "every attribute" sentences.
7. **TG5-19 (P3-4).** Plan and doc hygiene: the "every raise inside an except" wording, a Lessons entry for r3/r4, the blank lines, the "ambient" label.
8. **TG5-21.** No bypass today; it is a scan, not a guard, until P2-2 lands.
9. **TG5-22.** Frame locals, carried from r4. They predate the range and have no sink.
