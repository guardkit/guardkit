#!/bin/bash

# GuardKit Project Initialization Script
# Works with ~/.agentecflow structure (backward compatible)

set -e

# Configuration - Support multiple possible locations
if [ -n "$CLAUDE_HOME" ]; then
    AGENTECFLOW_HOME="$CLAUDE_HOME"
elif [ -d "$HOME/.agentecflow" ]; then
    AGENTECFLOW_HOME="$HOME/.agentecflow"
elif [ -d "$HOME/.agenticflow" ]; then
    AGENTECFLOW_HOME="$HOME/.agenticflow"
elif [ -d "$HOME/.agentic-flow" ]; then
    AGENTECFLOW_HOME="$HOME/.agentic-flow"
elif [ -d "$HOME/.claude" ]; then
    AGENTECFLOW_HOME="$HOME/.claude"
else
    echo "Error: No GuardKit installation found"
    echo "Please run the installer first"
    exit 1
fi

PROJECT_DIR="$(pwd)"
TEMPLATE="${1:-default}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         GuardKit Project Initialization              ║${NC}"
    echo -e "${BLUE}║         Template: ${BOLD}$(printf '%-20s' "$TEMPLATE")${NC}${BLUE}         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Show available templates
show_templates() {
    echo "Available templates:"
    if [ -d "$AGENTECFLOW_HOME/templates" ]; then
        for template_dir in "$AGENTECFLOW_HOME/templates"/*/; do
            if [ -d "$template_dir" ]; then
                local name=$(basename "$template_dir")
                case "$name" in
                    default)
                        echo "  • default - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)"
                        ;;
                    react-typescript)
                        echo "  • react-typescript - React frontend with feature-based architecture (9+/10)"
                        ;;
                    fastapi-python)
                        echo "  • fastapi-python - FastAPI backend with layered architecture (9+/10)"
                        ;;
                    nextjs-fullstack)
                        echo "  • nextjs-fullstack - Next.js App Router full-stack (9+/10)"
                        ;;
                    react-fastapi-monorepo)
                        echo "  • react-fastapi-monorepo - React + FastAPI monorepo with type safety (9.2/10)"
                        ;;
                    *)
                        echo "  • $name"
                        ;;
                esac
            fi
        done
    fi
}

# Interactive template selection
select_template_interactive() {
    show_templates
    echo ""
    read -p "Select template (default): " selected
    TEMPLATE="${selected:-default}"
}

# Detect existing project type
detect_project_type() {
    # Check for .csproj files
    if ls *.csproj 2>/dev/null | grep -q . || ls */*.csproj 2>/dev/null | grep -q .; then
        echo "dotnet"
    elif [ -f "package.json" ]; then
        if grep -q "react" package.json; then
            echo "react"
        elif grep -q "vue" package.json; then
            echo "vue"
        else
            echo "node"
        fi
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        echo "python"
    else
        echo "unknown"
    fi
}

# Check if already initialized
check_existing() {
    if [ -d ".claude" ]; then
        print_warning ".claude directory already exists"
        read -p "Reinitialize? This will backup the existing configuration (y/n): " -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Initialization cancelled"
            exit 0
        fi
        mv .claude .claude.backup.$(date +%Y%m%d_%H%M%S)
        print_success "Existing configuration backed up"
    fi
}

# Create project structure
create_project_structure() {
    print_info "Creating project structure..."

    # Always create .claude at root
    mkdir -p .claude/{agents,commands,hooks,templates,stacks}

    # Always create docs at root
    mkdir -p docs/{adr,state}

    # Create task management structure (core guardkit feature)
    mkdir -p tasks/{backlog,in_progress,in_review,blocked,completed}

    # Handle test directory based on project type
    local detected_type=$(detect_project_type)
    case "$detected_type" in
        dotnet)
            print_info "Tests will be managed within .NET solution structure"
            ;;
        *)
            if [ ! -d "tests" ]; then
                mkdir -p tests/{unit,integration,e2e}
                print_success "Created test directories"
            else
                print_info "Using existing tests directory"
            fi
            ;;
    esac

    print_success "Project structure created"
}

