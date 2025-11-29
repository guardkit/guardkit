# Curl Install Architecture

**Updated**: 2025-11-29
**Context**: Fix for task-create id_generator import bug
**Status**: FIXED - Curl install now works correctly

---

## Problem: Why Curl Install Was Broken

### Previous Architecture (BROKEN)

```bash
curl -sSL https://install.taskwright.dev | bash
```

**What happened**:
1. `install.sh` downloaded repo to **temporary directory** (`mktemp -d`)
2. Copied files to `~/.agentecflow/` (commands, agents, templates)
3. **Deleted temporary directory** on exit (`trap "rm -rf $TEMP_DIR" EXIT`)
4. Marker file created WITHOUT `repo_path` field

**Result**:
- ❌ Repository files deleted after installation
- ❌ `/task-create` couldn't find `installer/global/lib/id_generator.py`
- ❌ Import failed: "No module named 'id_generator'"
- ❌ System completely broken

### Why This Failed

Commands like `/task-create` are **specification-based** (`.md` files, not `.py` scripts) and execute inline Python code via Claude Code. The spec includes:

```python
from installer.global.lib.id_generator import generate_task_id
```

This requires:
1. The `installer/` directory to exist somewhere
2. Python to know where to find it (via `sys.path`)

With repo files deleted, **there was nothing to import**.

---

## Solution: Permanent Repository Clone

### New Architecture (FIXED)

```bash
curl -sSL https://install.taskwright.dev | bash
```

**What happens now**:

