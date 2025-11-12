---
id: TASK-51B2-A785
title: Fix agent markdown formatting in template-create
status: backlog
created: 2025-11-12T18:45:00Z
updated: 2025-11-12T18:45:00Z
priority: high
tags: [template-create, agents, formatting, phase-5]
complexity: 3
parent: TASK-51B2
related_tasks: [TASK-769D, TASK-51B2-C]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# CRITICAL SCOPE RESTRICTION - READ THIS FIRST

## 🚨 TECHNOLOGY-AGNOSTIC MANDATE 🚨

**This task is FORMATTING ONLY. The overlying architecture and goal is:**

✅ **AI-DRIVEN**: AI analyzes codebases and generates agent specifications
✅ **TECHNOLOGY-AGNOSTIC**: Works for ANY programming language without code changes
✅ **ZERO HARDCODED LOGIC**: No language detection, no pattern matching, no technology-specific code

**EXPLICITLY FORBIDDEN IN THIS TASK:**
❌ NO hardcoded Python language detection
❌ NO hardcoded C# language detection
❌ NO hardcoded TypeScript language detection
❌ NO file extension pattern matching
❌ NO framework-specific logic
❌ NO technology-specific code paths
❌ NO changes to AI analysis logic
❌ NO changes to agent identification logic

**SCOPE OF THIS TASK:**
✅ Fix file formatting ONLY (JSON array → Markdown with frontmatter)
✅ Change how agent data is WRITTEN to files
✅ NO changes to what agents are generated or how they're identified

The AI agent invocation (TASK-769D) is **working perfectly**. The agent analysis is **working perfectly**. This is purely a formatting bug in Phase 5 file output.

---

# Task: Fix Agent Markdown Formatting in Template-Create

## Context

TASK-769D successfully fixed AI agent invocation - the architectural-reviewer agent now properly analyzes codebases and generates specialized agent recommendations. **This is working perfectly and must not be changed.**

However, there's a **Phase 5 formatting bug** where agent files are written as raw JSON arrays instead of proper markdown with frontmatter.

## Problem Statement

**Phase 5 (Agent Generation) Output Bug**:
- Agent files are written as single-line JSON arrays (3909 bytes per file)
- Should be individual markdown files with YAML frontmatter and structured content
- This causes Agent Validation score to be 3.0/10 instead of expected 8-10/10

**Evidence from User Output**:
```bash
$ ls -la ~/.agentecflow/templates/c#-layered-architecture-template/agents/
-rw-r--r--  3909 api-service-specialist.md
-rw-r--r--  3909 business-logic-engine-specialist.md
-rw-r--r--  3909 mapperly-mapper-specialist.md
...
```

**Current Format** (WRONG):
```json
[{"name":"maui-viewmodel-specialist","description":"Creates MAUI ViewModels using CommunityToolkit.Mvvm with ObservableProperty, RelayCommand attributes...","reason":"Project extensively uses MVVM pattern...","technologies":["C#","MAUI","MVVM","CommunityToolkit.Mvvm"],"priority":10},{"name":"realm-repository-specialist",...}]
```

**Expected Format** (CORRECT - YAML Frontmatter + Markdown Body):
```markdown
---
name: maui-viewmodel-specialist
description: Creates MAUI ViewModels using CommunityToolkit.Mvvm with ObservableProperty, RelayCommand attributes, dependency injection patterns, and IsBusy/navigation coordination
priority: 10
technologies:
  - C#
  - MAUI
  - MVVM
  - CommunityToolkit.Mvvm
  - ObservableProperty
  - RelayCommand
  - Dependency Injection
---

# MAUI ViewModel Specialist

## Purpose

Creates MAUI ViewModels using CommunityToolkit.Mvvm with ObservableProperty, RelayCommand attributes, dependency injection patterns, and IsBusy/navigation coordination.

## Why This Agent Exists

Project extensively uses MVVM pattern with CommunityToolkit.Mvvm source generators for property binding, commands with CanExecute logic, and ViewModelBase inheritance.

## Technologies

- C#
- MAUI
- MVVM
- CommunityToolkit.Mvvm
- ObservableProperty
- RelayCommand
- Dependency Injection

## Usage

This agent is automatically invoked during `/task-work` when working on MAUI ViewModel implementations.
```

## YAML Frontmatter Format Specification

**CRITICAL**: Agent files MUST use YAML frontmatter format (NOT JSON, NOT plain text).

**YAML Frontmatter Structure**:
```yaml
---
name: agent-name-here
description: Single-line description of what the agent does
priority: 10
technologies:
  - Technology 1
  - Technology 2
  - Technology 3
---
```

