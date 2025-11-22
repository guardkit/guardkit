# Agent Enhance Strategy Simplification Specification

**Status**: DRAFT
**Created**: 2025-11-22
**Author**: Software Architect
**Related**: `/agent-enhance` command, `enhancer.py`

---

## Executive Summary

This specification proposes simplifying the `/agent-enhance` command's strategy selection from an enum-based `--strategy=VALUE` approach to boolean flags (`--hybrid`, `--static`). The change addresses user confusion around default vs recommended strategies and provides a clearer, more intuitive interface.

**Current State**: Verbose, confusing (default is "ai" but "hybrid" is recommended)
**Proposed State**: Simple, self-documenting (AI by default, opt-in for alternatives)

---

## 1. API Design

### 1.1 Proposed Interface

```bash
# AI strategy (default, best quality)
/agent-enhance template/agent

# Hybrid strategy (AI with fallback, production-safe)
/agent-enhance template/agent --hybrid

# Static strategy (fast/offline, basic quality)
/agent-enhance template/agent --static
```

### 1.2 Command-Line Arguments

**New Flag Structure** (boolean flags):

```python
parser.add_argument(
    "--hybrid",
    action="store_true",
    help="Use hybrid strategy (AI with static fallback for reliability)"
)
parser.add_argument(
    "--static",
    action="store_true",
    help="Use static strategy (fast keyword matching, offline-friendly)"
)
```

**Deprecated Flag** (kept for backward compatibility, 6-month deprecation period):

```python
parser.add_argument(
    "--strategy",
    choices=["ai", "static", "hybrid"],
    default=None,  # Changed from "ai" to None
    help="[DEPRECATED] Enhancement strategy. Use --hybrid or --static flags instead."
)
```

### 1.3 Strategy Resolution Algorithm

```python
def resolve_strategy(parsed_args) -> str:
    """
    Resolve strategy from command-line arguments.

    Priority:
    1. New flags (--hybrid, --static)
    2. Legacy --strategy flag (with deprecation warning)
    3. Default: "ai"

    Args:
        parsed_args: Parsed argparse.Namespace

    Returns:
        Strategy name ("ai", "hybrid", or "static")

    Raises:
        ValueError: If conflicting flags are provided
    """
    # Count boolean flags
    flag_count = sum([
        parsed_args.hybrid,
        parsed_args.static
    ])

    # Error: Multiple boolean flags
    if flag_count > 1:
        raise ValueError(
            "Conflicting strategy flags: --hybrid and --static are mutually exclusive"
        )

    # Case 1: New boolean flags (preferred)
    if parsed_args.hybrid:
        return "hybrid"
    if parsed_args.static:
        return "static"

    # Case 2: Legacy --strategy flag (deprecated)
    if parsed_args.strategy is not None:
        logger.warning(
            "⚠️  --strategy flag is deprecated and will be removed in v2.0\n"
            "   Use --hybrid or --static flags instead:\n"
            f"   /agent-enhance {parsed_args.agent_path} --{parsed_args.strategy}"
        )
        return parsed_args.strategy

    # Case 3: Default to AI
    return "ai"
```

### 1.4 Backward Compatibility

**Transition Strategy**: Phased deprecation over 6 months

**Phase 1 (Months 1-3): Deprecation Warnings**
- `--strategy` flag works but emits warnings
- Documentation shows new syntax
- Migration guide published

**Phase 2 (Months 4-6): Louder Warnings**
- Warning includes deprecation timeline
- Help text marked as `[DEPRECATED]`
- GitHub issue template for feedback

**Phase 3 (Month 7+): Removal**
- `--strategy` flag removed
- Error message with migration hint

**Compatibility Matrix**:

| Input | Phase 1-6 Behavior | Phase 7+ Behavior |
|-------|-------------------|-------------------|
| `/agent-enhance template/agent` | ✅ AI (default) | ✅ AI (default) |
| `/agent-enhance template/agent --hybrid` | ✅ Hybrid | ✅ Hybrid |
| `/agent-enhance template/agent --static` | ✅ Static | ✅ Static |
| `/agent-enhance template/agent --strategy=ai` | ⚠️ AI (deprecated) | ❌ Error + hint |
| `/agent-enhance template/agent --strategy=hybrid` | ⚠️ Hybrid (deprecated) | ❌ Error + hint |
| `/agent-enhance template/agent --strategy=static` | ⚠️ Static (deprecated) | ❌ Error + hint |

