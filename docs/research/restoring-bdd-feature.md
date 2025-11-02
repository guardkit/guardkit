# Restoring BDD Feature to Taskwright

## Executive Summary

This document provides complete instructions for restoring BDD (Behavior-Driven Development) functionality to taskwright if needed in the future. BDD was removed in commit `08e6f21` (November 2, 2025) to simplify the system and focus on lightweight task management.

## Why BDD Was Removed

**Decision Date**: November 2, 2025
**Commit**: `08e6f21e67983aa731f4ef5dd5415c2bf87587b2`

**Reasons for Removal**:
1. **Not fully implemented** - BDD mode was documented but incomplete
2. **Dependency on require-kit** - Full EARS → BDD workflow requires require-kit anyway
3. **Low expected usage** - Estimated <5% of users would use BDD mode
4. **Unnecessary complexity** - Added overhead to lightweight system
5. **Better served elsewhere** - require-kit provides complete EARS → Gherkin → Implementation flow

**Philosophy**: Keep taskwright lightweight and pragmatic. Users needing full BDD workflows should use require-kit which provides:
- EARS requirements notation
- Automated Gherkin generation from EARS
- Requirements traceability
- Epic/Feature hierarchy
- Complete BDD workflow support

## When to Consider Restoring BDD

Consider restoring BDD mode if:
- **High user demand** - More than 20% of users request BDD mode
- **Standalone BDD need** - Users want BDD without full requirements engineering
- **Integration changes** - require-kit integration becomes problematic
- **Market positioning** - Competitive advantage requires BDD support
- **Technical advancement** - New AI capabilities make BDD generation significantly better

**Threshold**: Restore only if clear evidence shows significant user demand and value addition.

## Files That Were Removed

### Agents (3 files deleted)
1. `.claude/agents/bdd-generator.md` - Main BDD generation agent
2. `installer/global/templates/maui-navigationpage/agents/bdd-generator.md` - MAUI template copy

### Instructions (1 file deleted)
3. `installer/global/instructions/core/bdd-gherkin.md` - BDD methodology and patterns

### Tasks (2 files deleted)
4. `tasks/backlog/TASK-037-remove-bdd-mode.md` - The removal task itself
5. `tasks/in_review/TASK-037-remove-bdd-mode.md` - Duplicate in review folder

### Documentation (1 file deleted)
6. `tasks/backlog/TASK-018-task-create-epic-link.md` - Related epic linking task

**Note**: The `bdd-generator` agent was also removed from any other template directories that may have contained copies.

## Restoration Steps

### Phase 1: Retrieve Deleted Files (15 minutes)

```bash
# Navigate to repository root
cd /path/to/taskwright

# Create restoration branch
git checkout -b restore-bdd-feature

# Retrieve the BDD generator agent
git show 08e6f21~1:.claude/agents/bdd-generator.md > .claude/agents/bdd-generator.md

# Retrieve the BDD instruction file
git show 08e6f21~1:installer/global/instructions/core/bdd-gherkin.md > installer/global/instructions/core/bdd-gherkin.md

# Retrieve MAUI template agent (if using MAUI template)
git show 08e6f21~1:installer/global/templates/maui-navigationpage/agents/bdd-generator.md > installer/global/templates/maui-navigationpage/agents/bdd-generator.md

# Verify files restored
ls -la .claude/agents/bdd-generator.md
ls -la installer/global/instructions/core/bdd-gherkin.md
```

### Phase 2: Update task-work Command (30 minutes)

**File**: `installer/global/commands/task-work.md`

**Changes needed**:

1. **Add BDD mode to mode parameter** (around line 50):
```markdown
- `--mode=<standard|tdd|bdd>`: Development methodology
  - `standard`: Requirements analysis → Planning → Implementation → Testing
  - `tdd`: Test-First development (Red → Green → Refactor)
  - `bdd`: Behavior-Driven Development (Gherkin scenarios → Implementation)
  - Default: `standard`
```

