# Claims packet: api review r7 (`73f2aa3..847c34c`, 10 commits, the r6 P3 batch)

This is an independent adversarial review (Opus), done on 2026-09-21. No code tree was changed. Every run
used a `git archive` copy in the reviewer's private scratch (`scratchpad/api-review-r7/`). Each mutation
was applied to a scratch copy, confirmed with grep, run, reversed, and md5-checked against the HEAD
blob. Every restore matched: api `847c34c`, core `dc41caa`.

| repo | worktree | branch | range | HEAD at review | tree state |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `73f2aa3..847c34c` | `847c34c` | clean before and after |

**Verdict: FIX-FIRST.** No P0. **1 P1:** the new network guard's enforcement half is held by no test.
**3 P2:** gaps in what the network guard covers. **9 P3.** No content leak ships. Every finding is about
what the test suite can prove.

## How it was run

- **Workspaces.** Each of the 10 commits was extracted into its own `ws-<sha>/api-obsm`. The siblings
  are the archives the brief named, the same for every commit: core-obsm `dc41caa`, utils-obsm
  `8572635`, copilot-mro-obsm `1c9144ac`, flynapse-otel `f2c1214` and shift-optimizer `8bd4d66`
  (the last three are the latest on or before `847c34c`'s commit time).
- **Recipe.** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`, with
  `PYTHONPATH` pinned to the archives and a fresh `PYTHONPYCACHEPREFIX` per run. The command was
  `/home/aditya/Code/api/.venv/bin/python -m pytest <lane> -o addopts="-ra --strict-markers" -p no:cacheprovider`.
  pytest's own exit status was read.
- **Where the code came from.** At HEAD, `flynapse_api.__file__` was
  `…/api-review-r7/ws-head/api-obsm/flynapse_api/__init__.py`, and core, utils, flynapse_otel and
  shift_optimizer came from the archives. The rootdir was always `ws-<sha>/api-obsm`.
- **Network.** No network call was made.
  - **Every run** sat behind the reviewer's `sitecustomize` guard, which children inherit through
    `PYTHONPATH`. It is stricter than api's: it allows loopback only, allows a single-label name only if
    `/etc/hosts` names it, and also wraps `sendto`, `sendmsg`, `gethostbyname*`, `gethostbyaddr` and
    `getnameinfo`. The environment also blanked `COGNITO_USER_POOL_ID` and set
    `AWS_EC2_METADATA_DISABLED=true`.
  - **Every network plant** also ran inside `unshare -rn`, a namespace with only a loopback
    interface. A C-level socket that escaped both guards therefore got `ENETUNREACH` from the kernel
    and never a route.
- **Real git.** A shared-clone mirror with real worktrees at HEAD (`mirror/`) ran `tests/unit/infra`
  with its 16 archive-skipped git tests live: **196 passed, 1 skipped**, exit 0, rootdir
  `mirror/api-obsm`. The nested pytest sessions load the new conftest without trouble.

### Lane results: exit 0 on every lane at every commit

| commit | unit | infra | automations | smoke | startup | api | middleware | otel `not postgres` | integ collect |
|---|---|---|---|---|---|---|---|---|---|
| `c7d32c7` | 887 + 16s | 172 + 16s | 296 | 21 + 3s | 69 | 25 | 310 | 35 | 376 |
| `de3198b` | 887 | 172 | 296 | ″ | ″ | ″ | ″ | 35 | 376 |
| `7894dcc` | 887 | 172 | 296 | ″ | ″ | ″ | ″ | 35 | 376 |
| `2d3ba94` | 888 | 173 | 296 | ″ | ″ | ″ | ″ | 35 | 376 |
| `1247c27` | 890 | 175 | 296 | ″ | ″ | ″ | ″ | 35 | 376 |
| `c6c82af` | 890 | 175 | 296 | ″ | ″ | ″ | ″ | 35 | 376 |
| `3ed8434` | 890 | 175 | 296 | ″ | ″ | ″ | ″ | **36** | **377** |
| `309c0d6` | 890 | 175 | 296 | ″ | ″ | ″ | ″ | 36 | 377 |
| `ef897f8` | **896** | **181** | 296 | ″ | ″ | ″ | ″ | 36 | 377 |
| `847c34c` | 896 | 181 | 296 | ″ | ″ | ″ | ″ | 36 | 377 |

- **Deltas.** Every delta equals the tests the commit adds.
- **Implementer's count.** 896 passed + 16 skipped = the implementer's "unit 912": the 16 run in a real
  checkout.
- **Network.** The reviewer's stricter guard recorded **0** attempts across all 90 lane runs,
  children included. So today's suite needs none of api's private-address allowance.

---

## Findings, ranked

### No P0

Nothing in the range ships content. The one production change is `loop.py:2648` (`getattr`), and it is
correct and mutation-proved.

### P1-1: The network guard's enforcement half is held by no test, and its test file says otherwise

The guard has two halves:
- **Refuse:** `tests/_netguard.py`.
- **Fail the test whose refusal a library swallowed:** `tests/conftest.py:310` (`_no_network`) and
  `:354` (the `pytest_sessionfinish` stray check).

The second half is why this guard exists: botocore swallowed all eight IMDS refusals. Yet no test holds
it. `tests/unit/infra/test_network_guard.py:3-6` says those tests pin "that a refusal a library swallowed
still fails the test that made it". None does: the `recorders` fixture deletes its own refusals
(`:48`) before `_no_network` reads them.

| mutation | result |
|---|---|
| MP9c: `if False and refused and not opted_in` (conftest `:310`) | guard file + Cognito pin **8 passed** |
| MP9d: `stray = []` (conftest `:354`) | **8 passed** |
| MP9e + MP9c: the IMDS disable removed as well | the smoke test passes with 8 refused, swallowed IMDS lookups. Only `test_this_session_runs_behind_the_guard` fails, and only because it asserts the env var. |
| MP9e alone (control) | smoke **ERROR**, "lookup 169.254.169.254:80" ×8. This confirms the implementer's one-off proof. |

**Scenario.** A later edit simplifies `_no_network` (say, a refactor to `request.addfinalizer` that
drops the check). The whole suite stays green. The next library that swallows a refusal, as botocore
did, degrades a test silently. The one-time proof in the plan is the only evidence that the mechanism
works.

**Fix.** Add a `pytester` test, or a nested-pytest subprocess like `test_checkout_variant_pin.py:609`
already uses. It should plant three swallowed refusals and assert that the inner session exits 1: one
in a test body, one in a module-scoped fixture (which also needs P2-1), and one at collection.

### P2-1: A refusal in a module-, class- or session-scoped fixture fails nothing, and the session exits 0

`_no_network` is function-scoped (`conftest.py:296`). It takes its mark after every higher-scoped
fixture has been set up, and checks before those fixtures are torn down. `pytest_sessionfinish` counts
only entries whose test id is `None` (`:354`). A fixture refusal carries `"… (setup)"` or
`"… (teardown)"`, so neither check sees it.

Plant N1 was a module-scoped fixture that swallows a refused lookup in setup and in teardown:
- `REFUSED` holds the entry, with test id `…test_n1… (setup)`;
- the test **passes**, and the session **exits 0** (`-k "n1_ or n14"`: 3 passed).

**Scenario.** A session fixture builds a client whose credential chain probes a remote endpoint and
swallows the failure, exactly the botocore shape. Nothing fails. This refutes the claim "every refusal
is recorded, and a test that triggered one fails."

**Fix.** Fail on any refusal whose id is not the current test's `(call)`, or read `REFUSED` in
`pytest_runtest_logreport` for every phase.

### P2-2: Python-level egress the guard never checks, so "every name lookup … is checked BEFORE it leaves" does not hold

`tests/_netguard.py:91-103` wraps `getaddrinfo`, `socket.connect` and `connect_ex` only. Each of the
following passed api's guard. Each was then stopped by the reviewer's guard beneath it, or by the empty
network namespace (plants in `ws-p/api-obsm/tests/unit/infra/r7plant/test_r7_net_plants.py`).

| plant | what reached the next layer |
|---|---|
| N2: a child `python -c` (7 spawn sites in the unit lanes) | the child's `getaddrinfo('r7-child.example.invalid')`, with no api guard in the child |
| N3: UDP `sendto(b"r7", ("8.8.8.8", 9))` | the datagram send (`r7-sendto 8.8.8.8`) |
| N4: `socket.gethostbyname("….example.invalid")` | the resolver. The docstring's "no DNS query leaves" is false. |
| N16: `getaddrinfo("r7plantsinglelabel", 80)` | the system resolver (`nameserver 10.255.255.254`, the WSL DNS proxy) |
| N7 uvloop, N8 `_socket.socket`, N11 libpq (numeric **and** a dotted name libpq resolved itself), N12 grpc | the kernel: `OSError(101, 'Network is unreachable')` or libpq's "could not translate host name". Nothing was recorded. |

- **What the guard discloses.** Its docstring (`_netguard.py:23-24`) covers C extensions, but then
  asserts "Those reach only the local services above". That rests only on today's `.env`; no test holds
  it.
- **Children.** They are not mentioned at all, though the commit says "every test session refuses the
  network".

**Fix.**
- Export the guard to children: a `sitecustomize` directory prepended to `os.environ["PYTHONPATH"]`
  in the conftest. Children append refusals to a file that `_no_network` reads.
- Wrap `sendto`, `sendmsg`, `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr` and `getnameinfo`.
- Refuse single-label names that `/etc/hosts` does not name.

### P2-3: The "private, non-link-local" allowance admits AWS's IPv6 metadata service and any LAN/VPC host

`_allowed_address` (`_netguard.py:44-51`) is `is_loopback or (is_private and not is_link_local)`. In
this Python (3.11.15), the rule allows:
- **`fd00:ec2::254`**, the EC2 IMDS IPv6 endpoint, and `fd00:ec2::23`, the EKS Pod Identity agent;
- any RFC1918 host, and 198.18/15, 6to4 `2002::/16`, Teredo and `64:ff9b:1::/48`.

N5 showed both `getaddrinfo("fd00:ec2::254")` and `connect(("fd00:ec2::254", 80, 0, 0))` passing api's
guard. The IPv4 metadata service, `::ffff:169.254.169.254` and `8.8.8.8` are refused (controls).

**Scenario.** On an IPv6-IMDS instance (a CodeBuild or EC2 runner), any non-boto client or a future
`AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE=IPv6` reaches the metadata service, which is the exact leak
class this guard was built for. A shared dev RDS or ElastiCache reached by IP over VPN or VPC is also
allowed. The allowance is unused here: 0 records under a loopback-only guard across every lane of every
commit.

**Fix.** Allow loopback only, plus an explicit opt-in list read from the environment (for example, a
compose network's CIDR).

### P3-1: Rule B's helper resolution is still by name for attribute calls, and the helper is read one level deep

`_callee` returns an attribute's tail (`test_paged_registry…:264-271`). `_helper_refusal` then resolves
that name through the accessor's `__globals__` (`:699`). Planted into core `dc41caa`'s real accessors,
each of these **passes** `test_every_allowlisted_accessor_is_real_and_its_reason_is_true`:

| plant | why it passes | at runtime |
|---|---|---|
| RB1: `get_tenant` returns `TenantService._row_to_tenant(row)` | the class staticmethod that `fetch_all`s every tenant is checked against the module-level `_row_to_tenant` | the listing runs |
| RB2: the module `_row_to_tenant` returns `_everyone()`, which `fetch_all`s | the body check looks only for direct `fetch*` calls | the listing runs |
| RB3: `match postgres.fetch_all: case _row_to_tenant: pass`, then the call | `_local_bindings` does not see an `ast.MatchAs` capture | `_row_to_tenant` is `fetch_all` |

Controls: an attribute call to `_listing` is refused, and MP1 (bindings ignored) and MP1b (identity
ignored) turn the posed-shape test red.

### P3-2: Rule B's one-row basis reads SQL quotes-first only, and the plain-select backstop reads only the outer list

- **The comment fix did not reach this check.** `_one_row_basis` strips comments with
  `_strip_sql_comments` alone (`:765`), so r6 P3-3's lexer never applies here.
- **Accepted by the real-accessor test on core** (plants, then an offline table of 16 shapes):

| plant | SQL | what PostgreSQL returns |
|---|---|---|
| RB5 | `… FROM tenants /* ' */ -- ' WHERE tenant_id = %s` | PostgreSQL sees no WHERE, so `get_tenant(x)` returns an arbitrary tenant |
| RB4 | `… WHERE tenant_id = %s -- by key\r OR true` | PostgreSQL ends a `--` comment at `\r`; both readings run to `\n` |
| RB6 | `… WHERE status IS NOT NULL UNION SELECT … WHERE tenant_id = %s` | every tenant, not the keyed one |
| RB7 | `SELECT s.* FROM (SELECT "json_agg"(t) …) s LIMIT 1` | one row holding every tenant: a quoted function name evades `_AGGREGATE` |
| RB8 | `SELECT s.* FROM table_to_xml('tenants', true, false, %s) s LIMIT 1` | one row holding every tenant. No quoting trick is needed. |
| table only | `query_to_xml(…)` in a FROM sub-select | same |
| table only | a recursive-CTE string fold inside a FROM sub-select | same |

Controls refused: an unquoted `json_agg` sub-select, `string_agg`, `ARRAY(SELECT…)`, a CTE-led
statement, `json_build_array` in the outer list, and `LIMIT 1` only inside a sub-query. MP2 (select
rule off) turns red.

### P3-3: The table detector's residuals (api-side Rule B)

Each of these, planted as a string in `flynapse_api/automations/announcements.py`, **passes**
`test_no_production_sql_reads_the_registry_table`:
- RA1: `SELECT table_to_xml('tenants', true, false, '')` (no FROM at all);
- RA2: `SELECT t.tenant_id FROM (tenants t JOIN operators o ON true)` (`_TABLE_ITEM` cannot start at
  `(`);
- RA3: `SELECT … -- the registry\rFROM tenants` (the lexer ends `--` at `\n` only, `:440`, as does
  `_COMMENT` at `:397`);
- RA4: `FROM U&"tenants"`.

RA3 is the one lexer infidelity found. The rest predate the range.

The r6 shapes and the brief's are flagged (tried and could not break): an apostrophe in a comment,
`psql --dbname app -c '…'`, a lateral sub-select, a `--` inside a dollar quote, and
`E'it\\' -- ' FROM tenants`. MP3a (quotes-first only) and MP3b (lexer only) are each red.

### P3-4: The uvicorn launch sweep misses 12 launch shapes (none exists in the estate today)

`_cli_launch_lines` / `_api_launches` (`test_uvicorn_leaves_logging_to_utils.py:211-263`), with
dot-directories skipped (`:276-283`). All 12 plants are missed; a `Procfile` control is found.

- **Shell and config:**
  - `gunicorn -k uvicorn.workers.UvicornWorker …`, whose worker sets `uvicorn.error` to
    `propagate=False` with gunicorn's handlers;
  - `hypercorn …`;
  - a compose `command:` YAML list;
  - `UVICORN_APP=flynapse_api.main:app uvicorn --port 8000`;
  - a Dockerfile with `ENV UVICORN_APP=…` and `CMD ["uvicorn","--port","8000"]`;
  - `.github/workflows/*.yml`.
- **Python:**
  - `uvicorn.main([...])`;
  - `from uvicorn.main import main; main([...])`;
  - `getattr(uvicorn, "run")(app)`;
  - `serve = uvicorn.run; serve(app)`;
  - `importlib.import_module("uvicorn").run(app)`;
  - `subprocess.run(["uvicorn", APP])` with the app in a variable.

The `UVICORN_APP` launch was run through the test's own `_CHILD` probe. It **applies `LOGGING_CONFIG`**
(`uvicorn`: StreamHandler, `propagate: False`).

Estate check: iac has no command override for api, and api's compose files and `.github` launch
nothing.

### P3-5: The image's log-config path: one decoy passes, the hardening is refused, and readability is inherited

- **D5.** `RUN rm -f /etc/flynapse-api/uvicorn_log_config.json` after the COPY passes all **11** image
  tests. A probe shows a missing file stops uvicorn with exit 2 ("Path … does not exist") before the app
  loads.
- **D4.** `COPY --chmod=0444 …` **fails 2 tests**. `_image_log_config` skips any COPY that starts with
  `--` (`:180`), so the one change that pins readability cannot land.
- **Readability.** The COPY carries the build context's mode into a root-owned file under
  `USER appuser` (`Dockerfile:72,103`; `Dockerfile.local:57,83`). A probe shows an unreadable file stops
  uvicorn with exit 2 ("is not readable"). A `umask 077` checkout makes the file 0600. The wheel path
  it replaced never depended on that.
- **Checked and correct.** The COPY is in the final stage of both images. Moving it to the builder is
  refused (D6). The `/srv` WORKDIR decoy is refused.

### P3-6: The `.dockerignore` check does not prove the file ships

`test_uvicorn…:389-408` reads `.dockerignore` with `fnmatch` and does not strip a leading `/` or `./`,
which Docker does. So `/flynapse_api/*.json` and `./flynapse_api/uvicorn_log_config.json` pass it (D1,
D1b). It never reads BuildKit's per-Dockerfile `Dockerfile.dockerignore` (D2 passes). Each of these
fails the build loudly at the COPY, not the container, so the cost is a red build.

### P3-7: The import-time sink guard misses 13 shapes, including two its commit names

`test_no_import_time_log_sinks.py:47-164`. Missed:
- **Decorator-applied helper.** `@register` on a configuring helper: the commit claims decorators and
  helpers "flagged where they are CALLED", but decorator application is no `ast.Call`.
- **`from logging import config as lc2; lc2.dictConfig(...)`.**
- **stdlib handlers.** `logging.getLogger().addHandler(logging.handlers.RotatingFileHandler(...))`,
  and a `StreamHandler`.
- **Derived loggers.** `logger.bind(x=1).add(...)`, `logger.opt(...).add(...)`.
- **A class instantiated at import**, whose `__init__` adds a sink.
- **Indirection.** `exec`, `lg = importlib.import_module('loguru').logger; lg.add`,
  `getattr(logger, 'add')`, `functools.partial(logger.add, …)()`, a helper alias `h = _sink; h()`.
- **`pytest_configure` in a conftest.** Out of the "import time" scope, but it has the same
  session-long effect.

Controls caught, and MP8 (helpers ignored) and MP8b (defaults unvisited) each turn red. The real tree
is clean.

### P3-8: The JWKS pin is blind to a non-propagating stdlib logger and to `warnings.warn`

`test_api_cognito_spans.py:275-330`.
- **The fix holds.** The implementer's decoy (a stdlib `warning` with the URL) fails 3/3 **alone**
  (`-k`) and in the file (J0).
- **J1.** A logger with `propagate=False` and its own `StreamHandler` passes alone and in the file. The
  URL goes to stderr, reaching neither capture.
- **J2.** `warnings.warn(f"jwks target {jwks_url}")` passes. The pool id appears in pytest's warnings
  summary, and in production it goes to stderr (no `captureWarnings` in utils or api).

### P3-9: The marker pin has two spellings past it, `uninstall()` persists, and two documentation drifts

- **N13a.** `m = pytest.mark; @m.network` lifts the guard, and `test_no_test_but_this_file_opts_in`
  stays green: `ast.unparse(node.value)` is `m`.
- **N13b.** `item.add_marker("network")` in a nested conftest does the same.
- **N14.** `_netguard.uninstall()` in one test leaves the guard off for the rest of the session and
  nothing fails. `_no_network` never asserts `installed()`, and outside the unit lane nothing does.
- **The "`| tail -1`" claim** (`conftest.py:353`) is false for strays. The N15 session exits 1, but its
  last line is `1 passed in 0.36s`: the stray line is written above the summary, not added to the
  stats as `imported_elsewhere` findings are.
- **Stale test docstrings.** `test_uvicorn_leaves_logging_to_utils.py:10,40,101` still say "the CLI
  launches name `flynapse_api/uvicorn_log_config.json`" and "every launch's relative
  `--log-config`". The images name `/etc/…` since `1247c27`.

---

## What I tried to break and could not

- **Network guard refusals (controls; each ERRORed at teardown).** All were refused before reaching the
  real functions:
  - `asyncio.open_connection("8.8.8.8")`;
  - `loop.create_connection` to a dotted name;
  - `socket.create_connection`;
  - `SSLContext.wrap_socket(...).connect`;
  - httpx, requests, and urllib3 with a dotted name;
  - numeric `getaddrinfo` of `8.8.8.8`, `2001:4860:4860::8888` and `169.254.169.254`;
  - IPv4-mapped `::ffff:169.254.169.254`.
- **The implementer's mutations, re-run.** MP9 (connects unchecked) turns 1 red; MP9b (install
  removed) turns 3 red; MP9e (IMDS disable removed) ERRORs the smoke test with 8 refusals.
