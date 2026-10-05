# Database users: consolidation (owner decisions 22–26)

**Status (2026-09-29, evening):** the owner has answered all five decisions, all yes.
- **Steps 1–2: MERGED and PUSHED.** Pushed as utils `b3edfbd` (0.1.41), core `bcdccb3`, shift-optimizer `3e07609`,
  copilot-mro `3f46076d` and api `b29d7be`. The owner's `.env` steps and the utils 0.1.41 publish are listed under
  step 2's notes.
- **Step 3 (Terraform):** approved and unpushed (`iac-roles` `db-roles-tf` @ `a47c0fb`). It waits on the owner's iac
  `obs-merge` → `main`.
- **Step 3 branch PUSHED** (owner: yes, 2026-09-29) as `origin/db-roles-tf` `a47c0fb`. A branch push triggers no CI.
  Merging into `main` still waits on the owner's iac `obs-merge` → `main`.
- **Step 3 MERGED into iac `main` (owner: merge now, 2026-10-01)** as `ff1cb5c`, pushed; iac tests 325 passed,
  `terraform fmt -check` clean. Not applied (owner: no apply for now). `main`'s plan check fails until the owner
  creates the AWS secret `api/postgres/passwords`.
- **Step 4: the owner's database side is DONE (2026-09-29 evening).**
  - The owner created `flynapse_inspect` (`LOGIN BYPASSRLS`, `pg_read_all_data`, `default_transaction_read_only=on`).
    Its password is `POSTGRES_INSPECT_PASSWORD` in `copilot-mro/.env`.
  - `.mcp.json` now logs in as `flynapse_inspect`.
  - The owner ran `REVOKE pg_read_all_data FROM flynapse_readonly`. On `copilot_mro_test`, readonly now reads exactly
    its 19 allowlisted relations (verified).
  - The code side is in flight: `db-roles-s4` in `utils-inspect` and `copilot-mro-inspect`, brief `s4-brief.md`. It
    covers:
    - `INSPECT_ROLE` in `utils.db_roles`;
    - repointing the cross-tenant tests and fixtures from readonly to inspect;
    - the extra-SELECT report becoming a failing finding;
    - a guard that no service module names the inspection user;
    - docs.
  - The order the plan asked for (repoint, then revoke) ran the other way. So any test that read beyond the 19
    through readonly is red until this batch merges.
- **Step 4 CLOSED and PUSHED (2026-09-30):** utils `5e9ae2e` (0.1.42), copilot-mro `1bfe2e70`, api `e449c7d`.
  - Built: `INSPECT_ROLE` and `inspect_credentials()`; the cross-tenant fixtures and the corpus door on
    `flynapse_inspect` (failing, not skipping, without its password); `flynapse_readonly`'s extra reads, ANY role
    membership (inheritance on or off, predefined roles included) and any default privilege naming it are findings
    that fail `--verify-only` and roll a provisioning run back; a guard that no service module, env template or
    tracked deployment file names the inspection user; the runbook's three owner commands.
  - Review history: one review (the membership gap), two fix rounds on fresh agents, a re-review. The post-merge gate
    found one red no worktree could see (below, Lessons); fix round 2 closed it before the push.
  - Publishing waits until all code changes are final (owner, 2026-09-30: all is dev). The next verify on the
    protected databases runs the new membership and default-privilege checks for the first time there.
- **Step 5 done except the owner's later cleanup (2026-09-30):** built, reviewed (one review, two fix rounds, a
  re-review), and the owner sheet proven end to end on throwaway clusters
  (`.superpowers/sdd/db-roles-consolidation/s5-owner-sheet.md`). The owner ran sheet steps 1–6; the controller
  verified every check and started the bot. Phoenix: identical fingerprint (65 tables, 1,874 rows), nothing
  foreign-owned, healthy and connected as `phoenix` to `phoenix`, no collector auth errors. The bot: connected as
  `telegram_bot_app` only, nothing in its database owned by anyone else (`public` included), its suite 2,473 passed
  as that user. Merged and pushed: copilot-mro `a90db4cd` (whole-tree non-db 15,146 passed), telegram-bot `95dc9f7`
  (with the README's `public`-owner check; suite 2,475 passed). Left: sheet step 8, the owner's, after a few healthy
  days.
- **Step 6 merged and pushed (2026-10-01); the owner's 4c is left:** built, reviewed by area, two fix rounds (pooled
  connections reset on release; client-side password hashing; verify requires the query user's settings exactly; the
  gate refuses `pg_logical_emit_message`), both re-reviews clean. The owner ran sheet steps 1–3 and the 4b verify
  from the merged code (both databases `rc=0`, query extra privileges 0). Merged, gated and pushed: utils `6b3e6a9`
  (0.1.43), copilot-mro `58f05103`, api `8be2b6c`. Left: the owner's 4c (rebuild the api container, then the
  sheet's two checks). No AWS deploy until App Runner gets `POSTGRES_QUERY_PASSWORD`.
- **Step 7 building (2026-10-01), started before the owner's 4c** (4c checks step 6 in the live container; step 7's
  build does not depend on it, and a step-6 fix from 4c would merge into step 7's branch): B14's `delete_tenant`
  definer with every tenant-delete caller routed through it, the grant user's `tenants` DELETE/TRUNCATE revoked,
  decision 24's PUBLIC revokes (`lo_*`, extension functions with the app user's grant-backs, TEMPORARY), a verify
  finding for each, and the owner's sheet; proven on a throwaway built from code. Branches `db-roles-s7` in
  copilot-mro and core.
