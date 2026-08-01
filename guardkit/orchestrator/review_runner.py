"""Headless review leg — the engine behind ``guardkit task-review``.

The pipeline's conductor spawns ``guardkit task-review …`` as a subprocess and
scrapes four text markers off its stdout. This module is the body of that
subcommand: it runs a purpose-built, *subtractive* distillation of the attended
``/task-review`` workflow on a local seat, then prints the marker block from
files it verified on disk.

Design pins (``docs/leg-invocation-design-pass-2026-08-02.md``):

* **Composition, not a new invocation path.** The model call goes through
  :func:`guardkit.orchestrator.specialist_invocations.run_specialist`, which
  delegates to the hardened chokepoint ``AgentInvoker._invoke_with_role`` and
  inherits its cancel monitor, heartbeat, instrumentation, no-activity watchdog,
  child-process reaping and never-raises contract. That chokepoint is also the
  only ``select_harness`` call site that passes ``cwd=`` (``agent_invoker.py``
  ~4525-4559); the design-phase call site in ``task_work_interface.py`` omits it
  and dies under the default langgraph harness. Never copy that one.
* **The leg prints the markers, not the model** (§e.3). Model-authored paths on
  stdout are an injection route into the pipeline's *planning* — the printed
  paths become the ``--task-id`` of the next dispatches. So the leg prints only
  paths that exist on disk **and** were written during this run.
* **Nothing is silently stripped** (§c.1). Every interactive checkpoint of the
  attended workflow carries an explicit disposition, reproduced in the report
  and in the per-leg receipt as the phases-not-run list.

Exit semantics are owned by the CLI (:mod:`guardkit.cli.task_review`); this
module returns a typed outcome and never calls :func:`sys.exit`.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from guardkit.orchestrator.prompts import load_protocol
from guardkit.orchestrator.specialist_invocations import run_specialist
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError, TaskParseError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

#: Internal SDK budget. Deliberately under the dispatcher's 600 s SIGKILL
#: (``forge/src/forge/adapters/guardkit/run.py:64``) so an over-long leg fails
#: *honestly* — a written partial plus exit 2 — instead of being killed with no
#: stdout at all (design §d stage 1, item 6).
DEFAULT_SDK_TIMEOUT_SECONDS = 480

#: The review leg runs as the read-only reviewer profile
#: (``coach`` / ``bypassPermissions`` — see ``_SPECIALIST_INVOCATION_PROFILE``).
REVIEW_SPECIALIST_NAME = "code-reviewer"

#: Read / Grep / Glob / Write only. No Bash, no Edit, no network — which is also
#: why the review leg crosses to non-Python repos free (design §g).
REVIEW_ALLOWED_TOOLS: Tuple[str, ...] = ("Read", "Grep", "Glob", "Write")

#: MIRROR of the pipeline's fix-task identifier shape,
#: ``forge/src/forge/cli/_serve_deps_stage_log.py:398``
#: (``default_fix_tasks_extractor``). A printed artefact whose *stem* does not
#: match this is silently dropped by the pipeline — which would end the journey
#: looking "clean". The leg therefore applies the same test as an admission
#: filter, so the mismatch surfaces here as a named failure instead of there as
#: silence.
FIX_TASK_STEM_RE = re.compile(r"^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$")

#: Provider prefixes that mean "a frontier vendor's API" for the M0 fence.
#: ``openai`` is handled separately: the fleet's own route *is*
#: ``init_chat_model("openai:<alias>")`` against a local ``OPENAI_BASE_URL``, so
#: the prefix alone proves nothing — see
#: :func:`guardkit.cli.task_review.resolve_m0_violation`.
FRONTIER_PROVIDER_PREFIXES: Tuple[str, ...] = (
    "anthropic",
    "azure_openai",
    "azure-openai",
    "bedrock",
    "bedrock_converse",
    "cohere",
    "deepseek",
    "fireworks",
    "google",
    "google_genai",
    "google_vertexai",
    "gemini",
    "groq",
    "mistralai",
    "openrouter",
    "perplexity",
    "together",
    "vertexai",
    "xai",
)

#: §c.1's dispositions, verbatim, as data. Written into the receipt so a reader
#: can see what did not happen; also rendered into the protocol injection.
PHASES_NOT_RUN: Tuple[Dict[str, str], ...] = (
    {
        "checkpoint": "Phase 0 — ad-hoc task creation from free text",
        "spec_pin": "task-review.md:93-101",
        "disposition": "REFUSED",
        "detail": (
            "The leg is id-form only. A --task-id with no task file on disk "
            "exits 2 naming the id; the leg never invents a task."
        ),
    },
    {
        "checkpoint": "Phase 1.6 — clarification questioner (Context A)",
        "spec_pin": "task-review-ext.md:573-641 (gating :325-330)",
        "disposition": "AUTO-ANSWERED",
        "answer_used": "defaults applied (unattended)",
        "detail": (
            "--defaults semantics. The report's Context Used section carries "
            "the mandatory line 'clarification: defaults applied (unattended)'."
        ),
    },
    {
        "checkpoint": "Phase 1.5 — fleet memory, MCP tier",
        "spec_pin": "task-review-ext.md:662-794 (never-blocks :826)",
        "disposition": "DECLARED-ABSENT",
        "detail": "No MCP server exists inside a headless harness run.",
    },
    {
        "checkpoint": "Phase 1.5 — fleet memory, CLI tier",
        "spec_pin": "guardkit memory search",
        "disposition": "ATTEMPTED-AND-RECORDED",
        "detail": (
            "Attempted by the leg before the model call; the outcome is "
            "recorded verbatim under fleet_memory_cli in this receipt."
        ),
    },
    {
        "checkpoint": "Phase 4.5 — knowledge capture (3-5 free-text questions)",
        "spec_pin": "task-review-ext.md:893-1018",
        "disposition": "DECLARED-ABSENT",
        "detail": "Blocking human Q&A; no defensible default exists.",
    },
    {
        "checkpoint": "Phase 5 — [A]ccept / [R]evise / [I]mplement / [C]ancel",
        "spec_pin": "task-review.md:146-154",
        "disposition": "RELOCATED",
        "relocated_to": (
            "the pipeline's own review gate (already attended; review rows "
            "carry gate_decision)"
        ),
        "detail": (
            "The unattended leg does not decide, it produces: findings present "
            "-> the [I]mplement path via implement_orchestrator."
            "handle_implement_option_sync; findings absent -> the [A]ccept "
            "path, empty artefact section plus an explicit clean line."
        ),
    },
)

#: The positively-clean sentence the report must carry when there are no
#: findings. An empty artefact section alone is indistinguishable downstream
#: from a leg that found problems and failed to print them (§c.1).
CLEAN_REVIEW_LINE = (
    "No findings. This review is positively clean — every item in scope was "
    "read and no defect was found."
)

#: Coordinator cure (LI coach finding 4): the exact-substring match on a
#: 100+ char em-dash sentence is the most likely first-crossing failure — a
#: local seat paraphrasing ONE character flips a genuinely clean review into
#: exit 2. The check now accepts the short un-mangleable sentinel token as
#: well; the protocol instructs the model to print BOTH.
CLEAN_REVIEW_SENTINEL = "CLEAN-REVIEW: NO FINDINGS"


def _clean_line_present(report_text: str) -> bool:
    """Whitespace/case-tolerant: the sentinel token or the full sentence."""
    import re as _re

    flat = " ".join(report_text.split()).lower()
    if " ".join(CLEAN_REVIEW_SENTINEL.split()).lower() in flat:
        return True
    return " ".join(CLEAN_REVIEW_LINE.split()).lower() in flat


# ---------------------------------------------------------------------------
# Typed results
# ---------------------------------------------------------------------------


@dataclass
class ContextPayload:
    """One resolved ``--context`` value (§c.4 — the flag carries two kinds)."""

    raw: str
    kind: str  # "file" | "inline-json" | "inline-text" | "unreadable"
    text: str = ""
    parsed: Optional[Any] = None
    note: Optional[str] = None

    def as_receipt_entry(self) -> Dict[str, Any]:
        entry: Dict[str, Any] = {"kind": self.kind, "value": self.raw[:400]}
        if self.note:
            entry["note"] = self.note
        if self.kind == "inline-json" and isinstance(self.parsed, dict):
            entry["json_keys"] = sorted(str(k) for k in self.parsed)
        return entry


@dataclass
class ReviewLegOutcome:
    """Everything the CLI needs to print markers, write a receipt and exit."""

    task_id: str
    status: str  # "clean" | "findings" | "timeout" | "failed" | "inconsistent"
    exit_code: int
    duration_seconds: float
    model: Optional[str]
    seat: Optional[str]
    findings: List[Dict[str, Any]] = field(default_factory=list)
    coach_score: Optional[float] = None
    fix_task_paths: List[str] = field(default_factory=list)
    rejected_artefacts: List[Dict[str, str]] = field(default_factory=list)
    report_path: Optional[str] = None
    findings_file: Optional[str] = None
    consistency_check: str = "not-run"
    clean_line_present: bool = False
    error: Optional[str] = None
    fleet_memory_cli: Dict[str, Any] = field(default_factory=dict)
    context_payloads: List[ContextPayload] = field(default_factory=list)
    producer: Dict[str, Any] = field(default_factory=dict)

    @property
    def emits_markers(self) -> bool:
        """Markers are printed only on the exit-0 path.

        The pipeline's parser ignores stdout shape entirely when
        ``exit_code != 0`` (``forge/.../parser.py:109-114`), so printing a
        marker block beside a failure would be noise at best and a
        half-truth at worst.
        """
        return self.exit_code == 0


# ---------------------------------------------------------------------------
# §c.4 — --context, both payload kinds
# ---------------------------------------------------------------------------


def load_context_payloads(
    values: Sequence[str], *, repo_root: Path
) -> List[ContextPayload]:
    """Resolve each ``--context`` value into a typed payload.

    The flag carries **two payload kinds on one option**: absolute paths from
    the pipeline's manifest resolver, and inline text/JSON forward context
    including the ``{"failure_pack": {...}}`` blob.

    Rule (§c.4): file if readable, else inline text with a ``json.loads``
    attempt. **Never fail on an unreadable value** — the manifest resolver
    itself degrades an unresolvable entry to a warning, and a leg stricter than
    its caller turns a warning into a dead journey.
    """
    payloads: List[ContextPayload] = []
    for raw in values or ():
        if raw is None:
            continue
        text = str(raw)
        candidate: Optional[Path] = None
        try:
            path = Path(text)
            if not path.is_absolute():
                path = repo_root / path
            if path.is_file():
                candidate = path
        except (OSError, ValueError):
            candidate = None

        if candidate is not None:
            try:
                payloads.append(
                    ContextPayload(
                        raw=text,
                        kind="file",
                        text=candidate.read_text(encoding="utf-8", errors="replace"),
                    )
                )
                continue
            except OSError as exc:
                payloads.append(
                    ContextPayload(
                        raw=text,
                        kind="unreadable",
                        note=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

        parsed: Optional[Any] = None
        kind = "inline-text"
        try:
            parsed = json.loads(text)
            kind = "inline-json"
        except (ValueError, TypeError):
            parsed = None
        payloads.append(ContextPayload(raw=text, kind=kind, text=text, parsed=parsed))
    return payloads


# ---------------------------------------------------------------------------
# Phase 1.5 CLI tier — attempted and recorded, never blocking
# ---------------------------------------------------------------------------


def attempt_fleet_memory_cli(
    query: str, *, repo_root: Path, timeout: float = 20.0
) -> Dict[str, Any]:
    """Attempt the fleet-memory **CLI** tier and record whatever happened.

    Never raises and never blocks the leg: the attended workflow's own rule is
    that memory never blocks (``task-review-ext.md:826``). Set
    ``GUARDKIT_REVIEW_MEMORY_CLI=0`` to skip the attempt (recorded as such).
    """
    if os.environ.get("GUARDKIT_REVIEW_MEMORY_CLI", "1") == "0":
        return {
            "attempted": False,
            "reason": "disabled via GUARDKIT_REVIEW_MEMORY_CLI=0",
        }
    try:
        completed = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["guardkit", "memory", "search", query],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 — never blocks the leg
        return {"attempted": True, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "attempted": True,
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "output": (completed.stdout or "")[-4000:],
        "stderr_tail": (completed.stderr or "")[-1000:],
    }


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def render_phases_not_run_table() -> str:
    """Render §c.1's dispositions as the markdown table the report reproduces."""
    rows = ["| Checkpoint | Spec pin | Disposition |", "|---|---|---|"]
    for phase in PHASES_NOT_RUN:
        rows.append(
            f"| {phase['checkpoint']} | `{phase['spec_pin']}` | "
            f"**{phase['disposition']}** |"
        )
    return "\n".join(rows)


def render_review_prompt(
    *,
    task_id: str,
    task: Dict[str, Any],
    report_path: Path,
    findings_path: Path,
    context_payloads: Sequence[ContextPayload],
    feature_yaml: Optional[str],
    fleet_memory_cli: Dict[str, Any],
    mode: str,
    depth: str,
) -> str:
    """Assemble the full prompt: protocol + injected context."""
    protocol = load_protocol("task_review_protocol")

    parts: List[str] = [
        protocol,
        "",
        "### Leg parameters",
        "",
        f"- TASK_ID: `{task_id}`",
        f"- review mode: `{mode}`",
        f"- review depth: `{depth}`",
        f"- review report to write: `{report_path}`",
        f"- findings file to write: `{findings_path}`",
        "",
        "### Task file",
        "",
        f"- path: `{task.get('file_path')}`",
        f"- title: {task.get('frontmatter', {}).get('title', '(untitled)')}",
        "",
        "```markdown",
        str(task.get("content", "")),
        "```",
        "",
        "### Acceptance criteria (from the task file)",
        "",
    ]
    criteria = task.get("acceptance_criteria") or []
    if criteria:
        parts.extend(f"- {c}" for c in criteria)
    else:
        parts.append("- (none declared in the task file)")

    parts.extend(["", "### Fleet memory — CLI tier outcome", "", "```json"])
    parts.append(json.dumps(fleet_memory_cli, indent=2, default=str))
    parts.extend(["```", ""])

    if feature_yaml:
        parts.extend(["### Feature YAML", "", f"- path: `{feature_yaml}`", ""])

    parts.append("### Context documents and forward context")
    parts.append("")
    if not context_payloads:
        parts.append("(none supplied)")
    for idx, payload in enumerate(context_payloads, start=1):
        parts.append(f"#### Context {idx} — {payload.kind}")
        parts.append("")
        if payload.kind == "unreadable":
            parts.append(
                f"`{payload.raw}` could not be read ({payload.note}). "
                "Recorded and ignored — an unreadable context is a warning, "
                "never a failure."
            )
        elif payload.kind == "file":
            parts.extend(["```", f"# {payload.raw}", payload.text[:20000], "```"])
        else:
            parts.extend(["```", payload.text[:20000], "```"])
        parts.append("")

    parts.extend(
        [
            "### Phases Not Run — reproduce this table in the report",
            "",
            render_phases_not_run_table(),
            "",
        ]
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Findings file
# ---------------------------------------------------------------------------


def read_findings_file(path: Path) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[str]]:
    """Read the model's findings file into ``(findings, coach_score, error)``.

    Accepts either a bare JSON array or an object with a ``findings`` key.
    Non-object elements are dropped — the pipeline's own extractor keeps only
    dicts (``parser.py:241``), so anything else could never survive the trip.
    """
    if not path.is_file():
        return [], None, f"findings file not written: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], None, f"findings file unreadable/malformed: {type(exc).__name__}: {exc}"

    coach_score: Optional[float] = None
    if isinstance(payload, dict):
        raw_findings = payload.get("findings", [])
        raw_score = payload.get("coach_score")
        if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool):
            coach_score = float(raw_score)
    elif isinstance(payload, list):
        raw_findings = payload
    else:
        return [], None, "findings file is neither a JSON object nor a JSON array"

    if not isinstance(raw_findings, list):
        return [], coach_score, "'findings' is not a JSON array"
    findings = [item for item in raw_findings if isinstance(item, dict)]
    return findings, coach_score, None


