"""Real Git writer admission and normal report/audit/checkpoint consumers.

No model, broker, remote repository or fixture product is used.
"""

import json
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace, MethodType

import pytest

from guardkit.orchestrator.task_work_scope import (
    checkout_lease,
    register_fresh_checkout,
    collect_changes,
    ScopeUnavailable,
)
from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def repository(root):
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / "base").write_text("baseline\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "immutable source")
    register_fresh_checkout(root, git(root, "rev-parse", "HEAD"))
    return root


def test_checkpoint_cumulative_inventory_and_audit_have_one_baseline(tmp_path):
    root = repository(tmp_path / "checkout")
    sys.path.insert(
        0, str(Path(__file__).resolve().parents[3] / "installer/core/commands")
    )
    from lib.plan_audit import PlanAuditor

    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-A")
        invoker = AgentInvoker(worktree_path=root)
        (root / "extensionless").write_text("new content\n")
        checkpoint = WorktreeCheckpointManager(
            root, "TASK-A", expected_branch="main", task_work_scope=scope
        )
        first = checkpoint.create_checkpoint(1, None)
        (root / "odd.unlisted-format").write_text("second turn\n")
        (root / "base").unlink()
        observed = collect_changes(scope)
        assert observed["created"] == ["extensionless", "odd.unlisted-format"]
        assert observed["deleted"] == ["base"]
        assert invoker._detect_git_changes()["created"] == observed["created"]
        auditor = PlanAuditor(root, task_work_scope=scope)
        assert auditor._files_this_task_changed("TASK-A") == {
            "created": ["extensionless", "odd.unlisted-format"],
            "modified": ["base"],
        }
        assert auditor._task_start_commit("TASK-A") == scope.baseline_commit
        assert first.scope_id == scope.scope_id
        assert first.baseline_commit == scope.baseline_commit
        checkpoint.create_checkpoint(2, None)
    with checkout_lease(root) as lease:
        successor = lease.admit("TASK-B")
        assert successor.baseline_commit != scope.baseline_commit
        assert collect_changes(successor)["created"] == []


def test_unapproved_checkpoint_is_kept_and_the_next_writer_is_admitted(tmp_path):
    """Step 2 (26 October 2026): an unapproved writer's work stays for the
    next writer, which is admitted."""
    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-A")
        (root / "partial").write_text("preserve me")
        WorktreeCheckpointManager(
            root, "TASK-A", expected_branch="main", task_work_scope=scope
        ).create_checkpoint(1, False)
        lease.poison("Original execution failure")
    assert not git(root, "status", "--porcelain", "--untracked-files=no")
    with checkout_lease(root) as lease:
        lease.admit("TASK-B")
    assert (root / "partial").read_text() == "preserve me"


def test_an_unregistered_checkout_is_admitted(tmp_path):
    root = repository(tmp_path / "checkout")
    from guardkit.orchestrator import task_work_scope as m

    _, gd = m.identity(root)
    m._fresh.pop(str(gd))
    with checkout_lease(root) as lease:
        assert lease.admit("TASK-A").baseline_commit == git(root, "rev-parse", "HEAD")


def test_distinct_checkouts_overlap_and_sibling_serializes(tmp_path):
    a = repository(tmp_path / "a")
    b = repository(tmp_path / "b")
    barrier = threading.Barrier(2)

    def independent(root):
        with checkout_lease(root) as lease:
            lease.admit("TASK-" + root.name)
            barrier.wait(timeout=5)

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(independent, [a, b]))
    sibling = repository(tmp_path / "sibling")
    a, evidence = fresh_with_sibling(tmp_path / "source-a", sibling, "A")
    b, evidence_b = fresh_with_sibling(tmp_path / "source-b", sibling, "B")
    assert evidence == evidence_b
    order = []
    lock = threading.Lock()
    first = threading.Event()
    release = threading.Event()

    def shared(root):
        with checkout_lease(root, evidence) as lease:
            lease.admit("TASK-" + root.name)
            with lock:
                order.append("start-" + root.name)
            if root == a:
                first.set()
                assert release.wait(5)
            with lock:
                order.append("end-" + root.name)

    with ThreadPoolExecutor(2) as pool:
        fa = pool.submit(shared, a)
        assert first.wait(5)
        fb = pool.submit(shared, b)
        release.set()
        fa.result(5)
        fb.result(5)
    assert order == ["start-A", "end-A", "start-B", "end-B"]


