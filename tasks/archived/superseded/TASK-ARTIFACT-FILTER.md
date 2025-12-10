# TASK-ARTIFACT-FILTER: Build Artifact Filtering

**Task ID**: TASK-ARTIFACT-FILTER
**Title**: Exclude Build Artifacts from Codebase Analysis
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 3/10 (Simple)
**Estimated Hours**: 2-3
**Phase**: 1 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

The codebase analyzer counts build artifacts (obj/, bin/, node_modules/) as source files, leading to incorrect language detection.

**Evidence from TASK-9037:**
```
.NET project: 606 .java files (from obj/Debug/) + 373 .cs files
Detected as: Java (wrong!)
Should be: C#
```

### Impact

- Wrong language detection (70% accuracy)
- Wrong framework detection
- Incorrect template generation
- Poor user experience

### Root Cause

The `stratified_sampler.py` includes all files regardless of whether they are source code or build artifacts.

---

## Solution Design

### Approach

Create an exclusion filter that removes build artifacts before analysis. This is a pure algorithmic solution (no AI required for this phase).

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/core/lib/codebase_analyzer/exclusion_patterns.py` | CREATE | Exclusion logic |
| `installer/core/lib/codebase_analyzer/stratified_sampler.py` | MODIFY | Use exclusion filter |
| `tests/unit/codebase_analyzer/test_exclusion_patterns.py` | CREATE | Unit tests |

---

## Implementation Details

### 1. ExclusionPatterns Module

```python
# installer/core/lib/codebase_analyzer/exclusion_patterns.py

from pathlib import Path
from typing import List, Optional, Set
import fnmatch
import logging

logger = logging.getLogger(__name__)


# Default patterns to exclude (always applied)
DEFAULT_EXCLUSIONS = [
    # Build outputs
    "obj/", "obj\\",
    "bin/", "bin\\",
    "build/", "build\\",
    "dist/", "dist\\",
    "out/", "out\\",
    "target/", "target\\",
    ".build/",

    # Dependencies
    "node_modules/", "node_modules\\",
    "vendor/", "vendor\\",
    ".venv/", ".venv\\",
    "venv/", "venv\\",
    "virtualenv/",
    "packages/",  # NuGet packages folder

    # IDE and editor
    ".idea/", ".idea\\",
    ".vscode/", ".vscode\\",
    ".vs/", ".vs\\",
    "*.swp",
    "*.swo",
    "*~",

    # Version control
    ".git/", ".git\\",
    ".svn/", ".svn\\",
    ".hg/", ".hg\\",

    # Python artifacts
    "__pycache__/", "__pycache__\\",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache/",
    ".tox/",
    "*.egg-info/",
    ".eggs/",
    ".mypy_cache/",

    # .NET artifacts
    "*.dll",
    "*.exe",
    "*.pdb",
    "*.cache",
    "*.nupkg",

    # Java artifacts
    "*.class",
    "*.jar",
    "*.war",

    # Compiled/binary
    "*.so",
    "*.dylib",
    "*.o",
    "*.a",

    # Test coverage
    "coverage/",
    ".coverage",
    "htmlcov/",

    # Logs and temp
    "*.log",
    "logs/",
    "tmp/",
    "temp/",
]


def load_gitignore_patterns(project_path: Path) -> List[str]:
    """
    Load patterns from .gitignore file.

    Args:
        project_path: Root of project

    Returns:
        List of gitignore patterns
    """
    gitignore_path = project_path / ".gitignore"
    patterns = []

    if not gitignore_path.exists():
        return patterns

    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    patterns.append(line)
        logger.debug(f"Loaded {len(patterns)} patterns from .gitignore")
    except Exception as e:
        logger.warning(f"Failed to read .gitignore: {e}")

    return patterns


