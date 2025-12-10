"""
Placeholder Patterns - Centralized pattern definitions for placeholder extraction.

TASK-IMP-TC-F8A3: Centralized placeholder patterns (DRY compliance)

This module provides language-specific patterns for identifying and extracting
placeholders from source code files. Patterns are organized by language and
can be easily extended for new languages.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlaceholderResult:
    """Result of placeholder extraction."""
    content: str  # Content with placeholders substituted
    placeholders: List[str]  # List of placeholder names found
    coverage: float  # Percentage of identifiable values replaced (0.0-1.0)


class PlaceholderPatterns:
    """
    Centralized placeholder pattern definitions.

    Patterns are tuples of (regex_pattern, replacement_placeholder, description).
    The regex should have a single capture group for the value to replace.
    """

    # Common placeholders used across all languages
    COMMON_PLACEHOLDERS = {
        'ProjectName': '{{ProjectName}}',
        'Namespace': '{{Namespace}}',
        'Author': '{{Author}}',
        'EntityName': '{{EntityName}}',
        'EntityNamePlural': '{{EntityNamePlural}}',
        'ModuleName': '{{ModuleName}}',
        'ClassName': '{{ClassName}}',
        'FunctionName': '{{FunctionName}}',
        'ServiceName': '{{ServiceName}}',
        'RepositoryName': '{{RepositoryName}}',
    }

    # Python-specific patterns
    PYTHON_PATTERNS: List[Tuple[str, str, str]] = [
        # Class definitions: class UserService -> class {{ClassName}}
        (r'\bclass\s+([A-Z][a-zA-Z0-9]+)(?:\(|:)', '{{ClassName}}', 'class name'),
        # Import statements: from myproject.module -> from {{ProjectName}}.module
        (r'\bfrom\s+([a-z][a-z0-9_]+)\.[a-z]', '{{ProjectName}}', 'project import'),
        # Module docstrings often contain project names
        (r'"""[^"]*\b([A-Z][a-zA-Z0-9]+)\s+(?:API|Service|Module)', '{{ProjectName}}', 'docstring project'),
    ]

    # JavaScript/TypeScript patterns
    JAVASCRIPT_PATTERNS: List[Tuple[str, str, str]] = [
        # Class definitions: class UserService -> class {{ClassName}}
        (r'\bclass\s+([A-Z][a-zA-Z0-9]+)\s*(?:extends|implements|{)', '{{ClassName}}', 'class name'),
        # Function components: function UserProfile -> function {{ComponentName}}
        (r'\bfunction\s+([A-Z][a-zA-Z0-9]+)\s*\(', '{{ComponentName}}', 'function component'),
        # Const components: const UserProfile = -> const {{ComponentName}} =
        (r'\bconst\s+([A-Z][a-zA-Z0-9]+)\s*=\s*(?:\(|function)', '{{ComponentName}}', 'const component'),
        # Export default class
        (r'\bexport\s+default\s+class\s+([A-Z][a-zA-Z0-9]+)', '{{ClassName}}', 'export class'),
        # Import from project: import { x } from 'myproject'
        (r"from\s+['\"](@?[a-z][a-z0-9-]*)/", '{{ProjectName}}/', 'project import'),
    ]

    # Svelte patterns (extends JavaScript)
    SVELTE_PATTERNS: List[Tuple[str, str, str]] = [
        # Script tag class imports
        (r'import\s+{[^}]*}\s+from\s+[\'"]\.\.?/lib/([a-z][a-z0-9-]*)/', '{{ModuleName}}/', 'lib import'),
        # Store imports: import { sessions } from '$lib/stores/sessions'
        (r"from\s+['\"]\\$lib/stores/([a-z][a-z0-9-]*)['\"]", '{{StoreName}}', 'store import'),
    ]

    # C# patterns
    CSHARP_PATTERNS: List[Tuple[str, str, str]] = [
        # Namespace declarations: namespace MyCompany.MyApp.Domain
        (r'namespace\s+([A-Za-z][A-Za-z0-9.]+)', '{{Namespace}}', 'namespace'),
        # Class declarations: public class UserService
        (r'\b(?:public|internal|private)?\s*(?:sealed|abstract|partial)?\s*class\s+([A-Z][a-zA-Z0-9]+)', '{{ClassName}}', 'class name'),
        # Interface declarations: public interface IUserService
        (r'\binterface\s+(I[A-Z][a-zA-Z0-9]+)', '{{InterfaceName}}', 'interface name'),
        # Record declarations: public record UserDto
        (r'\b(?:public|internal)?\s*record\s+([A-Z][a-zA-Z0-9]+)', '{{RecordName}}', 'record name'),
    ]

    # Generic entity patterns (apply to all languages)
    ENTITY_PATTERNS: List[Tuple[str, str, str]] = [
        # Common entity names in code
        (r'\b(User|Product|Order|Customer|Account|Profile|Session|Item|Category|Post|Comment)(?:s|es|ies)?\b', '{{EntityName}}', 'entity name'),
        # Service patterns: UserService, ProductRepository
        (r'\b([A-Z][a-z]+)(?:Service|Repository|Controller|Handler|Manager)\b', '{{EntityName}}', 'service entity'),
    ]

    # File extension to language mapping
    EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.svelte': 'svelte',
        '.cs': 'csharp',
        '.java': 'java',
        '.kt': 'kotlin',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
    }

    @classmethod
    def get_patterns_for_extension(cls, file_ext: str) -> List[Tuple[str, str, str]]:
        """
        Get placeholder patterns for a file extension.

        Args:
            file_ext: File extension including dot (e.g., '.py', '.ts')

        Returns:
            List of (pattern, replacement, description) tuples
        """
        language = cls.EXTENSION_LANGUAGE_MAP.get(file_ext.lower(), 'generic')

        patterns = []

        # Add language-specific patterns
        if language == 'python':
            patterns.extend(cls.PYTHON_PATTERNS)
        elif language in ('javascript', 'typescript'):
            patterns.extend(cls.JAVASCRIPT_PATTERNS)
        elif language == 'svelte':
            patterns.extend(cls.JAVASCRIPT_PATTERNS)
            patterns.extend(cls.SVELTE_PATTERNS)
        elif language == 'csharp':
            patterns.extend(cls.CSHARP_PATTERNS)

        # Add generic entity patterns for all languages
        patterns.extend(cls.ENTITY_PATTERNS)

        return patterns


