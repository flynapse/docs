# Claims packet — core PRE-PUSH full-diff review (queue step 16b, review 8 of 9)

**Verdict: PUSH-CLEAN — P0 0 · P1 0 · P2 0 · P3 1.** (The push gate is P0/P1 only; the one P3 is
PPC-F1, a C15 gate blindness to an out-of-contract findings shape, pooled to the estate micro-batch.)

Independent pre-push reviewer (Fable), 2026-09-23. READ-ONLY on the real tree throughout.

## Anchor and range

- Tree: `/home/aditya/Code/core-obsm`, branch `obs-merge`, HEAD **`6899974`**, clean (verified at start:
  `git status --porcelain` empty).
- **Pushed mainline measured by `ls-remote`, not tracking refs**: `origin` = `github.com/flynapse/core.git`;
  `refs/heads/master` = **`e10a9ce4680e1c6d6eda30324c65b97a7cf75688`** (2026-09-14, "merge: TanStack conversion,
  core side — Fable gate RC"). Per PUSH TRUTH (CHECKPOINT 43) core's origin has NOT moved, and the measurement
  agrees. `origin/obs-telemetry-merge` = `8b7dfad` is the colleague's own source branch, pushed.
- `git merge-base e10a9ce 6899974` = **`e10a9ce`** itself — the pushed master is an ancestor of the pinned HEAD.
- **Range reviewed: `e10a9ce..6899974` — 168 commits (159 first-parent)**.
- **Excluded as already-gated: nothing INSIDE the range.** The observability-rebuild batch-2 gate
  (phases ≤P10, R12–R21, and the visible "Fable gate R3/R11/RC" merges) sits entirely at or below
  `e10a9ce` on the pushed mainline, so it is excluded by construction of the range. Every commit
  in `e10a9ce..6899974` is colleague-era or this project's core work: the colleague's 5 branch commits
  (`03e15db`, `c718687`, `ad263aa`, `1013106`, `8b7dfad`), the B1 merge `5d40d70`, the G-lane /
  M-item / review-round chain (rounds R0a..R6, r7, r8), the r9 fix batch `16cd1ae..19403fa`,
  the r10-narrow subjects, `df6a352`, and the anon/C15 extension `170e2ab` + `6899974`.
- Claims indexes reconciled against (never as evidence): `claims-C1-utils-B1-core.md` (core `8b7dfad..d7f7b54`),
  `claims-core-rounds.md` (B1→`dc41caa`), `claims-core-r7.md`, `claims-core-r8.md`, `claims-core-r9.md`
  (15 answered rows + flip record), `claims-core-r10.md` (narrow), SDD ledger CHECKPOINT 43 + Add. 250–274.

## Pins and lane recipe

- Scratch: `~/.claude/scratch/obs-merge/prepush-core/` — `tree/` = `git archive 6899974` copy
  (391 files, count-verified vs `ls-tree -r`), `logs/`. Real tree never written; all proofs run from the copy.
- DB RUNS NOT SANCTIONED for this lane (one estate-wide db user; held elsewhere). Any db-only proof
  is marked "index-verified only — db re-execution requested".
- Every test run through `/home/aditya/Code/pytest-slot.sh`, `-n 2` max, `DEBUG=false`, pytest invoked
  from the scratch repo root with `PYTHONPATH` pinned; rootdir/module-path proof lines checked per run.

## Claims table

(rows accumulate as the review proceeds; final totals at the end)

| id | file:line | claim | evidence executed | verdict |
|---|---|---|---|---|
| PPC-01 | whole tree | HEAD `6899974` on `obs-merge`, clean; pushed master `e10a9ce` measured via `ls-remote`; merge-base = pushed master; range = 168 commits, all colleague-era/this-project | `git status/rev-parse/ls-remote/merge-base/rev-list` (see Anchor) | VERIFIED |
| PPC-02 | `scripts/rbac/anonymise_already_deleted_chats.sql` (`170e2ab`, on `600730e`) | C15 extension matches the owner's line (Add. 271/273/274): findings' copied `evidence.texts` FIRST (read-back handed to the gate via a transaction-local `set_config` — an aggregate SELECT, so it records even a 0), signals `user_id`+`excerpt`/`reason`/`comment`, shares `email`/`message`/`session_id`+`user_id`, agent_state payload→`{}`+label+pointer+version bump, memory events actor+comment; compaction digests DELETED; `_user_corrections`, `example_queries`, `evidence_excerpts`, finding `body`, themes/titles KEPT (non-compaction `memory_items` untouched by construction); `llm_turn_content` 30-day purge documented at `:61-62`; spilled S3 keys + Weaviate doc ids REPORTED (`spilled_objects_to_reap`, `compaction_index_docs_to_reap`) | full-file read at HEAD; every UPDATE keyed on the not-yet-anonymised shape (idempotence re-derived clause by clause, NULL payload/`detail` preserved); gate re-counts every half with matching predicates; the findings' SET is a deliberate superset of its WHERE (Add. 274 residual 1, over-scrub toward privacy) — gate/update pair coherent | VERIFIED (by reading; db execution not sanctioned here) |
| PPC-03 | same, `600730e` properties | STOP cases fail closed: BYPASSRLS refusal RAISES before any write; non-object signal `detail` is skipped by the UPDATE and COUNTED by the gate; non-object share/feedback payloads reach the gate via `->> 'user_id'` → NULL → counted; a scalar payload errors at `- 'comment'` (abort). `search_path = pg_catalog, pg_temp` pinned, every relation `public.`-qualified; `-v ON_ERROR_STOP=1` + aborted-tx `COMMIT`=ROLLBACK story correct; row locks only, no DDL | read; the jsonb operator semantics cross-checked (`- text` on arrays deletes matching string elements — the STOP test's seeded array proves the gate is reached, not an earlier error) | VERIFIED |
| PPC-04 | `tests/db/analytics/test_anonymise_deleted_chats_script_db.py` | The copies' statements only ever execute against `pg_temp.` shadows: `_shadowed()` creates `CREATE TEMP TABLE x (LIKE public.x INCLUDING ALL) ON COMMIT DROP` for all 10 relations, rewrites `public.` → `pg_temp.` and ASSERTS no `public.` remains; the chat-half tests run the body on real tables ONLY as the RLS-confined app role on self-seeded rows in an always-rolled-back transaction (the `600730e` pattern r10 reviewed). The `statements()` splitter honours `'` and `$$` quoting and drops `--` comments. 6 tests: refusal; one-run+idempotence (real); non-object feedback STOP (real); copies line+idempotence (shadows); non-object signal STOP (shadows); finding-text-left STOP (shadows, rewrite SKIPPED — proves the set_config hand-over is load-bearing) | full-file read; owner's-line assertions checked against the ruling row by row (keep body/title/theme/`example_queries`/`_user_corrections`/live rows; scrub s-old/s-nochat-via-block/s-half; delete only the deleted chat's digest) | VERIFIED by reading. The 6 db tests: **index-verified only — db re-execution requested** (Add. 274: core analytics at `170e2ab` = 156 passed incl. these 6) |
| PPC-05 | `6899974` | The plan-row commit records r9-28 RULED+BUILT accurately (scope, exclusions `llm_usage`/`llm_model_calls`/`llm_turn_content`, C15 pointer) | diff read | VERIFIED |
| PPC-06 | r9 fix batch `16cd1ae..19403fa` — sampled non-P2 rows | r9-22 (`42785ed`): `/users/email/<addr>` path segment withheld under any prefix, case-insensitive, filter seat unchanged; r9-27 (`2c7395e`): `_db_ok` re-raises unless `nothing_answered()` (positive libpq vocabulary, one canonical copy `tests/_db_reachability.py`, db conftest reads it); r9-21 (`b540596`): autouse EFFECT check on `flynapse_otel.bootstrap._state` + alias/lifespan-aware AST pin with its limit stated; r9-19 (`8d0df97`+`1e044b1`): percent-encoded/protocol-relative URLs withheld in pointer fields via the widened in-text rule, bucket-host-without-path recognised, scheme-less-after-text redacted in place, double-encoded limit restated; follow-up honestly reverts the redundant element-rule change (its mutants SURVIVED — covered by the in-text rule) | all four diffs read in full; named tests RE-RUN from the scratch copy (below) | VERIFIED |
| PPC-07 | sampled lane | `tests/unit/logging/test_access_line_withholds_personal_query.py` + `tests/unit/harness/test_no_live_service_pins.py` + `tests/api/harness/test_the_api_lanes_database_gates.py` + `tests/api/documents/test_document_answer_names_no_storage_location.py`: **90 passed, exit 0, 6.2 s** via `pytest-slot.sh`, serial, `DEBUG=false`, from the scratch copy; proof lines: rootdir + `core.__file__` inside the copy, `utils` = `/home/aditya/Code/utils-obsm`, `flynapse_otel` = `/home/aditya/Code/flynapse-otel` (`logs/sample-r9.log`). Disclosure: the db-gates pin test's "refused database" case attempts a connection to a NONEXISTENT database name on the local server (fails at FATAL, no session on the shared test DB) — collection-probe by design, not a db run | run log | VERIFIED |

| PPC-08 | full production diff, `e10a9ce..6899974` — `core/`, `scripts/`, `setup/` (88 files, +6168/−998) | Read END TO END (11,088 diff lines). Leak screen: every added exception-rendering site resolves to `failure_fields`/class-name-only/fixed sentences; `refused()` echoes `Refusal` ONLY (`ValidationError` excluded); `internal_error` reads `sys.exception()` and its `context` strings carry ids only; spans (`sweep_span`/`queue_span`/`cognito_spans`) pass literal `record_exception=False` + `set_status_on_exception=False`, bare `Status(ERROR)`, `type(error).__name__` only; storage locations typed out of reprs (`CatalogItem`, `repr=False` keys), `/pdf` headers lose `X-S3-Key`/`X-Bucket-Name`, `Cache-Control: private`; access line withholds `?search=` + `/users/email/<addr>`; invite token → fragment + POST body, deprecated GET logs no token; `RequestModel` NUL refusal at the boundary; M-PII-IDS holds on every touched log line (ids/counts/booleans, never addresses, search terms, contacts, tags/mentions) | sliced full read + targeted greps over added lines; correctness spot-derivations (ON CONFLICT DO NOTHING intra-batch duplicates safe; the accepted-rows Counter mapping; `iter_all_tenants` cursor/count algebra; the MintReceipt seal/registry redemption under its lock; keyset one-statement count+page; `_execute_many_on` savepoint rowcount-before-RELEASE) | VERIFIED — no P0/P1 anywhere in the production diff |
| PPC-09 | tests, range-wide (113 files, +26,112/−686) | No test file deleted; NO new `skip`/`xfail`/`skipif` markers added; `LAYOUT_EXEMPTIONS` untouched; the largest deleted block (`test_no_depth_coupled_paths.py`, 60 lines) is the reviewed rewrite that WIDENED the guard from `tests/` to the whole repo (`141e42e`) | diff-filter + grep screens; deleted-line audit of the top file | VERIFIED |
| PPC-10 | colleague era: `03e15db c718687 ad263aa 1013106 8b7dfad` + B1 merge `5d40d70` + triage `d7f7b54` | The colleague branch (+973/−1584, 30 files vs `e10a9ce`) and the merge record reconcile: idempotency PK really `(tenant_id, event_id)`; M-CAPTURE flipped opt-IN→opt-OUT at the merge with the pinning test; the 499/`duplicates` graft verified in the HEAD handler I read in PPC-08. First reviewed by `claims-C1-utils-B1-core.md` (core `8b7dfad..d7f7b54`); re-covered here at colleague-scope | merge stat + branch diff read; HEAD shapes all read in PPC-08 | VERIFIED |
| PPC-11 | `df6a352` | r10-P3-1 landed as ruled: the below-seat mint-registration limit DECLARED in `adopting_production_mints`' docstring, beside the two watched seats; no code change | diff read | VERIFIED |
| PPC-12 | round chain | Continuous, no open P0/P1 anywhere in it: B1 (`claims-C1-utils-B1-core.md`) → rounds R0a..R6 (`claims-core-rounds.md`, B1→`dc41caa`) → r7 → r8 (FIX-FIRST 0/1/5/10; P1-1 fixed `aba5b18`+`fe41002`, its seat re-examined by r9 — which found the PATH residual, fixed `42785ed` and re-run green here, PPC-06/07) → r9 (FIX-FIRST 0/0/4/11; all 15 answered rows FLIPPED, flip record verified present) → r10 NARROW (MERGE-CLEAN 0/0/0/1 at `19403fa`, four P2 seats re-proven, C15 never executed) → `df6a352` + anon extension (this review, first-review rigour). Add. 274's residuals 1–2 are recorded design limits (over-scrub toward privacy; un-gated writers outside the two ruled windows — declared in the C15 header); residual 3 (`memory_items.user_id` kept on retained notes) is assigned to the copilot-mro prepush reviewer, not this lane | index reads reconciled against the tree, never as evidence | VERIFIED |
| PPC-13 | full unit lane at HEAD, scratch copy, `-n 2` | **1997 passed, 11 failed, 2 errors, 60 skipped, 78.8 s, exit 1** — every failure/error is a PROVEN copy-location artefact: all 13 sit in cross-repo/checkout-resolution guards (`chat_turn_facts_drift_pin` ×4, run-error/run-status vocabulary pins ×2, `cross_repo_reads_name_their_checkout` ×4, `root_anchoring` ×1, `document_cache_scope_key` collection ×2) that anchor siblings the isolated archive does not have — and each fails LOUDLY by design instead of skipping. The skips are the same class (empty checkout parameter sets, absent siblings). Reconciliation: the same families run READ-ONLY in the REAL tree = **339 passed (drift pins + census) and 83 passed (the three remaining files), exit 0, `git status --porcelain` byte-identical before/after each run** | copy lane log + two real-tree logs (`logs/`); proof lines pin rootdir/`core` to the copy and `utils`/`flynapse_otel` to their pins | VERIFIED — lane green modulo proven artefacts |
| PPC-14 | `tests/conftest.py:148` (A2-P2-5 seat) | Live positive re-execution: an UNPINNED real-tree run refused with `` `utils` imports from /home/aditya/Code/utils, not from /home/aditya/Code/utils-obsm ``, exit 4 — the venv-`.pth`-outranks-PYTHONPATH refusal fires in production conditions, exactly the standing trap the recipe warns about | accidental-then-kept probe (first real-tree invocation ran unpinned) | VERIFIED |
| PPC-F1 | `scripts/rbac/anonymise_already_deleted_chats.sql:264,280` | **FINDING (P3):** the findings half is invisible to its own gate for an out-of-contract shape. Both the rewrite (`:264`) and the read-back (`:280`) are guarded by `jsonb_typeof(f.evidence -> 'texts') = 'array'`, so a finding whose `texts` is a STRING (or object) holding copied user text is neither scrubbed nor counted — the script reports success over it. The analogous out-of-contract shapes elsewhere STOP the run (non-object signal `detail` and share/feedback payloads are counted by the gate), and the header's STOP list (`:109-111`) names "a feedback, share or signal payload" only, so this is neither closed nor declared. No live instance: the distiller writes `texts` as an array; the shape needs a corrupt or hand-edited row. Fix is one clause: count `jsonb_typeof(f.evidence -> 'texts') NOT IN ('array')` (non-NULL) on findings linked to a deleted chat's signals in the gate, or declare the limit beside the STOP cases | script read at HEAD; predicate-by-predicate comparison of the STOP coverage across the six copy halves | **OPEN — P3** (pooled to the estate micro-batch; not push-blocking) |

## What I did not test

- **Any db execution.** The 6 C15 db tests (`test_anonymise_deleted_chats_script_db.py`) and every
  other `db`/`postgres`-marked lane: index-verified only — Add. 274 records core analytics at
  `170e2ab` = 156 passed incl. the 6 — **db re-execution requested** for the C15 file once the db
  slot frees. The C15 script itself was never executed by anyone (by design; owner runs it at Phase H).
- Mutation re-execution: none run in this lane. The r10 NARROW Fable review re-executed the
  load-bearing mutation battery for the four P2 seats two days ago at `19403fa`; of the commits
  since, `df6a352` and `6899974` are prose and `170e2ab` extends `600730e`'s SQL script, whose
  proof lane is the db test file (index-verified only, re-execution requested above) — SQL is not
  a `mutant.sh` seat. My sampled re-runs cover the r9-P3 seats' tests instead.
- The api gateway's side of the mounted-app seams (api's own prepush review covered `44bd8d1..4bc2d4f`).
- Live services: no Weaviate, S3, Cognito, SMTP, no network beyond localhost:5432's refused
  collection probe (PPC-07).

## Verdict

**PUSH-CLEAN — P0 0 · P1 0 · P2 0 · P3 1.**

15 claims: 14 VERIFIED, 1 OPEN (PPC-F1, P3 — the C15 gate cannot see a non-array
`improvement_findings.evidence.texts`, while every sibling out-of-contract shape stops the run;
no live instance, one-clause fix or a declared limit — routed to the estate micro-batch, NOT
push-blocking). Range `e10a9ce..6899974` (168 commits; nothing in-range excluded — the
rebuild-gated work sits at/below the pushed master by construction). HEAD clean before and after;
the real tree byte-untouched (read-only runs proven by `git status` capture, three times).
