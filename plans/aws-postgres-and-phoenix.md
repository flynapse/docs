# AWS: Postgres and Phoenix as containers on the Weaviate box

Status: **phase 1 in fix round 2; phase 2 (the Terraform) building alongside it** (2026-10-05). Phase 1 is the
box's compose, first boot, setup script, nightly backup and startup unit. Fix round 2 is copilot-mro only and phase
2 is iac only, so they run side by side. Phase 3 is the runbook. It is built before the AWS deploy; the owner deploys
to AWS only once all work is finished.

## Why

- **AWS has no Postgres.** The API moved from DynamoDB to Postgres, and DynamoDB's tables have left Terraform. But
  no Postgres exists on AWS: the App Runner service's database host still defaults to `localhost`, and no
  committed setting names a host.
- **AWS has no Phoenix that keeps its data.**
  - The main account runs no Phoenix at all. Its telemetry goes to CloudWatch, and the collector box keeps only the
    collector and Weaviate (observability ruling 14).
  - The client-account Terraform module has an optional Phoenix container. It has no database and no volume, so it
    loses its traces on every restart.

## Owner decisions

- **2026-10-05: Phoenix runs like Weaviate:** a container on the `weaviate-observability` EC2 box.
- **2026-10-05: Postgres runs as a container on the same box,** replacing DynamoDB for the API. Its data is on the
  box's data disk, as on the local stack. Phoenix keeps its traces in its own `phoenix` user and database in that
  Postgres. Asked against managed RDS, which the controller recommended; the owner chose the container.
- **2026-10-04: AWS deploy only once all work is finished.**
- **2026-10-05, the four open questions:**
  - **Size:** a 16 GB box (`t3.xlarge`) and a 50 GB data disk.
  - **Backups:** nightly dumps to S3, kept 14 days. The erasure receipt states that an erased person's data leaves the
    backups within 14 days.
  - **Data:** start empty. AWS is the dev environment; tenants and users are created fresh.
  - **Network:** the box stays in the public subnet. Postgres and Phoenix admit only App Runner's security group and
    the box itself; SSH stays limited to the owner's IP.
- **2026-10-05: the step 3b Terraform** (`db-roles-tf-query`) stays on its branch and merges with this plan's iac work.
  Auto mode refused the controller's merge into iac `main`.
- **2026-10-05: the box keeps deploying copilot-mro `main`, and `main` is fast-forwarded first.** The setup script
  clones `main` (hard-coded in `ec2.tf`). It last moved on 2026-02-11, is 3,164 commits behind `langgraph-merge` and
  lacks this work, so a box built from it would fail at boot and take Weaviate and the collector down with it.
  `main` is a strict ancestor of `langgraph-merge`. Before the deploy, `main` is fast-forwarded to `langgraph-merge`
  and pushed, with the owner's approval. Phase 2 still makes the branch a Terraform variable, defaulting to `main`.
