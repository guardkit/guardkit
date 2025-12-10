# TASK-DOC-F3A3: Documentation Suite for Agent Enhancement Workflow

**Task ID**: TASK-DOC-F3A3
**Priority**: MEDIUM
**Complexity**: 3/10 (Simple)
**Estimated Duration**: 1 day
**Status**: BACKLOG
**Created**: 2025-11-20
**Dependencies**: TASK-AI-2B37 (must be complete to document accurately)

---

## Overview

Create comprehensive documentation for the incremental agent enhancement workflow, including updates to main CLAUDE.md, workflow guides, comparison tables, and command documentation.

**Scope**:
- Update main CLAUDE.md with incremental workflow section
- Create detailed workflow guide with examples
- Add comparison table (automated Phase 7.5 vs incremental Phase 8)
- Update command documentation for `/template-create` and `/agent-enhance`
- Add troubleshooting guide

**Out of Scope**:
- API documentation (code docstrings already complete)
- Testing documentation (covered in TASK-TEST-87F4)
- E2E testing documentation (TASK-E2E-XXX)

---

## Acceptance Criteria

### AC1: Update Main CLAUDE.md

- [ ] **AC1.1**: Add "Incremental Agent Enhancement" section after template creation
- [ ] **AC1.2**: Document `--create-agent-tasks` flag for `/template-create`
- [ ] **AC1.3**: Document `/agent-enhance` command usage
- [ ] **AC1.4**: Add workflow diagram showing decision points
- [ ] **AC1.5**: Include quick reference table

**Location**: `CLAUDE.md` (lines ~180-220, after Template Creation section)

**Content Structure**:

```markdown
## Incremental Agent Enhancement

After creating a template with `/template-create`, you can optionally enhance agents incrementally using the `--create-agent-tasks` flag or `/agent-enhance` command.

### Two Workflows

#### Option 1: Create Agent Tasks During Template Creation

```bash
/template-create --name my-template --create-agent-tasks
```

This creates individual tasks for each agent, allowing you to:
- Enhance agents at your own pace
- Prioritize important agents first
- Track progress per agent

#### Option 2: Manual Enhancement Later

```bash
# Create template (agents are basic)
/template-create --name my-template

# Later, enhance specific agents
/agent-enhance my-template/mvvm-specialist
/agent-enhance my-template/repository-specialist --strategy=ai
```

### Strategy Options

| Strategy | Speed | Quality | AI Required |
|----------|-------|---------|-------------|
| `ai` | Slow (~30s) | High | Yes |
| `static` | Fast (<1s) | Medium | No |
| `hybrid` | Medium | High | Optional |

### When to Use Incremental Enhancement

**Use incremental enhancement when**:
- You want control over which agents to enhance
- You're learning a new stack (enhance agents as you go)
- Template has many agents (>10)
- You want to iterate on specific agents

**Skip incremental enhancement when**:
- Template has few agents (<5)
- You need quick setup
- All agents equally important

See: [Incremental Agent Enhancement Workflow](docs/workflows/incremental-agent-enhancement.md)
```

### AC2: Create Workflow Guide

- [ ] **AC2.1**: Create `docs/workflows/incremental-agent-enhancement.md`
- [ ] **AC2.2**: Include step-by-step examples
- [ ] **AC2.3**: Add decision tree for choosing strategy
- [ ] **AC2.4**: Include troubleshooting section
- [ ] **AC2.5**: Add real-world use cases

**File**: `docs/workflows/incremental-agent-enhancement.md` (~500 lines)

**Structure**:

```markdown
# Incremental Agent Enhancement Workflow

## Overview

## Quick Start

## Workflow Options

### Option 1: Task-Based Enhancement

### Option 2: Manual Enhancement

## Strategy Selection Guide

## Examples

### Example 1: React Template (10 agents)

### Example 2: FastAPI Template (8 agents)

## Comparison with Phase 7.5

## Troubleshooting

## Best Practices

## FAQ
```

### AC3: Create Comparison Table

- [ ] **AC3.1**: Compare Phase 7.5 (automated) vs Phase 8 (incremental)
- [ ] **AC3.2**: Show pros/cons of each approach
- [ ] **AC3.3**: Include migration guide from Phase 7.5 to Phase 8
- [ ] **AC3.4**: Add performance comparison

**Location**: `docs/workflows/incremental-agent-enhancement.md` (section ~line 100)

**Content**:

