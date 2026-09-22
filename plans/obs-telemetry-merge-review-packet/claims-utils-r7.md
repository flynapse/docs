# Claims packet — utils review round 7 (`594327e..4d86ae9`)

Independent adversarial review (Opus), 2026-09-21. It answers the implementer's response to review r6
(`claims-utils-r6.md`). Read-only against every real tree:

- each of the 14 commits (the base and the 13 in range) was `git archive`d into the private scratch `scratchpad/utils-review-r7/trees/`, with flynapse-otel as an archive of `927a729`;
- every mutation ran against a scratch copy (`mut/`, `mut2/`, `mut3/`), was grep-confirmed, run, reversed, and md5-checked against the `4d86ae9` blob;
- at the end, `diff -r` showed every copy (`mut/`, `mut2/`, `mut3/`, the posed `ws/utils-obsm`) byte-identical to the `4d86ae9` archive, and all 61 restores printed `RESTORED` with 0 `DIFFERS`.

`utils-obsm` itself moved during the review, to `8552ef2` plus 2 dirty files: the implementer's new G10R/R2 work on top of the range. `4d86ae9` is an ancestor of it. That work is **out of range and was not read**; every result below comes from the archives.

| repo | worktree | branch | range | commits | flynapse-otel under test |
|---|---|---|---|---|---|
| utils | `/home/aditya/Code/utils-obsm` | `obs-merge` | `594327e..4d86ae9` | d50635e, 642e7a3, 299115b, 7c21b64, 791df20, 7b27e06, ddb8e8d, 849ca21, 2df9dcb, b24a023, b87018e, f36857f, 4d86ae9 | archive of `927a729` |

**How it was run.**

- **Lane:** `/home/aditya/Code/api/.venv/bin/python -m pytest -o addopts="-ra --strict-markers" -p no:cacheprovider`, run from the archive root. `LOGURU_DIAGNOSE` and `LOGURU_BACKTRACE` were unset.
- **Environment:** `ENV_FILE=/home/aditya/Code/api/.env DEBUG=false POSTGRES_DB=copilot_mro_test`.
- **Paths:** `PYTHONPATH=<guard>:<archive>:<fo-927a729 archive>`, with a fresh `PYTHONPYCACHEPREFIX` for every run and every probe.
- **Network guard:** a `sitecustomize` refused every non-loopback connect and name lookup and the loopback service ports, and logged every attempt. Across all 14 sweeps, every mutant run and every probe it logged **0 refusals**; the only connects were the tests' and probes' own ephemeral loopback servers (7 per sweep up to 791df20, 11 from 7b27e06 on — the new real-urllib3 test).
- **Reporting:** a plugin printed `rootdir`, `utils.__file__`, `flynapse_otel.__file__` and `sitecustomize.__file__` for every run. Every exit status below is pytest's or ruff's own.
- **Deselected in the archive sweep:** `test_cross_repo_reads_name_their_checkout.py` and one `test_root_anchoring` case, as in r5 and r6 (they need the real workspace).

**Every commit is green at its own HEAD.** Each full suite exited 0, with `utils.__file__` pointing at that commit's archive (rootdir the same archive).

| commit | passed | skipped | commit | passed | skipped |
|---|---|---|---|---|---|
| 594327e (base) | 1792 | 11 | ddb8e8d | 1801 | 11 |
| d50635e | 1793 | 11 | 849ca21 | 1806 | 11 |
| 642e7a3 | 1795 | 11 | 2df9dcb | 1809 | 11 |
| 299115b | 1796 | 11 | b24a023 | 1810 | 11 |
| 7c21b64 | 1797 | 11 | b87018e | 1811 | 11 |
| 791df20 | 1798 | 11 | f36857f | 1823 | 11 |
| 7b27e06 | 1800 | 11 | 4d86ae9 | 1823 | 11 |

Each run also deselected 24 tests. The 11 skips at HEAD are the inventory's 8 `[copilot-mro]` cases and 3 `test_root_anchoring` cases. **With the sibling posed** (a scratch workspace holding the `4d86ae9` archive beside a `git archive` of copilot-mro-obsm `62c7413d`'s `copilot_mro/`), the inventory and bounding files ran **45 passed, 0 skipped**, `rootdir` and `utils.__file__` in the posed tree.

**Ruff at each HEAD** (ruff 0.14.0, `ruff check . --no-cache`): every HEAD, the base included, carries the same 1144 pre-existing diagnostics and `ruff check` exits 1. The per-commit delta by (file, code) is **zero at all 13 commits**; the two new modules (`_library_lines.py`, `_refusals.py`) carry none.

---

## Findings, ranked

**No P0.** Every r6 finding the range answers is closed at its named seat, and every r6 surviving mutant is now red (MR3, MR5, M23f, MG2, MI1, MI2, MI4, MI5). **But the range introduces a P1 into the privacy layer (P1-1) and a privacy regression (P2-1).** It also leaves r6's P1-1 class open in two shapes (P2-2, P2-3), and four withholding lines it added have no test that fails without them (P2-7). Verdict: **FIX-FIRST**.

Mutation totals: **61 distinct mutants and decoys**, each grep-confirmed, run, restored and md5-checked.

- **43 went red.**
- **18 survived:**
  - 7 are behaviour-proven real gaps: MD3, ME2, ME3, MS3, ML2, MV2 and MC2;
  - 4 are decoys planted to prove a hole: MI6, MI7, MI8 and MI10;
  - 4 change behaviour by reading: ME7, MU2c, MRe and MRf;
  - 3 are equivalent or unreachable: MP3 (the kwargs dict is always fresh), MU2 (`user_id` is forbidden upstream), and ME8.

### P1-1 — A spent `ExtraBudget` fails OPEN: every exception after it is never searched, and the message's quotes of it ship on every sink (new in b24a023; the guard pins only the extras)

