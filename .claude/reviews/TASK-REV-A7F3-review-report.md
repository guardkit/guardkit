# Architectural Review Report: TASK-REV-A7F3

## Executive Summary

**Task**: Review MCP Implementation Report for Template Consistency
**Review Mode**: Architectural
**Review Depth**: Standard
**Duration**: Comprehensive Analysis
**Date**: 2026-01-24

**Overall Assessment**: The MCP implementation proposal from TASK-REV-MCP contains excellent technical patterns but **does not follow GuardKit template conventions**. The proposed structure is a runtime project structure, not a GuardKit template structure. Significant revision is needed to create a proper `fastmcp-python` template.

**Architecture Score**: 45/100 (Template Consistency)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Technical Patterns | 90/100 | 10 critical patterns are excellent |
| Template Structure | 20/100 | Missing all GuardKit template components |
| Settings Convention | 0/100 | No settings.json or naming conventions |
| Agent Convention | 0/100 | No agent files defined |
| Documentation | 40/100 | Good technical docs, wrong format |

---

## Key Findings

### Finding 1: Proposed Structure is Runtime, Not Template

**MCP Proposal (TASK-REV-MCP Recommendation 1)**:
```
mcp-server-{name}/
├── src/
│   ├── __init__.py
│   ├── __main__.py          # Tool registration (CRITICAL)
│   ├── server.py            # FastMCP server implementation
│   ├── tools/
│   └── resources/
├── tests/
├── docker/
├── docs/
├── pyproject.toml
├── README.md
└── .claude/
    └── settings.json
```

**GuardKit Template Standard (fastapi-python)**:
```
fastapi-python/                    # Template root
├── .claude/                       # Claude Code integration
│   ├── CLAUDE.md                  # Template-specific CLAUDE.md
│   └── rules/                     # Path-specific rules
│       ├── code-style.md
│       ├── testing.md
│       └── api/
│           ├── routing.md
│           └── schemas.md
├── agents/                        # Specialist agents
│   ├── fastapi-specialist.md
│   ├── fastapi-specialist-ext.md
│   ├── fastapi-database-specialist.md
│   └── fastapi-testing-specialist.md
├── templates/                     # Code scaffolding templates
│   ├── api/router.py.template
│   ├── schemas/schemas.py.template
│   └── testing/conftest.py.template
├── manifest.json                  # Template metadata
├── settings.json                  # Naming conventions & structure
├── CLAUDE.md                      # Top-level guidance
└── README.md                      # Template documentation
```

**Gap**: The MCP proposal describes what a *generated MCP project* would look like, not what a *GuardKit template* should contain.

---

### Finding 2: Missing Required Template Components

| Component | Required? | MCP Proposal | fastapi-python | Gap |
|-----------|-----------|--------------|----------------|-----|
| `manifest.json` | ✅ | ❌ Missing | ✅ Complete | **Critical** |
| `settings.json` | ✅ | ❌ Missing | ✅ Complete | **Critical** |
| `agents/` directory | ✅ | ❌ Missing | ✅ 6 agents | **Critical** |
| `templates/` directory | ✅ | ❌ Missing | ✅ 8 templates | **Critical** |
| `.claude/rules/` | ✅ | ❌ Missing | ✅ 10 rules | **Major** |
| `.claude/CLAUDE.md` | ✅ | ❌ Missing | ✅ Present | **Major** |
| Top-level `CLAUDE.md` | ✅ | ❌ Missing | ✅ Present | **Major** |
| `README.md` | ✅ | ✅ Mentioned | ✅ Present | Minor |

**Impact**: A template created from the MCP proposal would not work with:
- `guardkit init fastmcp-python` (no manifest)
- Agent discovery (no agents directory)
- Code scaffolding (no templates directory)
- Naming conventions (no settings.json)

---

### Finding 3: manifest.json Requirements Not Addressed

**Required manifest.json structure** (from fastapi-python):

```json
{
  "schema_version": "1.0.0",
  "name": "fastmcp-python",          // Required
  "display_name": "FastMCP Python",   // Required
  "description": "...",               // Required
  "version": "1.0.0",
  "author": "GuardKit",
  "language": "Python",
  "language_version": ">=3.10",
  "frameworks": [
    {"name": "FastMCP", "version": ">=0.x", "purpose": "mcp_server"},
    {"name": "mcp", "version": ">=1.0", "purpose": "protocol"},
    {"name": "pytest", "version": ">=7.4.0", "purpose": "testing"}
  ],
  "architecture": "MCP Server Pattern",
  "patterns": [
    "Tool Registration in __main__.py",
    "Streaming Two-Layer Architecture",
    "stderr Logging",
    "String Parameter Conversion"
  ],
  "layers": ["tools", "resources", "server"],
  "placeholders": {...},
  "tags": ["python", "mcp", "fastmcp", "claude-code"],
  "category": "integration",
  "complexity": 5,
  "quality_scores": {...}
}
```

