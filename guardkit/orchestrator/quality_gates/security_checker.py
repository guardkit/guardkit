"""
Quick Security Checker for Coach Agent validation.

This module provides the SecurityChecker class that performs quick security checks
on code during AutoBuild validation. The checks are designed to be fast (substring
matching preferred over regex) while catching common security vulnerabilities.

Architecture:
    Implements hybrid detection pattern:
    - Substring matching for simple patterns (10x faster than regex)
    - Regex only when pattern matching is required
    - Path-based filtering to limit checks to relevant file types

Security Checks Implemented:
    Python (6 checks):
        - hardcoded-secrets: Hardcoded credentials detection
        - sql-injection: SQL string formatting detection
        - command-injection: Shell command injection detection
        - pickle-load: Deserialization attack detection
        - eval-exec: Dynamic code execution detection
        - debug-mode: Debug mode enabled detection

    JavaScript/TypeScript (5 checks):
        - dangerous-inner-html: React XSS risk detection
        - document-write: DOM XSS detection
        - inner-html: DOM manipulation XSS detection
        - new-function: Dynamic code generation detection
        - js-eval: JavaScript eval detection

    Universal (1 check):
        - cors-wildcard: CORS wildcard detection

    GitHub Actions (1 check):
        - gha-injection: Workflow injection detection

Example:
    >>> from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker
    >>>
    >>> checker = SecurityChecker("/path/to/worktree")
    >>> findings = checker.run_quick_checks()
    >>>
    >>> for finding in findings:
    ...     print(f"[{finding.severity}] {finding.check_id}: {finding.description}")
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Pattern, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Maximum length for matched text in findings (prevents excessive output)
MAX_MATCHED_TEXT_LENGTH = 200


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class SecurityFinding:
    """
    A security finding detected during quick checks.

    Attributes
    ----------
    check_id : str
        Unique identifier for the check (e.g., "hardcoded-secrets")
    severity : Literal["critical", "high", "medium", "low", "info"]
        Severity level of the finding
    description : str
        Human-readable description of the issue
    file_path : str
        Path to the file containing the issue
    line_number : int
        Line number where the issue was found
    matched_text : str
        The actual text that matched the pattern
    recommendation : str
        Actionable recommendation to fix the issue
    """

    check_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    file_path: str
    line_number: int
    matched_text: str
    recommendation: str


# ============================================================================
# Check Definitions
# ============================================================================


@dataclass
class SecurityCheck:
    """Definition of a security check."""

    check_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    recommendation: str
    file_extensions: Set[str]  # Empty set means all files
    # Detection can be substring(s) or regex pattern
    substrings: Optional[List[str]] = None
    regex_pattern: Optional[Pattern] = None
    # Function to filter false positives
    false_positive_filter: Optional[Callable[[str, int, List[str]], bool]] = None


# ============================================================================
# False Positive Filters
# ============================================================================


def _is_comment_line(line: str, file_ext: str) -> bool:
    """Check if a line is a comment."""
    stripped = line.strip()

    # Python/Shell style
    if file_ext in {".py", ".sh", ".yml", ".yaml"}:
        return stripped.startswith("#")

    # JavaScript/TypeScript style
    if file_ext in {".js", ".ts", ".jsx", ".tsx"}:
        return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")

    return False


def _filter_hardcoded_secrets(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for hardcoded-secrets check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # Skip if using environment variables
    if "os.environ" in line or "os.getenv" in line or "environ.get" in line:
        return True

    # Skip if value is empty string
    if re.search(r'(API_KEY|PASSWORD|SECRET)\s*=\s*["\']["\']', line):
        return True

    return False


def _filter_sql_injection(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for sql-injection check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # Only flag if it's an f-string with variable interpolation
    # Safe parameterized queries don't have f-string formatting
    if 'f"SELECT' not in line and "f'SELECT" not in line:
        return True

    return False


def _filter_command_injection(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for command-injection check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # Only flag f-string or string formatting variants
    # subprocess.run(["ls", path]) is safe (list form)
    if 'subprocess.run(f"' not in line and "subprocess.run(f'" not in line:
        if 'os.system(f"' not in line and "os.system(f'" not in line:
            return True

    return False


def _filter_eval_exec(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for eval-exec check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # ast.literal_eval is safe
    if "ast.literal_eval" in line or "literal_eval" in line:
        return True

    return False


def _filter_inner_html(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for inner-html check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # textContent is safe
    if ".textContent" in line:
        return True

    return False


def _filter_gha_injection(line: str, line_num: int, all_lines: List[str]) -> bool:
    """
    Filter false positives for GitHub Actions injection check.

    Returns True if this is a FALSE POSITIVE (should be skipped).
    """
    # Check if any dangerous context is present (not just safe ones)
    dangerous_contexts = [
        "github.event.issue.title",
        "github.event.issue.body",
        "github.event.pull_request.title",
        "github.event.pull_request.body",
        "github.event.comment.body",
        "github.event.review.body",
        "github.event.head_commit.message",
        "github.event.commits",
    ]

    has_dangerous_context = False
    for ctx in dangerous_contexts:
        if ctx in line:
            has_dangerous_context = True
            break

    # If no dangerous context, it's a false positive
    if not has_dangerous_context:
        return True

    return False


# ============================================================================
# Security Check Registry
# ============================================================================

# Python-specific checks
PYTHON_CHECKS: List[SecurityCheck] = [
    SecurityCheck(
        check_id="hardcoded-secrets",
        severity="critical",
        description="Hardcoded credential detected",
        recommendation="Use environment variables or a secrets manager instead of hardcoding credentials",
        file_extensions={".py"},
        regex_pattern=re.compile(r'(API_KEY|PASSWORD|SECRET)\s*=\s*["\'][^"\']+["\']'),
        false_positive_filter=_filter_hardcoded_secrets,
    ),
    SecurityCheck(
        check_id="sql-injection",
        severity="critical",
        description="Potential SQL injection via string formatting",
        recommendation="Use parameterized queries (cursor.execute(query, params)) instead of string formatting",
        file_extensions={".py"},
        regex_pattern=re.compile(r'f["\']SELECT.*\{'),
        false_positive_filter=_filter_sql_injection,
    ),
    SecurityCheck(
        check_id="command-injection",
        severity="critical",
        description="Potential command injection via shell command with user input",
        recommendation="Use subprocess with list arguments instead of shell=True with f-strings",
        file_extensions={".py"},
        substrings=['subprocess.run(f"', "subprocess.run(f'", 'os.system(f"', "os.system(f'"],
        false_positive_filter=_filter_command_injection,
    ),
    SecurityCheck(
        check_id="pickle-load",
        severity="critical",
        description="Unsafe deserialization using pickle",
        recommendation="Use json or a safer serialization format. Pickle can execute arbitrary code.",
        file_extensions={".py"},
        substrings=["pickle.load", "pickle.loads"],
    ),
    SecurityCheck(
        check_id="eval-exec",
        severity="high",
        description="Dynamic code execution detected",
        recommendation="Avoid eval/exec. Use ast.literal_eval for safe literal parsing or refactor to avoid dynamic code execution.",
        file_extensions={".py"},
        substrings=["eval(", "exec("],
        false_positive_filter=_filter_eval_exec,
    ),
    SecurityCheck(
        check_id="debug-mode",
        severity="high",
        description="Debug mode is enabled",
        recommendation="Ensure DEBUG is set to False in production. Use environment variables to control debug mode.",
        file_extensions={".py"},
        regex_pattern=re.compile(r'DEBUG\s*=\s*True'),
    ),
]

# JavaScript/TypeScript checks
JS_CHECKS: List[SecurityCheck] = [
    SecurityCheck(
        check_id="dangerous-inner-html",
        severity="high",
        description="dangerouslySetInnerHTML used in React component",
        recommendation="Sanitize HTML content with DOMPurify before using dangerouslySetInnerHTML, or use safer alternatives like textContent.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        substrings=["dangerouslySetInnerHTML"],
    ),
    SecurityCheck(
        check_id="document-write",
        severity="high",
        description="document.write usage detected (DOM XSS risk)",
        recommendation="Use safer DOM manipulation methods like createElement/appendChild or textContent.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        substrings=["document.write"],
    ),
    SecurityCheck(
        check_id="inner-html",
        severity="medium",
        description="innerHTML assignment detected (potential XSS)",
        recommendation="Use textContent for text, or sanitize with DOMPurify before using innerHTML.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        substrings=[".innerHTML"],
        false_positive_filter=_filter_inner_html,
    ),
    SecurityCheck(
        check_id="new-function",
        severity="high",
        description="Dynamic code generation with new Function()",
        recommendation="Avoid new Function() as it's similar to eval(). Refactor to use static functions or safer patterns.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        substrings=["new Function("],
    ),
    SecurityCheck(
        check_id="js-eval",
        severity="high",
        description="eval() usage detected in JavaScript",
        recommendation="Avoid eval(). Use JSON.parse() for JSON data or refactor to avoid dynamic code execution.",
        file_extensions={".js", ".jsx", ".ts", ".tsx"},
        substrings=["eval("],
    ),
]

# Universal checks (apply to multiple file types)
UNIVERSAL_CHECKS: List[SecurityCheck] = [
    SecurityCheck(
        check_id="cors-wildcard",
        severity="high",
        description="CORS wildcard (*) configuration detected",
        recommendation="Specify explicit origins instead of using wildcard (*) for CORS.",
        file_extensions={".py", ".js", ".ts", ".jsx", ".tsx"},
        regex_pattern=re.compile(r'(?:allow_origins|origin)\s*[=:]\s*\[?\s*["\']?\*["\']?'),
    ),
]

# GitHub Actions workflow checks
GHA_CHECKS: List[SecurityCheck] = [
    SecurityCheck(
        check_id="gha-injection",
        severity="critical",
        description="GitHub Actions workflow injection vulnerability",
        recommendation="Do not use untrusted input (issue title, PR title, comment body) directly in run: commands. Use an intermediate environment variable with proper escaping.",
        file_extensions={".yml", ".yaml"},
        # Match github.event context usage - the false_positive_filter determines if it's dangerous
        regex_pattern=re.compile(r'\$\{\{\s*github\.event'),
        false_positive_filter=_filter_gha_injection,
    ),
]


# ============================================================================
# SecurityChecker Class
# ============================================================================


class SecurityChecker:
    """
    Quick security checker for Coach validation.

    Performs fast security checks using hybrid detection (substring + regex)
    with path-based filtering to limit checks to relevant file types.

    Performance target: <30 seconds for 100-file project.

    Attributes
    ----------
    worktree_path : Path
        Path to the worktree to check

    Example
    -------
    >>> checker = SecurityChecker("/path/to/worktree")
    >>> findings = checker.run_quick_checks()
    >>> critical = [f for f in findings if f.severity == "critical"]
    >>> print(f"Found {len(critical)} critical issues")
    """

    # File extensions to scan
    PYTHON_EXTENSIONS = {".py"}
    JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}
    WORKFLOW_EXTENSIONS = {".yml", ".yaml"}

    # All source extensions
    SOURCE_EXTENSIONS = PYTHON_EXTENSIONS | JS_EXTENSIONS | WORKFLOW_EXTENSIONS

    # Directories to skip
    SKIP_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".guardkit",
        ".claude",
    }

    # Severity ordering for sorting
    SEVERITY_ORDER = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }

    def __init__(self, worktree_path: Union[str, Path]):
        """
        Initialize SecurityChecker.

        Parameters
        ----------
        worktree_path : Union[str, Path]
            Path to the worktree to check
        """
        self.worktree_path = Path(worktree_path)
        logger.debug(f"SecurityChecker initialized for: {self.worktree_path}")

    def run_quick_checks(self) -> List[SecurityFinding]:
        """
        Run all quick security checks and return findings.

        Returns
        -------
        List[SecurityFinding]
            List of findings sorted by severity (critical first)
        """
        logger.info(f"Starting security checks in {self.worktree_path}")
        findings: List[SecurityFinding] = []

        # Collect all checks
        all_checks = PYTHON_CHECKS + JS_CHECKS + UNIVERSAL_CHECKS + GHA_CHECKS

        # Scan files
        for file_path in self._iter_source_files():
            file_ext = file_path.suffix.lower()
            rel_path = str(file_path.relative_to(self.worktree_path))

            # Special handling for GHA files - must be in .github/workflows
            is_workflow_file = ".github/workflows" in str(file_path) and file_ext in self.WORKFLOW_EXTENSIONS

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for check in all_checks:
                    # Path-based filtering
                    if not self._check_applies_to_file(check, file_ext, is_workflow_file):
                        continue

                    # Run the check
                    check_findings = self._run_check(check, file_path, rel_path, file_ext, lines)
                    findings.extend(check_findings)

            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                continue

        # Sort by severity
        findings.sort(key=lambda f: self.SEVERITY_ORDER.get(f.severity, 5))

        logger.info(f"Security checks complete: {len(findings)} finding(s)")
        return findings

    def _iter_source_files(self):
        """
        Iterate over source files in the worktree.

        Yields
        ------
        Path
            Path to each source file
        """
        for path in self.worktree_path.rglob("*"):
            # Skip directories
            if path.is_dir():
                continue

            # Skip files in excluded directories
            if any(skip_dir in path.parts for skip_dir in self.SKIP_DIRS):
                continue

            # Check if it's a source file
            if path.suffix.lower() in self.SOURCE_EXTENSIONS:
                yield path

    def _check_applies_to_file(
        self, check: SecurityCheck, file_ext: str, is_workflow_file: bool
    ) -> bool:
        """
        Determine if a check applies to a file based on extension.

        Parameters
        ----------
        check : SecurityCheck
            The security check
        file_ext : str
            File extension (e.g., ".py")
        is_workflow_file : bool
            Whether this is a GitHub Actions workflow file

        Returns
        -------
        bool
            True if check applies to this file
        """
        # GHA checks only apply to workflow files
        if check.check_id == "gha-injection":
            return is_workflow_file

        # Other checks apply based on file extension
        if not check.file_extensions:
            return True  # Empty set means all files

        return file_ext in check.file_extensions

    def _run_check(
        self,
        check: SecurityCheck,
        file_path: Path,
        rel_path: str,
        file_ext: str,
        lines: List[str],
    ) -> List[SecurityFinding]:
        """
        Run a single security check on file content.

        Parameters
        ----------
        check : SecurityCheck
            The security check to run
        file_path : Path
            Absolute path to the file
        rel_path : str
            Relative path for reporting
        file_ext : str
            File extension
        lines : List[str]
            File content as lines

        Returns
        -------
        List[SecurityFinding]
            Findings from this check
        """
        findings: List[SecurityFinding] = []

        for line_num, line in enumerate(lines, start=1):
            # Skip comment lines (basic heuristic)
            if _is_comment_line(line, file_ext):
                continue

            # Check for match
            matched = False
            matched_text = ""

            if check.substrings:
                # Substring matching (fast)
                for substring in check.substrings:
                    if substring in line:
                        matched = True
                        matched_text = line.strip()
                        break
            elif check.regex_pattern:
                # Regex matching
                match = check.regex_pattern.search(line)
                if match:
                    matched = True
                    matched_text = match.group(0)

            if not matched:
                continue

            # Apply false positive filter
            if check.false_positive_filter:
                if check.false_positive_filter(line, line_num, lines):
                    continue  # Skip this match (false positive)

            # Create finding
            finding = SecurityFinding(
                check_id=check.check_id,
                severity=check.severity,
                description=check.description,
                file_path=rel_path,
                line_number=line_num,
                matched_text=matched_text[:MAX_MATCHED_TEXT_LENGTH],
                recommendation=check.recommendation,
            )
            findings.append(finding)

        return findings


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "SecurityChecker",
    "SecurityFinding",
]
