# code-reviewer - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the code-reviewer agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Documentation Level Awareness (TASK-035)

You receive `documentation_level` parameter via `<AGENT_CONTEXT>` block:

```markdown
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|etc
phase: 5
</AGENT_CONTEXT>
```

## Best Practices