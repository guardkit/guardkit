---
id: TASK-SHA-004
title: Add checksum validation to shared-agents downloads
status: backlog
created: 2025-11-28T20:30:00Z
updated: 2025-11-28T20:30:00Z
priority: high
tags: [shared-agents, security, checksum, validation, phase-0, prerequisite]
complexity: 3
estimated_effort: 2h
phase: "Phase 0: Prerequisites"
depends_on: []
blocks: [TASK-SHA-P1-004, TASK-SHA-P2-002, TASK-SHA-P3-002]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Add Checksum Validation

## Context

**Finding from Architectural Review**: GitHub Actions workflow and installer lack checksum validation. Downloaded archives could be corrupted or tampered with.

**Risk**: Medium severity - Corrupted downloads could break installations
**Mitigation**: Add SHA256 checksum generation and validation

## Description

Implement checksum validation for shared-agents downloads to ensure integrity and security. Update GitHub Actions release workflow to generate checksums, and update installer to validate them before extraction.

## Acceptance Criteria

- [ ] GitHub Actions workflow updated to generate SHA256 checksums
- [ ] Installer updated to validate checksums before extraction
- [ ] Checksum mismatch blocks installation with clear error message
- [ ] Missing checksum handled gracefully (warning, not failure)
- [ ] Documentation updated with security information
- [ ] Tested with valid and invalid checksums

## Implementation Approach

### 1. Update GitHub Actions Release Workflow

Modify `.github/workflows/release.yml` in shared-agents repository:

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
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Create release archive
        run: |
          # Create tarball
          tar -czvf shared-agents.tar.gz agents/ manifest.json

          # Generate SHA256 checksum
          sha256sum shared-agents.tar.gz > shared-agents.tar.gz.sha256

          # Display for verification
          echo "=== Release Archive ==="
          ls -lh shared-agents.tar.gz
          echo ""
          echo "=== Checksum ==="
          cat shared-agents.tar.gz.sha256

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            shared-agents.tar.gz
            shared-agents.tar.gz.sha256
          generate_release_notes: true
          body: |
            ## Installation

            Download and verify:
            ```bash
            VERSION=${{ github.ref_name }}
            curl -sL "https://github.com/taskwright-dev/shared-agents/releases/download/$VERSION/shared-agents.tar.gz" -o shared-agents.tar.gz
            curl -sL "https://github.com/taskwright-dev/shared-agents/releases/download/$VERSION/shared-agents.tar.gz.sha256" -o shared-agents.tar.gz.sha256

            # Verify checksum
            sha256sum -c shared-agents.tar.gz.sha256
            ```

            ## Checksum (SHA256)
            ```
            $(cat shared-agents.tar.gz.sha256)
            ```
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 2. Update Installer with Checksum Validation

Add to `installer/scripts/install.sh`:

```bash
validate_checksum() {
    local archive="$1"
    local checksum_file="$2"

    echo ""
    echo "🔍 Validating download integrity..."

    # Check if checksum file exists
    if [ ! -f "$checksum_file" ]; then
        echo "⚠️  WARNING: Checksum file not found: $checksum_file"
        echo "   Proceeding without checksum validation (not recommended)"
        echo ""
        return 0  # Don't fail, but warn
    fi

    # Validate checksum
    if sha256sum -c "$checksum_file" 2>/dev/null; then
        echo "✅ Checksum valid - download integrity verified"
        echo ""
        return 0
    else
        echo ""
        echo "======================================================================="
        echo "❌ ERROR: Checksum Validation Failed"
        echo "======================================================================="
        echo ""
        echo "The downloaded archive failed checksum validation."
        echo "This could indicate:"
        echo "  - Corrupted download (network issue)"
        echo "  - Tampered file (security issue)"
        echo "  - Incomplete download"
        echo ""
        echo "Expected checksum:"
        cat "$checksum_file"
        echo ""
        echo "Actual checksum:"
        sha256sum "$archive"
        echo ""
        echo "Installation BLOCKED for security."
        echo "Please try again or report this issue."
        echo ""
        echo "======================================================================="
        return 1
    fi
}

install_shared_agents() {
    local version_file="$SCRIPT_DIR/../shared-agents-version.txt"
    local version=$(cat "$version_file" 2>/dev/null || echo "v1.0.0")
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"
    local base_url="https://github.com/taskwright-dev/shared-agents/releases/download/$version"
    local archive_url="$base_url/shared-agents.tar.gz"
    local checksum_url="$base_url/shared-agents.tar.gz.sha256"

    echo "📦 Installing shared agents $version..."

    # Create target directory
    mkdir -p "$target_dir"

    # Download to temp location
    local temp_dir=$(mktemp -d)
    local temp_archive="$temp_dir/shared-agents.tar.gz"
    local temp_checksum="$temp_dir/shared-agents.tar.gz.sha256"

    # Download archive
    echo "⬇️  Downloading shared-agents $version..."
    if ! curl -sL "$archive_url" -o "$temp_archive"; then
        echo "❌ ERROR: Failed to download shared-agents"
        rm -rf "$temp_dir"
        return 1
    fi

    # Download checksum
    if ! curl -sL "$checksum_url" -o "$temp_checksum"; then
        echo "⚠️  WARNING: Failed to download checksum file"
        echo "   Proceeding without checksum validation (not recommended)"
    fi

    # Validate checksum
    if ! validate_checksum "$temp_archive" "$temp_checksum"; then
        echo "Installation aborted due to checksum validation failure"
        rm -rf "$temp_dir"
        exit 1
    fi

    # Extract to universal directory
    echo "📂 Extracting to $target_dir..."
    if tar -xz -C "$target_dir" --strip-components=1 < "$temp_archive"; then
        echo "✅ Installed shared agents to $target_dir"

        # Store version marker
        echo "$version" > "$target_dir/.version"

        # Cleanup
        rm -rf "$temp_dir"
        return 0
    else
        echo "❌ ERROR: Failed to extract shared agents"
        rm -rf "$temp_dir"
        return 1
    fi
}
```

