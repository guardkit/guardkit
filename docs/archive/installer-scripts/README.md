# Archived Installer Scripts

This directory contains archived installation scripts and test files that are no longer actively maintained.

## Files Archived (2025-11-26)

### PowerShell Installer (Non-Functional)

**install.ps1** (619 lines, last modified 2025-11-01)
- PowerShell installation script for Windows
- **Status**: Non-functional, archived
- **Reason**: Could not get Windows PowerShell installer working reliably
- **Replacement**: Windows users should use install.sh under WSL2 (Windows Subsystem for Linux)
- **See**: Main README.md for WSL2 installation instructions

### Test Scripts for TASK-011I

**TASK-011I-TEST-REPORT.md** (Last modified 2025-11-03)
- Test execution report for local template directory support
- 12 tests, 100% pass rate
- Historical record of TASK-011I completion

**test-task-011i.sh** (33,986 bytes, last modified 2025-10-27)
- Comprehensive test suite for TASK-011I
- Security validation, path traversal tests
- Local template directory support validation

**test-task-011i-simple.sh** (13,920 bytes, last modified 2025-10-27)
- Simplified test suite for TASK-011I
- Quick validation of core functionality

**TESTING_README.md** (Last modified 2025-11-03)
- Testing documentation for installation scripts
- Cross-platform testing guide
- Quick test instructions

### Status

All test scripts archived after successful completion and validation of TASK-011I. The work is complete and tests are no longer needed for ongoing development.

## Windows Installation (Current Approach)

For Windows users, we now recommend using WSL2 (Windows Subsystem for Linux) with the bash installer:

```bash
# 1. Install WSL2 (if not already installed)
wsl --install

# 2. Open WSL2 terminal and run bash installer
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# 3. Initialize your project
guardkit init react-typescript
```

See main README.md for complete WSL2 setup instructions.

## Active Installation Scripts

For current, maintained installation scripts, see:
- `installer/scripts/install.sh` - Primary bash installer (macOS/Linux/WSL2)
- `installer/scripts/init-project.sh` - Project initialization
- `installer/scripts/fix-zsh-path.sh` - PATH configuration utility
