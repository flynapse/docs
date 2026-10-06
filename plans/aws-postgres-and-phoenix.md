# AWS: Postgres and Phoenix as containers on the Weaviate box

Status (2026-10-06, 09:45 PDT): **phases 1 to 4 are built and reviewed; the dashboard is merged; the last fix rounds
run.**
- **Dashboard: MERGED and pushed** (`agent_sdk` `0795b14`). A hand publish with `move_latest` off pushes the commit
  tag alone, and its pin runs the workflow's steps sealed from the real AWS, GitHub and Docker CLIs.
- **copilot-mro** (`aws-pg-phoenix` `eb7aef68`): its fix round's re-review says MERGE-READY with two Minors (a loose
  docstring, a message line not pinned whole). A short round takes both now.
- **iac** (`aws-pg-phoenix` `df80315`): both fix rounds are done:
  - F1, the pins and the POC clone's token;
  - F2, the runbook's 16 fixes, the SSH tunnel included.
  Two re-reviews run in parallel, one per round. A last round F3 follows with their findings, the tunnel's exact text
  and one more reboot sentence.
- **The owner chose (06:09):** the POC's web app is opened through an SSH tunnel, with no change in AWS.
- **Next:**
  - iac F3 and its check;
  - the merges: copilot-mro into `langgraph-merge` after user erasure's X3 and X4, keeping both scope-guard blocks;
    iac into `main` with `db-roles-tf-query`;
  - then the owner's deploy.

Phase 1 is the box's compose, first boot, setup script, nightly backup and startup unit. Phase 3 is the runbook. It is
built before the AWS deploy; the owner deploys to AWS only once all work is finished.

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
    - **Owner, 2026-10-05:** no replay after a restore (user erasure decision 31 stands). The receipt gains
      `backups_days: 14` in the user-erasure P5 fix round. A restore can bring back people erased since the dump, and
      the runbook says so.
    - **Controller, 2026-10-05:** S3 rounds an expiry up to the next midnight UTC, so the bucket's expiry is 13 days.
      A user-erasure pin holds the receipt's bound at least the expiry plus 1.
    - **Owner, 2026-10-05 (after phase 2's review):** S3 can remove an expired dump "days or even weeks" late, and
      the dump stays readable until then. So the box's nightly backup also deletes its own dumps older than 13
      days. They are gone within 14 days while the box runs, and the 13-day expiry is the backstop.
      - The box's role gains `s3:ListBucket` (prefix-conditioned) and `s3:DeleteObject` on the prefix. It can already
        overwrite the dumps.
  - **The ingest Lambda (owner, 2026-10-05):** a follow-up after the deploy. It writes Postgres but has no settings
    or network path on AWS, so every ingest there fails, as it already did before this plan.
  - **The POC replica (owner, 2026-10-05):** it stays. The bucket policy denies its role, as it does App Runner's,
    the Lambdas' and the CI deployer's.
  - **Data:** start empty. AWS is the dev environment; tenants and users are created fresh.
  - **Network:** the box stays in the public subnet. Postgres and Phoenix admit only App Runner's security group and
    the box itself; SSH stays limited to the owner's IP. (An amendment at ~20:20 PDT let Postgres admit the POC
    replica's security group too; it was withdrawn at ~21:40, when the POC became a one-box install, below.)
- **2026-10-05 (~09:45 PDT): the iac merge is approved,** once phase 3's fix rounds are re-reviewed MERGE-READY and
  gated. It carries the step 3b Terraform too (below).
- **2026-10-05 (after phase 3's review): one combined deploy.** iac's root still holds the observability rebuild's
  pending apply order (B2 to B8). The AWS runbook takes it over: B4's log-group imports first, the POC replica
  stopped before its replacement, and step 6 listing everything else it carries. Alert arming (Phase 10, after
  B1a's gate) stays a later step.
- **2026-10-05 (~20:20 PDT): the API image is built by hand at deploy time.** api's GitHub build cannot build a
  current image: since `d4974ab` (2026-07-22) api declares `mro-copilot`, `core`, `flynapse-utils` and
  `shift-optimizer` as local path dependencies, its CI checks out api alone, and its wheel check refuses a `file://`
  requirement. So ECR's `:latest` is from before then unless pushed by hand. Asked against fixing the build first
  (recommended) and keeping the current image; the owner chose a runbook step in which they build the image on their
  machine from the checkouts and push it to ECR, tagged with the api commit. The GitHub build stays broken (a Future
  Improvement).
- **2026-10-05 (~20:20 PDT), superseded at ~21:40: the POC replica gets the Postgres settings.** The deploy replaces it, and a current API
  image needs Postgres at boot, which its setup does not give it. Its setup gets the box's Postgres host and the app
  passwords from the same secret App Runner reads, so it keeps working after the deploy. This amends the network
  decision below: Postgres (not Phoenix) also admits the POC replica's security group.
- **2026-10-05 (~21:40 PDT): the POC server is a one-box client install, built into this deploy.**
  - The owner's context: the POC server replicates how a client deployment runs, with everything (Postgres, Weaviate,
    the API, the dashboard and the rest) on one EC2 box. The internal deployment is this plan's main shape: App
    Runner runs the API, and a separate box runs Weaviate and Postgres.
  - So the POC server gets its own Postgres beside its own Weaviate, and never reaches the main box's Postgres. This
    supersedes the ~20:20 decision. Round 1d2 reverts the security-group change round 1d made for it (`97830ca`).
  - Asked against "its own plan, after this deploy" (recommended) and "keep today's version running", the owner chose
    to build it into this deploy.
  - A read-only design comes first (phase 4 below), then the owner's answers to its questions, then its rounds.
- **2026-10-05 (~21:05 PDT): the email login is stored in AWS.** api's GitHub build baked `SMTP_USER` and
  `SMTP_PASSWORD` into the image as build arguments. The hand-built image carries neither, and App Runner set neither,
  so the API would have sent no email (invitations, feedback, AD notifications).
  - The owner makes a Secrets Manager secret (`api/smtp`) with those two keys, once, before the deploy. App Runner
    reads it by reference, as it reads the Postgres passwords, with a grant of its own.
  - The owner chose this over deploying without email and over baking the login into the image (anyone who can pull
    the image could read it).
  - Fix round 1e builds it, and round 1d moves the image build before the deploy, so the build and push stay out of
    the outage.
- **2026-10-05: the step 3b Terraform** (`db-roles-tf-query`) stays on its branch and merges with this plan's iac work.
  Auto mode refused the controller's merge into iac `main`.
- **2026-10-05 (superseded ~22:50 PDT, below): the box keeps deploying copilot-mro `main`, and `main` is
  fast-forwarded first.** The setup script clones `main` (hard-coded in `ec2.tf`). It last moved on 2026-02-11, is
  3,164 commits behind `langgraph-merge` and lacks this work, so a box built from it would fail at boot and take
  Weaviate and the collector down with it. `main` is a strict ancestor of `langgraph-merge`. Before the deploy, `main`
  is fast-forwarded to `langgraph-merge` and pushed, with the owner's approval. Phase 2 still makes the branch a
  Terraform variable, defaulting to `main`.
- **2026-10-05 (~22:50 PDT): protect a client's box; our deploy never moves `main` or `:latest`.**
  - The POC design found that copilot-mro's old POC kit (`deployment/poc/restart-services.sh`, "go live changes",
    2025-12-11) restarts a box at a fixed private address outside our AWS network, most likely a client's server.
    At every restart it pulls copilot-mro `main`, logs in to our ECR, and pulls the API and dashboard images by their
    `latest` tags.
  - The deploy as written would fast-forward `main` and move `flynapse-api-ecr:latest`. That box's next restart would
    then run an API that cannot boot there (no Postgres, no multi-tenant collections).
  - Asked whether such a box still runs, the owner chose "protect it" over "no box runs it" and "I'll handle that
    box". So: our boxes deploy their own branch (`aws-deploy`, created and fast-forwarded by the runbook), App Runner
    runs the API image by its commit tag (recorded in `dev.tfvars`), and nothing in the deploy moves `main`,
    `flynapse-api-ecr:latest` or `dashboard-ecr:latest`. Fix round 1f builds it. It supersedes the decision above.
- **2026-10-05 (~22:50 PDT): the POC server's design questions** (phase 4), each the recommended option:
  - **Readiness on its own:** the box makes its passwords at first boot and a one-shot helper container migrates,
    provisions, verifies and creates the Weaviate collections before the API starts. Chosen over the owner making
    four SSM passwords and running the setup over tunnels after the deploy.
  - **No backups:** dev data, the data disk survives replacements, and the erasure receipt's 14 days hold with nothing
    to wait for. Chosen over local nightly dumps and nightly dumps to S3.
  - **Size:** `t3.xlarge` (16 GiB) and a 30 GB data disk, chosen over keeping `t2.large` and 10 GB.
  - **The POC's dashboard image (~23:30 PDT): refreshed on its own tag.** Dashboard's publish job always moves
    `dashboard-ecr:latest`, which the client's box pulls. A small dashboard change lets a hand run push only the
    commit tag, and the POC runs that tag. Chosen over keeping the POC's May dashboard.
- **2026-10-06 (06:09 PDT): the POC's web app is opened through an SSH tunnel, with no change in AWS.** The final
  review's lens B found that the tunnel works as things are:
  - the API's port 8000 is already public;
  - `http://localhost:3000` is in the API's default CORS origins;
  - the dashboard's password sign-in (Amplify SRP) needs no callback URL.

  Chosen over a port-3000 rule from the owner's address.
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

None open. The last one, whether a browser should reach the POC's UI, was answered on 2026-10-06: through an SSH
tunnel, with no change in AWS (Owner decisions). The owner answered the design's four questions on 2026-10-05.

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
- **Phase 1, fix round 2 (done, copilot-mro `585333e5`; re-reviewed MERGE-READY, OPEN 0).**
  - The re-review's live proof: SIGHUP, SIGINT and SIGTERM mid-dump each left no object, 6 of 6. A signal during the
    second database's dump left no Phoenix object and a complete `copilot_mro` one.
  - A default `timeout` signals the whole process group. `runuser -u` never calls `setsid()`, so git stays in that
    group, and `--kill-after` is not needed.
  - The merge waits for phase 3, as planned. Its Minors m-a, m-b and m-d ride with the box's dump prune round (same
    tree, small); m-c is a Future Improvement.
  - Compose runs whatever the pull did, and the unit fails afterwards, naming the pull. The pull is bounded by
    `timeout 300`. The Weaviate UI gets a restart policy, and the pin covers every service.
  - The backup traps HUP, INT and TERM and stops the upload in flight. Live, each signal mid-dump left no object,
    while round 1's script on SIGHUP completed a 100,000-byte object.
  - Two pins tightened. The unit's `[Service]` keys are an allow-list. The backup's stop-before-close order is
    pinned deterministically: a `kill` on `PATH` records whether the stream is still open.
  - 18 of 18 mutants killed. The non-db lane passed: 16524 passed, 0 failed.
