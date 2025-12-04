#!/bin/bash

##############################################################################
# verify-duplication.sh
#
# Verifies which agents are truly duplicated between GuardKit and RequireKit
# repos based on line-based similarity analysis.
#
# Usage: ./scripts/verify-duplication.sh
#
# Output:
#   - Console output with results
#   - docs/verified-agents-for-migration.md (detailed report)
##############################################################################

set -euo pipefail

# Configuration
GUARDKIT_AGENTS_DIR="${GUARDKIT_AGENTS_DIR:-installer/global/agents}"
SIMILARITY_THRESHOLD=${SIMILARITY_THRESHOLD:-80}
MANUAL_REVIEW_LOWER=${MANUAL_REVIEW_LOWER:-50}
MANUAL_REVIEW_UPPER=${MANUAL_REVIEW_UPPER:-80}
OUTPUT_FILE="${OUTPUT_FILE:-docs/verified-agents-for-migration.md}"

# Temporary files for storing results
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

DUPLICATES_FILE="$TEMP_DIR/duplicates.txt"
MANUAL_REVIEW_FILE="$TEMP_DIR/manual_review.txt"
LOW_SIMILARITY_FILE="$TEMP_DIR/low_similarity.txt"
GUARDKIT_ONLY_FILE="$TEMP_DIR/guardkit_only.txt"
REQUIREKIT_ONLY_FILE="$TEMP_DIR/requirekit_only.txt"

# Initialize result files
touch "$DUPLICATES_FILE" "$MANUAL_REVIEW_FILE" "$LOW_SIMILARITY_FILE" "$GUARDKIT_ONLY_FILE" "$REQUIREKIT_ONLY_FILE"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

##############################################################################
# Helper Functions
##############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

##############################################################################
# Find RequireKit Installation
##############################################################################

find_requirekit() {
    local candidates=(
        "../require-kit"
        "/Users/richardwoollcott/Projects/appmilla_github/require-kit"
        "$HOME/Projects/appmilla_github/require-kit"
        "~/Projects/require-kit"
        "/Users/richardwoollcott/Projects/require-kit"
        "$HOME/Projects/require-kit"
    )

    for path in "${candidates[@]}"; do
        expanded_path="${path/#\~/$HOME}"

        if [[ -d "$expanded_path/installer/global/agents" ]]; then
            echo "$expanded_path"
            return 0
        fi
    done

    return 1
}

##############################################################################
# Calculate Line-Based Similarity
#
# Algorithm: Calculates percentage of matching lines between two files
# using simple diff-based comparison.
#
# Args:
#   $1 = File 1 path
#   $2 = File 2 path
#
# Output:
#   Percentage (0-100)
##############################################################################

calculate_similarity() {
    local file1="$1"
    local file2="$2"

    if [[ ! -f "$file1" ]] || [[ ! -f "$file2" ]]; then
        echo "0"
        return 1
    fi

    # Get line counts
    local lines1=$(wc -l < "$file1" 2>/dev/null || echo 0)
    local lines2=$(wc -l < "$file2" 2>/dev/null || echo 0)

    if [[ $lines1 -eq 0 || $lines2 -eq 0 ]]; then
        echo "0"
        return 1
    fi

    # Use diff to find matching lines
    # Count total lines in both files
    local total_lines=$((lines1 + lines2))

    # Count lines that differ (common + different)
    # This is simplified: count unique lines in each file
    local matching_lines=$(comm -12 <(sort "$file1") <(sort "$file2") 2>/dev/null | wc -l)

    # Calculate similarity as: (2 * matching) / (total) * 100
    local similarity=$((matching_lines * 200 / total_lines))

    # Ensure result is between 0-100
    if [[ $similarity -gt 100 ]]; then
        similarity=100
    fi

    echo "$similarity"
}

##############################################################################
# Classify Agents by Content Similarity
##############################################################################

