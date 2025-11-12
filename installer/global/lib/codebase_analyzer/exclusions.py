"""Build artifact exclusion patterns for codebase analysis."""

from pathlib import Path
from typing import List, Optional
import fnmatch

# Universal exclusion patterns for all technology stacks
DEFAULT_EXCLUSIONS = [
    # .NET
    "obj/", "bin/", "*.user", "*.suo", "packages/",

    # Java
    "target/", "*.class", "*.jar", "*.war",

    # Node.js
    "node_modules/", "package-lock.json", "yarn.lock",

    # Python
    "__pycache__/", "*.pyc", "venv/", ".venv/", "*.egg-info/",

    # Go
    "vendor/",

    # Rust
    "target/", "Cargo.lock",

    # Generic
    "build/", "dist/", ".git/", ".svn/", ".vscode/", ".idea/", "*.log", "coverage/",
    ".pytest_cache/", ".DS_Store", "*.pyo",
]


def should_exclude_path(path: Path) -> bool:
    """
    Check if a path should be excluded based on DEFAULT_EXCLUSIONS patterns.

    This function uses glob-style pattern matching to determine if a file or
    directory should be excluded from codebase analysis. Patterns ending with '/'
    are treated as directory patterns, while others match against the full path.

    Args:
        path: Path to check (can be absolute or relative)

    Returns:
        True if path matches any exclusion pattern, False otherwise

    Examples:
        >>> should_exclude_path(Path("src/bin/debug.exe"))
        True
        >>> should_exclude_path(Path("src/domain/user.py"))
        False
        >>> should_exclude_path(Path("node_modules/express/lib/index.js"))
        True
    """
    # Convert to string for pattern matching
    path_str = str(path)
    path_parts = path.parts

    for pattern in DEFAULT_EXCLUSIONS:
        # Directory patterns (end with /)
        if pattern.endswith('/'):
            dir_name = pattern.rstrip('/')
            # Check if directory appears anywhere in path
            if dir_name in path_parts:
                return True
        # File patterns (use fnmatch for glob-style matching)
        else:
            # Check against full path
            if fnmatch.fnmatch(path_str, f"*{pattern}"):
                return True
            # Check against filename only
            if fnmatch.fnmatch(path.name, pattern):
                return True

    return False


def get_source_files(
    root_dir: Path,
    extensions: Optional[List[str]] = None
) -> List[Path]:
    """
    Get source files from root_dir, excluding build artifacts.

    This function recursively scans the directory tree and returns all files
    with the specified extensions, while excluding paths that match any of
    the DEFAULT_EXCLUSIONS patterns.

    Args:
        root_dir: Root directory to scan
        extensions: List of file extensions to include (e.g., ['.py', '.ts']).
                   If None, returns all non-excluded files.

    Returns:
        List of Path objects for source files (sorted by path)

    Raises:
        ValueError: If root_dir doesn't exist or isn't a directory

    Examples:
        >>> get_source_files(Path("src"), extensions=[".py"])
        [Path("src/domain/user.py"), Path("src/api/routes.py")]

        >>> get_source_files(Path("project"))
        [Path("project/main.py"), Path("project/config.json"), ...]

    Notes:
        - Symlinks are followed
        - Permission errors are silently skipped
        - Files in excluded directories are not traversed (performance optimization)
    """
    if not root_dir.exists():
        raise ValueError(f"Root directory does not exist: {root_dir}")

    if not root_dir.is_dir():
        raise ValueError(f"Root path is not a directory: {root_dir}")

    source_files = []

    def scan_directory(directory: Path) -> None:
        """Recursively scan directory, respecting exclusion patterns."""
        try:
            for item in directory.iterdir():
                # Check if this path should be excluded
                if should_exclude_path(item):
                    continue

                if item.is_dir():
                    # Recursively scan subdirectory
                    scan_directory(item)
                elif item.is_file():
                    # Check extension filter if provided
                    if extensions is None or item.suffix in extensions:
                        source_files.append(item)
        except PermissionError:
            # Skip directories we can't read
            pass

    scan_directory(root_dir)

    # Return sorted for consistent ordering
    return sorted(source_files)