- **Phase 1, the box's dump prune round (done 2026-10-05, copilot-mro `585333e5..93b64914`; in review).**
  - **The prune:** after every run, whatever the dumps did, the backup deletes every object under `<prefix>/` whose
    `LastModified` is more than 12 days old: dumps, partial objects and probe objects. It lists with exactly
    `--prefix "<prefix>/"`, deletes one key at a time, and prints only the keys it deleted. A failed listing or
    delete fails the unit, naming the prune; a refused key does not stop the others.
    - It uses `delete-object`, not `delete-objects`, because `delete-objects` exits 0 when it refuses a key.
  - **12 days, not the 13 of the owner's option text.** The owner's purpose was the receipt's 14 days, and 13 cannot
    meet it. A run deletes only what has passed the threshold, so a dump lives at most:
    - the threshold, 12 days;
    - plus the longest gap between two runs: a day, plus `RandomizedDelaySec` (10 min), plus systemd's default
      `AccuracySec` (1 min);
    - plus the run's `TimeoutStartSec` (3 h), since the prune comes after the dumps.

    That is 13 d 3 h 11 min, under 14 days. A test reads every term from the timer, the service and the script,
    against a constant named for core's `backups_days`.
  - **m-a, m-b, m-d:** a failed pull's FAILED line prints before `up -d`, and the unit still exits 1; the failed-pull
    test uses git's real 128 (corrected by the fix round below: `git pull` exits 1 when its fetch fails); the pull
    runs with `GIT_TERMINAL_PROMPT=0`.
  - Proofs: 18 of 18 mutants killed, the re-review's two survivors included. The non-db lane passed: 16538 passed,
    0 failed (fix round 2's 16524 plus 14 new tests), with no docker call.
  - **Rulings on its concerns:**
    - iac still says the prune is 13 days (README, about `:654`; `postgres_phoenix.tf:60`), and the README's
      `restart-services` lines lack m-d's facts. The next iac round fixes both (phase 3's list).
    - Incomplete multipart uploads get no new grant: no S3 API reads their parts, and the lifecycle aborts them
      after a day. Recorded as a Future Improvement.
    - A night without a prune (S3 refused, or the 3 h limit) fails the unit visibly, and the 13-day expiry is the
      bound until the next good night.
    - The fake `aws` models the CLI's text output; phase 3's first-deploy checks measure it.
  - **Its review (2026-10-05): MERGE-READY, OPEN 0, six Minors.** The bound holds while the nightly runs succeed, with
    a margin of 20 h 49 min. Measured from the erasure rather than the upload, a dump is gone within 13 d 6 h 11 min.
    - **Taken now, in a small fix round** (copilot-mro `93b64914..5700c550`, done, re-reviewed MERGE-READY, OPEN 0;
      21 of 21 mutants killed, the non-db lane 16545 passed, 0 failed):
      - m-1: the prune fails on a listing line it cannot read, but no test fed one. It also stopped at the first
        such line;
      - m-2: the bound's test read `TimeoutStartSec=0` as zero seconds, where systemd reads it as no limit;
      - m-3: `git pull` exits 1, not 128, when its fetch fails;
      - m-4: the cheap half. A key ending in a tab or a newline was reported pruned under the wrong name.
    - **To phase 3's runbook:**
      - m-5: two nights without a prune leave the unit inactive, not failed. One is a reboot during a run; the
        other is Docker failing to start;
      - m-6: the prune assumes a delete deletes, which versioning would break;
      - the prefix change: changing the backup prefix leaves the old prefix's dumps outside both the prune and
        the expiry.
    - **The fix round's re-review (2026-10-05): MERGE-READY, OPEN 0, four Minors.** The sentinel never reads as a
      key and keeps aws's own exit status; the bound still holds. All four Minors are taken in a fix round 2
      (`p1-prune-fix2-brief.md`), which starts once phase 3's lens A has read the tree:
      - n-1: two texts say more than the script does (a newline key's first line is still deleted; a failed
        listing prunes nothing);
      - n-2: the unreadable count is pinned only at 1;
      - n-3: the bound pin reads Unicode digits and spaces, so a timeout that systemd refuses would pass it;
      - n-4: the bound pin never reads `Type=`, so a later `Type=exec` would leave the run unbounded.
