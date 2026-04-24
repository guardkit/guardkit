---
id: TASK-FIX-7A01
title: Pin claude-agent-sdk to a compatibility band and log version at AutoBuild startup
status: backlog
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T12:55:00Z
priority: high
tags: [autobuild, sdk, claude-agent-sdk, version-pinning, diagnostics]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-w1-1
complexity: 3
depends_on: []
---

# Task: Pin claude-agent-sdk + log version at startup

## Description

Direct remediation for **Run 2** of FEAT-FORGE-002 (review TASK-REV-E4F5,
finding F1). The GB10 host's installed `claude-agent-sdk` cannot parse the
`rate_limit_event` message the API now streams. Root cause: three dependency
declarations pin only `claude-agent-sdk>=0.1.0` (no upper bound), and
`installer/scripts/install.sh` runs `pip install -e .[autobuild]` **without**
`--upgrade` — so re-running install.sh on a host that already has a stale
SDK leaves that stale SDK in place.

Audit trail: [docs/research/player-agent-sdk-audit-v0.1.36.md](../../docs/research/player-agent-sdk-audit-v0.1.36.md)
last froze the SDK contract against v0.1.36 (2026-02-13). The compatibility
floor for `rate_limit_event` is likely the first release after that.

## Acceptance Criteria

- [ ] `pyproject.toml` `[autobuild]` extra pins `claude-agent-sdk` to a band
      whose **lower bound** includes `rate_limit_event` parsing (verify against
      upstream release notes; if unreleased, file upstream issue per TASK-DOC-7A06
      and pin to the next release candidate the maintainer recommends).
- [ ] Same band applied in `pyproject.toml` `[all]` extra and `requirements.txt`.
- [ ] `installer/scripts/install.sh` either adds `--upgrade` to both the primary
      and `--user` fallback pip invocations, or gains a `--upgrade` flag that
      passes through. Default behavior should upgrade on re-runs; document the
      change in the script header.
- [ ] `AutoBuildOrchestrator.__init__` (or the nearest startup log site) emits
      one INFO-level log line with the resolved SDK version:
      `importlib.metadata.version("claude-agent-sdk")` — wrapped in
      try/except to tolerate missing-metadata environments.
- [ ] Unit test: a test that parses the startup log produced by the orchestrator
      on a known-good environment finds a line matching
      `claude-agent-sdk version: <semver>`.
- [ ] On GB10, a fresh `./installer/scripts/install.sh` (or documented equivalent)
      lifts the SDK to a version that parses `rate_limit_event` — verified by
      re-running FEAT-FORGE-002 Wave 1 to turn 1 completion (tracked as a
      manual verification step; not part of this task's automated gates).

## Files

- `pyproject.toml` (lines ~43, ~62)
- `requirements.txt` (line ~14)
- `installer/scripts/install.sh` (lines ~460–516)
- `guardkit/orchestrator/autobuild.py` (AutoBuildOrchestrator init site — add version log)
- `tests/test_autobuild_startup_logging.py` (new) OR extend nearest existing
  orchestrator test module.

## Implementation Notes

- Upper bound should be the next minor that upstream has historically shipped
  breaking-change cycles in (likely `<0.2`). Validate by reading recent
  `claude-agent-sdk` CHANGELOG / release notes before pinning.
- The version-log line should be printable **even if the SDK import fails** —
  fall back to logging "SDK not importable: {error}" so the single log line
  is always emitted.
- Don't introduce backwards-compatibility shims for the old unbounded pin —
  the new band is the new contract.

## Notes

- Cross-link: finding F1 + recommendation R1 in `.claude/reviews/TASK-REV-E4F5-review-report.md`
- Namespace-hygiene rule not triggered by this change (imports unchanged).
- If upstream `claude-agent-sdk` has not yet shipped `rate_limit_event` parsing,
  coordinate with TASK-DOC-7A06 (upstream-issue filing) before pinning a floor
  that doesn't exist yet.
