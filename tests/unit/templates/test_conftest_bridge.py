"""Tests for the features/conftest.py auto-install bridge (TASK-AB-BDDNEUTRAL01).

The installer is a guarded, idempotent, non-raising bootstrap helper. It writes
the canonical ``features/conftest.py`` pytest-bdd collection bridge into a
target directory ONLY when the project actually uses task-scoped BDD (a
``features/`` dir with at least one ``.feature`` file) and has no bridge yet.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


class TestLanguageCheck:
    """TS-lane D.1c: a TypeScript worktree must not receive a Python bridge.

    The bridge is a pytest-bdd collection hook. In a repo with no Python at
    all it is not merely useless — it is a Python file on disk that the
    project never asked for and the Player never wrote. ``ts-api-test``
    reaches this path for real: it carries
    ``features/get-time-endpoint/get-time-endpoint.feature`` (verified
    2026-07-31), so without the check its very first worktree gets one.

    The check is NEGATIVE by design — it refuses only when the target is
    POSITIVELY non-Python (a node manifest present AND no Python manifest).
    Backwards compatibility is the prime invariant, so every control below
    asserts the historic behaviour is byte-for-byte unchanged.
    """

    def test_typescript_worktree_gets_no_bridge(self, tmp_path: Path):
        _make_features(tmp_path, rel="get-time-endpoint/get-time-endpoint.feature")
        (tmp_path / "package.json").write_text(
            '{"name":"ts-api-test","scripts":{"test":"vitest run"}}',
            encoding="utf-8",
        )
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features" / "conftest.py").exists()

    def test_tsconfig_alone_is_enough_to_refuse(self, tmp_path: Path):
        _make_features(tmp_path)
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is False
        assert not (tmp_path / "features" / "conftest.py").exists()

    def test_refusal_is_loud_not_silent(self, tmp_path: Path, caplog):
        """A skip the operator cannot see is indistinguishable from a bug."""
        import logging

        _make_features(tmp_path)
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")

        with caplog.at_level(logging.INFO, logger="guardkit.templates.conftest_bridge"):
            assert install_features_conftest_bridge(tmp_path) is False

        assert any(
            "non-Python project" in record.message for record in caplog.records
        ), "the language-check refusal must name itself in the log"

    # ---- backwards-compatibility controls --------------------------------

    def test_python_worktree_still_gets_the_bridge(self, tmp_path: Path):
        """The Python path is unchanged (the control that matters most)."""
        _make_features(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is True
        assert (tmp_path / "features" / "conftest.py").is_file()

    def test_bare_worktree_with_no_manifests_still_gets_the_bridge(
        self, tmp_path: Path
    ):
        """No node manifest -> nothing changes. Every repo in the estate
        before tonight is this shape (or the Python one above)."""
        _make_features(tmp_path)

        assert install_features_conftest_bridge(tmp_path) is True
        assert (tmp_path / "features" / "conftest.py").is_file()

    @pytest.mark.parametrize(
        "marker,body",
        [
            ("pyproject.toml", "[project]\nname='x'\n"),
            ("setup.py", "from setuptools import setup\n"),
            ("setup.cfg", "[metadata]\nname = x\n"),
            ("requirements.txt", "pytest\n"),
            ("requirements-dev.txt", "pytest\n"),
            ("Pipfile", "[packages]\n"),
            ("tox.ini", "[tox]\n"),
            ("pytest.ini", "[pytest]\n"),
            ("conftest.py", "# root conftest\n"),
        ],
    )
    def test_polyglot_repo_keeps_the_bridge(
        self, tmp_path: Path, marker: str, body: str
    ):
        """A repo with BOTH stacks is a Python repo for this purpose.

        Refusing here would be a regression for any existing repo that
        happens to carry a package.json (docs tooling, a JS front end
        beside a Python API) — so the check demands the ABSENCE of every
        Python marker, not merely the presence of a node one.
        """
        _make_features(tmp_path)
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / marker).write_text(body, encoding="utf-8")

        assert install_features_conftest_bridge(tmp_path) is True
        assert (tmp_path / "features" / "conftest.py").is_file()


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
