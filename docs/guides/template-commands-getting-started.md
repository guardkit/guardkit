# Getting Started with Template Commands

**Purpose**: Complete beginner's guide to creating custom templates using `/template-create` and `/template-init` commands.

**Learn templates in**:
- **5 minutes**: Quick Start
- **15 minutes**: Core Concepts
- **45 minutes**: Complete Walkthrough

---

## Quick Start (5 minutes)

### What Are Template Commands?

GuardKit provides two complementary commands for creating custom project templates:

1. **`/template-create`** (Brownfield) - Extract templates from existing codebases
2. **`/template-init`** (Greenfield) - Create templates from scratch with AI assistance

### Which Command Should I Use?

```
Do you have existing code?
├─ YES → Use /template-create (extracts patterns from your codebase)
└─ NO  → Use /template-init (AI helps you design from scratch)
```

### Quick Example: Create Template from Existing Code

```bash
# Start in your existing project directory
cd ~/projects/my-maui-app

# Run template creation
/template-create

# Answer 8 quick questions about your codebase
# AI analyzes your code and generates template
# Complete template saved to installer/local/templates/
```

**Result**: Reusable template with your exact patterns, naming conventions, and architecture.

### Quick Example: Create Template from Scratch

```bash
# Start anywhere
/template-init

# Answer ~42 questions about technology choices
# AI generates intelligent defaults
# Complete template saved to installer/local/templates/
```

**Result**: Production-ready template based on best practices for your chosen stack.

---

## Core Concepts (15 minutes)

### Understanding the Template System

#### Template Structure

Every template contains 4 essential components:

```
installer/local/templates/my-template/
├── manifest.json          # What: Template metadata
├── settings.json          # How: Naming conventions & structure
├── CLAUDE.md             # Why: Architecture & best practices
└── templates/            # Code: Actual template files
    ├── domain/
    ├── viewmodels/
    └── views/
```

#### Template Placeholders

Templates use placeholders that get replaced during project generation:

| Placeholder | Example | Description |
|-------------|---------|-------------|
| `{{ProjectName}}` | "ShoppingApp" | Root project name |
| `{{EntityName}}` | "Product" | Entity/model name |
| `{{Verb}}` | "Get", "Create" | Action verb |
| `{{FeatureName}}` | "Products" | Feature/module name |

**Example Template File**:
```csharp
// GetEntity.cs.template
namespace {{ProjectName}}.Domain.{{EntityNamePlural}};

public class {{Verb}}{{EntityNamePlural}}
{
    public ErrorOr<List<{{EntityName}}>> Execute() { }
}

// Becomes (when used):
namespace ShoppingApp.Domain.Products;

public class GetProducts
{
    public ErrorOr<List<Product>> Execute() { }
}
```

### Brownfield vs Greenfield

#### Brownfield (/template-create)

**Best for**:
- Converting existing codebases to templates
- Capturing team's established patterns
- Preserving working architectures
- Creating templates from proven designs

**Process**:
1. AI analyzes codebase automatically (~30 seconds)
2. AI infers language, framework, architecture from code
3. Extracts patterns automatically
4. Generates template with your conventions

**Input**: Existing codebase
**Output**: Template matching your exact patterns

#### Greenfield (/template-init)

**Best for**:
- Starting new project types
- Designing ideal architecture
- Learning new technologies
- Prototyping approaches

**Process**:
1. Q&A session (42 questions, ~8 minutes)
2. AI generates intelligent defaults
3. Creates best-practice structure
4. Recommends appropriate agents

**Input**: Your technology preferences
**Output**: AI-designed template with best practices

### Key Differences

| Aspect | /template-create | /template-init |
|--------|------------------|----------------|
| **Input** | Existing code | Technology choices |
| **Questions** | 8 questions (~3 min) | 42 questions (~8 min) |
| **AI Role** | Pattern extraction | Design generation |
| **Output Quality** | Matches your code | Best practices |
| **Use When** | Have working code | Starting fresh |
| **Confidence** | Based on analysis | Based on knowledge |

