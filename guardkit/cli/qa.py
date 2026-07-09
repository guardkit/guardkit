"""``guardkit qa`` — QA format validation + the live-gate runner (WS2 B1 + B3).

v1 surface (scope-design §3 CLI table — ``walk`` (B5) + ``mutate`` /
``probe-boundaries`` (B6) land later):

    guardkit qa validate <kind> <path>     # exit 0 valid, 1 invalid (loud)
    guardkit qa schema <kind> [--out F]    # JSON-Schema export
    guardkit qa kinds                      # list known kinds
    guardkit qa live-gate --feature <id> --target <env> [--gates ..] [--campaign]

``validate``/``schema``/``kinds`` are on-demand format tools (no enforcement —
that is B2). ``live-gate`` runs the repo's registered F4 gates and emits the
results envelope on stdout for the forge adapter (scope-design §3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from guardkit.qa.formats import (
    FORMAT_KINDS,
    KIND_ALIASES,
    QAFormatError,
    export_json_schema,
    resolve_kind,
    validate_instance,
)

console = Console()

#: Exit codes for ``live-gate`` — distinct non-1 codes for the attribution
#: verdicts so the forge adapter can tell a feature failure (1) from an
#: instrument/environment fault (3/4), which per DF-017 never count against the
#: feature. (The authoritative verdict is the envelope's ``verdict`` field on
#: stdout; the exit code is a convenience mirror.)
_VERDICT_EXIT_CODES = {
    "pass": 0,
    "fail": 1,
    "instrument_fail": 3,
    "environment_fail": 4,
}


@click.group()
def qa() -> None:
    """QA verification formats (tier-1 F1–F5) and validators."""


@qa.command()
@click.argument("kind")
@click.argument("path", type=click.Path(path_type=Path))
def validate(kind: str, path: Path) -> None:
    """Validate a QA format instance file against its schema.

    KIND is one of the canonical kinds (pass-bar, known-failures, leak-sweep,
    gate-registry, results-envelope, evidence-index) or an f1..f5 alias.
    """
    try:
        instance = validate_instance(kind, path)
    except QAFormatError as exc:
        console.print("[bold red]✗ VALIDATION FAILED[/bold red]")
        # Print the full error verbatim — loud, field-level, never summarized.
        console.print(str(exc), highlight=False)
        sys.exit(1)
    console.print(
        f"[bold green]✓ VALID[/bold green] {path} "
        f"({instance.FORMAT_KIND} v{instance.format_version})"
    )


@qa.command()
@click.argument("kind")
@click.option(
    "--out",
    "out_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Write the JSON-Schema to a file instead of stdout.",
)
def schema(kind: str, out_path: Path | None) -> None:
    """Export the JSON-Schema for a QA format kind."""
    try:
        model = resolve_kind(kind)
    except QAFormatError as exc:
        console.print(f"[bold red]✗[/bold red] {exc}", highlight=False)
        sys.exit(1)
    text = export_json_schema(model)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        console.print(f"[green]Wrote[/green] {out_path}")
    else:
        click.echo(text)


@qa.command(name="live-gate")
@click.option("--feature", "feature_id", required=True, help="Feature id under test.")
@click.option("--target", "target_env", required=True, help="Target environment id.")
@click.option(
    "--gates",
    "gates",
    default=None,
    help="Comma-separated subset of registered gate ids (default: all).",
)
@click.option(
    "--campaign",
    is_flag=True,
    default=False,
    help="Campaign mode (attempts ledger is B4; accepted here, single run in v1).",
)
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Target repo root (default: cwd). Reads qa/gates/registry.yaml under it.",
)
def live_gate(
    feature_id: str,
    target_env: str,
    gates: str | None,
    campaign: bool,
    repo_root: Path,
) -> None:
    """Run the repo's registered F4 gates and emit the results envelope.

    Deterministic runner (DF-015 clause 1). Prints the F4 results envelope as
    JSON on stdout (the forge adapter parses its ``verdict``); exit code mirrors
    the verdict (0 pass, 1 fail, 3 instrument_fail, 4 environment_fail).

    ``--campaign`` records the run as attempt 1 of an F9 attempts ledger
    (``qa/attempts-<feature>.yaml``) and stamps the envelope's
    ``attempts_ledger_ref``. v1 has no live multi-attempt driver, so a single
    unattended run must be green or a pre-flight short-circuit — a run with reds
    that no arbiter has binned is honestly reported UNCLOSED (exit 2, DF-017
    §2.1), never a silent green.
    """
    # Imported lazily so `guardkit qa validate` has no orchestrator import cost.
    from guardkit.orchestrator.live_gate import (
        LiveGateError,
        LiveGateRunner,
        UndispositionedRedError,
    )

    requested = [g.strip() for g in gates.split(",") if g.strip()] if gates else None
    runner = LiveGateRunner(repo_root)
    try:
        envelope = runner.run(
            feature_id,
            target_env,
            requested_gate_ids=requested,
            campaign=campaign,
        )
        if campaign:
            envelope = _record_single_run_campaign(envelope, repo_root)
    except UndispositionedRedError as exc:
        # The run has reds no arbiter binned — UNCLOSED (never a silent green).
        console.print("[bold red]✗ live-gate run is UNCLOSED[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)
    except (QAFormatError, LiveGateError) as exc:
        # A missing/invalid registry or an unknown gate id is a loud config
        # error — never a silent green.
        console.print("[bold red]✗ live-gate could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    # The envelope on stdout is the contract for the forge adapter.
    click.echo(json.dumps(envelope.model_dump(mode="json"), indent=2))
    sys.exit(_VERDICT_EXIT_CODES.get(envelope.verdict, 1))


def _record_single_run_campaign(envelope, repo_root: Path):
    """Wrap a single B3 run as attempt 1 of an F9 ledger and stamp the envelope.

    Returns the finalized envelope (with ``attempts_ledger_ref`` /
    ``dispositions_ref`` set). Raises ``UndispositionedRedError`` if the run has
    unbinned reds — the CLI has no arbiter to bin them unattended.
    """
    from guardkit.orchestrator.live_gate import (
        finalize_envelope,
        single_run_campaign,
        write_campaign,
    )

    # The started timestamp's date part (YYYY-MM-DD) anchors the ledger entry.
    run_date = envelope.started[:10]
    result = single_run_campaign(envelope, date=run_date)
    refs = write_campaign(result, repo_root, run_id=envelope.run_id)
    return finalize_envelope(envelope, result, refs)


@qa.command()
def kinds() -> None:
    """List the known QA format kinds and their aliases."""
    alias_by_kind = {v: k for k, v in KIND_ALIASES.items()}
    for name, model in FORMAT_KINDS.items():
        alias = alias_by_kind.get(name, "")
        alias_txt = f"  (alias: {alias})" if alias else ""
        console.print(
            f"  {name:<18} v{model.CURRENT_FORMAT_VERSION}{alias_txt}"
        )
