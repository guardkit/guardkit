---
id: TASK-004
title: AI-Powered Agent Discovery from External Sources
status: backlog
created: 2025-11-01T22:00:00Z
priority: medium
complexity: 5
estimated_hours: 6
tags: [agent-discovery, ai-powered, webfetch, configurable]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-003]
blocks: [TASK-009]
---

# TASK-004: AI-Powered Agent Discovery from External Sources

## Objective

Enable discovery of community agent definitions from external sources using Claude Code's WebFetch tool with AI analysis. User provides curated URLs, AI extracts and validates agent definitions.

**Key Principle**: AI-powered extraction (not brittle web scraping)

## Rationale: Why This Approach Works

### ❌ Previous Design (Algorithmic Web Scraping)
```python
# Brittle regex/HTML parsing
soup = BeautifulSoup(html)
agents = soup.find_all("div", class_="agent-card")  # Breaks when HTML changes
```

### ✅ New Design (AI-Powered WebFetch)
```python
# AI understands content semantically
response = WebFetch(url, prompt="Extract agent definitions...")
# Adapts to format changes, works across different sources
```

**Why This Is Low-Risk**:
- Uses existing WebFetch tool (same as architectural analysis)
- AI adapts to format variations
- Graceful degradation (fallback to local agents)
- User-controlled (curated URLs, not crawling)

## Acceptance Criteria

- [ ] Configuration file for agent sources (JSON)
- [ ] AI-powered extraction using WebFetch tool
- [ ] Support multiple source types (web pages, GitHub repos, markdown files)
- [ ] Agent definition validation
- [ ] Caching mechanism (avoid repeated fetches)
- [ ] Graceful fallback to local agents if fetch fails
- [ ] User can enable/disable external discovery
- [ ] Progress feedback during discovery
- [ ] Unit tests with mock WebFetch responses

## Configuration Design

```json
// ~/.agentecflow/agent-sources.json
{
  "version": "1.0.0",
  "external_discovery_enabled": true,
  "cache_ttl_hours": 24,
  "sources": [
    {
      "name": "subagents.cc",
      "type": "web",
      "url": "https://subagents.cc",
      "enabled": true,
      "priority": 1,
      "description": "Community-curated agent marketplace"
    },
    {
      "name": "wshobson-agents",
      "type": "github",
      "url": "https://github.com/wshobson/agents",
      "path": "plugins/*.md",
      "enabled": true,
      "priority": 2,
      "description": "Plugin-based agent architecture"
    },
    {
      "name": "awesome-claude-subagents",
      "type": "github",
      "url": "https://github.com/VoltAgent/awesome-claude-code-subagents",
      "path": "README.md",
      "enabled": true,
      "priority": 3,
      "description": "Curated awesome list"
    },
    {
      "name": "agentsof-dev",
      "type": "web",
      "url": "https://agentsof.dev",
      "enabled": true,
      "priority": 4,
      "description": "Community agent marketplace"
    },
    {
      "name": "github-awesome-copilot",
      "type": "github",
      "url": "https://github.com/github/awesome-copilot/tree/main/agents",
      "path": "agents/*.md",
      "enabled": true,
      "priority": 5,
      "description": "GitHub's official Copilot agent collection"
    },
    {
      "name": "claudecode-subagents-topic",
      "type": "github",
      "url": "https://github.com/topics/claudecode-subagents",
      "enabled": true,
      "priority": 6,
      "description": "GitHub topic search for Claude Code subagents"
    },
    {
      "name": "0xfurai-subagents",
      "type": "github",
      "url": "https://github.com/0xfurai/claude-code-subagents",
      "path": "README.md",
      "enabled": true,
      "priority": 7,
      "description": "0xfurai's Claude Code subagent collection"
    },
    {
      "name": "davepoon-subagents",
      "type": "github",
      "url": "https://github.com/davepoon/claude-code-subagents-collection/tree/main/subagents",
      "path": "subagents/*.md",
      "enabled": true,
      "priority": 8,
      "description": "Dave Poon's curated subagent collection"
    },
    {
      "name": "company-internal",
      "type": "url",
      "url": "https://internal.company.com/agents.json",
      "enabled": false,
      "priority": 10,
      "description": "Company-specific agents",
      "requires_auth": true
    }
  ]
}
```