def test_feature_check_reentry_and_a_mutation_does_not_refuse(tmp_path):
    root = repository(tmp_path / "checkout")
    feature = FeatureOrchestrator.__new__(FeatureOrchestrator)
    feature._evidence_repos_resolved = []
    worktree = SimpleNamespace(path=root)
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        assert (
            feature._checked_writer(worktree, lambda: "clean failed check")
            == "clean failed check"
        )

    def mutation():
        (root / "new").write_text("gate wrote this")
        git(root, "add", "new")
        git(root, "commit", "-m", "unexpected gate commit")

    # Step 2 (26 October 2026): logged and left, never a refusal.
    feature._checked_writer(worktree, mutation)
    assert (root / "new").read_text() == "gate wrote this"
    with checkout_lease(root) as lease:
        lease.admit("TASK-B")


def test_real_feature_task_entry_serializes_aliases(tmp_path):
    root = repository(tmp_path / "checkout")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    feature = FeatureOrchestrator.__new__(FeatureOrchestrator)
    feature._evidence_repos_resolved = []
    feature._update_task_started = lambda feature, task_id: None
    order = []

    def run(self, task, feature, worktree, **kwargs):
        assert kwargs["shares_working_copy"] is False
        invoker = AgentInvoker(worktree_path=worktree.path)
        scope = invoker.task_work_scope
        order.append((task.id, scope.baseline_commit))
        (worktree.path / task.id).write_text("authored\n")
        WorktreeCheckpointManager(
            worktree.path, task.id, expected_branch="main", task_work_scope=scope
        ).create_checkpoint(1, True)
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    feature._execute_task_owned = MethodType(run, feature)
    f = SimpleNamespace(id="FEAT-X")
    with ThreadPoolExecutor(2) as pool:
        futures = [
            pool.submit(
                feature._execute_task,
                SimpleNamespace(id=f"TASK-{i}"),
                f,
                SimpleNamespace(path=p),
            )
            for i, p in enumerate([root, alias])
        ]
        assert all(x.result(10).success for x in futures)
    assert order[0][1] != order[1][1]


def test_real_wave_dispatcher_invoker_audit_checkpoint(tmp_path):
    import asyncio
    from guardkit.orchestrator.feature_loader import (
        Feature,
        FeatureTask,
        FeatureOrchestration,
        FeatureExecution,
    )

    sys.path.insert(
        0, str(Path(__file__).resolve().parents[3] / "installer/core/commands")
    )
    from lib.plan_audit import PlanAuditor, DeclaredFiles

    controller = repository(tmp_path / "controller")
    from guardkit.worktrees import WorktreeManager

    manager = WorktreeManager(controller)
    physical = manager.create("FEAT-WAVE", "main")
    root = physical.path
    tasks = [
        FeatureTask(
            id=f"TASK-WAVE-{i}",
            name=f"task{i}",
            file_path=Path(f"tasks/TASK-WAVE-{i}.md"),
            complexity=1,
            dependencies=[],
            status="pending",
        )
        for i in range(2)
    ]
    feature = Feature(
        id="FEAT-WAVE",
        name="wave",
        description="wave",
        created="2026-10-24",
        status="planned",
        complexity=1,
        estimated_tasks=2,
        tasks=tasks,
        orchestration=FeatureOrchestration(parallel_groups=[[t.id for t in tasks]]),
        execution=FeatureExecution(),
    )
    runner = FeatureOrchestrator(
        repo_root=controller,
        worktree_manager=manager,
        quiet=True,
        enable_context=False,
        max_parallel=2,
        task_timeout=30,
    )
    observed = []

    def player_boundary(self, task, feature, worktree, **kwargs):
        invoker = AgentInvoker(worktree_path=worktree.path)
        scope = invoker.task_work_scope
        if kwargs.get("repair_round"):
            assert kwargs["repair_round"].start_commit == scope.baseline_commit
            assert scope.admission_reason == "gate repair"
        suffix = "-repair" if kwargs.get("repair_round") else ""
        target = f"{task.id}{suffix}.source"
        (root / target).write_text("authored by this task\n")
        extra = f"{task.id}{suffix}.unexpected-format"
        (root / extra).write_text("own undeclared source\n")
        audit = PlanAuditor(root, task_work_scope=scope).audit_implementation(
            task.id, declared=DeclaredFiles(to_create=[target], to_modify=[])
        )
        block = invoker._plan_audit_block_from_report(audit)
        assert extra in block["extra_files"]
        # A preceding task's committed paths cannot enter this task's inventory.
        assert invoker._detect_git_changes()["created"] == sorted([target, extra])
        checkpoint = WorktreeCheckpointManager(
            root, task.id, expected_branch=physical.branch_name, task_work_scope=scope
        ).create_checkpoint(1, True)
        observed.append((task.id, scope.baseline_commit, checkpoint.commit_hash))
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    runner._execute_task_owned = MethodType(player_boundary, runner)
    result = asyncio.run(
        runner._execute_wave_parallel(1, [t.id for t in tasks], feature, physical)
    )
    assert all(r.success for r in result), result
    assert observed[1][1] == observed[0][2]
    # Reopen both tasks together. The second repair's baseline must be
    # captured only after the first admitted repair checkpoint completes.
    repair_results = asyncio.run(
        runner._execute_wave_parallel(
            2,
            [t.id for t in tasks],
            feature,
            physical,
            seed_feedback="Gate failed; repair the requested source",
        )
    )
    assert all(r.success for r in repair_results), repair_results
    assert observed[2][1] == observed[1][2]
    assert observed[3][1] == observed[2][2]


