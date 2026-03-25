"""
Comprehensive Test Suite for Direct Mode Auto-Detection Logic

Tests the implementation mode detection and auto-detection logic in AgentInvoker:
- Explicit frontmatter overrides (direct, task-work, unknown modes)
- Auto-detection defaults to task-work for complexity >= 2
- Direct mode only for scaffolding tasks with complexity <= 1
- Edge cases (missing frontmatter, invalid complexity, etc.)

Coverage Target: >=95%
Test Count: 25+ tests
"""

import pytest
from pathlib import Path

from guardkit.orchestrator.agent_invoker import AgentInvoker


# ==================== Fixtures ====================


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance."""
    return AgentInvoker(worktree_path=worktree_path)


def create_task_file(
    worktree_path: Path,
    task_id: str,
    frontmatter_yaml: str,
    body: str = "",
    subfolder: str = "backlog"
) -> Path:
    """Helper to create task markdown file in temp worktree.

    Args:
        worktree_path: Root worktree path
        task_id: Task identifier (e.g., "TASK-001")
        frontmatter_yaml: YAML frontmatter content (without --- delimiters)
        body: Optional markdown body content
        subfolder: Task folder (backlog, in_progress, etc.)

    Returns:
        Path to created task file
    """
    tasks_dir = worktree_path / "tasks" / subfolder
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task_file = tasks_dir / f"{task_id}-test-task.md"
    content = f"---\n{frontmatter_yaml}\n---\n\n{body}"
    task_file.write_text(content)
    return task_file


# ============================================================================
# 1. Explicit Implementation Mode Tests (5 tests)
# ============================================================================


def test_explicit_direct_mode_overrides_complexity(worktree_path, agent_invoker):
    """Test explicit implementation_mode: direct overrides complexity score."""
    create_task_file(
        worktree_path,
        "TASK-001",
        frontmatter_yaml="""
task_id: TASK-001
title: Test Task
complexity: 10
implementation_mode: direct
""",
        body="High complexity but explicitly direct mode"
    )

    mode = agent_invoker._get_implementation_mode("TASK-001")
    assert mode == "direct"


def test_explicit_task_work_mode_overrides_low_complexity(worktree_path, agent_invoker):
    """Test explicit implementation_mode: task-work overrides low complexity."""
    create_task_file(
        worktree_path,
        "TASK-002",
        frontmatter_yaml="""
task_id: TASK-002
title: Simple Task
complexity: 1
implementation_mode: task-work
""",
        body="Low complexity but explicitly task-work mode"
    )

    mode = agent_invoker._get_implementation_mode("TASK-002")
    assert mode == "task-work"


def test_unknown_implementation_mode_normalizes_to_task_work(worktree_path, agent_invoker):
    """Test unknown implementation_mode (e.g., manual) normalizes to task-work."""
    create_task_file(
        worktree_path,
        "TASK-003",
        frontmatter_yaml="""
task_id: TASK-003
title: Legacy Task
complexity: 2
implementation_mode: manual
""",
        body="Legacy manual mode should normalize to task-work"
    )

    mode = agent_invoker._get_implementation_mode("TASK-003")
    assert mode == "task-work"


def test_explicit_direct_mode_with_risk_keywords(worktree_path, agent_invoker):
    """Test explicit direct mode overrides high-risk keywords."""
    create_task_file(
        worktree_path,
        "TASK-004",
        frontmatter_yaml="""
task_id: TASK-004
title: Security Update
complexity: 2
implementation_mode: direct
""",
        body="Contains security keyword but explicitly direct mode"
    )

    mode = agent_invoker._get_implementation_mode("TASK-004")
    assert mode == "direct"


def test_explicit_task_work_mode_with_no_risk(worktree_path, agent_invoker):
    """Test explicit task-work mode with safe, low-complexity task."""
    create_task_file(
        worktree_path,
        "TASK-005",
        frontmatter_yaml="""
task_id: TASK-005
title: Safe Simple Task
complexity: 1
implementation_mode: task-work
""",
        body="Safe task with explicit task-work mode"
    )

    mode = agent_invoker._get_implementation_mode("TASK-005")
    assert mode == "task-work"


# ============================================================================
# 2. Auto-Detection: Complexity-Based Tests (7 tests)
#    New behaviour: only scaffolding + complexity <= 1 gets direct mode
# ============================================================================


def test_auto_detect_complexity_1_non_scaffolding_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=1 without scaffolding type returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-101",
        frontmatter_yaml="""
task_id: TASK-101
title: Simple Documentation Update
complexity: 1
""",
        body="Update README with latest installation instructions"
    )

    mode = agent_invoker._get_implementation_mode("TASK-101")
    assert mode == "task-work"


def test_auto_detect_scaffolding_complexity_1_returns_direct(worktree_path, agent_invoker):
    """Test scaffolding task with complexity=1 returns direct mode."""
    create_task_file(
        worktree_path,
        "TASK-101B",
        frontmatter_yaml="""
task_id: TASK-101B
title: Create Project Scaffold
complexity: 1
task_type: scaffolding
""",
        body="Generate project scaffold files"
    )

    mode = agent_invoker._get_implementation_mode("TASK-101B")
    assert mode == "direct"


def test_auto_detect_scaffolding_complexity_0_returns_direct(worktree_path, agent_invoker):
    """Test scaffolding task with complexity=0 returns direct mode."""
    create_task_file(
        worktree_path,
        "TASK-101C",
        frontmatter_yaml="""
task_id: TASK-101C
title: Create Trivial Scaffold
complexity: 0
task_type: scaffolding
""",
        body="Generate trivial scaffold"
    )

    mode = agent_invoker._get_implementation_mode("TASK-101C")
    assert mode == "direct"


def test_auto_detect_scaffolding_complexity_2_returns_task_work(worktree_path, agent_invoker):
    """Test scaffolding task with complexity=2 returns task-work (threshold exceeded)."""
    create_task_file(
        worktree_path,
        "TASK-101D",
        frontmatter_yaml="""
task_id: TASK-101D
title: Create Complex Scaffold
complexity: 2
task_type: scaffolding
""",
        body="Generate project scaffold with multiple templates"
    )

    mode = agent_invoker._get_implementation_mode("TASK-101D")
    assert mode == "task-work"


def test_auto_detect_complexity_2_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=2 without scaffolding returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-102",
        frontmatter_yaml="""
task_id: TASK-102
title: Add Logging to Utility Function
complexity: 2
""",
        body="Add debug logging to the file parser utility"
    )

    mode = agent_invoker._get_implementation_mode("TASK-102")
    assert mode == "task-work"


def test_auto_detect_complexity_3_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=3 returns task-work (no longer eligible for direct)."""
    create_task_file(
        worktree_path,
        "TASK-103",
        frontmatter_yaml="""
task_id: TASK-103
title: Refactor Helper Function
complexity: 3
""",
        body="Extract common logic into reusable helper function"
    )

    mode = agent_invoker._get_implementation_mode("TASK-103")
    assert mode == "task-work"


def test_auto_detect_complexity_4_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=4 returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-104",
        frontmatter_yaml="""
task_id: TASK-104
title: Implement New Feature
complexity: 4
""",
        body="Add new feature with multiple components"
    )

    mode = agent_invoker._get_implementation_mode("TASK-104")
    assert mode == "task-work"


def test_auto_detect_complexity_5_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=5 returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-105",
        frontmatter_yaml="""
task_id: TASK-105
title: Standard Feature Implementation
complexity: 5
""",
        body="Implement feature with standard complexity"
    )

    mode = agent_invoker._get_implementation_mode("TASK-105")
    assert mode == "task-work"


