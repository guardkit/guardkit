# Agent Enhancement Decision Guide

## Overview

When creating or improving agent templates in Taskwright, you'll face two key decisions:

1. **Format vs Enhance**: Should you use `/agent-format` or `/agent-enhance`?
2. **Hybrid vs Task-Work**: Should you use the hybrid strategy or full workflow?

This guide helps you choose the right approach based on your needs, time constraints, and quality requirements.

**Learn agent enhancement in**:
- **2 minutes**: Quick Start - Decision matrices
- **10 minutes**: Core Concepts - Strategy comparisons
- **30 minutes**: Complete Reference - Use cases and best practices

---

## Quick Start (2 minutes)

### Decision 1: Format vs Enhance

| Need | Command | Duration | Quality |
|------|---------|----------|---------|
| Basic structure | `/agent-format` | Instant | 6/10 |
| Template-specific content | `/agent-enhance` | 2-5 min | 9/10 |
| Code examples | `/agent-enhance` | 2-5 min | 9/10 |
| Boundary sections | `/agent-enhance` | 2-5 min | 9/10 |

### Decision 2: Hybrid vs Task-Work

| Need | Approach | Duration | Reliability |
|------|----------|----------|-------------|
| Fast enhancement | `--hybrid` | 2-5 min | 100% (with fallback) |
| Full quality gates | `/task-work` | 30-60 min | 100% (comprehensive) |

**Recommended Default**: `/agent-enhance template-name/agent-name --hybrid`

---

## Core Concepts (10 minutes)

### Decision 1: /agent-format vs /agent-enhance

#### When to Use /agent-format

**Purpose**: Structural consistency and basic formatting

**Automatic in**:
- `/template-create` (Phase 5) - Ensures all agents have consistent structure

**Manual use cases**:
- Quick structural fixes (missing sections)
- Consistency across template agents
- Batch structural updates

**What it does**:
- Adds missing standard sections
- Ensures proper heading hierarchy
- Validates frontmatter metadata
- Does NOT add template-specific content

**Quality**: 6/10 (basic structure, no context-specific content)

**Duration**: Instant (<1 second)

**Example**:
```bash
# Format single agent (rarely needed - template-create does this)
/agent-format react-typescript/testing-specialist

# Check formatting without applying
/agent-format react-typescript/testing-specialist --dry-run
```

#### When to Use /agent-enhance

**Purpose**: Add template-specific content, code examples, and best practices

**Manual use cases**:
- Adding code examples from template files
- Adding boundary sections (ALWAYS/NEVER/ASK)
- Adding template-specific best practices
- Creating template-aware guidance

**What it does**:
- Analyzes template files for relevant patterns
- Generates code examples using actual template code
- Adds boundary sections with validation
- Creates "Related Templates" section
- Adds anti-patterns and best practices

**Quality**: 9/10 (AI-powered, template-aware)

**Duration**: 2-5 minutes per agent

**Example**:
```bash
# Enhance with AI (recommended)
/agent-enhance react-typescript/testing-specialist --hybrid

# Preview enhancement first
/agent-enhance react-typescript/testing-specialist --dry-run

# Fast static fallback (if AI unavailable)
/agent-enhance react-typescript/testing-specialist --static
```

#### Decision Matrix

| Scenario | Recommended Command | Rationale |
|----------|---------------------|-----------|
| Creating template from codebase | `/agent-format` (automatic in `/template-create`) | Ensures structural consistency |
| Enhancing with code examples | `/agent-enhance --hybrid` | AI analyzes templates for relevant content |
| Quick structure fix | `/agent-format` | Fast, no AI needed |
| Adding boundary sections | `/agent-enhance --hybrid` | AI-powered with validation |
| Template-specific guidance | `/agent-enhance --hybrid` | Context-aware content generation |
| Batch structural updates | `/agent-format` (via tasks) | Fast for multiple agents |
| Batch content enhancement | `/agent-enhance --hybrid` (parallel) | Reliable with fallback |

### Decision 2: Hybrid vs Task-Work

Both approaches use the same AI enhancement logic and produce the same quality results. The difference is in workflow depth and time investment.

#### Option A: Hybrid Enhancement (Recommended)

**Command**:
```bash
/agent-enhance my-template/api-specialist --hybrid
```

**What it does**:
1. Tries AI enhancement (2-5 minutes)
2. Falls back to static if AI fails/times out
3. Validates boundary sections
4. Shows quality report

