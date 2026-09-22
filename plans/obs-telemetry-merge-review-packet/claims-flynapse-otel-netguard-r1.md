# Claims packet: flynapse-otel review — network guard r1 (M-SHARED-NETGUARD, `5146857` + `d1e531f`)

**PARTIAL — in progress (PAUSED by the owner 2026-09-22; resume from `~/.claude/scratch/obs-merge/otel-review-r7/PAUSED.md`).** Independent adversarial review by Opus, 2026-09-22. Read-only throughout: no code tree edited, checked out, stashed or committed; no docker, no DB, no live network. Every probe ran as a NESTED pytest session under the extract's own `guard_session` with raisers beneath `_REAL` (the sessions test's own conftest) or, where a real loopback socket was needed, against a test-owned loopback listener; nothing left this VM. The mutation battery (28 mutants, specs written) was interrupted by the pause after ONE result (NG03 KILLED); the extract's three guard files were md5-verified against the `d1e531f` blobs after the kill (all MATCH).

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` | `main` | `4b48507..d1e531f` | `5146857` `d1e531f` |

Reference: api-obsm `git show e3ba207:tests/_netguard.py` and its conftest hooks (`_guarded_phase`, `_stray_refusals`, `pytest_sessionfinish`), plus the api r8 additions the §4a-bis ruling carries.

**Baseline at `d1e531f`: 2576 passed, 1 skipped, 1 xfailed, rc=0** (`5146857`: 2576 passed, rc=0). Probe sessions: `scratchpad/otel-review-r7/ng/h*` (each a conftest + one test file; `run.sh <dir>` runs it through the slot script).

**Verdict so far: FIX-FIRST (provisional — 0 P0 · 1 P1 · 5 P2 · 4 P3; the mutation battery is owed).** The REFUSE half is as claimed wherever I pushed it (every entry point, IPv6, mapped loopback, fork children, concurrent child logs, exact `unguarded` ids). The FAIL half is not: a refusal inside a skipped or xfailed test — the exact api r8 addition the ruling carries — is silently accounted, and four of the five api r8 additions are not met. Adoption verdict so far: **do not adopt in the consumers until P1-1 is fixed**; the rest can land as declared limits or follow-ups.

---
## Findings, ranked

### No P0

### P1-1 (tier 1, severity 1): a refusal inside a skipped or xfailed test never fails anything (5146857)

**Where.** `network_plugin.py:77-104` (`_guarded_phase`): the refusals are collected in the `finally`, but `pytest.fail(...)` is reached only when `yield` did not raise. `Skipped` (a `pytest.skip()` in the body or in a fixture, a `skipif` condition), `XFailed` (`pytest.xfail()`), and any exception under `@pytest.mark.xfail` propagate through the `finally`, so the refusal is ACCOUNTED (`_ACCOUNTED`) and never reported — it is not even a stray at session end. With a PASSING body under `@pytest.mark.xfail`, the wrapper's own `Failed` is turned into XFAIL by the xfail plugin.

**Measured** (`ng/h1_skip`): five shapes — refusal then `pytest.skip()`; refusal in an `xfail` test that fails; refusal in an `xfail` test that passes; a probe-and-skip fixture (`create_connection(("127.0.0.1", 6379))` caught, `pytest.skip("no redis")`); refusal then `pytest.xfail()` — all reported SKIPPED/XFAIL; the control (refusal then pass) FAILED. Without the control the session exits **0** with five refusals recorded.

**Scenario.** The exact shape the guard was built against: a fixture probing the dev Redis or OTLP collector and skipping when unreachable. Under the guard the probe is refused, the test skips, and the lane is green with "N skipped" — the pre-guard world with a different word.

**Fix.** In the `finally`, when unexpected refusals were recorded, raise the phase failure REGARDLESS of what `yield` raised (chain the original as `__context__`), and mark the item so `pytest_runtest_makereport` turns an xfail into a failure. api r8 asked for exactly this (P3-1 there); the ruling lists it. Prove it with a nested session per shape.

### P2-1 (tier 1, severity 2): the api r8 additions the ruling carries are mostly not met

See the checklist below. Not met: wrap `psycopg2.connect` (H3: `psycopg2.connect("host=127.0.0.1 port=5432 …")` reaches `_connect` with zero refusals — the "C-level only" limit is overstated for the one Python seat every repo's DB access passes through); blank `*_PROXY` (H2: a loopback fake proxy received `CONNECT cognito-idp.ap-south-1.amazonaws.com:443` from `urllib.request` with zero refusals and the test PASSED); DynamoDB Local `8050` absent from `SERVICE_PORTS`; skip/xfail (P1-1). Met differently: the raw-socket self-tests use recorders beneath the real module attributes (stronger than `240.0.0.1`, and necessary — see P3-1).

### P2-2 (tier 1, severity 1): a port this process bound is "its own" by NUMBER only, and forever (network.py:391-398, 316)

**Measured** (`ng/h34`, raisers beneath): a UDP bind of `127.0.0.1:5432` succeeds while the LIVE dev Postgres listens on TCP 5432 → `5432 in OWN_PORTS` → `create_connection(("127.0.0.1", 5432))` reaches the real function; the socket is closed, the port stays open. An IPv6 `::1` bind of 6006 opens IPv4 `127.0.0.1:6006`; a `127.0.0.2` bind of 11434 opens `127.0.0.1:11434`. The control (4317, nobody bound) is refused.

**Scenario.** A test-owned UDP server (a statsd/syslog/DNS double) on port 0 lands in the ephemeral range — only 50051 is inside it, the declared exemption — but any test that binds a service port on another family, protocol or loopback address opens the LIVE service for the rest of the session, and a deliberate two-liner does it on purpose.

**Fix.** Record `(family, type, address, port)` and match the connect against the same family/type on the same address; prune on `close` (wrap `close`/`detach`, or check `sock.fileno()` liveness at `_check`). Pin with the UDP and `::1` shapes.

### P2-3 (tier 1, severity 2): pytest-xdist workers lose the session-level half (network_plugin.py:154-179)

**Measured** (`ng/h6_xdist`, api venv's xdist 3.8.0): an import-time refusal — serial: `2 passed, 1 network refusal`, rc=1; `-n 2`: `2 passed`, rc=0. In a worker `terminalreporter` is None and the worker's `session.exitstatus` is discarded by xdist.

**Scenario.** The workspace CLAUDE.md prescribes `pytest -n 4` for big lanes; shift-optimizer's and api's module-level `_postgres_reachable()` probes are exactly import/collection-time refusals. They vanish under `-n`.

**Fix.** In a worker, put the strays into `config.workeroutput` and have a controller-side `pytest_testnodedown` fail the session (the CLAUDE.md names the mechanism); until then, the adoption notes must say "serial, or the session half is off".

### P2-4 (tier 1, severity 2): children that drop the guard are wider than "env={}" (network.py:35-36, docs)

**Measured** (`ng/h8_children`): `python -I`, `-E`, `-S` → unguarded; an env that OVERRIDES `PYTHONPATH` (`{**os.environ, "PYTHONPATH": "/some/repo"}`) → unguarded while `FLYNAPSE_NETGUARD=1` is still set; appending to PYTHONPATH keeps it. Seven such spawn sites exist in the estate's tests (copilot-mro 4 incl. `fake_playwright_mcp_server.py`'s `{"PYTHONPATH": repo_root}`, api 2, telegram-bot 1).

**Fix.** Declare the four shapes; better, a `subprocess.Popen` audit seat that re-inserts `SITE_DIRECTORY` when the child env carries `FLYNAPSE_NETGUARD=1` without it, and records an "unguarded child" refusal for `-I`/`-E`/`-S` (api r8 P3-3's suggestion).

### P2-5 (tier 1, severity 2): a connection opened in an open phase serves the closed phases; `pytest_unconfigure`/`atexit` refusals are silent

- **Pooled reuse** (`ng/h9_pool`): a `phoenix`-marked test connects to a test-owned CHILD listener on 6006 (open in its phase) and keeps the socket in a module global; an UNMARKED test (6006 closed) sends on it — the listener received `from-B(closed-phase)`, zero refusals, rc=0. Every consumer's DB/Redis/HTTP client is a pool; the per-phase port rule is connect-time only. Declare it (the docs currently imply per-phase isolation: "a child of any other test may not").
- **After the session** (`ng/h7_atexit`): a refusal in the conftest's `pytest_unconfigure` or in an `atexit` handler → rc=0, nothing printed (the log is unlinked at `sessionfinish`; a `trylast` `pytest_sessionfinish` of the conftest WAS caught). The OTel SDK's `atexit` shutdown flush is exactly this shape for a session that opts out of `OTEL_SDK_DISABLED` (as flynapse-otel's own does). Fix: a guard-registered `atexit` (registered at conftest import, so it runs last) that prints and `os._exit(1)`s on unaccounted refusals; a second sweep in `pytest_unconfigure(trylast)`.

### P3s

- **P3-1 (docs/process, the ruling's `240.0.0.1`).** On this host `ip route get 240.0.0.1` → `via 172.24.208.1 dev eth0`: 240/4 is ROUTED (modern Linux treats it as unicast), so a connect to it sends a SYN off the VM to the Windows host. The api r8 premise "Linux refuses to route 240/4 locally" is false here. The shared guard's tests never depend on it (recorders beneath), which is the right design; the ruling text and api's own tests should drop the `240.0.0.1` idea. (Measured with the routing table only; no packet was sent.)
- **P3-2 (process).** A mis-marked `network` test errors TWICE: the marker failure raised in the setup WRAPPER before pytest's own setup ran leaves a second `ERROR … KeyError: <StashKey>` at teardown (`ng/h12_fork`). Fail after the `yield` instead, or from a plain `tryfirst` `pytest_runtest_setup`.
- **P3-3 (docs).** A name's verdict is never re-checked against its RESOLUTION (`_check` judges `localhost` and `/etc/hosts` loopback names by name; `socket.connect(("name", p))` resolves in C and connects to whatever glibc sorts first). Harmless on this host (`/etc/hosts` maps the hostname to 127.0.1.1 only) but a dual-mapped name (Docker Desktop's `host.docker.internal` lines, a LAN entry for the hostname) connects by name to the non-loopback address with no refusal. Not measured live (would need an edited hosts file). Declare, or resolve a NAME through `_REAL["getaddrinfo"]` inside `_check` and require every result loopback.
- **P3-4 (process).** A consumer test that monkeypatches a guarded entry point fails as "the network guard was uninstalled during call" — fail closed but misleading (api P3-12). One such site in the estate (copilot-mro `test_lang_agent_wrapper_checkpoint.py:701` patches `socket.create_connection`). Name `_REAL` as the seam in the message.

---
## api r8 additions checklist

| addition (ruling §4a-bis + api r8 rows) | shared guard | evidence |
|---|---|---|
| wrap `psycopg2.connect` (and `psycopg.connect`) | **NOT MET** | no `psycopg` in `network.py`/`network_plugin.py`; H3 reaches `psycopg2._connect` with 0 refusals; the docstring's "C-level sockets" limit is overstated for this Python seat |
| blank `*_PROXY` / `ALL_PROXY` | **NOT MET** | no `PROXY` in the guard; H2: loopback proxy received `CONNECT cognito-idp…:443`, 0 refusals, test PASSED |
| fail on refusals inside skipped or xfailed tests | **NOT MET** | P1-1, five shapes, session rc=0 |
| aim raw-socket self-tests at `240.0.0.1`; probes raise when `_REAL` is empty | **MET DIFFERENTLY (stronger)** | recorders beneath the real module attributes in `test_the_real_module_attributes_are_wrapped_end_to_end` and the `recorders` fixture; `240.0.0.1` is routed on this host anyway (P3-1) |
| DynamoDB Local `8050` in the port table | **NOT MET** | `SERVICE_PORTS` has ten entries, no 8050; `test_the_service_ports_are_the_dev_stacks` pins the ten |
| declare or refuse `-I`/`-E`/`-S` and scrubbed-env children (r8 P3-3) | **PARTLY** | `env={}` declared; `-I`/`-E`/`-S` and a PYTHONPATH override not (P2-4) |
| document the `_REAL` stub seam (r8 P3-12) | **MET** | module docstring names `_REAL` as the recorder seam; the misleading "uninstalled" message remains (P3-4) |
| "first on PYTHONPATH" made true (r8 P3-13) | **MET** | `guard_session` prepends `SITE_DIRECTORY`; pinned by `test_this_session_and_its_children_run_behind_the_guard` |

## `_netguard.py` behaviour diff (api `e3ba207` → shared `d1e531f`)

| behaviour | api `_netguard.py` + conftest | shared guard | note |
|---|---|---|---|
| allowed set | loopback + `/etc/hosts` loopback names | same | shared adds `rstrip(".")` and latin-1 bytes decode |
| service ports | same ten | same ten | neither has 8050 |
| port openings | conftest `_SERVICE_PORT_OPT_INS` by lane prefix, per phase | `NetworkPolicy`: by marker, lane, session; validated, frozen | shared is strictly wider |
| own-bound ports | none (a test server on 50051 would be refused) | `OWN_PORTS` by number | shared adds the hole in P2-2 |
| wrapped | 5 lookups ×2, `connect`/`connect_ex`/`sendto`/`sendmsg`, raw `_socket.socket` | + `bind`, `create_connection`, asyncio `open_connection` ×2, `BaseEventLoop.create_connection` | shared is wider (r7 P2-2 of api asked for these) |
| install guard | anywhere (`install()` at import when the env var is set) | refused outside pytest/a guarded child | shared is safer |
| children | `sitecustomize` by path, env vars, session log | same design, alias `_flynapse_netguard`, same-instance guarantee on package import | equal; both lose `-I`/`-E`/`-S`/PYTHONPATH-override children |
| refusal record | `(test, kind, host, port)` | `Refusal(test, kind, host, port, thread)` | shared names the thread |
| phase enforcement | conftest wrappers, same `finally` shape | plugin wrappers, same `finally` shape | BOTH have P1-1 (api r8 P3-1 found it there) |
| marker opt-out | one allowlisted test by node id | `unguarded` node ids, exact | equal |
| strays | conftest `pytest_sessionfinish` | plugin `pytest_sessionfinish(trylast)` + final-line tag | equal; both blind to `unconfigure`/`atexit` and to xdist workers |
| env pins | `AWS_EC2_METADATA_DISABLED`, `OTEL_SDK_DISABLED` in conftest | forced / defaulted by `guard_session` | equal |
| proxies | not blanked (r8 P3-2) | not blanked | equal — NOT MET |
| psycopg2 | not wrapped (r8 P2-2) | not wrapped | equal — NOT MET |
| concurrent child log | single `write()` per line, O_APPEND | same | H10: 1200/1200 lines intact from 3 children |

So the shared guard matches api's reference everywhere and exceeds it on scope, policy shape and install safety; it inherits api's three open holes (skip/xfail, proxies, psycopg2) and adds one of its own (own-port by number).

---
## What I tried to break and could not

- **Every entry point refuses before anything leaves** — the implementer's 37-case table plus my raw/IPv6/mapped variants ride the same recorders; nothing reached a recorder in any probe of mine.
- **Fork children** (`ng/h12_fork`): an `os.fork()` child's swallowed refusal fails the parent's phase (its pid differs; the log is shared).
- **Concurrent child logs** (`ng/h8_children`): three children × 400 refusals → 1200 parsed entries, 0 malformed lines.
- **`unguarded` matching** (`ng/h12_fork`): exact node id; a parametrized `test_param[1]` is NOT lifted by `test_param`; a substring is not lifted. (Fail closed; the adoption notes should say param ids are listed one by one.)
- **A `trylast` `pytest_sessionfinish` in the conftest** is still caught as a stray (the plugin's own `trylast` impl runs after it).
- **`installed()`** sees each of the 21 entry points one by one (the implementer's parametrized test; I read it, did not mutate yet).

## What I did not test (TODO at resume)

- The 28-mutant netguard battery (`scratchpad/otel-review-r7/mut/ng/`, specs + `run.sh`; results file has NG03 KILLED only; NG01/NG02 were interrupted mid-run and must be re-run): NG01 service-port rule off, NG02 private allowed, NG04 sendto, NG05 bind not recorded, NG06 install anywhere, NG07 AWS pin defaulted, NG08 hosts names not read, NG09 log not written, NG10 markers ignored, NG11 lane prefix equality, NG12 installed ignores raw type, NG13 marker check off, NG14 uninstalled check off, NG15 own ports ignored, NG16 any port openable, NG17 trailing dot, NG18 loop create_connection, NG19 site alias, NG20 site dir not first, NG21 strays never fail, NG22 child refusals not read in phase, NG23 connect_ex, NG24 name check off, NG25 expected held against test, NG26 OTel pin forced, NG27 thread name, NG28 mapped refused.
- The dual-mapped `/etc/hosts` name live (P3-3 is structural).
- A DNS query sent by hand to a loopback resolver (the forwarder class of P2-1's proxy; not probed).
- uvloop / a custom loop; `http.client` keep-alive through a fixture beyond the socket-level H9.
- The isolation guard's new rows (`test_testing_package_isolation.py` at 5146857) beyond reading them.
- Whether `guard_session` in a nested in-process `pytester.runpytest()` (not subprocess) would clobber the parent's `LOG_VARIABLE`/`POLICY` — the suite uses `runpytest_subprocess` only.

---
## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk F3 = residual (test hygiene).

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N1-01 | flynapse-otel | `network_plugin.py:60-105` | A phase during which a refusal was recorded FAILS, "whether or not anything noticed it" | plan, docstring | Five skip/xfail shapes exit 0 (`ng/h1_skip`); the control fails | sessions tests (no skip/xfail case) | not applicable (no guard exists) | 1 | 1 | F3 | **REFUTED** (P1-1) |
| N1-02 | flynapse-otel | `network.py:242-281` | Loopback only, `/etc/hosts` loopback names, mapped loopback, no private range | ruling | Implementer's table + my probes; NG03 (IPv6 unchecked) KILLED | `test_every_entry_point_refuses_before_anything_leaves` | partly: NG03 red; NG02/NG08/NG17/NG24/NG28 TODO | 1 | 0 (NG03) / 1 | F3 | **SETTLED for IPv6; rest ASSERTED** |
| N1-03 | flynapse-otel | `network.py:310-321`, `:391-398` | Service ports refused on loopback unless opened; a port this process bound is its own | ruling | UDP/IPv6/`127.0.0.2` binds open the LIVE port number for TCP loopback, never pruned (`ng/h34`) | `test_a_port_this_process_bound_is_its_own` | TODO (NG01, NG05, NG15, NG16) | 1 | 1 | F3 | **PARTIAL** (P2-2) |
| N1-04 | flynapse-otel | `network.py:44-48` (docstring) | Declared limit: C-level sockets only | docstring | `psycopg2.connect` is Python and unwrapped (`ng/h34` H3) | none | not applicable | 2 | 1 | F3 | **OPEN** (P2-1; api r8 (a)) |
| N1-05 | flynapse-otel | `network.py` (no proxy handling) | "a test never reaches beyond this machine" | docstring | Loopback proxy carried `CONNECT cognito…:443`, 0 refusals (`ng/h2_proxy`) | none | not applicable | 2 | 1 | F3 | **OPEN** (P2-1; api r8 (b)) |
| N1-06 | flynapse-otel | `network.py:103-114` | `SERVICE_PORTS` = the dev stack | ruling | 8050 absent | `test_the_service_ports_are_the_dev_stacks` | not applicable | 3 | 1 | F3 | **OPEN** (api r8 (e)) |
| N1-07 | flynapse-otel | `tests/unit/testing/test_network_guard.py:88-115`, `:335-435` | Broken guard reaches a recorder, never a packet | plan | Recorders beneath `_REAL` and beneath the real module attributes in the child | the same | TODO (NG battery) | 1 | 1 | F3 | **SETTLED in substance** (api r8 (d) met differently; `240.0.0.1` is routed here) |
| N1-08 | flynapse-otel | `network.py:32-36`, `_network_site/sitecustomize.py` | Every child installs the guard; `env={}` declared | plan | `-I`/`-E`/`-S`/PYTHONPATH-override children unguarded; 7 estate spawn sites override PYTHONPATH (`ng/h8_children`) | `test_this_session_and_its_children_run_behind_the_guard` | TODO (NG19, NG20) | 2 | 1 | F3 | **PARTIAL** (P2-4) |
| N1-09 | flynapse-otel | `network_plugin.py:154-179` | A refusal outside every phase fails the session, tagged on the final line | plan | Serial: yes (rc=1, tag); `-n 2`: rc=0 silent (`ng/h6_xdist`); `unconfigure`/`atexit`: rc=0 (`ng/h7_atexit`) | sessions tests (collection, session-end, child) | TODO (NG21, NG27) | 2 | 1 | F3 | **PARTIAL** (P2-3, P2-5) |
| N1-10 | flynapse-otel | `network_plugin.py:76-81` | Ports opened per PHASE; "a child of any other test may not" reach them | plan | A socket opened in an open phase serves a closed phase (`ng/h9_pool`) | ports session test | TODO (NG10) | 2 | 1 | F3 | **PARTIAL** (P2-5: declare) |
| N1-11 | flynapse-otel | `network_plugin.py:62-70` | `network` lifts only for exact `unguarded` ids | plan | Param id and substring not lifted (`ng/h12_fork`); second spurious `KeyError` ERROR per mis-marked test | marker sessions test | TODO (NG13) | 1 | 1 | F3 | **SETTLED in substance** (P3-2 noise) |
| N1-12 | flynapse-otel | `network.py:324-341`, `:541-561` | Children append one JSON line per refusal; the parent reads its window | plan | 1200/1200 from 3 concurrent children; fork child caught | child sessions tests | TODO (NG09, NG22) | 1 | 1 | F3 | **SETTLED in substance** |
| N1-13 | flynapse-otel | `network.py:163-236` | `NetworkPolicy` validated and frozen; only service ports openable | plan | Code read; implementer's 7 refusals | `test_a_policy_that_opens_nothing_real_is_refused` | TODO (NG11, NG16) | 1 | 1 | F3 | **ASSERTED** |
| N1-14 | flynapse-otel | `network.py:567-588` | `guard_session` forces AWS off, defaults OTel off, exports the site dir first | plan | Code read; implementer's env-pins test | `test_the_environment_pins` | TODO (NG07, NG20, NG26) | 1 | 1 | F3 | **ASSERTED** |
| N1-15 | flynapse-otel | `tests/unit/packaging/test_testing_package_isolation.py` (5146857) | Three modules stdlib-only; plugin alone imports pytest; `install()` refused outside a test process | plan | Code read | the isolation file | TODO (NG06) | 3 | 1 | F3 | **ASSERTED** |
| N1-16 | flynapse-otel | `network.py:274-281`, `:310-315` | A NAME is judged by the loopback set, "connect with a name resolves it in C" | docstring | Resolution never re-checked; harmless on this host's `/etc/hosts` | none | not applicable | 3 | 1 | F3 | **OPEN** (P3-3: declare) |
| N1-17 | flynapse-otel | `5146857`, `d1e531f` | Green at their own HEAD | process | 2576 passed, rc=0 both | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |

**Tier 0.** N1-02's IPv6 limb only (NG03 red before the pause).

---
## Open claims, tier 2 first

**Tier 2:** none.

**Tier 1**
1. **N1-01 (P1-1):** skip/xfail swallow a refusal — blocks adoption (every consumer has probe-and-skip fixtures).
2. **N1-04, N1-05, N1-06 (P2-1):** psycopg2 seat, proxies, 8050 — the ruling's own additions.
3. **N1-03 (P2-2):** own-port by number.
4. **N1-09 (P2-3, P2-5):** xdist workers; `unconfigure`/`atexit`.
5. **N1-08 (P2-4):** `-I`/`-E`/`-S`/PYTHONPATH-override children.
6. **N1-10 (P2-5):** pooled connections outlive the phase — declare.
7. **N1-16, P3-1, P3-2, P3-4.**

**TODO at resume:** the 28-mutant battery (every "Mutation-proved? TODO" cell), then re-state the tier-0 rows.
