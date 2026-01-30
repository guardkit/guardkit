#!/bin/bash

# Agentecflow - Global Installation Script
# Creates the complete ~/.agentecflow structure matching production setup

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Installation configuration
AGENTECFLOW_VERSION="2.0.0"
INSTALL_DIR="$HOME/.agentecflow"
CONFIG_DIR="$HOME/.config/agentecflow"
INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GITHUB_REPO="https://github.com/guardkit/guardkit"
GITHUB_BRANCH="main"
INSTALL_METHOD="git-clone"  # Default, updated if running via curl

# Test mode configuration
TEST_MODE=false
if [ "$1" = "--test-mode" ]; then
    TEST_MODE=true
    print_info "Running in test mode"
fi

# Function to print colored messages
print_message() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo ""
    print_message "$BLUE" "╔════════════════════════════════════════════════════════╗"
    print_message "$BLUE" "║         GuardKit Installation System                 ║"
    print_message "$BLUE" "║         Version: $AGENTECFLOW_VERSION                  ║"
    print_message "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo ""
}

print_success() {
    print_message "$GREEN" "✓ $1"
}

print_error() {
    print_message "$RED" "✗ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠ $1"
}

print_info() {
    print_message "$BLUE" "ℹ $1"
}

# Download repository if running via curl (files not available locally)
ensure_repository_files() {
    # Check if we have the required files
    if [ ! -f "$INSTALLER_DIR/scripts/init-project.sh" ] || [ ! -d "$INSTALLER_DIR/core/templates" ]; then
        print_info "Running from curl - cloning repository permanently..."
        INSTALL_METHOD="curl"

        # Determine permanent location for repository
        # Use ~/Projects/guardkit or ~/guardkit if ~/Projects doesn't exist
        local REPO_DEST
        if [ -d "$HOME/Projects" ]; then
            REPO_DEST="$HOME/Projects/guardkit"
        else
            REPO_DEST="$HOME/guardkit"
        fi

        # Check if git is available for cloning
        if command -v git &> /dev/null; then
            # Git available - clone repository
            print_info "Cloning repository to $REPO_DEST..."

            # Remove existing directory if present
            if [ -d "$REPO_DEST" ]; then
                print_warning "Repository already exists at $REPO_DEST"
                print_info "Updating existing repository..."
                cd "$REPO_DEST" && git pull
            else
                # Clone fresh
                if ! git clone "$GITHUB_REPO" "$REPO_DEST"; then
                    print_error "Failed to clone repository"
                    print_info "Try cloning manually: git clone $GITHUB_REPO $REPO_DEST"
                    exit 1
                fi
            fi

            # Update INSTALLER_DIR to point to cloned repo
            INSTALLER_DIR="$REPO_DEST/installer"
            print_success "Repository cloned to $REPO_DEST"
        else
            # Git not available - fall back to tarball download (PERMANENT location)
            print_warning "git not found - downloading tarball instead"
            print_info "Installing git is recommended for easier updates"

            # Create permanent directory
            mkdir -p "$REPO_DEST"

            # Download and extract
            print_info "Downloading from $GITHUB_REPO to $REPO_DEST..."
            if ! curl -sSL "$GITHUB_REPO/archive/refs/heads/$GITHUB_BRANCH.tar.gz" | tar -xz -C "$REPO_DEST" --strip-components=1; then
                print_error "Failed to download repository"
                print_info "Try installing git and cloning: git clone $GITHUB_REPO $REPO_DEST"
                exit 1
            fi

            # Update INSTALLER_DIR to point to downloaded repo
            INSTALLER_DIR="$REPO_DEST/installer"
            print_success "Repository downloaded to $REPO_DEST"
        fi

        if [ ! -d "$INSTALLER_DIR" ]; then
            print_error "Downloaded repository structure not as expected"
            exit 1
        fi
    fi
}

