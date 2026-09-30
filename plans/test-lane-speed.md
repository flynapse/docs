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
   - [x] `.wslconfig` now reads `processors=20` (Claude edited it on the owner's request, 2026-09-28).
   - [x] Owner ran `wsl --shutdown` (2026-09-29 ~04:50, all agents paused first); `nproc` reads 20 on resume. Postgres
     came back with its databases intact (no stale-bind-mount trap this time).
2. **Keep 6 slots, and measure the waits.** Six slots at `-n 4` is 24 workers, which is about right on 20 CPUs.
   - [x] `pytest-slot.sh` (in utils, `utils/dev/.claude/`) now prints how long each run waited. Each finished run also
     appends a line to `~/.claude/scratch/slots/runs.log` with its slot, wait, run time, exit status, free memory, load
     and working directory. Committed in utils as `47b125f` on `langgraph-merge` (not pushed).
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
   - **Superseded 2026-09-29** by the owner's workspace CLAUDE.md edit (utils `a0f1ee4`, `57c913a`, pushed): "Full
     suites: one per change, plus the merge".
     - Implementers run the FULL suite once, at hand-back, on their tip.
     - Reviewers and re-reviews run only the test folders the diff touches.
     - The full suite at the merge commit is the gate.
     - A surviving mutant's "full lane" is the folders that cover the mutated module.
     - [x] Audit of the running agents against the new rule (runs.log). Reviewers complied, apart from one whole-unit
       run already in flight at the change and two ~20 s iac full lanes. Implementers ran what their briefs named.
     - **Gap found:** the briefs and the controller's post-merge gates named SUBSETS as the "full suite":
       - copilot-mro: `tests/unit`, three `tests/db` folders and `tests/api/document_hub`;
       - core: `tests/unit tests/api` and `tests/db/user_erasure`.

       About 17 copilot-mro top-level test folders (`registries`, `agent_sdk`, `memory`, `ingestion`, `seeds`,
       `smoke` …), most of `tests/api` and `tests/db`, and core's `tests/authz` ran in no gate. That is how the
       copilot-mro route-table red (the erasure router missing from `CORE_ROUTER_MODULES`) was pushed twice.
     - [x] First real full suites run (2026-09-29, user-erasure P2 follow-up merge). The recipe is
       `~/.claude/scratch/user-erasure/p2c2-postmerge/gate.sh`:
       - every test folder except e2e and the live-service markers;
       - db serial;
       - copilot-mro `tests/db` one subfolder per run;
       - three streams, at most 8 workers.

       It surfaced copilot-mro reds that no subset gate had ever run, all pre-existing:
       - `tests/config/settings/test_config.py` ×3;
       - `tests/parsers/pilot/test_parser_metadata_sidecars.py` ×1;
       - whole-tree-only pollution: `test_debug_dumps.py` ×10, `test_lang_sad_activation.py` ×1, and the
         `test_chat_turn_facts_*` collection errors from a `_workspace` name collision.

       The details are in the user-erasure plan's "P2 CLOSED" block.
     - [ ] Owner decision pending: define one real full-suite command set per repo (everything except e2e and live
       tests; db folders serial; known reds listed: copilot-mro `tests/db` FI-12, the 4 xdist-only errors in
       `tests/api/tenancy/test_operator_grain_isolation.py`, core's workspace-layout reds), measure it once, then name
       it in every brief and post-merge gate. Recommended: yes.
4. **Speed up the slowest scan tests.** This is a Future Improvement, for a later small batch.
   - [ ] FI-2 first (owner, 2026-09-29: "go"): shrink the lang_agent activation matrix. SDD, fresh Opus implementer
     and reviewer; branch `activation-matrix` in `copilot-mro-matrix`; ledger `.superpowers/sdd/lang-activation-matrix/`.
     Measured before and after on the same box state. FI-1 waits for FI-2's measurement.
   - **FI-2 DONE (2026-09-29/30), merged and pushed with copilot-mro `1bfe2e70`.** Test-side only: every one of the
     150 cells still builds the full real runtime; the metaschema check of each distinct tool schema, the turn's
     catalog and the model factory are done once per matrix. The test went from 63–75 s (201 s under load) to 6–7 s
     quiet and 19 s at load 15. 20/20 mutants killed by both the old and the new test. Known gap: a defect seen only
     when the universe catalog is built a second time (the review's M21) is caught by the `tests/unit/lang_agent` lane,
     not this test.
   - [ ] **Production follow-up (owner, 2026-09-30: "go ahead"):** remember each tool schema that passed the metaschema
     check, per process (about 0.6–0.7 s of CPU saved per rich lang turn). Passes only, keyed on a sha256 of the
     canonical JSON, bounded; the test fixture goes. Ledger `.superpowers/sdd/schema-check-memo/`, branch
     `schema-check-memo`. The table-registry cache was judged not worth its risk (about 40 ms per turn).
5. **Fix the lang_agent `[deadline]` load flake** (owner, 2026-09-28: "fix lang_agent only for now"). Branch
   `la-deadline-fix`; ledger `.superpowers/sdd/lang-agent-deadline-flake/`.
   - [x] Fixed (`71be517b`, `9ab0d1a7`; test only). The cause is TIMING, not isolation: the deadline was set before
     setup, which under load used 43–75 ms of a 75/100 ms window. The fix holds the clock until the test's own
     blocking point, and the fixed waits become derived guards. 30/30 green under a simulated starved host; two
     mutants KILLED; unit 7780 passed.
   - [x] Reviewed (Opus): Spec ✅, quality approved, 0 blocking. It reproduced both signatures on `cee26494` and ran
     17 mutants; all but 4 minor gaps were killed. Review: `.superpowers/sdd/lang-agent-deadline-flake/review.md`.
   - [x] Merged `--no-ff` into copilot-mro `langgraph-merge` as `81a4b93a` (local). It rides with the P2 push.
   - [x] Post-merge `tests/unit -n 4` at `81a4b93a`: 7961 passed, 10 skipped, 0 failed (9 min 23 s). Worktree and branch removed.
   - The review's Minor findings and the implementer's follow-ups are FI-4 to FI-7 below.

6. **Keep the bytecode cache warm in `mutant.sh`** (owner, 2026-09-29: "ok. just this for now"). Today every
   invocation runs the command twice, the unmutated baseline and then the mutant, each with a brand-new empty cache
   prefix. So every run recompiles the whole import graph (the tree, its siblings, the venv's packages and the
   standard library), and a batch of ten mutants does it twenty times. The stale-bytecode trap the cold start guards
   against concerns the MUTATED file. So: keep one persistent cache per tree state, and never let the mutated file run
   from cached bytecode.
   - Batch: SDD, fresh Opus implementer and fresh Opus reviewer; branch `mutant-warm-cache` in `utils-mutant`; ledger
     `.superpowers/sdd/mutant-warm-cache/`.
   - [x] Build: a persistent cache prefix under `~/.claude/scratch/`, never the tree's own `__pycache__`. It is reused
     only while the tree's content is unchanged, and old prefixes are pruned. The mutated file's cache entries are
     removed before every run and on every restore path. A cold opt-out reproduces today's behaviour. The first
     automated tests for `mutant.sh`, including the same-size, same-second stale case.
   - [x] Measure one real copilot-mro mutant: old script, then the new script cold, then warm, with the same verdict
     each time.
   - [x] Review, merge into utils `langgraph-merge` only while no `mutant.sh` is running (bash reads a script as it
     runs), and update CLAUDE.md's bytecode line.
   - **Done 2026-09-29.** Merged as utils `04dc293` and pushed.
     - Review history: one review (F1, Important: a second signal could cut the restore short and fake a verdict in
       both directions), then two fix rounds and a re-review.
     - Measured on one copilot-mro mutant: old script 178 s, new script cold 137 s, warm 110–133 s, with the same
       verdict every time. The gain is about 20–35%.
     - The utils suite at the merge: 2060 passed, plus the 6 sibling-worktree census reds.
     - Code's CLAUDE.md now carries the new bytecode wording, uncommitted, alongside the 500k-cap edit.
     - Learning: a git merge writes a changed file as a NEW inode, so a `mutant.sh` already running keeps reading the
       old script. The "no run in progress" rule is belt and braces.
   - [ ] Code2's utils checkout (`multi-tenancy`) gets the same commit only when its session has no mutant running,
     and with the owner's go-ahead.

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

### FI-4: The lang_agent deadline tests' remaining gaps (flake-fix review, 2026-09-28)

None of these can turn a run red, and none changes production behaviour. Evidence and mutants are in
`.superpowers/sdd/lang-agent-deadline-flake/review.md`.

- **A late deadline passes (M1).** The close-down bound went from about 0.4 s to `window + 5 s`, so a deadline watcher
  up to about 5 s late passes; a 2 s-late mutant survived the file and the lane. Any wall-clock bound here depends on
  host speed, and the earlier held-clock test has the same bound. *Fix:* reword the `_CLOSE_WAIT` comment to say it
  bounds only a control that never fires.
- **The held-reads guard counts modules, not call sites (M2).** It proves each patched module read the held clock at
  least once. Leaving one `deadline_expired` read on the wall clock survives a plain run and only brings the flake
  back. *Fix:* count held reads per call site (keyed by the caller's code object) and assert the expected sites.
- **The admission case can pass before reaching admission (M3), and its `cancellation` param never does (follow-up
  2).** The clock releases at the authorization recheck, about 10 loop callbacks before the admission wait. On a host
  slowed by 10 ms or more per step, the graph call is closed by the check before admission instead, so a deaf
  admission wait survives. At this box's real load it does reach admission. The `cancellation` param reaches it at no
  stretch at all, so it proves only "closed before admission". Both are pre-existing; the fix narrowed M3. *Fix:*
  release the clock only once the graph call is waiting in admission, and assert that it was; set the cancellation only
  after that signal. The signal reads two private dispatcher attributes, which is the coupling paid for determinism.
- **Nothing proves a deadline does not fire early (M4).** A watcher that fires immediately survives the whole
  lang_agent lane. *Fix:* one backend-lifecycle case in which a turn with a generous deadline completes normally.
- **The SAD activation deadline test can pass without proving anything (follow-up 1).**
  `test_lang_sad_activation.py::test_a_hung_activation_query_cannot_outrun_the_turn_deadline` has no `hung.entered`
  assertion, and its 1 s deadline is armed before setup. *Fix:* add the assertion together with the held clock
  (`on_enter=clock.blocked`); the assertion alone would bring back this same flake as a rare red.
- **Two held-clock helpers (follow-up 3).** *Fix:* move `_ClockHeldUntilBlocked` into `_fixtures.py` and switch
  `_ClockHeldUntilInFlight` to it, keeping the resume-from-held behaviour. A pure refactor.
- **Bundling.** Follow-ups 1 and 3 and the M1 comment go in one commit; M3 and follow-up 2 share one remedy.

### FI-8: A sibling declaration crashes copilot-mro's `-n` lanes (found 2026-09-30)

- **What happens.** With `SIBLING_CHECKOUTS` set, `tests/_root.py` announces the declaration as a
  `SiblingDeclarationWarning`. `scripts/_workspace.py` loads `tests/_root.py` by path under the module name
  `_scripts_workspace_root_impl`, so the warning's class lives in a module the xdist controller cannot import. The
  controller fails to unserialize the worker's warning, every node goes down, and the lane ends `INTERNALERROR`
  (exit 3) in minutes. The `-W ignore::UserWarning:_scripts_workspace_root_impl` filter does not catch it: it matches
  the issuing location, and the warning is raised with `stacklevel=2`.
- **Why deferred.** A declaration is needed only while a stale sibling worktree would be picked by name; removing the
  stale worktree, or running that lane serially, avoids it. Recorded as a trap in the controller's memory.
- **The complete solution.** Make the class importable wherever a warning can be unserialized: `scripts/_workspace.py`
  registers the loaded module in `sys.modules` under the tests' own module name, or the warning class moves to a
  module both sides import by name. Add a test that runs a tiny `-n 2` session with a declaration set and expects a
  clean exit.
