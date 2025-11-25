---
id: TASK-HAI-007-8B1F
title: Update Documentation for Discovery and Haiku Agents
status: backlog
priority: high
tags: [haiku-agents, documentation, discovery, metadata]
epic: haiku-agent-implementation
complexity: 3
estimated_hours: 1.5
dependencies: [TASK-HAI-006]
blocks: [TASK-HAI-008]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Update Documentation for Discovery and Haiku Agents

## Context

Update project documentation to reflect AI-powered discovery system and new stack-specific Haiku agents. This ensures users understand how specialist agents are selected, the cost/speed benefits, and how to leverage the discovery system.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 3 (Finalization)
**Method**: Direct Claude Code implementation (writing task)
**Workspace**: WS-E (Conductor workspace - checkpoint merge after Wave 2)

## Objectives

1. Update `CLAUDE.md` - Agent discovery section
2. Update `docs/deep-dives/model-optimization.md` - Add Haiku agent details
3. Update `README.md` - Mention discovery system
4. Create `docs/guides/agent-discovery-guide.md` - Comprehensive guide
5. Update agent metadata schema documentation

## Files to Update

### 1. CLAUDE.md (Root-level project instructions)

**Section**: Core AI Agents (around line 380)

**Changes**:
```markdown
## Core AI Agents

### Agent Discovery System

Taskwright uses AI-powered agent discovery to automatically match tasks to appropriate specialists based on metadata (stack, phase, capabilities, keywords). No hardcoded mappings - discovery is intelligent and extensible.

**How It Works:**
1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans all agents for metadata match (stack + phase + keywords)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and why

**Discovery Metadata** (frontmatter in agent files):
- `stack`: [python, react, dotnet, typescript, etc.]
- `phase`: implementation | review | testing | orchestration
- `capabilities`: List of specific skills
- `keywords`: Searchable terms for matching

**Graceful Degradation**: Agents without metadata are skipped (no errors). System works during migration.

### Stack-Specific Implementation Agents (Haiku Model)

**Python Stack:**
- **python-api-specialist**: FastAPI endpoints, async patterns, Pydantic schemas

**React Stack:**
- **react-state-specialist**: React hooks, TanStack Query, state management

**.NET Stack:**
- **dotnet-domain-specialist**: Domain models, DDD patterns, value objects

**Benefits:**
- 4-5x faster implementation (Haiku vs Sonnet)
- 48-53% total cost savings (vs all-Sonnet)
- 90%+ quality maintained via Phase 4.5 test enforcement

### Global Agents
- **architectural-reviewer**: SOLID/DRY/YAGNI compliance review (Sonnet)
- **task-manager**: Unified workflow management (Sonnet)
- **test-verifier/orchestrator**: Test execution and quality gates (Sonnet)
... [existing agents]
```

### 2. docs/deep-dives/model-optimization.md

**Section**: Stack-Specific Agents (around line 206)

**Changes**:
```markdown
## Stack-Specific Agents

### Implementation Status

**Completed** (as of Nov 2025):
- ✅ python-api-specialist (Haiku) - FastAPI, async, Pydantic
- ✅ react-state-specialist (Haiku) - Hooks, TanStack Query, Zustand
- ✅ dotnet-domain-specialist (Haiku) - DDD, entities, value objects

**Discovery System**:
- AI-powered matching via metadata (stack, phase, capabilities, keywords)
- Graceful degradation: works with agents with/without metadata
- Fallback: task-manager if no specialist found
- Context analysis: detects stack from file extensions, project structure, keywords

**Cost Impact**:
| Scenario | Cost per Task | vs Baseline | vs Current |
|----------|---------------|-------------|------------|
| All-Sonnet (baseline) | $0.45 | - | +50% |
| Current (33% Haiku) | $0.30 | -33% | - |
| **Target (70% Haiku)** | **$0.20** | **-48%** | **-33%** |

**Performance Impact**:
- Phase 3 speed: 4-5x faster with Haiku (code generation)
- Overall task time: 40-50% faster completion
- Quality: Maintained at 90%+ via Phase 4.5 test enforcement

**Future Expansion**:
- Go, Rust, Java specialists (as demand grows)
- Existing agent migration (optional, via `/agent-enhance`)
```

### 3. README.md

**Section**: Core Features (around line 15)

**Changes**:
```markdown
**Core Features:**
- **Quality Gates**: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- **AI Agent Discovery**: Automatic specialist matching via metadata (stack, phase, keywords)
- **Stack-Specific Optimization**: Haiku agents for 48-53% cost savings, 4-5x faster implementation
- **Simple Workflow**: Create → Work → Complete (3 commands)
- **AI Collaboration**: AI handles implementation, humans make decisions
- **No Ceremony**: Minimal process, maximum productivity
```

### 4. docs/guides/agent-discovery-guide.md (NEW FILE)

