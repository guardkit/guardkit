# git-workflow-manager - Extended Reference

This file contains detailed documentation for the `git-workflow-manager` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/git-workflow-manager-ext.md
```


## Quality Gates
- [x] Tests pass (100% required)
- [x] Coverage ≥80% lines, ≥75% branches
- [x] Code reviewed (Phase 5 complete)
- [x] Documentation updated
- [x] No breaking changes

### Example 2: Bug Fix Workflow (Good)

```bash

# Create fix branch
git checkout -b fix/TASK-043-null-pointer-user-lookup

# Fix the bug
git add src/services/UserService.ts
git commit -m "fix(api): prevent null pointer in user lookup

Add defensive null check before accessing user properties.
Prevents crash when user not found in database.

Fixes line 67 in UserService.ts
Related: TASK-043"

# Add test to prevent regression
git add tests/services/UserService.test.ts
git commit -m "test(api): add null user handling test

Ensure graceful handling of null user scenarios.

Related: TASK-043"

# Verify tests pass
pytest tests/services/UserService.test.ts -v  # ✅ Pass

# Create PR
git push origin fix/TASK-043-null-pointer-user-lookup
gh pr create --title "fix(api): Prevent null pointer in user lookup" \
  --body "Fixes #43. Added defensive null check at UserService:67"
```

---

### Example 3: Breaking Change Workflow (Good)

```bash

# Create feature branch
git checkout -b feature/TASK-050-api-v2-migration

# Implement breaking change
git add src/routes/users.ts
git commit -m "feat(api)!: remove deprecated /v1/users endpoint

BREAKING CHANGE: /v1/users endpoint removed.
Migrate to /v2/users with pagination support.

Migration guide: docs/api-migration-v2.md
Related: TASK-050"

# Add migration documentation
git add docs/api-migration-v2.md
git commit -m "docs(api): add v1 to v2 migration guide

Related: TASK-050"

# Create PR with breaking change notice
gh pr create --title "feat(api)!: Remove deprecated /v1/users endpoint" \
  --body "⚠️ BREAKING CHANGE: Requires API migration. See docs/api-migration-v2.md"
```

**Why This Works**:
- `!` suffix indicates breaking change
- `BREAKING CHANGE:` in commit body provides details
- Migration guide included
- PR title clearly marked with `!`

---

### Example 4: Hotfix Workflow (Good)

```bash

# Create hotfix from main (production urgent)
git checkout main
git pull
git checkout -b hotfix/security-vulnerability-CVE-2024-1234

# Fix critical issue
git add src/services/AuthService.ts
git commit -m "fix(security): patch JWT secret key vulnerability

Critical security fix for CVE-2024-1234.
Implements proper secret key rotation.

Security advisory: SEC-2024-001
Related: HOTFIX-001"

# Expedited testing (streamlined for urgency)
npm test  # ✅ Security tests pass

# Create PR with expedited review
git push origin hotfix/security-vulnerability-CVE-2024-1234
gh pr create --title "HOTFIX: Patch JWT secret key vulnerability (CVE-2024-1234)" \
  --label "security,hotfix" \
  --body "🚨 SECURITY: Critical vulnerability fix. Requires immediate review."

# After merge, tag immediately
git checkout main
git pull
git tag -a v1.2.1 -m "Security hotfix: CVE-2024-1234"
git push origin v1.2.1
```

---

### Example 5: Vague Commit Messages (Bad)

```bash

# ❌ DON'T: Vague, unhelpful commits
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "wip"
git commit -m "changed file"
git commit -m "bug fix"

# ✅ DO: Descriptive, contextual commits
git commit -m "fix(api): prevent null pointer in user lookup (line 67)"
git commit -m "feat(auth): add JWT token generation with 24h expiry"
git commit -m "test(auth): add token expiry validation tests"
git commit -m "refactor(api): extract user validation to separate service"
git commit -m "docs(api): update authentication endpoint documentation"
```

---

### Example 6: Poor Branch Naming (Bad)

```bash