### The Complete Workflow

```
Phase 1: Choose Command
├─ Existing code? → /template-create
└─ Starting fresh? → /template-init

Phase 2: Answer Questions
├─ /template-create: 8 questions about codebase
└─ /template-init: 42 questions about preferences

Phase 3: AI Processing
├─ Code analysis (brownfield)
└─ Template generation (greenfield)

Phase 4: Template Creation
├─ manifest.json
├─ settings.json
├─ CLAUDE.md
├─ Code templates
└─ Specialized agents

Phase 5: Use Template
└─ guardkit init my-template
```

### What Gets Generated

#### manifest.json
Contains template metadata:
- Name, description, version
- Technology stack details
- Architecture patterns used
- Placeholders and their rules
- Complexity score (1-10)

#### settings.json
Defines project conventions:
- Naming patterns for classes, files, etc.
- Layer organization structure
- File organization rules
- Code style preferences

#### CLAUDE.md
AI guidance document:
- Architecture overview
- Technology stack description
- Project structure explanation
- Naming conventions with examples
- Patterns and best practices
- Quality standards
- Usage guidelines for AI agents

#### templates/
Actual code templates:
- Domain operations
- ViewModels, Views
- Repositories, Services
- Test templates
- Configuration files

Each file uses placeholders that get replaced during generation.

#### agents/ (Optional)
Custom AI agents specialized for your stack:
- Domain specialists
- Testing specialists
- UI specialists
- Architecture enforcers

---

## Complete Walkthrough (45 minutes)

### Part 1: Brownfield - Extract from Existing Code

Let's walk through creating a template from an existing .NET MAUI app.

#### Prerequisites

```bash
# You need:
- An existing codebase with consistent patterns
- Python 3.8+ (for template tools)
- Terminal access

# Optional but helpful:
- Multiple example files (5-10 minimum)
- Clear architecture patterns
- Established naming conventions
```

#### Step 1: Navigate to Codebase

```bash
cd ~/projects/my-maui-app
```

#### Step 2: Run /template-create

```bash
/template-create
```

You'll see:
```
============================================================
  Template Creation - Brownfield Q&A
============================================================

This will analyze your codebase and create a reusable template.
Press Ctrl+C at any time to save progress.
```

#### Step 3: Answer Questions

**Question 1: Codebase Location**
```
Where is the codebase you want to convert to a template?
  [1] Current directory (./)
  [2] Specify path

Enter number (default: 1): 1
```

**Question 2: Template Name**
```
What should this template be called?
  (Detected: maui-app)

Enter value (default: maui-app): mycompany-maui-template
```

**Question 3: Primary Language**
```
Primary language? (auto-detected if possible)
  [1] C#
  [2] TypeScript
  [3] Python
  [4] Java
  [5] Other

Detected: C#
Enter number (default: 1): 1
```

**Question 4: Template Purpose**
```
What is the primary purpose of this template?
  [1] Start new projects quickly
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold

Enter number (default: 1): 2
```

**Question 5: Architecture Pattern**
```
Primary architecture pattern? (auto-detected if possible)
  [1] MVVM
  [2] Clean Architecture
  [3] Hexagonal
  [4] Layered
  [5] MVC
  [6] Other

Detected: MVVM
Enter number (default: 1): 1
```

**Question 6: Example Files**
```
Include example files in analysis?
  [1] All matching files
  [2] Specific paths
  [3] Auto-select best examples

Enter number (default: 3): 3
```

**Question 7: Agent Preferences**
```
Generate custom agents for project-specific patterns?
  [1] Yes - Generate agents for capabilities not in global library
  [2] No - Use only global agents

Enter number (default: 1): 1
```

