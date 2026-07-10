---
format_version: 1
description: Reference slices for /template-create — extended documentation, not a command. Run /template-create.
---

# Template Create — Reference Slices

> **Reference file — not a command.** On-demand extension of `template-create.md`
> (K13 core/`-ext` shape, PB-13 wave 1). The core file's Command Options table,
> phase sequence, and Command Execution protocol are normative; nothing here
> overrides them.

## Output Structure

Creates complete template package in one of two locations (TASK-068):

### Default (Progressive Disclosure)

**Personal Use (default):**
```
~/.agentecflow/templates/{template_name}/
├── manifest.json                # Template metadata (TASK-005)
├── settings.json                # Generation settings (TASK-006)
├── CLAUDE.md                    # Core documentation (~8KB) (TASK-007)
├── docs/                        # Extended documentation (split structure)
│   ├── patterns/
│   │   └── README.md            # Pattern documentation
│   └── reference/
│       └── README.md            # Reference documentation
├── templates/                   # Template files (TASK-008)
│   ├── Domain/
│   │   ├── GetEntity.cs.template
│   │   └── CreateEntity.cs.template
│   ├── ViewModels/
│   │   └── EntityViewModel.cs.template
│   └── Views/
│       └── EntityPage.xaml.template
├── agents/                      # Custom agents (TASK-009)
│   ├── domain-operations-specialist.md      # Core (~6KB)
│   ├── domain-operations-specialist-ext.md  # Extended content
│   ├── mvvm-viewmodel-specialist.md         # Core (~6KB)
│   └── mvvm-viewmodel-specialist-ext.md     # Extended content
└── validation-report.md         # Quality report (TASK-043, only with --validate)
```
✅ Immediately available for `guardkit init {template_name}` without running install.sh

**Distribution (--output-location repo):**
```
installer/core/templates/{template_name}/
├── manifest.json
├── settings.json
├── CLAUDE.md                    # Core documentation
├── docs/                        # Extended documentation
│   ├── patterns/
│   └── reference/
├── templates/
├── agents/                      # Core + extended files
│   ├── specialist.md
│   └── specialist-ext.md
└── validation-report.md         # Only with --validate
```
⚠️ Requires running `./installer/scripts/install.sh` before use
📦 Suitable for version control and team distribution

### Single-File Mode (Not Recommended)

```bash
/template-create --no-split
```

Produces single CLAUDE.md and single agent files without progressive disclosure structure.

### Size Targets

| File | Target | Validation |
|------|--------|------------|
| CLAUDE.md (core) | ≤10KB | Warning at 15KB |
| Agent (core) | ≤15KB | Warning at 20KB |
| Token Reduction | ≥50% | Validated during /agent-enhance |

**Benefits:**
- 55-60% token reduction in typical tasks
- Faster AI responses from reduced initial context
- Same comprehensive content available on-demand

### Rules Structure Output (Default)

By default, the command generates a modular `.claude/rules/` directory (use `--no-rules-structure` to opt out):

```
~/.agentecflow/templates/{template_name}/
├── .claude/
│   ├── CLAUDE.md                    # Core documentation (~5KB)
│   └── rules/
│       ├── code-style.md            # paths: **/*.{ext}
│       ├── testing.md               # paths: **/*.test.*, **/tests/**
│       ├── patterns/
│       │   ├── repository.md
│       │   └── service-layer.md
│       └── agents/
│           ├── specialist-a.md      # paths: **/relevant/**
│           └── specialist-b.md
├── templates/
└── agents/                          # (legacy location, also generated)
```

**Benefits:**
- Path-specific loading: Rules only load when touching relevant files
- Reduced context window: 60-70% reduction vs single file
- Better organization: Related rules grouped in subdirectories
- Conditional agents: Agent guidance loads only when relevant

**Path Frontmatter:**

Rules files can include `paths:` frontmatter for conditional loading:

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules

