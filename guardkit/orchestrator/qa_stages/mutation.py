"""ST-05 mutation stage — break the key behaviour, require the tests to go red.

The worked example (study-tutor retro L5, commit ``268c0bf``): deleting the auth
header left the wave's 13 unit tests green → auth-header pins were missing on
**four verbs**. A test that survives its own mutation is a *proven* coverage
hole, not an opinion.

**Discipline (absence-of-failure family):** a surviving mutant is meaningful
ONLY against a green baseline. If the un-mutated tests are already red, the stage
raises :class:`MutationError` ("cannot assess") — it never reports "no coverage
holes" from an un-runnable suite. Each mutation SITE is a separate mutant (the
auth header on verb A and verb B are two mutants), so a per-verb coverage hole is
attributable even when a sibling verb's mutant is killed.

Granularity note: mutations are applied per-site so a whole-file test run can
still attribute a surviving mutant to the exact line the mutation touched. Every
mutant runs in its own THROWAWAY sandbox (never the task branch — see
:mod:`~guardkit.orchestrator.qa_stages.sandbox`).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from guardkit.orchestrator.qa_stages.errors import MutationError
from guardkit.orchestrator.qa_stages.sandbox import MutationSandbox


# --------------------------------------------------------------------------- #
# Test outcome + runner
# --------------------------------------------------------------------------- #
@dataclass
class TestOutcome:
    """Result of running the task's test command in a sandbox."""

    green: bool
    returncode: int
    tail: str = ""

    @property
    def red(self) -> bool:
        return not self.green


#: A test runner takes a sandbox root and returns the outcome of the suite there.
TestRunner = Callable[[Path], TestOutcome]


