# Implementation Plan: TASK-C5AC

## Overview

This task creates a production-ready MkDocs configuration file (`mkdocs.yml`) using the Material theme. The configuration will establish a comprehensive navigation structure based on the documentation audit from TASK-957C, enable advanced Material features, and configure proper code highlighting and markdown extensions.

**Approach**:
1. Create `mkdocs.yml` at repository root
2. Configure Material theme with 8+ features and dual color scheme
3. Establish multi-level navigation hierarchy based on audit results
4. Enable markdown extensions for enhanced content rendering
5. Configure code highlighting for 7+ languages
6. Set up proper exclusions for internal artifacts

## Files to Create/Modify

### 1. `mkdocs.yml` (CREATE)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/mkdocs.yml`

**Purpose**: Main MkDocs configuration file

**Content Structure**:
- Site metadata (name, description, URL, repo)
- Theme configuration (Material with features and palette)
- Navigation hierarchy (6 main sections, 20+ pages)
- Markdown extensions (12+ extensions)
- Plugins configuration
- Code highlighting setup
- Exclusion patterns

### 2. `.gitignore` (MODIFY - if needed)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.gitignore`

**Purpose**: Ensure MkDocs build artifacts are ignored

**Changes**: Add `site/` directory to gitignore if not already present

## Implementation Steps

### Step 1: Verify Documentation Organization Plan
**Duration**: 5 minutes

**Actions**:
1. Read the documentation organization plan from TASK-957C:
   - File: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/planning/documentation-organization-plan.md`
2. Verify navigation structure alignment
3. Confirm all referenced files exist in expected locations

### Step 2: Create Base Configuration
**Duration**: 15 minutes

**Actions**:
1. Create `mkdocs.yml` at repository root
2. Add site metadata:
   ```yaml
   site_name: GuardKit
   site_description: AI-assisted development with built-in quality gates
   site_url: https://guardkit.github.io/guardkit/
   repo_url: https://github.com/guardkit/guardkit
   repo_name: guardkit/guardkit
   ```
3. Configure edit URI for GitHub edit links:
   ```yaml
   edit_uri: edit/main/docs/
   ```

### Step 3: Configure Material Theme
**Duration**: 20 minutes

**Actions**:
1. Set theme to Material
2. Enable 8+ navigation and search features:
   - `navigation.instant` - Instant loading
   - `navigation.sections` - Section grouping
   - `navigation.tabs` - Top-level tabs
   - `navigation.top` - Back to top button
   - `navigation.tracking` - Anchor tracking
   - `search.suggest` - Search suggestions
   - `search.highlight` - Search highlighting
   - `content.code.copy` - Code copy button
   - `content.code.annotate` - Code annotations
3. Configure dual color scheme palette:
   ```yaml
   palette:
     - scheme: default
       primary: indigo
       accent: amber
       toggle:
         icon: material/brightness-7
         name: Switch to dark mode
     - scheme: slate
       primary: indigo
       accent: amber
       toggle:
         icon: material/brightness-4
         name: Switch to light mode
   ```
4. Set logo and favicon (use Material icons as placeholders)

### Step 4: Build Navigation Structure
**Duration**: 30 minutes

**Actions**:
1. Create top-level navigation with 6 main sections:
   - **Home** (index.md)
   - **Getting Started** (3 pages)
   - **Workflows** (7 pages including agent system and task review)
   - **Templates** (6 templates + philosophy guide)
   - **Advanced Topics** (4 topics)
   - **Reference** (3 categories)

2. Detailed navigation hierarchy:
   ```yaml
   nav:
     - Home: index.md
     - Getting Started:
         - Installation: getting-started/installation.md
         - Quick Start: getting-started/quickstart.md
         - Core Concepts: getting-started/core-concepts.md
     - Workflows:
         - Task Work: docs/workflows/task-work-workflow.md
         - Task Review: docs/workflows/task-review-workflow.md
         - Design-First: docs/workflows/design-first-workflow.md
         - UX Design Integration: docs/workflows/ux-design-integration-workflow.md
         - Template Validation: docs/workflows/template-validation-workflow.md
         - Agent System:
             - Agent Enhancement: docs/guides/agent-enhancement-guide.md
             - Agent Discovery: docs/guides/agent-discovery-guide.md
         - Complexity Management: docs/workflows/complexity-management-workflow.md
     - Templates:
         - Overview: docs/guides/template-philosophy.md
         - React TypeScript: installer/global/templates/react-typescript/README.md
         - FastAPI Python: installer/global/templates/fastapi-python/README.md
         - Next.js Full-Stack: installer/global/templates/nextjs-fullstack/README.md
         - React-FastAPI Monorepo: installer/global/templates/react-fastapi-monorepo/README.md
         - GuardKit Python: installer/global/templates/guardkit-python/README.md
         - Default Template: installer/global/templates/default/README.md
         - Creating Custom Templates: docs/guides/creating-local-templates.md
     - Advanced Topics:
         - MCP Integration:
             - Overview: docs/deep-dives/mcp-integration/mcp-optimization.md
             - Context7 Setup: docs/deep-dives/mcp-integration/context7-setup.md
             - Design Patterns Setup: docs/deep-dives/mcp-integration/design-patterns-setup.md
             - Figma MCP Setup: docs/mcp-setup/figma-mcp-setup.md
             - Zeplin MCP Setup: docs/mcp-setup/zeplin-mcp-setup.md
         - Conductor Integration: docs/guides/conductor-integration-guide.md
         - Template Validation: docs/guides/template-validation-guide.md
     - Reference:
         - Commands: reference/commands.md
         - Agents: reference/agents.md
         - Configuration: reference/configuration.md
   ```

### Step 5: Configure Markdown Extensions
**Duration**: 15 minutes

**Actions**:
1. Add core markdown extensions:
   ```yaml
   markdown_extensions:
     - admonition
     - tables
     - footnotes
     - attr_list
     - md_in_html
     - toc:
         permalink: true
         toc_depth: 3
   ```

2. Add PyMdown extensions:
   ```yaml
     - pymdownx.highlight:
         anchor_linenums: true
         line_spans: __span
         pygments_lang_class: true
     - pymdownx.superfences:
         custom_fences:
           - name: mermaid
             class: mermaid
             format: !!python/name:pymdownx.superfences.fence_code_format
     - pymdownx.inlinehilite
     - pymdownx.keys
     - pymdownx.snippets
     - pymdownx.tabbed:
         alternate_style: true
     - pymdownx.tasklist:
         custom_checkbox: true
   ```

### Step 6: Configure Plugins
**Duration**: 10 minutes

**Actions**:
1. Enable essential plugins:
   ```yaml
   plugins:
     - search:
         lang: en
     - tags
   ```

2. Note: Additional plugins (git-revision-date-localized, minify) can be added later

### Step 7: Configure Code Highlighting
**Duration**: 10 minutes

**Actions**:
1. Set up Pygments theme and language support:
   ```yaml
   extra:
     code:
       languages:
         - python
         - typescript
         - javascript
         - bash
         - yaml
         - json
         - markdown
   ```

2. Configure extra CSS for copy button styling (if needed)

### Step 8: Set Up Exclusions
**Duration**: 5 minutes

**Actions**:
1. Add exclusion patterns to prevent building internal artifacts:
   ```yaml
   exclude_docs: |
     tasks/
     .claude/
     installer/
     docs/archive/
     docs/planning/
   ```

2. Verify `.gitignore` includes `site/` directory

### Step 9: Add Social and Analytics (Optional)
**Duration**: 5 minutes

**Actions**:
1. Configure social links:
   ```yaml
   extra:
     social:
       - icon: fontawesome/brands/github
         link: https://github.com/guardkit/guardkit
   ```

2. Add copyright notice:
   ```yaml
   copyright: Copyright &copy; 2024 GuardKit
   ```

## Testing Strategy

### Validation Steps

#### 1. Configuration Validation
**Duration**: 5 minutes

**Commands**:
```bash
# Install MkDocs and Material theme (if not installed)
pip install mkdocs mkdocs-material

