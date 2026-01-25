---
id: TASK-SDK-E02D
title: Review Claude Agents SDK installation in install.sh
status: review_complete
created: 2026-01-25T09:30:00Z
updated: 2026-01-25T11:00:00Z
priority: high
tags: [installation, sdk, claude-agents, review]
task_type: review
complexity: 3
review_results:
  mode: code-quality
  depth: standard
  score: 85
  findings_count: 1
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-SDK-E02D-review-report.md
  completed_at: 2026-01-25T11:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review Claude Agents SDK installation in install.sh

## Description

Review the `installer/scripts/install.sh` script to verify if we are correctly installing the Claude Agents SDK. If not installed, we need to add installation steps following the official documentation at https://platform.claude.com/docs/en/agent-sdk/python

## Current State Analysis

### What the script currently does:

1. **Python Package Installation** (lines 336-415):
   - Installs `guardkit[autobuild]` which includes `claude-agent-sdk` as an optional dependency
   - Uses `python3 -m pip install -e "$repo_root[autobuild]"`
   - Falls back to `--user` install if `--break-system-packages` fails

2. **Dependencies checked** (lines 159-334):
   - Python 3.10+ (required)
   - pip3 (recommended)
   - Jinja2 (installed if missing)
   - python-frontmatter (installed if missing)
   - pydantic (installed if missing)

3. **AutoBuild CLI availability** (lines 868-903):
   - Checks for `guardkit-py` command
   - Provides guidance if not found

### What may be missing:

1. **Direct SDK verification** - The script installs via `[autobuild]` extras but doesn't verify the SDK is actually importable
2. **SDK-specific environment variables** - May need `ANTHROPIC_API_KEY` configuration guidance
3. **Version verification** - No check for minimum SDK version compatibility

## Reference Documentation

Official Claude Agent SDK Python installation:
- URL: https://platform.claude.com/docs/en/agent-sdk/python
- Installation command: `pip install claude-agent-sdk`
- Requires: Python 3.10+

## Acceptance Criteria

- [x] Verify `claude-agent-sdk` is included in `pyproject.toml` under `[autobuild]` extras
- [x] Confirm install.sh correctly installs the SDK via extras
- [x] Add explicit SDK import verification after installation
- [x] Add guidance for API key configuration if not present
- [x] Document SDK version requirements

## Test Requirements

- [ ] Run install.sh and verify SDK is importable: `python3 -c "import claude_agent_sdk"`
- [ ] Verify `guardkit autobuild` command works after installation
- [ ] Test installation on clean environment

## Initial Findings

### pyproject.toml Analysis (CONFIRMED)

The `claude-agent-sdk` **IS correctly specified** in `pyproject.toml`:

```toml
[project.optional-dependencies]
autobuild = [
    "claude-agent-sdk>=0.1.0",
]
```

This means when `install.sh` runs:
```bash
python3 -m pip install -e "$repo_root[autobuild]"
```

It DOES install the Claude Agent SDK as an optional dependency.

### Potential Gaps Identified

1. **No explicit SDK import verification** - After installation, the script only checks:
   - `python3 -c "import guardkit"` (line 389)
   - Does NOT verify `claude_agent_sdk` is importable

2. **No API key guidance** - The script doesn't mention `ANTHROPIC_API_KEY` requirement

3. **Silent failure possible** - If SDK installation fails but guardkit succeeds, AutoBuild will fail at runtime

## Questions to Answer

1. ~~Is `claude-agent-sdk` correctly specified in pyproject.toml extras?~~ **YES - CONFIRMED**
2. Is the import verification sufficient (`python3 -c "import guardkit"`)?
3. Should we add explicit `claude_agent_sdk` import check?
4. Do we need to add API key setup guidance?

## Files to Review

- `installer/scripts/install.sh` - Main installation script
- `pyproject.toml` - Package dependencies and extras
- `src/guardkit/__init__.py` - Package initialization
- `src/guardkit/autobuild/` - AutoBuild module using the SDK

## Implementation Notes

If changes are needed, they should be made in the `install_python_package()` function around line 336.