`ExtraBudget` (`utils/_exception_text.py:340-352`) raises `_BudgetSpent` through `_guarded` (`:355-363`) to `withheld_extra`'s outer `except` (`:394-397`), which returns the extra's type name. From then on, every later value spends past zero before `_withheld_value` (`:405`) reaches `found.append(value)` (`:407`). So an exception in a later extra — or a later stdlib `%s` argument, or a later `extra={...}` key — is **never appended to `found`**, and `withheld_quotes` (`:498-515`) is handed a list without it. Nothing records that the budget was spent: `_withhold_record` (`log_bridge.py:194-202`), the safe sink (`_loguru_default.py:95-99`) and `withheld_stdlib_message` (`_exception_text.py:533-542`) all go on to write the message.

| probe (sentinel `SEC_…`) | 2df9dcb (before the budget) | b24a023 and 4d86ae9 |
|---|---|---|
| `logger.error("failed: {err}", rows=list(range(20_000)), err=exc)` | `failed: ValueError` | **`failed: SEC_B1 after-big-list`**, `rows: "list"` |
| `logger.bind(ids=big).error("failed: {err}", err=exc)` | withheld | **leaks** |
| `logger.error("failed: {err}", meta={6000 keys}, err=exc)` | withheld | **leaks** |
| `logger.error("failed: {e}", w={400 × 50 nested dict}, e=exc)` | withheld | **leaks** (80 ms) |
| stdlib `std.error("rows %s failed: %s", big_list, exc)` | withheld | **leaks** |
| stdlib `std.error("failed: " + str(e), extra={"rows": big, "err": e})` | withheld | **leaks** |
| the same two calls on the **safe default** (no `setup_logging`) | withheld | **leak** on stderr |
| the first call on the **OTLP body** and the **human** line | — | **leak** on both |
| control: `err=` before the big extra | withheld | withheld |

The budget is reached by ordinary data, not only by attacks: a list of 10,000 ids, a dict of 5,000 entries, or about 2,000 five-column rows at depth 3. The test (`test_stdout_sinks_withhold_exception_text.py:539-572`) asserts `record["extra"] == {"big": "list", "after": "list"}` with a message of `"m"`, so a message that quotes the later exception is never checked. No estate call site was found by pattern search, so it is latent today — but it defeats the fail-closed contract the commit states ("past either, it fails closed"), and it was introduced by this range.

**Fix.** Make the spent state visible: `ExtraBudget` records `spent`, and every caller (the patcher, the safe sink, `withheld_stdlib_message`) writes `WITHHELD_MESSAGE` when it is set. Pin it with a record whose message quotes an exception placed after a budget-spending extra, on the loguru path, the stdlib `%s` path and the safe default.

### P2-1 — `LibraryLineFilter` flattens `record.args` before the stdlib twin runs, so exception text among a library record's arguments ships again (new in 7b27e06; r6 saw this shape withheld)

When a record from urllib3, botocore, boto3 or s3transfer holds a URL or path, the filter rewrites `record.msg, record.args = reduced, ()` (`utils/_library_lines.py:79`). It runs as a handler filter, **before** `InterceptHandler.emit` calls `withheld_stdlib_message(record.getMessage(), record)` (`intercept.py:68`). With `args` gone, the twin finds no exception, and the exception's `repr` — already formatted into the reduced `msg` — ships.

| probe | 791df20 | 7b27e06 and 4d86ae9 |
|---|---|---|
| **real urllib3** retry WARNING against a local dropping server | `… broken by 'RemoteDisconnected': /ap-south-1_SECPOOL/jwks.json` | `… broken by 'RemoteDisconnected('Remote end closed connection without response')': [path withheld]` |
| `urllib3.connectionpool` WARNING, `%r` of an exception carrying a username, plus a path | `'Weird'` | **`'Weird('SEC_F1 user=alice@example.com')'`** |
| `botocore.retryhandler` ERROR, `%s` of an exception plus a URL | `after Weird` | **`after SEC_F3 Username=bob@example.com`** |
| control: exception argument, no path (so no rewrite) | withheld | withheld |
| control: `exc_info` plus a path | withheld | withheld |

r6's "What I tried to break" row for 1290f27 recorded exactly the first shape as withheld (`RemoteDisconnected('Remote end closed…')` reduced to its type). The new test (`test_the_client_libraries_lines_carry_no_path_body_or_username`, `:823`) checks only that the retry line ends `": [path withheld]"` and that the path sentinel is absent. The estate's realistic content here is library-authored (hosts, errno text), so this is a regression of G.115's contract rather than a known personal-data leak.

**Fix.** Reduce after withholding, not instead of it: either have the filter call `withheld_stdlib_message` before it flattens, or move the reduction into `InterceptHandler.emit` after the twin, as `_LastResort` already does (`_loguru_default.py:145-149`). Pin the real urllib3 retry line for the exception's text as well as its path.

### P2-2 — The P1-1 fix honours the repr contract, but the production sinks render `str()`: a dataclass whose `__str__` hides a field still ships it (residual of r6 P1-1; clean at 8572635)

`_withheld_dataclass` (`_exception_text.py:442-465`) rebuilds a dataclass holding an exception whenever its `repr` is the generated one. The JSON and OTLP sinks do not render the extra's `repr`: `flatten` (`log_bridge.py:141-161`) writes `str(value)`. So a class that keeps a field out of logs by overriding `__str__` alone (default `repr`) is still expanded into the dict of its shown fields.

| plant | 8572635 | 594327e | 4d86ae9 |
|---|---|---|---|
| `@dataclass CustomStr(token, err)` with `__str__` → `CustomStr(err=ValueError)` | `CustomStr(err=ValueError)` | `{'token': 'SEC_D3 token', 'err': 'ValueError'}` | **`{'token': 'SEC_D3 token', 'err': 'ValueError'}`** |
| the same, `err=None` (control) | hidden | hidden | hidden |

