# Claims packet: telegram-bot review r3 (the shared detector's 12 findings, triaged and fixed)

Independent adversarial review by Opus, 2026-09-21. It was read-only throughout. No code tree was edited, checked out or committed. Every commit ran from a `git archive` copy in private scratch (`scratchpad/tg-review-r3/`). Every mutation ran in a separate archive copy (`ws-mut`). Each mutated file was restored from a pristine per-file backup and md5-checked against the `git show cfb1d98:<path>` blob after every run, and every restore matched.

One harness defect is disclosed here. My first harness restored a two-edit mutant (M4) in the wrong order and aborted on the md5 mismatch. That left `chat.py` mutated for one run (M5). I stopped the loop and rebuilt `ws-mut` from a fresh archive, verifying every file against HEAD. I then fixed the harness (one pristine backup per file) and re-ran M5 onward. M1 to M4 had run and restored correctly before the fault, and their results stand.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| telegram-bot | `/home/aditya/Code/telegram-bot` (clean, HEAD `cfb1d98`, unpushed) | `main` | `0f0337e..cfb1d98` | `52cd5b6` D1 · `3bc01b5` D2 · `8b67978` D3 · `c81bf86` D4 · `cfb1d98` D2b |

**How I ran it.**
- **Copies.** Each commit was extracted with `git archive <sha>` to `ws-<sha>/telegram-bot`. flynapse-otel `34c814a` was extracted beside it as `ws-<sha>/flynapse-otel`, so the editable sibling another lane is changing was never imported.
- **Interpreter.** I used telegram-bot's own `.venv`: Python 3.11.15, PTB 22.8, botocore 1.43.73, httpx 0.28.1, cryptography 50.0.0. It ran from the copy's root with `VIRTUAL_ENV` unset and `PYTHONPATH=<copy>:<copy>/tests:<otel copy>:<guard dir>`, which beats the venv's `.pth` files. A fresh `PYTHONPYCACHEPREFIX` was used for every run, and no `__pycache__` existed in any copy.
- **No network.** A `sitecustomize.py` on `PYTHONPATH` refused every non-loopback `connect`/`connect_ex`, every non-local `getaddrinfo` and any local Postgres socket, and logged each refusal. It was verified before use: a direct connect, an asyncio `sock_connect` and a DNS lookup were each refused and logged. Every test and probe run logged **0 refusals**.
- **No database.** `BOT_TEST_DB_URL=postgresql://127.0.0.1:1/none` (a closed loopback port), so the Postgres-backed tests SKIP through their own fixture. No schema was created. No `.env` exists in any archive, and none was read. No docker, AWS, Cognito or Telegram call was made, and no DB MCP was used.
- **Exit status.** pytest's own exit status was taken directly (`rc=$?`, no pipe) on every run.
- **Provenance.** `rootdir: …/tg-review-r3/ws-cfb1d98/telegram-bot`. `telegram_bot.__file__` = `…/ws-cfb1d98/telegram-bot/telegram_bot/__init__.py`. `flynapse_otel.__file__` = `…/ws-cfb1d98/flynapse-otel/flynapse_otel/__init__.py`. `test_import_provenance.py` passed, printing the same two paths.

**Every commit is green at its own HEAD.** Each step adds exactly the tests its commit adds: 2 + 1 + 2 + 1 + 1 = 7. That matches the implementer's `unit 2494 → 2501`.

| commit | result (pytest rc) |
|---|---|
| 0f0337e (base) | 2195 passed, 300 skipped (0) |
| 52cd5b6 D1 | 2197 passed, 300 skipped (0) |
| 3bc01b5 D2 | 2198 passed, 300 skipped (0) |
| 8b67978 D3 | 2200 passed, 300 skipped (0) |
| c81bf86 D4 | 2201 passed, 300 skipped (0) |
| cfb1d98 D2b | 2202 passed, 300 skipped (0) |

The 300 skips are the Postgres-backed tests, which skip with no reachable database, plus one live-stack test. None of the files the range touches, and none of the test files that exercise its code, is among the skipped files. The only overlap is one psycopg data-exception test in each telemetry file. `ruff check` and `mypy` are clean over every touched module and test.

**The detector rescan reproduces.** I ran the flynapse-otel `34c814a` detector read-only with the policy the plan names:
- `failure_fields` from `telegram_bot.failure`;
- `headline_of` from `flynapse_client.errors`;
- `configuration_error` from `telegram_bot.config`;
- `seed_attributes={"error"}`.

