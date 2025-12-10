# GitHub Pages Deployment Guide

Complete guide for deploying MkDocs documentation to GitHub Pages, based on actual deployment experience.

## Overview

This guide documents the complete process of setting up automated MkDocs documentation deployment to GitHub Pages using GitHub Actions, including all common issues and their solutions.

## Prerequisites

- Repository with MkDocs documentation in `docs/` directory
- `mkdocs.yml` configuration file in repository root
- GitHub Pages enabled in repository settings

## GitHub Actions Workflow Setup

### 1. Create Workflow File

Create `.github/workflows/docs.yml`:

```yaml
name: Build and Deploy MkDocs

on:
  push:
    branches: [main]
    paths:
      - docs/**
      - mkdocs.yml
      - .github/workflows/docs.yml
  workflow_dispatch:

env:
  PYTHON_VERSION: '3.12'

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: 'pages'
  cancel-in-progress: true

jobs:
  build:
    name: Build Documentation
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
          cache-dependency-path: docs/requirements.txt

      - name: Install MkDocs dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r docs/requirements.txt

      - name: Build MkDocs documentation
        run: mkdocs build

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/

  deploy:
    name: Deploy to GitHub Pages
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
        id: deployment
```

### 2. Create Requirements File

Create `docs/requirements.txt`:

```txt
mkdocs>=1.5.3
mkdocs-material>=9.5.0
pymdown-extensions>=10.7
```

## Common Issues and Solutions

### Issue 1: Missing requirements.txt

**Error:**
```
fatal: No such file or directory: docs/requirements.txt
```

**Cause:** Workflow references `docs/requirements.txt` but file doesn't exist.

**Solution:** Create `docs/requirements.txt` with MkDocs dependencies (see above).

---

### Issue 2: Navigation References Non-Existent Files

**Error:**
```
ERROR - Doc file 'getting-started/installation.md' not found
```

**Cause:** `mkdocs.yml` navigation points to files that don't exist.

**Solution:** Update `mkdocs.yml` navigation to match actual file structure:

```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Quick Start: guides/GETTING-STARTED.md
  - Core Concepts: concepts.md
```

---

### Issue 3: Deprecated Artifact Actions

**Error:**
```
This request has been automatically failed because it uses a deprecated
version of `actions/upload-artifact: v3`
```

**Cause:** Using deprecated v3 artifact actions (deprecated April 2024).

**Solution:** Update to v4 for both actions:

```yaml
- uses: actions/upload-artifact@v4
- uses: actions/download-artifact@v4
```

**Better Solution:** Use Pages-specific artifact action (see Issue 6).

---

### Issue 4: Warnings About Excluded Files

**Error:**
```
WARNING - A reference to 'analysis/github-agent-best-practices-analysis.md'
is included in the 'nav' configuration, but this file is excluded from
the built site.
```

**Cause:** Navigation references files in excluded directories.

**Solution:**

1. Add comprehensive exclusions to `mkdocs.yml`:

```yaml
exclude_docs: |
  tasks/
  .claude/
  installer/
  adr/
  analysis/
  archive/
  checklists/
  debugging/
  research/
  planning/
  proposals/
```

2. Remove excluded file references from navigation
3. Update documentation to avoid linking to excluded files

---

### Issue 5: MkDocs Strict Mode Failures

**Error:**
```
Aborted with 58 warnings in strict mode!
WARNING - Doc file 'deep-dives/conductor-integration.md' contains a link
'../../CLAUDE.md', but the target '../CLAUDE.md' is not found
```

**Cause:** Many internal docs reference files intentionally excluded from public site.

**Solution:** Remove `--strict` flag from build command:

```yaml
- name: Build MkDocs documentation
  run: mkdocs build  # Not: mkdocs build --strict
```

**Why this works:**
- Warnings about excluded files are expected and harmless
- These files are intentionally excluded from public documentation
- Actual errors (missing nav files) still cause build failure
- Real issues are caught, harmless warnings are ignored

---

### Issue 6: Artifact Deployment Format Error

**Error:**
```
Deploy to GitHub Pages
Artifact could not be deployed. Please ensure the content does not
contain any hard links, symlinks and total size is less than 10GB.
```

**Cause:** Using `actions/upload-artifact@v4` creates general-purpose artifacts, but `deploy-pages@v4` requires special Pages artifact format.

**Solution:** Use Pages-specific artifact action:

```yaml
- name: Upload Pages artifact
  uses: actions/upload-pages-artifact@v3  # Not: upload-artifact@v4
  with:
    path: site/
```

**Also remove these steps (not needed):**
- `actions/download-artifact@v4` (deploy-pages handles this)
- `actions/configure-pages@v4` (not needed with Actions deployment)

**Modern workflow:**
1. `upload-pages-artifact@v3` creates Pages-specific artifact
2. `deploy-pages@v4` automatically finds and deploys it
3. No manual artifact download needed
4. Simpler, more reliable than legacy gh-pages branch approach

---

### Issue 7: Wrong GitHub Pages Source Setting

**Error:** Build succeeds but site not deployed.

