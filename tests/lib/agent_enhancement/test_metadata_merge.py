"""
Test frontmatter metadata merge functionality.

TASK-ENH-DM01: Discovery metadata for agent matching.
"""

import pytest
from pathlib import Path
import tempfile
import frontmatter

# Import the modules to test
import sys
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from parser import EnhancementParser
from applier import EnhancementApplier


class TestMetadataValidation:
    """Test parser validation of frontmatter_metadata."""

    def test_validate_metadata_present_and_valid(self):
        """Test validation succeeds when metadata is present and valid."""
        parser = EnhancementParser()

        enhancement = {
            "sections": ["quick_start"],
            "quick_start": "## Quick Start\n\nExample",
            "frontmatter_metadata": {
                "stack": ["python"],
                "phase": "implementation",
                "capabilities": ["api", "async"],
                "keywords": ["fastapi", "api"]
            }
        }

        # Should not raise (validation is non-blocking, just logs warnings)
        parser._validate_metadata(enhancement)

    def test_validate_metadata_missing(self, caplog):
        """Test validation warns when metadata is missing."""
        parser = EnhancementParser()

        enhancement = {
            "sections": ["quick_start"],
            "quick_start": "## Quick Start\n\nExample"
        }

        # Should log warning but not raise
        parser._validate_metadata(enhancement)

        assert "missing 'frontmatter_metadata' field" in caplog.text.lower()

    def test_validate_metadata_invalid_type(self, caplog):
        """Test validation warns when metadata is wrong type."""
        parser = EnhancementParser()

        enhancement = {
            "sections": ["quick_start"],
            "quick_start": "## Quick Start\n\nExample",
            "frontmatter_metadata": "invalid string"
        }

        # Should log warning but not raise
        parser._validate_metadata(enhancement)

        assert "must be a dict" in caplog.text.lower()

    def test_validate_metadata_missing_stack(self, caplog):
        """Test validation warns when stack field is missing."""
        parser = EnhancementParser()

        enhancement = {
            "sections": ["quick_start"],
            "quick_start": "## Quick Start\n\nExample",
            "frontmatter_metadata": {
                "phase": "implementation"
            }
        }

        # Should log warning but not raise
        parser._validate_metadata(enhancement)

        assert "missing 'stack'" in caplog.text.lower()

    def test_validate_metadata_missing_phase(self, caplog):
        """Test validation warns when phase field is missing."""
        parser = EnhancementParser()

        enhancement = {
            "sections": ["quick_start"],
            "quick_start": "## Quick Start\n\nExample",
            "frontmatter_metadata": {
                "stack": ["python"]
            }
        }

        # Should log warning but not raise
        parser._validate_metadata(enhancement)

        assert "missing 'phase'" in caplog.text.lower()


class TestMetadataMerge:
    """Test applier metadata merge functionality."""

    def test_merge_metadata_content_adds_new_fields(self):
        """Test metadata merge adds new fields without overwriting existing."""
        applier = EnhancementApplier()

        # Original content with frontmatter
        content = """---
name: test-agent
description: Test agent
priority: 8
---

# Test Agent

Some content
"""

        metadata = {
            "stack": ["python"],
            "phase": "implementation",
            "capabilities": ["api", "async"],
            "keywords": ["fastapi", "api"]
        }

        # Merge metadata
        updated = applier._merge_frontmatter_metadata_content(content, metadata)

        # Parse result
        post = frontmatter.loads(updated)

        # Verify original fields preserved
        assert post.metadata["name"] == "test-agent"
        assert post.metadata["description"] == "Test agent"
        assert post.metadata["priority"] == 8

        # Verify new fields added
        assert post.metadata["stack"] == ["python"]
        assert post.metadata["phase"] == "implementation"
        assert post.metadata["capabilities"] == ["api", "async"]
        assert post.metadata["keywords"] == ["fastapi", "api"]

    def test_merge_metadata_content_preserves_existing(self):
        """Test metadata merge preserves existing fields."""
        applier = EnhancementApplier()

        # Original content with existing metadata fields
        content = """---
name: test-agent
stack: [typescript]
phase: review
capabilities: [linting]
---

# Test Agent
"""

        metadata = {
            "stack": ["python"],  # Try to overwrite
            "phase": "implementation",  # Try to overwrite
            "capabilities": ["api"],  # Try to overwrite
            "keywords": ["new"]  # New field
        }

        # Merge metadata
        updated = applier._merge_frontmatter_metadata_content(content, metadata)

        # Parse result
        post = frontmatter.loads(updated)

        # Verify original fields preserved (not overwritten)
        assert post.metadata["stack"] == ["typescript"]
        assert post.metadata["phase"] == "review"
        assert post.metadata["capabilities"] == ["linting"]

        # Verify new field added
        assert post.metadata["keywords"] == ["new"]

    def test_merge_metadata_file_io(self):
        """Test full file I/O metadata merge."""
        applier = EnhancementApplier()

        # Create temporary agent file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
