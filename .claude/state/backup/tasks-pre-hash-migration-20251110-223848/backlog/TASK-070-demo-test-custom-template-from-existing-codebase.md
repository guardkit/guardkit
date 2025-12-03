# TASK-070: Demo/Test - Create Custom Template from Existing Codebase

**Created**: 2025-01-10
**Priority**: High
**Type**: Testing & Demo
**Parent**: Template Strategy Validation
**Status**: backlog
**Complexity**: Medium (6/10)
**Estimated Effort**: 4-6 hours
**Dependencies**: None

---

## Problem Statement

One of GuardKit's key value propositions is the ability to extract templates from **existing, proven codebases** rather than starting from scratch. However, this workflow hasn't been thoroughly tested or documented for demos.

**Current State**: The `/template-create` command exists and works, but:
- No documented examples of extracting templates from real codebases
- No demo content showing the process
- No validation that extracted templates work in real scenarios
- No best practices for selecting source codebases

**Desired State**: Comprehensive demo and documentation showing how to:
1. Select a suitable existing codebase
2. Use `/template-create` to extract a template
3. Validate the generated template
4. Use the template to create new projects
5. Document the process for blog posts and videos

---

## Context

**Template Philosophy** (from CLAUDE.md):
> Your production code is better than any generic template. Create templates from what you've proven works.

**Use Cases**:
1. **Team Templates**: Extract patterns from successful team projects
2. **Client Templates**: Create reusable starting points for similar client projects
3. **Personal Templates**: Codify your own best practices
4. **Migration Templates**: Preserve architecture when starting new versions

**Ideal Source Codebases**:
- Production-ready projects (not prototypes)
- Well-structured with clear patterns
- Good test coverage
- Complete implementation (not partial)
- Size: 3,000-15,000 LOC (manageable but substantial)

**Candidate Codebases for Demo**:
1. **Public GitHub Repos**: Well-maintained open source projects
2. **GuardKit Itself**: Already proven (16K LOC, high quality)
3. **Example Apps**: Realworld.io implementations
4. **Personal Projects**: Your own proven codebases

---

## Objectives

### Primary Objective
Demonstrate and document the complete workflow for extracting a custom template from an existing codebase, validating it, and using it to create new projects.

### Success Criteria
- [ ] Suitable source codebase selected and documented
- [ ] Template extracted using `/template-create`
- [ ] Template validated with Level 2 validation (≥8.0/10)
- [ ] Template used to initialize 2+ new projects successfully
- [ ] Complete demo script created (blog-ready)
- [ ] Video outline created with timestamps
- [ ] Screenshots captured of entire process
- [ ] Best practices documented for template extraction
- [ ] Common pitfalls and solutions identified
- [ ] Before/after comparison documented

---

## Implementation Scope

### Phase 1: Select Source Codebase

**Criteria for Selection**:
- Production-ready and battle-tested
- Clear architectural patterns
- Good test coverage (≥70%)
- Size: 3,000-15,000 LOC (sweet spot)
- Open source or permission to use

**Option 1: Use RealWorld Example** (Recommended for Demo)
```bash
# Clone RealWorld React + Redux implementation
git clone https://github.com/gothinkster/react-redux-realworld-example-app.git
cd react-redux-realworld-example-app

# Analyze codebase
cloc .
# Expected: ~5,000-10,000 LOC

# Verify tests exist
npm install
npm test
```

**Option 2: Use Your Own Project**
```bash
# Use a proven personal or team project
# Requirements:
# - Production-ready
# - Clear patterns
# - Good test coverage
# - Complete implementation
```

**Option 3: Use Smaller Production App**
```bash
# Find suitable candidate on GitHub
# Search criteria:
# - Stars: 1,000+ (indicates quality)
# - Last commit: Within 6 months (actively maintained)
# - Has tests: Yes
# - Size: Medium (not too small or large)
```

**Document Selection**:
Create `source-codebase-selection.md`:
```markdown
# Source Codebase Selection

## Selected Project
- **Name**: [Project Name]
- **URL**: [GitHub URL]
- **Language/Stack**: [Tech stack]
- **Size**: [LOC count]
- **Quality Indicators**:
  - Stars: [count]
  - Test Coverage: [percentage]
  - Last Updated: [date]
  - Architecture: [pattern description]

## Why This Project?
- [Reason 1]
- [Reason 2]
- [Reason 3]

## Patterns to Extract
- [Pattern 1]
- [Pattern 2]
- [Pattern 3]
```

