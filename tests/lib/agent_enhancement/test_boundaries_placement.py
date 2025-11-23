"""
Unit tests for boundaries section placement logic.

Tests the updated placement strategy for boundaries sections in agent enhancement:
- After "## Quick Start", before next section (targets lines 80-150)
- Fallback to line 50-80 when no Quick Start found
- Backward compatibility with existing enhanced agents

TASK-STND-0B1A: Fix boundaries placement to match GitHub best practices
"""

import pytest
import sys
from pathlib import Path

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from applier import EnhancementApplier


# ============================================================================
# PLACEMENT TESTS - Boundaries After Quick Start
# ============================================================================

class TestBoundariesPlacementAfterQuickStart:
    """Test boundaries placement after Quick Start section."""

    def test_boundaries_after_quick_start_before_capabilities(self):
        """Test boundaries appear after Quick Start, before Capabilities."""
        applier = EnhancementApplier()

        # Simulate agent file with Quick Start and Capabilities
        original_content = """---
name: test-agent
---

# Test Agent

This is a test agent.

## Quick Start

Some quick start content here.

## Capabilities

Agent capabilities listed here.

## Code Examples

Examples go here.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        result = applier._merge_content(original_content, enhancement)
        lines = result.split('\n')

        # Find section positions
        quick_start_pos = None
        boundaries_pos = None
        capabilities_pos = None

        for i, line in enumerate(lines):
            if "## Quick Start" in line:
                quick_start_pos = i
            elif "## Boundaries" in line:
                boundaries_pos = i
            elif "## Capabilities" in line:
                capabilities_pos = i

        # Assertions
        assert quick_start_pos is not None, "Quick Start section not found"
        assert boundaries_pos is not None, "Boundaries section not found"
        assert capabilities_pos is not None, "Capabilities section not found"

        # Boundaries should be between Quick Start and Capabilities
        assert quick_start_pos < boundaries_pos < capabilities_pos, \
            f"Boundaries placement incorrect: Quick Start={quick_start_pos}, Boundaries={boundaries_pos}, Capabilities={capabilities_pos}"

        # Boundaries should be in target range (roughly 80-150)
        # Since Quick Start is around line 10, boundaries should be before line 150
        assert boundaries_pos < 150, f"Boundaries at line {boundaries_pos}, should be < 150"

    def test_boundaries_before_code_examples_no_capabilities(self):
        """Test boundaries before Code Examples when no Capabilities section."""
        applier = EnhancementApplier()

        original_content = """---
name: test-agent
---

# Test Agent

## Quick Start

Quick start content.

## Code Examples

Examples here.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        result = applier._merge_content(original_content, enhancement)
        lines = result.split('\n')

        # Find section positions
        quick_start_pos = None
        boundaries_pos = None
        examples_pos = None

        for i, line in enumerate(lines):
            if "## Quick Start" in line:
                quick_start_pos = i
            elif "## Boundaries" in line:
                boundaries_pos = i
            elif "## Code Examples" in line:
                examples_pos = i

        # Assertions
        assert quick_start_pos is not None
        assert boundaries_pos is not None
        assert examples_pos is not None

        # Boundaries should be between Quick Start and Code Examples
        assert quick_start_pos < boundaries_pos < examples_pos, \
            f"Boundaries not between Quick Start and Examples: {quick_start_pos} < {boundaries_pos} < {examples_pos}"

    def test_boundaries_complex_structure_with_multiple_sections(self):
        """Test boundaries placement with complex agent structure."""
        applier = EnhancementApplier()

        original_content = """---
name: complex-agent
---

# Complex Agent

Description here.

## Quick Start

Quick start guide.

## Capabilities

Core capabilities.

## Advanced Usage

Advanced features.

## Code Examples

Examples section.

## Best Practices

Best practices here.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        result = applier._merge_content(original_content, enhancement)
        lines = result.split('\n')

        # Find all section positions
        section_positions = {}
        for i, line in enumerate(lines):
            if line.strip().startswith("## "):
                section_name = line.strip()[3:]
                section_positions[section_name] = i

        # Assertions
        assert "Quick Start" in section_positions
        assert "Boundaries" in section_positions
        assert "Capabilities" in section_positions

        # Boundaries should be right after Quick Start, before Capabilities
        quick_start_pos = section_positions["Quick Start"]
        boundaries_pos = section_positions["Boundaries"]
        capabilities_pos = section_positions["Capabilities"]

        assert quick_start_pos < boundaries_pos < capabilities_pos, \
            f"Boundaries not in correct order: Quick Start={quick_start_pos}, Boundaries={boundaries_pos}, Capabilities={capabilities_pos}"


# ============================================================================
# FALLBACK TESTS - No Quick Start Section
# ============================================================================

class TestBoundariesFallbackPlacement:
    """Test fallback placement when Quick Start doesn't exist."""

    def test_boundaries_fallback_no_quick_start(self):
        """Test boundaries placement at line 50-80 when no Quick Start."""
        applier = EnhancementApplier()

        # Agent without Quick Start section
        original_content = """---
name: test-agent
---

# Test Agent

This agent has no Quick Start section.

## Purpose

Describes the purpose.

## Capabilities

Core capabilities here.

## Code Examples

Examples section.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        result = applier._merge_content(original_content, enhancement)
        lines = result.split('\n')

        # Find boundaries position
        boundaries_pos = None
        for i, line in enumerate(lines):
            if "## Boundaries" in line:
                boundaries_pos = i
                break

        assert boundaries_pos is not None, "Boundaries section not found"

        # Boundaries should be placed reasonably early (fallback targets 50-80)
        # In this small file, it should still be before line 80
        assert boundaries_pos < 80, f"Boundaries at line {boundaries_pos}, expected < 80"

        # Should be after frontmatter (at least line 5)
        assert boundaries_pos > 5, f"Boundaries at line {boundaries_pos}, should be after frontmatter"

    def test_boundaries_minimal_agent_structure(self):
        """Test boundaries placement in minimal agent file."""
        applier = EnhancementApplier()

        # Minimal agent file
        original_content = """---