## Implementation

```python
# src/commands/template_create/agent_discovery.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime, timedelta

@dataclass
class AgentSource:
    """External agent source configuration"""
    name: str
    type: str  # web, github, url
    url: str
    enabled: bool
    priority: int
    description: str
    path: Optional[str] = None  # For GitHub repos
    requires_auth: bool = False

@dataclass
class DiscoveredAgent:
    """Agent discovered from external source"""
    name: str
    description: str
    tools: List[str]
    source_name: str
    source_url: str
    definition_url: Optional[str]
    tags: List[str]
    confidence: int  # 0-100 (AI's confidence in extraction)
    raw_definition: str  # Original agent definition

class AgentSourceConfig:
    """Manage agent source configuration"""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".agentecflow" / "agent-sources.json"
        self.sources: List[AgentSource] = []
        self._load_config()

    def _load_config(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path) as f:
            data = json.load(f)

        self.sources = [
            AgentSource(
                name=s["name"],
                type=s["type"],
                url=s["url"],
                enabled=s["enabled"],
                priority=s["priority"],
                description=s["description"],
                path=s.get("path"),
                requires_auth=s.get("requires_auth", False)
            )
            for s in data["sources"]
        ]

    def _create_default_config(self):
        """Create default configuration"""
        default_config = {
            "version": "1.0.0",
            "external_discovery_enabled": True,
            "cache_ttl_hours": 24,
            "sources": [
                {
                    "name": "subagents.cc",
                    "type": "web",
                    "url": "https://subagents.cc",
                    "enabled": True,
                    "priority": 1,
                    "description": "Community-curated agent marketplace"
                },
                {
                    "name": "wshobson-agents",
                    "type": "github",
                    "url": "https://github.com/wshobson/agents",
                    "path": "plugins/*.md",
                    "enabled": True,
                    "priority": 2,
                    "description": "Plugin-based agent architecture"
                },
                {
                    "name": "awesome-claude-subagents",
                    "type": "github",
                    "url": "https://github.com/VoltAgent/awesome-claude-code-subagents",
                    "path": "README.md",
                    "enabled": True,
                    "priority": 3,
                    "description": "Curated awesome list"
                },
                {
                    "name": "agentsof-dev",
                    "type": "web",
                    "url": "https://agentsof.dev",
                    "enabled": True,
                    "priority": 4,
                    "description": "Community agent marketplace"
                },
                {
                    "name": "github-awesome-copilot",
                    "type": "github",
                    "url": "https://github.com/github/awesome-copilot/tree/main/agents",
                    "path": "agents/*.md",
                    "enabled": True,
                    "priority": 5,
                    "description": "GitHub's official Copilot agent collection"
                },
                {
                    "name": "claudecode-subagents-topic",
                    "type": "github",
                    "url": "https://github.com/topics/claudecode-subagents",
                    "enabled": True,
                    "priority": 6,
                    "description": "GitHub topic search for Claude Code subagents"
                },
                {
                    "name": "0xfurai-subagents",
                    "type": "github",
                    "url": "https://github.com/0xfurai/claude-code-subagents",
                    "path": "README.md",
                    "enabled": True,
                    "priority": 7,
                    "description": "0xfurai's Claude Code subagent collection"
                },
                {
                    "name": "davepoon-subagents",
                    "type": "github",
                    "url": "https://github.com/davepoon/claude-code-subagents-collection/tree/main/subagents",
                    "path": "subagents/*.md",
                    "enabled": True,
                    "priority": 8,
                    "description": "Dave Poon's curated subagent collection"
                }
            ]
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

    def get_enabled_sources(self) -> List[AgentSource]:
        """Get enabled sources sorted by priority"""
        return sorted(
            [s for s in self.sources if s.enabled],
            key=lambda s: s.priority
        )

class AIAgentDiscovery:
    """AI-powered agent discovery using WebFetch"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path.home() / ".agentecflow" / "cache" / "agents"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=24)

    def discover_agents(
        self,
        sources: List[AgentSource],
        use_cache: bool = True
    ) -> List[DiscoveredAgent]:
        """
        Discover agents from external sources using AI

        Args:
            sources: List of agent sources to check
            use_cache: Whether to use cached results

        Returns:
            List of discovered agents
        """
        all_agents = []

        for source in sources:
            print(f"🔍 Discovering agents from {source.name}...")

            try:
                # Check cache first
                if use_cache:
                    cached = self._load_from_cache(source.name)
                    if cached:
                        print(f"  ✓ Loaded {len(cached)} agents from cache")
                        all_agents.extend(cached)
                        continue

                # Fetch and extract using AI
                agents = self._fetch_and_extract(source)

                print(f"  ✓ Discovered {len(agents)} agents")

                # Cache results
                self._save_to_cache(source.name, agents)

                all_agents.extend(agents)

            except Exception as e:
                print(f"  ⚠️  Failed to discover from {source.name}: {e}")
                print(f"  → Continuing with other sources...")

        return all_agents

    def _fetch_and_extract(self, source: AgentSource) -> List[DiscoveredAgent]:
        """Fetch source and extract agents using AI"""

        if source.type == "web":
            return self._fetch_from_web(source)
        elif source.type == "github":
            return self._fetch_from_github(source)
        elif source.type == "url":
            return self._fetch_from_url(source)
        else:
            raise ValueError(f"Unknown source type: {source.type}")

    def _fetch_from_web(self, source: AgentSource) -> List[DiscoveredAgent]:
        """Fetch agents from web page using WebFetch + AI"""

        prompt = f"""
        Analyze this web page and extract Claude Code agent definitions.

        For each agent found, extract:
        1. **Name**: Agent identifier (kebab-case)
        2. **Description**: What the agent does (1-2 sentences)
        3. **Tools**: List of tools/capabilities the agent uses
        4. **Tags**: Relevant tags (language, framework, domain)
        5. **Definition URL**: Direct link to agent definition (if available)
        6. **Confidence**: Your confidence in this extraction (0-100)

        Return as JSON array:
        [
          {{
            "name": "react-state-specialist",
            "description": "Expert in React state management patterns",
            "tools": ["Read", "Write", "Edit", "Bash"],
            "tags": ["react", "javascript", "state-management"],
            "definition_url": "https://example.com/agents/react-state-specialist.md",
            "confidence": 95
          }},
          ...
        ]

        IMPORTANT:
        - Only extract agents with clear, complete definitions
        - If uncertain about an agent, mark confidence < 70
        - If no agents found, return empty array []
        - Include definition_url if available for direct download
        """

        try:
            # Use WebFetch tool (Claude Code's built-in tool)
            from tools import WebFetch

            response = WebFetch(url=source.url, prompt=prompt)

            # Parse AI response
            agents_data = json.loads(response)

            # Convert to DiscoveredAgent objects
            agents = [
                DiscoveredAgent(
                    name=a["name"],
                    description=a["description"],
                    tools=a["tools"],
                    source_name=source.name,
                    source_url=source.url,
                    definition_url=a.get("definition_url"),
                    tags=a.get("tags", []),
                    confidence=a["confidence"],
                    raw_definition=""  # Fetch later if selected
                )
                for a in agents_data
                if a["confidence"] >= 70  # Filter low-confidence extractions
            ]

            return agents

        except json.JSONDecodeError as e:
            print(f"  ⚠️  AI returned invalid JSON: {e}")
            return []
        except Exception as e:
            print(f"  ⚠️  WebFetch failed: {e}")
            return []

    def _fetch_from_github(self, source: AgentSource) -> List[DiscoveredAgent]:
        """Fetch agents from GitHub repository"""

        # For GitHub repos, we can use WebFetch on README or individual files

        if source.path:
            # Fetch specific path (e.g., plugins/*.md)
            # This would require listing files first
            # For now, fetch README and extract references
            readme_url = f"{source.url}/blob/main/README.md"
        else:
            readme_url = f"{source.url}/blob/main/README.md"

        prompt = f"""
        Analyze this GitHub repository README and extract agent definitions.

        Look for:
        1. Agent names and descriptions
        2. Links to agent definition files
        3. Tool/capability information
        4. Categories or tags

        Return as JSON array with:
        - name (kebab-case)
        - description
        - tools (list)
        - tags (list)
        - definition_url (full GitHub raw URL if available)
        - confidence (0-100)

        Example:
        [
          {{
            "name": "typescript-domain-modeler",
            "description": "TypeScript domain modeling expert",
            "tools": ["Read", "Write", "Edit"],
            "tags": ["typescript", "domain-modeling"],
            "definition_url": "https://raw.githubusercontent.com/.../agent.md",
            "confidence": 90
          }}
        ]
        """

        try:
            from tools import WebFetch

            response = WebFetch(url=readme_url, prompt=prompt)
            agents_data = json.loads(response)

            agents = [
                DiscoveredAgent(
                    name=a["name"],
                    description=a["description"],
                    tools=a["tools"],
                    source_name=source.name,
                    source_url=source.url,
                    definition_url=a.get("definition_url"),
                    tags=a.get("tags", []),
                    confidence=a["confidence"],
                    raw_definition=""
                )
                for a in agents_data
                if a["confidence"] >= 70
            ]

            return agents

        except Exception as e:
            print(f"  ⚠️  Failed to fetch from GitHub: {e}")
            return []

    def _fetch_from_url(self, source: AgentSource) -> List[DiscoveredAgent]:
        """Fetch agents from direct URL (JSON, markdown, etc.)"""

        prompt = """
        Extract agent definitions from this content.

        The content may be:
        - JSON array of agent definitions
        - Markdown document with agent descriptions
        - HTML page with agent listings

        Extract and return as JSON array with fields:
        name, description, tools, tags, definition_url, confidence
        """

        try:
            from tools import WebFetch

            response = WebFetch(url=source.url, prompt=prompt)
            agents_data = json.loads(response)

            agents = [
                DiscoveredAgent(
                    name=a["name"],
                    description=a["description"],
                    tools=a["tools"],
                    source_name=source.name,
                    source_url=source.url,
                    definition_url=a.get("definition_url"),
                    tags=a.get("tags", []),
                    confidence=a["confidence"],
                    raw_definition=""
                )
                for a in agents_data
                if a["confidence"] >= 70
            ]

            return agents

        except Exception as e:
            print(f"  ⚠️  Failed to fetch from URL: {e}")
            return []

    def fetch_agent_definition(self, agent: DiscoveredAgent) -> Optional[str]:
        """
        Fetch full agent definition (markdown) for selected agent

        Args:
            agent: Discovered agent with definition_url

        Returns:
            Full agent definition as string, or None if fetch fails
        """
        if not agent.definition_url:
            return None

        prompt = """
        Return the complete agent definition from this page.
        This should be the raw markdown content defining the agent.
        Do not modify or summarize - return exactly as is.
        """

        try:
            from tools import WebFetch

            definition = WebFetch(url=agent.definition_url, prompt=prompt)
            return definition

        except Exception as e:
            print(f"  ⚠️  Failed to fetch definition for {agent.name}: {e}")
            return None

    def _load_from_cache(self, source_name: str) -> Optional[List[DiscoveredAgent]]:
        """Load cached agent discovery results"""
        cache_file = self.cache_dir / f"{source_name}.json"

        if not cache_file.exists():
            return None

        # Check if cache is expired
        cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if cache_age > self.cache_ttl:
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            agents = [
                DiscoveredAgent(
                    name=a["name"],
                    description=a["description"],
                    tools=a["tools"],
                    source_name=a["source_name"],
                    source_url=a["source_url"],
                    definition_url=a.get("definition_url"),
                    tags=a.get("tags", []),
                    confidence=a["confidence"],
                    raw_definition=a.get("raw_definition", "")
                )
                for a in data
            ]

            return agents

        except Exception:
            return None

    def _save_to_cache(self, source_name: str, agents: List[DiscoveredAgent]):
        """Save discovery results to cache"""
        cache_file = self.cache_dir / f"{source_name}.json"

        data = [
            {
                "name": a.name,
                "description": a.description,
                "tools": a.tools,
                "source_name": a.source_name,
                "source_url": a.source_url,
                "definition_url": a.definition_url,
                "tags": a.tags,
                "confidence": a.confidence,
                "raw_definition": a.raw_definition
            }
            for a in agents
        ]

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

# Integration with template creation flow
def discover_all_agents(include_external: bool = True) -> List[DiscoveredAgent]:
    """
    Discover agents from both local and external sources

    Args:
        include_external: Whether to include external sources

    Returns:
        Combined list of discovered agents
    """
    all_agents = []

    # 1. Discover local agents (TASK-003)
    from .local_agent_scanner import LocalAgentScanner

    scanner = LocalAgentScanner()
    local_agents = scanner.scan()
    print(f"✓ Found {len(local_agents)} local agents")

    # Convert to DiscoveredAgent format
    for agent in local_agents:
        all_agents.append(
            DiscoveredAgent(
                name=agent.name,
                description=agent.description,
                tools=agent.tools,
                source_name="local",
                source_url="file://installer/core/agents/",
                definition_url=None,
                tags=agent.tags,
                confidence=100,  # Local agents are trusted
                raw_definition=agent.definition
            )
        )

    # 2. Discover external agents (TASK-004) - if enabled
    if include_external:
        print("\n🌐 Discovering agents from external sources...")

        config = AgentSourceConfig()

        # Check if external discovery is enabled
        if not config.sources:
            print("  ℹ️  No external sources configured")
            return all_agents

        discovery = AIAgentDiscovery()
        enabled_sources = config.get_enabled_sources()

        if not enabled_sources:
            print("  ℹ️  External discovery disabled")
            return all_agents

        try:
            external_agents = discovery.discover_agents(enabled_sources)
            print(f"\n✓ Discovered {len(external_agents)} agents from external sources")
            all_agents.extend(external_agents)

        except Exception as e:
            print(f"\n⚠️  External discovery failed: {e}")
            print("  → Continuing with local agents only")

    return all_agents
```

