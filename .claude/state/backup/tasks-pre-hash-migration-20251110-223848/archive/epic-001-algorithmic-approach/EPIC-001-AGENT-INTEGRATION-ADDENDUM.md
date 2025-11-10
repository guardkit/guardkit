# EPIC-001 Agent Integration Addendum

**Date**: 2025-11-01
**Focus**: Reusing existing agents + Configurable agent sources

---

## Overview

Two critical enhancements to agent discovery system:

1. **Reuse Existing Agents**: Integrate 15 existing taskwright agents into template orchestration
2. **Configurable Sources**: Allow custom agent source URLs (not hardcoded to 3 sources)

---

## Part 1: Existing Taskwright Agents

### Current Inventory

**15 Global Agents Already Defined** in `installer/global/agents/`:

| Agent | Category | Use Case |
|-------|----------|----------|
| architectural-reviewer.md | Architecture | Phase 2.5 architecture review |
| build-validator.md | Quality | Compilation and build verification |
| code-reviewer.md | Quality | Code quality review |
| complexity-evaluator.md | Planning | Task complexity evaluation |
| database-specialist.md | Specialized | Database design and optimization |
| debugging-specialist.md | Development | Systematic debugging |
| devops-specialist.md | Infrastructure | CI/CD, deployment, monitoring |
| figma-react-orchestrator.md | UX | Figma → React component generation |
| pattern-advisor.md | Architecture | Design pattern recommendations |
| python-mcp-specialist.md | Specialized | MCP server development |
| security-specialist.md | Quality | Security analysis and hardening |
| task-manager.md | Core | Task workflow management |
| test-orchestrator.md | Quality | Test execution orchestration |
| test-verifier.md | Quality | Test verification |
| zeplin-maui-orchestrator.md | UX | Zeplin → MAUI generation |

---

## Problem: Current Design Ignores Local Agents

### Current Flow (TASK-048-052)

```
Agent Discovery:
1. Scrape subagents.cc → List[AgentMetadata]
2. Parse GitHub repos → List[AgentMetadata]
3. Match & score agents
4. User selects agents
5. Download agents to template/agents/

❌ Problem: Completely ignores 15 existing taskwright agents!
```

**Why This Is Wrong**:
- `architectural-reviewer` is PERFECT for template orchestration
- `code-reviewer` should be included in generated templates
- `test-orchestrator` and `test-verifier` are quality gates
- `pattern-advisor` helps with architecture decisions
- **We're reinventing the wheel by downloading external agents!**

---

## Solution 1: Local-First Agent Discovery

### Updated Agent Discovery Flow

```
Phase 1: Local Agent Discovery (NEW)
├─ Scan installer/global/agents/
├─ Scan .claude/agents/ (project-specific)
└─→ List[LocalAgent]

Phase 2: Remote Agent Discovery (existing)
├─ Scrape subagents.cc
├─ Parse GitHub repos
└─→ List[RemoteAgent]

Phase 3: Combine & Deduplicate
├─ Merge local + remote
├─ Remove duplicates (prefer local)
└─→ Unified List[AgentMetadata]

Phase 4: Match & Score (existing)
└─→ Ranked agents

Phase 5: Selection with Local Priority
├─ Show local agents first (already vetted)
├─ Show remote agents second (external)
└─ User selects
```

---

### 🔧 TASK-048B: Local Agent Scanner (NEW)

**Objective**: Discover and integrate existing taskwright agents

**Estimated**: 4 hours | **Complexity**: 4/10 | **Priority**: HIGH

**Acceptance Criteria**:
- [ ] Scans `installer/global/agents/*.md`
- [ ] Scans `.claude/agents/*.md` (project-specific)
- [ ] Parses agent frontmatter (name, description, tools)
- [ ] Returns `List[LocalAgent]` compatible with `AgentMetadata`
- [ ] Marks agents as `source: "local_global"` or `source: "local_project"`

