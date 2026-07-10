"""Unit tests for the exemplar-layer coverage matrix (PB-7 / DIM1-F3).

Covers:
  * COVERED / WARN / MISSING classification per the design-of-record §2 rules;
  * the loader's REAL join (leaf parent-directory name) vs a naive "anywhere
    under the subdir tree" existence check — the nested-file gap;
  * the ``template_subdir`` additive alias (the ``tests`` -> ``testing`` class
    of mismatch);
  * OPTOUT/ERROR/SKIPPED files count for existence but never for validated
    coverage (``absence-of-failure-is-not-success.md``);
  * templates with no ``settings.json`` / empty ``layer_mappings`` -> zero
    rows, vacuously ``fully_covered``;
  * ``COVERAGE_ENFORCED`` is empty by default (report-only posture).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.templates.coverage_matrix import (
    COVERAGE_ENFORCED,
    CoverageStatus,
    compute_coverage,
    compute_coverage_all,
    compute_coverage_for_dir,
)

requires_treesitter = pytest.mark.skipif(
    not __import__(
        "guardkit.templates.parse_gate", fromlist=["available_languages"]
    ).available_languages(),
    reason="tree-sitter runtime not installed (pip install 'guardkit-py[templates]')",
)


def _write_settings(template_dir: Path, layer_mappings: dict) -> None:
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "settings.json").write_text(
        json.dumps({"schema_version": "1.0.0", "layer_mappings": layer_mappings})
    )


def _write_template_file(template_dir: Path, rel: str, content: str) -> None:
    fpath = template_dir / "templates" / rel
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(content)


class TestNoSettingsOrEmptyMappings:
    def test_no_settings_json_yields_zero_rows(self, tmp_path: Path) -> None:
        (tmp_path / "some-template").mkdir()
        result = compute_coverage("some-template", templates_base=tmp_path)
        assert result.layers == ()
        assert result.fully_covered is True
        assert result.total_count == 0

    def test_empty_layer_mappings_yields_zero_rows(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "empty-tpl"
        _write_settings(template_dir, {})
        result = compute_coverage("empty-tpl", templates_base=tmp_path)
        assert result.layers == ()
        assert result.fully_covered is True

    def test_nonexistent_template_dir_yields_zero_rows(self, tmp_path: Path) -> None:
        result = compute_coverage("nonexistent-xyz", templates_base=tmp_path)
        assert result.layers == ()


class TestMissing:
    def test_no_matching_directory_is_missing(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"services": {"directory": "src/service.py"}})
        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=False)
        assert len(result.layers) == 1
        row = result.layers[0]
        assert row.status is CoverageStatus.MISSING
        assert row.templates_present is False
        assert row.loader_reachable is False

    def test_nested_file_is_present_but_not_reachable(self, tmp_path: Path) -> None:
        """A file one level deeper than the layer subdir is present-but-unreachable.

        The loader's real join is leaf-parent-directory-name equality
        (``_match_files_by_subdirs``) — a file under
        ``templates/api/nested/x.py.template`` has parent name ``nested``,
        not ``api``, so the loader can never select it.
        """
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        _write_template_file(template_dir, "api/nested/router.py.template", "# x")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=False)
        row = result.layers[0]
        assert row.templates_present is True
        assert row.loader_reachable is False
        assert row.status is CoverageStatus.MISSING


class TestWarn:
    @requires_treesitter
    def test_optout_only_is_warn_not_covered(self, tmp_path: Path) -> None:
        from guardkit.templates.parse_gate import OPTOUT_MARKER

        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        _write_template_file(
            template_dir,
            "api/router.py.template",
            f"# {OPTOUT_MARKER}\nnot even python(((",
        )

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert row.templates_present is True
        assert row.loader_reachable is True
        assert row.gate_ok_files == ()
        assert len(row.gate_optout_files) == 1
        assert row.status is CoverageStatus.WARN

    @requires_treesitter
    def test_parse_error_only_is_warn_not_covered(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        # Unterminated function def -> a real tree-sitter ERROR node.
        _write_template_file(template_dir, "api/router.py.template", "def f(:\n")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert row.gate_ok_files == ()
        assert len(row.gate_error_files) == 1
        assert row.status is CoverageStatus.WARN

    def test_non_gated_extension_only_is_warn(self, tmp_path: Path) -> None:
        """A .toml/.ini-only layer is present+reachable but never gate-OK."""
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"config": {"directory": "config"}})
        _write_template_file(template_dir, "config/pyproject.toml.template", "[tool]")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert row.templates_present is True
        assert row.loader_reachable is True
        assert row.gate_ok_files == ()
        assert len(row.gate_skipped_files) == 1
        assert row.status is CoverageStatus.WARN

    def test_check_gate_false_treats_available_as_unvalidated(
        self, tmp_path: Path
    ) -> None:
        """gate unavailable -> present+reachable rows report WARN, never COVERED."""
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        _write_template_file(template_dir, "api/router.py.template", "x = 1\n")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=False)
        row = result.layers[0]
        assert row.loader_reachable is True
        assert row.gate_ok_files == ()
        assert row.status is CoverageStatus.WARN


class TestCovered:
    @requires_treesitter
    def test_valid_python_file_is_covered(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        _write_template_file(template_dir, "api/router.py.template", "x = 1\n")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert row.status is CoverageStatus.COVERED
        assert result.fully_covered is True

    @requires_treesitter
    def test_one_ok_file_covers_layer_even_with_a_sibling_optout(
        self, tmp_path: Path
    ) -> None:
        """>=1 gate-OK file is sufficient — a layer need not be unanimous."""
        from guardkit.templates.parse_gate import OPTOUT_MARKER

        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        _write_template_file(template_dir, "api/router.py.template", "x = 1\n")
        _write_template_file(
            template_dir,
            "api/weird.py.template",
            f"# {OPTOUT_MARKER}\n((( not python",
        )

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert len(row.gate_ok_files) == 1
        assert len(row.gate_optout_files) == 1
        assert row.status is CoverageStatus.COVERED


class TestTemplateSubdirAlias:
    @requires_treesitter
    def test_alias_resolves_name_mismatch(self, tmp_path: Path) -> None:
        """The tests -> testing class of mismatch, closed by template_subdir."""
        template_dir = tmp_path / "tpl"
        _write_settings(
            template_dir,
            {"tests": {"directory": "tests", "template_subdir": "testing"}},
        )
        _write_template_file(template_dir, "testing/conftest.py.template", "x = 1\n")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=True)
        row = result.layers[0]
        assert row.used_alias is True
        assert row.effective_subdir == "testing"
        assert row.status is CoverageStatus.COVERED

    def test_without_alias_the_mismatch_is_missing(self, tmp_path: Path) -> None:
        """Same fixture, no alias -> proves the alias is what closes the gap."""
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"tests": {"directory": "tests"}})
        _write_template_file(template_dir, "testing/conftest.py.template", "x = 1\n")

        result = compute_coverage("tpl", templates_base=tmp_path, check_gate=False)
        row = result.layers[0]
        assert row.used_alias is False
        assert row.status is CoverageStatus.MISSING


class TestComputeCoverageAll:
    def test_skips_nonexistent_names(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "real-tpl"
        _write_settings(template_dir, {})
        results = compute_coverage_all(
            names=["real-tpl", "ghost-tpl"], templates_base=tmp_path, check_gate=False
        )
        assert [r.template_name for r in results] == ["real-tpl"]

    def test_default_names_lists_all_template_dirs(self, tmp_path: Path) -> None:
        _write_settings(tmp_path / "tpl-a", {})
        _write_settings(tmp_path / "tpl-b", {})
        (tmp_path / "common").mkdir()  # excluded, matches parse_gate's convention

        results = compute_coverage_all(templates_base=tmp_path, check_gate=False)
        names = {r.template_name for r in results}
        assert names == {"tpl-a", "tpl-b"}


class TestComputeCoverageForDir:
    """Arbitrary-directory variant used by template-create's closing harvest
    report — the template need not live under the installed templates base."""

    def test_computes_against_a_freshly_harvested_dir(self, tmp_path: Path) -> None:
        harvested = tmp_path / "some-random-output-dir"
        _write_settings(harvested, {"api": {"directory": "src/api"}})
        _write_template_file(harvested, "api/router.py.template", "x = 1\n")

        result = compute_coverage_for_dir(harvested, check_gate=False)
        assert result.template_name == "some-random-output-dir"
        assert len(result.layers) == 1

    def test_explicit_name_overrides_dir_basename(self, tmp_path: Path) -> None:
        harvested = tmp_path / "output-dir"
        _write_settings(harvested, {})
        result = compute_coverage_for_dir(harvested, "my-template", check_gate=False)
        assert result.template_name == "my-template"

    def test_compute_coverage_delegates_to_for_dir(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {"api": {"directory": "src/api"}})
        via_name = compute_coverage("tpl", templates_base=tmp_path, check_gate=False)
        via_dir = compute_coverage_for_dir(template_dir, "tpl", check_gate=False)
        assert via_name == via_dir


@requires_treesitter
class TestAllShippedTemplatesReportOnly:
    """CI report-only gate over the real installed template set.

    Report-only for any template NOT in COVERAGE_ENFORCED — the matrix must
    compute without error, but a non-covered row does not fail the build.
    A template flips to red individually once added to COVERAGE_ENFORCED
    (the same seed-registry philosophy as PARSE_OPTOUT/TEMPLATES).
    """

    def test_computes_for_every_shipped_template_without_error(self) -> None:
        results = compute_coverage_all()
        assert len(results) >= 12  # the 12 stack templates (excludes common)

    def test_enforced_templates_are_fully_covered(self) -> None:
        results = compute_coverage_all(names=sorted(COVERAGE_ENFORCED))
        failures = {
            r.template_name: [
                (layer.layer, layer.status.value) for layer in r.non_covered
            ]
            for r in results
            if not r.fully_covered
        }
        assert not failures, f"COVERAGE_ENFORCED templates with gaps: {failures}"


class TestEnforcedRegistryDefault:
    def test_coverage_enforced_starts_report_only_plus_fastapi_python(self) -> None:
        """Report-only posture: only fastapi-python is enforced after its
        day-one holes (services/, tests->testing alias) were closed in this
        build; every other shipped template remains report-only."""
        assert COVERAGE_ENFORCED == frozenset({"fastapi-python"})

    def test_enforced_flag_reflects_membership(self, tmp_path: Path, monkeypatch) -> None:
        template_dir = tmp_path / "tpl"
        _write_settings(template_dir, {})
        monkeypatch.setattr(
            "guardkit.templates.coverage_matrix.COVERAGE_ENFORCED",
            frozenset({"tpl"}),
        )
        result = compute_coverage("tpl", templates_base=tmp_path)
        assert result.enforced is True

        result_unenforced = compute_coverage("other-tpl", templates_base=tmp_path)
        assert result_unenforced.enforced is False