**Frontmatter Rules**:
1. ✅ Starts with `---` (three dashes)
2. ✅ YAML key-value pairs (NOT JSON)
3. ✅ Arrays use YAML list format (`- item` on separate lines)
4. ✅ Ends with `---` (three dashes)
5. ✅ Followed by blank line before markdown content
6. ✅ NO comma-separated arrays (use YAML list format)
7. ✅ NO quotes unless necessary for special characters
8. ✅ Consistent 2-space indentation for nested items

**Example Frontmatter**:
```yaml
---
name: maui-viewmodel-specialist
description: Creates MAUI ViewModels using CommunityToolkit.Mvvm
priority: 10
technologies:
  - C#
  - MAUI
  - MVVM
  - CommunityToolkit.Mvvm
---
```

**NOT This** (JSON format):
```json
{
  "name": "maui-viewmodel-specialist",
  "technologies": ["C#", "MAUI", "MVVM"]
}
```

**NOT This** (Comma-separated):
```yaml
---
technologies: C#, MAUI, MVVM
---
```

## Root Cause Analysis

**Likely Location**: Phase 5 agent file writing in `/template-create` orchestrator
- File: `installer/global/commands/lib/template_create_orchestrator.py` (Phase 5 section)
- OR: `installer/global/lib/agent_generator/*.py` (agent file writer)

**Hypothesis**:
- AI returns JSON array with agent objects (correct)
- Phase 5 writes entire JSON array to each file (incorrect)
- Should parse JSON array and write individual markdown files per agent

## Acceptance Criteria

### Functional Requirements
1. ✅ Each agent gets its own properly formatted markdown file
2. ✅ **Agent files have YAML frontmatter** (NOT JSON) with metadata
3. ✅ **YAML frontmatter uses proper list format** for arrays (NOT comma-separated)
4. ✅ Agent files have markdown body with sections (Purpose, Why, Technologies, Usage)
5. ✅ All 7 agents from user output are properly formatted
6. ✅ Agent Validation score improves from 3.0/10 to 8-10/10
7. ✅ Overall template score improves from 9.2/10 to 9.5+/10

### Technical Requirements
8. ✅ Parse JSON array from AI response correctly
9. ✅ Extract agent metadata (name, description, reason, technologies, priority)
10. ✅ **Convert to YAML frontmatter format** (NOT JSON)
11. ✅ **Use YAML list syntax for arrays** (dash-prefixed lines, NOT comma-separated)
12. ✅ Generate markdown body sections
13. ✅ Write one file per agent (not all agents in one file)
14. ✅ File names match agent names (e.g., `maui-viewmodel-specialist.md`)

