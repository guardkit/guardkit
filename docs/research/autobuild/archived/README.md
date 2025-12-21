# AutoBuild Research

This folder contains research into **AutoBuild** - GuardKit's autonomous feature implementation capability using adversarial cooperation (dialectical autocoding).

## Overview

AutoBuild enables GuardKit to automatically implement features after `/feature-plan` generates subtasks, using a coach-player feedback loop that iterates until requirements are met.

## Key Concepts

- **Dialectical Autocoding**: Two-agent feedback loop (player + coach) for autonomous coding
- **Adversarial Cooperation**: Player implements, coach validates - neither can declare success alone
- **Multi-Model Support**: Works with Claude, Devstral 2, DeepSeek, and other LLMs
- **Fresh Context**: Each turn uses new agent instances to prevent context pollution

## Documents in This Folder

### Primary Research

| Document | Description |
|----------|-------------|
| [Adversarial_Cooperation_AutoBuild_Research.md](./Adversarial_Cooperation_AutoBuild_Research.md) | **Main document** - Complete analysis of the adversarial cooperation pattern, implementation architecture, and phased rollout plan |

### Related Research (Moved Here)

These documents were previously in the parent research folder and provide background context:

| Document | Description | Original Location |
|----------|-------------|-------------------|
| [claude_agent_sdk_integration_analysis.md](./claude_agent_sdk_integration_analysis.md) | Analysis of Claude Agents SDK capabilities | `docs/research/` |
| [Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md) | Fast-path implementation using Claude SDK | `docs/research/` |
| [Claude_Agent_SDK_True_End_to_End_Orchestrator.md](./Claude_Agent_SDK_True_End_to_End_Orchestrator.md) | Full automation specification | `docs/research/` |
| [Claude_Agent_SDK_Two_Command_Feature_Workflow.md](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md) | Two-command workflow approach | `docs/research/` |
| [agentecflow_langgraph_mcp_architecture_recommendation.md](./agentecflow_langgraph_mcp_architecture_recommendation.md) | LangGraph architecture recommendations | `docs/research/` |

## Key References

### Block AI Research Paper

The primary inspiration for AutoBuild is the Block AI Research paper "Adversarial Cooperation in Code Synthesis" (December 8, 2025):

- **Repository**: https://github.com/dhanji/g3
- **Key Finding**: Adversarial cooperation achieves 5/5 completeness vs 1-4.5/5 for single-agent approaches
- **Pattern**: Player implements → Coach validates → Iterate until approved

### Multi-Model Options

| Model | SWE-bench | Cost | Notes |
|-------|-----------|------|-------|
| Claude Sonnet 4 | ~50% | $3/$15 per M | Current default |
| Devstral 2 | 72.2% | $0.40/$2.00 | **Free during preview** |
| Devstral Small 2 | 68.0% | $0.10/$0.30 | Runs locally |
| DeepSeek R1 | ~65% | ~$0.14/$0.28 | Open weights |

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Research | ✅ Complete | Pattern analysis, architecture design |
| Phase 1 | 🔲 Not Started | Basic dialectical loop with single model |
| Phase 2 | 🔲 Not Started | Multi-model support (Devstral, DeepSeek) |
| Phase 3 | 🔲 Not Started | Parallel task execution |
| Phase 4 | 🔲 Not Started | Human-in-the-loop refinements |

## Quick Decision Summary

**Why AutoBuild (not Orchestration)?**
- "Orchestration" implies swarm/hive multi-agent systems
- AutoBuild is a bounded two-agent loop, not emergent behavior
- Clearer marketing: "autonomous feature building"

**Why LangGraph (not Claude SDK alone)?**
- Multi-model support (breaks vendor lock-in)
- Cost story ($0 with local Devstral vs $200/mo Claude Max)
- Industry-standard patterns (transferable knowledge)
- Better content opportunities

**Why Adversarial Cooperation (not single agent)?**
- Proven 5/5 completeness vs 1-4.5/5 for single agents
- Prevents premature success declaration
- Fresh context each turn prevents pollution
- Aligns with GuardKit philosophy: implementation ≠ done until validated

---

*Last Updated: December 19, 2025*