# Detect project context by finding .claude/ directory
# Sets PROJECT_ROOT if found
# Returns 0 (found) or 1 (not found)
detect_project_context() {
    local current_dir="$PWD"
    local max_depth=10
    local depth=0

    while [ "$depth" -lt "$max_depth" ]; do
        if [ -d "$current_dir/.claude" ]; then
            PROJECT_ROOT="$current_dir"
            return 0
        fi

        # Stop at filesystem root
        if [ "$current_dir" = "/" ]; then
            break
        fi

        # Move up one directory
        current_dir="$(dirname "$current_dir")"
        depth=$((depth + 1))
    done

    # Not found
    PROJECT_ROOT=""
    return 1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check for required commands
    for cmd in git curl bash; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done
    
    # Check for Node.js (optional but recommended)
    if ! command -v node &> /dev/null; then
        print_warning "Node.js not found. Some features may be limited."
    else
        print_success "Node.js found: $(node --version)"
    fi
    
    # Check for Python (REQUIRED for complexity evaluation and task splitting)
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.10+ is REQUIRED for GuardKit"
        echo ""
        print_info "Install Python using one of these methods:"
        echo ""
        echo "  1. Official Installer (Recommended - easiest)"
        echo "     Download from: https://www.python.org/downloads/"
        echo "     Run the installer, then restart your terminal"
        echo ""
        echo "  2. Homebrew (if already installed)"
        echo "     brew install python@3.13"
        echo ""
        echo "  3. pyenv (for developers managing multiple versions)"
        echo "     curl https://pyenv.run | bash"
        echo "     pyenv install 3.13 && pyenv global 3.13"
        echo "     Note: Requires shell configuration - see pyenv docs"
        echo ""
        missing_deps+=("python3")
    else
        # Check Python version
        python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        python_major=$(echo $python_version | cut -d. -f1)
        python_minor=$(echo $python_version | cut -d. -f2)

        if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 10 ]); then
            print_error "Python 3.10+ is required (found: Python $python_version)"
            echo ""
            print_info "Upgrade Python using one of these methods:"
            echo ""
            echo "  1. Official Installer (Recommended - easiest)"
            echo "     Download from: https://www.python.org/downloads/"
            echo "     Run the installer, then restart your terminal"
            echo ""
            echo "  2. Homebrew"
            echo "     brew install python@3.13 && brew link python@3.13"
            echo ""
            echo "  3. pyenv"
            echo "     pyenv install 3.13 && pyenv global 3.13"
            echo ""
            missing_deps+=("python3.10+")
        else
            print_success "Python found: Python $python_version (>= 3.10 required)"

            # Check for pip (needed for Jinja2, python-frontmatter, pydantic)
            if ! command -v pip3 &> /dev/null; then
                print_warning "pip3 not found - Python packages (Jinja2, python-frontmatter, pydantic) may need manual installation"
                print_info "Install with: python3 -m ensurepip or use your package manager"
            else
                print_success "pip3 found - can install Python dependencies"

                # Check if Jinja2 and python-frontmatter are installed
                print_info "Checking for Jinja2..."
                set +e  # Temporarily allow errors for package checks
                python3 -c "import jinja2" </dev/null 2>&1 >/dev/null
                jinja2_status=$?
                set -e  # Re-enable exit on error
                print_info "Jinja2 check completed (status: $jinja2_status)"

                if [ $jinja2_status -ne 0 ]; then
                    print_info "Installing Jinja2 (required for plan markdown rendering)..."
                    print_info "This may take a moment, please wait..."
                    # Try with --break-system-packages for PEP 668 compatibility (Python 3.11+)
                    set +e  # Temporarily allow errors
                    pip3 install --break-system-packages Jinja2 2>&1
                    if [ $? -ne 0 ]; then
                        # Fallback to user install if --break-system-packages not supported
                        print_info "Retrying with --user flag..."
                        pip3 install --user Jinja2 2>&1
                        if [ $? -ne 0 ]; then
                            print_warning "Failed to install Jinja2 - install manually with: pip3 install --user Jinja2"
                        else
                            print_success "Jinja2 installed successfully (user mode)"
                        fi
                    else
                        print_success "Jinja2 installed successfully"
                    fi
                    set -e  # Re-enable exit on error
                else
                    print_success "Jinja2 already installed"
                fi

                print_info "Checking for python-frontmatter..."
                set +e  # Temporarily allow errors for package checks
                python3 -c "import frontmatter" </dev/null 2>&1 >/dev/null
                frontmatter_status=$?
                set -e  # Re-enable exit on error
                print_info "python-frontmatter check completed (status: $frontmatter_status)"

                if [ $frontmatter_status -ne 0 ]; then
                    print_info "Installing python-frontmatter (required for plan metadata)..."
                    print_info "This may take a moment, please wait..."
                    # Try with --break-system-packages for PEP 668 compatibility (Python 3.11+)
                    set +e  # Temporarily allow errors
                    pip3 install --break-system-packages python-frontmatter 2>&1
                    if [ $? -ne 0 ]; then
                        # Fallback to user install if --break-system-packages not supported
                        print_info "Retrying with --user flag..."
                        pip3 install --user python-frontmatter 2>&1
                        if [ $? -ne 0 ]; then
                            print_warning "Failed to install python-frontmatter - install manually with: pip3 install --user python-frontmatter"
                        else
                            print_success "python-frontmatter installed successfully (user mode)"
                        fi
                    else
                        print_success "python-frontmatter installed successfully"
                    fi
                    set -e  # Re-enable exit on error
                else
                    print_success "python-frontmatter already installed"
                fi

                # Check and install pydantic (required for template creation)
                print_info "Checking for pydantic..."
                set +e  # Temporarily allow errors for package checks
                python3 -c "import pydantic" </dev/null 2>&1 >/dev/null
                pydantic_status=$?
                set -e  # Re-enable exit on error
                print_info "pydantic check completed (status: $pydantic_status)"

                if [ $pydantic_status -ne 0 ]; then
                    print_info "Installing pydantic (required for template creation)..."
                    print_info "This may take a moment, please wait..."
                    # Try with --break-system-packages for PEP 668 compatibility (Python 3.11+)
                    set +e  # Temporarily allow errors
                    pip3 install --break-system-packages pydantic 2>&1
                    if [ $? -ne 0 ]; then
                        # Fallback to user install if --break-system-packages not supported
                        print_info "Retrying with --user flag..."
                        pip3 install --user pydantic 2>&1
                        if [ $? -ne 0 ]; then
                            print_warning "Failed to install pydantic - install manually with: pip3 install --user pydantic"
                        else
                            print_success "pydantic installed successfully (user mode)"
                        fi
                    else
                        print_success "pydantic installed successfully"
                    fi
                    set -e  # Re-enable exit on error
                else
                    print_success "pydantic already installed"
                fi

                # Check and install python-dotenv (required for .env file loading)
                print_info "Checking for python-dotenv..."
                set +e  # Temporarily allow errors for package checks
                python3 -c "import dotenv" </dev/null 2>&1 >/dev/null
                dotenv_status=$?
                set -e  # Re-enable exit on error
                print_info "python-dotenv check completed (status: $dotenv_status)"

                if [ $dotenv_status -ne 0 ]; then
                    print_info "Installing python-dotenv (required for .env file loading)..."
                    print_info "This may take a moment, please wait..."
                    # Try with --break-system-packages for PEP 668 compatibility (Python 3.11+)
                    set +e  # Temporarily allow errors
                    pip3 install --break-system-packages python-dotenv 2>&1
                    if [ $? -ne 0 ]; then
                        # Fallback to user install if --break-system-packages not supported
                        print_info "Retrying with --user flag..."
                        pip3 install --user python-dotenv 2>&1
                        if [ $? -ne 0 ]; then
                            print_warning "Failed to install python-dotenv - install manually with: pip3 install --user python-dotenv"
                        else
                            print_success "python-dotenv installed successfully (user mode)"
                        fi
                    else
                        print_success "python-dotenv installed successfully"
                    fi
                    set -e  # Re-enable exit on error
                else
                    print_success "python-dotenv already installed"
                fi

                # Check and install graphiti-core (required for knowledge graph integration)
                print_info "Checking for graphiti-core..."
                set +e  # Temporarily allow errors for package checks
                python3 -c "from graphiti_core import Graphiti" </dev/null 2>&1 >/dev/null
                graphiti_status=$?
                set -e  # Re-enable exit on error
                print_info "graphiti-core check completed (status: $graphiti_status)"

                if [ $graphiti_status -ne 0 ]; then
                    print_info "Installing graphiti-core (required for knowledge graph integration)..."
                    print_info "This may take a moment, please wait..."
                    # Try with --break-system-packages for PEP 668 compatibility (Python 3.11+)
                    # Use python3 -m pip for reliability with multiple Python installations
                    set +e  # Temporarily allow errors
                    python3 -m pip install --break-system-packages graphiti-core 2>&1
                    if [ $? -ne 0 ]; then
                        # Fallback to user install if --break-system-packages not supported
                        print_info "Retrying with --user flag..."
                        python3 -m pip install --user graphiti-core 2>&1
                        if [ $? -ne 0 ]; then
                            print_warning "Failed to install graphiti-core - install manually with: python3 -m pip install --user graphiti-core"
                        else
                            print_success "graphiti-core installed successfully (user mode)"
                        fi
                    else
                        print_success "graphiti-core installed successfully"
                    fi
                    set -e  # Re-enable exit on error
                else
                    print_success "graphiti-core already installed"
                fi

                print_success "Python dependency checks complete"
            fi
        fi
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_info "Please install missing dependencies and try again."
        exit 1
    fi
    
    print_success "All required prerequisites met"
}

# Install guardkit Python package
install_python_package() {
    print_info "Installing guardkit Python package (with AutoBuild support)..."

    # Get repository root (parent of installer/)
    local repo_root="$(cd "$INSTALLER_DIR/.." && pwd)"

    # Check if we're in the guardkit repository
    if [ ! -f "$repo_root/pyproject.toml" ]; then
        print_warning "pyproject.toml not found at $repo_root"
        print_warning "Skipping Python package installation"
        return 0
    fi

    # Check if python3 with pip module is available (more reliable than pip3 command)
    if ! python3 -m pip --version &> /dev/null; then
        print_warning "python3 -m pip not available - cannot install guardkit package"
        print_info "The guardkit autobuild command will not be available"
        print_info "Install pip with: python3 -m ensurepip"
        return 0
    fi

    print_info "Installing from: $repo_root"

    # Install with [autobuild] extras to include claude-agent-sdk
    # Try installing with --break-system-packages (PEP 668 compliance for Python 3.11+)
    set +e  # Temporarily allow errors
    python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages 2>&1
    local install_status=$?
    set -e  # Re-enable exit on error

    if [ $install_status -ne 0 ]; then
        # Fallback to --user install
        print_info "Retrying with --user flag..."
        set +e
        python3 -m pip install -e "$repo_root[autobuild]" --user 2>&1
        install_status=$?
        set -e

        if [ $install_status -eq 0 ]; then
            print_success "guardkit package installed successfully (user mode, with AutoBuild)"
        else
            print_warning "Failed to install guardkit package"
            print_info "AutoBuild CLI will not be available"
            print_info "You can install manually with: python3 -m pip install -e \"$repo_root[autobuild]\""
            return 0
        fi
    else
        print_success "guardkit package installed successfully (with AutoBuild)"
    fi

    # Verify installation
    set +e
    python3 -c "import guardkit" 2>/dev/null
    local import_status=$?
    set -e

    if [ $import_status -eq 0 ]; then
        print_success "guardkit Python package is importable"
    else
        print_warning "guardkit package installed but not importable"
        print_info "You may need to restart your shell"
    fi

    # Verify Claude Agent SDK is available (for AutoBuild features)
    set +e
    python3 -c "import claude_agent_sdk" 2>/dev/null
    local sdk_status=$?
    set -e

    if [ $sdk_status -eq 0 ]; then
        print_success "Claude Agent SDK is available (AutoBuild ready)"
    else
        print_warning "Claude Agent SDK not importable"
        print_info "AutoBuild features require the SDK. Install with:"
        print_info "  pip install claude-agent-sdk"
        print_info "  # OR reinstall guardkit with: pip install guardkit-py[autobuild]"
    fi

    # Check if guardkit-py CLI is available
    if command -v guardkit-py &> /dev/null; then
        print_success "guardkit-py CLI command is available"
    else
        # Try to find it via Python
        set +e
        local cli_path=$(python3 -c "import shutil; p=shutil.which('guardkit-py'); print(p if p else '')" 2>/dev/null)
        set -e
        if [ -n "$cli_path" ]; then
            print_success "guardkit-py CLI found at: $cli_path"
        else
            print_warning "guardkit-py CLI not found in PATH"
            print_info "You may need to restart your shell or add ~/.local/bin to PATH"
        fi
    fi
}

