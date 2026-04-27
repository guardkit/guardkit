# Review Report: TASK-ABSR-7890 — Player↔Coach Test Divergence on TASK-J004-004

- **Task**: TASK-ABSR-7890 (review-only, diagnostic)
- **Parent**: TASK-REV-FA04 §F7, §R6 (Wave 1 follow-up)
- **Feature**: FEAT-ABSR-9C6E (autobuild stall resilience)
- **Date**: 2026-04-27
- **Worktree analysed**: `jarvis/.guardkit/worktrees/FEAT-J004-702C/`

---

## Executive Summary

The divergence is **real, mechanical, and explained by interpreter selection**. Same four test files, same 125-test set, opposite verdicts:

| Side  | Wrapper                          | Resolved Python                         | `import jarvis` | Result                |
|-------|----------------------------------|-----------------------------------------|-----------------|-----------------------|
| Player | `uv run pytest …`                | uv-managed venv (jarvis pin `<3.13,>=3.12`) | succeeds        | `125 passed`          |
| Coach  | `[sys.executable, "-m", "pytest"]` (subprocess path) **or** bare `pytest` (SDK path) | `/usr/local/bin/python3` = Framework 3.14 | fails           | `1 failed, 124 passed` |

The single failing test is `tests/test_phase2_dependencies.py::TestPhase1ImportSurfaceStillWorks::test_jarvis_package_imports`, which spawns `subprocess.run([sys.executable, "-c", "import jarvis"])` (test_phase2_dependencies.py:402-403). Because the test inherits `sys.executable` from the pytest process, **the same source code passes or fails depending on which interpreter pytest itself runs under** — exactly the broken-bootstrap path identified in TASK-REV-FA04 §F0/§F1/§F2.

This **confirms hypothesis 1** ("real environmental divergence — different interpreters") from §F7 and **rejects hypotheses 2 and 3** ("Player ran a subset" / "partial-load cache"). The 125-vs-(124+1) arithmetic shows Player ran the full set; the failure mechanism is a fresh-subprocess `import` so caching is irrelevant.