# ---------------------------------------------------------------------------
# §e.3 — artefact discipline
# ---------------------------------------------------------------------------


def admit_fix_task_paths(
    candidates: Sequence[Path],
    *,
    written_this_run: Sequence[Path],
    report_path: Path,
) -> Tuple[List[str], List[Dict[str, str]]]:
    """Filter candidate artefacts down to what may legally be printed.

    Four tests, all of which must pass (§e.3, §e.4):

    1. the path was **written by this leg in this run**;
    2. the path **exists on disk**;
    3. it is **not the review report** — the report's own stem
       (``TASK-REV-a1b2c3-review-report``) *matches* the pipeline's fix-task
       regex, so listing it would inject a phantom fix task and the conductor
       would dispatch a work leg against a review report;
    4. its stem matches the pipeline's fix-task identifier shape — otherwise
       the pipeline drops it silently and the journey ends looking clean.

    Returns ``(admitted_paths, rejections)``; rejections carry a reason so the
    receipt can name what was withheld and why.
    """
    written = {p.resolve() for p in written_this_run}
    report_resolved = report_path.resolve() if report_path else None

    admitted: List[str] = []
    rejected: List[Dict[str, str]] = []
    seen: set[str] = set()

    for candidate in candidates:
        resolved = candidate.resolve()
        as_str = str(resolved)
        if report_resolved is not None and resolved == report_resolved:
            rejected.append(
                {
                    "path": as_str,
                    "reason": (
                        "review report — never an artefact line (stem-collision "
                        "guard, design §c.1/§e.4)"
                    ),
                }
            )
            continue
        if resolved not in written:
            rejected.append(
                {"path": as_str, "reason": "not written by this leg in this run"}
            )
            continue
        if not resolved.is_file():
            rejected.append({"path": as_str, "reason": "does not exist on disk"})
            continue
        if not FIX_TASK_STEM_RE.match(resolved.stem):
            rejected.append(
                {
                    "path": as_str,
                    "reason": (
                        "stem does not match the pipeline's fix-task id shape "
                        f"{FIX_TASK_STEM_RE.pattern!r} — the pipeline would "
                        "drop it silently"
                    ),
                }
            )
            continue
        if as_str in seen:
            continue
        seen.add(as_str)
        admitted.append(as_str)

    return admitted, rejected


