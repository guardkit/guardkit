# MCP Integration (Optional)

Enhance GuardKit with Model Context Protocol servers for library documentation and design patterns.

## Overview

**All MCPs are optional** - GuardKit works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):

- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

## Setup Guides

- **[Context7 MCP Setup](deep-dives/mcp-integration/context7-setup.md)** - Up-to-date library documentation
- **[Design Patterns MCP Setup](deep-dives/mcp-integration/design-patterns-setup.md)** - Pattern recommendations

## Performance & Optimization

**Optimization Status**: ✅ All MCPs optimized (4.5-12% context window usage)

### Token Budgets

| MCP | Token Usage | When Used |
|-----|-------------|-----------|
| context7 | 2000-6000 tokens | Phase-dependent (when libraries detected) |
| design-patterns | ~5000 tokens | Phase 2.5A (architectural review) |

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

**Install MCPs If:**

- ✅ Using newer library versions frequently
- ✅ Working with niche libraries
- ✅ Need pattern recommendations during review

---

## Next Steps

- **Core MCPs**: Set up [Context7](deep-dives/mcp-integration/context7-setup.md) and [Design Patterns](deep-dives/mcp-integration/design-patterns-setup.md)
- **Optimization**: Read [MCP Optimization Guide](deep-dives/mcp-integration/mcp-optimization.md)