Everything r6 named is fixed: `field(repr=False)` (slots, frozen, `eq=False`, on a parent class), a subclass overriding `__repr__`, `@dataclass(repr=False)`, and a nested hidden field; MD1 and MD2 are red. No estate dataclass overrides `__str__` (searched), so it is latent. The same function's "a hidden field is still searched" is unpinned (MD3, P2-7).

**Fix.** Rebuild only when neither `__repr__` nor `__str__` is overridden (`type(value).__str__ is object.__str__` besides the repr check); otherwise write the type name. Pin the `__str__` shape.

### P2-3 — The same rebuild goes around the repr of a built-in container SUBCLASS: a NamedTuple, dict or list subclass whose repr masks a value exposes it (pre-existing since 1ca0268/8a55ca1; one live estate type)

`_withheld_value` (`_exception_text.py:418-436`) rebuilds any `dict` instance as a plain dict and any `list`/`tuple`/`set` instance as its base kind. A subclass that overrides `__repr__`/`__str__` to keep values out of logs loses that the moment it holds an exception:

| plant | 8572635, 594327e and 4d86ae9 | control, no exception |
|---|---|---|
| `NamedTuple(user, password, err)` with a masking `__repr__` | **`['u', 'SEC_N1 pw', 'ValueError']`** | `NT(user='u', password=***, err=None)` |
| `dict` subclass with a masking `__repr__`/`__str__` | **`{'user': 'u', 'password': 'SEC_N2 pw', 'err': 'ValueError'}`** | `MaskedDict(user='u', password=***)` |
| `list` subclass with a masking `__repr__` | **`['SEC_N3 item', 'ValueError']`** | `MaskedList(len=2)` |

**A live estate instance:** core-obsm `core/resources/document_viewer/services/storage_locations.py:180`, `class CatalogItem(dict)`, whose `repr`/`str` are a type-level log guard: "logging the item WHOLE names no location". A `CatalogItem` that holds an exception at depth ≤ 3 — or, since 642e7a3, any nested value that fails to walk (`_guarded` returns its type name, which marks the container changed) — is written as a plain dict with every storage location. No such content path was found today, so it is latent; it is the r6 P1-1 class, which d50635e fixed for dataclasses only.

**Fix.** Rebuild only exact built-in types (`type(value) in (dict, list, tuple, set, frozenset, deque)`); a subclass holding an exception becomes its type name. Pin the NamedTuple and dict-subclass shapes.

### P2-4 — A spent budget also rewrites every later PRIMITIVE extra: `tenant.id` becomes the string `"str"` (new in b24a023)

Once the budget is spent, every later extra becomes its type name, including strings and numbers, which cannot hold an exception:

```
with logger.contextualize(request_id="req-ctx-1"):
    logger.bind(ids=list(range(20_000))).info("bulk done", tenant_id="t-acme", user_id="u-42", count=20_000)
→ {"request.id": "req-ctx-1", "ids": "list", "tenant.id": "str", "enduser.id": "str", "count": "int"}
```

The JSON line and the OTLP attributes then carry a bogus tenant `"str"` and user `"str"`. A Logs Insights or LogQL query by tenant loses the record, and a per-tenant panel gains a tenant called `str`. The commit declares that the big extra itself becomes `"list"`; it does not mention the identities after it.

**Fix.** Let `str`, `int`, `float`, `bool` and `None` pass through without spending or being replaced (they cannot hold an exception), and keep the fail-closed decision for the message (P1-1).

### P2-5 — The library floor's own rationale ("their lines carry request paths, bodies and usernames") covers families it does not list: httpx at INFO, openai and anthropic at DEBUG (pre-existing; the claim is broader than the list)

`LIBRARY_FAMILIES` (`_library_lines.py:30`) is urllib3, botocore, boto3 and s3transfer. `httpx` is intercepted (`intercept.py:30`) but is not a family, so its lines pass the filter whole. Probed at the deployed level (`LOG_LEVEL=INFO`) against a local server:

- `INFO httpx: HTTP Request: DELETE http://…/v1/objects/SEC_Collection/0001?tenant=SEC_tenantkey "HTTP/1.0 200 OK"` — the weaviate client's REST shape. utils itself calls `data.delete_by_id` and `data.update` on tenant-scoped handles (`weaviate_service.py:633`, `:966`, `:1023`, `:1140`, `:1221`, `:2342`), and weaviate 4.17 puts the tenant key in the query (`collections/data/executor.py:641`). G24-01 calls a tenant key and a collection name "a tenant's identity", which is why this range took them out of refusal messages.
- `INFO httpx: HTTP Request: GET http://…/bucket/tenants/SEC_t1/SEC_user@example.com/report.pdf?:redacted …` — a presigned-S3 shape. `withhold_url_secrets` strips the signature; the key path, email included, stays (M-PII-IDS: "never emails").
- At `LOG_LEVEL=DEBUG`: `DEBUG openai._base_client: Request options: {… 'json_data': {'messages': [… 'SEC_prompt my passport number is 123' …]}}`, and the same from `anthropic._base_client` — whole prompt bodies, the "bodies" rationale exactly.

Also noted: `reduced_library_text` keeps `scheme://host`, and a virtual-host S3 URL's host is the bucket, which f36857f treats as an identity (`s3_service.py:1129`, `:1140`).

**Fix.** Either add `httpx` (reduce at INFO), `httpcore`, `openai` and `anthropic` (floor at INFO) to the families, or narrow the docstring and `setup_logging`'s text to the four families, and record httpx and the SDK bodies as owed.

### P2-6 — The inventory's "no fourth outcome" still has holes: five call shapes pass silently, four key shapes are misread, a constant collision misattributes a family, and the fixpoint is unpinned (residual of r6 P2-6)

