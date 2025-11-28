---
id: TASK-BDD-004
title: Implement BDD workflow routing logic
status: backlog
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, implementation, wave2]
complexity: 5
task_type: implementation
estimated_effort: 1-2 hours
wave: 2
parallel: false
implementation_method: task-work
parent_epic: bdd-restoration
depends_on: [TASK-BDD-001, TASK-BDD-003]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement BDD workflow routing logic

## Context

Implement the workflow routing that loads Gherkin scenarios from RequireKit and routes to bdd-generator agent for BDD mode implementation.

**Parent Epic**: BDD Mode Restoration
**Wave**: 2 (Implementation - after TASK-BDD-003)
**Implementation**: Use `/task-work` (full quality gates)
**Depends On**: TASK-BDD-001 (findings), TASK-BDD-003 (flag implementation)

## Description

Add BDD workflow routing across phases:
- Phase 1: Load Gherkin scenarios from RequireKit
- Phase 2: Include scenarios in planning context
- Phase 3: Route to bdd-generator agent
- Phase 4: Run BDD tests with appropriate framework

This completes the BDD mode implementation.

## Acceptance Criteria

### Phase 1: Load BDD Scenarios

**Location**: Determined by TASK-BDD-001

```python
# In Phase 1 context loading
if mode == "bdd":
    # Scenarios already validated in TASK-BDD-003
    scenario_ids = task_frontmatter["bdd_scenarios"]

    # Load from RequireKit
    scenarios = []
    requirekit_path = Path.home() / "Projects" / "require-kit"  # Or detect

    for scenario_id in scenario_ids:
        # Find scenario file
        scenario_file = requirekit_path / "docs" / "bdd" / f"{scenario_id}.feature"

        if not scenario_file.exists():
            print(f"ERROR: Scenario {scenario_id} not found at {scenario_file}")
            print(f"\nGenerate scenario in RequireKit:")
            print(f"  cd {requirekit_path}")
            print(f"  /generate-bdd REQ-XXX")
            sys.exit(1)

        # Read Gherkin content
        with open(scenario_file) as f:
            scenario_content = f.read()

        scenarios.append({
            "id": scenario_id,
            "file": str(scenario_file),
            "content": scenario_content
        })

    task_context["gherkin_scenarios"] = scenarios
    task_context["bdd_framework"] = detect_bdd_framework(project_path)

    print(f"✅ Loaded {len(scenarios)} BDD scenarios from RequireKit")
    for s in scenarios:
        print(f"   • {s['id']}")
```

### Phase 2: Include in Planning Context

```python
# In Phase 2 planning
if mode == "bdd":
    planning_context["bdd_scenarios"] = task_context["gherkin_scenarios"]
    planning_context["bdd_mode"] = True

    # Agent prompt should include:
    # "This is BDD mode. You will implement code to pass these Gherkin scenarios:"
    # [scenario content]
```

### Phase 3: Route to BDD Generator

```python
# In Phase 3 implementation
if mode == "bdd":
    agent_context = {
        "mode": "bdd",
        "scenarios": task_context["gherkin_scenarios"],
        "framework": task_context["bdd_framework"],
        "stack": detected_stack,
        "documentation_level": doc_level
    }

    # Invoke RequireKit's bdd-generator agent
    result = invoke_requirekit_agent("bdd-generator", agent_context)

    # Result should include:
    # - Step definitions generated
    # - Implementation code
    # - BDD test setup
```

### Phase 4: Run BDD Tests

```python
# In Phase 4 testing
if mode == "bdd":
    # Detect framework
    framework = task_context["bdd_framework"]

    if framework == "pytest-bdd":
        test_cmd = "pytest tests/ -v --gherkin-terminal-reporter"
    elif framework == "specflow":
        test_cmd = "dotnet test --filter Category=BDD"
    elif framework == "cucumber-js":
        test_cmd = "npm run test:bdd"
    else:
        test_cmd = "pytest tests/ -v"  # Default fallback

    # Run tests
    test_results = run_command(test_cmd)

    # Standard fix loop applies (Phase 4.5)
```

### BDD Framework Detection

```python
def detect_bdd_framework(project_path: Path) -> str:
    """
    Detect BDD testing framework based on project files.

    Returns:
        Framework name (pytest-bdd, specflow, cucumber-js, cucumber)
    """
    # Python
    if (project_path / "requirements.txt").exists():
        with open(project_path / "requirements.txt") as f:
            if "pytest-bdd" in f.read():
                return "pytest-bdd"

    if (project_path / "pyproject.toml").exists():
        with open(project_path / "pyproject.toml") as f:
            if "pytest-bdd" in f.read():
                return "pytest-bdd"

    # .NET
    if list(project_path.glob("*.csproj")):
        with open(list(project_path.glob("*.csproj"))[0]) as f:
            if "SpecFlow" in f.read():
                return "specflow"

    # TypeScript/JavaScript
    if (project_path / "package.json").exists():
        with open(project_path / "package.json") as f:
            pkg = json.load(f)
            if "@cucumber/cucumber" in pkg.get("devDependencies", {}):
                return "cucumber-js"

    # Ruby
    if (project_path / "Gemfile").exists():
        with open(project_path / "Gemfile") as f:
            if "cucumber" in f.read():
                return "cucumber"

    return "pytest-bdd"  # Default fallback
```

