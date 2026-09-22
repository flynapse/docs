# Claims packet: api review r8 (`847c34c..b3178f4`, 10 commits, the r7 batch)

This is an independent adversarial review (Opus), done on 2026-09-21. No code tree was changed. Every run
used a `git archive` copy, or a shared-clone mirror, in the reviewer's private scratch
(`scratchpad/api-review-r8/`). Each mutation was applied to a scratch copy, confirmed with grep, run under
a fresh `PYTHONPYCACHEPREFIX`, reversed from saved bytes, and md5-checked against the HEAD blob. All 38
restores matched.

| repo | worktree | branch | range | HEAD at review | tree state |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `847c34c..b3178f4` | `b3178f4` | clean, untouched |

**Verdict: FIX-FIRST.** No P0 and no P1. **2 P2**, both claims the batch makes that its guards do not
hold. **13 P3.** No content leak ships: the only production change is a docstring (`routers/auth.py`).
- **P2-1 (tier 2).** The "authoritative" Postgres test for Rule B cannot fail for a prefix-matching
  accessor, which its docstring says it catches. The static parse accepts one too. It has never run.
- **P2-2.** The service-port rule is measured as "nothing reaches a dev-stack port", but the unit and
  smoke lanes reach Postgres's port 11 times through libpq. The declared reason ("no Python-level guard
  can see" libpq) is overstated: `psycopg2.connect` is a Python seat.

The r7 P1 is fixed and mutation-settled at every scope it claims.

## How it was run

- **Workspaces.** Each of the 10 commits and the base were extracted into their own `ws-<sha>/api-obsm`.
  The siblings are the brief's archives: core-obsm `1232f21`, utils-obsm `4d86ae9`, copilot-mro-obsm
  `62c7413d` and flynapse-otel `5b86943`, plus shift-optimizer `8bd4d66` (api's `routers/optimizer.py`
  imports it). Each ws carries sibling symlinks so the layout tests see a workspace. They were declared
  through `SIBLING_CHECKOUTS` for core, utils and copilot-mro.
