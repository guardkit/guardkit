# TASK-CLAUDE-MD-AGENTS: Populate Agent Sections in CLAUDE.md

**Created**: 2025-11-15
**Priority**: High
**Type**: Documentation Enhancement
**Status**: Backlog
**Complexity**: 2/10 (Simple - AI extraction and formatting)
**Estimated Effort**: 30 minutes - 1 hour
**Dependencies**: None (works with current template structure)
**Related**: Template-create golden commit (03144d8)

---

## Problem Statement

The CLAUDE.md file in generated templates has empty "Purpose" and incomplete "When to Use" sections for all agents. The information exists in the agent .md files but isn't being extracted and formatted into CLAUDE.md.

**Current State (CLAUDE.md)**:
```markdown
### repository-pattern-specialist
**Purpose**: 

**When to Use**: Use this agent for tasks related to 
```

**Desired State**:
```markdown
### repository-pattern-specialist
**Purpose**: Repository pattern with Realm database abstraction and data access layers

**When to Use**: Use this agent when implementing data access layers, working with Realm database persistence, creating repository interfaces, or building offline-first mobile data architectures
```

**Goal**: Populate all agent sections in CLAUDE.md with accurate, helpful information extracted from the agent files.

---

## Context

**Template Structure**:
```
~/.agentecflow/templates/{template-name}/
├── CLAUDE.md (has agent sections to populate)
├── agents/
│   ├── maui-mvvm-specialist.md (has description/technologies)
│   ├── repository-pattern-specialist.md
│   └── ... (12 agents total)
└── templates/ (template files)
```

**Agent File Structure**:
```markdown
---
name: repository-pattern-specialist
description: Repository pattern with Realm database abstraction and data access layers
priority: 7
technologies:
  - C#
  - Repository Pattern
  - Realm Database
  - Data Access
---

# Repository Pattern Specialist

## Purpose
Repository pattern with Realm database abstraction and data access layers
```

**Current Issue**: CLAUDE.md generator creates agent section placeholders but doesn't fill them in.

---

## Objectives

### Primary Objective
Update CLAUDE.md in all generated templates to have complete, accurate "Purpose" and "When to Use" sections for every agent.

### Success Criteria
- [ ] All agent sections in CLAUDE.md have non-empty "Purpose"
- [ ] All agent sections have specific, actionable "When to Use" guidance
- [ ] Information accurately reflects the agent's actual capabilities
- [ ] Format is consistent across all agents
- [ ] Uses AI to generate "When to Use" based on agent description and technologies
- [ ] No hard-coded mappings or pattern matching
- [ ] Works for ANY set of agents (extensible)

---

## AI-First Approach

**CRITICAL**: This task MUST use AI to extract and format information, NOT hard-coded Python logic.

### Why AI-First?

**DO NOT**:
```python
# ❌ BAD - Hard-coded pattern matching
if 'repository' in agent_name.lower():
    purpose = "Data access and persistence"
elif 'mvvm' in agent_name.lower():
    purpose = "MVVM architecture patterns"
# etc... (maintenance nightmare)
```

**DO**:
```python
# ✅ GOOD - AI extracts and formats
agent_info = read_agent_file(agent_path)
enhanced_info = ai_analyze(f"""
    Agent: {agent_info['name']}
    Description: {agent_info['description']}
    Technologies: {agent_info['technologies']}
    
    Generate:
    1. Concise 1-sentence "Purpose" summary
    2. Specific "When to Use" guidance (2-3 scenarios)
    
    Format as JSON.
""")
```

---

## Implementation Scope

### Phase 1: Read Agent Files (5 min)

**File**: `installer/global/lib/template_creation/claude_md_generator.py`

**Function**: Add method to read agent metadata

```python
def _read_agent_metadata(self, agent_file: Path) -> Dict[str, Any]:
    """
    Read agent frontmatter and extract metadata.
    
    Returns:
        {
            'name': 'repository-pattern-specialist',
            'description': 'Repository pattern with Realm...',
            'technologies': ['C#', 'Repository Pattern', ...],
            'priority': 7
        }
    """
    import yaml
    
    content = agent_file.read_text()
    
    # Extract frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter
    
    return {}
```

### Phase 2: AI Enhancement (10 min)

**Function**: Use AI to generate "When to Use" guidance

