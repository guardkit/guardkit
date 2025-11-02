# Agent System Data Contracts

**Category**: Agent System
**Version**: 1.0.0
**Status**: ✅ COMPLETE

---

## Overview

Agent contracts define structures for agent discovery, generation, and recommendation workflows. These contracts support the multi-source agent system with priority-based selection.

---

## AgentInventory

**Source**: TASK-003 (Multi-Source Agent Scanner)
**Used By**: TASK-003 → TASK-009
**Schema Version**: 1.0.0

### Structure

```python
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from enum import Enum

class AgentSource(Enum):
    """Agent source types"""
    CUSTOM = "custom"          # .claude/agents/ (highest priority)
    TEMPLATE = "template"      # template/agents/
    GLOBAL = "global"          # installer/global/agents/
    GENERATED = "generated"    # AI-generated
    EXTERNAL = "external"      # subagents.cc, GitHub (lowest priority)

class AgentPriority(Enum):
    """Agent priority levels"""
    HIGHEST = 3  # User custom
    HIGH = 2     # Template-specific
    MEDIUM = 1   # Global or generated
    LOW = 0      # External suggestions

@dataclass
class AgentInventory:
    """Inventory of discovered agents from all sources"""

    schema_version: str = "1.0.0"

    # Agents by source (ordered by priority)
    custom_agents: List['AgentInfo'] = None      # Priority: HIGHEST
    template_agents: List['AgentInfo'] = None    # Priority: HIGH
    global_agents: List['AgentInfo'] = None      # Priority: MEDIUM
    generated_agents: List['GeneratedAgent'] = None  # Priority: MEDIUM
    external_agents: List['DiscoveredAgent'] = None  # Priority: LOW

    # Metadata
    scanned_at: datetime = None
    total_count: int = 0
    deduplication_applied: bool = False
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | str | Yes | Data contract version |
| `custom_agents` | List[AgentInfo] | No | User's custom agents (.claude/agents/) |
| `template_agents` | List[AgentInfo] | No | Template-specific agents |
| `global_agents` | List[AgentInfo] | No | Global built-in agents |
| `generated_agents` | List[GeneratedAgent] | No | AI-generated agents |
| `external_agents` | List[DiscoveredAgent] | No | External community agents |
| `scanned_at` | datetime | No | Scan timestamp |
| `total_count` | int | No | Total agent count across all sources |
| `deduplication_applied` | bool | No | Whether deduplication ran |

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "custom_agents": [
    {
      "name": "mycompany-react-specialist",
      "source": "custom",
      "priority": 3,
      "path": ".claude/agents/mycompany-react-specialist.md",
      "capabilities": ["react", "hooks", "state-management"]
    }
  ],
  "template_agents": [],
  "global_agents": [
    {
      "name": "architectural-reviewer",
      "source": "global",
      "priority": 1,
      "path": "installer/global/agents/architectural-reviewer.md",
      "capabilities": ["architecture", "review", "solid"]
    }
  ],
  "generated_agents": [],
  "external_agents": [],
  "scanned_at": "2025-11-01T15:45:00Z",
  "total_count": 2,
  "deduplication_applied": false
}
```

### Methods

```python
class AgentInventory:
    def all_agents(self) -> List['AgentInfo']:
        """Get all agents across all sources, ordered by priority"""
        all_agents = []

        if self.custom_agents:
            all_agents.extend(self.custom_agents)
        if self.template_agents:
            all_agents.extend(self.template_agents)
        if self.global_agents:
            all_agents.extend(self.global_agents)
        if self.generated_agents:
            all_agents.extend(self.generated_agents)
        if self.external_agents:
            all_agents.extend(self.external_agents)

        return all_agents

    def find_by_name(self, name: str) -> Optional['AgentInfo']:
        """Find agent by name (returns highest priority match)"""
        for agent in self.all_agents():
            if agent.name == name:
                return agent
        return None

    def has_capability(self, capability: str) -> bool:
        """Check if any agent has a capability"""
        for agent in self.all_agents():
            if capability in agent.capabilities:
                return True
        return False
```

---

## AgentInfo

**Purpose**: Represent a discovered agent from disk
**Part Of**: AgentInventory

### Structure

```python
@dataclass
class AgentInfo:
    """Discovered agent information"""

    name: str
    source: AgentSource  # "custom" | "template" | "global"
    priority: AgentPriority
    path: str  # File path
    capabilities: List[str]  # Extracted from agent definition
    description: Optional[str] = None
    tools: List[str] = None  # Tools available to agent
    tags: List[str] = None
    full_definition: Optional[str] = None  # Complete markdown content
```

### Example JSON

