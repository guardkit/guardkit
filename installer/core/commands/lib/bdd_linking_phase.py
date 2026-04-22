"""/feature-plan Step 11 orchestrator: link BDD scenarios to tasks (TASK-FP-LNKB-19AC).

.. note::

    **Not currently invoked from production code (TASK-FIX-RWOP1.1).**

    ``run_linking_phase`` is the in-process reference implementation of
    Step 11. It is kept here because its primitives (``discover_feature_file``,
    ``parse_matcher_response``) are reused by the production entry-point
    and because the integration tests in
    ``tests/integration/feature_plan/test_bdd_linking.py`` exercise the
    full orchestration path against mock matchers.

    The production runtime invokes Step 11 via the CLI shim
    ``installer/core/commands/lib/feature_plan_bdd_link.py``
    (``~/.agentecflow/bin/feature-plan-bdd-link``), driven from
    ``installer/core/commands/feature-plan.md`` Step 11 as two
    ``Execute:`` lines bracketing an ``INVOKE Task(bdd-linker, ...)``
    invocation. That split exists so the matcher (the ``bdd-linker``
    subagent) can run between ``prepare`` and ``apply`` without
    requiring Claude-as-runtime to compose a Python matcher callback
    inline. See TASK-REV-RWOP1 Finding #1 and TASK-FIX-RWOP1.1 for the
    full rationale.

This module wires the mechanical `bdd_linker` library (TASK-FP-LINK) into the
/feature-plan auto-detection pipeline. It handles everything deterministic
about the phase — feature-file discovery, matching-request construction,
interactive review, threshold application, summary emission — and delegates
only the scenario→task matching decision to a pluggable callback.

Design:

- The matching decision is made by the ``bdd-linker`` subagent (see
  ``installer/core/agents/bdd-linker.md``). /feature-plan invokes the subagent
  with the JSON payload produced by
  :func:`installer.core.commands.lib.bdd_linker.build_matching_request`, parses
  the returned JSON into ``TaskMatch`` values, and passes them back through
  this orchestrator's ``matcher`` callback. Tests inject a mock matcher so
  integration coverage does not depend on the LLM runtime.
- Interactive review uses ``rich.table.Table`` for display. Per-scenario
  controls (``[A]ccept all``, ``[E]dit scenario N``, ``[S]kip scenario N``,
  ``[D]one``) let users override the subagent's decision without leaving the
  terminal. In ``--no-questions`` mode, matches above threshold are applied
  automatically and below-threshold/untagged scenarios are reported in the
  summary.
- All file I/O continues to flow through
  :func:`installer.core.commands.lib.bdd_linker.apply_mapping`, preserving
  atomicity and idempotency guarantees from TASK-FP-LINK.

See ``installer/core/commands/feature-plan.md`` § "Step 11" for the prose
contract /feature-plan follows when invoking this orchestrator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from installer.core.commands.lib.bdd_linker import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    FeatureDocument,
    LinkingResult,
    MatchingRequest,
    TaskInfo,
    TaskMatch,
    apply_mapping,
    build_matching_request,
    existing_task_tags,
    parse_feature_file,
)


MatcherCallback = Callable[[MatchingRequest], object]
"""Signature of the matcher callback.

Accepts a :class:`MatchingRequest` and returns either:

- A list of :class:`TaskMatch` values (already parsed), or
- A JSON string / dict / list that :func:`parse_matcher_response` can decode.

