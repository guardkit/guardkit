"""Post-completion test verification for ``guardkit autobuild complete --verify``.

TASK-AB-VERIFYCLI01. R3 of the 2026-07-04 retro cross-reference showed
post-merge verification is a real aperture: ``after_wave: [2,3,4]`` left the
final waves ungated and ``tests/`` outside every gate, so nothing re-ran the
suite at completion. The slash-command workflow documented a ``--verify`` step
the Python CLI never implemented; this module is the ONE implementation both
entry points share (``cli-wrapper-shares-client-acquisition-path.md`` — a
CLI-only second implementation is exactly the divergence that rule documents).

Verification semantics (after-task check redesign, 31 October 2026):

- The verdict is each command's own exit code: 0 is ``passed`` and any other
  exit, 126 and 127 included, is ``failed`` (a declared script that ran and
  hit a missing program inside it failed; FEAT-8BB4). Only a check that never
  ran is ``unverified``: nothing is declared, the command's own program does
  not exist (``project_command_env.missing_program``, looked up before the
  run, the same rule as the after-task check), or it could not be started at
  all. ``unverified`` is not a pass.
- A timeout is ``failed`` (ran-and-hung is a real defect), never absent.
- The command is resolved in one place (``resolve_verify_command``): an
  explicit override, then the feature's smoke command, then the project's
  full check as declared in ``.guardkit/config.yaml``
  (``toolchain_declaration.full_check_parts``: the root ``test`` plus every
  component's and pattern part's ``test``, each in its own folder with its
  own declared ``test_timeout``). ``feature_check`` is not part of it.
  GuardKit never chooses a command a project did not declare.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from guardkit.orchestrator.launch_declaration import load_launch_declaration
from guardkit.orchestrator.project_command_env import (
    minimal_environment_note,
    missing_program,
    project_command_environment,
)

from guardkit.orchestrator.toolchain_declaration import (
    ToolchainDeclaration,
    full_check_parts,
    load_toolchain_declaration,
    resolve_component_cwd,
)
from guardkit.orchestrator import process_group

logger = logging.getLogger(__name__)

__all__ = [
    "VerificationResult",
    "NOTHING_DECLARED",
    "check_command_texts",
    "resolve_verify_command",
    "resolve_verify_command_with_declaration",
    "run_completion_verification",
]

# Full-suite verification needs more headroom than the 120s between-wave
# smoke default; 600s matches the smoke-gate schema's upper bound.
DEFAULT_VERIFY_TIMEOUT = 600

#: The source words when a project declares no check at all.
NOTHING_DECLARED = (
    "nothing declared: .guardkit/config.yaml declares no `toolchain` test "
    "command"
)


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a post-completion verification run.

    ``status`` is the enforcement source every display line must derive from
    (``display-must-derive-from-enforcement-source-not-proxy.md``): "verified"
    output is only legitimate when ``status == "passed"``, never inferred
    from "the completion succeeded".
    """

    status: str  # "passed" | "failed" | "unverified"
    command: str
    cwd: str
    returncode: Optional[int]
    detail: str
    output_tail: str = ""
    # Where the command came from — the same words ``resolve_verify_command``
    # returns, carried through so a receipt can say what was run and why that
    # command and not another.
    source: str = ""
    # The COMPLETE output of the run. ``output_tail`` is a 2000-character
    # excerpt kept for receipts and logs; it is far too short to hold the
    # names of every failing test when a suite fails badly (pytest's summary
    # block runs past 2000 characters at roughly twenty failures), so anything
    # that reads test names out of a run must read this field instead. Empty
    # only when the caller built the result by hand.
    full_output: str = ""

    @property
    def output_for_parsing(self) -> str:
        """The text to read test names out of — the whole run, never a tail.

        Falls back to the excerpt when the whole run was not recorded, so a
        result built by hand still parses; a real run always has the whole
        thing.
        """
        return self.full_output or self.output_tail or ""


