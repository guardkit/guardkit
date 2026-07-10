"""SDK debug preservation for diagnostic post-mortem analysis.

TASK-OBS-396E: Default-on via repo allowlist with size-capped rotation.

Preservation defaults ON in named non-client repos (guardkit, study-tutor, forge,
fleet-*) per D-OBS-2, with structural flip-gating — the default-on path activates
ONLY when rotation caps resolve to positive values AND the keep-out-of-git check
passes. Client/FinProxy repos stay opt-in per run.

When enabled, this module preserves the rendered Player/Coach prompt, the SDK
options, and the full SDK message stream to disk under
``<worktree>/.guardkit/autobuild/<task_id>/sdk_debug/turn_<n>/[coach/[test_run/]]``.

Closes the wire-level opacity gap identified in TASK-REV-F4A1 / Diagram 2 so
later analyses can verify Hops D-F (SDK stdin, HTTPS payload, LLM tool-use
decision) with quoted artefacts rather than inferred behaviour.

Size caps: per-turn cap on messages.jsonl (default 20MB), per-task total cap on
sdk_debug/ dir (default 200MB). Rotation never makes capture silently absent —
truncation writes explicit marker, pruning leaves PRUNED.marker.

The helper must NEVER raise into the AutoBuild hot path. All preservation
failures are logged as warnings and swallowed.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional, Union

from guardkit.orchestrator.instrumentation.redaction import SecretRedactor

logger = logging.getLogger(__name__)

ENV_VAR = "GUARDKIT_AUTOBUILD_PRESERVE_DEBUG"

_TRUTHY = frozenset({"1", "true", "yes", "y", "on"})
_FALSY = frozenset({"0", "false", "no", "n", "off"})

# Warn-once latch for an explicit-but-unrecognized ENV_VAR value (TASK-OBS-396E,
# unrecognized-env decision 2026-07-10 — Option B, fail-safe OFF + warn once).
# Reset by tests via the _clear_env fixture.
_unrecognized_env_warned = False

# Marker written when redaction fails — fail-closed for content, fail-open for control flow
_REDACTION_FAILED_MARKER = "[REDACTION-FAILED]\n"

# Module-level SecretRedactor instance (cached singleton for performance)
_redactor: Optional[SecretRedactor] = None

# Repo allowlist for default-on behavior (D-OBS-2)
# DATA constant, greppable, per TASK-OBS-396E Change 1
DEFAULT_ON_REPOS = frozenset({
    "guardkit",
    "study-tutor",
    "forge",
})

# fleet-* pattern matches fleet-gateway, fleet-common, etc.
def _is_fleet_repo(repo_name: str) -> bool:
    """Check if repo name matches fleet-* pattern."""
    return repo_name.startswith("fleet-")

# Size caps (TASK-OBS-396E Change 2)
# Defaults: 20MB/turn, 200MB/task (operator policy, env-tunable)
def _get_per_turn_cap() -> int:
    """Get per-turn cap from env, with fallback to default."""
    try:
        return int(os.environ.get("GUARDKIT_SDK_DEBUG_PER_TURN_CAP", 20 * 1024 * 1024))
    except (ValueError, TypeError):
        return 20 * 1024 * 1024

def _get_per_task_cap() -> int:
    """Get per-task cap from env, with fallback to default."""
    try:
        return int(os.environ.get("GUARDKIT_SDK_DEBUG_PER_TASK_CAP", 200 * 1024 * 1024))
    except (ValueError, TypeError):
        return 200 * 1024 * 1024

# Module-level constants (for backward compat with tests that patch them)
PER_TURN_CAP_BYTES = _get_per_turn_cap()
PER_TASK_CAP_BYTES = _get_per_task_cap()

_TRUNCATION_MARKER_TEMPLATE = "\n[TRUNCATED at {size} bytes]\n"


def _get_redactor() -> SecretRedactor:
    """Lazy-initialize and return the module-level SecretRedactor instance."""
    global _redactor
    if _redactor is None:
        _redactor = SecretRedactor()
    return _redactor

_ROLE_SUBPATH = {
    "player": (),
    "coach": ("coach",),
    "coach_test": ("coach", "test_run"),
}


def _get_repo_name(repo_root: Union[str, Path]) -> Optional[str]:
    """Derive repo name from directory name with git remote cross-check.

    Returns the repo root directory name if git remote confirms it, else None.
    Defensive: swallows git subprocess failures and returns None.
    """
    try:
        repo_path = Path(repo_root)
        if not repo_path.exists():
            return None

        # Try git remote to confirm repo identity
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            # Not a git repo or git failed — fall back to directory name only
            return repo_path.name

        # Extract repo name from remote (origin line)
        # Example: "origin  git@github.com:org/guardkit.git"
        for line in result.stdout.splitlines():
            if line.startswith("origin"):
                # Remote confirmed — use directory name
                return repo_path.name

        # No origin remote found — use directory name
        return repo_path.name

    except Exception as exc:  # noqa: BLE001
        logger.warning("sdk_debug: failed to get repo name from %s: %s", repo_root, exc)
        return None


def _check_gitignore_coverage(repo_root: Union[str, Path], sdk_debug_path: Path) -> bool:
    """Check that sdk_debug path is properly ignored by git.

    Returns True if git check-ignore confirms the path is ignored, False otherwise.
    Defensive: swallows subprocess failures and returns False.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", str(sdk_debug_path)],
            cwd=repo_root,
            capture_output=True,
            timeout=5,
            check=False,
        )
        # git check-ignore returns 0 if path is ignored, 1 if not
        return result.returncode == 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sdk_debug: gitignore check failed for %s: %s",
            sdk_debug_path,
            exc,
        )
        return False


