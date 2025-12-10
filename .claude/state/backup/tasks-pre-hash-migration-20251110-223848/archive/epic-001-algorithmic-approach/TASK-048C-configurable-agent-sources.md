---
id: TASK-048C
title: Configurable Agent Source Registry
status: backlog
created: 2025-11-01T19:15:00Z
priority: high
complexity: 3
estimated_hours: 3
tags: [agent-discovery, configuration, extensibility]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-048B]
blocks: [TASK-050]
---

# TASK-048C: Configurable Agent Source Registry

## Objective

Implement configurable agent source registry to allow users to add custom agent sources (company-internal repositories, private registries, etc.) beyond the hardcoded 3 external sources.

**Problem:** Agent sources hardcoded to subagents.cc, GitHub (wshobson), GitHub (VoltAgent)
**Solution:** JSON-based configuration with support for unlimited sources

## Acceptance Criteria

- [ ] Agent source registry configuration file (JSON)
- [ ] Support for multiple source types (local, GitHub, HTTP, custom)
- [ ] Priority ordering of sources
- [ ] Authentication configuration (tokens, credentials)
- [ ] Default configuration includes local + external sources
- [ ] Validation of source configuration
- [ ] Source enable/disable without deletion
- [ ] Add/remove sources programmatically
- [ ] CLI command to manage sources
- [ ] Integration with TASK-050 (matching algorithm)
- [ ] Unit tests for source management
- [ ] Documentation of configuration format

## Implementation

### 1. Configuration Schema

```python
# src/commands/template_create/agent_source_config.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
from enum import Enum
import json

class SourceType(Enum):
    """Types of agent sources"""
    LOCAL = "local"           # Local directory
    GITHUB = "github"         # GitHub repository
    HTTP = "http"             # HTTP endpoint
    SUBAGENTS_CC = "subagents_cc"  # subagents.cc marketplace
    CUSTOM = "custom"         # Custom implementation

@dataclass
class AgentSourceConfig:
    """Configuration for an agent source"""
    id: str                   # Unique identifier
    name: str                 # Display name
    type: SourceType          # Source type
    enabled: bool = True      # Whether source is active
    priority: int = 50        # Priority (1-100, higher = more priority)
    bonus_score: int = 0      # Bonus score for agents from this source

    # Type-specific configuration
    path: Optional[str] = None              # For LOCAL type
    repo: Optional[str] = None              # For GITHUB type (org/repo)
    url: Optional[str] = None               # For HTTP type
    auth: Optional[str] = None              # Authentication (env:VAR_NAME or token)
    branch: Optional[str] = None            # For GITHUB type
    subdirectory: Optional[str] = None      # Subdirectory in repo

    # Metadata
    description: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class AgentSourceRegistry:
    """Registry of all agent sources"""
    sources: List[AgentSourceConfig]
    version: str = "1.0"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'version': self.version,
            'sources': [
                {
                    'id': s.id,
                    'name': s.name,
                    'type': s.type.value,
                    'enabled': s.enabled,
                    'priority': s.priority,
                    'bonus_score': s.bonus_score,
                    'path': s.path,
                    'repo': s.repo,
                    'url': s.url,
                    'auth': s.auth,
                    'branch': s.branch,
                    'subdirectory': s.subdirectory,
                    'description': s.description,
                    'tags': s.tags,
                }
                for s in self.sources
            ]
        }

    @staticmethod
    def from_dict(data: Dict) -> 'AgentSourceRegistry':
        """Load from dictionary"""
        sources = [
            AgentSourceConfig(
                id=s['id'],
                name=s['name'],
                type=SourceType(s['type']),
                enabled=s.get('enabled', True),
                priority=s.get('priority', 50),
                bonus_score=s.get('bonus_score', 0),
                path=s.get('path'),
                repo=s.get('repo'),
                url=s.get('url'),
                auth=s.get('auth'),
                branch=s.get('branch'),
                subdirectory=s.get('subdirectory'),
                description=s.get('description'),
                tags=s.get('tags', []),
            )
            for s in data['sources']
        ]
        return AgentSourceRegistry(
            sources=sources,
            version=data.get('version', '1.0')
        )
```

### 2. Default Configuration

