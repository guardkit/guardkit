# Feature 1: Enhanced feature-plan Command

> **Feature ID**: FEATURE-001
> **Priority**: P0 (Enables all subsequent features)
> **Estimated Effort**: 2-3 days
> **Dependencies**: None

---

## Summary

Enhance the existing `/feature-plan` command to output structured YAML feature files that can be consumed by the AutoBuild orchestrator. This enables dependency-aware task execution and parallel processing.

---

## Current State

- `/feature-plan` analyzes a feature and creates tasks
- Tasks are created as markdown files in `.guardkit/tasks/`
- Human manually runs `/task-work` for each task
- No dependency tracking between tasks
- No parallel execution grouping

---

## Required Changes

### 1.1 Output Structure Enhancement

The feature-plan should output a structured feature file that can be consumed by the orchestrator:

```yaml
# .guardkit/features/FEAT-001.yaml
id: FEAT-001
name: "User Authentication"
description: "Add OAuth2 authentication flow"
created: 2025-01-15T10:30:00Z
status: planned  # planned | in_progress | completed | failed

complexity: 7  # 1-10 scale (aggregate of tasks)
estimated_tasks: 4

tasks:
  - id: TASK-001
    name: "Create auth service skeleton"
    complexity: 3
    dependencies: []
    status: pending
    
  - id: TASK-002  
    name: "Implement OAuth2 flow"
    complexity: 5
    dependencies: [TASK-001]
    status: pending
    
  - id: TASK-003
    name: "Add token refresh logic"
    complexity: 4
    dependencies: [TASK-002]
    status: pending
    
  - id: TASK-004
    name: "Integration tests"
    complexity: 3
    dependencies: [TASK-001, TASK-002, TASK-003]
    status: pending

orchestration:
  parallel_groups:
    - [TASK-001]           # Must complete first
    - [TASK-002, TASK-003] # Can run in parallel after TASK-001
    - [TASK-004]           # Final integration
  
  estimated_duration_minutes: 45
  recommended_parallel: 2
```

### 1.2 Dependency Analysis

Analyze task descriptions to identify dependencies:

```python
# guardkit/planning/dependencies.py
from dataclasses import dataclass
from typing import List, Set

@dataclass
class TaskDependency:
    task_id: str
    depends_on: List[str]
    reason: str  # Why this dependency exists

class DependencyAnalyzer:
    """Analyze tasks to identify dependencies."""
    
    def analyze(self, tasks: List[dict]) -> List[TaskDependency]:
        """
        Identify dependencies based on:
        - Explicit mentions ("after X", "requires Y")
        - File dependencies (task modifies file another task creates)
        - Logical ordering (tests depend on implementation)
        """
        pass
    
    def build_parallel_groups(
        self, 
        tasks: List[dict], 
        dependencies: List[TaskDependency]
    ) -> List[List[str]]:
        """
        Build execution groups where tasks in same group can run in parallel.
        
        Algorithm:
        1. Build dependency graph
        2. Topological sort
        3. Group tasks at same "level" (no dependencies between them)
        """
        pass
    
    def validate_no_cycles(self, dependencies: List[TaskDependency]) -> bool:
        """Ensure no circular dependencies exist."""
        pass
```

### 1.3 Complexity Scoring

Each task should have complexity score (1-10) based on:

```python
# guardkit/planning/complexity.py
from dataclasses import dataclass
from typing import List

@dataclass
class ComplexityFactors:
    files_to_modify: int      # Weight: 1.5
    integration_points: int    # Weight: 2.0
    test_requirements: int     # Weight: 1.0
    risk_factors: List[str]    # Weight: 1.5 per factor
    
    def calculate_score(self) -> int:
        """Calculate 1-10 complexity score."""
        raw = (
            self.files_to_modify * 1.5 +
            self.integration_points * 2.0 +
            self.test_requirements * 1.0 +
            len(self.risk_factors) * 1.5
        )
        # Normalize to 1-10
        return min(10, max(1, int(raw / 2)))

class ComplexityAnalyzer:
    """Analyze task complexity."""
    
    def analyze_task(self, task: dict, codebase_context: dict) -> ComplexityFactors:
        """
        Analyze task to determine complexity factors.
        
        Uses AI to:
        - Identify files likely to be modified
        - Count integration points (APIs, DBs, external services)
        - Assess test requirements
        - Identify risk factors (security, performance, data migration)
        """
        pass
```

### 1.4 Backward Compatibility

