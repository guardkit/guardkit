# Agent Enhance - Single Agent Enhancement Command

Enhance a single agent with template-specific content.

**Status**: IMPLEMENTED (TASK-PHASE-8-INCREMENTAL)

## Purpose

Enhance individual agent files with template-specific content including:
1. Related template references
2. Code examples from templates
3. Best practices documentation
4. Anti-patterns to avoid

This command provides granular control over agent enhancement as an alternative to fully automated workflows.

## Usage

```bash
# Enhance agent using template/agent format
/agent-enhance react-typescript/testing-specialist

# Enhance agent using absolute path
/agent-enhance /path/to/template/agents/testing-specialist.md

# Preview enhancement without applying (dry-run)
/agent-enhance react-typescript/testing-specialist --dry-run

# Use static strategy (keyword matching, no AI)
/agent-enhance react-typescript/testing-specialist --static

# Use hybrid strategy (AI with fallback to static)
/agent-enhance react-typescript/testing-specialist --hybrid

# Show detailed progress
/agent-enhance react-typescript/testing-specialist --verbose
```

## Command Options

### Required Arguments

```bash
agent_path               Agent path in one of two formats:
                         1. "template-dir/agent-name" (relative, slash-separated)
                            Example: react-typescript/testing-specialist
                         2. "/absolute/path/to/agent.md" (absolute path)
                            Example: /Users/me/.agentecflow/templates/my-template/agents/api-specialist.md
```

### Optional Flags

```bash
--dry-run                Show enhancement preview without applying changes
                         Default: false

--strategy STRATEGY      Enhancement strategy to use
                         Choices: ai, static, hybrid
                         Default: ai

                         Strategies:
                         - ai: AI-powered enhancement (best quality, 2-5 min)
                         - static: Keyword matching (fast, <5 sec, lower quality)
                         - hybrid: AI with fallback to static (recommended for production)

--verbose                Show detailed enhancement process
                         Default: false

--resume                 Resume from checkpoint after agent invocation
                         Use this flag on second run after exit code 42
                         The orchestrator automatically handles checkpoint-resume
                         You typically don't need to use this flag manually
                         Default: false
```

## Enhancement Strategies

### AI Strategy (Default)
- **Method**: Uses `agent-content-enhancer` agent via Task tool
- **Quality**: High - Understands context and generates relevant content
- **Speed**: 2-5 minutes per agent
- **Use when**: Quality is priority, time is available
- **Timeout**: 300 seconds (5 minutes)

### Static Strategy
- **Method**: Simple keyword matching between agent name and template files
- **Quality**: Basic - Only creates related templates list
- **Speed**: <5 seconds per agent
- **Use when**: Need quick results, AI unavailable
- **Limitations**: No code examples, no best practices

### Hybrid Strategy (Recommended)
- **Method**: Tries AI first, falls back to static on failure
- **Quality**: High when AI succeeds, basic when falls back
- **Speed**: 2-5 minutes (AI) or <5 seconds (fallback)
- **Use when**: Production environments, need reliability
- **Fallback triggers**: Timeout, AI error, API unavailable

## Relationship with /agent-format

GuardKit uses a **two-tier enhancement system** to balance speed, quality, and flexibility.

### Two-Tier Enhancement System

**Tier 1: Template-Level Formatting** (`/agent-format`):
- **Quality**: 6/10 (structural consistency)
- **Method**: Pattern-based transformations (no AI)
- **Duration**: <1 second per agent
- **Purpose**: Ensure all agents meet GitHub structural best practices
- **When**: Automatically during `/template-create` Phase 5.5
- **Output**: Consistent structure, boundary section templates, `[NEEDS_CONTENT]` markers

**Tier 2: Project-Level Enhancement** (`/agent-enhance`):
- **Quality**: 9/10 (AI-powered, template-specific)
- **Method**: AI-generated content with context from templates
- **Duration**: 2-5 minutes per agent
- **Purpose**: Add template-specific examples, best practices, and domain guidance
- **When**: After `/template-create` via enhancement tasks or manual invocation
- **Output**: Code examples from templates, related templates list, boundary rules

### When to Use Each Command

| Scenario | Command | Rationale |
|----------|---------|-----------|
| Creating template from codebase | `/agent-format` | Automatic in `/template-create` Phase 5.5, ensures consistent structure |
| Enhancing template agents with examples | `/agent-enhance` | Adds code examples, best practices extracted from your templates |
| Quick agent structure fixes | `/agent-format` | Fast structural corrections without AI dependency |
| Adding template-specific guidance | `/agent-enhance` | AI analyzes templates for relevant, contextual content |
| Formatting any agent file | `/agent-format` | Works on global, template, or user agents without template context |
| CI/CD quality checks | `/agent-format` | Deterministic validation, batch processing support |