**Question 8: Confirmation**
```
Summary of detected patterns:
- Language: C#
- Framework: .NET MAUI 8.0
- Architecture: MVVM
- Patterns: Domain operations, Repository, ErrorOr
- Layers: Domain, ViewModels, Views, Data
- Example files: 10 files selected

Confirm and proceed with generation? (Y/n): Y
```

#### Step 4: Watch AI Analysis

```
✅ Q&A complete

🔍 Analyzing codebase...
  ✓ Collected 10 file samples
  ✓ Built directory tree
  ✓ AI analysis complete (confidence: 87%)
```

The AI analyzes your code to extract:
- Naming patterns
- Architecture structure
- Common patterns
- Error handling approaches
- Testing strategies

#### Step 5: Template Generation

```
📝 Generating manifest...
  ✓ Template: mycompany-maui-template
  ✓ Language: C# (net8.0)
  ✓ Architecture: MVVM
  ✓ Patterns: 5 detected
  ✓ Placeholders: 8 defined
  ✓ Complexity: 6/10

⚙️  Generating settings...
  ✓ 5 naming conventions
  ✓ 3 layer mappings
  ✓ Code style: C# defaults

📚 Generating CLAUDE.md...
  ✓ Architecture overview
  ✓ Technology stack
  ✓ Project structure
  ✓ 3 code examples
  ✓ Quality standards

🎨 Generating templates...
  ✓ Domain/GetEntity.cs.template
  ✓ Domain/CreateEntity.cs.template
  ✓ ViewModels/EntityViewModel.cs.template
  ✓ Views/EntityPage.xaml.template
  ✓ Views/EntityPage.xaml.cs.template
  Total: 15 template files

🤖 Determining agent needs...
  ✓ Identified 3 capability needs
  ✓ Found 2 gaps to fill

💡 Creating project-specific agents...
  → Generating: mvvm-viewmodel-specialist
    ✓ Created (confidence: 85%)
  → Generating: domain-operations-specialist
    ✓ Created (confidence: 90%)
```

#### Step 6: Review Output

```
✅ Template package created successfully!

Output: installer/local/templates/mycompany-maui-template/
  ├── manifest.json (15 KB)
  ├── settings.json (8 KB)
  ├── CLAUDE.md (42 KB)
  ├── templates/ (15 files)
  └── agents/ (2 agents)

Next steps:
1. Review generated files
2. Test template: guardkit init mycompany-maui-template
3. Customize if needed
4. Share with team
```

#### Step 7: Test Your Template

```bash
# Create test project
mkdir ~/test-template
cd ~/test-template

# Initialize with your template
guardkit init mycompany-maui-template

# Verify files generated correctly
ls -la src/
```

### Part 2: Greenfield - Design from Scratch

Let's create a Python FastAPI template from scratch.

#### Step 1: Run /template-init

```bash
/template-init
```

#### Step 2: Complete Q&A (10 Sections)

The Q&A is longer (~42 questions) but guides you through complete design:

**Section 1: Template Identity** (2 questions)
```
What should this template be called?
Enter value: python-fastapi-clean

What is the primary purpose of this template?
  [1] Start new projects quickly
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold
Enter number: 4
```

**Section 2: Technology Stack** (3 questions)
```
Primary language?
  [1] C#
  [2] TypeScript
  [3] Python    ← Select this
  [4] Java
Enter number: 3

Framework?
  [1] FastAPI    ← Auto-detected for Python
  [2] Django
  [3] Flask
Enter number: 1

Framework version?
  [1] Latest (0.104+)
  [2] LTS
  [3] Specific version
Enter number: 1
```

**Section 3: Architecture Pattern** (2 questions)
```
Primary architecture pattern?
  [1] MVVM
  [2] Clean Architecture    ← Select for FastAPI
  [3] Hexagonal
  [4] Layered
Enter number: 2

Domain modeling approach?
  [1] Rich domain models
  [2] Anemic domain models
  [3] Functional
  [4] Data-centric
Enter number: 1
```

