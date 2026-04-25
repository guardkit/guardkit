"""SDK debug preservation for diagnostic post-mortem analysis.

When the ``GUARDKIT_AUTOBUILD_PRESERVE_DEBUG`` environment variable is truthy,
this module preserves the rendered Player/Coach prompt, the SDK options, and
the full SDK message stream to disk under
``<worktree>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/[coach/[test_run/]]``.

Closes the wire-level opacity gap identified in TASK-REV-F4A1 / Diagram 2 so
later analyses can verify Hops D-F (SDK stdin, HTTPS payload, LLM tool-use
decision) with quoted artefacts rather than inferred behaviour.

Default behaviour with the env var unset is zero disk cost — no directory is
created and the helper short-circuits on every call.

The helper must NEVER raise into the AutoBuild hot path. All preservation
failures are logged as warnings and swallowed.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

ENV_VAR = "GUARDKIT_AUTOBUILD_PRESERVE_DEBUG"

_TRUTHY = frozenset({"1", "true", "yes", "y", "on"})

_ROLE_SUBPATH = {
    "player": (),
    "coach": ("coach",),
    "coach_test": ("coach", "test_run"),
}


def preservation_enabled() -> bool:
    """Return True if SDK debug preservation is enabled via env var."""
    raw = os.environ.get(ENV_VAR, "")
    return raw.strip().lower() in _TRUTHY


def _role_segments(role: str) -> tuple[str, ...]:
    if role not in _ROLE_SUBPATH:
        logger.warning(
            "sdk_debug: unknown role %r, falling back to 'player'", role
        )
        role = "player"
    return _ROLE_SUBPATH[role]


def compute_debug_dir(
    workspace_root: Union[str, Path],
    task_id: str,
    turn: int,
    role: str,
) -> Path:
    """Compute the per-turn debug directory path.

    Path layout::

        <workspace_root>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/
        <workspace_root>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/coach/
        <workspace_root>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/coach/test_run/
    """
    base = (
        Path(workspace_root)
        / ".guardkit"
        / "autobuild"
        / task_id
        / "sdk_debug"
        / f"turn_{turn}"
    )
    for seg in _role_segments(role):
        base = base / seg
    return base


def _options_to_jsonable(options: Any) -> Any:
    """Best-effort conversion of ClaudeAgentOptions to a JSON-serialisable view.

    Tries dataclass.asdict, then pydantic model_dump, then __dict__,
    then repr() for non-serialisable fields.
    """
    if options is None:
        return None
    # Dataclass path
    try:
        if dataclasses.is_dataclass(options) and not isinstance(options, type):
            return _coerce_jsonable(dataclasses.asdict(options))
    except Exception:  # noqa: BLE001 — diagnostic-only path
        pass
    # Pydantic v2 path
    if hasattr(options, "model_dump"):
        try:
            return _coerce_jsonable(options.model_dump())
        except Exception:  # noqa: BLE001
            pass
    # Plain object path
    if hasattr(options, "__dict__"):
        try:
            return _coerce_jsonable(dict(options.__dict__))
        except Exception:  # noqa: BLE001
            pass
    return repr(options)


def _coerce_jsonable(obj: Any) -> Any:
    """Walk a structure and replace anything json.dumps would choke on with repr()."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _coerce_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_coerce_jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return repr(obj)


def _event_to_jsonable(event: Any) -> Any:
    """Convert a single SDK message event to a JSON-serialisable dict.

    SDK messages (AssistantMessage, ToolUseBlock, ToolResultBlock,
    ResultMessage, SystemMessage, UserMessage, etc.) are dataclasses or
    plain Python objects. This produces a defensive snapshot that always
    succeeds even for unknown types — diagnostic value over fidelity.
    """
    if event is None:
        return {"type": "None"}

    type_name = type(event).__name__
    payload: dict[str, Any] = {"type": type_name}

    # Dataclass path (covers most SDK messages)
    try:
        if dataclasses.is_dataclass(event) and not isinstance(event, type):
            payload.update(_coerce_jsonable(dataclasses.asdict(event)))
            return payload
    except Exception:  # noqa: BLE001
        pass

    # Pydantic-like path
    if hasattr(event, "model_dump"):
        try:
            payload.update(_coerce_jsonable(event.model_dump()))
            return payload
        except Exception:  # noqa: BLE001
            pass

    # Generic __dict__ path (handles content blocks built ad-hoc)
    if hasattr(event, "__dict__"):
        try:
            payload.update(_coerce_jsonable(dict(event.__dict__)))
            # Also walk a nested .content list of ContentBlocks if the
            # asdict path missed them (some SDK versions don't decorate
            # blocks as dataclasses).
            content = getattr(event, "content", None)
            if content is not None and "content" not in payload:
                payload["content"] = _coerce_jsonable(
                    [_event_to_jsonable(b) for b in content]
                    if isinstance(content, (list, tuple))
                    else _event_to_jsonable(content)
                )
            return payload
        except Exception:  # noqa: BLE001
            pass

    payload["repr"] = repr(event)
    return payload


def preserve_prompt(
    workspace_root: Union[str, Path],
    task_id: str,
    turn: int,
    role: str,
    prompt: str,
    options: Any,
) -> Optional[Path]:
    """Write prompt.txt and options.json for the given role/turn.

    Returns the directory written to, or None if preservation is disabled
    or failed. The returned path can be passed to subsequent
    :func:`preserve_event` calls. Idempotent: an existing turn directory
    is wiped and recreated to avoid stale state from interrupted runs.

    This function never raises into the caller.
    """
    if not preservation_enabled():
        return None
    try:
        debug_dir = compute_debug_dir(workspace_root, task_id, turn, role)
        if debug_dir.exists():
            # Idempotent re-run: wipe any prior turn content. We do this
            # at the leaf (player/coach/test_run) so a new role write in
            # the same turn does not clobber a previously-written role.
            shutil.rmtree(debug_dir, ignore_errors=True)
        debug_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = debug_dir / "prompt.txt"
        prompt_path.write_text(prompt or "", encoding="utf-8")

        options_path = debug_dir / "options.json"
        options_payload = _options_to_jsonable(options)
        options_path.write_text(
            json.dumps(options_payload, indent=2, default=repr) + "\n",
            encoding="utf-8",
        )

        # Pre-create empty messages.jsonl so a turn that crashes before
        # the first stream message still produces an artefact triple.
        messages_path = debug_dir / "messages.jsonl"
        if not messages_path.exists():
            messages_path.write_text("", encoding="utf-8")

        logger.info(
            "sdk_debug: preserved %s prompt for %s turn %s -> %s",
            role,
            task_id,
            turn,
            debug_dir,
        )
        return debug_dir
    except Exception as exc:  # noqa: BLE001 — diagnostic-only path
        logger.warning(
            "sdk_debug: failed to preserve prompt for %s turn %s role=%s: %s",
            task_id,
            turn,
            role,
            exc,
        )
        return None


def preserve_event(debug_dir: Optional[Path], event: Any) -> None:
    """Append one event to messages.jsonl as a single JSON line.

    No-op when ``debug_dir`` is None (preservation disabled or
    :func:`preserve_prompt` failed). Never raises.
    """
    if debug_dir is None:
        return
    try:
        line = json.dumps(_event_to_jsonable(event), default=repr)
        with (debug_dir / "messages.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")
    except Exception as exc:  # noqa: BLE001 — diagnostic-only path
        logger.warning("sdk_debug: failed to preserve event: %s", exc)


__all__ = [
    "ENV_VAR",
    "preservation_enabled",
    "compute_debug_dir",
    "preserve_prompt",
    "preserve_event",
]