These rules apply only when editing API-related files.
```

**When to Use:**
- Large templates (>20KB CLAUDE.md)
- Complex multi-technology stacks
- Templates with many specialized agents
- Performance-critical workflows

## AI-Native Codebase Analysis (Phase 1) - TASK-51B2

AI analyzes codebase directly and infers ALL metadata without Q&A or detector code.

### What AI Infers

**Language Detection**:
- Analyzes file extensions: `.py`, `.ts`, `.cs`, `.go`, `.rs`
- Reads config files: `package.json`, `requirements.txt`, `*.csproj`, `go.mod`, `Cargo.toml`
- Infers primary language with confidence score

**Framework Detection**:
- Analyzes dependencies in:
  - Python: `requirements.txt`, `pyproject.toml`
  - TypeScript: `package.json` dependencies
  - .NET: `*.csproj` PackageReference
  - Go: `go.mod` require statements
- Common frameworks: FastAPI, Flask, Django, React, Next.js, Vue, Angular, ASP.NET, Express

**Architecture Pattern**:
- Analyzes folder structure: `api/`, `models/`, `services/`, `controllers/`, `components/`, `domain/`, `infrastructure/`
- Identifies: Layered, MVC, MVVM, Clean Architecture, Hexagonal, Microservices

**Testing Framework**:
- Analyzes test files and dependencies
- Python: pytest, unittest
- TypeScript: Jest, Vitest, Mocha
- .NET: xUnit, NUnit, MSTest
- Go: testing package, testify

**Template Name**:
- Suggests based on language + framework
- Examples: "fastapi-python", "react-typescript", "nextjs-fullstack"

### How It Works

1. **Stratified Sampling**: Collects up to 20 representative files from codebase
2. **AI Prompt**: Requests structured analysis including metadata inference
3. **No Human Interaction**: AI infers everything from codebase files
4. **Confidence Scoring**: AI provides confidence level for inferences (90%+ = high)

### Fallback Behavior

If AI confidence is low (<50%), reasonable defaults are used:
- Template name from directory name
- Language from most common file extension
- Architecture from folder structure heuristics

Use `--name` flag to specify a custom template name if AI-generated name is not suitable.

## AI Analysis Output (Phase 1 Result)

Uses `architectural-reviewer` agent to analyze codebase:

**Input**:
- File samples (up to 20 stratified samples)
- Directory structure tree
- NO template context (AI infers everything)

**Output** (`CodebaseAnalysis`):
```python
@dataclass
class CodebaseAnalysis:
    # Technology Information
    technology: TechnologyInfo
        - primary_language: str
        - frameworks: List[str]
        - testing_frameworks: List[str]
        - build_tools: List[str]
        - databases: List[str]
        - infrastructure: List[str]

    # Architecture Information
    architecture: ArchitectureInfo
        - architectural_style: str
        - patterns: List[str]
        - layers: List[LayerInfo]
        - dependency_flow: str

    # Quality Assessment
    quality: QualityAssessment
        - solid_compliance: float (0-100)
        - dry_compliance: float (0-100)
        - yagni_compliance: float (0-100)
        - strengths: List[str]
        - improvements: List[str]

    # Example Files
    example_files: List[ExampleFile]
        - path: str
        - purpose: str
        - language: str
        - patterns_used: List[str]
        - key_concepts: List[str]

    # Overall Confidence
    overall_confidence: ConfidenceScore
        - percentage: int (0-100)
        - reasoning: str
```

## Component Generation (Phases 3-7)

### Manifest Generation (Phase 3)

Generates `manifest.json`:
```json
{
  "schema_version": "1.0.0",
  "name": "csharp-maui-mvvm-template",
  "display_name": "C# MAUI MVVM",
  "description": "C# template using MVVM architecture with .NET MAUI",
  "version": "1.0.0",
  "author": "Your Name",
  "language": "C#",
  "language_version": "net8.0",
  "frameworks": [
    {"name": ".NET MAUI", "version": "8.0", "purpose": "ui"},
    {"name": "xUnit", "version": "2.6.0", "purpose": "testing"}
  ],
  "architecture": "MVVM",
  "patterns": ["Result type pattern", "Repository pattern"],
  "layers": ["Domain", "ViewModels", "Views"],
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Name of the project/solution",
      "required": true,
      "pattern": "^[A-Za-z][A-Za-z0-9_]*$"
    }
  },
  "tags": ["csharp", "maui", "mvvm", "mobile"],
  "category": "mobile",
  "complexity": 6,
  "created_at": "2024-01-15T10:30:00Z",
  "source_project": "/path/to/analyzed/codebase",
  "confidence_score": 87
}
```

### Settings Generation (Phase 4)

Generates `settings.json`:
```json
{
  "schema_version": "1.0.0",
  "naming_conventions": {
    "class": {
      "pattern": "{{Name}}",
      "case_style": "PascalCase",
      "suffix": ".cs",
      "examples": ["GetProducts", "CreateOrder"]
    },
    "interface": {
      "pattern": "I{{Name}}",
      "case_style": "PascalCase",
      "prefix": "I",
      "suffix": ".cs"
    }
  },
  "file_organization": {
    "by_layer": true,
    "by_feature": false,
    "test_location": "separate",
    "max_files_per_directory": 50
  },
  "layer_mappings": {
    "Domain": {
      "directory": "src/Domain",
      "namespace_pattern": "{{ProjectName}}.Domain.{{SubPath}}",
      "file_patterns": ["*.cs", "!*Test.cs"]
    }
  },
  "code_style": {
    "indentation": "spaces",
    "indent_size": 4,
    "line_length": 120,
    "trailing_commas": false
  }
}
```

### Template File Generation (Phase 5) [REORDERED]

For each example file:
1. Read original content
2. Use AI to extract intelligent placeholders
3. Replace specific values with `{{PlaceholderName}}`
4. Preserve code structure and patterns
5. Validate template quality
6. Save as `.template` file

Example transformation:
```csharp
// Original: GetProducts.cs
namespace MyApp.Domain.Products;

