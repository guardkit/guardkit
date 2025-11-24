# Python CLI Tool with Orchestrator Pattern

## Project Context

This is a **production-grade Python CLI template** based on Taskwright's architecture (16K+ LOC in production). The template demonstrates the orchestrator pattern, dependency injection, agent-based systems, and markdown-driven command definitions - patterns proven in real-world CLI tool development.

## Core Principles

1. **Orchestrator Pattern**: Central coordinator manages complex workflows
2. **Dependency Injection**: Loose coupling via DI container
3. **Agent-Based System**: Specialized agents for specific tasks
4. **Markdown Commands**: Commands defined in markdown for AI/human readability
5. **Type Safety**: Comprehensive use of Pydantic for validation
6. **Minimal Dependencies**: Only essential libraries (Pydantic, Jinja2, PyYAML)

## Architecture Overview

### Orchestrator-Based Structure

```
{{project_name}}/
├── {{project_name}}/                 # Main package
│   ├── cli/                          # Command-line interface
│   │   ├── main.py                   # CLI entry point
│   │   └── commands.py               # Command definitions
│   │
│   ├── orchestrator/                 # Workflow coordination
│   │   ├── orchestrator.py           # Main orchestrator
│   │   ├── workflow.py               # Workflow definitions
│   │   └── di_container.py           # Dependency injection
│   │
│   ├── agents/                       # Specialized agents
│   │   ├── base_agent.py             # Base agent class
│   │   ├── analyzer_agent.py         # Code analyzer
│   │   ├── generator_agent.py        # Template generator
│   │   └── validator_agent.py        # Validator
│   │
│   ├── commands/                     # Command implementations
│   │   ├── analyze.py                # Analyze command
│   │   ├── generate.py               # Generate command
│   │   └── validate.py               # Validate command
│   │
│   ├── models/                       # Data models
│   │   ├── config.py                 # Configuration models
│   │   ├── result.py                 # Result models
│   │   └── workflow.py               # Workflow state
│   │
│   ├── config/                       # Configuration
│   │   ├── settings.py               # Settings management
│   │   └── loader.py                 # Config loader
│   │
│   └── utils/                        # Utilities
│       ├── file_ops.py               # File operations
│       ├── string_utils.py           # String helpers
│       └── logging.py                # Logging setup
│
├── .claude/                          # Claude Code integration
│   ├── commands/                     # Markdown command definitions
│   │   ├── analyze.md                # Analyze command spec
│   │   ├── generate.md               # Generate command spec
│   │   └── validate.md               # Validate command spec
│   │
│   └── agents/                       # Agent definitions
│       ├── analyzer-specialist.md    # Analyzer agent
│       └── generator-specialist.md   # Generator agent
│
├── tests/                            # Test suite
│   ├── unit/                         # Unit tests
│   │   ├── test_orchestrator.py
│   │   ├── test_agents.py
│   │   └── test_commands.py
│   │
│   ├── integration/                  # Integration tests
│   │   └── test_workflows.py
│   │
│   └── conftest.py                   # Shared fixtures
│
├── requirements.txt                  # Dependencies
├── pytest.ini                        # Pytest configuration
├── setup.py                          # Package setup
└── README.md                         # Project documentation
```

### Layer Responsibilities

**CLI Layer** (`cli/`):
- Command-line argument parsing
- User interaction and prompts
- Command dispatch to orchestrator
- Output formatting

**Orchestrator Layer** (`orchestrator/`):
- Workflow coordination
- Agent orchestration
- State management
- Dependency injection container
- Error handling and recovery

**Agent Layer** (`agents/`):
- Specialized task execution
- Domain-specific logic
- AI integration points
- Reusable components

**Command Layer** (`commands/`):
- Command implementations
- Business logic
- Workflow definitions
- Result aggregation

**Model Layer** (`models/`):
- Pydantic data models
- Configuration schemas
- Type-safe data structures
- Validation rules

**Config Layer** (`config/`):
- Settings management
- Environment variable handling
- Configuration loading
- Validation

## Technology Stack

### Core Dependencies
- **Pydantic** (>=2.0.0): Data validation and settings
- **Jinja2** (>=3.1.0): Template engine
- **PyYAML** (>=6.0): Configuration file parsing
- **python-frontmatter** (>=1.0.0): Markdown frontmatter parsing
- **pathspec** (>=0.11.0): Path pattern matching

