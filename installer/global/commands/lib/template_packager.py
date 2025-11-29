"""
Template Packaging System

Creates distributable .tar.gz packages from template directories with:
- Compressed archive creation
- SHA256 checksum generation
- Package metadata
- Distribution README

TASK-012: Template Packaging & Distribution (Sub-task 1: TASK-061)
"""

import hashlib
import json
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class PackageMetadata:
    """Metadata for a template package."""

    template_name: str
    version: str
    package_file: str
    checksum_sha256: str
    size_bytes: int
    created_at: str
    files_included: List[str] = field(default_factory=list)
    manifest: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "template_name": self.template_name,
            "version": self.version,
            "package_file": self.package_file,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "files_included": self.files_included,
            "manifest": self.manifest
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageMetadata":
        """Create from dictionary."""
        return cls(
            template_name=data["template_name"],
            version=data["version"],
            package_file=data["package_file"],
            checksum_sha256=data["checksum_sha256"],
            size_bytes=data["size_bytes"],
            created_at=data["created_at"],
            files_included=data.get("files_included", []),
            manifest=data.get("manifest")
        )


class TemplatePackager:
    """
    Creates distributable .tar.gz packages from template directories.

    Features:
    - Compresses template directory to .tar.gz
    - Generates SHA256 checksums for integrity verification
    - Creates package metadata JSON
    - Generates distribution README with installation instructions

    Example:
        packager = TemplatePackager(template_path=Path("templates/my-template"))
        result = packager.package(output_dir=Path("./dist"))
        print(f"Package: {result.package_file}")
        print(f"Checksum: {result.checksum_sha256}")
    """

    def __init__(self, template_path: Path):
        """
        Initialize packager.

        Args:
            template_path: Path to template directory to package
        """
        self.template_path = template_path

        if not template_path.exists():
            raise FileNotFoundError(f"Template path does not exist: {template_path}")

        if not template_path.is_dir():
            raise ValueError(f"Template path must be a directory: {template_path}")

    def package(
        self,
        output_dir: Path,
        version: Optional[str] = None,
        include_readme: bool = True
    ) -> PackageMetadata:
        """
        Create package from template directory.

        Args:
            output_dir: Directory to save package files
            version: Optional version string (extracted from manifest if not provided)
            include_readme: Whether to generate distribution README

        Returns:
            PackageMetadata with package details
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load manifest to get version and metadata
        manifest = self._load_manifest()
        if version is None:
            version = manifest.get("template", {}).get("version", "1.0.0")

        template_name = self.template_path.name

        # Create package filename
        package_filename = f"{template_name}-{version}.tar.gz"
        package_path = output_dir / package_filename

        # Create tar.gz archive
        files_included = self._create_tarball(package_path)

        # Generate checksum
        checksum = self._generate_checksum(package_path)

        # Create metadata
        metadata = PackageMetadata(
            template_name=template_name,
            version=version,
            package_file=package_filename,
            checksum_sha256=checksum,
            size_bytes=package_path.stat().st_size,
            created_at=datetime.utcnow().isoformat() + "Z",
            files_included=files_included,
            manifest=manifest
        )

        # Save metadata JSON
        metadata_path = output_dir / f"{template_name}-{version}.metadata.json"
        self._save_metadata(metadata, metadata_path)

        # Save checksum file
        checksum_path = output_dir / f"{package_filename}.sha256"
        self._save_checksum(checksum, package_filename, checksum_path)

        # Generate distribution README
        if include_readme:
            readme_path = output_dir / f"{template_name}-{version}.README.md"
            self._generate_readme(metadata, readme_path)

        return metadata

    def _create_tarball(self, output_path: Path) -> List[str]:
        """
        Create tar.gz archive from template directory.

        Args:
            output_path: Path to save .tar.gz file

        Returns:
            List of included file paths
        """
        files_included = []

        with tarfile.open(output_path, "w:gz") as tar:
            # Add template directory with relative path
            arcname = self.template_path.name
            tar.add(self.template_path, arcname=arcname)

            # Collect file list
            for root, dirs, files in self.template_path.walk():
                for file in files:
                    file_path = root / file
                    relative_path = file_path.relative_to(self.template_path.parent)
                    files_included.append(str(relative_path))

        return sorted(files_included)

    def _generate_checksum(self, file_path: Path) -> str:
        """
        Generate SHA256 checksum for file.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 checksum
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json from template directory."""
        manifest_path = self.template_path / "manifest.json"

        if not manifest_path.exists():
            return {}

        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_metadata(self, metadata: PackageMetadata, output_path: Path) -> None:
        """Save package metadata to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

    def _save_checksum(self, checksum: str, filename: str, output_path: Path) -> None:
        """
        Save checksum to file in standard format.

        Format: <checksum>  <filename>
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"{checksum}  {filename}\n")

    def _generate_readme(self, metadata: PackageMetadata, output_path: Path) -> None:
        """Generate distribution README with installation instructions."""
        template_name = metadata.template_name
        version = metadata.version
        package_file = metadata.package_file
        checksum = metadata.checksum_sha256

        manifest = metadata.manifest or {}
        description = manifest.get("template", {}).get("description", "No description")
        author = manifest.get("template", {}).get("author", "Unknown")

        readme_content = f"""# {template_name} Template Distribution Package

