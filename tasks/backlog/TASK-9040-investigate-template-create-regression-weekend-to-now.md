# TASK-9040: Investigate Template-Create Regression (Weekend → Now)

**Status**: backlog
**Priority**: critical
**Created**: 2025-11-12T01:00:00Z
**Updated**: 2025-11-12T01:00:00Z
**Tags**: #investigation #regression #template-create #forensics
**Complexity**: 4/10 (Investigation - no coding yet)

---

## Description

**Critical Problem**: `/template-create` worked over the weekend to create core templates, but now **nothing works**. Need forensic analysis to understand what changed.

**User Report**: "At the weekend I ran the commands to create the core templates shipping with taskwright and it appeared to work, now it all just seems to have fallen apart."

---

## Investigation Questions

### 1. What Was Working?
- [ ] Which specific commands worked over the weekend?
- [ ] What templates were successfully created?
- [ ] What output/results were generated?
- [ ] Were there any errors at the time (ignored)?

### 2. What Changed Since Weekend?
- [ ] Git commits between weekend and now
- [ ] File modifications (code, config, templates)
- [ ] Environment changes (Python version, dependencies)
- [ ] System changes (OS updates, PATH changes)

### 3. What's Broken Now?
- [ ] Specific error messages
- [ ] Which phase fails (Q&A, analysis, generation)
- [ ] Is it a complete failure or partial?
- [ ] Does it fail on all projects or just some?

### 4. Root Cause Hypotheses
- [ ] Code regression (recent commit broke something)
- [ ] Environment change (dependency version)
- [ ] Data corruption (config files)
- [ ] User error (different command usage)

---

## Investigation Tasks

### Phase 1: Review Weekend Work (30 min)

1. **Check git history**
   ```bash
   cd ~/Projects/appmilla_github/taskwright

   # Commits since weekend (adjust date)
   git log --since="2025-11-09" --oneline

   # What was changed?
   git log --since="2025-11-09" --stat

   # Show diffs for template-create changes
   git log --since="2025-11-09" -p -- installer/global/commands/lib/template_create*
   ```

2. **Find completed tasks**
   ```bash
   # Look for template-creation related tasks
   find tasks/completed -name "*template*" -type f

   # What was the weekend work?
   ls -la tasks/completed/TASK-BRIDGE-*/
   ```

3. **Check generated templates**
   ```bash
   # What templates exist?
   ls -la ~/.agentecflow/templates/
   ls -la installer/global/templates/

   # When were they created?
   ls -la --time-style=full-iso ~/.agentecflow/templates/*/
   ```

### Phase 2: Compare Working vs Broken (1 hour)

1. **Identify working commit**
   ```bash
   # Find commit from weekend
   git log --since="2025-11-09" --until="2025-11-10" --oneline

   # Checkout that commit
   git checkout <weekend_commit_hash>

   # Test if it works
   cd ~/Projects/DeCUK.Mobile.MyDrive
   /template-create --validate --skip-qa

   # Does it work? ✅ or ❌
   ```

2. **Identify breaking commit**
   ```bash
   # If it works on weekend commit, bisect to find breaking commit
   git bisect start
   git bisect bad HEAD  # Current (broken)
   git bisect good <weekend_commit_hash>  # Weekend (working)

   # Test each commit
   # Mark good/bad until bisect finds the culprit
   ```

3. **Compare code differences**
   ```bash
   # Compare working vs broken
   git diff <weekend_commit> HEAD -- installer/global/commands/lib/template_create*
   git diff <weekend_commit> HEAD -- installer/global/lib/codebase_analyzer/
   ```

### Phase 3: Environment Check (30 min)

1. **Python version**
   ```bash
   python3 --version
   # Was it upgraded recently?
   ```

2. **Dependencies**
   ```bash
   pip list | grep -i "anthropic\|langchain\|openai"
   # Check for version changes
   ```

3. **System changes**
   ```bash
   # MacOS updates?
   softwareupdate --history | grep "2025-11-"
   ```

### Phase 4: Reproduce Working State (30 min)

1. **Create test environment**
   ```bash
   # Checkout working commit
   git checkout <weekend_commit_hash>

   # Try to reproduce success
   cd ~/Projects/DeCUK.Mobile.MyDrive
   /template-create --validate --skip-qa
   ```

2. **Document working configuration**
   - Commit hash that works
   - Python version
   - Dependency versions
   - Command used
   - Output/results

---

## Expected Outputs

### Investigation Report
Document findings in: `docs/investigations/template-create-regression-20251112.md`

**Report should include:**
1. **Timeline**: What worked when
2. **Changes**: Git commits between working and broken
3. **Root Cause**: Specific change that broke it
4. **Fix**: What needs to be reverted/fixed
5. **Prevention**: How to avoid this in future

### Recommended Actions
Based on findings:
- Revert breaking commit (if found)
- Fix regression (if code issue)
- Update environment (if dependency issue)
- Create bug fix tasks

---

## Acceptance Criteria

- [ ] Identified which commit/change broke template-create
- [ ] Documented working vs broken state
- [ ] Root cause analysis complete
- [ ] Recommended fix identified
- [ ] Investigation report written

---

## Timeline

- **Total:** 2-3 hours (investigation only, no fixes)

---

## Related Tasks

- **TASK-BRIDGE-001 through TASK-BRIDGE-006:** Previous template-create work
- **TASK-9037:** Build artifact exclusion (potential fix)
- **TASK-9038, TASK-9039:** Future improvements

---

## Success Criteria

✅ **Understand what broke** - Clear explanation of regression
✅ **Know how to fix** - Specific action items
✅ **Prevent recurrence** - Testing/validation improvements
