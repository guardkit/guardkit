using ErrorOr;
using {ServiceName}.API.Application.DTOs.Requests;
using {ServiceName}.API.Application.DTOs.Responses;
using {ServiceName}.API.Application.Services.Interfaces;
using {ServiceName}.API.Domain.Entities;
using {ServiceName}.API.Infrastructure.Repositories.Interfaces;

namespace {ServiceName}.API.Application.Services.Implementations;

public class {Feature}Service : I{Feature}Service
{
    private readonly I{Feature}Repository _repository;
    private readonly ILogger<{Feature}Service> _logger;

    public {Feature}Service(
        I{Feature}Repository repository,
        ILogger<{Feature}Service> logger)
    {
        _repository = repository;
        _logger = logger;
    }

    public async Task<ErrorOr<List<{Feature}Response>>> GetAll{Feature}sAsync(
        CancellationToken cancellationToken)
    {
        try
        {
            var entities = await _repository.GetAllAsync(cancellationToken);
            var responses = entities.Select(e => new {Feature}Response
            {
                Id = e.Id,
                Name = e.Name,
                CreatedAt = e.CreatedAt,
                UpdatedAt = e.UpdatedAt
            }).ToList();

            return responses;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving {feature}s");
            return Error.Failure(
                code: "{Feature}.RetrievalError",
                description: "Failed to retrieve {feature}s");
        }
    }

    public async Task<ErrorOr<{Feature}Response>> Get{Feature}ByIdAsync(
        Guid id,
        CancellationToken cancellationToken)
    {
        var entity = await _repository.GetByIdAsync(id, cancellationToken);

        if (entity is null)
        {
            _logger.LogWarning("{Feature} with ID {Id} not found", id);
            return Error.NotFound(
                code: "{Feature}.NotFound",
                description: $"{Feature} with ID {id} not found");
        }

        return new {Feature}Response
        {
            Id = entity.Id,
            Name = entity.Name,
            CreatedAt = entity.CreatedAt,
            UpdatedAt = entity.UpdatedAt
        };
    }

    public async Task<ErrorOr<{Feature}Response>> Create{Feature}Async(
        Create{Feature}Request request,
        CancellationToken cancellationToken)
    {
        // Check for duplicates
        var existing = await _repository.FindByNameAsync(request.Name, cancellationToken);
        if (existing is not null)
        {
            return Error.Conflict(
                code: "{Feature}.Duplicate",
                description: $"{Feature} with name '{request.Name}' already exists");
        }

        var entity = new {Feature}
        {
            Id = Guid.NewGuid(),
            Name = request.Name,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        await _repository.AddAsync(entity, cancellationToken);

        _logger.LogInformation("{Feature} {Id} created successfully", entity.Id);

        return new {Feature}Response
        {
            Id = entity.Id,
            Name = entity.Name,
            CreatedAt = entity.CreatedAt,
            UpdatedAt = entity.UpdatedAt
        };
    }

    public async Task<ErrorOr<{Feature}Response>> Update{Feature}Async(
        Guid id,
        Update{Feature}Request request,
        CancellationToken cancellationToken)
    {
        var entity = await _repository.GetByIdAsync(id, cancellationToken);

        if (entity is null)
        {
            return Error.NotFound(
                code: "{Feature}.NotFound",
                description: $"{Feature} with ID {id} not found");
        }

        entity.Name = request.Name;
        entity.UpdatedAt = DateTime.UtcNow;

        await _repository.UpdateAsync(entity, cancellationToken);

        _logger.LogInformation("{Feature} {Id} updated successfully", id);

        return new {Feature}Response
        {
            Id = entity.Id,
            Name = entity.Name,
            CreatedAt = entity.CreatedAt,
            UpdatedAt = entity.UpdatedAt
        };
    }

    public async Task<ErrorOr<Deleted>> Delete{Feature}Async(
        Guid id,
        CancellationToken cancellationToken)
    {
        var entity = await _repository.GetByIdAsync(id, cancellationToken);

        if (entity is null)
        {
            return Error.NotFound(
                code: "{Feature}.NotFound",
                description: $"{Feature} with ID {id} not found");
        }

        await _repository.DeleteAsync(id, cancellationToken);

        _logger.LogInformation("{Feature} {Id} deleted successfully", id);

        return Result.Deleted;
    }
}

// Service interface
namespace {ServiceName}.API.Application.Services.Interfaces;

public interface I{Feature}Service
{
    Task<ErrorOr<List<{Feature}Response>>> GetAll{Feature}sAsync(CancellationToken cancellationToken);
    Task<ErrorOr<{Feature}Response>> Get{Feature}ByIdAsync(Guid id, CancellationToken cancellationToken);
    Task<ErrorOr<{Feature}Response>> Create{Feature}Async(Create{Feature}Request request, CancellationToken cancellationToken);
    Task<ErrorOr<{Feature}Response>> Update{Feature}Async(Guid id, Update{Feature}Request request, CancellationToken cancellationToken);
    Task<ErrorOr<Deleted>> Delete{Feature}Async(Guid id, CancellationToken cancellationToken);
}
