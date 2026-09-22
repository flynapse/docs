# Claims packet: core review r7 (`625c0d3..dc41caa`, 22 commits)

This is an independent adversarial review (Opus), done on 2026-09-21. No code tree was changed:
every run used a `git archive` copy in the reviewer's private scratch
(`scratchpad/core-review-r7/`). Every mutation was applied to a scratch copy, grep-confirmed, run,
restored, and its md5 checked against the HEAD blob; every restore matched. No DB MCP, no DDL/DML,
no docker, no AWS/Cognito. App-driving probes stubbed `utils.postgres` (a stub that raises on any
unstubbed read) and ran as pytest tests inside the scratch archive.

| repo | worktree | branch | range | HEAD at review | tree state |
|---|---|---|---|---|---|
| core | `/home/aditya/Code/core-obsm` | `obs-merge` | `625c0d3..dc41caa` | `dc41caa` | clean (checked: `git status --short` empty) |

Siblings: `utils-obsm` archived at `8572635`, `flynapse-otel` archived at `34c814a` (never the live
utils tree); every other sibling a read-only symlink. Lane recipe:
`ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test POSTGRES_USER=flynapse_app`
`PYTHONPATH=<ws>/core-obsm:<ws>/utils-obsm:<ws>/flynapse-otel`, `api/.venv/bin/python -m pytest
-p no:randomly -p no:cacheprovider -o addopts="-ra --strict-markers"`, run from the archive's
root, a fresh `PYTHONPYCACHEPREFIX` per run, pytest's own exit status recorded.
`rootdir` = `…/core-review-r7/ws-<sha>/core-obsm`; `core.__file__` = `…/ws-<sha>/core-obsm/core/__init__.py`;
`utils.__file__` = `…/ws-<sha>/utils-obsm/utils/__init__.py` (the 8572635 archive).

## Every commit at its own HEAD

| commit | unit | api | authz | db (F / E) |
|---|---|---|---|---|
| `625c0d3` (base) | 1869 + 2A | 1119 | 284 + 1U | 20 / 1 |
| `4040a82` M-PII-IDS | 1899 + 2A | 1119 | 284 + 1U | 21 / 1 (+ slip) |
| `0607160` M-SIGNUP-ORACLE | 1899 + 2A | 1121 + 1 flake | 284 + 1U | 21 / 1 (+ slip) |
| `66b0217` M-INVITE-FRAGMENT | 1899 + 2A | 1138 | 284 + 1U | 21 / 1 (+ slip) |
| `2158813` `_root.py` re-copy | 1899 + 2A | 1138 | 284 + 1U | 21 / 1 (+ slip) |
| `871c0f2` slip fix-forward | 1899 + 2A | 1138 | 284 + 1U | 20 / 1 |
| `0753e2d` G.117 | 1902 + 2A | 1138 | 284 + 1U | 20 / 1 |
| `b9a2343` plan | 1902 + 2A | 1138 | 284 + 1U | 20 / 1 |
| `b31bd00` header-only adapt | 1902 + 2A | 1138 | **285** | 20 / 1 |
| `a7bb837` F1 | 1918 + 2A | 1138 | 285 | 20 / 1 |
| `9188794` F2 | 1934 + 2A | 1138 | 285 | 20 / 1 |
| `2abc449` F4 | 1934 + 2A | 1144 | 285 | 20 / 1 |
| `f8d28c7` F11 | 1934 + 2A | 1144 | 285 | 21 / 1 |
| `94e0502` oracle ext. | 1934 + 2A | 1146 | 285 | 21 / 1 |
| `0e82657` F3 | 1936 + 2A | 1146 | 285 | 21 / 1 |
| `7438263` F5 | 1939 + 2A | 1146 | 285 | 21 / 1 |
| `360088f` nits | 1939 + 2A | 1146 | 285 | 21 / 1 |
| `3123800` F7 | 1954 + 2A | 1146 | 285 | 21 / 1 |
| `a58995a` F8 | 1954 + 2A | 1146 | 285 | 21 / 1 |
| `77a95bd` F9 | 1954 + 2A | 1151 | 285 | 21 / 1 |
| `60acad9` F10 | 1954 + 2A | 1154 | 285 | 21 / 1 |
| `c2daac0` plan | 1954 + 2A | 1153 + 1 flake | 285 | 21 / 1 |
| `dc41caa` plan | 1954 + 2A | 1154 | 285 | 21 / 1 |

