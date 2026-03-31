# Implementation Guide: Autobuild Efficiency

## Overview

This feature addresses the quality gate task inefficiency identified in TASK-REV-8D32's analysis of the youtube-transcript-mcp autobuild review. The goal is a 30-40% reduction in total orchestrator turns.

## Architecture

```
Feature Plan Generation          Autobuild Execution
┌─────────────────────┐     ┌──────────────────────────────┐
│ Research Template    │     │ _execute_turn()               │
│ ┌─────────────────┐ │     │                               │
│ │ + Lint AC in    │ │     │ Player → [NEW: Auto-Fix] →    │
│ │   every task    │ │     │           Coach               │
│ │ - No standalone │ │     │                               │
│ │   QG tasks      │ │     │ _discover_lint_commands()      │
│ └─────────────────┘ │     │ parse pyproject.toml / pkg.json│
└─────────────────────┘     │ run only configured tools      │
                            └──────────────────────────────┘
                                        │
                                Post-Build
                            ┌───────────────────┐
                            │ ReviewSummary      │
                            │ Generator          │
                            │ (structured .md)   │
                            └───────────────────┘
```

## Core Design Principle: Read the Project Config, Don't Guess

**The pre-Coach auto-fix step must discover lint tools from the project's own configuration files — never assume what tools a project uses based on the detected language.**

Why this matters:
- GuardKit itself is a Python project with **no ruff configured** — a static "python → ruff" mapping would be wrong
- Different projects use different linters (ruff vs flake8 vs pylint, eslint vs biome)
- Users may configure tools differently from template defaults
- A tool configured in pyproject.toml may not be installed if dev dependencies weren't installed

Detection approach per stack:

| Stack | Config File | What to parse | Example signals |
|-------|------------|---------------|-----------------|
| Python | `pyproject.toml` | `[tool.*]` sections | `[tool.ruff]` → ruff configured; `[tool.black]` → black configured; no `[tool.*]` → skip |
| TypeScript/JS | `package.json` | `scripts` + `devDependencies` | `scripts.lint` → `npm run lint`; `scripts.lint:fix` → `npm run lint:fix`; no lint script → skip |
| Go | `go.mod` + `.golangci.yml` | Config file existence | `.golangci.yml` → golangci-lint; always `gofmt` |
| Rust | `Cargo.toml` | Always available | `cargo fmt` (part of toolchain) |
| .NET | `*.csproj` | Always available | `dotnet format` (built-in) |

**If no lint tool is configured in the project → skip entirely with INFO log.**

## Wave 1: Parallel Tasks

### TASK-ABE-001: Lint Compliance in Task ACs

**What changes**: Research template prompt text only (no parser code changes).

**Key principle**: The instruction must be stack-agnostic. Say "lint compliance" not "ruff check".

**Modified prompts should include**:
- "Every implementation task MUST include an acceptance criterion: 'All modified files pass lint checks with zero errors'"
- "Do NOT create standalone quality gate verification tasks"

**Validation**: Generate a feature plan and verify:
- Each task has lint AC
- No task is solely a quality gate verification task

### TASK-ABE-002: Pre-Coach Auto-Fix

**What changes**: New `guardkit/orchestrator/lint_discovery.py` + method insertion in `autobuild.py` at L2366.

**Critical design decisions**:

1. **Config-driven discovery, not language-driven registry**: Parse `pyproject.toml` for `[tool.ruff]`, `[tool.black]`, etc. Parse `package.json` for `scripts.lint`. Do NOT use a static `LINT_FIX_COMMANDS["python"] = ["ruff"]` mapping.

2. **Insertion point**: After L2365 (cancellation resolved), before L2367 (Coach phase). The `player_result.report` dict carries lint results to Coach.

3. **Error handling policy**:
   - No lint tool configured → INFO log, skip (this is normal and expected)
   - Tool configured but not installed → WARN log, skip that command, continue
   - Lint command fails → WARN log, continue to Coach
   - Lint command times out (>30s) → WARN log, kill, continue to Coach
   - **Never block Coach evaluation due to lint auto-fix failure**

4. **TODO resolution**: Replace hardcoded `tech_stack="python"` at lines 3984 and 4187 with config-based detection.

**Data flow**:
```
Player completes → _run_lint_autofix(task_id, turn, worktree)
                    ├── _discover_lint_commands(worktree.path)
                    │   ├── parse pyproject.toml [tool.*] sections
                    │   ├── parse package.json scripts
                    │   ├── check go.mod + .golangci.yml
                    │   └── check Cargo.toml / *.csproj
                    ├── subprocess.run() for each discovered command
                    └── return LintAutoFixResult (or None if nothing configured)
                 → player_result.report["lint_autofix"] = result
                 → Coach receives report with lint results
```

**Example: How different projects are handled**:

| Project | pyproject.toml has | Discovered commands | Behaviour |
|---------|--------------------|--------------------|----|
| youtube-transcript-mcp | `[tool.ruff]` + `[tool.mypy]` | `ruff check . --fix`, `ruff format .` | Runs ruff auto-fix |
| guardkit | No `[tool.*]` lint sections | (empty) | Skips with INFO log |
| a React app | `package.json` with `scripts.lint` | `npm run lint -- --fix` | Runs npm lint:fix |
| a Go project | `go.mod` + `.golangci.yml` | `golangci-lint run --fix`, `gofmt -w .` | Runs both |
| unknown project | No recognisable config | (empty) | Skips with INFO log |

## Wave 2: Depends on Wave 1

### TASK-ABE-003: Structured Review Summaries

**What changes**: New `guardkit/orchestrator/review_summary.py` + integration in `feature_orchestrator.py`.

**Timing**: Runs after `orchestrate()` completes (post-build, not during).

**Input**: Feature execution results (task results, turn records, quality gate data).

**Output**: Markdown file alongside raw log.

## Testing Strategy

- **Unit tests**: Mock file reads for pyproject.toml/package.json, verify config-driven discovery, test graceful skip when unconfigured
- **Integration tests**: End-to-end feature plan generation with lint ACs, verify no QG tasks
- **Key test case**: GuardKit's own `pyproject.toml` (no `[tool.ruff]`) must result in skip, not failure
- **No live autobuild test needed**: Changes are verified by unit + integration tests

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Project has lint tool configured but not installed | WARN log + skip. Worktree setup should install dev deps, but never fail if it didn't. |
| Lint auto-fix introduces bugs | Coach still validates; auto-fix only for formatting/import sort. Ruff --fix is safe for auto-fixable rules. |
| Research template doesn't follow lint AC instruction | Add explicit example in prompt |
| Project uses an unknown lint tool | Skip — only tools with known `--fix` capability are discovered |
| Summary generator misses edge cases | Use actual turn data structure, not log parsing |
| pyproject.toml parsing fails (malformed TOML) | Catch exception, WARN log, skip |
