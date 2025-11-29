# TASK-DFFA: GitHub Actions MkDocs Deployment Workflow

**Task ID**: TASK-DFFA
**Status**: PLANNING
**Complexity**: 5/10 (Medium)
**Estimated Duration**: 2-3 hours
**Estimated LOC**: 120-150 lines (YAML)

---

## 1. Executive Summary

Design and implement a modern GitHub Actions workflow that automatically builds and deploys MkDocs documentation to GitHub Pages using the modern `actions/deploy-pages@v4` approach. The workflow will include security best practices, performance optimizations, and fail-safe mechanisms.

**Key Deliverable**: `.github/workflows/docs.yml` with automated CI/CD for documentation.

---

## 2. Architecture Overview

### 2.1 Deployment Strategy

**Modern GitHub Pages Deployment** (Recommended Approach):
```
Git Push to main
    ↓
GitHub Actions Triggered (docs.yml)
    ↓
Build Job
  - Setup Python 3.12
  - Cache pip dependencies
  - Install MkDocs + Material
  - Build site (mkdocs build --strict)
    ↓
Artifact Management
  - Upload site/ as artifact
    ↓
Deploy Job
  - Download artifact
  - Configure Pages
  - Deploy via actions/deploy-pages@v4
    ↓
GitHub Pages Live
```

### 2.2 Security & Permissions Model

**OIDC-Based Deployment** (Zero Long-Lived Secrets):
- `contents: read` - Read repository code
- `pages: write` - Write to GitHub Pages
- `id-token: write` - OIDC token generation (preferred over PAT)

**Concurrency Control**:
- Single deployment at a time
- Cancel in-progress on new push
- Prevents race conditions

### 2.3 Key Architectural Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Python 3.12 | Latest stable, better performance | ~5% faster builds |
| Pip caching | Dependency cache key on requirements | 60-80% faster builds on unchanged deps |
| `--strict` flag | Fail on warnings (links, formatting) | Catches documentation issues early |
| actions/deploy-pages@v4 | Modern approach (gh-pages deprecated) | Maintains GitHub's recommended path |
| Artifact upload | Decouple build/deploy jobs | Safer, allows job retry independently |
| Path filtering | Only trigger on docs/ changes | Reduces unnecessary builds by ~70% |

---

## 3. Implementation Plan

### 3.1 Phase 1: Workflow File Creation (30 min)

**File**: `.github/workflows/docs.yml`

**Structure**:
```yaml
name: Build and Deploy MkDocs
on:
  push:
    branches: [main]
    paths: [docs/, mkdocs.yml, .github/workflows/docs.yml]
  workflow_dispatch: ~

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
    runs-on: ubuntu-latest
    steps:
      # 1. Checkout
      # 2. Setup Python + cache
      # 3. Install dependencies
      # 4. Build with --strict
      # 5. Upload artifact

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      # 1. Download artifact
      # 2. Setup Pages
      # 3. Deploy
```

**Key Components**:
- **Triggers**: Push to main (with path filters) + manual dispatch
- **Environment variables**: Python version, build output path
- **Permissions**: Explicit permission grants for Pages deployment
- **Concurrency**: Named group for page deployments

### 3.2 Phase 2: Build Job Configuration (45 min)

**Job Name**: `build`

**Steps**:

1. **Checkout Code**
   ```yaml
   - uses: actions/checkout@v4
   ```
   - Standard repo checkout, no fetch depth needed

2. **Setup Python**
   ```yaml
   - uses: actions/setup-python@v4
     with:
       python-version: '3.12'
       cache: pip
       cache-dependency-path: requirements.txt
   ```
   - Caches pip packages (60-80% faster on cache hits)
   - Requires `requirements.txt` or `pyproject.toml`

3. **Install Dependencies**
   ```yaml
   - name: Install MkDocs dependencies
     run: |
       pip install --upgrade pip
       pip install mkdocs mkdocs-material pymdown-extensions
   ```
   - Material theme + extensions for navigation, code highlighting, etc.

4. **Build Documentation**
   ```yaml
   - name: Build MkDocs (strict mode)
     run: mkdocs build --strict
   ```
   - `--strict` fails on:
     - Broken links
     - Missing files
     - Invalid Markdown
   - Produces `site/` directory

