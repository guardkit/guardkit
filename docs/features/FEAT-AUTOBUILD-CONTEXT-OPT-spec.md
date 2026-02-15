# Feature Specification: AutoBuild Context Payload Optimization

## Overview

Reduce AutoBuild SDK session preamble from ~1,800 seconds (30 minutes) to ~300-400 seconds by eliminating unnecessary context injection. Currently, every AutoBuild SDK session loads ~1MB of user commands, project commands, rules, and the full 165KB interactive task-work specification — even though AutoBuild only needs the implementation execution protocol and project coding standards.

The fix is architecturally straightforward: stop invoking `/task-work` as an SDK skill (which forces loading all 25 user commands), and instead use focused autobuild-specific prompts with `setting_sources=["project"]` only.

## Problem Statement

AutoBuild's task execution flow creates two SDK sessions per task, each loading ~1MB of context before the first model turn:

| Source | Size | Files | Needed by AutoBuild? |
|--------|------|-------|---------------------|
| `~/.claude/commands/*.md` (user skills) | **758 KB** | 25 | **Only task-work.md (158KB)** |
| `.claude/commands/*.md` (project skills) | **157 KB** | 14 | Rarely |
| `.claude/rules/**/*.md` (project rules) | **57 KB** | 13 | Yes |
| `CLAUDE.md` files | **~15 KB** | 2 | Yes |
| **Total loaded per session** | **~987 KB** | | |
| **Total across 2 sessions** | **~1,974 KB** | | |
| **Actually needed** | **~92 KB** | | |

The root cause is a comment in `agent_invoker.py` (line ~2514) and `task_work_interface.py` (line ~352):

```python
# TASK-FB-FIX-014: Include "user" to load skills from ~/.claude/commands/
# Without "user", the SDK can't find /task-work skill
setting_sources=["user", "project"],
```

This loads **all 25 user commands** (758KB) just so the SDK can resolve `/task-work` as a skill — including completely irrelevant commands like `figma-to-react.md` (18KB), `template-create.md` (49KB), `agent-validate.md` (84KB), and `feature-plan.md` (64KB).

Even the task-work.md itself (158KB / 4,844 lines / ~45,000 tokens) is the full interactive specification including phases for clarification questions, human checkpoints, and interactive mode handling — most of which AutoBuild explicitly skips or auto-approves.

### Quantified Impact

- **Per task**: ~1,800s preamble (30 minutes) before first meaningful code output
- **Wave 2 (4 tasks)**: 4,800-7,200s (1.3-2 hours) of pure preamble overhead
- **Current timeout**: 7,200s total means only ~5,400s remains for actual implementation
- **Direct mode comparison**: ~60-120s preamble with `setting_sources=["project"]` (~78KB)

### Evidence Source

Full analysis in `.claude/reviews/TASK-REV-A781-review-report.md`.

## Scope

### In Scope

- Replace `/task-work` skill invocation in AutoBuild with focused direct prompts
- Switch both SDK sessions (design phase + Player Turn 1) to `setting_sources=["project"]`
- Create autobuild-specific prompt builders that inline only the needed execution protocol
- Add `--autobuild-mode` flag to skip unnecessary design subphases
- Expand direct mode auto-detection for complexity ≤3 tasks
- Preserve all existing interactive `/task-work` behaviour (zero regression)

### Out of Scope

- Merging pre-loop and Player Turn 1 into a single SDK session (R2 from review — higher risk, deferred)
- SDK-level prompt caching or session reuse (R5 from review — depends on SDK capabilities)
- Splitting the interactive task-work.md spec itself (that remains as-is for interactive use)
- Changes to Coach invocation (already uses `setting_sources=["project"]`)

## Technical Requirements

### 1. AutoBuild Implementation Prompt Builder

**File**: `guardkit/orchestrator/agent_invoker.py`

Create a new method `_build_autobuild_implementation_prompt()` that constructs a focused prompt containing only:

- Task requirements (from task markdown)
- Implementation execution protocol (phases 3-5 extracted from task-work spec, ~15-20KB)
- Report format specification (JSON schema for player_turn_N.json)
- Coach feedback from previous turn (if applicable)
- Job-specific Graphiti context (if available)
- Turn context (approaching_limit, escape hatch)
- Development mode (TDD/BDD/standard)
- Documentation level constraints

This prompt replaces the current pattern of invoking `/task-work TASK-XXX --implement-only` as an SDK skill.

