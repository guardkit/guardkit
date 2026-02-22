---
id: TASK-FIX-LI07
title: Fix post-install summary agent count undercount and add missing template descriptions
status: completed
created: 2026-02-22T14:20:00Z
updated: 2026-02-22T15:05:00Z
completed: 2026-02-22T15:05:00Z
priority: normal
tags: [installer, ux, post-install-summary, agents, templates, print-summary]
task_type: bug-fix
complexity: 1
parent_review: TASK-REV-LI03
---

# Task: Fix post-install summary agent count undercount and add missing template descriptions

## Description

`print_summary()` in `installer/scripts/install.sh` contains two display inaccuracies first visible in install 3:

1. **Agent count** reports `30` but `62` agents were installed — the glob used only finds top-level `.md` files, missing 32 stack-specific agents in subdirectories
2. **Template descriptions** for `fastmcp-python` and `mcp-typescript` are absent — these templates were added after the `case` statement was written

Both are in `print_summary()` and are 1-3 line fixes each.

**File**: `installer/scripts/install.sh`
**Function**: `print_summary()` (~lines 1504-1587)
**Evidence**: `docs/reviews/linux_install/linux_install_3.md` lines 299 (agent count), 313-314 (template descriptions)
**Review**: `tasks/backlog/TASK-REV-LI03-linux-install-3-analysis.md` Issues 2 & 3

---

## Issue A — Agent count uses shallow glob, misses stack-specific subdirectories

**Symptom** (install 3, line 299):

```
🤖 AI Agents: 30 (including clarification-questioner)
```

Install step (line 138) says:

```
✓ Installed 62 total agents (30 global + 32 stack-specific)
```

**Root cause** in `print_summary()`:

```bash
local agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
```

`ls "$INSTALL_DIR/agents/"*.md` only matches `.md` files directly inside `agents/`. Stack-specific agents are stored in subdirectories (`agents/react-typescript/`, `agents/fastapi-python/`, etc.) and are excluded by the shallow glob.

**Fix** — replace with `find`:

```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

---

## Issue B — `fastmcp-python` and `mcp-typescript` templates missing descriptions

**Symptom** (install 3, lines 313-314):

```
• fastmcp-python
• mcp-typescript
```

All other templates have a rating/description appended (e.g., `• fastapi-python - FastAPI backend with layered architecture (9+/10)`).

**Root cause**: The `case` statement in `print_summary()` has no entries for these two templates, so they fall through to `echo "  • $name"`.

**Fix** — add two `case` entries, using descriptions from the template manifests:

From `installer/core/templates/fastmcp-python/manifest.json`:
- `display_name`: `"FastMCP Python Server"`
- `description`: `"Production-ready FastMCP template implementing 10 critical patterns for building MCP servers. Features tool registration, resource management, and async patterns based on Model Context Protocol best practices."`

From `installer/core/templates/mcp-typescript/manifest.json`:
- `display_name`: `"MCP TypeScript Server"`
- `description`: `"Production-ready MCP server template using @modelcontextprotocol/sdk with TypeScript. Implements all 10 critical production patterns including stderr logging, tool registration, streaming architecture, Zod validation, and Docker deployment."`

Suggested concise summary lines (to match the style of existing entries):

```bash
fastmcp-python)
    echo "  • $name - FastMCP Python server with tool registration and async patterns"
    ;;
mcp-typescript)
    echo "  • $name - MCP TypeScript server with @modelcontextprotocol/sdk and Zod validation"
    ;;
```

---

## Acceptance Criteria

- [ ] Post-install summary shows the correct total agent count (e.g. `62`) rather than only the 30 global agents
- [ ] `fastmcp-python` and `mcp-typescript` are listed with descriptions matching their manifest display_name/purpose
- [ ] All existing template descriptions are unchanged (no regression)
- [ ] If a new template is added in future, it still falls through to `echo "  • $name"` gracefully (the `*)` catch-all remains)

## Implementation Notes

Both fixes are in `print_summary()`. Make them as a single commit.

**Agent count fix** — find the line:
```bash
local agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
```
Replace with:
```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

**Template description fix** — in the `case "$name" in` block, add before the `*)` catch-all:
```bash
fastmcp-python)
    echo "  • $name - FastMCP Python server with tool registration and async patterns"
    ;;
mcp-typescript)
    echo "  • $name - MCP TypeScript server with @modelcontextprotocol/sdk and Zod validation"
    ;;
```

## Test Requirements

- [ ] After fix, post-install summary shows `AI Agents: 62` (or the actual installed count from `find`)
- [ ] After fix, `fastmcp-python` and `mcp-typescript` lines include their descriptions
- [ ] Run install with a future hypothetical new template not in the case statement — confirm it still prints gracefully as `• template-name` via the `*)` catch-all
- [ ] `command_count` and `template_count` counts in the summary are unaffected

## Related

- Review: `tasks/backlog/TASK-REV-LI03-linux-install-3-analysis.md` Issues 2 & 3
- Evidence: `docs/reviews/linux_install/linux_install_3.md` lines 299, 313-314
- Template manifests: `installer/core/templates/fastmcp-python/manifest.json`, `installer/core/templates/mcp-typescript/manifest.json`
- Installer: `installer/scripts/install.sh` — `print_summary()` (~lines 1504-1587)
- Companion fix: `tasks/backlog/TASK-FIX-LI06-cli-path-false-alarm-warning.md`