**MCP Proposal**: No manifest defined at all.

---

### Finding 4: settings.json Naming Conventions Not Defined

**Required settings.json structure** (from fastapi-python):

```json
{
  "naming_conventions": {
    "tool": {
      "pattern": "{{name}}",
      "case_style": "snake_case",
      "examples": ["search_patterns", "get_details"],
      "description": "MCP tool functions use snake_case"
    },
    "server": {
      "pattern": "{{name}}-server",
      "examples": ["design-patterns-server", "requirements-server"]
    },
    "test_file": {
      "pattern": "test_{{feature}}.py",
      "examples": ["test_tools.py", "test_protocol.py"]
    }
  },
  "file_organization": {...},
  "layer_mappings": {...},
  "code_style": {...},
  "testing": {...}
}
```

**MCP Proposal**: Only mentions generic Python conventions without MCP-specific guidance.

---

### Finding 5: Agent Files Not Defined

**Required agent structure** (from fastapi-python):

```markdown
---
name: fastmcp-specialist
description: FastMCP server specialist for MCP development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

stack: [python, mcp, fastmcp]
phase: implementation
capabilities:
  - Tool registration patterns
  - Streaming architecture
  - Protocol testing
keywords: [mcp, fastmcp, python, claude-code, tools]
---

## Role
You are a FastMCP specialist...

## Boundaries
### ALWAYS
- ✅ Register tools in __main__.py
- ✅ Log to stderr only
...

## Capabilities
...

## References
...
```

**MCP Proposal**: No agents defined. The 10 critical patterns are documented in prose, not in agent format.

---

### Finding 6: Code Templates Not Defined

**Required template structure** (from fastapi-python):

```
templates/
├── server/__main__.py.template     # Tool registration
├── server/server.py.template       # FastMCP setup
├── tools/tool.py.template          # Tool implementation
├── resources/resource.py.template  # Resource definition
├── testing/conftest.py.template    # Test fixtures
└── testing/test_tool.py.template   # Tool test
```

Each template contains placeholders like `{{ToolName}}`, `{{ServerName}}`, `{{Description}}`.

**MCP Proposal**: Has inline code examples but not in template format with placeholders.

---

### Finding 7: Technical Patterns Are Excellent

Despite the template structure gaps, the **10 critical production patterns** from TASK-REV-MCP are excellent and should be preserved:

1. ✅ Use FastMCP, Not Custom Server Classes
2. ✅ Tool Registration in `__main__.py`
3. ✅ Logging to stderr
4. ✅ Streaming Tools Two-Layer Architecture
5. ✅ Error Handling for Streaming
6. ✅ MCP Parameter Type Conversion
7. ✅ Configuration with Absolute Paths
8. ✅ Timestamp Best Practices
9. ✅ Protocol Testing Commands
10. ✅ Docker Deployment Patterns

These should be translated into:
- Agent boundaries (ALWAYS/NEVER)
- Code templates with patterns embedded
- Rules in `.claude/rules/`

---

## Gap Analysis Summary

### Critical Gaps (Block template creation)

| Gap | Impact | Required Action |
|-----|--------|-----------------|
| No `manifest.json` | Template won't install | Create with full metadata |
| No `settings.json` | No naming conventions | Create with MCP conventions |
| No `agents/` directory | No specialist guidance | Create 2-3 MCP agents |
| No `templates/` directory | No code scaffolding | Create 6-8 code templates |

### Major Gaps (Degrade template quality)

| Gap | Impact | Required Action |
|-----|--------|-----------------|
| No `.claude/rules/` | No path-specific guidance | Create 3-5 rules files |
| No `.claude/CLAUDE.md` | No nested guidance | Create template CLAUDE.md |
| Patterns in prose | Not actionable for AI | Convert to agent format |

### Minor Gaps (Polish items)

| Gap | Impact | Required Action |
|-----|--------|-----------------|
| README format | Different from standard | Reformat to template README |
| Quality scores | Not defined | Calculate and document |

---

## Recommendations

### Recommendation 1: Do NOT Create Template from Current Proposal

**Decision**: The MCP proposal cannot be used directly to create a `fastmcp-python` template.

**Rationale**:
- Missing all 7 required template components
- Would require complete rewrite anyway
- Current proposal is valuable as *input* but not as *template structure*

---

### Recommendation 2: Create Proper Template Task

Create a new implementation task that:

1. **Uses TASK-REV-MCP patterns as input** (the 10 critical patterns)
2. **Follows fastapi-python as structural template** (copy structure)
3. **Generates all required components**:
   - `manifest.json` with MCP metadata
   - `settings.json` with MCP naming conventions
   - `agents/fastmcp-specialist.md` (core)
   - `agents/fastmcp-testing-specialist.md`
   - `templates/server/__main__.py.template`
   - `templates/tools/tool.py.template`
   - `.claude/rules/mcp-patterns.md`
   - `.claude/rules/testing.md`

---

### Recommendation 3: Template Naming Decision

**Options**:

| Name | Pros | Cons |
|------|------|------|
| `fastmcp-python` | Matches framework name | Might conflict with FastMCP project |
| `mcp-python` | Generic MCP support | Less specific |
| `mcp-server-python` | Clear purpose | Longer name |

**Recommendation**: `fastmcp-python` (follows `fastapi-python` convention)

---

### Recommendation 4: Template Scope

**Recommended Scope**:

| Component | Count | Rationale |
|-----------|-------|-----------|
| Agents | 3 | Core, Testing, Streaming specialist |
| Templates | 8 | Server, tools, resources, tests |
| Rules | 4 | Patterns, testing, config, docker |
| Complexity | 5 | Lower than fastapi (focused scope) |

**NOT in scope** (future templates):
- LangGraph integration (separate `langgraph-python` template)
- Multi-MCP orchestration (monorepo pattern)
- PM tool integration (specialized template)

---

## Decision Matrix

| Option | Effort | Value | Risk | Recommendation |
|--------|--------|-------|------|----------------|
| Accept MCP proposal as-is | Low | Low | High | **Not Recommended** |
| Revise MCP review recommendations | Medium | Medium | Low | Alternative |
| Create new template task from scratch | Medium | High | Low | **Recommended** |
| Create template + Requirements MCP | High | Very High | Medium | Stretch goal |

---

## Conclusion

**Primary Recommendation**: Create a new implementation task (not revision of TASK-REV-MCP) to build a proper `fastmcp-python` template following GuardKit conventions.

**Key Deliverables** (for new task):
1. `manifest.json` with MCP metadata
2. `settings.json` with MCP naming conventions
3. 3 agent files with embedded 10 critical patterns
4. 8 code templates with placeholders
5. `.claude/rules/` with 4 rules files
6. README.md following template standard
7. Quality validation with `/template-validate`

**TASK-REV-MCP Status**: The review contains valuable technical patterns but should be marked as "informational input" rather than "template specification". Its recommendations need translation to template format.

---

## Appendix A: Template Component Checklist

### manifest.json Required Fields

- [ ] `schema_version`: "1.0.0"
- [ ] `name`: "fastmcp-python"
- [ ] `display_name`: "FastMCP Python Server"
- [ ] `description`: Full description with patterns
- [ ] `version`: "1.0.0"
- [ ] `language`: "Python"
- [ ] `language_version`: ">=3.10"
- [ ] `frameworks`: FastMCP, mcp, pytest
- [ ] `architecture`: "MCP Server Pattern"
- [ ] `patterns`: All 10 critical patterns
- [ ] `layers`: tools, resources, server
- [ ] `placeholders`: ServerName, ToolName, etc.
- [ ] `tags`: python, mcp, fastmcp, claude-code
- [ ] `category`: "integration"
- [ ] `complexity`: 5
- [ ] `quality_scores`: SOLID, DRY, YAGNI, coverage

### settings.json Required Sections

- [ ] `naming_conventions`: tool, server, resource, test
- [ ] `file_organization`: by_feature
- [ ] `layer_mappings`: tools, resources, server
- [ ] `code_style`: PEP 8, type hints, async
- [ ] `testing`: pytest, protocol tests

### Agent Files Required

- [ ] `fastmcp-specialist.md`: Core MCP development
- [ ] `fastmcp-testing-specialist.md`: Protocol testing
- [ ] `fastmcp-streaming-specialist.md` (optional): Streaming patterns

### Template Files Required

- [ ] `server/__main__.py.template`
- [ ] `server/server.py.template`
- [ ] `tools/tool.py.template`
- [ ] `resources/resource.py.template`
- [ ] `config/pyproject.toml.template`
- [ ] `config/Dockerfile.template`
- [ ] `testing/conftest.py.template`
- [ ] `testing/test_tool.py.template`

---

## Appendix B: Files Analyzed

**From TASK-REV-MCP review**:
- `.claude/reviews/TASK-REV-MCP-review-report.md` (526 lines)

**GuardKit template comparison**:
- `installer/core/templates/fastapi-python/manifest.json`
- `installer/core/templates/fastapi-python/settings.json`
- `installer/core/templates/fastapi-python/agents/` (6 files)
- `installer/core/templates/fastapi-python/templates/` (8 directories)
- `installer/core/templates/fastapi-python/.claude/rules/` (10 files)
- `installer/core/templates/react-typescript/manifest.json`
- `docs/guides/template-philosophy.md`