def check_command_texts(declaration: Optional[ToolchainDeclaration]) -> List[str]:
    """The text of every command the full check can run, for the merge's
    judge-file rule: the root ``test`` and every component's and ``parts:``
    entry's ``test``."""
    if declaration is None:
        return []
    texts = [declaration.test] if declaration.test else []
    texts += [c.test for _, c in sorted((declaration.components or {}).items()) if c.test]
    texts += [entry.test for entry in declaration.parts or () if entry.test]
    return texts


def resolve_verify_command(
    repo_root: Path,
    smoke_command: Optional[str] = None,
    override: Optional[str] = None,
) -> Tuple[Optional[str], str, Optional[ToolchainDeclaration]]:
    """Resolve the verification for ``repo_root``.

    Precedence: explicit ``--verify-cmd`` override > the feature YAML's
    ``smoke_gates.command`` > the project's declared full check
    (:func:`resolve_verify_command_with_declaration`).

    Returns ``(command, source, declaration)``. ``command`` is the text shown
    in receipts, ``None`` when nothing is declared (the caller reports
    UNVERIFIED, never a pass). ``declaration`` is set when the full check is
    the declared one; :func:`run_completion_verification` then runs each part
    in its own folder.
    """
    if override:
        return override, "--verify-cmd override", None
    if smoke_command:
        return smoke_command, "feature smoke_gates.command", None
    try:
        declaration = load_toolchain_declaration(Path(repo_root))
    except Exception as exc:  # noqa: BLE001 - resolution never crashes a merge
        logger.warning(
            "Could not read the toolchain declaration in %s: %s", repo_root, exc
        )
        declaration = None
    return resolve_verify_command_with_declaration(repo_root, declaration)


def resolve_verify_command_with_declaration(
    repo_root: Path, declaration: Optional[ToolchainDeclaration]
) -> Tuple[Optional[str], str, Optional[ToolchainDeclaration]]:
    """The declared full check of ``declaration``, as the caller already read it.

    The merge reads ``.guardkit/config.yaml`` once with its own fail-closed
    reader (``merge_environment.read_merge_declarations``) and hands the
    declaration in here. With nothing declared the command is ``None``.
    """
    parts = full_check_parts(declaration, Path(repo_root))
    if not parts and not (declaration is not None and declaration.parts):
        return None, NOTHING_DECLARED, None
    assert declaration is not None
    # Said from the declaration, not from the folders found now: the check
    # is chosen on the target and the pattern parts are found in the joined
    # tree when it runs.
    pieces = [
        (p.test or "<nothing declared>") + ("" if p.cwd == "." else f" (in {p.cwd})")
        for p in parts
        if p.toolchain is None or p.name in (declaration.components or {})
    ]
    pieces += [
        f"{entry.test or '<nothing declared>'} (in each folder under "
        f"{entry.under} holding {entry.marker})"
        for entry in declaration.parts or ()
    ]
    text = pieces[0] if len(pieces) == 1 and parts and parts[0].cwd == "." else " ; ".join(pieces)
    return text, "repository toolchain declaration", declaration


def _install_part(
    folder: Path, install: str, timeout: int, env: Optional[dict]
) -> Optional[str]:
    """Run a part's declared install in its folder (argument list, no
    shell). ``None`` on success, else why it did not succeed."""
    import shlex

    try:
        argv = shlex.split(install)
    except ValueError as exc:
        return f"could not be split into arguments ({exc})"
    if not argv:
        return "is empty"
    try:
        run_env = (
            dict(env) if env is not None
            else project_command_environment(folder, load_launch_declaration(folder))
        )
        done = process_group.run_project_command(
            argv, cwd=str(folder), capture_output=True, text=True,
            timeout=timeout, env=run_env,
        )
    except subprocess.TimeoutExpired:
        return f"ran out of its {timeout} seconds"
    except OSError as exc:
        return f"could not start: {exc.strerror or type(exc).__name__}"
    if done.returncode != 0:
        tail = ((done.stderr or "") + (done.stdout or "")).strip()[-600:]
        return f"failed (exit {done.returncode}): {tail or '(no output)'}"
    return None


def _classify(returncode: int) -> Tuple[str, str]:
    if returncode == 0:
        return "passed", "verification command exited 0"
    return "failed", f"verification command failed (exit {returncode})"


