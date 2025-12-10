# Template Init - Greenfield Template Creation from Q&A Session

Orchestrates greenfield template creation through interactive Q&A session without requiring existing codebase.

**Status**: IMPLEMENTED (TASK-011, TASK-INIT-001 through TASK-INIT-009)

## Purpose

Enable users to create custom templates for new projects based on their preferred technology stack and architecture patterns through:
1. Interactive Q&A session covering technology choices
2. AI-powered agent generation with boundary sections
3. Validation and quality scoring
4. Flexible output locations (personal or repository)
5. CI/CD integration via exit codes

**Key Difference from /template-create**:
- **Brownfield** (`/template-create`): Analyzes existing codebase → extracts patterns → generates template
- **Greenfield** (`/template-init`): Q&A session → AI generates intelligent defaults → creates template

## Synopsis

```bash
/template-init [--validate] [--output-location=global|repo] [--no-create-agent-tasks]
```

Create greenfield template through interactive Q&A session with automatic quality assessment.

## Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--validate` | flag | false | Run extended validation (Level 2) with quality report |
| `--output-location` | global, repo | global | Where to save template |
| `--no-create-agent-tasks` | flag | false | Skip agent enhancement task creation |

### Output Locations

**global** (default): Personal templates (~/.agentecflow/templates/)
- For personal use and experimentation
- Immediate availability with `guardkit init {template_name}`
- Not shared with team
- No install.sh required

**repo**: Repository templates (installer/core/templates/)
- For team distribution
- Requires `./installer/scripts/install.sh` before use
- Shared across projects via version control
- Suitable for organizational standards

## Features

### 1. Boundary Sections (TASK-INIT-001)

All generated agents include ALWAYS/NEVER/ASK boundary sections based on GitHub best practices (2,500+ repo analysis).

**Format:**
- ✅ ALWAYS (5-7 rules): Non-negotiable actions agent MUST perform
- ❌ NEVER (5-7 rules): Prohibited actions agent MUST avoid
- ⚠️ ASK (3-5 scenarios): Situations requiring human escalation

**Example:**
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

**Benefits:**
- Prevents costly mistakes
- Reduces human intervention by 40%
- Improves agent discoverability and reusability
- Sets clear expectations for agent behavior

### 2. Agent Enhancement Tasks (TASK-INIT-002)

Creates enhancement tasks automatically after template generation, providing immediate next steps.

**Created:** One task per generated agent
**Location:** tasks/backlog/
**Task Metadata:**
- agent_file, template_dir, template_name, agent_name
- Priority: medium

**Enhancement Options:**
- **Option A (Recommended)**: `/agent-enhance <template>/<agent> --hybrid` (2-5 min per agent)
- **Option B (Optional)**: `/task-work TASK-AGENT-XXX` (30-60 min per agent - full workflow)

**To skip:** Use `--no-create-agent-tasks` flag (useful for CI/CD automation)

**Both approaches:**
- Use same AI enhancement logic
- Include boundary section validation
- Ensure ALWAYS/NEVER/ASK format compliance

### 3. Validation System (TASK-INIT-003, 004, 005)

Three-level validation for template quality assurance:

**Level 1: Automatic** (Always On - Phase 3.5)
- CRUD completeness validation (60% threshold)
- Layer symmetry checks
- Auto-fix recommendations
- Non-blocking warnings
- Duration: ~30 seconds
- **No user action required**

**Level 2: Extended** (--validate flag - Phase 5.5)
- All Level 1 checks
- Placeholder consistency validation
- Pattern fidelity spot-checks (5 random samples)
- Documentation completeness verification
- Quality report generation (validation-report.md)
- Exit code assignment based on score
- Duration: 2-5 minutes

**Level 3: Comprehensive** (/template-validate command)
- Interactive 16-section audit
- Section selection and session save/resume
- AI-assisted analysis (sections 8, 11, 12, 13)
- Inline issue fixes
- Comprehensive audit report (audit-report.md)
- Duration: 30-60 minutes (with AI)
- Use after basic creation for production-critical templates

