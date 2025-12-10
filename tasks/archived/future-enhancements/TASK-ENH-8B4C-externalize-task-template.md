---
task_id: TASK-ENH-8B4C
title: Move task template to external file with Jinja2
status: BACKLOG
priority: MEDIUM
complexity: 2
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [enhancement, phase-8, maintainability, templates]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-FIX-4B2E]
estimated_duration: 2 hours
technologies: [python, jinja2, templates]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Move Task Template to External File with Jinja2

## Problem Statement

The task content template is embedded as a 44-line f-string in the code, making it hard to maintain, modify, and test variations.

**Review Finding** (Section 2, Medium Priority Issue #5):
> **Location**: Lines 966-1009
> **Problem**: Task template embedded as 44-line f-string
> **Impact**: Hard to maintain and modify, difficult to test variations

## Current State

**Location**: `installer/core/commands/lib/template_create_orchestrator.py:966-1009`

```python
task_content = f"""---
task_id: {task_id}
title: "Enhance {agent_name} Agent"
status: BACKLOG
priority: MEDIUM
complexity: 5
# ... 40 more lines of embedded template
"""
```

**Problems**:
- Template logic mixed with code
- Hard to visualize template structure
- Hard to modify without code changes
- No syntax highlighting for YAML frontmatter
- Difficult to test different template variations
- Can't reuse template in other contexts

## Acceptance Criteria

### 1. External Template File
- [ ] Template moved to separate file (e.g., `agent_enhancement_task.md.j2`)
- [ ] File location: `installer/core/commands/lib/templates/`
- [ ] Jinja2 syntax for variables
- [ ] Template readable and well-formatted
- [ ] Comments in template explain sections

### 2. Template Rendering
- [ ] Use Jinja2 Template class
- [ ] Pass variables as dict to render()
- [ ] Handle missing variables gracefully
- [ ] Validate rendered output

### 3. Backward Compatibility
- [ ] Rendered output identical to current f-string
- [ ] No breaking changes to task format
- [ ] All existing tests still pass

### 4. Error Handling
- [ ] Template file not found → clear error
- [ ] Template syntax error → clear error with line number
- [ ] Missing required variable → clear error
- [ ] Invalid template path → fallback or error

### 5. Maintainability
- [ ] Template easier to edit than f-string
- [ ] Can preview template without running code
- [ ] Version control shows template changes clearly
- [ ] Documentation explains template variables

## Technical Details

### Files to Create

**1. `installer/core/commands/lib/templates/agent_enhancement_task.md.j2`**

New Jinja2 template file.

### Files to Modify

**1. `installer/core/commands/lib/template_create_orchestrator.py`**
- Remove embedded f-string (lines 966-1009)
- Add template loading and rendering logic
- Add error handling for template operations

### Recommended Implementation

#### Step 1: Create Template File

**File**: `installer/core/commands/lib/templates/agent_enhancement_task.md.j2`

```jinja2
---
task_id: {{ task_id }}
title: "Enhance {{ agent_name }} Agent"
status: BACKLOG
priority: {{ priority|default('MEDIUM') }}
complexity: {{ complexity|default(5) }}
created: {{ created_timestamp }}
updated: {{ created_timestamp }}
assignee: null
tags: [agent-enhancement, phase-8{% if template_name %}, {{ template_name }}{% endif %}]
related_tasks: []
estimated_duration: {{ estimated_duration|default('2-4 hours') }}
technologies: [{% for tech in technologies %}{{ tech }}{% if not loop.last %}, {% endif %}{% endfor %}]
---

# Enhance {{ agent_name }} Agent

## Context

This task enhances the `{{ agent_name }}` agent with:
- Code examples from template
- Best practices documentation
- Anti-patterns to avoid
- Integration guidance

**Agent File**: `{{ agent_file }}`
**Template**: `{{ template_name }}`
**Template Directory**: `{{ template_dir }}`

## Acceptance Criteria

### 1. Code Examples
- [ ] Add 3-5 code examples from template files
- [ ] Examples show best practices
- [ ] Examples are well-commented
- [ ] Examples cover common use cases

### 2. Best Practices Section
- [ ] Document recommended patterns
- [ ] Explain rationale for patterns
- [ ] Include performance considerations
- [ ] Link to relevant documentation

### 3. Anti-Patterns Section
- [ ] Document common mistakes
- [ ] Explain why they're problematic
- [ ] Show correct alternatives
- [ ] Include debugging tips

### 4. Integration Guidance
- [ ] How to use agent with /task-work
- [ ] When to invoke this agent
- [ ] Related agents to use with
- [ ] Example workflows

### 5. "Why This Agent Exists" Section
- [ ] Clear explanation of agent purpose
- [ ] Specific problems it solves
- [ ] Technologies it specializes in
- [ ] Value it provides to users

## Commands

```bash
# Option 1: Manual enhancement
/agent-enhance {{ agent_file }} {{ template_dir }}

# Option 2: Use with task workflow
/task-work {{ task_id }}
```

## Technical Details

**Enhancement Strategy**: {{ strategy|default('hybrid') }}
- Try AI-powered enhancement first
- Fall back to static enhancement if AI fails

**Technologies**:
{% for tech in technologies %}
- {{ tech }}
{% endfor %}

## Success Metrics

- [ ] Agent file has 3+ code examples
- [ ] Agent file has best practices section
- [ ] Agent file has anti-patterns section
- [ ] "Why This Exists" is meaningful (not circular)
- [ ] File compiles/validates

## Notes

{{ additional_notes|default('Generated by template-create Phase 8') }}
```

#### Step 2: Add Template Loader

```python
from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from pathlib import Path

class TemplateCreateOrchestrator:
    def __init__(self, ...):
        # ... existing init ...

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # We're generating markdown, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _load_task_template(self) -> Template:
        """Load agent enhancement task template.

        Returns:
            Template: Jinja2 template object

        Raises:
            TemplateNotFound: If template file doesn't exist
        """
        try:
            return self.jinja_env.get_template("agent_enhancement_task.md.j2")
        except TemplateNotFound:
            logger.error("Task template file not found")
            raise
```

#### Step 3: Render Template

```python
def _create_agent_enhancement_task(
    self,
    agent_name: str,
    agent_file: Path,
    template_dir: Path,
    template_name: str
) -> Optional[str]:
    """Creates individual task for agent enhancement.

    Args:
        agent_name: Name of agent
        agent_file: Path to agent markdown file
        template_dir: Path to template directory
        template_name: Name of template

    Returns:
        Optional[str]: Task ID if successful, None otherwise
    """
    # Generate task ID
    task_id = self._generate_task_id(agent_name)

    # Prepare template variables
    template_vars = {
        "task_id": task_id,
        "agent_name": agent_name,
        "agent_file": str(agent_file),
        "template_dir": str(template_dir),
        "template_name": template_name,
        "created_timestamp": datetime.datetime.now().isoformat(),
        "priority": "MEDIUM",
        "complexity": 5,
        "estimated_duration": "2-4 hours",
        "technologies": self._extract_technologies(agent_file),
        "strategy": "hybrid",
        "additional_notes": f"Generated by template-create for {template_name}",
    }

    # Render template
    try:
        template = self._load_task_template()
        task_content = template.render(**template_vars)
    except Exception as e:
        logger.error(f"Failed to render task template: {e}")
        return None

    # Write task file
    task_file = Path("tasks/backlog") / f"{task_id}.md"

    try:
        task_file.write_text(task_content)
        logger.info(f"Created task: {task_id}")
        return task_id
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create task {task_id}: {e}")
        return None

def _extract_technologies(self, agent_file: Path) -> list:
    """Extract technologies from agent frontmatter.

    Args:
        agent_file: Path to agent file

    Returns:
        list: List of technologies (e.g., ['python', 'fastapi'])
    """
    try:
        import frontmatter
        agent_doc = frontmatter.loads(agent_file.read_text())
        return agent_doc.metadata.get("technologies", [])
    except Exception:
        return []
```

### Benefits of Externalization

**Before** (Embedded):
```python
task_content = f"""
---
task_id: {task_id}
title: "Enhance {agent_name} Agent"
# ... 40 more lines
"""
```
- Hard to read
- No syntax highlighting
- Mixed concerns (code + template)
- Hard to version control diffs

**After** (External):
```python
template_vars = {"task_id": task_id, "agent_name": agent_name, ...}
task_content = template.render(**template_vars)
```
- Clean separation
- Syntax highlighting in .j2 file
- Easy to modify template
- Clear version control diffs

## Success Metrics

### Functional Tests
- [ ] Rendered output identical to current f-string
- [ ] All template variables populated correctly
- [ ] Missing optional variables use defaults
- [ ] Template syntax errors caught and reported

### Maintainability Tests
- [ ] Template file readable by non-programmers
- [ ] Template modifications don't require code changes
- [ ] Template can be tested independently
- [ ] Version control diffs show template changes clearly

### Error Handling
- [ ] Template file not found → clear error message
- [ ] Template syntax error → error with line number
- [ ] Missing required variable → clear error
- [ ] Handles unicode in variables

## Dependencies

**Related To**:
- TASK-FIX-4B2E (task creation workflow) - uses this template
- TASK-PHASE-8-INCREMENTAL (main implementation)

**Requires**:
- Jinja2 library (already in dependencies)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 2**: Code Quality Review - Medium Priority Issue #5
- **Lines 966-1009**: Task content as string literal
- **Section 6.1**: Could Fix #10 (1 hour estimate)

## Estimated Effort

**Duration**: 2 hours

**Breakdown**:
- Create template file (0.5 hours): Convert f-string to Jinja2
- Add template loader (0.5 hours): Setup Jinja2 environment
- Update task creation (0.5 hours): Use template rendering
- Testing (0.5 hours): Ensure identical output

## Test Plan

### Unit Tests

```python
def test_load_task_template():
    """Test template loading."""
    orchestrator = TemplateCreateOrchestrator()
    template = orchestrator._load_task_template()

    assert template is not None
    assert isinstance(template, Template)

def test_render_task_template():
    """Test template rendering with all variables."""
    orchestrator = TemplateCreateOrchestrator()
    template = orchestrator._load_task_template()

    vars = {
        "task_id": "TASK-TEST-12345678",
        "agent_name": "test-agent",
        "agent_file": "/path/to/agent.md",
        "template_dir": "/path/to/template",
        "template_name": "test-template",
        "created_timestamp": "2025-11-20T12:00:00",
        "technologies": ["python", "pytest"],
    }

    result = template.render(**vars)

    assert "TASK-TEST-12345678" in result
    assert "test-agent" in result
    assert "python" in result
    assert "pytest" in result

def test_render_task_template_with_defaults():
    """Test template rendering with missing optional variables."""
    orchestrator = TemplateCreateOrchestrator()
    template = orchestrator._load_task_template()

    # Minimal variables
    vars = {
        "task_id": "TASK-TEST-12345678",
        "agent_name": "test-agent",
        "agent_file": "/path/to/agent.md",
        "template_dir": "/path/to/template",
        "template_name": "test-template",
        "created_timestamp": "2025-11-20T12:00:00",
        "technologies": [],
    }

    result = template.render(**vars)

    # Should use defaults
    assert "priority: MEDIUM" in result
    assert "complexity: 5" in result

def test_task_content_matches_current():
    """Test that rendered template matches current f-string output."""
    orchestrator = TemplateCreateOrchestrator()

    # Capture current output
    current_output = orchestrator._create_agent_enhancement_task(
        agent_name="test-agent",
        agent_file=Path("/path/to/agent.md"),
        template_dir=Path("/path/to/template"),
        template_name="test-template"
    )

    # Should be identical (or at least functionally equivalent)
    assert "task_id:" in current_output
    assert "Enhance test-agent Agent" in current_output
```

### Integration Tests

```python
def test_template_create_with_external_template(tmp_path):
    """Test full template creation workflow with external template."""
    result = run_template_create(args=["--create-agent-tasks"])

    # Should create task files
    task_files = list(Path("tasks/backlog").glob("TASK-*.md"))
    assert len(task_files) > 0

    # Task content should be valid
    task_content = task_files[0].read_text()
    assert task_content.startswith("---")
    assert "task_id:" in task_content
```

## Notes

- **Priority**: MEDIUM - code quality improvement
- **Risk**: LOW - purely refactoring, no behavior change
- **Dependency**: Jinja2 already in requirements
- **Effort**: 1 hour per review, 2 hours for comprehensive solution

## Future Enhancements

### Template Variations
Once externalized, easy to create template variations:
- `agent_enhancement_task_simple.md.j2` (minimal version)
- `agent_enhancement_task_detailed.md.j2` (comprehensive version)
- Select template based on agent complexity

### Template Validation
Can add pre-render validation:
```python
def _validate_template_vars(self, vars: dict):
    """Validate required template variables are present."""
    required = ["task_id", "agent_name", "agent_file"]
    missing = [v for v in required if v not in vars]
    if missing:
        raise ValueError(f"Missing required variables: {missing}")
```
