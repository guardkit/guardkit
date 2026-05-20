"""Falsifier tests for the HarnessAdapter ABC (TASK-HMIG-001A, AC-005).

Verifies the abstract surface defined in
:mod:`guardkit.orchestrator.harness.adapter` enforces its contract: the
base class cannot be instantiated, incomplete subclasses cannot be
instantiated, and a trivial fake subclass implementing only ``invoke``
instantiates cleanly with the documented default property values.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import AsyncIterator

import pytest

from guardkit.orchestrator.harness import (
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
)


class _FakeHarness(HarnessAdapter):
    """Trivial concrete subclass for instantiation + default-property tests."""

    async def invoke(
        self,
        prompt: str,
        role: str,
        tools: list,
        cwd: Path,
        *,
        timeout_seconds: int,
    ) -> AsyncIterator[HarnessEvent]:
        yield ResultMessageEvent(session_id=None)


class _IncompleteHarness(HarnessAdapter):
    """Deliberately missing the abstract ``invoke`` method."""

    # No ``invoke`` defined — instantiation must raise TypeError.


def test_instantiating_abstract_adapter_raises_type_error() -> None:
    with pytest.raises(TypeError):
        HarnessAdapter()  # type: ignore[abstract]


def test_incomplete_subclass_missing_invoke_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _IncompleteHarness()  # type: ignore[abstract]


def test_trivial_concrete_subclass_instantiates_with_defaults() -> None:
    harness = _FakeHarness()
    assert harness.session_id is None
    assert harness.supports_resume is False


def test_invoke_signature_matches_contract() -> None:
    """Guard against accidental drift in the abstract method signature."""
    sig = inspect.signature(HarnessAdapter.invoke)
    params = sig.parameters
    assert list(params) == [
        "self",
        "prompt",
        "role",
        "tools",
        "cwd",
        "timeout_seconds",
    ]
    assert params["timeout_seconds"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.asyncio
async def test_fake_subclass_invoke_yields_events() -> None:
    """Sanity check the fake yields the expected event variant."""
    harness = _FakeHarness()
    events = []
    async for event in harness.invoke(
        prompt="hi",
        role="player",
        tools=[],
        cwd=Path("."),
        timeout_seconds=10,
    ):
        events.append(event)
    assert len(events) == 1
    assert isinstance(events[0], ResultMessageEvent)
    assert events[0].type == "result_message"