---

## 2. Implementation Strategy

### 2.1 Code Changes

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/agent-enhance.py`

#### Change 1: Add New Flags

```python
# BEFORE (lines 49-54)
parser.add_argument(
    "--strategy",
    choices=["ai", "static", "hybrid"],
    default="ai",
    help="Enhancement strategy (default: ai)"
)

# AFTER
parser.add_argument(
    "--hybrid",
    action="store_true",
    help="Use hybrid strategy (AI with static fallback for reliability)"
)
parser.add_argument(
    "--static",
    action="store_true",
    help="Use static strategy (fast keyword matching, offline-friendly)"
)
parser.add_argument(
    "--strategy",
    choices=["ai", "static", "hybrid"],
    default=None,
    help="[DEPRECATED] Enhancement strategy. Use --hybrid or --static flags instead."
)
```

#### Change 2: Add Strategy Resolution Function

```python
def resolve_strategy(parsed_args) -> str:
    """
    Resolve strategy from command-line arguments.

    Priority:
    1. New flags (--hybrid, --static)
    2. Legacy --strategy flag (with deprecation warning)
    3. Default: "ai"

    Args:
        parsed_args: Parsed argparse.Namespace

    Returns:
        Strategy name ("ai", "hybrid", or "static")

    Raises:
        ValueError: If conflicting flags are provided
    """
    # Count boolean flags
    flag_count = sum([
        parsed_args.hybrid,
        parsed_args.static
    ])

    # Error: Multiple boolean flags
    if flag_count > 1:
        raise ValueError(
            "Conflicting strategy flags: --hybrid and --static are mutually exclusive"
        )

    # Case 1: New boolean flags (preferred)
    if parsed_args.hybrid:
        return "hybrid"
    if parsed_args.static:
        return "static"

    # Case 2: Legacy --strategy flag (deprecated)
    if parsed_args.strategy is not None:
        logger.warning(
            "⚠️  --strategy flag is deprecated and will be removed in v2.0\n"
            "   Use --hybrid or --static flags instead:\n"
            f"   /agent-enhance {parsed_args.agent_path} --{parsed_args.strategy}"
        )
        return parsed_args.strategy

    # Case 3: Default to AI
    return "ai"
```

#### Change 3: Update Main Function

```python
# BEFORE (lines 96-100)
enhancer = SingleAgentEnhancer(
    strategy=parsed_args.strategy,
    dry_run=parsed_args.dry_run,
    verbose=parsed_args.verbose
)

# AFTER
try:
    strategy = resolve_strategy(parsed_args)
except ValueError as e:
    logger.error(f"✗ {e}")
    return 1

enhancer = SingleAgentEnhancer(
    strategy=strategy,
    dry_run=parsed_args.dry_run,
    verbose=parsed_args.verbose
)
```

### 2.2 No Changes to `enhancer.py`

**Rationale**: The `SingleAgentEnhancer` class already accepts a `strategy` string parameter. No changes needed to the enhancement logic itself—only the command-line interface changes.

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/lib/agent_enhancement/enhancer.py`

```python
# Lines 50-66 remain unchanged
def __init__(
    self,
    strategy: str = "ai",
    dry_run: bool = False,
    verbose: bool = False
):
    """
    Initialize enhancer.

    Args:
        strategy: Enhancement strategy (ai|static|hybrid)
        dry_run: If True, don't apply changes
        verbose: If True, show detailed process
    """
    self.strategy = strategy
    self.dry_run = dry_run
    self.verbose = verbose
```

---

## 3. User Experience

### 3.1 Help Text

```bash
$ /agent-enhance --help

usage: agent-enhance [-h] [--dry-run] [--hybrid] [--static]
                     [--strategy {ai,static,hybrid}] [--verbose]
                     agent_path

Enhance a single agent with template-specific content

positional arguments:
  agent_path            Agent path (template-dir/agent-name or /path/to/agent.md)

optional arguments:
  -h, --help            show this help message and exit
  --dry-run             Show what would be enhanced without applying
  --hybrid              Use hybrid strategy (AI with static fallback for reliability)
  --static              Use static strategy (fast keyword matching, offline-friendly)
  --strategy {ai,static,hybrid}
                        [DEPRECATED] Enhancement strategy. Use --hybrid or --static flags instead.
  --verbose             Show detailed enhancement process

Enhancement Strategies:
  (no flags)            AI strategy - Best quality, 2-5 minutes (default)
  --hybrid              Hybrid strategy - AI with fallback, production-safe
  --static              Static strategy - Fast keyword matching, <5 seconds
```

