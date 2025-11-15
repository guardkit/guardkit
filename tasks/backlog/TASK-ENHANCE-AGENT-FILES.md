# TASK-ENHANCE-AGENT-FILES: Connect Agents to Templates with AI-Powered Content

**Created**: 2025-11-15
**Priority**: Critical (Public Release Blocker)
**Type**: Documentation Enhancement / Quality Polish
**Status**: Backlog
**Complexity**: 3/10 (Medium-Low - Controlled AI enhancement)
**Estimated Effort**: 2-4 hours
**Dependencies**: TASK-CLAUDE-MD-AGENTS (should complete first)
**Blocks**: Public release (critical for first impressions)

---

## ⚠️ CRITICAL: AI-FIRST ARCHITECTURE REQUIREMENTS

**THIS TASK MUST FOLLOW AI-FIRST PRINCIPLES**

Before implementing ANYTHING, read these non-negotiable rules:

### 🚨 ABSOLUTELY FORBIDDEN 🚨

**DO NOT** write code like this:

```python
# ❌ FORBIDDEN - Hard-coded agent → template mappings
agent_templates = {
    'repository-pattern-specialist': [
        'ConfigurationRepository.cs.template',
        'DriverRepository.cs.template'
    ],
    'mvvm-specialist': [
        'ViewModel.cs.template'
    ]
}

# ❌ FORBIDDEN - Pattern matching on agent names
if 'repository' in agent_name.lower():
    templates = find_templates_with('Repository')
elif 'mvvm' in agent_name.lower():
    templates = find_templates_with('ViewModel')

# ❌ FORBIDDEN - Hard-coded content generation
if agent_name == 'repository-pattern-specialist':
    best_practices = [
        "Always use repository interfaces",
        "Keep repositories focused"
    ]
```

**WHY FORBIDDEN**: Hard-coding means:
- ❌ Won't work for new template types
- ❌ Won't work for different tech stacks
- ❌ Won't work for future agents
- ❌ Creates maintenance nightmare
- ❌ Defeats the entire purpose of AI-first architecture

### ✅ REQUIRED APPROACH ✅

**DO** write code like this:

```python
# ✅ REQUIRED - AI finds relevant templates
relevant_templates = ai_analyze(f"""
    Agent Name: {agent_name}
    Agent Description: {agent_description}
    Agent Technologies: {agent_technologies}
    
    Available Templates:
    {list_all_template_files()}
    
    Which templates are most relevant to this agent's expertise?
    Consider:
    - File names that match agent technologies
    - Patterns that match agent description
    - Code that demonstrates agent's domain
    
    Return JSON: {{"templates": [{{"path": "...", "relevance": "why relevant"}}]}}
""")

# ✅ REQUIRED - AI generates content based on actual templates
enhanced_content = ai_generate(f"""
    Agent: {agent_name}
    Related Templates: {relevant_templates}
    Template Contents: {read_template_contents(relevant_templates)}
    
    Generate documentation sections:
    1. When to Use (based on what the templates show)
    2. Related Templates (link to actual templates with explanations)
    3. Example Pattern (reference best example from templates)
    4. Best Practices (based on patterns in the templates)
    
    Base ALL content on the actual templates provided, not generic advice.
""")
```

**WHY REQUIRED**: AI approach means:
- ✅ Works for ANY agent type
- ✅ Works for ANY template structure
- ✅ Works for ANY technology stack
- ✅ Zero maintenance
- ✅ Content based on actual code

---

## Problem Statement

**Current State**: Agent files are functional but generic, disconnected from the 17 template files.

**Impact on Public Release**:
- ❌ Users won't discover which templates to use
- ❌ Templates appear disconnected from agents
- ❌ No learning examples from actual code
- ❌ Looks unfinished/low quality
- ❌ Poor first impression

**Example - Current Agent File**:

```markdown
---
name: repository-pattern-specialist
---

## Purpose
Repository pattern with Realm database abstraction and data access layers

## Why This Agent Exists
Specialized agent for repository pattern specialist

## Usage
This agent is automatically invoked during `/task-work` when working on repository pattern specialist implementations.
```

**Problems**:
1. ❌ Doesn't mention ConfigurationRepository.cs.template
2. ❌ Doesn't mention DriverRepository.cs.template
3. ❌ Doesn't mention LoadingRepository.cs.template
4. ❌ No code examples
5. ❌ No specific guidance
6. ❌ Generic boilerplate

