# Agent Discovery Guide

## Overview

GuardKit uses AI-powered agent discovery to automatically match tasks to appropriate specialist agents. This guide explains how discovery works, how to leverage it, and how to add discovery metadata to custom agents.

## How Discovery Works

### Phase 3 Discovery Flow

1. **Task Analysis**: Extract context from task
   - File extensions (`.py` -> python, `.tsx` -> react/typescript, `.cs` -> dotnet)
   - Keywords in title/description (fastapi, hooks, entity, etc.)
   - Project structure (package.json, requirements.txt, *.csproj)

2. **Agent Scanning**: Find all agents with metadata (in precedence order)
   - **Local agents**: `.claude/agents/*.md` *(Highest priority)*
   - User agents: `~/.agentecflow/agents/*.md`
   - Global agents: `installer/global/agents/*.md`
   - Template agents: `installer/global/templates/*/agents/*.md` *(Lowest priority)*

3. **Metadata Matching**: Filter and rank
   - Phase match: Required (implementation/review/testing/orchestration)
   - Stack match: Optional but scored
   - Keyword match: Relevance scoring (more matches = higher rank)

4. **Selection**: Use best match or fallback
   - Specialist found -> Use stack-specific Haiku agent
   - No match -> Fallback to task-manager (Sonnet)

### Example Discovery Session

**Task**: "Add FastAPI endpoint for user registration"

**Files**: `src/api/users.py`, `src/models/user.py`

**Discovery Output**:
```
Phase 3: Implementation
└─ Analyzing task context...
   ├─ Detected stack: [python]
   ├─ Keywords: [fastapi, api, endpoint]
   └─ Found specialist: fastapi-specialist (relevance: 3/5)

Using fastapi-specialist for implementation (Haiku model)
└─ Specialized in: FastAPI endpoints, async patterns, Pydantic schemas
└─ Source: template (fastapi-python)
```

## Agent Sources and Precedence

### Discovery Order

The agent discovery system scans 4 sources in priority order:

1. **Local** (`.claude/agents/`)  - **Highest Priority**
   - Created by `guardkit init <template>`
   - Project-specific customizations
   - **Always takes precedence** over all other sources

2. **User** (`~/.agentecflow/agents/`)
   - Personal agent library across all projects
   - Cross-project customizations
   - Overrides global and template agents

3. **Global** (`installer/global/agents/`)
   - Cross-stack agents only (orchestration, review, testing, debugging)
   - No stack-specific implementation agents
   - Fallback when local/user agents missing

4. **Template** (`installer/global/templates/*/agents/`)
   - Source definitions before initialization
   - Rarely invoked (templates copy to local on init)
   - Lowest priority

### Precedence Rule

**When duplicate agent names exist**: Local > User > Global > Template

The first agent found (highest priority) is used, and duplicates from lower priority sources are ignored.

### Precedence Examples

**Example 1: Local overrides template**
```
Local:    .claude/agents/fastapi-specialist.md (custom version)
Template: installer/global/templates/fastapi-python/agents/fastapi-specialist.md
Result:   Uses local version
```

**Example 2: User overrides template**
```
User:     ~/.agentecflow/agents/react-state-specialist.md (custom)
Template: installer/global/templates/react-typescript/agents/react-state-specialist.md
Result:   Uses user version
```

**Example 3: Fallback to cross-stack global**
```
Local:  (not found for Go stack)
Global: installer/global/agents/task-manager.md (cross-stack fallback)
Result: Uses task-manager as no Go-specific agent exists
```

**Example 4: Template agents discovered**
```
Project: Uses fastapi-python template
Local:   (not found)
Template: installer/global/templates/fastapi-python/agents/fastapi-specialist.md
Result:   Uses template agent for FastAPI implementation
```

## Discovery Metadata Schema

### Required Fields

**frontmatter (YAML)**:
```yaml
---
name: agent-name
stack: [python, react, dotnet]  # List of supported stacks
phase: implementation           # implementation | review | testing | orchestration
capabilities:                   # 5+ specific skills
  - Skill 1
  - Skill 2
keywords: [keyword1, keyword2]  # 5+ searchable terms
---
```

### Stack Values

**Supported stacks**:
- `python` - Python applications
- `react` - React frontend
- `dotnet`, `csharp` - .NET applications
- `typescript`, `javascript` - TypeScript/JavaScript
- `go` - Go applications
- `rust` - Rust applications
- `java` - Java applications
- `ruby` - Ruby applications
- `php` - PHP applications
- `cross-stack` - Works across multiple stacks

### Phase Values

- `implementation` - Creates/modifies code
- `review` - Analyzes code quality
- `testing` - Validates functionality
- `orchestration` - Coordinates workflows

## Adding Metadata to Custom Agents

### Using /agent-enhance

```bash
# Automatically adds discovery metadata
/agent-enhance ~/.agentecflow/agents/my-custom-agent.md
```

### Manual Metadata Addition

```markdown
---
name: my-custom-agent
description: Custom agent description
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

# Discovery metadata
stack: [python, react]
phase: implementation
capabilities:
  - Capability 1
  - Capability 2
  - Capability 3
  - Capability 4
  - Capability 5
keywords: [keyword1, keyword2, keyword3, keyword4, keyword5]
---

# Rest of agent content...
```

