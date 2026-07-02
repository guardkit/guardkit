"""
Tests for the system-plan mode detector.

Architecture-context lookup (the knowledge-graph "refine" path) was retired in
the fleet-memory cutover (FEAT-MEM-09). detect_mode now degrades to "setup".
"""

import pytest


class TestModeDetectorImport:
    def test_module_can_be_imported(self):
        from guardkit.planning import mode_detector

        assert mode_detector is not None

    def test_detect_mode_function_exists(self):
        from guardkit.planning.mode_detector import detect_mode

        assert callable(detect_mode)


class TestModeDetectorDegradesToSetup:
    @pytest.mark.asyncio
    async def test_returns_setup_when_client_none(self):
        from guardkit.planning.mode_detector import detect_mode

        assert await detect_mode(graphiti_client=None) == "setup"

    @pytest.mark.asyncio
    async def test_returns_setup_with_no_args(self):
        from guardkit.planning.mode_detector import detect_mode

        assert await detect_mode() == "setup"

    @pytest.mark.asyncio
    async def test_returns_setup_ignores_any_client(self):
        from guardkit.planning.mode_detector import detect_mode

        # Any client argument is ignored post-cutover.
        sentinel = object()
        assert await detect_mode(graphiti_client=sentinel, project_id="proj") == "setup"


class TestModeDetectorDefaultProjectId:
    @pytest.mark.asyncio
    async def test_uses_default_project_id_if_not_provided(self):
        from guardkit.planning.mode_detector import detect_mode

        # Should not raise when project_id is omitted (defaults to cwd name).
        assert await detect_mode() == "setup"

    @pytest.mark.asyncio
    async def test_uses_provided_project_id(self):
        from guardkit.planning.mode_detector import detect_mode

        assert await detect_mode(project_id="my-project") == "setup"


class TestModeDetectorReturnType:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        from guardkit.planning.mode_detector import detect_mode

        result = await detect_mode()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_only_returns_valid_modes(self):
        from guardkit.planning.mode_detector import detect_mode

        assert await detect_mode() in {"setup", "refine"}
