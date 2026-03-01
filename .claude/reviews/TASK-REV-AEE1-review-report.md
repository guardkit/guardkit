# Review Report: TASK-REV-AEE1

## Executive Summary

Four new GuardKit commands (`/system-arch`, `/system-design`, `/arch-refine`, `/design-refine`) are well-conceived and fill a genuine gap upstream of `/system-plan`. The existing codebase provides a strong foundation: `SystemPlanGraphiti`, `ArchitectureWriter`, entity dataclasses, and Jinja2 templates. Roughly 60-70% of `/system-arch` infrastructure already exists.

**Key findings**: 3 new entity types needed, 5 new templates, 2 new Graphiti service classes, 1 critical spike required (temporal superseding), and an ADR location conflict to resolve. Estimated effort: 16-22 days across 4 waves.

## Review Details
- **Mode**: Decision Analysis (deep)
- **Focus**: All aspects (technical, architecture, performance, security)
- **Priority**: Quality/reliability
- **Extensibility**: Considered
- **Complexity**: 8/10

---

## Section 1: What Already Exists (Reusable)

| Asset | Location | Reuse For |
|-------|----------|-----------|
| `SystemPlanGraphiti` | `guardkit/planning/graphiti_arch.py` | Direct reuse for `/system-arch`; extend for `/system-design` |
| `ArchitectureWriter` | `guardkit/planning/architecture_writer.py` | Direct reuse; extend for design-layer artefacts |
| `ArchitectureDecision` dataclass | `guardkit/knowledge/entities/architecture_context.py` | Reuse for ADRs; needs `superseded_by` field |
| `ComponentDef`, `SystemContextDef`, `CrosscuttingConcernDef` | `guardkit/knowledge/entities/` | Direct reuse |
| `adr.md.j2`, `system-context.md.j2`, `components.md.j2` | `guardkit/templates/` | Reuse; adr needs update |
| `get_relevant_context_for_topic()` | `SystemPlanGraphiti` | Reuse for `/arch-refine` semantic search |
| `has_architecture_context()` | `SystemPlanGraphiti` | `/system-design` prerequisite check |
| 12 existing ADRs | `docs/architecture/decisions/` | Numbering continues |

## Section 2: What Must Be Created

| Missing Asset | Required By |
|---------------|-------------|
| `DesignDecision` dataclass (DDR entity) | `/system-design`, `/design-refine` |
| `ApiContract` dataclass | `/system-design` |
| `DataModel` dataclass | `/system-design` |
| `container.md.j2` (C4 L2 Container) | `/system-arch` |
| `component-l3.md.j2` (C4 L3 Component) | `/system-design` |
| `api-contract.md.j2` | `/system-design` |
| `ddr.md.j2` (Design Decision Record) | `/system-design` |
| `SystemDesignGraphiti` class | `/system-design`, `/design-refine` |
| `DesignWriter` class | `/system-design` |
| 4 command specs | All commands |
| ADR numbering scanner | `/system-arch`, `/system-design` |
| Staleness flag mechanism | `/arch-refine`, `/design-refine` |
| Temporal superseding protocol | `/arch-refine`, `/design-refine` |

---

## Section 3: Architecture Findings

### Finding 1: ADR Location Conflict (MEDIUM)

**Current**: 12 ADRs at `docs/architecture/decisions/ADR-SP-NNN.md`
**BDD spec assumes** (ASSUM-005): `docs/adr/ADR-XXX-{slug}.md`

**Recommendation**: Use `docs/architecture/decisions/` (established convention). DDRs go to `docs/design/decisions/`. Override ASSUM-005 — convention is set by existing codebase.

### Finding 2: ADR Prefix Collision (LOW)

`ArchitectureDecision.entity_id` hardcodes `ADR-SP-` prefix. `/system-arch` ADRs need a distinct prefix.

**Recommendation**: Parametrise prefix on `ArchitectureDecision`: `prefix: str = "SP"` (backwards compatible). Use `"ARCH"` for `/system-arch` ADRs.

### Finding 3: Temporal Superseding Gap (HIGH)

Current `upsert_episode()` overwrites; BDD requires prior ADR to remain queryable with history.

**Recommended approach (Option A — Soft Superseding)**: Change existing ADR status to `"superseded"`, create new ADR with `supersedes` reference. Both remain queryable. Works with existing API. **Spike needed** to verify behaviour (1-2 hours).

### Finding 4: New Graphiti Groups Required (LOW)

Need `project_design` and `api_contracts` groups. Follows existing `SystemPlanGraphiti` pattern exactly.

