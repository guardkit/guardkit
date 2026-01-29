# GuardKit

![version](https://img.shields.io/badge/version-0.9.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)

**Plan Features. Build Faster.**

GuardKit is built on **Feature Plan Development (FPD)** — a feature-first workflow where a single `/feature-plan` command generates a complete, consistent plan, subtask breakdown, and implementation workspace.

## Key Features

- **Feature Planning** - Single `/feature-plan` command creates feature directory, README, implementation guide, and subtasks
- **Clarifying Questions** - Targeted questions before assumptions, complexity-gated
- **Architectural Review** - SOLID, DRY, YAGNI evaluation before coding
- **Test Enforcement** - Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **AI Agent Discovery** - Automatic specialist matching via metadata (stack, phase, keywords)
- **Quality Gates** - Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **Parallel Development** - Built-in wave detection + Conductor.build integration

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
React, Python, .NET templates and customization guide. See also [Template System Architecture](guides/template-system-architecture.md) for how templates work internally.

### 🤖 [Agent System](agents.md)
AI agent discovery, enhancement workflow, and boundary sections.

### 🔄 [Task Review](task-review.md)
Analysis and decision-making workflows separate from implementation.

### 🔌 [MCP Integration](mcp-integration.md) (Optional)
Enhance with Model Context Protocol servers for library docs and design patterns.

### 🧠 Knowledge Graph (Graphiti)
Learn how to integrate Graphiti's temporal knowledge graph for intelligent context management:
- **[Integration Guide](guides/graphiti-integration-guide.md)** - Add Graphiti to your GuardKit workflow
- **[Setup](setup/graphiti-setup.md)** - Installation and configuration
- **[Architecture](architecture/graphiti-architecture.md)** - How Graphiti enhances GuardKit

### 🛠️ [Troubleshooting](troubleshooting.md)
Common issues, solutions, and the `/debug` command.

## Example Workflow

### Feature Planning (Recommended)

```bash
# Install GuardKit
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# Initialize your project
cd /path/to/your/project
guardkit init react-typescript

# Plan a feature (single command!)
/feature-plan "add user authentication"

# System creates:
# ✅ Review task with technical options
# ✅ Subtask breakdown with parallel waves
# ✅ Implementation guide
# ✅ Feature workspace in tasks/backlog/

# Work through generated subtasks
/task-work TASK-AUTH-001
/task-complete TASK-AUTH-001
```

### Simple Tasks (Direct)

```bash
# Create and work on a simple task (natural language description)
/task-create "The login button styling is broken on mobile devices"
/task-work TASK-a3f8  # Plans, reviews, implements, tests
/task-complete TASK-a3f8
```

Three commands from idea to production-ready code.

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

**Plan Features. Build Faster.** Built for pragmatic developers who ship quality code.
