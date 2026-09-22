# Claims packet: iac r4 (the r3 fix pass, `d52e8b8..74346bb`) — PARTIAL — in progress

Independent adversarial review (Opus), 2026-09-22, read-only. Each commit was taken with `git archive <sha>` into
`scratchpad/iac-review-r4/at-<sha>/` and, because 20 tests need `.git`, also as a `git clone --no-hardlinks` of
`/home/aditya/Code/iac` checked out at that sha (`clone-<sha>/`; the HEAD clone matched its archive byte for byte,
`__pycache__` aside). Every pytest ran under `/home/aditya/Code/pytest-slot.sh` with `-n 2`, one process at a time.
Mutation proofs use `/home/aditya/Code/mutant.sh` against a separate clone at `74346bb`. No code tree was edited,
checked out, stashed or committed; no terraform, AWS, docker or live run. Working notes:
`/home/aditya/.claude/scratch/obs-merge/iac-review-r4/`.

| range | repo | worktree | branch | commits |
|---|---|---|---|---|
| `d52e8b8..74346bb` | iac | `/home/aditya/Code/iac` | `obs-merge` | `4afc68f` P2-2 · `013c9ae` P2-1 · `0a31a72` P2-3 · `37f82c4` P3-1 · `9bb3c3d` P3-2 · `d2c7aac` P3-3 · `56e7673` P3-6 · `d86b378` P3-7 · `9828e17` P3-8 · `74346bb` P3-4 |

## How it was run

- **Lane:** `DEBUG=false PYTHONPYCACHEPREFIX=<fresh> pytest-slot.sh -- python -m pytest -q -p no:cacheprovider -n 2`
  (`/home/aditya/Code/api/.venv/bin/python`), from each clone's root. rootdir = the clone.
- **Validators:** `bash scripts/validate_dashboards.sh`, `python scripts/validate_alarms.py`,
  `python scripts/validate_metric_vocabulary.py`; each one's own exit status captured.

| commit | pytest | exit | dashboards | alarms | vocabulary |
|---|---|---|---|---|---|
| `d52e8b8` (base) | 266 passed | 0 | 0 | 0 | 0 |
| `4afc68f` | 266 passed | 0 | 0 | 0 | 0 |
| `013c9ae` | 266 passed | 0 | 0 | 0 | 0 |
| `0a31a72` | 267 passed | 0 | 0 | 0 | 0 |
| `37f82c4` | 267 passed | 0 | 0 | 0 | 0 |
| `9bb3c3d` | 268 passed | 0 | 0 | 0 | 0 |
| `d2c7aac` | 272 passed | 0 | 0 | 0 | 0 |
| `56e7673` | 273 passed | 0 | 0 | 0 | 0 |
| `d86b378` | 274 passed | 0 | 0 | 0 | 0 |
| `9828e17` | 274 passed | 0 | 0 | 0 | 0 |
| `74346bb` | 275 passed | 0 | 0 | 0 | 0 |

Every commit is green at its own HEAD and the counts match every commit message (266 → 275).

(attacks, mutation proofs, commit-message audit and the claims table follow as they land)

---

## PARTIAL-2 (paused by owner request 2026-09-22; resumes from `PAUSED.md` in the notes dir)

**Mutation harness so far.** `mutant.sh` (single-file edits, md5-verified restore) and `runmut.sh` (file-creating
mutants, `git checkout -- . && git clean -fdq` then `git status --porcelain` must be empty) against `scratchpad/
iac-review-r4/mut/` at `74346bb`. Aimed runs first; every survivor I report below was RE-RUN against the FULL lane
(`-n 2 tests`, 275 tests) with the mutant applied and passed there too. 39 runs so far: 24 killed, 15 survived
(9 of the survivors are deliberate controls or the stated design; 6 are gaps, listed under findings).

### Findings so far (all P3; no P0/P1/P2 found yet)

**P3-A (`013c9ae`, IR4 Weaviate): the client security groups' EGRESS is unread.** W11 (`lambda_sg` egress cut to
443/tcp) → aimed 3 passed, FULL 275 passed. The docstring derives "the security groups the process egresses from"
but never reads their egress rules; a hardened Lambda SG produces exactly the connect timeout the guard is named
for. Fix: for each client group, require an egress rule covering both ports (or `-1`/all) to any destination.

**P3-B (`0a31a72`, IR4 POC `.env`): the guard reads the FIRST `cat > ./.env` heredoc only.** Four shapes that change
what the container actually reads all pass the FULL lane (275 passed each): L9b (a second `cat >> ./.env << EOF2`
appending `LOGURU_DIAGNOSE=YES`), L9c (`echo "LOGURU_DIAGNOSE=YES" >> ./.env`), L9h (a second TRUNCATING
`cat > ./.env << EOF2` later in the script, which wins at runtime), L9s (`sed -i` rewriting the line). The docstring's
"an `export` elsewhere never reaches a compose container" is true (L9x survives, correctly) but the bound is to one
heredoc's body, not to the file's final content. Fix: read every `> ./.env` / `>> ./.env` / `tee` / `sed -i … .env`
site, or fail closed when more than one write to `.env` exists.