def matches_pattern(file_path: Path, pattern: str, project_root: Path) -> bool:
    """
    Check if a file path matches an exclusion pattern.

    Args:
        file_path: Path to check (absolute or relative)
        pattern: Glob-style pattern
        project_root: Project root for relative resolution

    Returns:
        True if file should be excluded
    """
    # Get relative path from project root
    try:
        rel_path = file_path.relative_to(project_root)
    except ValueError:
        rel_path = file_path

    # Convert to string for matching
    path_str = str(rel_path)
    path_str_posix = str(rel_path).replace('\\', '/')

    # Handle directory patterns (ending with /)
    if pattern.endswith('/') or pattern.endswith('\\'):
        dir_pattern = pattern.rstrip('/\\')
        if dir_pattern in path_str_posix or path_str_posix.startswith(dir_pattern + '/'):
            return True
        # Check each path component
        for part in rel_path.parts:
            if part == dir_pattern:
                return True

    # Handle file patterns
    if fnmatch.fnmatch(path_str_posix, pattern):
        return True
    if fnmatch.fnmatch(rel_path.name, pattern):
        return True

    return False


def should_exclude(
    file_path: Path,
    project_root: Path,
    custom_exclusions: Optional[List[str]] = None
) -> bool:
    """
    Determine if a file should be excluded from analysis.

    Args:
        file_path: Path to file
        project_root: Project root directory
        custom_exclusions: Additional patterns to exclude

    Returns:
        True if file should be excluded
    """
    # Combine all patterns
    all_patterns = DEFAULT_EXCLUSIONS.copy()

    # Add gitignore patterns
    gitignore_patterns = load_gitignore_patterns(project_root)
    all_patterns.extend(gitignore_patterns)

    # Add custom exclusions
    if custom_exclusions:
        all_patterns.extend(custom_exclusions)

    # Check against patterns
    for pattern in all_patterns:
        if matches_pattern(file_path, pattern, project_root):
            return True

    return False


def filter_files(
    files: List[Path],
    project_root: Path,
    custom_exclusions: Optional[List[str]] = None
) -> List[Path]:
    """
    Filter out build artifacts and other excluded files.

    Args:
        files: List of file paths to filter
        project_root: Project root directory
        custom_exclusions: Additional patterns to exclude

    Returns:
        Filtered list of source files only
    """
    filtered = []
    excluded_count = 0

    for file_path in files:
        if should_exclude(file_path, project_root, custom_exclusions):
            excluded_count += 1
        else:
            filtered.append(file_path)

    logger.info(f"Filtered {excluded_count} files, keeping {len(filtered)} source files")
    return filtered


def get_exclusion_summary(
    files: List[Path],
    project_root: Path
) -> dict:
    """
    Get summary of what was excluded and why.

    Args:
        files: Original list of files
        project_root: Project root directory

    Returns:
        Summary dict with counts by pattern category
    """
    summary = {
        "total_files": len(files),
        "excluded_by_category": {
            "build_outputs": 0,
            "dependencies": 0,
            "ide": 0,
            "vcs": 0,
            "compiled": 0,
            "gitignore": 0,
            "other": 0
        },
        "source_files": 0
    }

    for file_path in files:
        if should_exclude(file_path, project_root):
            # Categorize exclusion
            path_str = str(file_path)
            if any(p in path_str for p in ['obj/', 'bin/', 'build/', 'dist/', 'target/']):
                summary["excluded_by_category"]["build_outputs"] += 1
            elif any(p in path_str for p in ['node_modules/', 'vendor/', 'venv/', 'packages/']):
                summary["excluded_by_category"]["dependencies"] += 1
            elif any(p in path_str for p in ['.idea/', '.vscode/', '.vs/']):
                summary["excluded_by_category"]["ide"] += 1
            elif any(p in path_str for p in ['.git/', '.svn/', '.hg/']):
                summary["excluded_by_category"]["vcs"] += 1
            elif any(path_str.endswith(ext) for ext in ['.dll', '.exe', '.class', '.jar', '.pyc']):
                summary["excluded_by_category"]["compiled"] += 1
            else:
                summary["excluded_by_category"]["other"] += 1
        else:
            summary["source_files"] += 1

    return summary
```

### 2. Integrate with Stratified Sampler

```python
# In installer/core/lib/codebase_analyzer/stratified_sampler.py

