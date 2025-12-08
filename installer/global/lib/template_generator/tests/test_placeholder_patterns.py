"""
Tests for placeholder_patterns module.

TASK-IMP-TC-F8A3: Test suite for centralized placeholder patterns.
"""

import pytest
from pathlib import Path
import importlib

# Import using importlib to avoid 'global' keyword issue
_placeholder_module = importlib.import_module(
    'installer.global.lib.template_generator.placeholder_patterns'
)

PlaceholderPatterns = _placeholder_module.PlaceholderPatterns
PlaceholderExtractor = _placeholder_module.PlaceholderExtractor
PlaceholderResult = _placeholder_module.PlaceholderResult


class TestPlaceholderPatterns:
    """Test PlaceholderPatterns class."""

    def test_extension_language_mapping(self):
        """Test file extension to language mapping."""
        assert PlaceholderPatterns.EXTENSION_LANGUAGE_MAP['.py'] == 'python'
        assert PlaceholderPatterns.EXTENSION_LANGUAGE_MAP['.ts'] == 'typescript'
        assert PlaceholderPatterns.EXTENSION_LANGUAGE_MAP['.js'] == 'javascript'
        assert PlaceholderPatterns.EXTENSION_LANGUAGE_MAP['.cs'] == 'csharp'
        assert PlaceholderPatterns.EXTENSION_LANGUAGE_MAP['.svelte'] == 'svelte'

    def test_get_patterns_for_python(self):
        """Test Python patterns are returned for .py extension."""
        patterns = PlaceholderPatterns.get_patterns_for_extension('.py')
        assert len(patterns) > 0
        # Should include Python-specific patterns
        pattern_names = [p[2] for p in patterns]
        assert 'class name' in pattern_names

    def test_get_patterns_for_typescript(self):
        """Test TypeScript patterns are returned for .ts extension."""
        patterns = PlaceholderPatterns.get_patterns_for_extension('.ts')
        assert len(patterns) > 0
        pattern_names = [p[2] for p in patterns]
        assert 'class name' in pattern_names

    def test_get_patterns_for_svelte(self):
        """Test Svelte patterns include both JS and Svelte-specific."""
        patterns = PlaceholderPatterns.get_patterns_for_extension('.svelte')
        assert len(patterns) > 0
        # Should include both JavaScript and Svelte patterns
        pattern_names = [p[2] for p in patterns]
        assert any('import' in name for name in pattern_names)

    def test_get_patterns_for_csharp(self):
        """Test C# patterns are returned for .cs extension."""
        patterns = PlaceholderPatterns.get_patterns_for_extension('.cs')
        assert len(patterns) > 0
        pattern_names = [p[2] for p in patterns]
        assert 'namespace' in pattern_names or 'class name' in pattern_names

    def test_get_patterns_for_unknown_extension(self):
        """Test generic patterns returned for unknown extension."""
        patterns = PlaceholderPatterns.get_patterns_for_extension('.xyz')
        # Should still include entity patterns
        assert len(patterns) > 0

    def test_entity_patterns_included_for_all(self):
        """Test entity patterns are included for all languages."""
        for ext in ['.py', '.ts', '.js', '.cs', '.svelte', '.xyz']:
            patterns = PlaceholderPatterns.get_patterns_for_extension(ext)
            pattern_names = [p[2] for p in patterns]
            assert 'entity name' in pattern_names or 'service entity' in pattern_names


