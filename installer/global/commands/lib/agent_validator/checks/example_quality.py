"""Example quality validation checks."""

import re
from typing import Dict, List, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class ExampleQualityChecks:
    """Validates quality of code examples."""

    WEIGHT = 0.15  # 15% of overall score

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all example quality checks."""
        return {
            'example_completeness': self._check_example_completeness(content),
            'example_context': self._check_example_context(content)
        }

    def _extract_code_blocks(self, content: str) -> List[Tuple[int, str, str]]:
        """
        Extract code blocks with line numbers and language tags.

        Returns:
            List of (line_number, language, content) tuples
        """
        lines = content.split('\n')
        code_blocks = []

        in_code_block = False
        current_block = []
        block_start_line = None
        block_language = None

        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Starting code block
                    in_code_block = True
                    block_start_line = i + 1
                    # Extract language tag
                    lang_match = line.strip()[3:].strip()
                    block_language = lang_match if lang_match else None
                    current_block = []
                else:
                    # Ending code block
                    in_code_block = False
                    code_blocks.append((
                        block_start_line,
                        block_language,
                        '\n'.join(current_block)
                    ))
            elif in_code_block:
                current_block.append(line)

        return code_blocks

    def _check_example_completeness(self, content: str) -> CheckResult:
        """Check if code examples are complete and runnable."""
        code_blocks = self._extract_code_blocks(content)

        if not code_blocks:
            return CheckResult(
                name="Example Completeness",
                measured_value=0,
                threshold="runnable examples",
                score=0.0,
                weight=0.50,
                status="fail",
                message="No code examples found",
                line_number=None,
                suggestion="Add complete, runnable code examples"
            )

        # Check completeness indicators
        complete_count = 0
        for line_num, language, code in code_blocks:
            # Consider an example complete if it:
            # 1. Has a language tag
            # 2. Has at least 3 lines
            # 3. Contains function/class definitions or imports
            has_language = language is not None
            has_substance = len(code.split('\n')) >= 3
            has_structure = any(
                keyword in code.lower()
                for keyword in ['def ', 'class ', 'function ', 'import ', 'const ', 'let ', 'var ']
            )

            if has_language and has_substance and has_structure:
                complete_count += 1

        completeness_percentage = (complete_count / len(code_blocks) * 100) if code_blocks else 0

        if completeness_percentage >= 80:
            score = 10.0
            status = "pass"
            message = f"{completeness_percentage:.0f}% of examples are complete (target: ≥80%)"
            suggestion = None
        elif completeness_percentage >= 60:
            score = 7.0
            status = "warn"
            message = f"{completeness_percentage:.0f}% of examples are complete (target: ≥80%)"
            suggestion = "Add more structure to examples (functions, classes, imports)"
        else:
            score = 4.0
            status = "fail"
            message = f"Only {completeness_percentage:.0f}% of examples are complete (target: ≥80%)"
            suggestion = "Make examples runnable with proper structure and context"

        return CheckResult(
            name="Example Completeness",
            measured_value=completeness_percentage,
            threshold=80,
            score=score,
            weight=0.50,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )

    def _check_example_context(self, content: str) -> CheckResult:
        """Check if examples have explanatory context."""
        code_blocks = self._extract_code_blocks(content)

        if not code_blocks:
            return CheckResult(
                name="Example Context",
                measured_value=0,
                threshold="explained examples",
                score=0.0,
                weight=0.50,
                status="fail",
                message="No code examples to evaluate",
                line_number=None,
                suggestion="Add code examples with explanations"
            )

        lines = content.split('\n')
        explained_count = 0

        for line_num, language, code in code_blocks:
            # Check if there's explanatory text before the code block
            # Look at 5 lines before the code block
            start_check = max(0, line_num - 6)
            preceding_lines = lines[start_check:line_num - 1]

            # Look for explanatory markers
            has_explanation = any(
                # Comments or descriptive text
                line.strip() and not line.strip().startswith('#')
                and any(marker in line.lower() for marker in [
                    'example', 'this', 'here', 'following', 'shows', 'demonstrates',
                    'do:', 'don\'t:', '✅', '❌'
                ])
                for line in preceding_lines
            )

            if has_explanation:
                explained_count += 1

        context_percentage = (explained_count / len(code_blocks) * 100) if code_blocks else 0

        if context_percentage >= 70:
            score = 10.0
            status = "pass"
            message = f"{context_percentage:.0f}% of examples have context (target: ≥70%)"
            suggestion = None
        elif context_percentage >= 50:
            score = 6.0
            status = "warn"
            message = f"{context_percentage:.0f}% of examples have context (target: ≥70%)"
            suggestion = "Add explanations before code examples (what/why)"
        else:
            score = 3.0
            status = "fail"
            message = f"Only {context_percentage:.0f}% of examples have context (target: ≥70%)"
            suggestion = "Add clear explanations before each code example"

        return CheckResult(
            name="Example Context",
            measured_value=context_percentage,
            threshold=70,
            score=score,
            weight=0.50,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )
