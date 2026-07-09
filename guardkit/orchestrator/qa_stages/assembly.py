"""CLI assembly for the deeper stages — turn ``--task`` / ``--seam`` into a run.

Kept out of ``guardkit/cli/qa.py`` so the campaign/probe wiring is unit-testable
without click. Two entry points:

- :func:`assemble_mutation_campaign` — builds the mutant set (strip-auth-header
  and/or git revert-hunk operators) over a task's deliverable files and runs it
  in a throwaway sandbox, returning the campaign result.
- :func:`resolve_probe_target` — imports a ``module.path:attr`` ProbeTarget for a
  seam; an unresolved/omitted target yields :class:`UnconfiguredProbeTarget`
  (which raises loudly on ``decode`` — no silent green).
"""

from __future__ import annotations

import importlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from guardkit.orchestrator.qa_stages.boundary import (
    ProbeTarget,
    UnconfiguredProbeTarget,
)
from guardkit.orchestrator.qa_stages.errors import BoundaryProbeError, MutationError
from guardkit.orchestrator.qa_stages.findings import Finding
from guardkit.orchestrator.qa_stages.mutation import (
    Mutant,
    MutationCampaignResult,
    make_pytest_runner,
    revert_hunks_operator,
    run_mutation_campaign,
    split_diff_by_file,
    strip_auth_header_operator,
)
from guardkit.orchestrator.qa_stages.sandbox import MutationSandbox

_OPERATORS = ("strip-auth-header", "revert-hunk")


@dataclass
class MutationAssembly:
    """A prepared mutation run plus the campaign result and derived findings."""

    task_id: str
    mutant_count: int
    result: MutationCampaignResult
    findings: List[Finding]


def _git_diff(repo_root: Path, base: str, rel: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", base, "--", rel],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


def _changed_files(repo_root: Path, base: str) -> List[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", base],
        capture_output=True,
        text=True,
        check=False,
    )
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def build_mutants(
    repo_root: Path,
    source_files: Sequence[str],
    operators: Sequence[str],
    *,
    base: str | None = None,
) -> List[Mutant]:
    """Build the mutant set for ``source_files`` under the selected operators."""
    mutants: List[Mutant] = []
    for rel in source_files:
        src = repo_root / rel
        if "strip-auth-header" in operators and src.is_file():
            text = src.read_text(encoding="utf-8")
            mutants.extend(strip_auth_header_operator(rel, text))
        if "revert-hunk" in operators:
            if base is None:
                raise MutationError(
                    "the revert-hunk operator requires --base (a git ref to diff against)"
                )
            diff = _git_diff(repo_root, base, rel)
            by_file = split_diff_by_file(diff)
            for _rel, hunks in by_file.items():
                mutants.extend(revert_hunks_operator(_rel, hunks))
    return mutants


def assemble_mutation_campaign(
    repo_root: Path,
    task_id: str,
    *,
    source_files: Sequence[str] | None,
    test_command: Sequence[str],
    operators: Sequence[str] = ("strip-auth-header",),
    base: str | None = None,
    timeout: int = 600,
) -> MutationAssembly:
    """Assemble and run a mutation campaign for a task; derive its findings.

    ``source_files`` may be ``None`` when ``base`` is given (files are derived
    from the diff). Surviving mutants become non-blocking coverage-hole findings.
    """
    for op in operators:
        if op not in _OPERATORS:
            raise MutationError(f"unknown operator {op!r} (known: {_OPERATORS})")
    repo_root = Path(repo_root).resolve()
    if source_files is None:
        if base is None:
            raise MutationError("provide --files or --base so the deliverable set is known")
        source_files = _changed_files(repo_root, base)
    if not source_files:
        raise MutationError("no deliverable source files to mutate")
    if not test_command:
        raise MutationError("a test command is required to kill mutants")

    mutants = build_mutants(repo_root, source_files, operators, base=base)
    sandbox = MutationSandbox(repo_root)
    runner = make_pytest_runner(test_command, timeout=timeout)
    result = run_mutation_campaign(sandbox, mutants, runner)

    findings: List[Finding] = []
    for survivor in result.survivors:
        findings.append(
            Finding(
                kind="mutation-survivor",
                subject=task_id,
                site=survivor.site,
                summary=(
                    f"Mutant survived: the `{survivor.operator}` mutation at "
                    f"{survivor.site} did NOT break any test — a proven coverage "
                    f"hole (the behaviour this line implements is unpinned)."
                ),
                evidence=f"operator={survivor.operator} site={survivor.site} suite stayed green",
                suggested_pin=(
                    "Add/extend a test that asserts the behaviour at this site so "
                    "the mutation is killed (e.g. pin the auth header / the reverted change)."
                ),
            )
        )
    return MutationAssembly(
        task_id=task_id,
        mutant_count=len(mutants),
        result=result,
        findings=findings,
    )


def resolve_probe_target(spec: str | None) -> ProbeTarget:
    """Resolve a ``module.path:attr`` ProbeTarget, or the loud unconfigured default.

    ``attr`` may be a ProbeTarget instance or a zero-arg factory returning one.
    A ``None`` spec returns :class:`UnconfiguredProbeTarget` — honest "not wired"
    that raises on ``decode`` (never a vacuous clean posture).
    """
    if not spec:
        return UnconfiguredProbeTarget()
    if ":" not in spec:
        raise BoundaryProbeError(
            f"--target must be 'module.path:attr', got {spec!r}"
        )
    module_path, attr = spec.split(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise BoundaryProbeError(f"could not import probe module {module_path!r}: {exc}") from exc
    try:
        obj = getattr(module, attr)
    except AttributeError as exc:
        raise BoundaryProbeError(f"{module_path!r} has no attribute {attr!r}") from exc
    target = obj() if callable(obj) and not _looks_like_target(obj) else obj
    if not _looks_like_target(target):
        raise BoundaryProbeError(
            f"{spec!r} did not resolve to a ProbeTarget (needs `decode` + `sealed_errors`)"
        )
    return target


def _looks_like_target(obj: object) -> bool:
    return hasattr(obj, "decode") and hasattr(obj, "sealed_errors")
