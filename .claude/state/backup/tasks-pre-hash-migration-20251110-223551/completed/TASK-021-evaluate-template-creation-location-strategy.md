# TASK-021: Evaluate Template Creation Location Strategy

**Priority**: Medium
**Type**: Investigation / Design Decision
**Epic**: EPIC-001 (AI Template Creation)
**Created**: 2025-01-07
**Status**: Completed
**Completed**: 2025-01-08
**Tags**: [template-creation, installation, workflow, design-decision]

## Issue Description

During template analysis testing, we observed that the `/template-create` command writes templates to the **repository location** rather than directly to the global `~/.agentecflow/templates/` directory. This raised the question: **Is this the intended behavior, or should templates be created directly in the global location?**

## Current Behavior (The Template Installation Flow)

### Current 3-Step Process

```
Step 1: Template Creation (Development)
├─ Location: /Users/richwoollcott/Projects/Github/guardkit/
│            installer/global/templates/ardalis-clean-architecture/
├─ Command: /template-create
└─ Output: Template written to REPOSITORY location

Step 2: Template Installation (Deployment)
├─ Location: ~/.agentecflow/templates/ardalis-clean-architecture/
├─ Command: ./installer/scripts/install.sh
└─ Output: Installer COPIES template from repo to global location

Step 3: Template Usage (Runtime)
├─ Location: Project directory
├─ Command: guardkit init ardalis-clean-architecture
└─ Output: Init reads from GLOBAL location (~/.agentecflow/templates/)
```

### User Experience Issue

When testing the `ardalis-clean-architecture` template:

```bash
# 1. Created template on macOS VM
/template-create  # Wrote to repo: ~/Projects/Github/guardkit/installer/global/templates/

# 2. Tried to use template immediately
guardkit init ardalis-clean-architecture
# ⚠️ Result: "Template 'ardalis-clean-architecture' not found, using default"

# 3. Had to run installer to make template available
./installer/scripts/install.sh
# ✅ Now template is available
```

**User Observation**: "I think it should have been written to the .agentecflow directory potentially"

## Investigation Questions

### 1. Intended Design vs. Actual Behavior

**Question**: Is the current behavior (repo → install.sh → global) the **intended design**, or is it an oversight?

**Scenarios to Consider:**

#### Scenario A: Current Design is Intentional
**Rationale:**
- Templates are **development artifacts** meant to be version-controlled
- Separation of concerns: Development (repo) vs. Deployment (global)
- Allows for template review/testing before installation
- Multiple templates can be created in a session, then batch-installed
- Supports CI/CD workflows (create templates, commit, install from repo)

**If this is correct**: Documentation should clarify this workflow

#### Scenario B: Design Should Be Direct-to-Global
**Rationale:**
- Immediate availability after creation (better UX)
- One-step process: Create → Use (no install step)
- Templates are user-specific, not necessarily for version control
- Simpler mental model for users

**If this is correct**: Need to refactor `/template-create` command

#### Scenario C: Hybrid Approach (Best of Both)
**Rationale:**
- Default: Write to global (immediate use)
- Optional flag: Write to repo for version control (`--to-repo`)
- Supports both use cases

**If this is correct**: Need to add `--output-location` parameter

### 2. Template Lifecycle Considerations

**Question**: What is the intended lifecycle of a created template?

**Possible Lifecycles:**

**Lifecycle 1: Personal Use**
```bash
User creates template from their codebase
└─> Template is for THEIR projects only
    └─> Should go directly to ~/.agentecflow/templates/
```

**Lifecycle 2: Team/Organization Use**
```bash
User creates template for team
└─> Template should be reviewed and tested
    └─> Goes to repo first (installer/global/templates/)
        └─> Team reviews, commits to git
            └─> install.sh distributes to team members
```

**Lifecycle 3: Public Distribution**
```bash
Template creator develops template
└─> Template goes to repo
    └─> Gets reviewed and polished
        └─> Committed to GitHub (guardkit repository)
            └─> install.sh makes it available globally
```

### 3. Installation Script Role

**Question**: Should `install.sh` be REQUIRED to use created templates, or should it be OPTIONAL?

**Option A: Required (Current Behavior)**
- Templates are always installed via `install.sh`
- Consistent with global agent/command installation
- Pro: Centralized installation process
- Con: Extra step for personal templates

**Option B: Optional (Direct Creation)**
- Templates created directly to global location
- `install.sh` only needed for repo-based templates
- Pro: Faster personal workflow
- Con: Two different template sources

### 4. Use Case Analysis

Let's evaluate which approach best serves different user types:

#### Use Case 1: Solo Developer (Personal Templates)
**Scenario**: Developer creates template from their own codebase for their own use.