```json
{
  "name": "maui-appshell-specialist",
  "source": "template",
  "priority": 2,
  "path": "installer/local/templates/maui-mvvm/agents/maui-appshell-specialist.md",
  "capabilities": ["maui", "appshell", "navigation", "xaml"],
  "description": "Specialist in .NET MAUI AppShell navigation patterns",
  "tools": ["Read", "Write", "Edit", "Grep"],
  "tags": ["maui", "navigation", "ui"],
  "full_definition": "# MAUI AppShell Navigation Specialist\n\n..."
}
```

### Validation Rules

```python
class AgentInfoValidator(Validator):
    def validate(self, agent: AgentInfo) -> ValidationResult:
        errors = []

        if not agent.name:
            errors.append("name is required")
        elif not agent.name.replace("-", "").replace("_", "").isalnum():
            errors.append(f"Invalid agent name: {agent.name}")

        if not agent.source:
            errors.append("source is required")

        if not agent.path:
            errors.append("path is required")

        if not agent.capabilities:
            errors.append("At least one capability is required")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

---

## GeneratedAgent

**Source**: TASK-004A (AI Agent Generator)
**Used By**: TASK-004A → TASK-009
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class GeneratedAgent:
    """AI-generated agent"""

    name: str
    description: str
    content: str  # Full agent markdown definition
    capabilities: List[str]
    tailored_to: List[str]  # Project-specific patterns this addresses
    tools: List[str]  # Tools needed
    confidence: float  # 0.0-1.0 (AI confidence in generation)
    generated_at: datetime = None
    based_on_examples: List[str] = None  # Example files used for generation
    source: AgentSource = AgentSource.GENERATED
    priority: AgentPriority = AgentPriority.MEDIUM
```

### Example JSON

```json
{
  "name": "maui-appshell-navigator",
  "description": "Specialist in .NET MAUI AppShell navigation for this project architecture",
  "content": "---\nname: maui-appshell-navigator\n...",
  "capabilities": ["maui", "appshell", "navigation", "deep-linking"],
  "tailored_to": [
    "Route registration pattern: Routing.RegisterRoute(...)",
    "Page naming: {{Verb}}{{Entity}}Page",
    "ViewModel binding conventions"
  ],
  "tools": ["Read", "Write", "Edit", "Grep"],
  "confidence": 0.88,
  "generated_at": "2025-11-01T15:50:00Z",
  "based_on_examples": [
    "src/Presentation/Views/ProductListPage.xaml",
    "src/Presentation/AppShell.xaml.cs"
  ],
  "source": "generated",
  "priority": 1
}
```

### Validation Rules

```python
class GeneratedAgentValidator(Validator):
    def validate(self, agent: GeneratedAgent) -> ValidationResult:
        errors = []
        warnings = []

        if not agent.name:
            errors.append("name is required")

        if not agent.content:
            errors.append("content is required")

        if not (0.0 <= agent.confidence <= 1.0):
            errors.append(f"confidence must be 0.0-1.0, got {agent.confidence}")

        if agent.confidence < 0.7:
            warnings.append(f"Low confidence in generated agent: {agent.confidence}")

        if not agent.capabilities:
            errors.append("At least one capability is required")

        if not agent.tailored_to:
            warnings.append("Agent has no project-specific tailoring")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## DiscoveredAgent

**Source**: TASK-004B (External Agent Discovery - Phase 2)
**Used By**: TASK-004B → TASK-009
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class DiscoveredAgent:
    """Externally discovered agent (community)"""

    name: str
    source_url: str  # Where it was discovered
    description: str
    capabilities: List[str]
    download_count: Optional[int] = None
    rating: Optional[float] = None  # 0.0-5.0
    confidence: float = 0.0  # 0.0-1.0 (extraction confidence)
    content: Optional[str] = None  # Full definition if downloaded
    author: Optional[str] = None
    discovered_at: datetime = None
    source: AgentSource = AgentSource.EXTERNAL
    priority: AgentPriority = AgentPriority.LOW
```

### Example JSON

```json
{
  "name": "maui-testing-specialist",
  "source_url": "https://subagents.cc/maui-testing-specialist",
  "description": "MAUI testing with Appium and xUnit patterns",
  "capabilities": ["maui", "testing", "appium", "ui-testing"],
  "download_count": 98,
  "rating": 4.5,
  "confidence": 0.82,
  "content": null,
  "author": "community-contributor",
  "discovered_at": "2025-11-01T15:55:00Z",
  "source": "external",
  "priority": 0
}
```

---

## AgentRecommendation

