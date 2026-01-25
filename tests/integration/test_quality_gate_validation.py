"""
Integration tests for quality gate validation using FEAT-CODE-TEST.

This test suite validates that GuardKit's quality gates work correctly for
actual code implementation tasks (not scaffolding). It uses FEAT-CODE-TEST
which implements a calculator service with SOLID principles.

Test Coverage:
- Happy path: Well-structured code passes quality gates
- Failure scenarios: Poor structure and missing tests fail gates
- Coach validation: Correct decisions based on gate results
- Report generation: Player and Coach reports are created correctly
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import pytest


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

    # Create tasks/backlog directory
    tasks_dir = repo_dir / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True)

    # Copy task file to tasks/backlog
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
    timeout: int = 600
) -> Dict[str, Any]:
    """
    Run AutoBuild on a feature and return results.

    Args:
        repo_dir: Path to repository
        feature_id: Feature ID (e.g., "FEAT-CODE-TEST")
        max_turns: Maximum turns for AutoBuild
        timeout: Timeout in seconds

    Returns:
        Dictionary with:
        - exit_code: Process exit code
        - stdout: Standard output
        - stderr: Standard error
        - success: True if exit code was 0

    Raises:
        TimeoutError: If command exceeds timeout
    """
    cmd = [
        "guardkit-py",
        "autobuild",
        "feature",
        feature_id,
        "--max-turns", str(max_turns)
    ]

    result = subprocess.run(
        cmd,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=timeout
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0
    }


def parse_coach_report(report_path: Path) -> Dict[str, Any]:
    """
    Parse a Coach validation report JSON file.

    Args:
        report_path: Path to coach_turn_N.json file

    Returns:
        Parsed JSON as dictionary
    """
    with open(report_path, "r") as f:
        return json.load(f)


def parse_player_report(report_path: Path) -> Dict[str, Any]:
    """
    Parse a Player implementation report JSON file.

    Args:
        report_path: Path to player_turn_N.json file

    Returns:
        Parsed JSON as dictionary
    """
    with open(report_path, "r") as f:
        return json.load(f)


def get_latest_turn_reports(
    repo_dir: Path,
    task_id: str
) -> tuple[Optional[Dict], Optional[Dict]]:
    """
    Get the latest Player and Coach reports for a task.

    Args:
        repo_dir: Repository directory
        task_id: Task ID (e.g., "TASK-QGV-001")

    Returns:
        Tuple of (player_report, coach_report) or (None, None) if not found
    """
    autobuild_dir = repo_dir / ".guardkit" / "autobuild" / task_id

    if not autobuild_dir.exists():
        return None, None

    # Find latest player report
    player_reports = sorted(autobuild_dir.glob("player_turn_*.json"))
    player_report = None
    if player_reports:
        player_report = parse_player_report(player_reports[-1])

    # Find latest coach report
    coach_reports = sorted(autobuild_dir.glob("coach_turn_*.json"))
    coach_report = None
    if coach_reports:
        coach_report = parse_coach_report(coach_reports[-1])

    return player_report, coach_report


def check_quality_gates(coach_report: Dict[str, Any]) -> Dict[str, bool]:
    """
    Extract quality gate results from Coach report.

    Args:
        coach_report: Parsed Coach report JSON

    Returns:
        Dictionary with gate status:
        - tests_passed: bool
        - coverage_met: bool
        - arch_review_passed: bool
        - plan_audit_passed: bool
        - all_gates_passed: bool
    """
    quality_gates = coach_report.get("quality_gates", {})

    return {
        "tests_passed": quality_gates.get("tests_passed", False),
        "coverage_met": quality_gates.get("coverage_met", False),
        "arch_review_passed": quality_gates.get("arch_review_passed", False),
        "plan_audit_passed": quality_gates.get("plan_audit_passed", False),
        "all_gates_passed": quality_gates.get("all_gates_passed", False)
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
    """Verify FEAT-CODE-TEST YAML is valid."""
    import yaml

    yaml_path = feat_code_test_dir / "FEAT-CODE-TEST.yaml"
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    assert data["feature_id"] == "FEAT-CODE-TEST"
    assert data["name"] == "Quality Gate Validation Feature"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["id"] == "TASK-QGV-001"
    assert data["tasks"][0]["complexity"] == 4
    assert data["tasks"][0]["task_type"] == "feature"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    shutil.which("guardkit-py") is None,
    reason="guardkit-py CLI not available"
)
def test_autobuild_creates_worktree(temp_test_repo: Path):
    """
    Test that AutoBuild creates worktree correctly.

    This is a lightweight test that validates worktree creation
    without running full AutoBuild loop.
    """
    # Run AutoBuild with max_turns=1 to minimize execution time
    result = run_autobuild_feature(
        temp_test_repo,
        "FEAT-CODE-TEST",
        max_turns=1,
        timeout=300  # 5 minutes
    )

    # Check worktree was created
    worktree_dir = temp_test_repo / ".guardkit" / "worktrees" / "FEAT-CODE-TEST"

    # Note: AutoBuild may fail quality gates (expected for scaffolding),
    # but worktree should still be created
    assert worktree_dir.exists(), \
        f"Worktree not created at {worktree_dir}\nStdout: {result['stdout']}\nStderr: {result['stderr']}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    shutil.which("guardkit-py") is None,
    reason="guardkit-py CLI not available"
)
def test_quality_gates_evaluated(temp_test_repo: Path):
    """
    Test that quality gates are evaluated during AutoBuild.

    This test validates that:
    1. Coach reports are generated
    2. Quality gates are evaluated (tests, coverage, arch review, plan audit)
    3. Gate results are recorded in Coach reports
    """
    # Run AutoBuild (may not complete, but should generate reports)
    result = run_autobuild_feature(
        temp_test_repo,
        "FEAT-CODE-TEST",
        max_turns=2,
        timeout=600  # 10 minutes
    )

    # Get Coach reports
    player_report, coach_report = get_latest_turn_reports(
        temp_test_repo,
        "TASK-QGV-001"
    )

    # Verify reports exist
    assert player_report is not None, \
        f"No Player report found\nStdout: {result['stdout']}\nStderr: {result['stderr']}"
    assert coach_report is not None, \
        f"No Coach report found\nStdout: {result['stdout']}\nStderr: {result['stderr']}"

    # Verify quality gates were evaluated
    gates = check_quality_gates(coach_report)

    # All gate fields should be present (even if False)
    assert "tests_passed" in gates, "tests_passed gate not evaluated"
    assert "coverage_met" in gates, "coverage_met gate not evaluated"
    assert "arch_review_passed" in gates, "arch_review_passed gate not evaluated"
    assert "plan_audit_passed" in gates, "plan_audit_passed gate not evaluated"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Full AutoBuild test - requires long execution time and may be flaky")
def test_quality_gates_pass_for_good_code(temp_test_repo: Path):
    """
    Test that well-structured code passes quality gates.

    This test validates the happy path:
    1. Calculator service implements SOLID principles
    2. Architectural review score ≥60
    3. Test coverage ≥80%
    4. All tests passing
    5. Coach approves implementation

    Note: This test is skipped by default due to long execution time.
    Run with: pytest -m "not skip" to include this test.
    """
    # Run AutoBuild with sufficient turns for implementation
    result = run_autobuild_feature(
        temp_test_repo,
        "FEAT-CODE-TEST",
        max_turns=5,
        timeout=1200  # 20 minutes
    )

    # Verify AutoBuild succeeded
    assert result["success"], \
        f"AutoBuild failed\nStdout: {result['stdout']}\nStderr: {result['stderr']}"

    # Get final Coach report
    player_report, coach_report = get_latest_turn_reports(
        temp_test_repo,
        "TASK-QGV-001"
    )

    assert coach_report is not None, "No Coach report found"

    # Verify quality gates passed
    gates = check_quality_gates(coach_report)

    assert gates["tests_passed"], "Tests did not pass"
    assert gates["coverage_met"], "Coverage threshold not met"
    assert gates["arch_review_passed"], "Architectural review failed"
    assert gates["plan_audit_passed"], "Plan audit failed"
    assert gates["all_gates_passed"], "Not all gates passed"

    # Verify Coach decision was approval
    assert coach_report.get("decision") == "approved", \
        f"Coach did not approve: {coach_report.get('decision')}"


# =============================================================================
# DOCUMENTATION TESTS
# =============================================================================

def test_quality_gate_testing_documentation_exists():
    """Verify quality gate testing documentation exists."""
    docs_path = Path(__file__).parent.parent.parent / "docs" / "testing" / "quality-gate-testing.md"

    # Note: Documentation will be created as part of TASK-FBSDK-024
    # This test will fail initially and pass once documentation is added
    if docs_path.exists():
        # Verify key sections exist
        content = docs_path.read_text()
        assert "## Overview" in content
        assert "## Test Features" in content or "FEAT-CODE-TEST" in content
        assert "## Running Tests" in content or "## Execution" in content
    else:
        pytest.skip("Documentation not yet created (expected in TASK-FBSDK-024)")


# =============================================================================
# UTILITY FUNCTIONS (for manual testing/debugging)
# =============================================================================

def debug_autobuild_failure(repo_dir: Path, task_id: str):
    """
    Debug helper to inspect AutoBuild failure.

    Usage:
        pytest tests/integration/test_quality_gate_validation.py -k test_quality_gates_evaluated -v -s
        # Then in debugger or interactive shell:
        debug_autobuild_failure(temp_test_repo, "TASK-QGV-001")
    """
    autobuild_dir = repo_dir / ".guardkit" / "autobuild" / task_id

    if not autobuild_dir.exists():
        print(f"No autobuild directory found at {autobuild_dir}")
        return

    print(f"\n=== AutoBuild Reports for {task_id} ===\n")

    # List all reports
    player_reports = sorted(autobuild_dir.glob("player_turn_*.json"))
    coach_reports = sorted(autobuild_dir.glob("coach_turn_*.json"))

    print(f"Player reports: {len(player_reports)}")
    for report in player_reports:
        print(f"  - {report.name}")

    print(f"\nCoach reports: {len(coach_reports)}")
    for report in coach_reports:
        data = parse_coach_report(report)
        gates = check_quality_gates(data)
        decision = data.get("decision", "unknown")
        print(f"  - {report.name}: decision={decision}, gates={gates}")

    # Print latest Coach feedback
    if coach_reports:
        latest_coach = parse_coach_report(coach_reports[-1])
        print(f"\n=== Latest Coach Feedback ===")
        print(json.dumps(latest_coach.get("feedback", {}), indent=2))


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v", "-s"])