def test_new_real_worktree_from_pin_is_reachable_but_old_work_is_preserved(tmp_path):
    from guardkit.worktrees import WorktreeManager

    source = repository(tmp_path / "source")
    pin = git(source, "rev-parse", "HEAD")
    manager = WorktreeManager(source)
    first = manager.create("FIRST", "main")
    with checkout_lease(first.path) as lease:
        lease.admit("TASK-FIRST")
        (first.path / "unfinished").write_text("do not discard")
        lease.poison("Original failed attempt")
    # This is the normal new-worktree constructor, using the same pinned ref.
    second = manager.create("SECOND", "main")
    assert git(second.path, "rev-parse", "HEAD") == pin
    with checkout_lease(second.path) as lease:
        scope = lease.admit("TASK-SECOND")
        assert scope.baseline_commit == pin
        assert collect_changes(scope)["created"] == []
    assert (first.path / "unfinished").read_text() == "do not discard"


def test_unbound_checkpoint_refuses_before_staging(tmp_path):
    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        head = git(root, "rev-parse", "HEAD")
        (root / "uncommitted").write_text("keep unstaged")
        with pytest.raises(ScopeUnavailable, match="admitted task scope"):
            WorktreeCheckpointManager(root, "TASK-A").create_checkpoint(1, True)
        assert git(root, "rev-parse", "HEAD") == head
        assert git(root, "diff", "--cached", "--name-only") == ""


def test_final_report_inventory_rejects_claimed_predecessor_and_preserves_odd_paths(
    tmp_path,
):

    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        invoker = AgentInvoker(worktree_path=root)
        (root / "odd source").write_text("own extensionless content")
        # Both report producers receive a plausible but unobserved claimed path.
        claimed = {"files_created": ["prior.py"], "files_modified": ["base"]}
        direct = json.loads(
            invoker._write_direct_mode_results("TASK-A", claimed).read_text()
        )
        assert direct["files_created"] == ["odd source"]
        assert direct["files_modified"] == []
        assert direct["claimed_files_created"] == ["prior.py"]
        output = SimpleNamespace(output={"files_created": ["peer.py"]})
        invoker._create_player_report_from_task_work("TASK-A", 1, output)
        from guardkit.orchestrator.paths import TaskArtifactPaths

        report = json.loads(
            TaskArtifactPaths.player_report_path("TASK-A", 1, root).read_text()
        )
        assert report["files_created"] == ["odd source"]
        assert "peer.py" in report["claimed_files_created"]
        assert report["scope_id"] == lease.scope.scope_id


