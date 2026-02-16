"""
Seam Tests S3: Orchestrator → Module Wiring.

Tests that verify orchestrator functions actually call their module dependencies,
catching stub implementations where orchestration functions silently skip steps.

Key seams tested:
    - run_system_plan() → parse_architecture_spec()
    - run_system_plan() → _persist_entities()
    - run_system_plan() → _write_artefacts()
    - run_impact_analysis() → Graphiti context retrieval

Test philosophy:
    - Use REAL implementations on the orchestrator side
    - Use protocol-level mocks ONLY at external boundaries (Graphiti client, filesystem)
    - DO NOT mock orchestrator functions themselves - that defeats the purpose

Anti-patterns avoided:
    - DO NOT mock run_system_plan() - call it directly
    - DO NOT mock parse_architecture_spec() - let it run against real fixtures
    - DO mock Graphiti client at protocol level (AsyncMock with .enabled = True)
    - DO use tmp directories for file I/O assertions
"""

from __future__ import annotations

import asyncio
import json
import pytest
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch, call, MagicMock

if TYPE_CHECKING:
    from typing import Generator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def orchestrator_spec_path() -> Path:
    """
    Return path to the orchestrator test spec fixture file.

    This fixture provides a valid architecture spec for testing
    the orchestrator's parsing and processing pipeline. It follows
    the arch_spec_parser expected format.

    Returns:
        Path: Absolute path to the orchestrator-spec.md fixture file.
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "orchestrator-spec.md"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture file not found: {fixture_path}. "
            "Ensure tests/fixtures/orchestrator-spec.md exists."
        )
    return fixture_path


@pytest.fixture
def graphiti_mock_enabled() -> Mock:
    """
    Create a protocol-level mock for an ENABLED Graphiti client.

    This mock simulates a fully functional Graphiti client that:
    - Has .enabled = True
    - Records all upsert_episode calls for verification
    - Returns mock UUIDs for successful upserts
    - Provides get_group_id() that returns properly prefixed group IDs

    Returns:
        Mock: Configured mock client behaving like enabled Graphiti.
    """
    mock_client = Mock()
    mock_client.enabled = True
    mock_client._upsert_calls = []
    mock_client._search_calls = []

    async def record_upsert(**kwargs: Any) -> Mock:
        """Record upsert call and return mock result with uuid."""
        mock_client._upsert_calls.append(kwargs)
        result = Mock()
        result.uuid = f"mock-uuid-{len(mock_client._upsert_calls)}"
        return result

    mock_client.upsert_episode = AsyncMock(side_effect=record_upsert)

    async def record_search(**kwargs: Any) -> list:
        """Record search call and return empty results."""
        mock_client._search_calls.append(kwargs)
        return []

    mock_client.search = AsyncMock(side_effect=record_search)

    def get_group_id(group_name: str) -> str:
        return f"test-project__{group_name}"

    mock_client.get_group_id = Mock(side_effect=get_group_id)

    return mock_client


@pytest.fixture
def graphiti_mock_disabled() -> Mock:
    """
    Create a protocol-level mock for a DISABLED Graphiti client.

    This mock simulates a Graphiti client that is not available:
    - Has .enabled = False
    - All operations should be skipped by orchestrator

    Returns:
        Mock: Configured mock client with .enabled = False.
    """
    mock_client = Mock()
    mock_client.enabled = False
    return mock_client


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """
    Create a temporary output directory for architecture artifacts.

    Args:
        tmp_path: Pytest's tmp_path fixture.

    Returns:
        Path: Path to temporary docs/architecture directory.
    """
    output_dir = tmp_path / "docs" / "architecture"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# =============================================================================
# SEAM: run_system_plan() → parse_architecture_spec()
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestRunSystemPlanCallsParseArchitectureSpec:
    """
    Tests that run_system_plan() with context file calls parse_architecture_spec().

    Verifies that the orchestrator is not a stub - it actually invokes the
    spec parser with the provided context file.
    """

    async def test_run_system_plan_with_context_calls_parse_architecture_spec(
        self,
        orchestrator_spec_path: Path,
        graphiti_mock_disabled: Mock,
        tmp_output_dir: Path,
    ):
        """
        run_system_plan() with context file calls parse_architecture_spec().

        This test verifies that when a context file is provided,
        the orchestrator actually invokes the parser - not a stub.
        """
        from guardkit.planning.system_plan import run_system_plan

        # We use a spy pattern: wrap the real function to track calls
        parse_call_args = []

        original_parse = None

        def tracking_parse_wrapper(path: Path):
            from guardkit.planning.arch_spec_parser import parse_architecture_spec as real_parse
            parse_call_args.append(path)
            return real_parse(path)

        with patch(
            "guardkit.planning.system_plan.parse_architecture_spec",
            side_effect=tracking_parse_wrapper,
        ), patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,  # Disable Graphiti
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        # Verify parse_architecture_spec was called
        assert len(parse_call_args) > 0, (
            "run_system_plan() did NOT call parse_architecture_spec() - "
            "this indicates a stub implementation!"
        )
        assert parse_call_args[0] == orchestrator_spec_path

    async def test_run_system_plan_parses_spec_and_extracts_entities(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        run_system_plan() parses spec and extracts entities (not empty result).

        Verifies that the parser returns actual entities from the fixture.
        """
        from guardkit.planning.system_plan import run_system_plan

        with patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        # Verify files were created (proof that parsing succeeded)
        assert (tmp_output_dir / "ARCHITECTURE.md").exists(), (
            "ARCHITECTURE.md not created - parser or writer is a stub"
        )
        assert (tmp_output_dir / "system-context.md").exists(), (
            "system-context.md not created - parser or writer is a stub"
        )


