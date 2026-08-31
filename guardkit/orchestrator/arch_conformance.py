"""Watch where the code sits against the repo's own architecture rules, and write it down.

WHAT THIS IS, AND WHAT IT IS NOT (2026-08-30)
---------------------------------------------
A repository can write down how it is meant to be built — "database queries live in
crud.py", "one feature does not import another feature" — in
``docs/architecture-rules.yaml``, and ``guardkit.conformance`` reads that file and
reports every place the code sits somewhere the rule did not name.

This module is the first and smallest step of wiring that checker into the build: after
each Coach turn it runs the checker over the build worktree and writes the checker's
own facts-only report next to that turn's Coach verdict.

**Nothing reads the receipt.** It changes no Coach verdict, raises no issue for the
Player, appears on no card, and is read by nothing at merge time. There is no switch to
turn it on or off, because there is nothing to turn on. It writes one file and logs one
line. That is deliberately the whole of it: the design's ladder puts watching first, so
that the receipts exist to be looked at before anything is allowed to act on them.

WHAT IT COSTS A BUILD
---------------------
Almost nothing, and nothing at all in a repository that has not written a rules file.
The checker reads the rules file before it reads any source, so a repository without one
returns immediately and this writes one small receipt saying so. Most repositories in
this estate have no rules file yet; that must cost a build one receipt and no more.

Absence is recorded, never silent. A missing rules file produces the checker's own
honest "could not run" report — nothing was checked, which is not the same as clean.

IT NEVER BREAKS A BUILD
-----------------------
Everything here sits inside one try/except (the same discipline as the Hurl twin
coverage check and the QAV shadow). If the checker raises, or the receipt cannot be
written, this logs one warning and the build carries on exactly as it would have.

TELLING THE CODE GENERATOR (2026-08-31)
---------------------------------------
The second half of this module is the step after watching: when the switch
``GUARDKIT_ARCH_CONFORMANCE_BLOCKING`` is set, a place in the code the code generator
just wrote that sits where this repository's own rules do not put it comes back to it
as one fix-this issue on its next turn, and no person is involved.

Nothing new was built to do that. The build loop already runs declared "run this
command; exit 0 is the pass" checks for a task, freezes them before the first turn,
and turns a failure into a must-fix issue in the reviewer's feedback. So this
synthesises one such check -- :func:`build_arch_conformance_rule` -- and the existing
path carries it. The command it runs is this module, run as a program
(:func:`main`), which is the only place that decides anything:

* It judges the task **only on the files that task changed.** This is the whole of the
  design and it is not optional. The pilot repository's main branch carries three
  known places on purpose, as the checker's own acceptance test; a whole-tree check
  would fail every task in every build forever, on somebody else's code. The starting
  commit is read once, before the first turn, when the worktree still holds exactly
  what the task started from, and the command compares against that -- including files
  git is not yet tracking, so a brand-new file cannot slip past unread.
* **It never becomes a wall.** If the checker cannot run -- no rules file, a rules file
  it cannot read, git not answering, anything at all -- it says so in one line and
  exits 0. A check that cannot run must not stop a build.
* **The words it prints are the checker's own**: the rule's id, the file and line, and
  the sentence the rule quotes from this repository's architecture record, word for
  word. No score, no severity, no telling-off. Whoever reads it draws the conclusion.

With the switch unset -- the default -- none of this happens: no rule is synthesised,
no command runs, no verdict changes, and the receipt above is still written exactly as
before.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

# The rules file this looks for in the build worktree. The checker owns the same
# constant; it is repeated here only so the log lines and the docstring above can name
# it without importing the checker at module load.
RULES_RELATIVE_PATH = "docs/architecture-rules.yaml"


def _receipt_path(worktree_path: Path, task_id: str, turn: int) -> Path:
    """Where this turn's receipt goes: beside the turn's Coach verdict.

    Uses the ``paths.py`` template so there is one place that knows the layout, with a
    literal fallback so an import quirk can never stop the receipt being written.
    """
    rel = ".guardkit/autobuild/{task_id}/arch_conformance_turn_{turn}.json"
    try:
        from guardkit.orchestrator.paths import TaskArtifactPaths

        return TaskArtifactPaths.arch_conformance_path(task_id, turn, Path(worktree_path))
    except Exception:  # noqa: BLE001 — an import quirk must not stop the receipt
        return Path(worktree_path) / rel.format(task_id=task_id, turn=turn)


def _relative_files(worktree_path: Path, changed_files: Optional[Iterable[str]]) -> list[str]:
    """The task's touched files as repository-relative POSIX paths.

    The Player reports the files it created and modified; some entries arrive absolute
    and some already relative. The checker compares them against paths it built with
    ``relative_to(repo).as_posix()``, so both shapes are put into that one shape here.
    Anything outside the worktree is dropped: a path this repository does not contain
    can never match a file the checker read.
    """
    root = Path(worktree_path).resolve()
    out: list[str] = []
    for entry in changed_files or []:
        if not entry:
            continue
        p = Path(str(entry))
        try:
            if p.is_absolute():
                rel = p.resolve().relative_to(root).as_posix()
            else:
                # Anchor to the worktree and resolve, so "./x" tidies to "x",
                # ".hidden/x" keeps its leading dot, and "../outside" raises
                # ValueError below and is dropped (lstrip stripped characters,
                # not a prefix — it invented in-tree paths from outside ones).
                rel = (root / p).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            continue  # not inside this worktree
        if rel:
            out.append(rel)
    return sorted(set(out))


def write_turn_receipt(
    worktree_path: Path,
    task_id: str,
    turn: int,
    changed_files: Optional[Iterable[str]] = None,
) -> tuple[Path, int]:
    """Run the checker over the worktree and write its report beside the Coach verdict.

    Returns the receipt path and the number of findings the report lists. Raises on any
    failure; ``observe_task_conformance`` is the caller that swallows those.

    SCOPE — changed files, when the Player has named any.
    The checker supports being narrowed to the files a change touched: every rule still
    runs over the whole source tree, so counts like "nine of the eleven other query
    sites are in crud.py" stay true, but only the findings in this task's own files are
    listed. That is the right scope here, because a build turn should be shown what this
    task did, not what the repository has always done. When the Player has named no
    files yet — the first turn of a task that has written nothing — narrowing to an
    empty list would report on nothing at all, so the whole tree is reported on instead
    and the receipt says which was done.
    """
    from guardkit.conformance import run, to_json

    worktree = Path(worktree_path)
    scope = _relative_files(worktree, changed_files)
    report = run(worktree, diff_scope=scope or None)
    if not scope:
        report.notes.append(
            "This task had named no changed files when this ran, so the whole source "
            "tree was reported on rather than a change within it.")

    payload = to_json(report)
    path = _receipt_path(worktree, task_id, turn)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path, len(payload.get("findings") or [])


def observe_task_conformance(
    worktree_path: Path,
    task_id: str,
    turn: int,
    changed_files: Optional[Iterable[str]] = None,
) -> Optional[Path]:
    """Write this turn's receipt. Never raises, never changes anything, logs one line.

    Returns the receipt path, or None if it could not be written — in which case one
    warning has been logged and the build is untouched.
    """
    try:
        path, findings = write_turn_receipt(
            worktree_path, task_id, turn, changed_files
        )
        logger.info(
            "Architecture rules receipt for %s turn %s: %s (%d finding(s); "
            "nothing reads this).",
            task_id,
            turn,
            path,
            findings,
        )
        return path
    except Exception as exc:  # noqa: BLE001 — this can never fail a build
        logger.warning(
            "Architecture rules check raised %s for %s turn %s; no receipt written "
            "and the build is untouched.",
            exc.__class__.__name__,
            task_id,
            turn,
        )
        return None


# ---------------------------------------------------------------------------
# The switch, and the check the code generator is told about
# ---------------------------------------------------------------------------

#: The switch that turns this from something written down into something the code
#: generator is told. Unset, or set to anything not in the list below, means no: no
#: rule is synthesised and a build behaves exactly as it did before this existed.
#: Named and shaped after ``zero_test_gate.BLOCKING_ENV_VAR`` and
#: ``boot_smoke_gate.BLOCKING_ENV_VAR``, which is deliberate -- one shape for every
#: instrument here that starts out watching and is later allowed to act.
BLOCKING_ENV_VAR = "GUARDKIT_ARCH_CONFORMANCE_BLOCKING"

_TRUTHY = {"1", "true", "yes", "on"}

#: The id the synthesised check carries in the task's rule block, and the name the
#: code generator sees at the head of the issue. Kept plain on purpose: it is read by
#: a reader, not parsed.
RULE_ID = "architecture-rules"

#: How long the command is given before it is treated as failed. The checker reads a
#: repository's Python files and nothing else -- no network, no container, no model --
#: so this is generous.
RULE_TIMEOUT_SECONDS = 120

#: How long git is given to answer. It is asked two read-only questions.
_GIT_TIMEOUT_SECONDS = 60


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator asked architecture findings to reach the code generator?

    Reads :data:`BLOCKING_ENV_VAR`. Absent or unrecognised means no. Same wording and
    same accepted values as the two gates named beside it above.
    """
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _TRUTHY


