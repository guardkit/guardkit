using {ServiceName}.API.Domain.Entities;
using {ServiceName}.API.Infrastructure.Repositories.Interfaces;

namespace {ServiceName}.API.Infrastructure.Repositories.Implementations;

/// <summary>
/// In-memory repository implementation for demonstration
/// Replace with EF Core or other persistence mechanism
/// </summary>
public class {Feature}Repository : I{Feature}Repository
{
    private readonly List<{Feature}> _data = new();
    private readonly ILogger<{Feature}Repository> _logger;

    public {Feature}Repository(ILogger<{Feature}Repository> logger)
    {
        _logger = logger;
    }

    public Task<List<{Feature}>> GetAllAsync(CancellationToken cancellationToken)
    {
        return Task.FromResult(_data.ToList());
    }

    public Task<{Feature}?> GetByIdAsync(Guid id, CancellationToken cancellationToken)
    {
        var entity = _data.FirstOrDefault(x => x.Id == id);
        return Task.FromResult(entity);
    }

    public Task<{Feature}?> FindByNameAsync(string name, CancellationToken cancellationToken)
    {
        var entity = _data.FirstOrDefault(x => x.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
        return Task.FromResult(entity);
    }

    public Task AddAsync({Feature} entity, CancellationToken cancellationToken)
    {
        _data.Add(entity);
        _logger.LogDebug("Added {Feature} with ID {Id}", entity.Id);
        return Task.CompletedTask;
    }

    public Task UpdateAsync({Feature} entity, CancellationToken cancellationToken)
    {
        var existing = _data.FirstOrDefault(x => x.Id == entity.Id);
        if (existing != null)
        {
            _data.Remove(existing);
            _data.Add(entity);
            _logger.LogDebug("Updated {Feature} with ID {Id}", entity.Id);
        }
        return Task.CompletedTask;
    }

    public Task DeleteAsync(Guid id, CancellationToken cancellationToken)
    {
        var entity = _data.FirstOrDefault(x => x.Id == id);
        if (entity != null)
        {
            _data.Remove(entity);
            _logger.LogDebug("Deleted {Feature} with ID {Id}", id);
        }
        return Task.CompletedTask;
    }
}

// Repository interface
namespace {ServiceName}.API.Infrastructure.Repositories.Interfaces;

public interface I{Feature}Repository
{
    Task<List<{Feature}>> GetAllAsync(CancellationToken cancellationToken);
    Task<{Feature}?> GetByIdAsync(Guid id, CancellationToken cancellationToken);
    Task<{Feature}?> FindByNameAsync(string name, CancellationToken cancellationToken);
    Task AddAsync({Feature} entity, CancellationToken cancellationToken);
    Task UpdateAsync({Feature} entity, CancellationToken cancellationToken);
    Task DeleteAsync(Guid id, CancellationToken cancellationToken);
}
