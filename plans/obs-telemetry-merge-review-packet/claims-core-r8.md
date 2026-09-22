# Claims packet: core review r8 (`dc41caa..b4d2c33`, 16 commits)

This is an independent adversarial review (Opus), done on 2026-09-21. **Verdict: FIX-FIRST —
0 P0 / 1 P1 / 5 P2 / 11 P3.**

## How the review ran

**Nothing real was edited.** No code tree was changed: every run used a `git archive` copy in the
reviewer's private scratch (`scratchpad/core-review-r8/`).

**How each mutant was proved:**
1. Applied to a scratch copy and grep-confirmed.
2. Run with a fresh `PYTHONPYCACHEPREFIX`.
3. Reversed, and its md5 checked against the HEAD blob.

From the coordinator's mid-review switch on, `.superpowers/tools/mutant.sh` did the same. After every
batch the whole scratch tree was `diff -r`'d against a fresh `git archive b4d2c33`; it was identical
each time.

**Hard bans kept:**
- No DB MCP and no DDL.
- No DML beyond what the suite did, plus three reviewer probe tests written in the suite's own idiom
  (the factory's mint, and VALUES-only SELECTs).
- No docker, no AWS, no Cognito.

| repo | worktree | branch | range | HEAD at review | tree state |
|---|---|---|---|---|---|
| core | `/home/aditya/Code/core-obsm` | `obs-merge` | `dc41caa..b4d2c33` | `b4d2c33` | read only (archives only) |

**Siblings:**
- `utils-obsm` archived at **`4d86ae9`** (the brief's snapshot; the implementer measured `8572635`);
- `flynapse-otel` archived at its HEAD **`05e1a6e`**;
- every other sibling is a read-only symlink.

**Lane recipe, run from each archive's root:**
- env: `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test POSTGRES_USER=flynapse_app`;
- `PYTHONPATH=<ws>/core-obsm:<ws>/utils-obsm:<ws>/flynapse-otel:<probes>`;
- command: `api/.venv/bin/python -m pytest -p r8netguard -p no:randomly -p no:cacheprovider -o addopts="-ra --strict-markers"`;
- pytest's own exit status recorded.

**`r8netguard`** is a scratch plugin. It REFUSES every non-loopback `connect` and every non-loopback
DNS lookup, and records each attempt. The brief bans network, and the pre-hygiene api lane reaches
AWS.

**Printed and checked for every run:**
- `rootdir` = `…/core-review-r8/ws-<sha>/core-obsm`;
- `core.__file__` = `…/ws-<sha>/core-obsm/core/__init__.py`;
- `utils.__file__` = `…/ws-<sha>/utils-obsm/utils/__init__.py` (the `4d86ae9` archive).

## Every commit at its own HEAD

| commit | unit (+2A) | api | authz | api lane: refused outbound attempts |
|---|---|---|---|---|
| `dc41caa` (base) | 2000 | 1154 | 285 | 120 (DNS `oidc.ap-south-1.amazonaws.com`) |
| `6e17993` M-FACTS-ANONYMISE read side | 2003 | 1154 | 285 | 120 |
| `2f972e4` limiter clock | 2003 | 1154 | 285 | 120 |
| `7d5144c` facts panels | 2010 | 1154 | 285 | 120 |
| `3f5508a` operator codes | 2010 | 1154 | 285 | 120 |
| `aa46baf` F7/F9 leftovers | 2022 | 1163 | 285 | 120 |
| `d8b330d` small items | 2022 | — (docs + an uncollected e2e script) | — | — |
| `fde8ccd` r7-P2-1 | 2060 | 1163 | 285 | 120 |
| `3b4369f` r7-P2-2 | 2065 | 1163 | 285 | 120 |
| `9ac18c0` r7-P2-3 | 2065 | 1163 | 285 | 120 |
| `e6dc582` r7-P2-4 | 2069 | 1163 | 285 | 120 |
| `93caffd` residuals | 2072 | 1166 | 285 | 120 |
| `1232f21` P3-7 + P3-1 | 2072 | 1180 | 285 | 120 |
| `d069a60` P3-4/5/9 | 2081 | 1182 | 285 | 120 |
| `044eeac` plan | code-identical to `d069a60` | | | |
| `5b49993` test hygiene | 2089 | 1182 | 285 | **0** |
| `b4d2c33` plan | 2089 | 1182 | 285 | **0** |

**`2A`** = the two symlink artefacts:
- `test_sibling_variant_picks_the_checkout_that_matches_this_one`;
- `…_falls_back_to_the_bare_name_when_there_is_no_twin`.

They are red at every commit, and nothing else is red in any unit/api/authz run (failure-id set
checked per log).

**HEAD matches the implementer exactly.** At `b4d2c33`, unit/api/authz = **2091 / 1182 / 285**, the
implementer's §20 numbers. **The newer utils (`4d86ae9` vs `8572635`) changes nothing measurable at
HEAD.**

**Why the base's unit count differs from r7's.** It is 2000, 46 above r7's 1954, while api/authz are
identical. The facts drift pin parametrizes over the copilot-mro checkouts beside it
(`copilot-mro-obsm-r7b` / `-cli` appeared since r7), as the g61 plan's own lesson records.

**Network.**
- The 120 refused lookups before `5b49993` are the comments routes' `DocumentService` constructor
  reaching AWS SSO.
- From `5b49993` the api lane attempts nothing. unit and authz attempt nothing at any commit.
- That confirms "25 → 0" under a stricter, DNS-level guard.
- The api lane fell from ~200 s to ~22 s at `5b49993`.

**xdist.** unit and api+authz under `-n 4` give the serial counts (2089; 1467), so no test fails only
under xdist.

### db lane, run 1 (serial, at `b4d2c33`)

I checked `ps` first: no copilot-mro registries/tenancy run was active. Result: 583 passed / 23 failed /
1 error / 1 skipped / 2 xfailed, rc=1. **That is exactly the implementer's §20 numbers and exactly
the named red set:**
- **20 traceparent reds.** 2 column checks, and 18 one-shot: 17 `UndefinedColumn "traceparent"` and
  1 `42703` inside the RLS case.
- **2 facts-column reds.** `test_answer_outcomes_split_yes_unsure_no_and_null` and
  `test_answer_outcomes_count_a_failed_turn_as_failed_never_unknown`, both `UndefinedColumn
  "turn_outcome"`.
- **The G.61 pair.** 1F `test_exactly_the_eight_identity_relations_cascade_with_a_tenant` and 1E
  `test_the_document_comments_and_their_votes_outlive_the_tenant`.
- **The one skip** is the data-dependent negative control in
  `test_seeded_head_role_dispatch_grant.py:383`.

**The session sentinel printed nothing: no leaked tenant.** Intermediate commits were not run on the
db lane (the brief allows two db runs).

### db lane, run 2 (serial, `-n 0`)

I checked `ps` again first: no copilot-mro registries/tenancy run was active. It ran on a scratch copy of
`b4d2c33` carrying two production mutants and three reviewer probe tests, over
`tests/db/zz_r8/test_r8_db_probes.py` + `tests/db/analytics/test_panels_quality_db.py`: 14 passed /
5 failed, rc=1.

- **Leak check.** The probe minted a REGISTERED scratch tenant and never closed it. The sentinel
  printed `scratch-tenant leak: 1 tenant(s) … t-dblane-3c8688af-r8-planted-leak-ff3e11aab4
  (r8-planted-leak): deleted now`, and the run exited 1. **No leaked tenant remains from either db
  run.** (For the same sentinel under xdist, see P2-5.)
- **A1** (`negative_feedback_drilldown` `JOIN` → `LEFT JOIN`, the live-block filter kept in `ON`):
  RED in `test_a_deleted_chats_question_never_appears_though_its_facts_still_count`. The deleted
  chat's thumbs-down came back with its comment `about VT-SECRET, since deleted`. The unit lane
  cannot see this mutant: full unit lane, `-n 4`, SURVIVED.
- **B1** (`FAILED_TURN_OUTCOME = "error"` → `"success"`): RED in
  `test_answer_outcomes_sql_puts_every_turn_in_exactly_one_series` (`failed 4 != 2`). The unit drift
  pin cannot see it: full unit lane `-n 4` SURVIVED, and api/analytics stayed green.
- **Probe, `top_cited_documents`.** One `doc_uid` cited once with `manual_type 'AMM'` and once with
  `manual_type NULL` (the card-batch fallback's shape) gives **two rows for `D1`**.
- **Pre-existing reds.** The two facts-column reds, as at HEAD.
- **A contaminated probe.** The third probe (an `answer_found` outside the vocabulary) shared the run
  with B1, and both its rows counted as `failed`. That one is reasoned from the SQL, not measured
  (P3-3).

**No commit is red at its own HEAD on unit/api/authz for any reason but the two recorded artefacts.**

---

## Findings, ranked

### P1-1 (sev 1): a user-search term — a name or an email address — is logged at INFO, twice, on every `GET /users/?search=`

**Where:**
- `core/resources/user/services/user_service.py:411-418` (`logger.info("Listing users", …, search=search, …)`);
- `core/resources/user/user_endpoints.py:828-830` (`f"Listing users for tenant: {tenant_id}, search: {search}, …"`).

**Evidence:**
- **The path is live.** dashboard-obsm `GrantOperatorDialog` → `useTenantUserSearch` →
  `SettingsAPI.searchTenantUsers` sends `GET /users/?search=<typed text>`
  (`lib/api/settings-api.ts:498`). The service matches it with `lower(name) LIKE %s OR lower(email)
  LIKE %s`, so what an administrator types is a colleague's name or address.
- **Measured.** Probe: `UserService.list_users("t-1", search="alice.smith@corp.example")`, with the
  DB stubbed, gives the loguru record `Listing users {'tenant_id': 't-1', 'search':
  'alice.smith@corp.example', …}`. utils `4d86ae9` has no value-level address redaction.
- **Why the M-PII-IDS guard passes it.** The guard keys on NAMES. `search` is not in `_PERSONAL`
  (`tests/unit/observability/test_core_logs_name_people_by_id.py:86-89`), and it is not one of the
  declared blind spots. HEAD's unit/api/authz lanes are green with the line in place.
- **The same text rides the URL.** Probe: a `uvicorn.access` record through utils' sinks renders
  `GET /users/?search=alice%40corp.com HTTP/1.1`, while `?token=` renders as `?:redacted`.
  flynapse-otel's `SECRET_PARAMETER_MARKERS` (`withholding.py:331-355`) names `email` but not
  `search`. So the gateway's access line and server spans carry it too: api's / flynapse-otel's half.
- **Owner ruling.** M-PII-IDS says "IDS ONLY… never emails". This is older than the range, but
  `fde8ccd` re-claims the sweep ("no core log line carries an email address"), and r7 did not flag it.

**Fix:**
- Drop `search` from both lines; log `search_given=bool(search)`.
- Pin it BEHAVIOURALLY: capture `list_users` and the route with an address-shaped search, and assert
  the address is absent.
- Estate-side: withhold the `search` query value in flynapse-otel's URL rule, or move the search into
  a body.
- For the guard: the only rule that catches a free-text field is a value-level one. An address-shaped
  string in any log extra or message is withheld in utils' sink.

### P2-1 (sev 1): the M-PII-IDS vocabulary misses the person-bearing names core itself uses

**Where:** `test_core_logs_name_people_by_id.py:86-104` (`_PERSONAL`, `_PERSON_NAME_FIELDS`, `_PERSON_RECORDS`).

**What `fde8ccd` fixed holds:**
- r7's own survivors are RED now, both at once. `pii1` (PUT /users `changes=update_data`) is flagged
  `<record update_data>` at `:1588`. `pii2` (`internal_error(f"…{email}")` on the anonymous door) is
  flagged `email` at `:1758`.
- The sink move kept the exception-text guard working. `f7`
  (`reason=exc.response["Error"]["Message"]` in `tenant_claim_writer`) is RED.

**The vocabulary is still the claim's limit.** In `comment_service.py` `create_comment`,
`current_user` is a PARAMETER holding `attributes.name` and `attributes.email`. Two in-situ mutants
there SURVIVED the full unit, api and authz lanes (`-n 4`):
- `cu2`: `logger.debug("Comment creation request validated successfully", author=current_user)`;
- `an`: `…, author=current_user["attributes"].get("name")`.

The same whole-record line in `get_current_user` (`comments_endpoints.py:186`) is caught. There
`current_user` is BUILT from `token_data.get("email")` in the same scope, so the taint reaches it; a
parameter carries no taint.

**Function-level plants that also pass:**
- `auth_context` or `token_data` logged whole;
- `token_data.get("given_name")`;
- `comment.author_name`;
- `mentions`;
- a parameter named `recipient`, `to` or `invitee_address`;
- a Cognito `Username`;
- `payload`;
- `body.dict()`;
- a cursor row from `SELECT * FROM users`;
- `user_row["name"]`.

"A record the code does not NAME as one" is declared, but these are the names core uses.

**Fix:**
- Add the names core uses: `current_user`, `auth_context`, `token_data`, `claims`, and the name
  fields `author_name`, `username`, `given_name`, `family_name`.
- The complete answer is a type — a `CurrentUser` whose `repr` hides `attributes` — or the value rule
  in P1-1.

### P2-2 (sev 1, tier 2): rows of chats deleted before `d4792d6b` keep the asker's `user_id` and cited titles, and two panels show them

**Where:**
- `core/resources/analytics/panels/quality.py:408` (`f.user_id AS user_id` in `unanswered_questions`);
- `:448` (`max(cited ->> 'document') AS label` in `top_cited_documents`).

**Why:**
- **When anonymisation runs.** Only inside `delete_chat`, from copilot-mro `d4792d6b` on
  (`chats.py:369`). Before it, `delete_chat` left `chat_turn_facts` untouched (the `d4792d6b` diff).
- **Nothing covers the rows already there.** No script in either repo anonymises chats that were
  already deleted: `DELETED_USER_ID` is used only in `chats.py` and the contract module.
- **Where the gap shows.** Take any database where the save-time writer (G.5) or the backfill wrote a
  row for a chat that was then deleted before `d4792d6b` deploys. There:
  - `unanswered_questions` lists that deleted chat's turn under its asker's real `user_id` (since
    `6e17993` its excerpt is NULL);
  - `top_cited_documents` can label a row with a title cited only from deleted chats (an uploaded
    document's title is the user's own).
- **What the tests seed.** The db case seeds only the anonymised shape.
- **What I could not measure.** Whether such rows exist in a real database: no DB read.
- **What does not leak.** The excerpt and the thumbs-down text do not, since `6e17993`.

**Fix (owner, data migration):**
- **A one-off anonymisation of chats that were already deleted**, in the provisioning run:
  `UPDATE chat_turn_facts f SET user_id='deleted-user', session_id=NULL, cited_documents=(… - 'document')
  FROM chats c WHERE c.tenant_id=f.tenant_id AND c.chat_id=f.chat_id AND c.deleted`.
- **A read-side defence in core.** Every `unanswered_questions` row is a saved `No` verdict, so a
  missing live block means a deleted one. Emit `CASE WHEN cb.block_id IS NULL THEN 'deleted-user'
  ELSE f.user_id END`.

### P2-3 (sev 2): `top_cited_documents` is not one row per `doc_uid`

**Why:**
- **The grouping.** `quality.py:453` groups by `doc_uid`, `manual_type` and the uid-less title.
- **Where the second value comes from.** copilot-mro's projection writes `manual_type: None` for the
  SAME `doc_uid` when a turn has no `citations` and falls back to its `document_batch`
  (`chat_turn_facts.py:494-498`). The card's `document_id` is the chunk's `doc_uid`
  (`_cards_core.py:277`).
- **Measured.** db probe: two rows for `D1`. The citation counts are split, and under `LIMIT 20` the
  duplicate can push another document out.
- **The test gap.** The db case covers an anonymised citation that keeps the same `manual_type` only.
- **Claim refuted.** This refutes `7d5144c`'s "one row per document, keyed on doc_uid".

**Fix:** `GROUP BY COALESCE(cited->>'doc_uid', 'title:' || (cited->>'document'))`, with
`max(cited->>'manual_type')` as the kind. Add a db case with the card-batch shape.

### P2-4 (sev 2): the scratch-tenant rule sees only the factory's literal; a forgotten `adopt` and a second registry pass everything

**Where:**
- `tests/unit/harness/test_scratch_tenant_rules.py:23-24` ("A statement that writes a `tenants` row,
  however it is spelled");
- `:116-131` (the importer rule).

**Plants.** Of four tenant writes in one planted db file, the rule caught only the literal (1 of 4).
These passed:
- `sql.SQL("INSERT INTO {} …").format(sql.Identifier("tenants"))`;
- `"INSERT INTO " + "tenants …"`;
- `TenantService.create_tenant(...)`, which is a production mint.

**Mutants that SURVIVED the full unit, api and authz lanes (`-n 4`):**
- **`adopt`:** `test_rbac_roundtrip.py`'s `scratch.adopt(fixed)` replaced by `pass`. This is the
  realistic regression: three db cases mint through `create_tenant` and depend on remembering to
  adopt.
- **`imp`:** `test_scratch_tenants_db.py` imports `from fixtures import scratch_tenants as st`
  (`tests/` is on `sys.path`). That is a SECOND module object with its own `_OUTSTANDING`.

**Why nothing else catches them:**
- The sentinel reads only `tests.fixtures.scratch_tenants._OUTSTANDING`, so it cannot see either.
- The importer rule's `tests.fixtures` branch (`:128-130`) is a no-op (`continue` inside the name
  loop).
- I did not run `adopt` on the db lane: it would leak a real `fixed-<uuid>` row every run.

**Fix: a runtime guarantee rather than a source rule.**
- A db/api conftest fixture patches `TenantService.create_tenant` and the grant pool's `execute` for
  the test session, so any `tenants` INSERT's id is adopted.
- At session end, fail if `sys.modules` holds more than one `*scratch_tenants` module object.

### P2-5 (sev 2): under xdist a leak is swept but never reported, and the run exits 0

**Where:** `tests/conftest.py:171-179` and `tests/fixtures/scratch_tenants.py:180-205`.

**Why:** xdist's worker `pytest_sessionfinish` is a hookwrapper. It copies `exitstatus` into
`workeroutput` BEFORE the conftest sentinel runs (`xdist/remote.py:141-149`). The sentinel's
`session.exitstatus = TESTS_FAILED` and its terminal lines stay on the worker.

**Measured with a no-DB probe.** A registered leak, with the registry's two DB touches pointed at an
in-memory table:
- `-n 0`: rc=1, and the leak is named;
- `-n 2`: rc=0, no line at all, and the id is swept on the worker.

**Why it matters now:**
- The owner has just made `-n 4` the default for non-DB lanes.
- core's api lane mints scratch tenants (the analytics seed).
- So "a leak fails the session and names it" holds only when the lane runs serially.

**Fix:**
- On a worker (`hasattr(config, "workeroutput")`), put the leaks in
  `config.workeroutput["scratch_leaks"]`.
- On the controller, collect them in `pytest_testnodedown` and fail the session, naming each.
- Mark the hook `trylast` (P3-1).

### P3-1: the sentinel runs before pending fixture teardowns on an interrupt, and process death is not "closed"

**Probe (no DB).** A module-scoped fixture held a registered tenant, and a test raised
`KeyboardInterrupt` mid-test:
- the sentinel printed a leak and deleted the tenant;
- the fixture's teardown then found it gone;
- the exit status became 1 (interrupted is 2).

**Why.** Conftest hooks run before `_pytest.runner.pytest_sessionfinish`, which is what tears down
anything still set up. `-x` / `--maxfail` are unaffected: pytest tears everything down on the failing
item.

**Process death.** SIGKILL, the OOM killer or a WSL crash have no session end at all. The registry is
in memory, so the row is only NAMED (the `t-dblane-<session>` prefix plus `created_at`, for owner
item C14). The factory's docstring (`scratch_tenants.py:5-7`) says the process-death case is "closed
here".

**Fix:**
- Mark the hook `@pytest.hookimpl(trylast=True)`.
- Leave a non-OK `exitstatus` alone.
- Reword the docstring.
- A start-of-session sweep of stale `t-dblane-*` rows older than N hours is the only closure for a
  killed run.

### P3-2: the failed-outcome drift pin checks membership, not "failed"

**Where:** `tests/unit/analytics/test_chat_turn_facts_drift_pin.py:835` (`FAILED_TURN_OUTCOME in registry.TURN_OUTCOMES`).

**Evidence:** B1 (`"success"`) SURVIVED the full unit lane and api/analytics. Only the db CTE case
kills it.

**Fix:** pin it as the one outcome that is not the success spelling, or ask copilot-mro for a named
constant.

### P3-3: the five-series partition has no catch-all

**Where:** `quality.py:182-186`.

**Why it holds today, and how it breaks:**
- It holds only because copilot-mro's `chat_turn_facts_answer_found_check` (present since
  `0775cc3d`) limits `answer_found`.
- Suppose a verdict is added to `ANSWER_FOUND_VALUES` and to the backfill's mirror. The drift pin
  stays green, and those turns vanish from all five series.
- This is reasoned from the SQL: my measuring probe was contaminated by B1.

**Fix:** make `unknown` the catch-all: `NOT failed AND answer_found IS DISTINCT FROM ALL('{Yes,Unsure,No}')`.

### P3-4: the unit live-block rule reads a spelling

**Where:** `tests/unit/analytics/test_panels_read_only_live_chat_blocks.py:23-35`.

**Evidence:**
- Decoy `AND (cb.deleted = false OR cb.deleted)` on `unanswered_questions` SURVIVED unit, api and
  authz (`-n 4`).
- A1 (`LEFT JOIN`) also survives unit.
- The db case is the real guard: measured for A1, reasoned for the decoy.

**Fix:** say in the unit rule's docstring that the db case is the real guard.

### P3-5: the panel cache serves a deleted chat's excerpt, giver and comment for up to 5 minutes

**Where:** `panel_service.py:134-162` caches rows for `analytics_cache_ttl_seconds = 300`
(`core/config.py:73`), in a SHARED cache in production.

**Why:** copilot-mro's `delete_chat` does not invalidate core's `analytics:panel:*` keys.

**Fix:** state it, or give a delete a per-tenant generation token that the cache key reads.

### P3-6: F10 residuals (probe of `document_answer`)

**Where:** `core/resources/document_viewer/services/storage_locations.py:52,57-66`.

**Kept:**
- scheme-less and protocol-relative AWS URLs;
- S3 access-point and object-lambda ARNs. `_S3_ARN` requires `s3:::`, so "ARNs" means bucket and
  object ARNs only;
- boto's `{"Bucket","Key"}` (the `Key` is kept);
- camelCase `s3Key` / `objectKey`;
- a list under `s3_key`;
- a MinIO URL inside text in a pointer field.

**Declared vs not.** Only "a bare key under an unlisted name" and "percent-encoded twice" are declared.
No live row is shown to carry any of these.

**`CatalogItem` holds:**
- M8 (`repr` = `dict(self)`) is RED ×2.
- M8b (`_row_to_item` builds a plain dict) is RED ×2.
- A copy is a plain dict, which is declared.

### P3-7: Cognito sweep residuals

**Where:** `test_cognito_calls_are_spanned.py:106, :22-39`.

**Plants that pass:**
- `object.__getattribute__(c, "admin_delete_user")`, with the name at index 1;
- an imported constant;
- a class constant.

**Unpinned declared limits.** The docstring says each declared limit is "a pinned plant below". The
paginator-after-span limit and the helper-outside-core limit have no plant.

**Kills.** `cog` (`_BY_NAME` reduced to `getattr`) is RED ×3. No such call exists in core today.

### P3-8: claim wording

- **`93caffd`.** It says the operator CRUD tests pin a refusal "without the key being echoed". They
  assert the VALUE is absent and the error type (`test_operator_crud.py:711-713`). M4 (loc passed
  through) is RED only in `test_validation_answers_quote_no_values.py::test_an_extra_fields_key_is_not_echoed_in_loc`.
- **`7d5144c`.** "one row per document" (P2-3); "a drift pin on … the failed outcome string" (P3-2).
- **Scratch-tenant rule.** "however it is spelled" (P2-4).

### P3-9: hygiene-audit residue, and the concurrency rule's scope

**Not added.** The audit's core item 4 also asked for:
- `OTEL_SDK_DISABLED` defaulting to true — not added and not mentioned;
- the refusing network guard — its deferral is declared in `test_no_live_service_pins.py`.

**Rule scope.** The README scopes "never concurrently with copilot-mro's tenancy lanes" to the db lane.
The api lane also mints scratch tenants (the analytics seed) and reads every tenant
(`test_operator_catalog.py:615`).

### P3-10: stale text

`tests/db/analytics/test_panels_quality_db.py:3-4` still says "the writer is a later stream's task".

### P3-11: observations, older than the range

- **Caller text at DEBUG.** `comment_service.py:302-305` logs `mentions=request.mentions` and
  `tags=request.tags`.
- **Spend by a deleted chat.** The per-user spend panel (`cost.py:198-217`) reads `llm_usage`, which
  `delete_chat` does not anonymise. A deleted chat's spend stays attributed to its user, by name or
  address. Owner question: does M-FACTS-ANONYMISE's "per-user panels show it as a deleted user" extend
  to spend?

---

## What I tried to break and could not

- **The question-text joins.**
  - M2 (the `unanswered_questions` filter dropped) is RED in unit.
  - A1 and B1 are RED in db.
  - Every other `chat_blocks` reader filters `deleted = false`.
  - `feedback_received_over_time` only counts.
  - No other core panel reads comment or block text, apart from the owner-only, flag-dark
    improvement findings.
- **The partition on the real relation holds.** `failed` is `IS NOT DISTINCT FROM 'error'`, a
  boolean that is never NULL, and the CHECK closes `answer_found`.
- **`(extra field)` is not a dashboard break.**
  - dashboard-obsm reads `msg` / `message` only (`fetch-utils.ts` `describeErrorDetailItem`,
    `improvement-api.ts` `describeDetailItem`). `loc` appears only in two test fixtures.
  - telegram-bot reads the `loc` of its own settings errors only.
  - api-obsm has no consumer.
- **Signup.** A `users_pkey` collision gets the same refusal (M5: RED). The catch wraps the one
  `users` INSERT only. A fresh domain-minted tenant cannot hit `users_pkey` (the key is
  `(tenant_id, user_id)`).
- **The ingest.** The refusal logs the door and ids (M6: RED ×2). The client IP is used only as
  Turnstile's `remoteip`.
- **Automations `kind`.** The refusal is fixed (M7: RED ×2).
- **Standalone launch.** M9 is RED. With `log_config=None`, access records reach utils' sinks, and
  `?token=` renders `?:redacted`.
- **Router sweep.** r7's `f8` on POST /roles is RED. 9 of 11 of my plants are caught. The misses: an
  unnamed `traceback.format_exc()` (owned by the traceback test), and a helper imported from another
  module (none exists).
- **G.117.** `g117b` (the only `import utils` moved under `TYPE_CHECKING`) is RED.
- **Hygiene pins.** H4 is RED. From `5b49993` there are zero outbound attempts.
- **Both db runs left no leaked tenant.**

## What I did not test / could not reproduce

- **Implementer numbers.** The "29 of 33 plants caught" (r7's plant file is not here), and the exact
  "25 outbound connects". My guard counts DNS attempts: 120 before `5b49993`, 0 after.
- **`7d5144c`'s db-only mutants.** The `not_recorded` bucket and the clarification denominator are
  ASSERTED from the implementer's record.
- **Two reasoned results.** The vocabulary-growth probe was contaminated. The decoy's db kill is
  reasoned, not run.
- **Live data.** Whether a real database holds un-anonymised rows of deleted chats (P2-2) or the F10
  spellings (P3-6): no DB read.
- **The `2f972e4` / `3f5508a` flakes.** Not re-created. Both files are green at every commit.
- **SIGKILL mid-fixture.** Not executed, because it would leave a real row.
- **Tools.** The coordinator's mid-review tools were used for every survivor re-run: xdist `-n 4` and
  `mutant.sh`. In this symlinked workspace the full unit lane always exits 1 on the two artefacts, so
  `mutant.sh` scores any unit-lane mutant KILLED. The first six `unit-*` results were that artefact.
  The re-runs deselect the pair (baseline 2089 passed, rc=0).

---

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state | Answers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r8-01 | core | `quality.py:337-338,413-414` | both question-text joins read live blocks; drilldown INNER | M-FACTS-ANONYMISE | M2 RED (unit, 1); A1 RED (db): deleted chat's comment returned | `test_panels_read_only_live_chat_blocks.py`; `test_panels_quality_db.py::test_a_deleted_chats_question_never_appears…` | yes, both halves | — | 0 | F1 | SETTLED (unit half spelling-only, r8-12) | new (`6e17993`) |
| r8-02 | core | `quality.py:408,448` | read side trusts delete-time anonymisation | M-FACTS-ANONYMISE | no retroactive anonymisation in either repo | none | n/a | 1 | 2 | F1 | OPEN, P2-2 | new |
| r8-03 | core | `quality.py:179-200` | `failed` series; five exclusive series | M-FACTS-FAILURES | B1 RED (db CTE, `failed 4 != 2`) | `test_answer_outcomes_sql_puts_every_turn_in_exactly_one_series` | yes | — | 0 | F2 | SETTLED | new (`7d5144c`) |
| r8-04 | core | `quality.py:182-186` | no catch-all series | — | reasoned; the CHECK holds it today | none | n/a | 2 | 1 | F2 | OPEN, P3-3 | new |
| r8-05 | core | `quality.py:71-77,241-249` | `facts_version` 0 → `not_recorded`; out of the clarification denominator | M-FACTS-FAILURES | db case green at HEAD | `test_a_turn_that_saved_no_block_counts_only_where_its_row_holds_a_fact` | impl only | — | 1 | F2 | ASSERTED | new |
| r8-06 | core | `quality.py:444-456` | one row per `doc_uid` | anonymised citations join their row | db probe: two rows for one `doc_uid` | `test_a_deleted_chats_citations_join_their_documents_row` (same `manual_type` only) | survivor shown | 2 | 1 | F2 | REFUTED, P2-3 | new |
| r8-07 | core | `test_chat_turn_facts_drift_pin.py:835` | failed outcome pinned by membership | — | B1 survives full unit + api/analytics | same | survivor shown | 2 | 1 | F2 | PARTIAL, P3-2 | new |
| r8-08 | core | `user_service.py:411-418`; `user_endpoints.py:828-830` | user search term logged at INFO | older than range | probe: the address in the record; access line too | `test_core_logs_name_people_by_id.py` (passes it) | live survivor | 1 | 1 | F1 | OPEN, P1-1 | r7-02 / M-PII-IDS |
| r8-09 | core | `test_core_logs_name_people_by_id.py:86-104` | name vocabulary | M-PII-IDS | `cu2`, `an` survive unit+api+authz | same | survivors shown | 1 | 1 | F1 | OPEN, P2-1 | r7-02 |
| r8-10 | core | `tests/_log_sinks.py`; PII guard | one sink derivation shared by both guards | r7-P2-1 | r7 `pii1` + `pii2` RED; `f7` RED after the move | both log guards | yes | — | 0 | F1 | SETTLED for r7's survivors | r7-02 |
| r8-11 | core | `test_tenant_service.py:1238-1360`; `tenant_service.py:1011-1020` | teardown pins restated as spellings; owner question | r7-P2-2 | still-unseen plants pinned; claims corrected | same | impl | 1 | 2 | F2 | OPEN (owner design question) | r7-10 |
| r8-12 | core | `test_panels_read_only_live_chat_blocks.py:23-35` | structural rule on a spelling | — | decoy + A1 survive unit | same | survivors shown | 2 | 1 | F2 | PARTIAL, P3-4 | new |
| r8-13 | core | `test_router_error_disclosure_sweep.py:1196-1383` | builders by import alias / partial; `yield`; chained causes | r7-P2-3 | r7 `f8` RED; 9/11 plants | same | yes | — | 0 | F1 | SETTLED | r7-18 |
| r8-14 | core | `storage_locations.py:180-193`; `document_service.py:386` | `CatalogItem` renders `document_answer` | r7-P2-4 | M8 RED ×2, M8b RED ×2 | `test_storage_locations_stay_out_of_logs.py` | yes | — | 0 | F1 | SETTLED (copies declared) | r7-09 |
| r8-15 | core | `logging_endpoints.py:93-116` | ingest refusal logs the door and ids | M-PII-IDS | M6 RED ×2 | `test_ingest_refusal_names_no_address.py` | yes | — | 0 | F1 | SETTLED | r7-26 |
| r8-16 | core | `user_service.py:537-548` | any unique violation on the signup door → `SIGNUP_NOT_COMPLETED` | M-SIGNUP-ORACLE | M5 RED | `test_signup_answers_no_account_existence.py::test_a_known_account_subject_is_the_same_refusal` | yes | — | 2 | F1 | SETTLED | r7-04 |
| r8-17 | core | `http_errors.py:68-98,198` | `(extra field)` in `loc` (contract change) | r7-P3-2 | M4 RED (routing test only); no dashboard consumer | `test_validation_answers_quote_no_values.py` | yes | 3 | 1 | F1 | SETTLED (claim wording, P3-8) | r7-13 |
| r8-18 | core | `automations_endpoints.py:196-230` | fixed `KIND_REFUSED` | r7-P3-2 | M7 RED ×2 | `test_automation_endpoints.py::test_create_refuses_every_kind_but_chat` | yes | — | 0 | F1 | SETTLED | r7-13 |
| r8-19 | core | `fastapi_app.py:327-345` | standalone `log_config=None` | r7-P3-7 | M9 RED; probe `?token=` → `?:redacted` | `test_standalone_uvicorn_leaves_logging_to_utils.py` | yes | — | 0 | F1 | SETTLED | r7-07 |
| r8-20 | core | `storage_locations.py:48-66,144-177` | F10 spellings | r7-P3-1 | probe: 6 shapes kept | `test_document_answer_names_no_storage_location.py` | impl | 2 | 1 | F1 | PARTIAL, P3-6 | r7-20 |
| r8-21 | core | `test_entrypoints_import_utils_first.py:73-100,165` | main-guard spellings; dead imports | r7-P3-4 | `g117b` RED; `g117` (self) RED ×3 | same | yes | — | 0 | F1 | SETTLED | r7-22 |
| r8-22 | core | `test_cross_repo_reads_name_their_checkout.py:886-915` | `_root` pin fails, never skips | r7-P3-9 | read; green at every commit | same | impl | 3 | 1 | F3 | ASSERTED | r7-16 |
| r8-23 | core | `test_cognito_calls_are_spanned.py:103-200` | folded names; by-name reaches | r6-F7 | `cog` RED ×3; 3 plants pass; 2 declared limits unpinned | same | yes (partial) | 3 | 1 | F1 | PARTIAL, P3-7 | r6-F7 |
| r8-24 | core | `test_refusal_is_the_only_echoed_value_error.py:398-420,530-570` | census: tuple unpack, `type()`; dynamic shapes declared and pinned | r7-P3-5 | read; plants pinned | same | impl | 3 | 1 | F1 | ASSERTED | r7-19 |
| r8-25 | core | `tests/fixtures/scratch_tenants.py`; `tests/conftest.py:171-179` | registered before INSERT; sentinel fails and names | audit §4 | db run 2: planted leak named, deleted, rc=1 | `test_scratch_tenants_db.py`; `test_scratch_tenant_rules.py` | yes (serial) | — | 0 | F2 | SETTLED serially | audit §4 |
| r8-26 | core | `tests/conftest.py:171-179` | sentinel under xdist | — | `-n 2`: swept, rc=0, no report | none | survivor shown | 2 | 1 | F2 | REFUTED under `-n`, P2-5 | new |
| r8-27 | core | `tests/conftest.py:171`; `scratch_tenants.py:5-7` | hook order; process death "closed" | — | Ctrl-C probe: false leak, exit 2→1; SIGKILL reasoned | none | probe | 2 | 1 | F2 | OPEN, P3-1 | new |
| r8-28 | core | `test_scratch_tenant_rules.py:23-24,116-131` | one writer of `tenants` rows under `tests/` | audit §4 | `adopt` + `imp` survive unit+api+authz; 3 of 4 plants pass | same | survivors shown | 2 | 1 | F2 | REFUTED as stated, P2-4 | new |
| r8-29 | core | `tests/conftest.py:156-168`; `test_router_error_disclosure_sweep.py:508` | EC2 pin; in-memory cache; comments lookup stubbed | audit §3.3 | H4 RED; api lane 0 outbound at HEAD | `test_no_live_service_pins.py` | yes | — | 0 | F2 | SETTLED (OTEL + guard owed, P3-9) | audit §3.3 |
| r8-30 | core | `panel_service.py:134-162`; `core/config.py:73` | 300 s panel cache | — | read | none | n/a | 2 | 1 | F1 | OPEN, P3-5 | new |
| r8-31 | core | `test_events_endpoint.py`; `test_chat_quality_endpoint_contract.py`; `test_operator_crud.py` | pinned clock; operator code redraw | flakes | green at every commit | same | impl | — | 1 | F2 | ASSERTED | r7 flake |
| r8-32 | core | range | every commit at its own HEAD | plan §2.4 | table above; HEAD = implementer's numbers under utils `4d86ae9` | the lanes | n/a | — | 1 | F2 | SETTLED | r7-24 |
| r8-33 | core | `test_panels_quality_db.py:3-4`; `scratch_tenants.py:5-7`; `93caffd` message; `test_cognito_calls_are_spanned.py:30`; README concurrency rule | stale or overclaiming text | — | read | none | n/a | 3 | 1 | F3 | OPEN, P3-8/9/10 | r7-25 |
| r8-34 | core | `comment_service.py:302-305`; `cost.py:198-217` | caller text at DEBUG; spend attribution after chat delete | older | read | none | n/a | 3 | 2 | F3 | OPEN (observation / owner question), P3-11 | new |

## Open claims, tier 2 first

**Tier 2:**

1. **r8-02 (P2-2).** A one-off anonymisation of chats already deleted before `d4792d6b` (the owner's
   provisioning run). Optionally, the read-side `CASE WHEN cb.block_id IS NULL THEN 'deleted-user'` in
   `unanswered_questions`.
2. **r8-11 (r7-10, carried).** Tenant teardown by privilege: no `DELETE` on `tenants` for the app
   roles, teardown through a definer function. The owner's design question.
3. **r8-34 (P3-11).** Does M-FACTS-ANONYMISE's "per-user panels show it as a deleted user" extend to
   `llm_usage` spend?

**Tier 1, in the order to fix:**

1. **r8-08 (P1-1).** Drop `search` from both log lines; pin with a behavioural capture. Estate:
   withhold `search` in flynapse-otel's URL rule, or move it to a body.
2. **r8-09 (P2-1).** Vocabulary for `current_user` / `auth_context` / `token_data` / name fields, or a
   type, or a value-level address rule in utils' sink.
3. **r8-26 (P2-5), r8-27 (P3-1).** Make the sentinel xdist-aware (`workeroutput` →
   `pytest_testnodedown`) and `trylast`. This is needed now that `-n 4` is the default.
4. **r8-28 (P2-4).** A runtime adoption shim for `create_tenant` / grant-pool INSERTs; a
   single-module check.
5. **r8-06 (P2-3).** Group `top_cited_documents` by `doc_uid` alone.
6. **r8-07, r8-04, r8-12, r8-30, r8-20, r8-23.** Pin failed as the non-success outcome; a catch-all
   series; state the unit rule's limit; state or fix the cache window; the F10 and Cognito residuals.
7. **r8-33, r8-05, r8-22, r8-24, r8-31.** Wording; the ASSERTED rows need a reviewer-seen red before
   they are tier 0.

**Tier 0 settled in this range:** r8-01, r8-03, r8-10, r8-13, r8-14, r8-15, r8-18, r8-19, r8-21,
r8-25, r8-29 — each seen RED here when its property was removed. r8-16 (the signup oracle, tier 2) and
r8-17 (the `loc` contract, tier 1) are SETTLED too. r8-32 is measured, tier 1.
