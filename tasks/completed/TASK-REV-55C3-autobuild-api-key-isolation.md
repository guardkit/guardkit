---
id: TASK-REV-55C3
title: Investigate AutoBuild API key isolation for VLLM/Qwen3 on Dell Pro Max
status: completed
task_type: review
review_mode: decision
review_depth: standard
created: 2026-02-22T00:00:00Z
updated: 2026-02-22T00:00:00Z
priority: medium
tags: [autobuild, configuration, vllm, api-key, environment]
complexity: 4
review_results:
  mode: decision
  depth: standard
  findings_count: 7
  recommendations_count: 5
  decision: accept
  report_path: docs/reviews/autobuild-api-key-isolation/TASK-REV-55C3-review-report.md
  completed_at: 2026-02-22T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate AutoBuild API key isolation for VLLM/Qwen3 on Dell Pro Max

## Description

Investigate whether the `ANTHROPIC_API_KEY` environment variable (and related configuration) can be scoped exclusively to AutoBuild sessions so that:

1. **AutoBuild sessions** on the Dell Pro Max point to a local **VLLM instance running Qwen3 Next Coder** (via a custom API base URL and key)
2. **Normal Claude Code sessions** (VS Code extension or terminal) continue to use the standard **Anthropic API** with Sonnet/Opus models

The goal is to have environment-level isolation so that running `guardkit autobuild` automatically picks up the VLLM-compatible configuration, while interactive Claude Code usage remains unaffected.

## Review Objectives

- [x] Determine how Claude Code resolves `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` at runtime
- [x] Investigate whether Claude Code supports per-project or per-command environment overrides
- [x] Explore wrapper script / shell alias approaches for AutoBuild invocation
- [x] Assess whether `.env` files, direnv, or similar tools can scope env vars per execution context
- [x] Review the AutoBuild CLI entry point to identify where env vars are consumed
- [x] Check if Claude Code supports config profiles or named environments
- [x] Document the recommended approach with minimal friction

## Key Questions

1. Can `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` be overridden per-invocation without affecting the global shell environment?
2. Does the AutoBuild CLI support `--api-key` or `--base-url` flags?
3. Can a wrapper script (e.g., `autobuild-local.sh`) set env vars inline before invoking AutoBuild?
4. Does VLLM's OpenAI-compatible API work with the Anthropic SDK's expected request/response format, or is an adapter needed?
5. Are there Claude Code settings (`.claude/settings.json` or similar) that allow per-context API configuration?

## Acceptance Criteria

- [x] Clear documentation of how Claude Code resolves API credentials
- [x] At least 2 viable approaches identified and compared
- [x] Recommended approach with step-by-step setup instructions
- [x] Confirmation of VLLM/Qwen3 compatibility with the Anthropic SDK client
- [x] No impact on normal Claude Code sessions verified

## Implementation Notes

Review completed. Full report at: `docs/reviews/autobuild-api-key-isolation/TASK-REV-55C3-review-report.md`

### Key Answers

1. **Per-invocation override**: Yes — shell inline env vars (`ANTHROPIC_BASE_URL=... guardkit autobuild task TASK-XXX`) work perfectly
2. **CLI `--api-key`/`--base-url` flags**: Not currently supported; would require code changes
3. **Wrapper script**: Yes — recommended approach (Approach A)
4. **VLLM compatibility**: VLLM natively supports Anthropic Messages API; no adapter needed
5. **Claude Code settings**: `.claude/settings.local.json` supports `env` field but affects ALL sessions in project

### Recommended Approach

**Approach A: Wrapper script** — creates `autobuild-vllm` command that sets env vars inline before invoking `guardkit autobuild`. Zero codebase changes, surgical isolation, works today.
