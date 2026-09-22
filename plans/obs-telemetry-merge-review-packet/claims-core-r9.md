# Claims packet: core review r9 (`376ae7b..16cd1ae`, 17 commits)

This is an independent adversarial review (Opus), done on 2026-09-22, of the r8 fix batch.
**Verdict: FIX-FIRST — 0 P0 / 0 P1 / 4 P2 / 11 P3.**

The batch does what r8 asked in almost every row. Every r8 survivor I re-ran is dead, and the three
db-only halves the implementer could not prove (P2-2, P2-3, P3-3) are now **proven**: each was
killed on the real relation by its own test. The four P2s are new:

- two are in the scratch-tenant machinery the batch built;
- one is the half of r8 P2-2 that was not fixed on the read side;
- one is in the owner's C15 script.

## How the review ran

**Nothing real was edited.** Every run used a `git archive` copy under
`~/.claude/scratch/obs-merge/core-review-r9/` (durable scratch), laid out as `ws-<sha>/core-obsm`,
with every workspace checkout linked beside it.

**Siblings were pinned.** `utils-obsm` `179cc6d` and `flynapse-otel` `df503c2` were archived into
`sib/` and linked in place of the live trees.

**Lane recipe:** the brief's own, run from the copy root, through `pytest-slot.sh`:
`ENV_FILE=… DEBUG=false POSTGRES_DB=copilot_mro_test POSTGRES_USER=flynapse_app`,
`PYTHONPATH=<copy>:<ws>/utils-obsm:<ws>/flynapse-otel`, `-p no:randomly -o addopts="-ra --strict-markers"`.

**A reviewer plugin, `probes/r9probe.py`, did two jobs:**
- it printed `rootdir`, `core.__file__`, `utils.__file__` and `flynapse_otel.__file__`, all inside
  the copy (`logs/header-16cd1ae.log`);
- it logged every write into the scratch-tenant registry.

**Mutation proofs:**
- `mutant.sh` on the copy `ws-mut` (baseline-checked, cold cache).
- For the db lane, four mutants were applied at once to the copy `ws-dbmut`. They sit in four
  independent SQL builders or seats, each is marked `MUTANT-R9-*` and was confirmed by grep, and the
  run used a cold cache.
- The implementer's own texts were re-used from its scratch directories.

**Durable record:** `NOTES.md`, `mutation-results.txt`, `logs/` and `probes/`, all under the scratch
directory.

