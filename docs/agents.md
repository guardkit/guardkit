# Agent System

AI agent discovery, enhancement workflow, and boundary sections.

## Agent Discovery

GuardKit uses AI-powered agent discovery to automatically match tasks to appropriate specialists based on metadata.

### How It Works

1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans all agents for metadata match (stack + phase + keywords)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and why

### Discovery Metadata

Agents include frontmatter metadata for automatic discovery:

- `stack`: [python, react, dotnet, typescript, cross-stack, etc.]
- `phase`: implementation | review | testing | orchestration | debugging
- `capabilities`: List of specific skills
- `keywords`: Searchable terms for matching

### Example: Agent Selection

```bash
/task-work TASK-042  # Task involves Python API implementation

# System analyzes:
# - Files: *.py (Python detected)
# - Keywords: "API endpoint", "FastAPI"
# - Phase: Implementation (Phase 3)

# Discovery matches:
# - Stack: python ✓
# - Phase: implementation ✓
# - Capabilities: api, async-patterns, pydantic ✓

# Selected: python-api-specialist
```

**[Agent Discovery Guide](guides/agent-discovery-guide.md)** - Comprehensive documentation.

## Stack-Specific Implementation Agents (Haiku Model)

Fast, cost-effective agents for implementation:

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

## Agent Enhancement

### Enhancement Commands

| Command | Purpose | Quality | Duration |
|---------|---------|---------|----------|
| `/agent-format` | Format to template standards | 6/10 | Instant |
| `/agent-enhance` | Project-specific enhancement | 9/10 | 2-5 min |
| `/agent-validate` | Quality validation | N/A | 1-2 min |

### Two-Tier Enhancement System

**Tier 1: Template-Level (`/agent-format`)**

- Instant formatting to template standards
- Quality: 6/10 (functional, not polished)
- Use during `/template-create` Phase 5.5

**Tier 2: Project-Level (`/agent-enhance`)**

- AI-powered, project-specific enhancement
- Quality: 9/10 (production-ready)
- Use after template initialization

### Agent Boundary Sections

All enhanced agents include **ALWAYS/NEVER/ASK boundary sections** (GitHub best practices, Critical Gap #4 fixed).

**Format:**

- **ALWAYS** (5-7 rules): Non-negotiable actions
- **NEVER** (5-7 rules): Prohibited actions
- **ASK** (3-5 scenarios): Situations requiring human escalation

**Example: Testing Agent**

```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity
- ⚠️ Performance tests failing: Ask if acceptable for non-production
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

**[Agent Enhancement with Boundary Sections](https://github.com/guardkit/guardkit/blob/main/CLAUDE.md#agent-enhancement-with-boundary-sections)** - Complete documentation.

## Guides

### 📖 [Agent Discovery Guide](guides/agent-discovery-guide.md)

Comprehensive documentation on how agent discovery works.

### 🎯 [Agent Enhancement Decision Guide](guides/agent-enhancement-decision-guide.md)

When to use /agent-format vs /agent-enhance.

### 🔄 [Incremental Enhancement Workflow](workflows/incremental-enhancement-workflow.md)

Step-by-step workflow for enhancing agents from 6/10 to 9/10.

### 📊 GitHub Agent Best Practices

Based on [analysis of 2,500+ repositories](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/), boundary sections were identified as Critical Gap #4. All enhanced agents now include ALWAYS/NEVER/ASK boundaries.

## Commands

- **[/agent-format](https://github.com/guardkit/guardkit/blob/main/installer/global/commands/agent-format.md)**: Format agent to template standards
- **[/agent-enhance](https://github.com/guardkit/guardkit/blob/main/installer/global/commands/agent-enhance.md)**: Project-specific enhancement
- **[/agent-validate](https://github.com/guardkit/guardkit/blob/main/installer/global/commands/agent-validate.md)**: Quality validation

---

## Next Steps

- **Learn Discovery**: [Agent Discovery Guide](guides/agent-discovery-guide.md)
- **Enhance Agents**: [Incremental Enhancement Workflow](workflows/incremental-enhancement-workflow.md)
- **Validate Quality**: Run `/agent-validate` on your agents