Both shapes are supported so /feature-plan can pass the raw subagent response
through without manual parsing, while tests can hand in an already-typed list.
"""


# ---------------------------------------------------------------------------
# Feature-file discovery
# ---------------------------------------------------------------------------


def discover_feature_file(
    project_root: Path,
    feature_slug: str,
) -> Optional[Path]:
    """Locate the ``.feature`` file for a feature slug.

    Checks the two conventions ``/feature-spec`` emits, in precedence order:

    1. ``features/{slug}/{slug}.feature`` — the default scaffolded layout
       (jarvis precedent, current /feature-spec output).
    2. ``features/{slug}.feature`` — the flat fallback used by older or
       hand-authored feature files.

    Args:
        project_root: Directory containing ``features/``. Usually the repo
            root /feature-plan is invoked from.
        feature_slug: Kebab-case slug of the feature (e.g., ``"dark-mode"``).

    Returns:
        The path to the first matching file, or ``None`` when no feature file
        exists. Returning ``None`` is the ``silent skip`` signal for Step 11:
        /feature-plan continues to the completion summary without noise.
    """
    if not feature_slug:
        return None

    candidates = [
        project_root / "features" / feature_slug / f"{feature_slug}.feature",
        project_root / "features" / f"{feature_slug}.feature",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Subagent response parsing
# ---------------------------------------------------------------------------


class MatcherResponseError(ValueError):
    """The ``bdd-linker`` subagent returned a payload we couldn't parse.

    Raised with an explanatory message so /feature-plan can surface the error
    to the user and offer a retry. Never swallowed silently — a half-parsed
    response would look like "the agent chose to tag nothing" and silently
    dormant R2 is exactly the failure mode this task is closing.
    """


def parse_matcher_response(raw: object) -> List[TaskMatch]:
    """Parse a subagent response into a list of :class:`TaskMatch`.

    Accepts:

    - A JSON string (``'[{"scenario_index": 0, ...}]'``) — typical subagent
      output via the Task tool.
    - A list of dicts (already-decoded JSON) — when the caller has already
      parsed the response.
    - A list of :class:`TaskMatch` — pass-through for tests that build matches
      directly.
    - A dict with a ``"matches"`` key — some subagents wrap the array.

    Raises:
        MatcherResponseError: If the payload can't be coerced into a list of
            valid ``TaskMatch`` values. The message names the specific problem
            (JSON decode error, missing field, wrong type) so callers can show
            actionable feedback rather than a bare stack trace.
    """
    if raw is None:
        raise MatcherResponseError("matcher returned None (expected JSON or list)")

    # Already-typed pass-through.
    if isinstance(raw, list) and raw and isinstance(raw[0], TaskMatch):
        # Validate the rest are also TaskMatch instances.
        for item in raw:
            if not isinstance(item, TaskMatch):
                raise MatcherResponseError(
                    "matcher returned mixed list — expected all TaskMatch items"
                )
        return list(raw)

    data: object
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MatcherResponseError(
                f"matcher returned invalid JSON: {exc.msg} "
                f"(line {exc.lineno} column {exc.colno})"
            ) from exc
    else:
        data = raw

    # Subagent may wrap the array — accept either shape.
    if isinstance(data, dict) and "matches" in data:
        data = data["matches"]

    if not isinstance(data, list):
        raise MatcherResponseError(
            f"matcher response must be a list (got {type(data).__name__})"
        )

    results: List[TaskMatch] = []
    for i, item in enumerate(data):
        if isinstance(item, TaskMatch):
            results.append(item)
            continue
        if not isinstance(item, dict):
            raise MatcherResponseError(
                f"matcher entry {i} is not an object (got {type(item).__name__})"
            )
        try:
            scenario_index = int(item["scenario_index"])
            task_id = str(item["task_id"])
            confidence = float(item["confidence"])
        except KeyError as exc:
            raise MatcherResponseError(
                f"matcher entry {i} missing required field: {exc.args[0]}"
            ) from exc
        except (TypeError, ValueError) as exc:
            raise MatcherResponseError(
                f"matcher entry {i} has invalid field type: {exc}"
            ) from exc
        if not task_id:
            raise MatcherResponseError(
                f"matcher entry {i} has empty task_id"
            )
        results.append(
            TaskMatch(
                scenario_index=scenario_index,
                task_id=task_id,
                confidence=confidence,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Interactive review
# ---------------------------------------------------------------------------


@dataclass
class _ReviewState:
    """Per-scenario review state used during interactive review.

    Tracks whether the user has accepted, edited, or skipped each proposed
    match. A scenario in ``action="skip"`` is excluded from the final
    ``apply_mapping`` call even if the original match was above threshold.
    """

    scenario_index: int
    task_id: str
    confidence: float
    action: str  # "accept" | "edit" | "skip"


def _run_interactive_review(
    doc: FeatureDocument,
    tasks: Sequence[TaskInfo],
    proposals: List[TaskMatch],
    threshold: float,
    input_fn: Callable[[str], str],
    printer: Callable[[str], None],
) -> List[TaskMatch]:
    """Present the subagent's proposals for interactive accept/edit/skip.

    Args:
        doc: Parsed feature document (for scenario names/keywords).
        tasks: Candidate tasks the subagent was asked to match against.
        proposals: Matches returned by the subagent, one at most per scenario
            (the orchestrator pre-buckets multi-match collisions by highest
            confidence before calling this function).
        threshold: Confidence threshold — purely informational during review,
            final application honours whatever the user confirms.
        input_fn: Callable that prompts the user (usually ``input``). Injected
            so tests can drive the review without stdin.
        printer: Callable used to emit the table and prompts (usually
            ``rich.console.Console.print`` or ``print``). Injected so tests
            can capture output.

    Returns:
        The confirmed :class:`TaskMatch` list — only "accept" and "edit"
        actions survive; "skip" actions are dropped.

    Prompt grammar:

    - Empty input (just Enter) → ``[A]ccept all`` with the current proposals.
    - ``a`` / ``A`` → accept-all (same as Enter).
    - ``d`` / ``D`` → done (finalise with current state).
    - ``e N TASK-ID`` → edit scenario ``N`` to point to ``TASK-ID``. Confidence
      is preserved. Use ``--`` as ``TASK-ID`` to clear a proposal instead of
      skipping it (rare).
    - ``s N`` → skip scenario ``N`` (drop its match entirely).
    """
    # Table of proposals, keyed by scenario index.
    state: Dict[int, _ReviewState] = {}
    for match in proposals:
        state[match.scenario_index] = _ReviewState(
            scenario_index=match.scenario_index,
            task_id=match.task_id,
            confidence=match.confidence,
            action="accept",
        )

    task_lookup: Dict[str, TaskInfo] = {t.task_id: t for t in tasks}

    def _render_table() -> None:
        """Render the current proposals in a rich table (fall back to text)."""
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError:  # pragma: no cover - rich is a core dep
            _render_plain()
            return

        table = Table(
            title=f"Proposed scenario→task mapping (threshold {threshold:.2f})",
            show_lines=False,
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("Scenario")
        table.add_column("Proposed Task")
        table.add_column("Confidence", justify="right")
        table.add_column("Status")

        for scenario in doc.scenarios:
            idx = scenario.index
            row_state = state.get(idx)
            if row_state is None:
                # No proposal — still render so the user can see the scenario.
                table.add_row(
                    str(idx),
                    scenario.name or f"<scenario {idx}>",
                    "-",
                    "-",
                    "untagged",
                )
                continue
            task = task_lookup.get(row_state.task_id)
            task_display = (
                f"{row_state.task_id} — {task.title}"
                if task is not None
                else row_state.task_id
            )
            conf_display = f"{row_state.confidence:.2f}"
            status_display = {
                "accept": "✓ accept",
                "edit": "✎ edited",
                "skip": "✗ skip",
            }[row_state.action]
            table.add_row(
                str(idx),
                scenario.name or f"<scenario {idx}>",
                task_display,
                conf_display,
                status_display,
            )

        console = Console(record=False)
        with console.capture() as cap:
            console.print(table)
        printer(cap.get())

    def _render_plain() -> None:
        """Minimal fallback rendering for when rich is unavailable."""
        lines = [
            f"Proposed scenario→task mapping (threshold {threshold:.2f})",
            "-" * 60,
        ]
        for scenario in doc.scenarios:
            idx = scenario.index
            row_state = state.get(idx)
            if row_state is None:
                lines.append(
                    f"  [{idx}] {scenario.name or '<scenario>'}  -> (untagged)"
                )
                continue
            lines.append(
                f"  [{idx}] {scenario.name or '<scenario>'}  -> "
                f"{row_state.task_id} ({row_state.confidence:.2f}) [{row_state.action}]"
            )
        printer("\n".join(lines))

    _render_table()

    # Interactive loop. Bail on any unrecognised command but show help once.
    help_line = (
        "Options: [A]ccept all (default) | [E] N TASK-ID (edit) | "
        "[S] N (skip) | [D]one"
    )
    printer(help_line)

    while True:
        try:
            raw = input_fn("Action [A/E/S/D]: ")
        except EOFError:
            # Non-interactive stdin — finalise with current state.
            break
        cmd = (raw or "").strip()
        if cmd == "" or cmd.lower() in {"a", "accept", "d", "done"}:
            break

        parts = cmd.split()
        op = parts[0].lower()

        if op in {"e", "edit"} and len(parts) >= 3:
            try:
                idx = int(parts[1])
            except ValueError:
                printer(f"  ! invalid scenario index: {parts[1]}")
                continue
            new_task = parts[2].strip()
            if idx not in state:
                # Create a new edit from scratch if the subagent didn't propose
                # one for this scenario.
                state[idx] = _ReviewState(
                    scenario_index=idx,
                    task_id=new_task,
                    confidence=1.0,
                    action="edit",
                )
            else:
                state[idx].task_id = new_task
                state[idx].action = "edit"
            _render_table()
            continue

        if op in {"s", "skip"} and len(parts) >= 2:
            try:
                idx = int(parts[1])
            except ValueError:
                printer(f"  ! invalid scenario index: {parts[1]}")
                continue
            if idx in state:
                state[idx].action = "skip"
            _render_table()
            continue

        printer(f"  ! unrecognised command: {cmd!r}")
        printer(help_line)

    # Return the surviving matches. Skips are dropped; edits and accepts flow
    # through at their recorded confidence.
    return [
        TaskMatch(
            scenario_index=s.scenario_index,
            task_id=s.task_id,
            confidence=s.confidence,
        )
        for s in state.values()
        if s.action != "skip"
    ]


# ---------------------------------------------------------------------------
# Phase orchestrator
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    """Result of running Step 11.

    Attributes:
        status: One of ``"no_feature_file"``, ``"no_scenarios"``,
            ``"all_tagged"``, ``"applied"``. The first three are
            silent-skip conditions; ``"applied"`` means ``apply_mapping`` was
            called (even if zero scenarios ended up tagged).
        feature_path: The discovered feature file, or ``None`` when skipped.
        linking_result: The :class:`LinkingResult` from ``apply_mapping`` when
            ``status == "applied"``, else ``None``.
        summary: One-line human-readable summary suitable for printing to the
            /feature-plan transcript. For silent skips this is an empty string
            so /feature-plan prints nothing.
    """

    status: str
    feature_path: Optional[Path] = None
    linking_result: Optional[LinkingResult] = None
    summary: str = ""


def run_linking_phase(
    project_root: Path,
    feature_slug: str,
    tasks: Iterable[TaskInfo],
    matcher: MatcherCallback,
    *,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    interactive: bool = True,
    input_fn: Callable[[str], str] = input,
    printer: Callable[[str], None] = print,
    dry_run: bool = False,
) -> PhaseResult:
    """Run Step 11 end-to-end.

    Flow:

    1. Discover ``features/{slug}/{slug}.feature`` (fallback
       ``features/{slug}.feature``). Skip silently if none exists.
    2. Parse the file. Skip silently if it has no scenarios.
    3. Build a :class:`MatchingRequest` (already-tagged scenarios omitted).
       Skip silently if there are no scenarios left to match — the re-run
       idempotency path.
    4. Invoke ``matcher(request)``. Parse the response via
       :func:`parse_matcher_response`; surface errors to the caller rather
       than silently dropping matches.
    5. If ``interactive=True``, present the proposals via ``rich`` and let
       the user accept/edit/skip per scenario. In ``--no-questions``
       (``interactive=False``) mode, apply the threshold without prompting.
    6. Call :func:`apply_mapping`. Emit the human-readable summary.

    Args:
        project_root: Repo root (where ``features/`` lives).
        feature_slug: Slug of the feature /feature-plan just created.
        tasks: Tasks /feature-plan just wrote — only the ID/title/description/
            ACs are used for matching.
        matcher: Callable that takes a :class:`MatchingRequest` and returns
            matches (see :data:`MatcherCallback`). In /feature-plan this is a
            thin wrapper around the Task-tool invocation of the ``bdd-linker``
            subagent; in tests it's a fixture.
        confidence_threshold: Below this, matches are reported as
            ``skipped_low_confidence``. Default 0.6 (via
            :data:`DEFAULT_CONFIDENCE_THRESHOLD`). Override with
            ``--bdd-link-threshold=0.X``.
        interactive: When True, present the rich review; when False, apply
            the threshold silently. /feature-plan sets this from
            ``--no-questions``.
        input_fn: Injection hook for ``input()`` so tests can drive the
            review loop.
        printer: Injection hook for progress output.
        dry_run: Forwarded to :func:`apply_mapping`; no file is written when
            True.

    Returns:
        A :class:`PhaseResult` describing what happened.

    Raises:
        MatcherResponseError: If ``matcher`` returns an unparseable payload.
            /feature-plan should catch and surface with a retry hint.
    """
    task_list = list(tasks)

    # Step 1: discovery.
    feature_path = discover_feature_file(project_root, feature_slug)
    if feature_path is None:
        return PhaseResult(status="no_feature_file")

    # Step 2: parse.
    doc = parse_feature_file(feature_path)
    if not doc.scenarios:
        return PhaseResult(
            status="no_scenarios",
            feature_path=feature_path,
        )

    # Step 3: identify work. If every scenario is already tagged, skip
    # silently — this is the re-run idempotency path.
    already = existing_task_tags(doc)
    if len(already) == len(doc.scenarios):
        return PhaseResult(
            status="all_tagged",
            feature_path=feature_path,
        )

    request = build_matching_request(
        doc,
        task_list,
        confidence_threshold=confidence_threshold,
        skip_already_tagged=True,
    )

    # Defensive: if nothing in the request (no scenarios left to ask about),
    # short-circuit. build_matching_request already handles this by returning
    # an empty scenarios list, but we catch it here so we don't invoke the
    # subagent for a no-op.
    if not request.scenarios:
        return PhaseResult(
            status="all_tagged",
            feature_path=feature_path,
        )

    # Step 4: invoke the matcher and parse.
    raw_response = matcher(request)
    proposals = parse_matcher_response(raw_response)

    # Pre-bucket by highest-confidence per scenario so the interactive review
    # shows one row per scenario even when the subagent returned multiple
    # candidates. apply_mapping re-buckets defensively, but de-duping upfront
    # makes the interactive table unambiguous.
    best_by_scenario: Dict[int, TaskMatch] = {}
    for match in proposals:
        current = best_by_scenario.get(match.scenario_index)
        if current is None or match.confidence > current.confidence:
            best_by_scenario[match.scenario_index] = match
    deduped = list(best_by_scenario.values())

    # Step 5: review.
    if interactive:
        confirmed = _run_interactive_review(
            doc=doc,
            tasks=task_list,
            proposals=deduped,
            threshold=confidence_threshold,
            input_fn=input_fn,
            printer=printer,
        )
    else:
        # --no-questions: accept the subagent's best matches as-is.
        # apply_mapping will still drop below-threshold ones and report them
        # in the summary; we pass them through so the summary is complete.
        confirmed = deduped

    # Step 6: apply and report.
    linking_result = apply_mapping(
        feature_path,
        confirmed,
        confidence_threshold=confidence_threshold,
        dry_run=dry_run,
    )
    summary = linking_result.summary
    printer(f"[Step 11] {summary}")

    return PhaseResult(
        status="applied",
        feature_path=feature_path,
        linking_result=linking_result,
        summary=summary,
    )


__all__ = [
    "MatcherCallback",
    "MatcherResponseError",
    "PhaseResult",
    "discover_feature_file",
    "parse_matcher_response",
    "run_linking_phase",
]
