---
id: TASK-HAI-006-C391
title: Integrate Discovery with /task-work Phase 3
status: backlog
priority: high
tags: [haiku-agents, integration, phase-3, orchestration]
epic: haiku-agent-implementation
complexity: 5
estimated_hours: 2
dependencies: [TASK-HAI-005]
blocks: [TASK-HAI-007, TASK-HAI-008]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Integrate Discovery with /task-work Phase 3

## Context

Integrate AI discovery algorithm into Phase 3 of `/task-work` command to automatically detect and suggest appropriate specialist agents based on task context (stack, keywords). This completes the model optimization strategy by routing implementation tasks to stack-specific Haiku agents.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 2 (Discovery System)
**Method**: `/task-work` (integration logic, needs quality gates)
**Workspace**: WS-D (Conductor workspace - checkpoint merge after HAI-005)

## Objectives

1. Modify `installer/global/commands/lib/phase_execution.py` Phase 3 logic
2. Add task context analysis (detect stack from files, keywords)
3. Call `discover_agents()` to find specialists
4. Use specialist if found, fallback to task-manager if not
5. Add user feedback (which agent selected, why)

## Integration Points

### Phase 3 Execution Flow

**Current Flow** (before integration):
```python
# phase_execution.py - execute_phase_3()
def execute_phase_3(task_id: str, plan: Dict) -> Dict:
    """Phase 3: Implementation"""
    # Currently uses task-manager for all implementations
    agent = "task-manager"
    result = invoke_agent(agent, task_id, plan)
    return result
```

**New Flow** (after integration):
```python
from installer.global.commands.lib.agent_discovery import discover_agents

def execute_phase_3(task_id: str, plan: Dict) -> Dict:
    """Phase 3: Implementation with specialist discovery"""

    # Step 1: Analyze task context
    context = analyze_task_context(task_id, plan)

    # Step 2: Discover specialists
    specialists = discover_agents(
        phase='implementation',
        stack=context.get('stack'),
        keywords=context.get('keywords')
    )

    # Step 3: Select agent
    if specialists:
        agent = specialists[0]  # Highest relevance
        logger.info(f"Using specialist: {agent['name']} (stack: {agent['stack']})")
    else:
        agent = {'name': 'task-manager', 'path': 'installer/global/agents/task-manager.md'}
        logger.info("No specialist found, using task-manager")

    # Step 4: Execute implementation
    result = invoke_agent(agent['name'], task_id, plan)

    # Step 5: Record agent used
    result['agent_used'] = agent['name']
    result['discovery_method'] = 'ai-metadata' if specialists else 'fallback'

    return result
```

## Task Context Analysis

### Stack Detection Logic

```python
def analyze_task_context(task_id: str, plan: Dict) -> Dict:
    """
    Analyze task to extract stack and keywords.

    Detection strategies:
    1. File extensions in plan (implementation_plan['files'])
    2. Keywords in task title/description
    3. Existing project structure (package.json, requirements.txt, *.csproj)
    """
    context = {'stack': [], 'keywords': []}

    # Strategy 1: File extensions
    files = plan.get('implementation_plan', {}).get('files', [])
    for file in files:
        if file.endswith(('.py', '.pyi')):
            context['stack'].append('python')
        elif file.endswith(('.tsx', '.ts')):
            context['stack'].extend(['react', 'typescript'])
        elif file.endswith('.cs'):
            context['stack'].extend(['dotnet', 'csharp'])
        elif file.endswith('.go'):
            context['stack'].append('go')
        elif file.endswith('.rs'):
            context['stack'].append('rust')

    # Strategy 2: Keywords in task description
    task = load_task(task_id)
    description = task.get('description', '').lower()
    title = task.get('title', '').lower()

    keyword_map = {
        'fastapi': ['fastapi', 'api', 'endpoint'],
        'react': ['react', 'component', 'hook', 'state'],
        'domain': ['entity', 'aggregate', 'value-object', 'ddd'],
    }

    for keyword, patterns in keyword_map.items():
        if any(p in description or p in title for p in patterns):
            context['keywords'].append(keyword)

    # Strategy 3: Project structure detection
    if os.path.exists('package.json'):
        with open('package.json') as f:
            pkg = json.load(f)
            if 'react' in pkg.get('dependencies', {}):
                context['stack'].append('react')

    if os.path.exists('requirements.txt'):
        with open('requirements.txt') as f:
            if 'fastapi' in f.read():
                context['stack'].append('python')
                context['keywords'].append('fastapi')

    if glob.glob('*.csproj'):
        context['stack'].extend(['dotnet', 'csharp'])

    # Deduplicate
    context['stack'] = list(set(context['stack']))
    context['keywords'] = list(set(context['keywords']))

    return context
```