```python
def _enhance_agent_info(self, agent_metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Use AI to generate enhanced agent documentation.
    
    Args:
        agent_metadata: Basic metadata from agent file
        
    Returns:
        {
            'purpose': 'One-sentence summary',
            'when_to_use': 'Specific usage scenarios'
        }
    """
    from installer.global.lib.ai.ai_client import AIClient
    
    ai = AIClient()
    
    prompt = f"""
    Generate documentation for a specialized AI agent:
    
    Agent Name: {agent_metadata['name']}
    Description: {agent_metadata['description']}
    Technologies: {', '.join(agent_metadata.get('technologies', []))}
    
    Generate:
    1. **Purpose**: A concise 1-sentence summary (use the description as base)
    2. **When to Use**: 2-3 specific scenarios when developers should use this agent
    
    Format your response as JSON:
    {{
        "purpose": "...",
        "when_to_use": "Use this agent when: (1) scenario one, (2) scenario two, (3) scenario three"
    }}
    
    Make "When to Use" specific and actionable. Focus on concrete development tasks.
    
    Examples of good "When to Use":
    - "Use this agent when implementing data access layers, creating repository interfaces, working with database migrations, or building offline-first persistence"
    - "Use this agent when creating ViewModels, implementing data binding, handling property change notifications, or building MVVM-based UI components"
    
    Respond ONLY with valid JSON.
    """
    
    response = ai.generate(
        prompt=prompt,
        system_prompt="You generate clear, actionable documentation for development tools. Output ONLY valid JSON.",
        max_tokens=500
    )
    
    # Parse JSON response
    import json
    result = json.loads(response)
    
    return result
```

### Phase 3: Update CLAUDE.md Template (10 min)

**File**: `installer/global/lib/template_creation/claude_md_generator.py`

**Method**: Update `_generate_agent_sections()` to use enhanced info

```python
def _generate_agent_sections(self, analysis: CodebaseAnalysis) -> str:
    """Generate agent usage sections with populated information."""
    
    # Get all agent files from template output
    agent_dir = self.output_path / "agents"
    if not agent_dir.exists():
        return ""
    
    sections = {
        'general': [],
        'testing': [],
        'ui': [],
        'other': []
    }
    
    # Process each agent
    for agent_file in agent_dir.glob("*.md"):
        # Read metadata
        metadata = self._read_agent_metadata(agent_file)
        
        # Enhance with AI
        enhanced = self._enhance_agent_info(metadata)
        
        # Categorize
        category = self._categorize_agent(metadata['name'])
        
        # Format section
        agent_section = f"""### {metadata['name']}
**Purpose**: {enhanced['purpose']}

**When to Use**: {enhanced['when_to_use']}
"""
        
        sections[category].append(agent_section)
    
    # Build final markdown
    result = "# Agent Usage\n\n"
    result += "This template includes specialized agents tailored to this project's patterns:\n\n"
    
    if sections['general']:
        result += "## General Agents\n\n"
        result += "\n".join(sections['general'])
        result += "\n"
    
    if sections['testing']:
        result += "## Testing Agents\n\n"
        result += "\n".join(sections['testing'])
        result += "\n"
    
    if sections['ui']:
        result += "## UI Agents\n\n"
        result += "\n".join(sections['ui'])
        result += "\n"
    
    # ... etc
    
    result += """
## General Guidance

- Use agents when implementing features that match their expertise
- Agents understand this project's specific patterns and conventions
- For tasks outside agent specializations, rely on general Claude capabilities
"""
    
    return result
```

### Phase 4: Testing (5 min)

**Test**: Run template creation and verify CLAUDE.md

```bash
# Generate a test template
cd ~/Projects/appmilla_github/taskwright
/template-create --name test-agent-docs --validate

# Verify CLAUDE.md has populated sections
cat ~/.agentecflow/templates/test-agent-docs/CLAUDE.md | grep -A3 "### repository-pattern-specialist"

# Expected output:
# ### repository-pattern-specialist
# **Purpose**: Repository pattern with Realm database abstraction and data access layers
# **When to Use**: Use this agent when implementing data access layers, creating repository interfaces...
```

---

## Files to Modify

### Primary Implementation
- [ ] `installer/global/lib/template_creation/claude_md_generator.py`
  - Add `_read_agent_metadata()` method (~15 LOC)
  - Add `_enhance_agent_info()` method (~40 LOC)
  - Update `_generate_agent_sections()` method (~30 LOC modified)
  - **Total**: ~85 LOC (55 new, 30 modified)

### Dependencies
- [ ] Ensure `yaml` package available (for frontmatter parsing)
- [ ] Ensure `AIClient` accessible (already exists in codebase)

---

## Acceptance Criteria

### Functional Requirements
- [ ] CLAUDE.md has complete "Purpose" for all agents
- [ ] CLAUDE.md has specific "When to Use" for all agents
- [ ] Information is accurate and helpful
- [ ] Works for any set of agents (not hard-coded)
- [ ] Uses AI to generate "When to Use" scenarios

### Quality Requirements
- [ ] "Purpose" is concise (1 sentence)
- [ ] "When to Use" is specific (2-3 scenarios)
- [ ] Language is actionable and clear
- [ ] Consistent formatting across all agents
- [ ] No errors in generated JSON

