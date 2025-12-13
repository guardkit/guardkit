# Implementation Guide: Unified Clarification Subagent

## Wave Breakdown

### Wave 1: Agent Creation (No Dependencies)

#### TASK-WC-005: Create clarification-questioner Agent
**Effort**: 2-3 hours
**Mode**: task-work

Create the unified agent at `installer/core/agents/clarification-questioner.md`.

The agent must:
1. Accept `context_type` parameter (review_scope, implementation_prefs, implementation_planning)
2. Import and use existing `lib/clarification/*` code
3. Respect all clarification flags (--no-questions, --with-questions, --defaults, --answers)
4. Return structured `ClarificationContext`
5. Include ALWAYS/NEVER/ASK boundaries

---

### Wave 2: Command Updates (Parallel - 3 Workspaces)

#### TASK-WC-006: Update task-work.md
**Effort**: 1-2 hours
**Mode**: direct
**Workspace**: `unified-clarification-wave2-1`

Add Phase 1.6 subagent invocation:
- Context type: `implementation_planning`
- Trigger: After Phase 1.5 (context loading), before Phase 2 (planning)
- Store result for Phase 2 prompt

#### TASK-WC-007: Update feature-plan.md
**Effort**: 1-2 hours
**Mode**: direct
**Workspace**: `unified-clarification-wave2-2`

Add two subagent invocations:
1. **Context A** (review_scope): Before /task-review execution
2. **Context B** (implementation_prefs): At [I]mplement decision checkpoint

#### TASK-WC-008: Update task-review.md
**Effort**: 1-2 hours
**Mode**: direct
**Workspace**: `unified-clarification-wave2-3`

Add Phase 1 subagent invocation:
- Context type: `review_scope`
- Trigger: During context loading, before review analysis
- Use result in review execution

---

### Wave 3: Infrastructure Updates (Parallel - 3 Workspaces)

#### TASK-WC-009: Update Installer
**Effort**: 0.5 hours
**Mode**: direct
**Workspace**: `unified-clarification-wave3-1`

Update `installer/scripts/install.sh`:
```bash
# Copy clarification-questioner agent
cp "$GUARDKIT_PATH/installer/core/agents/clarification-questioner.md" \
   "$HOME/.agentecflow/agents/"
```

#### TASK-WC-010: Update guardkit init
**Effort**: 0.5 hours
**Mode**: direct
**Workspace**: `unified-clarification-wave3-2`

Verify agent is discoverable after init:
- May be a no-op if agents are loaded from `~/.agentecflow/agents/` globally
- Document if behavior differs per template
- Test with template initialization

#### TASK-WC-011: Update Documentation
**Effort**: 1 hour
**Mode**: direct
**Workspace**: `unified-clarification-wave3-3`

Update files:
1. `CLAUDE.md` (root) - Clarifying Questions section
2. `.claude/CLAUDE.md` - Clarifying Questions section
3. Remove references to Python orchestrators for clarification
4. Document unified subagent pattern
5. Explain context types (A, B, C)

---

### Wave 4: Testing (Depends on Waves 2 & 3)

#### TASK-WC-012: Integration Smoke Tests
**Effort**: 1 hour
**Mode**: task-work

Create tests at `tests/integration/clarification/`:

Test cases:
1. `/task-work TASK-XXX` with complexity 5+ → clarification questions appear
2. `/task-work TASK-XXX --no-questions` → clarification skipped
3. `/feature-plan "description"` → Context A questions appear
4. `/feature-plan` [I]mplement → Context B questions appear
5. `/task-review TASK-XXX` → Context A questions appear

---

## Parallel Execution with Conductor

### Wave 2 Parallel Setup
```bash
# Create 3 workspaces for Wave 2
conductor spawn unified-clarification-wave2-1
conductor spawn unified-clarification-wave2-2
conductor spawn unified-clarification-wave2-3

# In each workspace:
# workspace 1: /task-work TASK-WC-006
# workspace 2: /task-work TASK-WC-007
# workspace 3: /task-work TASK-WC-008
```

### Wave 3 Parallel Setup
```bash
# Create 3 workspaces for Wave 3
conductor spawn unified-clarification-wave3-1
conductor spawn unified-clarification-wave3-2
conductor spawn unified-clarification-wave3-3

# In each workspace:
# workspace 1: Directly edit installer/scripts/install.sh
# workspace 2: Verify guardkit init behavior
# workspace 3: Directly edit CLAUDE.md files
```

---

## Key Files to Modify

| File | Task | Changes |
|------|------|---------|
| `installer/core/agents/clarification-questioner.md` | WC-005 | CREATE |
| `installer/core/commands/task-work.md` | WC-006 | Add Phase 1.6 |
| `installer/core/commands/feature-plan.md` | WC-007 | Add Context A + B |
| `installer/core/commands/task-review.md` | WC-008 | Add Context A |
| `installer/scripts/install.sh` | WC-009 | Add agent copy |
| `CLAUDE.md` | WC-011 | Update docs |
| `.claude/CLAUDE.md` | WC-011 | Update docs |
| `tests/integration/clarification/` | WC-012 | CREATE |

---

## Verification Checklist

After all tasks complete:

- [ ] Agent exists at `installer/core/agents/clarification-questioner.md`
- [ ] Agent copied during installation to `~/.agentecflow/agents/`
- [ ] `/task-work TASK-XXX` invokes clarification at Phase 1.6
- [ ] `/feature-plan "desc"` invokes clarification before review
- [ ] `/feature-plan` [I]mplement invokes clarification for prefs
- [ ] `/task-review TASK-XXX` invokes clarification at start
- [ ] CLAUDE.md documents unified subagent pattern
- [ ] All smoke tests pass
