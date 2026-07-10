"""``guardkit template`` — deterministic template tooling (DIM1-F4 / PB-8).

    guardkit template validate --deterministic [NAME...]   # render+parse gate

The **deterministic tier** renders every ``.template`` / ``.j2`` scaffold with
representative placeholders and parses the output per stack (ONE tree-sitter
parser + per-language descriptors, ``stack-plugin-architecture.md``). It exits 0
when every gated file parses (or carries an explicit opt-out), 1 on a parse
error, and 2 when the tree-sitter runtime is not installed (a gate that could not
run is NOT a pass — ``absence-of-failure-is-not-success``).

The **AI prose audit** is unchanged and lives elsewhere: the ``/template-validate``
skill (``installer/core/commands/template-validate.md``). This CLI does not
replace it — it adds the deterministic, CI-runnable tier the prose audit lacked.
"""

from __future__ import annotations

import sys
from typing import Tuple

import click
from rich.console import Console

from guardkit.templates.parse_gate import (
    FileStatus,
    ParseGateUnavailable,
    validate_templates,
)
from guardkit.templates.structure_lint import (
    COMMITTED_SERVING_WINDOW_TOKENS,
    Severity,
    lint_command_templates,
)

console = Console()


def _print_structure_lint() -> None:
    """Report-only template-structure lint over the sliceable command specs.

    PB-5 / DIM2-F4. Advisory ONLY — every finding needs a pinned-byte fix
    (an ADR-D re-pin event), so this NEVER changes the exit code. It surfaces
    the ambiguous anchors, missing protocol sections, oversized sections
    (now WARNING at the committed 32K floor, per WS4 Amendment M3), and
    unmarked example blocks that a fence-naive slicer would trip over.
    """
    results = lint_command_templates(
        serving_window_tokens=COMMITTED_SERVING_WINDOW_TOKENS
    )
    total_warn = sum(
        1 for fs in results.values() for f in fs if f.severity is Severity.WARNING
    )
    console.print()
    console.print(
        "[bold]Template-structure lint[/bold] "
        "[dim](PB-5/DIM2-F4 — report-only, advisory)[/dim]"
    )
    if not results:
        console.print("  [dim]no sliceable command specs found — skipped[/dim]")
        return
    for name, findings in results.items():
        if not findings:
            console.print(f"  [green]✓[/green] {name} — no structure findings")
            continue
        console.print(f"  {name}:")
        for f in findings:
            tag = (
                "[yellow]WARN[/yellow]"
                if f.severity is Severity.WARNING
                else "[dim]info[/dim]"
            )
            loc = f"L{f.line}" if f.line else "file"
            console.print(f"    {tag} [{f.check}] {loc}: {f.message}", highlight=False)
    console.print(
        f"  [dim]{total_warn} warning(s) — advisory; fixing pinned-template "
        f"anchors is an ADR-D re-pin event, not a gate failure.[/dim]"
    )


@click.group()
def template() -> None:
    """Stack-template tooling (deterministic render+parse gate)."""


@template.command()
@click.argument("names", nargs=-1)
@click.option(
    "--deterministic",
    is_flag=True,
    help="Run the deterministic render+parse gate (the only CLI tier).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="List every checked file, not just failures.",
)
def validate(names: Tuple[str, ...], deterministic: bool, verbose: bool) -> None:
    """Validate stack templates. Pass NAMES to scope to specific templates.

    Only ``--deterministic`` is implemented in the CLI; the AI prose audit is the
    ``/template-validate`` skill.
    """
    if not deterministic:
        console.print(
            "Only the [bold]--deterministic[/bold] tier is available from the CLI.\n"
            "  • deterministic render+parse gate:  "
            "[cyan]guardkit template validate --deterministic[/cyan]\n"
            "  • AI prose audit (unchanged):        [cyan]/template-validate[/cyan]"
        )
        return

    try:
        result = validate_templates(names=names or None)
    except ParseGateUnavailable as exc:
        console.print(f"[bold red]✗ GATE UNAVAILABLE[/bold red] {exc}", highlight=False)
        # Exit 2: could-not-run is not a pass and not a template failure.
        sys.exit(2)

    counts = result.counts()
    for fr in result.files:
        if fr.status is FileStatus.ERROR:
            console.print(f"[bold red]✗ PARSE ERROR[/bold red] [{fr.language}] {fr.rel_path}")
            for finding in fr.findings:
                console.print(
                    f"    {finding.kind} at {finding.line}:{finding.column}  "
                    f"{finding.snippet!r}",
                    highlight=False,
                )
        elif verbose and fr.status is FileStatus.OPTOUT:
            console.print(f"[yellow]○ opt-out[/yellow] {fr.rel_path} — {fr.reason}")
        elif verbose and fr.status is FileStatus.OK:
            console.print(f"[green]✓[/green] [{fr.language}] {fr.rel_path}")

    summary = (
        f"ok={counts['ok']} error={counts['error']} "
        f"opt-out={counts['optout']} skipped={counts['skipped']}"
    )
    if result.ok:
        console.print(f"[bold green]✓ TEMPLATE GATE PASSED[/bold green] ({summary})")
    else:
        console.print(f"[bold red]✗ TEMPLATE GATE FAILED[/bold red] ({summary})")

    # Second check: the report-only structure lint (PB-5/DIM2-F4). It runs
    # regardless of the parse-gate outcome and NEVER affects the exit code.
    _print_structure_lint()

    if not result.ok:
        sys.exit(1)
