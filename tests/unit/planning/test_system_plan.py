"""Tests for system_plan orchestrator (markdown-only, post fleet-memory cutover)."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from guardkit.planning.system_plan import (
    _DEFAULT_OUTPUT_DIR,
    _report_results,
    _write_artefacts,
    run_system_plan,
)
from guardkit.planning.arch_spec_parser import ArchSpecResult
from guardkit.knowledge.entities.architecture_context import ArchitectureDecision
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.system_context import SystemContextDef


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SPEC_CONTENT = """\
## 1. System Context

### Identity

- **Name**: TestApp
- **Purpose**: Unit test target
- **Methodology**: Modular

### External Systems

| System | Integration | Purpose |
|--------|-------------|---------|
| **Redis** | Direct | Cache |

## 2. Components

### COMP-api: API Layer

- **Purpose**: Handles requests
- **Responsibilities**: Routing
- **Dependencies**: Database

## 4. Cross-Cutting Concerns

### XC-logging: Logging

- **Approach**: JSON logging
- **Affected Components**: API Layer
- **Constraints**: No PII

## 5. Architecture Decisions

### ADR-SP-001: Use REST

- **Status**: Accepted
- **Context**: Simplicity
- **Decision**: REST API
- **Consequences**: +Simple
"""


@pytest.fixture
def spec_file(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text(MINIMAL_SPEC_CONTENT)
    return p


@pytest.fixture
def make_spec_result():
    """Create a sample ArchSpecResult for testing."""
    system = SystemContextDef(
        name="TestApp",
        purpose="Testing",
        bounded_contexts=["API"],
        external_systems=["Redis"],
        methodology="modular",
    )
    components = [
        ComponentDef(
            name="API Layer",
            description="Handles requests",
            responsibilities=["Routing"],
            dependencies=["Database"],
            methodology="modular",
        ),
    ]
    concerns = [
        CrosscuttingConcernDef(
            name="Logging",
            description="JSON logging",
            applies_to=["API Layer"],
            implementation_notes="No PII",
        ),
    ]
    decisions = [
        ArchitectureDecision(
            number=1,
            title="Use REST",
            status="accepted",
            context="Simplicity",
            decision="REST API",
            consequences=["+Simple"],
        ),
    ]
    return ArchSpecResult(
        system_context=system,
        components=components,
        concerns=concerns,
        decisions=decisions,
        parse_warnings=[],
    )


# ---------------------------------------------------------------------------
# _write_artefacts tests
# ---------------------------------------------------------------------------


class TestWriteArtefacts:
    def test_writes_files_for_modular(self, make_spec_result, tmp_path):
        output_dir = str(tmp_path / "output")
        files = _write_artefacts(make_spec_result, output_dir)

        assert len(files) >= 4  # index + system-context + components + crosscutting
        assert any("ARCHITECTURE.md" in f for f in files)
        assert any("system-context.md" in f for f in files)
        assert any("components.md" in f for f in files)  # modular, not ddd
        assert any("crosscutting-concerns.md" in f for f in files)

    def test_includes_adr_files(self, make_spec_result, tmp_path):
        output_dir = str(tmp_path / "output")
        files = _write_artefacts(make_spec_result, output_dir)
        assert any("ADR-SP-001.md" in f for f in files)

    def test_returns_empty_when_no_system_context(self, make_spec_result, tmp_path):
        make_spec_result.system_context = None
        output_dir = str(tmp_path / "output")
        files = _write_artefacts(make_spec_result, output_dir)
        assert files == []

    def test_ddd_methodology_uses_bounded_contexts(self, make_spec_result, tmp_path):
        make_spec_result.system_context.methodology = "ddd"
        for comp in make_spec_result.components:
            comp.methodology = "ddd"
        output_dir = str(tmp_path / "output")
        files = _write_artefacts(make_spec_result, output_dir)
        assert any("bounded-contexts.md" in f for f in files)


# ---------------------------------------------------------------------------
# _report_results tests
# ---------------------------------------------------------------------------


class TestReportResults:
    def test_prints_success_report(self, make_spec_result, capsys):
        _report_results(
            mode="setup",
            spec=make_spec_result,
            files_written=["docs/architecture/ARCHITECTURE.md"],
        )
        output = capsys.readouterr().out
        assert "System Plan Complete" in output
        assert "Mode: setup" in output
        assert "Total:" in output
        assert "ARCHITECTURE.md" in output

    def test_prints_none_written_when_no_files(self, make_spec_result, capsys):
        _report_results(
            mode="setup",
            spec=make_spec_result,
            files_written=[],
        )
        output = capsys.readouterr().out
        assert "none written" in output

    def test_prints_parse_warnings(self, make_spec_result, capsys):
        make_spec_result.parse_warnings = ["Missing section X"]
        _report_results(
            mode="setup",
            spec=make_spec_result,
            files_written=[],
        )
        output = capsys.readouterr().out
        assert "Missing section X" in output


# ---------------------------------------------------------------------------
# run_system_plan integration tests (markdown-only)
# ---------------------------------------------------------------------------


class TestRunSystemPlan:
    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_no_context_file_prints_message(self, mock_detect_mode, capsys):
        mock_detect_mode.return_value = "setup"

        await run_system_plan(
            description="TestApp",
            mode=None,
            focus="all",
            no_questions=False,
            defaults=False,
            context_file=None,
            enable_context=True,
        )

        output = capsys.readouterr().out
        assert "No --context file provided" in output
        mock_detect_mode.assert_called_once()

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_mode_override_skips_detection(self, mock_detect_mode, capsys):
        await run_system_plan(
            description="TestApp",
            mode="refine",
            focus="all",
            no_questions=False,
            defaults=False,
            context_file=None,
            enable_context=True,
        )

        output = capsys.readouterr().out
        assert "Mode: refine" in output
        mock_detect_mode.assert_not_called()

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_missing_context_file_reports_error(self, mock_detect_mode, capsys):
        mock_detect_mode.return_value = "setup"

        await run_system_plan(
            description="TestApp",
            mode=None,
            focus="all",
            no_questions=False,
            defaults=False,
            context_file="/nonexistent/path.md",
            enable_context=True,
        )

        output = capsys.readouterr().out
        assert "Error: Context file not found" in output

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan._write_artefacts")
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_full_pipeline_markdown_only(
        self, mock_detect_mode, mock_write, spec_file, capsys
    ):
        mock_detect_mode.return_value = "setup"
        mock_write.return_value = ["docs/architecture/ARCHITECTURE.md"]

        await run_system_plan(
            description="TestApp",
            mode=None,
            focus="all",
            no_questions=False,
            defaults=False,
            context_file=str(spec_file),
            enable_context=True,
        )

        output = capsys.readouterr().out
        assert "System Plan Complete" in output
        assert "Generating architecture markdown" in output
        mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# Anti-stub verification
# ---------------------------------------------------------------------------


class TestAntiStub:
    """Verify system_plan.py is not a stub per anti-stub quality rule."""

    def test_not_a_stub(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        lines = [
            l
            for l in content.split("\n")
            if l.strip()
            and not l.strip().startswith("#")
            and not l.strip().startswith('"')
        ]
        assert len(lines) > 50, f"Still a stub: only {len(lines)} non-comment lines"

    def test_contains_detect_mode(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "detect_mode" in content

    def test_contains_architecture_writer(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "ArchitectureWriter" in content

    def test_contains_parse_architecture_spec(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "parse_architecture_spec" in content
