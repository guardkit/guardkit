"""
Pattern Example Extraction for Template Generation

Extracts codebase-specific code examples to enrich pattern files in .claude/rules/patterns/.
Reuses PatternCategoryDetector from stratified_sampler for pattern detection.

TASK-PDI-003: Enrich pattern files with codebase-specific examples
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .codebase_analyzer.stratified_sampler import PatternCategoryDetector, PatternCategory

logger = logging.getLogger(__name__)


@dataclass
class CodeExample:
    """Represents an extracted code example."""
    pattern: str  # Pattern name (e.g., "Repository Pattern")
    file_path: str  # Relative path to source file
    snippet: str  # Code snippet (10-25 lines)
    language: str  # Language identifier for syntax highlighting
    context: str  # Brief context about the example
    best_practices: List[str]  # Extracted best practices (3-5 items)


class PatternExampleExtractor:
    """
    Extracts pattern-specific code examples from codebase samples.

    Uses PatternCategoryDetector to identify pattern types, then extracts
    representative code snippets with best practices.
    """

    # Pattern name mappings (from category to display name)
    PATTERN_NAMES = {
        PatternCategory.CRUD_CREATE: "CRUD Create Pattern",
        PatternCategory.CRUD_READ: "CRUD Read Pattern",
        PatternCategory.CRUD_UPDATE: "CRUD Update Pattern",
        PatternCategory.CRUD_DELETE: "CRUD Delete Pattern",
        PatternCategory.VALIDATORS: "Validator Pattern",
        PatternCategory.SPECIFICATIONS: "Specification Pattern",
        PatternCategory.REPOSITORIES: "Repository Pattern",
        PatternCategory.INFRASTRUCTURE: "Infrastructure Pattern",
        PatternCategory.QUERIES: "Query Pattern",
    }

    def __init__(self, pattern_detector: Optional[PatternCategoryDetector] = None):
        """
        Initialize pattern example extractor.

        Args:
            pattern_detector: Optional custom pattern detector
        """
        self.pattern_detector = pattern_detector or PatternCategoryDetector()

    def extract_examples(
        self,
        file_samples: List[Dict[str, str]],
        max_examples_per_pattern: int = 2
    ) -> Dict[str, List[CodeExample]]:
        """
        Extract code examples from file samples, grouped by pattern.

        Args:
            file_samples: List of dicts with 'path' and 'content' keys
            max_examples_per_pattern: Maximum examples to extract per pattern

        Returns:
            Dictionary mapping pattern name -> list of CodeExample objects

        Example:
            {
                "Repository Pattern": [
                    CodeExample(pattern="Repository Pattern", file_path="...", ...),
                    CodeExample(pattern="Repository Pattern", file_path="...", ...)
                ],
                "Validator Pattern": [...]
            }
        """
        examples_by_pattern: Dict[str, List[CodeExample]] = {}

        # Group files by pattern category
        categorized = self._categorize_samples(file_samples)

        # Extract examples from each category
        for category, samples in categorized.items():
            pattern_name = self.PATTERN_NAMES.get(category, category)
            examples = []

            for sample in samples[:max_examples_per_pattern]:
                example = self._extract_single_example(
                    sample,
                    pattern_name,
                    category
                )
                if example:
                    examples.append(example)

            if examples:
                examples_by_pattern[pattern_name] = examples

        logger.info(f"Extracted examples for {len(examples_by_pattern)} patterns")
        return examples_by_pattern

    def _categorize_samples(
        self,
        file_samples: List[Dict[str, str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Categorize file samples by pattern.

        Args:
            file_samples: List of file samples with 'path' and 'content'

        Returns:
            Dictionary mapping category -> list of samples
        """
        categorized: Dict[str, List[Dict[str, str]]] = {}

        for sample in file_samples:
            path = Path(sample['path'])
            category = self.pattern_detector.detect_pattern_from_path(path)

            if category != PatternCategory.OTHER:
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(sample)

        return categorized

    def _extract_single_example(
        self,
        sample: Dict[str, str],
        pattern_name: str,
        category: str
    ) -> Optional[CodeExample]:
        """
        Extract a single code example from a file sample.

        Args:
            sample: File sample with 'path' and 'content'
            pattern_name: Human-readable pattern name
            category: Pattern category identifier

        Returns:
            CodeExample object or None if extraction fails
        """
        try:
            file_path = sample['path']
            content = sample['content']

            # Determine language from file extension
            language = self._detect_language(file_path)

            # Extract meaningful snippet (10-25 lines)
            snippet = self._extract_snippet(content, category, max_lines=25)

            # Generate context description
            context = self._generate_context(file_path, category)

            # Extract best practices
            best_practices = self._extract_best_practices(content, category)

            if snippet:
                return CodeExample(
                    pattern=pattern_name,
                    file_path=file_path,
                    snippet=snippet,
                    language=language,
                    context=context,
                    best_practices=best_practices
                )

        except Exception as e:
            logger.warning(f"Failed to extract example from {sample.get('path', 'unknown')}: {e}")

        return None

    def _extract_snippet(
        self,
        content: str,
        category: str,
        max_lines: int = 25
    ) -> str:
        """
        Extract meaningful code snippet based on pattern category.

        Focuses on extracting the most representative portion of the code
        that demonstrates the pattern.

        Args:
            content: Full file content
            category: Pattern category
            max_lines: Maximum lines to extract

        Returns:
            Code snippet string
        """
        lines = content.split('\n')

        # Strategy: Find key method/function based on category
        if category in PatternCategory.get_crud_categories():
            snippet = self._extract_crud_method(lines, category)
        elif category == PatternCategory.REPOSITORIES:
            snippet = self._extract_repository_method(lines)
        elif category == PatternCategory.VALIDATORS:
            snippet = self._extract_validator_method(lines)
        elif category == PatternCategory.QUERIES:
            snippet = self._extract_query_method(lines)
        else:
            # Default: Extract first class/function definition
            snippet = self._extract_primary_definition(lines)

        # Truncate to max_lines if needed
        snippet_lines = snippet.split('\n')
        if len(snippet_lines) > max_lines:
            snippet_lines = snippet_lines[:max_lines]
            snippet_lines.append('    // ... (truncated)')

        return '\n'.join(snippet_lines)

    def _extract_crud_method(self, lines: List[str], category: str) -> str:
        """Extract CRUD operation method."""
        # Look for method signatures matching operation type
        keywords = {
            PatternCategory.CRUD_CREATE: ['Create', 'Add', 'Insert', 'Post'],
            PatternCategory.CRUD_READ: ['Get', 'Read', 'Fetch', 'Query', 'List'],
            PatternCategory.CRUD_UPDATE: ['Update', 'Modify', 'Put', 'Patch'],
            PatternCategory.CRUD_DELETE: ['Delete', 'Remove', 'Destroy']
        }

        search_keywords = keywords.get(category, [])
        return self._extract_method_by_keywords(lines, search_keywords)

    def _extract_repository_method(self, lines: List[str]) -> str:
        """Extract representative repository method."""
        # Look for async repository methods
        keywords = ['async', 'Task<', 'public', 'IEnumerable', 'List', 'Get', 'Find']
        return self._extract_method_by_keywords(lines, keywords)

    def _extract_validator_method(self, lines: List[str]) -> str:
        """Extract validator implementation."""
        keywords = ['Validate', 'IsValid', 'RuleFor', 'Specification', 'Check']
        return self._extract_method_by_keywords(lines, keywords)

    def _extract_query_method(self, lines: List[str]) -> str:
        """Extract query implementation."""
        keywords = ['Query', 'Select', 'Where', 'Execute', 'Fetch']
        return self._extract_method_by_keywords(lines, keywords)

    def _extract_method_by_keywords(
        self,
        lines: List[str],
        keywords: List[str]
    ) -> str:
        """
        Extract method containing any of the specified keywords.

        Prefers actual methods over constructors.

        Args:
            lines: File content lines
            keywords: Keywords to search for

        Returns:
            Extracted method as string
        """
        # First pass: Try to find non-constructor methods
        method_lines = self._find_method_with_keywords(lines, keywords, skip_constructors=True)
        if method_lines:
            return '\n'.join(method_lines)

        # Second pass: Accept constructors if no other methods found
        method_lines = self._find_method_with_keywords(lines, keywords, skip_constructors=False)
        if method_lines:
            return '\n'.join(method_lines)

        # Fallback: Return first 20 non-empty lines
        return '\n'.join(line for line in lines[:20] if line.strip())

    def _find_method_with_keywords(
        self,
        lines: List[str],
        keywords: List[str],
        skip_constructors: bool = False
    ) -> List[str]:
        """
        Find a method containing keywords.

        Args:
            lines: File content lines
            keywords: Keywords to search for
            skip_constructors: If True, skip constructor methods

        Returns:
            Method lines or empty list if not found
        """
        in_method = False
        method_lines = []
        brace_count = 0

        for i, line in enumerate(lines):
            # Check if line contains any keyword and looks like method signature
            if not in_method:
                line_lower = line.lower()
                if any(keyword.lower() in line_lower for keyword in keywords):
                    # Check if it's a method declaration (has parentheses)
                    if '(' in line and ('{' in line or i + 1 < len(lines)):
                        # Skip constructors if requested (they have class name in signature)
                        if skip_constructors:
                            # Simple heuristic: constructors often have no return type
                            # and method name matches class name pattern
                            if not any(ret_type in line for ret_type in ['Task', 'ErrorOr', 'async', 'public void', 'public int', 'public string', 'IEnumerable']):
                                continue

                        in_method = True
                        method_lines.append(line)
                        brace_count += line.count('{') - line.count('}')
                        continue

            if in_method:
                method_lines.append(line)
                brace_count += line.count('{') - line.count('}')

                # Stop when method ends (braces balanced)
                if brace_count == 0 and len(method_lines) > 1:
                    break

        return method_lines

    def _extract_primary_definition(self, lines: List[str]) -> str:
        """
        Extract primary class or function definition.

        Args:
            lines: File content lines

        Returns:
            Primary definition snippet
        """
        # Look for class/interface definition
        for i, line in enumerate(lines):
            if re.match(r'\s*(public|private|internal|protected)?\s*(class|interface|abstract)', line):
                # Extract class definition and first few members
                snippet_lines = []
                brace_count = 0
                started = False

                for j in range(i, min(i + 30, len(lines))):
                    snippet_lines.append(lines[j])
                    if '{' in lines[j]:
                        started = True
                    if started:
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        # Stop after first method or when getting too long
                        if len(snippet_lines) > 20:
                            break

                return '\n'.join(snippet_lines)

        # Fallback: First 15 lines
        return '\n'.join(lines[:15])

    def _detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to source file

        Returns:
            Language identifier for syntax highlighting
        """
        ext_to_lang = {
            '.cs': 'csharp',
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }

        ext = Path(file_path).suffix.lower()
        return ext_to_lang.get(ext, 'text')

    def _generate_context(self, file_path: str, category: str) -> str:
        """
        Generate context description for the example.

        Args:
            file_path: Path to source file
            category: Pattern category

        Returns:
            Brief context string
        """
        file_name = Path(file_path).name
        pattern_desc = self.PATTERN_NAMES.get(category, category)

        return f"From `{file_name}` demonstrating {pattern_desc}"

    def _extract_best_practices(
        self,
        content: str,
        category: str
    ) -> List[str]:
        """
        Extract best practices based on code patterns observed.

        Args:
            content: File content
            category: Pattern category

        Returns:
            List of 3-5 best practice strings
        """
        practices = []
        content_lower = content.lower()

        # Generic practices based on code observations
        if 'async' in content_lower and 'await' in content_lower:
            practices.append("Use async/await for asynchronous operations")

        if 'erroror' in content_lower or 'result<' in content_lower:
            practices.append("Return ErrorOr<T> or Result<T> for explicit error handling")

        if 'idisposable' in content_lower or 'using' in content:
            practices.append("Implement IDisposable for resource cleanup")

        if 'interface' in content_lower:
            practices.append("Depend on abstractions (interfaces) not implementations")

        # Category-specific practices
        if category == PatternCategory.REPOSITORIES:
            if 'readonly' in content_lower:
                practices.append("Use readonly fields for injected dependencies")
            if 'iqueryable' in content_lower:
                practices.append("Avoid exposing IQueryable outside repository")

        elif category == PatternCategory.VALIDATORS:
            if 'specification' in content_lower:
                practices.append("Use Specification pattern for complex validation rules")

        elif category in PatternCategory.get_crud_categories():
            if 'transaction' in content_lower:
                practices.append("Use transactions for data consistency")

        # Limit to 3-5 practices
        return practices[:5] if practices else [
            "Follow SOLID principles",
            "Write comprehensive unit tests",
            "Use meaningful names"
        ]


def extract_pattern_examples(
    file_samples: List[Dict[str, str]],
    max_examples_per_pattern: int = 2
) -> Dict[str, List[CodeExample]]:
    """
    Convenience function to extract pattern examples.

    Args:
        file_samples: List of file samples with 'path' and 'content'
        max_examples_per_pattern: Maximum examples per pattern

    Returns:
        Dictionary mapping pattern name -> list of CodeExample objects
    """
    extractor = PatternExampleExtractor()
    return extractor.extract_examples(file_samples, max_examples_per_pattern)