def test_auto_detect_complexity_10_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=10 (high) returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-106",
        frontmatter_yaml="""
task_id: TASK-106
title: Complex System Refactor
complexity: 10
""",
        body="Major architectural refactor"
    )

    mode = agent_invoker._get_implementation_mode("TASK-106")
    assert mode == "task-work"


def test_auto_detect_no_complexity_defaults_to_task_work(worktree_path, agent_invoker):
    """Test missing complexity field defaults to task-work."""
    create_task_file(
        worktree_path,
        "TASK-107",
        frontmatter_yaml="""
task_id: TASK-107
title: Task Without Complexity
""",
        body="No complexity score set"
    )

    mode = agent_invoker._get_implementation_mode("TASK-107")
    assert mode == "task-work"


# ============================================================================
# 3. Auto-Detection: Task Type Tests (4 tests)
# ============================================================================


def test_feature_type_complexity_1_returns_task_work(worktree_path, agent_invoker):
    """Test feature task type with complexity=1 returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-301A",
        frontmatter_yaml="""
task_id: TASK-301A
title: Simple Feature
complexity: 1
task_type: feature
""",
        body="Simple feature implementation"
    )

    mode = agent_invoker._get_implementation_mode("TASK-301A")
    assert mode == "task-work"


def test_bugfix_type_complexity_1_returns_task_work(worktree_path, agent_invoker):
    """Test bugfix task type with complexity=1 returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-301B",
        frontmatter_yaml="""
task_id: TASK-301B
title: Simple Fix
complexity: 1
task_type: bugfix
""",
        body="Simple bug fix"
    )

    mode = agent_invoker._get_implementation_mode("TASK-301B")
    assert mode == "task-work"


def test_no_task_type_complexity_1_returns_task_work(worktree_path, agent_invoker):
    """Test missing task_type with complexity=1 returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-301C",
        frontmatter_yaml="""
task_id: TASK-301C
title: Simple Task
complexity: 1
""",
        body="Task without explicit type"
    )

    mode = agent_invoker._get_implementation_mode("TASK-301C")
    assert mode == "task-work"


def test_scaffolding_type_explicit_task_work_overrides(worktree_path, agent_invoker):
    """Test explicit task-work overrides scaffolding auto-detection."""
    create_task_file(
        worktree_path,
        "TASK-301D",
        frontmatter_yaml="""
task_id: TASK-301D
title: Scaffold with Override
complexity: 1
task_type: scaffolding
implementation_mode: task-work
""",
        body="Scaffolding with explicit task-work override"
    )

    mode = agent_invoker._get_implementation_mode("TASK-301D")
    assert mode == "task-work"


# ============================================================================
# 4. Edge Cases and Error Handling (6 tests)
# ============================================================================


def test_task_not_found_defaults_to_task_work(agent_invoker):
    """Test non-existent task defaults to task-work."""
    mode = agent_invoker._get_implementation_mode("TASK-999")
    assert mode == "task-work"


def test_invalid_complexity_value_defaults_to_task_work(worktree_path, agent_invoker):
    """Test invalid complexity value (non-integer) defaults to task-work."""
    create_task_file(
        worktree_path,
        "TASK-401",
        frontmatter_yaml="""
task_id: TASK-401
title: Invalid Complexity Task
complexity: "low"
""",
        body="Complexity is a string instead of integer"
    )

    mode = agent_invoker._get_implementation_mode("TASK-401")
    assert mode == "task-work"


def test_empty_frontmatter_defaults_to_task_work(worktree_path, agent_invoker):
    """Test empty frontmatter defaults to task-work."""
    create_task_file(
        worktree_path,
        "TASK-402",
        frontmatter_yaml="",
        body="Task with no frontmatter"
    )

    mode = agent_invoker._get_implementation_mode("TASK-402")
    assert mode == "task-work"


def test_complexity_zero_non_scaffolding_returns_task_work(worktree_path, agent_invoker):
    """Test complexity=0 without scaffolding type returns task-work."""
    create_task_file(
        worktree_path,
        "TASK-404",
        frontmatter_yaml="""
