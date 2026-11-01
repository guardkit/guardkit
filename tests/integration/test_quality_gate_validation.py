"""
Integration tests for quality gate validation using FEAT-CODE-TEST.

This test suite validates that GuardKit's quality gates work correctly for
actual code implementation tasks (not scaffolding). It uses FEAT-CODE-TEST
which implements a calculator service with SOLID principles.

Test Coverage:
- The FEAT-CODE-TEST fixture exists and loads through the real FeatureLoader
- AutoBuild creates the feature's shared worktree
- The quality gate testing documentation exists

The tests that asserted the Coach report's per-gate record (tests, coverage,
architecture review, plan audit) were removed with that record on 27 October
2026 (628d22ac): the reviewer's verdict is advice and only the project's own
failing checks send a turn back.
"""

import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Dict, Any
import pytest


# =============================================================================
# RUN GUARDS
# =============================================================================
#
# test_autobuild_creates_worktree SHELLS OUT to a real AutoBuild run and then
# asserts on what it produced. It needs nothing beyond this interpreter: the
# shared worktree is created in AutoBuild's setup phase, before any model is
# invoked, so it runs seatless (the model endpoint deliberately unreachable)
# and is NOT guarded.
#
# History worth keeping: before 2026-08-14 it failed for a reason that had
# nothing to do with seats. The checked-in fixture had drifted from the schema
# FeatureLoader reads (`feature_id` instead of `id`, task `file` instead of
# `file_path`, a `status` value outside the allowed set, no `orchestration`
# block, and no `task_type` in the task file's frontmatter), so every run died
# at parse time. The fixture was repaired instead of guarding the failure.


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def test_features_dir() -> Path:
    """Get path to test features directory."""
    return Path(__file__).parent / "test_features"


@pytest.fixture
def feat_code_test_dir(test_features_dir: Path) -> Path:
    """Get path to FEAT-CODE-TEST directory."""
    return test_features_dir / "FEAT-CODE-TEST"


@pytest.fixture
def temp_test_repo(tmp_path: Path, feat_code_test_dir: Path) -> Path:
    """
    Create a temporary test repository with FEAT-CODE-TEST.

    This fixture:
    1. Creates a fresh git repository
    2. Copies FEAT-CODE-TEST files
    3. Creates .guardkit/features/ directory
    4. Returns path to temporary repo

    Cleanup happens automatically via tmp_path.
    """
    # Create repository structure
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    # Create .guardkit/features directory
    features_dir = repo_dir / ".guardkit" / "features"
    features_dir.mkdir(parents=True)

    # Copy FEAT-CODE-TEST.yaml to features directory
    shutil.copy(
        feat_code_test_dir / "FEAT-CODE-TEST.yaml",
        features_dir / "FEAT-CODE-TEST.yaml"
    )

    # Create tasks/backlog/<feature-slug>/ directory. AutoBuild derives the
    # feature slug from the first task's file_path and copies task files from
    # tasks/backlog/<slug>/, so the layout on disk has to match the file_path
    # recorded in FEAT-CODE-TEST.yaml.
    tasks_dir = repo_dir / "tasks" / "backlog" / "feat-code-test"
    tasks_dir.mkdir(parents=True)

    # Copy task file to tasks/backlog/<feature-slug>/
    shutil.copy(
        feat_code_test_dir / "TASK-QGV-001-calculator-service.md",
        tasks_dir / "TASK-QGV-001-calculator-service.md"
    )

    # Create initial commit
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit with FEAT-CODE-TEST"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )

    return repo_dir


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_autobuild_feature(
    repo_dir: Path,
    feature_id: str,
    max_turns: int = 5,
    timeout: int = 600,
    seatless: bool = False,
) -> Dict[str, Any]:
    """
    Run AutoBuild on a feature and return results.

    Args:
        repo_dir: Path to repository
        feature_id: Feature ID (e.g., "FEAT-CODE-TEST")
        max_turns: Maximum turns for AutoBuild
        timeout: Timeout in seconds
        seatless: Point the run at an unreachable model endpoint. Use this for
            assertions about work AutoBuild does BEFORE it invokes a model, so
            the test stays hermetic and fast instead of driving whatever seat
            the operator happens to have running. The M0 fence stops the Player
            and the run finishes in about two seconds.

    Returns:
        Dictionary with:
        - exit_code: Process exit code
        - stdout: Standard output
        - stderr: Standard error
        - success: True if exit code was 0

    Raises:
        TimeoutError: If command exceeds timeout

    Note:
        The CLI is invoked as `sys.executable -m guardkit.cli.main`, never as
        the bare `guardkit-py` on PATH. On a developer machine that shim can be
        a global install pointing at a completely different checkout, so a test
        running inside a worktree would silently exercise someone else's code.
        Going through the current interpreter pins the run to the code under
        test.
    """
    cmd = [
        sys.executable,
        "-m",
        "guardkit.cli.main",
        "autobuild",
        "feature",
        feature_id,
        "--max-turns", str(max_turns)
    ]

    env = os.environ.copy()
    if seatless:
        # A closed port, not a fake hostname: refused immediately, no DNS, no
        # retry storm, no traffic to anything the operator is running.
        env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:1"
        env["ANTHROPIC_API_KEY"] = "unused-by-design"

    result = subprocess.run(
        cmd,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0
    }


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_feat_code_test_structure_exists(feat_code_test_dir: Path):
    """Verify FEAT-CODE-TEST test feature structure exists."""
    assert feat_code_test_dir.exists(), "FEAT-CODE-TEST directory not found"
    assert (feat_code_test_dir / "README.md").exists(), "README.md not found"
    assert (feat_code_test_dir / "FEAT-CODE-TEST.yaml").exists(), "YAML not found"
    assert (feat_code_test_dir / "TASK-QGV-001-calculator-service.md").exists(), \
        "Task markdown not found"
    assert (feat_code_test_dir / "expected_structure.txt").exists(), \
        "Expected structure not found"