- **Recipe.** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`,
  `PYTHONPATH` pinned to the ws and the archives, and a fresh `PYTHONPYCACHEPREFIX` per run. The command
  was `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider -m "not postgres" <lane>`.
  pytest's own exit status was read.
- **Where the code came from.** The rootdir was always `ws-<sha>/api-obsm`. The conftest header showed
  flynapse_api from `ws-<sha>/api-obsm` (this checkout), and core, utils and copilot_mro from the
  archives (declared). A probe test (`r8probe/test_r8_provenance.py`) showed flynapse_otel,
  shift_optimizer and `_netguard` also came from the archives and the ws.
- **Network: none possible.** Every run, lane, mutant and plant ran inside `unshare -rn` with only
  `lo` up. The dev stack on the host's loopback was unreachable, so no test could reach Postgres or
  Redis whatever its marker. `AWS_EC2_METADATA_DISABLED=true` was set, and no bare interpreter imported
  anything from api.
- **A C-level witness.** An `LD_PRELOAD` shim (`tools/netlog.c`) logged every libc `connect`, `sendto`
  and `getaddrinfo` with `PYTEST_CURRENT_TEST`. A `sitecustomize` tracer logged the Python stack of every
  `psycopg2.connect`. Neither sends anything.
- **Real git.** A shared-clone mirror with real worktrees (api-obsm, core-obsm, utils-obsm and
  copilot-mro-obsm, all on `obs-merge`) ran `tests/unit/infra` at HEAD: **213 passed, 1 skipped**, exit
  0. It also ran the smoke lane at `6d7ab24`, `377471f` and HEAD (21 passed + 3 skipped, exit 0 each),
  and the uvicorn file at each commit from `10c5389` on (14 passed each).

### Lane results

| commit | unit | smoke | startup | api | middleware | otel + netguard | integ collect |
|---|---|---|---|---|---|---|---|
| `847c34c` (base) | 896 + 16s | 21 + 3s ‡ | 69 | 25 | 310 | 36 + 1s | 366 |
| `6d7ab24` | 905 + 16s | 21 + 3s ‡ | 69 | 25 | 310 | 36 + 1s | 366 |
| `707a08d` | 906 + 16s | — | — | — | — | — | 369 |
| `377471f` | 910 + 16s | 21 + 3s ‡ | 69 | 25 | 310 | **38** + 1s | **371** |
| `d93f75e` | 910 + 16s | — | — | — | — | — | 371 |
| `10c5389` | 912 + 16s, 1 † | — | — | — | — | — | 371 |
| `ae42c51` | 912 + 16s, 1 † | — | — | — | — | — | 371 |
| `7a56369` | 912 + 16s, 1 † | — | — | — | — | — | 371 |
| `f64124f` | 912 + 16s, 1 † | — | — | — | — | — | 371 |
| `821a95c` | 912 + 16s, 1 † | — | — | **26** | — | — | 371 |
| `b3178f4` | 912 + 16s, 1 † | 21 + 3s ‡ | 69 | 26 | 310 | 38 + 1s | 371 |

- **† archive-only.** `test_the_configuration_is_committed_world_readable` runs `git ls-files` and
  FAILS without a checkout (P3-10). It passes in the mirror at every commit that has it.
- **‡ artefact.** Smoke reports "1 wrong-checkout import" in the symlinked-archive layout at the base
  too. The mirror is clean at every commit it ran.
- **Deltas.** Every delta equals the tests the commit adds. 912 + 16 + 1 = 929, the implementer's unit.
- **Integration collect.** 371 is the implementer's 382 less 11 tests in the five modules that probe
  Postgres at collection and skip at module level. Postgres is unreachable in the namespace.
- **Refusals.** Zero network refusals in any lane at any commit. The libc shim saw Redis `6379` from
  `test_auth_cache.py::test_auth_cache_manager` at `847c34c`, `6d7ab24` and `707a08d`, and never from
  `377471f` on. That confirms 377471f's cache pin behaviourally. It saw Postgres `5432` in every commit
  (P2-2).

---

## Findings, ranked

### No P0, no P1

Nothing in the range ships content. r7's P1-1 is fixed: every phase and scope it claims turns its nested
test red under the reviewer's own mutants (r8-01 to r8-05).

### P2-1: Rule B's "authoritative" Postgres test cannot fail for a forward-prefix accessor (tier 2)

**Where.** `tests/integration/registry/test_single_row_accessors_return_the_tenant_asked_for.py:11-15,78-100`
and `test_paged_registry_reads_state_their_limit.py:50-62`.

**What the batch claims.** 707a08d demotes the static one-row parse to a "speed bump" and names this test
"the AUTHORITATIVE check". Its docstring says an accessor that "matches by prefix answers some other
tenant ... and fails here".

**Why it cannot.** Take the twins, where the shorter value is a prefix of the longer.
- **The forward direction** is `WHERE lower(domain) LIKE lower(%s) || '%' LIMIT 1`, a stored value that
  starts with the query. Asked for the longer twin, it can only match the longer one. Asked for the
  shorter, it matches both, and `fetch_one` takes the first row in scan order.
- **Scan order puts the shorter first.** The shorter twin is inserted first (heap order). The
  `lower(domain)` / `tenant_name` index order puts it first too ("twin-t.example" sorts before
  "twin-t.example.org").
- **So it passes both lookups.** Only the reverse direction (`%s LIKE domain || '%'`) returns the wrong
  twin.
- **The parse accepts it too.** Measured with the module's own `_one_row_basis` on posed accessors
  (`r8probe/test_r8_rule_b_prefix.py`): the prefix domain accessor, the prefix name accessor and the
  exact control each come back `('LIMIT 1', '')`.

So for `get_tenant_by_domain` and `get_tenant_by_name`, the auth STEP 0 lookups api calls
(`middleware/auth.py:200,233`), no guard catches a forward prefix match.

**List-then-filter passes too.** An accessor that `fetch_all`s the registry and filters in Python
returns exactly the tenant asked for. That unbounded read is the property Rule B exists for. Only the
parse sees it, and only when the listing is called directly: attribute-called and transitive helpers are
declared misses.

**The test has never run.** It is `postgres`-marked and deselected everywhere. It also seeds both rows
before its `try:` (`:90-95`), so if the second INSERT fails, the first tenant row is left behind.

**Scenario.** A later change makes the domain lookup forgiving: `LIKE`, or `starts_with` for
"subdomains". A login from `acme.co` then resolves to tenant `acme.com`, a cross-tenant login
resolution. The parse accepts it. The authoritative test passes, when it runs at all.

**Fix.**
- Add negative probes. Asking for a strict prefix of a stored value that is not itself stored
  (`twin-<token>.exam`, `rule-b-twin-<token>-`) must return `None`.
- Seed in both orders.
- Wrap `postgres.fetch_all` to raise while the accessor runs, so list-then-filter fails.
- Restate the authority. The parse is still the only boundedness guard, so it is not merely a speed
  bump.

### P2-2: The service-port rule's measurement is false for Postgres, and its declared limit is overstated

**Where.** `tests/_netguard.py:43-48`, `tests/conftest.py:338-345`, and plan §1 / §3 ("Measured ...
nothing in api reaches a dev-stack port through Python"; "no Python-level guard can see them").

**Measured (libc shim, test id attached).** The service-port rule says the unit and smoke lanes may not
reach 5432. Both do, through libpq:

| lane | libpq connects to `127.0.0.1:5432` | from |
|---|---|---|
| unit | 10 | `tests/unit/automations/test_tick_decisions.py`: ten tests, via `announcements.py:44-54` `_tenant_operator_ids` (`SELECT operator_id FROM operators`). The file's autouse `bell` fixture (`:116`) stubs `NotificationService.create` but not this read, although the file's docstring says "every assertion here holds with no server running". |
| smoke | 1 | `tests/smoke/automations/test_executor_real_adapter.py:302` `rbac_rows`, which reads real `user_departments` / `user_roles` rows |
| integration, at collection | 5 | module-level `_db_ready` / `_postgres_reachable` probes in 5 modules, including a `postgres`-deselected one |

- **On the implementer's machine**, with the dev Postgres up, every one of these was a live read of
  `copilot_mro_test`, made while the batch claimed nothing reaches the dev stack.
- **The declared limit is honest in letter, but its premise is wrong for Postgres.** The reviewer's
  tracer saw all 16 connects with a full Python stack at `psycopg2.connect`, called from
  `utils/postgres_service.py:284` `_ensure_pool`. That is the Python seat the guard could judge by the
  same host and port rule. grpc has one too (`grpc.*_channel`).

**Scenario.** A unit test that reaches a write path unstubbed, as the tick tests almost did, writes
into the developer's database. The guard stays silent, and the batch's measurement says it cannot
happen.

**Fix.**
- Wrap `psycopg2.connect` (and `psycopg.connect` if present) in `_netguard`, keyed on
  `host`/`hostaddr`/`port` or the DSN, and refuse 5432 outside `_SERVICE_PORT_OPT_INS`.
- Stub `_tenant_operator_ids` in the tick tests' `bell` fixture.
- Mark the smoke row-shape tests `postgres`, or move them to the integration lane.
- Pre-existing, and the same root: 40 unmarked tests in `tests/integration/automations` fail when
  Postgres is unreachable (120 of their 155 connects go through `_tenant_operator_ids`). So
  `-m "not postgres"` does not keep a lane off Postgres.

### P3-1: A refusal followed by a skip, or in an xfail test, passes the session

The claim is that a refusal fails its phase "whether or not anything noticed it"
(`tests/conftest.py:361-407`). Plants in `r8probe/test_r8_net_plants.py`, each run alone:
- **Skip after the refusal.** A swallowed refused lookup followed by `pytest.skip()` gives
  "1 skipped", exit 0.
- **xfail.** The same inside a test marked `@pytest.mark.xfail` gives "1 xfailed", exit 0.
- **Probe-and-skip.** A fixture that catches a refused `127.0.0.1:6379` connect and skips gives
  "1 skipped", exit 0.
- **Control.** The same refusal with no skip gives exit 1.

**Why.** The wrapper's `pytest.fail` runs only when the phase did not raise, so a skip wins. The xfail
plugin turns the wrapper's own `Failed` into XFAIL.

**Exposure today.** Every probe-and-skip in api goes through libpq, which is invisible anyway, so none
exists yet. It is the natural shape for a Redis or OTLP probe.

**Fix.** Check unexpected refusals in the `finally` and fail even when the outcome raised `Skipped`. Or
override the report in `pytest_runtest_makereport` when the phase recorded a refusal.

### P3-2: A loopback forwarder carries an external request with zero refusals

`r8probe/test_r8_net_plants.py::test_r8_loopback_forwarder_carries_an_external_request` sets
`HTTPS_PROXY` to a fake proxy on an ephemeral loopback port and calls `requests.get("https://cognito-idp...")`.
- The proxy received `CONNECT cognito-idp.ap-south-1.amazonaws.com:443 HTTP/1.0`.
- `REFUSED` stayed empty, and the test passed.

The same holds for any loopback tunnel (`ssh -L`, SSM port-forward, `kubectl port-forward`) on a
non-service port.

**Exposure.** No proxy variable is set in this shell or in api's `.env`. The guard's headline "nothing
leaves this machine through Python" (`_netguard.py:1`) holds only while that stays true, and nothing
says so.

**Fix.** Blank `*_PROXY`/`ALL_PROXY` in the conftest, as `COGNITO_USER_POOL_ID` is, and declare
tunnels.

### P3-3: Children the guard never reaches

`_netguard.py:32-35` says "every child Python process installs this guard". Four plants each saw
`'_netguard' in sys.modules` False in the child:
- `python -I`;
- `python -E`;
- `python -S`;
- a scrubbed `env={"PATH": ...}`.

None exists in api's tests today.

**Fix.** Declare it. Or refuse such spawns: an audit hook on `subprocess.Popen` that requires the
guard's variables in the child environment.

### P3-4: The guard's own tests make real lookups and connects when the guard is broken

`test_network_guard.py:9-10` says "a broken guard shows as a call that reached a recorder, never as a
packet". `test_network_guard_probes.py:5-6` says a planted lookup "never reaches the real resolver even
with the guard broken". The libc shim contradicts both:

| mutant | what the test did | libc record |
|---|---|---|
| MR3: the raw `_socket.socket` type left unguarded | `connect(("8.8.8.8", 53))` | real `connect inet 8.8.8.8:53` |
| MR1: the raw name functions left unwrapped | `_socket.getaddrinfo("example.invalid", 80)` | real lookup |
| MA11: the child's guard loaded but not installed | the child plant | real `getaddrinfo netguard-child-probe.example.invalid:443` |

The implementer's own mutation list includes "the raw type not swapped", and the plan records the
network namespace as "not built". Whether that run sent a SYN depends on how the mutant was written.

**Fix.** Aim the raw cases at `240.0.0.1`. Linux refuses to route 240/4 locally, so a broken guard gets
`ENETUNREACH` and no packet. Make the probes' fallback raise when `_REAL` is empty.

### P3-5: `COPY --chmod=0600` now passes every image test

10c5389 accepts every flagged COPY but `--from` (`test_uvicorn…:170-200`), and never reads the
`--chmod` value.
- **UD1.** `COPY --chmod=0600 flynapse_api/uvicorn_log_config.json /etc/…` in `Dockerfile` fails only
  the archive-only git test, the same as the control. All image tests pass.
- **What it ships.** A root-owned 0600 file under `USER appuser` (`Dockerfile:103`) stops uvicorn with
  exit 2 before the app loads, which r7 measured. The readability test checks the checkout's mode, not
  the COPY.
- **A regression.** r7's D4 refused every `--chmod`.

**Fix.** When `--chmod` is present, require the other-read bit. Better, require `--chmod=0444` once the
deferred Dockerfile change lands.

### P3-6: The uvicorn launch sweep misses four more launch shapes, none declared

In `r8probe/test_r8_static_decoys.py`, `_launch_files` found only the control among:
- `gunicorn.conf.py` (`worker_class = "uvicorn.workers.UvicornWorker"`, `wsgi_app = …`) with
  `exec gunicorn -c gunicorn.conf.py`;
- `from uvicorn import main; main.main([...])`, click's own entry, which is the shape the test's
  `_CHILD` uses;
- `from uvicorn.main import main as cli; cli.main(argv)`;
- a poetry script `serve = "uvicorn.main:main"`.

None is in the estate.

### P3-7: The sink guard misses five undeclared shapes, and three claimed shapes are unpinned

**Undeclared misses** (`_import_time_calls` returned `[]`):
- a helper imported from another module and called at import;
- an attribute decorator (`@helpers.register`);
- utils' own installers at import: `log_bridge.install(...)` and `setup_logging(...)`;
- a helper called in a class body.

**Claimed but unpinned.** The docstring (`:11-16`) and the code claim three more shapes. Each mutant
leaves the file green:
- SG1: `patch` dropped from `DERIVING`;
- SG2: `handlers` dropped from `_LOGGING_SUBMODULES`;
- SG3: the Timed and Watched handlers unlisted.

**Declared set.** Honest: replaying r7's own plant file gives S1, S3, S4, S7, S8, S9 and S10 missed and
the other six caught, exactly as the plan says. It is acceptable, because a test-session file sink ships
nothing.

### P3-8: The JWKS pin is blind to raw stdout and stderr

JD1 (`print(f"… {jwks_url}")`) and JD2 (`sys.stderr.write(…)`), placed after the fetch's log line, both
leave the file green. In production, stdout and stderr are the container log.

**Fix.** Add `capfd` to the pin.

The stdlib and warnings half is SETTLED (r8-17).

### P3-9: Rule B's "both readings must agree" is two-thirds unpinned

`_one_row_basis` (`test_paged_registry…:784-793`) reads the SQL both ways, needs a basis from each, and
needs the two to agree. Two mutants leave the file green (13 passed):
- RBm1: keep only the comments-first reading;
- RBm2: drop the agreement check.

Only "comments-first must find a basis" is pinned, by the implementer's posed `/* ' */ -- '` shape.

