# TASK-C7A9-REIMPLEMENT: Fix Agent Metadata Not Populated in CLAUDE.md

**Original Task**: TASK-CLAUDE-MD-AGENTS
**Original Implementation**: Commit e35f6f3 (2025-11-15)
**Status**: NEEDS RE-IMPLEMENTATION (lost in rollback)
**Priority**: HIGH
**Complexity**: 2/10 (Simple - code already exists, just needs to be reapplied)
**Estimated Effort**: 30-60 minutes

---

## Problem Statement

The CLAUDE.md file in generated templates is missing the "Agent Usage" section entirely. The code to populate this section exists in `claude_md_generator.py` (lines 800-1100), but it's not being called or the agents don't have the required metadata structure.

**Current State**: CLAUDE.md has NO agent usage section
**Desired State**: CLAUDE.md has "Agent Usage" section with Purpose and "When to Use" for each agent

---

## Investigation Findings

### What Exists in the Codebase

✅ **Code EXISTS** in `claude_md_generator.py`:
- Line 886: `_read_agent_metadata_from_file()` - reads frontmatter from agent files
- Line 916: `_enhance_agent_info_with_ai()` - generates AI-enhanced descriptions
- Line 805, 808: Calls to these methods exist
- Line 1048: Another call to enhancement

✅ **Commit History Shows**:
- Commit `e35f6f3`: "Enhance agent descriptions in CLAUDE.md with AI-generated guidance" (2025-11-15)
- Implementation added 361 lines (214 to claude_md_generator.py, 160 tests)
- Original task: TASK-CLAUDE-MD-AGENTS (exists in `tasks/backlog/`)

### What's Wrong

❌ **Agent Files Don't Have Frontmatter**:
```markdown
# Current agent file format (react-query-specialist.md):
# React Query Specialist

## Role
You are a TanStack Query (React Query) expert...

## Expertise
- Query management
- ...
```

❌ **Expected format**:
```markdown
---
name: react-query-specialist
description: TanStack Query expert for server-state management
priority: 7
technologies:
  - React
  - TanStack Query
  - TypeScript
---

# React Query Specialist
...
```

### Root Cause

**The agent generation code no longer creates agents with frontmatter metadata**, so the enhancement code (which expects frontmatter) cannot extract the metadata to populate CLAUDE.md.

**Two possible issues**:
1. Agent files are being created without frontmatter (most likely)
2. The CLAUDE.md generator isn't calling the agent usage methods
3. Both

---

## Solution Approach

### Option 1: Fix Agent Generation to Include Frontmatter ⭐ RECOMMENDED

**Rationale**: The enhancement code already exists and works. We just need agents with proper metadata.

**Steps**:
1. Find where agents are generated (likely `agent_generator.py`)
2. Ensure agents are created with frontmatter containing:
   - `name`: agent file name (without .md)
   - `description`: one-sentence summary
   - `priority`: 1-10 importance
   - `technologies`: list of relevant tech
3. Test that CLAUDE.md generation picks up the metadata

**Estimated Time**: 30 minutes

---

### Option 2: Extract Metadata from Agent Content

**Rationale**: If we can't add frontmatter, extract from existing content structure.

**Implementation**:
```python
def _extract_metadata_from_content(self, agent_file: Path) -> Dict[str, Any]:
    """Extract metadata from agent content without frontmatter."""
    content = agent_file.read_text()

    # Extract from structure
    metadata = {
        'name': agent_file.stem,
        'description': '',
        'technologies': [],
        'priority': 5
    }

    # Parse Role section for description
    if '## Role' in content:
        role_section = content.split('## Role')[1].split('##')[0]
        metadata['description'] = role_section.strip().split('\n')[0]

    # Parse Expertise section for technologies
    if '## Expertise' in content:
        expertise = content.split('## Expertise')[1].split('##')[0]
        techs = [line.strip('- ').strip() for line in expertise.split('\n') if line.strip().startswith('-')]
        metadata['technologies'] = techs[:5]  # First 5 items

    return metadata
```

