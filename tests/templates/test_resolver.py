"""Tests for guardkit.templates.resolver module.

DF-011 reshaped resolution: the template payload ships in the wheel under the
guardkit namespace (guardkit/_installer_core) and resolves via
importlib.resources, with an editable-checkout fallback to installer/core. The
former ~/.guardkit/templates user-override fallback was removed (no installer
ever populated it).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from guardkit.templates.resolver import (
    _get_installer_core_dir,
    _get_templates_base_dir,
    resolve_template_source_dir,
)


class TestResolveTemplateSourceDir:
    """Test resolve_template_source_dir (public API)."""

    def test_resolves_from_package_location(self, tmp_path: Path) -> None:
        """Template source resolved from installed package location."""
        templates_base = tmp_path / "_installer_core" / "templates"
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
        """Returns None when template not found."""
        templates_base = tmp_path / "_installer_core" / "templates"
        templates_base.mkdir(parents=True)

        with patch(
            "guardkit.templates.resolver._get_templates_base_dir",
            return_value=templates_base,
        ):
            result = resolve_template_source_dir("nonexistent-template")

        assert result is None

    def test_no_user_override_fallback(self, tmp_path: Path) -> None:
        """DF-011: the ~/.guardkit/templates user fallback was removed.

        A template that exists only outside the templates base dir must NOT
        resolve — there is exactly one resolution path (packaged, with an
        editable fallback), no third never-populated namespace.
        """
        templates_base = tmp_path / "_installer_core" / "templates"
        templates_base.mkdir(parents=True)
        # A stray template somewhere else on disk must be invisible.
        stray = tmp_path / "user_templates" / "custom-template"
        stray.mkdir(parents=True)

        with patch(
            "guardkit.templates.resolver._get_templates_base_dir",
            return_value=templates_base,
        ):
            assert resolve_template_source_dir("custom-template") is None


class TestGetTemplatesBaseDir:
    """Test _get_templates_base_dir returns valid path."""

    def test_returns_templates_under_installer_core(self) -> None:
        """Returns a Path ending with .../templates under the payload root."""
        result = _get_templates_base_dir()
        assert isinstance(result, Path)
        assert result.name == "templates"
        # Parent is the installer/core payload root (packaged _installer_core in
        # a wheel, or installer/core in an editable checkout).
        assert result.parent.name in ("_installer_core", "core")


class TestGetInstallerCoreDir:
    """Test the packaged-vs-editable resolution of the payload root."""

    def test_editable_checkout_resolves_repo_installer_core(self) -> None:
        """In this editable checkout the repo's installer/core is used.

        The packaged guardkit/_installer_core does not exist under an editable
        guardkit/, so resolution falls back to the repo's installer/core.
        """
        result = _get_installer_core_dir()
        assert isinstance(result, Path)
        assert result.parts[-2:] == ("installer", "core")
        assert (result / "templates").is_dir()

    def test_prefers_packaged_when_present(self, tmp_path: Path, monkeypatch) -> None:
        """When guardkit/_installer_core exists (wheel), it is preferred."""
        fake_pkg = tmp_path / "site" / "guardkit"
        packaged = fake_pkg / "_installer_core"
        (packaged / "templates").mkdir(parents=True)

        class _Files:
            def __str__(self) -> str:
                return str(fake_pkg)

        monkeypatch.setattr(
            "guardkit.templates.resolver.importlib_resources.files",
            lambda name: _Files(),
        )
        assert _get_installer_core_dir() == packaged


class TestInstallerCoreBootstrap:
    """DF-011: guardkit._bootstrap_installer_core makes installer.core importable
    in a wheel; in an editable checkout it no-ops (the real installer wins)."""

    def test_installer_core_importable(self) -> None:
        """installer.core resolves (editable: repo; wheel: packaged alias)."""
        import installer.core  # noqa: F401

        assert "installer.core" in sys.modules

    def test_editable_uses_repo_installer_core(self) -> None:
        """In this editable checkout installer.core is the repo copy, not the
        packaged _installer_core alias."""
        import installer.core

        assert "_installer_core" not in installer.core.__file__
        assert installer.core.__file__.endswith("installer/core/__init__.py")


class TestBackwardCompatibility:
    """Ensure the old init import path still works."""

    def test_init_module_exposes_private_wrapper(self) -> None:
        """guardkit.cli.init._resolve_template_source_dir still importable."""
        from guardkit.cli.init import _resolve_template_source_dir

        assert callable(_resolve_template_source_dir)

    def test_init_module_exposes_helper_alias(self) -> None:
        """guardkit.cli.init._get_templates_base_dir alias still importable."""
        from guardkit.cli.init import _get_templates_base_dir as init_base

        assert init_base is _get_templates_base_dir

    def test_patching_init_module_name_works(self, tmp_path: Path) -> None:
        """Patching via the old module path still controls behaviour."""
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

    def test_patching_init_helper_controls_private_wrapper(
        self, tmp_path: Path
    ) -> None:
        """Patching guardkit.cli.init._get_templates_base_dir controls _resolve."""
        from guardkit.cli.init import _resolve_template_source_dir

        templates_base = tmp_path / "_installer_core" / "templates"
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

        with (
            patch(
                "guardkit.templates.resolver._get_templates_base_dir",
                return_value=templates_base,
            ),
            patch(
                "guardkit.cli.init._get_templates_base_dir",
                return_value=templates_base,
            ),
        ):
            assert resolve_template_source_dir("nope") is None
            assert _resolve_template_source_dir("nope") is None