- **2026-10-05 (controller, from phase 1's review): no globals dump.** On AWS every role comes from code: first boot
  makes `phoenix`, and provisioning makes the app's. A globals dump without passwords would make provisioning find
  the roles already there and never set their passwords. The restore order is: first boot, then provisioning, then
  `pg_restore`, then verify.

## What exists today (measured 2026-10-05)

- **The box** (iac `ec2.tf`):
  - `t2.large` (2 vCPU, 8 GiB) in a public subnet, to avoid NAT costs, with a 30 GB root disk;
  - Weaviate's data on a separate 10 GB encrypted EBS volume, mounted at `/opt/persistent-data`. It survives an
    instance replacement, which `user_data_replace_on_change` triggers on any setup-script change;
  - the setup script (`demo_ec2_setup.sh`) clones the deployment repo and runs `deployment/demo/docker-compose.yml`
    (collector, Weaviate, Weaviate UI) under a systemd unit;
  - a hook already points the collector's content pipeline at a Phoenix when `PHOENIX_ENDPOINT` is set.
- **Network:**
  - the box's security group admits a listed set of ports from App Runner's and the Lambdas' security groups, and
    SSH from one IP;
  - App Runner reaches the VPC through its VPC connector, in a private subnet.
- **Database users:** the DB-roles program's provisioning (`provision_rls.py`), its owner sheets, and decisions
  22–28 (`db-roles-consolidation.md`).
- **The API's Postgres passwords** come by reference from the owner-made secret `api/postgres/passwords`. Three keys
  once step 3b merges.

## Design (to confirm at the start)

1. **Postgres container:**
   - PostgreSQL 16, matching the local stack, on the box's compose;
   - its data under `/opt/persistent-data` on the EBS volume;
   - its superuser password from a secret the setup script reads; never in the repo or the compose file;
   - listening only to App Runner's security group and the box itself, never the internet.
2. **Phoenix container:**
   - the image pinned as on the local stack;
   - auth on, with its secret and admin password from SSM, as the client-account module does;
   - its database is `phoenix` in that Postgres, owned by the `phoenix` user (the four owner lines in
     `copilot-mro/deployment/otel/README.md`);
   - a retention policy;
   - the collector's content pipeline and the API's erasure seam both point at it. The API also needs Phoenix's
     keys, or `PHOENIX_ENDPOINT=none` stops the erasure doors (user erasure, ruling O10).
3. **The database's setup**, run once by the owner over an SSH tunnel or on the box:
   - the schema (`migrate_tenancy_schema.py`);
   - provisioning (`provision_rls.py`), which creates the app, grant and query users;
   - `--verify-only` clean;
   - the `phoenix` user and database.

   No `flynapse_readonly` there (decision 27), and no inspection user (decision 23).
4. **The API:**
   - App Runner's database host, port, name and sslmode point at the box;
   - the three passwords stay in the secret;
   - a Postgres on plain EC2 has a real superuser, so the sheets' "On RDS" stops do not apply.
5. **Backups:**
   - a nightly dump to an S3 bucket with a lifecycle expiry, on a timer on the box;
   - the box's role may write only that prefix;
   - a restore drill;
   - the erasure receipt's backup bound (user erasure D12) then states that retention.
6. **Sizing:** Weaviate, Postgres, Phoenix and the collector share a `t3.xlarge` (16 GB), with a 50 GB data volume
   that can grow online.

## Open questions

None: the owner answered all four on 2026-10-05 (above).

## Risks

- **One box holds every store.** Losing the instance loses nothing (the data volume is separate). Losing the
  volume loses everything since the last nightly dump.
- **Upgrades and patching of Postgres are by hand.**
- **The `<secret ARN>:<JSON key>::` reference form** is unproven until the first deployment (DB roles step 3).

## Implementation notes

- **Phase 1 built (2026-10-05).** copilot-mro `aws-pg-phoenix` (`copilot-mro-awspg`, from `langgraph-merge`
  `a5374567`) and iac `aws-pg-phoenix` (`iac-awspg`, on step 3b's `5e08621`).
  - **Compose:** `postgres` (16-alpine; data on the volume; published 5432) and `phoenix` (20.8.0; its own database
    and user; auth on; 30-day retention; published 6006). Each secret is read by interpolation from one root-only
    env file, so each container gets only its own.
  - **First boot:** one SQL file creates the `phoenix` user from a SCRAM verifier computed on the box, its database
    with CONNECT and TEMPORARY revoked from PUBLIC, and `copilot_mro`. No password appears in any statement, command
    line or log (proven with `log_statement=all`).
  - **The setup script** reads the four secrets by name from SSM SecureStrings into a 0600 file. It refuses a value
    it cannot carry safely, naming the parameter.
  - **The nightly backup** streams a custom-format dump of each database to S3 through a FIFO, and kills the upload
    before end of stream on a failed dump, so no partial object is ever completed.
  - Review: FIX FIRST, one Important finding (the old startup unit) and nine Minors.
- **Phase 1, fix round 1 (2026-10-05).** copilot-mro `24e3652e`, iac `a74b69e`.
  - The startup unit runs as root from a root-owned copy. It pulls as ec2-user (`--ff-only`), then runs compose with
    the env file and the Phoenix override, and never `down`.
  - Docker waits for the data volume (`RequiresMountsFor`). The fstab line names the volume by UUID, and every
    compose run checks the mountpoint first.
  - Postgres waits out crash recovery (`start_period` 300 s) and stops cleanly (60 s). First boot's SQL stops at its
    first error. The volume root is 755. The Phoenix secret's rule is enforced.
  - The backup kills the upload's whole process group. On the same cut dump, the phase's script had completed a
    100,000-byte partial object.
  - Re-review: FIX FIRST, two open items. Every fix closed its finding, and nothing the phase proved moved.
    - A failed pull at boot stops the unit before compose, leaving the Weaviate UI down. The likely trigger is the
      GitHub token in the clone URL expiring.
    - A regression: `setsid` took the upload out of the backup script's process group. A signal to that group (a
      hand-run backup whose SSH session drops) then completed a partial object. Runs under systemd are unaffected.
- **Phase 1, fix round 2 (running).**
  - Compose runs whatever the pull did, and the unit fails afterwards, naming the pull. The pull is bounded by
    `timeout`. The Weaviate UI gets a restart policy, and the pin covers every service.
  - The backup traps HUP, INT and TERM and stops the upload's group first.
  - Two pins tighten: the unit's `[Service]` keys become an allow-list (an `ExecStartPre=… down` passed before), and
    the backup's stop-before-close order is pinned.
  - The iac README's "git pull origin main" lines go to phase 2, with the branch variable.

## Phase 3: what the runbook must cover (collected as the phases land)

- **Before the deploy:**
  - fast-forward copilot-mro `main` to `langgraph-merge` and push it, with the owner's approval. Check that the
    branch holds `deployment/demo/postgres/`;
  - create the four box parameters, and the placeholder for the API's Phoenix key.
- **After first boot:**
  - change the Phoenix admin's password;
  - mint a System API key each for the collector and the API, and store them;
  - put the collector's key into `/opt/otel/collector.env` and recreate the collector;
  - run `start-deployment` for App Runner.
- **The database, over an SSH tunnel:**
  - migrate, provision, and `--verify-only` clean;
  - no reporting user (leave `POSTGRES_READONLY_PASSWORD` unset) and no inspection user;
  - the sheets' "On RDS" stops do not apply: the box's Postgres has a real superuser.
- **First-deploy checks** (unprovable locally):
  - `docker-compose --env-file … config --quiet` reads the quoted values literally;
  - Phoenix creates its schema;
  - `\l+` and `\du` show the designed databases and users;
  - Docker waits for the mount (`RequiresMountsFor` with `nofail`): `systemctl show docker -p Requires -p After`
    names `opt-persistent\x2ddata.mount`;
  - `runuser` works under the unit.
- **Operations:**
  - every manual compose command runs as root with `--env-file` (and never `config` without `--quiet`);
  - the root-owned unit, script and backup files change only through a new instance or a manual `install`.
    Phase 1's fix round 2 reaches an existing box only that way;
  - a boot and a `systemctl restart weaviate-observability` both pull and apply the branch head;
  - backups run only through `systemctl`. A hand-run backup killed with SIGKILL can leave a partial object, which
    `pg_restore` rejects and the 14-day expiry removes;
  - rotation is by hand (a verifier or `\password`, plus the parameter);
  - growing the volume is the size in Terraform, then `xfs_growfs`.
- **Recovery:**
  - a failed first boot: stop Postgres, empty `postgres-data`, start again;
  - a volume attached after the device timeout leaves Docker "Dependency failed": attach it, then
    `systemctl start docker` and `systemctl restart weaviate-observability`;
  - a restore: first boot, then provisioning, then `pg_restore`, then verify.
- **The erasure receipt** states that an erased person's data leaves the backups within 14 days (user erasure D12).

## Future Improvements

- **The GitHub token sits in the instance's user data** (pre-existing). *Complete fix:* read it at boot from SSM,
  like the box's other secrets.
- **Postgres runs at the image's defaults** (128 MB shared buffers, 64 MB `/dev/shm`) with no memory limit, on a box
  it shares with Weaviate, Phoenix and the collector. *Complete fix:* tune it for a 16 GB box, with a compose memory
  budget.
- **`aws s3 cp -` needs `--expected-size`** once a dump passes about 50 GB.

## Lessons
