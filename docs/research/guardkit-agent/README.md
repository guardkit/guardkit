# GuardKit Agent Research

This folder contains research and specifications for **GuardKit Agent** - GuardKit's autonomous feature implementation capability using adversarial cooperation (dialectical autocoding).

## Two-Phase Approach

### Phase 1a: GuardKit Extension (START HERE)
**Effort**: 1-2 weeks | **Status**: Ready to Start

Extend GuardKit with adversarial Player/Coach pattern using Claude Agents SDK:
- Stay within Claude Code ecosystem
- Leverage existing GuardKit infrastructure
- Validate the adversarial pattern quickly
- **Document**: [Phase1a_GuardKit_Extension_Kickoff.md](./Phase1a_GuardKit_Extension_Kickoff.md)

### Phase 1b/2: Standalone GuardKit Agent (Later)
**Effort**: 3-4+ weeks | **Status**: Specified, waiting for Phase 1a learnings

Build standalone LangGraph/DeepAgents product:
- Replicate GuardKit functionality
- Add Memory MCP, job-specific context
- Multi-model support (break Claude lock-in)
- Build UI on top
- **Documents**: See "Phase 1b/2 Documents" section below

---

## Quick Start (Phase 1a)

```bash
# After implementation, usage will be:
/feature-build TASK-001 --max-turns 5
/feature-build FEAT-001
```

### How It Works

1. **Plan**: `/feature-plan` creates tasks (existing)
2. **Execute**: Player agent implements in isolated worktree
3. **Validate**: Coach agent reviews against requirements
4. **Iterate**: Coach feedback → Player refinement (max N turns)
5. **Merge**: Approved changes merged to main

---

## Documents

### Phase 1a Documents (Current Focus)

| Document | Description |
|----------|-------------|
| [Phase1a_GuardKit_Extension_Kickoff.md](./Phase1a_GuardKit_Extension_Kickoff.md) | **START HERE** - Claude Agent SDK approach |
| [Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md) | SDK technical details |
| [Adversarial_Cooperation_Research.md](./Adversarial_Cooperation_Research.md) | Academic backing (Block AI paper) |

### Phase 1b/2 Documents (Standalone Product)

| Document | Description |
|----------|-------------|
| [DeepAgents_Integration_Analysis.md](./DeepAgents_Integration_Analysis.md) | Why DeepAgents for Phase 1b |
| [Phase1_Kickoff.md](./Phase1_Kickoff.md) | DeepAgents-based kickoff |
| [Implementation_Readiness_Review.md](./Implementation_Readiness_Review.md) | DeepAgents readiness checklist |
| [GuardKit_Agent_Product_Specification.md](./GuardKit_Agent_Product_Specification.md) | Full product spec |
| FEATURE-001 through FEATURE-007 | Detailed feature specs |

### Research & Analysis

| Document | Description |
|----------|-------------|
| [Claude-Flow_Patterns_Research.md](./Claude-Flow_Patterns_Research.md) | Coordination patterns from claude-flow |
| [Devstral_2_Evaluation.md](./Devstral_2_Evaluation.md) | Multi-model evaluation |

---

## Key Concepts

- **Adversarial Cooperation**: Player implements, Coach validates - neither can declare success alone
- **Fresh Context**: Each turn uses new agent sessions to prevent context pollution
- **Dialectical Autocoding**: Two-agent feedback loop proven to achieve higher completion rates

---

## Technology Comparison

| Aspect | Phase 1a | Phase 1b/2 |
|--------|----------|------------|
| Framework | Claude Agent SDK | LangGraph + DeepAgents |
| Infrastructure | GuardKit (existing) | Build from scratch |
| Vendor lock-in | Claude only | Multi-model |
| Memory | Fresh each turn | Memory MCP |
| Effort | 1-2 weeks | 3-4+ weeks |
| Purpose | Validate pattern | Full product |

---

## CLI Naming

| Component | Name |
|-----------|------|
| Package | `guardkit-agent` |
| Full command | `guardkit-agent` |
| Short alias | `gka` |
| Config directory | `.gka/` |
| Config file | `gka.toml` |

---

## Success Metrics

| Metric | Phase 1a Target | Phase 1b Target |
|--------|-----------------|-----------------|
| Task completion rate | ≥50% | ≥70% |
| Average turns | ≤5 | ≤4 |
| Time to prototype | ≤2 weeks | ≤4 weeks |

---

## References

- [Block AI Adversarial Cooperation Paper](https://github.com/dhanji/g3) - Academic research
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk) - Programmatic Claude Code
- [DeepAgents](https://github.com/langchain-ai/deepagents) - 5.8k ⭐ LangChain agent harness
- [LangGraph](https://langchain-ai.github.io/langgraph/) - State management

---

*Last Updated: December 22, 2025 - Renamed from AutoBuild to GuardKit Agent*