**Hard bans kept:**
- no real tree touched;
- the C15 SQL was never run, and no DDL was run;
- the only DML was the suite's own, plus reviewer probe tests in the suite's idiom (rows planted
  under the seed's scratch tenant and removed in `finally`), plus literal or VALUES-only SELECTs and
  catalogue reads;
- no docker, no AWS, no subagents;
- **two db runs in total.**

**One protocol slip, stated here.** One measuring run (`OTEL_SDK_DISABLED=true`) put `tests/api`
under `-n 2`, in one session with unit and authz. The brief says the api lane runs serially. It
printed no leak, and it was not repeated. Every api number below is serial.

## Lanes at HEAD `16cd1ae`

| lane | result | vs implementer |
|---|---|---|
| unit `-n 2` | 2353 passed + 2 failed | = 2355. The 2 are the known symlink artefacts `test_sibling_variant_*` |
| api serial | 1210 passed, rc=0 | = |
| authz `-n 2` | 285 passed, rc=0 | = |
| db serial (run 1, full lane + 11 reviewer probes) | 599 passed / 22 failed / 1 skipped / 2 xfailed | see below |

**db run 1.** Before the run I checked `pgrep`: no copilot-mro db, registries or tenancy lane was
running.

- **The 22 reds** are exactly the environment reds r8 named:
  - 20 `traceparent` (2 column checks + 18 one-shot);
  - 2 `turn_outcome` (`test_answer_outcomes_split_yes_unsure_no_and_null`,
    `…count_a_failed_turn_as_failed_never_unknown`).
- **r8's G.61 pair now PASSES.** The database has moved since r8.
- **The 599 passed break down as:**
  - r8's 583;
  - the G.61 pair (2);
  - the implementer's 3 new db cases;
  - my 11 probes, all green, so every prediction held.
- **No leak line.** The registry log shows 5 production mints registered, and all 5 were real rows:
  rbac roundtrip ×3, harness ×2.

## Every commit at its own HEAD (unit + authz `-j 2 -n 2`; api serial `-j 1`)

| commit | unit+authz passed | reds besides the 2 artefacts | api |
|---|---|---|---|
| `fe41002` | 2608 | none | 1183 |
| `38030c7` | 2616 | none | 1183 |
| `c6a81e9` | 2618 | none | 1184 |
| `5f8c879` | 2618 | none | 1184 |
| `e9fb7b3` | 2619 | drift pin `…deleted_chats_user…` ×6 checkouts | (known red span, not run) |
| `b2d67f2`, `8a85539`, `029bb14`, `6cebf8e`, `4171575` | 2615 | the ×6 above, plus annotation-resolution ×2, the depth-coupled scan and the scratch-tenant source rule (the db test file does not parse) | (known red span) |
| `b730a95` | 2625 | none | 1184 |
| `5e5743d` | 2625 | none | 1209 |
| `b5d616d` | 2625 | none | 1210 |
| `b1f9a23` | 2637 | none | 1210 |
| `bc9f5c6` | 2637 | none | 1210 |
| `0ff7aaf` | 2638 | none | 1210 |
| `16cd1ae` | 2638 | none | 1210 |

No api run printed a leak.

**The red span is only the known misassembly.** Every red in `e9fb7b3..4171575` comes from the two
misplaced files: `quality.py`'s mirror, and a db test file that does not parse, which reddens every
AST scan that reads `tests/`. Nothing else is red in that span.

**`b730a95` equals the measured tree.**
- The implementer captured its working tree before the split, in its own `split/full.patch` (a
  `-U0` diff against `c6a81e9`, taken at 01:55:31).
- I applied that patch to an archive of `c6a81e9` with `git apply --unidiff-zero`. The result is
  md5-identical to `b730a95` on all five files it touches.
- It is identical tree-wide, except for the C15 SQL, which was untracked at the time and was
  committed in `e9fb7b3`.
- `b730a95..16cd1ae` touches no analytics file, so HEAD's analytics content is the measured content.

---

## Findings, ranked

### P2-1 (tier 1): the real sentinel is wired by a line only a SHAPE test guards; disabling it passes every lane

**Where:** the registration is `tests/conftest.py:181-186` (`pytest_configure` registers
`importlib.import_module(SCRATCH_TENANT_SENTINEL)`). Its only guard is
`tests/unit/harness/test_scratch_tenant_rules.py:125`.

**What the guard checks.** It is an AST check with two conditions:
- some `.register(` call exists inside `pytest_configure`;
- the string `"tests.fixtures.scratch_tenants"` appears anywhere in the file.

**Why the behavioural proof does not cover it.** The behavioural tests
(`test_scratch_tenant_sentinel_reports_under_xdist.py`) run pytester with **their own copy** of the
registration (`_CONFTEST`), so they never exercise the real line.

**Mutant REG:** `importlib.import_module(SCRATCH_TENANT_SENTINEL)` → `importlib.import_module("tests.fixtures")`,
which registers a package with no hooks.
- It SURVIVED `tests/unit/harness` (aimed).
- It SURVIVED the full unit+authz lane (2638 passed, rc=0).
- It SURVIVED the full api lane, serial (1210 passed, rc=0).

**Failure scenario.** A refactor of `pytest_configure` that keeps a `register(` call and the constant
(a reorder, a rename, a wrong module) silently removes the sentinel from every lane:
- a real leak in the db or api lane is neither swept nor named;
- the run exits 0;
- the shared database keeps the row.

This is P2-5's whole guarantee, lost behind a shape test.

**Fix:** a one-line behavioural pin in the session itself:
`request.config.pluginmanager.get_plugin("scratch-tenant-sentinel") is sys.modules["tests.fixtures.scratch_tenants"]`,
and the module's `pytest_sessionfinish` among `config.hook.pytest_sessionfinish.get_hookimpls()`.

### P2-2 (tier 1): in a combined session the shim registers STUBBED mints, so the sentinel can delete a shared-database row this run never created

**Where:**
- `tests/api/conftest.py:10-17` and `tests/db/conftest.py:79-87` put the shim in force with a
  SESSION-scoped autouse fixture;
- the shim itself is `tests/fixtures/scratch_tenants.py:200-222`.

**Why the scope matters.** Once an api or db test has started the shim, it stays in force for
every later test in that session, including tests outside those directories.

**Measured** (`logs/combined-probe.*`):
- The session was `tests/api/tenancy/test_the_api_lane_adopts_production_mints.py` +
  `tests/unit/db/test_tenant_service.py`.
- The unit file calls the REAL `create_tenant` over a stubbed grant pool with `tenant_id = "t-1"`.
- The shim registered **`t-1 (mint_tenant)` seven times**.
- At session end the sentinel queries `t-1` in the shared `copilot_mro_test`, and would DELETE it
  (with its cascade) and report it as a leak.
- Today `t-1` is absent. The probe removed the entry from the registry before the sentinel ran.

**Failure scenario.** `pyproject.toml` has `testpaths = ["tests"]`. A bare `pytest` (or `poetry run
pytest`) in core is therefore exactly this session: api sorts first, then authz, db, unit. The day
any lane (another repo's, a seed, a developer) holds a tenant `t-1`, a core run deletes it. That
breaks the module's own invariant: "Only rows this process registered are ever deleted — by id,
never by pattern".

**Not affected: the api lane alone.** Its registry log shows only fixture mints (the analytics seed
and the events tenants).

**Fix:**
- scope the shim to the tests of those two directories: a function-scoped autouse fixture, or check
  `request.node.path`;
- and/or register only when `tenant_service.get_grant_service` is the real function (a stubbed pool
  mints nothing real).

### P2-3 (tier 2): the TITLE half of r8 P2-2 is not fixed on the read side, and two texts say it is

**Where:**
- `core/resources/analytics/panels/quality.py:470-481` (`max(cited ->> 'document') AS label`, with
  no liveness);
- the docstring at `:457-465` ("A deleted chat's citations have lost their title");
- `scripts/rbac/anonymise_already_deleted_chats.sql:31-35` ("the question-text panels read live
  blocks only — the rows are wrong in the database, not on the dashboard").

**Measured** (db run 1, probe `test_r9_a_title_cited_only_from_an_unanonymised_deleted_chat_labels_its_row`):
- I planted a chat deleted before `d4792d6b`: chat and block soft-deleted, the facts row as written.
- It cites `{"doc_uid": "D-R9-PRIV", "document": "R9 private upload title"}`.
- `top_cited_documents` returns `label: 'R9 private upload title'`.

**Failure scenario.** Until the owner runs C15, a user's uploaded-document title — "the user's own",
by the ruling's reasoning — is shown on the Quality tab for a chat that user deleted. Meanwhile:
- the C15 header tells the owner the dashboard is already clean;
- the g61 §21 row records P2-2 as fixed.

The same is true after C15 for any row the settle-writer race (copilot-mro r8, P1 candidate) creates
later.

**Fix:** the read-side defence `e9fb7b3` gave `unanswered_questions` fits here too. Citations come
only from saved turns, so a citation whose block is not live is a deleted chat's. Take the label
over live blocks only:
`max(cited ->> 'document') FILTER (WHERE cb.block_id IS NOT NULL)` over a `LEFT JOIN chat_blocks cb … AND cb.deleted = false`.
Then correct both texts.

### P2-4 (tier 2): C15 is not idempotent on a NULL feedback payload, and its read-back cannot gate the COMMIT

**Where:**
- `scripts/rbac/anonymise_already_deleted_chats.sql:119-135` (the feedback half);
- `:147-154` (the read-back);
- `:156` (an unconditional `COMMIT`);
- the claims at `:54-59` ("a second run rewrites nothing and reports 0 rows") and `:137-138` ("to
  be inspected before COMMIT").

**Measured** (db run 1, VALUES-only SELECTs):
- For a NULL `feedback_data`, `(NULL - 'comment' - 'session_id') || jsonb_build_object(…)` is NULL.
- `feedback_data ->> 'user_id' IS DISTINCT FROM 'deleted-user'` is TRUE on the first run AND on the
  second.
- The column is nullable in the real database (`is_nullable = YES`).
- copilot-mro documents the shape: "A NULL payload stays NULL".
- `collect_explicit.py:346` handles `feedback_data is None`.

**Failure scenario.** Take any database holding a NULL-payload feedback row on a deleted chat,
including one copilot-mro's own delete already anonymised. There, C15:
- rewrites that row on every run;
- counts it in `feedback_rows_anonymised`;
- reports `feedback_rows_still_identifying > 0` forever.

The script says anything non-zero is "a row the predicates above did not reach, to be inspected
before COMMIT". But run as documented (`psql -v ON_ERROR_STOP=1 -f …`), the COMMIT has already
happened. So the owner is told the irreversible migration failed, with no way to stop it.

**Fix:**
- make the feedback predicate `cf.feedback_data IS NOT NULL AND (…)` and give the user id its own
  test;
- turn the read-back into a gate: a `DO` block that `RAISE`s when either count is non-zero (rolling
  back);
- or drop the `COMMIT` and tell the owner to commit by hand.

---

### P3-1: `top_cited_documents` still merges or lumps some documents

The docstring claims "one row per DOCUMENT". Measured in db run 1:
- **Title collision across kinds.** Two uid-less documents titled `R9 Chapter 5`, one AMM and one
  SRM, become ONE row: `citations 2`, `document_kind 'SRM'` (the `max`). The old key had kept them
  apart.
- **Anonymised uid-less citations.** Citations with no uid and no title, from different kinds, are
  lumped into ONE NULL-keyed row. A row with no label is therefore not "a document".

**Fix:** state both limits in the docstring. For the first, key uid-less titles on `(title, kind)`
when the kind is known.

### P3-2: under xdist, the sentinel double-reports and does not see crashes

Measured with the implementer's pytester harness (`logs/sentinel-probes.log`):
- **A worker that raises `KeyboardInterrupt` after leaking.** rc=2, and the leak is named, but
  **twice** ("2 tenant(s)"). `pytest_testnodedown` runs on `workerfinished` AND again on
  `errordown`.
- **A worker that dies (`os._exit`).** rc=1, and the leak is neither swept nor named. This is
  consistent with the declared limit on process death.
- **`-n 2 -x`.** rc=2 and the leak is named, as it should be.

A real Ctrl-C on the controller (as against one raised in a test) is reasoned, not run: the workers
sweep, but nobody names the leaks.

**Fix:** de-duplicate by `tenant_id` on the controller, and add "an xdist worker's death" to the
declared limit.

### P3-3: a production-minted scratch row cannot be named by its prefix

The docstring (`scratch_tenants.py:28-30`) says a row left by a killed process is "NAMED — by the
`t-dblane-<session>` prefix". Since `c6a81e9`, the registry also holds shim-registered production
mints, and their ids are bare uuids or `fixed-<uuid>` (the registry log from db run 1). A killed db
run holding one leaves a row that owner item C14's janitor cannot find by prefix.

### P3-4: importlib gets past the single-name guard

Measured (`logs/p24-importlib.log`):
- `importlib.reload(st)` empties `_OUTSTANDING` mid-session, and the plugin (the same module object)
  then reads an empty registry.
- `spec_from_file_location("tests.fixtures.scratch_tenants", …)` loads a SECOND module under the
  canonical name, with its own registry.

Both are contrived, and neither is declared. A module-level `_OUTSTANDING = globals().get("_OUTSTANDING", {})`
closes the reload case.

### P3-5: P3-6 (F10) leaves a residue inside pointer fields

The claim is "inside a pointer field, any absolute URI". Measured (`logs/p36-shapes.log`), a URL on
a NON-configured endpoint (a second MinIO) is KEPT in these spellings:
- percent-encoded (as an element and inside text);
- protocol-relative (as an element, inside text, and as a nested dict value).

The JSON-escaped spelling is caught. Outside pointer fields, everything I found kept falls under the
declared limits (boto `Prefix`, `Key` and `Bucket` at different levels, `s3_object_key`, a lone
`Key`), except a bare bucket host in text with no path.

**Over-withholding** (`logs/p36-fp.log`). The value "Refer to the copy at
acme.s3.amazonaws.com/x.pdf for the scan" is now dropped WHOLE: the scheme-less rule reads the text
before the first `/` as a host. At `c6a81e9` it was kept. This fails closed, but it is not "redacted
in place" as the docstring says.

### P3-6: P3-7's Cognito sweep still misses ordinary spellings

**Through `sweep()`: 11 of 11 plants missed** (`logs/p37-plants.log`):
- `from core import ops` + `ops.OP`;
- `import core.ops` with no alias + `core.ops.OP`;
- a module `OP: str = "…"` (an annotated assignment);
- the same in a class body, read as `self.OP`;
- a base class in another core module, read as `self.OP`;
- an imported class constant `K.OP`;
- a dict-constant subscript;
- a tuple-unpacked constant;
- a local variable holding a literal;
- `type(c).__dict__[…]`;
- an aliased `getattr`.

None of them is declared.

**In the tree:** two plants in `tenant_claim_writer.py` survive the aimed test and the full lanes
(`r9-P3-7-local-variable-literal`, `r9-P3-7-annotated-module-constant`).

This is spelling-hunting. The structural fix is already declared: botocore events on the two
factories.

### P3-7: P3-9's exporter pin reads names

The claim is true today. No test enters the lifespan in-process: `test_core_standalone_telemetry`
does so only in a subprocess string, and `OTEL_SDK_DISABLED=true` reddens exactly the 21 named span
tests (measured below). But `test_no_live_service_pins.py:30-91` reads two spellings only:
`setup_logging` / `bootstrap` by name, and `with TestClient(…)`.

Three plants SURVIVED the full unit+authz and api lanes:
- `async with lifespan(app)` in a test;
- `from fastapi.testclient import TestClient as Client` + `with Client(app)`;
- `from utils.logging_config import setup_logging as _configure` + `_configure(...)` in a core
  module (a second exporter seat).

**Fix:** state the limit, or pin behaviourally. For example, a session-end assertion that
flynapse-otel's bootstrap `_state` is untouched.

### P3-8: the P1-1 fix does not cover the email in the email-lookup path

`core/middleware/access_line.py:29` withholds query parameters only. `GET /users/email/<address>`
(`user_endpoints.py:1670`) carries the address in the PATH. The filter passes it:
`"GET /v1/users/email/alice.smith%40corp.example?company=Acme HTTP/1.1"` (`logs/p11-access.log`).

`api-obsm/flynapse_api/routers/users.py:11` imports `core.fastapi_app`, so the filter is installed
process-wide in the gateway as well. flynapse-otel's URL rule declares path segments unseen. I found
no first-party caller of that route in the workspace, so exposure is limited to direct callers.

**Fix:** withhold the `/users/email/{email}` segment in the same filter (and in api's seat).

### P3-9: C15 cannot reach some rows

These are C15's reach, not its correctness:
- **Facts rows with a NULL `chat_id`.** The column is nullable, and both the delete and C15 key on
  `chat_id`.
- **Chats soft-deleted while their blocks stayed live.** Before `d4792d6b` the delete ran two
  separate statements. Measured: `unanswered_questions` shows the real asker AND the excerpt for
  such a chat. After C15 the asker becomes `deleted-user`, but the live block's excerpt still shows,
  and so does the drilldown. C15 could also soft-delete the live blocks of deleted chats.
- **`[]` becomes NULL.** The facts half rewrites an empty `cited_documents` array to NULL, as the
  delete does. This is an observation only.

**What checked out:**
- the `BYPASSRLS` refusal fires for `flynapse_app` (`bypasses = False`);
- the operators resolve under the pinned `search_path`;
- an object payload is idempotent;
- every column the script names exists;
- FORCE RLS is on all four relations, and there are no triggers.

### P3-10: stale text

- `quality.py:13` still says "`delete_chat` leaves `chat_feedback` untouched". That has been false
  since copilot-mro `de2665b3`, and it contradicts the C15 header in the same batch. The range edited
  this docstring and kept the sentence.
- g61 §11 still lists the same item as future work.
- g61 §21's P2-2 row omits the title half (P2-3).
- The workspace plan's uncommitted M-FACTS-ANONYMISE note calls C15 "idempotent" (P2-4).

### P3-11: the brief's named skip, `test_automation_endpoints.py:64`, hides no red

**Verdict: it hides NO red today.**
- With the database present, the file runs 39 of 39, and the api lane has zero skips.
- Against a database that answers and refuses (`POSTGRES_DB=r9_no_such_db`), the lane goes RED
  through its gate tests (`test_the_estate_can_host_the_isolation_lane` / `…database_lane`). The
  file's module skip is one of 21 skips there.

**Residual.** `_db_ok()` swallows EVERY exception (`:56-61`, and the same code at
`test_events_endpoint.py:33-41`). The lane's gates skip only when no server is there. So a fault in
the database layer — a utils regression, or a tenancy rule that refuses the unbound `SELECT 1` —
skips both files instead of failing them. Other db-touching api tests would probably go red in the
same run.

**Fix:** re-raise anything that is not a connection refusal, as `tests/db/conftest.py`'s
`reachable_cluster` does.

---

## What I tried to break and could not

- **The db-only halves are PROVEN** (db run 2, all four mutants at once, each in its own builder or
  seat, 18 other tests green):
  - **M22** (the `unanswered_questions` CASE neutered) is KILLED by
    `test_a_chat_deleted_before_anonymisation_still_reads_as_a_deleted_user` (`'u-a-old'` returned).
  - **M23** (the old key `doc_uid, manual_type, title`) is KILLED by
    `test_a_card_batch_citation_joins_its_documents_row_whatever_its_kind_says` (`D1` ×2).
  - **M33** (the catch-all dropped) is KILLED by
    `test_answer_outcomes_sql_puts_every_turn_in_exactly_one_series` (`unknown 2 != 3`).
  - **M24** (the shim registers nothing) is KILLED by
    `test_a_production_mint_that_forgot_adopt_is_still_the_sessions`.
- **The sentinel under xdist works for the ordinary cases.** A leak is named with rc=1 both serially
  and at `-n 2`. A clean run is rc=0. A pending module teardown on Ctrl-C is not a false leak (rc=2).
  A leak plus an interrupt stays rc=2 and is named. `-n 2 -x` names it.
- **The implementer's sampled mutants are KILLED again:**
  - P2-5 worker hand-off;
  - P3-1 `trylast`, killed by the BEHAVIOURAL pytester file alone, not only the shape test;
  - P2-4 second name;
  - P3-2 B1 in unit;
  - P3-6 fold;
  - P3-7 second argument;
  - P3-9 module-level seat.
- **P3-9's "21".** With `OTEL_SDK_DISABLED=true` across unit, api and authz, exactly **21** span
  tests go red:
  - traceparent carrier ×2;
  - queue send span ×10;
  - cognito spans ×4;
  - spans-withhold ×5.
- **The per-user panels (r8 P2-2).**
  - `unanswered_questions` answers `deleted-user` (M22).
  - The drilldown excludes a deleted chat's un-anonymised feedback (probe).
  - Every usage panel reads `chat_blocks … deleted = false`.
  - Core's improvement panels show no signal text.
  - The only per-user panel still attributing a deleted chat is **spend** (`cost.py:198-217`,
    `llm_usage`). That is the OPEN owner question; I did not try to solve it.
- **P1-1's `search`.** It is withheld as `search`, `SEARCH` and a percent-encoded name. Both listing
  lines log `search_given` only.
- **The api lane alone** registers only real mints.

## What I did not test

- A real SIGINT delivered to an xdist controller (reasoned in P3-2).
- A SIGKILL while a fixture holds a tenant: it would leave a real row.
- Whether any real database holds NULL-payload feedback, NULL-`chat_id` facts rows or half-deleted
  chats. There were no reads of real data.
- The api half of the combined-session hazard, run against a present `t-1`: that would delete a row.
- `tests/e2e` holds no collected tests.

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state | Answers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r9-01 | core | `tests/conftest.py:181-186`; `scratch_tenants.py:301-322` | the sentinel is the fixture module, registered as a plugin; worker → `workeroutput` → controller | r8-P2-5 | pytester: leak rc=1 named, serial and `-n 2`; handoff mutant KILLED (re-run) | `test_scratch_tenant_sentinel_reports_under_xdist.py` | yes (module) | — | 0 | F2 | SETTLED for the module | r8-26 |
| r9-02 | core | `tests/conftest.py:181-186`; `test_scratch_tenant_rules.py:125` | the real registration guarded by AST shape | r8-P2-5 | REG mutant SURVIVED unit+authz (2638) AND api (1210) | shape test only | survivor shown | 2 | 1 | F2 | OPEN, P2-1 | new |
| r9-03 | core | `scratch_tenants.py:309` | `trylast`; a non-OK status left alone | r8-P3-1 | pytester Ctrl-C rc=2 with no false leak; trylast mutant KILLED by the behavioural file | same | yes | — | 0 | F2 | SETTLED | r8-27 |
| r9-04 | core | `scratch_tenants.py:301-307` | the controller collects in `pytest_testnodedown` | r8-P2-5 | interrupt at `-n 2`: named TWICE ("2 tenant(s)"); crash: not named (declared) | none | probe | 3 | 1 | F2 | PARTIAL, P3-2 | new |
| r9-05 | core | `tests/api/conftest.py:10-17`; `tests/db/conftest.py:79-87`; `scratch_tenants.py:200-222` | session-scoped runtime adoption of `mint_tenant` | r8-P2-4 | M24 KILLED (db); implementer's `adopt` KILLED; api alone registers only real mints | `test_a_production_mint_that_forgot_adopt_is_still_the_sessions` | yes | — | 0 | F2 | SETTLED within the db/api lanes | r8-28 |
| r9-06 | core | same | the shim stays in force for later tests of a combined session | — | `t-1` registered ×7 from stubbed unit mints; the sentinel would SELECT it and DELETE it | none | probe | 2 | 1 | F2 | OPEN, P2-2 | new |
| r9-07 | core | `scratch_tenants.py:53-58` | one import name; any other refuses | r8-P2-4 | second-name mutant KILLED; `reload` / canonical-name spec defeat it | `test_the_factory_refuses_to_load_under_a_second_name` | yes (other names) | 3 | 1 | F2 | PARTIAL, P3-4 | r8-28 |
| r9-08 | core | `scratch_tenants.py:28-30` | process death: a row NAMED by prefix | r8-P3-1 | production mints are bare uuids / `fixed-<uuid>` (db run 1 registry) | none | n/a | 3 | 1 | F3 | OPEN, P3-3 | r8-27 |
| r9-09 | core | `quality.py:428-440` | `unanswered_questions` answers `deleted-user` when the block is not live | r8-P2-2 | M22 KILLED (db); DELETED_USER_ID mirror KILLED (impl, unit) | `test_a_chat_deleted_before_anonymisation…` + drift pin | yes, both halves | — | 0 | F1 | SETTLED | r8-02 |
| r9-10 | core | `quality.py:457-481`; C15 `:31-35` | `top_cited_documents` label from any citation; "the dashboard is already clean" | r8-P2-2 | probe: a deleted chat's title labels the row | none | probe | 2 | 2 | F1 | OPEN, P2-3 | r8-02 |
| r9-11 | core | `quality.py:476-479` | GROUP BY `COALESCE(doc_uid, 'title:'‖title)`; `max(manual_type)` | r8-P2-3 | M23 KILLED (db); probes: a title collision across kinds merges; anonymised uid-less citations lump together | `test_a_card_batch_citation_joins…` | yes | 3 | 1 | F2 | SETTLED for `doc_uid`; P3-1 edges | r8-06 |
| r9-12 | core | `quality.py:189-214` | `unknown` is the catch-all; the verdict vocabulary mirrored | r8-P3-3 | M33 KILLED (db); vocabulary mirror KILLED (impl, unit) | CTE case + drift pin | yes, both halves | — | 0 | F2 | SETTLED | r8-04 |
| r9-13 | core | `test_chat_turn_facts_drift_pin.py:863-868` | failed = the one outcome that is not `success` | r8-P3-2 | B1 KILLED in unit (re-run) | same | yes | — | 0 | F2 | SETTLED | r8-07 |
| r9-14 | core | `test_panels_read_only_live_chat_blocks.py:7-15` | the unit rule states that it reads a spelling | r8-P3-4 | read; the db case kills A1 (r8) | same | n/a | — | 1 | F3 | SETTLED (text) | r8-12 |
| r9-15 | core | `panel_service.py:138-143` | the 300 s window after a delete is stated at the cache seat | r8-P3-5 | read | none | n/a | 3 | 2 | F1 | SETTLED as stated (the closure is an owner design call) | r8-30 |
| r9-16 | core | `scripts/rbac/anonymise_already_deleted_chats.sql:85-96` | refuses unless superuser or BYPASSRLS | C15 | `flynapse_app` `bypasses=False`; FORCE RLS on all four | none (owner-run) | n/a | — | 2 | F1 | SETTLED (probe) | r8-02 |
| r9-17 | core | same `:54-59, 119-156` | "idempotent"; read-back "before COMMIT" | C15 | NULL payload matches on runs 1 and 2; COMMIT unconditional | none | probe | 2 | 2 | F1 | REFUTED, P2-4 | r8-02 |
| r9-18 | core | same `:98-116` | facts half keyed on `chats.deleted` via `chat_id` | C15 | `chat_id` nullable; half-deleted chat keeps a live excerpt (probe) | none | probe | 3 | 2 | F1 | PARTIAL, P3-9 | r8-02 |
| r9-19 | core | `storage_locations.py:52-124,170-236` | six F10 shapes; folded key names; any value under a location key | r8-P3-6 | impl mutants ×6 KILLED (fold re-run KILLED); pointer-field percent-encoded and protocol-relative non-configured URLs KEPT; whole-value over-withhold | `test_document_answer_names_no_storage_location.py` | yes (the six) | 3 | 1 | F1 | PARTIAL, P3-5 | r8-20 |
| r9-20 | core | `test_cognito_calls_are_spanned.py:107-280` | by-name second argument; imported and class constants | r8-P3-7 | impl mutants KILLED (re-run); 11/11 reviewer plants missed; 2 in-tree plants survive the full lanes | same | yes (named spellings) | 3 | 1 | F1 | PARTIAL, P3-6 | r8-23 |
| r9-21 | core | `test_no_live_service_pins.py:28-91`; README | `OTEL_SDK_DISABLED` not set; exporters only in the standalone lifespan | r8-P3-9 | 21 span reds VERIFIED; seat mutant KILLED (re-run); 3 plants survive the full lanes | same | yes (seat) / survivors | 3 | 1 | F2 | PARTIAL, P3-7 | r8-29 |
| r9-22 | core | `core/middleware/access_line.py:29-51` | withhold personal QUERY values on `uvicorn.access` | r8-P1-1 | `search` withheld; the email-lookup path `/users/email/<addr>` passes (probe) | `test_access_line_withholds_personal_query.py` | impl (`search`) | 3 | 1 | F1 | PARTIAL, P3-8 | r8-08 |
| r9-23 | core | `test_operator_crud.py:711-717,783-784` | refusals assert the key is not echoed | r8-P3-8 | M4 KILLED there (impl) | same | impl | — | 1 | F1 | ASSERTED | r8-17 |
| r9-24 | core | `b730a95` | fix-forward restores the lane-green tree | history | recon of `c6a81e9` + `full.patch` md5-equal on 5 files | the lanes | n/a | — | 1 | F2 | SETTLED | r8 batch |
| r9-25 | core | range | every commit at its own HEAD | plan §2.4 | table above; the red span is only the known misassembly | the lanes | n/a | — | 1 | F2 | SETTLED | r8-32 |
| r9-26 | core | `quality.py:13`; g61 §11, §21; workspace plan note | stale or overclaiming text | — | read | none | n/a | 3 | 1 | F3 | OPEN, P3-10 | r8-33 |
| r9-27 | core | `tests/api/automations/test_automation_endpoints.py:56-64`; `test_events_endpoint.py:33-41` | a module skip when `SELECT 1` raises anything | earlier packet flag | 39/39 with the db; the lane is red when a server refuses; `_db_ok` swallows every exception | the lane gates | n/a | 3 | 1 | F2 | SETTLED (no hidden red); P3-11 residual | packet flag |
| r9-28 | core / copilot-mro | `cost.py:198-217`; `improvement_signals`, `llm_model_calls` | a deleted chat's identity kept outside facts and feedback | M-FACTS-ANONYMISE | read: `improvement_signals.detail` holds the typed comment excerpt + `user_id`/`chat_id`; `llm_usage` spend (carried) | none | n/a | 3 | 2 | F1 | OPEN (owner question) | r8-34 |

## Open claims, tier 2 first

**Tier 2 (owner or privacy):**

1. **r9-10 (P2-3).** Apply the read-side label defence to `top_cited_documents`, and correct the C15
   header and the panel docstring.
2. **r9-17 (P2-4).** Fix C15's feedback predicate for NULL payloads, and make the read-back a gate:
   `RAISE` before `COMMIT`. This must happen **before the owner runs it.**
3. **r9-18 (P3-9).** Optionally, have C15 also soft-delete the live blocks of deleted chats. Declare
   the NULL-`chat_id` reach.
4. **r9-28 (owner question, widened from r8-34).** `llm_usage` spend (carried). NEW: the delete and
   C15 leave `improvement_signals` (the typed comment excerpt, `user_id`, `chat_id`),
   `improvement_findings.evidence` and `llm_model_calls` untouched. Does M-FACTS-ANONYMISE extend to
   them?
5. **r9-15 (carried).** The generation-token closure of the 300 s panel cache is an owner design call.

**Tier 1, in order:**

1. **r9-02 (P2-1).** A behavioural pin that the real root conftest registers THIS module as the
   sentinel.
2. **r9-06 (P2-2).** Scope the shim to db and api tests, or refuse stubbed pools.
3. **r9-04, r9-07, r9-08.** Dedupe the controller's leaks; declare the reload and canonical-name
   defeats; correct "named by prefix".
4. **r9-11, r9-19, r9-20, r9-21, r9-22.** The edge limits of `top_cited_documents`; the pointer-field
   spellings and the over-withhold; the Cognito and exporter plants (state them or pin
   behaviourally); the email-lookup path.
5. **r9-26, r9-27.** Text corrections; `_db_ok` should re-raise a non-connection fault.

**Tier 0, settled in this range:** r9-01, r9-03, r9-05, r9-09, r9-12, r9-13. Each was seen RED here
when its property was removed. r9-24 and r9-25 are measured (tier 1).

## C15 SQL verdict

**Correct in intent; FIX-FIRST in mechanics:**
- the refusal works;
- the search path is safe;
- the names bind;
- object payloads are idempotent;
- it mirrors the delete's scope exactly.

What must change before the owner runs it:
- its idempotency and "0 rows on a second run" claims fail on NULL `feedback_data`, a shape
  copilot-mro documents;
- its read-back cannot stop the unconditional COMMIT;
- its header wrongly says the dashboard is already clean (titles still show, P2-3).

It reaches only rows keyed by a non-NULL `chat_id` of a `chats.deleted` chat. It cannot close the
settle-writer race (copilot-mro's fix). **Not run by the reviewer.**