### 3. Add Checksum Utilities

Create `installer/scripts/lib/checksum_utils.sh`:

```bash
#!/bin/bash
# checksum_utils.sh
# Checksum validation utilities

# Generate checksum for local file
generate_checksum() {
    local file="$1"
    local output="$2"

    if [ ! -f "$file" ]; then
        echo "ERROR: File not found: $file"
        return 1
    fi

    sha256sum "$file" > "$output"
    echo "✅ Checksum generated: $output"
}

# Verify checksum
verify_checksum() {
    local file="$1"
    local checksum_file="$2"

    if [ ! -f "$file" ]; then
        echo "ERROR: File not found: $file"
        return 1
    fi

    if [ ! -f "$checksum_file" ]; then
        echo "ERROR: Checksum file not found: $checksum_file"
        return 1
    fi

    if sha256sum -c "$checksum_file" 2>/dev/null; then
        echo "✅ Checksum valid"
        return 0
    else
        echo "❌ Checksum invalid"
        return 1
    fi
}

# Compare two checksums
compare_checksums() {
    local file1="$1"
    local file2="$2"

    local sum1=$(sha256sum "$file1" | cut -d' ' -f1)
    local sum2=$(sha256sum "$file2" | cut -d' ' -f1)

    if [ "$sum1" = "$sum2" ]; then
        echo "✅ Checksums match"
        return 0
    else
        echo "❌ Checksums differ"
        echo "  File 1: $sum1"
        echo "  File 2: $sum2"
        return 1
    fi
}
```

### 4. Add Security Documentation

Create `docs/security/checksum-validation.md`:

```markdown
# Checksum Validation

## Overview

All shared-agents releases include SHA256 checksums to ensure download integrity and security.

## Why Checksums?

**Integrity**: Detect corrupted downloads due to network issues
**Security**: Detect tampering or man-in-the-middle attacks
**Trust**: Verify you're installing the exact code that was released

## How It Works

### 1. Release Process

When a new version is released:
1. Archive created: `shared-agents.tar.gz`
2. Checksum generated: `sha256sum shared-agents.tar.gz > shared-agents.tar.gz.sha256`
3. Both files uploaded to GitHub release

### 2. Installation Process

When installer runs:
1. Downloads `shared-agents.tar.gz`
2. Downloads `shared-agents.tar.gz.sha256`
3. Validates: `sha256sum -c shared-agents.tar.gz.sha256`
4. Blocks installation if checksum fails

## Manual Verification

You can manually verify downloads:

```bash
# Download release
VERSION="v1.0.0"
curl -sL "https://github.com/taskwright-dev/shared-agents/releases/download/$VERSION/shared-agents.tar.gz" -o shared-agents.tar.gz
curl -sL "https://github.com/taskwright-dev/shared-agents/releases/download/$VERSION/shared-agents.tar.gz.sha256" -o shared-agents.tar.gz.sha256

# Verify checksum
sha256sum -c shared-agents.tar.gz.sha256

