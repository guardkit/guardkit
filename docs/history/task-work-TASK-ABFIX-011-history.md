# /task-work — TASK-ABFIX-011 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /task-work TASK-ABFIX-011 — 2026-06-24T21:38:44Z

### Prompt

```
/task-work TASK-ABFIX-011
```

### Assistant response

I'll start by locating and loading the task file for TASK-ABFIX-011.

Found it in `backlog`. Let me read the task file and check what else is in the task directory.

This is the deferred W3 of TASK-ABFIX-010 — a complexity-6 fix touching the Coach's isolated pytest execution path. It's tightly bound to the `absence-of-failure` / `absence-must-survive-every-reconciliation-layer` rule family I have loaded, and to `stack-plugin-architecture.md`. Before planning, I need to ground myself in the actual code surfaces. Let me verify the cited line numbers and map the territory in parallel.

Line numbers are close. Let me read the four key regions of `coach_validator.py` plus the environment bootstrap hook. Reading in parallel.

Let me read the remaining three coach_validator regions and the bootstrap hook in parallel.

Now I have all three injection sites and the classifier clearly mapped. The task's table labels were slightly swapped (`:4084` is the *isolated* path, `:4328` is the *standard* path), but the actual structure is now precise:

- **SDK**: `_pin_pytest_command` (3993) builds a string `<py> -m pytest …`
- **Isolated/parallel** (4087): `cmd = [interp, "-m", "pytest"] + parts[1:]`
- **Standard subprocess** (4328): identical argv shape
- **Classifier**: the Python `elif not tests_passed:` branch (4392–4428) — must learn returncode-4 / `unrecognized arguments`

The three injection sites share a near-identical shape → strong signal for one shared helper. Let me gather the supporting symbols and read the bootstrap hook before planning.

Now the bootstrap hook — option (a) for dependency handling. Let me read the `python_extras` install path.

The bootstrap's `python_extras` only installs *project-declared* extras, so it can't inject an arbitrary helper generically — confirming **option (b) probe-and-inject** as the robust, self-contained path (the task explicitly offers "(a) … or (b)"). Let me confirm guardkit's own packaging, whether `pytest-timeout` is currently resolvable, and the existing test patterns for these paths.

Key findings: `pytest_timeout` is importable in *this* dev env but declared in *no* manifest — confirming availability is environment-dependent and the **probe** must be load-bearing. And guardkit's `dev` extra already "dogfoods" `pytest-bdd` — the same pattern lets me add `pytest-timeout` there so guardkit self-builds actually get the benefit (the "(a)" half), while the probe gates everything (the "(b)" half).

Let me find existing tests for these paths and the stack-classifier contract.

Let me set up task tracking, then read the two most relevant existing test files to match their patterns.

The classifier test is a clean template. Now let me read the subprocess-path test to see how command construction is asserted (critical for testing injection).

Excellent — the test patterns are clear (mock `subprocess.run`, assert on `mock_run.call_args` command list). I now have everything to design precisely. But one decision is load-bearing for an AC and rests on pytest-timeout's actual behavior: **does `--timeout-method=signal` let the session continue (others run) while `thread` hard-kills it?** The AC "named FAILED + others run" depends on this. Let me verify empirically rather than from memory, and check two safety facts in the same batch.

Decisive result, exactly as reasoned:
- **`signal`**: `.F.` → `1 failed, 2 passed` with `FAILED test_hang.py::test_b_hangs` — the hung test is named-FAILED **and the others run**. This is precisely what the AC requires.
- **`thread`**: dumps tracebacks and hard-kills the session (no pass summary; cwd was reset = `os._exit`). Others never report.

So `signal` is the correct default. Now two safety facts before I finalize the plan.

Both safety facts confirmed:
- **Gate-freeze**: window `2026-05-11 → 2026-05-17` (inclusive) — **37 days expired** (today 2026-06-24). The "ACTIVE" label is a stale snapshot; by its own dates the freeze is lifted. My change is additive/gated/fail-safe anyway.
- **pytest config**: `addopts` has **no global `timeout`** setting → adding `pytest-timeout` to dev deps is fully inert until my gated `--timeout` injection passes it. Safe.

Two last verifications before I finalize: confirm `_detect_test_command` (which sets `_active_stack_profile`) runs before dispatch, and confirm there's no *other* pytest-command construction site (constraint 4).

Confirmed: `_detect_test_command` (sets `_active_stack_profile`) runs at 4194, before all three dispatch sites. Now the final constraint-4 audit — enumerate every pytest-command construction site in the file.

Three pytest-argv construction sites confirmed (4007 SDK string, 4087 isolated, 4328 standard). Let me verify the other `subprocess.run` sites are not pytest-test-execution paths I'd be missing (3089, the evidence-repo runner at 3330, and 4903).

