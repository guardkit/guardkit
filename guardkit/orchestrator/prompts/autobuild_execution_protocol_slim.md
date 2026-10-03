# AutoBuild Execution Protocol (Slim)

> Condensed protocol for local backends. Keeps quality gates, removes verbose guidance.

---

## Pre-Phase 3: Infrastructure

If task frontmatter has `requires_infrastructure`, start declared services:
{infrastructure_recipes_brief}

Cleanup after tests: `{infrastructure_cleanup}`

Skip if `requires_infrastructure` is absent.

---

## Phase 3: Implementation

1. Read the implementation plan from `.claude/task-plans/{task_id}-implementation-plan.md`
2. Implement all files listed in the plan
3. Follow detected stack conventions (type hints, strict mode, async patterns)
4. Create production-quality code with error handling
5. Do NOT create stubs (no `pass`, `raise NotImplementedError`, `return {}`, or TODO-only bodies)

File count constraints: minimal/standard = max 2 files, comprehensive = unlimited.

Modes: Standard = implement + test together. TDD = RED → GREEN → REFACTOR.

---

## Phases 4 and 5: Owned by the AutoBuildOrchestrator

Phases 4 (test execution) and 5 (code review) are executed by the AutoBuildOrchestrator after your Phase 3 completes. You do not need to invoke `test-orchestrator` or `code-reviewer` directly. Focus your turn on Phases 1, 2, 3, and (optionally) Phase 4.5 (test-fix loop) for your own feedback.

---

## Phase 4.5: Fix Loop

Run tests inline (e.g., `pytest`, `npm test`, `dotnet test`) for your own feedback — do not invoke `test-orchestrator`. Max 3 attempts. Fix implementation, NOT tests. Do NOT skip/comment out/ignore tests.

Loop: run tests inline → analyze failure → fix code → re-run tests inline → check results.
If all pass: finish your turn. If attempt > 3: report BLOCKED with diagnostics.

---

## Phase 5.5: Plan Audit

Compare actual vs planned: files, dependencies, LOC variance.
- LOW: <10% variance, no extra files
- MEDIUM: 10-30% variance, 1-2 extra files
- HIGH: >30% variance, 3+ extra files

Skip if no plan exists.

---

## Player Report

Write JSON to: `{worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json`

CRITICAL: `completion_promises` MUST have one entry per acceptance criterion. Empty array causes stalling.

```json
{
  "completion_promises": [
    {
      "criterion_id": "AC-001",
      "criterion_text": "Full text of acceptance criterion",
      "status": "complete",
      "evidence": "What you did to satisfy this criterion",
      "test_file": "tests/test_feature.py",
      "implementation_files": ["src/feature.py"]
    }
  ],
  "task_id": "TASK-XXX",
  "turn": 1,
  "files_modified": [],
  "files_created": [],
  "tests_written": [],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "Brief summary",
  "implementation_notes": "What and why",
  "concerns": [],
  "requirements_addressed": [],
  "requirements_remaining": []
}
```

Status values: "complete", "incomplete", "uncertain". Self-check: one entry per AC, no empty evidence.

**CRITICAL: `files_modified` / `files_created` MUST list only paths YOU wrote or edited this session.** Do NOT populate from `git status --porcelain` or directory sweeps — in parallel-wave runs the worktree may contain sibling tasks' in-flight writes, and the honesty auditor flags claims for paths you did not author as fabrications. Exclude orchestrator-managed paths (`.guardkit/`, `.claude/task-plans/`).

---

## Output Markers

Use these exact formats (parsed programmatically):
- `Phase N: Description` (e.g., `Phase 3: Implementation`)
- `✓ Phase N complete`
- `N tests passed` / `N tests failed`
- `Coverage: N.N%`
- `Quality gates: PASSED` / `Quality gates: FAILED`
- `Architectural Score: N/100`
