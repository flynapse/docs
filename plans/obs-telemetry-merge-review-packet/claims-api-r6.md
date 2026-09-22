# Claims packet: api review r6 (`517f655..73f2aa3`, 12 commits)

This is an independent adversarial review (Opus), done on 2026-09-21. No code tree was changed: every
run used a `git archive` copy in the reviewer's private scratch
(`scratchpad/api-review-r6/`). Every mutation was applied to a scratch copy, then restored, and the
md5 was checked against the HEAD blob; all 42 restores matched.

| repo | worktree | branch | range | HEAD at review | tree state |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `517f655..73f2aa3` | `73f2aa3` | clean (the controller confirmed it) |

The 12 commits, oldest first:

1. `4defb75`: the JWKS line logs the host only.
2. `ce53ecd`: the uvicorn `--log-config` change.
3. `0f4d58b`: `LOGURU_DIAGNOSE=NO`.
4. `e3c7b69`: the G.53 carry-spec documentation.
5. `8d7e39f`: the `_root.py` P3-1 fix.
6. `d474a90`: Rule B P3-2.
7. `2b2a731`: Rule B P3-3.
8. `6ae9701`: the traceparent consumer.
9. `8d7f587`: the invitation-preview POST.
10. `35639cb`: `GET /auth/permissions`.
11. `c2c99be`: the `test_jwks` rewrite and the sink guard.
12. `73f2aa3`: the conftest blanks the Cognito pool.

## How it was run

- Each commit, and the base, was extracted with `git archive <sha>` into `ws-<sha>/api-obsm`.
- Its siblings are archives taken at the commit's own time. For each sibling this is the latest
  commit on or before the api commit's committer date. The siblings are core-obsm, utils-obsm,
  copilot-mro-obsm, flynapse-otel and shift-optimizer. `core` / `utils` / `copilot-mro` are
  relative symlinks to the `-obsm` copies. `ws-<sha>/SIBLINGS.txt` records the SHAs.
- Recipe: `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`, with
  `PYTHONPATH` pinned to the archives and a fresh `PYTHONPYCACHEPREFIX` for every run. The command
  is `/home/aditya/Code/api/.venv/bin/python -m pytest <lane> -o addopts="-ra --strict-markers" -p
  no:cacheprovider`, and pytest's own exit status is read.
- The rootdir was always `ws-<sha>/api-obsm`. `flynapse_api`, `core`, `utils`, `flynapse_otel` and
  `shift_optimizer` resolved to the archives (`logs/<sha>/modules.txt`). `copilot_mro` is a
  namespace package whose first portion is the archive.
- Real git layout: the checkout-pin session tests skip in an archive. They were run separately in
  a shared-clone mirror with real worktrees at `6ae9701`, where `tests/unit/infra` gave 183 passed
  and 1 skipped.

**Network (read this first).** At `73f2aa3` the conftest states, and this review measured, that
every api test session BEFORE `73f2aa3` fetched the pool's JWKS from Cognito LIVE at import. The
brief's `ENV_FILE` names the real pool. So this reviewer's own first pass made live, unauthenticated
GETs to that public JWKS document. That pass covered the 9 commits from `517f655` to `6ae9701`, the
mutation runs, the collect runs and the mirror.

- **Evidence.** The old `test_jwks.py` file sink recorded 3 "Successfully fetched" lines per unit
  lane in each scratch `logs/test_jwks.log`.
- **Estimated count.** Roughly 80 to 110 GETs.
- **When it stopped.** On finding this, every later run went through a `sitecustomize` network
  guard (`scratchpad/api-review-r6/netguard/`). It REFUSES and RECORDS every non-loopback DNS
  lookup or connect, and children inherit it through `PYTHONPATH`.
- **Other calls.** No AWS API call and no DB call outside pytest were made. The DB was touched only
  by the suite's own tests and the one round-trip test the brief named.

### Lane results (exit 0 everywhere; unit / smoke / startup / api / middleware)