- **Step 7 built and reviewed (2026-10-01).**
  - **The build** (copilot-mro `c56a9230`, core `bed5952`): the sheet proven forward, rolled back and forward again,
    with both order hazards shown; 15 of 15 mutants killed; lanes green. The first implementer retired past the context
    cap at the WSL crash, and a fresh agent finished it.
  - **Review A (the code), 0 Critical, 2 Important:**
    - `--verify-only` misses a membership that is not inherited (`INHERIT FALSE`), through which the app user could
      take on the grant role and delete a tenant;
    - the tenant-lifecycle E2E asserts the grant role still deletes, so it fails after step 3.
  - **Review B (the sheet), 0 Critical, 3 Important:**
    - step 2's first check cannot run on this box as written;
    - the sheet never stops for an RDS probe;
    - on RDS, step 3 cannot succeed: the master user is not a superuser, and the `lo_*` and extension functions are
      owned by `rdsadmin`. Because the step is all-or-nothing, B14's `tenants` revoke would never land there either.
  - **The owner's rulings (2026-10-01):**
    - the app user keeps TEMPORARY on `copilot_mro_test` only; every other database loses it for every role.
    - RDS: split it and report the rest. B14's `tenants` revoke runs on its own and always lands. PUBLIC's reach
      revokes only what PUBLIC holds and the role can revoke. On a cluster where the provisioning role is not a
      superuser, the functions owned by `rdsadmin` are named, accepted findings, and the sheet stops for an RDS probe
      before step 3 runs there.
  - **Next:** a fix round with those rulings and both reviews' findings is running. Then a scoped re-review and the
    sheet to the owner. Before step 7 merges, merge the moved mainlines into its branches.
  - **Fix round progress (2026-10-01 evening).** Reading the 4,000-line provisioning script cost each agent most of its
    context, so the round runs in narrow parts from one design file (`~/.claude/scratch/db-roles/s7-fix1/DESIGN.md`)
    and symbol indexes:
    - part 1: the definer's docstring, the E2E preflight, two stale sentences;
    - part 2: PUBLIC's reach revokes only what PUBLIC holds and this role can revoke, one statement per routine; on
      RDS, functions a superuser owns are named accepted lines; every role is swept for undeclared definers;
    - part 3a: the definer-owner precondition (rc 2 before any write) and the two transactions (B14's revoke lands
      even if PUBLIC's reach rolls back), proven live on a throwaway;
    - core M6: a live test of the mint-receipt compensation through the definer;
    - part 3b: TEMPORARY on `copilot_mro_test` only, membership-aware checks with the RDS creator edge, the definer
      body compared, PostgreSQL 16's SET check (`cde5b722`);
    - part 4a: the owner's stand-in in the definer census (`62974389`); readonly reported once (`4d249ef5`); the sheet
      rewritten and re-proven forward, rollback, forward on a throwaway (`dffb96c5`);
    - part 4b: the mainlines merged into both branches (copilot-mro `70f3dcd0`, core `be055893`); the stand-in excluded
      from all six holder censuses, each naming it on an accepted line (`e50a3613`; controller ruling below); the
      RDS-shaped runs (a master not named `postgres`, PostgreSQL 16 and 15: verify 0 findings, 183 and 180 accepted
      lines); the sheet's RDS section filled;
    - part 4c: the sheet's proof at the merged tips (nothing moved), the build's six live mutants killed, the lanes
      green (step 7's live tests on a step-7 throwaway, since the shared test database has not had step 3 yet), one
      test fix (`c2be47d8`), and the consolidated report;
    - the scoped re-review, in two lenses, both FIX FIRST (2026-10-01, night):
      - **Lens A, the code, 0C/1I/2M.** The `tenants`, `user_erasures`, append-only-log and TEMPORARY censuses still
        read inherited privilege only. A role granted `pg_write_all_data WITH INHERIT FALSE` passes verify while able
        to empty `tenants`. Three conditions also have no test, and review A M4's no-user-trigger pin was never built.
      - **Lens B, the sheet, 0C/1I/4M.** On RDS for PostgreSQL 15 and later, AWS grants `rds_superuser`
        `pg_read_all_data` and `pg_write_all_data`. The holder censuses count it, so step 3 commits nothing there,
        and the sheet's RDS probe cannot see why. There are also four text fixes.

      Everything else held: every number the sheet quotes, both order hazards, and the two transactions.
    - **The owner's ruling (2026-10-02):** accept `rds_superuser` on one narrowly pinned line. It covers only its reach
      through those two predefined roles. These stay findings:
      - a direct grant to it;
      - any other path;
      - any other member of it but the owner;
      - any other role reaching the two predefined roles.
    - fix round 2:
      - **Part 2a: done (2026-10-02).** copilot-mro-s7 `2c0487bc`, core-s7 `4cf6487`. It built:
        - membership reach in every holder census;
        - the `rds_superuser` line;
        - the three tests;
        - the trigger pin.

        Step 7 from scratch at these tips moved no number the sheet quotes. On an RDS-shaped PostgreSQL 16, step 3
        lands with 184 accepted lines, 10 of them `rds_superuser`'s, and the three controls are red.
      - **Part 2b: done (2026-10-02).** copilot-mro-s7 `ab0f40f7`, core-s7 unchanged at `4cf64875`. It brought the
        sheet to the code: the RDS section, the four text fixes, the census's membership term, and a new read-only
        census row for user triggers in `tenants`' delete reach. It also fixed the TEMPORARY notice so it no longer
        contradicts an accepted line. It re-proved the sheet at the new tips: the local shape forward, rolled back and
        forward again, every quoted number reproduced. On an RDS-shaped run, step 3 lands with 184 accepted lines.
    - the scoped re-review of fix round 2, in two lenses (2026-10-02):
      - **Lens B, the sheet: SHEET-READY, apart from two Minors.** Its own run reproduced every number.
        - Where the master owns the database (the usual RDS shape), verify prints 192, not 193. The owner holds
          TEMPORARY by owning the database, so no accepted line is printed for it.
        - A column-level `UPDATE` is invisible to the holder censuses and to the sheet's probe.
      - **Lens A, the code: FIX FIRST, 0C/1I/2M.**
        - The `rds_superuser` line is pinned to the role's name only. A hand-made `rds_superuser`, even one that can
          log in, is accepted on a server where the run could revoke its data roles.
        - The writers censuses print a remedy that does nothing for a holder reaching the privilege through a
          membership.
        - One still-finding has only a text pin.

        It also found a gap older than step 7: no census sees column privileges. A column `UPDATE` on
        `user_operators` granted to the app role passes verify, and that grant then lets the role rewrite every grant
        in its tenant.
    - **Fix round 3 (ruled 2026-10-02; waits for the owner to allow new agents):**
      - the `rds_superuser` line accepts only where the run's role is no superuser, `rds_superuser` cannot log in, and
        `rdsadmin` exists as a superuser;
      - the right remedy text;
      - one live case for the still-finding;
      - column privileges in the writers censuses and the app role's check, and in the sheet's probe and census;
      - both RDS shapes in the sheet's counts;
      - a unit case for the trigger pin's `SET NULL` hop.

      It re-proves the sheet. A scoped re-review follows, then the sheet goes to the owner, with step 6's 4c first.
    - **Fix rounds 3 to 7 (2026-10-04, after the owner lifted the hold).** Docker Desktop was stopped on the host
      all day, so every throwaway was a user-space PostgreSQL 16 cluster unpacked from Ubuntu's own packages.
      - **Round 3** built what was ruled and re-issued the sheet. Lens B found it SHEET-READY, with every quoted
        number matching on the local shape and on three RDS shapes (A: the master is `postgres`; B: another master,
        `postgres` owns the database; C: the master created the database).
      - **Round 4** turned the last must-hold reads to the table level and gave a PUBLIC grant a remedy that names
        PUBLIC.
      - **Round 5** fixed round 4's quoted-name regression, and reports the read-only and grant roles' writes
        anywhere.
      - **Round 6** added an ownership census: any relation owned by a role other than `postgres` is a finding.
      - **Rounds 4 to 6 each turned up one more privilege class verify never read**, the last being schema and
        database ownership and CREATE on a schema. So **round 7** wrote a matrix of every PostgreSQL 16 privilege
        against every role, with the check that reads each cell. It found 21 holes. Part 7a closed 10, part 7b
        closed most of the rest, and part 7c (running) closes the last.
    - **Controller ruling (2026-10-04), confirmed by the owner the same night:** `rds_superuser`'s reach through
      `pg_read_all_data` and `pg_write_all_data` is ONE accepted line, as the owner's ruling words it ("one narrowly
      pinned line"), printed only while the premise holds.
      - Until now each census printed a line per holding: 10 lines, and about 460 per database had the last matrix
        cells closed the same way.
      - Where the premise fails, it is one finding. Any other path stays a finding.
    - **Controller ruling (2026-10-04):** nothing is accepted in silence. What the RDS master owns or holds is a named
      accepted line, like the older ones.
    - **Parts 7c to 7e (2026-10-04, evening; Docker Desktop back on, the shared cluster untouched).**
      - **7c** put `rds_superuser`'s data-role reach on one accepted line. It accepted the inspection user by its shape
        (decision 23: never named), and made any stray superuser a finding. It also closed the last two cells: a role
        the script does not manage reading or writing any relation.
      - **7d** merged the mainlines into the branch, so step 3 and the window run the code that will land. It re-issued
        the sheet and the census (FI-B: the owner of `tenants` is listed). It re-proved every block: 117 local checks
        and 215 on RDS.
      - **The controller read the shared dev cluster's roles,** read-only and never `copilot_mro`:
        - only `postgres` is a superuser;
        - `flynapse_inspect` is exactly the shape;
        - `phoenix` and `telegram_bot_app` hold nothing on `copilot_mro_test`.
        So step 0's verify there should print the inspection line alone.
      - **A three-lens re-review** (the checks; the tests; the sheet, re-proven independently) found:
        - one real hole: membership in the server-file roles (`pg_execute_server_program` and its two siblings) was
          read by no census. A role holding one runs OS commands as the server, while verify reads clean;
        - one wrong sentence in the sheet.
      - **7e** closed both. It also made the inspection fake read its SQL, and added the sheet's last corrections:
        `--no-ff` at the merge, and the inspection line's count may differ by database. Re-proof: 121 local checks
        and 216 on RDS.
    - **7e's scoped re-review: MERGE-READY, OPEN 0, SHEET READY (2026-10-04, night).** Its re-proof matched 7e's
      exactly: 121 local checks, 16 passes compared, 216 on RDS. A `phoenix` given `pg_execute_server_program` is now
      a finding, and the printed remedy clears it. Three Future Improvements (FI-R7E-1 to FI-R7E-3).
    - **SHEET READY (2026-10-04, night):** the controller filled the two tips (`copilot-mro-s7` `767cdaa6`, `core-s7`
      `be14dd81`) and lifted the banner; nothing else changed.
    - **Run (2026-10-04/05, night):**
      - the owner ran the sheet's steps 0 and 1 on both databases;
      - the controller merged `db-roles-s7` (core `f8f9f67`, copilot-mro `a5374567`);
      - the API was restarted on the merged code, and 2b's two checks pass;
      - the owner ran step 3 on both databases. Each privilege snapshot's diff is exactly the sheet's, and step 2's
        check 2 passes again after the revoke.
    - **Step 6 is closed:** both of its 4c checks pass. A chat turn's SQL ran as `flynapse_query` through the running
      API.
    - **Merged and pushed (2026-10-05):** core `master` `f8f9f67`, copilot-mro `langgraph-merge` `1f12e334` (step 7,
      plus user erasure's D8 copilot-mro half). The post-merge test run was green apart from the known failures of
      the sibling-checkout test family. The step's worktrees and branches are removed, and the rounds' Future
      Improvements are written below.
    - **Next:** step 8 (decision 27).
- **Step 8 built and reviewed (2026-10-05): decision 27.** Branch `db-roles-s8` in `copilot-mro-s8`, from
  `langgraph-merge` `1f12e334`, tip `05541e4a`.
  - The provisioner creates `flynapse_readonly` (LOGIN, BYPASSRLS, NOINHERIT, its password as a SCRAM verifier) only
    when `POSTGRES_READONLY_PASSWORD` is supplied, then grants exactly its table list. Absent with no password is a
    note, not a finding. An existing user is left as it is, and its password is never reset. An owner that cannot
    create a BYPASSRLS user (RDS's master) gets a finding, and the run rolls back.
  - The env samples call the password optional, and the cutover runbook has a section on the three cases.
  - Proofs: `tests/unit/db` 936 passed; `tests/db/tenancy` on a throwaway 680 passed; 11 of 11 mutants killed.
  - Review: MERGE-READY, OPEN 0. It ran step 7's merged script and the tip against the same databases, and found
    `--verify-only` output identical.
  - **Fix round 1 (done, tip `98ef0033`):**
    - A reporting password equal to the app's, grant's or query user's password is refused before anything
      connects, with exit 2. The review's m3 found the hole: the app's password would otherwise open a user that
      reads every tenant.
    - `test_schema_conformance.py`'s fallback passes `PGPASSWORD` to `docker exec` by name, with the value in the
      child's environment.
      - The secret scan only read SQL text, and it listed that very `docker exec` shape as allowed. It gains a
        command-line rule and now reads the test tree as well.
    - The refusal says the reporting user was not created, and names the users the run did create. A unit pin holds
      users created before grants. Six instructions that rotated a password with the plaintext in the statement now
      use `\password`.
    - Proofs: non-db 16537 passed, 0 failed; `tests/db/tenancy` on a throwaway 680 passed, 0 failed; 23 of 23 mutants
      killed; live, the refused run never connected and created nothing.
    - **A rule broke:** the implementer's probe connected once to the shared cluster on port 5432.
      - Loading `test_schema_conformance.py` connects at import time to `POSTGRES_HOST`/`POSTGRES_PORT`, which default
        to `localhost:5432`, and the probe had set only `ENV_FILE`.
      - The probe connected as `postgres` to database `postgres` and ran only the module's `SET search_path`. A
        second attempt failed authentication.
      - No DDL, grant or write ran, and `copilot_mro` was not touched.
  - **Fix round 1's re-review (2026-10-05): FIX FIRST, OPEN 1.**
    - **The finding:** the reused-password check compares raw strings, but libpq SASLpreps a password before it
      derives the verifier, and again at login.
      - Live on a throwaway, the app's password plus a soft hyphen (U+00AD) was not refused.
      - The reporting user was created, and it logged in with the app user's own password.
    - The other round-1 items held. Every lane was green, and port 5432 was never touched.
    - The fix-1 report said api and iac carry copies of the old rotation instruction. Neither does.
  - **Fix round 2 (running):**
    - "Equal" means equal after libpq's normalisation (C.1.2 to a space, B.1 removed, NFKC), or equal as raw strings.
      This applies to the reporting check and the owner check.
    - Also: the refusal tells how to fix a reporting user that already exists; with `--app-password`, the check also
      compares the settings' value; the cutover runbook creates `flynapse_inspect` without a plaintext `PASSWORD`;
      two spawners are pinned; and the secret scan's docstring states its other blind spots.
  - **Next:** a scoped re-review, the merge into `langgraph-merge`, the post-merge test run (with api's census, per the
    user-erasure merge protocol), then the push.
  - **Controller ruling (2026-10-01, night):** the owner's stand-in, the connected role that passed the definer-owner
    precondition, is excluded from every holder census, each naming it on an accepted line; any other member of the
    owner stays a finding. Why: under the RDS ruling ("report the rest"), a master that is a member of `postgres` but
    not named so would otherwise fail verify with 17 findings, and step 3 would commit nothing there.
  - **The owner's rulings (2026-10-01, evening):**
    - On RDS, PostgreSQL 16 makes the master a member of each role it creates, and the link cannot be removed. Verify
      names that one edge on its own accepted line, and every other edge stays a finding.
    - The owner runs step 6's 4c later today.
- **Steps 6–7** each start with an owner DDL step. Tenant delete (B14) is step 7. Step 6 also carries step 4's re-review
  n1: a test that the default-privilege check covers every object kind, not only tables.
- The ledger is `.superpowers/sdd/db-roles-consolidation/progress.md`.

**Research:** `~/.claude/scratch/db-roles/R1-db-roles.md` (census, duplication, target set, what each change touches,
risks, rollout order). This plan records the decisions and the order; the research carries the file-level detail.

## Decisions (owner, 2026-09-28/29)

22. **Phoenix and the Telegram bot get their own database users.** Today both log in as the superuser. Phoenix gets a
    `phoenix` user owning a dedicated `phoenix` database; the bot gets `telegram_bot_app`, owning its own database.
    Creating them is a cluster-owner hand step.
23. **A dev-only inspection user.** Local tools (the database MCP) and the data-checking tests move to
    `flynapse_inspect`: read-only, cross-tenant, dev clusters only, never in a service environment. `flynapse_readonly`
    then serves analytics only, with exactly its documented table list, and the privilege check fails on any extra
    read grant.
24. **AI-written SQL runs as a read-only user.** Before step 6, `db_query` ran as the main app user inside a
    read-only transaction behind an SQL gate. A dedicated `flynapse_query` pool makes "cannot write" a database
    privilege: select-only on the tool's table list, still bound by the tenant access rules (no bypass, unlike the
    analytics user), no EXECUTE grant and no definer function it can run, and no membership edges to any other user.
    Defence in depth, not a hole today. Through `db_query` (one gate-admitted statement inside a read-only
    transaction) it can write nothing: the gate also refuses `pg_logical_emit_message`, a WAL write the read-only
    transaction does not stop (step 6 re-review A). Past the gate, in a read-write transaction it opens itself, the user
    can still: create a persistent large object through PUBLIC's EXECUTE on the `lo_*` functions (`DROP OWNED` clears
    it), call `pg_notify` (nothing listens), use PUBLIC's TEMPORARY, call PUBLIC's ordinary extension functions (none
    can write, cross tenants or reach a definer; step 6 review A), and `ALTER ROLE` itself. A role-level setting it
    writes is a `--verify-only` finding (verify requires exactly the provisioned settings, cluster-wide, and none per
    database); a password it changes is not seen by verify, but fails closed, since the pool's next connection is
    refused. Step 7's default-privilege revokes take PUBLIC's EXECUTE
    on the `lo_*` and extension functions and PUBLIC's TEMPORARY, each with a verify finding; until then the pool
    resets every connection on release, so no session state crosses callers.
25. **One environment-variable name per password, one shared list of user names in code.** The old names stay as a
    deprecated fallback for one release. Owner scripts read the owner through the shared `owner_credentials()`.
26. **The deployed API gets the grant login.** App Runner passes only the main app login, so on AWS the paths that
    use `flynapse_grant` fail: signup's tenant creation, operator access grants, the boot seed and the erasure's AI
    turn-record deletion. The Terraform reads both grant settings (and the app password) from Secrets Manager. The
    owner creates the secret and runs the apply.

27. **Provisioning creates `flynapse_readonly` on request (owner, 2026-10-04).** Today the script grants to the
    reporting user but never creates it, and a missing one is a finding that rolls back the whole run. So every
    database had to carry a user that reads every tenant's rows, even where nothing uses it (no deployed service
    does: only the local Grafana, the quality-report script and two owner scripts read as it).
    - When `POSTGRES_READONLY_PASSWORD` is supplied, the script creates it with its reviewed attributes, and grants
      exactly its table list.
    - When the password is absent and the user too, the script skips it: not a finding.
    - When the user exists, its exact table list is enforced, as today.
    - Built after step 7 merges, since it is the same script.
28. **AWS gets Postgres and Phoenix as containers on the Weaviate box (owner, 2026-10-05).** AWS has no Postgres
    today: DynamoDB's tables left Terraform, and the API's database host still defaults to `localhost`.
    - Postgres runs as a container beside Weaviate on the `weaviate-observability` EC2 box, with its data on the
      box's disk, as on the local stack. It replaces DynamoDB for the API.
    - Phoenix runs there the same way ("replicate Weaviate"), keeping its traces in its own `phoenix` user and
      database in that Postgres, so they survive restarts. The client-account module's optional Phoenix, which keeps
      nothing across restarts, is a separate matter.
    - A nightly backup to S3 is built, since no managed backup exists, and the erasure receipt states its retention.
    - Planned separately: `docs/plans/aws-postgres-and-phoenix.md`.

## Order (from the research's rollout, with the rulings applied)

- [x] 1. Code only, no database change: the shared user-name module, env-var canonicalisation with fallbacks, owner
  scripts through `owner_credentials()`, an attribute check on the grant pool (it must never bypass the tenant rules),
  doc fixes (25).
- [x] 2. Measure: the privilege check reports extra read grants on `flynapse_readonly` (report-only first), run on the
  test database and the dev database.
- [ ] 3. Terraform for App Runner: the grant login and the app password from Secrets Manager (26). Written by Claude,
  applied by the owner; sequenced after iac `obs-merge` reaches `main`. Built and reviewed on iac `db-roles-tf` (`a47c0fb`). **Owner (2026-09-30):
  no apply for now.** Merged into iac `main` as `ff1cb5c` (2026-10-01); the apply waits on the owner.
- [ ] 4. The inspection user (23): hand DDL on the dev cluster by the owner, then repoint the MCP config and the
  data-checking tests, then revoke the extra grants from `flynapse_readonly` and turn the check into a finding.
  - Measured in step 2 (test database): `flynapse_readonly` can read 97 relations beyond its 19-relation list, which
    is effectively the whole `public` schema, including AI turn content, the erasure ledger, `tenants` and
    `user_operators`. They come from its membership in `pg_read_all_data`, not from table grants. So the remedy is
    `REVOKE pg_read_all_data FROM flynapse_readonly`, not per-table revokes. Role membership is cluster-wide, so the
    protected databases have the same surface.
- [x] 5. Side services (22): the `phoenix` and `telegram_bot_app` users and databases; the superuser leaves both
  connection strings.
- [x] 6. The read-only query pool (24): the new user, its grants, the second pool in copilot-mro, and a check that no
  definer function is executable by it.
- [x] 7. B14 tenant delete, then, on top of this: the definer function with execute revoked from PUBLIC and granted to
  `flynapse_grant` only, then `tenants` delete rights revoked from the grant user. Also the default-privilege revokes
  from decision 24: PUBLIC's EXECUTE on the `lo_*` and extension functions (granted back to the app user where it
  needs them; `wdm_graph` uses `similarity()`) and PUBLIC's TEMPORARY, each with a verify finding.
