# Python CLI Tool with Orchestrator Pattern

A production-grade Python CLI template based on Taskwright's architecture (16K+ LOC in production). This template demonstrates the orchestrator pattern, dependency injection, agent-based systems, and markdown-driven command definitions - patterns proven in real-world CLI tool development.

## Overview

This template provides a complete foundation for building sophisticated command-line tools with:

- **Orchestrator pattern**: Central coordinator for complex workflows
- **Dependency injection**: Loose coupling via DI container
- **Agent-based system**: Specialized agents for specific tasks
- **Markdown commands**: Human and AI readable command definitions
- **Type safety**: Comprehensive Pydantic validation
- **Minimal dependencies**: Only essential libraries (Pydantic, Jinja2, PyYAML)

## Quick Start

```bash
# Initialize new project from this template
taskwright init taskwright-python

# You'll be prompted for:
# - ProjectName (PascalCase): TaskManager
# - project_name (snake_case): task_manager
# - project-name (kebab-case): task-manager
# - ProjectDescription: A command-line task management tool
# - AuthorName: Your Name

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in editable mode for development
pip install -e .

# Run tests
pytest tests/ -v --cov={{project_name}}

# Run CLI
{{project-name}} --help
{{project-name}} analyze src/
```

## Features

### Core Architecture
- **Orchestrator Pattern** - Central coordination of workflows
- **Dependency Injection** - Service locator with factory pattern
- **Agent System** - Specialized agents for different tasks
- **Type Safety** - Pydantic models for all data structures

### Dependencies (Minimal)
- **Pydantic** (>=2.0.0) - Data validation and settings
- **Jinja2** (>=3.1.0) - Template engine
- **PyYAML** (>=6.0) - Configuration file parsing
- **python-frontmatter** (>=1.0.0) - Markdown frontmatter parsing
- **pathspec** (>=0.11.0) - Path pattern matching

### Development Tools
- **pytest** + **pytest-cov** - Testing with coverage (80% threshold)
- **ruff** - Fast Python linter and formatter
- **mypy** - Static type checker (optional)

### Key Patterns
- Markdown-driven command definitions
- Factory pattern for agent creation
- Strategy pattern for workflow execution
- Template generation with Jinja2

## Project Structure

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
│   │   └── *_agent.py                # Specific agents
│   │
│   ├── commands/                     # Command implementations
│   │   └── *.py                      # Command logic
│   │
│   ├── models/                       # Data models
│   │   ├── config.py                 # Configuration models
│   │   └── result.py                 # Result models
│   │
│   ├── config/                       # Configuration
│   │   └── settings.py               # Settings management
│   │
│   └── utils/                        # Utilities
│       └── *.py                      # Helper functions
│
├── .claude/                          # Claude Code integration
│   ├── commands/                     # Markdown command specs
│   └── agents/                       # Agent definitions
│
├── tests/                            # Test suite
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── conftest.py                   # Shared fixtures
│
├── requirements.txt                  # Dependencies
├── pytest.ini                        # Pytest configuration
├── setup.py                          # Package setup
└── README.md                         # This file
```

## Usage Examples

### Basic Command Execution

```bash
# Analyze code
{{project-name}} analyze src/

# Generate from template
{{project-name}} generate --template my-template

# Validate configuration
{{project-name}} validate config.yaml
```

### Programmatic Usage

```python
from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.orchestrator.orchestrator import Orchestrator

# Setup DI container
container = DIContainer()
container.register("config", load_config())

# Create orchestrator
orchestrator = Orchestrator(container)

# Execute workflow
result = orchestrator.execute_workflow(
    "analyze",
    {"path": "src/"}
)

if result.success:
    print(f"Analysis complete: {result.data}")
else:
    print(f"Error: {result.error}")
```

## Development Guide

### Adding a New Command

1. **Define command in markdown** (`.claude/commands/my-command.md`):

```markdown
---
name: my-command
description: Do something useful
usage: {{project-name}} my-command <arg>
---

# My Command

Detailed documentation here.
```

2. **Create command implementation** (`{{project_name}}/commands/my_command.py`):

```python
from typing import Dict, Any

