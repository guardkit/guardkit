---
id: TASK-BOOT-F632
title: Dependency-only install as primary strategy for incomplete projects
status: completed
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T12:00:00Z
completed: 2026-02-18T12:00:00Z
priority: critical
tags: [autobuild, environment-bootstrap, greenfield, install-strategy]
task_type: feature
complexity: 5
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-BOOT-F632/
---

# Task: Dependency-only install as primary strategy for incomplete projects

## Description

When a dependency manifest exists but the project source tree is incomplete (greenfield timing gap), the bootstrap attempts a full project install that fails. Dependencies needed by later waves are never installed.

This is NOT a "fallback" — it should be the **primary strategy** for incomplete projects. The detection logic is: does the declared source directory exist? If not, install declared dependencies individually instead of attempting a full project install.

See: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3) — Finding 2 (F2) and Recommendation 2 (R2).

## Context

Evidence from FEAT-BA28:
```
ValueError: Unable to determine which files to ship inside the wheel
The most likely cause is that there is no directory that matches the name
of your project (fastapi_health_app).
```

Wave 1 creates `pyproject.toml` with `name = "fastapi_health_app"` but the `fastapi_health_app/` package directory doesn't exist until later waves. The bootstrap runs `pip install -e .` which fails because the build system can't find the source directory.

**Co-dependency with R1**: For TASK-DB-003 tests to actually execute and pass, both R1 (TASK-BOOT-B032: Docker/infrastructure path) and R2 (this task: dependency installation) are required. R1 without R2 still results in `ModuleNotFoundError`. R2 without R1 still has no Docker infrastructure.

## Acceptance Criteria

- [x] `DetectedManifest` gains `is_project_complete() -> bool` method
- [x] `DetectedManifest` gains `get_dependency_install_commands() -> Optional[List[List[str]]]` method
- [x] `EnvironmentBootstrapper` checks `is_project_complete()` BEFORE attempting install
- [x] Incomplete projects use `get_dependency_install_commands()` instead of full install
- [x] Complete projects continue to use `install_command` (editable or standard) as today
- [x] Per-stack `is_project_complete()` implementations for all supported stacks
- [x] Per-stack `get_dependency_install_commands()` implementations for applicable stacks
- [x] Unit tests for detection logic per stack
- [x] Unit tests for dependency parsing per stack
- [x] Integration test: greenfield project with incomplete source tree installs dependencies

## Implementation

### Files Modified

| File | Changes |
|------|---------|
| `guardkit/orchestrator/environment_bootstrap.py` | Added `is_project_complete()`, `get_dependency_install_commands()`, and 4 private helpers to `DetectedManifest`; added `_run_single_command()` to `EnvironmentBootstrapper`; updated `bootstrap()` with detection-first logic |
| `tests/unit/test_environment_bootstrap.py` | Added 35 new tests across 3 classes (TestDetectedManifestIsProjectComplete, TestDetectedManifestGetDependencyInstallCommands, TestEnvironmentBootstrapperIncompleteProject) |

### Quality Results

- Tests: **89 passed, 0 failed**
- Coverage: **93%** on `environment_bootstrap.py` (threshold: ≥85%)
- New tests added: **35**

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
