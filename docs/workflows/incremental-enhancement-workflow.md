# Incremental Enhancement Workflow (Phase 8)

**Purpose**: Complete guide to Phase 8 agent enhancement during template creation, including task-based and direct command approaches.

**Learn incremental enhancement in**:
- **2 minutes**: Quick Start - Default workflow
- **10 minutes**: Core Concepts - Both approaches
- **30 minutes**: Complete Reference - Strategies and best practices

---

## Quick Start (2 minutes)

### Default Workflow (Task-Based)

```bash
# Step 1: Create template (tasks auto-created)
/template-create --path ~/my-project
# Output: Created 5 agent enhancement tasks in tasks/backlog/

# Step 2: Enhance agents (choose one approach)

# Approach A: Fast hybrid enhancement (2-5 min per agent)
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/testing-specialist --hybrid
/task-complete TASK-AGENT-001  # Mark task done
/task-complete TASK-AGENT-002  # Mark task done

# Approach B: Full workflow (30-60 min per agent)
/task-work TASK-AGENT-001  # Includes all quality gates
/task-work TASK-AGENT-002

# Step 3: Template ready
# All agents enhanced, boundary sections validated
```

**Recommended**: Use Approach A (hybrid) for speed unless you need full audit trail.

---

## Core Concepts (10 minutes)

### What is Phase 8?

Phase 8 is the **incremental agent enhancement phase** that runs after `/template-create` generates the basic template structure.

**When it runs**: After Phase 7 (Package Assembly) in `/template-create`

**What it does**:
1. Creates one enhancement task per agent file
2. Displays boundary sections announcement
3. Shows two enhancement options (hybrid vs task-work)
4. Allows you to choose enhancement approach

**Default behavior**: Tasks created automatically (skip with `--no-create-agent-tasks`)

### Two Enhancement Approaches

#### Approach 1: Task-Based (Default)

**When**: `/template-create` with default behavior

**Characteristics**:
- Enhancement tasks auto-created in `tasks/backlog/`
- Each task references specific agent file
- Tasks include metadata: `agent_file`, `template_dir`, `template_name`, `agent_name`
- Choose between hybrid command or task workflow

**Workflow**:
```bash
# Tasks created automatically
/template-create --path ~/my-project
# Output: Created TASK-AGENT-001, TASK-AGENT-002, TASK-AGENT-003

# Option 1: Enhance directly (2-5 min per agent)
/agent-enhance my-template/api-specialist --hybrid
/task-complete TASK-AGENT-001  # Mark task done

# Option 2: Full workflow (30-60 min per agent)
/task-work TASK-AGENT-001  # Runs Phases 2-5.5
```

**Benefits**:
- Task tracking for audit trail
- Status visibility (`/task-status`)
- Completion tracking
- Flexible enhancement approach

#### Approach 2: Direct Commands

**When**: `/template-create --no-create-agent-tasks`

**Characteristics**:
- No tasks created
- Direct enhancement commands
- Faster for experimentation
- No task backlog clutter

**Workflow**:
```bash
# Skip task creation
/template-create --path ~/my-project --no-create-agent-tasks

# Enhance directly
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/testing-specialist --hybrid
/agent-enhance my-template/domain-specialist --hybrid

# Optional: Validate
/template-validate my-template
```

**Benefits**:
- Faster iteration
- No task management overhead
- Clean for experiments
- Direct control

### Workflow Comparison

| Feature | Approach 1 (Task-Based) | Approach 2 (Direct Commands) |
|---------|------------------------|------------------------------|
| **Task creation** | Automatic | None (--no-create-agent-tasks) |
| **Enhancement method** | Hybrid or /task-work | Hybrid only |
| **Task tracking** | Yes (via /task-status) | No |
| **Audit trail** | Yes (task history) | No (command history only) |
| **Completion tracking** | Via /task-complete | Manual tracking |
| **Best for** | Production templates | Experimentation |
| **Overhead** | Task management | None |

---

## Complete Reference (30 minutes)

### Phase 8 Complete Workflow

#### Phase 8 Execution Flow

