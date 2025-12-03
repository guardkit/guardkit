# Shared Agents Architecture Proposal

**Status:** Approved  
**Date:** November 28, 2025  
**Author:** Rich (Appmilla)  
**Applies to:** GuardKit, RequireKit

---

## Executive Summary

This proposal addresses the duplication of sub-agent definitions between GuardKit and RequireKit repositories. Both tools evolved from the original `ai-engineer` repo and currently maintain separate copies of universal agents, leading to version drift and maintenance burden.

**Agreed Solution:** Hybrid approach using a dedicated `shared-agents` repository with build-time composition.

---

## Problem Statement

### Current Situation

Both repositories contain duplicate copies of universal agents:

| Agent | Purpose | Duplicated In |
|-------|---------|---------------|
| `requirements-analyst.md` | EARS notation validation, requirement refinement | Both repos |
| `bdd-generator.md` | Gherkin scenario creation | Both repos |
| `test-orchestrator.md` | Test execution coordination, coverage monitoring | Both repos |
| `code-reviewer.md` | Quality standards enforcement | Both repos |

### Issues with Duplication

1. **Version Drift** - Changes made in one repo don't propagate to the other
2. **Maintenance Burden** - Updating the same agent twice
3. **Inconsistent Behavior** - Users get different experiences depending on which repo was updated more recently
4. **Testing Complexity** - Need to test identical code in multiple places

---

## Agreed Solution: Hybrid Approach

We will implement a **build-time composition** strategy with a dedicated shared-agents repository.

### Architecture Overview

```
GitHub Organizations:
├── guardkit/
│   ├── guardkit           # Main tool with stack-specific agents
│   └── shared-agents        # Universal agents (source of truth)
│
└── requirekit/
    └── require-kit          # Requirements-specific commands + agents
```

### Shared Agents Repository Structure

```
guardkit/shared-agents/
├── agents/
│   ├── requirements-analyst.md
│   ├── bdd-generator.md
│   ├── test-orchestrator.md
│   └── code-reviewer.md
├── manifest.json            # Agent listing and metadata
├── version.txt              # Current version
├── CHANGELOG.md
└── README.md
```

### How It Works

1. **Source of Truth:** Universal agents live in `shared-agents` repo only
2. **Build-Time Download:** Installers download agents during installation
3. **Version Pinning:** Each consuming repo pins to a specific version
4. **No Runtime Dependencies:** Agents are copied at install time, not symlinked

---

## Implementation Details

### 1. Shared Agents Repository

**manifest.json:**
```json
{
  "version": "1.0.0",
  "agents": [
    {
      "name": "requirements-analyst",
      "file": "agents/requirements-analyst.md",
      "description": "Validates and refines requirements before implementation",
      "universal": true
    },
    {
      "name": "bdd-generator",
      "file": "agents/bdd-generator.md",
      "description": "Creates BDD scenarios from requirements",
      "universal": true
    },
    {
      "name": "test-orchestrator",
      "file": "agents/test-orchestrator.md",
      "description": "Coordinates test generation and execution",
      "universal": true
    },
    {
      "name": "code-reviewer",
      "file": "agents/code-reviewer.md",
      "description": "Enforces quality standards through code review",
      "universal": true
    }
  ]
}
```

### 2. GitHub Actions Release Workflow

**.github/workflows/release.yml:**
```yaml
name: Release Shared Agents

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create release archive
        run: |
          tar -czvf shared-agents.tar.gz agents/ manifest.json
          
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: shared-agents.tar.gz
          generate_release_notes: true
```

### 3. GuardKit Installer Integration

**installer/shared-agents-version.txt:**
```
v1.0.0
```

**installer/scripts/install.sh (additions):**
```bash
install_shared_agents() {
    local version_file="$SCRIPT_DIR/../shared-agents-version.txt"
    local version=$(cat "$version_file" 2>/dev/null || echo "v1.0.0")
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"
    local download_url="https://github.com/guardkit/shared-agents/releases/download/$version/shared-agents.tar.gz"
    
    echo "📦 Installing shared agents $version..."
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Download and extract
    if curl -sL "$download_url" | tar -xz -C "$target_dir" --strip-components=1; then
        echo "✅ Installed shared agents $version"
    else
        echo "⚠️  Failed to download shared agents, using bundled fallback"
        # Copy from bundled fallback if download fails
        cp -r "$SCRIPT_DIR/../fallback/agents/universal/"* "$target_dir/"
    fi
}

# Call during installation
install_shared_agents
```