**Validation Reports:**
- `validation-report.md` (Level 2) - Quality score, findings, recommendations
- `audit-report.md` (Level 3) - Comprehensive audit results

### 4. Quality Scoring (TASK-INIT-006)

Calculates 0-10 quality score from Q&A answers and template structure.

**Scoring Components:**
- Architecture clarity and pattern consistency
- Testing strategy completeness
- Error handling approach
- Documentation quality
- Agent coverage and specificity
- Technology stack maturity
- Development practices

**Output:**
- quality-report.md in template directory
- Overall score (0-10) and letter grade (A+ to F)
- Production readiness assessment (≥7/10 recommended)
- Component breakdowns with actionable recommendations

**Thresholds:**
- **8-10 (A/A+)**: Production-ready, high quality
- **6-7.9 (B/C)**: Medium quality, improvements recommended
- **<6 (D/F)**: Low quality, significant improvements required

### 5. Two-Location Output (TASK-INIT-007)

Save templates to personal or repository location.

**Global (default):**
```bash
/template-init
# Saves to ~/.agentecflow/templates/
# ✅ Immediate use: guardkit init {template-name}
# ✅ No install.sh required
```

**Repository:**
```bash
/template-init --output-location=repo
# Saves to installer/core/templates/
# ⚠️ Requires: ./installer/scripts/install.sh
# 📦 Suitable for team distribution
```

**Benefits:**
- Personal templates for experimentation
- Repository templates for organizational standards
- Consistent structure across both locations
- Same validation and quality checks

### 6. Discovery Metadata (TASK-INIT-008)

Agents include frontmatter for AI-powered discovery during /task-work execution.

**Metadata Fields:**
```yaml
---
stack: [python, fastapi, async]
phase: implementation
capabilities: [api-endpoints, request-validation, async-patterns, pydantic-models]
keywords: [python, api, fastapi, pydantic, async, endpoints]
---
```

**Discovery Process:**
1. **Phase 3**: System analyzes task context (file extensions, keywords, project structure)
2. **Discovery**: Scans all agents for metadata match (stack + phase + keywords)
3. **Selection**: Uses specialist if found, falls back to task-manager if not
4. **Feedback**: Shows which agent selected and why

**Benefits:**
- Intelligent agent selection during /task-work
- No hardcoded agent mappings required
- Extensible for new technology stacks
- Graceful degradation (agents without metadata skipped)

### 7. Agent Registration Verification (TASK-ENF-P0-3)

When initializing a project with `guardkit init`, the system verifies that template agents are properly registered for discovery. This ensures agents will be available during `/task-work` execution.

**Verification Steps:**
1. **Metadata Verification**: Check each agent's frontmatter for required fields (stack, phase, capabilities, keywords)
2. **Discovery Test**: Run agent discovery to verify agents are findable
3. **Registration Report**: Display registered agents with their stack and phase information

**Expected Output:**
```
============================================================
  Agent Discovery Verification
============================================================

🔍 Verifying agent metadata...
  ✓ react-state-specialist: Valid metadata
  ✓ test-orchestrator: Valid metadata

🧪 Testing agent discovery...
  ✅ Agent discovery successful:
      • react-state-specialist (stack: ['react', 'typescript'])
      • test-orchestrator (stack: ['cross-stack'])

============================================================
  Registered Agents
============================================================

  • react-state-specialist
    Stack: react, typescript, Phase: implementation
  • test-orchestrator
    Stack: cross-stack, Phase: testing
```

**Missing Metadata Handling:**
If agents are missing discovery metadata, you'll see warnings with enhancement suggestions:

```
⚠️  Warning: custom-specialist missing discovery metadata:
    - Missing required field: stack
    - Missing required field: keywords

💡 Tip: Enhance agents with:
   /agent-enhance .claude/agents/custom-specialist.md
```

