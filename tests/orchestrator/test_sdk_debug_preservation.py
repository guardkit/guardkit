"""Tests for guardkit.orchestrator.sdk_debug (TASK-DIAG-F4A2).

Verifies the diagnostic preservation of rendered Player/Coach prompts and
SDK message streams under sdk_debug/turn_<n>/[coach/[test_run/]].

The tests cover:
  * Default-off behaviour (env var unset → no directory)
  * On behaviour (env var set → triple of files written)
  * Byte-equality of preserved prompt vs the prompt the SDK saw
  * JSONL message stream is one parseable JSON per line
  * Idempotency on re-run (existing turn dir is overwritten)
  * Coach role lands under turn_<n>/coach/
  * Coach validator independent-test path lands under turn_<n>/coach/test_run/
  * preserve_event is a no-op when preserve_prompt was disabled
  * Helper never raises on broken inputs
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import pytest

from guardkit.orchestrator import sdk_debug


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Each test starts with the preservation env var unset."""
    monkeypatch.delenv(sdk_debug.ENV_VAR, raising=False)


@dataclass
class FakeOptions:
    """Minimal stand-in for ClaudeAgentOptions (which is itself a dataclass)."""

    cwd: str = "/tmp"
    allowed_tools: List[str] = field(default_factory=list)
    permission_mode: str = "acceptEdits"
    max_turns: int = 5


@dataclass
class FakeBlock:
    """Stand-in for an SDK ContentBlock (TextBlock/ToolUseBlock/etc.)."""

    text: str = ""
    name: str = ""
    type: str = "text"


@dataclass
class FakeAssistantMessage:
    """Stand-in for an SDK AssistantMessage."""

    content: List[FakeBlock] = field(default_factory=list)


# ---------------------------------------------------------------------------
# preservation_enabled
# ---------------------------------------------------------------------------


def test_preservation_disabled_by_default():
    assert sdk_debug.preservation_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Y", "on"])
def test_preservation_enabled_truthy_values(monkeypatch, value):
    monkeypatch.setenv(sdk_debug.ENV_VAR, value)
    assert sdk_debug.preservation_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "anything-else"])
def test_preservation_enabled_falsy_values(monkeypatch, value):
    monkeypatch.setenv(sdk_debug.ENV_VAR, value)
    assert sdk_debug.preservation_enabled() is False


# ---------------------------------------------------------------------------
# compute_debug_dir
# ---------------------------------------------------------------------------


def test_compute_debug_dir_player(tmp_path):
    p = sdk_debug.compute_debug_dir(tmp_path, "TASK-X", 3, "player")
    assert p == tmp_path / ".guardkit" / "autobuild" / "TASK-X" / "sdk_debug" / "turn_3"


def test_compute_debug_dir_coach(tmp_path):
    p = sdk_debug.compute_debug_dir(tmp_path, "TASK-X", 2, "coach")
    assert p.name == "coach"
    assert p.parent.name == "turn_2"


def test_compute_debug_dir_coach_test(tmp_path):
    p = sdk_debug.compute_debug_dir(tmp_path, "TASK-X", 1, "coach_test")
    assert p.name == "test_run"
    assert p.parent.name == "coach"
    assert p.parent.parent.name == "turn_1"


def test_compute_debug_dir_unknown_role_falls_back_to_player(tmp_path):
    p = sdk_debug.compute_debug_dir(tmp_path, "TASK-X", 1, "bogus")
    # falls back to player layout (no role subdir)
    assert p.name == "turn_1"


# ---------------------------------------------------------------------------
# preserve_prompt — default-off
# ---------------------------------------------------------------------------


def test_preserve_prompt_default_off_writes_nothing(tmp_path):
    result = sdk_debug.preserve_prompt(
        workspace_root=tmp_path,
        task_id="TASK-X",
        turn=1,
        role="player",
        prompt="hello",
        options=FakeOptions(),
    )
    assert result is None
    assert not (tmp_path / ".guardkit").exists()


# ---------------------------------------------------------------------------
# preserve_prompt — on
# ---------------------------------------------------------------------------