from .exclusion_patterns import filter_files

class StratifiedSampler:
    def sample_files(
        self,
        project_path: Path,
        max_files: int = 30,
        custom_exclusions: Optional[List[str]] = None
    ) -> List[FileSample]:
        """
        Sample files using stratified sampling after filtering artifacts.
        """
        # Get all files
        all_files = self._get_all_files(project_path)

        # Filter out build artifacts
        source_files = filter_files(
            files=all_files,
            project_root=project_path,
            custom_exclusions=custom_exclusions
        )

        # Continue with stratified sampling on source files only
        return self._stratified_sample(source_files, max_files)
```

---

## Acceptance Criteria

### Functional

- [ ] .NET projects detected as C# (not Java)
- [ ] Node.js projects detected as JavaScript/TypeScript (not considering node_modules)
- [ ] Python projects ignore __pycache__ and .venv
- [ ] Custom .gitignore patterns respected
- [ ] Build artifact count is 0 in sampled files

### Quality

- [ ] Test coverage >= 95%
- [ ] All tests passing
- [ ] Code follows project conventions

### Performance

- [ ] Filtering completes in < 1 second for 10,000 files
- [ ] Memory usage < 100MB

---

## Test Specifications

### Unit Tests

```python
# tests/unit/codebase_analyzer/test_exclusion_patterns.py

import pytest
from pathlib import Path
from installer.core.lib.codebase_analyzer.exclusion_patterns import (
    should_exclude,
    filter_files,
    load_gitignore_patterns,
    matches_pattern
)


class TestShouldExclude:
    """Tests for should_exclude function."""

    def test_excludes_dotnet_obj_folder(self, tmp_path):
        """Test that .NET obj/ folder is excluded."""
        file = tmp_path / "src" / "obj" / "Debug" / "Generated.java"
        file.parent.mkdir(parents=True)
        file.touch()

        assert should_exclude(file, tmp_path) is True

    def test_excludes_dotnet_bin_folder(self, tmp_path):
        """Test that .NET bin/ folder is excluded."""
        file = tmp_path / "MyProject" / "bin" / "Release" / "app.dll"
        file.parent.mkdir(parents=True)
        file.touch()

        assert should_exclude(file, tmp_path) is True

    def test_excludes_node_modules(self, tmp_path):
        """Test that node_modules is excluded."""
        file = tmp_path / "node_modules" / "react" / "index.js"
        file.parent.mkdir(parents=True)
        file.touch()

        assert should_exclude(file, tmp_path) is True

    def test_excludes_pycache(self, tmp_path):
        """Test that __pycache__ is excluded."""
        file = tmp_path / "src" / "__pycache__" / "module.cpython-39.pyc"
        file.parent.mkdir(parents=True)
        file.touch()

        assert should_exclude(file, tmp_path) is True

    def test_includes_source_files(self, tmp_path):
        """Test that source files are included."""
        # Create various source files
        files = [
            tmp_path / "src" / "main.py",
            tmp_path / "src" / "App.cs",
            tmp_path / "components" / "Button.tsx",
            tmp_path / "lib" / "utils.js"
        ]
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()

        for f in files:
            assert should_exclude(f, tmp_path) is False

    def test_excludes_compiled_files(self, tmp_path):
        """Test that compiled files are excluded."""
        files = [
            tmp_path / "lib.dll",
            tmp_path / "app.exe",
            tmp_path / "Main.class",
            tmp_path / "module.pyc"
        ]
        for f in files:
            f.touch()

        for f in files:
            assert should_exclude(f, tmp_path) is True


class TestGitignoreIntegration:
    """Tests for .gitignore pattern loading."""

    def test_loads_gitignore_patterns(self, tmp_path):
        """Test that .gitignore patterns are loaded."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\nsecrets/\n# comment\n\n")

        patterns = load_gitignore_patterns(tmp_path)

        assert "*.log" in patterns
        assert "secrets/" in patterns
        assert "# comment" not in patterns
        assert "" not in patterns

    def test_excludes_gitignore_patterns(self, tmp_path):
        """Test that .gitignore patterns are applied."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("secrets/\n*.env")

        secret_file = tmp_path / "secrets" / "keys.json"
        secret_file.parent.mkdir()
        secret_file.touch()

        env_file = tmp_path / ".env"
        env_file.touch()

        assert should_exclude(secret_file, tmp_path) is True
        assert should_exclude(env_file, tmp_path) is True

    def test_handles_missing_gitignore(self, tmp_path):
        """Test graceful handling when .gitignore doesn't exist."""
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []


class TestFilterFiles:
    """Tests for filter_files function."""

    def test_filters_build_artifacts(self, tmp_path):
        """Test complete filtering of build artifacts."""
        # Create mixed files
        source = tmp_path / "src" / "main.cs"
        artifact1 = tmp_path / "obj" / "Debug" / "generated.java"
        artifact2 = tmp_path / "bin" / "app.dll"

        for f in [source, artifact1, artifact2]:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()

        all_files = [source, artifact1, artifact2]
        filtered = filter_files(all_files, tmp_path)

        assert len(filtered) == 1
        assert source in filtered
        assert artifact1 not in filtered
        assert artifact2 not in filtered

    def test_respects_custom_exclusions(self, tmp_path):
        """Test that custom exclusions are applied."""
        file1 = tmp_path / "src" / "main.py"
        file2 = tmp_path / "generated" / "output.py"

        for f in [file1, file2]:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()

        filtered = filter_files(
            [file1, file2],
            tmp_path,
            custom_exclusions=["generated/"]
        )

        assert len(filtered) == 1
        assert file1 in filtered


class TestDotNetProject:
    """Integration tests for .NET project scenario."""

    def test_dotnet_project_detected_as_csharp(self, tmp_path):
        """Test that .NET project with Java in obj/ is detected as C#."""
        # Create .NET project structure
        cs_files = [
            tmp_path / "src" / "Program.cs",
            tmp_path / "src" / "Models" / "User.cs",
            tmp_path / "src" / "Services" / "UserService.cs"
        ]

        # Create Java files in obj/ (generated)
        java_files = [
            tmp_path / "obj" / "Debug" / "Generated1.java",
            tmp_path / "obj" / "Debug" / "Generated2.java",
            tmp_path / "obj" / "Release" / "Generated3.java"
        ]

        for f in cs_files + java_files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()

        all_files = cs_files + java_files
        filtered = filter_files(all_files, tmp_path)

        # Should only have C# files
        assert len(filtered) == 3
        assert all(f.suffix == '.cs' for f in filtered)
```

---

## Dependencies

### Depends On
- None (can start immediately)

### Blocks
- TASK-PHASE-1-CHECKPOINT (Phase 3) - needs filtered files

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Language detection accuracy | 95%+ | Test on 4 reference projects |
| Build artifact count | 0 | Verify no obj/bin/node_modules in samples |
| Test coverage | >= 95% | pytest --cov |
| Performance | < 1 second for 10K files | Benchmark test |

---

## Testing Checklist

### Before Completion

- [ ] Unit tests pass (pytest tests/unit/codebase_analyzer/test_exclusion_patterns.py)
- [ ] Coverage >= 95%
- [ ] .NET project (DeCUK.Mobile.MyDrive) detected as C#
- [ ] React project (bulletproof-react) detected as TypeScript
- [ ] FastAPI project detected as Python
- [ ] No regressions in existing tests

### Manual Verification

```bash
# Test on .NET project
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate --name test-dotnet
# Expected: C#, not Java

# Test on React project
cd ~/Projects/bulletproof-react
/template-create --validate --name test-react
# Expected: TypeScript/JavaScript
```

---

## Notes

- This phase does NOT require AI - it's pure algorithmic filtering
- The exclusion patterns are comprehensive but may need tuning
- Consider making exclusions configurable via `.agentecflow/config.json` in future

---

**Created**: 2025-11-18
**Phase**: 1 of 8 (Template-Create Redesign)
**Related**: TASK-9037-fix-build-artifact-exclusion-in-codebase-analyzer