def test_real_wave_timeout_keeps_child_and_worker_footprint_owned(
    tmp_path, monkeypatch
):
    import asyncio
    from guardkit.orchestrator.feature_loader import (
        Feature,
        FeatureTask,
        FeatureOrchestration,
        FeatureExecution,
    )
    from guardkit.worktrees import WorktreeManager
    from guardkit.orchestrator import task_work_scope as scope_module

    controller = repository(tmp_path / "controller")
    manager = WorktreeManager(controller)
    physical = manager.create("FEAT-TIMEOUT", "main")
    tasks = [
        FeatureTask(
            id=f"TASK-TIMEOUT-{i}",
            name=f"task{i}",
            file_path=Path(f"tasks/TASK-TIMEOUT-{i}.md"),
            complexity=1,
            dependencies=[],
            status="pending",
        )
        for i in range(2)
    ]
    feature = Feature(
        id="FEAT-TIMEOUT",
        name="timeout",
        description="timeout",
        created="2026-10-24",
        status="planned",
        complexity=1,
        estimated_tasks=2,
        tasks=tasks,
        orchestration=FeatureOrchestration(parallel_groups=[[t.id for t in tasks]]),
        execution=FeatureExecution(),
    )
    runner = FeatureOrchestrator(
        repo_root=controller,
        worktree_manager=manager,
        quiet=True,
        enable_context=False,
        max_parallel=2,
        task_timeout=1,
    )
    runner.task_timeout = 0.1
    monkeypatch.setattr(runner, "_resolve_task_timeout", lambda *a, **k: 0.1)
    child_started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    entered = []
    child = []

    def player_boundary(self, task, feature, worktree, **kwargs):
        entered.append(task.id)
        if len(entered) > 1:
            # The next task, admitted once the timed-out worker let go.
            return TaskExecutionResult(
                task_id=task.id, success=True, total_turns=1, final_decision="approved"
            )
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        child.append(proc)
        child_started.set()
        try:
            assert release.wait(10)
            (worktree.path / "after-timeout").write_text("late actual worker change")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            finished.set()
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    runner._execute_task_owned = MethodType(player_boundary, runner)

    async def run():
        wave = asyncio.ensure_future(runner._execute_wave_parallel(
            1, [t.id for t in tasks], feature, physical
        ))
        while not child_started.is_set():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.5)  # well past the first task's time limit
        assert child[0].poll() is None
        # Step 2 (26 October 2026): no fence refuses the next task; it waits
        # for the writer lock the timed-out worker still holds.
        assert len(entered) == 1
        _, gd = scope_module.identity(physical.path)
        assert scope_module._locks[str(gd)].locked()
        release.set()
        results = await wave
        assert finished.is_set()
        return results

    try:
        results = asyncio.run(run())
    finally:
        release.set()
        for proc in child:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
    assert (physical.path / "after-timeout").read_text() == "late actual worker change"
    assert len(entered) == 2
    decisions = {r.task_id: r.final_decision for r in results}
    assert decisions["TASK-TIMEOUT-0"] == "timeout"
    assert decisions["TASK-TIMEOUT-1"] == "approved"
    with checkout_lease(physical.path) as lease:
        lease.admit("TASK-NEXT")


def fresh_with_sibling(source, sibling, name, declared=None):
    import yaml
    from guardkit.worktrees import WorktreeManager
    from guardkit.orchestrator.task_work_scope import bind_fresh_footprint

    repository(source)
    record = source / ".guardkit/features/FEAT-BOUND.yaml"
    record.parent.mkdir(parents=True)
    raw = declared if declared is not None else [str(sibling)]
    record.write_text(yaml.safe_dump({"evidence_repos": raw}))
    git(source, "add", ".guardkit/features/FEAT-BOUND.yaml")
    git(source, "commit", "-m", "pinned declaration")
    worktree = WorktreeManager(source).create(name, "main")
    repos = bind_fresh_footprint(
        worktree.path, source, record, kind="feature", expected=raw
    )
    return worktree.path, repos


