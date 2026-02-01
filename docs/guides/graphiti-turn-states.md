# Turn State Tracking Guide

> **Status**: Placeholder - Full documentation coming in TASK-GDU-006

GuardKit captures turn states during `/feature-build` workflows for cross-turn learning.

## Quick Reference

**What Gets Captured:**
- Player decisions and actions
- Coach feedback and approval status
- Files modified during turn
- Acceptance criteria status
- Blockers encountered
- Progress summary

**Query Turn States:**
```bash
# View all recent turns
guardkit graphiti search "turn FEAT-XXX" --group turn_states

# View specific task turns
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5
```

## Coming Soon

Full documentation will include:
- Turn state schema reference
- Query examples
- Cross-turn learning patterns
- Debugging turn history
- Integration with AutoBuild

**See Also:**
- [AutoBuild Workflow Guide](autobuild-workflow.md)
- [Interactive Knowledge Capture](graphiti-knowledge-capture.md)
- [Job-Specific Context](graphiti-job-context.md)