**Benefits:**
- Early detection of metadata issues
- Confidence that template agents will be discovered
- Clear visibility into registered agents
- Graceful degradation (warnings, not errors)

### 8. Exit Codes (TASK-INIT-009)

Quality-based exit codes for CI/CD integration.

| Exit Code | Quality Score | Meaning | CI/CD Action |
|-----------|--------------|---------|--------------|
| 0 | ≥8/10 | High quality | ✅ Continue pipeline |
| 1 | 6-7.9/10 | Medium quality | ⚠️ Warning, review recommended |
| 2 | <6/10 | Low quality | ❌ Fail pipeline |
| 3 | N/A | Execution error | ❌ Fail pipeline |

**CI/CD Integration:**
```bash
# Quality gate in CI/CD pipeline
/template-init --validate --output-location=repo
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Template meets quality standards (≥8/10)"
    git add installer/core/templates/
    git commit -m "Add high-quality template"
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠️ Template has medium quality (6-7.9/10) - review recommended"
    # Continue but flag for review
else
    echo "❌ Template quality below threshold - improvements required"
    exit 1
fi
```

**Use Cases:**
- Automated template quality gates
- Pre-commit validation hooks
- CI/CD pipeline integration
- Quality threshold enforcement

## Workflow

The command executes these phases automatically:

### Phase 1: Identity (Section 1)
- Template name, purpose, description
- Target use case and project type
- Technology stack overview

### Phase 2: Q&A Session (Sections 2-10)
Interactive questionnaire covering:
- Architecture pattern and layers
- Technology stack (language, framework, version)
- Testing strategy and frameworks
- Error handling approach
- Dependency management
- Development practices
- Testing requirements
- Security considerations
- Deployment strategy
- Documentation requirements

**Duration**: 5-10 minutes
**Features**:
- Resume on interruption (saves progress to `.template-init-session.json`)
- Validation of all inputs
- Context-aware questions (skips irrelevant sections)

### Phase 3: Agent Generation
- Generate technology-specific agents based on Q&A answers
- Add boundary sections (ALWAYS/NEVER/ASK) to each agent
- Include discovery metadata (frontmatter) for intelligent selection
- Create agent recommendations (4-7 agents typical)
- Save agent definitions to template

**Duration**: 5-15 seconds

### Phase 3.5: Level 1 Validation (Automatic)
- CRUD completeness check (60% threshold)
- Layer symmetry validation
- Display warnings (non-blocking)
- Auto-fix recommendations

**Duration**: ~30 seconds

### Phase 4: Save Template
- Save to output location (global or repo)
- Ensure /template-validate compatibility (marker file)
- Create directory structure
- Write manifest, settings, CLAUDE.md, agents

**Template Structure:**
```
{template-name}/
├── template-manifest.json      # Template metadata
├── settings.json               # Default project settings
├── CLAUDE.md                   # Template-specific AI instructions
├── agents/                     # Generated agents with frontmatter
│   ├── testing-agent.md
│   ├── api-agent.md
│   └── repository-agent.md
├── templates/                  # Template files (optional)
└── .validation-compatible      # Marker for /template-validate
```

### Phase 4.5: Quality Scoring
- Calculate 0-10 quality score from Q&A answers
- Generate quality-report.md
- Display score summary with letter grade
- Show production readiness assessment

**Duration**: 10-30 seconds

### Phase 5: Agent Enhancement Tasks (Default - skip with --no-create-agent-tasks)
- Create one task per agent in tasks/backlog/
- Display boundary sections announcement:
  - Explains ALWAYS (5-7), NEVER (5-7), ASK (3-5) format
  - Shows emoji prefixes (✅/❌/⚠️)
  - Expected validation output
- Display two enhancement options:
  - Option A (Recommended): /agent-enhance template-name/agent-name --hybrid (2-5 minutes)
  - Option B (Optional): /task-work TASK-AGENT-XXX (30-60 minutes - full workflow)