### 3.2 Success Messages

**AI Strategy** (default):

```bash
$ /agent-enhance react-typescript/testing-specialist

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (AI strategy)
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

**Hybrid Strategy**:

```bash
$ /agent-enhance react-typescript/testing-specialist --hybrid

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (Hybrid strategy - AI succeeded)
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

**Hybrid Fallback**:

```bash
$ /agent-enhance react-typescript/testing-specialist --hybrid

Enhancing testing-specialist.md...
⚠️  AI enhancement timed out, falling back to static strategy
✓ Enhanced testing-specialist.md (Hybrid strategy - Static fallback)
  Sections added: 1
  Templates referenced: 5
  Code examples: 0
```

**Static Strategy**:

```bash
$ /agent-enhance react-typescript/testing-specialist --static

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (Static strategy)
  Sections added: 1
  Templates referenced: 5
  Code examples: 0
```

### 3.3 Error Messages

**Conflicting Flags**:

```bash
$ /agent-enhance react-typescript/testing-specialist --hybrid --static

✗ Conflicting strategy flags: --hybrid and --static are mutually exclusive

Choose one:
  /agent-enhance react-typescript/testing-specialist --hybrid
  /agent-enhance react-typescript/testing-specialist --static
```

**Deprecated Flag Warning**:

```bash
$ /agent-enhance react-typescript/testing-specialist --strategy=hybrid

⚠️  --strategy flag is deprecated and will be removed in v2.0
   Use --hybrid or --static flags instead:
   /agent-enhance react-typescript/testing-specialist --hybrid

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (Hybrid strategy)
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

**Post-Removal Error** (Phase 7+):

```bash
$ /agent-enhance react-typescript/testing-specialist --strategy=hybrid

✗ Unknown argument: --strategy

The --strategy flag has been removed. Use boolean flags instead:
  --hybrid    AI with static fallback (production-safe)
  --static    Fast keyword matching (offline-friendly)

Example:
  /agent-enhance react-typescript/testing-specialist --hybrid
```

---

## 4. Edge Cases

### 4.1 Multiple Boolean Flags

**Input**:
```bash
/agent-enhance template/agent --hybrid --static
```

**Behavior**:
- `resolve_strategy()` raises `ValueError`
- Error message shows mutually exclusive flags
- Exit code: 1
- No enhancement attempted

**Rationale**: Clear error is better than ambiguous precedence rules.

### 4.2 Legacy + New Flags (Transition Period)

**Input**:
```bash
/agent-enhance template/agent --strategy=hybrid --static
```

**Behavior**:
- New flags take precedence over legacy flag
- No deprecation warning (new syntax used)
- Returns: `"static"`

**Rationale**: If user provides new syntax, assume they've migrated. Don't mix old/new in warnings.

### 4.3 No Flags (Default)

**Input**:
```bash
/agent-enhance template/agent
```

**Behavior**:
- Returns: `"ai"`
- No warnings
- Best quality output

**Rationale**: AI is the best quality, so it should be the default. Users who need speed/reliability opt-in to alternatives.

### 4.4 Dry-Run with Strategy

**Input**:
```bash
/agent-enhance template/agent --hybrid --dry-run
```

**Behavior**:
- Runs hybrid strategy
- Shows preview without applying
- Includes strategy in output: `"(Hybrid strategy)"`

**Rationale**: Strategy selection is orthogonal to dry-run behavior.

### 4.5 Verbose with Deprecated Flag

**Input**:
```bash
/agent-enhance template/agent --strategy=ai --verbose
```

**Behavior**:
- Shows deprecation warning
- Shows detailed enhancement process
- Uses AI strategy

**Rationale**: Verbose mode doesn't suppress deprecation warnings.

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/tests/unit/test_agent_enhance_strategy_resolution.py`