**Goal**: Transform agents into rich, template-connected documentation that helps developers understand and use the templates effectively.

---

## Desired End State

**Enhanced Agent File Example**:

```markdown
---
name: repository-pattern-specialist
description: Repository pattern with Realm database abstraction and data access layers
priority: 10
technologies:
  - C#
  - Repository Pattern
  - Realm Database
  - Data Access
---

# Repository Pattern Specialist

## Purpose

Implements repository pattern with Realm database abstraction for mobile-first data access, providing a clean separation between business logic and data persistence layers.

## When to Use This Agent

Use this agent when:

1. **Creating Data Access Layers** - Implementing new repositories for entity persistence
2. **Working with Realm Database** - Building offline-first mobile data architectures
3. **Repository Refactoring** - Improving or modernizing existing data access patterns
4. **CRUD Operations** - Implementing Create, Read, Update, Delete with proper abstraction

## Related Templates

This template includes repository examples you can reference:

### Primary Examples

**`templates/other/ConfigurationRepository.cs.template`** - Configuration data access
- Demonstrates: Repository interface pattern, Realm integration, async CRUD operations
- Use for: Application configuration, settings management, feature flags
- Key Pattern: Single-entity repository with typed queries

**`templates/other/DriverRepository.cs.template`** - Driver entity repository  
- Demonstrates: Entity-specific repository, complex queries, relationship handling
- Use for: Domain entity repositories, business object persistence
- Key Pattern: Rich domain model with repository abstraction

**`templates/other/LoadingRepository.cs.template`** - Loading entity repository
- Demonstrates: Transaction management, bulk operations, error handling
- Use for: High-volume data operations, batch processing
- Key Pattern: ErrorOr integration for functional error handling

## Example Pattern

Here's the repository pattern as implemented in this template:

```csharp
// From ConfigurationRepository.cs.template
public interface I{{Namespace}}Repository
{
    Task<ErrorOr<{{Entity}}>> GetByIdAsync(string id);
    Task<ErrorOr<IEnumerable<{{Entity}}>>> GetAllAsync();
    Task<ErrorOr<{{Entity}}>> CreateAsync({{Entity}} entity);
    Task<ErrorOr<{{Entity}}>> UpdateAsync({{Entity}} entity);
    Task<ErrorOr<bool>> DeleteAsync(string id);
}

public class {{Namespace}}Repository : I{{Namespace}}Repository
{
    private readonly Realm _realm;
    
    public {{Namespace}}Repository(Realm realm)
    {
        _realm = realm;
    }
    
    public async Task<ErrorOr<{{Entity}}>> GetByIdAsync(string id)
    {
        // Realm query with error handling
        // See ConfigurationRepository.cs.template for full implementation
    }
}
```

**Key Features**:
- Interface for testability and dependency injection
- Async/await for non-blocking operations
- ErrorOr pattern for functional error handling
- Realm database integration
- Clean separation of concerns

## Best Practices

Based on the patterns in this template:

1. **Interface Segregation** - Always define repository interfaces for testability
   - Example: `IConfigurationRepository`, `IDriverRepository`
   - Benefit: Easy mocking in tests, DI-friendly

2. **Single Entity Focus** - One repository per aggregate root
   - Example: ConfigurationRepository handles Configuration entity only
   - Benefit: Clear responsibilities, easier to maintain

3. **Async by Default** - All database operations should be asynchronous
   - Pattern: `Task<ErrorOr<T>>` return types
   - Benefit: Non-blocking UI, better performance

4. **ErrorOr Integration** - Use functional error handling over exceptions
   - Pattern: Return `ErrorOr<Result>` instead of throwing
   - Benefit: Explicit error handling, type-safe errors

5. **Realm Best Practices** - Follow Realm-specific patterns
   - Use Realm queries efficiently
   - Manage transactions properly  
   - Consider in-memory Realm for testing

## Technologies

- **C#** - Primary language
- **Repository Pattern** - Data access abstraction
- **Realm Database** - Mobile-first embedded database
- **ErrorOr** - Functional error handling library
- **.NET MAUI** - Cross-platform framework

## Usage in Taskwright

This agent is automatically invoked during `/task-work` when:
- Task involves data access or persistence
- Creating new repository classes
- Working with Realm database
- Implementing CRUD operations

To manually use this agent:
```bash
# Reference in task description
/task-create "Implement UserRepository with Realm persistence"

