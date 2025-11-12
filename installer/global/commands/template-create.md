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

**Note**: As of TASK-51B2, the command uses AI-native analysis. No Q&A sessions, no detector code - AI analyzes codebases directly and infers all metadata. Use `/template-qa` for interactive customization if needed.

## Usage

```bash
# AI-native mode (default - AI analyzes codebase directly)
/template-create

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
```

## Output Structure

Creates complete template package in one of two locations (TASK-068):

**Personal Use (default):**
```
~/.agentecflow/templates/{template_name}/
├── manifest.json                # Template metadata (TASK-005)
├── settings.json                # Generation settings (TASK-006)
├── CLAUDE.md                    # Project documentation (TASK-007)
├── templates/                   # Template files (TASK-008)
│   ├── Domain/
│   │   ├── GetEntity.cs.template
│   │   └── CreateEntity.cs.template
│   ├── ViewModels/
│   │   └── EntityViewModel.cs.template
│   └── Views/
│       └── EntityPage.xaml.template
├── agents/                      # Custom agents (TASK-009)
│   ├── domain-operations-specialist.md
│   └── mvvm-viewmodel-specialist.md
└── validation-report.md         # Quality report (TASK-043, only with --validate)
```
✅ Immediately available for `taskwright init {template_name}` without running install.sh

**Distribution (--output-location repo):**
```
installer/global/templates/{template_name}/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── templates/
├── agents/
└── validation-report.md         # Only with --validate
```
⚠️ Requires running `./installer/scripts/install.sh` before use
📦 Suitable for version control and team distribution

## Command Options

### Required Options
None - all options have defaults

### Optional Options

```bash
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

See `/template-qa` command for interactive customization if AI inference is insufficient.

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
   taskwright init my-template
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
   taskwright init my-template
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
   taskwright init my-template

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
2. Test template with: taskwright init dotnet-maui-mvvm
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

### With taskwright init
```bash
# After creating template
/template-create
→ Output: ./templates/my-template/

# Use template
taskwright init my-template
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
- `taskwright init` - Apply template to new project
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

- [TASK-010: /template-create Command Orchestrator](../../tasks/backlog/TASK-010-template-create-command.md)
- [Template Creation Workflow](../../docs/workflows/template-creation-workflow.md)
- [Architecture Decision: Orchestrator Pattern](../../docs/decisions/orchestrator-pattern.md)

---

## Execution

When user invokes `/template-create [args]`, execute this checkpoint-resume workflow:

### Step 1: Parse Arguments

Extract arguments from user command:
- `--path PATH`: Codebase path (default: current directory)
- `--output-location global|repo`: Where to save template (default: global)
- `--skip-qa`: Skip Q&A session
- `--dry-run`: Analysis only, don't save
- `--validate`: Run extended validation
- `--max-templates N`: Limit template file count
- `--no-agents`: Skip agent generation
- `--max-iterations N`: Maximum checkpoint-resume iterations (default: 5)

Build Python command:
```bash
# Note: Cannot use '-m installer.global...' because 'global' is a reserved keyword
# Command uses direct file path execution instead (see Step 2 for implementation)
python3 <taskwright_path>/installer/global/commands/lib/template_create_orchestrator.py \
  [--path PATH] \
  [--output-location LOCATION] \
  [--skip-qa] \
  [--dry-run] \
  [--validate] \
  [--max-templates N] \
  [--no-agents]
```

### Step 2: Checkpoint-Resume Loop

Execute orchestrator in a loop to handle agent invocations:



### Exit Code Reference

| Code | Meaning | Cleanup | Break |
|------|---------|---------|-------|
| 0 | Success | Yes | Yes |
| 1 | User cancelled | Yes | Yes |
| 2 | Codebase not found | Yes | Yes |
| 3 | AI analysis failed | Yes | Yes |
| 4 | Component generation failed | Yes | Yes |
| 5 | Validation failed | Yes | Yes |
| 6 | Save failed | Yes | Yes |
| 42 | Need agent invocation | No | No (continue loop) |
| 130 | Interrupted (Ctrl+C) | No | Yes |