# ---------------------------------------------------------------------------
# §c.1 — the internal consistency check
# ---------------------------------------------------------------------------


def evaluate_consistency(
    *, findings: Sequence[Dict[str, Any]], fix_task_paths: Sequence[str]
) -> Tuple[str, Optional[str]]:
    """Return ``(verdict, failure_reason)`` for the pre-print consistency check.

    An empty ``## Artefacts`` section is indistinguishable downstream from a
    clean review: the extractor returns ``()``, the row records
    ``fix_tasks: []``, and the planner terminates ``CLEAN_REVIEW``. So a leg
    that finds problems and writes no fix tasks must **exit 2**, never print a
    clean-looking success.
    """
    if findings and not fix_task_paths:
        return (
            "FAILED",
            (
                f"{len(findings)} finding(s) recorded but zero fix-task files "
                "were admitted — refusing to print a clean-looking success "
                "(design §c.1, the empty-artefacts silent lie)"
            ),
        )
    if not findings and fix_task_paths:
        return (
            "FAILED",
            (
                f"{len(fix_task_paths)} fix-task file(s) written but the "
                "findings file is empty — the review claims clean while "
                "producing work"
            ),
        )
    return ("PASSED", None)


# ---------------------------------------------------------------------------
# Marker block — printed by the leg, from verified files
# ---------------------------------------------------------------------------


