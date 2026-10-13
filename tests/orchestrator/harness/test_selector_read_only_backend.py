"""A read-only request gets a read-only backend (13 October 2026).

Proof defect 5: the code reviewer asks for ``["Read", "Search", "Grep"]``, but
the LangGraph path built it a writable backend with a shell, and on the first
web fixture proof it ran long shell commands until it timed out. The selector
now asks ``build_autobuild_backend`` for ``read_only=True`` for such a request,
never for the Player, and refuses the request rather than build a writable
backend when the installed factory cannot honour it.

``guardkitfactory.harness`` is replaced with a stub module here: these tests
are about what the selector asks the factory for, and they must not depend on
the locally installed DeepAgents.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import select_harness

READ_ONLY_REVIEWER = ["Read", "Search", "Grep"]
TOOL_USING_COACH = ["Read", "Bash", "Grep", "Glob"]
PLAYER_TOOLS = ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"]


def _install_factory(monkeypatch, *, accepts_read_only: bool) -> List[Dict[str, Any]]:
    """Put a stub ``guardkitfactory.harness`` in place; return its backend calls."""
    calls: List[Dict[str, Any]] = []

    if accepts_read_only:

        def build_autobuild_backend(
            cwd,
            *,
            max_tool_result_chars=None,
            scratch_root=None,
            read_only: bool = False,
        ):
            calls.append({"cwd": cwd, "read_only": read_only})
            return SimpleNamespace(read_only=read_only)

    else:

        def build_autobuild_backend(cwd, *, max_tool_result_chars=None, scratch_root=None):
            calls.append({"cwd": cwd})
            return SimpleNamespace(read_only=None)

    class LangGraphHarness:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.backend = kwargs.get("backend")

    harness_mod = ModuleType("guardkitfactory.harness")
    harness_mod.LangGraphHarness = LangGraphHarness  # type: ignore[attr-defined]
    harness_mod.build_autobuild_backend = build_autobuild_backend  # type: ignore[attr-defined]
    harness_mod.build_autobuild_permissions = lambda: object()  # type: ignore[attr-defined]
    harness_mod.build_player_config = lambda **_: None  # type: ignore[attr-defined]
    package = ModuleType("guardkitfactory")
    package.harness = harness_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "guardkitfactory", package)
    monkeypatch.setitem(sys.modules, "guardkitfactory.harness", harness_mod)
    monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
    return calls


def _select(
    tmp_path: Path, seat: str, tools: List[str], role: Optional[str]
) -> Any:
    kwargs: Dict[str, Any] = {
        "cwd": tmp_path,
        "model": seat,
        "allowed_tools": tools,
        "permission_mode": "bypassPermissions",
    }
    if role is not None:
        kwargs["harness_role"] = role
    return select_harness(**kwargs)


def test_a_read_only_request_asks_for_a_read_only_backend(
    tmp_path, monkeypatch, m0_routine_fleet_route
):
    calls = _install_factory(monkeypatch, accepts_read_only=True)

    harness = _select(tmp_path, m0_routine_fleet_route, READ_ONLY_REVIEWER, "coach")

    assert calls == [{"cwd": tmp_path, "read_only": True}]
    assert harness.backend.read_only is True


@pytest.mark.parametrize(
    ("tools", "role"),
    [(TOOL_USING_COACH, "coach"), (PLAYER_TOOLS, "player"), (READ_ONLY_REVIEWER, "player")],
)
def test_other_requests_do_not_ask_for_read_only(
    tmp_path, monkeypatch, m0_routine_fleet_route, tools, role
):
    calls = _install_factory(monkeypatch, accepts_read_only=True)

    _select(tmp_path, m0_routine_fleet_route, tools, role)

    assert calls == [{"cwd": tmp_path, "read_only": False}]


def test_an_old_factory_refuses_the_read_only_request(
    tmp_path, monkeypatch, m0_routine_fleet_route
):
    calls = _install_factory(monkeypatch, accepts_read_only=False)

    with pytest.raises(AgentInvocationError, match="read-only backend"):
        _select(tmp_path, m0_routine_fleet_route, READ_ONLY_REVIEWER, "coach")
    assert calls == []


@pytest.mark.parametrize(
    ("tools", "role"), [(TOOL_USING_COACH, "coach"), (PLAYER_TOOLS, "player")]
)
def test_an_old_factory_still_builds_every_other_request(
    tmp_path, monkeypatch, m0_routine_fleet_route, tools, role
):
    calls = _install_factory(monkeypatch, accepts_read_only=False)

    harness = _select(tmp_path, m0_routine_fleet_route, tools, role)

    assert calls == [{"cwd": tmp_path}]
    assert harness.backend.read_only is None