### Testing
- **pytest** (>=7.4.0): Testing framework
- **pytest-cov** (>=4.1.0): Code coverage
- Coverage threshold: 80% line coverage, 75% branch coverage

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker (optional)

## Key Patterns

### 1. Orchestrator Pattern

The orchestrator coordinates workflows by delegating to specialized agents:

```python
# orchestrator/orchestrator.py
from typing import Dict, Any
from pydantic import BaseModel

class Orchestrator:
    """Central orchestrator for workflow coordination."""

    def __init__(self, di_container: DIContainer):
        """Initialize with dependency injection container."""
        self.container = di_container
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self.agents[name] = agent

    async def execute_workflow(
        self,
        workflow_name: str,
        context: Dict[str, Any]
    ) -> WorkflowResult:
        """Execute a workflow by coordinating agents."""
        workflow = self.container.get(f"workflow.{workflow_name}")

        result = WorkflowResult()
        for step in workflow.steps:
            agent = self.agents.get(step.agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {step.agent_name}")

            step_result = await agent.execute(step.params, context)
            result.add_step_result(step.name, step_result)

            if not step_result.success:
                return result.mark_failed(step_result.error)

        return result.mark_success()
```

**When to use:**
- Complex workflows with multiple steps
- Need to coordinate different specialized components
- Want centralized error handling and state management

### 2. Dependency Injection

Loose coupling via dependency injection container:

```python
# orchestrator/di_container.py
from typing import Any, Callable, Dict, Type
from pydantic import BaseModel

class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function for lazy instantiation."""
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        """Resolve a service by name."""
        if name in self._services:
            return self._services[name]

        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service
            return service

        raise ValueError(f"Service not found: {name}")

    def get_typed(self, service_type: Type[T]) -> T:
        """Resolve a service by type."""
        name = service_type.__name__
        return self.get(name)
```

**Usage:**
```python
# Register services
container = DIContainer()
container.register("config", load_config())
container.register_factory("analyzer_agent", lambda: AnalyzerAgent(container))
container.register_factory("orchestrator", lambda: Orchestrator(container))

# Resolve dependencies
orchestrator = container.get("orchestrator")
```

### 3. Agent-Based System

Specialized agents handle specific tasks:

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

class AgentResult(BaseModel):
    """Result from agent execution."""
    success: bool
    data: Dict[str, Any] = {}
    error: str | None = None

class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, container: DIContainer):
        """Initialize with DI container."""
        self.container = container

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResult:
        """Execute the agent's task."""
        pass

    def get_service(self, name: str) -> Any:
        """Get a service from the DI container."""
        return self.container.get(name)

# agents/analyzer_agent.py
class AnalyzerAgent(BaseAgent):
    """Agent for code analysis tasks."""

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResult:
        """Analyze code based on parameters."""
        try:
            path = params.get("path")
            if not path:
                return AgentResult(
                    success=False,
                    error="Missing 'path' parameter"
                )

            # Perform analysis
            results = self._analyze_code(path)

            return AgentResult(
                success=True,
                data={"analysis": results}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e)
            )

    def _analyze_code(self, path: str) -> Dict[str, Any]:
        """Internal analysis logic."""
        # Implementation here
        return {"metrics": {}, "issues": []}
```

**Creating new agents:**
1. Inherit from `BaseAgent`
2. Implement `execute()` method
3. Register in DI container
4. Use in workflows

### 4. Markdown Command Definitions

Commands defined as markdown with frontmatter:

```markdown
---
name: analyze
description: Analyze code quality and patterns
usage: {{project-name}} analyze <path>
examples:
  - {{project-name}} analyze src/
  - {{project-name}} analyze src/models/
---

# Analyze Command

Analyzes code at the specified path and provides metrics and recommendations.

## Parameters

- `path` (required): Directory or file to analyze

## Output

- Quality metrics (complexity, maintainability)
- Pattern detection (design patterns, anti-patterns)
- Recommendations for improvements
```

**Benefits:**
- Human and AI readable
- Version controlled with code
- Easy to update and document
- Consistent format

### 5. Pydantic Data Models

Type-safe configuration and data models:

```python
# models/config.py
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional

class AnalysisConfig(BaseModel):
    """Configuration for code analysis."""

    max_complexity: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum cyclomatic complexity"
    )

    ignore_patterns: List[str] = Field(
        default_factory=list,
        description="File patterns to ignore"
    )

    enable_metrics: bool = Field(
        default=True,
        description="Enable detailed metrics"
    )

    @validator("ignore_patterns")
    def validate_patterns(cls, v):
        """Validate ignore patterns."""
        for pattern in v:
            if not pattern:
                raise ValueError("Empty pattern not allowed")
        return v

