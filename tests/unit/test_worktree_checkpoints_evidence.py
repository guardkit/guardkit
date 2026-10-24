"""Evidence-repo checkpointing tests (TASK-AB-XREPOEV01 AC-004).

Verifies that ``WorktreeCheckpointManager`` commits and rolls back declared
sibling repos alongside the worktree, closing the BDDW-002 hazard (approved
sibling-repo work that was never versioned anywhere).
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.worktree_checkpoints import (
    Checkpoint,
    GitCommandExecutor,
    SubprocessGitExecutor,
    WorktreeCheckpointManager,
)

from guardkit.orchestrator.task_work_scope import bind_fresh_footprint, ScopeUnavailable
from tests.task_scope_fixtures import admitted_task, git, register_clean_fresh_checkout


@contextmanager
def _checkpoint_scope(worktree, task_id, evidence_repos=()):
    """Bind invented sibling inputs at the clean source, before Player writes."""
    if evidence_repos:
        declaration = worktree / ".guardkit" / "features" / "FEAT-CHECKPOINT.yaml"
        declaration.parent.mkdir(parents=True, exist_ok=True)
        raw = [str(repo.root) for repo in evidence_repos]
        declaration.write_text(json.dumps({"evidence_repos": raw}))
        git(worktree, "add", str(declaration.relative_to(worktree)))
        git(worktree, "commit", "-m", "fixture sibling declaration")
        register_clean_fresh_checkout(worktree)
        bound = bind_fresh_footprint(
            worktree, worktree, declaration, kind="feature", expected=raw
        )
        assert list(bound) == list(evidence_repos)
    else:
        register_clean_fresh_checkout(worktree)
        bound = ()
    with admitted_task(worktree, task_id, evidence_repos=bound) as (_, scope):
        yield scope


def _set_identity(path: Path) -> None:
    """Give a throwaway repo its own committer identity.

    ``git commit`` exits 128 ("Please tell me who you are") wherever no
    ``user.email``/``user.name`` is configured. A CI runner has none, and
    neither does a freshly set-up developer machine, so every test repo
    configures its own REPO-LOCAL identity instead of relying on whatever the
    machine happens to have globally.
    """
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(
            ["git", "-C", str(path), "config", key, value],
            check=True,
            capture_output=True,
        )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    _set_identity(path)
    (path / ".keep").write_text("x\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
        capture_output=True,
    )


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def worktree_and_sibling(tmp_path):
    worktree = tmp_path / "worktree"
    sibling = tmp_path / "guardkitfactory"
    _init_repo(worktree)
    _init_repo(sibling)
    return worktree, sibling


class TestEvidenceRepoCheckpoint:
    def test_checkpoint_commits_sibling_repo_work(self, worktree_and_sibling):
        worktree, sibling = worktree_and_sibling
        repo = EvidenceRepo(name="guardkitfactory", root=sibling)
        with _checkpoint_scope(worktree, "TASK-X", [repo]) as scope:
            manager = WorktreeCheckpointManager(
                task_work_scope=scope,
                worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo]
            )

            # Player writes only in the sibling repo.
            (sibling / "src").mkdir()
            (sibling / "src" / "deliverable.py").write_text("def f(): return 1\n")
            sibling_head_before = _head(sibling)

            cp = manager.create_checkpoint(turn=1, tests_passed=True, test_count=3)

            # Sibling work is now committed and recorded on the checkpoint.
            assert "guardkitfactory" in cp.evidence_commits
            assert cp.evidence_commits["guardkitfactory"] == _head(sibling)
            assert _head(sibling) != sibling_head_before
            # The deliverable is versioned (tracked, clean tree). The one
            # permitted residue is ``.guardkit-git.lock``: the sibling-commit
            # path creates that lock in the repo root (``:674``) and the JX
            # lane's junk-exclude keeps it OUT of the commit — before that, the
            # checkpoint versioned the harness's own lock file, which is the
            # defect, not this line.
            status = subprocess.run(
                ["git", "-C", str(sibling), "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            residue = [
                line
                for line in status.stdout.splitlines()
                if line.strip() and not line.endswith(".guardkit-git.lock")
            ]
            assert residue == [], f"unexpected uncommitted sibling state: {residue}"
            assert "?? .guardkit-git.lock" in status.stdout, (
                "the harness lock must be left untracked, never checkpointed"
            )

    def test_rollback_resets_sibling_repo(self, worktree_and_sibling):
        worktree, sibling = worktree_and_sibling
        repo = EvidenceRepo(name="guardkitfactory", root=sibling)
        with _checkpoint_scope(worktree, "TASK-X", [repo]) as scope:
            manager = WorktreeCheckpointManager(
                task_work_scope=scope,
                worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo]
            )

            # Turn 1: good sibling work, checkpoint.
            (sibling / "good.py").write_text("ok = True\n")
            manager.create_checkpoint(turn=1, tests_passed=True)
            good_head = _head(sibling)

            # Turn 2: polluted sibling work, checkpoint.
            (sibling / "bad.py").write_text("broken = True\n")
            manager.create_checkpoint(turn=2, tests_passed=False)
            assert (sibling / "bad.py").exists()

            # Roll back to turn 1.
            assert manager.rollback_to(1) is True
            assert _head(sibling) == good_head
            assert (sibling / "good.py").exists()
            assert not (sibling / "bad.py").exists()  # polluted work discarded

    def test_no_evidence_repos_is_unchanged_behaviour(self, worktree_and_sibling):
        worktree, _ = worktree_and_sibling
        with _checkpoint_scope(worktree, "TASK-X", ()) as scope:
            manager = WorktreeCheckpointManager(worktree_path=worktree, task_id="TASK-X", task_work_scope=scope)
            cp = manager.create_checkpoint(turn=1, tests_passed=True)
            assert cp.evidence_commits == {}

    def test_hung_sibling_commit_times_out_and_does_not_deadlock(self, tmp_path):
        # HIGH review fix: a hung git in the sibling repo must time out (it
        # holds a cross-process lock), return None, and not abort the worktree
        # checkpoint. The evidence repo's commits raise TimeoutExpired; the
        # worktree commits succeed.
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        factory = tmp_path / "guardkitfactory"
        _init_repo(factory)
        repo = EvidenceRepo(name="guardkitfactory", root=factory)

        real_executor = SubprocessGitExecutor()

        def fake_execute(command, cwd, check=True, timeout=None):
            if Path(cwd) == factory:
                raise subprocess.TimeoutExpired(cmd=command, timeout=timeout or 0)
            return real_executor.execute(command, cwd, check=check, timeout=timeout)

        executor = Mock(spec=GitCommandExecutor)
        executor.execute.side_effect = fake_execute

        with _checkpoint_scope(worktree, "TASK-X", [repo]) as scope:
            manager = WorktreeCheckpointManager(
                task_work_scope=scope,
                worktree_path=worktree,
                task_id="TASK-X",
                git_executor=executor,
                evidence_repos=[repo],
            )
            cp = manager.create_checkpoint(turn=1, tests_passed=True)
            assert cp.commit_hash == _head(worktree)  # real primary checkpoint landed
            assert "guardkitfactory" not in cp.evidence_commits  # timed out -> unversioned

    def test_non_git_sibling_is_refused_before_checkpoint(self, tmp_path):
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()
        (not_a_repo / "preserved.txt").write_text("unowned work\n")
        repo = EvidenceRepo(name="plain", root=not_a_repo)
        before = _head(worktree)
        with _checkpoint_scope(worktree, "TASK-X") as scope:
            manager = WorktreeCheckpointManager(
                worktree_path=worktree, task_id="TASK-X", evidence_repos=[repo],
                task_work_scope=scope,
            )
            with pytest.raises(ScopeUnavailable, match="membership differs"):
                manager.create_checkpoint(turn=1, tests_passed=True)
        assert _head(worktree) == before
        assert (not_a_repo / "preserved.txt").read_text() == "unowned work\n"
        assert not (not_a_repo / ".git").exists()


class TestCheckpointBackwardCompat:
    def test_old_checkpoint_json_without_evidence_commits(self):
        # checkpoints.json written before evidence support has no
        # evidence_commits key; Checkpoint(**data) must still deserialise.
        old = {
            "turn": 1,
            "commit_hash": "abc123",
            "timestamp": "2026-01-01T00:00:00",
            "tests_passed": True,
            "test_count": 5,
            "message": "old",
            "from_prior_run": False,
        }
        cp = Checkpoint.from_dict(old)
        assert cp.evidence_commits == {}

    def test_roundtrip_with_evidence_commits(self):
        cp = Checkpoint(
            turn=2,
            commit_hash="def456",
            timestamp="2026-01-01T00:00:00",
            tests_passed=True,
            evidence_commits={"guardkitfactory": "sha999"},
        )
        restored = Checkpoint.from_dict(cp.to_dict())
        assert restored.evidence_commits == {"guardkitfactory": "sha999"}


class TestCheckpointJunkExclusion:
    """Register 2a5 (2026-07-30): checkpoints must not bake machine-local junk."""

    def test_checkpoint_excludes_pip_cache_and_bootstrap_state(
        self, tmp_path
    ) -> None:
        import subprocess

        from guardkit.orchestrator.worktree_checkpoints import (
            WorktreeCheckpointManager,
        )

        wt = tmp_path / "wt"
        wt.mkdir()
        subprocess.run(["git", "-C", str(wt), "init", "-q"], check=True)
        _set_identity(wt)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-q", "--allow-empty", "-m", "seed"],
            check=True,
        )
        with _checkpoint_scope(wt, "TASK-JUNK-1", ()) as scope:
            # A real source change + the two junk classes.
            (wt / "src").mkdir()
            (wt / "src" / "real.py").write_text("x = 1\n")
            (wt / ".cache" / "pip" / "http-v2").mkdir(parents=True)
            (wt / ".cache" / "pip" / "http-v2" / "blob").write_text("junk")
            (wt / ".guardkit").mkdir(exist_ok=True)
            (wt / ".guardkit" / "bootstrap_state.json").write_text("{}")

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-JUNK-1", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None

            shown = subprocess.run(
                ["git", "-C", str(wt), "show", "--name-only", "--format=", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            assert "src/real.py" in shown
            assert ".cache/" not in shown
            assert "bootstrap_state.json" not in shown

    def test_checkpoint_survives_repo_gitignoring_the_same_junk(
        self, tmp_path
    ) -> None:
        """Belt + braces must not collide (FEAT-153C, 2026-07-31).

        When the target repo's own .gitignore ALSO lists the junk classes
        (api_test `82707ca`), a bare `:(exclude).cache` pathspec makes
        git 2.43 refuse the add outright (exit 1, "paths are ignored") the
        moment an ignored `.cache` exists on disk — the checkpoint dies
        before turn 1's commit. The glob-magic form must checkpoint clean.
        """
        import subprocess

        from guardkit.orchestrator.worktree_checkpoints import (
            WorktreeCheckpointManager,
        )

        wt = tmp_path / "wt"
        wt.mkdir()
        subprocess.run(["git", "-C", str(wt), "init", "-q"], check=True)
        _set_identity(wt)
        (wt / ".gitignore").write_text(".cache/\n.guardkit/bootstrap_state.json\n")
        subprocess.run(["git", "-C", str(wt), "add", ".gitignore"], check=True)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-q", "-m", "seed w/ belt"],
            check=True,
        )
        with _checkpoint_scope(wt, "TASK-JUNK-2", ()) as scope:
            (wt / "src").mkdir()
            (wt / "src" / "real.py").write_text("x = 1\n")
            (wt / ".cache" / "pip").mkdir(parents=True)
            (wt / ".cache" / "pip" / "blob").write_text("junk")
            (wt / ".guardkit").mkdir(exist_ok=True)
            (wt / ".guardkit" / "bootstrap_state.json").write_text("{}")

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-JUNK-2", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None, "checkpoint must survive the repo's own gitignore belt"

            shown = subprocess.run(
                ["git", "-C", str(wt), "show", "--name-only", "--format=", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            assert "src/real.py" in shown
            assert ".cache/" not in shown
            assert "bootstrap_state.json" not in shown


# =========================================================================
# TS-lane D.1c — the JUNK LAW extended to the JavaScript/TypeScript classes
# =========================================================================
#
# Design §B.6: "build junk is excluded by PATHSPEC, never by the target
# repo's .gitignore." The intent was written into the checkpoint code's own
# comment on 2026-07-30 and only Python junk was enumerated. ``706589f7``
# fixed the glob magic, not the coverage.
#
# The 706589f7 lesson is the law for the STYLE of every entry here, and it
# cuts BOTH ways, which is why every class below is proven in BOTH repo
# shapes:
#   * a repo that ALSO gitignores the junk — a wildcard-free
#     ``:(exclude)node_modules`` makes git 2.43 refuse the add outright
#     (exit 1, "paths are ignored") and the checkpoint dies; and
#   * a repo that does NOT gitignore it — an un-magicked ``**/node_modules/**``
#     (no ``,glob``) excludes NOTHING, and the junk lands in the commit.
# Only the fully-wildcarded ``:(exclude,glob)**/...`` form survives both.


def _init_bare_worktree(wt: Path, *, gitignore: str | None = None) -> None:
    """A scratch repo, with or without its own .gitignore belt."""
    wt.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(wt), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(wt), "config", "user.email", "t@t"], check=True
    )
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "t"], check=True)
    if gitignore is not None:
        (wt / ".gitignore").write_text(gitignore, encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "add", ".gitignore"], check=True)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-q", "-m", "seed w/ belt"], check=True
        )
    else:
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-q", "--allow-empty", "-m", "seed"],
            check=True,
        )


# The .gitignore a real TypeScript repo ships (ts-api-test, verified).
_TS_GITIGNORE = "node_modules/\ndist/\ncoverage/\n*.tsbuildinfo\n.DS_Store\n"


def _write_ts_junk_and_work(wt: Path) -> None:
    """Every junk class from design §B.6, plus real work and real ``dist/``."""
    # Real Player work — must survive.
    (wt / "src").mkdir(parents=True, exist_ok=True)
    (wt / "src" / "real.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (wt / "tests").mkdir(parents=True, exist_ok=True)
    (wt / "tests" / "real.test.ts").write_text("// t\n", encoding="utf-8")

    # node_modules at the root AND nested (monorepo shape).
    (wt / "node_modules" / "fastify").mkdir(parents=True, exist_ok=True)
    (wt / "node_modules" / "fastify" / "index.js").write_text("//dep\n")
    (wt / "packages" / "api" / "node_modules" / "dep").mkdir(parents=True)
    (wt / "packages" / "api" / "node_modules" / "dep" / "d.js").write_text("//d\n")

    # The framework caches.
    (wt / ".next" / "cache").mkdir(parents=True, exist_ok=True)
    (wt / ".next" / "cache" / "blob").write_text("junk")
    (wt / ".turbo").mkdir(parents=True, exist_ok=True)
    (wt / ".turbo" / "turbo.log").write_text("junk")

    # Coverage output, root and nested.
    (wt / "coverage" / "lcov-report").mkdir(parents=True, exist_ok=True)
    (wt / "coverage" / "lcov-report" / "index.html").write_text("junk")

    # Incremental-build stamps.
    (wt / "tsconfig.tsbuildinfo").write_text("{}")

    # dist/ is DELIBERATELY NOT excluded (design §B.6) — it is a real
    # deliverable in some repos, and dropping shipped output by pathspec
    # would be silent.
    (wt / "dist").mkdir(parents=True, exist_ok=True)
    (wt / "dist" / "server.js").write_text("//built\n")


def _committed_paths(wt: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(wt), "show", "--name-only", "--format=", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _assert_ts_junk_absent(shown: str) -> None:
    assert "src/real.ts" in shown, "real Player work must be checkpointed"
    assert "node_modules" not in shown
    assert ".next/" not in shown
    assert ".turbo/" not in shown
    assert "coverage/" not in shown
    assert ".tsbuildinfo" not in shown


class TestCheckpointExcludesTypeScriptJunk:
    """TS-lane D.1c: the JS/TS junk classes, proven in BOTH repo shapes."""

    def test_worktree_checkpoint_excludes_ts_junk_without_gitignore(
        self, tmp_path
    ) -> None:
        """The 706589f7 regression pattern, second half.

        A scratch repo WITHOUT a .gitignore is the shape that proves the
        pathspec is doing the work. ``git add -A`` would otherwise stage
        every file under ``node_modules/`` — the exact 2a5 flood in a new
        alphabet — and the target repo's own hygiene is precisely the
        dependency the checkpoint comment says this code exists to remove.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=None)
        with _checkpoint_scope(wt, "TASK-TS-1", ()) as scope:
            _write_ts_junk_and_work(wt)

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-TS-1", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None

            _assert_ts_junk_absent(_committed_paths(wt))

    def test_worktree_checkpoint_survives_repo_gitignoring_ts_junk(
        self, tmp_path
    ) -> None:
        """The 706589f7 regression pattern, first half.

        ts-api-test's real .gitignore lists every one of these classes. A
        wildcard-free exclude pathspec naming junk the repo ALSO ignores
        makes git 2.43 refuse the whole add — the checkpoint dies after a
        turn-1 coach approve, which is how FEAT-153C was found.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=_TS_GITIGNORE)
        with _checkpoint_scope(wt, "TASK-TS-2", ()) as scope:
            _write_ts_junk_and_work(wt)

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-TS-2", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None, (
                "checkpoint must survive the target repo's own gitignore belt"
            )

            _assert_ts_junk_absent(_committed_paths(wt))

    def test_dist_output_is_deliberately_still_committed(self, tmp_path) -> None:
        """Design §B.6, explicitly: ``dist/`` is NOT on the exclude list.

        ``dist/`` is a real deliverable in some repos (ts-api-test builds
        into it and gitignores it, but that is THAT repo's choice, not a
        law). Excluding it by pathspec would silently drop shipped output.
        Proven in the non-ignoring shape, where the pathspec is the only
        thing that could drop it.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=None)
        with _checkpoint_scope(wt, "TASK-TS-3", ()) as scope:
            _write_ts_junk_and_work(wt)

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-TS-3", task_work_scope=scope)
            mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)

            assert "dist/server.js" in _committed_paths(wt)

    def test_evidence_repo_checkpoint_excludes_ts_junk(self, tmp_path) -> None:
        """The SECOND add site (``:600-611``) carries the same law.

        Both sites are identical by construction (one shared constant), and
        this proves the sibling-evidence commit end to end rather than by
        reading the source.
        """
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        sibling = tmp_path / "ts-sibling"
        _init_bare_worktree(sibling, gitignore=None)
        repo = EvidenceRepo(name="ts-sibling", root=sibling)
        with _checkpoint_scope(worktree, "TASK-TS-4", [repo]) as scope:
            _write_ts_junk_and_work(sibling)

            mgr = WorktreeCheckpointManager(
                task_work_scope=scope,
                worktree_path=worktree, task_id="TASK-TS-4", evidence_repos=[repo]
            )
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)

            assert "ts-sibling" in cp.evidence_commits
            _assert_ts_junk_absent(_committed_paths(sibling))

    def test_both_add_sites_use_the_identical_exclude_list(self) -> None:
        """The two sites drifting apart is the failure mode this pins.

        Register 2a5 landed them as two copy-pasted literals; 706589f7 had
        to fix both. D.1c makes them ONE constant, and every entry is
        fully-wildcarded glob magic — the un-magicked form is a silent no-op.
        """
        import inspect

        from guardkit.orchestrator import worktree_checkpoints as wc

        assert wc.CHECKPOINT_EXCLUDE_PATHSPECS == (
            ":(exclude,glob)**/.cache/**",
            ":(exclude,glob)**/.guardkit/bootstrap_state.json",
            # LI stage-2: the Python junk classes — bytecode caches at any
            # depth and ``.local/`` (a pip --user install under a worktree
            # HOME). 223 junk files landed on one real work-leg drive.
            ":(exclude,glob)**/__pycache__/**",
            ":(exclude,glob)**/*.pyc",
            ":(exclude,glob)**/.local/**",
            # FL lane: the Dart classes — the pub cache (vendored source whose
            # OAuth samples trip the secret scan) and .dart_tool.
            ":(exclude,glob)**/.pub-cache/**",
            ":(exclude,glob)**/.dart_tool/**",
            # The HOME-pointed Dart family + the twice-seen harness spool.
            ":(exclude,glob)**/.dartServer/**",
            ":(exclude,glob)**/.dart-tool/**",
            ":(exclude,glob)**/.config/flutter/**",
            ":(exclude,glob)**/.flutter",
            ":(exclude,glob)**/.flutter/**",
            ":(exclude,glob)**/large_tool_results/**",
            ":(exclude,glob)**/large_tool_results",
            ":(exclude,glob)**/node_modules/**",
            ":(exclude,glob)**/.next/**",
            ":(exclude,glob)**/.turbo/**",
            ":(exclude,glob)**/coverage/**",
            ":(exclude,glob)**/*.tsbuildinfo",
            ":(exclude,glob)**/.tmp/**",
            ":(exclude,glob)**/.npm/**",
            ":(exclude,glob)**/.claude/task-plans/**",
            ":(exclude,glob)**/.guardkit-git.lock",
            # GuardKit's own build records (14 October 2026), the HEAD record
            # (head-identity.jsonl) included; the top-level transcript folder
            # is taken out after the add instead, never named here.
            ":(exclude,glob)**/.guardkit/autobuild/**",
            ":(exclude,glob)**/.guardkit/autobuild",
            ":(exclude,glob)**/.guardkit/qav-shadow/**",
            ":(exclude,glob)**/.guardkit/qav-shadow",
            ":(exclude,glob)**/.guardkit/memory-query-log.jsonl*",
            ":(exclude,glob)**/.guardkit/worktrees/**",
            ":(exclude,glob)**/.guardkit/worktrees",
            # GuardKit's private records (13 October 2026): the final
            # feature-check record can carry a credential in its output tails.
            ":(exclude,glob)**/.guardkit/autobuild-private/**",
            ":(exclude,glob)**/.guardkit/autobuild-private",
        )
        for spec in wc.CHECKPOINT_EXCLUDE_PATHSPECS:
            assert spec.startswith(":(exclude,glob)"), (
                f"{spec!r} must carry glob magic (706589f7): the un-magicked "
                "form excludes nothing in a repo without a .gitignore"
            )
            assert "**" in spec, f"{spec!r} must be fully wildcarded"

        # Neither add site may hand-roll its own list.
        source = inspect.getsource(wc)
        assert source.count('":(exclude,glob)') == len(
            wc.CHECKPOINT_EXCLUDE_PATHSPECS
        ), "exclude pathspecs must be declared exactly once, in the constant"

    def test_dist_is_not_on_the_exclude_list(self) -> None:
        """Design §B.6 says 'Explicitly NOT dist/' — pinned, not remembered."""
        from guardkit.orchestrator import worktree_checkpoints as wc

        assert not any(
            "dist" in spec for spec in wc.CHECKPOINT_EXCLUDE_PATHSPECS
        )


