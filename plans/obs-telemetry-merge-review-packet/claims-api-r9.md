# Claims packet: api review r9 (`e3ba207..fbd394c`, the r8 batch; eight never-reviewed commits; routed items)

Independent adversarial review (Opus), 2026-09-22. Read-only: no real tree was edited, checked out,
stashed or committed. Every run used a `git archive` copy under
`~/.claude/scratch/obs-merge/api-review-r9/ws/`: `api-obsm` (pristine `fbd394c`, for lanes and mutants),
`api-probe` (`fbd394c` plus the reviewer's probe files under `tests/r9probe/`), `api-survA`/`api-survB`
(surviving mutants applied), and one archive per older commit (`c-<sha>`). Siblings archived: core-obsm
`16cd1ae`, utils-obsm `179cc6d`, copilot-mro-obsm `557a178f`, flynapse-otel `0224a1a` (its tree was
dirty, so HEAD was archived), shift-optimizer `0b4de00`, declared through `SIBLING_CHECKOUTS`. Durable
record: `NOTES.md` beside them; mutant texts and logs in `mut/`; plant and probe logs in `runs/`.

| repo | worktree | branch | ranges | HEAD at review | tree state |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `e3ba207..fbd394c` (16) + `66868f8 a3004d0 d6ab632 cc56667 f985d8d 1b1d088 0c176bb 0e225bd` | `fbd394c` | clean, untouched |

**Verdicts.**
- **Part 1 (the r8 batch): FIX-FIRST.** 0 P0, 0 P1, **2 P2, 10 P3.** Every r8 finding the batch
  answered is answered at the scope it claims, and the headline measurement (0 connects to `:5432`) holds
  under a stronger witness. But Rule B's which-row test still cannot fail for two realistic wrong-tenant
  accessors (P2-1, tier 2), and the guard's session-level FAIL half switches off silently under
  `pytest -n` (P2-2).
- **Part 2 (the eight commits): FIX-FIRST.** 0 P0, 0 P1, **1 P2, 4 P3.** Nothing leaks at `fbd394c`.
  The guards of `0c176bb`, `0e225bd`, `f985d8d` and `cc56667` kill their mutants, and `1b1d088`'s
  conversion is sound. But the response-body and run-error sweeps claim a taint rule their code does not
  hold (P2-3).
- **Part 3 (routed): CLEAN.** The gateway's access line withholds `?search=`, measured on the real uvicorn
  line, on stdout and in the exported OTLP record. The docstring findings F4, F5 and F9 do not hold at
  `fbd394c`.
- **Totals: 0 P0 · 0 P1 · 3 P2 · 14 P3.**

## How it was run

- **A private network per run.** Every lane, plant and mutant ran inside `ns.sh`: `unshare -rnm`, only
  `lo` up, `/etc/resolv.conf` bind-mounted to `nameserver 127.0.0.1`, and a DNS witness on
  `127.0.0.1:53` that answers NXDOMAIN and logs every query. Nothing could leave the VM, and no dev
  service was reachable. The one exception is the Rule B database run (below), which needs the host's
  Postgres.
- **A logger that can see DNS.** `tools/netlog2.so` (`LD_PRELOAD`) logs libc `connect`, `sendto`,
  `sendmsg`, `sendmmsg`, `getaddrinfo`, `gethostbyname*_r`, `gethostbyaddr_r` and `getnameinfo`, with
  `PYTEST_CURRENT_TEST`. It sends nothing.
- **Why a second logger.** The implementer's `tools/netlog.so` interposes `connect` only, and glibc's
  resolver reaches its sockets through internal aliases no `LD_PRELOAD` sees. This was proved in the
  namespace, with resolv.conf pointed at a local UDP listener. The listener RECEIVED the query for
  `r9-dns-witness.example.invalid`, while `netlog.so` logged nothing at all (`tools/dnsprobe.py`).
- **Recipe.** `lane.sh` sets `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`,
  pins `PYTHONPATH` to the copy and the archives, and uses a private `PYTHONPYCACHEPREFIX`. It runs through
  `pytest-slot.sh` with `-p no:randomly -p no:cacheprovider -o addopts="-ra --strict-markers"`, serial,
  one pytest at a time. A provenance probe showed `flynapse_api`, `_netguard`, `core`, `utils`,
  `flynapse_otel` and `shift_optimizer` each loaded from the copy or its archive, and `PYTHONPATH[0]` was
  the copy's `tests/_netguard_site`. The rootdir was the copy.
- **Mutants.** Each went through `mutant.sh` (baseline-checked, cold bytecode), aimed at the file meant to
  catch it, and was md5-verified against the `fbd394c` blob after restore; every restore matched. A
  mutant that survived aimed was re-run on the FULL lanes. The survivors were applied together to
  `api-survA` (and `M2` alone to `api-survB`) and every lane was run. A test that catches one mutant
  alone would also fail with the others present, and none of the survivors mask one another.
- **Database: one DB-writing run of the two allowed.** It ran the Rule B file plus the reviewer's posed
  accessors, with `-m postgres`, outside the namespace, and nothing else ran concurrently. A read-only
  count afterwards found 0 `t-rule-b-%` tenant rows left.

## Lanes at `fbd394c`

| lane | result | note |
|---|---|---|
| unit | 928 passed, 20 skipped, 2 failed, 1 deselected | the failures and the extra skips are archive-layout artefacts: no `ws/core` primary checkout, and `git` absent (the implementer's real-tree run is 950 + 1d) |
| smoke | 21 passed, 3 deselected, "1 wrong-checkout import" | archive artefact, as r8's ‡ |
| startup / api / middleware | 69 / 26 / 310 passed | |
| integration `-m "not postgres"` | 364 passed, 1 failed, 24 deselected | the failure is `ws/core/core/fastapi_app.py` absent (artefact) |
| integration collect | 389 | |

**Network census, every lane plus collection.** The witness saw 0 DNS queries. libc saw 1
`getaddrinfo` and 1 `connect`, both to the forwarder test's own `127.0.0.1:<ephemeral>`. There were
**0 connects to `:5432`**. The implementer's headline measurement (r8's 16 → 0) holds, now with a
witness that could also have seen a lookup.

---

## Part 1 — the r8 fix batch (`e3ba207..fbd394c`)

### P2-1 (tier 2): Rule B's which-row test passes an ILIKE accessor and a suffix-matching accessor

**Where.** `tests/integration/registry/test_single_row_accessors_return_the_tenant_asked_for.py`
(`20fb066`): its probes, and the docstring's "a forward prefix match (`LIKE lower(%s) || '%'`, a
'forgiving subdomain' lookup)". Also the parse, `test_paged_registry_reads_state_their_limit.py::_one_row_basis`.

