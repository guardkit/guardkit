# Template Migration Guide

**Version**: 2.0.0
**Date**: 2025-11-09
**Type**: Breaking Changes

---

## Overview

As part of GuardKit's template quality initiative, we have updated templates based on comprehensive audit findings (TASK-056). This guide helps users migrate from removed templates and understand the reinstated default template.

**Goal**: Focus on high-quality reference implementations while providing a language-agnostic option for unsupported stacks.

---

## Template Changes in v2.0

### Summary

| Template | Status | Score | Notes |
|----------|--------|-------|-------|
| dotnet-aspnetcontroller | ❌ Removed | 6.5/10 | Redundant with dotnet-fastendpoints |
| default | ✅ Reinstated | 8.0/10 | Improved as language-agnostic starter |

**Update (TASK-060A)**: The `default` template has been reinstated with significant quality improvements (6.0 → 8.0) and repositioned as a language-agnostic starter for Go, Rust, Ruby, PHP, and other unsupported stacks.

---

## Detailed Migration Paths

### From `dotnet-aspnetcontroller` → `dotnet-fastendpoints`

#### Why This Template Was Removed

**Audit Score**: 6.5/10 (Grade C)

**Issues**:
- Traditional ASP.NET Core MVC Controller pattern
- Redundant with `dotnet-fastendpoints` and `dotnet-minimalapi`
- Below the 8/10 quality threshold
- Modern alternatives (FastEndpoints, Minimal API) are preferred

#### Recommended Migration

**Use `dotnet-fastendpoints` template** - Modern .NET API with REPR pattern and vertical slices.

```bash
# Initialize new project with dotnet-fastendpoints
guardkit init dotnet-fastendpoints
```

#### Key Differences

| Feature | dotnet-aspnetcontroller | dotnet-fastendpoints |
|---------|------------------------|----------------------|
| Pattern | MVC Controllers | REPR (Request-Endpoint-Response) |
| Architecture | Horizontal layers | Vertical slices |
| Error Handling | Try-catch | ErrorOr functional pattern |
| Endpoint Definition | Controller classes | Individual endpoint classes |
| Validation | Data annotations | FluentValidation |
| Response Types | ActionResult | TypedResults |

#### Migration Steps

**1. Convert Controllers to Endpoints**

**Before (Controller)**:
```csharp
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet("{id}")]
    public async Task<ActionResult<UserDto>> GetUser(int id)
    {
        var user = await _service.GetUserAsync(id);
        if (user == null)
            return NotFound();
        return Ok(user);
    }
}
```

**After (FastEndpoints)**:
```csharp
public class GetUserEndpoint : Endpoint<GetUserRequest, UserResponse>
{
    public override void Configure()
    {
        Get("/api/users/{id}");
        AllowAnonymous();
    }

    public override async Task HandleAsync(GetUserRequest req, CancellationToken ct)
    {
        var result = await _service.GetUserAsync(req.Id);

        if (result.IsError)
        {
            await SendNotFoundAsync(ct);
            return;
        }

        await SendOkAsync(result.Value, ct);
    }
}
```

**2. Update Service Layer to Use ErrorOr**

```csharp
// Before
public async Task<UserDto?> GetUserAsync(int id)
{
    var user = await _repository.GetByIdAsync(id);
    return user != null ? MapToDto(user) : null;
}

// After
public async Task<ErrorOr<UserDto>> GetUserAsync(int id)
{
    var user = await _repository.GetByIdAsync(id);

    if (user is null)
        return Errors.User.NotFound;

    return MapToDto(user);
}
```

**3. Update Project Structure**

```
Before (Horizontal Layers):
- Controllers/
- Services/
- Repositories/
- DTOs/

After (Vertical Slices):
- Features/
  - Users/
    - GetUser/
      - GetUserEndpoint.cs
      - GetUserRequest.cs
      - GetUserResponse.cs
      - GetUserValidator.cs
    - CreateUser/
    - UpdateUser/
```

#### Resources

