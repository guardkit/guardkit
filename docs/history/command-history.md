# Command History

Master chronological log of GuardKit slash-command invocations.
Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /task-complete TASK-ABFIX-010 — 2026-06-24T16:58:21Z

### Prompt

```
/task-complete TASK-ABFIX-010
```

### Assistant response

Executing `/task-complete TASK-ABFIX-010`. Pre-completion validation first — let me confirm the acceptance criteria status against what landed.

All in-scope ACs are met. Marking them complete (W3/W4 explicitly deferred, L3 scoped-out per operator decision):

Now the completion state transition — frontmatter to `completed` and move the folder:

Task moved to `completed`; no feature/epic rollup (standalone task). Now the Graphiti knowledge capture (the learning flywheel). Loading the MCP tool:

Writing the task outcome and the architectural decision to Graphiti:

Task outcome queued in the correct group (no override — Step 2a is a no-op). Now the architectural decision:

Both episodes queued in the correct groups (no group override — Step 2a no-op). Final step — commit the completion state:

There's an unexpected unstaged modification to the completed task file right after committing. Let me inspect it before doing anything — I didn't make further edits, so this could be a parallel session touching the shared tree.

I see what happened: commit `5d4f5b0d` recorded a **pure rename** (`0 insertions, 0 deletions`) — it captured the stale `in_review`/unticked content at the new path, leaving my frontmatter+AC edits unstaged. The working tree has the correct final content (`status: completed`, ACs ticked). I'll commit the content fix as a follow-up (not amend — a parallel session may have built on that commit per the shared-index caveat).


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


---

## /task-complete TASK-ABFIX-011 — 2026-06-24T22:32:50Z

### Prompt

```
/task-complete TASK-ABFIX-011 then commit
```

### Assistant response

Running `/task-complete` for TASK-ABFIX-011, then committing. First, let me validate completion state, check the `completed/` convention this repo uses, and check for any pre-staged files from parallel sessions (per my commit-hygiene note).

The convention is clear: sibling tasks use `tasks/completed/TASK-ABFIX-NNN/` subfolders directly (not `YYYY-MM`). The only staged file is my own earlier `git mv`. Let me confirm the parent ABFIX-010's layout to mirror it exactly.

Mirroring the parent's layout. Let me update the task frontmatter to completed state:

