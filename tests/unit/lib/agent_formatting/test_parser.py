"""
Unit tests for agent_formatting.parser module
"""

import pytest
from pathlib import Path
import tempfile
import importlib

# Use importlib to avoid 'global' keyword syntax issue in Python 3.14+
_parser = importlib.import_module('installer.global.lib.agent_formatting.parser')
extract_frontmatter = _parser.extract_frontmatter
find_sections = _parser.find_sections
find_code_blocks = _parser.find_code_blocks
parse_agent = _parser.parse_agent
AgentStructure = _parser.AgentStructure
Section = _parser.Section
CodeBlock = _parser.CodeBlock


class TestExtractFrontmatter:
    """Tests for extract_frontmatter function"""

    def test_extract_valid_frontmatter(self):
        """Test extracting valid YAML frontmatter"""
        content = """---
name: test-agent
description: Test agent
tools: Read, Write
---

Content here"""

        frontmatter, end_line = extract_frontmatter(content)

        assert frontmatter['name'] == 'test-agent'
        assert frontmatter['description'] == 'Test agent'
        assert frontmatter['tools'] == 'Read, Write'
        assert end_line == 5

    def test_extract_empty_frontmatter(self):
        """Test extracting empty frontmatter"""
        content = """---
---

Content here"""

        frontmatter, end_line = extract_frontmatter(content)

        assert frontmatter == {}
        assert end_line == 2

    def test_no_frontmatter(self):
        """Test content without frontmatter"""
        content = """# Heading

Content here"""

        frontmatter, end_line = extract_frontmatter(content)

        assert frontmatter == {}
        assert end_line == 0

    def test_malformed_frontmatter(self):
        """Test malformed YAML frontmatter"""
        content = """---
name: test
invalid yaml: [unclosed
---

Content"""

        frontmatter, end_line = extract_frontmatter(content)

        # Should return empty dict on YAML error
        assert frontmatter == {}
        assert end_line == 4  # Line after closing ---


class TestFindSections:
    """Tests for find_sections function"""

    def test_find_multiple_sections(self):
        """Test finding multiple markdown sections"""
        content = """---
name: test
---

## Section 1

Content 1

### Subsection 1.1

Subsection content

## Section 2

Content 2"""

        sections = find_sections(content, frontmatter_end=3)

        assert len(sections) == 3
        assert sections[0].title == 'Section 1'
        assert sections[0].level == 2
        assert sections[1].title == 'Subsection 1.1'
        assert sections[1].level == 3
        assert sections[2].title == 'Section 2'
        assert sections[2].level == 2

    def test_section_line_numbers(self):
        """Test that section line numbers are correct"""
        content = """---
name: test
---

## Section 1

Content here"""

        sections = find_sections(content, frontmatter_end=3)

        assert len(sections) == 1
        assert sections[0].start_line == 4  # Line with ## Section 1

    def test_no_sections(self):
        """Test content without sections"""
        content = """---
name: test
---

Just some content"""

        sections = find_sections(content, frontmatter_end=3)

        assert len(sections) == 0


class TestFindCodeBlocks:
    """Tests for find_code_blocks function"""

    def test_find_single_code_block(self):
        """Test finding a single code block"""
        content = """---
name: test
---

Some text

```python
def example():
    return True
```

More text"""

        code_blocks = find_code_blocks(content, frontmatter_end=3)

        assert len(code_blocks) == 1
        assert code_blocks[0].language == 'python'
        assert 'def example():' in code_blocks[0].content

    def test_find_multiple_code_blocks(self):
        """Test finding multiple code blocks"""
        content = """---
name: test
---

```bash
echo "hello"
```

Text

```python
print("world")
```"""

        code_blocks = find_code_blocks(content, frontmatter_end=3)

        assert len(code_blocks) == 2
        assert code_blocks[0].language == 'bash'
        assert code_blocks[1].language == 'python'

    def test_code_block_without_language(self):
        """Test code block without language specifier"""
        content = """---
name: test
---

```
plain code
```"""

        code_blocks = find_code_blocks(content, frontmatter_end=3)

        assert len(code_blocks) == 1
        assert code_blocks[0].language == ''

    def test_code_block_line_numbers(self):
        """Test that code block line numbers are correct"""
        content = """---
name: test
---

Line 4

```python
code here
```"""

        code_blocks = find_code_blocks(content, frontmatter_end=3)

        assert len(code_blocks) == 1
        assert code_blocks[0].start_line == 6  # Line with ```python


class TestParseAgent:
    """Tests for parse_agent function"""

    def test_parse_complete_agent(self, tmp_path):
        """Test parsing a complete agent file"""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
name: test-agent
description: A test agent
---

## Section 1

Text here

```python
def test():
    pass
```

## Section 2

More text"""
        )

        agent = parse_agent(agent_file)

        assert isinstance(agent, AgentStructure)
        assert agent.frontmatter['name'] == 'test-agent'
        assert len(agent.sections) == 2
        assert len(agent.code_blocks) == 1

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            parse_agent(Path('/nonexistent/file.md'))

    def test_parse_non_markdown_file(self, tmp_path):
        """Test parsing a non-markdown file"""
        non_md_file = tmp_path / "test.txt"
        non_md_file.write_text("content")

        with pytest.raises(ValueError, match="must be a markdown file"):
            parse_agent(non_md_file)

    def test_parse_minimal_agent(self, tmp_path):
        """Test parsing a minimal agent file"""
        agent_file = tmp_path / "minimal.md"
        agent_file.write_text(
            """---
name: minimal
---

Just some text"""
        )

        agent = parse_agent(agent_file)

        assert agent.frontmatter['name'] == 'minimal'
        assert len(agent.sections) == 0
        assert len(agent.code_blocks) == 0
        assert agent.frontmatter_end_line > 0
