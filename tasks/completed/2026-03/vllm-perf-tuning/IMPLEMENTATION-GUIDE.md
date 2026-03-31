# Implementation Guide: vLLM Performance Tuning (FEAT-VPT1)

**Parent Review**: TASK-REV-5E93
**Feature**: vLLM Performance Tuning for Dell ProMax GB10
**Total Tasks**: 2 (both complexity 1)

## Problem Statement

FEAT-1637 autobuild run profiling revealed:
1. `max_parallel=2` causes 4.3x throughput penalty (87s/turn vs 20s/turn) on single-GPU
2. `sdk_max_turns=50` is too restrictive for iterative tasks
3. `timeout_multiplier=4.0` provides excessive headroom
4. Embedding server over-reserves GPU memory by 70x

## Execution Strategy

### Wave 1: All Tasks (Parallel — No File Conflicts)

| Task | Description | Mode | Files |
|------|-------------|------|-------|
| TASK-VPT-001 | Tune local backend defaults | direct | `autobuild.py`, `agent_invoker.py`, tests |
| TASK-VPT-002 | Reduce embedding GPU | direct | `scripts/vllm-embed.sh` |

**No file conflicts**: VPT-001 modifies Python source, VPT-002 modifies a shell script.

## Architecture Constraints

**DO NOT MODIFY** the following:
- Auto-detection logic structure (only change the numeric values)
- Environment variable override mechanisms (GUARDKIT_MAX_PARALLEL_TASKS, GUARDKIT_SDK_MAX_TURNS, GUARDKIT_TIMEOUT_MULTIPLIER)
- CLI flag handling for `--max-parallel`
- Anthropic API behavior (all changes gated on local backend detection)

## Testing Strategy

- **TASK-VPT-001**: Update existing unit tests for new default values
- **TASK-VPT-002**: Manual verification on GB10 (infrastructure script, no automated test)

## Quick Reference

| Task ID | Priority | Effort | Key File | Key Change |
|---------|----------|--------|----------|------------|
| TASK-VPT-001 | High | Trivial | `autobuild.py:715`, `agent_invoker.py:155,764` | 3 numeric values |
| TASK-VPT-002 | Low | Trivial | `scripts/vllm-embed.sh` | 1 numeric value |
