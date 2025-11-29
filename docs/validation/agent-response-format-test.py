#!/usr/bin/env python3
"""
Validation script for .agent-response.json format.

This script demonstrates the correct format for agent response files
and validates that they conform to the AgentResponse dataclass schema.

Usage:
    python3 docs/validation/agent-response-format-test.py

Related: TASK-FIX-267C
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Use importlib to avoid 'global' keyword issue
import importlib
_invoker = importlib.import_module('installer.global.lib.agent_bridge.invoker')
AgentResponse = _invoker.AgentResponse


def test_valid_response():
    """Test Case 1: Valid response format."""
    print("\n" + "="*70)
    print("TEST CASE 1: Valid Response Format")
    print("="*70)

    # Create valid response data
    agent_output = {
        "sections": ["boundaries"],
        "boundaries": "## Boundaries\n\n### ALWAYS\n- ✅ Test rule\n\n### NEVER\n- ❌ Test prohibition\n\n### ASK\n- ⚠️ Test escalation"
    }

    response_data = {
        "request_id": "test-001",
        "version": "1.0",
        "status": "success",
        "response": json.dumps(agent_output),  # ✅ JSON-encoded string
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }

    try:
        response = AgentResponse(**response_data)
        print("✅ Response structure valid")
        print(f"   - request_id: {response.request_id}")
        print(f"   - status: {response.status}")
        print(f"   - response length: {len(response.response)} chars")

        # Test inner JSON parsing
        parsed_output = json.loads(response.response)
        print("✅ Agent output parsed successfully")
        print(f"   - sections: {parsed_output.get('sections', [])}")

        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def test_wrong_field_name():
    """Test Case 2: Wrong field name (result vs response)."""
    print("\n" + "="*70)
    print("TEST CASE 2: Wrong Field Name (result vs response)")
    print("="*70)

    response_data = {
        "request_id": "test-002",
        "version": "1.0",
        "status": "success",
        "result": "{\"sections\": []}",  # ❌ Should be "response"
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }

    try:
        response = AgentResponse(**response_data)
        print("❌ Should have failed but didn't!")
        return False
    except TypeError as e:
        if "unexpected keyword argument 'result'" in str(e):
            print(f"✅ Expected error caught: {e}")
            return True
        else:
            print(f"❌ Wrong error: {e}")
            return False


def test_wrong_data_type():
    """Test Case 3: Wrong data type (object vs string)."""
    print("\n" + "="*70)
    print("TEST CASE 3: Wrong Data Type (object vs string)")
    print("="*70)

    response_data = {
        "request_id": "test-003",
        "version": "1.0",
        "status": "success",
        "response": {"sections": []},  # ❌ Should be JSON string
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }

    try:
        response = AgentResponse(**response_data)
        # If it doesn't fail during init, it will fail during json.loads()
        try:
            parsed = json.loads(response.response)
            print("❌ Should have failed but didn't!")
            return False
        except TypeError as e:
            print(f"✅ Expected error during parsing: {e}")
            return True
    except Exception as e:
        print(f"⚠️ Failed during init (also acceptable): {e}")
        return True


def test_missing_required_field():
    """Test Case 4: Missing required field."""
    print("\n" + "="*70)
    print("TEST CASE 4: Missing Required Field")
    print("="*70)

    response_data = {
        "request_id": "test-004",
        "status": "success",
        "response": "{\"sections\": []}"
        # ❌ Missing: version, created_at, duration_seconds, metadata
    }

    try:
        response = AgentResponse(**response_data)
        print("❌ Should have failed but didn't!")
        return False
    except TypeError as e:
        if "missing" in str(e).lower():
            print(f"✅ Expected error caught: {e}")
            return True
        else:
            print(f"❌ Wrong error: {e}")
            return False


def test_error_response():
    """Test Case 5: Error response format."""
    print("\n" + "="*70)
    print("TEST CASE 5: Error Response Format")
    print("="*70)

    response_data = {
        "request_id": "test-005",
        "version": "1.0",
        "status": "error",
        "response": None,  # ✅ Can be None for errors
        "error_message": "Agent timeout after 120 seconds",
        "error_type": "timeout",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 120.0,
        "metadata": {}
    }

    try:
        response = AgentResponse(**response_data)
        print("✅ Error response structure valid")
        print(f"   - status: {response.status}")
        print(f"   - error_type: {response.error_type}")
        print(f"   - error_message: {response.error_message}")
        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def print_correct_format_example():
    """Print the correct format example."""
    print("\n" + "="*70)
    print("CORRECT FORMAT EXAMPLE")
    print("="*70)

    agent_output = {
        "sections": ["related_templates", "examples", "boundaries"],
        "related_templates": "## Related Templates\n\n- template1",
        "examples": "## Code Examples\n\n### Example 1\n```code```",
        "boundaries": "## Boundaries\n\n### ALWAYS\n- ✅ Rule 1"
    }

    response_data = {
        "request_id": "32ecfadc-2b66-4daa-a7c0-a03c449fcea5",
        "version": "1.0",
        "status": "success",
        "response": json.dumps(agent_output),
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }

    print(json.dumps(response_data, indent=2))
    print("\nKey Points:")
    print("  1. Field is named 'response' (NOT 'result')")
    print("  2. Response field contains JSON-encoded STRING (NOT object)")
    print("  3. All 9 required fields are present")
    print("  4. error_message and error_type are null for success")


def main():
    """Run all validation tests."""
    print("Agent Response Format Validation")
    print("Task: TASK-FIX-267C")
    print("Testing AgentResponse dataclass schema compliance")

    results = []

    results.append(("Valid Response", test_valid_response()))
    results.append(("Wrong Field Name", test_wrong_field_name()))
    results.append(("Wrong Data Type", test_wrong_data_type()))
    results.append(("Missing Required Field", test_missing_required_field()))
    results.append(("Error Response", test_error_response()))

    print_correct_format_example()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All validation tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