# models/result.py
class WorkflowResult(BaseModel):
    """Result from workflow execution."""

    success: bool = False
    steps: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: Optional[int] = None

    def add_step_result(self, step_name: str, result: Any) -> None:
        """Add result from a workflow step."""
        self.steps[step_name] = result

    def mark_success(self) -> "WorkflowResult":
        """Mark workflow as successful."""
        self.success = True
        return self

    def mark_failed(self, error: str) -> "WorkflowResult":
        """Mark workflow as failed."""
        self.success = False
        self.error = error
        return self
```

## CLI Implementation

### Using argparse

```python
# cli/main.py
import argparse
from typing import List
from {{project_name}}.orchestrator.orchestrator import Orchestrator
from {{project_name}}.orchestrator.di_container import DIContainer

def main(args: List[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="{{project-name}}",
        description="{{ProjectDescription}}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze code quality"
    )
    analyze_parser.add_argument(
        "path",
        help="Path to analyze"
    )

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate code from templates"
    )
    generate_parser.add_argument(
        "template",
        help="Template name"
    )

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Initialize DI container and orchestrator
    container = setup_container()
    orchestrator = container.get("orchestrator")

    # Execute command
    try:
        result = orchestrator.execute_workflow(
            workflow_name=parsed_args.command,
            context=vars(parsed_args)
        )

        if result.success:
            print_success(result)
            return 0
        else:
            print_error(result.error)
            return 1

    except Exception as e:
        print_error(str(e))
        return 1

def setup_container() -> DIContainer:
    """Setup dependency injection container."""
    from {{project_name}}.config.settings import load_settings
    from {{project_name}}.agents.analyzer_agent import AnalyzerAgent
    from {{project_name}}.agents.generator_agent import GeneratorAgent

    container = DIContainer()

    # Register configuration
    container.register("config", load_settings())

    # Register agents
    container.register_factory(
        "analyzer_agent",
        lambda: AnalyzerAgent(container)
    )
    container.register_factory(
        "generator_agent",
        lambda: GeneratorAgent(container)
    )

    # Register orchestrator
    container.register_factory(
        "orchestrator",
        lambda: Orchestrator(container)
    )

    return container
