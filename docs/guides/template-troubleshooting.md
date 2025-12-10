# Template Commands - Troubleshooting Guide

**Purpose**: Solutions to common issues with `/template-create` and `/template-init` commands.

**Format**: Problem → Cause → Solution

---

## Table of Contents

1. [Command Execution Issues](#command-execution-issues)
2. [Q&A Session Problems (template-init only)](#qa-session-problems)
3. [AI Analysis Failures](#ai-analysis-failures)
4. [Template Generation Issues](#template-generation-issues)
5. [Template Usage Problems](#template-usage-problems)
6. [Session Management](#session-management)
7. [Performance Issues](#performance-issues)
8. [Integration Issues](#integration-issues)

---

## Command Execution Issues

### Problem: Command Not Found

```bash
$ /template-create
bash: /template-create: No such file or directory
```

**Cause**: Command not registered in system PATH.

**Solution**:
```bash
# Check if installed
ls ~/.claude/commands/ | grep template

# If missing, reinstall
cd /path/to/guardkit
./installer/scripts/install.sh

# Verify installation
which template-create
```

### Problem: Permission Denied

```bash
$ /template-create
Permission denied
```

**Cause**: Script not executable.

**Solution**:
```bash
# Make executable
chmod +x ~/.claude/commands/template-create
chmod +x ~/.claude/commands/template-init

# Or reinstall with correct permissions
./installer/scripts/install.sh
```

### Problem: Python Not Found

```bash
$ /template-create
python3: command not found
```

**Cause**: Python 3.8+ not installed or not in PATH.

**Solution**:
```bash
# Check Python version
python3 --version

# If not installed:
# macOS:
brew install python@3.11

# Ubuntu/Debian:
sudo apt install python3.11

# Windows:
# Download from python.org

# Verify installation
python3 --version  # Should show 3.8+
```

### Problem: Module Import Errors

```bash
ModuleNotFoundError: No module named 'template_qa_session'
```

**Cause**: Python module path not configured.

**Solution**:
```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Add guardkit to path
export PYTHONPATH="$PYTHONPATH:/path/to/guardkit"

# Or add to ~/.bashrc or ~/.zshrc
echo 'export PYTHONPATH="$PYTHONPATH:/path/to/guardkit"' >> ~/.zshrc
source ~/.zshrc
```

---

## Q&A Session Problems

**Note**: Q&A sessions apply to `/template-init` only. `/template-create` uses AI-native analysis without Q&A as of TASK-51B2.

### Problem: Session Hangs on Question

```bash
Enter value:
# Cursor blinks, no response to input
```

**Cause**: Terminal input buffer issue or process hung.

**Solution**:
```bash
# Try Ctrl+C to interrupt
# Then resume:
/template-create --resume

# If that doesn't work:
# Kill process
ps aux | grep template
kill -9 <process_id>

# Delete session and restart
rm .template-create-session.json
/template-create
```

### Problem: Invalid Input Not Rejected

```bash
Template name: my template with spaces
# Accepted but causes errors later
```

**Cause**: Validation bug in older version.

**Solution**:
```bash
# Update to latest version
cd /path/to/guardkit
git pull origin main
./installer/scripts/install.sh

# Use correct format:
Template name: my-template-with-hyphens  # Correct
```

### Problem: Can't Skip Question

```bash
Enter number (default: 1):
# Want to skip but pressing Enter doesn't work
```

**Cause**: Question requires explicit input (no default).

**Solution**:
```bash
# Check if default shown:
Enter number (default: 1):  # Has default, can press Enter
Enter number:  # No default, must provide value

# If no default, must answer
# Can't skip required questions
```

### Problem: Lost Progress After Ctrl+C

```bash
# Ctrl+C during Q&A
# Restart loses all answers
```

**Cause**: Session file not saved or corrupted.

**Solution**:
```bash
# Check for session file
ls -la .template-*-session.json

# If exists, resume
/template-create --resume

# If corrupted, inspect
cat .template-create-session.json | jq .

# If completely lost, keep notes for next time
# Write answers down as you go
```

---

## AI Analysis Failures

### Problem: AI Analysis Times Out

```bash
🔍 Analyzing codebase...
  ✓ Collected 10 file samples
  ✓ Built directory tree
  ✗ AI analysis timeout after 60s
```

**Cause**: Large files, slow network, or AI service unavailable.

**Solution**:
```bash
# Try with smaller file set
/template-create --max-templates 5

# Or skip AI analysis (use heuristics)
/template-create --no-ai

# Check network
ping anthropic.com

# Try again during off-peak hours
```

### Problem: Low Confidence Score

```bash
Analysis Results:
  Confidence: 45%  # Very low
```

**Cause**: Inconsistent codebase patterns.

**Solution**:
```bash
# Clean up codebase first
# Fix inconsistent naming:
# ✗ GetProducts.cs, ProductGetter.cs, FetchProducts.cs
# ✓ GetProducts.cs, CreateProduct.cs, UpdateProduct.cs

# Ensure clear architecture:
# - Consistent layer separation
# - Clear naming patterns
# - Similar file structures

# Re-run after cleanup
/template-create
```

### Problem: Incorrect Pattern Detection

```bash
Detected Patterns:
  ✓ MVC architecture  # Wrong! It's MVVM
```

**Cause**: AI misinterpreted file structure.

**Solution**:
```bash
# Manually correct during Q&A
Architecture pattern?
  [1] MVVM  # ← Select correct one
  [2] MVC   # Ignore wrong detection

Detected: MVC (based on Controllers/ directory)
Enter number: 1  # Override detection

# Or improve codebase structure:
# Rename Controllers/ → ViewModels/
# Make architecture clearer
```

### Problem: AI Returns Empty Analysis

```bash
📊 Analysis Results:
  Technology Stack: (empty)
  Architecture: (empty)
  Patterns: (empty)
```

**Cause**: No recognizable patterns or unsupported language.

**Solution**:
```bash
# Check language support
# Supported: C#, TypeScript, Python, Java, Go, Rust

# If supported but empty:
# 1. Ensure code files present
ls -R src/ | grep -E '\.(cs|ts|py|java)$'

# 2. Check file selection
/template-create --path /correct/path

# 3. Manually specify during Q&A
# Skip auto-detection, provide manual answers
```

---

## Template Generation Issues

### Problem: No Template Files Generated

```bash
🎨 Generating templates...
  Total: 0 template files
```

**Cause**: No eligible files found or all failed validation.

**Solution**:
```bash
# Check file selection during Q&A
Example files?
  [3] Auto-select best examples  # Try this

# Or specify manually
  [2] Specific paths
Path: src/Domain/Products/GetProducts.cs
Path: src/Domain/Products/CreateProduct.cs
# ... provide multiple examples

# Ensure files have clear patterns
# AI needs recognizable structure to templatize
```

### Problem: Placeholders Not Replaced

```bash
# Generated template still has hardcoded values
namespace MyApp.Domain.Products;  # Should be {{ProjectName}}.Domain.{{EntityPlural}}
```

**Cause**: AI failed to identify placeholder candidates.

**Solution**:
```bash
# Check AI confidence
# Low confidence = poor placeholder extraction

# Manual fix:
# 1. Locate template file
cd installer/local/templates/my-template/templates/

# 2. Edit manually
vim Domain/GetEntity.cs.template

# 3. Replace manually:
# MyApp → {{ProjectName}}
# Products → {{EntityNamePlural}}
# Product → {{EntityName}}
```

### Problem: Template File Syntax Errors

```bash
# Generated template has invalid syntax
public class {{Verb}}{{Entity  # Missing closing brace
```

**Cause**: AI template extraction bug.

**Solution**:
```bash
# Fix manually
vim installer/local/templates/my-template/templates/Domain/GetEntity.cs.template

# Correct syntax:
public class {{Verb}}{{EntityNamePlural}}

# Test template
guardkit init my-template
# Verify generated file compiles
```

### Problem: manifest.json Validation Errors

```bash
Error: manifest.json invalid
  - Missing required field: 'language'
  - Invalid pattern: placeholders.ProjectName
```

**Cause**: Generation bug or manual edit error.

**Solution**:
```bash
# Validate JSON
cat installer/local/templates/my-template/manifest.json | jq .

# Fix required fields
{
  "name": "my-template",
  "language": "C#",  # Add missing fields
  "architecture": "MVVM"
}

# Validate placeholder patterns
"placeholders": {
  "ProjectName": {
    "pattern": "^[A-Za-z][A-Za-z0-9_]*$"  # Must be valid regex
  }
}
```

---

## Template Usage Problems

### Problem: Template Not Found

```bash
$ guardkit init my-template
Error: Template 'my-template' not found
```

**Cause**: Template not in search path.

**Solution**:
```bash
# Check template exists
ls installer/local/templates/ | grep my-template

# Check global templates
ls installer/core/templates/ | grep my-template

# If missing, template wasn't saved
# Re-run creation:
/template-create
# Ensure completion reaches "Template saved" message

# Verify save location
/template-create --output installer/local/templates/my-template
```

### Problem: Placeholder Values Not Replaced

```bash
# Generated code still has placeholders
namespace {{ProjectName}}.Domain.Products;  # Should be MyApp.Domain.Products
```

**Cause**: `guardkit init` failed to prompt or replace.

**Solution**:
```bash
# Check placeholder definitions in manifest.json
cat installer/local/templates/my-template/manifest.json | jq .placeholders

# Ensure required placeholders are defined
"placeholders": {
  "ProjectName": {
    "required": true,
    "pattern": "^[A-Za-z][A-Za-z0-9_]*$"
  }
}

# Re-init with explicit values
guardkit init my-template --ProjectName=MyApp
```

### Problem: Generated Project Won't Build

```bash
$ dotnet build
Error CS0103: The name 'Product' does not exist
```

**Cause**: Template missing dependencies or incomplete.

**Solution**:
```bash
# Check template completeness
cd installer/local/templates/my-template/

# Verify all templates present
ls templates/Domain/
ls templates/Data/
ls templates/ViewModels/

# Missing templates? Add manually or regenerate

# Check dependencies
cat manifest.json | jq .prerequisites

# Install required packages
dotnet add package ErrorOr
dotnet add package CommunityToolkit.Mvvm
```

---

## Session Management

### Problem: Session File Corrupted

```bash
$ /template-init --resume
Error: Session file corrupted or invalid JSON
```

**Cause**: Interrupted save or manual edit error.

**Solution**:
```bash
# Try to repair
cat .template-init-session.json | jq .
# If jq fails, file is corrupted

# Backup and delete
mv .template-init-session.json .template-init-session.json.bak
/template-init  # Start fresh

# If had important answers, try manual repair
vim .template-init-session.json.bak
# Fix JSON syntax
# Copy valid answers to new session
```

### Problem: Multiple Sessions Conflict

```bash
Warning: Multiple session files found
Which to use?
```

**Cause**: Multiple interrupted sessions or copies.

**Solution**:
```bash
# List all sessions
ls -la .template-*-session.json

# Choose correct one based on timestamp
ls -lt .template-*-session.json | head -1

# Remove old sessions
rm .template-init-session.json.old
rm .template-create-session.json.backup

# Keep only latest
```

### Problem: Can't Resume After Update

```bash
$ /template-init --resume
Error: Session version mismatch
```

**Cause**: Session from older version incompatible.

**Solution**:
```bash
# Check session version
cat .template-init-session.json | jq .session_version

# If old, must restart
rm .template-init-session.json
/template-init

# Or migrate (if migration script exists)
python scripts/migrate_session.py .template-init-session.json
```

---

## Performance Issues

### Problem: Q&A Very Slow

```bash
# Each question takes 3-5 seconds to display
```

**Cause**: Slow terminal or I/O issues.

**Solution**:
```bash
# Check terminal performance
time echo "test"  # Should be instant

# Try different terminal
# Use native terminal vs IDE terminal

# Check disk I/O
iostat 1

# If disk slow, move session file to faster drive
```

### Problem: AI Analysis Takes Forever

```bash
🔍 Analyzing codebase...
  (stuck for 5+ minutes)
```

**Cause**: Large codebase or slow AI service.

**Solution**:
```bash
# Interrupt (Ctrl+C) and limit files
/template-create --max-templates 10

# Or skip AI analysis
/template-create --no-ai

# For very large codebases:
# Pre-select representative files
/template-create
# Choose option [2] Specific paths
# Provide 5-10 best examples manually
```

### Problem: Template Generation Slow

```bash
🎨 Generating templates...
  (processing for 10+ minutes)
```

**Cause**: Generating too many templates.

**Solution**:
```bash
# Limit template count
/template-create --max-templates 15

# Or generate incrementally
# First run: Core templates
# Later: Add more as needed
```

---

## Integration Issues

### Problem: Git Integration Fails

```bash
Error: Could not determine git repository
```

**Cause**: Not in git repository or git not installed.

**Solution**:
```bash
# Check if in git repo
git status

# If not:
cd /path/to/your/git/repo
/template-create

# Check git installed
git --version

# If not:
# macOS: brew install git
# Ubuntu: sudo apt install git
```

### Problem: Template Not in Version Control

```bash
# Created template but git doesn't see it
```

**Cause**: Template created outside repository.

**Solution**:
```bash
# Check template location
/template-create --output $(pwd)/installer/local/templates/my-template

# Add to git
git add installer/local/templates/my-template/
git commit -m "Add my-template"

# Verify
git status
```

### Problem: MCP Integration Errors

```bash
Warning: MCP server 'context7' not responding
```

**Cause**: MCP server not running or misconfigured.

**Solution**:
```bash
# Check MCP servers
# See: docs/guides/context7-mcp-setup.md

# Template commands work without MCP
# MCP is optional enhancement

# To fix MCP:
# 1. Check server running
# 2. Verify configuration
# 3. Restart if needed

# Commands continue with fallback if MCP unavailable
```

---

## Common Error Messages

### "Codebase path does not exist"

**Cause**: Specified path doesn't exist or has typo.

**Solution**:
```bash
# Use tab completion
/template-create --path /Users/me/pro<TAB>

# Or use current directory
cd /path/to/codebase
/template-create  # Uses current directory
```

### "No valid template files generated"

**Cause**: No recognizable patterns or all files failed validation.

**Solution**:
```bash
# Ensure clear, consistent patterns in code
# Provide more example files (>10)
# Check files are readable
ls -l src/Domain/*.cs
```

### "Template name already exists"

**Cause**: Template with same name exists.

**Solution**:
```bash
# Choose different name
/template-create
Template name: my-template-v2

# Or overwrite (backup first)
mv installer/local/templates/my-template installer/local/templates/my-template.bak
/template-create
Template name: my-template
```

### "Permission denied writing to"

**Cause**: No write permission to template directory.

**Solution**:
```bash
# Check permissions
ls -ld installer/local/templates/

# Fix permissions
chmod u+w installer/local/templates/

# Or write to custom location
/template-create --output ~/my-templates/
```

### "AI analysis failed"

**Cause**: AI service unavailable or codebase unrecognizable.

**Solution**:
```bash
# Falls back to heuristics automatically
# Warning shown but continues

# To force heuristics only:
/template-create --no-ai

# Result: Lower confidence but still functional
```

---

## Getting Help

### Debugging Mode

```bash
# Enable verbose output
/template-create --verbose

# Shows detailed execution steps
# Helps identify where failure occurs
```

### Log Files

```bash
# Check logs
cat ~/.guardkit/logs/template-create.log
cat ~/.guardkit/logs/template-init.log

# Search for errors
grep ERROR ~/.guardkit/logs/template-create.log
```

### Reporting Issues

If problem persists:

1. **Gather Information**:
   ```bash
   # System info
   python3 --version
   git --version
   echo $SHELL

   # Error output
   /template-create 2>&1 | tee error.log

   # Session file (remove sensitive data)
   cat .template-create-session.json
   ```

2. **Check Existing Issues**:
   - [GitHub Issues](https://github.com/guardkit/guardkit/issues)
   - Search for similar problems

3. **Report Issue**:
   - Include error output
   - Provide steps to reproduce
   - Share session file (sanitized)
   - Mention system environment

4. **Community Help**:
   - [GitHub Discussions](https://github.com/guardkit/guardkit/discussions)
   - Team Slack: #guardkit-support

---

## Prevention Tips

### Before Running

1. **Prepare Codebase**:
   - Consistent naming
   - Clear architecture
   - Clean file structure

2. **Check Prerequisites**:
   - Python 3.8+
   - Git (if using git integration)
   - Disk space (>100MB for templates)

3. **Read Documentation**:
   - [Getting Started](./template-commands-getting-started.md)
   - [Walkthrough guides](./template-create-walkthrough.md)

### During Execution

1. **Save Progress**:
   - Use Ctrl+C frequently to save
   - Keep session file backed up

2. **Validate Input**:
   - Double-check paths
   - Verify template names
   - Review summaries

3. **Monitor Output**:
   - Watch for warnings
   - Note low confidence scores
   - Check for errors

### After Generation

1. **Test Immediately**:
   ```bash
   guardkit init my-template
   dotnet build
   dotnet test
   ```

2. **Verify Files**:
   - Check all expected files generated
   - Verify placeholders work
   - Test builds successfully

3. **Document Issues**:
   - Note any problems
   - Record solutions
   - Update template as needed

---

## Quick Reference

### Checklist for Failed Template Creation

```
□ Checked Python version (3.8+)?
□ Verified codebase path exists?
□ Confirmed consistent naming patterns?
□ Tried with --max-templates limit?
□ Checked session file exists if resuming?
□ Reviewed error logs?
□ Tested with --verbose flag?
□ Tried --no-ai fallback?
□ Checked disk space available?
□ Verified write permissions?
```

### Common Commands

```bash
# Retry with limits
/template-create --max-templates 10

# Skip AI
/template-create --no-ai

# Verbose output
/template-create --verbose

# Custom location
/template-create --output /custom/path

# Resume session
/template-create --resume

# Clean start
rm .template-create-session.json
/template-create
```

---

## Next Steps

- **Main Guide**: [template-commands-getting-started.md](./template-commands-getting-started.md)
- **Walkthroughs**: [template-create-walkthrough.md](./template-create-walkthrough.md)
- **Report Issues**: [GitHub Issues](https://github.com/guardkit/guardkit/issues)

---

**Created**: 2025-11-06
**Task**: TASK-014
**Version**: 1.0.0
**Maintained By**: Platform Team