### 4. RequireKit Installer Integration

**installer/shared-agents-version.txt:**
```
v1.0.0
```

**installer/scripts/install.sh (additions):**
```bash
install_shared_agents() {
    local version_file="$SCRIPT_DIR/../shared-agents-version.txt"
    local version=$(cat "$version_file" 2>/dev/null || echo "v1.0.0")
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"
    local download_url="https://github.com/guardkit/shared-agents/releases/download/$version/shared-agents.tar.gz"
    
    echo "📦 Installing shared agents $version..."
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Download and extract
    if curl -sL "$download_url" | tar -xz -C "$target_dir" --strip-components=1; then
        echo "✅ Installed shared agents $version"
    else
        echo "⚠️  Failed to download shared agents, using bundled fallback"
        cp -r "$SCRIPT_DIR/../fallback/agents/universal/"* "$target_dir/"
    fi
}

# Call during installation
install_shared_agents
```

### 5. Directory Structure After Installation

**GuardKit (standalone):**
```
.claude/
├── agents/
│   ├── universal/                    # Downloaded from shared-agents
│   │   ├── requirements-analyst.md
│   │   ├── bdd-generator.md
│   │   ├── test-orchestrator.md
│   │   └── code-reviewer.md
│   ├── react-specialist.md           # GuardKit-specific
│   ├── python-specialist.md          # GuardKit-specific
│   └── repository-pattern-specialist.md
└── commands/
    ├── task-create.md
    ├── task-work.md
    └── task-complete.md
```

**RequireKit (standalone):**
```
.claude/
├── agents/
│   ├── universal/                    # Downloaded from shared-agents
│   │   ├── requirements-analyst.md
│   │   ├── bdd-generator.md
│   │   ├── test-orchestrator.md
│   │   └── code-reviewer.md
│   └── requirements-gathering-specialist.md  # RequireKit-specific
└── commands/
    ├── gather-requirements.md
    ├── formalize-ears.md
    └── generate-bdd.md
```

**Combined Installation (GuardKit + RequireKit):**
```
.claude/
├── agents/
│   ├── universal/                    # Shared (only installed once)
│   │   ├── requirements-analyst.md
│   │   ├── bdd-generator.md
│   │   ├── test-orchestrator.md
│   │   └── code-reviewer.md
│   ├── react-specialist.md           # From GuardKit
│   ├── python-specialist.md          # From GuardKit
│   └── requirements-gathering-specialist.md  # From RequireKit
└── commands/
    ├── task-create.md                # From GuardKit
    ├── task-work.md                  # From GuardKit
    ├── gather-requirements.md        # From RequireKit
    └── formalize-ears.md             # From RequireKit
```

---

## Benefits of This Approach

| Benefit | Description |
|---------|-------------|
| **Single Source of Truth** | Universal agents live in one place only |
| **Independent Versioning** | Each repo can pin different versions if needed |
| **No Runtime Dependencies** | Agents are copied at install time |
| **Standalone Works** | Each repo still works independently |
| **Easy Updates** | Bump version in pinning file, re-run installer |
| **CI/CD Friendly** | No submodule complexity |
| **Contributor Friendly** | Standard git workflows |
| **Offline Fallback** | Bundled fallback agents if download fails |

---

## Migration Plan

### Phase 1: Create Shared Agents Repository (Day 1)

- [ ] Create `guardkit/shared-agents` repository
- [ ] Move universal agents from GuardKit to shared-agents
- [ ] Create `manifest.json` with agent metadata
- [ ] Create `version.txt` with initial version (v1.0.0)
- [ ] Set up GitHub Actions release workflow
- [ ] Create initial release (v1.0.0)

### Phase 2: Update GuardKit (Day 2)

- [ ] Add `installer/shared-agents-version.txt`
- [ ] Update `install.sh` with `install_shared_agents` function
- [ ] Create fallback agents directory for offline installation
- [ ] Remove duplicate universal agents from `.claude/agents/`
- [ ] Update documentation
- [ ] Test standalone installation

### Phase 3: Update RequireKit (Day 3)