It reads 53 modules. At `0f0337e` it reports 12 findings. At `cfb1d98` it reports exactly the 7 the plan triages as over-reports.

**Verdict: MERGE-CLEAN (0 P0 / 0 P1 / 3 P2 / 5 P3).** No exception text reaches a pilot's reply, a log line, a span or a stderr traceback on any path reachable today. How far each fix goes:
- **D2/D2b and D3** remove the text from every renderer that exists.
- **D1 and D4** remove it from the error's `str()` only. The same bytes still ride `__cause__` into every traceback renderer, and those renderers are the only sinks the plan says the message ever reached. For these two exception types, no such renderer is reachable today, which is why this is P2 and not P1.

The implementer should decide P2-1 (break the chain, or record why it stays) before this phase is marked closed.

---

## Findings, ranked

### No P0, no P1

I looked for a live path and did not find one.
- Every catch site of `ApiError`, `AuthError`, `CarrierFailure` and `InvalidCredentialKey` hands the error to `failure_fields` (class and frames, no chain walk) or to `headline_of` (class, status, door).
- Every reply reads a status code or a class.
- Every span write goes through `record_failure` (class only) and the shared export boundary.

A whole-exception renderer would print the chain. I checked the four that could, and none can see an `ApiError` or a `CarrierFailure` today:
- **asyncio's "Task exception was never retrieved".** `page_photos._document` catches `Exception`, and the `run_turn` gather (`return_exceptions=True`) marks every leg's exception retrieved.
- **PTB's own `exc_info` records.** PTB 22.8 routes handler, job and polling failures to `report_failure`, and its task-done callback retrieves every task exception.
- **`sys.excepthook` at exit.** `post_init` (`_publish_commands`, `digest.catch_up`) calls no `flynapse_client` door.
- **A stdlib record with `exc_info` from this repo.** The log sweep forbids it.

### P2-1: D1 and D4 withhold the text from the error's `str()` only. `__cause__` still carries it to every traceback renderer, and the new tests pin that in place

`flynapse_client/_door.py:193` and `flynapse_client/chat.py:112` (`raise transport_error(...) from exc`); `telegram_bot/handlers/voice.py:205-210` (`raise CarrierFailure(...) from error`).

The plan's sink map for rows 1-2 says the message "reached only what renders a raised exception whole: a traceback on stderr (PTB's own records …) and any future `%s` or `exc_info` site". D1 changes the message and keeps `from exc`. So on every renderer in that list, the httpx text is still there: the traceback prints the cause's `Type: message` line before "The above exception was the direct cause of the following exception". D4 is the same, with PTB's `NetworkError` text, which the D4 commit itself says "can quote a token-bearing file URL". PTB 22.8 bears that out:
- `_bot.py:4131` builds `file_path` as `…/file/bot<TOKEN>/…`;
- `_httpxrequest.py:303` renders httpx's text into the `NetworkError`;
- `_baserequest.py:333` quotes the server's payload on a non-JSON error.

I measured it with real code paths and real exception objects, at base and at HEAD (`scratchpad/tg-review-r3/chainprobe.py`, `logs/chainprobe*.out`):

| renderer | D1 `ApiError` (`send_json`, h11-style cause) base → HEAD | D4 `CarrierFailure` (real `_download`) base → HEAD | D3 `InvalidCredentialKey` base → HEAD |
|---|---|---|---|
| `str()` / `repr()` | leak → clean | leak → clean | leak → clean |
| `headline_of` / `failure_fields` | clean → clean | clean → clean | n/a |
| `traceback.format_exception` (what `sys.excepthook` and `Formatter.formatException` print) | **leak → leak** | **leak → leak** | leak → clean |
| a third-party record with `exc_info`, through the bot's own stdout `FailureFormatter` | **leak → leak** | **leak → leak** | leak → clean |
| an asyncio "never retrieved" record, through the same formatter | **leak → leak** | not built | n/a |
| default `sys.excepthook` | not reached today | not reached today | leak → clean |

These are the lines that still carry the text at HEAD. Neither is a quoted source line:
```
httpx.RemoteProtocolError: illegal status line: bytearray(b'HTTP/1.1 SENTINEL-h11-server-bytes')
telegram.error.NetworkError: httpx.RemoteProtocolError: GET https://api.telegram.org/file/bot123456:SENTINEL-bot-token-secret/voice/file_1.oga
```

