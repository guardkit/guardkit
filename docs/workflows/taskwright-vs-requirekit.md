# Taskwright vs RequireKit: Comparison and Decision Guide

## Overview

The Taskwright ecosystem offers two complementary tools: **Taskwright** (lightweight task workflow) and **RequireKit** (formal requirements management). This guide helps you choose the right tool for your project and understand when to use both together.

**Think of it as a spectrum:**

```
Plain AI Coding ←──────── Taskwright ──────────→ RequireKit
(Cursor, Claude)         (SWEET SPOT)          (Enterprise SDD)

✗ No structure          ✓ Structured workflow    ✓ Complete traceability
✗ No quality gates      ✓ Quality gates         ✓ Comprehensive gates
✗ No verification       ✓ Automated testing     ✓ Multi-level validation
✓ Zero overhead         ✓ Minimal overhead      ✗ Heavy overhead
✓ Fast iteration        ✓ Fast with safety      ✗ Slow iteration
```

## Side-by-Side Comparison

| Feature | Taskwright | RequireKit | Recommendation |
|---------|------------|------------|----------------|
| **Setup Time** | 5 minutes | 2-4 hours | Taskwright for quick start |
| **Per-Task Overhead** | 10-15 minutes | 30-60 minutes | Taskwright for agile teams |
| **EARS Requirements** | Not supported | Required | RequireKit for compliance |
| **BDD Scenarios** | Not supported | Automatic generation | RequireKit for behavior specs |
| **Epic/Feature Hierarchy** | Not supported | Full hierarchy | RequireKit for large projects |
| **PM Tool Integration** | Manual (GitHub only) | Automatic (Jira, Linear, Azure DevOps) | RequireKit for enterprise |
| **Quality Gate Coverage** | 80% (core gates) | 100% (all gates) | Taskwright for most teams |
| **Architectural Review** | Phase 2.5B only | Multi-phase | Taskwright sufficient |
| **Test Enforcement** | Phase 4.5 (3 attempts) | Phase 4.5 + Manual QA | Same in both |
| **Plan Audit** | Phase 5.5 (basic) | Phase 5.5 + Compliance | Taskwright for most |
| **Documentation Output** | Markdown plans | EARS + BDD + Plans | RequireKit for regulation |
| **Agent Orchestration** | Single agent | Multi-agent | RequireKit for complex |
| **MCP Server Required** | No | Yes (optional) | Taskwright for simplicity |
| **Team Size** | 1-5 developers | 5+ developers | Taskwright for small teams |
| **Project Scale** | Individual tasks | Features/Epics hierarchy | Depends on complexity |
| **Compliance Needs** | Low | High (FDA, SOX, etc.) | RequireKit for regulation |
| **Ideal For** | Startups, MVPs, agile | Enterprise, regulated | Match to context |

## When to Use Taskwright

### ✅ Perfect For

**Small to Medium Projects:**
- Individual tasks and small features
- <50 tasks total
- Single product or service

**Agile Development:**
- Fast iteration cycles (1-2 week sprints)
- Frequent releases
- MVP development
- Rapid prototyping

**Small Teams:**
- 1-5 developers
- Single team, co-located or remote
- No cross-functional dependencies
- Direct communication

**Minimal Compliance:**
- No regulatory requirements
- Internal tools
- SaaS products (non-healthcare, non-financial)
- Open source projects

**Quick Wins:**
- Bug fixes and hotfixes
- Feature enhancements
- Refactoring tasks
- Documentation updates

### Example: Startup SaaS Product

**Context:**
- 3 developers
- Building MVP for B2B SaaS
- 2-week sprints
- No compliance requirements

**Workflow:**
```bash
# Sprint planning: Create tasks
/task-create "Add OAuth2 authentication"
/task-create "Implement user dashboard"
/task-create "Add billing integration"

# Development: Use Taskwright workflow
/task-work TASK-001  # Auto-proceeds, quality gates enforced
/task-work TASK-002  # Architectural review, test enforcement
/task-work TASK-003  # Plan audit, scope creep detection

# Sprint review: All tasks completed with quality assurance
```

**Benefits:**
- ✅ Minimal overhead (10-15 min per task)
- ✅ No heavy process (just tasks and descriptions)
- ✅ Full quality gates (architectural review, test enforcement)
- ✅ Fast iteration (hours to days per task)
- ✅ Simple task tracking (markdown files)

