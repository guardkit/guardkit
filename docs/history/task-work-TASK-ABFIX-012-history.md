# /task-work — TASK-ABFIX-012 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /task-work TASK-ABFIX-012 — 2026-06-24T22:36:32Z

### Prompt

```
/task-work TASK-ABFIX-012
```

### Assistant response

I'll start by reading the task file to understand what TASK-ABFIX-012 requires.

This is a complex (complexity-7) fix in the Coach validation logic — exactly the kind of subtle false-green/false-red territory the entire `.claude/rules/` corpus warns about. Getting it wrong re-introduces a regression. I need to deeply understand the actual code before touching anything.

Let me read the key code surfaces in parallel.

Now the core file. Let me read the cited regions of `coach_validator.py` in parallel — the classifier, the infra patterns, the classifier call site, and the parallel amnesty.

Let me read the classifier itself, its call site, and the parallel amnesty region in parallel.

The line numbers in the task have drifted. Let me locate the actual symbols precisely with grep, in parallel.

Now let me read the actual classifier definition, the `IndependentTestResult` dataclass, and the `signal_absent` decision points in `run_independent_tests`.

I now understand the classifier. Two critical things to nail down before designing: (1) there appear to be **two** decision paths (`validate()` and a primary `gather_evidence` path), and (2) how the ABFIX-010 `signal_absent`/`None` channel actually routes. Let me scope these precisely.

Both paths resolve `task_type`/`profile`, but `_classify_test_failure` is only called in `validate()` (line 2112). I need to understand how the **primary** `gather_evidence` path handles test failures and the absent signal. Let me read it.

`gather_evidence` builds an evidence bundle but does **not** classify — classification must happen in its consumer. The pivotal question is which path is live in production and where the test-failure classification + absent-routing happens for it. This determines where I edit. Let me trace the callers.

The live path is `gather_evidence` → `CoachEvidenceBundle` → consumed in `agent_invoker.py` by deterministic guards + the LLM Coach. The classifier (`_classify_test_failure`) is **not** applied in this path. I must understand the deterministic guards that gate on `independent_tests` before framing the work. Let me read the guard region and the bundle override.

I now have a deep architectural picture. This is a genuinely cross-module, safety-critical change:

- **Live path** is `gather_evidence` → `CoachEvidenceBundle` → deterministic guards in `agent_invoker` (`_reconcile_absent_independent_test_signal`, `_apply_runtime_parity_guard`) + LLM Coach. The `_classify_test_failure` / parallel-amnesty logic the task cites lives in the **legacy** `validate()` path, which is **not** the live decision path.
- A genuine independent CODE failure (`tests_passed=False, signal_absent=False`) currently has **no deterministic blocking guard** in the live path — it relies on the LLM Coach, which is exactly what false-approved FMDR-004.

Given ultracode and the complexity, I'll run a comprehensive parallel **Understand+Design** workflow to map the remaining unknowns exactly and adversarially check the design against the rule corpus before I touch code. Let me update my todos and launch it.

Now the comprehensive Understand+Design workflow — parallel deep-readers mapping exact edit sites, then an adversarial synthesis that cross-checks the design against the rule corpus.

The parse error is from a stray character in a long template-literal prompt. Let me write the workflow to a file cleanly (easier to iterate) and run it via `scriptPath`.

Workflow is running in the background (5 parallel readers + adversarial design synthesis). While it works, let me handle the task state transition that the workflow doesn't touch — moving TASK-ABFIX-012 to `in_progress` and updating its frontmatter.
