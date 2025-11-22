"""Tests for main validator."""

import unittest
import sys
from pathlib import Path
import tempfile

# Add lib path
lib_path = Path(__file__).parent.parent.parent / 'installer' / 'global' / 'commands' / 'lib'
sys.path.insert(0, str(lib_path))

from agent_validator import AgentValidator, ValidationConfig


class TestAgentValidator(unittest.TestCase):
    """Test main validation orchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = ValidationConfig()
        self.validator = AgentValidator(self.config)

    def test_validator_initializes_all_checks(self):
        """Test that validator initializes all check categories."""
        expected_categories = [
            'structure',
            'example_density',
            'boundaries',
            'specificity',
            'example_quality',
            'maintenance'
        ]

        for category in expected_categories:
            self.assertIn(category, self.validator.checks)

    def test_validate_simple_agent(self):
        """Test validation of a simple agent file."""
        content = """---
name: test-agent
summary: A test agent
category: Testing
---

## Purpose
This is a test agent.

## ALWAYS
- Do this
- Do that
- Another rule
- Fourth rule
- Fifth rule

## NEVER
- Don't do this
- Don't do that
- Another prohibition
- Fourth prohibition
- Fifth prohibition

## When to Ask
- Ask about this
- Ask about that
- Ask about something else

## Examples

```python
def example():
    return "test"
```

```python
def another_example():
    return "test2"
```
"""

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            report = self.validator.validate(temp_path)

            # Check report structure
            self.assertIsNotNone(report)
            self.assertGreater(report.overall_score, 0)
            self.assertLessEqual(report.overall_score, 10)
            self.assertEqual(report.file, str(temp_path))
            self.assertGreater(report.lines, 0)

            # Check categories
            self.assertGreater(len(report.category_scores), 0)

        finally:
            temp_path.unlink()

    def test_should_run_category_filtering(self):
        """Test category filtering."""
        config = ValidationConfig(check_categories=['structure', 'boundaries'])
        validator = AgentValidator(config)

        self.assertTrue(validator._should_run_category('structure'))
        self.assertTrue(validator._should_run_category('boundaries'))
        self.assertFalse(validator._should_run_category('specificity'))

    def test_determine_status(self):
        """Test status determination from score."""
        self.assertEqual(self.validator._determine_status(9.5), 'excellent')
        self.assertEqual(self.validator._determine_status(8.5), 'good')
        self.assertEqual(self.validator._determine_status(7.5), 'acceptable')
        self.assertEqual(self.validator._determine_status(6.5), 'below_target')
        self.assertEqual(self.validator._determine_status(4.0), 'poor')


if __name__ == '__main__':
    unittest.main()
