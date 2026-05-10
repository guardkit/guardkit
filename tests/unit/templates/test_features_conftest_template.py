"""Unit tests for the canonical features/conftest.py template (TASK-AB-004).

The template lives at
``installer/core/templates/common/features/conftest.py.template`` and is the
collection-bridge that GuardKit projects copy into their ``features/``
directory. Per-task glue lookup is the load-bearing change versus the
single-task legacy version: when ``GUARDKIT_BDD_TASK_ID`` is set, the
collector prefers ``test_<slug>__<sanitised_task_id>.py`` over
``test_<slug>.py``.

These tests load the template via ``importlib.util.spec_from_file_location``
(the .template suffix means it is not auto-discovered) and exercise the
pure helpers ``_sanitise_tag``, ``_glue_candidates``, and ``_select_glue``.
End-to-end pytest-bdd collection is exercised by the consuming project's
own test suite; here we only validate the template's selection logic.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE_PATH = (
    _REPO_ROOT
    / "installer"
    / "core"
    / "templates"
    / "common"
    / "features"
    / "conftest.py.template"
)


def _load_template_module():
    """Load the conftest.py.template file as an importable module.

    The .template suffix means importlib's default extension-driven loader
    inference fails (returns ``spec=None``); pass an explicit
    :class:`SourceFileLoader` instead so the file is treated as Python
    source regardless of its filename suffix.
    """
    module_name = "_features_conftest_template_under_test"
    loader = SourceFileLoader(module_name, str(_TEMPLATE_PATH))
    spec = importlib.util.spec_from_loader(module_name, loader)
    assert spec is not None, (
        f"Could not load template at {_TEMPLATE_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def conftest_module():
    return _load_template_module()


@pytest.fixture
def slug_dir(tmp_path: Path) -> Path:
    """Create a ``features/<slug>/`` directory with a feature file inside."""
    slug = tmp_path / "fleet-gateway-common-and-interfaces"
    slug.mkdir()
    return slug


@pytest.fixture
def feature_file(slug_dir: Path) -> Path:
    fp = slug_dir / "fleet-gateway-common-and-interfaces.feature"
    fp.write_text("Feature: x\n", encoding="utf-8")
    return fp


# ---------------------------------------------------------------------------
# _sanitise_tag — must mirror bdd_runner._build_pytest_argv
# ---------------------------------------------------------------------------


class TestSanitiseTag:
    def test_strips_leading_at_and_replaces_punctuation(self, conftest_module):
        assert conftest_module._sanitise_tag("@task:TASK-FG-002") == "task_TASK_FG_002"

    def test_handles_tag_without_leading_at(self, conftest_module):
        # Internal callers pass the env var (no @) directly.
        assert conftest_module._sanitise_tag("TASK-FG-002") == "TASK_FG_002"

    def test_idempotent_for_already_sanitised(self, conftest_module):
        assert conftest_module._sanitise_tag("TASK_FG_002") == "TASK_FG_002"


# ---------------------------------------------------------------------------
# _glue_candidates — priority order
# ---------------------------------------------------------------------------


class TestGlueCandidates:
    def test_per_task_first_then_legacy_when_env_set(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC: when GUARDKIT_BDD_TASK_ID is set, the per-task glue is first
        # in the candidate list and the legacy glue is the fallback.
        monkeypatch.setenv(conftest_module._BDD_TASK_ID_ENV, "TASK-FG-002")
        candidates = conftest_module._glue_candidates(feature_file)

        assert len(candidates) == 2
        assert candidates[0].name == (
            "test_fleet_gateway_common_and_interfaces__TASK_FG_002.py"
        )
        assert candidates[1].name == (
            "test_fleet_gateway_common_and_interfaces.py"
        )

    def test_only_legacy_when_env_unset(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC: env var unset → only legacy candidate (preserves single-task
        # projects that have not opted into per-task naming).
        monkeypatch.delenv(conftest_module._BDD_TASK_ID_ENV, raising=False)
        candidates = conftest_module._glue_candidates(feature_file)

        assert len(candidates) == 1
        assert candidates[0].name == (
            "test_fleet_gateway_common_and_interfaces.py"
        )


# ---------------------------------------------------------------------------
# _select_glue — picks the first candidate that exists on disk
# ---------------------------------------------------------------------------


class TestSelectGlue:
    def test_per_task_glue_selected_when_both_exist(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC (TASK-AB-004 verification recipe): with both the legacy shared
        # module and the per-task module present, the per-task module wins
        # when the env var matches.
        slug_dir = feature_file.parent
        legacy = slug_dir / "test_fleet_gateway_common_and_interfaces.py"
        per_task = (
            slug_dir
            / "test_fleet_gateway_common_and_interfaces__TASK_FG_002.py"
        )
        legacy.write_text("# legacy\n", encoding="utf-8")
        per_task.write_text("# per-task\n", encoding="utf-8")

        monkeypatch.setenv(conftest_module._BDD_TASK_ID_ENV, "TASK-FG-002")
        selected = conftest_module._select_glue(feature_file)

        assert selected == per_task

    def test_falls_back_to_legacy_when_per_task_missing(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC: env var set but per-task glue does not exist → legacy fallback.
        slug_dir = feature_file.parent
        legacy = slug_dir / "test_fleet_gateway_common_and_interfaces.py"
        legacy.write_text("# legacy\n", encoding="utf-8")

        monkeypatch.setenv(conftest_module._BDD_TASK_ID_ENV, "TASK-FG-002")
        selected = conftest_module._select_glue(feature_file)

        assert selected == legacy

    def test_picks_legacy_when_env_unset(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC: env unset, only legacy module exists → legacy selected.
        slug_dir = feature_file.parent
        legacy = slug_dir / "test_fleet_gateway_common_and_interfaces.py"
        legacy.write_text("# legacy\n", encoding="utf-8")

        monkeypatch.delenv(conftest_module._BDD_TASK_ID_ENV, raising=False)
        selected = conftest_module._select_glue(feature_file)

        assert selected == legacy

    def test_returns_none_when_no_glue_present(
        self, conftest_module, feature_file: Path, monkeypatch
    ):
        # AC: when neither file exists, the conftest yields nothing
        # (current behaviour preserved). Here we exercise _select_glue,
        # which the _FeatureFile.collect() iterator depends on.
        monkeypatch.setenv(conftest_module._BDD_TASK_ID_ENV, "TASK-FG-002")
        selected = conftest_module._select_glue(feature_file)

        assert selected is None