```python
"""
Unit tests for /agent-enhance strategy resolution.

Tests the resolve_strategy() function with various flag combinations.
"""

import pytest
from argparse import Namespace
from installer.global.commands.agent_enhance import resolve_strategy


class TestStrategyResolution:
    """Test strategy resolution logic."""

    def test_default_ai_strategy(self):
        """No flags should default to AI."""
        args = Namespace(
            hybrid=False,
            static=False,
            strategy=None,
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "ai"

    def test_hybrid_flag(self):
        """--hybrid flag should return hybrid."""
        args = Namespace(
            hybrid=True,
            static=False,
            strategy=None,
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "hybrid"

    def test_static_flag(self):
        """--static flag should return static."""
        args = Namespace(
            hybrid=False,
            static=True,
            strategy=None,
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "static"

    def test_conflicting_flags_error(self):
        """--hybrid and --static together should raise error."""
        args = Namespace(
            hybrid=True,
            static=True,
            strategy=None,
            agent_path="template/agent"
        )
        with pytest.raises(ValueError, match="mutually exclusive"):
            resolve_strategy(args)

    def test_legacy_strategy_ai(self, caplog):
        """--strategy=ai should work with deprecation warning."""
        args = Namespace(
            hybrid=False,
            static=False,
            strategy="ai",
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "ai"
        assert "deprecated" in caplog.text.lower()

    def test_legacy_strategy_hybrid(self, caplog):
        """--strategy=hybrid should work with deprecation warning."""
        args = Namespace(
            hybrid=False,
            static=False,
            strategy="hybrid",
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "hybrid"
        assert "deprecated" in caplog.text.lower()

    def test_legacy_strategy_static(self, caplog):
        """--strategy=static should work with deprecation warning."""
        args = Namespace(
            hybrid=False,
            static=False,
            strategy="static",
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "static"
        assert "deprecated" in caplog.text.lower()

    def test_new_flag_precedence_over_legacy(self):
        """New flags should take precedence over --strategy."""
        args = Namespace(
            hybrid=False,
            static=True,
            strategy="hybrid",  # Should be ignored
            agent_path="template/agent"
        )
        assert resolve_strategy(args) == "static"
```

### 5.2 Integration Tests

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/tests/integration/test_agent_enhance_workflows.py`

```python
"""
Integration tests for /agent-enhance command workflows.

Tests actual enhancement execution with different strategies.
"""

import pytest
from pathlib import Path
import subprocess


class TestAgentEnhanceWorkflows:
    """Test complete enhancement workflows."""

    @pytest.fixture
    def test_agent(self, tmp_path):
        """Create a test agent file."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()
        agent_file = agent_dir / "test-specialist.md"
        agent_file.write_text("""---
name: test-specialist
description: Test specialist agent
---

# Test Specialist

Initial content.
""")
        return agent_file

    @pytest.fixture
    def test_template(self, tmp_path):
        """Create test template directory with files."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.template").write_text("Test template content")
        return tmp_path

    def test_ai_strategy_workflow(self, test_agent, test_template):
        """Test full AI enhancement workflow."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "AI strategy" in result.stdout
        assert "Sections added:" in result.stdout

    def test_hybrid_strategy_workflow(self, test_agent, test_template):
        """Test hybrid enhancement workflow."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--hybrid"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Hybrid strategy" in result.stdout

    def test_static_strategy_workflow(self, test_agent, test_template):
        """Test static enhancement workflow."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--static"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Static strategy" in result.stdout
        # Static should be fast
        assert "seconds" not in result.stdout or "< 5" in result.stdout

    def test_conflicting_flags_error(self, test_agent, test_template):
        """Test error handling for conflicting flags."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--hybrid", "--static"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1
        assert "mutually exclusive" in result.stderr.lower()

    def test_dry_run_preview(self, test_agent, test_template):
        """Test dry-run mode shows preview without applying."""
        # Read original content
        original_content = test_agent.read_text()

        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--hybrid", "--dry-run"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "[DRY RUN]" in result.stdout
        assert "Preview" in result.stdout

        # Verify file unchanged
        assert test_agent.read_text() == original_content
```

### 5.3 Backward Compatibility Tests

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/tests/integration/test_agent_enhance_backward_compat.py`

