# RequireKit Curl Install Fix

**Date**: 2025-11-29
**Context**: Applied same curl install fix as GuardKit
**Status**: Complete - ready for testing

---

## Changes Applied to RequireKit

Applied the same architectural fixes that were implemented for GuardKit to ensure consistent installation experience across both packages.

---

## Files Changed

### 1. install.sh - Curl Install Support

**File**: `/Users/richardwoollcott/Projects/appmilla_github/require-kit/installer/scripts/install.sh`

**Changes**:

1. **Added GitHub repo constants** (lines 11-12):
   ```bash
   GITHUB_REPO="https://github.com/requirekit/require-kit"
   GITHUB_BRANCH="main"
   ```

2. **Added `ensure_repository_files()` function** (lines 47-110):
   - Clones repo to `~/Projects/require-kit` (or `~/require-kit`)
   - Supports git clone (preferred) or tarball download (fallback)
   - Repository persists after installation
   - Handles existing repos (git pull to update)

3. **Updated `create_marker_file()` function** (lines 149-189):
   - Changed from `.marker` to `.marker.json` (JSON format)
   - Added `repo_path` field
   - Matches GuardKit marker file structure
   - Includes metadata: package, version, installed date, capabilities

4. **Updated marker file verification** (line 215):
   - Changed from `require-kit.marker` to `require-kit.marker.json`

5. **Added `ensure_repository_files` to main flow** (line 338):
   - Called before `check_prerequisites`
   - Ensures repo files available before installation

---

## Marker File Format

### Old Format (Plain Text)
```
{
  "name": "require-kit",
  "version": "1.0.0",
  ...
}
```
**Filename**: `~/.agentecflow/require-kit.marker`

### New Format (JSON with repo_path)
```json
{
  "package": "require-kit",
  "version": "1.0.0",
  "installed": "2025-11-29T12:00:00Z",
  "install_location": "/Users/[username]/.agentecflow",
  "repo_path": "/Users/[username]/Projects/require-kit",
  "provides": [
    "requirements_engineering",
    "ears_notation",
    "bdd_generation",
    "epic_management",
    "feature_management",
    "requirements_traceability"
  ],
  "requires": [
    "guardkit"
  ],
  "integration_model": "bidirectional_optional",
  "description": "Requirements engineering and BDD for Agentecflow",
  "homepage": "https://github.com/requirekit/require-kit"
}
```
**Filename**: `~/.agentecflow/require-kit.marker.json`

**Key differences**:
- ✅ JSON format matches GuardKit
- ✅ `repo_path` field for module imports
- ✅ Consistent field names (`package` vs `name`, `installed` vs `installed_at`)
- ✅ Added `requires` field (documents dependency on GuardKit)
- ✅ Added `integration_model` and `homepage`

---

## Feature Detection Updates

### 2. feature_detection.py (Both Repos)

**Files**:
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/feature_detection.py`
- `/Users/richardwoollcott/Projects/appmilla_github/require-kit/installer/core/lib/feature_detection.py`

**Changes** (lines 81-89):
```python
def is_require_kit_installed(self) -> bool:
    """Check if require-kit is installed."""
    # Check for JSON marker file (new format)
    marker_json = self.agentecflow_home / "require-kit.marker.json"
    if marker_json.exists():
        return True
    # Fallback to old format for backwards compatibility
    marker_old = self.agentecflow_home / "require-kit.marker"
    return marker_old.exists()
```

**Benefits**:
- ✅ Supports both old and new marker formats
- ✅ Backwards compatible with existing installations
- ✅ Shared file stays in sync between repos

---

## Verification Script Updates

### 3. check-requirekit.sh

**File**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/testing/pre-launch-2025-11-29/check-requirekit.sh`

**Changes** (lines 15-25):
```bash
if [ -f ~/.agentecflow/require-kit.marker.json ]; then
    echo "   ✓ ~/.agentecflow/require-kit.marker.json exists"
    ((SUCCESS++))
elif [ -f ~/.agentecflow/require-kit.marker ]; then
    echo "   ✓ ~/.agentecflow/require-kit.marker exists (old format)"
    echo "   ⚠ Consider reinstalling for JSON format with repo_path"
    ((SUCCESS++))
else
    echo "   ✗ ~/.agentecflow/require-kit.marker.json NOT FOUND"
    ((FAIL++))
fi
```

**Benefits**:
- ✅ Checks for new JSON format first
- ✅ Falls back to old format with warning
- ✅ Clear messaging about format differences

---

## Installation Workflow

### Curl Install (NEW)

```bash
# One command install
curl -sSL https://install.requirekit.dev | bash

# What happens:
# 1. Download install.sh via curl
# 2. ensure_repository_files() runs
# 3. If git available: Clone to ~/Projects/require-kit
# 4. If git not available: Download tarball to ~/Projects/require-kit
# 5. Install commands, agents, lib to ~/.agentecflow/
# 6. Create marker file: ~/.agentecflow/require-kit.marker.json
# 7. Repository persists for module imports

# Verify installation
cat ~/.agentecflow/require-kit.marker.json | grep repo_path
# Output: "repo_path": "/Users/[username]/Projects/require-kit"

# Updates
cd ~/Projects/require-kit
git pull
# Symlinks auto-update ✅
```

