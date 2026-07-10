"""Tests for the `guardkit template coverage` CLI subcommand (PB-7 / DIM1-F3).

Covers:
  * exit 0 report-only for unenforced templates with gaps;
  * exit 1 when an enforced (mocked) template has a non-covered row;
  * CLI registration under the `template` group.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from guardkit.cli.template import coverage, template
from guardkit.templates.coverage_matrix import LayerCoverage, TemplateCoverage


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _missing_row(layer: str) -> LayerCoverage:
    return LayerCoverage(
        layer=layer,
        effective_subdir=layer,
        used_alias=False,
        templates_present=False,
        loader_reachable=False,
    )


def _covered_row(layer: str) -> LayerCoverage:
    return LayerCoverage(
        layer=layer,
        effective_subdir=layer,
        used_alias=False,
        templates_present=True,
        loader_reachable=True,
        reachable_files=(f"{layer}/x.py.template",),
        gate_ok_files=(f"{layer}/x.py.template",),
    )


class TestCoverageCommand:
    def test_registered_under_template_group(self) -> None:
        assert "coverage" in template.commands

    def test_report_only_exits_zero_with_gaps(self, runner: CliRunner) -> None:
        result_data = TemplateCoverage(
            template_name="fastapi-python",
            layers=(_covered_row("api"), _missing_row("services")),
            enforced=False,
        )
        with patch(
            "guardkit.cli.template.gate_is_available", return_value=True
        ), patch(
            "guardkit.cli.template.compute_coverage_all", return_value=[result_data]
        ):
            result = runner.invoke(coverage, ["fastapi-python"])

        assert result.exit_code == 0
        assert "services" in result.output
        assert "missing" in result.output

    def test_enforced_template_with_gap_exits_nonzero(self, runner: CliRunner) -> None:
        result_data = TemplateCoverage(
            template_name="fastapi-python",
            layers=(_covered_row("api"), _missing_row("services")),
            enforced=True,
        )
        with patch(
            "guardkit.cli.template.gate_is_available", return_value=True
        ), patch(
            "guardkit.cli.template.compute_coverage_all", return_value=[result_data]
        ):
            result = runner.invoke(coverage, ["fastapi-python"])

        assert result.exit_code == 1
        assert "COVERAGE GATE FAILED" in result.output

    def test_fully_covered_enforced_template_exits_zero(
        self, runner: CliRunner
    ) -> None:
        result_data = TemplateCoverage(
            template_name="fastapi-python",
            layers=(_covered_row("api"),),
            enforced=True,
        )
        with patch(
            "guardkit.cli.template.gate_is_available", return_value=True
        ), patch(
            "guardkit.cli.template.compute_coverage_all", return_value=[result_data]
        ):
            result = runner.invoke(coverage, ["fastapi-python"])

        assert result.exit_code == 0
        assert "COVERAGE REPORT COMPLETE" in result.output

    def test_no_layer_mappings_is_reported_and_skipped(self, runner: CliRunner) -> None:
        result_data = TemplateCoverage(
            template_name="default", layers=(), enforced=False
        )
        with patch(
            "guardkit.cli.template.gate_is_available", return_value=True
        ), patch(
            "guardkit.cli.template.compute_coverage_all", return_value=[result_data]
        ):
            result = runner.invoke(coverage, ["default"])

        assert result.exit_code == 0
        assert "no layer_mappings, skipped" in result.output

    def test_gate_unavailable_warns_but_still_reports(self, runner: CliRunner) -> None:
        result_data = TemplateCoverage(
            template_name="fastapi-python",
            layers=(_covered_row("api"),),
            enforced=False,
        )
        with patch(
            "guardkit.cli.template.gate_is_available", return_value=False
        ), patch(
            "guardkit.cli.template.compute_coverage_all", return_value=[result_data]
        ) as mock_compute:
            result = runner.invoke(coverage, [])

        assert "tree-sitter runtime not installed" in result.output
        mock_compute.assert_called_once_with(names=None, check_gate=False)
        assert result.exit_code == 0

    def test_real_fastapi_python_is_fully_covered_and_enforced(
        self, runner: CliRunner
    ) -> None:
        """Integration smoke: real template dir, no mocking.

        fastapi-python is COVERAGE_ENFORCED (PB-7 build step 4) and reports
        9/9 after the services/ exemplar + tests->testing alias landed.
        """
        result = runner.invoke(coverage, ["fastapi-python"])
        assert result.exit_code == 0
        assert "fastapi-python" in result.output
        assert "9/9 covered" in result.output
        assert "enforced" in result.output