```python
"""
Backward compatibility tests for /agent-enhance command.

Ensures legacy --strategy flag continues to work during deprecation period.
"""

import pytest
import subprocess


class TestBackwardCompatibility:
    """Test backward compatibility with --strategy flag."""

    @pytest.fixture
    def test_agent(self, tmp_path):
        """Create a test agent file."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()
        agent_file = agent_dir / "test-specialist.md"
        agent_file.write_text("""---
name: test-specialist
---

# Test Specialist
""")
        return agent_file

    def test_legacy_strategy_ai_still_works(self, test_agent, caplog):
        """--strategy=ai should still work with warning."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--strategy=ai"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "deprecated" in result.stderr.lower()
        assert "AI strategy" in result.stdout

    def test_legacy_strategy_hybrid_still_works(self, test_agent):
        """--strategy=hybrid should still work with warning."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--strategy=hybrid"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "deprecated" in result.stderr.lower()
        assert "Hybrid strategy" in result.stdout

    def test_legacy_strategy_static_still_works(self, test_agent):
        """--strategy=static should still work with warning."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--strategy=static"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "deprecated" in result.stderr.lower()
        assert "Static strategy" in result.stdout

    def test_new_flags_preferred_over_legacy(self, test_agent):
        """New flags should suppress deprecation warnings."""
        result = subprocess.run(
            ["python", "installer/global/commands/agent-enhance.py",
             str(test_agent), "--hybrid"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "deprecated" not in result.stderr.lower()
        assert "Hybrid strategy" in result.stdout
```

### 5.4 Test Coverage Requirements

| Component | Coverage Target | Priority |
|-----------|----------------|----------|
| `resolve_strategy()` | 100% | HIGH |
| CLI argument parsing | 100% | HIGH |
| Error messages | 100% | HIGH |
| Success messages | 90% | MEDIUM |
| Integration workflows | 80% | MEDIUM |
| Edge cases | 100% | HIGH |

---

## 6. Documentation Updates

### 6.1 agent-enhance.md Structure

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/agent-enhance.md`

#### Section 1: Quick Start (New)

```markdown
## Quick Start

```bash
# Best quality (AI-powered, 2-5 minutes)
/agent-enhance react-typescript/testing-specialist

# Production-safe (AI with fallback)
/agent-enhance react-typescript/testing-specialist --hybrid

# Fast/offline (keyword matching, <5 seconds)
/agent-enhance react-typescript/testing-specialist --static

# Preview changes
/agent-enhance react-typescript/testing-specialist --dry-run
```

**When to use each strategy:**
- **No flags (AI)**: Best quality, sufficient time available, single agent
- **--hybrid**: Production environments, batch enhancements, need reliability
- **--static**: CI/CD pipelines, offline development, quick scaffolding
```

#### Section 2: Usage (Updated)

```markdown
## Usage

```bash
# Enhance agent using template/agent format
/agent-enhance react-typescript/testing-specialist

# Enhance agent using absolute path
/agent-enhance /path/to/template/agents/testing-specialist.md

# Preview enhancement without applying (dry-run)
/agent-enhance react-typescript/testing-specialist --dry-run

# Use hybrid strategy (AI with fallback to static)
/agent-enhance react-typescript/testing-specialist --hybrid

# Use static strategy (keyword matching, no AI)
/agent-enhance react-typescript/testing-specialist --static

# Show detailed progress
/agent-enhance react-typescript/testing-specialist --verbose
```
```

#### Section 3: Command Options (Updated)

```markdown
## Command Options

### Required Arguments

```bash
agent_path               Agent path in one of two formats:
                         1. "template-dir/agent-name" (relative, slash-separated)
                            Example: react-typescript/testing-specialist
                         2. "/absolute/path/to/agent.md" (absolute path)
                            Example: /Users/me/.agentecflow/templates/my-template/agents/api-specialist.md
```

### Optional Flags

```bash
--dry-run                Show enhancement preview without applying changes
                         Default: false

--hybrid                 Use hybrid strategy (AI with static fallback)
                         Recommended for production environments
                         Default: false (uses AI if not specified)

--static                 Use static strategy (keyword matching only)
                         Best for offline/CI environments
                         Default: false (uses AI if not specified)

--verbose                Show detailed enhancement process
                         Default: false
```

### Deprecated Flags

```bash
--strategy STRATEGY      [DEPRECATED - Will be removed in v2.0]
                         Use --hybrid or --static flags instead

                         Legacy support only:
                         --strategy=ai      → (no flag needed - AI is default)
                         --strategy=hybrid  → use --hybrid
                         --strategy=static  → use --static
```
```

#### Section 4: Enhancement Strategies (Simplified)

```markdown
## Enhancement Strategies

