"""
Tests to verify GR-005 documentation accuracy and completeness.

This test suite validates that:
1. CLAUDE.md contains all documented commands
2. FEAT-GR-005.md is marked as implemented
3. All command examples are valid
4. Troubleshooting section covers key scenarios
"""

import re
from pathlib import Path


def test_claude_md_has_query_commands_section():
    """Verify CLAUDE.md contains Knowledge Query Commands section."""
    claude_md = Path("CLAUDE.md")
    assert claude_md.exists(), "CLAUDE.md not found"

    content = claude_md.read_text()

    # Check for main section heading
    assert "### Knowledge Query Commands" in content, \
        "Knowledge Query Commands section missing from CLAUDE.md"


def test_claude_md_documents_all_commands():
    """Verify all four query commands are documented in CLAUDE.md."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Extract the Knowledge Query Commands section
    section_start = content.find("### Knowledge Query Commands")
    section_end = content.find("### Turn State Tracking", section_start)

    assert section_start != -1, "Knowledge Query Commands section not found"
    assert section_end != -1, "Turn State Tracking section not found"

    section_content = content[section_start:section_end]

    # Check for each command
    commands = ["show", "search", "list", "status"]
    for cmd in commands:
        assert f"guardkit graphiti {cmd}" in section_content, \
            f"Command 'guardkit graphiti {cmd}' not documented"


def test_claude_md_has_command_examples():
    """Verify CLAUDE.md includes concrete usage examples."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Check for specific examples
    examples = [
        'guardkit graphiti show FEAT-SKEL-001',
        'guardkit graphiti search "authentication patterns"',
        'guardkit graphiti list features',
        'guardkit graphiti status',
    ]

    for example in examples:
        assert example in content, \
            f"Example '{example}' not found in CLAUDE.md"


def test_claude_md_documents_knowledge_groups():
    """Verify CLAUDE.md documents knowledge group taxonomy."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Check for knowledge groups section
    assert "**Knowledge Groups:**" in content, \
        "Knowledge Groups section missing"

    # Check for key groups
    groups = [
        "System Knowledge",
        "Project Knowledge",
        "Decisions",
        "Learning",
        "Turn States",
    ]

    for group in groups:
        assert group in content, \
            f"Knowledge group '{group}' not documented"


def test_claude_md_has_turn_state_tracking_section():
    """Verify CLAUDE.md documents turn state tracking."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    assert "### Turn State Tracking (AutoBuild)" in content, \
        "Turn State Tracking section missing"

    # Check for key turn state concepts
    concepts = [
        "What Gets Captured",
        "Query Turn States",
        "Turn State Schema",
        "feature_id",
        "task_id",
        "turn_number",
        "coach_decision",
    ]

    for concept in concepts:
        assert concept in content, \
            f"Turn state concept '{concept}' not documented"


def test_claude_md_has_troubleshooting_section():
    """Verify CLAUDE.md includes troubleshooting guidance."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    assert "### Troubleshooting Graphiti" in content, \
        "Troubleshooting Graphiti section missing"

    # Check for common issues
    issues = [
        "Command not found",
        "Connection errors",
        "No results from queries",
        "Empty turn states",
        "Slow queries",
        "Stale knowledge",
    ]

    for issue in issues:
        assert issue in content, \
            f"Troubleshooting issue '{issue}' not documented"


def test_feat_gr005_marked_as_implemented():
    """Verify FEAT-GR-005.md is marked as implemented."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    assert feat_doc.exists(), "FEAT-GR-005 documentation not found"

    content = feat_doc.read_text()

    # Check for implementation status
    assert "**Status**: ✅ **IMPLEMENTED**" in content, \
        "FEAT-GR-005 not marked as implemented"


def test_feat_gr005_has_implementation_notes():
    """Verify FEAT-GR-005.md includes implementation notes."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    content = feat_doc.read_text()

    # Check for implementation notes section
    assert "## Implementation Notes" in content, \
        "Implementation Notes section missing"

    # Check for key subsections
    subsections = [
        "### Completed Tasks",
        "### Key Implementation Details",
        "### Documentation Updates",
        "### Addressing TASK-REV-1505 Findings",
        "### Performance Characteristics",
        "### Known Limitations",
        "### Success Metrics",
        "### Lessons Learned",
    ]

    for subsection in subsections:
        assert subsection in content, \
            f"Subsection '{subsection}' missing from implementation notes"


def test_feat_gr005_documents_all_tasks():
    """Verify FEAT-GR-005.md documents all implementation tasks."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    content = feat_doc.read_text()

    # Check for all task IDs
    tasks = [
        "TASK-GR5-001",  # show
        "TASK-GR5-002",  # search
        "TASK-GR5-003",  # list
        "TASK-GR5-004",  # status
        "TASK-GR5-005",  # output formatting
        "TASK-GR5-006",  # TurnStateEpisode schema
        "TASK-GR5-007",  # turn state capture
        "TASK-GR5-008",  # turn context loading
        "TASK-GR5-009",  # tests
        "TASK-GR5-010",  # documentation
    ]

    for task_id in tasks:
        assert task_id in content, \
            f"Task {task_id} not documented in FEAT-GR-005"


