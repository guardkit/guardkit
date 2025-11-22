"""Tests for example density checks."""

import unittest
import sys
from pathlib import Path

# Add lib path
lib_path = Path(__file__).parent.parent.parent / 'installer' / 'global' / 'commands' / 'lib'
sys.path.insert(0, str(lib_path))

from agent_validator.checks.example_density import ExampleDensityChecks


class TestExampleDensityChecks(unittest.TestCase):
    """Test example density validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = ExampleDensityChecks()

    def test_code_percentage_calculation(self):
        """Test code percentage calculation."""
        content = """---
name: test
---

Some text here

```python
code line 1
code line 2
code line 3
```

More text
"""
        result = self.checker._check_code_percentage(content)

        # Should calculate percentage of code vs total content
        self.assertGreater(result.measured_value, 0)
        self.assertLess(result.measured_value, 100)

    def test_example_count(self):
        """Test example counting."""
        content = """
```python
example 1
```

```javascript
example 2
```

```bash
example 3
```
"""
        result = self.checker._check_example_count(content)

        self.assertEqual(result.measured_value, 3)
        self.assertEqual(result.name, "Example Count")

    def test_example_format_do_dont(self):
        """Test DO/DON'T format detection."""
        content = """
✅ DO this:
```python
good_code()
```

❌ DON'T do this:
```python
bad_code()
```
"""
        result = self.checker._check_example_format(content)

        # Should detect formatted examples
        self.assertGreater(result.measured_value, 0)

    def test_no_examples(self):
        """Test handling of content with no code examples."""
        content = "Just plain text with no code examples"

        result = self.checker._check_example_count(content)

        self.assertEqual(result.measured_value, 0)
        self.assertEqual(result.status, "fail")


if __name__ == '__main__':
    unittest.main()