#### If Git is Available (Recommended)
1. Detects `git` command is available
2. Clones repository to **permanent location**:
   - `~/Projects/taskwright` (if `~/Projects/` exists)
   - `~/taskwright` (if `~/Projects/` doesn't exist)
3. Creates symlinks in `~/.agentecflow/` pointing to repo
4. Creates marker file with `repo_path` field
5. Repository **persists after installation**

#### If Git is NOT Available (Fallback)
1. Downloads tarball from GitHub
2. Extracts to **permanent location** (same as above)
3. Creates symlinks and marker file
4. Repository **persists after installation**
5. **Note**: Updates require manual re-download (no `git pull`)

### Benefits

✅ **Repository files persist** - Available for Python imports
✅ **Updates work** - `git pull` in repo updates everything (symlinks point to repo)
✅ **Consistent with git clone install** - Same file structure
✅ **Graceful fallback** - Works without git (downloads tarball)
✅ **Clear repo location** - `repo_path` in marker file

---

## File Structure After Install

### Git Clone Install (Manual)
```
~/Projects/appmilla_github/taskwright/
├── installer/
│   ├── global/
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── lib/
│   │   │   └── id_generator.py  ← Python modules here
│   │   └── templates/
│   └── scripts/
│       └── install.sh
└── .git/  ← Can run git pull for updates

~/.agentecflow/
├── commands/     → symlink to repo
├── agents/       → symlink to repo
├── templates/    → user templates (NOT symlinked)
├── bin/          → command script symlinks
└── taskwright.marker.json
    {
      "repo_path": "~/Projects/appmilla_github/taskwright",
      ...
    }
```

### Curl Install (NEW - with git)
```
~/Projects/taskwright/  ← Cloned by installer
├── installer/
│   ├── global/
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── lib/
│   │   │   └── id_generator.py  ← Python modules here
│   │   └── templates/
│   └── scripts/
│       └── install.sh
└── .git/  ← Can run git pull for updates

~/.agentecflow/
├── commands/     → symlink to ~/Projects/taskwright/...
├── agents/       → symlink to ~/Projects/taskwright/...
├── templates/    → user templates (NOT symlinked)
├── bin/          → command script symlinks
└── taskwright.marker.json
    {
      "repo_path": "~/Projects/taskwright",
      ...
    }
```

### Curl Install (OLD - BROKEN)
```
~/Projects/taskwright/  ← DOES NOT EXIST!

~/.agentecflow/
├── commands/     → copied files (outdated on updates)
├── agents/       → copied files (outdated on updates)
├── templates/    → user templates
├── bin/          → command script symlinks
└── taskwright.marker.json  ← Missing repo_path!
```

---

## Import Resolution Flow

### Step 1: User Runs Command

```bash
cd ~/Projects/my-api-service
/task-create "Add user login"
```

### Step 2: Claude Code Executes task-create.md

The spec includes repository resolution code:

```python
# Find taskwright repo
def _find_taskwright_repo():
    # Check marker file first (most reliable)
    marker_json = Path.home() / ".agentecflow" / "taskwright.marker.json"
    if marker_json.exists():
        with open(marker_json) as f:
            data = json.load(f)
            repo_path = Path(data.get("repo_path", ""))
            if repo_path.exists():
                return repo_path  # ← Returns ~/Projects/taskwright

    # Fallback to common locations...
    return None

taskwright_repo = _find_taskwright_repo()
sys.path.insert(0, str(taskwright_repo))
```

### Step 3: Import Succeeds

```python
# Now Python can find the module!
from installer.global.lib.id_generator import generate_task_id
```

Path resolution:
```
sys.path = [
    "~/Projects/taskwright",  # ← Added by resolution code
    ...
]

Import: installer.global.lib.id_generator
Resolves to: ~/Projects/taskwright/installer/global/lib/id_generator.py
✅ SUCCESS
```

---

## Installation Comparison

| Method | Repository Location | Updates | Symlinks | Works? |
|--------|-------------------|---------|----------|--------|
| **Git clone (manual)** | User chooses (e.g., `~/Projects/appmilla_github/taskwright`) | `git pull` | Yes | ✅ Yes |
| **Curl install (NEW)** | Auto: `~/Projects/taskwright` | `git pull` (if git available) | Yes | ✅ Yes |
| **Curl install (OLD)** | ❌ None (temp dir deleted) | ❌ Reinstall required | No | ❌ No |

---

## User Experience

### Git Clone Install (Recommended for Developers)

```bash
# Clone to custom location
cd ~/Projects/appmilla_github
git clone https://github.com/taskwright/taskwright.git
cd taskwright
./installer/scripts/install.sh

# Updates
cd ~/Projects/appmilla_github/taskwright
git pull
# Symlinks automatically point to updated files ✅
```

**Pros**:
- ✅ Choose installation location
- ✅ Easy updates (`git pull`)
- ✅ See git history
- ✅ Can contribute changes

**Cons**:
- ⚠️ Requires git
- ⚠️ Extra step (clone before install)

### Curl Install (NEW - Convenient for Users)

```bash
# One command install
curl -sSL https://install.taskwright.dev | bash

# Updates
cd ~/Projects/taskwright
git pull
# Symlinks automatically point to updated files ✅
```

**Pros**:
- ✅ One command install
- ✅ Automatic repository setup
- ✅ Easy updates (if git available)
- ✅ Same structure as git clone

**Cons**:
- ⚠️ Fixed installation location (`~/Projects/taskwright`)
- ⚠️ Without git, updates require reinstall

---

## Edge Cases Handled

### Case 1: `~/Projects/` Doesn't Exist

```bash
# Install detects missing ~/Projects/ directory
# Falls back to ~/taskwright
curl -sSL https://install.taskwright.dev | bash

# Result
ls ~/taskwright  # ← Repository here
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
# "repo_path": "/Users/[username]/taskwright"
```

### Case 2: Repository Already Exists

```bash
# Already have ~/Projects/taskwright
ls ~/Projects/taskwright/.git  # Exists

# Run install again
curl -sSL https://install.taskwright.dev | bash

# Installer detects existing repo and updates it
cd ~/Projects/taskwright && git pull
# ✅ Updated to latest version
```

### Case 3: Git Not Available

```bash
# Machine without git
which git
# git not found

# Install uses tarball download
curl -sSL https://install.taskwright.dev | bash

# Warning: git not found - downloading tarball instead
# Installing git is recommended for easier updates

# Result
ls ~/Projects/taskwright  # ← Repository files here (no .git/)
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
# "repo_path": "/Users/[username]/Projects/taskwright"

# Updates require manual reinstall
curl -sSL https://install.taskwright.dev | bash  # Re-downloads
```

---

## Migration Path for Existing Users

### If Installed via OLD Curl Method

**Symptoms**:
- `/task-create` fails with import error
- Marker file missing `repo_path`
- No repository directory exists

**Fix**:
```bash
# Remove broken installation
rm -rf ~/.agentecflow

# Reinstall with new method
curl -sSL https://install.taskwright.dev | bash

# Verify
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
ls ~/Projects/taskwright/installer/global/lib/id_generator.py
```

### If Installed via Git Clone

**Good news**: Already working correctly!

**Optional**: Update to get latest fixes
```bash
cd ~/Projects/appmilla_github/taskwright  # Your clone location
git pull
./installer/scripts/install.sh  # Regenerates marker file with repo_path
```

---

## Testing Checklist

- [x] Fresh curl install creates permanent repository
- [x] Marker file includes `repo_path`
- [x] Task creation works from user projects
- [x] Updates work with `git pull` (if git available)
- [x] Fallback to tarball works (without git)
- [x] `~/Projects/` detection works
- [x] Existing repository detection works
- [ ] VM testing (pending user verification)

---

## Recommendation

**For public launch**: Curl install is NOW the recommended method for users.

**Installation page should say**:

```markdown
## Quick Install (Recommended)

One command to install:

\`\`\`bash
curl -sSL https://install.taskwright.dev | bash
\`\`\`

This will:
- Clone the repository to `~/Projects/taskwright`
- Install commands and agents to `~/.agentecflow/`
- Make everything available globally

## Updates

\`\`\`bash
cd ~/Projects/taskwright
git pull
\`\`\`

## Manual Install (For Contributors)

\`\`\`bash
cd ~/Projects
git clone https://github.com/taskwright/taskwright.git
cd taskwright
./installer/scripts/install.sh
\`\`\`
```

---

**Status**: Ready for VM testing and public launch ✅
