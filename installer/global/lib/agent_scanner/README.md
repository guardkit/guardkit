# Multi-Source Agent Scanner

Scans agent definitions from multiple sources in priority order to build a complete inventory of available agents.

## Overview

The Multi-Source Agent Scanner implements a priority-based agent discovery system that respects user customizations while providing fallback options from templates and global built-in agents.

### Agent Priority Order

1. **Custom Agents** (Priority 3) - `.claude/agents/` - User's custom agents always take precedence
2. **Template Agents** (Priority 2) - `template/agents/` - Template-specific agents
3. **Global Agents** (Priority 1) - `installer/global/agents/` - Built-in system agents

## Key Features

- ✅ Multi-source scanning (custom, template, global)
- ✅ Priority-based agent resolution
- ✅ Frontmatter parsing with python-frontmatter
- ✅ Graceful error handling for missing directories
- ✅ Duplicate detection and reporting
- ✅ High-performance directory scanning (<1s for 100 agents)
- ✅ Comprehensive data structures

## Usage

### Basic Scanning

```python
from agent_scanner import MultiSourceAgentScanner

# Create scanner with default paths
scanner = MultiSourceAgentScanner()

# Scan all sources
inventory = scanner.scan()

# Output:
# 📦 Scanning agent sources...
#   ✓ Found 3 custom agents in .claude/agents/
#   ✓ Found 2 template-specific agents
#   ✓ Found 15 global agents
#
# 💡 Agent Priority:
#   • react-specialist: Using your custom version
#
# 📊 Total: 20 agents available
```

### Custom Paths

```python
from pathlib import Path
from agent_scanner import MultiSourceAgentScanner

scanner = MultiSourceAgentScanner(
    custom_path=Path("/path/to/custom/agents"),
    template_path=Path("/path/to/template/agents"),
    global_path=Path("/path/to/global/agents")
)

inventory = scanner.scan()
```

### Query Inventory

```python
# Find specific agent (returns highest priority match)
agent = inventory.find_by_name("react-specialist")
if agent:
    print(f"Found: {agent.name} from {agent.source}")

# Check if agent exists
if inventory.has_agent("maui-specialist"):
    print("MAUI specialist available")

# Get all agents from specific source
custom_agents = inventory.get_by_source("custom")
print(f"Custom agents: {len(custom_agents)}")

# Get all agents in priority order
all_agents = inventory.all_agents()
for agent in all_agents:
    print(f"{agent.name} (priority: {agent.priority})")
```

## Data Structures

### AgentDefinition

Represents a discovered agent with all its metadata:

```python
@dataclass
class AgentDefinition:
    name: str                  # Agent name
    description: str           # Agent description
    tools: List[str]          # Available tools
    tags: List[str]           # Agent tags
    source: str               # "custom", "template", or "global"
    source_path: Path         # Path to agent file
    priority: int             # 3=custom, 2=template, 1=global
    full_definition: str      # Complete markdown content
```

### AgentInventory

Complete inventory of all discovered agents:

```python
@dataclass
class AgentInventory:
    custom_agents: List[AgentDefinition]
    template_agents: List[AgentDefinition]
    global_agents: List[AgentDefinition]

    def all_agents() -> List[AgentDefinition]
    def find_by_name(name: str) -> Optional[AgentDefinition]
    def has_agent(name: str) -> bool
    def get_by_source(source: str) -> List[AgentDefinition]
```

## Agent File Format

Agent files must be markdown with YAML frontmatter:

```markdown
---
name: my-agent
description: Description of what this agent does
tools: [Read, Write, Grep, Bash]
tags: [testing, custom]
---

# My Agent

Detailed documentation about the agent.

## Capabilities
- Capability 1
- Capability 2
```

### Required Fields

- `name` - Agent identifier (defaults to filename stem if missing)
- `description` - Brief description of agent's purpose

### Optional Fields

- `tools` - List of tools the agent uses (default: [])
- `tags` - List of tags for categorization (default: [])

## Performance

The scanner is highly optimized for performance:

- Scans 100 agents in ~0.44 seconds
- Lazy evaluation (only scans when needed)
- Efficient file system operations
- Minimal memory footprint

## Error Handling

The scanner handles errors gracefully:

- Missing directories: Returns empty list (no crash)
- Invalid agent files: Logs warning and continues
- Malformed frontmatter: Skips file and continues
- Missing required fields: Skips file and continues

## Testing

Comprehensive test suite with 16 tests covering:

- ✅ Data structure creation
- ✅ Priority ordering
- ✅ Multi-source scanning
- ✅ Duplicate detection
- ✅ Error handling
- ✅ Performance requirements

Run tests:

```bash
python -m pytest tests/unit/test_multi_source_scanner.py -v
```

Coverage: **85%** (exceeds 80% requirement)

## Integration

The scanner integrates with:

- TASK-004A: AI Agent Generator (uses inventory to avoid duplicates)
- TASK-009: Agent Orchestration System
- Template Creation: Provides agent inventory during template generation

## Example

See `examples/agent_scanner_usage.py` for a complete working example:

```bash
python examples/agent_scanner_usage.py
```

## Architecture

```
MultiSourceAgentScanner
├── scan() - Main entry point
├── _scan_directory() - Scan single directory
├── _parse_agent_file() - Parse agent markdown
├── _find_global_agents_path() - Auto-detect global path
└── _report_duplicates() - Report duplicate agents

AgentInventory
├── all_agents() - Get all in priority order
├── find_by_name() - Find by name (highest priority)
├── has_agent() - Check existence
└── get_by_source() - Filter by source
```

## License

MIT

## Author

Taskwright Team