5. **Upload Build Artifact**
   ```yaml
   - uses: actions/upload-artifact@v3
     with:
       name: github-pages
       path: site/
       retention-days: 1
   ```
   - Decouple build from deploy (retry safety)
   - 1-day retention (temporary staging)

### 3.3 Phase 3: Deploy Job Configuration (30 min)

**Job Name**: `deploy`

**Constraints**:
- `needs: build` - Only runs after successful build
- `environment: github-pages` - Creates GitHub Pages environment

**Steps**:

1. **Setup GitHub Pages**
   ```yaml
   - uses: actions/configure-pages@v4
   ```
   - Configures Pages for deployment
   - Sets up artifact staging

2. **Download Build Artifact**
   ```yaml
   - uses: actions/download-artifact@v3
     with:
       name: github-pages
   ```
   - Restores `site/` directory

3. **Deploy to Pages**
   ```yaml
   - uses: actions/deploy-pages@v4
     id: deployment
   ```
   - Modern deployment approach
   - Returns `page_url` output

### 3.4 Phase 4: Configuration & Optimization (30 min)

**Path Filtering** (Trigger Optimization):
```yaml
on:
  push:
    branches: [main]
    paths:
      - docs/**
      - mkdocs.yml
      - .github/workflows/docs.yml
```
- Only triggers on doc changes
- Skips workflow on code-only commits

**Concurrency Control**:
```yaml
concurrency:
  group: 'pages'
  cancel-in-progress: true
```
- Prevents simultaneous deployments
- Cancels older runs on new push

**Environment Configuration**:
```yaml
environment:
  name: github-pages
  url: ${{ steps.deployment.outputs.page_url }}
```
- Creates named environment (visible in Settings → Environments)
- Shows deployment URL in Actions UI

---

## 4. External Dependencies

| Dependency | Version | Purpose | Risk |
|-----------|---------|---------|------|
| `actions/checkout@v4` | v4 | Repository checkout | Low |
| `actions/setup-python@v4` | v4 | Python environment | Low |
| `actions/upload-artifact@v3` | v3 | Build artifact upload | Low |
| `actions/download-artifact@v3` | v3 | Artifact retrieval | Low |
| `actions/configure-pages@v4` | v4 | Pages configuration | Low |
| `actions/deploy-pages@v4` | v4 | Pages deployment | Low |
| `mkdocs` | ^1.5.0 | Documentation builder | Low |
| `mkdocs-material` | ^9.4.0 | Material theme | Low |
| `pymdown-extensions` | ^10.0 | Markdown extensions | Low |

**Version Strategy**:
- Pin major versions (`@v4`)
- Use `@v4` for stability
- Update quarterly via Dependabot

---

## 5. Security Considerations

### 5.1 Permission Model

**Principle**: Least privilege access

```yaml
permissions:
  contents: read       # Read source code
  pages: write         # Publish to Pages
  id-token: write      # OIDC token generation
```

**Why Not Using PAT?**
- ❌ Long-lived credentials
- ❌ Requires manual rotation
- ❌ Broad permissions

**Why OIDC?**
- ✅ Temporary tokens (job-scoped)
- ✅ Automatic rotation
- ✅ Fine-grained permissions

### 5.2 Artifact Security

- **Upload staging**: Uploaded to temporary GitHub storage
- **Retention**: Auto-deleted after 1 day
- **Access**: Only available to same workflow run

### 5.3 Protected Branch Integration

**Recommended Settings** (GitHub Settings → Branches):
```
Branch Name Pattern: main
  ✓ Require status checks before merging
    - workflow:Build and Deploy MkDocs / build
```

Ensures documentation builds cleanly before merges.

---

## 6. Performance Optimizations

### 6.1 Caching Strategy

**Pip Cache**:
- **Key**: `${{ hashFiles('**/requirements.txt') }}`
- **Hit Rate**: ~85% for unchanged dependencies
- **Time Saved**: 3-4 minutes per build

**Configuration**:
```yaml
- uses: actions/setup-python@v4
  with:
    cache: pip
    cache-dependency-path: requirements.txt
```

