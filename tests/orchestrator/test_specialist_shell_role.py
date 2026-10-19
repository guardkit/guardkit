"""Specialists get their own shell folders, never the builder's or checker's.

19 October 2026 (review R1). A specialist runs with the Player's or the
Coach's permissions: ``run_specialist`` gives the test orchestrator
``agent_type="player"`` and the code reviewer ``agent_type="coach"``, and
``AgentInvoker`` passes that on as the harness role. Without more, the
selector would give the test orchestrator (which runs shell commands) the
builder's home and temporary folders. ``run_specialist`` now also names the
shell role ``"specialist"``.

These tests go through the real callers: ``run_specialist`` and a real
``AgentInvoker`` into the real selector, which builds the shell with the real
guardkitfactory. The invocation is stopped as soon as the shell is built, and
the shell's ``HOME`` and ``TMPDIR`` are compared with the builder's and the
checker's, built through the same ``AgentInvoker`` the normal way.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

import pytest

backend_config = pytest.importorskip(
    "guardkitfactory.harness.backend_config",
    reason="guardkitfactory + langchain stack not installed; seam test only",
)

from guardkit.orchestrator.harness import selector  # noqa: E402
from guardkit.orchestrator.specialist_invocations import run_specialist  # noqa: E402
from tests.conftest import M0_FLEET_SEAT  # noqa: E402

pytestmark = pytest.mark.seam


class _StopAfterTheShell(Exception):
    """Raised once the shell is built, so no model is ever called."""


def _worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    subprocess.run(["git", "init", "-q", str(worktree)], check=True)
    return worktree


@pytest.fixture()
def shells(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Record every shell the selector builds, then stop the invocation."""
    built: list[dict[str, Any]] = []
    real_build = selector._build_backend_with_optional_cap

    def record(factory: Any, worktree: Path, *args: Any, **kwargs: Any) -> Any:
        backend = real_build(
            backend_config.build_autobuild_backend, worktree, *args, **kwargs
        )
        env = backend.default._env
        built.append(
            {"role": kwargs.get("shell_role"), "HOME": env["HOME"], "TMPDIR": env["TMPDIR"]}
        )
        raise _StopAfterTheShell()

    monkeypatch.setattr(selector, "_build_backend_with_optional_cap", record)
    monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
    # A local model address (the M0 fence needs one); nothing is ever sent,
    # because the invocation stops once the shell is built.
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    # The Player route's own launch settings: a profile of this test's own,
    # offline, no tracing; restored afterwards.
    profile = tmp_path / "dcode-profile"
    profile.mkdir()
    # The selector keeps one dcode profile per process; start from none so
    # an earlier test's profile does not refuse this one (as test_selector).
    monkeypatch.setattr(selector, "_AUTO_DCODE_PROFILE", None)
    monkeypatch.setenv("DEEPAGENTS_HOME", str(profile))
    monkeypatch.setenv("DEEPAGENTS_CODE_OFFLINE", "1")
    for name in ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"):
        monkeypatch.setenv(name, "false")
    return {"built": built, "worktree": _worktree(tmp_path)}


def _invoker(worktree: Path) -> Any:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=60,
        model_name=M0_FLEET_SEAT,
    )


def _invoke_as(invoker: Any, agent_type: str) -> None:
    try:
        asyncio.run(
            invoker._invoke_with_role(
                prompt="x",
                agent_type=agent_type,
                allowed_tools=["Read", "Bash"],
                permission_mode="acceptEdits" if agent_type == "player" else "bypassPermissions",
                task_id="TASK-SHELL-1",
                turn=1,
            )
        )
    except Exception:  # noqa: BLE001 - stopped on purpose after the shell
        pass


def _specialist(invoker: Any, worktree: Path, name: str) -> None:
    result = asyncio.run(
        run_specialist(
            specialist_name=name,
            worktree_path=worktree,
            task_id="TASK-SHELL-1",
            sdk_timeout=60,
            prompt="x",
            allowed_tools=["Read", "Bash"],
            agent_invoker=invoker,
        )
    )
    # The runner never raises; it reports the stop as a failure.
    assert result.status == "failed"


def test_specialists_get_their_own_home_and_tmpdir(shells: dict) -> None:
    worktree = shells["worktree"]
    built = shells["built"]
    invoker = _invoker(worktree)

    _invoke_as(invoker, "player")
    _invoke_as(invoker, "coach")
    _specialist(invoker, worktree, "test-orchestrator")
    _specialist(invoker, worktree, "code-reviewer")

    assert [shell["role"] for shell in built] == [
        "builder", "checker", "specialist", "specialist",
    ], built
    builder, checker, tester, reviewer = built
    for specialist in (tester, reviewer):
        for name in ("HOME", "TMPDIR"):
            assert specialist[name] != builder[name], (name, specialist, builder)
            assert specialist[name] != checker[name], (name, specialist, checker)
            # Outside the project: in the checkout's own git folder.
            assert Path(specialist[name]).is_relative_to(worktree.resolve() / ".git")
    assert Path(tester["HOME"]).name == "specialist-SHELL-HOME"
    assert Path(tester["TMPDIR"]).name == "specialist-SHELL-TMPDIR"
    assert builder["HOME"] != checker["HOME"]


def test_a_specialist_keeps_its_permission_role_and_harness_route(
    shells: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the shell's folders change, not the permission role or route.

    The test orchestrator still takes the Player's route (the selector sets
    up the dcode Player launch for it, as before); the code reviewer does not.
    """
    worktree = shells["worktree"]
    player_launches: list[Path] = []
    real_launch = selector._configure_dcode_launch

    def launch(task_worktree: Path) -> Path:
        player_launches.append(task_worktree)
        return real_launch(task_worktree)

    monkeypatch.setattr(selector, "_configure_dcode_launch", launch)
    invoker = _invoker(worktree)

    _specialist(invoker, worktree, "test-orchestrator")
    assert len(player_launches) == 1
    _specialist(invoker, worktree, "code-reviewer")
    assert len(player_launches) == 1

    assert [shell["role"] for shell in shells["built"]] == ["specialist", "specialist"]


def test_an_unknown_shell_role_is_refused() -> None:
    with pytest.raises(ValueError, match="shell_role must be one of"):
        selector.select_harness(shell_role="reviewer", cwd=Path("/nonexistent"))
