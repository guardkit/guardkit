"""Tests for the features/conftest.py auto-install bridge (TASK-AB-BDDNEUTRAL01).

The installer is a guarded, idempotent, non-raising bootstrap helper. It writes
the canonical ``features/conftest.py`` pytest-bdd collection bridge into a
target directory ONLY when the project actually uses task-scoped BDD (a
``features/`` dir with at least one ``.feature`` file) and has no bridge yet.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path

import guardkit.templates.conftest_bridge as bridge
from guardkit.templates.conftest_bridge import install_features_conftest_bridge


_FEATURE_BODY = """\
@task:TASK-AB-BDDNEUTRAL01
Feature: Sample
  Scenario: One
    Given a thing
"""


def _make_features(target: Path, *, rel: str = "sample.feature") -> Path:
    feature = target / "features" / rel
    feature.parent.mkdir(parents=True, exist_ok=True)
    feature.write_text(_FEATURE_BODY, encoding="utf-8")
    return feature


class TestInstallHappyPath:
    def test_installs_when_features_present_and_no_bridge(self, tmp_path: Path):
        _make_features(tmp_path)
        dest = tmp_path / "features" / "conftest.py"
        assert not dest.exists()

        installed = install_features_conftest_bridge(tmp_path)

        assert installed is True
        assert dest.is_file()
        # Content is the canonical bridge (carries the collection hook).
        text = dest.read_text(encoding="utf-8")
        assert "pytest_collect_file" in text
        assert "GUARDKIT_BDD_TASK_ID" in text

    def test_installed_content_matches_canonical_template(self, tmp_path: Path):
        _make_features(tmp_path)
        install_features_conftest_bridge(tmp_path)

        from guardkit.templates.resolver import _get_templates_base_dir

        template = (
            _get_templates_base_dir()
            / "common"
            / "features"
            / "conftest.py.template"
        )
        assert (tmp_path / "features" / "conftest.py").read_text(
            encoding="utf-8"
        ) == template.read_text(encoding="utf-8")

    def test_nested_feature_file_triggers_install(self, tmp_path: Path):
        # Recursive discovery: features/<slug>/<slug>.feature (jarvis layout).
        _make_features(tmp_path, rel="login/login.feature")
        assert install_features_conftest_bridge(tmp_path) is True
        assert (tmp_path / "features" / "conftest.py").is_file()

    def test_returns_true_only_once_idempotent(self, tmp_path: Path):
        _make_features(tmp_path)
        assert install_features_conftest_bridge(tmp_path) is True
        # Second call is a no-op (bridge now exists).
        assert install_features_conftest_bridge(tmp_path) is False


class TestGuards:
    def test_no_features_dir_is_noop(self, tmp_path: Path):
        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features").exists()

    def test_features_dir_without_feature_files_is_noop(self, tmp_path: Path):
        (tmp_path / "features").mkdir()
        # A stray non-.feature file does not count.
        (tmp_path / "features" / "README.md").write_text("x", encoding="utf-8")
        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features" / "conftest.py").exists()

    def test_never_clobbers_existing_conftest(self, tmp_path: Path):
        _make_features(tmp_path)
        dest = tmp_path / "features" / "conftest.py"
        dest.write_text("# project's own bridge\n", encoding="utf-8")

        installed = install_features_conftest_bridge(tmp_path)

        assert installed is False
        # Untouched.
        assert dest.read_text(encoding="utf-8") == "# project's own bridge\n"

    def test_vendored_feature_files_are_ignored(self, tmp_path: Path):
        # A .feature under an excluded vendored dir must NOT trigger install.
        vendored = tmp_path / "features" / "node_modules" / "pkg"
        vendored.mkdir(parents=True)
        (vendored / "vendor.feature").write_text(_FEATURE_BODY, encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features" / "conftest.py").exists()

    def test_dotdir_feature_files_are_ignored(self, tmp_path: Path):
        hidden = tmp_path / "features" / ".cache"
        hidden.mkdir(parents=True)
        (hidden / "x.feature").write_text(_FEATURE_BODY, encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is False


class TestNonRaising:
    def test_missing_template_returns_false_not_raise(
        self, tmp_path: Path, monkeypatch
    ):
        _make_features(tmp_path)
        # Point the template resolver at an empty dir so the template is absent.
        empty = tmp_path / "no_templates_here"
        empty.mkdir()
        monkeypatch.setattr(bridge, "_get_templates_base_dir", lambda: empty)

        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features" / "conftest.py").exists()

    def test_copy_error_returns_false_not_raise(
        self, tmp_path: Path, monkeypatch
    ):
        _make_features(tmp_path)

        def _boom(*_a, **_k):
            raise OSError("disk full")

        monkeypatch.setattr(bridge.shutil, "copy2", _boom)
        assert install_features_conftest_bridge(tmp_path) is False
