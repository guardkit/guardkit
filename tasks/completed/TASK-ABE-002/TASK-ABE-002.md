---
id: TASK-ABE-002
title: Add project-aware pre-Coach lint auto-fix step to autobuild orchestrator
status: completed
created: 2026-03-10T12:00:00Z
updated: 2026-03-10T16:30:00Z
completed: 2026-03-10T16:30:00Z
completed_location: tasks/completed/TASK-ABE-002/
previous_state: in_review
priority: high
tags: [autobuild, quality-gates, efficiency, stack-agnostic, orchestrator]
complexity: 5
task_type: feature
parent_review: TASK-REV-8D32
feature_id: FEAT-ABE
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add project-aware pre-Coach lint auto-fix step to autobuild orchestrator

## Description

Add an automatic lint/format fix step in the autobuild orchestrator between Player completion and Coach invocation. This step reads the project's own configuration files to discover which lint/format tools are configured, and runs only those tools. If the project has not configured any lint tool, the step is skipped entirely.

**Core principle: never assume what tools a project uses — read the project's own configuration.**

This is critical because:
- Different projects use different linters (ruff vs flake8 vs pylint, eslint vs biome)
- GuardKit itself has no ruff configured despite being a Python project
- Users may install and configure tools differently from template defaults
- A static `LINT_FIX_COMMANDS` registry that maps "python" → "ruff" would be wrong for projects that don't use ruff

## Acceptance Criteria

1. A `_run_lint_autofix()` method exists in the autobuild orchestrator
2. The method discovers lint tools by **parsing the project's configuration files**, not by assuming tools from the detected language
3. Detection follows a priority chain per stack (see Detection Strategy below)
4. If no lint tool is configured in the project, the step is skipped with an INFO log — never fails, never installs tools the project doesn't declare
5. The lint auto-fix runs at the correct insertion point: after line 2365 in `_execute_turn()` (post-cancellation-check, pre-Coach-phase)
6. Lint results are injected into `player_result.report["lint_autofix"]` so the Coach can see what was auto-fixed
7. The step only runs when `player_result.success is True` and `worktree is not None`
8. The step gracefully handles: lint tool configured but not installed (warn + skip), lint command failure (warn + continue), empty worktree
9. The step logs the number of issues auto-fixed at INFO level
10. The hardcoded `tech_stack="python"` TODOs at lines 3984 and 4187 are resolved using the same detection mechanism
11. Unit tests verify config-based detection, graceful skip when unconfigured, and failure handling

## Detection Strategy

### Policy: Read the project config, don't guess

The detection must be **config-driven**, not **language-driven**. The question is not "what language is this?" but "what lint tools has this project configured?"

### Python Projects (pyproject.toml)

Parse `pyproject.toml` using `tomllib` (stdlib in 3.11+):

| Signal | What it means | Command |
|--------|--------------|---------|
| `[tool.ruff]` section exists | ruff is configured | `ruff check . --fix` |
| `[tool.ruff.format]` section exists | ruff formatter configured | `ruff format .` |
| `[tool.black]` section exists | black is configured | `black .` |
| `[tool.isort]` section exists | isort is configured | `isort .` |
| `[tool.flake8]` section exists | flake8 is configured (no --fix) | Skip (flake8 has no auto-fix) |
| `[tool.pylint]` section exists | pylint configured (no --fix) | Skip (pylint has no auto-fix) |
| None of the above | No lint tool configured | Skip entirely |

**Priority**: If multiple tools configured, prefer ruff (it subsumes isort and partially replaces black).

**Also check**: `setup.cfg` for `[flake8]`, `[isort]` sections (legacy projects).

### TypeScript/JavaScript Projects (package.json)

Parse `package.json`:

| Signal | What it means | Command |
|--------|--------------|---------|
| `scripts.lint` exists | Project has a lint script | `npm run lint -- --fix` (or detect fix variant) |
| `scripts.lint:fix` exists | Explicit fix script | `npm run lint:fix` |
| `scripts.format` exists | Format script configured | `npm run format` |
| `eslint` in `devDependencies` + no lint script | ESLint installed but no script | `npx eslint . --fix` |
| `biome` in `devDependencies` | Biome configured | `npx biome check --write` |
| None of the above | No lint tool configured | Skip entirely |

**Priority**: Prefer `scripts.lint:fix` > `scripts.lint -- --fix` > `scripts.format`.

### Go Projects (go.mod)