# =============================================================================
# SEAM: run_system_plan() → _persist_entities()
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestRunSystemPlanCallsPersistEntities:
    """
    Tests that run_system_plan() calls _persist_entities() when Graphiti available.

    Verifies that when Graphiti is enabled, the orchestrator actually
    persists entities to the knowledge graph.
    """

    async def test_run_system_plan_calls_persist_entities_when_graphiti_available(
        self,
        orchestrator_spec_path: Path,
        graphiti_mock_enabled: Mock,
        tmp_output_dir: Path,
    ):
        """
        run_system_plan() with Graphiti available calls _persist_entities().

        This is the core seam test: verifies orchestrator wiring to persistence.
        """
        from guardkit.planning.system_plan import run_system_plan

        persist_call_args = []

        async def tracking_persist(service, spec):
            persist_call_args.append((service, spec))
            # Return mock counts
            return {
                "system_contexts": 1 if spec.system_context else 0,
                "components": len(spec.components),
                "concerns": len(spec.concerns),
                "decisions": len(spec.decisions),
            }

        with patch(
            "guardkit.planning.system_plan._persist_entities",
            side_effect=tracking_persist,
        ), patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=graphiti_mock_enabled,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=True,
            )

        assert len(persist_call_args) > 0, (
            "run_system_plan() did NOT call _persist_entities() when Graphiti available - "
            "this indicates a stub implementation!"
        )

    async def test_persist_entities_actually_calls_graphiti_upsert(
        self,
        orchestrator_spec_path: Path,
        graphiti_mock_enabled: Mock,
        tmp_output_dir: Path,
    ):
        """
        _persist_entities() actually calls Graphiti client upsert methods.

        Verifies the persistence layer is not a stub by running the real
        _persist_entities function with a mock client and checking upserts.
        """
        from guardkit.planning.arch_spec_parser import parse_architecture_spec
        from guardkit.planning.system_plan import _persist_entities
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        # Parse the fixture
        spec = parse_architecture_spec(orchestrator_spec_path)

        # Create service with mock client
        service = SystemPlanGraphiti(
            client=graphiti_mock_enabled,
            project_id="test-project",
        )

        # Call the real _persist_entities
        counts = await _persist_entities(service, spec)

        # Verify upsert_episode was called
        assert graphiti_mock_enabled.upsert_episode.called, (
            "_persist_entities() did NOT call Graphiti upsert_episode - stub detected!"
        )
        assert len(graphiti_mock_enabled._upsert_calls) > 0

        # Verify counts match expected
        assert counts["system_contexts"] == 1
        assert counts["components"] == 2  # Core + Infra from fixture
        assert counts["concerns"] == 1    # Observability from fixture
        assert counts["decisions"] == 1   # ADR-SP-001 from fixture