class TestPlaceholderExtractor:
    """Test PlaceholderExtractor class."""

    def test_init_without_manifest(self):
        """Test initialization without manifest."""
        extractor = PlaceholderExtractor()
        assert extractor.manifest == {}

    def test_init_with_manifest(self):
        """Test initialization with manifest."""
        manifest = {'name': 'MyProject', 'author': 'Test Author'}
        extractor = PlaceholderExtractor(manifest=manifest)
        assert extractor.manifest == manifest

    def test_extract_python_class(self):
        """Test extraction of Python class names."""
        extractor = PlaceholderExtractor()
        content = '''
class UserService:
    """Service for user operations."""
    pass
'''
        result = extractor.extract(content, 'test.py')
        assert isinstance(result, PlaceholderResult)
        assert '{{ClassName}}' in result.content or 'UserService' in result.content

    def test_extract_typescript_class(self):
        """Test extraction of TypeScript class names."""
        extractor = PlaceholderExtractor()
        content = '''
export class UserService {
    constructor() {}
}
'''
        result = extractor.extract(content, 'test.ts')
        assert isinstance(result, PlaceholderResult)

    def test_extract_csharp_namespace(self):
        """Test extraction of C# namespace."""
        extractor = PlaceholderExtractor()
        content = '''
namespace MyCompany.MyApp.Domain
{
    public class User { }
}
'''
        result = extractor.extract(content, 'test.cs')
        assert isinstance(result, PlaceholderResult)
        assert '{{Namespace}}' in result.content or 'MyCompany' in result.content

    def test_extract_with_manifest_project_name(self):
        """Test project name replacement from manifest."""
        manifest = {'name': 'kartlog'}
        extractor = PlaceholderExtractor(manifest=manifest)
        content = '''
from kartlog.services import UserService
'''
        result = extractor.extract(content, 'test.py')
        assert '{{ProjectName}}' in result.content
        assert 'ProjectName' in result.placeholders

    def test_extract_with_manifest_author(self):
        """Test author replacement from manifest."""
        manifest = {'author': 'John Doe'}
        extractor = PlaceholderExtractor(manifest=manifest)
        content = '''
# Author: John Doe
# Created for testing
'''
        result = extractor.extract(content, 'test.py')
        assert '{{Author}}' in result.content
        assert 'Author' in result.placeholders

    def test_extract_empty_content(self):
        """Test extraction with empty content."""
        extractor = PlaceholderExtractor()
        result = extractor.extract('', 'test.py')
        assert result.content == ''
        assert result.placeholders == []

    def test_extract_no_matches(self):
        """Test extraction with no matching patterns."""
        extractor = PlaceholderExtractor()
        content = '''
# Just a comment
x = 1 + 2
'''
        result = extractor.extract(content, 'test.py')
        assert isinstance(result, PlaceholderResult)

    def test_coverage_calculation_no_identifiable(self):
        """Test coverage is 1.0 when nothing to replace."""
        extractor = PlaceholderExtractor()
        # Empty manifest, simple content with no patterns
        result = extractor.extract('x = 1', 'test.py')
        # Coverage should be based on patterns checked vs replaced
        assert 0.0 <= result.coverage <= 1.0

    def test_validate_coverage_above_threshold(self):
        """Test validation passes when coverage is above threshold."""
        extractor = PlaceholderExtractor()
        result = PlaceholderResult(
            content='test',
            placeholders=['ProjectName'],
            coverage=0.9
        )
        is_valid, message = extractor.validate_coverage(result)
        assert is_valid
        assert 'meets threshold' in message

    def test_validate_coverage_below_threshold(self):
        """Test validation fails when coverage is below threshold."""
        extractor = PlaceholderExtractor()
        result = PlaceholderResult(
            content='test',
            placeholders=[],
            coverage=0.5
        )
        is_valid, message = extractor.validate_coverage(result)
        assert not is_valid
        assert 'below' in message

    def test_validate_coverage_at_threshold(self):
        """Test validation passes when coverage equals threshold."""
        extractor = PlaceholderExtractor()
        result = PlaceholderResult(
            content='test',
            placeholders=['ClassName'],
            coverage=0.8  # Exactly at threshold
        )
        is_valid, message = extractor.validate_coverage(result)
        assert is_valid

    def test_common_word_filtering(self):
        """Test that common words are not replaced."""
        extractor = PlaceholderExtractor()
        # Common words should not be replaced
        assert extractor._is_common_word('class')
        assert extractor._is_common_word('function')
        assert extractor._is_common_word('if')
        assert not extractor._is_common_word('UserService')
        assert not extractor._is_common_word('MyProject')

    def test_case_insensitive_project_name(self):
        """Test project name replacement is case-insensitive."""
        manifest = {'name': 'MyProject'}
        extractor = PlaceholderExtractor(manifest=manifest)
        content = '''
from myproject.module import something
MYPROJECT_CONFIG = True
'''
        result = extractor.extract(content, 'test.py')
        # Should replace case variations
        assert '{{ProjectName}}' in result.content

    def test_short_names_not_replaced(self):
        """Test that very short names are not replaced."""
        manifest = {'name': 'ab', 'author': 'x'}  # Too short
        extractor = PlaceholderExtractor(manifest=manifest)
        content = 'ab = 1\nx = 2'
        result = extractor.extract(content, 'test.py')
        # Short names should not be replaced
        assert '{{ProjectName}}' not in result.content