```python
# Default agent sources configuration

DEFAULT_AGENT_SOURCES = AgentSourceRegistry(
    sources=[
        # Priority 1: Local guardkit agents (highest priority)
        AgentSourceConfig(
            id="local_global",
            name="GuardKit Built-in Agents",
            type=SourceType.LOCAL,
            enabled=True,
            priority=100,
            bonus_score=20,
            path="installer/core/agents",
            description="Battle-tested agents included with guardkit",
            tags=["official", "local"]
        ),

        # Priority 2: Local user agents
        AgentSourceConfig(
            id="local_user",
            name="User Custom Agents",
            type=SourceType.LOCAL,
            enabled=True,
            priority=90,
            bonus_score=15,
            path=".claude/agents",
            description="User's custom agents for this project",
            tags=["custom", "local"]
        ),

        # Priority 3: External curated sources
        AgentSourceConfig(
            id="subagents_cc",
            name="Subagents.cc Marketplace",
            type=SourceType.SUBAGENTS_CC,
            enabled=True,
            priority=70,
            bonus_score=5,
            url="https://subagents.cc",
            description="Community agent marketplace",
            tags=["community", "external"]
        ),

        AgentSourceConfig(
            id="wshobson_agents",
            name="wshobson/agents",
            type=SourceType.GITHUB,
            enabled=True,
            priority=65,
            bonus_score=3,
            repo="wshobson/agents",
            branch="main",
            description="Curated agent collection by wshobson",
            tags=["community", "external", "github"]
        ),

        AgentSourceConfig(
            id="voltagent",
            name="VoltAgent Repository",
            type=SourceType.GITHUB,
            enabled=True,
            priority=60,
            bonus_score=2,
            repo="VoltAgent/agents",
            branch="main",
            description="VoltAgent's agent repository",
            tags=["community", "external", "github"]
        ),

        # Example: Company-internal source (disabled by default)
        AgentSourceConfig(
            id="company_internal",
            name="Company Internal Agents",
            type=SourceType.GITHUB,
            enabled=False,  # User enables when needed
            priority=85,
            bonus_score=10,
            repo="mycompany/claude-agents",
            branch="main",
            auth="env:GITHUB_TOKEN",  # Use env variable for auth
            description="Company's internal agent repository",
            tags=["company", "internal", "private"]
        ),
    ]
)
```

### 3. Configuration Manager

```python
# src/commands/template_create/agent_source_manager.py

import os
from pathlib import Path

class AgentSourceManager:
    """Manages agent source configuration"""

    DEFAULT_CONFIG_PATH = Path.home() / ".guardkit" / "agent-sources.json"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize manager

        Args:
            config_path: Path to config file (default: ~/.guardkit/agent-sources.json)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.registry = self._load_or_create_default()

    def _load_or_create_default(self) -> AgentSourceRegistry:
        """Load config or create default"""
        if not self.config_path.exists():
            # Create default configuration
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            registry = DEFAULT_AGENT_SOURCES
            self.save(registry)
            return registry

        # Load existing
        try:
            data = json.loads(self.config_path.read_text())
            return AgentSourceRegistry.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load config: {e}. Using defaults.")
            return DEFAULT_AGENT_SOURCES

    def save(self, registry: Optional[AgentSourceRegistry] = None):
        """Save configuration"""
        if registry is None:
            registry = self.registry

        self.config_path.write_text(
            json.dumps(registry.to_dict(), indent=2)
        )

    def add_source(self, source: AgentSourceConfig):
        """Add a new agent source"""
        # Check for duplicate ID
        if any(s.id == source.id for s in self.registry.sources):
            raise ValueError(f"Source with ID '{source.id}' already exists")

        self.registry.sources.append(source)
        self.save()

    def remove_source(self, source_id: str):
        """Remove an agent source"""
        self.registry.sources = [
            s for s in self.registry.sources
            if s.id != source_id
        ]
        self.save()

    def enable_source(self, source_id: str):
        """Enable a source"""
        for source in self.registry.sources:
            if source.id == source_id:
                source.enabled = True
                self.save()
                return
        raise ValueError(f"Source '{source_id}' not found")

    def disable_source(self, source_id: str):
        """Disable a source"""
        for source in self.registry.sources:
            if source.id == source_id:
                source.enabled = False
                self.save()
                return
        raise ValueError(f"Source '{source_id}' not found")

    def get_enabled_sources(self) -> List[AgentSourceConfig]:
        """Get all enabled sources, sorted by priority"""
        enabled = [s for s in self.registry.sources if s.enabled]
        return sorted(enabled, key=lambda s: s.priority, reverse=True)

    def get_source(self, source_id: str) -> Optional[AgentSourceConfig]:
        """Get specific source by ID"""
        for source in self.registry.sources:
            if source.id == source_id:
                return source
        return None

    def resolve_auth(self, source: AgentSourceConfig) -> Optional[str]:
        """
        Resolve authentication credential

        Supports:
        - env:VAR_NAME - Read from environment variable
        - Direct token string

        Returns:
            Resolved credential or None
        """
        if not source.auth:
            return None

        # Environment variable
        if source.auth.startswith("env:"):
            var_name = source.auth[4:]
            return os.environ.get(var_name)

        # Direct token
        return source.auth
```