### Finding 5: Pipeline Enforcement (LOW)

`/system-design` uses `has_architecture_context()` as prerequisite gate. Offers to chain to `/system-arch` if missing. Identical pattern to `/system-plan` mode auto-detection.

### Finding 6: C4 Diagram Strategy (MEDIUM)

| Command | Level | Template |
|---------|-------|----------|
| `/system-arch` | L1 Context | Existing `system-context.md.j2` |
| `/system-arch` | L2 Container | NEW `container.md.j2` |
| `/system-design` | L3 Component (>3 internal OR explicit) | NEW `component-l3.md.j2` |
| Refine commands | Revised L1/L2/L3 | Reuse templates |

**Recommendation**: Use native C4 Mermaid syntax (`C4Context`, `C4Container`, `C4Component`) for new templates. Don't change existing templates.

### Finding 7: ADR Template Missing "Alternatives Considered" (LOW)

Existing `adr.md.j2` lacks this section. Required by BDD spec.

**Fix**: Add `alternatives_considered: List[str]` to `ArchitectureDecision`, conditionally render in template.

### Finding 8: OpenAPI Generation Quality Risk (MEDIUM)

Claude generating OpenAPI 3.1 YAML from free-form answers risks structural errors.

**Recommendation**: Add `openapi-spec-validator` validation gate in `/system-design`.

### Finding 9: Multi-Protocol Extensibility (LOW)

ASSUM-008 confirms MCP + A2A + ACP. These are evolving protocols.

**Recommendation**: Make protocol selection user-configurable in `/system-design` session. Specify version targets.

---

## Section 4: Technical Options Analysis

### Option 1: Four-Wave Sequential Build (Recommended)

**Wave 1** (Days 1-3): Entity foundation + temporal superseding spike
- Update `ArchitectureDecision` (3 new fields)
- Create `DesignDecision`, `ApiContract`, `DataModel` dataclasses
- Spike: verify temporal superseding with existing Graphiti API

**Wave 2** (Days 4-6): Templates + Graphiti services
- Update `adr.md.j2`, create 4 new templates
- Create `SystemDesignGraphiti`, `DesignWriter` classes

**Wave 3** (Days 7-14): Command specs (parallelisable)
- `/system-arch.md` (3-4 days)
- `/system-design.md` (3-4 days, parallel)
- `/arch-refine.md` (2-3 days, after spike)
- `/design-refine.md` (2-3 days, parallel with arch-refine)

**Wave 4** (Days 15-18): Integration testing
- Test full pipeline on real project
- Verify Graphiti seeding flows downstream
- Test graceful degradation

**Effort**: 16-22 days | **Risk**: LOW (spike de-risks before Wave 3)

### Option 2: Command-Specs-First (Lightweight)

Write all 4 command specs first without Python infrastructure changes. Commands instruct Claude to generate artefacts directly. Python entity/template work deferred.

**Effort**: 8-12 days | **Risk**: MEDIUM (no type safety, no template reuse, Graphiti integration untested)

### Option 3: Phased Delivery (Two Releases)

**Release 1**: `/system-arch` + `/arch-refine` only (10-12 days)
**Release 2**: `/system-design` + `/design-refine` (8-10 days, after Release 1 validated)

**Effort**: 18-22 days total | **Risk**: LOW (validates pipeline incrementally)

---

## Section 5: Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Temporal superseding mechanism unproven | **HIGH** | Spike (1-2 hours) before `/arch-refine` spec |
| OpenAPI generation quality | MEDIUM | Add `openapi-spec-validator` gate |
| C4 diagram splitting for large projects | MEDIUM | Warning + manual split at review gate (MVP); automated Phase 2 |
| ADR location convention conflict | LOW | Follow existing code convention |
| Concurrent session conflict | LOW | Last-write-wins (existing upsert semantics) |
| MCP/A2A/ACP protocol evolution | LOW | User-selectable, version-pinned |

---

## Section 6: Decisions Required Before Implementation

1. **ADR location**: Use `docs/architecture/decisions/` (not `docs/adr/`)?
2. **DDR location**: Use `docs/design/decisions/` (not `docs/ddr/`)?
3. **ADR prefix**: Parametrise prefix (`"ARCH"` for `/system-arch`, `"SP"` default)?
4. **Temporal superseding**: Data-level Option A (spike first)?
5. **C4 Mermaid syntax**: Native C4 keywords for new templates?
6. **OpenAPI validation**: Add as quality gate?

All recommended **yes** — see rationale in Section 3.
