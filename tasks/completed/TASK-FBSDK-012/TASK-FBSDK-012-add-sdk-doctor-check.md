---
id: TASK-FBSDK-012
title: Add SDK doctor check to guardkit doctor command
status: completed
created: 2026-01-19T18:30:00Z
updated: 2026-01-19T21:30:00Z
completed: 2026-01-19T21:30:00Z
priority: medium
tags: [feature-build, sdk-integration, diagnostics, doctor]
complexity: 4
parent_review: TASK-REV-FB17
wave: 2
implementation_mode: task-work
depends_on:
  - TASK-FBSDK-010
code_review_score: 8.5/10
architectural_review_score: 72/100
test_coverage: 90%
tests_passed: 68/68
completed_location: tasks/completed/TASK-FBSDK-012/
---

# TASK-FBSDK-012: Add SDK Doctor Check

## Problem Statement

Feature-build failures can occur due to environment issues:
- Claude Code CLI not installed or not in PATH
- API authentication not configured
- SDK package not installed
- SDK can't connect to Claude API

These environment issues cause immediate failure but are difficult to diagnose without running a full feature-build.

## Solution

Add a `--check=sdk` option to `guardkit doctor` that verifies all SDK prerequisites before running feature-build.

## Implementation

### Step 1: Add SDK Check Function

Create new file or add to existing doctor module:

```python
# guardkit/cli/doctor_checks.py

import shutil
import subprocess
from typing import List, Tuple

def check_sdk_prerequisites() -> List[Tuple[str, bool, str]]:
    """Check all SDK prerequisites.

    Returns:
        List of (check_name, passed, message) tuples
    """
    results = []

    # Check 1: Claude Code CLI in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        results.append(("Claude Code CLI", True, f"Found at {claude_path}"))
    else:
        results.append(("Claude Code CLI", False,
            "Not found. Install: npm install -g @anthropic-ai/claude-code"))

    # Check 2: Claude Code version
    if claude_path:
        try:
            version = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version.returncode == 0:
                results.append(("Claude Code version", True, version.stdout.strip()))
            else:
                results.append(("Claude Code version", False, version.stderr.strip()))
        except Exception as e:
            results.append(("Claude Code version", False, str(e)))

    # Check 3: SDK package installed
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
        results.append(("claude-agent-sdk package", True, "Installed"))
    except ImportError:
        results.append(("claude-agent-sdk package", False,
            "Not installed. Run: pip install claude-agent-sdk"))

    # Check 4: API authentication
    # Check for ANTHROPIC_API_KEY or Claude Code auth
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        # Mask key for display
        masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        results.append(("API Key (env)", True, f"ANTHROPIC_API_KEY set ({masked})"))
    else:
        # Check Claude Code auth file
        auth_file = Path.home() / ".claude" / "auth.json"
        if auth_file.exists():
            results.append(("API Key (Claude Code)", True, "Claude Code authenticated"))
        else:
            results.append(("API Key", False,
                "Not found. Set ANTHROPIC_API_KEY or run: claude auth"))

    return results


async def check_sdk_connectivity() -> Tuple[bool, str]:
    """Test SDK can execute a trivial query.

    Returns:
        (passed, message) tuple
    """
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions

        # Simple query that should complete quickly
        async for message in query(
            prompt="Say 'SDK OK' and nothing else.",
            options=ClaudeAgentOptions(
                max_turns=1,
                allowed_tools=[],  # No tools needed
            )
        ):
            pass

        return True, "SDK connectivity verified"

    except Exception as e:
        return False, f"SDK connectivity failed: {type(e).__name__}: {e}"
```

### Step 2: Add to Doctor Command

Update `guardkit/cli/doctor.py`:

```python
import asyncio
import click
from guardkit.cli.doctor_checks import check_sdk_prerequisites, check_sdk_connectivity

@click.command()
@click.option("--check", type=click.Choice(["all", "sdk", "paths", "symlinks"]),
              default="all", help="Specific check to run")
@click.option("--connectivity/--no-connectivity", default=False,
              help="Test SDK connectivity (makes API call)")
def doctor(check: str, connectivity: bool):
    """Diagnose GuardKit installation and environment."""

    if check in ["all", "sdk"]:
        click.echo("\n=== SDK Prerequisites ===\n")

        results = check_sdk_prerequisites()
        all_passed = True

        for name, passed, message in results:
            status = click.style("✓", fg="green") if passed else click.style("✗", fg="red")
            click.echo(f"  {status} {name}: {message}")
            if not passed:
                all_passed = False

        if connectivity:
            click.echo("\n=== SDK Connectivity ===\n")
            passed, message = asyncio.run(check_sdk_connectivity())
            status = click.style("✓", fg="green") if passed else click.style("✗", fg="red")
            click.echo(f"  {status} {message}")
            if not passed:
                all_passed = False

        if all_passed:
            click.echo(click.style("\n✓ SDK checks passed", fg="green"))
        else:
            click.echo(click.style("\n✗ SDK checks failed", fg="red"))
            raise SystemExit(1)
```

### Step 3: Update CLI Help

```
$ guardkit doctor --help

Usage: guardkit doctor [OPTIONS]

  Diagnose GuardKit installation and environment.

Options:
  --check [all|sdk|paths|symlinks]  Specific check to run  [default: all]
  --connectivity / --no-connectivity
                                    Test SDK connectivity (makes API call)
  --help                            Show this message and exit.
```

## Usage Examples

```bash
# Quick SDK check (no API call)
guardkit doctor --check=sdk

# Full SDK check with connectivity test
guardkit doctor --check=sdk --connectivity

# All checks
guardkit doctor
```

## Expected Output

```
=== SDK Prerequisites ===

  ✓ Claude Code CLI: Found at /usr/local/bin/claude
  ✓ Claude Code version: claude 1.2.3
  ✓ claude-agent-sdk package: Installed
  ✓ API Key (Claude Code): Claude Code authenticated

=== SDK Connectivity ===

  ✓ SDK connectivity verified

✓ SDK checks passed
```

Or on failure:

```
=== SDK Prerequisites ===

  ✗ Claude Code CLI: Not found. Install: npm install -g @anthropic-ai/claude-code
  ✗ claude-agent-sdk package: Not installed. Run: pip install claude-agent-sdk
  ✗ API Key: Not found. Set ANTHROPIC_API_KEY or run: claude auth

✗ SDK checks failed
```

## Acceptance Criteria

- [x] `guardkit doctor` checks CLI, package, and auth (via existing CLIToolCheck, PackageCheck, and new ClaudeAuthCheck)
- [x] `--connectivity` flag tests actual SDK query (SDKConnectivityCheck class)
- [x] Exit code 1 on any failure (run_doctor returns 1 on failures)
- [x] Clear error messages with fix instructions (details field with remediation)
- [x] API key masked in output for security (first 8...last 4 chars)
- [x] Works without network if `--connectivity` not specified (skipped by default)

## Test Plan

1. **Unit Test**: Mock `shutil.which`, verify CLI check
2. **Unit Test**: Mock import, verify package check
3. **Integration Test**: Run on machine with/without SDK installed
4. **Manual Test**: Run `guardkit doctor --check=sdk --connectivity`

## Files to Modify/Create

| File | Changes |
|------|---------|
| `guardkit/cli/doctor_checks.py` | New file with check functions |
| `guardkit/cli/doctor.py` | Add --check=sdk option |

## Notes

- Prevents false-positive feature-build failures from environment issues
- Quick check (no --connectivity) for CI pipelines
- Full check (--connectivity) for debugging