**Measured on `copilot_mro_test`** (DB run 1, both seed orders, `runs/db/db1.log`). The file's own ten
tests pass (the implementer's "10 passed" reproduced). The reviewer's posed accessors, held to the file's
own `_prove`, gave:

| posed accessor (SQL) | authoritative check | parse (`_one_row_basis`) |
|---|---|---|
| suffix, the real "forgiving subdomain": `WHERE lower(%s) LIKE '%%' \|\| lower(domain) … LIMIT 1` | **PASSES** in both orders | `LIMIT 1`, accepted |
| ILIKE by domain: `WHERE domain ILIKE %s … LIMIT 1` | **PASSES** in both orders | `LIMIT 1`, accepted |
| ILIKE by name: `WHERE tenant_name ILIKE %s LIMIT 1` | **PASSES** in both orders | `LIMIT 1`, accepted |
| reverse prefix (control): `WHERE lower(%s) LIKE lower(domain) \|\| '%%'` | fails, caught | `LIMIT 1`, accepted |

The ILIKE accessor resolved `twin-<token>_example` (a `_` wildcard) to the twin, and `%` to some tenant.

**Why.** Every probe is a PREFIX of a stored value (`[:-3]`, `[:-1]`). That catches a forward prefix
match and a substring match. It cannot catch a pattern (the caller's text used as a `LIKE` pattern), or
a suffix match, which is what a subdomain-forgiving lookup actually is (`eu.acme.com` ends with
`acme.com`). So the docstring mislabels the shape it guards.

**Scenario.** A later change makes the auth STEP 0 domain lookup case-insensitive with `ILIKE` (a common
idiom), or makes it "forgive subdomains". A login from `x@acme_com`, `eu.acme.com` or `evilacme.com` then
resolves tenant `acme.com`, a cross-tenant login resolution. The parse accepts it, and the authoritative
test passes it in both seed orders.

**Fix.** Add probes that must return `None`: a wildcard (`%`, and each stored value with `.` → `_`), a
suffix-extended value (`eu.` + domain, `x` + domain), and a superstring. Pose the ILIKE and suffix
accessors in-lane, as the file already does for the forward prefix. Pin case behaviour explicitly:
case-insensitive for the domain, exact for the name.

### P2-2 (tier 1): the guard's session-level FAIL half is silent under `pytest -n`

**Where.** `tests/conftest.py:562-605`, whose `pytest_sessionfinish` sets `session.exitstatus` and tags
the final line. `e3ba207` added pytest-xdist "for parallel test lanes", and the workspace prescribes
`pytest -n 4` for big lanes.

**Measured** (`runs/plants/import-*.log`). The probes file's `import` plant, a refusal at collection,
gives:
- **serial:** "5 passed, 1 network refusal", rc 1;
- **`-n 2`:** "5 passed", rc 0, with nothing printed.

A phase refusal (`body`) still fails under `-n 2` (rc 1). So the per-phase half survives xdist, and the
session half is lost. The worker's exit status is discarded and its terminal reporter is `None`. The
checkout pin's session-end half (`imported_elsewhere`) is lost the same way.

**Declared?** No. Nothing in api's conftest, `_netguard.py`, `pyproject.toml` or `docs/plans` says
"serial". Only the implementer's scratch notes do. The netguard r1 review filed the same mechanism
against the shared guard (P2-3).

**Scenario.** A developer runs `pytest -n 4 tests/unit`, as the workspace prescribes. A new module-level
Redis or OTLP probe, or a stray lookup at collection, is refused and swallowed, and the lane exits 0
with no tag. So does a provable wrong-checkout import.

**Fix.** In a worker, put the strays and findings into `config.workeroutput`, and fail from a
controller-side `pytest_testnodedown`. Or refuse `-n` in `pytest_configure` until that exists. Either way,
say it in the conftest.

### P3s (part 1)

- **P3-1: several Python seats into libpq are not wrapped, and a service file defeats the target
  reading.** Plants in the namespace (`runs/plants/per-test.log` + netlog) each PASSED with a libc
  connect and zero refusals:
  - `psycopg2.extensions.connection(dsn)`, `psycopg2._connect(dsn)` and `psycopg.pq.PGconn.connect(dsn)`,
    each to `127.0.0.1:5432`;
  - `PGSERVICEFILE` with `host=10.9.9.9` plus `psycopg2.connect("service=r9svc port=6543")`. The guard
    read a Unix socket on 6543; libpq connected to `10.9.9.9:6543`, beyond loopback.

  The docstring's "libpq has one [Python seat], above" is the same overstatement r8 P2-2 made, one
  level down. No estate code uses these entry points today. Fix: declare them. Read `service` and
  `PGSERVICE` and refuse a service lookup, since the guard cannot resolve it.
- **P3-2: ten guard rules are unpinned. Each mutant below survives the aimed lane AND the full lanes**
  (`runs/survA`, `runs/survB`):
  - M1: every `/etc/hosts` name allowed, whatever it maps to (the shared guard's NG08b);
  - M2: `/etc/hosts` not read at all (NG08);
  - M3: a `sitecustomize.py` ahead of the guard's on a child's `PYTHONPATH` not refused;
  - M4: `PGHOST`/`PGPORT`/`PGHOSTADDR` ignored;
  - M5: `hostaddr` ignored;
  - M6: only the first of several hosts judged;
  - M7: the `os.exec` and `os.posix_spawn` audit events not judged (the behaviour is right today:
    plants p26 and p27 are refused);
  - M8: an XPASS not overridden (the behaviour is right today: plant p30 fails);
  - M9: the proxy loop removed;
  - M12: a DSN never parsed.

  Why the driver ones survive: every DSN case in the probe table also lands on port 5432, so the port
  rule refuses it whatever the parser read. It fails closed by accident. M9 survives because the proxy
  pin only bites when the runner exports a proxy; the implementer killed p32-M1 only with
  `HTTPS_PROXY` exported. M10 (lowercase proxies kept) survives aimed and is implied by M9. M11 (the
  Unix-socket port rule skipped) is the one KILLED. Fix: a DSN case beyond loopback on a non-service
  port; the `PGHOST`, `hostaddr` and multi-host shapes; a synthetic hosts table (loopback, LAN and dual
  lines); an `os.execv`/`posix_spawn` plant; an XPASS probe; and a nested session that exports proxies.
- **P3-3: the spawn hook misses Python children started through a launcher.** Two plants, p20
  `["env", python, "-I", "-c", …]` and p21 `["env", "-i", "PATH=…", python, …]`, each started an
  unguarded child whose lookup reached the DNS witness, with zero refusals. `env` is neither a named
  interpreter, nor a `#!` script, nor a shell string (the declared miss). The same holds for `timeout`,
  `nice`, `nohup`, `xargs`, `stdbuf`. Two related shapes:
  - A child env without `API_TEST_NETGUARD_LOG` runs guarded, but its refusals never reach the parent
    (p23). Nothing left, but the report was lost.
  - A child env carrying `API_TEST_NETGUARD_PORTS=6379` reaches Redis's port (p24).

  The workspace plan's §4a-bis row says "`-I`/`-E`/`-S`/scrubbed-env Python children refused". A
  scrubbed env through `env -i` is not. Fix: read through known launchers to the program they run;
  require the log variable; refuse a child env that sets the ports variable.
- **P3-4: the raw C socket type is reachable through the stdlib.** `socket.SocketType(...)` is the raw
  `_socket.socket`, captured by `socket.py` at import. So is `super(socket.socket, s).connect(addr)`.
  Each reached a libc `connect` to `:6379` with zero refusals (p11, p10). The docstring declares only a
  `_socket.socket` captured by `from _socket import socket`; the stdlib's own public alias is that
  capture and is not named. Fix: declare both, or rebind `socket.SocketType` at install.
- **P3-5: a Python DNS client goes out through a loopback resolver.** With resolv.conf at `127.0.0.1`,
  as a stock Ubuntu host has `127.0.0.53` (and systemd-resolved listens on `127.0.0.53` here too),
  `dns.resolver.Resolver().resolve("r9-dnspython.example.invalid")` (dnspython 2.8.0 is installed, and
  email-validator uses it) sent the query with zero refusals. The witness received it (p12). The claim
  "A refused name is refused BEFORE any lookup, so no DNS query leaves either" holds only for the
  wrapped lookup functions. A loopback resolver is a forwarder, the same class as r8 P3-2's proxy.
  Fix: refuse port 53 on loopback (the host resolver's service port), or declare it.
- **P3-6: `SERVICE_PORTS` misses eight dev-stack services LISTENING on this box.** These are Grafana
  3000, Loki 3100 (log push), Tempo 3200, pgAdmin 5050, Weaviate UI 7777, redis-commander 8081 (an HTTP
  forwarder into Redis), Prometheus 9090 and Alertmanager 9093 (alert POST). All are in
  `copilot-mro/deployment/docker-compose.yml`, and all were connected to with zero refusals (p13).
  `8050` was the same class in r8, and a hand-kept list will keep missing the next one. Fix: refuse every
  loopback port below the kernel's ephemeral range (`ip_local_port_range`) unless opted in. Test-owned
  servers bind port 0, so they are unaffected.
- **P3-7: the proxy removal is undone by the app's own `load_dotenv()`, and its pin is vacuous in an
  ordinary run.** The conftest REMOVES `*_PROXY`. `flynapse_api/main.py:26`'s module-level
  `load_dotenv()` (`override=False`) then refills any variable a found `.env` names. Measured with a
  `.env` in the reviewer's copy: after `import flynapse_api.main`, `HTTPS_PROXY` was back and
  `getproxies()` returned `https` (`runs/plants/proxy.log`). A BLANKED variable survives
  `override=False`, which is what r8 proposed ("as `COGNITO_USER_POOL_ID` is"). The conftest cites r8 for
  "REMOVED, not blanked", and the test is still named `…_proxy_blanking_closes`. api-obsm's `.env`
  (→ `api/.env`) has 0 proxy lines today. All spellings were verified removed at conftest time (p28:
  `ALL_PROXY`, `all_proxy`, `https_proxy`, `grpc_proxy`, `FTP_PROXY` gone, `NO_PROXY` kept). Fix: blank
  them instead of removing them, and pin from a nested session that exports them.
- **P3-8: a refusal after `sessionfinish` is silent.** Three plants each gave rc 0 with nothing printed
  and nothing left (`runs/plants/s-*.log`):
  - a refusal inside an `atexit` callback (the OTel flush shape);
  - a non-daemon thread's refusal after the last test;
  - a refusal followed by `pytest.exit(..., returncode=0)`.

  The log is unlinked at `sessionfinish`. Fix: a guard-registered `atexit` check, and a
  `pytest_unconfigure(trylast)` sweep (the shared guard's r1 P2-5).
- **P3-9: the P3-4 evidence was measured with a witness that cannot see DNS.** The implementer's NOTES
  cite "port-53 connects 0/0/0 (nameserver 10.255.255.254 never reached)" from `netlog.so`. Proved above,
  that shim is blind to glibc's resolver. **The claim itself holds:** replayed under the DNS witness,
  MR1 (raw names unwrapped) and MA11 (child guard not installed) are KILLED with 0 DNS queries and 0
  non-loopback libc calls (`mut/results4.log`). Future witness runs should use a lookup-logging shim or
  a DNS listener.
- **P3-10: stale prose.**
  - `docs/plans/api-review-r7-batch.md:53` still says "(libpq, grpc, uvloop) … no Python-level guard can
    see them". `:185` still says "nothing in api reaches a dev-stack port through Python". r8 P2-2's fix
    list said "Correct plan §1/§3", and `_netguard.py:75` still sends readers to that document.
  - `_netguard.py:70-72` still names grpc as a C extension with no Python seat. r8 noted `grpc.*_channel`
    is one. The plant p14 reached `connect 10.9.9.9:4317` (declared as C-level).
  - `_netguard.py:111` says "The same list as the estate's shared guard … plus Postgres". The shared list
    already holds 5432.
  - The test name `…_proxy_blanking_closes` contradicts "REMOVED, not blanked".

## Part 2 — the eight never-reviewed commits

Each commit's own tests were run at that commit (`runs/commits/`):
- `66868f8`: 58 passed;
- `1b1d088`: 105 passed;
- `0c176bb`: 12 passed;
- `0e225bd`: 2 passed;
- `a3004d0` and `d6ab632`: RED (P3-14);
- `f985d8d`: collection ERROR (P3-14);
- `cc56667`: 61 failed, all in `tests/integration/automations`, which needed a live Postgres until
  `91781ef`. That is the namespace, not the commit.

### P2-3 (tier 1): the response-body and run-error sweeps claim a taint rule their code does not hold

**Where.**
- `tests/unit/api_surface/test_no_exception_text_in_response_bodies.py` (`a3004d0`) says: "A local
  ASSIGNED that text counts as the exception: `message = str(exc)` followed by `detail=message` is the
  same leak with one more line, and both sibling guards are blind to it." Its `_tainted_names` docstring
  adds: "every local in *scope* assigned from its text, to a fixed point."
- `test_no_exception_text_in_run_error_column.py` (`cc56667`) says: "A local ASSIGNED that text counts as
  the exception, to a fixed point."

**Measured, with each sweep's OWN `_offenders` on posed source** (`tests/r9probe/sweeps`). The controls
(`detail=str(exc)`, `run_error(…, str(exc))`) are FLAGGED. MISSED:

| shape | response sweep | run-error sweep |
|---|---|---|
| `message += str(exc)` | MISSED (RS2) | MISSED (ES1) |
| `status, message = 500, str(exc)` | MISSED (RS3) | MISSED (ES2) |
| `payload["error"] = str(exc)`; `JSONResponse(payload)` | MISSED (RS4) | — |
| `errors.append(str(exc))`; `detail=errors` | MISSED (RS6) | — |
| set in the handler, returned or written AFTER it (`failure = str(exc)` … `return {"error": failure}`) | MISSED (RS1, in a route) | MISSED (ES3) |
| `from fastapi.responses import JSONResponse as JR` | MISSED (RS5) | — |

The taint handles only `Assign`, `AnnAssign` and `NamedExpr` with a bare-name target, and only statements
inside the handler body.

**At a real site.** R1 (`routers/auth.py` logout, BotoCoreError branch: `refusal["cause"] = str(exc)`;
`detail=refusal`) SURVIVES the aimed sweep. The full unit lane kills it through a behaviour test
(`test_logout_revocation.py::test_a_call_that_never_reached_cognito_is_the_same_502`), not through the
sweep. Both of the gateway's current body-building error sites (logout, `/health/ready`) are pinned
behaviourally. **No leak ships at `fbd394c`.** The exposure is the rule's stated purpose: a NEW route or
module, "held to the rule the day it is written".

**Scenario.** A new gateway route catches an upstream failure and builds `payload["error"] = str(exc)`,
or sets `failure = str(exc)` in the handler and returns it after. The sweep passes, and a DSN, an ARN or
an account id goes to the caller, anonymous on an unauthenticated route. The run-error twin writes the
text into `automation_runs.error`, which core serves to tenant callers.

**Fix.** Taint every name bound under the handler (`AugAssign`, tuple and starred targets, subscript
and attribute stores, `.append`/`.extend`/`.update`/`.setdefault` on a tainted container), and carry the
taint to the end of the enclosing function, not the end of the handler. Resolve aliased response
classes through the imports. Put each shape among the detector's self-test plants.

### P3s (part 2)

- **P3-11: the log sweep (`66868f8`, as tightened by `1b1d088`/`cc56667`) misses text by one
  indirection, and does not say so.** Each of these was MISSED by its `_offenders` (LS0, an f-string
  reading `exc`, is FLAGGED):
  - LS1: text through a local (`detail = f"x {exc}"; logger.error(detail)`);
  - LS2: `sys.exception()` (3.11, beside the banned `sys.exc_info`);
  - LS3: a function-local bound logger (`log = logger.bind(…)`);
  - LS7: a `self.log` logger;
  - LS5: stdlib `logging.error`;
  - LS4: `print` to stdout, which is the container log (r8 P3-8's premise);
  - LS9: `warnings.warn`;
  - LS8: an exception stored in the handler and logged after it;
  - LS6: `task.exception()` rendered outside any handler. The shape exists at `loop.py:3388`, correctly
    written today.

  The real-site plant L1 (`worker.py`, text through a local) survives the aimed sweep AND the full lanes.
  Its own docstring declares none of this; the sibling's docstring says "both sibling guards are blind".
  Fix: the same taint as P2-3, plus `sys.exception`, `logging.*` roots and bound-logger locals, or
  declare them.
- **P3-12: the served `reason` column takes any exception's `.reason`.** `automations/one_shot.py:210-224`
  does `reason = getattr(exc, "reason", None)` and writes it to `automation_runs.reason` when it is a
  `str`. Core serves that column as `AutomationRun.reason` (`schemas.py:368`). The run-error sweep
  watches only `error` (ES4, `reason=str(exc)`, MISSED). The convention is a machine token
  (`AdMaterializeError`). But `urllib.error.URLError` and websockets' `ConnectionClosed` carry free text
  in `.reason`, and the one-shot catch-all takes every exception. Fix: accept only a token from a
  declared set, or `isinstance(exc, <the token-carrying family>)`.
- **P3-13: stale docstring.** `automations/document_hub_cleanup.py:103` (`_sweep_sync`) says "The cause is
  chained, and its text rides into the row's `error`." Since `b6471c8`/`cc56667` the one-shot close
  writes `run_error(INTERNAL, "the run failed")` plus the reason token. The text rides nowhere.
- **P3-14 (process, declared): three commits land their guard RED at their own commit.**
  - `a3004d0`'s response sweep flags `auth/auth.py` ×2 and `cache_management.py`. Its message says "this
    commit lands the guard red against the checked-in tree".
  - `d6ab632` is still red: 2 failed.
  - `f985d8d` gives a collection ERROR (`executor.REASON_AD_MATERIALIZE_FAILED` absent). Its message
    says "Production edits stay uncommitted for owner review".

  The production landed in `b6471c8`. A `git bisect` across `a3004d0..b6471c8` reds for reasons
  unrelated to the bug being hunted.

## Part 3 — routed items

- **(a) `?search=` on the gateway's access line: WITHHELD** (probe, `runs/search/`).
  - **How.** The real uvicorn ran in the Dockerfile's CMD form (`--log-config
    flynapse_api/uvicorn_log_config.json`, `PYTHONUNBUFFERED=1`, `PYTHONPATH` = copy + `flynapse_api`)
    inside the namespace, with a test-owned OTLP/HTTP sink on `127.0.0.1:4318`.
  - **A probe app.** The real `main:app` cannot finish its lifespan without Postgres (traceback
    withheld). So the probe app, `ws/api-probe/flynapse_api/r9_access_probe_app.py`, is `main.py`'s own
    `setup_logging(...)` call and `instrument_gateway(...)`, verbatim, around two routes.
  - **Result.** The stdout JSON access line AND the exported OTLP log record carry
    `"GET /health/live?:redacted HTTP/1.1"` for `?search=alice.smith%40corp.example`. They carry
    `/api/v1/users/?:redacted` for `?search=…&limit=5` (the whole query goes) and redact `?user_search=`.
    `?token=` (control) is withheld. The exported server span carries none of the typed text (G.111).
  - **Limit.** The rule is name-based by design (G.116): `?q=carol.white%40corp.example` and
    `?query=…` pass verbatim on stdout and OTLP. No estate route declares either through `Query(...)`
    today (enumerated); the only typed-text query parameters found are `search` (×3) and core's comments
    `tags`. api has no URL or log redaction of its own: its code logs `request.url.path` only, and the
    access line is uvicorn's, through utils' intercept → flynapse-otel's `withhold_url_secrets` (df503c2
    is in the archived `0224a1a`). **Deploy note:** api's lock carries flynapse-otel `0.1.1` as a develop path
    dependency (through utils), so dev runs whatever the checkout holds. A deployed image carries `search`
    only once its flynapse-otel build includes df503c2 (M-VERSIONS).
- **(b) the docstring audit's api findings: none holds at `fbd394c`.** The audit's quotes match
  `bc8e268`'s text.

  | finding | at `fbd394c` | evidence |
  |---|---|---|
  | F4 `queue_telemetry.py:90` `retry` trigger "and by nothing else" | **does not hold.** Removed at `b6471c8`. The comment now says "There is no `retry` trigger, and a retry must not introduce one" (`:102`). The three values are pinned with their count by `tests/unit/telemetry/test_queue_trigger_vocabulary.py`. The retry SQL binds `TRIGGER_SCHEDULED` (core `automation_store.py:2606`) | `git log -S"and by nothing else"`; the file at HEAD |
  | F5 `queue_telemetry.py:55` "two ten-key deny-lists" | **does not hold.** Removed at `08f54f9`. It now reads "overlap only in part, neither contains the other, and `tenant.id` is on neither", which is TRUE: app 10 keys, collector 9, 5 shared (`session.id`, `user.id`, `enduser.id`, `url.path`, `http.target`) | `flynapse_otel/registry.py:28-41`; `copilot-mro-obsm/deployment/otel/base.yaml:76-95` |
  | F9 `lifecycle_span.py:4` "the only lifecycle spans in the estate" | **does not hold.** Removed at `b6471c8`. The remaining claim, "the span vocabulary deliberately matches copilot-mro's … so one query reads both runtimes", is true for the ATTRIBUTES (`lifecycle.phase`, `operation.outcome`, `lifecycle.degraded_components`, `lifecycle.failed_component`: copilot-mro `main.py:103-238`). Span NAMES differ (`api.lifecycle.*` vs `mro.lifecycle.*`), which the docstring does not claim otherwise | the file at HEAD |

---

## What I tried to break and could not

- **Controls refused and failed their phase, with the refusal named.** These were psycopg2 `connect`,
  psycopg 3 sync and async `connect`, SQLAlchemy's engine, urllib3, httpx, a thread, a
  `multiprocessing` spawn child, `os.posix_spawn(… -I …)`, and `os.execv(… -I …)` inside a guarded child.
  The last was refused by the child's own hook and reported to the parent's call phase.
- **Skip and xfail shapes.** XPASS, imperative `pytest.xfail`, `unittest.skipTest` and
  `pytest.importorskip` after a refusal each FAIL ("does not excuse it").
- **The implementer's mutants, replayed at HEAD, all KILLED:** p33-M2, p34-MR3, p313-M3, p311-MA3,
  p32-M1 (with a proxy exported), p36-M4, p37-SG3 and p39-RBm2, plus the reviewer's equivalents of the
  three whose texts moved: X1 (`install()` skips `_wrap_drivers`), X2 (driver judge off) and X3
  (`makereport` override off). MR1 and MA11 were witnessed with 0 DNS queries.
- **Rule B.** The authoritative file runs green, catches its forward-prefix and list-then-filter posed
  accessors in both orders, and catches a reverse prefix. Seeding inside `try:` left 0 rows.
- **Part 2 mutants KILLED at HEAD:**
  - C1: the JWKS span renamed off `cognito.*`;
  - C2: `server.address` set to the full URL (pool id);
  - C3: `/test-cookie` echoes the value;
  - F1 and F2: `pattern_delete_failed` ignored in `auth.py` and `cache.py`;
  - F3: `materialise_busy` filed `INTERNAL`;
  - E1: the one-shot `error` carries `{exc}`.
- **`1b1d088`.** 100 `**failure_fields(...)` call sites with 0 keyword collisions (`error_type`, `stack`,
  `aws_error_code`, `sqlstate`, `pg_primary`), and 0 constant loguru messages with braces and keyword
  arguments.
- **`d6ab632`.** `cache_management.py` was imported and mounted by nothing at its parent (`git grep`).
- **`4ec93a8`.** The `--chmod` rule was read: octal only, other-read required, symbolic refused.
- **Postgres opens by MARKER.** A marked child inherits `[5432]`. No unmarked lane reaches `:5432`.

## What I did not test

- **The real gateway app under uvicorn.** Its lifespan needs Postgres. The access-line probe used
  `main.py`'s logging and instrumentation verbatim around a probe app.
- **No docker build.** BuildKit's `--chmod` on created directories was not observed.
- **The second allowed DB run was not used.**
- **Per-commit full lanes.** The r8 batch commits were run on their own changed tests only (below);
  the full lanes ran at `fbd394c`.
- **Siblings are HEAD archives,** not per-commit SHAs, so the part-2 commits' own-test results are at
  today's siblings.
- **uvloop and grpc** beyond one plant each.

## Per-commit own tests, the r8 batch

Each commit was archived, and ONLY the test files it added or changed were run, in the namespace
(`runs/commits/r8-batch.summary`). Every commit made 0 DNS queries.

| commit | result | | commit | result |
|---|---|---|---|---|
| `91781ef` | 151 passed, 17 deselected | | `484fa6f` | 2 passed |
| `799dee7` | 17 passed | | `31a5792` | 11 passed |
| `02c9710` | 24 passed | | `3f0df5e` | 13 passed |
| `20fb066` | 13 passed, 10 deselected | | `60ad75d` | 13 passed, 1 skipped (the git half, outside a checkout) |
| `2d49c3f` | 22 passed | | `fdc3a90` | 33 passed |
| `5a2c162` | 59 passed, 14 skipped | | `867c66d` | 38 passed |
| `42174b3` | 37 passed | | `fbd394c` | 34 passed |
| `4ec93a8`, `497ab00` | 13 passed, 1 failed | | | |

The failure at `4ec93a8` and `497ab00` is `test_the_configuration_is_committed_world_readable` in a
`.git`-less archive: exactly r8 P3-10, which `60ad75d` then fixed. It is an artefact, not a regression.

## Claims table

Severity: the finding's P level (P0 a content leak that ships … P3 docs or process; — for a settled row). Tier (§2.3a): 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 =
irreversible or estate-shaping. Chunk F1 = production-adjacent, F3 = the residual (test hygiene).

| # | Part | File:line | Claim | Evidence (command / artefact) | Guard test | Mutation-proved? | Severity | Tier | Chunk | Verdict | Failure scenario |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r9-01 | 1 | `tests/_netguard.py`, conftest; plan §4a-bis | Measured under `unshare -rn`: 0 connects to `:5432`, 1 in total | `lanes.sh` in `ns.sh` + netlog2 + DNS witness: 0 DNS, 1 getaddrinfo + 1 connect (forwarder), 0 `:5432` | every lane | n/a | — | 0 | F3 | SETTLED | — |
| r9-02 | 1 | `_netguard.py:33-43,302-481` (`91781ef`, `799dee7`) | `psycopg2.connect` and psycopg 3 `Connection`/`AsyncConnection.connect` are guarded seats; a driver imported while lifted is wrapped by the next `install()` | plants p01/p04/p06/p08 FAIL with `psycopg*.connect 127.0.0.1:5432`; X1, X2 KILLED | `test_every_wrapped_entry_point…`, `test_a_driver_imported_while…` | yes (reviewer) | — | 0 | F3 | SETTLED | — |
| r9-03 | 1 | `_netguard.py:33-35,70-72` | "libpq has one [Python seat]"; the target is read "as libpq reads it" | p02 `psycopg2.extensions.connection`, p03 `_connect`, p05 `PGconn.connect` → libc `:5432`, 0 refusals; p07 service file → `10.9.9.9:6543` | none | n/a | P3 | 1 | F3 | REFUTED (P3-1) | a helper or test builds a connection through an unwrapped entry point, or `PGSERVICE`, and reaches the dev DB or a remote host silently |
| r9-04 | 1 | `_netguard.py:176-218,317-344,157,484-575`; conftest `:82-92,478-490` | The hosts rule, libpq env/`hostaddr`/multi-host/DSN reading, `os.exec`/`posix_spawn` judging, sitecustomize-ahead refusal, XPASS override and proxy removal are each held by a test | M1-M9, M12 SURVIVE aimed AND full lanes (`runs/survA`, `survB`); M11 KILLED | the guard file (does not pin these) | yes: survivors | P3 | 1 | F3 | OPEN (P3-2) | a refactor of any of these rules regresses with every lane green |
| r9-05 | 1 | `conftest.py:361-490` (`02c9710`) | A refusal fails its phase even when it skipped or is xfail | p30 XPASS, p31 `pytest.xfail`, p32 `skipTest`, p33 `importorskip` FAIL; X3 and p31-M1 equivalent KILLED; M8 (XPASS path) SURVIVES | `test_a_swallowed_refusal…[skip-after, fixture-skip, xfail]` | yes (XPASS unpinned) | — | 0 | F3 | SETTLED (behaviour); XPASS unpinned in r9-04 | — |
| r9-06 | 1 | `conftest.py:562-605` (+ `e3ba207`) | A refusal outside every phase fails the session, tagged | serial rc 1; `-n 2` rc 0, silent (`runs/plants/import-*`) | `test_a_refusal_outside_every_test_phase…` (serial only) | n/a | P2 | 1 | F3 | REFUTED under xdist (P2-2) | `pytest -n 4` lanes pass with import-time refusals and wrong-checkout imports |
| r9-07 | 1 | `conftest.py:82-92` (`2d49c3f`) | No proxy variable reaches the session or its children | p28: all spellings removed, NO_PROXY kept; `import flynapse_api.main` restores `HTTPS_PROXY` from a found `.env` (`runs/plants/proxy.log`); M9/M10 survive without an exported proxy | `test_no_proxy_variable_reaches…` | yes only with a proxy exported | P3 | 1 | F3 | PARTIAL (P3-7) | a developer's `.env` gains a corporate proxy, and after the first app import every external request tunnels out through loopback |
| r9-08 | 1 | `_netguard.py:45-56,484-580` (`5a2c162`) | A child Python the guard would not reach is refused before it starts (`-I/-E/-S`, scrubbed env) | direct spawns refused (8 params, p26, p27); p20 `env python -I`, p21 `env -i` → DNS queries reached the witness; p23 no-log child unreported; p24 ports var opens Redis | `test_a_child_python_the_guard_would_not_reach…` | yes for direct spawns; M3/M7 survive | P3 | 1 | F3 | PARTIAL (P3-3) | a test runs a CLI via `env -i …` for a clean environment; the child's traffic is unguarded |
| r9-09 | 1 | `_netguard.py:663-696`, `test_network_guard.py:1-17,247-300` (`42174b3`) | `installed()` is every seat; a broken guard's self-tests send nothing | MR1, MA11 KILLED with 0 DNS and 0 non-loopback calls under the DNS witness; MR3 KILLED | `test_every_seat_is_part_of_installed` | yes | — | 0 | F3 | SETTLED (the implementer's port-53 evidence was blind: P3-9) | — |
| r9-10 | 1 | `_netguard.py:26-31` | Every raw-socket route is checked, except a pre-install `from _socket import socket` | p11 `socket.SocketType`, p10 `super(socket.socket, s).connect` → libc `:6379`, 0 refusals | none | n/a | P3 | 1 | F3 | OPEN (P3-4) | code using the stdlib alias connects anywhere unrefused |
| r9-11 | 1 | `_netguard.py:29-30` | "A refused name is refused BEFORE any lookup, so no DNS query leaves either" | p12 dnspython via the loopback resolver: the witness received the query, 0 refusals | none | n/a | P3 | 1 | F3 | REFUTED for Python DNS clients (P3-5) | on a stock host (resolv.conf 127.0.0.53) a dnspython or email-validator lookup leaks the name |
| r9-12 | 1 | `_netguard.py:110-126` (`fbd394c`) | `SERVICE_PORTS` is the dev stack (8050 added) | p13: 3000, 3100, 3200, 5050, 7777, 8081, 9090, 9093 LISTENING, reached with 0 refusals; M-8050 KILLED (implementer) | `test_every_wrapped_entry_point…` | 8050 yes | P3 | 1 | F3 | PARTIAL (P3-6) | a test pushes to Loki or Alertmanager, or writes Redis via redis-commander, on the live stack |
| r9-13 | 1 | `conftest.py:206-219`, `sitecustomize.py` (`fbd394c`) | The site directory is FIRST on `PYTHONPATH` | provenance probe: `PYTHONPATH[0]` = site dir; p313-M3 replay KILLED | `test_this_session_and_its_children…` | yes | — | 0 | F3 | SETTLED | — |
| r9-14 | 1 | `conftest.py:418-465`, `test_network_guard.py` (`fdc3a90`, `867c66d`) | A child's refusal fails ITS call phase; "uninstalled" names the seat and `_REAL` | p311-MA3 replay KILLED; p25/p27 messages carry "(child pid"; the socket-double probe message | the nested `child`, `socket-double` probes | yes | — | 0 | F3 | SETTLED | — |
| r9-15 | 1 | conftest `pytest_sessionfinish` | Every refusal is reported | `atexit`, late thread and `pytest.exit(0)` after a refusal: rc 0, silent, nothing left | none | n/a | P3 | 1 | F3 | OPEN (P3-8) | an OTel `atexit` flush's refusal passes unseen |
| r9-16 | 1 | implementer NOTES (P3-4 evidence) | "port-53 connects 0/0/0 (nameserver never reached)" | `tools/dnsprobe.py`: a UDP listener received the glibc query, and `netlog.so` logged nothing | n/a | n/a | P3 | 1 | F3 | REFUTED as evidence; the claim holds by r9-09 (P3-9) | a future witness run reports "0 DNS" while queries leave |
| r9-17 | 1 | `tests/integration/registry/test_single_row_accessors…py` (`20fb066`) | Each accessor returns exactly the tenant asked for; the probes catch a "forgiving subdomain" lookup | DB run 1: ILIKE-domain, ILIKE-name and suffix-domain posed accessors PASS `_prove` in both orders; ILIKE resolved `_` and `%`; the parse gives `LIMIT 1` for all | the file itself | yes for forward prefix and listing (the implementer's p21-M1); no for these | P2 | 2 | F1 | REFUTED for ILIKE and suffix (P2-1) | cross-tenant login resolution at auth STEP 0 after a "case-insensitive" or "subdomain" change |
| r9-18 | 1 | `test_paged_registry…py:784-793` (`3f0df5e`) | Both comment readings must find the same basis | p39-RBm2 replay KILLED | `test_every_allowlisted_accessor…` posed pair | yes | — | 0 | F3 | SETTLED | — |
| r9-19 | 1 | `test_uvicorn_leaves_logging_to_utils.py` (`4ec93a8`, `497ab00`, `60ad75d`) | `--chmod` must keep other-read; four launch shapes seen; the git half skips outside a checkout | p36-M4 replay KILLED; archive lane shows the SKIP; `--chmod` code read | that file | yes | — | 0 | F1 | SETTLED | — |
| r9-20 | 1 | `test_no_import_time_log_sinks.py` (`484fa6f`); `test_api_cognito_spans.py` (`31a5792`) | The claimed sink shapes are pinned; the JWKS pin reads fd 1/2 | p37-SG3 replay KILLED; C2 KILLED | those files | yes | — | 0 | F3 | SETTLED | — |
| r9-21 | 1 | `docs/plans/api-review-r7-batch.md:53,185`; `_netguard.py:70-72,111`; test name | The prose r8 asked to correct is corrected | still says no Python guard can see libpq, and nothing reaches a dev-stack port; grpc "no Python seat"; "plus Postgres"; "blanking" | none | n/a | P3 | 1 | F3 | OPEN (P3-10) | readers sent to the r7 plan take refuted limits as true |
| r9-22 | 2 | `test_no_exception_text_in_response_bodies.py:341-412` (`a3004d0`) | "A local ASSIGNED that text counts as the exception … to a fixed point" | own `_offenders`: RS1-RS6 MISSED (`+=`, tuple, subscript, append, returned after the handler, aliased class); R1 real-site plant SURVIVES aimed (killed in the full lane by a behaviour test) | `test_the_detector_flags_every_leak_shape` | yes: R1 survives the sweep | P2 | 1 | F1 | REFUTED (P2-3) | a new route returns `payload["error"] = str(exc)` to an anonymous caller |
| r9-23 | 2 | `test_no_exception_text_in_run_error_column.py:313-430` (`cc56667`) | Same taint rule for `automation_runs.error`; the vocabulary is closed | ES1-ES3 MISSED; E1 (`{exc}` in the detail) KILLED; Rule 2 structural | that file | yes (E1) | P2 | 1 | F1 | PARTIAL (P2-3) | a retry path keeps `last = str(exc)` and writes it after the loop into a column core serves |
| r9-24 | 2 | `test_gateway_logs_carry_no_exception_text.py` (`66868f8`, `1b1d088`, `cc56667`) | "No gateway log record carries an exception's TEXT" | LS1-LS9 MISSED; L1 real-site plant SURVIVES aimed and full lanes; debt 0 at HEAD | that file | yes: L1 survives | P3 | 1 | F3 | PARTIAL (P3-11) | `msg = f"…{exc}"; logger.error(msg)` ships a DSN to the log pipe |
| r9-25 | 2 | `automations/one_shot.py:210-224` | The run row says which kind of failure through a machine token | `reason = getattr(exc, "reason")` if `str`; served as `AutomationRun.reason`; ES4 MISSED | none | n/a | P3 | 1 | F1 | OPEN (P3-12) | a `URLError("…host…")` reason reaches the dashboard |
| r9-26 | 2 | `automations/document_hub_cleanup.py:103` | "its text rides into the row's `error`" | one-shot close writes `run_error(INTERNAL, "the run failed")` | none | n/a | P3 | 1 | F3 | REFUTED (prose, P3-13) | someone re-adds the text "as documented" |
| r9-27 | 2 | `a3004d0`, `d6ab632`, `f985d8d` | Each commit is green on its own tests | own-tests at each commit: RED, RED (2), collection ERROR; declared in two messages | n/a | n/a | P3 | 1 | F3 | REFUTED, declared (P3-14) | a bisect across the range reds for the wrong reason |
| r9-28 | 2 | `main.py:531-566`, `tests/api/credentials/…` (`0e225bd`) | `/test-cookie` reports presence and length only; no gateway route echoes a credential | C3 KILLED; own tests 2 passed | `test_no_route_the_gateway_serves_echoes_a_credential` | yes | — | 0 | F1 | SETTLED | — |
| r9-29 | 2 | `auth/jwks.py`, `routers/auth.py`, `test_cognito_calls_are_spanned.py` (`0c176bb`) | Every Cognito call exports an INTERNAL span with the host only | C1, C2 KILLED; own tests 12 passed; the transport span's `url.full` path is reduced to `/:redacted` at export (G.111) | those files | yes | — | 0 | F1 | SETTLED | — |
| r9-30 | 2 | `middleware/auth.py:1259-1262`, `middleware/cache.py:68-69`, `executor.py:985-1014` (`f985d8d` guards) | An unreachable cache is reported; `materialise_busy`/`no_verdicts` are categorised apart | F1, F2, F3 KILLED at HEAD | the three test files | yes | — | 0 | F1 | SETTLED at HEAD (red at its own commit: r9-27) | — |
| r9-31 | 2 | 13 modules (`1b1d088`) | 127 flags converted to a constant message + `**failure_fields(exc)`; nothing else changed | AST scan: 100 sites, 0 keyword collisions, 0 brace+kwargs messages; own tests 105 passed | the log sweep, the format-string guard | n/a | — | 1 | F1 | SETTLED | — |
| r9-32 | 2 | `routers/cache_management.py` deleted (`d6ab632`) | The router was dead | `git grep` at `d6ab632^`: nothing imports or mounts it | n/a | n/a | — | 1 | F1 | SETTLED | — |
| r9-33 | 3a | gateway access line (uvicorn → utils intercept → flynapse-otel) | `?search=` is withheld | real uvicorn probe: stdout and OTLP log `?:redacted` for `search`/`user_search`; span clean; `q`/`query` pass (name-based) | flynapse-otel `test_a_search_parameter…` | upstream (df503c2 S1-S3) | — | 0 | F1 | SETTLED (deploy needs a published flynapse-otel carrying df503c2) | — |
| r9-34 | 3b | `queue_telemetry.py:55,90`; `lifecycle_span.py:4` | F4, F5, F9 (docstring audit) | `git log -S`; the files at HEAD | `test_queue_trigger_vocabulary.py` (F4) | n/a | — | 1 | F3 | NONE HOLDS at `fbd394c` | — |

## Open claims, tier 2 first

**Tier 2**
1. **r9-17 (P2-1).** Add wildcard, suffix and superstring probes and pose the ILIKE and suffix accessors
   in-lane. Then run once against `copilot_mro_test`.

**Tier 1**, in the order to fix:
1. **r9-06 (P2-2).** Report the session half through xdist, or refuse `-n`, and say so.
2. **r9-22, r9-23 (P2-3).** Widen the taint (augmented and tuple assignment, containers, after the
   handler, aliased classes) in both sweeps, with self-test plants. Then r9-24 (the log sweep, P3-11).
3. **r9-03, r9-08, r9-10, r9-11 (P3-1, P3-3, P3-4, P3-5).** Declare or refuse the libpq entry points and
   service files, launcher children, `socket.SocketType`, and loopback `:53`.
4. **r9-04 (P3-2).** Pin the ten surviving rules.
5. **r9-07, r9-12, r9-15 (P3-7, P3-6, P3-8).** Blank the proxies. Refuse loopback ports below the
   ephemeral range. Add an `atexit`/`unconfigure` sweep.
6. **r9-21, r9-25, r9-26, r9-16, r9-27 (P3-10, P3-12, P3-13, P3-9, P3-14).** Prose, the `reason`
   column, and process.

## For the shared-guard port (M-SHARED-NETGUARD): copy, and do not copy

**Copy from api's guard (each held under mutation here):**
- the psycopg seats and `install()` re-wrapping a driver imported while lifted (`91781ef`, `799dee7`);
- the `makereport` override (`02c9710`), plus an XPASS probe, which api lacks (M8);
- `unguarded_seats()` as the meaning of "installed" (`42174b3`);
- the child refusal pinned to the CALL phase (`fdc3a90`);
- the "uninstalled" message naming the seat and `_REAL` (`867c66d`);
- `8050`, and the site directory FIRST (`fbd394c`);
- the spawn audit hook's direct-spawn judging (`5a2c162`), including `#!` scripts and combined option
  letters.

**Do NOT copy as-is:**
- **proxy REMOVAL.** Blank instead, so a later `load_dotenv(override=False)` cannot refill it, and pin it
  from a nested session that exports proxies.
- **the spawn hook's program test alone.** Add launchers (`env`, `env -i`, `timeout`, `nice`, `nohup`,
  `xargs`) and require the log variable in a child env.
- **the hand-kept `SERVICE_PORTS`.** Eight listening dev-stack ports are missing. Refuse loopback ports
  below the ephemeral range instead.
- **`/etc/hosts` names trusted by name** (unpinned both ways, never re-checked against resolution).
- **"C-level only: libpq has one Python seat".** There are three more entry points and service files.
- **"no DNS query leaves" without refusing loopback `:53`.**
- **the libpq target reader without a test per rule.** Env, `hostaddr`, multi-host and DSN reading all
  survive (every DSN case lands on 5432).
- **a session half with no xdist path and no `atexit`/`unconfigure` sweep.**
- **a connect-only libc logger as the witness for "sends nothing".**