### P3-10: The readability test fails outside a git checkout

`test_uvicorn…:510-522` calls `git ls-files --stage` with `check=True`, so it FAILS in an archive or a
`.git`-less build context. The suite's other 16 git-dependent tests skip there.

It is mutation-checked in the mirror: mode 0600 gives red ("appuser could not read it"), and restored
gives green, md5 and mode verified.

### P3-11: The child plant does not pin phase attribution

`test_network_guard.py:228` expects `"(child pid"`. The session-level stray line carries the same text.
With call-phase enforcement removed (MA3), the child case stayed GREEN: the child's refusal fell outside
every accounted range, and the stray check failed the session with "(child pid". So "a child's refusal
fails ITS phase" is unpinned. The session still fails.

**Fix.** Expect `"refused during call"` together with `"(child pid"`.

### P3-12: An ordinary socket test double fails as "the network guard was uninstalled"

A test with `monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])` fails "the network guard
was uninstalled during call". It fails closed, but the message misleads, and nothing tells an author
that `_netguard._REAL` is the stub seam.

### P3-13: Documentation drift

- **`_netguard_site` is not "first on PYTHONPATH"** (`conftest.py:83`, `sitecustomize.py:3`, plan §1).
  `pinned_pythonpath` moves the four pinned roots in front of it: it measured at index 4. A
  `sitecustomize.py` at api's root (the usual coverage-subprocess recipe) then shadows it. The guard's
  own test catches that (red), so this is a docs error, not a hole.