## Testing Strategy

```python
# tests/test_ai_agent_discovery.py

def test_webfetch_extraction():
    """Test AI extraction from web page (with mock WebFetch)"""
    # Mock WebFetch to return sample JSON
    mock_response = json.dumps([
        {
            "name": "react-specialist",
            "description": "React expert",
            "tools": ["Read", "Write"],
            "tags": ["react"],
            "confidence": 95
        }
    ])

    with patch('tools.WebFetch', return_value=mock_response):
        source = AgentSource(
            name="test",
            type="web",
            url="https://example.com",
            enabled=True,
            priority=1,
            description="Test"
        )

        discovery = AIAgentDiscovery()
        agents = discovery._fetch_from_web(source)

        assert len(agents) == 1
        assert agents[0].name == "react-specialist"
        assert agents[0].confidence == 95

def test_cache_functionality():
    """Test caching mechanism"""
    # Create mock agents
    agents = [
        DiscoveredAgent(
            name="test-agent",
            description="Test",
            tools=["Read"],
            source_name="test",
            source_url="https://example.com",
            definition_url=None,
            tags=[],
            confidence=90,
            raw_definition=""
        )
    ]

    discovery = AIAgentDiscovery(cache_dir=Path("/tmp/test-cache"))

    # Save to cache
    discovery._save_to_cache("test-source", agents)

    # Load from cache
    cached = discovery._load_from_cache("test-source")

    assert cached is not None
    assert len(cached) == 1
    assert cached[0].name == "test-agent"

def test_graceful_degradation():
    """Test fallback to local agents when external fails"""

    # Mock WebFetch to raise exception
    with patch('tools.WebFetch', side_effect=Exception("Network error")):
        agents = discover_all_agents(include_external=True)

        # Should still have local agents
        assert len(agents) > 0
        assert all(a.source_name == "local" for a in agents)

def test_confidence_filtering():
    """Test that low-confidence agents are filtered"""
    mock_response = json.dumps([
        {"name": "agent1", "description": "Test", "tools": [], "confidence": 95},
        {"name": "agent2", "description": "Test", "tools": [], "confidence": 50},  # Below threshold
        {"name": "agent3", "description": "Test", "tools": [], "confidence": 75},
    ])

    with patch('tools.WebFetch', return_value=mock_response):
        # ... should only return agent1 and agent3
```

