---
id: TASK-SHA-P1-001
title: Create shared-agents repository structure
status: backlog
created: 2025-11-28T20:30:00Z
updated: 2025-11-28T20:30:00Z
priority: high
tags: [shared-agents, repository, phase-1, setup]
complexity: 2
estimated_effort: 1h
phase: "Phase 1: Create Shared Agents Repository"
depends_on: [TASK-SHA-000, TASK-SHA-001, TASK-SHA-002, TASK-SHA-003, TASK-SHA-004]
blocks: [TASK-SHA-P1-002, TASK-SHA-P1-003, TASK-SHA-P1-004]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Create Shared Agents Repository Structure

## Context

**Phase**: Phase 1 - Create Shared Agents Repository
**Goal**: Initialize the `guardkit/shared-agents` repository with proper directory structure and documentation.

## Description

Create a new GitHub repository for shared agents with the proper directory structure, licensing, and documentation. This will serve as the single source of truth for universal agents shared between TaskWright and RequireKit.

## Acceptance Criteria

- [ ] GitHub repository created: `guardkit/shared-agents`
- [ ] Directory structure created:
  ```
  shared-agents/
  ├── agents/                 # Agent markdown files
  ├── .github/
  │   └── workflows/          # CI/CD workflows
  ├── docs/                   # Documentation
  ├── README.md               # Repository overview
  ├── CHANGELOG.md            # Version history
  ├── LICENSE                 # License file
  └── .gitignore              # Git ignore rules
  ```
- [ ] README.md documents purpose and usage
- [ ] LICENSE file matches TaskWright/RequireKit (same license)
- [ ] .gitignore configured for markdown and temp files
- [ ] Initial commit pushed to main branch

## Implementation Approach

### 1. Create GitHub Repository

```bash
# Using GitHub CLI
gh repo create guardkit/shared-agents \
  --public \
  --description "Universal AI agents shared between TaskWright and RequireKit" \
  --homepage "https://github.com/guardkit"

# Or create via GitHub web UI:
# https://github.com/organizations/guardkit/repositories/new
```

### 2. Clone and Initialize

```bash
# Clone repository
git clone https://github.com/guardkit/shared-agents.git
cd shared-agents

# Create directory structure
mkdir -p agents
mkdir -p .github/workflows
mkdir -p docs

# Create placeholder files
touch agents/.gitkeep
touch .github/workflows/.gitkeep
touch docs/.gitkeep
```

### 3. Create README.md

```markdown
# Shared Agents

Universal AI agents shared between [TaskWright](https://github.com/guardkit/guardkit) and [RequireKit](https://github.com/requirekit/require-kit).

## Overview

This repository provides a single source of truth for AI agents that are used by multiple tools in the TaskWright ecosystem. By maintaining agents in one location, we ensure consistency, reduce duplication, and simplify maintenance.

## Agents

The following universal agents are provided:

- **code-reviewer** - Quality standards enforcement
- **test-orchestrator** - Test execution coordination
- **architectural-reviewer** - Architecture compliance review
- (Additional agents listed in manifest.json)

## Installation

Shared agents are automatically downloaded during installation of TaskWright or RequireKit. Manual installation is not required.

### For Tool Maintainers

To integrate shared-agents into your tool:

1. Add version pinning file:
   ```bash
   echo "v1.0.0" > installer/shared-agents-version.txt
   ```

2. Update installer script to download agents:
   ```bash
   # See: docs/integration-guide.md
   ```

3. Install to `.claude/agents/universal/` directory

## Versioning

This repository follows [semantic versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes to agent interfaces
- **MINOR** (0.X.0): New agents or backward-compatible enhancements
- **PATCH** (0.0.X): Bug fixes and documentation updates

## Releases

Releases are published via GitHub Releases and include:
- `shared-agents.tar.gz` - Agent files and manifest
- `shared-agents.tar.gz.sha256` - Checksum for integrity verification

View releases: https://github.com/guardkit/shared-agents/releases

## Documentation

- [Integration Guide](docs/integration-guide.md) - How to use shared-agents in your tool
- [Changelog](CHANGELOG.md) - Version history and release notes
- [Contributing](docs/contributing.md) - How to contribute new agents

## Security

All releases include SHA256 checksums for integrity verification. See [Security](docs/security.md) for details.

## License

[MIT License](LICENSE) - Same as TaskWright and RequireKit

## Support

- **Issues**: https://github.com/guardkit/shared-agents/issues
- **Discussions**: https://github.com/guardkit/shared-agents/discussions
- **TaskWright**: https://github.com/guardkit/guardkit
- **RequireKit**: https://github.com/requirekit/require-kit

---

**Maintained by**: [TaskWright](https://github.com/guardkit)
**Version**: See [CHANGELOG.md](CHANGELOG.md)
```

