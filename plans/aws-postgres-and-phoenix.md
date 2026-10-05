# AWS: Postgres and Phoenix as containers on the Weaviate box

Status: **phase 1 is done, and the box's dump prune round (with phase 1's three Minors) was reviewed MERGE-READY at
copilot-mro `93b64914`; phase 2 (the Terraform) is done at iac `3933f47` (re-reviewed MERGE-READY, OPEN 0); phase 3,
the runbook, is being built in iac with phase 2's four Minors (five commits in at `99f85b9`); the prune's fix
round is done at copilot-mro `5700c550` and in re-review** (2026-10-05, ~08:45 PDT). Phase 1 is the box's compose, first boot, setup script, nightly backup and startup unit. Phase 3 is the
runbook. It is built before the AWS deploy; the owner deploys to AWS only once all work is finished.

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
    test uses git's real 128; the pull runs with `GIT_TERMINAL_PROMPT=0`.
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
    - **Taken now, in a small fix round** (copilot-mro `93b64914..5700c550`, done, in re-review; 21 of 21 mutants
      killed, the non-db lane 16545 passed, 0 failed):
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
  - before changing `box_postgres_backup_prefix`, empty the old prefix: afterwards neither the prune nor the expiry
    covers it;
  - never turn on the bucket's versioning by hand: each prune delete would leave only a delete marker.

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
  in it cannot be represented exactly, so the fix round makes such lines fail the run instead. *Complete fix:* list
  with `--encoding-type url` and decode each key exactly (S3's form encoding, decoded as `unquote_plus` does, keeping
  a trailing newline).
- **Two nights without a prune do not fail the unit (prune review, m-5).** *Complete fix:* run the prune in a unit
  of its own, without `Requires=docker.service`, triggered after the dumps or on its own timer.
- **The prune trusts that a delete deletes (prune review, m-6).** *Complete fix:* fail the run when a delete's
  response carries a delete marker or a version id.
- **The bucket's expiry is scoped to the backup prefix (prune review).** A changed prefix orphans the old one's
  dumps. *Complete fix:* make the expiry cover the whole bucket, which holds only backups, and let the api's
  backups row read that form.

- **The GitHub token sits in the instance's user data** (pre-existing). *Complete fix:* read it at boot from SSM,
  like the box's other secrets.
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
- **App Runner is closed to new customers** (AWS's pages, 2026-10-05). The existing service is unaffected; a new
  account could not create one. *Complete fix, if ever needed:* move the API to ECS on Fargate.

## Lessons
