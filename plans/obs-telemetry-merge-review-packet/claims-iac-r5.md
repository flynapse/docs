# Claims packet: iac r5 (the post-r4 fix batch `74346bb..d1ebeb1`, plus `234603b`, `013dc89`, `9fda3db`, `5e476e0`) — PARTIAL

**PARTIAL (first version, written right after the lanes).** Independent adversarial review (Opus), 2026-09-22,
read-only. Durable notes: `~/.claude/scratch/obs-merge/iac-review-r5/NOTES.md`.

## Lanes (measured)

Every SHA was cloned (`git clone --no-hardlinks /home/aditya/Code/iac`, checked out inside the clone) under
`~/.claude/scratch/obs-merge/iac-review-r5/clone-<sha>/`. Lane from the clone root:
`DEBUG=false PYTHONPYCACHEPREFIX=<private> pytest-slot.sh -- api/.venv/bin/python -m pytest -q -p no:cacheprovider -n 2`,
then the three validators. rootdir captured with `--co` per clone: the clone itself in all 22. Every clone
`git status --porcelain --ignored` empty after its lane.

| commit | pytest | exit | dashboards | alarms | vocabulary | message says |
|---|---|---|---|---|---|---|
| `74346bb` (base) | 275 passed | 0 | 0 | 0 | 0 | — |
| `d76c439` | 277 passed | 0 | 0 | 0 | 0 | 275 → 277 |
| `f5b73f3` | 277 passed | 0 | 0 | 0 | 0 | 277 → 277 |
| `17a65c1` | 285 passed | 0 | 0 | 0 | 0 | 277 → 285 |
| `bac0f33` | 286 passed | 0 | 0 | 0 | 0 | 285 → 286 |
| `ac5ab23` | 293 passed | 0 | 0 | 0 | 0 | 286 → 293 |
| `6615cb0` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `0963a3e` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `a04b9c0` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `d417b1a` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `61c5297` | 293 passed | 0 | 0 | 0 | 0 | 293 → 293 |
| `4e2a936` | 296 passed | 0 | 0 | 0 | 0 | 293 → 296 |
| `ca095c8` | 296 passed | 0 | 0 | 0 | 0 | 296 → 296 |
| `2965526` | 296 passed | 0 | 0 | 0 | 0 | 296 → 296 |
| `0dda33a` | 301 passed | 0 | 0 | 0 | 0 | 296 → 301 |
| `d1ebeb1` | 302 passed | 0 | 0 | 0 | 0 | 301 → 302 |
| `2d493c8` (base of `9fda3db`) | 83 passed | 0 | 0 | 0 | 0 | — |
| `9fda3db` | 91 passed | 0 | 0 | 0 | 0 | 91 |
| `234603b` | 101 passed | 0 | 0 | 0 | 0 | "101 passed (91 at 9fda3db)" |
| `5e476e0` | 142 passed | 0 | 0 | 0 | 0 | 131 → 142 (CP 15b) |
| `89f3592` (base of `013dc89`) | 206 passed | 0 | 0 | 0 | 0 | — |
| `013dc89` | 243 passed | 0 | 0 | 0 | 0 | — |

Findings, claims table and the four part-2 sections follow in the next revision.
