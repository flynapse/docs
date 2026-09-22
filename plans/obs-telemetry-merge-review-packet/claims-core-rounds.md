# Claims packet — core review rounds after B1 (`d7f7b54`) through `dc41caa`

Assembled 2026-09-22 by an Opus packet assembler, read-only. This file continues
`claims-C1-utils-B1-core.md`, which ends at core `d7f7b54`. It files every core review round since, and the
implementer rounds that answered them, as adjudicable rows re-stated against the tree as it stood when this file
was written. Nothing was run, edited, committed, stashed or checked out. No database, docker, AWS, Cognito or MCP
call was made.

**Sources.**
- The SDD ledger `.superpowers/sdd/observability-telemetry-merge-and-completion/progress.md`: CHECKPOINT 25
  addenda 3–6; Addenda 25, 30, 32, 37, 42, 43, 45, 46, 49, 52, 61, 63, 66, 68, 73, 74, 75, 76, 92, 95; CHECKPOINTS 31 and 32.
- Each reviewer's final report: the `SubagentHandback` or last assistant message of
  `~/.claude/projects/-home-aditya-Code/0de8ad5d-…/subagents/agent-<id>.jsonl`.
- The implementers' reports.
- core-obsm's own plan, `docs/plans/g61-comments-survive-tenant-delete.md` at HEAD (§5d, §7, §8, §9, §11–§17).
- The master plan: §2.2 step 4, §2.3a, §4a-bis, G.44, G.48, G.61, G.68, G.104, G.115, G.117, §6 and §8 Lessons.
- The owner decision sheet `owner-decisions-2026-09-22.md`.