## Benefits

### Cost Savings
- Haiku agents: 80% cheaper than Sonnet ($1/$5 vs $3/$15 per M tokens)
- Phase 3 optimization: 70% of tokens with 80% cost reduction
- Total savings: 48-53% vs all-Sonnet baseline

### Speed Improvements
- Haiku: 4-5x faster than Sonnet for code generation
- Overall task completion: 40-50% faster

### Quality Maintenance
- Phase 4.5: Test enforcement ensures 100% pass rate
- Phase 2.5: Architectural review (Sonnet) catches design issues
- Result: 90%+ quality with Haiku implementation

## Available Specialists

> **Note**: Stack-specific agents are distributed across templates. Global agents are cross-stack only.

### Python Stack (via `fastapi-python` template)
| Agent | Capabilities | Keywords |
|-------|-------------|----------|
| **fastapi-specialist** | FastAPI endpoints, async patterns, Pydantic schemas | fastapi, async, endpoints, router, dependency-injection |
| **fastapi-database-specialist** | Database operations and query optimization | sqlalchemy, database, query, orm |
| **fastapi-testing-specialist** | Testing patterns and pytest integration | pytest, testing, fixtures, async-tests |

### React Stack (via `react-typescript` template)
| Agent | Capabilities | Keywords |
|-------|-------------|----------|
| **react-state-specialist** | React hooks, TanStack Query, state management | hooks, useState, useEffect, tanstack-query, zustand |
| **react-query-specialist** | TanStack Query patterns and cache management | query, cache, mutations, optimistic-updates |
| **form-validation-specialist** | React Hook Form + Zod patterns | forms, validation, zod, react-hook-form |
| **feature-architecture-specialist** | Feature-based organization | features, modules, boundaries |

### Next.js Stack (via `nextjs-fullstack` template)
| Agent | Capabilities | Keywords |
|-------|-------------|----------|
| **nextjs-fullstack-specialist** | Full-stack Next.js patterns | nextjs, server-components, app-router |
| **nextjs-server-components-specialist** | Server component patterns | rsc, server-components, streaming |
| **nextjs-server-actions-specialist** | Server action patterns | server-actions, mutations, forms |

## Graceful Degradation

**Agents WITHOUT metadata**: Skipped during discovery (no errors)
**No agents found**: Fallback to task-manager
**Partial migration**: System works with mixed agent pool

## Troubleshooting

### "Template agents not found after initialization"

**Symptom**: Agent not discovered after `guardkit init <template>`

**Possible causes**:
1. `.claude/agents/` directory missing or empty
2. Template initialization failed
3. Agent files not copied correctly

**Solutions**:
- Verify `.claude/agents/` directory exists: `ls .claude/agents/`
- Re-run template init: `guardkit init <template>`
- Check template has agents: `ls installer/global/templates/<template>/agents/`

### "Wrong agent selected (global instead of local)"

**Symptom**: Global agent used despite local customization

**Possible causes**:
1. Local agent has different filename than expected
2. Local agent missing required metadata (stack, phase)
3. Local agent metadata doesn't match task criteria

**Solutions**:
- Verify local agent filename matches global: `ls .claude/agents/`
- Check frontmatter has `stack`, `phase`, `capabilities`, `keywords`
- Use `/agent-enhance .claude/agents/<agent>.md` to fix metadata

### "No specialist found, using task-manager"

**Possible causes**:
1. Stack not detected (check file extensions, project structure)
2. No agent matches stack + phase
3. Agent metadata incomplete (missing stack or phase)

**Solutions**:
- Verify task has files with recognized extensions
- Check if specialist exists for your stack
- Add metadata to custom agents via `/agent-enhance`

### "Discovery skipped X agents without metadata"

**This is normal** during migration. Agents without metadata are skipped, system uses fallback. To fix:
```bash
/agent-enhance installer/global/agents/my-agent.md
```

## Advanced: Discovery API

```python
from installer.global.commands.lib.agent_discovery import discover_agents

# Find all implementation agents
agents = discover_agents(phase='implementation')

# Find Python specialists
python_agents = discover_agents(phase='implementation', stack=['python'])

# Find with keyword matching
fastapi_agents = discover_agents(
    phase='implementation',
    stack=['python'],
    keywords=['fastapi', 'async', 'endpoint']
)

# Results sorted by relevance score
print(agents[0]['name'])  # Highest ranked agent
```

## Future Expansion

**Planned Specialists**:
- Go: API, concurrency patterns
- Rust: Memory safety, performance
- Java: Spring Boot, enterprise patterns

**Migration Path**:
1. Create specialist agent with metadata
2. Deploy to `installer/global/agents/`
3. Discovery automatically includes in matching
4. No code changes required

## See Also

- [Model Optimization Deep Dive](../deep-dives/model-optimization.md)
- [Agent Enhancement Command](../../installer/global/commands/agent-enhance.md)
- [CLAUDE.md - Core AI Agents](../../CLAUDE.md#core-ai-agents)

---

**Last Updated**: 2025-11-27
**Document Version**: 1.1
**Related Tasks**: TASK-HAI-005-7A2E, TASK-ENF-P0-1, TASK-ENF-P0-2