@pytest.mark.integration
@pytest.mark.slow
def test_feat_code_test_yaml_valid(feat_code_test_dir: Path):
    """
    Verify FEAT-CODE-TEST YAML matches the schema the feature loader requires.

    The key names here are load-bearing: FeatureLoader requires 'id' and 'name'
    at feature level and 'id' and 'file_path' on every task, and Feature.status
    is a closed set. This test previously pinned 'feature_id', which held a
    stale fixture in place and hid two real parse failures.
    """
    import yaml

    yaml_path = feat_code_test_dir / "FEAT-CODE-TEST.yaml"
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "FEAT-CODE-TEST"
    assert data["name"] == "Quality Gate Validation Feature"
    assert data["status"] == "planned"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["id"] == "TASK-QGV-001"
    assert data["tasks"][0]["complexity"] == 4
    assert data["tasks"][0]["task_type"] == "feature"
    assert data["tasks"][0]["file_path"] == (
        "tasks/backlog/feat-code-test/TASK-QGV-001-calculator-service.md"
    )
    assert data["orchestration"]["parallel_groups"] == [["TASK-QGV-001"]]


@pytest.mark.integration
def test_feat_code_test_yaml_loads_through_feature_loader(
    temp_test_repo: Path,
):
    """
    The fixture parses and validates through the real FeatureLoader.

    This is the test that would have caught the drift. Reading the YAML with
    pyyaml only proves it is well-formed text; running it through the loader
    proves the field names are the ones GuardKit actually reads. Runs entirely
    in-process against a temp repo - no CLI, no model seat, no network.
    """
    from guardkit.orchestrator.feature_loader import FeatureLoader

    feature = FeatureLoader.load_feature("FEAT-CODE-TEST", repo_root=temp_test_repo)

    assert feature.id == "FEAT-CODE-TEST"
    assert [task.id for task in feature.tasks] == ["TASK-QGV-001"]
    assert FeatureLoader.validate_feature(feature, repo_root=temp_test_repo) == []


@pytest.mark.integration
@pytest.mark.slow
def test_autobuild_creates_worktree(temp_test_repo: Path):
    """
    Test that AutoBuild creates worktree correctly.

    The shared worktree is created in the setup phase, before any model is
    invoked, so this runs seatless: the model endpoint is deliberately
    unreachable and the whole thing takes about two seconds. That keeps the
    default suite off whatever seat the operator has running, and it keeps the
    test sharp - if worktree creation ever moved to after the first model call,
    this would go red, which is exactly the signal wanted.
    """
    # Run AutoBuild with max_turns=1 to minimize execution time
    result = run_autobuild_feature(
        temp_test_repo,
        "FEAT-CODE-TEST",
        max_turns=1,
        timeout=300,  # 5 minutes
        seatless=True,
    )

    # Check worktree was created
    worktree_dir = temp_test_repo / ".guardkit" / "worktrees" / "FEAT-CODE-TEST"

    # Note: AutoBuild may fail quality gates (expected for scaffolding),
    # but worktree should still be created
    assert worktree_dir.exists(), \
        f"Worktree not created at {worktree_dir}\nStdout: {result['stdout']}\nStderr: {result['stderr']}"


# =============================================================================
# DOCUMENTATION TESTS
# =============================================================================

def test_quality_gate_testing_documentation_exists():
    """Verify quality gate testing documentation exists."""
    docs_path = Path(__file__).parent.parent.parent / "docs" / "testing" / "quality-gate-testing.md"

    # The documentation was added by TASK-FBSDK-024 and is part of this repo.
    assert docs_path.exists(), f"Quality gate testing documentation missing: {docs_path}"

    # Verify key sections exist
    content = docs_path.read_text()
    assert "## Overview" in content
    assert "## Test Features" in content or "FEAT-CODE-TEST" in content
    assert "## Running Tests" in content or "## Execution" in content


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v", "-s"])