r6's four mutants (MI1, MI2, MI4, MI5) are red, and so are MV1 (keyword `name=` never read) and MV3 (an unresolved name skipped silently). Probed against the inventory's own `_emissions()` (`test_legacy_family_inventory.py:378-416`):

| shape | outcome |
|---|---|
| a bound-method alias: `emit = svc.increment_counter; emit("llm_probe_leak_total", email=e)` | **silent** — not an emission, not unresolved |
| `getattr(svc, "increment_counter")(…)` | **silent** |
| `functools.partial(svc.increment_counter, "…")(…)` | **silent** |
| the Document Hub wrapper through a module attribute: `operations.record_document_hub_metric("undeclared…", email=e)` (`:331` requires an `ast.Name`) | **silent** |
| a bare-name call `increment_counter("…", email=e)` (`:327` requires an attribute) | **silent** |
| `labels = {"tenant_id": t}; labels["email"] = e; …(**labels)` | resolves with `{tenant_id}` only — the `email` key is never checked |
| the same through `labels.update(email=e)` | same |
| `**{**extra, "tenant_id": t}` | the `**extra` keys are dropped without a report |
| two functions that each bind `labels = {...}` | the later literal wins for both (`_dict_literals`, `:143-164`) |
| two scanned modules binding the same constant name to different families | the emitter resolves to the OTHER module's family (`shared_constants.update`, `:407`): a probe emitting `llm_probe_leak_total` resolved as the declared `llm_requests_total` |
| a lambda forwarder, a class-level constant, a `*args` forwarder | reported (red) |

The four decoys planted in `utils/llm.py` confirm the holes in the real suite: MI6 (a bound-method alias), MI7 (the wrapper through a module attribute), MI8 (a label added after the literal) and MI10 (`getattr`) each leave the inventory and bounding files green, 37 passed.

**MV2 survives** (the forwarder fixpoint loop runs once): the suite stays green, 37 passed, because the "forwarder of a forwarder" plant defines the inner forwarder first, so one pass suffices. Behaviour-proven: with MV2 and the OUTER forwarder defined first, the emission disappears (`found=[]`, `unresolved=[]`); at HEAD it resolves to `('llm_request_duration', 'histogram', ['email'])`.

The runtime backstop (ddb8e8d: an undeclared family keeps only `tenant_id`; a declared one drops undeclared keys) limits what these shapes can export, so this is guard integrity, not a leak. But the file's docstring (`:21-27`, `:282-286`) still promises that every call "either resolves … or lands" in `unresolved`.

**Fix.** Report any `ast.Call` whose callee resolves to a metric method by other means (a `Name` bound to an attribute of a metric method, `getattr`, `partial`), accept the wrapper through an attribute, report `**` splats of names that are mutated after their literal, key the constants by module, and add an outer-first plant for the fixpoint.

### P2-7 — Four withholding lines the range added have no test: each mutant survives the full observability suite and ships text (behaviour-proven)

| mutant | line | suite | behaviour at HEAD → with the mutant |
|---|---|---|---|
| **ML2**: `_URL` reduction removed, bare paths still withheld | `_library_lines.py:52-54` (7b27e06) | 677 passed | `Retrying after timeout: https://cognito-idp.ap-south-1.amazonaws.com` → **`…amazonaws.com/ap-south-1_SECPOOL/.well-known/jwks.json`**; `Sending to https://<bucket>.s3…amazonaws.com` → **`…/tenants/SEC_t1/doc.pdf`**. The test's only INFO+ library line has a bare path, so the reduction that answers r6 P2-5's pool-id case in a full URL is unpinned. |
| **MD3**: a `repr=False` field no longer searched | `_exception_text.py:456-458` (d50635e) | 677 passed | `logger.error(f"job failed: {exc}", outcome=Outcome("failed", exc))` with `err` hidden: `job failed: ValueError` → **`job failed: SEC_MD3 hidden-field exception`**. The test's `Hidden` case asserts only the extra's rendering. |
| **MS3**: stdlib extras walked at `EXTRA_DEPTH`, not `+ 1` | `_exception_text.py:541` (7c21b64) | 677 passed | On the safe default and the OTel stderr handler, `extra={"d": {"a": {"b": {"c": exc}}}}` beside `"failed: " + str(exc)`: `failed: ValueError` → **`failed: SEC_MS3 …`**. Under `setup_logging` the patcher's second walk masks it, which is why the suite cannot see it. |
| **ME3**: `withheld_quotes`' net returns the message | `_exception_text.py:514-515` (642e7a3) | 677 passed | An exception whose `__cause__` property raises: `[message withheld: withholding it failed]` → **`failed: SEC_ME3 quoted`**. Only a contrived exception reaches this net, but it is the one line that decides fail-closed. |

