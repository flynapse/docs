# AWS: Postgres and Phoenix as containers on the Weaviate box

Status: **phase 1 built, in review** (2026-10-05): the box's compose, first boot, setup script and nightly backup.
A fix round follows, because the box's old startup unit cannot start the new stack. Phase 2 is the Terraform and
phase 3 the runbook. It is built before the AWS deploy; the owner deploys to AWS only once all work is finished.

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

## Lessons