| commit | unit | smoke | startup | api | middleware | integration collect | otel fake-store |
|---|---|---|---|---|---|---|---|
| `517f655` | 868 + 16s | 21 + 3s | 69 | 16 | 307 | 371 | 8 |
| `4defb75` | 871 | 21 + 3s | 69 | 16 | 307 | 371 | 8 |
| `ce53ecd` | 879 | ″ | ″ | 16 | 307 | 371 | 8 |
| `0f4d58b` | 881 | ″ | ″ | 16 | 307 | 371 | 8 |
| `e3c7b69` | 881 | ″ | ″ | 16 | 307 | 371 | 8 |
| `8d7e39f` | 884 | ″ | ″ | 16 | 307 | 371 | 8 |
| `d474a90` | 884 | ″ | ″ | 16 | 307 | 371 | 8 |
| `2b2a731` | 884 | ″ | ″ | 16 | 307 | 371 | 8 |
| `6ae9701` | 880 | ″ | ″ | 16 | 307 | 376 | 12 |
| `8d7f587` | 880 | ″ | ″ | 16 | 310 | 376 | 35 (all otel, not postgres) |
| `35639cb` | 880 | ″ | ″ | 25 | 310 | 376 | 35 |
| `c2c99be` | 885 | ″ | ″ | 25 | 310 | 376 | 35 |
| `73f2aa3` | 887 | ″ | ″ | 25 | 310 | 376 | 35 |

- **Deltas.** Every delta equals the tests the commit adds or removes. At `6ae9701`, 7
  carried_traceparent cases go and 3 guard tests arrive.
- **`8d7f587`.** It was committed through a pipe that tested `tail`'s exit status, not pytest's.
  It is **green at its own HEAD** on all five lanes.
- **The round trip.** `tests/integration/otel/test_one_shot_traceparent_round_trip.py` at
  `6ae9701` gives 1 failed. The failure is solely `psycopg2.errors.UndefinedColumn: column
  "traceparent" of relation "automation_runs"` at the enqueue INSERT.
- **Its skip condition.** Without `POSTGRES_DB` the conftest refuses the session outright
  (`ProtectedDatabaseError`). So the module-level skip is reached only when Postgres itself cannot
  be reached, as the claim says.

### Where each test path tries to go (netguard replay, all five lanes + collect + otel)

| commit | Cognito JWKS (refused) | IMDS 169.254.169.254:80 (refused) | anything else |
|---|---|---|---|
| `6ae9701`, `8d7f587`, `35639cb` | 8 (unit 5, startup 1, api 1, middleware 1) | 8 (smoke) | none |
| `c2c99be` | 5 (unit 2, startup 1, api 1, middleware 1) | 8 (smoke) | none |
| `73f2aa3` | **0** | 8 (smoke) | none |

---

## Findings, ranked

### No P0, no P1, no P2

Nothing that ships a content leak by default, nothing that breaks a guard's core property, and every
commit is green at its own HEAD. Every item below is P3. The verdict is **MERGE-CLEAN**.

### P3-1: Rule B's call allowlist matches a NAME, so an alias called `_row_to_tenant` passes the real accessor test

**Where.** `test_paged_registry_reads_state_their_limit.py:155,593`.

**What passes.** The following was planted in the snapshot's real `TenantService.get_tenant`:

- `_row_to_tenant = postgres.fetch_all`
- `return _row_to_tenant(f"SELECT {_TENANT_COLUMNS} FROM tenants")`

`test_every_allowlisted_accessor_is_real_and_its_reason_is_true` then passes (B5), although
`get_tenant` now returns every tenant. An import alias (`from … import list_all_tenants as
_row_to_tenant`) passes too.

**Why it matters.** This defeats the stated purpose of P3-2, which was to refuse an alias of
`fetch_all`.

**Fix.** Allow `_row_to_tenant` only when it resolves to the module-level def. That means refusing
any local binding or import alias of an allowlisted name.

### P3-2: `_AGGREGATE` misses PostgreSQL 16's strict and SQL/JSON aggregates

**Where.** `test_paged_registry_reads_state_their_limit.py:144`. The regex predates the range.

**What passes.** Each of these gets basis `LIMIT 1`:

- `jsonb_agg_strict(t)`, `json_agg_strict`
- `JSON_ARRAYAGG(...)`, `JSON_OBJECTAGG(...)`

With `LIMIT 1` added, each passes. A duplicate `get_tenant_by_name` returning `jsonb_agg_strict`
over every tenant passes the real accessor test (B6). The `json_agg` control fails it (B6c).

### P3-3: A quote character inside a `--` comment opens a quoted span, which hides `tenants`

**Where.** `_strip_sql_comments` at `test_paged_registry_reads_state_their_limit.py:384-406`.