**Current Workflow** (repo → install → global):
```bash
/template-create  # Creates in repo
./installer/scripts/install.sh  # Install to global
guardkit init my-template  # Use it
```
**Rating**: ⚠️ Extra step (install.sh) feels unnecessary

**Direct-to-Global Workflow**:
```bash
/template-create  # Creates in ~/.agentecflow/templates/
guardkit init my-template  # Use immediately
```
**Rating**: ✅ Streamlined, immediate use

---

#### Use Case 2: Team Lead (Shared Templates)
**Scenario**: Team lead creates template for entire team to use.

**Current Workflow** (repo → git → team install):
```bash
/template-create  # Creates in repo
git add installer/global/templates/team-template/
git commit -m "Add team template"
git push
# Team members pull and run install.sh
```
**Rating**: ✅ Clear separation, version control built-in

**Direct-to-Global Workflow**:
```bash
/template-create --to-repo  # Explicitly write to repo
git add installer/global/templates/team-template/
git commit -m "Add team template"
git push
# Team members pull and run install.sh
```
**Rating**: ✅ Same workflow, more explicit

---

#### Use Case 3: Open Source Contributor (Public Templates)
**Scenario**: Contributor creates template for guardkit repository.

**Current Workflow**:
```bash
/template-create  # Creates in repo (correct!)
# Review template quality
git add installer/global/templates/new-template/
git commit -m "Add new template"
git push
# Create PR for guardkit repo
```
**Rating**: ✅ Perfect - templates are in repo as artifacts

---

#### Use Case 4: Template Development/Testing
**Scenario**: Developer iterating on template creation.

**Current Workflow**:
```bash
/template-create  # Version 1 in repo
./installer/scripts/install.sh  # Install
guardkit init test-template  # Test
# Find issues, recreate template
/template-create  # Version 2 in repo (overwrites)
./installer/scripts/install.sh  # Reinstall
guardkit init test-template  # Test again
```
**Rating**: ⚠️ Reinstall step is tedious during iteration

**Direct-to-Global Workflow**:
```bash
/template-create  # Version 1 in global (immediate)
guardkit init test-template  # Test immediately
# Find issues, recreate
/template-create --overwrite  # Version 2 (overwrites in global)
guardkit init test-template  # Test immediately
```
**Rating**: ✅ Faster iteration cycle

## Evaluation Criteria

### Factor 1: User Experience (UX)
- **Simplicity**: How easy is it for users to create and use templates?
- **Clarity**: Is the workflow intuitive?
- **Speed**: How quickly can users go from creation to usage?

### Factor 2: Flexibility
- **Personal Use**: Does it support solo developers?
- **Team Use**: Does it support team distribution?
- **Public Use**: Does it support open-source contributions?

### Factor 3: Consistency
- **Command Pattern**: Does it match other GuardKit commands?
- **Installation Model**: Does it align with agent/command installation?

### Factor 4: Maintainability
- **Code Simplicity**: How complex is the implementation?
- **Documentation**: How much explanation is needed?

## Proposed Solutions

### Solution A: Keep Current Behavior (Repo-First)

**What**: No changes. Templates always created in repo.

**Implementation**: None (already implemented)

**Pros**:
- ✅ Consistent with current codebase
- ✅ No refactoring needed
- ✅ Works well for team/public templates
- ✅ Clear separation of development vs deployment

**Cons**:
- ❌ Extra step for personal templates
- ❌ Confusing for solo developers
- ❌ install.sh required every time

**Acceptance**: Document workflow clearly in CLAUDE.md

---

### Solution B: Direct-to-Global (Personal-First)

**What**: Change `/template-create` to write directly to `~/.agentecflow/templates/`

**Implementation**:
```bash
# Change target directory
TEMPLATE_DIR="$HOME/.agentecflow/templates/$TEMPLATE_NAME"
```

**Pros**:
- ✅ Immediate template availability
- ✅ Better UX for solo developers
- ✅ Faster iteration during development

**Cons**:
- ❌ Breaks team distribution workflow
- ❌ Templates not in version control by default
- ❌ Inconsistent with agent installation model

**Acceptance**: Refactor `/template-create` command

---

### Solution C: Hybrid with Flag (Recommended)

**What**: Default to global, but allow repo output via flag

**Implementation**:
```bash
/template-create --output-location=global   # Default
/template-create --output-location=repo     # For distribution
/template-create -o repo                    # Short form
```

**Pros**:
- ✅ Supports all use cases
- ✅ Defaults to better UX (immediate use)
- ✅ Explicit for team/public templates
- ✅ Maintains flexibility

**Cons**:
- ⚠️ Adds command complexity
- ⚠️ Need to document both options

**Acceptance**: Implement `--output-location` parameter

---

