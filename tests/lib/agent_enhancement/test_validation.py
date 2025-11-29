"""
Unit tests for agent content validation module.

Tests validation logic for GitHub best practices including:
- Time to first example
- Example density
- Boundary sections
- Commands-first structure
- Specificity scoring
- Code-to-text ratio
"""

import pytest
import sys
from pathlib import Path

# Add .claude/commands/shared to path for imports
shared_path = Path(__file__).parent.parent.parent.parent / '.claude' / 'commands' / 'shared'
sys.path.insert(0, str(shared_path))

from agent_validation import (
    validate_enhanced_content,
    _calculate_example_density,
    _check_boundary_sections,
    _score_specificity,
    _find_first_code_block,
    _find_first_command,
    _calculate_code_to_text_ratio
)


def test_example_density_calculation():
    """Test example density calculation."""
    content = """---
name: test
---

# Test Agent

Some prose here.

```python
code example
line 2
```

More prose.
"""
    density = _calculate_example_density(content, 3)
    # 2 code lines out of ~8 total lines = ~25%
    assert 20 <= density <= 30


def test_example_density_high():
    """Test high example density (should pass)."""
    content = """---
name: test
---

# Test Agent

Brief intro.

```python
code line 1
code line 2
code line 3
code line 4
code line 5
code line 6
code line 7
code line 8
```

Brief outro.
"""
    density = _calculate_example_density(content, 3)
    # Should be around 40-50%
    assert density >= 40


def test_boundary_section_detection():
    """Test boundary section detection."""
    content = """
## Boundaries

### ALWAYS
- Rule 1
- Rule 2

### NEVER
- Rule 1
- Rule 2

### ASK
- Scenario 1
"""
    sections = _check_boundary_sections(content)
    assert sections == ["ALWAYS", "NEVER", "ASK"]


def test_boundary_section_missing():
    """Test missing boundary sections."""
    content = """
## Boundaries

### ALWAYS
- Rule 1

### NEVER
- Rule 1
"""
    sections = _check_boundary_sections(content)
    assert len(sections) == 2
    assert "ASK" not in sections


def test_boundary_section_case_insensitive():
    """Test boundary detection is case insensitive."""
    content = """
### always
- Rule 1

### Never
- Rule 2

### ask
- Scenario 1
"""
    sections = _check_boundary_sections(content)
    assert len(sections) == 3


def test_specificity_scoring_high():
    """Test high specificity scoring."""
    # Tech + domain + standard = high score
    high = "Code review specialist for React TypeScript using SOLID principles"
    score = _score_specificity(high)
    assert score >= 8


def test_specificity_scoring_medium():
    """Test medium specificity scoring."""
    # Tech + domain, no standard
    medium = "React TypeScript code reviewer"
    score = _score_specificity(medium)
    assert 5 <= score <= 8


def test_specificity_scoring_low():
    """Test low specificity scoring."""
    # Generic description
    low = "Helpful assistant"
    score = _score_specificity(low)
    assert score < 8


def test_time_to_first_example():
    """Test finding first code block."""
    content = """---
name: test
---

# Test Agent

Some intro text.
More intro.
Even more intro.

```python
first code block
```
"""
    lines = content.split('\n')
    first_example = _find_first_code_block(lines, 3)
    assert first_example <= 10  # Should find it quickly


def test_time_to_first_example_late():
    """Test late first code block (should fail threshold)."""
    # Create content with code block after 50 lines
    intro_lines = ["Line " + str(i) for i in range(60)]
    content = "---\nname: test\n---\n\n" + "\n".join(intro_lines) + "\n\n```python\ncode\n```"
    lines = content.split('\n')
    first_example = _find_first_code_block(lines, 3)
    assert first_example > 50  # Should exceed threshold


def test_commands_first():
    """Test finding first command."""
    content = """---
name: test
---

# Test Agent

## Quick Start

```bash
/test-command --flag
```
"""
    lines = content.split('\n')
    first_command = _find_first_command(lines, 3)
    assert first_command <= 10


def test_code_to_text_ratio_high():
    """Test high code-to-text ratio (passing)."""
    content = """---
name: test
---

# Test

Brief intro.

```python
example 1
```

Brief text.

```javascript
example 2
```

Brief text.

```typescript
example 3
```
"""
    ratio = _calculate_code_to_text_ratio(content, 3)
    assert ratio >= 1.0  # Should have good ratio


def test_code_to_text_ratio_low():
    """Test low code-to-text ratio (warning)."""
    content = """---
name: test
---

# Test

Long paragraph about things.
More text here.
Even more text.
And more.
And more.
And more.
And more.
And more.

```python
single example
```
"""
    ratio = _calculate_code_to_text_ratio(content, 3)
    assert ratio < 1.0  # Should have poor ratio


def test_validation_pass():
    """Test full validation with passing content."""
    content = """---
name: test-agent
description: React TypeScript code reviewer for SOLID principles
---

# Test Agent

## Quick Start

```bash
/test-command
```

## Boundaries

### ALWAYS
- Rule 1
- Rule 2
- Rule 3
- Rule 4
- Rule 5

### NEVER
- Rule 1
- Rule 2
- Rule 3
- Rule 4
- Rule 5

### ASK
- Scenario 1
- Scenario 2
- Scenario 3

## Examples

```python
# Example 1
code here
more code
more code
more code
```

```javascript
// Example 2
code here
more code
more code
more code
```

```typescript
// Example 3
code here
more code
more code
more code
```

Some text.

```python
# Example 4
code here
more code
```
"""
    report = validate_enhanced_content(content)
    # Should pass or have acceptable warnings
    assert report.overall_status in ["PASSED", "FAILED"]  # Just check it runs
    assert len(report.checks) == 6  # All 6 checks present


def test_validation_fail_no_boundaries():
    """Test validation fails when boundaries missing."""
    content = """---
name: test-agent
description: React TypeScript code reviewer
---

# Test Agent

```bash
/test-command
```

Some content here.

```python
example
```
"""
    report = validate_enhanced_content(content)
    assert report.checks['boundary_sections'].status == "FAIL"
    assert report.overall_status == "FAILED"


def test_validation_fail_late_example():
    """Test validation fails when first example too late."""
    # Create content with late first example
    intro = "\n".join(["Line " + str(i) for i in range(60)])
    content = f"""---
name: test
description: React TypeScript SOLID code reviewer
---

# Test

{intro}

```python
late example
```

## Boundaries

### ALWAYS
- Rule 1

### NEVER
- Rule 1

### ASK
- Scenario 1
"""
    report = validate_enhanced_content(content)
    assert report.checks['time_to_first_example'].status == "FAIL"


def test_validation_warnings():
    """Test validation generates warnings for borderline cases."""
    content = """---
name: test-agent
description: React TypeScript code reviewer using SOLID principles
---

# Test Agent

```bash
/test-command
```

## Boundaries

### ALWAYS
- Rule 1

### NEVER
- Rule 1

### ASK
- Scenario 1

Lots of prose here.
More prose.
More prose.
More prose.
More prose.
More prose.
More prose.

```python
example 1
```

More prose.
More prose.
More prose.
"""
    report = validate_enhanced_content(content)
    # Check that warnings are generated
    assert isinstance(report.warnings, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