- [ ] 3b. Terraform: App Runner reads `POSTGRES_QUERY_PASSWORD` from the same owner-made secret, by reference (owner,
  2026-10-04: write it now; the owner applies it at deploy). Building on iac `db-roles-tf-query`.
- [ ] 8. Decision 27: provisioning creates `flynapse_readonly` when its password is supplied, and a missing one with no
  password is no finding. After step 7's merge.

**Rules for every step:** grants and revokes run on `copilot_mro_test` first, then the protected databases, with the
provisioning verify before and after. Table ownership stays with `postgres`. The auto-mode classifier refuses Claude's
DDL on shared databases, so every DDL step is the owner's to run.

## Implementation notes

- **Steps 1–2** (2026-09-29): built on branch `db-roles-s1` in `utils-roles`, `copilot-mro-roles`, `core-roles`,
  `shift-optimizer-roles` and `api-roles`.
  - **Review history:**
    - The review found one Important gap: role creation could hand the app role the owner's password in transition
      shells.
    - Fix round 1 made the provisioner refuse a restricted role whose password equals the owner's, and refuse
      disagreeing old and new names. The Minor findings were closed as well.
    - Three more rounds closed what each re-review found:
      - the owner check blind to `POSTGRES_OWNER_PASSWORD`, and the transition shell with only `POSTGRES_PASSWORD`
        exported;
      - "the password follows the user" pinned for all 16 owner scripts;
      - refusal remedies that lead with the owner's case;
      - a restricted `--user` refused up front;
      - the env templates and the runbook matched to the behaviour.
    - From round 2 on, each fix round ran on a fresh agent (the 500k-token cap).
  - **Merged `--no-ff` into the moved mainlines**, with no conflicts:
    - utils `00d0823`;
    - core `020fd08`;
    - shift-optimizer `bd410d9`;
    - copilot-mro `60bcd0b8`;
    - api `8b74c53`.
  - **Version commits:**
    - utils bumped to 0.1.41 (`b3edfbd`);
    - the core and shift-optimizer codeartifact floors raised to `>=0.1.41` (`bcdccb3`, `3e07609`);
    - the api and copilot-mro lock version lines updated (`b29d7be`, `3f46076d`).
  - **Post-merge full suites** (`~/.claude/scratch/db-roles/postmerge/gate.sh`): the same failure set as the
    user-erasure merge gate, all pre-existing or environmental:
    - the sibling-worktree census tests;
    - copilot-mro's `tests/config` ×3 and pilot ftd ×1;
    - whole-tree pollution;
    - the solver performance test under load. It passed at load 3.5.
    - The `test_registered_packages_restore` merge-order pair is now green.
  - **Owner steps now:**
    - Publish utils 0.1.41 before any core or shift-optimizer wheel.
    - Delete `GRANT_POSTGRES_PASSWORD` from `copilot-mro/.env` and `api/.env`.
    - Add `POSTGRES_READONLY_PASSWORD` to `copilot-mro/deployment/.env`.
    - Export `POSTGRES_OWNER_PASSWORD` for the owner scripts.