# Expected output:
# shared-agents.tar.gz: OK
```

## What If Checksum Fails?

If checksum validation fails:

1. **Try again**: Network issues can cause corrupted downloads
2. **Check version**: Ensure you're downloading the correct version
3. **Report issue**: If problem persists, file a security issue

**DO NOT**:
- Skip checksum validation
- Manually edit checksum file
- Use untrusted downloads

## Fallback Behavior

If checksum file is missing (e.g., old release):
- Installation continues with warning
- Not recommended for production use
- Upgrade to version with checksums

## Security Best Practices

1. **Always verify checksums** in production
2. **Use HTTPS** for downloads (enforced)
3. **Report suspicious checksums** immediately
4. **Keep installer updated** for latest security features

## Support

Security issues: security@taskwright.dev
General issues: https://github.com/taskwright-dev/shared-agents/issues
```

## Test Requirements

### Unit Tests

Create `tests/unit/test-checksum-validation.sh`:

```bash
#!/bin/bash
# Test checksum validation

test_valid_checksum() {
    echo "Test: Valid checksum"

    # Create test file
    echo "test content" > /tmp/test.txt

    # Generate checksum
    sha256sum /tmp/test.txt > /tmp/test.txt.sha256

    # Validate
    validate_checksum /tmp/test.txt /tmp/test.txt.sha256

    [ $? -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL"

    # Cleanup
    rm /tmp/test.txt /tmp/test.txt.sha256
}

test_invalid_checksum() {
    echo "Test: Invalid checksum"

    # Create test file
    echo "test content" > /tmp/test.txt

    # Generate checksum
    sha256sum /tmp/test.txt > /tmp/test.txt.sha256

    # Modify file (corrupt it)
    echo "corrupted" >> /tmp/test.txt

    # Validate (should fail)
    validate_checksum /tmp/test.txt /tmp/test.txt.sha256

    [ $? -ne 0 ] && echo "✅ PASS (correctly detected invalid)" || echo "❌ FAIL"

    # Cleanup
    rm /tmp/test.txt /tmp/test.txt.sha256
}

test_missing_checksum() {
    echo "Test: Missing checksum file"

    # Create test file (no checksum)
    echo "test content" > /tmp/test.txt

    # Validate (should warn but not fail)
    validate_checksum /tmp/test.txt /tmp/nonexistent.sha256

    [ $? -eq 0 ] && echo "✅ PASS (graceful handling)" || echo "❌ FAIL"

    # Cleanup
    rm /tmp/test.txt
}

# Run tests
test_valid_checksum
test_invalid_checksum
test_missing_checksum
```

### Integration Tests

- [ ] Test GitHub Actions workflow generates checksums
- [ ] Test installer downloads and validates checksums
- [ ] Test checksum mismatch blocks installation
- [ ] Test missing checksum shows warning
- [ ] Test manual verification instructions work

## Dependencies

**Prerequisite Tasks**: None (Phase 0)

**Blocks**:
- TASK-SHA-P1-004 (Set up GitHub Actions) - needs checksum generation
- TASK-SHA-P2-002 (Update TaskWright Installer) - needs validation logic
- TASK-SHA-P3-002 (Update RequireKit Installer) - needs validation logic

**External Dependencies**:
- `sha256sum` command (standard on Unix systems)
- `curl` for HTTPS downloads (already required)

## Success Criteria

- [ ] GitHub Actions workflow generates SHA256 checksums
- [ ] Installer validates checksums before extraction
- [ ] Checksum mismatch blocks installation
- [ ] Missing checksum handled gracefully (warning, not failure)
- [ ] Security documentation created
- [ ] All tests pass (valid, invalid, missing checksum scenarios)
- [ ] Manual verification instructions work

## Estimated Effort

**Total**: 2 hours
- GitHub Actions workflow: 30 minutes
- Installer validation: 1 hour
- Documentation: 30 minutes

## Notes

### Why SHA256?

- **Industry standard** for file integrity
- **Cryptographically secure** (collision resistance)
- **Built-in** on all modern systems
- **Fast** to compute and verify

### Why Not Fail on Missing Checksum?

**Rationale**: Backward compatibility with old releases

Old shared-agents releases may not have checksums. Blocking installation would break existing workflows.

**Approach**: Warn but don't fail
- Production installs should upgrade to versions with checksums
- Development/testing can proceed with warning

### Alternative: GPG Signatures

**Future enhancement** (not in scope for Phase 0):
- GPG sign releases for authenticity (not just integrity)
- More complex setup (key management)
- Higher security bar (verify publisher identity)

For now, SHA256 checksums provide good integrity protection.

## Related Documents

- Architectural Review: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md` (Technical Implementation section)
- GitHub Actions Workflow: `.github/workflows/release.yml` (in shared-agents repo)
- Security Documentation: `docs/security/checksum-validation.md` (to be created)
