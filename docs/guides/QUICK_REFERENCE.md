# Taskwright Quick Reference Guide

## Quick Start Commands

### Installation
```bash
# Install globally (one-time)
curl -sSL https://raw.githubusercontent.com/appmilla/taskwright/main/installer/scripts/install.sh | bash

# Initialize projects with stack templates
taskwright init react                  # React + TypeScript + Vite + Playwright
taskwright init python                 # Python + FastAPI + pytest + LangGraph
taskwright init dotnet-microservice    # .NET microservices + FastEndpoints
taskwright init maui-appshell         # .NET MAUI + AppShell + MVVM
taskwright init maui-navigationpage   # .NET MAUI + NavigationPage + MVVM
taskwright init typescript-api        # NestJS TypeScript backend API
taskwright init default               # Language-agnostic template
```

## Core Workflow Commands

### Task Management
```bash
# Create tasks
/task-create "Task title"
/task-create "Task title" priority:high
/task-create "Task title" tags:feature,api

# Work on tasks (automatic planning + implementation + testing)
/task-work TASK-XXX
/task-work TASK-XXX --mode=tdd
/task-work TASK-XXX --design-only
/task-work TASK-XXX --implement-only

# Complete tasks
/task-complete TASK-XXX

# View task status
/task-status
/task-status TASK-XXX

# Refine implementation
/task-refine TASK-XXX
```

## Command Parameters

### /task-create Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| title | string | Task description (required) | "Add login feature" |
| priority | enum | Task priority | priority:high, priority:medium, priority:low |
| tags | list | Task categorization | tags:api,security |

### /task-work Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| task_id | string | Task identifier (required) | TASK-001 |
| --mode | enum | Development mode | --mode=standard, --mode=tdd |
| --design-only | flag | Planning phase only | --design-only |
| --implement-only | flag | Implementation phase only | --implement-only |

### /task-complete Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| task_id | string | Task identifier (required) | TASK-001 |

### /task-status Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| task_id | string | Optional task identifier | TASK-001 |

## Available Templates

### React Stack
**Production Patterns Included:**
- Error boundaries for resilient error handling
- SSE hooks for real-time streaming
- Performance optimization (memoization, debouncing)
- Accessibility patterns (WCAG 2.1 AA)
- Advanced testing (visual regression, performance)
- Security patterns (input sanitization)

**Key Files:**
- `CLAUDE.md` - Complete development context
- `PATTERNS.md` - Production-tested patterns
- Templates for hooks, components, services

**Setup:**
```bash
taskwright init react
cd my-project
npm install
npm run dev
```

### Python Stack
**Production Patterns Included:**
- Surgical coding philosophy (minimal changes)
- Factory pattern throughout
- LangGraph workflow orchestration
- SSE streaming with completion events
- MCP server integration
- Regression test markers

**Key Files:**
- `CLAUDE.md` - Surgical coding prompts
- Templates for endpoints, agents, workflows
- Comprehensive test templates

**Setup:**
```bash
taskwright init python
cd my-project
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt
uvicorn main:app --reload
```

### .NET Microservice Stack
**Production Patterns Included:**
- FastEndpoints with REPR pattern
- Either monad for functional error handling
- OpenTelemetry observability
- Domain-driven design structure
- Health check endpoints
- Integration testing focus

**Project Structure:**
```
ServiceName.API/
├── Domain/         # Entities and errors
├── Endpoints/      # FastEndpoints
├── Services/       # Business logic
├── Infrastructure/ # Cross-cutting concerns
└── Validators/     # FluentValidation

ServiceName.Tests/
├── Unit/          # Service tests
└── Integration/   # API tests
```

**Setup:**
```bash
taskwright init dotnet-microservice
cd my-project
dotnet build
dotnet run
dotnet test
```

### .NET MAUI Stack
**Production Patterns Included:**
- MVVM with UseCase pattern
- Functional error handling (Either monad)
- Outside-In TDD approach
- Cache-aside pattern
- Loading scope pattern
- Navigation service