- **Step 3** (2026-09-29): built on branch `db-roles-tf` in `iac-roles` from `obs-merge`, reviewed through two fix
  rounds and approved (OPEN 0). It is not pushed and waits on the owner's `obs-merge` → `main`.
  - The owner steps are in the SDD workspace (`s3-tf-report.md`):
    - create the secret `api/postgres/passwords` before any plan;
    - drop `-var postgres_password`;
    - rotate both passwords after the apply;
    - `start-deployment` after any rotation;
    - confirm the Postgres host, port, database and sslmode reach App Runner (neither `dev.tfvars` nor CI sets them).
  - **Step 3b (2026-10-05)** adds a third key, `POSTGRES_QUERY_PASSWORD` (iac `db-roles-tf-query` `5e08621`, accepted
    by controller read: one reference, its pin, 16/16 mutants killed, iac 335 passed). Its owner steps are in
    `s3b-tf-query-report.md`:
    - the secret holds all three keys, and every `put-secret-value` writes all three, since it replaces the whole
      JSON;
    - `flynapse_query` exists on the deployed database before its password goes in;
    - rotation names the third user.

    A missing key fails only at the deployment, not at the plan. The database host is still not set anywhere
    (`aws-postgres-and-phoenix.md`).
  - The current app password sits in every earlier state version, and it may be the literal `postgres` if CI ever
    applied. Rotation closes that.
  - The grant USER is plain config, because a role name is not a secret. Decision 26's wording above covers the
    passwords.