**The tree.** `/home/aditya/Code/core-obsm`, branch `obs-merge`. A live implementer (`a669194b19f6a0d15`) committed
while this was assembled: `360088f` (the controller's note) → `3123800` (r6-F7) → `a58995a` (r6-F8) → `77a95bd`
(r6-F9) → `60acad9` (r6-F10) → `c2daac0` + **`dc41caa`** (g61 plan §17, the r6 record). **Every "State 2026-09-22"
cell is as of `dc41caa`, tree clean.**

## Rounds

| round | reviewer agent id | range | verdict (P0/P1/P2/P3) | ledger | what its "Tier" column meant |
|---|---|---|---|---|---|
| **R0a** correctness + gaps (six-repo batch; **core half only** filed here) | `a2a0edc3c3898cd61` | core `0609ad2` (moved to `b68e41c` mid-review) | "nothing breaks a consumer or loses data"; 3 core findings, not P-ranked | CP25 ("two adversarial reviews ran — AFTER the commits"); CP25 core-lane row | no table — severity derived (`*`) |
| **R0b** guard attack (six-repo; core half by sub-agent `a857866e85022a204`) | `a82f7a058bb89b9d6` | core `0609ad2` | core half: 4 proved defeats + 2 sweep blind spots | same | own tier 1/2 = consequence; severity derived |
| **R1** G.61 diff review — **implementer-commissioned** (spawnDepth 2 under `a5def59035346105b`), not a gate | `aaf847b0b13ef2655` | `0609ad2` + the uncommitted G.61 diff (landed as `b68e41c`) | 1 / 5 / 8 (its own scale) | none; triaged in g61 §5d | no table — derived |
| **R2** first independent core review | `af78213934793d676` | `0609ad2..23ee9b0` | FIX-FIRST 0 / 1 / 12 | CP25 addendum 6 | §2.3a-like (2 = schema) — derived |
| **R3A** reviewer A, in-tree mutations | `ac7886cea2b69e7f5` | `1e7d706`, `d59c44a`, `54b81c1` at HEAD `d62d6da` | FIX-FIRST 0 / 1 / 5 | Add. 25 (launch), **30** | §2.3a-like (0 = prose) — derived |
| **R3B** reviewer B = **the M-TRACEBACK scratch review** (one round; the brief listed it twice) | `a6c547ab2505f68e3` | `d59c44a..fdccdae` | FIX-FIRST 0 / 1 / 10 | Add. 25, **32** | confidence (0 = mutation-proved) — derived |
| **R4A** review A: teardown, scripts, Cognito | `ae5833840feb585bf` | `d62d6da..ba86d85`, lens A | FIX-FIRST 0 / 1 / 8 | Add. 42, **45** | **severity**: 0 = irreversible data loss or leak, 1 = correctness/availability, 2 = hygiene/test strength — moved |
| **R4B** review B: bodies, logs, spans | `a25426e0233505143` | `d62d6da..ba86d85`, lens B | FIX-FIRST 0 / 1 / 9 | Add. 42, **46** | severity (0 = leak) — moved |
| **G44** core-g44 review | `a692e04365c9121c6` | `core-obsm-g44` `425e3b7..eac494d` (`563a819`, `eac494d`) | MERGE-CLEAN 0 / 0 / 5 | Add. 43, **49** | severity — moved |
| **R5A** review A2 | `af2708fc9edbb7d7a` | `ba86d85..e8b894d`, lens A | MERGE-CLEAN 0 / 0 / 6 | Add. 68, **75** | severity 0–3 — moved |
| **R5B** review B2 | `a077df0019eb861ca` | `ba86d85..e8b894d`, lens B | FIX-FIRST 0 / 1 / 8 | Add. 68, **73** | severity (0 = leak) — moved |
| **R6** review r6 | `ab7273142e8ff7e86` | `e8b894d..625c0d3` (16 SHAs, each green at its own HEAD) | MERGE-CLEAN 0 / 0 / 11 + 4 nits | Add. **92** (launch), **95** (verdict) | severity 0–2 — moved |

| implementer | commits | ledger | independently reviewed by |
|---|---|---|---|
| `a5def59035346105b` (G.61, follow-ons, M-TRACEBACK, third-review batch, G.91/G.89/G.48) | `b68e41c..ba86d85` | CP25 add. 3, 6; Add. 25, 42 | R2, R3A, R3B, R4A, R4B |
| `a8c929bd273ac5005` (worktree: G.44 producer, keyset) | `563a819`, `eac494d`, `4c4bf6b`, `d8d8325` (merged at `3f1a588`) | Add. 37, 43, 52 | G44; R5A for `d8d8325` |
| `a8dca58e2bc842a65` (fourth-review fixes, g44 merge) | `bdaea7b..e8b894d` | Add. 61, 68 | R5A, R5B |
| `a669194b19f6a0d15` (LIVE) — A2+B2 fixes, M-JOB-TRACEPARENT, G.53 carry | `240bb9d..625c0d3` | Add. 92 | R6 |
| same — M-PII-IDS, M-SIGNUP-ORACLE, M-INVITE-FRAGMENT core half, `_root.py` re-copy, G.117 | `4040a82..b9a2343` | Add. 95 | **not yet** (core r7 queued, CP31) |
| same — r6 fix batch | `b31bd00..dc41caa` (recorded in g61 §17) | CP31 lanes table | **not yet** |

**22 commits (`625c0d3..dc41caa`, three of them plan records) have no independent review.** Every code commit among
them carries an implementer-recorded mutation proof. None carries a reviewer's.

**Not in these tables:** G.21, M-RUNERROR's core half (`bbc67ed`; reviewer `a95bdecf6cb95ed17`). It is a core
round, filed in `claims-copilot-mro-rounds.md` as G21-01 … G21-11. R0a and R0b's copilot-mro halves are filed there
too. See "Filed elsewhere" at the end.

## Scales

- **Severity** is the reviewer's own number, moved out of the column they called "Tier". The last column of the
  rounds table gives each round's definition. `*` means the assembler derived it, because that round's "Tier" meant
  something else:
  - `0*` a content or personal-data leak that ships;
  - `1*` a correctness or availability defect, or a gate, lock or guard-integrity defect;
  - `2*` a coverage gap (a blind guard or an unguarded property, with no live instance);
  - `3*` docs, prose or process.

  `—` means the claim holds and there is no defect. Where a thread spans rounds, each round's value is named.
- **Tier** is §2.3a's scale, assigned by the assembler:
  - **0** — a verifiable property that an **independent reviewer** saw a named guard fail on under a named
    mutation, with nothing later refuting it. It never goes to Fable.
  - **1** — consequential but reversible.
  - **2** — irreversible or estate-shaping: schema and its deploy order, tenancy teardown, personal data, a wire
    contract other repos consume, signal names and attributes, outcome semantics.

  A tier-2 decision stays tier 2 even when its code is settled: the guard proves the implementation, not the
  judgment. **An implementer's own mutation proof never buys tier 0.**
- **Chunk.** Tier 2 goes to F1. Tier 0/1 rows whose subject is content, PII, identity or tenancy teardown go to F1.
  Other defect fixes, tracing coverage, the keyset reader, backfill, stamps and the merge (its accepted bisect hole
  included) go to F2. Deferred, owner-owed, other accepted debt, prose, process and lane infrastructure go to F3.
- **Claim state (at review)**, as that reviewer found it: SETTLED, ASSERTED, OPEN, REFUTED or PARTIAL.
- **State 2026-09-22**, verified at `dc41caa`. It opens with one of these:
  - `HOLDS`;
  - `FIXED-AT <sha> · reviewer-proved` / `· reviewer-held` (held under attack with no reviewer mutation) /
    `· implementer-proved only`;
  - `FIXED (prose/plan)`;
  - `STILL OPEN`;
  - `SUPERSEDED-BY <M-*>`;
  - `ACCEPTED-AS-DEBT`;
  - `DEFERRED`;
  - `OWNER-OWED`;
  - `REFUTED` (the reviewer's claim was refuted).
- **File:line** marked `@HEAD` was re-resolved by the assembler at `dc41caa`. The only production file changed after
  the first resolution pass (`360088f`) is `document_endpoints.py`, and it was re-read. Unmarked cells are as the
  reviewer cited them at the reviewed SHA.

---

## Findings, ranked

The assembler's ranking of what an auditor needs, not a new review.

### 1. Twenty-two commits since the last independent review carry the round's riskiest changes

R6, the last independent review, is MERGE-CLEAN at `625c0d3`. It found no leak shipping. Everything since was proved
only by the implementer that wrote it:
- **M-PII-IDS** (R4B-06);
- **M-SIGNUP-ORACLE** and its extension (R5B-03, IMP-01);
- **M-INVITE-FRAGMENT**, core half (IMP-02);
- the r6 answers to F1 (T-06), F2 (R6-01), F3 (T-01), F4 (T-07), F5 (T-10), F7 (T-02, T-03), F8 (T-04), F9 (T-05),
  F10 (R6-03) and F11 (R6-04).

Three of those answer guards that had already been defeated in two to four consecutive rounds. **Core r7 is the
missing gate.**

### 2. Two owner-run DDL steps gate any core deploy, and both are unrun by rule

- **C1**, `drop_comments_tenants_fk.sql` (R2-01, R2-02, T-08). Until it runs, tenant deletes answer 503.
- **C9**, the `automation_runs.traceparent` column (R6-06, R6-02, R6-04). Until it exists, every one-shot enqueue
  fails `UndefinedColumn` and api's worker refuses to boot, which stops all automations.

core's db lane is red by design until both run: 21 failed + 1 error. 20 failures await C9; the G.61 pair (1F + 1E)
awaits C1 (g61 §17, as corrected in `dc41caa`).

### 3. Two r6 findings are still partly open at `dc41caa`

The implementer closed its r6 queue with `60acad9` (F10) and recorded the round in g61 §17. Two parts of it were
never claimed:
- **F7, Cognito part**: a folded `getattr` and `operator.methodcaller` (T-09). No commit touches the Cognito sweep,
  and g61 §17's F7 row names no Cognito shape.
- **F9, part**: `type('X', (Refusal,), {})` and a tuple-unpack alias (T-05). `77a95bd` and g61 §17 both claim only
  module and class bodies, lambdas and `partial`.

F10 now carries a declared, pinned limit: outside the pointer fields, a url on an S3-compatible host that is not the
configured endpoint is not recognisable by its shape (R6-03).

### 4. Tier-2 judgment no test settles

- The M-CASCADE mechanism keeps comment PII until someone runs a manual sweep (R1-02 → M-COMMENT-PII).
- The teardown lock does not cover keys deeper than `tenants` (IMP-06).
- The anonymous email-existence door (IMP-10 → M-EMAIL-DOOR).
- The producer-span vocabulary and won/lost semantics are ASSERTED only (G44-09, G44-10).
- The 422 body contract changed for every route, and no round records a consumer check (T-07).

### 5. Guards were defeated in consecutive rounds

- The register lock was blessed by one hunk in **four** rounds, then frozen empty (T-01).
- The router disclosure sweep was defeated **three** times (T-04).
- The log and span guards were partial in **every** round (T-02, T-03).
- The Refusal census was defeated twice (T-05).
- The storage-location pin was shape-only once (T-06).

Two threads ended in a structural answer rather than another detector patch: the registers frozen empty (T-01), and
storage locations hidden by type (T-06). The rest are still detector patches. The plan's Lessons already carry the
rule: "a guard patched three times, with a P1 in every review round, was a design problem".

### 6. The record contradicts itself in five places (assembler spot-checks)

**(a)** The decision sheet's C1 says the refusal is "a 503 that names the script". It does not.
`TEARDOWN_CASCADE_MISMATCH` (`core/resources/tenants/services/tenant_service.py:239-243` @HEAD) names no file. The
log line beside it does, per g61 §8 F1b.

**(b)** §4a-bis's controller call under M-SIGNUP-ORACLE says "core r6 found" the no-workspace 500. **R6's report
does not contain it** (both deliveries, identical, were read). It came from the implementer's residual list in its
`b9a2343` report, and g61 §16 records it there (IMP-01).

**(c)** g61 §11's bullet "`iter_all_tenants` still pages by offset (carried from §7)" is **stale**. Since `eac494d`
(merged at `3f1a588`), `iter_all_tenants` walks `list_tenants_page` (`tenant_service.py:432-470` @HEAD).

**(d)** The master plan's §2.2 step 4 lists "Five schema changes" and **omits the comments-FK drop**. It is carried
only by C1 and by C5's order, because `migrate_tenancy_schema.py` never drops a constraint. A reader of the DB step
alone misses it.

**(e)** The g61 plan recorded r6 only after the fix batch (§17, `c2daac0`; lane count corrected in `dc41caa`).
Its §17 F7 row claims no Cognito shape (T-09), and its §11 still carries (c)'s stale bullet.

---

## What the reviewers tried to break and could not

Aggregated from each report's "held" or "could not break" section. Each is evidence behind a row below.

- **R0a:**
  - Savepoint mechanics: `rowcount` is read before `RELEASE`, and `skipped_unchanged` partitions correctly at 0, 1
    and many refusals.
  - A dropped connection aborts the run rather than being swallowed.
  - `runs_on_schedule` blast radius: no `model_dump()` of `Automation` is round-tripped into a write.
  - `sweep_span.py`'s keywords are literal `False`.
- **R0b** (`a857866e85022a204`): the savepoint proof is not structurally vacuous. Removing all three savepoint
  statements gives 2 failures with the right diagnostic, and it calls the production symbol. `ONE_SHOT_KINDS` is
  genuinely single-sourced: api's `loop.py:313` is a plain rebind, asserted with `is`.
- **R1:**
  - No consumer relied on the cascade. The residue sweep `delete_unentitled_partition.py` is catalog-derived, so
    comments are swept automatically.
  - The cardinal "eight" family is consistent with the 8 `_TENANTS_FK` attachment sites.
  - Both singled-out guards are non-vacuous (the splice is asserted to have mutated).
  - The PL/pgSQL is valid (`RETURN;` in `DO`; the aggregate over zero rows). ACCESS EXCLUSIVE on `tenants` is correct.
  - `flynapse_grant` holds no privilege on `comments`.
- **R2:**
  - `SET NULL` is impossible.
  - Re-attaching the FK fails 9 unit guards.
  - Votes survive. The PG16 vote-delete failure was reproduced on 16.11.
  - 64 rows fit the subxid cache and the 65th overflows.
  - The `runs_on_schedule` guard derives routes from the router.
  - The keyset uses one expression for the sort and the cursor, and the status filter applies to page and total alike.
- **R3A:**
  - No race between check and delete short of DDL. No fail-open on a DB error.
  - A migrated catalog reads `[]` (probe over 35 real edges).
  - The stamps have no cross-width reader.
  - The keyset model is faithful: the count SQL has no cursor clause.
  - The live subxid measurement runs in the db lane and reads the writing backend.
- **R3B:**
  - All 118 `**failure_fields(...)` sites are free of keyword collisions, wrong handler names and braces.
  - 54 of 55 `internal_error` calls sit inside exactly one `except`.
  - Nothing reads `CommentDatabaseError`'s message estate-wide.
- **R4A:**
  - Fail-closed on all three shapes.
  - The channel door is gated.
  - Drift answers correctly for 5 catalog shapes.
  - Cognito spans carry no pool, user, email or ARN on live spans.
  - Behaviour is unchanged. Every commit's touched tests are green at its own SHA.
- **R4B:**
  - No HTTP consumer depends on the old 400s or texts.
  - `send_invitation_email`'s new required `invitation_id` is passed by both callers.
  - Both span test files use a private provider, not G.110's scrubber.
  - Each fix commit's tests fail at its parent.
- **G44:**
  - No text is exported under a real psycopg2 DETAIL or an RLS error.
  - Consumer parity holds.
  - A real 8-thread race gives 1 won and 7 lost, all roots.
  - The walk has no skip, duplicate or loop under adversarial sequences.
  - The guard reads `core/` and `scripts/`.
- **R5A:**
  - MintReceipt resists copy, deepcopy, pickle, `object.__new__`, a real seal, an other-tenant receipt and a
    32-thread redeem.
  - The lock matrix, privilege and deadlock analysis hold, and the path fails closed.
  - `d8d8325` is one snapshot.
  - The migration argv premise holds.
  - The SQL cannot be captured by an operator or a function.
  - Every fix commit is red on its parent's source.
- **R5B:**
  - `stream_body` survives close, first-read failure and `GeneratorExit`.
  - `raise Refusal(str(e))` and 10 other wrappings fire the raise rule.
  - The whole B-F5 list fires.
  - `RequestModel` rejects nested NULs and NUL keys, and every mounted body inherits it.
  - Commit hygiene holds.
- **R6:**
  - 16 SHAs are green at their own HEAD.
  - The core app's handlers apply because it is mounted in api (`main.py:480`).
  - Traceparent edge cases hold under probe: an extra field, 56 characters, whitespace, a newline, version `ff`,
    zero ids, non-ASCII digits.
  - `migrate_tenancy_schema.py`'s ADD COLUMN pass would add `traceparent text`.

**Assembler spot-checks that matched the record at `dc41caa`:**
- The gate sits inside `delete_tenant` (`:946`), with `LOCK` then check then DELETE on one cursor (`:1030-1037`).
- The script's `SET LOCAL search_path = pg_catalog, pg_temp` (`:158`) and its `public.`-qualified relations.
- `json.dumps` precedes `send_span` (`automation_store.py:1108-1111`).
- `repr=False` on `s3_key` and `url` (`pdf_object_resolver.py:86,96`).
- Both registers are asserted `== {}`.
- The timezone refusal is a fixed sentence (`schemas.py:123`).
- `EXPECTED_COLUMNS["automation_runs"]` includes `traceparent`, and the shape test is at `test_automation_tables.py:384`.
- The witness commits before its zero (`test_chat_turn_facts_backfill_db.py:284,292`).
- `models.py:121` "Only the casualty half is rendered".
- `test_rbac_roundtrip.py:141,178` prose corrected.
- The `/documents/document` storage predicate after `60acad9`: `_AWS_HOST_SUFFIXES` includes `amazonaws.com.cn`
  (`document_endpoints.py:82`), `LOCATION_WITHHELD` (`:93`), `_is_storage_location` (`:104`).

## What I did not test

- **Nothing was executed.** No lane, no mutation, no probe. Every mutation result below is a reviewer's or an
  implementer's record, cited by its source. None was reproduced here.
- The r6 fix batch was read by commit message, diffstat and spot reads of the resulting source. Its mutation claims
  ("7 mutants RED", "11 mutants RED", …) are the implementer's.
- Items routed out of core were not verified in their trees:
  - utils G.115, `0211f9b`;
  - copilot-mro's `data_discovery/jobs.py` and `document_hub/jobs.py`;
  - copilot-mro's `ad_notification_dispatcher.py` offset walk;
  - the api prose and the `SIBLING_CHECKOUTS` leak;
  - api's POST-preview skip list;
  - flynapse-otel's corpus rows for r6 F7 (`34c814a`).
- Live database state was not checked: whether C1 or C9 has run anywhere, and whether any comment was lost since
  2026-09-21. The earlier read-only check (plan G.61; g61 §5a) found 9 recorded deletions, all of empty scratch
  tenants.
- **What the reviewers themselves did not test:**
  - R3B: the db and authz lanes, by instruction.
  - R2: the keyset tests were not re-run.
  - R4A: whether any role holds CREATE on `public`. DB access was banned, and T-08's overload-capture risk depends
    on it.
  - R0a: whether a SERIALIZABLE serialization failure survives `ROLLBACK TO`. Nothing sets that isolation.
  - Nobody ran `drop_comments_tenants_fk.sql`, by rule.
  - The production Postgres major version (R2 F12) was not found in iac.
- **One reviewer breached its ban**, and it is recorded rather than hidden. R5B's probe of
  `GET /v1/users/email/a%00b@x.example` read the local test DB once, read-only, through the app pool. The plan's
  Lessons (2026-09-22) now extend "no direct DB queries" to app-driving probes.

---

## Claims table

Rows `T-*` are threads: one property attacked in several rounds, filed once with every source named. The per-round
rows follow.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state (at review) | State 2026-09-22 | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-01 | core | `tests/unit/observability/test_core_logs_carry_no_exception_text.py:1482-1483`, `tests/unit/observability/test_core_log_messages_are_not_format_strings.py:207-208` @HEAD; `tests/_register_reasons.py` | Both exception-text debt registers (M-TRACEBACK debt, format-string) are frozen EMPTY; re-opening one means editing an `assert … == {}` | Each round blessed a real planted leak with one test-only hunk: no frozen twin (R3B M3); entry + bumped total + reason `"9999-99-99 lgtm"` (R4B F7, 97 passed); a reason citing any plan that names the module, `docs/plans/../../README.md` or `2000-01-01` (R5B P2-3, 2809 passed); a new `docs/plans/bless.md` naming the exact key (R6 F3, 221 passed; a plan-line HTML comment variant 218 passed) | four defeats, each over a real planted leak | the two `== {}` assertions | defeats: R3B, R4B, R5B, R6. Fix `0e82657`: implementer only (the bless.md hunk RED, per commit) | R3B 1*, R4B 1*, R5B 0, R6 0 | 1 | F1 | REFUTED in R3B, R4B, R5B, R6 | FIXED-AT `0e82657` · implementer-proved only (chain `bc3285c` → `0c617f9` → `c7863c6` → `0e82657`) | a6c547ab2505f68e3 P2-3; a25426e0233505143 F7; a077df0019eb861ca P2-3; ab7273142e8ff7e86 F3; Add. 32, 46, 73, 95 |
| T-02 | core | `tests/unit/observability/test_core_logs_carry_no_exception_text.py` | The log guard derives sinks and follows a caught exception's taint through every shape a reviewer found; the rest is declared in its docstring | R3B: `logger.patch`, helper-side alias, two-hop wrapper, helper name alias, splat, a subset sink witness. R4B F5: 8 of 21 plants unblocked — aliased cross-module sink, `warnings.warn`, exception factory, gather/`.exception()`, `.with_traceback`. R5B P2-7: `append`, `nonlocal`, `yield`, `LoggerAdapter`, `from sys import stderr`, `os.write(2,…)`, `loop.call_exception_handler`. R6 F7: `sys.excepthook`, `pprint`, `traceback.print_last`, `out = sys.stderr`, class-attribute logger, `setattr`/ContextVar stashes | no shape had a live instance in core when found (R3B scan, R5B, R6) | `LEAK_SHAPES` self-test with sanctioned twins | `425e3b7` by R4B (raise rule off → 3 red; patch door off → 1 red); `552a5ad` by R5B (warn disabled → RED); `574113f` by R6 (listed shapes caught). `3123800`: implementer only (11 mutants) | R3B 2*, R4B 0, R5B 0, R6 0 | 1 | F1 | PARTIAL every round | FIXED-AT `3123800` · implementer-proved only. Declared, not closed: run-time-chosen levels, `setattr`/ContextVar/other-object stashes, cross-module hand-offs, `partial` of a derived helper, `sys.stderr.buffer`, third-party printers | a6c547ab2505f68e3 P2-4; a25426e0233505143 F5; a077df0019eb861ca P2-7; ab7273142e8ff7e86 F7 |
| T-03 | core | `tests/unit/observability/test_core_spans_withhold_exception_text.py` (name-tail `:214` @HEAD) | The span sweep derives openers and writers and follows a caught exception's taint into span status, attributes, events, names and links | R0b: `trace.Status(ERROR, str(exc))` and a bare `except:` + `format_exc()` passed all three estate sweeps. R2 F2: a traceback rendered into a local; `trace.use_span` with defaults (exported `status.description` + an `exception` event on the real SDK); `sys.exc_info()`. R3A P2-2: `for`/`with`/comprehension targets, same-module helper, opener `attributes=` and name, `add_link`. R4B F6: a name bound in the `except` written after the `try`; a same-module `_mark(span, exc)`. R5B P2-7: helper alias, `append`. R6 F7: an opener reached through a name; return/yield hand-off | core's openers are `sweep_span.py` and `queue_span.py`; no live instance in any round | detector self-test; `::test_use_span_with_its_defaults_really_exports_the_message` | `a56a305` by R4B (each of five mechanisms red when removed); `af5fc0c` by R5B (helpers → `{}` → RED). `0ea20d3`, `d59c44a`, `574113f`, `3123800`: implementer only | R0b 2*, R2 2*, R3A 2*, R4B 0, R5B 0, R6 0 | 1 | F1 | REFUTED (R0b, R2), PARTIAL (R3A, R4B, R5B, R6) | FIXED-AT `3123800` · implementer-proved only; declared: baggage and metrics, cross-module hand-offs | a82f7a058bb89b9d6 #5, #13; af78213934793d676 F2; ac7886cea2b69e7f5 P2-2; a25426e0233505143 F6; a077df0019eb861ca P2-7; ab7273142e8ff7e86 F7 |
| T-04 | core | `tests/api/tenancy/test_router_error_disclosure_sweep.py` | Behavioural half: per module, inject every exception type it catches, carrying a secret, through every route. Structural half: no response built from the text of a caught non-`Refusal`, through aliases, helpers, attributes and returned values | R3B: its P1 sat in the sweep's blind spot (module exempt; only `RuntimeError` injected). R4B F4: a planted `except LookupError as e: raise HTTPException(400, detail=str(e))` passed (203 + 129 green). R5B P2-1: `exc.response["Error"]["Message"]` (2810 green) and a returned `{"error": str(missing)}`. R6 F8: unnamed `sys.exception()`, text returned after the `try`, AugAssign/AnnAssign/tuple aliases, `H = HTTPException`, headers on the injected response | each round's plant green on the then-current guard | the sweep file | `0e0c57d`: implementer re-ran R4B's plant RED; R5B then defeated it. `241151c`: R6 PARTIAL. `a58995a`: implementer only (5 mutants) | R3B 2*, R4B 1*, R5B 0, R6 1 | 1 | F1 | REFUTED (R4B, R5B), PARTIAL (R6) | FIXED-AT `a58995a` · implementer-proved only | a6c547ab2505f68e3 Q6; a25426e0233505143 F4; a077df0019eb861ca P2-1; ab7273142e8ff7e86 F8 |
| T-05 | core | `tests/api/tenancy/test_refusal_is_the_only_echoed_value_error.py:218` @HEAD (census: 37 constructions in 28 functions) | Count every construction of `Refusal` or a descendant — per module, class and function scope — resolved through aliases, subclassing and attribute spellings, pinned by equality | R5B P2-2: the census pinned functions, not statements, and matched the bare name (a second server-text `Refusal` in `create_user` + `Refusal as Declined` → 134 passed). R6 F9: function bodies only — module-level, class-body, `lambda x: Refusal(x)`, `partial(Refusal)`, `type('X', (Refusal,), {})`, tuple-unpack alias missed | R5B audited all 18 sites / 6 classes: no server data today; R6 confirmed 33/25 at `625c0d3` | the census | `f155fb6`: implementer (3 plants RED), R6 PARTIAL. `77a95bd`: implementer only (module-level plant in `user_service` RED) | R5B 0, R6 1 | 1 | F1 | REFUTED (R5B), PARTIAL (R6) | FIXED-AT `77a95bd` · implementer-proved only, for module/class bodies, lambdas and partials. `type('X', (Refusal,), {})` and a tuple-unpack alias are claimed by neither the commit nor g61 §17 — unverified | a077df0019eb861ca P2-2; ab7273142e8ff7e86 F9 |
| T-06 | core | `core/resources/document_viewer/services/pdf_object_resolver.py:84-96` @HEAD (`s3_key`, `url` as `field(repr=False)`); `pdf_page_endpoints.py`; `services/pdf_page_service.py` | The `/pdf` routes log `document_id` + department only; storage locations are hidden BY TYPE in the resolved objects; the pin follows containers, aliases, streams, spans and globals | R5B P1: both routes logged the tenant object key at INFO on every request; the service logged bucket + key + filename; the resolver logged a whole stored url — B-F8 had fixed the wire only. R6 F1: the fix's AST pin was shape-only — `logger.info("catalog probe done", found=matches)` passed 3273 tests; 15 of 17 plants missed; dataclass reprs carried the key | R5B source read; R6 m1b | `tests/unit/observability/test_storage_locations_stay_out_of_logs.py::test_no_log_line_on_the_storage_surface_names_a_storage_location` (:369), `::test_the_resolved_objects_reprs_name_no_location` (:515), `::test_resolving_a_catalog_hit_logs_no_location` (:530) | `240bb9d`: R6 m1 RED (route capture) — the source fix holds. `a7bb837`: implementer only (7 mutants) | R5B 0, R6 0 | 1 | F1 | OPEN (R5B), PARTIAL (R6) | FIXED-AT `240bb9d` (reviewer-proved at source, R6) + `a7bb837` (type + pin) · implementer-proved only | a077df0019eb861ca P1; ab7273142e8ff7e86 F1; Add. 73, 92, 95 |
| T-07 | core | `core/resources/http_errors.py:167` @HEAD (`request_validation_refused`); `core/fastapi_app.py:169`; `core/resources/request_model.py`; `core/resources/automations/models/schemas.py:123` @HEAD | A 422 answers `loc`/`msg`/`type` only; `msg` verbatim only for a core `Refusal`, every other value error normalised; a NUL refused at the model boundary; the timezone refusal a fixed sentence | R3B P2-1: `timezone: "America"` → site-packages path in the 422 (pre-existing; any authenticated caller). R4B F3: a NUL in `name` → psycopg2 driver text in a 400 on all 7 `refused` routes incl. anonymous `POST /users`. R5B P2-4: the NUL 422 echoed the WHOLE raw body incl. `password` (no core handler). R6 F4: `msg` still quoted input — the timezone `{value!r}`, and `EmailStr`'s IDNA refusal naming the decoded domain label | probes through the mounted app in each round | `tests/api/routing/test_validation_answers_quote_no_values.py`; `tests/unit/automations/test_automation_schemas.py`; `test_refusal_is_the_only_echoed_value_error.py` (NUL) | `337cbb2` by R4B (2 red at parent); `9532a15` by R5B (`UserCreate`→`BaseModel` → 2 RED); `3513dfa` by R6 (m2 RED 8 — keys hold, `msg` did not). `2abc449`: implementer only (4 mutants) | R3B 0*, R4B 0, R5B 1, R6 1 | 2 | F1 | OPEN (R3B, R4B), PARTIAL (R5B, R6) | FIXED-AT `2abc449` · implementer-proved only. The 422 body shape changed for every route; no round records a consumer check | a6c547ab2505f68e3 P2-1; a25426e0233505143 F3; a077df0019eb861ca P2-4; ab7273142e8ff7e86 F4 |
| T-08 | core | `scripts/rbac/drop_comments_tenants_fk.sql:158-211` @HEAD | `SET LOCAL search_path = pg_catalog, pg_temp`; every relation `public.`-qualified; predicate and idempotency described as they are | R1: path unpinned, predicate over-described (matches any FK, not only the CASCADE one), re-run raises without the self-FK. R2 F10: `public, pg_catalog` let `public` shadow built-ins. R3A P2-5: `pg_temp` implicitly first. R4A P2#5: `public.format(text, text)` beats `pg_catalog.format(text, VARIADIC "any")` whatever the path order | R4A: exploitable only if a role holds CREATE on `public` — not verified | `tests/unit/db/test_tenant_cascade_boot_check.py::test_the_remedy_script_pins_a_search_path_nothing_can_shadow` (:496), `::test_the_remedy_script_names_every_relation_by_schema` (:510) | R4A m-pgtemp 1F (on `a59daa1`); R5A: `ce64cb7`'s pins red on parent source | R1 3*, R2 2*, R3A 2*, R4A 0 | 2 | F1 | PARTIAL (R4A) | FIXED-AT `ce64cb7` · reviewer-proved for the text (R5A: "operators and functions cannot be captured"). Never executed — running it is OWNER-OWED C1 | aaf847b0b13ef2655 P2; af78213934793d676 F10; ac7886cea2b69e7f5 P2-5; ae5833840feb585bf P2#5; af2708fc9edbb7d7a |
| T-09 | core | `tests/unit/observability/test_cognito_calls_are_spanned.py:225` @HEAD (declared blind spots `:25-28`) | Every Cognito call sits lexically inside `with cognito_span(client, "<Op>")` naming that op; ops read from botocore's `cognito-idp` model; 5 sites and 2 factories pinned by equality | R4A P2#6: a sixth unwrapped `admin_delete_user` → 202 passed. R5A P2-2: a paginator → 1734 green; also `_make_api_call`, `partial`, a lambda run outside its span, a span on another client, constant-named factories. R6 F7: a folded `getattr(c, 'admin_' + 'get_user')` and `operator.methodcaller` silent | no live unwrapped call; the botocore read needs no credentials (R5A socket-denied probe) | `::test_every_cognito_call_is_inside_the_span_that_names_it` (:225) | `775b30a`: implementer; R5A defeated it. `dcb27e0`: implementer (7 mutants + paginator plant); R6 HOLDS with minor gaps | R4A 1, R5A 2, R6 2 | 1 | F2 | REFUTED (R5A), HOLDS-with-gaps (R6) | STILL OPEN for the two R6 F7 shapes: no commit after `dcb27e0` touches the file, its declared blind spots (`:25-28` @HEAD) name only run-time-named ops, late paginator iteration and helpers outside `core/`, and g61 §17's F7 row claims no Cognito shape | ae5833840feb585bf P2#6; af2708fc9edbb7d7a P2-2; ab7273142e8ff7e86 F7 |
| T-10 | core | `scripts/_workspace.py`, `tests/conftest.py`, `tests/_root.py` @HEAD | Scripts and the root conftest resolve siblings through ONE `tests/_root.py`, a byte copy of api's git-family resolver. A bare path is returned only when no checkout of the sibling exists; a declared sibling always raises; the conftest refuses unless `utils` is the paired checkout; drift-pinned to api's committed copy | R4A P1: `_workspace.py` (a copy of the OLD split) sent `core-obsm-g44` to the pre-merge `utils`/`copilot-mro`/`api`; its parity test stayed green because both copies were wrong alike. api r5 (Add. 63): `_workspace.py:77` swallowed every `RootAnchorError`. R5A P2-4: a malformed `SIBLING_CHECKOUTS` ignored with no checkout; P2-5: roots appended after the venv `.pth`. R6 F5: no drift pin; api `8d7e39f` changed `_root.py` four minutes after `bd9c160` | posed workspaces (R4A, R5A); R5A: the carried resolver answers `-obsm` from `core-obsm-g44` | `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py`; `tests/unit/infra/test_conftest_imports_the_paired_utils.py` | `1f03ef1`, `2c3d064`, `24f6cce`: R5A (red on parent source). `bd9c160`: R6 (fixture off → +4 reds). `df907e1`, `2ab3e0a`: R6 HOLDS, not re-mutated. `2158813` (md5 `3d192468`) and `7438263`: implementer only | R4A 1, R5A 2, R6 2 | 1 | F3 | REFUTED (R4A), PARTIAL (R5A, R6) | FIXED-AT `7438263` · implementer-proved only for the drift pin; earlier links reviewer-held. `pyproject.toml:43` `path = "../utils"` STILL OPEN — declared uncatchable (TOML cannot name a variant) | ae5833840feb585bf P1; api r5 (Add. 63); af2708fc9edbb7d7a P2-4, P2-5; ab7273142e8ff7e86 F5 |
| R0a-01 | core | `scripts/backfill_chat_turn_facts.py` (writer; one commit per 500-row batch at `0609ad2`) | Commit the writes in chunks of ≤64 rows; keep the 500-row read | One savepoint per row puts 500 subxids in one transaction; past `PGPROC_MAX_CACHED_SUBXIDS` = 64 every backend's visibility check for those xids falls to the `pg_subtrans` SLRU | R0a reasoned it; R2 checked the arithmetic (the 65th assignment overflows); R3A measured live: with the chunking bypassed `pg_stat_get_backend_subxact` reads `[(64, True)]` | `tests/unit/analytics/test_chat_turn_facts_subtransaction_budget.py::test_backfill_itself_never_hands_a_transaction_more_rows_than_the_bound` (:312); `tests/db/analytics/test_chat_turn_facts_backfill_db.py::test_no_backfill_transaction_overflows_the_backends_subxid_cache` (:392) | yes — R3A: bypass → both fail | 1* | 0 | F2 | OPEN (reasoned) | FIXED-AT `0ea20d3` (+ `d59c44a` driver + live test) · reviewer-proved (R3A) | a2a0edc3c3898cd61 #1; g61 §7 |
| R0a-02 | core | `scripts/backfill_chat_turn_facts.py` `run()` | Exit non-zero when any row was refused | Savepoints turned an aborting refusal into a counted one, so an all-refused run exited 0 | R0a scenario (statement_timeout, revoked grant, new NOT NULL); no scheduled caller found | `tests/unit/analytics/test_chat_turn_facts_backfill_report.py::test_a_run_that_refused_rows_exits_non_zero` (:165) | not by a reviewer (R2 named the guard, mutated only RELEASE) | 1* | 1 | F2 | OPEN | FIXED-AT `0ea20d3` · implementer-proved only | a2a0edc3c3898cd61 #2; g61 §7 |
| R0a-03 | core | `core/resources/tenants/services/tenant_service.py` `list_tenants` (`:560`) and `list_tenants_page` (`:598`) @HEAD | Page the registry by value on `(COALESCE(created_at,''), tenant_id)`; the offset reader gets a total order | An offset walk with no tiebreaker skips a live tenant when one is deleted mid-walk, and the total shrinks by the same one, so the roster comes back short without raising | R0a worked example; R2: one expression feeds sort, predicate and cursor; `copilot_mro_test` holds a NULL `created_at`; G44 KM1–KM4; R5A one snapshot | `tests/unit/db/test_tenant_keyset_page.py::test_the_offset_reader_breaks_ties_the_same_way` (:348); `tests/db/rbac/test_tenant_keyset_page_db.py` | yes — G44 (KM1–KM4); R5A (LEFT→INNER JOIN red in the db lane) | 1* | 0 | F2 | OPEN (reasoned) | FIXED-AT `2e66ee6` + `eac494d` (walk) + `d8d8325` (one statement) · reviewer-proved (G44, R5A). api's walker moved in api `6afd640` (N4 slice) | a2a0edc3c3898cd61 #3; CP25 add. 3; Add. 8 |
| R0b-01 | core | `tests/unit/automations/test_runs_on_schedule_contract.py:239` @HEAD | Pin `runs_on_schedule` on the REAL routes' serialisation args, all four `Automation` routes | The guard built its own `FastAPI()` and read only `route.response_model`; OpenAPI is blind to `response_model_exclude`; only 2 of 4 routes were named | `response_model_exclude={"runs_on_schedule"}` on `GET /automations/{id}` → 228 passed, field gone from the wire | `::test_no_real_route_serialises_the_field_away_again` (:239) | yes — R2: `response_model_exclude` on PATCH → fails; routes derived from the router, pinned to 4 | 2* | 0 | F2 | REFUTED (guard blind) | FIXED-AT `0ea20d3` · reviewer-proved (R2) | a857866e85022a204 #1; a82f7a058bb89b9d6 #6; g61 §7 |
| R0b-02 | core | `scripts/backfill_chat_turn_facts.py` (`RELEASE SAVEPOINT` ×2) | Every SAVEPOINT is matched by exactly one RELEASE, and the depth returns to zero after a refused row | Dropping both RELEASEs left the db file 5/5 green while 100 savepoints stayed open over 100 rows | a857866e85022a204: live count 0 → 100 | `test_chat_turn_facts_subtransaction_budget.py::test_every_savepoint_is_matched_by_exactly_one_release` (:187), `::test_the_depth_returns_to_zero_after_a_refused_row_too` (:171) | yes — R2: handler RELEASE dropped → both fail | 2* | 0 | F2 | OPEN (unguarded) | FIXED-AT `0ea20d3` · reviewer-proved (R2) | a857866e85022a204 #2; a82f7a058bb89b9d6 #7; g61 §7 |
| R0b-03 | core | `tests/db/analytics/test_chat_turn_facts_backfill_db.py:284,292` @HEAD | The witness commits as production does, so its closing zero can only be the abort's | `assert _facts_count == 0` measured the test's own `finally: rollback()`; three valid rows gave 0 too | a857866e85022a204 ran the block with no refusal → 0 | the witness itself | not by a reviewer | 2* | 1 | F3 | REFUTED (vacuous) | FIXED-AT `0ea20d3` · implementer-proved only (the assembler read commit-then-assert at HEAD) | a857866e85022a204 #3; a82f7a058bb89b9d6 #10; g61 §7 |
| R0b-04 | core | `scripts/run_db_lane.py:268-305` @HEAD (`_provision`, `--registry core`) | Keep the lane `--registry core`, owner of its own scratch, no policies; record that the chat relations are not built | `chats`, `chat_blocks`, `chat_turn_facts` are copilot-mro relations; `provision_rls.py` refuses a core-only schema | the 14 `tests/db/analytics` files pass only when run by hand against the shared `copilot_mro_test`; `_BLOCKS_SQL` has no tenant predicate, so isolation rests on RLS | none | n/a | 2* | 1 | F3 | OPEN | STILL OPEN — recorded in `_provision`'s body ("Recorded rather than worked around"). Every db-lane figure in this slice was taken by hand against `copilot_mro_test`, not through `run_db_lane.py` | a857866e85022a204 #4 |
| R1-01 | core | `core/resources/tenants/tenant_endpoints.py` 200 body (`residual_rows_notice`); `core/services/__init__.py` | Make the deploy order (migration before code) enforceable, not documentary | On an unmigrated cluster the 200 body promises comments survive while the FK still cascades them — the original P0, re-armed with a written promise; the only detector was a db lane red by construction | reviewer read | first answer a boot log line (`af6adce`) — see R2-03 | n/a (finding) | 1* | 2 | F1 | OPEN | FIXED-AT `af6adce` (detect) → `1e7d706` (503) → `802850c` (gate inside `delete_tenant`) → `221dbf4` (one locked transaction) · reviewer-proved by R3A and R4A, held by R5A; the rebindable-gate residue is R6-01 | aaf847b0b13ef2655 P0-1; g61 §5d |
| R1-02 | core | `core/db/table_definitions.py` `comments` (`author_name`, `author_email`, `content`, `mentions`) | Dropping the FK keeps comment personal data after a tenant delete | A deletion is the operation most likely to be an erasure request; the alternative, anonymising the author fields inside the teardown, was never weighed | reviewer read; `delete_unentitled_partition.py` is catalog-derived and does reach comments | none | n/a | 0* | 2 | F1 | OPEN | SUPERSEDED-BY M-COMMENT-PII (KEEP; `--purged-tenant <id> --execute` removes them). Caveat recorded: the sweep is manual and dry-run by default | aaf847b0b13ef2655 P1-2; g61 §5d; §4a-bis M-COMMENT-PII; CP25 add. 4, 5 |
| R1-03 | core | `core/resources/tenants/models.py:115-129` @HEAD | Say only the casualty half of the notice is rendered | `models.py` claimed the rendering keeps both halves honest; rendering against a regressed census produced a self-contradicting sentence | reviewer rendered `_residual_rows_notice(… + ("comments","comment_thumbs_up"))` | none (prose) | n/a | 3* | 1 | F3 | REFUTED | FIXED (prose) at `af6adce` — `:121` @HEAD: "Only the casualty half is rendered" | aaf847b0b13ef2655 P1-3; g61 §5d |
| R1-04 | core | `tests/unit/db/test_tenant_cascade_census.py:392` @HEAD | Guard the hand-written survivor clause against naming a relation the census destroys | Only one direction was guarded; the wire sentence had a literal-presence test | reviewer's proposal | `::test_the_survivor_clause_never_names_a_relation_the_census_destroys` (:392), `::test_no_relation_that_survives_a_teardown_is_named_among_the_casualties` (:317) | yes — R2: re-attach `_TENANTS_FK` → 9 unit failures (census ×6, boot ×3) | 2* | 0 | F1 | OPEN | FIXED-AT `af6adce` · reviewer-proved (R2) | aaf847b0b13ef2655 P1-4; af78213934793d676 table |
| R1-05 | core | `tests/db/rbac/test_rbac_roundtrip.py:141,178` @HEAD | — (finding: stale "cascades on teardown" prose; a comment and votes leak on the shared estate if an assert fails) | — | reviewer read | none | n/a | 2* | 1 | F3 | OPEN | REFUTED by the implementer: fixed and committed before the report landed (g61 §5d). Prose at HEAD reads "mostly cascades" and "cleans the identity children" | aaf847b0b13ef2655 P1-5; g61 §5d |
| R1-06 | core | `core/db/table_definitions.py:1030-1047` @HEAD | Scope "losing the FK loses nothing" to the application role; state the superuser and race gaps; do not close them | A `WITH CHECK` binds only roles RLS applies to, and provisioning runs as `postgres`. R2 F9: a request that bound its tenant before a concurrent teardown commits can still insert | R1 read `table_builder.py:403-410`; R3A: the residue sweep is catalog-driven | none | n/a | 3* | 2 | F1 | OPEN | STILL OPEN by design — stated in code, no register key ("the racing row is the designed residue class", g61 §8 F9); R3A "OPEN (verified)" | aaf847b0b13ef2655 P1-6; af78213934793d676 F9; ac7886cea2b69e7f5 |
| R1-07 | core | `tests/unit/db/test_tenant_cascade_census.py` (`AGREED_CASCADE`, `SURVIVING_RELATIONS`); `tests/db/rbac/test_tenant_teardown_db.py` (`CASCADING_RELATIONS`, `SURVIVING_RELATIONS`) | Keep four hand-kept literals of the cascade set, the permanently vacuous `_PARTITION_REMOVE_WARNING` half, and substring matching | The db copies make the pin measure the CLUSTER rather than agree with the registry by construction | reviewer counted 4 literals, zero hits for the warning half; a paraphrase defeats the match | the census tests | n/a | 3* | 1 | F3 | OPEN | STILL OPEN — recorded, not acted on (g61 §5d) | aaf847b0b13ef2655 P2; g61 §5d |
| R2-01 | core | `core/db/table_definitions.py` `get_comments_table_definition` (no `_TENANTS_FK`) | M-CASCADE mechanism: drop `_TENANTS_FK` from `comments`; the other eight stay | `SET NULL` is impossible (`tenant_id` NOT NULL, leads the PK); `RESTRICT` blocks deletes; core has no documents table | emitted DDL printed; `ALL_TABLES` has no document relation; votes FK only to `comments` | `test_tenant_cascade_census.py::test_the_cascade_set_is_the_one_a_human_last_agreed_to`, `::test_the_product_relations_survive…` | yes — R2 re-attach → 9 unit failures | — | 2 | F1 | SETTLED (DDL) | OWNER-OWED C1 (the live constraint drop, before core deploys) — code HOLDS | af78213934793d676 table; §4a-bis M-CASCADE |
| R2-02 | core | `scripts/rbac/drop_comments_tenants_fk.sql` | Look the constraint up in the catalog; refuse unless exactly one match; change no rows; run as the table owner, off-peak, before deploying | The constraint name may differ between databases | the test DB holds exactly one `comments→tenants` FK (`comments_tenant_id_fkey`); ACCESS EXCLUSIVE on `tenants` is correct (R1, R2) | text pins only (T-08) | the script has never run, by rule | — | 2 | F1 | OPEN (unrun) | OWNER-OWED C1 (C5 step 3). Until it runs, both doors answer 503 and the db lane shows the 2 G.61 reds | af78213934793d676 table; decision sheet C1 |
| R2-03 | core | `core/services/__init__.py:201`, `core/fastapi_app.py:265-267`, gate `tenant_service.py:331` @HEAD | Enforce the deploy order: refuse the teardown (503) while the catalog disagrees, and pin the boot wiring | `af6adce`'s "now enforced" was false: replacing the boot call with `pass` left unit 1457 / api 884 green | R2 mutation | `tests/unit/db/test_tenant_cascade_boot_check.py::test_the_boot_path_really_runs_the_check` (:425); `tests/api/tenancy/test_tenant_teardown.py::test_the_teardown_refuses_while_the_database_would_break_the_bodys_promise` (:562) | yes — R3A: route call → `pass` failed 9 api tests; the boot wiring is pinned | 1* | 0 | F1 | REFUTED ("enforced") | FIXED-AT `1e7d706` · reviewer-proved (R3A); the gate later moved into `delete_tenant` (R3A-01) | af78213934793d676 F1; CP25 add. 6 |
| R2-04 | core | `core/resources/tenants/tenant_endpoints.py` (`_residual_rows_notice(census)`) | Render the notice's casualty half from the census; drop "comments" from the confirmation message | Counting from a sentence is how the body came to lie | family grep over core and the `-obsm` siblings | `test_tenant_cascade_census.py::test_the_notice_follows_a_census_it_has_never_seen` (:275) | yes — R2 re-attach mutation | — | 0 | F1 | SETTLED | HOLDS | af78213934793d676 table |
| R2-05 | core | `core/resources/rbac/postgres_init.py` (`comments_sync_thumbs`); `drop_comments_tenants_fk.sql:114` @HEAD | Under the old schema a tenant with any vote could not be deleted (InsufficientPrivilege → 500): remove the path, do not widen the grant role | The trigger is not SECURITY DEFINER; `flynapse_grant` has no privilege on `comments` | R2 reproduced on PG 16.11 (precondition off); R1 read the grant set; R2 F12: on PG17+ AFTER triggers run as the queuing role | `tests/db/rbac/test_tenant_teardown_db.py::test_the_document_comments_and_their_votes_outlive_the_tenant` (errors until C1) | yes — R2 precondition-off run | — | 1 | F1 | SETTLED on PG16 | HOLDS; the PG17+ qualifier is stated in the script (`1e7d706`); no guard for the version dependence | af78213934793d676 table, F12; aaf847b0b13ef2655 |
| R2-06 | core | `scripts/backfill_chat_turn_facts.py` (`backfill()` → `upsert_facts`) | The driver goes through the 64-row chunking | `execute_many` straight from `backfill()` kept unit 1457 and db 5 green | R2 mutation | see R0a-01's guards | yes — R3A: bypass → both fail, live `[(64, True)]` | 2* | 0 | F2 | REFUTED (bypass green) | FIXED-AT `d59c44a` · reviewer-proved (R3A) | af78213934793d676 F3; ac7886cea2b69e7f5 |
| R2-07 | core | `scripts/backfill_chat_turn_facts.py` (module docstring; subxid comment) | Correct "one cursor with one commit"; a DECLINED row (`ON CONFLICT … WHERE false`) costs a subxid too, a refused row none | Stale prose; `heap_lock_tuple` assigns an xid | R2 (PLAUSIBLE-wrong); the implementer measured it | none | n/a | 3* | 1 | F3 | OPEN | FIXED (prose) at `d59c44a`; the declined/refused costs are the implementer's measurement, not reproduced (R3A: OPEN) | af78213934793d676 F4; ac7886cea2b69e7f5 |
| R2-08 | core | `core/resources/tenants/tenant_endpoints.py` (`_CONFIRM_MISMATCH`, `_PARTITION_REMOVE_WARNING`) | Render both owner-facing casualty lists from the census through a phrase table; guard completeness | Both omitted pending invitations, which a teardown deletes | R2 read the census | `test_tenant_cascade_census.py::test_every_relation_the_census_destroys_is_named_to_the_owner` (:349) | yes — R3A: invitations phrase dropped → fails | 1* | 0 | F1 | OPEN | FIXED-AT `1e7d706` · reviewer-proved (R3A) | af78213934793d676 F5 |
| R2-09 | core | `tests/db/rbac/test_tenant_teardown_db.py` (migration precondition + vote seed) | Scope the precondition and the vote seed to the survival case only | A fixture-wide precondition errored three unrelated cases (identity cascade, audit trail, tenant event) until C1 | R2: precondition + vote off → those 3 passed on the unmigrated DB | none (lane evidence) | n/a | 2* | 1 | F3 | OPEN | FIXED-AT `1e7d706` · reviewer-held (R3A lane run: the identity case passes unmigrated); no guard | af78213934793d676 F6; ac7886cea2b69e7f5 |
| R2-10 | core | `tenant_service.py:688` @HEAD (page rows drop `_PAGE_SORT_KEY`) | `list_tenants_page` returns the same tenant shape as `list_tenants` | Every dict carried `keyset_sort_key` | R2 probe | `tests/unit/db/test_tenant_keyset_page.py::test_a_page_returns_the_same_tenant_shape_as_the_offset_reader` (:372) | yes — R3A `if True` mutant | 1* | 0 | F2 | OPEN | FIXED-AT `1e7d706` · reviewer-proved (R3A) | af78213934793d676 F7 |
| R2-11 | core | `core/services/__init__.py:122` (`tenant_cascade_drift`), `core/db/table_definitions.py:1836` (`cascade_closure_over_edges`) @HEAD | Walk the closure transitively, one algorithm shared with the census; a realistic stub | The check saw direct children of `tenants` only; the stub posed a catalog Postgres never produces | R2 live probe: no deeper cascade today (PLAUSIBLE) | db `test_tenant_teardown_db.py::test_the_catalog_check_agrees_with_an_independent_recursive_reading` (:298) | partial — see R3A-02 | 2* | 1 | F1 | OPEN | FIXED-AT `1e7d706` · reviewer-held (R3A: ASSERTED, then its P2-1 → R3A-02: `803b46b`, `221dbf4`) | af78213934793d676 F8 |
| R2-12 | core | g61 §7 / master plan (log-pipe count) | The log-pipe `format_exc` scope is 51 sites in 8 files, not 13 | It sets the size of the owner's traceback question | R2 AST count; R3A recount at `d59c44a`: 51 in 8 | none | n/a | 3* | 1 | F3 | OPEN | FIXED (plan) — M-TRACEBACK ruled; every site converted at `fdccdae` (R3B-09); registers empty, then frozen (T-01) | af78213934793d676 F11; ac7886cea2b69e7f5 |
| R2-13 | core | `core/resources/automations/services/automation_store.py` (status constants); `core/resources/automations/sweep_span.py` | Stop typing `success`/`abandoned` (no producer writes them); add a drift pin against the producer; keep `traced_sweep` with a corrected reason | A mirrored vocabulary drifts silently | producer grep (completed/failed/awaiting_input/skipped) | `tests/unit/automations/test_run_status_vocabulary_drift_pin.py::test_every_status_core_mirrors_is_one_the_producer_writes` (:168) | yes — R2: `_STATUS_COMPLETED = "success"` fails on api and api-obsm | — | 0 | F2 | SETTLED | HOLDS | af78213934793d676 table; g61 §7 |
| R3A-01 | core | `core/resources/channel_provisioning/channel_provisioning_endpoints.py:253` (door), `:313-316` (backstop 503); `tenant_service.py:946` (`delete_tenant`) @HEAD | The cascade gate lives inside `TenantService.delete_tenant`; both doors ask first and answer 503 | `DELETE /channel-users` called `delete_tenant` with no gate — a live door (gateway exact-path arm; the telegram-bot client). The SQL header and plan §3 ("unavailable, not destructive") were false for it | R3A code read; no data at risk today (channel tenants hold no comments) | `tests/unit/db/test_tenant_service.py::test_a_delete_is_refused_under_the_lock_before_any_row_is_touched` (:1044); `tests/api/tenancy/test_channel_user_deprovisioning.py::test_the_door_refuses_while_the_database_would_break_the_teardowns_promise` (:628) | yes — R4A: m-gate-off 4F, m-door-off 5F | 1* | 0 | F1 | OPEN (P1) | FIXED-AT `802850c` · reviewer-proved (R4A); header and plan prose corrected | ac7886cea2b69e7f5 P1-1; Add. 30, 42 |
| R3A-02 | core | `tests/unit/db/test_tenant_cascade_boot_check.py:251`; `core/services/__init__.py:77-104` @HEAD | The catalog stub EVALUATES the query's predicates; relations are read as `pg_class` identities | Narrowing the query to `confrelid = 'public.tenants'::regclass` left all 13 unit tests green; the db test discriminates only while unmigrated | R3A mutation + a simulated migrated catalog | `::test_the_stub_catalog_applies_a_narrowing_predicate_rather_than_ignoring_it` (:251); db `::test_the_catalog_check_agrees_with_an_independent_recursive_reading` (:298) | R4A: m-oid unit green, db 2F; `::regclass::text` rendering is covered only by the db lane | 2* | 1 | F1 | PARTIAL | FIXED-AT `803b46b` (+ `221dbf4` identities) · reviewer-held (R4A, R5A); rendering still db-lane-only | ac7886cea2b69e7f5 P2-1; ae5833840feb585bf |
| R3A-03 | core | `core/db/stamps.py:1-33` | Scope `utc_stamp`'s "the one spelling" to the identity cluster | `users` (naive `isoformat`) and `user_operators` (`+00:00`) use other spellings; no ordering defect | R3A read | none (prose) | n/a | 3* | 1 | F3 | REFUTED (overclaim) | FIXED (prose) at `cb2d0d9` · R4A HELD | ac7886cea2b69e7f5 P2-3; ae5833840feb585bf |
| R3A-04 | core | `core/services/__init__.py:122` @HEAD | Refuse on drift in BOTH directions (a declared cascade the database lacks → INCOMPLETE) and never conflate schemas | Only `live − declared` was checked, so a missing cascade over-claims the deletion; `_bare` conflated same-named tables | R3A (PLAUSIBLE; the test DB has `public` only) | `test_tenant_cascade_boot_check.py::test_a_declared_cascade_this_database_lacks_is_the_other_half_of_the_drift` (:272), `::test_a_relation_in_another_schema_is_never_conflated_with_the_registrys` (:289) | yes — R4A: m-oneway 2F, m-bare 1F | 1* | 0 | F1 | OPEN | FIXED-AT `1d08786` (+ `221dbf4`, R4A-03) · reviewer-proved (R4A) | ac7886cea2b69e7f5 P2-4; ae5833840feb585bf |
| R3A-05 | core | `tenant_service.py:239-259` @HEAD (refusal sentences); `tenant_endpoints.py:101-116` | Teardown answers 503 on an undeclared live cascade; an unreadable catalog → 503 (fail closed) | Enforce the deploy order; "could not check" is not "checked and fine" | R3A: route call → `pass` failed 9 api tests; `if not undeclared` failed `[catalog unreadable]` | `test_tenant_teardown.py::test_the_teardown_refuses_while_the_database_would_break_the_bodys_promise` (:562) | yes (R3A) | — | 0 | F1 | SETTLED | HOLDS (refined: gate in `delete_tenant`; an odd row shape → UNVERIFIED 503 since `221dbf4`) | ac7886cea2b69e7f5 table |
| R3A-06 | core | `tenant_service.py:235-243` @HEAD; `test_tenant_teardown.py:611` | Read the catalog on every call (no cache); the 503 names no file, the log line does | A cached refusal outlives the migration; a cached agreement outlives a re-added cascade; a filename on the wire describes the server's layout | R3A read; implementer measured ~4.7 ms per call | `::test_the_cascade_check_is_read_on_every_teardown_not_cached` (:611); `test_tenant_service.py::test_the_gate_is_asked_on_every_delete_not_cached` (:1088) | no | — | 1 | F1 | ASSERTED | HOLDS. Spot-check: decision sheet C1 says the 503 "names the script"; it does not | ac7886cea2b69e7f5 table; g61 §8 F1b |
| R3A-07 | core | `core/db/stamps.py:36-38` | Fixed-width 27-character `utc_stamp` for the five identity writers | `Z` sorts after `.`, so a whole-second stamp sorted after the rest of its own second | controller finding, verified | `tests/unit/db/test_text_stamps_are_fixed_width.py::test_a_whole_second_keeps_its_fraction` (:59) + one case per writer; a db ordering case | yes — R3A: no `timespec` → 8 unit + 1 db failed | — | 0 | F2 | SETTLED | HOLDS | ac7886cea2b69e7f5 table; Add. 25 |
| R3A-08 | core | `tenant_service.py:212` @HEAD (`_KEYSET_SORT_KEY`) | Do not pad legacy fraction-less stamps; a total order suffices | Padding puts a regex into every page comparison to fix an order no caller sees | R3A: no cross-width reader in 4 repos | `tests/db/rbac/test_tenant_keyset_page_db.py::test_a_stored_fraction_less_stamp_sorts_late_in_its_second_and_is_still_read_once` (:237) | no | — | 1 | F2 | ASSERTED | HOLDS | ac7886cea2b69e7f5 table |
| R3A-09 | core | `tests/unit/db/test_tenant_keyset_page.py` (in-memory model) | The model applies every predicate to the count; `total` is asserted on every page | The old model never applied the cursor to the count, so no walk could see a count computed under the cursor | R3A mutation | `::test_the_true_count_rides_every_page` (:295) | yes — R3A: cursor into count → `[5,3,1,0]` / `[2,1,0]` | — | 0 | F2 | SETTLED | HOLDS | ac7886cea2b69e7f5 table; Add. 25 |
| R3A-10 | core | `core/services/__init__.py:122` @HEAD | A migrated cluster reads `[]`, so the gate does not block the positive case | A gate that never clears is an outage | R3A read-only probe over the real edges minus the comments FK → `[]` | stub-only unit test | no | — | 2 | F1 | ASSERTED | HOLDS by probe; provable live only after C1 | ac7886cea2b69e7f5 table |
| R3B-01 | core | `pdf_page_service.py:251,257,340,346` → `pdf_page_endpoints.py:142,215` (at `fdccdae`) | Storage failures answer typed 404 (missing) / 503 (other storage) / 500 (else), fixed text | S3 and driver text reached a 400 body: MinIO host + bucket + tenant key, an IAM ARN, the object key; server faults misreported as 400; the disclosure sweep exempted the module | R3B TestClient probe with stubbed S3 | `tests/api/documents/test_pdf_failure_bodies.py` | yes — R4B: 21 pass, 18 red at parent | 0* | 0 | F1 | OPEN (live leak) | FIXED-AT `2d5e136` · reviewer-proved (R4B) at request time; the streaming path stayed open → R4B-01 | a6c547ab2505f68e3 P1; Add. 32 |
| R3B-02 | core | `test_core_logs_carry_no_exception_text.py` (converted-module set) | Pin the converted module set by equality, not a `>=` floor of 30 | Stripping `failure_fields` from 4 modules kept the file 82/82 green | R3B M2 | the module-set pin in the same file | yes — R4B: `setup/` dropped from the sweep → caught by the equality pin | 1* | 0 | F1 | REFUTED ("clean cannot be reached by deletion") | FIXED-AT `1134f79` · reviewer-proved (R4B) | a6c547ab2505f68e3 P2-2; a25426e0233505143 |
| R3B-03 | core | `cognito_identities.py`, `tenant_claim_writer.py`, `turnstile.py`; dead `validate_pdf_access` | Constant messages with the cause chained by `from`; a raise rule flags caught text in a new exception's message | Text inside another exception's message was unguarded (M5: only the behavioural test turned red); no renderer today | R3B scan | the log guard's raise rule | yes — R4B: raise rule off → 3 red; each carrier red at parent | 2* | 0 | F1 | OPEN (latent) | FIXED-AT `425e3b7` (+ `2d5e136` deletes `validate_pdf_access`) · reviewer-proved (R4B). R4B: a chained cause still printed through the stdout sink → R4B-02 | a6c547ab2505f68e3 P2-5; a25426e0233505143 |
| R3B-04 | core | `role_endpoints.py:264,329`, anonymous `user_endpoints.py:979`, `tenant_endpoints.py:500`, `operator_endpoints.py:426,471,552` (at `fdccdae`) | `except ValueError: detail=str(e)` must not echo a pydantic `ValidationError` (`input_value=`) | `ValidationError` is a `ValueError` subclass | R3B (PLAUSIBLE; subclassing verified) | router sweep injects a real `ValidationError` | R4B: `refused` sends it to 500 — but echoes other ValueErrors (R4B-03) | 0* | 1 | F1 | OPEN | FIXED-AT `2d5e136` · reviewer-proved (R4B: a real `ValidationError` now goes to 500); the echo of other ValueErrors was closed by the `Refusal` type (R4B-03) | a6c547ab2505f68e3 P2-6 |
| R3B-05 | core | `invitation_endpoints.py`, `invitation_dispatcher.py`, `user_service.py`, the Turnstile path | Converted failure lines carry the ids they can safely name (`tenant_id`, a new required `invitation_id`, `user_id`); the Turnstile cause type is logged at source | The conversion had dropped identifiers operators need | R3B read | invitation email and endpoint tests | yes — R4B: 7 red at parent; both callers pass `invitation_id` | 2* | 0 | F1 | OPEN | FIXED-AT `11d8854` (+ `425e3b7`) · reviewer-proved (R4B) | a6c547ab2505f68e3 P2-7; a25426e0233505143 |
| R3B-06 | core | `core/resources/http_errors.py:122` @HEAD; `role_endpoints.py:380` | Correct "every caller is an `except` block" and "logs an empty trace" | `role_endpoints.py:382` calls it outside one (correctly logging context without error fields) | R3B scan | none (prose) | n/a | 3* | 1 | F3 | REFUTED | FIXED (prose) at `2d5e136` — `:122` @HEAD: "Nearly every caller is an `except` block. One is not —" | a6c547ab2505f68e3 P2-8 |
| R3B-07 | core | `setup/dynamodb/*.py` | Sweep `setup/` with all three log guards and convert its sites | Three owner-run scripts wrote exception text (`f"…{e}"`, `traceback.print_exc()`) outside `SWEPT_ROOTS` | R3B scan (said 11; the sweep counts 9 — R4B-05) | the log guards; the swept-roots pin | yes — R4B: 9 sites red at parent; `setup/` dropped → caught | 2* | 0 | F1 | OPEN | FIXED-AT `07d7bbe` · reviewer-proved (R4B) | a6c547ab2505f68e3 P2-9; a25426e0233505143 |
| R3B-08 | core | `core/resources/document_viewer/document_endpoints.py` (404 branch) | Choose the 404 by a `not_found` flag with fixed text; remove the ValueError → 400 branch | A service sentence containing "not found" passed through (it named the table); the 400 branch caught only server faults | R3B (PLAUSIBLE); the implementer found the 400 branch wider than reported | `tests/api/documents/test_document_failure_bodies.py` | yes — R4B (VERIFIED, red at parent) | 2* | 0 | F1 | OPEN | FIXED-AT `2d5e136` · reviewer-proved (R4B) | a6c547ab2505f68e3 P2-10; a25426e0233505143 table |
| R3B-09 | core | 118 converted log sites (`fdccdae`) | A constant message + `**failure_fields(exc)` (type and frames, never the message) | M-TRACEBACK | R3B: no keyword collisions, argument always the handler's own name, no braces, no stdlib logger; about 25 read by hand | log sweep, format-string guard, logger-binding guard | yes — R3B M1 red | — | 0 | F1 | SETTLED | HOLDS | a6c547ab2505f68e3 table |
| R3B-10 | core | `core/resources/http_errors.py:109` @HEAD (`internal_error`) | The shared 500 funnel logs `failure_fields(sys.exception())`; its callers stop feeding it text | The funnel rendered `format_exc` for about 55 callers | R3B: 55 sites in 13 modules scanned | `tests/unit/observability/test_internal_error_logs_no_exception_text.py` + the log sweep | yes — R3B M4: 2 red | — | 0 | F1 | SETTLED | HOLDS | a6c547ab2505f68e3 table |
| R3B-11 | core | `comment_service.py` (six wraps) | `CommentDatabaseError` carries a constant; the driver error chains with `from` | The traceback was the exception's message | R3B: nothing estate-wide reads its message | behavioural test + (since `425e3b7`) the raise rule | R3B M5: behavioural red, sweep green; R4B: raise rule off → 3 red | — | 0 | F1 | PARTIAL (sweep blind) | HOLDS — both guards now bite | a6c547ab2505f68e3 table; a25426e0233505143 |
| R3B-12 | core | `document_service.py:222-236`; `document_endpoints.py:213-219,276-282` (at `fdccdae`) | A failed document read returns a constant; both catalog routes answer a fixed 500 | psycopg2 text reached a 500 body | R3B read | `tests/api/documents/test_document_failure_bodies.py` | no reviewer mutation of this change (R3B read it; R4B mutated the neighbouring 404 change, R3B-08) | — | 1 | F1 | ASSERTED (R3B) | HOLDS | a6c547ab2505f68e3 table; a25426e0233505143 table |
| R4A-01 | core | `tenant_service.py:291` (`MintReceipt`), `:720` (`mint_tenant`), `:1003-1023` (inline redeem) @HEAD | The one way past the cascade gate is a sealed, tenant-bound, single-use receipt from `mint_tenant`, not a boolean | `delete_tenant(…, **{"minted_in_this_request": True})` passed the AST guard (m-splat, 52 passed); callers of `_unmint_*` were unpinned; `scripts/` and `setup/` unscanned | R4A m-splat | `test_tenant_service.py::test_the_old_flag_is_not_a_way_past_the_gate` (:1115), `::test_a_receipt_cannot_be_built_copied_or_conjured` (:1129), `::test_a_receipt_deletes_only_the_tenant_it_was_issued_for_and_only_once` (:1146) | yes — R5A forgery probe: copy, deepcopy, pickle, `object.__new__`, real seal, other-tenant receipt, a 32-thread redeem (1 ok, 31 TypeError) | 0 | 2 | F1 | REFUTED (shape-only guard) | FIXED-AT `04f7d4d` · reviewer-proved (R5A); the guard around the type → R5A-01 | ae5833840feb585bf P2#2; af2708fc9edbb7d7a |
| R4A-02 | core | `core/services/__init__.py:77-104` @HEAD (`pg_class`/`pg_namespace`); every reader on the grant pool | Read relations as `(nspname, relname)`, walked from the `tenants` that `'tenants'::regclass` names on the GRANT cursor | `regclass::text` renders bare when a schema ahead of `public` holds the name: an `other.comments` or a `"$user"` schema → spurious refusals, and the fail-open half could mask a missing `public.tenant_invitations` FK. The catalog was read on the app pool while the DELETE ran on the grant pool | R4A emulated catalogs (5 other shapes answered right) | `test_tenant_cascade_boot_check.py::test_a_relation_in_another_schema_is_never_conflated_with_the_registrys` (:289); db `test_tenant_teardown_db.py::test_the_check_reads_the_real_catalog_on_the_locked_grant_cursor` (:326) | R5A: db lane MISMATCH on `flynapse_grant` — a behavioural pass, not a mutation | 1 | 2 | F1 | PARTIAL | FIXED-AT `221dbf4` · reviewer-held (R5A) | ae5833840feb585bf P2#3; af2708fc9edbb7d7a |
| R4A-03 | core | `tenant_service.py:1030-1037` @HEAD | `LOCK TABLE tenants IN ROW EXCLUSIVE MODE` → catalog read → DELETE in one grant-cursor transaction; a refusal rolls back; odd shapes → UNVERIFIED 503 | The check and the DELETE were separate transactions, so an `ADD FOREIGN KEY … CASCADE` committed between them would cascade; an odd row shape raised `KeyError` → 500 | R4A (needs concurrent owner DDL) | `test_tenant_service.py::test_a_delete_is_refused_under_the_lock_before_any_row_is_touched` (:1044); db `::test_delete_tenant_itself_asks_this_catalog_before_it_deletes` (:779) | R5A: lock matrix (conflicts with SHARE ROW EXCLUSIVE and ACCESS EXCLUSIVE), privilege (`flynapse_grant` has DELETE), no new deadlock path, fail closed; db PASSED — no mutation | 0 | 2 | F1 | OPEN | FIXED-AT `221dbf4` · reviewer-held (R5A). Residual (keys deeper than `tenants`) → IMP-06 | ae5833840feb585bf P2#4; af2708fc9edbb7d7a |
| R4A-04 | core | `core/resources/cognito_spans.py:31`, `cognito_identities.py:31` (at `ba86d85`); `pyproject.toml:43` | Import `aws_span` / `finish_dependency_span` from `utils.observability.dependency_spans` | G.48 core half | only `utils-obsm` (`e6005bd`, unpublished, still `0.1.39`) has them; against any older utils the channel-provisioning and invitation imports — so app assembly — fail | none | n/a | 1 | 1 | F3 | OPEN | OWNER-OWED — recorded as a deploy prerequisite (`4803f70`, g61 §13); ordered by M-VERSIONS (flynapse-otel → utils `0.2.0` → core); executed in C5 / Phase H | ae5833840feb585bf P2#7; af2708fc9edbb7d7a (A-7 HELD); §4a-bis M-VERSIONS |
| R4A-05 | core | `tests/unit/infra/test_root_anchoring.py` | The G.89 checkout census counts a `<base>` / `<base>-*` directory only when it holds `pyproject.toml` | A marker-less `core-*` directory (a worktree mid-add, a leftover) hard-failed the census | R4A: 1 failed on a posed marker-less directory | the posed `<repo>-review-notes` case | R5A: HELD (green; parent tests pass) — no mutation | 2 | 1 | F3 | OPEN | FIXED-AT `16af5c0` · reviewer-held (R5A) | ae5833840feb585bf P2#8; af2708fc9edbb7d7a |
| R4A-06 | core | `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` (script sweep) | A literal names a checkout when a path segment is a workspace directory and it builds a path: operands of `/`, `+`, `%`; `join`; `Path`-family; f-strings; `.format`; names bound to such literals; `with_name`/`with_stem`; starred and folded literals; dict constants; environment defaults | R4A: `Path(WORKSPACE, "utils")`, a bare `join`, an f-string, `+`, `Path("../utils")` and a constant all returned `[]`. R5A P2-6: `REPO_ROOT.with_name("utils")` → 112 green; starred literals, dict constants, env defaults | R4A, R5A plants | the sweep's pinned cases | `ddb30a5`: R5A defeated it. `0990e73`: implementer only (6/6 red); in R6's range with no R6 finding | 2 | 1 | F3 | REFUTED (R4A, R5A) | FIXED-AT `0990e73` · implementer-proved only. Declared uncatchable: run-time names, constants on attributes or imported, `getattr`/`partial` | ae5833840feb585bf P2#9; af2708fc9edbb7d7a P2-6 |
| R4A-07 | core | `tenant_service.py:946` (`delete_tenant`), `:239-259` @HEAD | The gate inside `delete_tenant` is read before any row: unreadable → UNVERIFIED 503, empty catalog → INCOMPLETE 503, mismatch → MISMATCH 503 | A backstop no door can skip | R4A: unit refusal ×3 + a db backstop against the real catalog; R5A: the db case gets MISMATCH, not UNVERIFIED | `test_tenant_service.py::test_a_delete_is_refused_under_the_lock_before_any_row_is_touched` (:1044); `test_tenant_teardown.py::test_the_services_backstop_is_answered_as_the_same_503` (:598) | yes — R4A m-gate-off 4F, m-door-off 5F | — | 0 | F1 | SETTLED | HOLDS | ae5833840feb585bf table; af2708fc9edbb7d7a |
| R4A-08 | core | `core/resources/cognito_spans.py` + 5 call sites | Every Cognito call exports an INTERNAL `aws_span` `cognito.<op>` carrying class and AWS code only; a replayed create is an answer, not a failure; behaviour unchanged | G.48 core half: Cognito calls were anonymous in traces | R4A on live spans (a private provider, no scrubber): `to_json` swept for pool, username, email, password, subject, ARN, account | `tests/unit/observability/test_cognito_spans.py::test_a_refused_call_is_an_error_span_with_its_class_and_code_and_no_words` (:171), `::test_the_replay_path_is_an_answer_not_a_failure` (:154) | yes — R4A m-span-off 3F | — | 0 | F1 | SETTLED | HOLDS | ae5833840feb585bf table; Add. 42 |
| R4B-01 | core | `core/resources/document_viewer/services/pdf_page_service.py:75` @HEAD (`stream_body`; was the inline generator at `:267`) | A failed read or close while `/pdf/stream` is SENDING logs the constant "Document stream interrupted" with type and frames and ENDS the stream; every generator, `StreamingResponse` and background site in `core/` is pinned by equality | The generator ran after the route returned, with try/finally and no except: an S3 `ReadTimeoutError` escaped every core handler, Starlette's `ServerErrorMiddleware` re-raised after api's handler, and utils' stdout JSON sink wrote `…flynapse-private.s3…/tenants/t-secret/manual-X.pdf`. The B-P1 claim "anything else reaches the 500 funnel" was false for this path | R4B replay through `log_bridge.install(json_stdout=True)` + intercept | `tests/api/documents/test_pdf_stream_interruption.py`; `tests/unit/observability/test_core_response_bodies_catch_their_failures.py::test_the_population_of_code_that_can_run_after_a_route_is_pinned` (:256) | yes — R5B: unguarded read → 3 RED; close-after-full-stream, first-read failure and `GeneratorExit` probes held | 0 | 0 | F1 | OPEN (P1) | FIXED-AT `bdaea7b` + `c4b0e77` · reviewer-proved (R5B) | a25426e0233505143 F1; a077df0019eb861ca table; Add. 46, 68, 73 |
| R4B-02 | utils | `utils/observability/log_bridge.py:139-143` (at the time) | (cross-lane) The stdout JSON sink writes the full `format_exception`, causes included, for every record with `exc_info` | Every exception escaping to uvicorn in api leaks this way; `raise X("const") from exc` still prints the cause; G.112 withheld only at the OTLP provider | R4B replay | none in core | n/a | 0 | 2 | F1 | OPEN | Routed to utils as G.115 (Add. 46). The plan's G.115 entry says BUILT at utils `0211f9b`, unreviewed, box still `[ ]` — utils slice, not verified here | a25426e0233505143 F1; plan G.115 |
| R4B-03 | core | `core/exceptions/exceptions.py:145` (`class Refusal(ValueError)`), `core/resources/http_errors.py:146` (`refused`) @HEAD | A TYPE: `refused` echoes a `Refusal` only; every other `ValueError` goes to `internal_error` (fixed 500, type and frames logged) | `refused` echoed any non-pydantic ValueError. Anonymous `POST /users` with a stored tenant id `"legacy tenant.acme"` answered 400 quoting it (`TenancyBindingError`); utils documents that class and four more as code defects | R4B probes P-A, P-B | `tests/api/tenancy/test_refusal_is_the_only_echoed_value_error.py` (8 diverted classes → 500) | R5B: HOLDS, "n/a (type)" — no reviewer mutation | 0 | 1 | F1 | PARTIAL | FIXED-AT `9532a15` · reviewer-held (R5B). The census of constructions is T-05 | a25426e0233505143 F2; a077df0019eb861ca table |
| R4B-04 | core | `pdf_page_service.py:272-280` @HEAD | No `X-S3-Key` / `X-Bucket-Name` headers; no `s3_key` / `bucket_name` in the download-url body; `Cache-Control: private` on tenant file bytes | The dashboard stream proxy (`app/api/documents/[id]/stream/route.ts:78`) forwards every backend header to the browser; the module's own rule is "the caller names a document, never an object"; `public, max-age=3600` sat on authenticated bytes | R4B read; low severity (the presigned URL names the same bucket and key to the same caller); no dashboard reader | `tests/api/documents/test_pdf_wire_names_no_storage_layout.py` | yes — R5B: header re-added → RED | 2* | 0 | F1 | OPEN | FIXED-AT `1d7238d` · reviewer-proved (R5B) on the wire; the logs stayed open → T-06 | a25426e0233505143 F8; a077df0019eb861ca |
| R4B-05 | core | `test_core_logs_carry_no_exception_text.py:89` (at `ba86d85`); `07d7bbe` subject | "Eleven" `setup/` sites → the measured nine | The guard at the parent flags 9 | R4B count | none (prose) | n/a | 3* | 1 | F3 | REFUTED | FIXED (prose) at `552a5ad` | a25426e0233505143 F9 |
| R4B-06 | core | `core/resources/user/user_endpoints.py`, `core/resources/user/services/user_service.py`, `core/resources/invitations/services/invitation_service.py`, `…/invitation_dispatcher.py`, `scripts/backfill_chat_turn_facts.py` — 11 sites (`4040a82`; g61 §16) | Log people by `user_id` / `tenant_id` / `invitation_id`, never an address or a contact record (M-PII-IDS) | R4B F10: an email in an f-string INFO line on anonymous `POST /users`, `create_user email=`, a tenant's whole contact JSON on a parse failure — outside M-TRACEBACK | R4B read; the implementer confirmed the contact-JSON dump. Kept with a reason: `setup/dynamodb/get_users_data.py`. Judged not personal: `<channel>-<id>@channel-users.invalid` | `tests/unit/observability/test_core_logs_name_people_by_id.py::test_no_core_log_line_carries_an_address_or_a_contact_record` (:276), `::test_the_converted_lines_name_people_by_their_ids` (:341), `::test_an_unparseable_contact_is_logged_by_its_tenant_not_its_contents` (:428) | implementer only (10 mutants) | 0* | 2 | F1 | OPEN (owner) | FIXED-AT `4040a82` + `871c0f2` · implementer-proved only. `4040a82` left a db-lane case red for 5 commits, fixed forward (g61 §16 slip) | a25426e0233505143 F10; §4a-bis M-PII-IDS; g61 §16; Add. 95 |
| G44-01 | core | `core/resources/automations/services/automation_store.py:1108-1111` @HEAD | Serialise `params` and `operator_ids` BEFORE opening the send span | `json.dumps` inside `with send_span` exported an error span (`TypeError`) for an INSERT that never ran, against the docstring's promise | G44 probe (a `datetime` param) | `tests/unit/observability/test_automation_queue_send_span.py::test_a_refused_argument_opens_no_span[unserialisable-params]` (:333) | implementer only; in R5A's range with no finding | 2 | 1 | F2 | REFUTED (docstring promise) | FIXED-AT `4c4bf6b` · implementer-proved only; the assembler read the order at HEAD | a692e04365c9121c6 F1; Add. 49, 52 |
| G44-02 | core (+ copilot-mro) | `core/resources/automations/queue_span.py:57-58` (at `563a819`) | Say truthfully who logs a failed enqueue | "Every caller logs through `failure_fields`" was false: copilot-mro `data_discovery/jobs.py:191-194` (`opt(exception=True)` + f`{exc}`) and `document_hub/jobs.py:172-177` (`error=str(exc)`) log exception text, an older leak | G44 read | none | n/a | 2 | 1 | F3 | REFUTED | FIXED (prose) at `4c4bf6b`; the two copilot-mro sites were routed to the copilot-mro lane (N2 slice, not verified here) | a692e04365c9121c6 F2 |
| G44-03 | workspace docs | `docs/plans/observability-coverage-matrix.md:41,326` | Record the producer span | §D said "no producer span" | G44 read | none | n/a | 2 | 1 | F3 | OPEN | FIXED (plan) by the controller (Add. 76; docs uncommitted): the matrix shows `automation.queue.send` PRODUCER 2/2. It still calls the link inert, which `7c506e6` + api `6ae9701` have since changed in code (C9 pending) | a692e04365c9121c6 F3; Add. 76 |
| G44-04 | core | `tenant_service.py:667-698` @HEAD (`registry` count CTE LEFT JOIN keyset `page` CTE) | Page and count in ONE statement, one snapshot | A tenant deleted between the final call's count and its page made a complete walk refuse (`TenantRegistryTruncated`), and the boot reconcile reconciled nothing | G44 probe (rows a, b, c; page 2); the offset walk had the same race | `tests/db/rbac/test_tenant_keyset_page_db.py` (the empty last page still carries the true count) | yes — R5A: LEFT→INNER JOIN keeps 63 unit tests green, fails the db case | 2 | 0 | F2 | REFUTED ("the final count has forgotten") | FIXED-AT `d8d8325` · reviewer-proved (R5A, db lane only) | a692e04365c9121c6 F4; af2708fc9edbb7d7a; Add. 52 |
| G44-05 | core, api | `tenant_service.py:329-331` (at `eac494d`); api `tests/unit/infra/test_paged_registry_reads_state_their_limit.py:24,89-91,460,471` | Stop saying core pages by offset, or that paging callers depend on `list_tenants`' default | Both false after `eac494d` | G44 read | none | n/a | 2 | 1 | F3 | OPEN | core half FIXED (prose) at `d8d8325` (F5b); api half routed to the api lane (N4 slice) | a692e04365c9121c6 F5; Add. 52 |
| G44-06 | core | `automation_store.py:77` (module import of `queue_span`) | Import `queue_span` as a module so the tenancy-contract guard's `__wrapped__` scan keeps an exact set | A decorator would hide the function from the scan | G44: it hides nothing; if it fails, it fails loudly | `tests/unit/automations/test_store_tenancy_contract.py::test_the_named_set_is_the_set_that_actually_carries_the_marker` (:85) | no | 2 | 1 | F2 | ASSERTED | HOLDS. The lasting fix — a dedicated marker attribute instead of `__wrapped__` (G44 I2) — is STILL OPEN and is not recorded in the g61 plan or the master plan | a692e04365c9121c6 table, I2 |
| G44-07 | copilot-mro (core reader) | `tenant_service.py:560` @HEAD (`list_tenants` still defined) | Keep the offset reader for its remaining callers | Its only callers are copilot-mro: `ad_notification_dispatcher.py:1201` (a hand-written offset walk keeping page 1's total) and `scripts/ad/seed_ad_notification_subscription.py:84` (oldest row only; fine) | G44 I4; Add. 8 | none for the copilot-mro walk | n/a | 3* | 1 | F3 | OPEN | STILL OPEN — queued in the copilot-mro lane (Add. 8; N2 slice) | a692e04365c9121c6 I4; Add. 8 |
| G44-08 | core | `core/resources/automations/queue_span.py:144-145` @HEAD | `record_exception=False`, `set_status_on_exception=False`; the class name and a bare ERROR, no description | SDK defaults export the message | a real `psycopg2.IntegrityError` / `UniqueViolation` with `DETAIL: Key (…)=(tnt-SECRET-42,…)` through both producers — live and exported spans carry only `error.type`; a real RLS `InsufficientPrivilege` → the class name | `test_automation_queue_send_span.py::test_a_failed_insert_carries_its_class_and_not_one_character_of_its_message` (:297) | yes — G44 PM1–PM3 | — | 0 | F1 | SETTLED | HOLDS | a692e04365c9121c6 table |
| G44-09 | core | `queue_span.py:112-127` (at `563a819`) | `automation.queue.send` (PRODUCER) carries the consumer's vocabulary (`messaging.*`, `automation.trigger/kind/id/scheduled_for`) and identity `tenant.id` + `enduser.id` | Producer/consumer parity; `enduser.id` is the surrogate `users.user_id`, not an email | G44 diffed against api `queue_telemetry.py:273-289` and `run_span.py:39-46`; `scheduled_for`'s isoformat equals the DB value on real PG | dict-equality tests in `test_automation_queue_send_span.py` | no (reasoned) | — | 2 | F1 | ASSERTED | HOLDS | a692e04365c9121c6 table |
| G44-10 | core | `automation_store.py:858` @HEAD (`claim_run` send span) | A lost claim is `claim.outcome=lost` with outcome ok — arbitration is not an error | Error-rate panels must not count a lost race | a real 8-thread PG race: 1 won (a real row id), 7 lost, all trace roots | won/lost tests | no | — | 2 | F1 | ASSERTED | HOLDS | a692e04365c9121c6 table |
| G44-11 | core | `tenant_service.py:432-470` @HEAD (`iter_all_tenants`) | The walk ends on an empty page or `next=None`, never a short page; a repeated cursor raises; check against the FINAL count; a vanishing count refuses | Readers that clamp the limit; a reader that ignores `after`; deletes mid-walk | G44 adversarial sequences over the real reader | enumeration, ignores-cursor, final-count and vanishing tests (`tests/unit/db`) | yes — G44 KM1 (6 red), KM2, KM3 (3 red), KM4 | — | 0 | F2 | SETTLED | HOLDS (a one-page registry now costs 2 calls) | a692e04365c9121c6 table; Add. 43 |
| G44-12 | core | `tests/unit/infra/test_paged_registry_reads_state_their_limit.py` (core's copy) | `list_tenants_page` only at its defining site; `list_tenants` has no allowed production caller in `core/` or `scripts/` (Rule B) | Keep offset walks from coming back | G44 | the file | yes — GM1, GM2 red | — | 0 | F2 | SETTLED | HOLDS | a692e04365c9121c6 table |
| R5A-01 | core | `tests/unit/db/test_tenant_service.py:1209` @HEAD | Nothing outside `tenant_service.py` names the seal, the registry or `_redeem_receipt` — over `core/`, `scripts/`, `setup/`, string spellings included; the receipt is redeemed inline | A `scripts/force_teardown.py` importing `_issue_receipt` deleted with 0 gate calls (2401 green); `vars(ts)["_issue_receipt"]`, `getattr(ts, "_issue"+"_receipt")`, and a patched `_redeem_receipt` + `mint_receipt=True` all bypassed | R5A probes against the real module | `::test_nothing_outside_the_tenant_service_touches_the_receipt_registry` (:1209), `::test_every_spelling_of_a_receipt_private_is_seen` (:1405), `::test_a_patched_redeemer_is_not_a_way_past_the_gate` (:1411) | yes — R6 m5 RED 1 | 1 | 0 | F1 | REFUTED (guard scope) | FIXED-AT `457cbd6` · reviewer-proved (R6). Declared residue: run-time names, `importlib`, a test's monkeypatch | af2708fc9edbb7d7a P2-1; ab7273142e8ff7e86 |
| R5A-02 | core | merge `3f1a588` (`obs-merge-g44` → `obs-merge`) | Record the bisect hole; do not rewrite history | `3f1a588` is red at its own SHA: `test_the_population_of_code_that_can_run_after_a_route_is_pinned` fails until `c4b0e77` classifies g44's `send_span` | R5A: `--cc` and the remerge diff are empty; 1 unit failure | none | measured | 3 | 1 | F2 | OPEN | ACCEPTED-AS-DEBT — no register key; the bisect note is in g61 §15 (`git bisect skip` it); no history rewrite, by rule | af2708fc9edbb7d7a P2-3; g61 §15 (`aaf9069`) |
| R5A-03 | core | `scripts/run_db_lane.py:305-324` @HEAD | No `--password` on the migration child's argv; the password rides the child's environment | Any local user reads an argv through `ps` / `/proc/<pid>/cmdline` (utils r3 audit, Add. 66) | R5A verified the premise: copilot-mro-obsm `migrate_tenancy_schema.py:3843` defaults `--password` to `POSTGRES_PASSWORD`; the migration never prints `args` | `tests/unit/db/test_run_db_lane_credentials.py` | yes — R5A: red on parent source | — | 0 | F1 | SETTLED | HOLDS | af2708fc9edbb7d7a table; Add. 66, 68 |
| R5B-01 | core | `core/resources/http_errors.py:192` @HEAD (`response_validation_failed`); `core/fastapi_app.py:170`; `test_core_response_bodies_catch_their_failures.py:256` | A core handler for `ResponseValidationError`: a fixed 500 that logs type, frames and the route TEMPLATE. The stream census resolves `StreamingResponse` / `FileResponse` through aliases and pins what each site streams | On a model mismatch it escaped every core `try` with the failing field's `input` (48 `response_model` routes); `iter(lambda: body.read(n), b"")` or an aliased `StreamingResponse` passed the census | R5B probe on fastapi 0.118.2; R6: the core app is mounted in api (`main.py:480`), so its handlers apply | `::test_the_population_of_code_that_can_run_after_a_route_is_pinned` (:256) | yes — R6 m7 RED 2 (census); the handler: R6 read + existing test, no reviewer mutation | 0 | 1 | F1 | OPEN | FIXED-AT `3513dfa` · reviewer-proved (R6) for the census; the handler reviewer-held | a077df0019eb861ca P2-5; ab7273142e8ff7e86 |
| R5B-02 | core | `core/resources/document_viewer/document_endpoints.py:79-170` @HEAD | `GET /documents/document` drops every pointer field still holding a string, and any `s3://` or AWS-host url at any depth | It returned the catalog `url` (bucket + key) and the S3 pointer fields; `CORE.DOCUMENT` has no dashboard consumer | R5B read; the implementer re-verified no consumer | `tests/api/documents/test_document_answer_names_no_storage_location.py` | yes — R6 m3 RED 2 | 0 | 1 | F1 | OPEN | FIXED-AT `4c1e825` · reviewer-proved (R6) "as stated"; the survivors below the top level are R6-03 (`60acad9`) | a077df0019eb861ca P2-6; ab7273142e8ff7e86 |
| R5B-03 | core | `core/resources/user/user_endpoints.py` (anonymous `POST /users`); `SIGNUP_NOT_COMPLETED` at `core/resources/user/services/user_service.py:102` @HEAD | The anonymous door answers an existing address with `SIGNUP_NOT_COMPLETED`, the constant the domain refusal uses; trusted callers keep the specific sentence | "User with email X already exists in this tenant" was an account-existence oracle | R5B read; the domain arm already refused a fixed sentence | `tests/api/tenancy/test_signup_answers_no_account_existence.py::test_the_two_refusals_are_byte_identical` (:125), `::test_an_existing_address_is_told_nothing_about_its_account` (:112), `::test_an_authenticated_caller_keeps_the_specific_sentence` (:138) | implementer only (2 mutants; status, body and every header byte-identical) | 0* | 2 | F1 | OPEN (owner) | FIXED-AT `0607160` · implementer-proved only. Residuals listed, not fixed (g61 §16): timing (1–2 DB round trips, only in the tenant-create race); a new address still answers 201 | a077df0019eb861ca P2-8; §4a-bis M-SIGNUP-ORACLE; g61 §16 |
| R5B-04 | core | `core/resources/comments/exceptions/comment_exceptions.py:36,51,67` @HEAD | `CommentNotFoundError`, `CommentValidationError`, `CommentPermissionError` are `Refusal`s | The structural sweep found `handle_comment_exception` echoing them; their messages name only the caller's comment id or own user id, or are fixed | R5B audited every raise site | the refusal-class census (T-05) | no (n/a) | — | 1 | F1 | ASSERTED | HOLDS | a077df0019eb861ca table; g61 §14 B-F4 |
| R6-01 | core | `tenant_service.py:1003-1012` (comment), `:265` (`LOCK_TENANTS_FOR_TEARDOWN`), `:331` (gate) @HEAD | Nothing outside `tenant_service` rebinds the gate or its lock; `DELETE FROM tenants` / `TRUNCATE` has one site (`.py` and `.sql`); the comment names which tests pin what | m6: `setattr(ts, "require_the_cascade_the_"+"notice_describes", lambda cursor=None: None)`, an overwritten lock and a raw `DELETE FROM tenants` from `scripts/zz.py` → 450 passed; the comment "the spellings are pinned" was false. Worse than A2-P2-1: no receipt needed | R6 m6 | `test_tenant_service.py::test_nothing_outside_the_tenant_service_rebinds_the_gate_or_its_lock` (:1255), `::test_the_gate_and_its_lock_are_each_bound_once_in_their_module` (:1273), `::test_delete_from_tenants_is_issued_at_one_site` (:1330), `::test_every_spelling_of_a_gate_rebinding_is_seen` (:1366) | implementer only (both m6 plants + a `scripts/` raw DELETE RED) | 0 | 2 | F1 | REFUTED | FIXED-AT `9188794` · implementer-proved only. Declared: run-time names, `importlib`, a test's monkeypatch | ab7273142e8ff7e86 F2; Add. 95 |
| R6-02 | workspace plan | master plan §2.2 step 4 (`observability-telemetry-merge-and-completion.md:92-98`) | List `automation_runs.traceparent` as the fifth schema change, with its deploy consequence | `7c506e6`'s dependency was recorded only in core's plan and the commit; the master plan said "Four schema changes" and G.68 "No migration was written" | R6: if the migration runs late, the API serves on (`fastapi_app.py:282`), every `enqueue_one_shot_run` fails `UndefinedColumn` (DocHub upload and cleanup, data discovery), and api's worker refuses to boot (`worker.py:243`), stopping all automations | none (plan text) | n/a | 1 | 2 | F1 | OPEN | FIXED (plan) by the controller (Add. 95; docs working tree, uncommitted) — the assembler read "Five schema changes … `automation_runs.traceparent` … owner item C9". The column itself: OWNER-OWED C9 | ab7273142e8ff7e86 F6; Add. 95 |
| R6-03 | core | `core/resources/document_viewer/document_endpoints.py:79-170` @HEAD (`_AWS_HOST_SUFFIXES` `:82`, `LOCATION_WITHHELD` `:93`, `_is_storage_location` `:104`, `document_answer` `:157`) | Inside a pointer field, at any depth, every absolute URI is a location; storage hosts include `.amazonaws.com.cn` and the configured `AWS_S3_ENDPOINT_URL` host; a location inside text is redacted in place; a location used as a dict key drops the entry; the remaining limit is stated and pinned | R6 F10: `4c1e825`'s rule applied only at the top level — MinIO / non-AWS urls inside `references`, `.amazonaws.com.cn` hosts, `s3://` inside text and `s3://` dict keys survived | R6 probes | `tests/api/documents/test_document_answer_names_no_storage_location.py::test_no_location_survives_below_the_top_level` (:159), `::test_what_counts_as_a_storage_location` (:112), `::test_the_stated_limit_an_unconfigured_compatible_host_outside_a_pointer_passes` (:176) | implementer only (5 mutants) | 1 | 1 | F1 | PARTIAL ("literally true; applies only at the top level") | FIXED-AT `60acad9` · implementer-proved only. Declared and pinned limit: outside the pointer fields, a url on an S3-compatible host that is not the configured endpoint is not recognisable by its shape | ab7273142e8ff7e86 F10; g61 §17 |
| R6-04 | core | `tests/db/automations/test_automation_tables.py:311-315,384` @HEAD | `EXPECTED_COLUMNS["automation_runs"]` includes `traceparent`, so the column-set red is the live-migration gate; a nullability/default shape test like `queue_seconds`' | The test failed on its DDL-vs-expectation half and would have stayed red after C9 | R6 m8: the failure moves to the live-columns check at :344 | `::test_traceparent_is_nullable_text_with_no_default` (:384) | implementer only | 1 | 1 | F3 | PARTIAL ("19 migration-gated") | FIXED-AT `f8d28c7` · implementer-proved only. The db lane at `60acad9` shows 21 failed + 1 error by design: 20 await C9, and the G.61 pair (1F + 1E) awaits C1 (g61 §17, corrected in `dc41caa`) | ab7273142e8ff7e86 F11 |
| R6-05 | core | `test_core_logs_carry_no_exception_text.py:85`; `_no_sibling_declaration` docstring; `__traceparent__` comments; five "source line" docstrings | Prose says what is true now | Stale "names the module"; "4 reds" vs the measured 6; the retired `params` carrier; `failure_fields` no longer quotes source lines (utils M-STACK-HEADERS) | R6 nits; the implementer's grep of the family | none | n/a | 3* | 1 | F3 | OPEN (nits) | FIXED (prose) at `0e82657`, `7438263`, `360088f` | ab7273142e8ff7e86 nits |
| R6-06 | core | `core/db/table_definitions.py:1314-1319` @HEAD; `automation_store.py` (one-shot enqueue); `queue_span.valid_traceparent` | M-JOB-TRACEPARENT: a nullable `automation_runs.traceparent` (text, no default); `enqueue_one_shot_run` writes its own send span's W3C value, validated on write and read; `claim_run` writes none | Nothing stored the producer's context, so every consumer trace started fresh | R6: emitted DDL `traceparent text,`; one reader projects it; 17 edge probes held | `tests/unit/automations/test_run_traceparent_carrier.py`; db `test_automation_tables.py::test_traceparent_is_nullable_text_with_no_default` (:384) | yes — R6 m4a RED 7, m4b RED 2, m4c RED 9 | — | 2 | F1 | SETTLED (code) | OWNER-OWED C9 — test DB now, production before core AND api's worker deploy — code HOLDS | ab7273142e8ff7e86 table; §4a-bis M-JOB-TRACEPARENT; Add. 92 |
| R6-07 | core | `tests/unit/infra/test_cross_repo_reads_name_their_checkout.py` (`_no_sibling_declaration`) | An autouse fixture isolates every checkout test from a shell `SIBLING_CHECKOUTS` | A declaration leaking into the tests turns them red (api's version of the same defect, G44 I1) | R6 | the fixture | yes — R6: fixture off + a primary declaration → +4 reds | — | 0 | F3 | SETTLED | HOLDS | ab7273142e8ff7e86 table |
| IMP-01 | core | `core/resources/user/user_endpoints.py` (anonymous `POST /users`, no tenant resolved) | Refuse a signup whose company, invitation and domain resolve no tenant BEFORE the INSERT, with `SIGNUP_NOT_COMPLETED`, byte-identical to the existing-account refusal | The unbound INSERT hit RLS → 500: a workspace-existence oracle and a crash | the implementer's M-SIGNUP-ORACLE residual list (`b9a2343` report; g61 §16) | `tests/api/tenancy/test_signup_answers_no_account_existence.py::test_a_signup_that_resolves_no_workspace_is_told_nothing_about_it` (:181), `::test_no_workspace_and_an_existing_account_are_byte_identical` (:189) | implementer only (a mutant RED) | 0* | 2 | F1 | OPEN (implementer-found) | FIXED-AT `94e0502` · implementer-proved only. Spot-check: §4a-bis attributes this to "core r6"; R6's report does not contain it | a669194b19f6a0d15 (`b9a2343` report); g61 §16; §4a-bis M-SIGNUP-ORACLE; Add. 95 |
| IMP-02 | core | `core/resources/invitations/invitation_endpoints.py`, `models.py`, `services/invitation_email_composer.py` (`66b0217`) | M-INVITE-FRAGMENT core half: the link is `/invite#token=`; `POST /invitations/preview {token}` (extra fields and NUL refused) answers byte-identically to the GET; the GET is deprecated for one release and logs each use without the token | The secret in `?token=` reached ALB / CloudFront / Amplify logs and browser history | owner ruling B10 | `tests/api/invitations/test_invitation_preview_by_body.py` | implementer only (6 mutants) | 0* | 2 | F1 | ASSERTED (implementer) | FIXED-AT `66b0217` · implementer-proved only. The GET's removal after one release: STILL OPEN (g61 §11). The api skip list / limiter half is api's (N4 slice; Add. 102) | §4a-bis M-INVITE-FRAGMENT; a669194b19f6a0d15; g61 §16 |
| IMP-03 | core | `scripts/{backfill_chat_turn_facts,purge_product_events,review_improvement_findings,set_tenant_content_capture}.py` | Import `utils` at module level so M-G117-DEFAULT's safe loguru sink is installed before `main`; the twelve entrypoints pinned by equality | These four imported `utils` only inside functions, keeping loguru's default `diagnose=True` sink | the utils r3 audit list (g61 §14); implementer scan | `tests/unit/observability/test_entrypoints_import_utils_first.py::test_the_entrypoints_are_the_recorded_ones` (:138), `::test_every_entrypoint_imports_utils_while_it_is_still_importing` (:150) | implementer only (2 mutants) | 0* | 1 | F1 | ASSERTED (implementer) | FIXED-AT `0753e2d` · implementer-proved only; depends on utils `3e7477e` shipping with core (M-VERSIONS) | §4a-bis M-G117-DEFAULT; g61 §14, §16; a669194b19f6a0d15 |
| IMP-04 | core | `tests/authz/roles/test_bootstrap_seeds.py:664` @HEAD | The closed-door pin matches the failing frame by line number | utils M-STACK-HEADERS made `failure_fields`' stack frame headers only, so a pin that read the frame's SOURCE line went red with no core change | commit message | `::test_the_tenants_door_is_shut_and_that_is_deliberate` (:664) | implementer only (a mutant RED) | 3* | 1 | F3 | — | FIXED-AT `b31bd00` · implementer-proved only | commit `b31bd00`; §4a-bis M-STACK-HEADERS |
| IMP-05 | core | `_create_signup_tenant` race branch (`user_endpoints.py`) | Keep mapping any mint `ValueError` in the race branch to the fixed 400 | Nothing leaks (fixed text), but a server fault there is reported as the caller's; the complete fix catches `Refusal` only | implementer | none | n/a | 3* | 1 | F3 | OPEN | DEFERRED — g61 §11 | a8dca58e2bc842a65 report; g61 §11 |
| IMP-06 | core | `tenant_service.py:1030-1037` @HEAD | The teardown lock covers keys INTO `tenants`, not keys deeper in the closure | A new `ON DELETE CASCADE` key into e.g. `users` between the read and the DELETE is not blocked; the complete fix locks every declared relation in ROW EXCLUSIVE, which needs the grant role to hold a write privilege on all eight | R5A confirmed the gap is real and declared | none | n/a | 1* | 2 | F1 | OPEN | DEFERRED — g61 §11 | af2708fc9edbb7d7a; a8dca58e2bc842a65 report; g61 §11 |
| IMP-07 | core | tenant update, role create, operator create/delete refusal branches | Accept that `refused` is pinned by its own unit test there, not by the route | These branches are gated before the disclosure sweep's injection | implementer | `refused`'s unit test | n/a | 2* | 1 | F3 | OPEN | DEFERRED — g61 §11 | a5def59035346105b report; g61 §11 |
| IMP-08 | core | `roles` and `departments` lists, `users` pages (`created_at`-only `ORDER BY` + `LIMIT/OFFSET`) | Leave the unstable sort; the fix is the tenants one (primary key as a second sort column) | Found while checking the stamps' consumers; out of scope | implementer | none | n/a | 2* | 1 | F3 | OPEN | DEFERRED — g61 §11 | g61 §11 |
| IMP-09 | core | identity-cluster text stamps | Keep text stamps; chronology rests on every writer using one helper | `timestamptz` makes it a property of the data, but needs DDL, a parse of both widths and a re-typed keyset cursor | implementer | none | n/a | 3* | 2 | F1 | OPEN | DEFERRED — g61 §11 (this lane may not alter a table) | g61 §11 |
| IMP-10 | core | `core/resources/user/user_endpoints.py` (anonymous `GET /users/email/{email}`) | Keep the anonymous email-existence door | A recorded trade-off for signup recovery; rate-limited; it undercuts A19 | the implementer's residual list; owner B13 | none | n/a | 0* | 2 | F1 | OPEN | SUPERSEDED-BY M-EMAIL-DOOR (KEEP; the proper fix recorded in §6) | a669194b19f6a0d15 (`b9a2343` report); Add. 95 B13; §4a-bis M-EMAIL-DOOR; §6 |

### Re-stated from `claims-C1-utils-B1-core.md`

| row there | change since | state 2026-09-22 |
|---|---|---|
| **B1-18** (FK-free tenant-classed relations survive teardown; tier 2, OPEN) | M-CASCADE deliberately **added `comments` and `comment_thumbs_up`** to the FK-free set (R2-01). The teardown gate now reads the catalog both ways and refuses on drift (R3A-04, R4A-07). But by construction it still cannot see a relation with no FK, and the residue sweep is manual (M-COMMENT-PII). | STILL OPEN, and widened by ruling. The declared teardown contract the row asks for does not exist. |

---

## Totals

**109 rows**: 10 threads (`T-*`) and 99 per-round rows. Counted by script from the table above.

| State 2026-09-22 | Tier 0 | Tier 1 | Tier 2 | total |
|---|---|---|---|---|
| HOLDS | 15 | 6 | 3 | 24 |
| FIXED-AT · reviewer-proved or reviewer-held | 21 | 8 | 5 | 34 |
| FIXED-AT · implementer-proved only | 0 | 15 | 6 | 21 |
| FIXED (prose/plan, no guard) | 0 | 10 | 1 | 11 |
| STILL OPEN | 0 | 4 | 1 | 5 |
| SUPERSEDED-BY a ruling | 0 | 0 | 2 | 2 |
| ACCEPTED-AS-DEBT | 0 | 1 | 0 | 1 |
| DEFERRED | 0 | 3 | 2 | 5 |
| OWNER-OWED | 0 | 1 | 3 | 4 |
| REFUTED (the finding itself) | 0 | 1 | 0 | 1 |
| Routed out of this slice | 0 | 0 | 1 | 1 |
| **total** | **36** | **49** | **24** | **109** |

- **Chunks:** F1 65 · F2 18 · F3 26.
- **Claim state as the reviewer found it:** OPEN 51 · REFUTED 22 · SETTLED 17 · ASSERTED 10 · PARTIAL 8 · none 1.
  That is 22 claims whose own guard or statement a reviewer broke.

**Tier 0 is not empty in this slice: 36 rows.** The original nine packet files had none (README).
- **The reason is structural.** From R2 onward, each core reviewer mutated the PREVIOUS round's fixes. So a fix
  that survived a named mutation by a different agent became adjudicable from one row.
- **Every tier-0 row is HOLDS (15) or FIXED-AT · reviewer-proved (21).**
- **No r6 answer is tier 0.** The 21 "implementer-proved only" rows wait on core r7.

## Open claims, tier 2 first

### Tier 2 — judgment remains (owner-owed, deferred, superseded, open or routed)

1. **R2-01 / R2-02 / T-08 — C1, the comments-FK drop, OWNER-OWED.**
   - It must run before core deploys. Until then tenant deletes answer 503 (safe, but blocking) and 2 db reds stand.
   - For the auditor: was "drop the FK" right, rather than "anonymise at teardown"? The owner ruled M-CASCADE, and
     then M-COMMENT-PII kept the personal data (R1-02).
2. **R6-06 / R6-02 / R6-04 — C9, the `automation_runs.traceparent` column, OWNER-OWED.** It is needed in the test
   DB now, and in production before core AND api's worker deploy. A late migration stops every automation.
3. **R1-02 — comment PII survives a tenant delete, SUPERSEDED-BY M-COMMENT-PII.** Removal depends on a manual,
   dry-run-by-default sweep that nothing schedules.
4. **IMP-10 — the anonymous `GET /users/email/{email}` existence door, SUPERSEDED-BY M-EMAIL-DOOR (KEEP).** By
   design, it undercuts M-SIGNUP-ORACLE (R5B-03).
5. **IMP-06 — the teardown lock does not cover cascade keys deeper than `tenants`.** DEFERRED.
6. **IMP-09 — identity stamps stay text.** DEFERRED.
7. **R1-06 — the FK's integrity guarantee is gone for superuser and racing writers.** Stated in code, not closed. The
   racing row is designed residue. STILL OPEN.
8. **R4B-02 — utils' stdout sink printed exception text for every escaped exception (G.115).** Routed to utils. The
   plan says it is built at `0211f9b` and unreviewed. See the utils slice.
9. **Tier 2, fixed but implementer-proved only (core r7's queue):**
   - T-07: the 422 contract, where no round records a consumer check;
   - R4B-06: M-PII-IDS;
   - R5B-03 and IMP-01: the two signup oracles;
   - IMP-02: the invite fragment;
   - R6-01: the gate cannot be rebound.
10. **Tier 2, ASSERTED or reviewer-held without a mutation:**
    - G44-09: producer vocabulary and identity;
    - G44-10: won/lost is not an error;
    - R3A-10: a migrated catalog reads `[]` (a probe only; provable live after C1);
    - R4A-02: `pg_class` identities;
    - R4A-03: lock, catalog read and DELETE in one transaction. This and R4A-02 were held by analysis and a db
      pass, with no mutation.

### Tier 1 — still open, owner-owed, deferred or accepted

- **T-09**: the Cognito sweep misses a folded `getattr` and `operator.methodcaller`.
- **R0b-04**: `run_db_lane.py` cannot run `tests/db/analytics` (chat relations missing, no RLS). Every db figure is a
  hand run.
- **G44-07**: copilot-mro's offset walk over `list_tenants`, owed in the copilot-mro lane.
- **R1-07**: four hand-kept cascade literals.
- **R4A-04**: the utils release that core's imports need is OWNER-OWED (M-VERSIONS, C5).
- **R5A-02**: the bisect hole at merge `3f1a588` is ACCEPTED-AS-DEBT.
- **IMP-05, IMP-07, IMP-08**: DEFERRED (g61 §11).
- **Residue inside rows filed as FIXED or HOLDS:**
  - T-05: `type('X', (Refusal,), {})` and a tuple-unpack alias are claimed by neither `77a95bd` nor g61 §17.
  - T-10: `pyproject.toml`'s `../utils` is declared uncatchable.
  - G44-06: the lasting `__wrapped__` → marker-attribute fix is recorded in no plan.
  - T-02 and T-03: the declared blind-spot lists.

### Tier 1 — fixed, implementer-proved only (core r7's queue)

- T-01, T-02, T-03, T-04, T-05, T-06, T-10;
- R0a-02, R0b-03;
- R4A-06, G44-01, R6-03, R6-04;
- IMP-03, IMP-04.

## Filed elsewhere — pointers, not duplicates

- **G.21, the core half of M-RUNERROR** (`bbc67ed`; reviewer `a95bdecf6cb95ed17`, implementer `a9bce2a727442a3e9`).
  It is a core round, but it is filed in `claims-copilot-mro-rounds.md` as rows **G21-01 … G21-11**, with Repo = core.
  It is not repeated here.
- **R0a and R0b's copilot-mro halves** are filed in `claims-copilot-mro-rounds.md`:
  - `LG-01` … `LG-03` for `a82f7a058bb89b9d6`;
  - `LC-01`, `LC-02` for `a2a0edc3c3898cd61`.

  Only their core halves are here.
- **Routed out of core by these rounds, and not verified here:**
  - utils G.115 (R4B-02);
  - copilot-mro `data_discovery/jobs.py` and `document_hub/jobs.py` (G44-02), and the `ad_notification_dispatcher.py`
    offset walk (G44-07);
  - api's "core is OFFSET" prose and its `SIBLING_CHECKOUTS` test leak (G44-05, G44 I1);
  - flynapse-otel's corpus rows for r6 F7 (`34c814a`).

## Could not trace

- **Where two core-lane items came from.** CP25's lane row lists "terminal-status prose (`success`, `abandoned`)"
  and "stale `sweep_span.py:33`". Both were fixed (`af6adce`, `0ea20d3`) and settled by R2 (R2-13). Neither R0a's nor
  R0b's report names them; R0a checked `sweep_span.py:105-106` and found it sound. They are filed only as R2's claim,
  with no row for the finding that raised them.
- **R1's range at the SHA level.** It reviewed the uncommitted G.61 diff on `0609ad2` (its brief says `git diff HEAD`),
  which landed as `b68e41c` at about the same minute. Its transcript cannot tell which hunks were already committed
  when it read them.
- **Per-mutant detail behind implementer counts** such as "34 mutants", "84 mutants", "28 mutants" or "7 mutants
  RED". These rows are filed as "implementer-proved". The detail lives only in the implementers' scratch directories,
  which were not read.
- **The rest of `d7f7b54..0609ad2`** (`afd93fd` … `d368c7a`: G.69 savepoint, G.46 sweeps, the registry walk, the G.61
  text repair):
  - No round in this file reviewed it as a range.
  - R0a and R0b attacked parts of it: the savepoint and `runs_on_schedule`.
  - `claims-G5-chat-turn-facts.md` covers the backfill mirror, and `claims-copilot-mro-rounds.md` covers G.21.
  - No packet file was found for the G.61 text-repair commits `eaa714b`, `f71e182` and `c0be8f5`, or for G.46's core
    sweeps.
- **G.115's state in utils.** Cited from the plan entry only (R4B-02).