### Phase 2: Prepare Source Codebase

**Clean Up Before Extraction**:
```bash
cd [source-codebase-directory]

# Remove unnecessary files
rm -rf .git
rm -rf node_modules
rm -rf venv
rm -rf __pycache__
rm -rf .pytest_cache
rm -rf coverage
rm -rf dist
rm -rf build

# Remove sensitive files
rm -f .env
rm -f .env.local
rm -f config/production.yml

# Verify structure
tree -L 3 -I 'node_modules|venv|__pycache__|.git'
```

**Document Current State**:
```bash
# Take screenshots
# 1. Project structure in file explorer
# 2. Key files in editor
# 3. Test results
# 4. Running application

# Document statistics
cloc . > codebase-stats.txt
```

### Phase 3: Extract Template with /template-create

**Backup .claude Directory** (if exists):
```bash
# If source codebase has .claude, backup it
if [ -d .claude ]; then
  mv .claude .claude.backup
fi
```

**Run Template Creation**:
```bash
# Use SlashCommand tool
/template-create --validate --output-location=repo
```

**Interactive Prompts** (example for RealWorld React):
```
Template name? realworld-react-redux
Template description? Production-grade React + Redux application based on RealWorld spec
Technology stack? react-typescript
Author? [Your Name]
Version? 1.0.0
```

**Expected Output**:
```
installer/global/templates/realworld-react-redux/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── README.md
├── validation-report.md
└── templates/
    ├── src/
    ├── tests/
    ├── package.json
    └── ...
```

**Restore .claude** (if backed up):
```bash
if [ -d .claude.backup ]; then
  mv .claude.backup .claude
fi
```

### Phase 4: Review and Enhance Template

**Review Validation Report**:
```bash
# Use Read tool
cat installer/global/templates/realworld-react-redux/validation-report.md
```

**Check Quality Score**:
- Target: ≥8.0/10
- If <8.0: Run comprehensive audit (`/template-validate`)

**Review Manifest**:
```bash
# Check placeholders are correct
cat installer/global/templates/realworld-react-redux/manifest.json
```

**Verify Placeholders**:
```json
{
  "placeholders": {
    "ProjectName": { ... },
    "project-name": { ... },
    "description": { ... },
    "author": { ... }
  }
}
```

**Enhance CLAUDE.md** (if needed):
```bash
# Use Edit tool to add:
# - Pattern explanations
# - Architecture notes
# - Best practices
# - Common pitfalls
```

### Phase 5: Test Template Initialization

**Test 1: Initialize First Project**:
```bash
# Create test workspace
mkdir -p ~/template-test-workspace/project-1
cd ~/template-test-workspace/project-1

# Initialize with custom template
guardkit init realworld-react-redux

# Prompts:
# ProjectName: BlogPlatform
# project-name: blog-platform
# description: A blogging platform for developers
# author: Test User

# Verify structure
tree -L 2
```

**Verify Placeholder Substitution**:
```bash
# Check that placeholders were replaced
grep -r "ProjectName" src/
# Should NOT find literal "{{ProjectName}}"

grep -r "blog-platform" src/
# SHOULD find actual project name
```

**Test Installation**:
```bash
# Install dependencies
npm install
# Expected: Clean install with no errors

# Run tests
npm test
# Expected: All tests pass

# Run development server
npm run dev
# Expected: App runs on http://localhost:5173

# Build production
npm run build
# Expected: Build succeeds
```

**Test 2: Initialize Second Project** (Different Parameters):
```bash
cd ~/template-test-workspace/project-2
guardkit init realworld-react-redux

# Prompts:
# ProjectName: ForumApp
# project-name: forum-app
# description: A community forum application
# author: Test User

# Verify it works independently
npm install
npm test
npm run dev
```

### Phase 6: Document Extraction Process

**Create Blog Post** (`docs/demos/custom-template-extraction-blog.md`):
```markdown
# Creating a Custom Template from Your Production Codebase

## Introduction
You've built a successful application. Now you want to replicate that success for your next project. With GuardKit's `/template-create` command, you can extract a template from any existing codebase in minutes.

## Why Extract Templates?
- Preserve proven patterns
- Speed up new projects
- Ensure consistency across projects
- Share best practices with team

## Step-by-Step Guide

### 1. Choose Your Source Codebase
[Selection criteria...]

### 2. Prepare the Codebase
[Cleanup steps...]

### 3. Extract the Template
```bash
/template-create --validate --output-location=repo
```
[Interactive prompts...]

### 4. Review Validation Report
[What to look for...]

### 5. Test Your Template
[Initialization steps...]

### 6. Share with Team
[Distribution options...]

## Best Practices
- Start with production-ready code
- Clean up before extraction
- Validate thoroughly
- Test with multiple projects
- Document patterns

## Common Pitfalls
- Including .env files (security risk)
- Not cleaning node_modules/venv
- Hardcoded values instead of placeholders
- Missing test coverage

## Conclusion
[Summary and next steps...]
```

