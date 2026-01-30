"""
Stub Detection Library

Detects placeholder comments and stub implementations in code files to prevent
non-functional implementations from passing quality gates.

Core Capabilities:
  • Language-agnostic stub detection (Python, TypeScript, Go, Rust, C#)
  • Placeholder comment detection (TODO, FIXME, "In production...")
  • Stub pattern detection (return [], pass, NotImplementedError, etc.)
  • Library import verification for migration tasks
  • File:line references for all findings

Usage:
    from lib.stub_detector import detect_stubs, verify_library_usage

    # Detect stubs in a file
    findings = detect_stubs(Path("src/service.py"), content)

    # Verify library usage
    findings = verify_library_usage(
        Path("src/service.py"),
        content,
        required_imports=["from graphiti_core import Graphiti"]
    )

See Also:
    docs/guides/stub-detection.md - User guide for Phase 4.5 integration
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


__all__ = [
    # Core detection
    'detect_stubs',
    'detect_language',
    'verify_library_usage',

    # Data structures
    'StubFinding',

    # Constants
    'LANGUAGE_PATTERNS',
]


@dataclass
class StubFinding:
    """
    A detected stub pattern in code.

    Attributes:
        file_path: Path to the file containing the stub
        line_number: Line number where stub was found (1-indexed)
        pattern_type: Type of pattern detected (e.g., "placeholder_comment")
        description: Human-readable description of the finding
        severity: Severity level ("warning" | "error")
        language: Detected language (e.g., "python", "typescript")

    Examples:
        >>> finding = StubFinding(
        ...     file_path=Path("src/service.py"),
        ...     line_number=42,
        ...     pattern_type="placeholder_comment",
        ...     description="Found placeholder comment in python code",
        ...     severity="error",
        ...     language="python"
        ... )
    """
    file_path: Path
    line_number: int
    pattern_type: str
    description: str
    severity: str
    language: str


# Language-specific detection patterns
# Format: {language: {extensions, comment_patterns, stub_patterns}}
LANGUAGE_PATTERNS: Dict[str, Dict] = {
    "python": {
        "extensions": [".py"],
        "comment_patterns": [
            r'#.*[Ii]n production.*would',
            r'#\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'return \[\]',
            r'return None',
            r'^\s*pass\s*$',
            r'raise NotImplementedError',
        ],
    },
    "typescript": {
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
            r'/\*.*[Ii]n production.*would.*\*/',
        ],
        "stub_patterns": [
            r'return \[\]',
            r'return null',
            r'return undefined',
            r'throw new Error\(["\']Not implemented',
        ],
    },
    "go": {
        "extensions": [".go"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'return nil',
            r'panic\(["\']not implemented',
        ],
    },
    "rust": {
        "extensions": [".rs"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'todo!\(\)',
            r'unimplemented!\(\)',
            r'panic!\(["\']not implemented',
        ],
    },
    "csharp": {
        "extensions": [".cs"],
        "comment_patterns": [
            r'//.*[Ii]n production.*would',
            r'//\s*(TODO|FIXME).*implement',
        ],
        "stub_patterns": [
            r'throw new NotImplementedException\(\)',
            r'return null',
            r'return default',
        ],
    },
}


# Pre-compile regex patterns for performance
_COMPILED_PATTERNS: Dict[str, Dict[str, List[re.Pattern]]] = {}


def _compile_patterns() -> None:
    """
    Pre-compile all regex patterns for performance.

    Called once at module load time.
    """
    global _COMPILED_PATTERNS

    for lang, patterns in LANGUAGE_PATTERNS.items():
        _COMPILED_PATTERNS[lang] = {
            "comment": [re.compile(p, re.IGNORECASE) for p in patterns["comment_patterns"]],
            "stub": [re.compile(p) for p in patterns["stub_patterns"]],
        }


def detect_language(file_path: Path) -> str:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to the file to analyze

    Returns:
        Language name (e.g., "python", "typescript") or "unknown" if not recognized

    Examples:
        >>> detect_language(Path("service.py"))
        'python'
        >>> detect_language(Path("component.tsx"))
        'typescript'
        >>> detect_language(Path("unknown.xyz"))
        'unknown'
    """
    ext = file_path.suffix.lower()
    for lang, config in LANGUAGE_PATTERNS.items():
        if ext in config["extensions"]:
            return lang
    return "unknown"