- **Phase 2, the Terraform (done at iac `3933f47`: reviewed FIX FIRST, OPEN 2; its fix round re-reviewed
  MERGE-READY, OPEN 0).**
  - **The re-review (2026-10-05):** every finding closed, and the guards fail for the right reasons. It confirmed:
    - `aws:PrincipalArn` carries a role's path as `.arn` does, so the deny has no path hole;
    - CI runs as an IAM user, which the deny never names;
    - the targeted apply pulls in neither App Runner nor the Lambda;
    - every page of the prune's listing matches the `s3:prefix` condition;
    - the role allows exactly what the as-built prune does.
  - **Its four Minors ride with phase 3** (same tree):
    - m-1: the readers guard tests a literal ARN against one sample key, so a grant on another database's dumps
      escapes it;
    - m-2: a second bucket policy that names the bucket through a local passes, and would replace the pinned policy
      at apply;
    - m-3: more texts still say the prune is 13 days;
    - m-4: the single-apply fallback must wait for step 5's key, not only step 4.
  - **The fix round (2026-10-05, iac `377c051..3933f47`):**
    - the bucket's deny on the four broad roles, with a guard that works out the broad readers from the root's own
      grants. The guard needs the deny's list to match exactly, so narrowing a role's S3 access means taking it out
      of the deny too;
    - the 13-day expiry; the box's prune grants (list `<prefix>/` with the trailing slash, delete under it, no read);
      one prefix variable; object lock refused;
    - `WEAVIATE_URL` by `box.<env>.internal`; the role-resource and network-interface guard holes; the instance's
      `depends_on`;
    - the README's owner steps in the new order, the stale texts, the key check and the probes' negative controls;
    - beyond the brief: the bucket guard also fails on a versioning or object-lock resource whose bucket it cannot
      tell apart.
    - Proofs: iac's tests 445 passed, 1 skipped (shellcheck absent); `fmt`, `validate` and the three CI validators
      pass; 32 of 32 mutants killed.
    - CI's Terraform runs as backend-bootstrap's `terraform-deployer`, which the deny never names.
  - **I-1:** two more roles can read and delete every dump: the POC replica's and the CI deployer's. The deny must
    be `s3:*`, since the bucket-level actions otherwise let App Runner's role remove the deny itself.
    - The safe form names the four roles in an `aws:PrincipalArn` condition, never as principals, and never by
      exclusion.
    - A guard fails on any broad-S3 role the deny does not name.
  - **I-2:** the owner steps deployed the API before its database existed. The order is now: a targeted apply of
    the box side, first boot, migrate and provision, mint the keys, the full apply, then confirm `SUCCEEDED`.
  - Minors folded in: three guard holes plus object lock; the instance waits for its SSM grant; stale texts; the
    API's key checked over the tunnel; the multipart probe's negative control.
  - The fix round also sets the expiry to 13, gives the box's role its prune rights, takes every backup path from
    one prefix variable, and names Weaviate by the box's name.
  - The box:
    - `t3.xlarge`, with a 50 GB volume that has `prevent_destroy` and `stop_instance_before_detaching`;
    - the setup script finds the volume by its id (the NVMe by-id path), and grows the filesystem at first boot.
  - `deployment_github_branch`, default `main`, refuses a SHA or a `refs/` path, and the boot fails unless the
    clone is on that branch. The repository URL must end in `copilot-mro`.
  - Ports 5432 and 6006 are open to App Runner's security group only. The instance role reads exactly the five
    parameters and writes only the backup prefix.
  - The bucket:
    - public access blocked, ownership enforced, SSE-S3;
    - TLS and `AES256` required;
    - objects expire after 14 days (13 after the fix round) and unfinished uploads after 1; no versioning.
  - App Runner reaches the box by one private name, `box.<env>.internal`, for Postgres and Phoenix. Its own Phoenix
    key comes by reference.
  - 22 of 22 mutants killed. iac's tests: 423 passed.
  - **Its fix round, after the review:**
    - an explicit deny on the backup bucket for App Runner's and the Lambdas' roles, whose `AmazonS3FullAccess`
      reaches it today;
    - the expiry set to 13 days;
    - `WEAVIATE_URL` by the box's name.
  - **Open, for the owner:** the ingest Lambda writes Postgres, but its Terraform gives it no Postgres settings (this
    was already so). Should ingest on AWS reach the box's Postgres?
- **Phase 3, the runbook (built at iac `3933f47..99f85b9`, 5 commits; in review by two lenses).**
  - **The round (2026-10-05):**
    - iac's README demo-box section is now the owner's deploy runbook, in deploy order: before the deploy, the seven
      steps, after the deploy, operations, and recovery. Every bullet of the list below has its lines (the round's
      coverage table, in `p3-runbook-report.md`).
    - The prune texts say 12 days, with the 13 d 3 h 11 min bound, and every object under the prefix. The
      restart-services lines are corrected.
    - Phase 2's m-1: the readers guard matches a literal pattern as IAM does, against the bucket and every object in
      it. m-2: the untold-bucket check covers all seven configuration types.
    - Six runbook pins: the steps' order, step 2's targets, step 4's order, step 5's key, no `start-deployment`
      advice, and no key on an argument list.
    - The database step runs the cutover runbook's commands over the tunnel, in a clean shell (`env -i`,
      `ENV_FILE=/dev/null`). Without it, the owner's dev `.env` would leak in, and a dev
      `POSTGRES_READONLY_PASSWORD` would create the reporting user on the box.
    - Proofs: iac's tests 472 passed, 1 skipped; `fmt`, `validate` and the three validators pass; 13 of 13 mutants
      killed.
  - **Rulings on its concerns:**
    - `--no-snapshot` on the first migrate is accepted: the database is new and empty.
    - The restore's first provisioning run exits 1 by design. Accepted only if the runbook names the exact message
      and stops on any other. A roles-only mode is a Future Improvement.
    - `provision_rls.py`'s docstring is stale about `agent_state`. Recorded in the DB-roles plan.
    - **`start-deployment`:** the round's brief over-generalised the plan's two rules. A rotated secret reaches App
      Runner only at its next deployment, so rotation ends with `start-deployment`, run only when `list-operations`
      shows the latest operation `SUCCEEDED`. After a rollback, the runbook still says never. The next fix round
      builds it and narrows the pin. The owner may overturn this.
    - The Phase 10 sentence that `main` has no `deployment/otel/` goes stale at the fast-forward. The next fix
      round corrects it.
    - m-2's reach stays the seven types: ACLs are closed by the enforced ownership, and access points by the SSE-KMS
      Future Improvement.
  - **The review is split in two lenses,** because the round's implementer ended at 563k tokens. Lens A takes the
    runbook's prose and commands; lens B takes the guards and the pins.
  - **The reviews (2026-10-05): both FIX FIRST.**
    - **Lens A, the runbook: OPEN 7.**
      - Step 6 deploys whatever image `:latest` holds, and the runbook never names or checks it.
      - The restore's expected failure is not quoted, and its own remedy (run the migration) would break the restore.
      - Rotation is wrong for the app roles' secret (a Secrets Manager JSON secret). It lacks the redeploy and the old
        key's revocation, opens `secrets.env` in an editor, and leaves the box's own secrets stale for a re-initdb.
      - Three blocks open a new shell on their first line, so a pasted block runs outside it.
      - It ignores the root's other unapplied work: the observability rebuild's apply order.
      - Two Minors to fix now: a bare `docker-compose` under `sudo -i`, and the prefix change's order.
    - **Lens B, the guards and pins: OPEN 4,** all Minor real holes:
      - `count = 0` on a pinned configuration drops it at apply, and both guards pass;
      - `s3:GetObjectVersion` reads a dump unseen;
      - the argument-list pin misses three curl forms and a `put-parameter` after a global option;
      - the step-2 pin misses `-target <address>` written with a space.
  - **Controller rulings:**
    - The runbook names and checks the image before step 6 and before a rotation's redeploy. Deploying by the
      immutable `:<sha>` tag is a Future Improvement.
    - The box-only passwords (the superuser, `phoenix`) rotate by `\password`, then the parameter, then replacing the
      instance, whose setup script rewrites `secrets.env` from the parameters, verifier included. Never an editor.
    - Changing the prefix: apply, one hand-run backup, then empty the old prefix (the list below is changed).
    - A restore drill joins "After the deploy".
    - Every Minor of both lenses is taken, and lens B's FI-1, FI-2, FI-3 and FI-7 too.
    - **The owner's decision on the root's other work: one combined deploy** (see Owner decisions).
  - **Two fix rounds, in turn, on the same tree:** 1b, the guards (running); then 1a, the runbook for the combined
    deploy, with lens A's findings and every runbook pin.