### Git Clone Install (Manual)

```bash
# Clone to custom location
cd ~/Projects/appmilla_github
git clone https://github.com/requirekit/require-kit.git
cd require-kit
./installer/scripts/install.sh

# What happens:
# 1. ensure_repository_files() detects files exist (no download)
# 2. SCRIPT_DIR already set to installer/ directory
# 3. Install proceeds normally
# 4. Marker file created with repo_path

# Verify installation
cat ~/.agentecflow/require-kit.marker.json | grep repo_path
# Output: "repo_path": "/Users/[username]/Projects/appmilla_github/require-kit"

# Updates
cd ~/Projects/appmilla_github/require-kit
git pull
# Symlinks auto-update ✅
```

---

## Consistency with GuardKit

Both packages now have **identical installation architecture**:

| Feature | GuardKit | RequireKit |
|---------|-----------|-----------|
| **Curl install** | ✅ Clones to `~/Projects/guardkit` | ✅ Clones to `~/Projects/require-kit` |
| **Marker format** | JSON (`.marker.json`) | JSON (`.marker.json`) |
| **repo_path field** | ✅ Yes | ✅ Yes |
| **Git clone support** | ✅ Yes (preferred) | ✅ Yes (preferred) |
| **Tarball fallback** | ✅ Yes (no git) | ✅ Yes (no git) |
| **Persistent repo** | ✅ Yes | ✅ Yes |
| **Auto-update** | ✅ `git pull` | ✅ `git pull` |
| **feature_detection.py** | ✅ JSON + fallback | ✅ JSON + fallback |

---

## Benefits

### User Experience
- ✅ **Consistent install** - Same process for both packages
- ✅ **One command** - Curl install "just works"
- ✅ **Easy updates** - `git pull` in repo directory
- ✅ **No manual setup** - Repository cloned automatically

### Developer Experience
- ✅ **Module imports work** - `repo_path` enables Python imports
- ✅ **Symlinks auto-update** - Edit files in repo, changes propagate
- ✅ **Clear structure** - Repos in `~/Projects/` by default
- ✅ **Backwards compatible** - Old marker format still detected

### System Integration
- ✅ **Matched formats** - Both use JSON markers
- ✅ **Shared detection** - `feature_detection.py` works for both
- ✅ **Clean coexistence** - No conflicts, clear boundaries
- ✅ **Dependency clarity** - RequireKit marker documents GuardKit requirement

---

## Testing Checklist

### RequireKit Fresh Install

- [ ] Curl install clones repo to `~/Projects/require-kit`
- [ ] Marker file is JSON format with `repo_path`
- [ ] Commands work from any directory
- [ ] `feature_detection.is_require_kit_installed()` returns True
- [ ] Verification script passes all checks

### RequireKit Update from Old Install

- [ ] Old marker file (`.marker`) still detected
- [ ] Reinstall creates new JSON marker
- [ ] `repo_path` field populated correctly
- [ ] No breaking changes to existing installations

### Integration Testing

- [ ] GuardKit detects RequireKit via JSON marker
- [ ] RequireKit detects GuardKit via JSON marker
- [ ] BDD mode works when both installed
- [ ] `supports_bdd()` returns True

---

## VM Testing Commands

```bash
# On VM - Test fresh RequireKit install

# 1. Install RequireKit (curl method - simulated)
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
./installer/scripts/install.sh

# 2. Verify marker file
cat ~/.agentecflow/require-kit.marker.json
cat ~/.agentecflow/require-kit.marker.json | grep repo_path
# Should output: "repo_path": "/Users/[username]/Projects/require-kit"

# 3. Verify feature detection
cd ~/Projects/appmilla_github/guardkit
python3 -c "from installer.core.lib.feature_detection import is_require_kit_installed; print('RequireKit installed:', is_require_kit_installed())"
# Should output: RequireKit installed: True

# 4. Run verification script
bash docs/testing/pre-launch-2025-11-29/check-requirekit.sh
# All checks should pass ✅

# 5. Test BDD mode (should now work)
cd ~/Projects/test-api-service
/task-work TASK-001 --mode=bdd
# Should validate RequireKit and proceed (not tested yet - need scenarios)
```

---

## Migration Notes

### For Users with Old RequireKit Install

**Symptoms**:
- Marker file is `require-kit.marker` (not `.json`)
- Missing `repo_path` field
- Repository files may not exist

**Fix**:
```bash
# Remove old installation
rm -rf ~/.agentecflow/require-kit.marker
rm -rf ~/.agentecflow/commands/require-kit
rm -rf ~/.agentecflow/agents/require-kit

# Reinstall with new script
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
./installer/scripts/install.sh

# Verify new format
cat ~/.agentecflow/require-kit.marker.json | jq .
```

**Note**: Old marker format is still supported for detection, but new installs should use JSON format.

---

## Status

- [x] RequireKit install.sh updated
- [x] Marker file format changed to JSON
- [x] `repo_path` field added
- [x] Curl install support added
- [x] feature_detection.py updated (both repos)
- [x] Verification script updated
- [ ] VM testing (pending)
- [ ] Documentation updated (README, guides)

---

**Ready for VM testing alongside GuardKit fix!** 🚀