MRe (`filename2` dropped) and MRf (a string argument's `repr` dropped: an escaped `{e.args[1]!r}` would ship) also survive; both are named in b87018e's docstring.

**Fix.** One test per line, each asserting the message, not only the extra: a full URL in a family WARNING; an exception only in a hidden field and quoted in the message; a 3-level stdlib `extra=` on the safe default; an exception whose chain cannot be read; an `OSError` with `filename2`; and an escaped argument's `repr`.

### P3 findings

- **P3-1 — G24-01 residuals (severity 3).**
  - `utils/migrate_weaviate_collection.py:228-229` quotes a collection name (a CLI script);
  - `utils/document_catalogs.py:101`, `:108` quote the per-airline catalog name from the environment (config time).
  - Since f36857f a non-`str` offending value rides raw on `error.<name>` and `error.ids`. When it is unpicklable (a lock passed as `tenant_id`, as `operator_ids` or as a cache-key family), the refusal can no longer be pickled or deep-copied — the r6 P2-2 property, lost again for that narrow shape. It was picklable at 594327e, when only the value's repr was in the message. Carrying `value_type` alone for non-`str` values would close it.
- **P3-2 — "It never raises" overclaims (severity 3).** `log_bridge.py:191` and `_exception_text.py:389` say it never raises. A getter raising `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` or a custom `BaseException` subclass propagates into the loguru and the stdlib log call. That is the right behaviour — none of them is an error to swallow — but it should be declared. loguru's own wrong-argument-count `IndexError` raises before the patcher (loguru's semantics, not in scope). A stdlib `%`-format that fails writes `WITHHOLDING_FAILED` and loses the constant template, which is what an operator needs to find the call; the level, logger, function and line survive.
- **P3-3 — An undeclared COUNTER keeps `tenant_id` (severity 3).** M-CARDINALITY says tenant identity goes "on a short NAMED list of instruments only"; an undeclared counter is on no list, yet `_UNDECLARED_ALLOWED` (`metrics.py:106`) keeps it. It costs one series per tenant per family, so it is cheap. This was the controller's call; flag it for the owner to confirm. An undeclared histogram drops the tenant (`:242`).
- **P3-4 — The cap is exact; one cosmetic seam (severity 3).** When a run's "`[Previous line repeated N more times]`" line lands at the edge of the kept tail and its three header lines fall in the omitted middle, it reads as repeating a line that is not shown. `sys.tracebacklimit` is ignored (declared).
- **P3-5 — Ruff is not clean at any HEAD (severity 3).** There are 1144 pre-existing diagnostics; the range adds none.
- **P3-6 — Operator-facing lines the range added are unpinned (severity 2).**
  - **MC2** (N counts lines, not frames) survives 31 passed. On an outer-30 + recursion-200 + inner-30 stack it prints `[15 frames omitted]` against the true 212, because the tests' stacks never put a "repeated" line in the omitted middle.
  - **ME2** (a failed nested value blanks its whole extra) survives. `box={"row": <raising>, "n": 7}` becomes `'dict'` instead of `{'row': 'Row', 'n': 7}` — fail-safe, but the per-value scope the docstring states is untested.
  - **ME7** (`_LastResort`'s inner net removed) survives. The outer net still catches, so the safe default writes `utils safe logging fallback failed: TypeError` instead of a `WITHHOLDING_FAILED` record with its level and location.
  - **MU2c** (the undeclared allowlist widened to `department`) survives: the test proves `email` and `route` are dropped, not that the allowlist IS `{tenant_id}`. `assert _UNDECLARED_ALLOWED == {"tenant_id"}`, or a key sweep, would pin it.

---

## What I tried to break and could not

- **r6's survivors are dead.** MR3 (2 failed), MR5 (1), M23f (1: `test_a_finished_futures_exception_is_withheld_from_the_message_that_quotes_it`), MG2 (1: `test_a_refusal_crosses_a_process_boundary_and_its_ids_stay_read_only`), MI1, MI2, MI4, MI5 (1 each).
- **r6's P1-1 plants are clean** on JSON, human and OTLP: `Outcome(token=field(repr=False), err=exc)` → `{'err': 'ValueError'}`, and `Creds` with a masking `__repr__` → `Creds`. Variants also clean: `slots=True`, `frozen=True, eq=False`, a hidden field on a parent class, a subclass overriding `__repr__`, `@dataclass(repr=False)`, a hidden field in a nested dataclass, and a field whose `repr` masks while its `str` leaks. MD1 and MD2 are red.
- **Recursion cap (2df9dcb).** In direct, mutual, three-function-cycle, two-line, outer-30 + recursion-200 + inner-30 and outer-30 + recursion-3 + inner-30 stacks:
  - the kept ends are byte-identical to `format_tb`'s first lines;
  - shown frames plus N equal the true frame count every time (for example 25 + 212 + 25 = 262);
  - output is 51 lines and about 7 KB instead of 1000 lines and 140 KB;
  - an audit hook saw **0 opens** (`open`, `os.open`, `io.open_code`) across all of them.
- **Never raises (642e7a3).** ME1 (only the budget caught at the top), ME4 (the intercept's `try` removed), ME5 (the stderr handler's fallback silent) and ME6 (the patcher's net keeps the extras) are each red.
  - A `__str__` returning a non-`str` becomes the type name.
  - A stdlib `%`-format with the wrong argument count, or `%d` of a `str`, becomes `WITHHOLDING_FAILED` on JSON and stderr, with no "--- Logging error ---".
  - Logging from 8 frames short of the recursion limit, and `logger.exception` of a `RecursionError`, both work.
  - A dataclass with a looping field `repr` hangs the patcher, but it hung the sink at the base too (no regression).
- **The floor (7b27e06).** ML1 (bare paths kept), ML3 (`s3transfer` dropped), ML4 (the opt-out lifts WARNING reduction), ML5 (the filter never drops sub-INFO), ML6 (the last resort does not reduce), ML7 (`boto3` dropped) and ML8 (the opt-out on by default) are each red.
  - It survives uvicorn's `LOGGING_CONFIG` applied after `install` (the DEBUG line stays dropped, the WARNING stays reduced).
  - A bare `dictConfig({"version": 1})` disables the family loggers, which fails closed.
  - With `LOG_LIBRARY_DEBUG=1`, WARNING and ERROR lines stay reduced (a botocore ERROR with a path is clean).
  - A child logger set to DEBUG is still dropped.
  - A family logger with `propagate=False` and its own raw handler bypasses everything, by construction; no estate code configures one (searched).
- **Undeclared family (ddb8e8d).** An undeclared histogram exports no attribute, so `tenant_id` can never be a histogram's multiplier. MU1 (the allowlist block removed), MU2b (`email` allowed), MU3 (the allowlist emptied) and MU4 (the histogram tenant drop removed) are each red.
- **Recursion cap mutants.** MC1 (26 lines kept) and MC3 (no cap) are red.
- **Carried residuals (b87018e).** MRa (the args repr), MRb (the 8+ single argument), MRc (`filename`) and MRd (`__notes__`) are each red.
- **G24-01 mutants (f36857f).** MG5 (the tenant back in the binding message), MG6 (the segment back in the cache message), MG7 (the host back in the S3 message), MG8 (no per-name attributes: 25 failed), MG9 (the operator id back) and MG10 (`operator_ids` back in "must be iterable") are each red. MP1 (no `__reduce__`) and MP2 (attributes settable) are red.
- **Stdlib twin mutants (7c21b64).** MS1 (`msg` not searched: 2 failed) and MS2 (extras not searched) are red.
- **Budgets, timing.**
  - 16 × 250-member groups plus 50 KB: 5 ms, withheld whole.
  - 300 one-link exceptions: withheld whole.
  - 256 exceptions plus 50 KB: 149 ms, quote withheld.
  - A 5 MB string extra plus a quoted exception: 98 ms, withheld.
  - A 200k list or set extra: 80–124 ms (it was 640 ms at r6).
  - Fail-closed never loses the record: it keeps the record and rewrites extras (P1-1 and P2-4 are what it gets wrong).
- **Refusals (299115b, f36857f).** Pickle, deepcopy and copy round-trip for every `str` offending value. `ReadOnlyIds` refuses item and attribute assignment. `str` and `repr` of every binding, cache-key and S3-host refusal carry no sentinel.
- **Stdlib twin (7c21b64).** `logger.error(exc)` on a stdlib logger and a stdlib `extra={"err": exc}` are withheld under `setup_logging` and on the safe default.
- **The posed sibling.** With copilot-mro-obsm `62c7413d` beside it, the inventory's copilot-mro limb resolves every emission shape (45 passed, 0 unresolved).
- **`captureWarnings`.** No estate caller (searched), as 4d86ae9 now declares.

## What I did not test

- Any live collector, Weaviate, Cognito, AWS or Postgres path. The httpx, openai, anthropic and urllib3 probes hit a local HTTP server on loopback with fake credentials.
- `test_cross_repo_reads_name_their_checkout.py` in the real workspace (deselected, as in r5 and r6).
- The full suite with the copilot-mro sibling posed; only the inventory and bounding files ran posed.
- flynapse-otel's M-FAILURE-HOME copy (r6 U6-03, routed to the fo lane) and its `withholding` rules beyond `withhold_url_secrets`.
- Behaviour under Python 3.12+.
- The implementer's own mutants beyond the ones re-stated here.
- Whether any estate call site today logs a > 10,000-node extra beside an exception (a pattern search found none; P1-1 is latent on that evidence only).

---

## Claims table

**Severity** is this reviewer's own scale: 0 = a content leak that ships, 1 = guard or lock integrity (including a latent leak or a fail-closed guard that fails open), 2 = a coverage gap, 3 = docs or process, — = nothing owed.

**Tier** is the packet's §2.3a scale: 0 = settled by a guard I SAW fail, 1 = consequential but reversible, 2 = irreversible or estate-shaping (a content leak into retained logs, a type-level log guard).

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U7-01 | utils | `utils/_exception_text.py:340-363`, `:394-397`; `log_bridge.py:194-202`; `_loguru_default.py:95-99`; `_exception_text.py:533-542` | One 10,000-node budget per record across all extras; "past either, it fails closed" (b24a023) | r6 P3-2: the work bound multiplied through extras | the extras fail closed, the MESSAGE fails open: an exception after the spend is never found, and its quote ships on JSON, human, OTLP, the safe default, stdlib `%s` args and `extra=`; clean at 2df9dcb | `test_the_work_bound_is_per_record_not_per_exception` (pins the extras; the message is `"m"`) | n/a — behaviour probe at 3 commits × 6 seats | 1 (latent content leak; a fail-closed guard fails open) | 2 | F1 | REFUTED — P1-1 |
| U7-02 | utils | `utils/_exception_text.py:498-515` | One link budget across every exception of a record, deduplicated (b24a023) | r6 P3-2: 16 groups took 5.2 s | 16 × 250 groups + 50 KB: 5 ms, withheld whole; 300 one-link: withheld; 256 + 50 KB: 149 ms, quote withheld | same test (the group half) | not re-run by me (the implementer reports "links not summed" red) | — | 1 | F3 | ASSERTED |
| U7-03 | utils | `utils/_library_lines.py:79`; `observability/intercept.py:68` | `LibraryLineFilter` rewrites `msg, args` to the reduced text (7b27e06) | reduce URLs and paths in the four families' lines | `args` are flattened before the stdlib twin: the real urllib3 retry WARNING ships `RemoteDisconnected('Remote end closed…')`, and a botocore ERROR ships `Username=…`; clean at 791df20 | `test_the_client_libraries_lines_carry_no_path_body_or_username` (checks the path only) | n/a — behaviour probe at 3 commits | 1 (a regression of a shape r6 SAW withheld) | 1 | F1 | REFUTED — P2-1 |
| U7-04 | utils | `utils/_exception_text.py:442-465` | A dataclass holding an exception is rebuilt within its own repr contract (d50635e) | r6 P1-1 | `repr=False` (slots, frozen, `eq=False`, a parent's), a custom `__repr__` and a class-level `repr=False` are clean; a custom `__str__` with the default `repr` ships on JSON and OTLP (clean at 8572635) | `test_a_dataclass_is_rebuilt_within_its_own_repr_contract` | **yes** — MD1: 1, MD2: 1 failed | 1 (latent; the sinks' contract is `str()`) | 2 | F1 | PARTIAL — P2-2 |
| U7-05 | utils | `utils/_exception_text.py:456-458` | A hidden field is still searched, so the message's quotes of an exception in it are withheld (d50635e) | the docstring says so | HEAD: `job failed: ValueError`; with MD3: `job failed: SEC_…` | **none effective** | **MD3 survives** (677 passed), behaviour-proven | 1 | 1 | F1 | OPEN — P2-7 |
| U7-06 | utils | `utils/_exception_text.py:418-436` | Built-in containers holding an exception are rebuilt as their own kind (since 1ca0268/8a55ca1; unchanged in range) | extras-as-types | NamedTuple, dict and list SUBCLASSES with a masking repr expose masked values; core-obsm `CatalogItem(dict)` (`storage_locations.py:180`) is a live type guard of this shape | `test_a_container_without_an_exception_keeps_its_own_rendering` (no-exception control only) | n/a — behaviour probe at 3 commits | 1 (latent; defeats a type guard) | 2 | F1 | OPEN — P2-3 |
| U7-07 | utils | `utils/_exception_text.py:355-363`, `:394-397` | A spent budget turns every later extra into its type name (b24a023) | fail closed | primitives too: `tenant.id: "str"`, `enduser.id: "str"`, `count: "int"` on JSON and OTLP | the b24a023 test (pins `"after": "list"`) | n/a — behaviour probe | 2 | 1 | F1 | OPEN — P2-4 |
| U7-08 | utils | `utils/_library_lines.py:1-30`; `observability/intercept.py:30`; `logging_config.py:54-60` (the `setup_logging` docstring) | "The HTTP and AWS client libraries' own log lines: floored at INFO, their URLs reduced" = four families | r6 P2-5 | at INFO, httpx ships a Weaviate collection plus `?tenant=` and a presigned key path with an email; at DEBUG, openai and anthropic ship whole prompt bodies | **none** for these families | not recorded | 2 | 1 | F1 | PARTIAL — P2-5 |
| U7-09 | utils | `utils/_library_lines.py:52-54` | A family line's URL is reduced to `scheme://host` (7b27e06) | r6 P2-5 (the pool id in a URL) | with ML2, a full URL in a WARNING or INFO line ships its path (pool id, S3 tenant key) | **none effective** | **ML2 survives** (677 passed), behaviour-proven | 1 | 1 | F1 | OPEN — P2-7 |
| U7-10 | utils | `utils/_library_lines.py:57-80`; `observability/intercept.py:147-176`; `_loguru_default.py:145-149` | Floor at INFO, filter drops sub-INFO, one opt-out, WARNING+ stays reduced, the last resort reduces (7b27e06) | r6 P2-5 | survives uvicorn's `dictConfig`; a bare `dictConfig` disables the loggers (closed); a child set to DEBUG is dropped; with the opt-out, WARNING and ERROR stay reduced | `test_the_client_libraries_lines_carry_no_path_body_or_username[*]`, `test_the_families_are_floored_a_higher_level_is_kept_and_reset_restores_them`, `test_a_client_librarys_warning_has_its_path_withheld_on_the_safe_default` | **yes** — ML1: 3, ML3: 2, ML4: 1, ML5: 1, ML6: 1, ML7: 2, ML8: 2 failed | — | 0 | F1 | SETTLED |
| U7-11 | utils | `utils/observability/metrics.py:106`, `:242-263` | An undeclared family exports only `tenant_id`; an undeclared histogram exports nothing (ddb8e8d) | r6 P2-6, runtime half | `email` and `route` dropped; a histogram exports no attribute | `test_an_undeclared_family_exports_nothing_but_its_tenant`, `test_an_undeclared_histogram_drops_a_tenant_too` | **yes** — MU1: 2, MU2b: 1, MU3: 3, MU4: 1 failed. MU2c (allowlist + `department`) survives; MU2 is equivalent (`user_id` forbidden upstream) | 3 (the allowlist is not pinned by equality; M-CARDINALITY's letter) | 0 | F1 | SETTLED; residuals P3-3, P3-6 |
| U7-12 | utils | `tests/unit/observability/test_legacy_family_inventory.py:198-416` | Every emission shape resolves or is reported; forwarders are followed to a fixpoint (849ca21) | r6 P2-6, inventory half | 5 call shapes silent (bound alias, `getattr`, `partial`, the wrapper via an attribute, a bare-name call); 4 key shapes misread; a constant collision misattributes a family | `test_every_emission_shape_is_resolved_or_reported[*]`, `test_no_emission_shape_went_unresolved[*]`, `test_every_emitted_family_is_declared[*]` | **partly** — MI1, MI2, MI4, MI5: 1 each, MV1: 2, MV3: 2 red; **MV2 survives** (behaviour-proven); decoys MI6, MI7, MI8, MI10 green | 1 | 1 | F1 | PARTIAL — P2-6 |
| U7-13 | utils | `observability/log_bridge.py:179-206`; `observability/intercept.py:65-72`, `:100-105`, `:122-133`; `_exception_text.py:394-397` | Logging never raises; withholding fails closed to type names and `WITHHOLDING_FAILED` (642e7a3) | r6 P2-1 | a raising getter becomes `Row`; a bad `%`-format becomes a constant with no "Logging error"; `BaseException` subclasses propagate (right, but undeclared) | `test_a_log_call_never_raises_when_withholding_fails`, `test_a_stdlib_record_whose_format_fails_is_a_constant_never_its_arguments` | **yes** — ME1, ME4, ME5, ME6: 1 failed each. ME2 and ME7 survive (operator-side, P3-6); ME8 is unreachable | 3 (the docstring overclaims) | 0 | F2 | SETTLED; residual P3-2 |
| U7-14 | utils | `utils/_exception_text.py:514-515` | `withheld_quotes` fails closed to `WITHHOLDING_FAILED` (642e7a3) | r6 P2-1 | an exception whose `__cause__` property raises: withheld at HEAD; with ME3 it ships `failed: SEC_…` | **none effective** | **ME3 survives**, behaviour-proven | 1 | 1 | F1 | OPEN — P2-7 |
| U7-15 | utils | `utils/_refusals.py:18-53`; `weaviate_service.py:377` | `ReadOnlyIds` pickles and deep-copies; `attach_ids` (299115b) | r6 P2-2 | `str` values round-trip through pickle, deepcopy and copy; a non-`str` unpicklable value (f36857f) makes the refusal unpicklable | `test_a_refusal_crosses_a_process_boundary_and_its_ids_stay_read_only` | **yes** — MG2: 1, MP1: 1, MP2: 1 failed; MP3 is equivalent | 3 | 0 | F2 | SETTLED; residual P3-1 |
| U7-16 | utils | `utils/_exception_text.py:518-542`; `_loguru_default.py:139-149` | The stdlib twin searches `record.msg` and `extra=` (7c21b64) | r6 P2-3 | msg-is-the-exception and an `extra=` exception are withheld on JSON, OTLP, stderr and the safe default | `test_a_stdlib_record_whose_message_is_the_exception_is_withheld`, `test_the_safe_sink_withholds_an_exception_quoted_beside_the_message` | **yes** — MS1: 2, MS2: 1 failed | — | 0 | F1 | SETTLED |
| U7-17 | utils | `utils/_exception_text.py:541` | stdlib extras are walked one level deeper (`EXTRA_DEPTH + 1`) for the wrapper dict (7c21b64) | parity with loguru extras | with MS3, a 3-level nested `extra=` ships on the safe default and the OTel stderr handler | **none effective** | **MS3 survives**, behaviour-proven | 1 | 1 | F1 | OPEN — P2-7 |
| U7-18 | utils | `utils/_exception_text.py:409-415` | A finished future's exception joins `found` (791df20 pins it) | r6 P2-4 | — | `test_a_finished_futures_exception_is_withheld_from_the_message_that_quotes_it` | **yes** — M23f: 1 failed | — | 0 | F1 | SETTLED |
| U7-19 | utils | `utils/_exception_text.py:56`, `:86-90` | A stack is capped at 25 lines at each end, with `[N frames omitted]` (2df9dcb) | r6 P3-1 | the ends are identical to `format_tb` in 6 shapes; shown + N = the true frame count; 0 opens | `test_recursion_traceback_cannot_collapse_is_capped_at_each_end[*]`, `test_a_run_of_four_says_one_more_time_as_traceback_does` | **yes** — MR3: 2, MR5: 1, MC1: 2, MC3: 2 failed; **MC2 survives** (N counts lines: 15 vs 212), behaviour-proven | 2 | 1 | F3 | PARTIAL — P3-6 |
| U7-20 | utils | `utils/_exception_text.py:258-300` | Carried residuals: the args repr, an 8+ single arg, `filename`/`filename2`, `__notes__` (b87018e) | r6 P3-4 | the four named shapes are withheld | `test_the_carried_residuals_are_quotes_too` | **yes** — MRa, MRb, MRc, MRd: 1 failed each; MRe (`filename2`) and MRf (an argument's `repr`) survive | 2 | 1 | F1 | PARTIAL — P2-7 |
| U7-21 | utils | `utils/tenancy_context.py:181-239`; `cache_keys.py:192-345`; `s3_service.py:1124-1141` | G24-01 beyond Weaviate: constant messages, ids as attributes (f36857f) | r6 P3-5 | `str` and `repr` carry no sentinel. Residuals: `migrate_weaviate_collection.py:228`, `document_catalogs.py:101`, `:108` | the 12 sentinel cases plus the S3 raise test | **yes** — MG5: 2, MG6: 1, MG7: 2, MG8: 25, MG9: 2, MG10: 1 failed | 3 | 0 | F1 | SETTLED; residual P3-1 |
| U7-22 | utils | `utils/_interpreter_hooks.py:87-100` | The warnings trade-offs are declared (4d86ae9) | r6 P3-3 | the text matches r6 P3-3; `captureWarnings` has no estate caller (searched) | **none** (docs) | n/a | 3 | 1 | F3 | ASSERTED |
| U7-23 | utils | whole range | Each commit is green at its own HEAD; ruff adds nothing; the copilot-mro limb runs when posed | lane rules | 14 sweeps exit 0; 1144 ruff diagnostics each, zero (file, code) delta; posed with copilot-mro-obsm `62c7413d`: 45 passed, 0 skipped | the suite | n/a (measurement) | 3 (1144 pre-existing ruff diagnostics) | 0 | F2 | SETTLED (measured) |

**Totals: 23 claims.**

- 8 SETTLED, all tier 0 (U7-23 is a measurement, not a guard);
- 2 ASSERTED;
- 5 PARTIAL;
- 2 REFUTED;
- 6 OPEN.

---

## Open claims, tier 2 first

**Tier 2**

- **U7-01 (P1-1)** — a spent node budget fails OPEN for the message: an exception placed after a ~10,000-node extra, stdlib argument or `extra=` key is never searched, and its quote ships on every sink. Introduced by b24a023; the test pins only the extras. FIX-FIRST.
- **U7-04 (P2-2)** — the dataclass rebuild honours `repr` but the production sinks render `str()`: a `__str__`-hidden field ships.
- **U7-06 (P2-3)** — NamedTuple, dict and list subclasses with a masking repr are rebuilt as plain containers; core's `CatalogItem` is a live instance of that type guard.

**Tier 1**

- **U7-03** (P2-1: the library filter drops `args` before the stdlib twin; exception text ships again).
- **U7-05, U7-09, U7-14, U7-17** and the MRe/MRf half of **U7-20** (P2-7: withholding lines with no test — MD3, ML2, ME3, MS3 survive and ship text).
- **U7-07** (P2-4: `tenant.id: "str"` after a spent budget).
- **U7-08** (P2-5: httpx at INFO, openai and anthropic at DEBUG).
- **U7-12** (P2-6: silent inventory shapes; MV2 survives).
- **U7-19** (P3-6: MC2, N unpinned for mixed stacks).
- **U7-02** and **U7-22** (asserted).

