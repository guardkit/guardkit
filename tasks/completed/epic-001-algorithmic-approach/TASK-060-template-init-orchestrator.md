---
id: TASK-060
title: Implement /template-init command orchestrator
status: backlog
created: 2025-11-01T16:26:00Z
priority: medium
complexity: 6
estimated_hours: 7
tags: [template-init, orchestration, cli]
epic: EPIC-001
feature: template-init
dependencies: [TASK-042, TASK-043, TASK-044, TASK-045, TASK-046, TASK-053, TASK-054, TASK-055, TASK-056, TASK-057, TASK-058, TASK-059]
blocks: []
---

# TASK-060: Implement /template-init Command Orchestrator

## Objective

Integrate all Q&A sections into cohesive `/template-init` command:
- Orchestrate 9-section Q&A flow
- Implement CLI interface
- Generate template from answers
- Support flags (--technology, --quick, --from)
- Create final template package

## Acceptance Criteria

- [ ] Command executable: `/template-init`
- [ ] Runs all 9 sections in sequence
- [ ] Supports --technology <tech> flag
- [ ] Supports --quick mode (defaults)
- [ ] Supports --from <template> flag
- [ ] Generates template from Q&A answers
- [ ] Uses TASK-042, 043, 044 generators
- [ ] Validates template (TASK-046)
- [ ] Creates package
- [ ] Integration tests passing

## Implementation

```python
# installer/global/commands/template-init.py

class TemplateInitCommand:
    def execute(self, options):
        flow = QAFlowManager(template_name)

        if options.from_template:
            # Start from existing template
            pass

        # Run Q&A flow
        session = flow.start_session()

        while True:
            question = flow.next_question()
            if not question:
                break

            answer = prompt_user(question)
            flow.answer_question(answer)

        # Generate template from answers
        generate_template_from_answers(session.answers)

        print(f"✅ Template created: {template_name}")
```

**Estimated Time**: 7 hours | **Complexity**: 6/10 | **Priority**: MEDIUM
