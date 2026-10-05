# AWS: Postgres and Phoenix as containers on the Weaviate box

Status: **planned, not started** (2026-10-05). It is built before the AWS deploy. The owner deploys to AWS only once
all work is finished.

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
6. **Sizing:** Weaviate, Postgres, Phoenix and the collector share the box. The instance and the data volume are
   expected to grow. Measure Weaviate's current use before choosing.

## Open questions (ask before building)

- The instance size and the data volume's size.
- The backup retention, in days. The erasure receipt states it.
- Whether any data on AWS must be carried over (DynamoDB's old contents, the client's users).
- Whether the box stays in the public subnet with the database port closed to the internet, or moves behind a NAT.

## Risks

- **One box holds every store.** Losing the instance loses nothing (the data volume is separate). Losing the
  volume loses everything since the last nightly dump.
- **Upgrades and patching of Postgres are by hand.**
- **The `<secret ARN>:<JSON key>::` reference form** is unproven until the first deployment (DB roles step 3).

## Lessons