**Tradeoffs:**
- ⚠️ No formal requirements (task descriptions only)
- ⚠️ No automatic PM tool sync (manual GitHub integration)
- ⚠️ No epic/feature hierarchy
- ⚠️ No compliance traceability

## When to Use RequireKit

### ✅ Perfect For

**Large Projects:**
- 10+ features
- 3+ epics
- 100+ tasks
- Multiple products or services

**Enterprise Development:**
- Long release cycles (quarterly, annually)
- Stakeholder sign-offs required
- Multi-team coordination
- Cross-functional dependencies

**Large Teams:**
- 5+ developers
- Multiple teams or departments
- Distributed globally
- Complex communication needs

**High Compliance:**
- Regulatory requirements (FDA, SOX, HIPAA)
- Medical devices (IEC 62304)
- Financial services (SOC 2)
- Government contracts

**Complex Requirements:**
- Formal requirements management needed
- Behavior-driven development (BDD)
- Requirements traceability matrices
- Stakeholder approval workflows

### Example: Healthcare Application

**Context:**
- 15 developers across 3 teams
- FDA-regulated medical device
- Quarterly releases with validation
- Strict traceability requirements

**Workflow (RequireKit):**
```bash
# Requirements phase
/gather-requirements "Patient Data Management"
/formalize-ears REQ-001  # EARS notation for FDA compliance

# Epic/Feature planning
/epic-create "Patient Data Management"
/feature-create "Secure Patient Records" epic:EPIC-001

# Task generation with BDD
/feature-generate-tasks FEAT-001
# → Generates TASK-001, TASK-002, TASK-003 with BDD scenarios

# Development with full traceability
/task-work TASK-001 --mode=bdd
# → Complete EARS → BDD → Code → Tests traceability

# PM tool sync
/task-sync TASK-001 --rollup-progress  # Automatic Jira sync
```

**Benefits:**
- ✅ Complete traceability (EARS → BDD → Code → Tests)
- ✅ Automatic PM tool sync (Jira, Linear, Azure DevOps)
- ✅ Epic/Feature hierarchy for portfolio management
- ✅ Formal requirements (EARS notation)
- ✅ BDD scenario generation
- ✅ Compliance-ready documentation

**Tradeoffs:**
- ⚠️ Higher overhead (30-60 min per task)
- ⚠️ Longer setup (2-4 hours initial configuration)
- ⚠️ More ceremony (requirements → BDD → implementation)
- ⚠️ Steeper learning curve

## Hybrid Approach: Use Both

The most effective approach for many teams is to use **both tools** strategically:

### Scenario 1: Most Tasks with Taskwright, Critical Features with RequireKit

**Example: Fintech Startup**
- Core banking features → RequireKit (regulatory compliance)
- UI improvements → Taskwright (fast iteration)
- Bug fixes → Taskwright (quick wins)
- Security features → RequireKit (traceability)

```bash
# Critical feature (RequireKit)
/epic-create "ACH Payment Processing" requirements:[REQ-001,REQ-002]
/feature-generate-tasks FEAT-001
/task-work TASK-001 --mode=bdd  # Full traceability

# UI enhancement (Taskwright)
/task-create "Improve dashboard loading time"
/task-work TASK-050  # Fast, quality-gated

# Bug fix (Taskwright)
/task-create "Fix date picker validation"
/task-work TASK-051  # Quick, tested
```

### Scenario 2: Start with Taskwright, Upgrade to RequireKit Later

**Example: Growing SaaS Company**

**Phase 1 (0-6 months):** Taskwright only
- Fast MVP development
- Minimal process overhead
- Core quality gates

**Phase 2 (6-12 months):** Add RequireKit for new features
- Keep existing Taskwright tasks
- New complex features use RequireKit
- Gradual adoption

**Phase 3 (12+ months):** Full RequireKit for regulated features
- Critical features → RequireKit
- Standard features → Taskwright
- Bug fixes → Taskwright

### Scenario 3: Team-Based Routing

**Example: Enterprise SaaS Company**

**Backend Team (Security/Compliance):**
- Use RequireKit for all features
- Full EARS → BDD → Code traceability
- Regulatory compliance focus