**Create Video Script** (`docs/demos/custom-template-extraction-video.md`):
```markdown
# Custom Template Extraction - Video Script

## Opening (0:00-0:45)
- **Hook**: "What if you could turn any successful project into a reusable template in 5 minutes?"
- **Problem**: Starting new projects from scratch wastes time and loses proven patterns
- **Solution**: GuardKit's `/template-create` extracts templates from existing code
- **What we'll cover**: Complete workflow from codebase to template to new project

## Demo Part 1: Select and Prepare (0:45-2:00)
- Show example codebase (RealWorld React)
- Explain why it's a good candidate
- Walk through cleanup process
- Show before state (structure, patterns)

## Demo Part 2: Extract Template (2:00-4:00)
- Run `/template-create` command
- Show interactive prompts
- Explain what's happening (analysis, placeholder detection)
- Show generated template structure
- Review validation report

## Demo Part 3: Test Template (4:00-6:30)
- Initialize new project from template
- Show placeholder substitution
- Install dependencies
- Run tests
- Start development server
- Show working application

## Demo Part 4: Second Project (6:30-7:30)
- Initialize another project (different name)
- Show how quickly it works the second time
- Demonstrate reusability

## Explanation (7:30-9:00)
- Explain quality gates (validation)
- Discuss placeholder system
- Highlight customization options
- Show where to learn more

## Closing (9:00-10:00)
- Recap process
- Call to action: Extract your own templates
- Point to documentation
- Thank viewers
```

### Phase 7: Create Before/After Comparison

**Document Transformation** (`docs/demos/template-extraction-comparison.md`):
```markdown
# Template Extraction: Before and After

## Source Codebase (Before)

### Structure
```
realworld-react/
├── src/
│   ├── components/
│   ├── api/
│   └── ...
├── package.json (hardcoded name: "realworld-react")
└── README.md (project-specific)
```

### Characteristics
- Hardcoded project name: "realworld-react"
- Specific README content
- No placeholders
- Single-use codebase

## Generated Template (After)

### Structure
```
installer/global/templates/realworld-react-redux/
├── manifest.json (placeholders defined)
├── CLAUDE.md (pattern documentation)
├── README.md (template usage guide)
├── validation-report.md (quality: 8.5/10)
└── templates/
    ├── src/
    ├── package.json (name: "{{project-name}}")
    └── README.md (template: "{{description}}")
```

### Characteristics
- Placeholder system: {{ProjectName}}, {{project-name}}
- Reusable for infinite projects
- Quality validated: 8.5/10
- Documentation included
- Customizable per project

## New Projects (After Template Use)

### Project 1: blog-platform
- Name: "BlogPlatform"
- Initialized in 2 minutes
- All patterns preserved
- Tests passing
- Ready for feature development

### Project 2: forum-app
- Name: "ForumApp"
- Initialized in 2 minutes
- Independent from Project 1
- Same proven architecture
- Ready for customization

## Value Delivered
- Time saved: 4-8 hours per new project
- Quality guaranteed: 8.5/10
- Consistency: 100%
- Reusability: Unlimited
```

### Phase 8: Document Best Practices

