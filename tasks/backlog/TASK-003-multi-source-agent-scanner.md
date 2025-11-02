---
id: TASK-003
title: Multi-Source Agent Scanner
status: backlog
created: 2025-11-01T23:00:00Z
priority: high
complexity: 4
estimated_hours: 8
tags: [agent-discovery, multi-source, scanning]
epic: EPIC-001
feature: agent-discovery
dependencies: []
blocks: [TASK-004A, TASK-009]
---

# TASK-003: Multi-Source Agent Scanner

## Objective

Scan **three agent sources** in priority order to build complete inventory of available agents:
1. User's custom agents (`.claude/agents/`) - HIGHEST priority
2. Template agents (from template being used/generated) - HIGH priority
3. Global built-in agents (`installer/global/agents/`) - MEDIUM priority

**Key Principle**: User's custom agents always take precedence

## Context

**From Agent Strategy (Approved)**:
- Agent Priority: User Custom > Template > Global > AI-Generated > External
- User's agents have highest priority (always preferred over generic equivalents)
- Need complete inventory before AI generation (TASK-004A)

## Acceptance Criteria

- [ ] Scan `.claude/agents/` directory (user's custom agents)
- [ ] Scan template agents if using/generating from template
- [ ] Scan `installer/global/agents/` (built-in agents)
- [ ] Parse agent markdown frontmatter (name, description, tools, tags)
- [ ] Return prioritized inventory (user > template > global)
- [ ] Handle missing directories gracefully
- [ ] Detect duplicate agents (same name across sources)
- [ ] Preserve source information (which directory agent came from)
- [ ] Unit tests for all three sources
- [ ] Performance: Scan 100 agents in <1 second

## Implementation

```python
# src/commands/template_create/agent_scanner.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
import frontmatter

@dataclass
class AgentDefinition:
    """Discovered agent definition"""
    name: str
    description: str
    tools: List[str]
    tags: List[str]
    source: str  # "custom", "template", "global"
    source_path: Path
    priority: int  # 3=custom, 2=template, 1=global
    full_definition: str  # Complete markdown content

@dataclass
class AgentInventory:
    """Complete inventory of available agents"""
    custom_agents: List[AgentDefinition]  # .claude/agents/
    template_agents: List[AgentDefinition]  # template/agents/
    global_agents: List[AgentDefinition]  # installer/global/agents/

    def all_agents(self) -> List[AgentDefinition]:
        """Return all agents in priority order"""
        return (
            self.custom_agents +
            self.template_agents +
            self.global_agents
        )

    def find_by_name(self, name: str) -> Optional[AgentDefinition]:
        """Find agent by name (returns highest priority match)"""
        for agent in self.all_agents():
            if agent.name == name:
                return agent
        return None

    def has_agent(self, name: str) -> bool:
        """Check if agent exists (any source)"""
        return self.find_by_name(name) is not None

    def get_by_source(self, source: str) -> List[AgentDefinition]:
        """Get all agents from specific source"""
        return [a for a in self.all_agents() if a.source == source]

class MultiSourceAgentScanner:
    """Scan multiple agent sources in priority order"""

    def __init__(
        self,
        custom_path: Path = None,
        template_path: Path = None,
        global_path: Path = None
    ):
        """
        Initialize scanner

        Args:
            custom_path: Path to .claude/agents/ (default: current project)
            template_path: Path to template/agents/ (default: None if not using template)
            global_path: Path to installer/global/agents/ (default: auto-detect)
        """
        self.custom_path = custom_path or Path(".claude/agents")
        self.template_path = template_path  # May be None
        self.global_path = global_path or self._find_global_agents_path()

    def scan(self) -> AgentInventory:
        """
        Scan all agent sources

        Returns:
            AgentInventory with agents from all sources
        """
        print("📦 Scanning agent sources...")

        # Scan user's custom agents (highest priority)
        custom = self._scan_directory(
            self.custom_path,
            source="custom",
            priority=3
        )
        if custom:
            print(f"  ✓ Found {len(custom)} custom agents in .claude/agents/")

        # Scan template agents (if using template)
        template = []
        if self.template_path and self.template_path.exists():
            template = self._scan_directory(
                self.template_path,
                source="template",
                priority=2
            )
            if template:
                print(f"  ✓ Found {len(template)} template-specific agents")

        # Scan global built-in agents
        global_agents = self._scan_directory(
            self.global_path,
            source="global",
            priority=1
        )
        if global_agents:
            print(f"  ✓ Found {len(global_agents)} global agents")

        # Create inventory
        inventory = AgentInventory(
            custom_agents=custom,
            template_agents=template,
            global_agents=global_agents
        )

        # Report duplicates (inform user)
        self._report_duplicates(inventory)

        total = len(inventory.all_agents())
        print(f"\n📊 Total: {total} agents available")

        return inventory

    def _scan_directory(
        self,
        directory: Path,
        source: str,
        priority: int
    ) -> List[AgentDefinition]:
        """
        Scan single directory for agent definitions

        Args:
            directory: Directory to scan
            source: Source identifier (custom/template/global)
            priority: Priority level (3=highest, 1=lowest)

        Returns:
            List of discovered agents
        """
        if not directory.exists():
            return []

        agents = []

        # Find all .md files
        for md_file in directory.glob("*.md"):
            try:
                agent = self._parse_agent_file(md_file, source, priority)
                if agent:
                    agents.append(agent)
            except Exception as e:
                print(f"  ⚠️  Failed to parse {md_file.name}: {e}")
                continue

        return agents

    def _parse_agent_file(
        self,
        file_path: Path,
        source: str,
        priority: int
    ) -> Optional[AgentDefinition]:
        """
        Parse agent markdown file

        Args:
            file_path: Path to .md file
            source: Source identifier
            priority: Priority level

        Returns:
            AgentDefinition if valid, None otherwise
        """
        # Read file with frontmatter
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract metadata from frontmatter
        metadata = post.metadata

        # Required fields
        name = metadata.get('name', file_path.stem)
        description = metadata.get('description', '')

        if not name or not description:
            return None

        # Optional fields
        tools = metadata.get('tools', [])
        tags = metadata.get('tags', [])

        # Full content (including frontmatter and body)
        full_definition = file_path.read_text(encoding='utf-8')

        return AgentDefinition(
            name=name,
            description=description,
            tools=tools,
            tags=tags,
            source=source,
            source_path=file_path,
            priority=priority,
            full_definition=full_definition
        )

    def _find_global_agents_path(self) -> Path:
        """Auto-detect path to installer/global/agents/"""
        # Try common locations
        candidates = [
            Path("installer/global/agents"),
            Path.cwd() / "installer/global/agents",
            Path.home() / ".agentecflow/global/agents",
        ]

        for path in candidates:
            if path.exists():
                return path

        # Default (may not exist yet)
        return Path("installer/global/agents")

    def _report_duplicates(self, inventory: AgentInventory):
        """Report agents with same name across different sources"""

        # Build name -> sources map
        name_sources: Dict[str, List[str]] = {}

        for agent in inventory.all_agents():
            if agent.name not in name_sources:
                name_sources[agent.name] = []
            name_sources[agent.name].append(agent.source)

        # Find duplicates
        duplicates = {
            name: sources
            for name, sources in name_sources.items()
            if len(sources) > 1
        }

        if duplicates:
            print("\n💡 Agent Priority:")
            for name, sources in duplicates.items():
                # Custom always wins
                if "custom" in sources:
                    print(f"  • {name}: Using your custom version")
                elif "template" in sources:
                    print(f"  • {name}: Using template version")
```

## Usage Examples

### Example 1: Scan All Sources

```python
scanner = MultiSourceAgentScanner()
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

print(f"Custom agents: {len(inventory.custom_agents)}")
print(f"Template agents: {len(inventory.template_agents)}")
print(f"Global agents: {len(inventory.global_agents)}")
```

### Example 2: Find Specific Agent

```python
inventory = scanner.scan()

# Find agent (returns highest priority match)
agent = inventory.find_by_name("react-specialist")

if agent:
    print(f"Found: {agent.name}")
    print(f"Source: {agent.source}")  # "custom" (highest priority)
    print(f"Description: {agent.description}")
    print(f"Tools: {', '.join(agent.tools)}")
```

### Example 3: Check for Duplicates

```python
inventory = scanner.scan()

# Check if agent exists
if inventory.has_agent("maui-specialist"):
    agent = inventory.find_by_name("maui-specialist")
    print(f"Using {agent.source} version: {agent.source_path}")
else:
    print("Agent not found - will need to generate")
```

## Testing Strategy

```python
# tests/test_multi_source_scanner.py

def test_scan_custom_agents():
    """Test scanning user's custom agents"""
    # Create test custom agents
    custom_dir = Path("tests/fixtures/custom-agents")
    custom_dir.mkdir(parents=True, exist_ok=True)

    # Create test agent file
    agent_file = custom_dir / "my-custom-agent.md"
    agent_file.write_text("""---
name: my-custom-agent
description: My custom agent
tools: [Read, Write]
tags: [custom]
---

# My Custom Agent

This is my custom agent.
""")

    scanner = MultiSourceAgentScanner(custom_path=custom_dir)
    inventory = scanner.scan()

    assert len(inventory.custom_agents) == 1
    assert inventory.custom_agents[0].name == "my-custom-agent"
    assert inventory.custom_agents[0].source == "custom"
    assert inventory.custom_agents[0].priority == 3

def test_priority_order():
    """Test that custom agents take precedence"""
    # Create duplicate agent in custom and global
    # ... setup fixtures

    scanner = MultiSourceAgentScanner(
        custom_path=custom_dir,
        global_path=global_dir
    )
    inventory = scanner.scan()

    # Find duplicate agent
    agent = inventory.find_by_name("react-specialist")

    # Should return custom version (highest priority)
    assert agent.source == "custom"
    assert agent.priority == 3

def test_missing_directories():
    """Test graceful handling of missing directories"""
    scanner = MultiSourceAgentScanner(
        custom_path=Path("/nonexistent/custom"),
        template_path=Path("/nonexistent/template"),
        global_path=Path("/nonexistent/global")
    )

    # Should not crash
    inventory = scanner.scan()

    assert len(inventory.all_agents()) == 0

def test_invalid_agent_files():
    """Test handling of malformed agent files"""
    # Create directory with invalid files
    # ... setup fixtures with missing frontmatter

    scanner = MultiSourceAgentScanner(custom_path=test_dir)
    inventory = scanner.scan()

    # Should skip invalid files and continue
    assert len(inventory.custom_agents) >= 0  # No crash
```

## Integration with Template Creation

```python
# In /template-create command
def template_create():
    # Q&A session
    answers = qa_session.run()

    # AI analysis
    analysis = analyzer.analyze(answers.codebase_path)

    # Scan existing agents
    scanner = MultiSourceAgentScanner()
    inventory = scanner.scan()

    # AI generation (TASK-004A) uses inventory
    generator = AIAgentGenerator(inventory=inventory)
    generated_agents = generator.generate(analysis)

    # ... continue with template generation
```

## Definition of Done

- [ ] Multi-source scanning implemented (custom, template, global)
- [ ] Agent file parsing with frontmatter
- [ ] Priority ordering (custom > template > global)
- [ ] Duplicate detection and reporting
- [ ] Missing directory handling (graceful)
- [ ] AgentInventory data structure complete
- [ ] Helper methods (find_by_name, has_agent, get_by_source)
- [ ] Unit tests passing (>85% coverage)
- [ ] Performance test (<1s for 100 agents)
- [ ] Integration with TASK-004A verified

**Estimated Time**: 8 hours | **Complexity**: 4/10 | **Priority**: HIGH

## Benefits

- ✅ Respects user's custom work (highest priority)
- ✅ Template-aware (includes template agents)
- ✅ Complete inventory (all sources scanned)
- ✅ Duplicate detection (informs user)
- ✅ Fast (efficient directory scanning)
- ✅ Extensible (easy to add more sources)

---

**Created**: 2025-11-01
**Status**: ✅ **APPROVED** - Ready for implementation
**Dependencies**: None (first task in agent system)
**Blocks**: TASK-004A (AI Generator), TASK-009 (Orchestration)