def render_marker_block(
    *,
    fix_task_paths: Sequence[str],
    findings: Sequence[Dict[str, Any]],
    coach_score: Optional[float] = None,
) -> str:
    """Render the exact four-marker shape ``forge``'s parser scrapes.

    Shapes pinned against ``forge/src/forge/adapters/guardkit/parser.py``
    (regexes at :36-61, extractors at :185-241):

    * ``## Artefacts`` heading, then one ``- <path>`` line per fix task;
    * a bare ``coach_score: <float>`` line — emitted **before** the artefact
      section so it can never be mistaken for an artefact line;
    * ``## Detection Findings`` heading, then a fenced JSON **array**.

    ``## Coach Breakdown`` is not emitted: the review leg has no coach and
    inventing a criterion table would be a fabricated gate.
    """
    lines: List[str] = []
    if coach_score is not None:
        lines.append(f"coach_score: {coach_score}")
        lines.append("")
    lines.append("## Artefacts")
    if fix_task_paths:
        lines.extend(f"- {path}" for path in fix_task_paths)
    else:
        lines.append(
            "_(no fix tasks — the review is positively clean; see the report)_"
        )
    lines.append("")
    lines.append("## Detection Findings")
    lines.append("```json")
    lines.append(json.dumps(list(findings), indent=2, default=str))
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The producer seam
# ---------------------------------------------------------------------------