- **`conftest.py:340` says the integration lane's "tests carry the `postgres` marker".** 40 unmarked
  tests there reach Postgres (P2-2).
- **`SERVICE_PORTS` omits DynamoDB Local's `8050`,** which api's own `.env` names
  (`AWS_DYNAMODB_LOCAL_ENDPOINT`). The workspace also has a `dynamodb-local` MCP server.
- **`ML1` (IPv4-mapped unmapping removed) is an equivalent mutant on Python 3.11.15**
  (`::ffff:127.0.0.1`.is_loopback is True). The branch matters only for `EXPLICIT_ALLOWANCES`.
- **The brief cites an owner ruling `M-SHARED-NETGUARD`.** It is not in §4a-bis of the governing plan.
  The only mention is `flynapse-otel/docs/plans/shared-exception-text-detector.md:971`. By §2.3a that is
  CLAIMED BUT NOT FOUND, and it is the controller's to record.

---

## What I tried to break and could not

- **The FAIL half, at every scope claimed.** Each of the reviewer's own conftest mutants turned the
  matching nested test red:
  - MA1 (setup unhooked): `module-setup`.
  - MA2 (teardown unhooked): `module-teardown`.
  - MA3 (call unhooked): `body`, `service-port` and `uninstall`, plus the allowlisted-marker test and
    both integration-lane tests.
  - MA10 (first refusal of a phase dropped): 4 red.
  - MA4 (child log unread) and MA15 (pid filter inverted): `child`.
  - MA5 (uninstall check off): `uninstall`.
  - MA6 (strays dropped), MA7 (tag dropped), MA8 (exit not flipped) and MA14 (every refusal accounted
    from index 0): the collection-time test.
  - MA9 (marker check off): the plugin-added-marker test.