**P3-C (`4afc68f`, IR4 `_hcl_blocks`): the second "one lexical body" asymmetry — name escapes.** `_structured_file`
runs `_decode_name_escapes` before scanning; `HclFile.__init__` does not. W10u: a new Lambda with
`"WEAVIATE_URL" = "http://${aws_instance.weaviate_observability.private_ip}:8080"`, no gRPC port, no `vpc_config`,
classified REQUIRED with a literal `LOGURU_DIAGNOSE = "NO"` → FULL lane 277 passed. `env_assignments` reads that key
as `WEAVIATE_URL`; `attributes()` drops it. Contrived (same tier as r3's P3-8). Fix: decode name escapes in
`HclFile.__init__`, or reuse `_structured_file`'s prepared text.

**Note (not a finding):** the Weaviate client scan still fails OPEN on a non-literal env shape (W18 `dynamic
"environment"`, W19 `variables = merge(...)`: aimed 3 passed each), but the FULL lane kills both (W18R, W19R: 1
failed) through the LOGURU REQUIRED rule's fail-closed on the same block — as long as every Weaviate client is
REQUIRED there, which today's classification enforces. Stated so the coupling is visible.

### Mutation results so far

| mutant | file | edit | aimed | FULL | reading |
|---|---|---|---|---|---|
| H1 | `tests/_hcl_blocks.py` | `token = at` (the r3 offset put back) | KILLED (`test_escapes_comments_and_heredocs_do_not_move_a_boundary`) | — | P2-2 fix proven |
| W10 | `lambda.tf` | new Lambda, `"WEAVIATE_URL" = …` quoted, no gRPC/VPC | KILLED (both Weaviate checks) | — | r3 W10 now red |
| W10p | `lambda.tf` | same, `("WEAVIATE_URL") = …` | KILLED (both) | — | paren key read |
| W10u | `lambda.tf` (+REQUIRED) | same, `"WEAVIATE_URL"` | SURVIVED | 277 passed | **P3-C** |
| W18 / W18R | `lambda.tf` (+REQUIRED) | `dynamic "environment"` client | SURVIVED | 1 failed (LOGURU) | note |
| W19 / W19R | `lambda.tf` (+REQUIRED) | `variables = merge(local.x, {…})` | SURVIVED | 1 failed (LOGURU) | note |
| W1 | `ec2.tf` | content `from_port = to_port = 8080` | KILLED (`…admits_both_ports…`) | — | r3 W1 red |
| W2 | `ec2.tf` | `protocol = "udp"` | KILLED | — | r3 W2 red |
| W3 | `ec2.tf` | instance on `poc_replica` SG | KILLED | — | r3 W3 red |
| W4 | `apprunner.tf` | URL host → `poc_replica` | KILLED | — | r3 W4 red |
| W9 | `apprunner.tf` | `egress_type = "DEFAULT"` | KILLED | — | r3 W9 red |
| W7 | `ec2.tf` | 50051 dropped from `for_each` | KILLED | — | control still red |
| W12 | `ec2.tf` | admission by `cidr_blocks` instead of SGs | KILLED | — | fails closed, as stated |
| W14 | `ec2.tf` | `for_each = toset([...])` | KILLED | — | fails closed, as stated |
| W16 | `apprunner.tf` | URL host `public_ip` | KILLED | — | fails closed, as stated |
| W20 | `ec2.tf` | SG admits `apprunner_sg` only | KILLED | — | Lambda refused |
| W13 | `ec2.tf` | `iterator = "port"`, `port.value` | SURVIVED | 275 passed | control: iterator read correctly |
| W11 | `lambda.tf` | `lambda_sg` egress → 443/tcp only | SURVIVED | 275 passed | **P3-A** |
| L9 | `poc_ec2_setup.sh` | heredoc gains `LOGURU_DIAGNOSE=YES` | KILLED (`…turn_loguru_diagnose_off[aws_instance.poc_replica]`) | — | r3 L9 red |
| L9rm | `poc_ec2_setup.sh` | the NO line removed | KILLED | — | as claimed |
| L9g | `poc_ec2_setup.sh` | `LOGURU_DIAGNOSE=$LOGURU_DIAGNOSE` | KILLED | — | fails closed |
| L9q | `poc_ec2_setup.sh` | `LOGURU_DIAGNOSE="NO"` | SURVIVED | — | control: quotes stripped, correct |
| L9x | `poc_ec2_setup.sh` | `export LOGURU_DIAGNOSE=YES` outside the heredoc | SURVIVED | — | correct per docstring |
| L9b / L9c / L9h / L9s | `poc_ec2_setup.sh` | append heredoc / `echo >>` / second truncating heredoc / `sed -i` | SURVIVED | 275 passed each | **P3-B** |
| P1 | `ec2_poc.tf` | `user_data_replace_on_change = false` | KILLED (`…apply_the_env_they_configure[aws_instance.poc_replica]`) | — | as claimed |
| P2 | `ec2_poc.tf` | `ignore_changes = [ami, user_data]` | KILLED | — | as claimed |
| P3 | `ec2_poc.tf` | the replace-on-change line removed | KILLED | — | absent ≠ true |
| L11 | `lambda.tf` | `ignore_changes = [image_uri, environment]` | KILLED (`…apply_the_env…[aws_lambda_function.s3_pdf_processor]`) | — | r3 L11 red |
| L11b | `lambda.tf` | the same, multi-line list | KILLED | — | list parsing holds |
| L11c | `lambda.tf` | `environment[0].variables["LOGURU_DIAGNOSE"]` | KILLED | — | a key inside covers |
| L11d | `lambda.tf` | `ignore_changes = all` | KILLED | — | as claimed |
| L11t | `lambda.tf` | `ignore_changes = [image_uri, tags]` | SURVIVED | — | control: unrelated path |
| L11e | `apprunner.tf` | `ignore_changes = [source_configuration[0].image_repository[0].image_configuration]` | KILLED (`…[aws_apprunner_service.api]`) | — | a parent covers |
| L11f | `apprunner.tf` | `ignore_changes = [network_configuration]` | SURVIVED | — | control: unrelated path |

### Verified by reading (no mutant yet)

- `74346bb`: all five recorders exist in utils-obsm `utils/llm.py` at the stated lines (359, 425, 831, 1233, 1337)
  and each emits its family inside its own body (386; 466/473/522/529; 877; 1261-1272; 1375/1380).
  `note_embedding_cache_hits` is called from `utils/embedding_service.py:386,493`; copilot-mro-obsm does not call it
  directly. copilot-mro-obsm `tests/integration/otel/_emitted_series.py:186,188` STILL names
  `_record_embedding_cache_metrics` — the commit message credits that fix to "the utils lane", which cannot touch
  copilot-mro; nobody owns it (P3, process).
- utils `0e9b2a8`'s two other wrong names (`service.py:upload`, `processing.py:_index`) never appeared in iac: the
  platform-health note names files only, and each of the five Document Hub files it names emits a family
  (copilot-mro-obsm `service.py:1032`, `processing.py:292/542/549/570/577`, `cleanup.py:448/469`,
  `notifications.py:110/125`, `indexing.py:756`). Nothing to fix here. The pin test reads only backticked
  identifiers, so a wrong FILE name in either note is unguarded (contrived, P3 at most).
- `d86b378`: truthful today. `cb5d309d` is not an ancestor of copilot-mro `obs-merge` (`735f8213`) and
  `claude_cli_telemetry.py` does not exist there; it exists on `obs-merge-cli` (`a532a23c`) with
  `OTEL_SERVICE_NAME: "claude-code"`, logs on, metrics `none`. The DARK sentence parses under `STATE_GRAMMAR["DARK"]`.
- copilot-mro `main`'s `deployment/poc/docker-compose.yml` api service reads `./.env` via `env_file` and its
  `environment:` list sets no `LOGURU_*`, so the `.env` seat is real (compose `environment:` would override it).

### TODO (not yet examined) — in order

1. P3-2 (`9bb3c3d`): plant L5 (`*.tf.json`), L6 (registry module), L6b (`source = "../../other-repo/…"`, expected
   to SURVIVE — local-but-outside-repo), L6c (`git::` source), L4 (local-module ECS task), an `override.tf`.
2. P3-1 (`37f82c4`): L8 (`lambda_src/helpers/__init__.py` importing loguru), a nested-function import; and whether
   `source_dir` is read (the test hardcodes `lambda_src`).
3. P3-8 (`9828e17`): C2, C3 (`otel_claude_code_…`), the old pattern put back, `claude[._]code` regex (expected
   SURVIVE), a label value.
4. P3-6 (`56e7673`): the two "one exception" removals.
5. P3-7 (`d86b378`): DARK sentence removed; lowercased; WIRED flip without the merge (expected to pass — truth
   unchecked, stated).
6. P3-4 (`74346bb`): old name put back; a recorder dropped; a wrong file path (expected SURVIVE).
7. HCL trap probes against `_hcl_blocks` directly (heredoc, `$${`, comments, nested dynamic, jsonencode, for_each).
8. Commit-message audit table; the claims table proper; final verdict.