- [FastEndpoints Documentation](https://fast-endpoints.com/)
- [REPR Pattern Guide](docs/patterns/repr-pattern.md)
- [ErrorOr Pattern](docs/patterns/erroror-pattern.md)
- [Vertical Slice Architecture](docs/patterns/vertical-slice-architecture.md)

---

### Default Template - Reinstated and Improved

#### Status Update (TASK-060A)

**Previous Score**: 6.0/10 (Grade C) - Removed in initial v2.0 release
**Current Score**: 8.0/10 (Grade B) - **Reinstated** with quality improvements

**Improvements Made**:
- Clear guidance on when to use vs when NOT to use
- Comprehensive settings.json with documentation level system
- Detailed README.md with usage examples
- Repositioned as language-agnostic starter for unsupported stacks
- Strong emphasis on migration path to specialized templates

#### When to Use Default Template

**Use default template for**:
- **Unsupported Languages**: Go, Rust, Ruby, PHP, Kotlin, Swift, Elixir, Scala
- **Custom Stacks**: Unique technology combinations
- **Prototyping**: Exploring GuardKit before committing to a stack
- **Template Development**: Building custom templates with `/template-create`

**Do NOT use default for well-supported stacks** - use specialized templates instead.

#### Migration Recommendations

If you were previously advised to avoid the default template, consider these updated guidelines:

| Project Type | Recommended Template | Description |
|--------------|---------------------|-------------|
| **Unsupported Language** | `default` | **Go, Rust, Ruby, PHP, Kotlin, Swift** |
| Frontend Web App | `react` | React + TypeScript + Vite + Tailwind |
| Backend API (Python) | `python` | FastAPI + pytest + LangGraph |
| Backend API (.NET) | `dotnet-fastendpoints` | FastEndpoints + REPR + ErrorOr |
| Backend API (Node.js) | `typescript-api` | NestJS + Domain modeling |
| Full-Stack App | `fullstack` | React + Python integrated |
| Mobile App (.NET) | `maui-appshell` | .NET MAUI + AppShell + MVVM |

#### Usage Examples

**Example 1: Go Project**

```bash
# Initialize with default template
guardkit init default

# Customize .claude/settings.json
{
  "stack": {
    "language": "go",
    "testing": {
      "command": "go test ./...",
      "coverage_command": "go test -cover ./..."
    }
  }
}

# Start working
/task-create "Add user authentication endpoint"
/task-work TASK-001
```

**Example 2: Rust Project**

```bash
# Initialize
guardkit init default

# Customize settings
{
  "stack": {
    "language": "rust",
    "testing": {
      "command": "cargo test",
      "coverage_command": "cargo tarpaulin"
    }
  }
}
```

**Example 3: For Supported Stacks, Use Specialized Templates**

```bash
# React project → Use react template (NOT default)
guardkit init react

# Python API → Use python template (NOT default)
guardkit init python

# .NET API → Use dotnet-fastendpoints (NOT default)
guardkit init dotnet-fastendpoints
```

**3. Migrate Existing Tasks**

If you have existing tasks from the `default` template:

```bash
# Copy task files to new project
cp -r old-project/tasks/* new-project/tasks/

# Update task frontmatter if needed (technology stack)
# Edit tasks/in_progress/TASK-XXX.md
# Update stack: from "generic" to "react" (or your chosen stack)
```

**4. Customize if Needed**

The technology-specific templates provide starting points. If you need customization:

```bash
# Option 1: Use template as-is and customize over time
guardkit init react
# Add your custom patterns incrementally

# Option 2: Create custom template from your existing codebase
cd your-production-codebase
/template-create  # Creates custom template
guardkit init your-custom-template
```

---

## Creating Custom Templates

**For projects with unique requirements**, create a template from your production codebase:

### Using `/template-create` Command

```bash
# 1. Navigate to your production codebase
cd ~/projects/your-production-app

# 2. Run template creation (interactive)
/template-create

# Or non-interactive:
/template-create --name my-custom-template --output-location personal

# 3. Use your custom template
cd ~/projects/new-project
guardkit init my-custom-template
```

### Benefits of Custom Templates

1. **Based on Real Code**: Templates reflect your actual production patterns
2. **Team-Specific**: Captures your team's conventions and standards
3. **Complete Patterns**: Includes all layers, testing strategies, and tooling
4. **Quality Validated**: Can be validated with `/template-validate` command

### Template Validation

Before using a custom template in production:

```bash
# Level 2: Extended validation (recommended)
/template-create --validate --name my-template

# Level 3: Comprehensive audit (optional)
/template-validate ~/.agentecflow/templates/my-template
```

---

## Accessing Archived Templates

If you absolutely need the old templates, they are preserved in git history.

### Access via Git Tag

```bash
# Checkout the tag before removal
git checkout v1.9-templates-before-removal

# View template directory
ls installer/global/templates/

# Copy specific template if needed
cp -r installer/global/templates/dotnet-aspnetcontroller ~/my-backup/

# Return to current branch
git checkout main
```

### Extract Specific Template

```bash
# Extract from git history
git show v1.9-templates-before-removal:installer/global/templates/dotnet-aspnetcontroller/CLAUDE.md > dotnet-aspnetcontroller-CLAUDE.md

# Or extract entire directory
git archive v1.9-templates-before-removal installer/global/templates/dotnet-aspnetcontroller | tar -x
```

---

## Frequently Asked Questions

### Q: Why were these templates changed?

**A**: After a comprehensive audit (TASK-056), we identified that:
- Only 30% of templates met the 8+/10 quality threshold
- `dotnet-aspnetcontroller` (6.5/10) was redundant with modern alternatives
- `default` (6.0/10) needed improvement to provide clear value

**TASK-060A Update**: The `default` template has been **reinstated** with quality improvements (6.0 → 8.0) and repositioned as a language-agnostic starter for Go, Rust, Ruby, PHP, and other unsupported stacks.

Our strategy focuses on **quality over quantity** - fewer, better templates that serve as exemplary reference implementations.

### Q: What if I was using `dotnet-aspnetcontroller` in production?

**A**: You have several options:

1. **Continue using your existing setup** - Already initialized projects are not affected
2. **Migrate to `dotnet-fastendpoints`** - Modern REPR pattern with better architecture (see migration guide above)
3. **Extract from archive** - Access the old template via git tag if absolutely needed
4. **Create custom template** - Use `/template-create` from your existing codebase

### Q: What if I need to use the `default` template?

**A**: The `default` template is now reinstated and improved (8.0/10). Use it for:

- **Unsupported Languages**: Go, Rust, Ruby, PHP, Kotlin, Swift, Elixir, Scala
- **Custom Stacks**: Unique technology combinations
- **Prototyping**: Exploring GuardKit before committing

**However, if you're using a supported stack, always choose the specialized template**:
- **JavaScript/TypeScript**: `react` or `typescript-api`
- **Python**: `python`
- **.NET**: `dotnet-fastendpoints` or `dotnet-minimalapi`
- **.NET Mobile**: `maui-appshell`
- **Full-stack**: `fullstack`

Specialized templates provide significantly better guidance and patterns for those stacks.

### Q: Will future versions remove more templates?

**A**: Our goal is to maintain high-quality reference templates (8+/10 score). Current templates meeting this threshold:

- `maui-appshell` (8.8/10) ✅
- `maui-navigationpage` (8.5/10) ✅
- `fullstack` (8.0/10) ✅
- `default` (8.0/10) ✅ **(Reinstated in TASK-060A)**

We're working to improve the remaining templates (`react`, `python`, `typescript-api`, `dotnet-fastendpoints`, `dotnet-minimalapi`) to reach the quality threshold.

### Q: How do I know which template to choose?

**A**: Use this decision tree:

```
What language/stack are you using?
├─ Go, Rust, Ruby, PHP, Kotlin, Swift, Elixir, Scala → default (language-agnostic)
├─ Mobile (.NET) → maui-appshell (modern) or maui-navigationpage (traditional)
├─ Full-stack (React + Python) → fullstack
├─ Frontend (React/TypeScript) → react
└─ Backend API → What language?
    ├─ Python → python (FastAPI)
    ├─ .NET → dotnet-fastendpoints (modern) or dotnet-minimalapi (lightweight)
    └─ Node.js → typescript-api (NestJS)
```

### Q: Can I still use guardkit without templates?

**A**: Yes, but not recommended. Templates provide:
- Architecture patterns and best practices
- Quality gates and testing strategies
- AI agents specialized for your stack
- Code generation templates
- Documentation and examples

For best results, choose a template that matches your technology stack or create a custom template from your codebase.

---

## Template Quality Scores

For reference, here are the quality scores from audits:

| Template | Score | Grade | Status |
|----------|-------|-------|--------|
| maui-appshell | 8.8/10 | B+ | ✅ Kept (Reference) |
| maui-navigationpage | 8.5/10 | A- | ✅ Kept (Reference) |
| fullstack | 8.0/10 | B+ | ✅ Kept (Reference) |
| **default** | **8.0/10** | **B** | ✅ **Reinstated (TASK-060A)** |
| react | 7.5/10 | B | ⚠️ Kept (Needs improvement) |
| python | 7.5/10 | B | ⚠️ Kept (Needs improvement) |
| typescript-api | 7.2/10 | B | ⚠️ Kept (Needs improvement) |
| dotnet-fastendpoints | 7.0/10 | B | ⚠️ Kept (Needs improvement) |
| dotnet-minimalapi | 6.8/10 | C | ⚠️ Kept (Needs improvement) |
| dotnet-aspnetcontroller | 6.5/10 | C | ❌ Removed (Redundant) |

**Note**: The `default` template was initially removed (6.0/10) but has been reinstated with quality improvements (8.0/10) as a language-agnostic starter for unsupported stacks (Go, Rust, Ruby, PHP, etc.).

---

## Support

### Questions or Issues?

- **GitHub Issues**: [Report migration issues](https://github.com/guardkit/guardkit/issues)
- **Discussions**: [Ask questions](https://github.com/guardkit/guardkit/discussions)
- **Documentation**: [Template guides](docs/guides/)

### Additional Resources

- [Template Strategy Decision](docs/research/template-strategy-decision.md)
- [Template Audit Comparative Analysis](docs/research/template-audit-comparative-analysis.md)
- [Template Validation Guide](docs/guides/template-validation-guide.md)
- [Creating Local Templates](docs/guides/creating-local-templates.md)

---

**Migration Guide Version**: 1.0
**GuardKit Version**: 2.0.0
**Last Updated**: 2025-11-09
