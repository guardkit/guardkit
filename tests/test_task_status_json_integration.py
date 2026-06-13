import subprocess
import sys
import json
from pathlib import Path

def test_task_status_json_script():
    """Test that the task_status_json script runs correctly."""
    
    # Test 1: Run without arguments (should return full dashboard)
    result = subprocess.run([
        sys.executable, 
        "installer/core/commands/lib/task_status_json.py"
    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    
    print("Exit code:", result.returncode)
    print("Stdout:", result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
    print("Stderr:", result.stderr)
    
    # Should succeed
    assert result.returncode == 0, f"Script failed with exit code {result.returncode}"
    
    # Should output valid JSON
    try:
        data = json.loads(result.stdout)
        assert "schema_version" in data
        assert "generated_at" in data
        assert "base_path" in data
        assert "summary" in data
        assert "tasks" in data
        print("✓ Full dashboard JSON is valid")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON output: {e}")
        raise
    
    # Test 2: Run with specific task ID (should return single task)
    result2 = subprocess.run([
        sys.executable, 
        "installer/core/commands/lib/task_status_json.py",
        "TEST-001"
    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    
    print("\nSingle task test:")
    print("Exit code:", result2.returncode)
    print("Stdout:", result2.stdout)
    print("Stderr:", result2.stderr)
    
    # Should succeed
    assert result2.returncode == 0, f"Single task script failed with exit code {result2.returncode}"
    
    # Should output valid JSON for single task
    try:
        data = json.loads(result2.stdout)
        assert "id" in data
        assert data["id"] == "TEST-001"
        print("✓ Single task JSON is valid")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON output for single task: {e}")
        raise
    
    # Test 3: Run with non-existent task ID (should fail)
    result3 = subprocess.run([
        sys.executable, 
        "installer/core/commands/lib/task_status_json.py",
        "NON-EXISTENT"
    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    
    print("\nNon-existent task test:")
    print("Exit code:", result3.returncode)
    print("Stdout:", result3.stdout)
    print("Stderr:", result3.stderr)
    
    # Should fail with exit code 1
    assert result3.returncode == 1, f"Expected exit code 1, got {result3.returncode}"
    assert "not found" in result3.stderr.lower()
    print("✓ Non-existent task correctly handled")


if __name__ == "__main__":
    test_task_status_json_script()
    print("\n✓ All integration tests passed!")