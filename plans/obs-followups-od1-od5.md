# Observability follow-ups — OD-1 (bot stderr hides pilot words) + OD-5 (copilot-mro body echoes → refusals)

Owner rulings 2026-09-25 (from `observability-residual-builds.md` §Owner decisions): **OD-1 → HIDE**, **OD-5 → FIX**.
Research: `~/.claude/scratch/obs-residuals/research/R3-od1-tg-stderr.md` (OD-1) and
`R4-od5-mro-body-echoes.md` (+ `R4-probe/`) (OD-5). Ledger:
`/home/aditya/Code/.superpowers/sdd/obs-followups-od1-od5/progress.md`.
Model policy: implementers and reviewers Opus (owner: "SDD driven, Opus agents"); final review Opus.
Push: Claude may push this work (owner, 2026-09-25); fast-forward or merge only — never rebase/squash (ratchet).

## Global constraints

- One implementer per worktree; worktrees at sibling depth (`/home/aditya/Code/<repo>-<lane>`), plain `git worktree`,
  scratch under `~/.claude/scratch/obs-followups/<lane>/`.
- Every test run through `pytest-slot.sh`; mutation proofs through `mutant.sh`; red-before for every behaviour change.
- Commits by named pathspec; never `git add -A`, amend, rebase or squash. The exception-text register must EQUAL the
  scan after every task; the register only shrinks.
- Env: `DEBUG=false POSTGRES_DB=copilot_mro_test PYTHONPATH=<worktree>`; copilot-mro uses the api venv; telegram-bot its
  own venv, no xdist. Known env reds: `test_cross_repo_reads_name_their_checkout.py` variants (they move as worktrees
  come and go), Postgres-dependent tests, load-sensitive timing tests.

## Owner decisions (ALL RULED by the owner 2026-09-25 as recommended: D1 approve · D2 include · D3 accept · D4 accept)

- **D1 — one ruled policy widening.** copilot-mro's register test refuses ANY new refusal type against the adoption
  baseline. OD-5 needs exactly one (`Refusal`). Proposal: a literal, dated allowance naming that one type inside the
  register test, going inert once pushed. First post-adoption widening in the estate. Recommend: approve.
- **D2 — two detector-blind siblings.** Data Discovery `runner.py:61` and `level1.py:1375` persist exception text into
  `failure_message`, which the dashboard renders and notifications carry. Recommend: include (one type check each).