# Agent will be selected based on keywords: Repository, Realm, persistence
```

## Common Scenarios

### Scenario 1: Creating a New Repository

```bash
/task-create "Create ProductRepository with CRUD operations"

# Agent provides:
# - Repository interface pattern from templates
# - Realm integration guidance
# - ErrorOr error handling
# - Async operation patterns
```

### Scenario 2: Refactoring Existing Data Access

```bash
/task-create "Refactor OrderDataService to use repository pattern"

# Agent provides:
# - Migration path from direct DB access to repository
# - Interface extraction guidance
# - Testing strategy with repository mocks
```

### Scenario 3: Adding Complex Queries

```bash
/task-create "Add GetActiveDriversForRoute query to DriverRepository"

# Agent provides:
# - Realm query patterns from DriverRepository.cs.template
# - Performance optimization guidance
# - Error handling for query failures
```

## See Also

- **Configuration Templates**: ConfigurationEngine.cs.template, ConfigurationService.cs.template
- **Related Agents**: realm-database-specialist, error-handling-specialist
- **Testing**: xunit-nsubstitute-specialist for repository testing
```

---

## Implementation Plan

### Phase 1: Setup and Safety Checks (10 min)

**File**: `installer/global/lib/template_creation/agent_enhancer.py` (NEW FILE)

**Purpose**: Create dedicated module for agent enhancement (keeps code isolated and testable)

**Safety Check Function**:

```python
def validate_no_hard_coding(code: str) -> tuple[bool, list[str]]:
    """
    Validate that code doesn't contain hard-coded mappings.
    
    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    
    # Check for hard-coded agent names
    if re.search(r'["\']repository["\'].*:', code):
        violations.append("Hard-coded agent name mapping detected")
    
    # Check for hard-coded template names
    if re.search(r'agent_templates\s*=\s*{', code):
        violations.append("Hard-coded agent_templates dictionary detected")
    
    # Check for pattern matching on agent names
    if re.search(r'if.*agent_name.*\.lower\(\).*in', code):
        violations.append("Pattern matching on agent_name detected")
    
    # Check for template name matching
    if re.search(r'if.*["\']Repository["\'].*in.*template', code):
        violations.append("Hard-coded template pattern matching detected")
    
    return (len(violations) == 0, violations)
```

**Pre-Implementation Check**:
```python
# Before any enhancement, verify approach
approach_code = """
# Your implementation approach here
"""

is_valid, violations = validate_no_hard_coding(approach_code)
if not is_valid:
    raise ValueError(f"AI-First violation detected: {violations}")
```

### Phase 2: AI Template Discovery (30 min)

**Function**: Find templates relevant to each agent using AI

```python
from pathlib import Path
from typing import Dict, List
import json

class AgentEnhancer:
    """Enhance agent files with template references using AI."""
    
    def __init__(self, ai_client):
        self.ai = ai_client
    
    def find_relevant_templates(
        self,
        agent_metadata: Dict[str, any],
        all_templates: List[Path]
    ) -> List[Dict[str, str]]:
        """
        Use AI to find templates relevant to this agent.
        
        Args:
            agent_metadata: Agent name, description, technologies
            all_templates: List of all template file paths
            
        Returns:
            [
                {
                    "path": "templates/other/ConfigurationRepository.cs.template",
                    "relevance": "Demonstrates repository pattern with Realm",
                    "priority": "primary"
                }
            ]
        """
        
        # Create template listing for AI
        template_list = "\n".join([
            f"- {t.relative_to(template_root)}"
            for t in all_templates
        ])
        
        prompt = f"""
You are analyzing which code templates are relevant to a specialized AI agent.

**Agent Information:**
- Name: {agent_metadata['name']}
- Description: {agent_metadata['description']}
- Technologies: {', '.join(agent_metadata.get('technologies', []))}

**Available Templates:**
{template_list}

**Your Task:**
Identify which templates are most relevant to this agent's expertise.

**Matching Criteria:**
1. **Technology Match** - Template uses agent's technologies
2. **Pattern Match** - Template demonstrates patterns in agent description
3. **Name Match** - Template name suggests relevance (e.g., "Repository" for repository-pattern agent)
4. **Code Content** - Template would be useful for someone learning this agent's domain

**Priority Levels:**
- "primary" - Perfect example, must include (2-3 templates)
- "secondary" - Helpful reference, nice to have (1-3 templates)
- "tertiary" - Tangentially related, optional (0-2 templates)

**Response Format:**
Return ONLY valid JSON (no markdown, no explanation):

{{
  "templates": [
    {{
      "path": "templates/other/ConfigurationRepository.cs.template",
      "relevance": "One sentence explaining why this template is relevant",
      "priority": "primary"
    }}
  ]
}}

**Important:**
- Base relevance on ACTUAL template paths provided
- Do NOT invent template paths
- If no templates match, return empty array
- Focus on top 3-5 most relevant templates
"""

        response = self.ai.generate(
            prompt=prompt,
            system_prompt="You are a technical documentation expert. Respond ONLY with valid JSON matching the exact format requested.",
            max_tokens=1000
        )
        
        # Parse JSON response
        try:
            result = json.loads(response)
            return result.get('templates', [])
        except json.JSONDecodeError:
            # Fallback: No templates if JSON parsing fails
            print(f"Warning: Could not parse AI response for {agent_metadata['name']}")
            return []
```