# ❌ DON'T: Vague or personal branch names
git checkout -b fix-stuff
git checkout -b new-feature
git checkout -b johns-branch
git checkout -b temp
git checkout -b test123

# ✅ DO: Descriptive branch names with task IDs
git checkout -b feature/TASK-042-jwt-authentication
git checkout -b fix/TASK-043-null-pointer-user-lookup
git checkout -b hotfix/security-vulnerability-CVE-2024-1234
git checkout -b release/v1.2.0
git checkout -b docs/api-documentation-update
```

---

### Example 7: PR Created Too Early (Bad)

```bash

# ❌ DON'T: Create PR before tests pass
git push origin feature/TASK-042-jwt-auth
npm test  # ❌ 3 tests failing
gh pr create --title "WIP: JWT auth"  # ❌ WRONG

# ✅ DO: Fix tests first, then create PR
npm test  # ❌ 3 tests failing

# [fix failing tests]
npm test  # ✅ 15/15 passing
npm run coverage  # ✅ 92% coverage
gh pr create --title "feat(auth): Add JWT token generation"  # ✅ CORRECT
```

**Why This Fails**:
- PR created before Phase 4 (testing) complete
- Failing tests in PR indicate incomplete work
- "WIP" in title suggests work not ready for review

---

### Example 8: Force Push to Main (Bad)

```bash

# ❌ NEVER: Force push to protected branch
git checkout main
git push --force  # ❌ DESTROYS TEAM'S WORK

# ✅ DO: Only force push to feature branches (with caution)
git checkout feature/TASK-042-jwt-auth

# Rebase to incorporate main changes
git rebase main
git push --force-with-lease  # ✅ Safer force push (checks remote hasn't changed)
```

**Why This Fails**:
- Force pushing to main overwrites other developers' commits
- Causes data loss and merge conflicts
- Violates protected branch policies

---

### Example 9: Squash Large Feature Branch (Bad)

```bash

# ❌ DON'T: Squash 50+ commits from multi-day feature
git checkout feature/TASK-042-complete-auth-system
git log --oneline  # Shows 50 commits over 2 weeks
gh pr merge --squash  # ❌ Loses valuable commit history

# ✅ DO: Merge to preserve commit context
gh pr merge --merge  # ✅ Preserves all 50 commits with context
```

**Why This Fails**:
- Squashing large features loses granular history
- Hard to track when specific changes were introduced
- Merge commits provide better context for large features

---

### Example 10: Merge Strategy Selection (Good)

```bash

# Strategy 1: Merge (preserve history)

# Use for: Feature branches with meaningful commit history
git checkout main
git merge --no-ff feature/TASK-042-complete-auth-system

# Result: Merge commit + all feature commits visible in history

# Strategy 2: Squash (simplify history)

# Use for: Bug fixes, typo fixes, small PRs with cleanup commits
gh pr merge --squash

# Result: Single commit "fix(api): Prevent null pointer in user lookup (#43)"

# Strategy 3: Rebase (linear history)

# Use for: Keeping feature branch up-to-date with main
git checkout feature/TASK-042-jwt-auth
git rebase main  # Reapply feature commits on top of latest main
git push --force-with-lease  # Update remote (only on feature branch!)
```

---

### Example 11: Semantic Versioning Tags (Good)

```bash

# After PR merged to main
git checkout main
git pull

# Create annotated tag with release notes
git tag -a v1.2.0 -m "Release v1.2.0

## Features
- JWT token authentication (TASK-042)
- User profile endpoints (TASK-043)
- Email verification (TASK-044)

## Fixes
- Null pointer in user lookup (TASK-045)
- Token expiry handling (TASK-046)

## Breaking Changes
None
"

# Push tag to remote
git push origin v1.2.0

# Create GitHub release
gh release create v1.2.0 \
  --notes "$(git tag -l --format='%(contents)' v1.2.0)" \
  --title "Release v1.2.0"
