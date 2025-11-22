"""
Integration tests for /agent-format command
"""

import pytest
from pathlib import Path
import tempfile
import subprocess
import sys


@pytest.fixture
def sample_agent_file(tmp_path):
    """Create a sample agent file for testing"""
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text(
        """---
name: test-agent
description: Test agent for integration testing
---

This is a test agent with minimal content.

It has some text but no code examples or structure."""
    )
    return agent_file


@pytest.fixture
def high_quality_agent_file(tmp_path):
    """Create a high-quality agent file"""
    agent_file = tmp_path / "good-agent.md"
    agent_file.write_text(
        """---
name: good-agent
description: Python testing agent using TDD
---

Test specialist agent.

## Quick Start

```bash
/test --mode=tdd
```

## Boundaries

### ALWAYS
- Run tests before committing
- Validate inputs

### NEVER
- Skip test coverage
- Commit failing tests

### ASK
- When requirements are ambiguous
- When tests conflict

## Examples

```python
def test_example():
    assert True
```

Some explanation here.

```python
def another_example():
    return "result"
```"""
    )
    return agent_file


class TestCommandExecution:
    """Tests for command execution"""

    def test_format_single_agent(self, sample_agent_file):
        """Test formatting a single agent file"""
        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(sample_agent_file),
                '--no-backup',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert sample_agent_file.exists()

        # Check that file was modified
        content = sample_agent_file.read_text()
        assert 'Quick Start' in content or 'ALWAYS' in content

    def test_dry_run_mode(self, sample_agent_file):
        """Test dry-run mode doesn't modify files"""
        original_content = sample_agent_file.read_text()

        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(sample_agent_file),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert 'DRY RUN' in result.stdout

        # File should not be modified
        assert sample_agent_file.read_text() == original_content

    def test_validate_only_mode(self, sample_agent_file):
        """Test validate-only mode"""
        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(sample_agent_file),
                '--validate-only',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert 'VALIDATE ONLY' in result.stdout

    def test_backup_creation(self, sample_agent_file):
        """Test that backup file is created"""
        backup_file = sample_agent_file.with_suffix('.md.bak')

        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(sample_agent_file),
                '--backup',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert backup_file.exists()


class TestQualityImprovement:
    """Tests for quality improvement"""

    def test_low_quality_to_better(self, sample_agent_file):
        """Test that low-quality agent is improved"""
        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(sample_agent_file),
                '--no-backup',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0

        # Check formatted content has improvements
        content = sample_agent_file.read_text()

        # Should have boundary sections
        assert 'ALWAYS' in content
        assert 'NEVER' in content
        assert 'ASK' in content

        # Should have content markers
        assert '[NEEDS_CONTENT' in content

    def test_high_quality_preserved(self, high_quality_agent_file):
        """Test that high-quality agent is not degraded"""
        original_content = high_quality_agent_file.read_text()

        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(high_quality_agent_file),
                '--no-backup',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0

        formatted_content = high_quality_agent_file.read_text()

        # Original content should be preserved
        # (Allow for added markers but no removal)
        assert 'Quick Start' in formatted_content
        assert 'ALWAYS' in formatted_content
        assert 'test_example' in formatted_content


class TestBatchProcessing:
    """Tests for batch processing"""

    def test_process_multiple_files(self, tmp_path):
        """Test processing multiple agent files"""
        # Create multiple agent files
        for i in range(3):
            agent_file = tmp_path / f"agent-{i}.md"
            agent_file.write_text(
                f"""---
name: agent-{i}
description: Test agent {i}
---

Content for agent {i}"""
            )

        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                str(tmp_path / '*.md'),
                '--no-backup',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert 'Found 3 agent(s)' in result.stdout
        assert 'SUMMARY' in result.stdout


class TestErrorHandling:
    """Tests for error handling"""

    def test_nonexistent_file(self):
        """Test error handling for nonexistent file"""
        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                '/nonexistent/file.md',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 1
        assert 'No agents found' in result.stderr or 'No agents found' in result.stdout

    def test_invalid_glob_pattern(self):
        """Test error handling for invalid glob pattern"""
        result = subprocess.run(
            [
                sys.executable,
                'installer/global/commands/agent-format.py',
                '/tmp/nonexistent/*.md',
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 1
        assert 'No agents found' in result.stderr or 'No agents found' in result.stdout