### Solution D: Smart Detection (Most User-Friendly)

**What**: Detect context and choose automatically

**Implementation Logic**:
```bash
if [[ inside guardkit repo ]]; then
    OUTPUT_DIR="installer/global/templates/"
    echo "📦 Template for distribution (in repo)"
elif [[ --to-repo flag ]]; then
    OUTPUT_DIR="installer/global/templates/"
    echo "📦 Template for distribution"
else
    OUTPUT_DIR="$HOME/.agentecflow/templates/"
    echo "👤 Template for personal use (in global)"
fi
```

**Pros**:
- ✅ Best UX (smart defaults)
- ✅ No flag needed for common case
- ✅ Still supports all workflows
- ✅ Clear feedback on where template was created

**Cons**:
- ⚠️ "Magic" behavior might surprise users
- ⚠️ More complex implementation

**Acceptance**: Implement context detection + `--to-repo` override

---

## Acceptance Criteria

- [ ] **AC1**: Investigation documented with clear analysis of all use cases
- [ ] **AC2**: Decision made on which solution to implement (A, B, C, or D)
- [ ] **AC3**: Decision rationale documented (why chosen solution is best)
- [ ] **AC4**: If changes needed, implementation plan documented
- [ ] **AC5**: User documentation updated to reflect chosen approach
- [ ] **AC6**: Test scenarios defined for chosen solution
- [ ] **AC7**: Migration path considered (if existing templates affected)
- [ ] **AC8**: Stakeholder feedback gathered (if applicable)

## Testing Scenarios (Post-Decision)

### Scenario 1: Solo Developer - Personal Template
```bash
# Create template from personal project
cd ~/my-project
/template-create

# Expected: Template immediately usable
guardkit init my-custom-template
# ✅ Should work without install.sh
```

### Scenario 2: Team Lead - Distributed Template
```bash
# Create template for team (in guardkit repo)
cd ~/Projects/guardkit
/template-create [appropriate-flag]

# Expected: Template in repo for version control
git status
# ✅ Should show: installer/global/templates/team-template/
```

### Scenario 3: Template Iteration
```bash
# Create, test, recreate loop
/template-create
guardkit init test-template  # Test v1
/template-create --overwrite  # Recreate
guardkit init test-template  # Test v2
# ✅ Should complete quickly without install.sh
```

## Related Files

```
installer/
├── scripts/
│   └── install.sh ← Copies templates repo → global
└── global/
    └── templates/ ← Current template creation target

~/.agentecflow/
└── templates/ ← Where guardkit init reads from

installer/global/commands/
└── template-create.md ← Command that creates templates
```

## Decision Framework

Use this framework to make the final decision:

| Criterion | Weight | Solution A (Repo) | Solution B (Global) | Solution C (Hybrid) | Solution D (Smart) |
|-----------|--------|-------------------|---------------------|---------------------|-------------------|
| Personal Use UX | 30% | 4/10 | 9/10 | 8/10 | 9/10 |
| Team Distribution | 25% | 9/10 | 3/10 | 8/10 | 9/10 |
| Implementation Complexity | 20% | 10/10 | 7/10 | 6/10 | 5/10 |
| Documentation Clarity | 15% | 7/10 | 8/10 | 6/10 | 8/10 |
| Consistency | 10% | 8/10 | 5/10 | 7/10 | 7/10 |
| **Weighted Score** | - | **7.0** | **6.5** | **7.2** | **7.9** |

**Preliminary Recommendation**: Solution D (Smart Detection) scores highest

## Questions for Discussion

1. What percentage of users will create templates for personal use vs. team/public distribution?
2. Is the extra `install.sh` step acceptable for team/public templates?
3. Should we optimize for the most common use case?
4. How important is consistency with the current agent installation model?
5. Are users aware of the `installer/global/templates/` vs `~/.agentecflow/templates/` distinction?

## Next Steps

1. **Gather Context**: Review original design intentions (if documented)
2. **User Feedback**: Get input from early users (if any)
3. **Prototype**: Test Solution D (Smart Detection) in isolated environment
4. **Document**: Update CLAUDE.md with clear explanation of chosen approach
5. **Implement**: Make changes if decision is not Solution A

## References

- **Discovery Context**: Template analysis conversation, Section "The Template Installation Flow"
- **Related Issue**: TASK-018 (clean-architecture-specialist agent mismatch)
- **Template Tested**: `ardalis-clean-architecture` (generated from CleanArchitecture-ardalis repo)

---

**Created during**: Template Analysis Task
**Conversation Section**: "The Template Installation Flow"
**User Quote**: "I think it should have been written to the .agentecflow directory potentially, I suppose the way it's done it we would run the install.sh script again to make the new template available assuming the template is included in the installer?"