**Project Structure:**
```
AppName/
├── Core/         # Models and interfaces
├── UseCases/     # Business logic
├── Services/     # Infrastructure
├── ViewModels/   # MVVM
├── Views/        # XAML pages
└── Tests/        # Integration tests
```

**Setup:**
```bash
taskwright init maui-appshell  # or maui-navigationpage
cd my-project
dotnet build
dotnet run --framework net8.0-android  # or net8.0-ios, net8.0-maccatalyst
dotnet test --filter Category=Integration
```

### TypeScript API Stack
**Production Patterns Included:**
- NestJS with modular architecture
- Result patterns for error handling
- Domain modeling with TypeScript
- Comprehensive testing with Jest
- OpenAPI documentation generation
- Dependency injection containers

**Project Structure:**
```
src/
├── modules/        # Feature modules
├── common/         # Shared utilities
├── database/       # Database configuration
├── auth/          # Authentication module
└── config/        # Application configuration

test/
├── unit/          # Unit tests
├── integration/   # API tests
└── e2e/          # End-to-end tests
```

**Setup:**
```bash
taskwright init typescript-api
cd my-project
npm install
npm run start:dev
npm run test
```

## Quality Gates

### All Stacks Include:
| Gate | Threshold | Enforcement |
|------|-----------|-------------|
| Code Coverage | ≥80% line | Required |
| Branch Coverage | ≥75% | Required |
| Test Pass Rate | 100% | Required |
| Compilation | 100% | Required |
| Architectural Review | ≥60/100 | Required |

### Stack-Specific Requirements:

**React:**
- Render time <100ms
- Accessibility score 100%
- Bundle size optimized

**Python:**
- Max 3 files per feature
- All endpoints use Pydantic
- SSE streams send completion

**.NET Microservice:**
- P95 response <200ms
- All operations return Either
- OpenTelemetry required

**.NET MAUI:**
- Page load <500ms
- ViewModels contain no logic
- Integration tests required

## Development Workflow

### Standard Development Flow
```bash
# 1. Create task
/task-create "Add user authentication" priority:high

# 2. Work on task (automatic phases)
/task-work TASK-001
# Phases:
#   Phase 1: Load Task Context
#   Phase 2: Implementation Planning
#   Phase 2.5B: Architectural Review
#   Phase 2.7: Complexity Evaluation
#   Phase 2.8: Human Checkpoint (if complex)
#   Phase 3: Implementation
#   Phase 4: Testing
#   Phase 4.5: Test Enforcement Loop
#   Phase 5: Code Review
#   Phase 5.5: Plan Audit

# 3. Complete task
/task-complete TASK-001
```

### Design-First Workflow (Complex Tasks)
```bash
# 1. Create complex task
/task-create "Refactor authentication system" priority:high

# 2. Design phase only
/task-work TASK-002 --design-only

# [Human reviews and approves plan]

# 3. Implementation phase
/task-work TASK-002 --implement-only

# 4. Complete
/task-complete TASK-002
```

### TDD Workflow
```bash
# 1. Create task requiring complex logic
/task-create "Calculate tax rates" priority:medium

# 2. Work with TDD mode
/task-work TASK-003 --mode=tdd
# Automatic Red → Green → Refactor cycle

# 3. Complete
/task-complete TASK-003
```

## Key Patterns by Stack

### React Patterns
```typescript
// Error Boundary
<ErrorBoundary fallback={<ErrorFallback />}>
  <Component />
</ErrorBoundary>

// SSE Hook
const { data, error, isConnected } = useSSE('/api/stream');

// Performance
const MemoizedComponent = memo(Component);
const debouncedSearch = useDebouncedCallback(search, 300);
```