**Characteristics**:
- **Duration**: 2-5 minutes per agent
- **Quality**: 9/10 (AI-powered with fallback)
- **Reliability**: 100% (falls back to static on AI failure)
- **Phases**: Enhancement only (no quality gates)
- **Traceability**: Command output only

**Use when**:
- Need fast, reliable enhancement
- Working interactively
- Experimenting with templates
- Using Conductor for parallel enhancement

**Exit strategy**: Falls back to static (creates "Related Templates" section only)

#### Option B: Full Workflow with /task-work

**Command**:
```bash
# Tasks automatically created during /template-create
/task-work TASK-AGENT-XXX
```

**What it does**:
1. Phase 2: Planning (minimal for documentation)
2. Phase 2.5: Architecture review (documentation quality)
3. Phase 3: AI enhancement (same logic as hybrid)
4. Phase 4: Validation (boundary sections, format)
5. Phase 5: Code review (completeness check)
6. Phase 5.5: Plan audit (scope verification)

**Characteristics**:
- **Duration**: 30-60 minutes per agent (includes all phases)
- **Quality**: 9/10 (same AI logic as hybrid)
- **Reliability**: 100% (comprehensive testing)
- **Phases**: Full workflow (2-5.5)
- **Traceability**: Complete task tracking

**Use when**:
- Need full quality gates
- Production-critical templates
- Team distribution (audit trail required)
- Learning agent enhancement workflow

**Exit strategy**: None - runs full workflow or blocks on failure

#### Comparison Table

| Feature | Option A (Hybrid) | Option B (Task-Work) |
|---------|-------------------|----------------------|
| **Duration** | 2-5 min | 30-60 min |
| **Quality** | 9/10 | 9/10 |
| **AI Logic** | Same | Same |
| **Phases** | Enhancement only | Full workflow (2-5.5) |
| **Testing** | Validation only | Full test suite |
| **Review** | None | Architectural + Code |
| **Traceability** | Command output | Full task tracking |
| **Fallback** | Static on failure | Blocks on failure |
| **Best for** | Fast iteration, experimentation | Production templates, team distribution |
| **Parallel** | Yes (Conductor) | Yes (Conductor) |

---

## Complete Reference (30 minutes)

### Use Case Examples

#### 1. Creating Template from Codebase

**Scenario**: Running `/template-create` for the first time

**Automatic behavior**:
- Phase 5: `/agent-format` runs automatically on all agents
- Phase 8: Enhancement tasks created in `tasks/backlog/`

**Your choice** (Phase 8):
```bash
# Option A: Enhance interactively (recommended for first-time)
/agent-enhance my-template/api-specialist --hybrid      # 2-5 min
/agent-enhance my-template/testing-specialist --hybrid  # 2-5 min
/agent-enhance my-template/domain-specialist --hybrid   # 2-5 min

# Option B: Use task workflow (recommended for production)
/task-work TASK-AGENT-001  # 30-60 min
/task-work TASK-AGENT-002  # 30-60 min
/task-work TASK-AGENT-003  # 30-60 min

# Parallel enhancement (Conductor)
# Launch 3 workspaces, run /task-work in each
```

**Recommendation**: Use Option A (hybrid) for speed unless you need full audit trail.

#### 2. Quick Structure Fix

**Scenario**: Agent missing standard sections after manual edit

**Solution**:
```bash
# Fix structure instantly
/agent-format my-template/broken-agent

# Preview first
/agent-format my-template/broken-agent --dry-run
```

**Why not /agent-enhance?**: No need for AI - just structural fix (instant vs 2-5 min)

#### 3. Adding Code Examples

**Scenario**: Agent has structure but needs template-specific examples

**Solution**:
```bash
# AI analyzes templates and generates relevant examples
/agent-enhance my-template/api-specialist --hybrid
```

**Output**:
```markdown
## Related Templates

- templates/api/endpoints/UserController.cs.template
- templates/api/endpoints/OrderController.cs.template
- templates/api/models/ApiResponse.cs.template

## Code Examples

### Example 1: Creating REST Endpoint

```csharp
[ApiController]
[Route("api/[controller]")]
public class {{EntityName}}Controller : ControllerBase
{
    private readonly I{{EntityName}}Repository _repository;

    [HttpGet]
    public async Task<ActionResult<IEnumerable<{{EntityName}}>>> GetAll()
    {
        var items = await _repository.GetAllAsync();
        return Ok(items);
    }
}
```

### Example 2: Error Handling Pattern

[AI-generated example using template patterns]
```

