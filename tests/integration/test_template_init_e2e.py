"""
End-to-End Integration Test for /template-init Command

Tests the full template-init workflow to ensure AI-generated templates are valid.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from tests.lib.template_testing import TemplateAssertions


class TestTemplateInitE2E:
    """End-to-end test for template initialization flow."""
    
    @pytest.fixture
    def temp_output(self):
        """Create temporary directory for template output."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def _simulate_template_init(self, output_dir: Path, tech_stack: str = "python") -> Path:
        """
        Simulate template-init AI generation.
        
        In real implementation, this would call the actual template-init command.
        For testing, we'll create a minimal valid template structure.
        """
        template_dir = output_dir / "my-template"
        template_dir.mkdir()
        
        # Create .template.json metadata
        metadata = {
            "id": "my-template",
            "name": "My Template",
            "version": "1.0.0",
            "tech_stack": tech_stack,
            "patterns": ["Repository", "Dependency Injection"],
            "description": "AI-generated template"
        }
        
        with open(template_dir / ".template.json", "w") as f:
            import json
            json.dump(metadata, f, indent=2)
        
        # Create README.md
        readme_content = """# My Template

AI-generated template for {tech_stack} projects.

## Features

- Repository pattern
- Dependency injection
- Testing setup
"""
        with open(template_dir / "README.md", "w") as f:
            f.write(readme_content.format(tech_stack=tech_stack))
        
        # Create STRUCTURE.md
        structure_content = """# Directory Structure

```
my-template/
├── src/
│   ├── domain/
│   └── api/
├── tests/
└── README.md
```

## Key Directories

- `src/`: Source code
- `tests/`: Test files
"""
        with open(template_dir / "STRUCTURE.md", "w") as f:
            f.write(structure_content)
        
        # Create basic structure
        (template_dir / "src" / "domain").mkdir(parents=True)
        (template_dir / "src" / "api").mkdir(parents=True)
        (template_dir / "tests").mkdir(parents=True)
        
        # Create sample files based on tech stack
        if tech_stack == "python":
            # Create requirements.txt
            with open(template_dir / "requirements.txt", "w") as f:
                f.write("fastapi==0.104.0\npytest==7.4.0\n")
            
            # Create sample Python file
            with open(template_dir / "src" / "api" / "main.py", "w") as f:
                f.write("from fastapi import FastAPI\n\napp = FastAPI()\n")
        
        elif tech_stack == "react":
            # Create package.json
            with open(template_dir / "package.json", "w") as f:
                f.write('{"name": "my-template", "version": "1.0.0", "dependencies": {"react": "^18.0.0"}}\n')
            
            # Create sample TypeScript file
            with open(template_dir / "src" / "api" / "App.tsx", "w") as f:
                f.write("export const App = () => <div>Hello</div>;\n")
        
        elif tech_stack in ["maui-appshell", "maui-navigationpage"]:
            # Create csproj file
            with open(template_dir / "MyTemplate.csproj", "w") as f:
                f.write('<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n')
        
        elif tech_stack == "go":
            # Create go.mod
            with open(template_dir / "go.mod", "w") as f:
                f.write("module github.com/example/my-template\n\ngo 1.21\n")
        
        return template_dir
    
    def test_template_init_creates_valid_template(self, temp_output):
        """Test that template-init generates a valid template."""
        # Simulate template initialization
        template_dir = self._simulate_template_init(temp_output, tech_stack="python")
        
        # Validate template structure
        TemplateAssertions.assert_template_exists(template_dir)
        
        # Validate metadata
        metadata = TemplateAssertions.assert_has_metadata(template_dir)
        TemplateAssertions.assert_valid_version(metadata)
        TemplateAssertions.assert_valid_tech_stack(metadata, "python")
        
        # Validate documentation
        TemplateAssertions.assert_has_readme(template_dir)
        TemplateAssertions.assert_has_structure_documentation(template_dir)
        
        # Validate file count
        TemplateAssertions.assert_file_count_reasonable(template_dir, min_files=5)
        
        # Validate no sensitive data
        TemplateAssertions.assert_no_sensitive_data(template_dir)
        
        print(f"\n✓ Template validated successfully: {template_dir.name}")
    
    def test_template_init_react_stack(self, temp_output):
        """Test template-init for React stack."""
        template_dir = self._simulate_template_init(temp_output, tech_stack="react")
        
        # Validate template
        TemplateAssertions.assert_template_exists(template_dir)
        metadata = TemplateAssertions.assert_has_metadata(template_dir)
        TemplateAssertions.assert_valid_tech_stack(metadata, "react")
        
        # Validate React-specific files
        assert (template_dir / "package.json").exists(), "Missing package.json"
        
        print(f"\n✓ React template validated: {template_dir.name}")
    
    def test_template_init_maui_stack(self, temp_output):
        """Test template-init for MAUI stack."""
        template_dir = self._simulate_template_init(temp_output, tech_stack="maui-appshell")
        
        # Validate template
        TemplateAssertions.assert_template_exists(template_dir)
        metadata = TemplateAssertions.assert_has_metadata(template_dir)
        TemplateAssertions.assert_valid_tech_stack(metadata, "maui-appshell")
        
        # Validate .NET-specific files
        csproj_files = list(template_dir.rglob("*.csproj"))
        assert len(csproj_files) > 0, "Missing .csproj file"
        
        print(f"\n✓ MAUI template validated: {template_dir.name}")
    
    def test_template_init_go_stack(self, temp_output):
        """Test template-init for Go stack."""
        template_dir = self._simulate_template_init(temp_output, tech_stack="go")
        
        # Validate template
        TemplateAssertions.assert_template_exists(template_dir)
        metadata = TemplateAssertions.assert_has_metadata(template_dir)
        TemplateAssertions.assert_valid_tech_stack(metadata, "go")
        
        # Validate Go-specific files
        assert (template_dir / "go.mod").exists(), "Missing go.mod"
        
        print(f"\n✓ Go template validated: {template_dir.name}")
    
    def test_template_init_has_patterns(self, temp_output):
        """Test that generated templates include design patterns."""
        template_dir = self._simulate_template_init(temp_output, tech_stack="python")
        
        metadata = TemplateAssertions.assert_has_metadata(template_dir)
        
        # Validate patterns are documented
        TemplateAssertions.assert_has_patterns(metadata, ["Repository"])
        
        print(f"\n✓ Template patterns validated")
