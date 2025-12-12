"""Unit tests for rules_generator module."""

import os
import tempfile
import pytest
from pathlib import Path

# Import the modules we'll be testing
from installer.core.lib.rules_generator.code_style import generate_code_style_rules
from installer.core.lib.rules_generator.testing import generate_testing_rules
from installer.core.lib.rules_generator.patterns import generate_pattern_rules
from installer.core.lib.rules_generator.generator import generate_rules_structure


class TestCodeStyleGenerator:
    """Test code style rules generation."""

    def test_code_style_python(self):
        """Test Python code style rules generation."""
        rules = generate_code_style_rules(language="python")

        assert "paths: **/*.py" in rules
        assert "# Python Code Style" in rules or "Python" in rules
        assert len(rules) > 100  # Should have meaningful content

    def test_code_style_typescript(self):
        """Test TypeScript code style rules generation."""
        rules = generate_code_style_rules(language="typescript")

        assert "paths: **/*.{ts,tsx}" in rules
        assert "TypeScript" in rules
        assert len(rules) > 100

    def test_code_style_javascript(self):
        """Test JavaScript code style rules generation."""
        rules = generate_code_style_rules(language="javascript")

        assert "paths: **/*.{js,jsx}" in rules
        assert "JavaScript" in rules
        assert len(rules) > 100

    def test_code_style_unsupported_language(self):
        """Test unsupported language returns generic rules."""
        rules = generate_code_style_rules(language="unknown")

        # Should return some generic content or raise an error
        assert rules is not None
        assert len(rules) > 0


class TestTestingRulesGenerator:
    """Test testing rules generation."""

    def test_testing_pytest(self):
        """Test pytest testing rules generation."""
        rules = generate_testing_rules(framework="pytest")

        assert "paths: **/tests/**/*.py" in rules or "paths: **/*test*.py" in rules
        assert "pytest" in rules
        assert len(rules) > 100

    def test_testing_vitest(self):
        """Test vitest testing rules generation."""
        rules = generate_testing_rules(framework="vitest")

        assert "paths: **/*.test.{ts,tsx}" in rules or "paths: **/*.spec.{ts,tsx}" in rules
        assert "vitest" in rules
        assert len(rules) > 100

    def test_testing_jest(self):
        """Test jest testing rules generation."""
        rules = generate_testing_rules(framework="jest")

        assert "paths:" in rules
        assert "jest" in rules
        assert len(rules) > 100

    def test_testing_unsupported_framework(self):
        """Test unsupported framework returns generic rules."""
        rules = generate_testing_rules(framework="unknown")

        assert rules is not None
        assert len(rules) > 0


class TestPatternsGenerator:
    """Test architecture pattern rules generation."""

    def test_pattern_clean_architecture(self):
        """Test Clean Architecture pattern rules generation."""
        rules = generate_pattern_rules(pattern="clean-architecture")

        assert "clean" in rules.lower() or "architecture" in rules.lower()
        assert len(rules) > 100

    def test_pattern_mvvm(self):
        """Test MVVM pattern rules generation."""
        rules = generate_pattern_rules(pattern="mvvm")

        assert "mvvm" in rules.lower() or "model-view-viewmodel" in rules.lower()
        assert len(rules) > 100

    def test_pattern_layered(self):
        """Test Layered architecture pattern rules generation."""
        rules = generate_pattern_rules(pattern="layered")

        assert "layer" in rules.lower()
        assert len(rules) > 100

    def test_pattern_unsupported(self):
        """Test unsupported pattern returns generic rules."""
        rules = generate_pattern_rules(pattern="unknown")

        assert rules is not None
        assert len(rules) > 0


class TestRulesStructureGenerator:
    """Test main rules structure generation orchestrator."""

    def test_generate_rules_structure_default(self):
        """Test rules structure generation with default settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "layered"
            }

            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            rules_dir = template_dir / ".claude" / "rules"
            assert rules_dir.exists()
            assert (rules_dir / "code-style.md").exists()
            assert (rules_dir / "testing.md").exists()
            assert (rules_dir / "patterns" / "layered.md").exists()

    def test_generate_rules_structure_typescript(self):
        """Test rules structure generation for TypeScript project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            qa_answers = {
                "language": "typescript",
                "testing_framework": "vitest",
                "architecture_pattern": "clean-architecture"
            }

            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            rules_dir = template_dir / ".claude" / "rules"
            code_style = (rules_dir / "code-style.md").read_text()
            testing = (rules_dir / "testing.md").read_text()

            assert "**/*.{ts,tsx}" in code_style
            assert "vitest" in testing

    def test_generate_rules_structure_validates_size(self):
        """Test that generated CLAUDE.md size is validated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            # Create a large CLAUDE.md file
            claude_md = template_dir / ".claude" / "CLAUDE.md"
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text("x" * 6000)  # 6KB, over limit

            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "layered"
            }

            # Should raise an error or warning about size
            with pytest.raises(ValueError, match="CLAUDE.md size"):
                generate_rules_structure(
                    template_dir=str(template_dir),
                    qa_answers=qa_answers,
                    claude_md_size_limit=5000
                )

    def test_generate_rules_structure_creates_directories(self):
        """Test that all required directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "mvvm"
            }

            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            assert (template_dir / ".claude" / "rules").exists()
            assert (template_dir / ".claude" / "rules" / "patterns").exists()

    def test_generate_rules_structure_with_missing_qa_answers(self):
        """Test rules structure generation with missing Q&A answers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            qa_answers = {}  # Empty answers

            # Should handle gracefully or use defaults
            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            # At minimum, should create the rules directory
            rules_dir = template_dir / ".claude" / "rules"
            assert rules_dir.exists()