public class GetProducts
{
    public ErrorOr<List<Product>> Handle() { ... }
}

// Generated: GetEntity.cs.template
namespace {{ProjectName}}.Domain.{{EntityNamePlural}};

public class {{Verb}}{{EntityNamePlural}}
{
    public ErrorOr<List<{{EntityName}}>> Handle() { ... }
}
```

### Agent Recommendation (Phase 6) [REORDERED]

Identifies capability needs and generates custom agents:

**Capability Analysis**:
- MVVM patterns → `mvvm-viewmodel-specialist`
- Navigation patterns → `navigation-specialist`
- ErrorOr usage → `error-pattern-specialist`
- Domain operations → `domain-operations-specialist`

**Agent Generation**:
- Uses `architectural-reviewer` to generate agent definitions
- Based on actual code examples from codebase
- Captures project-specific patterns and conventions
- Marks reusable agents for global library

**Boundary Sections**: Agents include ALWAYS/NEVER/ASK sections conforming to GitHub best practices (2,500+ repo analysis). See [Understanding Boundary Sections](#understanding-boundary-sections) below.

### Agent Formatting (Phase 5.5) [AUTOMATIC]

**Runs automatically after agent generation**, before CLAUDE.md generation.

During template creation, `/template-create` automatically runs `/agent-format` on all generated agents:

**Why `/agent-format` (not `/agent-enhance`)?**

1. **Speed**: Completes in <1 minute for all agents
2. **No AI Cost**: Template creation is free (no Claude API calls)
3. **Reusability**: Generic boundaries work for ANY project
4. **Progressive Enhancement**: Users can upgrade to 9/10 later

**Result**: All template agents ship with:
- ✅ GitHub-compliant boundaries (6/10 quality)
- ✅ Proper placement (lines 80-150)
- ✅ ALWAYS/NEVER/ASK framework
- ✅ Role-specific content (testing/architecture/etc.)

### Quality Tier System

Templates use a **two-tier quality approach**:

| Tier | Quality | How | When |
|------|---------|-----|------|
| **Template** | 6/10 | `/agent-format` (auto) | Template creation |
| **Project** | 9/10 | `/agent-enhance` (manual) | After project init |

### For Template Users

When you initialize a project from a template:
```bash
guardkit init react-typescript
# All agents have generic boundaries (6/10)

