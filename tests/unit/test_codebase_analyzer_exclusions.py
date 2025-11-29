"""
Unit Tests for Codebase Analyzer Exclusions

Tests the exclusions module functionality:
- should_exclude_path()
- get_source_files()
- DEFAULT_EXCLUSIONS patterns
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from lib.codebase_analyzer.exclusions import (
    should_exclude_path,
    get_source_files,
    DEFAULT_EXCLUSIONS
)


class TestShouldExcludePath:
    """Test should_exclude_path() function."""

    def test_exclude_bin_directory(self):
        """Test that bin/ directories are excluded."""
        assert should_exclude_path(Path("project/bin/debug.exe")) is True
        assert should_exclude_path(Path("bin/release.exe")) is True

    def test_exclude_obj_directory(self):
        """Test that obj/ directories are excluded."""
        assert should_exclude_path(Path("project/obj/Debug/file.cs")) is True
        assert should_exclude_path(Path("obj/file.cs")) is True

    def test_exclude_node_modules(self):
        """Test that node_modules/ is excluded."""
        assert should_exclude_path(Path("project/node_modules/express/index.js")) is True

    def test_exclude_pycache(self):
        """Test that __pycache__/ is excluded."""
        assert should_exclude_path(Path("src/__pycache__/module.pyc")) is True

    def test_exclude_pyc_files(self):
        """Test that *.pyc files are excluded."""
        assert should_exclude_path(Path("src/module.pyc")) is True
        assert should_exclude_path(Path("tests/test_file.pyc")) is True

    def test_exclude_venv_directory(self):
        """Test that venv/ directories are excluded."""
        assert should_exclude_path(Path("venv/lib/python3.9/site-packages")) is True
        assert should_exclude_path(Path(".venv/bin/python")) is True

    def test_exclude_target_directory(self):
        """Test that target/ directories are excluded (Java/Rust)."""
        assert should_exclude_path(Path("target/debug/app")) is True

    def test_exclude_git_directory(self):
        """Test that .git/ directories are excluded."""
        assert should_exclude_path(Path(".git/objects/abc")) is True

    def test_exclude_build_directory(self):
        """Test that build/ directories are excluded."""
        assert should_exclude_path(Path("build/output/app.exe")) is True

    def test_exclude_dist_directory(self):
        """Test that dist/ directories are excluded."""
        assert should_exclude_path(Path("dist/bundle.js")) is True

    def test_include_source_files(self):
        """Test that source files are NOT excluded."""
        assert should_exclude_path(Path("src/domain/user.py")) is False
        assert should_exclude_path(Path("src/api/routes.ts")) is False
        assert should_exclude_path(Path("Program.cs")) is False
        assert should_exclude_path(Path("main.go")) is False

    def test_include_test_files(self):
        """Test that test files are NOT excluded (handled elsewhere)."""
        assert should_exclude_path(Path("tests/test_user.py")) is False
        assert should_exclude_path(Path("tests/unit/test_api.ts")) is False

    def test_exclude_log_files(self):
        """Test that *.log files are excluded."""
        assert should_exclude_path(Path("app.log")) is True
        assert should_exclude_path(Path("logs/debug.log")) is True
        assert should_exclude_path(Path("src/test.log")) is True

    def test_exclude_ds_store(self):
        """Test that .DS_Store files are excluded."""
        assert should_exclude_path(Path(".DS_Store")) is True
        assert should_exclude_path(Path("src/.DS_Store")) is True


class TestGetSourceFiles:
    """Test get_source_files() function."""

    def setup_method(self):
        """Create a temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_get_python_files(self):
        """Test getting Python files."""
        # Create directory structure
        src_dir = self.temp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")
        (src_dir / "utils.py").write_text("def helper(): pass")

        # Create build artifacts (should be excluded)
        pycache = src_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "main.pyc").write_text("compiled")

        # Get source files
        files = get_source_files(self.temp_path, extensions=[".py"])

        # Verify
        assert len(files) == 2
        file_names = {f.name for f in files}
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "main.pyc" not in file_names

    def test_get_typescript_files(self):
        """Test getting TypeScript files."""
        # Create directory structure
        src_dir = self.temp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.ts").write_text("console.log('hello')")

        # Create node_modules (should be excluded)
        node_modules = self.temp_path / "node_modules"
        node_modules.mkdir()
        express_dir = node_modules / "express"
        express_dir.mkdir()
        (express_dir / "index.ts").write_text("export default {}")

        # Get source files
        files = get_source_files(self.temp_path, extensions=[".ts"])

        # Verify
        assert len(files) == 1
        assert files[0].name == "app.ts"

    def test_get_csharp_files_exclude_bin_obj(self):
        """Test getting C# files while excluding bin/obj."""
        # Create directory structure
        src_dir = self.temp_path / "src"
        src_dir.mkdir()
        (src_dir / "Program.cs").write_text("class Program {}")

        # Create bin directory (should be excluded)
        bin_dir = self.temp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "Debug.cs").write_text("// compiled")

        # Create obj directory (should be excluded)
        obj_dir = self.temp_path / "obj"
        obj_dir.mkdir()
        (obj_dir / "Temp.cs").write_text("// temp")

        # Get source files
        files = get_source_files(self.temp_path, extensions=[".cs"])

        # Verify
        assert len(files) == 1
        assert files[0].name == "Program.cs"

    def test_get_all_files_no_extension_filter(self):
        """Test getting all files when no extension filter provided."""
        # Create mixed files
        (self.temp_path / "script.py").write_text("print('hello')")
        (self.temp_path / "config.json").write_text("{}")
        (self.temp_path / "readme.md").write_text("# README")

        # Create excluded file
        pycache = self.temp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_text("compiled")

        # Get all files
        files = get_source_files(self.temp_path, extensions=None)

        # Verify
        assert len(files) == 3
        file_names = {f.name for f in files}
        assert "script.py" in file_names
        assert "config.json" in file_names
        assert "readme.md" in file_names
        assert "module.pyc" not in file_names

    def test_invalid_root_directory_raises_error(self):
        """Test that invalid root directory raises ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            get_source_files(Path("/nonexistent/path"))

    def test_file_as_root_raises_error(self):
        """Test that file path as root raises ValueError."""
        file_path = self.temp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="not a directory"):
            get_source_files(file_path)

    def test_nested_exclusions(self):
        """Test that nested excluded directories are handled correctly."""
        # Create nested structure
        src_dir = self.temp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")

        # Create nested excluded directories
        venv_dir = src_dir / "venv"
        venv_dir.mkdir()
        lib_dir = venv_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "package.py").write_text("# external package")

        # Get source files
        files = get_source_files(self.temp_path, extensions=[".py"])

        # Verify - only main.py, not the venv package
        assert len(files) == 1
        assert files[0].name == "main.py"


class TestDefaultExclusions:
    """Test DEFAULT_EXCLUSIONS constant."""

    def test_contains_dotnet_patterns(self):
        """Test that .NET patterns are included."""
        assert "bin/" in DEFAULT_EXCLUSIONS
        assert "obj/" in DEFAULT_EXCLUSIONS
        assert "packages/" in DEFAULT_EXCLUSIONS

    def test_contains_java_patterns(self):
        """Test that Java patterns are included."""
        assert "target/" in DEFAULT_EXCLUSIONS
        assert "*.class" in DEFAULT_EXCLUSIONS

    def test_contains_nodejs_patterns(self):
        """Test that Node.js patterns are included."""
        assert "node_modules/" in DEFAULT_EXCLUSIONS

    def test_contains_python_patterns(self):
        """Test that Python patterns are included."""
        assert "__pycache__/" in DEFAULT_EXCLUSIONS
        assert "*.pyc" in DEFAULT_EXCLUSIONS
        assert "venv/" in DEFAULT_EXCLUSIONS

    def test_contains_generic_patterns(self):
        """Test that generic patterns are included."""
        assert "build/" in DEFAULT_EXCLUSIONS
        assert "dist/" in DEFAULT_EXCLUSIONS
        assert ".git/" in DEFAULT_EXCLUSIONS
        assert "coverage/" in DEFAULT_EXCLUSIONS