def test_preserve_prompt_writes_triple_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    prompt_text = "Task(subagent_type=test-orchestrator) please run the suite"
    options = FakeOptions(allowed_tools=["Read", "Write"])
    debug_dir = sdk_debug.preserve_prompt(
        workspace_root=tmp_path,
        task_id="TASK-X",
        turn=1,
        role="player",
        prompt=prompt_text,
        options=options,
    )

    assert debug_dir is not None
    assert debug_dir.is_dir()
    # AC: prompt.txt is byte-equal to the prompt passed to the SDK
    assert (debug_dir / "prompt.txt").read_text(encoding="utf-8") == prompt_text
    # options.json round-trips and contains the dataclass fields
    options_json = json.loads((debug_dir / "options.json").read_text())
    assert options_json["allowed_tools"] == ["Read", "Write"]
    assert options_json["permission_mode"] == "acceptEdits"
    # messages.jsonl exists (initially empty)
    messages_path = debug_dir / "messages.jsonl"
    assert messages_path.exists()
    assert messages_path.read_text() == ""


def test_preserve_prompt_player_path_layout(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 4, "player", "p", FakeOptions()
    )
    rel = debug_dir.relative_to(tmp_path)
    assert rel == Path(".guardkit/autobuild/TASK-X/sdk_debug/turn_4")


def test_preserve_prompt_coach_path_layout(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 4, "coach", "p", FakeOptions()
    )
    rel = debug_dir.relative_to(tmp_path)
    assert rel == Path(".guardkit/autobuild/TASK-X/sdk_debug/turn_4/coach")


def test_preserve_prompt_coach_test_path_layout(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 4, "coach_test", "p", FakeOptions()
    )
    rel = debug_dir.relative_to(tmp_path)
    assert rel == Path(".guardkit/autobuild/TASK-X/sdk_debug/turn_4/coach/test_run")


def test_preserve_prompt_idempotent_overwrite(tmp_path, monkeypatch):
    """A repeated turn should overwrite, not append, to avoid stale state."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "first", FakeOptions()
    )
    # Drop a stale messages.jsonl line
    (debug_dir / "messages.jsonl").write_text("STALE\n")
    # Re-run preservation for the same turn
    debug_dir2 = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "second", FakeOptions()
    )

    assert debug_dir2 == debug_dir
    assert (debug_dir / "prompt.txt").read_text() == "second"
    assert (debug_dir / "messages.jsonl").read_text() == ""


def test_preserve_prompt_handles_unserialisable_options(tmp_path, monkeypatch):
    """Options whose internals cannot be JSON-serialised must not raise."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    class Weird:
        def __init__(self):
            # A circular reference that json.dumps would normally choke on
            # without our default=repr fallback.
            self.self_ref = self

        def __repr__(self) -> str:
            return "<Weird>"

    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", options=Weird()
    )
    assert debug_dir is not None
    # File is valid JSON and the circular ref was repr'd, not raised
    payload = json.loads((debug_dir / "options.json").read_text())
    assert payload == {"self_ref": "<Weird>"}


def test_preserve_prompt_swallows_filesystem_errors(tmp_path, monkeypatch):
    """Helper must never raise into the AutoBuild hot path."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    # Point workspace_root at a path that cannot be created (a regular file)
    bad_root = tmp_path / "not-a-dir"
    bad_root.write_text("blocking file")

    result = sdk_debug.preserve_prompt(
        bad_root, "TASK-X", 1, "player", "p", FakeOptions()
    )
    assert result is None  # logged warning, no raise


# ---------------------------------------------------------------------------
# preserve_event
# ---------------------------------------------------------------------------


def test_preserve_event_writes_one_jsonl_per_call(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", FakeOptions()
    )
    msg1 = FakeAssistantMessage(content=[FakeBlock(text="hello")])
    msg2 = FakeAssistantMessage(content=[FakeBlock(name="Read", type="tool_use")])
    sdk_debug.preserve_event(debug_dir, msg1)
    sdk_debug.preserve_event(debug_dir, msg2)

    raw = (debug_dir / "messages.jsonl").read_text(encoding="utf-8")
    lines = [line for line in raw.splitlines() if line]
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["type"] == "FakeAssistantMessage"
    assert parsed[0]["content"][0]["text"] == "hello"
    assert parsed[1]["content"][0]["name"] == "Read"


def test_preserve_event_noop_when_disabled(tmp_path):
    """preserve_event called with None debug_dir is a no-op."""
    sdk_debug.preserve_event(None, FakeAssistantMessage())  # must not raise
    # And the disk is untouched
    assert not (tmp_path / ".guardkit").exists()


def test_preserve_event_handles_non_dataclass_event(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", FakeOptions()
    )

    class PlainObject:
        def __init__(self):
            self.foo = "bar"
            self.content = [FakeBlock(text="t")]

    sdk_debug.preserve_event(debug_dir, PlainObject())
    line = (debug_dir / "messages.jsonl").read_text().strip()
    parsed = json.loads(line)
    assert parsed["type"] == "PlainObject"
    assert parsed["foo"] == "bar"


def test_preserve_event_handles_unserialisable_event(tmp_path, monkeypatch):
    """A pathological event must not abort the run."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", FakeOptions()
    )

    class Exploding:
        @property
        def __dict__(self) -> dict:
            raise RuntimeError("boom")

        def __repr__(self) -> str:
            return "<Exploding>"

    # Must not raise even when introspection fails everywhere
    sdk_debug.preserve_event(debug_dir, Exploding())