# Optional: Upgrade to domain-specific (9/10)
/agent-enhance .claude/agents/api-specialist.md
```

This approach ensures:
- ✅ Templates are fast to create
- ✅ Users get immediate value (6/10 > 0/10)
- ✅ Users can enhance when needed
- ✅ No forced AI costs during template creation

### CLAUDE.md Generation (Phase 7) [REORDERED]

**CRITICAL CHANGE** (TASK-019A): This phase NOW runs AFTER agents are generated.

Generates comprehensive project documentation with:
- Architecture overview with layer descriptions
- Technology stack with versions
- Project structure visualization
- Naming conventions with examples
- Patterns and best practices
- Code examples from analysis
- Quality standards (coverage, SOLID scores)
- **Agent usage** (NOW scans actual agents from Phase 6)
  - Eliminates AI hallucinations about non-existent agents
  - Documents only agents that actually exist
  - Extracts metadata from agent frontmatter
  - Groups agents by category (domain, ui, testing, etc.)

## Understanding Boundary Sections

As of TASK-STND-773D (2025-11-22), all enhanced agents include **ALWAYS/NEVER/ASK boundary sections** conforming to GitHub best practices (analysis of 2,500+ repositories).

### Format Specification

**Structure**:
- **ALWAYS** (5-7 rules): Non-negotiable actions the agent MUST perform
- **NEVER** (5-7 rules): Prohibited actions the agent MUST avoid
- **ASK** (3-5 scenarios): Situations requiring human escalation

**Emoji Format**:
- ✅ ALWAYS prefix (green checkmark)
- ❌ NEVER prefix (red X)
- ⚠️ ASK prefix (warning sign)

**Rule Format**: `[emoji] [action] ([brief rationale])`

### Examples

**Testing Agent** (GitHub-compliant format):
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

**Repository Agent** (GitHub-compliant format):
```markdown
## Boundaries

### ALWAYS
- ✅ Inject repositories via constructor (enforces DI pattern)
- ✅ Return ErrorOr<T> for all operations (consistent error handling)
- ✅ Use async/await for database operations (prevents thread blocking)
- ✅ Implement IDisposable for database connections (resource cleanup)
- ✅ Validate input parameters before database access (prevent injection)

### NEVER
- ❌ Never use `new()` for repository instantiation (breaks testability and DI)
- ❌ Never expose IQueryable outside repository (violates encapsulation)
- ❌ Never use raw SQL without parameterization (SQL injection risk)
- ❌ Never ignore database errors (silent failures prohibited)
- ❌ Never commit transactions within repository (violates SRP)

### ASK
- ⚠️ Complex joins across >3 tables: Ask if raw SQL vs EF Core query
- ⚠️ Caching strategy needed: Ask if in-memory vs distributed cache
- ⚠️ Soft delete vs hard delete: Ask for data retention policy decision
```

### DO and DON'T

**✅ DO**:
- Use specific, actionable verbs ("Validate input", "Run tests", "Log errors")
- Include brief rationale in parentheses ("(prevents SQL injection)", "(ensures audit trail)")
- Follow emoji format consistently (✅ ALWAYS, ❌ NEVER, ⚠️ ASK)
- Maintain rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)

**❌ DON'T**:
- Use vague language ("Handle things properly", "Be careful")
- Omit rationale ("Validate input" without explaining why)
- Mix emoji formats (🚫 instead of ❌)
- Exceed count limits (8+ rules per section becomes overwhelming)

### Validation

Enhanced agents are validated for:
- **Section Presence**: All three sections (ALWAYS, NEVER, ASK) must exist
- **Rule Counts**: 5-7 ALWAYS, 5-7 NEVER, 3-5 ASK
- **Emoji Format**: Correct emoji prefixes (✅/❌/⚠️)
- **Placement**: Boundaries section after "Quick Start", before "Capabilities"

**Validation Output**:
```yaml
validation_report:
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  boundary_completeness:
    always_count: 6 ✅
    never_count: 6 ✅
    ask_count: 4 ✅
    emoji_correct: true ✅
    format_valid: true ✅
    placement_correct: true ✅
  overall_status: PASSED
