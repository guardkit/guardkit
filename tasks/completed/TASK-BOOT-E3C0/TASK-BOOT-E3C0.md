---
id: TASK-BOOT-E3C0
title: Add ProjectEnvironmentDetector and bootstrap phase to feature orchestrator
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17T00:00:00Z
completed_location: tasks/completed/TASK-BOOT-E3C0/
priority: critical
tags: [autobuild, environment-bootstrap, feature-orchestrator, root-cause-fix]
task_type: feature
complexity: 6
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: 98
  last_run: 2026-02-17T00:00:00Z
  tests_passed: 55
  tests_total: 55
  regressions: 0
organized_files:
  - TASK-BOOT-E3C0.md
---

# Task: Add ProjectEnvironmentDetector and bootstrap phase to feature orchestrator

## Description

**This is the root cause fix for TASK-DB-003 stalling.** AutoBuild's `_setup_phase()` creates a worktree but never installs the target project's dependencies. This task adds a `ProjectEnvironmentDetector` that scans the worktree for dependency manifests and runs the appropriate install commands.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — Finding 0 and R1.

## Context

The actual error from FEAT-BA28's TASK-DB-003:
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

The `pyproject.toml` exists in the worktree (created by Wave 1's Player), but nobody ever runs `pip install -e .` before Wave 2's Coach tries to run pytest.

## Acceptance Criteria

- [x] New module `guardkit/orchestrator/environment_bootstrap.py` with `ProjectEnvironmentDetector` class
- [x] Detector scans worktree root for dependency manifests (lock files first, then manifest files)
- [x] Supported stacks (minimum for v1):
  - Python: `poetry.lock` → `poetry install`, `pyproject.toml` → `pip install -e ".[dev,test]"` or `pip install -e .`, `requirements.txt` → `pip install -r requirements.txt`
  - Node: `pnpm-lock.yaml` → `pnpm install`, `yarn.lock` → `yarn install`, `package-lock.json`/`package.json` → `npm install`
  - .NET: `*.csproj`/`*.sln` → `dotnet restore`
  - Go: `go.mod` → `go mod download`
  - Rust: `Cargo.toml` → `cargo build` (or `cargo check`)
  - Flutter: `pubspec.yaml` → `flutter pub get`
- [x] `_bootstrap_environment()` method added to `FeatureOrchestrator` (called in `_setup_phase()` after worktree creation — Phase 1.5)
- [x] `_already_bootstrapped()` check prevents redundant installs via manifest content hash tracking in `.guardkit/bootstrap_state.json`
- [x] Bootstrap is synchronous (must complete before agents run)
- [x] Failed bootstrap logs warning but does NOT block execution (Player may handle it)
- [x] Monorepo support: scans worktree root AND depth-1 subdirectories
- [x] Unit tests for detector (mock filesystem with various manifest combinations)
- [x] Unit tests for bootstrap state tracking (hash-based dedup)
- [x] Existing tests continue to pass

## Open Design Decision: Virtual Environment Policy

**Status**: Resolved — v1 installs into the current Python (no venv creation). See TASK-REV-4D57 review report, Scope Question 5 for risks and alternatives.

## Known Limitation: Monorepo Depth

Depth-1 scanning will NOT detect manifests in deeper structures like `packages/backend/api/pyproject.toml`. This is acceptable for v1 and documented in the module's docstring.

## Key Files

- `guardkit/orchestrator/environment_bootstrap.py` — NEW: detector and bootstrap logic
- `guardkit/orchestrator/feature_orchestrator.py` — `_setup_phase()` integration (Phase 1.5)
- `guardkit/orchestrator/__init__.py` — Updated exports
- `tests/unit/test_environment_bootstrap.py` — NEW: 55 unit tests

## Implementation Notes

```python
# Proposed API
class ProjectEnvironmentDetector:
    """Detect project dependencies and install commands."""

    def __init__(self, worktree_path: Path, scan_depth: int = 1):
        self.worktree_path = worktree_path
        self.scan_depth = scan_depth

    def detect(self) -> List[Tuple[str, Path, List[str]]]:
        """Return list of (stack, manifest_path, install_cmd)."""
        ...

class EnvironmentBootstrapper:
    """Bootstrap project dependencies in a worktree."""

    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path
        self._state_file = worktree_path / ".guardkit" / "bootstrap_state.json"

    def bootstrap(self) -> BootstrapResult:
        """Detect and install dependencies. Idempotent."""
        ...

    def _already_bootstrapped(self, manifest: Path) -> bool:
        """Check if manifest was already processed (content hash match)."""
        ...
```