# Copy template files
copy_template_files() {
    local detected_type=$(detect_project_type)
    local effective_template="$TEMPLATE"
    
    # Auto-select template based on detected type if using default
    if [ "$TEMPLATE" = "default" ] && [ "$detected_type" != "unknown" ]; then
        case "$detected_type" in
            react) effective_template="react-typescript" ;;
            python) effective_template="fastapi-python" ;;
            node) effective_template="nextjs-fullstack" ;;
        esac
        if [ "$effective_template" != "default" ]; then
            print_info "Auto-selected template: $effective_template (detected $detected_type project)"
        fi
    fi
    
    local template_dir="$AGENTECFLOW_HOME/templates/$effective_template"

    if [ ! -d "$template_dir" ]; then
        print_warning "Template '$effective_template' not found, using default"
        template_dir="$AGENTECFLOW_HOME/templates/default"
        effective_template="default"
    fi
    
    print_info "Using template: $effective_template"
    
    # Copy CLAUDE.md context file (check both locations, .claude/ takes precedence)
    if [ -f "$template_dir/.claude/CLAUDE.md" ]; then
        cp "$template_dir/.claude/CLAUDE.md" .claude/
        print_success "Copied project context file (from .claude/)"
    elif [ -f "$template_dir/CLAUDE.md" ]; then
        cp "$template_dir/CLAUDE.md" .claude/
        print_success "Copied project context file"
    fi
    
    # Copy template agents first (take precedence)
    if [ -d "$template_dir/agents" ] && [ "$(ls -A $template_dir/agents 2>/dev/null)" ]; then
        cp -r "$template_dir/agents/"* .claude/agents/ 2>/dev/null || true
        print_success "Copied template-specific agents"
    fi

    # Copy global agents (skip if file exists from template)
    local global_agent_count=0
    if [ -d "$AGENTECFLOW_HOME/agents" ] && [ "$(ls -A $AGENTECFLOW_HOME/agents 2>/dev/null)" ]; then
        for agent_file in "$AGENTECFLOW_HOME/agents"/*.md; do
            if [ -f "$agent_file" ]; then
                local agent_name=$(basename "$agent_file")
                # Only copy if file doesn't already exist (template takes precedence)
                if [ ! -f ".claude/agents/$agent_name" ]; then
                    cp "$agent_file" ".claude/agents/$agent_name"
                    ((global_agent_count++))
                fi
            fi
        done
        if [ $global_agent_count -gt 0 ]; then
            print_success "Added $global_agent_count global agent(s)"
        fi
    fi
    
    # Copy templates
    if [ -d "$template_dir/templates" ]; then
        cp -r "$template_dir/templates/"* .claude/templates/ 2>/dev/null || true
        print_success "Copied template files"
    fi

    # Copy template docs (patterns/reference for progressive disclosure)
    if [ -d "$template_dir/docs" ]; then
        local docs_copied=0

        # Copy patterns if exists
        if [ -d "$template_dir/docs/patterns" ]; then
            mkdir -p docs/patterns
            cp -r "$template_dir/docs/patterns/"* docs/patterns/ 2>/dev/null && docs_copied=1 || true
        fi

        # Copy reference if exists
        if [ -d "$template_dir/docs/reference" ]; then
            mkdir -p docs/reference
            cp -r "$template_dir/docs/reference/"* docs/reference/ 2>/dev/null && docs_copied=1 || true
        fi

        if [ $docs_copied -eq 1 ]; then
            print_success "Copied template documentation (patterns/reference)"
        fi
    fi

    # Copy .claude/rules/ directory (for Claude Code modular rules)
    if [ -d "$template_dir/.claude/rules" ]; then
        mkdir -p .claude/rules
        cp -r "$template_dir/.claude/rules/"* .claude/rules/ 2>/dev/null || true
        print_success "Copied rules structure for Claude Code"
    fi

    # Copy other template-specific files
    for file in "$template_dir"/*.md "$template_dir"/*.json; do
        if [ -f "$file" ] && [ "$(basename "$file")" != "CLAUDE.md" ]; then
            cp "$file" .claude/
        fi
    done 2>/dev/null || true
    
    # Link to global commands
    if [ -d "$AGENTECFLOW_HOME/commands" ]; then
        for cmd in "$AGENTECFLOW_HOME/commands"/*.md; do
            if [ -f "$cmd" ]; then
                local cmd_name=$(basename "$cmd")
                # Create symlink or copy if symlink fails
                ln -sf "$cmd" ".claude/commands/$cmd_name" 2>/dev/null || \
                cp "$cmd" ".claude/commands/$cmd_name"
            fi
        done
        print_success "Linked GuardKit commands"
    fi
    
    TEMPLATE="$effective_template"  # Update for later use
}

# Create project configuration
create_config() {
    print_info "Creating project configuration..."
    
    local project_name=$(basename "$PROJECT_DIR")
    local detected_type=$(detect_project_type)
    
    cat > .claude/settings.json << EOF
{
  "version": "1.0.0",
  "extends": "$AGENTECFLOW_HOME/templates/$TEMPLATE",
  "project": {
    "name": "$project_name",
    "template": "$TEMPLATE",
    "detected_type": "$detected_type",
    "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  },
  "methodology": {
    "requirements": "EARS",
    "testing": "BDD",
    "documentation": "ADR"
  },
  "quality": {
    "coverage": 80,
    "complexity": 10,
    "gates": true
  }
}
EOF
    
    print_success "Created project configuration"
}

# Create initial files
create_initial_files() {
    print_info "Creating initial documentation..."
    
    # Create .claudeignore
    cat > .claude/.claudeignore << 'EOF'
# Files to exclude from Claude context
node_modules/
venv/
.venv/
__pycache__/
*.pyc
dist/
build/
bin/
obj/
.git/
.env
*.log
coverage/
*.tmp
.vs/
.vscode/settings.json
.idea/
*.user
*.suo
EOF
    
    # Create initial sprint file
    cat > docs/state/current-sprint.md << EOF
---
sprint: 1
start: $(date +%Y-%m-%d)
status: planning
---

# Sprint 1 - Project Setup

## Goals
- [ ] Set up GuardKit system
- [ ] Create first task
- [ ] Complete implementation with quality gates

## Progress
- Overall: 10% [██░░░░░░░░░░░░░░░░░░]

## Next Steps
1. Use \`/task-create\` to create your first task
2. Use \`/task-work\` to implement with quality gates
3. Use \`/task-complete\` to finish and archive
EOF
    
    # Create first ADR
    cat > docs/adr/0001-adopt-agentic-flow.md << EOF
---
id: ADR-001
status: accepted
date: $(date +%Y-%m-%d)
---

# ADR-001: Adopt GuardKit System

## Status
Accepted

## Context
We need a lightweight task workflow system with built-in quality gates that prevents broken code from reaching production.

## Decision
Adopt the GuardKit system with automated architectural review and test enforcement.

## Consequences
**Positive:**
- Quality-first approach with automated gates
- Lightweight task workflow (create → work → complete)
- AI collaboration with human oversight
- Zero ceremony overhead

**Negative:**
- Initial setup required
- Learning curve for quality gates
EOF
    
    print_success "Created initial documentation"
}

# Print next steps
print_next_steps() {
    local detected_type=$(detect_project_type)
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ GuardKit successfully initialized!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}📁 Project Structure Created:${NC}"
    echo "  .claude/       - GuardKit configuration"
    echo "  docs/          - Documentation and ADRs"
    echo "  tasks/         - Task workflow (backlog → in_progress → in_review → blocked → completed)"
    echo ""
    echo -e "${BOLD}Project Configuration:${NC}"
    echo "  🎨 Template: $TEMPLATE"
    echo "  🔍 Detected Type: $detected_type"
    echo ""
    
    # List installed agents
    echo -e "${BOLD}AI Agents:${NC}"
    if [ -d ".claude/agents" ]; then
        for agent in .claude/agents/*.md; do
            if [ -f "$agent" ]; then
                echo "  🤖 $(basename "$agent" .md)"
            fi
        done
    fi
    echo ""
    
    # Template-specific instructions (simplified)
    case "$TEMPLATE" in
        dotnet-aspnetcontroller)
            echo -e "${BOLD}Quick Start for .NET Web API (Controllers):${NC}"
            echo ""
            echo "  📦 Creating .NET Web API Project:"
            echo "     dotnet new webapi -n YourServiceName --use-controllers"
            echo ""
            echo "  ✨ GuardKit provides:"
            echo "     • ErrorOr pattern for functional error handling"
            echo "     • Controller best practices and examples"
            echo "     • Specialized AI agents for .NET development"
            echo "     • Testing patterns and quality gates"
            echo ""
            echo "  🚀 GuardKit Workflow:"
            echo "     1. /task-create 'Add product endpoints'"
            echo "     2. /task-work TASK-001"
            echo "     3. /task-complete TASK-001"
            echo ""
            ;;
        dotnet-minimalapi)
            echo -e "${BOLD}Quick Start for .NET Minimal API:${NC}"
            echo ""
            echo "  📦 Creating .NET Minimal API Project:"
            echo "     dotnet new web -n YourServiceName"
            echo "     # or"
            echo "     dotnet new webapi -n YourServiceName --use-minimal-apis"
            echo ""
            echo "  ✨ GuardKit provides:"
            echo "     • ErrorOr pattern for functional error handling"
            echo "     • Minimal API best practices and examples"
            echo "     • Specialized AI agents for .NET development"
            echo "     • Testing patterns and quality gates"
            echo ""
            echo "  🚀 GuardKit Workflow:"
            echo "     1. /task-create 'Add weather endpoints'"
            echo "     2. /task-work TASK-001"
            echo "     3. /task-complete TASK-001"
            echo ""
            ;;
        react-typescript)
            echo -e "${BOLD}Quick Start for React TypeScript:${NC}"
            echo "  1. Create your first task: /task-create 'Add user dashboard component'"
            echo "  2. Work on it: /task-work TASK-001"
            echo "  3. Complete: /task-complete TASK-001"
            echo ""
            ;;
        fastapi-python)
            echo -e "${BOLD}Quick Start for FastAPI Python:${NC}"
            echo "  1. Create your first task: /task-create 'Add API endpoint'"
            echo "  2. Work on it: /task-work TASK-001"
            echo "  3. Complete: /task-complete TASK-001"
            echo ""
            ;;
        nextjs-fullstack)
            echo -e "${BOLD}Quick Start for Next.js Full-Stack:${NC}"
            echo "  1. Create your first task: /task-create 'Add user page'"
            echo "  2. Work on it: /task-work TASK-001"
            echo "  3. Complete: /task-complete TASK-001"
            echo ""
            ;;
        react-fastapi-monorepo)
            echo -e "${BOLD}Quick Start for React + FastAPI Monorepo:${NC}"
            echo "  1. Create your first task: /task-create 'Add user feature'"
            echo "  2. Work on it: /task-work TASK-001"
            echo "  3. Complete: /task-complete TASK-001"
            echo ""
            ;;
    esac
    
    echo -e "${BOLD}GuardKit Workflow:${NC}"
    echo ""
    echo "  Simple Task Management:"
    echo "    /task-create      - Create a new task"
    echo "    /task-work        - Work on task (with quality gates)"
    echo "    /task-complete    - Complete and archive task"
    echo "    /task-status      - View task status"
    echo "    /task-refine      - Iterative refinement"
    echo ""
    echo "  Design-First Workflow (complex tasks):"
    echo "    /task-work --design-only      - Plan approval checkpoint"
    echo "    /task-work --implement-only   - Implement approved plan"
    echo ""
    echo "  Utilities:"
    echo "    /debug            - Troubleshoot issues"
    echo ""
    echo -e "${BOLD}Using AI Agents:${NC}"
    echo "  AI agents are invoked automatically during /task-work"
    echo "  They handle architectural review, testing, and code review"
    echo ""
    echo -e "${BOLD}Need Requirements Management?${NC}"
    echo "  For EARS notation, BDD, epics, and portfolio management:"
    echo -e "  Install require-kit: ${BLUE}https://github.com/requirekit/require-kit${NC}"
    echo ""
    echo -e "${BOLD}⚠️  Important - If using VS Code:${NC}"
    echo "  Reload VS Code window to enable slash commands:"
    echo "  • Press Cmd+Shift+P (macOS) or Ctrl+Shift+P (Windows/Linux)"
    echo "  • Type 'Developer: Reload Window' and press Enter"
    echo "  • Or close and reopen VS Code"
    echo ""
    echo -e "${BLUE}Ready to start development!${NC}"
}

# Main function
main() {
    # Handle arguments
    case "$1" in
        -h|--help|help)
            show_templates
            exit 0
            ;;
        -i|--interactive)
            select_template_interactive
            ;;
        "")
            # No template specified, try to auto-detect or go interactive
            local detected=$(detect_project_type)
            if [ "$detected" != "unknown" ]; then
                print_info "Detected project type: $detected"

                read -p "Use matching template? (y/n): " -r
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    case "$detected" in
                        react) TEMPLATE="react-typescript" ;;
                        python) TEMPLATE="fastapi-python" ;;
                        node) TEMPLATE="nextjs-fullstack" ;;
                        *) TEMPLATE="default" ;;
                    esac
                else
                    select_template_interactive
                fi
            else
                select_template_interactive
            fi
            ;;
        *)
            TEMPLATE="$1"
            ;;
    esac
    
    print_header
    print_info "Using GuardKit from: $AGENTECFLOW_HOME"
    check_existing
    create_project_structure
    copy_template_files
    create_config
    create_initial_files
    print_next_steps
}

# Run main
main "$@"