```

### Background

**Why Boundary Sections?**

GitHub analysis of 2,500+ repositories identified explicit boundaries as **Critical Gap #4** (0/10 score). Research shows:
- Boundary clarity prevents mistakes and reduces human intervention by 40%
- Explicit ALWAYS/NEVER/ASK framework reduces ambiguity in agent behavior
- Consistent format improves agent discoverability and reusability

**References**:
- [GitHub Agent Best Practices Analysis](../../docs/analysis/github-agent-best-practices-analysis.md)
- [agent-content-enhancer.md](../../installer/core/agents/agent-content-enhancer.md) (detailed specification)
- [TASK-STND-773D](../../tasks/in_progress/TASK-STND-773D-standardize-agent-boundary-sections.md) (implementation task)

## Error Handling

### Common Errors

**Codebase Not Found**:
```
Error: Codebase path does not exist: /path/to/codebase
Solution: Verify path and try again
```

**AI Analysis Failed**:
```
Warning: AI analysis failed, falling back to heuristics
Impact: Lower confidence scores, less detailed analysis
```

**No Template Files Generated**:
```
Error: No valid template files generated
Possible causes:
- No eligible source files found
- All files failed validation
Solution: Check --max-templates setting or file patterns
```

**Save Permission Denied**:
```
Error: Permission denied writing to /output/path
Solution: Check directory permissions or use --output to specify different path
```

### Validation

Validates each component before saving:

**Manifest Validation**:
- Required fields present (name, language, architecture)
- Valid placeholder patterns
- Valid complexity score (1-10)

**Settings Validation**:
- Valid case styles (PascalCase, camelCase, etc.)
- Valid test location (separate, adjacent, none)
- Valid layer mappings

**Template Validation**:
- Placeholders match format `{{Name}}`
- Content not empty
- Language-specific syntax checks
- Placeholder usage consistency

## Examples

### Personal Template (Default - Immediate Use)
```bash
$ /template-create

# Creates in ~/.agentecflow/templates/
# Immediately available without install.sh

[... Q&A and generation ...]

✅ Template Package Created Successfully!

📁 Location: ~/.agentecflow/templates/my-template/
🎯 Type: Personal use (immediately available)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  └── agents/ (2 agents)

📝 Next Steps:
   guardkit init my-template
```

### Team Distribution Template
```bash
$ /template-create --output-location repo

# Creates in installer/core/templates/
# For version control and team distribution

[... Q&A and generation ...]

✅ Template Package Created Successfully!

📁 Location: installer/core/templates/my-template/
📦 Type: Distribution (requires installation)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  └── agents/ (2 agents)

📝 Next Steps:
   git add installer/core/templates/my-template/
   git commit -m "Add my-template template"
   ./installer/scripts/install.sh
   guardkit init my-template
```

### Template with Extended Validation
```bash
$ /template-create --validate

# Runs all standard phases PLUS Phase 5.7 Extended Validation
# Generates detailed quality report

[... Q&A and generation ...]

============================================================
Phase 5.7: Extended Validation
------------------------------------------------------------
  Running extended validation checks...

  Overall Score: 8.7/10 (Grade: A-)
  Production Ready: ✅ Yes
  Exit Code: 0

  Recommendations: 2
    - Standardize placeholder naming conventions across all templates
    - Enhance CLAUDE.md with more detailed architecture and examples

  ✓ Validation report: ~/.agentecflow/templates/my-template/validation-report.md

============================================================

✅ Template Package Created Successfully!

📁 Location: ~/.agentecflow/templates/my-template/
🎯 Type: Personal use (immediately available)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  ├── agents/ (2 agents)
  └── validation-report.md (12 KB)

📝 Next Steps:
   guardkit init my-template

# Exit code: 0 (production ready - score ≥8/10)
$ echo $?
0
```

**Quality Score Interpretation:**
- **8-10 (Grade A/B+)**: Production ready - Exit code 0
- **6-7.9 (Grade B/C)**: Needs improvement - Exit code 1
- **<6 (Grade F)**: Not ready - Exit code 2

### Modular Rules Structure (Default)
```bash
$ /template-create

# Default behavior generates modular .claude/rules/ structure
# TASK-TC-DEFAULT-FLAGS: Rules structure is now the default

[... Q&A and generation ...]

✅ Template Package Created Successfully!

📁 Location: ~/.agentecflow/templates/my-template/
🎯 Type: Personal use (immediately available)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── .claude/
  │   └── rules/
  │       ├── core.md (8 KB) - Core principles and philosophy
  │       ├── stack.md (12 KB) - Stack-specific guidance
  │       ├── quality.md (6 KB) - Quality gates and standards
  │       ├── workflow.md (10 KB) - Development workflows
  │       └── agents.md (8 KB) - Agent integration
  ├── templates/ (15 files)
  └── agents/ (2 agents)

📝 Next Steps:
   guardkit init my-template

# To use progressive disclosure (split files) instead:
$ /template-create --no-rules-structure
```

### Basic Usage (Legacy Example)
```bash
$ /template-create

============================================================
  Template Creation - Brownfield Q&A
============================================================

Where is the codebase you want to convert to a template?
  [1] Current directory (./)
  [2] Specify path

Enter number (default: 1): 1

What should this template be called?
  (Detected: maui-app-template)