## Future Improvements

- **The password variables' names are pinned in iac as literals (step 3b, concern 1).**
  - iac's CI lane checks out iac alone, so its guard cannot read utils' `db_roles.py`.
  - A rename in utils of `POSTGRES_PASSWORD`, `POSTGRES_GRANT_PASSWORD` or `POSTGRES_QUERY_PASSWORD` would pass every
    test and fail at the next deployment.
  - *Complete fix:* a cross-repo pin in a lane that checks out both repos (api's checkout-pinned lane), comparing
    iac's three keys with utils' constants.

- **The passwords guard is a text matcher (step 3).**
  - *What is missing:* two ways around it survive:
    - a CI `-var=`/`TF_VAR_` override of `postgres_grant_user`;
    - role chaining, where a new role trusts the App Runner instance role and holds broad secrets access.
  - *Why deferred:* a text check over HCL can always be dodged. Two hardening rounds closed the likely paths.
  - *Complete fix:* an IAM policy check on the rendered plan in CI, for example IAM Access Analyzer. Narrower
    alternatives:
    - fail on any trust policy naming the instance role;
    - scan workflow `-var=` arguments.
- **`AZURE_OPENAI_API_KEY` reaches App Runner as plain env (step 3).**
  - *What is missing:* it is not stored as a secret.
  - *Complete fix:* move it to Secrets Manager through `runtime_environment_secrets`, like the database passwords.
- **An `.env` that itself pairs the app user with the owner's password is not caught on a trust-auth cluster (steps
  1–2, fix round 2).**
  - *What is missing:* the provisioner refuses whenever a restricted role's password equals a password it can see as
    the owner's: the one it logs in with, or `POSTGRES_OWNER_PASSWORD`. Take a checkout whose `.env` names
    `flynapse_app` with the owner's real secret, run on a trust-auth cluster with no owner variable set. The owner
    resolves to the built-in default, trust accepts it, and the role is created with the secret the process never
    saw as the owner's.
  - *Why deferred:* closing it means refusing role creation whenever the owner resolved to the built-in default.
    That changes dev-box and preflight behaviour. No cluster in the trees uses trust auth, and RDS never does.
  - *Complete fix:* require `POSTGRES_OWNER_PASSWORD` (or an explicit `--password`) whenever the provisioner CREATES a
    role, and keep the default only for `--verify-only`.