#: The producer's own guide/readme, written at its steps 9-10
#: (``implement_orchestrator.handle_implement_option``). They land in the same
#: directory as the fix tasks but are never fix tasks, so they are dropped from
#: the candidate list by name rather than surfaced as "withheld artefacts" —
#: naming them here keeps the exclusion narrow and auditable.
PRODUCER_SIDECARS: Tuple[str, ...] = ("README.md", "IMPLEMENTATION-GUIDE.md")


def _snapshot_backlog(repo_root: Path) -> Dict[Path, Tuple[int, int]]:
    """Fingerprint ``tasks/backlog/**/*.md`` so new writes can be identified."""
    backlog = repo_root / "tasks" / "backlog"
    snapshot: Dict[Path, Tuple[int, int]] = {}
    if not backlog.is_dir():
        return snapshot
    for path in backlog.rglob("*.md"):
        try:
            stat = path.stat()
        except OSError:  # pragma: no cover — racing filesystem
            continue
        snapshot[path.resolve()] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _diff_backlog(
    before: Dict[Path, Tuple[int, int]], repo_root: Path
) -> List[Path]:
    """Return the backlog task files created or rewritten since ``before``."""
    after = _snapshot_backlog(repo_root)
    changed = [
        path
        for path, sig in after.items()
        if before.get(path) != sig and path.name not in PRODUCER_SIDECARS
    ]
    return sorted(changed)


def _import_producer():
    """Import ``handle_implement_option_sync``, bootstrapping ``lib.*`` if needed.

    ``installer/core/lib/implement_orchestrator.py`` mixes absolute
    ``installer.core.lib.*`` imports with bare ``lib.*`` ones, so the payload
    root has to be on ``sys.path`` for the bare form to resolve when the leg
    runs with ``cwd`` set to somebody else's worktree. Resolved via the same
    packaged/editable resolver the rest of the installer payload uses.
    """
    import sys

    try:
        from installer.core.lib.implement_orchestrator import (  # noqa: PLC0415
            handle_implement_option_sync,
        )

        return handle_implement_option_sync
    except ImportError:
        pass

    from guardkit.templates.resolver import (  # noqa: PLC0415
        _get_installer_core_dir,
    )

    core_dir = str(_get_installer_core_dir())
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    from installer.core.lib.implement_orchestrator import (  # noqa: PLC0415
        handle_implement_option_sync,
    )

    return handle_implement_option_sync


