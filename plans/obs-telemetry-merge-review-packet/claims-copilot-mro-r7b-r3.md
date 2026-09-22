# Claims packet — copilot-mro r7b r3: the fix-forward batch for review r7b r2 — PARTIAL

**PARTIAL (first version, written after lane R).** Verdict pending: lane T, mutation batch, per-commit
greenness and the trial-merge lanes are still running. Findings below are measured; counts will move.

Independent adversarial review (Opus), 2026-09-22, of `afe79dbb..53411ed7` on `obs-merge-r7b`
(5 commits). Read-only on every real tree. Copies are `git clone --shared` checkouts under
`~/.claude/scratch/obs-merge/r7b-review-r3/{ws,wsm,merge}/`; siblings are pinned shared clones
(`sib/SHAS.txt`: core-obsm `42785ed`, utils-obsm `fe45c35`, api-obsm `fbd394c`, flynapse-otel
`1749854`, dashboard-obsm `f8c4614`). A `sitecustomize` guard (`site/`) strips primary-checkout
`.pth` paths and refuses non-loopback DNS/connect and docker/psql/aws execs; `rootdir` is the copy in
every log.

| range | commits |
|---|---|
| `afe79dbb..53411ed7` (5) | `d91ff4a1` P2-1 residency host shape · `69229bb7` P3-1 roster count · `78303518` P3-2 wrong type · `7a2e5648` P3-3 exit 3 · `53411ed7` P3-4 healthcheck 1–255 |

## Lanes (so far)

| lane | tree | result |
|---|---|---|
| **R** (r2's 22 files), `-n 2` | HEAD `53411ed7` | **695 passed, 1 failed** (known `test_langchain_ambient_surface_policy`, fixed on obs-merge `16d5d1d1`), 2 skipped (docker absent) — equals the implementer's 695/1/2 |

## Findings so far

- **P2 (candidate) — the bedrock check does not read the host botocore connects to.** (a) An
  `endpoint_url` in the AWS shared config file (profile key or `services` section, chosen by
  `AWS_PROFILE`/`AWS_CONFIG_FILE`) is ADMITTED; botocore connects to the API Gateway / ALB / any host
  it names (measured). (b) `https://evil.example\@bedrock-runtime.<region>.amazonaws.com` is ADMITTED
  (urlsplit sees Bedrock) while botocore/urllib3 and requests connect to `evil.example` (measured) —
  refutes r2's "no client differential there".
- **P3 (candidate) — healthcheck parser:** a newline, or a mid-word `#`, followed by `exit 0` is
  admitted; `/bin/sh` exits 0 on a failed request (measured).
- **P3 (candidate) — the post-walk count read** re-opens the two-statement window core closed; a
  signup in it refuses an evaluate-CLI fan-out that has no clean replay.
- **P3 (candidate) — ollama:** an integer IPv4 literal (`134744072`, `0x08080808`) passes as a
  "single label"; glibc resolves it to `8.8.8.8`.