```markdown
## Comparison: Automated vs Incremental

| Aspect | Phase 7.5 (Removed) | Phase 8 (Incremental) |
|--------|---------------------|----------------------|
| **Execution** | Automatic during /template-create | Manual or task-based |
| **Control** | None (all-or-nothing) | Full (per-agent) |
| **Speed** | Fast (parallel) | Flexible (on-demand) |
| **Success Rate** | 0% (removed due to failures) | High (tested workflow) |
| **Complexity** | High (checkpoint-resume, exit code 42) | Low (simple commands) |
| **User Experience** | Confusing (silent failures) | Clear (explicit actions) |
| **Quality** | Inconsistent | Consistent (validated) |

### When to Use Each

**Phase 7.5** (REMOVED):
- ❌ Not available (removed in TASK-SIMP-9ABE)
- Previously attempted automatic enhancement
- Failed due to over-engineering

**Phase 8** (Incremental):
- ✅ All new templates
- ✅ Templates with >5 agents
- ✅ Learning new stacks
- ✅ Need control over enhancement

### Migration from Phase 7.5

If you have templates created with old Phase 7.5:
1. Agents may have partial or no enhancements
2. Re-run `/agent-enhance` on specific agents
3. Or use `--create-agent-tasks` to systematically enhance
```

### AC4: Update Command Documentation

- [ ] **AC4.1**: Update `/template-create` command spec with `--create-agent-tasks` flag
- [ ] **AC4.2**: Create `/agent-enhance` command spec
- [ ] **AC4.3**: Include all flags (--dry-run, --strategy, --verbose)
- [ ] **AC4.4**: Add examples and error scenarios

**File 1**: `installer/core/commands/template-create.md` (add ~30 lines)

```markdown
## Incremental Agent Enhancement

### --create-agent-tasks Flag

Create individual tasks for each agent to enhance incrementally.

```bash
/template-create --name my-template --create-agent-tasks
```

**Behavior**:
- Creates template with basic agents (Phase 6)
- Creates TASK-XXX for each agent
- Each task calls `/agent-enhance` for one agent
- Use `/task-work TASK-XXX` to enhance agents individually

**Example Output**:
```
✅ Template created: my-template
✅ 8 agent tasks created:
   - TASK-001: Enhance mvvm-specialist
   - TASK-002: Enhance repository-specialist
   ...

Next steps:
  /task-work TASK-001   # Enhance first agent
  /task-status --all    # See all agent tasks
```
```

**File 2**: `installer/core/commands/agent-enhance.md` (new file, ~200 lines)

```markdown
# /agent-enhance - Enhance Single Agent with Template Context

## Usage

```bash
/agent-enhance <template>/<agent> [--strategy=ai|static|hybrid] [--dry-run] [--verbose]
```

## Examples

```bash
# Enhance with AI strategy
/agent-enhance react-typescript/mvvm-specialist

# Preview changes without applying (dry-run)
/agent-enhance react-typescript/repository-specialist --dry-run

# Use static strategy (fast, no AI)
/agent-enhance fastapi-python/api-specialist --strategy=static

# Verbose output for debugging
/agent-enhance nextjs-fullstack/auth-specialist --verbose

# Hybrid strategy (AI with fallback)
/agent-enhance my-template/custom-agent --strategy=hybrid
```

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--strategy` | Enhancement strategy (ai/static/hybrid) | `ai` |
| `--dry-run` | Preview changes without applying | `false` |
| `--verbose` | Show detailed progress | `false` |

## Strategies

### AI Strategy (Recommended)

... [detailed explanation]

### Static Strategy (Fast)

... [detailed explanation]

### Hybrid Strategy (Balanced)

... [detailed explanation]

## Output

... [example outputs]

## Error Handling

... [common errors and solutions]
```

### AC5: Add Troubleshooting Guide

- [ ] **AC5.1**: Common issues and solutions
- [ ] **AC5.2**: Debugging tips
- [ ] **AC5.3**: FAQ section
- [ ] **AC5.4**: Links to related documentation

**Location**: `docs/workflows/incremental-agent-enhancement.md` (section ~line 400)

**Content**:

```markdown
## Troubleshooting

### Agent Enhancement Fails

**Symptom**: `/agent-enhance` exits with error code 3

**Possible Causes**:
1. AI timeout (>300s)
2. Invalid enhancement response
3. Permission error (read-only file)

**Solution**:
```bash
# Try hybrid strategy (falls back to static)
/agent-enhance template/agent --strategy=hybrid

# Check file permissions
ls -la ~/.agentecflow/templates/template/agents/

# Use verbose mode for debugging
/agent-enhance template/agent --verbose
```

### Dry-Run Shows No Changes

**Symptom**: `--dry-run` shows empty diff