- **The inspection-user guard does not scan iac (step 4).**
  - *What is missing:* the guard reads copilot-mro, core and api service code, env templates and copilot-mro's tracked
    `deployment/` files, but not `iac/*.tf`, where an App Runner environment could still name the inspection password.
  - *Complete fix:* the same token scan over the iac repo's tracked `.tf` and `.tfvars` files.
- **Step 5's guards and sheet leave three gaps.**
  - The Phoenix guard reads only the overlay file, so a `phoenix` service added to the base compose file would merge in
    unseen. *Complete fix:* check the rendered `dev + phoenix` configuration, keeping the raw `env_file`/`extends`
    refusal.
  - Step 8's bound on the final `CASCADE` does not name a publication that includes a `phoenix` table (the live
    `postgres` database has none). *Complete fix:* add `pg_publication_rel` to the outside-dependents check.
  - The otel README's own Phoenix procedure still sets the password with an interactive `\password`, unlike the sheet.
- **Core still carries step 6's old sentences (step 6 fix round 1, re-review B N-1).**
  - *What is missing:* four comments in core's tests describe utils' pool open as unlocked (step 6's M2 locked it),
    and three sentences say `db_query` runs model-written SQL as the app user (`tenant_service.py:15`,
    `tests/db/rbac/test_tenant_teardown_db.py:31` and `:351`).
  - *Why deferred:* core is outside step 6's batch, and none of them changes behaviour.
  - *Complete fix:* reword the seven with core's next change that touches those files.
- **A table dropped from `db_query`'s allowlist keeps the query user's SELECT (step 6 re-review B N-2).**
  - *What is missing:* provisioning grants the allowlist but never revokes a grant outside it, so `--verify-only`
    and every later provisioning run fail with `query extra privileges` until the owner runs the `REVOKE` by hand (the
    runbook names it).
  - *Why deferred:* it fails closed and names the table; no table is being dropped from the list.
  - *Complete fix:* `grant_query_role` revokes every privilege the user holds outside the allowlist, pinned by a live
    test that drops a table from the list.
- **The SAD-local fixture's full provisioning path is unexercised (step 1).**
  - *What is missing:* `provision_rls` makes `postgres` own its security-definer functions, and the fixture never
    creates that role.
  - *Complete fix:* create the owner role in the fixture, or have the fixture run the provisioner as its own
    superuser.
- **Step 7's verify: what the fix rounds left (2026-10-04).** Each item below fails closed (verify stays red) or is
  test-only, unless it says otherwise.
  - **Step 1 on a database a non-`postgres` master owns** (PostgreSQL 15 and later) fails with an uncaught
    `InsufficientPrivilege`: `postgres` lacks CREATE on `public`, and nothing is written. The sheet's probe stops the
    owner first. *Complete fix:* a precondition that exits ABORTED (2) with the remedy.
  - **The order of the printed remedies matters.** Run last-first, they can strip `postgres`'s own privileges on a
    relation while verify reads clean. On RDS that breaks `delete_tenant` in the shape where `rds_superuser` holds
    neither data role. Handing ownership back also takes the old owner's grants, and the app role's DML on an
    ordinary table is checked nowhere. *Complete fix:* must-hold checks for the owner role's privileges and the app
    role's DML.
  - **On RDS, the master cannot hand back a relation the read-only, app or grant role owns.** *Complete fix:* the
    remedy says to grant the master the role `WITH INHERIT TRUE` first, then run the `ALTER`.
  - **A write reached through a membership is reported once per relation** (125 findings for `pg_write_all_data`),
    each REVOKE taking nothing back. The membership finding names the real remedy. *Complete fix:* one collapsed
    finding, or the membership clause on each.
  - **Bare names:** utils' completeness cross-check and RLS emitters, and a few remedies (schema and role names in
    `CREATE ON SCHEMA`, default-privilege and membership remedies), print names unquoted. A name that needs quoting
    would raise or print a remedy that does not parse. No name in the schema needs quoting today. *Complete fix:*
    `quote_ident` everywhere a name is printed or run.
  - **A grant made by a grant-option holder stays after its printed remedy.** *Complete fix:* name the grantor in the
    remedy.
  - **`s7-census.sql`'s `tenants writer` row leaves out whichever role owns `tenants`.** Verify is the gate.
  - **Unpinned or weakly pinned:**
    - the new pass's quoted-name path (mutants X8b, X21);
    - relation kinds in the unit fakes (X14, X16);
    - a TRUNCATE outside `public` (X6);
    - two wording mutants (PD1, PC1);
    - two live acceptance tests that keep their own `has_table_privilege` SQL (`test_grant_role_acceptance.py:408`,
      `test_user_operator_grants.py:336`).
  - **Never run:** PostgreSQL 15, a real RDS, and the real Docker CLI. The local proof ran the sheet's `docker` blocks
    through a stand-in.
