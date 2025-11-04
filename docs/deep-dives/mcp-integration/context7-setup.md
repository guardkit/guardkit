# Context7 MCP Setup Guide

**Purpose**: Enhance `/task-work` command with up-to-date library documentation during implementation phases (2, 3, and 4).

**MCP Server**: `upstash/context7` (Node.js-based, real-time documentation for 2000+ libraries)

---

## Overview

Context7 is an MCP server that solves the problem of stale documentation by providing **real-time, version-specific** documentation and code examples directly from official sources. This ensures your implementations use the latest patterns and APIs, not outdated training data.

**Key Benefits**:
- Up-to-date library documentation (React, FastAPI, Next.js, etc.)
- Version-specific code examples
- Automatic during `/task-work` execution (Phases 2, 3, 4)
- Falls back gracefully if unavailable (uses training data)

---

## Prerequisites

Before installing, ensure you have:
- **Node.js** v18 or later ([download here](https://nodejs.org/))
- **npm** (comes with Node.js)
- **Claude Code** or compatible MCP client (Cursor, VS Code with MCP extension)

Verify installations:
```bash
node --version  # Should show v18.0.0 or later
npm --version   # Should show v8.0.0 or later
```

---

## Quick Start (Recommended)

### Method 1: Smithery CLI (Automatic Setup)

**Fastest method** - Automatically configures Context7 for your MCP client:

```bash
# For Claude Code
npx -y @smithery/cli@latest install @upstash/context7-mcp --client claude

# For Cursor
npx -y @smithery/cli@latest install @upstash/context7-mcp --client cursor

# For VS Code
npx -y @smithery/cli@latest install @upstash/context7-mcp --client vscode
```

This automatically:
- Installs Context7 MCP server
- Configures MCP client settings
- Sets up API key (if required)
- Verifies connection

**Skip to [Step 4: Verify Installation](#step-4-verify-installation) if using Smithery CLI.**

---

## Method 2: Manual Installation

If you prefer manual setup or Smithery CLI is unavailable:

### Step 1: Choose Installation Method

Context7 offers two transport methods:

**HTTP Transport** (Recommended):
- Hosted by Upstash (no local server)
- Always up-to-date
- Requires internet connection
- Free tier available

**Stdio Transport** (Advanced):
- Self-hosted via npm package
- Runs locally
- Requires Node.js runtime
- More control over caching

**For most users**: HTTP transport is simpler and recommended.

---

### Step 2A: HTTP Transport Setup (Recommended)

**For Claude Code:**

1. Edit `~/.config/claude-code/mcp.json`:

```json
{
  "mcpServers": {
    "context7": {
      "transport": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

2. Restart Claude Code.

**For Cursor:**

1. Edit `~/.cursor/mcp.json` (or `.cursor/mcp.json` in project root):

```json
{
  "mcpServers": {
    "context7": {
      "transport": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

2. Restart Cursor.

---

### Step 2B: Stdio Transport Setup (Advanced)

**Only use if you need local hosting or offline access.**

**Step 1: Install Context7 package**

```bash
# Install globally
npm install -g @upstash/context7-mcp

# Or install locally (requires absolute path in config)
npm install @upstash/context7-mcp
```

**Step 2: Configure MCP client**

**For Claude Code** (`~/.config/claude-code/mcp.json`):

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

**For Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

**Step 3: Restart your MCP client**

---

### Step 3: Verify Configuration Syntax

Ensure the JSON is valid (no trailing commas, proper quotes):

```bash
# macOS/Linux - validate JSON
python3 -m json.tool ~/.config/claude-code/mcp.json

# Windows (PowerShell) - validate JSON
Get-Content "$env:APPDATA\claude-code\mcp.json" | ConvertFrom-Json
```

If valid, you'll see formatted JSON output. If invalid, fix syntax errors before proceeding.

---

### Step 4: Verify Installation

**Restart your MCP client** (Claude Code, Cursor, etc.) completely to load the new MCP server configuration.

The MCP server will start automatically when your client launches and will be available as `mcp__context7__*` tools.

**Test in Claude Code:**

```
Can you use Context7 to get the latest React hooks documentation?
```

**Expected response**:
- Claude should use `mcp__context7__resolve-library-id` ("react")
- Then use `mcp__context7__get-library-docs` with resolved ID
- Should return current React documentation

**If successful**: Context7 is working! Proceed to [Usage](#available-mcp-tools) section.

**If failed**: See [Troubleshooting](#troubleshooting) section below.

---

## Available MCP Tools

Once installed, the following tools are available:

### 1. `mcp__context7__resolve-library-id`

**Purpose**: Convert library name to Context7-compatible ID

**Use Case**: Always call this BEFORE getting documentation

**Parameters**:
```typescript
{
  libraryName: string  // "react", "fastapi", "next.js", etc.
}
```

**Example**:
```
Query: resolve-library-id("fastapi")

Response:
{
  id: "/tiangolo/fastapi",
  version: "0.104.0",
  trust_score: 9.5,
  last_updated: "2024-01-15"
}
```

---

### 2. `mcp__context7__get-library-docs`

**Purpose**: Fetch up-to-date library documentation

**Use Case**: Primary tool for `/task-work` Phases 2, 3, 4 when implementing with specific libraries

**Parameters**:
```typescript
{
  context7CompatibleLibraryID: string,  // From resolve-library-id
  topic?: string,                       // Optional: narrow to specific area
  tokens?: number                       // Optional: max tokens (default: 5000)
}
```

**Example**:
```
Query: get-library-docs({
  context7CompatibleLibraryID: "/tiangolo/fastapi",
  topic: "dependency-injection",
  tokens: 5000
})

Response:
# FastAPI Dependency Injection

FastAPI uses Python's type hints to provide a powerful dependency injection system...

[Latest patterns, code examples, best practices]
```

---

## Integration with `/task-work` Command

Context7 is integrated into multiple phases of the `/task-work` command:

### Phase 2: Implementation Planning

**When**: Task requires specific library or framework

**What happens**:
1. Detect required libraries from task description
2. Resolve library IDs via Context7
3. Fetch documentation for each library
4. Incorporate latest patterns into implementation plan

**Example**:
```
Task: "Implement JWT authentication endpoint using FastAPI"

Context7 Usage:
📚 Fetching latest documentation for FastAPI...
✅ Retrieved FastAPI documentation (topic: dependency-injection)

Implementation plan now includes:
- Latest FastAPI dependency injection patterns
- Current security best practices
- Up-to-date code examples
```

---

### Phase 3: Implementation

**When**: Implementing with library-specific patterns

**What happens**:
1. For each library-specific feature
2. Fetch focused documentation with topic parameter
3. Implement using latest patterns from Context7

**Example**:
```
Task: "Implement custom React hook for form validation"

Context7 Usage:
📚 Fetching latest documentation for React (hooks)...
✅ Retrieved React documentation (topic: hooks)

Implementation uses:
- Current hook best practices
- Latest dependency array patterns
- Up-to-date error handling
```

---

### Phase 4: Testing

**When**: Setting up tests with testing frameworks

**What happens**:
1. Detect testing framework (pytest, Vitest, xUnit)
2. Fetch testing documentation
3. Generate tests following framework best practices

**Example**:
```
Task: "Write tests for authentication service"

Context7 Usage:
📚 Fetching latest documentation for pytest...
✅ Retrieved pytest documentation (topic: fixtures)

Tests use:
- Latest fixture patterns
- Current async testing approaches
- Up-to-date assertion methods
```

---

## Best Practices

### 1. Always Resolve First

**DON'T** assume library path format:
```python
# ❌ Bad: Assuming path format
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/react",  # Wrong format
  ...
)
```

**DO** resolve library ID first:
```python
# ✅ Good: Resolve first
library_id = mcp__context7__resolve_library_id("react")
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID=library_id,
  ...
)
```

---

### 2. Use Topic Parameter

**Narrow documentation to relevant sections** to reduce token usage:

```python
# Instead of fetching all docs (may exceed token limit)
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/facebook/react"
)

# Narrow to specific topic
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/facebook/react",
  topic="hooks",  # Only fetch hooks documentation
  tokens=5000
)
```

---

### 3. Cache Library IDs

**Reuse resolved IDs within same task session:**

```python
# At start of Phase 2
fastapi_id = mcp__context7__resolve_library_id("fastapi")
pytest_id = mcp__context7__resolve_library_id("pytest")

# Reuse in Phase 3
fastapi_docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID=fastapi_id,  # Reuse
  ...
)

# Reuse in Phase 4
pytest_docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID=pytest_id,  # Reuse
  ...
)
```

---

### 4. Limit Token Usage

**Default 5000 tokens is usually sufficient:**

```python
# For most cases, default is fine
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/tiangolo/fastapi",
  topic="dependency-injection",
  tokens=5000  # Default
)

# Only increase if documentation is truncated
docs = mcp__context7__get_library_docs(
  context7CompatibleLibraryID="/tiangolo/fastapi",
  topic="dependency-injection",
  tokens=8000  # Increased
)
```

---

### 5. Always Inform User

**Display what documentation is being fetched:**

```python
print("📚 Fetching latest documentation for FastAPI...")

docs = mcp__context7__get_library_docs(...)

print("✅ Retrieved FastAPI documentation (topic: dependency-injection)")
```

---

## When NOT to Use Context7

**Skip Context7 for:**

1. **Standard language features**
   - JavaScript syntax (const, let, arrow functions)
   - Python syntax (list comprehensions, decorators)
   - TypeScript types (interfaces, generics)

2. **Well-established patterns**
   - SOLID principles
   - DRY principle
   - Design patterns (Factory, Repository, Observer)

3. **General software engineering concepts**
   - REST API principles
   - Database normalization
   - Async/await concepts

4. **Standard library functions**
   - JavaScript: Array.map, Promise.all
   - Python: json.loads, datetime.now
   - C#: LINQ, Task.Run

**These are already in training data and don't need current documentation.**

---

## Supported Libraries

Context7 provides documentation for 2000+ popular libraries across all major ecosystems:

### JavaScript/TypeScript
- react, next.js, vue, angular, svelte
- express, nestjs, fastify
- vitest, jest, playwright, cypress
- tailwindcss, styled-components
- prisma, typeorm, mongoose

### Python
- fastapi, django, flask
- pytest, unittest
- pydantic, sqlalchemy
- langchain, langgraph
- pandas, numpy, scikit-learn

### .NET/C#
- aspnetcore, maui
- entity-framework
- xunit, nunit
- polly, fluentvalidation
- fastendpoints

### Other
- rust, go, java, kotlin
- docker, kubernetes
- terraform, ansible

**Check availability**: Use `resolve-library-id` to verify library is available.

---

## Troubleshooting

### MCP Server Not Available

**Symptom**: `/task-work` doesn't fetch Context7 docs, tools not found

**Check**:
```bash
# Verify MCP server is configured
cat ~/.config/claude-code/mcp.json  # macOS/Linux
type %APPDATA%\claude-code\mcp.json  # Windows

# Restart Claude Code completely
```

**Solution**:
- Ensure `mcp.json` has correct configuration
- For HTTP transport: Check internet connection
- For stdio transport: Verify `node` is in PATH
- Restart MCP client completely (quit and relaunch)

---

### Library Not Found

**Symptom**: `resolve-library-id` returns "Library not found"

**Check**:
```
# Try different variations
resolve-library-id("react")           # ✅ Works
resolve-library-id("facebook/react")  # ❌ Too specific
resolve-library-id("React")           # ❌ Case sensitive

# Check spelling
resolve-library-id("fastapi")   # ✅ Correct
resolve-library-id("fast-api")  # ❌ Wrong spelling
```

**Solution**:
- Use common library name (lowercase)
- Try package manager name (e.g., "next.js" not "nextjs")
- Check official package name on npm/PyPI/NuGet

---

### Documentation Retrieval Failed

**Symptom**: Error when fetching documentation

**Check**:
```bash
# HTTP transport: Check internet connection
ping mcp.context7.com

# Stdio transport: Check node is running
ps aux | grep context7
```

**Solution**:
- For HTTP: Verify internet connection
- For stdio: Check Node.js is installed and in PATH
- Try reducing `tokens` parameter
- Check library ID is correct format (from `resolve-library-id`)

---

### Slow Response Times

**Symptom**: Context7 queries take >5 seconds

**Solution**:
1. **Use topic parameter** to narrow docs:
   ```python
   # Slow: Fetches all docs
   docs = get_library_docs("/facebook/react")

   # Fast: Focused on topic
   docs = get_library_docs("/facebook/react", topic="hooks")
   ```

2. **Reduce token limit**:
   ```python
   # Default: 5000 tokens
   docs = get_library_docs(..., tokens=3000)  # Faster
   ```

3. **Switch to HTTP transport** (if using stdio):
   - HTTP is hosted and optimized by Upstash
   - Usually faster than local stdio

---

### No Documentation Returned

**Symptom**: MCP query returns empty results

**Check**:
- Library ID may be incorrect (re-run `resolve-library-id`)
- Topic may be too specific (try broader term or omit)
- Token limit may be too low (increase to 5000+)

**Solution**:
```python
# If this returns empty:
docs = get_library_docs("/react", topic="server-components", tokens=2000)

# Try this:
docs = get_library_docs("/react", topic="components", tokens=5000)

# Or omit topic entirely:
docs = get_library_docs("/react", tokens=5000)
```

---

## HTTP vs Stdio Transport

| Feature | HTTP (Recommended) | Stdio (Advanced) |
|---------|-------------------|------------------|
| **Setup complexity** | Simple (2 lines config) | Complex (npm install) |
| **Maintenance** | None (hosted by Upstash) | Update npm package |
| **Speed** | Fast (CDN-backed) | Varies (local) |
| **Offline support** | ❌ Requires internet | ✅ Works offline |
| **Control** | Limited | Full control |
| **Best for** | Most users | Advanced setups, enterprise |

**Recommendation**: Start with HTTP transport. Only switch to stdio if you need offline support or custom caching.

---

## Performance Optimization

Context7 is already optimized in Taskwright (see [MCP Optimization Guide](mcp-optimization-guide.md)):

**Current metrics**:
- Context window usage: 4.5-12%
- Average query time: <2 seconds
- Token consumption: 2000-6000 tokens per query

**Built-in optimizations**:
1. **Lazy loading**: Only loaded when needed
2. **Topic scoping**: Focused queries reduce token usage
3. **Token limits**: Default 5000 tokens prevents overload
4. **Phase-specific**: Only used in Phases 2, 3, 4
5. **Caching**: Library IDs cached within session

---

## Graceful Degradation

If Context7 is unavailable, the system **automatically falls back** to training data:

```
📚 Fetching latest documentation for FastAPI...
⚠️  Context7 MCP unavailable, using training data
✅ Proceeding with implementation (may use older patterns)
```

**Impact**:
- No task failures
- Implementation continues normally
- May use slightly outdated patterns
- Quality gates still enforced

**System continues to work without Context7** - it's an enhancement, not a requirement.

---

## Related Documentation

- [Context7 MCP Integration Workflow](../workflows/context7-mcp-integration-workflow.md) - Usage patterns and examples
- [MCP Optimization Guide](mcp-optimization-guide.md) - Performance and token usage
- [task-work.md](../../installer/global/commands/task-work.md) - Full command specification
- [task-manager.md](../../installer/global/agents/task-manager.md) - Task manager agent

---

## Summary

**Installation**: HTTP transport (2-line config) or stdio (npm install)

**Usage**: Automatic in `/task-work` Phases 2, 3, 4 when library-specific APIs involved

**Value**: Latest library patterns, up-to-date documentation, no deprecated code

**Integration**: Seamless with graceful fallback if unavailable

**Optional**: System works fine without Context7 (uses training data as fallback)

---

## Next Steps

1. Install Context7 MCP server (HTTP transport recommended)
2. Configure your MCP client (Claude Code, Cursor, etc.)
3. Restart client and verify with test query
4. Use `/task-work` to see Context7 in action
5. Monitor [MCP Optimization Guide](mcp-optimization-guide.md) for best practices

---

**Context7 is maintained by**: [Upstash](https://github.com/upstash/context7)

**License**: Apache 2.0 (free and open-source)

**Support**: [GitHub Issues](https://github.com/upstash/context7/issues)
