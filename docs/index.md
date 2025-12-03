# GuardKit

![version](https://img.shields.io/badge/version-0.9.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)

**Lightweight AI-assisted development with built-in quality gates.**

Stop shipping broken code. Get architectural review before implementation and automatic test enforcement after. Simple task workflow, no ceremony.

## Key Features

- **Architectural Review** - SOLID, DRY, YAGNI evaluation before coding (saves 40-50% rework time)
- **Test Enforcement** - Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **AI Agent Discovery** - Automatic specialist matching via metadata (stack, phase, keywords)
- **Stack-Specific Optimization** - Haiku agents for 48-53% cost savings, 4-5x faster implementation
- **Quality Gates** - Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **Simple Workflow** - Create → Work → Complete (3 commands)

## Quick Start

New to GuardKit? Start here:

- **[5-Minute Quickstart](guides/GETTING-STARTED.md)** - Get up and running fast
- **[GuardKit Workflow](guides/guardkit-workflow.md)** - Learn the core workflow
- **[Choose a Template](templates.md)** - Select your tech stack

## Documentation Sections

### 📚 [Core Concepts](concepts.md)
Learn the fundamentals: workflow, complexity evaluation, quality gates, and task states.

### 🚀 [Advanced Topics](advanced.md)
Design-first workflow, UX integration, iterative refinement, and plan modification.

### 🎨 [Templates](templates.md)
React, Python, .NET templates and customization guide.

### 🤖 [Agent System](agents.md)
AI agent discovery, enhancement workflow, and boundary sections.

### 🔄 [Task Review](task-review.md)
Analysis and decision-making workflows separate from implementation.

### 🔌 [MCP Integration](mcp-integration.md) (Optional)
Enhance with Model Context Protocol servers for library docs and design patterns.

### 🛠️ [Troubleshooting](troubleshooting.md)
Common issues, solutions, and the `/debug` command.

## Example Workflow

```bash
# Install GuardKit
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# Initialize your project
cd /path/to/your/project
guardkit init react-typescript

# Create and work on a task
/task-create "Add user authentication"
/task-work TASK-001  # Plans, reviews, implements, tests
/task-complete TASK-001
```

That's it! Three commands from idea to production-ready code.

## When to Use GuardKit

### ✅ Use GuardKit When

- Individual tasks or small features (1-8 hours)
- Solo dev or small teams (1-3 developers)
- Need quality enforcement without ceremony
- Want AI assistance with human oversight
- Small-to-medium projects
- Learning new stack (use reference templates)
- Creating team templates (use `/template-create`)

### 🔗 Use RequireKit When

For formal requirements management (EARS notation, BDD with Gherkin, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with GuardKit.

## Links

- **[GitHub Repository](https://github.com/guardkit/guardkit)** - Source code and contributions
- **[Report an Issue](https://github.com/guardkit/guardkit/issues)** - Bug reports and feature requests
- **[RequireKit](https://github.com/requirekit/require-kit)** - Formal requirements management

---

**Built for pragmatic developers who ship quality code fast.**
