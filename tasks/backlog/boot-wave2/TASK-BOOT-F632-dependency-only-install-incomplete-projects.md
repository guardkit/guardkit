---
id: TASK-BOOT-F632
title: Dependency-only install as primary strategy for incomplete projects
status: backlog
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: critical
tags: [autobuild, environment-bootstrap, greenfield, install-strategy]
task_type: feature
complexity: 5
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: []
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

- [ ] `DetectedManifest` gains `is_project_complete() -> bool` method
- [ ] `DetectedManifest` gains `get_dependency_install_commands() -> Optional[List[List[str]]]` method
- [ ] `EnvironmentBootstrapper` checks `is_project_complete()` BEFORE attempting install
- [ ] Incomplete projects use `get_dependency_install_commands()` instead of full install
- [ ] Complete projects continue to use `install_command` (editable or standard) as today
- [ ] Per-stack `is_project_complete()` implementations for all supported stacks
- [ ] Per-stack `get_dependency_install_commands()` implementations for applicable stacks
- [ ] Unit tests for detection logic per stack
- [ ] Unit tests for dependency parsing per stack
- [ ] Integration test: greenfield project with incomplete source tree installs dependencies

## Implementation Notes

### Detection-first approach (NOT try-fail-fallback)

```
EnvironmentBootstrapper.bootstrap():
  for manifest in manifests:
      if manifest.is_project_complete():
          run install_command (existing logic)
      else:
          dep_commands = manifest.get_dependency_install_commands()
          if dep_commands:
              run each dep_command
          else:
              log warning: "Incomplete project, no dependency install available"
```

### Per-stack is_project_complete() implementations

```
Python (pyproject.toml):
    Parse project name from [project].name
    Check if matching directory exists OR src/ layout exists
    Return True if source directory found

Node (package.json):
    Check if main/module entry point file exists
    Return True if entry point found

.NET (*.csproj):
    Always return True (dotnet restore doesn't need source)

Go (go.mod):
    Always return True (go mod download doesn't need source)

Rust (Cargo.toml):
    Check if src/ directory exists
    Return True if found

Flutter (pubspec.yaml):
    Check if lib/ directory exists
    Return True if found
```

### Per-stack get_dependency_install_commands()

```
Python (pyproject.toml):
    Parse [project.dependencies] using tomllib (stdlib 3.11+)
    Return [sys.executable, "-m", "pip", "install", dep] for each dependency
    Note: Use simple parsing — extract package names and version pins,
    skip complex specifiers. This needs to install sqlalchemy, asyncpg, etc.

Node (package.json):
    Parse dependencies object
    Return ["npm", "install", dep] for each dependency

.NET: Return [["dotnet", "restore"]] (always works without source)
Go: Return [["go", "mod", "download"]] (always works without source)
Rust: Return [["cargo", "fetch"]] (always works without source)
Flutter: Return [["flutter", "pub", "get"]] (always works without source)
```

### Parsing complexity note

Parsing dependency specifiers from `pyproject.toml` is non-trivial (version constraints, extras, optional dependencies). Use the simplest possible parser:
- `tomllib` reads TOML (stdlib in 3.11+, `tomli` backport for 3.10)
- `[project.dependencies]` is a list of PEP 508 strings
- For v1: split on `>=`, `<=`, `==`, `~=`, `!=`, `[` to extract package name
- Install with `pip install "dep_string"` (pass the full PEP 508 string to pip, let pip handle version resolution)

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/environment_bootstrap.py` | Add `is_project_complete()`, `get_dependency_install_commands()` to `DetectedManifest`; update `EnvironmentBootstrapper.bootstrap()` |
| `tests/unit/test_environment_bootstrap.py` | Add tests for detection and dependency install logic |

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