```
Phase 8: Agent Task Creation (Default)
├─ 1. Scan for agent files
│  ├─ Search: template_dir/agents/*.md
│  └─ Found: 5 agent files
│
├─ 2. Create enhancement tasks
│  ├─ TASK-AGENT-001: Enhance api-specialist.md
│  ├─ TASK-AGENT-002: Enhance testing-specialist.md
│  ├─ TASK-AGENT-003: Enhance domain-specialist.md
│  ├─ TASK-AGENT-004: Enhance integration-specialist.md
│  └─ TASK-AGENT-005: Enhance security-specialist.md
│
├─ 3. Display boundary sections announcement
│  ├─ ALWAYS (5-7): Non-negotiable actions
│  ├─ NEVER (5-7): Prohibited actions
│  └─ ASK (3-5): Escalation situations
│
├─ 4. Display enhancement options
│  ├─ Option A: /agent-enhance --hybrid (2-5 min)
│  └─ Option B: /task-work TASK-XXX (30-60 min)
│
└─ 5. Wait for user action
   ├─ User chooses Option A or B
   └─ User enhances agents incrementally
```

#### Task Metadata Structure

Each enhancement task includes:

```yaml
---
id: TASK-AGENT-001
title: Enhance api-specialist agent
status: backlog
created: 2025-11-27T10:00:00Z
priority: medium
tags: [agent-enhancement, template-creation]

# Phase 8 metadata
agent_file: /path/to/template/agents/api-specialist.md
template_dir: /path/to/template
template_name: my-template
agent_name: api-specialist
---
```

**Metadata usage**:
- `agent_file`: Full path to agent markdown file
- `template_dir`: Template root directory
- `template_name`: Template identifier
- `agent_name`: Agent identifier (without .md extension)

### Approach 1: Task-Based Enhancement (Detailed)

#### Step-by-Step Workflow

**Step 1: Create template with tasks**
```bash
/template-create --path ~/company-api

# Output:
✓ Phase 1-7: Complete (manifest, settings, templates, agents generated)
✓ Phase 8: Created 5 agent enhancement tasks

Created tasks:
- TASK-AGENT-A1B2: Enhance api-specialist agent
- TASK-AGENT-C3D4: Enhance testing-specialist agent
- TASK-AGENT-E5F6: Enhance domain-specialist agent
- TASK-AGENT-G7H8: Enhance integration-specialist agent
- TASK-AGENT-I9J0: Enhance security-specialist agent

Enhancement Options:
  Option A (Recommended): /agent-enhance template-name/agent-name --hybrid (2-5 min)
  Option B (Optional): /task-work TASK-AGENT-XXX (30-60 min)

Both use same AI enhancement logic with boundary validation.
```

**Step 2: Review tasks**
```bash
/task-status

# Output:
BACKLOG (5 tasks):
- TASK-AGENT-A1B2: Enhance api-specialist agent [priority: medium]
- TASK-AGENT-C3D4: Enhance testing-specialist agent [priority: medium]
- TASK-AGENT-E5F6: Enhance domain-specialist agent [priority: medium]
- TASK-AGENT-G7H8: Enhance integration-specialist agent [priority: medium]
- TASK-AGENT-I9J0: Enhance security-specialist agent [priority: medium]
```

**Step 3A: Fast enhancement (hybrid strategy)**
```bash
# Enhance first agent
/agent-enhance company-api/api-specialist --hybrid

# Output (2-5 minutes):
✓ Enhanced api-specialist.md
  Strategy: AI (hybrid with static fallback)
  Sections added: 4
  Templates referenced: 12
  Code examples: 5
  Boundary sections: ✅ Validated (ALWAYS: 6, NEVER: 6, ASK: 4)

# Mark task complete
/task-complete TASK-AGENT-A1B2

# Repeat for other agents
/agent-enhance company-api/testing-specialist --hybrid
/task-complete TASK-AGENT-C3D4

/agent-enhance company-api/domain-specialist --hybrid
/task-complete TASK-AGENT-E5F6
```

**Step 3B: Full workflow (task-work)**
```bash
# Run full workflow for first agent
/task-work TASK-AGENT-A1B2

# Workflow (30-60 minutes):
Phase 2: Planning (minimal - documentation task)
Phase 2.5: Architecture review (documentation quality)
Phase 2.7: Complexity evaluation (usually 2-3/10)
Phase 3: Enhancement (same AI logic as hybrid)
Phase 4: Validation (boundary sections, format)
Phase 5: Code review (completeness)
Phase 5.5: Plan audit (scope verification)

# Output:
✓ Task complete: TASK-AGENT-A1B2
  Status: IN_REVIEW
  Agent enhanced with full quality gates

# Review and complete
/task-complete TASK-AGENT-A1B2
```

**Step 4: Verify completion**
```bash
/task-status

# Output:
COMPLETED (5 tasks):
- TASK-AGENT-A1B2: Enhance api-specialist agent ✓
- TASK-AGENT-C3D4: Enhance testing-specialist agent ✓
- TASK-AGENT-E5F6: Enhance domain-specialist agent ✓
- TASK-AGENT-G7H8: Enhance integration-specialist agent ✓
- TASK-AGENT-I9J0: Enhance security-specialist agent ✓
```

