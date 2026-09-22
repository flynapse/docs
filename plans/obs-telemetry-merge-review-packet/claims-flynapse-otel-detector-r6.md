# Claims packet: flynapse-otel review r6 (the answer to r5: proven narrowing, policy validation and ratchet, ratchet base, URL withholding, failure home, drop views, isolation guard, log boundary)

Independent adversarial review by Opus, 2026-09-21. It was read-only throughout. No code tree was edited, checked out or committed. Every mutation ran in a private scratch copy of `927a729` (`scratchpad/otel-review-r6/m/flynapse-otel`), was applied, grep-confirmed, run, reversed from a backup, and md5-checked against the `git show 927a729:<path>` blob after each run; every restore matched. Every ratchet experiment ran in scratch git repositories (`scratchpad/otel-review-r6/ratchet_ws/`); the real repos were only read (`git branch -vv`, `rev-parse`, `merge-base`, `archive`).

| repo | tree | branch | range reviewed | commits |
|---|---|---|---|---|
| flynapse-otel | `/home/aditya/Code/flynapse-otel` (clean, HEAD `927a729`) | `main` (ahead of `origin/main` by 35) | `34c814a..927a729` | `fe4c15e` `7c5e0e6` `8014514` `f2c1214` `e56005b` `65b6eb2` `030785b` `e478f1c` `493357d` `850678b` `927a729` |

**How I ran it.**
- Each commit was extracted with `git archive <sha>` into `scratchpad/otel-review-r6/c/<sha>`, with the sibling repos (`utils`, `core`, `dashboard`) symlinked beside it, so the parity test reads utils `594327e` by `git show` from the sibling checkout.
- The command, from the tree root: `DEBUG=false PYTHONPYCACHEPREFIX=<fresh dir> PYTHONPATH=<tree>:<guard> /home/aditya/Code/flynapse-otel/.venv/bin/python -m pytest -p no:cacheprovider`. Every `__pycache__` was cleared first.
- **Network guard:** a `sitecustomize.py` on `PYTHONPATH` replaces `socket.connect`/`connect_ex`/`getaddrinfo` and refuses every non-loopback address (a probe connect to `1.1.1.1:80` raised `NetworkRefused` before each run). Loopback stays open because the suite's own instrumentor tests serve on `127.0.0.1`.
- I checked pytest's own exit status on every run (`PYTEST_RC`).
- `flynapse_otel.__file__` pointed into the scratch tree on every run, and `rootdir` was `…/otel-review-r6/c/<sha>`.

**Every commit is green at its own HEAD.** Each run also had 1 skipped and 1 xfailed, the same as r5's base: the skip is `test_root_anchoring`'s "other checkout" proof, which finds no sibling checkout in scratch; the xfail is the declared hand-built `SyntaxError` header forgery.

| commit | result | PYTEST_RC |
|---|---|---|
| 34c814a (base) | 1832 passed | 0 |
| fe4c15e | 1874 passed | 0 |
| 7c5e0e6 | 1901 passed | 0 |
| 8014514 | 1923 passed | 0 |
| f2c1214 | 1938 passed | 0 |
| e56005b | 2087 passed | 0 |
| 65b6eb2 | 2152 passed | 0 |
| 030785b | 2186 passed | 0 |
| e478f1c | 2191 passed | 0 |
| 493357d | 2204 passed | 0 |
| 850678b | 2205 passed | 0 |
| 927a729 | 2212 passed | 0 |

**Corpus:** 1425 rows at `927a729` (1159 leak, 246 clean, 20 limit), as claimed.

**Verdict: FIX-FIRST.** No content leak ships today, and every r5 finding the implementer answered is answered in substance: all 12 r5 P1-1 regression plants are caught, every r5 policy attack is refused or ratcheted, every r5 surviving mutant now dies, and the estate re-scan reproduces exactly. Three things still stop a clean pass, and all three sit on the adoption path:
- **P1-1 (again):** the new `proven` set is still not a proof. 21 new plants that `de501a8` catches go silent at `927a729`. None is live in the estate, and a sketch that closes 15 of them changes zero estate findings.
- **P1-2:** refusal types are matched by TAIL NAME. A code-only alias (`Refusal = Exception`) or any same-named class from another module silences a body echo with no policy line and no register line changed, so neither ratchet sees it. core's refusal type is literally named `Refusal`.
- **P2-1 (tier 2):** during adoption the ratchet has no baseline in any consumer. Every consumer's register is a new file and nothing is pushed; four of six are on `obs-merge` with no upstream. The only green path is `missing_ok=True`, which returns `None`, and the plan does not say what a guard does with it.

---
## Findings, ranked

### No P0

- **Estate exposure of every new narrowing hole is zero.** I re-scanned r5's six estate snapshots with `927a729` twice: once as shipped, and once with a strict-proof sketch that closes 15 of the 21 plants below. The two scans are identical in all six repos (utils 117 findings, core 29, api 15, shift 8, telegram-bot 117, copilot-mro 900). So no live site rests on the holes.
- **The re-scan claim reproduces.** Against `de501a8`, `927a729` drops exactly the 8 copilot-mro keys r5 measured as over-reports (7 `health_check` body keys and `scripts/certify_model_profile.py::main` `helper.caught-text`) and adds none, in all six repos.
- **The two adoption trees agree too.** On utils-obsm `594327e` (119 findings, 81 keys) and telegram-bot `cfb1d98` (112 findings and 66 keys under the `failure_fields`-only policy; 7 under its own intended policy), `de501a8`, `34c814a` and `927a729` give identical results.

### P1-1: the callee set is "proven" while the name is rebound in ways the proof never reads (fe4c15e)

**Where.**
- `flynapse_otel/testing/exception_text/_scan.py:223-324`: `proven`, `_proven`, `_proven_name`, `_proven_method` and `_transparent`.
- The proof is consumed by `returned_slots` at `:326-346`.
- The facts it ignores are at `_facts.py:304`, `:343`, `:351` and `:376`, where `revoked_all` is set.

`_proven_name` reads only the module's own `Binding` list for the name, and `_proven_method` only class-scope `def`s. Everything that rebinds a function or method WITHOUT a name binding in that module is invisible, and the narrowing then drops the exception argument.

The scan already records some of these: a star import, `exec` and `globals()[…] =` each set `Facts.revoked_all`. The proof never consults that flag; only builtin trust does (`_facts.py:417`).

**Measured.** The plants are in `plants6/p_proof.py`. Each of these 21 is caught by `de501a8` and silent at `927a729`:

| id | shape |
|---|---|
| B01 | `from vendor import *` AFTER `def describe(label, exc): return label` |
| B02 | `exec("from vendor import describe")` |
| B03 | `globals()["describe"] = vendor.describe` |
| B04 | `setattr(sys.modules[__name__], "describe", …)` |
| B05 | `sys.modules[__name__].describe = …` |
| B06 / B06b | another scanned module monkeypatches `a.describe = lambda label, exc: f"{label}: {exc}"`, or sets it to an external |
| B07 | `Reporter.describe = lambda self, label, exc: …` after the class |
| B08 | `setattr(Reporter, "describe", vendor.describe)` |
| **B09** | **`__init__` does `if describe is not None: self.describe = describe` (constructor-injected strategy), then `self.describe("sync", exc)`** |
| B10 | a class decorator rewrites the method |
| B11 | a metaclass `__new__` rewrites it |
| B12 | a base class's `__init_subclass__` rewrites it |
| B13 | `class Loud(vendor.DescribeMixin, Reporter)`: an external base earlier in the MRO |
| B14 | `__getattribute__` intercepts `describe` |
| B16 | `sys.modules["pkg.a"] = loud` in the package `__init__` |
| B24b | another module rebinds `functools.cache` |
| B25 | `builtins.staticmethod = …` |
| B26 | `self = other` inside the method |
| B27 | a nested callback `def on_fail(self, exc)` inside a method, whose own `self` is another object |
| B30 | `self.describe = types.MethodType(vendor.describe, self)` in `__init__` |

**Correctly refused (16 of my plants).** `__wrapped__`, a module `__getattr__`, a conditional def vs an import fallback, conditional defs in both branches, dict dispatch (`H[k](…)`, and `H.get(k)(…)` after a mutation), a `global` rebind in a function, `importlib.reload`, a `functools.wraps` wrapper that appends `args`, an in-module `functools.lru_cache = …`, a subclass override by assignment in another module, a `try`/`except ImportError` fallback, walrus, a class-body `global`, `match` capture, and `del` then re-import.

Every r5 plant also stays caught: A20 to A26, A28, A30 to A32 and A34, plus A08 and E01, newly.

**Operator view.** Nothing appears in a scan. A leak written behind a constructor-injected override (B09), a class monkeypatch (B07), or a star import placed after the def (B01) reconciles clean.

**Fix, and it is precision-free.** `scratchpad/otel-review-r6/strict_proof.py` sketches the fix, and it changes zero estate findings. Refuse the proof when:
- `facts.revoked_all` is set;
- the callee name appears anywhere in the scan as an attribute-store target, as a literal `setattr` name, or as a literal string subscript-store key (which covers B04 to B12 and B30);
- for `self.`/`cls.`: any class in the union carries a class decorator, a metaclass or class keywords, or defines `__getattribute__` or `__init_subclass__`.

The sketch closes 15 of the 21. The remaining six can be refused or declared:
- B13: refuse when a scanned subclass lists a base outside the scan and `RECORD_BASES`;
- B16: refuse cross-module proofs when the scan stores into `sys.modules[…]`;
- B24b/B25: refuse the transparent-decorator allowlist when the scan stores to `functools.*` or `builtins.*` anywhere;
- B26/B27: require `self` to be the enclosing METHOD's own first parameter with no other binding.

Cost: B01b (a star import BEFORE the def, where the def wins) becomes an over-report, which is conservative.

### P1-2: refusal types are matched by TAIL NAME, so code alone can bless a body echo (7c5e0e6)

**Where.** `_module.py:121-133` (`_handler_types` and `_types_of` both return `tail(item)`), used at:
- `:460`, a handler of refusal types;
- `:504`, `isinstance` narrowing;
- `:787`, a parameter annotated with one.

`Policy.__post_init__` (`_model.py:197`) refuses only BUILTIN names (`BUILTIN_EXCEPTIONS`, `:174`).

**Measured.** In `policy6.py`, each case silences `raise HTTPException(500, detail=str(err))`.

With `refusal_types={"Refusal"}`, a legitimate policy that passes validation:
- N1: `Refusal = Exception`, then `except Refusal as err`.
- N2: `from builtins import Exception as Refusal`.
- N6: `from vendor.errors import Refusal`, a DIFFERENT class with the same tail.
- N7: `Εxception = Exception` (Greek Epsilon) with `refusal_types={"Εxception"}`.

In every case the policy ratchet sees no change, because the policy did not change. The register sees no change either, because there is no finding.

core defines `class Refusal(ValueError)` (`core/exceptions/exceptions.py:145`), and the plan hands core `refusal_types` = its refusal classes. So for core, any module that imports or defines another `Refusal`, or aliases one, is sanctioned in every body. That is the same "one line blesses a leak" lever r5 P1-2 closed, now with no policy line at all.

**Also accepted at construction (held only by the policy ratchet).**
- Third-party broad classes as refusal types: N4 `ValidationError` (pydantic's message quotes the input) and N5 `ClientError` (botocore's quotes the AWS message).
- Third-party readers: N14 `jsonable_encoder` from `fastapi.encoders`, N17 `safe_repr` from pydantic, and N18 a `__main__` source.

Each of these silences a real leak once added. The ratchet names each one (`NEW REFUSAL TYPE`, `NEW READER`), but see P2-1: at adoption there is no baseline to name it against.

**Fix.**
- Resolve refusal types the way `is_record` now resolves records (`_scan.py:164-200`). Declare each by its qualified name (`core.exceptions.exceptions.Refusal`), and match a handler, an `isinstance` or an annotation by `resolve_all` of the spelled class to that qualified name, never by tail.
- Have the scan refuse a policy whose refusal name resolves to no class defined in the scan.
- Refuse a reader source that is neither in the scan nor one of the estate homes (`flynapse_otel.failure`, `utils.observability*`).

### P2-1 (tier 2): the ratchet has no baseline anywhere during adoption, and a moved register forces the same opt-out (f2c1214)

**Where.** `_ratchet.py:67-120` (`merge_base_text`), and the plan's P2-2 notes (`docs/plans/shared-exception-text-detector.md:842-847`). The notes say `missing_ok=True` is for a new register, but not what an adopting guard does with the `None` it returns, nor which `against` each repo passes.

**The real layout, read-only.**