**Frontend Team (UI/UX):**
- Use Taskwright for most features
- Fast iteration on UI improvements
- Quality gates for testing

**DevOps Team (Infrastructure):**
- Use Taskwright for infrastructure tasks
- Simple, tested, documented

## Integration Points

Both tools integrate seamlessly:

### Shared Quality Gates
- Architectural Review (Phase 2.5B)
- Test Enforcement (Phase 4.5)
- Code Review (Phase 5)
- Plan Audit (Phase 5.5)

### Shared Task Format
- Same markdown frontmatter
- Same state machine (backlog → in_progress → in_review → completed)
- Same directory structure (tasks/)

### Cross-References
```yaml
# Taskwright task can reference RequireKit requirements
---
id: TASK-042
title: Implement OAuth2 authentication
requirements: [REQ-001, REQ-002]  # RequireKit requirements
bdd_scenarios: [BDD-001]           # RequireKit BDD scenarios
---
```

### Upgrade Path
```bash
# Convert Taskwright task to RequireKit workflow
/task-convert TASK-042 --to-requirekit

# Generates:
# - REQ-XXX (EARS requirement)
# - BDD-XXX (Gherkin scenarios)
# - Links task to RequireKit artifacts
```

## Decision Matrix

Use this matrix to decide which tool(s) to use:

| Question | Taskwright | RequireKit | Both |
|----------|------------|------------|------|
| Team size <5? | ✅ | ❌ | ⚠️ |
| No compliance needs? | ✅ | ❌ | ⚠️ |
| Fast iteration required? | ✅ | ❌ | ✅ |
| Formal requirements needed? | ❌ | ✅ | ✅ |
| PM tool sync required? | ❌ | ✅ | ✅ |
| Epic/Feature hierarchy? | ❌ | ✅ | ✅ |
| <50 tasks total? | ✅ | ⚠️ | ❌ |
| Regulated industry? | ❌ | ✅ | ✅ |
| BDD required? | ❌ | ✅ | ✅ |

**Legend:**
- ✅ Perfect fit
- ⚠️ Can work, but not ideal
- ❌ Not recommended

## Cost-Benefit Analysis

### Taskwright

**Time Investment:**
- Setup: 5 minutes
- Per task: 10-15 minutes overhead
- Learning curve: 1 hour

**Value Delivered:**
- 80% of quality gates
- Fast iteration
- Minimal ceremony
- Embedded in `/task-work`

**ROI:** High for small teams, agile projects

### RequireKit

**Time Investment:**
- Setup: 2-4 hours
- Per task: 30-60 minutes overhead
- Learning curve: 1-2 days

**Value Delivered:**
- 100% quality gates
- Complete traceability
- PM tool integration
- Compliance-ready

**ROI:** High for regulated industries, large teams

## FAQ

### Q: Can I use Taskwright without RequireKit?
**A:** Yes! Taskwright is standalone. Use task descriptions and acceptance criteria instead of formal requirements.

### Q: Can I use RequireKit without Taskwright?
**A:** No. RequireKit builds on Taskwright's task workflow and quality gates.

### Q: Can I switch from Taskwright to RequireKit mid-project?
**A:** Yes. RequireKit integrates with existing Taskwright tasks. Use `/task-convert` to upgrade tasks.

### Q: Which tool has better quality gates?
**A:** Both have the same core gates (architectural review, test enforcement, code review, plan audit). RequireKit adds compliance-specific gates (requirements traceability, BDD validation).

### Q: Do I need to learn both tools?
**A:** Start with Taskwright. Add RequireKit only when you need formal requirements, epic/feature hierarchy, or PM tool integration.

### Q: What if I need formal requirements but don't want the overhead?
**A:** Consider hybrid approach: Use RequireKit for critical features (security, compliance) and Taskwright for everything else.

## Related Documentation

- [Taskwright Workflow](../guides/taskwright-workflow.md) - Complete Taskwright workflow
- [RequireKit Documentation](https://github.com/requirekit/require-kit) - Full RequireKit documentation
- [Quality Gates Workflow](./quality-gates-workflow.md) - Shared quality gates
- [Complexity Management](./complexity-management-workflow.md) - Task complexity evaluation

---

**Last Updated**: 2025-11-03
**Version**: 1.0.0
**Maintained By**: Taskwright Team