**Complete Guide Structure**:
```markdown
# Agent Discovery Guide

## Overview

Taskwright uses AI-powered agent discovery to automatically match tasks to appropriate specialist agents. This guide explains how discovery works, how to leverage it, and how to add discovery metadata to custom agents.

## How Discovery Works

### Phase 3 Discovery Flow

1. **Task Analysis**: Extract context from task
   - File extensions (`.py` → python, `.tsx` → react/typescript, `.cs` → dotnet)
   - Keywords in title/description (fastapi, hooks, entity, etc.)
   - Project structure (package.json, requirements.txt, *.csproj)

2. **Agent Scanning**: Find all agents with metadata
   - Global agents: `installer/global/agents/*.md`
   - Template agents: `installer/global/templates/*/agents/*.md`
   - User agents: `~/.agentecflow/agents/*.md`

3. **Metadata Matching**: Filter and rank
   - Phase match: Required (implementation/review/testing/orchestration)
   - Stack match: Optional but scored
   - Keyword match: Relevance scoring (more matches = higher rank)

4. **Selection**: Use best match or fallback
   - Specialist found → Use stack-specific Haiku agent
   - No match → Fallback to task-manager (Sonnet)

### Example Discovery Session

**Task**: "Add FastAPI endpoint for user registration"

**Files**: `src/api/users.py`, `src/models/user.py`

**Discovery Output**:
```
Phase 3: Implementation
└─ Analyzing task context...
   ├─ Detected stack: [python]
   ├─ Keywords: [fastapi, api, endpoint]
   └─ Found specialist: python-api-specialist (relevance: 3/5)

Using python-api-specialist for implementation (Haiku model)
└─ Specialized in: FastAPI endpoints, async patterns, Pydantic schemas
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

## Graceful Degradation

**Agents WITHOUT metadata**: Skipped during discovery (no errors)
**No agents found**: Fallback to task-manager
**Partial migration**: System works with mixed agent pool

## Troubleshooting

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

## See Also

- [Model Optimization Deep Dive](../deep-dives/model-optimization.md)
- [Agent Enhancement Guide](./agent-enhancement-guide.md)
- [CLAUDE.md - Core AI Agents](../../CLAUDE.md#core-ai-agents)
```

### 5. installer/global/commands/agent-enhance.md

**Section**: Add "Discovery Metadata" section

**Changes** (around line 60, after "Understanding Boundary Sections"):
```markdown
## Discovery Metadata

As of HAI-001 (Nov 2025), agents enhanced via `/agent-enhance` include **discovery metadata** for AI-powered agent matching.

**Added Fields** (frontmatter):
- `stack`: List of supported technology stacks (python, react, dotnet, etc.)
- `phase`: Agent role (implementation, review, testing, orchestration)
- `capabilities`: 5+ specific skills
- `keywords`: 5+ searchable terms for matching

**Benefits**:
- Automatic specialist selection in Phase 3
- No hardcoded mappings (extensible)
- 48-53% cost savings via Haiku agents
- 4-5x faster implementation

**Example**:
```yaml
---
name: python-api-specialist
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling patterns
keywords: [fastapi, async, endpoints, router, dependency-injection]
---
```

**See**: [Agent Discovery Guide](../../docs/guides/agent-discovery-guide.md)
```

## Acceptance Criteria

- [ ] `CLAUDE.md` updated with discovery system explanation
- [ ] `CLAUDE.md` lists 3 new stack-specific agents
- [ ] `docs/deep-dives/model-optimization.md` updated with implementation status
- [ ] `docs/deep-dives/model-optimization.md` includes cost impact table
- [ ] `README.md` mentions AI agent discovery in features
- [ ] `docs/guides/agent-discovery-guide.md` created (comprehensive guide)
- [ ] `installer/global/commands/agent-enhance.md` explains discovery metadata
- [ ] All documentation links are valid
- [ ] Code examples are accurate
- [ ] Terminology is consistent across all files

## Testing

```bash
# Verify links
grep -r "agent-discovery-guide.md" docs/ CLAUDE.md README.md

# Verify terminology consistency
grep -r "AI-powered discovery" docs/ CLAUDE.md
grep -r "discovery metadata" docs/ CLAUDE.md

# Verify code examples are valid
# (manually test Python API example)
```

## Implementation Notes

**Documentation Style**:
- Clear, concise explanations
- Real-world examples
- Cost/speed benefits quantified
- Troubleshooting guidance
- Links to related documentation

**Audience**:
- Users: Understand how discovery works
- Developers: Learn to add metadata to custom agents
- Blog readers: Understand value proposition

## Risk Assessment

**LOW Risk**: Documentation-only changes, no code impact

**Mitigations**:
- Review for accuracy
- Validate all links
- Test code examples

## Rollback Strategy

**If documentation errors**:
```bash
# Revert all documentation changes
git checkout CLAUDE.md README.md docs/
```

**Recovery Time**: <1 minute

## Reference Materials

- `CLAUDE.md` - Current documentation
- `docs/deep-dives/model-optimization.md` - Model strategy
- `tasks/backlog/haiku-agent-implementation/README.md` - Epic overview
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema spec

## Deliverables

1. Updated: `CLAUDE.md` (discovery system section)
2. Updated: `docs/deep-dives/model-optimization.md` (implementation status)
3. Updated: `README.md` (features section)
4. Created: `docs/guides/agent-discovery-guide.md` (comprehensive guide)
5. Updated: `installer/global/commands/agent-enhance.md` (metadata section)

## Success Metrics

- Documentation completeness: All sections updated
- Link validity: 100% working links
- Code example accuracy: All examples tested
- User clarity: Clear explanations for non-technical users
- Developer guidance: Complete API documentation

## Risk: LOW | Rollback: Revert files (<1 min)