2. **Add BDD mode section** (insert after TDD section, around line 2300):
```markdown
### BDD (Behavior-Driven Development) Mode

**When to Use**:
- User-facing features with clear behaviors
- Need for executable specifications
- Collaboration between technical and non-technical stakeholders
- Living documentation requirements

**Workflow**:
1. Convert requirements to Gherkin scenarios
2. Implement step definitions
3. Write implementation to pass scenarios
4. Refactor while keeping scenarios green

**Agent**: Uses `bdd-generator` to create Gherkin scenarios from requirements

**Example**:
```bash
/task-work TASK-001 --mode=bdd
```

**Prerequisites**:
- Task must have linked requirements (via require-kit)
- Or task description must include clear behavioral requirements

**Output**:
- Gherkin feature files in `docs/bdd/`
- Step definition files (stack-specific location)
- Implementation files
- Test execution results
```

3. **Add BDD mode implementation to Phase 1** (around line 1000):
```markdown
**For BDD Mode**:
- Convert requirements/description to Gherkin scenarios
- Identify Feature, Scenario, Given/When/Then structure
- Create scenario outline if data-driven tests needed
- Document automation approach
```

### Phase 3: Update task-manager Agent (20 minutes)

**File**: `.claude/agents/task-manager.md`

**Changes needed**:

1. **Add BDD mode to mode selection** (around line 50):
```python
def select_development_mode(task, mode_flag):
    """Select development mode based on task and user preference."""
    if mode_flag:
        return mode_flag  # User explicitly chose mode

    # Auto-detect if not specified
    if has_linked_requirements(task) or has_behavioral_requirements(task):
        return "bdd"  # Requirements suggest BDD
    elif is_complex_business_logic(task):
        return "tdd"  # Complex logic benefits from TDD
    else:
        return "standard"  # Default
```

2. **Add BDD mode implementation** (around line 120):
```python
def implement_bdd_mode():
    """Implement BDD mode workflow."""
    print("\n🥒 BDD MODE: Behavior-Driven Development")
    print("Converting requirements to Gherkin scenarios...\n")

    # Phase 1: Generate Gherkin scenarios
    invoke_agent("bdd-generator", task_context={
        "task": task,
        "requirements": load_requirements(task),
        "epic": task.epic,
        "feature": task.feature
    })

    # Phase 2: Implementation Planning
    # (Standard Phase 2 with BDD context)

    # Phase 3: Implementation
    # - Implement step definitions
    # - Write implementation code
    # - Run scenarios

    # Phase 4: Scenario Execution
    print("\n🧪 PHASE 4: Execute BDD Scenarios")
    run_gherkin_scenarios()

    # Phase 5: Code Review
    # (Standard Phase 5)
```

3. **Update mode descriptions** (around line 80):
```markdown
## Development Modes

### Standard Mode
- Linear workflow: Requirements → Plan → Implement → Test
- Best for straightforward implementations

### TDD Mode
- Test-First workflow: Red → Green → Refactor
- Best for complex business logic

### BDD Mode
- Behavior-First workflow: Gherkin → Implementation → Verification
- Best for user-facing features
- Requires clear behavioral requirements
```

### Phase 4: Update Template Manifests (10 minutes)

**For each template that should support BDD**:

**File**: `installer/global/templates/*/config/manifest.json` or `manifest.json`

**Add to agents array**:
```json
{
  "agents": [
    "task-manager.md",
    "code-reviewer.md",
    "test-orchestrator.md",
    "bdd-generator.md"  // ← ADD THIS
  ]
}
```

**Templates to update**:
- `installer/global/templates/default/manifest.json`
- `installer/global/templates/react/manifest.json`
- `installer/global/templates/python/manifest.json`
- `installer/global/templates/maui-appshell/config/manifest.json`
- `installer/global/templates/maui-navigationpage/manifest.json`
- Any other templates supporting BDD

### Phase 5: Update Documentation (20 minutes)

#### 5.1 Update CLAUDE.md

**File**: `CLAUDE.md`

**Changes**:

1. **Add BDD to development modes** (around line 150):
```markdown
**Development Mode Selection:**
- **TDD**: Complex business logic (Red → Green → Refactor)
- **BDD**: User-facing features (Gherkin → Implementation → Verification)
- **Standard**: Straightforward implementations
```

