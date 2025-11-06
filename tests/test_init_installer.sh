#!/bin/bash

# Comprehensive Test Suite for INSTALLER-001 (init-project.sh)
# Tests the modified global agents copy logic with counter functionality

set -e

# Test configuration
TEST_DIR=$(mktemp -d)
SCRIPT_PATH="/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/scripts/init-project.sh"
MOCK_AGENTECFLOW="$TEST_DIR/mock-agentecflow"
MOCK_PROJECT="$TEST_DIR/mock-project"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results array
declare -a TEST_RESULTS

# Helper: Print test header
print_test_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Suite: INSTALLER-001 Global Agents Copy Logic${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Helper: Print test result
print_test_result() {
    local test_name="$1"
    local passed="$2"
    local details="$3"

    ((TESTS_RUN++))

    if [ "$passed" = "true" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        ((TESTS_PASSED++))
        TEST_RESULTS+=("$test_name: PASS")
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        if [ -n "$details" ]; then
            echo -e "  ${YELLOW}Details:${NC} $details"
        fi
        ((TESTS_FAILED++))
        TEST_RESULTS+=("$test_name: FAIL - $details")
    fi
}

# Helper: Extract agent count from output (macOS-compatible)
extract_agent_count() {
    local output="$1"
    # Look for pattern like "Added N global agent(s)"
    echo "$output" | grep "Added.*global agent" | sed 's/.*Added \([0-9]*\).*/\1/' || echo "0"
}

# Test 1: Syntax validation
test_syntax_validation() {
    local test_name="Bash syntax validation"

    local output=$(bash -n "$SCRIPT_PATH" 2>&1)
    local passed="true"

    if [ $? -ne 0 ]; then
        passed="false"
    fi

    print_test_result "$test_name" "$passed" "Script has valid bash syntax"
}

# Test 2: Verify separate if blocks (not elif)
test_separate_if_blocks() {
    local test_name="Separate if blocks structure (not elif)"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Check the specific section (lines 227-249) uses separate if blocks
    # The pattern should be: if [ -d template_agents ]; then ... fi
    # Followed by: if [ -d global_agents ]; then ... for loop ... fi

    if echo "$script_content" | sed -n '227,249p' | grep -q "if \[ -d.*template_dir.*agents"; then
        if echo "$script_content" | sed -n '227,249p' | grep -q "if \[ -d.*AGENTECFLOW_HOME.*agents"; then
            # Make sure no elif in this section
            if ! echo "$script_content" | sed -n '227,249p' | grep -q "elif"; then
                passed="true"
            fi
        fi
    fi

    print_test_result "$test_name" "$passed" "Uses separate if blocks for template and global agents"
}

# Test 3: Verify iteration through global agents with counter
test_global_agent_iteration() {
    local test_name="Global agents iteration with counter"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Should have:
    # - for agent_file in ... loop
    # - if [ -f "$agent_file" ] check
    # - ((global_agent_count++)) counter

    if echo "$script_content" | sed -n '236,249p' | grep -q "for agent_file in"; then
        if echo "$script_content" | sed -n '236,249p' | grep -q "if \[ -f"; then
            if echo "$script_content" | sed -n '236,249p' | grep -q "global_agent_count"; then
                passed="true"
            fi
        fi
    fi

    print_test_result "$test_name" "$passed" "For loop with file check and counter present"
}

# Test 4: Verify counter initialization
test_counter_initialization() {
    local test_name="Counter initialized before loop"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Should initialize counter on line 234: local global_agent_count=0
    if echo "$script_content" | sed -n '234,236p' | grep -q "global_agent_count=0"; then
        passed="true"
    fi

    print_test_result "$test_name" "$passed" "Counter initialized to 0 before loop"
}

# Test 5: Verify print_success with counter
test_counter_output_message() {
    local test_name="Print message with counter value"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Should print message with counter: print_success "Added $global_agent_count global agent(s)"
    if echo "$script_content" | sed -n '246,248p' | grep -q 'print_success.*global_agent_count'; then
        passed="true"
    fi

    print_test_result "$test_name" "$passed" "Message includes counter value"
}

# Test 6: Verify precedence logic
test_precedence_logic() {
    local test_name="Template agents take precedence over global"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Check for the comment about precedence and the conditional logic
    if echo "$script_content" | sed -n '239,241p' | grep -q "Only copy if file doesn't already exist"; then
        if echo "$script_content" | sed -n '240,241p' | grep -q "! -f.*agent_name"; then
            passed="true"
        fi
    fi

    print_test_result "$test_name" "$passed" "Template agents take precedence (skip if exists)"
}

# Test 7: Copy template agents logic
test_copy_template_agents() {
    local test_name="Copy template-specific agents first"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Should copy template agents BEFORE global agents
    # Line 227-231: template agents copy
    # Line 233+: global agents copy

    local template_line=$(echo "$script_content" | grep -n "Copy template agents first" | head -1 | cut -d: -f1)
    local global_line=$(echo "$script_content" | grep -n "Copy global agents" | head -1 | cut -d: -f1)

    if [ -n "$template_line" ] && [ -n "$global_line" ] && [ "$template_line" -lt "$global_line" ]; then
        passed="true"
    fi

    print_test_result "$test_name" "$passed" "Template agents copied before global agents"
}

# Test 8: Verify agent_name extraction
test_agent_name_extraction() {
    local test_name="Agent filename extracted from path"

    local script_content=$(cat "$SCRIPT_PATH")
    local passed="false"

    # Should extract basename: local agent_name=$(basename "$agent_file")
    if echo "$script_content" | sed -n '238,242p' | grep -q 'agent_name=$(basename'; then
        passed="true"
    fi

    print_test_result "$test_name" "$passed" "Agent name extracted using basename"
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "Total Tests:  ${TESTS_RUN}"
    echo -e "Passed:       ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed:       ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo -e "${GREEN}All tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}Some tests FAILED${NC}"
        return 1
    fi
}

# Cleanup function
cleanup() {
    cd /
    rm -rf "$TEST_DIR"
}

# Main execution
main() {
    print_test_header

    test_syntax_validation
    test_separate_if_blocks
    test_global_agent_iteration
    test_counter_initialization
    test_counter_output_message
    test_precedence_logic
    test_copy_template_agents
    test_agent_name_extraction

    print_summary
    local exit_code=$?

    cleanup
    return $exit_code
}

# Run tests
main
exit $?