**Implementation**:

```python
# installer/global/commands/lib/agent_discovery/local_scanner.py

from pathlib import Path
import frontmatter

class LocalAgentScanner:
    def scan_agents(self) -> List[AgentMetadata]:
        agents = []

        # Scan global agents
        global_agents = self._scan_directory(
            Path(__file__).parent.parent.parent / "installer/global/agents",
            source="local_global"
        )
        agents.extend(global_agents)

        # Scan project agents (if in project)
        if Path(".claude/agents").exists():
            project_agents = self._scan_directory(
                Path(".claude/agents"),
                source="local_project"
            )
            agents.extend(project_agents)

        return agents

    def _scan_directory(self, path: Path, source: str) -> List[AgentMetadata]:
        agents = []

        for agent_file in path.glob("*.md"):
            try:
                with open(agent_file, 'r') as f:
                    post = frontmatter.load(f)

                # Extract metadata from frontmatter or content
                name = post.get('name', agent_file.stem)
                description = post.get('description', self._extract_first_line(post.content))
                tools = post.get('tools', [])
                category = post.get('category', 'general')

                agents.append(AgentMetadata(
                    name=name,
                    description=description,
                    category=category,
                    tools=tools,
                    source_url=str(agent_file),  # Local path
                    source=source,
                    downloads=0,  # N/A for local
                    favorites=0,  # N/A for local
                    last_updated=str(agent_file.stat().st_mtime)
                ))

            except Exception as e:
                logger.warning(f"Failed to parse {agent_file}: {e}")
                continue

        return agents

    def _extract_first_line(self, content: str) -> str:
        """Extract first meaningful line as description"""
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:200]
        return "No description available"
```

**Integration with TASK-050**:

```python
# Updated agent matching (TASK-050)

class AgentMatcher:
    def match_agents(self, all_agents, stack_result, arch_result):
        scored_agents = []

        for agent in all_agents:
            score = 0

            # Local agents get bonus (already vetted for taskwright)
            if agent.source.startswith("local"):
                score += 20  # +20 bonus for local agents

            # Technology match (40%)
            score += self._score_technology(agent, stack_result) * 0.4

            # Pattern match (30%)
            score += self._score_patterns(agent, arch_result) * 0.3

            # ... rest of scoring

            if score >= 60:
                scored_agents.append({
                    'agent': agent,
                    'score': int(score),
                    'is_local': agent.source.startswith("local")
                })

        return sorted(scored_agents, key=lambda x: (x['is_local'], x['score']), reverse=True)
```

**UI Display**:

```
📊 Found 28 agents from 4 sources:
   - local_global: 15 agents (taskwright built-in)
   - local_project: 2 agents (project-specific)
   - subagents.cc: 8 agents
   - github: 3 agents

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ TASKWRIGHT BUILT-IN (15 agents - already integrated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[x] architectural-reviewer               Score: 95
    Source: taskwright (local_global)
    SOLID/DRY/YAGNI compliance review
    Tools: Read, Analyze, Search

[x] code-reviewer                        Score: 92
    Source: taskwright (local_global)
    Code quality and standards enforcement
    Tools: Read, Write, Search, Grep

[x] test-orchestrator                    Score: 90
    Source: taskwright (local_global)
    Test execution and quality gates
    Tools: Read, Write, Bash, Search

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 EXTERNAL AGENTS (11 agents)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] react-state-specialist                Score: 88
    Source: subagents.cc (248 downloads)
    React state management expert
    Tools: Read, Write, Edit, Bash

Options:
  [A] Accept all taskwright built-in + recommended external (score ≥85)
  [T] Accept taskwright built-in only
  [C] Customize selection
```

---

### Recommended Local Agents for Templates

**Core Development** (Include in all templates):
- ✅ `task-manager` - Task workflow orchestration
- ✅ `code-reviewer` - Code quality enforcement