### Approach 2: Direct Commands Enhancement (Detailed)

#### Step-by-Step Workflow

**Step 1: Create template without tasks**
```bash
/template-create --path ~/company-api --no-create-agent-tasks

# Output:
✓ Phase 1-7: Complete (manifest, settings, templates, agents generated)
✓ Phase 8: Skipped (--no-create-agent-tasks)

Template created: company-api
Agents generated: 5
Enhancement tasks: 0 (skipped)

Next steps:
  /agent-enhance company-api/AGENT-NAME --hybrid
```

**Step 2: Enhance agents directly**
```bash
# Enhance each agent (2-5 min each)
/agent-enhance company-api/api-specialist --hybrid
/agent-enhance company-api/testing-specialist --hybrid
/agent-enhance company-api/domain-specialist --hybrid
/agent-enhance company-api/integration-specialist --hybrid
/agent-enhance company-api/security-specialist --hybrid

# Total time: 10-25 minutes (sequential) or 2-5 minutes (parallel with Conductor)
```

**Step 3: Optional validation**
```bash
# Validate entire template
/template-validate company-api

# Output:
✓ Template Validation Report

Overall Score: 8.5/10

Strengths:
- All agents have boundary sections ✅
- Code examples present in all agents ✅
- Consistent structure across agents ✅

Recommendations:
- Add more anti-patterns to testing-specialist
- Expand code examples in domain-specialist
```

### Batch Enhancement Strategies

#### Strategy 1: Parallel Enhancement (Conductor)

**Best for**: 3+ agents, time-sensitive delivery

**Setup**:
1. Create template with tasks (default)
2. Launch Conductor with N workspaces (1 per agent)
3. Run `/agent-enhance --hybrid` in each workspace

**Example (5 agents)**:
```bash
# Workspace 1
/agent-enhance company-api/api-specialist --hybrid
/task-complete TASK-AGENT-A1B2

# Workspace 2
/agent-enhance company-api/testing-specialist --hybrid
/task-complete TASK-AGENT-C3D4

# Workspace 3
/agent-enhance company-api/domain-specialist --hybrid
/task-complete TASK-AGENT-E5F6

# Workspace 4
/agent-enhance company-api/integration-specialist --hybrid
/task-complete TASK-AGENT-G7H8

# Workspace 5
/agent-enhance company-api/security-specialist --hybrid
/task-complete TASK-AGENT-I9J0

# Total time: 2-5 minutes (parallel) vs 10-25 minutes (sequential)
```

**Benefits**:
- 5x faster than sequential
- Independent failures (isolation)
- Natural concurrency
- Full task tracking maintained

**Trade-offs**:
- Requires Conductor setup
- More system resources
- Coordination overhead (minimal)

#### Strategy 2: Sequential Enhancement

**Best for**: 1-2 agents, learning, limited resources

**Workflow**:
```bash
# One agent at a time
/agent-enhance company-api/api-specialist --hybrid
# Wait 2-5 minutes
/task-complete TASK-AGENT-A1B2

/agent-enhance company-api/testing-specialist --hybrid
# Wait 2-5 minutes
/task-complete TASK-AGENT-C3D4

# Continue for remaining agents
```

**Benefits**:
- Simpler setup
- Resource-friendly
- Easier troubleshooting
- Focus on one agent at a time

**Trade-offs**:
- Slower (10-25 min for 5 agents)
- No concurrency

#### Strategy 3: Hybrid Parallel/Sequential

**Best for**: Priority-based enhancement, staged delivery

**Workflow**:
```bash
# Phase 1: High-priority agents (parallel)
# Workspace 1
/agent-enhance company-api/api-specialist --hybrid

# Workspace 2
/agent-enhance company-api/domain-specialist --hybrid

# Phase 2: Lower-priority agents (sequential)
/agent-enhance company-api/testing-specialist --hybrid
/agent-enhance company-api/integration-specialist --hybrid
/agent-enhance company-api/security-specialist --hybrid
```

**Benefits**:
- Optimized resource usage
- Priority-driven
- Flexible approach

### Best Practices

#### 1. Use Hybrid Strategy for Reliability

**Why**: Falls back to static if AI unavailable (100% reliability)

**How**:
```bash
/agent-enhance my-template/agent --hybrid
```

**Alternative** (AI only, 95% reliability):
```bash
/agent-enhance my-template/agent  # No --hybrid flag
```

#### 2. Enhance Related Agents Together

**Why**: Consistent patterns across related agents