- [ ] Add `installer/shared-agents-version.txt`
- [ ] Update `install.sh` with `install_shared_agents` function
- [ ] Create fallback agents directory for offline installation
- [ ] Remove duplicate universal agents from `.claude/agents/`
- [ ] Update documentation
- [ ] Test standalone installation

### Phase 4: Integration Testing (Day 4)

- [ ] Test GuardKit standalone installation
- [ ] Test RequireKit standalone installation
- [ ] Test combined installation (both tools)
- [ ] Test version pinning (different versions in each repo)
- [ ] Test offline fallback behavior
- [ ] Update CI/CD pipelines

### Phase 5: Documentation & Release (Day 5)

- [ ] Update README files in all three repos
- [ ] Create migration guide for existing users
- [ ] Announce change in release notes
- [ ] Tag new releases of GuardKit and RequireKit

---

## Version Management

### Versioning Strategy

The `shared-agents` repository follows semantic versioning:

- **MAJOR:** Breaking changes to agent interfaces or behavior
- **MINOR:** New agents added, backward-compatible enhancements
- **PATCH:** Bug fixes, documentation updates

### Updating Shared Agents

1. Make changes in `shared-agents` repository
2. Create new release tag (e.g., `v1.1.0`)
3. Update `shared-agents-version.txt` in GuardKit
4. Update `shared-agents-version.txt` in RequireKit
5. Release new versions of consuming tools

### Rollback Procedure

If issues are discovered:

1. Revert `shared-agents-version.txt` to previous version
2. Re-run installer to download previous agent versions
3. Investigate and fix issues in `shared-agents`
4. Release patch version when fixed

---

## Future Considerations

### Additional Shared Resources

This pattern can be extended to share:

- **Commands:** Universal commands used by both tools
- **Templates:** Shared template files
- **Quality Gates:** Common quality gate definitions

### MCP Server Integration

When transitioning to MCP servers, the shared-agents pattern provides a foundation:

- Agents can be served dynamically from an MCP server
- Version pinning moves from file-based to API-based
- Same single-source-of-truth principle applies

---

## Alternatives Considered

### 1. NPM/PyPI Package

**Rejected because:**
- Adds package manager dependency complexity
- More complex for local development
- Overkill for markdown files

### 2. Git Submodules

**Rejected because:**
- Notoriously difficult for contributors
- Extra steps for cloning (`--recursive`)
- Can confuse CI/CD pipelines

### 3. Copy-Paste with Manual Sync

**Rejected because:**
- Current approach, proven to cause drift
- High maintenance burden
- Error-prone

---

## Appendix: Agent Definitions

### requirements-analyst.md

```markdown
---
name: requirements-analyst
description: Validates and refines requirements before implementation
model: sonnet
tools: Read, Write, Search
universal: true
---

You are a requirements analyst who ensures all requirements are clear, complete, and implementable.

## Responsibilities

1. Validate EARS notation compliance
2. Identify missing requirements
3. Clarify ambiguous requirements
4. Ensure testability
5. Check for conflicts
```

### bdd-generator.md

```markdown
---
name: bdd-generator
description: Creates BDD scenarios from requirements
model: sonnet
tools: Read, Write, Search
universal: true
---

You are a BDD specialist who creates comprehensive Gherkin scenarios from requirements.

## Responsibilities

1. Generate Given-When-Then scenarios
2. Ensure scenario coverage
3. Create edge case scenarios
4. Maintain scenario consistency
```

### test-orchestrator.md

```markdown
---
name: test-orchestrator
description: Coordinates test generation and execution
model: sonnet
tools: Read, Write, Execute, Search
universal: true
---

You are a test orchestrator who ensures comprehensive test coverage.

## Responsibilities

1. Generate test cases from requirements
2. Create unit tests
3. Create integration tests
4. Execute test suites
5. Report coverage metrics
```

### code-reviewer.md

```markdown
---
name: code-reviewer
description: Enforces quality standards through code review
model: sonnet
tools: Read, Write, Search, Grep
universal: true
---

You are a code reviewer who ensures code quality and standards compliance.

## Responsibilities

1. Requirements compliance
2. Code quality checks
3. Security review
4. Performance analysis
5. Documentation verification
```

---

**Document Version:** 1.0  
**Last Updated:** November 28, 2025  
**Status:** Approved for Implementation
