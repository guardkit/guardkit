# Code Quality Review Report: TASK-SDK-E02D

## Executive Summary

**Review Type**: Code Quality (--mode=code-quality)
**Task**: Review Claude Agents SDK installation in install.sh
**Complexity**: 3/10 (Simple)
**Overall Finding**: The SDK installation is **correctly implemented** with one notable quality gap

**Score: 85/100**

| Category | Score | Notes |
|----------|-------|-------|
| Correctness | 95/100 | SDK is properly specified and installed |
| Error Handling | 80/100 | Good fallback patterns, missing SDK-specific verification |
| Documentation | 85/100 | Good inline comments, could improve API key guidance |
| Maintainability | 85/100 | Clean structure, follows existing patterns |
| User Experience | 80/100 | Missing explicit SDK verification feedback |

---

## Review Findings

### ✅ What's Working Correctly

#### 1. pyproject.toml Configuration (CORRECT)

```toml
[project.optional-dependencies]
autobuild = [
    "claude-agent-sdk>=0.1.0",
]
```

**Analysis**: The `claude-agent-sdk` is correctly specified as an optional dependency under the `[autobuild]` extras group with an appropriate minimum version constraint (`>=0.1.0`).

**Location**: [pyproject.toml:35-37](pyproject.toml#L35-L37)

#### 2. install.sh Installation Logic (CORRECT)

```bash
# Install with [autobuild] extras to include claude-agent-sdk
python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages 2>&1
```

**Analysis**: The script correctly installs the package with `[autobuild]` extras, which triggers installation of `claude-agent-sdk` as a dependency.

**Location**: [installer/scripts/install.sh:360-365](installer/scripts/install.sh#L360-L365)

#### 3. Runtime SDK Checks (CORRECT)

The codebase implements proper runtime SDK availability checks:

- **CLI Pre-flight**: [guardkit/cli/autobuild.py:53-98](guardkit/cli/autobuild.py#L53-L98) - `_check_sdk_available()` and `_require_sdk()` functions
- **Agent Invoker**: [guardkit/orchestrator/agent_invoker.py:1195-1210](guardkit/orchestrator/agent_invoker.py#L1195-L1210) - Dynamic import with helpful error message
- **Doctor Command**: [guardkit/cli/doctor.py:413-436](guardkit/cli/doctor.py#L413-L436) - SDK package check included in diagnostics

**Pattern used throughout**:
```python
try:
    from claude_agent_sdk import query
    return True
except ImportError:
    return False
```

#### 4. Error Messages (GOOD)

When SDK is missing, users receive helpful guidance:

```
Error: Claude Agent SDK not available

AutoBuild requires the Claude Agent SDK.

To install:
  pip install claude-agent-sdk
  # OR
  pip install guardkit-py[autobuild]

For more info: guardkit doctor
```

---

### ⚠️ Quality Gap: Missing Post-Installation SDK Verification

**Location**: [installer/scripts/install.sh:387-398](installer/scripts/install.sh#L387-L398)

**Current behavior**: The script only verifies `guardkit` is importable:
```bash
python3 -c "import guardkit" 2>/dev/null
```

**Gap**: No verification that `claude_agent_sdk` is actually importable after installation.

**Risk**: If SDK installation fails silently (e.g., dependency conflict, network issue), users won't discover this until they try to run AutoBuild, leading to a poor user experience.

**Impact**: Low - The SDK will be checked at runtime and provide clear error messages. However, immediate feedback during installation would be better UX.

---

## Recommendations

### Recommendation 1: Add SDK Import Verification (Priority: Medium)

**Add explicit SDK verification after installation** in `install_python_package()`:

```bash
# After existing guardkit import check (line 398):

# Verify AutoBuild SDK if installed with autobuild extras
if python3 -c "import claude_agent_sdk" 2>/dev/null; then
    print_success "Claude Agent SDK is available (AutoBuild ready)"
else
    print_warning "Claude Agent SDK not importable after installation"
    print_info "AutoBuild features may not work. Try: pip install claude-agent-sdk"
fi
```

**Files to modify**: [installer/scripts/install.sh](installer/scripts/install.sh) (around line 398)

**Complexity**: Simple addition (~10 lines)

### Recommendation 2: Add API Key Guidance (Priority: Low)

**Add a note about API key requirements** in the installation summary:

```bash
# In print_summary() function:
echo ""
echo -e "${BOLD}API Key Configuration:${NC}"
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY is set"
else
    echo -e "  ${YELLOW}⚠${NC} ANTHROPIC_API_KEY not set"
    echo "      AutoBuild requires API credentials. See: guardkit doctor"
fi
```

**Files to modify**: [installer/scripts/install.sh](installer/scripts/install.sh) (around line 1440)

**Note**: The official SDK documentation shows `ANTHROPIC_API_KEY` or Claude Code authentication is required.

### Recommendation 3: Document SDK Version Requirements (Priority: Low)

**Add a comment** in pyproject.toml explaining version constraints:

```toml
[project.optional-dependencies]
# Claude Agent SDK for AutoBuild Player/Coach workflow
# Requires Python 3.10+ (same as guardkit)
# See: https://platform.claude.com/docs/en/agent-sdk/python
autobuild = [
    "claude-agent-sdk>=0.1.0",
]
```

---

## Acceptance Criteria Analysis

| Criterion | Status | Notes |
|-----------|--------|-------|
| ✅ Verify `claude-agent-sdk` in pyproject.toml `[autobuild]` extras | **VERIFIED** | Line 36 |
| ✅ Confirm install.sh correctly installs SDK via extras | **VERIFIED** | Line 363 |
| ⚠️ Add explicit SDK import verification after installation | **MISSING** | Recommended as enhancement |
| ⚠️ Add guidance for API key configuration | **PARTIAL** | `guardkit doctor` covers this |
| ⚠️ Document SDK version requirements | **PARTIAL** | Version constraint exists, docs could improve |

---

## Test Verification

| Test | Expected Result | How to Verify |
|------|-----------------|---------------|
| SDK is importable | `python3 -c "import claude_agent_sdk"` exits 0 | Run after `pip install guardkit-py[autobuild]` |
| `guardkit autobuild` command works | Shows help or runs successfully | Run `guardkit autobuild --help` |
| `guardkit doctor` shows SDK status | SDK check passes | Run `guardkit doctor` |

---

## Conclusion

The Claude Agent SDK installation is **correctly implemented**. The current architecture follows best practices:

1. **Optional dependency pattern** - SDK is not required for core guardkit functionality
2. **Runtime availability checks** - All AutoBuild entry points verify SDK before use
3. **Graceful degradation** - Clear error messages guide users to install SDK when needed
4. **Multiple installation paths** - Users can install via `pip install claude-agent-sdk` or `pip install guardkit-py[autobuild]`

The single quality gap (missing post-installation verification) is a minor UX improvement that would provide immediate feedback during installation rather than waiting for first AutoBuild use.

---

## Decision

**[A]ccept** - The implementation is correct. The identified gap is a minor enhancement, not a blocker.

**Options**:
- **[A]ccept**: Archive this review as complete (current implementation is correct)
- **[I]mplement**: Create implementation task for the SDK verification enhancement
- **[C]ancel**: Discard review

---

*Review completed: 2026-01-25*
*Mode: code-quality*
*Depth: standard*
