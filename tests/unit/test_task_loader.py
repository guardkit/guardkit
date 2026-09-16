"""
Unit tests for TaskLoader.

This module provides comprehensive tests for task file loading and parsing,
ensuring robust YAML frontmatter handling and content extraction.
"""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch

from guardkit.tasks.task_loader import (
    TaskLoader,
    TaskNotFoundError,
    TaskParseError,
)


# ============================================================================
# Test: Task File Discovery
# ============================================================================


def test_load_task_from_backlog(tmp_path):
    """Test loading task from backlog directory."""
    # Create task file in backlog
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Test Task
---

## Requirements
Implement feature X

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify
    assert task_data["task_id"] == "TASK-AB-001"
    assert "feature X" in task_data["requirements"]
    assert len(task_data["acceptance_criteria"]) == 2


def test_load_task_from_in_progress(tmp_path):
    """Test loading task from in_progress directory."""
    # Create task file in in_progress
    task_file = tmp_path / "tasks" / "in_progress" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
---

## Requirements
Implement feature X
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify found in in_progress
    assert task_data["task_id"] == "TASK-AB-001"


def test_load_task_not_found(tmp_path):
    """Test TaskNotFoundError when task doesn't exist."""
    # Attempt to load non-existent task
    with pytest.raises(TaskNotFoundError) as exc_info:
        TaskLoader.load_task("TASK-AB-999", repo_root=tmp_path)

    # Verify error message includes search paths
    assert "TASK-AB-999" in str(exc_info.value)
    assert "backlog" in str(exc_info.value)
    assert "in_progress" in str(exc_info.value)


def test_load_task_not_found_includes_hints(tmp_path):
    """Test TaskNotFoundError includes helpful hints (TASK-NDS-003)."""
    with pytest.raises(TaskNotFoundError) as exc_info:
        TaskLoader.load_task("TASK-AB-999", repo_root=tmp_path)

    error_message = str(exc_info.value)

    # Verify error message indicates subdirectory search
    assert "/**/" in error_message or "subdirectories" in error_message

    # Verify hints section is present
    assert "Hints:" in error_message
    assert "Check task ID format" in error_message
    assert ".md extension" in error_message
    assert "tasks/backlog/<feature-slug>/" in error_message


