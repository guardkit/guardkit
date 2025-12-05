# Template Create - AI-Powered Template Generation from Existing Codebase

Orchestrates complete template creation from existing codebases using AI-powered analysis and generation.

**Status**: IMPLEMENTED (TASK-010)

## Purpose

Automate template creation from brownfield (existing) codebases by:
1. AI-native codebase analysis (TASK-51B2) - AI infers language, framework, architecture directly
2. Generating manifest.json (TASK-005)
3. Generating settings.json (TASK-006)
4. Generating .template files (TASK-008)
5. Generating CLAUDE.md (TASK-007)
6. Recommending specialized agents (TASK-009)
7. Saving complete template package

**Note**: As of TASK-51B2, the command uses AI-native analysis. No Q&A sessions, no detector code - AI analyzes codebases directly and infers all metadata. Use `--name` flag to override AI-generated template names if needed.

## Usage

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

# Analyze specific codebase path
/template-create --path /path/to/codebase

# Save to custom output directory (DEPRECATED: use --output-location)
/template-create --output /path/to/output

# Maximum number of template files to generate
/template-create --max-templates 20

# Dry run (analyze only, don't save)
/template-create --dry-run
```

## Complete Workflow

The command orchestrates all template creation phases:

```
Phase 1: AI-Native Codebase Analysis (TASK-51B2)
├─ File collection (stratified sampling, max 20 samples)
├─ Directory tree generation
├─ AI infers ALL metadata from codebase:
│  ├─ Primary language (from file extensions, config files)
│  ├─ Framework (from dependencies: package.json, requirements.txt, *.csproj)
│  ├─ Architecture pattern (from folder structure)
│  ├─ Testing framework (from test files)
│  └─ Template name (suggested from project)
├─ Architecture analysis (patterns, layers, abstractions)
└─ Quality assessment (SOLID, DRY, YAGNI)

Phase 2: Manifest Generation (TASK-005)
├─ Template identity (name, version, author)
├─ Technology stack detection
├─ Framework version inference
├─ Placeholder extraction
└─ Complexity scoring

Phase 3: Settings Generation (TASK-006)
├─ Naming conventions extraction
├─ File organization patterns
├─ Layer mappings
├─ Code style inference
└─ Generation options

Phase 4: Template File Generation (TASK-008)
├─ AI-powered placeholder extraction
├─ Template content generation
├─ Pattern identification
├─ Quality scoring
└─ Validation

Phase 4.5: Completeness Validation (TASK-040)
├─ CRUD operation completeness checks
├─ Layer symmetry validation
├─ False negative detection
├─ Auto-fix recommendations
└─ Quality gate enforcement

Phase 5: Agent Recommendation (TASK-009)
├─ Capability needs identification
├─ Gap analysis vs existing agents
├─ AI-powered agent generation
└─ Reusability assessment

Phase 5.5: Agent Formatting (Automatic)
├─ Runs /agent-format on all generated agents
├─ Adds boundary section templates (ALWAYS/NEVER/ASK)
├─ Ensures structural consistency
├─ Quality: 6/10 (structural, not domain-specific)
└─ Sets foundation for Phase 8 enhancement

Phase 6: CLAUDE.md Generation (TASK-007)
├─ Template documentation
├─ Usage instructions
├─ Best practices
└─ Agent integration guide

Phase 7: Package Assembly
├─ Directory structure creation
├─ File writing (manifest, settings, CLAUDE.md)
├─ Template files organization
├─ Agent files (if generated)
└─ Validation summary

Phase 7.5: Extended Validation (TASK-043) [OPTIONAL - only with --validate]
├─ Placeholder consistency validation
├─ Pattern fidelity spot-checks (5 random templates)
├─ Documentation completeness verification
├─ Agent reference validation
├─ Manifest accuracy checks
├─ Overall quality score calculation (0-10)
├─ Validation report generation (validation-report.md)
└─ Exit code assignment (0/1/2)

Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95, TASK-UX-3A8D, TASK-DOC-1C5A) [DEFAULT - skip with --no-create-agent-tasks]
├─ Creates one task per agent file
├─ Task metadata includes agent_file, template_dir, template_name, agent_name
├─ Tasks created in backlog with priority: medium
├─ Displays boundary sections announcement (TASK-DOC-1C5A):
│  ├─ Explains ALWAYS (5-7), NEVER (5-7), ASK (3-5) format
│  ├─ Shows emoji prefixes (✅/❌/⚠️)
│  └─ Expected validation output
├─ Displays two enhancement options:
│  ├─ Option A (Recommended): /agent-enhance template-name/agent-name --hybrid (2-5 minutes per agent)
│  └─ Option B (Optional): /task-work TASK-AGENT-XXX (30-60 minutes per agent - full workflow)
└─ Both approaches use the same AI enhancement logic with boundary validation

