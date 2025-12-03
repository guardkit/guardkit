# Template Philosophy

## Overview

GuardKit's template strategy is simple: **Reference implementations for learning, `/template-create` for production.**

## The 5 Templates

### Stack-Specific Reference Templates

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **react-typescript** | Learn frontend best practices | Evaluating GuardKit, learning React patterns |
| **fastapi-python** | Learn backend API patterns | Evaluating GuardKit, learning FastAPI |
| **nextjs-fullstack** | Learn full-stack development | Evaluating GuardKit, learning Next.js App Router |

### Specialized Template

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **react-fastapi-monorepo** | Learn monorepo patterns | Full-stack monorepo with React + FastAPI, type-safe contracts |

### Language-Agnostic Template

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **default** | Language-agnostic foundation | Go/Rust/Ruby/Elixir projects, evaluation, before `/template-create` |

## Why This Approach?

### 1. Your Code > Generic Templates

**Your production codebase**:
- ✅ Proven to work in production
- ✅ Matches your team's conventions
- ✅ Contains your specific patterns
- ✅ Reflects your architecture decisions

**Generic templates**:
- ⚠️ May not match your conventions
- ⚠️ Generic patterns (not your proven ones)
- ⚠️ Require customization anyway

### 2. Developers Are Opinionated

Every team develops unique:
- Code organization preferences
- Naming conventions
- Architecture patterns
- Technology choices
- Quality standards

**Rather than shipping 50 templates trying to cover every opinion, we provide 5 high-quality templates (3 stack-specific + 1 specialized + 1 language-agnostic) and tools to create your own.**

### 3. Quality Over Quantity

**Old approach**: 9 templates, unknown quality, high maintenance

**New approach**: 5 templates (3 stack-specific at 9+/10, 1 specialized at 9+/10, 1 language-agnostic at 8+/10), low maintenance

### 4. Learning Resource First

Reference templates teach:
- How to structure templates for `/template-create`
- What makes a template high quality
- Stack-specific best practices
- GuardKit workflow integration

## The Production Workflow

### Step 1: Evaluate with Reference Templates

```bash
# Try GuardKit quickly
guardkit init react-typescript

# Explore generated code
# See GuardKit in action
```

### Step 2: Create Your Template

```bash
# Once you're convinced, create from your code
cd your-production-codebase
/template-create

# Answer questions about your stack
# AI generates template automatically
```

### Step 3: Use Your Template

```bash
# Now use YOUR patterns, not ours
guardkit init your-custom-template

# Get YOUR best practices
# Follow YOUR conventions
```

## Comparison with Other Tools

| Tool | Approach | GuardKit Difference |
|------|----------|---------------------|
| create-react-app | 1 opinionated template | 3 reference examples + create your own |
| dotnet new | 50+ built-in templates | 3 references + `/template-create` from your code |
| Yeoman | Community generators | `/template-create` from production code |

**Unique value**: Create templates from your actual production code, not from generic examples.

## When to Use Which Template

### Use react-typescript When:
- ⏱️ Evaluating GuardKit (< 1 hour)
- 📚 Learning React + TypeScript best practices
- 🎓 Training new team members
- 🔍 Reference for building your own template

### Use fastapi-python When:
- ⏱️ Evaluating GuardKit for backend
- 📚 Learning FastAPI best practices
- 🎓 Training Python developers
- 🔍 Reference for API architecture

### Use nextjs-fullstack When:
- ⏱️ Evaluating GuardKit for full-stack
- 📚 Learning Next.js App Router
- 🎓 Training full-stack developers
- 🔍 Reference for modern Next.js

### Use react-fastapi-monorepo When:
- ⏱️ Evaluating GuardKit for full-stack monorepo
- 📚 Learning monorepo patterns with type safety
- 🎓 Training teams on React + FastAPI integration
- 🔍 Reference for monorepo architecture

### Use default When:
- 🌐 Working with Go, Rust, Ruby, Elixir, PHP, or other unsupported languages
- ⏱️ Quick evaluation without stack commitment
- 🎯 Learning GuardKit before creating custom template
- 📝 Need language-agnostic workflow foundation

### Use `/template-create` When:
- 🚀 Production projects
- 🏢 Team/organization templates
- 🎯 Custom stack not covered by references
- ✅ You have proven production code

## FAQ

**Q: Why don't you ship templates for [my favorite stack]?**

A: We provide stack-specific templates for the most popular stacks (React, FastAPI, Next.js) and a language-agnostic `default` template for everything else. For production, YOUR code is better than any template we could create—use `/template-create` from your codebase.

**Q: Can I modify the reference templates?**

A: Yes, but we recommend using them as references and creating your own with `/template-create` instead.

**Q: What happened to the other templates?**

A: We reduced from 9 to 5 high-quality templates:
- **3 stack-specific** at 9+/10 (react-typescript, fastapi-python, nextjs-fullstack)
- **1 specialized** at 9+/10 (react-fastapi-monorepo)
- **1 language-agnostic** at 8+/10 (default)

The `default` template was temporarily removed but has been reinstated with quality improvements (TASK-060A). The monorepo template was added in TASK-062. The guardkit-python template was removed in TASK-G6D4 (created user confusion, no valid use case). Old templates are archived. See [Template Migration Guide](template-migration.md).

**Q: How do I share templates with my team?**

A: Use `/template-create` in your repo, commit to git, team members run `install.sh`. See [Creating Local Templates](creating-local-templates.md).

## Agent Enhancement Strategy

### Why Templates Ship with Generic Boundaries

Templates include **generic boundaries (6/10 quality)** generated by `/agent-format`:

**Reasons**:
1. **Speed**: All template agents enhanced in <1 minute (vs 45+ minutes with AI)
2. **No AI Dependencies**: No Claude API calls during template creation
3. **Zero Cost**: Template authors don't pay for AI generation
4. **Maximum Reusability**: Generic boundaries work for ANY project using the stack
5. **Progressive Enhancement**: Users can upgrade to 9/10 when they need it

### Two-Tier Quality System

| Tier | Quality | Generated By | When | Who Benefits |
|------|---------|--------------|------|--------------|
| **Template (Tier 1)** | 6/10 | `/agent-format` | Template creation | All users (included) |
| **Project (Tier 2)** | 9/10 | `/agent-enhance` | After project init | Individual users (optional) |

### Template User Workflow

**Day 1: Initialize with template**
```bash
guardkit init react-typescript
# All agents have generic boundaries (6/10)
# Immediate value: Better than 0/10, follows GitHub standards
```

**Optional: Upgrade to domain-specific**
```bash
# Enhance critical agents for your specific codebase
/agent-enhance .claude/agents/api-specialist.md
/agent-enhance .claude/agents/testing-specialist.md
# Now 9/10 with boundaries tailored to YOUR project
```

### Benefits of This Approach

1. **Template authors**: Fast creation, no API costs
2. **Template users**: Immediate 6/10 quality, optional upgrade to 9/10
3. **Cost distribution**: Users only pay for AI if they choose to upgrade
4. **Quality consistency**: All templates meet 6/10 baseline

## Related Documentation

- [Creating Local Templates](creating-local-templates.md) - Create templates from your code
- [Agent Enhancement Decision Guide](agent-enhancement-decision-guide.md) - Choose between /agent-format and /agent-enhance
- [Template Quality Validation](template-quality-validation.md) - Quality standards
- [Template Migration Guide](template-migration.md) - Migrating from old templates
- [Template Strategy Decision](../research/template-strategy-decision.md) - Full rationale