def test_load_task_search_order(tmp_path):
    """Test that backlog is searched before in_progress."""
    # Create task in both locations (should find backlog first)
    backlog_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    backlog_file.parent.mkdir(parents=True, exist_ok=True)
    backlog_file.write_text(
        """---
title: From Backlog
---
Requirements from backlog
"""
    )

    in_progress_file = tmp_path / "tasks" / "in_progress" / "TASK-AB-001.md"
    in_progress_file.parent.mkdir(parents=True, exist_ok=True)
    in_progress_file.write_text(
        """---
title: From In Progress
---
Requirements from in_progress
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Should find backlog version first
    assert task_data["frontmatter"]["title"] == "From Backlog"


# ============================================================================
# Test: Frontmatter Parsing
# ============================================================================


def test_parse_task_with_frontmatter(tmp_path):
    """Test parsing task with YAML frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: OAuth Implementation
status: backlog
priority: high
requirements: Implement OAuth2 authentication
acceptance_criteria:
  - Support authorization code flow
  - Handle token refresh
  - Include tests
---

# Task Content
This is the task content.
"""
    )

    # Load and parse
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify frontmatter
    assert task_data["frontmatter"]["id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "OAuth Implementation"
    assert task_data["frontmatter"]["status"] == "backlog"
    assert task_data["frontmatter"]["priority"] == "high"

    # Verify requirements from frontmatter
    assert "OAuth2 authentication" in task_data["requirements"]

    # Verify acceptance criteria from frontmatter
    assert len(task_data["acceptance_criteria"]) == 3
    assert "authorization code flow" in task_data["acceptance_criteria"][0]


def test_parse_task_without_frontmatter(tmp_path):
    """Test parsing task without frontmatter (content-only)."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Implement feature X

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
"""
    )

    # Load and parse
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify requirements extracted from content
    assert "feature X" in task_data["requirements"]

    # Verify acceptance criteria extracted from content
    assert len(task_data["acceptance_criteria"]) == 2


def test_parse_task_malformed_yaml(tmp_path):
    """Test TaskParseError when YAML is malformed."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: [invalid yaml
---

Content
"""
    )

    # Should raise TaskParseError
    with pytest.raises(TaskParseError) as exc_info:
        TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert "Failed to parse" in str(exc_info.value)


# ============================================================================
# Test: Requirements Extraction
# ============================================================================


def test_extract_requirements_from_frontmatter(tmp_path):
    """Test extracting requirements from frontmatter field."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
requirements: Implement OAuth2 authentication with token refresh
---

Other content
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "OAuth2 authentication" in task_data["requirements"]


def test_extract_requirements_from_content_section(tmp_path):
    """Test extracting requirements from ## Requirements section."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Implement feature X with the following:
- OAuth2 support
- Token refresh

## Other Section
Other content
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "feature X" in task_data["requirements"]
    assert "OAuth2 support" in task_data["requirements"]


def test_extract_requirements_from_first_paragraph(tmp_path):
    """Test fallback to first paragraph when no explicit requirements."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """This task implements OAuth2 authentication.

Additional details here.
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "OAuth2 authentication" in task_data["requirements"]


def test_extract_requirements_list_from_frontmatter(tmp_path):
    """Test extracting requirements as list from frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
requirements:
  - Implement OAuth2
  - Add token refresh
  - Include tests
---
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    # Should join list into string
    assert "OAuth2" in task_data["requirements"]
    assert "token refresh" in task_data["requirements"]


# ============================================================================
# Test: Acceptance Criteria Extraction
# ============================================================================


def test_extract_acceptance_criteria_from_frontmatter(tmp_path):
    """Test extracting acceptance criteria from frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
acceptance_criteria:
  - Support OAuth2
  - Handle refresh
  - Include tests
---
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 3
    assert "OAuth2" in task_data["acceptance_criteria"][0]


def test_extract_acceptance_criteria_from_content_section(tmp_path):
    """Test extracting acceptance criteria from ## Acceptance Criteria section."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Acceptance Criteria
- [ ] Support OAuth2
- [x] Handle refresh
- Include tests

## Other Section
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 3
    assert "OAuth2" in task_data["acceptance_criteria"][0]
    assert "refresh" in task_data["acceptance_criteria"][1]


def test_extract_acceptance_criteria_various_formats(tmp_path):
    """Test parsing various bullet/checkbox formats."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Acceptance Criteria
- [ ] Checkbox unchecked
- [x] Checkbox checked
- Bullet point
* Asterisk bullet
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 4


def test_extract_acceptance_criteria_default(tmp_path):
    """Test default when no criteria found."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Just requirements, no criteria
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    # Should have default message
    assert "No acceptance criteria specified" in task_data["acceptance_criteria"]


# ============================================================================
# Test: Complete Task Data Structure
# ============================================================================


def test_load_task_returns_complete_structure(tmp_path):
    """Test that load_task returns all expected fields."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
---

## Requirements
Implement feature
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify all expected keys present
    assert "task_id" in task_data
    assert "requirements" in task_data
    assert "acceptance_criteria" in task_data
    assert "frontmatter" in task_data
    assert "content" in task_data
    assert "file_path" in task_data

    # Verify types
    assert isinstance(task_data["task_id"], str)
    assert isinstance(task_data["requirements"], str)
    assert isinstance(task_data["acceptance_criteria"], list)
    assert isinstance(task_data["frontmatter"], dict)
    assert isinstance(task_data["content"], str)
    assert isinstance(task_data["file_path"], Path)


# ============================================================================
# Test: Nested Directory Support (TASK-NDS-001)
# ============================================================================


def test_load_task_from_nested_directory(tmp_path):
    """Test loading task from nested subdirectory."""
    # Create task in nested folder
    task_file = tmp_path / "tasks" / "backlog" / "feature-slug" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Nested Task
---

## Requirements
Implement feature X
"""
    )

    # Should find task in nested directory
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert task_data["task_id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "Nested Task"


def test_load_task_with_extended_filename(tmp_path):
    """Test loading task with extended filename (descriptive suffix)."""
    # Create task with extended filename
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001-create-auth-service.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Auth Service Task
---

## Requirements
Implement auth service
"""
    )

    # Should match extended filename
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert task_data["task_id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "Auth Service Task"


def test_load_task_extended_filename_in_nested_dir(tmp_path):
    """Test loading task with extended filename in nested directory."""
    # Create task with extended filename in nested directory
    task_file = (
        tmp_path
        / "tasks"
        / "backlog"
        / "auth-feature"
        / "TASK-AB-001-create-auth-service.md"
    )
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Nested Auth Task
---

## Requirements
Implement nested auth
"""
    )

    # Should find nested task with extended filename
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert task_data["task_id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "Nested Auth Task"


def test_search_order_with_nested_directories(tmp_path):
    """Test that backlog is searched before in_progress with nested dirs."""
    # Create task in nested backlog
    backlog_file = tmp_path / "tasks" / "backlog" / "feature" / "TASK-AB-001.md"
    backlog_file.parent.mkdir(parents=True, exist_ok=True)
    backlog_file.write_text(
        """---
title: From Nested Backlog
---
"""
    )

    # Create task in flat in_progress
    in_progress_file = tmp_path / "tasks" / "in_progress" / "TASK-AB-001.md"
    in_progress_file.parent.mkdir(parents=True, exist_ok=True)
    in_progress_file.write_text(
        """---
title: From In Progress
---
"""
    )

    # Should find backlog version first (even though nested)
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert task_data["frontmatter"]["title"] == "From Nested Backlog"


def test_deeply_nested_task_discovery(tmp_path):
    """Test finding tasks in deeply nested directories."""
    # Create task in deeply nested path
    task_file = (
        tmp_path
        / "tasks"
        / "backlog"
        / "epic"
        / "feature"
        / "sprint"
        / "TASK-AB-001.md"
    )
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Deeply Nested Task
---
"""
    )

    # Should find deeply nested task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert task_data["task_id"] == "TASK-AB-001"


