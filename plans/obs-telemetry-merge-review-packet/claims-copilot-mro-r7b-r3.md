# Claims packet — copilot-mro r7b r3: the fix-forward batch for review r7b r2

**Verdict: MERGE-CLEAN — P0 0 · P1 0 · P2 1 · P3 5.** The one P2 (the judge endpoint check still does
not read the host the client connects to, in two channels) is a fix-forward, not a merge blocker:
r7b strictly improves on its base, which had no Bedrock host check at all, and merge-blocking is
P0/P1. The five P3s are Future-Improvements candidates, not a new round. The trial merge onto
`obs-merge` `16760afc` costs **one** conflict; against tbD `3637540d` r7b adds **one** more. Both
resolutions are applied, committed and proved green in scratch (§Trial merge).

Independent adversarial review (Opus), 2026-09-22, of `afe79dbb..53411ed7` on `obs-merge-r7b`
(5 commits). This is the **third** reviewer of the lane: the first was killed by a machine restart,
the second (this one) was paused by the owner at the agent cap and resumed; both handed over through
`~/.claude/scratch/obs-merge/r7b-review-r3/{NOTES,PAUSED}.md`, which this packet supersedes.

Read-only on every real tree. Copies are `git clone --shared` checkouts under
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
| full `tests/integration/otel`, serial | HEAD `53411ed7` | **green** — proved as `mutant.sh`'s baseline for the HC5 full-lane replay (the script refuses a red baseline) |
| **the two hand-resolved registers**, serial | **merged tree `347e36d7`** | **212 passed, 1 skipped**, then the skipped cross-repo case **10 passed** with `PHASE1C_UTILS_REPOSITORY` set (§Trial merge) |

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
| `AZURE_OPENAI_ENDPOINT` = **another tenant's** resource | ADMITTED | **declared limit — honest** (§Verdicts) |
| `OPENAI_BASE_URL=evil` beside a good endpoint | ADMITTED | unread spelling — not in `JUDGE_ENDPOINT_VARIABLES` |

### ollama (out of the fix's scope; recorded because the probe reaches it)

`127.0.0.1:11434`, `[::1]:11434`, single-label `ollama`, `*.internal`, `169.254.169.254` admitted (all
declared); `8.8.8.8`, `100.64.0.1` (CGNAT — declared false refusal), `localhost.` refused.
**Undeclared:** the integer IPv4 literals `134744072` and `0x08080808` are admitted as "a single
label", and glibc `inet_aton` resolves both to **8.8.8.8**; the v4-mapped/NAT64 forms
`[::ffff:8.8.8.8]`, `[64:ff9b::808:808]` are refused while `[2001::1]` (Teredo, `is_private=True` in
`ipaddress`) is admitted.

### healthcheck parser (`53411ed7`)

Parser verdict beside what `/bin/sh` actually exits on a failing request:
`exit 01` / `exit 010` admitted (sh exits 1 / 10 — both non-zero, correct); `exit +1`, `exit 1 `
trailing, Arabic-indic digit, `exit $X`, `|| exit 1; exit 0`, CR, tab-separated `;` all refused.
**Three admitted bypasses (P3):** a **newline** then `exit 0`; a **mid-word `#`** then `; exit 0`; a
mid-word `#` then `|| true` — each admitted by the parser while `sh` exits **0** on a failed request.
A word-start `#` comment is admitted and harmless (sh exits 22). The aimed decoy r2 left open, HC5,
is now dead at full-lane scope.

## Trial merge — against `obs-merge` `16760afc` (re-run at finish; evidence is current)

`obs-merge` moved twice during this lane: `80bfa139` → `ce545211` (7 commits) → **`16760afc`**. The
merge was re-run from scratch at each move; **the conflict set is identical at all three bases**. The
last delta, `16760afc`, is one docstring-only commit in
`tests/unit/observability/test_no_exception_text_in_logs.py` — a file r7b's whole branch never
touches (measured: `git diff --name-only <merge-base>..53411ed7` has no hit), so it cannot interact.