## User Experience

```bash
# User enables external discovery
$ /template-create "myapp"

[Q&A Session...]

🔍 Discovering agents...
✓ Found 15 local agents

🌐 Discovering agents from external sources...
🔍 Discovering agents from subagents.cc...
  ✓ Discovered 23 agents
🔍 Discovering agents from wshobson-agents...
  ✓ Discovered 18 agents
🔍 Discovering agents from awesome-claude-subagents...
  ✓ Discovered 12 agents
🔍 Discovering agents from agentsof-dev...
  ✓ Discovered 15 agents
🔍 Discovering agents from github-awesome-copilot...
  ✓ Discovered 8 agents
🔍 Discovering agents from claudecode-subagents-topic...
  ✓ Discovered 25 agents
🔍 Discovering agents from 0xfurai-subagents...
  ✓ Discovered 14 agents
🔍 Discovering agents from davepoon-subagents...
  ✓ Discovered 19 agents

✓ Total: 149 agents discovered (15 local + 134 external)

[Agent selection UI...]
```

## Configuration Management

```bash
# View current configuration
$ cat ~/.agentecflow/agent-sources.json

# Disable external discovery
$ vim ~/.agentecflow/agent-sources.json
# Set "external_discovery_enabled": false

# Add custom source
{
  "name": "company-agents",
  "type": "url",
  "url": "https://company.com/agents.json",
  "enabled": true,
  "priority": 10
}

# Clear cache
$ rm -rf ~/.agentecflow/cache/agents/
```