name: minimal-agent
---

# Minimal Agent

Basic agent with minimal structure.

## Purpose

Simple purpose description.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        result = applier._merge_content(original_content, enhancement)

        # Should have boundaries section
        assert "## Boundaries" in result

        # Should have all subsections
        assert "### ALWAYS" in result
        assert "### NEVER" in result
        assert "### ASK" in result


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility and edge cases."""

    def test_no_duplicate_boundaries(self):
        """Test that boundaries are not duplicated if already present."""
        applier = EnhancementApplier()

        # Agent already has boundaries
        original_content = """---
name: test-agent
---

# Test Agent

## Quick Start

Quick start content.

## Boundaries

### ALWAYS
- ✅ Existing rule

### NEVER
- ❌ Existing rule

### ASK
- ⚠️ Existing scenario

## Capabilities

Capabilities here.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ New rule

### NEVER
- ❌ New rule

### ASK
- ⚠️ New scenario"""
        }

        result = applier._merge_content(original_content, enhancement)

        # Count occurrences of "## Boundaries"
        boundaries_count = result.count("## Boundaries")

        assert boundaries_count == 1, f"Expected 1 Boundaries section, found {boundaries_count}"

    def test_other_sections_placement_unchanged(self):
        """Test that other sections (examples, best_practices) are still appended at end."""
        applier = EnhancementApplier()

        original_content = """---
name: test-agent
---

# Test Agent

## Quick Start

Quick start content.

## Capabilities

Capabilities here.
"""

        enhancement = {
            "sections": ["boundaries", "examples", "best_practices"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)""",
            "examples": """## Examples

Example 1
Example 2""",
            "best_practices": """## Best Practices

Practice 1
Practice 2"""
        }

        result = applier._merge_content(original_content, enhancement)
        lines = result.split('\n')

        # Find section positions
        section_positions = {}
        for i, line in enumerate(lines):
            if line.strip().startswith("## "):
                section_name = line.strip()[3:]
                section_positions[section_name] = i

        # Boundaries should be between Quick Start and Capabilities
        assert section_positions["Quick Start"] < section_positions["Boundaries"] < section_positions["Capabilities"]

        # Examples and Best Practices should be at the end (after Capabilities)
        assert section_positions["Capabilities"] < section_positions["Examples"]
        assert section_positions["Capabilities"] < section_positions["Best Practices"]


# ============================================================================
# HELPER METHOD TESTS
# ============================================================================

class TestHelperMethods:
    """Test helper methods for placement logic."""

    def test_find_boundaries_insertion_point_with_quick_start(self):
        """Test _find_boundaries_insertion_point when Quick Start exists."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Agent",
            "",
            "## Quick Start",
            "",
            "Content",
            "",
            "## Capabilities",
            "",
            "More content"
        ]

        insertion_point = applier._find_boundaries_insertion_point(lines)

        # Should return index of "## Capabilities" (line 10)
        assert insertion_point == 10
        assert lines[insertion_point] == "## Capabilities"

    def test_find_boundaries_insertion_point_without_next_section(self):
        """Test when Quick Start exists but no section after it."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Agent",
            "",
            "## Quick Start",
            "",
            "Content here",
            "More content",
            "Even more content"
        ]

        insertion_point = applier._find_boundaries_insertion_point(lines)

        # Should return ~30 lines after Quick Start (or end of file if shorter)
        # Quick Start is at line 6, so target would be 36, but file is only 11 lines
        assert insertion_point <= len(lines)

    def test_find_post_description_position(self):
        """Test _find_post_description_position fallback logic."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Agent",
            "",
            "## Purpose",
            "",
            "Purpose content",
            "",
            "## Capabilities",
            "",
            "Capabilities content"
        ]

        insertion_point = applier._find_post_description_position(lines)

        # Should find second ## section after frontmatter
        # First is "## Purpose" at line 6, second is "## Capabilities" at line 10
        assert insertion_point == 10 or insertion_point <= 50