**Key constraints**:
- The prompt must produce output compatible with `TaskWorkStreamParser` (existing parser)
- Player report JSON schema must remain identical (PLAYER_REPORT_SCHEMA)
- Git change detection enrichment must still work
- `task_work_results.json` must still be written for Coach validation

### 2. AutoBuild Design Prompt Builder

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

Create a new method `_build_autobuild_design_prompt()` that constructs a focused prompt containing only:

- Task requirements
- Design phase execution protocol (phases 1.5-2.8, ~10-15KB)
- Output format for implementation plan
- Complexity evaluation criteria
- Architectural review criteria (SOLID/DRY/YAGNI)

This replaces the current pattern of invoking `/task-work TASK-XXX --design-only` as an SDK skill.

**Key constraints**:
- Output must be parseable by existing `_parse_design_result()`
- `DesignPhaseResult` dataclass schema unchanged
- Implementation plan must be compatible with downstream Player consumption

### 3. SDK Session Configuration Changes

**File**: `guardkit/orchestrator/agent_invoker.py` — `_invoke_task_work_implement()`

```python
# BEFORE (loads ~987KB per session):
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Loads ALL user commands
    ...
)
prompt = f"/task-work {task_id} --implement-only --mode={mode}"

# AFTER (loads ~72KB per session):
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Only project rules + CLAUDE.md
    ...
)
prompt = self._build_autobuild_implementation_prompt(
    task_id=task_id,
    mode=mode,
    documentation_level=documentation_level,
)
```

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py` — `_execute_via_sdk()`

```python
# BEFORE:
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],
    ...
)
prompt = self._build_design_prompt(task_id, options)  # "/task-work TASK-XXX --design-only"

# AFTER:
options = ClaudeAgentOptions(
    setting_sources=["project"],
    ...
)
prompt = self._build_autobuild_design_prompt(task_id, options)
```

### 4. Execution Protocol Extraction

Create a reference file containing the autobuild-relevant subset of the task-work execution protocol:

**File**: `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (~15-20KB)

Extract from the full task-work.md only:
- Phase 3: Implementation (core execution loop)
- Phase 4: Testing and validation
- Phase 5: Code review and quality gates
- Report format specification
- Quality gate thresholds
- File count constraints by documentation level
- Anti-stub rules (critical for quality)

This file is **read at runtime** by the prompt builders, not loaded via SDK setting_sources. This means it's loaded once per Python process, not injected into every SDK session's token context.

Similarly for design phases:

**File**: `guardkit/orchestrator/prompts/autobuild_design_protocol.md` (~10-15KB)

Extract:
- Phase 1.5: Task context loading
- Phase 2: Implementation planning
- Phase 2.5B: Architectural review (simplified for autobuild)
- Phase 2.7: Complexity evaluation
- Output format specifications

### 5. AutoBuild Mode Flag for Design Phase

When autobuild invokes the design phase, skip phases that add latency without value in autonomous mode:

| Phase | Interactive | AutoBuild | Rationale |
|-------|-----------|-----------|-----------|
| 1.6 Clarification | Yes | **Skip** | No human present |
| 2 Planning | Yes | Yes | Essential |
| 2.1 Library Context | Yes | **Skip** | Adds 30-60s, marginal value |
| 2.5A Pattern MCP | Yes | **Skip** | Pattern suggestions add latency |
| 2.5B Arch Review | Yes | **Lightweight** | Reduce to inline check, skip subagent |
| 2.7 Complexity | Yes | Yes | Needed for orchestration decisions |
| 2.8 Checkpoint | Yes | **Auto-approve** | Already implemented |

The autobuild design prompt builder encodes these decisions directly — no flag parsing needed since autobuild never goes through the interactive path.

### 6. Expanded Direct Mode Auto-Detection

**File**: `guardkit/orchestrator/agent_invoker.py` — `_get_implementation_mode()`

Expand criteria for automatic direct mode detection:

```python
def _get_implementation_mode(self, task_id: str) -> str:
    # Existing: check frontmatter for explicit implementation_mode
    impl_mode = task_data.get("frontmatter", {}).get("implementation_mode")
    if impl_mode == "direct":
        return "direct"

    # NEW: Auto-detect direct mode for simple tasks
    complexity = task_data.get("frontmatter", {}).get("complexity", 5)
    if complexity <= 3:
        # Check for high-risk keywords that would require full task-work
        risk_keywords = ["security", "auth", "migration", "database", "api"]
        title = task_data.get("frontmatter", {}).get("title", "").lower()
        body = task_data.get("body", "").lower()
        has_risk = any(kw in title or kw in body for kw in risk_keywords)

        if not has_risk:
            logger.info(
                f"[{task_id}] Auto-detected direct mode "
                f"(complexity={complexity}, no risk keywords)"
            )
            return "direct"

    return "task-work"
```

