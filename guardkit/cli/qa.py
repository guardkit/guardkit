"""``guardkit qa`` — QA format validation + JSON-Schema export (WS2 session B1).

v1 surface (scope-design §3 CLI table — the remaining subcommands land later:
``live-gate``/``walk`` in B3/B5, ``mutate``/``probe-boundaries`` in B6):

    guardkit qa validate <kind> <path>     # exit 0 valid, 1 invalid (loud)
    guardkit qa schema <kind> [--out F]    # JSON-Schema export
    guardkit qa kinds                      # list known kinds

No enforcement lives here — validation is on-demand; the gates that REFUSE on
missing/invalid instances are session B2's deliverable.
"""

from __future__ import annotations

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
        console.print(f"[bold red]✗ VALIDATION FAILED[/bold red]")
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
