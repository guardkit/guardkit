"""
Plan Audit Module - Compare actual implementation against original plan (Hubbard's Step 6).

Part of TASK-025: Implement Phase 5.5 Plan Audit.

This module implements John Hubbard's Step 6 (Audit) from his proven 6-step workflow.
It verifies that actual implementation matches the approved architectural plan by:
- Comparing files created vs planned
- Comparing dependencies added vs planned
- Comparing LOC (lines of code) vs estimates
- Comparing duration vs estimates

Research support:
- John Hubbard's 6-step workflow (Step 6: Audit)
- ThoughtWorks: "Agents frequently don't follow all instructions"
- Closes critical gap identified in SDD vs AI-Engineer analysis

Author: Claude (Anthropic)
Created: 2025-10-18
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Literal, Optional, Set
from pathlib import Path
from datetime import datetime
import json
import re
import subprocess
from guardkit.lib.project_git import run_git


@dataclass
class Discrepancy:
    """Represents a single discrepancy between planned and actual implementation."""
    category: str  # "files", "dependencies", "loc", "duration"
    severity: Literal["low", "medium", "high"]
    message: str
    planned: Any
    actual: Any
    variance: float  # Percentage variance (e.g., 55.0 for 55%)


@dataclass
class DeclaredFiles:
    """What a task document itself says it will create and change.

    Two answers, kept apart, because "creates nothing and changes two files"
    is a thing a task must be able to say.

    ``None`` means the task document has no such section at all: it made no
    claim, so the audit makes none either. An empty list is a real claim -
    the section is there and says it creates (or changes) nothing - and
    anything found beyond it is sprawl. Empty is not the same as absent.
    """
    to_create: Optional[List[str]] = None
    to_modify: Optional[List[str]] = None


@dataclass
class PlanAuditReport:
    """Complete audit report with all discrepancies and recommendations."""
    task_id: str
    plan_summary: Dict[str, Any]
    actual_summary: Dict[str, Any]
    discrepancies: List[Discrepancy]
    severity: Literal["low", "medium", "high"]
    recommendations: List[str]
    timestamp: str
    plan_path: str
    audit_duration_seconds: float


# The only files this audit never counts: caches, installed packages and
# compiled leftovers. Nobody writes them by hand and nobody reviews them.
#
# Test files and database migrations used to be on this list. They are not any
# more, and that is the point of the change: a task whose sprawl lands in a
# test file or in a migration is exactly the sprawl this audit exists to see,
# and hiding those trees is how a whole invented database migration went
# unnoticed on one build and broke the next one.
#
# Nothing here names a programming language. The audit asks git what changed,
# and git does not care what a file contains - a Kotlin file, a SQL migration
# and a Markdown page all count the same.
_NEVER_COUNTED_DIRECTORY_NAMES = frozenset({
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "coverage",
    ".git",
})
_NEVER_COUNTED_SUFFIXES = frozenset({".pyc", ".pyo"})

# The factory's own paperwork, which the machinery writes into the worktree
# while a task runs: the turn-by-turn checkpoints and the player's own note of
# what it meant to touch. Nobody chose to write these and no reviewer reads
# them, so reporting them as files the task added would bury the real answer
# in noise on every single build.
_NEVER_COUNTED_PATH_PREFIXES = (".guardkit/", "docs/state/")


# A PLANNED FILE'S OWN TEST OR STYLESHEET (18 October 2026, made blunt 19
# October after two rounds of review). An extra file is still counted and still
# named, but it is recorded in a low discrepancy of its own, and does not count
# towards the "three extra files is high" line, only when ALL of these hold:
#
#   1. it is in the same directory as a planned file;
#   2. it is a test or a style/image file, never production code, and its
#      derived name equals that planned file's derived name:
#        - a planned file: its name with the last extension removed
#          (``user.service.ts`` → ``user.service``, ``handler.go`` → ``handler``);
#        - a test: its name with the last extension removed, then exactly one
#          test marker removed - a trailing ``.test``/``.spec`` segment, or
#          else a ``_test``/``_spec`` suffix, or else a ``test_`` prefix
#          (``user.service.test.ts`` → ``user.service``, ``handler_test.go`` →
#          ``handler``, ``test_feature.py`` → ``feature``). A name with no
#          marker is not a test;
#        - a style or image file (css, scss, sass, less, svg, png, jpg, gif,
#          webp, ico): its name with the last extension removed, then one
#          trailing ``.module`` removed (``EmptyState.module.css`` →
#          ``EmptyState``, ``logo.svg`` → ``logo``);
#   3. it is not a protected file (below).
#
# So ``components/EmptyState.module.css`` beside a planned
# ``components/EmptyState.tsx`` is low, and ``handler_test.go`` beside a
# planned ``handler.go``; ``user.repository.test.ts`` beside a planned
# ``user.service.ts`` is not. A same-named test in another directory, a same-named
# production file (``NotesPage.utils.ts``), a helper, or anything under a test
# directory counts in full. Anything ambiguous counts in full.
#
# A protected file is never a companion, whatever it is called or wherever it
# sits: container and compose files, READMEs, migrations, lockfiles and
# dependency manifests (the files this audit reads dependencies from), CI and
# workflow files, environment files, and infrastructure and deploy files.
#
# Build FEAT-86FD (18 October 2026) stalled three turns on a plan audit that
# called a planned component's stylesheet, a page test and a helper "high".
# GuardKit had no path-based infrastructure list to reuse, so the list is here.
_PROTECTED_NAMES = frozenset({
    # lockfiles
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lockb", "bun.lock", "poetry.lock", "uv.lock", "pipfile.lock",
    "cargo.lock", "gemfile.lock", "composer.lock", "go.sum",
    "packages.lock.json", "pubspec.lock", "mix.lock",
    # dependency manifests (what _extract_dependencies reads, and their kin)
    "package.json", "pyproject.toml", "requirements.txt", "pipfile",
    "setup.py", "setup.cfg", "go.mod", "cargo.toml", "gemfile",
    "composer.json", "pubspec.yaml", "directory.packages.props",
    # build, deploy and CI entry points
    "makefile", "procfile", "jenkinsfile", ".gitlab-ci.yml",
    "azure-pipelines.yml", "bitbucket-pipelines.yml", "skaffold.yaml",
    "chart.yaml", "values.yaml", "kustomization.yaml",
})
# Any dot-separated part of the name starting with one of these protects it,
# so ``Dockerfile.dev``, ``NotesPage.Dockerfile`` and ``README.md`` all count.
_PROTECTED_NAME_PART_PREFIXES = (
    "dockerfile", "containerfile", "readme",
)
_PROTECTED_SUFFIXES = (
    ".lock", ".csproj", ".fsproj", ".vbproj", ".sln", ".tf", ".tfvars",
    ".dockerignore", ".sql",
)
_PROTECTED_DIRECTORY_NAMES = frozenset({
    "migrations", "migration", "migrate", "alembic", ".github", ".circleci",
    ".buildkite", ".gitlab", ".woodpecker", ".devcontainer", "deploy",
    "deployment", "deployments", "infra", "infrastructure", "terraform",
    "helm", "k8s", "kubernetes", "ansible",
})


def _without_last_extension(path: str) -> str:
    """The file's name, lower-cased, with its last extension removed."""
    name = path.rsplit("/", 1)[-1].lower()
    head, dot, _ = name.rpartition(".")
    return head if dot and head else name


