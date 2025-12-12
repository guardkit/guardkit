# Review Report: TASK-REV-INIT

## Executive Summary

**Critical Finding**: The `guardkit init` command (via `init-project.sh`) does NOT copy the `.claude/rules/` directory structure from templates. This means users initializing projects with rules-enabled templates will NOT receive the modular rules structure that provides 60-70% context window reduction.

**Overall Assessment**: 6/10 - Templates have been properly updated with rules structure, but the initialization flow is broken for this new structure.

## Review Details

- **Mode**: Code Quality Review
- **Depth**: Standard
- **Duration**: ~30 minutes
- **Reviewer**: Claude AI

## Findings

### Critical Issues

#### 1. [CRITICAL] init-project.sh Does Not Copy .claude/rules/ Directory

**Location**: [installer/scripts/init-project.sh](installer/scripts/init-project.sh):195-270

**Evidence**: The `copy_template_files()` function copies:
- `CLAUDE.md` from template root (line 196-199)
- `agents/` directory (lines 201-222)
- `templates/` directory (lines 225-229)
- `docs/patterns/` and `docs/reference/` (lines 231-250)

**Missing**: No code to copy `.claude/rules/` directory from template source.

**Impact**:
- Users running `guardkit init react-typescript` get the template's `CLAUDE.md` but NOT the modular rules structure
- The 60-70% context window reduction benefit is lost
- References in CLAUDE.md to `.claude/rules/patterns/` and `.claude/rules/guidance/` become broken

**Severity**: CRITICAL - This breaks the intended functionality of the rules structure feature.

#### 2. [MEDIUM] Inconsistent CLAUDE.md Location in Templates

**Finding**: Templates have inconsistent CLAUDE.md placement:
- `react-typescript/CLAUDE.md` (root level)
- `react-typescript/.claude/CLAUDE.md` (doesn't exist - only `.claude/rules/` exists)
- `default/.claude/CLAUDE.md` (inside .claude)
- `fastapi-python/CLAUDE.md` (root level) AND `fastapi-python/.claude/CLAUDE.md` (both exist)

**Impact**: init-project.sh only copies `$template_dir/CLAUDE.md`, potentially missing `.claude/CLAUDE.md` in some templates.

#### 3. [LOW] Documentation References to `rules/agents/`

**Finding**: 25 files still reference `rules/agents/` instead of `rules/guidance/` (the renamed directory from TASK-CRS-014).

**Files with outdated references** (excluding task/review files):
- Some may be historical task descriptions that don't need updating
- The rules-structure-guide.md has been correctly updated

**Impact**: Low - Most references are in completed task files, not user-facing documentation.

### Positive Findings

1. **Templates Have Correct Rules Structure**
   - All 5 reference templates have proper `.claude/rules/` directories
   - Rules structure follows the documented pattern (code-style.md, testing.md, patterns/, guidance/)
   - `install.sh` correctly copies templates to `~/.agentecflow/templates/`

2. **Documentation is Accurate**
   - `rules-structure-guide.md` correctly documents `rules/guidance/` (not `rules/agents/`)
   - Root CLAUDE.md correctly references rules structure as default for `/template-create`
   - Progressive disclosure architecture is well documented

3. **Install Script Copies Full Template Structure**
   - `install.sh` (line 395-406) does a full `cp -r` of templates to `~/.agentecflow/templates/`
   - This means templates stored in `~/.agentecflow/templates/` DO include `.claude/rules/`
   - The problem is only in `init-project.sh` which selectively copies files

## Recommendations

### 1. [HIGH PRIORITY] Update init-project.sh to Copy .claude/rules/

Add the following code block to `copy_template_files()` function after line 229:

```bash
# Copy .claude/rules/ directory (for Claude Code modular rules)
if [ -d "$template_dir/.claude/rules" ]; then
    mkdir -p .claude/rules
    cp -r "$template_dir/.claude/rules/"* .claude/rules/ 2>/dev/null || true
    print_success "Copied rules structure for Claude Code"
fi
```

### 2. [MEDIUM PRIORITY] Handle Both CLAUDE.md Locations

Update the CLAUDE.md copy logic to check both locations:

```bash
# Copy CLAUDE.md context file (check both locations)
if [ -f "$template_dir/.claude/CLAUDE.md" ]; then
    cp "$template_dir/.claude/CLAUDE.md" .claude/
    print_success "Copied project context file"
elif [ -f "$template_dir/CLAUDE.md" ]; then
    cp "$template_dir/CLAUDE.md" .claude/
    print_success "Copied project context file"
fi
```

### 3. [LOW PRIORITY] Standardize Template CLAUDE.md Location

Consider moving all template CLAUDE.md files to `.claude/CLAUDE.md` for consistency, OR documenting that templates should have CLAUDE.md at the template root (not in .claude/).

### 4. [LOW PRIORITY] Add Post-Init Verification

Add a verification step at the end of init-project.sh that checks if rules structure was expected and copied:

```bash
# Verify rules structure if template had it
if [ -d "$template_dir/.claude/rules" ] && [ ! -d ".claude/rules" ]; then
    print_warning "Rules structure expected but not copied"
fi
```

## Files Requiring Changes

| File | Priority | Change Required |
|------|----------|-----------------|
| `installer/scripts/init-project.sh` | HIGH | Add .claude/rules/ copying logic |
| `installer/scripts/init-project.sh` | MEDIUM | Handle both CLAUDE.md locations |

## Implementation Complexity

- **Effort**: Low (1-2 hours)
- **Risk**: Low (additive change, no breaking changes)
- **Files to Change**: 1 (`init-project.sh`)
- **Lines of Code**: ~15-20 new lines

## Verification Checklist

After implementation:
- [ ] Run `guardkit init react-typescript` in test directory
- [ ] Verify `.claude/rules/` directory is created
- [ ] Verify `.claude/rules/guidance/` contains agent summaries
- [ ] Verify `.claude/rules/patterns/` contains pattern files
- [ ] Verify `.claude/rules/code-style.md` and `testing.md` exist
- [ ] Verify CLAUDE.md is copied correctly
- [ ] Run `guardkit doctor` to verify installation health

## Conclusion

The rules structure feature is correctly implemented in templates and well documented, but the initialization flow (`guardkit init`) does not copy the `.claude/rules/` directory. This is a critical gap that should be addressed to deliver the intended 60-70% context window reduction to users.

The fix is straightforward - approximately 15-20 lines of bash code in `init-project.sh`.

---

**Review Date**: 2025-12-11
**Review Mode**: code-quality
**Review Depth**: standard
