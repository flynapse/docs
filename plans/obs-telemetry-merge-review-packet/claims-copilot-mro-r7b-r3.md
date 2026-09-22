# Claims packet — copilot-mro r7b r3: the fix-forward batch for review r7b r2 — PARTIAL

**PARTIAL (second version, written at the owner's PAUSE, agent cap cut to 1).** Verdict still pending:
three trial-merge conflict resolutions (tbD's own, not r7b's) and the verdicts on the four declared
limits are not finalised. Everything below is measured. The reviewer who started this lane was killed;
this is the resuming reviewer. Resume state: `~/.claude/scratch/obs-merge/r7b-review-r3/PAUSED.md`.

**Owner-trimmed scope (last r7b round, LIGHT):** (1) host/proxy/azure probes against `d91ff4a1`;
(2) a trial merge vs CURRENT `obs-merge` HEAD and vs tbD `3637540d`; (3) ≤6 mutants on the P2-1 host
check plus r2's HC5 replayed against the FULL otel lane. Touched suites at `53411ed7` only. No
per-commit sweep; P3s are Future-Improvements candidates, not a new round.

Independent adversarial review (Opus), 2026-09-22, of `afe79dbb..53411ed7` on `obs-merge-r7b`
(5 commits). Read-only on every real tree. Copies are `git clone --shared` checkouts under
`~/.claude/scratch/obs-merge/r7b-review-r3/{ws,wsm,merge}/`; siblings are pinned shared clones
(`sib/SHAS.txt`: core-obsm `42785ed`, utils-obsm `fe45c35`, api-obsm `fbd394c`, flynapse-otel
`1749854`, dashboard-obsm `f8c4614`). A `sitecustomize` guard (`site/`) strips primary-checkout
`.pth` paths and refuses non-loopback DNS/connect and docker/psql/aws execs; `rootdir` is the copy in
every log. No docker, DB write, network or AWS call was made; every run went through `pytest-slot.sh`,
one at a time, at `-n 2` or less.

| range | commits |
|---|---|
| `afe79dbb..53411ed7` (5) | `d91ff4a1` P2-1 residency host shape · `69229bb7` P3-1 roster count · `78303518` P3-2 wrong type · `7a2e5648` P3-3 exit 3 · `53411ed7` P3-4 healthcheck 1–255 |

## Lanes

| lane | tree | result |
|---|---|---|
| **R** (r2's 22 touched files), `-n 2` | HEAD `53411ed7` | **695 passed, 1 failed, 2 skipped**. The one red is `test_langchain_ambient_surface_policy`, red at r7b's base too and fixed on `obs-merge` by `16d5d1d1`; the skips are the two docker-gated Grafana cases. Equals the implementer's own 695/1/2 |
| **full `tests/integration/otel`**, serial | HEAD `53411ed7` | **green** — proved as `mutant.sh`'s baseline for the HC5 full-lane replay (the script refuses a red baseline) |

Lane T (the 8 touched dirs) was stopped under the owner's trim; the implementer's own T at `53411ed7`
reads 5501 passed / 10 failed / 30 skipped, its 10 reds being r2's pre-existing xdist set (both files
green serially).

## Mutation proofs

`mutant.sh` on a copy (`wsm/`), cold bytecode, one at a time through `pytest-slot.sh`, serial,
`-p no:randomly`; every restore verified against `git show 53411ed7:<path>` (all MATCH).

| mutant | file | aimed at | result |
|---|---|---|---|
| RES4 bedrock `search` not `fullmatch` | `contracts.py` | `test_judge_provider_residency.py` | **KILLED** rc=1 6s |
| RES5 region = any label | `contracts.py` | ″ | **KILLED** rc=1 6s |
| RES6 `.amazonaws.com` suffix back | `contracts.py` | ″ | **KILLED** rc=1 6s |
| RES7 proxy check off | `contracts.py` | ″ | **KILLED** rc=1 9s |
| RES9 azure same-resource check off | `contracts.py` | ″ | **KILLED** rc=1 7s |
| RES12 proxy value echoed in the message | `contracts.py` | ″ | **KILLED** rc=1 6s |
| HC5 `\|\| exit 256` (r2's survivor) | `deployment/docker-compose.yml` | `test_grafana_service_health_and_env.py` | **KILLED** rc=1 5s |
| **HC5 `\|\| exit 256`, FULL otel lane** | `deployment/docker-compose.yml` | **all of `tests/integration/otel`** | **KILLED** rc=1 16s |

**7 distinct mutants, 8 runs, 8 KILLED, 0 survivors.** The last row is the one the implementer skipped
and r2's open **P3-4**: r2 recorded HC5 as surviving *including the full otel lane*; at `53411ed7` it
dies there too. **R7B2-18 / P3-4 is CLOSED.**

## Probe table — the P2-1 host check (`d91ff4a1`) exercised directly

Direct calls into `require_in_account_endpoint` with env dicts, beside the host each HTTP client
actually resolves (`urlsplit` / urllib3 2.5.0 / httpx 0.28.1 / requests 2.32.5 / botocore, the last
always refused at connect by the guard, so only the *chosen* host is read). No real connect was made.
Raw: `probes/{parse_diff,env_probe,roster_probe,hc_probe,r2_table_replay}.out`.

### bedrock host shape

| case | value | check | clients see | verdict |
|---|---|---|---|---|
| real regional | `https://bedrock-runtime.us-east-1.amazonaws.com` | ADMITTED | same | correct |
| **case** | `https://BEDROCK-RUNTIME.US-EAST-1.AMAZONAWS.COM` · `bedrocK-runtime…` | ADMITTED | same | correct (host lower-cased before match) |
| **trailing dot** | `…amazonaws.com.` | refused | same | declared false refusal — a real FQDN form is rejected |
| **port** | `…amazonaws.com:8443/x?y#z` | ADMITTED | same | correct (port/path/query not part of the host) |
| **scheme** | `http://…` · `ftp://…` · `file://…/etc/passwd` | ADMITTED | same | **gap (P3):** the scheme is never checked; `http://` downgrades TLS, `ftp`/`file` only fail later in botocore |
| bare host | `bedrock-runtime.us-east-1.amazonaws.com` (no scheme) | ADMITTED | botocore `ValueError: Invalid endpoint` | harmless |
| **userinfo** | `https://bedrock-runtime…amazonaws.com@evil.example` | refused | `evil.example` | correct |
| **userinfo, backslash** | `https://evil.example\@bedrock-runtime…amazonaws.com` | **ADMITTED** | urllib3 `evil.example`, requests `evil.example`, **botocore connects `evil.example`** | **BYPASS (P2)** — `urlsplit` splits on the last `@`, the clients treat `\` as an authority delimiter. Doubled `\\` likewise. Refutes r2's "no client differential there" |
| userinfo, `%5C` / `/@` / `#@` / `?@` | — | as expected | no differential | correct |
| userinfo, `;@` | `https://evil.example;@bedrock-runtime…` | ADMITTED | all clients see bedrock | no differential — harmless |
| userinfo, tab / newline | — | ADMITTED | botocore `ValueError: Invalid endpoint` | harmless (client rejects) |
| **`.amazonaws.com.cn`** | `https://bedrock-runtime.cn-north-1.amazonaws.com.cn` | refused | same | **declared-shape gap (P3):** the China partition's real Bedrock host cannot be configured |
| **region shape** | `…bedrock-runtime.us-east-99.amazonaws.com` · `…aa-bbbb-1…` | ADMITTED | same | shape-only, as documented; no region registry. The S3 legacy host `bedrock-runtime.s3-us-west-2…` is refused (the fix's stated target) |
| **`-fips` placement** | `bedrock-runtime-fips.<r>.amazonaws.com` ADMITTED · `bedrock-fips-runtime.<r>…` refused | | same | correct — only the real spelling passes |
| **vpce placement** | `vpce-1.bedrock-runtime-fips.<r>.vpce.amazonaws.com` ADMITTED · `vpce-1.evil.bedrock-runtime.<r>.vpce…` refused | | same | correct |
| IDN / punycode | `bеdrock-runtime…` (Cyrillic е) · `xn--bdrock-runtime-7kb…` | refused | urllib3/requests punycode it | correct |
| `%2e` / `%00` / `\evil.example` / `//host` / `[::1]` | — | refused | — | correct |
| **AWS shared-config `endpoint_url`** | profile key, `services` section, or via `AWS_PROFILE` | **ADMITTED** (no env var is set) | **botocore connects to the API-Gateway / ALB / `evil.example` it names** | **BYPASS (P2)** — the check reads only environment variables; the config FILE is an unread channel to the same setting |

### proxies

Every `*_proxy` spelling planted with a sentinel-bearing value on a bedrock run:
`HTTPS_PROXY`, `https_proxy`, `Https_Proxy`, `HTTP_PROXY`, `http_proxy`, `ALL_PROXY`, `all_proxy`,
`FTP_PROXY`, `SOCKS_PROXY`, `socks5_proxy`, `WS_PROXY` — **all refused**, and on azure too.
`' http://mitm:3128 '` (padded) refused. `HTTPS_PROXY=''` / `'   '` admitted (they route nothing —
`urllib.getproxies()` confirms an all-whitespace value yields `{'https': '  '}`, which requests
treats as no proxy). `NO_PROXY=*` alone admitted; `HTTPS_PROXY` + `NO_PROXY=*` still refused, as the
docstring declares. **No refusal message echoed the sentinel.** `AWS_CA_BUNDLE=/evil.pem` alone
admitted, as declared. r2's surviving `HTTPS_PROXY` + `AWS_CA_BUNDLE` case is now refused.

### azure

| case | check | verdict |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` alone | ADMITTED | correct |
| `AZURE_API_BASE` alone | refused | correct (the deployment variable is required) |
| `AZURE_API_BASE` same host, UPPER + port + path | ADMITTED | **same-host normalisation holds** |
| `AZURE_API_BASE` same host, other port `:8443` / `http://` | ADMITTED | host-grain by design; scheme and port unread |
| `AZURE_API_BASE` other resource, same service | refused | correct |
| `AZURE_API_BASE` same resource, `cognitiveservices` spelling | refused | correct — a different host is a different host |
| `AZURE_OPENAI_ENDPOINT` trailing dot / whitespace / userinfo `evil@` | refused | correct |
| `AZURE_OPENAI_ENDPOINT` **backslash userinfo** | ADMITTED | the same parser differential as bedrock (P2 above) |
| `AZURE_OPENAI_ENDPOINT` bare host, no scheme | ADMITTED | harmless |
| `AZURE_OPENAI_ENDPOINT` `xn--` label | ADMITTED | a punycode resource label is a legal one-label host |
| `AZURE_OPENAI_ENDPOINT` = **another tenant's** resource | ADMITTED | **declared limit** (verdict below) |
| `OPENAI_BASE_URL=evil` beside a good endpoint | ADMITTED | unread spelling — not in `JUDGE_ENDPOINT_VARIABLES` |

### ollama (out of the fix's scope; recorded because the probe reaches it)

`127.0.0.1:11434`, `[::1]:11434`, single-label `ollama`, `*.internal`, `169.254.169.254` admitted (all
declared); `8.8.8.8`, `100.64.0.1` (CGNAT — declared false refusal), `localhost.` refused.
**Unexpected, not declared:** the integer IPv4 literals `134744072` and `0x08080808` are admitted as
"a single label", and glibc `inet_aton` resolves both to **8.8.8.8**; the v4-mapped/NAT64 forms
`[::ffff:8.8.8.8]`, `[64:ff9b::808:808]` are refused while `[2001::1]` (Teredo, `is_private=True` in
`ipaddress`) is admitted. P3 candidates.

### healthcheck parser (`53411ed7`)

Parser verdict beside what `/bin/sh` actually exits on a failing request:
`exit 01` / `exit 010` admitted (sh exits 1 / 10 — both non-zero, correct); `exit +1`, `exit 1 `
trailing, Arabic-indic digit, `exit $X`, `|| exit 1; exit 0`, CR, tab-separated `;` all refused.
**Three admitted bypasses (P3):** a **newline** then `exit 0`; a **mid-word `#`** then `; exit 0`; a
mid-word `#` then `|| true` — each admitted by the parser while `sh` exits **0** on a failed request.
A word-start `#` comment is admitted and harmless (sh exits 22).

## Trial merge — vs CURRENT `obs-merge` HEAD `ce545211`

`obs-merge` moved 7 commits past the `80bfa139` the killed reviewer used, so the merge was redone.
Scratch clones `merge/m4` (r7b then tbD) and `merge/m5` (tbD alone, the control).

**1. r7b `53411ed7` onto `obs-merge` `ce545211` — ONE conflict.**

- `tests/unit/metering/test_usage_ledger_write_guards.py`, two hunks (a docstring and the assertion
  block of the R7B-41 test). Both sides assert the SAME ruled shape — `error_type` + `stack`, no
  rendered traceback — and `obs-merge`'s side is a strict superset (it also pins `tenant_id` and that
  the driver's host does not appear). **Resolution: `--ours` (keep `obs-merge`).** r7b's R7B-41 fix is
  already absorbed there; the file is untouched by this r3 range.
- Merge commit `9e39317d`, tree `920b1399`; `git diff ce545211 HEAD -- <that file>` is empty.

**2. + tbD `3637540d` — 4 conflicts; the control says r7b adds exactly ONE.**

`merge/m5` (tbD alone onto `ce545211`) conflicts in `scripts/purge_llm_turn_content.py`,
`tests/unit/observability/_mro_exception_text_debt.py` and
`tests/unit/observability/test_phase1c_nonagent_scope_guard.py` — the same three. tbD's other r7b-adjacent
file, `tests/unit/ad/test_ad_evaluate_transitions.py`, **auto-merges clean**.

- **`scripts/ad/evaluate_ad_applicability.py` — the one r7b adds. RESOLVED and applied in `m4`.**
  r7b's side carries the P1-1 `roster_refusal` arm (the `EXIT_DISPATCH_REFUSED` path) that tbD has
  never seen; tbD's side converts the `expected_dispatch_failures` arm to `failure_fields(exc)` and
  spells out the no-clean-replay prose r7b had already factored into `_NO_CLEAN_REPLAY`.
  **Recipe (`merge/resolve_eval.py`, r2's, re-applied):** keep r7b's `roster_refusal` arm whole; in
  the `expected_dispatch_failures` arm keep r7b's message (with `_NO_CLEAN_REPLAY`), drop the `(%s)`
  format and its `type(exc).__name__` argument, and add tbD's `extra=failure_fields(exc)`. Verified
  after: no conflict markers, `failure_fields` imported (line 146, from tbD's auto-merged hunk), and
  the type name survives where it is not a leak (`dispatch_line = f"FAILED ({type(exc).__name__})…"`).

**Still to finalise (not r7b's, but the merge agent needs them) — see PAUSED.md:** the three tbD-only
conflicts. Intended resolutions, from the hunks read: `purge_llm_turn_content.py` = **ours**
(`obs-merge`'s M-CAPTURE-TRUNCATE deleted the S3 reaper tbD's hunk re-adds);
`_mro_exception_text_debt.py` = **theirs** (tbD paid the debt down — `DEBT` entries deleted, keys moved
into `REPAIRED`; it already carries the two `purge_llm_turn_content` keys `obs-merge` added, but
`obs-merge`'s M-CAPTURE-TRUNCATE comment is lost and must be carried over);
`test_phase1c_nonagent_scope_guard.py` = **union** (two disjoint approval blocks, M-CLI-TELEMETRY /
M-CAPTURE-TRUNCATE from `obs-merge` and M-TRACEBACK lane D from tbD).

## Findings

- **P2 — the bedrock/azure host check does not read the host the client connects to (two channels).**
  (a) An `endpoint_url` in the AWS shared config file (profile key or `services` section, selected by
  `AWS_PROFILE` / `AWS_CONFIG_FILE`) is **ADMITTED** and botocore connects to the API Gateway, ALB or
  arbitrary host it names — measured. The check reads environment variables only. (b)
  `https://evil.example\@bedrock-runtime.<region>.amazonaws.com` is **ADMITTED** (`urlsplit` sees
  Bedrock) while urllib3, requests and botocore connect to `evil.example` — measured; the same
  differential admits a backslash-userinfo `AZURE_OPENAI_ENDPOINT`. This refutes r2's "no client
  differential there" and is the same class of hole `d91ff4a1` set out to close.
- **P3 — the healthcheck parser** admits a newline, or a mid-word `#`, followed by `exit 0` / `|| true`;
  `/bin/sh` then exits 0 on a failed request. (The aimed decoy r2 left open, HC5, is now dead.)
- **P3 — the post-walk count read** (`69229bb7`) re-opens the two-statement window core closed: a
  signup landing between the walk and the count refuses an evaluate-CLI fan-out that has no clean
  replay. (Verdict on the implementer's declared trade-off: pending.)
- **P3 — scheme unchecked**: `http://`, `ftp://` and `file://` Bedrock endpoints are admitted.
- **P3 — `.amazonaws.com.cn`**: the China partition's real Bedrock host cannot be configured.
- **P3 — ollama** admits an integer IPv4 literal (`134744072`, `0x08080808`) as a "single label";
  glibc resolves both to `8.8.8.8`. Also admits `[2001::1]`.

## Verdicts on the declared limits

PENDING (see PAUSED.md). Draft, from the measurements above: *AWS_PROFILE unread* — honest limit for
the account question, but it is **not** honest for the endpoint question, because the same file
`AWS_PROFILE` selects also carries `endpoint_url`, which is a destination the check claims to hold
(P2a). *Other-tenant `AZURE_OPENAI_ENDPOINT` admitted* — honest limit (a host cannot prove a tenant).
*Count-race refusal* — honest, narrow trade-off. *ollama `.internal` / link-local admitted* — honest
limit as declared; the integer-literal admission is a **gap**, not a declared limit.