# =========================================================================
# JX lane — npm's caches are minted INSIDE the worktree
# =========================================================================
#
# Evidence: the two real TypeScript builds (FEAT-TST1 on ts-api-test,
# 2026-07-31 → 08-01). Checkpoint ``ce4f43b`` carried
#   1365 paths under ``.tmp/``   (node's compile cache)
#      8 paths under ``.npm/``   (npm ``_logs/`` + update-notifier stamp)
#      1 ``.claude/task-plans/`` plan stub (orchestrator-minted)
#      1 ``.guardkit-git.lock``  (the harness's cross-process lock)
# beside roughly ten paths of real Player work. ts-api-test's .gitignore
# lists node_modules/dist/coverage/*.tsbuildinfo and knows nothing about
# any of the four — which is precisely the target-repo-hygiene dependency
# the junk law exists to remove.
#
# Each class is proven in BOTH repo shapes, per the 706589f7 pattern:
#   * WITHOUT a .gitignore — proves the pathspec is doing the work (the
#     un-magicked ``**`` form would be a silent no-op here); and
#   * WITH the repo gitignoring the same junk — proves the add is not
#     REFUSED outright (exit 1, "paths are ignored"), which is how the
#     wildcard-free form killed a checkpoint after a turn-1 coach approve.


# What a repo that HAS learned about npm's in-worktree caches would ignore.
_NPM_CACHE_GITIGNORE = (
    "node_modules/\n.tmp/\n.npm/\n.claude/task-plans/\n.guardkit-git.lock\n"
)