### 4. Create CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository structure
- Documentation framework
- CI/CD workflows

## [1.0.0] - TBD

### Added
- Initial release of shared agents
- Universal agents: code-reviewer, test-orchestrator, architectural-reviewer
- Manifest.json for agent discovery
- SHA256 checksum validation
- Integration documentation

[Unreleased]: https://github.com/guardkit/shared-agents/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/guardkit/shared-agents/releases/tag/v1.0.0
```

### 5. Create LICENSE

```
MIT License

Copyright (c) 2025 TaskWright

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 6. Create .gitignore

```gitignore
# macOS
.DS_Store

# Editor files
.vscode/
.idea/
*.swp
*.swo
*~

# Temporary files
*.tmp
*.bak
*.log

# Build artifacts
*.tar.gz
*.zip

# Testing
coverage/
.pytest_cache/
```

### 7. Initial Commit

```bash
# Stage all files
git add .

# Commit
git commit -m "chore: Initialize shared-agents repository

- Add directory structure
- Add README with project overview
- Add CHANGELOG for version tracking
- Add MIT LICENSE (consistent with TaskWright/RequireKit)
- Add .gitignore for common artifacts"

# Push to main
git push origin main
```

## Test Requirements

### Validation Checklist

- [ ] Repository accessible at `https://github.com/guardkit/shared-agents`
- [ ] All files committed and pushed
- [ ] README renders correctly on GitHub
- [ ] License is MIT (matches TaskWright/RequireKit)
- [ ] Directory structure matches specification
- [ ] No syntax errors in markdown

## Dependencies

**Prerequisite Tasks**: All Phase 0 tasks (TASK-SHA-000 through SHA-004)

**Blocks**:
- TASK-SHA-P1-002 (Migrate agents - needs structure)
- TASK-SHA-P1-003 (Create manifest - needs directory)
- TASK-SHA-P1-004 (Set up GitHub Actions - needs repository)

**External Dependencies**:
- GitHub organization: `guardkit` (must have permissions)
- Git installed locally
- GitHub CLI (optional, can use web UI)

## Success Criteria

- [ ] Repository created and accessible
- [ ] All required files present and correct
- [ ] Documentation clear and complete
- [ ] License matches TaskWright/RequireKit
- [ ] Initial commit pushed to main
- [ ] No errors or warnings

## Estimated Effort

**Total**: 1 hour
- Repository creation: 15 minutes
- Documentation: 30 minutes
- Testing and verification: 15 minutes

## Notes

### Repository Settings

**Recommended settings**:
- Default branch: `main`
- Visibility: Public
- Features: Issues, Discussions enabled
- Merge strategy: Squash and merge (for clean history)
- Branch protection: Require PR reviews for main

### Repository Description

**Short description**: "Universal AI agents shared between TaskWright and RequireKit"

**Topics**: `ai`, `agents`, `guardkit`, `requirekit`, `claude-code`

## Related Documents

- Implementation Plan: `tasks/backlog/shared-agents-refactoring/IMPLEMENTATION-PLAN.md`
- Architectural Review: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md`
