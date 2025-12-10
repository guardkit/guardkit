"""
Unit tests for agent_formatting.metrics module
"""

import pytest
from pathlib import Path
import tempfile
import importlib

# Use importlib to avoid 'global' keyword syntax issue in Python 3.14+
_parser = importlib.import_module('installer.core.lib.agent_formatting.parser')
parse_agent = _parser.parse_agent

_metrics = importlib.import_module('installer.core.lib.agent_formatting.metrics')
check_time_to_first_example = _metrics.check_time_to_first_example
calculate_example_density = _metrics.calculate_example_density
check_boundary_sections = _metrics.check_boundary_sections
check_commands_first = _metrics.check_commands_first
calculate_code_to_text_ratio = _metrics.calculate_code_to_text_ratio
calculate_specificity_score = _metrics.calculate_specificity_score
calculate_metrics = _metrics.calculate_metrics
QualityMetrics = _metrics.QualityMetrics


@pytest.fixture
def sample_agent(tmp_path):
    """Create a sample agent file for testing"""
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text(
        """---
name: test-agent
description: Python testing agent for TDD workflows
---

Role description here.

## Quick Start

```bash
/test --mode=tdd
```

## Boundaries

### ALWAYS
- Rule 1
- Rule 2

### NEVER
- Rule 3
- Rule 4

### ASK
- Scenario 1
- Scenario 2

## Examples

```python
def test_example():
    assert True
```

Some prose paragraph here with explanation.

More text explaining the concept.
"""
    )
    return parse_agent(agent_file)


class TestCheckTimeToFirstExample:
    """Tests for check_time_to_first_example function"""

    def test_early_example(self, tmp_path):
        """Test agent with example in first 50 lines"""
        agent_file = tmp_path / "early.md"
        agent_file.write_text(
            """---
name: test
---

Text

```python
code
```"""
        )
        agent = parse_agent(agent_file)

        line_num = check_time_to_first_example(agent)

        assert line_num < 50
        assert line_num >= 0

    def test_late_example(self, tmp_path):
        """Test agent with example after 50 lines"""
        agent_file = tmp_path / "late.md"
        # Create content with lots of text before first example
        lines = ['---', 'name: test', '---', '']
        lines.extend(['Text line'] * 60)
        lines.extend(['', '```python', 'code', '```'])

        agent_file.write_text('\n'.join(lines))
        agent = parse_agent(agent_file)

        line_num = check_time_to_first_example(agent)

        assert line_num >= 50

    def test_no_examples(self, tmp_path):
        """Test agent with no code examples"""
        agent_file = tmp_path / "no-examples.md"
        agent_file.write_text(
            """---
name: test
---

Just text, no code"""
        )
        agent = parse_agent(agent_file)

        line_num = check_time_to_first_example(agent)

        assert line_num == -1


class TestCalculateExampleDensity:
    """Tests for calculate_example_density function"""

    def test_high_density(self, tmp_path):
        """Test agent with high code density"""
        agent_file = tmp_path / "high-density.md"
        agent_file.write_text(
            """---
name: test
---

```python
line1
line2
line3
line4
line5
```

Text
Text"""
        )
        agent = parse_agent(agent_file)

        density = calculate_example_density(agent)

        # 5 code lines, ~7 total content lines = ~71%
        assert density > 50

    def test_low_density(self, tmp_path):
        """Test agent with low code density"""
        agent_file = tmp_path / "low-density.md"
        agent_file.write_text(
            """---
name: test
---

Text line 1
Text line 2
Text line 3
Text line 4
Text line 5

```python
code
```"""
        )
        agent = parse_agent(agent_file)

        density = calculate_example_density(agent)

        # 1 code line, ~6 total lines = ~17%
        assert density < 30

    def test_no_content(self, tmp_path):
        """Test agent with no content"""
        agent_file = tmp_path / "no-content.md"
        agent_file.write_text(
            """---
name: test
---"""
        )
        agent = parse_agent(agent_file)

        density = calculate_example_density(agent)

        assert density == 0.0


class TestCheckBoundarySections:
    """Tests for check_boundary_sections function"""

    def test_all_sections_present(self, sample_agent):
        """Test agent with all boundary sections"""
        boundaries = check_boundary_sections(sample_agent)

        assert boundaries['ALWAYS'] is True
        assert boundaries['NEVER'] is True
        assert boundaries['ASK'] is True

    def test_missing_sections(self, tmp_path):
        """Test agent with missing boundary sections"""
        agent_file = tmp_path / "missing.md"
        agent_file.write_text(
            """---
name: test
---

## Boundaries

### ALWAYS
- Rule 1

No NEVER or ASK sections"""
        )
        agent = parse_agent(agent_file)

        boundaries = check_boundary_sections(agent)

        assert boundaries['ALWAYS'] is True
        assert boundaries['NEVER'] is False
        assert boundaries['ASK'] is False

    def test_no_boundary_sections(self, tmp_path):
        """Test agent without any boundary sections"""
        agent_file = tmp_path / "no-boundaries.md"
        agent_file.write_text(
            """---
name: test
---

Just content"""
        )
        agent = parse_agent(agent_file)

        boundaries = check_boundary_sections(agent)

        assert boundaries['ALWAYS'] is False
        assert boundaries['NEVER'] is False
        assert boundaries['ASK'] is False