Audit complete. The other `subprocess.run` sites are confirmed **out of scope**: `3089` is the smoke/runtime-parity check (arbitrary entry point, not pytest), `3344` is the evidence-repo runner (sibling-repo declared command, any stack), `4903` is AC-command verification. Exactly **three pytest construction sites** + the classifier, matching the task's "four surfaces."

I now have complete grounding. Let me set up tracking and write the plan.

Now the implementation plan (Phase 2).

Now transition the task to in_progress.

**Phase 2.5 — architectural self-review** against the loaded rules:

- **SOLID/DRY**: one `_pytest_timeout_argv()` consumed at 3 sites + one `_is_pytest_timeout_usage_error()` at 2 classifier sites — directly defends the family's recurring "Nth-injection-site drift" lesson.
- **stack-plugin-architecture.md**: Python-only arg gated by `_active_stack_profile is None`; non-Python `classify_absent_for_stack` branch untouched. ✓
- **absence-of-failure / absence-must-survive**: usage-error → `signal_absent=True` (absent, composes with ABFIX-010 `None`); narrow match can't mask a genuine exit-1 failure. ✓
- **Fail toward feedback**: probe error → no inject; plugin-vanished → absent. ✓

One sharp implementation risk surfaced in review: a subprocess probe sharing the global `subprocess.run` mock would perturb existing tests (double-count / `assert_called_once`). Resolution — **probe in-process via `find_spec` when the pinned interpreter == `sys.executable` (the unit-test fixture case), subprocess-probe only when a real venv differs** (production). That's both more correct and collision-free. Let me confirm no existing test asserts exact-equality/length on these commands before I rely on it.

The exact-equality assertions are only on **non-pytest** commands (`npm test`, `dotnet test`) — the shell branch I never inject into. And `test_coach_parallel_isolation.py:251`'s `mock_run.assert_called_once()` is safe because my in-process probe (no subprocess when `interp == sys.executable`, the no-venv fixture case) doesn't consume the mock. Design confirmed collision-free. One broad sweep to be certain there's no surprise exact-assert elsewhere:

All exact-equality assertions are `uv`/`docker`/`pip` bootstrap commands — none on the coach pytest path. Design is fully validated and collision-free. Phase 2.5 complete.

Let me check the import header (I need `importlib.util` and confirm `sys`/`subprocess`/`os` are imported) before writing the helpers.

`importlib` isn't imported (I'll use a method-local import, matching the file's lazy-import idiom). Let me see the spot just after imports for the module constant.

I'll add the module constant after the logger definition.

Phase 3a — add the constructor cache field, then the helper methods. First the cache:

Now the helper block — inserted after `_pytest_env`, before `_run_isolated_tests`:

Phase 3b — inject `_pytest_timeout_argv()` at all three sites. First the SDK string path (`_pin_pytest_command`):

Now the isolated/parallel-wave site (disambiguated by `cwd=str(tmpdir_path)`):

Now the standard subprocess site (disambiguated by `cwd=str(self.worktree_path)`):

Phase 3c — extend the absent classifier. First the **standard** path (add `timeout_usage_error` to the absent triggers):

Now the **isolated** path — add the same usage-error classification (it currently has no absent classifier on the run path):

Phase 3d — add `pytest-timeout` to guardkit's `dev` and `all` extras (the dogfood half, mirroring the existing pytest-bdd pattern). First `dev`:

Now I'll add `pytest-timeout` to both `dev` and `all`:

All Phase 3 edits done. Let me verify the module imports cleanly before writing tests.

Now Phase 4 — the test file. I'll cover every AC: gating, the probe (both interpreter cases), all three injection sites, the classifier on both subprocess paths, and real-execution tests (hung single-wave, hung parallel-wave, asyncio-not-interrupted).

Now run the new test file (disabling the default `--cov` addopts for speed):

Module-level import helper was wrong. Let me fix it with a clean `importlib.util` import:

All 39 pass, including the real hung-test (single + parallel-wave) and asyncio cases. Phase 4.5 — run the touched existing suites to confirm no regression (locally the in-process probe returns True, so injection actually fires in these — the real test of my collision analysis):

No regressions — 93 passed, 1 pre-existing quarantine skip, 1 pre-existing warning. My collision analysis held in practice. Let me run a broader regression net across the coach/quality-gates surface plus the main validator suite.

A real regression surfaced — and it's instructive: `test_subprocess_argv_pins_interpreter` uses a **real venv** (`/tmp/.../venv/bin/python` ≠ `sys.executable`), so the probe ran and injection correctly fired, but the test asserts **exact** argv equality via `assert_called_once_with`/`call(...)` — a pattern my earlier `assert cmd ==` grep missed. Let me read it and find any siblings using the same assertion style.

