"""
Inline design phase execution protocol for AutoBuild pre-loop.

This module provides a slim inline protocol (~15KB) that replaces the
full /task-work --design-only skill invocation (~165KB) in the pre-loop
SDK prompt. Combined with setting_sources=["project"] instead of
["user", "project"], this eliminates ~840KB of unnecessary context loading.

Architecture:
    The protocol instructs the SDK agent to execute Phases 1.5 through 2.8
    directly, without needing the task-work skill or any user commands.
    Output markers are carefully aligned with TaskWorkInterface._parse_sdk_output()
    regex patterns to ensure backward compatibility.

TASK-POF-003: Created as part of preamble overhead fix.

Example:
    >>> from guardkit.orchestrator.quality_gates.design_protocol import (
    ...     build_inline_design_protocol,
    ... )
    >>> protocol = build_inline_design_protocol("TASK-001", {"autobuild_mode": True}, Path("/repo"))
    >>> assert "TASK-001" in protocol
    >>> assert len(protocol) <= 20480  # 20KB limit
"""

from pathlib import Path
from typing import Any, Dict


# Maximum protocol size in bytes (acceptance criterion)
MAX_PROTOCOL_SIZE = 20480  # 20KB


def build_inline_design_protocol(
    task_id: str,
    options: Dict[str, Any],
    worktree_path: Path,
) -> str:
    """Build inline design phase execution protocol for SDK invocation.

    Generates a self-contained prompt that instructs the SDK agent to execute
    design phases (1.5 through 2.8) without requiring the /task-work skill.

    Parameters
    ----------
    task_id : str
        Task identifier (e.g., "TASK-001")
    options : Dict[str, Any]
        Execution options:
        - autobuild_mode: Use autonomous optimizations (skip clarification, auto-approve)
        - skip_arch_review: Omit Phase 2.5B architectural review
        - no_questions: Skip Phase 1.6 clarification
        - docs: Documentation level (minimal/standard/comprehensive)
    worktree_path : Path
        Path to the worktree where the task executes

    Returns
    -------
    str
        Complete inline protocol string for SDK invocation
    """
    autobuild_mode = options.get("autobuild_mode", False)
    skip_arch_review = options.get("skip_arch_review", False)
    docs_level = options.get("docs", "minimal")

    # Build conditional sections
    arch_review_section = _build_arch_review_section() if not skip_arch_review else ""
    phase_list = _build_phase_list(skip_arch_review)

    protocol = f"""You are executing the design phase for task {task_id}.

Your job is to read the task, create an implementation plan, evaluate complexity, and approve the design. Follow each phase exactly.

## Phases to Execute

{phase_list}

---

## Phase 1.5: Load Task Context

1. Use the Glob tool to find the task file:
   - Search pattern: `tasks/*/{task_id}*.md`
   - Check directories: backlog/, in_progress/, design_approved/
2. Read the task file using the Read tool
3. Extract from the file:
   - **Title**: From frontmatter `title:` field
   - **Description**: From `## Description` section
   - **Acceptance Criteria**: From `## Acceptance Criteria` section
   - **Implementation Notes**: From `## Implementation Notes` section (if present)
   - **Complexity**: From frontmatter `complexity:` field (if present)
   - **Tags**: From frontmatter `tags:` field (if present)

If the task file is not found, output:
```
Error: Task file not found for {task_id}
```
and stop.

Display a brief summary of what you loaded.

---

## Phase 2: Implementation Planning

Based on the task context from Phase 1.5, create an implementation plan.

### Plan Requirements

The plan MUST include:
1. **Overview**: Brief description of what will be implemented
2. **Files to Create/Modify**: List each file with its purpose
3. **Implementation Approach**: Step-by-step approach
4. **Test Strategy**: What tests to write and how to verify
5. **Dependencies**: Any new packages or modules needed
6. **Estimated Effort**: Rough estimate (lines of code, time)
7. **Risks**: Potential issues and mitigations

### Documentation Level: {docs_level}
- If minimal: Keep the plan concise, structured data focus
- If standard: Include brief architecture notes
- If comprehensive: Include detailed rationale and alternatives

### Save the Plan

Write the implementation plan to this exact path:
`.claude/task-plans/{task_id}-implementation-plan.md`

Create the directory if it doesn't exist using Bash: `mkdir -p .claude/task-plans`

After saving, output this exact line:
```
Plan saved to: .claude/task-plans/{task_id}-implementation-plan.md
```
{arch_review_section}
---

## Phase 2.7: Complexity Evaluation

Evaluate the implementation complexity on a 1-10 scale.

### Scoring Factors

| Factor | Score Range | Criteria |
|--------|------------|---------|
| File complexity | 0-3 | 1-2 files=1, 3-5=2, 6+=3 |
| Pattern complexity | 0-2 | Known patterns=0, novel=1, complex integration=2 |
| Risk level | 0-3 | No risks=0, external deps=1, security/schema=2, breaking changes=3 |
| Dependencies | 0-2 | None=0, internal=1, external=2 |

Total score = sum of factors (cap at 10).

Output the score in this exact format:
```
Complexity: N/10
```

where N is the calculated score (1-10).

---

## Phase 2.8: Design Checkpoint

The design checkpoint is auto-approved (autonomous execution mode, no human present).

Output these exact lines:
```
Phase 2.8: checkpoint approved
State: DESIGN_APPROVED
```

---

## Output Summary

After completing all phases, provide a brief summary:

```
Design Phase Complete for {task_id}
- Plan: .claude/task-plans/{task_id}-implementation-plan.md
- Complexity: [score]/10
- Checkpoint: approved
```

## CRITICAL: Output Format Requirements

The following output markers MUST appear exactly as shown (they are parsed programmatically):
1. `Plan saved to: .claude/task-plans/{task_id}-implementation-plan.md`
2. `Complexity: N/10` (where N is a number 1-10)
3. `Phase 2.8: checkpoint approved`
4. `State: DESIGN_APPROVED`
{_build_arch_marker_reminder() if not skip_arch_review else ""}
Do NOT modify these marker formats. They are required for automated processing.
"""
    return protocol