# =============================================================================
# SEAM: run_system_plan() → _write_artefacts()
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestRunSystemPlanCallsWriteArtefacts:
    """
    Tests that run_system_plan() calls _write_artefacts().

    Verifies markdown artifacts are actually generated.
    """

    async def test_run_system_plan_calls_write_artefacts(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        run_system_plan() with context file calls _write_artefacts().

        Uses MagicMock to track calls while returning valid data.
        """
        from guardkit.planning.system_plan import run_system_plan

        # Create a mock that returns valid file list
        write_mock = MagicMock(return_value=[
            str(tmp_output_dir / "ARCHITECTURE.md"),
            str(tmp_output_dir / "system-context.md"),
        ])

        with patch(
            "guardkit.planning.system_plan._write_artefacts",
            write_mock,
        ), patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        assert write_mock.called, (
            "run_system_plan() did NOT call _write_artefacts() - stub detected!"
        )
        # Verify spec was passed (not None or empty)
        call_args = write_mock.call_args[0]
        assert call_args[0] is not None, "Spec passed to _write_artefacts was None"
        assert call_args[0].system_context is not None, "Spec has no system_context"

    async def test_write_artefacts_produces_actual_files(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        _write_artefacts() produces actual files in output directory.
        """
        from guardkit.planning.system_plan import run_system_plan

        with patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        # Verify files were created
        assert (tmp_output_dir / "ARCHITECTURE.md").exists(), (
            "ARCHITECTURE.md not created - _write_artefacts is a stub!"
        )
        assert (tmp_output_dir / "system-context.md").exists(), (
            "system-context.md not created - _write_artefacts is a stub!"
        )


# =============================================================================
# SEAM: Graceful Degradation (no Graphiti still writes artefacts)
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestGracefulDegradation:
    """
    Tests that run_system_plan() gracefully degrades when Graphiti unavailable.

    Verifies that markdown artifacts are still generated even when
    Graphiti persistence is skipped.
    """

    async def test_run_system_plan_without_graphiti_still_writes_artefacts(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        run_system_plan() without Graphiti still calls _write_artefacts().

        Uses MagicMock to track calls while returning valid data.
        """
        from guardkit.planning.system_plan import run_system_plan

        # Create a mock that returns valid file list
        write_mock = MagicMock(return_value=[
            str(tmp_output_dir / "ARCHITECTURE.md"),
            str(tmp_output_dir / "system-context.md"),
        ])

        with patch(
            "guardkit.planning.system_plan._write_artefacts",
            write_mock,
        ), patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,  # Graphiti completely unavailable
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=True,
            )

        assert write_mock.called, (
            "run_system_plan() did NOT call _write_artefacts() when Graphiti unavailable - "
            "graceful degradation broken!"
        )
        # Verify spec was passed (not None or empty)
        call_args = write_mock.call_args[0]
        assert call_args[0] is not None, "Spec passed to _write_artefacts was None"

    async def test_artefacts_produced_even_when_graphiti_disabled(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        Markdown artefacts are produced even when Graphiti is disabled.
        """
        from guardkit.planning.system_plan import run_system_plan

        with patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode=None,
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        # Verify files were created despite no Graphiti
        assert (tmp_output_dir / "ARCHITECTURE.md").exists()
        assert (tmp_output_dir / "system-context.md").exists()


# =============================================================================
# SEAM: run_impact_analysis() → Graphiti Context Retrieval
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestRunImpactAnalysisCallsGraphiti:
    """
    Tests that run_impact_analysis() calls Graphiti context retrieval.

    Verifies the impact analysis orchestrator actually queries Graphiti.
    """

    async def test_run_impact_analysis_calls_graphiti_search(
        self,
        graphiti_mock_enabled: Mock,
    ):
        """
        run_impact_analysis() calls Graphiti search for context retrieval.
        """
        from guardkit.planning.impact_analysis import run_impact_analysis
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        # Create SystemPlanGraphiti instance with mock client
        sp = SystemPlanGraphiti(
            client=graphiti_mock_enabled,
            project_id="test-project",
        )

        result = await run_impact_analysis(
            sp=sp,
            client=graphiti_mock_enabled,
            task_or_topic="test topic for impact analysis",
            depth="standard",
        )

        # Verify Graphiti search was called
        assert graphiti_mock_enabled.search.called, (
            "run_impact_analysis() did NOT call Graphiti search - stub detected!"
        )
        assert len(graphiti_mock_enabled._search_calls) > 0

    async def test_run_impact_analysis_searches_architecture_group(
        self,
        graphiti_mock_enabled: Mock,
    ):
        """
        run_impact_analysis() searches the project_architecture group.
        """
        from guardkit.planning.impact_analysis import run_impact_analysis
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        sp = SystemPlanGraphiti(
            client=graphiti_mock_enabled,
            project_id="test-project",
        )

        await run_impact_analysis(
            sp=sp,
            client=graphiti_mock_enabled,
            task_or_topic="order management impact",
            depth="standard",
        )

        # Verify get_group_id was called for architecture group
        group_id_calls = [
            str(c) for c in graphiti_mock_enabled.get_group_id.call_args_list
        ]
        assert any("project_architecture" in c for c in group_id_calls), (
            "run_impact_analysis() did NOT query project_architecture group!"
        )

    async def test_run_impact_analysis_returns_no_context_when_unavailable(
        self,
        graphiti_mock_disabled: Mock,
    ):
        """
        run_impact_analysis() returns no_context status when Graphiti unavailable.
        """
        from guardkit.planning.impact_analysis import run_impact_analysis
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        sp = SystemPlanGraphiti(
            client=graphiti_mock_disabled,
            project_id="test-project",
        )

        result = await run_impact_analysis(
            sp=sp,
            client=graphiti_mock_disabled,
            task_or_topic="test topic",
            depth="standard",
        )

        assert result.get("status") == "no_context", (
            "run_impact_analysis() should return no_context when Graphiti disabled"
        )


# =============================================================================
# SEAM: Feature Plan Integration → Context Builder
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestFeaturePlanCallsContextBuilder:
    """
    Tests that FeaturePlanIntegration calls context builder modules.

    Verifies that feature planning actually invokes the context builder
    for Graphiti context enrichment.
    """

    async def test_build_enriched_prompt_calls_context_builder(
        self,
        tmp_path: Path,
    ):
        """
        build_enriched_prompt() calls FeaturePlanContextBuilder.build_context().
        """
        from guardkit.commands.feature_plan_integration import FeaturePlanIntegration

        # Create mock context builder
        mock_context = MagicMock()
        mock_context.feature_spec = None
        mock_context.to_prompt_context.return_value = "Mock context"

        build_context_calls = []

        async def tracking_build_context(description, **kwargs):
            build_context_calls.append((description, kwargs))
            return mock_context

        integration = FeaturePlanIntegration(
            project_root=tmp_path,
            enable_context=True,
        )

        # Replace context builder's build_context with tracking version
        integration.context_builder.build_context = tracking_build_context

        result = await integration.build_enriched_prompt(
            description="Test feature description",
            tech_stack="python",
        )

        # Verify build_context was called
        assert len(build_context_calls) > 0, (
            "build_enriched_prompt() did NOT call context_builder.build_context() - stub detected!"
        )
        assert build_context_calls[0][0] == "Test feature description"

    async def test_feature_plan_disabled_context_still_returns_prompt(
        self,
        tmp_path: Path,
    ):
        """
        build_enriched_prompt() with disabled context returns valid prompt.
        """
        from guardkit.commands.feature_plan_integration import FeaturePlanIntegration

        integration = FeaturePlanIntegration(
            project_root=tmp_path,
            enable_context=False,  # Disabled
        )

        result = await integration.build_enriched_prompt(
            description="Test feature",
            tech_stack="python",
        )

        # Should return prompt without calling context builder
        assert "Test feature" in result
        assert isinstance(result, str)


# =============================================================================
# Integration: Full Orchestrator Pipeline
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestFullOrchestratorPipeline:
    """
    Integration tests for the full orchestrator pipeline.

    Verifies that all seams work together correctly.
    """

    async def test_full_system_plan_pipeline_with_graphiti(
        self,
        orchestrator_spec_path: Path,
        graphiti_mock_enabled: Mock,
        tmp_output_dir: Path,
    ):
        """
        Full run_system_plan() pipeline: parse → persist → write.

        Verifies all orchestrator wiring works end-to-end.
        """
        from guardkit.planning.system_plan import run_system_plan

        with patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=graphiti_mock_enabled,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode="setup",
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=True,
            )

        # Verify all seams were exercised
        # 1. Parse happened (files written means parse succeeded)
        assert (tmp_output_dir / "ARCHITECTURE.md").exists()

        # 2. Persist happened (upsert was called)
        assert graphiti_mock_enabled.upsert_episode.called
        assert len(graphiti_mock_enabled._upsert_calls) > 0

        # 3. Write happened (files exist)
        assert (tmp_output_dir / "system-context.md").exists()
        assert (tmp_output_dir / "components.md").exists()

    async def test_full_system_plan_pipeline_without_graphiti(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        Full run_system_plan() pipeline without Graphiti: parse → write.

        Verifies graceful degradation produces artifacts.
        """
        from guardkit.planning.system_plan import run_system_plan

        with patch(
            "guardkit.planning.system_plan._get_graphiti_client",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "guardkit.planning.system_plan._DEFAULT_OUTPUT_DIR",
            str(tmp_output_dir),
        ):
            await run_system_plan(
                description="Test System",
                mode="setup",
                focus="all",
                no_questions=False,
                defaults=False,
                context_file=str(orchestrator_spec_path),
                enable_context=False,
            )

        # Verify parse and write happened
        assert (tmp_output_dir / "ARCHITECTURE.md").exists()
        assert (tmp_output_dir / "system-context.md").exists()


# =============================================================================
# Anti-Stub Verification: Ensure Real Logic Executed
# =============================================================================


@pytest.mark.seam
@pytest.mark.asyncio
class TestAntiStubVerification:
    """
    Tests that verify orchestrator functions contain real logic, not stubs.

    These tests check that orchestrators produce meaningful output,
    not just return None or empty results.
    """

    async def test_parse_architecture_spec_returns_non_empty_result(
        self,
        orchestrator_spec_path: Path,
    ):
        """
        parse_architecture_spec() returns non-empty result from real fixture.
        """
        from guardkit.planning.arch_spec_parser import parse_architecture_spec

        result = parse_architecture_spec(orchestrator_spec_path)

        # Verify it's not a stub returning empty/None
        assert result is not None, "parse_architecture_spec returned None - stub!"
        assert result.system_context is not None, "No system_context - stub!"
        assert len(result.components) > 0, "No components parsed - stub!"

    async def test_architecture_writer_produces_content(
        self,
        orchestrator_spec_path: Path,
        tmp_output_dir: Path,
    ):
        """
        ArchitectureWriter produces files with actual content.
        """
        from guardkit.planning.arch_spec_parser import parse_architecture_spec
        from guardkit.planning.architecture_writer import ArchitectureWriter

        spec = parse_architecture_spec(orchestrator_spec_path)
        writer = ArchitectureWriter()

        writer.write_all(
            output_dir=tmp_output_dir,
            system=spec.system_context,
            components=spec.components,
            concerns=spec.concerns,
            decisions=spec.decisions,
        )

        # Verify files have content
        arch_md = tmp_output_dir / "ARCHITECTURE.md"
        assert arch_md.exists()
        content = arch_md.read_text()
        assert len(content) > 100, "ARCHITECTURE.md has no content - stub writer!"
        assert "Test System" in content, "System name not in output - stub writer!"

    async def test_persist_entities_calls_correct_upsert_methods(
        self,
        orchestrator_spec_path: Path,
        graphiti_mock_enabled: Mock,
    ):
        """
        _persist_entities() calls upsert methods for all entity types.
        """
        from guardkit.planning.arch_spec_parser import parse_architecture_spec
        from guardkit.planning.system_plan import _persist_entities
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        spec = parse_architecture_spec(orchestrator_spec_path)

        service = SystemPlanGraphiti(
            client=graphiti_mock_enabled,
            project_id="test-project",
        )

        counts = await _persist_entities(service, spec)

        # Verify counts are non-zero for entities in fixture
        assert counts["system_contexts"] > 0, "No system context persisted - stub!"
        assert counts["components"] > 0, "No components persisted - stub!"
        assert graphiti_mock_enabled.upsert_episode.call_count >= 2, (
            "Too few upsert calls - stub implementation!"
        )