**Example**:
```bash
# API layer agents together
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/integration-specialist --hybrid

# Domain layer agents together
/agent-enhance my-template/domain-specialist --hybrid
/agent-enhance my-template/repository-specialist --hybrid
```

#### 3. Preview with --dry-run First

**Why**: See enhancement before applying

**How**:
```bash
# Preview
/agent-enhance my-template/agent --hybrid --dry-run

# Review output, then apply
/agent-enhance my-template/agent --hybrid
```

#### 4. Commit After Each Agent

**Why**: Incremental version control, easy rollback

**How**:
```bash
/agent-enhance my-template/api-specialist --hybrid
git add .
git commit -m "Enhance api-specialist agent"

/agent-enhance my-template/testing-specialist --hybrid
git add .
git commit -m "Enhance testing-specialist agent"
```

#### 5. Validate Before Distribution

**Why**: Ensure quality before sharing with team

**How**:
```bash
# After all enhancements complete
/template-validate my-template

# Fix any issues found
/agent-enhance my-template/AGENT-NAME --hybrid  # Re-enhance if needed
```

#### 6. Use Tasks for Production Templates

**Why**: Full traceability and audit trail

**How**:
```bash
# Production workflow
/template-create --path ~/prod-api --output-location repo

# Use task workflow (not hybrid shortcuts)
/task-work TASK-AGENT-001
/task-work TASK-AGENT-002
/task-complete TASK-AGENT-001
/task-complete TASK-AGENT-002
```

#### 7. Use Direct Commands for Experimentation

**Why**: Fast iteration without task clutter

**How**:
```bash
# Experimental workflow
/template-create --path ~/test-api --no-create-agent-tasks

# Enhance directly
/agent-enhance test-api/api-specialist --hybrid
/agent-enhance test-api/testing-specialist --hybrid

# Discard if not useful (no task cleanup needed)
```

### Troubleshooting

#### Issue: AI Enhancement Times Out

**Symptoms**: Enhancement hangs for >5 minutes

**Diagnosis**:
```bash
# Check if using hybrid (should have fallback)
/agent-enhance my-template/agent --hybrid --verbose

# Output shows:
AI enhancement timeout (300s)
Falling back to static strategy...
✓ Static enhancement complete
```

**Solutions**:

1. **Already using --hybrid**: Enhancement should complete with static fallback
   - If still hangs, interrupt (Ctrl+C) and retry
   - Check system resources (AI may be queued)

2. **Not using --hybrid**: Add flag for automatic fallback
   ```bash
   /agent-enhance my-template/agent --hybrid
   ```

3. **Persistent timeout**: Use static directly
   ```bash
   /agent-enhance my-template/agent --static  # Instant, basic quality
   ```

#### Issue: Enhancement Tasks Not Created

**Symptoms**: `/template-create` completes but no tasks in backlog

**Diagnosis**:
```bash
/task-status

# Output:
BACKLOG (0 tasks)
# No TASK-AGENT-XXX tasks found
```

**Cause**: Used `--no-create-agent-tasks` flag

**Solutions**:

1. **Re-run without flag** (if template not yet distributed):
   ```bash
   # Caution: May overwrite existing template
   /template-create --path ~/my-project
   ```

2. **Enhance directly** (recommended if template already exists):
   ```bash
   /agent-enhance my-template/agent-1 --hybrid
   /agent-enhance my-template/agent-2 --hybrid
   /agent-enhance my-template/agent-3 --hybrid
   ```

3. **Create tasks manually** (if tracking needed):
   ```bash
   # For each agent
   /task-create "Enhance api-specialist agent" \
     priority:medium \
     tags:agent-enhancement,my-template
   ```

#### Issue: Enhancement Quality Low

**Symptoms**: Agent has structure but missing code examples, boundary sections, or template-specific guidance

**Diagnosis**:
```bash
# Check agent file
cat my-template/agents/api-specialist.md

# Look for:
## Related Templates  # Should have template list
## Code Examples       # Should have examples
## Boundaries          # Should have ALWAYS/NEVER/ASK
```

**Cause**: Used `--static` strategy or `/agent-format` (basic quality)

**Solutions**:

1. **Re-enhance with AI**:
   ```bash
   /agent-enhance my-template/api-specialist --hybrid
   ```

2. **Use full workflow** (if audit trail needed):
   ```bash
   /task-work TASK-AGENT-XXX
   ```

3. **Validate quality**:
   ```bash
   /agent-validate my-template/agents/api-specialist.md
   ```

#### Issue: Boundary Sections Missing or Invalid