classify_agents() {
    local guardkit_dir="$1"
    local requirekit_dir="$2"

    log_info "Scanning GuardKit agents..."

    # Get list of GuardKit agents
    if [[ ! -d "$guardkit_dir" ]]; then
        log_error "GuardKit agents directory not found: $guardkit_dir"
        return 1
    fi

    # Process GuardKit agents
    find "$guardkit_dir" -name "*.md" -type f | sort | while IFS= read -r agent_file; do
        local agent_name=$(basename "$agent_file" .md)

        if [[ -n "$requirekit_dir" && -d "$requirekit_dir" ]]; then
            local requirekit_file="$requirekit_dir/$(basename "$agent_file")"

            if [[ -f "$requirekit_file" ]]; then
                # Both files exist - calculate similarity
                local similarity=$(calculate_similarity "$agent_file" "$requirekit_file")

                if [[ $similarity -ge $SIMILARITY_THRESHOLD ]]; then
                    echo "$agent_name:$similarity" >> "$DUPLICATES_FILE"
                elif [[ $similarity -ge $MANUAL_REVIEW_LOWER ]]; then
                    echo "$agent_name:$similarity" >> "$MANUAL_REVIEW_FILE"
                else
                    # Low similarity (<50%) - exists in both but significantly different
                    echo "$agent_name:$similarity" >> "$LOW_SIMILARITY_FILE"
                fi
            else
                # GuardKit only
                echo "$agent_name" >> "$GUARDKIT_ONLY_FILE"
            fi
        else
            # No RequireKit - all are unique
            echo "$agent_name" >> "$GUARDKIT_ONLY_FILE"
        fi
    done

    # Find RequireKit-only agents (if RequireKit exists)
    if [[ -n "$requirekit_dir" && -d "$requirekit_dir" ]]; then
        log_info "Checking for RequireKit-only agents..."

        find "$requirekit_dir" -name "*.md" -type f | while IFS= read -r agent_file; do
            local agent_name=$(basename "$agent_file" .md)
            local guardkit_file="$guardkit_dir/${agent_name}.md"

            if [[ ! -f "$guardkit_file" ]]; then
                echo "$agent_name" >> "$REQUIREKIT_ONLY_FILE"
            fi
        done
    fi
}

##############################################################################
# Count results from files
##############################################################################

count_results() {
    local file="$1"
    if [[ -f "$file" ]] && [[ -s "$file" ]]; then
        wc -l < "$file"
    else
        echo "0"
    fi
}

##############################################################################
# Generate Report
##############################################################################

generate_report() {
    local requirekit_status="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local dup_count=$(count_results "$DUPLICATES_FILE")
    local manual_count=$(count_results "$MANUAL_REVIEW_FILE")
    local low_sim_count=$(count_results "$LOW_SIMILARITY_FILE")
    local gk_only_count=$(count_results "$GUARDKIT_ONLY_FILE")
    local rk_only_count=$(count_results "$REQUIREKIT_ONLY_FILE")

    # Build markdown report
    cat > "$OUTPUT_FILE" << EOF
# Agent Duplication Verification Report

**Generated**: $timestamp
**Threshold**: $SIMILARITY_THRESHOLD% for duplicate classification
**Manual Review Range**: $MANUAL_REVIEW_LOWER%-$MANUAL_REVIEW_UPPER%

## Verification Method

This report uses **line-based similarity analysis** to identify duplicate agents:

1. Reads agent files from both repositories
2. Compares line content using sorted diff matching
3. Calculates similarity percentage: (2 × matching_lines) / (total_lines) × 100
4. Classifies agents:
   - **Duplicate**: ≥$SIMILARITY_THRESHOLD% match
   - **Manual Review**: $MANUAL_REVIEW_LOWER%-$MANUAL_REVIEW_UPPER% match
   - **Unique**: <$MANUAL_REVIEW_LOWER% match

## RequireKit Status

$requirekit_status

## Summary

| Category | Count |
|----------|-------|
| Truly Duplicated (≥80%) | $dup_count |
| Manual Review (50-80%) | $manual_count |
| Low Similarity (<50%) | $low_sim_count |
| GuardKit-Only | $gk_only_count |
| RequireKit-Only | $rk_only_count |

## Truly Duplicated Agents (≥$SIMILARITY_THRESHOLD%)

These agents are confirmed duplicates and should be reviewed for consolidation:

EOF

    if [[ $dup_count -eq 0 ]]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo "" >> "$OUTPUT_FILE"
        sort "$DUPLICATES_FILE" | while IFS=':' read -r agent similarity; do
            echo "- **${agent}** - ${similarity}% match" >> "$OUTPUT_FILE"
        done
    fi

    cat >> "$OUTPUT_FILE" << EOF

## Manual Review Required ($MANUAL_REVIEW_LOWER%-$MANUAL_REVIEW_UPPER%)

These agents have partial overlap and need manual inspection:

EOF

    if [[ $manual_count -eq 0 ]]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo "" >> "$OUTPUT_FILE"
        sort "$MANUAL_REVIEW_FILE" | while IFS=':' read -r agent similarity; do
            echo "- **${agent}** - ${similarity}% match" >> "$OUTPUT_FILE"
        done
    fi

    cat >> "$OUTPUT_FILE" << EOF

## Low Similarity Agents (<$MANUAL_REVIEW_LOWER%)

These agents exist in BOTH repositories but have significantly diverged (not worth consolidating):

EOF

    if [[ $low_sim_count -eq 0 ]]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo "" >> "$OUTPUT_FILE"
        sort "$LOW_SIMILARITY_FILE" | while IFS=':' read -r agent similarity; do
            echo "- **${agent}** - ${similarity}% match (diverged)" >> "$OUTPUT_FILE"
        done
    fi

    cat >> "$OUTPUT_FILE" << EOF

## GuardKit-Only Agents (No Equivalent in RequireKit)

These agents are unique to GuardKit and don't need consolidation:

EOF

    if [[ $gk_only_count -eq 0 ]]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo "" >> "$OUTPUT_FILE"
        sort "$GUARDKIT_ONLY_FILE" | while IFS= read -r agent; do
            echo "- ${agent}" >> "$OUTPUT_FILE"
        done
    fi

    cat >> "$OUTPUT_FILE" << EOF

## RequireKit-Only Agents (New to RequireKit)

These agents exist only in RequireKit and may need to be evaluated for GuardKit inclusion:

EOF

    if [[ $rk_only_count -eq 0 ]]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo "" >> "$OUTPUT_FILE"
        sort "$REQUIREKIT_ONLY_FILE" | while IFS= read -r agent; do
            echo "- ${agent}" >> "$OUTPUT_FILE"
        done
    fi

    cat >> "$OUTPUT_FILE" << EOF

## Migration Recommendations

### Action Items
1. **Review Duplicates**: Consolidate agents marked as truly duplicated
2. **Manual Inspection**: Review agents in the manual review section to determine if consolidation is beneficial
3. **Unique Assessment**: Evaluate RequireKit-only agents for potential GuardKit integration

### Notes
- This analysis is based on line-level matching and may miss structural similarities
- Manual code review is recommended for agents in the manual review category
- Consider domain-specific differences when evaluating consolidation
EOF

    log_success "Report generated: $OUTPUT_FILE"
}

