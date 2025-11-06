"""
Unit tests for template_init models

Tests GreenfieldTemplate data model including serialization.
"""

import pytest
import sys
from pathlib import Path

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"))

from template_init.models import GreenfieldTemplate


class TestGreenfieldTemplate:
    """Test GreenfieldTemplate data model"""

    def test_create_template(self):
        """Test creating a GreenfieldTemplate instance"""
        template = GreenfieldTemplate(
            name="test-template",
            manifest={"name": "test"},
            settings={"type": "greenfield"},
            claude_md="# Test Template",
            project_structure={"src": {"type": "directory"}},
            code_templates={"main.py": "print('hello')"},
            inferred_analysis=None,
        )

        assert template.name == "test-template"
        assert template.manifest == {"name": "test"}
        assert template.settings == {"type": "greenfield"}
        assert template.claude_md == "# Test Template"
        assert template.project_structure == {"src": {"type": "directory"}}
        assert template.code_templates == {"main.py": "print('hello')"}

    def test_to_dict(self):
        """Test converting template to dictionary"""
        template = GreenfieldTemplate(
            name="test-template",
            manifest={"name": "test", "version": "1.0.0"},
            settings={"type": "greenfield", "language": "python"},
            claude_md="# Test Template\n\nTest content",
            project_structure={"src": {"type": "directory"}},
            code_templates={"main.py": "print('hello')"},
            inferred_analysis=None,
        )

        data = template.to_dict()

        assert isinstance(data, dict)
        assert data["name"] == "test-template"
        assert data["manifest"] == {"name": "test", "version": "1.0.0"}
        assert data["settings"] == {"type": "greenfield", "language": "python"}
        assert data["claude_md"] == "# Test Template\n\nTest content"
        assert data["project_structure"] == {"src": {"type": "directory"}}
        assert data["code_templates"] == {"main.py": "print('hello')"}
        assert "inferred_analysis" not in data  # Not serialized

    def test_from_dict(self):
        """Test creating template from dictionary"""
        data = {
            "name": "test-template",
            "manifest": {"name": "test", "version": "1.0.0"},
            "settings": {"type": "greenfield"},
            "claude_md": "# Test",
            "project_structure": {"src": {"type": "directory"}},
            "code_templates": {"main.py": "print('hello')"},
        }

        template = GreenfieldTemplate.from_dict(data)

        assert template.name == "test-template"
        assert template.manifest == {"name": "test", "version": "1.0.0"}
        assert template.settings == {"type": "greenfield"}
        assert template.claude_md == "# Test"
        assert template.project_structure == {"src": {"type": "directory"}}
        assert template.code_templates == {"main.py": "print('hello')"}
        assert template.inferred_analysis is None

    def test_from_dict_with_analysis(self):
        """Test creating template from dict with inferred analysis"""

        class MockAnalysis:
            language = "Python"

        data = {
            "name": "test-template",
            "manifest": {},
            "settings": {},
            "claude_md": "",
            "project_structure": {},
            "code_templates": {},
        }

        mock_analysis = MockAnalysis()
        template = GreenfieldTemplate.from_dict(data, inferred_analysis=mock_analysis)

        assert template.inferred_analysis is mock_analysis
        assert template.inferred_analysis.language == "Python"

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip (to_dict -> from_dict)"""
        original = GreenfieldTemplate(
            name="test-template",
            manifest={"name": "test", "version": "1.0.0"},
            settings={"type": "greenfield", "language": "python"},
            claude_md="# Test Template\n\nContent",
            project_structure={"src": {"type": "directory"}, "tests": {"type": "directory"}},
            code_templates={"main.py": "print('hello')", "test.py": "def test(): pass"},
            inferred_analysis=None,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = GreenfieldTemplate.from_dict(data)

        # Verify equality (excluding inferred_analysis)
        assert restored.name == original.name
        assert restored.manifest == original.manifest
        assert restored.settings == original.settings
        assert restored.claude_md == original.claude_md
        assert restored.project_structure == original.project_structure
        assert restored.code_templates == original.code_templates

    def test_empty_code_templates(self):
        """Test template with no code templates"""
        template = GreenfieldTemplate(
            name="minimal-template",
            manifest={},
            settings={},
            claude_md="",
            project_structure={},
            code_templates={},  # Empty
            inferred_analysis=None,
        )

        assert template.code_templates == {}
        assert len(template.code_templates) == 0

    def test_complex_project_structure(self):
        """Test template with nested project structure"""
        structure = {
            "src": {
                "type": "directory",
                "children": {
                    "api": {"type": "directory"},
                    "domain": {"type": "directory"},
                    "infrastructure": {"type": "directory"},
                },
            },
            "tests": {
                "type": "directory",
                "children": {
                    "unit": {"type": "directory"},
                    "integration": {"type": "directory"},
                },
            },
        }

        template = GreenfieldTemplate(
            name="complex-template",
            manifest={},
            settings={},
            claude_md="",
            project_structure=structure,
            code_templates={},
            inferred_analysis=None,
        )

        assert "src" in template.project_structure
        assert "tests" in template.project_structure
        assert "children" in template.project_structure["src"]
        assert "api" in template.project_structure["src"]["children"]

    def test_multiple_code_templates(self):
        """Test template with multiple code templates"""
        templates = {
            "src/main.py": "# Main entry point\nif __name__ == '__main__':\n    pass",
            "src/api/routes.py": "# API routes\nfrom fastapi import FastAPI",
            "tests/test_main.py": "# Tests\nimport pytest",
            "README.md": "# Project\n\nDescription",
            ".gitignore": "*.pyc\n__pycache__/",
        }

        template = GreenfieldTemplate(
            name="multi-file-template",
            manifest={},
            settings={},
            claude_md="",
            project_structure={},
            code_templates=templates,
            inferred_analysis=None,
        )

        assert len(template.code_templates) == 5
        assert "src/main.py" in template.code_templates
        assert "tests/test_main.py" in template.code_templates
        assert "README.md" in template.code_templates
