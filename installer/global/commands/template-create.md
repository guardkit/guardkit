# Template Create - AI-Powered Template Generation from Existing Codebase

Orchestrates complete template creation from existing codebases using AI-powered analysis and generation.

**Status**: IMPLEMENTED (TASK-010)

## Purpose

Automate template creation from brownfield (existing) codebases by:
1. Running interactive Q&A to gather context (TASK-001)
2. Analyzing codebase with AI (TASK-002)
3. Generating manifest.json (TASK-005)
4. Generating settings.json (TASK-006)
5. Generating CLAUDE.md (TASK-007)
6. Generating .template files (TASK-008)
7. Recommending specialized agents (TASK-009)
8. Saving complete template package

## Usage

```bash
# Interactive mode (default - creates in ~/.agentecflow/templates/)
/template-create

# Create for team distribution (requires install.sh)
/template-create --output-location repo
/template-create -o repo  # Short form

# Analyze specific codebase path
/template-create --path /path/to/codebase

# Skip Q&A and use defaults
/template-create --skip-qa

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
Phase 1: Q&A Session (TASK-001)
├─ Interactive questions about codebase
├─ Codebase path selection
└─ Context gathering (8 questions)

Phase 2: AI Analysis (TASK-002)
├─ File collection (max 10 samples)
├─ Directory tree generation
├─ AI-powered architecture analysis
└─ Quality assessment

Phase 3: Manifest Generation (TASK-005)
├─ Template identity (name, version, author)
├─ Technology stack detection
├─ Framework version inference
├─ Placeholder extraction
└─ Complexity scoring

Phase 4: Settings Generation (TASK-006)
├─ Naming conventions extraction
├─ File organization patterns
├─ Layer mappings
├─ Code style inference
└─ Generation options

Phase 5: Template File Generation (TASK-008) [REORDERED]
├─ AI-powered placeholder extraction
├─ Template content generation
├─ Pattern identification
├─ Quality scoring
└─ Validation

Phase 5.5: Completeness Validation (TASK-040)
├─ CRUD operation completeness checks
├─ Layer symmetry validation
├─ False negative detection
├─ Auto-fix recommendations
└─ Quality gate enforcement

Phase 6: Agent Recommendation (TASK-009) [REORDERED]
├─ Capability needs identification
├─ Gap analysis vs existing agents
├─ AI-powered agent generation
└─ Reusability assessment

Phase 7: CLAUDE.md Generation (TASK-007) [REORDERED]
├─ Architecture overview
├─ Technology stack documentation
├─ Project structure visualization
├─ Naming conventions guide
├─ Patterns and best practices
├─ Code examples
├─ Quality standards
└─ Agent usage (NOW scans actual agents from Phase 6)

Phase 8: Template Package Assembly
├─ Directory structure creation
├─ File writing (manifest, settings, CLAUDE.md)
├─ Template files organization
├─ Agent files (if generated)
└─ Validation summary

Phase 5.7: Extended Validation (TASK-043) [OPTIONAL - only with --validate]
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

--skip-qa                Skip interactive Q&A, use defaults
                         Default: false

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

## Q&A Session (Phase 1)

Interactive session with 8 questions:

### Section 1: Codebase Location
```
Where is the codebase you want to convert to a template?
  Options:
  - Current directory
  - Specify path
```

### Section 2: Template Identity
```
What should this template be called?
  Validation: 3-50 chars, alphanumeric + hyphens/underscores
  Default: {inferred from directory name}
```

### Section 3: Technology Stack
```
Primary language? (auto-detected if possible)
  Options: C#, TypeScript, Python, Java, Kotlin, Go, Rust, Other
```

### Section 4: Template Purpose
```
What is the primary purpose of this template?
  [1] Start new projects quickly
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold
```

### Section 5: Architecture Pattern
```
Primary architecture pattern? (auto-detected if possible)
  Options: MVVM, Clean, Hexagonal, Layered, MVC, Other
```

### Section 6: Example Files
```
Include example files in analysis?
  Options: All matching files, Specific paths, Auto-select best examples
```

### Section 7: Agent Preferences
```
Generate custom agents for project-specific patterns?
  [Yes] Generate agents for capabilities not in global library
  [No] Use only global agents
```

### Section 8: Confirmation
```
Summary of detected patterns and planned template structure.
Confirm to proceed with generation?
```

## AI Analysis (Phase 2)

Uses `architectural-reviewer` agent to analyze codebase:

**Input**:
- File samples (up to 10 representative files)
- Directory structure tree
- Q&A context (language, architecture, purpose)

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