**Quality Assurance** (Include in quality-focused templates):
- ✅ `architectural-reviewer` - Architecture compliance
- ✅ `test-orchestrator` - Test execution
- ✅ `test-verifier` - Test verification
- ✅ `build-validator` - Compilation checks

**Architecture** (Include in complex templates):
- ✅ `software-architect` - System design
- ✅ `pattern-advisor` - Design pattern recommendations

**Specialized** (Include based on stack):
- ✅ `database-specialist` - Data-heavy applications
- ✅ `devops-specialist` - Infrastructure/deployment
- ✅ `security-specialist` - Security-critical applications
- ✅ `debugging-specialist` - Debugging support

**UX** (Include for UI-heavy applications):
- ✅ `figma-react-orchestrator` - React + Figma projects
- ✅ `zeplin-maui-orchestrator` - MAUI + Zeplin projects

---

## Part 2: Configurable Agent Sources

### Current Problem: Hardcoded Sources

**Current Design (TASK-048, 049)**:

```python
# Hardcoded in task implementation
sources = [
    "https://subagents.cc",
    "github:wshobson/agents",
    "github:VoltAgent/awesome-claude-code-subagents"
]

# ❌ Cannot add custom sources
# ❌ Cannot disable sources
# ❌ Cannot prioritize sources
```

---

### Solution 2: Configurable Agent Source Registry

### 🔧 TASK-048C: Configurable Agent Sources (NEW)

**Objective**: Allow users to configure custom agent source URLs

**Estimated**: 3 hours | **Complexity**: 3/10 | **Priority**: MEDIUM

**Configuration File**: `~/.agentecflow/agent-sources.json`

```json
{
  "version": "1.0",
  "sources": [
    {
      "id": "local_global",
      "name": "Taskwright Built-in",
      "type": "local",
      "path": "installer/global/agents",
      "enabled": true,
      "priority": 1,
      "bonus_score": 20
    },
    {
      "id": "local_project",
      "name": "Project Agents",
      "type": "local",
      "path": ".claude/agents",
      "enabled": true,
      "priority": 2,
      "bonus_score": 15
    },
    {
      "id": "subagents_cc",
      "name": "Subagents.cc Marketplace",
      "type": "web",
      "url": "https://subagents.cc",
      "enabled": true,
      "priority": 3,
      "cache_ttl": 900
    },
    {
      "id": "wshobson",
      "name": "wshobson/agents",
      "type": "github",
      "repo": "wshobson/agents",
      "branch": "main",
      "path": "agents",
      "enabled": true,
      "priority": 4,
      "cache_ttl": 3600
    },
    {
      "id": "voltagent",
      "name": "VoltAgent Awesome List",
      "type": "github",
      "repo": "VoltAgent/awesome-claude-code-subagents",
      "branch": "main",
      "path": "agents",
      "enabled": true,
      "priority": 5,
      "cache_ttl": 3600
    },
    {
      "id": "company_internal",
      "name": "MyCompany Internal Agents",
      "type": "github",
      "repo": "mycompany/claude-agents",
      "branch": "main",
      "path": "agents",
      "enabled": true,
      "priority": 6,
      "cache_ttl": 1800,
      "auth": "env:GITHUB_TOKEN"
    },
    {
      "id": "custom_url",
      "name": "Custom Agent Repository",
      "type": "http",
      "url": "https://my-internal-server.com/agents/index.json",
      "enabled": false,
      "priority": 7,
      "auth": "env:CUSTOM_API_KEY"
    }
  ],
  "defaults": {
    "cache_ttl": 900,
    "timeout": 30,
    "max_retries": 3
  }
}
```

**Implementation**:

```python
# installer/global/commands/lib/agent_discovery/source_registry.py

from pathlib import Path
import json
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class AgentSource:
    id: str
    name: str
    type: str  # local, web, github, http
    enabled: bool
    priority: int
    bonus_score: int = 0
    cache_ttl: int = 900
    # Type-specific fields
    path: str = None
    url: str = None
    repo: str = None
    branch: str = "main"
    auth: str = None

class AgentSourceRegistry:
    CONFIG_PATH = Path.home() / ".agentecflow" / "agent-sources.json"

    def __init__(self):
        self.sources = self._load_sources()

    def _load_sources(self) -> List[AgentSource]:
        """Load agent sources from config file"""

        if not self.CONFIG_PATH.exists():
            # Create default configuration
            self._create_default_config()

        with open(self.CONFIG_PATH, 'r') as f:
            config = json.load(f)

        sources = []
        for source_data in config['sources']:
            if source_data['enabled']:
                sources.append(AgentSource(**source_data))

        # Sort by priority
        return sorted(sources, key=lambda x: x.priority)

    def get_enabled_sources(self) -> List[AgentSource]:
        """Get all enabled sources, sorted by priority"""
        return [s for s in self.sources if s.enabled]

    def add_source(self, source: AgentSource):
        """Add new agent source to registry"""
        self.sources.append(source)
        self._save_sources()

    def disable_source(self, source_id: str):
        """Disable an agent source"""
        for source in self.sources:
            if source.id == source_id:
                source.enabled = False
        self._save_sources()

    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "version": "1.0",
            "sources": [
                {
                    "id": "local_global",
                    "name": "Taskwright Built-in",
                    "type": "local",
                    "path": "installer/global/agents",
                    "enabled": True,
                    "priority": 1,
                    "bonus_score": 20
                },
                {
                    "id": "subagents_cc",
                    "name": "Subagents.cc",
                    "type": "web",
                    "url": "https://subagents.cc",
                    "enabled": True,
                    "priority": 3,
                    "cache_ttl": 900
                },
                # ... etc
            ],
            "defaults": {
                "cache_ttl": 900,
                "timeout": 30,
                "max_retries": 3
            }
        }

        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(default_config, f, indent=2)
```

**Updated Agent Discovery Orchestrator**:

```python
# installer/global/commands/lib/agent_discovery/orchestrator.py

class AgentDiscoveryOrchestrator:
    def __init__(self):
        self.registry = AgentSourceRegistry()

    def discover_all_agents(self, stack_result, arch_result):
        """Discover agents from all enabled sources"""

        all_agents = []

        for source in self.registry.get_enabled_sources():
            try:
                if source.type == "local":
                    agents = self._discover_local(source)
                elif source.type == "web":
                    agents = self._discover_web(source)
                elif source.type == "github":
                    agents = self._discover_github(source)
                elif source.type == "http":
                    agents = self._discover_http(source)

                # Apply bonus score for priority sources
                for agent in agents:
                    agent.bonus_score = source.bonus_score

                all_agents.extend(agents)

            except Exception as e:
                logger.warning(f"Failed to discover from {source.name}: {e}")
                continue

        return all_agents

    def _discover_local(self, source):
        """Discover from local directory"""
        scanner = LocalAgentScanner()
        return scanner.scan_directory(source.path, source.id)

    def _discover_web(self, source):
        """Discover from web URL"""
        scraper = SubagentsCcScraper()  # or generic scraper
        return scraper.scrape(source.url)

    def _discover_github(self, source):
        """Discover from GitHub repository"""
        parser = GitHubAgentParser(source.repo, source.branch, source.path, source.auth)
        return parser.parse_agents()

    def _discover_http(self, source):
        """Discover from HTTP JSON endpoint"""
        response = requests.get(source.url, headers={'Authorization': self._get_auth(source.auth)})
        return [AgentMetadata(**agent) for agent in response.json()]
```

---

### CLI Commands for Source Management

```bash
# List configured sources
/template-sources list

# Add custom source
/template-sources add \
  --id mycompany-agents \
  --name "MyCompany Agents" \
  --type github \
  --repo mycompany/claude-agents \
  --priority 6

# Disable source
/template-sources disable subagents_cc

# Enable source
/template-sources enable subagents_cc

# Test source (check connectivity)
/template-sources test mycompany-agents
```