**Section 4: Project Structure** (2 questions)
```
Layer organization?
  [1] Single project
  [2] By layer (Domain, Infrastructure, API)
  [3] By feature (vertical slices)
  [4] Hybrid
Enter number: 2

Standard folders to include?
  [1] src
  [2] tests
  [3] docs
  [4] scripts
  [5] All above
Enter number: 5
```

**Section 5: Testing Strategy** (3 questions)
```
Unit testing framework?
  [1] pytest    ← Auto-select for Python
  [2] unittest
Enter number: 1

Testing scope (select multiple)?
  [1] Unit tests
  [2] Integration tests
  [3] E2E tests
  [4] Performance tests
Enter numbers: 1,2,3

Test pattern preference?
  [1] Arrange-Act-Assert (AAA)
  [2] BDD (Given-When-Then)
  [3] No preference
Enter number: 1
```

**Section 6: Error Handling** (2 questions)
```
Error handling strategy?
  [1] Result type pattern
  [2] Exception-based
  [3] Error codes
  [4] Mixed approach
Enter number: 1

Input validation?
  [1] Pydantic models    ← Perfect for FastAPI
  [2] Manual validation
  [3] Minimal
Enter number: 1
```

**Section 7: Dependency Management** (2 questions)
```
Dependency injection?
  [1] FastAPI built-in (Depends)
  [2] Third-party (dependency-injector)
  [3] Manual
Enter number: 1

Configuration approach?
  [1] Environment variables + Pydantic Settings
  [2] JSON config files
  [3] Both
Enter number: 1
```

**Section 8: UI/Navigation**
```
(Skipped - backend API selected)
```

**Section 9: Additional Patterns** (3 questions)
```
Data access pattern?
  [1] Repository pattern
  [2] Direct ORM access
  [3] CQRS
Enter number: 1

API pattern?
  [1] REST
  [2] REPR (Request-Endpoint-Response)
  [3] GraphQL
Enter number: 2

State management?
  (Not applicable for backend API)
```

**Section 10: Documentation Input** (2 questions)
```
Have documentation to guide template creation?
  [1] Yes
  [2] No
Enter number: 2
```

#### Step 3: Watch AI Generation

```
============================================================
  Phase 2: AI Template Generation
============================================================

🤖 Generating template structure...
  ✓ Analyzed technology choices
  ✓ Generated layer structure
  ✓ Defined naming conventions
  ✓ Created code style guide

📝 Creating manifest.json...
  ✓ Template metadata
  ✓ Technology stack: Python 3.9+, FastAPI 0.104+
  ✓ Architecture: Clean Architecture
  ✓ Patterns: Repository, REPR, Result types

⚙️  Creating settings.json...
  ✓ Naming: snake_case for functions/modules
  ✓ Layer structure: domain, infrastructure, api
  ✓ Test organization: tests/{layer}/

📚 Creating CLAUDE.md...
  ✓ Architecture principles
  ✓ Clean Architecture layers
  ✓ FastAPI best practices
  ✓ Testing strategy
  ✓ Code examples

🎨 Creating code templates...
  ✓ domain/entity.py.template
  ✓ domain/repository_interface.py.template
  ✓ infrastructure/repository_impl.py.template
  ✓ api/endpoint.py.template
  ✓ tests/test_domain.py.template
  Total: 12 template files

============================================================
  Phase 3: Agent System
============================================================

🤖 Setting up agent system...
  ✓ Selected: architectural-reviewer
  ✓ Selected: test-verifier
  ✓ Selected: code-reviewer
  ✓ Generated: python-fastapi-specialist
  ✓ Generated: clean-architecture-specialist
  ✓ Generated: pytest-specialist
  Total: 7 agents ready

============================================================
  Phase 4: Save Template
============================================================

💾 Saving template...
  ✓ Saved: manifest.json
  ✓ Saved: settings.json
  ✓ Saved: CLAUDE.md
  ✓ Saved: 12 code templates
  ✓ Saved: 7 agents
```