# Backup existing installation
backup_existing() {
    # Check for any existing installations
    local existing_dirs=()

    [ -d "$HOME/.agentecflow" ] && existing_dirs+=(".agentecflow")
    [ -d "$HOME/.agenticflow" ] && existing_dirs+=(".agenticflow")
    [ -d "$HOME/.agentic-flow" ] && existing_dirs+=(".agentic-flow")
    [ -d "$HOME/.claude" ] && existing_dirs+=(".claude")
    
    if [ ${#existing_dirs[@]} -gt 0 ]; then
        print_warning "Found existing installations: ${existing_dirs[*]}"
        
        for dir in "${existing_dirs[@]}"; do
            local full_path="$HOME/$dir"
            local backup_dir="${full_path}.backup.$(date +%Y%m%d_%H%M%S)"
            print_info "Creating backup of $dir at $backup_dir"
            mv "$full_path" "$backup_dir"
            print_success "Backup created: $backup_dir"
        done
    fi
}

# Create complete directory structure matching Product Owner's setup
create_directories() {
    print_info "Creating complete directory structure..."
    
    # Create all directories that Product Owner has
    mkdir -p "$INSTALL_DIR"/{agents,bin,cache,commands,completions,docs,instructions,plugins,scripts,templates,versions}

    # Create project management directories
    mkdir -p "$INSTALL_DIR/project-templates"/{tasks,portfolio}
    
    # Create sub-directories for instructions
    mkdir -p "$INSTALL_DIR/instructions"/{core,stacks}
    
    # Create sub-directories for templates
    mkdir -p "$INSTALL_DIR/templates"/{default,react-typescript,fastapi-python,nextjs-fullstack,react-fastapi-monorepo}
    
    # Create versions structure
    mkdir -p "$INSTALL_DIR/versions/$AGENTICFLOW_VERSION"
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    print_success "Complete directory structure created"
}

# Copy and organize global files
install_global_files() {
    print_info "Installing global files..."
    
    # Copy instructions
    if [ -d "$INSTALLER_DIR/core/instructions" ]; then
        cp -r "$INSTALLER_DIR/core/instructions/"* "$INSTALL_DIR/instructions/" 2>/dev/null || true
        print_success "Installed methodology instructions"
    fi
    
    # Copy templates with complete structure
    if [ -d "$INSTALLER_DIR/core/templates" ]; then
        for template_dir in "$INSTALLER_DIR/core/templates"/*; do
            if [ -d "$template_dir" ]; then
                local template_name=$(basename "$template_dir")
                cp -r "$template_dir" "$INSTALL_DIR/templates/" 2>/dev/null || true
                
                # Ensure each template has agents directory
                mkdir -p "$INSTALL_DIR/templates/$template_name/agents"
            fi
        done
        print_success "Installed project templates"
    fi
    
    # Copy Python libraries from installer/core/lib (for imports like 'from lib.id_generator')
    if [ -d "$INSTALLER_DIR/core/lib" ]; then
        mkdir -p "$INSTALL_DIR/commands/lib"

        # Copy Python production files only (exclude test_*, cache, coverage)
        find "$INSTALLER_DIR/core/lib" \
            -maxdepth 1 \
            -type f \
            -name "*.py" \
            ! -name "test_*" \
            ! -name "*_test.py" \
            -exec cp {} "$INSTALL_DIR/commands/lib/" \; 2>/dev/null || true

        # Copy subdirectories (like mcp/) with their Python files
        for subdir in "$INSTALLER_DIR/core/lib"/*/ ; do
            if [ -d "$subdir" ]; then
                subdir_name=$(basename "$subdir")
                # Skip test directories and cache
                if [[ ! "$subdir_name" =~ ^(tests?|__pycache__|\.pytest_cache)$ ]]; then
                    mkdir -p "$INSTALL_DIR/commands/lib/$subdir_name"
                    find "$subdir" \
                        -type f \
                        -name "*.py" \
                        ! -name "test_*" \
                        ! -name "*_test.py" \
                        -exec cp {} "$INSTALL_DIR/commands/lib/$subdir_name/" \; 2>/dev/null || true
                fi
            fi
        done

        local global_lib_count=$(find "$INSTALL_DIR/commands/lib" -name "*.py" 2>/dev/null | wc -l)
        print_success "Installed global Python libraries ($global_lib_count modules)"
    fi

    # Copy commands
    if [ -d "$INSTALLER_DIR/core/commands" ]; then
        # Copy markdown command files
        find "$INSTALLER_DIR/core/commands" -maxdepth 1 -name "*.md" -exec cp {} "$INSTALL_DIR/commands/" \; 2>/dev/null || true

        # Copy lib directory (excluding test files, cache, and artifacts)
        if [ -d "$INSTALLER_DIR/core/commands/lib" ]; then
            mkdir -p "$INSTALL_DIR/commands/lib"

            # Copy Python production files only (exclude test_*, cache, coverage)
            find "$INSTALLER_DIR/core/commands/lib" \
                -maxdepth 1 \
                -type f \
                -name "*.py" \
                ! -name "test_*" \
                ! -name "*_test.py" \
                -exec cp {} "$INSTALL_DIR/commands/lib/" \; 2>/dev/null || true

            # Copy documentation files (README, API docs)
            find "$INSTALLER_DIR/core/commands/lib" \
                -maxdepth 1 \
                -type f \
                -name "*.md" \
                ! -name "TASK-*.md" \
                -exec cp {} "$INSTALL_DIR/commands/lib/" \; 2>/dev/null || true

            # Copy templates directory (for Jinja2 templates)
            if [ -d "$INSTALLER_DIR/core/commands/lib/templates" ]; then
                cp -r "$INSTALLER_DIR/core/commands/lib/templates" "$INSTALL_DIR/commands/lib/" 2>/dev/null || true
                print_success "Installed Jinja2 templates for plan rendering"
            fi

            # Copy review_modes directory (for task-review command)
            if [ -d "$INSTALLER_DIR/core/commands/lib/review_modes" ]; then
                cp -r "$INSTALLER_DIR/core/commands/lib/review_modes" "$INSTALL_DIR/commands/lib/" 2>/dev/null || true
                print_success "Installed review_modes for task-review command"
            fi

            # Copy review_templates directory (for task-review command)
            if [ -d "$INSTALLER_DIR/core/commands/lib/review_templates" ]; then
                cp -r "$INSTALLER_DIR/core/commands/lib/review_templates" "$INSTALL_DIR/commands/lib/" 2>/dev/null || true
                print_success "Installed review_templates for task-review command"
            fi

            # Count installed Python files
            local python_count=$(ls -1 "$INSTALL_DIR/commands/lib/"*.py 2>/dev/null | wc -l)
            print_success "Installed commands with lib ($python_count Python modules, production only)"
        else
            print_success "Installed commands"
        fi
    fi
    
    # Copy documentation
    if [ -d "$INSTALLER_DIR/core/docs" ]; then
        cp -r "$INSTALLER_DIR/core/docs/"* "$INSTALL_DIR/docs/" 2>/dev/null || true
        print_success "Installed documentation"
    fi
    
    # Copy the initialization script
    if [ -f "$INSTALLER_DIR/scripts/init-project.sh" ]; then
        cp "$INSTALLER_DIR/scripts/init-project.sh" "$INSTALL_DIR/scripts/init-project.sh"
        chmod +x "$INSTALL_DIR/scripts/init-project.sh"
        print_success "Installed initialization script"
    fi
    
    print_success "Global files installed"
}

# Install global agents (comprehensive agent ecosystem)
install_global_agents() {
    print_info "Installing global AI agents..."

    # Ensure agents directory exists
    mkdir -p "$INSTALL_DIR/agents"

    # Install core global agents first
    if [ -d "$INSTALLER_DIR/core/agents" ] && [ "$(ls -A $INSTALLER_DIR/core/agents)" ]; then
        cp -r "$INSTALLER_DIR/core/agents/"* "$INSTALL_DIR/agents/" 2>/dev/null || true
        print_success "Installed core global agents"
    fi

    # Copy clarification-questioner agent (explicit for clarity)
    if [ -f "$INSTALLER_DIR/core/agents/clarification-questioner.md" ]; then
        cp "$INSTALLER_DIR/core/agents/clarification-questioner.md" \
           "$INSTALL_DIR/agents/"
        print_success "  ✓ Installed clarification-questioner agent"
    else
        print_warning "  ⚠ Warning: clarification-questioner.md not found"
    fi

    # Install stack-specific agents to global location for template copying
    for template_dir in "$INSTALLER_DIR/core/templates"/*; do
        if [ -d "$template_dir/agents" ] && [ "$(ls -A $template_dir/agents)" ]; then
            local template_name=$(basename "$template_dir")
            mkdir -p "$INSTALL_DIR/stack-agents/$template_name"
            cp -r "$template_dir/agents/"* "$INSTALL_DIR/stack-agents/$template_name/" 2>/dev/null || true
            print_success "Installed $template_name stack agents"
        fi
    done

    # Count total agents
    local global_agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
    local stack_agent_count=$(find "$INSTALL_DIR/stack-agents" -name "*.md" 2>/dev/null | wc -l)
    local total_agents=$((global_agent_count + stack_agent_count))

    if [ $total_agents -gt 0 ]; then
        print_success "Installed $total_agents total agents ($global_agent_count global + $stack_agent_count stack-specific)"

        # List the global agents
        if [ $global_agent_count -gt 0 ]; then
            echo "  Global agents:"
            for agent in "$INSTALL_DIR/agents/"*.md; do
                if [ -f "$agent" ]; then
                    echo "    - $(basename "$agent" .md)"
                fi
            done
        fi
    else
        print_warning "No agents found to install"
        print_info "Creating placeholder agents..."
        
        # Create the 4 core agents as placeholders if they don't exist
        cat > "$INSTALL_DIR/agents/requirements-analyst.md" << 'EOF'
---
name: requirements-analyst
description: Specialist in gathering and formalizing requirements using EARS notation
tools: Read, Write, Search
model: sonnet
---

You are a requirements engineering specialist focused on EARS notation.

## Your Responsibilities
1. Gather requirements through structured Q&A
2. Formalize requirements using EARS patterns
3. Validate completeness and clarity
4. Maintain traceability

## EARS Patterns
- Ubiquitous: "The [system] shall [behavior]"
- Event-driven: "When [trigger], the [system] shall [response]"
- State-driven: "While [condition], the [system] shall [behavior]"
- Unwanted: "If [error], then the [system] shall [recovery]"
- Optional: "Where [feature], the [system] shall [behavior]"
EOF

        cat > "$INSTALL_DIR/agents/bdd-generator.md" << 'EOF'
---
name: bdd-generator
description: Converts EARS requirements to BDD/Gherkin scenarios
tools: Read, Write, Generate
model: sonnet
---

You are a BDD specialist who converts EARS requirements to Gherkin scenarios.

## Your Responsibilities
1. Analyze EARS requirements
2. Generate comprehensive BDD scenarios
3. Ensure testability
4. Maintain requirement traceability

## Gherkin Format
Feature: [Feature Name]
  Scenario: [Scenario Description]
    Given [initial context]
    When [action or event]
    Then [expected outcome]
EOF

        cat > "$INSTALL_DIR/agents/code-reviewer.md" << 'EOF'
---
name: code-reviewer
description: Reviews code for quality, standards, and best practices
tools: Read, Analyze, Comment
model: sonnet
---

You are a code quality specialist focused on standards and best practices.

## Your Responsibilities
1. Review code changes for quality
2. Check adherence to patterns
3. Validate test coverage
4. Ensure documentation
EOF

        cat > "$INSTALL_DIR/agents/test-orchestrator.md" << 'EOF'
---
name: test-orchestrator
description: Manages test execution and quality gates
tools: Execute, Analyze, Report
model: sonnet
---

You are a test orchestration specialist managing quality gates.

## Your Responsibilities
1. Determine which tests to run
2. Execute test suites
3. Validate quality gates
4. Generate test reports
EOF
        
        print_success "Created core placeholder agents"
    fi

    # Create stack-agents directory structure even if no agents
    mkdir -p "$INSTALL_DIR/stack-agents"/{default,react-typescript,fastapi-python,nextjs-fullstack,react-fastapi-monorepo}
}

# Create the main CLI executables
create_cli_commands() {
    print_info "Creating CLI commands..."
    
    # Create guardkit-init command (primary command)
    cat > "$INSTALL_DIR/bin/guardkit-init" << 'EOF'
#!/bin/bash

# GuardKit Project Initialization
# Primary command for initializing projects

AGENTECFLOW_HOME="$HOME/.agentecflow"
PROJECT_DIR="$(pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_help() {
    echo "GuardKit Project Initialization"
    echo ""
    echo "Usage: guardkit-init [template]"
    echo ""
    echo "Templates:"
    echo "  default              - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)"
    echo "  react-typescript     - React frontend with feature-based architecture (9+/10)"
    echo "  fastapi-python       - FastAPI backend with layered architecture (9+/10)"
    echo "  nextjs-fullstack     - Next.js App Router full-stack (9+/10)"
    echo "  react-fastapi-monorepo - React + FastAPI monorepo with type safety (9.2/10)"
    echo ""
    echo "Examples:"
    echo "  guardkit-init                     # Interactive setup"
    echo "  guardkit-init react-typescript    # Initialize with React template"
    echo "  guardkit-init fastapi-python      # Initialize with FastAPI template"
}

if [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    print_help
    exit 0
fi

# Check if GuardKit is installed
if [ ! -d "$AGENTECFLOW_HOME" ]; then
    echo -e "${RED}Error: GuardKit not installed at $AGENTECFLOW_HOME${NC}"
    echo "Please run the installer first"
    exit 1
fi

# Run the initialization script
if [ -f "$AGENTECFLOW_HOME/scripts/init-project.sh" ]; then
    # Set environment variable for the init script
    export CLAUDE_HOME="$AGENTECFLOW_HOME"
    exec "$AGENTECFLOW_HOME/scripts/init-project.sh" "$@"
else
    echo -e "${RED}Error: Initialization script not found${NC}"
    echo "Looking for: $AGENTECFLOW_HOME/scripts/init-project.sh"
    exit 1
fi
EOF

    chmod +x "$INSTALL_DIR/bin/guardkit-init"
    print_success "Created guardkit-init command"

    # Create guardkit main command
    cat > "$INSTALL_DIR/bin/guardkit" << 'EOF'
#!/bin/bash

# GuardKit CLI
# Main command-line interface for GuardKit

AGENTECFLOW_HOME="$HOME/.agentecflow"
AGENTECFLOW_VERSION="1.0.0"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_help() {
    echo "GuardKit - Lightweight AI-Assisted Development"
    echo ""
    echo "Usage: guardkit <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init [template]     Initialize GuardKit in current directory"
    echo "  autobuild <cmd>     Autonomous task implementation (Player-Coach)"
    echo "  graphiti <cmd>      Knowledge graph management"
    echo "  doctor              Check system health and configuration"
    echo "  version             Show version information"
    echo "  help                Show this help message"
    echo ""
    echo "AutoBuild Commands:"
    echo "  autobuild task TASK-XXX     Execute Player-Coach loop for a task"
    echo "  autobuild status TASK-XXX   Check worktree status"
    echo ""
    echo "Graphiti Commands:"
    echo "  graphiti status             Show connection and seeding status"
    echo "  graphiti seed [--force]     Seed system context into Graphiti"
    echo "  graphiti verify [--verbose] Verify seeded knowledge with test queries"
    echo "  graphiti seed-adrs          Seed feature-build ADRs"
    echo ""
    echo "Examples:"
    echo "  guardkit init                      # Interactive initialization"
    echo "  guardkit init react-typescript     # Initialize with React template"
    echo "  guardkit init fastapi-python       # Initialize with FastAPI template"
    echo "  guardkit autobuild task TASK-001   # Autonomous task implementation"
    echo "  guardkit graphiti status           # Check Graphiti connection"
    echo "  guardkit doctor                    # Check installation health"
}

# Detect project context by traversing upward
detect_project_context() {
    local current_dir="$PWD"
    local max_depth=10
    local depth=0

    while [ "$depth" -lt "$max_depth" ]; do
        if [ -d "$current_dir/.claude" ]; then
            PROJECT_ROOT="$current_dir"
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

case "$1" in
    init)
        shift
        export CLAUDE_HOME="$AGENTECFLOW_HOME"
        exec "$AGENTECFLOW_HOME/bin/guardkit-init" "$@"
        ;;
    autobuild)
        # Find guardkit-py CLI - resolve to full path for reliable -x test
        GUARDKIT_PY=""
        if command -v guardkit-py &> /dev/null; then
            # Resolve to full path (fixes bug where -x test fails on command name)
            GUARDKIT_PY="$(command -v guardkit-py)"
        elif [ -x "/Library/Frameworks/Python.framework/Versions/Current/bin/guardkit-py" ]; then
            GUARDKIT_PY="/Library/Frameworks/Python.framework/Versions/Current/bin/guardkit-py"
        elif [ -x "$HOME/.local/bin/guardkit-py" ]; then
            GUARDKIT_PY="$HOME/.local/bin/guardkit-py"
        elif [ -x "/usr/local/bin/guardkit-py" ]; then
            GUARDKIT_PY="/usr/local/bin/guardkit-py"
        else
            # Try to find it via Python
            GUARDKIT_PY=$(python3 -c "import shutil; p=shutil.which('guardkit-py'); print(p if p else '')" 2>/dev/null)
        fi

        if [ -n "$GUARDKIT_PY" ] && [ -x "$GUARDKIT_PY" ]; then
            shift  # Remove 'autobuild' from args
            exec "$GUARDKIT_PY" autobuild "$@"
        else
            # Python CLI not installed - show guidance
            echo -e "${YELLOW}AutoBuild CLI requires guardkit-py package${NC}"
            echo ""
            echo "The guardkit autobuild command requires the guardkit Python package."
            echo ""
            echo "To install:"
            echo "  pip install -e /path/to/guardkit  # From guardkit repository"
            echo ""
            echo "Or use the /feature-build slash command in Claude Code instead."
            echo "It uses Task tool agents when the CLI is not available."
            echo ""
            echo "Example:"
            echo "  /feature-build TASK-XXX"
            echo "  /feature-build FEAT-XXX"
            exit 1
        fi
        ;;
    graphiti)
        # Find guardkit-py CLI - same logic as autobuild
        GUARDKIT_PY=""
        if command -v guardkit-py &> /dev/null; then
            GUARDKIT_PY="$(command -v guardkit-py)"
        elif [ -x "/Library/Frameworks/Python.framework/Versions/Current/bin/guardkit-py" ]; then
            GUARDKIT_PY="/Library/Frameworks/Python.framework/Versions/Current/bin/guardkit-py"
        elif [ -x "$HOME/.local/bin/guardkit-py" ]; then
            GUARDKIT_PY="$HOME/.local/bin/guardkit-py"
        elif [ -x "/usr/local/bin/guardkit-py" ]; then
            GUARDKIT_PY="/usr/local/bin/guardkit-py"
        else
            # Try to find it via Python
            GUARDKIT_PY=$(python3 -c "import shutil; p=shutil.which('guardkit-py'); print(p if p else '')" 2>/dev/null)
        fi

        if [ -n "$GUARDKIT_PY" ] && [ -x "$GUARDKIT_PY" ]; then
            shift  # Remove 'graphiti' from args
            exec "$GUARDKIT_PY" graphiti "$@"
        else
            # Python CLI not installed - show guidance
            echo -e "${YELLOW}Graphiti CLI requires guardkit-py package${NC}"
            echo ""
            echo "The guardkit graphiti command requires the guardkit Python package."
            echo ""
            echo "To install:"
            echo "  pip install -e /path/to/guardkit[autobuild]  # From guardkit repository"
            echo ""
            echo "Or install directly:"
            echo "  pip install guardkit-py[autobuild]"
            exit 1
        fi
        ;;
    doctor)
        echo -e "${BLUE}Running GuardKit diagnostics...${NC}"
        echo ""

        # Check installation
        echo "Installation:"
        if [ -d "$AGENTECFLOW_HOME" ]; then
            echo -e "  ${GREEN}✓${NC} GuardKit home: $AGENTECFLOW_HOME"

            # Check key directories
            for dir in agents bin cache commands completions docs instructions plugins scripts templates versions; do
                if [ -d "$AGENTECFLOW_HOME/$dir" ]; then
                    echo -e "  ${GREEN}✓${NC} Directory $dir exists"
                else
                    echo -e "  ${RED}✗${NC} Directory $dir missing"
                fi
            done
        else
            echo -e "  ${RED}✗${NC} GuardKit home not found"
        fi

        # Check agents
        echo ""
        echo "AI Agents:"
        if [ -d "$AGENTECFLOW_HOME/agents" ]; then
            agent_count=$(ls -1 "$AGENTECFLOW_HOME/agents/"*.md 2>/dev/null | wc -l)
            if [ "$agent_count" -ge 4 ]; then
                echo -e "  ${GREEN}✓${NC} $agent_count agents installed"
            else
                echo -e "  ${YELLOW}⚠${NC} Only $agent_count agents found (expected 4+)"
            fi
        fi

        # Check PATH
        echo ""
        echo "PATH Configuration:"
        if [[ ":$PATH:" == *":$AGENTECFLOW_HOME/bin:"* ]]; then
            echo -e "  ${GREEN}✓${NC} GuardKit bin in PATH"
        else
            echo -e "  ${YELLOW}⚠${NC} Add to PATH: export PATH=\"\$HOME/.agentecflow/bin:\$PATH\""
        fi

        # Check Claude Code integration
        echo ""
        echo "Claude Code Integration:"
        if [ -L "$HOME/.claude/commands" ]; then
            target=$(readlink "$HOME/.claude/commands")
            if [ "$target" = "$AGENTECFLOW_HOME/commands" ]; then
                echo -e "  ${GREEN}✓${NC} Commands symlinked correctly"
            else
                echo -e "  ${YELLOW}⚠${NC} Commands symlinked to unexpected location: $target"
            fi
        elif [ -d "$HOME/.claude/commands" ]; then
            echo -e "  ${YELLOW}⚠${NC} Commands directory exists but is not symlinked"
            echo -e "      Run installer again to create symlink"
        else
            echo -e "  ${RED}✗${NC} Commands not configured for Claude Code"
        fi

        if [ -L "$HOME/.claude/agents" ]; then
            target=$(readlink "$HOME/.claude/agents")
            if [ "$target" = "$AGENTECFLOW_HOME/agents" ]; then
                echo -e "  ${GREEN}✓${NC} Agents symlinked correctly"
            else
                echo -e "  ${YELLOW}⚠${NC} Agents symlinked to unexpected location: $target"
            fi
        elif [ -d "$HOME/.claude/agents" ]; then
            echo -e "  ${YELLOW}⚠${NC} Agents directory exists but is not symlinked"
            echo -e "      Run installer again to create symlink"
        else
            echo -e "  ${RED}✗${NC} Agents not configured for Claude Code"
        fi

        if [ -L "$HOME/.claude/commands" ] && [ -L "$HOME/.claude/agents" ]; then
            echo -e "  ${GREEN}✓${NC} Compatible with Conductor.build for parallel development"
        fi

        # Check for local project templates
        echo ""
        echo "Local Templates:"
        PROJECT_ROOT=""
        if detect_project_context; then
            echo -e "  ${GREEN}✓${NC} Project context found: $PROJECT_ROOT"

            if [ -d "$PROJECT_ROOT/.claude/templates" ]; then
                local_template_count=$(ls -1d "$PROJECT_ROOT/.claude/templates"/*/ 2>/dev/null | wc -l)
                if [ "$local_template_count" -gt 0 ]; then
                    echo -e "  ${GREEN}✓${NC} $local_template_count local templates available"
                    echo ""
                    echo "  Available local templates:"
                    for template_dir in "$PROJECT_ROOT/.claude/templates"/*; do
                        if [ -d "$template_dir" ]; then
                            name=$(basename "$template_dir")
                            # Validate template structure
                            valid="${GREEN}✓${NC}"
                            status="valid"
                            if [ ! -f "$template_dir/CLAUDE.md" ]; then
                                valid="${RED}✗${NC}"
                                status="missing CLAUDE.md"
                            elif [ ! -d "$template_dir/agents" ]; then
                                valid="${RED}✗${NC}"
                                status="missing agents/"
                            elif [ ! -d "$template_dir/templates" ]; then
                                valid="${RED}✗${NC}"
                                status="missing templates/"
                            fi
                            echo -e "    $valid $name ($status)"
                        fi
                    done
                else
                    echo -e "  ${YELLOW}⚠${NC} No local templates found"
                fi
            else
                echo -e "  ${YELLOW}⚠${NC} No .claude/templates/ directory"
            fi

            echo ""
            echo "  Template resolution order:"
            echo "    1. Local (.claude/templates/) [HIGHEST PRIORITY]"
            echo "    2. Global (~/.agentecflow/templates/)"
            echo "    3. Default (CLAUDE_HOME/templates/) [LOWEST PRIORITY]"
        else
            echo -e "  ${BLUE}ℹ${NC} Not in a project directory"
            echo -e "      Run this command from a project initialized with guardkit-init"
        fi
        ;;
    version|--version|-v)
        echo "GuardKit version $AGENTECFLOW_VERSION"
        echo "Installation: $AGENTECFLOW_HOME"
        ;;
    help|--help|-h|"")
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run 'guardkit help' for usage information"
        exit 1
        ;;
esac
EOF

    chmod +x "$INSTALL_DIR/bin/guardkit"

    # Create shorthand aliases
    ln -sf "$INSTALL_DIR/bin/guardkit" "$INSTALL_DIR/bin/gk"
    ln -sf "$INSTALL_DIR/bin/guardkit-init" "$INSTALL_DIR/bin/gki"

    print_success "Created CLI commands (guardkit, guardkit-init, gk, gki)"
}

# Setup shell integration
setup_shell_integration() {
    print_info "Setting up shell integration..."

    local shell_config=""
    local shell_name=""

    # Enhanced shell detection
    if [ -n "$ZSH_VERSION" ] || [ -n "$ZSH_NAME" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
        shell_name="zsh"
        shell_config="$HOME/.zshrc"
        print_info "Detected zsh shell"
    elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
        shell_name="bash"
        print_info "Detected bash shell"
        if [ -f "$HOME/.bashrc" ]; then
            shell_config="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            shell_config="$HOME/.bash_profile"
        elif [ "$(uname)" = "Darwin" ]; then
            # macOS defaults to .bash_profile
            shell_config="$HOME/.bash_profile"
        else
            # Linux defaults to .bashrc
            shell_config="$HOME/.bashrc"
        fi
    else
        # Try to detect from SHELL environment variable
        case "$SHELL" in
            */zsh)
                shell_name="zsh"
                shell_config="$HOME/.zshrc"
                print_info "Detected zsh from SHELL variable"
                ;;
            */bash)
                shell_name="bash"
                shell_config="$HOME/.bashrc"
                print_info "Detected bash from SHELL variable"
                ;;
            *)
                shell_name="unknown"
                print_warning "Unknown shell: $SHELL"
                ;;
        esac
    fi
    
    if [ -z "$shell_config" ]; then
        print_warning "Could not detect shell configuration file"
        print_info "Please add the following to your shell configuration manually:"
        echo "    export PATH=\"\$HOME/.agentecflow/bin:\$PATH\""
        echo "    export AGENTECFLOW_HOME=\"\$HOME/.agentecflow\""
        return
    fi

    # Remove old configurations if they exist
    if grep -q "\.agenticflow\|\.agentic-flow\|\.claude\|CLAUDE_HOME\|AGENTIC_FLOW_HOME\|AGENTICFLOW_HOME" "$shell_config" 2>/dev/null; then
        print_info "Removing old GuardKit configurations..."
        # Create backup
        cp "$shell_config" "$shell_config.backup.$(date +%Y%m%d_%H%M%S)"

        # Use sed to remove entire configuration blocks (comments + code + fi)
        # This prevents orphaned 'fi' statements
        sed -i.bak '/# Agentic Flow/,/^fi$/d; /# Agentecflow/,/^fi$/d' "$shell_config" 2>/dev/null || \
        sed -i '' '/# Agentic Flow/,/^fi$/d; /# Agentecflow/,/^fi$/d' "$shell_config" 2>/dev/null || \
        {
            # Fallback: Remove individual lines but also check for orphaned fi
            grep -v "\.agenticflow\|\.agentic-flow\|\.claude\|CLAUDE_HOME\|AGENTIC_FLOW_HOME\|AGENTICFLOW_HOME" "$shell_config" > "$shell_config.tmp"
            # Remove orphaned 'fi' that appears after removed 'if' statements
            awk '
                /^# Agentic Flow/ { in_block=1; next }
                /^# Agentecflow/ { in_block=1; next }
                in_block && /^fi$/ { in_block=0; next }
                !in_block { print }
            ' "$shell_config.tmp" > "$shell_config.tmp2"
            mv "$shell_config.tmp2" "$shell_config"
            rm -f "$shell_config.tmp"
        }
    fi

    # Check if already configured correctly
    if grep -q "\.agentecflow/bin" "$shell_config" 2>/dev/null; then
        print_info "Shell integration already configured"
        return
    fi

    # Add to shell configuration with shell-specific completions
    if [ "$shell_name" = "bash" ]; then
        cat >> "$shell_config" << 'EOF'

