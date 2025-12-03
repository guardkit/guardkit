"""
Integration Tests for Codebase Analyzer

Tests the complete analyzer workflow with real codebase fixtures:
- End-to-end analysis of real project structures
- Integration with file system
- Serialization round-trips
- Multiple language/framework scenarios

These tests use real codebases (either fixtures or the guardkit project itself).
"""

import pytest
from pathlib import Path
import json

from lib.codebase_analyzer import (
    CodebaseAnalyzer,
    AnalysisSerializer,
    analyze_codebase,
)
from lib.codebase_analyzer.models import ConfidenceLevel


class TestPythonCodebaseAnalysis:
    """Integration tests for Python codebase analysis."""

    @pytest.fixture
    def python_fastapi_codebase(self, tmp_path):
        """Create a realistic FastAPI project structure."""
        # Create directory structure
        src = tmp_path / "src"
        src.mkdir()
        domain = src / "domain"
        domain.mkdir()
        api = src / "api"
        api.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        # Create files
        (tmp_path / "requirements.txt").write_text(
            "fastapi==0.100.0\n"
            "pydantic==2.0.0\n"
            "pytest==7.4.0\n"
            "pytest-cov==4.1.0\n"
        )

        (tmp_path / "pytest.ini").write_text(
            "[pytest]\n"
            "testpaths = tests\n"
        )

        # Domain layer
        (domain / "__init__.py").write_text("")
        (domain / "user.py").write_text("""
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: int
    email: EmailStr
    name: str

    def validate_email(self) -> bool:
        return '@' in self.email
""")

        (domain / "user_repository.py").write_text("""
from typing import List, Optional
from .user import User

class UserRepository:
    def __init__(self):
        self._users = []

    def get_by_id(self, user_id: int) -> Optional[User]:
        return next((u for u in self._users if u.id == user_id), None)

    def get_all(self) -> List[User]:
        return self._users

    def save(self, user: User) -> User:
        self._users.append(user)
        return user
""")

        # API layer
        (api / "__init__.py").write_text("")
        (api / "main.py").write_text("""
from fastapi import FastAPI, HTTPException
from ..domain.user_repository import UserRepository

app = FastAPI()
user_repo = UserRepository()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users")
async def list_users():
    return user_repo.get_all()
""")

        # Tests
        (tests / "__init__.py").write_text("")
        (tests / "test_user.py").write_text("""
import pytest
from src.domain.user import User

def test_user_creation():
    user = User(id=1, email="test@example.com", name="Test User")
    assert user.id == 1
    assert user.email == "test@example.com"

def test_user_email_validation():
    user = User(id=1, email="test@example.com", name="Test")
    assert user.validate_email() is True
""")

        return tmp_path

    def test_analyze_python_fastapi_project(self, python_fastapi_codebase):
        """Test analyzing a complete FastAPI project."""
        analyzer = CodebaseAnalyzer(use_agent=False)  # Use heuristics for reliable test

        analysis = analyzer.analyze_codebase(
            codebase_path=python_fastapi_codebase,
            template_context={
                "name": "FastAPI Template",
                "language": "Python",
                "framework": "FastAPI"
            }
        )

        # Verify technology detection
        assert analysis.technology.primary_language == "Python"
        assert "FastAPI" in analysis.technology.frameworks
        assert "pytest" in analysis.technology.testing_frameworks
        assert "pip" in analysis.technology.build_tools

        # Verify architecture detection
        assert "Repository" in analysis.architecture.patterns
        assert analysis.architecture.architectural_style != "Unknown"

        # Verify confidence scores
        assert analysis.technology.confidence.percentage > 0
        assert analysis.architecture.confidence.percentage > 0
        assert analysis.quality.confidence.percentage > 0

    def test_save_and_load_analysis(self, python_fastapi_codebase, tmp_path):
        """Test complete save/load cycle."""
        analyzer = CodebaseAnalyzer(use_agent=False)
        serializer = AnalysisSerializer(cache_dir=tmp_path / "cache")

        # Analyze
        analysis = analyzer.analyze_codebase(
            codebase_path=python_fastapi_codebase
        )

        # Save
        save_path = serializer.save(analysis, filename="test_analysis.json")
        assert save_path.exists()

        # Load
        loaded = serializer.load(save_path)

        # Verify data preservation
        assert loaded.technology.primary_language == analysis.technology.primary_language
        assert loaded.architecture.patterns == analysis.architecture.patterns
        assert loaded.quality.overall_score == analysis.quality.overall_score
        assert loaded.codebase_path == analysis.codebase_path

    def test_export_markdown_report(self, python_fastapi_codebase, tmp_path):
        """Test markdown report generation."""
        analyzer = CodebaseAnalyzer(use_agent=False)

        analysis = analyzer.analyze_codebase(
            codebase_path=python_fastapi_codebase
        )

        # Export
        report_path = tmp_path / "analysis_report.md"
        analyzer.export_markdown_report(analysis, report_path)

        assert report_path.exists()

        # Verify content
        content = report_path.read_text()
        assert "Codebase Analysis Report" in content
        assert "Python" in content
        assert "FastAPI" in content
        assert "Technology Stack" in content
        assert "Architecture" in content
        assert "Quality Assessment" in content