### Agent Invocation

**RequireKit's bdd-generator location**: `~/.agentecflow/agents/bdd-generator.md` (via RequireKit installation)

**Invocation pattern**:
```python
def invoke_requirekit_agent(agent_name: str, context: dict):
    """
    Invoke agent from RequireKit installation.

    Args:
        agent_name: Agent file name (e.g., "bdd-generator")
        context: Agent context dictionary

    Returns:
        Agent execution result
    """
    agent_file = Path.home() / ".agentecflow" / "agents" / f"{agent_name}.md"

    if not agent_file.exists():
        raise FileNotFoundError(f"RequireKit agent not found: {agent_file}")

    # Load and execute agent (implementation depends on TaskWright's agent system)
    # This follows same pattern as other agents (task-manager, code-reviewer, etc.)
```

## Testing Requirements

### Test BDD Workflow End-to-End

**Setup**:
```bash
# Create test scenario in RequireKit
cd ~/Projects/require-kit
cat > docs/bdd/BDD-TEST-001.feature << 'GHERKIN'
Feature: Sample Test Feature
  Scenario: Sample test
    Given a sample context
    When an action occurs
    Then a result is produced
GHERKIN

# Create test task
cd ~/Projects/test-project
/task-create "Test BDD workflow"

# Edit task frontmatter:
bdd_scenarios: [BDD-TEST-001]
```

**Test**:
```bash
/task-work TASK-TEST-001 --mode=bdd

Expected:
✅ Loads BDD-TEST-001.feature
✅ Shows scenario content
✅ Routes to bdd-generator
✅ Generates step definitions
✅ Implements sample code
✅ Runs BDD tests
✅ Tests pass
✅ Task → IN_REVIEW
```

### Test Error: Scenario Not Found

```bash
# Task with non-existent scenario
bdd_scenarios: [BDD-NONEXISTENT]

/task-work TASK-XXX --mode=bdd

Expected:
❌ ERROR: Scenario BDD-NONEXISTENT not found
📖 Shows expected file path
📖 Suggests /generate-bdd command
```

### Test Fix Loop

```bash
# Implement with bug causing BDD test failure

/task-work TASK-XXX --mode=bdd

Expected:
✅ Implementation completes
❌ BDD tests fail
🔄 Fix loop attempt 1
✅ Tests pass on retry
✅ Task → IN_REVIEW
```

### Test Framework Detection

- [ ] Python project → detects pytest-bdd
- [ ] .NET project → detects SpecFlow
- [ ] TypeScript project → detects Cucumber.js
- [ ] Fallback works if no framework detected

## Success Criteria

- [ ] Scenarios load from RequireKit
- [ ] Planning context includes scenarios
- [ ] bdd-generator agent invoked
- [ ] BDD tests run in Phase 4
- [ ] Fix loop works for failing BDD tests
- [ ] Framework detection works
- [ ] All test scenarios pass

## Implementation Notes

### Scenario Loading Strategy

**Option 1**: Direct file access (simpler)
- Read .feature files directly from RequireKit path
- Pros: Fast, no API needed
- Cons: Requires RequireKit in known location

**Option 2**: RequireKit API (future)
- Call RequireKit function to load scenarios
- Pros: Abstraction, location-independent
- Cons: Requires RequireKit API implementation

**Recommendation**: Start with Option 1 (file access)

### Agent Metadata Discovery

**After TASK-BDD-006** completes, bdd-generator will have discovery metadata:

```yaml
---
name: bdd-generator
stack: [cross-stack]
phase: implementation
capabilities: [ears-to-gherkin, scenario-generation, bdd]
---
```

TaskWright should discover it via metadata matching (same as other agents).

## Related Tasks

**Depends On**: 
- TASK-BDD-001 (investigation - integration points)
- TASK-BDD-003 (flag implementation - validation done)

**Blocks**: TASK-BDD-005 (testing needs this complete)

**Parallel With**: TASK-BDD-006 (RequireKit agents - different repo)

**Wave**: 2 (sequential after TASK-BDD-003)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md) (Phase 3, lines 138-189)
- TASK-BDD-001 findings
- TASK-BDD-003 validation logic