**Boundary Sections**: Enhanced agents automatically include:
- ALWAYS (5-7 rules): Non-negotiable actions
- NEVER (5-7 rules): Prohibited actions
- ASK (3-5 scenarios): Escalation situations

See [Understanding Boundary Sections](#understanding-boundary-sections) for details.
```

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
installer/global/templates/{template_name}/
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

## Command Options

### Required Options
None - all options have defaults

### Optional Options

```bash
--name NAME              Custom template name (overrides AI-generated name)
                         Pattern: lowercase, numbers, hyphens only (^[a-z0-9-]+$)
                         Length: 3-50 characters
                         Examples: my-api-template, react-admin, dotnet-api
                         Default: AI-generated from codebase analysis

--output-location LOC    Where to save template package (TASK-068)
  -o LOC                 'global' = ~/.agentecflow/templates/ (default, immediate use)
                         'repo' = installer/global/templates/ (distribution, requires install.sh)
                         Default: global

--path PATH              Path to codebase to analyze
                         Default: current directory

--output PATH            DEPRECATED - Output directory for template package
                         Use --output-location instead
                         Default: determined by --output-location

--max-templates N        Maximum template files to generate
                         Default: unlimited (all eligible files)

--dry-run                Analyze and show plan without saving
                         Default: false

--save-analysis          Save analysis JSON for debugging
                         Default: false

--no-agents              Skip agent generation phase
                         Default: false (agents are generated)

--create-agent-tasks     Create individual enhancement tasks for each agent (default: enabled)
                         DEPRECATED: Use --no-create-agent-tasks to disable

--no-create-agent-tasks  Skip agent task creation (TASK-UX-3A8D)
                         Default: false (tasks ARE created by default)

                         By default (when not specified):
                         - Runs Phase 8: Task Creation
                         - Creates one task per agent file
                         - Displays two enhancement options:
                           - Option A (Recommended): /agent-enhance for fast enhancement (2-5 minutes per agent)
                           - Option B (Optional): /task-work for full workflow with quality gates (30-60 minutes)
                         - Both approaches use the same AI enhancement logic
                         - Provides control over which agents to enhance and when

                         Use --no-create-agent-tasks to skip task creation when:
                         - You don't plan to enhance agents immediately
                         - You prefer manual task creation later
                         - You're creating templates for evaluation only

--validate               Run extended validation and generate quality report (TASK-043)
                         Default: false (only Phase 5.5 validation runs)

                         When enabled:
                         - Runs all Phase 5.5 completeness checks
                         - Adds extended validation checks (Phase 5.7)
                         - Generates validation-report.md in template directory
                         - Exit code based on quality score:
                           0 = Score ≥8/10 (production ready)
                           1 = Score 6.0-7.9/10 (needs improvement)
                           2 = Score <6/10 (not ready)

                         Extended checks include:
                         - Placeholder consistency validation
                         - Pattern fidelity spot-checks (5 random files)
                         - Documentation completeness verification
                         - Agent reference validation
                         - Manifest accuracy checks

--verbose                Show detailed progress and debugging info
                         Default: false
```

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
- [agent-content-enhancer.md](../../installer/global/agents/agent-content-enhancer.md) (detailed specification)
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

# Creates in installer/global/templates/
# For version control and team distribution

[... Q&A and generation ...]

✅ Template Package Created Successfully!

📁 Location: installer/global/templates/my-template/
📦 Type: Distribution (requires installation)

  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  └── agents/ (2 agents)

📝 Next Steps:
   git add installer/global/templates/my-template/
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
- `installer/global/commands/lib/template_create_orchestrator.py` - Main orchestration logic

**Component Generators** (from dependencies):
- `installer/global/commands/lib/template_qa_session.py` - Q&A (TASK-001)
- `installer/global/lib/codebase_analyzer/ai_analyzer.py` - Analysis (TASK-002)
- `installer/global/lib/template_creation/manifest_generator.py` - Manifest (TASK-005)
- `installer/global/lib/settings_generator/generator.py` - Settings (TASK-006)
- `installer/global/lib/template_generator/claude_md_generator.py` - CLAUDE.md (TASK-007)
- `installer/global/lib/template_generator/template_generator.py` - Templates (TASK-008)
- `installer/global/lib/agent_generator/agent_generator.py` - Agents (TASK-009)

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

## Exit Codes

- `0` - Template created successfully
- `1` - User cancelled during Q&A
- `2` - Codebase not found or inaccessible
- `3` - AI analysis failed (and no fallback available)
- `4` - Component generation failed
- `5` - Validation failed
- `6` - Save failed (permissions, disk space)
- `130` - Interrupted with Ctrl+C (session saved)

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

## Command Execution

Execute this command using a checkpoint-resume loop that handles Python-Claude agent bridge communication.

### Execution Loop

When the user invokes `/template-create`, execute this loop:

```
LOOP (max 5 iterations to prevent infinite loops):
  1. Run Python orchestrator
  2. Capture exit code
  3. IF exit code == 0: SUCCESS - display results and exit loop
  4. IF exit code == 42: AGENT NEEDED - handle bridge protocol (see below)
  5. IF exit code == other: ERROR - display error and exit loop
  6. After handling exit code 42, add --resume flag and continue loop
```

### Step 1: Run Python Orchestrator

**IMPORTANT**: This script requires Python 3.10+ (uses `|` union type syntax).

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

If Python version error occurs (`TypeError: unsupported operand type(s) for |`), the user needs Python 3.10+.

Capture the exit code from this command.

### Step 2: Handle Exit Code 42 (NEED_AGENT)

When exit code is 42, Python has written a request file and needs Claude to invoke an agent.

**2a. Read the agent request file:**

```bash
cat .agent-request.json
```

The file has this structure:
```json
{
  "request_id": "uuid-string",
  "version": "1.0",
  "phase": 6,
  "phase_name": "agent_generation",
  "agent_name": "architectural-reviewer",
  "prompt": "Full prompt text for the agent...",
  "timeout_seconds": 120,
  "created_at": "ISO-8601-timestamp",
  "context": {},
  "model": null
}
```

**2b. Invoke the agent using Task tool:**

Use the Task tool to invoke the agent specified in `agent_name` with the `prompt` from the request file.

Example:
```
Task: Invoke the "architectural-reviewer" agent with the prompt from .agent-request.json
```

Capture the agent's complete response text.

**2c. Write the agent response file:**

Create `.agent-response.json` with this exact structure:

```json
{
  "request_id": "<copy from request>",
  "version": "1.0",
  "status": "success",
  "response": "<agent's complete response text as a string>",
  "error_message": null,
  "error_type": null,
  "created_at": "<current ISO-8601 timestamp>",
  "duration_seconds": <time taken in seconds>,
  "metadata": {
    "agent_name": "<copy from request>",
    "model": "claude-sonnet-4"
  }
}
```

**CRITICAL**: The `response` field MUST be a string, not an object. If the agent returns JSON, serialize it to a string.

**2d. Delete the request file:**

```bash
rm .agent-request.json
```

**2e. Re-run orchestrator with --resume flag:**

Add `--resume` to the original arguments and continue the loop:

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@" --resume
```

### Step 3: Handle Success (Exit Code 0)

When exit code is 0:
1. Display the success message from Python's output
2. Clean up any remaining bridge files:
   ```bash
   rm -f .agent-request.json .agent-response.json .template-create-state.json
   ```
3. Exit the loop

### Step 4: Handle Errors (Other Exit Codes)

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | SUCCESS | Display results, cleanup, exit |
| 1 | USER_CANCELLED | Display cancellation message |
| 2 | CODEBASE_NOT_FOUND | Display error with path |
| 3 | ANALYSIS_FAILED | Display error, suggest --verbose |
| 4 | GENERATION_FAILED | Display error |
| 5 | VALIDATION_FAILED | Display validation errors |
| 6 | SAVE_FAILED | Display file I/O error |
| 42 | NEED_AGENT | Handle bridge protocol (loop) |
| 130 | INTERRUPTED | Display interruption message |

### Error Handling for Bridge Protocol

**If `.agent-request.json` does not exist when exit code is 42:**
```
ERROR: Exit code 42 received but no .agent-request.json found.
This indicates a bug in the orchestrator. Please report this issue.
```

**If agent invocation fails:**
Write an error response to `.agent-response.json`:
```json
{
  "request_id": "<from request>",
  "version": "1.0",
  "status": "error",
  "response": null,
  "error_message": "<error description>",
  "error_type": "AgentInvocationError",
  "created_at": "<timestamp>",
  "duration_seconds": 0,
  "metadata": {}
}
```
Then continue with `--resume` to let Python handle the fallback.

**If JSON parsing fails:**
Display error and suggest re-running without --resume:
```
ERROR: Failed to parse bridge protocol files.
Try: rm -f .agent-request.json .agent-response.json .template-create-state.json
Then re-run: /template-create [original args]
```

### Example Execution Flow

```
User: /template-create --path /my/project

[Iteration 1]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project
  Exit code: 42

  Read: .agent-request.json
  Agent: architectural-reviewer
  Invoke agent with prompt...
  Write: .agent-response.json
  Delete: .agent-request.json

[Iteration 2]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project --resume
  Exit code: 0

  SUCCESS: Template created at ~/.agentecflow/templates/my-project/
  Cleanup bridge files
  Exit loop
```

**Note**: This command uses the orchestrator pattern with checkpoint-resume. The Python orchestrator handles state persistence in `.template-create-state.json`, and the bridge protocol enables AI-powered agent generation that produces 7-8 agents at 90%+ confidence (vs 3 agents at 68% with heuristic fallback).