**Source**: TASK-009 (Agent Orchestration)
**Used By**: TASK-009 → TASK-010, TASK-011
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class AgentRecommendation:
    """Complete agent recommendation for template"""

    schema_version: str = "1.0.0"

    # Agents to use (by priority)
    use_existing: List[AgentInfo]  # From inventory (custom/template/global)
    newly_generated: List[GeneratedAgent]  # AI-created for this project
    optional_suggestions: List[AgentSuggestion]  # External options

    # Deduplication results
    skipped_duplicates: Dict[str, str]  # name → reason skipped
    conflicts_resolved: Dict[str, str]  # name → resolution

    # Metadata
    total_count: int = 0
    recommended_at: datetime = None
    external_discovery_enabled: bool = False
```

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "use_existing": [
    {
      "name": "architectural-reviewer",
      "source": "global",
      "priority": 1,
      "capabilities": ["architecture", "review"]
    }
  ],
  "newly_generated": [
    {
      "name": "maui-appshell-navigator",
      "description": "MAUI AppShell navigation specialist",
      "capabilities": ["maui", "navigation"],
      "confidence": 0.88
    }
  ],
  "optional_suggestions": [
    {
      "agent": {
        "name": "xaml-performance-analyzer",
        "source_url": "https://github.com/user/agents",
        "description": "XAML performance profiling"
      },
      "reason": "Complementary capability not currently needed",
      "user_decision": "pending"
    }
  ],
  "skipped_duplicates": {
    "react-specialist": "You have custom mycompany-react-specialist"
  },
  "conflicts_resolved": {},
  "total_count": 2,
  "recommended_at": "2025-11-01T16:00:00Z",
  "external_discovery_enabled": false
}
```

### Methods

```python
class AgentRecommendation:
    def all_agents(self) -> List[Union[AgentInfo, GeneratedAgent]]:
        """Get all recommended agents (excluding optional)"""
        agents = []
        agents.extend(self.use_existing)
        agents.extend(self.newly_generated)
        return agents

    def save_to_template(self, template_dir: Path):
        """Save all agents to template directory"""
        agents_dir = template_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        for agent in self.all_agents():
            agent_file = agents_dir / f"{agent.name}.md"
            content = agent.full_definition if hasattr(agent, 'full_definition') else agent.content
            agent_file.write_text(content)
```

### Validation Rules

