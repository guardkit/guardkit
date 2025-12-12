"""Main rules structure generator orchestrator."""

import os
from pathlib import Path
from typing import Dict, Optional

from installer.core.lib.rules_generator.code_style import generate_code_style_rules
from installer.core.lib.rules_generator.testing import generate_testing_rules
from installer.core.lib.rules_generator.patterns import generate_pattern_rules


def generate_rules_structure(
    template_dir: str,
    qa_answers: Dict[str, str],
    claude_md_size_limit: int = 5000
) -> None:
    """
    Generate complete rules structure for a template.

    Creates .claude/rules/ directory with:
    - code-style.md (language-specific)
    - testing.md (framework-specific)
    - patterns/{pattern}.md (architecture-specific)

    Args:
        template_dir: Path to template directory
        qa_answers: Dictionary of Q&A session answers
        claude_md_size_limit: Maximum size for core CLAUDE.md in bytes

    Raises:
        ValueError: If CLAUDE.md exceeds size limit
    """
    template_path = Path(template_dir)
    claude_dir = template_path / ".claude"
    rules_dir = claude_dir / "rules"
    patterns_dir = rules_dir / "patterns"

    # Validate CLAUDE.md size if it exists
    claude_md_path = claude_dir / "CLAUDE.md"
    if claude_md_path.exists():
        claude_md_size = claude_md_path.stat().st_size
        if claude_md_size > claude_md_size_limit:
            raise ValueError(
                f"CLAUDE.md size ({claude_md_size} bytes) exceeds limit "
                f"({claude_md_size_limit} bytes). Consider moving content to rules/"
            )

    # Create directories
    rules_dir.mkdir(parents=True, exist_ok=True)
    patterns_dir.mkdir(parents=True, exist_ok=True)

    # Generate code-style.md
    language = qa_answers.get("language", "").lower()
    if language:
        code_style_content = generate_code_style_rules(language)
        (rules_dir / "code-style.md").write_text(code_style_content)

    # Generate testing.md
    testing_framework = qa_answers.get("testing_framework", "").lower()
    if testing_framework:
        testing_content = generate_testing_rules(testing_framework)
        (rules_dir / "testing.md").write_text(testing_content)

    # Generate patterns/{pattern}.md
    architecture_pattern = qa_answers.get("architecture_pattern", "").lower()
    if architecture_pattern:
        pattern_content = generate_pattern_rules(architecture_pattern)
        # Normalize pattern name for filename
        pattern_filename = architecture_pattern.replace("_", "-").replace(" ", "-")
        (patterns_dir / f"{pattern_filename}.md").write_text(pattern_content)


def validate_rules_structure(template_dir: str) -> bool:
    """
    Validate that rules structure was generated correctly.

    Args:
        template_dir: Path to template directory

    Returns:
        True if valid, False otherwise
    """
    template_path = Path(template_dir)
    rules_dir = template_path / ".claude" / "rules"

    if not rules_dir.exists():
        return False

    # Check for at least one rules file
    has_code_style = (rules_dir / "code-style.md").exists()
    has_testing = (rules_dir / "testing.md").exists()
    has_patterns = (rules_dir / "patterns").exists() and any(
        (rules_dir / "patterns").iterdir()
    )

    return has_code_style or has_testing or has_patterns