def _planned_name(path: str) -> str:
    """A planned file's name for matching: ``user.service.ts`` → ``user.service``."""
    return _without_last_extension(path)


_STYLE_AND_IMAGE_SUFFIXES = (
    ".css", ".scss", ".sass", ".less",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
)


def _companion_name(path: str) -> Optional[str]:
    """An extra file's name for matching, or ``None`` when it is neither a
    test nor a style or image file (production code is never a companion).

    A style or image file drops its last extension and then one trailing
    ``.module``. A test drops its last extension and then exactly one test
    marker: a trailing ``.test``/``.spec`` segment, or else a ``_test``/
    ``_spec`` suffix, or else a ``test_`` prefix.
    """
    name = path.rsplit("/", 1)[-1].lower()
    base = _without_last_extension(path)
    if base == name:
        return None  # no extension at all: ambiguous, counts in full
    if name.endswith(_STYLE_AND_IMAGE_SUFFIXES):
        return base[: -len(".module")] if base.endswith(".module") else base
    for marker in (".test", ".spec", "_test", "_spec"):
        if base.endswith(marker) and len(base) > len(marker):
            return base[: -len(marker)]
    if base.startswith("test_") and len(base) > len("test_"):
        return base[len("test_"):]
    return None


def _is_protected(path: str) -> bool:
    """Whether ``path`` is a file that is never a companion of planned work."""
    parts = path.split("/")
    name = parts[-1].lower()
    if name in _PROTECTED_NAMES or name.endswith(_PROTECTED_SUFFIXES):
        return True
    if name.startswith(".env") or name.startswith("."):
        # .env*, and every other dotfile (.gitlab-ci.yml, .npmrc, ...)
        return True
    name_parts = name.split(".")
    if any(
        p.startswith(_PROTECTED_NAME_PART_PREFIXES) or p == "env"
        for p in name_parts
    ):
        return True
    if "migration" in name:
        return True
    # compose*.y*ml and docker-compose*.y*ml, under any prefix
    if name.endswith((".yml", ".yaml")) and any(
        p.startswith(("compose", "docker-compose")) for p in name_parts
    ):
        return True
    return any(part.lower() in _PROTECTED_DIRECTORY_NAMES for part in parts[:-1])


