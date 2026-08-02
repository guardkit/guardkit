"""``guardkit task-work`` — the headless work leg's CLI adapter.

The pipeline's conductor spawns this as a subprocess (``SUBPROCESS_STAGE_COMMANDS``
maps the work stage to the literal string ``"task-work"``) with an argv shaped
like::

    guardkit task-work --build-id <id> --correlation-id <cid> --task-id <fix_task_id>
                       --fix-task <json> [--context <text|path> ...] --nats

**``--fix-task`` is dispatch-fatal if undeclared.** The forward-context builder's
first entry for a Mode-C work dispatch is
``ContextEntry(flag="--fix-task", kind="text")``
(``forge/src/forge/pipeline/forward_context_builder.py:617-669`` →
``dispatchers/subprocess.py:378-379``), so it rides on *every* real argv. Click
rejects an unknown option with exit 2 before the command body runs — an
undeclared ``--fix-task`` would kill every dispatch at parse time, and the
failure would look like a leg that ran and refused. It is declared here, and
tolerant of absence so an attended run needs no JSON blob.

``--task-id`` carries the **fix task's** id, which is a file *stem*
(e.g. ``TASK-FW-002-some-slug``), not a bare identifier.

Exit codes are a contract with the dispatcher, so this command owns them
directly rather than delegating to ``handle_cli_errors`` (whose
``TaskNotFoundError → 1`` mapping contradicts the design's Phase-0 REFUSED
disposition, which is exit 2):

* ``0`` — the Coach approved;
* ``2`` — every refusal and every failure.

Nothing else. There is no exit 1 on this command.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import click

from guardkit.orchestrator.m0_fence import FRONTIER_ESCAPE_ENV, resolve_m0_violation
from guardkit.orchestrator.review_runner import render_marker_block
from guardkit.orchestrator.work_runner import (
    DEFAULT_LEG_BUDGET_SECONDS,
    DEFAULT_MAX_TURNS,
    DEFAULT_SDK_TIMEOUT_SECONDS,
    EMPTY_ARTEFACTS_NOTE,
    run_work_leg,
    write_receipt,
)

logger = logging.getLogger(__name__)

_NATS_NOTICE = (
    "guardkit task-work: --nats accepted for dispatch compatibility — "
    "streaming NOT BUILT (no NATS wiring exists on this path). Nothing was "
    "emitted to the bus."
)


@click.command("task-work")
@click.option(
    "--task-id",
    "task_id",
    required=True,
    help=(
        "The FIX TASK's identifier — a file stem, e.g. "
        "TASK-FW-002-some-slug. The task file must already exist on disk."
    ),
)
@click.option(
    "--build-id",
    "build_id",
    default=None,
    help="Pipeline build id; recorded in the leg receipt.",
)
@click.option(
    "--correlation-id",
    "correlation_id",
    default=None,
    help="Pipeline correlation id; recorded in the leg receipt.",
)
@click.option(
    "--feature-yaml",
    "feature_yaml",
    default=None,
    help="Path to the feature YAML, when the dispatch supplies one.",
)
@click.option(
    "--context",
    "context_values",
    multiple=True,
    help=(
        "Context payload. Repeatable, and carries two kinds on one flag: an "
        "absolute path to a context document (the originating review's "
        "artefacts), or inline text/JSON forward context. Unreadable values "
        "are recorded and ignored, never fatal."
    ),
)
@click.option(
    "--fix-task",
    "fix_task",
    default=None,
    help=(
        "The dispatch's FixTaskRef JSON audit anchor. Present on every "
        "pipeline argv; optional here so an attended run needs no blob. The "
        "task file on disk — not this payload — is the source of truth."
    ),
)
@click.option(
    "--nats",
    "nats",
    is_flag=True,
    default=False,
    help=(
        "Accepted for dispatch compatibility — streaming NOT BUILT. Passing it "
        "prints one notice to stderr and emits nothing."
    ),
)
@click.option(
    "--mode",
    "mode",
    default=None,
    help=(
        "Accepted for caller compatibility and recorded in the receipt. Free "
        "form on purpose: the dispatcher emits no --mode for this stage, and a "
        "Choice would turn an unfamiliar value into a parse-time dead journey."
    ),
)
@click.option(
    "--max-turns",
    "max_turns",
    type=int,
    default=DEFAULT_MAX_TURNS,
    show_default=True,
    help=(
        "Player-Coach turns for this fix task. Two, not autobuild's five: a "
        "work leg is one fix, and the JOURNEY's bound is max_review_cycles."
    ),
)
@click.option(
    "--model",
    "model",
    default=None,
    help=(
        "Model alias for the work seat. Defaults to NONE — never autobuild's "
        "frontier-named default (cli/autobuild.py:208). A frontier prefix is "
        f"refused unless {FRONTIER_ESCAPE_ENV}=1, and so is an unnamed seat: "
        "the effective-seat fence at select_harness judges what the harness "
        "would actually run on."
    ),
)
@click.option(
    "--sdk-timeout",
    "sdk_timeout",
    type=int,
    default=DEFAULT_SDK_TIMEOUT_SECONDS,
    show_default=True,
    help="Per-invocation model budget in seconds.",
)
@click.option(
    "--leg-budget",
    "leg_budget",
    type=int,
    default=DEFAULT_LEG_BUDGET_SECONDS,
    show_default=True,
    help=(
        "The leg's loop-level clock in seconds. Kept UNDER the pipeline's "
        "1800s work-stage tripwire so an over-long leg fails honestly with a "
        "written receipt instead of being SIGKILLed with nothing on disk."
    ),
)
def task_work(
    task_id: str,
    build_id: Optional[str],
    correlation_id: Optional[str],
    feature_yaml: Optional[str],
    context_values: Tuple[str, ...],
    fix_task: Optional[str],
    nats: bool,
    mode: Optional[str],
    max_turns: int,
    model: Optional[str],
    sdk_timeout: int,
    leg_budget: int,
) -> None:
    """Run the headless work leg for a fix task and print the pipeline markers.

    \b
    Exit Codes:
        0: The Coach approved.
        2: Every refusal and every failure — the id-form refusal, the M0
           fence, an orchestration failure, and any non-approved outcome.
    """
    if nats:
        click.echo(_NATS_NOTICE, err=True)

    # The CLI-level fence still judges a SUPPLIED alias, so an obviously
    # frontier --model dies before a model is ever constructed. It does NOT
    # decide the seat question: the chokepoint at select_harness judges the
    # EFFECTIVE seat (including model=None), and the receipt REPORTS that
    # verdict rather than re-deriving one (stage-2 design §3.3).
    violation = resolve_m0_violation(model)
    if violation is not None:
        if os.environ.get(FRONTIER_ESCAPE_ENV) == "1":
            click.echo(
                f"{violation} Proceeding because {FRONTIER_ESCAPE_ENV}=1.", err=True
            )
        else:
            click.echo(
                f"{violation} Set {FRONTIER_ESCAPE_ENV}=1 to override deliberately.",
                err=True,
            )
            sys.exit(2)

    repo_root = Path.cwd()
    outcome = run_work_leg(
        task_id=task_id,
        repo_root=repo_root,
        context=context_values,
        fix_task=fix_task,
        feature_yaml=feature_yaml,
        mode=mode,
        max_turns=max_turns,
        model=model,
        sdk_timeout=sdk_timeout,
        leg_budget=leg_budget,
    )

    # The receipt is written on EVERY path, before anything can go wrong with
    # printing — a refusal, a failure and an approval all leave one behind.
    write_receipt(
        outcome,
        repo_root=repo_root,
        build_id=build_id,
        correlation_id=correlation_id,
    )

    # The markers print on every path too, but the Artefacts section is the
    # EMPTY placeholder unconditionally: a work leg CONSUMES fix tasks and must
    # never mint one. Any printed path whose stem matches the fix-task regex is
    # harvested as a new fix task and fans out another work dispatch. No
    # coach_score either — the Coach contract is binary, and a number here
    # would be a fabricated gate.
    click.echo(
        render_marker_block(
            fix_task_paths=(),
            findings=outcome.findings,
            coach_score=None,
            empty_artefacts_note=EMPTY_ARTEFACTS_NOTE,
        )
    )

    if outcome.approved:
        sys.exit(0)

    click.echo(f"guardkit task-work: {outcome.error}", err=True)
    sys.exit(2)


__all__ = ["task_work"]