| Signal | What it means | Command |
|--------|--------------|---------|
| `.golangci.yml` or `.golangci.yaml` exists | golangci-lint configured | `golangci-lint run --fix` |
| Neither exists | Only gofmt available (always present in Go) | `gofmt -w .` |

### Rust Projects (Cargo.toml)

| Signal | What it means | Command |
|--------|--------------|---------|
| `Cargo.toml` exists | Rust project | `cargo fmt` (rustfmt always available with toolchain) |
| `clippy` section in config | Clippy configured | `cargo clippy --fix --allow-dirty` |

### .NET Projects (*.csproj)

| Signal | What it means | Command |
|--------|--------------|---------|
| `*.csproj` exists | .NET project | `dotnet format` (built-in) |

### Fallback

If no configuration signals are found for any stack → skip lint auto-fix entirely with:
```
INFO: [task_id] No lint tool configured in project — skipping pre-Coach auto-fix
```

## Implementation Notes

### Integration Point

```python
# autobuild.py:_execute_turn(), after L2365, before L2367
# ===== Pre-Coach: Lint Auto-Fix =====
if player_result.success and worktree is not None:
    lint_result = self._run_lint_autofix(task_id, turn, worktree)
    if lint_result is not None:
        player_result.report["lint_autofix"] = lint_result.to_dict()
# ===== Coach Phase =====  (existing)
```

### Config-Driven Discovery (replaces static LINT_FIX_COMMANDS)

```python
def _discover_lint_commands(worktree_path: Path) -> List[str]:
    """Discover lint fix commands from the project's own configuration.

    Reads pyproject.toml, package.json, etc. to find what tools
    the project has actually configured. Never assumes tools.
    Returns empty list if no lint tools configured.
    """
    commands = []

    # Python: parse pyproject.toml for [tool.*] sections
    pyproject = worktree_path / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        tools = data.get("tool", {})
        if "ruff" in tools:
            commands.append("ruff check . --fix")
            if "format" in tools.get("ruff", {}):
                commands.append("ruff format .")
        elif "black" in tools:
            commands.append("black .")
        if "isort" in tools and "ruff" not in tools:
            commands.append("isort .")

    # TypeScript/JS: parse package.json scripts
    pkg_json = worktree_path / "package.json"
    if pkg_json.exists():
        import json
        with open(pkg_json) as f:
            pkg = json.load(f)
        scripts = pkg.get("scripts", {})
        if "lint:fix" in scripts:
            commands.append("npm run lint:fix")
        elif "lint" in scripts:
            commands.append("npm run lint -- --fix")
        if "format" in scripts:
            commands.append("npm run format")

    # Go: check for golangci config
    if (worktree_path / "go.mod").exists():
        if any((worktree_path / f).exists()
               for f in [".golangci.yml", ".golangci.yaml"]):
            commands.append("golangci-lint run --fix")
        commands.append("gofmt -w .")

    # Rust: cargo fmt is always available
    if (worktree_path / "Cargo.toml").exists():
        commands.append("cargo fmt")

    # .NET: dotnet format is built-in
    if list(worktree_path.glob("*.csproj")):
        commands.append("dotnet format")

    return commands
```

### Error Handling Policy

| Scenario | Action |
|----------|--------|
| No lint tool configured | Skip with INFO log |
| Lint tool configured but not installed | WARN log, skip that command, continue |
| Lint command fails (non-zero exit) | WARN log, continue to Coach |
| Lint command times out (>30s) | WARN log, kill, continue to Coach |
| Multiple lint tools configured | Run all discovered commands in order |

**Never block Coach evaluation due to lint auto-fix failure.**

### Key Files

- `guardkit/orchestrator/autobuild.py` — main integration (lines 2365-2367, 3984, 4187)
- New: `guardkit/orchestrator/lint_discovery.py` — config-driven lint tool discovery
- `guardkit/commands/feature_spec.py` — `detect_stack()` for language detection (secondary signal)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_detect_test_command()` pattern reference

## Coach Validation

- `pytest tests/ -v --tb=short` — all tests pass
- Verify lint discovery parses `pyproject.toml` `[tool.*]` sections, not hardcoded tool names per language
- Verify lint discovery parses `package.json` `scripts` for JS/TS projects
- Verify graceful skip when project has no lint tool configured (e.g., GuardKit's own pyproject.toml)
- Verify graceful handling when lint tool is configured but not installed
- Verify `player_result.report["lint_autofix"]` is populated correctly