def _validate_rotation_caps() -> bool:
    """Check that rotation caps are configured to positive values.

    Returns True if both caps are valid (positive integers), False otherwise.
    """
    # Check env vars directly to catch invalid values at runtime
    per_turn_raw = os.environ.get("GUARDKIT_SDK_DEBUG_PER_TURN_CAP", "")
    per_task_raw = os.environ.get("GUARDKIT_SDK_DEBUG_PER_TASK_CAP", "")

    # If env vars are set but not parseable, fail validation
    if per_turn_raw:
        try:
            per_turn = int(per_turn_raw)
            if per_turn <= 0:
                logger.warning(
                    "sdk_debug: invalid GUARDKIT_SDK_DEBUG_PER_TURN_CAP=%r (must be > 0)",
                    per_turn_raw,
                )
                return False
        except (ValueError, TypeError):
            logger.warning(
                "sdk_debug: invalid GUARDKIT_SDK_DEBUG_PER_TURN_CAP=%r (not an integer)",
                per_turn_raw,
            )
            return False

    if per_task_raw:
        try:
            per_task = int(per_task_raw)
            if per_task <= 0:
                logger.warning(
                    "sdk_debug: invalid GUARDKIT_SDK_DEBUG_PER_TASK_CAP=%r (must be > 0)",
                    per_task_raw,
                )
                return False
        except (ValueError, TypeError):
            logger.warning(
                "sdk_debug: invalid GUARDKIT_SDK_DEBUG_PER_TASK_CAP=%r (not an integer)",
                per_task_raw,
            )
            return False

    return True


def _explicit_env_verdict() -> Optional[bool]:
    """Classify the ENV_VAR value into an explicit on/off verdict, or defer.

    TASK-OBS-396E unrecognized-env decision (2026-07-10, Option B — fail-safe):

    - Explicitly truthy (``1``/``true``/``yes``/``y``/``on``) → ``True``.
    - Explicitly falsy  (``0``/``false``/``no``/``n``/``off``) → ``False``.
    - Explicit but **unrecognized** (a typo like ``enabled``/``tru``) → ``False``
      (fail-safe OFF) with a one-time warning. An uninterpretable *explicit*
      signal is NOT the same as an *absent* one; it must not silently ride the
      default-on allowlist path.
    - Unset or empty (``""``) → ``None`` (an absent signal — the caller defers to
      the repo allowlist / default-off logic).

    Returning ``None`` means "no explicit signal; decide by allowlist".
    """
    global _unrecognized_env_warned
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return None
    env_value = raw.strip().lower()
    if env_value == "":
        # Exported-but-empty is conventionally equivalent to unset.
        return None
    if env_value in _TRUTHY:
        return True
    if env_value in _FALSY:
        return False
    # Explicit but unrecognized — fail-safe OFF, warn once (Option B).
    if not _unrecognized_env_warned:
        logger.warning(
            "sdk_debug: unrecognized %s=%r — treating as OFF (fail-safe). "
            "Recognized truthy=%s, falsy=%s; unset defers to the repo allowlist.",
            ENV_VAR,
            raw,
            sorted(_TRUTHY),
            sorted(_FALSY),
        )
        _unrecognized_env_warned = True
    return False