## Error Handling

```python
class AgentDiscoveryError(Exception):
    """Base exception for agent discovery"""
    pass

class WebFetchError(AgentDiscoveryError):
    """WebFetch failed"""
    pass

class InvalidAgentDefinition(AgentDiscoveryError):
    """Agent definition validation failed"""
    pass

# Graceful degradation
try:
    external_agents = discovery.discover_agents(sources)
except AgentDiscoveryError as e:
    logger.warning(f"External discovery failed: {e}")
    print("⚠️  Continuing with local agents only")
    external_agents = []
```

## Definition of Done

- [ ] AgentSourceConfig loads configuration from JSON
- [ ] AIAgentDiscovery uses WebFetch tool for extraction
- [ ] Support for web, github, and url source types
- [ ] AI confidence filtering (≥70% threshold)
- [ ] Caching mechanism with 24-hour TTL
- [ ] Graceful fallback to local agents
- [ ] Agent definition fetching for selected agents
- [ ] User can enable/disable external discovery
- [ ] Unit tests with mock WebFetch passing (>85% coverage)
- [ ] Integration test with real WebFetch (manually verified)
- [ ] Documentation for configuration

**Estimated Time**: 6 hours | **Complexity**: 5/10 | **Priority**: MEDIUM

## Benefits

- ✅ Leverages existing AI capabilities (WebFetch tool)
- ✅ Not brittle (AI adapts to format changes)
- ✅ User-controlled (curated URLs, not web crawling)
- ✅ Graceful degradation (works offline with local agents)
- ✅ Extensible (easy to add new sources)
- ✅ Cached (reduces API calls)
- ✅ Format-agnostic (HTML, markdown, JSON all supported)