**Possible Causes**:
1. Agent already enhanced
2. No relevant templates found
3. Static strategy found no matches

**Solution**:
```bash
# Check if agent already has content
cat ~/.agentecflow/templates/template/agents/agent.md

# Try AI strategy for better matching
/agent-enhance template/agent --strategy=ai --dry-run
```

### Task Creation Fails

**Symptom**: `--create-agent-tasks` doesn't create tasks

**Possible Causes**:
1. Tasks directory doesn't exist
2. Permission error
3. Invalid task format

**Solution**:
```bash
# Verify tasks directory exists
ls -la tasks/

# Check taskwright installation
taskwright doctor

# Try without --create-agent-tasks flag
/template-create --name template
```

## FAQ

### Q: Should I use automated or incremental enhancement?

A: Phase 7.5 (automated) has been removed. Use Phase 8 (incremental) for all new templates.

### Q: Can I enhance agents after template creation?

A: Yes! Use `/agent-enhance template/agent` anytime after template creation.

### Q: Which strategy is best?

A: Start with `hybrid` (AI with fallback to static). Use `static` for speed, `ai` for quality.

### Q: How long does AI enhancement take?

A: ~10-30 seconds per agent (with 300s timeout). Use `--verbose` to monitor progress.

### Q: Can I re-enhance an agent?

A: Yes, `/agent-enhance` can be run multiple times. Use `--dry-run` to preview changes first.
```

---

## Implementation Plan

### Step 1: Update Main CLAUDE.md (2 hours)

- Add incremental enhancement section
- Update table of contents
- Add cross-references

### Step 2: Create Workflow Guide (3 hours)

- Write comprehensive guide
- Add real-world examples
- Include decision trees
- Add troubleshooting

### Step 3: Create Comparison Table (1 hour)

- Document Phase 7.5 vs Phase 8 differences
- Add migration guide
- Include performance metrics

### Step 4: Update Command Documentation (2 hours)

- Update `/template-create` spec
- Create `/agent-enhance` spec
- Add examples and error scenarios

### Step 5: Review and Polish (1 hour)

- Verify all cross-references
- Check markdown formatting
- Test all command examples
- Spell check and grammar

---

## Documentation Structure

```
CLAUDE.md (updated)
└── Incremental Agent Enhancement section

docs/workflows/
└── incremental-agent-enhancement.md (new)
    ├── Overview
    ├── Quick Start
    ├── Workflow Options
    ├── Strategy Selection
    ├── Examples
    ├── Comparison Table
    ├── Troubleshooting
    └── FAQ

installer/core/commands/
├── template-create.md (updated)
│   └── --create-agent-tasks flag
└── agent-enhance.md (new)
    ├── Usage
    ├── Flags
    ├── Strategies
    ├── Examples
    └── Error Handling
```

---

## Success Metrics

### Quantitative

- ✅ All 5 acceptance criteria met
- ✅ CLAUDE.md updated (~50 new lines)
- ✅ Workflow guide created (~500 lines)
- ✅ Command docs updated/created (~250 lines)
- ✅ 0 broken links or cross-references

### Qualitative

- ✅ Clear and concise writing
- ✅ Comprehensive examples
- ✅ Helpful troubleshooting guides
- ✅ Easy to navigate
- ✅ Consistent formatting

---

## Dependencies

**Blocks**:
- TASK-E2E-XXX (E2E documentation references this)

**Depends On**:
- TASK-PHASE-8-INCREMENTAL (✅ completed)
- TASK-AI-2B37 (⏳ must be complete to document AI integration accurately)

**Related**:
- TASK-TEST-87F4 (tests reference documentation)

---

## Deliverables

1. ✅ Updated `CLAUDE.md` with incremental enhancement section
2. ✅ New `docs/workflows/incremental-agent-enhancement.md` guide
3. ✅ Updated `installer/core/commands/template-create.md`
4. ✅ New `installer/core/commands/agent-enhance.md`
5. ✅ Comparison table (Phase 7.5 vs Phase 8)
6. ✅ Troubleshooting guide and FAQ

---

## Next Steps

After task creation:

```bash
# Review task details
cat tasks/backlog/TASK-DOC-F3A3-documentation-suite-agent-enhancement.md

# When ready to implement (after TASK-AI-2B37 complete)
/task-work TASK-DOC-F3A3

# Track progress
/task-status TASK-DOC-F3A3

# Complete after review
/task-complete TASK-DOC-F3A3
```

---

**Created**: 2025-11-20
**Status**: BACKLOG
**Ready for Implementation**: After TASK-AI-2B37 complete
