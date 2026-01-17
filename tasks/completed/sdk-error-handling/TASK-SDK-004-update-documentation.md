---
id: TASK-SDK-004
title: Document optional dependency installation
status: completed
created: 2026-01-06T15:35:00Z
updated: 2026-01-06T16:45:00Z
completed: 2026-01-06T16:45:00Z
priority: low
tags: [documentation, installation]
complexity: 2
parent_task: TASK-REV-SDK1
implementation_mode: direct
wave: 2
conductor_workspace: sdk-error-wave2-2
---

# Task: Document optional dependency installation

## Description

Update installation documentation to clearly explain the optional dependency pattern for AutoBuild features.

## Documentation Updates

### README.md

Add to installation section:

```markdown
## Installation

### Basic Installation

```bash
pip install guardkit-py
```

### With AutoBuild Support

AutoBuild (`/feature-build`, `guardkit autobuild`) requires the Claude Agent SDK:

```bash
pip install guardkit-py[autobuild]
```

### Development Installation

```bash
pip install guardkit-py[dev]      # Testing dependencies
pip install guardkit-py[all]      # Everything
```
```

### CLAUDE.md (Installation & Setup section)

Update to clarify:

```markdown
## Installation & Setup

```bash
# Install basic guardkit
pip install guardkit-py

# Install with AutoBuild support (required for /feature-build)
pip install guardkit-py[autobuild]

# Initialize with template
guardkit init [template-name]
```

**Note**: AutoBuild features (`/feature-build`, `guardkit autobuild`) require the optional `claude-agent-sdk` dependency. If you see "Claude Agent SDK not installed", run:

```bash
pip install guardkit-py[autobuild]
# OR
pip install claude-agent-sdk
```
```

## Files to Modify

- `README.md` - Add optional dependencies section
- `CLAUDE.md` - Update Installation & Setup section
- `docs/guides/guardkit-workflow.md` - Add note about AutoBuild requirements

## Acceptance Criteria

- [x] README.md explains basic vs autobuild installation
- [x] CLAUDE.md mentions autobuild optional dependency
- [x] guardkit-workflow.md notes AutoBuild requirements
- [x] All pip install commands are accurate

## Notes

- This is a documentation-only change
- No code modifications required
- Can be done as a direct edit (no formal task-work needed)
- Part of SDK Error Handling feature (TASK-REV-SDK1 recommendations)

## Implementation Summary

Updated three documentation files to explain optional dependency installation:

1. **README.md** - Added pip installation options with basic, autobuild, and dev extras
2. **CLAUDE.md** - Updated Installation & Setup section with all pip options and note about AutoBuild requirements
3. **docs/guides/guardkit-workflow.md** - Added Requirements section to AutoBuild Delegation explaining the dependency
