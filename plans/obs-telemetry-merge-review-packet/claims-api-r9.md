# Claims packet: api review r9 — PARTIAL (in progress; rows may still change)

Independent adversarial review (Opus), 2026-09-22. Read-only: no real tree was edited, checked out,
stashed or committed. Every run used a `git archive` copy under
`~/.claude/scratch/obs-merge/api-review-r9/ws/` (api-obsm `fbd394c` twice: `api-obsm` kept pristine for
lanes and mutants, `api-probe` for plants; siblings archived: core-obsm `16cd1ae`, utils-obsm `179cc6d`,
copilot-mro-obsm `557a178f`, flynapse-otel `0224a1a` (its tree was dirty, so HEAD was archived),
shift-optimizer `0b4de00`, declared through `SIBLING_CHECKOUTS`). Durable notes: `NOTES.md` beside them.

| repo | worktree | branch | ranges | HEAD at review | tree state |
|---|---|---|---|---|---|
| api | `/home/aditya/Code/api-obsm` | `obs-merge` | `e3ba207..fbd394c` (16) + 8 never-reviewed commits | `fbd394c` | clean, untouched |

## How it was run

- **A private network per run.** Every lane, plant and mutant ran inside `ns.sh`: `unshare -rnm`, only
  `lo` up, `/etc/resolv.conf` bind-mounted to `nameserver 127.0.0.1`, and a DNS witness on
  `127.0.0.1:53` that answers NXDOMAIN and logs every query. Nothing could leave the VM, and no dev
  service was reachable. The one exception is the Rule B database run (below), which needs the host's
  Postgres.
- **A logger that can see DNS.** `tools/netlog2.so` (LD_PRELOAD) logs libc `connect`, `sendto`,
  `sendmsg`, `sendmmsg`, `getaddrinfo`, `gethostbyname*_r`, `gethostbyaddr_r` and `getnameinfo`, with
  `PYTEST_CURRENT_TEST`. It sends nothing.
- **Why a second logger.** The implementer's `tools/netlog.so` interposes `connect` only, and glibc's
  resolver reaches its sockets through internal aliases no `LD_PRELOAD` sees. Proved in the namespace
  with resolv.conf pointed at a local UDP listener: the listener RECEIVED the query for
  `r9-dns-witness.example.invalid`, and `netlog.so` logged nothing at all (`tools/dnsprobe.py`).
- **Recipe.** `lane.sh` = `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`,
  `PYTHONPATH` pinned to the copy and the archives, a private `PYTHONPYCACHEPREFIX`, through
  `pytest-slot.sh`, `-p no:randomly -p no:cacheprovider -o addopts="-ra --strict-markers"`, serial.
  Provenance probe: `flynapse_api`, `_netguard`, `core`, `utils`, `flynapse_otel`, `shift_optimizer` each
  from the copy or its archive; `PYTHONPATH[0]` = the copy's `tests/_netguard_site`.
- **Mutants** through `mutant.sh` (baseline-checked), aimed, each md5-verified against the `fbd394c` blob
  after restore.
- **Database.** One DB-writing run of the two allowed (Rule B, below); a read-only count afterwards
  found 0 `t-rule-b-%` rows left.

## Lanes at `fbd394c`

| lane | result | note |
|---|---|---|
| unit | 928 passed, 20 skipped, 2 failed, 1 deselected | the failures and extra skips are archive-layout artefacts (no `ws/core` primary checkout; `git` absent) |
| smoke | 21 passed, 3 deselected, "1 wrong-checkout import" | archive artefact, as r8's ‡ |
| startup / api / middleware | 69 / 26 / 310 passed | |
| integration `-m "not postgres"` | 364 passed, 1 failed (`ws/core/core/fastapi_app.py` absent: artefact), 24 deselected | |
| integration collect | 389 | |

**Network census across every lane and the collection:** 0 DNS queries at the witness; 1 libc
`getaddrinfo` and 1 `connect`, both to the forwarder test's own `127.0.0.1:<ephemeral>`; **0 connects to
`:5432`**. The implementer's headline measurement (r8's 16 → 0) holds, now with a witness that could have
seen a lookup.

(Findings, claims table and parts 2 and 3 follow in the final version.)

## Findings so far (PARTIAL, 04:20)

- **Part 1 (r8 batch):** P2 Rule B's which-row test passes ILIKE and suffix-matching accessors (DB run 1,
  both seed orders); P2 the session half is silent under `pytest -n` (import-time refusal: serial rc 1,
  `-n 2` rc 0); P3s: undeclared driver bypasses (`psycopg2.extensions.connection`, `psycopg2._connect`,
  `psycopg.pq.PGconn.connect`, `service=` files), launcher children (`env python -I`, `env -i`), stdlib raw
  sockets (`socket.SocketType`, `super(socket.socket, s).connect`), a Python DNS client through a loopback
  resolver, eight dev-stack ports LISTENING here and not refused, the proxy removal undone by `main.py`'s
  `load_dotenv()`, 11 of 12 reviewer mutants of the guard surviving the aimed lane.
- **Part 2:** P2 the response-body and run-error sweeps' taint misses `+=`, tuple targets, container
  writes and a value set in the handler and used after it (each sweep's own `_offenders`, plus a real-site
  plant that survives); P3 the log sweep's blind spots; the served `reason` column; stale prose in
  `document_hub_cleanup.py`. Guards of `0c176bb`, `0e225bd`, `f985d8d`, `cc56667` KILL their mutants.
- **Part 3:** F4/F5/F9 do not hold at `fbd394c` (fixed at `b6471c8` / `08f54f9`); the `?search=` access-line
  probe is pending.
