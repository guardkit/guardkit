"""Repair 7: record what a declared command actually ran against.

These pin the recording module on its own, with real git and real files but
fake Docker:

* the source identity covers untracked files (changing only an untracked
  file's bytes changes it) and leaves ignored files out;
* a write during the command is recorded as "source changed during the
  command", and a quiet command as "source unchanged between start and end";
* a plain directory (an isolated copy has no .git) covers every file it
  holds; symbolic links are recorded with their target, never followed;
* the originating worktree's identity is taken through a temporary index and
  never writes the real one;
* a declared environment inventory is saved with a hash, an undeclared one
  says "not declared";
* container events are kept only from the command's own interval, capped,
  and a missing Docker tool is "not available", never "no events";
* bounds and capture failures are recorded, never raised.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator import run_evidence as re_mod
from guardkit.orchestrator.run_evidence import (
    NOT_AVAILABLE,
    NOT_DECLARED,
    NOT_LOOKED_UP,
    NOT_RECORDED_TOO_LARGE,
    SOURCE_CHANGED,
    SOURCE_UNCHANGED,
    CommandEvidence,
    DockerProbe,
    EvidenceLimits,
    EvidenceRequest,
    HelperRun,
    docker_events_between,
    originating_worktree_identity,
    request_from_declaration,
    request_from_repo,
    run_environment_inventory,
    source_manifest,
    start_command_evidence,
)
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / ".gitignore").write_text("ignored/\n")
    (root / "app.txt").write_text("tracked\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    (root / "notes.txt").write_text("untracked one\n")
    (root / "ignored").mkdir()
    (root / "ignored" / "env.txt").write_text("installed things\n")
    return root


def _no_docker() -> DockerProbe:
    return DockerProbe(runner=_boom_runner, which=lambda _name: None)


def _boom_runner(*_a, **_k):  # pragma: no cover - must never be called
    raise AssertionError("docker must not be called when it is not on PATH")


# ---------------------------------------------------------------------------
# 1. Source identity
# ---------------------------------------------------------------------------


def test_changing_only_an_untracked_file_changes_the_identity(repo):
    first = source_manifest(repo)
    (repo / "notes.txt").write_text("untracked two\n")
    second = source_manifest(repo)

    assert first["status"] == "recorded" and second["status"] == "recorded"
    paths = [e[0] for e in first["_entries"]]
    assert "notes.txt" in paths and "app.txt" in paths
    assert first["digest"] != second["digest"]
    assert first["head"] == _git(repo, "rev-parse", "HEAD").strip()


def test_ignored_files_are_left_out_of_a_git_worktree(repo):
    first = source_manifest(repo)
    (repo / "ignored" / "env.txt").write_text("a different install\n")
    second = source_manifest(repo)

    assert not any(e[0].startswith("ignored/") for e in first["_entries"])
    assert first["digest"] == second["digest"]


def test_a_write_during_the_command_is_recorded_as_changed(repo):
    evidence = CommandEvidence(
        EvidenceRequest(kind="test"), command="x", execution_root=repo, docker=_no_docker()
    ).begin()
    (repo / "notes.txt").write_text("written while the command ran\n")
    (repo / "new.txt").write_text("new\n")
    record = evidence.finish()

    assert record["source"]["verdict"] == SOURCE_CHANGED
    changed = record["source"]["changed_paths"]
    assert changed["modified"] == ["notes.txt"]
    assert record["source"]["files_created_during_the_command"]["paths"] == ["new.txt"]
    assert "continuous" not in record["source"]["verdict"]
    assert "do not show what the bytes were" in record["source"]["what_this_shows"]
    json.dumps(record)  # the record is plain JSON


def test_a_quiet_command_is_recorded_as_unchanged(repo):
    evidence = CommandEvidence(
        EvidenceRequest(kind="test"), command="x", execution_root=repo, docker=_no_docker()
    ).begin()
    record = evidence.finish()

    assert record["source"]["verdict"] == SOURCE_UNCHANGED
    assert record["source"]["changed_paths"] is None
    manifest = record["source"]["manifest"]
    assert manifest["entries_total"] == record["source"]["before"]["file_count"]
    assert "_entries" not in record["source"]["before"]


def test_a_plain_directory_covers_every_file_and_records_links_unfollowed(tmp_path):
    root = tmp_path / "copy"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "a.py").write_bytes(b"print(1)\n")
    target_dir = tmp_path / "elsewhere"
    target_dir.mkdir()
    (target_dir / "big.bin").write_bytes(b"x" * 10)
    os.symlink(str(target_dir), str(root / ".venv"))
    os.symlink("pkg/a.py", str(root / "link.py"))

    record = source_manifest(root)

    assert record["status"] == "recorded"
    assert "plain directory" in record["file_set"]
    entries = {e[0]: e for e in record["_entries"]}
    assert entries["pkg/a.py"][2] == hashlib.sha256(b"print(1)\n").hexdigest()
    assert entries[".venv"] == [".venv", "symlink", str(target_dir)]
    assert entries["link.py"] == ["link.py", "symlink", "pkg/a.py"]
    assert not any(p.startswith(".venv/") for p in entries)


def test_too_large_is_recorded_not_raised(repo):
    record = source_manifest(repo, limits=EvidenceLimits(max_files=1))
    assert record["status"] == NOT_RECORDED_TOO_LARGE
    assert "more than 1 files" in record["limit_reached"]

    record = source_manifest(repo, limits=EvidenceLimits(max_bytes=3))
    assert record["status"] == NOT_RECORDED_TOO_LARGE


def test_a_capture_failure_is_recorded_not_raised(repo):
    def _broken(*_a, **_k):
        raise OSError("git vanished")

    record = source_manifest(repo, runner=_broken)
    assert record["status"].startswith("not recorded: capture error")

    evidence = CommandEvidence(
        EvidenceRequest(kind="test"),
        command="x",
        execution_root=repo,
        runner=_broken,
        docker=_no_docker(),
    ).begin()
    out = evidence.finish()
    assert out["source"]["verdict"].startswith("not compared")


def test_start_command_evidence_never_raises():
    evidence = start_command_evidence(None, command="x", execution_root=None)
    record = evidence.finish()
    assert record["capture_errors"]


# ---------------------------------------------------------------------------
# The originating worktree's identity
# ---------------------------------------------------------------------------


def test_origin_identity_covers_untracked_files_and_never_writes_the_real_index(repo):
    index = repo / ".git" / "index"
    before_bytes = index.read_bytes()
    before_mtime = index.stat().st_mtime_ns

    first = originating_worktree_identity(repo)
    (repo / "notes.txt").write_text("untracked changed\n")
    second = originating_worktree_identity(repo)

    assert first["status"] == "recorded"
    assert first["head"] == _git(repo, "rev-parse", "HEAD").strip()
    assert first["tree_with_untracked"] != second["tree_with_untracked"]
    # The untracked file is in the tree; the ignored one is not.
    listing = _git(repo, "ls-tree", "-r", "--name-only", first["tree_with_untracked"])
    assert "notes.txt" in listing.split()
    assert "ignored/env.txt" not in listing.split()
    # The real index is untouched and the file is still untracked.
    assert index.read_bytes() == before_bytes
    assert index.stat().st_mtime_ns == before_mtime
    assert "?? notes.txt" in _git(repo, "status", "--porcelain")


def test_origin_identity_of_a_plain_directory_says_so(tmp_path):
    record = originating_worktree_identity(tmp_path)
    assert record["status"].startswith("not recorded")


# ---------------------------------------------------------------------------
# 2. Environment inventory
# ---------------------------------------------------------------------------


def test_declared_inventory_is_saved_with_its_hash(tmp_path):
    request = EvidenceRequest(kind="t", environment_inventory="printf 'pkg==1.0\\n'")
    record = run_environment_inventory(request, cwd=tmp_path, env=None)

    assert record["status"] == "recorded"
    assert record["output"] == "pkg==1.0\n"
    assert record["output_sha256"] == hashlib.sha256(b"pkg==1.0\n").hexdigest()
    assert record["exit_code"] == 0


def test_inventory_output_is_capped_but_hashed_whole(tmp_path):
    request = EvidenceRequest(kind="t", environment_inventory="printf 'abcdefghij'")
    record = run_environment_inventory(
        request, cwd=tmp_path, env=None, limits=EvidenceLimits(inventory_output_bytes=4)
    )
    assert record["output"] == "abcd" and record["output_truncated"] is True
    assert record["output_sha256"] == hashlib.sha256(b"abcdefghij").hexdigest()


def test_undeclared_inventory_says_not_declared(tmp_path):
    assert run_environment_inventory(
        EvidenceRequest(kind="t"), cwd=tmp_path, env=None
    ) == {"status": NOT_DECLARED}
    assert run_environment_inventory(
        EvidenceRequest(kind="t", inventory_looked_up=False), cwd=tmp_path, env=None
    ) == {"status": NOT_LOOKED_UP}


def test_inventory_is_read_from_the_declaration(tmp_path):
    decl = parse_toolchain_block(
        {"test": "make test", "environment_inventory": "pip list", "environment_inventory_timeout": 30}
    )
    request = request_from_declaration("suite", decl, task="TASK-1", turn=2)
    assert request.environment_inventory == "pip list"
    assert request.inventory_timeout == 30
    assert request.observer == {"task": "TASK-1", "turn": 2}

    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text(
        "toolchain:\n  environment_inventory: 'npm ls --all'\n"
    )
    assert request_from_repo("probe", tmp_path).environment_inventory == "npm ls --all"
    assert request_from_repo("probe", tmp_path / "nowhere").environment_inventory is None


def test_a_component_inventory_wins_over_the_root(tmp_path):
    decl = parse_toolchain_block(
        {
            "environment_inventory": "root-inventory",
            "components": {"app": {"cwd": "app", "environment_inventory": "app-inventory"}},
        }
    )
    request = request_from_declaration("suite", decl, component=decl.component("app"))
    assert request.environment_inventory == "app-inventory"


def test_inventory_runs_before_the_first_source_observation(repo):
    request = EvidenceRequest(
        kind="t", environment_inventory="printf x > inventory-side-effect.txt"
    )
    record = CommandEvidence(
        request, command="x", execution_root=repo, docker=_no_docker()
    ).begin().finish()
    # The inventory's own write lands before the "before" observation, so it
    # is not reported as a change made during the command.
    assert record["source"]["verdict"] == SOURCE_UNCHANGED
    assert record["environment_inventory"]["status"] == "recorded"


# ---------------------------------------------------------------------------
# 3. Container events
# ---------------------------------------------------------------------------


def _event(kind: str, action: str, seconds: float, cid: str = "c1") -> dict:
    return {
        "Type": kind,
        "Action": action,
        "Actor": {"ID": cid, "Attributes": {"name": f"n-{cid}"}},
        "time": int(seconds),
        "timeNano": int(seconds * 1_000_000_000),
    }


def _fake_docker(events, calls=None, returncode=0, stderr=b""):
    def _runner(argv, **kwargs):
        if calls is not None:
            calls.append(list(argv))
        payload = "\n".join(json.dumps(e) for e in events).encode()
        return HelperRun(returncode, payload, stderr)

    return DockerProbe(runner=_runner, which=lambda _n: "/usr/bin/docker")


def test_events_are_kept_only_from_the_command_interval():
    calls: list = []
    probe = _fake_docker(
        [
            _event("container", "create", 99.5, "before"),
            _event("container", "destroy", 100.5, "inside"),
            _event("network", "disconnect", 101.0, "net"),
            _event("image", "pull", 100.6, "img"),
            _event("container", "destroy", 102.1, "after"),
        ],
        calls,
    )
    record = docker_events_between(100.0, 101.5, probe=probe)

    assert record["status"] == "recorded"
    kept = [e["Actor"]["ID"] for e in record["events"]]
    assert kept == ["inside", "net"]
    assert record["events_in_interval"] == 2
    argv = calls[0]
    assert argv[:2] == ["docker", "events"]
    assert argv[argv.index("--since") + 1] == "100.000000"
    assert argv[argv.index("--until") + 1] == "101.500000"
    assert "type=container" in argv and "type=network" in argv
    assert "attributed" not in json.dumps(record).replace("not attributed", "")
    assert "nothing here says which command" in record["what_this_shows"]


def test_events_are_capped_by_count_and_size():
    many = [_event("container", "start", 100.0 + i / 1000, f"c{i}") for i in range(50)]
    record = docker_events_between(
        99.0, 200.0, probe=_fake_docker(many), limits=EvidenceLimits(docker_events=5)
    )
    assert record["events_kept"] == 5
    assert record["events_in_interval"] == 50
    assert record["truncated"] is True

    record = docker_events_between(
        99.0, 200.0, probe=_fake_docker(many), limits=EvidenceLimits(docker_bytes=300)
    )
    assert 0 < record["events_kept"] < 50 and record["truncated"] is True


def test_missing_docker_is_not_available_never_no_events():
    record = docker_events_between(1.0, 2.0, probe=_no_docker())
    assert record["status"] == NOT_AVAILABLE
    assert "events" not in record


def test_an_unreachable_daemon_is_not_available():
    probe = _fake_docker([], returncode=1, stderr=b"Cannot connect to the Docker daemon")
    record = docker_events_between(1.0, 2.0, probe=probe)
    assert record["status"] == NOT_AVAILABLE
    assert "Cannot connect" in record["reason"]


def test_the_switch_turns_the_query_off(monkeypatch):
    monkeypatch.setenv(re_mod.DOCKER_SWITCH_ENV, "0")
    record = docker_events_between(1.0, 2.0)
    assert record["status"].startswith("not recorded: switched off")


def test_a_command_record_carries_the_observer_and_its_events(repo, monkeypatch):
    monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-A")
    clock_values = iter([10.0, 10.5, 11.0, 11.5, 12.0, 12.5])

    def _clock():
        return next(clock_values)

    probe = _fake_docker(
        [_event("container", "destroy", 10.7, "during"), _event("container", "destroy", 13.0, "later")]
    )
    record = CommandEvidence(
        EvidenceRequest(kind="independent suite", observer={"task": "TASK-1", "turn": 3}),
        command="pytest -q",
        execution_root=repo,
        docker=probe,
        clock=_clock,
    ).begin().finish()

    assert record["observer"] == {"build": "build-A", "task": "TASK-1", "turn": 3}
    assert [e["Actor"]["ID"] for e in record["container_events"]["events"]] == ["during"]
    assert record["interval"]["started_unix"] < record["interval"]["ended_unix"]


# ---------------------------------------------------------------------------
# Fix pass (independent coach, 12 October 2026)
# ---------------------------------------------------------------------------


def test_a_helper_limit_holds_even_when_a_setsid_child_keeps_the_pipes(tmp_path):
    import time as _time

    request = EvidenceRequest(
        kind="t", environment_inventory="setsid sleep 12 & sleep 60", inventory_timeout=1
    )
    started = _time.monotonic()
    record = run_environment_inventory(request, cwd=tmp_path, env=None)
    elapsed = _time.monotonic() - started

    assert record["status"] == "not recorded: timed out after 1s"
    assert elapsed < 10, f"the 1s limit took {elapsed:.1f}s"


def test_files_made_by_the_command_do_not_change_the_verdict_on_either_root_kind(repo, tmp_path):
    plain = tmp_path / "copy"
    plain.mkdir()
    (plain / "app.txt").write_text("source\n")
    for root in (repo, plain):
        evidence = CommandEvidence(
            EvidenceRequest(kind="t"), command="x", execution_root=root, docker=_no_docker()
        ).begin()
        (root / "made-by-run.txt").write_text("cache\n")
        record = evidence.finish()
        assert record["source"]["verdict"] == (
            f"{SOURCE_UNCHANGED}; 1 files created during the command"
        ), root
        assert record["source"]["files_created_during_the_command"]["paths"] == ["made-by-run.txt"]
        assert record["source"]["after"]["digest"] != record["source"]["before"]["digest"]


@pytest.mark.parametrize("change", ["contents", "mode", "link target", "removed"])
def test_a_change_to_a_file_that_existed_before_is_source_changed(tmp_path, change):
    root = tmp_path / "copy"
    root.mkdir()
    (root / "a.txt").write_text("a\n")
    os.symlink("a.txt", str(root / "link"))
    evidence = CommandEvidence(
        EvidenceRequest(kind="t"), command="x", execution_root=root, docker=_no_docker()
    ).begin()
    if change == "contents":
        (root / "a.txt").write_text("b\n")
    elif change == "mode":
        os.chmod(root / "a.txt", 0o700)
    elif change == "link target":
        os.unlink(root / "link")
        os.symlink("elsewhere", str(root / "link"))
    else:
        os.unlink(root / "a.txt")
    record = evidence.finish()
    assert record["source"]["verdict"] == SOURCE_CHANGED


def test_a_component_uses_only_its_own_inventory():
    decl = parse_toolchain_block(
        {"environment_inventory": "root-inventory", "components": {"app": {"cwd": "app"}}}
    )
    request = request_from_declaration(
        "suite", decl, component=decl.component("app"), component_name="app"
    )
    assert request.environment_inventory is None
    assert run_environment_inventory(request, cwd=".", env=None) == {
        "status": "not declared for component app"
    }


def test_a_git_listing_that_times_out_is_recorded_as_timed_out(repo):
    def _slow_git(argv, **kwargs):
        return HelperRun(None, b"", b"", timed_out=True)

    record = source_manifest(repo, runner=_slow_git)
    assert record["status"] == re_mod.NOT_RECORDED_TIMED_OUT
    assert "took longer than" in record["limit_reached"]