This is for `CoachVerifier` (which I didn't touch) — the failing one is a different class, `TestCoachValidatorInterpreter`. The actual call had a mocked `subprocess.run` + a real venv path, so the **subprocess-probe** branch consumed the mock (returncode 0 → "available" → injected). Let me find that exact test.

Now it's clear. Only `test_subprocess_argv_pins_interpreter` breaks: it mocks `subprocess.run` **and** sets a real venv path, so the subprocess-probe branch consumes the mock (rc 0 → "available" → injects + extra call). The sibling `test_sdk_command_pins_interpreter` (no mock) passes because the real probe against a `touch`ed fake venv fails → no injection. The broad 474-test run confirms this is the **only** collision.

This test's concern is interpreter-pinning, not timeout. The minimal, intent-preserving fix is to disable injection within it (set the cache False), with a comment tying it to this task:

Let me re-run the failing test plus the full broad sweep to confirm green.

514 passed, 6 pre-existing skips, 2 pre-existing warnings. Let me cast the widest net — run **every** test file that references `CoachValidator`/`run_independent_tests` to catch any remaining probe/injection collision I haven't exercised yet.

The grep caught a non-`.py` fixture. Let me filter to actual test files and re-run.

9 failures, all in one file: `test_coach_sdk_stream_resilience.py`. I touched the SDK path (`_pin_pytest_command`), so I must determine if these are mine or pre-existing. Let me see the failure detail and check against a clean tree.

This failure is `LangGraphHarnessError: ... model=None: "Could not resolve authentication method"` — a guardkitfactory/LangGraph-harness auth failure, nothing to do with `--timeout` (the test doesn't reference `_pin_pytest_command`). This is exactly the hazard from my memory note: *harness-touching tests fail locally because guardkitfactory is installed and the LangGraph path needs auth*. Let me prove it's pre-existing by stashing my changes and running the same file.

Confirmed pre-existing: the same 9 fail on the clean tree (my coach changes stashed). They're the documented LangGraph-harness auth hazard from my memory note, unrelated to this task. Let me verify my changes restored intact after the stash pop.

All changes intact. The 9 failures are definitively pre-existing (LangGraph-harness auth, my documented memory hazard) — my subprocess-mode tests never touch the harness. Let me run my new tests under the **real** addopts (coverage config, as CI does) for parity, and capture coverage of the changed code.

File-level 14% is expected (the file is 2229 statements; my scoped tests touch only the timeout paths — unrelated methods have their own suites). What matters is that **my new code** is covered. Let me verify precisely by locating my new method line numbers and cross-checking against the coverage "missing" set.

My helper block (4068–4205) sits entirely in the coverage gap between missing-ranges `4034` and `4243` → **fully covered**. Let me confirm the remaining injection/classifier sites (4276, 4309, 4545, 4641) aren't in the missing set:

**All new code lines covered.** Phase 4/4.5 complete with no regressions (the 9 LangGraph failures proven pre-existing). Let me update tracking and do the Phase 5 self-review by reading the final state of the key changed regions.

The helper block reads cleanly — real logic, DRY, fail-safe, well-documented. One important packaging check before finalizing: if there's a `uv.lock`, adding a dependency without updating it could break `uv sync --frozen`. Let me verify.

Two key findings: (1) there **is** a `uv.lock`, but (2) CI `tests.yml` installs via `pip install -e ".[dev]"` (reads pyproject directly, no lock) — and line 71 **already** `pip install`s `pytest-timeout` ad-hoc. So my dev-extra addition just *declares* what CI already installs. But a stale `uv.lock` could break any `uv sync --frozen` path (including worktree bootstrap). Let me regenerate the lock properly.

`uv` 0.11.8 is available, and CI line 71 installs `pytest-timeout` for hang-protection — so my dev-extra declaration aligns with existing intent. Let me regenerate the lock so no `uv sync --frozen` path breaks.

`uv lock` added `pytest-timeout v2.4.0` (mine) **plus** `tree-sitter` + `tree-sitter-language-pack` (not mine). That signals the lock was *already* stale vs pyproject before my change. I need to understand this before including unrelated lock churn in my diff. Let me investigate.

The lock was **already stale** before my change (missing `tree-sitter`, a transitive dep of guardkitfactory's wiring analysis — confirmed by the project's own rules referencing it). `uv lock` synced that pre-existing staleness alongside adding my `pytest-timeout`. CI uses pip (not the lock), so this only matters for `uv sync --frozen` paths — and keeping the lock consistent is the correct state. Let me confirm the lock is now up-to-date:

Lock is consistent (`uv lock --check` exit 0); CI is pip-based so this only helps local/bootstrap `uv` paths. Everything is green and correct. Now Phase 5 finalization — mark the ACs complete and add a completion record to the task file.

Now transition the task to `in_review` (all quality gates passed) and update the frontmatter:

Final consolidated green-state confirmation across all my changes plus the regression-sensitive files:

All green — 115 passed, 1 pre-existing skip, 1 pre-existing warning. Final state is exactly as planned.
