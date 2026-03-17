# Review Report: TASK-REV-4219

## Executive Summary

Graphiti was reported unavailable during a `/system-arch` session on agentic-dataset-factory despite all infrastructure (FalkorDB, vLLM LLM, vLLM embeddings) being healthy. The root cause is a Python environment mismatch: the `graphiti_check.py` script's shebang resolves to system Python which lacks `graphiti-core`. A secondary issue is a missing execute permission on the symlink target.

**Recommended fix: Option B (wrapper script)** — with a refinement. The installer should generate a bash wrapper at `~/.agentecflow/bin/graphiti-check` that explicitly invokes the guardkit venv Python. This follows the existing pattern used for `agentic-init` in `install-global.sh`.

However, a critical finding is that **the symlink/wrapper may not be the primary invocation path**. The `task-work.md` command spec and `graphiti-knowledge.md` rules both instruct Claude Code to use `python -m installer.core.commands.lib.graphiti_check`, not the `graphiti-check` CLI symlink. This means the fix must also ensure the `python` used for module invocation resolves to the guardkit venv.

## Review Details

- **Mode**: Architectural / Decision Analysis
- **Depth**: Standard
- **Task**: TASK-REV-4219
- **Source**: `docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md`

## Root Cause Analysis

### Primary Issue

`graphiti_check.py` line 1 contains `#!/usr/bin/env python3`. When invoked as a CLI script (via the `~/.agentecflow/bin/graphiti-check` symlink), `env` resolves `python3` to the **system Python**, which does not have `graphiti-core` installed.

The `graphiti-core` library IS installed in:
- GuardKit venv (`guardkit/.venv/`) — Python 3.14
- Graphiti MCP server venv (`graphiti/mcp_server/.venv/`) — Python 3.10
- uv cache (`~/.cache/uv/archive-v0/`)

But NOT in:
- System Python (`/usr/bin/python3` or Homebrew Python)

### Secondary Issue

The symlink target `graphiti_check.py` has permissions `-rw-r--r--` (not executable). When called directly as `graphiti-check`, the shell cannot execute it even if the shebang were correct.

### Invocation Path Analysis

There are **two distinct invocation paths** for this script:

| Path | Used By | How It Works | Affected? |
|------|---------|--------------|-----------|
| `~/.agentecflow/bin/graphiti-check` (symlink) | Unknown/legacy | Symlink → `.py` file, uses shebang | YES — both shebang and permissions broken |
| `python -m installer.core.commands.lib.graphiti_check` | `task-work.md`, `graphiti-knowledge.md` rules | Module invocation, uses whatever `python` resolves to | YES — if `python` resolves to system Python |

The `/system-arch` command likely failed via one of these paths. The key insight is that **both paths** have the same fundamental problem: they depend on the ambient `python3`/`python` resolving to an environment with `graphiti-core`.

## Fix Options Evaluation

### Option A: Fix Shebang to Use GuardKit Venv

**Approach**: Replace `#!/usr/bin/env python3` with `#!/path/to/guardkit/.venv/bin/python`

| Criterion | Assessment |
|-----------|------------|
| Correctness | Fixes CLI symlink path only |
| Robustness | **Fragile** — hardcoded path breaks if venv moves or is recreated |
| Scope | Does NOT fix `python -m` invocation path |
| Existing installs | Requires manual edit or reinstall |
| Complexity | Trivial |

**Verdict**: Insufficient — only fixes one of two invocation paths, and fragile.

### Option B: Installer Creates Wrapper Script (Recommended)

**Approach**: Replace symlink with a generated bash wrapper that explicitly uses guardkit venv Python.

```bash
#!/usr/bin/env bash
exec /path/to/guardkit/.venv/bin/python /path/to/graphiti_check.py "$@"
```

| Criterion | Assessment |
|-----------|------------|
| Correctness | Fixes CLI invocation path completely |
| Robustness | **Good** — path written at install time, follows existing `agentic-init` pattern |
| Scope | Fixes CLI path; does NOT fix `python -m` path |
| Existing installs | Requires reinstall (`guardkit init` or `install.sh`) |
| Complexity | Low — pattern already exists in `install-global.sh` |
| Execute permission | **Solved** — wrapper is a new file with `chmod +x` |

**Verdict**: Good for the CLI path. Must be combined with a fix for the module invocation path.

### Option C: Install graphiti-core into System Python

**Approach**: `pip3 install graphiti-core[falkordb]` into system Python.

| Criterion | Assessment |
|-----------|------------|
| Correctness | Fixes both invocation paths if system Python is what resolves |
| Robustness | **Poor** — pollutes system Python, breaks on OS upgrade, PEP 668 managed env conflicts |
| Scope | Fixes all paths where system Python is used |
| Existing installs | Manual action per machine |
| Complexity | Trivial |

**Note**: The current `install.sh` already attempts this (lines 355-385) with `--break-system-packages` and `--user` fallbacks. The fact that graphiti-core is NOT in the system Python suggests this step either failed silently or was skipped.

**Verdict**: Already attempted by installer. Not reliable as sole fix. The PEP 668 externally-managed-environment restriction on modern Python makes this increasingly fragile.

### Option D: Configure Claude Code to Use GuardKit Venv Python

**Approach**: Configure Claude Code to use the guardkit venv Python for tool script execution.

| Criterion | Assessment |
|-----------|------------|
| Correctness | Would fix module invocation path |
| Robustness | Depends on Claude Code configuration capabilities |
| Scope | Only affects Claude Code invocation context |
| Existing installs | Configuration change only |
| Complexity | **Unknown** — may not be configurable |

