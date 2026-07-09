"""``guardkit qa`` — QA format validation + the live-gate runner (WS2 B1 + B3).

v1 surface (scope-design §3 CLI table — ``walk`` is B5):

    guardkit qa validate <kind> <path>     # exit 0 valid, 1 invalid (loud)
    guardkit qa schema <kind> [--out F]    # JSON-Schema export
    guardkit qa kinds                      # list known kinds
    guardkit qa live-gate --feature <id> --target <env> [--gates ..] [--campaign]
    guardkit qa mutate --task <id> ...            # ST-05 mutation stage (B6)
    guardkit qa probe-boundaries --seam <id> ...  # ST-06 boundary probes (B6)

``validate``/``schema``/``kinds`` are on-demand format tools (no enforcement —
that is B2). ``live-gate`` runs the repo's registered F4 gates and emits the
results envelope on stdout for the forge adapter (scope-design §3). ``mutate``
and ``probe-boundaries`` are the B6 deeper stages — standalone (the Coach does
not consume them in v1), and **advisory by default**: findings file as
task-shaped records and do NOT block (exit 0). ``--strict`` opts a run into a
non-zero exit when findings exist (the gate-promotion path; see WS2 §B6 STATUS
for the gate-vs-advisory verdict).
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
    MARKDOWN_KINDS,
    MarkdownFormat,
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
    """QA verification formats (tier-1 F1–F5, tier-2/3 F6–F15 + deploy-profile)."""


@qa.command()
@click.argument("kind")
@click.argument("path", type=click.Path(path_type=Path))
def validate(kind: str, path: Path) -> None:
    """Validate a QA format instance file against its schema.

    KIND is any canonical kind (pass-bar, known-failures, leak-sweep,
    gate-registry, results-envelope, evidence-index, seam-manifest,
    deploy-record, disposition-record, attempts-ledger, live-matrix,
    deploy-profile, runbook, discovery-gates, kickoff-prompt, review-findings,
    walk-checkpoints) or an f1..f15 alias. ``runbook`` (F11) is validated as a
    markdown-convention document; all others as YAML/JSON.
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
    # F11 (runbook) is a markdown-convention format — it has no JSON-Schema;
    # print its human-readable convention description instead.
    if isinstance(model, type) and issubclass(model, MarkdownFormat):
        text = model.describe_schema()
    else:
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


#: Advisory-by-default: findings do NOT block in v1. ``--strict`` maps a run
#: that produced findings to this non-zero code (the gate-promotion path).
_FINDINGS_STRICT_EXIT = 3


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


