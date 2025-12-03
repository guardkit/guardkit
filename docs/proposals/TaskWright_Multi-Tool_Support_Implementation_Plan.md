# GuardKit Multi-Tool Support Implementation Plan

**Version**: 1.0  
**Date**: November 19, 2025  
**Author**: Implementation Plan based on GitHub SpecKit Analysis  
**Status**: Ready for Implementation

---

## Executive Summary

GuardKit can support multiple AI coding tools (Claude Code, Cursor, Windsurf, GitHub Copilot, OpenCode, Codex) with **Medium effort (8 days, 5/10 complexity)** by adopting SpecKit's proven architectural patterns. The core insight: **keep template generation logic universal**, only vary the final output format per tool.

### Key Decision: Pre-Built Template Packages + Tool-Specific Formatters

- ✅ **Simpler** than initially estimated
- ✅ **Proven** approach (SpecKit has 42.5k stars)
- ✅ **Scalable** - easy to add new tools
- ✅ **Maintainable** - single source of truth

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [How SpecKit Solves This](#how-speckit-solves-this)
3. [GuardKit Adaptation Strategy](#guardkit-adaptation-strategy)
4. [Implementation Phases](#implementation-phases)
5. [Code Examples](#code-examples)
6. [Testing Strategy](#testing-strategy)
7. [Rollout Plan](#rollout-plan)
8. [References](#references)

---

## Current State Analysis

### GuardKit's Claude Code Dependencies

GuardKit is currently **deeply integrated** with Claude Code:

```
.claude/
├── agents/
│   ├── repository-pattern-specialist.md
│   ├── mvvm-specialist.md
│   └── ...
├── commands/
│   ├── task-create.md
│   └── task-work.md
└── CLAUDE.md
```

**Dependencies:**
- Agent files with YAML frontmatter
- `.claude/agents/` directory structure
- `CLAUDE.md` configuration file
- Slash commands (`/task-create`, `/task-work`)
- Specific metadata format in agent files

### What Other Tools Expect

| Tool | Config Dir | Agent Files | Main Config | Slash Commands |
|------|-----------|-------------|-------------|----------------|
| **Claude Code** | `.claude/` | `.claude/agents/*.md` | `CLAUDE.md` | Native `/` commands |
| **Cursor** | `.cursor/` | `.cursorrules` (single file) | `.cursorrules` | `@` mentions |
| **Windsurf** | `.windsurf/` | `.windsurf/workflows/*.md` | `WINDSURF.md` | Native `/` commands |
| **Copilot** | `.github/` | `.github/agents/*.md` | `COPILOT.md` | Via prompts |
| **OpenCode** | `.opencode/` | Unknown (TBD) | `OPENCODE.md` | Unknown |
| **Codex** | `.codex/` | Unknown (TBD) | `CODEX.md` | Unknown |

**The Challenge:** Different directory structures, file formats, and invocation patterns.

---

## How SpecKit Solves This

### 1. Single Source of Truth: AGENT_CONFIG Dictionary

SpecKit maintains one config dictionary in Python:

```python
# src/specify_cli/__init__.py
AGENT_CONFIG = {
    "claude": {
        "name": "Claude Code",
        "folder": ".claude/commands/",
        "install_url": "https://claude.ai/download",
        "requires_cli": True,
    },
    "copilot": {
        "name": "GitHub Copilot",
        "folder": ".github/prompts/",
        "install_url": None,  # IDE-based
        "requires_cli": False,
    },
    "cursor-agent": {
        "name": "Cursor",
        "folder": ".cursor/prompts/",
        "install_url": "https://cursor.sh",
        "requires_cli": True,
    },
    "windsurf": {
        "name": "Windsurf",
        "folder": ".windsurf/workflows/",
        "install_url": "https://windsurf.com",
        "requires_cli": True,
    },
    # ... 11 agents total (15+ now)
}
```

**Benefits:**
- Single place to add new tools
- Clear metadata per tool
- Easy to validate tool availability

### 2. Pre-Built Template Packages

SpecKit generates **22 template packages** per release:

```
GitHub Releases:
├── spec-kit-template-claude-sh-v0.0.79.zip
├── spec-kit-template-claude-ps-v0.0.79.zip
├── spec-kit-template-copilot-sh-v0.0.79.zip
├── spec-kit-template-copilot-ps-v0.0.79.zip
├── spec-kit-template-cursor-sh-v0.0.79.zip
└── ...
```

Each template contains:
- Tool-specific directory structure
- Tool-specific command files
- Universal templates (`.specify/templates/`)
- Scripts (bash or PowerShell)

**Download at init time:**
```bash
specify init my-project --ai claude
# Downloads spec-kit-template-claude-sh-v0.0.79.zip
# Extracts to my-project/
```

### 3. Universal Core + Tool-Specific Wrappers

```
project/
├── .specify/              # ✅ UNIVERSAL (all tools)
│   ├── memory/
│   │   └── constitution.md
│   ├── scripts/
│   │   └── bash/          # or powershell/
│   └── templates/
│       ├── spec-template.md
│       ├── plan-template.md
│       └── tasks-template.md
│
├── .claude/               # 🔧 TOOL-SPECIFIC (Claude Code)
│   └── commands/
│       ├── speckit.constitution.md
│       ├── speckit.specify.md
│       └── ...
│
├── CLAUDE.md              # 🔧 CONTEXT (Claude Code)
└── AGENTS.md              # ✅ FALLBACK (all tools)
```

**Key Insight:** 
- Core templates are **universal**
- Only command wrappers are **tool-specific**
- AGENTS.md provides **universal fallback** for any tool

### 4. Command File Formats Per Tool

**Claude Code** (Markdown with arguments):
```markdown
---
title: Create Feature Specification
description: Define what you want to build
---

# /speckit.specify

Create a feature specification...

$ARGUMENTS
```

**Windsurf** (TOML):
```toml
[command]
name = "/speckit.specify"
description = "Create feature specification"
template = "{{args}}"
```

**Copilot** (Prompt Markdown):
```markdown
# Specify Feature

Create a detailed specification...

User input: $1
```

### 5. Universal Fallback: AGENTS.md

For tools without native command support:

```markdown
# GuardKit Commands

## Creating Templates

To create a template from an existing codebase:

1. Run template analysis on your codebase
2. Review generated agents
3. Customize as needed

Example:
```
Create a template called "my-template" from the codebase at /path/to/project
```

## Working with Tasks

[Full instructions for manual workflow]
```

**Any tool** can read this file and guide users through the workflow.

### 6. Tool Detection (Optional)

```python
def detect_installed_tool() -> str:
    """Auto-detect which AI coding tool is installed"""
    
    # Check for Claude Code
    if shutil.which("claude"):
        return "claude"
    
    # Check for Cursor
    if shutil.which("cursor"):
        return "cursor"
    
    # Check for Windsurf  
    if shutil.which("windsurf"):
        return "windsurf"
    
    # Default
    return "claude"
```

---

## GuardKit Adaptation Strategy

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         GuardKit CLI (guardkit)             │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │   Core Logic (Tool-Agnostic)             │  │
│  │  - Codebase Analysis                     │  │
│  │  - Agent Generation                      │  │
│  │  - Template Generation                   │  │
│  │  - AI-Powered Content Creation           │  │
│  └──────────────────────────────────────────┘  │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐  │
│  │   TOOL_CONFIG (Single Source of Truth)   │  │
│  │  - Tool metadata                         │  │
│  │  - Directory structures                  │  │
│  │  - File formats                          │  │
│  └──────────────────────────────────────────┘  │
│                     │                           │
│         ┌───────────┴───────────┬──────────┐   │
│         ▼           ▼           ▼          ▼   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────┐ │
│  │ Claude   │ │ Cursor   │ │Windsurf│ │ ... │ │
│  │Formatter │ │Formatter │ │Formattr│ │     │ │
│  └──────────┘ └──────────┘ └────────┘ └─────┘ │
│         │           │           │          │   │
│         └───────────┴───────────┴──────────┘   │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐  │
│  │   Generated Template Package             │  │
│  │  - Tool-specific structure               │  │
│  │  - Formatted agents                      │  │
│  │  - Context files                         │  │
│  │  - Universal AGENTS.md fallback          │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Core Principles

1. **Universal Core**: All analysis and generation logic is tool-agnostic
2. **Thin Formatters**: Tool-specific code only handles output formatting
3. **Pre-Built Packages**: Distribute ready-to-use template structures
4. **Universal Fallback**: AGENTS.md works with any tool
5. **Explicit Tool Selection**: `--tool` flag is clearer than auto-detection

---

## Implementation Phases

### Phase 1: Extract Core Logic (2 days)

**Goal:** Separate tool-agnostic logic from Claude-specific code.

**Tasks:**
- [ ] Create `guardkit/core/template_creator.py` (pure business logic)
- [ ] Create `guardkit/core/codebase_analyzer.py` (analysis only)
- [ ] Create `guardkit/core/agent_generator.py` (AI-powered agent creation)
- [ ] Move all AI calls to core modules
- [ ] Remove Claude-specific assumptions from core

**File Structure:**
```
guardkit/
├── core/
│   ├── __init__.py
│   ├── template_creator.py      # Main orchestrator
│   ├── codebase_analyzer.py     # File analysis
│   ├── agent_generator.py       # AI agent generation
│   └── models.py                # Data classes
```

**Key Classes:**
```python
@dataclass
class Agent:
    name: str
    description: str
    priority: int
    technologies: List[str]
    content: str
    
@dataclass
class Template:
    name: str
    path: str
    content: str
    template_type: str  # 'code', 'config', etc.

@dataclass
class AnalysisResult:
    stack: str
    agents: List[Agent]
    templates: List[Template]
    technologies: List[str]
    patterns: Dict[str, Any]
```

### Phase 2: Create TOOL_CONFIG (3 hours)

**Goal:** Single source of truth for all tool configurations.

**Tasks:**
- [ ] Create `guardkit/config/tools.py`
- [ ] Define TOOL_CONFIG dictionary
- [ ] Add metadata for 4 initial tools (Claude, Cursor, Windsurf, Copilot)
- [ ] Create tool validation functions

**Implementation:**
```python
# guardkit/config/tools.py

TOOL_CONFIG = {
    "claude": {
        "name": "Claude Code",
        "folder": ".claude/",
        "agents_dir": ".claude/agents/",
        "commands_dir": ".claude/commands/",
        "context_file": "CLAUDE.md",
        "install_url": "https://claude.ai/download",
        "requires_cli": True,
        "cli_command": "claude",
        "agent_format": "markdown_frontmatter",
        "supports_slash_commands": True,
    },
    "cursor": {
        "name": "Cursor",
        "folder": ".cursor/",
        "agents_dir": ".cursor/",  # Single .cursorrules file
        "commands_dir": None,  # No separate commands
        "context_file": ".cursorrules",
        "install_url": "https://cursor.sh",
        "requires_cli": True,
        "cli_command": "cursor",
        "agent_format": "single_file",
        "supports_slash_commands": False,  # Uses @ mentions
    },
    "windsurf": {
        "name": "Windsurf",
        "folder": ".windsurf/",
        "agents_dir": ".windsurf/workflows/",
        "commands_dir": ".windsurf/workflows/",
        "context_file": "WINDSURF.md",
        "install_url": "https://windsurf.com",
        "requires_cli": True,
        "cli_command": "windsurf",
        "agent_format": "markdown_frontmatter",
        "supports_slash_commands": True,
    },
    "copilot": {
        "name": "GitHub Copilot",
        "folder": ".github/",
        "agents_dir": ".github/agents/",
        "commands_dir": ".github/prompts/",
        "context_file": "COPILOT.md",
        "install_url": None,  # IDE-based
        "requires_cli": False,
        "cli_command": None,
        "agent_format": "markdown",
        "supports_slash_commands": False,  # Via prompts
    },
}

def get_tool_config(tool_name: str) -> dict:
    """Get configuration for a specific tool."""
    if tool_name not in TOOL_CONFIG:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOL_CONFIG[tool_name]

def list_supported_tools() -> List[str]:
    """List all supported tools."""
    return list(TOOL_CONFIG.keys())

def detect_installed_tool() -> Optional[str]:
    """Auto-detect which AI coding tool is installed."""
    for tool_name, config in TOOL_CONFIG.items():
        if config["requires_cli"] and config["cli_command"]:
            if shutil.which(config["cli_command"]):
                return tool_name
    return None
```

### Phase 3: Build Tool-Specific Formatters (2 days)

**Goal:** Create formatter classes for each supported tool.

**Tasks:**
- [ ] Create `guardkit/formatters/base.py` (abstract base)
- [ ] Create `guardkit/formatters/claude.py`
- [ ] Create `guardkit/formatters/cursor.py`
- [ ] Create `guardkit/formatters/windsurf.py`
- [ ] Create `guardkit/formatters/copilot.py`
- [ ] Create `guardkit/formatters/universal.py` (AGENTS.md)

**File Structure:**
```
guardkit/
├── formatters/
│   ├── __init__.py
│   ├── base.py              # Abstract formatter
│   ├── claude.py            # Claude Code formatter
│   ├── cursor.py            # Cursor formatter
│   ├── windsurf.py          # Windsurf formatter
│   ├── copilot.py           # GitHub Copilot formatter
│   └── universal.py         # AGENTS.md generator
```

**Base Formatter:**
```python
# guardkit/formatters/base.py

from abc import ABC, abstractmethod
from typing import List
from guardkit.core.models import Agent, Template

class BaseFormatter(ABC):
    """Abstract base class for tool-specific formatters."""
    
    def __init__(self, tool_config: dict):
        self.config = tool_config
    
    @abstractmethod
    def format_agent(self, agent: Agent) -> str:
        """Format an agent for this tool."""
        pass
    
    @abstractmethod
    def format_context_file(self, template_info: dict) -> str:
        """Generate the main context file (CLAUDE.md, .cursorrules, etc)."""
        pass
    
    @abstractmethod
    def get_agent_file_path(self, agent_name: str) -> str:
        """Get the output path for an agent file."""
        pass
    
    def format_all_agents(self, agents: List[Agent]) -> dict:
        """
        Format all agents for this tool.
        Returns dict of {file_path: content}
        """
        output = {}
        for agent in agents:
            path = self.get_agent_file_path(agent.name)
            content = self.format_agent(agent)
            output[path] = content
        return output
```

**Claude Formatter:**
```python
# guardkit/formatters/claude.py

class ClaudeFormatter(BaseFormatter):
    """Formatter for Claude Code."""
    
    def format_agent(self, agent: Agent) -> str:
        """Format agent with YAML frontmatter."""
        return f"""---
name: {agent.name}
description: {agent.description}
priority: {agent.priority}
technologies:
{self._format_yaml_list(agent.technologies)}
---

# {self._format_title(agent.name)}

{agent.content}

## Technologies

{self._format_bullet_list(agent.technologies)}

## Usage in GuardKit

This agent is automatically invoked during `/task-work` when the task involves {agent.name.replace('-', ' ')}.
"""
    
    def format_context_file(self, template_info: dict) -> str:
        """Generate CLAUDE.md"""
        return f"""# {template_info['name']} Template

## Overview

{template_info['description']}

## Technology Stack

{self._format_bullet_list(template_info['technologies'])}

## Agents

{len(template_info['agents'])} specialized agents available:

{self._format_agent_list(template_info['agents'])}

## Templates

{len(template_info['templates'])} code templates included.

## Usage

Use `/task-create` to create tasks from specifications.
Use `/task-work` to implement tasks with AI assistance.
"""
    
    def get_agent_file_path(self, agent_name: str) -> str:
        """Return .claude/agents/agent-name.md"""
        return f"{self.config['agents_dir']}{agent_name}.md"
    
    def _format_yaml_list(self, items: List[str]) -> str:
        return "\n".join(f"  - {item}" for item in items)
    
    def _format_bullet_list(self, items: List[str]) -> str:
        return "\n".join(f"- {item}" for item in items)
```

**Cursor Formatter:**
```python
# guardkit/formatters/cursor.py

class CursorFormatter(BaseFormatter):
    """Formatter for Cursor (single .cursorrules file)."""
    
    def format_agent(self, agent: Agent) -> str:
        """Format agent as markdown section."""
        return f"""
## {self._format_title(agent.name)}

**Description**: {agent.description}

**Technologies**: {', '.join(agent.technologies)}

**Priority**: {agent.priority}

{agent.content}

---
"""
    
    def format_context_file(self, template_info: dict) -> str:
        """Generate .cursorrules with all agents."""
        agents_content = "\n".join(
            self.format_agent(agent) 
            for agent in template_info['agents']
        )
        
        return f"""# {template_info['name']} Template

## Overview

{template_info['description']}

## Technology Stack

{', '.join(template_info['technologies'])}

## Available Agents

{agents_content}

## Usage

Reference specific agents using @ mentions:
- @{template_info['agents'][0].name}
- Use natural language to describe tasks
- Cursor will select appropriate agents automatically
"""
    
    def format_all_agents(self, agents: List[Agent]) -> dict:
        """Cursor uses single file, return context file only."""
        # For Cursor, all agents go into .cursorrules
        return {}  # Handled by format_context_file
    
    def get_agent_file_path(self, agent_name: str) -> str:
        """Cursor doesn't use separate agent files."""
        return None
```

**Universal Formatter:**
```python
# guardkit/formatters/universal.py

class UniversalFormatter:
    """Creates AGENTS.md for any tool."""
    
    def create_agents_md(self, template_info: dict) -> str:
        """Create universal AGENTS.md file."""
        return f"""# {template_info['name']} - Agent Reference

## Overview

This template includes {len(template_info['agents'])} specialized agents for {template_info['stack']} development.

## Available Agents

{self._format_agents_reference(template_info['agents'])}

## How to Use

### With Claude Code
```
/task-create "Your task description"
/task-work TASK-001
```

### With Cursor
```
@codebase Create task: Your task description
```

### With Windsurf
```
/task Create task: Your task description
```

### With GitHub Copilot
Describe your task in natural language and reference this file.

### Manual Workflow
1. Review the agent descriptions above
2. Identify which agents are relevant to your task
3. Manually invoke or reference them in your AI tool
4. Follow the guidance provided by each agent

## Templates Included

{len(template_info['templates'])} code templates are available in this template.

## Technologies

{', '.join(template_info['technologies'])}
"""
    
    def _format_agents_reference(self, agents: List[Agent]) -> str:
        sections = []
        for agent in agents:
            sections.append(f"""### {agent.name}

**Description**: {agent.description}

**Technologies**: {', '.join(agent.technologies)}

**When to use**: {agent.content.split('\n\n')[0]}
""")
        return "\n\n".join(sections)
```

### Phase 4: Build Pre-Packaged Templates (1 day)

**Goal:** Create distributable template packages like SpecKit.

**Tasks:**
- [ ] Create `scripts/build-templates.sh`
- [ ] Set up GitHub release workflow
- [ ] Generate template packages for each tool
- [ ] Test package extraction

**Build Script:**
```bash
#!/bin/bash
# scripts/build-templates.sh

set -e

VERSION="v1.0.0"
DIST_DIR="dist/templates"
TOOLS=("claude" "cursor" "windsurf" "copilot")

echo "Building template packages for version $VERSION"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

for tool in "${TOOLS[@]}"; do
    echo "Building $tool template..."
    
    # Create temp directory with tool-specific structure
    TEMP_DIR="$(mktemp -d)"
    
    # Generate tool-specific structure
    python -m guardkit.scripts.generate_template_structure \
        --tool "$tool" \
        --output "$TEMP_DIR" \
        --version "$VERSION"
    
    # Create zip package
    PACKAGE_NAME="guardkit-template-${tool}-${VERSION}.zip"
    (cd "$TEMP_DIR" && zip -r "$DIST_DIR/$PACKAGE_NAME" .)
    
    echo "✅ Created $PACKAGE_NAME"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
done

echo "✅ All template packages built in $DIST_DIR"
```

**Package Contents Example (Claude):**
```
guardkit-template-claude-v1.0.0.zip
├── .claude/
│   ├── agents/
│   │   └── .gitkeep
│   └── commands/
│       ├── task-create.md
│       └── task-work.md
├── templates/
│   └── README.md
├── CLAUDE.md.template
├── AGENTS.md.template
└── .gitignore
```

### Phase 5: Update CLI (3 days)

**Goal:** Integrate multi-tool support into guardkit CLI.

**Tasks:**
- [ ] Add `--tool` option to `template-create` command
- [ ] Implement tool detection (optional)
- [ ] Update command flow to use formatters
- [ ] Add validation for tool-specific requirements
- [ ] Update help text and documentation

**Updated CLI:**
```python
# guardkit/cli.py

import click
from pathlib import Path
from guardkit.config.tools import TOOL_CONFIG, detect_installed_tool
from guardkit.core.template_creator import TemplateCreator
from guardkit.formatters import get_formatter
from guardkit.formatters.universal import UniversalFormatter

@cli.command()
@click.option(
    '--tool', 
    type=click.Choice(['claude', 'cursor', 'windsurf', 'copilot']),
    help='AI coding tool to generate template for'
)
@click.option(
    '--codebase',
    required=True,
    type=click.Path(exists=True),
    help='Path to existing codebase to analyze'
)
@click.option(
    '--name',
    required=True,
    help='Name for the new template'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Output directory (default: ~/.guardkit/templates/{name})'
)
def template_create(tool: str, codebase: str, name: str, output: str):
    """
    Create a GuardKit template from an existing codebase.
    
    Analyzes the codebase and generates:
    - Specialized agents for the technology stack
    - Code templates and patterns
    - Tool-specific configuration files
    """
    
    # Auto-detect tool if not specified
    if not tool:
        detected = detect_installed_tool()
        if detected:
            click.echo(f"Auto-detected tool: {detected}")
            tool = detected
        else:
            click.echo("No AI coding tool detected. Please specify --tool")
            tool = click.prompt(
                'Select tool',
                type=click.Choice(['claude', 'cursor', 'windsurf', 'copilot'])
            )
    
    # Get tool configuration
    tool_config = TOOL_CONFIG[tool]
    click.echo(f"\n🔧 Creating template for {tool_config['name']}")
    
    # Set output directory
    if not output:
        output = Path.home() / '.guardkit' / 'templates' / name
    output = Path(output)
    
    # Phase 1: Analyze codebase (tool-agnostic)
    click.echo(f"\n📊 Analyzing codebase at {codebase}...")
    creator = TemplateCreator()
    
    with click.progressbar(
        length=100,
        label='Analyzing files'
    ) as bar:
        analysis = creator.analyze_codebase(codebase)
        bar.update(30)
        
        # Phase 2: Generate agents (AI-powered, tool-agnostic)
        click.echo(f"\n🤖 Generating {analysis.stack} agents...")
        agents = creator.generate_agents(analysis)
        bar.update(30)
        
        # Phase 3: Generate templates (tool-agnostic)
        click.echo(f"\n📝 Extracting templates...")
        templates = creator.generate_templates(analysis)
        bar.update(20)
        
        # Phase 4: Format for specific tool
        click.echo(f"\n🎨 Formatting for {tool_config['name']}...")
        formatter = get_formatter(tool)
        bar.update(20)
    
    # Create output directory structure
    output.mkdir(parents=True, exist_ok=True)
    
    # Write agents (tool-specific format)
    agent_files = formatter.format_all_agents(agents)
    for file_path, content in agent_files.items():
        full_path = output / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    # Write context file (tool-specific)
    context_content = formatter.format_context_file({
        'name': name,
        'description': f'Template for {analysis.stack} development',
        'stack': analysis.stack,
        'technologies': analysis.technologies,
        'agents': agents,
        'templates': templates,
    })
    context_file = output / tool_config['context_file']
    context_file.write_text(context_content)
    
    # Write universal AGENTS.md (works with any tool)
    universal = UniversalFormatter()
    agents_md = universal.create_agents_md({
        'name': name,
        'stack': analysis.stack,
        'technologies': analysis.technologies,
        'agents': agents,
        'templates': templates,
    })
    (output / 'AGENTS.md').write_text(agents_md)
    
    # Write templates
    templates_dir = output / 'templates'
    templates_dir.mkdir(exist_ok=True)
    for template in templates:
        template_path = templates_dir / template.path
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template.content)
    
    # Success message
    click.echo(f"\n✅ Template created successfully!")
    click.echo(f"\n📂 Output: {output}")
    click.echo(f"\n📊 Generated:")
    click.echo(f"   • {len(agents)} agents")
    click.echo(f"   • {len(templates)} templates")
    click.echo(f"   • 1 {tool_config['context_file']} file")
    click.echo(f"   • 1 AGENTS.md (universal)")
    
    if tool_config['supports_slash_commands']:
        click.echo(f"\n💡 Usage in {tool_config['name']}:")
        click.echo(f"   /task-create \"Your task description\"")
        click.echo(f"   /task-work TASK-001")
    else:
        click.echo(f"\n💡 Usage in {tool_config['name']}:")
        click.echo(f"   Reference AGENTS.md for agent descriptions")
        click.echo(f"   Use natural language to describe tasks")


def get_formatter(tool_name: str):
    """Factory function to get the right formatter."""
    formatters = {
        'claude': lambda: ClaudeFormatter(TOOL_CONFIG['claude']),
        'cursor': lambda: CursorFormatter(TOOL_CONFIG['cursor']),
        'windsurf': lambda: WindsurfFormatter(TOOL_CONFIG['windsurf']),
        'copilot': lambda: CopilotFormatter(TOOL_CONFIG['copilot']),
    }
    
    if tool_name not in formatters:
        raise ValueError(f"No formatter for tool: {tool_name}")
    
    return formatters[tool_name]()
```

---

## Code Examples

### Example: Creating a Template for Different Tools

```bash
# For Claude Code
guardkit template-create \
    --tool claude \
    --codebase ~/projects/my-maui-app \
    --name maui-enterprise

# For Cursor
guardkit template-create \
    --tool cursor \
    --codebase ~/projects/my-maui-app \
    --name maui-enterprise

# For Windsurf
guardkit template-create \
    --tool windsurf \
    --codebase ~/projects/my-maui-app \
    --name maui-enterprise

# Auto-detect tool
guardkit template-create \
    --codebase ~/projects/my-maui-app \
    --name maui-enterprise
```

### Example: Generated Output Structure

**For Claude Code:**
```
~/.guardkit/templates/maui-enterprise/
├── .claude/
│   └── agents/
│       ├── repository-pattern-specialist.md
│       ├── mvvm-specialist.md
│       └── ... (12 agents)
├── templates/
│   ├── ConfigurationRepository.cs.template
│   ├── ViewModel.cs.template
│   └── ... (17 templates)
├── CLAUDE.md
└── AGENTS.md
```

**For Cursor:**
```
~/.guardkit/templates/maui-enterprise/
├── .cursorrules              # ALL agents in one file
├── templates/
│   ├── ConfigurationRepository.cs.template
│   ├── ViewModel.cs.template
│   └── ... (17 templates)
└── AGENTS.md
```

### Example: Using Generated Template

**Claude Code:**
```bash
# Copy to project
cp -r ~/.guardkit/templates/maui-enterprise/.claude ~/my-project/
cp ~/.guardkit/templates/maui-enterprise/CLAUDE.md ~/my-project/

# Use in Claude
cd ~/my-project
claude

# In Claude:
/task-create "Implement user authentication with repository pattern"
```

**Cursor:**
```bash
# Copy to project
cp ~/.guardkit/templates/maui-enterprise/.cursorrules ~/my-project/

# Use in Cursor
@codebase Implement user authentication with repository pattern
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_formatters.py

def test_claude_formatter():
    """Test Claude formatter produces correct output."""
    agent = Agent(
        name="test-specialist",
        description="Test agent",
        priority=5,
        technologies=["Python", "FastAPI"],
        content="Test content"
    )
    
    formatter = ClaudeFormatter(TOOL_CONFIG['claude'])
    output = formatter.format_agent(agent)
    
    assert "---" in output  # Has frontmatter
    assert "name: test-specialist" in output
    assert "# Test Specialist" in output
    assert "/task-work" in output


def test_cursor_formatter():
    """Test Cursor formatter produces correct output."""
    agent = Agent(
        name="test-specialist",
        description="Test agent",
        priority=5,
        technologies=["Python"],
        content="Test content"
    )
    
    formatter = CursorFormatter(TOOL_CONFIG['cursor'])
    output = formatter.format_agent(agent)
    
    assert "## Test Specialist" in output
    assert "**Technologies**: Python" in output
    assert "---" in output  # Section separator
```

### Integration Tests

```python
# tests/test_integration.py

def test_full_template_creation_claude():
    """Test complete template creation for Claude."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test codebase
        test_codebase = create_test_codebase(tmpdir)
        
        # Run template creation
        result = runner.invoke(cli, [
            'template-create',
            '--tool', 'claude',
            '--codebase', test_codebase,
            '--name', 'test-template',
            '--output', tmpdir
        ])
        
        assert result.exit_code == 0
        
        # Verify structure
        assert (Path(tmpdir) / '.claude' / 'agents').exists()
        assert (Path(tmpdir) / 'CLAUDE.md').exists()
        assert (Path(tmpdir) / 'AGENTS.md').exists()
        
        # Verify content
        claude_md = (Path(tmpdir) / 'CLAUDE.md').read_text()
        assert 'test-template' in claude_md
```

### Manual Testing Checklist

- [ ] Create template with `--tool claude`
- [ ] Verify `.claude/agents/` contains agent files
- [ ] Verify `CLAUDE.md` is generated
- [ ] Verify `AGENTS.md` is generated
- [ ] Test in actual Claude Code
- [ ] Repeat for Cursor
- [ ] Repeat for Windsurf
- [ ] Repeat for Copilot
- [ ] Test auto-detection
- [ ] Test with invalid tool name
- [ ] Test with non-existent codebase

---

## Rollout Plan

### Phase 1: Claude Code (Current State)

**Timeline**: Already complete  
**Goal**: Maintain current functionality

- ✅ Claude Code templates working
- ✅ Agent generation working
- ✅ AI-powered enhancement working

### Phase 2: Add Cursor Support (Week 1)

**Priority**: High (most popular alternative to Claude)

**Tasks:**
1. Implement CursorFormatter
2. Test with real Cursor installation
3. Document Cursor-specific usage
4. Update README

**Release**: v1.1.0 - "Cursor Support"

### Phase 3: Add Windsurf + Copilot (Week 2-3)

**Priority**: Medium (expanding tool support)

**Tasks:**
1. Implement WindsurfFormatter
2. Implement CopilotFormatter
3. Test with real installations
4. Document usage for both tools
5. Update README

**Release**: v1.2.0 - "Multi-Tool Support"

### Phase 4: Community Contributions (Ongoing)

**Priority**: Low (nice to have)

**Tasks:**
1. Document how to add new tools
2. Create CONTRIBUTING.md
3. Accept PRs for new tool formatters
4. Test community-contributed tools

**Tools to consider:**
- OpenCode
- Codex
- Amazon Q Developer
- Cody
- Tabnine
- Others as they emerge

---

## Success Metrics

### Technical Metrics

- ✅ Template creation works for 4 tools (Claude, Cursor, Windsurf, Copilot)
- ✅ Core logic is 100% tool-agnostic
- ✅ Adding a new tool requires <200 lines of code
- ✅ All tests pass for each tool
- ✅ Pre-built packages available in releases

### User Metrics

- ✅ Users can create templates with any supported tool
- ✅ Templates work correctly in target AI tools
- ✅ Documentation is clear for each tool
- ✅ Users can switch between tools easily

### Quality Metrics

- ✅ Generated agents are high quality (8+/10)
- ✅ Templates are accurate to codebase
- ✅ Tool-specific formatting is correct
- ✅ No hard-coded tool assumptions in core

---

## References

### SpecKit Resources

- **GitHub Repo**: https://github.com/github/spec-kit
- **AGENTS.md**: https://github.com/github/spec-kit/blob/main/AGENTS.md
- **Release Packages**: https://github.com/github/spec-kit/releases

### Key Files to Reference

- `src/specify_cli/__init__.py` - AGENT_CONFIG dictionary
- `.github/workflows/scripts/create-release-packages.sh` - Package generation
- Templates for each agent in releases

### GuardKit Project Files

- `/mnt/project/Creating_a_System-Wide_Claude_Code_Installation_Architecture__Separating_Global_Methodology_from_Project_Implementation.md`
- `/mnt/project/SpecKit_and_OpenSpec_Analysis__AI_Coding_Frameworks_vs_Task_Management_Integration.md`

---

## Appendix: Quick Reference

### TOOL_CONFIG Keys

```python
{
    "name": "Display name",
    "folder": "Root config folder",
    "agents_dir": "Where agents go",
    "commands_dir": "Where commands go (or None)",
    "context_file": "Main config file name",
    "install_url": "Download URL (or None)",
    "requires_cli": True/False,
    "cli_command": "Command to check",
    "agent_format": "Format type",
    "supports_slash_commands": True/False,
}
```

### Common Commands

```bash
# Create template
guardkit template-create --tool claude --codebase ./my-app --name my-template

# List supported tools
guardkit tools list

# Check tool installation
guardkit tools check

# Build release packages
./scripts/build-templates.sh
```

### Directory Structure Reference

```
Template Output:
├── .{tool}/              # Tool-specific config
│   └── agents/           # Agent definitions (or single file)
├── templates/            # Universal code templates
├── {TOOL}.md            # Tool context file
└── AGENTS.md            # Universal fallback
```

---

## Conclusion

This implementation plan provides a **clear, proven path** to multi-tool support for GuardKit. By adopting SpecKit's architectural patterns, we can:

1. **Maintain simplicity** - Core logic stays unchanged
2. **Scale easily** - Adding tools is straightforward
3. **Ensure quality** - Proven approach with 42.5k stars
4. **Ship incrementally** - Start with Claude, add tools gradually

**Estimated Total Effort**: 8 working days  
**Complexity**: Medium (5/10)  
**Risk**: Low (proven architecture)

The key insight: **Keep template generation universal, only vary the final output format**. This is exactly what SpecKit does, and it works brilliantly.

---

**Document Version**: 1.0  
**Last Updated**: November 19, 2025  
**Status**: Ready for Implementation