| repo | branch | upstream | nearest remote ref | its merge base |
|---|---|---|---|---|
| flynapse-otel | `main` | `origin/main` | `origin/main` | 35 behind HEAD |
| telegram-bot | `main` | `origin/main` | `origin/main` | 21 behind HEAD |
| shift-optimizer | `main` | `main/main` | `main/main` (the remote is named `main`, so `origin/main` does not exist) | 8 behind HEAD |
| utils-obsm | `obs-merge` | **none** | `origin/langgraph-merge` | 91 behind HEAD |
| api-obsm | `obs-merge` | **none** | `origin/langgraph-merge` | 65 behind HEAD |
| copilot-mro-obsm | `obs-merge` | **none** | `origin/langgraph-merge` | 162 behind HEAD |
| core-obsm | `obs-merge` | **none** | `origin/master` (no `origin/main`) | 121 behind HEAD |

**Measured in mirrors** (`ratchet6.py`, scratch clones of each shape):
- **L1, the flynapse-otel and telegram-bot shape.** `origin/main` catches committed growth (`GREW`). `main`, `HEAD` and a SHA are each refused (`ValueError`).
- **L2, the `-obsm` shape.** `origin/obs-merge` and `@{u}` fail closed (`ValueError`). `origin/main` fails closed with `FileNotFoundError`, because the shared-detector register is a NEW file in every consumer. With `missing_ok=True` the result is `None`, both at adoption and after any later growth of the never-pushed register (L2e).
- **L3, shift-optimizer.** `origin/main` fails closed and `main/main` works, so each guard needs its own `against`.
- **L4.** A clean checkout at the pushed tip raises. With `base_may_be_head=True` it compares the working tree with HEAD, which catches uncommitted growth. Moving `refs/remotes/origin/main` to HEAD locally passes committed growth (L4d). That is deliberate and inherent, and the docstring declares it.
- **L5.** A local branch literally named `origin/main` fails closed.
- **L6.** Inside a `git worktree` on `obs-merge`, it catches.

**So:** until each consumer's first push, the only way to make a consumer's guard green is `missing_ok=True`. A guard that then skips on `None` has an inert register ratchet and an inert policy ratchet for the whole adoption window. That window is when registers are built and when P1-2's third-party refusal types and readers would be declared.

**The coordinator's three r7 attacks, against the SHARED ratchet:**
1. **`git merge -s ours` discarding a repair: immune by construction.** The shared ratchet never walks history; it compares trees at the merge base.
   - C1b: a repair that LANDED upstream, un-done by `-s ours` on a branch, is caught (`NEW KEY` and `UN-REPAIRED`).
   - C1a and C1c: a repair only on a local branch, or only on a pushed side branch that never reached `origin/main`, passes. That is correct under the base-relative contract, because the repair never reached the base.
2. **Register and guard moved to a new folder, with an un-repair in the same commit.**
   - Reading the NEW path fails closed (`FileNotFoundError`).
   - With `missing_ok=True` the result is `None`, and the defeat succeeds if the guard skips.
   - Reading the base at the OLD path catches it (`NEW KEY` and `UN-REPAIRED`), but `merge_base_text` has no way to say "this register moved from X". A legitimate move is therefore pushed toward exactly the `missing_ok=True` that defeats the ratchet.
3. **Shallow clones fail closed in every shape where the base is outside the fetched depth:**
   - `--depth 1 --branch feature` gives `ValueError` (no remote ref);
   - `--depth 1 --no-single-branch`, with or without `base_may_be_head`, gives `RuntimeError` (no merge base);
   - `--depth 2` gives `RuntimeError`;
   - a CI-style `fetch --depth 1 <sha>` gives `ValueError`;
   - `--depth 3`, where the base is inside the depth, catches `GREW`.

   Same-commit policy and register loosening on local `main` is caught on both sides (`GREW` and `NEW REFUSAL TYPE`).

**Fix.**
- When the register is missing at the merge base, fall back to the register as it stood in the commit that first ADDED it on this branch (`git log --full-history --diff-filter=A --format=%H -- <path>`, oldest). Growth after adoption is then ratcheted before any push.
- Give `merge_base_text` a `moved_from=` path, read at the base when the new path is absent, so a move does not need `missing_ok`.
- Write the per-repo `against` into the plan: `origin/main`, `main/main` for shift-optimizer, and a decision for the four `obs-merge` worktrees.

### P2-2: `load_policy` executes the base policy text with the CURRENT imports, so a split policy is unratcheted (7c5e0e6)

**Where.** `_model.py:246-254`.

If a repo's policy module imports any part of its policy (`from tests._policy_readers import READERS`), the merge-base text is executed against the working tree's `READERS`. Baseline and current are then identical, and `policy_problems` returns `[]`.

**Measured:** in `policy6.py` L1, a new reader added only in the imported module passes. The same holds for a policy computed from the environment (L2).

Two further bypasses, both deliberate:
- Post-validation mutation is not frozen. `policy.bounded_readers[...] = …` (M1) works, `refusal_types` passed as a `set` can be `.add("Exception")`-ed after validation, and `object.__setattr__` works (M2). The ratchet still names each one.
- The SHARED `ESTATE_FAILURE_FIELDS` mutated in-process (M6) is blind even to the ratchet.

**Fix.**
- Have `load_policy` refuse a policy module that imports anything but `flynapse_otel.testing.exception_text`, or compare a canonical serialization of the whole policy.
- Freeze the policy in `__post_init__`: `MappingProxyType(dict(...))`, and coerce every set field to `frozenset`.

### P2-3: URL withholding (65b6eb2): the five declared residuals are the only r5 ones left, but not the only ones

**r5's 50 cases.** Exactly U12, U15, U27, U36 and U48 still leak, and all five are declared. All the r5 P2-4 fixes hold: U04, U05, U11, U17, U21, U23, U28 to U32, U35 and U40.

**Beyond them** (`url6.py`, 50 new cases; 20 leak at HEAD, of which V03, V06, V11, V37 and V48 are by design or in a declared family):
- **Vocabulary:** `pw`, `pin`, `sid`, `access_code`, `refresh` and `bearer` as parameter names (V24 to V26, V29, V31, V32). `state` and `nonce` also ship, arguably not credentials.
- **Decoding stops at 3 passes** (`withholding.py:724`) while the docstring says "percent-decoded to a fixed point". A quadruple-encoded name ships (V13).
- **Fullwidth `＆` and `？` separators** (V35, V36), the U27 family.
- **A JSON `\u0026`-escaped ampersand** (V50), as Go's `encoding/json` writes by default.
- **Path-embedded webhook secrets** (`hooks.slack.com/services/T/B/<secret>`, V38). This is U36's family, but U36 is declared as a telegram-bot matter only.
- **The continuation bound.** A value running past 8 words (V01), or across a newline (V05), ships. The 8-word bound is unpinned: mutant MW01b (8 to 2) survives.

