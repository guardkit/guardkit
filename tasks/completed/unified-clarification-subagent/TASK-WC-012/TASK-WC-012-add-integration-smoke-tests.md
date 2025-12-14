---
id: TASK-WC-012
title: Add integration smoke tests
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-14T00:05:00Z
completed: 2025-12-14T00:05:00Z
priority: medium
tags: [clarification, testing, integration, wave-4]
complexity: 4
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 4
implementation_mode: task-work
conductor_workspace: null
dependencies:
  - TASK-WC-006
  - TASK-WC-007
  - TASK-WC-008
  - TASK-WC-009
  - TASK-WC-010
  - TASK-WC-011
supersedes:
  - TASK-WC-004
test_results:
  status: passed
  total_tests: 112
  passed: 112
  failed: 0
  coverage: 100%
  last_run: 2025-12-13T23:30:00Z
---

# Task: Add Integration Smoke Tests

## Description

Create integration smoke tests that verify clarification works correctly across all commands (`/task-work`, `/feature-plan`, `/task-review`).

## Location

`tests/integration/clarification/`

## Test Cases

### Test Suite 1: task-work Clarification

```python
# test_task_work_clarification.py

def test_task_work_high_complexity_shows_questions():
    """Complexity 5+ should trigger clarification questions."""
    # Create task with complexity 5
    # Run /task-work
    # Verify clarification questions appear
    pass

def test_task_work_low_complexity_skips_questions():
    """Complexity 1-2 should skip clarification."""
    # Create task with complexity 2
    # Run /task-work
    # Verify no clarification questions
    pass

def test_task_work_no_questions_flag_skips():
    """--no-questions should skip clarification."""
    # Create task with complexity 5
    # Run /task-work --no-questions
    # Verify no clarification questions
    pass

def test_task_work_with_questions_forces_clarification():
    """--with-questions should force clarification."""
    # Create task with complexity 2
    # Run /task-work --with-questions
    # Verify clarification questions appear
    pass

def test_task_work_defaults_applies_silently():
    """--defaults should apply defaults without prompting."""
    # Create task with complexity 5
    # Run /task-work --defaults
    # Verify no prompts but clarification context set
    pass
```

### Test Suite 2: feature-plan Clarification

```python
# test_feature_plan_clarification.py

def test_feature_plan_shows_context_a():
    """Context A (review scope) should appear before review."""
    # Run /feature-plan "test feature"
    # Verify Context A questions appear
    pass

def test_feature_plan_implement_shows_context_b():
    """Context B (implementation prefs) should appear at [I]mplement."""
    # Run /feature-plan "test feature"
    # Choose [I]mplement
    # Verify Context B questions appear
    pass

def test_feature_plan_no_questions_skips_both():
    """--no-questions should skip both Context A and B."""
    # Run /feature-plan "test feature" --no-questions
    # Verify no Context A questions
    # Choose [I]mplement
    # Verify no Context B questions
    pass
```

### Test Suite 3: task-review Clarification

```python
# test_task_review_clarification.py

def test_task_review_decision_mode_shows_questions():
    """Decision mode with complexity 4+ should show questions."""
    # Create review task with complexity 5
    # Run /task-review --mode=decision
    # Verify Context A questions appear
    pass

def test_task_review_code_quality_skips_low_complexity():
    """Code quality mode with complexity 4 should skip."""
    # Create review task with complexity 4
    # Run /task-review --mode=code-quality
    # Verify no questions
    pass

def test_task_review_high_complexity_always_asks():
    """Complexity 7+ should always ask regardless of mode."""
    # Create review task with complexity 8
    # Run /task-review --mode=code-quality
    # Verify questions appear
    pass
```

### Test Suite 4: Agent Discovery

```python
# test_agent_discovery.py

def test_clarification_agent_exists():
    """Verify clarification-questioner agent is installed."""
    agent_path = Path.home() / ".agentecflow" / "agents" / "clarification-questioner.md"
    assert agent_path.exists()

def test_clarification_agent_has_required_fields():
    """Verify agent has required frontmatter fields."""
    agent_path = Path.home() / ".agentecflow" / "agents" / "clarification-questioner.md"
    content = agent_path.read_text()
    assert "name: clarification-questioner" in content
    assert "tools: Read, Write, Python" in content
    assert "stack: [cross-stack]" in content
```

### Test Suite 5: Python Module Integration

```python
# test_clarification_module.py

def test_clarification_module_importable():
    """Verify clarification module can be imported."""
    import sys
    sys.path.insert(0, str(Path.home() / ".agentecflow" / "lib"))
    from clarification import ClarificationContext, Question, Decision
    assert ClarificationContext is not None

def test_generators_work():
    """Verify question generators produce valid questions."""
    from clarification.generators.planning_generator import generate_planning_questions
    questions = generate_planning_questions(mock_task, mock_context)
    assert len(questions) > 0
    for q in questions:
        assert q.id
        assert q.text
        assert q.options
```

## Test Infrastructure

### Fixtures

```python
# conftest.py

@pytest.fixture
def mock_task():
    """Create mock task for testing."""
    return {
        "id": "TASK-TEST-001",
        "title": "Test task",
        "description": "Test description",
        "complexity": 5,
        "acceptance_criteria": ["AC1", "AC2"],
    }

@pytest.fixture
def mock_context():
    """Create mock project context."""
    return {
        "stack": "python",
        "files": ["main.py", "test_main.py"],
    }
```

### Test Helpers

```python
# helpers.py

def create_test_task(complexity: int = 5) -> str:
    """Create a test task and return its ID."""
    # Implementation
    pass

def run_command_with_input(command: str, inputs: List[str]) -> str:
    """Run a slash command with simulated user inputs."""
    # Implementation
    pass
```

## Acceptance Criteria

- [x] All test suites created
- [x] All test cases pass
- [x] Tests run in CI pipeline
- [x] Test coverage includes all three context types
- [x] Test coverage includes all flags
- [x] Agent discovery tests pass on fresh installation

## Notes

- Tests should be runnable without user interaction
- Use `--defaults` flag or mock inputs for automation
- Consider timeout handling for integration tests
- Document any manual testing steps that can't be automated