def _git(repo: Path, *args: str) -> str:
    """Ask git one read-only question inside ``repo`` and return what it said.

    Raises ``ValueError`` with a sentence a person can read whenever git is not there,
    does not answer, or answers with an error. Every caller here turns that into "the
    check could not run", never into a failed build.
    """
    if shutil.which("git") is None:
        raise ValueError("git is not on this machine.")
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True,
            timeout=_GIT_TIMEOUT_SECONDS)
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"git {' '.join(args)} failed in {repo}: "
            f"{(exc.stderr or '').strip() or 'no reason given'}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            f"git {' '.join(args)} did not answer within "
            f"{_GIT_TIMEOUT_SECONDS} seconds in {repo}") from exc
    except OSError as exc:
        raise ValueError(f"git could not be run in {repo}: {exc}") from exc
    return done.stdout


def starting_commit(worktree_path: Path) -> str:
    """The commit this worktree sits on right now.

    Read before the first turn, when the worktree still holds exactly what the task
    started from, so that everything different from it later is this task's own work.
    """
    sha = _git(Path(worktree_path), "rev-parse", "HEAD").strip()
    if not sha:
        raise ValueError(f"git named no commit for {worktree_path}.")
    return sha


def files_changed_since(repo: Path, start_commit: str) -> list[str]:
    """The repository-relative files that differ from ``start_commit`` right now.

    Two questions, because one is not enough. ``git diff`` names every tracked file
    that differs from that commit, committed or not -- but it says nothing about a
    file git has never been told about, and a brand-new file is exactly where new code
    goes. So the files git is not tracking are asked for separately and added. Missing
    them would let a whole new file pass unread, which is this estate's known failure
    class: a check that runs, looks in the wrong place, and reports success.
    """
    repo = Path(repo)
    changed = _git(repo, "diff", "--name-only", start_commit).splitlines()
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({line.strip() for line in (*changed, *untracked) if line.strip()})