**Critical**: This function has ZERO hard-coding. AI decides relevance.

### Phase 3: Read Template Contents (15 min)

**Function**: Read actual template file contents for AI to analyze

```python
def read_template_contents(
    self,
    template_paths: List[str],
    max_lines_per_template: int = 50
) -> str:
    """
    Read template file contents for AI analysis.
    
    Args:
        template_paths: List of template file paths
        max_lines_per_template: Limit lines per template (prevent token overflow)
        
    Returns:
        Formatted string with template contents
    """
    contents = []
    
    for path in template_paths[:5]:  # Limit to top 5 templates
        try:
            full_path = self.template_root / path
            if not full_path.exists():
                continue
                
            lines = full_path.read_text().splitlines()
            
            # Truncate if too long
            if len(lines) > max_lines_per_template:
                lines = lines[:max_lines_per_template]
                lines.append("... (truncated)")
            
            content = "\n".join(lines)
            
            contents.append(f"""
**Template: {path}**
```
{content}
```
""")
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}")
            continue
    
    return "\n\n".join(contents)
```

### Phase 4: AI Content Generation (45 min)

**Function**: Generate enhanced agent content based on templates

```python
def generate_enhanced_content(
    self,
    agent_metadata: Dict[str, any],
    relevant_templates: List[Dict[str, str]]
) -> str:
    """
    Use AI to generate enhanced agent documentation.
    
    Args:
        agent_metadata: Agent name, description, technologies
        relevant_templates: Templates found in Phase 2
        
    Returns:
        Enhanced markdown content for agent file
    """
    
    # Read template contents
    template_paths = [t['path'] for t in relevant_templates if t['priority'] == 'primary']
    template_contents = self.read_template_contents(template_paths)
    
    # Build template summary for AI
    template_summary = "\n".join([
        f"- **{t['path']}**: {t['relevance']} (Priority: {t['priority']})"
        for t in relevant_templates
    ])
    
    prompt = f"""
You are writing documentation for a specialized AI coding agent.

**Agent Information:**
- Name: {agent_metadata['name']}
- Description: {agent_metadata['description']}
- Technologies: {', '.join(agent_metadata.get('technologies', []))}

**Related Templates:**
{template_summary}

**Template Code Examples:**
{template_contents}

**Your Task:**
Generate comprehensive documentation sections for this agent file.

**Required Sections:**

1. **Purpose** (1-2 sentences)
   - Concise description of what this agent helps with
   - Should expand on the basic description with more context

2. **When to Use This Agent** (3-4 scenarios)
   - Specific development scenarios when this agent is useful
   - Base scenarios on what the templates demonstrate
   - Format as numbered list with scenario names

3. **Related Templates** (Primary templates section)
   - List primary templates with explanations
   - For each template, explain: what it demonstrates, when to use it, key pattern
   - Use actual template paths provided

4. **Example Pattern** (Code example)
   - Show a key code pattern from the best template
   - Include code snippet with {{{{placeholders}}}}
   - Explain key features

5. **Best Practices** (3-5 practices)
   - Extract best practices from the template code
   - Base on actual patterns in templates, not generic advice
   - Include examples where helpful

**CRITICAL REQUIREMENTS:**
- Base ALL content on the actual templates provided
- Use ONLY the template paths given (don't invent paths)
- Extract patterns from the actual template code
- Be specific and actionable, not generic
- Include code examples with proper placeholders

**Format:**
Return the sections in markdown format, properly formatted for inclusion in agent file.
Use proper markdown headings (##), code blocks with language tags, and lists.
"""

    response = self.ai.generate(
        prompt=prompt,
        system_prompt="""You are a technical writer creating developer documentation. 
        Your content must be:
        1. Based on actual code provided
        2. Specific and actionable
        3. Properly formatted markdown
        4. Accurate to the templates shown""",
        max_tokens=2000
    )
    
    return response
```

