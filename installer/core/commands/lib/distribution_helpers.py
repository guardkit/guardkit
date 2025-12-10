"""
Distribution Helper Utilities

Utilities to help teams distribute templates:
- Git commit/tag helpers
- Usage instructions generator
- Sharing guide (git, package, registry)
- Installation verification

TASK-012: Template Packaging & Distribution (Sub-task 4: TASK-064)
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class GitOperationResult:
    """Result of git operation."""

    success: bool
    command: str
    output: str = ""
    error: str = ""


class DistributionHelper:
    """
    Helper utilities for distributing templates.

    Features:
    - Git commit helper with template metadata
    - Git tag helper with semantic versioning
    - Usage instructions generator
    - Sharing guide generator (multiple distribution methods)
    - Installation verification script generator

    Example:
        helper = DistributionHelper(template_path=Path("templates/my-template"))

        # Commit template to git
        result = helper.create_git_commit("Add my-template v1.0.0")

        # Create version tag
        helper.create_git_tag("1.0.0")

        # Generate documentation
        helper.generate_usage_instructions(output_path=Path("USAGE.md"))
        helper.generate_sharing_guide(output_path=Path("SHARING.md"))
    """

    def __init__(self, template_path: Path):
        """
        Initialize distribution helper.

        Args:
            template_path: Path to template directory
        """
        self.template_path = template_path

        if not template_path.exists():
            raise FileNotFoundError(f"Template path does not exist: {template_path}")

    def create_git_commit(
        self,
        message: str,
        add_files: bool = True
    ) -> GitOperationResult:
        """
        Create git commit for template.

        Args:
            message: Commit message
            add_files: Whether to git add files first (default: True)

        Returns:
            GitOperationResult with operation details
        """
        try:
            if add_files:
                # Add template files
                add_result = self._run_git_command(
                    ["git", "add", str(self.template_path)]
                )
                if not add_result.success:
                    return add_result

            # Create commit
            commit_result = self._run_git_command(
                ["git", "commit", "-m", message]
            )

            return commit_result

        except Exception as e:
            return GitOperationResult(
                success=False,
                command="git commit",
                error=str(e)
            )

    def create_git_tag(
        self,
        version: str,
        message: Optional[str] = None,
        annotated: bool = True
    ) -> GitOperationResult:
        """
        Create git tag for template version.

        Args:
            version: Version string (e.g., "1.0.0")
            message: Optional tag message (default: "Release v{version}")
            annotated: Whether to create annotated tag (default: True)

        Returns:
            GitOperationResult
        """
        try:
            template_name = self.template_path.name
            tag_name = f"{template_name}-v{version}"

            if message is None:
                message = f"Release {template_name} v{version}"

            if annotated:
                cmd = ["git", "tag", "-a", tag_name, "-m", message]
            else:
                cmd = ["git", "tag", tag_name]

            return self._run_git_command(cmd)

        except Exception as e:
            return GitOperationResult(
                success=False,
                command="git tag",
                error=str(e)
            )

    def push_to_remote(
        self,
        remote: str = "origin",
        push_tags: bool = True
    ) -> GitOperationResult:
        """
        Push commits and tags to remote repository.

        Args:
            remote: Remote name (default: "origin")
            push_tags: Whether to push tags (default: True)

        Returns:
            GitOperationResult
        """
        try:
            # Push commits
            push_result = self._run_git_command(
                ["git", "push", remote]
            )

            if not push_result.success:
                return push_result

            # Push tags if requested
            if push_tags:
                tags_result = self._run_git_command(
                    ["git", "push", remote, "--tags"]
                )
                return tags_result

            return push_result

        except Exception as e:
            return GitOperationResult(
                success=False,
                command="git push",
                error=str(e)
            )

    def generate_usage_instructions(
        self,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate usage instructions for template.

        Args:
            output_path: Optional path to save instructions (default: template_path/USAGE.md)

        Returns:
            Usage instructions as markdown string
        """
        template_name = self.template_path.name

        # Load manifest for details
        manifest = self._load_manifest()
        description = manifest.get("template", {}).get("description", "No description")
        version = manifest.get("template", {}).get("version", "unknown")

        instructions = f"""# Using {template_name} Template

Version: {version}

## Description

{description}

## Installation

### Method 1: From Local Directory

If you have the template in your local filesystem:

```bash
# Copy to project templates directory
cp -r {template_name} /path/to/your/project/.claude/templates/

# Initialize project
cd /path/to/your/project
guardkit init {template_name}
```

### Method 2: From Package (.tar.gz)

If you have a template package:

```bash
# Extract package
tar -xzf {template_name}-{version}.tar.gz

# Copy to project
cp -r {template_name} /path/to/your/project/.claude/templates/

# Initialize project
cd /path/to/your/project
guardkit init {template_name}
```

### Method 3: From Git Repository

If template is in a git repository:

```bash
# Clone repository
git clone <repository-url>

# Copy template
cp -r <repo-path>/{template_name} /path/to/your/project/.claude/templates/

# Initialize project
cd /path/to/your/project
guardkit init {template_name}
```

## Usage

After installation, initialize a new project:

```bash
guardkit init {template_name}
```

This will:
1. Copy template files to your project
2. Set up AI agents for your stack
3. Configure project settings
4. Create initial project structure

## Next Steps

After initialization:

1. Review the generated project structure
2. Customize agent configurations if needed
3. Start building with `/task-create "Your first task"`

## Template Contents

{self._format_template_contents(manifest)}

## Support

For issues or questions about this template:
- Check the template CLAUDE.md for detailed guidance
- Review manifest.json for configuration options
- Consult the agents/ directory for AI agent capabilities

## Customization

You can customize this template by:
1. Modifying template files in the templates/ directory
2. Adding custom agents in the agents/ directory
3. Adjusting settings in settings.json
4. Updating patterns in CLAUDE.md

See CUSTOMIZATION.md for detailed customization guide.
"""

        # Save if output path provided
        if output_path is None:
            output_path = self.template_path / "USAGE.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(instructions)

        return instructions

    def generate_sharing_guide(
        self,
        output_path: Optional[Path] = None,
        include_registry: bool = False
    ) -> str:
        """
        Generate sharing guide for template distribution.

        Args:
            output_path: Optional path to save guide (default: template_path/SHARING.md)
            include_registry: Whether to include registry instructions (default: False)

        Returns:
            Sharing guide as markdown string
        """
        template_name = self.template_path.name
        manifest = self._load_manifest()
        version = manifest.get("template", {}).get("version", "unknown")

        guide = f"""# Sharing {template_name} Template

This guide explains how to share this template with your team or the community.

## Method 1: Git Repository (Recommended for Teams)

### Initial Setup

```bash
# Add template to git
git add {template_name}/
git commit -m "Add {template_name} template v{version}"

# Tag the version
git tag -a {template_name}-v{version} -m "Release {template_name} v{version}"

# Push to remote
git push origin main
git push origin --tags
```

### Team Members Installation

```bash
# Clone repository
git clone <your-repo-url>

# Copy template to their project
cp -r <repo>/{template_name} ~/.claude/templates/

# Or install globally
./installer/scripts/install.sh
```

### Updating

```bash
# Pull latest changes
git pull origin main

# Check for new version tags
git tag -l "{template_name}-v*"

# Checkout specific version
git checkout {template_name}-v{version}
```

## Method 2: Package Distribution (.tar.gz)

### Create Package

```bash
# Install packaging tools (if not already installed)
pip install -r requirements.txt

# Create package
python -m installer.core.commands.lib.template_packager \\
    --template {template_name} \\
    --output ./dist

# This creates:
# - {template_name}-{version}.tar.gz (package)
# - {template_name}-{version}.tar.gz.sha256 (checksum)
# - {template_name}-{version}.metadata.json (metadata)
# - {template_name}-{version}.README.md (instructions)
```

### Distribute Package

Share the following files:
- `{template_name}-{version}.tar.gz` - The template package
- `{template_name}-{version}.tar.gz.sha256` - Checksum for verification
- `{template_name}-{version}.README.md` - Installation instructions

Options for distribution:
1. **Internal file share**: Copy to shared network drive
2. **Cloud storage**: Upload to Dropbox, Google Drive, etc.
3. **Package server**: Host on internal artifact repository
4. **Email**: Attach to email (if small enough)

### Installation from Package

```bash
# Download package files
wget <package-url>/{template_name}-{version}.tar.gz
wget <package-url>/{template_name}-{version}.tar.gz.sha256

# Verify integrity
sha256sum -c {template_name}-{version}.tar.gz.sha256

# Extract
tar -xzf {template_name}-{version}.tar.gz

# Install
cp -r {template_name} ~/.claude/templates/
```

## Method 3: Direct Copy (Simple for Small Teams)

### Share via Network/USB

```bash
# Copy entire template directory
cp -r {template_name} /path/to/shared/location/

# Team members copy to their machine
cp -r /path/to/shared/location/{template_name} ~/.claude/templates/
```

{'## Method 4: Template Registry (Coming Soon)' if include_registry else ''}

{f'''### Publish to Registry

```bash
# Login to registry
guardkit registry login

# Publish template
guardkit registry publish {template_name}

# Team members install
guardkit registry install {template_name}
```

### Update Template

```bash
# Update version in manifest.json
# Update changelog

# Publish new version
guardkit registry publish {template_name} --version {version}
```
''' if include_registry else ''}

## Verification

After installation, verify the template works:

```bash
# Create test project
mkdir test-project
cd test-project

# Initialize with template
guardkit init {template_name}

# Verify structure
ls -la

# Verify agents
ls -la .claude/agents/

# Run validation
guardkit doctor
```

## Version Management

### Semantic Versioning

This template uses semantic versioning (major.minor.patch):
- **Major**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **Minor**: New features, backward compatible (e.g., 1.0.0 → 1.1.0)
- **Patch**: Bug fixes (e.g., 1.0.0 → 1.0.1)

### Changelog

Always update the changelog in manifest.json when releasing:

```json
{{
  "changelog": [
    {{
      "version": "{version}",
      "date": "{datetime.utcnow().isoformat()[:10]}",
      "changes": [
        "Added new feature X",
        "Fixed bug Y"
      ]
    }}
  ]
}}
```

## Best Practices

1. **Version Everything**: Always tag git commits with version numbers
2. **Document Changes**: Keep changelog up to date
3. **Test Before Sharing**: Verify template works on clean project
4. **Provide Examples**: Include example projects or screenshots
5. **Support Your Users**: Provide contact information for support

## Troubleshooting

Common issues and solutions:

### Template Not Found
- Verify template is in correct directory (~/.claude/templates/)
- Check manifest.json exists and is valid JSON

### Version Conflicts
- Check installed version: `cat ~/.claude/templates/{template_name}/manifest.json`
- Update to latest: re-copy from source

### Missing Dependencies
- Review manifest.json for required tools
- Install dependencies: `pip install -r requirements.txt` (if applicable)

## Getting Help

- Template documentation: See CLAUDE.md in template directory
- Project documentation: https://github.com/agentecflow/ai-engineer
- Issues: Open issue on GitHub repository

---

Generated: {datetime.utcnow().isoformat()[:10]}
Template: {template_name} v{version}
"""

        # Save if output path provided
        if output_path is None:
            output_path = self.template_path / "SHARING.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(guide)

        return guide

    def generate_verification_script(
        self,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate installation verification script.

        Args:
            output_path: Optional path to save script (default: template_path/verify.sh)

        Returns:
            Verification script as string
        """
        template_name = self.template_path.name

        script = f"""#!/bin/bash
# Template Installation Verification Script
# Template: {template_name}
# Generated: {datetime.utcnow().isoformat()[:10]}

set -e

echo "========================================"
echo "Template Installation Verification"
echo "Template: {template_name}"
echo "========================================"
echo ""

# Check template directory exists
echo "Checking template directory..."
if [ -d "$HOME/.claude/templates/{template_name}" ]; then
    echo "✓ Template directory found"
else
    echo "✗ Template directory not found"
    echo "  Expected: $HOME/.claude/templates/{template_name}"
    exit 1
fi

# Check manifest.json exists and is valid
echo ""
echo "Checking manifest.json..."
MANIFEST="$HOME/.claude/templates/{template_name}/manifest.json"
if [ -f "$MANIFEST" ]; then
    echo "✓ manifest.json found"

    # Validate JSON
    if command -v jq &> /dev/null; then
        if jq empty "$MANIFEST" 2>/dev/null; then
            echo "✓ manifest.json is valid JSON"

            # Check version
            VERSION=$(jq -r '.template.version' "$MANIFEST")
            echo "  Version: $VERSION"
        else
            echo "✗ manifest.json is invalid JSON"
            exit 1
        fi
    fi
else
    echo "✗ manifest.json not found"
    exit 1
fi

# Check required directories
echo ""
echo "Checking template structure..."
DIRS=("agents" "templates")
for DIR in "${{DIRS[@]}}"; do
    if [ -d "$HOME/.claude/templates/{template_name}/$DIR" ]; then
        COUNT=$(find "$HOME/.claude/templates/{template_name}/$DIR" -type f | wc -l)
        echo "✓ $DIR/ directory exists ($COUNT files)"
    else
        echo "⚠ $DIR/ directory not found (optional)"
    fi
done

# Check CLAUDE.md exists
echo ""
echo "Checking documentation..."
if [ -f "$HOME/.claude/templates/{template_name}/CLAUDE.md" ]; then
    echo "✓ CLAUDE.md found"
else
    echo "⚠ CLAUDE.md not found (optional)"
fi

# Try to initialize test project (dry run)
echo ""
echo "Testing template initialization (dry run)..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

if command -v guardkit &> /dev/null; then
    echo "✓ guardkit command available"
    # Note: Actual dry-run would need to be implemented in guardkit
    echo "  (Skipping actual initialization test)"
else
    echo "⚠ guardkit command not found"
    echo "  Install guardkit to test initialization"
fi

# Cleanup
cd -
rm -rf "$TEMP_DIR"

echo ""
echo "========================================"
echo "✓ Verification Complete"
echo "========================================"
echo ""
echo "Template {template_name} is properly installed."
echo "You can now use it with: guardkit init {template_name}"
"""

        # Save if output path provided
        if output_path is None:
            output_path = self.template_path / "verify.sh"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script)

        # Make script executable
        output_path.chmod(0o755)

        return script

    def _run_git_command(self, cmd: List[str]) -> GitOperationResult:
        """
        Run git command and capture result.

        Args:
            cmd: Command and arguments as list

        Returns:
            GitOperationResult
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=self.template_path.parent,
                capture_output=True,
                text=True,
                check=True
            )

            return GitOperationResult(
                success=True,
                command=" ".join(cmd),
                output=result.stdout
            )

        except subprocess.CalledProcessError as e:
            return GitOperationResult(
                success=False,
                command=" ".join(cmd),
                output=e.stdout,
                error=e.stderr
            )
        except FileNotFoundError:
            return GitOperationResult(
                success=False,
                command=" ".join(cmd),
                error="Git command not found. Is git installed?"
            )

    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json from template."""
        import json

        manifest_path = self.template_path / "manifest.json"

        if not manifest_path.exists():
            return {}

        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _format_template_contents(self, manifest: Dict[str, Any]) -> str:
        """Format template contents for documentation."""
        lines = []

        # Stack
        stack = manifest.get("stack", {})
        if stack:
            lines.append("### Technology Stack")
            lines.append("")
            for key, value in stack.items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")

        # Agents
        agents = manifest.get("agents", [])
        if agents:
            lines.append(f"### AI Agents ({len(agents)})")
            lines.append("")
            for agent in agents:
                lines.append(f"- {agent}")
            lines.append("")

        return "\n".join(lines) if lines else "See manifest.json for contents"


# Module exports
__all__ = [
    "DistributionHelper",
    "GitOperationResult",
]