**Over-withholding** (fail closed, but it destroys debugging value):
- `GET /static/app.js?t=1695301234` becomes `?:redacted`;
- `?email_verified=true&page=2` and `?invite_id=42` are redacted whole;
- **the new non-web digits rule destroys the host.** `postgres://db:5432/app?note=a@b` becomes `postgres://b`, and `git+ssh://host:22/repo@v1.2 checked out` becomes `git+ssh://v1.2 checked out`: any later `@` in the run makes `host:port` read as `user:password`.

**Fix.** Add the six names and pin the 8-word bound. Either decode to a real fixed point (with a budget) or change the docstring. Declare the separator, escaped-ampersand and path-token families together with U27 and U36. The lost host is the price of U04/U05, because a password may hold `/` or `?`. Failing closed is defensible, but declare it.

### P3 (docs, process and defence in depth)

- **URL timing.**
  - r5's shapes now cost 1.4 to 1.5x (L6 1.08 to 1.55 s; L7 4.66 to 7.13 s, 2 MB of ` ?a=`).
  - The new anchors cost 2 to 4 µs per character where they cost nothing before (N1 ` ;a=` 3.1 s/MB; N3 ` //x@` 3.8 s/MB; N5 ` %3a%2f%2f` 2.2 s/MB).
  - It is linear (0.25/0.5/1/2 MB of ` //x@`: 0.86/1.78/3.55/9.7 s, measured under a concurrent mutation run).
  - There is no length cap before the boundary, and it runs in the logging call. Recommend withholding a string past a size bound whole (fail closed).
- **The log boundary (927a729) fails OPEN on unknown container types.** `_vetted` (`withholding.py:654-674`) returns any value that is not a str, bytes, Mapping, list or tuple as it is. A `frozenset`/`set`/`deque` body holding a rendered traceback ships it (B14), although the docstring says "the body, whatever its shape". Everything the r5 P3 listed now holds: attributes, dict and list bodies, keys, bytes, tuples and depth-7 nesting (B2 to B8). Return `UNVETTED` for any other non-primitive.
- **Header variants the body rule does not know.**
  - loguru's `Traceback (most recent call last, catch point marked):` (B11). The bridge sends the stdlib rendering, so this is not reachable today.
  - A lower-cased rendering (B18).
- **Site fingerprints** (`_facts.py:391`, `limit=400`). Two different leaks whose normalised source shares its first 400 characters get the same `site` (measured), so "a leak fixed and another added under the same key cannot hide" fails for long calls. Two identical copy-pasted lines also share a site (count governs).
- **Unpinned bits.**
  - MV09: the `Accepted.sites` type check.
  - MR08: the HEAD `rev-parse` failure path.
  - MP11: `functools.cache` transparency, which only affects precision.
  - MB05: r5's "precise ignored" now only widens `returned_text`, whose sources are already flagged at the def, so it is effectively equivalent.
  - MB01b is equivalent at HEAD, because the `return_slots` membership check precedes it.
- **Dates:** only ISO `YYYY-MM-DD` is read. `2099‑12‑31` (U+2011), `2099/12/31` and `31-12-2099` escape the future-date check.
- **copilot-mro r7 M-TRACEBACK plants, folded in** (`mro7_conv.py`, all 75 plants).
  - The shared detector catches everything the coordinator named:
    - `task.exception()` inline (N06, N06b, N19);
    - a walrus-bound `future.exception()` (N05);
    - the `**kw` forwarding helper (N10);
    - gather results by index (N14), by tuple unpacking (N13), by comprehension (N01d) and by negated narrowing (N01b, N01c);
    - decoy describer modules matched by tail or file stem (N30, N31, N32, N33);
    - `type is` and `match` narrowing on a SEEDED value (V01, V02, V03);
    - all 47 r6-era plants in `plants.py`.
  - It misses seven:
    - N01, N02, N03, N04 and N18: `isinstance`, `type is`, `match` and queue narrowing on a value that no source seeds. The shared model has no "narrowed to an exception" source.
    - N15 (V07): a `SimpleNamespace` attribute read through `vars()`.
    - N20 (V04, V05): `notes.setdefault("errors", []).append(str(e))` then logging `notes`. **This last one is a realistic shape, and it is not declared.** `defaultdict(list)[k].append` (V06) is caught.
- **The isolation guard (493357d) and the drop views (e478f1c) hold.** r5's MB02 to MB04 are red, and so are five more spellings of mine (MB04b to MB04f). Removing the four old `http/dup` names (MD01), or any one of them (MD02), turns the bootstrap tests red.

---

## What I tried to break and could not

- **r5's P1-1 regressions.** All 12 are caught at `927a729` (A20 to A26, A28, A30 to A32, A34), and so are A08 and E01, newly. Of the 162 r5 plants, 148 are correct. The 14 still missed (A29, C44, C45, C61, D10, D21, D24, D25, R01, R03, S01, S02, S04, S08) are each a pinned `limit` row in the corpus. My proof mutants MP01 to MP10 and MP12 each turn the suite red.
- **Return shapes under narrowing** (`plants6/p_returns.py`, 25 plants): a generator expression, `map`, `partial`, `IfExp`, `BoolOp`, `dict(…)`, `.format`, an alias, a nested helper, a class instance field, tuple unpacking, a comprehension, `getattr`, walrus, `*a`/`**k` calls, `try/finally`, two returns, `with`, a loop, a `global`, `str.join`, `vars`, `__dict__` and `format_exception`. All are caught.
- **The fixed-point cap** (`_MAX_ROUNDS = 12`). Forwarding chains of depth 5, 11, 12, 13, 14, 20 and 40, in one module and across modules, in both definition orders, are all caught. Unsettled callees read every argument, so stopping early fails closed.
- **The policy.**
  - r5's P1 to P5, P7 and P8 are each refused at construction; P6 is named by the ratchet (`NEW READER`).
  - A typo'd sink (`lgo`) is refused.
  - `dataclasses.replace` re-validates.
  - An empty `sinks` only narrows (more findings).
  - A fullwidth `Ｅxception` or a `builtins.Exception` refusal type blesses nothing, because the AST is NFKC-normalised and the tail differs.
  - A renderer name from a third-party source (`print_exception`) is refused by name.
  - Today `_NEVER_READERS` equals the vocabulary's renderers plus the `sys` accessors.