2. **Update task-work examples** (around line 100):
```bash
/task-work TASK-XXX [--mode=standard|tdd|bdd]
```

3. **Add BDD workflow section** (around line 200):
```markdown
## BDD Workflow

For user-facing features requiring executable specifications:

```bash
# Create task with requirements
/task-create "User authentication" requirements:[REQ-001,REQ-002]

# Work in BDD mode
/task-work TASK-001 --mode=bdd

# BDD workflow:
# 1. Generate Gherkin scenarios from requirements
# 2. Implement step definitions
# 3. Write implementation
# 4. Execute scenarios
# 5. Code review
```

**Output**:
- Feature files: `docs/bdd/*.feature`
- Step definitions: Stack-specific location
- Implementation: Following scenarios
```

#### 5.2 Update .claude/CLAUDE.md

**File**: `.claude/CLAUDE.md`

**Changes**:

1. **Add BDD agent to agent list** (around line 400):
```markdown
**Stack-Specific Agents:**
- API/Domain/Testing/UI specialists per technology stack
- **bdd-generator**: Converts requirements to Gherkin scenarios (when BDD mode enabled)
```

2. **Update development best practices** (around line 500):
```markdown
**Development Mode Selection:**
- **TDD**: Complex business logic (Red → Green → Refactor)
- **BDD**: User-facing features with clear behaviors (Scenarios → Implementation)
- **Standard**: Straightforward implementations

**Note:** BDD mode requires either:
- Linked requirements (via require-kit integration)
- Clear behavioral requirements in task description
```

#### 5.3 Update README or Getting Started

**If BDD examples were in README**, restore them:

```markdown
## BDD Mode Example

For features requiring executable specifications:

```bash
# Create task with clear behavior
/task-create "User login functionality" requirements:[REQ-AUTH-001]

# Implement using BDD mode
/task-work TASK-001 --mode=bdd

# Generated:
# - docs/bdd/user-authentication.feature
# - tests/step_definitions/authentication_steps.py
# - src/auth/login.py
```
```

### Phase 6: Update feature_detection.py (5 minutes)

**File**: `installer/global/commands/lib/feature_detection.py`

**Current state**: Function `supports_bdd()` still exists (it's a shared file with require-kit)

**Update docstring** to reflect BDD now available in taskwright:
```python
def supports_bdd() -> bool:
    """
    Check if BDD generation is available.

    BDD generation is now supported in taskwright standalone mode.
    Enhanced BDD workflow (with EARS requirements) available when
    require-kit is also installed.

    Returns:
        bool: True if BDD generation available (always True in taskwright)
    """
    return True  # Now native to taskwright
```

**Note**: If this breaks require-kit compatibility, consider:
```python
def supports_bdd() -> bool:
    """
    Check if BDD generation is available.

    Returns True if either:
    - taskwright has bdd-generator agent (standalone BDD)
    - require-kit is installed (full EARS → BDD workflow)

    Returns:
        bool: True if BDD generation available
    """
    packages = get_installed_packages()

    # Check if taskwright has BDD agent
    if 'taskwright' in packages:
        bdd_agent_path = Path.home() / '.agentecflow' / 'agents' / 'bdd-generator.md'
        if bdd_agent_path.exists():
            return True

    # Check if require-kit provides BDD
    if 'require-kit' in packages:
        return True

    return False
```

### Phase 7: Add BDD Templates (15 minutes)

Create BDD scenario template if needed:

**File**: `installer/global/templates/default/templates/bdd-scenario.md`

```markdown
# BDD Scenario Template

## Feature: [Feature Name]

```gherkin
# Requirement: [REQ-ID]
# Task: [TASK-ID]

@priority-[high|medium|low] @[feature-area]
Feature: [Feature Name]
  As a [user role]
  I want [capability]
  So that [business value]

  Background:
    Given [common setup for all scenarios]

  @happy-path
  Scenario: [Primary success scenario]
    Given [initial context]
    When [user action]
    Then [expected outcome]
    And [additional assertions]

  @edge-case
  Scenario: [Edge case description]
    Given [edge condition setup]
    When [trigger]
    Then [edge case handling]

  @error-handling
  Scenario: [Error scenario]
    Given [setup that could fail]
    When [failure occurs]
    Then [error is handled gracefully]
```

## Step Definitions

**Location**: [Stack-specific, e.g., `tests/step_definitions/`]

**Implementation**: Created by BDD agent based on scenarios
```

### Phase 8: Update Installer (5 minutes)

**File**: `installer/scripts/install.sh`

Verify installer copies BDD files correctly:

```bash
# In copy_global_resources() function, verify:
cp -r "$INSTALLER_DIR/global/instructions" "$AGENTECFLOW_HOME/" || true
cp -r "$INSTALLER_DIR/global/agents" "$AGENTECFLOW_HOME/" || true

# These should now include bdd-generator.md and bdd-gherkin.md
```

### Phase 9: Update Changelog (10 minutes)

**File**: `installer/CHANGELOG.md`

Add restoration entry:

```markdown
## [2.1.0] - YYYY-MM-DD

### Added
- **BDD Mode Restored**: Full Behavior-Driven Development support
  - `bdd-generator` agent for Gherkin scenario generation
  - `--mode=bdd` flag for task-work command
  - BDD methodology instructions
  - Template support for BDD workflow

### Why Restored
[Explain the reasons for restoration, e.g.:]
- Strong user demand (>30% of surveyed users requested BDD)
- Improved AI capabilities for Gherkin generation
- Standalone BDD use case validated through user feedback
- Complementary to require-kit (not redundant)

### Migration
- Existing tasks can now use `--mode=bdd`
- BDD scenarios output to `docs/bdd/` directory
- Requires clear behavioral requirements or linked EARS requirements
- Full EARS → BDD workflow still available via require-kit

### Breaking Changes
None - this is an additive feature restoration

### Known Limitations
- BDD mode works best with linked requirements (require-kit)
- Standalone BDD relies on task description quality
- Gherkin generation quality depends on requirement clarity
```

### Phase 10: Testing (30 minutes)

#### 10.1 Unit Tests

```bash
# Test feature detection
cd ~/.agentecflow/commands/lib
python3 << 'EOF'
from feature_detection import supports_bdd, get_installed_packages

print("Installed packages:", get_installed_packages())
print("Supports BDD:", supports_bdd())
# Should return True after restoration
EOF
```

#### 10.2 Integration Tests

**Test 1: BDD Agent Exists**
```bash
# Verify agent file exists
test -f ~/.agentecflow/agents/bdd-generator.md && echo "✅ BDD agent restored" || echo "❌ Agent missing"

# Verify instruction file exists
test -f ~/.agentecflow/instructions/core/bdd-gherkin.md && echo "✅ BDD instructions restored" || echo "❌ Instructions missing"
```

**Test 2: Command Help Shows BDD**
```bash
# In Claude Code
/task-work --help

# Should show:
# --mode=<standard|tdd|bdd>
#   - bdd: Behavior-Driven Development (Gherkin scenarios → Implementation)
```

**Test 3: BDD Mode Execution**
```bash
# Create test task
/task-create "Test BDD restoration"

# Try BDD mode
/task-work TASK-TEST-001 --mode=bdd

# Expected:
# 🥒 BDD MODE: Behavior-Driven Development
# Converting requirements to Gherkin scenarios...
# [bdd-generator agent loads and generates scenarios]
```

**Test 4: Template Includes BDD Agent**
```bash
# Check template manifest
cat installer/global/templates/default/manifest.json | grep bdd-generator
# Should find: "bdd-generator.md"

# Verify MAUI template
cat installer/global/templates/maui-navigationpage/manifest.json | grep bdd-generator
# Should find: "bdd-generator.md"
```

#### 10.3 Documentation Tests

```bash
# Search for BDD references (should find them after restoration)
grep -r "mode=bdd" CLAUDE.md .claude/CLAUDE.md installer/global/commands/

# Verify complete BDD workflow documented
grep -r "BDD Mode" CLAUDE.md

# Check examples exist
grep -r "task-work.*--mode=bdd" CLAUDE.md
```

### Phase 11: Release (10 minutes)

```bash
# Commit changes
git add .
git commit -m "Restore BDD feature to taskwright

Restored complete BDD (Behavior-Driven Development) support:
- bdd-generator agent for Gherkin scenario generation
- BDD methodology instructions
- --mode=bdd flag for task-work command
- Template integration for BDD workflow
- Updated documentation and examples

Why restored: [Explain reason, e.g., strong user demand]

Closes: #[issue-number]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Merge to main
git checkout main
git merge --no-ff restore-bdd-feature

# Tag release
git tag -a v2.1.0 -m "BDD feature restoration"

# Push
git push origin main --tags
```

## Complete File Recovery Commands

For quick restoration, use these commands:

```bash
#!/bin/bash
# restore-bdd.sh - Quick BDD feature restoration script

RESTORE_COMMIT="08e6f21~1"  # Commit before BDD removal

echo "Restoring BDD feature files..."

# Create restoration branch
git checkout -b restore-bdd-feature

# Restore main BDD agent
git show $RESTORE_COMMIT:.claude/agents/bdd-generator.md > .claude/agents/bdd-generator.md
echo "✅ Restored .claude/agents/bdd-generator.md"

# Restore BDD instructions
git show $RESTORE_COMMIT:installer/global/instructions/core/bdd-gherkin.md > installer/global/instructions/core/bdd-gherkin.md
echo "✅ Restored installer/global/instructions/core/bdd-gherkin.md"

# Restore MAUI template BDD agent
mkdir -p installer/global/templates/maui-navigationpage/agents
git show $RESTORE_COMMIT:installer/global/templates/maui-navigationpage/agents/bdd-generator.md > installer/global/templates/maui-navigationpage/agents/bdd-generator.md
echo "✅ Restored installer/global/templates/maui-navigationpage/agents/bdd-generator.md"

# Verify restoration
echo ""
echo "Verification:"
test -f .claude/agents/bdd-generator.md && echo "✅ BDD agent exists" || echo "❌ BDD agent missing"
test -f installer/global/instructions/core/bdd-gherkin.md && echo "✅ BDD instructions exist" || echo "❌ BDD instructions missing"

echo ""
echo "⚠️  Manual steps still required:"
echo "  1. Update installer/global/commands/task-work.md (add BDD mode)"
echo "  2. Update .claude/agents/task-manager.md (add BDD implementation)"
echo "  3. Update template manifests (add bdd-generator.md)"
echo "  4. Update CLAUDE.md and documentation"
echo "  5. Update feature_detection.py docstrings"
echo "  6. Update CHANGELOG.md"
echo "  7. Run tests"
echo ""
echo "See docs/research/restoring-bdd-feature.md for complete instructions"
```

Save this script and run:
```bash
chmod +x restore-bdd.sh
./restore-bdd.sh
```

## BDD Generator Agent Reference

### Complete Agent File

The `bdd-generator.md` agent has these key sections:

1. **EARS to Gherkin Transformation Patterns**
   - Event-Driven → Scenario
   - State-Driven → Scenario with Background
   - Unwanted Behavior → Error Scenario
   - Optional Feature → Feature Toggle Scenario

2. **Gherkin Best Practices**
   - Structure rules (one behavior per scenario, independence, etc.)
   - Writing guidelines (DO/DON'T lists)

3. **Scenario Generation Process**
   - Step 1: Analyze EARS requirement
   - Step 2: Create base scenario
   - Step 3: Add edge cases
   - Step 4: Organize and tag

4. **Output Template**
   - Feature structure with metadata
   - Background setup
   - Happy path scenarios
   - Edge case scenarios
   - Error handling scenarios
   - Performance scenarios

5. **Common Patterns**
   - Authentication scenarios
   - Data validation scenarios
   - API interaction scenarios

6. **Advanced Techniques**
   - Data tables
   - Background context
   - Scenario outlines

7. **Integration Guidance**
   - Linking to implementation
   - Automation hints
   - Test framework integration

### Key Capabilities

The BDD generator can:
- Convert EARS requirements to Gherkin
- Generate happy path scenarios
- Create edge case scenarios
- Add error handling scenarios
- Include performance requirements
- Use scenario outlines for data-driven tests
- Tag scenarios appropriately
- Link to requirement IDs
- Provide test automation hints

## BDD Instruction File Reference

The `bdd-gherkin.md` instruction file provides:

1. **EARS to Gherkin Mapping**
   - Event-driven → Scenario
   - State-driven → Background + Scenario
   - Unwanted behavior → Error scenario

2. **Gherkin Syntax**
   - Feature, Scenario, Given/When/Then keywords
   - Background, Scenario Outline, Examples

3. **Best Practices**
   - One behavior per scenario
   - Independent scenarios
   - Clear language
   - Concrete examples

4. **Complete Examples**
   - User authentication
   - Data validation
   - API interactions

5. **Tagging Strategy**
   - Priority levels
   - Feature areas
   - Test types (smoke, regression)

## Integration with require-kit

If both taskwright and require-kit are installed:

**taskwright provides**:
- Standalone BDD mode (task description → Gherkin)
- Quick BDD scenario generation
- BDD without full requirements engineering

**require-kit provides**:
- Full EARS requirements management
- EARS → Gherkin automation
- Requirements traceability
- Epic/Feature/Requirement hierarchy
- Comprehensive BDD workflow

**Collaboration**:
- taskwright BDD mode can leverage require-kit requirements
- `feature_detection.supports_bdd()` returns True if either package provides BDD
- Task-work checks for linked requirements (require-kit) first
- Falls back to standalone BDD if no requirements linked

## Decision Checklist

Before restoring BDD, verify:

- [ ] **User Demand**: >20% of users requesting BDD mode
- [ ] **Clear Use Case**: Standalone BDD need validated
- [ ] **Resource Availability**: Time to maintain BDD feature
- [ ] **AI Quality**: Current LLM can generate quality Gherkin
- [ ] **No Overlap**: BDD in taskwright complements (not duplicates) require-kit
- [ ] **Documentation**: Willing to maintain BDD documentation
- [ ] **Testing**: Can test BDD generation quality
- [ ] **Support**: Can support users with BDD questions

**Recommendation**: Only restore if all boxes checked.

## Alternative: Recommend require-kit

Instead of restoring BDD to taskwright, consider:

**Enhanced require-kit Recommendation**:

```markdown
## BDD Workflow

For BDD workflows, install **require-kit** which provides:
- EARS requirements notation
- Automated Gherkin generation
- Requirements traceability
- Complete BDD lifecycle

**Installation**:
```bash
cd require-kit
./installer/scripts/install.sh
```

**Usage**:
```bash
# Create epic with EARS requirements
/epic-create "User Management"
/formalize-ears REQ-001

# Generate BDD scenarios from EARS
/generate-bdd REQ-001

# Implement with full context
/task-work TASK-001  # Automatically includes BDD scenarios
```

**Benefits**:
- Complete requirements → scenarios → implementation flow
- Traceability from requirement to test
- Living documentation
- No duplication between tools
```

This approach:
- Keeps taskwright lightweight
- Provides superior BDD experience (with full requirements)
- Maintains clear separation of concerns
- Reduces maintenance burden

## Summary

**Restoration Effort**: ~2-3 hours total
**Maintenance Burden**: Medium (requires ongoing LLM prompt tuning)
**User Benefit**: High (if demand validated)

**Recommendation**: Only restore if clear evidence of need. Otherwise, recommend require-kit for superior BDD experience.

**Quick Restoration**: Use the `restore-bdd.sh` script + manual documentation updates

**Complete Restoration**: Follow all 11 phases above

---

**Last Updated**: 2025-11-02
**Removal Commit**: `08e6f21`
**Restoration Status**: Not restored (as of this document)
**Decision Authority**: Project maintainer based on user demand metrics