- **Class and session scopes.** Plants in `r8probe/test_r8_scopes.py` in a session fixture's setup and
  teardown and a class fixture's setup and teardown each gave exit 1 with "refused during
  setup/teardown". The unplanted control gave exit 0.
- **Service ports and loopback-only.**
  - MS1 (port rule off): 4 red, which matches the implementer's count.
  - MS2 (every port opened): 6 red.
  - MS3 (5432 opened for every lane): 2 red.
  - ML2 (single labels allowed), MR1 (raw names unwrapped), MR2 (`sendmsg` address ignored) and MR3
    (raw type unguarded) each turned the entry-point sweep red.
  - MA11 (child guard never installed): 2 red.
- **Cache pin.** CP1 (the pin called without `force_in_memory`) turns the pin test red. The libc shim
  shows `6379` gone from `377471f` on.
- **Rule B link test.** LK1 (an extra accessor in the Postgres test's `ACCESSORS`) turns it red.
- **PermissionsResponse.**
  - PR1 (drop empty entries in `permission_payload`, `middleware/auth.py:1365`) turns 2 red.
  - The production map is built by `authz_resolver.capabilities_by_department` (`middleware/auth.py:996`),
    keyed `str(department_name).strip().lower()` (core `authz/resolver.py:191`).
  - The dashboard already reads by that key (`dashboard-obsm lib/auth/grantable.ts:24-26`,
    `settings/department/account/page.tsx:103`), so the contract correction matches both ends.
- **Sweep and image.**
  - US1 (`.yaml` unread): the compose decoy red.
  - US2 (`VOLUME` not counted): both image cases red.
  - DI1 (the per-Dockerfile ignore file always named `Dockerfile.dockerignore`): the build-context test
    red.
  - The six planted later touches and four ignore decoys are all caught.
- **JWKS stdlib and warnings.** Each gave 3/3 red:
  - JW3: `warnings.warn` with the URL.
  - JW4: a non-propagating logger with only a `NullHandler`.
- **Sink guard.** SG6 (derived loggers never loggers) is red.
- **r7's sink plants.** Replayed read-only through HEAD's guard, they match the implementer's claim
  exactly.

## What I did not test

- **No Postgres test ran:** not the registry accessor test, not the traceparent round trip, and nothing
  against a database. P2-1's ordering argument is reasoned from PostgreSQL's scan and index order, not
  executed. The parse half was executed.
- **No docker build.** `COPY --chmod`, the file mode inside an image and BuildKit's ignore behaviour are
  argued from the files.
- **The namespace's side effects.** Every lane ran with the dev stack unreachable. So each Postgres
  reach was observed as a refused libc connect, not as a query. What those reads return on a live
  database was not observed.
- **Sibling SHAs.** The siblings are the brief's fixed SHAs, not per-commit ones.
- **The 16 git-dependent tests and the readability test** ran live in the mirror at HEAD, and the
  uvicorn file at each of its commits. The other lanes did not run in the mirror per commit.

## Claims table

| # | Repo | File:line | Claim (decision taken) | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state | r7 finding answered |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r8-01 | api | `tests/conftest.py:361-422` | A refusal fails the PHASE it was made in (setup, call, teardown), so any fixture scope fails | MA1, MA2, MA3, MA10 red; class and session plants exit 1 | `test_a_swallowed_refusal_fails_the_phase_it_was_made_in[body, module-setup, module-teardown, service-port]` | yes (reviewer's own) | — | 0 | F3 | SETTLED | P1-1, P2-1: FIXED |
| r8-02 | api | `tests/conftest.py:425-447,479-521` | A refusal outside every phase fails the session, tagged on the final line | MA6, MA7, MA8, MA14 red | `test_a_refusal_outside_every_test_phase_fails_the_session_on_its_final_line` | yes | — | 0 | F3 | SETTLED | P1-1, P3-9 (`tail -1`): FIXED |
| r8-03 | api | `tests/_netguard.py:32-35,336-355`, `_netguard_site/sitecustomize.py` | Children install the guard and report through the session log | MA4, MA15, MA11 red; `-I`/`-E`/`-S`/scrubbed-env children unguarded; MA3 leaves `child` green (stray backs it) | `…[child-(child pid]`, `test_this_session_and_its_children_run_behind_the_guard` | yes, for "fails the session"; phase attribution unpinned | 3 | 0 (session) / 1 (rest) | F3 | SETTLED for the session exit; OPEN for flags and env (P3-3) and phase (P3-11) | P2-2 (children): PARTIAL |
| r8-04 | api | `tests/conftest.py:387-400` | A phase that leaves the guard uninstalled fails; re-installed every phase | MA5 red; `test_the_guard_is_back_after_the_opted_in_test` | `…[uninstall-…]` | yes | — | 0 | F3 | SETTLED | P3-9 (N14): FIXED |
| r8-05 | api | `tests/conftest.py:369-376` | The resolved `network` marker fails every test but the one allowlisted | MA9 red | `test_the_network_marker_on_any_other_test_fails_it` | yes | — | 0 | F3 | SETTLED | P3-9 (N13a/b): FIXED |
| r8-06 | api | `tests/_netguard.py:125-147,193-209,256-286` | Loopback only; every name function in `socket` and `_socket`; raw `_socket.socket` guarded | ML2, MR1, MR2, MR3 red; ML1 equivalent on 3.11.15 | `test_every_wrapped_entry_point_refuses_beyond_loopback_before_it_leaves` | yes | — | 0 | F3 | SETTLED | P2-2 (Python level), P2-3: FIXED |
| r8-07 | api | `tests/_netguard.py:74-85,153-167,212-226`; `conftest.py:343-351,381` | Service ports refused on loopback outside an opted-in lane | MS1 (4), MS2 (6), MS3 (2) red | `test_only_a_lane_that_opted_in_reaches_a_service_port`, nested `service-port`, integration-lane pair | yes | — | 0 | F3 | SETTLED (Python level) | (audit items 1-2) |
| r8-08 | api | `tests/_netguard.py:43-48`; `conftest.py:338-342`; plan §1/§3 | "no Python-level guard can see" libpq; "nothing in api reaches a dev-stack port" | libc shim: unit 10, smoke 1, integ-collect 5 connects to `5432`; tracer shows each at Python `psycopg2.connect` | none | n/a | 2 | 1 | F3 | OPEN (P2-2) | P2-2 (C level): overstated declaration |
| r8-09 | api | `tests/conftest.py:383-406` | A refusal fails its phase "whether or not anything noticed it" | skip-after-refusal, xfail and probe-and-skip plants exit 0; control exit 1 | none | n/a | 3 | 1 | F3 | OPEN (P3-1) | new |
| r8-10 | api | `tests/_netguard.py:1,125-147` | "Nothing leaves this machine through Python" | a loopback fake proxy received `CONNECT cognito-idp…:443` with 0 refusals | none | n/a | 3 | 1 | F3 | OPEN (P3-2) | new (P2-3's neighbour) |
| r8-11 | api | `test_network_guard.py:9-10`; `test_network_guard_probes.py:5-6` | A broken guard never produces a packet or a real lookup | MR3: libc `connect 8.8.8.8:53`; MR1 and MA11: real `getaddrinfo` | none | n/a | 3 | 1 | F3 | OPEN (P3-4) | new |
| r8-12 | api | `tests/conftest.py:204-212` | The process cache is pinned in memory before any app import | CP1 red; libc `6379` gone from `377471f` on | `test_the_process_cache_resolves_in_memory_without_a_socket` | yes | — | 0 | F3 | SETTLED | (audit item 1) |
| r8-13 | api | `tests/integration/registry/test_single_row_accessors_return_the_tenant_asked_for.py:11-15,78-100` | The Postgres test is Rule B's authority and catches listing and prefix matching | parse accepts prefix accessors (`LIMIT 1`); twins ordered so a forward prefix passes; list-then-filter passes; never run; seeds before `try:` | itself (unrun) | no | 2 | 2 | F1 | OPEN (P2-1) | P3-1/2/3: DECLARED, replacement authority does not hold |
| r8-14 | api | `test_paged_registry…:784-793` | Both comment readings must find a basis, and the bases must agree | RBm1 and RBm2 green (13 passed); the implementer's quotes-first-only mutant not replayed | `test_the_one_row_check_refuses_every_listing_shape_and_accepts_a_bounded_read` | partly (implementer's only) | 3 | 1 | F3 | ASSERTED (P3-9) | P3-2 (RB5): FIXED, partly pinned |
| r8-15 | api | `test_paged_registry…:839-854` | Every allowlisted accessor is asked by the Postgres test | LK1 red | `test_the_authoritative_postgres_test_asks_every_allowlisted_accessor` | yes | — | 0 | F3 | SETTLED | new |
| r8-16 | api | `test_uvicorn…:243-259,302-360` | The sweep reads gunicorn, hypercorn, YAML lists, `.github`, `UVICORN_APP`, `uvicorn.main` | US1 red; 4 undeclared shapes missed | `test_the_sweep_sees_every_launch_shape_and_no_prose`, equality pin | yes | 3 | 1 | F1 | PARTIAL (P3-6) | P3-4: PARTIAL |
| r8-17 | api | `test_uvicorn…:170-230,486-507` | Nothing after the COPY touches the file; flagged COPYs resolve | US2 red; 6 later-touch decoys caught; UD1 `--chmod=0600` passes every image test | `test_nothing_after_the_copy_removes_or_changes_the_configuration` | yes for later touches | 3 | 1 | F1 | PARTIAL (P3-5) | P3-5: PARTIAL; `COPY --chmod` deferred (declared) |
| r8-18 | api | `test_uvicorn…:510-522` | The committed file is world-readable | mirror: 0600 red, 0644 green; fails outside git | itself | yes (mirror) | 3 | 0 (checkout) | F1 | SETTLED in git; OPEN outside (P3-10) | P3-5 (readability): FIXED for the checkout |
| r8-19 | api | `test_uvicorn…:552-600` | Read the ignore file BuildKit reads, normalised as Docker does | DI1 red; 4 decoys caught; control clean | `test_the_build_context_does_not_exclude_the_configuration` | yes | — | 0 | F3 | SETTLED | P3-6: FIXED |
| r8-20 | api | `test_no_import_time_log_sinks.py:11-23,69-210` | Decorators, `from logging import config`, `addHandler`, derived loggers seen; rest declared | SG6 red; SG1-SG3 green; 5 undeclared misses; r7 plants replayed as claimed | `test_the_sweep_flags_import_time_sinks_and_leaves_function_scoped_ones` | yes (SG6); claimed shapes unpinned | 3 | 1 | F3 | PARTIAL (P3-7) | P3-7: PARTIAL, declared set honest |
| r8-21 | api | `tests/unit/telemetry/test_api_cognito_spans.py:275-345` | Every stdlib record at `callHandlers` and every warning is read | JW3 and JW4 red 3/3; JD1 and JD2 (print, stderr) green | `test_the_jwks_fetch_logs_the_host_and_never_the_pool` | yes (JW3, JW4) | 3 | 1 | F1 | SETTLED for stdlib and warnings; OPEN for stdout and stderr (P3-8) | P3-8: FIXED, residual |
| r8-22 | api | `flynapse_api/routers/auth.py:42-45`; `middleware/auth.py:996,1365`; `test_permissions_endpoint.py:133-160` | `capabilitiesByDepartment` is keyed by lowercased, trimmed department NAME, one entry per membership | PR1 red (2); resolver keys `strip().lower()`; the dashboard reads by that key | `test_capabilities_are_keyed_by_the_lowercased_department_name` | yes | — | 0 | F1 | SETTLED | M-PERMISSIONS-ENDPOINT contract: CORRECTED |
| r8-23 | api | `conftest.py:83`; `sitecustomize.py:3`; plan §1 | The site directory is first on `PYTHONPATH` | measured at index 4 behind the pinned roots; a root `sitecustomize.py` shadows it (the guard test goes red) | `test_this_session_and_its_children_run_behind_the_guard` | decoy red | 3 | 1 | F3 | OPEN, docs (P3-13) | — |
| r8-24 | api | `tests/conftest.py:387` | "Uninstalled" means uninstalled | a `monkeypatch` socket double fails with that message | none | n/a | 3 | 1 | F3 | OPEN (P3-12) | — |
| r8-25 | api | `tests/_netguard.py:74-85` | The service-port list covers the dev stack | `.env` names DynamoDB Local on `8050`, which is not listed | none | n/a | 3 | 1 | F3 | OPEN (P3-13) | — |
| r8-26 | workspace | `docs/plans/observability-telemetry-merge-and-completion.md` §4a-bis | Owner ruling M-SHARED-NETGUARD | not in §4a-bis; only flynapse-otel's plan names it | none | n/a | 3 | 1 | F3 | CLAIMED BUT NOT FOUND | — |

## Open claims, tier 2 first

**Tier 2:**
1. **r8-13 (P2-1).** Rule B's authority.
   - Give the Postgres test negative prefix probes and both seed orders.
   - Refuse `fetch_all` during the accessor call.
   - Move the seed inside the `try:`.
   - Run it once against `copilot_mro_test`.
   - Stop calling the parse a speed bump for boundedness.

**Tier 1**, in the order to fix:
1. **r8-08 (P2-2).** Wrap `psycopg2.connect` with the host and port rule. Stub `_tenant_operator_ids`
   in the tick tests. Mark or move the smoke row-shape tests. Correct plan §1/§3 and
   `conftest.py:340`.
2. **r8-09 (P3-1).** Fail a phase with unexpected refusals even when it skipped or xfailed.
3. **r8-10, r8-03 (P3-2, P3-3).** Blank the proxy variables. Declare or refuse `-I`/`-E`/`-S` and
   scrubbed-env children.
4. **r8-11 (P3-4).** Aim the raw and child cases at `240.0.0.1`, and make the probes raise when `_REAL`
   is empty.
5. **r8-17, r8-18 (P3-5, P3-10).** Read the `--chmod` value. Skip the git half outside a checkout.
6. **r8-14, r8-20, r8-21, r8-16 (P3-9, P3-7, P3-8, P3-6).**
   - Pin the quotes-first reading and the agreement check.
   - Plant `patch`, `from logging import handlers` and the Timed/Watched handlers.
   - Add `capfd` to the JWKS pin.
   - Declare or catch the four launch shapes and the five sink shapes.
7. **r8-03 (phase attribution), r8-23 to r8-26 (P3-11 to P3-13).**
   - Tighten the child assertion.
   - Document the `_REAL` stub seam.
   - Add `8050`.
   - Correct the "first on PYTHONPATH" prose.
   - Have the controller record M-SHARED-NETGUARD.