**Create Guide** (`docs/guides/template-extraction-best-practices.md`):
```markdown
# Template Extraction Best Practices

## Selecting Source Codebases

### ✅ Good Candidates
- Production-ready applications
- Clear architectural patterns
- Good test coverage (≥70%)
- Complete implementations
- Size: 3,000-15,000 LOC
- Well-documented code

### ❌ Poor Candidates
- Prototypes or POCs
- Inconsistent architecture
- No tests
- Partial implementations
- Too small (<1,000 LOC) or too large (>50,000 LOC)
- Messy or undocumented

## Preparation Checklist

- [ ] Remove .git directory
- [ ] Remove node_modules/venv
- [ ] Remove build artifacts
- [ ] Remove .env files
- [ ] Remove sensitive data
- [ ] Remove IDE-specific files (.vscode, .idea)
- [ ] Ensure tests pass
- [ ] Clean up commented code
- [ ] Remove dead code

## Extraction Process

1. **Analyze First**: Understand patterns before extracting
2. **Clean Thoroughly**: Remove all artifacts and sensitive data
3. **Validate Output**: Always use `--validate` flag
4. **Review Manifest**: Check placeholders are appropriate
5. **Enhance CLAUDE.md**: Add pattern documentation
6. **Test Thoroughly**: Initialize 2+ projects to verify

## Post-Extraction

### Quality Gates
- Validation score: ≥8.0/10
- Placeholder consistency: 100%
- Tests pass: 100%
- Documentation: Complete

### Testing Checklist
- [ ] Initialize project with template
- [ ] Verify placeholder substitution
- [ ] Install dependencies successfully
- [ ] Run tests (all pass)
- [ ] Run development server
- [ ] Build production version
- [ ] Initialize second project (verify reusability)

## Common Issues and Solutions

### Issue 1: Hardcoded Values
**Problem**: Project has hardcoded values that should be placeholders
**Solution**: Edit manifest.json to add placeholders, update template files

### Issue 2: Missing Dependencies
**Problem**: Generated template missing key dependencies
**Solution**: Verify requirements.txt/package.json is complete

### Issue 3: Low Quality Score
**Problem**: Validation score <8.0/10
**Solution**: Run `/template-validate` comprehensive audit, fix identified issues

### Issue 4: Placeholder Substitution Fails
**Problem**: Placeholders not replaced during init
**Solution**: Check manifest.json format, verify placeholder syntax

## Distribution Strategies

### Personal Use
```bash
# Default location (automatic)
~/.agentecflow/templates/your-template/
```

### Team Use
```bash
# Repository location (requires --output-location=repo)
installer/global/templates/your-template/
```

### Public Distribution
1. Create template in repository
2. Validate thoroughly (Level 3 audit)
3. Document patterns in CLAUDE.md
4. Test with multiple users
5. Publish to GitHub/npm/PyPI
```

---

## Acceptance Criteria

### Extraction Process
- [ ] Source codebase selected and documented
- [ ] Codebase prepared (cleaned, validated)
- [ ] Template extracted with `/template-create --validate`
- [ ] Validation score ≥8.0/10
- [ ] Manifest reviewed and enhanced
- [ ] CLAUDE.md reviewed and enhanced

### Template Validation
- [ ] Template initializes successfully (project 1)
- [ ] Placeholder substitution works correctly
- [ ] Dependencies install without errors
- [ ] Tests pass (100%)
- [ ] Development server runs
- [ ] Production build succeeds
- [ ] Second project initializes successfully (project 2)

### Documentation
- [ ] Blog post created and reviewed
- [ ] Video script created with timestamps
- [ ] Before/after comparison documented
- [ ] Best practices guide created
- [ ] Screenshots captured (15+)
- [ ] Common issues documented

### Demo Content
- [ ] Complete demo repository ready
- [ ] Source codebase example preserved
- [ ] Generated template included
- [ ] Two test projects included
- [ ] README guides users through demo

---

## Deliverables

1. **Source Codebase Selection Document** (`source-codebase-selection.md`)
2. **Extracted Template** (`installer/global/templates/[template-name]/`)
3. **Validation Report** (≥8.0/10 score)
4. **Blog Post** (`custom-template-extraction-blog.md`)
5. **Video Script** (`custom-template-extraction-video.md`)
6. **Before/After Comparison** (`template-extraction-comparison.md`)
7. **Best Practices Guide** (`template-extraction-best-practices.md`)
8. **Demo Repository** (GitHub: guardkit-custom-template-demo)
9. **Screenshots** (15+ images of entire process)
10. **Test Projects** (2 initialized projects)

---

## Success Metrics

**Quantitative**:
- Template quality score: ≥8.0/10
- Template initialization success: 100%
- Test pass rate: 100%
- Documentation completeness: 100%
- Screenshots captured: 15+

**Qualitative**:
- Clear demonstration of value proposition
- Confidence in recommending workflow to users
- Identification of any rough edges
- Ready-to-use demo content for marketing
- Comprehensive best practices guide

---

## Related Tasks

- **TASK-069**: Demo/Test - Core Template Usage
- **TASK-071**: Demo/Test - Greenfield Project with Template Creation
- **TASK-072**: Demo/Test - End-to-End GuardKit Workflow
- **TASK-066**: Create GuardKit Python Template

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Depends On**: None
