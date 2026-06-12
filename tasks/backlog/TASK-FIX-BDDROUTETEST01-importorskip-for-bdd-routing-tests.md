---
id: TASK-FIX-BDDROUTETEST01
title: test_bdd_multi_stack_routing.py must importorskip guardkitfactory (collection error in factory-less envs)
task_type: feature
status: backlog
created: 2026-06-12T19:50:00Z
priority: medium
tags: [tests, guardkitfactory, seam, portability]
complexity: 1
---

# Task: importorskip guard for the BDD routing tests

## Problem (observed 2026-06-12)

`tests/unit/orchestrator/quality_gates/test_bdd_multi_stack_routing.py`
(merged with TASK-BDDW-002) imports `guardkitfactory.bdd` at module level
with no guard:

```python
from guardkit.orchestrator.quality_gates... # fine
from guardkitfactory.bdd import StackProfile, discover          # unguarded
from guardkitfactory.bdd.plugins import CucumberJSPlugin, ...   # unguarded
```

In any environment without guardkitfactory installed — including autobuild
**worktree venvs** (observed in the FEAT-C332 worktree: pytest collection
ERROR, `Interrupted: 1 error during collection`, which aborts the entire
`tests/unit/orchestrator/quality_gates/` run) and a plain
`pip install guardkit-py[dev]` — the file breaks collection rather than
skipping. Every other factory-dependent test in the repo uses the
`pytest.importorskip("guardkitfactory...")` + `@pytest.mark.seam` pattern
(e.g. `tests/orchestrator/harness/test_xrepo_contract_seam.py`,
`tests/orchestrator/test_wiring_seam_real_factory.py`).

## Fix

Add at module top, before the factory imports:

```python
import pytest

pytest.importorskip("guardkitfactory.bdd")
```

and mark the module `pytestmark = pytest.mark.seam` for consistency with
the other cross-repo seam tests.

## Acceptance criteria

- [ ] AC-001: with guardkitfactory absent, the module SKIPS cleanly (no
      collection error; sibling tests in the directory still run).
- [ ] AC-002: with guardkitfactory installed, all 11 routing tests still pass.

## Evidence

- Collection error reproduced in the FEAT-C332 worktree venv (pre
  guardkitfactory install), 2026-06-12.
- Pattern prior art: `.claude/rules/harness-cancellation-contract.md`
  (seam-test section); `tests/orchestrator/harness/test_xrepo_contract_seam.py`.