def test_feature_producer_selects_complete_pinned_inputs_before_setup(
    tmp_path, monkeypatch
):
    import yaml
    from guardkit.orchestrator.feature_loader import (
        Feature,
        FeatureOrchestration,
        FeatureExecution,
    )
    from guardkit.worktrees import WorktreeManager
    from guardkit.orchestrator.task_work_scope import current_lease, _selected, identity

    sibling = repository(tmp_path / "sibling")
    source = repository(tmp_path / "source")
    record = source / ".guardkit/features/FEAT-SIBLING.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({"evidence_repos": [str(sibling)]}))
    git(source, "add", ".")
    git(source, "commit", "-m", "pinned feature declaration")
    feature = Feature(
        id="FEAT-SIBLING",
        name="siblings",
        description="siblings",
        created="2026-10-24",
        status="planned",
        complexity=1,
        estimated_tasks=0,
        tasks=[],
        orchestration=FeatureOrchestration(parallel_groups=[]),
        execution=FeatureExecution(),
        evidence_repos=[str(sibling)],
        file_path=record,
    )
    runner = FeatureOrchestrator(
        repo_root=source,
        worktree_manager=WorktreeManager(source),
        quiet=True,
        enable_context=False,
    )
    seen = []

    def bootstrap(worktree, **kwargs):
        lease = current_lease(worktree.path)
        assert {r for _, r, _ in lease.repositories} == {worktree.path, sibling}
        assert lease.scope is not None
        seen.append("bootstrap")
        (worktree.path / "package-lock.json").write_text("fixture bootstrap output")

    sibling_start = git(sibling, "rev-parse", "HEAD")
    monkeypatch.setattr(runner, "_bootstrap_environment", bootstrap)
    _, worktree = runner._create_new_worktree(feature, feature.id, "main")
    assert seen == []
    monkeypatch.setattr(runner, "_update_task_started", lambda *args: None)

    def player(self, task, feature, worktree, **kwargs):
        seen.append("player")
        invoker = AgentInvoker(worktree_path=worktree.path)
        assert invoker._detect_git_changes()["created"] == ["package-lock.json"]
        WorktreeCheckpointManager(
            worktree.path,
            task.id,
            task_work_scope=invoker.task_work_scope,
            evidence_repos=self._evidence_repos_resolved,
        ).create_checkpoint(1, True)
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    runner._execute_task_owned = MethodType(player, runner)
    task_result = runner._execute_task(
        SimpleNamespace(id="TASK-SIBLING"), feature, worktree
    )
    assert task_result.success
    assert seen == ["bootstrap", "player"]
    selection = _selected[str(identity(worktree.path)[1])]
    assert selection["inputs"][str(sibling)] == sibling_start
    assert selection["provenance"] == "selected starting inputs; not approval"
    with checkout_lease(worktree.path, runner._evidence_repos_resolved) as lease:
        scope = lease.admit("TASK-SIBLING", feature.id)
        assert scope.source_declaration
        assert scope.build_id


def test_standalone_producer_reads_original_task_blob_and_scopes_reports(tmp_path):
    import yaml
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
    from guardkit.worktrees import WorktreeManager
    from guardkit.orchestrator.task_work_scope import current_lease

    sibling = repository(tmp_path / "sibling")
    source = repository(tmp_path / "source")
    task = source / "tasks/backlog/TASK-SIBLING.md"
    task.parent.mkdir(parents=True)
    task.write_text(
        "---\n"
        + yaml.safe_dump({"id": "TASK-SIBLING", "evidence_repos": [str(sibling)]})
        + "---\nTask\n"
    )
    git(source, "add", ".")
    git(source, "commit", "-m", "pinned task declaration")
    runner = AutoBuildOrchestrator(
        repo_root=source,
        worktree_manager=WorktreeManager(source),
        enable_context=False,
        enable_pre_loop=False,
    )

    def player(self, *args, **kwargs):
        lease = current_lease()
        root = Path(lease.scope.repositories[0].root)
        invoker = AgentInvoker(worktree_path=root, evidence_repos=self._evidence_repos)
        (sibling / "sibling-extensionless").write_text("own sibling work")
        observed = invoker._detect_git_changes()
        assert observed["created"] == ["sibling:sibling-extensionless"]
        WorktreeCheckpointManager(
            root,
            "TASK-SIBLING",
            task_work_scope=lease.scope,
            evidence_repos=self._evidence_repos,
        ).create_checkpoint(1, True)
        return SimpleNamespace(final_decision="approved")

    runner._orchestrate_owned = MethodType(player, runner)
    assert (
        runner.orchestrate(
            "TASK-SIBLING", "requirement", [], task_file_path=task
        ).final_decision
        == "approved"
    )
    assert (sibling / "sibling-extensionless").exists()


def _sibling_case(tmp_path, bad):
    import yaml
    from guardkit.worktrees import WorktreeManager

    sibling = repository(tmp_path / "sibling")
    source = repository(tmp_path / "source")
    raw = [str(sibling)]
    if bad == "missing":
        raw.append(str(tmp_path / "missing"))
    if bad == "malformed":
        raw.append({"wrong": "path"})
    record = source / ".guardkit/features/FEAT-BAD.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({"evidence_repos": raw}))
    if bad != "missing_source":
        git(source, "add", ".")
        git(source, "commit", "-m", "pinned feature declaration")
    wt = WorktreeManager(source).create("BAD", "main")
    if bad == "dirty":
        (sibling / "preserved").write_text("unapproved input")
    if bad == "failed":
        with checkout_lease(sibling) as lease:
            lease.poison("known failed predecessor")
    expected = raw + ["../different"] if bad == "changed_declaration" else raw
    return sibling, source, record, wt, expected


