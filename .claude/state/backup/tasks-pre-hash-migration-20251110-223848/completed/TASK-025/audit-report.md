# RequireKit Reference Audit Report

**Generated**: 2025-11-03T13:59:30.903757
**Files Scanned**: 17
**Total Findings**: 75

## Summary by Category

- **Heavy** (must remove/rewrite): 19 findings
- **Light** (needs context check): 49 findings
- **Integration** (add RequireKit notes): 7 findings

---

## Heavy RequireKit References (Priority)

These features are RequireKit-specific and must be removed or heavily rewritten:

### complexity-management-workflow.md

- **Line 53** (RequireKit command reference)
  ```
  > **Note:** For formal requirements management (EARS notation, BDD scenarios, epic hierarchy), see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
  ```

- **Line 53** (EARS notation reference)
  ```
  > **Note:** For formal requirements management (EARS notation, BDD scenarios, epic hierarchy), see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
  ```

- **Line 53** (Epic/feature hierarchy)
  ```
  > **Note:** For formal requirements management (EARS notation, BDD scenarios, epic hierarchy), see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
  ```

### design-first-workflow.md

- **Line 56** (RequireKit command reference)
  ```
  > **Note:** Phase 1 (Requirements Analysis) is part of RequireKit. GuardKit uses task descriptions and acceptance criteria directly. For EARS notation and formal requirements, see [RequireKit](https://github.com/requirekit/require-kit).
  ```

- **Line 56** (EARS notation reference)
  ```
  > **Note:** Phase 1 (Requirements Analysis) is part of RequireKit. GuardKit uses task descriptions and acceptance criteria directly. For EARS notation and formal requirements, see [RequireKit](https://github.com/requirekit/require-kit).
  ```

### iterative-refinement-workflow.md

- **Line 151** (RequireKit command reference)
  ```
  > **Note:** For epic/feature hierarchy and context, see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
  ```

- **Line 151** (Epic/feature hierarchy)
  ```
  > **Note:** For epic/feature hierarchy and context, see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
  ```

- **Line 216** (RequireKit command reference)
  ```
  > **Note:** For formal feature/epic hierarchies and requirements traceability, see [RequireKit](https://github.com/requirekit/require-kit).
  ```

### quality-gates-workflow.md

- **Line 503** (RequireKit command reference)
  ```
  > **Note:** For PM tool synchronization (Jira, Linear, Azure DevOps), see [RequireKit](https://github.com/requirekit/require-kit) which provides automatic issue sync.
  ```

### guardkit-vs-requirekit.md

- **Line 28** (Epic/feature hierarchy)
  ```
  | **Epic/Feature Hierarchy** | Not supported | Full hierarchy | RequireKit for large projects |
  ```

- **Line 108** (Epic/feature hierarchy)
  ```
  - ⚠️ No epic/feature hierarchy
  ```

- **Line 157** (EARS notation reference)
  ```
  /formalize-ears REQ-001  # EARS notation for FDA compliance
  ```

- **Line 159** (Epic/feature hierarchy)
  ```
  # Epic/Feature planning
  ```

- **Line 178** (Epic/feature hierarchy)
  ```
  - ✅ Epic/Feature hierarchy for portfolio management
  ```

- **Line 179** (EARS notation reference)
  ```
  - ✅ Formal requirements (EARS notation)
  ```

- **Line 180** (BDD scenario generation)
  ```
  - ✅ BDD scenario generation
  ```

- **Line 301** (Epic/feature hierarchy)
  ```
  | Epic/Feature hierarchy? | ❌ | ✅ | ✅ |
  ```

- **Line 358** (Epic/feature hierarchy)
  ```
  **A:** Start with GuardKit. Add RequireKit only when you need formal requirements, epic/feature hierarchy, or PM tool integration.
  ```

- **Line 366** (RequireKit command reference)
  ```
  - [RequireKit Documentation](https://github.com/requirekit/require-kit) - Full RequireKit documentation
  ```

---

## Light RequireKit Mentions

These mentions may need context clarification or removal:

### complexity-guide.md

- **Line 102** (Phase 1 general mention): `├── TASK-070.1: Phase 1 - Event store setup (5/10)...`

### design-first-workflow-card.md