**Validation**: Content must reference actual templates, not invented ones.

### Phase 5: Assembly and Validation (20 min)

**Function**: Combine all sections into enhanced agent file

```python
def enhance_agent_file(
    self,
    agent_file: Path,
    all_templates: List[Path]
) -> bool:
    """
    Enhance a single agent file with template references.
    
    Args:
        agent_file: Path to agent markdown file
        all_templates: List of all available templates
        
    Returns:
        True if successful, False otherwise
    """
    
    # Read existing agent metadata
    agent_metadata = self._read_frontmatter(agent_file)
    
    # Find relevant templates (AI-powered)
    relevant_templates = self.find_relevant_templates(
        agent_metadata,
        all_templates
    )
    
    if not relevant_templates:
        print(f"No relevant templates found for {agent_metadata['name']}")
        # Keep existing file unchanged
        return False
    
    # Generate enhanced content (AI-powered)
    enhanced_content = self.generate_enhanced_content(
        agent_metadata,
        relevant_templates
    )
    
    # Validate content references actual templates
    for template in relevant_templates:
        if template['priority'] == 'primary':
            if template['path'] not in enhanced_content:
                print(f"Warning: Primary template {template['path']} not referenced in content")
    
    # Build final agent file
    final_content = f"""---
name: {agent_metadata['name']}
description: {agent_metadata['description']}
priority: {agent_metadata.get('priority', 7)}
technologies:
{self._format_yaml_list(agent_metadata.get('technologies', []))}
---

# {self._format_title(agent_metadata['name'])}

{enhanced_content}

## Technologies

{self._format_bullet_list(agent_metadata.get('technologies', []))}

## Usage in Taskwright

This agent is automatically invoked during `/task-work` when the task involves {agent_metadata['name'].replace('-', ' ')}.
"""
    
    # Write enhanced file
    agent_file.write_text(final_content)
    
    return True
```

### Phase 6: Batch Processing (15 min)

**Function**: Process all agents in a template

```python
def enhance_all_agents(
    self,
    template_dir: Path
) -> Dict[str, bool]:
    """
    Enhance all agent files in a template directory.
    
    Args:
        template_dir: Root directory of template
        
    Returns:
        {agent_name: success_status}
    """
    
    self.template_root = template_dir
    agents_dir = template_dir / "agents"
    templates_dir = template_dir / "templates"
    
    if not agents_dir.exists():
        print(f"No agents directory in {template_dir}")
        return {}
    
    # Get all agent files
    agent_files = list(agents_dir.glob("*.md"))
    
    # Get all template files
    all_templates = list(templates_dir.rglob("*.template"))
    
    print(f"Found {len(agent_files)} agents and {len(all_templates)} templates")
    
    results = {}
    
    for agent_file in agent_files:
        agent_name = agent_file.stem
        print(f"\nEnhancing {agent_name}...")
        
        try:
            success = self.enhance_agent_file(agent_file, all_templates)
            results[agent_name] = success
            
            if success:
                print(f"  ✓ Enhanced successfully")
            else:
                print(f"  ⚠ No templates found, kept original")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[agent_name] = False
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    print(f"\n{'='*60}")
    print(f"Enhanced {successful}/{len(results)} agents successfully")
    
    return results
```

---

## Integration Point

**Where to call from**: During template creation, AFTER agents are generated

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Integration** (in Phase 7 - after agent generation):