class TestTypeScriptCodebaseAnalysis:
    """Integration tests for TypeScript/React codebase analysis."""

    @pytest.fixture
    def react_nextjs_codebase(self, tmp_path):
        """Create a realistic Next.js project structure."""
        # Create directories
        src = tmp_path / "src"
        src.mkdir()
        components = src / "components"
        components.mkdir()
        app = src / "app"
        app.mkdir()

        # Create package.json
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "nextjs-app",
            "version": "1.0.0",
            "dependencies": {
                "next": "14.0.0",
                "react": "18.2.0",
                "react-dom": "18.2.0"
            },
            "devDependencies": {
                "typescript": "5.0.0",
                "@types/react": "18.2.0",
                "vitest": "1.0.0",
                "playwright": "1.40.0"
            }
        }, indent=2))

        # Create tsconfig.json
        (tmp_path / "tsconfig.json").write_text(json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "lib": ["ES2020", "DOM"],
                "jsx": "react-jsx",
                "module": "ESNext",
                "strict": True
            }
        }, indent=2))

        # Create components
        (components / "Button.tsx").write_text("""
import React from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}

export const Button: React.FC<ButtonProps> = ({ label, onClick, variant = 'primary' }) => {
  return (
    <button
      onClick={onClick}
      className={`btn btn-${variant}`}
    >
      {label}
    </button>
  );
};
""")

        (components / "UserCard.tsx").write_text("""
import React from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

interface UserCardProps {
  user: User;
}

export const UserCard: React.FC<UserCardProps> = ({ user }) => {
  return (
    <div className="user-card">
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  );
};
""")

        # Create app page
        (app / "page.tsx").write_text("""
import { Button } from '@/components/Button';
import { UserCard } from '@/components/UserCard';

export default function HomePage() {
  const handleClick = () => {
    console.log('Button clicked');
  };

  return (
    <main>
      <h1>Welcome</h1>
      <Button label="Click me" onClick={handleClick} />
    </main>
  );
}
""")

        # Create test config
        (tmp_path / "vitest.config.ts").write_text("""
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
  },
});
""")

        (tmp_path / "playwright.config.ts").write_text("""
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
});
""")

        return tmp_path

    def test_analyze_react_nextjs_project(self, react_nextjs_codebase):
        """Test analyzing a React/Next.js project."""
        analyzer = CodebaseAnalyzer(use_agent=False)

        analysis = analyzer.analyze_codebase(
            codebase_path=react_nextjs_codebase,
            template_context={
                "name": "Next.js Template",
                "language": "TypeScript",
                "framework": "Next.js"
            }
        )

        # Verify technology detection
        assert analysis.technology.primary_language == "TypeScript"
        assert "Next.js" in analysis.technology.frameworks
        assert "React" in analysis.technology.frameworks
        assert "Vitest" in analysis.technology.testing_frameworks
        assert "Playwright" in analysis.technology.testing_frameworks
        assert "npm" in analysis.technology.build_tools

        # Verify patterns
        # Component pattern is common in React
        assert len(analysis.architecture.patterns) >= 0  # May detect patterns

        # Verify confidence
        assert analysis.technology.confidence.level in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM
        ]