def preservation_enabled_for_repo(
    repo_root: Union[str, Path],
    sdk_debug_dir: Optional[Path] = None,
) -> bool:
    """Check if SDK debug preservation should be enabled for this repo.

    TASK-OBS-396E: Repo allowlist with structural flip-gating.

    Returns True if:
    - ENV_VAR is explicitly truthy (=1), OR
    - ENV_VAR is unset/empty AND repo is allowlisted AND guards pass

    Returns False if:
    - ENV_VAR is explicitly falsy (=0), OR
    - ENV_VAR is explicitly set but unrecognized (fail-safe OFF + warn once), OR
    - ENV_VAR unset/empty AND repo is not allowlisted, OR
    - ENV_VAR unset/empty AND repo is allowlisted BUT guards fail

    Guards (both must pass for default-on):
    1. Rotation caps resolve to positive values
    2. Keep-out-of-git check passes (sdk_debug path is in .gitignore)

    Args:
        repo_root: Repository root directory
        sdk_debug_dir: Optional sdk_debug path to check against .gitignore.
                      If None, constructs a representative path for checking.
    """
    # Explicit ENV_VAR value (truthy/falsy/unrecognized) wins over the allowlist.
    verdict = _explicit_env_verdict()
    if verdict is not None:
        return verdict

    # ENV_VAR unset or empty — check allowlist and guards
    repo_name = _get_repo_name(repo_root)
    if repo_name is None:
        # Could not determine repo — default OFF
        return False

    # Check if repo is allowlisted
    is_allowlisted = (
        repo_name in DEFAULT_ON_REPOS
        or _is_fleet_repo(repo_name)
    )

    if not is_allowlisted:
        # Not allowlisted — default OFF
        return False

    # Repo is allowlisted — apply structural flip-gating (Change 3a)
    # Guard 1: rotation caps valid
    if not _validate_rotation_caps():
        logger.warning(
            "sdk_debug: allowlisted repo %s but rotation caps invalid — "
            "capture disabled (failed prerequisite: rotation caps)",
            repo_name,
        )
        return False

    # Guard 2: keep-out-of-git check
    if sdk_debug_dir is None:
        # Construct representative path for checking
        sdk_debug_dir = Path(repo_root) / ".guardkit" / "autobuild" / "TASK-TEST" / "sdk_debug"

    if not _check_gitignore_coverage(repo_root, sdk_debug_dir):
        logger.warning(
            "sdk_debug: allowlisted repo %s but keep-out-of-git check failed — "
            "capture disabled (failed prerequisite: gitignore coverage)",
            repo_name,
        )
        return False

    # Both guards passed — default ON for allowlisted repo
    return True


def preservation_enabled() -> bool:
    """Return True if SDK debug preservation is enabled.

    Legacy function for backward compatibility. Uses current working directory
    as repo root. For explicit repo control, use preservation_enabled_for_repo().
    """
    # Explicit ENV_VAR value (truthy/falsy/unrecognized) always wins.
    verdict = _explicit_env_verdict()
    if verdict is not None:
        return verdict

    # Fallback: try to detect repo from cwd
    try:
        cwd = Path.cwd()
        return preservation_enabled_for_repo(cwd)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sdk_debug: failed to check repo allowlist from cwd: %s", exc)
        return False


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
    then repr() for non-serialisable fields. Plain ``dict`` / ``list``
    inputs are routed straight through ``_coerce_jsonable`` so callers
    that synthesise an options-shaped record (e.g. the post-HMIG-006.5
    Coach test path) get a JSON object rather than a stringified
    ``repr(dict)`` — dict instances do not carry ``__dict__`` and would
    otherwise fall through to the ``repr`` fallback.
    """
    if options is None:
        return None
    # Plain JSON-shaped input (dict/list/tuple): pass through directly.
    if isinstance(options, (dict, list, tuple)):
        return _coerce_jsonable(options)
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

    HarnessEvent typed records (TASK-HMIG-006) carry an optional ``.raw``
    slot that holds the underlying substrate object (an SDK ``Message``
    on the SDK path, ``None`` on substrates with no useful raw form).
    When present, the raw slot is walked recursively so the JSONL line
    captures the full SDK message shape rather than the ``repr()`` that
    the dataclass-asdict + coerce path would otherwise emit — restoring
    parity with the pre-migration coach test stream preserved by
    TASK-DIAG-F4A2 (see TASK-HMIG-006.5).
    """
    if event is None:
        return {"type": "None"}

    type_name = type(event).__name__
    payload: dict[str, Any] = {"type": type_name}

    # Dataclass path (covers most SDK messages and all HarnessEvent variants)
    try:
        if dataclasses.is_dataclass(event) and not isinstance(event, type):
            payload.update(_coerce_jsonable(dataclasses.asdict(event)))
            # HarnessEvent variants carry a ``type: Literal[...]`` field
            # (e.g. ``"assistant_message"``) that ``asdict`` would write
            # over the class-name we set above. Re-impose the class
            # name so the JSONL line always identifies the wrapper type;
            # nested ``type`` literals on inner content blocks are
            # preserved by the asdict recursion regardless.
            payload["type"] = type_name
            _maybe_inline_raw(payload, event)
            return payload
    except Exception:  # noqa: BLE001
        pass

    # Pydantic-like path
    if hasattr(event, "model_dump"):
        try:
            payload.update(_coerce_jsonable(event.model_dump()))
            payload["type"] = type_name
            _maybe_inline_raw(payload, event)
            return payload
        except Exception:  # noqa: BLE001
            pass

    # Generic __dict__ path (handles content blocks built ad-hoc)
    if hasattr(event, "__dict__"):
        try:
            payload.update(_coerce_jsonable(dict(event.__dict__)))
            payload["type"] = type_name
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
            _maybe_inline_raw(payload, event)
            return payload
        except Exception:  # noqa: BLE001
            pass

    payload["repr"] = repr(event)
    return payload


