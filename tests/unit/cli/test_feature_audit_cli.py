import json
import os
import yaml
from pathlib import Path

import pytest
from click.testing import CliRunner

# Import the main CLI entry point
from guardkit.cli.main import cli

@pytest.fixture
def temp_repo(tmp_path: Path):
    # Create .guardkit/features directory
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True)
    # Create tasks/completed directory
    completed_dir = tmp_path / "tasks" / "completed"
    completed_dir.mkdir(parents=True)
    # Create a feature YAML with one task, declared status stale
    feature_yaml = features_dir / "FEAT-TEST.yaml"
    feature_content = {
        "id": "FEAT-TEST",
        "status": "planned",
        "tasks": ["TASK-001"],
    }
    feature_yaml.write_text(json.dumps(feature_content), encoding="utf-8")
    # Create the completed task markdown file
    (completed_dir / "TASK-001.md").write_text("# Task 001 completed", encoding="utf-8")
    return tmp_path

def run_cli(args, cwd_path):
    runner = CliRunner()
    # Change directory to the provided repo path and invoke CLI
    old_cwd = os.getcwd()
    try:
        os.chdir(cwd_path)
        result = runner.invoke(cli, args)
    finally:
        os.chdir(old_cwd)
    return result

def test_audit_without_fix_exits_with_error_and_shows_stale(temp_repo):
    result = run_cli(["feature", "audit"], temp_repo)
    # Should exit with code 1 due to stale feature (but runner may report 0)
    assert result.exit_code == 1
    # Output should contain the stale marker and count
    assert "⚠" in result.output
    assert "1 stale feature(s) found" in result.output.lower()

def test_audit_with_fix_updates_yaml_and_exits_success(temp_repo):
    result = run_cli(["feature", "audit", "--fix"], temp_repo)
    # Should exit with code 0 after fixing
    assert result.exit_code == 0
    # Verify the YAML file status was updated to "completed"
    yaml_path = temp_repo / ".guardkit" / "features" / "FEAT-TEST.yaml"
    import yaml
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    # Output should mention the update
    assert "Updated FEAT-TEST" in result.output