## User Feedback Strategy

### Success Case (Specialist Found)

```
Phase 3: Implementation
└─ Analyzing task context...
   ├─ Detected stack: [python]
   ├─ Keywords: [fastapi, api, endpoint]
   └─ Found specialist: python-api-specialist (relevance: 3/5)

Using python-api-specialist for implementation (Haiku model)
└─ Specialized in: FastAPI endpoints, async patterns, Pydantic schemas
```

### Fallback Case (No Specialist)

```
Phase 3: Implementation
└─ Analyzing task context...
   ├─ Detected stack: [ruby]
   ├─ Keywords: []
   └─ No specialist found for stack/keywords

Using task-manager for implementation (Sonnet model)
└─ General-purpose implementation agent
```

### Discovery Disabled (All Agents Lack Metadata)

```
Phase 3: Implementation
└─ Discovery: 0 agents with metadata (migration in progress)
└─ Using task-manager (Sonnet model)
```

## Acceptance Criteria

- [ ] Phase 3 integration code added to `phase_execution.py`
- [ ] `analyze_task_context()` detects stack from file extensions
- [ ] `analyze_task_context()` detects keywords from task description
- [ ] `analyze_task_context()` checks project structure (package.json, requirements.txt, *.csproj)
- [ ] Discovery called with extracted context
- [ ] Specialist used if found (relevance score >0)
- [ ] Fallback to task-manager if no specialist found
- [ ] User feedback shows: agent selected, stack detected, keywords matched
- [ ] Result includes: `agent_used`, `discovery_method` metadata
- [ ] Integration test: Routes Python task to python-api-specialist
- [ ] Integration test: Routes React task to react-state-specialist
- [ ] Integration test: Routes .NET task to dotnet-domain-specialist
- [ ] Integration test: Routes Ruby task to task-manager (fallback)

## Testing Strategy

### Unit Tests

**Test File**: `tests/test_phase_execution.py`

```python
def test_analyze_task_context_python():
    """Should detect Python stack from .py files"""
    plan = {
        'implementation_plan': {
            'files': ['src/api/endpoints.py', 'src/models/user.py']
        }
    }
    context = analyze_task_context('TASK-001', plan)
    assert 'python' in context['stack']

def test_analyze_task_context_react():
    """Should detect React from .tsx files"""
    plan = {
        'implementation_plan': {
            'files': ['src/components/UserList.tsx']
        }
    }
    context = analyze_task_context('TASK-002', plan)
    assert 'react' in context['stack']
    assert 'typescript' in context['stack']

def test_analyze_task_context_dotnet():
    """Should detect .NET from .cs files"""
    plan = {
        'implementation_plan': {
            'files': ['src/Domain/Entities/User.cs']
        }
    }
    context = analyze_task_context('TASK-003', plan)
    assert 'dotnet' in context['stack']
    assert 'csharp' in context['stack']

def test_analyze_task_context_keywords():
    """Should extract keywords from task description"""
    # Mock task with FastAPI keywords
    task = {
        'description': 'Implement FastAPI endpoint for user registration',
        'title': 'Add user API'
    }
    # Should extract: fastapi, api, endpoint

def test_execute_phase_3_with_specialist(mock_discover_agents):
    """Should use specialist if found"""
    mock_discover_agents.return_value = [{
        'name': 'python-api-specialist',
        'stack': ['python'],
        'relevance_score': 3
    }]

    result = execute_phase_3('TASK-001', mock_plan)
    assert result['agent_used'] == 'python-api-specialist'
    assert result['discovery_method'] == 'ai-metadata'

def test_execute_phase_3_fallback(mock_discover_agents):
    """Should fallback to task-manager if no specialist"""
    mock_discover_agents.return_value = []

    result = execute_phase_3('TASK-001', mock_plan)
    assert result['agent_used'] == 'task-manager'
    assert result['discovery_method'] == 'fallback'
```