### AI Strategy (Default)
**Command**: `/agent-enhance template/agent` (no flags)

- **Method**: Uses `agent-content-enhancer` agent via Task tool
- **Quality**: High - Understands context and generates relevant content
- **Speed**: 2-5 minutes per agent
- **Use when**: Quality is priority, time is available
- **Best for**: Individual agent enhancements, learning template patterns

### Hybrid Strategy (Production-Safe)
**Command**: `/agent-enhance template/agent --hybrid`

- **Method**: Tries AI first, falls back to static on failure
- **Quality**: High when AI succeeds, basic when falls back
- **Speed**: 2-5 minutes (AI) or <5 seconds (fallback)
- **Use when**: Production environments, need reliability
- **Best for**: Batch enhancements, CI/CD pipelines, team templates
- **Fallback triggers**: Timeout, AI error, API unavailable

### Static Strategy (Fast/Offline)
**Command**: `/agent-enhance template/agent --static`

- **Method**: Simple keyword matching between agent name and template files
- **Quality**: Basic - Only creates related templates list
- **Speed**: <5 seconds per agent
- **Use when**: Need quick results, AI unavailable, offline development
- **Best for**: Scaffolding, quick previews, CI/CD pipelines
- **Limitations**: No code examples, no best practices
```

#### Section 5: Examples (Updated)

```markdown
## Examples

### Example 1: Basic Enhancement (AI)
```bash
$ /agent-enhance react-typescript/testing-specialist

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (AI strategy)
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

### Example 2: Production-Safe Enhancement (Hybrid)
```bash
$ /agent-enhance react-typescript/testing-specialist --hybrid

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (Hybrid strategy - AI succeeded)
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

### Example 3: Fast Enhancement (Static)
```bash
$ /agent-enhance react-typescript/testing-specialist --static

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (Static strategy)
  Sections added: 1
  Templates referenced: 5
  Code examples: 0
```

### Example 4: Dry-Run Preview
```bash
$ /agent-enhance react-typescript/testing-specialist --dry-run

Enhancing testing-specialist.md...
✓ Enhanced testing-specialist.md (AI strategy)
  Sections added: 4
  Templates referenced: 8
  Code examples: 3

[DRY RUN] Changes not applied

--- Preview ---
## Related Templates
- templates/tests/unit/ComponentTest.tsx.template
- templates/tests/integration/ApiTest.tsx.template
...
```
```

#### Section 6: Best Practices (Updated)

```markdown
## Best Practices

1. **Start with AI for learning**: Use default AI strategy to see high-quality examples
2. **Use --hybrid for production**: Provides AI quality with static fallback for reliability
3. **Use --static for CI/CD**: Fast, deterministic results for automated pipelines
4. **Preview first with --dry-run**: Review changes before applying
5. **Use --verbose for debugging**: See detailed process when issues occur
6. **Batch enhance related agents**: Enhance domain, testing, UI agents together
7. **Commit after enhancement**: Track agent changes in version control

### Migration from --strategy Flag

If you're using the deprecated `--strategy` flag:

```bash
# OLD (deprecated)
/agent-enhance template/agent --strategy=hybrid

# NEW (recommended)
/agent-enhance template/agent --hybrid
```

The `--strategy` flag will be removed in v2.0. Update your scripts and workflows.
```

### 6.2 CLAUDE.md Updates

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/CLAUDE.md`

Update the "UX Design Integration" section to reflect new syntax:

```markdown
## UX Design Integration

Converts design system files (Figma, Zeplin) into components with **zero scope creep**.

**Supported:**
- `/figma-to-react` - Figma → TypeScript React + Tailwind + Playwright
- `/zeplin-to-maui` - Zeplin → XAML + C# + platform tests

**Agent Enhancement:**
```bash
# AI strategy (default, best quality)
/agent-enhance template/agent

# Hybrid strategy (production-safe)
/agent-enhance template/agent --hybrid

# Static strategy (fast/offline)
/agent-enhance template/agent --static
```
```

### 6.3 Migration Guide

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/docs/guides/agent-enhance-migration-guide.md` (NEW)

```markdown
# Agent Enhance Migration Guide

## Overview

