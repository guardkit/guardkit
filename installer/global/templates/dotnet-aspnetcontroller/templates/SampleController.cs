using ErrorOr;
using Microsoft.AspNetCore.Mvc;
using {ServiceName}.API.Application.DTOs.Requests;
using {ServiceName}.API.Application.DTOs.Responses;
using {ServiceName}.API.Application.Services.Interfaces;

namespace {ServiceName}.API.Controllers;

/// <summary>
/// Sample controller demonstrating CRUD operations with ErrorOr pattern
/// </summary>
[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class {Feature}Controller : ControllerBase
{
    private readonly I{Feature}Service _service;
    private readonly ILogger<{Feature}Controller> _logger;

    public {Feature}Controller(
        I{Feature}Service service,
        ILogger<{Feature}Controller> logger)
    {
        _service = service;
        _logger = logger;
    }

    /// <summary>
    /// Get all {feature}s
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<{Feature}Response>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll(CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Retrieving all {feature}s");
        var result = await _service.GetAll{Feature}sAsync(cancellationToken);

        return result.Match(
            value => Ok(value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Get {feature} by ID
    /// </summary>
    [HttpGet("{id}")]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(
        [FromRoute] Guid id,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Retrieving {feature} with ID {Id}", id);
        var result = await _service.Get{Feature}ByIdAsync(id, cancellationToken);

        return result.Match(
            value => Ok(value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Create a new {feature}
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Create(
        [FromBody] Create{Feature}Request request,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Creating new {feature}");
        var result = await _service.Create{Feature}Async(request, cancellationToken);

        return result.Match(
            value => CreatedAtAction(
                nameof(GetById),
                new { id = value.Id },
                value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Update an existing {feature}
    /// </summary>
    [HttpPut("{id}")]
    [ProducesResponseType(typeof({Feature}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Update(
        [FromRoute] Guid id,
        [FromBody] Update{Feature}Request request,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Updating {feature} with ID {Id}", id);
        var result = await _service.Update{Feature}Async(id, request, cancellationToken);

        return result.Match(
            value => Ok(value),
            errors => Problem(errors)
        );
    }

    /// <summary>
    /// Delete a {feature}
    /// </summary>
    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Delete(
        [FromRoute] Guid id,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Deleting {feature} with ID {Id}", id);
        var result = await _service.Delete{Feature}Async(id, cancellationToken);

        return result.Match(
            _ => NoContent(),
            errors => Problem(errors)
        );
    }
}
