"""
Unit Tests for TemplateAssertions

Tests the template assertion helpers for integration tests.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from tests.lib.template_testing.template_assertions import TemplateAssertions


class TestTemplateAssertions:
    """Unit tests for TemplateAssertions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)
    
    def test_assert_template_exists_pass(self, temp_dir):
        """Test template existence assertion when directory exists."""
        # Should not raise
        TemplateAssertions.assert_template_exists(temp_dir)
    
    def test_assert_template_exists_fail_missing(self):
        """Test template existence assertion when directory missing."""
        non_existent = Path("/tmp/does_not_exist_12345")
        
        with pytest.raises(AssertionError, match="does not exist"):
            TemplateAssertions.assert_template_exists(non_existent)
    
    def test_assert_has_metadata_pass(self, temp_dir):
        """Test metadata assertion when valid."""
        metadata = {
            "id": "test-template",
            "name": "Test Template",
            "version": "1.0.0",
            "tech_stack": "python"
        }
        
        with open(temp_dir / ".template.json", "w") as f:
            json.dump(metadata, f)
        
        result = TemplateAssertions.assert_has_metadata(temp_dir)
        
        assert result["id"] == "test-template"
        assert result["version"] == "1.0.0"
    
    def test_assert_has_metadata_fail_missing_file(self, temp_dir):
        """Test metadata assertion when file missing."""
        with pytest.raises(AssertionError, match="Missing .template.json"):
            TemplateAssertions.assert_has_metadata(temp_dir)
    
    def test_assert_has_metadata_fail_missing_fields(self, temp_dir):
        """Test metadata assertion when fields missing."""
        incomplete_metadata = {"id": "test"}
        
        with open(temp_dir / ".template.json", "w") as f:
            json.dump(incomplete_metadata, f)
        
        with pytest.raises(AssertionError, match="Missing 'name' in metadata"):
            TemplateAssertions.assert_has_metadata(temp_dir)
    
    def test_assert_has_required_files_pass(self, temp_dir):
        """Test required files assertion when all exist."""
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()
        
        # Should not raise
        TemplateAssertions.assert_has_required_files(temp_dir, ["file1.txt", "file2.txt"])
    
    def test_assert_has_required_files_fail(self, temp_dir):
        """Test required files assertion when some missing."""
        (temp_dir / "file1.txt").touch()
        
        with pytest.raises(AssertionError, match="Missing required files"):
            TemplateAssertions.assert_has_required_files(temp_dir, ["file1.txt", "file2.txt"])
    
    def test_assert_has_readme_pass(self, temp_dir):
        """Test README assertion when file exists."""
        with open(temp_dir / "README.md", "w") as f:
            f.write("# Test Template\n\nThis is a test template with enough content.")
        
        # Should not raise
        TemplateAssertions.assert_has_readme(temp_dir)
    
    def test_assert_has_readme_fail_missing(self, temp_dir):
        """Test README assertion when file missing."""
        with pytest.raises(AssertionError, match="Missing README.md"):
            TemplateAssertions.assert_has_readme(temp_dir)
    
    def test_assert_has_readme_fail_too_short(self, temp_dir):
        """Test README assertion when content too short."""
        with open(temp_dir / "README.md", "w") as f:
            f.write("# Test")
        
        with pytest.raises(AssertionError, match="too short"):
            TemplateAssertions.assert_has_readme(temp_dir)
    
    def test_assert_has_structure_documentation_pass(self, temp_dir):
        """Test structure documentation assertion when valid."""
        structure_content = """# Directory Structure

## Overview

```
template/
├── src/
└── tests/
```

## Key Directories

- src/: Source code
- tests/: Test files
"""
        with open(temp_dir / "STRUCTURE.md", "w") as f:
            f.write(structure_content)
        
        # Should not raise
        TemplateAssertions.assert_has_structure_documentation(temp_dir)
    
    def test_assert_valid_tech_stack_pass(self):
        """Test tech stack validation when matching."""
        metadata = {"tech_stack": "python"}
        
        # Should not raise
        TemplateAssertions.assert_valid_tech_stack(metadata, "python")
    
    def test_assert_valid_tech_stack_fail(self):
        """Test tech stack validation when mismatched."""
        metadata = {"tech_stack": "react"}
        
        with pytest.raises(AssertionError, match="Expected tech_stack"):
            TemplateAssertions.assert_valid_tech_stack(metadata, "python")
    
    def test_assert_has_patterns_pass(self):
        """Test patterns assertion when all present."""
        metadata = {"patterns": ["Repository", "Factory", "Singleton"]}
        
        # Should not raise
        TemplateAssertions.assert_has_patterns(metadata, ["Repository", "Factory"])
    
    def test_assert_has_patterns_fail(self):
        """Test patterns assertion when some missing."""
        metadata = {"patterns": ["Repository"]}
        
        with pytest.raises(AssertionError, match="Missing expected patterns"):
            TemplateAssertions.assert_has_patterns(metadata, ["Repository", "Factory"])
    
    def test_assert_valid_version_pass(self):
        """Test version validation with valid semantic version."""
        metadata = {"version": "1.2.3"}
        
        # Should not raise
        TemplateAssertions.assert_valid_version(metadata)
    
    def test_assert_valid_version_fail_format(self):
        """Test version validation with invalid format."""
        metadata = {"version": "1.2"}
        
        with pytest.raises(AssertionError, match="must be semantic"):
            TemplateAssertions.assert_valid_version(metadata)
    
    def test_assert_valid_version_fail_non_numeric(self):
        """Test version validation with non-numeric parts."""
        metadata = {"version": "1.2.beta"}
        
        with pytest.raises(AssertionError, match="must be integers"):
            TemplateAssertions.assert_valid_version(metadata)
    
    def test_assert_file_count_reasonable_pass(self, temp_dir):
        """Test file count assertion when sufficient."""
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()
        (temp_dir / "file3.txt").touch()
        
        # Should not raise
        TemplateAssertions.assert_file_count_reasonable(temp_dir, min_files=3)
    
    def test_assert_file_count_reasonable_fail(self, temp_dir):
        """Test file count assertion when insufficient."""
        (temp_dir / "file1.txt").touch()
        
        with pytest.raises(AssertionError, match="too few files"):
            TemplateAssertions.assert_file_count_reasonable(temp_dir, min_files=3)
    
    def test_assert_no_sensitive_data_pass(self, temp_dir):
        """Test sensitive data assertion with safe files."""
        (temp_dir / "README.md").touch()
        (temp_dir / "main.py").touch()
        
        # Should not raise
        TemplateAssertions.assert_no_sensitive_data(temp_dir)
    
    def test_assert_no_sensitive_data_fail(self, temp_dir):
        """Test sensitive data assertion with sensitive files."""
        (temp_dir / ".env").touch()
        (temp_dir / "secrets.json").touch()
        
        with pytest.raises(AssertionError, match="potentially sensitive"):
            TemplateAssertions.assert_no_sensitive_data(temp_dir)
    
    def test_assert_compilation_success_python(self, temp_dir):
        """Test compilation check for Python."""
        (temp_dir / "requirements.txt").touch()
        
        result = TemplateAssertions.assert_compilation_success(temp_dir, "python")
        
        assert result is True
    
    def test_assert_compilation_success_react(self, temp_dir):
        """Test compilation check for React."""
        (temp_dir / "package.json").touch()
        
        result = TemplateAssertions.assert_compilation_success(temp_dir, "react")
        
        assert result is True
    
    def test_assert_compilation_success_unknown_stack(self, temp_dir):
        """Test compilation check for unknown stack."""
        result = TemplateAssertions.assert_compilation_success(temp_dir, "unknown")
        
        assert result is True  # Unknown stacks pass by default