```python
# In template_create_orchestrator.py, after agent generation

def _phase7_enhance_agents(self) -> None:
    """Phase 7: Enhance agent files with template references."""
    
    print("\n" + "=" * 60)
    print("  Phase 7: Agent Enhancement")
    print("=" * 60)
    
    from installer.global.lib.template_creation.agent_enhancer import AgentEnhancer
    from installer.global.lib.ai.ai_client import AIClient
    
    # Initialize enhancer
    ai_client = AIClient()
    enhancer = AgentEnhancer(ai_client)
    
    # Enhance all agents
    results = enhancer.enhance_all_agents(
        self.config.output_path
    )
    
    # Report
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    if successful == total:
        print(f"✅ All {total} agents enhanced successfully")
    else:
        print(f"⚠️  Enhanced {successful}/{total} agents")
```

---

## Testing Requirements

### Test 1: No Hard-Coding Validation

**Purpose**: Ensure no hard-coded mappings exist

```python
def test_no_hard_coding():
    """Verify implementation uses AI, not hard-coding."""
    
    # Read agent_enhancer.py source
    source_code = Path("installer/global/lib/template_creation/agent_enhancer.py").read_text()
    
    # Check for forbidden patterns
    is_valid, violations = validate_no_hard_coding(source_code)
    
    assert is_valid, f"Hard-coding detected: {violations}"
    
    # Verify AI methods are used
    assert "ai.generate(" in source_code, "No AI generation found"
    assert "find_relevant_templates" in source_code, "Missing AI template discovery"
```

### Test 2: Template Discovery Works

**Purpose**: Verify AI correctly identifies relevant templates

```python
def test_template_discovery():
    """Test AI finds correct templates for agent."""
    
    enhancer = AgentEnhancer(ai_client)
    
    # Test repository agent
    agent_metadata = {
        'name': 'repository-pattern-specialist',
        'description': 'Repository pattern with Realm database',
        'technologies': ['C#', 'Repository Pattern', 'Realm']
    }
    
    templates = [
        Path("templates/other/ConfigurationRepository.cs.template"),
        Path("templates/other/DriverRepository.cs.template"),
        Path("templates/other/DomainCameraView.cs.template"),  # Should NOT match
    ]
    
    relevant = enhancer.find_relevant_templates(agent_metadata, templates)
    
    # Should find repository templates
    paths = [t['path'] for t in relevant]
    assert 'ConfigurationRepository.cs.template' in str(paths)
    assert 'DriverRepository.cs.template' in str(paths)
    
    # Should NOT find camera view
    assert 'DomainCameraView' not in str(paths)
```

### Test 3: Content Quality

**Purpose**: Verify generated content references templates

```python
def test_content_references_templates():
    """Verify AI content includes template references."""
    
    enhancer = AgentEnhancer(ai_client)
    
    relevant_templates = [
        {
            'path': 'templates/other/ConfigurationRepository.cs.template',
            'relevance': 'Repository pattern example',
            'priority': 'primary'
        }
    ]
    
    content = enhancer.generate_enhanced_content(
        agent_metadata={'name': 'test-agent', 'description': 'Test'},
        relevant_templates=relevant_templates
    )
    
    # Must reference the template
    assert 'ConfigurationRepository.cs.template' in content
    
    # Must have required sections
    assert '## When to Use' in content
    assert '## Related Templates' in content
    assert '## Example Pattern' in content
    assert '## Best Practices' in content
```

### Test 4: End-to-End

**Purpose**: Verify full workflow produces quality output

```bash
# Create test template
cd ~/Projects/appmilla_github/taskwright
/template-create --name test-enhanced --validate

# Check agent files are enhanced
cat ~/.agentecflow/templates/test-enhanced/agents/repository-pattern-specialist.md

# Verify:
# ✅ Has "Related Templates" section
# ✅ References actual template files
# ✅ Includes code examples
# ✅ Has specific "When to Use" scenarios
# ✅ Lists best practices from templates
```

---

## Quality Gates

### Gate 1: Pre-Implementation Review

**Before writing code**, create implementation plan and verify:

- [ ] Plan uses AI for template discovery (not hard-coded mappings)
- [ ] Plan uses AI for content generation (not hard-coded templates)
- [ ] No pattern matching on agent names
- [ ] No template name hard-coding
- [ ] Passes `validate_no_hard_coding()` check

### Gate 2: Code Review

**After implementation**, verify:

- [ ] `agent_enhancer.py` has zero hard-coded mappings
- [ ] All template discovery uses AI
- [ ] All content generation uses AI
- [ ] Unit tests pass (all 4 tests)
- [ ] Code follows AI-first principles

### Gate 3: Output Quality

**After test run**, verify:

- [ ] Agent files reference actual templates
- [ ] Content is specific (not generic)
- [ ] Code examples from real templates
- [ ] "When to Use" scenarios are actionable
- [ ] Best practices based on template patterns

---

## Acceptance Criteria

### Functional Requirements

- [ ] All agents enhanced (12/12 for MyDrive example)
- [ ] Each agent references 2-5 relevant templates
- [ ] Content includes code examples from templates
- [ ] "When to Use" section has specific scenarios
- [ ] "Best Practices" extracted from actual code
- [ ] Works for ANY template structure (not hard-coded)

### Quality Requirements

- [ ] Content quality: 8+/10 (specific, actionable)
- [ ] Template references: 100% accurate (no invented paths)
- [ ] Code examples: From actual templates
- [ ] Formatting: Proper markdown
- [ ] Consistency: Similar format across all agents

### AI-First Requirements (CRITICAL)

- [ ] ✅ Uses AI for template discovery
- [ ] ✅ Uses AI for content generation
- [ ] ✅ Zero hard-coded agent → template mappings
- [ ] ✅ Zero pattern matching on names
- [ ] ✅ Passes `validate_no_hard_coding()` check
- [ ] ✅ Extensible to new agent types
- [ ] ✅ Extensible to new template structures

---

## Expected Output Examples

### Before Enhancement

```markdown
---
name: repository-pattern-specialist
---

## Purpose
Repository pattern with Realm database abstraction and data access layers

## Usage
This agent is automatically invoked during `/task-work`.
```

**Rating**: 3/10 - Minimal, generic

### After Enhancement

```markdown
---
name: repository-pattern-specialist
---

# Repository Pattern Specialist

## Purpose

Implements repository pattern with Realm database abstraction for mobile-first data access, providing clean separation between business logic and data persistence layers.

## When to Use This Agent

Use this agent when:

1. **Creating Data Access Layers** - Implementing new repositories for entity persistence
2. **Working with Realm Database** - Building offline-first mobile data architectures  
3. **Repository Refactoring** - Improving or modernizing existing data access patterns
4. **CRUD Operations** - Implementing Create, Read, Update, Delete with proper abstraction

## Related Templates

### Primary Examples

**`templates/other/ConfigurationRepository.cs.template`**
- **Demonstrates**: Repository interface pattern, Realm integration, async CRUD
- **Use for**: Application configuration, settings management, feature flags
- **Key Pattern**: Single-entity repository with typed queries

**`templates/other/DriverRepository.cs.template`**
- **Demonstrates**: Entity-specific repository, complex queries, relationships
- **Use for**: Domain entity repositories, business object persistence
- **Key Pattern**: Rich domain model with repository abstraction

## Example Pattern

```csharp
// From ConfigurationRepository.cs.template
public interface I{{Namespace}}Repository
{
    Task<ErrorOr<{{Entity}}>> GetByIdAsync(string id);
    Task<ErrorOr<{{Entity}}>> CreateAsync({{Entity}} entity);
}

public class {{Namespace}}Repository : I{{Namespace}}Repository
{
    private readonly Realm _realm;
    
    public async Task<ErrorOr<{{Entity}}>> GetByIdAsync(string id)
    {
        // Implementation from template
    }
}
```

## Best Practices

1. **Interface Segregation** - Always define repository interfaces
   - Example: `IConfigurationRepository` for testability
   
2. **Single Entity Focus** - One repository per aggregate root
   - Example: ConfigurationRepository handles Configuration only

3. **Async by Default** - All database operations asynchronous
   - Pattern: `Task<ErrorOr<T>>` return types

4. **ErrorOr Integration** - Functional error handling over exceptions
   - Benefit: Explicit error handling, type-safe errors

## Usage in Taskwright

This agent is automatically invoked when working with repository patterns and data access.
```

**Rating**: 9/10 - Comprehensive, specific, template-connected

---

## Success Metrics