**Symptoms**: Agent enhanced but boundary sections missing or incorrectly formatted

**Diagnosis**:
```bash
# Validate agent
/agent-validate my-template/agents/api-specialist.md

# Output shows validation errors:
❌ Boundary sections: Missing "NEVER" section
❌ ALWAYS rules: 3 found, expected 5-7
```

**Cause**: Enhancement used older version, static strategy, or manual editing

**Solutions**:

1. **Re-enhance with hybrid** (includes boundary validation):
   ```bash
   /agent-enhance my-template/api-specialist --hybrid
   ```

2. **Manual fix** (if re-enhancement not desired):
   - Add missing sections following format
   - Ensure 5-7 ALWAYS rules (✅ prefix)
   - Ensure 5-7 NEVER rules (❌ prefix)
   - Ensure 3-5 ASK scenarios (⚠️ prefix)

3. **Validate after fix**:
   ```bash
   /agent-validate my-template/agents/api-specialist.md
   ```

### Code Examples

#### Example 1: Fast Template Creation (Experimentation)

```bash
# Create template without tasks (fast iteration)
/template-create --path ~/experimental-api --no-create-agent-tasks

# Enhance key agents only (2-5 min total)
/agent-enhance experimental-api/api-specialist --hybrid
/agent-enhance experimental-api/testing-specialist --hybrid

# Test template
guardkit init experimental-api

# Discard if not useful (no task cleanup needed)
```

**Use case**: Trying out template creation, may not keep

#### Example 2: Production Template (Full Audit Trail)

```bash
# Create template with tasks (default)
/template-create --path ~/production-api --output-location repo

# Use full workflow for each agent (30-60 min each)
/task-work TASK-AGENT-001  # api-specialist
/task-work TASK-AGENT-002  # testing-specialist
/task-work TASK-AGENT-003  # domain-specialist

# Complete tasks
/task-complete TASK-AGENT-001
/task-complete TASK-AGENT-002
/task-complete TASK-AGENT-003

# Validate before distribution
/template-validate production-api

# Commit
git add .
git commit -m "Add production-api template with enhanced agents"
```

**Use case**: Template for team distribution, needs audit trail

#### Example 3: Parallel Enhancement (Conductor)

```bash
# Main workspace: Create template
/template-create --path ~/company-api

# Launch 5 Conductor workspaces (one per agent)

# Workspace 1
/agent-enhance company-api/api-specialist --hybrid
/task-complete TASK-AGENT-001

# Workspace 2
/agent-enhance company-api/testing-specialist --hybrid
/task-complete TASK-AGENT-002

# Workspace 3
/agent-enhance company-api/domain-specialist --hybrid
/task-complete TASK-AGENT-003

# Workspace 4
/agent-enhance company-api/integration-specialist --hybrid
/task-complete TASK-AGENT-004

# Workspace 5
/agent-enhance company-api/security-specialist --hybrid
/task-complete TASK-AGENT-005

# Main workspace: Validate
/template-validate company-api

# Total time: 2-5 minutes (parallel) vs 10-25 minutes (sequential)
```

**Use case**: Time-sensitive delivery, 5+ agents

#### Example 4: Incremental Team Template

```bash
# Create template (default)
/template-create --path ~/team-template

# Enhance high-priority agents first (sequential)
/agent-enhance team-template/api-specialist --hybrid
/task-complete TASK-AGENT-001
git commit -m "Enhance api-specialist"

/agent-enhance team-template/domain-specialist --hybrid
/task-complete TASK-AGENT-002
git commit -m "Enhance domain-specialist"

# Distribute partial template for team feedback
git push

# Enhance remaining agents later based on feedback
/agent-enhance team-template/testing-specialist --hybrid
/task-complete TASK-AGENT-003
git commit -m "Enhance testing-specialist"
```

**Use case**: Iterative team template development with feedback loops

---

## See Also

- [Agent Enhancement Decision Guide](../guides/agent-enhancement-decision-guide.md) - Choose right enhancement strategy
- [Template Create Command](../../installer/global/commands/template-create.md) - Complete template creation workflow
- [Agent Enhance Command](../../installer/global/commands/agent-enhance.md) - Command reference
- [Agent Discovery Guide](../guides/agent-discovery-guide.md) - How agents are matched to tasks
- [Template Validation Guide](../guides/template-validation-guide.md) - Quality assurance workflows

---

**Last Updated**: 2025-11-27
**Document Version**: 1.0
**Related Tasks**: TASK-DOC-83F0, TASK-DOC-F3BA, TASK-PHASE-8-INCREMENTAL, TASK-UX-3A8D
