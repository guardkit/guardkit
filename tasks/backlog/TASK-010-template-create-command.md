---
id: TASK-010
title: /template-create Command Orchestrator
status: backlog
created: 2025-11-01T20:50:00Z
priority: high
complexity: 5
estimated_hours: 6
tags: [command, orchestration]
epic: EPIC-001
feature: commands
dependencies: [TASK-001, TASK-002, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009]
blocks: []
---

# TASK-010: /template-create Command Orchestrator

## Objective

Orchestrate the complete /template-create flow:
1. Q&A session (TASK-001)
2. AI analysis (TASK-002)
3. Template generation (TASK-005-008)
4. Agent recommendation (TASK-009)
5. Save template

## Implementation

Much simpler than algorithmic approach - just orchestrate AI-powered components.

```python
def template_create(project_root: Path):
    # Q&A
    qa = TemplateCreateQASession()
    answers = qa.run()
    
    # AI Analysis
    analyzer = AICodebaseAnalyzer(qa_context=answers)
    analysis = analyzer.analyze(answers.codebase_path)
    
    # Generate template components
    manifest = ManifestGenerator().from_analysis(analysis)
    settings = SettingsGenerator().from_analysis(analysis)
    claude_md = ClaudeMdGenerator().from_analysis(analysis)
    templates = TemplateGenerator().from_examples(analysis.example_files)
    agents = AgentRecommender().recommend(analysis)
    
    # Save template
    save_template(manifest, settings, claude_md, templates, agents)
```

**Estimated Time**: 6 hours | **Complexity**: 5/10 | **Priority**: HIGH