Scratch clones: `merge/m6` (r7b then tbD, fully resolved) and `merge/m7` (tbD alone, the control).

**1. r7b `53411ed7` onto `obs-merge` `16760afc` — ONE conflict.**

- `tests/unit/metering/test_usage_ledger_write_guards.py`, two hunks (a docstring and the assertion
  block of the R7B-41 test). Both sides assert the SAME ruled shape — `error_type` + `stack`, no
  rendered traceback — and `obs-merge`'s side is a strict superset (it also pins `tenant_id` and that
  the driver's host does not appear). **Resolution: `--ours` (keep `obs-merge`).** r7b's R7B-41 fix is
  already absorbed there; the file is untouched by this r3 range.
- Merge commit `ba87fd2c`, tree `3cb7519f`; `git diff 16760afc HEAD -- <that file>` is empty.

**2. + tbD `3637540d` — 4 conflicts; the control says r7b adds exactly ONE.**

`merge/m7` (tbD alone onto `16760afc`) conflicts in `scripts/purge_llm_turn_content.py`,
`tests/unit/observability/_mro_exception_text_debt.py` and
`tests/unit/observability/test_phase1c_nonagent_scope_guard.py` — the same three, with or without
r7b. tbD's other r7b-adjacent file, `tests/unit/ad/test_ad_evaluate_transitions.py`, **auto-merges
clean**. **Final merge commit `75b919e8`, tree `347e36d7`, working tree clean.**

| file | whose | resolution | applied & checked |
|---|---|---|---|
| `scripts/ad/evaluate_ad_applicability.py` | **r7b adds this one** | **recipe** (below) | resolved; parses; `failure_fields` imported (line 146, tbD's auto-merged hunk) |
| `scripts/purge_llm_turn_content.py` | tbD's | **`--ours`, whole file** | byte-identical to `16760afc`; zero reaper references |
| `tests/unit/observability/_mro_exception_text_debt.py` | tbD's | **theirs ×2 + carry one comment** | register invariants re-derived: `SEEDED` 508 = `DEBT` 439 + `REPAIRED` 69, `DEBT ⊆ SEEDED`, `REPAIRED == SEEDED − DEBT`, `REPAIRED ∩ DEBT = ∅` |
| `tests/unit/observability/test_phase1c_nonagent_scope_guard.py` | tbD's | **union** | 5 ours + 8 theirs, proved disjoint |

**The merged tree was then run**: `test_no_exception_text_in_logs.py` +
`test_phase1c_nonagent_scope_guard.py` → **212 passed, 1 skipped**; the skip is the cross-repo half
(it wants a `utils` checkout name), re-run with `PHASE1C_UTILS_REPOSITORY=<pinned utils-obsm>` → **10
passed**. Both hand-resolved registers are green.

### The four resolutions in full (the merge agent's input)

1. **`scripts/ad/evaluate_ad_applicability.py`** — r7b's side carries the P1-1 `roster_refusal` arm
   (the `EXIT_DISPATCH_REFUSED` path) that tbD has never seen; tbD's side converts the
   `expected_dispatch_failures` arm to `failure_fields(exc)` and spells out the no-clean-replay prose
   r7b had already factored into `_NO_CLEAN_REPLAY`. **Recipe** (`merge/resolve_eval.py`, r2's,
   re-applied unchanged): keep r7b's `roster_refusal` arm whole; in the `expected_dispatch_failures`
   arm keep r7b's message (with `_NO_CLEAN_REPLAY`), drop the `(%s)` format and its
   `type(exc).__name__` argument, and add tbD's `extra=failure_fields(exc)`. The type name survives
   where it is not a leak (`dispatch_line = f"FAILED ({type(exc).__name__}) — see log"`).
2. **`scripts/purge_llm_turn_content.py` — `--ours` on the WHOLE FILE, and this matters.** `obs-merge`
   (owner ruling M-CAPTURE-TRUNCATE, B8 / G.7(c)) *deleted* the never-built S3 spill and its reaper;
   tbD's entire delta to this file is a `failure_fields` conversion *inside that reaper*. **Trap:**
   four of tbD's hunks here **auto-merge** (the `Callable`/`List` imports, `loguru`, the
   `failure_fields` import, `RETURNING content_s3_key` in `_DELETE_SQL`, `_object_deleter()` and the
   docstring), so resolving only the two *marked* hunks leaves a half-resurrected reaper: a `RETURNING`
   clause and an `_object_deleter` with no `reap_objects` to call them. `git checkout --ours <path>`
   takes the merge's stage-2 blob and discards those too — verified byte-identical to `16760afc`.
