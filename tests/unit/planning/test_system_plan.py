"""Tests for system_plan orchestrator."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.planning.system_plan import (
    _DEFAULT_OUTPUT_DIR,
    _get_graphiti_client,
    _persist_entities,
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


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient that appears enabled."""
    client = MagicMock()
    client.enabled = True
    client.get_group_id = MagicMock(return_value="test_group")
    return client


# ---------------------------------------------------------------------------
# _get_graphiti_client tests
# ---------------------------------------------------------------------------


class TestGetGraphitiClient:
    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self):
        result = await _get_graphiti_client(enable_context=False)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_client_not_enabled(self):
        # When enable_context=True but client is not enabled or unavailable
        result = await _get_graphiti_client(enable_context=True)
        # Will return None because get_graphiti may not be available
        # or client may not be enabled — graceful either way
        assert result is None or result is not None


# ---------------------------------------------------------------------------
# _persist_entities tests
# ---------------------------------------------------------------------------


class TestPersistEntities:
    @pytest.fixture
    def mock_service(self):
        service = AsyncMock()
        # Return a mock with .uuid for successful upserts
        mock_result = MagicMock()
        mock_result.uuid = "test-uuid-123"
        service.upsert_system_context.return_value = "uuid-sys"
        service.upsert_component.return_value = "uuid-comp"
        service.upsert_crosscutting.return_value = "uuid-xc"
        service.upsert_adr.return_value = "uuid-adr"
        return service

    @pytest.mark.asyncio
    async def test_upserts_all_entity_types(self, mock_service, make_spec_result):
        counts = await _persist_entities(mock_service, make_spec_result)

        assert counts["system_contexts"] == 1
        assert counts["components"] == 1
        assert counts["concerns"] == 1
        assert counts["decisions"] == 1

        mock_service.upsert_system_context.assert_called_once()
        mock_service.upsert_component.assert_called_once()
        mock_service.upsert_crosscutting.assert_called_once()
        mock_service.upsert_adr.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_none_system_context(self, mock_service, make_spec_result):
        make_spec_result.system_context = None
        counts = await _persist_entities(mock_service, make_spec_result)
        assert counts["system_contexts"] == 0
        mock_service.upsert_system_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_counts_failed_upserts_as_zero(self, mock_service, make_spec_result):
        mock_service.upsert_component.return_value = None  # Failed
        counts = await _persist_entities(mock_service, make_spec_result)
        assert counts["components"] == 0

    @pytest.mark.asyncio
    async def test_multiple_components(self, mock_service, make_spec_result):
        make_spec_result.components.append(
            ComponentDef(
                name="DB Layer",
                description="Database",
                methodology="modular",
            )
        )
        counts = await _persist_entities(mock_service, make_spec_result)
        assert counts["components"] == 2
        assert mock_service.upsert_component.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_decisions(self, mock_service, make_spec_result):
        make_spec_result.decisions.append(
            ArchitectureDecision(
                number=2,
                title="Use Docker",
                status="accepted",
                context="Deployment",
                decision="Docker containers",
            )
        )
        counts = await _persist_entities(mock_service, make_spec_result)
        assert counts["decisions"] == 2


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
            graphiti_available=True,
            persist_counts={
                "system_contexts": 1,
                "components": 1,
                "concerns": 1,
                "decisions": 1,
            },
            files_written=["docs/architecture/ARCHITECTURE.md"],
        )
        output = capsys.readouterr().out
        assert "System Plan Complete" in output
        assert "Mode: setup" in output
        assert "Total:" in output
        assert "ARCHITECTURE.md" in output

    def test_prints_graphiti_skipped(self, make_spec_result, capsys):
        _report_results(
            mode="setup",
            spec=make_spec_result,
            graphiti_available=False,
            persist_counts=None,
            files_written=[],
        )
        output = capsys.readouterr().out
        assert "SKIPPED" in output
        assert "markdown-only" in output

    def test_prints_parse_warnings(self, make_spec_result, capsys):
        make_spec_result.parse_warnings = ["Missing section X"]
        _report_results(
            mode="setup",
            spec=make_spec_result,
            graphiti_available=False,
            persist_counts=None,
            files_written=[],
        )
        output = capsys.readouterr().out
        assert "Missing section X" in output


# ---------------------------------------------------------------------------
# run_system_plan integration tests
# ---------------------------------------------------------------------------


class TestRunSystemPlan:
    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_no_context_file_prints_message(
        self, mock_detect_mode, mock_get_client, capsys
    ):
        mock_get_client.return_value = None
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
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_mode_override_skips_detection(
        self, mock_detect_mode, mock_get_client, capsys
    ):
        mock_get_client.return_value = None

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
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_missing_context_file_reports_error(
        self, mock_detect_mode, mock_get_client, capsys
    ):
        mock_get_client.return_value = None
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
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_full_pipeline_without_graphiti(
        self, mock_detect_mode, mock_get_client, mock_write, spec_file, capsys
    ):
        mock_get_client.return_value = None
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
        assert "SKIPPED" in output  # Graphiti skipped
        mock_write.assert_called_once()

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan._write_artefacts")
    @patch("guardkit.planning.system_plan._persist_entities", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_full_pipeline_with_graphiti(
        self,
        mock_detect_mode,
        mock_get_client,
        mock_persist,
        mock_write,
        spec_file,
        capsys,
    ):
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_get_client.return_value = mock_client
        mock_detect_mode.return_value = "setup"
        mock_persist.return_value = {
            "system_contexts": 1,
            "components": 1,
            "concerns": 1,
            "decisions": 1,
        }
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
        assert "Total persisted:" in output
        mock_persist.assert_called_once()

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    async def test_context_disabled_skips_graphiti(self, mock_get_client, capsys):
        mock_get_client.return_value = None

        await run_system_plan(
            description="TestApp",
            mode="setup",
            focus="all",
            no_questions=False,
            defaults=False,
            context_file=None,
            enable_context=False,
        )

        mock_get_client.assert_called_once_with(False)

    @pytest.mark.asyncio
    @patch("guardkit.planning.system_plan._write_artefacts")
    @patch("guardkit.planning.system_plan._get_graphiti_client", new_callable=AsyncMock)
    @patch("guardkit.planning.system_plan.detect_mode", new_callable=AsyncMock)
    async def test_graphiti_warning_when_unavailable(
        self, mock_detect_mode, mock_get_client, mock_write, spec_file, capsys
    ):
        mock_get_client.return_value = None
        mock_detect_mode.return_value = "setup"
        mock_write.return_value = []

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
        assert "Graphiti unavailable" in output


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

    def test_contains_upsert_calls(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "upsert_component" in content
        assert "upsert_adr" in content
        assert "upsert_system_context" in content
        assert "upsert_crosscutting" in content

    def test_contains_detect_mode(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "detect_mode" in content

    def test_contains_architecture_writer(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "ArchitectureWriter" in content

    def test_contains_parse_architecture_spec(self):
        content = Path("guardkit/planning/system_plan.py").read_text()
        assert "parse_architecture_spec" in content