def produce_fix_tasks(
    *, task_id: str, task: Dict[str, Any], report_path: Path, repo_root: Path
) -> Tuple[List[Path], Dict[str, Any]]:
    """Take the ``[I]mplement`` path via the **existing** fix-task producer.

    Calls ``implement_orchestrator.handle_implement_option_sync(review_task,
    review_report_path)`` — the real signature, verified in
    ``installer/core/lib/implement_orchestrator.py:732`` (the ext doc's
    ``handle_implement_option`` description at ext:1711-1716 disagrees with the
    code; the code wins, design §e.6).

    Two hazards handled here:

    * the producer prints a ten-step narration to **stdout**, and this leg's
      stdout is the pipeline's control surface — so it is redirected to stderr;
    * the producer calls ``sys.exit(1)`` when the report yields no parseable
      recommendations, which would take the whole leg down with the wrong exit
      code — so ``SystemExit`` is caught and reported.
    """
    before = _snapshot_backlog(repo_root)
    info: Dict[str, Any] = {"called": True}

    try:
        handle_implement_option_sync = _import_producer()
    except Exception as exc:  # noqa: BLE001
        info.update(
            {"ok": False, "error": f"producer unimportable: {type(exc).__name__}: {exc}"}
        )
        return [], info

    review_task = {
        "id": task_id,
        "title": task.get("frontmatter", {}).get("title") or task_id,
        "created": task.get("frontmatter", {}).get("created"),
    }
    if not review_task["created"]:
        review_task.pop("created")

    narration = io.StringIO()
    try:
        with contextlib.redirect_stdout(narration):
            handle_implement_option_sync(review_task, str(report_path))
        info["ok"] = True
    except SystemExit as exc:
        info.update({"ok": False, "error": f"producer exited: code={exc.code}"})
    except Exception as exc:  # noqa: BLE001
        info.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        info["narration_tail"] = narration.getvalue()[-4000:]

    written = _diff_backlog(before, repo_root)
    info["files_touched"] = [str(p) for p in written]
    return written, info


# ---------------------------------------------------------------------------
# The model call
# ---------------------------------------------------------------------------


def _build_agent_invoker(*, worktree_path: Path, sdk_timeout: int, model: Optional[str]):
    """Construct the hardened invoker the specialist runner composes over.

    ``AgentInvoker(worktree_path=...)`` constructs from a bare path — no
    worktree creation — because the dispatch's ``cwd`` *is* the build's
    worktree. Imported lazily so ``guardkit --help`` does not pay for the
    orchestrator's import graph.
    """
    from guardkit.orchestrator.agent_invoker import AgentInvoker  # noqa: PLC0415

    return AgentInvoker(
        worktree_path=worktree_path,
        sdk_timeout_seconds=sdk_timeout,
        model_name=model,
    )


def _invoke_review_specialist(
    *,
    prompt: str,
    repo_root: Path,
    task_id: str,
    sdk_timeout: int,
    model: Optional[str],
):
    """Run the review specialist once and return its ``SpecialistInvocationResult``."""
    agent_invoker = _build_agent_invoker(
        worktree_path=repo_root, sdk_timeout=sdk_timeout, model=model
    )
    return asyncio.run(
        run_specialist(
            REVIEW_SPECIALIST_NAME,
            repo_root,
            task_id,
            sdk_timeout,
            prompt,
            list(REVIEW_ALLOWED_TOOLS),
            agent_invoker,
        )
    )


def _looks_like_timeout(error: Optional[str], elapsed: float, budget: int) -> bool:
    """Classify a specialist failure as the leg's own budget expiring."""
    if elapsed >= budget * 0.95:
        return True
    if not error:
        return False
    lowered = error.lower()
    return "timeout" in lowered or "timed out" in lowered


def _write_partial_report(report_path: Path, task_id: str, reason: str) -> None:
    """Write an honest partial when the leg ran out of budget (§d stage 1.6)."""
    if report_path.exists():
        return
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(
                [
                    f"# Review Report — {task_id} (PARTIAL)",
                    "",
                    "## Summary",
                    "",
                    "**This review did not complete.** The leg's internal budget "
                    "expired before the model wrote a report.",
                    "",
                    f"Reason: {reason}",
                    "",
                    "No findings were produced. Nothing in this file may be read "
                    "as a clean review — the review did not happen.",
                    "",
                    "## Phases Not Run",
                    "",
                    render_phases_not_run_table(),
                    "",
                ]
            ),
            encoding="utf-8",
        )
    except OSError as exc:  # pragma: no cover — defensive
        logger.warning("could not write partial report %s: %s", report_path, exc)


# ---------------------------------------------------------------------------
# Receipt (§f, M5)
# ---------------------------------------------------------------------------


def receipt_path_for(repo_root: Path, task_id: str) -> Path:
    """``.guardkit/autobuild/{task_id}/task_review_results.json``.

    Mirrors ``task_work_results.json`` so the leg's receipt lands inside a
    receipt family the pipeline's stage exporter already copies out — M5 gains
    a per-leg receipt with zero new export code.
    """
    return repo_root / ".guardkit" / "autobuild" / task_id / "task_review_results.json"