name: test-agent
description: Test agent
---

# Test Agent

Some content
""")
            temp_path = Path(f.name)

        try:
            metadata = {
                "stack": ["python"],
                "phase": "implementation",
                "capabilities": ["api", "async"],
                "keywords": ["fastapi", "api"]
            }

            # Merge metadata
            applier._merge_frontmatter_metadata(temp_path, metadata)

            # Read and verify
            post = frontmatter.load(temp_path)

            # Original fields preserved
            assert post.metadata["name"] == "test-agent"
            assert post.metadata["description"] == "Test agent"

            # New fields added
            assert post.metadata["stack"] == ["python"]
            assert post.metadata["phase"] == "implementation"
            assert post.metadata["capabilities"] == ["api", "async"]
            assert post.metadata["keywords"] == ["fastapi", "api"]

        finally:
            # Cleanup
            temp_path.unlink()

    def test_merge_metadata_file_too_large(self):
        """Test metadata merge rejects files exceeding size limit."""
        applier = EnhancementApplier()

        # Create temporary agent file that exceeds 100KB
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("---\nname: test\n---\n")
            f.write("x" * 101_000)  # 101KB of content
            temp_path = Path(f.name)

        try:
            metadata = {"stack": ["python"]}

            # Should raise ValueError for security
            with pytest.raises(ValueError, match="Agent file too large"):
                applier._merge_frontmatter_metadata(temp_path, metadata)

        finally:
            # Cleanup
            temp_path.unlink()

    def test_apply_calls_metadata_merge(self):
        """Test that apply() calls metadata merge when metadata is present."""
        applier = EnhancementApplier()

        # Create temporary agent file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
name: test-agent
---

# Test Agent
""")
            temp_path = Path(f.name)

        try:
            enhancement = {
                "sections": ["quick_start"],
                "quick_start": "## Quick Start\n\nExample",
                "frontmatter_metadata": {
                    "stack": ["python"],
                    "phase": "implementation"
                }
            }

            # Apply enhancement
            applier.apply(temp_path, enhancement)

            # Read and verify metadata was merged
            post = frontmatter.load(temp_path)
            assert post.metadata["stack"] == ["python"]
            assert post.metadata["phase"] == "implementation"

            # And content was merged
            assert "## Quick Start" in post.content

        finally:
            # Cleanup
            temp_path.unlink()


class TestPromptBuilderMetadata:
    """Test prompt builder includes metadata instructions."""

    def test_prompt_includes_metadata_schema(self):
        """Test prompt includes frontmatter_metadata in JSON schema."""
        from prompt_builder import EnhancementPromptBuilder

        builder = EnhancementPromptBuilder()
        prompt = builder.build(
            agent_metadata={"name": "test", "description": "test"},
            templates=[],
            template_dir=Path("/tmp")
        )

        # Verify schema includes frontmatter_metadata
        assert "frontmatter_metadata" in prompt
        assert '"type": "object"' in prompt
        assert '"stack"' in prompt
        assert '"phase"' in prompt
        assert '"capabilities"' in prompt
        assert '"keywords"' in prompt

    def test_prompt_includes_metadata_instructions(self):
        """Test prompt includes instructions for generating metadata."""
        from prompt_builder import EnhancementPromptBuilder

        builder = EnhancementPromptBuilder()
        prompt = builder.build(
            agent_metadata={"name": "test", "description": "test"},
            templates=[],
            template_dir=Path("/tmp")
        )

        # Verify instructions present
        assert "Discovery Metadata" in prompt
        assert "agent matching" in prompt.lower()
        assert "Technology stacks from file extensions" in prompt
