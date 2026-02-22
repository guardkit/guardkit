---
id: TASK-FS-001
title: "Create /feature-spec slash command definition"
status: backlog
task_type: feature
parent_review: TASK-REV-F445
feature_id: FEAT-FS01
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T12:00:00Z
priority: high
tags: [feature-spec, slash-command, prompt-engineering, bdd, gherkin, methodology]
complexity: 6
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create /feature-spec slash command definition

## Description

Create the `/feature-spec` slash command markdown file that encodes the 6-phase Propose-Review specification methodology. This is the most important file in the entire feature -- the prompt methodology IS the product.

**This is a prompt engineering task, not a code task.** The output is a markdown file that Claude Code interprets as a command definition.

## Files to Create

1. `.claude/commands/feature-spec.md` (project-local, for dogfooding inside GuardKit repo)
2. `installer/core/commands/feature-spec.md` (identical content, for global distribution via install.sh)

## Files NOT to Touch

- Any existing command files (especially `feature-plan.md`, `system-plan.md`)
- Any Python source files

## Implementation Notes

### Study These First (Read-Only Reference)

- `installer/core/commands/feature-plan.md` -- format conventions, structure
- `.claude/commands/generate-bdd.md` -- the command being superseded (learn what NOT to do)

### Key Design Decisions to Encode

| Decision | What It Means for the Command |
|----------|-------------------------------|
| D1 (Gherkin format) | Generate Given/When/Then scenarios, not prose |
| D5 (Unstructured input) | Accept any text -- pasted, file ref, rough notes |
| D6 (Propose-review) | AI proposes grouped scenarios, human curates |
| D9 (Assumptions manifest) | Track every inference with confidence levels |
| D10 (Domain language) | "upload should succeed" not "return 201" |
| D11 (Additive only) | No changes to existing workflows |

### The 6-Phase Cycle Must Be Explicit

1. **Context Gathering** -- AI reads codebase, Graphiti, existing `.feature` files (no human interaction)
2. **Initial Proposal** -- AI generates complete Gherkin set grouped by Spec by Example categories
3. **Human Curation** -- Accept/reject/modify/add/defer per group (fast path: accept entire groups)
4. **Edge Case Expansion** -- AI generates security, concurrency, failure recovery scenarios
5. **Assumption Resolution** -- AI proposes defaults with confidence levels for deferred items
6. **Output Generation** -- Write `.feature`, `_assumptions.yaml`, `_summary.md`

### Specification by Example Categories

- `@key-example` -- Core happy path behaviour
- `@boundary` -- Values at exact boundaries (0, 1, max, max+1)
- `@negative` -- Invalid input, unauthorised access
- `@edge-case` -- Unusual situations, concurrency, failure recovery
- `@smoke` -- Minimal set Coach must verify (cross-cutting)
- `@regression` -- Protecting against previously-observed failures (cross-cutting)

### Learnings from /generate-bdd (Being Retired)

- Do NOT include implementation hints in Gherkin comments (e.g., `# Implementation: tests/e2e/auth.spec.ts::testLogin`)
- Do NOT skip interactive review -- the propose-review cycle is the key improvement
- DO use `Background:` sections for shared context
- DO use `Scenario Outline` with `Examples` tables for parameterised cases

### Must Include

- 2-3 worked examples showing: (a) input -> proposal -> curation -> output, (b) assumption resolution flow, (c) edge case expansion
- Contrasting examples of good vs bad scenarios (concrete vs abstract, domain vs implementation language)
- Stack detection instructions (priority order from Section 5.2 of the feature spec)
- Instruction to check for existing `.feature` files from `/generate-bdd`
- Output file naming convention: `features/{kebab-case-name}/`

### YAML Frontmatter

Include frontmatter with `name`, `description`, `arguments`, `flags` fields. This is a new convention for this command -- existing commands don't use frontmatter, but it makes the command self-documenting.

## Acceptance Criteria

- [ ] File exists: `.claude/commands/feature-spec.md`
- [ ] File exists: `installer/core/commands/feature-spec.md` (identical content)
- [ ] File contains YAML frontmatter with: `name`, `description`, `arguments`, `flags`
- [ ] File defines the Propose-Review methodology with all 6 phases
- [ ] File includes Specification by Example categories: `@key-example`, `@boundary`, `@negative`, `@edge-case`
- [ ] File includes `@smoke` and `@regression` cross-cutting tags
- [ ] File instructs AI to generate `Background:` sections where applicable
- [ ] File instructs AI to use `Scenario Outline` with `Examples` tables for parameterised cases
- [ ] File includes propose-review interaction pattern (accept/reject/modify/add/defer per group)
- [ ] File includes edge case expansion phase
- [ ] File includes assumption resolution with confidence levels and "propose default" pattern
- [ ] File includes instructions to use domain language (not implementation language)
- [ ] File includes stack-agnostic codebase context reading instructions
- [ ] File includes instruction to check for existing `.feature` files
- [ ] File includes 2-3 worked examples
- [ ] File specifies output file naming convention and structure
- [ ] File size > 5000 bytes
- [ ] Both files are identical (`filecmp.cmp()`)

## Coach Validation Commands

```bash
python -c "
import yaml
with open('.claude/commands/feature-spec.md') as f:
    content = f.read()
    fm = content.split('---')[1]
    data = yaml.safe_load(fm)
    assert 'name' in data, 'Missing name'
    assert 'description' in data, 'Missing description'
    print('Frontmatter OK')
"
python -c "
import os
size = os.path.getsize('.claude/commands/feature-spec.md')
assert size > 5000, f'Command definition too short ({size} bytes)'
print(f'Size OK: {size} bytes')
"
python -c "
content = open('.claude/commands/feature-spec.md').read()
required = ['Propose', 'Review', 'Boundary', 'Assumption', 'domain language', '@smoke', 'Background']
for term in required:
    assert term.lower() in content.lower(), f'Missing methodology section: {term}'
print('Methodology sections OK')
"
python -c "
import filecmp
assert filecmp.cmp('.claude/commands/feature-spec.md', 'installer/core/commands/feature-spec.md'), 'Files differ'
print('Installer copy matches')
"
```

## Player Constraints

- Do not modify any existing command files
- Study `installer/core/commands/feature-plan.md` for conventions but do not change it
- Study `.claude/commands/generate-bdd.md` to understand what to improve upon but do not modify it
