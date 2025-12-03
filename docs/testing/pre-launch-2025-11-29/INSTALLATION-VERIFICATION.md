# Installation Verification Guide

**Created**: 2025-11-29
**Purpose**: Correct verification steps for TaskWright and RequireKit installation

---

## TaskWright Installation Verification

### Method 1: Check Marker File

```bash
ls ~/.agentecflow/guardkit.marker
```

**Expected**: File exists

### Method 2: Check Commands

```bash
which guardkit
# Expected: /Users/[username]/.agentecflow/bin/guardkit (or similar)

guardkit --version
# Expected: Version number or help output
```

### Method 3: Check Directory Structure

```bash
ls ~/.agentecflow/
```

**Expected to see**:
- `bin/` - Symlinked commands
- `agents/` - Global agents
- `commands/` - Command specifications
- `templates/` - User templates
- `guardkit.marker` - Installation marker
- `guardkit.marker.json` - Installation metadata (optional)

---

## RequireKit Installation Verification

### IMPORTANT: RequireKit Installation Status

**On your main development machine**: RequireKit is **NOT installed**
- You have `ears-requirements.md` which is just TaskWright's EARS documentation
- The actual RequireKit repo and tools are not present

**For VM testing**: You need to actually install RequireKit

### Method 1: Check Marker File (PRIMARY)

```bash
ls ~/.agentecflow/require-kit.marker
```

**Expected**:
- ✅ **File exists** = RequireKit is installed
- ❌ **File not found** = RequireKit is NOT installed

**This is the definitive check** - TaskWright's BDD mode uses this exact check (see `installer/global/lib/feature_detection.py:76`)

### Method 2: Check RequireKit Commands

```bash
which req-create
# Expected: /Users/[username]/.agentecflow/bin/req-create

# Try running a RequireKit command
req-create --help
```

**If these fail**, RequireKit is not properly installed.

### Method 3: Check Directory Structure

```bash
ls ~/Projects/require-kit
```

**Expected**: RequireKit repository exists

```bash
ls ~/.agentecflow/bin/ | grep req
```

**Expected to see**:
- `req-create`
- `formalize-ears`
- `generate-bdd`
- Other RequireKit commands

### Method 4: Python Feature Detection

```bash
cd ~/Projects/appmilla_github/guardkit
python3 -c "from installer.global.lib.feature_detection import is_require_kit_installed; print('RequireKit installed:', is_require_kit_installed())"
```

**Expected**:
- `RequireKit installed: True` = Installed
- `RequireKit installed: False` = Not installed

---

## Common Installation Issues

### Issue: Marker File Not Found

**Symptom**:
```bash
$ ls ~/.agentecflow/require-kit.marker
ls: /Users/[username]/.agentecflow/require-kit.marker: No such file or directory
```

**Diagnosis**: RequireKit is not installed

**Solution**:
```bash
# 1. Clone RequireKit
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git

# 2. Run installer
cd require-kit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# 3. Verify marker file created
ls ~/.agentecflow/require-kit.marker
```

### Issue: Commands Not Found

**Symptom**:
```bash
$ req-create --help
bash: req-create: command not found
```

**Diagnosis**: Syml inks not created or PATH not updated

**Solution**:
```bash
# Re-run RequireKit installer
cd ~/Projects/require-kit
./installer/scripts/install.sh

# Check if symlinks exist
ls -la ~/.agentecflow/bin/req-*

# If symlinks exist but command not found, check PATH
echo $PATH | grep -o ".agentecflow/bin"
# Should see: .agentecflow/bin

# If not in PATH, add to shell config
echo 'export PATH="$HOME/.agentecflow/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: Have EARS Instructions But Not RequireKit

**Symptom**:
```bash
$ ls ~/.agentecflow/instructions/core/ears-requirements.md
# File exists

$ ls ~/.agentecflow/require-kit.marker
# File NOT found
```

**Diagnosis**: You have TaskWright's EARS documentation, but not RequireKit itself

**Explanation**: TaskWright includes basic EARS documentation in `instructions/core/ears-requirements.md`, but this is NOT the same as having RequireKit installed. RequireKit provides the full requirements management workflow.

**Solution**: Install RequireKit if you need BDD mode:
```bash
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
./installer/scripts/install.sh
```

---

## Testing BDD Mode Availability

### Quick Check

```bash
cd ~/Projects/appmilla_github/guardkit
python3 << 'EOF'
from installer.global.lib.feature_detection import supports_bdd
print("BDD mode available:", supports_bdd())
EOF
```

**Expected**:
- `BDD mode available: True` = Can use `--mode=bdd`
- `BDD mode available: False` = BDD mode will error

### Full Feature Check

```bash
python3 << 'EOF'
from installer.global.lib.feature_detection import get_available_features
import json
print(json.dumps(get_available_features(), indent=2))
EOF
```

**Example Output** (TaskWright only):
```json
{
  "task_management": true,
  "quality_gates": true,
  "architectural_review": true,
  "test_enforcement": true,
  "requirements_engineering": false,
  "bdd_generation": false,
  "epic_management": false,
  "feature_management": false
}
```

**Example Output** (TaskWright + RequireKit):
```json
{
  "task_management": true,
  "quality_gates": true,
  "architectural_review": true,
  "test_enforcement": true,
  "requirements_engineering": true,
  "bdd_generation": true,
  "epic_management": true,
  "feature_management": true
}
```

---

## For VM Testing

### Pre-Test Checklist

Before starting the VM test plan, verify:

- [ ] TaskWright marker exists: `ls ~/.agentecflow/guardkit.marker`
- [ ] RequireKit marker exists: `ls ~/.agentecflow/require-kit.marker`
- [ ] BDD mode available: `python3 -c "from installer.global.lib.feature_detection import supports_bdd; print(supports_bdd())"`
- [ ] Both command sets work: `guardkit --version` and `req-create --help`

**If any checks fail**, re-run the respective installer before proceeding with tests.

---

## Summary

**Definitive Installation Checks**:

| Tool | Marker File | Command Check |
|------|-------------|---------------|
| **TaskWright** | `~/.agentecflow/guardkit.marker` | `guardkit --version` |
| **RequireKit** | `~/.agentecflow/require-kit.marker` | `req-create --help` |

**BDD Mode Availability**:
```python
from installer.global.lib.feature_detection import supports_bdd
supports_bdd()  # True = BDD mode works, False = will error
```

**Remember**: Just having `ears-requirements.md` doesn't mean RequireKit is installed!
