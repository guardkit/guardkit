#!/bin/bash

# GuardKit Initialization Feature Testing - Repository Cloning Script
# This script clones all test repositories for evaluating the initialization feature

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_REPOS_DIR="${1:-./test-repos}"
CLONE_DEPTH="${CLONE_DEPTH:-1}"  # Shallow clone by default for speed

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GuardKit Initialization Test Repos${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Target directory: ${GREEN}${TEST_REPOS_DIR}${NC}"
echo -e "Clone depth: ${GREEN}${CLONE_DEPTH}${NC} (set CLONE_DEPTH=0 for full clone)"
echo ""

# Create test repos directory
mkdir -p "${TEST_REPOS_DIR}"
cd "${TEST_REPOS_DIR}"

echo -e "${BLUE}Working directory: ${GREEN}$(pwd)${NC}"
echo ""

# Function to clone a repository
clone_repo() {
    local name=$1
    local url=$2
    local category=$3

    echo -e "${YELLOW}[$category]${NC} Cloning ${BLUE}$name${NC}..."

    if [ -d "$name" ]; then
        echo -e "${YELLOW}  ⚠ Directory exists, skipping${NC}"
        return
    fi

    if [ "$CLONE_DEPTH" -eq 0 ]; then
        git clone "$url" "$name" 2>&1 | sed 's/^/  /'
    else
        git clone --depth "$CLONE_DEPTH" "$url" "$name" 2>&1 | sed 's/^/  /'
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Success${NC}"
    else
        echo -e "${RED}  ✗ Failed${NC}"
        return 1
    fi
    echo ""
}

# Phase 1: Small Repositories (Quick Validation)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PHASE 1: Small Repositories${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

clone_repo "go-clean-architecture" \
    "https://github.com/zhashkevych/go-clean-architecture.git" \
    "Go"

clone_repo "bulletproof-react" \
    "https://github.com/alan2207/bulletproof-react.git" \
    "React"

# Phase 2: Medium Complexity (Comprehensive Validation)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PHASE 2: Medium Complexity${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

clone_repo "full-stack-fastapi-template" \
    "https://github.com/fastapi/full-stack-fastapi-template.git" \
    "Python"

clone_repo "CleanArchitecture-ardalis" \
    "https://github.com/ardalis/CleanArchitecture.git" \
    ".NET"

clone_repo "go-rest-api" \
    "https://github.com/qiangxue/go-rest-api.git" \
    "Go"

# Phase 3: Complex/Multi-Stack (Edge Cases)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PHASE 3: Complex/Multi-Stack${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

clone_repo "CleanArchitecture-jasontaylor" \
    "https://github.com/jasontaylordev/CleanArchitecture.git" \
    ".NET"

clone_repo "Go-Clean-Architecture-REST-API" \
    "https://github.com/AleksK1NG/Go-Clean-Architecture-REST-API.git" \
    "Go"

clone_repo "actix-examples" \
    "https://github.com/actix/examples.git" \
    "Rust"

clone_repo "rocket" \
    "https://github.com/rwf2/Rocket.git" \
    "Rust"

clone_repo "Practical.CleanArchitecture" \
    "https://github.com/phongnguyend/Practical.CleanArchitecture.git" \
    ".NET"

# Phase 4: Microservices (Advanced)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PHASE 4: Microservices${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

clone_repo "eShop" \
    "https://github.com/dotnet/eShop.git" \
    ".NET"

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cloning Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${GREEN}Repository Summary:${NC}"
echo ""

# Count directories (repos)
repo_count=$(find . -maxdepth 1 -type d ! -name "." | wc -l | tr -d ' ')
echo -e "Total repositories cloned: ${GREEN}${repo_count}${NC}"
echo ""

echo -e "${YELLOW}Repository Locations:${NC}"
echo ""
echo "Phase 1 (Small):"
echo "  • go-clean-architecture"
echo "  • bulletproof-react"
echo ""
echo "Phase 2 (Medium):"
echo "  • full-stack-fastapi-template"
echo "  • CleanArchitecture-ardalis"
echo "  • go-rest-api"
echo ""
echo "Phase 3 (Complex):"
echo "  • CleanArchitecture-jasontaylor"
echo "  • Go-Clean-Architecture-REST-API"
echo "  • actix-examples"
echo "  • rocket"
echo "  • Practical.CleanArchitecture"
echo ""
echo "Phase 4 (Microservices):"
echo "  • eShop"
echo ""

# Calculate total size
total_size=$(du -sh . 2>/dev/null | cut -f1)
echo -e "Total size: ${GREEN}${total_size}${NC}"
echo ""

echo -e "${GREEN}✓ All repositories ready for testing!${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Review docs/testing/initialization-test-plan.md"
echo "  2. Follow docs/testing/quick-start-guide.md"
echo "  3. Run initialization feature on each repository"
echo "  4. Document results using the test data collection template"
echo ""