# GuardKit
export PATH="$HOME/.agentecflow/bin:$PATH"
export AGENTECFLOW_HOME="$HOME/.agentecflow"
# Note: Config folder stays .agentecflow for methodology compatibility

# GuardKit completions (bash)
if [ -f "$HOME/.agentecflow/completions/guardkit.bash" ]; then
    source "$HOME/.agentecflow/completions/guardkit.bash"
fi
EOF
    else
        # For zsh or other shells, skip bash completions
        cat >> "$shell_config" << 'EOF'

# GuardKit
export PATH="$HOME/.agentecflow/bin:$PATH"
export AGENTECFLOW_HOME="$HOME/.agentecflow"
# Note: Config folder stays .agentecflow for methodology compatibility
EOF
    fi
    
    print_success "Shell integration added to $shell_config"
    print_info "Please restart your shell or run: source $shell_config"
}

# Create global configuration
create_global_config() {
    print_info "Creating global configuration..."
    
    cat > "$CONFIG_DIR/config.json" << EOF
{
  "version": "$AGENTICFLOW_VERSION",
  "installation": {
    "home": "$INSTALL_DIR",
    "installed": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  },
  "defaults": {
    "template": "react",
    "testing": {
      "coverage_threshold": 80,
      "quality_gates": true
    },
    "requirements": {
      "format": "EARS",
      "validation": true
    }
  },
  "agents": {
    "core": [
      "requirements-analyst",
      "bdd-generator",
      "code-reviewer",
      "test-orchestrator"
    ]
  },
  "plugins": {
    "auto_discover": true,
    "directories": [
      "~/.agentecflow/plugins"
    ]
  }
}
EOF

    print_success "Global configuration created"
}