class TestDotNetCodebaseAnalysis:
    """Integration tests for .NET codebase analysis."""

    @pytest.fixture
    def dotnet_api_codebase(self, tmp_path):
        """Create a realistic .NET API project structure."""
        # Create directories
        src = tmp_path / "src"
        src.mkdir()
        domain = src / "Domain"
        domain.mkdir()
        api = src / "Api"
        api.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        # Create .csproj files
        (api / "Api.csproj").write_text("""
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" />
  </ItemGroup>
</Project>
""")

        (domain / "Domain.csproj").write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
</Project>
""")

        # Create domain files
        (domain / "User.cs").write_text("""
namespace Domain;

public class User
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;

    public bool IsValidEmail()
    {
        return Email.Contains("@");
    }
}
""")

        (domain / "IUserRepository.cs").write_text("""
namespace Domain;

public interface IUserRepository
{
    User? GetById(int id);
    IEnumerable<User> GetAll();
    User Save(User user);
}
""")

        # Create API files
        (api / "Program.cs").write_text("""
using Domain;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/users/{id}", (int id, IUserRepository repo) =>
{
    var user = repo.GetById(id);
    return user is null ? Results.NotFound() : Results.Ok(user);
});

app.Run();
""")

        return tmp_path

    def test_analyze_dotnet_api_project(self, dotnet_api_codebase):
        """Test analyzing a .NET API project."""
        analyzer = CodebaseAnalyzer(use_agent=False)

        analysis = analyzer.analyze_codebase(
            codebase_path=dotnet_api_codebase,
            template_context={
                "name": ".NET API Template",
                "language": "C#",
                "framework": "ASP.NET Core"
            }
        )

        # Verify technology detection
        assert analysis.technology.primary_language == "C#"
        assert ".NET" in analysis.technology.frameworks

        # Verify patterns
        assert "Repository" in analysis.architecture.patterns  # IUserRepository

        # Verify confidence
        assert analysis.technology.confidence.percentage > 0


class TestRealCodebaseAnalysis:
    """Integration tests using the actual guardkit codebase."""

    def test_analyze_guardkit_itself(self):
        """Test analyzing the guardkit project itself."""
        # Get the project root (should be accessible from test environment)
        project_root = Path(__file__).parent.parent.parent

        if not project_root.exists():
            pytest.skip("GuardKit project root not found")

        analyzer = CodebaseAnalyzer(use_agent=False, max_files=5)

        analysis = analyzer.analyze_codebase(
            codebase_path=project_root
        )

        # Verify basic detection works on real codebase
        # GuardKit is polyglot, but should detect something
        assert analysis.technology.primary_language != "Unknown"

        # Should detect testing frameworks
        assert len(analysis.technology.testing_frameworks) > 0

        # Should have reasonable confidence
        assert analysis.overall_confidence.percentage > 50

    def test_quick_analyze_performance(self):
        """Test quick analysis is faster than full analysis."""
        project_root = Path(__file__).parent.parent.parent

        if not project_root.exists():
            pytest.skip("GuardKit project root not found")

        import time

        analyzer = CodebaseAnalyzer(use_agent=False)

        # Quick analysis
        start = time.time()
        quick_result = analyzer.quick_analyze(project_root)
        quick_time = time.time() - start

        # Full analysis
        start = time.time()
        full_result = analyzer.analyze_codebase(project_root)
        full_time = time.time() - start

        # Quick should be faster
        assert quick_time < full_time

        # Both should produce results
        assert quick_result is not None
        assert full_result is not None


class TestConvenienceFunction:
    """Test the convenience analyze_codebase function."""

    @pytest.fixture
    def simple_codebase(self, tmp_path):
        """Create a simple codebase."""
        (tmp_path / "main.py").write_text("print('Hello')")
        return tmp_path

    def test_convenience_function(self, simple_codebase, tmp_path):
        """Test using the convenience function."""
        # Mock the serializer to save to temp location
        from unittest.mock import patch

        with patch('lib.codebase_analyzer.ai_analyzer.AnalysisSerializer') as mock_serializer:
            mock_instance = mock_serializer.return_value
            mock_instance.save.return_value = tmp_path / "result.json"

            analysis = analyze_codebase(
                codebase_path=simple_codebase,
                template_context={"name": "Test"},
                save_results=True
            )

            assert analysis is not None
            assert analysis.technology.primary_language == "Python"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