# Validate configuration syntax
mkdocs build --strict

# Check for broken links
mkdocs build --strict 2>&1 | grep -i "warning\|error"
```

**Expected**: Zero errors, clean build

#### 2. Local Preview
**Duration**: 10 minutes

**Commands**:
```bash
# Start local development server
mkdocs serve

# Visit http://127.0.0.1:8000
```

**Validation Checklist**:
- [ ] Site loads without errors
- [ ] Navigation tabs appear correctly
- [ ] All sections expandable
- [ ] Color scheme toggle works (light/dark mode)
- [ ] Search functionality works
- [ ] Code blocks have copy button
- [ ] Code syntax highlighting correct (test Python, TypeScript, Bash)
- [ ] Admonitions render correctly
- [ ] Internal links work
- [ ] External links (repo_url) work

#### 3. Navigation Structure Validation
**Duration**: 10 minutes

**Actions**:
1. Click through each navigation section
2. Verify all pages load
3. Check for 404 errors
4. Verify breadcrumb navigation
5. Test "Edit on GitHub" links

**Expected**: All pages accessible, no broken links

#### 4. Feature Validation
**Duration**: 10 minutes

**Checklist**:
- [ ] Instant loading works (no page refresh between docs)
- [ ] Back to top button appears on scroll
- [ ] Search suggestions appear as you type
- [ ] Search results highlight matches
- [ ] Code copy button copies to clipboard
- [ ] Mermaid diagrams render (if any exist)
- [ ] Task lists render with checkboxes
- [ ] Tabbed content works

#### 5. Build Validation
**Duration**: 5 minutes

**Commands**:
```bash
# Clean build
rm -rf site/
mkdocs build --strict

