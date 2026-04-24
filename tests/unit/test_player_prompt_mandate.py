"""
Unit tests for TASK-FIX-7A08: Player execution-protocol prompts must mandate
`Task(subagent_type=...)` invocation for Phase 3, Phase 4, and Phase 5.

Covers AC:
- "All three execution-protocol prompts ... mandate Task(subagent_type=<specialist>)
   for Phase 3, Phase 4, and Phase 5, sourced from phase_specialists.py"
- "Inline bash commands for tests (pytest tests/ -v, npm test, etc.) are
   replaced by prose directing the Player to invoke test-orchestrator via Task"
- "_build_inline_implement_protocol in guardkit/orchestrator/agent_invoker.py
   is updated so rendered prompts include the mandate language regardless of
   which template backs them"
- "For every non-direct task-type profile, the rendered prompt contains the
   literal substrings subagent_type=\"test-orchestrator\" and
   subagent_type=\"code-reviewer\""

Coverage target: >=85% on changed lines.
Test count: 18 tests across 4 test classes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.phase_specialists import (
    GENERIC_PHASE_3_FALLBACK,
    STACK_TO_PHASE_3_SPECIALIST,
    STATIC_PHASE_SPECIALISTS,
)
from guardkit.orchestrator.prompts import clear_cache, load_protocol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear protocol cache before each test so file edits are seen."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def worktree_no_stack(tmp_path):
    """Worktree without .claude/settings.json → detect_stack_template returns None."""
    worktree = tmp_path / "worktrees" / "TASK-TEST"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def worktree_fastapi(tmp_path):
    """Worktree with .claude/settings.json pointing at fastapi-python."""
    worktree = tmp_path / "worktrees" / "TASK-TEST-FASTAPI"
    worktree.mkdir(parents=True)
    settings_dir = worktree / ".claude"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text(
        '{"project": {"template": "fastapi-python"}}'
    )
    return worktree


@pytest.fixture
def invoker_full(worktree_no_stack):
    """Invoker that loads the full protocol (timeout_multiplier <= 1.0)."""
    inv = AgentInvoker(worktree_path=worktree_no_stack)
    inv.timeout_multiplier = 1.0
    return inv


@pytest.fixture
def invoker_medium(worktree_no_stack):
    """Invoker that loads the medium protocol (timeout_multiplier > 1.0)."""
    inv = AgentInvoker(worktree_path=worktree_no_stack)
    inv.timeout_multiplier = 2.0
    return inv


@pytest.fixture
def invoker_fastapi(worktree_fastapi):
    """Invoker with fastapi-python stack template → python-api-specialist Phase-3."""
    inv = AgentInvoker(worktree_path=worktree_fastapi)
    inv.timeout_multiplier = 1.0
    return inv


# ---------------------------------------------------------------------------
# 1. Protocol .md files — mandate language and placeholder presence
# ---------------------------------------------------------------------------


class TestProtocolFileMandate:
    """The three .md protocol templates must contain the mandate language
    and the specialist placeholders they expect the loader to substitute."""

    PROTOCOL_NAMES = [
        "autobuild_execution_protocol",
        "autobuild_execution_protocol_medium",
        "autobuild_execution_protocol_slim",
    ]

    @pytest.mark.parametrize("protocol_name", PROTOCOL_NAMES)
    def test_protocol_has_phase_3_placeholder(self, protocol_name):
        """Phase 3 must delegate via {phase_3_specialist} placeholder."""
        content = load_protocol(protocol_name)
        assert "{phase_3_specialist}" in content, (
            f"{protocol_name}.md is missing {{phase_3_specialist}} placeholder — "
            "the Phase-3 specialist must be sourced from phase_specialists.py "
            "via placeholder substitution, not hardcoded."
        )

    @pytest.mark.parametrize("protocol_name", PROTOCOL_NAMES)
    def test_protocol_has_phase_4_placeholder(self, protocol_name):
        """Phase 4 must delegate via {phase_4_specialist} placeholder."""
        content = load_protocol(protocol_name)
        assert "{phase_4_specialist}" in content, (
            f"{protocol_name}.md is missing {{phase_4_specialist}} placeholder."
        )

    @pytest.mark.parametrize("protocol_name", PROTOCOL_NAMES)
    def test_protocol_has_phase_5_placeholder(self, protocol_name):
        """Phase 5 must delegate via {phase_5_specialist} placeholder."""
        content = load_protocol(protocol_name)
        assert "{phase_5_specialist}" in content, (
            f"{protocol_name}.md is missing {{phase_5_specialist}} placeholder."
        )

    @pytest.mark.parametrize("protocol_name", PROTOCOL_NAMES)
    def test_protocol_has_task_tool_mandate(self, protocol_name):
        """Each protocol must include the Task(subagent_type=…) pattern."""
        content = load_protocol(protocol_name)
        # The mandate uses `Task(subagent_type="…"` in the example code block.
        assert 'subagent_type="{phase_3_specialist}"' in content
        assert 'subagent_type="{phase_4_specialist}"' in content
        assert 'subagent_type="{phase_5_specialist}"' in content

    @pytest.mark.parametrize("protocol_name", PROTOCOL_NAMES)
    def test_protocol_removes_inline_pytest_command(self, protocol_name):
        """Inline `pytest tests/ -v` invocations must be gone (the defect)."""
        content = load_protocol(protocol_name)
        assert "pytest tests/ -v" not in content, (
            f"{protocol_name}.md still contains an inline `pytest tests/ -v` "
            "invocation — Phase 4 must delegate to test-orchestrator, not "
            "invite inline execution."
        )


# ---------------------------------------------------------------------------
# 2. Loader path (_build_autobuild_implementation_prompt) — substitution
# ---------------------------------------------------------------------------


class TestLoaderPathSubstitutesSpecialists:
    """The production prompt loader must substitute every placeholder using
    phase_specialists.py constants so the rendered prompt contains literal
    `subagent_type="test-orchestrator"` and `subagent_type="code-reviewer"`
    strings."""

    def test_full_protocol_substitutes_phase_4_specialist(self, invoker_full):
        prompt = invoker_full._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert f'subagent_type="{STATIC_PHASE_SPECIALISTS["4"]}"' in prompt
        assert 'subagent_type="test-orchestrator"' in prompt  # literal AC

    def test_full_protocol_substitutes_phase_5_specialist(self, invoker_full):
        prompt = invoker_full._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert f'subagent_type="{STATIC_PHASE_SPECIALISTS["5"]}"' in prompt
        assert 'subagent_type="code-reviewer"' in prompt  # literal AC

    def test_medium_protocol_substitutes_phase_4_specialist(self, invoker_medium):
        prompt = invoker_medium._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert 'subagent_type="test-orchestrator"' in prompt

    def test_medium_protocol_substitutes_phase_5_specialist(self, invoker_medium):
        prompt = invoker_medium._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert 'subagent_type="code-reviewer"' in prompt

    def test_no_unresolved_specialist_placeholder(self, invoker_full):
        """No `{phase_N_specialist}` literal may survive into the rendered prompt."""
        prompt = invoker_full._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert "{phase_3_specialist}" not in prompt
        assert "{phase_4_specialist}" not in prompt
        assert "{phase_5_specialist}" not in prompt

    def test_phase_3_specialist_generic_fallback_when_stack_undetected(
        self, invoker_full
    ):
        """Without .claude/settings.json, Phase 3 falls back to the generic
        label from phase_specialists.GENERIC_PHASE_3_FALLBACK — not a guess."""
        prompt = invoker_full._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert f'subagent_type="{GENERIC_PHASE_3_FALLBACK}"' in prompt

    def test_phase_3_specialist_resolves_from_stack_template(self, invoker_fastapi):
        """With project.template = fastapi-python, Phase-3 resolves to
        python-api-specialist — proving the prompt consumes phase_specialists.py
        rather than hardcoding."""
        expected = STACK_TO_PHASE_3_SPECIALIST["fastapi-python"]
        assert expected == "python-api-specialist"  # sanity check source
        prompt = invoker_fastapi._build_autobuild_implementation_prompt(
            task_id="TASK-001", mode="standard", turn=1, max_turns=5
        )
        assert f'subagent_type="{expected}"' in prompt


# ---------------------------------------------------------------------------
# 3. Inline builder (_build_inline_implement_protocol) — mandate language
# ---------------------------------------------------------------------------


class TestInlineBuilderMandate:
    """_build_inline_implement_protocol renders the same mandate language
    without loading a .md file."""

    @pytest.mark.parametrize("mode", ["standard", "tdd", "bdd"])
    def test_inline_builder_has_phase_4_mandate(self, invoker_full, mode):
        prompt = invoker_full._build_inline_implement_protocol("TASK-I", mode=mode)
        assert 'subagent_type="test-orchestrator"' in prompt

    @pytest.mark.parametrize("mode", ["standard", "tdd", "bdd"])
    def test_inline_builder_has_phase_5_mandate(self, invoker_full, mode):
        prompt = invoker_full._build_inline_implement_protocol("TASK-I", mode=mode)
        assert 'subagent_type="code-reviewer"' in prompt

    def test_inline_builder_removes_inline_pytest(self, invoker_full):
        """The inline builder must no longer emit inline `pytest tests/ -v`
        as the test-runner directive (that prose is the defect)."""
        prompt = invoker_full._build_inline_implement_protocol("TASK-I", mode="standard")
        assert "pytest tests/ -v --tb=short" not in prompt
        assert "npx tsc --noEmit" not in prompt

    def test_inline_builder_phase_3_uses_phase_specialists_fallback(
        self, invoker_full
    ):
        """Phase 3 must render GENERIC_PHASE_3_FALLBACK when stack undetected."""
        prompt = invoker_full._build_inline_implement_protocol("TASK-I", mode="standard")
        assert f'subagent_type="{GENERIC_PHASE_3_FALLBACK}"' in prompt

    def test_inline_builder_phase_3_uses_stack_specialist(self, invoker_fastapi):
        """Phase 3 resolves to python-api-specialist for fastapi-python stack."""
        prompt = invoker_fastapi._build_inline_implement_protocol(
            "TASK-I", mode="standard"
        )
        expected = STACK_TO_PHASE_3_SPECIALIST["fastapi-python"]
        assert f'subagent_type="{expected}"' in prompt
