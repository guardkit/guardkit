---
id: TASK-FRR-PEB-001
title: Pipeline error-bridge recovery
status: in_progress
created: 2026-05-06 00:00:00+00:00
priority: high
task_type: feature
---

# Task: Pipeline error-bridge recovery

## Description

Modify `pipeline_consumer.py` to recover from transient NATS errors by
republishing through the dead-letter bridge. The consumer lives at
`src/forge/adapters/nats/pipeline_consumer.py` but AC text below
references it by basename to keep the prose readable.

## Acceptance Criteria

- [ ] AC-1: `pipeline_consumer.py` publishes a recovery event after a
  transient failure.
- [ ] AC-2: Errors classified as permanent are forwarded to the
  dead-letter bridge unchanged.
- [ ] AC-3: All modified files pass project-configured lint/format
  checks with zero errors.