### AI-First Requirements
- [ ] No hard-coded agent name → description mappings
- [ ] No pattern matching on agent names
- [ ] AI generates all "When to Use" content
- [ ] Works for agents from ANY codebase

---

## Test Plan

### Test 1: Verify Information Extraction
```python
# Test reading agent metadata
metadata = generator._read_agent_metadata(
    Path("agents/repository-pattern-specialist.md")
)

assert metadata['name'] == 'repository-pattern-specialist'
assert 'Repository pattern' in metadata['description']
assert 'C#' in metadata['technologies']
```

### Test 2: Verify AI Enhancement
```python
# Test AI enhancement
enhanced = generator._enhance_agent_info(metadata)

assert 'purpose' in enhanced
assert 'when_to_use' in enhanced
assert len(enhanced['purpose']) > 0
assert 'Use this agent when' in enhanced['when_to_use']
```

### Test 3: End-to-End Test
```bash
# Create template
/template-create --name test-e2e --validate

# Check CLAUDE.md
cat ~/.agentecflow/templates/test-e2e/CLAUDE.md

# Verify all agents have:
# - Non-empty Purpose
# - Specific When to Use
# - Proper formatting
```

---

## Example Output

### Before (Current)
```markdown
### repository-pattern-specialist
**Purpose**: 

**When to Use**: Use this agent for tasks related to 
```

### After (Fixed)
```markdown
### repository-pattern-specialist
**Purpose**: Repository pattern with Realm database abstraction and data access layers

**When to Use**: Use this agent when implementing data access layers, creating repository interfaces, working with Realm database persistence, building offline-first mobile architectures, or designing data access patterns with proper separation of concerns
```

---

## Rationale for AI-First Approach

### Why NOT Hard-Code?

**Problem with hard-coding**:
```python
# This breaks when:
# - New agent types emerge
# - Agent names change
# - Different codebases need different guidance
agent_guidance = {
    'repository': 'Use for data access',
    'mvvm': 'Use for UI patterns',
    # ... 50+ entries to maintain
}
```

**Solution with AI**:
```python
# This works for ANY agent, ANY codebase, ANY naming
enhanced = ai.generate(f"Generate guidance for: {description}")
```

### Benefits

1. **Zero Maintenance**: Works for new patterns without code changes
2. **Context-Aware**: Guidance specific to actual technologies used
3. **Consistent Quality**: AI generates similar format for all agents
4. **Extensible**: Works for 5 agents or 50 agents

---

## Edge Cases

### Edge Case 1: Agent with No Technologies
```python
if not metadata.get('technologies'):
    # AI can still generate guidance from description
    enhanced = _enhance_agent_info(metadata)
```

### Edge Case 2: AI Response Not JSON
```python
try:
    result = json.loads(response)
except JSONDecodeError:
    # Fallback to description
    result = {
        'purpose': metadata['description'],
        'when_to_use': f"Use this agent for {metadata['name'].replace('-', ' ')}"
    }
```

### Edge Case 3: Empty Agent Directory
```python
if not agent_dir.exists() or not list(agent_dir.glob("*.md")):
    # Skip agent sections entirely
    return ""
```

---

## Success Metrics

**Before Fix**:
- Purpose filled: 0%
- When to Use specific: 0%
- User clarity: Low

**After Fix**:
- Purpose filled: 100%
- When to Use specific: 100%
- User clarity: High

**User Impact**:
- Developers know exactly when to use each agent
- Clear guidance without reading agent files
- Better agent adoption and usage

---

## Related Issues

**Original Problem**: Template-create degradation (SOLVED by commit 03144d8)

**This Task**: Polish the CLAUDE.md documentation output

**Future Enhancement**: Could enhance the agent files themselves with template references (separate task)

---

## Implementation Notes

### Minimal Changes

This task makes ONLY these changes:
1. Add `_read_agent_metadata()` - reads YAML frontmatter
2. Add `_enhance_agent_info()` - calls AI for enhancement
3. Update `_generate_agent_sections()` - uses enhanced info

**No other changes** to:
- Template generation logic
- Agent generation logic
- Orchestrator workflow
- Other CLAUDE.md sections

### Testing Strategy

**Unit Tests**: Test each method individually
**Integration Test**: Full template creation
**Manual Verification**: Check CLAUDE.md output

---

## Timeline

- **Phase 1** (Read metadata): 5 min
- **Phase 2** (AI enhancement): 10 min
- **Phase 3** (Update template): 10 min
- **Phase 4** (Testing): 5 min
- **Total**: 30 minutes implementation + testing

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-15
**AI-First**: ✅ Yes (uses AI for all content generation)
**Hard-Coding**: ❌ None (zero pattern matching)
**Complexity**: 2/10 (Simple enhancement)