**Why hybrid?**: Falls back to static if AI unavailable (reliability)

#### 4. Batch Enhancement (5+ agents)

**Scenario**: Enhancing multiple agents simultaneously

**Solution (Conductor parallel)**:
```bash
# Workspace 1
/agent-enhance my-template/api-specialist --hybrid

# Workspace 2
/agent-enhance my-template/testing-specialist --hybrid

# Workspace 3
/agent-enhance my-template/domain-specialist --hybrid

# Workspace 4
/agent-enhance my-template/integration-specialist --hybrid

# Workspace 5
/agent-enhance my-template/security-specialist --hybrid

# Total time: 2-5 minutes (parallel) vs 10-25 minutes (sequential)
```

**Alternative (sequential)**:
```bash
# One at a time
for agent in api-specialist testing-specialist domain-specialist; do
  /agent-enhance my-template/$agent --hybrid
done
```

**Recommendation**: Use Conductor for parallel enhancement (5x faster)

#### 5. Production Template with Audit Trail

**Scenario**: Creating template for team distribution

**Solution**:
```bash
# Use task workflow for traceability
/template-create --path ~/company-api --output-location repo

# Enhancement tasks auto-created
/task-work TASK-AGENT-001  # Full workflow with audit trail
/task-work TASK-AGENT-002
/task-work TASK-AGENT-003

# Complete tasks (tracked in git)
/task-complete TASK-AGENT-001
/task-complete TASK-AGENT-002
/task-complete TASK-AGENT-003
```

**Why /task-work?**: Complete audit trail for team review and compliance

#### 6. Experimenting with Template

**Scenario**: Testing template creation, may discard

**Solution**:
```bash
# Skip task creation
/template-create --no-create-agent-tasks

# Enhance directly (fast iteration)
/agent-enhance my-template/api-specialist --hybrid --dry-run  # Preview
/agent-enhance my-template/api-specialist --hybrid            # Apply
```

**Why --no-create-agent-tasks?**: Avoids cluttering task backlog during experiments

#### 7. AI Enhancement Unavailable

**Scenario**: Working offline or AI timeout

**Solution**:
```bash
# Use static strategy (instant, basic quality)
/agent-enhance my-template/api-specialist --static

# Or use hybrid (tries AI, falls back to static)
/agent-enhance my-template/api-specialist --hybrid
```

**Output (static)**:
```markdown
## Related Templates

- templates/api/UserController.cs.template
- templates/api/OrderController.cs.template

(No code examples, no best practices - just template list)
```

**Quality**: 6/10 (basic) vs 9/10 (AI)

### Batch Enhancement Strategies

#### Parallel Enhancement (Recommended for 3+ agents)

**Using Conductor.build**:

1. **Launch workspaces** (one per agent)
2. **Run enhancement in parallel**:
   ```bash
   # Each workspace
   /agent-enhance my-template/AGENT-NAME --hybrid
   ```
3. **Commit when done**

**Benefits**:
- 5x faster than sequential (5 agents: 2-5 min vs 10-25 min)
- Independent failures (one fails, others succeed)
- Natural concurrency (no coordination needed)

**When to use**:
- Enhancing 3+ agents
- Time-sensitive delivery
- Experimenting with multiple agents

#### Sequential Enhancement

**Single workspace**:
```bash
/agent-enhance my-template/api-specialist --hybrid
# Wait 2-5 minutes
/agent-enhance my-template/testing-specialist --hybrid
# Wait 2-5 minutes
/agent-enhance my-template/domain-specialist --hybrid
```

**Benefits**:
- Simpler (no Conductor setup)
- Resource-friendly (one AI request at a time)
- Easier to troubleshoot (focus on one agent)

**When to use**:
- Enhancing 1-2 agents
- Limited system resources
- Learning enhancement process

### Quality vs Speed Trade-offs

#### Quality Spectrum

| Strategy | Quality | Duration | Use Case |
|----------|---------|----------|----------|
| `/agent-format` | 6/10 | Instant | Structure only |
| `/agent-enhance --static` | 6/10 | <5 sec | AI unavailable |
| `/agent-enhance --hybrid` | 9/10 | 2-5 min | Fast + reliable |
| `/agent-enhance` (AI only) | 9/10 | 2-5 min | AI available |
| `/task-work TASK-AGENT-XXX` | 9/10 | 30-60 min | Full audit trail |