@pytest.mark.parametrize("bad", ["dirty", "failed", "changed_declaration", "missing_source"])
def test_sibling_selection_admits_what_earlier_work_or_bookkeeping_left(tmp_path, bad):
    """Step 2 (26 October 2026): a sibling with earlier or failed work, a
    loaded declaration that differs from the committed one, or a declaration
    that is not committed yet, no longer refuses the writer."""
    from guardkit.orchestrator.task_work_scope import bind_fresh_footprint

    sibling, source, record, wt, expected = _sibling_case(tmp_path, bad)
    repos = bind_fresh_footprint(
        wt.path, source, record, kind="feature", expected=expected
    )
    assert [Path(r.root).resolve() for r in repos] == [sibling.resolve()]
    with checkout_lease(wt.path, repos) as lease:
        lease.admit("TASK-A")
    if bad == "dirty":
        assert (sibling / "preserved").read_text() == "unapproved input"


def test_original_failed_task_result_survives_ownership_teardown(tmp_path):
    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    runner._update_task_started = lambda *args: None
    original = TaskExecutionResult(
        task_id="TASK-FAIL",
        success=False,
        total_turns=1,
        final_decision="error",
        error="RequiredReadError: missing declared prerequisite",
    )
    runner._execute_task_owned = lambda *args, **kwargs: original
    result = runner._execute_task(
        SimpleNamespace(id="TASK-FAIL"),
        SimpleNamespace(id="FEAT-X"),
        SimpleNamespace(path=root),
    )
    assert result is original
    assert result.error == "RequiredReadError: missing declared prerequisite"
    with checkout_lease(root) as lease:  # the next writer is admitted (step 2)
        lease.admit("TASK-NEXT")


def test_checkpoint_rollback_and_history_stay_in_the_admitted_scope(tmp_path):
    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-A")
        (root / "base").write_text("continuation edits")
        checkpoint = WorktreeCheckpointManager(root, "TASK-A", task_work_scope=scope)
        checkpoint.create_checkpoint(1, True)
        (root / "later").write_text("later checkpoint")
        second = checkpoint.create_checkpoint(2, False)
        assert checkpoint.rollback_to(1)
        assert not (root / "later").exists()
        from guardkit.orchestrator.paths import TaskArtifactPaths

        private = TaskArtifactPaths.private_artifact_path(
            "TASK-A", "unused", root
        ).parent
        histories = list(private.glob("checkpoint-history-*.json"))
        assert histories
        history = json.loads(histories[0].read_text())
        assert history["scope_id"] == scope.scope_id
        assert history["checkpoints"][-1]["commit_hash"] == second.commit_hash


def test_feature_check_and_task_share_the_complete_sibling_lease(tmp_path):

    sibling = repository(tmp_path / "sibling")
    a, repos = fresh_with_sibling(tmp_path / "source-a", sibling, "GATE")
    b, other = fresh_with_sibling(tmp_path / "source-b", sibling, "TASK")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = repos
    with checkout_lease(a, repos) as lease:
        lease.admit("TASK-REPAIR")
    started = threading.Event()
    release = threading.Event()
    task_entered = threading.Event()

    def gate():
        started.set()
        assert release.wait(5)
        return "clean failed gate"

    def task():
        with checkout_lease(b, other) as lease:
            lease.admit("TASK-OTHER")
            task_entered.set()

    with ThreadPoolExecutor(2) as pool:
        check = pool.submit(runner._checked_writer, SimpleNamespace(path=a), gate)
        assert started.wait(5)
        work = pool.submit(task)
        assert not task_entered.wait(0.1)
        release.set()
        assert check.result(5) == "clean failed gate"
        work.result(5)
    with checkout_lease(a, repos) as lease:
        assert (
            lease.admit("TASK-REPAIR", round_id="2").admission_reason == "gate repair"
        )


def test_uncertain_gate_child_preserves_unavailable_footprint(tmp_path):
    from guardkit.orchestrator.process_group import CleanupUnavailableError

    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    child = []

    def gate():
        child.append(
            subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        )
        raise CleanupUnavailableError("fixture cannot establish child shutdown")

    try:
        with pytest.raises(CleanupUnavailableError):
            runner._checked_writer(SimpleNamespace(path=root), gate)
        assert child[0].poll() is None
        # Step 2 (26 October 2026): the gate's own failure is raised to its
        # caller; it never refuses the next writer.
        with checkout_lease(root) as lease:
            lease.admit("TASK-NEXT")
    finally:
        for proc in child:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)