### Workflow Integration

```bash
# Step 1: Create template (uses /agent-format automatically in Phase 5.5)
/template-create --path ~/my-project

# Phase 5.5 runs /agent-format on all agents:
# - Adds boundary section templates (ALWAYS/NEVER/ASK)
# - Ensures structural consistency
# - Adds [NEEDS_CONTENT] markers
# - Quality: 6/10 (structure only)

# Step 2: Enhance agents with template-specific content
# Option A: Use enhancement tasks (created with --create-agent-tasks, default)
/task-work TASK-AGENT-XXX  # Works through each agent enhancement

# Option B: Enhance agents manually
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/testing-specialist --hybrid

# Result: Agents now have:
# - Structural consistency (from /agent-format)
# - Template-specific examples (from /agent-enhance)
# - Best practices from your codebase
# - Quality: 9/10
```

### Quality Comparison

| Aspect | `/agent-format` (6/10) | `/agent-enhance` (9/10) |
|--------|------------------------|-------------------------|
| **Structure** | ✅ GitHub best practices | ✅ Preserved from format |
| **Boundaries** | ✅ Template sections added | ✅ Filled with specific rules |
| **Examples** | ❌ `[NEEDS_CONTENT]` markers | ✅ Real code from templates |
| **Best Practices** | ❌ Generic guidance | ✅ Template-specific patterns |
| **Related Templates** | ❌ Not included | ✅ Intelligent matching |
| **Speed** | ⚡ <1 second | 🐢 2-5 minutes |
| **AI Dependency** | ❌ None (pattern-based) | ✅ Required (or static fallback) |
| **Template Context** | ❌ Not required | ✅ Required |

### Why Two Tiers?

**Tier 1 (Format)** provides:
- Fast, deterministic baseline quality
- Structural consistency across all agents
- No AI dependency (works in CI/CD, offline)
- 100% content preservation
- Clear markers for human/AI enhancement

**Tier 2 (Enhance)** provides:
- Template-specific domain knowledge
- Real code examples from your codebase
- Intelligent template matching
- Best practices extraction
- Filled boundary rules

**Both quality levels are intentional**:
- Format ensures every agent meets minimum standards (6/10)
- Enhance adds project-specific depth where needed (9/10)
- Two-tier approach balances speed, cost, and quality

### Cross-References