So D1 and D4 changed no rendering sink's output. The one consumer they did change, a bare `str()` of the error, is not a sink in this repo: the log sweep forbids `%s` of an exception, and the OTLP route stands one in by its class. D3 and D2 differ, and the probe shows why: D3 uses `from None` and D2 uses `_raise_unchained`, so the default printer never shows the chain. The repo already knows this shape. The signed leg in `dochub.py` breaks its chain for exactly this reason, and D1's own docstring edit (`_door.py:28-30`) says the chained cause "can quote the signed URL".

**The new guards resist the complete fix.** Each D1 and D4 test asserts `sentinel in str(<error>.__cause__)` as its premise (`test_chat_client.py:344`, `test_provisioning_client.py:240`, `test_voice_notes.py:478`). Mutation M3 breaks the chain at both D1 sites (`from None`), which is the complete fix, and both D1 tests go red on that premise line.

**Failure scenario.** No reachable path triggers this today. It fires on the first of these:
- a new `create_task` without a catch-all around a door call;
- a caught `ApiError` re-raised out of a PTB callback in a way that reaches `_LOGGER.exception`;
- the owner extending M-TRACEBACK to stdout for third-party records, the open question in the plan's Future Improvements.

Then a proxy's illegal status line, or a file URL with the BotFather token on its path, prints in full, directly above a class-only message that looks withheld.

**Fix (either option; the plan must say which):**
- (a) Break the chain the way the signed leg and `AuthError` do: `from None` with `__context__` cleared, which is `_raise_unchained`'s shape. Re-anchor each test's premise on the exception the fake transport raised, captured in the handler rather than read back through `__cause__`. Add one whole-chain assertion (`_chain_text`).
- (b) Keep the chain on purpose. Then rows 1-2 of the plan and the two docstrings must say that D1 and D4 remove the text from `str()`, and that the same text still reaches every traceback renderer through `__cause__`. They must also say what "for a debugger" costs: nothing in production reads the chain, because `failure_fields` does not walk it.

### P2-2: the new D1 tests check the error object, not the readers every sink uses. A field decoy passes them

`tests/unit/sdk/test_chat_client.py:329`, `tests/unit/sdk/test_provisioning_client.py:228`.

Both tests assert `str(error)` and the exact message. Neither reads `path`, and `path` is the field `headline_of` renders into every door log line (`door=…`). Mutation M5 puts the httpx text into `transport_error`'s `path=` (`f"{path} ({exc})"`) and leaves the message clean:
- both new D1 tests stay **green**;
- the mutant is caught only by the older `test_a_transport_failure_mid_stream_surfaces_as_the_typed_api_error`, which pins `error.path == STREAM_PATH`;
- on the `send_json` side (every other door), nothing pins `path`.

Fix: in each D1 test, also assert that `headline_of(error)` and `failure_fields(error)` carry no sentinel. That checks the two readers every log sink goes through, not only the object.

D4's test calls `_download` directly with a hand-built `NetworkError` rather than going through PTB's transport. That is acceptable: the object is real and carries the sentinel, and the older turn-level test covers the reply.

### P2-3: nothing guards the reply sink. A pilot-facing reply that quotes the chained httpx text passes all 2202 tests

`telegram_bot/handlers/chat.py:3015-3028` (`_door_failure`).

Mutation M15 changes the transport-failure branch to `_with_status(f"{PIPELINE_APOLOGY} {error.__cause__ or ''}", last_line)`. That is reachable: every transport `ApiError` of a copilot turn goes there. It passes the targeted set **and the whole suite (2202 passed, rc 0)**. Nothing catches it for three reasons:
- The detector does not model a Telegram send as a sink.
- The log sweep reads only log, print and exit sinks.
- No copilot-turn test scripts a transport failure through the real client. The only `raise httpx.…` in `tests/unit/bot/` is fastlane's `ConnectError`, which goes through `fastlane._apology`.

The plan's Phase B claim "Replies to the pilot: none echoes exception text" is true by reading today. I re-checked all four reply builders, and a grep finds no reply that quotes exception text. But the claim is held by nothing.

Fix: one turn-level test in `_copilot_harness` whose route raises an h11-style `RemoteProtocolError` carrying a sentinel. It should assert the sentinel is absent from every message the pilot received, and absent from the turn's log records (`caplog` plus `failure_fields`).