Version: {version}
Author: {author}

## Description

{description}

## Package Contents

- **Package**: `{package_file}`
- **Size**: {self._format_size(metadata.size_bytes)}
- **Checksum (SHA256)**: `{checksum}`
- **Files**: {len(metadata.files_included)} files included

## Installation

### Method 1: Local Template Directory

```bash
# Extract package
tar -xzf {package_file}

# Copy to local templates directory
cp -r {template_name} /path/to/your/project/.claude/templates/

# Or copy to global templates directory (requires installation)
cp -r {template_name} ~/.agentecflow/templates/
```

### Method 2: Using taskwright init

```bash
# Extract package
tar -xzf {package_file}

# Initialize project with template
cd your-project
taskwright init {template_name}
```

## Verification

Verify package integrity before installation:

```bash
# Check SHA256 checksum
sha256sum -c {package_file}.sha256

# Or manually compare
sha256sum {package_file}
# Should match: {checksum}
```

## Usage

After installation, initialize a new project:

```bash
taskwright init {template_name}
```

## Template Contents

This package includes:

{self._format_manifest_contents(manifest)}

## Support

For issues or questions, contact: {author}

## Package Metadata

- **Created**: {metadata.created_at}
- **Metadata File**: `{template_name}-{version}.metadata.json`

---

Generated by Taskwright Template Packaging System
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

    def _format_size(self, size_bytes: int) -> str:
        """Format byte size as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _format_manifest_contents(self, manifest: Dict[str, Any]) -> str:
        """Format manifest contents for README."""
        lines = []

        # Stack information
        stack = manifest.get("stack", {})
        if stack:
            lines.append("### Technology Stack\n")
            for key, value in stack.items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")

        # Agents
        agents = manifest.get("agents", [])
        if agents:
            lines.append(f"### AI Agents ({len(agents)})\n")
            for agent in agents[:5]:
                lines.append(f"- {agent}")
            if len(agents) > 5:
                lines.append(f"- ... and {len(agents) - 5} more")
            lines.append("")

        # Templates
        templates = manifest.get("templates", {})
        if templates:
            lines.append(f"### Template Files ({len(templates)} categories)\n")
            for category, info in templates.items():
                desc = info.get("description", "") if isinstance(info, dict) else ""
                lines.append(f"- **{category}**: {desc}")
            lines.append("")

        return "\n".join(lines) if lines else "- See manifest.json for full contents"


def verify_package(package_path: Path, checksum_path: Path) -> bool:
    """
    Verify package integrity using checksum file.

    Args:
        package_path: Path to .tar.gz package
        checksum_path: Path to .sha256 checksum file

    Returns:
        True if checksum matches, False otherwise
    """
    # Read expected checksum
    with open(checksum_path, "r", encoding="utf-8") as f:
        expected_checksum = f.read().strip().split()[0]

    # Calculate actual checksum
    packager = TemplatePackager(package_path.parent)
    actual_checksum = packager._generate_checksum(package_path)

    return actual_checksum == expected_checksum


# Module exports
__all__ = [
    "TemplatePackager",
    "PackageMetadata",
    "verify_package",
]