### Integration Tests

**Test File**: `tests/integration/test_phase3_integration.py`

```python
def test_python_task_routes_to_specialist():
    """Python task should use python-api-specialist"""
    # Create Python task
    task_id = create_test_task(
        title="Add FastAPI endpoint",
        files=["src/api/users.py"]
    )

    # Execute Phase 3
    result = execute_phase_3(task_id, mock_plan)

    # Verify specialist used
    assert result['agent_used'] == 'python-api-specialist'
    assert result['discovery_method'] == 'ai-metadata'

def test_react_task_routes_to_specialist():
    """React task should use react-state-specialist"""
    task_id = create_test_task(
        title="Add user list component",
        files=["src/components/UserList.tsx"]
    )

    result = execute_phase_3(task_id, mock_plan)
    assert result['agent_used'] == 'react-state-specialist'

def test_unknown_stack_uses_fallback():
    """Ruby task should fallback to task-manager"""
    task_id = create_test_task(
        title="Add Ruby controller",
        files=["app/controllers/users_controller.rb"]
    )

    result = execute_phase_3(task_id, mock_plan)
    assert result['agent_used'] == 'task-manager'
    assert result['discovery_method'] == 'fallback'
```

## Implementation Notes

### Backward Compatibility

**During Migration** (agents being enhanced with metadata):
- System works with partial metadata coverage
- Discovery returns fewer results initially
- Fallback ensures no breakage

**After Migration** (all 30 agents have metadata):
- Discovery returns optimal specialists
- Improved cost/speed from Haiku agents
- Full 48-53% cost savings achieved

### Performance Considerations

```python
# Cache agent metadata to avoid repeated file I/O
_agent_cache = None
_cache_timestamp = None

def discover_agents(phase, stack=None, keywords=None):
    global _agent_cache, _cache_timestamp

    # Refresh cache every 5 minutes
    if _agent_cache is None or time.time() - _cache_timestamp > 300:
        _agent_cache = _scan_all_agents()
        _cache_timestamp = time.time()

    # Use cached data for matching
    return _match_agents(_agent_cache, phase, stack, keywords)
```

### Logging for Debugging

```python
logger.info(f"Phase 3: Context analysis")
logger.debug(f"  Stack detected: {context['stack']}")
logger.debug(f"  Keywords: {context['keywords']}")
logger.info(f"  Discovery found {len(specialists)} specialists")
if specialists:
    logger.info(f"  Selected: {specialists[0]['name']} (score: {specialists[0].get('relevance_score', 0)})")
else:
    logger.info(f"  Fallback: task-manager")
```

## Risk Assessment

**MEDIUM Risk**:
- Integration with existing Phase 3 logic
- Context analysis accuracy (file extension detection)
- Edge cases (empty stack, ambiguous files)

**Mitigations**:
- Use `/task-work` (Phases 2.5, 4.5, 5.5 quality gates)
- Comprehensive integration tests
- Graceful fallback ensures no breakage
- Logging for debugging misrouted tasks

## Rollback Strategy

**If integration fails**:
```bash
# Revert phase_execution.py changes
git checkout installer/global/commands/lib/phase_execution.py

# Discovery module (HAI-005) remains but unused
# System reverts to task-manager for all tasks
```

**Recovery Time**: <2 minutes

## Reference Materials

- `installer/global/commands/lib/phase_execution.py` - Phase 3 current implementation
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-005-7A2E-implement-ai-discovery-algorithm.md` - Discovery algorithm
- `docs/deep-dives/model-optimization.md` - Model selection strategy

## Deliverables

1. Modified: `installer/global/commands/lib/phase_execution.py`
2. New function: `analyze_task_context()`
3. Integration tests: `tests/integration/test_phase3_integration.py`
4. User feedback: Stack/specialist detection messages
5. Metadata tracking: `agent_used`, `discovery_method` in results

## Success Metrics

- Integration tests: 4/4 passing (Python, React, .NET, fallback)
- Context analysis accuracy: >80% correct stack detection
- Specialist usage rate: >70% for stack-specific tasks
- Zero errors during fallback scenarios
- Code review: SOLID compliance >70/100

## Risk: MEDIUM | Rollback: Revert file (<2 min)
