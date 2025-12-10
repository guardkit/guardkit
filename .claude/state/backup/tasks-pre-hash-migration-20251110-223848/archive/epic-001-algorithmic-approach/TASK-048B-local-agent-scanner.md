---
id: TASK-048B
title: Local Agent Scanner
status: backlog
created: 2025-11-01T19:00:00Z
priority: high
complexity: 4
estimated_hours: 4
tags: [agent-discovery, local-agents, reusability]
epic: EPIC-001
feature: agent-discovery
dependencies: []
blocks: [TASK-050]
---

# TASK-048B: Local Agent Scanner

## Objective

Implement local agent scanner to discover and catalog existing guardkit agents from `installer/core/agents/` directory, ensuring these battle-tested agents are prioritized in template creation.

**Problem:** 15 existing guardkit agents are ignored by current design
**Solution:** Local-first agent discovery with bonus scoring

## Acceptance Criteria

- [ ] Scan `installer/core/agents/` directory
- [ ] Parse agent markdown files (metadata + capabilities)
- [ ] Extract: name, description, tools, technology tags, specializations
- [ ] Catalog all 15+ existing agents
- [ ] Validate agent format (ensure well-formed)
- [ ] Cache discovered agents (5-minute TTL)
- [ ] Support custom local agent directories
- [ ] Integration with TASK-050 (matching algorithm)
- [ ] Unit tests for agent parsing
- [ ] Documentation of agent format

## Existing Agents to Discover

From `installer/core/agents/`:

1. **architectural-reviewer.md** - SOLID/DRY/YAGNI compliance review
2. **bdd-generator.md** - BDD/Gherkin scenario generation
3. **build-validator.md** - Compilation and dependency validation
4. **code-reviewer.md** - Code quality enforcement
5. **complexity-evaluator.md** - Task complexity evaluation
6. **database-specialist.md** - Data architecture patterns
7. **debugging-specialist.md** - Root cause analysis
8. **devops-specialist.md** - Infrastructure and CI/CD
9. **figma-react-orchestrator.md** - Figma → React conversion
10. **pattern-advisor.md** - Design pattern recommendations
11. **python-mcp-specialist.md** - MCP server development
12. **requirements-analyst.md** - EARS notation requirements
13. **security-specialist.md** - Security validation
14. **task-manager.md** - Workflow management
15. **test-orchestrator.md** - Test execution coordination
16. **test-verifier.md** - Test validation
17. **zeplin-maui-orchestrator.md** - Zeplin → MAUI conversion

## Implementation

### 1. Agent Metadata Parser