Key: `2A` = two reds that are an artefact of the symlinked scratch workspace
(`test_sibling_variant_picks_the_checkout_that_matches_this_one`,
`…_falls_back_to_the_bare_name_when_there_is_no_twin`: `sibling_variant` resolves the git worktree
list to `/home/aditya/Code/api-obsm` while the candidates are the symlink paths). Proven: the same
file run in the real `core-obsm` tree at `dc41caa` (read-only, `-p no:cacheprovider`, pycache
prefixed) = 57 passed, and `git status` stayed empty. `1U` = `test_the_tenants_door_is_shut_and_that_is_deliberate`,
red at `625c0d3..b9a2343` ONLY because the brief's utils (`8572635`) contains utils `1ca934f`
(M-STACK-HEADERS); under utils `d7e1541` (= `1ca934f^`) authz is 285/285 at `625c0d3` and `b9a2343`.
`b31bd00` is the adaptation. `flake` = `test_the_sixty_first_request_in_a_minute_is_429` (202 ≠ 429,
timing, older than the range) at `0607160` and again at the docs-only `c2daac0`; the file re-run alone: 10 passed both times. The implementer's `60acad9` numbers (unit 1956 = 1954 + the 2 that pass in the real tree, api 1154, authz 285, db 574P/21F/1E/2S/2XF) reproduce exactly.