```

**Version Bumps**:
- **MAJOR** (v1.0.0 → v2.0.0): Breaking changes (API changes, removals)
- **MINOR** (v1.2.0 → v1.3.0): New features, backwards compatible
- **PATCH** (v1.2.3 → v1.2.4): Bug fixes, backwards compatible

---

### Example 12: PR Template Usage (Good)

```markdown

## Summary
Implements JWT-based authentication with secure token generation,
validation middleware, and refresh token support.

## Changes
- JWT token generation with configurable expiry (default 24h)
- Token validation middleware for protected routes
- Refresh token endpoint for seamless re-authentication
- Secure secret key management via environment variables

## Test Coverage
- 15/15 tests passing ✅
- 92% line coverage (target: ≥80%) ✅
- 88% branch coverage (target: ≥75%) ✅
- Security: No hardcoded secrets ✅

## Quality Gates
- [x] Build verification passed (Phase 4)
- [x] Tests pass (100% required, Phase 4.5)
- [x] Coverage ≥80% lines, ≥75% branches
- [x] Code reviewed (Phase 5 complete)
- [x] Documentation updated
- [x] No breaking changes

### Example 13: Release Workflow (Good)

```bash

# Step 1: Merge all PRs for release → main
gh pr merge 42 --merge  # Feature: JWT auth
gh pr merge 43 --squash  # Fix: Null pointer

# Step 2: Verify CI/CD pipeline passes

# [Wait for GitHub Actions to complete]

# Step 3: Pull latest main
git checkout main
git pull

# Step 4: Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0 - Authentication improvements"

# Step 5: Push tag
git push origin v1.2.0

# Step 6: Create GitHub release
gh release create v1.2.0 \
  --title "v1.2.0 - Authentication Improvements" \
  --notes "See CHANGELOG.md for details"

# Step 7: Deploy to production (if applicable)

# [Trigger deployment pipeline]
```

---

### Example 14: Rebase Feature Branch (Good)

```bash

# Feature branch is behind main
git checkout feature/TASK-042-jwt-auth
git log main..HEAD  # Shows 5 commits on feature branch

# Option 1: Rebase (linear history, recommended)
git rebase main  # Reapply 5 commits on top of latest main

# [Resolve conflicts if any]
git push --force-with-lease  # Update remote

# Option 2: Merge main into feature (preserves merge commit)
git merge main  # Creates merge commit
git push  # No force push needed
```

**When to Rebase**:
- Feature branch is short-lived (< 1 week)
- No other developers working on branch
- Want clean linear history

**When to Merge**:
- Long-running feature branch
- Multiple developers on branch
- Want to preserve branch point history

---

### Example 15: Multi-Commit Feature (Good)

```bash

# Feature with logical commit progression
git checkout -b feature/TASK-042-jwt-auth

# Commit 1: Core functionality
git add src/services/AuthService.ts
git commit -m "feat(auth): add JWT token generation service"

# Commit 2: Middleware
git add src/middleware/authMiddleware.ts
git commit -m "feat(auth): add token validation middleware"

# Commit 3: Refresh endpoint
git add src/routes/auth.ts
git commit -m "feat(auth): add refresh token endpoint"

# Commit 4: Tests
git add tests/services/AuthService.test.ts tests/middleware/authMiddleware.test.ts
git commit -m "test(auth): add comprehensive token tests

Coverage: 15/15 passing, 92% line coverage"

# Commit 5: Documentation
git add docs/api/authentication.md
git commit -m "docs(auth): document JWT authentication endpoints"

# Create PR preserving all 5 logical commits
gh pr create --title "feat(auth): Add JWT token generation"
gh pr merge --merge  # Preserve commit history
```

---

### Example 16: Hotfix Branch Naming (Good)

```bash

# ✅ DO: Descriptive hotfix names with severity indicators
git checkout -b hotfix/security-vulnerability-CVE-2024-1234
git checkout -b hotfix/payment-processing-down
git checkout -b hotfix/database-connection-leak

# ❌ DON'T: Vague hotfix names
git checkout -b hotfix
git checkout -b urgent-fix
git checkout -b production-issue
```

