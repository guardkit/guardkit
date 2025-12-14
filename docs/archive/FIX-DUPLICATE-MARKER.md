# FIX: Duplicate Marker Files (Minor Issue)

## Problem

After installation, two marker files exist:
- `guardkit.marker.json` (correct, new format)
- `guardkit.manifest.json` (legacy, should not exist)

## Root Cause

File: `installer/scripts/install.sh` lines 1539-1542

```bash
# Line 1539: Creates manifest file (LEGACY)
create_package_marker

# Line 1542: Creates marker file (NEW)
create_marker_file
```

Both functions are called, creating two files.

## Impact

**Minor** - Cosmetic issue, doesn't break functionality
- Installation works correctly
- Commands work correctly
- Just confusing to have two files

## Fix

**Option 1: Remove Legacy Function Call** (Recommended)

File: `installer/scripts/install.sh`
Line: 1539

```bash
# BEFORE:
create_package_marker

# AFTER:
# create_package_marker  # DEPRECATED - using create_marker_file instead
```

**Option 2: Remove create_package_marker Function Entirely**

Delete lines 1267-1276 entirely (function definition + call).

## Recommended: Option 1

Just comment out line 1539. Keep the function for reference but don't call it.

## Testing

After fix:
```bash
# Clean install
rm -rf ~/.agentecflow
curl -sSL .../install.sh | bash

# Check files created
ls ~/.agentecflow/*.json

# Expected output (only one file):
# guardkit.marker.json
```

## Implementation Time

**1 minute** - Comment out one line

## Priority

**LOW** - Cosmetic issue, can be fixed anytime
**SAFE** - Won't break anything, just removes unnecessary file

## Note

This is already documented in line 1270:
```bash
print_info "Skipping legacy marker creation (using JSON marker instead)..."
```

But the function is still being called on line 1539. Just remove that call.
