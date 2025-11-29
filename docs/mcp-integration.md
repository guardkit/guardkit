# MCP Integration (Optional)

Enhance Taskwright with Model Context Protocol servers for library documentation and design patterns.

## Overview

**All MCPs are optional** - Taskwright works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):

- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

**Design MCPs** (ONLY used for specific commands):

- **figma-dev-mode**: Figma design extraction (ONLY for `/figma-to-react` command)
- **zeplin**: Zeplin design extraction (ONLY for `/zeplin-to-maui` command)

!!! note
    Design MCPs should only be installed if you're actively using those specific design-to-code commands. They are NOT used during regular `/task-work` execution.

## Setup Guides

### Core MCPs (Recommended for All Users)

- **[Context7 MCP Setup](deep-dives/mcp-integration/context7-setup.md)** - Up-to-date library documentation
- **[Design Patterns MCP Setup](deep-dives/mcp-integration/design-patterns-setup.md)** - Pattern recommendations

### Design MCPs (Only if Using Design-to-Code Workflows)

- **[Figma MCP Setup](mcp-setup/figma-mcp-setup.md)** - For `/figma-to-react` command only
- **[Zeplin MCP Setup](mcp-setup/zeplin-mcp-setup.md)** - For `/zeplin-to-maui` command only

## Performance & Optimization

**Optimization Status**: ✅ All MCPs optimized (4.5-12% context window usage)

### Token Budgets

| MCP | Token Usage | When Used |
|-----|-------------|-----------|
| context7 | 2000-6000 tokens | Phase-dependent (when libraries detected) |
| design-patterns | ~5000 tokens | Phase 2.5A (architectural review) |
| figma-dev-mode | Image-based | `/figma-to-react` command only |
| zeplin | Design-based | `/zeplin-to-maui` command only |

**[MCP Optimization Guide](deep-dives/mcp-integration/mcp-optimization.md)** - Detailed usage guidelines.

## Benefits

### Context7 MCP

**Purpose**: Provides up-to-date library documentation

**Use Cases:**

- New library versions (post-training data cutoff)
- Obscure libraries not in training data
- API changes and deprecations

**Example:**

```bash
# Task uses React Query v5 (newer than training data)
/task-work TASK-042

# Context7 automatically provides React Query v5 docs
# Phase 2: Planning with current API
# Phase 3: Implementation with correct patterns
```

### Design Patterns MCP

**Purpose**: Recommends appropriate design patterns

**Use Cases:**

- Architectural review (Phase 2.5A)
- Pattern selection guidance
- Anti-pattern detection

**Example:**

```bash
# Task involves state management
/task-work TASK-043

# Design Patterns MCP suggests:
# - Repository Pattern (data access)
# - Observer Pattern (state changes)
# - Singleton Pattern (global state)
```

### Figma & Zeplin MCPs

**Purpose**: Design-to-code conversion

**Use Cases:**

- Converting Figma designs to React components
- Converting Zeplin designs to .NET MAUI components
- Visual regression testing

**Example:**

```bash
# Convert Figma design to React
/figma-to-react <file-key> [node-id]

# Figma MCP extracts design
# Generates TypeScript React + Tailwind + Playwright tests
# Visual fidelity: >95%
```

**[UX Design Integration Workflow](workflows/ux-design-integration-workflow.md)** - Complete documentation.

## Installation

### Context7 MCP

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    }
  }
}
```

### Design Patterns MCP

```json
{
  "mcpServers": {
    "design-patterns": {
      "command": "node",
      "args": ["/path/to/design-patterns-mcp/index.js"]
    }
  }
}
```

**Full setup instructions**: See individual MCP setup guides linked above.

## When to Install MCPs

### Install Core MCPs If:

- ✅ Using newer library versions frequently
- ✅ Working with niche libraries
- ✅ Need pattern recommendations during review

### Install Design MCPs If:

- ✅ Actively using `/figma-to-react` or `/zeplin-to-maui`
- ✅ Regular design-to-code conversion workflow
- ❌ NOT using design-to-code commands (skip these)

---

## Next Steps

- **Core MCPs**: Set up [Context7](deep-dives/mcp-integration/context7-setup.md) and [Design Patterns](deep-dives/mcp-integration/design-patterns-setup.md)
- **Optimization**: Read [MCP Optimization Guide](deep-dives/mcp-integration/mcp-optimization.md)
- **Design Workflow**: Explore [UX Design Integration](workflows/ux-design-integration-workflow.md)