- Both approaches use same AI enhancement logic with boundary validation

**Duration**: 5-10 seconds

### Phase 5.5: Extended Validation (--validate flag only)
- Placeholder consistency validation
- Pattern fidelity spot-checks
- Documentation completeness verification
- Generate validation-report.md
- Calculate exit code based on quality score

**Duration**: 2-5 minutes

### Phase 6: Display Guidance
- Location-specific usage instructions
- Validation options (Level 2 and Level 3)
- Next steps (enhancement tasks, validation)
- CI/CD integration examples (if --validate used)

## Examples

### Basic Usage (Personal Template)
```bash
/template-init
# Interactive Q&A → saves to ~/.agentecflow/templates/
# ✅ Immediate use: guardkit init {template-name}
```

### Repository Template with Validation
```bash
/template-init --validate --output-location=repo
# Full quality assessment → saves to installer/core/templates/
# ⚠️ Requires: ./installer/scripts/install.sh before use
# 📊 Generates validation-report.md and quality-report.md
```

### Skip Agent Enhancement Tasks
```bash
/template-init --no-create-agent-tasks
# For CI/CD automation where enhancement tasks not needed
# Still generates agents with boundary sections
```

### Personal Template with Validation
```bash
/template-init --validate
# Quality assessment for personal template
# Saves to ~/.agentecflow/templates/ with validation report
```

### Complete CI/CD Pipeline Integration
```bash
#!/bin/bash
# Quality gate in CI/CD pipeline

echo "Creating template with validation..."
/template-init --validate --output-location=repo --no-create-agent-tasks
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "✅ Template quality: HIGH (≥8/10)"
    echo "✅ Ready for production use"
    git add installer/core/templates/
    git commit -m "Add high-quality template [automated]"
    git push
    ;;
  1)
    echo "⚠️ Template quality: MEDIUM (6-7.9/10)"
    echo "⚠️ Review recommended before production use"
    git add installer/core/templates/
    git commit -m "Add medium-quality template [needs review]"
    # Could optionally create PR instead of direct push
    ;;
  2)
    echo "❌ Template quality: LOW (<6/10)"
    echo "❌ Improvements required before deployment"
    echo "See validation-report.md for specific issues"
    exit 1
    ;;
  3)
    echo "❌ Template creation failed"
    echo "Check logs for error details"
    exit 1
    ;;
esac
```

### Comprehensive Audit Workflow
```bash
# Step 1: Create basic template
/template-init
# Result: Template saved to ~/.agentecflow/templates/my-template

# Step 2: Later, run comprehensive audit
/template-validate ~/.agentecflow/templates/my-template
# Interactive 16-section audit with AI assistance
# Result: audit-report.md generated
```

## Generated Files

### Template Structure
```
my-template/
├── template-manifest.json      # Template metadata
├── settings.json               # Project settings
├── CLAUDE.md                   # AI instructions
├── agents/                     # Generated agents with frontmatter
│   ├── testing-agent.md       # With ALWAYS/NEVER/ASK boundaries
│   ├── api-agent.md
│   └── repository-agent.md
├── templates/                  # Template files (optional)
└── .validation-compatible      # Marker for /template-validate
```

### Reports (with --validate)
```
my-template/
├── quality-report.md          # Quality scoring results (Phase 4.5)
│   ├── Overall score (0-10)
│   ├── Letter grade (A+ to F)
│   ├── Component breakdowns
│   └── Recommendations
└── validation-report.md       # Extended validation findings (Phase 5.5)
    ├── Placeholder consistency
    ├── Pattern fidelity checks
    ├── Documentation completeness
    └── Exit code justification
```

### Tasks (default - skip with --no-create-agent-tasks)
```
tasks/backlog/
├── TASK-AGENT-HHMMSS-1.md    # Enhancement task for agent 1
│   ├── Metadata: agent_file, template_dir, template_name
│   ├── Enhancement options (A: hybrid, B: full workflow)
│   └── Priority: medium
├── TASK-AGENT-HHMMSS-2.md    # Enhancement task for agent 2
└── TASK-AGENT-HHMMSS-3.md    # Enhancement task for agent 3
```

## Comparison: /template-init vs /template-create

| Feature | /template-init | /template-create |
|---------|----------------|------------------|
| **Input** | Q&A session | Existing codebase |
| **Use Case** | Greenfield projects | Brownfield projects |
| **Boundary Sections** | ✅ Yes (TASK-INIT-001) | ✅ Yes |
| **Agent Tasks** | ✅ Yes (TASK-INIT-002) | ✅ Yes |
| **Validation Levels** | ✅ L1/L2/L3 (TASK-INIT-003-005) | ✅ L1/L2/L3 |
| **Quality Scoring** | ✅ Q&A-based (TASK-INIT-006) | ✅ Code analysis-based |
| **Output Locations** | ✅ global/repo (TASK-INIT-007) | ✅ global/repo |
| **Discovery Metadata** | ✅ Yes (TASK-INIT-008) | ✅ Yes |
| **Exit Codes** | ✅ Yes (TASK-INIT-009) | ✅ Yes |
| **AI Analysis** | Generated from Q&A | Inferred from codebase |
| **Template Files** | Optional (starter files) | Extracted from code |
| **Duration** | 5-15 minutes | 2-10 minutes |

**When to use:**
- **template-init**: Starting new project from scratch, no existing codebase
- **template-create**: Extracting template from existing, proven codebase

**Both commands:**
- Generate agents with boundary sections and discovery metadata
- Support three validation levels (L1/L2/L3)
- Create agent enhancement tasks by default
- Provide quality scoring and reports
- Support personal and repository output locations
- Include CI/CD integration via exit codes

## Session Resume

If interrupted (Ctrl+C), the Q&A session saves progress to `.template-init-session.json`. On next run, you'll be prompted to resume.

**Resume Behavior:**
- Automatically detects incomplete session
- Prompts to resume or start fresh
- Preserves all answered questions
- Continues from last completed section

## Input Validation

All inputs are validated during Q&A session:
- **Template names**: alphanumeric + hyphens only (^[a-z0-9-]+$), 3-50 characters
- **Technology choices**: verified against known options
- **Architecture patterns**: validated against supported patterns
- **Version numbers**: format validation for framework versions

## Error Handling

Graceful error handling with clear messages:
- **Q&A cancellation**: Returns to prompt, saves session state
- **Generation failures**: Shows error details, suggests fixes
- **Save failures**: Reports specific issues (permissions, disk space)
- **Validation errors**: Actionable recommendations for improvement

## Troubleshooting

### Q&A Session Fails
- Check `.template-init-session.json` exists and is valid JSON
- Verify Python 3.8+ installed
- Ensure terminal supports interactive input
- Clear session file if corrupted: `rm .template-init-session.json`

### Template Generation Fails
- Review Q&A answers (saved in session file)
- Check disk space available
- Verify write permissions to output location
- Check Python dependencies installed

### Agent Setup Fails
- Ensure global agents exist in `installer/core/agents/`
- Check agent markdown files are valid
- Verify agent generation dependencies

### Validation Fails (--validate)
- Check quality-report.md for specific issues
- Review validation-report.md for detailed findings
- Address blocking issues before re-running
- Consider using /template-validate for comprehensive audit

### Save Fails
- Check destination directory writable
- Verify no existing template with same name
- Ensure sufficient disk space
- Check file system permissions

### Exit Code Issues (CI/CD)
- Only applies when --validate flag used
- Without --validate, exit code always 0 (success) or 3 (error)
- Quality thresholds: 0 (≥8), 1 (6-7.9), 2 (<6), 3 (error)
- Review validation-report.md for score details

## Understanding Boundary Sections

Boundary sections define agent behavior using three tiers:

