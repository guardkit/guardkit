---
id: TASK-FMT-006
title: Create .claude/rules for fastmcp-python template
status: backlog
task_type: documentation
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: medium
tags: [template, mcp, fastmcp, rules]
complexity: 4
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 2
parallel_group: wave2
implementation_mode: task-work
conductor_workspace: fastmcp-wave2-4
dependencies: [TASK-FMT-002]
---

# Task: Create .claude/rules for fastmcp-python template

## Description

Create the `.claude/rules/` directory structure for the `fastmcp-python` template. These rules provide path-specific guidance that loads conditionally based on active files.

## Reference

Use `installer/core/templates/fastapi-python/.claude/rules/` as structural reference.

## Files to Create

```
installer/core/templates/fastmcp-python/.claude/rules/
├── mcp-patterns.md      # Core MCP patterns (paths: src/**/*.py)
├── testing.md           # Testing patterns (paths: tests/**/*.py)
├── docker.md            # Docker patterns (paths: **/Dockerfile, docker-compose.yml)
└── config.md            # Configuration patterns (paths: **/.mcp.json, pyproject.toml)
```

## Acceptance Criteria

### mcp-patterns.md

- [ ] Frontmatter with paths: `src/**/*.py`
- [ ] 10 critical patterns documented
- [ ] Code examples for each pattern
- [ ] Links to MCP documentation

```markdown
---
paths: src/**/*.py, **/__main__.py
---

# MCP Development Patterns

## Critical Pattern 1: Tool Registration in __main__.py
Tools MUST be registered at module level in `__main__.py`.
...

## Critical Pattern 2: Logging to stderr
stdout is reserved for MCP protocol communication.
...
```

### testing.md

- [ ] Frontmatter with paths: `tests/**/*.py`
- [ ] Protocol testing patterns
- [ ] String parameter test patterns
- [ ] Async test patterns

### docker.md

- [ ] Frontmatter with paths: `**/Dockerfile, **/docker-compose.yml`
- [ ] Non-root user pattern
- [ ] PYTHONUNBUFFERED requirement
- [ ] Claude Code Docker configuration

### config.md

- [ ] Frontmatter with paths: `**/.mcp.json, **/pyproject.toml`
- [ ] Absolute path requirements
- [ ] PYTHONPATH configuration
- [ ] Environment variables

## Pattern Coverage

| Pattern | Rule File |
|---------|-----------|
| FastMCP not custom | mcp-patterns.md |
| __main__.py registration | mcp-patterns.md |
| stderr logging | mcp-patterns.md |
| Streaming two-layer | mcp-patterns.md |
| CancelledError handling | mcp-patterns.md |
| String param conversion | mcp-patterns.md |
| Absolute paths | config.md |
| datetime.now(UTC) | mcp-patterns.md |
| Protocol testing | testing.md |
| Docker patterns | docker.md |

## Gap Analysis Additions (TASK-REV-A7F9)

The following rule file was identified in gap analysis and MUST be included:

### Additional Rule File: security.md (GAP-1: Critical)

```
installer/core/templates/fastmcp-python/.claude/rules/security.md
```

**Frontmatter**:
```yaml
---
paths: src/**/*.py, **/.mcp.json, **/config/*.py
---
```

**Required Content**:

```markdown
# MCP Security Patterns

## OAuth 2.1 Requirements (March 2025 Mandatory)

For HTTP-based MCP transports, OAuth 2.1 is **mandatory** per the June 2025 specification update.

### Required Security Features

1. **PKCE (Proof Key for Code Exchange)** - Required for ALL clients
2. **Short-lived Access Tokens** - 15-60 minutes maximum
3. **Refresh Token Rotation** - New refresh token on each use
4. **Scope-based Access Control** - Granular permissions per tool
5. **Resource Indicators (RFC 8707)** - Prevent token mis-redemption

### Configuration Example

\`\`\`json
{
  "security": {
    "auth_required": true,
    "oauth": {
      "pkce_required": true,
      "token_ttl_seconds": 3600,
      "refresh_rotation": true
    },
    "rate_limit": 1000
  }
}
\`\`\`

### NEVER

- ❌ Never echo secrets in tool results or elicitation messages
- ❌ Never use long-lived access tokens (>1 hour)
- ❌ Never skip PKCE for public clients

## Transport Deprecation Notice (GAP-6)

⚠️ **SSE Transport Deprecated** (June 2025)

The Server-Sent Events (SSE) transport is **deprecated** and replaced by **Streamable HTTP**.

- ❌ Do NOT use SSE transport in new projects
- ✅ Use STDIO for local development
- ✅ Use Streamable HTTP for production networked deployment

## References

- [MCP Specification June 2025](https://modelcontextprotocol.io/specification/2025-11-25)
- [OAuth 2.1 for MCP](https://auth0.com/blog/mcp-specs-update-all-about-auth/)
- [RFC 8707 Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)
```

### Updated Rule File Structure

```
installer/core/templates/fastmcp-python/.claude/rules/
├── mcp-patterns.md      # Core MCP patterns (paths: src/**/*.py)
├── testing.md           # Testing patterns (paths: tests/**/*.py)
├── docker.md            # Docker patterns (paths: **/Dockerfile)
├── config.md            # Configuration patterns (paths: **/.mcp.json)
└── security.md          # OAuth 2.1 & transport security (NEW - GAP-1, GAP-6)
```

### Acceptance Criteria Addition

- [ ] `security.md` created with OAuth 2.1 requirements
- [ ] PKCE requirement documented
- [ ] Token lifetime guidance (15-60 minutes)
- [ ] Refresh token rotation documented
- [ ] SSE deprecation warning included
- [ ] Streamable HTTP recommended for production

### Source

These additions address gaps identified in TASK-REV-A7F9 gap analysis:
- GAP-1: OAuth 2.1 security requirements (Critical)
- GAP-6: SSE transport deprecation notice (Minor)

## Test Execution Log

[Automatically populated by /task-work]