**Estimated Time**: 45 minutes

---

### Option 3: Hybrid Approach

Modify `_read_agent_metadata_from_file()` to try frontmatter first, then fall back to content parsing.

**Estimated Time**: 60 minutes

---

## Recommended Implementation Plan

### Step 1: Investigate Agent Generation (10 min)

```bash
# Find where agents are created
grep -rn "def.*generate.*agent\|class.*AgentGenerator" installer/global/lib

# Check recent agent files
ls -la ~/.agentecflow/templates/react-typescript/agents/
cat ~/.agentecflow/templates/react-typescript/agents/react-query-specialist.md | head -30

# Find agent generation code
find installer/global -name "*agent*gen*.py" -type f
```

### Step 2: Check If Frontmatter Support Exists (5 min)

```python
# Check if agent_generator.py supports frontmatter
grep -A20 "def.*write.*agent\|def.*create.*agent" installer/global/lib/agent_generator/agent_generator.py
```

### Step 3: Implement Fix (15 min)

**If frontmatter support exists**:
- Ensure it's being called with proper metadata
- Test agent generation creates frontmatter

**If frontmatter support doesn't exist**:
- Add frontmatter creation to agent generation
- Use template like:
  ```python
  frontmatter = f"""---
name: {agent_name}
description: {description}
priority: {priority}
technologies: {yaml.dump(technologies)}
---

"""
  ```

### Step 4: Verify CLAUDE.md Generation (5 min)

```bash
# Regenerate template
cd ~/Projects/appmilla_github/taskwright
python installer/scripts/install.py  # or however you regenerate

# Check CLAUDE.md
cat ~/.agentecflow/templates/react-typescript/CLAUDE.md | grep -A10 "Agent Usage"

# Expected output:
# # Agent Usage
#
# ## react-query-specialist
# **Purpose**: TanStack Query expert for server-state management
# **When to Use**: Use this agent when implementing queries, managing cache...
```

### Step 5: Test and Commit (5 min)

```bash
# Test on 2-3 templates
/template-create # or test command

# Verify all have agent sections
for template in react-typescript fastapi-python; do
  echo "=== $template ==="
  grep -A3 "## Agent Usage" ~/.agentecflow/templates/$template/CLAUDE.md
done

# Commit
git add .
git commit -m "fix: Restore agent metadata in CLAUDE.md generation

Restores functionality from commit e35f6f3 that was lost.

- Ensures agents have frontmatter with metadata
- CLAUDE.md now includes Agent Usage section
- Each agent has Purpose and When to Use populated

Task: TASK-C7A9-REIMPLEMENT
Original: TASK-CLAUDE-MD-AGENTS
"
```

---

## Files to Check/Modify

### Primary Files

1. **Agent Generation** (most likely needs fixing):
   - `installer/global/lib/agent_generator/agent_generator.py`
   - Look for where agent files are written
   - Ensure frontmatter is included

2. **CLAUDE.md Generation** (already has the code):
   - `installer/global/lib/template_generator/claude_md_generator.py`
   - Lines 800-1100: Enhancement code EXISTS
   - May need to ensure `_generate_dynamic_agent_usage()` is called

3. **Orchestrator** (may need to ensure proper flow):
   - `installer/global/commands/lib/template_create_orchestrator.py`
   - Ensure agents are generated BEFORE CLAUDE.md
   - Ensure CLAUDE.md generator has access to agent files

---

## Acceptance Criteria

- [ ] Agent files have frontmatter with: name, description, priority, technologies
- [ ] CLAUDE.md has "Agent Usage" section
- [ ] Each agent has non-empty "Purpose"
- [ ] Each agent has specific "When to Use" guidance
- [ ] AI enhancement works (or fallback to pattern-based)
- [ ] Tested on 3+ templates (react-typescript, fastapi-python, nextjs-fullstack)

---

## Reference Materials