### P3-1: D3's "the chain stays broken" is `from None`, which this repo's own doctrine says is not a break

`telegram_bot/crypto.py:71-76`, `tests/unit/bot/test_credential_crypto.py:147`.

`InvalidCredentialKey.__context__` is still the Fernet `ValueError`, message included (probe: `__context__ carries: True`). This repo's own doctrine says `from None` "only hides the link from the default traceback printer while leaving it there for any logger, debugger or crash reporter to walk". It says so twice: in `auth.py:27-29` and in `test_cognito_auth.py`'s `_chain_text` docstring. The D3 test asserts exactly `__cause__ is None and __suppress_context__` and labels that "the chain stays broken".

It is harmless today. The one real sink is `sys.excepthook` at start-up, and it honours suppression (probe: clean at HEAD). The stdlib logging renderer honours it too, and Fernet's text is constant.

Fix: relabel the assertion ("hidden from the default printer"), or use `_raise_unchained`'s shape and assert `__context__ is None`.

The signed leg, which predates this range, has the same shape (`dochub.py:224-232`): its `__context__` is the httpx error, which can quote the presigned URL. D1 re-wrote that docstring family to say the leg "breaks the chain", so both are worth fixing in one pass.

### P3-2: D2b left a stale docstring, and overstates its own cost

- **Docstring drift.**
  - `telegram_bot/failure.py:17-19` still says Cognito failures become `AuthError` "from the service's own error code". Since D2b the name comes from the exception's class, and the response is not read. This repeats the docstring-family lesson.
  - The tests `test_a_service_error_that_echoes_the_{password,refresh_token}_is_scrubbed` still say "scrubbed" in their names, though their docstrings were fixed.
- **The cost is smaller than the plan states.** The plan says "an unmodeled code (throttling) now reads `ClientError`".
  - Cognito's own throttle, `TooManyRequestsException`, is one of the 18 modelled errors, and it keeps its name (`logs/authprobe.out`).
  - botocore's default retry policy retries `ThrottlingException`, the plan's own example, up to 5 attempts before raising (`botocore/data/_retry.json`, `throttling_exception`).
  - No sink ever showed the code: `headline_of`, `failure_fields` and `record_failure` all render an `AuthError` as `AuthError`. So an operator could not tell a wrong password from a throttle before this range either. D2 and D2b change only what a whole-exception rendering shows.
  - That observability gap predates the range. The real fix, `aws_error_code` as a log field, is already in Future Improvements.

### P3-3: no guard in this repo stops the next `raise X(f"…{exc}")`

`test_logs_carry_no_exception_text.py` covers log, print, `SystemExit`, exit and stream sinks. The only raise it knows is `SystemExit`, and it does not see a raised construction carrying text. That gap is why D1-D4 were found by the shared detector and not by the repo's own guard. Each fix lands with a test pinned to its own site, so a new site elsewhere lands green until the detector is adopted. The plan already covers this: adoption follows the detector review. I record it so the green suite is not read as "the class is closed".

### P3-4 (predates the range): two more exception messages carry content no rule vouches for

- `flynapse_client/_door.py:71-73`: a 401's body snippet is composed into `AuthError`'s message. This is documented in `errors.py`.
- `flynapse_client/events.py:463-466`: `MalformedEventError` quotes `data[:120]!r` of a malformed SSE event, which can be a `synthesis_chunk` of the answer. That is the pilot's own content.

`run_turn` catches both and handles them through `failure_fields` and `_door_failure`, so neither is rendered today. They are latent for the same reason as P2-1, and the fix has the same shape. Route them to whoever takes P2-1.

### P3-5: the plan's triage paragraph overstates what D1 changed

Plan Phase D, "Where `ApiError`'s text went (rows 1-2)", lists "a traceback on stderr … and any future `%s` or `exc_info` site". Read beside D1's "the cause stays chained", it implies D1 closed all of those paths. It closed the `%s` path only. Fold this correction into whichever option P2-1 takes.

---

## What I tried to break and could not

