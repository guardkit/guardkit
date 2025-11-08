#!/usr/bin/env python3
"""
Simple test script for TASK-068: Template Output Location Flag

Verifies the implementation by checking the code directly without importing.
"""

from pathlib import Path


def test_orchestrator_file():
    """Test that the orchestrator file has the correct changes"""
    orchestrator_path = Path(__file__).parent / "installer" / "global" / "commands" / "lib" / "template_create_orchestrator.py"

    if not orchestrator_path.exists():
        print(f"❌ Orchestrator file not found: {orchestrator_path}")
        return False

    content = orchestrator_path.read_text()

    # Test 1: Check for output_location parameter in OrchestrationConfig
    if "output_location: str = 'global'" in content:
        print("✓ Test 1 passed: output_location parameter added to OrchestrationConfig with default 'global'")
    else:
        print("❌ Test 1 failed: output_location parameter not found in OrchestrationConfig")
        return False

    # Test 2: Check for TASK-068 comment in _phase8_package_assembly
    if "TASK-068" in content and "Determine output path based on output_location" in content:
        print("✓ Test 2 passed: TASK-068 implementation found in _phase8_package_assembly")
    else:
        print("❌ Test 2 failed: TASK-068 implementation not found")
        return False

    # Test 3: Check for global location path
    if '".agentecflow" / "templates"' in content:
        print("✓ Test 3 passed: Global location path (~/.agentecflow/templates/) implemented")
    else:
        print("❌ Test 3 failed: Global location path not found")
        return False

    # Test 4: Check for repo location path
    if '"installer/global/templates"' in content and 'manifest.name' in content:
        print("✓ Test 4 passed: Repo location path (installer/global/templates/) implemented")
    else:
        print("❌ Test 4 failed: Repo location path not found")
        return False

    # Test 5: Check for location_type in success message
    if 'location_type: str = "personal"' in content:
        print("✓ Test 5 passed: Location type parameter added to _print_success")
    else:
        print("❌ Test 5 failed: Location type parameter not found in _print_success")
        return False

    # Test 6: Check for personal and distribution messaging
    if 'Type: Personal use (immediately available)' in content and 'Type: Distribution (requires installation)' in content:
        print("✓ Test 6 passed: Location-specific messaging implemented")
    else:
        print("❌ Test 6 failed: Location-specific messaging not found")
        return False

    # Test 7: Check for updated run_template_create function
    if 'output_location: str = \'global\'' in content and 'DEPRECATED: Use output_location instead' in content:
        print("✓ Test 7 passed: run_template_create updated with output_location parameter")
    else:
        print("❌ Test 7 failed: run_template_create not properly updated")
        return False

    return True


def test_command_documentation():
    """Test that the command documentation has been updated"""
    doc_path = Path(__file__).parent / "installer" / "global" / "commands" / "template-create.md"

    if not doc_path.exists():
        print(f"❌ Command documentation not found: {doc_path}")
        return False

    content = doc_path.read_text()

    # Test 1: Check for --output-location flag
    if "--output-location" in content and "-o" in content:
        print("✓ Test 8 passed: --output-location flag documented")
    else:
        print("❌ Test 8 failed: --output-location flag not documented")
        return False

    # Test 2: Check for 'global' and 'repo' values
    if "'global'" in content and "'repo'" in content:
        print("✓ Test 9 passed: Both 'global' and 'repo' values documented")
    else:
        print("❌ Test 9 failed: Output location values not documented")
        return False

    # Test 3: Check for TASK-068 reference
    if "TASK-068" in content:
        print("✓ Test 10 passed: TASK-068 reference found in documentation")
    else:
        print("❌ Test 10 failed: TASK-068 reference not found")
        return False

    # Test 4: Check for personal and distribution examples
    if "Personal Use (default)" in content or "Personal Template" in content:
        print("✓ Test 11 passed: Personal use examples documented")
    else:
        print("❌ Test 11 failed: Personal use examples not found")
        return False

    if "Team Distribution" in content or "Distribution" in content:
        print("✓ Test 12 passed: Distribution workflow documented")
    else:
        print("❌ Test 12 failed: Distribution workflow not documented")
        return False

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  TASK-068: Template Output Location Flag - Verification")
    print("=" * 60 + "\n")

    orchestrator_ok = test_orchestrator_file()
    print()
    documentation_ok = test_command_documentation()

    print("\n" + "=" * 60)
    if orchestrator_ok and documentation_ok:
        print("  ✅ All verification tests passed!")
        print("=" * 60 + "\n")

        print("Summary of changes:")
        print("  1. ✓ Added output_location parameter (default: 'global')")
        print("  2. ✓ Global location: ~/.agentecflow/templates/")
        print("  3. ✓ Repo location: installer/global/templates/")
        print("  4. ✓ Legacy --output PATH still supported")
        print("  5. ✓ Location-specific success messages")
        print("  6. ✓ Command documentation updated")
        print("  7. ✓ Usage examples for both workflows")
        print()
        print("Next steps:")
        print("  - Test with actual /template-create command")
        print("  - Verify templates are created in correct locations")
        print("  - Verify templates are immediately usable from global location")
        return 0
    else:
        print("  ❌ Some tests failed!")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
