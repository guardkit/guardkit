# Review: Graphiti Unavailable During /system-arch Session

**Date:** 2026-03-17
**Project:** agentic-dataset-factory
**Command:** `/system-arch`
**Severity:** Medium — architecture artefacts generated successfully but not seeded to Graphiti

## Summary

During a `/system-arch` session on agentic-dataset-factory, Graphiti was reported as unavailable despite all infrastructure being healthy. The root cause is that `graphiti-core` is not installed in the Python environment used by Claude Code's tool scripts.

## Symptom

The `/system-arch` command proceeded without Graphiti persistence:
```
WARNING: Graphiti unavailable — architecture definition will continue WITHOUT persistence.
Markdown artefacts will still be generated in docs/architecture/.
```

9 ADRs, C4 diagrams, domain model, and assumptions were generated as markdown but NOT seeded to the Graphiti knowledge graph.

## Root Cause

The `graphiti-check` script (`~/.agentecflow/bin/graphiti-check`) uses `#!/usr/bin/env python3` which resolves to the **system Python**. The system Python does **not** have `graphiti-core` installed.

```
$ python3 /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib/graphiti_check.py
{"available": false, "error": "graphiti-core not installed", ...}
```

## Infrastructure Status (All Healthy)

All three Graphiti dependencies were verified as running and reachable at the time of the failure:

| Component | Host | Port | Status |
|-----------|------|------|--------|
| FalkorDB | whitestocks (100.92.74.2 via Tailscale) | 6379 | Port open, accepting connections |
| vLLM LLM server | promaxgb10-41b1 (100.84.90.91) | 8000 | Running, serving `claude-sonnet-4-6` (Qwen3-Coder-Next-FP8) |
| vLLM embedding server | promaxgb10-41b1 | 8001 | Running, serving `nomic-embed-text-v1.5` |

## Graphiti Configuration (Correct)

`.guardkit/graphiti.yaml` in agentic-dataset-factory is correctly configured:
```yaml
project_id: agentic-dataset-factory
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

System seeding had previously completed successfully (`.guardkit/seeding/.system_seeded.json` present).

## Where graphiti-core IS Installed

| Location | Python Version | Has graphiti-core | Has redis |
|----------|---------------|-------------------|-----------|
| System Python (`/usr/bin/python3` or Homebrew) | 3.x | NO | NO |
| GuardKit venv (`guardkit/.venv/`) | 3.14 | YES | YES |
| Graphiti MCP server venv (`graphiti/mcp_server/.venv/`) | 3.10 | YES | — |
| uv cache (`~/.cache/uv/archive-v0/`) | — | YES (cached) | — |

## Secondary Issue: Symlink Permission

The `graphiti-check` symlink target lacks execute permission:

```
$ ls -la ~/.agentecflow/bin/graphiti-check
lrwxr-xr-x  graphiti-check -> .../guardkit/installer/core/commands/lib/graphiti_check.py

$ ls -la .../guardkit/installer/core/commands/lib/graphiti_check.py
-rw-r--r--  graphiti_check.py    # <-- not executable
```

The script works when invoked as `python3 graphiti_check.py` but fails when called directly as `graphiti-check` because the symlink target is not executable.

## Fix Options

### Option A: Fix the shebang to use guardkit venv (Quick but fragile)

Update `graphiti_check.py` shebang to use the guardkit venv Python, or have the installer resolve the correct Python at install time:

```python
#!/Users/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python
```

**Pro:** Correct — guardkit tools should use the guardkit environment where their dependencies live.
**Con:** Fragile if the venv path changes. Could be solved by having the installer write the shebang dynamically.

### Option B: Installer creates a wrapper script (Recommended)

Instead of symlinking directly to the `.py` file, the installer writes a shell wrapper:

```bash
#!/usr/bin/env bash
exec /path/to/guardkit/.venv/bin/python /path/to/graphiti_check.py "$@"
```

**Pro:** Explicit Python resolution, survives path changes better, fixes the execute permission issue.
**Con:** Extra indirection.

### Option C: Install graphiti-core into system Python

```bash
pip3 install graphiti-core[falkordb]
```

**Pro:** Quickest fix.
**Con:** Pollutes system Python, may conflict with other projects, not reproducible.

### Option D: Claude Code configuration

Configure Claude Code to use the guardkit venv Python for tool scripts. This may not be configurable.

## Recommended Fix

**Option B** — have the guardkit installer generate wrapper scripts that explicitly invoke the guardkit venv Python. This also fixes the execute permission issue since the wrapper would be a new file with correct permissions.

Additionally, fix the execute permission on `graphiti_check.py`:
```bash
chmod +x installer/core/commands/lib/graphiti_check.py
```

## Impact

- `/system-arch` completed successfully — all markdown artefacts were generated
- Architecture context is NOT in Graphiti — `/system-design`, `/system-plan`, and `/feature-spec` will not have Graphiti-backed context for this project until retroactively seeded
- Once fixed, the architecture artefacts can be retroactively seeded to Graphiti

## Retroactive Seeding

After the fix, the architecture artefacts in `agentic-dataset-factory/docs/architecture/` should be seeded to Graphiti to restore the intended state. The following groups should be populated:

| Entity Type | Graphiti Group | Source File |
|-------------|---------------|-------------|
| System context | `project_architecture` | `ARCHITECTURE.md` |
| 6 modules/components | `project_architecture` | `ARCHITECTURE.md`, `domain-model.md` |
| 9 ADRs | `project_decisions` | `decisions/ADR-ARCH-*.md` |
| 10 assumptions | `project_architecture` | `assumptions.yaml` |
| Cross-cutting concerns | `project_architecture` | `ARCHITECTURE.md` |

## Reproduction Steps

1. Open a Claude Code session in any project with `.guardkit/graphiti.yaml` configured
2. Run any command that calls `get_graphiti()` (e.g. `/system-arch`)
3. Observe "Graphiti unavailable" warning
4. Verify with: `python3 -c "import graphiti_core"` → `ModuleNotFoundError`
5. Verify guardkit venv has it: `/path/to/guardkit/.venv/bin/python -c "import graphiti_core"` → success