- **Step 7's verify: what the last re-reviews left (2026-10-04, night).** Each item fails closed or is test-only.
  - **A server-file membership granted by a non-superuser holding ADMIN cannot be cleared by its printed remedy.**
    - The printed `REVOKE <group> FROM <member>` is a no-op WARNING when a superuser runs it. It fails with
      "dependent privileges exist" when the ADMIN holder runs it.
    - Verify still fails, so nothing reads clean.
    - *Complete fix:* print `GRANTED BY <grantor>`, or `CASCADE`.
  - **A unit fake decides a result from its test data, not from the SQL:** the inspection shape's BYPASSRLS row filter.
    Mutants O7b and A2-6 survive the unit run and are killed live. *Complete fix:* the fake reads the filter from the
    SQL it is given.
  - **Unpinned cells:**
    - materialized views and foreign tables in the relation data census;
    - the app role's `nextval` outside `public` (live), PUBLIC's `nextval`, and default privileges on functions and
      types (all three closed, none pinned);
    - a managed role in the server-file census, live.
  - **One cause can make several findings,** for example a membership and each relation it reaches. *Complete fix:*
    one finding per cause.
  - **The sheet's probe query 8 leaves out the relation's owner,** like the `tenants writer` row above. Fixing it
    changes the probe's output on RDS, so it needs a re-measure.
  - **The sheet has no step-0 run of the branch's own verify.** An unmanaged holding on `copilot_mro` first shows at
    step 3, after the merge, where it fails closed. *Complete fix:* step 0 runs the branch's verify read-only.
  - **The "On RDS" probe's item 5 still accepts any `pg_…` row** (sheet text). A server-file role there fails verify.
  - **Role names in the REVOKE remedies are unquoted.** This is part of the "Bare names" item above.
- **Every login can CONNECT to `copilot_mro` through PUBLIC (AWS Postgres and Phoenix, phase 1).**
  - *What is missing:* PUBLIC keeps CONNECT on the app database, and provisioning revokes only TEMPORARY. On the AWS
    box the `phoenix` user shares the cluster, so it can connect there and reach whatever PUBLIC holds.
  - *Complete fix:* provisioning revokes CONNECT from PUBLIC on the app database and grants it to the managed roles,
    with a verify cell.
- **Step 8: what its review left (2026-10-05).**
  - **An existing reporting user is not held to its whole shape.** A NOLOGIN, NOBYPASSRLS or INHERIT reporting user
    reads clean today, since step 7 exempts it from the LOGIN check; CREATEDB and REPLICATION are findings.
    *Complete fix:* verify holds an existing reporting user to exactly LOGIN, BYPASSRLS and NOINHERIT.
  - **`--verify-only` does not predict the creation refusal.** It names the superuser requirement but does not check
    whether the connecting role could create a BYPASSRLS user, so a real run can still roll back. *Complete fix:* a
    precondition, like the definer-owner check, that refuses before phase 1 creates anything.
  - **Any two service users may share a password.** Fix round 1 refuses the reporting user's password when it
    equals a service user's. *Complete fix:* refuse any two of the app, grant, query and reporting users that share a
    password, before connecting.
  - **utils' `readonly_credentials` docstring** still says the provisioner reads the reporting password only to
    compare it with the owner's. Fix it with utils' next change.
  - **`tests/db/memory/test_memory_operator_rls.py:292` passes the owner's password in an in-process argument
    list.** It is not visible in `ps`, but it is the shape the secret scan refuses elsewhere.