- **The ratchet.**
  - A local ref, `HEAD`, a SHA, `@{u}` and a local branch literally named `origin/main` are each refused.
  - Inside a `git worktree` it works.
  - `-s ours` un-doing a LANDED repair is caught.
  - Every shallow shape with the base outside the depth fails closed.
  - Same-commit policy and register loosening is caught on both sides.
  - r5's MU60 and MU61 die, and so do my MR01 to MR07 and MV01 to MV08, MV10 and MV11.
- **Failure home.**
  - **Parity:** `flynapse_otel/failure.py` at `927a729` is AST-identical, docstrings aside, to utils `594327e`'s `utils/_exception_text.py` plus `utils/observability/failure.py`, function by function and constant by constant. The one difference is `rendered_failure`, which inlines one local (`links = _links(exc)`).
  - **The parity test** pins the full SHA and compares every field, renderer and helper with `==`. The one exception is a finished future's repr, which names its address, so it is compared by the secret's absence.
  - **No file reads.** An audit hook on `open`, plus spies on every `linecache` entry point, saw ZERO reads across `failure_fields`, `rendered_failure`, `frame_headers`, `withheld_exception_text`, `withheld_rendered_traceback`, `withheld_extra` (an asyncio future and a Task in DEBUG mode, a `concurrent.futures` future, a dataclass, a nested list), `withheld_quotes`, `withheld_stdlib_message` and the log boundary. For a debug-mode future, asyncio reads the source line when the future is CREATED, never at `repr`.
- **The log boundary.** An attribute value, a dict body, a list body, a tuple attribute, a mapping key, bytes and depth-7 nesting are each reduced to frames. Depth 12 becomes `<unvetted>`. CRLF, indented and JSON-escaped renderings are withheld, with the text around them over-withheld. B2, B3 and B6 from r5 are fixed.
- **r5's 11 unpinned URL markers.** Every marker and exact name, old and new, is now pinned (the MWM and MWN rows in the appendix). The `http/dup` drop views and the isolation-guard spellings are in the appendix.
- **The estate.** The re-scan claim, and both adoption trees, reproduce exactly.

## What I did not test

- The live bootstrap under `OTEL_SEMCONV_STABILITY_OPT_IN=http/dup`. The drop views are checked by the unit tests and my mutants only.
- ASGI's metrics, because the instrumentor is not installed in this venv.
- core, api, copilot-mro and shift-optimizer at their CURRENT HEADs. The brief named two adoption trees; the other four were scanned as r5's snapshots. Several of those trees moved during this review (utils-obsm `7c21b64`, copilot-mro-obsm `36aa4254`).
- Python 3.12+ syntax (type parameters, `type` statements), because the venv is 3.11.
- The implementer's Q, PV, PR, K, C and G mutation tables, row by row. I ran independent mutants instead.
- Red counts per mutant. My harness recorded pytest's exit status and killed or survived; the per-test counts were truncated.
- Where the OTLP encoder's "Invalid type … of value …" exception, raised for a `frozenset` body (B14), is itself logged.
- Whether any estate URL today uses `pw`, `pin`, `sid`, `access_code`, `refresh` or `bearer` as a parameter name.
- `pre_boundary`'s `deepcopy` failure path.

---

## Claims table

Severity: 0 = a content leak that ships; 1 = guard or lock integrity; 2 = a coverage gap; 3 = docs or process. Tier is §2.3a's: 0 = settled by a guard I SAW fail; 1 = consequential but reversible; 2 = irreversible or estate-shaping. Chunk: F1 = contract and privacy.

