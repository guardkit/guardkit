"""
Unit tests for seed_script_generator module.

Tests the generation of executable bash scripts for Graphiti seeding,
containing all guardkit graphiti add-context commands.

Coverage Target: >= 80%
"""

from pathlib import Path
import stat

from guardkit.planning.seed_script_generator import generate_seed_script


class TestGenerateSeedScript:
    """Tests for generate_seed_script function."""

    def test_generate_seed_script_creates_file(self, tmp_path: Path) -> None:
        """Test that generate_seed_script creates the bash script."""
        adr_paths = [Path("docs/adr/0001-first.md")]
        spec_path = Path("docs/spec/feature-spec.md")

        result = generate_seed_script(
            feature_id="FEAT-TEST-001",
            adr_paths=adr_paths,
            spec_path=spec_path,
            warnings_path=None,
            output_dir=tmp_path,
        )

        assert result.exists()
        assert result.name == "seed-FEAT-TEST-001.sh"

    def test_generate_seed_script_has_shebang(self, tmp_path: Path) -> None:
        """Test that the script has #!/usr/bin/env bash shebang."""
        result = generate_seed_script(
            feature_id="FEAT-SHEBANG",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_generate_seed_script_has_set_e(self, tmp_path: Path) -> None:
        """Test that the script has set -e for fail-fast behavior."""
        result = generate_seed_script(
            feature_id="FEAT-SETE",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "set -e" in content

    def test_generate_seed_script_includes_status_check(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes graphiti status command."""
        result = generate_seed_script(
            feature_id="FEAT-STATUS",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "guardkit graphiti status" in content

    def test_generate_seed_script_includes_adr_commands(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes add-context for each ADR."""
        adr_paths = [
            Path("docs/adr/0001-auth-strategy.md"),
            Path("docs/adr/0002-database-choice.md"),
            Path("docs/adr/0003-api-design.md"),
        ]

        result = generate_seed_script(
            feature_id="FEAT-ADR",
            adr_paths=adr_paths,
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "guardkit graphiti add-context docs/adr/0001-auth-strategy.md" in content
        assert "guardkit graphiti add-context docs/adr/0002-database-choice.md" in content
        assert "guardkit graphiti add-context docs/adr/0003-api-design.md" in content

    def test_generate_seed_script_includes_spec_command(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes add-context for spec."""
        spec_path = Path("docs/spec/FEAT-XYZ-spec.md")

        result = generate_seed_script(
            feature_id="FEAT-SPEC",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=spec_path,
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "guardkit graphiti add-context docs/spec/FEAT-XYZ-spec.md" in content

    def test_generate_seed_script_includes_warnings_when_provided(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes add-context for warnings when provided."""
        warnings_path = Path("docs/warnings/FEAT-WARN-warnings.md")

        result = generate_seed_script(
            feature_id="FEAT-WARN",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            warnings_path=warnings_path,
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "guardkit graphiti add-context docs/warnings/FEAT-WARN-warnings.md" in content

    def test_generate_seed_script_excludes_warnings_when_none(
        self, tmp_path: Path
    ) -> None:
        """Test that the script doesn't include warnings section when None."""
        result = generate_seed_script(
            feature_id="FEAT-NOWARN",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            warnings_path=None,
            output_dir=tmp_path,
        )

        content = result.read_text()
        # Should not have warnings-related commands
        assert "warnings" not in content.lower() or "Seed warnings" not in content

    def test_generate_seed_script_includes_verify_command(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes verify command."""
        result = generate_seed_script(
            feature_id="FEAT-VERIFY",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert "guardkit graphiti verify --verbose" in content

    def test_generate_seed_script_includes_echo_messages(
        self, tmp_path: Path
    ) -> None:
        """Test that the script includes descriptive echo messages."""
        result = generate_seed_script(
            feature_id="FEAT-ECHO",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        assert 'echo "=== Seeding FEAT-ECHO' in content
        assert 'echo "Seeding ADR files..."' in content
        assert 'echo "Seeding feature specification..."' in content
        assert 'echo "Verifying seeding..."' in content
        assert 'echo "=== Seeding complete ===' in content

    def test_generate_seed_script_default_output_dir(self) -> None:
        """Test that default output_dir is scripts."""
        import inspect
        from guardkit.planning.seed_script_generator import generate_seed_script

        sig = inspect.signature(generate_seed_script)
        output_dir_param = sig.parameters["output_dir"]
        assert output_dir_param.default == Path("scripts")

    def test_generate_seed_script_creates_output_dir_if_not_exists(
        self, tmp_path: Path
    ) -> None:
        """Test that the function creates output directory if it doesn't exist."""
        output_dir = tmp_path / "nested" / "scripts"

        result = generate_seed_script(
            feature_id="FEAT-NESTED",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=output_dir,
        )

        assert output_dir.exists()
        assert result.parent == output_dir

    def test_generate_seed_script_is_executable(self, tmp_path: Path) -> None:
        """Test that the generated script is executable."""
        result = generate_seed_script(
            feature_id="FEAT-EXEC",
            adr_paths=[Path("docs/adr/test.md")],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        # Check file permissions include execute bit
        file_stat = result.stat()
        assert file_stat.st_mode & stat.S_IXUSR  # User execute permission

    def test_generate_seed_script_idempotent(self, tmp_path: Path) -> None:
        """Test that running generate_seed_script multiple times is idempotent."""
        args = {
            "feature_id": "FEAT-IDEM",
            "adr_paths": [Path("docs/adr/test.md")],
            "spec_path": Path("docs/spec.md"),
            "output_dir": tmp_path,
        }

        result1 = generate_seed_script(**args)
        content1 = result1.read_text()

        result2 = generate_seed_script(**args)
        content2 = result2.read_text()

        assert content1 == content2

    def test_generate_seed_script_empty_adr_paths(self, tmp_path: Path) -> None:
        """Test that the script handles empty ADR paths gracefully."""
        result = generate_seed_script(
            feature_id="FEAT-NOADR",
            adr_paths=[],
            spec_path=Path("docs/spec.md"),
            output_dir=tmp_path,
        )

        content = result.read_text()
        # Should still create script with spec and verify
        assert "guardkit graphiti add-context docs/spec.md" in content
        assert "guardkit graphiti verify --verbose" in content

    def test_generate_seed_script_proper_section_order(
        self, tmp_path: Path
    ) -> None:
        """Test that script sections are in the correct order."""
        warnings_path = Path("docs/warnings/test.md")

        result = generate_seed_script(
            feature_id="FEAT-ORDER",
            adr_paths=[Path("docs/adr/0001.md")],
            spec_path=Path("docs/spec.md"),
            warnings_path=warnings_path,
            output_dir=tmp_path,
        )

        content = result.read_text()
        lines = content.split("\n")

        # Find key sections and verify order
        shebang_line = next(
            (i for i, line in enumerate(lines) if line.startswith("#!/")), -1
        )
        set_e_line = next(
            (i for i, line in enumerate(lines) if "set -e" in line), -1
        )
        status_line = next(
            (i for i, line in enumerate(lines) if "graphiti status" in line), -1
        )
        adr_line = next(
            (i for i, line in enumerate(lines) if "ADR" in line), -1
        )
        spec_line = next(
            (i for i, line in enumerate(lines) if "specification" in line.lower()), -1
        )
        verify_line = next(
            (i for i, line in enumerate(lines) if "verify" in line.lower()), -1
        )

        assert shebang_line < set_e_line < status_line < adr_line < spec_line < verify_line

    def test_generate_seed_script_with_path_objects(self, tmp_path: Path) -> None:
        """Test that Path objects are handled correctly."""
        result = generate_seed_script(
            feature_id="FEAT-PATH",
            adr_paths=[Path("docs") / "adr" / "0001.md"],
            spec_path=Path("docs") / "spec" / "feature.md",
            warnings_path=Path("docs") / "warnings" / "warn.md",
            output_dir=tmp_path,
        )

        content = result.read_text()
        # Paths should be converted to forward slashes (POSIX style for bash)
        assert "docs/adr/0001.md" in content or "docs\\adr\\0001.md" in content