### Technology-Agnostic Requirements
15. ✅ **NO hardcoded language detection** (AI already did this)
16. ✅ **NO pattern matching** (AI already identified patterns)
17. ✅ **NO technology-specific code** (works for C#, Python, TypeScript, Go, etc.)
18. ✅ Code changes are FORMATTING ONLY (JSON → Markdown with YAML frontmatter conversion)

### Quality Gates
19. ✅ All existing unit tests pass (100%)
20. ✅ Integration test: `/template-create` generates properly formatted agents with YAML frontmatter
21. ✅ Coverage: ≥80% line, ≥75% branch
22. ✅ No changes to AI invocation logic (TASK-769D must remain working)
23. ✅ YAML frontmatter is valid and parseable by standard YAML parsers

## Implementation Guidance

### Where to Look

**Phase 5 Agent Generation Code**:
```bash
# Primary locations to investigate:
installer/global/commands/lib/template_create_orchestrator.py  # Phase 5 section
installer/global/lib/agent_generator/                          # Agent file writing
installer/global/lib/agent_generator/generator.py              # Likely culprit
```

**What to Fix**:
1. Find where agent JSON is written to files
2. Replace with proper markdown formatter
3. Write individual files per agent (not all agents to each file)

### Example Fix Pattern

**Current (Broken)**:
```python
# Somewhere in Phase 5 or agent_generator
agent_json = json.dumps(agents)  # agents is list of dicts
for agent in agents:
    agent_file = f"{agent['name']}.md"
    with open(agent_file, 'w') as f:
        f.write(agent_json)  # ← BUG: writes entire array to each file
```

**Fixed (Correct)**:
```python
# Import or create markdown formatter
from installer.global.lib.agent_generator.markdown_formatter import format_agent_markdown

for agent in agents:
    agent_file = f"{agent['name']}.md"
    markdown_content = format_agent_markdown(agent)  # ← Convert single agent to markdown
    with open(agent_file, 'w') as f:
        f.write(markdown_content)
```

**Markdown Formatter Function**:
```python
def format_agent_markdown(agent: dict) -> str:
    """
    Convert agent dict to markdown with YAML frontmatter.

    CRITICAL: Uses YAML list syntax for arrays (dash-prefixed lines).
    NOT comma-separated, NOT JSON arrays.
    """

    # YAML frontmatter - note the YAML list syntax for technologies
    tech_list = '\n'.join(f"  - {tech}" for tech in agent['technologies'])

    frontmatter = f"""---
name: {agent['name']}
description: {agent['description']}
priority: {agent['priority']}
technologies:
{tech_list}
---

"""

    # Markdown body
    body = f"""# {agent['name'].replace('-', ' ').title()}

## Purpose

{agent['description']}

## Why This Agent Exists

{agent['reason']}

## Technologies

{chr(10).join(f"- {tech}" for tech in agent['technologies'])}

## Usage

This agent is automatically invoked during `/task-work` when working on {agent['name'].replace('-', ' ')} implementations.
"""

    return frontmatter + body
```

### Testing Strategy

**Unit Tests**:
```python
import yaml

def test_format_agent_markdown():
    """Test single agent formatting with YAML frontmatter."""
    agent = {
        "name": "test-specialist",
        "description": "Test description",
        "reason": "Test reason",
        "technologies": ["Python", "pytest"],
        "priority": 8
    }

    result = format_agent_markdown(agent)

    # Verify YAML frontmatter structure
    assert result.startswith("---\n")  # Starts with YAML delimiter
    assert "name: test-specialist" in result
    assert "  - Python" in result  # YAML list syntax (NOT "Python, pytest")
    assert "  - pytest" in result  # Each technology on separate line
    assert "## Purpose" in result
    assert "## Why This Agent Exists" in result
    assert "## Technologies" in result

    # Verify YAML is parseable
    frontmatter_end = result.find("---", 4)
    yaml_content = result[4:frontmatter_end]
    parsed = yaml.safe_load(yaml_content)
    assert parsed['name'] == 'test-specialist'
    assert parsed['technologies'] == ['Python', 'pytest']
    assert isinstance(parsed['technologies'], list)  # Must be list, not string

def test_write_agent_files():
    """Test writing multiple agent files."""
    agents = [
        {"name": "agent1", ...},
        {"name": "agent2", ...}
    ]

    write_agent_files(agents, temp_dir)

    assert (temp_dir / "agent1.md").exists()
    assert (temp_dir / "agent2.md").exists()
    assert len(list(temp_dir.glob("*.md"))) == 2
```

**Integration Test**:
```bash
# Run /template-create and verify agent formatting
cd test_codebase
/template-create --validate

# Check agent files
cat ~/.agentecflow/templates/TEST-template/agents/test-specialist.md
# Should show proper markdown with frontmatter, not JSON
```

## Success Metrics

**Before** (Current State):
```bash
Agent Validation: 3.0/10 ❌
Overall Score: 9.2/10
Files: 7 agents, all 3909 bytes (JSON)
Format: Raw JSON array
```

**After** (Expected State):
```bash
Agent Validation: 8.0-10.0/10 ✅
Overall Score: 9.5+/10
Files: 7 agents, varying sizes (markdown)
Format: Proper YAML frontmatter + markdown body
```

## Related Tasks

- **TASK-769D**: ✅ COMPLETE - AI agent invocation working (Phase 1)
- **TASK-51B2-C**: ✅ COMPLETE - AI agent generation working (Phase 5 logic)
- **TASK-51B2-A785**: 🔄 THIS TASK - Fix agent file formatting (Phase 5 output)

**Relationship**:
- TASK-769D: Fixed AI invocation (Phase 1 - Codebase Analysis)
- TASK-51B2-C: Fixed agent identification (Phase 5 - Agent Generation logic)
- TASK-51B2-A785: Fix agent file writing (Phase 5 - File output formatting)

All three are complementary and use technology-agnostic, AI-driven approach.

## Important Notes

1. **DO NOT TOUCH AI LOGIC**: TASK-769D and TASK-51B2-C fixed the AI analysis. This works perfectly.

2. **FORMATTING ONLY**: This is a pure file I/O formatting bug, not an analysis bug.

3. **YAML FRONTMATTER MANDATORY**: Agent files MUST use YAML frontmatter format with proper YAML list syntax for arrays. NOT JSON, NOT comma-separated strings.

4. **TECHNOLOGY-AGNOSTIC**: The fix must work for C#, Python, TypeScript, Go, Rust, Ruby, PHP, etc. without ANY language-specific code.

5. **SCOPE DISCIPLINE**: Do not "improve" the agent analysis or add pattern detection. Just fix the file output format.

6. **VALIDATION**: After this fix, Agent Validation should improve from 3.0/10 to 8-10/10, and overall template score should improve to 9.5+/10.

## Implementation Estimate

**Duration**: 2-3 hours
**Complexity**: 3/10 (Low-Medium)

**Breakdown**:
- 30 min: Locate agent file writing code
- 60 min: Implement markdown formatter
- 30 min: Update file writing logic
- 30 min: Write unit tests
- 30 min: Integration testing

## Test Execution Log

_Automatically populated by /task-work_