def test_real_feature_command_timeout_ends_child_before_releasing_gate(tmp_path):
    import shlex
    from guardkit.orchestrator.feature_check import run_feature_check_command

    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    code = "import time; time.sleep(30)"
    result = runner._checked_writer(
        SimpleNamespace(path=root),
        run_feature_check_command,
        shlex.quote(sys.executable) + " -c " + shlex.quote(code),
        cwd=root,
        timeout=0.1,
    )
    assert result["timed_out"] is True
    # The real process-group runner establishes termination, so a clean
    # failure can reach the existing repair/new-task path.
    with checkout_lease(root) as lease:
        lease.admit("TASK-AFTER-CLEAN-GATE")


def test_bootstrap_runs_once_per_wave_under_contention_before_player(tmp_path):
    from guardkit.orchestrator.task_work_scope import current_lease

    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    runner._update_task_started = lambda *args: None
    runner._bootstrap_pending = True
    runner._baseline_probe_pending = True
    events = []
    observed = []
    bootstraps = []

    def bootstrap(worktree, **kwargs):
        scope = current_lease().scope
        bootstraps.append(scope.scope_id)
        events.append("bootstrap")
        (root / "generated.project-lock").write_text(str(len(bootstraps)))

    runner._bootstrap_environment = bootstrap

    def player(self, task, feature, worktree, **kwargs):
        invoker = AgentInvoker(worktree_path=root)
        scope = invoker.task_work_scope
        events.append("player")
        observed.append((scope.scope_id, invoker._detect_git_changes()))
        WorktreeCheckpointManager(
            root, task.id, task_work_scope=scope
        ).create_checkpoint(1, True)
        return TaskExecutionResult(
            task_id=task.id, success=True, total_turns=1, final_decision="approved"
        )

    runner._execute_task_owned = MethodType(player, runner)
    for wave in range(2):
        runner._bootstrap_pending = True
        with ThreadPoolExecutor(2) as pool:
            futures = [
                pool.submit(
                    runner._execute_task,
                    SimpleNamespace(id=f"TASK-{wave}-{i}"),
                    SimpleNamespace(id="FEAT-X"),
                    SimpleNamespace(path=root),
                )
                for i in range(2)
            ]
            assert all(f.result(10).success for f in futures)
    assert events == [
        "bootstrap",
        "player",
        "player",
        "bootstrap",
        "player",
        "player",
    ]
    assert len(bootstraps) == 2
    assert observed[0][1]["created"] == ["generated.project-lock"]
    assert observed[1][1]["created"] == []
    assert observed[2][1]["modified"] == ["generated.project-lock"]
    assert observed[3][1]["modified"] == []


def test_bootstrap_exception_preserves_original_type_and_partial_work(tmp_path):
    class BootstrapPrerequisiteError(RuntimeError):
        pass

    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    runner._bootstrap_pending = True

    def failed(worktree, **kwargs):
        (root / "partial-bootstrap.lock").write_text("preserve generated input")
        raise BootstrapPrerequisiteError("declared installer unavailable")

    runner._bootstrap_environment = failed
    with pytest.raises(BootstrapPrerequisiteError) as caught:
        runner._execute_task(
            SimpleNamespace(id="TASK-A"),
            SimpleNamespace(id="FEAT-X"),
            SimpleNamespace(path=root),
        )
    result = runner._create_error_result("TASK-A", caught.value)
    assert result.error_type == "BootstrapPrerequisiteError"
    assert result.error == "declared installer unavailable"
    assert (root / "partial-bootstrap.lock").read_text() == "preserve generated input"
    with checkout_lease(root) as lease:  # the next writer starts from it (step 2)
        lease.admit("TASK-NEXT")


def test_same_owner_resume_keeps_live_history_and_ignores_saved_authority(tmp_path):
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-A")
        invoker = AgentInvoker(worktree_path=root)
        runner = AutoBuildOrchestrator(
            repo_root=root,
            agent_invoker=invoker,
            enable_context=False,
            enable_pre_loop=False,
        )
        runner.task_work_scope = scope
        runner._turn_history = []
        worktree, start_turn = runner._resume_from_state(
            "TASK-A", tmp_path / "nonexistent-saved-file"
        )
        assert worktree.path == root
        assert worktree.base_branch == scope.baseline_commit
        assert start_turn == 1
        assert runner.task_work_scope is scope