**Mechanism.** Quotes are read first. So in `FROM operators o -- each operator's rows, filtered on
status\n, tenants t WHERE t.status = 'active'`, the apostrophe starts a span that runs to the
literal's opening quote. The comment's "on" then ends the FROM list, and `_registry_sql` returns
`[]`. PostgreSQL itself reads `tenants`.

**Variants.**

- The same happens with a double-quoted word in the comment. Both variants predate the range.
- **`2b2a731` adds a new variant.** A `$x$` inside a comment with a later `$x$` literal is detected
  (`[1]`) at `d474a90` and missed (`[]`) at `2b2a731`.
- This is the mirror of P3-3: a quote marker inside a comment, where P3-3 was a comment marker
  inside a quote.

**Fix.** One left-to-right lexer that knows which of comment, literal or dollar body it is in,
instead of the "quotes first" pass.

### P3-4: The uvicorn launch sweep sees two spellings only

**Where.** `test_uvicorn_leaves_logging_to_utils.py:152`.

**Decoys.** Each of these was planted in a new file and left the equality pin green (the control
was caught):

- options before the app: `uvicorn --host … flynapse_api.main:app`;
- a quoted app: `uvicorn "flynapse_api.main:app"`;
- `from uvicorn import run; run(...)`;
- `uvicorn.Server(uvicorn.Config(...)).run()`;
- `python -m uvicorn --app-dir flynapse_api main:app`.

Each applies uvicorn's default `LOGGING_CONFIG`. No such launch exists today.

**Also outside the sweep.**

- Dot-directories are out of scope by design.
- Other repos' launch recipes are out of scope: copilot-mro `.claude/skills/debug-rag/REFERENCE.md:513,671`
  and core `tests/e2e/documents/live_pdf_endpoints.py:215` start the api without `--log-config`
  (dev only).

### P3-5: The relative `--log-config` path couples boot to WORKDIR and to the installed wheel, and the guard sees neither

**Where.** `Dockerfile:57,122` and the test at `:105,221`.

**What the guard checks.** It resolves the path from the repo root and checks `pyproject` for an
`exclude`. It was measured that `poetry build` ships the JSON.

**Failures it does not see.** The CLI's `--log-config` is `click.Path(exists=True)`, so a missing
file stops uvicorn before the app loads.

- A final stage with `WORKDIR /srv` (decoy) passes all 22 tests in the two image test files. The
  container would then exit 2 at boot.
- So does an unpinned build (`API_VERSION` empty, which the Dockerfile supports). That installs
  "latest" from CodeArtifact, and every wheel published before `ce53ecd` lacks the file.
- The deploy workflow pins the version, so the production path is safe.

### P3-6: The pool id reaches the log pipe at `LOG_LEVEL=DEBUG`, through urllib3's request line

**Measured.** Through utils' real JSON stdout sink, with a loopback server standing in for Cognito,
the line appears as `urllib3.connectionpool … "GET /ap-south-1_PoolSentinel9/.well-known/jwks.json
HTTP/1.1" 200`. `withhold_url_secrets` does not reduce a path. Nothing appears at INFO.

**What already knows about it.** The implementer recorded it at `73f2aa3` (plan §3), and the fix
belongs to utils' `intercept`.

**Separately, the JWKS pin (`test_api_cognito_spans.py:270`) is order-dependent for stdlib
records.** A decoy was planted: `logging.getLogger(__name__).warning("jwks target %s", jwks_url)`.

- It PASSES the three pin cases when they run alone (`-k jwks_fetch_logs`).
- It fails them in the file and in the lane, because by then an earlier test has installed the
  intercept.

### P3-7: The consumer requires a core carrying `OneShotRun.traceparent`, and an older core stops every one-shot dispatch

**Where.** `loop.py:2646`.

**Measured.** `6ae9701` was run against core `3513dfa`. The dispatch ends `errored=True` with
`AttributeError` at `traceparent=run.traceparent`, AFTER the take. So the row is claimed and never
run, until recovery re-queues it and the same thing happens again.

**Why it is only P3.** Deploy order is ruled (core, then api).

**Why it still matters.**

- This conflicts with the module's own doctrine: "a malformed carrier costs the link, never the
  dispatch".
- Once api's `core` dependency returns to CodeArtifact, nothing enforces a version floor.

**Fix.** `getattr(run, "traceparent", None)`, or a `core` version floor.