def _write_npm_cache_junk_and_work(wt: Path) -> None:
    """The exact junk classes checkpoint ``ce4f43b`` swept up, plus work."""
    # Real Player work — must survive.
    (wt / "src").mkdir(parents=True, exist_ok=True)
    (wt / "src" / "time.ts").write_text("export const t = 1;\n", encoding="utf-8")

    # node's compile cache: root, and nested (npm run from a workspace dir).
    (wt / ".tmp" / "node-compile-cache" / "v22.18.0-arm64").mkdir(parents=True)
    (wt / ".tmp" / "node-compile-cache" / "v22.18.0-arm64" / "015aa58f").write_text(
        "junk"
    )
    (wt / "packages" / "api" / ".tmp").mkdir(parents=True)
    (wt / "packages" / "api" / ".tmp" / "blob").write_text("junk")

    # npm's own cache dir.
    (wt / ".npm" / "_logs").mkdir(parents=True)
    (wt / ".npm" / "_logs" / "2026-08-01T06_42_36_334Z-debug-0.log").write_text("j")
    (wt / ".npm" / "_update-notifier-last-checked").write_text("j")

    # The orchestrator's plan stub.
    (wt / ".claude" / "task-plans").mkdir(parents=True)
    (wt / ".claude" / "task-plans" / "TASK-TST1-001-implementation-plan.md").write_text(
        "# plan\n"
    )

    # The harness's cross-process git lock.
    (wt / ".guardkit-git.lock").write_text("")

    # Player-authorable ``.claude/`` content that MUST survive: the exclude
    # is anchored to ``task-plans/`` precisely so these are not swept up.
    (wt / ".claude" / "rules").mkdir(parents=True)
    (wt / ".claude" / "rules" / "autobuild.md").write_text("# rule\n")

    # A ``.tmp``-SUFFIXED file is not a ``.tmp`` directory — must survive.
    (wt / "src" / "fixture.tmp").write_text("data\n")


