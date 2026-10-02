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
    - running: the scoped re-review, in two lenses (the code; the sheet and the rollout). Then the sheet goes to the
      owner, with step 6's 4c first.
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
- [ ] 6. The read-only query pool (24): the new user, its grants, the second pool in copilot-mro, and a check that no
  definer function is executable by it.
- [ ] 7. B14 tenant delete, then, on top of this: the definer function with execute revoked from PUBLIC and granted to
  `flynapse_grant` only, then `tenants` delete rights revoked from the grant user. Also the default-privilege revokes
  from decision 24: PUBLIC's EXECUTE on the `lo_*` and extension functions (granted back to the app user where it
  needs them; `wdm_graph` uses `similarity()`) and PUBLIC's TEMPORARY, each with a verify finding.

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
  - The current app password sits in every earlier state version, and it may be the literal `postgres` if CI ever
    applied. Rotation closes that.
  - The grant USER is plain config, because a role name is not a secret. Decision 26's wording above covers the
    passwords.

## Future Improvements

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
- **A large file's agents work from a design file and symbol indexes (step 7 fix round, 2026-10-01).** Two agents ran
  out of context reading the 4,000-line provisioning script. The round then ran as narrow parts, each with a
  "read only this" list, slices through a regenerated symbol index (`/usr/bin/grep`, since `grep` is ugrep here), and
  a "Status after part N" section appended to one design file, so every next agent started from durable state.