class TestCheckCommandsFirst:
    """Tests for check_commands_first function"""

    def test_early_command(self, sample_agent):
        """Test agent with command example in first 50 lines"""
        line_num = check_commands_first(sample_agent)

        assert line_num < 50
        assert line_num >= 0

    def test_no_commands(self, tmp_path):
        """Test agent without command examples"""
        agent_file = tmp_path / "no-commands.md"
        agent_file.write_text(
            """---
name: test
---

```python
# Python code, not bash
pass
```"""
        )
        agent = parse_agent(agent_file)

        line_num = check_commands_first(agent)

        assert line_num == -1

    def test_late_command(self, tmp_path):
        """Test agent with command after 50 lines"""
        agent_file = tmp_path / "late-command.md"
        lines = ['---', 'name: test', '---', '']
        lines.extend(['Text'] * 60)
        lines.extend(['', '```bash', 'echo "test"', '```'])

        agent_file.write_text('\n'.join(lines))
        agent = parse_agent(agent_file)

        line_num = check_commands_first(agent)

        assert line_num >= 50


class TestCalculateCodeToTextRatio:
    """Tests for calculate_code_to_text_ratio function"""

    def test_high_ratio(self, tmp_path):
        """Test agent with high code-to-text ratio"""
        agent_file = tmp_path / "high-ratio.md"
        agent_file.write_text(
            """---
name: test
---

Paragraph 1

```python
code1
```

Paragraph 2

```python
code2
```"""
        )
        agent = parse_agent(agent_file)

        ratio = calculate_code_to_text_ratio(agent)

        # 2 code blocks, 2 paragraphs = 1:1 ratio
        assert ratio >= 1.0

    def test_low_ratio(self, tmp_path):
        """Test agent with low code-to-text ratio"""
        agent_file = tmp_path / "low-ratio.md"
        agent_file.write_text(
            """---
name: test
---

Paragraph 1

Paragraph 2

Paragraph 3

```python
code
```"""
        )
        agent = parse_agent(agent_file)

        ratio = calculate_code_to_text_ratio(agent)

        # 1 code block, 3 paragraphs = ~0.33:1
        assert ratio < 0.5


class TestCalculateSpecificityScore:
    """Tests for calculate_specificity_score function"""

    def test_high_specificity(self, sample_agent):
        """Test agent with high specificity score"""
        score = calculate_specificity_score(sample_agent)

        # Has "Python" and "testing" = 4 + 3 = 7
        assert score >= 7

    def test_low_specificity(self, tmp_path):
        """Test agent with low specificity score"""
        agent_file = tmp_path / "low-spec.md"
        agent_file.write_text(
            """---
name: test
description: A generic helper agent
---

Content"""
        )
        agent = parse_agent(agent_file)

        score = calculate_specificity_score(agent)

        assert score < 5

    def test_max_specificity(self, tmp_path):
        """Test agent with maximum specificity"""
        agent_file = tmp_path / "max-spec.md"
        agent_file.write_text(
            """---
name: test
description: Python testing agent using TDD and SOLID principles
---

Content"""
        )
        agent = parse_agent(agent_file)

        score = calculate_specificity_score(agent)

        # Has Python (tech), testing (domain), TDD + SOLID (standards) = 4+3+3 = 10
        assert score == 10


class TestCalculateMetrics:
    """Tests for calculate_metrics function"""

    def test_calculate_all_metrics(self, sample_agent):
        """Test calculating all metrics for an agent"""
        metrics = calculate_metrics(sample_agent)

        assert isinstance(metrics, QualityMetrics)
        assert metrics.time_to_first_example >= 0
        assert 0 <= metrics.example_density <= 100
        assert len(metrics.boundary_sections) == 3
        assert metrics.commands_first >= 0
        assert metrics.code_to_text_ratio >= 0
        assert 0 <= metrics.specificity_score <= 10


class TestQualityMetrics:
    """Tests for QualityMetrics dataclass methods"""

    def test_get_status_pass(self):
        """Test status classification for PASS agent"""
        metrics = QualityMetrics(
            time_to_first_example=30,
            example_density=45.0,
            boundary_sections={'ALWAYS': True, 'NEVER': True, 'ASK': True},
            commands_first=25,
            code_to_text_ratio=1.2,
            specificity_score=9,
        )

        assert metrics.get_status() == 'PASS'

    def test_get_status_warn(self):
        """Test status classification for WARN agent"""
        metrics = QualityMetrics(
            time_to_first_example=30,
            example_density=35.0,  # Below 40% but above 30%
            boundary_sections={'ALWAYS': True, 'NEVER': True, 'ASK': True},
            commands_first=25,
            code_to_text_ratio=0.9,  # Below 1.0 but above 0.8
            specificity_score=9,
        )

        assert metrics.get_status() == 'WARN'

    def test_get_status_fail(self):
        """Test status classification for FAIL agent"""
        metrics = QualityMetrics(
            time_to_first_example=80,  # Over 50 lines
            example_density=25.0,
            boundary_sections={'ALWAYS': False, 'NEVER': False, 'ASK': False},
            commands_first=-1,
            code_to_text_ratio=0.5,
            specificity_score=6,
        )

        assert metrics.get_status() == 'FAIL'

    def test_passes_threshold_true(self):
        """Test passes_threshold for qualifying agent"""
        metrics = QualityMetrics(
            time_to_first_example=30,
            example_density=40.0,
            boundary_sections={'ALWAYS': True, 'NEVER': True, 'ASK': True},
            commands_first=25,
            code_to_text_ratio=1.0,
            specificity_score=8,
        )

        assert metrics.passes_threshold() is True

    def test_passes_threshold_false(self):
        """Test passes_threshold for non-qualifying agent"""
        metrics = QualityMetrics(
            time_to_first_example=60,  # Fails threshold
            example_density=40.0,
            boundary_sections={'ALWAYS': True, 'NEVER': True, 'ASK': True},
            commands_first=25,
            code_to_text_ratio=1.0,
            specificity_score=8,
        )

        assert metrics.passes_threshold() is False