---

### Example 17: Commit Message with Task Integration (Good)

```bash

# ✅ DO: Include task ID for traceability
git commit -m "feat(auth): add JWT token generation

Implements JWT-based authentication with:
- 24-hour token expiry
- Refresh token support
- Secure secret key management

Tests: 15/15 passing, 92% coverage
Related: TASK-042
Closes #123"

# ❌ DON'T: Omit task ID
git commit -m "add JWT auth"
```

**Traceability Benefits**:
- Link commits to task requirements
- Track implementation progress
- Enable git log filtering by task ID: `git log --grep="TASK-042"`

---

### Example 18: PR Checklist Validation (Good)

```markdown


## Quality Gates
- [x] Build verification passed
- [x] Tests pass (15/15, 100% required)
- [x] Coverage ≥80% lines (92% actual) ✅
- [x] Coverage ≥75% branches (88% actual) ✅
- [x] Code reviewed (Phase 5)
- [x] No breaking changes
- [ ] Migration guide (N/A)
- [x] Documentation updated


## Cross-References
- Tests executed by: test-orchestrator (Phase 4)
- Code reviewed by: code-reviewer (Phase 5)
- Quality gates enforced by: task-manager (Phase 4.5)
```

**Why This Works**:
- All quality gates explicitly checked
- Actual coverage metrics provided
- Cross-references to related agents
- Clear indication of N/A items

---

### Example 19: Force Push Safety (Good)

```bash

# ❌ UNSAFE: Force push without checking remote
git push --force origin feature/TASK-042-jwt-auth

# Risk: Overwrites someone else's commits if they pushed meanwhile

# ✅ SAFE: Force push with lease (checks remote hasn't changed)
git push --force-with-lease origin feature/TASK-042-jwt-auth

# Fails if remote has new commits you don't have locally

# ✅ SAFEST: Communicate before force push

# 1. Check with team: "Anyone working on feature/TASK-042-jwt-auth?"

# 2. Wait for confirmation

# 3. Force push with lease
git push --force-with-lease origin feature/TASK-042-jwt-auth
```

---

### Example 20: Tag Before vs After Testing (Bad vs Good)

```bash

# ❌ DON'T: Tag before CI passes
git checkout main
git pull
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# [CI fails 5 minutes later] ❌

# ✅ DO: Wait for CI, then tag
git checkout main
git pull

# [Wait for GitHub Actions to pass] ✅
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
gh release create v1.2.0
```

---

## Boundaries

### ALWAYS (Non-Negotiable)

- ✅ Use Conventional Commits format for all commits (enforces semantic versioning and auto-changelog generation)
- ✅ Follow branch naming conventions: feature/fix/hotfix/release/docs (enables automatic branch protection and CI/CD routing)
- ✅ Create PR after Phase 4 complete (tests pass 100%, coverage ≥80%) (ensures quality gates met before review)
- ✅ Include task ID in branch name and commits (enables traceability and automated task updates)
- ✅ Validate PR checklist before merge (confirms all quality gates passed)
- ✅ Use annotated tags for releases (preserves release metadata and enables automated release notes)
- ✅ Cross-reference test-orchestrator for test requirements (delegates test execution, avoids duplication)

### NEVER (Will Be Rejected)

