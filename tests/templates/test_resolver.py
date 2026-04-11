"""Tests for guardkit.templates.resolver module.

Validates that resolve_template_source_dir behaves identically to
the original _resolve_template_source_dir that lived in guardkit.cli.init.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from guardkit.templates.resolver import (
    _get_templates_base_dir,
    _get_user_templates_dir,
    resolve_template_source_dir,
)


class TestResolveTemplateSourceDir:
    """Test resolve_template_source_dir (public API)."""

    def test_resolves_from_package_location(self, tmp_path: Path) -> None:
        """Template source resolved from installed package location."""
        templates_base = tmp_path / "installer" / "core" / "templates"
        template_dir = templates_base / "fastapi-python"
        template_dir.mkdir(parents=True)
        (template_dir / "manifest.json").write_text("{}")

        with patch(
            "guardkit.templates.resolver._get_templates_base_dir",
            return_value=templates_base,
        ):
            result = resolve_template_source_dir("fastapi-python")

        assert result is not None
        assert result == template_dir

    def test_returns_none_for_unknown_template(self, tmp_path: Path) -> None:
        """Returns None when template not found anywhere."""
        templates_base = tmp_path / "installer" / "core" / "templates"
        templates_base.mkdir(parents=True)

        with (
            patch(
                "guardkit.templates.resolver._get_templates_base_dir",
                return_value=templates_base,
            ),
            patch(
                "guardkit.templates.resolver._get_user_templates_dir",
                return_value=tmp_path / "user_templates",
            ),
        ):
            result = resolve_template_source_dir("nonexistent-template")

        assert result is None

    def test_falls_back_to_user_templates(self, tmp_path: Path) -> None:
        """Falls back to ~/.guardkit/templates/ for user-installed templates."""
        # Package templates: no match
        pkg_templates = tmp_path / "pkg_templates"
        pkg_templates.mkdir()

        # User templates: has match
        user_templates = tmp_path / "user_templates"
        user_template_dir = user_templates / "custom-template"
        user_template_dir.mkdir(parents=True)
        (user_template_dir / "manifest.json").write_text("{}")

        with (
            patch(
                "guardkit.templates.resolver._get_templates_base_dir",
                return_value=pkg_templates,
            ),
            patch(
                "guardkit.templates.resolver._get_user_templates_dir",
                return_value=user_templates,
            ),
        ):
            result = resolve_template_source_dir("custom-template")

        assert result is not None
        assert result == user_template_dir

    def test_package_takes_priority_over_user(self, tmp_path: Path) -> None:
        """Package-installed template takes priority over user template."""
        # Package templates: has match
        pkg_templates = tmp_path / "pkg_templates"
        pkg_dir = pkg_templates / "my-template"
        pkg_dir.mkdir(parents=True)

        # User templates: also has match
        user_templates = tmp_path / "user_templates"
        user_dir = user_templates / "my-template"
        user_dir.mkdir(parents=True)

        with (
            patch(
                "guardkit.templates.resolver._get_templates_base_dir",
                return_value=pkg_templates,
            ),
            patch(
                "guardkit.templates.resolver._get_user_templates_dir",
                return_value=user_templates,
            ),
        ):
            result = resolve_template_source_dir("my-template")

        assert result == pkg_dir


class TestGetTemplatesBaseDir:
    """Test _get_templates_base_dir returns valid path."""

    def test_returns_path(self) -> None:
        """Returns a Path object ending with installer/core/templates."""
        result = _get_templates_base_dir()
        assert isinstance(result, Path)
        assert result.parts[-3:] == ("installer", "core", "templates")


class TestGetUserTemplatesDir:
    """Test _get_user_templates_dir returns valid path."""

    def test_returns_path(self) -> None:
        """Returns a Path under home directory."""
        result = _get_user_templates_dir()
        assert isinstance(result, Path)
        assert result.parts[-2:] == (".guardkit", "templates")


class TestBackwardCompatibility:
    """Ensure the old import path still works."""

    def test_init_module_exposes_private_wrapper(self) -> None:
        """guardkit.cli.init._resolve_template_source_dir still importable."""
        from guardkit.cli.init import _resolve_template_source_dir

        assert callable(_resolve_template_source_dir)

    def test_init_module_exposes_helper_aliases(self) -> None:
        """guardkit.cli.init helper aliases still importable."""
        from guardkit.cli.init import (
            _get_templates_base_dir as init_base,
            _get_user_templates_dir as init_user,
        )

        assert init_base is _get_templates_base_dir
        assert init_user is _get_user_templates_dir

    def test_patching_init_module_name_works(self, tmp_path: Path) -> None:
        """Patching via the old module path still controls behaviour.

        Many existing tests patch "guardkit.cli.init._resolve_template_source_dir".
        This must continue to work.
        """
        templates_base = tmp_path / "templates"
        template_dir = templates_base / "test-template"
        template_dir.mkdir(parents=True)

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=template_dir,
        ):
            from guardkit.cli.init import _resolve_template_source_dir

            result = _resolve_template_source_dir("test-template")

        assert result == template_dir

    def test_patching_init_helpers_controls_private_wrapper(
        self, tmp_path: Path
    ) -> None:
        """Patching helper functions at init module level controls _resolve behaviour.

        Existing tests patch guardkit.cli.init._get_templates_base_dir.
        The _resolve_template_source_dir wrapper in init.py must honour those patches.
        """
        from guardkit.cli.init import _resolve_template_source_dir

        templates_base = tmp_path / "installer" / "core" / "templates"
        template_dir = templates_base / "my-template"
        template_dir.mkdir(parents=True)

        with patch(
            "guardkit.cli.init._get_templates_base_dir",
            return_value=templates_base,
        ):
            result = _resolve_template_source_dir("my-template")

        assert result == template_dir

    def test_resolve_identical_behaviour(self, tmp_path: Path) -> None:
        """Public resolve_template_source_dir behaves identically to init wrapper."""
        from guardkit.cli.init import _resolve_template_source_dir

        templates_base = tmp_path / "pkg"
        templates_base.mkdir()

        user_templates = tmp_path / "user"
        user_templates.mkdir()

        with (
            patch(
                "guardkit.templates.resolver._get_templates_base_dir",
                return_value=templates_base,
            ),
            patch(
                "guardkit.templates.resolver._get_user_templates_dir",
                return_value=user_templates,
            ),
            patch(
                "guardkit.cli.init._get_templates_base_dir",
                return_value=templates_base,
            ),
            patch(
                "guardkit.cli.init._get_user_templates_dir",
                return_value=user_templates,
            ),
        ):
            # Both should return None for nonexistent template
            assert resolve_template_source_dir("nope") is None
            assert _resolve_template_source_dir("nope") is None
