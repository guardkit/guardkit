# TASK-010 Implementation Plan

## Task: Update Manifest and Configuration

**Created**: 2025-11-01
**Complexity**: 2/10 (Simple configuration updates)
**Estimated Duration**: 1 hour

## Overview

Update manifest.json and configuration files to reflect guardkit's focus on task workflow with quality gates, removing any remaining requirements management references.

## Analysis

### Current State

1. **installer/global/manifest.json**: Already correctly updated with:
   - Name: "guardkit" ✓
   - Correct capabilities (no requirements-engineering or bdd-generation) ✓
   - Includes architectural-review and test-enforcement ✓

2. **Template settings**: Checked two MAUI template settings files - both are clean and focused on their specific stack configurations (no requirements-related paths)

3. **.claude/settings.json**: Contains legacy references that should be cleaned:
   - Name: "ai-engineer-sdlc" (should align with guardkit)
   - Features section references requirements and epics/features hierarchy
   - Description mentions "Software Engineering Lifecycle System"

### Required Changes

Only `.claude/settings.json` needs updating to align with guardkit branding and remove requirements-related configuration.

## Implementation Plan

### Files to Modify

1. `.claude/settings.json` - Update branding and remove requirements references

### Detailed Changes

#### File 1: `.claude/settings.json`

**Changes Required**:

1. **Update metadata** (lines 2-4):
   - Change name from "ai-engineer-sdlc" to "guardkit"
   - Update description to emphasize task workflow + quality gates

2. **Clean features section** (lines 5-19):
   - Remove or simplify requirements section (lines 6-9)
   - Remove tracking hierarchy reference to epics/features (line 16)
   - Keep testing section as-is (it's relevant)

**Proposed Updated Structure**:
```json
{
  "name": "guardkit",
  "version": "1.0.0",
  "description": "Lightweight task workflow with quality gates and architectural review",
  "features": {
    "testing": {
      "specification": "BDD/Gherkin",
      "execution": "automated",
      "gates": ["coverage", "complexity", "compliance"]
    },
    "tracking": {
      "state": "markdown",
      "changelog": true
    }
  },
  "defaults": {
    "testCoverage": 80,
    "maxComplexity": 10
  },
  // ... rest remains the same
}
```

### Implementation Steps

1. ✅ Verify manifest.json (already correct)
2. ✅ Check template settings (already clean)
3. ⏳ Update .claude/settings.json
4. ⏳ Validate JSON syntax
5. ⏳ Test configuration loading (if applicable)

## Testing Strategy

### Validation Steps

1. **JSON Syntax Validation**:
   ```bash
   python3 -m json.tool .claude/settings.json > /dev/null
   ```

2. **Verify Changes**:
   - Name is "guardkit"
   - No requirements-engineering references
   - No epics/features hierarchy references
   - Quality gates configuration intact

3. **Manual Review**:
   - Read updated file to confirm all changes correct
   - Ensure no syntax errors introduced

## Risk Assessment

**Risk Level**: LOW

- Simple JSON configuration update
- No code changes required
- Easy to rollback if needed
- manifest.json already correct (no changes needed)

## Success Criteria

- [ ] .claude/settings.json updated with guardkit branding
- [ ] No requirements-related configuration remains
- [ ] All JSON files have valid syntax
- [ ] Testing and quality gate configuration preserved

## Estimated LOC Changes

- Lines Modified: ~15 lines
- Files Changed: 1 file
- No new files created
- No files deleted

## Dependencies

None - standalone configuration update

## Notes

- manifest.json is already correct (no changes needed)
- Template settings are clean (no changes needed)
- Only .claude/settings.json requires update