- **Line 16** (Phase 1 general mention): `> **Note:** Phase 1 (Requirements Analysis) is part of RequireKit. GuardKit us...`

### complexity-management-workflow.md

- **Line 53** (BDD/Gherkin keyword mention): `> **Note:** For formal requirements management (EARS notation, BDD scenarios, ep...`
- **Line 53** (Formal requirements management): `> **Note:** For formal requirements management (EARS notation, BDD scenarios, ep...`
- **Line 354** (Phase 1 general mention): `├── TASK-040.1: Phase 1 - Foundation (models, interfaces)...`

### design-first-workflow.md

- **Line 56** (Formal requirements management): `> **Note:** Phase 1 (Requirements Analysis) is part of RequireKit. GuardKit us...`
- **Line 56** (Phase 1 general mention): `> **Note:** Phase 1 (Requirements Analysis) is part of RequireKit. GuardKit us...`

### iterative-refinement-workflow.md

- **Line 151** (Epic keyword mention): `> **Note:** For epic/feature hierarchy and context, see [RequireKit](https://git...`
- **Line 216** (Epic keyword mention): `> **Note:** For formal feature/epic hierarchies and requirements traceability, s...`
- **Line 216** (Formal requirements management): `> **Note:** For formal feature/epic hierarchies and requirements traceability, s...`

### markdown-plans-workflow.md

- **Line 497** (Phase 1 general mention): `Commit 2: Implement JWT service (Phase 1)...`

### maui-migration-tasks-summary.md