**ALWAYS (5-7 rules)**: Non-negotiable actions
- Format: `✅ [action] ([rationale])`
- Example: `✅ Run build verification before tests (block if compilation fails)`

**NEVER (5-7 rules)**: Prohibited actions
- Format: `❌ Never [action] ([rationale])`
- Example: `❌ Never approve code with failing tests (zero tolerance policy)`

**ASK (3-5 scenarios)**: Escalation situations
- Format: `⚠️ [scenario]: Ask [clarification] ([context])`
- Example: `⚠️ Coverage 70-79%: Ask if acceptable given task complexity`

**Why Boundary Sections?**

GitHub analysis of 2,500+ repositories identified explicit boundaries as Critical Gap #4:
- Prevents costly mistakes
- Reduces human intervention by 40%
- Improves agent discoverability
- Sets clear behavior expectations

**Validation:**
During agent enhancement (Option A or B), boundary sections are automatically validated:
- Section presence (all three required)
- Rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- Emoji format (✅/❌/⚠️ prefixes)
- Placement (after "Quick Start", before "Capabilities")

## Related Commands

- `/template-create` - Create template from existing codebase (brownfield)
- `/template-validate <path>` - Comprehensive 16-section audit (Level 3 validation)
- `/agent-enhance <template>/<agent> --hybrid` - Quick agent enhancement (2-5 min)
- `/task-work TASK-AGENT-XXX` - Full agent enhancement workflow (30-60 min)
- `guardkit init <template>` - Initialize project using template

## Dependencies

### Internal
- Q&A session infrastructure (TASK-001B)
- Agent orchestration (TASK-009)
- Settings generator (TASK-005)
- AI analysis (TASK-006)
- Claude MD generation (TASK-007)
- Template generation (TASK-008)
- Validation system (TASK-040, TASK-043)
- Quality scoring (TASK-INIT-006)
- Discovery metadata (TASK-INIT-008)

### External
None (uses Python stdlib only)

## Testing

### Unit Tests
Located in `tests/test_template_init/`:
- `test_command.py` - Command orchestration
- `test_ai_generator.py` - Template generation
- `test_models.py` - Data models
- `test_errors.py` - Error handling
- `test_validation.py` - Validation system
- `test_boundary_sections.py` - Boundary section generation
- `test_discovery_metadata.py` - Metadata generation
- `test_quality_scoring.py` - Quality score calculation

### Integration Tests
Located in `tests/integration/`:
- `test_template_init_flow.py` - End-to-end workflow
- `test_template_init_resume.py` - Session resume
- `test_template_init_validation.py` - Input validation
- `test_template_init_locations.py` - Output location handling
- `test_template_init_exit_codes.py` - CI/CD exit code behavior

### Manual Testing
```bash
# Basic usage
/template-init

# With validation
/template-init --validate

# Repository location
/template-init --output-location=repo

# Complete workflow
/template-init --validate --output-location=repo --no-create-agent-tasks
```

## See Also

- [Template Philosophy Guide](../../docs/guides/template-philosophy.md) - Why templates?
- [Template Validation Guide](../../docs/guides/template-validation-guide.md) - Validation levels
- [Agent Discovery Guide](../../docs/guides/agent-discovery-guide.md) - Discovery metadata
- [GitHub Agent Best Practices Analysis](../../docs/analysis/github-agent-best-practices-analysis.md) - Boundary sections research
- [template-create.md](./template-create.md) - Brownfield template creation
- [TASK-5E55 Gap Analysis](../../tasks/completed/template-init-porting/TASK-5E55-parity-analysis.md) - Feature parity review

---

**Status**: ✅ IMPLEMENTED (TASK-011, TASK-INIT-001 through TASK-INIT-009)
**Version**: 2.0.0
**Last Updated**: 2025-11-26
**Ported Features**: 13 features from /template-create (boundary sections, agent tasks, validation L1/L2/L3, quality scoring, two-location output, discovery metadata, exit codes)