def test_backward_compatibility_flat_structure(tmp_path):
    """Test backward compatibility with flat directory structure."""
    # Create task in flat backlog (original structure)
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Flat Task
---

## Requirements
Implement flat feature
"""
    )

    # Should still find task in flat structure
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert task_data["task_id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "Flat Task"


def test_task001_shape_preserves_full_fallback_and_wrapped_criteria():
    """The frozen task001 shape keeps every instruction and five complete ACs."""
    content = """
# Define records and exact-byte source ingestion

Read the seed README shared contracts first. Complete predecessors before starting.

## Files this task may change

- src/career_assistant/__init__.py
- src/career_assistant/models.py
- src/career_assistant/evidence.py
- pyproject.toml
- tests/test_evidence.py
- README.md

## Request served

Import saved synthetic snapshots and resolve every candidate claim against its exact original
source, retaining unknowns and the distinction between direct, adjacent and missing evidence.

## Implementation

Implement the README shared model/error/canonicalization contracts before other tasks consume
them. Freeze public field names in code, including strict BriefContent inputs and server-owned
output identities. Add complete type validation, nonempty IDs, permitted enums and integer/boolean
distinctions. No runtime module reads acceptance-spec or test aliases.

Implement reusable source-record functions in evidence.py: exact bytes/hash, source metadata,
confined relative paths, UTF-8 byte spans and exact excerpt validation. Source identity is separate
from role deduplication and model inference. Preserve original evidence plus ordered authenticated
correction records/effective statements; validate source/correction relationships and limits
without a fixture-specific prose oracle. Corrected wording is not required to be in original bytes.

Set package/CLI metadata but do not introduce agent calls or extra files. Keep initial fixture
integrity assertions and add behavior tests alongside them. pyproject may package skill data later;
dcode is a coding-worker runtime choice and is not a product dependency.

## Acceptance criteria

- Exact-byte hashes preserve LF, Unicode and empty-source identity; no decoding normalization.
- Reject absolute/parent/symlink/intermediate-symlink/escaped paths and mismatched content hashes.
- UTF-8 span tests cover accented/multibyte characters, byte boundaries, end-exclusive semantics,
  OOB/negative spans and wrong excerpt paired with a real source ID/hash.
- Canonical action bytes use complete payload, sorted keys, indent2, ensure_ascii false and final LF.
  Same textual payload with distinct JSON types is not silently equated.
- BriefContent rejects forged output metadata and broken proof references; public record serializers
  preserve checker spellings. Imports are side-effect free. No product implementation is hardcoded
  to any fixture role, evidence fact, expected output or request alias.

## Verification boundary

Run the frozen .guardkit toolchain command only in the assigned sandbox worktree. Preserve
supplied fixtures, task/config inputs and external checker. Record actual exits/failures and
meaningful new assertions; do not claim execution from static review. Use no new test filenames.
"""

    assert TaskLoader._extract_requirements({}, content) == content.strip()
    assert TaskLoader._extract_acceptance_criteria({}, content) == [
        "Exact-byte hashes preserve LF, Unicode and empty-source identity; no decoding normalization.",
        "Reject absolute/parent/symlink/intermediate-symlink/escaped paths and mismatched content hashes.",
        (
            "UTF-8 span tests cover accented/multibyte characters, byte boundaries, "
            "end-exclusive semantics,\n"
            "  OOB/negative spans and wrong excerpt paired with a real source ID/hash."
        ),
        (
            "Canonical action bytes use complete payload, sorted keys, indent2, "
            "ensure_ascii false and final LF.\n"
            "  Same textual payload with distinct JSON types is not silently equated."
        ),
        (
            "BriefContent rejects forged output metadata and broken proof references; "
            "public record serializers\n"
            "  preserve checker spellings. Imports are side-effect free. No product "
            "implementation is hardcoded\n"
            "  to any fixture role, evidence fact, expected output or request alias."
        ),
    ]


def test_task002_shape_preserves_all_wrapped_acceptance_text():
    """The frozen task002 AC shape remains seven complete criteria."""
    content = """# Persist queue, decisions and transactional brief records