db lane, by failure-id set (not count): `625c0d3` = 19 traceparent (18 one-shot + the column-set
check) + the G.61 1F + 1E. `4040a82..2158813` = that + the recorded slip
(`test_a_refusal_by_address_is_logged_loudly_and_names_neither_secret`), gone at `871c0f2`.
`f8d28c7..dc41caa` = that + `test_traceparent_is_nullable_text_with_no_default` = **20 traceparent +
G.61 1F + 1E, exactly the expected set** (set md5 identical at every commit from `f8d28c7`). All 20
are the missing column: 17 `UndefinedColumn … "traceparent"`, 1 `42703` inside the RLS case, the
column check's LIVE half ("live columns off the declared shape"), and the shape test's C9 message.
One data-dependent skip (`test_tenant_teardown_db.py:1000`, "every tenant on this database holds an
operator") ran instead of skipping at `4040a82` only — shared test-DB state, older than the range.

**No commit is red at its own HEAD for a reason the plan does not already record.**

---

## Findings, ranked

### No P0, no P1

No content leak ships in the range. Every one of the 15 converted log statements names ids; the
two signup refusals and the unresolved-signup refusal are byte-identical (status, body, every
header) and so are the flag-UP and flag-DOWN existing-address answers; the POST and GET preview
answer identically for every status including the two the commit did not pin (`accepted`, a
server fault); no token reaches any log line on either door. What follows are guards that pass a
plausible regression, and claims in the range that say more than the guard holds.

### P2-1 (sev 1): the M-PII-IDS sweep's sink set is narrower than this repo's other log guards — two realistic regressions pass all four lanes

`tests/unit/observability/test_core_logs_name_people_by_id.py:95` (`_is_log_call`), `:57` (`_PERSONAL`),
`:62` (`_RECORDS`), `:108` (`_neutralised`), `:145` (`_read_for_a_field`).

- **The documented historical defect passes.** `http_errors.internal_error(context)` LOGS its
  `context`, and its own docstring says "one caller put the email address it was looking up into
  context". Mutant `pii2`: `core/resources/user/user_endpoints.py:1757` →
  `raise internal_error(f"Error getting user by email {email}")` on the ANONYMOUS
  `GET /users/email/{email}` door. unit+api+authz **3393 passed**; db failure set identical to the
  HEAD baseline. The exception-text guard derives logging helpers as sinks; this guard does not.
- **A whole profile dict under an unlisted name passes.** Mutant `pii1`: after
  `user_endpoints.py:1588` add `logger.info("Updating user fields", user_id=…, tenant_id=…,
  changes=update_data)` (`update_data` = the body's name, email, preferences). unit+api+authz
  **3393 passed**; db identical to baseline. `update_data` is built from `user_data.dict()`, and
  `_read_for_a_field` exempts `user_data` because it is the receiver of `.dict` — so
  `.dict()` / `.model_dump()` of the request body is read as "a field", not the record.
- Plant sweep over the guard's own `personal_log_reads` (probe `pii_plants.py`): **22 of 33 leak
  shapes missed**, 18 of them outside its declared blind spots — a person's `name` (not in the
  vocabulary at all), `mail` / `e-mail` / `address` keys, `.dict()`/`model_dump()`, a response
  model in an f-string, a row found BY the address then logged whole, an invitation row fetched and
  logged whole, a logger method alias, `functools.partial`, `getattr(logger, "info")`,
  `sys.stderr.write`, `pprint`, `json.dumps(user)` (any attribute-call neutralises its argument),
  `rsplit("@",1)[-2]` and `split("@")[:1]` (read as the domain half); plus span attributes and
  exception messages, which the file does not claim. (Declared and missed: a `self` stash, a
  cross-function hand-off.)
- Floor and witness: present (`len(swept) >= 150`, 155 measured; six named witness files). The
  converted functions are pinned by equality of their id keywords; mutant `pii0` (restore
  `email=user_data["email"]` in `UserService.create_user`) is RED.

**Fix:** one sink derivation for all three log guards (the exception-text guard's: helper sinks,
aliases, partials, streams, pprint); treat `.dict()` / `.model_dump()` / `json.dumps` of a record as
the record; add person-name reads on a user record (`user_data["name"]`, `.name` on a
user/invitation row) to the vocabulary. Or — the type route — a `UserRecord` whose repr hides
`email`/`name`, as F1 did for the storage objects.

### P2-2 (sev 1): F2's "every statement that empties `tenants` is exactly `TenantService.delete_tenant`" is refuted by this repo's own SQL idiom

`tests/unit/db/test_tenant_service.py:1298` (`_TENANT_TEARDOWN_SQL`, anchored at the statement's
start), `:1238` (`gate_rebindings`), `:1330`.

- Plant `f2new`: a new helper `scripts/_tenant_purge.py` deleting children then `tenants` through
  `sql.SQL("DELETE FROM {} WHERE tenant_id = %s").format(sql.Identifier(table))` — the composition
  `scripts/run_db_lane.py:207,227` already uses. unit+api+authz **3393 passed**; db identical to
  baseline.
- Probe `f2_plants.py` over the pin's own functions: **missed** — multi-statement string
  (`"BEGIN; DELETE FROM tenants …"`), a leading `--` comment, `/* */` between DELETE and FROM, a
  table-loop f-string, `"DELETE FROM " + T`, a helper call; in `.sql`: a `DO $$ … $$` block, a
  function body, a `/* */` prefix. Rebinding: `ts.__dict__.update(require_the_cascade_…=…)`,
  `vars(ts).update(LOCK_TENANTS_FOR_TEARDOWN=…)`, a `"".join([...])` name, a dotted
  `mock.patch` target, and replacing `TenantService.delete_tenant` itself.
- r6's own m6 (setattr + lock overwrite + raw DELETE) is RED at HEAD (2 tests). The gate's
  behaviour INSIDE `delete_tenant` is solid: mutant `gate-swallow` (try/except around the gate
  call, `tenant_service.py:1042`) → 3 RED.

This is the second round in which the teardown lock is patched as a source-shape pin. Per the
plan's lesson ("a second P1 in the same mechanism stops the patching"), the complete answer is in
the database, not in a scan: the app roles hold no `DELETE` on `tenants`, and teardown runs through
one `SECURITY DEFINER` function (or a `BEFORE DELETE` trigger) that performs the cascade check. That
is a privilege/RLS decision → tier 2, owner.

### P2-3 (sev 1): F8's builder aliases follow `H = HTTPException` but not an IMPORT alias

`tests/api/tenancy/test_router_error_disclosure_sweep.py:1165` (`_builder_aliases`), `:1032`.

Mutant `f8`: `role_endpoints.py:8` `+ from fastapi import HTTPException as _Failed`; `:265-266` →
`except Exception as failure: raise _Failed(status_code=500, detail=f"Error creating role: {failure}")`.
`POST /roles` create is one of the branches the docstring calls undriveable, so only the structural
half can see it. unit+api+authz **3393 passed**; db identical to baseline. The exception-text log
guard deliberately leaves response bodies to this sweep, so nothing else sees it. Also missed by the
structural rule (probe `f8_plants.py`): Starlette's `HTTPException as StarletteHTTPException`, a
`yield` of exception text inside a generator handed to `StreamingResponse` (core streams PDFs), a
`Refusal`-only handler echoing `e.__cause__` (the whole handler is skipped), and
`functools.partial(HTTPException, 500)`.

**Fix:** resolve builder names through the module's imports (the span guard's
`_otel_import_aliases` already does this); add `StreamingResponse`/`HTMLResponse`/`ORJSONResponse` to
the builders and treat a generator's `yield` as a body; judge a Refusal handler's reads of
`__cause__`/`__context__`.