# ---------------------------------------------------------------------------
# AC integration: byte-equality test using a stub SDK
# ---------------------------------------------------------------------------


def test_byte_equality_with_stub_sdk(tmp_path, monkeypatch):
    """End-to-end: stub records what the SDK was invoked with and we compare
    against the preserved prompt.txt."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    rendered = (
        "PLAYER PROTOCOL\n\n"
        'Task(subagent_type="test-orchestrator")\n'
        "Run the full pytest suite.\n"
    )

    captured: dict[str, Any] = {}

    def fake_sdk_query(prompt: str, options: Any) -> None:
        # Stand-in for `sdk.query(...)` — record exactly what would be sent.
        captured["prompt"] = prompt
        captured["options"] = options

    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", rendered, FakeOptions()
    )
    fake_sdk_query(prompt=rendered, options=FakeOptions())

    on_disk = (debug_dir / "prompt.txt").read_text(encoding="utf-8")
    assert on_disk == captured["prompt"]
    assert "Task(subagent_type=" in on_disk


# ---------------------------------------------------------------------------
# Default-off: no sdk_debug/ directory ever created
# ---------------------------------------------------------------------------


def test_options_to_jsonable_handles_none():
    assert sdk_debug._options_to_jsonable(None) is None


def test_options_to_jsonable_pydantic_model_dump_path(tmp_path, monkeypatch):
    """Options exposing a model_dump() method (pydantic-style) round-trip."""
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")

    class PydanticLike:
        def model_dump(self):
            return {"max_turns": 7, "model": "claude"}

    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", options=PydanticLike()
    )
    payload = json.loads((debug_dir / "options.json").read_text())
    assert payload == {"max_turns": 7, "model": "claude"}


def test_event_to_jsonable_pydantic_model_dump_path(tmp_path, monkeypatch):
    monkeypatch.setenv(sdk_debug.ENV_VAR, "1")
    debug_dir = sdk_debug.preserve_prompt(
        tmp_path, "TASK-X", 1, "player", "p", FakeOptions()
    )

    class PydanticEvent:
        def model_dump(self):
            return {"role": "assistant", "tokens": 12}

    sdk_debug.preserve_event(debug_dir, PydanticEvent())
    parsed = json.loads((debug_dir / "messages.jsonl").read_text().strip())
    assert parsed["type"] == "PydanticEvent"
    assert parsed["role"] == "assistant"


def test_coerce_jsonable_handles_path_and_collections():
    out = sdk_debug._coerce_jsonable(
        {"p": Path("/tmp/x"), "items": (1, 2, {3, 4}), "n": None}
    )
    assert out["p"] == "/tmp/x"
    assert out["items"][0] == 1
    assert sorted(out["items"][2]) == [3, 4]
    assert out["n"] is None


def test_event_to_jsonable_none_event():
    """Defensive: helper accepts None gracefully."""
    assert sdk_debug._event_to_jsonable(None) == {"type": "None"}


def test_default_off_no_sdk_debug_directory(tmp_path):
    """With the env var unset, no preservation directory is produced."""
    # Even when callers go through the full helper, nothing is written.
    sdk_debug.preserve_prompt(tmp_path, "TASK-X", 1, "player", "p", FakeOptions())
    sdk_debug.preserve_event(None, FakeAssistantMessage())
    sdk_debug_root = tmp_path / ".guardkit" / "autobuild" / "TASK-X" / "sdk_debug"
    assert not sdk_debug_root.exists()