def _assert_npm_cache_junk_absent(shown: str) -> None:
    assert "src/time.ts" in shown, "real Player work must be checkpointed"
    assert ".tmp/" not in shown, "node's compile cache must not be checkpointed"
    assert ".npm/" not in shown, "npm's cache must not be checkpointed"
    assert "task-plans" not in shown, "the plan stub is orchestrator-minted"
    assert ".guardkit-git.lock" not in shown, "the harness lock is not work"
    # Over-exclusion guards — the anchoring must not eat real work.
    assert ".claude/rules/autobuild.md" in shown, (
        "``.claude/`` at large is Player-authorable: the exclude is anchored "
        "to ``task-plans/`` and must not swallow the rest of ``.claude/``"
    )
    assert "src/fixture.tmp" in shown, (
        "``**/.tmp/**`` excludes a .tmp DIRECTORY, never a .tmp-suffixed file"
    )


class TestCheckpointExcludesNpmCacheJunk:
    """JX lane: npm's in-worktree caches, proven in BOTH repo shapes."""

    def test_worktree_checkpoint_excludes_npm_cache_junk_without_gitignore(
        self, tmp_path
    ) -> None:
        """The shape ts-api-test actually had: nothing gitignored.

        ts-api-test's .gitignore covers node_modules/dist/coverage/
        *.tsbuildinfo and NOT one of these four classes, which is why
        checkpoint ``ce4f43b`` committed 1374 junk paths. The pathspec —
        not the target repo's hygiene — has to do the work.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=None)
        with _checkpoint_scope(wt, "TASK-JX-1", ()) as scope:
            _write_npm_cache_junk_and_work(wt)

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-JX-1", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None

            _assert_npm_cache_junk_absent(_committed_paths(wt))

    def test_worktree_checkpoint_survives_repo_gitignoring_npm_cache_junk(
        self, tmp_path
    ) -> None:
        """The 706589f7 refusal half, for the four new classes.

        Once a target repo learns to gitignore these (the obvious local
        cure), a wildcard-free exclude pathspec naming them would make
        git 2.43 refuse the whole add — checkpoint dead after a turn-1
        coach approve. The fully-wildcarded form must survive.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=_NPM_CACHE_GITIGNORE)
        with _checkpoint_scope(wt, "TASK-JX-2", ()) as scope:
            _write_npm_cache_junk_and_work(wt)

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-JX-2", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None, (
                "checkpoint must survive the repo's own gitignore belt (706589f7)"
            )

            _assert_npm_cache_junk_absent(_committed_paths(wt))

    def test_evidence_repo_checkpoint_excludes_npm_cache_junk(
        self, tmp_path
    ) -> None:
        """The SECOND add site carries the same law (one shared constant)."""
        worktree = tmp_path / "worktree"
        _init_repo(worktree)
        sibling = tmp_path / "npm-sibling"
        _init_bare_worktree(sibling, gitignore=None)
        repo = EvidenceRepo(name="npm-sibling", root=sibling)
        with _checkpoint_scope(worktree, "TASK-JX-3", [repo]) as scope:
            _write_npm_cache_junk_and_work(sibling)

            mgr = WorktreeCheckpointManager(
                task_work_scope=scope,
                worktree_path=worktree, task_id="TASK-JX-3", evidence_repos=[repo]
            )
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)

            assert "npm-sibling" in cp.evidence_commits
            _assert_npm_cache_junk_absent(_committed_paths(sibling))

    def test_tracked_claude_work_still_checkpoints_when_modified(
        self, tmp_path
    ) -> None:
        """The over-exclusion hazard, pinned where it would bite hardest.

        guardkit's own repo TRACKS 1606 files under ``.claude/`` and is
        itself an autobuild target. A blanket ``**/.claude/**`` exclude
        would silently drop a Player's edit to a tracked ``.claude/rules/``
        file from every checkpoint — pathspec excludes suppress staging of
        MODIFICATIONS to tracked files too, not just new junk. This is the
        same test ``dist/`` passes by being absent from the list.
        """
        wt = tmp_path / "wt"
        _init_bare_worktree(wt, gitignore=None)
        (wt / ".claude" / "rules").mkdir(parents=True)
        (wt / ".claude" / "rules" / "autobuild.md").write_text("# v1\n")
        subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "-q", "-m", "tracked .claude"],
            check=True,
        )

        with _checkpoint_scope(wt, "TASK-JX-4", ()) as scope:
            # The Player edits the tracked rule as its deliverable.
            (wt / ".claude" / "rules" / "autobuild.md").write_text("# v2 (player)\n")

            mgr = WorktreeCheckpointManager(worktree_path=wt, task_id="TASK-JX-4", task_work_scope=scope)
            cp = mgr.create_checkpoint(turn=1, tests_passed=True, test_count=0)
            assert cp is not None

            assert ".claude/rules/autobuild.md" in _committed_paths(wt), (
                "a tracked .claude/ deliverable must still be checkpointed"
            )
