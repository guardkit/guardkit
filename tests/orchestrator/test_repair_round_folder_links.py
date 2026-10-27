"""A protected path reached through a folder symlink is fingerprinted.

The walk of the worktree used to prune folder symlinks, so with a committed
``infra -> build/runtime`` link a write through ``infra/config.txt`` (a
protected path: ``infra/`` is a protected folder) was never seen. The walk now
follows folder links, names what lies under them by the logical path, does
not follow a link back into a folder already on its way (so a loop ends), and
treats a link that leads nowhere, or a folder it cannot read, as unavailable.

Driven through the same real re-open and loop as
``test_repair_round_plan_audit_loop`` (only the model's answer is a stand-in,
and it approves). Every file name and content is invented.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.repair_round import protected_fingerprints

from tests.orchestrator.test_repair_round_plan_audit_loop import (  # noqa: F401
    APPROVE,
    TASK_ID,
    _git,
    _no_model_can_be_reached,
    _write,
    make_project,
    reopen_and_repair,
    run_round,
)

pytestmark = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads unreadable files"
)

HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}
LOGICAL = "infra/config.txt"


def _project_with_a_folder_link(tmp_path: Path, direct_mode: bool) -> Path:
    repo = make_project(
        tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
    )
    _write(repo, "build/runtime/config.txt", "replicas=1\n")  # ignored (build/)
    (repo / "infra").symlink_to("build/runtime")  # committed folder link
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "infra is a link to the runtime folder")
    first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
    assert first["decision"] == "approved", first["history"][-1].coach_result.report
    return repo


def _refused(repo: Path, outcome: Dict[str, Any], category: str) -> Dict[str, Any]:
    assert outcome["decision"] != "approved"
    report = outcome["history"][-1].coach_result.report
    issues = [i for i in report.get("issues", []) if i.get("category") == category]
    assert issues, report
    private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
    assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
    assert outcome["fo"]._repair_approvals.get(TASK_ID) is None
    return issues[0]


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
class TestAProtectedPathBehindAFolderLink:
    def test_a_write_through_the_link_is_refused_naming_the_logical_path(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / LOGICAL).write_text("replicas=9\n"),
        )
        # git sees nothing: the link is unchanged and its target is ignored.
        assert _git(repo, "status", "--porcelain", "--", "infra") == ""
        issue = _refused(repo, outcome, "repair_round_protected")
        assert "build/runtime/config.txt (as infra/config.txt)" in issue["details"]["protected"]

    def test_unchanged_approves(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        outcome = reopen_and_repair(repo, HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        # Keyed by the real path; protected because infra/ reaches it.
        assert "build/runtime/config.txt" in dict(outcome["repair_round"].protected_fingerprints)

    def test_a_loop_ends_and_unchanged_approves(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        # A link back up the tree, inside the linked folder: infra/back -> ../..
        # Every file is now reachable as infra/back/..., so every file is
        # protected; a repair that changes nothing still approves.
        (repo / "build" / "runtime" / "back").symlink_to("../..")
        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    def test_a_file_protected_only_through_an_alias_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """Codex's case: infra -> build/runtime, build/runtime/back -> ../..,
        so build/other.txt is protected as infra/back/build/other.txt."""
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        _write(repo, "build/other.txt", "unprotected on its own path\n")
        (repo / "build" / "runtime" / "back").symlink_to("../..")
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=lambda root: (root / "build" / "other.txt").write_text("changed\n"),
        )
        issue = _refused(repo, outcome, "repair_round_protected")
        assert "build/other.txt (as infra/back/build/other.txt)" in issue["details"]["protected"]

    def test_a_folder_link_made_to_lead_nowhere_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """What was under it is now missing from the walk: a protected change."""
        repo = _project_with_a_folder_link(tmp_path, direct_mode)

        def _dangle(root: Path) -> None:
            (root / "infra").unlink()
            (root / "infra").symlink_to("build/missing")

        outcome = reopen_and_repair(repo, HELPER, model_verdict=APPROVE, shell_step=_dangle)
        issue = _refused(repo, outcome, "repair_round_protected")
        # Gone from the protected files, named by the protected name it had;
        # and the link itself was retargeted.
        assert "build/runtime/config.txt (as infra/config.txt)" in issue["details"]["protected"]
        assert "infra" in issue["details"]["protected"]

    def test_an_unprotected_link_that_leads_nowhere_changes_nothing(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        (repo / "docs-link.md").symlink_to("docs/missing.md")  # as real projects have
        outcome = reopen_and_repair(repo, HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report


class TestTheWalk:
    def test_logical_paths_and_a_loop(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path)
        _write(repo, "build/runtime/config.txt", "replicas=1\n")
        (repo / "infra").symlink_to("build/runtime")
        (repo / "build" / "runtime" / "back").symlink_to("../..")
        from guardkit.orchestrator.repair_round import protected_files

        files = protected_files(repo)
        # One entry per real file, keyed by its real path and named by the
        # protected path that reaches it; the loop ends.
        assert LOGICAL in files["build/runtime/config.txt"][0]
        assert len(files) == len({fingerprint for _, fingerprint in files.values()})

    def test_a_real_file_is_protected_whichever_path_the_walk_meets_first(
        self, tmp_path: Path
    ) -> None:
        """Protection belongs to the real file: reached through a protected
        folder link that sorts before build/ or after it, it is protected."""
        from guardkit.orchestrator.repair_round import protected_files

        for name in ("ansible", "infra"):
            repo = make_project(tmp_path / name)
            _write(repo, "build/runtime/config.txt", "replicas=1\n")
            (repo / name).symlink_to("build/runtime")
            files = protected_files(repo)
            assert f"{name}/config.txt" in files["build/runtime/config.txt"][0]


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
class TestReachabilityEdges:
    def test_a_protected_folder_link_outside_the_worktree_is_never_walked(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """A link out of the worktree (to / or a home folder, here to a folder
        nobody may read) is fingerprinted by its text and target, never
        walked; retargeting it is still a change."""
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        outside = tmp_path / "outside-helm"
        (outside / "a").mkdir(parents=True)
        (outside / "b").mkdir()
        (repo / "helm").symlink_to(outside / "a")
        _git(repo, "add", "helm")
        _git(repo, "commit", "-q", "-m", "helm charts live outside the worktree")
        os.chmod(outside / "a", 0)
        try:
            unchanged = reopen_and_repair(repo, HELPER, model_verdict=APPROVE)
            assert unchanged["decision"] == "approved", unchanged["history"][-1].coach_result.report

            def _retarget(root: Path) -> None:
                (root / "helm").unlink()
                (root / "helm").symlink_to(outside / "b")

            retargeted = reopen_and_repair(
                repo, {}, model_verdict=APPROVE, fo=unchanged["fo"], shell_step=_retarget
            )
            assert retargeted["decision"] != "approved"
            report = retargeted["history"][-1].coach_result.report
            issues = [
                i for i in report.get("issues", [])
                if i.get("category") == "repair_round_protected"
            ]
            assert issues and "helm" in issues[0]["details"]["protected"]
        finally:
            os.chmod(outside / "a", 0o755)

    def test_a_protected_folder_that_links_into_node_modules_is_still_protected(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """Exclusion is judged on the LOGICAL path: infra -> node_modules/pkg/
        deploy keeps infra/config.txt protected, so a write through it is
        refused."""
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        _write(repo, "node_modules/pkg/deploy/config.txt", "replicas=1\n")
        (repo / "infra").symlink_to("node_modules/pkg/deploy")
        assert run_round(
            repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"}
        )["decision"] == "approved"
        outcome = reopen_and_repair(
            repo, HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / "infra" / "config.txt").write_text("replicas=9\n"),
        )
        issue = _refused(repo, outcome, "repair_round_protected")
        assert any("infra/config.txt" in p for p in issue["details"]["protected"])

    def test_node_modules_under_its_own_name_is_never_walked(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """A folder nobody may read inside node_modules would refuse the turn
        if the walk went in; it does not."""
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        (repo / "node_modules" / "locked").mkdir(parents=True)
        os.chmod(repo / "node_modules" / "locked", 0)
        try:
            outcome = reopen_and_repair(
                repo, HELPER, model_verdict=APPROVE,
                shell_step=lambda root: _write(root, "node_modules/pkg/package.json", "{}\n"),
            )
        finally:
            os.chmod(repo / "node_modules" / "locked", 0o755)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report


class TestCoachOneEdges:
    """Coach review 1 (20 October 2026): links out of the worktree, nested
    link chains, loops to an intermediate folder, logical exclusion, and a
    protected pipe."""

    @pytest.mark.timeout(60)
    def test_a_link_out_of_the_worktree_is_never_walked_or_opened(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_files

        repo = make_project(tmp_path / "p")
        outside = tmp_path / "outside"
        (outside / "locked").mkdir(parents=True)
        _write(outside, "Dockerfile", "FROM scratch\n")
        os.mkfifo(outside / "env.fifo")  # opening it would block forever
        (repo / "vendor").symlink_to(outside)        # unprotected name: not walked
        (repo / "root-link").symlink_to("/")         # not walked
        (repo / "infra").symlink_to(outside)         # protected folder name
        (repo / ".env").symlink_to(outside / "env.fifo")  # protected file name
        _write(outside, "secret.env", "TOKEN=1\n")
        (repo / ".env.local").symlink_to(outside / "secret.env")  # opened, it would refuse
        os.chmod(outside / "locked", 0)
        os.chmod(outside / "secret.env", 0)
        try:
            files = protected_files(repo)
        finally:
            os.chmod(outside / "locked", 0o755)
            os.chmod(outside / "secret.env", 0o600)
        assert "link:.env.local" in files
        # The protected links are fingerprinted as links; nothing beyond them.
        assert "link:infra" in files and "link:.env" in files
        assert not any(
            key.startswith(("vendor", "root-link", "infra/", "link:vendor", "link:root-link"))
            for key in files
        )
        assert not any(names and names[0].startswith("infra/") for names, _ in files.values())

    @pytest.mark.parametrize("names", [("a", "b"), ("infra", "deploy")])
    @pytest.mark.timeout(60)
    def test_twenty_two_nested_levels_of_double_links_finish_fast(
        self, tmp_path: Path, names: tuple
    ) -> None:
        import time

        from guardkit.orchestrator.repair_round import protected_files

        repo = make_project(tmp_path)
        levels = 22
        for n in range(levels + 1):
            (repo / "chain" / f"d{n}").mkdir(parents=True)
        _write(repo, f"chain/d{levels}/Dockerfile", "FROM scratch\n")
        for n in range(levels):
            for name in names:
                (repo / "chain" / f"d{n}" / name).symlink_to(f"../d{n + 1}")
        started = time.monotonic()
        files = protected_files(repo)
        assert time.monotonic() - started < 10
        assert f"chain/d{levels}/Dockerfile" in files

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    @pytest.mark.timeout(120)
    def test_loops_to_an_intermediate_folder_and_to_itself_approve(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = _project_with_a_folder_link(tmp_path, direct_mode)
        (repo / "build" / "runtime" / "up").symlink_to("..")      # to an intermediate folder
        (repo / "build" / "runtime" / "me").symlink_to(".")       # to its own folder (infra/me)
        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.timeout(60)
    def test_the_walk_never_opens_a_protected_pipe(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_files

        repo = make_project(tmp_path)
        os.mkfifo(repo / ".env")
        (repo / "deploy" / "run.sock.link").symlink_to("../.env")  # a link to the pipe
        files = protected_files(repo)
        assert files[".env"][1] != ""
        assert len({fingerprint for _, fingerprint in files.values()}) == len(files)

    # Direct mode also runs the factory's own checkers over the worktree;
    # those open only regular files from guardkitfactory 519508e onwards.
    @pytest.mark.timeout(120)
    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_protected_pipe_is_fingerprinted_by_its_type(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        if direct_mode and not _factory_checkers_skip_special_files():
            pytest.skip(
                "direct mode needs guardkitfactory whose checkers open only "
                "regular files (guardkitfactory.regular_file); the installed "
                "one would block on the pipe"
            )
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        os.mkfifo(repo / ".env")  # ignored, protected; open() on it would block
        assert run_round(
            repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"}
        )["decision"] == "approved"
        unchanged = reopen_and_repair(repo, HELPER, model_verdict=APPROVE)
        assert unchanged["decision"] == "approved", unchanged["history"][-1].coach_result.report
        assert dict(unchanged["repair_round"].protected_fingerprints)[".env"] != ""

        def _now_a_file(root: Path) -> None:
            (root / ".env").unlink()
            (root / ".env").write_text("A=1\n")

        changed = reopen_and_repair(
            repo, {}, model_verdict=APPROVE, fo=unchanged["fo"], shell_step=_now_a_file
        )
        assert changed["decision"] != "approved"
        report = changed["history"][-1].coach_result.report
        assert any(
            i.get("category") == "repair_round_protected" and ".env" in i["details"]["protected"]
            for i in report.get("issues", [])
        )


def _factory_checkers_skip_special_files() -> bool:
    """True when the installed guardkitfactory reads only regular files."""
    import importlib.util

    try:
        return importlib.util.find_spec("guardkitfactory.regular_file") is not None
    except ImportError:
        return False


def _approved_project(tmp_path: Path, direct_mode: bool, build) -> Path:
    """A project with no declarations, shaped by ``build(repo)``, committed and
    approved in round 1."""
    repo = make_project(
        tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
    )
    build(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "the shape under test")
    first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
    assert first["decision"] == "approved", first["history"][-1].coach_result.report
    return repo


def _declare(repo: Path, *paths: str) -> None:
    """Rewrite the task document so it declares ``paths`` as files to modify."""
    task = next((repo / "tasks" / "in_progress").glob("*.md"))
    text = task.read_text()
    head, _, rest = text.partition("## Acceptance Criteria")
    task.write_text(
        head + "## Files to Modify\n\n" + "".join(f"- `{p}`\n" for p in paths)
        + "\n## Acceptance Criteria" + rest
    )


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
class TestNamesAndLinksAreKept:
    """Codex round 2: a record keeps every protected name that reached it, and
    every link at a protected position is fingerprinted itself."""

    def test_a_folder_link_retargeted_between_protected_targets_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "build/a/README.md", "first\n")   # protected by name
            _write(repo, "build/b/README.md", "second\n")  # protected by name
            (repo / "infra").symlink_to("build/a")

        repo = _approved_project(tmp_path, direct_mode, build)

        def _retarget(root: Path) -> None:
            (root / "infra").unlink()
            (root / "infra").symlink_to("build/b")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=_retarget)
        issue = _refused(repo, outcome, "repair_round_protected")
        assert "infra" in issue["details"]["protected"]

    @pytest.mark.parametrize("change", ["retarget", "delete"])
    def test_a_protected_file_link_retargeted_or_deleted_is_refused(
        self, tmp_path: Path, direct_mode: bool, change: str
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "build/env/.env.a", "A=1\n")  # ignored, protected (dotfile)
            _write(repo, "build/env/.env.b", "A=1\n")
            (repo / ".env").symlink_to("build/env/.env.a")  # ignored, protected

        repo = _approved_project(tmp_path, direct_mode, build)

        def _change(root: Path) -> None:
            (root / ".env").unlink()
            if change == "retarget":
                (root / ".env").symlink_to("build/env/.env.b")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=_change)
        issue = _refused(repo, outcome, "repair_round_protected")
        assert ".env" in issue["details"]["protected"]

    def test_a_deletion_through_a_link_into_node_modules_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "node_modules/pkg/deploy/config.txt", "replicas=1\n")
            (repo / "infra").symlink_to("node_modules/pkg/deploy")

        repo = _approved_project(tmp_path, direct_mode, build)
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=lambda root: (root / "infra" / "config.txt").unlink(),
        )
        issue = _refused(repo, outcome, "repair_round_protected")
        assert (
            "node_modules/pkg/deploy/config.txt (as infra/config.txt)"
            in issue["details"]["protected"]
        )

    @pytest.mark.parametrize("actual_declarations", [False, True])
    def test_target_edits_require_actual_paths_not_folder_or_file_aliases(
        self, tmp_path: Path, direct_mode: bool, actual_declarations: bool
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "build/runtime/config.txt", "replicas=1\n")
            (repo / "infra").symlink_to("build/runtime")
            _write(repo, "build/out.txt", "A=1\n")
            (repo / ".env").symlink_to("build/out.txt")
            _declare(repo, *(('build/runtime/config.txt', 'build/out.txt')
                             if actual_declarations else ('infra/config.txt', '.env')))

        repo = _approved_project(tmp_path, direct_mode, build)

        def _edit(root: Path) -> None:
            (root / "infra" / "config.txt").write_text("replicas=2\n")
            (root / ".env").write_text("A=2\n")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=_edit)
        if actual_declarations:
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        else:
            issue = _refused(repo, outcome, "repair_round_protected")
            assert any(p.startswith("build/runtime/config.txt") for p in issue["details"]["protected"])
            assert any(p.startswith("build/out.txt") for p in issue["details"]["protected"])

    def test_a_planned_name_does_not_cover_an_unplanned_one(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """The same real file reached as declared infra/config.txt and as
        undeclared deploy/config.txt: the edit still counts."""
        def build(repo: Path) -> None:
            _write(repo, "build/runtime/config.txt", "replicas=1\n")
            (repo / "infra").symlink_to("build/runtime")
            (repo / "deploy" / "runtime").symlink_to("../build/runtime")
            _declare(repo, "infra/config.txt")

        repo = _approved_project(tmp_path, direct_mode, build)
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=lambda root: (root / "infra" / "config.txt").write_text("replicas=2\n"),
        )
        issue = _refused(repo, outcome, "repair_round_protected")
        assert any("deploy/runtime/config.txt" in p for p in issue["details"]["protected"])


class TestCoachTwoEdges:
    def test_a_sibling_folder_whose_name_starts_like_the_worktree_is_outside(
        self, tmp_path: Path
    ) -> None:
        """A worktree and its similarly named sibling: the separator matters."""
        from guardkit.orchestrator.repair_round import protected_files

        repo = make_project(tmp_path)
        sibling = Path(str(repo) + "-sibling")
        (sibling / "locked").mkdir(parents=True)
        _write(sibling, "Dockerfile", "FROM scratch\n")
        (repo / "infra").symlink_to(sibling)
        os.chmod(sibling / "locked", 0)  # walked, it would refuse
        try:
            files = protected_files(repo)
        finally:
            os.chmod(sibling / "locked", 0o755)
        assert "link:infra" in files
        assert not any("Dockerfile" in key and key != "deploy/Dockerfile" for key in files)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_outside_link_met_unprotected_first_is_recorded_from_a_protected_root(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """ansible -> build/runtime sorts before build/, so the first walk meets
        build/runtime/ext unprotected; the second walk, from ansible, records
        it as ansible/ext, and retargeting it is refused."""
        outside = tmp_path / "outside"
        (outside / "a").mkdir(parents=True)
        (outside / "b").mkdir()

        def build(repo: Path) -> None:
            (repo / "build" / "runtime").mkdir(parents=True)
            (repo / "build" / "runtime" / "ext").symlink_to(outside / "a")
            (repo / "ansible").symlink_to("build/runtime")

        repo = _approved_project(tmp_path / "p", direct_mode, build)

        def _retarget(root: Path) -> None:
            (root / "build" / "runtime" / "ext").unlink()
            (root / "build" / "runtime" / "ext").symlink_to(outside / "b")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=_retarget)
        issue = _refused(repo, outcome, "repair_round_protected")
        assert "build/runtime/ext (as ansible/ext)" in issue["details"]["protected"]

    @pytest.mark.timeout(60)
    def test_a_deep_chain_of_protected_folders_is_quick(self, tmp_path: Path) -> None:
        import time

        from guardkit.orchestrator.repair_round import protected_files

        repo = make_project(tmp_path)
        path = repo
        for _ in range(600):  # the coach's shape: 600 nested protected folders
            path = path / "helm"
        _write(path, "config.txt", "deep\n")
        started = time.monotonic()
        files = protected_files(repo)
        assert time.monotonic() - started < 10
        assert any(key.endswith("/config.txt") for key in files)


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
@pytest.mark.parametrize("shape", ["control-no-alias", "monorepo-alias", "unprotected-folder-alias"])
def test_a_planned_edit_of_a_declared_real_path_approves_whatever_aliases_reach_it(
    tmp_path: Path, direct_mode: bool, shape: str
) -> None:
    """Coach review 3: a task that declares a protected file's REAL path is
    not refused because an ordinary alias also reaches it (a monorepo's
    web/common -> ../common, or zops -> ops)."""
    if shape == "unprotected-folder-alias":
        target = "ops/migrations/0001.sql"
    else:
        target = "common/package.json"

    def build(repo: Path) -> None:
        if shape == "unprotected-folder-alias":
            _write(repo, target, "select 1;\n")
            (repo / "zops").symlink_to("ops")
        else:
            _write(repo, target, '{"name": "common"}\n')
            if shape == "monorepo-alias":
                (repo / "web").mkdir()
                (repo / "web" / "common").symlink_to("../common")
        _declare(repo, target)

    repo = _approved_project(tmp_path, direct_mode, build)
    outcome = reopen_and_repair(
        repo, {}, model_verdict=APPROVE,
        shell_step=lambda root: (root / target).write_text("changed\n"),
    )
    assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
class TestActualPathDeclarations:
    @pytest.mark.parametrize("declaration", ["two-aliases", "all-aliases", "actual"])
    def test_three_aliases_cannot_authorize_target_contents(
        self, tmp_path: Path, direct_mode: bool, declaration: str
    ) -> None:
        target = "build/runtime/config.txt"

        def build(repo: Path) -> None:
            _write(repo, target, "before\n")
            for name in ("ansible", "helm", "infra"):
                (repo / name).symlink_to("build/runtime")
            paths = {"two-aliases": ("ansible/config.txt", "infra/config.txt"),
                     "all-aliases": ("ansible/config.txt", "helm/config.txt", "infra/config.txt"),
                     "actual": (target,)}[declaration]
            _declare(repo, *paths)

        repo = _approved_project(tmp_path, direct_mode, build)
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=lambda root: (root / "helm/config.txt").write_text("after\n"),
        )
        if declaration == "actual":
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        else:
            issue = _refused(repo, outcome, "repair_round_protected")
            assert any(p.startswith(target) for p in issue["details"]["protected"])

    @pytest.mark.parametrize("actual_declaration", [False, True])
    @pytest.mark.parametrize("aliases", [("ansible", "helm", "infra"), ("infrastructure", "helm", "k8s")])
    def test_nested_link_permission_uses_its_actual_entry(
        self, tmp_path: Path, direct_mode: bool, actual_declaration: bool, aliases: tuple
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "build/runtime/README.a", "same\n")
            _write(repo, "build/runtime/README.b", "same\n")
            (repo / "build/runtime/current").symlink_to("README.a")
            for alias in aliases:
                (repo / alias).symlink_to("build/runtime")
            _declare(repo, *(('build/runtime/current',) if actual_declaration
                             else tuple(f"{alias}/current" for alias in aliases)))

        repo = _approved_project(tmp_path, direct_mode, build)

        def retarget(root: Path) -> None:
            link = root / aliases[1] / "current"
            link.unlink()
            link.symlink_to("README.b")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=retarget)
        if actual_declaration:
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        else:
            issue = _refused(repo, outcome, "repair_round_protected")
            assert any(p.startswith("build/runtime/current") for p in issue["details"]["protected"])

    @pytest.mark.parametrize("alias", ["docs", "large_tool_results", ".claude/task-plans",
                                      "tasks/completed", "conversation_history"])
    @pytest.mark.parametrize("changed", [False, True])
    def test_logical_factory_prefix_cannot_hide_an_actual_readme(
        self, tmp_path: Path, direct_mode: bool, alias: str, changed: bool
    ) -> None:
        target = "build/runtime/state/README.md"

        def build(repo: Path) -> None:
            _write(repo, target, "before\n")
            (repo / alias).parent.mkdir(parents=True, exist_ok=True)
            (repo / alias).symlink_to(os.path.relpath(repo / "build/runtime", (repo / alias).parent))

        repo = _approved_project(tmp_path, direct_mode, build)
        assert target in protected_fingerprints(repo)
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=(lambda root: (root / target).write_text("after\n")) if changed else None,
        )
        if changed:
            issue = _refused(repo, outcome, "repair_round_protected")
            assert any(p.startswith(target) for p in issue["details"]["protected"])
        else:
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("namespace", ["docs/state", ".guardkit", "tasks/in_progress",
        "large_tool_results", ".claude/task-plans", "conversation_history"])
    @pytest.mark.parametrize("retarget", [False, True])
    def test_factory_targets_stay_excluded_but_outside_links_are_guarded(
        self, tmp_path: Path, direct_mode: bool, namespace: str, retarget: bool
    ) -> None:
        target = f"{namespace}/README.fixture"

        def build(repo: Path) -> None:
            _write(repo, target, "before\n")
            (repo / "infra").symlink_to(namespace)
            (repo / "docs/state/other").mkdir(parents=True, exist_ok=True)

        repo = _approved_project(tmp_path, direct_mode, build)
        snapshot = protected_fingerprints(repo)
        assert target not in snapshot
        assert "link:infra" in snapshot

        def edit(root: Path) -> None:
            if retarget:
                (root / "infra").unlink()
                (root / "infra").symlink_to("docs/state/other")
            else:
                (root / "infra/README.fixture").write_text("after\n")

        outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=edit)
        if retarget:
            issue = _refused(repo, outcome, "repair_round_protected")
            assert "infra" in issue["details"]["protected"]
        else:
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("name", ["memory-query-log.jsonl", "memory-query-log.jsonl.1", "config.yaml"])
    def test_nested_factory_memory_logs_keep_their_narrow_exclusion(
        self, tmp_path: Path, direct_mode: bool, name: str
    ) -> None:
        target = f"infra/nested/.guardkit/{name}"
        repo = _approved_project(tmp_path, direct_mode, lambda root: _write(root, target, "before\n"))
        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE,
            shell_step=lambda root: (root / target).write_text("after\n"),
        )
        if name.startswith("memory-query-log.jsonl"):
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        else:
            _refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("directory", [".venv", ".venv-extra", ".local", "lib/site-packages",
                                           "nested/.tmp", "nested/.npm", "node_modules"])
    @pytest.mark.parametrize("alias_mode", ["none", "undeclared", "declared"])
    def test_package_install_noise_and_protected_aliases(
        self, tmp_path: Path, direct_mode: bool, directory: str, alias_mode: str
    ) -> None:
        target = f"{directory}/package.json"

        def build(repo: Path) -> None:
            _write(repo, target, '{"version": 1}\n')
            _write(repo, "common/package.json", '{"name": "fixture", "version": 1}\n')
            _declare(repo, "common/package.json", *((target,) if alias_mode == "declared" else ()))
            if alias_mode != "none":
                (repo / "infra").symlink_to(directory)

        repo = _approved_project(tmp_path, direct_mode, build)
        def installed_change(root: Path) -> None:
            # Simulate a dependency bump and its installed bytes. This audit
            # control never needs to invoke a package manager.
            (root / "common/package.json").write_text('{"name": "fixture", "version": 2}\n')
            (root / target).write_text('{"version": 2}\n')

        outcome = reopen_and_repair(
            repo, {}, model_verdict=APPROVE, shell_step=installed_change,
        )
        if alias_mode == "undeclared":
            issue = _refused(repo, outcome, "repair_round_protected")
            assert any(p.startswith(target) for p in issue["details"]["protected"])
        else:
            assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("entry", [".venv", ".local", "nested/.tmp", "nested/.npm"])
    def test_package_namespace_symlink_entry_is_recorded_before_pruning(
        self, tmp_path: Path, direct_mode: bool, entry: str
    ) -> None:
        def build(repo: Path) -> None:
            _write(repo, "build/a/README.md", "same\n")
            _write(repo, "build/b/README.md", "same\n")
            (repo / entry).parent.mkdir(parents=True, exist_ok=True)
            (repo / entry).symlink_to(os.path.relpath(repo / "build/a", (repo / entry).parent))

        repo = _approved_project(tmp_path, direct_mode, build)
        assert f"link:{entry}" in protected_fingerprints(repo)

        def retarget(root: Path) -> None:
            link = root / entry
            link.unlink()
            link.symlink_to(os.path.relpath(root / "build/b", link.parent))

        issue = _refused(repo, reopen_and_repair(
            repo, {}, model_verdict=APPROVE, shell_step=retarget,
        ), "repair_round_protected")
        assert entry in issue["details"]["protected"]


class TestActualPathSnapshotIdentity:
    def test_witness_changes_do_not_change_an_object_fingerprint(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_fingerprint_changes

        repo = make_project(tmp_path)
        _write(repo, "build/runtime/config.txt", "same\n")
        (repo / "infra").symlink_to("build/runtime")
        before = protected_fingerprints(repo)
        (repo / "infra").rename(repo / "ansible")
        after = protected_fingerprints(repo)
        key = "build/runtime/config.txt"
        assert before[key] != after[key]  # witnesses really changed
        assert key not in protected_fingerprint_changes(before.items(), after)
        assert {"link:infra", "link:ansible"} <= protected_fingerprint_changes(before.items(), after)

    def test_distinct_protected_hardlink_paths_have_distinct_records(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_fingerprint_changes

        repo = make_project(tmp_path)
        _write(repo, "infra/a.txt", "before\n")
        os.link(repo / "infra/a.txt", repo / "infra/b.txt")
        before = protected_fingerprints(repo)
        assert {"infra/a.txt", "infra/b.txt"} <= before.keys()
        (repo / "infra/a.txt").write_text("after\n")
        after = protected_fingerprints(repo)
        assert {"infra/a.txt", "infra/b.txt"} <= protected_fingerprint_changes(before.items(), after)

    @pytest.mark.parametrize("name", [".venv", ".local", ".tmp", ".npm", "site-packages", "node_modules"])
    def test_package_directory_names_do_not_exclude_plain_files(self, tmp_path: Path, name: str) -> None:
        repo = make_project(tmp_path)
        _write(repo, f"infra/{name}", "ordinary file\n")
        assert f"infra/{name}" in protected_fingerprints(repo)


def test_git_worktree_marker_is_not_a_protected_file(tmp_path: Path) -> None:
    _write(tmp_path, ".git", "gitdir: elsewhere\n")
    assert protected_fingerprints(tmp_path) == {}


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
@pytest.mark.parametrize("both_declared", [False, True])
def test_hardlink_content_changes_require_each_actual_protected_path(
    tmp_path: Path, direct_mode: bool, both_declared: bool
) -> None:
    def build(repo: Path) -> None:
        _write(repo, "infra/a.txt", "before\n")
        os.link(repo / "infra/a.txt", repo / "infra/b.txt")
        _declare(repo, "infra/a.txt", *(("infra/b.txt",) if both_declared else ()))

    repo = _approved_project(tmp_path, direct_mode, build)
    outcome = reopen_and_repair(
        repo, {}, model_verdict=APPROVE,
        shell_step=lambda root: (root / "infra/a.txt").write_text("after\n"),
    )
    if both_declared:
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
    else:
        issue = _refused(repo, outcome, "repair_round_protected")
        assert "infra/b.txt" in issue["details"]["protected"]


@pytest.mark.parametrize("target", ["tasks/custom/README.md", "large_tool_results-copy/README.md",
    ".claude/custom/README.md", "conversation_history-copy/README.md"])
def test_factory_exclusions_do_not_expand_to_neighboring_namespaces(tmp_path: Path, target: str) -> None:
    _write(tmp_path, target, "ordinary protected file\n")
    assert target in protected_fingerprints(tmp_path)


@pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
@pytest.mark.parametrize("all_actual_paths", [False, True])
def test_link_retarget_membership_requires_old_and_new_actual_target_declarations(
    tmp_path: Path, direct_mode: bool, all_actual_paths: bool
) -> None:
    """A declared link does not authorize other records entering/leaving the
    protected set, even when their existing bytes remain unchanged."""
    targets = ("build/a.txt", "build/b.txt")

    def build(repo: Path) -> None:
        _write(repo, targets[0], "first target\n")
        _write(repo, targets[1], "second target\n")
        (repo / ".env").symlink_to(targets[0])
        _declare(repo, ".env", *(targets if all_actual_paths else ()))

    repo = _approved_project(tmp_path, direct_mode, build)
    before_bytes = {target: (repo / target).read_bytes() for target in targets}
    before = protected_fingerprints(repo)
    assert targets[0] in before and targets[1] not in before

    def retarget(root: Path) -> None:
        (root / ".env").unlink()
        (root / ".env").symlink_to(targets[1])

    outcome = reopen_and_repair(repo, {}, model_verdict=APPROVE, shell_step=retarget)
    assert {target: (repo / target).read_bytes() for target in targets} == before_bytes
    after = protected_fingerprints(repo)
    assert targets[0] not in after and targets[1] in after
    if all_actual_paths:
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
    else:
        issue = _refused(repo, outcome, "repair_round_protected")
        assert {p.split(" (as ", 1)[0] for p in issue["details"]["protected"]} == set(targets)