def run_completion_verification(
    repo_root: Path,
    command: Optional[str],
    source: str,
    declaration: Optional[ToolchainDeclaration] = None,
    timeout: int = DEFAULT_VERIFY_TIMEOUT,
    env: Optional[dict] = None,
    own_process_group: bool = False,
) -> VerificationResult:
    """Run the resolved verification in ``repo_root``.

    With ``declaration`` (the declared full check), every part of
    :func:`toolchain_declaration.full_check_parts`, found in ``repo_root``
    now, runs its ``test`` once in its own folder, each within its own
    declared ``test_timeout`` (the root's is the top-level one); ``timeout``
    then bounds only a part's install. The result is ``failed`` if any part failed, otherwise
    ``unverified`` if any part could not run (nothing declared for it, or it
    could not start), otherwise ``passed``. Without it, ``command`` runs at
    ``repo_root``.

    Never raises. Only ``passed`` may ever be rendered as success. ``env``
    and ``own_process_group`` are as for :func:`_run_one`.
    """
    cwd = str(repo_root)
    if not command:
        return VerificationResult(
            status="unverified",
            command="",
            cwd=cwd,
            returncode=None,
            detail=f"UNVERIFIED: {source}",
            source=source,
        )
    if declaration is None:
        return _run_one(
            Path(repo_root), command, source, timeout, env, own_process_group
        )
    parts = full_check_parts(declaration, Path(repo_root))
    if not parts:
        return VerificationResult(
            status="unverified", command=command, cwd=cwd, returncode=None,
            detail=f"UNVERIFIED: {NOTHING_DECLARED}", source=source,
        )
    results: List[Tuple[str, VerificationResult]] = []
    for part in parts:
        label = part.name if part.cwd == "." else f"{part.name} (in {part.cwd})"
        if not part.test:
            results.append((label, VerificationResult(
                status="unverified", command="", cwd=part.cwd, returncode=None,
                detail=f"nothing declared for part {label}", source=source,
            )))
            continue
        try:
            folder = resolve_component_cwd(Path(repo_root), part.cwd)
        except ValueError as exc:
            results.append((label, VerificationResult(
                status="unverified", command=part.test, cwd=part.cwd,
                returncode=None, detail=str(exc), source=source,
            )))
            continue
        if part.toolchain is not None and part.toolchain.install:
            problem = _install_part(
                folder, part.toolchain.install,
                min(part.toolchain.install_timeout, timeout), env,
            )
            if problem is not None:
                results.append((label, VerificationResult(
                    status="unverified", command=part.test, cwd=part.cwd,
                    returncode=None, source=source,
                    detail=f"the declared install (`{part.toolchain.install}`) "
                    f"for part {label} {problem}",
                )))
                continue
        part_timeout = (part.toolchain or declaration).test_timeout
        results.append(
            (label, _run_one(
                folder, part.test, source, part_timeout, env, own_process_group
            ))
        )
    if len(results) == 1:
        return replace(results[0][1], command=command)
    statuses = [r.status for _, r in results]
    status = (
        "failed" if "failed" in statuses
        else "unverified" if "unverified" in statuses
        else "passed"
    )
    shown = [(label, r) for label, r in results if r.status == status]
    detail = "; ".join(f"{label}: {r.detail}" for label, r in shown)
    full = "\n".join(
        f"=== {label}: {r.command}\n{r.full_output or r.output_tail}"
        for label, r in results
    )
    return VerificationResult(
        status=status,
        command=command,
        cwd=cwd,
        returncode=next((r.returncode for _, r in shown if r.returncode), None)
        if status == "failed" else (0 if status == "passed" else None),
        detail=detail,
        output_tail=full[-2000:],
        source=source,
        full_output=full,
    )