## Phase 3: what the runbook must cover (collected as the phases land)

- **The deploy order (phase 2 review, I-2):**
  1. stop the box;
  2. a targeted apply of the box side, which leaves out App Runner;
  3. first boot;
  4. migrate, provision and `--verify-only` over the tunnel;
  5. mint both Phoenix keys and store them;
  6. the full apply, which deploys the API once against a ready database;
  7. `aws apprunner list-operations` shows `SUCCEEDED`.

  Never follow a rolled-back deploy with `start-deployment`: it redeploys the old configuration.
- **Before the deploy:**
  - stop the box before the first apply: it replaces the volume attachment, which was recorded without the new
    stop flag;
  - fast-forward copilot-mro `main` to `langgraph-merge` and push it, with the owner's approval. Check that the
    branch holds `deployment/demo/postgres/`;
  - create the four box parameters. The API's Phoenix key gets no placeholder: it is minted and stored before the
    full apply (deploy step 5).
- **After first boot:**
  - change the Phoenix admin's password;
  - mint a System API key each for the collector and the API, and store them;
  - put the collector's key into `/opt/otel/collector.env` and recreate the collector;
  - store the API's key in its parameter before the full apply, which deploys it. Never `start-deployment`.
- **The database, over an SSH tunnel:**
  - migrate, provision, and `--verify-only` clean, with the DB-roles sheet's exact invocations (the README's owner
    steps only summarise them);
  - no reporting user (leave `POSTGRES_READONLY_PASSWORD` unset) and no inspection user;
  - the sheets' "On RDS" stops do not apply: the box's Postgres has a real superuser.
- **First-deploy checks** (unprovable locally):
  - `docker-compose --env-file … config --quiet` reads the quoted values literally;
  - Phoenix creates its schema;
  - `\l+` and `\du` show the designed databases and users;
  - Docker waits for the mount (`RequiresMountsFor` with `nofail`): `systemctl show docker -p Requires -p After`
    names `opt-persistent\x2ddata.mount`;
  - `runuser` works under the unit;
  - the volume's NVMe by-id link exists on Amazon Linux 2023;
  - a multipart upload passes the bucket's SSE policy;
  - optional: Ctrl-C one backup run by hand, and confirm no new object appears;
  - the multipart probe's negative control: the same upload without `--sse` is refused. Both probes run as root
    with the backup's environment;
  - the API's Phoenix key works: a request to `/v1/projects` with it returns 200. The key is read with `read -rs`
    and reaches curl on stdin (`-H @-` fed by `printf`), never on curl's command line;
  - the prune's listing works under the role's `s3:prefix` condition: as root with the backup's environment,
    `aws s3api list-objects-v2 --prefix "$BACKUP_PREFIX/" --query 'Contents[].[LastModified, Key]' --output text`
    prints a time, a tab and a key per line (or `None`), and `date -u -d` reads the time. This is the one CLI
    behaviour the unit tests take from a fake;
  - the first nightly run (or `systemctl start postgres-backup`) logs both dumps, no FAILED line and no `pruned`
    line, and ends with status 0;
  - `systemctl list-timers postgres-backup.timer` shows the next run between 21:30 and 21:41 UTC;
  - about 13 days in, the journal shows `pruned` lines for the oldest night, and nothing under the prefix is older
    than 13 days;
  - `systemctl restart weaviate-observability` leaves the unit active.
- **Operations:**
  - every manual compose command runs as root with `--env-file` (and never `config` without `--quiet`);
  - the root-owned unit, script and backup files change only through a new instance or a manual `install`.
    Phase 1's fix round 2 reaches an existing box only that way;
  - a boot and a `systemctl restart weaviate-observability` both pull and apply the branch head. A failed pull still
    brings the stack up and fails the unit: after a reboot, check `systemctl status weaviate-observability`;
  - backups run only through `systemctl`. A hand-run backup killed with SIGKILL can leave a partial object, which
    `pg_restore` rejects and the nightly prune (or the 13-day expiry) removes;
  - rotation is by hand (a verifier or `\password`, plus the parameter);
  - growing the volume is the size in Terraform, then `xfs_growfs`.
- **Recovery:**
  - a failed first boot: stop Postgres, empty `postgres-data`, start again;
  - a volume attached after the device timeout leaves Docker "Dependency failed": attach it, then
    `systemctl start docker` and `systemctl restart weaviate-observability`;
  - a restore: first boot, then provisioning, then `pg_restore`, then verify. A restore can bring back people
    erased since the dump; no replay exists (user erasure decision 31).
- **The erasure receipt** states that an erased person's data leaves the backups within 14 days (user erasure D12).
  The nightly prune makes that hold while the box's nightly runs succeed; the 13-day expiry is the backstop. The
  receipt wording pass should say so.
- **iac's texts to correct** (the next iac round: a phase 2 fix round 2 if its re-review asks, otherwise phase 3's):
  - the prune is 12 days, not 13, with the bound above (the README, about `:654`; `postgres_phoenix.tf:60`);
  - the README's `restart-services` lines (about `:243-245` and `:576-577`): run the pull only through `systemctl`;
    git never prompts; a failed pull is named before compose runs, the stack still comes up, and the unit then
    fails, naming the pull.
- **From the prune's review** (phase 3's round):
  - run the "nothing older than 13 days" check right after a nightly run has finished, never just before one;
  - read a missed night from `journalctl -u postgres-backup` (the previous boot included) and the timer's `LAST`,
    never from `systemctl is-failed`. A reboot during a run, or Docker failing to start, skips a night without
    failing the unit; start it by hand once the box is healthy;
  - changing `box_postgres_backup_prefix`: apply first, run one backup by hand to the new prefix, then empty the
    old prefix, which neither the prune nor the expiry covers any more. (Post-review change, lens A's m-3: emptying
    it first leaves no backups until the next run, and a run before the apply writes a dump that never expires.)
  - never turn on the bucket's versioning by hand: each prune delete would leave only a delete marker.
- **The Weaviate schema step (controller finding, 2026-10-05, ~21:30 PDT).** The API refuses to start unless Weaviate
  has every declared multi-tenant collection, with exactly the partitions Postgres's tenants imply. It does this in a
  deployed environment, with no way to only warn.
  - The seven declared collections date from 2026-07-30 and 2026-08-16. The image that wrote the box's Weaviate is
    older, so the box almost surely has none of them, and App Runner's deployment in step 6 would fail.
  - Step 4 runs copilot-mro's `scripts/provision_weaviate_mt.py` (no `--partitions-from`) over the tunnel. It only
    adds the missing collections. A dry run of the API's boot checks comes before step 6's apply.
  - The runbook also says what to run when tenants are added later. Round 1d2 builds it.