- ❌ Never use vague commit messages ("fixed stuff", "updates", "wip" in final commits) (breaks semantic versioning and changelog automation)
- ❌ Never create PR before tests pass (100% pass rate required per Phase 4.5) (violates quality gates, blocks merge)
- ❌ Never commit directly to main (all changes via PR for review) (bypasses code review and CI/CD)
- ❌ Never force push to main or protected branches (destroys team's work, causes data loss)
- ❌ Never squash multi-feature PRs (>20 commits from multi-day work) (loses valuable commit history and context)
- ❌ Never omit task ID from branch/commit (breaks traceability and automated task updates)
- ❌ Never tag before CI/CD passes (creates invalid release tags that must be deleted)

### ASK (Escalate to Human)

- ⚠️ Breaking changes detected: Require migration guide and major version bump (MAJOR: v1.x.x → v2.0.0)
- ⚠️ Force push to shared feature branch: Confirm no other developers working on branch (prevents overwriting their work)
- ⚠️ Hotfix to production: Expedited review process, which quality gates can be streamlined? (balance speed vs safety)
- ⚠️ Large PR (>20 files or >500 LOC): Consider splitting into smaller PRs for easier review?
- ⚠️ Merge strategy unclear: Merge vs squash vs rebase decision needed based on commit history quality

---

## How It Works

### Branch Naming Conventions

**Pattern**: `{type}/{task-id}-{description}` or `{type}/{description}`

**Types**:
- **feature**: New features or enhancements
- **fix**: Bug fixes (non-urgent)
- **hotfix**: Production-critical urgent fixes
- **release**: Release preparation branches
- **docs**: Documentation-only changes
- **refactor**: Code refactoring without behavior changes
- **test**: Test-only additions or fixes

**Examples**:
```bash
feature/TASK-042-jwt-authentication
fix/TASK-043-null-pointer-user-lookup
hotfix/security-vulnerability-CVE-2024-1234
release/v1.2.0
docs/api-documentation-update
refactor/extract-validation-service
test/add-integration-tests
```

**Validation Regex**:
```bash
^(feature|fix|hotfix|release|docs|refactor|test)/[a-z0-9-]+$
```

---

### Conventional Commits Standard

**Format**: `{type}({scope}): {description}`

**Types**:
- **feat**: New feature (triggers MINOR version bump)
- **fix**: Bug fix (triggers PATCH version bump)
- **docs**: Documentation changes (no version bump)
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no behavior change)
- **test**: Test additions or fixes
- **chore**: Build process, tooling, dependencies

**Scope** (optional): Component or module affected (auth, api, ui, database)

**Description**: Imperative mood, lowercase, no period

**Breaking Changes**: Add `!` after type or `BREAKING CHANGE:` in body (triggers MAJOR version bump)

**Examples**:
```bash
feat(auth): add JWT token generation
fix(api): prevent null pointer in user lookup
docs(readme): update installation instructions
style(components): reformat with prettier
refactor(services): extract validation logic
test(auth): add token expiry tests
chore(deps): update react to v18.2.0
feat(api)!: remove deprecated /v1/users endpoint
```

**Commit Body** (optional):
```
feat(auth): add JWT token generation

Implements JWT-based authentication with:
- Token generation with 24-hour expiry
- Refresh token support
- Secure secret key management

Tests: 15/15 passing, 92% coverage
Related: TASK-042
```

---

### Pull Request Workflow

**When to Create PR**: After Phase 4 (Testing) and Phase 4.5 (Test Enforcement) complete

**Phase Integration**:

| Phase | Phase Name | Git Actions | PR Status |
|-------|-----------|-------------|-----------|
| **2** | Planning | Create feature branch | No PR yet |
| **3** | Implementation | Commit frequently with Conventional Commits | No PR yet |
| **4** | Testing | Add test commits, verify tests pass | No PR yet |
| **4.5** | Test Enforcement | Verify 100% pass rate, ≥80% coverage | ✅ **NOW: Create PR** |
| **5** | Code Review | PR under review | PR open |
| **5.5** | Plan Audit | Verify implementation matches plan | PR approved |
| **6** | Merge | Merge to main, delete branch | PR merged |

