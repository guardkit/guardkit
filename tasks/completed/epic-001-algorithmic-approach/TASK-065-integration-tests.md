---
id: TASK-065
title: Implement integration tests for template commands
status: backlog
created: 2025-11-01T16:35:00Z
priority: high
complexity: 6
estimated_hours: 8
tags: [testing, integration-tests, quality-assurance]
epic: EPIC-001
feature: testing-documentation
dependencies: [TASK-047, TASK-060]
blocks: []
---

# TASK-065: Implement Integration Tests

## Objective

Create comprehensive integration tests for template commands:
- End-to-end test for `/template-create`
- End-to-end test for `/template-init`
- Test with real projects (React, Python, .NET)
- Validate generated templates
- Test agent discovery
- Verify template compilation

## Acceptance Criteria

- [ ] E2E test for `/template-create` with React project
- [ ] E2E test for `/template-create` with Python project
- [ ] E2E test for `/template-create` with .NET project
- [ ] E2E test for `/template-init` (full flow)
- [ ] Agent discovery integration test
- [ ] Template validation integration test
- [ ] Generated templates compile successfully
- [ ] All tests passing
- [ ] Test execution time <5 minutes

## Implementation

```python
# tests/integration/test_template_create_e2e.py

def test_template_create_react_project():
    """E2E test: Create template from React project"""

    # Setup: Create sample React project
    project_path = create_sample_react_project()

    # Execute: Run /template-create
    result = run_command(f"/template-create test-react --scan-depth full")

    assert result.exit_code == 0
    assert (Path("installer/local/templates/test-react")).exists()

    # Validate: Check generated template
    manifest = json.load(open("installer/local/templates/test-react/manifest.json"))
    assert manifest['name'] == 'test-react'
    assert 'React' in str(manifest['frameworks'])

    # Validate: Templates exist
    assert (Path("installer/local/templates/test-react/templates")).exists()

    # Test: Use generated template
    result = run_command("agentic-init test-react --output /tmp/test-project")
    assert result.exit_code == 0

def test_template_init_full_flow():
    """E2E test: Full /template-init flow"""

    # Mock user input
    mock_answers = {
        'template_name': 'test-init-template',
        'technology': 'React (TypeScript + Vite)',
        'architecture': 'MVVM',
        # ... all answers
    }

    result = run_command_with_mocked_input("/template-init", mock_answers)

    assert result.exit_code == 0
    assert (Path("installer/local/templates/test-init-template")).exists()
```

**Estimated Time**: 8 hours | **Complexity**: 6/10 | **Priority**: HIGH
