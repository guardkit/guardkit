# Claude Skills Evaluation for GuardKit and RequireKit

**Date**: December 2025  
**Status**: Analysis Complete  
**Recommendation**: Do NOT adopt Skills for quality gates; consider only for optional advisory content

## Executive Summary

This document evaluates Anthropic's Claude Skills feature for potential adoption in GuardKit and RequireKit repositories. After thorough analysis, **Skills are NOT recommended for quality gates or mandatory workflows** due to their heuristic-based invocation model. Skills may offer limited value for optional reference material but would introduce risk to the deterministic execution model that makes GuardKit's quality gates reliable.

## What Are Claude Skills?

Claude Skills are organized folders of instructions, scripts, and resources that agents can discover and load dynamically to perform better at specific tasks. They were introduced by Anthropic in October 2025.

### Key Characteristics

1. **Progressive Disclosure**: At startup, only skill metadata (name + description) loads into the system prompt. Full content loads only when Claude determines the skill is relevant.

2. **Automatic Triggering**: Unlike explicit commands, Skills are invoked based on Claude's judgment about task relevance.

3. **Filesystem-Based**: Skills are directories containing a `SKILL.md` file with YAML frontmatter and instructions.

4. **Cross-Platform**: Skills work across Claude.ai, Claude Code, Claude Agent SDK, and the Claude API.

### How AgentOS Uses Skills

AgentOS (a competing spec-driven development framework) converts coding standards into Claude Code Skills:

- Standards are not injected explicitly into commands
- Each standard file becomes a separate Skill
- Skills are placed in `.claude/skills/` folder
- Claude applies them intelligently based on current task

**Key AgentOS Quote**: "Unlike Claude Code subagents (which you explicitly trigger with instructions like 'delegate to agent-name') or injected standards (which are specifically referenced), Claude Code Skills cannot be directly invoked."

## The Fundamental Problem for GuardKit

### Skills Are Heuristic-Based

Skills execute based on Claude's judgment:
> "Claude automatically recognizes when to use each Skill based on the current task"

### GuardKit's Quality Gates Are Non-Negotiable

GuardKit's quality gates MUST execute in sequence:

```
Phase 2.5: Architectural Review → MUST run, MUST score ≥60/100
Phase 4.5: Test Enforcement → MUST run, MUST pass 100%
Phase 5.5: Plan Audit → MUST run, MUST have 0 violations
```

These are fundamentally different execution models:

| Pattern | Execution Model | Failure Mode |
|---------|----------------|--------------|
| **Skills** | "Apply when Claude thinks relevant" | Might skip if Claude doesn't see relevance |
| **GuardKit Phases** | "Always execute in this order" | Blocks until gate passes |

### Risk Assessment

If quality gates were converted to Skills:

1. **Phase 2.5 (Architectural Review)**: Claude might decide "this task is simple, I'll skip the architectural review"
2. **Phase 4.5 (Test Enforcement)**: Claude might think "tests passed last time, probably fine"
3. **Phase 5.5 (Plan Audit)**: Claude might skip scope creep detection for "obvious" implementations

**This defeats the entire purpose of GuardKit's quality enforcement.**

## Comparison: Current Architecture vs Skills

| Aspect | Current GuardKit Approach | Skills Approach |
|--------|---------------------------|-----------------|
| **Invocation** | Explicit `/task-work` with numbered phases | Automatic, context-based |
| **Execution Order** | Deterministic, sequential | Non-deterministic |
| **Failure Handling** | Blocks progression, requires resolution | Might not trigger at all |
| **Quality Guarantee** | 100% gate execution | Variable based on Claude's judgment |
| **Human Checkpoints** | Explicit triggers at defined points | No guaranteed triggers |
| **Predictability** | Highly predictable | Unpredictable |

## Where Skills Might Help (Limited Scope)

Skills could potentially add value only for **discretionary, context-dependent knowledge** that isn't a blocking gate:

### Potentially Suitable

1. **Stack Detection Patterns**: When Claude is determining technology stack
2. **Best Practices Library**: Reference material for implementation quality (but gate still runs explicitly)
3. **Optional Documentation**: Style guides, naming conventions

### Not Suitable

1. **Quality Gates**: Any blocking checkpoint
2. **Phase Execution**: Any mandatory workflow step
3. **Validation Rules**: Coverage thresholds, compilation checks
4. **Human Checkpoints**: Complexity triggers, approval gates

## RequireKit Considerations

RequireKit's EARS formalization and BDD generation are also explicit workflows:

```
/gather-requirements → Interactive Q&A (explicit)
/formalize-ears → EARS conversion (explicit)
/generate-bdd → Gherkin generation (explicit)
```

These are user-triggered actions, not ambient behaviors. Skills would be inappropriate here as well.

## What GuardKit Already Does Right

GuardKit's current architecture correctly implements:

1. **Explicit Commands**: `/task-work`, `/task-create`, `/task-complete`
2. **Numbered Phases**: 2 → 2.5 → 2.8 → 3 → 4 → 4.5 → 5 → 5.5
3. **Blocking Gates**: Quality checks that prevent progression
4. **Agent Discovery**: YAML frontmatter with stack, phase, capabilities metadata
5. **Human Checkpoints**: Triggered by complexity ≥7 or other criteria

This is the correct pattern for mandatory quality enforcement.

## AgentOS vs GuardKit: Different Goals

| AgentOS | GuardKit |
|---------|----------|
| Coding standards are advisory | Quality gates are mandatory |
| Improve code quality when applied | Prevent bad code from progressing |
| Flexible application | Deterministic execution |
| "Nice to have" enforcement | "Must have" enforcement |

AgentOS's pattern works for their use case (optional guidance). GuardKit's pattern is correct for its use case (mandatory gates).

## Recommendation

### Do NOT Adopt Skills For:

- ❌ Quality gates (architectural review, test enforcement, plan audit)
- ❌ Phase execution in `/task-work`
- ❌ Human checkpoint triggers
- ❌ Validation thresholds
- ❌ Any mandatory workflow step

### Consider Skills Only For:

- ⚠️ Optional reference material that enhances but doesn't gate
- ⚠️ Documentation that provides context but isn't required
- ⚠️ Stack-specific tips that improve quality but don't block

### Primary Recommendation

**Keep the current explicit phase-based architecture.** The deterministic execution order is a feature, not a limitation. It ensures 100% quality gate execution, which is GuardKit's core value proposition.

## Alternative: Progressive Disclosure

Instead of Skills, consider **progressive disclosure** within the current architecture:

- Split large files into core + extended references
- Load extended content only when needed
- Maintain explicit control over what loads when
- Preserve deterministic execution

See companion document: `progressive-disclosure-analysis.md`

## References

- [Anthropic: Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Docs: Agent Skills Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- [AgentOS Skills Integration](https://buildermethods.com/agent-os/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)

## Conclusion

Claude Skills are a powerful feature for optional, context-aware enhancements. However, they are fundamentally incompatible with GuardKit's mandatory quality gate architecture. The heuristic-based invocation model introduces unacceptable risk for quality enforcement workflows.

**GuardKit's explicit, deterministic phase execution is the correct pattern for mandatory quality gates. Do not compromise this for token efficiency or perceived simplicity.**