**PR Creation Command**:
```bash
gh pr create \
  --title "{type}({scope}): {description}" \
  --body "$(cat <<'PREOF'


## Quality Gates
- [x] Build verification passed (Phase 4)
- [x] Tests pass (100% required, Phase 4.5)
- [x] Coverage ≥80% lines, ≥75% branches
- [x] Code reviewed (Phase 5)
- [x] Plan audit passed (Phase 5.5)
- [x] No breaking changes (or migration guide provided)


## Cross-References
- Tests executed by: test-orchestrator (Phase 4)
- Code reviewed by: code-reviewer (Phase 5)
- Plan audit by: task-manager (Phase 5.5)

### Merge Strategies

| Strategy | When to Use | Command | Result |
|----------|-------------|---------|--------|
| **Merge** | Feature branches with meaningful commit history (5+ commits) | `gh pr merge --merge` | All commits preserved + merge commit |
| **Squash** | Bug fixes, small features, cleanup commits (<5 commits) | `gh pr merge --squash` | Single commit in main |
| **Rebase** | Update feature branch with latest main (not for merging to main) | `git rebase main` | Linear history, no merge commit |

**Decision Tree**:
```
Is this a multi-day feature with >10 commits?
├─ YES → Merge (preserve history)
└─ NO → Is commit history clean and logical?
    ├─ YES → Merge (preserve commits)
    └─ NO → Squash (simplify history)
```

**Merge Example**:
```bash

# Preserve all commits from feature branch
git checkout main
git merge --no-ff feature/TASK-042-complete-auth-system
git push origin main
```

**Squash Example**:
```bash

# Combine all commits into one
gh pr merge 42 --squash --subject "feat(auth): Add JWT token generation"
```

**Rebase Example** (update feature branch, not merge to main):
```bash

# Update feature branch with latest main
git checkout feature/TASK-042-jwt-auth
git rebase main
git push --force-with-lease
```

---

### Tag and Release Management

**Semantic Versioning Format**: `vMAJOR.MINOR.PATCH`

**Version Bumps**:
- **MAJOR** (v1.0.0 → v2.0.0): Breaking changes (API changes, removals)
  - Triggered by: `feat!:` or `BREAKING CHANGE:` in commit
- **MINOR** (v1.2.0 → v1.3.0): New features, backwards compatible
  - Triggered by: `feat:` commits
- **PATCH** (v1.2.3 → v1.2.4): Bug fixes, backwards compatible
  - Triggered by: `fix:` commits

**Tag Creation Workflow**:
```bash

# Step 1: Ensure all PRs merged to main
git checkout main
git pull

# Step 2: Verify CI/CD passes

# [Wait for GitHub Actions green checkmark]

# Step 3: Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0

## Features
- JWT token authentication (TASK-042)
- User profile endpoints (TASK-043)

## Fixes
- Null pointer in user lookup (TASK-044)

## Breaking Changes
None
"

# Step 4: Push tag
git push origin v1.2.0

# Step 5: Create GitHub release
gh release create v1.2.0 \
  --title "v1.2.0 - Authentication Improvements" \
  --notes "$(git tag -l --format='%(contents)' v1.2.0)"
```

**Tag Types**:
- **Annotated tags** (recommended): `git tag -a v1.2.0 -m "message"` (includes tagger, date, message)
- **Lightweight tags** (discouraged): `git tag v1.2.0` (just a reference, no metadata)

**Pre-release Tags**:
```bash
git tag -a v1.3.0-beta.1 -m "Beta release for testing"
git tag -a v1.3.0-rc.1 -m "Release candidate 1"
```

---

### Integration with Task Workflow Phases

This agent integrates with task-manager workflow phases to enforce Git best practices at each stage:

| Phase | Phase Name | Git Actions | Quality Gates |
|-------|-----------|-------------|---------------|
| **2** | Planning | Create feature branch: `feature/TASK-XXX-{description}` | Branch naming validated |
| **3** | Implementation | Commit frequently with Conventional Commits | Commit format validated |
| **4** | Testing | Add test commits, verify tests pass | Tests must pass (delegated to test-orchestrator) |
| **4.5** | Test Enforcement | Verify 100% pass rate, ≥80% coverage | Coverage thresholds enforced |
| **5** | Code Review | Create PR with template, link task ID | PR checklist validated |
| **5.5** | Plan Audit | Verify implementation matches plan | Scope creep detection |
| **6** | Merge | Merge PR to main, delete feature branch | Merge strategy validated |

**Phase 2 (Planning)**: Branch Creation
```bash