def test_feat_gr005_documents_success_criteria():
    """Verify FEAT-GR-005.md documents all success criteria as met."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    content = feat_doc.read_text()

    # Find the Success Metrics section
    success_section = content[content.find("### Success Metrics"):]

    # Check that all criteria are marked as complete
    criteria = [
        "Show works",
        "Search works",
        "List works",
        "Status works",
        "Helpful output",
        "Turn states",
    ]

    for criterion in criteria:
        assert f"✅ **{criterion}**" in success_section or f"✅ {criterion}" in success_section, \
            f"Success criterion '{criterion}' not marked as complete"


def test_command_examples_use_correct_syntax():
    """Verify command examples use correct CLI syntax."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Extract code blocks
    code_blocks = re.findall(r'```bash\n(.*?)\n```', content, re.DOTALL)

    # Check for common syntax errors
    for block in code_blocks:
        if "guardkit graphiti" in block:
            # Should not have typos
            assert "grapihiti" not in block, "Typo in 'graphiti'"
            assert "guardikt" not in block, "Typo in 'guardkit'"

            # Check valid command structure
            lines = [line.strip() for line in block.split('\n')
                    if line.strip() and not line.strip().startswith('#')]

            for line in lines:
                if line.startswith("guardkit graphiti"):
                    # Should have valid subcommand
                    valid_commands = ["show", "search", "list", "status", "seed",
                                    "capture", "verify", "add-context", "clear"]
                    parts = line.split()
                    if len(parts) >= 3:
                        subcommand = parts[2]
                        # Remove any trailing arguments
                        subcommand = subcommand.split('[')[0].strip()
                        assert any(cmd in subcommand for cmd in valid_commands), \
                            f"Invalid subcommand in: {line}"


def test_troubleshooting_provides_actionable_solutions():
    """Verify troubleshooting section provides concrete solutions."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Extract troubleshooting section
    troubleshooting_start = content.find("### Troubleshooting Graphiti")
    troubleshooting_end = content.find("## Development Best Practices", troubleshooting_start)

    assert troubleshooting_start != -1, "Troubleshooting section not found"

    troubleshooting_content = content[troubleshooting_start:troubleshooting_end]

    # Each issue should have code examples
    code_blocks = re.findall(r'```bash\n(.*?)\n```', troubleshooting_content, re.DOTALL)

    assert len(code_blocks) >= 5, \
        f"Troubleshooting should have at least 5 code examples, found {len(code_blocks)}"


def test_documentation_cross_references_are_valid():
    """Verify cross-references to other documentation are valid."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Check for reference to FEAT-GR-005
    assert "FEAT-GR-005" in content, \
        "Reference to FEAT-GR-005 missing"

    # Check that referenced file exists
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    assert feat_doc.exists(), \
        "Referenced FEAT-GR-005 documentation file does not exist"


def test_turn_state_schema_documentation_is_complete():
    """Verify turn state schema is fully documented."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Extract Turn State Schema section
    schema_start = content.find("**Turn State Schema:**")
    schema_end = content.find("**Benefits:**", schema_start)

    assert schema_start != -1, "Turn State Schema section not found"

    schema_content = content[schema_start:schema_end]

    # Check for all schema fields
    fields = [
        "feature_id",
        "task_id",
        "turn_number",
        "player_decision",
        "coach_decision",
        "feedback_summary",
        "blockers_found",
        "files_modified",
        "acceptance_criteria_status",
        "mode",
    ]

    for field in fields:
        assert field in schema_content, \
            f"Turn state field '{field}' not documented"


def test_knowledge_groups_match_implementation():
    """Verify documented knowledge groups match actual implementation."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Expected groups from implementation (graphiti.py)
    expected_groups = [
        "product_knowledge",
        "command_workflows",
        "patterns",
        "agents",
        "project_overview",
        "project_architecture",
        "feature_specs",
        "project_decisions",
        "architecture_decisions",
        "task_outcomes",
        "failure_patterns",
        "successful_fixes",
        "turn_states",
    ]

    for group in expected_groups:
        assert group in content, \
            f"Knowledge group '{group}' not documented in CLAUDE.md"


def test_implementation_notes_include_performance_data():
    """Verify FEAT-GR-005 implementation notes include performance characteristics."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    content = feat_doc.read_text()

    # Check for performance section
    assert "### Performance Characteristics" in content, \
        "Performance Characteristics section missing"

    # Check for response time estimates
    commands = ["show", "search", "list", "status"]

    for cmd in commands:
        assert f"`{cmd}`" in content, \
            f"Performance data for '{cmd}' command missing"


def test_documentation_includes_integration_points():
    """Verify FEAT-GR-005 documents integration with other features."""
    feat_doc = Path("docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md")
    content = feat_doc.read_text()

    # Check for integration points section
    assert "### Integration Points" in content, \
        "Integration Points section missing"

    # Check for key integrations
    integrations = [
        "Feature Planning",
        "/feature-plan",
        "AutoBuild",
        "/feature-build",
        "Interactive Capture",
    ]

    for integration in integrations:
        assert integration in content, \
            f"Integration point '{integration}' not documented"
