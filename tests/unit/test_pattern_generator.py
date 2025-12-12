"""
Tests for Pattern Example Extractor (TASK-PDI-003)

Tests the extraction of codebase-specific code examples for pattern files.
"""

import pytest
from pathlib import Path
from installer.core.lib.pattern_generator import (
    PatternExampleExtractor,
    CodeExample,
    extract_pattern_examples
)
from installer.core.lib.codebase_analyzer.stratified_sampler import PatternCategory


class TestPatternExampleExtractor:
    """Test PatternExampleExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return PatternExampleExtractor()

    @pytest.fixture
    def sample_repository_file(self):
        """Sample repository file content."""
        return {
            'path': 'src/Repositories/DriverRepository.cs',
            'content': '''using ErrorOr;
using DeCUK.Mobile.MyDrive.Domain;

namespace DeCUK.Mobile.MyDrive.Infrastructure.Repositories
{
    public class DriverRepository : IDriverRepository
    {
        private readonly IRealmAccessor _realmAccessor;

        public DriverRepository(IRealmAccessor realmAccessor)
        {
            _realmAccessor = realmAccessor;
        }

        public async Task<ErrorOr<DriverDetails>> GetDriverDetails()
        {
            var result = await _realmAccessor.ExecuteReadAsync<DriverDetails>(
                realm => realm.All<RealmDriver>().FirstOrDefault()
                    ?? AppErrors.Driver.GetFailed,
                AppErrors.Driver.DatabaseError);

            return result.IsError ? result.Errors : result.Value;
        }

        public async Task<ErrorOr<Updated>> UpdateDriver(DriverDetails driver)
        {
            return await _realmAccessor.ExecuteWriteAsync(
                realm =>
                {
                    var realmDriver = realm.All<RealmDriver>().FirstOrDefault();
                    if (realmDriver == null)
                        return AppErrors.Driver.NotFound;

                    realmDriver.Name = driver.Name;
                    return Result.Updated;
                },
                AppErrors.Driver.UpdateFailed);
        }
    }
}'''
        }

    @pytest.fixture
    def sample_validator_file(self):
        """Sample validator file content."""
        return {
            'path': 'src/Validators/DriverValidator.cs',
            'content': '''using FluentValidation;

namespace DeCUK.Mobile.MyDrive.Validators
{
    public class DriverValidator : AbstractValidator<Driver>
    {
        public DriverValidator()
        {
            RuleFor(x => x.Name)
                .NotEmpty()
                .WithMessage("Driver name is required");

            RuleFor(x => x.LicenseNumber)
                .NotEmpty()
                .WithMessage("License number is required")
                .Matches(@"^[A-Z0-9]+$")
                .WithMessage("License number must be alphanumeric");
        }
    }
}'''
        }

    def test_categorize_samples(self, extractor, sample_repository_file):
        """Test categorization of file samples."""
        samples = [sample_repository_file]
        categorized = extractor._categorize_samples(samples)

        assert PatternCategory.REPOSITORIES in categorized
        assert len(categorized[PatternCategory.REPOSITORIES]) == 1

    def test_detect_language_csharp(self, extractor):
        """Test language detection for C#."""
        lang = extractor._detect_language('DriverRepository.cs')
        assert lang == 'csharp'

    def test_detect_language_python(self, extractor):
        """Test language detection for Python."""
        lang = extractor._detect_language('repository.py')
        assert lang == 'python'

    def test_detect_language_typescript(self, extractor):
        """Test language detection for TypeScript."""
        lang = extractor._detect_language('repository.ts')
        assert lang == 'typescript'

    def test_extract_repository_method(self, extractor, sample_repository_file):
        """Test extraction of repository method."""
        lines = sample_repository_file['content'].split('\n')
        snippet = extractor._extract_repository_method(lines)

        assert 'GetDriverDetails' in snippet or 'UpdateDriver' in snippet
        assert 'async' in snippet.lower()
        assert 'Task' in snippet

    def test_extract_validator_method(self, extractor, sample_validator_file):
        """Test extraction of validator method."""
        lines = sample_validator_file['content'].split('\n')
        snippet = extractor._extract_validator_method(lines)

        assert 'RuleFor' in snippet or 'Validate' in snippet

    def test_extract_single_example_repository(self, extractor, sample_repository_file):
        """Test extraction of single repository example."""
        example = extractor._extract_single_example(
            sample_repository_file,
            "Repository Pattern",
            PatternCategory.REPOSITORIES
        )

        assert example is not None
        assert example.pattern == "Repository Pattern"
        assert example.language == 'csharp'
        assert len(example.snippet) > 0
        assert 'DriverRepository' in example.file_path
        assert len(example.best_practices) >= 3

    def test_extract_best_practices_async(self, extractor):
        """Test best practices extraction for async code."""
        content = '''
        public async Task<ErrorOr<User>> GetUser(int id)
        {
            return await _repository.FindAsync(id);
        }
        '''
        practices = extractor._extract_best_practices(content, PatternCategory.REPOSITORIES)

        assert any('async' in p.lower() for p in practices)

    def test_extract_best_practices_erroror(self, extractor):
        """Test best practices extraction for ErrorOr pattern."""
        content = '''
        public ErrorOr<User> GetUser(int id)
        {
            var user = _repository.Find(id);
            return user ?? AppErrors.User.NotFound;
        }
        '''
        practices = extractor._extract_best_practices(content, PatternCategory.REPOSITORIES)

        assert any('erroror' in p.lower() or 'result' in p.lower() for p in practices)

    def test_extract_examples_multiple_patterns(
        self,
        extractor,
        sample_repository_file,
        sample_validator_file
    ):
        """Test extraction with multiple pattern types."""
        samples = [sample_repository_file, sample_validator_file]
        examples = extractor.extract_examples(samples, max_examples_per_pattern=2)

        # Should have examples for both patterns
        assert "Repository Pattern" in examples
        assert "Validator Pattern" in examples

    def test_extract_examples_limits_per_pattern(self, extractor):
        """Test that max_examples_per_pattern is respected."""
        # Create 5 repository files
        samples = [
            {
                'path': f'src/Repositories/Repo{i}.cs',
                'content': f'''
                public class Repo{i} : IRepository
                {{
                    public async Task<User> GetUser() {{ return null; }}
                }}
                '''
            }
            for i in range(5)
        ]

        examples = extractor.extract_examples(samples, max_examples_per_pattern=2)

        # Should have Repository Pattern with max 2 examples
        if "Repository Pattern" in examples:
            assert len(examples["Repository Pattern"]) <= 2

    def test_extract_pattern_examples_convenience_function(self, sample_repository_file):
        """Test convenience function for extraction."""
        samples = [sample_repository_file]
        examples = extract_pattern_examples(samples, max_examples_per_pattern=1)

        assert isinstance(examples, dict)
        assert len(examples) >= 0

    def test_extract_snippet_truncation(self, extractor):
        """Test that snippets are truncated to max_lines."""
        # Create a very long file
        long_content = '\n'.join([f'    line {i};' for i in range(100)])
        snippet = extractor._extract_snippet(
            long_content,
            PatternCategory.REPOSITORIES,
            max_lines=25
        )

        lines = snippet.split('\n')
        assert len(lines) <= 26  # max_lines + 1 for truncation indicator

    def test_generate_context(self, extractor):
        """Test context generation for examples."""
        context = extractor._generate_context(
            'src/Repositories/DriverRepository.cs',
            PatternCategory.REPOSITORIES
        )

        assert 'DriverRepository.cs' in context
        assert 'Repository Pattern' in context

    def test_extract_examples_empty_samples(self, extractor):
        """Test extraction with no samples."""
        examples = extractor.extract_examples([], max_examples_per_pattern=2)

        assert examples == {}

    def test_extract_examples_no_recognized_patterns(self, extractor):
        """Test extraction when no patterns are recognized."""
        samples = [
            {
                'path': 'README.md',
                'content': '# Project Documentation'
            }
        ]
        examples = extractor.extract_examples(samples, max_examples_per_pattern=2)

        # Should not extract examples from non-code files
        assert len(examples) == 0 or all(len(ex) == 0 for ex in examples.values())

    def test_crud_create_extraction(self, extractor):
        """Test extraction of CRUD Create pattern."""
        sample = {
            'path': 'src/UseCases/CreateUser/CreateUserHandler.cs',
            'content': '''
            public class CreateUserHandler
            {
                public async Task<ErrorOr<User>> Handle(CreateUserCommand command)
                {
                    var user = new User(command.Name, command.Email);
                    await _repository.AddAsync(user);
                    return user;
                }
            }
            '''
        }

        example = extractor._extract_single_example(
            sample,
            "CRUD Create Pattern",
            PatternCategory.CRUD_CREATE
        )

        assert example is not None
        assert 'Create' in example.file_path or 'create' in example.snippet.lower()

    def test_crud_read_extraction(self, extractor):
        """Test extraction of CRUD Read pattern."""
        sample = {
            'path': 'src/UseCases/GetUser/GetUserHandler.cs',
            'content': '''
            public class GetUserHandler
            {
                public async Task<ErrorOr<User>> Handle(GetUserQuery query)
                {
                    var user = await _repository.GetByIdAsync(query.UserId);
                    return user ?? AppErrors.User.NotFound;
                }
            }
            '''
        }

        example = extractor._extract_single_example(
            sample,
            "CRUD Read Pattern",
            PatternCategory.CRUD_READ
        )

        assert example is not None
        assert 'Get' in example.file_path or 'get' in example.snippet.lower()