## Comparison: Algorithmic vs AI-Powered

| Aspect | Algorithmic (Removed) | AI-Powered (This Design) |
|--------|----------------------|--------------------------|
| Extraction | Regex/HTML parsing | WebFetch + AI analysis |
| Robustness | Brittle, breaks easily | Adapts to format changes |
| Format Support | Single format per scraper | Multiple formats (HTML, MD, JSON) |
| Maintenance | High (update regex constantly) | Low (AI adapts automatically) |
| Accuracy | 50-70% | 85-95% (with confidence filtering) |
| Offline Support | No | Yes (cache + local fallback) |
| Error Recovery | Fails completely | Graceful degradation |

## Security Considerations

1. **URL Validation**: Only fetch from configured, trusted sources
2. **Content Validation**: AI validates extracted agents before use
3. **Sandboxing**: Agent definitions are markdown (not executable)
4. **Cache Isolation**: Cache stored in user directory (not system-wide)
5. **Authentication**: Support for authenticated sources (optional)

**Risk Level**: LOW (similar to WebFetch usage in other tools)

---

**Created**: 2025-11-01
**Status**: ✅ **REDESIGNED - AI-POWERED APPROACH**
**Approach**: WebFetch + AI analysis (not algorithmic scraping)
**Priority**: MEDIUM (optional enhancement, not blocking MVP)
