"""``guardkit qa`` — QA format validation + the live-gate runner (WS2 B1 + B3).

v1 surface (scope-design §3 CLI table — ``walk`` is B5):

    guardkit qa validate <kind> <path>     # exit 0 valid, 1 invalid (loud)
    guardkit qa schema <kind> [--out F]    # JSON-Schema export
    guardkit qa kinds                      # list known kinds
    guardkit qa live-gate --feature <id> --target <env> [--gates ..]
    guardkit qa review [range selectors]          # R-b advisory code review (S5)
    guardkit qa classify-scenarios --feature-file F --repo R [--json]
                                                  # the routing law by rule alone over one
                                                  # .feature; writes nothing, never asks the model

``validate``/``schema``/``kinds`` are on-demand format tools (no enforcement —
that is B2). ``live-gate`` runs the repo's registered F4 gates and emits the
results envelope on stdout for the forge adapter (scope-design §3). The
``mutate`` and ``probe-boundaries`` commands were deleted in the cull (27
October 2026, GKT-154).

``review`` (R-b, options paper ``factory-code-quality-seat-options-2026-07.md``
stage S-5) is the **on-demand advisory code-review entry**: the coordinator runs
it over any range — the R-b inspector reads a git diff on a local seat and emits
an F14 review-findings record with reasons. It is **advisory-only and flag-gated
default-OFF** (``qa.review_seat`` / ``GUARDKIT_QA_REVIEW_SEAT``): when the flag is
OFF the command is a provable no-op (exit 0, no git, no seat); when ON it emits
and exits 0 — it NEVER blocks. Promotion to a blocking gate is the S-4
calibration bar (Rich's numbers), not this command. The same advisory review is
wired as a step in the ``autobuild complete --verify`` gate flow (behind the
same flag), where it attaches its F14 record as a flow artifact and never
changes the completion's exit code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

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
    repo_root: Path,
) -> None:
    """Run the repo's registered F4 gates and emit the results envelope.

    Deterministic runner (DF-015 clause 1). Prints the F4 results envelope as
    JSON on stdout (the forge adapter parses its ``verdict``); exit code mirrors
    the verdict (0 pass, 1 fail, 3 instrument_fail, 4 environment_fail).
    """
    # Imported lazily so `guardkit qa validate` has no orchestrator import cost.
    from guardkit.orchestrator.live_gate import LiveGateError, LiveGateRunner

    requested = [g.strip() for g in gates.split(",") if g.strip()] if gates else None
    runner = LiveGateRunner(repo_root)
    try:
        envelope = runner.run(
            feature_id,
            target_env,
            requested_gate_ids=requested,
        )
    except (QAFormatError, LiveGateError) as exc:
        # A missing or unreadable registry, or a gate script that is not
        # there, means there is nothing to run.
        console.print("[bold red]✗ live-gate could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    # The envelope on stdout is the contract for the forge adapter.
    click.echo(json.dumps(envelope.model_dump(mode="json"), indent=2))
    sys.exit(_VERDICT_EXIT_CODES.get(envelope.verdict, 1))


@qa.command(name="normalize-stamps")
@click.option("--feature", "feature_id", required=True, help="Feature id (FEAT-X) to stamp.")
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Target repo root (default: cwd). Reads .guardkit/features/<id>.yaml under it.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Classify and print the result; write nothing.",
)
@click.option(
    "--ignore-existing",
    is_flag=True,
    default=False,
    help="Classify EVERY title as if unstamped (dry-run only; the reproduction proof).",
)
@click.option(
    "--http-surface/--no-http-surface",
    "http_surface",
    default=None,
    help=(
        "Override the repo HTTP-surface detection that gates R9 (hurl). Without "
        "it the surface is STRUCTURAL: a hurl gate in qa/gates/registry.yaml, "
        "`surface: http` in .guardkit/config.yaml, or an exact web-framework "
        "dependency in pyproject/package.json — never free text."
    ),
)
@click.option(
    "--no-model",
    "no_model",
    is_flag=True,
    default=False,
    help=(
        "Classify by rule only; never ask the model fallback about titles no "
        "rule decides."
    ),
)
def normalize_stamps(
    feature_id: str,
    repo_root: Path,
    dry_run: bool,
    ignore_existing: bool,
    http_surface: bool | None,
    no_model: bool,
) -> None:
    """THE STAMP NORMALIZER — mint ``verifier:`` stamps by rule (R1–R10) and WRITE them.

    Rules doc: ai-transition/docs/routing-law-stamp-normalizer-rules-2026-08-15.md.
    Rich's conditions: it WRITES the feature YAML's ``scenarios:`` map (only titles
    lacking a stamp — never overwrites). Titles no rule can decide are handed to a
    model (ruled 2026-08-31; only those titles, answer checked against the closed
    list, listed under `model_stamped`); anything still undecided is left
    unstamped and named under `refused`. With ``--no-model`` the model is never
    asked (the JSON's `model_outcome.status` is `switched_off`). Prints the
    result as JSON on stdout (forge's hook parses it); exit 0 when it ran
    (whether or not titles were left unstamped; the cull, 27 October 2026), 2
    when it cannot run (the feature file is missing or cannot be read).
    """
    from guardkit.orchestrator.stamp_normalizer import (
        StampNormalizerError,
        normalize_feature,
    )

    features_dir = repo_root / ".guardkit" / "features"
    yaml_path = features_dir / f"{feature_id}.yaml"
    if not yaml_path.exists():
        alt = features_dir / f"{feature_id}.yml"
        if alt.exists():
            yaml_path = alt
    if not yaml_path.exists():
        payload = {
            "feature_id": feature_id,
            "error": f"feature file not found: {yaml_path}",
            "refused": [],
        }
        click.echo(json.dumps(payload, indent=2))
        console.print(f"[bold red]✗ normalize-stamps: {payload['error']}[/bold red]", highlight=False)
        sys.exit(2)

    try:
        result = normalize_feature(
            yaml_path,
            None,
            repo_root,
            dry_run=dry_run,
            ignore_existing=ignore_existing,
            repo_has_http_surface=http_surface,
            use_model=not no_model,
        )
    except StampNormalizerError as exc:
        payload = {"feature_id": feature_id, "error": str(exc), "refused": [], "written": False}
        click.echo(json.dumps(payload, indent=2))
        console.print("[bold red]✗ normalize-stamps could not run[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    if result.model_stamped:
        # THE MODEL FALLBACK (RULED 2026-08-31): the titles no rule could
        # decide, and what the model decided for each. Named in the JSON
        # (`model_stamped`) AND echoed on stderr ahead of the JSON, so nobody
        # mistakes a model-decided stamp for a rule-decided one.
        err_console = Console(stderr=True)
        err_console.print(
            f"[bold yellow]! normalize-stamps: the model decided "
            f"{len(result.model_stamped)} scenario(s) no rule could decide:[/bold yellow]",
            highlight=False,
        )
        for title in result.model_stamped:
            err_console.print(
                f"  - {title} -> {result.stamped.get(title, '?')}",
                highlight=False,
                soft_wrap=True,
            )
    if result.operator_stamped:
        # L3: an operator stamp is never silent — it is attended human work
        # handed to Rich. Named in the JSON (`operator_stamped`) AND in the
        # human echo (stderr, ahead of the JSON, so the hook's stdout parse
        # stays clean). Each title says whether a rule or the model decided it.
        err_console = Console(stderr=True)
        err_console.print(
            f"[bold yellow]! normalize-stamps minted `operator` (attended human work) "
            f"for {len(result.operator_stamped)} scenario(s):[/bold yellow]",
            highlight=False,
        )
        for title in result.operator_stamped:
            how = "decided by the model" if title in result.model_stamped else "rule R10"
            err_console.print(f"  - {title} ({how})", highlight=False, soft_wrap=True)
    click.echo(json.dumps(result.to_dict(), indent=2))
    sys.exit(0)


def _find_feature_file(feature_file: Path, repo_root: Path) -> Path | None:
    """Where ``--feature-file`` points. An absolute path is taken as it is; a
    relative one is looked for under ``--repo`` first (the way feature paths
    are written everywhere else in guardkit), then under the current
    directory. ``None`` = nowhere."""
    if feature_file.is_absolute():
        return feature_file if feature_file.exists() else None
    for base in (repo_root, Path.cwd()):
        candidate = base / feature_file
        if candidate.exists():
            return candidate
    return None


@qa.command(name="classify-scenarios")
@click.option(
    "--feature-file",
    "feature_file",
    required=True,
    type=click.Path(path_type=Path),
    help=(
        "The Gherkin .feature file to classify. A relative path is looked for "
        "under --repo first, then under the current directory."
    ),
)
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Target repo root (default: cwd). Its manifests decide whether the wire rule (hurl) is armed.",
)
@click.option(
    "--http-surface/--no-http-surface",
    "http_surface",
    default=None,
    help=(
        "Override the repo HTTP-surface detection that gates R9 (hurl). Without "
        "it the surface is STRUCTURAL: a hurl gate in qa/gates/registry.yaml, "
        "`surface: http` in .guardkit/config.yaml, or an exact web-framework "
        "dependency in pyproject/package.json — never free text."
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print the result as exactly one JSON object on stdout (forge's spec leg parses it).",
)
def classify_scenarios(
    feature_file: Path,
    repo_root: Path,
    http_surface: bool | None,
    as_json: bool,
) -> None:
    """Say, by rule alone, which worked examples in one .feature file can be proven.

    The routing law's dry run for a spec that has no plan yet (2026-09-07, the
    rewrite-on-refusal lane): forge runs it on the committed draft before the
    spec card opens, so an example no rule can prove goes back to the spec
    writer before Rich is asked anything. For every scenario in the file it
    prints the home the rules would mint (the rule R1-R10 and the verifier
    word) or that the scenario is refused. Same rules, same order and same
    HTTP-surface detection as ``normalize-stamps``; the model fallback is
    never asked. It reads the .feature and the repo's manifests and writes
    nothing anywhere — no feature YAML is read or touched.

    Exit 0 whether or not anything is refused (the output says which:
    ``refused_titles``). Exit 2 only when it cannot run (the file is missing
    or cannot be read); with ``--json`` that is one ``{"error": "..."}``
    object on stdout.
    """
    from guardkit.orchestrator.stamp_normalizer import (
        NormalizeContext,
        StampNormalizerError,
        classify_scenario,
        detect_repo_http_surface,
        extract_scenario_blocks,
    )

    given = str(feature_file)

    def _cannot_run(message: str) -> None:
        if as_json:
            click.echo(json.dumps({"error": message}, indent=2))
        click.echo(f"classify-scenarios: {message}", err=True)
        sys.exit(2)

    path = _find_feature_file(feature_file, repo_root)
    if path is None:
        where = "" if feature_file.is_absolute() else f" (looked under {repo_root} and the current directory)"
        _cannot_run(f"feature file not found: {given}{where}")
        return  # pragma: no cover — _cannot_run exits
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _cannot_run(f"feature file cannot be read: {path} ({exc})")
        return  # pragma: no cover — _cannot_run exits

    if http_surface is None:
        has_http, evidence = detect_repo_http_surface(repo_root)
    else:
        has_http = bool(http_surface)
        evidence = (
            "overridden by the caller (--http-surface)"
            if has_http
            else "overridden by the caller (--no-http-surface)"
        )
    ctx = NormalizeContext(repo_has_http_surface=has_http, http_surface_evidence=evidence)

    try:
        blocks = extract_scenario_blocks(text)
    except StampNormalizerError as exc:
        _cannot_run(f"feature file could not be parsed: {path} ({exc})")
        return  # pragma: no cover — _cannot_run exits

    rows = []
    homes = []
    refused_titles: list[str] = []
    for block in blocks:
        home = classify_scenario(block.title, block.steps_text, ctx, annotations=block.annotations)
        homes.append(home)
        rows.append(
            {
                "title": block.title,
                "home": home.verifier if home is not None else None,
                "rule": home.rule if home is not None else None,
                "refused": home is None,
            }
        )
        if home is None and block.title not in refused_titles:
            refused_titles.append(block.title)

    payload = {
        "feature_file": given,
        "repo_has_http_surface": has_http,
        "http_surface_evidence": evidence,
        "scenarios": rows,
        "refused_titles": refused_titles,
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        surface_word = "yes" if has_http else "no"
        click.echo(f"{len(rows)} scenario(s) in {given}; HTTP surface: {surface_word} ({evidence})")
        for row, home in zip(rows, homes):
            if home is None:
                click.echo(f"  - {row['title']} -> refused: no rule decides it")
            else:
                click.echo(f"  - {row['title']} -> {home.verifier} ({home.rule}: {home.evidence})")
    if refused_titles:
        # One plain line on stderr so a person reading a log sees the refusal
        # without parsing the JSON; stdout stays exactly one object.
        click.echo(
            f"classify-scenarios: {len(refused_titles)} of {len(rows)} scenario(s) cannot be "
            f"proven by rule: " + "; ".join(refused_titles),
            err=True,
        )
    sys.exit(0)


@qa.command(name="review")
@click.option(
    "--repo",
    "repo_root",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    help="Repo root to review (default: cwd).",
)
@click.option(
    "--base",
    default=None,
    help="Review a range: 'git diff <base> [<head>]' (any range, e.g. main, "
    "or a 'main..feature' expression).",
)
@click.option(
    "--head",
    default=None,
    help="Range head, paired with --base. Omit for a single-ended range/expr.",
)
@click.option("--commit", "commit", default=None, help="Review one commit's diff (git show).")
@click.option("--merge", "merge", default=None, help="Review a merge commit vs its first parent.")
@click.option(
    "--staged",
    is_flag=True,
    default=False,
    help="Review the staged working tree only (git diff --cached).",
)
@click.option(
    "--unstaged",
    is_flag=True,
    default=False,
    help="Review unstaged working-tree changes only (git diff).",
)
@click.option(
    "--seat",
    "model",
    default=None,
    help=(
        "Local reviewer seat (qwen36-workhorse | gemma4-coach). Default: "
        "GUARDKIT_REVIEW_SEAT_MODEL; with neither set, no model is called."
    ),
)
@click.option(
    "--write/--no-write",
    "write",
    default=True,
    help="Write the F14 record to qa/review-<id>.yaml (default: write).",
)
@click.option(
    "--advisory/--blocking",
    "advisory",
    default=True,
    help="Advisory (default; exit 0 always). Blocking mode is gated on the S-4 "
    "calibration bar and not yet available.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Also emit the F14 record as JSON on stdout.",
)
def review(
    repo_root: Path,
    base: str | None,
    head: str | None,
    commit: str | None,
    merge: str | None,
    staged: bool,
    unstaged: bool,
    model: str | None,
    write: bool,
    advisory: bool,
    as_json: bool,
) -> None:
    """R-b advisory code review over any range — emit F14 findings, never block.

    The inspector: reads a git diff on a local seat and writes up findings with
    reasons (F14 review-findings). Advisory-only and flag-gated default-OFF
    (``qa.review_seat`` / ``GUARDKIT_QA_REVIEW_SEAT``) — when OFF it is a provable
    no-op; when ON it emits and exits 0. Promotion to a blocking gate is the S-4
    calibration bar, not this command.

    \b
    Subject (choose one; default = the whole working tree):
        --base main [--head feat]   an arbitrary range
        --commit <sha>              one commit
        --merge <sha>               a merge vs its first parent
        --staged / --unstaged       the working tree, narrowed

    \b
    Exit codes:
        0  advisory outcome (no-op / clean / findings / a named seat error)
        2  the requested range could not be read, or bad options
    """
    from guardkit.qa.diff_ingest import (
        DiffIngestError,
        ingest_commit,
        ingest_merge,
        ingest_range,
        ingest_working_tree,
    )
    from guardkit.qa.review_seat import (
        is_review_seat_enabled,
        run_advisory_review,
    )

    if not advisory:
        console.print(
            "[bold red]✗[/bold red] --blocking is not available: a blocking "
            "review gate is gated on the S-4 calibration bar (Rich's catch-rate "
            "floor + over-flag ceiling). This lane ships advisory-only.",
            highlight=False,
        )
        sys.exit(2)

    # Exactly one subject selector (working-tree scope flags are one group).
    selectors = [
        ("--base", base is not None),
        ("--commit", commit is not None),
        ("--merge", merge is not None),
        ("--staged/--unstaged", staged or unstaged),
    ]
    chosen = [name for name, on in selectors if on]
    if len(chosen) > 1:
        console.print(
            f"[bold red]✗[/bold red] choose one review subject, got: "
            f"{', '.join(chosen)}",
            highlight=False,
        )
        sys.exit(2)
    if staged and unstaged:
        console.print(
            "[bold red]✗[/bold red] --staged and --unstaged are mutually exclusive.",
            highlight=False,
        )
        sys.exit(2)
    if head is not None and base is None:
        console.print(
            "[bold red]✗[/bold red] --head requires --base.", highlight=False
        )
        sys.exit(2)

    # Flag-gate FIRST: default-OFF ⇒ a provable no-op (no git, no seat). The
    # coordinator opts in per run with GUARDKIT_QA_REVIEW_SEAT=1 (or the repo's
    # qa.review_seat), mirroring qa.enforce_tier1.
    if not is_review_seat_enabled(Path(repo_root)):
        console.print(
            "[yellow]○ review seat OFF[/yellow] (qa.review_seat / "
            "GUARDKIT_QA_REVIEW_SEAT) — no-op. Set the flag to run the advisory "
            "review. This never blocks; it is advisory until the S-4 bar."
        )
        sys.exit(0)

    # Build the review subject (the one genuinely-new S-1 piece). A range that
    # cannot be read is a loud config error (exit 2) — never a faked empty review.
    try:
        if base is not None:
            payload = ingest_range(Path(repo_root), base, head)
        elif commit is not None:
            payload = ingest_commit(Path(repo_root), commit)
        elif merge is not None:
            payload = ingest_merge(Path(repo_root), merge)
        elif staged:
            payload = ingest_working_tree(Path(repo_root), scope="staged")
        elif unstaged:
            payload = ingest_working_tree(Path(repo_root), scope="unstaged")
        else:
            payload = ingest_working_tree(Path(repo_root), scope="all")
    except DiffIngestError as exc:
        console.print("[bold red]✗ could not read the review subject[/bold red]", highlight=False)
        console.print(str(exc), highlight=False)
        sys.exit(2)

    outcome = run_advisory_review(
        Path(repo_root), payload, model=model, write=write
    )
    _display_review_outcome(outcome, as_json=as_json)
    # Advisory: ALWAYS exit 0. A seat outage / parse failure is a named result,
    # not a failure of this command.
    sys.exit(0)


def _display_review_outcome(outcome, as_json: bool = False) -> None:
    """Render an advisory :class:`ReviewOutcome` — used by the CLI and the
    autobuild gate-flow step. Advisory throughout: an error is a NAMED line,
    never a non-zero verdict."""
    import json as _json

    from rich.markup import escape

    console.print()
    if not outcome.enabled:
        note = outcome.notes[0] if outcome.notes else "review seat OFF — no-op"
        console.print(f"[yellow]○ {escape(note)}[/yellow]")
        return
    if outcome.error is not None:
        # ON but the seat could not be reached / its output could not be parsed.
        console.print(
            Panel(
                f"[yellow]○ advisory review did not emit[/yellow]\n\n"
                f"{escape(outcome.error)}\n\n"
                "Advisory: this never blocks. The seat outage/parse failure is "
                "recorded as-is (honesty-to-state), not a faked clean review.",
                title="Review Advisory (no record)",
                border_style="yellow",
            )
        )
        return

    record = outcome.record
    total = record.stats.findings_total
    header = (
        f"[green]✓ clean[/green]" if total == 0 else f"[yellow]⚠ {total} finding(s)[/yellow]"
    )
    lines = [
        f"{header}  ·  subject: {escape(record.subject.kind)} "
        f"{escape(record.subject.ref)}",
        f"confirmed {record.stats.confirmed} · refuted {record.stats.refuted} "
        f"· refutations attempted {record.stats.refutations_attempted}",
    ]
    if outcome.emitted_path:
        lines.append(f"[dim]F14 record →[/dim] {escape(outcome.emitted_path)}")
    for note in outcome.notes:
        lines.append(f"[dim]note:[/dim] {escape(note)}")
    console.print(
        Panel(
            "\n".join(lines),
            title="Advisory Code Review (R-b) — advisory, never blocks",
            border_style="green" if total == 0 else "yellow",
        )
    )
    for f in record.findings:
        console.print(
            f"  [yellow]•[/yellow] [{escape(f.severity)}/{escape(f.dimension)}/"
            f"{escape(f.status)}] {escape(f.summary)}"
        )
    if as_json:
        click.echo(_json.dumps(record.model_dump(mode="json"), indent=2))


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