- **D3 — status for non-refusal failures.** Data Discovery / Document Hub errors that are not deliberate refusals move
  from 400/403/404 to 500 (dashboard shows "Something went wrong" toast plus the page's fixed sentence). Recommend:
  accept (core precedent; a non-refusal is the server's failure).
- **D4 — `/brief` fallback.** Pilots see "The METAR source failed." instead of scrubbed upstream text.
  Recommend: accept.

## Controller rulings (pre-flight)

- **R-OD1-JOB:** a PTB/APScheduler `Job` argument stands in as its name on both sinks (job names are the bot's own,
  not pilot content; without it stderr loses them). Cost if wrong: one small revert.
- **R-OD1-MOVE:** move the OTLP stand-in rule into `telegram_bot/failure.py` (not duplicate); OTLP output unchanged.
- **R-T2-DHERR:** Task 2 rebases `DocumentHubUploadPolicyError` (`document_hub/errors.py`) onto `Refusal` (409, dict
  detail) so the shared helper's dict path is exercised by a real class; Task 4 does not touch `errors.py`.
  `ReadOnlyValidationError` (Data Discovery connectors) is rebased in Task 3.
- **R-OD5-MIXINS:** one `Refusal` base plus builtin-preserving subclasses (value / lookup / permission), status set at
  the raise site; one shared relay helper; unsure-bucket sites default to the generic fallback (fail-safe: a missed
  conversion degrades a message, never leaks).

## Tasks

### Task 1: OD-1 — stderr renders third-party records like the OTLP route (telegram-bot, lane TG)
- [x] Move the stand-in rule (`telemetry.py:520-621`) into `failure.py` behind one public helper; `_scrubbed_copy`
      uses it (OTLP unchanged); `FailureFormatter` formats a copy with it.
- [x] `Job` stands in as its name on both sinks (R-OD1-JOB).
- [x] Tests per R3 §4: real-PTB stderr assertions for records A and B (sentinel text + `first_name` absent; update id,
      template, frames present); real `configure_logging` fresh-interpreter case; PP-TG-14 expectation updates;
      bot-line byte-identity parametrised; moved unit tests re-pointed; mutation proofs (a) and (b) KILLED.
- [x] One-off census over the full unit lane: every bot record's stood-in body equals its plain message.
- [x] Register guard run: 0 new findings. Prose that becomes false edited (R3 §5).

### Task 2: OD-5 foundation (copilot-mro, lane M0) — needs D1
- [x] New framework-free `app/utils/refusal.py` (base + three builtin-preserving subclasses; Document Hub upload
      policy error rebased as a 409 refusal with its dict detail); new `app/api/refusals.py` shared relay helper.
- [x] Policy names the one refusal type; the ruled widening allowance (D1) in the register test; plant test copies
      the refusal module into its tmp tree; census-pin skeleton with one site file per family.
- [x] Unit tests of the helper and subclasses (base preservation, status override, dict detail).

### Task 3: OD-5 Data Discovery (lane M1, after Task 2) — needs D2, D3
- [ ] Relay funnel via the shared helper; route-reachable fixed / caller-safe raises converted with their statuses;
      internal and library text falls to the fixed fallback; D2 siblings if ruled in.
- [ ] Red-before sentinel test per error kind; census file; delete the 21 register entries.

### Task 4: OD-5 Document Hub (lane M2, after Task 2) — needs D3
- [x] Relay funnel via the helper; substring status ladder removed (status at the raise); route enum parse refused
      with a fixed sentence; conversions; sentinel tests; census file; delete the 12 entries.

### Task 5: OD-5 chat uploads/read + `/brief` (lane M3, after Task 2) — needs D4
- [ ] R1–R7 relays via the helper (status at the raise; "disabled" 403 kept); R2/R3 fallbacks; `/brief` fallback;
      conversions; sentinel tests (replacing `test_brief_endpoint_logic.py:585-596`); census file; delete 7 entries.

## Review & merge protocol

Per task: implementer → task reviewer (re-runs proofs) → fix rounds → merge `--no-ff` into the mainline. Tasks 3–5
share only the register JSON (disjoint entry blocks) → mechanical union at merge. Final whole-batch review (Opus),
one fix wave, one scoped re-review, then push.

## Future Improvements

- **FI-TG-6 — `BaseRequest` raw-body line** (`telegram/request/_baserequest.py:399`): a non-JSON response body prints
  verbatim on BOTH sinks (a direct string argument). Unlikely to carry pilot words (proxy/HTML error pages); complete
  fix: stand in direct string arguments of that one logger/template, or cap and hash the body.
- **FI-OTEL-13 — estate-wide ruled widenings:** a `ruled=` parameter on flynapse-otel's policy ratchet instead of a
  per-repo literal allowance (D1).

- **FI-TG-7 — OTLP ships exception text passed BESIDE the exception** (pre-existing at `a1d1f2a`): a record passing an
  exception AND its text (`"%s: %s", exc, str(exc)`, or a template quoting it) exports the text in the OTLP body;
  stderr withholds it since Task 1. No PTB/APScheduler/httpx call site of this shape is known. Complete fix: in
  `_scrubbed_copy`, run the exception-quote withholding against the original record before the credential scrub.
- **FI-TG-8 — standing byte-identity census** (Task 1 review M4): the bot-line identity guard is 12 synthetic kinds; the
  census over real call sites ran once. A future bot line passing `%s` of a list would silently print `['<str>', …]`
  (fail-closed). Complete fix: keep the census plugin as a standing test over every `telegram_bot.*` record.

## Lessons

_(plan-scoped; append after any owner correction)_

## Implementation notes

_(per task, filled as work lands)_

**Status at compaction checkpoint 1 (2026-09-25):** Task 1 merged (telegram-bot `bff16ea`, unpushed until the batch
final review); Task 2 in flight on `copilot-mro-od5` (`fu-od5` from `e0cdea42`); Tasks 3–5 follow in parallel after
Task 2 merges. Execution: SDD, Opus implementers + reviewers. Ledger holds agent ids and next steps.

#### Notes: Task 1 — OD-1: DONE + MERGED (telegram-bot main `bff16ea`; review clean, Spec ✅ / Quality approved)
- `effb186` stand-in rule moved into `failure.py` (`stood_in_body`); OTLP `_scrubbed_copy` calls it (byte-identical
  output except `Job` → its name); `FailureFormatter` formats a copy · `fa6fcf6` docstring · `93cb62c` mypy override
  for `apscheduler.*` (ruled in) · `a28133f` malformed library call prints template + stood-in args (closes the
  `handleError` raw-args path) · **pre-review fix `9d40f7d`:** the formatter's copy keeps the original msg/args so
  exception-text withholding stays at `a1d1f2a` parity (an exception passed beside its text had started printing).
- Proofs: unit 2473 passed; census 0 mismatches (619 records, 154/206 sites + 52 read by hand); mutants (a) stand-in
  dropped, (b) Update passed through, (c) Job name lost, C1 revert, (v) helper mutates its record — all KILLED
  (implementer and reviewer, independently). Reviewer planted 33 records on both routes: every pilot-content shape
  hidden on stderr; OTLP unchanged except the Job case.
- Deferred minors (final review triages): docstring reflow `failure.py:251`; `telemetry.py:46-49` parity sentence;
  FI-TG-8.

**Status at compaction checkpoint 2 (2026-09-27):** Tasks 1, 2, 4 complete and merged (telegram-bot `bff16ea`;
copilot-mro `langgraph-merge` `eca6bd9f` T2, `683808f3` T4); Tasks 3 and 5 implemented and in task review
(`fu-od5-dd` @ `5e06f5e2`, `fu-od5-chat` @ `2fd95aa3`). Then: merge T3/T5 (union the register JSON + scope-guard
set), final whole-batch review, one fix wave, push telegram-bot + copilot-mro. Nothing pushed yet.

#### Notes: Task 2 — OD-5 foundation: DONE + MERGED (`langgraph-merge` `eca6bd9f`; review APPROVED after one fix round)
- `7c4bc2a0` foundation (`app/utils/refusal.py`, `app/api/refusals.py` `refusal_or`, DH upload-policy error →
  `(Refusal, RuntimeError)` 409 dict, policy names `Refusal`, `RULED_POLICY_WIDENINGS`, plant test copies) ·
  `e2565747` census pin + family site files · `e2668cac` scope-guard paths · `7c8bfe55` non-refusal logged at `error`
  when the fallback status ≥ 500, else `warning` (ruling T2-C1) · `e897c067` review fixes: every refusal class carries a
  sample and a chained-cause sentinel proves no class renders its cause/context (I1); two-family pin test (M1);
  allowance comment corrected (M2); failure log attributed to the calling route via `opt(depth=1)` (M3).
- Learning: a census that pins classes by NAME cannot see what a class RENDERS — the sentinel over every discovered
  subclass (with a mandatory sample) is what closes it. Rule carried to T3–T5: each family samples only its own classes.

#### Notes: Task 4 — Document Hub: DONE + MERGED (`langgraph-merge` `683808f3`; review APPROVED after one fix round)
- `60e5a130` raises → refusals (status at the raise) · `2aab5d0b` relay via `refusal_or`, fixed 500 "Document Hub request
  failed", ladder removed, `group_by` fixed 400 · `8b4da575` 12 register entries repaired + scope guard · `a2852bb1`
  review fix: the register rebuilt byte-minimal against `eca6bd9f` (the first rewrite re-encoded 28 unrelated `—`
  lines — the file is mixed-serialised; edit textually, never re-dump) + the sentinel also reads stdlib logging.
- Red-before 89 failed / 90 passed at `eca6bd9f` (the greens are cases the old relay already answered safely).