### Original Task Specification
- Location: `tasks/backlog/TASK-CLAUDE-MD-AGENTS.md`
- Complete implementation details
- Test specifications
- Example outputs

### Original Implementation Commit
```bash
git show e35f6f3

# Key changes:
# - Added _read_agent_metadata_from_file()
# - Added _enhance_agent_info_with_ai()
# - Updated _extract_agent_metadata() to use AI
# - Added 160 lines of tests
```

### Example Agent Frontmatter Format
```yaml
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
```

### Example CLAUDE.md Output
```markdown
# Agent Usage

This template includes specialized agents tailored to this project's patterns:

## repository-pattern-specialist
**Purpose**: Repository pattern with Realm database abstraction and data access layers

**When to Use**: Use this agent when implementing data access layers, creating repository interfaces, working with Realm database persistence, building offline-first mobile architectures, or designing data access patterns with proper separation of concerns

## react-query-specialist
**Purpose**: TanStack Query expert for server-state management in React applications

**When to Use**: Use this agent when implementing queries with useQuery, managing mutations, designing cache invalidation strategies, implementing optimistic updates, or integrating React Query DevTools
```

---

## Testing Checklist

### Unit Tests (if time permits)
- [ ] Test frontmatter extraction
- [ ] Test AI enhancement (with mock)
- [ ] Test fallback when AI unavailable

### Integration Tests
- [ ] Generate template with agents
- [ ] Verify CLAUDE.md has Agent Usage section
- [ ] Verify all agents listed
- [ ] Verify Purpose and When to Use populated

### Manual Verification
```bash
# Test 3 templates
for template in react-typescript fastapi-python nextjs-fullstack; do
  echo "=== Testing $template ==="

  # Check agent files have frontmatter
  for agent in ~/.agentecflow/templates/$template/agents/*.md; do
    echo "Agent: $(basename $agent)"
    head -10 "$agent" | grep "^---" && echo "  ✓ Has frontmatter" || echo "  ✗ Missing frontmatter"
  done

  # Check CLAUDE.md has agent section
  grep -q "# Agent Usage" ~/.agentecflow/templates/$template/CLAUDE.md \
    && echo "  ✓ CLAUDE.md has Agent Usage" \
    || echo "  ✗ CLAUDE.md missing Agent Usage"
done
```

---

## Quick Win: Check Current State

Before implementing, verify what's already there:

```bash
# Check if code exists (should return results)
grep -n "_enhance_agent_info_with_ai" installer/global/lib/template_generator/claude_md_generator.py

# Check if it's being called (should show call sites)
grep -n "generate.*agent.*usage\|_generate_dynamic_agent_usage" installer/global/lib/template_generator/claude_md_generator.py

# Check agent format (should show frontmatter or just markdown)
head -20 ~/.agentecflow/templates/react-typescript/agents/react-query-specialist.md

# Check CLAUDE.md (should have or be missing Agent Usage)
grep -A20 "# Agent Usage" ~/.agentecflow/templates/react-typescript/CLAUDE.md
```

---

## Success Metrics

**Before Fix**:
- Agent Usage in CLAUDE.md: ❌ Missing
- Agent metadata: ❌ No frontmatter
- Purpose populated: 0%
- When to Use specific: 0%

**After Fix**:
- Agent Usage in CLAUDE.md: ✅ Present
- Agent metadata: ✅ Frontmatter included
- Purpose populated: 100%
- When to Use specific: 100%

---

## Notes

### Why This Matters

Good agent documentation in CLAUDE.md helps users:
1. Know which agents exist in their template
2. Understand when to use each agent
3. Get started quickly without reading all agent files
4. Make informed decisions about agent usage

### Related Issues

- Original implementation: Commit e35f6f3 (2025-11-15)
- Related to agent generation in Phase 6-7
- May be affected by recent Phase 7.5 changes

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-20
**Priority**: HIGH (user-facing documentation quality)
**Complexity**: 2/10 (code exists, just needs proper data flow)
**Estimated Duration**: 30-60 minutes