## Expected Savings

| Change | Context Reduction | Estimated Time Savings |
|--------|------------------|----------------------|
| `setting_sources=["project"]` | 987KB → 72KB per session | ~600-900s |
| Focused prompts (no skill expansion) | Eliminates 158KB spec parsing | ~120-180s |
| Skip unnecessary design phases | 3-5 fewer subagent calls | ~180-300s |
| Direct mode for complexity ≤3 | Avoids problem entirely | Variable |
| **Combined** | | **~1,200-1,500s** |

**Expected preamble**: 1,800s → ~300-400s per task.

## Implementation Approach

### Phase 1: Quick Wins (~2 hours)

1. Create `autobuild_execution_protocol.md` by extracting phases 3-5 from task-work.md
2. Create `autobuild_design_protocol.md` by extracting phases 1.5-2.8
3. Add `_build_autobuild_implementation_prompt()` to `agent_invoker.py`
4. Switch `_invoke_task_work_implement()` to use `setting_sources=["project"]` + new prompt
5. Expand `_get_implementation_mode()` with auto-detection for complexity ≤3

### Phase 2: Design Phase Optimization (~2 hours)

1. Add `_build_autobuild_design_prompt()` to `task_work_interface.py`
2. Switch `_execute_via_sdk()` to use `setting_sources=["project"]` + new prompt
3. Encode phase skipping directly in the autobuild design prompt

### Phase 3: Validation (~1 hour)

1. Run autobuild on a complexity 4-5 task and measure preamble duration
2. Verify Player report JSON schema compliance
3. Verify Coach can still validate Player output
4. Verify TaskWorkStreamParser compatibility
5. Compare quality of output (implementation completeness, test coverage)

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Prompt quality degradation (missing context from full spec) | Medium | Extract protocol carefully; test on real tasks before committing |
| TaskWorkStreamParser incompatibility | Low | Parser uses regex on output text; prompt instructs same output format |
| Coach validation breaks | Low | Coach reads player_turn_N.json and task_work_results.json — schema unchanged |
| Interactive `/task-work` regression | Very Low | Zero changes to interactive path; only autobuild invocation path changes |
| Direct mode auto-detection false positives | Low | Conservative criteria (complexity ≤3 AND no risk keywords) |

## Success Criteria

1. **Preamble reduction**: AutoBuild task preamble ≤ 600s (down from ~1,800s)
2. **No quality regression**: Player report quality and test coverage match current levels
3. **Schema compatibility**: All existing JSON schemas (player report, task_work_results, coach decision) unchanged
4. **Interactive preservation**: `/task-work` in interactive Claude Code sessions works identically
5. **Wave 2 viability**: A 4-task wave completes within 7,200s total timeout

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | New prompt builder, setting_sources change, direct mode auto-detect |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | New prompt builder, setting_sources change |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | **NEW** — extracted phases 3-5 |
| `guardkit/orchestrator/prompts/autobuild_design_protocol.md` | **NEW** — extracted phases 1.5-2.8 |
| `guardkit/orchestrator/prompts/__init__.py` | **NEW** — protocol loading utility |
| `tests/unit/test_agent_invoker.py` | Tests for new prompt builder and auto-detection |
| `tests/unit/test_task_work_interface.py` | Tests for new design prompt builder |
| `tests/integration/test_autobuild_context_opt.py` | End-to-end preamble measurement |

## Relationship to Review TASK-REV-A781

This feature implements **R1** (Reduce context payload), **R3** (Skip unnecessary phases), and **R4** (Expand direct mode) from the review. R2 (Eliminate double session) and R5 (Prompt caching) are deferred to future work.

| Review Rec | Status | Notes |
|-----------|--------|-------|
| R1: Reduce context payload | **This feature** | Core change |
| R3: Skip unnecessary phases | **This feature** | Encoded in autobuild prompts |
| R4: Expand direct mode | **This feature** | Auto-detection for complexity ≤3 |
| R2: Eliminate double session | Deferred | Architectural change, higher risk |
| R5: Prompt caching | Deferred | Depends on SDK capabilities |
