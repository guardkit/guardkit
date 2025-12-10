---
id: TASK-047
title: Implement /template-create command orchestrator
status: backlog
created: 2025-11-01T16:12:00Z
priority: high
complexity: 6
estimated_hours: 6
tags: [template-create, orchestration, cli]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037, TASK-038, TASK-039, TASK-042, TASK-043, TASK-045, TASK-046]
blocks: []
---

# TASK-047: Implement /template-create Command Orchestrator

## Objective

Integrate all pattern extraction components into cohesive `/template-create` command:
- Orchestrate 8-phase workflow
- Implement CLI interface
- Add interactive mode
- Create final template package
- Handle errors gracefully

## Acceptance Criteria

- [ ] Command executable: `/template-create <name>`
- [ ] Runs all 8 phases in sequence
- [ ] Supports --scan-depth (quick|full)
- [ ] Supports --interactive mode
- [ ] Supports --scan-paths option
- [ ] Supports --discover-agents flag
- [ ] Creates template in installer/local/templates/
- [ ] Generates .tar.gz package
- [ ] Shows progress indicator
- [ ] Handles errors gracefully
- [ ] Integration tests passing

## Implementation

```python
# installer/core/commands/template-create.py

class TemplateCreateCommand:
    def execute(self, template_name, options):
        print("Phase 1: Detecting technology stack...")
        stack_result = detect_stack(project_path)

        print("Phase 2: Analyzing architecture...")
        arch_result = analyze_architecture(project_path, stack_result)

        print("Phase 3: Extracting code patterns...")
        patterns = extract_patterns(project_path, stack_result, arch_result)

        if options.discover_agents:
            print("Phase 4: Discovering agents...")
            agents = discover_agents(stack_result, arch_result)

            print("Phase 5: Selecting agents...")
            selected = select_agents_interactive(agents)

        print("Phase 6: Generating template...")
        generate_template(template_name, stack_result, arch_result, patterns, selected)

        print("Phase 7: Validating template...")
        validate_template(template_path)

        print("Phase 8: Packaging template...")
        package_template(template_path)

        print(f"✅ Template created: {template_name}")
```

**Estimated Time**: 6 hours | **Complexity**: 6/10 | **Priority**: HIGH
