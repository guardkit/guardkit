"""
Unit tests for system-plan mode detection logic.

Tests mode auto-detection based on Graphiti architecture context.
These are TDD RED phase tests - they will fail until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_graphiti_enabled():
    """Mock Graphiti client that is enabled."""
    mock = MagicMock()
    mock.enabled = True
    return mock


@pytest.fixture
def mock_graphiti_disabled():
    """Mock Graphiti client that is disabled."""
    mock = MagicMock()
    mock.enabled = False
    return mock


class TestModeDetectorExistence:
    """Test that mode detector module and function exist."""

    def test_module_exists(self):
        """Test that mode_detector module can be imported."""
        # This will fail until we create guardkit/planning/mode_detector.py
        from guardkit.planning import mode_detector

        assert mode_detector is not None

    def test_detect_mode_function_exists(self):
        """Test that detect_mode function exists."""
        from guardkit.planning.mode_detector import detect_mode

        assert callable(detect_mode)


class TestModeDetectorWithoutGraphiti:
    """Test mode detection when Graphiti is not available."""

    @pytest.mark.asyncio
    async def test_returns_setup_when_graphiti_none(self):
        """Test that detect_mode returns 'setup' when Graphiti client is None."""
        from guardkit.planning.mode_detector import detect_mode

        result = await detect_mode(graphiti_client=None)
        assert result == "setup"

    @pytest.mark.asyncio
    async def test_returns_setup_when_graphiti_disabled(self, mock_graphiti_disabled):
        """Test that detect_mode returns 'setup' when Graphiti is disabled."""
        from guardkit.planning.mode_detector import detect_mode

        result = await detect_mode(graphiti_client=mock_graphiti_disabled)
        assert result == "setup"

    @pytest.mark.asyncio
    async def test_logs_graceful_degradation(self, mock_graphiti_disabled, caplog):
        """Test that graceful degradation is logged."""
        from guardkit.planning.mode_detector import detect_mode

        with caplog.at_level("INFO"):
            await detect_mode(graphiti_client=mock_graphiti_disabled)

        # Should log that falling back to setup mode
        assert any(
            "setup" in record.message.lower() and "fallback" in record.message.lower()
            for record in caplog.records
        )


class TestModeDetectorWithGraphiti:
    """Test mode detection when Graphiti is available."""

    @pytest.mark.asyncio
    async def test_returns_setup_when_no_architecture_context(self, mock_graphiti_enabled):
        """Test returns 'setup' when has_architecture_context returns False."""
        from guardkit.planning.mode_detector import detect_mode

        # Mock SystemPlanGraphiti.has_architecture_context to return False
        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            result = await detect_mode(
                graphiti_client=mock_graphiti_enabled,
                project_id="test-project"
            )

            assert result == "setup"
            mock_instance.has_architecture_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_refine_when_architecture_exists(self, mock_graphiti_enabled):
        """Test returns 'refine' when has_architecture_context returns True."""
        from guardkit.planning.mode_detector import detect_mode

        # Mock SystemPlanGraphiti.has_architecture_context to return True
        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=True)
            MockGraphiti.return_value = mock_instance

            result = await detect_mode(
                graphiti_client=mock_graphiti_enabled,
                project_id="test-project"
            )

            assert result == "refine"
            mock_instance.has_architecture_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_system_plan_graphiti_with_correct_params(self, mock_graphiti_enabled):
        """Test that SystemPlanGraphiti is created with correct parameters."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            await detect_mode(
                graphiti_client=mock_graphiti_enabled,
                project_id="my-project"
            )

            # Should create SystemPlanGraphiti with client and project_id
            MockGraphiti.assert_called_once_with(
                client=mock_graphiti_enabled,
                project_id="my-project"
            )


