# /template-create Command - Complete Walkthrough

**Purpose**: Step-by-step guide to extracting reusable templates from existing codebases (brownfield approach).

**Time to Complete**: 20-45 minutes (depending on codebase complexity)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Q&A Session](#phase-1-qa-session)
4. [Phase 2: AI Analysis](#phase-2-ai-analysis)
5. [Phase 3: Template Generation](#phase-3-template-generation)
6. [Phase 4: Review & Test](#phase-4-review--test)
7. [Phase 5: Customization](#phase-5-customization)
8. [Real-World Examples](#real-world-examples)
9. [Tips & Best Practices](#tips--best-practices)

---

## Overview

### What is /template-create?

The `/template-create` command analyzes your existing codebase and automatically generates a reusable template that captures your:
- Architecture patterns
- Naming conventions
- Code structure
- Best practices
- Team standards

### When to Use

Use `/template-create` when you:
- ✅ Have a working codebase with consistent patterns
- ✅ Want to replicate successful designs
- ✅ Need to enforce team standards
- ✅ Are standardizing multiple similar projects
- ✅ Want to preserve legacy patterns during migration

### Input → Output

```
INPUT: Existing codebase
  ├── Consistent architecture
  ├── 5-10 example files
  └── Clear patterns

                ↓
         /template-create
                ↓

OUTPUT: Reusable template
  ├── manifest.json (metadata)
  ├── settings.json (conventions)
  ├── CLAUDE.md (guidance)
  ├── templates/ (code files)
  └── agents/ (specialized AI)
```

### Command Options

```bash
# Interactive mode (recommended)
/template-create

# Analyze specific path
/template-create --path /path/to/codebase

# Skip Q&A (use defaults)
/template-create --skip-qa

# Custom output location
/template-create --output /custom/path

# Limit template files generated
/template-create --max-templates 20

# Dry run (analyze without saving)
/template-create --dry-run

# Save analysis for debugging
/template-create --save-analysis

# Skip agent generation
/template-create --no-agents

# Verbose output
/template-create --verbose
```

---

## Prerequisites

### Required

1. **Existing Codebase**
   - Minimum 5-10 example files
   - Consistent architecture patterns
   - Clear naming conventions

2. **Python 3.8+**
   ```bash
   python3 --version
   # Should show 3.8 or higher
   ```

3. **Terminal Access**
   - Can run interactive commands
   - Has write permissions to template directory

### Recommended

1. **Multiple Examples**
   - At least 5-10 files per pattern
   - Clear layer separation
   - Consistent naming

2. **Documentation**
   - README explaining architecture
   - Code comments
   - Architecture diagrams (optional)

3. **Working Code**
   - Builds successfully
   - Tests passing
   - Production-ready quality

### Preparation Checklist

Before running the command:

```bash
# 1. Verify codebase location
cd /path/to/your/codebase
ls -la

# 2. Check Python version
python3 --version

# 3. Review codebase structure
tree -L 2 src/

# 4. Ensure consistent patterns
# - Same naming conventions across files?
# - Clear layer separation?
# - Repeatable patterns?

# 5. Clean up if needed
# - Remove experimental code
# - Delete unused files
# - Fix inconsistent naming
```

---

## Phase 1: Q&A Session

Duration: ~3-5 minutes (8 questions)

### Starting the Session

```bash
cd /path/to/your/codebase
/template-create
```

Output:
```
============================================================
  Template Creation - Brownfield Q&A
============================================================

This will analyze your codebase and create a reusable template.
Estimated time: 5-10 minutes
Press Ctrl+C at any time to save progress and exit.

Starting Q&A session...
```

### Question 1: Codebase Location

```
------------------------------------------------------------
  Section 1: Codebase Location
------------------------------------------------------------

Where is the codebase you want to convert to a template?
  [1] Current directory (./)
  [2] Specify path

Enter number (default: 1):
```

**Tips**:
- Option 1: Use if already in project directory
- Option 2: Specify absolute or relative path

**Example Responses**:
```bash
# Already in correct directory
Enter: 1

# Need to specify path
Enter: 2
Path: /Users/me/projects/my-app
```

### Question 2: Template Name

```
------------------------------------------------------------
  Section 2: Template Identity
------------------------------------------------------------

What should this template be called?
  Validation: 3-50 chars, alphanumeric + hyphens/underscores
  (Detected from directory: my-maui-app)

Enter value (default: my-maui-app):
```

**Naming Guidelines**:
- Use descriptive names: `mycompany-maui-mvvm`
- Include technology: `dotnet-webapi-clean`
- Add purpose: `mobile-appshell-template`
- Avoid generic names: `template1`, `my-template`

**Good Examples**:
- `acme-maui-appshell` - Company + tech + pattern
- `python-fastapi-microservice` - Stack + architecture
- `react-nextjs-dashboard` - Framework + purpose

**Bad Examples**:
- `template` - Too generic
- `my-template-v2-final` - Unclear versioning
- `Template123` - No description

### Question 3: Primary Language

```
Primary language? (auto-detected if possible)
  [1] C#
  [2] TypeScript
  [3] Python
  [4] Java
  [5] Kotlin
  [6] Go
  [7] Rust
  [8] Other

Detected: C# (based on .csproj files)
Enter number (default: 1):
```

**Detection Method**:
- Looks for config files (.csproj, package.json, setup.py)
- Analyzes file extensions
- Checks build files

**If Detection Wrong**:
Simply enter correct number - your choice overrides detection.

### Question 4: Template Purpose

```
What is the primary purpose of this template?
  [1] Start new projects quickly [DEFAULT]
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold

Enter number (default: 1):
```

**Purpose Guide**:

| Choice | Best For | Quality Focus |
|--------|----------|---------------|
| **1. Quick Start** | Rapid prototyping | Speed over rigor |
| **2. Team Standards** | Consistency | Company patterns |
| **3. Prototype** | Experiments | Flexibility |
| **4. Production** | Enterprise apps | Complete quality gates |

**Recommendation**: Choose **2 (Team Standards)** for most internal templates.

### Question 5: Architecture Pattern

```
Primary architecture pattern? (auto-detected if possible)
  [1] MVVM
  [2] Clean Architecture
  [3] Hexagonal
  [4] Layered
  [5] MVC
  [6] Vertical Slice
  [7] Simple (no formal architecture)
  [8] Other

Detected: MVVM (based on ViewModels/ directory)
Enter number (default: 1):
```

**Detection Method**:
- Scans directory names (ViewModels, Domain, Infrastructure)
- Analyzes file organization
- Checks namespace patterns

**Architecture Decision Guide**:

```
Mobile/Desktop App?
├─ MVVM (most common)
└─ MVC (traditional)

Backend API?
├─ Clean Architecture (enterprise)
├─ Hexagonal (ports & adapters)
├─ Vertical Slice (feature-focused)
└─ Layered (traditional)

Microservice?
└─ Hexagonal or Clean

Simple Tool/Script?
└─ Simple (no formal architecture)
```

### Question 6: Example Files

```
Include example files in analysis?
  [1] All matching files (thorough but slow)
  [2] Specific paths (manual selection)
  [3] Auto-select best examples (recommended)

Enter number (default: 3):
```

**Option Comparison**:

| Option | Files Analyzed | Duration | Best For |
|--------|---------------|----------|----------|
| **1. All** | All matching | 2-5 min | Small codebases (<50 files) |
| **2. Specific** | Your selection | 1-2 min | Know best examples |
| **3. Auto** | AI-selected 10 | 30-60 sec | Most cases (recommended) |

**Recommendation**: Use option **3 (Auto)** - AI picks diverse, representative examples.

**If choosing Option 2 (Specific)**:
```
Enter file paths (one per line, empty line when done):
Path: src/Domain/Products/GetProducts.cs
Path: src/Domain/Products/CreateProduct.cs
Path: src/ViewModels/ProductsViewModel.cs
Path: src/Views/ProductsPage.xaml
Path:
```

### Question 7: Agent Preferences

```
Generate custom agents for project-specific patterns?
  [1] Yes - Generate agents for capabilities not in global library
  [2] No - Use only global agents

Enter number (default: 1):
```

**What Are Custom Agents?**

AI specialists tuned to YOUR specific patterns:
- `mycompany-domain-specialist` - Your domain patterns
- `mycompany-viewmodel-specialist` - Your MVVM approach
- `mycompany-testing-specialist` - Your test patterns

**When to Generate**:
- ✅ Have unique patterns (custom logging, security)
- ✅ Company-specific conventions
- ✅ Non-standard architectures
- ❌ Using standard patterns (global agents sufficient)

**Recommendation**:
- Choose **Yes (1)** for company templates
- Choose **No (2)** for learning/prototyping

### Question 8: Confirmation

```
------------------------------------------------------------
  Summary of Detected Patterns
------------------------------------------------------------

Template Name: mycompany-maui-template
Language: C# (net8.0)
Framework: .NET MAUI 8.0
Architecture: MVVM
Purpose: Enforce team standards

Detected Patterns:
  ✓ Domain operations (verb-based naming)
  ✓ Repository pattern
  ✓ ErrorOr error handling
  ✓ MVVM with CommunityToolkit
  ✓ Dependency injection

Detected Layers:
  ✓ Domain (business logic)
  ✓ Data (repositories)
  ✓ ViewModels (presentation logic)
  ✓ Views (UI)

Example Files Selected:
  1. src/Domain/Products/GetProducts.cs
  2. src/Domain/Products/CreateProduct.cs
  3. src/Domain/Orders/GetOrders.cs
  4. src/Data/Repositories/ProductRepository.cs
  5. src/ViewModels/ProductsViewModel.cs
  6. src/ViewModels/OrdersViewModel.cs
  7. src/Views/ProductsPage.xaml
  8. src/Views/ProductsPage.xaml.cs
  9. tests/Domain/GetProductsTests.cs
  10. tests/ViewModels/ProductsViewModelTests.cs

Confirm and proceed with generation? (Y/n):
```

**What to Check**:
- ✅ Language/framework correct?
- ✅ Architecture matches your design?
- ✅ Patterns captured accurately?
- ✅ Example files representative?

**If Something Wrong**:
- Enter `n` to cancel
- Fix codebase or naming
- Re-run command

**If Everything Looks Good**:
- Enter `Y` to proceed

---

## Phase 2: AI Analysis

Duration: 10-30 seconds

### What Happens

The AI analyzes your codebase to extract intelligent patterns.

```
✅ Q&A complete

============================================================
  Phase 2: AI Codebase Analysis
============================================================

🔍 Analyzing codebase...
```

### Step 1: File Collection

```
📂 Collecting files...
  ✓ Found 150 total files
  ✓ Filtered to 45 relevant files
  ✓ Selected 10 best examples

Example files:
  • GetProducts.cs (Domain operation - Query)
  • CreateProduct.cs (Domain operation - Command)
  • ProductRepository.cs (Data access)
  • ProductsViewModel.cs (MVVM presentation)
  • GetProductsTests.cs (Unit test example)
```

**What It Does**:
- Scans entire codebase
- Filters by language and patterns
- Selects diverse examples
- Prioritizes well-structured files

### Step 2: Directory Tree

```
🌳 Building directory structure...
  ✓ Mapped 15 directories
  ✓ Identified 4 layers
  ✓ Detected 3 feature areas
```

Creates structural map:
```
src/
├── Domain/              (Business logic)
│   ├── Products/
│   └── Orders/
├── Data/                (Data access)
│   └── Repositories/
├── ViewModels/          (Presentation logic)
└── Views/               (UI)
```

### Step 3: AI Pattern Analysis

```
🤖 AI analyzing patterns...
  ✓ Architecture analysis complete
  ✓ Pattern detection complete
  ✓ Quality assessment complete
  ✓ Confidence score: 87%
```

**AI Analyzes**:

1. **Architecture**
   - Layer dependencies
   - Separation of concerns
   - Pattern consistency

2. **Naming Conventions**
   - Class naming patterns
   - Method naming patterns
   - File organization

3. **Error Handling**
   - ErrorOr usage
   - Exception patterns
   - Validation approaches

4. **Testing Patterns**
   - Test structure
   - Mocking strategies
   - Assertion styles

5. **Quality Metrics**
   - SOLID compliance (0-100)
   - DRY compliance (0-100)
   - YAGNI compliance (0-100)

### Analysis Output

```
📊 Analysis Results:

Technology Stack:
  • Language: C# 8.0 (net8.0)
  • Framework: .NET MAUI 8.0.0
  • Testing: xUnit 2.6.0
  • DI: Microsoft.Extensions.DependencyInjection
  • Error Handling: ErrorOr 2.0.1

Architecture:
  • Style: MVVM
  • Patterns: Domain operations, Repository, DI
  • Layers: Domain → Data → ViewModels → Views
  • Dependency Flow: Inward (Clean Architecture style)

Naming Conventions Detected:
  • Domain: {Verb}{Entity} (e.g., GetProducts)
  • Repositories: I{Entity}Repository / {Entity}Repository
  • ViewModels: {Feature}ViewModel
  • Views: {Feature}Page
  • Tests: {ClassName}Tests

Quality Assessment:
  • SOLID Compliance: 85/100
  • DRY Compliance: 80/100
  • YAGNI Compliance: 90/100
  • Overall Quality: High
  • Confidence: 87%

Strengths:
  ✓ Consistent naming across all layers
  ✓ Clear separation of concerns
  ✓ Good error handling with ErrorOr
  ✓ Comprehensive test coverage
  ✓ Modern .NET patterns

Areas for Improvement:
  ⚠ Some duplicate validation logic
  ⚠ Minor SOLID violations in ViewModels
  ⚠ Could benefit from more abstractions

Confidence Score: 87%
  High confidence - patterns are consistent and well-established
```

---

## Phase 3: Template Generation

Duration: 5-15 seconds

### Component 1: Manifest Generation

```
============================================================
  Phase 3: Template Component Generation
============================================================

📝 Generating manifest.json...
```

**What Gets Generated**:

```json
{
  "schema_version": "1.0.0",
  "name": "mycompany-maui-template",
  "display_name": "MyCompany .NET MAUI Template",
  "description": "Company-standard MAUI template with MVVM, Domain pattern, and ErrorOr",
  "version": "1.0.0",
  "author": "Your Name",
  "language": "C#",
  "language_version": "net8.0",
  "frameworks": [
    {
      "name": ".NET MAUI",
      "version": "8.0.0",
      "purpose": "ui"
    },
    {
      "name": "xUnit",
      "version": "2.6.0",
      "purpose": "testing"
    }
  ],
  "architecture": "MVVM",
  "patterns": [
    "Domain operations (verb-based)",
    "Repository pattern",
    "ErrorOr error handling",
    "Dependency injection"
  ],
  "layers": [
    {
      "name": "Domain",
      "purpose": "Business logic",
      "patterns": ["Domain operations", "ErrorOr"]
    },
    {
      "name": "Data",
      "purpose": "Data access",
      "patterns": ["Repository pattern"]
    },
    {
      "name": "ViewModels",
      "purpose": "Presentation logic",
      "patterns": ["MVVM", "CommunityToolkit.Mvvm"]
    },
    {
      "name": "Views",
      "purpose": "User interface",
      "patterns": ["XAML", "Code-behind"]
    }
  ],
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Root project name",
      "required": true,
      "pattern": "^[A-Za-z][A-Za-z0-9_]*$",
      "example": "ShoppingApp"
    },
    "Entity": {
      "name": "{{EntityName}}",
      "description": "Entity/model name (singular)",
      "required": true,
      "pattern": "^[A-Z][A-Za-z0-9]*$",
      "example": "Product"
    }
  },
  "tags": ["csharp", "maui", "mvvm", "mobile", "company-standard"],
  "category": "mobile",
  "complexity": 6,
  "created_at": "2025-11-06T10:30:00Z",
  "source_project": "/Users/me/projects/my-maui-app",
  "confidence_score": 87
}
```

Output:
```
  ✓ Template metadata complete
  ✓ 8 placeholders defined
  ✓ 4 layers documented
  ✓ 4 patterns captured
  ✓ Complexity score: 6/10
```

### Component 2: Settings Generation

```
⚙️  Generating settings.json...
```

**What Gets Generated**:

```json
{
  "schema_version": "1.0.0",
  "naming_conventions": {
    "domain_operations": {
      "pattern": "{{Verb}}{{EntityNamePlural}}",
      "case_style": "PascalCase",
      "examples": ["GetProducts", "CreateProduct", "UpdateOrder"]
    },
    "repositories": {
      "interface_pattern": "I{{EntityName}}Repository",
      "implementation_pattern": "{{EntityName}}Repository",
      "case_style": "PascalCase"
    },
    "viewmodels": {
      "pattern": "{{FeatureName}}ViewModel",
      "case_style": "PascalCase"
    },
    "views": {
      "pattern": "{{FeatureName}}Page",
      "case_style": "PascalCase"
    },
    "tests": {
      "pattern": "{{ClassName}}Tests",
      "case_style": "PascalCase"
    }
  },
  "prohibited_suffixes": [
    "UseCase",
    "Engine",
    "Handler",
    "Processor"
  ],
  "file_organization": {
    "by_layer": true,
    "by_feature": false,
    "test_location": "separate"
  },
  "layer_mappings": {
    "Domain": {
      "directory": "src/Domain",
      "namespace_pattern": "{{ProjectName}}.Domain.{{SubPath}}",
      "file_patterns": ["*.cs", "!*Tests.cs"]
    },
    "Data": {
      "directory": "src/Data",
      "namespace_pattern": "{{ProjectName}}.Data.{{SubPath}}"
    },
    "ViewModels": {
      "directory": "src/ViewModels",
      "namespace_pattern": "{{ProjectName}}.ViewModels"
    },
    "Views": {
      "directory": "src/Views",
      "namespace_pattern": "{{ProjectName}}.Views"
    }
  },
  "code_style": {
    "indentation": "spaces",
    "indent_size": 4,
    "line_length": 120,
    "trailing_commas": false,
    "brace_style": "new_line"
  }
}
```

Output:
```
  ✓ 5 naming conventions captured
  ✓ 4 layer mappings defined
  ✓ Code style: C# defaults
  ✓ File organization rules set
```

### Component 3: CLAUDE.md Generation

```
📚 Generating CLAUDE.md...
```

Creates comprehensive AI guidance document with:

1. **Architecture Overview** (from analysis)
2. **Technology Stack** (detected frameworks)
3. **Project Structure** (directory tree)
4. **Naming Conventions** (with examples)
5. **Patterns & Best Practices** (from code analysis)
6. **Code Examples** (from your actual files)
7. **Quality Standards** (coverage, SOLID scores)
8. **Agent Usage Guidelines** (when to use which agent)

Output:
```
  ✓ Architecture section (15 lines)
  ✓ Technology stack (8 frameworks)
  ✓ Project structure visualization
  ✓ 5 naming convention examples
  ✓ 4 pattern descriptions
  ✓ 3 code examples (from your files)
  ✓ Quality standards (80% coverage, 85 SOLID)
  ✓ Agent guidelines

  Total: 487 lines
```

### Component 4: Template Files Generation

```
🎨 Generating template files...
```

For each example file, AI:
1. Reads original content
2. Identifies specific values (names, types, etc.)
3. Replaces with intelligent placeholders
4. Preserves structure and patterns
5. Validates template quality

**Example Transformation**:

```csharp
// BEFORE (GetProducts.cs):
namespace MyApp.Domain.Products;

public class GetProducts
{
    private readonly IProductRepository _repository;

    public GetProducts(IProductRepository repository)
    {
        _repository = repository;
    }

    public async Task<ErrorOr<List<Product>>> ExecuteAsync()
    {
        return await _repository.GetAllAsync();
    }
}

// AFTER (GetEntity.cs.template):
namespace {{ProjectName}}.Domain.{{EntityNamePlural}};

public class {{Verb}}{{EntityNamePlural}}
{
    private readonly I{{EntityName}}Repository _repository;

    public {{Verb}}{{EntityNamePlural}}(I{{EntityName}}Repository repository)
    {
        _repository = repository;
    }

    public async Task<ErrorOr<List<{{EntityName}}>>> ExecuteAsync()
    {
        return await _repository.GetAllAsync();
    }
}
```

Output:
```
  Processing files:
  ✓ Domain/GetEntity.cs.template (from GetProducts.cs)
  ✓ Domain/CreateEntity.cs.template (from CreateProduct.cs)
  ✓ Data/EntityRepository.cs.template (from ProductRepository.cs)
  ✓ Data/IEntityRepository.cs.template (from IProductRepository.cs)
  ✓ ViewModels/EntityViewModel.cs.template (from ProductsViewModel.cs)
  ✓ Views/EntityPage.xaml.template (from ProductsPage.xaml)
  ✓ Views/EntityPage.xaml.cs.template (from ProductsPage.xaml.cs)
  ✓ Tests/Domain/GetEntityTests.cs.template (from GetProductsTests.cs)

  Total: 15 template files generated
  Quality score: 92/100 (High confidence placeholders)
```

### Component 5: Agent Generation

```
🤖 Determining agent needs...
  ✓ Analyzed capability requirements
  ✓ Compared against global agent library
  ✓ Identified 3 capability needs
  ✓ Found 2 gaps to fill

💡 Creating project-specific agents...
```

**Gap Analysis**:

```
Capabilities Needed:
  1. MVVM ViewModel patterns → Global: mvvm-specialist ✓
  2. Domain operations (verb-based) → Gap found! ✗
  3. ErrorOr error handling → Global: error-pattern-specialist ✓
  4. Repository pattern → Global: repository-specialist ✓
  5. Company logging standards → Gap found! ✗
```

**Agent Generation**:

```
  → Generating: mycompany-domain-specialist
    Based on: GetProducts.cs, CreateProduct.cs, UpdateOrder.cs
    Expertise: Verb-based domain operations with ErrorOr
    ✓ Created (confidence: 90%)

  → Generating: mycompany-logging-specialist
    Based on: Logger usage patterns across all layers
    Expertise: Company logging standards and practices
    ✓ Created (confidence: 85%)
```

Output:
```
  Total agents: 7
    • 5 from global library (reused)
    • 2 generated (project-specific)

  Global agents:
    • architectural-reviewer
    • test-verifier
    • code-reviewer
    • mvvm-specialist
    • error-pattern-specialist

  Generated agents:
    • mycompany-domain-specialist
    • mycompany-logging-specialist
```

---

## Phase 4: Review & Test

### Final Output Summary

```
============================================================
  Template Package Complete
============================================================

✅ Template saved successfully!

Location: installer/local/templates/mycompany-maui-template/

Package Contents:
  ├── manifest.json              (15.2 KB)
  ├── settings.json              (8.1 KB)
  ├── CLAUDE.md                  (42.7 KB)
  ├── templates/                 (15 files)
  │   ├── Domain/
  │   │   ├── GetEntity.cs.template
  │   │   ├── CreateEntity.cs.template
  │   │   └── UpdateEntity.cs.template
  │   ├── Data/
  │   │   ├── IEntityRepository.cs.template
  │   │   └── EntityRepository.cs.template
  │   ├── ViewModels/
  │   │   └── EntityViewModel.cs.template
  │   ├── Views/
  │   │   ├── EntityPage.xaml.template
  │   │   └── EntityPage.xaml.cs.template
  │   └── Tests/
  │       ├── Domain/GetEntityTests.cs.template
  │       └── ViewModels/EntityViewModelTests.cs.template
  └── agents/                    (2 files)
      ├── mycompany-domain-specialist.md
      └── mycompany-logging-specialist.md

Generation Statistics:
  • Analysis confidence: 87%
  • Files processed: 10
  • Templates generated: 15
  • Custom agents: 2
  • Total time: 48 seconds

Quality Metrics:
  • Placeholder accuracy: 92%
  • Pattern consistency: 95%
  • SOLID compliance: 85/100
  • Template completeness: 100%

Next Steps:
  1. Review template files
  2. Test with: taskwright init mycompany-maui-template
  3. Customize if needed
  4. Share with team
```

### Step 1: Review Generated Files

```bash
# Navigate to template
cd installer/local/templates/mycompany-maui-template/

# List contents
ls -la

# Review manifest
cat manifest.json | jq .

# Review settings
cat settings.json | jq .

# Review CLAUDE.md
less CLAUDE.md

# Check template files
ls -la templates/Domain/
cat templates/Domain/GetEntity.cs.template
```

### Step 2: Test Template

```bash
# Create test project
mkdir ~/test-template
cd ~/test-template

# Initialize with your template
taskwright init mycompany-maui-template

# Follow prompts to fill placeholders:
# ProjectName: TestApp
# EntityName: Product

# Verify generated structure
tree src/

# Expected output:
src/
├── Domain/
│   ├── Products/
│   │   ├── GetProducts.cs
│   │   ├── CreateProduct.cs
│   │   └── UpdateProduct.cs
├── Data/
│   └── Repositories/
│       ├── IProductRepository.cs
│       └── ProductRepository.cs
├── ViewModels/
│   └── ProductsViewModel.cs
└── Views/
    ├── ProductsPage.xaml
    └── ProductsPage.xaml.cs
```

### Step 3: Verify Generated Code

```bash
# Check a generated file
cat src/Domain/Products/GetProducts.cs
```

Expected:
```csharp
namespace TestApp.Domain.Products;

public class GetProducts
{
    private readonly IProductRepository _repository;

    public GetProducts(IProductRepository repository)
    {
        _repository = repository;
    }

    public async Task<ErrorOr<List<Product>>> ExecuteAsync()
    {
        return await _repository.GetAllAsync();
    }
}
```

✅ **Placeholders correctly replaced**
✅ **Structure preserved**
✅ **Patterns maintained**

### Step 4: Build & Test

```bash
# Build project
dotnet build

# Run tests
dotnet test

# Expected:
Build succeeded.
    0 Warning(s)
    0 Error(s)

Test run successful.
```

---

## Phase 5: Customization

### When to Customize

Customize your generated template when you need to:
- Add company-specific patterns
- Include proprietary libraries
- Adjust naming conventions
- Add custom quality gates
- Extend agent capabilities

### Customization Areas

#### 1. Add Company Libraries

Edit `manifest.json`:
```json
{
  "prerequisites": {
    "packages": [
      "ErrorOr (2.0+)",
      "CommunityToolkit.Mvvm",
      "MyCompany.Logging (2.1.0)",        // Add this
      "MyCompany.Security (3.0.0)"        // Add this
    ]
  }
}
```

#### 2. Customize Templates

Edit template files to include company patterns:

```csharp
// templates/Domain/GetEntity.cs.template
using MyCompany.Logging;              // Add company using
using MyCompany.Security;

namespace {{ProjectName}}.Domain.{{EntityNamePlural}};

[RequirePermission("{{EntityName}}.Read")]  // Add company security
public class {{Verb}}{{EntityNamePlural}}
{
    private readonly ICompanyLogger<{{Verb}}{{EntityNamePlural}}> _logger;  // Company logger
    private readonly I{{EntityName}}Repository _repository;

    public {{Verb}}{{EntityNamePlural}}(
        ICompanyLogger<{{Verb}}{{EntityNamePlural}}> logger,
        I{{EntityName}}Repository repository)
    {
        _logger = logger;  // Company logging
        _repository = repository;
    }

    public async Task<ErrorOr<List<{{EntityName}}>>> ExecuteAsync()
    {
        using var _ = _logger.BeginScope("{{Verb}}{{EntityNamePlural}}");
        _logger.LogInformation("Starting execution");

        var result = await _repository.GetAllAsync();

        _logger.LogInformation("Execution complete");
        return result;
    }
}
```

#### 3. Update CLAUDE.md

Add company-specific guidance:

```markdown
## Company Standards

### Logging
All operations MUST use `ICompanyLogger<T>`:
- Begin scope at method start
- Log info at start and completion
- Log warnings for errors
- Log exceptions with full context

### Security
All domain operations accessing sensitive data MUST:
- Use `[RequirePermission]` attribute
- Check permissions before execution
- Log security events
- Handle authorization failures gracefully
```

#### 4. Customize Agents

Edit generated agent files:

```markdown
<!-- agents/mycompany-domain-specialist.md -->

## Company Standards

### Required Packages
- MyCompany.Logging 2.1.0+
- MyCompany.Security 3.0.0+
- ErrorOr 2.0+

### Mandatory Patterns
1. **Logging**: Use ICompanyLogger<T> with scopes
2. **Security**: Apply [RequirePermission] for sensitive ops
3. **Error Handling**: Always return ErrorOr<T>
4. **Naming**: {Verb}{EntityPlural} (e.g., GetProducts)

### Code Template
```csharp
[RequirePermission("{{Entity}}.{{Action}}")]
public class {{Verb}}{{EntityPlural}}
{
    private readonly ICompanyLogger<{{Verb}}{{EntityPlural}}> _logger;

    public async Task<ErrorOr<{{ReturnType}}>> ExecuteAsync()
    {
        using var _ = _logger.BeginScope("{{Verb}}{{EntityPlural}}");
        // ... implementation
    }
}
```
```

---

## Real-World Examples

### Example 1: E-Commerce Mobile App

**Scenario**: Extract template from production shopping app.

**Input Codebase**:
```
ShoppingApp/
├── Domain/
│   ├── Products/
│   │   ├── GetProducts.cs
│   │   ├── GetProductById.cs
│   │   ├── SearchProducts.cs
│   │   └── CreateProduct.cs
│   ├── Orders/
│   │   ├── GetOrders.cs
│   │   ├── CreateOrder.cs
│   │   └── CancelOrder.cs
│   └── Cart/
│       ├── GetCart.cs
│       ├── AddToCart.cs
│       └── RemoveFromCart.cs
├── Data/
│   └── Repositories/
│       ├── ProductRepository.cs
│       ├── OrderRepository.cs
│       └── CartRepository.cs
├── ViewModels/
│   ├── ProductsViewModel.cs
│   ├── OrdersViewModel.cs
│   └── CartViewModel.cs
└── Views/
    ├── ProductsPage.xaml
    ├── OrdersPage.xaml
    └── CartPage.xaml
```

**Command**:
```bash
cd ~/projects/ShoppingApp
/template-create
```

**Q&A Responses**:
- Codebase: Current directory
- Name: ecommerce-maui-template
- Language: C#
- Purpose: Production-ready scaffold
- Architecture: MVVM + Domain pattern
- Examples: Auto-select
- Agents: Yes, generate custom

**Generated Template**:
```
ecommerce-maui-template/
├── manifest.json
│   - Patterns: Domain ops, Repository, MVVM, Cart management
│   - Complexity: 7/10
├── settings.json
│   - Naming: {Verb}{EntityPlural}
│   - Layers: Domain, Data, ViewModels, Views
├── CLAUDE.md
│   - E-commerce patterns
│   - Cart state management
│   - Order processing flow
└── templates/
    ├── Domain/
    │   ├── GetEntity.cs.template
    │   ├── CreateEntity.cs.template
    │   └── UpdateEntity.cs.template
    ├── Data/EntityRepository.cs.template
    ├── ViewModels/EntityViewModel.cs.template
    └── Views/EntityPage.xaml.template
```

**Reusability**: Can generate products, orders, cart, customers, payments, etc.

### Example 2: Healthcare API

**Scenario**: Extract template from HIPAA-compliant FastAPI service.

**Input Codebase**:
```
HealthcareAPI/
├── domain/
│   ├── patients/
│   │   ├── get_patients.py
│   │   ├── create_patient.py
│   │   └── update_patient.py
│   └── appointments/
│       ├── get_appointments.py
│       └── schedule_appointment.py
├── infrastructure/
│   ├── repositories/
│   │   ├── patient_repository.py
│   │   └── appointment_repository.py
│   └── security/
│       ├── authorization.py
│       └── audit_logger.py
├── api/
│   └── endpoints/
│       ├── patients.py
│       └── appointments.py
└── tests/
    ├── domain/
    └── api/
```

**Generated Template Highlights**:
- **Security**: HIPAA compliance patterns
- **Audit Logging**: Every operation logged
- **Error Handling**: Result types with detailed errors
- **Testing**: Security-focused test patterns

### Example 3: Internal Tool Migration

**Scenario**: Standardize 10 internal tools to consistent pattern.

**Approach**:
1. Pick best example tool
2. Run `/template-create` on it
3. Review and enhance template
4. Apply to other 9 tools
5. Iterate based on learnings

**Benefits**:
- Consistent architecture across tools
- Easier onboarding (same patterns)
- Simplified maintenance
- Knowledge sharing

---

## Tips & Best Practices

### Before Running

1. **Clean Up Codebase**
   ```bash
   # Remove experimental code
   git clean -fdx

   # Delete unused files
   find . -name "*.bak" -delete
   find . -name "*.tmp" -delete

   # Fix inconsistent naming
   # (manual review required)
   ```

2. **Verify Consistency**
   ```bash
   # Check naming patterns
   find src/Domain -name "*.cs" | head -10

   # Should be consistent:
   # ✓ GetProducts.cs, CreateProduct.cs, UpdateOrder.cs
   # ✗ ProductGetter.cs, ProductCreationService.cs
   ```

3. **Document Patterns**
   ```bash
   # Create README if missing
   cat > README.md <<EOF
   # MyApp Architecture

   ## Patterns
   - Domain: Verb-based operations
   - Repository: Interface + Implementation
   - MVVM: CommunityToolkit
   - Errors: ErrorOr pattern
   EOF
   ```

### During Q&A

1. **Use Descriptive Names**
   - ✅ `mycompany-maui-mvvm-appshell`
   - ❌ `template1`

2. **Choose Correct Purpose**
   - Team template? → "Enforce team standards"
   - Quick prototype? → "Prototype/experiment"

3. **Let AI Auto-Select**
   - Use option 3 (Auto-select) for example files
   - AI picks diverse, representative samples

4. **Generate Custom Agents**
   - Always say "Yes" for company templates
   - Captures your unique patterns

### After Generation

1. **Review Everything**
   ```bash
   # Check manifest
   cat manifest.json | jq .

   # Verify settings
   cat settings.json | jq .naming_conventions

   # Read CLAUDE.md
   less CLAUDE.md

   # Inspect templates
   ls templates/
   cat templates/Domain/GetEntity.cs.template
   ```

2. **Test Thoroughly**
   ```bash
   # Test in clean directory
   mkdir /tmp/test-template
   cd /tmp/test-template
   taskwright init mycompany-template

   # Verify builds
   dotnet build
   dotnet test
   ```

3. **Iterate**
   - Found issues? Fix source codebase
   - Re-run `/template-create`
   - Compare outputs
   - Keep improving

### Common Mistakes to Avoid

1. ❌ **Running on Inconsistent Code**
   - AI extracts patterns - inconsistency confuses it
   - Fix codebase first

2. ❌ **Too Few Examples**
   - Need 5-10 examples minimum
   - More examples = better patterns

3. ❌ **Mixing Architectures**
   - Don't mix MVVM + MVC in same codebase
   - Separate templates for different patterns

4. ❌ **Skipping Review**
   - Always review generated templates
   - AI is good but not perfect

5. ❌ **Not Testing**
   - Test before sharing with team
   - Catch issues early

### Optimization Tips

1. **Faster Analysis**
   ```bash
   # Use --skip-qa for repeated runs
   /template-create --skip-qa --output /tmp/test

   # Limit files analyzed
   /template-create --max-templates 10
   ```

2. **Debug Issues**
   ```bash
   # Save analysis output
   /template-create --save-analysis

   # Check analysis.json
   cat .template-analysis.json | jq .
   ```

3. **Dry Run**
   ```bash
   # Preview without saving
   /template-create --dry-run
   ```

---

## Next Steps

### Immediate Actions

1. ✅ Run `/template-create` on your best codebase
2. ✅ Review generated template
3. ✅ Test with sample project
4. ✅ Customize if needed
5. ✅ Share with team

### Learn More

- **Command Reference**: [template-create.md](../../installer/global/commands/template-create.md)
- **Greenfield Guide**: [template-init-walkthrough.md](./template-init-walkthrough.md)
- **Q&A Details**: [template-qa-guide.md](./template-qa-guide.md)
- **Troubleshooting**: [template-troubleshooting.md](./template-troubleshooting.md)
- **Customization**: [creating-local-templates.md](./creating-local-templates.md)

### Get Help

- Report issues: [GitHub Issues](https://github.com/taskwright/taskwright/issues)
- Ask questions: [Discussions](https://github.com/taskwright/taskwright/discussions)
- Team Slack: #taskwright-templates

---

**Created**: 2025-11-06
**Task**: TASK-014
**Version**: 1.0.0
**Maintained By**: Platform Team