### P3-8: The import-time sink guard sees `logger.add` / `logger.configure` spelled literally only

**Where.** `test_no_import_time_log_sinks.py:39,50`.

**Decoys.** Each passes the guard (the control was caught):

- `from loguru import logger as log; log.add(...)`;
- a helper that adds a sink, called at module level;
- a sink added in a default argument;
- `add = logger.add; add(...)`;
- a stdlib `logging.basicConfig(filename=...)`.

The first two are natural shapes.

### P3-9: One smoke test still reaches toward AWS, through the IMDS credential probe

**Where.** `tests/smoke/automations/test_executor_real_adapter.py:165`.

**What happens.** The test builds copilot-mro's real pipeline. That constructs langchain_aws
`ChatBedrockConverse`, and boto's credential chain then tries 169.254.169.254:80. This happens 8
times per smoke run, at every commit including `73f2aa3`.

**Scope.** No Bedrock API call is made, because construction only. It predates the range. It is the
only non-loopback network path left in the five lanes.

### P3-10: Documentation drift

1. **The ruling row is out of date.** The §4a-bis M-JOB-TRACEPARENT consequence still reads "api's
   producer writes it and `carried_traceparent` reads it". What happened is that core's enqueue
   writes it and api deleted `carried_traceparent`. G.68 is updated, but the ruling row carries no
   controller-call note.
2. **A core test comment is stale.** core `tests/unit/observability/test_core_spans_withhold_exception_text.py:1041`
   still says the key is "Declared and READ in api".
3. **"Beside utils' sinks" overstates the pre-change hazard.** It appears at `README.md:56-58` and
   `Dockerfile:119-121`. Measured: in the normal order, utils' intercept REPLACES uvicorn's handlers,
   and a `?token=` access line is withheld even under the default config. The raw token prints only
   when uvicorn's config is RE-APPLIED after `setup_logging`. That is the case the change closes;
   with the JSON config re-applied, the line stays withheld.
4. **`_definition` does not check `co_filename`.** A function reassigned onto `TenantService` from
   another file, whose name and first line coincide with a def in `tenant_service.py`, would be
   read as that def. This is contrived and was not planted.

### Process note (not against the range)

Replaying any api commit before `73f2aa3` with the standard lane recipe makes live Cognito calls.
Every brief that reviews older api commits should add `COGNITO_USER_POOL_ID=` or a network guard.

---

## What I tried to break and could not

- **uvicorn access lines.**
  - With the JSON config, then `setup_logging`, a `uvicorn.access` record carrying
    `/invitations/preview?token=SECRET` printed `preview?:redacted`.
  - The same held with the JSON config re-applied after `setup_logging`.
  - Only uvicorn's DEFAULT config, re-applied, printed the raw token.
  - The incremental dictConfig configures nothing, closes nothing, and leaves no handler on any of
    the four uvicorn loggers.
- **Launch paths.** None were missed in api, compose, the poc docker-compose (`copilot-mro-obsm
  deployment/poc/docker-compose.yml:223`, which uses the image CMD) or iac (App Runner has no
  `start_command`). No gunicorn, no Procfile.
- **JWKS.**
  - No pool id in any exception text: `failure_fields` holds the type and frames only. The
    transport-failure case carries the pool id in its message, and the pin proves it is not
    written.
  - No pool id in a span attribute: `server.address` is the host.
  - No WARNING-level urllib3 retry line: requests' default adapter has `max_retries=0`.
  - The live `requests` transport span keeps `url.full`, which flynapse-otel reduces on export.
    This was documented earlier in G.48.
- **`LOGURU_DIAGNOSE`.**
  - An `ARG` substitution (`ENV LOGURU_DIAGNOSE=${DIAG}`) makes loguru raise, and the test fails.
  - An `exec env LOGURU_DIAGNOSE=YES uvicorn` CMD fails three exec-target pins.
  - The build uses the last stage with no `target:`, which is the stage the test reads.
- **`_root.py` P3-1.**
  - The live-layout diff of the old (`29a0841a`) against the new (`3d192468`) resolver covered 42
    callers (21 checkouts × 2 positions) × 26 names × {`sibling_family`, `sibling_choice`,
    `expect`}. That is 2352 answers, and **0 changed**, which confirms the "42 × 21, 0 changed"
    claim.
  - utils-obsm, core-obsm and copilot-mro-obsm HEAD all hold md5 `3d192468`.