| # | Repo | File:line | Decision taken | Why | Evidence | Guard test | Mutation-proved? | Severity | Tier | Chunk | Claim state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R6-01 | flynapse-otel | `_scan.py:223-346` | A call's value is narrowed to the arguments a PROVEN callee set returns; a proof needs every binding to be a transparent def, a lambda, or an alias or import proven into the scan; `self.f` is the union of every same-named method | r5 P1-1 (12 regressions) | All 12 r5 plants caught, plus A08 and E01. **21 new plants silent** (B01–B14, B16, B24b–B27, B30); all are caught by `de501a8`. Estate exposure 0 | corpus `rev:otel-r5/precision*` rows | yes: MP01–MP10 and MP12 red (my mutants); MU03–MU06 and MB01 red. The PROPERTY fails on the 21 | 1 | 1 | F1 | **PARTIAL**: r5's shapes SETTLED; "proven" REFUTED (P1-1) |
| R6-02 | flynapse-otel | `_module.py:121-133`, `:460`, `:504`, `:787` | Refusal types are matched by the TAIL of the spelled class | Designed refusals are clean in bodies | N1, N2, N6 and N7: an alias or a same-named class silences `HTTPException(detail=str(err))` with no policy or register diff; core's type is `Refusal` | none | not applicable: no guard exists | 1 | 2 | F1 | **OPEN** (P1-2) |
| R6-03 | flynapse-otel | `_model.py:126-217` | `BoundedReader`/`Policy.__post_init__` refuse builtin, stdlib and renderer readers, sinks outside log/output/span, non-span-safe span readers, builtin refusal types, and shrunken parameter names | r5 P1-2 (P1–P8) | r5's P1–P5, P7 and P8 refused; P6 ratcheted; typo'd sink refused. Third-party refusal types (N4, N5) and readers (N14, N17, N18) accepted, and silence a leak | `test_exception_text_policy.py` | yes: MV01, MV02, MV06 and MV07 red | 1 | 2 | F1 | **PARTIAL** |
| R6-04 | flynapse-otel | `_model.py:219-254` | `policy_problems` names every widening against `load_policy(merge-base text)` | Hold the repo-local readers (P6) | Every single-file widening named; the merge-base text runs with CURRENT imports, so a split policy (L1) or an env-built one (L2) is blind; post-validation mutation (M1, M2, set fields) not frozen; the shared `ESTATE_FAILURE_FIELDS` mutated in-process (M6) is blind | the same file | yes: MV03, MV04, MV05 and MV08 red | 1 | 1 | F1 | **PARTIAL** (P2-2) |
| R6-05 | flynapse-otel | `_ratchet.py:67-120` | `merge_base_text` takes only `refs/remotes/*`; base == HEAD raises unless opted in; a missing register raises unless `missing_ok` | r5 P2-2 (R1, R2b, R9, R4, MU60, MU61) | Local ref, HEAD, SHA, `@{u}` and a shadowing `origin/main` branch refused; worktree works; shallow fails closed. **At adoption no consumer has a baseline** (new register, nothing pushed, 4 of 6 on `obs-merge` with no upstream), so `missing_ok=True` is the only green path; a moved register forces the same | `test_exception_text_ratchet.py` | yes: MR01–MR03, MR07, MU60 and MU61 red. MR08 (HEAD rev-parse failure) survives | 1 | 2 | F1 | **PARTIAL** (P2-1) |
| R6-06 | flynapse-otel | `_ratchet.py:26-64`; `_model.py:37-60`, `:107-116` | NEW SITE, SITES DROPPED, UN-REPAIRED; a date regex bounded by digits; `reconcile` refuses an unlisted site | r5 P2-2 (R3, dates) | All refused as designed | the same file | yes: MR04, MR05, MR06, MV10 and MV11 red. MV09 (`sites` type check) survives | 1 | 0 | F1 | **SETTLED** |
| R6-07 | flynapse-otel | `_facts.py:391` (`limit=400`) | A site fingerprint is the rule plus the first 400 characters of normalised source | Line-free fingerprint | Two different leaks sharing their first 400 characters share a site (measured); only ISO dates are read (`2099‑12‑31` with U+2011 escapes) | none | no | 3 | 1 | F1 | **OPEN** (P3) |
| R6-08 | flynapse-otel | `_ratchet.py` (whole) | Coordinator attack 1: a `git merge -s ours` that discards a repair | copilot-mro r7 defeated its local ratchet with it | Immune: no history walk. A landed repair un-done by `-s ours` is CAUGHT (C1b); a repair that never reached the base passes, by contract (C1a, C1c) | `ratchet6.py` | I saw it fail on the defeating input (C1b) | 1 | 0 | F1 | **SETTLED** |
| R6-09 | flynapse-otel | `_ratchet.py:110-116` | Coordinator attack 2: register and guard moved with an un-repair | the same | Fails closed at the new path; defeated by `missing_ok=True`; reading the OLD path catches it, but no `moved_from=` exists | none | no | 1 | 1 | F1 | **PARTIAL** (P2-1) |
| R6-10 | flynapse-otel | `_ratchet.py:91-107` | Coordinator attack 3: shallow clones | the same | Fails closed in all six shallow shapes with the base outside the depth; correct at depth 3 | `ratchet6.py` | I saw it fail closed | 1 | 0 | F1 | **SETTLED** |
| R6-11 | flynapse-otel | `tests/fixtures/exception_text/corpus.json` (8014514) | Corpus rows for r5's surviving mutants | r5 P2-1 | 1425 rows; every r5 survivor now dies | the corpus test | yes: MU03–MU06, MB01, MU12–MU14, MU48, MU70, MU60 and MU61 all red; MB01b equivalent at HEAD; MB05 now only widens `returned_text` | 1 | 0 | F1 | **SETTLED** |
| R6-12 | flynapse-otel | `_module.py` (e56005b) and `__init__.py` docstring | Coverage: `type(exc)(…)`, `IfExp`/`BoolOp`/walrus/`partial` doors, route and handler registrars, `headers=`, `add_note`, new levels, LoggerAdapter, `os.fdopen`, `showwarning`, rich `print_exception`; the overclaim withdrawn | r5 P2-3 | Every r5 plant the commit claims is caught; the 14 still missed (including S01, S02, S04 and S08) are pinned `limit` rows. The undeclared miss is `d.setdefault(k, []).append(str(e))` then logging `d` (mro r7 N20; my V04, V05) | corpus | implementer's C1–C21; my mutants did not re-cover these | 2 | 1 | F1 | **PARTIAL** |
| R6-13 | flynapse-otel | `_scan.py:164-200` | Record-field sanction only for a class the scan PROVES a record | r5 C46 | `t: ReadTimeout` is text again | corpus | yes: MP12 red | 2 | 0 | F1 | **SETTLED** |
| R6-14 | flynapse-otel | `withholding.py:218-345`, `:570-745` (65b6eb2) | Continuation up to 8 words; non-web `name:digits@`; matrix params; decode ≤3 passes; scheme-relative userinfo; encoded whole URLs; 6 new markers and 3 exact names | r5 P2-4, utils r5 P3-17 | Of r5's 50, only the declared U12, U15, U27, U36 and U48 leak. 20 NEW residuals (vocabulary `pw`/`pin`/`sid`/`access_code`/`refresh`/`bearer`; quadruple encoding against a "fixed point" docstring; fullwidth separators; JSON `\u0026`-escaped ampersand; path webhooks; more than 8 words) | `test_log_pipe_withholds_url_secrets.py` | yes: MW01–MW15 red and every marker and exact name red (MWM, MWN); **MW01b (8 to 2 words) survives** | 2 | 2 | F1 | **PARTIAL** (P2-3) |
| R6-15 | flynapse-otel | `withholding.py:800-808` | Outside the web schemes, `name:digits` before an `@` is a user and password | U04, U05 | `postgres://db:5432/app?note=a@b` becomes `postgres://b`; `git+ssh://host:22/repo@v1.2` becomes `git+ssh://v1.2`; `?t=…`, `?email…`, `?invit…` are over-withheld. The lost host is inherent to reading a password that holds `/` or `?`, so failing closed is defensible, but it is undeclared | the same file | yes: MW06 red | 3 | 1 | F1 | **OPEN** (P3: declare) |
| R6-16 | flynapse-otel | `withholding.py:570-650` | New anchors (`//…@`, `;name=`, `%3a%2f%2f`) and continuation | r5 P2-4 | Linear, but 2 to 4 µs per character on dense input (1 MB ≈ 3–5 s); r5 shapes 1.4–1.5x; no length cap | `test_…timing` rows (implementer) | not re-mutated | 3 | 1 | F1 | **OPEN** (P3) |
| R6-17 | flynapse-otel | `failure.py` (030785b); `test_failure_parity_with_utils.py` | Port of utils `594327e`: collapsed recursion, partial and suppressed-context quotes, `withheld_extra`/`withheld_quotes`/`withheld_stdlib_message`; `UTILS_PARITY_SHA` pinned in full, compared by `==` | M-FAILURE-HOME | AST-identical to utils `594327e` except one inlined local; futures compared by secret absence (their repr names an address) | the parity test and `test_exception_quotes.py` | yes: MF01–MF10 red | 1 | 0 | F1 | **SETTLED** |
| R6-18 | flynapse-otel | `failure.py:69-104`; `withheld_extra` `:387-441` | No renderer reads a file | M-STACK-HEADERS / B4 | Audit hook on `open` plus linecache spies: zero reads on 4 shapes and 5 extras, including DEBUG-mode asyncio futures and Tasks | `test_failure_fields.py` (r5's MB06 red) | probe only this round | 0 | 1 | F1 | **SETTLED** |
| R6-19 | flynapse-otel | `bootstrap.py:87-100`, `:283` (e478f1c) | Drop the old `http.{server,client}.{request,response}.size` names too | r5 P3 (`http/dup`) | 8 names dropped; pinned by equality | `test_unread_http_body_sizes_are_dropped.py` | yes: MD01 (all four old names removed) and MD02 (one removed) red | 3 | 0 | F3 | **SETTLED** |
| R6-20 | flynapse-otel | `tests/unit/packaging/test_testing_package_isolation.py` (493357d) | Imports read by distribution; relative and computed import targets | r5 P3 (MB02–MB04) | r5's three spellings and five more are each a finding | the isolation file | yes: r5's MB02, MB03 and MB04 red, and my MB04b–MB04f red (`__import__(…, fromlist=…)`, `find_spec` on a computed name, `runpy.run_module`, `pkgutil.resolve_name`, `import pytest` in `testing`) | 3 | 0 | F3 | **SETTLED** |
| R6-21 | flynapse-otel | `_vocabulary.py` (850678b); `_model.py:165-172` | `format_last` removed; every renderer pinned to a real `traceback` attribute | r5 P3 | The pin holds. `_NEVER_READERS` is a hand-kept COPY of the renderer and `sys` names (equal today, not derived, not pinned) | `test_exception_text_scan.py:290-299` | implementer (red with `format_last`) | 3 | 1 | F1 | **PARTIAL** (drifting copy) |
| R6-22 | flynapse-otel | `withholding.py:534-558`, `:654-700` (927a729) | The log boundary reduces a rendered traceback in every string it walks | r5 P3 (B2, B3, B6) | Attribute, dict, list, tuple, key, bytes and nested bodies are fixed. **`_vetted` returns other types as they are**: a `set`/`frozenset` body ships a rendering (B14). loguru's `…catch point marked):` header (B11) ships; it is not reachable via the bridge | `test_log_pipe_withholds_exception_text.py` | yes: MW12, MW13 and ML01 (back to str-only) red; nothing pins unknown container types | 2 | 2 | F1 | **PARTIAL** |
| R6-23 | flynapse-otel | detector (whole) | copilot-mro r7 M-TRACEBACK plants folded in | coordinator | 68 of 75 caught (every family the coordinator named); 7 missed: unseeded `isinstance`/`type is`/`match`/queue narrowing (N01–N04, N18), a `SimpleNamespace` read by `vars()` (N15), and the setdefault chain (N20) | none (not rows) | no | 2 | 1 | F1 | **PARTIAL** |
| R6-24 | flynapse-otel | estate | Re-scan versus `de501a8`: 0 new, 0 missing beyond copilot-mro's 8 over-reports | implementer's claim | Reproduced on r5's six snapshots; utils-obsm `594327e` 119/81 and telegram-bot `cfb1d98` 112/66 (7 under its own policy) identical across `de501a8`, `34c814a` and `927a729` | none | not applicable | 3 | 1 | F1 | **SETTLED** |
| R6-25 | flynapse-otel | all 11 commits | Each commit green at its own HEAD | process | 1874 → 2212 passed, `PYTEST_RC=0`, network guard on | the suite | not applicable | 3 | 1 | F3 | **SETTLED** |

**Tier 0.** Eight rows are settled by guards I watched fail on the defeating input: R6-06, R6-08, R6-10, R6-11, R6-13, R6-17, R6-19 and R6-20. Their properties do not go to Fable.

---

## Open claims, tier 2 first

**Tier 2: open or partial**

1. **R6-02 (P1-2): refusal types matched by tail.** A code-only alias or a same-named class blesses a body echo invisibly to both ratchets. Fix before core adopts: core's refusal type is `Refusal`.
2. **R6-05 and R6-09 (P2-1): no ratchet baseline during adoption in any consumer, and no `moved_from=`.** The plan must say what a guard does with `None`, and which `against` each repo uses.
3. **R6-03 (P1-2 residue): construction validation stops only builtins and stdlib.** Third-party refusal types and readers pass until a baseline exists.
4. **R6-14 (P2-3): URL residuals beyond the declared five.** The 8-word bound is unpinned.
5. **R6-22: `_vetted` fails open on unknown container types.**

**Tier 1: open, partial or refuted**

1. **R6-01 (P1-1):** "proven" is refuted by 21 plants. There is no estate exposure, and a precision-free fix closes 15.
2. **R6-04 (P2-2):** `load_policy` runs the base text with current imports; the policy is not frozen.
3. **R6-12 and R6-23:** the setdefault chain; the unseeded-narrowing and `vars()` reads from mro r7.
4. **R6-07, R6-15, R6-16 and R6-21:** the site-fingerprint bound, non-ISO dates, non-web over-withholding, timing without a cap, and the `_NEVER_READERS` copy.

---

## Appendix: mutation battery (106 mutants of `927a729`)

Apply, grep-confirm, run the named test directories (the detector's under `tests/unit/testing` and `tests/unit/packaging`; URL and boundary under `tests/unit/logging` and `tests/unit/tracing`; failure under `tests/unit/failure` and `tests/unit/logging`; views under `tests/unit/bootstrap`), reverse, md5 against the `927a729` blob. All 106 restores matched. "red" means pytest exited 1 with at least one failing test.

Six survive:
- **MB01b** is equivalent at HEAD: the membership check precedes it.
- **MB05** now only widens `returned_text`, whose sources are already flagged at the def.
- **MP11** affects precision only.
- **MV09**, **MR08** and **MW01b** are unpinned. MW01b matters: the 8-word bound is a privacy rule.

| mutant | what it breaks | result | pytest rc | applied | md5 restored |
|---|---|---|---|---|---|
| MU03 | unknown keyword never lands in `**kw` | red (killed) | 1 | True | True |
| MU04 | extra positional never lands in `*args` | red (killed) | 1 | True | True |
| MU05 | reaches needs ALL proven functions | red (killed) | 1 | True | True |
| MU06 | dstar lands nowhere | red (killed) | 1 | True | True |
| MB01 | generator callees read as returning nothing | red (killed) | 1 | True | True |
| MB01b | generator callees: missing slots read as empty | **survived** | 0 | True | True |
| MB05 | resolution ignores precise (unique tail) | **survived** | 0 | True | True |
| MU12 | isinstance narrowing on any type | red (killed) | 1 | True | True |
| MU13 | handler with ANY refusal type | red (killed) | 1 | True | True |
| MU14 | mutated mapping constant still resolves | red (killed) | 1 | True | True |
| MU48 | NUMERIC +strerror/filename | red (killed) | 1 | True | True |
| MU70 | column: positional dict ignored | red (killed) | 1 | True | True |
| MU60 | ratchet ls-tree failure -> None | red (killed) | 1 | True | True |
| MU61 | ratchet show failure -> None | red (killed) | 1 | True | True |
| MP01 | decorated def accepted in a proof | red (killed) | 1 | True | True |
| MP02 | out-of-scan import skipped | red (killed) | 1 | True | True |
| MP03 | unfollowable binding skipped | red (killed) | 1 | True | True |
| MP04 | self.f: enclosing class need not define f | red (killed) | 1 | True | True |
| MP05 | self.f: a non-def class binding is skipped | red (killed) | 1 | True | True |
| MP06 | _transparent always true | red (killed) | 1 | True | True |
| MP07 | builtin decorators trusted by name | red (killed) | 1 | True | True |
| MP08 | positional-only takes keywords | red (killed) | 1 | True | True |
| MP09 | carried labels dropped | red (killed) | 1 | True | True |
| MP10 | self.f union over this module only | red (killed) | 1 | True | True |
| MP11 | functools.cache not transparent (over-report probe) | **survived** | 0 | True | True |
| MP12 | is_record trusts external classes | red (killed) | 1 | True | True |
| MV01 | builtins allowed as readers | red (killed) | 1 | True | True |
| MV02 | stdlib sources allowed | red (killed) | 1 | True | True |
| MV03 | policy ratchet ignores wider sinks | red (killed) | 1 | True | True |
| MV04 | policy ratchet ignores new sources | red (killed) | 1 | True | True |
| MV05 | policy ratchet ignores fewer seeds | red (killed) | 1 | True | True |
| MV06 | span-safe list ignored | red (killed) | 1 | True | True |
| MV07 | refusal builtins check off | red (killed) | 1 | True | True |
| MV08 | load_policy accepts any object | red (killed) | 1 | True | True |
| MV09 | Accepted.sites type check off | **survived** | 0 | True | True |
| MV10 | reconcile ignores declared sites | red (killed) | 1 | True | True |
| MV11 | site fingerprint includes nothing | red (killed) | 1 | True | True |
| MR01 | local ref accepted as base | red (killed) | 1 | True | True |
| MR02 | base at HEAD passes | red (killed) | 1 | True | True |
| MR03 | missing register reads as None | red (killed) | 1 | True | True |
| MR04 | NEW SITE passes | red (killed) | 1 | True | True |
| MR05 | SITES DROPPED passes | red (killed) | 1 | True | True |
| MR06 | date regex word-boundary | red (killed) | 1 | True | True |
| MR07 | merge-base failure returns None | red (killed) | 1 | True | True |
| MR08 | HEAD rev-parse failure ignored | **survived** | 0 | True | True |
| MW01 | no continuation past a space | red (killed) | 1 | True | True |
| MW01b | continuation 8 -> 2 | **survived** | 0 | True | True |
| MW02 | matrix anchor finder dropped | red (killed) | 1 | True | True |
| MW03 | scheme-relative finder dropped | red (killed) | 1 | True | True |
| MW04 | encoded-URL finder dropped | red (killed) | 1 | True | True |
| MW05 | decode once, not to a fixed point | red (killed) | 1 | True | True |
| MW06 | digits password read as port everywhere | red (killed) | 1 | True | True |
| MW07 | scheme-relative opener dropped from userinfo | red (killed) | 1 | True | True |
| MW08 | encoded run not re-judged decoded | red (killed) | 1 | True | True |
| MW09 | matrix parameters not judged | red (killed) | 1 | True | True |
| MW10 | quick exit ignores ';' | red (killed) | 1 | True | True |
| MW11 | quick exit ignores '%' | red (killed) | 1 | True | True |
| MW12 | attribute strings skip traceback reduction | red (killed) | 1 | True | True |
| MW13 | bytes skip traceback reduction | red (killed) | 1 | True | True |
| MW14 | _OWN_RUN never stops a continuation | red (killed) | 1 | True | True |
| MW15 | nested scheme-relative userinfo in a parameter ignored | red (killed) | 1 | True | True |
| MWM ×20 | each SECRET_PARAMETER_MARKERS entry dropped: amz, goog, sig, credential, token, key, secret, password, passwd, pwd, auth, session, jwt, hmac, ticket, assertion, saml, verifier, invit, email | red (killed), all 20 | 1 | True | True |
| MWN ×4 | each SECRET_PARAMETER_NAMES entry dropped: code, pass, otp, t | red (killed), all 4 | 1 | True | True |
| MF01 | recursion cutoff 3 -> 4 | red (killed) | 1 | True | True |
| MF02 | no first-line partial quote | red (killed) | 1 | True | True |
| MF03 | suppressed __context__ not walked | red (killed) | 1 | True | True |
| MF04 | withheld_extra skips dataclasses | red (killed) | 1 | True | True |
| MF05 | finished futures not read | red (killed) | 1 | True | True |
| MF06 | multi-arg partial quotes dropped | red (killed) | 1 | True | True |
| MF07 | boto Message partial dropped | red (killed) | 1 | True | True |
| MF08 | withheld_quotes cap off | red (killed) | 1 | True | True |
| MF09 | stdlib message ignores exc_info | red (killed) | 1 | True | True |
| MF10 | extra depth 3 -> 1 | red (killed) | 1 | True | True |
| MD01 | old http/dup names not dropped | red (killed) | 1 | True | True |
| MD02 | one old name not dropped | red (killed) | 1 | True | True |
| MB02 | live.py imports a dev-only opentelemetry package | red (killed) | 1 | True | True |
| MB03 | runtime __init__ exposes testing lazily | red (killed) | 1 | True | True |
| MB04 | runtime relative import_module of testing | red (killed) | 1 | True | True |
| MB04b | runtime __import__ with fromlist | red (killed) | 1 | True | True |
| MB04c | runtime importlib.util.find_spec+exec of testing | red (killed) | 1 | True | True |
| MB04d | runtime runpy of testing module | red (killed) | 1 | True | True |
| MB04e | runtime pkgutil.resolve_name of testing | red (killed) | 1 | True | True |
| MB04f | testing imports a third-party dev dep (pytest) | red (killed) | 1 | True | True |
| ML01 | body walked without traceback reduction (old str-only) | red (killed) | 1 | True | True |
