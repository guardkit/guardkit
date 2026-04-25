# AutoBuild Execution Protocol (Slim)

> Condensed protocol for local backends. Keeps quality gates, removes verbose guidance.

---

## Pre-Phase 3: Infrastructure

If task frontmatter has `requires_infrastructure`, start declared services:
- PostgreSQL: `docker run -d --name guardkit-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine`
- Redis: `docker run -d --name guardkit-test-redis -p 6380:6379 redis:7-alpine`
- MongoDB: `docker run -d --name guardkit-test-mongo -p 27018:27017 mongo:7`

Cleanup after tests: `docker rm -f guardkit-test-pg guardkit-test-redis guardkit-test-mongo 2>/dev/null || true`

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

## Phase 4: Testing

Compile first:
- Python: `python -m py_compile <file.py>`
- TypeScript: `npx tsc --noEmit`
- .NET: `dotnet build --no-restore`

Run tests:
- Python: `pytest tests/ -v --cov=src --cov-report=term --cov-report=json`
- TypeScript: `npm test -- --coverage`
- .NET: `dotnet test --collect:"XPlat Code Coverage" --logger:"json"`

Quality gates: Compilation 100%, Tests 100%, Line coverage ≥80%, Branch coverage ≥75%.

Report format (parsed programmatically):
```
N tests passed
N tests failed
Coverage: N.N%
```

---

## Phase 4.5: Fix Loop

Max 3 attempts. Fix implementation, NOT tests. Do NOT skip/comment out/ignore tests.

Loop: analyze failure → fix code → recompile → retest → check results.
If all pass: proceed to Phase 5. If attempt > 3: report BLOCKED with diagnostics.

---

## Phase 5: Code Review

Check: unused imports, missing error handling, hardcoded secrets, SOLID/DRY/YAGNI compliance.
Run linter if available (Python: `ruff check .`, TypeScript: `npm run lint`).

Output: `Quality gates: PASSED` or `Quality gates: FAILED`

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

---

## Output Markers

Use these exact formats (parsed programmatically):
- `Phase N: Description` (e.g., `Phase 3: Implementation`)
- `✓ Phase N complete`
- `N tests passed` / `N tests failed`
- `Coverage: N.N%`
- `Quality gates: PASSED` / `Quality gates: FAILED`
- `Architectural Score: N/100`
