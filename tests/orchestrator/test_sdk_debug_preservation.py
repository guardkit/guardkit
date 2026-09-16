"""Tests for guardkit.orchestrator.sdk_debug (TASK-DIAG-F4A2).

Verifies the diagnostic preservation of rendered Player/Coach prompts and
SDK message streams under sdk_debug/turn_<n>/[coach/[test_run/]].

The tests cover:
  * Default-on-by-allowlist behaviour (D-OBS-2 / TASK-OBS-396E): env var unset →
    ON in allowlisted repos (guards permitting), OFF elsewhere
  * Explicit env override: truthy → ON, falsy → OFF, unrecognized → fail-safe OFF
    + warn once (unrecognized-env decision 2026-07-10, Option B)
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
    """Each test starts with the preservation env var unset and the warn latch reset."""
    monkeypatch.delenv(sdk_debug.ENV_VAR, raising=False)
    # Reset the one-time unrecognized-env warning latch (TASK-OBS-396E).
    monkeypatch.setattr(sdk_debug, "_unrecognized_env_warned", False, raising=False)


@pytest.fixture
def _non_allowlisted_repo(monkeypatch):
    """Force repo detection to a non-allowlisted (client-style) repo.

    Under the D-OBS-2 default-on-by-allowlist contract, preservation defaults
    ON in allowlisted repos (guardkit/forge/study-tutor/fleet-*). These tests
    run inside a checkout named ``guardkit``, so they must pin the repo name to
    something non-allowlisted to exercise the default-OFF path.
    """
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "some-client-repo")


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


def test_preservation_disabled_outside_allowlisted_repos(_non_allowlisted_repo):
    """D-OBS-2: with the env var unset, a non-allowlisted repo defaults OFF."""
    assert sdk_debug.preservation_enabled() is False


def test_preservation_enabled_by_default_in_allowlisted_repo(monkeypatch, tmp_path):
    """D-OBS-2: with the env var unset, an allowlisted repo defaults ON once guards pass."""
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "guardkit")
    # Neutralise the structural flip-gates so the test asserts the allowlist path,
    # not the ambient git/gitignore state of the checkout it happens to run in.
    monkeypatch.setattr(sdk_debug, "_validate_rotation_caps", lambda: True)
    monkeypatch.setattr(sdk_debug, "_check_gitignore_coverage", lambda *_: True)
    assert sdk_debug.preservation_enabled_for_repo(tmp_path) is True


def test_preservation_default_on_gated_by_structural_guards(monkeypatch, tmp_path):
    """An allowlisted repo still defaults OFF if a flip-gate fails (fail-safe)."""
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "guardkit")
    monkeypatch.setattr(sdk_debug, "_validate_rotation_caps", lambda: True)
    monkeypatch.setattr(sdk_debug, "_check_gitignore_coverage", lambda *_: False)
    assert sdk_debug.preservation_enabled_for_repo(tmp_path) is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Y", "on"])
def test_preservation_enabled_truthy_values(monkeypatch, value):
    monkeypatch.setenv(sdk_debug.ENV_VAR, value)
    assert sdk_debug.preservation_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_preservation_enabled_explicit_falsy_values(monkeypatch, value):
    """Explicit falsy values force OFF regardless of repo allowlist."""
    # Even in an allowlisted repo with passing guards, explicit-off wins.
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "guardkit")
    monkeypatch.setattr(sdk_debug, "_validate_rotation_caps", lambda: True)
    monkeypatch.setattr(sdk_debug, "_check_gitignore_coverage", lambda *_: True)
    monkeypatch.setenv(sdk_debug.ENV_VAR, value)
    assert sdk_debug.preservation_enabled() is False


@pytest.mark.parametrize("value", ["", "  "])
def test_preservation_empty_env_defers_to_allowlist(monkeypatch, value):
    """An exported-but-empty env var is equivalent to unset (defers to allowlist)."""
    # Non-allowlisted → OFF.
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "some-client-repo")
    monkeypatch.setenv(sdk_debug.ENV_VAR, value)
    assert sdk_debug.preservation_enabled() is False


def test_preservation_unrecognized_env_is_off_even_in_allowlisted_repo(
    monkeypatch, tmp_path, caplog
):
    """TASK-OBS-396E decision (2026-07-10, Option B): an explicit-but-unrecognized
    value is fail-safe OFF and warns — it must NOT silently ride the default-on
    allowlist path the way an *absent* value does."""
    # Allowlisted repo with passing guards: if unrecognized fell through to the
    # allowlist (Option A), this would be True. Option B makes it False.
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "guardkit")
    monkeypatch.setattr(sdk_debug, "_validate_rotation_caps", lambda: True)
    monkeypatch.setattr(sdk_debug, "_check_gitignore_coverage", lambda *_: True)
    monkeypatch.setenv(sdk_debug.ENV_VAR, "enabled")  # a plausible typo

    with caplog.at_level("WARNING"):
        assert sdk_debug.preservation_enabled_for_repo(tmp_path) is False
    assert any("unrecognized" in rec.message.lower() for rec in caplog.records)


def test_preservation_unrecognized_env_warns_only_once(monkeypatch, caplog):
    """The fail-safe warning is latched to fire once, not on every hot-path call."""
    monkeypatch.setattr(sdk_debug, "_get_repo_name", lambda _root: "some-client-repo")
    monkeypatch.setenv(sdk_debug.ENV_VAR, "banana")

    with caplog.at_level("WARNING"):
        assert sdk_debug.preservation_enabled() is False
        assert sdk_debug.preservation_enabled() is False
        assert sdk_debug.preservation_enabled() is False
    warnings = [r for r in caplog.records if "unrecognized" in r.message.lower()]
    assert len(warnings) == 1


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


def test_preserve_prompt_default_off_writes_nothing(tmp_path, _non_allowlisted_repo):
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


def test_default_off_no_sdk_debug_directory(tmp_path, _non_allowlisted_repo):
    """With the env var unset in a non-allowlisted repo, no preservation dir is produced."""
    # Even when callers go through the full helper, nothing is written.
    sdk_debug.preserve_prompt(tmp_path, "TASK-X", 1, "player", "p", FakeOptions())
    sdk_debug.preserve_event(None, FakeAssistantMessage())
    sdk_debug_root = tmp_path / ".guardkit" / "autobuild" / "TASK-X" / "sdk_debug"
    assert not sdk_debug_root.exists()


# Failed graph capture is deliberately independent of the SDK repr serializer.
def _failed_result(messages=None, **state):
    error = RuntimeError("exception text must never be retained")
    error.raw_result = {"messages": messages or [], **state}
    return error


def _failure_lines(path):
    return [json.loads(line) for line in (path / "messages.jsonl").read_text().splitlines()]


def test_failure_disabled_and_unsupported_repr(tmp_path):
    class Poison:
        def __repr__(self):
            raise AssertionError("repr must not be called")

    sdk_debug.preserve_failure(None, Poison())
    sdk_debug.preserve_failure(tmp_path, _failed_result([Poison()]))
    records = _failure_lines(tmp_path)
    assert records[0]["terminal_graph_index"] is None
    assert records[0]["text_empty"] is None
    assert records[0]["usage"] is None
    assert records[-1]["skills_metadata"] == "not_recorded"
    assert "exception text" not in (tmp_path / "messages.jsonl").read_text()


def test_failure_state_metadata_excludes_memory_content(tmp_path):
    import hashlib
    content = "private instruction text"
    sdk_debug.preserve_failure(tmp_path, _failed_result(
        skills_metadata=[{"name": "planning", "path": "/skills/planning/SKILL.md", "description": "excluded"}],
        skills_load_errors=[
            {"path": "/bad/SKILL.md", "error": "excluded"},
            "Cannot load skills from '/missing/skills': excluded backend error",
            "unknown error format: excluded",
        ],
        memory_contents={"/AGENTS.md": content},
    ))
    state = _failure_lines(tmp_path)[-1]
    assert state["skills_metadata"] == [{"name": "planning", "path": "/skills/planning/SKILL.md"}]
    assert state["skills_load_errors"] == [
        {"path": "/bad/SKILL.md"}, {"path": "/missing/skills"},
        {"path": None, "status": "not_recorded"},
    ]
    assert "excluded" not in (tmp_path / "messages.jsonl").read_text()
    assert state["memory"] == [{"path": "/AGENTS.md", "sha256": hashlib.sha256(content.encode()).hexdigest(), "bytes": len(content)}]
    assert content not in (tmp_path / "messages.jsonl").read_text()


@pytest.mark.parametrize("cap_kind", ["turn", "task"])
def test_failure_prospective_utf8_caps(monkeypatch, tmp_path, cap_kind):
    messages = pytest.importorskip("langchain_core.messages")
    debug = sdk_debug.compute_debug_dir(tmp_path, "TASK-CAP", 2, "player")
    debug.mkdir(parents=True)
    old = debug.parent / "turn_1"
    old.mkdir()
    (old / "prompt.txt").write_bytes(b"x" * 200)
    cap = 1000
    monkeypatch.setattr(sdk_debug, "PER_TURN_CAP_BYTES", cap if cap_kind == "turn" else 10000)
    monkeypatch.setattr(sdk_debug, "PER_TASK_CAP_BYTES", cap if cap_kind == "task" else 10000)
    error = _failed_result([messages.AIMessage(content="\U0001f600" * 10000)])
    sdk_debug.preserve_failure(debug, error)
    first = (debug / "messages.jsonl").read_bytes()
    assert _failure_lines(debug)[0]["type"] == "GraphFailure"
    assert _failure_lines(debug)[0]["text_length"] == 10000
    assert _failure_lines(debug)[-1]["type"] == "GraphFailureTruncated"
    assert len(first) + (200 if cap_kind == "task" else 0) <= cap
    sdk_debug.preserve_failure(debug, error)
    assert (debug / "messages.jsonl").read_bytes() == first


def test_failure_large_field_is_bounded_and_explicit(tmp_path):
    messages = pytest.importorskip("langchain_core.messages")
    sdk_debug.preserve_failure(tmp_path, _failed_result([messages.AIMessage(content="é" * 10000)]))
    record = _failure_lines(tmp_path)[1]
    assert record["truncated"] is True
    assert record["content"].endswith("[TRUNCATED]")
    assert len(record["content"].encode()) <= sdk_debug._FAILURE_FIELD_BYTES


@pytest.mark.parametrize("failure", ["serialize", "redact", "redactor_setup", "extract", "write"])
def test_failure_capture_fails_closed(monkeypatch, tmp_path, failure, caplog):
    from unittest.mock import Mock
    secret = "do-not-log-failed-payload"
    fail = Mock(side_effect=RuntimeError(secret))
    if failure == "serialize":
        monkeypatch.setattr(sdk_debug.json, "dumps", fail)
    elif failure == "redact":
        monkeypatch.setattr(sdk_debug, "_get_redactor", fail)
    elif failure == "redactor_setup":
        monkeypatch.setattr(sdk_debug, "_FailureScrubber", fail)
    elif failure == "extract":
        monkeypatch.setattr(sdk_debug, "_failure_records", fail)
    else:
        monkeypatch.setattr(Path, "open", fail)
    sdk_debug.preserve_failure(tmp_path, _failed_result())
    assert secret not in caplog.text
    if failure != "write":
        assert _failure_lines(tmp_path) == [{"type": "GraphFailureRedactionError", "message": "[REDACTION-FAILED]"}]


def test_failure_without_graph_needs_no_optional_substrate(monkeypatch, tmp_path):
    import builtins
    original_import = builtins.__import__

    def without_langchain(name, *args, **kwargs):
        if name.startswith("langchain_core"):
            raise AssertionError("SDK failure capture must not import optional graph dependencies")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_langchain)
    sdk_debug.preserve_failure(tmp_path, RuntimeError("no graph"))
    summary = _failure_lines(tmp_path)[0]
    assert summary["graph_result_available"] is False
    assert summary["finish_reason"] is None
    assert summary["stop_reason"] is None
    assert summary["text_length"] is None


def test_failure_metadata_unknowns_and_content_blocks(tmp_path):
    messages = pytest.importorskip("langchain_core.messages")
    sdk_debug.preserve_failure(tmp_path, _failed_result([messages.AIMessage(
        content=[{"type": "text", "text": "first"}, {"type": "output_text", "text": " second"}, {"type": "reasoning", "text": "hidden"}],
        response_metadata={"finish_reason": 42, "stop_reason": "length", "unrelated": "drop-me",
                           "token_usage": {"completion_tokens": 12, "prompt_tokens": "unknown", "extra": 99}},
    )]))
    records = _failure_lines(tmp_path)
    assert records[0]["text_length"] == len("first\n second")
    assert records[0]["finish_reason"] is None
    assert records[0]["stop_reason"] == "length"
    assert records[0]["failure_category"] == "truncated_terminal"
    assert records[0]["usage"] == {"completion_tokens": 12}
    assert "drop-me" not in (tmp_path / "messages.jsonl").read_text()


def test_failure_cap_includes_existing_utf8_bytes(monkeypatch, tmp_path):
    existing = '{"type":"existing","content":"é"}\n'.encode()
    path = tmp_path / "messages.jsonl"
    path.write_bytes(existing)
    monkeypatch.setattr(sdk_debug, "PER_TURN_CAP_BYTES", len(existing) + 90)
    sdk_debug.preserve_failure(tmp_path, RuntimeError("unavailable"))
    assert path.read_bytes().startswith(existing)
    assert path.stat().st_size <= sdk_debug.PER_TURN_CAP_BYTES
    assert _failure_lines(tmp_path)[-1]["type"] == "GraphFailureTruncated"


@pytest.mark.parametrize("content", ["  ", [{"type": "text", "text": "  "}]])
def test_failure_whitespace_is_extracted_as_empty(tmp_path, content):
    messages = pytest.importorskip("langchain_core.messages")
    sdk_debug.preserve_failure(tmp_path, _failed_result([messages.AIMessage(
        content=content, additional_kwargs={"finish_reason": "length"},
    )]))
    summary = _failure_lines(tmp_path)[0]
    assert summary["text_length"] == 0
    assert summary["text_empty"] is True
    assert summary["finish_reason"] == "length"


def test_failure_terminal_metadata_summarizes_provider_fields(monkeypatch, tmp_path):
    messages = pytest.importorskip("langchain_core.messages")
    secret = "opaque-terminal-credential-9381"
    monkeypatch.setenv("MALICIOUS_API_KEY", secret)
    invalid_args = f'{{"password":"{secret}","body":"é"}}'
    raw_args = f'{{"authorization":"{secret}","body":"é"'
    reasoning_block = f"private block {secret}"
    reasoning_kwarg = f"private kwarg {secret}"
    error_text = f"provider parse error {secret}"
    message = messages.AIMessage(
        content=[
            {"type": "reasoning", "text": reasoning_block},
            {"type": "text", "text": "short visible result"},
        ],
        invalid_tool_calls=[{
            "id": "invalid-1",
            "name": f"write_{secret}",
            "args": invalid_args,
            "error": error_text,
            "type": "invalid_tool_call",
        }],
        additional_kwargs={
            "tool_calls": [{
                "id": "raw-1",
                "type": "function",
                "function": {"name": "write_file", "arguments": raw_args},
            }],
            "reasoning_content": reasoning_kwarg,
        },
        usage_metadata={
            "input_tokens": 5,
            "output_tokens": 8192,
            "total_tokens": 8197,
            "output_token_details": {"reasoning": 8000},
        },
        response_metadata={
            "finish_reason": "length",
            "headers": {"authorization": secret},
            "token_usage": {
                "prompt_tokens": True,
                "completion_tokens": 8192,
                "total_tokens": float("nan"),
                "completion_tokens_details": {"reasoning_tokens": 8000},
                "credential": secret,
            },
        },
    )

    sdk_debug.preserve_failure(tmp_path, _failed_result([message]))
    records = _failure_lines(tmp_path)
    persisted = (tmp_path / "messages.jsonl").read_text()
    assert secret not in persisted
    assert invalid_args not in persisted
    assert raw_args not in persisted
    assert reasoning_block not in persisted
    assert reasoning_kwarg not in persisted
    assert error_text not in persisted

    for record in records[:2]:
        assert record["finish_reason"] == "length"
        assert record["usage"] == {
            "input_tokens": 5,
            "output_tokens": 8192,
            "total_tokens": 8197,
            "output_token_details": {"reasoning": 8000},
        }
        assert record["provider_usage"] == {
            "completion_tokens": 8192,
            "completion_tokens_details": {"reasoning_tokens": 8000},
        }
        invalid = record["invalid_tool_calls"]
        assert invalid["count"] == 1
        assert invalid["recorded_count"] == 1
        assert invalid["truncated"] is False
        assert invalid["calls"][0]["name"] == "write_[REDACTED]"
        assert invalid["calls"][0]["arguments"] == {
            "present": True,
            "type": "string",
            "empty": False,
            "characters": len(invalid_args),
            "bytes": len(invalid_args.encode()),
        }
        assert invalid["calls"][0]["error"] == {
            "present": True,
            "type": "string",
        }
        raw = record["raw_tool_calls"]
        assert raw["count"] == 1
        assert raw["recorded_count"] == 1
        assert raw["truncated"] is False
        assert raw["calls"][0]["name"] == "write_file"
        assert raw["calls"][0]["arguments"] == {
            "present": True,
            "type": "string",
            "empty": False,
            "characters": len(raw_args),
            "bytes": len(raw_args.encode()),
        }
        reasoning = record["reasoning_text"]
        assert reasoning == {
            "present": True,
            "carrier_count": 2,
            "text_count": 2,
            "nonempty_text_count": 2,
            "characters": len(reasoning_block) + len(reasoning_kwarg),
            "bytes": len(reasoning_block.encode()) + len(reasoning_kwarg.encode()),
            "truncated": False,
            "empty": False,
        }


@pytest.mark.parametrize(
    ("kind", "field"),
    [("reasoning", "text"), ("reasoning", "reasoning"), ("thinking", "thinking")],
)
def test_failure_reasoning_content_is_metadata_only(tmp_path, kind, field):
    messages = pytest.importorskip("langchain_core.messages")
    private = "The hidden deliberation considers an unpublished acquisition."
    visible = "Visible result"
    sdk_debug.preserve_failure(tmp_path, _failed_result([
        messages.AIMessage(
            content=[
                {"type": kind, field: private},
                {"type": "text", "text": visible},
            ],
            response_metadata={"finish_reason": "length"},
        ),
    ]))

    persisted = (tmp_path / "messages.jsonl").read_text()
    records = _failure_lines(tmp_path)
    assert private not in persisted
    assert visible in persisted
    for record in records[:2]:
        assert record["reasoning_text"] == {
            "present": True,
            "carrier_count": 1,
            "text_count": 1,
            "nonempty_text_count": 1,
            "characters": len(private),
            "bytes": len(private.encode()),
            "truncated": False,
            "empty": False,
        }
    assert records[1]["content"] == [
        {"type": "text", "text": visible},
    ]


def test_failure_terminal_metadata_distinguishes_absent_empty_and_truncated(tmp_path):
    messages = pytest.importorskip("langchain_core.messages")
    absent = tmp_path / "absent"
    absent.mkdir()
    sdk_debug.preserve_failure(absent, _failed_result([
        messages.AIMessage(content="visible"),
    ]))
    absent_summary = _failure_lines(absent)[0]
    assert absent_summary["invalid_tool_calls"] == {
        "present": True, "count": 0, "recorded_count": 0,
        "truncated": False, "calls": [],
    }
    for metadata_field in ("raw_tool_calls", "reasoning_text", "provider_usage"):
        assert metadata_field not in absent_summary

    empty = tmp_path / "empty"
    empty.mkdir()
    sdk_debug.preserve_failure(empty, _failed_result([
        messages.AIMessage(
            content="visible",
            additional_kwargs={"tool_calls": [], "reasoning_content": ""},
        ),
    ]))
    empty_summary = _failure_lines(empty)[0]
    assert empty_summary["raw_tool_calls"] == {
        "present": True, "count": 0, "recorded_count": 0,
        "truncated": False, "calls": [],
    }
    assert empty_summary["reasoning_text"] == {
        "present": True, "carrier_count": 1, "text_count": 1,
        "nonempty_text_count": 0, "characters": 0, "bytes": 0,
        "truncated": False, "empty": True,
    }

    bounded = tmp_path / "bounded"
    bounded.mkdir()
    too_many = [{
        "id": f"invalid-{index}", "name": "", "args": "", "error": None,
        "type": "invalid_tool_call",
    } for index in range(sdk_debug._FAILURE_SUMMARY_ITEMS + 1)]
    sdk_debug.preserve_failure(bounded, _failed_result([
        messages.AIMessage(content="visible", invalid_tool_calls=too_many),
    ]))
    bounded_summary = _failure_lines(bounded)[0]
    invalid = bounded_summary["invalid_tool_calls"]
    assert invalid["count"] == len(too_many)
    assert invalid["recorded_count"] == sdk_debug._FAILURE_SUMMARY_ITEMS
    assert invalid["truncated"] is True
    assert invalid["calls"][0]["name_empty"] is True
    assert invalid["calls"][0]["arguments"]["empty"] is True
    assert invalid["calls"][0]["error"] == {
        "present": True, "type": "null",
    }