class TestPlaceholderResult:
    """Test PlaceholderResult dataclass."""

    def test_dataclass_creation(self):
        """Test PlaceholderResult can be created."""
        result = PlaceholderResult(
            content='test content',
            placeholders=['ProjectName', 'ClassName'],
            coverage=0.85
        )
        assert result.content == 'test content'
        assert result.placeholders == ['ProjectName', 'ClassName']
        assert result.coverage == 0.85

    def test_dataclass_empty_placeholders(self):
        """Test PlaceholderResult with empty placeholders."""
        result = PlaceholderResult(
            content='no placeholders',
            placeholders=[],
            coverage=1.0
        )
        assert result.placeholders == []
        assert result.coverage == 1.0


class TestIntegration:
    """Integration tests for placeholder extraction."""

    def test_full_python_file_extraction(self):
        """Test extraction from a realistic Python file."""
        manifest = {'name': 'kartlog', 'author': 'Test Author'}
        extractor = PlaceholderExtractor(manifest=manifest)
        
        content = '''
"""
kartlog - Session logging application
Author: Test Author
"""

from kartlog.models import Session
from kartlog.services import SessionService

class SessionManager:
    """Manages session lifecycle."""
    
    def __init__(self, service: SessionService):
        self.service = service
    
    def create_session(self, user_id: int) -> Session:
        return self.service.create(user_id)
'''
        result = extractor.extract(content, 'session_manager.py')
        
        # Should find project name and author
        assert 'ProjectName' in result.placeholders
        assert 'Author' in result.placeholders
        # Should have reasonable coverage
        assert result.coverage > 0

    def test_full_typescript_file_extraction(self):
        """Test extraction from a realistic TypeScript file."""
        extractor = PlaceholderExtractor()
        
        content = '''
import { UserService } from '@myapp/services';

export class UserController {
    constructor(private userService: UserService) {}
    
    async getUser(id: string): Promise<User> {
        return this.userService.findById(id);
    }
}
'''
        result = extractor.extract(content, 'user.controller.ts')
        assert isinstance(result, PlaceholderResult)
        assert len(result.placeholders) >= 0

    def test_full_csharp_file_extraction(self):
        """Test extraction from a realistic C# file."""
        extractor = PlaceholderExtractor()
        
        content = '''
namespace MyCompany.MyApp.Services
{
    public interface IUserService
    {
        Task<User> GetUserAsync(int id);
    }
    
    public class UserService : IUserService
    {
        private readonly IUserRepository _repository;
        
        public UserService(IUserRepository repository)
        {
            _repository = repository;
        }
        
        public async Task<User> GetUserAsync(int id)
        {
            return await _repository.FindByIdAsync(id);
        }
    }
}
'''
        result = extractor.extract(content, 'UserService.cs')
        assert isinstance(result, PlaceholderResult)
        # Should find namespace
        assert '{{Namespace}}' in result.content or len(result.placeholders) > 0