class TestModeDetectorErrorHandling:
    """Test graceful error handling in mode detection."""

    @pytest.mark.asyncio
    async def test_returns_setup_on_graphiti_error(self, mock_graphiti_enabled):
        """Test returns 'setup' when Graphiti operations fail."""
        from guardkit.planning.mode_detector import detect_mode

        # Mock has_architecture_context to raise exception
        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(
                side_effect=Exception("Graphiti connection error")
            )
            MockGraphiti.return_value = mock_instance

            result = await detect_mode(
                graphiti_client=mock_graphiti_enabled,
                project_id="test-project"
            )

            # Should fall back to setup mode
            assert result == "setup"

    @pytest.mark.asyncio
    async def test_logs_graphiti_error(self, mock_graphiti_enabled, caplog):
        """Test that Graphiti errors are logged."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(
                side_effect=Exception("Connection timeout")
            )
            MockGraphiti.return_value = mock_instance

            with caplog.at_level("WARNING"):
                await detect_mode(
                    graphiti_client=mock_graphiti_enabled,
                    project_id="test-project"
                )

            # Should log the error
            assert any(
                "error" in record.message.lower() or "failed" in record.message.lower()
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_warns_user_about_fallback(self, mock_graphiti_enabled, caplog):
        """Test that user is warned about fallback to setup mode."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(
                side_effect=Exception("Network error")
            )
            MockGraphiti.return_value = mock_instance

            with caplog.at_level("INFO"):
                await detect_mode(
                    graphiti_client=mock_graphiti_enabled,
                    project_id="test-project"
                )

            # Should warn about falling back to setup
            log_messages = [record.message.lower() for record in caplog.records]
            assert any("setup" in msg and "fallback" in msg for msg in log_messages)


class TestModeDetectorDefaultProjectId:
    """Test handling of project_id parameter."""

    @pytest.mark.asyncio
    async def test_uses_default_project_id_if_not_provided(self, mock_graphiti_enabled):
        """Test that a default project_id is used if not provided."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            # Call without project_id
            await detect_mode(graphiti_client=mock_graphiti_enabled)

            # Should still create SystemPlanGraphiti with some project_id
            MockGraphiti.assert_called_once()
            call_kwargs = MockGraphiti.call_args[1]
            assert "project_id" in call_kwargs
            assert call_kwargs["project_id"] is not None

    @pytest.mark.asyncio
    async def test_uses_provided_project_id(self, mock_graphiti_enabled):
        """Test that provided project_id is used."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            await detect_mode(
                graphiti_client=mock_graphiti_enabled,
                project_id="custom-project"
            )

            # Should use the provided project_id
            MockGraphiti.assert_called_once_with(
                client=mock_graphiti_enabled,
                project_id="custom-project"
            )


class TestModeDetectorLogging:
    """Test logging behavior of mode detector."""

    @pytest.mark.asyncio
    async def test_logs_detected_mode_setup(self, mock_graphiti_enabled, caplog):
        """Test that detected mode 'setup' is logged."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            with caplog.at_level("INFO"):
                result = await detect_mode(
                    graphiti_client=mock_graphiti_enabled,
                    project_id="test"
                )

            # Should log the detected mode
            assert any(
                "setup" in record.message.lower() and "mode" in record.message.lower()
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_logs_detected_mode_refine(self, mock_graphiti_enabled, caplog):
        """Test that detected mode 'refine' is logged."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=True)
            MockGraphiti.return_value = mock_instance

            with caplog.at_level("INFO"):
                result = await detect_mode(
                    graphiti_client=mock_graphiti_enabled,
                    project_id="test"
                )

            # Should log the detected mode
            assert any(
                "refine" in record.message.lower() and "mode" in record.message.lower()
                for record in caplog.records
            )


class TestModeDetectorReturnType:
    """Test return type and values of detect_mode."""

    @pytest.mark.asyncio
    async def test_returns_string(self, mock_graphiti_enabled):
        """Test that detect_mode returns a string."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()
            mock_instance.has_architecture_context = AsyncMock(return_value=False)
            MockGraphiti.return_value = mock_instance

            result = await detect_mode(graphiti_client=mock_graphiti_enabled)

            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_only_returns_valid_modes(self, mock_graphiti_enabled):
        """Test that detect_mode only returns valid mode values."""
        from guardkit.planning.mode_detector import detect_mode

        with patch("guardkit.planning.mode_detector.SystemPlanGraphiti") as MockGraphiti:
            mock_instance = MagicMock()

            # Test both cases
            valid_modes = {"setup", "refine"}

            for has_context in [True, False]:
                mock_instance.has_architecture_context = AsyncMock(return_value=has_context)
                MockGraphiti.return_value = mock_instance

                result = await detect_mode(graphiti_client=mock_graphiti_enabled)

                assert result in valid_modes