def _folder(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _beside_the_plan(extra: Set[str], planned: Set[str]) -> Set[str]:
    """The extra files that are a planned file's own test or stylesheet.

    ``planned`` is every file the plan names (to create or to change). See the
    conditions at the top of this file. Nothing is removed from the audit by
    this: the caller still names every one.
    """
    planned_by_folder_and_name = {(_folder(p), _planned_name(p)) for p in planned}
    beside: Set[str] = set()
    for path in extra:
        name = _companion_name(path)
        if (
            name is not None
            and (_folder(path), name) in planned_by_folder_and_name
            and not _is_protected(path)
        ):
            beside.add(path)
    return beside


# A REPAIR ROUND (20 October 2026). A gate that runs after a wave can re-open an
# approved task with the gate's output as feedback. To make that gate pass the
# Player may have to make files the task document never named - the failing
# end-to-end test's helpers, seed scripts beside the check - and the audit,
# comparing the whole task with the task document, refused every such turn as
# high. The task then stalled although the Player was doing what the round
# asked. No rule about how many files, or which folder, can tell the files a
# repair needs from unrelated work; the reviewer, who has the failing check in
# front of it, can. So in a repair round, and only there:
#
#   * a non-protected extra file the ROUND made (one that was not in the
#     repository when the round started) does not count towards the "three
#     extra files is high" line. It is named, in a low discrepancy of its own,
#     for the reviewer, whose prompt for the turn says it is a repair round and
#     asks it to refuse the turn if any such file is not needed to make the
#     failing check pass (AgentInvoker._build_coach_prompt);
#   * a protected file (see _is_protected above) the round made, changed or
#     deleted that the plan does not name is high, whatever the reviewer says,
#     whatever file sections the task document has, and whatever an earlier
#     round did: it is read from git since the round started
#     (_repair_round_protected), like the reviewer's list;
#   * a non-protected extra file this task's earlier repair round showed the
#     reviewer on the turn it approved is not counted again (named in a low
#     discrepancy of its own); the files are handed over with the round, in
#     memory, and are only ever this task's own;
#   * any other extra file an earlier, approved round made counts exactly as
#     it did when that round was approved.
#
# What the reviewer is shown does not come from these discrepancies: it is
# every file git says changed since the round started that the task document
# does not name (PlanAuditor._repair_round_facts), whether or not the task
# document has a "files to modify" section.
#
# The round is handed to the auditor in memory by the orchestrator that
# re-opened the task (guardkit/orchestrator/repair_round.py); nothing on disk
# makes a turn a repair round. Ordinary turns are not touched by any of this.

_FOR_THE_REVIEWER_MESSAGE = (
    "made by this repair round, for the reviewer to judge against the failing check"
)
_PROTECTED_IN_REPAIR_MESSAGE = "protected, made or changed by this repair round"
_APPROVED_BY_A_REPAIR_MESSAGE = "approved by an earlier repair round of this task"


def _repair_round_split(
    extra: Set[str],
    existed_at_round_start: Set[str],
    approved_by_repairs: Set[str] = frozenset(),
) -> "tuple[Set[str], Set[str], Set[str]]":
    """Split a repair round's extra files: ``(counted, approved, for_reviewer)``.

    ``counted`` were in the repository when the round started, were not
    approved by an earlier repair round, and count as on an ordinary turn;
    ``approved`` were approved by an earlier repair round; ``for_reviewer`` is
    every non-protected file this round made. A protected file is in none of
    the last two: it is refused through :func:`_repair_round_protected`. See
    the rule above.
    """
    earlier = {path for path in extra if path in existed_at_round_start}
    approved = {
        path for path in earlier
        if path in approved_by_repairs and not _is_protected(path)
    }
    made = extra - earlier
    return earlier - approved, approved, {p for p in made if not _is_protected(p)}


def _repair_round_protected(
    changed_this_round: List[str],
    planned: Set[str],
) -> Set[str]:
    """The protected files a repair round made, changed or deleted that the
    plan does not name. Nothing an earlier round did exempts one.

    Read from git since the round started (``changed_this_round``), so it holds
    whichever file sections the task document has: a task that declares only
    files to modify cannot make a migration in a repair round either.
    """
    return {
        path
        for path in changed_this_round
        if _is_protected(path) and path not in planned
    }


class PlanAuditor:
    """Main auditor class that compares planned vs actual implementation."""

    def __init__(
        self,
        workspace_root: Path = Path("."),
        path_exclusion: Optional[Callable[[str], bool]] = None,
        repair_round: Optional[Any] = None,
    ):
        """
        Initialize plan auditor.

        Args:
            workspace_root: Root directory of the workspace (default: current directory)
            path_exclusion: Optional caller-owned predicate for paths produced by
                machinery around the implementation. The default preserves the
                standalone auditor's existing behaviour. If the predicate
                raises, the path remains in the audit so a broken exclusion can
                never hide implementation scope.
            repair_round: Set only when a gate re-opened this approved task:
                a ``guardkit.orchestrator.repair_round.RepairRound`` handed
                over in memory (see ``_repair_round_split``). ``None`` -
                every ordinary turn - audits exactly as before.
        """
        self.workspace_root = workspace_root
        self.path_exclusion = path_exclusion
        self.repair_round = repair_round

    def audit_implementation(
        self,
        task_id: str,
        declared: Optional[DeclaredFiles] = None,
    ) -> PlanAuditReport:
        """
        Main entry point: audit what was built against what was planned.

        Two ways to say what was planned:

        * ``declared`` given - the task document's own declaration of the
          files it will create and change is the plan, on every path. The
          player's own note of what it meant to touch is still read and
          reported alongside, but it no longer decides anything: a build
          graded against its own note is not graded.
        * ``declared`` omitted - the player's note is the plan, which is how
          this worked before task documents declared their files.

        When the task document is the plan, only files are judged. A task
        document declares files; it says nothing about dependencies, line
        counts or hours, so this comparison says nothing about them either.

        Args:
            task_id: Task identifier (e.g., "TASK-025")
            declared: The task document's declaration, or None.

        Returns:
            Complete audit report with discrepancies and severity

        Raises:
            PlanAuditError: If there is nothing to compare against - no
                declaration and no plan on disk.

        Example:
            >>> auditor = PlanAuditor()
            >>> report = auditor.audit_implementation("TASK-025")
            >>> print(report.severity)
            'low'
        """
        start_time = datetime.now()

        # The player's own note of what it intended to touch. Optional now:
        # it is the plan only when the task document declared nothing.
        player_note = self._load_plan(task_id)

        if declared is None:
            if not player_note:
                raise PlanAuditError(f"No implementation plan found for {task_id}")
            plan = player_note
        else:
            plan = {"plan": self._planned_from_declaration(declared)}

        # Analyze actual implementation
        actual = self._analyze_implementation(
            task_id, plan, scan_dependencies=declared is None
        )

        # Compare and detect discrepancies
        discrepancies = self._compare(plan, actual, files_only=declared is not None)

        # Calculate overall severity
        severity = self._calculate_severity(discrepancies)

        # Generate actionable recommendations
        recommendations = self._generate_recommendations(discrepancies, severity)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        plan_summary = self._extract_plan_summary(plan)
        if declared is None:
            plan_summary["planned_files_source"] = "the player's own note"
        else:
            plan_summary["planned_files_source"] = "the task document"
            # Reported, never graded: what the player said it would touch,
            # kept beside the verdict so a person can see both.
            plan_summary["player_note_files"] = self._player_note_files(player_note)

        return PlanAuditReport(
            task_id=task_id,
            plan_summary=plan_summary,
            actual_summary=actual,
            discrepancies=discrepancies,
            severity=severity,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat(),
            plan_path=f"docs/state/{task_id}/implementation_plan.md",
            audit_duration_seconds=duration
        )

    @staticmethod
    def _planned_from_declaration(declared: DeclaredFiles) -> Dict[str, Any]:
        """Turn the task document's declaration into the plan being compared.

        The two ``declares_...`` flags carry the difference between a section
        that is there and says "nothing" and a section that is not there at
        all. Without them an absent section would read as a claim that the
        task touches no files, and every file found would be reported as
        sprawl.
        """
        return {
            "files_to_create": list(declared.to_create or []),
            "files_to_modify": list(declared.to_modify or []),
            "declares_files_to_create": declared.to_create is not None,
            "declares_files_to_modify": declared.to_modify is not None,
            "external_dependencies": [],
            "estimated_loc": 0,
            "estimated_duration": "N/A",
        }

    @staticmethod
    def _player_note_files(player_note: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """The files the player's own note named, for reporting only."""
        if not player_note:
            return {"present": False, "files_to_create": [], "files_to_modify": []}
        note = player_note.get("plan", {}) or {}
        return {
            "present": True,
            "files_to_create": list(note.get("files_to_create", []) or []),
            "files_to_modify": list(note.get("files_to_modify", []) or []),
        }

    def _load_plan(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load saved implementation plan from disk.

        Looks for the plan under ``{workspace_root}/docs/state/{task_id}/``,
        preferring markdown over legacy JSON. Returns None when no plan is
        on disk — callers treat that as "skip audit".
        """
        ws_md = self.workspace_root / "docs" / "state" / task_id / "implementation_plan.md"
        ws_json = self.workspace_root / "docs" / "state" / task_id / "implementation_plan.json"

        if not (ws_md.exists() or ws_json.exists()):
            return None

        try:
            if ws_md.exists():
                from .plan_markdown_parser import (
                    PlanMarkdownParser,
                    PlanMarkdownParserError,
                )
                try:
                    parser = PlanMarkdownParser()
                    return parser.parse_file(ws_md)
                except PlanMarkdownParserError:
                    # Fall through to JSON or minimal shape.
                    pass
            if ws_json.exists():
                return json.loads(ws_json.read_text())
            return {"plan": {}}
        except Exception:
            return {"plan": {}}

    def _analyze_implementation(
        self,
        task_id: str,
        plan: Dict[str, Any],
        scan_dependencies: bool = True,
    ) -> Dict[str, Any]:
        """
        Work out what this task actually did: files made, files edited, lines,
        dependencies, hours.

        Args:
            task_id: Task identifier
            plan: The plan being compared against
            scan_dependencies: Whether to read the project's dependency files.
                Off when the task document is the plan, because a task
                document declares files and says nothing about dependencies.

        Returns:
            Dictionary with actual implementation metrics. ``files_read`` says
            whether git could answer at all: when it is False nobody counted,
            and a count nobody took is never published as a count of nothing.
        """
        changed = self._files_this_task_changed(task_id)
        return {
            "files_created": self._scan_created_files(plan, task_id, changed),
            "files_modified": self._scan_modified_files(plan, task_id, changed),
            "files_read": changed is not None,
            "total_loc": self._count_lines_of_code(plan),
            "dependencies": self._extract_dependencies() if scan_dependencies else [],
            "duration_hours": self._calculate_duration(task_id),
            "repair_round": (
                self._repair_round_facts(task_id) if changed is not None else None
            ),
        }

    def _task_start_commit(self, task_id: Optional[str]) -> str:
        """Where this task's work began, named in a way git understands.

        The build loop commits a checkpoint at the end of every turn, so from
        the second turn onward "what differs from the latest commit" answers
        almost nothing - which is how a task could rewrite half an application
        and the audit see none of it. The task's own checkpoint file records
        the first checkpoint's commit, and the commit before that one is where
        this task started.

        When there is no checkpoint file, nothing has been committed for this
        task yet, so the latest commit is the right place to measure from.
        """
        first = self._first_checkpoint_commit(task_id)
        return f"{first}^" if first else "HEAD"

    def _first_checkpoint_commit(self, task_id: Optional[str]) -> Optional[str]:
        """The commit of this task's first checkpoint, or ``None``."""
        if task_id:
            checkpoints = (
                self.workspace_root
                / ".guardkit"
                / "autobuild"
                / str(task_id)
                / "checkpoints.json"
            )
            try:
                data = json.loads(checkpoints.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = None
            if isinstance(data, dict):
                entries = data.get("checkpoints")
                if isinstance(entries, list) and entries and isinstance(entries[0], dict):
                    commit = entries[0].get("commit_hash")
                    if isinstance(commit, str) and commit.strip():
                        return commit.strip()
        return None

    def _is_ancestor(self, older: str, newer: str) -> bool:
        """Whether ``older`` is ``newer`` or one of its ancestors. False when
        git cannot say."""
        try:
            done = run_git(
                ["merge-base", "--is-ancestor", older, newer],
                cwd=self.workspace_root,
                check=False,
                timeout=30,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False
        return done.returncode == 0

    def _repair_round_facts(self, task_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """What the audit needs to know about a repair round, or ``None``.

        ``None`` - the audit is an ordinary one - unless a repair round was
        given AND it belongs to this task's history: the task's first
        checkpoint is at or before the round's start, and the round's start is
        at or before the worktree's current commit (a round whose start was
        rolled back is audited as an ordinary turn). ``implicated_paths`` are
        the files the gate's output names, matched against the repository as
        it was when the round started.
        """
        round_ = self.repair_round
        if round_ is None or not isinstance(round_.start_commit, str):
            return None
        start = round_.start_commit.strip()
        if not start:
            return None
        first = self._first_checkpoint_commit(task_id)
        if not first:
            return None
        if not (self._is_ancestor(first, start) and self._is_ancestor(start, "HEAD")):
            return None
        existed = self._paths_at_commit(start)
        if existed is None:
            return None
        from guardkit.orchestrator.repair_round import implicated_paths

        try:
            from guardkit.orchestrator.arch_conformance import files_changed_since

            since_start = files_changed_since(self.workspace_root, start)
        except (ImportError, ValueError, OSError):
            return None
        changed_this_round = sorted(
            path for path in since_start if not self._is_player_excluded(path)
        )
        return {
            "round_number": getattr(round_, "round_number", None),
            "start_commit": start,
            "existed_at_round_start": existed,
            "approved_by_earlier_repairs": set(
                getattr(round_, "approved_by_earlier_repairs", ()) or ()
            ),
            # Every file git says changed since the round started (made,
            # edited or deleted), after the same exclusions as the audit.
            "changed_this_round": changed_this_round,
            "implicated_paths": implicated_paths(
                str(getattr(round_, "gate_output", "") or ""), existed
            ),
        }

    def _paths_at_commit(self, commit: str) -> Optional[Set[str]]:
        """Every file the repository held at ``commit``.

        ``None`` when git could not say - no repository, no such commit, no
        git. Used only to tell a file this task made from a file it edited.
        """
        try:
            done = run_git(
                ["ls-tree", "-r", "--name-only", commit],
                cwd=self.workspace_root,
                check=False,
                timeout=30,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None
        if done.returncode != 0:
            return None
        return {line.strip() for line in done.stdout.splitlines() if line.strip()}

    def _files_this_task_changed(
        self, task_id: Optional[str]
    ) -> Optional[Dict[str, List[str]]]:
        """What this task changed, split into files it made and files it edited.

        Asked of git and of nothing else, so it holds whatever the project is
        written in. The list covers everything that differs from the commit
        this task started from, committed or not, plus files git has never
        been told about - a brand new file is exactly where new code goes.

        ``None`` when git could not answer at all, which the caller must treat
        as "nobody counted" rather than as "nothing changed".
        """
        try:
            from guardkit.orchestrator.arch_conformance import files_changed_since
        except ImportError:
            return None

        start = self._task_start_commit(task_id)
        try:
            changed = files_changed_since(self.workspace_root, start)
        except (ValueError, OSError):
            return None

        existed_before = self._paths_at_commit(start)
        if existed_before is None:
            return None

        created: List[str] = []
        modified: List[str] = []
        for rel_path in changed:
            if self._is_player_excluded(rel_path):
                continue
            if rel_path in existed_before:
                modified.append(rel_path)
            else:
                created.append(rel_path)
        return {"created": sorted(created), "modified": sorted(modified)}

    def _is_player_excluded(self, rel_path: str) -> bool:
        """Whether a changed path is never counted as this task's work: the
        audit's own never-counted paths, then the caller's exclusion."""
        if self._is_excluded(Path(rel_path)):
            return True
        if self.path_exclusion is not None:
            try:
                return bool(self.path_exclusion(rel_path))
            except Exception:
                # Counting the path is the safe fallback. A caller's broken
                # filter must not make real scope disappear.
                return False
        return False

    def _scan_created_files(
        self,
        plan: Dict[str, Any],
        task_id: Optional[str] = None,
        changed: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """
        The files this task made, read from git.

        This used to walk the whole worktree for a fixed list of file
        endings - .py, .ts, .cs and a few more - which counted every source
        file in the repository whether this task had touched it or not, and
        knew nothing about any language that was not on the list. Git knows
        exactly which files this task made, and knows it for every language.

        A planned file that is on disk counts as made whatever git says: an
        earlier turn may already have committed it, and "did you write the
        file you said you would" is answered by the file being there.

        Args:
            plan: The plan being compared against
            task_id: Task identifier, used to find where this task started
            changed: The already-read change set, when the caller has one

        Returns:
            List of file paths this task made, repository-relative
        """
        if changed is None:
            changed = self._files_this_task_changed(task_id)

        made = list(changed["created"]) if changed else []
        planned_to_create = plan.get("plan", {}).get("files_to_create", []) or []
        for rel_path in planned_to_create:
            if rel_path not in made and (self.workspace_root / rel_path).exists():
                made.append(rel_path)
        return sorted(set(made))

    def _scan_modified_files(
        self,
        plan: Dict[str, Any],
        task_id: Optional[str] = None,
        changed: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """
        The files this task edited, read from git.

        This used to ask what differs from the latest commit, which answers
        nothing from the second turn onward because the build loop commits a
        checkpoint at the end of every turn. It now asks what differs from the
        commit this task started from, which is the blast radius the audit
        exists to report.

        Returns ``[]`` when git could not answer, and the caller reads
        ``files_read`` to tell that apart from "this task edited nothing".

        Args:
            plan: The plan being compared against (kept for signature parity)
            task_id: Task identifier, used to find where this task started
            changed: The already-read change set, when the caller has one

        Returns:
            List of file paths this task edited, repository-relative
        """
        if changed is None:
            changed = self._files_this_task_changed(task_id)
        return list(changed["modified"]) if changed else []

    def _count_lines_of_code(self, plan: Dict[str, Any]) -> int:
        """
        Count actual lines of code in created/modified files.

        Args:
            plan: Implementation plan

        Returns:
            Total non-empty, non-comment lines
        """
        total_loc = 0
        plan_data = plan.get("plan", {})
        planned_files = (
            plan_data.get("files_to_create", []) +
            plan_data.get("files_to_modify", [])
        )

        for file_path_str in planned_files:
            file_path = self.workspace_root / file_path_str
            if file_path.exists():
                total_loc += self._count_file_loc(file_path)

        return total_loc

    def _count_file_loc(self, file_path: Path) -> int:
        """
        Count non-empty, non-comment lines in a file.

        Simple LOC counter that excludes:
        - Blank lines
        - Single-line comments (#, //, /*)
        - Lines with only whitespace

        Args:
            file_path: Path to file

        Returns:
            Number of lines of code
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            loc = 0
            for line in lines:
                stripped = line.strip()
                # Skip blank lines and common comment patterns
                if stripped and not stripped.startswith(('#', '//', '/*', '*', '"""', "'''")):
                    loc += 1

            return loc
        except Exception:
            return 0

    def _extract_dependencies(self) -> List[str]:
        """
        Extract dependencies from package files.

        Supports:
        - Python: requirements.txt, pyproject.toml
        - JavaScript/TypeScript: package.json
        - .NET: *.csproj

        Returns:
            List of dependency names
        """
        deps: Set[str] = set()

        # Python: requirements.txt
        req_file = self.workspace_root / "requirements.txt"
        if req_file.exists():
            deps.update(self._parse_requirements_txt(req_file))

        # Python: pyproject.toml
        pyproject_file = self.workspace_root / "pyproject.toml"
        if pyproject_file.exists():
            deps.update(self._parse_pyproject_toml(pyproject_file))

        # JavaScript/TypeScript: package.json
        pkg_file = self.workspace_root / "package.json"
        if pkg_file.exists():
            deps.update(self._parse_package_json(pkg_file))

        # .NET: *.csproj
        for csproj in self.workspace_root.glob("**/*.csproj"):
            deps.update(self._parse_csproj(csproj))

        return sorted(list(deps))

    def _parse_requirements_txt(self, file_path: Path) -> Set[str]:
        """Parse Python requirements.txt."""
        deps = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, ~=, etc.)
                        pkg = re.split(r'[=<>~!]', line)[0].strip()
                        if pkg:
                            deps.add(pkg)
        except Exception:
            pass
        return deps

    def _parse_pyproject_toml(self, file_path: Path) -> Set[str]:
        """Parse Python pyproject.toml (simplified - no TOML parser)."""
        deps = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple regex to extract dependencies
                matches = re.findall(r'"([a-zA-Z0-9_-]+)\s*[=<>~]', content)
                deps.update(matches)
        except Exception:
            pass
        return deps

    def _parse_package_json(self, file_path: Path) -> Set[str]:
        """Parse JavaScript/TypeScript package.json."""
        deps = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            deps.update(data.get("dependencies", {}).keys())
            deps.update(data.get("devDependencies", {}).keys())
        except Exception:
            pass
        return deps

    def _parse_csproj(self, file_path: Path) -> Set[str]:
        """Parse .NET .csproj file (simplified - no XML parser)."""
        deps = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple regex to extract PackageReference
                matches = re.findall(r'<PackageReference Include="([^"]+)"', content)
                deps.update(matches)
        except Exception:
            pass
        return deps

    def _calculate_duration(self, task_id: str) -> float:
        """
        Calculate actual implementation duration from task metadata or git commits.

        Simplified implementation - checks task metadata for timestamps.

        Args:
            task_id: Task identifier

        Returns:
            Duration in hours (0.0 if not available)
        """
        # Placeholder - actual implementation would:
        # 1. Check task metadata for start/end timestamps
        # 2. Use git commit history to calculate duration
        # For MVP, return 0.0 (duration tracking not yet implemented)
        return 0.0

    def _compare(
        self,
        plan: Dict[str, Any],
        actual: Dict[str, Any],
        files_only: bool = False,
    ) -> List[Discrepancy]:
        """
        Compare planned vs actual, return list of discrepancies.

        Args:
            plan: Implementation plan
            actual: Actual implementation metrics
            files_only: Judge files and nothing else. Set when the task
                document is the plan: it declares files, and says nothing
                about dependencies, line counts or hours, so neither does
                this comparison.

        Returns:
            List of discrepancies found
        """
        discrepancies = []
        plan_data = plan.get("plan", {})

        # Compare files
        discrepancies.extend(self._compare_files(plan_data, actual))

        if files_only:
            return discrepancies

        # Compare dependencies
        discrepancies.extend(self._compare_dependencies(plan_data, actual))

        # Compare LOC
        discrepancies.extend(self._compare_loc(plan_data, actual))

        # Compare duration (if available)
        discrepancies.extend(self._compare_duration(plan_data, actual))

        return discrepancies

    def _compare_files(
        self,
        plan_data: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Compare files: detect extra/missing files."""
        discrepancies = []

        planned_files = set(plan_data.get("files_to_create", []))
        actual_files = set(actual.get("files_created", []))

        # Whether the list of files this task changed could be read from git
        # at all. When it could not, no claim is made about files that were
        # not planned: a count nobody took must never be published as a count
        # of nothing. Callers that hand in their own numbers say nothing, and
        # are taken at their word.
        files_read = actual.get("files_read", True)
        # Whether the plan says anything about files to create. A task
        # document with no such section made no claim, so nothing found is
        # called sprawl. A section that is there and says "nothing" is a
        # claim, and then everything found is sprawl.
        create_axis_claimed = plan_data.get("declares_files_to_create", True)

        extra_files = (
            actual_files - planned_files
            if (files_read and create_axis_claimed)
            else set()
        )
        missing_files = planned_files - actual_files

        # Extra files that are a planned file's own test or stylesheet are
        # named in a low discrepancy of their own and do not count towards
        # the line below (see _beside_the_plan at the top of this file).
        planned_anywhere = planned_files | set(plan_data.get("files_to_modify", []))
        beside = _beside_the_plan(extra_files, planned_anywhere)
        counted_extra = extra_files - beside

        # A repair round's own rule (see _repair_round_split at the top of
        # this file). Absent on every ordinary turn.
        repair_facts = actual.get("repair_round")
        approved_by_repair: Set[str] = set()
        protected_touched: Set[str] = set()
        for_reviewer: Set[str] = set()
        if repair_facts:
            approved_by_repairs = set(
                repair_facts.get("approved_by_earlier_repairs") or ()
            )
            # From git since the round started, whatever sections the task
            # document has (not from the extra files above, which are empty
            # when the task declares no files to create).
            protected_touched = _repair_round_protected(
                list(repair_facts.get("changed_this_round") or ()),
                planned_anywhere,
            )
            if counted_extra:
                counted_extra, approved_by_repair, for_reviewer = _repair_round_split(
                    counted_extra,
                    set(repair_facts.get("existed_at_round_start") or ()),
                    approved_by_repairs,
                )
                counted_extra -= protected_touched

        if counted_extra:
            severity = "medium" if len(counted_extra) <= 2 else "high"
            variance = (len(counted_extra) / max(len(planned_files), 1)) * 100

            discrepancies.append(Discrepancy(
                category="files",
                severity=severity,
                message=f"{len(counted_extra)} extra file(s) not in plan",
                planned=sorted(list(planned_files)),
                actual=sorted(list(counted_extra)),
                variance=variance
            ))

        if beside:
            discrepancies.append(Discrepancy(
                category="files",
                severity="low",
                message=(
                    f"{len(beside)} extra file(s) not in plan, each a planned "
                    f"file's own test or stylesheet"
                ),
                planned=sorted(list(planned_files)),
                actual=sorted(list(beside)),
                variance=(len(beside) / max(len(planned_files), 1)) * 100,
            ))

        if protected_touched:
            discrepancies.append(Discrepancy(
                category="files",
                severity="high",
                message=(
                    f"{len(protected_touched)} extra file(s) not in plan, "
                    f"{_PROTECTED_IN_REPAIR_MESSAGE}"
                ),
                planned=sorted(list(planned_files)),
                actual=sorted(list(protected_touched)),
                variance=(len(protected_touched) / max(len(planned_files), 1)) * 100,
            ))

        if approved_by_repair:
            discrepancies.append(Discrepancy(
                category="files",
                severity="low",
                message=(
                    f"{len(approved_by_repair)} extra file(s) not in plan, "
                    f"{_APPROVED_BY_A_REPAIR_MESSAGE}"
                ),
                planned=sorted(list(planned_files)),
                actual=sorted(list(approved_by_repair)),
                variance=(len(approved_by_repair) / max(len(planned_files), 1)) * 100,
            ))

        if for_reviewer:
            discrepancies.append(Discrepancy(
                category="files",
                severity="low",
                message=(
                    f"{len(for_reviewer)} extra file(s) not in plan, "
                    f"{_FOR_THE_REVIEWER_MESSAGE}"
                ),
                planned=sorted(list(planned_files)),
                actual=sorted(list(for_reviewer)),
                variance=(len(for_reviewer) / max(len(planned_files), 1)) * 100,
            ))

        if missing_files:
            variance = (len(missing_files) / max(len(planned_files), 1)) * 100

            discrepancies.append(Discrepancy(
                category="files",
                severity="high",
                message=f"{len(missing_files)} planned file(s) not created",
                planned=sorted(list(missing_files)),
                actual=sorted(list(actual_files)),
                variance=variance
            ))

        # Modification-axis comparison: only fire when the plan declared
        # modifications. AC-5 — when ``files_to_modify`` is empty, the plan
        # makes no claim about modifications, so unplanned-modification
        # noise is suppressed regardless of what the Player touched.
        planned_modify = set(plan_data.get("files_to_modify", []))
        actual_modify = set(actual.get("files_modified", []))

        # A task document that has a "files to modify" section has made a
        # claim even when the section says "nothing", so the comparison runs.
        # Without such a section the old rule holds: say nothing unless the
        # plan named something.
        modify_axis_claimed = plan_data.get(
            "declares_files_to_modify", bool(planned_modify)
        )

        if modify_axis_claimed and files_read:
            missing_modify = planned_modify - actual_modify
            extra_modify = actual_modify - planned_modify

            if missing_modify:
                variance = (len(missing_modify) / max(len(planned_modify), 1)) * 100
                discrepancies.append(Discrepancy(
                    category="files",
                    severity="medium",
                    message=f"{len(missing_modify)} planned file(s) not modified",
                    planned=sorted(list(missing_modify)),
                    actual=sorted(list(actual_modify)),
                    variance=variance,
                ))

            if extra_modify:
                variance = (len(extra_modify) / max(len(planned_modify), 1)) * 100
                discrepancies.append(Discrepancy(
                    category="files",
                    severity="low",
                    message=f"{len(extra_modify)} unplanned modification(s)",
                    planned=sorted(list(planned_modify)),
                    actual=sorted(list(extra_modify)),
                    variance=variance,
                ))

        return discrepancies

    def _compare_dependencies(
        self,
        plan_data: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Compare dependencies: detect extra/missing deps."""
        discrepancies = []

        planned_deps = set(plan_data.get("external_dependencies", []))
        actual_deps = set(actual.get("dependencies", []))

        extra_deps = actual_deps - planned_deps
        missing_deps = planned_deps - actual_deps

        if extra_deps:
            severity = "medium" if len(extra_deps) <= 1 else "high"
            variance = (len(extra_deps) / max(len(planned_deps), 1)) * 100

            discrepancies.append(Discrepancy(
                category="dependencies",
                severity=severity,
                message=f"{len(extra_deps)} extra dependenc(ies) not in plan",
                planned=sorted(list(planned_deps)),
                actual=sorted(list(extra_deps)),
                variance=variance
            ))

        if missing_deps:
            variance = (len(missing_deps) / max(len(planned_deps), 1)) * 100

            discrepancies.append(Discrepancy(
                category="dependencies",
                severity="medium",
                message=f"{len(missing_deps)} planned dependenc(ies) not added",
                planned=sorted(list(missing_deps)),
                actual=sorted(list(actual_deps)),
                variance=variance
            ))

        return discrepancies

    def _compare_loc(
        self,
        plan_data: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Compare lines of code: calculate variance %."""
        discrepancies = []

        planned_loc = plan_data.get("estimated_loc", 0)
        actual_loc = actual.get("total_loc", 0)

        if planned_loc > 0 and actual_loc > 0:
            variance = ((actual_loc - planned_loc) / planned_loc) * 100

            if abs(variance) > 10:  # More than 10% variance
                if abs(variance) < 30:
                    severity = "low"
                elif abs(variance) < 50:
                    severity = "medium"
                else:
                    severity = "high"

                discrepancies.append(Discrepancy(
                    category="loc",
                    severity=severity,
                    message=f"LOC variance: {variance:+.1f}% ({planned_loc} → {actual_loc} lines)",
                    planned=planned_loc,
                    actual=actual_loc,
                    variance=abs(variance)
                ))

        return discrepancies

    def _compare_duration(
        self,
        plan_data: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Compare duration: calculate variance %."""
        discrepancies = []

        planned_duration_str = plan_data.get("estimated_duration", "0 hours")
        planned_duration = self._parse_duration(planned_duration_str)
        actual_duration = actual.get("duration_hours", 0.0)

        if planned_duration > 0 and actual_duration > 0:
            variance = ((actual_duration - planned_duration) / planned_duration) * 100

            if abs(variance) > 10:  # More than 10% variance
                if abs(variance) < 30:
                    severity = "low"
                elif abs(variance) < 50:
                    severity = "medium"
                else:
                    severity = "high"

                discrepancies.append(Discrepancy(
                    category="duration",
                    severity=severity,
                    message=f"Duration variance: {variance:+.1f}% ({planned_duration:.1f}h → {actual_duration:.1f}h)",
                    planned=planned_duration,
                    actual=actual_duration,
                    variance=abs(variance)
                ))

        return discrepancies

    def _parse_duration(self, duration_str: str) -> float:
        """
        Parse duration string to hours (e.g., '4 hours' -> 4.0).

        Args:
            duration_str: Duration string like "4 hours", "2.5h", "3 days"

        Returns:
            Duration in hours
        """
        if not duration_str:
            return 0.0

        try:
            duration_str = duration_str.lower()

            # Try to extract number
            match = re.search(r'(\d+\.?\d*)', duration_str)
            if not match:
                return 0.0

            value = float(match.group(1))

            # Convert to hours based on unit
            if 'day' in duration_str:
                return value * 8  # Assume 8-hour workday
            elif 'min' in duration_str:
                return value / 60
            else:  # Default to hours
                return value

        except Exception:
            return 0.0

    def _calculate_severity(self, discrepancies: List[Discrepancy]) -> Literal["low", "medium", "high"]:
        """
        Calculate overall severity based on all discrepancies.

        Rules:
        - 2+ high severity → high
        - 1 high OR 3+ medium → high
        - 1+ medium → medium
        - Otherwise → low

        Args:
            discrepancies: List of discrepancies

        Returns:
            Overall severity level
        """
        if not discrepancies:
            return "low"

        # Count by severity
        high_count = sum(1 for d in discrepancies if d.severity == "high")
        medium_count = sum(1 for d in discrepancies if d.severity == "medium")

        if high_count >= 2:
            return "high"
        elif high_count == 1 or medium_count >= 3:
            return "high"
        elif medium_count >= 1:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        discrepancies: List[Discrepancy],
        severity: str
    ) -> List[str]:
        """
        Generate actionable recommendations based on discrepancies.

        Args:
            discrepancies: List of discrepancies
            severity: Overall severity level

        Returns:
            List of recommendation strings
        """
        recommendations = []

        for disc in discrepancies:
            if disc.category == "files" and "extra" in disc.message:
                files_preview = ', '.join(disc.actual[:3])
                if len(disc.actual) > 3:
                    files_preview += f", ... and {len(disc.actual) - 3} more"
                recommendations.append(
                    f"Review extra files for scope creep: {files_preview}"
                )

            elif disc.category == "files" and "missing" in disc.message:
                files_preview = ', '.join(disc.planned[:3])
                if len(disc.planned) > 3:
                    files_preview += f", ... and {len(disc.planned) - 3} more"
                recommendations.append(
                    f"Verify planned files were created: {files_preview}"
                )

            elif disc.category == "dependencies" and "extra" in disc.message:
                deps_preview = ', '.join(disc.actual[:3])
                if len(disc.actual) > 3:
                    deps_preview += f", ... and {len(disc.actual) - 3} more"
                recommendations.append(
                    f"Justify extra dependencies: {deps_preview}"
                )

            elif disc.category == "loc" and disc.variance > 50:
                recommendations.append(
                    f"Understand why LOC exceeded estimate by {disc.variance:.0f}%"
                )

            elif disc.category == "duration" and disc.variance > 50:
                recommendations.append(
                    f"Analyze duration overrun ({disc.variance:.0f}%) for future estimates"
                )

        if not recommendations:
            recommendations.append("No major concerns - implementation closely matches plan")

        return recommendations

    def _extract_plan_summary(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary from plan for report."""
        plan_data = plan.get("plan", {})
        return {
            "files": len(plan_data.get("files_to_create", [])),
            "files_to_modify": len(plan_data.get("files_to_modify", [])),
            "dependencies": len(plan_data.get("external_dependencies", [])),
            "estimated_loc": plan_data.get("estimated_loc", 0),
            "estimated_duration": plan_data.get("estimated_duration", "N/A")
        }

    def _is_excluded(self, file_path: Path) -> bool:
        """
        Whether this file is never counted by the audit.

        Only caches, installed packages, compiled leftovers and the factory's
        own paperwork - see the lists at the top of this file. Test files and
        database migrations used to be excluded here and are counted now,
        because sprawl that lands in a test or in a migration is still sprawl,
        and it was invisible.

        Directory names are matched against the path's own parts rather than
        with a glob, because a glob of the ``**/node_modules/**`` shape does
        not reliably match on every version of Python and quietly let whole
        trees back in.

        Args:
            file_path: Path to check, repository-relative

        Returns:
            True if should be excluded
        """
        if file_path.suffix in _NEVER_COUNTED_SUFFIXES:
            return True
        as_written = "/".join(file_path.parts)
        if as_written.startswith(_NEVER_COUNTED_PATH_PREFIXES):
            return True
        # Every part except the file's own name: a file called "coverage" is
        # a file, a directory called "coverage" is a cache.
        return any(
            part in _NEVER_COUNTED_DIRECTORY_NAMES for part in file_path.parts[:-1]
        )


class PlanAuditError(Exception):
    """Raised when plan audit operations fail."""
    pass


def format_audit_report(report: PlanAuditReport) -> str:
    """
    Format audit report as human-readable summary.

    Args:
        report: Audit report to format

    Returns:
        Formatted report string
    """
    severity_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴"
    }

    output = []
    output.append("=" * 70)
    output.append(f"PLAN AUDIT - {report.task_id}")
    output.append("=" * 70)
    output.append("")

    # Planned implementation
    output.append("PLANNED IMPLEMENTATION:")
    plan = report.plan_summary
    output.append(f"  Files: {plan['files']} files ({plan['estimated_loc']} lines)")
    output.append(f"  Dependencies: {plan['dependencies']}")
    output.append(f"  Duration: {plan['estimated_duration']}")
    output.append("")

    # Actual implementation
    output.append("ACTUAL IMPLEMENTATION:")
    actual = report.actual_summary
    output.append(f"  Files: {len(actual.get('files_created', []))} files ({actual.get('total_loc', 0)} lines)")
    output.append(f"  Dependencies: {len(actual.get('dependencies', []))}")
    output.append(f"  Duration: {actual.get('duration_hours', 0):.1f} hours")
    output.append("")

    # Discrepancies
    if report.discrepancies:
        output.append("DISCREPANCIES:")
        for disc in report.discrepancies:
            emoji = severity_emoji.get(disc.severity, "⚠️")
            output.append(f"  {emoji} {disc.message}")

            # Show details for file/dependency discrepancies
            if disc.category in ["files", "dependencies"] and isinstance(disc.actual, list):
                for item in disc.actual[:5]:  # Show first 5
                    output.append(f"      - {item}")
                if len(disc.actual) > 5:
                    output.append(f"      ... and {len(disc.actual) - 5} more")

        output.append("")
    else:
        output.append("DISCREPANCIES: None")
        output.append("")

    # Severity
    severity_emoji_overall = severity_emoji.get(report.severity, "⚠️")
    output.append(f"SEVERITY: {severity_emoji_overall} {report.severity.upper()}")
    output.append("")

    # Recommendations
    output.append("RECOMMENDATIONS:")
    for i, rec in enumerate(report.recommendations, 1):
        output.append(f"  {i}. {rec}")
    output.append("")

    # Options
    output.append("OPTIONS:")
    output.append("  [A]pprove - Accept implementation as-is, update plan retroactively")
    output.append("  [R]evise - Request removal of scope creep items")
    output.append("  [E]scalate - Mark as complex, create follow-up task")
    output.append("  [C]ancel - Block task completion")
    output.append("")

    return "\n".join(output)


# Module exports
__all__ = [
    "PlanAuditor",
    "PlanAuditReport",
    "DeclaredFiles",
    "Discrepancy",
    "PlanAuditError",
    "format_audit_report"
]