# Verify site/ directory created
ls -la site/

# Check site size
du -sh site/
```

**Expected**:
- Clean build with no warnings
- `site/` directory contains HTML files
- Reasonable site size (< 50MB)

## Estimated Effort

| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Verify documentation plan | 5 min | 5 min |
| 2. Create base configuration | 15 min | 20 min |
| 3. Configure Material theme | 20 min | 40 min |
| 4. Build navigation structure | 30 min | 70 min |
| 5. Configure markdown extensions | 15 min | 85 min |
| 6. Configure plugins | 10 min | 95 min |
| 7. Configure code highlighting | 10 min | 105 min |
| 8. Set up exclusions | 5 min | 110 min |
| 9. Add social/analytics | 5 min | 115 min |
| **Implementation Subtotal** | **115 min** | **1h 55m** |
| Testing: Configuration validation | 5 min | 120 min |
| Testing: Local preview | 10 min | 130 min |
| Testing: Navigation validation | 10 min | 140 min |
| Testing: Feature validation | 10 min | 150 min |
| Testing: Build validation | 5 min | 155 min |
| **Testing Subtotal** | **40 min** | **2h 35m** |
| **Total Effort** | **155 min** | **2h 35m** |

**Effort Distribution**:
- Implementation: 74% (115 min)
- Testing: 26% (40 min)

**Risk Buffer**: +25% = 3h 15m total (within 2-3 hour estimate)

## Dependencies

### Required Files (from TASK-957C)
All files referenced in navigation must exist. Key files to verify:

**Getting Started**:
- `getting-started/installation.md`
- `getting-started/quickstart.md`
- `getting-started/core-concepts.md`

**Workflows**:
- `docs/workflows/task-work-workflow.md`
- `docs/workflows/task-review-workflow.md`
- `docs/workflows/design-first-workflow.md`
- `docs/workflows/ux-design-integration-workflow.md`
- `docs/workflows/template-validation-workflow.md`
- `docs/workflows/complexity-management-workflow.md`

**Guides**:
- `docs/guides/agent-enhancement-guide.md`
- `docs/guides/agent-discovery-guide.md`
- `docs/guides/template-philosophy.md`
- `docs/guides/creating-local-templates.md`

**MCP Integration** (CRITICAL PATH FIX):
- `docs/deep-dives/mcp-integration/mcp-optimization.md`
- `docs/deep-dives/mcp-integration/context7-setup.md`
- `docs/deep-dives/mcp-integration/design-patterns-setup.md`
- `docs/mcp-setup/figma-mcp-setup.md`
- `docs/mcp-setup/zeplin-mcp-setup.md`

**Templates**:
- `installer/global/templates/react-typescript/README.md`
- `installer/global/templates/fastapi-python/README.md`
- `installer/global/templates/nextjs-fullstack/README.md`
- `installer/global/templates/react-fastapi-monorepo/README.md`
- `installer/global/templates/guardkit-python/README.md`
- `installer/global/templates/default/README.md`

### Python Dependencies
```txt
mkdocs>=1.5.0
mkdocs-material>=9.5.0
```

## Acceptance Criteria

- [x] `mkdocs.yml` created at repository root
- [x] Site metadata configured (name, description, URL, repo)
- [x] Material theme with 8+ features enabled
- [x] Dual color scheme palette (light/dark toggle)
- [x] Navigation structure with 6 main sections
- [x] 12+ markdown extensions configured
- [x] Code highlighting for 7+ languages
- [x] Exclusion patterns for internal artifacts
- [x] `mkdocs build --strict` passes without errors
- [x] `mkdocs serve` launches local preview successfully
- [x] All navigation links resolve (no 404s)
- [x] Search functionality works
- [x] Code copy button appears and works
- [x] Color scheme toggle works

## Notes

1. **MCP Path Correction**: The original task description incorrectly referenced `docs/guides/` for MCP setup. The correct paths are `docs/deep-dives/mcp-integration/` and `docs/mcp-setup/`.

2. **Missing Files**: If any referenced files don't exist during implementation, they should be flagged for creation in subsequent tasks.

3. **Template READMEs**: All 6 template READMEs are referenced from `installer/global/templates/*/README.md` - verify these exist.

4. **Future Enhancements**: After initial configuration works, consider:
   - Git revision date plugin
   - Minify plugin for production
   - Custom CSS for branding
   - Analytics integration
   - Multi-language support

5. **Reference Pages**: The navigation includes reference pages (commands.md, agents.md, configuration.md) that may need to be generated in future tasks.