class PlaceholderExtractor:
    """
    Extract placeholders from source code files.

    Uses language-specific patterns to identify project-specific values
    and replace them with standardized placeholders.

    Following SRP: This class only handles placeholder extraction.
    """

    # Coverage threshold for validation (80%)
    COVERAGE_THRESHOLD = 0.8

    def __init__(self, manifest: Optional[Dict] = None):
        """
        Initialize extractor with optional manifest for project-specific replacements.

        Args:
            manifest: Optional manifest dict with 'name', 'author' fields
        """
        self.manifest = manifest or {}
        self._replacement_count = 0
        self._identifiable_count = 0

    def extract(self, content: str, file_path: str) -> PlaceholderResult:
        """
        Extract placeholders from file content.

        Args:
            content: Source code content
            file_path: Path to file (used to determine language)

        Returns:
            PlaceholderResult with modified content and placeholder list
        """
        self._replacement_count = 0
        self._identifiable_count = 0

        # Get file extension
        file_ext = Path(file_path).suffix.lower()

        # Start with original content
        modified_content = content
        placeholders_found: List[str] = []

        # Apply manifest-based replacements first (highest priority)
        modified_content, manifest_placeholders = self._apply_manifest_replacements(
            modified_content
        )
        placeholders_found.extend(manifest_placeholders)

        # Apply language-specific patterns
        patterns = PlaceholderPatterns.get_patterns_for_extension(file_ext)
        for pattern, replacement, description in patterns:
            modified_content, found = self._apply_pattern(
                modified_content, pattern, replacement
            )
            if found and replacement not in placeholders_found:
                # Extract placeholder name from {{Name}} format
                placeholder_name = replacement.replace('{{', '').replace('}}', '').rstrip('/')
                if placeholder_name not in placeholders_found:
                    placeholders_found.append(placeholder_name)

        # Calculate coverage
        coverage = self._calculate_coverage()

        return PlaceholderResult(
            content=modified_content,
            placeholders=placeholders_found,
            coverage=coverage
        )

    def _apply_manifest_replacements(self, content: str) -> Tuple[str, List[str]]:
        """
        Apply project-specific replacements from manifest.

        Args:
            content: Source code content

        Returns:
            Tuple of (modified_content, list_of_placeholder_names)
        """
        placeholders = []

        # Replace project name if in manifest
        project_name = self.manifest.get('name', '')
        if project_name and len(project_name) >= 3:
            # Escape for regex
            escaped_name = re.escape(project_name)
            # Replace project name (case-insensitive for paths)
            if re.search(escaped_name, content, re.IGNORECASE):
                content = re.sub(escaped_name, '{{ProjectName}}', content, flags=re.IGNORECASE)
                placeholders.append('ProjectName')
                self._replacement_count += 1
            self._identifiable_count += 1

        # Replace author if in manifest
        author = self.manifest.get('author', '')
        if author and len(author) >= 2:
            escaped_author = re.escape(author)
            if re.search(escaped_author, content):
                content = re.sub(escaped_author, '{{Author}}', content)
                placeholders.append('Author')
                self._replacement_count += 1
            self._identifiable_count += 1

        return content, placeholders

    def _apply_pattern(
        self,
        content: str,
        pattern: str,
        replacement: str
    ) -> Tuple[str, bool]:
        """
        Apply a single pattern replacement.

        Args:
            content: Source code content
            pattern: Regex pattern with capture group
            replacement: Placeholder to substitute

        Returns:
            Tuple of (modified_content, was_found)
        """
        self._identifiable_count += 1

        # Find all matches
        matches = re.findall(pattern, content)
        if not matches:
            return content, False

        # For each unique match, replace it
        for match in set(matches):
            if isinstance(match, tuple):
                match = match[0]  # Use first capture group

            # Only replace if match is substantial (not common words)
            if len(match) >= 2 and not self._is_common_word(match):
                # Create specific replacement that preserves structure
                # e.g., class UserService -> class {{ClassName}}
                # But we need to be careful not to replace too much
                escaped_match = re.escape(match)
                content = re.sub(r'\b' + escaped_match + r'\b', replacement, content)
                self._replacement_count += 1

        return content, True

    def _is_common_word(self, word: str) -> bool:
        """Check if word is too common to replace."""
        common_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'should', 'may', 'might', 'must',
            'if', 'else', 'elif', 'for', 'while', 'try', 'except',
            'return', 'yield', 'import', 'from', 'as', 'with',
            'class', 'def', 'function', 'const', 'let', 'var',
            'public', 'private', 'protected', 'static', 'final',
            'true', 'false', 'null', 'none', 'undefined',
            'string', 'int', 'float', 'bool', 'boolean', 'void',
            'list', 'dict', 'array', 'object', 'any',
        }
        return word.lower() in common_words

    def _calculate_coverage(self) -> float:
        """Calculate replacement coverage."""
        if self._identifiable_count == 0:
            return 1.0  # Nothing to replace = full coverage
        return self._replacement_count / self._identifiable_count

    def validate_coverage(self, result: PlaceholderResult) -> Tuple[bool, str]:
        """
        Validate that placeholder coverage meets threshold.

        Args:
            result: PlaceholderResult from extraction

        Returns:
            Tuple of (is_valid, message)
        """
        if result.coverage >= self.COVERAGE_THRESHOLD:
            return True, f"Coverage {result.coverage:.1%} meets threshold"

        return False, (
            f"Coverage {result.coverage:.1%} below {self.COVERAGE_THRESHOLD:.0%} threshold. "
            f"Consider adding more patterns for this language."
        )
