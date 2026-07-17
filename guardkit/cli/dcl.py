"""``guardkit dcl`` — the DCL derivation surface (D2, design §2).

    guardkit dcl check <file> [--json]                 # compile gate
    guardkit dcl author --feature <slug> --task <ID>   # seat authors the .dcl (§10)
    guardkit dcl derive --feature <ID> [--repo .]      # write derived set + receipt
    guardkit dcl run --assertions <file> [--base-url-env VAR]   # execute, F4 envelope

Idiom (mirrors ``guardkit qa``): lazy imports inside command bodies, loud typed
exit codes, the F4 envelope on stdout for the ``run`` gate. ``check`` mirrors the
vendored WASM checker's exit codes (0 ok, 1 compile-failed, 2 harness fault).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
def dcl() -> None:
    """DCL spec-track derivation (compile gate, derive assertions, run the F4 gate)."""


@dcl.command()
@click.argument("dcl_file", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit the checker envelope as JSON.")
def check(dcl_file: Path, as_json: bool) -> None:
    """Compile a ``.dcl`` and gate on a clean compile (ok + zero errors).

    Exit: 0 compile-clean, 1 compile failed (errors), 2 harness/instrument fault.
    """
    from guardkit.qa.dcl.checker import CheckerError
    from guardkit.qa.dcl.checker import check as run_check

    try:
        envelope = run_check(dcl_file)
    except CheckerError as exc:
        console.print("[bold red]✗ checker could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    if as_json:
        click.echo(json.dumps(envelope, indent=2))

    ok = bool(envelope.get("ok")) and envelope.get("errorCount", 1) == 0
    if ok:
        console.print(
            f"[bold green]✓ COMPILE OK[/bold green] {dcl_file} "
            f"(warnings: {envelope.get('warningCount', 0)})"
        )
        sys.exit(0)
    errors = [d for d in envelope.get("diagnostics", []) if d.get("severity") == "error"]
    console.print(
        f"[bold red]✗ COMPILE FAILED[/bold red] {dcl_file} "
        f"({envelope.get('errorCount')} error(s))",
        highlight=False,
    )
    for d in errors:
        console.print(f"  - [{d.get('code')}] {d.get('message')}", highlight=False)
    sys.exit(1)


@dcl.command()
@click.option("--feature", "feature", required=True, help="Feature slug (also the .dcl file stem).")
@click.option("--task", "task", required=True, help="Task id (stamped as the // @task: marker).")
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Target repo root (default: cwd).",
)
@click.option(
    "--request",
    "request_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Recorded feature Request markdown (default: "
    "feature_spec_inputs/<feature>.md under the repo).",
)
@click.option(
    "--criteria",
    "criteria_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Machine criteria YAML — a pass-bar or pass-bar-seed (default: "
    "qa/pass-bar-<task>.yaml under the repo).",
)
@click.option("--capability", "capability", default=None, help="Capability name (recorded on the receipt).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit the authoring envelope as JSON.")
def author(
    feature: str,
    task: str,
    repo_root: Path,
    request_path: Path | None,
    criteria_path: Path | None,
    capability: str | None,
    as_json: bool,
) -> None:
    """Author features/<feature>/<feature>.dcl via the seat (the §10 protocol).

    ONE seat call under the sha-pinned vocabulary reference; if it compiles dirty,
    exactly ONE bounded repair call carrying the checker's verbatim diagnostics.
    Endpoint/model resolve from ``qa.dcl_author`` (config) with env overrides.

    Exit: 0 authored (artifact + receipt written), 1 LOUD authoring failure
    (receipt written authored:false, artifact NOT written, any pre-existing
    artifact left untouched), 2 instrument/usage error (nothing written).
    """
    from guardkit.qa.dcl.author import AuthoringInstrumentError, author_dcl

    repo = Path(repo_root)
    req = Path(request_path) if request_path else repo / "feature_spec_inputs" / f"{feature}.md"
    crit = Path(criteria_path) if criteria_path else repo / "qa" / f"pass-bar-{task}.yaml"

    try:
        result = author_dcl(
            feature=feature,
            task=task,
            repo_root=repo,
            request_path=req,
            criteria_path=crit,
            capability=capability,
        )
    except AuthoringInstrumentError as exc:
        # Exit 2: nothing written except this error message.
        console.print("[bold red]✗ authoring instrument error[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    if as_json:
        click.echo(json.dumps(result.envelope(), indent=2))

    if result.authored:
        console.print(
            f"[bold green]✓ AUTHORED[/bold green] {feature} "
            f"({result.attempts} attempt(s), "
            f"{'zero-shot' if result.zero_shot_clean else 'repaired'} clean)"
        )
        console.print(f"  [dim]artifact →[/dim] {result.artifact}")
        console.print(f"  [dim]receipt  →[/dim] {result.receipt}")
        sys.exit(0)

    console.print(
        f"[bold red]✗ AUTHORING FAILED[/bold red] {feature}: {result.failure_reason}",
        highlight=False,
    )
    console.print(f"  [dim]receipt →[/dim] {result.receipt} [dim](authored: false)[/dim]")
    sys.exit(1)


@dcl.command()
@click.option("--feature", "feature", required=True, help="Feature id (also the output file stem).")
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Target repo root (default: cwd). Binding at qa/dcl/binding.yaml.",
)
@click.option(
    "--dcl",
    "dcl_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Explicit .dcl path (default: features/<feature>/<feature>.dcl).",
)
@click.option("--capability", "capability", default=None, help="Capability name (default: the sole one).")
def derive(feature: str, repo_root: Path, dcl_path: Path | None, capability: str | None) -> None:
    """Derive the outside-in assertion set + receipt for a feature.

    Writes ``qa/dcl/derived/<feature>.yaml`` (the assertion set) and
    ``qa/dcl/derivation-<feature>.yaml`` (the F-format receipt). Exit: 0 written,
    2 config/derivation fault (loud).
    """
    from guardkit.qa.dcl.binding import binding_path, load_binding, sha256_of
    from guardkit.qa.dcl.checker import CHECKER_PIN, CheckerError
    from guardkit.qa.dcl.checker import check as run_check
    from guardkit.qa.dcl.checker import ir as run_ir
    from guardkit.qa.dcl.deriver import DerivationError, derive as run_derive, make_receipt
    from guardkit.qa.formats.base import QAFormatError

    repo = Path(repo_root)
    src = Path(dcl_path) if dcl_path else repo / "features" / feature / f"{feature}.dcl"
    if not src.is_file():
        console.print(f"[bold red]✗[/bold red] .dcl not found: {src}", highlight=False)
        sys.exit(2)
    bpath = binding_path(repo)
    if not bpath.is_file():
        console.print(f"[bold red]✗[/bold red] binding not found: {bpath}", highlight=False)
        sys.exit(2)

    try:
        binding = load_binding(bpath)
        envelope = run_check(src)
        ir_obj = run_ir(src)
        result = run_derive(ir_obj, binding, feature=feature, capability=capability)
    except (CheckerError, DerivationError, QAFormatError) as exc:
        console.print("[bold red]✗ derivation failed[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    derived_path = repo / "qa" / "dcl" / "derived" / f"{feature}.yaml"
    result.assertion_set.write_yaml(derived_path)

    receipt = make_receipt(
        result,
        feature=feature,
        source_dcl=str(src),
        source_dcl_sha256=sha256_of(src),
        binding_sha256=sha256_of(bpath),
        checker_ok=bool(envelope.get("ok")),
        error_count=envelope.get("errorCount", 0),
        warning_count=envelope.get("warningCount", 0),
        checker_pin=CHECKER_PIN,
    )
    receipt_path = repo / "qa" / "dcl" / f"derivation-{feature}.yaml"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml

    receipt_path.write_text(
        yaml.safe_dump(receipt.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )

    console.print(
        f"[bold green]✓ DERIVED[/bold green] {feature}: "
        f"{len(result.run_ids)} RUN / {len(result.skip_ids)} SKIP"
    )
    console.print(f"  [dim]set  →[/dim] {derived_path}")
    console.print(f"  [dim]receipt →[/dim] {receipt_path}")
    sys.exit(0)


@dcl.command()
@click.option(
    "--assertions",
    "assertions_path",
    required=True,
    type=click.Path(path_type=Path, dir_okay=False),
    help="Derived assertion-set file (qa/dcl/derived/<feature>.yaml).",
)
@click.option(
    "--base-url-env",
    "base_url_env",
    default="API_TEST_BASE_URL",
    show_default=True,
    help="NAME of the env var holding the base URL (never a hard-coded URL).",
)
def run(assertions_path: Path, base_url_env: str) -> None:
    """Execute the RUN assertions and emit the F4 gate envelope on stdout.

    Exit: 0 all pass, 1 any assertion failed, 2 config/instrument fault (loud).
    """
    from guardkit.qa.dcl.assertion_runner import RunnerError, run_file

    try:
        envelope, exit_code = run_file(assertions_path, base_url_env)
    except RunnerError as exc:
        console.print("[bold red]✗ assertion run could not start[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    # The envelope on stdout is the F4 contract for the live-gate executor.
    click.echo(json.dumps(envelope, indent=2))
    sys.exit(exit_code)
