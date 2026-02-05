# Review Report: TASK-REV-2F28

## Executive Summary

The `guardkit init mcp-server-python` command failed to create MCP server files because **the template `mcp-server-python` does not exist**. The correct template name is `fastmcp-python`. The init system silently fell back to the `default` template, which only provides task workflow infrastructure - not MCP-specific files.

**Root Cause**: Template naming mismatch - user expected `mcp-server-python`, but the actual template is named `fastmcp-python`.

**Impact**: User got an empty project structure instead of a ready-to-use MCP server skeleton.

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Standard |
| **Duration** | ~15 minutes |
| **Reviewer** | architectural-reviewer |

## Findings

### Finding 1: Template Does Not Exist (ROOT CAUSE)

**Evidence** (from [init_1.md](../../docs/reviews/python-mcp/init_1.md):13):
```
⚠ Template 'mcp-server-python' not found, using default
```

The user ran `guardkit init mcp-server-python`, but this template name is not available.

### Finding 2: Available Templates

| Template | Description | Exists |
|----------|-------------|--------|
| `default` | Basic GuardKit structure | ✅ |
| `fastapi-python` | FastAPI REST API | ✅ |
| `fastmcp-python` | Python MCP server (FastMCP) | ✅ |
| `mcp-typescript` | TypeScript MCP server | ✅ |
| `react-typescript` | React + TypeScript | ✅ |
| `nextjs-fullstack` | Next.js fullstack | ✅ |
| `react-fastapi-monorepo` | React + FastAPI monorepo | ✅ |
| `mcp-server-python` | **DOES NOT EXIST** | ❌ |

### Finding 3: Silent Fallback to Default

**Evidence** ([init-project.sh:187-191](../../installer/scripts/init-project.sh#L187-L191)):
```bash
if [ ! -d "$template_dir" ]; then
    print_warning "Template '$effective_template' not found, using default"
    template_dir="$AGENTECFLOW_HOME/templates/default"
    effective_template="default"
fi
```

The script shows a warning but continues execution. Combined with success messages like "✓ Copied template files", this creates a misleading impression that the command succeeded.

### Finding 4: Naming Convention Inconsistency

| TypeScript Pattern | Python Pattern | Issue |
|--------------------|----------------|-------|
| `mcp-typescript` | `fastmcp-python` | Inconsistent naming |

The TypeScript template uses the generic `mcp-typescript` name, but the Python template emphasizes the framework (`fastmcp-python`). A user naturally trying `mcp-server-python` or `mcp-python` would fail.

### Finding 5: User Experience Issues

1. **No Template List**: User must guess or know template names
2. **No Suggestion**: When template not found, system doesn't suggest similar names
3. **False Success**: Output shows green checkmarks even when using fallback

## Recommendations

### Recommendation 1: Add Template Alias (Recommended)

**Impact**: High | **Effort**: Low

Create an alias so `mcp-server-python` maps to `fastmcp-python`. This is the fastest fix with minimal risk.

**Implementation**:
```bash
# In init-project.sh
case "$effective_template" in
    "mcp-server-python"|"mcp-python")
        effective_template="fastmcp-python"
        print_info "Template alias: using 'fastmcp-python'"
        ;;
esac
```

### Recommendation 2: Improve Error Handling

**Impact**: High | **Effort**: Medium

When template not found:
1. Show error (not warning) with clear message
2. List available templates
3. Suggest closest match (fuzzy matching)
4. Require explicit `--force-default` to continue with default

**Example UX**:
```
❌ Template 'mcp-server-python' not found.

Available templates:
  - fastmcp-python (Python MCP server)
  - mcp-typescript (TypeScript MCP server)
  - fastapi-python (FastAPI REST API)
  - react-typescript (React frontend)
  - nextjs-fullstack (Next.js fullstack)
  - default (basic structure)

Did you mean: fastmcp-python?

Use 'guardkit init --list' to see all templates.
```

### Recommendation 3: Add `--list` Flag

**Impact**: Medium | **Effort**: Low

Add `guardkit init --list` to show available templates with descriptions.

### Recommendation 4: Standardize Template Naming

**Impact**: Low | **Effort**: Medium

Consider renaming for consistency:
- `fastmcp-python` → `mcp-python` (with `fastmcp-python` as alias)
- Or keep both names as aliases

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| **1. Add alias (`mcp-server-python` → `fastmcp-python`)** | 9/10 | Low | Low | **Recommended - Quick fix** |
| 2. Improve error handling | 8/10 | Medium | Low | Should do |
| 3. Add `--list` flag | 6/10 | Low | Low | Nice to have |
| 4. Standardize naming | 5/10 | Medium | Medium | Consider for future |

## User's Immediate Solution

Run the correct command:
```bash
guardkit init fastmcp-python
```

This will initialize a Python MCP server project with:
- FastMCP framework setup
- 10 critical MCP patterns embedded
- Test infrastructure
- Docker deployment ready
- Complete documentation

## Next Steps (If [I]mplement Chosen)

1. **TASK-INIT-001**: Add template alias mapping in `init-project.sh`
2. **TASK-INIT-002**: Improve error messaging when template not found
3. **TASK-INIT-003**: Add `guardkit init --list` command

## Appendix

### Files Reviewed

- [docs/reviews/python-mcp/init_1.md](../../docs/reviews/python-mcp/init_1.md) - User's init output
- [installer/scripts/init-project.sh](../../installer/scripts/init-project.sh) - Init script
- [guardkit/cli/init.py](../../guardkit/cli/init.py) - Python CLI init command
- `~/.agentecflow/templates/` - Installed templates directory
- [~/.agentecflow/templates/fastmcp-python/README.md](../../installer/core/templates/fastmcp-python/README.md) - FastMCP template docs

### Template Validation

The `fastmcp-python` template is well-documented and contains:
- 10 critical MCP patterns
- Complete test infrastructure
- Docker deployment support
- Comprehensive documentation

**Template Quality Score**: 9/10 (High quality, well-maintained)

---

**Review Generated**: 2026-02-03
**Task ID**: TASK-REV-2F28