##############################################################################
# Main Execution
##############################################################################

main() {
    log_info "Starting agent duplication verification..."
    echo ""

    # Verify GuardKit agents directory exists
    if [[ ! -d "$GUARDKIT_AGENTS_DIR" ]]; then
        log_error "GuardKit agents directory not found: $GUARDKIT_AGENTS_DIR"
        exit 1
    fi

    log_success "Found GuardKit agents at: $GUARDKIT_AGENTS_DIR"

    # Try to find RequireKit
    requirekit_dir=""
    requirekit_status="RequireKit not found. Comparison skipped - treating all GuardKit agents as unique."

    if requirekit_dir=$(find_requirekit); then
        log_success "Found RequireKit at: $requirekit_dir"
        requirekit_status="RequireKit found at: $requirekit_dir"
        requirekit_status="${requirekit_status}\n\nAll agents from both repositories have been compared."
    else
        log_warning "RequireKit not found in expected locations"
        log_info "Checked: ../require-kit, ~/Projects/require-kit, /Users/richardwoollcott/Projects/require-kit"
    fi

    echo ""

    # Run classification - append installer/global/agents to RequireKit path
    local requirekit_agents_dir=""
    if [[ -n "$requirekit_dir" ]]; then
        requirekit_agents_dir="$requirekit_dir/installer/global/agents"
    fi
    classify_agents "$GUARDKIT_AGENTS_DIR" "$requirekit_agents_dir"

    # Generate report
    generate_report "$requirekit_status"

    # Display summary to console
    echo ""
    log_success "Verification complete!"
    echo ""
    echo "Summary:"
    echo "  Duplicates (≥80%): $(count_results "$DUPLICATES_FILE")"
    echo "  Manual Review (50-80%): $(count_results "$MANUAL_REVIEW_FILE")"
    echo "  Low Similarity (<50%): $(count_results "$LOW_SIMILARITY_FILE")"
    echo "  GuardKit-Only: $(count_results "$GUARDKIT_ONLY_FILE")"
    echo "  RequireKit-Only: $(count_results "$REQUIREKIT_ONLY_FILE")"
    echo ""
    echo "Detailed report: $OUTPUT_FILE"
}

# Execute main function
main "$@"
