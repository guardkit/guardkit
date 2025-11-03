using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Moq;
using ErrorOr;
using {ServiceName}.API.Application.DTOs.Requests;
using {ServiceName}.API.Application.DTOs.Responses;
using {ServiceName}.API.Application.Services.Interfaces;
using {ServiceName}.API.Controllers;

namespace {ServiceName}.Tests.Unit.Controllers;

public class {Feature}ControllerTests
{
    private readonly Mock<I{Feature}Service> _serviceMock;
    private readonly Mock<ILogger<{Feature}Controller>> _loggerMock;
    private readonly {Feature}Controller _controller;

    public {Feature}ControllerTests()
    {
        _serviceMock = new Mock<I{Feature}Service>();
        _loggerMock = new Mock<ILogger<{Feature}Controller>>();
        _controller = new {Feature}Controller(_serviceMock.Object, _loggerMock.Object);
    }

    [Fact]
    public async Task GetById_WhenExists_ReturnsOk()
    {
        // Arrange
        var id = Guid.NewGuid();
        var expected = new {Feature}Response 
        { 
            Id = id, 
            Name = "Test {Feature}",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };
        
        _serviceMock
            .Setup(x => x.Get{Feature}ByIdAsync(id, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expected);

        // Act
        var result = await _controller.GetById(id);

        // Assert
        var okResult = result.Should().BeOfType<OkObjectResult>().Subject;
        var response = okResult.Value.Should().BeOfType<{Feature}Response>().Subject;
        response.Id.Should().Be(id);
        response.Name.Should().Be("Test {Feature}");
    }

    [Fact]
    public async Task GetById_WhenNotFound_ReturnsNotFound()
    {
        // Arrange
        var id = Guid.NewGuid();
        var error = Error.NotFound("{Feature}.NotFound", $"{Feature} with ID {id} not found");
        
        _serviceMock
            .Setup(x => x.Get{Feature}ByIdAsync(id, It.IsAny<CancellationToken>()))
            .ReturnsAsync(error);

        // Act
        var result = await _controller.GetById(id);

        // Assert
        var objectResult = result.Should().BeOfType<ObjectResult>().Subject;
        objectResult.StatusCode.Should().Be(404);
    }

    [Fact]
    public async Task Create_WithValidData_ReturnsCreated()
    {
        // Arrange
        var request = new Create{Feature}Request { Name = "New {Feature}" };
        var expected = new {Feature}Response 
        { 
            Id = Guid.NewGuid(), 
            Name = "New {Feature}",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };
        
        _serviceMock
            .Setup(x => x.Create{Feature}Async(request, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expected);

        // Act
        var result = await _controller.Create(request);

        // Assert
        var createdResult = result.Should().BeOfType<CreatedAtActionResult>().Subject;
        var response = createdResult.Value.Should().BeOfType<{Feature}Response>().Subject;
        response.Name.Should().Be("New {Feature}");
    }

    [Fact]
    public async Task Delete_WhenExists_ReturnsNoContent()
    {
        // Arrange
        var id = Guid.NewGuid();
        
        _serviceMock
            .Setup(x => x.Delete{Feature}Async(id, It.IsAny<CancellationToken>()))
            .ReturnsAsync(Result.Deleted);

        // Act
        var result = await _controller.Delete(id);

        // Assert
        result.Should().BeOfType<NoContentResult>();
    }
}