#### Step 4: Review Generated Template

```
✅ Template saved to: installer/local/templates/python-fastapi-clean

Template structure:
  ├── manifest.json              (Technology: Python + FastAPI)
  ├── settings.json              (Conventions: Clean Architecture)
  ├── CLAUDE.md                  (Best practices guide)
  ├── templates/
  │   ├── domain/                (Business logic layer)
  │   │   ├── entity.py.template
  │   │   └── repository_interface.py.template
  │   ├── infrastructure/        (Data access layer)
  │   │   └── repository_impl.py.template
  │   ├── api/                   (Presentation layer)
  │   │   └── endpoint.py.template
  │   └── tests/
  │       ├── test_domain.py.template
  │       └── test_api.py.template
  └── agents/
      ├── python-fastapi-specialist.md
      ├── clean-architecture-specialist.md
      └── pytest-specialist.md

💡 Next steps:
   1. Review template at: installer/local/templates/python-fastapi-clean/
   2. Customize agents if needed
   3. Test with: guardkit init python-fastapi-clean
```

#### Step 5: Test Template

```bash
# Create test project
mkdir ~/test-fastapi
cd ~/test-fastapi

# Initialize with template
guardkit init python-fastapi-clean

# Review generated structure
tree src/

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start API
uvicorn src.api.main:app --reload
```

### Part 3: Comparing the Results

#### Brownfield Output (from existing code)

```
mycompany-maui-template/
- Matches YOUR exact patterns
- Uses YOUR naming conventions
- Preserves YOUR architecture decisions
- Includes YOUR team's practices
- Quality: Proven (it's working code)
```

**Best for**: Replicating proven designs

#### Greenfield Output (AI-designed)

```
python-fastapi-clean/
- Based on industry best practices
- Clean Architecture principles
- Modern FastAPI patterns
- Comprehensive test coverage
- Quality: Ideal (best practices)
```

**Best for**: Learning and optimal design

---

## Quick Reference

### Command Comparison

| Feature | /template-create | /template-init |
|---------|------------------|----------------|
| **Input** | Existing codebase | Your preferences |
| **Time** | ~5 min (8 questions) | ~10 min (42 questions) |
| **AI Role** | Extract patterns | Generate design |
| **Output** | Your patterns | Best practices |
| **Session Save** | Yes (Ctrl+C) | Yes (Ctrl+C) |
| **Customization** | Post-generation | Pre-generation (via Q&A) |
| **Confidence** | Code analysis score | Knowledge-based |
| **Agents** | Pattern-specific | Stack-specific |

### When to Use Each

**Use /template-create when**:
- ✅ You have working code with consistent patterns
- ✅ Team wants to replicate proven designs
- ✅ Capturing legacy patterns for migration
- ✅ Converting project to template quickly

**Use /template-init when**:
- ✅ Starting new technology stack
- ✅ Designing ideal architecture
- ✅ Learning best practices
- ✅ No existing code to analyze
- ✅ Want AI-recommended structure

### Next Steps

1. **Try Brownfield**
   ```bash
   cd your-project
   /template-create
   ```

2. **Try Greenfield**
   ```bash
   /template-init
   ```

3. **Deep Dive**
   - [Complete /template-create Walkthrough](./template-create-walkthrough.md)
   - [Complete /template-init Walkthrough](./template-init-walkthrough.md)
   - [Troubleshooting Guide](./template-troubleshooting.md)

4. **Learn More**
   - [Creating Local Templates](./creating-local-templates.md)
   - [Template Command Specification](../../installer/core/commands/template-create.md)
   - [Template Structure Reference](../../docs/architecture/template-structure.md)

---

**Created**: 2025-11-06
**Task**: TASK-014
**Maintained By**: Platform Team
