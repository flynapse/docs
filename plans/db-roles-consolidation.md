# Database users: consolidation (owner decisions 22–26)

**Status (2026-09-29, evening):** the owner has answered all five decisions, all yes.
- **Steps 1–2: MERGED and PUSHED.** Pushed as utils `b3edfbd` (0.1.41), core `bcdccb3`, shift-optimizer `3e07609`,
  copilot-mro `3f46076d` and api `b29d7be`. The owner's `.env` steps and the utils 0.1.41 publish are listed under
  step 2's notes.
- **Step 3 (Terraform):** approved and unpushed (`iac-roles` `db-roles-tf` @ `a47c0fb`). It waits on the owner's iac
  `obs-merge` → `main`.
- **Steps 4–7** are next. Each starts with an owner DDL step; step 4's is `REVOKE pg_read_all_data FROM
  flynapse_readonly`. Tenant delete (B14) is step 7.
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
24. **AI-written SQL runs as a read-only user.** Today `db_query` runs as the main app user inside a read-only
    transaction behind an SQL gate. A dedicated `flynapse_query` pool makes "cannot write" a database privilege:
    select-only on the tool's table list, still bound by the tenant access rules (no bypass, unlike the analytics
    user), no execute on non-catalog functions, and no membership edges to any other user. Defence in depth, not a
    hole today.
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
  applied by the owner; sequenced after iac `obs-merge` reaches `main`.
- [ ] 4. The inspection user (23): hand DDL on the dev cluster by the owner, then repoint the MCP config and the
  data-checking tests, then revoke the extra grants from `flynapse_readonly` and turn the check into a finding.
  - Measured in step 2 (test database): `flynapse_readonly` can read 97 relations beyond its 19-relation list, which
    is effectively the whole `public` schema, including AI turn content, the erasure ledger, `tenants` and
    `user_operators`. They come from its membership in `pg_read_all_data`, not from table grants. So the remedy is
    `REVOKE pg_read_all_data FROM flynapse_readonly`, not per-table revokes. Role membership is cluster-wide, so the
    protected databases have the same surface.
- [ ] 5. Side services (22): the `phoenix` and `telegram_bot_app` users and databases; the superuser leaves both
  connection strings.
- [ ] 6. The read-only query pool (24): the new user, its grants, the second pool in copilot-mro, and a check that no
  definer function is executable by it.
- [ ] 7. B14 tenant delete, then, on top of this: the definer function with execute revoked from PUBLIC and granted to
  `flynapse_grant` only, then `tenants` delete rights revoked from the grant user.

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
- **The SAD-local fixture's full provisioning path is unexercised (step 1).**
  - *What is missing:* `provision_rls` makes `postgres` own its security-definer functions, and the fixture never
    creates that role.
  - *Complete fix:* create the owner role in the fixture, or have the fixture run the provisioner as its own
    superuser.

## Lessons

- **Fix rounds get fresh agents (owner, 2026-09-29).** Fix round 1 resumed the steps 1–2 implementer, whose context
  was already very high. The owner ruled that every later fix round, and the scoped re-review after it, runs on a NEW
  agent. Brief it from the review file, the fix brief and the ledger, never by resuming the earlier implementer or
  reviewer. The owner then made it a workspace rule: no agent past 500k tokens of context gets more work. The round-1
  implementer (about 720k) was stopped on its last step, with all its work committed. That stop killed its hand-back
  lanes, which then had to be re-run, so the owner refined the rule: an agent that crosses the cap mid-task
  finishes that task, and only then retires. A fresh reviewer took the re-review.
