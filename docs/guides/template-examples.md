# Template Commands - Practical Examples

**Purpose**: Real-world examples and use cases for `/template-create` and `/template-init` commands.

**Learn from examples**:
- **5 minutes**: Quick examples
- **15 minutes**: Detailed case studies
- **30 minutes**: Complete workflows

---

## Table of Contents

1. [Quick Examples](#quick-examples)
2. [Brownfield Examples](#brownfield-examples-template-create)
3. [Greenfield Examples](#greenfield-examples-template-init)
4. [Industry-Specific Examples](#industry-specific-examples)
5. [Team Scenarios](#team-scenarios)
6. [Migration Examples](#migration-examples)

---

## Quick Examples

### Example 1: Extract from Existing MAUI App (5 min)

**Scenario**: You have a working .NET MAUI app with MVVM pattern. Want to reuse for future projects.

```bash
cd ~/projects/ShoppingApp
/template-create
```

**Q&A Answers**:
```
Codebase: [1] Current directory
Name: company-maui-shopping
Language: [1] C#
Purpose: [2] Enforce team standards
Architecture: [1] MVVM
Examples: [3] Auto-select
Agents: [1] Yes
Confirm: Y
```

**Result**: Template with Products, Orders, Cart patterns ready to reuse.

### Example 2: Design Python API from Scratch (10 min)

**Scenario**: Starting new microservice project, want best practices.

```bash
/template-init
```

**Key Answers**:
```
Name: python-fastapi-microservice
Purpose: [4] Production-ready
Language: [3] Python
Framework: [1] FastAPI
Architecture: [2] Clean Architecture
Domain: [1] Rich domain models
Testing: [1] pytest
Scope: 1,2,3 (Unit, Integration, E2E)
Error: [1] Result type
Validation: [1] Pydantic
DI: [1] Built-in (Depends)
Data: [1] Repository pattern
API: [2] REPR
```

**Result**: Production-ready FastAPI template with Clean Architecture.

---

## Brownfield Examples (/template-create)

### Case Study 1: E-Commerce Mobile App

**Context**:
- Platform: .NET MAUI
- Architecture: MVVM + Domain operations
- Features: Products, Orders, Cart, Checkout
- Team size: 5 developers
- Goal: Standardize future e-commerce apps

**Codebase Structure**:
```
ShoppingApp/
├── Domain/
│   ├── Products/
│   │   ├── GetProducts.cs
│   │   ├── GetProductById.cs
│   │   ├── SearchProducts.cs
│   │   └── CreateProduct.cs (admin)
│   ├── Orders/
│   │   ├── GetOrders.cs
│   │   ├── CreateOrder.cs
│   │   └── CancelOrder.cs
│   ├── Cart/
│   │   ├── GetCart.cs
│   │   ├── AddToCart.cs
│   │   ├── RemoveFromCart.cs
│   │   └── ClearCart.cs
│   └── Checkout/
│       ├── CalculateTotal.cs
│       └── ProcessPayment.cs
├── Data/
│   └── Repositories/
│       ├── ProductRepository.cs
│       ├── OrderRepository.cs
│       └── CartRepository.cs
├── ViewModels/
│   ├── ProductsViewModel.cs
│   ├── ProductDetailViewModel.cs
│   ├── CartViewModel.cs
│   └── CheckoutViewModel.cs
└── Views/
    ├── ProductsPage.xaml
    ├── ProductDetailPage.xaml
    ├── CartPage.xaml
    └── CheckoutPage.xaml
```

**Command Execution**:
```bash
cd ~/projects/ShoppingApp
/template-create
```

**Q&A Session**:
```
============================================================
  Template Creation - Brownfield Q&A
============================================================

Codebase location: [1] Current directory

Template name: ecommerce-maui-template

Primary language: [1] C# (detected)

Template purpose: [2] Enforce team standards

Architecture: [1] MVVM (detected from ViewModels/)

Example files: [3] Auto-select best examples

Generate custom agents: [1] Yes

Summary:
  ✓ Language: C# (net8.0)
  ✓ Framework: .NET MAUI 8.0
  ✓ Architecture: MVVM + Domain
  ✓ Patterns: Domain ops, Repository, ErrorOr, MVVM
  ✓ Layers: Domain, Data, ViewModels, Views
  ✓ Files: 15 examples selected

Confirm: Y
```

**Generated Template**:
```
ecommerce-maui-template/
├── manifest.json
│   • Complexity: 7/10
│   • Patterns: Domain, Repository, MVVM, ErrorOr
│   • Layers: 4 layers
├── settings.json
│   • Naming: {Verb}{EntityPlural}
│   • Repositories: I{Entity}Repository
│   • ViewModels: {Feature}ViewModel
├── CLAUDE.md
│   • E-commerce patterns
│   • Cart state management
│   • Payment processing flows
└── templates/
    ├── Domain/
    │   ├── GetEntity.cs.template
    │   ├── CreateEntity.cs.template
    │   ├── UpdateEntity.cs.template
    │   ├── DeleteEntity.cs.template
    │   └── CartOperations/
    │       ├── AddToCart.cs.template
    │       └── RemoveFromCart.cs.template
    ├── Data/
    │   ├── IEntityRepository.cs.template
    │   └── EntityRepository.cs.template
    ├── ViewModels/
    │   ├── EntityListViewModel.cs.template
    │   ├── EntityDetailViewModel.cs.template
    │   └── CartViewModel.cs.template
    └── Views/
        ├── EntityListPage.xaml.template
        ├── EntityDetailPage.xaml.template
        └── CartPage.xaml.template
```

**Reusability**:
After creating template, used it for:
1. **FoodDeliveryApp**: Products → Restaurants, Orders → Deliveries
2. **BookstoreApp**: Products → Books, Cart → Reading list
3. **FashionApp**: Products → Clothing items, Orders → Purchases

**Time Saved**: 16 hours per new app (vs building from scratch).

### Case Study 2: Healthcare HIPAA-Compliant API

**Context**:
- Platform: Python + FastAPI
- Architecture: Clean Architecture
- Compliance: HIPAA
- Features: Patients, Appointments, Medical Records
- Security: Audit logging, encryption, access control
- Goal: Template for all healthcare APIs

**Codebase Structure**:
```
HealthcareAPI/
├── domain/
│   ├── patients/
│   │   ├── get_patients.py
│   │   ├── get_patient_by_id.py
│   │   ├── create_patient.py
│   │   ├── update_patient.py
│   │   └── delete_patient.py
│   ├── appointments/
│   │   ├── get_appointments.py
│   │   ├── schedule_appointment.py
│   │   └── cancel_appointment.py
│   └── medical_records/
│       ├── get_records.py
│       ├── add_record.py
│       └── get_record_history.py
├── infrastructure/
│   ├── repositories/
│   │   ├── patient_repository.py
│   │   ├── appointment_repository.py
│   │   └── record_repository.py
│   ├── security/
│   │   ├── authorization.py
│   │   ├── encryption.py
│   │   └── audit_logger.py
│   └── database/
│       └── connection.py
├── api/
│   └── endpoints/
│       ├── patients.py
│       ├── appointments.py
│       └── records.py
└── tests/
    ├── domain/
    ├── api/
    └── security/
```

**Special Requirements**:
- Every operation must log to audit trail
- PII must be encrypted at rest
- Role-based access control (RBAC)
- Data retention policies enforced

**Command Execution**:
```bash
cd ~/projects/HealthcareAPI
/template-create
```

**Key Q&A Answers**:
```
Name: healthcare-fastapi-hipaa
Purpose: [4] Production-ready (HIPAA compliance)
Architecture: [2] Clean Architecture
Examples: [2] Specific paths (to ensure security patterns included)
  Path: domain/patients/get_patients.py
  Path: infrastructure/security/authorization.py
  Path: infrastructure/security/audit_logger.py
  Path: infrastructure/security/encryption.py
  Path: api/endpoints/patients.py
  # ... more security-critical files
Agents: [1] Yes (generates HIPAA-compliance specialist)
```

**Generated Template Highlights**:
- **Security-First**: Authorization decorator on all endpoints
- **Audit Trail**: Every operation logged with WHO, WHAT, WHEN
- **Encryption**: PII fields automatically encrypted
- **RBAC**: Role checks in all domain operations
- **Testing**: Security tests included

**Template Usage**:
```bash
# Create new service: Labs Management
guardkit init healthcare-fastapi-hipaa

Placeholders:
  EntityName: Lab
  EntityNamePlural: Labs
```

**Generated Files Include**:
```python
# domain/labs/get_labs.py
from security.authorization import require_permission
from security.audit import audit_log

@require_permission("lab.read")
@audit_log(action="read_labs", resource="labs")
async def get_labs(user: User) -> Result[List[Lab], Error]:
    """Get labs with automatic audit logging and RBAC."""
    # Implementation includes:
    # - Permission check (via decorator)
    # - Audit trail (via decorator)
    # - PII encryption (in Lab model)
    # - Error handling
    pass
```

**Impact**:
- 100% HIPAA compliance from day one
- Zero security issues in 6 months
- 40 hours saved per new service
- Standardized audit logging across team

### Case Study 3: Internal Tools Standardization

**Context**:
- Company has 10 internal tools
- Built by different developers over 3 years
- Inconsistent patterns, styles, testing
- Goal: Create standard template, migrate all tools

**Approach**:
1. Pick best tool (most consistent, best tested)
2. Extract template
3. Apply to others
4. Iterate based on learnings

**Selected Tool**: Employee Directory (best patterns)

```bash
cd ~/company/tools/employee-directory
/template-create
```

**Template Name**: `company-internal-tool-standard`

**Generated Template Includes**:
- Company logging library
- Company auth system
- Company UI theme
- Standard error handling
- Standard testing setup
- Company CI/CD integration

**Migration Process**:

```bash
# For each tool:
cd ~/company/tools/project-tracker

# Create new project from template
mkdir ../project-tracker-new
cd ../project-tracker-new
guardkit init company-internal-tool-standard

# Migrate business logic
cp -r ../project-tracker/src/domain/* src/domain/
# Adapt to template structure

# Run tests
npm test

# Compare
diff -r ../project-tracker ../project-tracker-new
```

**Results After 6 Months**:
- All 10 tools standardized
- 80% code coverage (was 20%)
- Consistent UX across tools
- Onboarding time: 2 weeks → 3 days
- Bug rate: -60%

---

## Greenfield Examples (/template-init)

### Case Study 1: New Python Microservice

**Context**:
- Starting greenfield microservice
- Team familiar with Python, new to FastAPI
- Want best practices from start
- Need: API, database, testing, CI/CD

**Command Execution**:
```bash
/template-init
```

**Complete Q&A Session**:
```
============================================================
  Section 1: Template Identity
============================================================

Template name: payment-service-template

Purpose: [4] Production-ready scaffold

============================================================
  Section 2: Technology Stack
============================================================

Language: [3] Python

Framework: [1] FastAPI (Latest 0.104+)

Version: [1] Latest

============================================================
  Section 3: Architecture
============================================================

Architecture: [2] Clean Architecture

Domain modeling: [1] Rich domain models

============================================================
  Section 4: Project Structure
============================================================

Organization: [2] By layer (Domain, Infrastructure, API)

Standard folders: [7] All (src, tests, docs, scripts, .github, docker)

============================================================
  Section 5: Testing
============================================================

Testing framework: [1] pytest

Scope: 1,2,3 (Unit, Integration, E2E)

Pattern: [1] Arrange-Act-Assert

============================================================
  Section 6: Error Handling
============================================================

Strategy: [1] Result type pattern

Validation: [1] Pydantic models

============================================================
  Section 7: Dependencies
============================================================

DI: [1] Built-in (FastAPI Depends)

Configuration: [1] Environment variables + Pydantic Settings

============================================================
  Section 9: Additional Patterns
============================================================

Data access: [1] Repository pattern

API pattern: [2] REPR (Request-Endpoint-Response)

============================================================
  Section 10: Documentation
============================================================

Has documentation: [2] No

✅ Q&A Complete
```

**Generated Template**:
```
payment-service-template/
├── manifest.json
│   • Language: Python 3.11+
│   • Framework: FastAPI 0.104+
│   • Architecture: Clean Architecture
│   • Complexity: 6/10
├── settings.json
│   • Naming: snake_case modules, PascalCase classes
│   • Layers: domain, infrastructure, api, tests
│   • Code style: PEP 8, Black formatter
├── CLAUDE.md
│   • Clean Architecture principles
│   • FastAPI best practices
│   • REPR pattern explained
│   • Repository pattern usage
│   • Testing strategy
├── templates/
│   ├── domain/
│   │   ├── entity.py.template
│   │   ├── value_object.py.template
│   │   ├── repository_interface.py.template
│   │   └── domain_service.py.template
│   ├── infrastructure/
│   │   ├── repository_impl.py.template
│   │   ├── database.py.template
│   │   └── external_service.py.template
│   ├── api/
│   │   ├── endpoint.py.template
│   │   ├── request.py.template
│   │   ├── response.py.template
│   │   └── dependencies.py.template
│   ├── tests/
│   │   ├── unit/
│   │   │   └── test_domain.py.template
│   │   ├── integration/
│   │   │   └── test_repository.py.template
│   │   └── e2e/
│   │       └── test_api.py.template
│   ├── docker/
│   │   ├── Dockerfile.template
│   │   └── docker-compose.yml.template
│   └── github/
│       └── workflows/
│           └── ci.yml.template
└── agents/
    ├── python-fastapi-specialist.md
    ├── clean-architecture-specialist.md
    └── pytest-specialist.md
```

**Using Template**:
```bash
mkdir ~/projects/payment-service
cd ~/projects/payment-service
guardkit init payment-service-template

# Prompts:
ProjectName: PaymentService
EntityName: Payment
```

**Generated Structure**:
```
payment-service/
├── src/
│   ├── domain/
│   │   ├── payments/
│   │   │   ├── payment.py (Entity)
│   │   │   ├── payment_repository.py (Interface)
│   │   │   └── process_payment.py (Domain service)
│   ├── infrastructure/
│   │   ├── repositories/
│   │   │   └── payment_repository_impl.py
│   │   └── database/
│   │       └── connection.py
│   ├── api/
│   │   └── payments/
│   │       ├── endpoint.py
│   │       ├── request.py
│   │       └── response.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── requirements.txt
└── pyproject.toml
```

**Outcome**:
- Production-ready from day one
- 100% test coverage from start
- CI/CD pipeline included
- Clean Architecture enforced
- Team alignment on patterns
- Time to first deploy: 2 days (vs 2 weeks)

### Case Study 2: React Dashboard from Scratch

**Context**:
- Building admin dashboard for SaaS product
- TypeScript + React + Next.js
- Need: Auth, data tables, charts, forms
- Team: 3 frontend developers

**Key Q&A Answers**:
```
Name: saas-admin-dashboard
Purpose: [4] Production-ready
Language: [2] TypeScript
Framework: Next.js 14 (App Router)
Architecture: [3] Component-based
Organization: [3] By feature
Folders: [7] All
Testing framework: Vitest + React Testing Library
Scope: 1,2,3 (Unit, Component, E2E with Playwright)
UI architecture: [3] Component-based (React)
State: [2] Redux Toolkit
```

**Generated Template Highlights**:
- Next.js 14 App Router structure
- Server/Client components
- API routes for backend
- Component library (shadcn/ui)
- Dark mode support
- Authentication flow
- Data fetching patterns
- E2E tests with Playwright

**Reusability**:
Used template for:
1. Admin Dashboard (original)
2. Customer Portal
3. Analytics Dashboard
4. Internal Tools Portal

**Time Saved**: 80 hours setup time per dashboard.

---

## Industry-Specific Examples

### Finance: Trading Platform

**Requirements**:
- High performance (sub-millisecond latency)
- Audit compliance (SOX, Dodd-Frank)
- Real-time data processing
- Transaction safety

**Template Approach**:
```bash
/template-create
# Extract from existing trading app
# Include: Real-time data handling, transaction patterns, audit logging

Result:
- finance-trading-template
- Patterns: Event sourcing, CQRS, saga pattern
- Compliance: Every transaction logged, reproducible
- Performance: Optimized data structures, caching
```

### Healthcare: Patient Portal

**Requirements**:
- HIPAA compliance
- Patient consent management
- Medical records access
- Appointment scheduling

**Template Approach**:
```bash
/template-init
# Design with HIPAA from start
# Include: Encryption, audit, consent, access control

Result:
- healthcare-patient-portal
- Security: End-to-end encryption, MFA
- Compliance: Audit trail, data retention policies
- Testing: Security-focused tests included
```

### Education: Learning Management System

**Requirements**:
- Multi-tenant (school districts)
- Student/teacher/admin roles
- Content management
- Progress tracking

**Template Approach**:
```bash
/template-create
# Extract from successful LMS
# Include: Multi-tenancy, RBAC, content patterns

Result:
- education-lms-template
- Architecture: Multi-tenant by design
- Roles: Flexible RBAC system
- Content: Versioning, publishing workflow
```

---

## Team Scenarios

### Scenario 1: Onboarding New Developer

**Challenge**: New developer needs to contribute quickly.

**Solution with Template**:
```bash
# Day 1: New developer
git clone company-repo
guardkit init company-standard-template

# Fill project details
ProjectName: NewFeature
EntityName: Feature

# Generated project ready to code
# - Company patterns enforced
# - Tests included
# - CI/CD configured
# - Documentation present

# Developer productive: Day 1 vs Week 3
```

### Scenario 2: Multiple Teams, One Standard

**Challenge**: 5 teams, different projects, need consistency.

**Solution**:
```bash
# Platform team creates template
/template-create
# Extract from best team's project
# Enhance with company standards

# Share template
git commit -m "Add company-standard-template"

# All teams use
Team A: guardkit init company-standard-template
Team B: guardkit init company-standard-template
# ... etc

Result:
- Consistent code across teams
- Easy team transfers
- Shared knowledge base
- Unified CI/CD
```

### Scenario 3: Migrating Legacy Patterns

**Challenge**: Move from old patterns to new architecture.

**Solution**:
```bash
# Create template with new patterns
/template-init
# Design ideal architecture

# Migrate incrementally
# Each new feature uses new template
# Old code gradually refactored

# After 6 months:
# - 70% on new patterns
# - Team aligned on direction
# - Clear migration path
```

---

## Migration Examples

### Example 1: Monolith to Microservices

**Before**: Large monolithic application

**Strategy**:
1. Extract microservice template from monolith
2. Create new services with template
3. Gradually move features

**Commands**:
```bash
# Extract template from monolith's best module
cd ~/projects/monolith
/template-create --path src/modules/payments
# Name: microservice-template

# Create first microservice
mkdir ~/projects/payment-service
cd ~/projects/payment-service
guardkit init microservice-template

# Repeat for other services
```

**Result**: 12 microservices in 6 months, consistent patterns.

### Example 2: Framework Upgrade

**Before**: React 16 → React 18 + Next.js 14

**Strategy**:
1. Create new template with React 18
2. Migrate components incrementally
3. Run old and new in parallel

**Commands**:
```bash
# Create modern React template
/template-init
# Language: TypeScript
# Framework: Next.js 14
# Name: react18-nextjs14-template

# Create new app structure
mkdir ~/projects/app-v2
cd ~/projects/app-v2
guardkit init react18-nextjs14-template

# Migrate components one by one
# Test both versions
# Switch when ready
```

**Result**: Smooth migration, no big-bang, reduced risk.

---

## Quick Reference

### When to Use /template-create

✅ Have working code with clear patterns
✅ Want to preserve existing architecture
✅ Team familiar with current approach
✅ Proven patterns in production

### When to Use /template-init

✅ Starting fresh with no existing code
✅ Want industry best practices
✅ Learning new technology
✅ Designing ideal architecture

### Template Naming Examples

**Good Names**:
- `company-dotnet-webapi`
- `python-fastapi-microservice`
- `react-nextjs-dashboard`
- `mobile-maui-appshell`

**Bad Names**:
- `template1`
- `my-template-final-v2`
- `test-template`
- `template`

---

## Next Steps

### Try These Examples

1. **Quick Win**: Extract template from your best project
   ```bash
   cd ~/projects/your-best-project
   /template-create
   ```

2. **Design Ideal**: Create greenfield template for next project
   ```bash
   /template-init
   # Answer with ideal architecture
   ```

3. **Standardize Team**: Create company standard
   ```bash
   # Pick best project
   # Extract template
   # Share with team
   ```

### Learn More

- **Getting Started**: [template-commands-getting-started.md](./template-commands-getting-started.md)
- **Walkthroughs**: [template-create-walkthrough.md](./template-create-walkthrough.md), [template-init-walkthrough.md](./template-init-walkthrough.md)
- **Customization**: [creating-local-templates.md](./creating-local-templates.md)

---

**Created**: 2025-11-06
**Task**: TASK-014
**Version**: 1.0.0
**Maintained By**: Platform Team