### 6.2 Path Filtering

**Benefit**: Avoids unnecessary builds
- **Code-only changes**: Workflow skipped
- **Doc changes**: Workflow runs
- **Estimated savings**: 60-70% fewer builds

### 6.3 Build Optimization

**MkDocs Build Time**: ~2-5 seconds (single-threaded)
**Deployment Time**: ~10-15 seconds
**Total**: ~15-20 seconds (cached dependencies)

---

## 7. Testing Strategy

### 7.1 Local Validation

**Before Merge**:
```bash
# Install dependencies
pip install mkdocs mkdocs-material pymdown-extensions

# Test build locally
mkdocs build --strict

# Verify site/ output
ls -la site/index.html
```

### 7.2 Workflow Syntax Validation

**GitHub Provides**:
- YAML syntax validation (automatic)
- Workflow validation on push
- Pre-flight checks in Actions tab

### 7.3 Deployment Verification

**Post-Deploy Checks**:
1. **Status Check**: Green checkmark in Actions UI
2. **URL Accessibility**: Click deployment URL
3. **Content Verification**: Search docs, verify navigation
4. **Performance**: Check page load time (<2s)

### 7.4 Failure Scenarios & Recovery

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| Build fails (syntax error) | `mkdocs build --strict` | Fix Markdown, push again |
| Missing dependency | pip install fails | Add to mkdocs.yml requirements |
| Broken link | `mkdocs build --strict` | Fix link in docs/ |
| Deploy permission denied | actions/deploy-pages fails | Check GitHub Pages settings |
| Artifact expiration | Download fails | Re-run build job |

---

## 8. Implementation Phases

### Phase A: Core Workflow (45 min)
- Create `.github/workflows/docs.yml`
- Implement build job (checkout, Python, install, build)
- Implement deploy job (configure, download, deploy)
- Add trigger configuration (push filters)

### Phase B: Optimization (30 min)
- Add pip caching
- Configure concurrency control
- Add path filtering
- Set environment configuration

### Phase C: Testing (30 min)
- Local validation (`mkdocs build --strict`)
- Push to feature branch
- Verify workflow runs
- Check deployed site
- Test rollback (force push old version)

### Phase D: Documentation (15 min)
- Add comments to workflow
- Update CONTRIBUTING.md with deployment flow
- Document environment variables

**Total Duration**: 2-3 hours

---

## 9. File Structure

### New Files

```
.github/
└── workflows/
    └── docs.yml (NEW - 120-150 lines)
```

### Modified Files

None (existing mkdocs.yml already configured)

### Dependencies

- **mkdocs.yml**: Already in place ✓
- **docs/ directory**: Already populated ✓
- **GitHub Pages**: Automatic (no setup needed)

---

## 10. Key Workflow Outputs

### 10.1 Build Job Outputs

- **Artifact**: `github-pages` (site/ directory)
- **Duration**: 15-20 seconds (with cache hits)
- **Size**: ~5-10 MB (site files)

### 10.2 Deploy Job Outputs

- **Deployment**: GitHub Pages live
- **URL**: https://taskwright-dev.github.io/taskwright/
- **Duration**: 10-15 seconds
- **Status**: ✅ deployment-status in PR

### 10.3 Monitoring & Alerts

**Available in Actions Tab**:
- Build/deploy job duration
- Artifact size
- Deployment URL
- Run history
- Failure logs

---

## 11. Configuration Checklist

Before implementation, verify:

- [ ] GitHub Pages enabled in repo settings
- [ ] Documentation in `docs/` directory
- [ ] `mkdocs.yml` configured correctly
- [ ] `site_url` points to correct GitHub Pages domain
- [ ] Branch protection rules ready (optional but recommended)
- [ ] Team members can view Actions tab

**Post-Implementation**:
- [ ] First workflow run succeeds
- [ ] Deployed site accessible at configured URL
- [ ] All internal links working
- [ ] Search functionality operational
- [ ] Code blocks rendering correctly
- [ ] Mobile responsive design verified

---

## 12. Rollback & Recovery Procedures

### Quick Rollback (if deployed docs are broken)