Enter value (default: maui-app-template): dotnet-maui-mvvm

[... rest of Q&A ...]

✓ Q&A complete

🔍 Analyzing codebase...
  ✓ Collected 10 file samples
  ✓ Built directory tree
  ✓ AI analysis complete (confidence: 87%)

📝 Generating manifest...
  ✓ Template: dotnet-maui-mvvm
  ✓ Language: C# (net8.0)
  ✓ Architecture: MVVM
  ✓ Complexity: 6/10

⚙️  Generating settings...
  ✓ 5 naming conventions
  ✓ 3 layer mappings
  ✓ Code style: C# defaults

🎨 Generating templates...
  ✓ Domain/GetEntity.cs.template
  ✓ Domain/CreateEntity.cs.template
  ✓ ViewModels/EntityViewModel.cs.template
  ✓ Views/EntityPage.xaml.template
  Total: 15 template files

🤖 Determining agent needs...
  ✓ Identified 3 capability needs
  ✓ Found 2 gaps to fill

💡 Creating project-specific agents...
  → Generating: mvvm-viewmodel-specialist
    ✓ Created (confidence: 85%)
  → Generating: domain-operations-specialist
    ✓ Created (confidence: 90%)

📚 Generating CLAUDE.md...
  ✓ Architecture overview
  ✓ Technology stack
  ✓ 3 code examples
  ✓ Quality standards
  ✓ Agent usage (2 agents documented)

✅ Template package created successfully!

Output: ./templates/dotnet-maui-mvvm/
  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  └── agents/ (2 agents)

Next steps:
1. Review generated files in ./templates/dotnet-maui-mvvm/
2. Test template with: guardkit init dotnet-maui-mvvm
3. Share template with team or contribute to global library
```

### Dry Run Mode
```bash
$ /template-create --dry-run

[... performs analysis ...]

✓ Analysis complete

📋 Template Generation Plan:

Template: python-fastapi-clean
Language: Python (>=3.9)
Architecture: Clean Architecture
Complexity: 7/10

Components:
✓ manifest.json (would generate)
✓ settings.json (would generate)
✓ CLAUDE.md (would generate)
✓ 22 template files (would generate)
✓ 3 custom agents (would generate)

No files written (--dry-run mode)
```

### Custom Output Path (DEPRECATED)
```bash
# DEPRECATED: Use --output-location instead
$ /template-create --path ~/projects/my-app --output ~/templates/my-template

✓ Analyzing: ~/projects/my-app
✓ Output to: ~/templates/my-template

[... generation ...]

✅ Template saved to: ~/templates/my-template

# RECOMMENDED: Use --output-location for standard workflows
$ /template-create --path ~/projects/my-app  # Personal use
$ /template-create --path ~/projects/my-app -o repo  # Distribution
```

## Integration Points

### With /template-init (Greenfield)
```bash
# Greenfield: Create from scratch
/template-init
→ Q&A about technology choices
→ AI generates intelligent defaults
→ Template created without existing code

# Brownfield: Create from existing code
/template-create
→ Q&A about existing codebase
→ AI analyzes actual code
→ Template extracted from examples
```

### With guardkit init
```bash
# After creating template
/template-create
→ Output: ./templates/my-template/