task_id: TASK-404
title: Zero Complexity Task
complexity: 0
""",
        body="Complexity set to zero"
    )

    mode = agent_invoker._get_implementation_mode("TASK-404")
    assert mode == "task-work"


def test_negative_complexity_returns_task_work(worktree_path, agent_invoker):
    """Test negative complexity defaults to task-work."""
    create_task_file(
        worktree_path,
        "TASK-405",
        frontmatter_yaml="""
task_id: TASK-405
title: Negative Complexity Task
complexity: -5
""",
        body="Complexity set to negative value"
    )

    mode = agent_invoker._get_implementation_mode("TASK-405")
    assert mode == "task-work"


def test_task_in_different_subfolder(worktree_path, agent_invoker):
    """Test task in in_progress folder defaults to task-work."""
    create_task_file(
        worktree_path,
        "TASK-406",
        frontmatter_yaml="""
task_id: TASK-406
title: In Progress Task
complexity: 2
""",
        body="Task located in in_progress folder",
        subfolder="in_progress"
    )

    mode = agent_invoker._get_implementation_mode("TASK-406")
    assert mode == "task-work"


# ============================================================================
# 5. Integration Tests: Combined Scenarios (4 tests)
# ============================================================================


def test_combined_scaffolding_low_complexity_returns_direct(worktree_path, agent_invoker):
    """Test scaffolding + complexity 1 = direct."""
    create_task_file(
        worktree_path,
        "TASK-501",
        frontmatter_yaml="""
task_id: TASK-501
title: Create Project Scaffold
complexity: 1
task_type: scaffolding
""",
        body="""
## Description
Generate project scaffold with basic files.

## Acceptance Criteria
- [ ] Scaffold files created
"""
    )

    mode = agent_invoker._get_implementation_mode("TASK-501")
    assert mode == "direct"


def test_combined_non_scaffolding_low_complexity_returns_task_work(worktree_path, agent_invoker):
    """Test non-scaffolding + low complexity = task-work."""
    create_task_file(
        worktree_path,
        "TASK-502",
        frontmatter_yaml="""
task_id: TASK-502
title: Update Documentation Examples
complexity: 1
description: Refresh code examples in user guide
tags:
  - documentation
  - examples
""",
        body="""
## Description
Update the code examples in the user guide to reflect the latest changes.

## Acceptance Criteria
- [ ] All code examples run without errors
"""
    )

    mode = agent_invoker._get_implementation_mode("TASK-502")
    assert mode == "task-work"


def test_combined_scaffolding_high_complexity_returns_task_work(worktree_path, agent_invoker):
    """Test scaffolding + high complexity = task-work."""
    create_task_file(
        worktree_path,
        "TASK-503",
        frontmatter_yaml="""
task_id: TASK-503
title: Complex Multi-Template Scaffold
complexity: 5
task_type: scaffolding
""",
        body="""
## Description
Create complex multi-template scaffold with configuration.

## Acceptance Criteria
- [ ] Multiple templates generated
- [ ] Configuration files created
- [ ] Validation passes
"""
    )

    mode = agent_invoker._get_implementation_mode("TASK-503")
    assert mode == "task-work"


def test_combined_high_complexity_safe_content_returns_task_work(worktree_path, agent_invoker):
    """Test high complexity even with safe content = task-work."""
    create_task_file(
        worktree_path,
        "TASK-504",
        frontmatter_yaml="""
task_id: TASK-504
title: Refactor Reporting Module
complexity: 7
description: Major refactor of reporting system
""",
        body="""
## Description
Refactor the reporting module to support multiple output formats.

## Acceptance Criteria
- [ ] Support PDF, CSV, JSON outputs
- [ ] Maintain backward compatibility
- [ ] Add comprehensive tests
"""
    )

    mode = agent_invoker._get_implementation_mode("TASK-504")
    assert mode == "task-work"