## Phase 4: the POC server as a one-box client install (owner, 2026-10-05)

- **Goal.** After this deploy, the POC server runs everything on one EC2 box, as a client install would: its own
  Postgres beside its own Weaviate, plus the API, the dashboard and the rest. The API boots on it (migrated and
  provisioned database, Weaviate's collections and partitions), and the box survives a reboot.
- **Order.**
  - A read-only design (`p4-poc-design.md` in the plan's SDD workspace) covers:
    - the services, and reuse of the main box's `deployment/demo/`;
    - the passwords, and which container gets which;
    - how the database and Weaviate are made ready (at first boot or by the owner);
    - later tenants, reboots, backups, the POC's existing data, the runbook, and IAM and network.
  - Then the owner's answers to the design's questions.
  - Then its rounds, in copilot-mro (`deployment/poc/`, branch `aws-pg-phoenix`) and iac.
  - The two-lens re-review then covers it with the rest of phase 3.
- **Already known.**
  - The POC compose sets `WEAVIATE_URL` in `environment:`, which overrides `.env`.
  - The dashboard reads the API's `.env`.
  - The POC's restart unit (a template enabled without an instance) and its restart script (user `ubuntu`) do not
    work on the AWS POC. The design found why: they serve a client's box (see the ~23:10 decision), so they stay
    untouched and the AWS POC gets its own.
  - Its setup passes AWS access keys as template variables.
- **The design (done 2026-10-05, ~23:05 PDT; owner's answers ~23:10).**
  - **The services:** a new compose overlay beside the unchanged base adds Postgres 16, listening on the box's
    loopback only, with its data on the POC's data disk. No Phoenix: the API is told the host has none, so user
    erasure records that skip honestly instead of holding.
  - **Readiness:** passwords generated at first boot into a root-only file on the data disk (kept across replacements;
    the setup stops if the database exists without them). A one-shot helper container from the API's own image runs
    the checkout's migration, provisioning, verification and Weaviate schema scripts before the API may start. It
    migrates only an empty database; a database that holds data is verified, and a needed migration is the owner's
    step, with a snapshot first.
  - **Startup:** a new root-owned unit and script on the main box's pattern that never take the stack down, never
    pull code or images, and wait for the data disk.
  - **IAM:** the CI deploy user's static keys leave the POC; its role gains a scoped ECR pull grant. No security
    group change; the main box's group is never extended to the POC.
  - **Existing data:** the old Weaviate collections stay, because the schema step copies its shape from them. Before
    the deploy the runbook reads the POC's Weaviate version (not newer than the pin), the seven legacy sources, and
    that no declared collection exists with multi-tenancy off.
  - **Under the protection decision:** the POC clones the deploy branch and pulls the API by its commit tag.
  - **Rounds:** three in copilot-mro (the helper program, the overlay, the startup unit and script), then three in iac
    (the setup script, the role and size, the runbook).
- **Implementation notes (2026-10-06, to 03:55 PDT).**
  - **copilot-mro (`aws-pg-phoenix`):**
    - **P4-1 (`a8c9ec67`):** `deployment/poc/db_init.py`.
      - It waits at most 300 s for Weaviate.
      - **A fresh database:** migrate with `--no-snapshot`, provision, verify, then the Weaviate collections, never
        with `--partitions-from`.
      - **An existing database:** the migration runs only with `--verify-only`. A failure names the README's
        "Operations (POC)" step "A schema change", and exits 1.
    - **P4-2 (`96cc2fcc`):**
      - **On an existing database, db-init checks the provisioning first** and provisions only if that check fails
        (the controller's ruling). Provisioning takes ACCESS EXCLUSIVE locks on every tenant table while an API
        serves.
      - **The overlay** `deployment/poc/docker-compose.postgres.yml`:
        - `postgres:16-alpine`, on `127.0.0.1:5432` only, its password only through `${…:?}`;
        - db-init from the API's image, with read-only mounts, `init: true` and `WEAVIATE_URL`;
        - the API's additions, and its `depends_on` db-init completed.
      - `.env.sample` gains the four password names, and the compose tests read the overlay.
      - The client kit stays byte-identical to the branch's merge base.
    - **P4-3 (`e4e8bb57`):** `poc-stack.service` and `poc-stack-up.sh`.
      - A oneshot unit that never runs down, pull or git. It runs as root, after docker and the network, with a
        1,200 s start limit (Postgres' 300 s recovery window plus db-init's 300 s Weaviate wait and its steps).
      - `up -d --pull never`: an implicit pull would use an ECR login that expired 12 hours after the first boot. A
        missing image now fails the unit, by design.
      - It refreshes the three public-address lines of `.env` from IMDSv2, with a 60 s token and 10 s per call. An
        answer that is not an IPv4 address leaves the file as it is, with a warning.
      - It refuses, running nothing, without the data volume mounted, the secrets file, or one of the three lines.
      - Its 31 tests run the real script against stubs: 40 of 40 mutants died.
      - **What only the box can prove:** compose's `--pull never` failing on a missing image, the boot order, IMDS at
        boot, and systemd's PATH finding `docker-compose`. The deploy's checks and one stop and start are the proof.
  - **iac (`aws-pg-phoenix`):**
    - **P4-4 (`c153078`):** `poc_ec2_setup.sh`, on the main box's pattern:
      - the data volume found by its id;
      - scoped permissions;
      - secrets made once;
      - ECR by the instance role;
      - the image-label check;
      - both env files and both compose files.

      It also adds `poc_dashboard_image_tag`.
    - **P4-5 (`7545a90`):** `poc_replica_ecr_pull` (pull only, two repositories), which the instance waits for;
      `t3.xlarge`; 30 GB; the attachment's stop flag.
    - **P4-6 (`860f55a`):** the runbook's POC parts.
      - Before the deploy: the POC's Weaviate read, and the dashboard published by hand with `move_latest=false`,
        its tag then set in `dev.tfvars`.
      - Counts 61/11/4.
      - The POC's checks after the deploy, "Operations (POC)" and "Recovery (POC)".
      - **The rotation's way back after a rollback** (the controller's ruling): in the rotation path only, after a
        login proof with the stored value, one `start-deployment` gated on
        `START_DEPLOYMENT:ROLLBACK_SUCCEEDED`. The deploy path keeps "never after a rollback".
      - **`prevent_destroy` on the POC data disk** (the controller's ruling): it is the POC database's only copy,
        and the main box's volume already makes a whole-root destroy refuse.
  - **Dashboard (`dashboard-publish-tag`):**
    - `6011e32`: a hand run with `move_latest` off pushes the commit tag alone;
    - fix 1 (`317f462`): the pin proves the push, catches any `latest`, and the summary names tags only;
    - fix 2 (`7672233`): the pin seals its step runs from the real AWS CLI (refusing `aws`, `docker` and `gh` first
      on `PATH`, its own `HOME`), and `continue-on-error` on a step fails it;
    - fix 3 (`6654418`): the seal proves itself through the pin's own runner, no caller credential variable reaches
      a step, and `continue-on-error` on the job fails the pin.
- **The final review (2026-10-06, 04:05 to 05:30 PDT), three lenses on iac `860f55a` and copilot-mro `e4e8bb57`.**
  - **Lens A, the main deploy's runbook: FIX FIRST, 2 Important, 7 Minor.**
    - **I-1:** nothing checks the three database passwords typed at step 4 before step 6's apply. A typo in the grant
      or query password would show only at the first signup or query, after the deploy looks done.
    - **I-2:** the box's Weaviate version is never read before step 3 starts the pinned version on its only data.
    - Every phase 3 finding is closed, and the plan counts derive from the Terraform.
  - **Lens B, iac's code, scripts, guards and pins: FIX FIRST, 1 Important, 4 Minor.** The Terraform plans what is
    intended and the grants are exact. All five findings are gaps in the pins:
    - **I-1:** the image's commit labels are unpinned. A wrong edit would pass every test, then stop the POC at
      boot after step 6 replaced it.
    - **m-1:** guard 1 skips quoted `.env` words.
    - **m-2:** nothing would stop a `compose config` line printing every password to cloud-init's log.
    - **m-3:** the POC's volume stage runs only its happy path.
    - **m-4:** the IAM pin skips a role it cannot resolve.
  - **Lens C, the POC end to end: MERGE-READY, 4 Minor.**
    - **The two repositories agree:** the three address lines are byte-identical in both.
    - **m-1:** the runbook never proves a stop and start.
    - **m-2:** at a reboot Docker restarts the API before db-init runs, so db-init gates only the API's creation.
    - **m-3:** a refused dispatch leaves the runbook's "list again" endless.
    - **m-4:** the POC's password rotation has no login check.
    - **Also:** db-init's message is to name the unit's two lines; the clone keeps the GitHub token in `.git/config`.
  - **The 05:02 restart** cut both reviews' mutant runs short (about 40 mutants); the fix rounds run them.
  - **The rulings:**
    - one copilot-mro fix round;
    - iac in two rounds, one after the other on the one tree: F1 the pins and the token, F2 the runbook;
    - guard 1's compose allowance stays, with lens B's two fixes;
    - the IMDS hop limit of 2 stays (the API reaches Bedrock and S3 through the instance role);
    - the token on `git clone`'s argument list at first boot stays in the user-data Future Improvement.
  - **A merge-order fact:** on the branch, `provision_rls.py` treats a missing `flynapse_readonly` role as fatal, and
    nothing on the POC creates it. `langgraph-merge` (`2b364e03`) makes it a note, and the deploy clones `aws-deploy`
    after the merge, so the deploy is safe. A POC cloned from the branch itself would fail at first boot.
  - **Learnings:**
    - **Tests that run shell scripts on this box can reach the real AWS account.** `/usr/local/bin/aws` finds
      `~/.aws` even with `HOME` unset. Every such test puts refusing `aws`, `gh` and `docker` stubs first on `PATH`
      and sets its own `HOME`.
    - **Compose behaviour cannot be proven without Docker here:** overlay merges, `up -d` re-running an exited
      one-shot, and `run` ignoring `container_name`. The final review checks it against the Compose spec, and the
      deploy's checks are the live proof.
    - **db-init's failure message says "run compose up -d again".** That leaves the startup unit disabled after a
      failed first boot. The README gives the unit's two lines instead, and the final review's fix round corrects
      the message.
    - **Memory: the machine restarted at 05:02 (2026-10-06).** The guest ran out of RAM and its 16 GB of swap, with
      four of this program's agents and another session's sharing the box. The slot script checks free memory only
      when a run starts. Heavy runs now ask for 10 GB free (`pytest-slot.sh -m 10`), one at a time per agent.
    - **A killed mutant run leaves its mutant in place.** `mutant.sh` cannot restore a file on SIGKILL. After a
      restart, compare each extract or worktree with its commit before any further run. Two held a mutant on
      2026-10-06.
    - **A browser reaches the POC through a tunnel with no change.** `http://localhost:3000` is already a default CORS
      origin, and the dashboard's sign-in needs no callback URL.
- **The fix rounds (2026-10-06, 06:10 to 09:45 PDT).**
  - **copilot-mro** (`e4e8bb57..eb7aef68`):
    - db-init's schema-change message now ends with the unit's two lines (`systemctl enable poc-stack`, then
      `systemctl restart poc-stack`), pinned word for word;
    - the reboot comment and its family are corrected: a new API starts only after db-init, while a reboot restarts
      the existing one;
    - a new test pins the overlay's API environment exactly. Without it, pointing the API at the superuser passed
      every test.
    - Lens C's 14 mutants and 5 more die; the full suite equals P4-3's.
    - **Its re-review:** MERGE-READY, with two Minors taken in a short second round.
  - **iac F1** (`860f55a..76369c7`):
    - the six image labels are pinned and tied to the setup's image check;
    - guard 1 reads dequoted words;
    - the setup's compose calls are pinned to `pull` and `up -d`;
    - the volume-stage tests run on both scripts;
    - the IAM pin fails on a role it cannot resolve;
    - the POC clone's remote goes back to the token-free URL right after the clone.
    - 662 passed; lens B's 26 mutants and 7 more die.
  - **iac F2** (`76369c7..df80315`), the runbook:
    - step 6 tests each role's password before the apply;
    - the box's Weaviate version is read before step 3;
    - the retry checks the image;
    - a stop-and-start check, and the IMDS warning's recovery;
    - a login check per rotated POC role;
    - the tunnel;
    - "A schema change" tied to db-init's message;
    - lens A's text minors.
    - 679 passed. It stopped at its size limit before its seven mutants, which its re-review runs.
  - **Dashboard fix 4** (`ce36b07`): the seal's self-test proves its order and its tool list. Every step runs with
    the session bus and the instance metadata service switched off. Merged into `agent_sdk` (`0795b14`) after its
    gate: the five-file lane 35/35, lint and tsc clean. A push to `agent_sdk` publishes nothing, since the workflow
    runs on `main` with `[publish]` or by hand.
  - **The tunnel, ruled:**
    - `-o ExitOnForwardFailure=yes`, as the README's other tunnels;
    - a free one of local ports 3000 and 3001, both default CORS origins of the API. On the owner's machine, the
      local Grafana holds `127.0.0.1:3000`.
  - **Learnings:**
    - **After the 05:02 restart, every local container port but Phoenix's reset connections from WSL,** while the
      data inside was intact. A raw TCP probe per port shows it; `ss` still lists the listener. One stop and start
      of the containers, on the owner's word, fixed it.
    - **The account's session rate limit stopped three agents at about 07:00.** Each resumed from its transcript
      after the reset, once its tree and extract were checked.

## Future Improvements

- **The network-interface guard does not follow a data-source indirection to the box's interface (phase 2 fix
  round, concern 7).** A security group attached through a `data "aws_network_interface"` lookup would pass. No such
  lookup exists today. *Complete fix:* resolve data sources in the guard, or fail on any `aws_network_interface*`
  data source in the root.
- **The prune cannot reach incomplete multipart uploads (prune round, concern 2).** An upload stopped past the CLI's
  8 MiB threshold leaves parts holding part of a dump. No S3 API reads them, and the lifecycle aborts them after a
  day, but S3 may run that abort late. *Complete fix:* grant `s3:ListBucketMultipartUploads` and
  `s3:AbortMultipartUpload` on the prefix, and have the prune abort uploads older than its threshold. The CLI's own
  cleanup of a failed upload then works too.
- **The prune trusts the box's clock (prune round, concern 3).** A clock far ahead would delete young dumps, the
  night's own included. EC2's time sync makes this remote. *Complete fix:* take "now" from S3 (the listing
  response's `Date`), or refuse to prune when the box's clock runs ahead of it.
- **The backup test's unit-file parser duplicates the startup test's (prune round, concern 6).** *Complete fix:* one
  helper under `tests/unit/demo_box/`, after the owner confirms.
- **The prune reads keys from the CLI's text output (prune review, m-4's full fix).** A key with a tab or a newline
  in it cannot be represented exactly, so the fix round makes such lines fail the run instead. The fix round's
  re-review found the silent cases: the line before the newline is still read and its key deleted, and the run exits
  0 when the part after the newline is `None` or reads as a row of its own (a blank time reads as midnight). Only an
  operator can write such a key. *Complete fix:* list
  with `--encoding-type url` and decode each key exactly (S3's form encoding, decoded as `unquote_plus` does, keeping
  a trailing newline).
- **Two nights without a prune do not fail the unit (prune review, m-5).** *Complete fix:* run the prune in a unit
  of its own, without `Requires=docker.service`, triggered after the dumps or on its own timer.
- **The prune trusts that a delete deletes (prune review, m-6).** *Complete fix:* fail the run when a delete's
  response carries a delete marker or a version id.
- **The bucket's expiry is scoped to the backup prefix (prune review).** A changed prefix orphans the old one's
  dumps. *Complete fix:* make the expiry cover the whole bucket, which holds only backups, and let the api's
  backups row read that form.

- **The GitHub token sits in the instance's user data** (pre-existing). On the POC it is also on `git clone`'s
  argument list during the first boot (the final review's lens C); iac's fix round F1 removes it from the clone's
  `.git/config` afterwards. *Complete fix:* read it at boot from SSM, like the box's other secrets, and hand it to
  git through a credential helper, never the URL.
- **Postgres runs at the image's defaults** (128 MB shared buffers, 64 MB `/dev/shm`) with no memory limit, on a box
  it shares with Weaviate, Phoenix and the collector. *Complete fix:* tune it for a 16 GB box, with a compose memory
  budget.
- **`aws s3 cp -` needs `--expected-size`** once a dump passes about 50 GB.
- **SSE-KMS for the dumps (phase 2 review, I-1's complete fix).** A customer managed key whose policy admits only the
  box's role and the owner, in place of a deny list to keep up to date. It costs about $1 a month, plus requests.
- **The ingest Lambda's Postgres (owner: after the deploy).** Settings by reference, its password read from the
  parameter store at start, and 5432 from `lambda_sg`.
- **The backup's two `[SIGINT]` tests fail when pytest starts with SIGINT ignored** (under `nohup`, or as a
  script's background job). The failure is false, not a vacuous pass (phase 1 re-review, m-c). *Complete fix:* start
  the script through a small exec wrapper that resets HUP, INT and TERM to their defaults.
- **App Runner deploys the mutable `:latest` (phase 3's review, I-1's complete fix).** Every deployment pulls
  `:latest` as it is at that moment: step 6, a re-apply after a rollback, and a rotation's redeploy. api's CI pushes
  it from both `main` and `develop`. The runbook checks the image's tags first. *Complete fix:* deploy by the
  immutable `:<sha>` tag that the same CI run pushes, set in Terraform.
- **The restore's first provisioning run fails by design (phase 3, concern 3).** It creates the roles, then refuses
  the empty database, and the runbook names the message to expect. An expected failure in a runbook invites the
  owner to pass over a real one. *Complete fix:* a roles-only mode in copilot-mro's `provision_rls.py`, so every
  step of the restore exits 0.
- **The untold-bucket check counts seven configuration types (phase 3, concern 8).** Other resources that name a
  bucket, such as `aws_s3_bucket_acl` and `aws_s3_object`, are not counted. ACLs are closed by the enforced
  ownership, and an object write is no read. *Complete fix:* count every resource type with a `bucket` argument.
- **App Runner is closed to new customers** (AWS's pages, 2026-10-05). The existing service is unaffected; a new
  account could not create one. *Complete fix, if ever needed:* move the API to ECS on Fargate.
- **api's GitHub build cannot build the API image (owner, 2026-10-05: hand-built for this deploy).** Since `d4974ab`
  (2026-07-22) api declares `mro-copilot`, `core`, `flynapse-utils` and `shift-optimizer` as local path
  dependencies, under its own comment that they must stay on CodeArtifact. Its CI checks out api alone, and its wheel
  check refuses a `file://` requirement, so every push to `main` or `develop` fails before the image. *Complete fix:*
  CI swaps the path dependencies for published versions at build time (or checks the siblings out at pinned
  commits), the siblings publish in order (flynapse-otel, utils, core, copilot-mro), and api builds `:latest` again.
- **A bad prune threshold aborts the prune in silence (prune fix round 2, concern 3).** `PRUNE_AFTER_DAYS` is a
  constant, so only an edit reaches it, and the keep test catches one by its behaviour. But a non-numeric value makes
  bash's arithmetic abort the whole `prune || failed+=(...)` line, and the run exits 0 having pruned nothing.
  *Complete fix:* refuse a non-numeric threshold before the prune, or run its arithmetic where a failure fails the
  run.
- **A second `TimeoutStartSec=` is refused only by an unpack's `ValueError`** (prune fix round 2, concern 2). It fails
  the test all the same. *Complete fix:* a named assert, like the `Type=` check.
- **No repo test can see an override on the box itself** (prune fix round 2's re-review). A drop-in or `systemctl
  edit` changes the loaded unit without changing the repo's files. *Complete fix:* the setup script checks the
  loaded units after install (`systemctl show -p Type,TimeoutStartUSec` on the service, and the timer's delays).
- **`span`'s refusal message omits `infinity`** (prune fix round 3, concern 4). Both unit tests refuse `infinity` on
  purpose, but the message says systemd reads only digits and units. *Complete fix:* name `infinity` in the message.
- **A second `aws_s3_bucket` naming the backup bucket would read as another bucket's** (phase 3 fix round 1b,
  concern 2). Only a deliberate `import` reaches it, and the bucket guard does not count `aws_s3_bucket` itself.
  *Complete fix:* count it, and refuse a second resource for the same bucket name.
- **Bucket-level actions are not counted by the readers guard** (phase 3 fix round 1b, concern 3), for example
  `PutBucketOwnershipControls`, `PutBucketPublicAccessBlock` and `PutReplicationConfiguration`. Each needs a second
  step to reach a dump, or affects only availability. *Complete fix:* count every action that can change who reads
  the bucket.
- **The hand-built image takes third-party versions from pip at build time** (phase 3 fix round 1a2, concern 2), as
  api's own production build does, not from api's `poetry.lock`. Two builds of the same commits can differ.
  *Complete fix:* export the lock's pins as a constraints file and install with it.
- **The image check proves only the api commit** (phase 3 fix round 1a2, concern 4). The sibling repositories'
  commits are printed and kept as image labels, not checked. The script also does not warn when a checkout has
  uncommitted changes. `git archive` stages the commit, so such changes never reach the image, but step 4 runs from
  those checkouts. *Complete fix:* the check reads all six commits from the labels, and the script refuses a dirty
  checkout.
- **App Runner's HTTP health check stays off** (phase 3 fix round 1a2, concern 8). Its comment's condition is now met:
  the image serves `/health/live` at the root. Over TCP's check it adds little for this deploy, since an image that
  fails at startup never opens its port. *Complete fix:* turn it on in a later apply, path `/health/live`.
- **No script runs the API's two boot checks outside a boot** (phase 3 fix round 1d2, concern 1). Step 6's dry run
  uses the provisioning scripts' verify-only modes instead. It does not check the database's row-level security as
  App Runner's role sees it, and once tenants exist nothing before a deploy checks for partitions no tenant names.
  *Complete fix:* a copilot-mro script that runs both boot checks, read only, as the app's role, for the runbook to
  call.
- **The Weaviate schema step needs seven legacy collections** (POC design, finding 1; round 1d2, concern 3). The
  provisioner copies six collections' shape from live legacy collections, so a Weaviate without them (every fresh
  client box) cannot get its schema, and the provisioner stops at the first missing one. *Complete fix:* commit the
  seven collections' intended properties and vectors, generated once from a cluster that has the sources; the
  provisioner and its verify mode read that file when a source is absent, and a pin regenerates and compares it.
  Then the POC's old collections may go.
- **The client kit's restart files still pull `main` and `latest`** (POC design, finding 2). Our deploy now leaves
  both alone, but two other paths still move them: dashboard's publish job pushes `dashboard-ecr:latest` on every
  `[publish]` commit to its `main`, and api's image build (broken since July) pushed `flynapse-api-ecr:latest`.
  *Complete fix:* once the owner confirms which client boxes exist, give each its own pinned tags and branch, then
  retire `copilots.service` and `restart-services.sh` from copilot-mro.
- **The POC's S3 policy reaches every bucket** (POC design). *Complete fix:* narrow it to the buckets the POC's API
  uses, then drop the role from the dumps bucket's deny. That is the precondition for any S3 backup of the POC.
- **The POC's containers reach its instance role, and its API port is public** (the final review's lens C, 2026-10-06).
  - The metadata hop limit of 2 lets a container fetch the role's credentials. The API needs that: it reaches
    Bedrock and S3 through the role, with no static keys.
  - Ports 8000 and 4318 admit the whole internet (the design kept the group unchanged).
  - So a request forgery in the API would reach the role, and with it the S3 policy above.

  *Complete fix:* narrow the S3 policy first. Then admit 8000 and 4318 only from the owner's address, which the SSH
  tunnel the owner chose already allows for. Or put the API behind a proxy that alone reaches the metadata service.
- **Formats copied between iac and copilot-mro, with nothing comparing them** (P4-3, concern 2). Several values are
  written twice, once in each repository:
  - the three `.env` address lines;
  - the unit's and script's install paths;
  - the box's paths.

  The final review compared them byte for byte, but a test in one repository cannot read the other on this branch.
  *Complete fix:* a cross-repository pin run where both checkouts sit side by side (the workspace's `tests/_root.py`
  `sibling_repo`), at the merge gate.
- **The POC's `.env` holds the Azure key and Grafana's password, and the dashboard reads that file** (POC design).
  *Complete fix:* move both into the root-only secrets file, and take the GitHub token out of user data.
- **Nothing after the deploy proves email works** (phase 3 fix round 1e, concern 2). Step 6 checks that the secret
  holds both keys, not that Gmail accepts the login or the default sender. *Complete fix:* a step 7 check that sends
  one test message to the owner through the API.
- **The POC sends no email** (round 1e, item 4). Its `.env` carries no email setting, and the hand-built image carries
  none, so once the POC runs that image it sends none. Email is not needed for the POC to boot, and a client install
  brings its own mail login. *Complete fix:* if the POC should send mail, add the two keys to its root-only secrets
  file at first boot.

- **The backup's unit pins check that a value is present, not the timer's whole effect** (prune round 5, concern 1,
  and its re-review's N-1; pre-existing). Each of these passes every demo-box test, yet stops the nightly run:
  `Persistent=true` followed by `Persistent=false`; an emptied `WantedBy=`; an empty `OnBootSec=` (or any `On*=`
  trigger key) after `OnCalendar=`, which clears every trigger; `Unit=` naming another service. The erasure bound
  still holds, because the bucket's lifecycle rule expires the prefix after 13 days; what stops is the backups.
  *Complete fix:* pin each key's final value list as systemd computes it (the last assignment wins; an empty one
  clears the list before it), treat every `On*=` key as one trigger list, and refuse any `Unit=` other than the
  backup service. Also pin the header check's top control character (`\x1f`).
- **copilot-mro tests fail intermittently under `-n`** (prune round 5, concern 4; P4-1, concern 4):
  `tests/agent_sdk/techpub/test_techpub_tools.py::test_final_round_trip_closes_the_delta_new_then_nil` answered
  `UNREACHABLE` where `NIL` was expected once, and passed alone and with its file run serially. An isolation bug,
  outside this plan's code. Two ingest tests (`test_document_writers_name_their_operator[crew_manual_parser]`,
  `test_ifim_revision_identity`) also failed once on one worker and pass serially; an earlier test replacing a
  module in `sys.modules` is the likely cause. A wall-clock test fails the same way under heavy load (P4-2):
  `tests/unit/lang_agent/test_manual_research_graph.py::test_parent_fans_out_two_compiled_research_graphs_and_waits_to_join`
  missed its 1 s wait at a load of 12 to 19, and passed serially 10 times. *Complete fix:* find the state each shares
  across a worker and isolate it, and give the wall-clock test a bound that does not depend on the host's load.
- **The API image's health check calls `curl`, which `python:3.11-slim` lacks** (P4-2, concern 7). On the POC,
  `docker ps` may show the API unhealthy while it serves; nothing waits on it, and the runbook reads `/health/ready`
  instead. *Complete fix:* a Python health probe in the image, or `curl` installed in it.

- **ECR tags stay mutable** (round 1f, concern 5). Step 6 relies on `describe-images` showing one tag and the
  build's push time to notice a replaced `:<api commit>` image. *Complete fix:* make commit tags immutable (ECR's
  tag-mutability exclusions can keep `latest` mutable for the client path).
- **The runbook's inline-code scans read one line at a time** (round 1f, concern 7). A code span wrapped across two
  lines escapes them. *Complete fix:* scan joined paragraphs, or refuse a wrapped span.

- **Rotating a box-only password replaces the instance** (round 1c, concern 3). The box reads those secrets at
  first boot, so a rotation is a full box outage, the API's database included. *Complete fix:* rotate them in
  place: rewrite the root-only secrets file and recreate only the containers that read it.

- **Grafana's admin password is regenerated into the POC's `.env` on every replacement** (P4-4, concern 6;
  pre-existing), while Grafana keeps its own in its database. *Complete fix:* generate it once into the root-only
  secrets file, beside the Postgres passwords.

- **The setup's compose pin finds calls by name** (iac F1, concern 5). A helper renamed along with every caller is
  seen only if the stubbed boot runs it. Like guard 1, the pin reads no heredoc body. *Complete fix:* resolve shell
  functions before the scan, and scan heredoc bodies that are executed.
- **The demo box keeps its GitHub token in its clone's `.git/config`** (iac F1, concern 7). This is by design: its
  startup unit pulls at every boot. The POC's clone no longer keeps it. *Complete fix:* a credential helper that
  reads a root-only file, so no token sits in a world-readable tree.
- **The dashboard pin's stand-ins do not cover a Windows `aws.exe` reached through WSL interop** (dashboard
  re-review, route 2). A Linux workflow's step never calls it. *Complete fix:* a fixed step `PATH`, not the caller's.
- **The dashboard pin refuses `${{ secrets.* }}` and `${{ github.token }}` only in the steps' own `env:` and `run:`
  and in the build's tags.** A top-level `env:` value reaches a step raw. That is harmless in the test, which holds
  no credential, but a later top-level secret would give every step the token. *Complete fix:* refuse them in the
  workflow's and the job's `env:` too.

## Lessons

- **Ask what a server is for before recommending how it connects (2026-10-05).** I recommended giving the POC server
  the main box's Postgres, assuming it was a second copy of the internal deployment. The owner corrected that: it
  replicates a client install, with everything on one box. A round was built on the wrong premise and reverted. Rule:
  when a recommendation depends on a component's purpose, state the assumed purpose in the question, so the owner can
  correct the premise before choosing.
- **Name the slices an implementer reads (2026-10-05).** Round 1d's brief listed three reports, the plan, eight files
  and "every guard that reads" the area. The implementer spent 356k tokens reading before its first edit, and stopped
  after one item. Rule: a brief names the sections and line ranges to read, points at a prior round's design instead
  of its whole report, and says "read only what each item names".