# Use template
guardkit init my-template
→ Applies template to new project
→ Prompts for placeholder values
→ Generates project structure
```

### With Task Workflow
```bash
# Template creation as a task
/task-create "Create template from MyApp codebase"
/task-work TASK-XXX
→ Executes /template-create orchestration
→ Reviews generated artifacts
→ Tests template application
/task-complete TASK-XXX
```

## Implementation Details

### Python Modules

**Core Orchestrator**:
- `installer/core/commands/lib/template_create_orchestrator.py` - Main orchestration logic

**Component Generators** (from dependencies):
- `installer/core/commands/lib/template_qa_session.py` - Q&A (TASK-001)
- `installer/core/lib/codebase_analyzer/ai_analyzer.py` - Analysis (TASK-002)
- `installer/core/lib/template_creation/manifest_generator.py` - Manifest (TASK-005)
- `installer/core/lib/settings_generator/generator.py` - Settings (TASK-006)
- `installer/core/lib/template_generator/claude_md_generator.py` - CLAUDE.md (TASK-007)
- `installer/core/lib/template_generator/template_generator.py` - Templates (TASK-008)
- `installer/core/lib/agent_generator/agent_generator.py` - Agents (TASK-009)

**Dependencies**:
- Python 3.8+ (stdlib for Q&A)
- All component generators as per their TASK specifications

### Architecture

Follows orchestrator pattern:
- **Orchestrator**: Coordinates workflow, doesn't do implementation work
- **Components**: Each phase handled by specialized generator
- **Error Handling**: Graceful degradation (e.g., fallback to heuristics if AI fails)
- **Progress Display**: Clear feedback at each phase
- **Validation**: Validates outputs before proceeding to next phase

## Testing

**Test Files**:
- `tests/integration/test_template_create_orchestrator.py` - Full workflow tests
- `tests/unit/test_template_create_phases.py` - Individual phase tests

**Coverage Target**: >80%

**Key Test Scenarios**:
- Complete end-to-end workflow
- Q&A session integration
- AI analysis success and fallback
- All component generations
- Dry run mode
- Error handling for each phase
- Output validation
- Custom output paths

## Performance Considerations

**Typical Execution Time**:
- Q&A Session: 2-5 minutes (user-dependent)
- AI Analysis: 10-30 seconds
- Component Generation: 5-15 seconds
- Template File Generation: 1-3 seconds per file
- Total: 3-8 minutes for typical codebase

**Optimization Tips**:
- Use `--max-templates` to limit file generation
- Use `--skip-qa` for repeated runs during testing
- Use `--dry-run` to preview without file I/O

## Related Commands

- `/template-init` - Greenfield template creation (no existing codebase)
- `/template-create-qa` - Standalone Q&A session for greenfield
- `guardkit init` - Apply template to new project
- `/task-create` - Create development task

## Dependencies

**Required Tasks** (must be completed):
- TASK-001: Brownfield Q&A Session
- TASK-002: AI Codebase Analyzer
- TASK-005: Manifest Generator
- TASK-006: Settings Generator
- TASK-007: CLAUDE.md Generator
- TASK-008: Template File Generator
- TASK-009: Agent Recommender

**Optional Dependencies**:
- `architectural-reviewer` agent (falls back to heuristics if unavailable)
- MCP servers (context7, design-patterns) for enhanced analysis

## Future Enhancements

Planned for future iterations:
- Template versioning and upgrade paths
- Multi-codebase analysis (extract common patterns from multiple projects)
- Template composition (combine multiple templates)
- CI/CD integration (automated template updates)
- Template marketplace integration
- Incremental updates (detect changes and update template)

## See Also

### Command Documentation
- [Agent Enhance Command](agent-enhance.md) - Enhance individual agents with template-specific content

### Workflow Guides
- [Agent Enhancement Decision Guide](../../../docs/guides/agent-enhancement-decision-guide.md) - Choose between /agent-format and /agent-enhance
- [Incremental Enhancement Workflow](../../../docs/workflows/incremental-enhancement-workflow.md) - Phase 8 agent enhancement strategies

### Implementation Tasks
- [TASK-010: /template-create Command Orchestrator](../../tasks/backlog/TASK-010-template-create-command.md)
- [Template Creation Workflow](../../docs/workflows/template-creation-workflow.md)
- [Architecture Decision: Orchestrator Pattern](../../docs/decisions/orchestrator-pattern.md)

---


**Usage examples (moved verbatim from the core's `## Usage` section):**

```bash
# AI-native mode (default - AI analyzes codebase directly)
/template-create

# With custom template name
/template-create --name my-custom-template

# Custom name with validation
/template-create --name my-api-template --validate

# Custom name for team distribution
/template-create --name company-api-template --output-location repo

# Create for team distribution (requires install.sh)
/template-create --output-location repo
/template-create -o repo  # Short form

# Default behavior (rules structure - TASK-TC-DEFAULT-FLAGS)
/template-create

# Opt-out to use progressive disclosure instead of rules structure
/template-create --no-rules-structure

# Combined with validation
/template-create --validate

# Custom name (uses rules structure by default)
/template-create --name my-template

# Analyze specific codebase path
/template-create --path /path/to/codebase

# Save to custom output directory (DEPRECATED: use --output-location)
/template-create --output /path/to/output

# Maximum number of template files to generate
/template-create --max-templates 20

# Dry run (analyze only, don't save)
/template-create --dry-run
```

