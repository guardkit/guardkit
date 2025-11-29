# /template-create Command - Complete Walkthrough

**Purpose**: Step-by-step guide to extracting reusable templates from existing codebases (brownfield approach).

**Time to Complete**: 20-45 minutes (depending on codebase complexity)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: AI-Native Codebase Analysis](#phase-1-ai-native-codebase-analysis)
4. [Phase 2: Template Generation](#phase-2-template-generation)
5. [Phase 3: Review & Test](#phase-3-review--test)
6. [Phase 4: Customization](#phase-4-customization)
7. [Real-World Examples](#real-world-examples)
8. [Tips & Best Practices](#tips--best-practices)

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
# AI-native mode (default - AI analyzes codebase automatically)
/template-create

# Analyze specific path
/template-create --path /path/to/codebase

# Create for team distribution (requires install.sh)
/template-create --output-location repo

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

## Phase 1: AI-Native Codebase Analysis

Duration: ~10-30 seconds (fully automatic)

### Starting AI Analysis

```bash
cd /path/to/your/codebase
/template-create
```

Output:
```
============================================================
  Template Creation - AI-Native Analysis
============================================================

This will analyze your codebase and create a reusable template.
AI will automatically infer language, framework, and architecture.
Estimated time: 30-60 seconds

Starting AI analysis...
```

**What Happens (Automatically)**:

The AI analyzes your codebase directly without asking questions, inferring ALL metadata:

1. **Primary Language** - Detected from file extensions (.py, .ts, .cs, etc.) and config files (package.json, requirements.txt, *.csproj)
2. **Framework** - Detected from dependencies in config files
3. **Architecture Pattern** - Detected from folder structure (ViewModels/, Domain/, etc.)
4. **Testing Framework** - Detected from test files and dependencies
5. **Template Name** - Suggested from project directory name

### Example AI Analysis Output

```
🔍 Analyzing codebase...

Detected Configuration:
  • Language: C# (net8.0)
  • Framework: .NET MAUI 8.0
  • Architecture: MVVM
  • Testing: xUnit 2.6.0
  • Template Name: my-maui-app

Found Patterns:
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

Confidence: 87%

Proceeding to template generation...
```

**No User Input Required** - AI infers everything automatically!

---

## Phase 2: Template Generation

Duration: 5-15 seconds

### What Happens

Using the AI analysis from Phase 1, the system now generates all template components.

```
✅ AI analysis complete

============================================================
  Phase 2: Template Component Generation
============================================================

📝 Generating template files...
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

## Phase 3: Review & Test

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

## Phase 4: Customization

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
   # Limit files analyzed for faster processing
   /template-create --max-templates 10

   # Test with specific path
   /template-create --path /path/to/codebase --dry-run
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