- **Traceparent.**
  - None, garbage and all-zero ids each start a fresh root and the run completes.
  - A `__traceparent__` key in params links nothing.
  - No production reader of the key, and no reader of `carried_traceparent`, remains anywhere in
    api, core, utils, copilot-mro, flynapse-otel, shift-optimizer or telegram-bot.
  - Core's reader validates W3C v00 and rejects zero ids.
  - The static guard can be defeated by rebinding `run` with a `%`-formatted key. The behaviour
    tests catch that (2 failed).
- **Invitation preview.** Core has no single-segment `POST /invitations/{id}` route that could
  shadow `/preview`: `revoke` and `resend` sit under `/{id}/…`. `HEAD` is neither skipped nor a
  door.
- **Permissions endpoint.**
  - It is not in any skip list.
  - With no token it returns 401 before the route. A skip-listed mutant is caught.
  - The tenant comes from verified claims, and a membership row authorises it. So another tenant
    cannot read it, and it exposes no more than the existing header does.
  - The body equals the header by construction. The one divergence path is `json.dumps` failing
    on a non-JSON value, which drops the header only. The real fields are JSON-native:
    `joined_at` is TEXT and capabilities are sorted lists.
  - It carries `no-store`, and every other `Cache-Control` in the mounted apps is `private` or
    `no-store`.

## What I did not test

- Anything needing a Docker image build or an image run.
- The App Runner or compose runtime environment. A runtime `LOGURU_DIAGNOSE` override (decoy LD3)
  is outside the image guard's scope.
- Postgres-marked integration lanes other than the round trip. After the migration, the round trip
  cannot be run here because of the DDL ban.
- Sockets opened from C code: libpq and grpc. The netguard sees Python sockets only.
- The e2e scripts.
- The implementer's "buckets split by method" mutant. I proved GET-only (I3) instead.
- The per-tree counts in `e3c7b69`'s carry spec. They were superseded when the carries landed.
- The dashboard's adoption of `/auth/permissions`.

---

## Claims table