3. **`tests/unit/observability/_mro_exception_text_debt.py` — theirs on both hunks, then re-add one
   comment.** Hunk 1: `obs-merge` still lists 50 `scripts/…` keys in `DEBT`; tbD deletes them because
   lane D repaired those sites. Hunk 2: `obs-merge` adds 2 keys to `REPAIRED`
   (`purge_llm_turn_content.py::main`, `::reap_objects`) with an M-CAPTURE-TRUNCATE comment; tbD adds
   68, a superset that already contains both. **Checked before taking theirs:** every one of the 50
   keys leaving `DEBT` is present in tbD's `REPAIRED` additions (`comm -23` empty), so nothing is
   silently dropped. Only `obs-merge`'s explanatory comment is lost, so it is re-added above those two
   keys. **This register is guard-checked both ways** (the sweep must EQUAL `DEBT`; `REPAIRED` is
   append-only and may never meet `DEBT`), so a careless union here goes red — the invariants above
   were re-derived from the merged file and the guard was then run green.
4. **`tests/unit/observability/test_phase1c_nonagent_scope_guard.py` — union, both comments kept.**
   Two disjoint approval blocks: `obs-merge`'s M-CLI-TELEMETRY (`claude_cli_telemetry.py`,
   `sad_runner.py`) + M-CAPTURE-TRUNCATE (`llm_turn_content.py`, `purge_llm_turn_content.py`,
   `drop_llm_turn_content_spill.sql`), and tbD's M-TRACEBACK lane-D list (8 scripts). Disjointness
   asserted, not assumed. `obs-merge`'s `purge_llm_turn_content.py` entry must stay, because
   resolution 2 keeps that file at `obs-merge`'s version.

## Verdicts on the four DECLARED limits

