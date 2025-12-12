"""Integration tests for rules generator in template-init workflow."""

import tempfile
import pytest
from pathlib import Path

from installer.core.lib.rules_generator import generate_rules_structure


class TestRulesGeneratorIntegration:
    """Integration tests for complete rules generation workflow."""

    def test_full_python_template_generation(self):
        """Test complete Python template with rules structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            claude_dir = template_dir / ".claude"
            claude_dir.mkdir(parents=True)

            # Create a minimal CLAUDE.md
            (claude_dir / "CLAUDE.md").write_text("# Core documentation\n" * 100)

            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "layered"
            }

            # Generate rules structure
            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            # Verify structure created
            rules_dir = claude_dir / "rules"
            assert rules_dir.exists()

            # Verify files created
            assert (rules_dir / "code-style.md").exists()
            assert (rules_dir / "testing.md").exists()
            assert (rules_dir / "patterns" / "layered.md").exists()

            # Verify content
            code_style_content = (rules_dir / "code-style.md").read_text()
            assert "paths: **/*.py" in code_style_content
            assert "Python" in code_style_content

            testing_content = (rules_dir / "testing.md").read_text()
            assert "pytest" in testing_content
            assert "paths:" in testing_content

            layered_content = (rules_dir / "patterns" / "layered.md").read_text()
            assert "Layered" in layered_content or "layer" in layered_content.lower()

    def test_full_typescript_react_template_generation(self):
        """Test complete TypeScript React template with rules structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            claude_dir = template_dir / ".claude"
            claude_dir.mkdir(parents=True)

            # Create a minimal CLAUDE.md
            (claude_dir / "CLAUDE.md").write_text("# Core documentation\n" * 100)

            qa_answers = {
                "language": "typescript",
                "testing_framework": "vitest",
                "architecture_pattern": "clean-architecture"
            }

            # Generate rules structure
            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            # Verify structure created
            rules_dir = claude_dir / "rules"
            assert rules_dir.exists()

            # Verify files created
            assert (rules_dir / "code-style.md").exists()
            assert (rules_dir / "testing.md").exists()
            assert (rules_dir / "patterns" / "clean-architecture.md").exists()

            # Verify content
            code_style_content = (rules_dir / "code-style.md").read_text()
            assert "**/*.{ts,tsx}" in code_style_content
            assert "TypeScript" in code_style_content

            testing_content = (rules_dir / "testing.md").read_text()
            assert "vitest" in testing_content

            clean_arch_content = (rules_dir / "patterns" / "clean-architecture.md").read_text()
            assert "Clean" in clean_arch_content or "clean" in clean_arch_content.lower()

    def test_size_validation_error(self):
        """Test that size validation works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            claude_dir = template_dir / ".claude"
            claude_dir.mkdir(parents=True)

            # Create a large CLAUDE.md that exceeds limit
            (claude_dir / "CLAUDE.md").write_text("x" * 6000)

            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "layered"
            }

            # Should raise ValueError due to size
            with pytest.raises(ValueError, match="CLAUDE.md size"):
                generate_rules_structure(
                    template_dir=str(template_dir),
                    qa_answers=qa_answers,
                    claude_md_size_limit=5000
                )

    def test_missing_qa_answers_graceful_handling(self):
        """Test graceful handling of missing Q&A answers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            claude_dir = template_dir / ".claude"
            claude_dir.mkdir(parents=True)

            qa_answers = {}  # Empty answers

            # Should create directory structure but may skip file generation
            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=5000
            )

            # Should at least create the rules directory
            rules_dir = claude_dir / "rules"
            assert rules_dir.exists()

    def test_custom_size_limit(self):
        """Test custom CLAUDE.md size limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            claude_dir = template_dir / ".claude"
            claude_dir.mkdir(parents=True)

            # Create CLAUDE.md that's under custom limit but over default
            (claude_dir / "CLAUDE.md").write_text("x" * 7000)

            qa_answers = {
                "language": "python",
                "testing_framework": "pytest",
                "architecture_pattern": "layered"
            }

            # Should succeed with custom limit
            generate_rules_structure(
                template_dir=str(template_dir),
                qa_answers=qa_answers,
                claude_md_size_limit=10000  # Custom higher limit
            )

            # Verify structure created
            rules_dir = claude_dir / "rules"
            assert rules_dir.exists()
            assert (rules_dir / "code-style.md").exists()

    def test_all_supported_languages(self):
        """Test rules generation for all supported languages."""
        languages = {
            "python": "**/*.py",
            "typescript": "**/*.{ts,tsx}",
            "javascript": "**/*.{js,jsx}",
            "csharp": "**/*.cs",
            "java": "**/*.java"
        }

        for language, expected_path in languages.items():
            with tempfile.TemporaryDirectory() as tmpdir:
                template_dir = Path(tmpdir)
                claude_dir = template_dir / ".claude"
                claude_dir.mkdir(parents=True)

                qa_answers = {
                    "language": language,
                    "testing_framework": "pytest",
                    "architecture_pattern": "layered"
                }

                generate_rules_structure(
                    template_dir=str(template_dir),
                    qa_answers=qa_answers,
                    claude_md_size_limit=5000
                )

                # Verify language-specific path pattern
                code_style_content = (claude_dir / "rules" / "code-style.md").read_text()
                assert expected_path in code_style_content, \
                    f"Expected '{expected_path}' in code-style.md for {language}"

    def test_all_testing_frameworks(self):
        """Test rules generation for all testing frameworks."""
        frameworks = ["pytest", "vitest", "jest", "xunit", "nunit", "junit"]

        for framework in frameworks:
            with tempfile.TemporaryDirectory() as tmpdir:
                template_dir = Path(tmpdir)
                claude_dir = template_dir / ".claude"
                claude_dir.mkdir(parents=True)

                qa_answers = {
                    "language": "python",
                    "testing_framework": framework,
                    "architecture_pattern": "layered"
                }

                generate_rules_structure(
                    template_dir=str(template_dir),
                    qa_answers=qa_answers,
                    claude_md_size_limit=5000
                )

                # Verify framework-specific content
                testing_content = (claude_dir / "rules" / "testing.md").read_text()
                assert framework in testing_content.lower(), \
                    f"Expected '{framework}' in testing.md"

    def test_all_architecture_patterns(self):
        """Test rules generation for all architecture patterns."""
        patterns = {
            "clean-architecture": "Clean Architecture",
            "mvvm": "MVVM",
            "layered": "Layered",
            "hexagonal": "Hexagonal",
            "microservices": "Microservices"
        }

        for pattern, expected_text in patterns.items():
            with tempfile.TemporaryDirectory() as tmpdir:
                template_dir = Path(tmpdir)
                claude_dir = template_dir / ".claude"
                claude_dir.mkdir(parents=True)

                qa_answers = {
                    "language": "python",
                    "testing_framework": "pytest",
                    "architecture_pattern": pattern
                }

                generate_rules_structure(
                    template_dir=str(template_dir),
                    qa_answers=qa_answers,
                    claude_md_size_limit=5000
                )

                # Verify pattern file created
                pattern_file = claude_dir / "rules" / "patterns" / f"{pattern}.md"
                assert pattern_file.exists(), \
                    f"Expected pattern file for {pattern}"

                # Verify pattern-specific content
                pattern_content = pattern_file.read_text()
                assert expected_text in pattern_content or expected_text.lower() in pattern_content.lower(), \
                    f"Expected '{expected_text}' in {pattern}.md"