```python
# src/commands/template_create/local_agent_scanner.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from pathlib import Path
import re
from datetime import datetime, timedelta

@dataclass
class LocalAgentMetadata:
    """Metadata for a local agent"""
    name: str
    file_path: Path
    description: str
    tools: List[str]              # Tools available to agent
    technologies: Set[str]        # Technology tags (React, Python, etc.)
    specializations: Set[str]     # Specializations (testing, security, etc.)
    capabilities: List[str]       # Capabilities/use cases
    source: str = "local_global"  # Source identifier
    priority_bonus: int = 20      # Bonus score for local agents

@dataclass
class AgentScanResult:
    """Result of scanning for agents"""
    agents: List[LocalAgentMetadata]
    scan_time: datetime
    total_found: int
    valid_count: int
    invalid_files: List[str]

class LocalAgentScanner:
    """Scanner for local agent directory"""

    CACHE_TTL = timedelta(minutes=5)

    def __init__(
        self,
        agent_dir: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize scanner

        Args:
            agent_dir: Directory to scan (defaults to installer/core/agents)
            use_cache: Whether to use cache
        """
        if agent_dir is None:
            # Default to global agents
            agent_dir = Path(__file__).parent.parent.parent.parent / "installer" / "global" / "agents"

        self.agent_dir = agent_dir
        self.use_cache = use_cache
        self._cache: Optional[AgentScanResult] = None
        self._cache_time: Optional[datetime] = None

    def scan(self, force_refresh: bool = False) -> AgentScanResult:
        """
        Scan for local agents

        Args:
            force_refresh: Force refresh (ignore cache)

        Returns:
            AgentScanResult with discovered agents
        """
        # Check cache
        if (
            not force_refresh
            and self.use_cache
            and self._cache is not None
            and self._cache_time is not None
            and datetime.now() - self._cache_time < self.CACHE_TTL
        ):
            return self._cache

        # Scan directory
        agents = []
        invalid_files = []

        if not self.agent_dir.exists():
            return AgentScanResult(
                agents=[],
                scan_time=datetime.now(),
                total_found=0,
                valid_count=0,
                invalid_files=[]
            )

        for agent_file in self.agent_dir.glob("*.md"):
            try:
                metadata = self._parse_agent_file(agent_file)
                if metadata:
                    agents.append(metadata)
                else:
                    invalid_files.append(agent_file.name)
            except Exception as e:
                invalid_files.append(f"{agent_file.name} (error: {e})")

        result = AgentScanResult(
            agents=agents,
            scan_time=datetime.now(),
            total_found=len(agents) + len(invalid_files),
            valid_count=len(agents),
            invalid_files=invalid_files
        )

        # Update cache
        self._cache = result
        self._cache_time = datetime.now()

        return result

    def _parse_agent_file(self, file_path: Path) -> Optional[LocalAgentMetadata]:
        """
        Parse agent markdown file

        Agent file format:
        ```markdown
        # Agent Name

        Description paragraph

        ## Tools
        - Read, Write, Edit, Bash, etc.

        ## Specializations
        - Technology: React, TypeScript
        - Domain: Testing, Security
        ```
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return None

        # Extract name (first H1)
        name_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if not name_match:
            return None
        name = name_match.group(1).strip()

        # Extract description (paragraph after H1)
        desc_match = re.search(
            r'^#\s+.+?\n\n(.+?)(?:\n\n##|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract tools
        tools = self._extract_tools(content)

        # Extract technologies and specializations
        technologies, specializations = self._extract_tags(content)

        # Extract capabilities
        capabilities = self._extract_capabilities(content)

        return LocalAgentMetadata(
            name=name,
            file_path=file_path,
            description=description,
            tools=tools,
            technologies=technologies,
            specializations=specializations,
            capabilities=capabilities,
            source="local_global",
            priority_bonus=20  # Bonus for local agents
        )

    def _extract_tools(self, content: str) -> List[str]:
        """Extract tools from agent file"""
        tools = []

        # Look for Tools section or parenthetical mentions
        # Format 1: "## Tools\n- Read, Write, Edit"
        tools_section = re.search(
            r'##\s+Tools[:\s]*\n(.+?)(?:\n\n##|\Z)',
            content,
            re.MULTILINE | re.DOTALL
        )
        if tools_section:
            tool_text = tools_section.group(1)
            # Extract tools from list or comma-separated
            found_tools = re.findall(r'(?:^-\s+|\b)([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', tool_text)
            tools.extend(found_tools)

        # Format 2: "(Tools: Read, Write, Bash)"
        inline_tools = re.findall(r'\(Tools:\s*([^)]+)\)', content)
        for tool_list in inline_tools:
            tools.extend([t.strip() for t in tool_list.split(',')])

        return list(set(tools))  # Deduplicate

    def _extract_tags(self, content: str) -> tuple[Set[str], Set[str]]:
        """
        Extract technology and specialization tags

        Returns:
            (technologies, specializations)
        """
        technologies = set()
        specializations = set()

        # Technology tags: React, TypeScript, Python, etc.
        tech_keywords = {
            'React', 'TypeScript', 'JavaScript', 'Python', 'Go', 'Rust',
            'Java', 'C#', '.NET', 'MAUI', 'Ruby', 'PHP', 'Elixir',
            'FastAPI', 'Django', 'Flask', 'Next.js', 'Vue', 'Angular'
        }

        for keyword in tech_keywords:
            # Case-insensitive search
            if re.search(rf'\b{keyword}\b', content, re.IGNORECASE):
                technologies.add(keyword.lower())

        # Specialization tags from common patterns
        spec_patterns = {
            'testing': r'\b(?:test|testing|QA|quality)\b',
            'security': r'\b(?:security|authentication|authorization)\b',
            'architecture': r'\b(?:architecture|SOLID|design pattern)\b',
            'database': r'\b(?:database|SQL|NoSQL|data)\b',
            'devops': r'\b(?:devops|CI/CD|deployment|infrastructure)\b',
            'ui': r'\b(?:UI|UX|design|figma|zeplin)\b',
            'api': r'\b(?:API|REST|GraphQL|endpoint)\b',
        }

        for spec, pattern in spec_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                specializations.add(spec)

        return technologies, specializations

    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract capability descriptions"""
        capabilities = []

        # Look for bulleted lists under certain headers
        capability_headers = ['Capabilities', 'Use Cases', 'Responsibilities', 'Specializations']

        for header in capability_headers:
            section = re.search(
                rf'##\s+{header}[:\s]*\n(.+?)(?:\n\n##|\Z)',
                content,
                re.MULTILINE | re.DOTALL | re.IGNORECASE
            )
            if section:
                section_text = section.group(1)
                # Extract bullet points
                bullets = re.findall(r'^[\s-]*[-*]\s+(.+)$', section_text, re.MULTILINE)
                capabilities.extend(bullets)

        return capabilities[:10]  # Limit to top 10

    def get_agent_by_name(self, name: str) -> Optional[LocalAgentMetadata]:
        """Get specific agent by name"""
        result = self.scan()
        for agent in result.agents:
            if agent.name.lower() == name.lower():
                return agent
        return None

    def filter_by_technology(self, technology: str) -> List[LocalAgentMetadata]:
        """Filter agents by technology"""
        result = self.scan()
        return [
            agent for agent in result.agents
            if technology.lower() in agent.technologies
        ]

    def filter_by_specialization(self, specialization: str) -> List[LocalAgentMetadata]:
        """Filter agents by specialization"""
        result = self.scan()
        return [
            agent for agent in result.agents
            if specialization.lower() in agent.specializations
        ]
```

