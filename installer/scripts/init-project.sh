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
TEMPLATE=""
PROJECT_NAME=""
COPY_GRAPHITI=""

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

# Normalize project name to a valid project_id
# Matches guardkit.knowledge.graphiti_client.normalize_project_id()
normalize_project_id() {
    local name="$1"
    # Lowercase, replace non-alphanumeric (except hyphens) with hyphens
    local normalized
    normalized=$(echo "$name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
    # Truncate to 50 chars
    echo "${normalized:0:50}"
}

# Find source graphiti.yaml by walking up from parent of cwd
find_source_graphiti_config() {
    local start_dir="$1"
    local current_dir="$start_dir"
    local max_depth=10
    local depth=0

    while [ "$depth" -lt "$max_depth" ]; do
        if [ -f "$current_dir/.guardkit/graphiti.yaml" ]; then
            echo "$current_dir/.guardkit/graphiti.yaml"
            return 0
        fi
        if [ "$current_dir" = "/" ]; then
            return 1
        fi
        current_dir="$(dirname "$current_dir")"
        depth=$((depth + 1))
    done
    return 1
}

# Copy graphiti config from source, replacing project_id
copy_graphiti_config() {
    local source_file="$1"
    local target_dir="$2"
    local new_project_id="$3"
    local target_file="$target_dir/.guardkit/graphiti.yaml"

    mkdir -p "$target_dir/.guardkit"

    if [ ! -f "$source_file" ]; then
        print_warning "Source graphiti.yaml not found: $source_file"
        return 1
    fi

    # Copy the file, then replace the project_id line
    cp "$source_file" "$target_file"
    # Replace the project_id value (handles both quoted and unquoted YAML)
    sed -i '' "s/^project_id:.*$/project_id: $new_project_id/" "$target_file"

    print_success "Copied Graphiti config from $source_file"
    print_success "Set project_id: $new_project_id"
    return 0
}

# Write minimal graphiti.yaml with just project_id
write_graphiti_config() {
    local target_dir="$1"
    local project_id="$2"
    local target_file="$target_dir/.guardkit/graphiti.yaml"

    mkdir -p "$target_dir/.guardkit"
    echo "project_id: $project_id" > "$target_file"

    print_success "Written project_id to .guardkit/graphiti.yaml"
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
    # Skip -ext.md files - they stay in ~/.agentecflow/ for on-demand loading
    # (progressive disclosure: core files load always, extended files load on-demand)
    local template_agent_count=0
    if [ -d "$template_dir/agents" ] && [ "$(ls -A $template_dir/agents 2>/dev/null)" ]; then
        for agent_file in "$template_dir/agents"/*.md; do
            if [ -f "$agent_file" ]; then
                local agent_name=$(basename "$agent_file")
                # Skip extended files (-ext.md)
                case "$agent_name" in
                    *-ext.md) continue ;;
                esac
                cp "$agent_file" ".claude/agents/$agent_name"
                ((template_agent_count++))
            fi
        done
        if [ $template_agent_count -gt 0 ]; then
            print_success "Copied $template_agent_count template-specific agent(s)"
        fi
    fi

    # Copy global agents (skip if file exists from template, skip -ext.md)
    local global_agent_count=0
    if [ -d "$AGENTECFLOW_HOME/agents" ] && [ "$(ls -A $AGENTECFLOW_HOME/agents 2>/dev/null)" ]; then
        for agent_file in "$AGENTECFLOW_HOME/agents"/*.md; do
            if [ -f "$agent_file" ]; then
                local agent_name=$(basename "$agent_file")
                # Skip extended files (-ext.md)
                case "$agent_name" in
                    *-ext.md) continue ;;
                esac
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
    
    # NOTE: Global commands are already available via ~/.claude/commands/ symlink
    # Do NOT create project-level command symlinks - this causes duplicate commands
    # in Claude Code's autocomplete (user + project both point to same files)
    #
    # Commands are loaded from:
    #   ~/.claude/commands/ → ~/.agentecflow/commands/ (global, always available)
    #
    # Project-specific commands can still be added to .claude/commands/ if needed,
    # but we don't duplicate the global ones here.
    
    TEMPLATE="$effective_template"  # Update for later use
}

# Verify rules structure was copied correctly
verify_rules_structure() {
    local template_dir="$1"

    if [ -d "$template_dir/.claude/rules" ]; then
        if [ -d ".claude/rules" ]; then
            local template_rules=$(find "$template_dir/.claude/rules" -type f -name "*.md" | wc -l | tr -d ' ')
            local copied_rules=$(find ".claude/rules" -type f -name "*.md" | wc -l | tr -d ' ')

            if [ "$copied_rules" -ge "$template_rules" ]; then
                print_success "Rules structure verified ($copied_rules rule files)"
            else
                print_warning "Rules structure incomplete: expected $template_rules files, found $copied_rules"
            fi
        else
            print_warning "Rules structure expected but not found - Claude Code context optimization unavailable"
        fi
    fi
}

# Create project configuration
create_config() {
    print_info "Creating project configuration..."

    local project_name
    if [ -n "$PROJECT_NAME" ]; then
        project_name="$PROJECT_NAME"
    else
        project_name=$(basename "$PROJECT_DIR")
    fi
    local detected_type=$(detect_project_type)

    # Use ~ for portability instead of absolute path
    local extends_path="~/.agentecflow/templates/$TEMPLATE"

    cat > .claude/settings.json << EOF
{
  "version": "1.0.0",
  "extends": "$extends_path",
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
    local interactive=false

    # Parse arguments - support flags mixed with positional args
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help|help)
                show_templates
                echo ""
                echo "Options:"
                echo "  -n, --project-name NAME    Override project name (defaults to directory name)"
                echo "  --copy-graphiti [PATH]     Copy Graphiti config from existing project"
                echo "                             Without PATH: auto-discovers from parent directories"
                echo "                             With PATH: copies from specified project directory"
                echo "  -i, --interactive          Interactive setup mode"
                echo "  -h, --help                 Show this help message"
                exit 0
                ;;
            -i|--interactive)
                interactive=true
                shift
                ;;
            -n|--project-name)
                if [ -z "$2" ] || [[ "$2" == -* ]]; then
                    print_error "--project-name requires a value"
                    exit 1
                fi
                PROJECT_NAME="$2"
                shift 2
                ;;
            --copy-graphiti)
                # --copy-graphiti with optional path argument
                if [ -n "$2" ] && [[ "$2" != -* ]]; then
                    COPY_GRAPHITI="$2"
                    shift 2
                else
                    COPY_GRAPHITI="auto"
                    shift
                fi
                ;;
            -*)
                print_error "Unknown option: $1"
                echo "Run 'guardkit init --help' for usage"
                exit 1
                ;;
            *)
                # Positional argument = template name
                if [ -z "$TEMPLATE" ]; then
                    TEMPLATE="$1"
                else
                    print_error "Unexpected argument: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Default template if not specified
    if [ -z "$TEMPLATE" ]; then
        if [ "$interactive" = true ]; then
            select_template_interactive
        else
            # Try to auto-detect or go interactive
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
        fi
    fi

    # Default TEMPLATE fallback
    TEMPLATE="${TEMPLATE:-default}"

    print_header
    print_info "Using GuardKit from: $AGENTECFLOW_HOME"
    check_existing
    create_project_structure
    copy_template_files
    verify_rules_structure "$AGENTECFLOW_HOME/templates/$TEMPLATE"
    create_config
    create_initial_files

    # Handle Graphiti config (after structure is created)
    local project_id
    if [ -n "$PROJECT_NAME" ]; then
        project_id=$(normalize_project_id "$PROJECT_NAME")
    else
        project_id=$(normalize_project_id "$(basename "$PROJECT_DIR")")
    fi

    if [ -n "$COPY_GRAPHITI" ]; then
        local source_config=""
        if [ "$COPY_GRAPHITI" = "auto" ]; then
            # Auto-discover: walk up from parent of cwd
            local parent_dir
            parent_dir="$(cd "$PROJECT_DIR/.." 2>/dev/null && pwd)"
            source_config=$(find_source_graphiti_config "$parent_dir" 2>/dev/null || true)
        else
            # Explicit path provided
            local explicit_path
            explicit_path=$(eval echo "$COPY_GRAPHITI")  # expand ~
            if [ -f "$explicit_path/.guardkit/graphiti.yaml" ]; then
                source_config="$explicit_path/.guardkit/graphiti.yaml"
            elif [ -f "$explicit_path" ]; then
                # Maybe they pointed directly at the file
                source_config="$explicit_path"
            fi
        fi

        if [ -n "$source_config" ]; then
            copy_graphiti_config "$source_config" "$PROJECT_DIR" "$project_id"
        else
            print_warning "No source graphiti.yaml found, writing project_id only"
            write_graphiti_config "$PROJECT_DIR" "$project_id"
        fi
    else
        # Default: write minimal graphiti config with project_id
        write_graphiti_config "$PROJECT_DIR" "$project_id"
    fi

    print_next_steps
}

# Run main
main "$@"