### P2-4 (sev 2): F1's pin passes a whole catalog record logged under an unlisted name

`core/resources/document_viewer/services/document_service.py:375-406` (`_row_to_item`),
`tests/unit/observability/test_storage_locations_stay_out_of_logs.py:59` (`STORAGE_NAMES`).

Mutant `f1new`: `logger.debug("Reassembled catalog item", item=item)` before `return item` — the
item carries `url` (bucket + the tenant's object key) and the whole `attributes` overflow.
unit+api+authz **3393 passed**; db identical to baseline. It is the declared class ("a location held
under a name outside the vocabulary"), but it is the most natural regression in the one module that
builds these records, and the TYPE fix covers `ResolvedObject`/`ChatArtifact` only. r6's own m1b is
RED at HEAD (static + behavioural); r6's 17 storage plants: 12 caught, 2 held by the new type
(`repr=False`), 3 declared.

**Fix:** a typed catalog item whose repr hides the pointer fields, or taint a name bound from a
call whose callee returns a dict carrying a storage key.

### P3-1: F10's stated limit is not the whole limit

`core/resources/document_viewer/document_endpoints.py:86,90,157`. `document_answer` (probe
`f10.py`) keeps: a bare object key (`"s3_key": "tenants/t-1/…pdf"`), a bucket/key split, an
`arn:aws:s3:::…`, `s3a://` in text (and inside a pointer field's text), a JSON-escaped
`https:\/\/…amazonaws.com\/…`, a percent-encoded URL. The docstring names only "an S3-compatible
host that is not the configured endpoint". No live row was shown to carry these (no DB access here),
so this is a coverage statement, not a leak.

### P3-2: `loc` still carries caller-chosen keys; one manual 422 echoes input

`core/resources/http_errors.py:58,88`. `POST /invitations/preview` with `{"token": "t.x", "<key>": true}`
answers `{"loc": ["body", "<key>"], "msg": "Extra inputs are not permitted", …}` (probe; the
caller's own input, not a credential value). Older than the range:
`core/resources/automations/automations_endpoints.py:219-226` raises a hand-built 422 whose `detail`
quotes the submitted `kind` (and `:218` logs it raw). Authenticated, own input.

### P3-3: signup oracle residuals

- A body whose `external_id` already has a row trips `users_pkey`, not the email index →
  `user_service.py:541` re-raises → **500** (probe `test_probe_pkey_collision…`), where every other
  refusal is 400 and a fresh body is 201. The sub is also what the anonymous
  `GET /users/email/{email}` returns (B13), so it adds little, but it is a distinguishable answer on
  the ruled door.
- `user_service.py:532-536` logs `user_id=user_id` for the refused attempt — that is the BODY's
  `external_id` (caller-chosen text), not the existing account's id, so "the log says it, by ids"
  names nobody an operator can find.
- By nature: 201 (and a pending row) for a fresh address, 400 otherwise; so an attacker with a
  control address still learns existence. Recorded in the g61 plan; restated for the packet.

### P3-4: G.117's guard counts imports that never run and misses two entrypoint spellings

`tests/unit/observability/test_entrypoints_import_utils_first.py:67,125`. Passes the guard (probe
`g117_plants.py`): `if TYPE_CHECKING: from utils.config import Settings`, `if False: import utils`,
`import utils` placed after `main()` inside the `__main__` block. Undetected entrypoints:
`if "__main__" == __name__:`, `if __name__ == "__main__" and …:`, `__name__ in ("__main__",)`.
Today: all 12 entrypoints reach utils through real module-level imports (chains printed and
checked); no `__main__.py`, no console scripts.

### P3-5: F9's census counts constructions it can name

Probe `f9.py`: uncounted — `cls = Refusal if x else ValueError; raise cls(m)`, a dict dispatch,
`type("Declined", (Refusal,), {})`, `getattr(ce, "Refusal")(m)`, `Refusal.__new__`. And by design a
text swap inside an existing site (`Refusal(f"taken by {row['owner_email']}")` for `Refusal("taken")`)
keeps the census equal. All contrived except the last, which is a text rule the census never claimed.

### P3-6: F3's freeze lives in the file it freezes

`tests/unit/observability/test_core_logs_carry_no_exception_text.py:1480`. r6's bless hunk (entry
+ twin + dated reason + `docs/plans/bless.md` over a real `cause=str(exc)` leak in
`_extract_contact_email`) is RED at HEAD (1 test: the freeze). The same hunk plus replacing the
three `== {}` asserts with `pass` → **147 passed**. That is the stated design ("re-opening one means
editing that assertion"); an in-tree lock cannot stop a same-diff edit. A merge-base ratchet (as
copilot-mro's `_register_ratchet.py`) or a CODEOWNERS rule is the stronger lock.

### P3-7: invite residuals

- `core/fastapi_app.py:327`: the standalone path (`start_api.sh`, "a debug run, an incident
  bypass") runs uvicorn with its default access log, and utils' intercept routes `uvicorn.access`
  into loguru (`intercept.py:26`) without query withholding, so the deprecated GET's `?token=`
  lands in that process's log. The gateway path is covered by api's log-config and flynapse-otel's
  `token` query rule.
- `tests/api/invitations/test_invitation_preview_by_body.py:94` pins parity for five cases; `accepted`
  and a server fault are not among them. Both hold (probes: identical 200 / identical fixed 500 with
  the token absent).

### P3-8: documentation

- M-PII-IDS says **eleven** sites (commit `4040a82`, the test docstring, the g61 plan, ledger); the
  commit's own enumeration is **15 log statements** (create_user 2, contact 1, registration mail 4,
  the two doors 5, dispatcher 1, mismatch refusals 2), and "five f-string lines" were four f-strings
  and one `email=` keyword. The g61 plan's own lesson (line 712, "Count from the tool, not from the
  brief. A commit message said 'eleven' because the review did; the sweep found nine") is the same
  slip, repeated with the same number; the §16 row (line 539) also omits the unverified-signup
  `user_email=` line from its list.
- `9188794`'s message and the `tenant_service.py:1010-1016` comment: "every statement that empties
  tenants" / the spellings pinned — see P2-2.
- `a58995a`'s "builder aliases" — assignment only (P2-3).
- g61 plan §M-INVITE-FRAGMENT "api half owed: … exempt only GET" is stale (api `8d7f587`).

### P3-9: the `_root.py` drift pin skips rather than fails, and reads api's live HEAD

`tests/unit/infra/test_cross_repo_reads_name_their_checkout.py:886-896`. Any exception from
`sibling_variant` → `skip`; so a workspace the resolver refuses reports a skip, not a drift. And
core's unit result now depends on api-obsm's HEAD at run time (today: api-obsm `2d3ba94`, md5
`3d192468` = core = utils = copilot-mro). By design; recorded so a red in core after an api commit
is read correctly.

### Observation, older than the range, outside M-PII-IDS's letter

`core/resources/logging/logging_endpoints.py:106` logs the public telemetry ingest's rate-limit key
at WARNING; for the anonymous door that key is `request.client.host` — a client IP address.

---

## What I tried to break and could not

- **PII on live paths.** A widened taint sweep (names, rows, profiles, payloads) over `core/`,
  `scripts/`, `setup/`: the only hits are tenant/company names, table names and the synthetic channel
  username. Every exception message that quotes an address (`free_email_domains.py:66`, the trusted
  `Refusal`s at `user_service.py:539,659`) is either converted `from None` or logged by
  `failure_fields` (type + frames). utils' SMTP service logs neither recipient nor message. No span
  in core carries a person.
- **The signup refusals.** flag-DOWN existing = flag-DOWN unresolved = flag-UP domain refusal =
  flag-UP existing (status, body, every header; probes + the committed pins). No Cognito call on the
  door; the only extra side effect on the existing path is the failed INSERT.
- **Invite.** POST/GET parity for `accepted` and for a 500; no token in any log line on either door,
  with the least happy path; the composer's percent-encoding is pinned (`a%2Bb%2Fc`); the token is
  emailed from one composer only and returned by no response model.
- **F1.** r6's m1b RED (2 tests); the resolver capture is behavioural.
- **F2 from the inside.** The gate call swallowed → 3 RED; m6 → 2 RED.
- **F3.** r6's bless hunk → RED.
- **F4.** r6's IDNA plant (value_error passed through) → 3 RED; the timezone Refusal re-quoting
  `{value!r}` → 5 RED; the discriminated union's `union_tag_invalid` always quotes the field name
  `type`, so the 4-char rule refuses it; `extra_forbidden`, NUL, wrong type, malformed JSON quote
  no value.
- **F7.** 16 new exception-text plants: every miss was a declared blind spot (named `patch`
  function, logger factory, runtime level, `sys.stderr.buffer`, ContextVar, response body). Span
  guard: 8 plants, one miss, declared (helper through a dict).
- **F11.** Declaring `traceparent` as `text NOT NULL DEFAULT ''` → RED in the unit lane
  (`test_the_traceparent_carrier_is_the_column_the_owner_ruled`); the db reds are the live gate.
- **G.117.** All 12 entrypoints reach `utils` through real module-level imports; utils `8572635`
  installs the safe sink in `utils/__init__.py:32-34`.
- **94e0502.** The two edited tests were strengthened, not relaxed.
- **Settling mutants run here, all RED:** `sig` (the domain branch's sentence reworded → the
  byte-identity case), `link` (`#` → `?` → 2), `par` (POST previews a different token → 4),
  `gettok` (the deprecated GET logs `token=` → 2), `g117` (drop one script's `import utils` → 1),
  `f7` (botocore's `Error.Message` logged in `tenant_claim_writer` → 1), `pii0` (→ 1).

## What I did not test

- Timing between the refusals against a real database (DB ban); reasoned only.
- Whether any live catalog row carries a bare object key / ARN / escaped URL (P3-1) — needs a read
  of the catalog.
- The api gateway's handling of the POST preview (skip list, rate limiter): api's range.
- The shared flynapse-otel detector (excluded by the brief).
- The dashboard half of M-INVITE-FRAGMENT.

## Claims table

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r7-01 | core | `user_service.py:141,156,225,262,269,498,580`; `user_endpoints.py:953,1732,1733,1737,1742`; `invitation_dispatcher.py:113`; `invitation_service.py:409,616` | 15 log statements name people by `user_id`/`tenant_id`/`invitation_id` | M-PII-IDS | widened sweep: no live hit; behavioural captures of contact, registration mail, unsent invite, mismatch refusal (db) | `test_core_logs_name_people_by_id.py` | yes: `pii0` RED | — | 0 | F1 | SETTLED |
| r7-02 | core | `test_core_logs_name_people_by_id.py:95,62,145` | sweep sinks = level methods, bind/opt/patch, print, warn | — | `pii1` (PUT /users `changes=update_data`) and `pii2` (`internal_error(f"…{email}")` on the anonymous door) pass all 4 lanes; 22/33 plants missed (18 undeclared) | same | yes: survivors shown | 1 | 1 | F1 | OPEN, P2-1 |
| r7-03 | core | `user_service.py:527-536`; `user_endpoints.py:158,944-951` | one constant `SIGNUP_NOT_COMPLETED` for exists / domain refusal / unresolved | M-SIGNUP-ORACLE + extension | byte-identical status/body/headers, 4 combinations incl. flag-UP existing (probe) | `test_signup_answers_no_account_existence.py` | yes: `sig` (domain sentence reworded) RED | — | 2 | F1 | SETTLED |
| r7-04 | core | `user_service.py:541` | a `users_pkey` collision re-raises → 500 | not in the ruling's scope | probe: known `external_id` → 500 | none | n/a | 2 | 1 | F1 | OPEN, P3-3 |
| r7-05 | core | `invitation_email_composer.py:38` | link `/invite#token=<quote(token, safe='')>` | M-INVITE-FRAGMENT | html + text parts carry `#token=`, no `?token=`; `a%2Bb%2Fc` pinned | `test_invitation_email.py:111`, `test_invitation_preview_by_body.py` | yes: `link` (`?token=`) RED ×2 | — | 0 | F1 | SETTLED |
| r7-06 | core | `invitation_endpoints.py:160-197`; `models.py:56-64` | POST preview = GET via one `_preview`; GET deprecated, token-free usage log | M-INVITE-FRAGMENT | parity incl. `accepted` + 500 (probes); no token in logs | `test_invitation_preview_by_body.py` | yes: `par` (POST looks up another token) RED ×4; `gettok` (GET logs `token=`) RED ×2 | — | 0 | F1 | SETTLED (2 cases unpinned, P3-7) |
| r7-07 | core | `fastapi_app.py:327` | standalone uvicorn keeps its default access log | debug/bypass path | utils intercept routes `uvicorn.access` unredacted | none | n/a | 2 | 1 | F1 | OPEN, P3-7 |
| r7-08 | core | `pdf_object_resolver.py:86,96` | `field(repr=False)` on `s3_key` / `url` | r6-F1: a type | repr/str pinned | `test_storage_locations_stay_out_of_logs.py` | yes: r6 m1b RED ×2 | — | 0 | F1 | SETTLED |
| r7-09 | core | `document_service.py:375-406`; storage pin `:59` | pin keyed on a name vocabulary | r6-F1 | `f1new` (`item=item`) passes 4 lanes | same | yes: survivor | 2 | 1 | F1 | OPEN, P2-4 |
| r7-10 | core | `test_tenant_service.py:1238-1360` | static pins: no gate/lock rebinding; one `DELETE FROM tenants` site | r6-F2 | `f2new` (psycopg2.sql helper) passes 4 lanes; 15 of 19 shapes missed | same | yes: m6 RED; `f2new` survives | 1 | 2 | F2 | REFUTED as stated ("every statement"), P2-2 |
| r7-11 | core | `tenant_service.py:1040-1042` | lock + gate before the DELETE inside `delete_tenant` | M-CASCADE | swallowing the gate → 3 RED | `test_a_delete_is_refused_under_the_lock_before_any_row_is_touched` | yes | — | 0 | F2 | SETTLED |
| r7-12 | core | `http_errors.py:58-110,165-189` | 422 = loc/msg/type; msg only for a core Refusal, else fixed; 4-char echo rule | r6-F4 | r6 IDNA + timezone plants RED; union tag, NUL, extra, JSON quote no value | `test_validation_answers_quote_no_values.py`, `test_automation_schemas.py` | yes: 3 + 5 RED | — | 0 | F1 | SETTLED |
| r7-13 | core | `http_errors.py:58` (`loc`); `automations_endpoints.py:219-226` | `loc` passes through; hand-built 422 quotes `kind` | loc is a location | probe: extra key echoed in `loc` | none | n/a | 3 | 1 | F1 | OPEN, P3-2 |
| r7-14 | core | `table_definitions.py:1319`; `test_automation_tables.py` EXPECTED_COLUMNS | `traceparent text`, nullable, no default; expectation includes it | r6-F11 / M-JOB-TRACEPARENT | db: 20 migration-gated reds, all the missing column | `test_the_traceparent_carrier_is_the_column_the_owner_ruled` (unit) + db shape test | yes: NOT NULL DEFAULT mutant RED (unit) | — | 2 | F2 | SETTLED (live half waits for C9) |
| r7-15 | core | `test_core_logs_carry_no_exception_text.py:1480`; `test_core_log_messages_are_not_format_strings.py:206` | both registers frozen `== {}` | r6-F3 | bless hunk RED; + 3-line unfreeze → 147 passed | same | yes both ways | 3 | 1 | F3 | PARTIAL, P3-6 |
| r7-16 | core | `test_cross_repo_reads_name_their_checkout.py:886-930` | `_root.py` byte-equal to api's committed copy; empty `utils-notes` no checkout | r6-F5 | md5 3d192468 in core/api/utils/copilot-mro | same | impl | 3 | 1 | F3 | SETTLED (skip-on-error, P3-9) |
| r7-17 | core | `test_core_logs_carry_no_exception_text.py`; `test_core_spans_withhold_exception_text.py` | F7 shapes followed; rest declared | r6-F7 | 16 log + 8 span plants: misses all declared | same | yes: `f7` (`exc.response["Error"]["Message"]` in `tenant_claim_writer`) RED | — | 0 | F1 | SETTLED (declared limits stand) |
| r7-18 | core | `test_router_error_disclosure_sweep.py:1165,1032` | builder aliases = assignment aliases | r6-F8 | `f8` (import-aliased HTTPException on POST /roles) passes 4 lanes | same | yes: survivor | 1 | 1 | F1 | OPEN, P2-3 |
| r7-19 | core | `test_refusal_is_the_only_echoed_value_error.py:225,363` | census per construction, module/class/lambda/partial | r6-F9 | 5 dynamic shapes uncounted; text swap equal | same | impl | 3 | 1 | F1 | PARTIAL, P3-5 |
| r7-20 | core | `document_endpoints.py:78-183` | pointer fields dropped at depth; storage hosts incl. `.com.cn` + configured endpoint; in-text redaction | r6-F10 | 7 shapes kept (bare key, ARN, s3a, escaped, encoded) | `test_document_answer_names_no_storage_location.py` | impl 5 | 2 | 1 | F1 | PARTIAL, P3-1 |
| r7-21 | core | `scripts/{backfill_chat_turn_facts,purge_product_events,review_improvement_findings,set_tenant_content_capture}.py` | module-level `import utils` after path setup | M-G117-DEFAULT | 12 chains printed; utils installs the safe sink at import | `test_entrypoints_import_utils_first.py` | yes: `g117` (drop `import utils` from `purge_product_events`) RED | — | 0 | F1 | SETTLED |
| r7-22 | core | `test_entrypoints_import_utils_first.py:67,125` | entrypoint = `if __name__ == "__main__"`; any module-level import counts | — | TYPE_CHECKING / `if False` imports pass; 3 spellings undetected | same | n/a | 3 | 1 | F1 | OPEN, P3-4 |
| r7-23 | core | `tests/authz/roles/test_bootstrap_seeds.py:743-749` | closed-door pin matches the frame by line number | utils M-STACK-HEADERS | authz 285 from `b31bd00`; red before only under the new utils | same | impl 1 (measured, not re-mutated) | — | 1 | F2 | SETTLED |
| r7-24 | core | range | every commit at its own HEAD | plan §2.4 | table above | the lanes | n/a | — | 1 | F2 | SETTLED (all reds accounted) |
| r7-25 | core | g61 plan §16 line 539, `4040a82` msg, `test_core_logs_name_people_by_id.py:4` | "eleven sites"; "every statement"; "builder aliases"; "api half owed" | — | 15 statements; P2-2; P2-3; api `8d7f587` | none | n/a | 3 | 1 | F3 | OPEN, P3-8 |
| r7-26 | core | `logging_endpoints.py:106` | public ingest rate-limit key (client IP) logged at WARNING | cost bound | read | none | n/a | 3 | 1 | F3 | OPEN (observation, older) |

## Open claims, tier 2 first

**Tier 2:**

1. **r7-10 (P2-2).** The tenant-teardown lock is the second round of a source-shape pin on the same
   mechanism. Owner decision: move the guarantee into Postgres — revoke `DELETE` on `tenants` from
   the app roles and route teardown through one `SECURITY DEFINER` function (or a `BEFORE DELETE`
   trigger) that runs the cascade check — or accept the scan and restate the claim as "the spellings
   below".

**Tier 1, in the order to fix:**

1. **r7-02 (P2-1).** One sink derivation for the three log guards; `.dict()`/`model_dump()`/`json.dumps`
   of a record is the record; person names on user/invitation records; derived helper sinks
   (`internal_error`).
2. **r7-18 (P2-3).** Import-alias resolution for response builders; streaming bodies; Refusal
   handlers reading `__cause__`.
3. **r7-09 (P2-4).** A typed catalog item or call-result taint in `document_service`.
4. **r7-20, r7-13, r7-04, r7-07.** State (or close) the F10 limit; decide whether `loc` keys are
   acceptable; a `users_pkey` collision on the signup door → the fixed refusal; the standalone
   uvicorn launch passes utils' log config or `access_log=False`.
5. **r7-22, r7-19, r7-15.** Guard hardening (G.117 dead imports, census dynamic shapes, merge-base
   ratchet for the frozen registers).
6. **r7-25, r7-26.** Documentation; the IP observation to the owner with M-PII-IDS's scope.

**Tier 0 settled in this range:** r7-01, r7-05, r7-06, r7-08, r7-11, r7-12, r7-17, r7-21 — each
seen RED here when its property was removed. r7-03 and r7-14 are SETTLED too but tier 2 (signal
contract / schema); r7-23 and r7-24 are measured, tier 1.