def test_cancelled_waiter_cannot_start_after_the_owner_exits(tmp_path):
    root = repository(tmp_path / "checkout")
    runner = FeatureOrchestrator.__new__(FeatureOrchestrator)
    runner._evidence_repos_resolved = []
    runner._execute_task_owned = lambda *args, **kwargs: pytest.fail(
        "Cancelled queued Player started"
    )
    acquired = threading.Event()
    release = threading.Event()
    cancelled = threading.Event()

    def owner():
        with checkout_lease(root) as lease:
            lease.admit("TASK-OWNER")
            acquired.set()
            assert release.wait(5)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(owner)
        assert acquired.wait(5)
        waiting = pool.submit(
            runner._execute_task,
            SimpleNamespace(id="TASK-WAIT"),
            SimpleNamespace(id="FEAT-X"),
            SimpleNamespace(path=root),
            cancellation_event=cancelled,
        )
        cancelled.set()
        try:
            result = waiting.result(2)
            assert not result.success
            assert "cancelled" in result.error.lower()
        finally:
            release.set()
            first.result(5)


def _forget_this_process(root):
    """What a new process (a resumed build) knows: nothing in memory."""
    from guardkit.orchestrator import task_work_scope as m

    _, gd = m.identity(root)
    for registry in (m._fresh, m._selected, m._bindings, m._approved_heads):
        registry.pop(str(gd), None)


def test_a_resumed_task_tests_the_parts_changed_in_every_turn(tmp_path):
    """Turn 1 changes part A and is checkpointed; the build is resumed and
    the next turn changes only part B. The resumed admission keeps the
    task's first starting commit, so part A is still tested (1 November
    2026: the resume used to start from the HEAD it found)."""
    from guardkit.orchestrator.toolchain_declaration import (
        parse_toolchain_block,
        parts_for_files,
    )

    root = repository(tmp_path / "checkout")
    start = git(root, "rev-parse", "HEAD")
    declaration = parse_toolchain_block({
        "components": {
            "a": {"cwd": "a", "test": "true"},
            "b": {"cwd": "b", "test": "true"},
        }
    })
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-RESUME")
        assert scope.baseline_commit == start
        (root / "a").mkdir()
        (root / "a" / "one.txt").write_text("turn 1\n")
        WorktreeCheckpointManager(
            root, "TASK-RESUME", expected_branch="main", task_work_scope=scope
        ).create_checkpoint(1, None)
        lease.poison("the process stopped mid-task")
    assert git(root, "rev-parse", "HEAD") != start

    _forget_this_process(root)
    with checkout_lease(root) as lease:
        resumed = lease.admit("TASK-RESUME")
        assert resumed.baseline_commit == start
        assert resumed.admission_reason == "resumed"
        (root / "b").mkdir()
        (root / "b" / "two.txt").write_text("turn 2\n")
        changes = collect_changes(resumed)
    files = changes["created"] + changes["modified"]
    assert [p.name for p in parts_for_files(declaration, root, files)] == ["a", "b"]


def test_a_resume_with_only_a_checkpoint_starts_from_its_parent(tmp_path):
    """No scope record (an older run): the parent of the task's first
    checkpoint is its starting commit."""
    from guardkit.orchestrator.paths import TaskArtifactPaths

    root = repository(tmp_path / "checkout")
    start = git(root, "rev-parse", "HEAD")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-OLD")
        (root / "work.txt").write_text("turn 1\n")
        WorktreeCheckpointManager(
            root, "TASK-OLD", expected_branch="main", task_work_scope=scope
        ).create_checkpoint(1, None)
    for record in TaskArtifactPaths.task_private_dir("TASK-OLD", root).glob("scope-*.json"):
        record.unlink()

    _forget_this_process(root)
    with checkout_lease(root) as lease:
        assert lease.admit("TASK-OLD").baseline_commit == start


def test_a_repair_round_starts_from_where_it_is_admitted(tmp_path):
    """A recorded starting commit belongs to its own round: a repair round
    is admitted at the HEAD it finds."""
    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        scope = lease.admit("TASK-R")
        (root / "work.txt").write_text("turn 1\n")
        WorktreeCheckpointManager(
            root, "TASK-R", expected_branch="main", task_work_scope=scope
        ).create_checkpoint(1, None)
    head = git(root, "rev-parse", "HEAD")
    with checkout_lease(root) as lease:
        assert lease.admit("TASK-R", round_id="2").baseline_commit == head