def build_receipt(
    outcome: ReviewLegOutcome, *, build_id: Optional[str], correlation_id: Optional[str]
) -> Dict[str, Any]:
    """Assemble the per-leg receipt payload."""
    return {
        "leg": "task-review",
        "task_id": outcome.task_id,
        "build_id": build_id,
        "correlation_id": correlation_id,
        "status": outcome.status,
        "exit_code": outcome.exit_code,
        "model": outcome.model,
        # Coordinator cure (LI coach finding 1): the M0 fence judges only a
        # SUPPLIED --model, and the pipeline's dispatch never supplies one —
        # the receipt must say so, or a reader mistakes model:null for
        # "fenced". The effective-seat fence is the ledgered follow-up.
        "m0_fence": (
            "evaluated (--model supplied)"
            if outcome.model
            else "NOT-EVALUATED (no --model supplied; effective seat = "
            "harness default — fence the resolved seat before the first "
            "UNATTENDED crossing)"
        ),
        "seat": outcome.seat,
        "duration_seconds": round(outcome.duration_seconds, 3),
        "findings_count": len(outcome.findings),
        "coach_score": outcome.coach_score,
        "fix_task_paths": list(outcome.fix_task_paths),
        "rejected_artefacts": list(outcome.rejected_artefacts),
        "review_report_path": outcome.report_path,
        "findings_file": outcome.findings_file,
        "clean_line_present": outcome.clean_line_present,
        "consistency_check": outcome.consistency_check,
        "phases_not_run": [dict(phase) for phase in PHASES_NOT_RUN],
        "fleet_memory_cli": outcome.fleet_memory_cli,
        "context": [p.as_receipt_entry() for p in outcome.context_payloads],
        "producer": outcome.producer,
        "error": outcome.error,
    }


