# Template Spec: python-library
# GuardKit workflow: /template-create --name python-library --path <source_repo>
# Then: /agent-enhance on generated specialist agents

## What This Is

A GuardKit project template for standalone Python library packages — importable,
pip-installable packages with no web server, no MCP layer, no agent runtime.

## Source Repo

**`youtube-transcript-mcp`** — `/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp`

This is the definitive source. It is the most recent, most complete Python project
in the workspace, built via AutoBuild, integration-tested, and already following
all the right patterns. The youtube-insights-mcp project was bootstrapped FROM
this template concept — so it is the natural exemplar.

Key patterns `/template-create` will extract from it:
- hatchling build backend with `pyproject.toml`
- `src/{package_name}/` layout
- `pytest` with `asyncio_mode = "auto"`, `not integration` default gate
- Markers: `slow`, `integration`, `seam`, `integration_contract`
- `ruff` with `select = ["E", "F", "W", "I", "N", "UP"]`, line-length 100
- `mypy` strict
- `FastMCP` / `asyncio` patterns (for the MCP server aspect — extract async patterns only)
- conftest.py factory function pattern (mock data classes + factory functions, not fixtures)
- stderr-only logging, no print()
- `from __future__ import annotations` on all modules

## How to Run

From the guardkit repo in Claude Code:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
/template-create --name python-library --path /Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp
```

## Post-Creation Enhancements

After `/template-create` generates the template, these additions/corrections should
be applied manually or via a follow-up task:

### 1. Add py.typed marker
The template should include `py.typed` as a required file in the package root.
This is PEP 561 — signals to mypy and IDEs that the library is fully typed.
Without it, consumers of the library lose type-checking value.

Add to manifest.json patterns:
```
"py.typed PEP 561 marker (empty file in package root)"
```

Add to CLAUDE.md ALWAYS rules:
```
- Add `py.typed` (empty file) to the package directory — required for PEP 561
```

### 2. Remove MCP-specific patterns
The source repo is an MCP server. The template should strip:
- `mcp>=1.0.0` from dependencies
- FastMCP-specific agent boundaries (stdout reserved for MCP protocol, etc.)
- MCP tool registration patterns

The template is for general Python libraries, not MCP servers.
The `fastmcp-python` template already covers MCP servers.

### 3. Add _internal/ convention
Add to CLAUDE.md:
```
- Prefix private implementation modules with _ (e.g. _internal/, _utils.py)
- Never import from _internal/ in public-facing modules without explicit re-export
```

### 4. Update manifest category
Set `"category": "library"` (not `"integration"` which is used for MCP servers).

### 5. Agent enhancement
After template creation, run `/agent-enhance` on each generated specialist agent
to lift from generic 6/10 to project-specific 9/10 boundaries.

Focus especially on:
- `python-library-specialist` — public API discipline, py.typed, backwards compat
- `python-testing-specialist` — integration marker discipline, factory function pattern

## Template Name and Location

- **Template name:** `python-library`
- **Display name:** `Python Library Package`
- **Install location:** `installer/core/templates/python-library/`

## Primary Use Cases (context for agent enhancement)

- `youtube-channel-intelligence` — YouTube Data API wrapper, outlier scoring, SQLite
- `nats-core` (Ship's Computer) — shared Pydantic schemas and NATS client utilities
- Any shared Python package pip-installed by multiple repos in the ecosystem

## Success Criteria

- `guardkit template-validate python-library` passes
- A project bootstrapped with `guardkit init python-library` installs cleanly
- `pytest` runs with zero network calls
- `ruff check .` and `mypy src/` pass clean on a bootstrapped project
- `py.typed` exists in the generated package root
- No MCP-specific content in manifest, CLAUDE.md, or agent files