**Architectural rationale**: the divergence is *expected by design at the wrapper layer* (Coach uses orchestrator `sys.executable` for trust-but-verify; Player runs project tests via the project's own conventions, which for jarvis means `uv run`) but *unintended at the outcome layer* (Player gates passing should mean tests would also pass under Coach). This is the asymmetry §F7 flagged.

**Implication for TASK-ABSR-2468 (R3 — Coach env-class conditional approval)**: R3's premise is that "all four Player gates passing" is a meaningful signal of correctness. This investigation shows that on a broken-bootstrap project that uses uv, **Player gates can pass purely because uv silently bypassed the bootstrap** — the gates measured a different environment than the one Coach later validated. R3 must therefore not unconditionally trust Player gates; it needs an additional precondition (broken-bootstrap detected ∧ project does not use uv, or equivalent).

---

## Findings

### F1. Player and Coach ran the same test command at the file-set level

Coach's command is recorded verbatim in three turns:

```
pytest tests/test_config_settings.py tests/test_phase2_dependencies.py tests/test_phase4_dependencies.py tests/test_routing_history_schema_smoke.py -v --tb=short
```

(`coach_turn_1.json:15`, `coach_turn_2.json:15`, `coach_turn_3.json:15` — identical across all three turns).

Coach's result line is `1 failed, 124 passed, 2 warnings in 3.29s` (turn 1), `3.24s` (turn 2), `3.49s` (turn 3) — **125 collected, 1 failed**.

Player's report claims `tests_passed_count: 125` (`player_turn_1.json:80`-equivalent for each turn, and `task_work_results.json:14` recording `tests_passed: 125, tests_failed: 0`). `task_work_results.json:104` confirms `tests_written: []` — **Player wrote no new tests**, so the 125 collected on Player's side must equal the 125 collected on Coach's side. Player's `test_output_summary` is empty across all three turns (`player_turn_1.json:80`, `player_turn_2.json:88`, `player_turn_3.json:91`), so the raw output from Player's run is not preserved in the artefacts — Player's claim is structured (`tests_passed_count: 125`) but not transcript-backed.

**Conclusion**: both sides ran the same 125-test set. The `124 + 1 = 125` arithmetic rules out "Player skipped the failing test" (hypothesis 2 of §F7).

### F2. The failing test inherits the pytest interpreter

`tests/test_phase2_dependencies.py:400-410`:

```python
def test_jarvis_package_imports(self) -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import jarvis; print(jarvis.__version__)"],
        ...
    )
    assert result.returncode == 0, (
        f"`import jarvis` regressed under the Phase 2 pins.\n"
        ...
    )
```

The test spawns a Python subprocess using `sys.executable` — the very interpreter pytest itself is running under. There is no environment indirection (no PATH lookup, no shell). The pass/fail of this test is therefore a direct function of *which interpreter ran pytest*.

In a properly-installed project, `[that-python, "-c", "import jarvis"]` succeeds. On the broken-bootstrap worktree (where `pip install -e .` failed because `jarvis` requires Python `<3.13,>=3.12` and `sys.executable` is 3.14), it fails immediately with `ModuleNotFoundError`. The empty traceback Coach reported (`File "<string>", line 1, in <module>` with no follow-on lines beyond the ModuleNotFoundError) matches a clean subprocess `python -c "import jarvis"` failing on a missing package.

### F3. Coach's interpreter is Framework Python 3.14 — confirmed

The autobuild history captures Coach's interpreter consistency diagnostic (added by TASK-REV-CB30 R7) at three points (turns 1, 2, 3 of TASK-J004-004), each line identical:

> `INFO:guardkit.orchestrator.quality_gates.coach_validator:Test execution environment: sys.executable=/usr/local/bin/python3, which pytest=/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest, coach_test_execution=sdk`

(`docs/history/autobuild-FEAT-J004-702C-history.md:362, 649, 777, 905`)

So:

- **`sys.executable` = `/usr/local/bin/python3`** — the orchestrator's Python, which on this Mac is the Framework 3.14 install (per parent review §F10).
- **`which pytest` = `…/3.14/bin/pytest`** — the pytest binary on PATH is the Framework 3.14 one.
- **`coach_test_execution=sdk`** — Coach selected the SDK path (running pytest via Claude Code's Bash tool).

The history shows Coach logging two messages back-to-back per turn:

```
INFO:…:Running independent tests via SDK (environment parity): pytest tests/…
INFO:…:Running independent tests via subprocess: pytest tests/…
```

(`autobuild-FEAT-J004-702C-history.md:651/658, 779/786, 907/914`)

Both messages name the same `pytest tests/…` command. The SDK invocation goes through the Claude Code CLI's Bash tool (which resolves `pytest` from PATH = `/…/3.14/bin/pytest`), and the subprocess invocation goes through `coach_validator.py:1704` which builds `[sys.executable, "-m", "pytest"] + parts[1:]` (= `[/usr/local/bin/python3, "-m", "pytest", …]` = also Framework 3.14). **Both paths converge on Python 3.14**, neither of which can `import jarvis` because of the broken bootstrap.

### F4. Player's interpreter is the uv-managed venv — strong inferential evidence

The Player turn JSONs do not preserve a raw shell transcript, so I cannot quote the exact Bash invocation. The evidence is inferential, but mutually reinforcing:

1. **All eight `completion_promises` in `player_turn_1/2/3.json` and `task_work_results.json:140-220` reference `uv run` for every executable check**:
   - AC-001/AC-002/AC-003/AC-004/AC-005/AC-006: "both pass under `uv run pytest tests/test_routing_history_schema_smoke.py` (10/10 passing)" / "both pass under `uv run pytest`"
   - AC-007: "Re-ran `uv run python -m mypy src/jarvis/infrastructure/routing_history.py`"
   - AC-008: "Re-ran in turn 3: `uv run python -m ruff check …` returns 'All checks passed!' and `uv run python -m ruff format --check …` returns '2 files already formatted'"
2. **Jarvis is a uv-managed project** — `uv.lock` is in the `files_modified` list (`task_work_results.json:99`) and `pyproject.toml` declares `requires-python = ">=3.12,<3.13"` (per parent review §F1).
3. **The arithmetic only closes if Player's `import jarvis` succeeded**. Player's structured count is 125 passed, no failures. The Coach-confirmed 125-test set contains exactly one test (`test_jarvis_package_imports`) whose pass/fail depends on whether `jarvis` is installed in the running interpreter. Therefore Player's interpreter had `jarvis` installed.
4. **`uv run` is the only mechanism on this worktree that produces such an interpreter**. `uv run pytest` reads `pyproject.toml`, resolves a Python in `[>=3.12, <3.13)`, materialises a `.venv` if needed, runs `pip install -e .` against that venv, and execs pytest with that venv's Python on `sys.executable`. The orchestrator never gives Player a working venv (per parent review §F2 — `BootstrapResult.venv_python = None` because the `requires-python` mismatch path doesn't enter `_ensure_venv`), so any working interpreter Player used must have been bootstrapped *by Player itself*. `uv run` is the wrapper that does that.

**Conclusion**: Player ran `uv run pytest tests/test_config_settings.py tests/test_phase2_dependencies.py tests/test_phase4_dependencies.py tests/test_routing_history_schema_smoke.py` (or equivalent), uv installed jarvis into a `<3.13` venv, the test's `sys.executable` resolved to that venv's Python, `import jarvis` succeeded, all 125 tests passed.

This is **hypothesis 1 of §F7 confirmed**: real environmental divergence — different interpreters, via different wrappers.

### F5. `test_jarvis_package_imports` was run by Player

Hypothesis 2 of §F7 ("Player's tests don't include `test_jarvis_package_imports`") is **rejected**. The 125 count requires running all four files — `test_phase2_dependencies.py` is one of them — and that file contains `test_jarvis_package_imports` (verified at `tests/test_phase2_dependencies.py:376-411`). pytest would have collected it under any default invocation.

Hypothesis 3 of §F7 ("partial-load cache") is **rejected**. The test always spawns a fresh `subprocess.run([sys.executable, "-c", "import jarvis"])`. Each invocation is a brand-new Python process, so import caching is impossible. The pass/fail is purely a function of "is jarvis installed in this Python's site-packages".

### F6. Architectural intent vs unintended consequence

**Intent at the wrapper layer is sound**. There are good reasons each side runs tests its own way:

- **Coach uses `[sys.executable, "-m", "pytest"]`** (forced subprocess path is used unconditionally for `requires_infra` and custom-API-base tasks; the SDK path is otherwise allowed for parity, but ends up at the same Framework 3.14 here). Using `sys.executable` is the trust-but-verify contract: Coach asserts results in *the same Python the orchestrator runs under*, so that "Coach approved" implies "GuardKit-installed-self-tests would also pass". This is the behaviour TASK-REV-CB30 R5 added (`coach_validator.py:1839-1849`: "The subprocess path uses sys.executable, bypassing PATH entirely").
- **Player runs the project's tests via the project's conventions** because the SDK Player uses `task-work --implement-only`, which executes via Claude Code's Bash tool. The Player has every incentive (and instruction) to follow the project's tooling — `uv run pytest` for a uv-managed jarvis is the right command from the project's perspective.

**Unintended consequence**: when the project pins a Python the orchestrator's `sys.executable` doesn't satisfy, Player's wrapper (uv) silently provisions a different working interpreter, while Coach's `sys.executable` continues to inherit the broken one. Player and Coach are now testing in different worlds, and the discrepancy is invisible from inside either side's output — only the orchestrator can see both. This is the gap §F7 surfaced.

### F7. Player gates are *systematically* more permissive when uv hides a broken bootstrap

The asymmetry is not a one-off accident; it is the structural consequence of the wrapper choice:

| Project pins `requires-python` satisfied by `sys.executable`? | Project uses uv? | Player passes? | Coach passes? | Aligned? |
|---|---|---|---|---|
| Yes | n/a | yes | yes | ✓ |
| No | yes | yes (uv bootstraps a satisfying interpreter) | no (sys.executable still 3.14) | ✗ Asymmetric |
| No | no | no (Player can't bootstrap; tests fail too) | no | ✓ (both fail) |

The asymmetric row is exactly the J004-004 case. Forge/study-tutor/agentic-dataset-factory/specialist-agent (per parent review §F9) all sit in the top row (pins `>=3.11` or `>=3.12` with no upper bound — Framework 3.14 satisfies them all), so this divergence has not been observable on those projects.

### F8. Coach does record the diagnostic, but the issue classification masks the root cause

Coach correctly identified the failure as `failure_classification: "infrastructure"` and `failure_confidence: "ambiguous"` (`coach_turn_1.json:43-44`) and emitted a `must_fix` issue. The remediation text Coach wrote (`coach_turn_1.json:41`) however suggests *application-level* fixes ("Add mock fixtures for external services", "Use SQLite for test database", "Mark integration tests with @pytest.mark.integration"). None of those address the actual root cause (broken bootstrap → wrong interpreter), and none would help — there is no external service involved; the failure is a local `import jarvis` in a Python that doesn't have `jarvis` installed. This is consistent with the parent review's §F3 finding that Coach has no conditional-approval branch for `infrastructure/ambiguous` + all-Player-gates-passed, and no specific remediation text for the broken-bootstrap class.

This is **out of scope for TASK-ABSR-7890** but is restated here because it tightens the narrative for TASK-ABSR-2468.

---

## Verification of Acceptance Criteria

| AC | Status | Evidence |
|----|--------|----------|
| Read player_turn_*.json and task_work_results.json | ✓ | F1, F4, F5 |
| Identify Player's pytest command vs Coach's | ✓ | F1, F4 (Player: `uv run pytest …`; Coach: `pytest …` resolving to Framework 3.14) |
| Identify Python interpreter used by Player vs Coach | ✓ | F3 (Coach = Framework 3.14 via `sys.executable`), F4 (Player = uv-managed `<3.13` venv) |
| Determine whether `test_jarvis_package_imports` was run by Player | ✓ | F5 (yes, run; passed because uv venv had `jarvis` installed) |
| Document findings in `.claude/reviews/TASK-ABSR-7890-report.md` | ✓ | This file |
| Document architectural rationale if real divergence | ✓ | F6 (intent sound at wrapper layer; consequence unintended at outcome layer) |
| File follow-up task if Player gates systematically more permissive | ✓ | See Recommendations R6.1, R6.2 below |

---

## Recommendations

These are scoping notes for follow-up tasks, not implementation. The investigation is review-only.

### R6.1 — Strengthen TASK-ABSR-2468's preconditions

TASK-ABSR-2468 (R3 — Coach env-class conditional approval) should add a precondition to its "trust Player gates" branch: **don't trust Player gates if the project might use a different interpreter than Coach**. Concrete signals:

- Project root contains `uv.lock` or `poetry.lock` or `Pipfile.lock` *and* `pyproject.toml`'s `requires-python` does not include `sys.version_info[:2]`.
- `BootstrapResult` recorded a `requires-python` mismatch (post-R7 alignment of Jarvis pins, or post-R5 interpreter-discovery work).

In those cases R3 must NOT use Player-gates-passing as a corroborating signal — Coach should rely on its own independent test run (which is what already happens; R3's only proposed escape hatch must not weaken it).

**Suggested action**: amend TASK-ABSR-2468's acceptance criteria to require this precondition before R3 ships. Cross-link to this report as the supporting evidence.

### R6.2 — Optional: expose the wrapper choice in Player turn artefacts

Player's `task_work_results.json` does not record *how* it ran tests (no shell transcript, no command captured). The Player evidence text mentions `uv run` repeatedly, but the structured fields are empty (`test_output_summary: ""`). This investigation would have been a 60-second confirmation if `task_work_results.json` carried a `test_command_actually_run: "uv run pytest …"` field.

**Suggested action**: file a separate, low-priority TASK to capture the Player's actual test invocation in `task_work_results.json` (or `player_turn_N.json`). This is *not* required for FEAT-ABSR-9C6E to ship — TASK-ABSR-2468's precondition is the load-bearing change.

### R6.3 — Confirm that R7 (Jarvis pin alignment) closes the divergence

Once parent-review §R7 lands (Jarvis aligned to `>=3.11` to match the LangChain-DeepAgents portfolio), the asymmetric row in F7 disappears for jarvis. This investigation should be revisited if a *new* sibling project chooses to keep tight `requires-python` pins; the meta-rule remains: **wrappers that bootstrap their own interpreter (uv, poetry, hatch) can mask broken-bootstrap state from any verification step that uses `sys.executable`**.

**Suggested action**: add a one-line note to the autobuild-stall-resilience IMPLEMENTATION-GUIDE.md tying R6.1 to R7's completion ("R6.1 precondition becomes load-bearing only when a sibling project re-introduces tight Python pins; once R7 lands, the immediate trigger for J004-004 is removed but the precondition remains valuable as defence-in-depth").

---

## Out-of-Scope (per task brief)

- Implementing any of R6.1/R6.2/R6.3 — those are separate follow-up tasks (or amendments to existing ones).
- Reviewing other features' Player↔Coach divergence patterns — this was a single-incident investigation per the task scope.
- Re-checking TASK-ABSR-2468's design beyond the precondition note in R6.1 — that task has its own design pass.

---

## Provenance

- **Failing-run worktree** (preserved): `jarvis/.guardkit/worktrees/FEAT-J004-702C/`
- **Autobuild artefacts**: `jarvis/.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-004/`
  - `task_work_results.json` (Player's structured report — 125 passed, all gates green)
  - `player_turn_1.json`, `player_turn_2.json`, `player_turn_3.json` (no raw transcript; structured promises only)
  - `coach_turn_1.json`, `coach_turn_2.json`, `coach_turn_3.json` (1 failed / 124 passed verbatim across all three turns)
  - `turn_state_turn_1.json`, `turn_state_turn_2.json`, `turn_state_turn_3.json` (Coach feedback echo)
- **Autobuild log**: `jarvis/docs/history/autobuild-FEAT-J004-702C-history.md`
  - Lines 362, 649, 777, 905: Coach interpreter diagnostic (`sys.executable=/usr/local/bin/python3`, `which pytest=…/3.14/bin/pytest`, `coach_test_execution=sdk`)
  - Lines 651/658, 779/786, 907/914: Coach SDK-then-subprocess invocation logs
  - Lines 275, 299, 305, 311, 525, 609, 652, 703, 726, 732, 780, 831, 855, 859, 908: Player's `claude_agent_sdk` bundled CLI at `/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude`
- **Failing test source**: `jarvis/.guardkit/worktrees/FEAT-J004-702C/tests/test_phase2_dependencies.py:376-411` (`TestPhase1ImportSurfaceStillWorks::test_jarvis_package_imports`)
- **Coach pytest invocation site**: `guardkit/orchestrator/quality_gates/coach_validator.py:1702-1712` (subprocess path uses `[sys.executable, "-m", "pytest"]`); diagnostic at `1791-1800`
- **Parent review**: `guardkit/.claude/reviews/TASK-REV-FA04-report.md` §F0/F1/F2/F7/R6, §F9 (sibling project pins), §F10 (GuardKit-self runs from 3.14 venv)