### 4. CLI Integration

```python
# CLI commands for managing sources

def cmd_agent_source_list():
    """List all configured agent sources"""
    manager = AgentSourceManager()
    sources = manager.registry.sources

    print(f"\nConfigured Agent Sources ({len(sources)} total):\n")

    for source in sorted(sources, key=lambda s: s.priority, reverse=True):
        status = "✓ ENABLED" if source.enabled else "✗ DISABLED"
        print(f"{status} | Priority {source.priority} | {source.name} ({source.id})")
        print(f"         Type: {source.type.value} | Bonus: +{source.bonus_score}")
        if source.description:
            print(f"         {source.description}")
        print()

def cmd_agent_source_add(
    source_id: str,
    name: str,
    source_type: str,
    **kwargs
):
    """Add a new agent source"""
    manager = AgentSourceManager()

    source = AgentSourceConfig(
        id=source_id,
        name=name,
        type=SourceType(source_type),
        **kwargs
    )

    manager.add_source(source)
    print(f"✓ Added source '{name}' ({source_id})")

def cmd_agent_source_enable(source_id: str):
    """Enable an agent source"""
    manager = AgentSourceManager()
    manager.enable_source(source_id)
    print(f"✓ Enabled source '{source_id}'")

def cmd_agent_source_disable(source_id: str):
    """Disable an agent source"""
    manager = AgentSourceManager()
    manager.disable_source(source_id)
    print(f"✓ Disabled source '{source_id}'")
```

## Testing Strategy

```python
# tests/test_agent_source_config.py

def test_default_configuration():
    """Test default configuration includes expected sources"""
    assert len(DEFAULT_AGENT_SOURCES.sources) >= 5

    # Check local_global exists and has high priority
    local_global = next(s for s in DEFAULT_AGENT_SOURCES.sources if s.id == "local_global")
    assert local_global.priority == 100
    assert local_global.bonus_score == 20
    assert local_global.enabled is True

def test_configuration_serialization():
    """Test config can be saved and loaded"""
    original = DEFAULT_AGENT_SOURCES

    # Serialize
    data = original.to_dict()

    # Deserialize
    loaded = AgentSourceRegistry.from_dict(data)

    assert len(loaded.sources) == len(original.sources)
    assert loaded.version == original.version

def test_add_source():
    """Test adding a new source"""
    manager = AgentSourceManager(config_path=Path("/tmp/test-config.json"))

    new_source = AgentSourceConfig(
        id="test_source",
        name="Test Source",
        type=SourceType.GITHUB,
        repo="test/repo"
    )

    manager.add_source(new_source)

    # Should be in registry
    assert any(s.id == "test_source" for s in manager.registry.sources)

def test_enable_disable():
    """Test enabling/disabling sources"""
    manager = AgentSourceManager(config_path=Path("/tmp/test-config.json"))

    # Disable a source
    manager.disable_source("subagents_cc")
    source = manager.get_source("subagents_cc")
    assert source.enabled is False

    # Re-enable
    manager.enable_source("subagents_cc")
    source = manager.get_source("subagents_cc")
    assert source.enabled is True

def test_auth_resolution():
    """Test authentication credential resolution"""
    manager = AgentSourceManager()

    # Test env variable resolution
    os.environ["TEST_TOKEN"] = "secret123"

    source = AgentSourceConfig(
        id="test",
        name="Test",
        type=SourceType.GITHUB,
        auth="env:TEST_TOKEN"
    )

    token = manager.resolve_auth(source)
    assert token == "secret123"
```

## Definition of Done

- [ ] Agent source configuration schema defined
- [ ] Default configuration with local + external sources
- [ ] Configuration manager implemented
- [ ] Add/remove/enable/disable sources
- [ ] Priority ordering of sources
- [ ] Authentication credential resolution
- [ ] JSON serialization/deserialization
- [ ] CLI commands for source management
- [ ] Unit tests for configuration passing
- [ ] Documentation of configuration format
- [ ] Integration ready for TASK-050

**Estimated Time**: 3 hours | **Complexity**: 3/10 | **Priority**: HIGH

## Impact

Enables enterprise-ready agent discovery:
- **Unlimited sources** (not hardcoded to 3)
- **Company-internal repositories** supported
- **Private authentication** (tokens, env variables)
- **Priority control** per source
- **Local-first** with configurable bonuses
- **Enterprise extensibility** for any workflow