**Verdict**: Speculative. Claude Code's Python resolution is not easily configurable. The `python -m` path in command specs assumes the current `python` has the right packages.

## Recommended Approach

### Combined Fix: Option B + Enhanced Installer + Command Spec Update

The fix requires addressing **both** invocation paths:

#### Fix 1: Wrapper Script (Option B) — for CLI path

The installer should generate `~/.agentecflow/bin/graphiti-check` as a bash wrapper (not a symlink):

```bash
#!/usr/bin/env bash
# Generated by guardkit installer — do not edit
GUARDKIT_VENV="/path/to/guardkit/.venv"
exec "$GUARDKIT_VENV/bin/python" -m installer.core.commands.lib.graphiti_check "$@"
```

This follows the established pattern from `install-global.sh` lines 132-193 (`agentic-init` wrapper).

#### Fix 2: Update Command Specs — for module invocation path

Update `task-work.md` and `graphiti-knowledge.md` to use the guardkit venv Python explicitly:

**Before**:
```bash
python -m installer.core.commands.lib.graphiti_check --status --quiet
```

**After**:
```bash
/path/to/guardkit/.venv/bin/python -m installer.core.commands.lib.graphiti_check --status --quiet
```

Or better, use the wrapper:
```bash
graphiti-check --status --quiet
```

This ensures Claude Code calls the correct Python regardless of ambient environment.

#### Fix 3: Harden the Installer — for existing install resilience

The installer's existing attempt to install `graphiti-core` into system Python (install.sh lines 355-385) should be audited:
- Add `set -e` error checking to confirm success
- Log the actual Python path being used
- Verify the import actually works after installation

#### Fix 4: Execute Permission

```bash
chmod +x installer/core/commands/lib/graphiti_check.py
```

This is a one-line fix that should be done regardless of other changes.

### Implementation Priority

| Fix | Priority | Effort | Impact |
|-----|----------|--------|--------|
| Fix 4: chmod +x | P0 | 1 min | Unblocks symlink path |
| Fix 1: Wrapper script | P1 | 1-2 hours | Correct CLI invocation |
| Fix 2: Command spec update | P1 | 30 min | Correct module invocation |
| Fix 3: Installer hardening | P2 | 1-2 hours | Prevents recurrence |

## Impact on Existing Installations

| Scenario | Impact | Remediation |
|----------|--------|-------------|
| New installations | No impact — wrapper generated at install time | N/A |
| Existing installations with working Graphiti | No impact — system Python happens to have graphiti-core | Reinstall upgrades symlink to wrapper |
| Existing installations with broken Graphiti | **This is the current bug** | Reinstall required, or manual wrapper creation |
| Installations without Graphiti configured | No impact — graphiti-check not called | N/A |

## Retroactive Seeding

After the fix is applied, the agentic-dataset-factory architecture artefacts should be retroactively seeded:

```bash
guardkit graphiti seed --force
```

This will seed:
- System context from `ARCHITECTURE.md`
- 6 modules/components
- 9 ADRs (`decisions/ADR-ARCH-*.md`)
- 10 assumptions (`assumptions.yaml`)
- Cross-cutting concerns

The `--force` flag is needed to re-seed even though `.guardkit/seeding/.system_seeded.json` exists from a prior (partial?) seeding.

## Decision Matrix

| Option | Correctness | Robustness | Scope | Effort | Recommendation |
|--------|-------------|------------|-------|--------|----------------|
| A: Fix shebang | Partial | Fragile | CLI only | Trivial | Not recommended |
| B: Wrapper script | Full (CLI) | Good | CLI only | Low | **Recommended** (combined) |
| C: System pip | Full | Poor | Both paths | Trivial | Not recommended |
| D: Claude Code config | Unknown | Unknown | Module only | Unknown | Not feasible |
| **B+Spec update** | **Full** | **Good** | **Both paths** | **Low-Medium** | **Best option** |

## Implementation Tasks

1. **TASK-FIX-GC01**: Add execute permission to `graphiti_check.py` and update installer to generate wrapper script instead of symlink
2. **TASK-FIX-GC02**: Update command specs (`task-work.md`, `graphiti-knowledge.md`) to use wrapper or explicit venv Python path
3. **TASK-FIX-GC03**: Harden installer's graphiti-core installation step with proper error checking
4. **TASK-SEED-ADF**: Retroactively seed agentic-dataset-factory architecture artefacts after fix is deployed

## Appendix

### Files Examined

- `installer/core/commands/lib/graphiti_check.py` — Script with broken shebang
- `installer/scripts/install.sh` — Installer (lines 355-385: graphiti-core install attempt)
- `installer/core/commands/task-work.md` — Command spec using `python -m` invocation
- `.claude/rules/graphiti-knowledge.md` — Rules referencing `python -m` invocation
- `docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md` — Incident report

### Invocation Path Diagram

```
Claude Code session
  │
  ├─ /system-arch command
  │    └─ Calls get_graphiti() or graphiti-check
  │         │
  │         ├─ PATH A: ~/.agentecflow/bin/graphiti-check (symlink)
  │         │    └─ graphiti_check.py (not executable, shebang → system python)
  │         │         └─ import graphiti_core → ModuleNotFoundError ✗
  │         │
  │         └─ PATH B: python -m installer.core.commands.lib.graphiti_check
  │              └─ "python" resolves to system python
  │                   └─ import graphiti_core → ModuleNotFoundError ✗
  │
  └─ Result: "Graphiti unavailable" warning, artefacts not seeded
```