### 2. Integration Helper

```python
# Quick usage for other tasks

def discover_local_agents() -> List[LocalAgentMetadata]:
    """
    One-line helper for discovering local agents

    Usage:
        agents = discover_local_agents()
        for agent in agents:
            print(f"{agent.name}: {agent.description}")
    """
    scanner = LocalAgentScanner()
    result = scanner.scan()
    return result.agents
```

## Testing Strategy

```python
# tests/test_local_agent_scanner.py

def test_scan_global_agents():
    """Test scanning installer/core/agents directory"""
    scanner = LocalAgentScanner()
    result = scanner.scan(force_refresh=True)

    # Should find at least 15 agents
    assert result.valid_count >= 15
    assert len(result.agents) >= 15

    # Check known agents exist
    agent_names = {agent.name.lower() for agent in result.agents}
    assert "architectural-reviewer" in agent_names or "architectural reviewer" in agent_names
    assert "code-reviewer" in agent_names or "code reviewer" in agent_names
    assert "test-orchestrator" in agent_names or "test orchestrator" in agent_names

def test_agent_metadata_extraction():
    """Test metadata extraction from agent file"""
    # Create test agent file
    test_agent = '''
    # Test Agent

    This agent handles testing tasks for React applications.

    ## Tools
    - Read, Write, Bash, Grep

    ## Capabilities
    - Run unit tests
    - Generate test reports
    - Validate code coverage
    '''

    file_path = create_temp_file("test-agent.md", test_agent)
    scanner = LocalAgentScanner(agent_dir=file_path.parent)

    agent = scanner._parse_agent_file(file_path)

    assert agent is not None
    assert agent.name == "Test Agent"
    assert "React" in agent.technologies or "react" in agent.technologies
    assert "testing" in agent.specializations
    assert len(agent.tools) > 0
    assert agent.priority_bonus == 20

def test_technology_filtering():
    """Test filtering agents by technology"""
    scanner = LocalAgentScanner()
    react_agents = scanner.filter_by_technology("react")

    # Should find figma-react-orchestrator
    assert any("figma" in agent.name.lower() for agent in react_agents)

def test_cache_functionality():
    """Test caching works"""
    scanner = LocalAgentScanner(use_cache=True)

    # First scan
    result1 = scanner.scan()
    time1 = result1.scan_time

    # Second scan (should use cache)
    result2 = scanner.scan()
    time2 = result2.scan_time

    assert time1 == time2  # Same cached result

    # Force refresh
    result3 = scanner.scan(force_refresh=True)
    assert result3.scan_time > time2
```

## Definition of Done

- [ ] Local agent scanner implemented
- [ ] Parses all 15+ existing agents from installer/core/agents
- [ ] Extracts metadata: name, description, tools, technologies, specializations
- [ ] Caching implemented (5-minute TTL)
- [ ] Support for custom agent directories
- [ ] Technology/specialization filtering
- [ ] Unit tests for parsing passing
- [ ] Integration ready for TASK-050
- [ ] Documentation of agent format

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: HIGH

## Impact

Enables reuse of existing guardkit agents:
- 15+ battle-tested agents discovered automatically
- Local-first approach (priority bonus)
- Better template quality out-of-the-box
- No reinventing the wheel
- Foundation for TASK-048C (configurable sources)
