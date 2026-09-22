# PARTIAL — Claims packet — utils review round 9 (`179cc6d..fe45c35`)

**PARTIAL: the review is running.** The per-commit sweep, the real-lane decoys and the mutation proofs are still
running. Findings below are probe-backed. Their severities are provisional until the lanes land.

Independent adversarial review (Opus), 2026-09-22. Read-only against every real tree. utils-obsm HEAD is `fe45c35`
and clean. The copies are `git archive`s in `~/.claude/scratch/obs-merge/utils-review-r9/work/{head,base}`.
Durable notes are in `~/.claude/scratch/obs-merge/utils-review-r9/NOTES.md`.

## Findings so far (provisional)

- **P1-1 (provisional): the fail-closed reader still passes key-adding writes and family misreads silently.**
  I ran 59 plants through `_emissions` at `fe45c35` (`probes/attack1.py`). All 18 silent-GREEN shapes are
  pre-existing. The redesign closed 20 others that were silent at `179cc6d`.
  - A chained assignment (`labels = alias = {…}; alias["email"] = e`) passes, and so do the 3-way and `|=` forms.
  - A forwarder referenced without being called passes (alias, `functools.partial`, callback, `getattr` by string).
  - A decorator that injects a key into a forwarder passes.
  - So does a wrapper class method named `increment_counter` or `record_histogram` (wrong keys, wrong kind), and an
    `import … as` alias of a metric function or of the Document Hub wrapper.
  - On the family side, an IMPORTED constant rebound in the importing module passes (under `if`, through `global`,
    top-level non-literal, by `for`, `with`, `def`, or in a re-exporter). So do module-level `locals()` and `vars()`.
- **P3 (provisional):** in `fabb94c`, an exception inside a container inside `args` (tuple, list or dict) is not
  reached. A quote of it ships.
- **P3 (provisional):** P3-6's docstring pin reads only bullet lines. The r8 M25 prose replay is expected to survive.
- **P3 (provisional):** in P3-4, the identity pin guards `_RESERVED_LOG_RECORD_ATTRIBUTES`. The seat the bridge uses is
  `_RESERVED_ATTRIBUTES` (`log_bridge.py:119,154`).
- **P3 (provisional):** in P3-5, the SQL rule misses SQL that does not open the string (a comment, `BEGIN;`, a CTE,
  `executescript`). It also misses concatenated SQL, `DROP MATERIALIZED VIEW/TYPE/EXTENSION/OWNED`, Redis
  `execute_command("FLUSHALL")` and Redis `unlink`.

The estate view is re-derived: 24 emissions, 0 unresolved, byte-identical between `fe45c35` and `179cc6d`, against
copilot-mro-obsm `c27db590`.
