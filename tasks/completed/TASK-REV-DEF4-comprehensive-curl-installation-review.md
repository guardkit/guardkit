---
id: TASK-REV-DEF4
title: Comprehensive review of curl installation fixes before public launch
status: review_complete
created: 2025-11-29T19:00:00Z
updated: 2025-11-29T19:35:00Z
priority: critical
tags: [review, installation, pre-launch, regression-risk, curl, python-imports]
task_type: review
decision_required: true
complexity: 8
related_tasks:
  - TASK-FIX-A7B3  # Taskwright Python import path fix
  - TASK-FIX-C2D8  # RequireKit Python import path fix
review_results:
  mode: architectural
  depth: comprehensive
  score: 30
  findings_count: 6
  recommendations_count: 6
  decision: no-go-launch
  report_path: .claude/reviews/TASK-REV-DEF4-review-report.md
  completed_at: 2025-11-29T19:35:00Z
  launch_recommendation: NO-GO
  confidence_level: 95%
  estimated_fix_time: 4-6 hours
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Comprehensive review of curl installation fixes before public launch

## Context

We are approaching **public launch** and have discovered critical installation issues in both Taskwright and RequireKit when installed via curl (not from local git clone). Multiple fixes have been implemented in rapid succession on the macOS Parallels VM, and we need to ensure these fixes are correct, complete, and won't cause regressions.

**Urgency**: HIGH - Public launch is imminent
**Risk Level**: CRITICAL - Broken installation will damage user trust and adoption

## Problem Discovery Timeline

### Issue 1: `taskwright init` Command Not Found (RESOLVED)
**Problem**: After curl installation, users couldn't run `taskwright init` in their shell.

**Root Cause**: The curl install didn't download the repository, so the init command had no code to execute.

**Fix Applied**: Modified install script to:
- Download the repository to a permanent location
- Save repository location in marker file (`repo_path` field)
- Enable commands to reference repository code

**Status**: ✅ Fixed (verified on macOS Parallels VM)

### Issue 2: Python Import Path Failures (CURRENT)
**Problem**: After curl installation, `/task-create` command fails in Claude Code with Python import errors.

**Root Cause**: Documentation and code use `from installer.core.lib.X` imports, but:
- `global` is a Python reserved keyword (causes syntax errors)
- The `installer/` directory doesn't exist in `~/.agentecflow/` after installation
- Python doesn't know to look in the repository path from marker file

**Fix Tasks Created**:
- **TASK-FIX-A7B3**: Fix Taskwright Python import paths
- **TASK-FIX-C2D8**: Fix RequireKit Python import paths (lower priority, fewer Python dependencies)

**Status**: ⚠️ Tasks created but not yet implemented

### Issue 3: Potential Undiscovered Issues
**Concern**: Rapid fixes on VM may have introduced other issues or missed edge cases.

## Review Objectives

### 1. Validate Python Import Path Solution

**Questions to Answer**:
- [ ] What is the correct import path pattern for curl-installed files?
- [ ] Should we use relative imports (`from lib.X`) or absolute paths?
- [ ] Do we need Python path bootstrap code in every command?
- [ ] Will the chosen solution work across all platforms (macOS, Linux, Windows)?
- [ ] Are there any other Python import locations beyond `id_generator.py`?

**Analysis Required**:
- Audit all Python imports in both Taskwright and RequireKit
- Verify `installer.core.lib` vs `lib` vs path manipulation approaches
- Test proposed solution on fresh curl installation
- Ensure solution works from both Claude Code and shell

### 2. Installation Script Integrity

**Questions to Answer**:
- [ ] Are all necessary Python files copied during installation?
- [ ] Is the `repo_path` correctly set and used?
- [ ] Are symlinks created correctly and reliably?
- [ ] Does the installation handle upgrades/reinstalls correctly?
- [ ] Are there any platform-specific issues (Parallels VM vs native macOS)?

**Analysis Required**:
- Review `installer/scripts/install.sh` for both projects
- Verify file copying logic matches runtime expectations
- Test installation scenarios: fresh, upgrade, reinstall
- Check for race conditions or temporary file issues

### 3. Marker File Design

**Questions to Answer**:
- [ ] Is the marker file format stable and forward-compatible?
- [ ] Is `repo_path` the right approach for curl installations?
- [ ] Should marker file include Python path configuration?
- [ ] Are there security implications of storing repo paths?

**Analysis Required**:
- Review marker file schema in both projects
- Verify marker file is created/updated correctly
- Check for edge cases (missing marker, corrupted marker, multiple markers)

### 4. Command Execution Flow

**Questions to Answer**:
- [ ] How do slash commands in Claude Code find Python dependencies?
- [ ] How do shell commands (`taskwright init`) find Python dependencies?
- [ ] Are the paths consistent between Claude Code and shell execution?
- [ ] Do all commands follow the same import pattern?

**Analysis Required**:
- Trace execution flow from slash command → Python script → imports
- Document differences between Claude Code and shell execution
- Identify any hardcoded paths or assumptions

### 5. Regression Risk Assessment

**Critical Questions**:
- [ ] Will these fixes break existing local git clone installations?
- [ ] Will these fixes affect Conductor.build worktree usage?
- [ ] Are we introducing new dependencies or requirements?
- [ ] Could these changes affect users who installed before the fix?

**Analysis Required**:
- Test matrix: curl install, git clone, Conductor worktree, upgrade scenario
- Backward compatibility with existing marker files
- Migration path for users with broken installations

### 6. Documentation Accuracy

**Questions to Answer**:
- [ ] Does CLAUDE.md reflect the correct installation process?
- [ ] Are Python import examples in documentation correct?
- [ ] Is the troubleshooting guide up to date?
- [ ] Do we need to update README or installation docs?

**Analysis Required**:
- Audit all installation-related documentation
- Verify code examples match actual working code
- Check for outdated references to old installation process

## Files to Review

### Taskwright
```
installer/scripts/install.sh                    # Installation script
installer/core/lib/id_generator.py            # Example Python module with import issues
installer/core/commands/task-create.md        # Command with Python import documentation
tasks/backlog/TASK-FIX-A7B3-*.md               # Fix task for Python imports
.agentecflow/taskwright.marker.json             # Marker file with repo_path
CLAUDE.md                                        # Installation documentation
README.md                                        # User-facing installation guide
```

### RequireKit
```
installer/scripts/install.sh                    # Installation script
global/lib/feature_detection.py                 # Python module that may have import issues
tasks/backlog/TASK-FIX-C2D8-*.md               # Fix task for Python imports
.agentecflow/require-kit.marker.json            # Marker file
README.md                                        # Installation documentation
```

### Cross-Project
```
~/.agentecflow/                                 # Shared installation directory
~/.agentecflow/bin/                             # Symlinked commands
~/.agentecflow/commands/lib/                    # Installed Python libraries
```

## Success Criteria

### Must Have (Blockers for Public Launch)
- [ ] **Zero Python import errors** on fresh curl installation
- [ ] **Both shell and Claude Code execution** work correctly
- [ ] **No regressions** for existing git clone installations
- [ ] **Clear migration path** for users with broken installations
- [ ] **Documentation is accurate** and matches working installation

### Should Have (High Priority)
- [ ] **Automated test** for curl installation flow
- [ ] **Installation verification** command (e.g., `taskwright doctor`)
- [ ] **Clear error messages** if installation is incomplete
- [ ] **Platform compatibility** verified (macOS, Linux at minimum)

### Nice to Have (Post-Launch)
- [ ] **Rollback mechanism** for failed installations
- [ ] **Installation telemetry** to catch issues early
- [ ] **CI/CD testing** of curl installation process

## Review Mode Recommendation

**Suggested Mode**: `architectural` with `comprehensive` depth

**Rationale**:
- Pre-launch review requires highest scrutiny
- Installation architecture affects all users
- Regression risk is high due to rapid changes
- Need to validate design decisions, not just code quality

**Alternative**: Could use `technical-debt` mode to assess if quick fixes created debt

## Deliverables

### Review Report Should Include:

1. **Executive Summary**
   - Overall installation architecture assessment
   - Critical issues found (if any)
   - Go/No-Go recommendation for public launch

2. **Detailed Findings**
   - Python import path solution evaluation
   - Installation script completeness check
   - Regression risk analysis
   - Platform compatibility assessment

3. **Actionable Recommendations**
   - Priority 1 (must fix before launch)
   - Priority 2 (should fix before launch)
   - Priority 3 (can defer to post-launch)

4. **Decision Points**
   - Import path strategy: relative vs absolute vs bootstrap
   - Marker file design: current vs alternative approaches
   - Testing strategy: manual vs automated
   - Launch readiness: go vs delay vs conditional launch

5. **Implementation Guidance**
   - If import path changes needed, specific pattern to use
   - If installation script changes needed, exact modifications
   - If documentation updates needed, sections to revise
   - Test plan to verify fixes

## Next Steps After Review

### If Review Approves Launch:
1. Mark TASK-FIX-A7B3 and TASK-FIX-C2D8 as approved approach
2. Implement Python import fixes as recommended
3. Run final verification test
4. Update documentation
5. Proceed with public launch

### If Review Requires Changes:
1. Create new implementation tasks based on review recommendations
2. Fix critical issues identified
3. Re-test installation flow
4. Schedule follow-up review (quick mode)
5. Delay launch if necessary

### If Review Finds Blockers:
1. Escalate critical issues
2. Assess launch delay impact
3. Create emergency fix tasks
4. Consider phased rollout strategy

## Risk Mitigation

**If we launch with broken installation**:
- First user experience will be negative
- Support burden will be high
- Reputation damage for "production-ready" claim
- Potential security issues if users work around broken install

**If we delay launch for comprehensive fixes**:
- Additional development time
- Delayed user feedback
- Potential competitive disadvantage
- But: Higher quality first impression

## Related Context

**Recent Changes**:
- Marker file format updated to include `repo_path`
- Installation script modified to download repository
- Multiple commits made on macOS Parallels VM
- Both Taskwright and RequireKit affected

**Testing Environment**:
- macOS running under Parallels virtualization
- Claude Code integration testing
- Shell command testing
- Both projects tested in isolation and together

**Integration Points**:
- Taskwright can detect RequireKit via marker file
- Shared `~/.agentecflow/` directory structure
- Both use similar installation script patterns
- Both have Python import dependencies

## Questions for Human Decision

1. **Import Path Strategy**: Should we use relative imports (`from lib.X`), Python path bootstrap, or symlink approach? (See TASK-FIX-A7B3 for options)

2. **Testing Priority**: Should we add automated installation testing before launch, or rely on manual verification?

3. **Launch Timing**: If minor issues found, should we:
   - Fix and delay launch
   - Launch with known issues + quick hotfix plan
   - Phased rollout (early adopters first)

4. **Documentation**: Should we add "Installation Troubleshooting" section to CLAUDE.md before launch?

5. **Backward Compatibility**: Do we need to support users who installed during the "broken" period, or require fresh reinstall?

## Success Metrics

After fixes are implemented and launched:
- [ ] Zero installation failure reports in first week
- [ ] `taskwright init` works for 100% of curl installations
- [ ] `/task-create` works in Claude Code for 100% of installations
- [ ] No regression reports from existing git clone users
- [ ] Installation documentation receives zero "doesn't work" issues

---

## Review Execution Plan

**Recommended Command**:
```bash
/task-review TASK-REV-DEF4 --mode=architectural --depth=comprehensive
```

**Estimated Duration**: 4-6 hours (comprehensive depth)

**Expected Outcome**: Detailed architectural review report with go/no-go recommendation for public launch, specific implementation guidance for Python import fixes, and risk assessment for all identified issues.