def _build_phase_list(skip_arch_review: bool) -> str:
    """Build the list of phases to execute."""
    phases = [
        "1. **Phase 1.5**: Load Task Context - Read the task file and extract requirements",
        "2. **Phase 2**: Implementation Planning - Create and save the implementation plan",
    ]
    if not skip_arch_review:
        phases.append(
            "3. **Phase 2.5B**: Architectural Review - Evaluate SOLID/DRY/YAGNI principles"
        )
    phases.extend([
        f"{'4' if not skip_arch_review else '3'}. **Phase 2.7**: Complexity Evaluation - Score complexity 1-10",
        f"{'5' if not skip_arch_review else '4'}. **Phase 2.8**: Design Checkpoint - Auto-approve design",
    ])
    return "\n".join(phases)


def _build_arch_review_section() -> str:
    """Build Phase 2.5B architectural review section."""
    return """
---

## Phase 2.5B: Architectural Review

Review the implementation plan for architectural quality.

### Evaluation Criteria

Score each principle from 0-100:

**SOLID Principles**:
- Single Responsibility: Each class/module has one reason to change
- Open/Closed: Open for extension, closed for modification
- Liskov Substitution: Subtypes substitutable for base types
- Interface Segregation: No forced dependency on unused interfaces
- Dependency Inversion: Depend on abstractions, not concretions

**DRY (Don't Repeat Yourself)**:
- No duplicated logic across modules
- Shared functionality properly extracted
- Constants and configuration centralized

**YAGNI (You Aren't Gonna Need It)**:
- No speculative features or over-engineering
- Minimum complexity for requirements
- No unnecessary abstractions

### Output Format

Output the scores in these exact formats:
```
Architectural Score: N/100
SOLID: N
DRY: N
YAGNI: N
```

where N is the calculated score (0-100) for each.

### Thresholds
- Score >= 80: Good architecture
- Score 60-79: Acceptable with recommendations
- Score < 60: Needs revision (flag issues)
"""


def _build_arch_marker_reminder() -> str:
    """Build reminder for architectural review output markers."""
    return """5. `Architectural Score: N/100` (where N is 0-100)
6. `SOLID: N`, `DRY: N`, `YAGNI: N` (where N is 0-100 for each)
"""