- **A pilot's reply.** There are four reply builders: `chat._door_failure:3015`, `uploads._door_failure:2581`, `invites._apology:496` and `fastlane._apology:599`. Each reads `status_code` and `isinstance` only. `CarrierFailure` is answered with its `apology`, which the carrier writes. A grep of `telegram_bot/` for `{error…}`, `str(error)`, `repr(error)`, `.args`, `.message` and `.description` finds no reply that quotes exception text. The one `str(error)` is a predicate (`uploads.py:2578`). The unguarded half is P2-3.
- **A log line at the fixed sites.** I planted a `%s` of the exception beside the D1 raise (M13) and beside the D4 raise (M14). Both were caught by `test_logs_carry_no_exception_text.py`, which discovers `flynapse_client/` as well as `telegram_bot/`.
- **A span.** `record_failure` writes the class only. The `34c814a` boundary strips `exception.message`, `exception.stacktrace` and status descriptions from the httpx instrumentor's CLIENT spans. No span write was added or changed in the range. botocore is not instrumented (`INSTRUMENTATIONS` = httpx, psycopg, threading).
- **D2b's premise.** I measured it offline against botocore 1.43.73's model:
  - `InitiateAuth` declares 18 errors.
  - For every one, the shape name equals the error code, and `client.exceptions.from_code(code)` returns the same-named subclass.
  - `ThrottlingException` maps to the base `ClientError`. `TooManyRequestsException` is modelled.
- **D2 and D2b in a rendered traceback.** I drove a real `CognitoAuthenticator` against a stub raising three errors: a modelled error quoting the username and a sentinel, an unmodelled one with a prose `Code`, and a modelled throttle. I checked `traceback.format_exception(AuthError)` at each commit:
  - base `0f0337e`: all three leak;
  - `3bc01b5` (D2): the unmodelled one still leaks, which is exactly the defect D2b names;
  - `cfb1d98`: all three clean, with `__cause__` and `__context__` both `None`.
  
  My first run reported a false leak: the username appeared in the quoted source line of my own probe's call. I fixed the probe and re-ran; this is the plan's own source-line lesson.
- **Anything that branches on the Cognito code.** Nothing does.
  - `call_with_backoff` retries only an `ApiError` with status 429 (`retry.py:52`).
  - Every `AuthError` consumer branches on the TYPE only: `chat.py:3026`, `uploads.py:2586`, `manuals.py:889/955/1470`, `document_watch.py:565/572`, and `fastlane`/`invites` through `not isinstance(error, ApiError)`.
  - The copy a pilot reads was already the same for a wrong password and a throttle before this range.
- **`configuration_error` (rows 4, 11, 12).**
  - I set all 30 settings fields to sentinel values and made each field invalid in turn. 29 fields can be made invalid; `digest_feeds` accepts `""`.
  - Each case was rendered plain, with `refusal=MINT_REFUSAL` and with `refusal=SEED_REFUSAL`: **0 leaks in 87 renderings**.
  - The premise held: pydantic's own `str(error)` carried a sentinel in 19 of the 29 cases. The missing-field case prints only `TELEGRAM_BOT_TOKEN — Field required`.
  - There are no custom validators, and the only field types are `str`, `SecretStr`, `int` and `bool`.
  - `SystemExit(msg)` at exit prints the message and no traceback, so the retained `__context__` (the `ValidationError`) is never rendered.
  - M16, a reader that appends `input`, is caught by `test_app_wiring.py:673`.
- **The four `run_turn` legs (rows 6-9).**
  - The detector's own helper map (`ScanResult.helpers`) names the flagged values: `continue_chat_id` and `token` (`_run_turn` slots 4 and 2), `final.citations` and `token` (`send_cited_pages`), and `cost_usd` (`count`, `TurnTrace.finished`).
  - Each descends from `_or_raise(session_leg)` or `_or_raise(token_leg)` through `final`. `_or_raise` raises any `BaseException` leg (`chat.py:2522-2523`). The one other assignment, `_delivered(send_leg)`, returns `Message | None`.
  - None of these values can be an exception, so these are the detector's declared flow-insensitivity over-report.
  - One aside: the detector's helper map shows the `token` parameter landing in "raise" and "log" slots. I traced it. The token reaches only the bearer header. The "raise" slot is the stream's own answer: `_PipelineFailure(event.message)` (`chat.py:2599`) and the door clients' raises. The detector derives those from the call the token was handed to, and no credential reaches a message. `_PipelineFailure`'s message is the backend's error frame; like P3-4, it is caught and logged through `failure_fields` only.
- **The implementer's evidence for row 5 and row 10.** Fernet's constructor messages are constant today, as D3 says, and `upload_filename` keeps only `PurePosixPath(file_path).name`. So the tokened `file_path` never reaches the upload name or the `voice note … uploaded as` line.
- **Commit hygiene.** Each fix landed with its test in the same commit, and each commit is green at its own HEAD. There were no amends. D2's flaw was fixed forward as D2b, as the lessons require.