### Agent Invocation Flow

```
1. Orchestrator runs → Exit 42
2. Command reads .agent-request.json
3. Command validates request format
4. Command checks for stale files
5. Command invokes agent via Task tool
6. Agent returns response (or times out/errors)
7. Command writes .agent-response.json
8. Command deletes .agent-request.json
9. Command re-runs orchestrator with --resume
10. Orchestrator reads .agent-response.json
11. Orchestrator continues or exits with 0/error
```

### Error Handling Strategy

**File I/O Errors:**
- Malformed JSON: Print error, cleanup, break
- Missing files: Print error, cleanup, break
- Write failures: Print error, cleanup, break
- Delete failures: Print warning, continue

**Agent Invocation Errors:**
- Task tool unavailable: Write error response, continue (orchestrator handles)
- Agent timeout: Write timeout response, continue
- Agent error: Write error response, continue

**Loop Control:**
- Maximum iterations: Prevents infinite loops
- Cleanup on all error exits
- No cleanup on Ctrl+C (preserves session state)

```python
import json
from pathlib import Path
import time
import sys
from datetime import datetime

# Configuration
DEFAULT_MAX_ITERATIONS = 5
ORCHESTRATOR_TIMEOUT_MS = 600000  # 10 minutes
STALE_FILE_THRESHOLD_SECONDS = 600  # 10 minutes
DEFAULT_AGENT_TIMEOUT_SECONDS = 120  # 2 minutes
MAX_REQUEST_SIZE_BYTES = 1024 * 1024  # 1 MB
MAX_RESPONSE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

max_iterations = DEFAULT_MAX_ITERATIONS  # Configurable via --max-iterations
iteration = 0
resume_flag = False

# ============================================================================
# PYTHONPATH Discovery and Setup
# ============================================================================
# Fix for TASK-BRIDGE-005: Set PYTHONPATH so Python can find 'installer' module
# when running from any directory (not just taskwright directory)

def find_taskwright_path():
    """
    Find taskwright installation directory.

    Tries multiple strategies in priority order:
    1. Follow ~/.agentecflow symlink (if exists and points to taskwright)
    2. Check standard location: ~/Projects/appmilla_github/taskwright
    3. Check current directory (fallback for development)

    Returns:
        Path object pointing to taskwright directory, or None if not found
    """
    from pathlib import Path

    # Strategy 1: Follow ~/.agentecflow symlink
    agentecflow = Path.home() / ".agentecflow"
    if agentecflow.is_symlink():
        target = agentecflow.resolve()
        # Symlink points to taskwright/.agentecflow, go up one level
        if target.name == ".agentecflow":
            taskwright_path = target.parent
            if (taskwright_path / "installer").exists():
                return taskwright_path

    # Strategy 2: Standard installation location
    standard_path = Path.home() / "Projects" / "appmilla_github" / "taskwright"
    if (standard_path / "installer").exists():
        return standard_path

    # Strategy 3: Current directory (if running from taskwright directory)
    if Path("installer").exists():
        return Path.cwd()

    return None

# Discover taskwright installation directory
taskwright_path = find_taskwright_path()

if taskwright_path is None:
    print("❌ ERROR: Cannot find taskwright installation directory")
    print()
    print("   Searched locations:")
    print("   - ~/.agentecflow symlink target")
    print("   - ~/Projects/appmilla_github/taskwright")
    print("   - Current directory: " + str(Path.cwd()))
    print()
    print("   Troubleshooting:")
    print("   1. Verify taskwright is installed:")
    print("      ls ~/Projects/appmilla_github/taskwright")
    print("   2. Check symlink configuration:")
    print("      ls -la ~/.agentecflow")
    print("   3. Run install.sh if needed:")
    print("      ~/Projects/appmilla_github/taskwright/installer/scripts/install.sh")
    print()
    print("   Manual workaround:")
    print("   export PYTHONPATH=\"~/Projects/appmilla_github/taskwright:$PYTHONPATH\"")
    print("   /template-create --path .")
    sys.exit(1)

# Set PYTHONPATH to include taskwright directory
# Preserve existing PYTHONPATH by appending (not replacing)
import os
original_pythonpath = os.environ.get("PYTHONPATH", "")
if original_pythonpath:
    os.environ["PYTHONPATH"] = f"{taskwright_path}:{original_pythonpath}"
else:
    os.environ["PYTHONPATH"] = str(taskwright_path)

print(f"🔍 Taskwright path: {taskwright_path}")
print(f"🐍 PYTHONPATH: {os.environ['PYTHONPATH']}")
print()

# ============================================================================
# End PYTHONPATH Setup
# ============================================================================

# Exit code messages: (message, should_cleanup, should_break)
# - message: User-facing message to display
# - should_cleanup: Whether to remove temporary files
# - should_break: Whether to exit the loop
EXIT_MESSAGES = {
    0: ("✅ Template created successfully!", True, True),
    1: ("⚠️  Template creation cancelled by user", True, True),
    2: ("❌ ERROR: Codebase not found or inaccessible", True, True),
    3: ("❌ ERROR: AI analysis failed", True, True),
    4: ("❌ ERROR: Component generation failed", True, True),
    5: ("❌ ERROR: Validation failed", True, True),
    6: ("❌ ERROR: Save failed (check permissions and disk space)", True, True),
    130: ("⚠️  Template creation interrupted (Ctrl+C)\n   Session state saved - you can resume later", False, True),
}

# Build initial command
# CRITICAL: Cannot use '-m installer.global...' because 'global' is a reserved keyword
# Use direct file path execution instead
orchestrator_script = taskwright_path / "installer" / "global" / "commands" / "lib" / "template_create_orchestrator.py"
cmd_parts = [
    "python3",
    str(orchestrator_script)
]

# Add user arguments
if path:
    cmd_parts.extend(["--path", path])
if output_location:
    cmd_parts.extend(["--output-location", output_location])
if skip_qa:
    cmd_parts.append("--skip-qa")
if dry_run:
    cmd_parts.append("--dry-run")
if validate:
    cmd_parts.append("--validate")
if max_templates:
    cmd_parts.extend(["--max-templates", str(max_templates)])
if no_agents:
    cmd_parts.append("--no-agents")

print("🚀 Starting template creation...\n")

# Execution loop
while iteration < max_iterations:
    iteration += 1

    # Add --resume flag if this is a resume run
    if resume_flag and "--resume" not in cmd_parts:
        cmd_parts.append("--resume")

    # Run orchestrator with PYTHONPATH set
    cmd_without_env = " ".join(cmd_parts)
    # Prepend PYTHONPATH export to command so bash subprocess can find installer module
    cmd = f'PYTHONPATH="{taskwright_path}" {cmd_without_env}'
    print(f"📍 Iteration {iteration}: Running orchestrator...")

    result = await bash(cmd, timeout=ORCHESTRATOR_TIMEOUT_MS)
    exit_code = result.exit_code

    # Handle exit code using dispatch pattern
    if exit_code in EXIT_MESSAGES:
        message, should_cleanup, should_break = EXIT_MESSAGES[exit_code]
        print(f"\n{message}")
        if should_cleanup:
            cleanup_all_temp_files()
        if should_break:
            break

    elif exit_code == 42:
        # NEED_AGENT - Handle agent invocation
        print(f"\n🔄 Agent invocation required...\n")

        # Read agent request
        request_file = Path(".agent-request.json")
        if not request_file.exists():
            print("❌ ERROR: Agent request file not found")
            print("   This is a bug in the orchestrator - please report it.")
            cleanup_all_temp_files()
            break

        # Check for stale files
        try:
            age_seconds = time.time() - request_file.stat().st_mtime
            if age_seconds > STALE_FILE_THRESHOLD_SECONDS:
                print(f"⚠️  Warning: Request file is {age_seconds:.0f}s old (may be stale)")
        except Exception:
            pass  # Ignore stat errors

        # Check file size
        try:
            request_size = request_file.stat().st_size
            if request_size > MAX_REQUEST_SIZE_BYTES:
                print(f"❌ ERROR: Agent request file too large ({request_size} bytes)")
                print(f"   Maximum allowed: {MAX_REQUEST_SIZE_BYTES} bytes")
                cleanup_request_file()
                break
        except Exception as e:
            print(f"⚠️  Warning: Could not check request file size: {e}")

        # Parse agent request
        try:
            request_data = json.loads(request_file.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Malformed agent request file: {e}")
            cleanup_request_file()
            break
        except Exception as e:
            print(f"❌ ERROR: Failed to read agent request: {e}")
            cleanup_request_file()
            break

        # Validate required fields with types
        required_fields = {
            "agent_name": str,
            "prompt": str,
            "request_id": str,
            "version": str
        }

        validation_failed = False
        for field, expected_type in required_fields.items():
            if field not in request_data:
                print(f"❌ ERROR: Missing required field '{field}' in agent request")
                cleanup_request_file()
                validation_failed = True
                break
            if not isinstance(request_data[field], expected_type):
                print(f"❌ ERROR: Field '{field}' has wrong type (expected {expected_type.__name__})")
                cleanup_request_file()
                validation_failed = True
                break

        if validation_failed:
            break

        agent_name = request_data["agent_name"]
        prompt = request_data["prompt"]
        request_id = request_data["request_id"]

        # Validate timeout with type checking
        timeout_seconds = request_data.get("timeout_seconds", DEFAULT_AGENT_TIMEOUT_SECONDS)
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            print(f"⚠️  Warning: Invalid timeout_seconds, using default ({DEFAULT_AGENT_TIMEOUT_SECONDS}s)")
            timeout_seconds = DEFAULT_AGENT_TIMEOUT_SECONDS

        print(f"  Agent: {agent_name}")
        print(f"  Timeout: {timeout_seconds}s")
        print(f"  Invoking agent...\n")

        # Invoke agent via Task tool
        start_time = time.time()

        try:
            agent_response = await invoke_agent_subagent(
                agent_name=agent_name,
                prompt=prompt,
                timeout_seconds=timeout_seconds
            )
            status = "success"
            error_message = None
            error_type = None
        except NameError as e:
            print(f"  ❌ Task tool not available in this environment")
            agent_response = None
            status = "error"
            error_message = "Task tool is not available"
            error_type = "TaskToolUnavailable"
        except TimeoutError as e:
            print(f"  ⚠️  Agent invocation timed out")
            agent_response = None
            status = "timeout"
            error_message = str(e)
            error_type = "TimeoutError"
        except Exception as e:
            print(f"  ⚠️  Agent invocation failed: {e}")
            agent_response = None
            status = "error"
            error_message = str(e)
            error_type = type(e).__name__

        duration = time.time() - start_time

        # Write response
        response_data = {
            "request_id": request_id,
            "version": "1.0",
            "status": status,
            "response": agent_response,
            "error_message": error_message,
            "error_type": error_type,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": round(duration, 3),
            "metadata": {
                "agent_name": agent_name,
                "model": "claude-sonnet-4-5"
            }
        }

        response_file = Path(".agent-response.json")

        # Check response size before writing
        response_json = json.dumps(response_data, indent=2)
        if len(response_json) > MAX_RESPONSE_SIZE_BYTES:
            print(f"  ❌ ERROR: Agent response too large ({len(response_json)} bytes)")
            print(f"     Writing minimal error response instead...")
            # Write minimal error response
            error_response = {
                "request_id": request_id,
                "version": "1.0",
                "status": "error",
                "error_type": "ResponseTooLarge",
                "error_message": f"Agent response exceeded {MAX_RESPONSE_SIZE_BYTES} bytes",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            response_json = json.dumps(error_response, indent=2)

        # Write response file
        try:
            response_file.write_text(response_json)
        except Exception as e:
            print(f"  ❌ Failed to write agent response: {e}")
            cleanup_all_temp_files()
            break

        print(f"  ✓ Response written ({duration:.1f}s)")

        # Verify response file exists and is readable
        if not response_file.exists():
            print("  ❌ ERROR: Failed to verify response file")
            cleanup_all_temp_files()
            break

        try:
            # Validate we can read it back
            json.loads(response_file.read_text())
        except Exception as e:
            print(f"  ❌ ERROR: Response file corrupted: {e}")
            cleanup_all_temp_files()
            break

        # Cleanup request file after successful response write
        try:
            request_file.unlink()
        except Exception as e:
            print(f"  ⚠️  Warning: Could not delete request file: {e}")

        print(f"  🔄 Resuming orchestrator...\n")

        # Set resume flag for next iteration
        resume_flag = True

    else:
        # Unknown exit code
        print(f"\n❌ ERROR: Unexpected exit code {exit_code}")
        cleanup_all_temp_files()
        break

# Check for infinite loop
if iteration >= max_iterations:
    print(f"\n❌ ERROR: Maximum iterations ({max_iterations}) reached")
    print("   This may indicate a bug - please report it")
    cleanup_all_temp_files()

def cleanup_request_file():
    """Remove agent request file only"""
    try:
        Path(".agent-request.json").unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️  Warning: Could not delete request file: {e}")

def cleanup_response_file():
    """Remove agent response file only"""
    try:
        Path(".agent-response.json").unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️  Warning: Could not delete response file: {e}")

def cleanup_all_temp_files():
    """Remove all temporary files"""
    for file in [".agent-request.json", ".agent-response.json", ".template-create-state.json"]:
        try:
            Path(file).unlink(missing_ok=True)
        except Exception as e:
            print(f"⚠️  Warning: Could not delete {file}: {e}")

async def invoke_agent_subagent(agent_name: str, prompt: str, timeout_seconds: int = 120) -> str:
    """
    Invoke agent using Task tool.

    Args:
        agent_name: Name of agent to invoke
        prompt: Complete prompt text
        timeout_seconds: Maximum wait time (currently not enforced by Task tool)

    Returns:
        Agent response text

    Raises:
        NameError: If Task tool is not available
        TimeoutError: If agent exceeds timeout
        Exception: If agent invocation fails
    """
    # Map agent names to subagent types
    #
    # To add new agent mappings:
    # 1. Add entry: "agent-name": "subagent-type"
    # 2. Ensure subagent type exists in Claude Code agent registry
    # 3. Test invocation with /template-create
    #
    # Common subagent types:
    # - "software-architect": Architecture and design decisions
    # - "code-reviewer": Code quality and best practices
    # - "qa-tester": Testing strategies and coverage
    # - "general-purpose": General analysis and recommendations
    agent_mapping = {
        "architectural-reviewer": "software-architect",
        "software-architect": "software-architect",
        "code-reviewer": "code-reviewer",
        "qa-tester": "qa-tester",
    }

    # Get mapped subagent type or use direct mapping
    subagent_type = agent_mapping.get(agent_name)
    if not subagent_type:
        print(f"⚠️  Warning: Unknown agent '{agent_name}', using direct mapping")
        subagent_type = agent_name

    # Invoke via Task tool
    try:
        result = await task(
            subagent_type=subagent_type,
            description=f"Template analysis: {agent_name}",
            prompt=prompt
        )
        return result
    except NameError:
        # Task tool not available
        raise
    except Exception as e:
        # Other errors during invocation
        raise
```