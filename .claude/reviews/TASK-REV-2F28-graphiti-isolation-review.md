# Review Report: TASK-REV-2F28 - Graphiti Project Isolation

## Executive Summary

Graphiti project isolation is **robust and directory-based by default**, but **repository renaming/moving WILL orphan existing knowledge** unless mitigated. The isolation mechanism uses the current working directory name as the project identifier, which is then prefixed to all project-scoped group IDs.

**Key Finding**: Moving `youtube-transcript-mcp` to `guardkit-examples` will result in orphaned knowledge unless you either (1) migrate early before significant seeding, or (2) configure an explicit project_id that survives the move.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Quick
- **Duration**: ~15 minutes
- **Files Analyzed**: 4 core files

## Findings

### Finding 1: Project Isolation Mechanism

**Location**: [graphiti_client.py:207-211](guardkit/knowledge/graphiti_client.py#L207-L211)

The project ID is determined by a cascading priority:
1. **Explicit config** (`GraphitiConfig.project_id`) - highest priority
2. **Auto-detect from cwd** - default behavior

```python
if self.config.project_id is not None:
    self._project_id = self.config.project_id
elif auto_detect_project:
    self._project_id = normalize_project_id(get_current_project_name())
```

**Impact**: Auto-detection is the default. Moving a directory changes the project ID.

### Finding 2: Group ID Prefixing Pattern

**Location**: [graphiti_client.py:323-325](guardkit/knowledge/graphiti_client.py#L323-L325)

Project-scoped groups use the pattern: `{project_id}__{group_name}`

```python
return f"{self._project_id}__{group_name}"
```

**Example**:
- Current: `youtube-transcript-mcp__project_overview`
- After move: `guardkit-examples__project_overview` (new, empty)
- Orphaned: `youtube-transcript-mcp__project_overview` (has data, never queried)

### Finding 3: System vs Project Groups

**Location**: [graphiti_client.py:183-190](guardkit/knowledge/graphiti_client.py#L183-L190), [graphiti_client.py:1043-1064](guardkit/knowledge/graphiti_client.py#L1043-L1064)

Two scopes exist:

| Scope | Prefix Pattern | Examples | Migration Impact |
|-------|---------------|----------|------------------|
| **System** | None (unprefixed) | `guardkit_templates`, `product_knowledge` | Unaffected by moves |
| **Project** | `{project}__{group}` | `project_overview`, `feature_specs` | Orphaned on move |

**Project groups affected by migration**:
- `project_overview`
- `project_architecture`
- `feature_specs`
- `project_decisions`
- `project_constraints`
- `domain_knowledge`

### Finding 4: No Built-in Migration Path

There is **no utility** to:
- Rename project prefixes in existing episodes
- Copy episodes from one project namespace to another
- Reconcile orphaned knowledge after a directory rename

The `clear_project_groups()` method can delete project knowledge, but cannot migrate it.

### Finding 5: Project Name Normalization

**Location**: [graphiti_client.py:55-90](guardkit/knowledge/graphiti_client.py#L55-L90)

Project IDs are normalized:
- `YouTube Transcript MCP` → `youtube-transcript-mcp`
- `guardkit-examples` → `guardkit-examples`

This normalization is consistent, but the source (directory name) remains mutable.

### Finding 6: Current Project State

From [GRAPHITI-KNOWLEDGE.md](../youtube-transcript-mcp/docs/research/GRAPHITI-KNOWLEDGE.md):
- Knowledge is documented but may not be fully seeded yet
- Walking skeleton features (FEAT-SKEL-001 to 003) are planned
- Project is at early stage before significant knowledge accumulation

## Risk Assessment

| Risk | Severity | Likelihood | Notes |
|------|----------|------------|-------|
| Knowledge orphaning on move | **High** | **Certain** | If data seeded, it WILL be orphaned |
| Data loss | **Low** | Low | Data isn't lost, just unreachable |
| Re-seeding overhead | **Medium** | Medium | Depends on knowledge volume |

## Recommendations

### Option 1: [M]igrate Early (RECOMMENDED)

Move repository **before** significant knowledge seeding.

**Rationale**:
- Current state shows minimal knowledge seeded (mostly documentation)
- Walking skeleton features not yet implemented
- Clean slate avoids technical debt

**Steps**:
1. Move repo: `github.com/RichWoollcott/youtube-transcript-mcp` → `github.com/guardkit/guardkit-examples`
2. Re-initialize: `guardkit init` in new location
3. Re-seed system knowledge (automatic on init)
4. Project knowledge seeds under `guardkit-examples__*` prefix

**Effort**: Low (if done now)

### Option 2: [C]onfigure Explicit ID

Set `project_id` in configuration to decouple from directory name.

**Implementation** (requires code addition):
```python
# In guardkit.yaml or similar config
graphiti:
  project_id: "youtube-mcp"  # Explicit, survives directory moves
```

**Current limitation**: No config file mechanism exists for project_id. Would require:
- Creating `guardkit.yaml` schema with `graphiti.project_id` field
- Loading config at GraphitiClient initialization
- ~2-4 hour implementation effort

**Rationale**: Future-proof but requires development work.

### Option 3: [A]ccept Re-seeding

Move when ready and re-seed knowledge as needed.

**Rationale**:
- Knowledge can be regenerated from documentation
- No urgent need for complex migration
- Simplest approach if knowledge volume remains low

**Trade-off**: May lose any manually captured insights not in documentation.

### Option 4: [N]o Action - REJECTED

Current isolation mechanism is NOT robust enough for repo moves. This option is not viable for the stated use case.

## Decision Matrix

| Option | Effort | Future-Proof | Data Preserved | Recommended For |
|--------|--------|--------------|----------------|-----------------|
| Migrate Early | Low | Medium | N/A | Early-stage projects |
| Configure ID | Medium | High | Yes | Established projects |
| Accept Re-seed | Low | Low | No | Low-value knowledge |

## Conclusion

**Recommended Decision**: **[M]igrate Early**

The youtube-transcript-mcp project is at an ideal stage for migration:
1. Walking skeleton not yet built (FEAT-SKEL-001 still planned)
2. Knowledge is mostly documented, not heavily seeded
3. Moving now avoids future migration complexity
4. Dual-use (personal + example) works better under the guardkit org

**Next Steps** (if [M]igrate Early chosen):
1. Fork/transfer to guardkit/guardkit-examples
2. Update remote URLs locally
3. Run `guardkit init` to establish new project namespace
4. Proceed with walking skeleton implementation

---

## Appendix: Code References

| File | Key Functions |
|------|---------------|
| `guardkit/knowledge/graphiti_client.py` | `get_current_project_name()`, `normalize_project_id()`, `_apply_group_prefix()` |
| `guardkit/integrations/graphiti/project.py` | `initialize_project()`, `get_project_info()` |
| `guardkit/knowledge/project_seeding.py` | `seed_project_knowledge()` |

---

_Review completed: 2026-02-04_
_Reviewer: architectural-reviewer agent_