**Cause:** GitHub Pages source set to "Deploy from a branch" instead of "GitHub Actions".

**Solution:**

1. Go to repository Settings → Pages
2. Under "Build and deployment"
3. Set Source to "GitHub Actions" (not "Deploy from a branch")
4. Save changes

---

### Issue 8: Broken Internal Links

**Error:** 404 errors on deployed site for internal documentation links.

**Cause:** Documentation links to files excluded from public site (tasks/, installer/, analysis/, etc.).

**Solution:** Remove links to excluded files:

**Before:**
```markdown
- [Implementation Details](../../tasks/completed/TASK-031/)
- [Git State Helper](../../installer/core/lib/git_state_helper.py)
```

**After:**
```markdown
<!-- Remove links to excluded internal files -->
```

Keep only:
- Links within `docs/` directory
- External links (https://)
- GitHub repository links

---

## Verification Steps

### 1. Verify Workflow Completes

Check GitHub Actions tab:
- Build job shows green checkmark
- Deploy job shows green checkmark
- No error messages in logs

### 2. Verify Site Accessibility

Visit your GitHub Pages URL:
```
https://<username>.github.io/<repository>/
```

Test:
- Homepage loads
- Navigation works
- Search functions
- All pages accessible (no 404s)
- Mobile responsive

### 3. Verify No Console Errors

Open browser DevTools console:
- No JavaScript errors
- No 404 errors for resources
- All links work

---

## Best Practices

### 1. Organize Documentation

```
docs/
├── index.md                    # Homepage
├── guides/                     # User guides
│   ├── getting-started.md
│   └── tutorial.md
├── workflows/                  # Workflow documentation
├── deep-dives/                 # Technical deep dives
└── requirements.txt            # Python dependencies
```

### 2. Navigation Structure

Keep navigation max 3 levels deep:

```yaml
nav:
  - Home: index.md
  - Getting Started:           # Level 1
      - Quick Start: guides/getting-started.md   # Level 2
  - Core Concepts: concepts.md
```

### 3. Exclude Internal Files

Exclude development/internal files from public documentation:

```yaml
exclude_docs: |
  tasks/
  .claude/
  installer/
  research/
  planning/
```

### 4. Link Only to Public Files

- ✅ Link to files in `docs/` directory
- ✅ Link to external resources
- ✅ Link to GitHub repository files
- ❌ Don't link to excluded internal files
- ❌ Don't link to tasks/, installer/, etc.

### 5. Use Relative Paths

Within documentation:
```markdown
[Guide](guides/getting-started.md)           # ✅ Good
[Guide](../guides/getting-started.md)        # ✅ Good
[Guide](/guides/getting-started.md)          # ❌ Avoid absolute paths
```

### 6. Test Locally First

Before pushing:
```bash
mkdocs build
mkdocs serve
# Visit http://127.0.0.1:8000
```

---

## Troubleshooting Checklist

If deployment fails, check:

- [ ] `docs/requirements.txt` exists with all dependencies
- [ ] `mkdocs.yml` navigation matches actual file structure
- [ ] Using `upload-pages-artifact@v3` (not `upload-artifact@v4`)
- [ ] GitHub Pages source set to "GitHub Actions"
- [ ] No links to excluded files in documentation
- [ ] All navigation files actually exist
- [ ] Build completes without errors (warnings OK)
- [ ] Workflow has correct permissions (pages: write, id-token: write)

---

## Migration from Other Systems

### From Legacy gh-pages Branch

**Old approach:**
```yaml
- name: Deploy
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./site
```

**New approach:**
```yaml
- name: Upload Pages artifact
  uses: actions/upload-pages-artifact@v3
  with:
    path: site/

# In separate deploy job:
- name: Deploy to GitHub Pages
  uses: actions/deploy-pages@v4
```

**Benefits:**
- No gh-pages branch to manage
- No custom tokens needed (OIDC authentication)
- Automatic artifact handling
- Simpler rollback (re-run workflow)

---

## Complete Working Example

See [GuardKit's docs.yml](https://github.com/guardkit/guardkit/blob/main/.github/workflows/docs.yml) for a complete, production-ready workflow that handles all these issues correctly.

**Key features:**
- Modern Actions-based deployment
- Comprehensive error handling
- Fast builds with pip caching
- Clear documentation
- All common issues resolved

---

## Additional Resources

- **GitHub Actions for Pages**: https://github.com/actions/deploy-pages
- **MkDocs Documentation**: https://www.mkdocs.org/
- **Material for MkDocs**: https://squidfunk.github.io/mkdocs-material/

---

## Summary

The most common deployment issues and solutions:

1. **Missing requirements.txt** → Create with MkDocs dependencies
2. **Wrong artifact action** → Use `upload-pages-artifact@v3`
3. **Wrong Pages source** → Set to "GitHub Actions" in settings
4. **Broken links** → Remove links to excluded internal files
5. **Strict mode failures** → Remove `--strict` flag
6. **Navigation errors** → Ensure all nav files exist

Follow this guide and you'll have a working GitHub Pages deployment with zero issues.
