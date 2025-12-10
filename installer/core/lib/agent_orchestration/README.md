# Agent System Orchestration

Complete orchestration of the agent system workflow for template creation.

## Overview

This module coordinates the entire agent discovery and generation process:

1. **Phase 1: Inventory** - Scan existing agents (custom, template, global)
2. **Phase 2: Generation** - Generate missing agents using AI
3. **Phase 3: External Discovery** - Optional community agent suggestions (Phase 2)
4. **Phase 4: Recommendation** - Build final agent recommendation
5. **Phase 5: Summary** - Display results to user

## Architecture

```
AgentOrchestrator
├─> MultiSourceAgentScanner (TASK-003)
│   └─> AgentInventory
├─> AIAgentGenerator (TASK-004A)
│   └─> GeneratedAgent[]
├─> ExternalDiscovery (Phase 2)
│   └─> DiscoveredAgent[]
└─> AgentRecommendation
```

## Usage

### Basic Usage

```python
from lib.agent_orchestration import get_agents_for_template
from lib.codebase_analyzer import analyze_codebase

# Analyze codebase
analysis = analyze_codebase(project_root)

# Get agent recommendations
agents = get_agents_for_template(analysis)

# Use agents in template
for agent in agents.all_agents():
    save_agent_to_template(agent, template_dir)
```

### Advanced Usage

```python
from lib.agent_orchestration import AgentOrchestrator
from pathlib import Path

# Initialize with custom settings
orchestrator = AgentOrchestrator(
    template_path=Path("templates/react/agents"),
    enable_external_discovery=True  # Phase 2 feature
)

# Get recommendations
recommendation = orchestrator.recommend_agents(analysis)

# Access different agent types
print(f"Custom agents: {len(recommendation.use_custom)}")
print(f"Generated agents: {len(recommendation.generated)}")
print(f"External suggestions: {len(recommendation.external_suggestions)}")

# Get summary
print(recommendation.summary())
```

## Data Models

### AgentRecommendation

Complete agent recommendation with all sources:

```python
@dataclass
class AgentRecommendation:
    use_custom: List[AgentDefinition]  # User's custom agents
    use_template: List[AgentDefinition]  # Template agents
    use_global: List[AgentDefinition]  # Global built-in agents
    generated: List[GeneratedAgent]  # AI-created agents
    external_suggestions: List[DiscoveredAgent]  # Phase 2

    def all_agents() -> List  # All usable agents
    def total_count() -> int  # Total count
    def summary() -> str  # Human-readable summary
```

### DiscoveredAgent (Phase 2)

External agent discovered from community sources:

```python
@dataclass
class DiscoveredAgent:
    name: str
    description: str
    source_url: str
    tags: List[str]
    relevance_score: float  # 0-100
```

## Features

### Error Handling

The orchestrator includes comprehensive error handling:

```python
try:
    recommendation = orchestrator.recommend_agents(analysis)
except Exception as e:
    # Graceful fallback to minimal agent set
    recommendation = orchestrator._fallback_recommendation()
```

### Progress Feedback

Real-time progress feedback to user:

```
============================================================
  Agent System
============================================================

📦 Scanning agent sources...
  ✓ Found 3 custom agents in .claude/agents/
  ✓ Found 15 global agents

📊 Total: 18 agents available

🤖 Determining agent needs...
  ✓ Identified 5 capability needs
  ✓ Found 2 gaps to fill

💡 Creating project-specific agents...
  → Generating: maui-appshell-navigator
    ✓ Created: maui-appshell-navigator (confidence: 85%)

============================================================
  Agent Setup Complete
============================================================

Total: 20 agents
  • Custom: 3
  • Global: 15
  • Generated: 2
```

### External Discovery (Phase 2)

Optional community agent discovery:

```python
# Enable external discovery
agents = get_agents_for_template(
    analysis=analysis,
    enable_external=True
)

# User will be prompted:
# 🌐 Discover community agents? [y/N]
```

## Integration

### Template Creation

Used in `/template-create` command:

```python
def template_create(project_root: Path):
    # Step 1: Q&A
    qa = TemplateCreateQASession()
    answers = qa.run()

    # Step 2: AI Analysis
    analyzer = AICodebaseAnalyzer(qa_context=answers)
    analysis = analyzer.analyze(answers.codebase_path)

    # Step 3: Agent System (TASK-009)
    agents = get_agents_for_template(analysis)

    # Step 4: Save to template
    template_dir = Path(f"installer/local/templates/{answers.template_name}")
    agents_dir = template_dir / "agents"
    agents_dir.mkdir(exist_ok=True)

    for agent in agents.all_agents():
        agent_file = agents_dir / f"{agent.name}.md"
        agent_file.write_text(agent.full_definition)
```

## Testing

### Unit Tests

```python
def test_orchestration_flow():
    """Test complete orchestration"""
    analysis = CodebaseAnalysis(...)
    orchestrator = AgentOrchestrator()

    recommendation = orchestrator.recommend_agents(analysis)

    assert recommendation.total_count() > 0
    assert recommendation is not None

def test_error_handling():
    """Test graceful error handling"""
    # Should not crash even if phases fail
    recommendation = orchestrator.recommend_agents(invalid_analysis)
    assert recommendation is not None
```

### Integration Tests

```python
def test_end_to_end_flow():
    """Test complete flow from analysis to recommendation"""
    # Analyze real project
    analysis = analyze_codebase("examples/sample-project")

    # Get recommendations
    agents = get_agents_for_template(analysis)

    # Verify results
    assert agents.total_count() > 0
    assert len(agents.use_global) > 0
```

## Dependencies

- `lib.agent_scanner` - Multi-source agent scanning (TASK-003)
- `lib.agent_generator` - AI agent generation (TASK-004A)
- `lib.codebase_analyzer` - Codebase analysis (TASK-002)

## Future Enhancements (Phase 2)

- [ ] External agent discovery from registries
- [ ] Community agent suggestions from GitHub
- [ ] Agent relevance scoring
- [ ] Deduplication of similar agents
- [ ] Agent versioning and updates

## Related

- [TASK-002: Codebase Analysis](../../tasks/completed/TASK-002-codebase-analysis.md)
- [TASK-003: Agent Scanner](../agent_scanner/README.md)
- [TASK-004A: Agent Generator](../agent_generator/README.md)
- [TASK-009: Agent Orchestration](../../tasks/in_progress/TASK-009-agent-orchestration.md)
- [TASK-010: Template Create Command](../../tasks/backlog/TASK-010-template-create.md)