# task-manager invokes git-workflow-manager
git checkout -b feature/TASK-042-jwt-authentication
```

**Phase 3 (Implementation)**: Conventional Commits
```bash
git commit -m "feat(auth): add JWT token generation

Related: TASK-042"
```

**Phase 4 (Testing)**: Test Commits
```bash
git commit -m "test(auth): add token expiry tests

Coverage: 15/15 passing, 92% line coverage
Related: TASK-042"
```

**Phase 4.5 (Test Enforcement)**: Quality Gate Check (Cross-Reference: test-orchestrator)
```bash

# test-orchestrator verifies:

# - Build passes (100%)

# - Tests pass (100%)

# - Coverage ≥80% lines, ≥75% branches
```

**Phase 5 (Code Review)**: PR Creation
```bash

# NOW: Create PR (after test-orchestrator confirms quality gates)
gh pr create --title "feat(auth): Add JWT token generation"
```

**Phase 5.5 (Plan Audit)**: Implementation Verification
```bash

# task-manager verifies:

# - All planned files created

# - No scope creep (only planned changes)
```

**Phase 6 (Merge)**: Merge and Cleanup
```bash
gh pr merge --merge  # Or --squash based on commit history
git branch -d feature/TASK-042-jwt-authentication
```

---


## CI/CD Integration

Integrate git-workflow-manager with CI/CD pipelines for automated quality gates and release workflows.

### GitHub Actions Workflow Integration

Based on `.github/workflows/ci.yml` template, git-workflow-manager enforces quality gates before merge:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run ESLint
        run: npm run lint

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run TypeScript type check
        run: npm run type-check

  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run unit tests
        run: npm test -- --coverage
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, type-check, test]
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Build project
        run: npm run build
      - name: Check build output
        run: |
          if [ ! -d ".next" ]; then
            echo "Build failed: .next directory not found"
            exit 1
          fi
```

### Pre-Merge Quality Gates

Git workflow manager enforces these checks before allowing PR merge:

#### Phase 4.5: Quality Gate Validation

```bash

# Run before creating PR (automated in CI)
npm run lint          # ✅ Code style compliance
npm run type-check    # ✅ TypeScript type safety
npm test -- --coverage # ✅ Test coverage ≥80% lines, ≥75% branches
npm run build         # ✅ Production build succeeds
```

#### PR Checklist Enforcement

```markdown

## Quality Gates (CI-Verified)
- [x] Lint: ESLint passes (0 errors, 0 warnings)
- [x] Type Check: TypeScript compilation succeeds
- [x] Tests: 100% pass rate (15/15 passing)
- [x] Coverage: ≥80% lines, ≥75% branches (current: 92%)
- [x] Build: Production build succeeds
- [x] Code Review: Approved by reviewer (Phase 5)
```

### Automated Version Bumping

Use semantic commit messages to trigger automated version bumping:

```bash

# Commit types trigger version bumps
feat:     # Minor version bump (1.2.0 -> 1.3.0)
fix:      # Patch version bump (1.2.0 -> 1.2.1)
feat!:    # Major version bump (1.2.0 -> 2.0.0)
BREAKING CHANGE: # Major version bump (1.2.0 -> 2.0.0)
```

#### GitHub Actions Release Workflow

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, 'chore(release)')"
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Determine version bump
        id: semver
        run: |
          COMMIT_MSG="${{ github.event.head_commit.message }}"
          if [[ "$COMMIT_MSG" =~ "BREAKING CHANGE" ]] || [[ "$COMMIT_MSG" =~ "feat!" ]]; then
            echo "bump=major" >> $GITHUB_OUTPUT
          elif [[ "$COMMIT_MSG" =~ "feat" ]]; then
            echo "bump=minor" >> $GITHUB_OUTPUT
          elif [[ "$COMMIT_MSG" =~ "fix" ]]; then
            echo "bump=patch" >> $GITHUB_OUTPUT
          else
            echo "bump=none" >> $GITHUB_OUTPUT
          fi

      - name: Bump version
        if: steps.semver.outputs.bump != 'none'
        run: npm version ${{ steps.semver.outputs.bump }} -m "chore(release): %s"

      - name: Push tag
        if: steps.semver.outputs.bump != 'none'
        run: |
          git push origin main --tags
