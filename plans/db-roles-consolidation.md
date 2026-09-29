# Database users: consolidation (owner decisions 22–26)

**Status (2026-09-29):** the owner has answered all five decisions, all yes. Queued to start after the user-erasure P2
push. Nothing has been built yet. Tenant delete (B14) waits on this batch.

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

- [ ] 1. Code only, no database change: the shared user-name module, env-var canonicalisation with fallbacks, owner
  scripts through `owner_credentials()`, an attribute check on the grant pool (it must never bypass the tenant rules),
  doc fixes (25).
- [ ] 2. Measure: the privilege check reports extra read grants on `flynapse_readonly` (report-only first), run on the
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
  - The review found one Important gap: role creation could hand the app role the owner's password in transition
    shells. It is in fix round 1.
  - Merge order: utils first, then the rest. The user-erasure `ue-p2c2` utils branch merges before this one.
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
- **The SAD-local fixture's full provisioning path is unexercised (step 1).**
  - *What is missing:* `provision_rls` makes `postgres` own its security-definer functions, and the fixture never
    creates that role.
  - *Complete fix:* create the owner role in the fixture, or have the fixture run the provisioner as its own
    superuser.

## Lessons

None yet.