- [/agent-format Command](agent-format.md) - Pattern-based formatting (Tier 1)
- [/template-create Phase 5.5](template-create.md#phase-55-agent-formatting) - Automatic formatting during template creation
- [/template-create Phase 8](template-create.md#phase-8-agent-enhancement-tasks) - Enhancement task creation (optional)

## Exit Codes

- `0` - Success (agent enhanced)
- `1` - Agent file not found
- `2` - Template directory not found
- `3` - Enhancement failed
- `4` - Validation error (malformed enhancement data)
- `5` - Permission error (cannot write to agent file)
- `42` - Agent invocation needed (checkpoint saved for resume)

## Output Structure

### Default (Progressive Disclosure)

When enhancing an agent, two files are produced:

```
agents/
├── my-agent.md        # Core content (~6KB)
└── my-agent-ext.md    # Extended content (~10KB)
```

**Core file contains:**
- Frontmatter (discovery metadata)
- Quick Start (5-10 examples)
- Boundaries (ALWAYS/NEVER/ASK)
- Capabilities summary
- Loading instructions

**Extended file contains:**
- Detailed code examples (30+)
- Best practices with explanations
- Anti-patterns with code samples
- Technology-specific guidance
- Troubleshooting scenarios

### Single-File Mode (Not Recommended)

```bash
/agent-enhance my-agent.md --no-split
```

Produces single enhanced file without progressive disclosure structure.

### Loading Extended Content

The core file includes loading instructions:

```markdown
## Extended Reference

Before generating code, load the extended reference:

\`\`\`bash
cat agents/my-agent-ext.md
\`\`\`
```

### Size Targets

| Component | Target | Validation |
|-----------|--------|------------|
| Core file | ≤15KB | Warning at 20KB |
| Extended file | No limit | Informational |
| Token Reduction | ≥50% | Validated |

**Benefits:**
- 55-60% token reduction in typical tasks
- Faster AI responses from reduced initial context
- Same comprehensive content available on-demand

## Output Format

### Success Output
```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

### Dry-Run Output
```
✓ Enhanced testing-specialist.md
  Sections added: 4
  Templates referenced: 8
  Code examples: 3

[DRY RUN] Changes not applied

--- Preview ---
## Related Templates
- templates/tests/unit/ComponentTest.tsx.template
- templates/tests/integration/ApiTest.tsx.template
...
```

### Validation Report (Post-GitHub Standards)

When enhancing agents, you'll now receive a validation report showing quality metrics:

```yaml
✅ Enhanced architectural-reviewer.md

Validation Report:
  time_to_first_example: 35 lines ✅
  example_density: 47% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: 28 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.3:1 ✅
  overall_status: PASSED
  iterations_required: 1
  warnings: []
```

**Validation Status**:
- ✅ = Passed quality threshold
- ⚠️ = Warning (below target but acceptable)
- ❌ = Failed (agent quality below minimum)

If validation fails after 3 iterations, you'll receive the best attempt with detailed failure report.

**Reference**: See [GitHub Agent Best Practices Analysis](../../docs/analysis/github-agent-best-practices-analysis.md) for detailed rationale behind these standards.

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
  - Pydantic schema generation
keywords: [fastapi, async, endpoints, router, dependency-injection]
---
```

**See**: [Agent Discovery Guide](../../docs/guides/agent-discovery-guide.md) for comprehensive documentation.

### Metadata Validation Output (TASK-ENF-P0-4)

After enhancement, the command validates discovery metadata:

```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
✓ Discovery metadata validated successfully
```

If metadata is incomplete:

```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5

⚠️  Agent metadata incomplete:
    - Missing required field: stack
    - Missing required field: capabilities
    - Missing required field: keywords

💡 Tip: Re-run enhancement with AI strategy for metadata generation
```

**Note**: Missing metadata is a warning only (graceful degradation). The agent is still enhanced and usable.

### Error Output
```
✗ Enhancement failed: Agent file not found
Path: ~/.agentecflow/templates/react-typescript/agents/testing-specialist.md
```

## Path Resolution

The command supports two path formats:

### Format 1: Relative "template-dir/agent-name"
```bash
/agent-enhance react-typescript/testing-specialist
```

**Resolution Logic**:
1. Split by `/` to get template_name and agent_name
2. Look in global templates: `~/.agentecflow/templates/{template_name}/`
3. If not found, look in repo templates: `installer/global/templates/{template_name}/`
4. Agent file: `{template_dir}/agents/{agent_name}.md`

### Format 2: Absolute Path
```bash
/agent-enhance /Users/me/.agentecflow/templates/my-template/agents/api-specialist.md
```

**Resolution Logic**:
1. Use path directly as agent_file
2. Template directory: `{agent_file.parent.parent}` (go up from agents/ to template/)

## Enhancement Process

### Step 1: Load Agent Metadata
- Read agent file frontmatter
- Extract agent name, description, capabilities

### Step 2: Discover Relevant Templates
- Find all `.template` files in template directory
- Filter by relevance to agent capabilities (AI mode)
- Return all templates (static mode)

### Step 3: Generate Enhancement
- **AI Mode**: Invoke agent-content-enhancer with prompt
- **Static Mode**: Match keywords between agent name and template names
- **Hybrid Mode**: Try AI, fallback to static on error

### Step 4: Validate Enhancement
- Check required keys: `sections`
- Verify `sections` is a list
- Ensure content is well-formed

### Step 5: Apply Enhancement
- Parse existing agent file
- Insert new sections (related_templates, examples, best_practices)
- Preserve existing frontmatter and content
- Generate unified diff for preview

### Step 6: Write or Preview
- **Normal Mode**: Write changes to agent file
- **Dry-Run Mode**: Show diff preview only

## Integration with Task System

### Used by `/task-work`
When a task has `type: agent_enhancement`, `/task-work` will call `/agent-enhance` command:

```bash
# Task metadata
{
    "type": "agent_enhancement",
    "agent_file": "~/.agentecflow/templates/my-template/agents/api-specialist.md",
    "template_dir": "~/.agentecflow/templates/my-template",
    "template_name": "my-template",
    "agent_name": "api-specialist"
}

# Task work will execute:
/agent-enhance my-template/api-specialist
```

### Created by Phase 8
When `/template-create --create-agent-tasks` runs:
1. Phase 8 creates one task per agent
2. Each task includes `/agent-enhance` command in description
3. User can work through tasks individually with `/task-work TASK-ID`

## Examples

### Example 1: Basic Enhancement
```bash
$ /agent-enhance react-typescript/testing-specialist

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

### Example 2: Dry-Run Preview
```bash
$ /agent-enhance react-typescript/testing-specialist --dry-run

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md
  Sections added: 4
  Templates referenced: 8
  Code examples: 3

[DRY RUN] Changes not applied

--- Preview ---
## Related Templates
- templates/tests/unit/ComponentTest.tsx.template
- templates/tests/integration/ApiTest.tsx.template
- templates/tests/e2e/E2ETest.tsx.template
- templates/components/Button.tsx.template
- templates/components/Form.tsx.template
- templates/hooks/useForm.ts.template
- templates/hooks/useApi.ts.template
- templates/utils/testHelpers.ts.template

## Code Examples

### Unit Test Example
```typescript
// From templates/tests/unit/ComponentTest.tsx.template
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
});
```

## Best Practices

1. **Use hybrid strategy for production**: Provides AI quality with static fallback
2. **Preview first with --dry-run**: Review changes before applying
3. **Use verbose for debugging**: See detailed process when issues occur
4. **Batch enhance related agents**: Enhance domain, testing, UI agents together
5. **Commit after enhancement**: Track agent changes in version control

## Error Handling

### Common Errors

**Agent File Not Found**:
```
Error: Agent file not found: ~/.agentecflow/templates/my-template/agents/unknown.md
Solution: Verify agent name and template directory exist
```

**Template Directory Not Found**:
```
Error: Template directory not found: ~/.agentecflow/templates/unknown-template
Solution: Verify template was created successfully
```

**Permission Denied**:
```
Error: Cannot write to agent file: Permission denied
Solution: Check file permissions or use sudo
```

**AI Timeout (AI Strategy)**:
```
Warning: AI enhancement failed, falling back to static: TimeoutError
Solution: Use --static for faster (lower quality) results
```

**Validation Failed**:
```
Error: Validation failed: Missing required key: sections
Solution: This is a bug - please report it
```

## Performance Characteristics

| Strategy | Duration | Quality | Reliability |
|----------|----------|---------|-------------|
| **AI** | 2-5 min | High | 70-80% |
| **Static** | <5 sec | Basic | 100% |
| **Hybrid** | 2-5 min (or <5 sec fallback) | High (or Basic) | 100% |

## Related Commands

- `/agent-format` - Pattern-based agent formatting (Tier 1, structural consistency)
- `/template-create --create-agent-tasks` - Creates enhancement tasks for all agents
- `/task-work TASK-ID` - Works through agent enhancement tasks
- `/template-validate` - Validates template quality including agents

## Implementation Details

### Python Modules

**Command Entry Point**:
- `installer/global/commands/agent-enhance.py` - Command implementation

**Core Modules**:
- `installer/global/lib/agent_enhancement/enhancer.py` - SingleAgentEnhancer class
- `installer/global/lib/agent_enhancement/prompt_builder.py` - AI prompt generation
- `installer/global/lib/agent_enhancement/parser.py` - Response parsing
- `installer/global/lib/agent_enhancement/applier.py` - File modification

### Dependencies
- Python 3.8+ (stdlib for file operations)
- `frontmatter` library (agent metadata parsing)
- Claude Code Task tool (AI strategy only)

## See Also

### Command Documentation
- [Template Create Command](template-create.md) - Complete template creation including Phase 8 agent enhancement

### Workflow Guides
- [Agent Enhancement Decision Guide](../../../docs/guides/agent-enhancement-decision-guide.md) - Choose between /agent-format and /agent-enhance
- [Incremental Enhancement Workflow](../../../docs/workflows/incremental-enhancement-workflow.md) - Phase 8 agent enhancement strategies

### Reference Documentation
- [Agent Enhancement Best Practices](../../docs/guides/agent-enhancement-best-practices.md)
- [Agent Response Format Specification](../../docs/reference/agent-response-format.md) - Required format for `.agent-response.json` files (TASK-FIX-267C)

### Implementation Tasks
- [TASK-PHASE-8-INCREMENTAL: Incremental Agent Enhancement Workflow](../../tasks/backlog/TASK-PHASE-8-INCREMENTAL-specification.md)
- [Template Creation Workflow](../../docs/workflows/template-creation-workflow.md)

---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/agent-enhance "$@"
```

**Note**: The command uses an absolute path to a symlinked Python script in `~/.agentecflow/bin/`. This allows the command to work from any directory, including Conductor worktrees. The symlink points to the actual script in the repository, so updates propagate automatically.

---

**Document Status**: READY FOR IMPLEMENTATION
**Last Updated**: 2025-11-25
**Related Tasks**: TASK-PHASE-8-INCREMENTAL, HAI-001