```python
class AgentRecommendationValidator(Validator):
    def validate(self, rec: AgentRecommendation) -> ValidationResult:
        errors = []
        warnings = []

        if not rec.use_existing and not rec.newly_generated:
            errors.append("Recommendation must include at least one agent")

        # Validate all agents
        for agent in rec.use_existing:
            result = AgentInfoValidator().validate(agent)
            if not result.is_valid:
                errors.extend([f"use_existing.{e}" for e in result.errors])

        for agent in rec.newly_generated:
            result = GeneratedAgentValidator().validate(agent)
            if not result.is_valid:
                errors.extend([f"newly_generated.{e}" for e in result.errors])

        # Check for duplicates within recommendation
        all_names = [a.name for a in rec.all_agents()]
        if len(all_names) != len(set(all_names)):
            errors.append("Duplicate agent names in recommendation")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## AgentSuggestion

**Purpose**: Represent an optional external agent suggestion
**Part Of**: AgentRecommendation

### Structure

```python
class UserDecision(Enum):
    """User's decision on suggestion"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PREVIEW = "preview"

@dataclass
class AgentSuggestion:
    """Optional agent suggestion"""

    agent: DiscoveredAgent
    reason: str  # Why this is suggested
    alternatives: List[str] = None  # Similar agents already in use
    user_decision: UserDecision = UserDecision.PENDING
```

### Example JSON

```json
{
  "agent": {
    "name": "maui-testing-specialist",
    "source_url": "https://subagents.cc/maui-testing-specialist",
    "description": "MAUI testing with Appium",
    "capabilities": ["maui", "testing", "appium"]
  },
  "reason": "Similar to test-verifier but includes Appium patterns",
  "alternatives": ["test-verifier"],
  "user_decision": "pending"
}
```

---

## Usage Example

```python
# Phase 1: Scan all sources (TASK-003)
from agent_scanner import MultiSourceAgentScanner

scanner = MultiSourceAgentScanner(
    project_root=Path.cwd(),
    template_path=None  # or Path to template
)
inventory: AgentInventory = scanner.scan()

# Phase 2: Generate missing agents (TASK-004A)
from agent_generator import AIAgentGenerator

generator = AIAgentGenerator(analysis=codebase_analysis)
generated: List[GeneratedAgent] = generator.generate_for_gaps(inventory)

# Phase 3: Orchestrate recommendation (TASK-009)
from agent_orchestration import AgentOrchestrator

orchestrator = AgentOrchestrator(
    inventory=inventory,
    generated_agents=generated,
    enable_external=False  # Phase 1, default OFF
)
recommendation: AgentRecommendation = orchestrator.recommend()

# Validate
validator = AgentRecommendationValidator()
result = validator.validate(recommendation)

if not result.is_valid:
    raise ValidationError(result.errors)

# Save to template
recommendation.save_to_template(template_dir)
```

---

## Priority and Deduplication

### Priority Rules

```python
# Agent priority (highest to lowest)
PRIORITY_ORDER = [
    AgentSource.CUSTOM,     # User's .claude/agents/ (Priority 3)
    AgentSource.TEMPLATE,   # Template-specific (Priority 2)
    AgentSource.GLOBAL,     # Built-in global (Priority 1)
    AgentSource.GENERATED,  # AI-generated (Priority 1)
    AgentSource.EXTERNAL    # Community (Priority 0)
]
```

### Deduplication Logic

```python
class AgentDeduplicator:
    """Handle agent deduplication"""

    def deduplicate(self, inventory: AgentInventory) -> AgentInventory:
        """Remove duplicate agents, keeping highest priority"""

        seen_names = set()
        skipped = {}

        # Process in priority order
        for source in PRIORITY_ORDER:
            agents = self._get_agents_by_source(inventory, source)

            for agent in agents:
                if agent.name in seen_names:
                    # Skip duplicate, keep higher priority version
                    skipped[agent.name] = f"Duplicate of {source.value} agent (kept higher priority)"
                else:
                    seen_names.add(agent.name)

        inventory.deduplication_applied = True
        return inventory

    def check_similarity(self, agent1: AgentInfo, agent2: AgentInfo) -> float:
        """Check semantic similarity between agents (0.0-1.0)"""
        # Compare capabilities
        caps1 = set(agent1.capabilities)
        caps2 = set(agent2.capabilities)

        if not caps1 or not caps2:
            return 0.0

        intersection = len(caps1 & caps2)
        union = len(caps1 | caps2)

        return intersection / union if union > 0 else 0.0
```

---

## Testing

```python
# tests/test_agent_contracts.py

def test_agent_inventory_creation():
    """Test AgentInventory creation"""
    inventory = AgentInventory(
        custom_agents=[create_mock_agent_info("custom-agent", "custom")],
        global_agents=[create_mock_agent_info("global-agent", "global")],
        total_count=2
    )

    assert len(inventory.all_agents()) == 2
    assert inventory.find_by_name("custom-agent") is not None

def test_agent_priority():
    """Test agent priority ordering"""
    custom = create_mock_agent_info("agent", "custom")
    global_agent = create_mock_agent_info("agent", "global")

    assert custom.priority > global_agent.priority

def test_generated_agent_validation():
    """Test generated agent validation"""
    validator = GeneratedAgentValidator()

    # Valid
    valid = GeneratedAgent(
        name="test-agent",
        description="Test agent",
        content="# Test Agent",
        capabilities=["test"],
        tailored_to=["pattern1"],
        tools=["Read"],
        confidence=0.9
    )
    result = validator.validate(valid)
    assert result.is_valid

    # Low confidence (valid but warns)
    low_conf = GeneratedAgent(
        name="test-agent",
        description="Test",
        content="# Test",
        capabilities=["test"],
        tailored_to=[],
        tools=["Read"],
        confidence=0.6
    )
    result = validator.validate(low_conf)
    assert result.is_valid
    assert len(result.warnings) > 0

def test_agent_recommendation():
    """Test agent recommendation"""
    rec = AgentRecommendation(
        use_existing=[create_mock_agent_info("existing", "global")],
        newly_generated=[create_mock_generated_agent()],
        optional_suggestions=[],
        total_count=2
    )

    assert len(rec.all_agents()) == 2

    # Validate
    validator = AgentRecommendationValidator()
    result = validator.validate(rec)
    assert result.is_valid

def test_deduplication():
    """Test deduplication logic"""
    dedup = AgentDeduplicator()

    inventory = AgentInventory(
        custom_agents=[create_mock_agent_info("react-specialist", "custom")],
        global_agents=[create_mock_agent_info("react-specialist", "global")],  # Duplicate
        total_count=2
    )

    deduplicated = dedup.deduplicate(inventory)

    # Should keep custom (higher priority), skip global
    all_agents = deduplicated.all_agents()
    assert len(all_agents) == 1
    assert all_agents[0].source == AgentSource.CUSTOM
```

---

**Created**: 2025-11-01
**Status**: ✅ COMPLETE
**Next**: [template-contracts.md](template-contracts.md)