## Request served

Keep one durable shortlist with source provenance; import idempotently and preserve corrections,
rejections and generated outputs after restarting.

## Acceptance criteria

- Two imports yield stable snapshot/app IDs, unchanged sources and zero new public history;
  supplied bundle yields seven snapshots/five roles/one incomplete source through generic parsing.
- Mirrors link; engagement/location variants stay separate; blocked access does not imply closure.
- Default list hides only explicit rejection; restart/reimport preserve it and its reason.
- Correction/rejection replay, conflict, unknown IDs and exact flat action payload hashes behave
  correctly after close/reopen; prior actions, evidence bytes and outputs never mutate.
- Concurrent same-key requests have one owner and at most one published output/history row.
- Changing evidence/correction during a pinned run refuses publication; saving requirements does
  not itself invalidate replay. Unpublished/failed proposals never appear in public list/history.
- Simulated crash/file loss recovers Markdown from a valid published row without duplicate history.

## Verification boundary

The following peer section is not acceptance text.
"""

    criteria = TaskLoader._extract_acceptance_criteria({}, content)

    assert len(criteria) == 7
    assert criteria[0].endswith(
        "\n  supplied bundle yields seven snapshots/five roles/one incomplete source "
        "through generic parsing."
    )
    assert criteria[3].endswith(
        "\n  correctly after close/reopen; prior actions, evidence bytes and outputs never mutate."
    )
    assert criteria[5].endswith(
        "\n  not itself invalidate replay. Unpublished/failed proposals never appear "
        "in public list/history."
    )
    assert "Verification boundary" not in criteria[-1]


def test_acceptance_criteria_keep_nested_content_and_fenced_examples():
    """Nested/fenced bullets stay with their parent and fenced headings do not stop it."""
    content = """```markdown
## Acceptance Criteria
- This bullet is an example, not a real criterion.
```

## Acceptance Criteria
- [ ] xylophone behavior is preserved
  Wrapped explanation.
  - nested bullet
  - [ ] nested checkbox
  ## Nested heading

  ```markdown
  ## This heading is fenced
  - This bullet is fenced
  ```

### Criterion detail
More detail for the same criterion.
- [X] Second criterion
## Verification
- This belongs to the next peer section.
"""

    assert TaskLoader._extract_acceptance_criteria({}, content) == [
        (
            "xylophone behavior is preserved\n"
            "  Wrapped explanation.\n"
            "  - nested bullet\n"
            "  - [ ] nested checkbox\n"
            "  ## Nested heading\n\n"
            "  ```markdown\n"
            "  ## This heading is fenced\n"
            "  - This bullet is fenced\n"
            "  ```\n\n"
            "### Criterion detail\n"
            "More detail for the same criterion."
        ),
        "Second criterion",
    ]


def test_acceptance_prefix_removal_is_exact_and_malformed_items_are_safe():
    """Prefix parsing does not use a character-set lstrip or invent empty ACs."""
    content = """## Acceptance Criteria
- [x] xylophone starts with x\x20\x20
  wrapped after a Markdown hard break
* [brackets] remain literal
- [maybe] malformed checkbox remains literal
- [ ]
- [x]    leading spaces after the real prefix remain
## Next section
ignored
"""

    assert TaskLoader._extract_acceptance_criteria({}, content) == [
        "xylophone starts with x  \n  wrapped after a Markdown hard break",
        "[brackets] remain literal",
        "[maybe] malformed checkbox remains literal",
        "   leading spaces after the real prefix remain",
    ]


def test_unclosed_fence_keeps_apparent_sections_inside_the_criterion():
    """An unclosed fenced example cannot turn its contents into structure."""
    content = """## Acceptance Criteria
- Preserve this example:
  ```text
## Apparent peer heading
- Apparent top-level bullet
"""

    assert TaskLoader._extract_acceptance_criteria({}, content) == [
        (
            "Preserve this example:\n"
            "  ```text\n"
            "## Apparent peer heading\n"
            "- Apparent top-level bullet"
        )
    ]


def test_requirements_fallback_empty_body_keeps_existing_sentinel():
    assert TaskLoader._extract_requirements({}, " \n\t\n") == "No requirements specified"


def test_frontmatter_and_explicit_requirements_keep_precedence():
    content = """# Full task body

## Requirements
Only this explicit section.

## Other section
Other body text.
"""

    assert TaskLoader._extract_requirements(
        {"requirements": "Frontmatter wins"}, content
    ) == "Frontmatter wins"
    assert TaskLoader._extract_requirements({}, content) == "Only this explicit section."
