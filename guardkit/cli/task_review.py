"""``guardkit task-review`` — the headless review leg's CLI adapter.

The pipeline's conductor spawns this as a subprocess
(``SUBPROCESS_STAGE_COMMANDS`` maps the review stage to the literal string
``"task-review"``) with an argv shaped like::

    guardkit task-review --build-id <id> --correlation-id <cid> --task-id <id>
                         [--feature-yaml <path>] [--context <text|path> ...] --nats

Click rejects an unknown option with exit 2 *before* the command body runs, so
this module accepts the **union** of both callers' flags — the dispatcher's set
plus the attended review vocabulary (``--mode``, ``--depth``, ``--model``,
``--sdk-timeout``). Accepting a flag is not the same as implementing it:
``--nats`` is accepted for dispatch compatibility and says so, on **stderr**,
because stdout is the pipeline's marker scrape.

Exit codes are a contract with the dispatcher, so this command owns them
directly rather than delegating to ``handle_cli_errors`` (whose
``TaskNotFoundError → 1`` mapping contradicts the design's Phase-0 REFUSED
disposition, which is exit 2):

* ``0`` — the leg ran, the report exists, the markers are on stdout;
* ``2`` — every refusal and every failure: the Phase-0 id-form refusal, the M0
  fence, a specialist failure, the internal budget expiring, and the
  consistency check.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import click

from guardkit.orchestrator.m0_fence import (  # noqa: F401  (re-exported)
    FRONTIER_ESCAPE_ENV,
    FRONTIER_PROVIDER_PREFIXES,
    _split_provider_prefix,
    resolve_m0_violation,
)
from guardkit.orchestrator.review_runner import (
    DEFAULT_SDK_TIMEOUT_SECONDS,
    render_marker_block,
    run_review_leg,
    write_receipt,
)

logger = logging.getLogger(__name__)

# ``FRONTIER_ESCAPE_ENV``, ``_split_provider_prefix`` and ``resolve_m0_violation``
# used to be defined in this module. They MOVED (stage-2 design §3.1) to
# :mod:`guardkit.orchestrator.m0_fence` so the M0 rule is stated exactly once —
# the chokepoint fence at ``harness/selector.py`` builds on the same predicate
# rather than restating it. They are re-exported here (and kept in ``__all__``)
# so ``tests/unit/test_task_review_leg.py`` and any other importer are unchanged.

_NATS_NOTICE = (
    "guardkit task-review: --nats accepted for dispatch compatibility — "
    "streaming NOT BUILT (no NATS wiring exists on this path). Nothing was "
    "emitted to the bus."
)


@click.command("task-review")
@click.option(
    "--task-id",
    "task_id",
    required=True,
    help="Task identifier to review. The task file must already exist on disk.",
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
        "absolute path to a context document, or inline text/JSON forward "
        "context. Unreadable values are recorded and ignored, never fatal."
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
    type=click.Choice(
        ["architectural", "code-quality", "decision", "technical-debt", "security"],
        case_sensitive=False,
    ),
    default="architectural",
    show_default=True,
    help="Review mode.",
)
@click.option(
    "--depth",
    "depth",
    type=click.Choice(["quick", "standard", "comprehensive"], case_sensitive=False),
    default="standard",
    show_default=True,
    help="Review depth.",
)
@click.option(
    "--model",
    "model",
    default=None,
    help=(
        "Model alias for the review seat. A frontier provider prefix is "
        f"refused unless {FRONTIER_ESCAPE_ENV}=1 (the M0 fence). Defaults to "
        "the harness's configured seat."
    ),
)
@click.option(
    "--sdk-timeout",
    "sdk_timeout",
    type=int,
    default=DEFAULT_SDK_TIMEOUT_SECONDS,
    show_default=True,
    help=(
        "Internal model-call budget in seconds. Kept under the dispatcher's "
        "600s SIGKILL so an over-long leg fails honestly with a written "
        "partial instead of dying with no stdout."
    ),
)
def task_review(
    task_id: str,
    build_id: Optional[str],
    correlation_id: Optional[str],
    feature_yaml: Optional[str],
    context_values: Tuple[str, ...],
    nats: bool,
    mode: str,
    depth: str,
    model: Optional[str],
    sdk_timeout: int,
) -> None:
    """Run the headless review leg for a task and print the pipeline markers.

    \b
    Exit Codes:
        0: The review ran; markers are on stdout.
        2: Refused or failed — id-form refusal, M0 fence, specialist failure,
           budget expiry, or the internal consistency check.
    """
    if nats:
        click.echo(_NATS_NOTICE, err=True)

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
    outcome = run_review_leg(
        task_id=task_id,
        repo_root=repo_root,
        context=context_values,
        feature_yaml=feature_yaml,
        mode=mode,
        depth=depth,
        model=model,
        sdk_timeout=sdk_timeout,
    )

    write_receipt(
        outcome,
        repo_root=repo_root,
        build_id=build_id,
        correlation_id=correlation_id,
    )

    if not outcome.emits_markers:
        click.echo(f"guardkit task-review: {outcome.error}", err=True)
        sys.exit(outcome.exit_code)

    producer_error = outcome.producer.get("error")
    if producer_error:
        # The producer can fail *after* writing the fix-task files (its guide /
        # README steps run last). The files are real and admitted; say so rather
        # than let a half-completed producer pass unmentioned.
        click.echo(
            "guardkit task-review: the fix-task producer reported an error after "
            f"writing {len(outcome.fix_task_paths)} admitted fix-task file(s) — "
            f"{producer_error}",
            err=True,
        )

    click.echo(
        render_marker_block(
            fix_task_paths=outcome.fix_task_paths,
            findings=outcome.findings,
            coach_score=outcome.coach_score,
        )
    )
    for rejection in outcome.rejected_artefacts:
        click.echo(
            f"guardkit task-review: artefact withheld — {rejection['path']}: "
            f"{rejection['reason']}",
            err=True,
        )
    sys.exit(0)


__all__ = ["FRONTIER_ESCAPE_ENV", "resolve_m0_violation", "task_review"]