- **Every commit is green at its own HEAD** on 9 lanes: 90 runs, exit 0, and 0 attempts under a
  stricter, child-inherited guard. The real-git mirror gives 196 passed and 1 skipped.
- **Rule B controls.** An unquoted aggregate in a sub-select, `string_agg`, `ARRAY(SELECT…)`, a
  CTE-led statement and an attribute call to a non-helper are all refused. MP1, MP1b, MP2, MP3a and
  MP3b are each red.
- **The implementer's P3-1 plant.** `_row_to_tenant = postgres.fetch_all` inside `get_tenant` fails:
  the posed-shape test is red under MP1.
- **P3-7.** Restoring the hard read (T1) turns red both
  `test_a_run_from_a_core_without_the_column_still_dispatches` and the consumer equality pin. Restored,
  16 pass. There is no other hard read of `.traceparent` in `flynapse_api`.
- **P3-6.** The implementer's decoy fails alone and in the file.
- **Image placement.** The COPY is in the final stage of both images. The builder-stage move (D6) and
  the relative path under WORKDIR `/srv` are refused.
- **Launches that could bypass the sweep in reality.** There are none: iac has no command override for
  api; `compose.yaml` and `compose.local.yaml` set no `command:`; and `.github/workflows` launch nothing.
- **P3-10 docs.** README, both CMD comments and `run.py` now describe the measured order (utils
  replaces uvicorn's handler; only re-application leaks).

## What I did not test

- **No docker build or run** (banned). The final-stage COPY, the file mode inside the image and the
  real `.dockerignore` behaviour are argued from the files and the click probes, not built.
- **Postgres-marked integration tests**, `tests/db` and `tests/e2e`: only collection and the
  `not postgres` otel set ran.
- **The pre-`ef897f8` IMDS probe** was suppressed in every run by the reviewer's
  `AWS_EC2_METADATA_DISABLED=true`, on purpose, so that no network call was made.
- **Sibling SHAs.** The siblings are the brief's fixed SHAs, not per-commit-date ones. During this
  review core-obsm moved to `2f972e4` with 6 uncommitted files, and utils and copilot-mro also moved.
  None of that was tested. The reviewer touched no code tree.
- **The 16 git-dependent tests** ran live at HEAD only, in the mirror, not per commit.
- **C-level bypasses** (uvloop, `_socket`, libpq, grpc) were shown only in an empty network namespace.
  They reached the kernel; no route was ever offered.

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r7-01 | api | `tests/conftest.py:296-316` | `_no_network` fails a test whose refusal was swallowed | botocore swallowed 8 IMDS refusals | MP9e smoke ERROR with 8 lookups; MP9c keeps the guard file green (8 passed); MP9e+MP9c: smoke passes silently | none (`test_network_guard.py:3-6` claims one; `recorders` deletes its refusals at `:48`) | no standing guard: MP9c survives | 1 | 1 | F3 | OPEN, P1-1 |
| r7-02 | api | `tests/conftest.py:348-362` | A refusal outside any test fails the session | nothing else catches it | N15 exits 1, but `tail -1` reads `1 passed` | none | MP9d survives (8 passed) | 1 | 1 | F3 | OPEN, P1-1 / P3-9 |
| r7-03 | api | `tests/conftest.py:302-310,354` | The per-test mark is taken at function-fixture setup; sessionfinish reads id `None` only | "a test that triggered one fails" | N1: module-fixture setup and teardown refusals recorded, session exits 0 | none | n/a | 2 | 1 | F3 | REFUTED, P2-1 |
| r7-04 | api | `tests/_netguard.py:91-103` | Wrap `getaddrinfo`, `connect`, `connect_ex` | "every lookup and TCP/UDP connect … before it leaves" | N2 child, N3 `sendto`, N4 `gethostbyname`, N16 single-label reach the next layer; N7/N8/N11/N12 reach the kernel (ENETUNREACH in netns) | `test_network_guard.py` | n/a | 2 | 1 | F3 | PARTIAL, P2-2 |
| r7-05 | api | `tests/_netguard.py:44-51` | Allow private non-link-local addresses | docker bridge, local services | `fd00:ec2::254` and `fd00:ec2::23` pass lookup and connect (N5); the allowance is unused (0 records, loopback-only guard, 90 runs) | none | n/a | 2 | 1 | F3 | OPEN, P2-3 |
| r7-06 | api | `tests/_netguard.py:63-88` | Refuse dotted names without DNS, and non-local connects | stop the leak before it leaves | controls c1 to c9 all refused and failed (asyncio, `create_connection`, ssl, httpx, requests, urllib3, numeric v4/v6/IMDS, IPv4-mapped IMDS) | `test_a_lookup_and_a_connect_beyond_this_machine_are_refused_before_they_leave` | yes: MP9 1 red, MP9b 3 red | — | 0 | F3 | SETTLED |
| r7-07 | api | `tests/conftest.py:80` | Force `AWS_EC2_METADATA_DISABLED=true` | 8 IMDS probes per smoke run | MP9e: smoke ERROR with 8 refused lookups | `test_this_session_runs_behind_the_guard` | yes | — | 0 | F3 | SETTLED |
| r7-08 | api | `tests/unit/infra/test_network_guard.py:96-114` | Equality pin on `*.mark.network` users | one escape hatch | N13a `m = pytest.mark` and N13b `item.add_marker("network")` lift the guard with the pin green; N14 `uninstall()` persists | itself | decoys green | 3 | 1 | F3 | PARTIAL, P3-9 |
| r7-09 | api | `test_paged_registry_reads_state_their_limit.py:653-719` | Resolve an allowlisted helper by binding and identity | r6 P3-1 | RB1 attribute call, RB2 transitive helper and RB3 match capture pass the real-accessor test on core `dc41caa` | `test_every_allowlisted_accessor_is_real_and_its_reason_is_true`, posed shapes | yes: MP1, MP1b red; decoys green | 3 | 1 | F3 | PARTIAL, P3-1 |
| r7-10 | api | `…:148-157, 767-771` | `*agg*` family plus a plain outer select list | r6 P3-2 | RB7 quoted `"json_agg"` sub-select, RB8 `table_to_xml`, `query_to_xml` and a recursive-CTE fold accepted; unquoted aggregate and `string_agg` refused | same | yes: MP2 red; decoys green | 3 | 1 | F3 | PARTIAL, P3-2 |
| r7-11 | api | `…:765` | The basis check strips comments quotes-first only | (not revisited by r6 P3-3) | RB5 `/* ' */ -- ' WHERE …` and RB6 UNION-with-key-last accepted | same | n/a | 3 | 1 | F3 | OPEN, P3-2 |
| r7-12 | api | `…:425-503` | A PostgreSQL-order lexer, unioned with the quotes-first reading | r6 P3-3 | r6's three shapes plus psql, `E''`, a dollar comment and a lateral join flagged; `\r` defeats both readings (RA3, RB4) | `test_the_detectors_flag_the_shapes_they_claim_to_flag` | yes: MP3a, MP3b red | 3 | 1 | F3 | PARTIAL, P3-2 / P3-3 |
| r7-13 | api | `…:115-117` | Table-reference grammar | — | RA1 `table_to_xml('tenants')`, RA2 `FROM (tenants t JOIN …)` and RA4 `U&"tenants"` pass | `test_no_production_sql_reads_the_registry_table` | n/a | 3 | 1 | F3 | OPEN, P3-3 (predates range) |
| r7-14 | api | `test_uvicorn_leaves_logging_to_utils.py:211-283` | Logical-line CLI rule plus a Python-API rule | r6 P3-4 | 12 shapes missed; `UVICORN_APP` shown to apply `LOGGING_CONFIG`; none present in api, iac, compose or `.github` | `test_the_sweep_sees_every_launch_shape_and_no_prose`, equality pin | decoys green (the implementer's mutations not re-run) | 3 | 1 | F1 | PARTIAL, P3-4 |
| r7-15 | api | `Dockerfile:72`, `Dockerfile.local:57` | COPY the config to an absolute `/etc` path in the final stage | r6 P3-5 | final stage in both; D6 builder move refused; D5 `RUN rm` passes 11 tests; D4 `--chmod` fails 2; probes: missing or unreadable file gives exit 2 | `test_the_images_config_path_holds_whatever_the_workdir`, `test_the_images_launch_leaves_logging_to_utils` | D6 red; D5 green | 3 | 1 | F1 | PARTIAL, P3-5 |
| r7-16 | api | `test_uvicorn…:389-408` | `.dockerignore` fnmatch check | the COPY source must ship | `/flynapse_api/*.json`, `./flynapse_api/…` and `Dockerfile.dockerignore` all pass | itself | decoys green | 3 | 1 | F3 | PARTIAL, P3-6 |
| r7-17 | api | `tests/unit/telemetry/test_api_cognito_spans.py:275-330` | Capture loguru plus a root stdlib handler at DEBUG | r6 P3-6 | J0 decoy: 3 red alone and in the file; J1 non-propagating logger and J2 `warnings.warn` pass | itself | yes (J0) | 3 | 1 | F1 | PARTIAL, P3-8 |
| r7-18 | api | `flynapse_api/automations/loop.py:2648` | `getattr(run, "traceparent", None)` | a core without the column costs the link, not the dispatch | T1 hard read: 2 red; restored: 16 pass; no other hard read | `test_a_run_from_a_core_without_the_column_still_dispatches`, `test_every_consumer_span_takes_the_rows_traceparent_column` | yes | — | 0 | F3 | SETTLED |
| r7-19 | api | `tests/unit/infra/test_no_import_time_log_sinks.py:47-164` | A resolver over aliases, the stdlib, decorators, defaults and helpers | r6 P3-8 | 13 shapes missed (decorator-applied helper, `from logging import config`, `addHandler(RotatingFileHandler)`, `bind().add`, class init, …); controls caught; real tree clean | `test_the_sweep_flags_import_time_sinks_and_leaves_function_scoped_ones` | yes: MP8, MP8b red; decoys green | 3 | 1 | F3 | PARTIAL, P3-7 |
| r7-20 | api | `README.md:52-60`, `Dockerfile:119-126`, `Dockerfile.local:100-104`, `flynapse_api/run.py` | Describe the uvicorn-handler risk as measured | r6 P3-10 | read against r6's measurement: consistent | none | n/a | — | 1 | F3 | OPEN (verified by reading; nothing holds it) |
| r7-21 | api | `test_uvicorn…:10,40,101`; `tests/_netguard.py:23-24`; `tests/conftest.py:353` | Docstrings and comments | — | stale relative-path prose; "reach only the local services" unguarded; the `tail -1` claim false (N15) | none | n/a | 3 | 1 | F3 | OPEN, P3-9 |

## Open claims, tier 2 first

**Tier 2:** none. Every claim is test infrastructure or one reversible production line.

**Tier 1**, in the order to fix:
1. **r7-01 / r7-02 (P1-1).** Pin the enforcement half with a nested-session test: swallowed refusals in
   a test body, a module fixture and at collection must each fail the inner session.
2. **r7-03 (P2-1).** Count refusals from every fixture phase.
3. **r7-04 (P2-2).** Carry the guard into children, and wrap `sendto`, `sendmsg`, `gethostby*` and
   `getnameinfo`. Refuse single-label names absent from `/etc/hosts`.
4. **r7-05 (P2-3).** Loopback only, plus an explicit, environment-declared allowance.
5. **r7-09 to r7-13 (P3-1 to P3-3).**
   - Resolve an attribute call's receiver, or refuse any attribute call.
   - Recurse into the helper with the accessor's own rules, and count `MatchAs` / `MatchStar` /
     `MatchMapping.rest` bindings.
   - Require the basis in BOTH comment readings.
   - End `--` comments at `\r`.
   - Refuse set-returning or XML functions and sub-selects in FROM, or better, move the one-row claim
     from a SQL parse to a `LIMIT 1` / unique-key predicate the accessor cannot hide.
6. **r7-14 to r7-16 (P3-4 to P3-6).**
   - Widen the sweep: `UVICORN_APP`, YAML lists, `uvicorn.main`, `uvicorn.workers`, dot-directories
     other than `.git` and `.venv`.
   - Accept flagged COPYs and add `--chmod=0444`.
   - Refuse a later RUN that removes the path.
   - Normalise `/` and `./` ignore patterns, and read `<Dockerfile>.dockerignore`.
7. **r7-17, r7-19 (P3-7, P3-8).** Resolver additions; capture `warnings` and every stdlib logger with
   a handler.
8. **r7-08, r7-21 (P3-9).**
   - Pin the marker by resolved marks (`item.iter_markers`) at collection, not by AST.
   - Assert `installed()` in `_no_network`'s teardown.
   - Tag the stray on the summary line.
   - Refresh the three stale docstrings.
