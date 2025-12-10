# /template-init Command - Complete Walkthrough

**Purpose**: Step-by-step guide to creating templates from scratch using AI-powered generation (greenfield approach).

**Time to Complete**: 15-30 minutes (including Q&A session)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Q&A Session](#phase-1-qa-session)
4. [Phase 2: AI Template Generation](#phase-2-ai-template-generation)
5. [Phase 3: Agent Setup](#phase-3-agent-setup)
6. [Phase 4: Review & Test](#phase-4-review--test)
7. [Real-World Examples](#real-world-examples)
8. [Tips & Best Practices](#tips--best-practices)

---

## Overview

### What is /template-init?

The `/template-init` command uses AI to generate complete project templates from scratch based on your technology preferences and architecture decisions. Unlike `/template-create` which extracts from existing code, this command designs templates using best practices.

### When to Use

Use `/template-init` when you:
- ✅ Don't have existing code to analyze
- ✅ Want to design ideal architecture
- ✅ Need best-practice recommendations
- ✅ Are learning new technology stacks
- ✅ Want AI-generated optimal patterns

### Input → Output

```
INPUT: Your preferences
  ├── Technology choices (language, framework)
  ├── Architecture decisions (MVVM, Clean, etc.)
  └── Project requirements (testing, patterns)

                ↓
           /template-init
                ↓

OUTPUT: AI-designed template
  ├── manifest.json (metadata)
  ├── settings.json (conventions)
  ├── CLAUDE.md (best practices)
  ├── templates/ (code files)
  └── agents/ (specialized AI)
```

### Command Usage

```bash
# Interactive mode (default)
/template-init

# Resume from saved session
/template-init --resume

# Use custom session file
/template-init --session-file /path/to/session.json

# Skip Q&A (use defaults)
/template-init --skip
```

---

## Prerequisites

### Required

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **Terminal with Interactive Support**
   - Can display prompts
   - Supports keyboard input

3. **Clear Vision** (Recommended)
   - Know what technology stack you want
   - Have architecture preferences
   - Understand your testing needs

### Preparation Checklist

Before running the command:

```bash
# 1. Research technology choices
# - Which language? (C#, Python, TypeScript, etc.)
# - Which framework? (MAUI, FastAPI, React, etc.)
# - Which architecture? (MVVM, Clean, Hexagonal, etc.)

# 2. Define project requirements
# - Testing strategy?
# - Error handling approach?
# - UI needs (if applicable)?

# 3. Optional: Gather documentation
# - Architecture diagrams
# - Style guides
# - Team standards

# 4. Allocate time
# - Q&A: 8-10 minutes
# - AI Generation: 30-60 seconds
# - Review: 5-10 minutes
```

---

## Phase 1: Q&A Session

Duration: ~8-10 minutes (42 questions across 10 sections)

### Starting the Session

```bash
/template-init
```

Output:
```
============================================================
  /template-init - Greenfield Template Creation
============================================================

This Q&A will guide you through creating a new project template.
The session covers 10 sections with ~42 questions.

Estimated time: 8-10 minutes
Press Ctrl+C at any time to save and resume later.

============================================================
  Phase 1: Q&A Session
============================================================
```

### Section 1: Template Identity (2 questions)

#### Question 1: Template Name

```
------------------------------------------------------------
  Section 1: Template Identity (1/10)
------------------------------------------------------------

What should this template be called?
  Validation: 3-50 chars, alphanumeric + hyphens/underscores
  Example: python-fastapi-clean-architecture

Enter value:
```

**Naming Best Practices:**
- Include technology: `python-fastapi-api`
- Include architecture: `dotnet-clean-architecture`
- Include purpose: `react-dashboard-template`
- Be specific: `mobile-maui-appshell-mvvm`

**Examples:**
- ✅ `python-fastapi-microservice`
- ✅ `typescript-nextjs-dashboard`
- ✅ `dotnet-maui-mvvm-mobile`
- ❌ `my-template` (too generic)
- ❌ `template-v2-final` (poor versioning)

#### Question 2: Template Purpose

```
What is the primary purpose of this template?
  [1] Start new projects quickly [DEFAULT]
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold

Enter number (default: 1):
```

**Purpose Impact:**

| Choice | Code Quality | Testing | Documentation | Best For |
|--------|--------------|---------|---------------|----------|
| **1. Quick Start** | Good | Basic | Minimal | Learning, prototyping |
| **2. Team Standards** | High | Comprehensive | Detailed | Company templates |
| **3. Prototype** | Flexible | Optional | Light | Experiments |
| **4. Production** | Highest | Complete | Extensive | Enterprise apps |

### Section 2: Technology Stack (3 questions)

#### Question 3: Primary Language

```
------------------------------------------------------------
  Section 2: Technology Stack (2/10)
------------------------------------------------------------

Primary language?
  [1] C#
  [2] TypeScript
  [3] Python
  [4] Java
  [5] Swift
  [6] Kotlin
  [7] Go
  [8] Rust
  [9] Other

Enter number:
```

**Decision Guide:**

```
Mobile App?
├─ iOS → Swift
├─ Android → Kotlin
├─ Cross-platform → C# (MAUI) or TypeScript (React Native)

Backend API?
├─ Microservices → Go, Python (FastAPI)
├─ Enterprise → C#, Java
├─ Rapid development → Python, TypeScript

Frontend?
├─ TypeScript (React, Next.js, Vue)
└─ Specialized frameworks as needed
```

#### Question 4: Framework Selection

```
Framework? (based on Python selection)
  [1] FastAPI (modern async API framework)
  [2] Django (full-featured web framework)
  [3] Flask (micro web framework)
  [4] Other

Enter number:
```

**Framework appears based on language:**
- **C#**: ASP.NET Core, .NET MAUI, Blazor
- **TypeScript**: React, Next.js, NestJS, Angular
- **Python**: FastAPI, Django, Flask
- **Java**: Spring Boot, Quarkus, Micronaut
- **Go**: Gin, Echo, Fiber

#### Question 5: Framework Version

```
Framework version?
  [1] Latest (FastAPI 0.104+) [DEFAULT]
  [2] LTS (Long Term Support)
  [3] Specific version

Enter number (default: 1):
```

**Recommendation:**
- **Latest**: For new projects, modern features
- **LTS**: For enterprise, stability-focused
- **Specific**: When matching existing infrastructure

### Section 3: Architecture Pattern (2 questions)

#### Question 6: Primary Architecture

```
------------------------------------------------------------
  Section 3: Architecture Pattern (3/10)
------------------------------------------------------------

Primary architecture pattern?
  [1] MVVM (Model-View-ViewModel)
  [2] Clean Architecture
  [3] Hexagonal (Ports & Adapters)
  [4] Layered Architecture
  [5] MVC (Model-View-Controller)
  [6] Vertical Slice Architecture
  [7] Simple (no formal architecture)
  [8] Other

Enter number:
```

**Architecture Decision Matrix:**

| Type | Best For | Complexity | Testability | Separation |
|------|----------|------------|-------------|------------|
| **MVVM** | UI apps (WPF, MAUI, Xamarin) | Medium | High | Excellent |
| **Clean** | Enterprise, complex domains | High | Highest | Maximum |
| **Hexagonal** | Domain-driven, microservices | High | Highest | Excellent |
| **Layered** | Traditional apps, proven pattern | Low | Good | Good |
| **MVC** | Web apps, familiar pattern | Low | Good | Moderate |
| **Vertical Slice** | Feature-focused, microservices | Medium | High | Feature-based |
| **Simple** | Scripts, tools, small apps | Minimal | Basic | Minimal |

#### Question 7: Domain Modeling Approach

```
Domain modeling approach?
  [1] Rich domain models (behavior + data)
  [2] Anemic domain models (data only)
  [3] Functional approach (immutable data)
  [4] Data-centric (database-first)

Enter number:
```

**Approach Comparison:**

| Approach | Logic Location | Complexity | Best For |
|----------|---------------|------------|----------|
| **Rich** | In domain models | High | Complex business logic |
| **Anemic** | In services | Low | CRUD apps, simple logic |
| **Functional** | Pure functions | Medium | Stateless operations |
| **Data-centric** | Stored procedures | Low | Database-heavy apps |

### Section 4: Project Structure (2 questions)

#### Question 8: Layer Organization

```
------------------------------------------------------------
  Section 4: Project Structure (4/10)
------------------------------------------------------------

Layer organization?
  [1] Single project (everything in one)
  [2] By layer (Domain, Infrastructure, API)
  [3] By feature (vertical slices)
  [4] Hybrid (layers + features)

Enter number:
```

**Examples:**

**Option 1: Single Project**
```
src/
├── models/
├── services/
├── controllers/
└── main.py
```

**Option 2: By Layer**
```
src/
├── Domain/
├── Infrastructure/
├── API/
└── Tests/
```

**Option 3: By Feature**
```
src/
├── Products/
│   ├── domain.py
│   ├── repository.py
│   └── api.py
└── Orders/
    ├── domain.py
    ├── repository.py
    └── api.py
```

**Option 4: Hybrid**
```
src/
├── Domain/
│   ├── Products/
│   └── Orders/
├── Infrastructure/
│   ├── Products/
│   └── Orders/
└── API/
    ├── Products/
    └── Orders/
```

#### Question 9: Standard Folders

```
Standard folders to include? (select multiple)
  [1] src (source code)
  [2] tests (test files)
  [3] docs (documentation)
  [4] scripts (automation scripts)
  [5] .github (GitHub workflows)
  [6] docker (Docker configs)
  [7] All above

Enter numbers (comma-separated, e.g., 1,2,3):
```

**Recommendation**: Choose option **7 (All)** for production templates.

### Section 5: Testing Strategy (3 questions)

#### Question 10: Unit Testing Framework

```
------------------------------------------------------------
  Section 5: Testing Strategy (5/10)
------------------------------------------------------------

Unit testing framework?
  (Auto-selected based on Python)
  [1] pytest [RECOMMENDED]
  [2] unittest (built-in)
  [3] Other

Enter number (default: 1):
```

**Framework appears based on language:**
- **C#**: xUnit, NUnit, MSTest
- **TypeScript**: Jest, Vitest, Mocha
- **Python**: pytest, unittest
- **Java**: JUnit, TestNG

#### Question 11: Testing Scope

```
Testing scope (select multiple)?
  [1] Unit tests (fast, isolated)
  [2] Integration tests (component interaction)
  [3] End-to-end tests (full system)
  [4] Performance tests (load, stress)
  [5] Security tests (vulnerabilities)

Enter numbers (comma-separated):
```

**Recommendation:**
- **Minimum**: 1,2 (unit + integration)
- **Standard**: 1,2,3 (+ e2e)
- **Enterprise**: 1,2,3,4,5 (complete)

#### Question 12: Test Pattern Preference

```
Test pattern preference?
  [1] Arrange-Act-Assert (AAA)
  [2] Given-When-Then (BDD style)
  [3] No preference (flexible)

Enter number:
```

**Pattern Examples:**

```python
# AAA Pattern
def test_get_products():
    # Arrange
    repository = MockRepository()
    service = ProductService(repository)

    # Act
    result = service.get_products()

    # Assert
    assert result.success
    assert len(result.value) == 3

# Given-When-Then Pattern
def test_get_products():
    # Given a product repository with 3 products
    repository = MockRepository(products=[p1, p2, p3])
    service = ProductService(repository)

    # When getting all products
    result = service.get_products()

    # Then should return success with 3 products
    assert result.success
    assert len(result.value) == 3
```

### Section 6: Error Handling (2 questions)

#### Question 13: Error Handling Strategy

```
------------------------------------------------------------
  Section 6: Error Handling (6/10)
------------------------------------------------------------

Error handling strategy?
  [1] Result type pattern (Result<T, Error>)
  [2] Exception-based (try/catch)
  [3] Error codes (return codes)
  [4] Mixed approach (results + exceptions)
  [5] Minimal (basic error handling)

Enter number:
```

**Strategy Comparison:**

| Strategy | Explicitness | Type Safety | Performance | Best For |
|----------|--------------|-------------|-------------|----------|
| **Result type** | High | Excellent | Good | Functional, explicit errors |
| **Exceptions** | Medium | Good | Slower | Traditional OOP |
| **Error codes** | High | Poor | Fast | System programming |
| **Mixed** | Medium | Good | Good | Pragmatic approach |
| **Minimal** | Low | Poor | Fast | Prototypes only |

#### Question 14: Input Validation

```
Input validation approach?
  [1] FluentValidation (C#) / Pydantic (Python)
  [2] Data annotations / Decorators
  [3] Manual validation in code
  [4] Minimal validation

Enter number:
```

**For Python/FastAPI**: Pydantic is highly recommended (option 1)
**For C#/.NET**: FluentValidation for complex, DataAnnotations for simple

### Section 7: Dependency Management (2 questions)

#### Question 15: Dependency Injection

```
------------------------------------------------------------
  Section 7: Dependency Management (7/10)
------------------------------------------------------------

Dependency injection approach?
  [1] Built-in framework DI (FastAPI Depends)
  [2] Third-party container (dependency-injector)
  [3] Manual dependency injection
  [4] None (direct instantiation)

Enter number:
```

**Recommendation**: Use built-in framework DI when available (option 1).

#### Question 16: Configuration Approach

```
Configuration approach?
  [1] Environment variables + Settings class
  [2] JSON/YAML config files
  [3] Both (config files + env override)
  [4] Configuration service
  [5] Minimal configuration

Enter number:
```

**Best Practice**: Option 1 or 3 for 12-factor app compliance.

### Section 8: UI/Navigation (Conditional - 2 questions)

**Note**: Only shown if UI framework selected (MAUI, React, etc.)

#### Question 17: UI Architecture

```
------------------------------------------------------------
  Section 8: UI/Navigation (8/10)
------------------------------------------------------------

UI architecture pattern?
  [1] MVVM (Model-View-ViewModel)
  [2] MVC (Model-View-Controller)
  [3] Component-based (React style)
  [4] Code-behind (simple)

Enter number:
```

**Shown based on framework:**
- **MAUI/WPF**: MVVM recommended
- **React/Vue**: Component-based
- **ASP.NET**: MVC

#### Question 18: Navigation Pattern

```
Navigation approach?
  [1] Framework-recommended (e.g., Shell for MAUI)
  [2] Custom navigation service
  [3] Minimal navigation

Enter number:
```

### Section 9: Additional Patterns (Conditional - 3 questions)

**Note**: Questions adapt based on previous answers.

#### Question 19: Data Access Pattern

```
------------------------------------------------------------
  Section 9: Additional Patterns (9/10)
------------------------------------------------------------

Data access pattern?
  [1] Repository pattern
  [2] Direct ORM/database access
  [3] CQRS (Command Query Responsibility Segregation)
  [4] Event sourcing

Enter number:
```

#### Question 20: API Pattern

```
API pattern? (for backend services)
  [1] REST (traditional)
  [2] REPR (Request-Endpoint-Response)
  [3] Minimal APIs (.NET 6+)
  [4] GraphQL
  [5] gRPC

Enter number:
```

#### Question 21: State Management

```
State management? (for UI apps)
  [1] Framework-recommended
  [2] Redux/NgRx pattern
  [3] Minimal (local state only)

Enter number:
```

### Section 10: Documentation Input (Optional - 5 questions)

#### Question 22: Has Documentation?

```
------------------------------------------------------------
  Section 10: Documentation Input (10/10)
------------------------------------------------------------

Do you have existing documentation to guide template creation?
  [1] Yes
  [2] No

Enter number:
```

**If Yes, additional questions follow:**

#### Question 23: Documentation Input Method

```
How would you like to provide documentation?
  [1] File paths (local files)
  [2] Paste text directly
  [3] URLs (web documentation)
  [4] Mix of above

Enter number:
```

#### Question 24-26: Content Collection

Based on method selected, collect:
- File paths (with validation)
- Pasted text (multi-line input)
- URLs (with format validation)

#### Question 27: Documentation Usage

```
How should documentation guide template creation?
  [1] Strict adherence (follow exactly)
  [2] General guidance (inform decisions)
  [3] Naming conventions only
  [4] For reasoning/context only

Enter number:
```

### Q&A Completion

```
============================================================
  Q&A Session Summary
============================================================

Template Identity:
  • Name: python-fastapi-clean
  • Purpose: Production-ready scaffold

Technology Stack:
  • Language: Python 3.9+
  • Framework: FastAPI 0.104+
  • Version: Latest

Architecture:
  • Pattern: Clean Architecture
  • Domain: Rich domain models
  • Organization: By layer

Testing:
  • Framework: pytest
  • Scope: Unit, Integration, E2E
  • Pattern: Arrange-Act-Assert

Error Handling:
  • Strategy: Result type pattern
  • Validation: Pydantic models

Additional:
  • DI: FastAPI Depends
  • Config: Environment variables
  • Data: Repository pattern
  • API: REPR pattern

✅ Q&A complete! Proceeding to template generation...
```

---

## Phase 2: AI Template Generation

Duration: 30-60 seconds

### AI Processing

```
============================================================
  Phase 2: AI Template Generation
============================================================

🤖 Analyzing your technology choices...
  ✓ Language: Python 3.9+
  ✓ Framework: FastAPI 0.104+
  ✓ Architecture: Clean Architecture
  ✓ Patterns: Repository, REPR, Result types
```

### Component Generation

#### Step 1: Manifest Generation

```
📝 Generating manifest.json...
  ✓ Template metadata created
  ✓ Technology stack: Python + FastAPI
  ✓ Architecture: Clean Architecture
  ✓ 6 placeholders defined
  ✓ Complexity: 7/10
```

Generated content:
```json
{
  "name": "python-fastapi-clean",
  "language": "Python",
  "language_version": "3.9+",
  "frameworks": [
    {"name": "FastAPI", "version": "0.104+", "purpose": "api"},
    {"name": "pytest", "version": "7.0+", "purpose": "testing"},
    {"name": "Pydantic", "version": "2.0+", "purpose": "validation"}
  ],
  "architecture": "Clean Architecture",
  "patterns": [
    "Repository pattern",
    "REPR (Request-Endpoint-Response)",
    "Result type pattern",
    "Dependency injection"
  ],
  "layers": ["Domain", "Infrastructure", "API", "Tests"]
}
```

#### Step 2: Settings Generation

```
⚙️  Generating settings.json...
  ✓ Naming conventions: snake_case
  ✓ Layer structure: domain, infrastructure, api
  ✓ File organization: by layer
  ✓ Code style: PEP 8
```

Generated content:
```json
{
  "naming_conventions": {
    "modules": "snake_case",
    "classes": "PascalCase",
    "functions": "snake_case",
    "constants": "UPPER_SNAKE_CASE"
  },
  "layer_mappings": {
    "domain": {
      "directory": "src/domain",
      "namespace_pattern": "src.domain.{subpath}"
    },
    "infrastructure": {
      "directory": "src/infrastructure",
      "dependencies": ["domain"]
    },
    "api": {
      "directory": "src/api",
      "dependencies": ["domain", "infrastructure"]
    }
  }
}
```

#### Step 3: CLAUDE.md Generation

```
📚 Generating CLAUDE.md...
  ✓ Clean Architecture principles
  ✓ FastAPI best practices
  ✓ Testing strategy
  ✓ Code examples
  ✓ Quality standards
```

Content includes:
- Architecture overview
- Layer responsibilities
- FastAPI patterns
- Repository pattern usage
- Testing approach
- Code examples

#### Step 4: Code Templates Generation

```
🎨 Generating code templates...
  ✓ domain/entity.py.template
  ✓ domain/repository_interface.py.template
  ✓ infrastructure/repository_impl.py.template
  ✓ api/endpoint.py.template
  ✓ api/request.py.template
  ✓ api/response.py.template
  ✓ tests/test_domain.py.template
  ✓ tests/test_api.py.template

  Total: 12 template files
```

**Example Template** (domain/entity.py.template):
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class {{EntityName}}:
    """{{EntityName}} domain entity."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def validate(self) -> list[str]:
        """Validate entity state."""
        errors = []

        # Add validation logic here

        return errors

    @property
    def is_valid(self) -> bool:
        """Check if entity is valid."""
        return len(self.validate()) == 0
```

---

## Phase 3: Agent Setup

Duration: 5-15 seconds

```
============================================================
  Phase 3: Agent System
============================================================

🤖 Setting up agent system...
  ✓ Scanning global agents
  ✓ Analyzing capability needs
  ✓ Generating specialized agents
```

### Agent Selection

```
Global Agents (reused):
  ✓ architectural-reviewer
  ✓ test-verifier
  ✓ code-reviewer
  ✓ software-architect

Generated Agents:
  ✓ python-fastapi-specialist
  ✓ clean-architecture-specialist
  ✓ pytest-specialist

Total: 7 agents configured
```

---

## Phase 4: Review & Test

### Final Output

```
============================================================
  Template Creation Complete
============================================================

✅ Template saved to: installer/local/templates/python-fastapi-clean

📦 Package Contents:
  ├── manifest.json (12.3 KB)
  ├── settings.json (6.8 KB)
  ├── CLAUDE.md (38.5 KB)
  ├── templates/ (12 files)
  │   ├── domain/
  │   │   ├── entity.py.template
  │   │   └── repository_interface.py.template
  │   ├── infrastructure/
  │   │   └── repository_impl.py.template
  │   ├── api/
  │   │   ├── endpoint.py.template
  │   │   ├── request.py.template
  │   │   └── response.py.template
  │   └── tests/
  │       ├── test_domain.py.template
  │       └── test_api.py.template
  └── agents/ (3 files)
      ├── python-fastapi-specialist.md
      ├── clean-architecture-specialist.md
      └── pytest-specialist.md

💡 Next steps:
   1. Review template at: installer/local/templates/python-fastapi-clean/
   2. Customize if needed
   3. Test with: guardkit init python-fastapi-clean
```

### Testing the Template

```bash
# Create test project
mkdir ~/test-fastapi
cd ~/test-fastapi

# Initialize with template
guardkit init python-fastapi-clean

# Prompts will ask for:
# - ProjectName: ProductAPI
# - EntityName: Product

# Verify structure
tree src/

# Expected:
src/
├── domain/
│   ├── products/
│   │   ├── product.py
│   │   └── product_repository.py
├── infrastructure/
│   └── repositories/
│       └── product_repository_impl.py
├── api/
│   └── products/
│       ├── endpoint.py
│       ├── request.py
│       └── response.py
└── tests/
    ├── domain/
    │   └── test_product.py
    └── api/
        └── test_products_endpoint.py

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start API
uvicorn src.api.main:app --reload
```

---

## Real-World Examples

### Example 1: Python Microservice

**Q&A Selections:**
- Language: Python
- Framework: FastAPI
- Architecture: Clean Architecture
- Domain: Rich models
- Testing: pytest + integration
- Error: Result type pattern

**Generated Template Highlights:**
- Clean separation of concerns
- Repository pattern for data access
- REPR API pattern
- Comprehensive test structure
- Docker configuration
- GitHub Actions CI/CD

### Example 2: React Dashboard

**Q&A Selections:**
- Language: TypeScript
- Framework: Next.js 14
- Architecture: Component-based
- Testing: Jest + Playwright
- State: Redux Toolkit

**Generated Template Highlights:**
- App Router structure
- Server/Client components
- API routes
- Component library setup
- E2E test examples
- Deployment configuration

### Example 3: Mobile App

**Q&A Selections:**
- Language: C#
- Framework: .NET MAUI
- Architecture: MVVM
- UI: Shell navigation
- Testing: xUnit + UI tests

**Generated Template Highlights:**
- MVVM with CommunityToolkit
- Shell-based navigation
- Platform-specific code organization
- XAML styling templates
- Platform test runners

---

## Tips & Best Practices

### Before Q&A

1. **Research Your Stack**
   - Understand framework options
   - Know architecture patterns
   - Have testing strategy in mind

2. **Document Decisions**
   - Keep notes of answers
   - Record reasoning
   - Save for team reference

3. **Consider Team**
   - What's familiar to team?
   - What matches company standards?
   - What enables onboarding?

### During Q&A

1. **Be Thoughtful**
   - Take time on architecture decision
   - Choose production-appropriate options
   - Think about long-term maintenance

2. **Use Defaults When Unsure**
   - Defaults are typically best practices
   - Can customize after generation

3. **Save Progress**
   - Press Ctrl+C anytime to save
   - Resume with `--resume` flag

### After Generation

1. **Review Thoroughly**
   ```bash
   # Check all generated files
   cd installer/local/templates/your-template
   find . -type f -name "*.md" -o -name "*.json"

   # Read CLAUDE.md completely
   less CLAUDE.md

   # Inspect templates
   cat templates/domain/entity.py.template
   ```

2. **Test Immediately**
   - Generate sample project
   - Verify builds
   - Run tests
   - Check for issues

3. **Customize As Needed**
   - Add company standards
   - Include proprietary packages
   - Adjust naming conventions
   - Enhance agent guidance

### Session Resume

If interrupted:

```bash
# Session automatically saved to:
.template-init-session.json

# Resume with:
/template-init --resume

# Or specify file:
/template-init --session-file /path/to/session.json
```

### Common Mistakes to Avoid

1. ❌ **Rushing Through Q&A**
   - Take time for architecture decisions
   - Wrong choice = inappropriate template

2. ❌ **Choosing Unfamiliar Stack**
   - Pick technologies you/team understand
   - Don't experiment on production template

3. ❌ **Skipping Testing Options**
   - Always include comprehensive testing
   - Tests are crucial for quality

4. ❌ **Not Reviewing Output**
   - Always review before using
   - AI is good but verify quality

5. ❌ **Ignoring Customization**
   - Generated template is starting point
   - Customize for company standards

---

## Next Steps

### After Template Creation

1. **Review & Enhance**
   - Add company-specific patterns
   - Include proprietary libraries
   - Document team standards

2. **Test Thoroughly**
   - Generate multiple test projects
   - Verify different scenarios
   - Check edge cases

3. **Share with Team**
   - Commit to repository
   - Document usage
   - Train team members

4. **Iterate**
   - Gather feedback
   - Update based on usage
   - Version appropriately

### Learn More

- **Command Reference**: [template-init.md](../../installer/core/commands/template-init.md)
- **Q&A Details**: [template-qa-guide.md](./template-qa-guide.md)
- **Brownfield Approach**: [template-create-walkthrough.md](./template-create-walkthrough.md)
- **Troubleshooting**: [template-troubleshooting.md](./template-troubleshooting.md)
- **Customization**: [creating-local-templates.md](./creating-local-templates.md)

---

**Created**: 2025-11-06
**Task**: TASK-014
**Version**: 1.0.0
**Maintained By**: Platform Team