@qa.command()
@click.option("--task", "task_id", required=True, help="Task id under mutation (finding subject).")
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Repo root the throwaway sandbox is copied from (default: cwd).",
)
@click.option(
    "--files",
    "files",
    default=None,
    help="Comma-separated deliverable source files to mutate (default: derive from --base diff).",
)
@click.option(
    "--test-command",
    "test_command",
    required=True,
    help="Shell test command that must go RED when the behaviour breaks "
    "(e.g. 'python -m pytest -q tests/unit').",
)
@click.option(
    "--operator",
    "operators",
    multiple=True,
    type=click.Choice(["strip-auth-header", "revert-hunk"]),
    default=("strip-auth-header",),
    help="Mutation operator(s). revert-hunk requires --base.",
)
@click.option("--base", default=None, help="Git base ref for revert-hunk / file derivation.")
@click.option("--timeout", default=600, show_default=True, help="Per-mutant test timeout (s).")
@click.option("--no-file", "no_file", is_flag=True, default=False, help="Do not write finding files.")
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit non-zero (3) if any mutant survived (gate mode; default is advisory exit 0).",
)
def mutate(
    task_id: str,
    repo_root: Path,
    files: str | None,
    test_command: str,
    operators: tuple[str, ...],
    base: str | None,
    timeout: int,
    no_file: bool,
    strict: bool,
) -> None:
    """ST-05 mutation stage — break the key behaviour, require the tests to go red.

    Each mutation runs in a THROWAWAY sandbox (never the task branch). A mutant
    that survives its own test suite is a proven coverage hole, filed as a
    non-blocking finding. Advisory by default (exit 0); ``--strict`` exits 3 on
    any survivor.
    """
    import shlex

    from guardkit.orchestrator.qa_stages import write_findings
    from guardkit.orchestrator.qa_stages.assembly import assemble_mutation_campaign
    from guardkit.orchestrator.qa_stages.errors import MutationError

    source_files = [f.strip() for f in files.split(",") if f.strip()] if files else None
    try:
        assembly = assemble_mutation_campaign(
            Path(repo_root),
            task_id,
            source_files=source_files,
            test_command=shlex.split(test_command),
            operators=list(operators),
            base=base,
            timeout=timeout,
        )
    except MutationError as exc:
        console.print("[bold red]✗ mutation stage could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    res = assembly.result
    console.print(
        f"[bold]qa mutate[/bold] {task_id}: {assembly.mutant_count} mutant(s) — "
        f"[green]{len(res.killed)} killed[/green], "
        f"[yellow]{len(assembly.findings)} survived[/yellow], "
        f"{len(res.errored)} errored"
    )
    for finding in assembly.findings:
        console.print(f"  [yellow]⚠ SURVIVOR[/yellow] {finding.site} — {finding.summary}")
    if assembly.findings and not no_file:
        paths = write_findings(assembly.findings, Path(repo_root), date=_today())
        for path in paths:
            console.print(f"  [dim]filed[/dim] {path}")
    if strict and assembly.findings:
        sys.exit(_FINDINGS_STRICT_EXIT)
    sys.exit(0)


@qa.command(name="probe-boundaries")
@click.option("--seam", "seam_id", required=True, help="Seam id from the F6 manifest to probe.")
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    default=None,
    help="F6 seam-manifest file (validates --seam is a declared seam id).",
)
@click.option(
    "--target",
    "target_spec",
    default=None,
    help="ProbeTarget as 'module.path:attr' (instance or zero-arg factory). "
    "Omit to run the loud unconfigured target (honest 'not wired').",
)
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Repo root findings are written under (default: cwd).",
)
@click.option("--no-file", "no_file", is_flag=True, default=False, help="Do not write finding files.")
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit non-zero (3) if any raw-error leak / junk-accept was found "
    "(gate mode; default is advisory exit 0).",
)
def probe_boundaries(
    seam_id: str,
    manifest_path: Path | None,
    target_spec: str | None,
    repo_root: Path,
    no_file: bool,
    strict: bool,
) -> None:
    """ST-06 boundary probes — feed non-conforming inputs at an F6 seam.

    A raw error leaking past the seam's sealed error set (or a garbage input
    silently accepted) is a non-blocking finding. Advisory by default (exit 0);
    ``--strict`` exits 3 on any finding. An unconfigured target raises loudly
    (honest "not wired") rather than reporting a clean posture.
    """
    from guardkit.orchestrator.qa_stages import (
        Finding,
        run_boundary_probes,
        write_findings,
    )
    from guardkit.orchestrator.qa_stages.assembly import resolve_probe_target
    from guardkit.orchestrator.qa_stages.boundary import load_seam_ids
    from guardkit.orchestrator.qa_stages.errors import BoundaryProbeError, QAStageStubError

    if manifest_path is not None:
        try:
            declared = load_seam_ids(manifest_path)
        except QAFormatError as exc:
            console.print("[bold red]✗ invalid seam manifest[/bold red]", highlight=False)
            console.print(str(exc), highlight=False)
            sys.exit(2)
        if seam_id not in declared:
            console.print(
                f"[bold red]✗[/bold red] seam {seam_id!r} not in manifest "
                f"(declared: {', '.join(declared) or '<none>'})",
                highlight=False,
            )
            sys.exit(2)

    try:
        target = resolve_probe_target(target_spec)
        result = run_boundary_probes(seam_id, target)
    except QAStageStubError as exc:
        console.print(
            "[bold yellow]⚠ boundary probe target not wired[/bold yellow]", highlight=False
        )
        console.print(str(exc), highlight=False)
        # Honest "not configured" — never a silent green. Non-blocking (exit 0).
        sys.exit(0)
    except BoundaryProbeError as exc:
        console.print("[bold red]✗ boundary probe could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    findings = [
        Finding(
            kind="boundary-leak" if o.classification == "leak" else "boundary-accept",
            subject=seam_id,
            site=o.input_label,
            summary=o.detail,
            evidence=f"input={o.input_label} classification={o.classification} "
            f"exc={o.exception_type}",
            suggested_pin=(
                "Fold this input class into the seam's sealed error set (reject "
                "with the seam's own error type), or reject garbage before decode."
            ),
        )
        for o in result.findings
    ]
    console.print(
        f"[bold]qa probe-boundaries[/bold] {seam_id}: {len(result.outcomes)} probe(s) — "
        f"[yellow]{len(result.leaks)} raw-error leak(s)[/yellow], "
        f"{len(result.findings)} total finding(s)"
    )
    for o in result.findings:
        console.print(f"  [yellow]⚠ {o.classification.upper()}[/yellow] {o.input_label} — {o.detail}")
    if findings and not no_file:
        paths = write_findings(findings, Path(repo_root), date=_today())
        for path in paths:
            console.print(f"  [dim]filed[/dim] {path}")
    if strict and findings:
        sys.exit(_FINDINGS_STRICT_EXIT)
    sys.exit(0)


@qa.command()
def kinds() -> None:
    """List the known QA format kinds and their aliases."""
    alias_by_kind = {v: k for k, v in KIND_ALIASES.items()}
    all_kinds = {**FORMAT_KINDS, **MARKDOWN_KINDS}
    for name, model in all_kinds.items():
        alias = alias_by_kind.get(name, "")
        alias_txt = f"  (alias: {alias})" if alias else ""
        medium = " [markdown]" if name in MARKDOWN_KINDS else ""
        console.print(
            f"  {name:<18} v{model.CURRENT_FORMAT_VERSION}{alias_txt}{medium}"
        )