- **Step 8's fix round 1: what is left (2026-10-05).**
  - **`test_schema_conformance.py` connects to a database when it is imported.** Its cluster check reads
    `POSTGRES_HOST`/`POSTGRES_PORT` directly, defaulting to `localhost:5432`, not the settings `ENV_FILE` names. A
    lane pointed at a throwaway only through `ENV_FILE` therefore reaches the shared cluster as soon as it loads the
    module. *Complete fix:* resolve the address through the same settings as the rest of the suite, and connect in
    a fixture rather than at import.
  - **The secret scan's command-line rule has stated blind spots:** a command line given as one string
    (`shell=True`), a list reaching `subprocess` through a loop target or a container, spawners this repo does not
    call (`asyncio.create_subprocess_exec`, `os.exec*`), and programs outside its list. The SAD test's own argv check
    is now a narrower twin of it. *Complete fix:* retire the twin, and widen the rule as those shapes appear.
  - **The re-review found four more blind spots in the rule (m-1).** It does not see:
    - a command line grown after it is built (`.append`, `.extend`, or `+=` on a stored line), an idiom the tree
      already uses at 8 sites, none with a secret;
    - a list spread into the line (`*flags`);
    - a helper's parameter not led by a known program;
    - a libpq URI's userinfo under a neutral name.

    Fix round 2 names them in the docstring. *Complete fix:* read the arguments of `.append` and `.insert` as
    elements, and the value of `.extend` and `+=` as a line; follow a spread to its list. One test shape each.
  - **Two false-finding shapes (m-6):** `secrets.token_*` naming a random container, network or database, and a tuple
    led by a program name used as data. Only the registered pragma hits one today.
  - **The `docker exec` attempt's environment is pinned by nothing that runs here (m-7).** A mutant that drops the
    value from the child's environment survives, because the 18 tests that need the dump skip whenever the fallback
    fails. *Complete fix:* after the import-time-connect fix above, unit-pin `_pg_dump_schema_only`'s attempts: the
    variable passed by name, and the value in each environment.
- **copilot-mro's non-db lane reads the local test database (AWS phase 1, fix round 1).** Seven tests not marked
  `db` read `copilot_mro_test`. Three skip with "not present in this database" (the optimizer plan digest, the
  inventory plan, the optimizer decompose); four pass only with a database (`test_reset_demo`,
  `test_workout_tool_adapters`, and `test_doc_catalog_ingest_writes` twice). *Complete fix:* mark them `db`, or have
  them skip without a database, so the non-db lane needs none.

## Lessons

- **A guard that walks a directory must be run on the primary checkout before a push (step 4, 2026-09-30).** The
  inspection-user guard walked copilot-mro's `deployment/` with `rglob`. Every lane ran in worktrees, which have no
  runtime data, so the implementer, two reviewers and a re-reviewer all saw it green; the post-merge gate on the
  primary hit a root-owned Redis dump and failed. Rule: a scan enumerates git-tracked files (`git ls-files`), never the
  filesystem, and a merge's gate runs on the primary before the push.

- **Fix rounds get fresh agents (owner, 2026-09-29).** Fix round 1 resumed the steps 1–2 implementer, whose context
  was already very high. The owner ruled that every later fix round, and the scoped re-review after it, runs on a NEW
  agent. Brief it from the review file, the fix brief and the ledger, never by resuming the earlier implementer or
  reviewer. The owner then made it a workspace rule: no agent past 500k tokens of context gets more work. The round-1
  implementer (about 720k) was stopped on its last step, with all its work committed. That stop killed its hand-back
  lanes, which then had to be re-run, so the owner refined the rule: an agent that crosses the cap mid-task
  finishes that task, and only then retires. A fresh reviewer took the re-review.

- **Name the shared database, not the database name, in a safety rule (step 7, part 4b, 2026-10-01).** Briefs said
  "never connect to `copilot_mro`". Part 4b read that as forbidding a database of that name inside its own throwaway
  container too, so it skipped the sheet's re-proof at the merged tips, which needs one. Rule: a brief names what is
  protected by where it lives (the shared server's `copilot_mro`, the `postgres` container on port 5432), and says
  outright that a throwaway built from code may hold databases of any name.
- **"Never connect to 5432" needs the address exported, not only `ENV_FILE` (step 8 fix round 1, 2026-10-05).** The
  implementer's probe loaded `test_schema_conformance.py`, which connects at import to `POSTGRES_HOST`/`POSTGRES_PORT`
  (default `localhost:5432`), so it reached the shared cluster although its settings named the throwaway. Rule: every
  brief whose lanes or probes import `tests/db` modules exports `POSTGRES_HOST`/`POSTGRES_PORT` and
  `PGHOST`/`PGPORT` set to the throwaway, as well as `ENV_FILE`.
- **A class hunt needs a matrix, not another review (step 7, fix rounds 4–7, 2026-10-04).** Rounds 4, 5 and 6
  each closed what the last review found, and each re-review then found one more privilege class verify never read.
  Round 7 wrote down every privilege PostgreSQL has against every role, with the check that reads each cell, and
  found 21 holes at once. Rule: when a second review in a row finds a new member of the same class, stop fixing one
  at a time. Write the class out completely, and close it by construction.
- **A large file's agents work from a design file and symbol indexes (step 7 fix round, 2026-10-01).** Two agents ran
  out of context reading the 4,000-line provisioning script. The round then ran as narrow parts, each with a
  "read only this" list, slices through a regenerated symbol index (`/usr/bin/grep`, since `grep` is ugrep here), and
  a "Status after part N" section appended to one design file, so every next agent started from durable state.
- **A merge by name records whatever the name points at then (step 7 part 7d, 2026-10-04).** Part 7d merged
  `langgraph-merge` and `master` "by name". A test-only merge landed on both 18 seconds earlier. The sheet, the
  report and the ledger all named the SHAs the brief gave, not the ones actually merged. Lens B caught it by reading
  the merge commits' parents. Rule: a report names a merge's parents as `git log --format=%p` prints them, never as the
  brief expected them.
- **A matrix needs a row for every kind of grant, including predefined roles (step 7 re-review, 2026-10-04).** The
  privilege matrix left membership in PostgreSQL's predefined server-file roles as "may" for unmanaged roles. That
  membership lets a role run OS commands as the server, a superuser's reach, so verify read clean on it. Rule: a
  matrix of privileges lists every predefined role whose membership grants a capability. Each is a row, never a
  "may" by default.