def build_arch_conformance_rule(
    worktree_path: Path,
    task_id: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[dict[str, Any]]:
    """The check to hand the build loop for this task, or ``None`` for nothing to do.

    Shaped exactly like the rule dicts ``spec_conformance`` already runs -- the same
    move ``verifier_stamp.build_rule_from_frontmatter`` makes for the routing law:
    a repository-level rule nobody had to write into a task, wired into the machinery
    that already exists rather than a second copy of it.

    ``None``, and therefore nothing at all, in every one of these cases:

    * the switch is not set (the default, and a build is then byte-for-byte what it
      was before this existed);
    * the repository under build has written no ``docs/architecture-rules.yaml``, so
      there are no rules of its own to check it against;
    * the commit this task starts from cannot be read, so the check could not be held
      to this task's own files -- and a check that would judge a task on the whole
      tree is worse than no check, because the pilot repository's main branch carries
      known places on purpose.

    Never raises: it is called from a place that must not fail a build.
    """
    try:
        if not blocking_requested(env):
            return None

        worktree = Path(worktree_path)
        if not (worktree / RULES_RELATIVE_PATH).is_file():
            logger.debug(
                "Architecture rules: %s has no %s, so no check was added for %s.",
                worktree, RULES_RELATIVE_PATH, task_id or "<task>")
            return None

        try:
            sha = starting_commit(worktree)
        except ValueError as exc:
            logger.warning(
                "Architecture rules: %s is set, but the commit %s starts from could "
                "not be read (%s), so no check was added. The check only ever judges "
                "the files a task changed, and without that commit it cannot tell "
                "them from the rest of the repository.",
                BLOCKING_ENV_VAR, task_id or "<task>", exc)
            return None

        command = (
            f"{shlex.quote(sys.executable)} -m guardkit.orchestrator.arch_conformance "
            f"--repo . --since {shlex.quote(sha)}")
        logger.info(
            "Architecture rules: %s is set and %s has a rules file, so %s will be "
            "checked against it on the files it changes since %s.",
            BLOCKING_ENV_VAR, worktree, task_id or "<task>", sha[:12])
        return {
            "id": RULE_ID,
            "type": "assert_command",
            "command": command,
            "expected_exit": 0,
            "timeout": RULE_TIMEOUT_SECONDS,
        }
    except Exception as exc:  # noqa: BLE001 -- this can never fail a build
        logger.warning(
            "Architecture rules: working out the check for %s raised %s, so no check "
            "was added and the build is untouched.",
            task_id or "<task>", exc.__class__.__name__)
        return None


# ---------------------------------------------------------------------------
# The command the check runs
# ---------------------------------------------------------------------------

#: Printed when the check could not be made, for any reason at all. Exit 0 follows it.
_COULD_NOT_RUN = "Architecture rules were not checked: {why} Nothing was checked, which is not the same as clean."


def _finding_lines(report: Any) -> list[str]:
    """The checker's own words for every place it reports, and nothing else.

    Rule id, file and line, what is there, the rule's sentence, and the sentence the
    rule quotes from the architecture record with the document it came from -- each
    carried through exactly as the checker wrote it. Nothing here summarises, scores,
    ranks or scolds; whoever reads this draws the conclusion.
    """
    lines: list[str] = []
    for rule in report.rules:
        for site in rule.reported_findings(report.narrowed):
            lines.append("")
            lines.append(f"{rule.rule_id} -- {site.where}")
            lines.append(
                f"    what is there: {site.observed}"
                + (f", inside {site.enclosing}()" if site.enclosing else ""))
            for extra in site.also_at:
                lines.append(f"    also here:     {extra}")
            lines.append(f"    the rule:      {rule.says}")
            source = rule.source or {}
            where = source.get("document") or "(no document named)"
            if source.get("section"):
                where = f"{where}, section \"{source['section']}\""
            lines.append(
                f"    from the record: {where} -- \"{source.get('sentence') or ''}\"")
    return lines


def check_changed_files(repo: Path, start_commit: str) -> tuple[int, str]:
    """Run the checker over the files changed since ``start_commit``. Never raises.

    Returns the exit code and the text to print. 1 -- and only 1 -- means the checker
    ran and reported places inside those files. Everything else is 0: nothing to
    report, nothing changed yet, or the checker could not run at all.
    """
    repo = Path(repo)
    try:
        scope = files_changed_since(repo, start_commit)
    except ValueError as exc:
        return 0, _COULD_NOT_RUN.format(why=f"{exc}")

    if not scope:
        return 0, ("Architecture rules: this task has changed no files yet, so there "
                   "was nothing of its own to check.")

    try:
        from guardkit.conformance import run
        report = run(repo, diff_scope=scope)
    except Exception as exc:  # noqa: BLE001 -- a checker that cannot run is not a wall
        return 0, _COULD_NOT_RUN.format(
            why=f"the checker raised {exc.__class__.__name__}: {exc}.")

    if report.could_not_run or not report.ran:
        return 0, _COULD_NOT_RUN.format(why=f"{report.could_not_run or 'it did not run.'}")

    findings = report.reported_findings
    tail: list[str] = []
    if report.unsupported:
        tail.append("")
        tail.append("These rules could not be checked at all, so they are not clean "
                    "either -- they are unread:")
        for rule in report.unsupported:
            tail.append(f"    {rule.rule_id}: {rule.unsupported_reason}")

    if not findings:
        head = (f"Architecture rules: the {len(scope)} file(s) this task changed sit "
                f"where this repository's own {len(report.rules)} rule(s) put them.")
        return 0, "\n".join([head, *tail])

    # The reader of this only ever sees the LAST 2000 characters of it (the build
    # loop keeps a tail, not the whole thing), so everything that must be read is put
    # at the END. A framing line at the top would be the first thing cut.
    head = [
        f"Architecture rules: {len(findings)} place(s) in the {len(scope)} file(s) "
        f"this task changed sit somewhere this repository's own rules do not name."
    ]
    foot = [
        "",
        f"{len(findings)} place(s) above, from {len(report.rules)} rule(s), over the "
        f"{len(scope)} file(s) this task changed. Each is the checker's own words: "
        f"the rule, where it is, and the sentence that rule quotes from this "
        f"repository's architecture record. Fix the code, or say so if the rule is "
        f"the thing that is wrong. Places elsewhere in this repository that this task "
        f"did not touch are not listed and are not this task's to fix.",
    ]
    return 1, "\n".join([*head, *_finding_lines(report), *tail, *foot])


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="python -m guardkit.orchestrator.arch_conformance",
        description=(
            "Check the files a task changed against the repository's own architecture "
            "rules. Exit 1 means there is something to read; exit 0 means there is "
            "not, or that the check could not be made at all -- a check that cannot "
            "run must not stop a build."))


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    parser.add_argument("--repo", type=Path, default=Path("."),
                        help="the repository to read (default: the current directory)")
    parser.add_argument("--since", required=True, metavar="COMMIT",
                        help="the commit this task started from; everything different "
                             "from it is this task's own work")
    args = parser.parse_args(argv)
    code, text = check_changed_files(args.repo, args.since)
    print(text)
    return code


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