---

## Updated Task Dependencies

### New Tasks

**TASK-048B**: Local Agent Scanner
- **Depends**: None
- **Blocks**: TASK-050 (needs local agents)
- **Priority**: HIGH
- **Estimated**: 4 hours

**TASK-048C**: Configurable Agent Sources
- **Depends**: None
- **Blocks**: TASK-048, TASK-049 (uses source registry)
- **Priority**: MEDIUM
- **Estimated**: 3 hours

### Updated Existing Tasks

**TASK-050** (Agent Matching):
- Add: Bonus scoring for local agents (+20 points)
- Add: Sort by (is_local, score) instead of just score

**TASK-051** (Selection UI):
- Add: Group agents by source (Local first, then external)
- Add: Show source name and priority
- Add: Option to accept "Taskwright built-in only"

**TASK-047** (template-create orchestrator):
- Add: Uses AgentDiscoveryOrchestrator (respects source registry)

**TASK-060** (template-init orchestrator):
- Add: Uses AgentDiscoveryOrchestrator

---

## Benefits

### 1. Reuse Existing Agents ✅

**Before**:
- 15 taskwright agents ignored
- Download external agents from scratch
- Reinvent the wheel

**After**:
- 15 taskwright agents automatically discovered
- Prioritized in selection (bonus +20 points)
- Templates include battle-tested agents

### 2. Configurable Sources ✅

**Before**:
- 3 hardcoded sources
- Cannot add company-internal agents
- Cannot disable sources

**After**:
- Unlimited custom sources
- Company-internal repositories supported
- GitHub private repos with auth
- HTTP endpoints for custom registries
- Enable/disable per source

### 3. Enterprise-Ready ✅

**Company Use Case**:
```json
{
  "sources": [
    {
      "id": "company_core",
      "name": "MyCompany Core Agents",
      "type": "github",
      "repo": "mycompany/core-agents",
      "priority": 1,
      "bonus_score": 30,
      "auth": "env:GITHUB_TOKEN"
    },
    {
      "id": "company_team",
      "name": "Platform Team Agents",
      "type": "github",
      "repo": "mycompany/platform-agents",
      "priority": 2,
      "bonus_score": 25
    },
    {
      "id": "subagents_cc",
      "enabled": false  // Disable external sources for compliance
    }
  ]
}
```

---

## Recommended Implementation Order

1. **TASK-048B** (Local Scanner) - 4 hours
   - Immediate value: Integrate 15 existing agents
2. **TASK-048C** (Configurable Sources) - 3 hours
   - Foundation for extensibility
3. **Update TASK-050** (Bonus scoring) - 1 hour
4. **Update TASK-051** (UI grouping) - 1 hour

**Total**: 9 hours additional effort

---

## Success Criteria

### Must Have
- [ ] 15 taskwright agents discovered automatically
- [ ] Local agents prioritized in selection
- [ ] Agent sources configurable via JSON
- [ ] Can add company-internal GitHub repos
- [ ] Can disable external sources

### Should Have
- [ ] CLI commands for source management
- [ ] Authentication for private repos
- [ ] HTTP endpoint support for custom registries

### Nice to Have
- [ ] Web UI for source configuration
- [ ] Agent source validation on save
- [ ] Automatic source health checks

---

## Conclusion

**Impact**:
- ✅ Reuses 15 existing taskwright agents (battle-tested)
- ✅ Allows unlimited custom agent sources
- ✅ Enterprise-ready (private repos, auth, compliance)
- ✅ Reduces external dependencies
- ✅ Improves template quality with proven agents

**Effort**: +9 hours (2 new tasks + 2 updates)

**Recommendation**: **IMPLEMENT** both enhancements before v1 release

---

**Created**: 2025-11-01
**Priority**: HIGH
**Impact**: HIGH