- **Severity** (this review's own scale): 0 = a content leak that ships, 1 = guard or lock
  integrity, 2 = a coverage gap, 3 = docs or process, — = no finding.
- **Tier** (§2.3a): 0 = settled by a guard I saw fail, 1 = consequential but reversible, 2 =
  irreversible or estate-shaping.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r6-01 | api | `flynapse_api/auth/jwks.py:48` | The fetch's INFO line binds `host=` only | The URL path is the pool id | Pin serialises each loguru record on success, transport failure and no keys | `tests/unit/telemetry/test_api_cognito_spans.py:270` | yes: J1 old line 3 red; J2 `path=` field 3 red | — | 0 | F1 | SETTLED |
| r6-02 | api | `jwks.py` → urllib3 `connectionpool` | none (recorded at `73f2aa3` §3, fix left to utils) | the line is the library's | loopback probe through utils' JSON stdout sink at `LOG_LEVEL=DEBUG`: path with the pool id printed; INFO: nothing | none (pin stubs the transport) | n/a | 2 (DEBUG only) | 1 | F1 | OPEN, P3-6 |
| r6-03 | api | `test_api_cognito_spans.py:270` | Pin claims "every record the fetch writes" | cover stdlib too | stdlib-logger decoy passes alone (`-k`), fails in file and lane | same | yes: J1/J2 red; decoy shows order dependence | 1 | 1 | F1 | PARTIAL, P3-6 |
| r6-04 | api | `Dockerfile:122`, `Dockerfile.local:103`, `README.md:52-53`, `flynapse_api/run.py:44` | Every launch: incremental no-op `--log-config`, or `log_config=None` | uvicorn's `LOGGING_CONFIG` handler prints full tracebacks and the raw access line when re-applied | child-interpreter Config probe; access-line probe (above) | `tests/unit/infra/test_uvicorn_leaves_logging_to_utils.py` | yes: U1 to U5, GU-probe-blind, GU-sweep-blind all red | — | 0 | F1 | SETTLED |
| r6-05 | api | `test_uvicorn_leaves_logging_to_utils.py:152` | Launch sweep pinned by equality | a new launch is judged | control caught; 5 real launch shapes missed | same | yes (GU-sweep-blind red); decoys U1 to U5 green | 1 | 1 | F1 | PARTIAL, P3-4 |
| r6-06 | api | `Dockerfile:57,122`; test `:105,:221` | Relative config path, shipped in the wheel | the CLI cannot say `None` | `poetry build` lists `flynapse_api/uvicorn_log_config.json` (measured) | `test_the_configuration_ships_in_the_wheel_the_image_installs` | WORKDIR `/srv` decoy passes 22 tests; the unpinned-wheel path is unguarded | 2 | 1 | F3 | PARTIAL, P3-5 |
| r6-07 | api | `Dockerfile:88`, `Dockerfile.local:76` | Final stage sets `LOGURU_DIAGNOSE=NO` once | loguru reads it at first import, default on | behaviour probe plus control; last stage is the built stage | `test_image_version_plumbing_api.py:360` | yes: L1 YES, L2 removed, GL-probe-blind, LD1 ARG, LD2 CMD env (3 other pins) all red | — | 0 | F1 | SETTLED (image scope; runtime overrides outside it) |
| r6-08 | api | `tests/_root.py:276-290`, `tests/_checkout_pin.py:165-170` | A markerless, git-less dir is no repository; rule 2 falls back to the chosen checkout's git primary | an empty `core-notes` silenced rule 2 | 2352-answer live diff, 0 changed; carriers md5 `3d192468`; mirror infra 183 + 1s | `test_root_anchoring.py::…only_with_git_or_the_marker`, `test_checkout_variant_pin.py::…[core-analytics]` | yes: R1, R2 red | — | 0 | F3 | SETTLED |
| r6-09 | api | `test_paged_registry_reads_state_their_limit.py:535` | Read the def Python runs (name plus first line) | a duplicate def read the first | real-accessor duplicate with `json_agg` fails (B6c) | posed dup + real accessor test | yes: B1 red | 3 (no `co_filename`) | 0 | F3 | SETTLED |
| r6-10 | api | `…:155`, `…:593` | Refuse every call but `fetch_one` and `_row_to_tenant` | aliases, helpers and `map` were unbounded | real `get_tenant` rebinding `_row_to_tenant = postgres.fetch_all` passes (B5) | `test_every_allowlisted_accessor_is_real_and_its_reason_is_true` | B3 red; B5 decoy green | 1 | 1 | F3 | PARTIAL, P3-1 |
| r6-11 | api | `…:144` | `_AGGREGATE` denylist | one row holding every tenant | `jsonb_agg_strict`, `json_agg_strict`, `JSON_ARRAYAGG`, `JSON_OBJECTAGG` pass (B6 on real accessor) | same | control red; decoys green | 1 | 1 | F3 | OPEN, P3-2 |
| r6-12 | api | `…:384-406` | Dollar-quoted spans (P3-3) | `$$--$$` swallowed a FROM | self-test gains 3 snippets | `test_the_detectors_flag_the_shapes_they_claim_to_flag` | B4 red; a quote in a comment hides `tenants` (`'`, `"`, and `$x$`, the last NEW at `2b2a731`) | 1 | 1 | F3 | PARTIAL, P3-3 |
| r6-13 | api | `flynapse_api/automations/loop.py:2646`, `telemetry/queue_telemetry.py` | Consumer links through `run.traceparent`; params carrier retired | M-JOB-TRACEPARENT | None, garbage, all-zero and params cases; estate grep clean | `test_producer_context_rides_the_column.py`, `test_one_shot_queue_signals.py` | yes: T1 `None`, T2 params, T3 no link, GT sweep-blind all red | — | 0 | F3 | SETTLED |
| r6-14 | api | `loop.py:2646` | Hard read of `run.traceparent` | core `7c506e6` added it | against core `3513dfa`: `errored=True`, AttributeError after the take | none | n/a | 2 | 1 | F3 | OPEN, P3-7 |
| r6-15 | api | `tests/integration/otel/test_one_shot_traceparent_round_trip.py` | Red until the column migration; skip only if unreachable | the column is the owner's DDL | 1 failed, UndefinedColumn only; the conftest refuses when `POSTGRES_DB` is unset | itself | not mutable without DDL | — | 1 | F3 | ASSERTED |
| r6-16 | docs | plan §4a-bis M-JOB-TRACEPARENT; core `test_core_spans_withhold_exception_text.py:1041` | Ruling text vs implementation | — | the ruling row still names `carried_traceparent`; the core comment says api reads it | none | n/a | 3 | 1 | F3 | OPEN, P3-10 |
| r6-17 | api | `middleware/auth.py:754-758`, `middleware/rate_limit.py:307` | Preview POST+GET skipped on the EXACT path; one door bucket | M-INVITE-FRAGMENT; one oracle | no shadowing core route; HEAD not exempt | `test_skip_path_matching.py`, `test_rate_limit.py` | yes: I1 any-method, I2 prefix, I3 GET-only all red | — | 0 | F1 | SETTLED |
| r6-18 | api | `routers/auth.py:49-67`, `middleware/auth.py:1342` | `GET /auth/permissions`, body = `permission_payload(ctx)` = header; `no-store`; 401 before the route | B11 | real fields JSON-native; tenant from verified claims | `tests/api/permissions/test_permissions_endpoint.py` | yes: P1 second derivation, P2 no-store dropped, P3 route skipped, P4 sanitise off all red | — | 0 | F1 | SETTLED |
| r6-19 | api | `main.py:556` | `/test-cookie` deprecated; constant, credential-free log | one release, then delete | pinned line, no token or cookie in records | `test_each_test_cookie_use_logs_a_constant_line_with_no_credential` | not run by me | — | 1 | F1 | ASSERTED |
| r6-20 | api | `tests/unit/auth/test_jwks.py`, `tests/unit/infra/test_no_import_time_log_sinks.py:39,50` | No import-time sink; hermetic JWKS tests | the old file wrote the pool URL to disk, fetched live and asserted nothing | 4 hermetic tests | both files | yes: J3 all-keys, G-sink descends into functions both red; decoys S1 to S5 green | 1 | 1 | F3 | PARTIAL, P3-8 |
| r6-21 | api | `tests/conftest.py:75` | Force `COGNITO_USER_POOL_ID=""` | every session fetched JWKS live | netguard: Cognito 8/8/8/5 → 0 at `73f2aa3` | `tests/unit/infra/test_suite_never_reaches_cognito.py` | yes: C1 red (and netguard recorded a refused `cognito-idp` attempt) | — | 0 | F3 | SETTLED |
| r6-22 | api | `tests/smoke/automations/test_executor_real_adapter.py:165` | none (predates the range) | — | 8 IMDS probes per smoke run at every commit | none | n/a | 2 | 1 | F3 | OPEN, P3-9 |
| r6-23 | api | `README.md:56-58`, `Dockerfile:119-121` | "beside utils' sinks" | — | default-config probe withholds; only re-application leaks | none | n/a | 3 | 1 | F3 | OPEN, P3-10 |
| r6-24 | copilot-mro, core | `debug-rag/REFERENCE.md:513,671`; core `live_pdf_endpoints.py:215` | Dev launch recipes without `--log-config` | outside api's sweep | read | none | n/a | 3 | 1 | F3 | OPEN, P3-4 |
| r6-25 | api | `docs/plans/g53-checkout-pin-by-git-family.md` (`e3c7b69`) | Carry-spec corrections P2-1/P3-4/P3-5 | round-5 re-check | carriers landed at md5 `3d192468`; per-tree counts not re-measured | none | n/a | 3 | 1 | F3 | ASSERTED |

## Open claims, tier 2 first

**Tier 2:** none. The only estate-shaping surfaces in the range are two. The auth skip list (r6-17)
and the permissions read API (r6-18) are both mutation-SETTLED. The traceparent carrier (r6-13) is
SETTLED on the consumer side, and its schema half belongs to core.

**Tier 1, OPEN or PARTIAL, in the order to fix:**

1. **r6-10, r6-11, r6-12 (Rule B).** Replace the name allowlist with a resolution check. Add the
   strict and SQL/JSON aggregates. Lex SQL in one pass.
2. **r6-14.** Make the consumer tolerant of a core without the field, or pin a core floor.
3. **r6-05, r6-06.** Widen the launch sweep, or pin an absolute config path the image itself
   writes. Assert the final stage's WORKDIR.
4. **r6-02, r6-03.** Floor `urllib3.connectionpool` in utils' intercept. Install the intercept in
   the JWKS pin itself, so it does not depend on test order.
5. **r6-20.** Resolve logger aliases, and descend into module-level calls of local helpers.
6. **r6-22.** Stub the Bedrock client construction in the smoke test, or set `AWS_EC2_METADATA_DISABLED=true`
   in the conftest.
7. **r6-16, r6-23, r6-24, r6-25.** Documentation.