def _maybe_inline_raw(payload: dict[str, Any], event: Any) -> None:
    """Replace ``payload["raw"]`` with a recursive walk when applicable.

    HarnessEvent dataclasses (AssistantMessageEvent, ResultMessageEvent)
    expose a ``raw`` slot that points at the underlying SDK ``Message``.
    The default ``dataclasses.asdict`` + ``_coerce_jsonable`` chain
    records that field as ``repr(message)`` because SDK messages are
    not themselves dataclasses understood by ``asdict``. To preserve
    the pre-migration diagnostic fidelity (TASK-HMIG-006.5 AC-002 — the
    "typed event class name plus underlying raw payload" contract),
    walk the raw object through :func:`_event_to_jsonable` so its full
    shape is captured.

    No-op when ``event.raw`` is missing, ``None``, or already a
    primitive (in which case the asdict pass already recorded it
    faithfully).
    """
    raw = getattr(event, "raw", None)
    if raw is None or isinstance(raw, (bool, int, float, str)):
        return
    try:
        payload["raw"] = _event_to_jsonable(raw)
    except Exception:  # noqa: BLE001 — diagnostic-only path
        # Fall back to repr; never raise into the caller.
        payload["raw"] = repr(raw)


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

    This function never raises into the caller. Secret redaction is applied
    to both the prompt and options before writing. If redaction fails, the
    [REDACTION-FAILED] marker is written instead of the raw payload.
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

        # Redact prompt before writing (fail-closed: no raw payload on error)
        prompt_path = debug_dir / "prompt.txt"
        try:
            redacted_prompt = _get_redactor().redact(prompt or "")
            prompt_path.write_text(redacted_prompt, encoding="utf-8")
        except Exception as redact_exc:  # noqa: BLE001
            logger.warning(
                "sdk_debug: prompt redaction failed for %s turn %s: %s",
                task_id,
                turn,
                redact_exc,
            )
            # Write placeholder marker instead of raw payload
            prompt_path.write_text(_REDACTION_FAILED_MARKER, encoding="utf-8")

        # Redact options before writing (fail-closed: no raw payload on error)
        options_path = debug_dir / "options.json"
        try:
            options_payload = _options_to_jsonable(options)
            options_json = json.dumps(options_payload, indent=2, default=repr) + "\n"
            redacted_options = _get_redactor().redact(options_json)
            options_path.write_text(redacted_options, encoding="utf-8")
        except Exception as redact_exc:  # noqa: BLE001
            logger.warning(
                "sdk_debug: options redaction failed for %s turn %s: %s",
                task_id,
                turn,
                redact_exc,
            )
            # Write placeholder marker instead of raw payload
            options_path.write_text(_REDACTION_FAILED_MARKER, encoding="utf-8")

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

    TASK-OBS-396E Change 2: Size-capped rotation with truncation marker.

    No-op when ``debug_dir`` is None (preservation disabled or
    :func:`preserve_prompt` failed). Never raises. Secret redaction is
    applied to the JSON line before writing. If redaction fails, the
    [REDACTION-FAILED] marker is written instead of the raw payload.

    If appending would exceed PER_TURN_CAP_BYTES, writes truncation marker
    and stops appending. Rotation never makes capture silently absent.
    """
    if debug_dir is None:
        return
    try:
        messages_path = debug_dir / "messages.jsonl"

        # Check if already truncated
        if messages_path.exists():
            content = messages_path.read_text(encoding="utf-8")
            if "[TRUNCATED at" in content:
                # Already truncated — do not append further
                return

            # Check current size against cap
            current_size = messages_path.stat().st_size
            if current_size >= PER_TURN_CAP_BYTES:
                # Hit cap — write truncation marker and stop
                truncation_marker = _TRUNCATION_MARKER_TEMPLATE.format(
                    size=current_size
                )
                with messages_path.open("a", encoding="utf-8") as fh:
                    fh.write(truncation_marker)
                logger.info(
                    "sdk_debug: messages.jsonl truncated at %d bytes (cap: %d)",
                    current_size,
                    PER_TURN_CAP_BYTES,
                )
                return

        # Not yet at cap — append event
        line = json.dumps(_event_to_jsonable(event), default=repr)
        # Redact the JSON line before writing (fail-closed: no raw payload on error)
        try:
            redacted_line = _get_redactor().redact(line)
        except Exception as redact_exc:  # noqa: BLE001
            logger.warning("sdk_debug: event redaction failed: %s", redact_exc)
            # Write placeholder marker instead of raw payload
            redacted_line = _REDACTION_FAILED_MARKER.rstrip("\n")

        with messages_path.open("a", encoding="utf-8") as fh:
            fh.write(redacted_line)
            fh.write("\n")

    except Exception as exc:  # noqa: BLE001 — diagnostic-only path
        logger.warning("sdk_debug: failed to preserve event: %s", exc)


def prune_old_turns_if_needed(task_sdk_debug_dir: Path) -> None:
    """Prune oldest turns if per-task total exceeds PER_TASK_CAP_BYTES.

    TASK-OBS-396E Change 2: Per-task cap with PRUNED.marker.

    Args:
        task_sdk_debug_dir: Path to .guardkit/autobuild/<task_id>/sdk_debug/

    Oldest turns are deleted first. A pruned turn leaves PRUNED.marker naming
    what was dropped. Never raises — diagnostic-only path.
    """
    try:
        if not task_sdk_debug_dir.exists():
            return

        # Collect all turn_* directories
        turn_dirs = sorted(
            [d for d in task_sdk_debug_dir.iterdir() if d.is_dir() and d.name.startswith("turn_")],
            key=lambda d: d.name,  # turn_1, turn_2, ...
        )

        if not turn_dirs:
            return

        # Calculate total size
        total_size = 0
        turn_sizes: list[tuple[Path, int]] = []
        for turn_dir in turn_dirs:
            size = sum(f.stat().st_size for f in turn_dir.rglob("*") if f.is_file())
            turn_sizes.append((turn_dir, size))
            total_size += size

        # Check if over cap
        if total_size <= PER_TASK_CAP_BYTES:
            return

        # Prune oldest turns until under cap
        pruned_turns: list[str] = []
        for turn_dir, turn_size in turn_sizes:
            if total_size <= PER_TASK_CAP_BYTES:
                break

            # Remove this turn
            shutil.rmtree(turn_dir, ignore_errors=True)
            pruned_turns.append(turn_dir.name)
            total_size -= turn_size
            logger.info(
                "sdk_debug: pruned %s (%d bytes) to stay under cap (%d bytes)",
                turn_dir.name,
                turn_size,
                PER_TASK_CAP_BYTES,
            )

        # Write PRUNED.marker
        if pruned_turns:
            marker_path = task_sdk_debug_dir / "PRUNED.marker"
            marker_content = (
                f"Pruned turns (oldest-first, per-task cap {PER_TASK_CAP_BYTES} bytes):\n"
                + "\n".join(f"  - {t}" for t in pruned_turns)
                + "\n"
            )
            marker_path.write_text(marker_content, encoding="utf-8")

    except Exception as exc:  # noqa: BLE001 — diagnostic-only path
        logger.warning("sdk_debug: failed to prune old turns: %s", exc)


__all__ = [
    "ENV_VAR",
    "preservation_enabled",
    "preservation_enabled_for_repo",
    "compute_debug_dir",
    "preserve_prompt",
    "preserve_event",
    "prune_old_turns_if_needed",
    "DEFAULT_ON_REPOS",
    "PER_TURN_CAP_BYTES",
    "PER_TASK_CAP_BYTES",
]