| declared limit | verdict | why |
|---|---|---|
| **`AWS_PROFILE` not read** | **honest for the ACCOUNT question, GAP for the ENDPOINT question** | The docstring's reason — a host cannot prove which account the credentials name — is true and the right call. But `AWS_PROFILE` is not only an account selector: it selects the shared-config section that carries **`endpoint_url`**, which is precisely the destination this check claims to hold. Measured: with no endpoint environment variable set, a profile or `services` `endpoint_url` is ADMITTED and botocore connects to the API Gateway, ALB or `evil.example` it names. The check reads the environment spellings of that setting and not the file spelling of the same setting — a gap in its stated contract, not a limit of what a host can prove. **Folded into the P2.** |
| **other-tenant `AZURE_OPENAI_ENDPOINT` admitted** | **honest limit** | `x.openai.azure.com` genuinely carries no tenant information; proving ownership needs a network call against a declared tenant id, which this check deliberately does not make. The design compensates where it can: the variable is REQUIRED, must be ONE resource label under the three real service domains, and every other azure spelling must name the SAME host (measured: other-resource and `cognitiveservices`-spelling variants refused). The residual risk is a deployment that declares its own resource wrongly — the credentials' job, as the docstring says. **No action.** |
| **count-race refusal** (`69229bb7`) | **honest, narrow trade-off — record it** | The direction is right and fail-closed: r2's R7B2-07 was that a short roster was taken as the roster and tenants were silently dropped. Mutants P31N/P31C/P31D/P31E all die, so the check is real. The cost is a FALSE refusal when a signup lands between the walk and the count — a window core narrowed but did not close — and it lands on a CLI whose dispatch has no clean replay (the verdicts are committed; the announcement is what is lost). **P3, Future Improvement**, not a blocker. |
| **ollama `.internal` / link-local / single-label admitted** | **honest as declared — but the integer IPv4 literal is an UNDECLARED GAP** | A self-hosted server on a private network is exactly what the rule is for, and `169.254.169.254` is named in the declaration. The undeclared part: `_is_private_host` treats "no dot" as a private single label, so the integer literals `134744072` and `0x08080808` pass — and glibc `inet_aton` resolves both to **8.8.8.8**. That is not "a name no public resolver answers"; it is a public address in disguise, and it defeats the single-label test by construction. **P3, Future Improvement.** (`[2001::1]` being admitted follows `ipaddress`'s own `is_private`, a weaker finding.) |

## Findings

- **P2 — the judge endpoint check does not read the host the client connects to (two channels, one
  defect).** (a) An `endpoint_url` in the AWS shared config file (profile key or `services` section,
  selected by `AWS_PROFILE` / `AWS_CONFIG_FILE`) is **ADMITTED** and botocore connects to the API
  Gateway, ALB or arbitrary host it names — measured. The check reads environment variables only.
  (b) `https://evil.example\@bedrock-runtime.<region>.amazonaws.com` is **ADMITTED** (`urlsplit`
  splits the netloc on the last `@`, so it sees Bedrock) while urllib3, requests and botocore treat
  `\` as an authority delimiter and connect to `evil.example` — measured; the same differential
  admits a backslash-userinfo `AZURE_OPENAI_ENDPOINT`. This refutes r2's "no client differential
  there" and is the same class of hole `d91ff4a1` set out to close. **Fix-forward, not a blocker:**
  the base admitted *any* `*.amazonaws.com` host, so r7b is strictly better, and the attacker needs
  config-write access the check was never a boundary against.

### Future Improvements (P3 — for the plan file, not a new round)

1. **Healthcheck parser bypasses.** A newline, or a mid-word `#`, followed by `exit 0` / `|| true` is
   admitted while `/bin/sh` exits **0** on a failed request. The parser lexes the probe as one line
   and treats `#` as a comment only at word start. The complete fix is to refuse a probe containing a
   newline outright and to treat `#` as a comment introducer wherever the shell does, rather than
   extending the status-token rule again; HC5 showed the token rule is now sound.
2. **The count-race refusal** (see §Verdicts). The elegant fix is to read the page set and the count
   in ONE statement, or to re-walk once on a mismatch before refusing, so a concurrent signup costs a
   retry rather than an unreplayable refusal.
3. **Scheme unchecked.** `http://`, `ftp://` and `file://` Bedrock endpoints are admitted;
   `_endpoint_host` keeps only the hostname. `http://` is the live one — it silently downgrades TLS to
   a host the check has otherwise pinned. The fix is to require `https` (and to keep the bare
   `host:port` shape `OLLAMA_HOST` needs).
4. **`.amazonaws.com.cn` cannot be configured.** The China partition's real Bedrock host
   (`bedrock-runtime.cn-north-1.amazonaws.com.cn`) is refused by the `\.amazonaws\.com` tail. Nothing
   deploys there today, so this is a latent false refusal, not a live break; the fix is a partition
   alternation in `_BEDROCK_RUNTIME_HOST`, not a suffix relaxation.
5. **ollama integer IPv4 literals** (see §Verdicts). The fix is to try `inet_aton`-style parsing (or
   reject all-digit / `0x` hosts) before falling back to the "no dot = single label" rule.

**Also worth carrying, though not a finding against r7b:** the trailing-dot false refusal
(`…amazonaws.com.` is a legal FQDN form) is declared and deliberate, and stripping one trailing dot
before the match would remove it at no cost to the check.