async def execute_my_command(
    orchestrator: Orchestrator,
    args: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute my command logic."""
    result = await orchestrator.execute_workflow(
        "my_workflow",
        args
    )
    return result.data
```

3. **Add CLI parser** (in `cli/main.py`):

```python
my_cmd_parser = subparsers.add_parser(
    "my-command",
    help="Do something useful"
)
my_cmd_parser.add_argument("arg", help="Argument description")
```

4. **Write tests** (`tests/unit/test_my_command.py`):

```python
def test_my_command():
    result = execute_my_command(orchestrator, {"arg": "test"})
    assert result["success"] == True
```

### Adding a New Agent

1. **Create agent class** (`{{project_name}}/agents/my_agent.py`):

```python
from {{project_name}}.agents.base_agent import BaseAgent, AgentResult

class MyAgent(BaseAgent):
    """Agent for specific task."""

    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResult:
        """Execute agent logic."""
        try:
            # Implementation here
            return AgentResult(
                success=True,
                data={"result": "value"}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e)
            )
```

2. **Register in DI container** (in `cli/main.py`):

```python
container.register_factory(
    "my_agent",
    lambda: MyAgent(container)
)
```

3. **Use in workflows**:

```python
orchestrator.register_agent("my_agent", container.get("my_agent"))
```

### Creating a Workflow

```python
# orchestrator/workflow.py
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class WorkflowStep:
    name: str
    agent_name: str
    params: Dict[str, Any]

@dataclass
class Workflow:
    name: str
    steps: List[WorkflowStep]

# Define workflow
my_workflow = Workflow(
    name="my_workflow",
    steps=[
        WorkflowStep(
            name="step1",
            agent_name="analyzer_agent",
            params={"type": "code"}
        ),
        WorkflowStep(
            name="step2",
            agent_name="generator_agent",
            params={"template": "default"}
        ),
    ]
)
```

## Testing

### Run All Tests

```bash
# Run with coverage
pytest tests/ -v --cov={{project_name}} --cov-report=term --cov-report=html

# Run specific test file
pytest tests/unit/test_orchestrator.py -v

# Run with markers
pytest -m unit  # Unit tests only
pytest -m integration  # Integration tests only
```

### Writing Tests

```python
# tests/unit/test_my_feature.py
import pytest
from {{project_name}}.my_module import MyClass

def test_my_feature():
    """Test my feature."""
    instance = MyClass()
    result = instance.do_something()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_feature():
    """Test async feature."""
    result = await my_async_function()
    assert result is not None
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from {{project_name}}.orchestrator.di_container import DIContainer

@pytest.fixture
def container():
    """Create DI container for tests."""
    container = DIContainer()
    # Register test services
    return container

@pytest.fixture
def orchestrator(container):
    """Create orchestrator for tests."""
    from {{project_name}}.orchestrator.orchestrator import Orchestrator
    return Orchestrator(container)
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
{{ProjectName}}_DEBUG=true
{{ProjectName}}_LOG_LEVEL=INFO
{{ProjectName}}_CONFIG_PATH=config.yaml
```

### Settings File

```python
# config/settings.py
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings."""

    debug: bool = Field(False, env="{{ProjectName}}_DEBUG")
    log_level: str = Field("INFO", env="{{ProjectName}}_LOG_LEVEL")

    class Config:
        env_prefix = "{{ProjectName}}_"
        env_file = ".env"
```

## Best Practices

### 1. Use Type Hints Everywhere

```python
# Good
def process_data(input: str, config: Dict[str, Any]) -> ProcessResult:
    pass

# Bad
def process_data(input, config):
    pass
```

### 2. Leverage Pydantic for Validation

```python
# Good
class Config(BaseModel):
    path: str
    max_size: int = Field(gt=0)

config = Config(path="src/", max_size=100)

# Bad
config = {"path": "src/", "max_size": 100}  # No validation
```

### 3. Use Dependency Injection

```python
# Good - testable, loosely coupled
class MyService:
    def __init__(self, container: DIContainer):
        self.config = container.get("config")

# Bad - tightly coupled, hard to test
class MyService:
    def __init__(self):
        self.config = load_config()  # Global state
```

### 4. Return Results, Don't Raise Exceptions (in agents)

```python
# Good - predictable control flow
return AgentResult(success=False, error="Invalid input")

# Bad - unpredictable, crashes CLI
raise ValueError("Invalid input")
```

### 5. Keep Agents Focused

Each agent should have a single responsibility:

```python
# Good - focused agent
class AnalyzerAgent(BaseAgent):
    """Analyzes code quality."""
    pass

# Bad - too many responsibilities
class AllInOneAgent(BaseAgent):
    """Analyzes, generates, validates, and deploys."""
    pass
```

## Troubleshooting

### Common Issues

**Issue**: `Service not found: my_service`
- **Solution**: Register service in DI container before use
- **Fix**: `container.register("my_service", MyService())`

**Issue**: Tests can't import package
- **Solution**: Install package in editable mode
- **Fix**: `pip install -e .`

**Issue**: Coverage below 80%
- **Solution**: Add more test cases
- **Fix**: Identify uncovered lines with `--cov-report=html` and add tests

**Issue**: Workflow fails silently
- **Solution**: Ensure agent returns `AgentResult` with `success=False` on error
- **Fix**: Wrap agent logic in try/except and return error result

## Performance Tips

### 1. Use Lazy Loading for Expensive Resources

```python
# Register as factory (created on first use)
container.register_factory(
    "expensive_resource",
    lambda: ExpensiveResource()
)
```

### 2. Cache Computation Results

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(arg: str) -> str:
    # Expensive computation
    return result
```

### 3. Use Generators for Large Data

```python
def process_large_file(path: str):
    """Process file line by line (memory efficient)."""
    with open(path) as f:
        for line in f:
            yield process_line(line)
```

## License

See LICENSE file for details.

## Credits

Based on Taskwright's production architecture:
- [Taskwright](https://github.com/taskwright-dev/taskwright) - 16K+ LOC, proven in production
- Orchestrator pattern
- Agent-based system
- Markdown command definitions

## Further Reading

- See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Packaging Guide](https://packaging.python.org/)
- [pytest Documentation](https://docs.pytest.org/)
