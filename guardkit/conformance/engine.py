"""Running every rule in a repository's rules file over that repository.

The order of work: read the rules file, confirm the rules were written for this
repository, work out what its directories mean, parse every Python file under the
source root once, then hand each rule to the check that matches its shape.

Three things this deliberately does. It parses each file once and shares the result,
so a rule costs almost nothing to add. It records every site a rule matched, not only
the ones in the wrong place, because "seven of the nine query sites are in crud.py"
is what makes a finding readable. And it treats a rule it cannot run as unchecked
rather than clean.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

from guardkit.conformance import checks
from guardkit.conformance.facts import FileFacts
from guardkit.conformance.model import (
    CLEAN,
    ELSEWHERE,
    EXCEPTED,
    FINDING,
    UNSUPPORTED,
    AT_HOME,
    Report,
    RuleOutcome,
    Site,
    Tally,
    Unsupported,
)
from guardkit.conformance.rules import (
    DEFAULT_RULES_PATH,
    Layout,
    Rule,
    RulesFile,
    load,
    repo_identity,
    skip_dir,
)


def place(site: Site, rule: Rule) -> None:
    """Decide whether a site is somewhere the rule already allows.

    Exceptions come first: a site the rules file names, with a reason a person wrote,
    is excepted wherever it is. Then the home file. Everything else is a finding.
    """
    if site.placement == EXCEPTED and site.exception_reason:
        return
    for exc in rule.exceptions:
        if exc["path"] != site.path:
            continue
        lines = exc.get("lines")
        if lines is None or site.line in lines:
            site.placement = EXCEPTED
            site.exception_reason = exc.get("why") or "named as an exception in the rules file"
            return
    home = rule.signal("home_file")
    if home and not site.always_a_finding and Path(site.path).name == str(home):
        site.placement = AT_HOME
        return
    site.placement = ELSEWHERE


def _read_source_tree(repo: Path, layout: Layout, report: Report) -> list[tuple[str, FileFacts]]:
    """Every Python file under the source root, parsed once.

    A file that will not parse is recorded by name and skipped. It is never silently
    dropped: a file the checker could not read is a hole in every count below it.
    """
    root = repo / layout.source_root
    files: list[tuple[str, FileFacts]] = []
    if not root.is_dir():
        report.notes.append(
            f"There is no {layout.source_root}/ directory in {repo}. No Python file was "
            f"read, so no rule about source code could match anything.")
        return files
    for path in sorted(root.rglob("*.py")):
        rel_parts = path.relative_to(repo).parts
        if any(skip_dir(p) for p in rel_parts[:-1]):
            continue
        rel = path.relative_to(repo).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            report.files_unparsed.append(
                {"path": rel, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        files.append((rel, FileFacts(rel, tree)))
    return files


def _file_in_scope(rel: str, rule: Rule, layout: Layout) -> bool:
    if not layout.in_scope(rel, rule.scope):
        return False
    for skip in (rule.signal("skip_files") or []):
        if rel == str(skip).strip("/"):
            return False
    for skip in (rule.signal("skip_directories") or []):
        d = str(skip).strip("/")
        if rel == d or rel.startswith(d + "/"):
            return False
    if rule.kind == "module-import-boundary" and rel in layout.composition_root:
        return False
    return True


def files_touched_by(repo: Path, git_range: str) -> list[str]:
    """The repo-relative files a git range touched.

    This is the only process this program ever starts, it only reads, and it runs only
    when a range was asked for. Everything else here is Python's standard library over
    files on disk.
    """
    if shutil.which("git") is None:
        raise ValueError("git is not on this machine, so a range of commits cannot be "
                         "turned into a list of files.")
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only", git_range],
            capture_output=True, text=True, check=True, timeout=60)
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"git could not read the range {git_range!r} in {repo}: "
            f"{(exc.stderr or '').strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"git did not answer within 60 seconds for {git_range!r}") from exc
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def run(repo: Path, rules_path: Path | None = None,
        allow_foreign_rules: bool = False,
        diff_range: str | None = None,
        diff_scope: list[str] | None = None) -> Report:
    """Check ``repo`` against its own rules file and report what was seen.

    Two modes, as the design asks for. By default the whole source tree is reported
    on. Given ``diff_range`` (or a ready-made ``diff_scope``), every rule still runs
    over the whole tree — the counts that let a reader say "nine of the eleven other
    query sites are in crud.py" would be meaningless otherwise — but only the findings
    in the files that change touched are reported, and the rest are counted and named
    as being elsewhere in the repository.
    """
    repo = repo.resolve()
    rp = (rules_path or (repo / DEFAULT_RULES_PATH))
    report = Report(repo=str(repo), rules_path=str(rp))

    if not repo.is_dir():
        report.could_not_run = f"There is no directory at {repo}."
        report.notes.append(report.could_not_run)
        return report

    if not rp.is_file():
        report.could_not_run = (
            f"There is no rules file at {rp}. This repository has not stated any "
            f"architecture rules a machine can apply, so nothing was checked. That is "
            f"not the same as clean.")
        report.notes.append(report.could_not_run)
        return report

    try:
        rules_file: RulesFile = load(rp)
    except ValueError as exc:
        report.could_not_run = str(exc)
        report.notes.append(report.could_not_run)
        return report

    actual, how = repo_identity(repo)
    report.repo_identified_as = actual
    report.rules_written_for = rules_file.repo
    if rules_file.repo and rules_file.repo != actual and not allow_foreign_rules:
        report.could_not_run = (
            f"These rules were written for the repository {rules_file.repo!r}. The "
            f"repository at {repo} identifies as {actual!r} ({how}). Nothing was "
            f"checked. Architecture rules describe one repository's layout and mean "
            f"nothing in another. Pass --allow-foreign-rules to run them anyway.")
        report.notes.append(report.could_not_run)
        return report

    if diff_range is not None:
        try:
            diff_scope = files_touched_by(repo, diff_range)
        except ValueError as exc:
            report.could_not_run = str(exc)
            report.notes.append(report.could_not_run)
            return report
    if diff_scope is not None:
        report.diff_scope = sorted(diff_scope)
        report.notes.append(
            f"Narrowed to the {len(report.diff_scope)} file(s) this change touched. "
            f"Every rule still ran over the whole source tree; findings outside those "
            f"files are counted below but not listed.")

    layout = Layout(repo, rules_file.layout_cfg)
    report.notes.append(
        f"Repository identified as {actual!r} ({how}); the rules file was written for "
        f"{rules_file.repo!r}."
        + ("  THESE RULES WERE NOT WRITTEN FOR THIS REPOSITORY — run anyway because "
           "--allow-foreign-rules was passed." if rules_file.repo and rules_file.repo != actual
           else ""))
    report.notes.append(
        f"{len(rules_file.rules)} rule(s) read from {rp}, derived from "
        f"{rules_file.source_record}.")
    report.notes.append(
        f"Feature modules under {layout.source_root}/: "
        + (", ".join(layout.feature_names) or "(none)")
        + ". Infrastructure: " + (", ".join(sorted(layout.infrastructure)) or "(none)")
        + ". Composition root: " + (", ".join(sorted(layout.composition_root)) or "(none)"))

    files = _read_source_tree(repo, layout, report)
    report.files_scanned = len(files)
    report.ran = True

    for rule in rules_file.rules:
        outcome = RuleOutcome(
            rule_id=rule.id, says=rule.says, source=rule.source,
            kind=rule.kind or "(none stated)", scope=rule.scope,
            exceptions=rule.exceptions, inherited_signals=list(rule.inherited))
        report.rules.append(outcome)

        per_file = checks.PER_FILE_CHECKS.get(rule.kind)
        per_repo = checks.PER_REPO_CHECKS.get(rule.kind)
        if per_file is None and per_repo is None:
            outcome.status = UNSUPPORTED
            outcome.unsupported_reason = (
                f"This rule says it is checked by looking for "
                f"{rule.kind or 'a shape it does not name'}, and this checker has no "
                f"such check. Nothing was checked for it. The shapes it does have are: "
                f"{', '.join(checks.KNOWN_KINDS)}.")
            continue

        tally = Tally()
        try:
            if per_repo is not None:
                found = per_repo(rule, repo, layout, files, tally)
            else:
                found = []
                for rel, facts in files:
                    if _file_in_scope(rel, rule, layout):
                        tally.add("files in scope", 1)
                        found.extend(per_file(rule, rel, facts, layout, tally))
        except Unsupported as exc:
            outcome.status = UNSUPPORTED
            outcome.unsupported_reason = (
                f"This rule could not be run as written: {exc}. Nothing was checked "
                f"for it.")
            continue

        outcome.examined = dict(tally.counts)
        for site in found:
            place(site, rule)
            if report.diff_scope is not None:
                site.in_this_change = site.path in report.diff_scope
        outcome.sites = found
        outcome.status = FINDING if outcome.findings else CLEAN

    return report
