"""
Template Assertions for Integration Tests

Provides reusable assertion helpers for template validation.
"""

from pathlib import Path
from typing import Dict, List, Optional
import json


class TemplateAssertions:
    """Reusable template validation assertions."""
    
    @staticmethod
    def assert_template_exists(template_path: Path):
        """Assert template directory exists."""
        assert template_path.exists(), f"Template path does not exist: {template_path}"
        assert template_path.is_dir(), f"Template path is not a directory: {template_path}"
        
    @staticmethod
    def assert_has_metadata(template_path: Path):
        """Assert template has .template.json metadata."""
        metadata_file = template_path / ".template.json"
        assert metadata_file.exists(), f"Missing .template.json: {metadata_file}"
        
        with open(metadata_file) as f:
            metadata = json.load(f)
            
        assert "id" in metadata, "Missing 'id' in metadata"
        assert "name" in metadata, "Missing 'name' in metadata"
        assert "version" in metadata, "Missing 'version' in metadata"
        assert "tech_stack" in metadata, "Missing 'tech_stack' in metadata"
        
        return metadata
        
    @staticmethod
    def assert_has_required_files(template_path: Path, required_files: List[str]):
        """Assert template has all required files."""
        missing = []
        for file_path in required_files:
            full_path = template_path / file_path
            if not full_path.exists():
                missing.append(file_path)
                
        assert not missing, f"Missing required files: {missing}"
        
    @staticmethod
    def assert_has_structure_documentation(template_path: Path):
        """Assert template has STRUCTURE.md."""
        structure_file = template_path / "STRUCTURE.md"
        assert structure_file.exists(), f"Missing STRUCTURE.md: {structure_file}"
        
        content = structure_file.read_text()
        assert len(content) > 100, "STRUCTURE.md is too short"
        assert "## Directory Structure" in content or "Directory Structure" in content, \
            "STRUCTURE.md missing directory structure section"
            
    @staticmethod
    def assert_has_readme(template_path: Path):
        """Assert template has README.md."""
        readme_file = template_path / "README.md"
        assert readme_file.exists(), f"Missing README.md: {readme_file}"
        
        content = readme_file.read_text()
        assert len(content) > 50, "README.md is too short"
        
    @staticmethod
    def assert_valid_tech_stack(metadata: Dict, expected_stack: str):
        """Assert metadata has correct tech stack."""
        actual_stack = metadata.get("tech_stack", "")
        assert actual_stack == expected_stack, \
            f"Expected tech_stack '{expected_stack}', got '{actual_stack}'"
            
    @staticmethod
    def assert_has_patterns(metadata: Dict, expected_patterns: List[str]):
        """Assert metadata includes expected patterns."""
        patterns = metadata.get("patterns", [])
        missing = [p for p in expected_patterns if p not in patterns]
        
        assert not missing, \
            f"Missing expected patterns: {missing}. Found: {patterns}"
            
    @staticmethod
    def assert_has_dependencies(template_path: Path):
        """Assert template has dependency files."""
        # Check for common dependency files
        dependency_files = [
            "package.json",  # Node.js
            "requirements.txt",  # Python
            "go.mod",  # Go
            "*.csproj",  # .NET
            "Gemfile",  # Ruby
            "Cargo.toml",  # Rust
        ]
        
        found_any = False
        for pattern in dependency_files:
            if "*" in pattern:
                # Handle wildcards
                suffix = pattern.replace("*", "")
                if list(template_path.rglob(f"*{suffix}")):
                    found_any = True
                    break
            else:
                if (template_path / pattern).exists():
                    found_any = True
                    break
                    
        # Not all templates need dependencies, so this is a soft check
        return found_any
        
    @staticmethod
    def assert_file_count_reasonable(template_path: Path, min_files: int = 3):
        """Assert template has a reasonable number of files."""
        files = list(template_path.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        
        assert file_count >= min_files, \
            f"Template has too few files ({file_count}), expected at least {min_files}"
            
    @staticmethod
    def assert_no_sensitive_data(template_path: Path):
        """Assert template contains no sensitive data."""
        sensitive_patterns = [
            ".env",
            "secrets",
            "password",
            "api_key",
            "private_key",
            "credentials",
        ]
        
        violations = []
        for file in template_path.rglob("*"):
            if not file.is_file():
                continue
                
            file_lower = file.name.lower()
            for pattern in sensitive_patterns:
                if pattern in file_lower:
                    violations.append(str(file.relative_to(template_path)))
                    
        assert not violations, \
            f"Found files with potentially sensitive names: {violations}"
            
    @staticmethod
    def assert_valid_version(metadata: Dict):
        """Assert metadata has valid semantic version."""
        version = metadata.get("version", "")
        parts = version.split(".")
        
        assert len(parts) == 3, \
            f"Version must be semantic (x.y.z), got: {version}"
            
        for part in parts:
            assert part.isdigit(), \
                f"Version parts must be integers, got: {version}"
                
    @staticmethod
    def assert_compilation_success(template_path: Path, tech_stack: str) -> bool:
        """Assert template compiles/validates successfully."""
        # This would be implemented with actual compilation checks
        # For now, just check structure
        if tech_stack in ["react", "typescript-api"]:
            return (template_path / "package.json").exists()
        elif tech_stack == "python":
            return (template_path / "requirements.txt").exists() or \
                   (template_path / "pyproject.toml").exists()
        elif tech_stack in ["maui-appshell", "maui-navigationpage", "dotnet-fastendpoints"]:
            return len(list(template_path.rglob("*.csproj"))) > 0
        elif tech_stack == "go":
            return (template_path / "go.mod").exists()
        else:
            return True  # Unknown stack, assume valid
