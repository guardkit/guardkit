---
id: TASK-SHA-002
title: Create shared-agents repository and migrate verified agents
status: backlog
created: 2025-11-28T21:00:00Z
updated: 2025-11-28T21:00:00Z
priority: high
tags: [shared-agents, repository, lean]
complexity: 3
estimated_effort: 2h
depends_on: [TASK-SHA-001]
blocks: [TASK-SHA-003, TASK-SHA-004]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Create Shared Agents Repository

## Context

Create `guardkit/shared-agents` repository and migrate the verified agents (from TASK-SHA-001) to it. Keep it simple - just the essentials.

## Acceptance Criteria

- [ ] GitHub repository created: `https://github.com/guardkit/shared-agents`
- [ ] Verified agents copied to `agents/` directory
- [ ] Simple `manifest.json` listing agent files
- [ ] Basic README with usage instructions
- [ ] MIT LICENSE (same as TaskWright/RequireKit)
- [ ] v1.0.0 release created with tarball

## Implementation

### 1. Create Repository

```bash
# Using GitHub CLI (or create via web UI)
gh repo create guardkit/shared-agents \
  --public \
  --description "Universal AI agents shared between TaskWright and RequireKit"

# Clone it
git clone https://github.com/guardkit/shared-agents.git
cd shared-agents
```

### 2. Copy Verified Agents

```bash
# Create agents directory
mkdir agents

# Copy verified agents (from TASK-SHA-001 list)
# Example (replace with actual verified list):
cp ../guardkit/installer/global/agents/code-reviewer.md agents/
cp ../guardkit/installer/global/agents/test-orchestrator.md agents/
# ... copy others from verified list
```

### 3. Create manifest.json

```json
{
  "schema_version": "1.0",
  "version": "1.0.0",
  "agents": [
    "agents/code-reviewer.md",
    "agents/test-orchestrator.md"
  ]
}
```

### 4. Create README.md

```markdown
# Shared Agents

Universal AI agents shared between TaskWright and RequireKit.

## What is this?

This repository contains agent definitions that are used by both:
- [TaskWright](https://github.com/guardkit/guardkit)
- [RequireKit](https://github.com/requirekit/require-kit)

Instead of duplicating agents in both repos, we maintain them here.

## Installation

Agents are automatically installed when you run TaskWright or RequireKit installers. No manual installation needed.

## Updating

Tools use version pinning. To update:
1. Change `installer/shared-agents-version.txt` to desired version
2. Re-run installer

## Agents Included

See [manifest.json](manifest.json) for complete list.

## License

MIT License - Same as TaskWright and RequireKit
```

### 5. Add LICENSE

```
MIT License

Copyright (c) 2025 TaskWright

Permission is hereby granted, free of charge...
[Standard MIT license text]
```

### 6. Create Initial Release

```bash
# Commit everything
git add .
git commit -m "Initial release - shared agents v1.0.0"
git push origin main

# Create tarball
tar -czf shared-agents.tar.gz agents/ manifest.json

# Create GitHub release
gh release create v1.0.0 \
  shared-agents.tar.gz \
  --title "v1.0.0 - Initial Release" \
  --notes "First release of shared agents"

# Cleanup
rm shared-agents.tar.gz
```

## Test Requirements

- [ ] Repository accessible on GitHub
- [ ] All verified agents present
- [ ] manifest.json valid JSON
- [ ] v1.0.0 release downloadable
- [ ] Tarball extracts correctly

## Estimated Effort

**2 hours**
- Repository setup: 30 minutes
- Copy agents: 30 minutes
- Documentation: 30 minutes
- Release: 30 minutes

## Success Criteria

- [ ] Repository created and public
- [ ] All verified agents migrated
- [ ] v1.0.0 release published
- [ ] Tarball downloads and extracts correctly
- [ ] manifest.json lists all agents

## Notes

**Keep it simple**: We don't need elaborate CI/CD, multiple workflows, or complex documentation. Just the basics to get started. We can enhance later if needed.

**What we're NOT doing** (intentionally):
- ❌ Checksums (GitHub is reliable)
- ❌ Elaborate CI/CD workflows (simple release is enough)
- ❌ Extensive documentation (README covers basics)
- ❌ Fallback agents (handle edge cases if they occur)
