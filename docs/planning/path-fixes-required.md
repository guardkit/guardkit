# Path Fixes Required for TASK-957C

**Date**: 2025-11-25
**Status**: Documented (requires manual fix in main repo)

## Summary

The main repository's README.md contains 3 path mismatches that reference non-existent files. These need to be corrected to point to the actual MCP integration documentation in `docs/deep-dives/mcp-integration/`.

## Path Corrections Needed

### File: /Users/richardwoollcott/Projects/appmilla_github/guardkit/README.md

#### Fix 1: Context7 Setup Path (Line 360)
**Current (incorrect)**:
```markdown
- [Context7 Setup](docs/guides/context7-mcp-setup.md) - Up-to-date library docs (recommended)
```

**Should be**:
```markdown
- [Context7 Setup](docs/deep-dives/mcp-integration/context7-setup.md) - Up-to-date library docs (recommended)
```

#### Fix 2: Design Patterns Setup Path (Line 361)
**Current (incorrect)**:
```markdown
- [Design Patterns Setup](docs/guides/design-patterns-mcp-setup.md) - Pattern recommendations
```

**Should be**:
```markdown
- [Design Patterns Setup](docs/deep-dives/mcp-integration/design-patterns-setup.md) - Pattern recommendations
```

#### Fix 3: MCP Optimization Guide Path (Line 379)
**Current (incorrect)**:
```markdown
- [MCP Optimization Guide](docs/guides/mcp-optimization-guide.md) - Model Context Protocol integration
```

**Should be**:
```markdown
- [MCP Optimization Guide](docs/deep-dives/mcp-integration/mcp-optimization.md) - Model Context Protocol integration
```

## Verification

After fixes are applied, verify that all links resolve correctly:

```bash
# Check that target files exist
ls -lh docs/deep-dives/mcp-integration/context7-setup.md
ls -lh docs/deep-dives/mcp-integration/design-patterns-setup.md
ls -lh docs/deep-dives/mcp-integration/mcp-optimization.md
```

Expected output:
- context7-setup.md: 17 KB, 728 lines
- design-patterns-setup.md: 19 KB, 745 lines
- mcp-optimization.md: 34 KB, 1134 lines

## Status Check

**Main CLAUDE.md** (CORRECT):
- ✅ Line 700: `docs/deep-dives/mcp-integration/context7-setup.md`
- ✅ Line 701: `docs/deep-dives/mcp-integration/design-patterns-setup.md`
- ✅ Line 717: `docs/deep-dives/mcp-integration/mcp-optimization.md`

**README.md** (NEEDS FIX):
- ❌ Line 360: `docs/guides/context7-mcp-setup.md` (incorrect)
- ❌ Line 361: `docs/guides/design-patterns-mcp-setup.md` (incorrect)
- ❌ Line 379: `docs/guides/mcp-optimization-guide.md` (incorrect)

## Implementation

These fixes should be applied in the main repository using:

```bash
# Navigate to main repo
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Apply fixes using sed or manual edit
# Then commit
git add README.md
git commit -m "fix: Correct MCP integration documentation paths in README

- Update Context7 Setup link to deep-dives/mcp-integration/
- Update Design Patterns Setup link to deep-dives/mcp-integration/
- Update MCP Optimization Guide link to deep-dives/mcp-integration/

Fixes broken documentation links. All files exist at deep-dives paths.
Task: TASK-957C"
```

## Why This Matters

1. **Broken Links**: Users clicking these links in README.md get 404 errors
2. **Documentation Discovery**: MCP integration guides are in deep-dives/, not guides/
3. **Consistency**: CLAUDE.md already has correct paths, README.md should match
4. **MkDocs Migration**: Documentation plan assumes correct paths

## Related Files

Other files that reference old paths (lower priority):
- tasks/backlog/design-url-integration/TASK-UX-187C-update-claude-md.md (lines 207-208)
- installer/core/agents/task-manager.md (line 345)
- Various completed task files (historical reference only)

These can be fixed later as they're not primary user-facing documentation.