def _check_patterns(
    line: str,
    patterns: List[re.Pattern],
    file_path: Path,
    line_number: int,
    pattern_type: str,
    severity: str,
    language: str,
    description_template: str
) -> Optional[StubFinding]:
    """
    Check a line against a list of compiled regex patterns.

    Helper function to reduce duplication between comment and stub pattern checks.

    Args:
        line: Line of code to check
        patterns: List of compiled regex patterns
        file_path: Path to file being checked
        line_number: Current line number (1-indexed)
        pattern_type: Type of pattern ("placeholder_comment" | "stub_implementation")
        severity: Severity level ("warning" | "error")
        language: Detected language
        description_template: Description template with {pattern} placeholder

    Returns:
        StubFinding if pattern matches, None otherwise
    """
    for pattern in patterns:
        if pattern.search(line):
            return StubFinding(
                file_path=file_path,
                line_number=line_number,
                pattern_type=pattern_type,
                description=description_template.format(
                    language=language,
                    pattern=pattern.pattern
                ),
                severity=severity,
                language=language
            )
    return None


def detect_stubs(file_path: Path, content: str) -> List[StubFinding]:
    """
    Detect potential stub implementations in a file (language-agnostic).

    Scans for:
      1. Placeholder comments (# TODO implement, // In production, etc.)
      2. Stub patterns (return [], pass, raise NotImplementedError, etc.)

    Args:
        file_path: Path to the file being analyzed
        content: File content as string

    Returns:
        List of StubFinding objects (one per detected stub)

    Examples:
        >>> content = '''
        ... def get_users():
        ...     # TODO implement this
        ...     return []
        ... '''
        >>> findings = detect_stubs(Path("service.py"), content)
        >>> len(findings)
        2
        >>> findings[0].pattern_type
        'placeholder_comment'
        >>> findings[1].pattern_type
        'stub_implementation'
    """
    findings = []
    language = detect_language(file_path)

    if language == "unknown":
        return findings  # Skip unknown languages

    patterns = _COMPILED_PATTERNS[language]
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Check comment patterns (placeholder comments)
        finding = _check_patterns(
            line=line,
            patterns=patterns["comment"],
            file_path=file_path,
            line_number=i,
            pattern_type="placeholder_comment",
            severity="error",
            language=language,
            description_template="Found placeholder comment in {language} code"
        )
        if finding:
            findings.append(finding)
            continue  # Only report once per line

        # Check stub patterns (empty implementations)
        finding = _check_patterns(
            line=line,
            patterns=patterns["stub"],
            file_path=file_path,
            line_number=i,
            pattern_type="stub_implementation",
            severity="warning",
            language=language,
            description_template="Found stub implementation pattern: {pattern}"
        )
        if finding:
            findings.append(finding)

    return findings


def verify_library_usage(
    file_path: Path,
    content: str,
    required_imports: Optional[List[str]] = None,
    required_calls: Optional[List[str]] = None
) -> List[StubFinding]:
    """
    Verify a file uses expected library imports and calls.

    Works across languages - just checks if the string is present.

    Args:
        file_path: Path to the file being analyzed
        content: File content as string
        required_imports: Expected import statements (e.g., ["from graphiti_core import Graphiti"])
        required_calls: Expected library calls (e.g., ["graphiti.search"])

    Returns:
        List of StubFinding objects for missing imports/calls

    Examples:
        >>> content = '''
        ... from other_lib import Thing
        ... def process():
        ...     pass
        ... '''
        >>> findings = verify_library_usage(
        ...     Path("service.py"),
        ...     content,
        ...     required_imports=["from graphiti_core import Graphiti"]
        ... )
        >>> len(findings)
        1
        >>> findings[0].pattern_type
        'missing_import'

    Note:
        This function checks for string presence only. It does not:
        - Parse AST to verify actual usage
        - Check if imports are commented out
        - Verify correct library call signatures

        For migration tasks, presence is sufficient to confirm the attempt
        to use the library was made (vs returning stubs).
    """
    language = detect_language(file_path)
    findings = []

    # Check required imports
    if required_imports:
        for imp in required_imports:
            if imp not in content:
                findings.append(StubFinding(
                    file_path=file_path,
                    line_number=1,
                    pattern_type="missing_import",
                    description=f"Expected import '{imp}' not found",
                    severity="error",
                    language=language
                ))

    # Check required calls (optional verification)
    if required_calls:
        for call in required_calls:
            if call not in content:
                findings.append(StubFinding(
                    file_path=file_path,
                    line_number=1,
                    pattern_type="missing_call",
                    description=f"Expected library call '{call}' not found",
                    severity="warning",
                    language=language
                ))

    return findings


# Compile patterns at module load time
_compile_patterns()
