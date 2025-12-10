# Template-Create Fixes for Complex Codebases

## Overview

This task group addresses issues discovered when running `/template-create` against the MyDrive .NET MAUI repository (309 files, 11 frameworks, 11 patterns, 9 layers). The command produced partial output due to size validation failures and missing agent generation.

**Source Review**: [TASK-REV-TC01-mydrive-review-report.md](../../../.claude/reviews/TASK-REV-TC01-mydrive-review-report.md)

## Problem Statement

The `/template-create` command fails for complex codebases:

1. **CLAUDE.md not generated**: Core content (36.95KB) exceeds 10KB limit
2. **No agents directory**: Phase 5 fails silently, no fallback triggered
3. **Miscategorized templates**: C#/.NET files placed in "other" category
4. **Technical debt**: `installer/global/` naming causes Python import issues

## Impact

- **Blocking**: Users cannot generate templates for enterprise-scale projects
- **Quality**: Generated templates missing specialized agents
- **Developer Experience**: Confusing "other" category for well-known file types

## Solution Summary

| Task | Problem | Solution | Priority |
|------|---------|----------|----------|
| TASK-FIX-CLMD-SIZE | 36.95KB > 10KB limit | Truncate + summarize content | Critical |
| TASK-FIX-AGENT-GEN | No agents generated | Add heuristic fallback | High |
| TASK-FIX-LAYER-CLASS | Files in "other" | Add C# classifier | Medium |
| TASK-ENH-SIZE-LIMIT | No override option | Add `--claude-md-size-limit` flag | Low |
| TASK-RENAME-GLOBAL | Python keyword issue | Rename directory | Medium |

## Success Criteria

After implementation:

```bash
# This should work without errors
cd ~/Projects/MyDrive
/template-create --name mydrive-maui

# Expected output:
# ✅ manifest.json (2.1KB)
# ✅ settings.json (1.8KB)
# ✅ CLAUDE.md (core: 8.5KB, 76% reduction)
# ✅ docs/patterns/README.md (12KB)
# ✅ docs/reference/README.md (15KB)
# ✅ templates/ (10 files)
# ✅ agents/ (3-5 agents)
```

## Files Modified

| File | Tasks |
|------|-------|
| `installer/global/lib/template_generator/claude_md_generator.py` | FIX-CLMD-SIZE |
| `installer/global/lib/template_generator/models.py` | FIX-CLMD-SIZE, ENH-SIZE-LIMIT |
| `installer/global/lib/agent_generator/agent_generator.py` | FIX-AGENT-GEN |
| `installer/global/commands/lib/template_create_orchestrator.py` | FIX-AGENT-GEN, ENH-SIZE-LIMIT |
| `installer/global/lib/template_generator/layer_classifier.py` | FIX-LAYER-CLASS |
| `installer/global/commands/template-create.md` | ENH-SIZE-LIMIT |
| `installer/global/*` (directory rename) | RENAME-GLOBAL |

## Testing Strategy

1. **Unit tests**: Each task adds specific unit tests
2. **Integration test**: Re-run `/template-create` on MyDrive after Wave 1
3. **Regression test**: Verify existing templates still generate correctly

## Related Documentation

- [Progressive Disclosure Guide](../../../docs/guides/progressive-disclosure.md)
- [Template Create Command](../../../installer/global/commands/template-create.md)
- [Agent Generator](../../../installer/global/lib/agent_generator/agent_generator.py)
