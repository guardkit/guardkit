"""
Multi-Source Agent Scanner

Scans agent definitions from multiple sources in priority order and builds
a complete inventory of available agents.

TASK-PD-004: Enhanced to exclude -ext.md extended files from discovery
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
import frontmatter


def is_extended_file(path: Path) -> bool:
    """
    Check if file is an extended content file.

    TASK-PD-004: Extended files end with -ext.md and should be excluded
    from agent discovery. They are supplementary content loaded on-demand.

    Args:
        path: Path to check

    Returns:
        True if file is an extended file (-ext.md), False otherwise

    Examples:
        >>> is_extended_file(Path("task-manager-ext.md"))
        True
        >>> is_extended_file(Path("task-manager.md"))
        False
        >>> is_extended_file(Path("my-ext-agent.md"))
        False  # 'ext' not at end of stem
    """
    return path.stem.endswith('-ext')


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
    global_agents: List[AgentDefinition]  # installer/core/agents/

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
        custom_path: Optional[Path] = None,
        template_path: Optional[Path] = None,
        global_path: Optional[Path] = None
    ):
        """
        Initialize scanner

        Args:
            custom_path: Path to .claude/agents/ (default: current project)
            template_path: Path to template/agents/ (default: None if not using template)
            global_path: Path to installer/core/agents/ (default: auto-detect)
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

        TASK-PD-004: Extended files (-ext.md) are excluded from discovery.
        Only core agent files are returned.

        Args:
            directory: Directory to scan
            source: Source identifier (custom/template/global)
            priority: Priority level (3=highest, 1=lowest)

        Returns:
            List of discovered agents (excluding extended files)
        """
        if not directory.exists():
            return []

        agents = []

        # Find all .md files (excluding extended files)
        for md_file in directory.glob("*.md"):
            # TASK-PD-004: Skip extended files from discovery
            if is_extended_file(md_file):
                continue

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
        """Auto-detect path to installer/core/agents/"""
        # Try common locations
        candidates = [
            Path("installer/core/agents"),
            Path.cwd() / "installer/core/agents",
            Path.home() / ".agentecflow/global/agents",
        ]

        for path in candidates:
            if path.exists():
                return path

        # Default (may not exist yet)
        return Path("installer/core/agents")

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