The `/agent-enhance` command has simplified its strategy selection from `--strategy=VALUE` to boolean flags (`--hybrid`, `--static`). This guide helps you migrate existing scripts and workflows.

## What's Changing

### Old Syntax (Deprecated)
```bash
/agent-enhance template/agent --strategy=ai
/agent-enhance template/agent --strategy=hybrid
/agent-enhance template/agent --strategy=static
```

### New Syntax (Recommended)
```bash
/agent-enhance template/agent              # AI (default)
/agent-enhance template/agent --hybrid     # Hybrid
/agent-enhance template/agent --static     # Static
```

## Migration Steps

### 1. Update Shell Scripts

**Before**:
```bash
#!/bin/bash
for agent in testing-specialist api-specialist domain-specialist; do
    /agent-enhance react-typescript/$agent --strategy=hybrid
done
```

**After**:
```bash
#!/bin/bash
for agent in testing-specialist api-specialist domain-specialist; do
    /agent-enhance react-typescript/$agent --hybrid
done
```

### 2. Update CI/CD Pipelines

**GitHub Actions - Before**:
```yaml
- name: Enhance agents
  run: |
    /agent-enhance template/agent-1 --strategy=static
    /agent-enhance template/agent-2 --strategy=static
```

**GitHub Actions - After**:
```yaml
- name: Enhance agents
  run: |
    /agent-enhance template/agent-1 --static
    /agent-enhance template/agent-2 --static
```

### 3. Update Documentation

Search your project for `--strategy=` and replace with boolean flags:
```bash
# Find all references
rg --type md "--strategy="

# Review and update manually
```

## Timeline

| Phase | Dates | Status |
|-------|-------|--------|
| **Phase 1-2** | Months 1-6 | `--strategy` works with warnings |
| **Phase 3** | Month 7+ | `--strategy` removed, errors shown |

## FAQ

**Q: When will --strategy be removed?**
A: Version 2.0 (approximately 6 months from now).

**Q: What happens if I don't migrate?**
A: Your scripts will continue to work but will show deprecation warnings. After v2.0, they will fail with an error message.

**Q: Can I mix old and new syntax?**
A: Yes, during the transition period. New flags take precedence.

**Q: How do I suppress warnings?**
A: Migrate to the new syntax. Warnings are intentional to encourage migration.

## Getting Help