**Key insight**: Hybrid and Task-Work produce same quality (9/10), differ in workflow depth.

#### Speed Optimization

**Fastest approach** (3 agents):
```bash
# Conductor: 3 parallel workspaces
# Total time: 2-5 minutes
/agent-enhance my-template/agent-1 --hybrid  # Workspace 1
/agent-enhance my-template/agent-2 --hybrid  # Workspace 2
/agent-enhance my-template/agent-3 --hybrid  # Workspace 3
```

**Slowest approach** (3 agents):
```bash
# Single workspace, sequential, full workflow
# Total time: 90-180 minutes
/task-work TASK-AGENT-001  # 30-60 min
/task-work TASK-AGENT-002  # 30-60 min
/task-work TASK-AGENT-003  # 30-60 min
```

**Recommendation**: Use parallel hybrid unless you need audit trail.

#### Reliability Considerations

| Strategy | Reliability | Failure Mode |
|----------|-------------|--------------|
| `--static` | 100% | Never fails (basic output) |
| `--hybrid` | 100% | Falls back to static |
| AI only | 95% | Fails on timeout/API error |
| `/task-work` | 100% | Blocks on failure |

**Key insight**: Hybrid is most reliable for production (never fails, best quality when AI succeeds).

### Understanding Boundary Sections

Enhanced agents automatically include boundary sections that define agent behavior:

**ALWAYS (5-7 rules)**: Non-negotiable actions the agent MUST perform
**NEVER (5-7 rules)**: Prohibited actions the agent MUST avoid
**ASK (3-5 scenarios)**: Situations requiring human escalation

**Example (Testing Agent)**:
```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

**Validation**: Both `/agent-enhance --hybrid` and `/task-work` validate boundary sections:
- Section presence (all three required)
- Rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- Emoji format (✅/❌/⚠️ prefixes)
- Placement (after "Quick Start", before "Capabilities")

### Troubleshooting

#### Issue: AI Enhancement Times Out

**Symptoms**: Enhancement hangs for >5 minutes

**Solutions**:
1. Use `--hybrid` (falls back to static automatically)
   ```bash
   /agent-enhance my-template/agent --hybrid
   ```

2. Use `--static` directly (instant, basic quality)
   ```bash
   /agent-enhance my-template/agent --static
   ```

3. Check MCP connection (if using Context7):
   ```bash
   # Test MCP
   /debug
   ```

#### Issue: Enhancement Tasks Not Created

**Symptoms**: `/template-create` completes but no tasks in backlog

**Cause**: Used `--no-create-agent-tasks` flag

**Solutions**:
1. Re-run without flag (creates tasks):
   ```bash
   /template-create --path ~/my-project
   ```

2. Enhance directly (skip task workflow):
   ```bash
   /agent-enhance my-template/agent-1 --hybrid
   /agent-enhance my-template/agent-2 --hybrid
   ```

#### Issue: Enhancement Quality Low

**Symptoms**: Agent has structure but missing code examples, boundary sections

**Cause**: Used `--static` strategy or `/agent-format`

**Solutions**:
1. Re-enhance with AI:
   ```bash
   /agent-enhance my-template/agent --hybrid
   ```

2. Use full workflow:
   ```bash
   /task-work TASK-AGENT-XXX
   ```

#### Issue: Boundary Sections Missing

**Symptoms**: Agent enhanced but no ALWAYS/NEVER/ASK sections

**Cause**: Enhancement used older version or static strategy

**Solutions**:
1. Re-enhance with hybrid (includes validation):
   ```bash
   /agent-enhance my-template/agent --hybrid
   ```

2. Validate agent:
   ```bash
   /agent-validate my-template/agents/agent.md
   ```

---

## See Also

- [Incremental Enhancement Workflow](../workflows/incremental-enhancement-workflow.md) - Phase 8 workflow details
- [Agent Enhance Command](../../installer/global/commands/agent-enhance.md) - Complete command reference
- [Template Create Command](../../installer/global/commands/template-create.md) - Template creation workflow
- [Agent Discovery Guide](agent-discovery-guide.md) - How agents are matched to tasks
- [Template Validation Guide](template-validation-guide.md) - Quality assurance workflows

---

**Last Updated**: 2025-11-27
**Document Version**: 1.0
**Related Tasks**: TASK-DOC-83F0, TASK-DOC-F3BA