- **Line 358** (Phase 1 general mention): `**Week 1: Foundation (Phase 1)**...`
- **Line 419** (Phase 1 general mention): `3. **Start Phase 1**: Begin with `TASK-011-create-maui-appshell-template-structu...`

### maui-template-migration-plan.md

- **Line 429** (Phase 1 general mention): `1. **Immediate**: Start Phase 1 (Create global templates)...`

### guardkit-vs-requirekit.md

- **Line 5** (Formal requirements management): `The GuardKit ecosystem offers two complementary tools: **GuardKit** (lightwe...`
- **Line 27** (BDD/Gherkin keyword mention): `| **BDD Scenarios** | Not supported | Automatic generation | RequireKit for beha...`
- **Line 28** (Epic keyword mention): `| **Epic/Feature Hierarchy** | Not supported | Full hierarchy | RequireKit for l...`
- **Line 34** (BDD/Gherkin keyword mention): `| **Documentation Output** | Markdown plans | EARS + BDD + Plans | RequireKit fo...`
- **Line 106** (Formal requirements management): `- ⚠️ No formal requirements (task descriptions only)...`
- **Line 108** (Epic keyword mention): `- ⚠️ No epic/feature hierarchy...`
- **Line 140** (Formal requirements management): `- Formal requirements management needed...`
- **Line 141** (BDD/Gherkin keyword mention): `- Behavior-driven development (BDD)...`
- **Line 142** (Formal requirements management): `- Requirements traceability matrices...`
- **Line 159** (Epic keyword mention): `# Epic/Feature planning...`
- **Line 160** (Epic keyword mention): `/epic-create "Patient Data Management"...`
- **Line 161** (Epic keyword mention): `/feature-create "Secure Patient Records" epic:EPIC-001...`
- **Line 163** (BDD/Gherkin keyword mention): `# Task generation with BDD...`
- **Line 165** (BDD/Gherkin keyword mention): `# → Generates TASK-001, TASK-002, TASK-003 with BDD scenarios...`
- **Line 168** (BDD/Gherkin keyword mention): `/task-work TASK-001 --mode=bdd...`
- **Line 169** (BDD/Gherkin keyword mention): `# → Complete EARS → BDD → Code → Tests traceability...`
- **Line 176** (BDD/Gherkin keyword mention): `- ✅ Complete traceability (EARS → BDD → Code → Tests)...`
- **Line 178** (Epic keyword mention): `- ✅ Epic/Feature hierarchy for portfolio management...`
- **Line 179** (Formal requirements management): `- ✅ Formal requirements (EARS notation)...`
- **Line 186** (BDD/Gherkin keyword mention): `- ⚠️ More ceremony (requirements → BDD → implementation)...`
- **Line 203** (Epic keyword mention): `/epic-create "ACH Payment Processing" requirements:[REQ-001,REQ-002]...`
- **Line 205** (BDD/Gherkin keyword mention): `/task-work TASK-001 --mode=bdd  # Full traceability...`
- **Line 220** (Phase 1 general mention): `**Phase 1 (0-6 months):** GuardKit only...`
- **Line 241** (BDD/Gherkin keyword mention): `- Full EARS → BDD → Code traceability...`
- **Line 275** (BDD/Gherkin keyword mention): `bdd_scenarios: [BDD-001]           # RequireKit BDD scenarios...`
- **Line 286** (BDD/Gherkin keyword mention): `# - BDD-XXX (Gherkin scenarios)...`
- **Line 299** (Formal requirements management): `| Formal requirements needed? | ❌ | ✅ | ✅ |...`
- **Line 301** (Epic keyword mention): `| Epic/Feature hierarchy? | ❌ | ✅ | ✅ |...`
- **Line 304** (BDD/Gherkin keyword mention): `| BDD required? | ❌ | ✅ | ✅ |...`
- **Line 346** (Formal requirements management): `**A:** Yes! GuardKit is standalone. Use task descriptions and acceptance crite...`
- **Line 355** (BDD/Gherkin keyword mention): `**A:** Both have the same core gates (architectural review, test enforcement, co...`
- **Line 355** (Formal requirements management): `**A:** Both have the same core gates (architectural review, test enforcement, co...`
- **Line 358** (Epic keyword mention): `**A:** Start with GuardKit. Add RequireKit only when you need formal requireme...`
- **Line 358** (Formal requirements management): `**A:** Start with GuardKit. Add RequireKit only when you need formal requireme...`
- **Line 360** (Formal requirements management): `### Q: What if I need formal requirements but don't want the overhead?...`

---

## Integration Opportunities

These mentions could benefit from RequireKit integration notes:

### complexity-management-workflow.md

- **Line 53** (Requirements management mention): `> **Note:** For formal requirements management (EARS notation, BDD scenarios, ep...`

### quality-gates-workflow.md

- **Line 503** (PM tool mention (potential integration note)): `> **Note:** For PM tool synchronization (Jira, Linear, Azure DevOps), see [Requi...`

### guardkit-vs-requirekit.md

- **Line 5** (Requirements management mention): `The GuardKit ecosystem offers two complementary tools: **GuardKit** (lightwe...`
- **Line 29** (PM tool mention (potential integration note)): `| **PM Tool Integration** | Manual (GitHub only) | Automatic (Jira, Linear, Azur...`
- **Line 140** (Requirements management mention): `- Formal requirements management needed...`
- **Line 172** (PM tool mention (potential integration note)): `/task-sync TASK-001 --rollup-progress  # Automatic Jira sync...`
- **Line 177** (PM tool mention (potential integration note)): `- ✅ Automatic PM tool sync (Jira, Linear, Azure DevOps)...`

---

## Files by Finding Count (Priority Order)

- **guardkit-vs-requirekit.md**: 50 findings
- **complexity-management-workflow.md**: 7 findings
- **iterative-refinement-workflow.md**: 6 findings
- **design-first-workflow.md**: 4 findings
- **maui-migration-tasks-summary.md**: 2 findings
- **quality-gates-workflow.md**: 2 findings
- **markdown-plans-workflow.md**: 1 findings
- **maui-template-migration-plan.md**: 1 findings
- **complexity-guide.md**: 1 findings
- **design-first-workflow-card.md**: 1 findings

---

## Next Steps

1. **Address Heavy References** (Priority)
   - Remove RequireKit commands
   - Remove EARS notation examples
   - Remove BDD generation workflows
   - Remove epic hierarchy references
   - Remove PM tool integration details

2. **Review Light Mentions**
   - Check context and clarify if needed
   - Remove if not applicable to GuardKit
   - Update phase numbering (Phase 1 = RequireKit)

3. **Add Integration Notes**
   - Add standard RequireKit integration note:
   ```markdown
   > **Note:** For formal requirements management (EARS notation, BDD scenarios, epic hierarchy),
   > see [RequireKit](https://github.com/requirekit/require-kit) which integrates with GuardKit.
   ```

4. **Validate Updates**
   - Ensure command syntax matches specifications
   - Verify all examples work standalone (GuardKit only)
   - Check phase descriptions are accurate
