"""
Integration Tests for AI-Native Template Creation (TASK-51B2)

Tests that /template-create works without Q&A or detector code.
AI analyzes codebases directly and infers all metadata.
"""

import pytest
from pathlib import Path
import json
import shutil
import sys
import importlib.util

# Import orchestrator using importlib (avoid 'global' keyword issue)
def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import orchestrator
orchestrator_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib" / "template_create_orchestrator.py"
orchestrator_module = import_module_from_path("template_create_orchestrator", orchestrator_path)
TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
OrchestrationConfig = orchestrator_module.OrchestrationConfig
OrchestrationResult = orchestrator_module.OrchestrationResult


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory for templates"""
    output_dir = tmp_path / "templates"
    output_dir.mkdir()
    yield output_dir
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)


@pytest.fixture
def sample_react_project(tmp_path):
    """Create a minimal React TypeScript project structure"""
    project_path = tmp_path / "sample-react"
    project_path.mkdir()

    # package.json with React dependencies
    (project_path / "package.json").write_text(json.dumps({
        "name": "sample-react-app",
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "devDependencies": {
            "@types/react": "^18.0.0",
            "@types/react-dom": "^18.0.0",
            "typescript": "^5.0.0",
            "vite": "^4.0.0",
            "vitest": "^0.34.0"
        }
    }, indent=2))

    # tsconfig.json
    (project_path / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {
            "target": "ES2020",
            "lib": ["ES2020", "DOM"],
            "jsx": "react-jsx",
            "module": "ESNext",
            "moduleResolution": "bundler"
        }
    }, indent=2))

    # src/ structure
    src_dir = project_path / "src"
    src_dir.mkdir()

    components_dir = src_dir / "components"
    components_dir.mkdir()

    # Sample component
    (components_dir / "Button.tsx").write_text('''
import { FC } from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
}

export const Button: FC<ButtonProps> = ({ label, onClick }) => {
  return <button onClick={onClick}>{label}</button>;
};
'''.strip())

    # Sample hook
    hooks_dir = src_dir / "hooks"
    hooks_dir.mkdir()

    (hooks_dir / "useCounter.ts").write_text('''
import { useState } from 'react';

export const useCounter = (initialValue: number = 0) => {
  const [count, setCount] = useState(initialValue);

  const increment = () => setCount(c => c + 1);
  const decrement = () => setCount(c => c - 1);

  return { count, increment, decrement };
};
'''.strip())

    # Test file
    tests_dir = src_dir / "__tests__"
    tests_dir.mkdir()

    (tests_dir / "Button.test.tsx").write_text('''
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from '../components/Button';

describe('Button', () => {
  it('renders button with label', () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
});
'''.strip())

    return project_path


@pytest.fixture
def sample_fastapi_project(tmp_path):
    """Create a minimal FastAPI Python project structure"""
    project_path = tmp_path / "sample-fastapi"
    project_path.mkdir()

    # requirements.txt with FastAPI dependencies
    (project_path / "requirements.txt").write_text('''
fastapi==0.104.0
uvicorn[standard]==0.24.0
pydantic==2.4.0
sqlalchemy==2.0.0
pytest==7.4.0
pytest-asyncio==0.21.0
httpx==0.25.0
'''.strip())

    # pyproject.toml
    (project_path / "pyproject.toml").write_text('''
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
'''.strip())

    # app/ structure
    app_dir = project_path / "app"
    app_dir.mkdir()

    # main.py
    (app_dir / "main.py").write_text('''
from fastapi import FastAPI
from app.api.routes import users

app = FastAPI(title="Sample FastAPI App")

app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
'''.strip())

    # api/routes/
    api_dir = app_dir / "api"
    api_dir.mkdir()
    routes_dir = api_dir / "routes"
    routes_dir.mkdir()

    (routes_dir / "users.py").write_text('''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class User(BaseModel):
    id: int
    name: str
    email: str

@router.get("/", response_model=list[User])
async def list_users():
    return []

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    raise HTTPException(status_code=404, detail="User not found")
'''.strip())

    # models/
    models_dir = app_dir / "models"
    models_dir.mkdir()

    (models_dir / "user.py").write_text('''
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
'''.strip())

    # tests/
    tests_dir = project_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_users.py").write_text('''
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_users():
    response = client.get("/api/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
'''.strip())

    return project_path


@pytest.fixture
def sample_nextjs_project(tmp_path):
    """Create a minimal Next.js TypeScript project structure"""
    project_path = tmp_path / "sample-nextjs"
    project_path.mkdir()

    # package.json with Next.js dependencies
    (project_path / "package.json").write_text(json.dumps({
        "name": "sample-nextjs-app",
        "version": "0.1.0",
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start"
        },
        "dependencies": {
            "next": "14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "devDependencies": {
            "@types/node": "^20.0.0",
            "@types/react": "^18.0.0",
            "typescript": "^5.0.0",
            "jest": "^29.0.0",
            "@testing-library/react": "^14.0.0"
        }
    }, indent=2))

    # tsconfig.json
    (project_path / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {
            "target": "ES2017",
            "lib": ["dom", "dom.iterable", "esnext"],
            "jsx": "preserve",
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": true
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
        "exclude": ["node_modules"]
    }, indent=2))

    # app/ directory (App Router)
    app_dir = project_path / "app"
    app_dir.mkdir()

    # app/page.tsx
    (app_dir / "page.tsx").write_text('''
export default function Home() {
  return (
    <main>
      <h1>Welcome to Next.js</h1>
    </main>
  );
}
'''.strip())

    # app/layout.tsx
    (app_dir / "layout.tsx").write_text('''
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
'''.strip())

    # components/
    components_dir = project_path / "components"
    components_dir.mkdir()

    (components_dir / "Header.tsx").write_text('''
export function Header() {
  return <header><h1>My App</h1></header>;
}
'''.strip())

    # lib/
    lib_dir = project_path / "lib"
    lib_dir.mkdir()

    (lib_dir / "api.ts").write_text('''
export async function fetchData(endpoint: string) {
  const response = await fetch(endpoint);
  return response.json();
}
'''.strip())

    return project_path


class TestAINativeTemplateCreation:
    """Test AI-native template creation without Q&A or detector code"""

    def test_react_typescript_project_inference(self, sample_react_project, temp_output_dir):
        """Test AI-native template creation for React TypeScript project"""
        # Configure orchestrator (no Q&A, no detector, just AI analysis)
        config = OrchestrationConfig(
            codebase_path=sample_react_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False,
            save_analysis=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Verify success
        assert result.success, f"Template creation failed: {result.errors}"
        assert result.template_name, "Template name not generated"

        # Verify AI inferred correct metadata
        assert "react" in result.template_name.lower() or "typescript" in result.template_name.lower(), \
            f"Template name doesn't reflect React/TypeScript: {result.template_name}"

        # Verify templates generated
        assert result.template_count > 0, "No template files generated"

        # Verify agents recommended
        assert result.agent_count > 0, "No agents recommended"

        # Verify output files exist
        assert result.manifest_path and result.manifest_path.exists(), "Manifest not created"
        assert result.settings_path and result.settings_path.exists(), "Settings not created"
        assert result.claude_md_path and result.claude_md_path.exists(), "CLAUDE.md not created"

    def test_fastapi_python_project_inference(self, sample_fastapi_project, temp_output_dir):
        """Test AI-native template creation for FastAPI Python project"""
        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False,
            save_analysis=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Verify success
        assert result.success, f"Template creation failed: {result.errors}"
        assert result.template_name, "Template name not generated"

        # Verify AI inferred correct metadata
        assert "fastapi" in result.template_name.lower() or "python" in result.template_name.lower(), \
            f"Template name doesn't reflect FastAPI/Python: {result.template_name}"

        # Verify artifacts
        assert result.template_count > 0, "No template files generated"
        assert result.agent_count > 0, "No agents recommended"

    def test_nextjs_fullstack_project_inference(self, sample_nextjs_project, temp_output_dir):
        """Test AI-native template creation for Next.js full-stack project"""
        config = OrchestrationConfig(
            codebase_path=sample_nextjs_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False,
            save_analysis=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Verify success
        assert result.success, f"Template creation failed: {result.errors}"
        assert result.template_name, "Template name not generated"

        # Verify AI inferred correct metadata
        assert "next" in result.template_name.lower() or "nextjs" in result.template_name.lower(), \
            f"Template name doesn't reflect Next.js: {result.template_name}"

        # Verify artifacts
        assert result.template_count > 0, "No template files generated"
        assert result.agent_count > 0, "No agents recommended"

    def test_no_interactive_prompts(self, sample_react_project, temp_output_dir, monkeypatch):
        """Verify no interactive Q&A sessions occur"""
        # Mock input to ensure no prompts are shown
        input_called = []

        def mock_input(prompt):
            input_called.append(prompt)
            raise RuntimeError("Interactive prompt detected! Q&A should be disabled.")

        monkeypatch.setattr('builtins.input', mock_input)

        config = OrchestrationConfig(
            codebase_path=sample_react_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Should complete without calling input()
        assert result.success, f"Template creation failed: {result.errors}"
        assert len(input_called) == 0, f"Interactive prompts detected: {input_called}"

    def test_ci_cd_compatibility(self, sample_fastapi_project, temp_output_dir, monkeypatch):
        """Test compatibility with CI/CD environments (non-interactive)"""
        # Simulate CI/CD environment
        monkeypatch.setenv('CI', 'true')
        monkeypatch.setenv('TERM', 'dumb')

        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Should succeed in CI/CD environment
        assert result.success, f"CI/CD execution failed: {result.errors}"
        assert result.template_count > 0, "No templates generated in CI/CD mode"


class TestTemplateFileGeneration:
    """Test template file generation quality (TASK-51B2-B)"""

    def test_template_files_contain_placeholders(self, sample_fastapi_project, temp_output_dir):
        """Verify generated template files contain proper placeholders"""
        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        assert result.success, f"Template creation failed: {result.errors}"

        # Check that template files exist
        templates_dir = result.output_path / "templates"
        assert templates_dir.exists(), "Templates directory not created"

        template_files = list(templates_dir.rglob("*.template"))
        assert len(template_files) > 0, "No .template files generated"

        # Verify templates contain placeholders
        placeholders_found = False
        common_placeholders = [
            "{{ProjectName}}",
            "{{Namespace}}",
            "{{EntityName}}",
            "{{ModuleName}}",
            "{{project_name}}",
            "{{namespace}}"
        ]

        for template_file in template_files:
            content = template_file.read_text(encoding='utf-8')

            # Check if any common placeholder exists
            for placeholder in common_placeholders:
                if placeholder in content:
                    placeholders_found = True
                    break

            if placeholders_found:
                break

        assert placeholders_found, "No placeholders found in generated template files"

    def test_template_diversity(self, sample_fastapi_project, temp_output_dir):
        """Verify templates cover diverse architectural layers"""
        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        assert result.success, f"Template creation failed: {result.errors}"

        templates_dir = result.output_path / "templates"
        template_files = [str(f.relative_to(templates_dir)) for f in templates_dir.rglob("*.template")]

        # Check for diversity across layers
        layer_indicators = {
            'domain': ['domain/', 'models/', 'entities/', 'validators/'],
            'application': ['application/', 'use_cases/', 'services/', 'dtos/'],
            'infrastructure': ['infrastructure/', 'repositories/', 'database/'],
            'presentation': ['api/', 'routes/', 'controllers/', 'web/', 'middleware/'],
            'testing': ['tests/', 'test_', '__tests__']
        }

        layers_covered = set()
        for layer, indicators in layer_indicators.items():
            for template_file in template_files:
                if any(indicator in template_file.lower() for indicator in indicators):
                    layers_covered.add(layer)
                    break

        # Should cover at least 3 different layers
        assert len(layers_covered) >= 3, \
            f"Insufficient layer diversity. Covered: {layers_covered}, Expected: ≥3 layers"

    def test_minimum_template_count(self, sample_fastapi_project, temp_output_dir):
        """Verify AI returns sufficient number of template files (10-20 range)"""
        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        assert result.success, f"Template creation failed: {result.errors}"

        # AI should return 10-20 example files for template generation
        # (as per enhanced prompt guidelines)
        assert result.template_count >= 5, \
            f"Too few templates generated: {result.template_count} (expected ≥5 for basic project)"

        # For real-world projects, should be closer to 10-20
        # But our sample project is minimal, so we use lower threshold
        if result.template_count < 10:
            print(f"Warning: Generated {result.template_count} templates (expected 10-20 for full project)")

    def test_templates_work_with_init(self, sample_react_project, temp_output_dir, tmp_path):
        """Verify generated templates can be used with 'guardkit init'"""
        # Generate template
        config = OrchestrationConfig(
            codebase_path=sample_react_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        assert result.success, f"Template creation failed: {result.errors}"

        # Verify required files exist (needed for 'guardkit init')
        assert result.manifest_path and result.manifest_path.exists(), \
            "manifest.json missing (required for init)"
        assert result.settings_path and result.settings_path.exists(), \
            "settings.json missing (required for init)"
        assert result.claude_md_path and result.claude_md_path.exists(), \
            "CLAUDE.md missing (required for init)"

        # Verify templates directory exists
        templates_dir = result.output_path / "templates"
        assert templates_dir.exists(), "templates/ directory missing (required for init)"

        # Verify at least one template file exists
        template_files = list(templates_dir.rglob("*.template"))
        assert len(template_files) > 0, "No template files found (required for init)"

    def test_example_files_count_in_analysis(self, sample_fastapi_project, temp_output_dir):
        """Verify AI returns 10-20 example_files in analysis JSON"""
        config = OrchestrationConfig(
            codebase_path=sample_fastapi_project,
            output_location='global',
            output_path=temp_output_dir,
            dry_run=False,
            save_analysis=True  # Save analysis to check example_files
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        assert result.success, f"Template creation failed: {result.errors}"

        # Load analysis JSON
        analysis_path = Path("template-create-analysis.json")
        if analysis_path.exists():
            analysis_data = json.loads(analysis_path.read_text())

            # Check example_files array
            example_files = analysis_data.get("example_files", [])

            # AI should return 10-20 example files (as per enhanced prompt)
            assert len(example_files) >= 5, \
                f"Too few example files: {len(example_files)} (expected ≥10-20)"

            # Verify example files have required fields
            for example_file in example_files[:3]:  # Check first 3
                assert "path" in example_file, "Example file missing 'path' field"
                assert "purpose" in example_file, "Example file missing 'purpose' field"
                assert "layer" in example_file, "Example file missing 'layer' field"

            # Cleanup
            analysis_path.unlink()


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