def _run_one(
    repo_root: Path,
    command: str,
    source: str,
    timeout: int,
    env: Optional[dict],
    own_process_group: bool,
) -> VerificationResult:
    """Run one command in ``repo_root``. Never raises.

    ``env`` is the command's whole environment. ``None`` (every caller but
    the merge) builds it here from nothing, with ``repo_root``'s own
    ``launch:`` block (``project_command_env``): never a copy of this
    process's environment, which holds the factory's credentials. The merge
    passes the minimal environment it builds the same way (13 October 2026,
    item 2a).

    ``own_process_group`` (the merge passes it) runs the command in a process
    group of its own, so a timeout ends everything the command started, not
    only the shell (``process_group.run_in_own_group``). Off, the command
    runs exactly as before.
    """
    cwd = str(repo_root)
    logger.info(
        "Post-completion verification (%s): %s (cwd=%s, timeout=%ds)",
        source,
        command,
        cwd,
        timeout,
    )
    built_here = env is None
    try:
        # Built from nothing (13 October 2026) unless the caller (the merge)
        # hands in the environment it built the same way.
        run_env: Dict[str, str] = (
            project_command_environment(
                repo_root, load_launch_declaration(repo_root)
            )
            if env is None
            else dict(env)
        )
    except OSError as exc:
        return VerificationResult(
            status="unverified",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification command could not start: {exc}",
            source=source,
        )
    missing = missing_program(command, repo_root, run_env)
    if missing is not None:
        return VerificationResult(
            status="unverified",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification command could not start: {missing}",
            source=source,
        )
    if own_process_group:
        from guardkit.orchestrator.process_group import run_in_own_group

        try:
            run = run_in_own_group(
                command,
                shell=True,
                cwd=cwd,
                env=run_env,
                timeout=timeout,
            )
        except OSError as exc:
            return VerificationResult(
                status="unverified",
                command=command,
                cwd=cwd,
                returncode=None,
                detail=f"verification command could not start: {exc}",
                source=source,
            )
        if run.timed_out:
            return VerificationResult(
                status="failed",
                command=command,
                cwd=cwd,
                returncode=None,
                detail=f"verification timed out after {timeout}s",
                output_tail=run.stdout[-2000:],
                source=source,
                full_output=run.stdout,
            )
        proc = subprocess.CompletedProcess(
            command, run.returncode, run.stdout, run.stderr
        )
        return _noted(
            _verification_from_run(proc, command, cwd, source),
            run_env if built_here else None,
        )

    try:
        # TS-lane D.1b (design §B.5): the second declared-command shell site.
        # ``env=`` is EXPLICIT so the resolution rule is visible where the
        # command runs: worktree/repo cwd + the daemon PATH, on which node
        # resolves ONLY via the D.0 symlink fence. Never source nvm here.
        proc = process_group.run_project_command(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        # Ran-and-hung is a genuine defect (runtime-parity L3 precedent):
        # a suite that hangs post-merge must block, never read as absent.
        stdout = exc.stdout or b""
        tail = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else str(stdout)
        return VerificationResult(
            status="failed",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification timed out after {timeout}s",
            output_tail=tail[-2000:],
            source=source,
            full_output=tail,
        )
    except OSError as exc:
        return VerificationResult(
            status="unverified",
            command=command,
            cwd=cwd,
            returncode=None,
            detail=f"verification command could not start: {exc}",
            source=source,
        )

    return _noted(
        _verification_from_run(proc, command, cwd, source),
        run_env if built_here else None,
    )


def _noted(
    result: VerificationResult, env: Optional[Dict[str, str]]
) -> VerificationResult:
    """A failed result's detail, with the settings the factory held back.

    Names only, never values (13 October 2026). ``env`` is ``None`` when the
    caller chose the environment, and the result is then unchanged.
    """
    if env is None or result.status != "failed":
        return result
    return replace(result, detail=f"{result.detail}. {minimal_environment_note(env)}")


def _verification_from_run(
    proc: "subprocess.CompletedProcess",
    command: str,
    cwd: str,
    source: str,
) -> VerificationResult:
    """Classify a finished run by its exit code alone."""
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    status, detail = _classify(proc.returncode)
    return VerificationResult(
        status=status,
        command=command,
        cwd=cwd,
        returncode=proc.returncode,
        detail=detail,
        output_tail=output[-2000:],
        source=source,
        full_output=output,
    )
