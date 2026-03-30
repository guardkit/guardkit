"""Tests for human-in-the-loop checkpoint hooks.

Validates CheckpointHook base class, CLICheckpointHook, WebhookCheckpointHook,
AutoApproveHook, CheckpointConfig, and the create_checkpoint_hook factory.

Coverage Target: >=85%
Test Count: 35+ tests
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the module from the template's lib directory
# ---------------------------------------------------------------------------
_LIB_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "checkpoint_hooks.py"
)


@pytest.fixture(scope="module")
def hooks_mod():
    """Load the checkpoint_hooks module directly from source."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("checkpoint_hooks", str(_LIB_PATH))
    spec = importlib.util.spec_from_loader("checkpoint_hooks", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["checkpoint_hooks"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture
def CheckpointStage(hooks_mod):
    return hooks_mod.CheckpointStage


@pytest.fixture
def CheckpointDecision(hooks_mod):
    return hooks_mod.CheckpointDecision


@pytest.fixture
def CheckpointContext(hooks_mod):
    return hooks_mod.CheckpointContext


@pytest.fixture
def CheckpointConfig(hooks_mod):
    return hooks_mod.CheckpointConfig


@pytest.fixture
def CheckpointHook(hooks_mod):
    return hooks_mod.CheckpointHook


@pytest.fixture
def CLICheckpointHook(hooks_mod):
    return hooks_mod.CLICheckpointHook


@pytest.fixture
def WebhookCheckpointHook(hooks_mod):
    return hooks_mod.WebhookCheckpointHook


@pytest.fixture
def AutoApproveHook(hooks_mod):
    return hooks_mod.AutoApproveHook


@pytest.fixture
def create_checkpoint_hook(hooks_mod):
    return hooks_mod.create_checkpoint_hook


@pytest.fixture
def sample_context(CheckpointContext, CheckpointStage):
    """Create a sample checkpoint context for testing."""
    return CheckpointContext(
        stage=CheckpointStage.POST_EVALUATION,
        target="test-target-001",
        attempt=2,
        max_retries=3,
        player_output='{"title": "Test", "body": "Content"}',
        coach_verdict={"decision": "reject", "score": 2, "issues": ["too short"]},
        metadata={"domain": "example"},
    )


# ===================================================================
# CheckpointStage Tests
# ===================================================================


class TestCheckpointStage:
    """Tests for the CheckpointStage enum."""

    def test_has_five_stages(self, CheckpointStage):
        assert len(CheckpointStage) == 5

    def test_pre_generation_value(self, CheckpointStage):
        assert CheckpointStage.PRE_GENERATION.value == "pre-generation"

    def test_post_generation_value(self, CheckpointStage):
        assert CheckpointStage.POST_GENERATION.value == "post-generation"

    def test_post_evaluation_value(self, CheckpointStage):
        assert CheckpointStage.POST_EVALUATION.value == "post-evaluation"

    def test_on_rejection_value(self, CheckpointStage):
        assert CheckpointStage.ON_REJECTION.value == "on-rejection"

    def test_on_exhaustion_value(self, CheckpointStage):
        assert CheckpointStage.ON_EXHAUSTION.value == "on-exhaustion"

    def test_stages_are_strings(self, CheckpointStage):
        for stage in CheckpointStage:
            assert isinstance(stage.value, str)


# ===================================================================
# CheckpointDecision Tests
# ===================================================================


class TestCheckpointDecision:
    """Tests for the CheckpointDecision enum."""

    def test_has_four_decisions(self, CheckpointDecision):
        assert len(CheckpointDecision) == 4

    def test_proceed_value(self, CheckpointDecision):
        assert CheckpointDecision.PROCEED.value == "proceed"

    def test_skip_value(self, CheckpointDecision):
        assert CheckpointDecision.SKIP.value == "skip"

    def test_override_value(self, CheckpointDecision):
        assert CheckpointDecision.OVERRIDE.value == "override"

    def test_abort_value(self, CheckpointDecision):
        assert CheckpointDecision.ABORT.value == "abort"

    def test_decisions_are_strings(self, CheckpointDecision):
        for decision in CheckpointDecision:
            assert isinstance(decision.value, str)

    def test_can_construct_from_string(self, CheckpointDecision):
        assert CheckpointDecision("proceed") == CheckpointDecision.PROCEED
        assert CheckpointDecision("abort") == CheckpointDecision.ABORT


# ===================================================================
# CheckpointContext Tests
# ===================================================================


class TestCheckpointContext:
    """Tests for the CheckpointContext dataclass."""

    def test_required_fields(self, CheckpointContext, CheckpointStage):
        ctx = CheckpointContext(
            stage=CheckpointStage.PRE_GENERATION,
            target="target-1",
        )
        assert ctx.stage == CheckpointStage.PRE_GENERATION
        assert ctx.target == "target-1"

    def test_default_values(self, CheckpointContext, CheckpointStage):
        ctx = CheckpointContext(
            stage=CheckpointStage.PRE_GENERATION,
            target="target-1",
        )
        assert ctx.attempt == 1
        assert ctx.max_retries == 3
        assert ctx.player_output is None
        assert ctx.coach_verdict is None
        assert ctx.metadata == {}

    def test_all_fields_populated(self, sample_context, CheckpointStage):
        assert sample_context.stage == CheckpointStage.POST_EVALUATION
        assert sample_context.target == "test-target-001"
        assert sample_context.attempt == 2
        assert sample_context.max_retries == 3
        assert sample_context.player_output is not None
        assert sample_context.coach_verdict is not None
        assert sample_context.metadata == {"domain": "example"}

    def test_metadata_default_is_independent(self, CheckpointContext, CheckpointStage):
        """Ensure default metadata dict is not shared between instances."""
        ctx1 = CheckpointContext(stage=CheckpointStage.PRE_GENERATION, target="a")
        ctx2 = CheckpointContext(stage=CheckpointStage.PRE_GENERATION, target="b")
        ctx1.metadata["key"] = "value"
        assert "key" not in ctx2.metadata


# ===================================================================
# CheckpointConfig Tests
# ===================================================================


class TestCheckpointConfig:
    """Tests for the CheckpointConfig dataclass."""

    def test_defaults(self, CheckpointConfig):
        cfg = CheckpointConfig()
        assert cfg.enabled is True
        assert cfg.mode == "auto"
        assert cfg.stages == ["post-evaluation"]
        assert cfg.webhook_url is None
        assert cfg.webhook_timeout == 300.0

    def test_is_stage_enabled_when_in_list(self, CheckpointConfig, CheckpointStage):
        cfg = CheckpointConfig(stages=["post-evaluation", "on-rejection"])
        assert cfg.is_stage_enabled(CheckpointStage.POST_EVALUATION) is True
        assert cfg.is_stage_enabled(CheckpointStage.ON_REJECTION) is True

    def test_is_stage_disabled_when_not_in_list(self, CheckpointConfig, CheckpointStage):
        cfg = CheckpointConfig(stages=["post-evaluation"])
        assert cfg.is_stage_enabled(CheckpointStage.PRE_GENERATION) is False

    def test_is_stage_disabled_when_checkpoints_disabled(
        self, CheckpointConfig, CheckpointStage
    ):
        cfg = CheckpointConfig(enabled=False, stages=["post-evaluation"])
        assert cfg.is_stage_enabled(CheckpointStage.POST_EVALUATION) is False

    def test_stages_default_is_independent(self, CheckpointConfig):
        cfg1 = CheckpointConfig()
        cfg2 = CheckpointConfig()
        cfg1.stages.append("on-rejection")
        assert "on-rejection" not in cfg2.stages


# ===================================================================
# CheckpointHook (Base) Tests
# ===================================================================


class TestCheckpointHookBase:
    """Tests for the base CheckpointHook class."""

    def test_default_returns_proceed(self, CheckpointHook, CheckpointDecision, sample_context):
        hook = CheckpointHook()
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.PROCEED

    def test_is_subclassable(self, CheckpointHook, CheckpointDecision):
        class CustomHook(CheckpointHook):
            async def on_checkpoint(self, stage, context):
                return CheckpointDecision.ABORT

        hook = CustomHook()
        result = asyncio.run(
            hook.on_checkpoint("any", MagicMock())
        )
        assert result == CheckpointDecision.ABORT


# ===================================================================
# CLICheckpointHook Tests
# ===================================================================


class TestCLICheckpointHook:
    """Tests for the interactive CLI checkpoint hook."""

    def test_proceed_decision(self, CLICheckpointHook, CheckpointDecision, sample_context):
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.PROCEED

    def test_skip_decision(self, CLICheckpointHook, CheckpointDecision, sample_context):
        hook = CLICheckpointHook(input_fn=lambda _: "s")
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.SKIP

    def test_override_decision(self, CLICheckpointHook, CheckpointDecision, sample_context):
        hook = CLICheckpointHook(input_fn=lambda _: "o")
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.OVERRIDE

    def test_abort_decision(self, CLICheckpointHook, CheckpointDecision, sample_context):
        hook = CLICheckpointHook(input_fn=lambda _: "a")
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.ABORT

    def test_override_not_available_at_pre_generation(
        self, CLICheckpointHook, CheckpointDecision, CheckpointContext, CheckpointStage
    ):
        """Override is not valid at pre-generation; retries until valid input."""
        inputs = iter(["o", "p"])
        hook = CLICheckpointHook(input_fn=lambda _: next(inputs))
        ctx = CheckpointContext(stage=CheckpointStage.PRE_GENERATION, target="t1")
        result = asyncio.run(
            hook.on_checkpoint("pre-generation", ctx)
        )
        assert result == CheckpointDecision.PROCEED

    def test_invalid_input_retries(
        self, CLICheckpointHook, CheckpointDecision, sample_context
    ):
        """Invalid input followed by valid input."""
        inputs = iter(["x", "z", "p"])
        hook = CLICheckpointHook(input_fn=lambda _: next(inputs))
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.PROCEED

    def test_eof_returns_abort(
        self, CLICheckpointHook, CheckpointDecision, sample_context
    ):
        """EOFError (e.g. piped input) returns ABORT."""

        def raise_eof(_):
            raise EOFError

        hook = CLICheckpointHook(input_fn=raise_eof)
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.ABORT

    def test_keyboard_interrupt_returns_abort(
        self, CLICheckpointHook, CheckpointDecision, sample_context
    ):
        def raise_interrupt(_):
            raise KeyboardInterrupt

        hook = CLICheckpointHook(input_fn=raise_interrupt)
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.ABORT

    def test_displays_player_output_preview(
        self, CLICheckpointHook, sample_context, capsys
    ):
        """Verify player output is shown (truncated if long)."""
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        captured = capsys.readouterr()
        assert "Player output:" in captured.out
        assert "Test" in captured.out

    def test_displays_coach_verdict(
        self, CLICheckpointHook, sample_context, capsys
    ):
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        captured = capsys.readouterr()
        assert "Coach verdict:" in captured.out
        assert "reject" in captured.out

    def test_displays_metadata(
        self, CLICheckpointHook, sample_context, capsys
    ):
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        captured = capsys.readouterr()
        assert "domain: example" in captured.out

    def test_long_player_output_truncated(
        self, CLICheckpointHook, CheckpointContext, CheckpointStage, capsys
    ):
        ctx = CheckpointContext(
            stage=CheckpointStage.POST_GENERATION,
            target="t1",
            player_output="x" * 500,
        )
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        asyncio.run(
            hook.on_checkpoint("post-generation", ctx)
        )
        captured = capsys.readouterr()
        assert "..." in captured.out

    def test_on_exhaustion_allows_proceed(
        self, CLICheckpointHook, CheckpointDecision, CheckpointContext, CheckpointStage
    ):
        """On exhaustion, PROCEED means extend retries."""
        hook = CLICheckpointHook(input_fn=lambda _: "p")
        ctx = CheckpointContext(
            stage=CheckpointStage.ON_EXHAUSTION,
            target="t1",
            attempt=3,
            max_retries=3,
        )
        result = asyncio.run(
            hook.on_checkpoint("on-exhaustion", ctx)
        )
        assert result == CheckpointDecision.PROCEED


# ===================================================================
# WebhookCheckpointHook Tests
# ===================================================================


class TestWebhookCheckpointHook:
    """Tests for the webhook checkpoint hook."""

    def test_sends_correct_payload(self, WebhookCheckpointHook, sample_context):
        """Verify the webhook receives the correct JSON payload."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"decision": "proceed"})

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        # Verify the post was called with correct URL
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args
        assert call_kwargs[0][0] == "https://example.com/hook"
        payload = call_kwargs[1]["json"]
        assert payload["stage"] == "post-evaluation"
        assert payload["target"] == "test-target-001"

    def test_parses_skip_response(self, WebhookCheckpointHook, CheckpointDecision, sample_context):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"decision": "skip"})

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.SKIP

    def test_non_200_defaults_to_proceed(
        self, WebhookCheckpointHook, CheckpointDecision, sample_context
    ):
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.PROCEED

    def test_invalid_decision_defaults_to_proceed(
        self, WebhookCheckpointHook, CheckpointDecision, sample_context
    ):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"decision": "invalid_value"})

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.PROCEED

    def test_timeout_defaults_to_proceed(
        self, WebhookCheckpointHook, CheckpointDecision, sample_context
    ):
        import asyncio as _asyncio

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=_asyncio.TimeoutError())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()
        mock_aiohttp.TimeoutError = _asyncio.TimeoutError  # not needed but consistent

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook", timeout=1.0)
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.PROCEED

    def test_connection_error_defaults_to_proceed(
        self, WebhookCheckpointHook, CheckpointDecision, sample_context
    ):
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=ConnectionError("refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.PROCEED

    def test_missing_aiohttp_defaults_to_proceed(
        self, WebhookCheckpointHook, CheckpointDecision, sample_context
    ):
        """When aiohttp is not installed, gracefully default to PROCEED."""
        # Remove aiohttp from sys.modules if present
        with patch.dict("sys.modules", {"aiohttp": None}):
            hook = WebhookCheckpointHook(url="https://example.com/hook")
            result = asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        assert result == CheckpointDecision.PROCEED

    def test_custom_headers_passed(self, WebhookCheckpointHook, sample_context):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"decision": "proceed"})

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_aiohttp = MagicMock()
        mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = MagicMock()

        headers = {"Authorization": "Bearer token123"}

        with patch.dict("sys.modules", {"aiohttp": mock_aiohttp}):
            hook = WebhookCheckpointHook(
                url="https://example.com/hook", headers=headers
            )
            asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )

        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["headers"] == {"Authorization": "Bearer token123"}


# ===================================================================
# AutoApproveHook Tests
# ===================================================================


class TestAutoApproveHook:
    """Tests for the auto-approve checkpoint hook."""

    def test_always_returns_proceed(
        self, AutoApproveHook, CheckpointDecision, sample_context
    ):
        hook = AutoApproveHook()
        result = asyncio.run(
            hook.on_checkpoint("post-evaluation", sample_context)
        )
        assert result == CheckpointDecision.PROCEED

    def test_returns_proceed_for_all_stages(
        self, AutoApproveHook, CheckpointDecision, CheckpointStage, CheckpointContext
    ):
        hook = AutoApproveHook()
        for stage in CheckpointStage:
            ctx = CheckpointContext(stage=stage, target="t1")
            result = asyncio.run(
                hook.on_checkpoint(stage.value, ctx)
            )
            assert result == CheckpointDecision.PROCEED

    def test_logging_disabled_by_default(
        self, AutoApproveHook, sample_context, caplog
    ):
        hook = AutoApproveHook()
        with caplog.at_level(logging.INFO, logger="deepagents.checkpoint"):
            asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )
        assert "Auto-approved" not in caplog.text

    def test_logging_enabled_when_configured(
        self, AutoApproveHook, sample_context, caplog
    ):
        hook = AutoApproveHook(log_checkpoints=True)
        with caplog.at_level(logging.INFO, logger="deepagents.checkpoint"):
            asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )
        assert "Auto-approved" in caplog.text
        assert "post-evaluation" in caplog.text
        assert "test-target-001" in caplog.text


# ===================================================================
# create_checkpoint_hook Factory Tests
# ===================================================================


class TestCreateCheckpointHook:
    """Tests for the checkpoint hook factory function."""

    def test_disabled_returns_auto_approve(
        self, create_checkpoint_hook, CheckpointConfig, AutoApproveHook
    ):
        cfg = CheckpointConfig(enabled=False)
        hook = create_checkpoint_hook(cfg)
        assert isinstance(hook, AutoApproveHook)

    def test_auto_mode_returns_auto_approve(
        self, create_checkpoint_hook, CheckpointConfig, AutoApproveHook
    ):
        cfg = CheckpointConfig(mode="auto")
        hook = create_checkpoint_hook(cfg)
        assert isinstance(hook, AutoApproveHook)

    def test_cli_mode_returns_cli_hook(
        self, create_checkpoint_hook, CheckpointConfig, CLICheckpointHook
    ):
        cfg = CheckpointConfig(mode="cli")
        hook = create_checkpoint_hook(cfg)
        assert isinstance(hook, CLICheckpointHook)

    def test_webhook_mode_returns_webhook_hook(
        self, create_checkpoint_hook, CheckpointConfig, WebhookCheckpointHook
    ):
        cfg = CheckpointConfig(mode="webhook", webhook_url="https://example.com/hook")
        hook = create_checkpoint_hook(cfg)
        assert isinstance(hook, WebhookCheckpointHook)

    def test_webhook_mode_without_url_raises(
        self, create_checkpoint_hook, CheckpointConfig
    ):
        cfg = CheckpointConfig(mode="webhook", webhook_url=None)
        with pytest.raises(ValueError, match="webhook_url is required"):
            create_checkpoint_hook(cfg)

    def test_unknown_mode_raises(self, create_checkpoint_hook, CheckpointConfig):
        cfg = CheckpointConfig(mode="unknown")
        with pytest.raises(ValueError, match="Unknown checkpoint mode"):
            create_checkpoint_hook(cfg)

    def test_auto_mode_enables_logging(
        self, create_checkpoint_hook, CheckpointConfig, sample_context, caplog
    ):
        """Auto mode should log checkpoints for audit trail."""
        cfg = CheckpointConfig(mode="auto")
        hook = create_checkpoint_hook(cfg)
        with caplog.at_level(logging.INFO, logger="deepagents.checkpoint"):
            asyncio.run(
                hook.on_checkpoint("post-evaluation", sample_context)
            )
        assert "Auto-approved" in caplog.text
