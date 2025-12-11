---
id: TASK-RULES-ENHANCE
title: Enrich rules/guidance and rules/patterns content during template-create
status: completed
task_type: implementation
created: 2025-12-11T17:45:00Z
updated: 2025-12-11T18:30:00Z
completed: 2025-12-11T18:30:00Z
priority: high
tags: [template-create, rules-structure, content-quality, progressive-disclosure]
complexity: 5
related_to: [TASK-REV-CB0F, TASK-TC-DEFAULT-FLAGS]
---

# Task: Enrich Rules Guidance Content During Template Creation

## Background

Review TASK-REV-CB0F identified that when using `--use-rules-structure`, the generated content in `.claude/rules/guidance/` and `.claude/rules/patterns/` is stub/placeholder content, not the rich content produced by `/agent-enhance`.

### Current Output (rules/guidance/realm-repository-erroror-specialist.md)

```markdown
# realm-repository-erroror-specialist

## Purpose

Specialized agent for specific tasks

## Capabilities

- Specialized task handling

## Usage

This agent is automatically invoked when working on relevant files.

## Best Practices

- Follow agent guidance
- Review generated code
- Ask for clarification when needed
```

### Expected Output (from /agent-enhance)

```markdown
# Realm Repository Pattern Specialist

## Purpose

Repository pattern with Realm database, RealmAccessor for thread-safety, and ErrorOr functional error handling

## Boundaries

### ALWAYS
- ✅ Use IRealmAccessor for all Realm operations (ensures thread-safety and proper disposal)
- ✅ Materialize queries with `.ToList()` before returning from ExecuteReadAsync
...

### NEVER
- ❌ Never instantiate Realm directly in repositories
...

### ASK
- ⚠️ Complex queries spanning multiple tables: Ask if query should be moved...
```

## Problem Statement

The rules structure generator produces placeholder content for:
- `.claude/rules/guidance/*.md` files
- `.claude/rules/patterns/*.md` files

While the `agents/` directory gets the full enhanced content from `/agent-enhance`.

## Root Cause

The rules structure generator in Phase 6 creates stub files independently of the agent enhancement process in Phase 8. These two systems are not integrated.

## Proposed Solution

### Option A: Copy Agent Content to Rules (Recommended)

After agent enhancement (Phase 8), copy the enhanced agent content to the corresponding rules/guidance file:

```python
# In rules_generator.py or post-Phase 8 hook

def sync_agent_to_guidance(agent_file: Path, rules_dir: Path):
    """Copy enhanced agent content to rules/guidance with path frontmatter."""
    agent_content = agent_file.read_text()

    # Extract agent name
    agent_name = agent_file.stem.replace('-specialist', '-specialist')

    # Determine path pattern from agent stack/phase
    path_pattern = infer_path_pattern(agent_content)

    # Add path frontmatter
    rules_content = f"""---
paths: {path_pattern}
---

{agent_content}
"""

    guidance_file = rules_dir / 'guidance' / f'{agent_name}.md'
    guidance_file.write_text(rules_content)
```

**Pros**: Simple, maintains single source of truth in agents/
**Cons**: Duplication of content

### Option B: Symlink Rules to Agents

Create symlinks from rules/guidance/ to agents/:

```bash
ln -s ../../../agents/realm-repository-pattern-specialist.md \
      .claude/rules/guidance/realm-repository-pattern-specialist.md
```

**Pros**: No duplication, always in sync
**Cons**: Symlinks can be problematic across platforms, Claude Code may not follow them

### Option C: Enhance Rules Generator (Comprehensive)

Modify the rules structure generator to produce rich content by:
1. Using the same AI enhancement pipeline as agent-enhance
2. Extracting patterns and practices from template source code
3. Generating boundary sections based on layer/pattern

**Pros**: Native rich content in rules structure
**Cons**: More complex, duplicates agent-enhance logic

## Recommended Approach

**Option A with improvements**:

1. During Phase 6 (rules generation), create placeholder files with correct paths
2. During Phase 8 (agent enhancement), sync enhanced content to rules/guidance
3. Add `paths:` frontmatter based on agent metadata (stack, phase, layer)

### Path Pattern Mapping

| Agent Layer | Path Pattern |
|-------------|--------------|
| Presentation/ViewModels | `**/ViewModels/**`, `**/Views/**` |
| Data Access/Repository | `**/Repositories/**`, `**/Data/**` |
| Business Logic/Engine | `**/Engines/**`, `**/Services/**` |
| Infrastructure | `**/Infrastructure/**` |
| Testing | `**/*.Tests/**`, `**/*Tests.cs` |

## Implementation Tasks

1. **Modify rules_generator.py**
   - Add `sync_agent_to_guidance()` function
   - Call after Phase 8 completes

2. **Add path pattern inference**
   - Map agent `stack` and `phase` metadata to file path patterns
   - Use layer information from manifest.json

3. **Handle progressive disclosure split**
   - Copy core file to rules/guidance/
   - Reference extended file in loading instructions

4. **Update patterns/ content similarly**
   - Extract pattern content from template source
   - Or derive from agent capabilities

## Acceptance Criteria

- [ ] rules/guidance/*.md files contain full boundary sections (ALWAYS/NEVER/ASK)
- [ ] rules/guidance/*.md files have correct `paths:` frontmatter
- [ ] rules/patterns/*.md files contain pattern-specific content with examples
- [ ] Content matches quality of /agent-enhance output
- [ ] No duplication of content maintenance (single source of truth)

## Testing

```bash
# Create template with rules structure
/template-create --name test-template

# Verify guidance content
cat ~/.agentecflow/templates/test-template/.claude/rules/guidance/realm-*.md
# Should show full boundaries, not placeholders

# Verify path patterns
grep -r "paths:" ~/.agentecflow/templates/test-template/.claude/rules/
# Should show relevant file patterns
```