def write_receipt(
    outcome: ReviewLegOutcome,
    *,
    repo_root: Path,
    build_id: Optional[str],
    correlation_id: Optional[str],
) -> Optional[Path]:
    """Write the receipt; never raises (a receipt failure must not fail a leg)."""
    path = receipt_path_for(repo_root, outcome.task_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                build_receipt(
                    outcome, build_id=build_id, correlation_id=correlation_id
                ),
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return path
    except OSError as exc:  # pragma: no cover — defensive
        logger.warning("could not write review receipt %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# The leg
# ---------------------------------------------------------------------------


def run_review_leg(
    *,
    task_id: str,
    repo_root: Path,
    context: Sequence[str] = (),
    feature_yaml: Optional[str] = None,
    mode: str = "architectural",
    depth: str = "standard",
    model: Optional[str] = None,
    sdk_timeout: int = DEFAULT_SDK_TIMEOUT_SECONDS,
) -> ReviewLegOutcome:
    """Run the headless review leg end to end. Never raises; never exits."""
    started = time.monotonic()
    seat = os.environ.get("OPENAI_BASE_URL")
    report_path = repo_root / ".claude" / "reviews" / f"{task_id}-review-report.md"
    findings_path = (
        repo_root / ".guardkit" / "autobuild" / task_id / "review_findings.json"
    )

    def _outcome(status: str, exit_code: int, **kwargs: Any) -> ReviewLegOutcome:
        return ReviewLegOutcome(
            task_id=task_id,
            status=status,
            exit_code=exit_code,
            duration_seconds=time.monotonic() - started,
            model=model,
            seat=seat,
            report_path=str(report_path),
            findings_file=str(findings_path),
            **kwargs,
        )

    # --- Phase 0 disposition: REFUSED. id-form only, no silent fallback. -----
    try:
        task = TaskLoader.load_task(task_id, repo_root=repo_root)
    except (TaskNotFoundError, TaskParseError) as exc:
        return _outcome(
            "failed",
            2,
            error=(
                f"REFUSED (Phase 0, ad-hoc task creation): the review leg is "
                f"id-form only and no task file exists for {task_id}. {exc}"
            ),
        )

    payloads = load_context_payloads(context, repo_root=repo_root)
    memory = attempt_fleet_memory_cli(
        task.get("frontmatter", {}).get("title") or task_id, repo_root=repo_root
    )

    prompt = render_review_prompt(
        task_id=task_id,
        task=task,
        report_path=report_path,
        findings_path=findings_path,
        context_payloads=payloads,
        feature_yaml=feature_yaml,
        fleet_memory_cli=memory,
        mode=mode,
        depth=depth,
    )

    # Pre-create the output directories so a Write-only specialist cannot fail
    # on a missing parent.
    for directory in (report_path.parent, findings_path.parent):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover — defensive
            logger.warning("could not create %s: %s", directory, exc)

    invoke_started = time.monotonic()
    try:
        result = _invoke_review_specialist(
            prompt=prompt,
            repo_root=repo_root,
            task_id=task_id,
            sdk_timeout=sdk_timeout,
            model=model,
        )
        status = getattr(result, "status", "failed")
        error = getattr(result, "error", None)
    except Exception as exc:  # noqa: BLE001 — the leg must never traceback out
        status, error = "failed", f"{type(exc).__name__}: {exc}"
    elapsed = time.monotonic() - invoke_started

    if status != "passed":
        if _looks_like_timeout(error, elapsed, sdk_timeout):
            reason = error or f"internal SDK budget of {sdk_timeout}s expired"
            _write_partial_report(report_path, task_id, reason)
            return _outcome(
                "timeout",
                2,
                error=(
                    f"the review leg exceeded its internal {sdk_timeout}s budget "
                    f"({elapsed:.0f}s elapsed); a partial report was written. "
                    f"Detail: {reason}"
                ),
                fleet_memory_cli=memory,
                context_payloads=payloads,
            )
        return _outcome(
            "failed",
            2,
            error=f"review specialist failed: {error}",
            fleet_memory_cli=memory,
            context_payloads=payloads,
        )

    if not report_path.is_file():
        return _outcome(
            "failed",
            2,
            error=(
                f"the review specialist finished but wrote no report at "
                f"{report_path} — refusing to report a review that produced "
                "nothing"
            ),
            fleet_memory_cli=memory,
            context_payloads=payloads,
        )

    findings, coach_score, findings_error = read_findings_file(findings_path)
    if findings_error:
        return _outcome(
            "failed",
            2,
            error=(
                f"{findings_error} — without a findings file the leg cannot "
                "tell a clean review from an unreported one"
            ),
            fleet_memory_cli=memory,
            context_payloads=payloads,
            producer={"called": False, "reason": "no usable findings file"},
        )

    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    clean_line_present = _clean_line_present(report_text)

    produced: List[Path] = []
    producer_info: Dict[str, Any] = {"called": False}
    if findings:
        produced, producer_info = produce_fix_tasks(
            task_id=task_id, task=task, report_path=report_path, repo_root=repo_root
        )

    # Coordinator cure (LI coach finding 3): the belt was tautological
    # (candidates == written_this_run). Candidates are now the FULL backlog
    # listing, so the written-this-run filter is load-bearing: a pre-existing
    # admissible-stem file in the backlog can never be printed as this leg's
    # work. `produced` is already the before/after diff (the producer
    # snapshots the backlog around its own writes).
    all_backlog = sorted(_snapshot_backlog(repo_root).keys())
    fix_task_paths, rejected = admit_fix_task_paths(
        all_backlog, written_this_run=produced, report_path=report_path
    )

    verdict, failure = evaluate_consistency(
        findings=findings, fix_task_paths=fix_task_paths
    )

    if verdict != "PASSED":
        return _outcome(
            "inconsistent",
            2,
            error=failure,
            findings=findings,
            coach_score=coach_score,
            fix_task_paths=fix_task_paths,
            rejected_artefacts=rejected,
            consistency_check=verdict,
            clean_line_present=clean_line_present,
            fleet_memory_cli=memory,
            context_payloads=payloads,
            producer=producer_info,
        )

    if not findings and not clean_line_present:
        return _outcome(
            "inconsistent",
            2,
            error=(
                "the review reported no findings but the report does not carry "
                "the explicit clean line — a clean review must be POSITIVELY "
                "clean (design §c.1)"
            ),
            findings=findings,
            coach_score=coach_score,
            consistency_check="FAILED",
            clean_line_present=False,
            fleet_memory_cli=memory,
            context_payloads=payloads,
            producer=producer_info,
        )

    return _outcome(
        "findings" if findings else "clean",
        0,
        findings=findings,
        coach_score=coach_score,
        fix_task_paths=fix_task_paths,
        rejected_artefacts=rejected,
        consistency_check=verdict,
        clean_line_present=clean_line_present,
        fleet_memory_cli=memory,
        context_payloads=payloads,
        producer=producer_info,
    )


__all__ = [
    "CLEAN_REVIEW_LINE",
    "DEFAULT_SDK_TIMEOUT_SECONDS",
    "FIX_TASK_STEM_RE",
    "FRONTIER_PROVIDER_PREFIXES",
    "PHASES_NOT_RUN",
    "REVIEW_ALLOWED_TOOLS",
    "REVIEW_SPECIALIST_NAME",
    "ContextPayload",
    "ReviewLegOutcome",
    "admit_fix_task_paths",
    "attempt_fleet_memory_cli",
    "build_receipt",
    "evaluate_consistency",
    "load_context_payloads",
    "produce_fix_tasks",
    "read_findings_file",
    "receipt_path_for",
    "render_marker_block",
    "render_phases_not_run_table",
    "render_review_prompt",
    "run_review_leg",
    "write_receipt",
]