### Quantitative

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Content Quality | 3/10 | 9/10 | ≥8/10 |
| Template References | 0 | 2-5 per agent | ≥2 |
| Code Examples | 0 | 1-2 per agent | ≥1 |
| Specific Scenarios | 0 | 3-4 per agent | ≥3 |
| Best Practices | 0 | 3-5 per agent | ≥3 |

### Qualitative

**User Experience**:
- ✅ Developers know which templates to use
- ✅ Clear examples from actual code
- ✅ Actionable guidance
- ✅ Professional first impression

**Public Release Readiness**:
- ✅ Templates appear complete and polished
- ✅ Documentation is self-contained
- ✅ No "unfinished" feeling
- ✅ Competitive with commercial tools

---

## Risk Mitigation

### Risk 1: Going Off-Rails (Like TASK-9039)

**Mitigation**:
- ✅ Explicit AI-first requirements in task
- ✅ `validate_no_hard_coding()` pre-check
- ✅ Code review gate before merging
- ✅ Example of what NOT to do clearly shown

### Risk 2: AI Invents Template Paths

**Mitigation**:
- ✅ Provide actual template list to AI
- ✅ Validation: Content must reference provided templates
- ✅ Warning if primary templates not referenced

### Risk 3: Generic Content (Not Template-Specific)

**Mitigation**:
- ✅ AI receives template contents, not just names
- ✅ Prompt emphasizes "base on actual templates"
- ✅ Quality check: Content must include code examples

### Risk 4: Performance (AI Calls Per Agent)

**Mitigation**:
- ✅ Acceptable: 2 AI calls per agent (discovery + generation)
- ✅ Total: 24 AI calls for 12 agents (~2-3 minutes)
- ✅ One-time cost during template creation

---

## Timeline

| Phase | Description | Time |
|-------|-------------|------|
| 1 | Setup & safety checks | 10 min |
| 2 | AI template discovery | 30 min |
| 3 | Read template contents | 15 min |
| 4 | AI content generation | 45 min |
| 5 | Assembly & validation | 20 min |
| 6 | Batch processing | 15 min |
| **Implementation Total** | | **2 hrs 15 min** |
| Testing | Unit + integration tests | 30 min |
| Manual Verification | Check output quality | 15 min |
| **Total** | | **3 hours** |

---

## Checklist for Implementation

### Before Starting

- [ ] Read entire task specification
- [ ] Understand AI-first requirements
- [ ] Review "ABSOLUTELY FORBIDDEN" section
- [ ] Plan implementation approach
- [ ] Verify approach with `validate_no_hard_coding()`

### During Implementation

- [ ] Create `agent_enhancer.py` file
- [ ] Implement template discovery (AI-powered)
- [ ] Implement content generation (AI-powered)
- [ ] Add validation checks
- [ ] Write unit tests
- [ ] Test on real template

### After Implementation

- [ ] Run `validate_no_hard_coding()` on source
- [ ] Verify all tests pass
- [ ] Create test template
- [ ] Manually review agent files
- [ ] Check for hard-coded mappings
- [ ] Verify quality (8+/10)

### Before Committing

- [ ] No hard-coded agent → template mappings
- [ ] No pattern matching on agent names
- [ ] AI used for all content generation
- [ ] Tests pass
- [ ] Manual review shows quality output
- [ ] Ready for public release

---

## Related Tasks

- **TASK-CLAUDE-MD-AGENTS** - Populates CLAUDE.md sections (prerequisite)
- **TASK-AI-FIRST-GUIDELINES** - Architecture principles (reference)
- **TASK-AI-FIRST-AUDIT** - Code quality checks (validation)

---

## Post-Completion Verification

After completing this task, verify:

```bash
# 1. Create new template
/template-create --name verification-test --validate

# 2. Check agent quality
cat ~/.agentecflow/templates/verification-test/agents/repository-pattern-specialist.md

# 3. Verify contains:
# ✅ "Related Templates" section with 2-5 templates
# ✅ Code examples from actual templates
# ✅ Specific "When to Use" scenarios  
# ✅ Best practices from template patterns
# ✅ No generic boilerplate

# 4. Quality score
# Expected: 8-9/10 (compared to 3/10 before)
```

---

**Document Status**: Ready for Implementation  
**Critical for**: Public Release (First Impressions)  
**AI-First**: ✅ 100% (Zero hard-coding allowed)  
**Estimated Impact**: Transform agent quality from 3/10 to 9/10
