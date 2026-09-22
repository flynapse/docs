# Claims packet: flynapse-otel review — network guard r1 (M-SHARED-NETGUARD, `5146857` + `d1e531f`)

Independent adversarial review by Opus, 2026-09-22 (paused once by the owner, resumed; this is the final version). Read-only throughout: no code tree edited, checked out, stashed or committed; no docker, no DB, no live network. Every probe ran as a NESTED pytest session under the extract's own `guard_session`, with raisers beneath `_REAL` (the sessions test's own conftest shape) or, where a real socket was needed, against a test-owned loopback listener; nothing left this VM. Mutations ran in a durable extract (`~/.claude/scratch/obs-merge/otel-review-r7/c/d1e531f`) through `mutant.sh` (baseline green first, md5-verified restore); every restore matched.

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` (HEAD `df503c2` at the end; the range is fixed) | `main` | `4b48507..d1e531f` | `5146857` `d1e531f` |

Reference: api-obsm `git show e3ba207:tests/_netguard.py` and its conftest hooks (the brief's pin), and api-obsm's own later fixes to that copy (`91781ef` psycopg seat, `02c9710` skip/xfail, `2d49c3f` `*_PROXY`), read at `2d49c3f`.

**How I ran it.** Extract root, every pytest through `/home/aditya/Code/pytest-slot.sh --`, one at a time: `DEBUG=false PYTHONPATH=<extract> flynapse-otel/.venv/bin/python -m pytest -p no:cacheprovider` (Python 3.11.15; that venv has no xdist, so lanes are serial). `flynapse_otel.__file__` printed inside the extract before each lane; rootdir = the extract. For the nested sessions the outer shell had every `FLYNAPSE_NETGUARD*` variable unset and `COLUMNS=500`. The one xdist probe used the api venv's pytest-xdist 3.8.0 with `PYTHONPATH` pinned to the extract (`flynapse_otel.__file__` confirmed in the extract).

**Lanes.** `5146857`: 2576 passed, 1 skipped, 1 xfailed, rc=0. `d1e531f`: 2576 passed, 1 skipped, 1 xfailed, rc=0 (55 s).

**Verdict: FIX-FIRST — 0 P0 · 1 P1 · 6 P2 · 3 P3.** The REFUSE half holds wherever I pushed it: every wrapped entry point, IPv6, mapped loopback, fork children, concurrent child logs, exact `unguarded` ids; 27 of 28 mutants are red. The FAIL half does not: a refusal inside a skipped or xfailed test is accounted and never reported (P1-1). And four of the five api r8 additions the ruling carries are NOT met — while api's OWN copy now meets them (`91781ef`, `02c9710`, `2d49c3f`), so adopting the shared guard as written and deleting api's copy, as the adoption notes say, would REGRESS api on three fixed findings.

**Adoption guidance.** Do not adopt in any consumer until P1-1 is fixed, and do not adopt in api until the shared guard is a superset of api's current copy: port `02c9710` (skip/xfail via `pytest_runtest_makereport`), `91781ef` (psycopg2 `connect` and psycopg 3 `Connection.connect`/`AsyncConnection.connect` as guarded seats, `parse_dsn`/`conninfo_to_dict` for host and port) and `2d49c3f` (every `*_proxy` variable REMOVED, `NO_PROXY` kept, pinned) — api's are the reference implementation, and api measured `240.0.0.1` routed on this kernel too and now uses `255.255.255.255` / `ff02::1`. The adoption notes must also say: serial lanes only until the session half reports through xdist (P2-3); list parametrized node ids one by one in `unguarded`; add `8050`.

---
## Findings, ranked

### No P0

### P1-1 (tier 1, severity 1): a refusal inside a skipped or xfailed test never fails anything (5146857)

**Where.** `network_plugin.py:77-104` (`_guarded_phase`). The refusals are collected in the `finally`, but `pytest.fail(...)` is reached only when `yield` did not raise. `Skipped` (from `pytest.skip()` in the body or a fixture), `XFailed` (`pytest.xfail()`) and any exception under `@pytest.mark.xfail` propagate through the `finally`, so the refusal is ACCOUNTED (`_ACCOUNTED`) and never reported — not even as a stray at session end. When an `xfail` test PASSES, the xfail plugin turns the wrapper's own `Failed` into XFAIL.

**Measured** (`ng/h1_skip`). Five shapes each reported SKIPPED or XFAIL: a refusal then `pytest.skip()`; a refusal in an `xfail` test that fails; a refusal in an `xfail` test that passes; a probe-and-skip fixture (`create_connection(("127.0.0.1", 6379))` caught, `pytest.skip("no redis")`); a refusal then `pytest.xfail()`. The control (a refusal, then pass) FAILED. Without the control the session exits **0** with five refusals recorded. api r8 P3-1 measured the same shape in api's copy; api fixed it in `02c9710`.

**Scenario.** The exact shape the guard exists for: a fixture that probes the dev Redis or the OTLP collector and skips when unreachable. Under the guard the probe is refused, the test skips, and the lane is green with "N skipped".

**Fix.** Port api `02c9710`: record unexpected refusals on the item in the `finally`, and fail the report in a `pytest_runtest_makereport` wrapper (`tryfirst`, so its second half runs last) when the phase skipped or the test is xfail. Prove each of the five shapes in a nested session.

### P2-1 (tier 2, severity 2): the ruling's api r8 additions are mostly unmet, and api's own copy is now ahead

See the checklist below. NOT met: wrapping `psycopg2.connect` — measured (`ng/h34`): `psycopg2.connect("host=127.0.0.1 port=5432 …")` reaches `psycopg2._connect` with zero refusals, so the docstring's "C-level sockets" limit is overstated for the one Python seat every repo's DB pool passes through; blanking `*_PROXY` — measured (`ng/h2_proxy`): a test-owned loopback proxy received `CONNECT cognito-idp.ap-south-1.amazonaws.com:443 HTTP/1.0` from `urllib.request`, zero refusals, and the test PASSED; `8050` (DynamoDB Local) is absent from `SERVICE_PORTS` and pinned out by `test_the_service_ports_are_the_dev_stacks`; skip/xfail (P1-1). **Tier 2 because the ruling says api's `_netguard.py` "is deleted at adoption"**: api now carries all three fixes, so adoption as written regresses api.

**Fix.** Port api `91781ef`, `2d49c3f` and `02c9710` (P1-1), and add `8050`. Then the shared guard is a superset of the reference and the deletion is safe.

### P2-2 (tier 1, severity 1): a port this process bound is "its own" by NUMBER only, and forever (network.py:391-398, :316)

**Measured** (`ng/h34`, raisers beneath). A UDP bind of `127.0.0.1:5432` succeeds while the live dev Postgres listens on TCP 5432, so `5432 in OWN_PORTS`, and then `create_connection(("127.0.0.1", 5432))` reaches the real function. The socket is closed and the port stays open. An IPv6 `::1` bind of 6006 opens IPv4 `127.0.0.1:6006`. A `127.0.0.2` bind of 11434 opens `127.0.0.1:11434`. The control (4317, bound by nobody) is refused.

**Scenario.** Any test that binds a service-port number on another protocol, family or loopback address — a UDP statsd or syslog double, or a deliberate two-liner — opens the LIVE dev service for the rest of the session.

**Fix.** Record `(family, type, address, port)` and match a connect against the same family, type and address. Prune on `close`/`detach`, or check that the socket is still live at `_check`. Pin it with the UDP and `::1` shapes.

### P2-3 (tier 1, severity 2): pytest-xdist workers lose the session-level half (network_plugin.py:154-179)

**Measured** (`ng/h6_xdist`). An import-time refusal: serial gives `2 passed, 1 network refusal`, rc=1; `-n 2` gives `2 passed`, rc=0. In a worker `terminalreporter` is None, and xdist discards the worker's `session.exitstatus`.

**Scenario.** The workspace CLAUDE.md prescribes `pytest -n 4` for big lanes, and module-level `_postgres_reachable()` probes (shift-optimizer, api integration) are exactly import- or collection-time refusals. Under `-n` they vanish.

**Fix.** In a worker, put the strays into `config.workeroutput`, and fail the session from a controller-side `pytest_testnodedown`. Until then the adoption notes must say "serial, or the session half is off".

### P2-4 (tier 1, severity 2): children that drop the guard are wider than `env={}` (network.py:35-36)

**Measured** (`ng/h8_children`).
- `python -I`, `-E` and `-S` children are unguarded.
- A child whose env OVERRIDES `PYTHONPATH` (`{**os.environ, "PYTHONPATH": "/some/repo"}`) is unguarded while `FLYNAPSE_NETGUARD=1` is still set.
- Appending to `PYTHONPATH` keeps the guard.

Seven spawn sites in the estate's tests override `PYTHONPATH`: copilot-mro 4 (including `fake_playwright_mcp_server.py`'s `{"PYTHONPATH": repo_root}`), api 2 and telegram-bot 1.

**Fix.** Declare the four shapes. Better, add a `subprocess.Popen` seat that re-inserts `SITE_DIRECTORY` when a child env carries `FLYNAPSE_NETGUARD=1` without it, and that records an "unguarded child" refusal for `-I`/`-E`/`-S`.

### P2-5 (tier 1, severity 2): per-phase ports are checked at connect time only, and refusals after `sessionfinish` are silent

- **Pooled reuse** (`ng/h9_pool`). A `phoenix`-marked test connects to a test-owned CHILD listener on 6006 (open in its phase) and keeps the socket in a module global. An UNMARKED test (6006 closed) sends on it: the listener received `from-B(closed-phase)`, with zero refusals and rc=0. Every consumer's DB, Redis and HTTP client is a pool, so the docs' "a child of any other test may not" overstates per-phase isolation. Declare it.
- **After the session** (`ng/h7_atexit`). A refusal in the conftest's `pytest_unconfigure` or in an `atexit` handler gives rc=0 and prints nothing, because the log is unlinked at `sessionfinish`. A conftest `trylast` `pytest_sessionfinish` WAS caught. The OTel SDK's `atexit` shutdown flush has exactly this shape in a session that opts out of `OTEL_SDK_DISABLED`, as flynapse-otel's own does. **Fix:** a guard-registered `atexit` hook that reports and exits non-zero on unaccounted refusals, plus a sweep in `pytest_unconfigure(trylast)`.

### P2-6 (tier 1, severity 1): the `/etc/hosts` loopback-name rule is unpinned in BOTH directions, and a name is never re-checked against what it resolves to (network.py:257-281, :310-315)

**Measured (mutants, full lane).**
- NG08 (no `/etc/hosts` name read: only `localhost`) SURVIVES the full lane (2576 passed).
- **NG08b (EVERY name in `/etc/hosts` allowed, whatever address it maps to) SURVIVES the full lane** (113 s, rc=0).

`_check` judges a NAME by that set and never by its resolution. `socket.connect(("name", port))` resolves in C and connects to whatever glibc sorts first.

**Scenario.** On a host whose `/etc/hosts` lists a LAN or Docker entry (`192.168.65.2 host.docker.internal`, `10.0.0.5 db.internal`), a regression to NG08b makes `connect(("db.internal", 5432))` a live off-box connect with no refusal, and no test notices. The same holds today, without any mutant, for a name that `/etc/hosts` maps to BOTH a loopback and a non-loopback address. This host's `/etc/hosts` maps only loopback addresses, so the dual case is structural and was not measured live.

**Fix.** Pin the rule with a synthetic hosts table (make `_loopback_names` take a path, and test a loopback line, a LAN line and a dual line). In `_check`, resolve a NAME through `_REAL["getaddrinfo"]` and require every result to be loopback.

### P3s

- **P3-1 (process; the ruling's `240.0.0.1`).** On this host `ip route get 240.0.0.1` returns `via 172.24.208.1 dev eth0`: 240/4 is ROUTED, so a connect to it leaves the VM. api r8 independently measured the same and moved to `255.255.255.255` / `ff02::1` (`2d49c3f` line). The shared guard's tests never depend on it (recorders sit beneath), which is the right design. Strike `240.0.0.1` from the ruling text. This was measured with the routing table only; no packet was sent.
- **P3-2 (process).** A mis-marked `network` test errors TWICE (`ng/h12_fork`). The marker failure is raised in the setup WRAPPER before pytest's own setup runs, which leaves a second `ERROR … KeyError: <StashKey>` at teardown. Fail after the `yield`, or from a plain `tryfirst` `pytest_runtest_setup`.
- **P3-3 (process).** A consumer test that monkeypatches a guarded entry point fails as "the network guard was uninstalled during call". That fails closed, but it misleads. One such site exists in the estate (copilot-mro `test_lang_agent_wrapper_checkpoint.py:701` patches `socket.create_connection`). Name `_REAL` as the seam in the message.

---
## api r8 additions checklist (ruling §4a-bis M-SHARED-NETGUARD)

| addition | shared guard at `d1e531f` | evidence | api's own copy |
|---|---|---|---|
| wrap `psycopg2.connect` (and psycopg 3) | **NOT MET** | no `psycopg` in `network.py` or `network_plugin.py`; `ng/h34` reaches `psycopg2._connect` with 0 refusals; "C-level only" is overstated | met, `91781ef` (+ `799dee7` pin) |
| blank the `*_PROXY` variables | **NOT MET** | no proxy handling; `ng/h2_proxy`: `CONNECT cognito-idp…:443`, 0 refusals, PASSED | met, `2d49c3f` (removed, `NO_PROXY` kept) |
| fail on refusals inside skipped or xfailed tests | **NOT MET** | P1-1: five shapes, session rc=0 | met, `02c9710` |
| raw-socket self-tests at a locally refused address | **MET DIFFERENTLY (stronger)** | recorders beneath the real module attributes (`test_the_real_module_attributes_are_wrapped_end_to_end`, the `recorders` fixture); `240.0.0.1` is routed here anyway | moved to `255.255.255.255` / `ff02::1` |
| DynamoDB Local `8050` in the port table | **NOT MET** | ten entries, pinned by equality, no 8050 | — |
| (r8 P3-3) `-I`/`-E`/`-S` and scrubbed-env children | **PARTLY** | `env={}` declared; the flags and a `PYTHONPATH` override not (P2-4) | — |
| (r8 P3-12) the `_REAL` stub seam documented | **MET** | named in the module docstring; the misleading message remains (P3-3) | — |
| (r8 P3-13) the site directory first on `PYTHONPATH` | **MET** | `guard_session` prepends it; pinned; NG20 red | — |

## `_netguard.py` behaviour diff (api `e3ba207` → shared `d1e531f`)

| behaviour | api `_netguard.py` + conftest at `e3ba207` | shared guard at `d1e531f` | note |
|---|---|---|---|
| allowed set | loopback plus `/etc/hosts` loopback names | same | shared adds `rstrip(".")` and a latin-1 bytes decode; neither pins the hosts filter (P2-6) |
| service ports | the same ten | the same ten | neither has 8050 |
| port openings | conftest `_SERVICE_PORT_OPT_INS`, by lane prefix, per phase | `NetworkPolicy`: by marker, lane or session; validated and frozen | shared is wider |
| own-bound ports | none | `OWN_PORTS`, by number | shared adds P2-2 |
| wrapped | 5 lookups × 2 modules, `connect`/`connect_ex`/`sendto`/`sendmsg`, the raw `_socket.socket` | + `bind`, `create_connection`, asyncio `open_connection` × 2, `BaseEventLoop.create_connection` | shared is wider |
| install | at import whenever the env var is set | refused outside pytest or a guarded child | shared is safer |
| children | `sitecustomize` by path, env vars, session log | same design, the `_flynapse_netguard` alias, one instance on package import | equal; both lose `-I`/`-E`/`-S` and `PYTHONPATH`-override children |
| refusal record | `(test, kind, host, port)` | `Refusal(test, kind, host, port, thread)` | shared names the thread |
| phase enforcement | conftest wrappers, the same `finally` shape | plugin wrappers, the same `finally` shape | BOTH had P1-1 at `e3ba207`; api fixed it in `02c9710` |
| the marker opt-out | one allowlisted test by node id | `unguarded` node ids, exact | equal |
| strays | conftest `pytest_sessionfinish` | plugin `pytest_sessionfinish(trylast)` plus a final-line tag | equal; both are blind to `unconfigure`/`atexit` and to xdist workers |
| env pins | set in the conftest | forced or defaulted by `guard_session` | equal |
| proxies, psycopg | not handled at `e3ba207` | not handled | api fixed both since; shared lags |
| concurrent child log | one `write()` per line, `O_APPEND` | same | `ng/h8_children`: 1200 of 1200 lines intact from 3 children |

---
## What I tried to break and could not

- **Every entry point refuses before anything leaves**: the implementer's 37-case table, plus my IPv6, mapped and raw variants on the same recorders. NG03, NG04, NG12, NG18, NG23 and NG24 are red.
- **Fork children** (`ng/h12_fork`): a forked child's swallowed refusal fails the parent's phase.
- **Concurrent child logs** (`ng/h8_children`): three children × 400 refusals give 1200 parsed entries and 0 malformed lines.
- **`unguarded` matching** (`ng/h12_fork`): exact; a parametrized `test_param[1]` is NOT lifted by `test_param`, and a substring is not lifted (fail closed).
- **A conftest `trylast` `pytest_sessionfinish`** is still caught as a stray.
- **27 of 28 mutants red** (aimed at `test_network_guard.py`, `test_network_guard_sessions.py` and `test_testing_package_isolation.py`; baseline 15 s green). See the appendix.

## What I did not test

- The dual-mapped `/etc/hosts` name, live (it needs an edited hosts file; P2-6 is structural plus the NG08b mutant).
- A DNS query sent by hand to a loopback resolver.
- uvloop or a custom event-loop policy.
- `guard_session` inside an in-process `pytester.runpytest()`, which could clobber the parent's `LOG_VARIABLE`/`POLICY`. The suite uses `runpytest_subprocess` only.
- Kill REASONS per mutant: `mutant.sh` records only the result line. The kills are aimed, and each was in the file that pins its behaviour.

---
## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier is §2.3a's: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk F3 = the residual (test hygiene).

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N1-01 | flynapse-otel | `network_plugin.py:60-105` | A phase during which a refusal was recorded FAILS "whether or not anything noticed it" | plan, docstring | Five skip/xfail shapes exit 0 (`ng/h1_skip`); the control fails | the sessions tests (no skip/xfail case) | not applicable: no guard exists | 1 | 1 | F3 | **REFUTED** (P1-1) |
| N1-02 | flynapse-otel | `network.py:242-281` | Loopback only, mapped loopback, no private range, `/etc/hosts` loopback names | ruling | Refuse half holds on every probe; the hosts filter is unpinned both ways | `test_every_entry_point_refuses_before_anything_leaves`, `test_loopback_passes_through_to_the_real_functions` | yes: NG02, NG03, NG17, NG24, NG28 red. **NG08 and NG08b survive the full lane** | 1 | 0 (address rule) / 1 (hosts) | F3 | **SETTLED for addresses; OPEN for hosts names** (P2-6) |
| N1-03 | flynapse-otel | `network.py:310-321`, `:391-398` | Service ports refused on loopback unless opened; a port this process bound is its own | ruling | UDP, `::1` and `127.0.0.2` binds open the live port NUMBER for TCP loopback, never pruned (`ng/h34`) | `test_a_port_this_process_bound_is_its_own`, `test_every_service_port_is_refused_on_loopback` | yes: NG01, NG05, NG15, NG16 red (the rule exists); the hole has no guard | 1 | 1 | F3 | **PARTIAL** (P2-2) |
| N1-04 | flynapse-otel | `network.py:44-48` | Declared limit: C-level sockets only | docstring | `psycopg2.connect` is Python and unwrapped (`ng/h34`); api wrapped it (`91781ef`) | none | not applicable | 2 | 2 | F3 | **OPEN** (P2-1; api r8 (a)) |
| N1-05 | flynapse-otel | `network.py` (no proxy handling) | "a test never reaches beyond this machine" | docstring | A loopback proxy carried `CONNECT cognito…:443`, 0 refusals (`ng/h2_proxy`); api fixed it (`2d49c3f`) | none | not applicable | 2 | 2 | F3 | **OPEN** (P2-1; api r8 (b)) |
| N1-06 | flynapse-otel | `network.py:103-114` | `SERVICE_PORTS` = the dev stack | ruling | 8050 is absent | `test_the_service_ports_are_the_dev_stacks` | not applicable | 3 | 1 | F3 | **OPEN** (api r8 (e)) |
| N1-07 | flynapse-otel | `network.py:347-477`; `tests/unit/testing/test_network_guard.py:88-115`, `:335-435` | Every listed entry point is wrapped; a broken guard reaches a recorder, never a packet | plan | Recorders beneath `_REAL` and beneath the real module attributes | `test_the_real_module_attributes_are_wrapped_end_to_end`, `test_installed_is_false_while_any_one_entry_point_is_unguarded` | yes: NG04, NG12, NG18, NG23 red | 1 | 0 | F3 | **SETTLED** (api r8 (d) met differently) |
| N1-08 | flynapse-otel | `network.py:32-36`, `:567-588`; `_network_site/sitecustomize.py` | Every child installs the guard; `env={}` declared | plan | `-I`/`-E`/`-S` and `PYTHONPATH`-override children are unguarded; 7 estate spawn sites override `PYTHONPATH` (`ng/h8_children`) | `test_this_session_and_its_children_run_behind_the_guard` | yes, for the declared path: NG19, NG20 red | 2 | 1 | F3 | **PARTIAL** (P2-4) |
| N1-09 | flynapse-otel | `network_plugin.py:123-179` | A refusal outside every phase fails the session, tagged on the final line | plan | Serial: yes. `-n 2`: rc=0, silent (`ng/h6_xdist`). `unconfigure`/`atexit`: rc=0 (`ng/h7_atexit`) | the collection, session-end and child sessions tests | yes, serial: NG21, NG27 red | 2 | 0 (serial) / 1 (xdist, atexit) | F3 | **PARTIAL** (P2-3, P2-5) |
| N1-10 | flynapse-otel | `network_plugin.py:76-81` | Ports opened per PHASE; "a child of any other test may not" reach them | plan | A socket opened in an open phase serves a closed phase (`ng/h9_pool`) | the ports sessions test | yes: NG10 red (connect-time rule) | 2 | 1 | F3 | **PARTIAL** (P2-5: declare) |
| N1-11 | flynapse-otel | `network_plugin.py:62-70` | `network` lifts only for exact `unguarded` ids | plan | Neither a param id nor a substring is lifted; a spurious second `KeyError` ERROR per mis-marked test | the marker sessions test | yes: NG13 red | 1 | 0 | F3 | **SETTLED** (P3-2 noise) |
| N1-12 | flynapse-otel | `network.py:324-341`, `:541-561`; `network_plugin.py:86-96` | Children append one JSON line per refusal; the parent reads its window; expected refusals are not held against a test | plan | 1200/1200 lines from 3 concurrent children; a forked child caught | the child sessions tests | yes: NG09, NG22, NG25 red | 1 | 0 | F3 | **SETTLED** |
| N1-13 | flynapse-otel | `network.py:163-236` | `NetworkPolicy` is validated and frozen; only service ports can be opened; lanes match by prefix | plan | The implementer's seven refusals plus mutants | `test_a_policy_that_opens_nothing_real_is_refused`, `test_a_policy_opens_a_tests_session_lane_and_marker_ports_by_exact_name` | yes: NG11, NG16 red | 1 | 0 | F3 | **SETTLED** |
| N1-14 | flynapse-otel | `network.py:567-588` | `guard_session` forces AWS metadata off, defaults OTel off, and puts the site dir first | plan | Mutants | `test_the_environment_pins`, `test_this_session_and_its_children_run_behind_the_guard` | yes: NG07, NG20, NG26 red | 1 | 0 | F3 | **SETTLED** |
| N1-15 | flynapse-otel | `network.py:439-450`; `tests/unit/packaging/test_testing_package_isolation.py` | `install()` refused outside a test process; the three modules isolated | plan | Mutant | the isolation file | yes: NG06 red | 1 | 0 | F3 | **SETTLED** |
| N1-16 | flynapse-otel | `network_plugin.py:97-98` | A phase that left the guard uninstalled fails | plan | Mutant | `test_an_uninstall_cannot_outlast_its_test` | yes: NG14 red | 1 | 0 | F3 | **SETTLED** |
| N1-17 | flynapse-otel | `5146857`, `d1e531f` | Green at their own HEADs | process | 2576 passed, rc=0 at both | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |
| N1-18 | workspace | plan §4a-bis M-SHARED-NETGUARD | "api's `_netguard.py` is the reference and is deleted at adoption" | ruling | api's copy now carries the three fixes the shared copy lacks (`91781ef`, `02c9710`, `2d49c3f`); deleting it regresses api | none | not applicable | 1 | 2 | F3 | **OPEN** (adoption order: port first) |

**Tier 0 (settled by guards I SAW fail):** N1-07, N1-11, N1-12, N1-13, N1-14, N1-15, N1-16, and the address limb of N1-02 and the serial limb of N1-09. These properties do not go to Fable.

---
## Open claims, tier 2 first

**Tier 2**
1. **N1-18 / P2-1: adoption order.** Port api `02c9710`, `91781ef` and `2d49c3f` into the shared guard before any consumer adopts it, and before api deletes its copy.
2. **N1-04, N1-05:** the psycopg seat and the proxy variables (the same port).

**Tier 1**
1. **N1-01 (P1-1):** skip/xfail swallows a refusal.
2. **N1-02 hosts limb (P2-6):** the `/etc/hosts` filter is unpinned (NG08/NG08b survive), and names are never re-checked against their resolution.
3. **N1-03 (P2-2):** own ports by number.
4. **N1-09 (P2-3, P2-5):** xdist workers; `unconfigure`/`atexit`.
5. **N1-08 (P2-4):** `-I`/`-E`/`-S` and `PYTHONPATH`-override children.
6. **N1-10 (P2-5):** pooled connections outlive the phase (declare).
7. **N1-06, P3-1 (strike `240.0.0.1`), P3-2, P3-3.**

---
## Appendix: mutation battery (30 runs on `d1e531f`)

`~/.claude/scratch/obs-merge/otel-review-r7/mut/ng/`. There is one baseline (the aimed command, green, 15 s), then each mutant runs with `mutant.sh -B`: aimed at the two guard test files plus the isolation file, `-x`, cold bytecode, md5-verified restore. The survivors were re-run against the FULL lane.

| mutant | what it breaks | result |
|---|---|---|
| NG01 | no service-port rule | KILLED |
| NG02 | private ranges allowed | KILLED |
| NG03 | IPv6 endpoints unchecked | KILLED |
| NG04 | `sendto` unchecked | KILLED |
| NG05 | `bind` not recorded in OWN_PORTS | KILLED |
| NG06 | `install()` anywhere | KILLED |
| NG07 | AWS metadata pin only defaulted | KILLED |
| **NG08** | `/etc/hosts` names not read (localhost only) | **SURVIVED aimed and on the FULL lane (2576 passed)** |
| **NG08b** | EVERY `/etc/hosts` name allowed, whatever it maps to | **SURVIVED on the FULL lane** |
| NG09 | a refusal not written to the session log | KILLED |
| NG10 | markers ignored when opening ports | KILLED |
| NG11 | a lane prefix matched by equality | KILLED |
| NG12 | `installed()` blind to the raw type | KILLED |
| NG13 | the marker check off | KILLED |
| NG14 | the uninstalled check off | KILLED |
| NG15 | own ports ignored | KILLED |
| NG16 | any port openable | KILLED |
| NG17 | a trailing dot kept on names | KILLED |
| NG18 | the loop's `create_connection` unchecked | KILLED |
| NG19 | the child's site alias not registered | KILLED |
| NG20 | the site dir last on `PYTHONPATH` | KILLED |
| NG21 | strays never fail the session | KILLED |
| NG22 | a child's refusals not read in its phase | KILLED |
| NG23 | `connect_ex` unchecked | KILLED |
| NG24 | lookups' name check off | KILLED |
| NG25 | expected refusals held against the test | KILLED |
| NG26 | the OTel pin forced | KILLED |
| NG27 | the thread name dropped | KILLED |
| NG28 | a mapped address refused outright | KILLED |