```

### Alternative: Using Click/Typer

For more complex CLIs, consider Click or Typer:

```python
# With Typer (type-safe CLI)
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Analyze code quality and patterns."""
    container = setup_container()
    orchestrator = container.get("orchestrator")

    result = orchestrator.execute_workflow(
        "analyze",
        {"path": path, "verbose": verbose}
    )

    if result.success:
        typer.secho("Analysis complete!", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Error: {result.error}", fg=typer.colors.RED)
        raise typer.Exit(1)
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_orchestrator.py
import pytest
from {{project_name}}.orchestrator.orchestrator import Orchestrator
from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.agents.base_agent import AgentResult

def test_orchestrator_execute_workflow():
    """Test basic workflow execution."""
    # Setup
    container = DIContainer()
    orchestrator = Orchestrator(container)

    # Mock agent
    class MockAgent:
        async def execute(self, params, context):
            return AgentResult(success=True, data={"result": "test"})

    orchestrator.register_agent("test_agent", MockAgent())

    # Execute
    result = await orchestrator.execute_workflow(
        "test_workflow",
        {"input": "test"}
    )

    # Assert
    assert result.success
    assert "test_agent" in result.steps

def test_dependency_injection():
    """Test DI container registration and resolution."""
    container = DIContainer()

    # Register service
    container.register("test_service", "test_value")

    # Resolve
    service = container.get("test_service")
    assert service == "test_value"

    # Test factory
    call_count = 0
    def factory():
        nonlocal call_count
        call_count += 1
        return f"instance_{call_count}"

    container.register_factory("factory_service", factory)

    # First call creates instance
    instance1 = container.get("factory_service")
    assert instance1 == "instance_1"

    # Second call returns same instance (singleton)
    instance2 = container.get("factory_service")
    assert instance2 == instance1
```

### Integration Tests

```python
# tests/integration/test_workflows.py
import pytest
from {{project_name}}.cli.main import setup_container

@pytest.mark.integration
async def test_full_analyze_workflow(tmp_path):
    """Test complete analyze workflow."""
    # Setup
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello(): pass")

    container = setup_container()
    orchestrator = container.get("orchestrator")

    # Execute
    result = await orchestrator.execute_workflow(
        "analyze",
        {"path": str(test_file)}
    )

    # Assert
    assert result.success
    assert "analysis" in result.steps
```

## Development Workflow

### Quick Start

```bash
# Clone/Initialize
git clone <repo>
cd {{project-name}}

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov={{project_name}}

# Run CLI
python -m {{project_name}}.cli.main analyze src/
```

### Adding New Commands

1. **Define command in markdown** (`.claude/commands/my-command.md`)
2. **Create command implementation** (`{{project_name}}/commands/my_command.py`)
3. **Create agent if needed** (`{{project_name}}/agents/my_agent.py`)
4. **Register in DI container** (`cli/main.py`)
5. **Add CLI parser** (`cli/main.py`)
6. **Write tests** (`tests/unit/test_my_command.py`)

### Adding New Agents

1. **Create agent class** (inherit from `BaseAgent`)
2. **Implement `execute()` method**
3. **Register in DI container**
4. **Create markdown definition** (`.claude/agents/my-agent.md`)
5. **Write unit tests**

## Best Practices

### 1. Separation of Concerns

- **CLI**: Only handle argument parsing and output formatting
- **Commands**: Orchestrate workflows, don't implement logic
- **Agents**: Implement specific tasks, keep focused
- **Models**: Data validation only, no business logic

### 2. Dependency Injection

```python
# Good: Dependencies injected via container
class MyAgent(BaseAgent):
    def __init__(self, container: DIContainer):
        super().__init__(container)
        self.config = container.get("config")

# Bad: Direct instantiation
class MyAgent:
    def __init__(self):
        self.config = load_config()  # Tight coupling
```

### 3. Type Safety

```python
# Good: Type hints and Pydantic models
def analyze_code(path: str, config: AnalysisConfig) -> AnalysisResult:
    pass

# Bad: No types
def analyze_code(path, config):
    pass
```

### 4. Error Handling

```python
# Good: Return results with success/error
return AgentResult(
    success=False,
    error="Invalid path provided"
)

# Bad: Unhandled exceptions
raise ValueError("Invalid path")  # Crashes CLI
```

### 5. Testing

```python
# Good: Test through public interface
result = await orchestrator.execute_workflow("test", {})
assert result.success

# Bad: Testing internal details
assert orchestrator._internal_state == "expected"  # Brittle
```

## Common Patterns

### Configuration Management

```python
# config/settings.py
from pydantic import BaseSettings
from typing import Dict, Any

class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "{{project-name}}"
    debug: bool = False
    log_level: str = "INFO"

    # Agent configurations
    analyzer_config: Dict[str, Any] = {}
    generator_config: Dict[str, Any] = {}

    class Config:
        env_prefix = "{{ProjectName}}_"
        env_file = ".env"

def load_settings() -> Settings:
    """Load application settings."""
    return Settings()
```

### Workflow Definitions

```python
# orchestrator/workflow.py
from dataclasses import dataclass
from typing import List

@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    name: str
    agent_name: str
    params: Dict[str, Any]

@dataclass
class Workflow:
    """Workflow definition."""
    name: str
    steps: List[WorkflowStep]

# Define workflows
WORKFLOWS = {
    "analyze": Workflow(
        name="analyze",
        steps=[
            WorkflowStep(
                name="scan_files",
                agent_name="analyzer_agent",
                params={"type": "files"}
            ),
            WorkflowStep(
                name="analyze_code",
                agent_name="analyzer_agent",
                params={"type": "quality"}
            ),
        ]
    ),
}
```

## Performance Considerations

### Lazy Loading

```python
# Use factories for expensive resources
container.register_factory(
    "expensive_resource",
    lambda: ExpensiveResource()  # Only created when needed
)
```

### Caching

```python
# Cache results when appropriate
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(input: str) -> str:
    # Expensive operation
    return result
```

## Troubleshooting

### Common Issues

**Issue: Service not found**
```
Solution: Ensure service is registered in DI container before use
```

**Issue: Workflow fails silently**
```
Solution: Check agent execute() method returns AgentResult with success=False on errors
```

**Issue: Tests can't find modules**
```
Solution: Install package in editable mode: pip install -e .
```

## Further Reading

- [Orchestrator Pattern](https://martinfowler.com/articles/patterns-of-distributed-systems/)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Effective Python](https://effectivepython.com/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.