Now move the task to `completed/` (mirroring the parent's layout):

Task moved to completed. Now the Graphiti knowledge-capture step (non-blocking). Let me load the MCP write tool.

Now write the task outcome and the key architectural decision to Graphiti (non-blocking):

Write 1 confirmed in the correct group (no override). Now the architectural decision:

Both Graphiti writes succeeded in the correct groups. Now the commit. Per my commit-hygiene notes, let me first verify the current staging state and HEAD (both can shift mid-session), then stage only my files with explicit pathspecs.

Clean state — HEAD steady, no parallel-session pollution, only my files plus untracked noise (`.claude/hooks/.state/`, `docs/history/`) to exclude. Let me stage exactly my files with explicit pathspecs and verify the staged set.

The non-existent `backlog/` pathspec aborted the whole `git add` (the rename's delete-side is already captured as `R100`). Let me re-run without it.

Staged set is exactly my 7 files (task `.md` now `R064` due to the completion summary I added); the untracked noise stays excluded. Let me write a commit message and commit to main.


---

## /task-work TASK-ABFIX-012 — 2026-06-24T22:36:32Z

### Prompt

```
/task-work TASK-ABFIX-012
```

### Assistant response

I'll start by reading the task file to understand what TASK-ABFIX-012 requires.

This is a complex (complexity-7) fix in the Coach validation logic — exactly the kind of subtle false-green/false-red territory the entire `.claude/rules/` corpus warns about. Getting it wrong re-introduces a regression. I need to deeply understand the actual code before touching anything.

Let me read the key code surfaces in parallel.

Now the core file. Let me read the cited regions of `coach_validator.py` in parallel — the classifier, the infra patterns, the classifier call site, and the parallel amnesty.

Let me read the classifier itself, its call site, and the parallel amnesty region in parallel.

The line numbers in the task have drifted. Let me locate the actual symbols precisely with grep, in parallel.

Now let me read the actual classifier definition, the `IndependentTestResult` dataclass, and the `signal_absent` decision points in `run_independent_tests`.

I now understand the classifier. Two critical things to nail down before designing: (1) there appear to be **two** decision paths (`validate()` and a primary `gather_evidence` path), and (2) how the ABFIX-010 `signal_absent`/`None` channel actually routes. Let me scope these precisely.

Both paths resolve `task_type`/`profile`, but `_classify_test_failure` is only called in `validate()` (line 2112). I need to understand how the **primary** `gather_evidence` path handles test failures and the absent signal. Let me read it.

`gather_evidence` builds an evidence bundle but does **not** classify — classification must happen in its consumer. The pivotal question is which path is live in production and where the test-failure classification + absent-routing happens for it. This determines where I edit. Let me trace the callers.

The live path is `gather_evidence` → `CoachEvidenceBundle` → consumed in `agent_invoker.py` by deterministic guards + the LLM Coach. The classifier (`_classify_test_failure`) is **not** applied in this path. I must understand the deterministic guards that gate on `independent_tests` before framing the work. Let me read the guard region and the bundle override.

I now have a deep architectural picture. This is a genuinely cross-module, safety-critical change:

- **Live path** is `gather_evidence` → `CoachEvidenceBundle` → deterministic guards in `agent_invoker` (`_reconcile_absent_independent_test_signal`, `_apply_runtime_parity_guard`) + LLM Coach. The `_classify_test_failure` / parallel-amnesty logic the task cites lives in the **legacy** `validate()` path, which is **not** the live decision path.
- A genuine independent CODE failure (`tests_passed=False, signal_absent=False`) currently has **no deterministic blocking guard** in the live path — it relies on the LLM Coach, which is exactly what false-approved FMDR-004.

Given ultracode and the complexity, I'll run a comprehensive parallel **Understand+Design** workflow to map the remaining unknowns exactly and adversarially check the design against the rule corpus before I touch code. Let me update my todos and launch it.

Now the comprehensive Understand+Design workflow — parallel deep-readers mapping exact edit sites, then an adversarial synthesis that cross-checks the design against the rule corpus.

The parse error is from a stray character in a long template-literal prompt. Let me write the workflow to a file cleanly (easier to iterate) and run it via `scriptPath`.

Workflow is running in the background (5 parallel readers + adversarial design synthesis). While it works, let me handle the task state transition that the workflow doesn't touch — moving TASK-ABFIX-012 to `in_progress` and updating its frontmatter.


---

## /task-complete TASK-ABFIX-012 — 2026-06-25T05:01:42Z

### Prompt

```
/task-complete TASK-ABFIX-012 then commit
```

### Assistant response

The user explicitly authorized completion + commit. Executing `/task-complete`. First: pre-completion validation already passed (ACs ✅, 578/0 tests ✅, adversarial review CLOSED ✅). Now file organization → Graphiti capture → git commit.

Let me move the task to `completed` and load the Graphiti write tool in parallel:

Index is clean (only my task file). Let me update the completed task's frontmatter and write the Graphiti knowledge episodes in parallel:

Now the Graphiti knowledge capture — task outcome + the design-rule decision (both episodes in parallel):

Both episodes queued to the correct groups (no override — Step 2a no-op). Now the commit. Let me stage exactly my files with explicit pathspecs and verify the staged set before committing:

The `git add` aborted on the non-existent `tasks/backlog/...` path (already moved away), so my source/test files didn't stage. Let me re-stage only existing paths:

Staged set is exactly correct — only ABFIX-012 files; the unrelated `.claude/hooks/.state/` and `docs/history/` are left untouched. Committing to `main` (your established workflow):

Done. `/task-complete TASK-ABFIX-012 then commit` executed end-to-end.


---

## /feature-plan guardkit-memory-harvest-publisher-walk-guardkit-s-knowledge- — 2026-06-25T14:24:10Z

### Prompt

```
/feature-plan "Guardkit memory harvest publisher: walk guardkit's knowledge artifacts and publish each
as a canonical MemoryEpisodeV1 onto the NATS MEMORY stream via nats_core.NATSClient.publish_episode().
project_id='guardkit'; episode_type per source (adr / feature_outcome / review_report / document);
content_format markdown|text for prose docs (the relay chunks + embeds them), json for structured
payloads. episode_id is a DETERMINISTIC hash of the artifact's natural key so re-harvest is idempotent
(JetStream dedupes on Nats-Msg-Id=episode_id). Connect as the dedicated 'guardkit' NATS user (already
provisioned; password in nats-infrastructure/.env GUARDKIT_NATS_PASSWORD) which has publish rights on
memory.episode.> (the fleet-memory user is consumer-only and cannot publish). Idempotent + resumable:
safe to run repeatedly. Tests: subject resolves to
memory.episode.guardkit.{episode_type}; episode_id stable across runs; >900KB body rejected with an
actionable error; dry-run mode lists what would publish without connecting." --context docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md
```

### Assistant response

I'll start by reading the context brief and checking for any existing related tasks/features, since the recent git history shows substantial memory-publisher work already.

Brief is comprehensive and no prior feature/tasks exist. Before planning, I need to ground the plan in guardkit's actual structure (the feature-plan classification guide warns hard against invented paths). Let me explore the real doc taxonomy, CLI structure, and the sibling-repo references.

Key findings: guardkit has a Click/argparse CLI in `guardkit/cli/` (subcommands registered via `main.py`), and **`nats_core` is NOT installed in guardkit's env — it's sibling repo `../nats-core`**. That dependency wiring is a real planning concern. Let me verify the CLI registration pattern and the actual `nats_core` contract (the brief is human-written and could drift from code).

Contract confirmed against real code. Let me look at the reference publisher impl and the `publish_episode` body (the 900KB guard + subject resolution) so the plan mirrors what exists.

Let me check how guardkit is expected to pull in `nats-core` (there's a comment near line 105) — the dependency wiring is the main integration risk.

I now have solid grounding. Key facts confirmed against real code:
- **CLI**: Click-based, subcommands in `guardkit/cli/` registered in `main.py` via `cli.add_command()`.
- **`nats_core` contract** (verified): `NATSConfig(url, user, password: SecretStr, name)` → `connect()` / `publish_episode(episode)` / `disconnect()`; `publish_episode` resolves `memory.episode.{project_id}.{episode_type}`, sets `Nats-Msg-Id` header, raises `ValueError` if >900KB.
- **Idempotency pattern to mirror**: `fleet-memory`'s `_derive_episode_id` = `f"ep-{sha256(natural_key).hex()[:16]}"`.
- **Dependency wiring**: `nats-core` is **not installed** — it's sibling `../nats-core` (pkg `nats-core` v0.4.0); guardkit pulls siblings via `[tool.uv.sources]` editable paths (the guardkitfactory pattern).
- **Doc taxonomy is large** (50+ `docs/*` dirs) — the brief itself says "confirm against the real doc taxonomy."

A few genuine scoping decisions will materially change the plan. Let me confirm them before generating tasks.

All four answered with the recommended options: curated config-driven scope, new `guardkit memory` group, skip+report for oversized, and an `operator_handoff` task for the live GB10 run.

Let me check the generation tooling and existing file conventions so the artifacts I produce match this repo.

The bin script accepts `--feature-id` (so I can fix IDs upfront) and the repo's task frontmatter uses `depends_on:` + `parent_review`/`feature_id`/`wave`. Let me do one final grounding check — confirm the curated harvest dirs actually contain content — then build the plan.

Critical confirmation: **oversized docs exist today** — 8+ docs over 880KB (two `reseed_guardkit_*.md` files exceed 2MB). So the skip+report path fires on the very first run; it's a real, testable case, not hypothetical. 456 curated docs total (331 in `docs/reviews`).

I have everything needed. Let me build the feature plan. Setting up tracking and creating the folder:

Now creating the task files (7 tasks + a planning record):

Now the 7 task files:

Now the IMPLEMENTATION-GUIDE.md (with the mandatory Mermaid diagrams + §4 Integration Contracts) and README.md:

All 10 artifacts created. Now generating the structured `FEAT-HARV.yaml` for AutoBuild (`--discover` resolves task file paths from disk):

The YAML generated cleanly (AC-quality review: 0 unverifiable). The script's dependency-derived waves put TASK-HARV-006 and 007 both in Wave 4 (both depend only on 005). But logically the live GB10 run (007) should follow the acceptance suite (006) being green — let me make that an explicit edge so the wave ordering is correct, then regenerate.

Feature validates: `✓ Feature FEAT-HARV is valid`. Let me confirm the final wave structure and task_type frontmatter are all correct:

Final structure is correct and the feature validates. Waves: `1:[001,002] → 2:[003,004] → 3:[005] → 4:[006] → 5:[007]`, all `task_type`s set.

One real pre-build risk I want to harden against: `nats_core` is currently **not importable** in the active env, and a Player that merely edits `pyproject.toml` won't materialise the editable install — so Wave 2's `import nats_core` could fail at test collection. Let me make that install step explicit in TASK-HARV-001:


---

## /task-work TASK-FIX-RELAYBATCH01 — 2026-06-26T15:52:33Z

### Prompt

```
/task-work TASK-FIX-RELAYBATCH01
```

### Assistant response

I'll start by locating the task file for TASK-FIX-RELAYBATCH01.

The task file doesn't exist. Let me search more broadly to confirm.

The task file doesn't exist yet, but `RELAYBATCH` is referenced in TASK-HARV-007. Let me look at that context.

This is important context. TASK-FIX-RELAYBATCH01 is referenced in TASK-HARV-007 as a **blocking fix filed in `fleet-memory/tasks/backlog/`** — a *different* repository, not guardkit. The fix is in the **fleet-memory relay** (the NATS→pgvector write path), not in guardkit's code. Let me verify the repo layout before doing anything.

There's a `fleet-memory` repo at `~/Projects/appmilla_github/fleet-memory`. The task belongs there, not in guardkit. Let me check it.

The task lives in the **fleet-memory** repo, not guardkit. This matters: `/task-work` does stack detection, file creation, and test execution against the current working directory. Running it from guardkit would misdetect the stack and create files in the wrong repo. Let me read the task and check fleet-memory's project setup before recommending the path.

I now fully understand: this is a real, well-specified bug fix, but it lives in the **fleet-memory** repo and the code to fix is `fleet-memory/src/fleet_memory/embed.py`. Running guardkit's `/task-work` machinery from the guardkit cwd would misdetect the stack and write files into the wrong repo. Let me check fleet-memory's setup and the actual code before recommending how to proceed.

fleet-memory is itself a guardkit-initialized project (its own `.claude/settings.json`, `tasks/`, Python stack). The task and the code (`src/fleet_memory/embed.py`) both live there. Let me read the actual code so my recommendation is grounded, then I'll confirm how you want to proceed.

I have what I need. The situation is clear and I want to confirm direction before acting, because it determines where work happens.

**What's going on:** `TASK-FIX-RELAYBATCH01` is **not a guardkit task**. It lives in the sibling repo `~/Projects/appmilla_github/fleet-memory` (which is itself a guardkit-initialized project with its own `.claude/`, agents, Python stack, and `tasks/` workflow). The bug and its fix are in [fleet-memory `src/fleet_memory/embed.py`](../fleet-memory/src/fleet_memory/embed.py) — `embed()` sends every chunk in one `/v1/embeddings` request, so multi-chunk episodes blow past the embed `n_ctx` (2048) and 400. The fix is to sub-batch by a token budget ≤ n_ctx.

`/task-work` is working-directory-sensitive (stack detection, file creation, test runs all target the cwd). I'm running in the **guardkit** session, so the guardkit agents and Python-stack detection here would target the wrong repo. I shouldn't drive guardkit's task-work machinery against fleet-memory's code.

Let me grab the call site + token-budget settings so the options are concrete, then confirm with you.

I now have the full scope. The fix is small and crisp: make `embed()` sub-batch by an estimated-token budget ≤ n_ctx instead of sending all chunks in one request (plus a settings knob, a single-oversized-chunk guard, and a unit test). The only real question is **where/how** to run it, since the task is in fleet-memory and I'm in the guardkit session.


---

## /feature-plan FEAT-MEM-08 — 2026-06-28T19:58:11Z

### Prompt

```
/feature-plan FEAT-MEM-08 --context docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md
```

### Assistant response

I'll start by reading the feature brief to understand the scope of FEAT-MEM-08.

This is a substantial cutover feature with a comprehensive brief. Before I orchestrate the plan, I must verify the live integration points actually exist in the codebase (the brief lists specific paths, and inventing paths is the #1 `/feature-plan` defect class). Let me map the real surface.

All brief paths exist on disk, and `fleet_memory_client.py` correctly does not yet exist. Now let me map the actual call-site shapes and the fleet-memory contract before designing tasks. I'll fan out parallel exploration.

Both sibling repos exist with the fleet-memory contract present. Now I'll fan out three parallel Explore agents to map the precise call-site shapes — this drives correct task design.

I now have a complete, verified map of both repos. Let me confirm one contract detail that determines a key design fork — whether fleet-memory's typed payloads reject extra fields (this decides how task-outcome's `lessons`/`approach`/`task_id` are carried).

Key contract detail confirmed: fleet-memory's `BasePayload` uses `extra="ignore"` — so extra fields on `build_outcome` (task_id/lessons/approach) are **silently dropped**, not stored or embedded. That makes the typed-payload field gap a real design fork that also determines whether this feature touches the sibling `fleet-memory` repo.

I have a fully verified map of both repos (write call-sites, GROI read call-sites, the fleet-memory MCP/NATS contract, the `query_logger` evidence hook, and the 9 project + 20 system `group_id` definitions in `_group_defs.py`). The brief already settles most decisions; two genuine forks remain that change the task breakdown, so I'll confirm those before generating the plan.

Both forks resolved:
1. **Extend `build_outcome` (cross-repo)** — W1 includes a fleet-memory-repo task adding optional `task_id`/`lessons`/`approach`; the feature declares `fleet-memory` as an `evidence_repos`.
2. **Split code vs. proof** — each wave splits autobuild code+tests from `operator_handoff` live-proof tasks (soak audit, "prove a real run reads", cutover sign-off).

Let me check the planning tooling available on this box before generating the structure.

All tooling is present: `generate-feature-yaml` supports `--feature-id`/`--feature-slug`/`--discover`, `guardkit feature validate` exists, and FEAT-MEM-08 is unfiled with no conflicting tasks. I'll use the real feature ID `FEAT-MEM-08` and slug `memory-cutover`.

The brief is itself the completed decision analysis and the user supplied a fully-specified feature, so I'll record the decision in a review task for provenance and proceed straight to generating the structure (10 tasks, 8 waves, with the two resolved forks baked in). Let me create the review task and the feature folder.

Now the 10 task files. Starting with W1 — the mapping table (the core design driver, produced first) and the adapter + cross-repo payload extension.

W2 — the dual-write repoint (consumes both the adapter and the extended payload) plus the operator-gated soak audit.

W3 — the GROI reads wiring plus the acceptance-gate operator task ("prove a real run reads").

W4 — CLI commands, the config/docs flip, and the final operator cutover sign-off.

All 10 task files are written. Now the IMPLEMENTATION-GUIDE.md with the mandatory Mermaid diagrams (data flow, integration-contract sequence, task-dependency graph) and the §4 Integration Contracts section.

All 10 task files, the guide, and the README are written. Now generate the structured YAML with the real feature ID `FEAT-MEM-08`, slug `memory-cutover`, and `--discover` to resolve `file_path` from the files on disk.

The YAML is generated with 8 waves. Two follow-ups before validation: (1) the AC linter found **0 unverifiable criteria**; (2) the R3 smoke-gate nudge fired — correctly, I will **not** inject smoke gates because the test paths don't exist yet (they're created by this feature), which would violate the path-verification rule. Let me inspect the YAML, then add the cross-repo `evidence_repos` declaration for TASK-MEM08-003.

The YAML is well-formed (`task_type`/`consumer_context` correctly live in the task-file frontmatter, read by FeatureLoader). Before adding the cross-repo `evidence_repos` declaration, let me confirm FeatureLoader actually supports that key — adding an unknown key would fail schema validation.

`evidence_repos` is an officially supported feature-level field. Let me check the exact format used by FEAT-HARV (the harvest feature, same fleet-memory/nats neighborhood) and mirror it.

`evidence_repos` is a plain path list. Since TASK-MEM08-002/004 import `nats_core`/`fleet_memory` in the worktree venv, let me check guardkit's pyproject extras + `[tool.uv.sources]` so I declare `bootstrap_extras` correctly (this is exactly the uv-sources gotcha from [[env-bootstrap-uvsources-gotcha]]).

Critical bootstrap finding: **fleet-memory is NOT in guardkit's pyproject** (no extra, no `[tool.uv.sources]`), but `nats-core` IS (the `memory` extra → editable `../nats-core`). Per the brief, guardkit talks to fleet-memory via `nats_core.publish_episode` (writes) + the MCP tools (reads/writes) — it should **not** `import fleet_memory`. So `bootstrap_extras: [dev, memory]` (gets nats-core) is the right declaration, and I must steer the adapter task away from a direct `fleet_memory` import. Let me wire both into the YAML and harden TASK-MEM08-002.

Now align the guide's wave table with the canonical computed waves (008 lands in Wave 6 alongside the 007 gate since it only depends on 006) and add the no-`fleet_memory`-import note to the risks.

Now run the pre-flight validation on the feature YAML (Step 8.5).

Validation passes (`✓ Feature FEAT-MEM-08 is valid`) — task_types, file paths, dependencies, and intra-wave conflicts all clean. Final inventory check:


---

## /task-review install-sh-backup-existing-moves-the-whole-claude-dir-should — 2026-07-09T05:38:36Z

### Prompt

```
/task-review "install.sh backup_existing moves the whole ~/.claude dir — should it exclude Claude Code state?" --mode=decision --depth=quick
```

### Assistant response

I'll execute this decision review. First, Phase 0 (ad-hoc task creation) and locating the actual code in parallel.

`guardkit task` isn't a subcommand. Let me check the CLI and read the actual code.

The concern is confirmed: `backup_existing()` does `mv "$HOME/.claude"` — it **moves the entire directory**, not a copy. Let me check `INSTALL_DIR`, the call site, and the more surgical backup logic that also exists (lines 1677–1689).
