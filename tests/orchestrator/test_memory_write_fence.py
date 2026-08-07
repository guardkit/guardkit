"""The test suite must not be able to write to the real memory store.

``AutoBuildOrchestrator.orchestrate`` records a build outcome at every
terminal. Eighteen test files in this suite drive ``orchestrate(...)`` with
fixture task ids, and on the factory seat — memory ON, the broker reachable,
the writer credential exported, which is this estate's NORMAL state — each of
those runs would publish a made-up build outcome into the same store the gates
read back as priors. Fixture tasks would become production history.

``tests/conftest.py`` fences this with an autouse fixture. These tests prove
the fence is really on, and that the one file allowed past it is the one whose
subject IS the capture seam.

Nothing here touches a broker, a store, or the network.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def orchestrator(tmp_path: Path):
    """An orchestrator built the same way the other suites build one."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    (tmp_path / ".git").mkdir()
    (tmp_path / ".guardkit").mkdir()
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=3,
        worktree_manager=MagicMock(),
        enable_pre_loop=False,
    )


class TestLiveMemoryWritesAreFenced:
    """No unmarked test can reach the real writer."""

    def test_capture_never_reaches_the_writer_even_with_memory_declared_on(
        self, orchestrator, monkeypatch
    ):
        """The fence holds when the environment says memory is ON.

        Asserting only ``result is None`` proves NOTHING: the real method
        returns None when memory is off, which is the state the belt half of
        the fence puts every test in anyway. Such a test passes with the braces
        (the method patch) removed entirely — mutation-checked — so it cannot
        tell a working fence from a missing one.

        This is the shape that can. Declare memory ON, so the belt is defeated
        and the real method WOULD go looking for a client, then watch the door
        the real method has to walk through. If the braces are gone, that door
        opens and this fails.
        """
        called: list = []

        def _tripwire(*_args, **_kwargs):
            called.append(True)
            raise AssertionError(
                "the fence is gone: a fixture build reached the memory client"
            )

        monkeypatch.setenv("FLEET_MEMORY_ENABLED", "true")
        monkeypatch.setattr(
            "guardkit.orchestrator.autobuild.get_memory_client", _tripwire
        )
        monkeypatch.setattr(
            "guardkit.knowledge.outcome_manager.get_memory_client", _tripwire
        )

        result = orchestrator._capture_build_outcome(
            "TASK-FENCE-001",
            success=True,
            final_decision="approved",
            turn_history=[],
            task_title="A fixture task that must never reach the store",
            requirements="none",
        )

        assert called == [], "the capture seam asked for a memory client"
        assert result is None

    def test_the_real_capture_is_not_the_one_installed(self, orchestrator):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # The fence swaps the method out wholesale, so the bound method is not
        # the production one. If this ever passes by accident, the fence is
        # gone and fixture builds are writing to the live store again.
        assert (
            AutoBuildOrchestrator._capture_build_outcome.__name__
            == "_no_memory_write"
        )

    def test_memory_is_off_in_the_environment(self):
        import os

        # The belt half of the fence: nothing in a test session declares
        # memory ON, so a lazily built client comes up disabled.
        assert os.environ.get("FLEET_MEMORY_ENABLED") is None

    def test_the_fence_accepts_any_capture_call_shape(self, orchestrator):
        # The stand-in has to swallow every keyword the real method takes, or
        # the fence itself would break the builds it is protecting.
        assert (
            orchestrator._capture_build_outcome(
                "TASK-FENCE-002",
                success=False,
                final_decision="crashed",
                turn_history=[MagicMock()],
                task_title="t",
                requirements="r",
                error="boom",
            )
            is None
        )


class TestTheFencesCoverageIsHonestlyBounded:
    """Where the braces stop, and what holds the gap shut today.

    The method patch — the half that actually holds, because it sits above the
    lazily-built process-wide client — protects exactly one door:
    ``AutoBuildOrchestrator._capture_build_outcome``. It does NOT protect a
    test that calls ``outcome_manager.capture_task_outcome`` (or the verified
    variant) directly, which is the door the ``guardkit memory capture-outcome``
    CLI path goes through. Such a test is covered only by the belt — the
    ``FLEET_MEMORY_ENABLED`` delenv — and ``tests/conftest.py`` documents in its
    own words why the belt leaks: an earlier test that built the client while
    memory was ON keeps an enabled client no matter what later tests do to the
    environment.

    No test exploits that today: every file that calls those functions also
    patches ``get_memory_client``, so the real client is never reached. That is
    a fact about the current suite, not a guarantee, so it is asserted rather
    than assumed. The braces are deliberately not extended over those functions
    — the suites whose SUBJECT is the writer have to be able to call them.
    """

    def test_every_direct_caller_of_the_writer_fakes_the_client(self):
        tests_dir = Path(__file__).resolve().parent.parent
        unfaked = sorted(
            p.relative_to(tests_dir).as_posix()
            for p in tests_dir.rglob("test_*.py")
            if "capture_task_outcome" in (text := p.read_text(encoding="utf-8"))
            and "get_memory_client" not in text
        )
        assert unfaked == [], (
            "these tests call the outcome writer without faking "
            "get_memory_client, so only the leaky belt stands between them "
            "and the live store: " + ", ".join(unfaked)
        )


class TestTheOptOutIsExplicit:
    """The marker exists, is registered, and is used by exactly one module."""

    def test_marker_is_registered(self, pytestconfig):
        markers = pytestconfig.getini("markers")
        assert any(m.startswith("allow_memory_capture") for m in markers), markers

    def test_only_the_capture_suite_opts_out(self):
        # Greppable by design: an opt-out that spreads is a fence that has
        # stopped meaning anything.
        tests_dir = Path(__file__).resolve().parent.parent
        users = sorted(
            p.relative_to(tests_dir).as_posix()
            for p in tests_dir.rglob("test_*.py")
            if "allow_memory_capture" in p.read_text(encoding="utf-8")
        )
        assert users == [
            "orchestrator/test_autobuild_outcome_capture.py",
            "orchestrator/test_memory_write_fence.py",
        ], users