- Existing `/feature-plan` behavior unchanged by default
- New `--structured` flag outputs YAML format
- Task markdown files still created for `/task-work` compatibility

```python
# In feature-plan command handler
if structured:
    # New behavior: YAML feature file
    write_feature_yaml(feature_id, tasks, dependencies, parallel_groups)
    
# Always: Create task markdown files (backward compatible)
for task in tasks:
    write_task_markdown(task)
```

---

## File Changes

### New Files

```
guardkit/
├── planning/
│   ├── __init__.py
│   ├── dependencies.py      # DependencyAnalyzer
│   ├── complexity.py        # ComplexityAnalyzer
│   └── feature_writer.py    # YAML feature file writer
```

### Modified Files

```
.claude/commands/feature-plan.md  # Add --structured flag handling
guardkit/cli/feature.py           # CLI integration (if exists)
```

---

## Acceptance Criteria

- [ ] `/feature-plan "description" --structured` outputs YAML feature file
- [ ] Feature file saved to `.guardkit/features/FEAT-XXX.yaml`
- [ ] Feature file includes task dependencies
- [ ] Feature file includes parallel execution groups
- [ ] Each task has complexity score (1-10)
- [ ] Existing task markdown files still created in `.guardkit/tasks/`
- [ ] Feature file parseable by Python (`pyyaml`)
- [ ] No circular dependencies allowed (validation error if detected)
- [ ] Backward compatible: `/feature-plan` without `--structured` works as before

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_dependencies.py
def test_dependency_analyzer_finds_explicit_deps():
    tasks = [
        {"id": "TASK-001", "description": "Create user model"},
        {"id": "TASK-002", "description": "After user model, add authentication"}
    ]
    analyzer = DependencyAnalyzer()
    deps = analyzer.analyze(tasks)
    
    assert any(d.task_id == "TASK-002" and "TASK-001" in d.depends_on for d in deps)

def test_parallel_groups_respects_dependencies():
    deps = [
        TaskDependency("TASK-002", ["TASK-001"], "requires model"),
        TaskDependency("TASK-003", ["TASK-001"], "requires model"),
        TaskDependency("TASK-004", ["TASK-002", "TASK-003"], "integration")
    ]
    analyzer = DependencyAnalyzer()
    groups = analyzer.build_parallel_groups(tasks, deps)
    
    assert groups[0] == ["TASK-001"]
    assert set(groups[1]) == {"TASK-002", "TASK-003"}  # Parallel
    assert groups[2] == ["TASK-004"]

def test_complexity_scoring():
    factors = ComplexityFactors(
        files_to_modify=3,
        integration_points=2,
        test_requirements=2,
        risk_factors=["security"]
    )
    score = factors.calculate_score()
    assert 1 <= score <= 10
```

### Integration Tests

```python
# tests/integration/test_feature_plan.py
@pytest.mark.integration
async def test_feature_plan_structured_creates_yaml():
    result = await run_cli([
        "feature-plan", 
        "Add user authentication",
        "--structured"
    ])
    
    assert result.exit_code == 0
    
    # Verify YAML file created
    feature_files = list(Path(".guardkit/features").glob("FEAT-*.yaml"))
    assert len(feature_files) == 1
    
    # Verify parseable
    import yaml
    with open(feature_files[0]) as f:
        data = yaml.safe_load(f)
    
    assert "tasks" in data
    assert "orchestration" in data
    assert "parallel_groups" in data["orchestration"]
```

---

## Example Usage

```bash
# New structured output
/feature-plan "Add OAuth2 authentication with Google and GitHub providers" --structured

# Output:
# ✅ Feature FEAT-001 created
# 📋 Tasks: 5
#    TASK-001: Create OAuth service interface (complexity: 3)
#    TASK-002: Implement Google OAuth provider (complexity: 5)
#    TASK-003: Implement GitHub OAuth provider (complexity: 5)
#    TASK-004: Add session management (complexity: 4)
#    TASK-005: Integration tests (complexity: 3)
# 
# 🔀 Parallel execution groups:
#    Group 1: [TASK-001]
#    Group 2: [TASK-002, TASK-003] (can run in parallel)
#    Group 3: [TASK-004]
#    Group 4: [TASK-005]
#
# 📁 Feature file: .guardkit/features/FEAT-001.yaml
# 📁 Task files: .guardkit/tasks/TASK-001.md ... TASK-005.md
```

---

## References

- Main spec: `AutoBuild_Product_Specification.md`
- Kickoff doc: `AutoBuild_Phase1_Kickoff.md`