### Python Patterns
```python
# Factory Pattern
def create_agent_factory(config: AgentConfig):
    return Agent(config)

# LangGraph Workflow
workflow = StateGraph(State)
workflow.add_node("process", process_node)
workflow.add_edge("process", "validate")

# SSE Streaming
async def stream_response():
    yield "data: Starting\n\n"
    # ... processing
    yield "event: done\ndata: {}\n\n"
```

### .NET Patterns
```csharp
// Either Monad
public async Task<Either<Error, Product>> GetProductAsync(Guid id)
{
    return await TryAsync(async () =>
    {
        var product = await _repository.GetByIdAsync(id);
        return product != null
            ? Right<Error, Product>(product)
            : Left<Error, Product>(new NotFoundError());
    })
    .IfFail(ex => Left<Error, Product>(new ServiceError(ex.Message)));
}

// FastEndpoint
public class GetProduct : Endpoint<GetRequest, GetResponse>
{
    public override void Configure()
    {
        Get("/api/products/{id}");
    }
}
```

### MAUI Patterns
```csharp
// UseCase
public async Task<Either<Error, Data>> ExecuteAsync(object? param)
{
    // Try cache first
    var cached = await _cache.GetAsync<Data>(key);
    if (cached != null) return cached;

    // Fetch from API
    return await _api.GetAsync<Data>(endpoint);
}

// ViewModel
[RelayCommand]
private async Task LoadData()
{
    using (var _ = new LoadingScope(this))
    {
        var result = await _useCase.ExecuteAsync();
        result.Match(
            Right: data => Data = data,
            Left: error => ShowError(error)
        );
    }
}
```

## Task States & Transitions

```
BACKLOG
   ├─ (task-work) ──────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                            ↓              ↓
   │                        BLOCKED        BLOCKED
   │
   └─ (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (task-work --implement-only) ─→ IN_PROGRESS
```

**States:**
- **BACKLOG**: New task, not started
- **DESIGN_APPROVED**: Design approved (design-first workflow)
- **IN_PROGRESS**: Active development
- **IN_REVIEW**: All quality gates passed
- **BLOCKED**: Tests failed or quality gates not met
- **COMPLETED**: Finished and archived

## Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `taskwright: command not found` | Run `source ~/.bashrc` or `source ~/.zshrc` |
| NuGet package conflicts | Ensure all target .NET 8.0 |
| Either monad errors | Add `using static LanguageExt.Prelude;` |
| React SSE not closing | Ensure `event: done` is sent |
| Python tests not found | Check pytest.ini configuration |
| Tests failing | Auto-fix runs (up to 3 attempts) |
| Low coverage | Check uncovered lines in report |

## Documentation Links

- [Getting Started Guide](GETTING-STARTED.md) - 5-minute quickstart
- [Taskwright Workflow](taskwright-workflow.md) - Complete workflow guide
- [MCP Optimization Guide](mcp-optimization-guide.md) - Library docs integration
- [Template Selection](maui-template-selection.md) - MAUI template guide
- [Domain Layer Pattern](../patterns/domain-layer-pattern.md) - Verb-based operations

## Best Practices

### Universal
1. Always use the templates as starting points
2. Follow the quality gates strictly
3. Test from the outside in
4. Use factory patterns for consistency
5. Handle errors functionally, not with exceptions

### Stack-Specific
- **React**: Prioritize accessibility and performance
- **Python**: Keep changes surgical, reuse patterns
- **.NET Microservice**: Use Either monad everywhere
- **.NET MAUI**: Keep ViewModels thin, logic in UseCases

## Next Steps

1. Choose your stack and initialize a project
2. Review the stack's CLAUDE.md file
3. Start with `/task-create`
4. Follow the task-work workflow
5. Use quality gates to ensure standards

> **Need Formal Requirements?**
> RequireKit adds EARS notation, BDD scenarios, and epic/feature hierarchy.
> See: https://github.com/requirekit/require-kit

---

*This guide covers the enhanced Taskwright system with production-tested patterns from multiple successful projects.*