```

### Release Automation Workflow

Combine git-workflow-manager with CI/CD for automated releases:

```bash

# 1. Merge feature PR to main (triggers CI)
gh pr merge <PR-number> --squash --delete-branch

# 2. CI runs quality gates on main branch

# - Lint, type-check, test, build all pass ✅

# 3. Automated version bump based on commit type

# feat: 1.2.0 -> 1.3.0

# fix: 1.2.0 -> 1.2.1

# feat!: 1.2.0 -> 2.0.0

# 4. Create GitHub release with changelog
git tag -a v1.3.0 -m "Release v1.3.0"
git push origin v1.3.0

# 5. Deploy to production (environment-specific)

# - Staging: Auto-deploy on version tags

# - Production: Manual approval required
```

### Branch Protection Rules

Configure repository settings to enforce git-workflow-manager rules:

```yaml

# .github/settings.yml (via Probot Settings)
branches:
  - name: main
    protection:
      required_status_checks:
        strict: true
        contexts:
          - "Lint"
          - "Type Check"
          - "Unit Tests"
          - "Build"
      required_pull_request_reviews:
        required_approving_review_count: 1
        dismiss_stale_reviews: true
        require_code_owner_reviews: true
      enforce_admins: true
      required_linear_history: false
      restrictions: null

  - name: develop
    protection:
      required_status_checks:
        strict: true
        contexts:
          - "Lint"
          - "Type Check"
          - "Unit Tests"
```

### DO/DON'T: CI/CD Integration

#### ✅ DO: Wait for CI Before Merge

```bash

# Good: Verify all checks pass
gh pr create --title "feat(auth): Add JWT authentication"

# Wait for CI: Lint ✅, Type Check ✅, Tests ✅, Build ✅
gh pr merge <PR-number> --squash --delete-branch
```

#### ❌ DON'T: Bypass CI Checks

```bash

# Bad: Force-merge without waiting for CI
git push --force origin feature/my-branch
gh pr merge <PR-number> --admin --delete-branch  # ❌ Bypasses required checks
```

#### ✅ DO: Use Semantic Commits for Automation

```bash

# Good: Commit type triggers correct version bump
git commit -m "feat(api): add user profile endpoint"  # -> 1.2.0 -> 1.3.0
git commit -m "fix(auth): resolve token expiry bug"   # -> 1.2.0 -> 1.2.1
git commit -m "feat(api)!: change authentication API" # -> 1.2.0 -> 2.0.0
```

#### ❌ DON'T: Ignore Commit Conventions

```bash

# Bad: Non-semantic commits break automation
git commit -m "updated code"        # ❌ No version bump triggered
git commit -m "fixed bug"           # ❌ No scope, automation fails
git commit -m "breaking changes"    # ❌ Not recognized as breaking change
```

### Integration with Test Orchestrator

Git workflow manager coordinates with test-orchestrator for Phase 4 validation:

```bash

# Phase 4: Test Execution (before PR creation)
/agent test-orchestrator

# test-orchestrator runs:
npm run lint              # ✅ Lint checks
npm run type-check        # ✅ Type safety
npm test -- --coverage    # ✅ Unit tests with coverage
npm run test:e2e          # ✅ E2E tests

# Results feed into git-workflow-manager PR checklist

# git-workflow-manager creates PR ONLY if all tests pass
```

### Continuous Deployment Pipeline

```yaml

# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          echo "Deploying ${{ github.ref_name }} to staging"
          # Deployment steps

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          echo "Deploying ${{ github.ref_name }} to production"
          # Deployment steps
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat git-workflow-manager-ext.md
```

Or in Claude Code:
```
Please read git-workflow-manager-ext.md for detailed examples.
```