**Option 1: Force Previous Commit**
```bash
git revert HEAD
git push origin main
# Workflow re-runs, deploys previous version
```

**Option 2: Manual Pages Configuration**
- GitHub Settings → Pages → Choose a different branch
- Or temporarily disable Pages, re-enable

### Build Failure Recovery

1. **Check Actions tab** for error details
2. **Fix identified issue** (Markdown syntax, broken link, etc.)
3. **Commit and push** to trigger re-run
4. **Re-run job** manually from Actions UI if needed

---

## 13. Success Criteria

Workflow is successful when:

1. ✅ `.github/workflows/docs.yml` created with 120-150 lines
2. ✅ Workflow triggers on push to main (docs/ changes)
3. ✅ Build job completes in <20 seconds
4. ✅ `mkdocs build --strict` passes without warnings/errors
5. ✅ Artifact uploaded successfully
6. ✅ Deploy job completes in 10-15 seconds
7. ✅ Site deployed to GitHub Pages
8. ✅ Documentation accessible at configured URL
9. ✅ All navigation, search, and features working
10. ✅ Workflow can be manually triggered via workflow_dispatch
11. ✅ Concurrency control prevents simultaneous deployments
12. ✅ Permissions follow least-privilege principle

---

## 14. Related Tasks & Dependencies

**Dependencies**:
- ✅ TASK-DOCS-002: MkDocs installation & configuration (assumed complete)
- ✅ TASK-DOCS-003: Documentation structure & content (assumed complete)

**Related Work**:
- TASK-C5AC: MkDocs configuration (completed, generated mkdocs.yml)
- TASK-957C: Documentation organization plan
- Future: TASK-DOCS-005: Analytics integration (Google Analytics)
- Future: TASK-DOCS-006: Search optimization (Algolia)

---

## 15. Open Questions & Decisions

**Already Decided**:
- ✅ Modern deployment (actions/deploy-pages@v4)
- ✅ No gh-pages branch approach
- ✅ Pip caching enabled
- ✅ OIDC authentication
- ✅ Path filtering enabled

**Optional Enhancements** (out of scope):
- ?  Pre-deployment link checking (htmltest)
- ?  Analytics integration (GA4)
- ?  Versioned documentation (mike)
- ?  Search indexing (Algolia)

---

## 16. Next Steps

1. **Review this plan** - Approve/request changes
2. **Create workflow file** - Implement Phase A-D
3. **Test locally** - Run `mkdocs build --strict`
4. **Push feature branch** - Verify workflow runs
5. **Check deployed site** - Validate all features
6. **Merge to main** - Enable for all team members
7. **Monitor first 5 runs** - Catch any edge cases

---

## 17. Technical Specifications

### Python Version & Dependencies

```
Python: 3.12.x (latest stable)
mkdocs: ^1.5.0
mkdocs-material: ^9.4.0
pymdown-extensions: ^10.0
```

### Build Environment

- **Runner**: ubuntu-latest (current: Ubuntu 24.04)
- **Python**: 3.12 (installed via setup-python@v4)
- **Package Manager**: pip
- **Build Tool**: mkdocs CLI

### GitHub Pages Configuration

- **Source**: Deploy from Actions (modern approach)
- **Branch**: Automatic (Actions handles)
- **Domain**: taskwright-dev.github.io/taskwright/ (from mkdocs.yml site_url)

---

## Implementation Notes

**Code Quality Standards**:
- YAML properly formatted (2-space indentation)
- Comments explain non-obvious decisions
- Actions versions pinned to major version
- No hardcoded paths or credentials

**Documentation Standards**:
- Each step has descriptive name
- Environment variables clearly documented
- Error handling explicit
- Recovery procedures documented

**Performance Standards**:
- Cached builds: 15-20 seconds
- Non-cached builds: 30-40 seconds
- Deployment: 10-15 seconds
- Total time (first-time): <60 seconds

**Security Standards**:
- OIDC tokens (no PATs)
- Minimal permissions granted
- No secrets in workflow
- Artifact cleanup after 1 day

---

**Plan Status**: READY FOR IMPLEMENTATION
**Created**: 2025-11-27
**By**: DevOps Specialist Agent