def make_pytest_runner(
    command: Sequence[str],
    *,
    timeout: int = 600,
) -> TestRunner:
    """Build a :data:`TestRunner` that shells ``command`` with ``cwd=sandbox``.

    ``command`` is the task's own test command (e.g.
    ``[sys.executable, "-m", "pytest", "-q", "tests/unit"]``). A non-zero exit —
    including a timeout (124-style) — is RED; a mutation that leaves the suite
    green survived. Absence-of-failure: a collection/spawn error is red (an
    un-runnable suite is never a silent pass).
    """
    argv = list(command)

    def _run(sandbox_root: Path) -> TestOutcome:
        try:
            proc = subprocess.run(
                argv,
                cwd=str(sandbox_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            tail = (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else ""
            return TestOutcome(green=False, returncode=124, tail=tail + "\n[timeout]")
        except OSError as exc:  # spawn failure — red, never a silent green
            return TestOutcome(green=False, returncode=127, tail=f"[spawn error] {exc}")
        tail = (proc.stdout + "\n" + proc.stderr)[-2000:]
        return TestOutcome(green=proc.returncode == 0, returncode=proc.returncode, tail=tail)

    return _run


# --------------------------------------------------------------------------- #
# Mutants + operators
# --------------------------------------------------------------------------- #
@dataclass
class Mutant:
    """One mutation applied to a fresh sandbox in place.

    ``apply`` mutates the materialized sandbox (never the source tree). ``site``
    labels the exact location so a surviving mutant is attributable.
    """

    operator: str
    site: str
    apply: Callable[[Path], None]


#: A mutation operator inspects a source file and yields zero or more Mutants.
MutationOperator = Callable[[Path, str], List[Mutant]]


# Matches an ``"Authorization":`` (or ``'Authorization'``) KEY inside a header
# mapping — the value/expression after the colon is left untouched, so f-string
# braces and multi-line values are never mis-parsed. Renaming the KEY makes the
# header never get set under that name, which is exactly "delete the auth header"
# for any consumer that reads ``headers["Authorization"]`` / ``.get(...)``.
_AUTH_KEY = re.compile(
    r"""(?P<q1>['"])Authorization(?P<q2>['"])(?P<sep>\s*:)""",
    re.IGNORECASE,
)

#: The mutated key name — a real key the consumer will never look up.
_MUTATED_AUTH_KEY = "X-GuardkitMutatedAuth"


def strip_auth_header_operator(rel_path: str, text: str) -> List[Mutant]:
    """Per-site "delete the auth header" operator (the retro worked example).

    For each ``"Authorization":`` key in a header mapping it emits ONE mutant
    that renames just that key (value untouched), so the request silently goes
    out unauthenticated — the structure still runs, exactly like deleting the
    header. If the verb's test never asserts the header, the suite stays green
    and the mutant SURVIVES → a proven coverage hole for that verb.
    """
    mutants: List[Mutant] = []
    for match in _AUTH_KEY.finditer(text):
        start, end = match.span()
        line_no = text.count("\n", 0, start) + 1
        replacement = f"{match.group('q1')}{_MUTATED_AUTH_KEY}{match.group('q2')}{match.group('sep')}"
        mutated = text[:start] + replacement + text[end:]

        def _apply(sandbox_root: Path, _mut=mutated, _rel=rel_path) -> None:
            (sandbox_root / _rel).write_text(_mut, encoding="utf-8")

        mutants.append(
            Mutant(
                operator="strip-auth-header",
                site=f"{rel_path}:{line_no}",
                apply=_apply,
            )
        )
    return mutants


def revert_hunks_operator(
    rel_path: str,
    diff_hunks: Sequence[str],
) -> List[Mutant]:
    """Git-backed "revert the patch hunks" operator (scope §3.8).

    Each hunk of the task's own diff becomes one mutant that ``git apply -R``'s
    that single hunk in the sandbox — reverting the task's change for that hunk.
    If the suite stays green after a hunk is reverted, the task's behaviour
    change in that hunk is unpinned (a coverage hole). Requires a git sandbox.
    """
    mutants: List[Mutant] = []
    for idx, hunk in enumerate(diff_hunks, start=1):
        def _apply(sandbox_root: Path, _hunk=hunk) -> None:
            proc = subprocess.run(
                ["git", "-C", str(sandbox_root), "apply", "-R", "--recount", "-"],
                input=_hunk,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise MutationError(
                    f"could not reverse-apply hunk {_hunk[:80]!r}: {proc.stderr.strip()}"
                )

        mutants.append(
            Mutant(operator="revert-hunk", site=f"{rel_path}#hunk{idx}", apply=_apply)
        )
    return mutants


def split_diff_by_file(diff: str) -> dict[str, List[str]]:
    """Split a unified ``git diff`` into per-file lists of single-hunk patches.

    Each returned patch carries its file's ``diff --git`` / ``---`` / ``+++``
    header plus exactly one ``@@`` hunk, so it can be reverse-applied on its own.
    """
    by_file: dict[str, List[str]] = {}
    file_blocks = re.split(r"(?m)^(?=diff --git )", diff)
    for block in file_blocks:
        if not block.strip():
            continue
        header_lines: List[str] = []
        hunk_start = None
        lines = block.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith("@@"):
                hunk_start = i
                break
            header_lines.append(line)
        if hunk_start is None:
            continue
        m = re.search(r"(?m)^\+\+\+ b/(.+)$", block)
        rel = m.group(1).strip() if m else "unknown"
        header = "".join(header_lines)
        hunks: List[str] = []
        current: List[str] = []
        for line in lines[hunk_start:]:
            if line.startswith("@@"):
                if current:
                    hunks.append(header + "".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            hunks.append(header + "".join(current))
        if hunks:
            by_file.setdefault(rel, []).extend(hunks)
    return by_file


# --------------------------------------------------------------------------- #
# Campaign
# --------------------------------------------------------------------------- #
@dataclass
class MutantResult:
    """One mutant's verdict: survived (coverage hole) or killed (covered)."""

    operator: str
    site: str
    survived: bool
    returncode: int
    error: Optional[str] = None


@dataclass
class MutationCampaignResult:
    """The campaign outcome. Surviving mutants are the coverage-hole findings."""

    baseline_green: bool
    results: List[MutantResult] = field(default_factory=list)

    @property
    def survivors(self) -> List[MutantResult]:
        return [r for r in self.results if r.survived and r.error is None]

    @property
    def killed(self) -> List[MutantResult]:
        return [r for r in self.results if not r.survived and r.error is None]

    @property
    def errored(self) -> List[MutantResult]:
        return [r for r in self.results if r.error is not None]


def run_mutation_campaign(
    sandbox: MutationSandbox,
    mutants: Sequence[Mutant],
    run_tests: TestRunner,
) -> MutationCampaignResult:
    """Run a mutation campaign; each mutant gets a fresh throwaway sandbox.

    1. Baseline: materialize a clean sandbox and run the suite — it MUST be
       green, else raise :class:`MutationError` (absence-of-failure: a red
       baseline cannot certify "no coverage holes").
    2. Per mutant: materialize a fresh sandbox, apply the mutant, run the suite.
       Green after mutation → SURVIVED (coverage hole). Red → killed.
    """
    with sandbox.materialize() as baseline_box:
        baseline = run_tests(baseline_box.path)
    if baseline.red:
        raise MutationError(
            "mutation baseline is RED — cannot assess coverage holes against a "
            f"failing suite (rc={baseline.returncode}).\n{baseline.tail}"
        )

    results: List[MutantResult] = []
    for mut in mutants:
        with sandbox.materialize() as box:
            try:
                mut.apply(box.path)
            except MutationError as exc:
                results.append(
                    MutantResult(mut.operator, mut.site, survived=False,
                                 returncode=-1, error=str(exc))
                )
                continue
            outcome = run_tests(box.path)
        results.append(
            MutantResult(
                operator=mut.operator,
                site=mut.site,
                survived=outcome.green,
                returncode=outcome.returncode,
            )
        )
    return MutationCampaignResult(baseline_green=True, results=results)