## What I did not test

- **The 300 Postgres-backed tests.** They were skipped by design: no DB touch was permitted, so their green at each HEAD is not measured here. None of them exercises code in the range.
- **A live PTB transport failure.** D4's premise, that a real PTB `NetworkError` can carry the file URL, was checked by reading PTB 22.8 (`_bot.py:4131`, `_httpxrequest.py:303`, `_baserequest.py:333`), not with a loopback file server.
- **Frame locals.** The raised errors' tracebacks hold frames whose locals include the password (`_initiate_auth`'s `request`) and the bearer token (`send_json`'s `headers`). This bot has no locals-rendering sink (no Sentry, no loguru `diagnose`). This predates the range and was not probed further.
- **The detector itself.** It is reviewed separately (`claims-flynapse-otel-detector-r5.md`). Here it was only run.
- **Stdout policy for third-party records.** This is an owner question (plan Future Improvements). P2-1's option (b) depends on the answer.

## Plants (16), at HEAD `cfb1d98`

Each plant ran against the targeted set: `tests/unit/sdk`, `test_credential_crypto`, `test_voice_notes`, `test_door_failure_logging`, `test_logs_carry_no_exception_text`, `test_logs_withhold_exception_text` and `test_app_wiring`. That is 477 passed and 1 skipped unmutated. A plant that survived the targeted set was then run against the whole suite.

| # | plant | result | reading |
|---|---|---|---|
| M1 | `transport_error` renders `{type}: {exc}` (D1 reverted) | 2 red (both D1 tests) | D1 guard sound |
| M2 | `transport_error` renders `{exc!r}` | 2 red | sound |
| M3 | `from exc` → `from None` at both D1 sites (the complete fix) | **2 red, on the premise line** | tests pin the chain (P2-1) |
| M4 | `stream_turn` bypasses the factory with `f"… {exc}"` | 3 red | sound |
| M5 | httpx text into `path=`, message clean | **new D1 tests green**; 1 older `path` pin red | P2-2 |
| M6 | `_failure_detail` reads `Code` raw (D2b reverted to D2) | 1 red (the unmodelled test) | D2b guard sound |
| M7 | `_failure_detail` renders `Code: Message` (D2 reverted) | 4 red | sound |
| M8 | `_failure_detail` renders `{type}: {exc}` | 7 red | sound |
| M9 | `InvalidCredentialKey` renders `({error}` (D3 reverted) | 2 red (both parametrizations) | D3 guard sound |
| M10 | `from None` → `from error` | 2 red | sound |
| M11 | `CarrierFailure` reason renders `{error}` (D4 reverted) | 1 red | D4 guard sound |
| M12 | NetworkError text into `apology` (the pilot's reply) | 1 red | sound |
| M13 | `LOGGER.warning("…%s", exc)` beside the D1 raise | 1 red (log sweep) | sound |
| M14 | `LOGGER.warning("…%s", error)` beside the D4 raise | 1 red (log sweep) | sound |
| M15 | `_door_failure` quotes `error.__cause__` to the pilot | **0 red, targeted and whole suite (2202 passed)** | P2-3 |
| M16 | `configuration_error` appends pydantic's `input` | 1 red (`test_app_wiring.py:673`) | over-report triage guard sound |

Every restore was md5-equal to the HEAD blob, except M4's. M4's copy was replaced by a full rebuild from the archive, verified file by file (see the header). The HEAD blob md5s were: `_door.py 24aaee08…`, `flynapse_client/chat.py eecd431b…`, `crypto.py 1f57937c…`, `voice.py 79e97c63…`, `handlers/chat.py e251b3ae…`, `config.py 1553c949…`, and `auth.py` (md5 not recorded here).

## Claims table

Severity on a SETTLED row is the class of the property the row holds: 0 means it would be a content leak if it regressed. On an OPEN or PARTIAL row, severity is the finding's own.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TG3-01 | telegram-bot | `flynapse_client/_door.py:111-122` | `transport_error` names method, door and the failure's CLASS; never `{exc}` | h11 quotes a server's status line; httpx text is unvouched | Probe: `str`/`repr` clean at HEAD, leaked at base | `test_chat_client.py:329`, `test_provisioning_client.py:228` | **yes**: M1 and M2 each red both; M4 red 3 | 0 | 0 | F1 | **SETTLED** for the message |
| TG3-02 | telegram-bot | `_door.py:193`, `chat.py:112` | The cause stays chained (`from exc`) "for a debugger" | Keep the httpx exception for debugging | Probe: `format_exception`, a third-party stdout `exc_info` record and an asyncio never-retrieved record all carry the h11 bytes at base AND at HEAD; no renderer reachable for `ApiError` today | the D1 tests assert `sentinel in str(__cause__)` | **yes, and the tests pin the channel**: M3 (the complete fix) turns both D1 tests red | 2 | 1 | F1 | **OPEN**: P2-1 |
| TG3-03 | telegram-bot | `telegram_bot/handlers/voice.py:205-210` | `CarrierFailure`'s reason names the note and the class; cause chained | PTB's `NetworkError` renders httpx text and can quote the tokened file URL | `str` clean; the chain carries `bot<token>` in `format_exception` and a third-party stdout record; `CarrierFailure` always caught by `run_turn` → `failure_fields` | `test_voice_notes.py:468` | **yes** for the message: M11 red, M12 red; the chain is pinned (`:478`) | 2 | 1 | F1 | **PARTIAL**: message SETTLED, chain OPEN (P2-1) |
| TG3-04 | telegram-bot | `flynapse_client/auth.py:258-269` | A failed auth call is named by its class only; the response is not read (D2b) | `Message` is free text about the request; an unmodelled `Code` is whatever the answer said | 18/18 declared errors → same-named subclass; traceback probe clean at HEAD for modelled, unmodelled and throttle; unmodelled leaked at `3bc01b5` | `test_cognito_auth.py:603`, `:623`, plus the pre-existing password and refresh-token tests | **yes**: M6 red 1; M7 red 4; M8 red 7 | 0 | 0 | F1 | **SETTLED** |
| TG3-05 | telegram-bot | `auth.py:235-255` (unchanged) | The `AuthError` chain is cleared by `_raise_unchained` | `from None` leaves `__context__` | Probe: `__cause__` and `__context__` both `None` in all three cases | `test_a_login_that_also_fails_after_a_failed_refresh_carries_no_chain` and the `_chain_text` tests | pre-existing guard; M8 turns it red too | 0 | 0 | F1 | **SETTLED** |
| TG3-06 | telegram-bot | `auth.py` (D2b cost) | Accept: an unmodelled code reads `ClientError` | Class-only is detector-clean and total | No consumer branches on code or message; retry only on `ApiError` 429; Cognito's throttle is modelled; botocore retries `ThrottlingException`; no sink ever rendered `AuthError`'s message | none needed | n/a | 3 | 1 | F1 | **SETTLED**: the cost is smaller than stated (P3-2) |
| TG3-07 | telegram-bot | `telegram_bot/crypto.py:68-76` | `InvalidCredentialKey` names the class and states the requirement; `from None` | Its one sink is stderr at every start | Probe: default `excepthook`, `format_exception` and stdout record clean at HEAD, leaked at base; `__context__` still holds the Fernet `ValueError` | `test_credential_crypto.py:128` | **yes**: M9 red 2, M10 red 2 | 0 | 0 | F1 | **SETTLED** on every stdlib renderer; the assertion's label is PARTIAL (P3-1) |
| TG3-08 | telegram-bot | `app.py:1339`, `mint_invites.py:177`, `seed_salary.py:152` | Rows 4, 11, 12 are over-reports: `configuration_error` renders `loc` and `msg` only | pydantic renders its input; the reader does not | 87 renderings, 0 leaks; premise held on 19/29; `SystemExit` prints no traceback | `test_app_wiring.py:673` | **yes**: M16 red | 0 | 0 | F1 | **SETTLED** (the controller's Option 3 for adoption is not in this range) |
| TG3-09 | telegram-bot | `handlers/chat.py:2221`, `:2305`, `:2497`, `:2510` | Rows 6-9 are over-reports: the detector's flow-insensitivity | `_or_raise` raises any exception leg | The helper map names the values (token, chat id, `final`, `cost_usd`); `_or_raise:2522`; `_delivered` returns `Message | None` | none (register entries planned at adoption) | n/a | 0 | 1 | F1 | **SETTLED** by reading; register entries owed at adoption |
| TG3-10 | telegram-bot | range `0f0337e..cfb1d98` | Every commit lands fix + guard, green at its own HEAD | Lesson "every commit lands green" | 2195 → 2197 → 2198 → 2200 → 2201 → 2202 passed, 300 skipped (DB), rc 0 each; ruff and mypy clean | the suite | n/a | 3 | 0 | F3 | **SETTLED** (DB-backed half not measured) |
| TG3-11 | telegram-bot | detector rescan | 12 → exactly the 7 | — | Reproduced with `34c814a`, same policy, same seven | not adopted | n/a | 3 | 1 | F3 | **SETTLED** |
| TG3-12 | telegram-bot | `tests/unit/telemetry/test_logs_carry_no_exception_text.py` | The log sweep covers the fixed sites | — | Plants beside the D1 and D4 raises | the sweep | **yes**: M13 red, M14 red | 0 | 0 | F1 | **SETTLED** |
| TG3-13 | telegram-bot | the D1 tests | Assert `str()` and the exact message; not `path`, `headline_of` or `failure_fields` | — | M5 (text into `path=`) passes both new tests; caught only by the older mid-stream `path` pin; nothing pins `path` for `send_json` | older `test_chat_client.py` test | **yes, partly**: 1 older test red | 2 | 1 | F1 | **PARTIAL**: P2-2 |
| TG3-14 | telegram-bot | `handlers/chat.py:3015-3028` | "Replies never echo exception text" (Phase B claim, relied on by Phase D) | — | True by reading all four builders; M15 (reply quotes `error.__cause__`) passes 2202/2202 | none | **yes, and the property fails to be guarded**: 0 red | 2 | 1 | F1 | **OPEN**: P2-3 |
| TG3-15 | telegram-bot | repo guard set | No in-repo guard for a raised construction carrying text | Found only by the shared detector | The sweep's only raise sink is `SystemExit` | none until adoption | n/a | 3 | 1 | F3 | **OPEN**: P3-3 (closes at adoption) |
| TG3-16 | telegram-bot | `telegram_bot/failure.py:17-19`; two test names in `test_cognito_auth.py` | Still say "from the service's own error code" and "scrubbed" | — | Read at HEAD | none | n/a | 3 | 1 | F3 | **OPEN**: P3-2 |
| TG3-17 | telegram-bot | `flynapse_client/dochub.py:224-232` (predates the range) | Signed leg `from None`; `__context__` keeps the httpx error | — | D1 re-wrote the family's docstring to "breaks the chain"; the test asserts `__cause__` only (`test_dochub_client.py:458`) | partial | n/a | 3 | 1 | F3 | **OPEN**: P3-1 |
| TG3-18 | telegram-bot | `flynapse_client/events.py:463-466`, `_door.py:71-73` (predate the range) | Exception messages quote SSE data and a 401 body | — | Caught by `run_turn` → `failure_fields`; not rendered today | none | n/a | 3 | 1 | F3 | **OPEN**: P3-4 (route with P2-1) |
| TG3-19 | telegram-bot | plan Phase D, "Where `ApiError`'s text went" | Reads as if D1 closed the traceback paths | — | See TG3-02 | none | n/a | 3 | 1 | F3 | **OPEN**: P3-5 |

## Open claims, tier 2 first

**Tier 2: none.** Nothing in this range is irreversible or estate-shaping. The range is unpushed, adds no schema, and touches no shared contract.

**Tier 1: open or partial**

1. **TG3-02 and TG3-03 (P2-1): the chained cause.** D1 and D4 withhold the text from `str()` only, and every traceback renderer still prints it through `__cause__`. Decide option (a), break the chain and re-anchor the tests, or option (b), keep it and correct the plan and docstrings. Decide it before the Phase D box is closed and before detector adoption.
2. **TG3-14 (P2-3): the reply sink is unguarded.** Add one turn-level transport-failure test with a sentinel.
3. **TG3-13 (P2-2): the D1 tests read the object, not the readers.** Add `headline_of` and `failure_fields` assertions.
4. **TG3-15 (P3-3): no raise-text guard in the repo.** This closes when the shared detector is adopted (the ledger's adoption order puts telegram fifth).
5. **TG3-16, TG3-17, TG3-18, TG3-19 (P3-1, P3-2, P3-4, P3-5):** the docstrings and plan paragraph, the `from None` label, and the two exception messages that predate the range. These are one small pass, best folded into the P2-1 decision.
