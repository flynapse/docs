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
   - [x] **Production follow-up (owner, 2026-09-30: "go ahead"):** remember each tool schema that passed the metaschema
     check, per process. Passes only, keyed on the validator class plus a sha256 of the canonical JSON, bounded at
     1,024; non-JSON content is never keyed; the test fixture is gone. Ledger `.superpowers/sdd/schema-check-memo/`.
     The table-registry cache was judged not worth its risk (about 40 ms per turn).
     - **DONE 2026-09-30, merged and pushed with copilot-mro `211298ad`.** One rich MRO turn's assembly CPU went
       from 2.1–2.4 s to 0.19–0.24 s under load (about 10x less); real metaschema checks per turn 153 → 0; the
       matrix test stays at about 20 s. Review (Opus): Spec and Quality PASS, two Minors fixed before the merge
       (a real draft-07 `$schema` test, the no-lock comment). 11 of 12 mutants killed at build, the survivor killed
       by the fix. Whole-tree non-db at the merge: 15,155 passed, 0 failed.
     - Implementation note: the cached value is a small pass record, not a raising helper: a helper keyed on the
       digest alone cannot see the schema it has to check.
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
- **BUILT 2026-09-30** (owner's go the same day). Branch `scan-index` in `copilot-mro-scanidx`, from `a90db4cd`, tip
  `6b0e6771` (17 commits, test-only, not merged). Brief, census and report: `.superpowers/sdd/test-lane-speed/`
  (`fi1-brief.md`, `fi1-report.md`); scratch evidence `~/.claude/scratch/copilot-mro/scan-index/`.
  - **Census.** 73 test files walk a tree; 52 read or parse a source tree (the in-scope set), 21 do not (a prompt
    looked up by name, the test's own tmp dir, a few YAML files, a git diff). `test_test_layout_rules` walks but reads
    nothing and stays as it was.
  - **Built.** `tests/_source_index.py`: `SOURCES`, one per process. Each file is read once and parsed once, keyed by
    resolved path and checked against mtime and size on every lookup. A file that does not parse raises every time.
    A module's `ast.walk` is taken once and replayed. `python_files` keeps a guard's rglob file set; `listed_files`
    is the git listing. A sweep-sized parse (>= 1 MB of new source) first collects the waiting garbage, then parses
    and walks with the collector paused, then calls `gc.freeze()`.
  - **Guards.** 51 of the 52 now read through the index; each gained a planted module caught through its own sweep.
    Three sweeps changed their file set, and only on the primary checkout: the exception-text log sweep, the
    resolver-name pin and the Document Hub removed-constant pin now take what git lists. They had also read the
    primary's ignored `scratchpad/`, `.superpowers/` and `.dev_runs/` scripts, and one read its `.venv`. The
    ambient-env scan now excludes the Weaviate test volume, whose raft `users.json` it read on the primary.
  - **Unchanged by design.** The exception-text register scan cannot take trees: the estate detector parses source
    text itself. It only runs with the collector paused (84 s -> 67 s, the same 33 findings). The depth guard's walker
    check now asks its cheap half first; proven identical over 1,683 modules.
  - **Measured.** Three before/after pairs of the whole-tree non-db lane, each back to back:
    - Pair 1, index without the freeze: 39:49 -> 40:14, no gain. Full collections walked the retained trees.
    - Pair 2, freeze after the collect: 42:03 -> 32:15.
    - Pair 3, final code, run in reverse order (after first, load 14 -> 12; before second, load 12 -> 10):
      32:52 -> 25:04. CPU 6,286 -> 5,144 s.
    - What the pairs show (review A, 2026-09-30): the direction and the mechanism, not a point figure. The same base
      code ran 32:52, 39:49 and 42:03 on pytest's clock, a spread as large as the effect. Pair 3 was not
      like-for-like (the slot log shows 3.5 other runs beside the before run against 2.8 beside the after run, and
      twice the major faults before), so its -24% overstates; pair 2 was the fairer pair (-23% clock, -17% CPU, on
      intermediate code). Reviewer's estimate: **-15 to -25%**. Peak single process +0.4 to +0.85 GB against the three
      base runs (1.94 / 1.77 / 2.21 -> 2.62 GB); the lane's total memory was not measured.
    - The 52 guard files' tests (those of 1 s or more), summed: 1,689 -> 716 s. The lane's slowest test is now the
      register scan (183 -> 141 s). The depth guard went 115 -> 40 s and the logger rules 124 -> 9 s.
    - Equality: per guard module, the files read and every test local, before vs after, fixed hash seed. The
      differences left are explained, and on the same tree the old and new sweeps return identical results. After
      the lane, every tree the index still held was unchanged. 15 mutants on the final code, all killed.
  - [x] Review, split by area (A the index, B the guards; both APPROVE WITH FIXES, `fi1-review-{A,B}.md`).
  - [x] **Fix round 1 (2026-09-30)**, tip `48fa74b8` (two commits on `6b0e6771`; `fi1-fix1-report.md`):
    - `listed_files` is never an empty sweep. A checkout that is its own git toplevel is listed by git; a copy
      without `.git` (a `git archive` extract, a copy another repository ignores) is walked, `__pycache__` aside;
      empty raises naming the root. The legacy-metrics and alertmanager sweeps use it instead of their own copies of
      the listing; the Document Hub pin gained a floor (> 800 files, the package reached). All five listing guards
      now pass in an extract; only the register-history tests still need git history.
    - The index holds Python source only and refuses any other path; `read_text` / `read_bytes` read everything else
      directly and keep nothing (the two byte sweeps, the ambient-env scan with the developer's `.env`, the AD query
      contract, the database-names and inspect-user scans). The two byte-sweep files at `-n 0`: peak RSS 1,180 ->
      1,039 MB; index retained 176 -> 32 MB, non-source 144 -> 0 MB.
    - Tests: the stamp's size half is pinned; `gc.freeze()`'s introspection blind spot is written at
      `SETTLE_AFTER_BYTES` and tripwired (no suite module may call `gc.get_objects` / `gc.get_referrers`); the
      one-instance test now checks every loaded module's index. Every second sweep that lacked a plant has one, each
      failing when the index serves empty bytes; the judge-residency plant goes through the sweep's own enumeration;
      the db-lane plant has a marked sibling.
    - 12 mutants KILLED (incl. review A's MA1, the empty listing, a non-`.py` file through the index, a b5-style root
      drop, the path-only key and the swallowed parse error), two of them re-run aimed at the one test meant to kill
      them. Hand-back whole-tree non-db lane at `48fa74b8`: 15,203 passed, 61 skipped, 0 failed (+15 new tests); no
      timing claimed.
  - [ ] Merge by the controller. The full suite at the merge commit is the gate.
  - **Future Improvements (FI-1).**
    - *The register scan is the lane's floor at 141 s.* The estate detector (flynapse-otel) takes source text. The
      complete fix is an `analyse` that accepts parsed trees, plus the detector's own walk memo. It is a flynapse-otel
      change, outside this tree.
    - *The depth guard is still 40 s.* Its `_walker_functions` and `_tainted_names` re-walk function subtrees
      (O(n·depth)). The complete fix is a single bottom-up pass, proven identical like the walker reorder.
    - *An extract is walked, a copy is taken as given.* Since fix round 1 a copy without `.git` is walked, so it
      passes in a `git archive` extract. The trade-off: a `cp -r` / rsync copy of the PRIMARY (no `.git`, but its
      `.venv`, `scratchpad/` and runtime dumps) would be read whole, and so would a cache a run in the copy writes
      (`.pytest_cache` unless `-p no:cacheprovider`, as `parallel-commits.sh` passes). The complete fix, if such copies
      ever matter: honour the copy's own `.gitignore` for untracked files while keeping every file an extract was given
      (git cannot do both without a repository). The inspect-user guard keeps its own tracked-only listing of
      `deployment/` and still needs a checkout.
    - *The freeze is process-wide.* An object alive at the moment of the freeze and later caught in a reference cycle
      is kept until the worker exits, and its finalizer never runs. `gc.get_objects` / `gc.get_referrers` are blind to
      it; a tripwire now fails if a suite module calls either. A selective freeze does not exist in CPython.
    - *A decoded copy per `errors` mode* (review A M-2). `text()` keeps one string per mode even when the strict
      decode succeeds, so a clean file read as `strict`, `replace` and `ignore` holds three equal strings. The fix:
      for a non-strict mode, try the strict text first and store it under the requested key (the result is identical
      by definition), as `_tree` already does.
    - *Two production invalid-escape warnings no longer surface in the lane* (review A M-3; 128 -> 35 warnings).
      The index parses with `DeprecationWarning` / `SyntaxWarning` silenced, and with warm bytecode the guards' parses
      were the only place the lane showed `agent_evaluation/contracts.py:199` (a backslash before a backtick) and
      `parsers/wdm_pipeline/wdm_parser/validate.py:1` (`'\d'`). The fix is in production code, separately: correct those
      two escapes (raw strings); optionally a lint that compiles production modules with warnings as errors.
    - *Multi-root plants sit in one root* (review B M-6, pre-existing). Dropping a root that holds no finding from a
      multi-root sweep (the seat guard's `demo`, and the loguru, weaviate, secret-in-SQL, content-spill, tool-results
      and detail-keywords sweeps) survives each guard's own file: `python_files` refuses a missing root, but a root
      dropped from the tuple goes unnoticed. The fix: parametrize each plant over its roots, one planted module per
      root, each expected in the report (the DDL shadow plant now sits in the second root, and the b5-style drop of it
      was killed).
    - *The legacy-metrics guard's own text cache* (review B, pre-existing). `_production_files`' `lru_cache` keeps the
      `replace`-decoded text of every production file, the 70 MB archive and the CSV dumps included, about 355 MB on
      the worker that runs it (the two-file peak is still ~1 GB after fix round 1). The fix: skip binary files (a NUL
      byte in the first block) and cap the decoded size, or keep only the per-name hit sets rather than the texts.
    - *A quiet re-measure* (review A's recipe). No other slot holder, 1-minute load under 2 and swap near idle;
      each tree warmed once; ABBA ABBA with at least four runs per arm, `PYTHONHASHSEED=0`, the same test set; per run
      the pytest clock, user+sys CPU, and a 5 s sampler of PSI and every xdist worker's RSS (which also gives the lane
      total). Cheaper and less noisy: the same protocol on the 52 census files alone at `-n 0`. Until then, admit
      whole-tree copilot-mro lanes with `pytest-slot.sh -m 8`.
  - **Learnings.**
    - Sharing the parse alone did not speed the lane. The trees a worker keeps made every full collection walk
      millions of nodes: pytest runs five of them at session cleanup, and one test's own `gc.collect()` took 96 s on
      the swapping box. Measure the lane, not only the guards.
    - `git stash` is repository-wide across worktrees. A `stash pop` on a clean tree popped another session's stash
      (`fe0155a1`, "pre-MT-merge ... mro_documents_aixl"). It was restored with `git stash store` and the tree change
      reversed. Never use stash in a shared repository; use a commit or a copy.
    - (Fix round 1) A floor added after a sweep's finding assertion can make its plant pass for the wrong reason:
      pytest's rewritten `assert len(scanned) > 800` prints `scanned`, which names the planted file, so a plant
      matching only the file name passed with the index serving empty bytes. Match the finding's own message, and
      prove each plant with the empty-bytes sabotage run. pytest also truncates a long list in its own summary line;
      a plant that matches more than the first finding needs the guard's assertion to carry its list as the message.

### FI-2: Shrink the lang_agent activation matrix (owner go 2026-10-01; CLOSED 2026-10-01, owner: dropped, premise stale)

- **Closed, not merged (owner, 2026-10-01).**
  - The 201 s below predates round 1: round 1 and the production schema-check memo had already cut the test to 14–22 s
    alone.
  - The build (a proven 96-cell cover of the 150-cell matrix, branch `fi2` `fe7a2d20`, report
    `.superpowers/sdd/test-lane-speed/fi2-report.md`) saved only 3–5 s. It also gave up three-way coverage: one designed
    mutant survived.
  - The lane's floor is a 141 s test elsewhere, so the lane would not have got faster. The full 150-cell matrix stays,
    and the branch is deleted.
  - The fix that would keep every cell and be cheaper is in production (cache the table registry and the skill
    packages once per process). It reopens round 1's ruling against that cache, and stays the owner's call.

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

### FI-4: The lang_agent deadline tests' remaining gaps (flake-fix review, 2026-09-28; owner go 2026-10-01; built and reviewed 2026-10-01)

- **Built and reviewed (2026-10-01).** Branch `fi4` `ba5074f2`: test-only, five files under `tests/unit/lang_agent/`,
  with every item below. The task review approved it with 0 Critical and 0 Important findings, and three Minors:
  - M4 proves only "does not fire at once";
  - in two rows the clock's release never takes effect, so they end through a path production cannot take;
  - the SAD row's time bound includes setup.

  A small fix round for the three is running. FI-4 then merges with user erasure Task 15's copilot-mro merge and
  shares its gate.

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

### FI-9: Two live copies of `doc_catalog` in one xdist worker bypass `tests/unit/ingest`'s patches (found 2026-10-01)

- **What happens.** A non-db `-n 4` run on the user-erasure F1 fix tip had 3 failures in `tests/unit/ingest`: one
  worker held two live copies of `copilot_mro.app.services.doc_catalog`, so the tests' patches landed on the copy the
  code under test did not use. They pass alone and in their folder serially; a later run was green.
- **Likely cause.** `tests/registries/tenancy/test_document_catalog_indexes.py:70` registers a by-path copy of the
  module in `sys.modules` and never restores the original.
- **Complete fix.** That test restores `sys.modules` (a fixture that saves and puts back the entry), or loads its copy
  under a private name; a guard test fails on any test that leaves a replaced `sys.modules` entry behind.

### FI-8: A sibling declaration crashes copilot-mro's `-n` lanes (found 2026-09-30; owner go 2026-10-01; built and reviewed; merged 2026-10-01 with the user-erasure batch, core `c6f6e2e` + copilot-mro `5c2bf7f4`, gate green but for the known census reds, pushed)

- **Built (2026-10-01):** copilot-mro `fi8` `58f05103..2a80403d` and core `fi8` `7c8c9a9..05e90a4` (core's
  `scripts/_core_workspace.py` is the same loader and crashed copilot-mro's lanes too). Both helpers load
  `tests/_root.py` as `_root` (reuse a `_root` loaded from the same file, register a fresh one, leave a foreign one in
  place). `tests/_root.py` is untouched. Red-before: a `-n 2` probe exited 3; after, the once-crashing `-n 4` lane with
  `SIBLING_CHECKOUTS` set and no `-W` filter passes (15,416). Task review: approve, 0/0/3 Minor. They merge together:
  the copilot-mro half with an unfixed core still exits 3. It also closes the user-erasure plan's T3-C4.
- **After the merge:** the `-W ignore::UserWarning:_scripts_workspace_root_impl` filter matches nothing and can leave
  the lane recipes (outside a `tests/` root it no longer rescues a run; `-W ignore::UserWarning:_root` does).
- **FIs from the review:** utils carries a latent instance (`ForeignPrivatePatchWarning`,
  `tests/unit/infra/test_no_private_library_globals_assigned.py:118`; cannot fire today). api's `ad_materialize`
  worker now registers copilot-mro's `tests/_root.py` as `sys.modules["_root"]` in production (nothing imports it):
  one docstring sentence, or drop the registration there.

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

## Lessons

- **Re-measure an FI's premise on the current mainline before building it (FI-2, 2026-10-01).** FI-2 was briefed on a
  201 s measurement taken before round 1. At the build's base the test already took 14–22 s, so the build bought 3–5 s
  at the cost of coverage, and the owner dropped it. Rule: an FI justified by a measured cost gets that cost measured
  again on the current mainline (one run, through `pytest-slot.sh`) before the brief goes out. If it no longer clears
  the bar, take it back to the owner instead of building.
