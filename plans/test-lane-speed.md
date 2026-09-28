# Test-lane speed

Owner-agreed 2026-09-28, after they asked whether the test-run throttle could be loosened. This file is the list of
record. Items 1–3 are acted on; item 4 is a Future Improvement for a later small batch.

## Measurements (2026-09-28)

These come from 219 slotted runs in the obs-follow-up session's agent transcripts, plus live samples.

**Machine**
- The laptop is an Intel Core Ultra 9 185H with 16 cores, 22 logical processors and 32 GB of RAM.
- WSL was given 12 processors and 24 GB of RAM.

**Load**
- Half the runs started with a 1-minute load above 12. A live sample read 27.
- `pytest-slot.sh` allows 6 slots at `-n 4` each. That is 24 workers on 12 CPUs before anything else runs.
- The algotrade session in `~/Code2` shares the same slot files, the same CPUs and the same RAM. In one live sample it
  held 4 of the 6 slots while 4 runs waited.

**Slots and memory**
- No run timed out waiting for a slot.
- At least 6 GB of RAM was free at 215 of 219 starts, so the memory gate almost never binds.
- Wait time was not logged, which item 2 fixes.

**Where the time goes**
- Runs of 5 minutes or more make up 63% of all test time, and runs of 1 minute or more make up 86%.
- copilot-mro's unit lane (about 7,500 tests) took 11–27 minutes, depending on load.

**The floor**
A lane can't finish faster than its slowest test. These are the slowest seen, all in copilot-mro, with times measured
under load:
- `test_sql_spine_activation_mirrors_the_claude_registration_predicates`, in `tests/unit/lang_agent/test_lang_pilot_tool_runtime.py`:
  201 s. It builds a full runtime for every cell of a policy × department × grant matrix.
- The exception-text register scan, in `tests/unit/observability/test_mro_exception_text_register.py`: 39–121 s.
- The SDK tool-handler seating scan: 83 s.
- The no-exception-text-in-logs scan: 24–69 s.
- The depth-coupled-paths guard: 59 s.
- The markers-registered scans: 26–46 s.
- The S3 pagination scans: 34–38 s.
- The cross-repo checkout-name scan: 36 s.
- The tool-results exception-text scan: 34 s.
- The legacy-metrics scan: 29 s.
- The shared-helper import scans: 22–25 s.
- The raw-connection tenancy scan: 22 s.

`tests/integration/otel/test_collector_queue_survives_restart.py` runs for 60–110 s per test, but it is an
integration lane, not the unit lane.

## Decisions (owner, 2026-09-28)

1. **Give WSL more CPUs:** `processors` goes from 12 to 20 in the Windows `.wslconfig`, and memory stays at 24 GB. The
   host has 32 GB, and the earlier VM crashes were host memory starvation.
   - The change applies only after `wsl --shutdown`. That stops every agent and the Docker stack, and it can bring
     back the Postgres stale-bind-mount trap.
   - Claude's edit to the file was refused by the auto-mode classifier, so the owner makes the edit and restarts at a
     quiet point.
   - [ ] Owner edits `.wslconfig` and restarts WSL.
2. **Keep 6 slots, and measure the waits.** Six slots at `-n 4` is 24 workers, which is about right on 20 CPUs.
   - [x] `pytest-slot.sh` (in utils, `utils/dev/.claude/`) now prints how long each run waited. Each finished run also
     appends a line to `~/.claude/scratch/slots/runs.log` with its slot, wait, run time, exit status, free memory, load
     and working directory. The edit is uncommitted, for the owner to commit.
   - [x] The log has been live since 2026-09-28 07:02 PDT. Its first entry shows a 324 s wait for a 1 s run.
   - [ ] Review slot and CPU sizing from `runs.log` after a week of runs.
3. **Run the full lanes less often.**
   - Implementers run only the tests they touch while they work, and each full lane once per round, at the end.
   - A branch's baseline is the controller's post-merge result for the same base SHA; it is never re-run.
   - Reviewers run each full lane once per review. Scoped re-reviews run the fix's tests plus one full run of the
     lanes the fix touched.
   - Mutants are aimed at the test file meant to kill them.
   - [x] Written into the user-erasure P2 lane context, and sent to the running Task 6 implementer.
   - [ ] Carry the rule into every later brief (standing).
4. **Speed up the slowest scan tests.** This is a Future Improvement, for a later small batch.
5. **Fix the lang_agent `[deadline]` load flake** (owner, 2026-09-28: "fix lang_agent only for now"). Branch
   `la-deadline-fix`; ledger `.superpowers/sdd/lang-agent-deadline-flake/`.
   - [x] Fixed (`71be517b`, `9ab0d1a7`; test only). The cause is TIMING, not isolation: the deadline was set before
     setup, which under load used 43–75 ms of a 75/100 ms window. The fix holds the clock until the test's own
     blocking point, and the fixed waits become derived guards. 30/30 green under a simulated starved host; two
     mutants KILLED; unit 7780 passed.
   - [ ] Review (in flight), then merge into `langgraph-merge`. It rides with the P2 push.
   - Follow-ups the implementer reported, for the review to rule on:
     - `test_lang_sad_activation.py` has the same race and can pass without proving anything.
     - The admission test's `cancellation` param proves only "closed before admission".
     - There could be one shared held-clock helper in `_fixtures.py`.

## Future Improvements

### FI-1: Share one parse of the source tree across the whole-repo scans

- **What is slow.** About a dozen copilot-mro unit tests each walk and parse the whole source tree (and some walk
  sibling repos) on their own. Every lane pays that cost roughly a dozen times, and the slowest scan sets the lane's
  minimum wall time under xdist.
- **Why it was deferred.** It is test-infrastructure work across many guard files, and it was found in the middle of
  the user-erasure and eval batches. Changing guards needs its own review, so that a cached parse cannot hide a new
  finding. See the "guards prove shape, not behaviour" lesson.
- **The complete solution.**
  - One session-scoped source index: each file read and parsed once, keyed by path and modification time.
  - Every scan guard consumes that index.
  - Each guard keeps its own planted-decoy test, proving it still sees a fresh violation.
  - Measure before and after with `--durations=30` on a quiet box.

### FI-2: Shrink the lang_agent activation matrix

- **What is slow.** `test_sql_spine_activation_mirrors_the_claude_registration_predicates` builds a full runtime for
  every cell of the policy × department × grant matrix, taking 201 s under load.
- **The complete solution.**
  - Derive the expected activation from the predicates once.
  - Build the runtime only for one representative cell per distinct predicate outcome, plus the edges the docstring
    names (off-MRO for AMOS, and the upload-gated `maintenance-planning`).
  - Or build the catalog without the full runtime, if the activation is a pure function of the turn.
  - Keep the matrix's coverage claim and prove it with a mutant on each predicate.

### FI-3: Split a fast iteration lane from the full lane

- **The idea.** Mark the whole-repo scans and give implementers a lane that skips them for iteration. Full lanes,
  reviews and post-merge runs still include them.
- **The catch.** A marker that deselects guards is easy to misuse. It only pays off if FI-1 leaves the scans still slow.