# Install completion scripts
install_completions() {
    print_info "Installing shell completions..."

    # Bash completion
    cat > "$INSTALL_DIR/completions/agentecflow.bash" << 'EOF'
# Bash completion for agentecflow and agentec-init

# Helper function to list all available templates dynamically
_list_all_templates() {
    local templates=()
    local agentecflow_home="$HOME/.agentecflow"

    # Add local templates if in a project
    local current_dir="$PWD"
    local max_depth=10
    local depth=0
    while [ "$depth" -lt "$max_depth" ]; do
        if [ -d "$current_dir/.claude/templates" ]; then
            for template_dir in "$current_dir/.claude/templates"/*; do
                if [ -d "$template_dir" ]; then
                    templates+=("$(basename "$template_dir")")
                fi
            done
            break
        fi
        if [ "$current_dir" = "/" ]; then
            break
        fi
        current_dir="$(dirname "$current_dir")"
        depth=$((depth + 1))
    done

    # Add global templates
    if [ -d "$agentecflow_home/templates" ]; then
        for template_dir in "$agentecflow_home/templates"/*; do
            if [ -d "$template_dir" ]; then
                local name=$(basename "$template_dir")
                # Add only if not already in list (avoid duplicates)
                if [[ ! " ${templates[@]} " =~ " ${name} " ]]; then
                    templates+=("$name")
                fi
            fi
        done
    fi

    echo "${templates[@]}"
}

_agentecflow() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="init doctor version help"

    case "${prev}" in
        agentecflow|af)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
        init|agentec-init|ai)
            local templates=$(_list_all_templates)
            COMPREPLY=( $(compgen -W "${templates}" -- ${cur}) )
            return 0
            ;;
    esac
}

_agentec_init() {
    local cur templates
    cur="${COMP_WORDS[COMP_CWORD]}"
    templates=$(_list_all_templates)
    COMPREPLY=( $(compgen -W "${templates}" -- ${cur}) )
}

complete -F _agentecflow agentecflow
complete -F _agentecflow af
complete -F _agentec_init agentec-init
complete -F _agentec_init ai
EOF
    
    print_success "Shell completions installed"
}

# Create version management
create_version_management() {
    print_info "Setting up version management..."
    
    # Create version file
    echo "$AGENTICFLOW_VERSION" > "$INSTALL_DIR/versions/current"
    
    # Create symlink to current version
    ln -sf "$AGENTICFLOW_VERSION" "$INSTALL_DIR/versions/latest"
    
    # Create version info file
    cat > "$INSTALL_DIR/versions/$AGENTICFLOW_VERSION/info.json" << EOF
{
  "version": "$AGENTICFLOW_VERSION",
  "released": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "features": [
    "EARS requirements notation",
    "BDD/Gherkin generation",
    "Epic/Feature/Task hierarchy",
    "Portfolio management",
    "PM tool integration",
    "Quality gates",
    "Test orchestration",
    "10+ core AI agents",
    "8 project templates",
    "Agentecflow Stage 1-4 support"
  ]
}
EOF
    
    print_success "Version management configured"
}

# Create cache directories
setup_cache() {
    print_info "Setting up cache directories..."
    
    mkdir -p "$INSTALL_DIR/cache"/{responses,artifacts,sessions}
    
    # Create cache config
    cat > "$INSTALL_DIR/cache/config.json" << 'EOF'
{
  "max_size_mb": 100,
  "ttl_hours": 24,
  "auto_clean": true
}
EOF
    
    print_success "Cache directories created"
}

# Validate installation
validate_installation() {
    print_info "Validating installation..."

    # Test Python imports work
    python3 << 'EOF'
import sys
import os

# Change to installed commands directory
os.chdir(os.path.expanduser("~/.agentecflow/commands"))

# Test critical imports
try:
    from lib.id_generator import generate_task_id, validate_task_id
    print("✅ Python imports validated successfully")
except ImportError as e:
    print(f"❌ ERROR: Python import validation failed")
    print(f"   {e}")
    print("")
    print("   This is a bug in the installation script.")
    print("   Please report this issue with the error message above.")
    sys.exit(1)
EOF

    if [ $? -ne 0 ]; then
        echo ""
        print_error "Installation validation failed"
        print_error "Installation incomplete - please report this issue"
        exit 1
    fi

    print_success "Installation validated successfully"
}

# Final summary
print_summary() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ GuardKit installation complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Installation Summary:${NC}"
    echo "  📁 Home Directory: $INSTALL_DIR"
    echo "  🔧 Configuration: $CONFIG_DIR"
    echo "  📦 Version: $AGENTECFLOW_VERSION"
    echo ""
    echo -e "${BOLD}Installed Components:${NC}"

    # Count components
    local agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
    local template_count=$(ls -1d "$INSTALL_DIR/templates"/*/ 2>/dev/null | wc -l)
    local command_count=$(ls -1 "$INSTALL_DIR/commands/"*.md 2>/dev/null | wc -l)

    echo "  🤖 AI Agents: $agent_count (including clarification-questioner)"
    echo "  📋 Templates: $template_count"
    echo "  ⚡ Commands: $command_count"
    echo ""
    echo -e "${BOLD}Available Commands:${NC}"
    echo "  • guardkit-init [template]  - Initialize a project"
    echo "  • guardkit init             - Alternative initialization"
    echo "  • guardkit doctor           - Check system health"
    echo "  • gk                          - Short for guardkit"
    echo "  • gki                         - Short for guardkit-init"
    echo ""
    echo -e "${BOLD}Available Templates:${NC}"
    for template in "$INSTALL_DIR/templates"/*/; do
        if [ -d "$template" ]; then
            local name=$(basename "$template")
            case "$name" in
                default)
                    echo "  • $name - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)"
                    ;;
                react-typescript)
                    echo "  • $name - React frontend with feature-based architecture (9+/10)"
                    ;;
                fastapi-python)
                    echo "  • $name - FastAPI backend with layered architecture (9+/10)"
                    ;;
                nextjs-fullstack)
                    echo "  • $name - Next.js App Router full-stack (9+/10)"
                    ;;
                react-fastapi-monorepo)
                    echo "  • $name - React + FastAPI monorepo with type safety (9.2/10)"
                    ;;
                *)
                    echo "  • $name"
                    ;;
            esac
        fi
    done
    echo ""
    echo -e "${BOLD}Claude Code Integration:${NC}"
    if [ -L "$HOME/.claude/commands" ] && [ -L "$HOME/.claude/agents" ]; then
        echo -e "  ${GREEN}✓${NC} Commands available in Claude Code (via symlink)"
        echo -e "  ${GREEN}✓${NC} Agents available in Claude Code (via symlink)"
        echo -e "  ${GREEN}✓${NC} Compatible with Conductor.build for parallel development"
    else
        echo -e "  ${YELLOW}⚠${NC} Claude Code integration not configured"
    fi
    echo ""
    echo -e "${BOLD}AutoBuild Configuration:${NC}"
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY is set"
    else
        echo -e "  ${YELLOW}⚠${NC} ANTHROPIC_API_KEY not set"
        echo "      AutoBuild requires API credentials or Claude Code authentication"
        echo "      Run 'guardkit doctor' to check configuration"
    fi
    echo ""
    echo -e "${YELLOW}⚠ Next Steps:${NC}"
    echo "  1. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
    echo "  2. Navigate to your project directory"
    echo "  3. Run: guardkit-init [template]  # e.g., react-typescript, fastapi-python, nextjs-fullstack"
    echo "  4. (Optional) Install Conductor.build for parallel development"
    echo ""
    echo -e "${BLUE}📚 Documentation: $INSTALL_DIR/docs/${NC}"
    echo -e "${BLUE}❓ Check health: guardkit doctor${NC}"
    echo -e "${BLUE}🔗 Conductor: https://conductor.build${NC}"
}

# Create marker file for guardkit installation (DEPRECATED - using create_marker_file instead)
# This function is kept for reference but should not be called
create_package_marker() {
    print_info "Skipping legacy marker creation (using JSON marker instead)..."

    # Only create manifest for compatibility
    if [ -f "$INSTALLER_DIR/core/manifest.json" ]; then
        cp "$INSTALLER_DIR/core/manifest.json" "$INSTALL_DIR/guardkit.manifest.json"
        print_success "Package manifest created"
    fi
}

# Setup Claude Code integration (for Conductor compatibility)
setup_claude_integration() {
    print_info "Setting up Claude Code integration..."

    # Ensure ~/.claude exists
    if [ ! -d "$HOME/.claude" ]; then
        mkdir -p "$HOME/.claude"
        print_success "Created ~/.claude directory"
    fi

    # Handle existing commands directory
    if [ -d "$HOME/.claude/commands" ] && [ ! -L "$HOME/.claude/commands" ]; then
        local backup_dir="$HOME/.claude/commands.backup.$(date +%Y%m%d_%H%M%S)"
        mv "$HOME/.claude/commands" "$backup_dir"
        print_warning "Backed up existing commands to $backup_dir"
    elif [ -L "$HOME/.claude/commands" ]; then
        rm "$HOME/.claude/commands"
        print_info "Removed existing commands symlink"
    fi

    # Handle existing agents directory
    if [ -d "$HOME/.claude/agents" ] && [ ! -L "$HOME/.claude/agents" ]; then
        local backup_dir="$HOME/.claude/agents.backup.$(date +%Y%m%d_%H%M%S)"
        mv "$HOME/.claude/agents" "$backup_dir"
        print_warning "Backed up existing agents to $backup_dir"
    elif [ -L "$HOME/.claude/agents" ]; then
        rm "$HOME/.claude/agents"
        print_info "Removed existing agents symlink"
    fi

    # Create symlinks
    ln -sf "$INSTALL_DIR/commands" "$HOME/.claude/commands"
    ln -sf "$INSTALL_DIR/agents" "$HOME/.claude/agents"

    # Verify symlinks
    if [ -L "$HOME/.claude/commands" ] && [ -L "$HOME/.claude/agents" ]; then
        print_success "Claude Code integration configured successfully"
        print_info "  Commands: ~/.claude/commands → ~/.agentecflow/commands"
        print_info "  Agents: ~/.claude/agents → ~/.agentecflow/agents"
        echo ""
        print_success "All guardkit commands now available in Claude Code!"
        print_info "Compatible with Conductor.build for parallel development"
    else
        print_error "Failed to create symlinks for Claude Code integration"
        print_warning "Commands and agents may not be available in Claude Code"
    fi
}

# Create symlinks for Python command scripts in ~/.agentecflow/bin/
# This allows commands to work from any directory
setup_python_bin_symlinks() {
    print_info "Setting up Python command script symlinks..."

    local BIN_DIR="$INSTALL_DIR/bin"
    local COMMANDS_DIR="$INSTALLER_DIR/core/commands"
    local COMMANDS_LIB_DIR="$INSTALLER_DIR/core/commands/lib"

    # Create bin directory if it doesn't exist
    if [ ! -d "$BIN_DIR" ]; then
        mkdir -p "$BIN_DIR"
        print_success "Created bin directory: $BIN_DIR"
    fi

    # Track statistics
    local symlinks_created=0
    local symlinks_updated=0
    local symlinks_skipped=0
    local errors=0

    # Find all Python command scripts
    local python_scripts=()

    # Find scripts in commands/ directory (exclude lib/)
    if [ -d "$COMMANDS_DIR" ]; then
        while IFS= read -r script; do
            python_scripts+=("$script")
        done < <(find "$COMMANDS_DIR" -maxdepth 1 -type f -name "*.py" 2>/dev/null)
    fi

    # Find scripts in commands/lib/ directory (top-level only, not subdirectories)
    if [ -d "$COMMANDS_LIB_DIR" ]; then
        while IFS= read -r script; do
            python_scripts+=("$script")
        done < <(find "$COMMANDS_LIB_DIR" -maxdepth 1 -type f -name "*.py" 2>/dev/null)
    fi

    # Check if we found any scripts
    if [ ${#python_scripts[@]} -eq 0 ]; then
        print_warning "No Python command scripts found"
        return 0
    fi

    print_info "Found ${#python_scripts[@]} Python command script(s)"

    # Create symlink for each Python script
    for script_path in "${python_scripts[@]}"; do
        local script_file=$(basename "$script_path")
        local symlink_name="${script_file%.py}"

        # Skip __init__.py files
        if [ "$script_file" = "__init__.py" ]; then
            ((symlinks_skipped++))
            continue
        fi

        # Skip test files (files starting with test_)
        if [[ "$script_file" == test_* ]]; then
            ((symlinks_skipped++))
            continue
        fi

        # Convert underscores to hyphens
        symlink_name="${symlink_name//_/-}"

        local symlink_path="$BIN_DIR/$symlink_name"

        # Check if script is readable
        if [ ! -r "$script_path" ]; then
            print_warning "Cannot read script: $script_path (skipping)"
            ((errors++))
            continue
        fi

        # Check for conflicts
        if [ -L "$symlink_path" ]; then
            local existing_target=$(readlink "$symlink_path")
            if [ "$existing_target" != "$script_path" ]; then
                print_warning "Symlink conflict: $symlink_name"
                print_warning "  Existing: $existing_target"
                print_warning "  New: $script_path"
                print_error "Cannot create symlink due to conflict"
                ((errors++))
                continue
            fi
        fi

        # Create or update symlink
        # NOTE: Do NOT chmod symlinks - on macOS/Linux, chmod on a symlink
        # modifies the TARGET file's permissions, which would mark library
        # files as executable in git. Symlinks inherit target permissions.
        if [ -L "$symlink_path" ]; then
            local current_target=$(readlink "$symlink_path")
            if [ "$current_target" = "$script_path" ]; then
                ((symlinks_skipped++))
            else
                ln -sf "$script_path" "$symlink_path"
                ((symlinks_updated++))
                print_info "  Updated: $symlink_name"
            fi
        elif [ -e "$symlink_path" ]; then
            print_error "Cannot create symlink: $symlink_path exists as regular file"
            ((errors++))
        else
            ln -s "$script_path" "$symlink_path"
            ((symlinks_created++))
            print_info "  Created: $symlink_name → $(basename $script_path)"
        fi
    done

    # Summary
    echo ""
    if [ $errors -eq 0 ]; then
        print_success "Python command symlinks configured successfully"
        print_info "  Created: $symlinks_created"
        print_info "  Updated: $symlinks_updated"
        print_info "  Skipped: $symlinks_skipped"
        print_info "  Location: $BIN_DIR"
        print_info "Commands can now be executed from any directory"
    else
        print_warning "Python command symlinks configured with errors"
        print_info "  Created: $symlinks_created"
        print_info "  Updated: $symlinks_updated"
        print_info "  Skipped: $symlinks_skipped"
        print_error "  Errors: $errors"
        print_warning "Some commands may not work correctly"
    fi
}

# Create marker file for bidirectional integration
create_marker_file() {
    print_info "Creating marker file for package detection..."

    local marker_file="$INSTALL_DIR/guardkit.marker.json"
    local install_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Determine repository root (parent of installer/)
    # INSTALLER_DIR is set at top of script (line 20)
    # Navigate from installer/ to repo root
    local repo_root
    if [ -d "$INSTALLER_DIR" ]; then
        repo_root="$(cd "$INSTALLER_DIR/.." && pwd)"
    else
        repo_root="$PWD"  # Fallback to current directory
    fi

    # Create marker file from template with substitution
    cat > "$marker_file" << EOF
{
  "package": "guardkit",
  "version": "$AGENTECFLOW_VERSION",
  "installed": "$install_date",
  "install_location": "$INSTALL_DIR",
  "install_method": "$INSTALL_METHOD",
  "python_lib_path": "$INSTALL_DIR/commands/lib",
  "provides": [
    "task_management",
    "quality_gates",
    "architectural_review",
    "test_enforcement",
    "design_first_workflow",
    "complexity_evaluation",
    "stack_templates"
  ],
  "optional_integration": [
    "require-kit"
  ],
  "integration_model": "bidirectional_optional",
  "description": "Task execution and quality gates for Agentecflow",
  "homepage": "https://github.com/guardkit/guardkit"
}
EOF

    if [ -f "$marker_file" ]; then
        print_success "Marker file created: $marker_file"
        print_info "  Package: guardkit (standalone + optional require-kit integration)"
        print_info "  Install method: $INSTALL_METHOD"
        print_info "  Model: Bidirectional optional integration"

        # Check if require-kit is also installed
        if [ -f "$INSTALL_DIR/require-kit.marker.json" ]; then
            print_success "  ✓ require-kit detected - Full requirements management available"
        else
            print_info "  ℹ Install require-kit for requirements management features"
        fi
    else
        print_error "Failed to create marker file"
    fi
}

# Main installation
main() {
    print_header

    print_info "Installing GuardKit to $INSTALL_DIR"
    echo ""

    # Ensure we have repository files (download if running via curl)
    ensure_repository_files

    # Run installation steps
    check_prerequisites
    install_python_package
    backup_existing
    create_directories
    install_global_files
    install_global_agents
    create_cli_commands
    setup_shell_integration
    create_global_config
    install_completions
    create_version_management
    setup_cache
    # create_package_marker  # DEPRECATED - using create_marker_file instead
    setup_claude_integration
    setup_python_bin_symlinks
    create_marker_file

    # Validate installation
    validate_installation

    # Print summary
    print_summary
}

# Run main installation
main "$@"