- **Questions**: Open an issue with the `question` label
- **Bug Reports**: Open an issue with the `bug` label
- **Migration Problems**: Tag issues with `migration`
```

---

## 7. Migration Timeline

### Phase 1: Announcement (Month 1)

**Actions**:
1. Release v1.5 with new flags + deprecation warnings
2. Publish migration guide
3. Update all documentation
4. Announce in release notes

**User Impact**: None (warnings only)

### Phase 2: Reinforcement (Months 2-6)

**Actions**:
1. Add deprecation warning to help text
2. Include migration hint in warnings
3. Track usage metrics (if telemetry available)
4. Send reminders to active users

**User Impact**: Warnings visible in output

### Phase 3: Removal (Month 7+)

**Actions**:
1. Release v2.0 with `--strategy` removed
2. Show helpful error with migration hint
3. Update changelog

**User Impact**: Old scripts fail with clear error

**Rollback Plan**: If >20% of users haven't migrated by Month 6, extend Phase 2 by 3 months.

---

## 8. Success Metrics

### 8.1 Adoption Metrics

- **Target**: 80% of users using new syntax by Month 3
- **Measurement**: Count `--hybrid`/`--static` vs `--strategy=` in logs (if telemetry available)

### 8.2 Support Metrics

- **Target**: <5 migration-related issues per month
- **Measurement**: GitHub issues tagged with `migration`

### 8.3 Documentation Metrics

- **Target**: 90% positive feedback on migration guide
- **Measurement**: GitHub reactions on migration guide PR

---

## 9. Risk Assessment

### 9.1 High Risk: User Confusion

**Risk**: Users don't understand when to use which strategy
**Mitigation**:
- Clear "Quick Start" section in docs
- Decision tree in help text
- Examples for each use case

### 9.2 Medium Risk: Breaking CI/CD Pipelines

**Risk**: Automated pipelines break after v2.0 release
**Mitigation**:
- 6-month deprecation period
- Loud warnings in CI environments
- Migration guide with CI-specific examples

### 9.3 Low Risk: Edge Case Conflicts

**Risk**: Users provide conflicting flags (`--hybrid --static`)
**Mitigation**:
- Clear error message
- Mutual exclusivity validation
- Unit tests for all flag combinations

---

## 10. Design Rationale

### 10.1 Why Boolean Flags?

**Problem**: `--strategy=VALUE` requires remembering exact values and is verbose.

**Solution**: Boolean flags are self-documenting:
- `--hybrid` clearly means "hybrid strategy"
- `--static` clearly means "static strategy"
- No flag means "default" (AI)

**Trade-off**: Slightly more arguments in `argparse`, but much clearer UX.

### 10.2 Why AI as Default?

**Problem**: Current default is "ai" but "hybrid" is recommended for production.

**Solution**: Make AI the default because:
1. Best quality for learning and exploration
2. Most users start with single agents (not batch)
3. Users who need reliability opt-in to `--hybrid`

**Trade-off**: Production users must add `--hybrid` flag, but this is explicit and intentional.

### 10.3 Why 6-Month Deprecation?

**Problem**: Need balance between fast iteration and user stability.

**Solution**: 6 months provides:
1. Time for users to migrate existing scripts
2. Multiple release cycles to communicate change
3. Opportunity to gather feedback

**Trade-off**: Longer support burden, but less user frustration.

### 10.4 Why Keep --strategy During Transition?

**Problem**: Breaking change would disrupt all existing users.

**Solution**: Keep `--strategy` with warnings to allow gradual migration.

**Trade-off**: More complex argument parsing during transition, but zero breaking changes.

---

## 11. Implementation Checklist

### Code Changes
- [ ] Add `--hybrid` and `--static` flags to argument parser
- [ ] Add `resolve_strategy()` function
- [ ] Update `main()` to use `resolve_strategy()`
- [ ] Add conflict validation
- [ ] Add deprecation warnings
- [ ] Update success messages to include strategy name

### Testing
- [ ] Unit tests for `resolve_strategy()`
- [ ] Unit tests for flag combinations
- [ ] Integration tests for each strategy
- [ ] Backward compatibility tests
- [ ] Edge case tests (conflicts, etc.)

### Documentation
- [ ] Update agent-enhance.md with new syntax
- [ ] Add "Quick Start" section
- [ ] Update "Enhancement Strategies" section
- [ ] Update "Examples" section
- [ ] Update "Best Practices" section
- [ ] Create migration guide
- [ ] Update CLAUDE.md references
- [ ] Update changelog

### Release
- [ ] Version bump (v1.5)
- [ ] Release notes with migration guide link
- [ ] Announcement in README
- [ ] GitHub discussion for feedback

### Post-Release (Month 3)
- [ ] Review adoption metrics
- [ ] Address migration issues
- [ ] Adjust timeline if needed

### Pre-Removal (Month 6)
- [ ] Final migration reminder
- [ ] Verify >80% adoption
- [ ] Prepare v2.0 release notes

### Removal (Month 7+)
- [ ] Remove `--strategy` flag
- [ ] Add helpful error message
- [ ] Version bump (v2.0)
- [ ] Update documentation
- [ ] Announce breaking change

---

## 12. Appendix

### A. Code Diff Summary

**Files Modified**:
1. `installer/global/commands/agent-enhance.py` (~50 lines changed)
2. `installer/global/commands/agent-enhance.md` (~100 lines changed)
3. `CLAUDE.md` (~10 lines changed)

**Files Created**:
1. `docs/guides/agent-enhance-migration-guide.md` (new)
2. `tests/unit/test_agent_enhance_strategy_resolution.py` (new)
3. `tests/integration/test_agent_enhance_workflows.py` (new)
4. `tests/integration/test_agent_enhance_backward_compat.py` (new)

**Total LOC**: ~650 lines (code + tests + docs)

### B. References

- [argparse Boolean Flags](https://docs.python.org/3/library/argparse.html#action)
- [Semantic Versioning](https://semver.org/)
- [Deprecation Best Practices](https://12factor.net/dependencies)
- [CLI Design Principles](https://clig.dev/)

---

**Specification Status**: READY FOR REVIEW
**Estimated Implementation Time**: 4-6 hours (code + tests + docs)
**Risk Level**: LOW (backward compatible, phased approach)
**User Impact**: HIGH (improved UX, clearer intent)
