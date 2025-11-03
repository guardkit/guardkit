using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using {ServiceName}.API.Application.DTOs.Requests;
using {ServiceName}.API.Application.DTOs.Responses;
using {ServiceName}.Tests.Integration.Fixtures;

namespace {ServiceName}.Tests.Integration.Controllers;

public class {Feature}ControllerIntegrationTests : IClassFixture<ApiFactory>
{
    private readonly ApiFactory _factory;
    private readonly HttpClient _client;

    public {Feature}ControllerIntegrationTests(ApiFactory factory)
    {
        _factory = factory;
        _client = _factory.CreateClient();
    }

    [Fact]
    public async Task GetAll_ReturnsOkWithList()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/{feature}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var content = await response.Content.ReadFromJsonAsync<List<{Feature}Response>>();
        content.Should().NotBeNull();
    }

    [Fact]
    public async Task Create_WithValidData_ReturnsCreated()
    {
        // Arrange
        var request = new Create{Feature}Request { Name = "Integration Test {Feature}" };

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/{feature}", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var created = await response.Content.ReadFromJsonAsync<{Feature}Response>();
        created.Should().NotBeNull();
        created!.Name.Should().Be("Integration Test {Feature}");
        response.Headers.Location.Should().NotBeNull();
    }

    [Fact]
    public async Task GetById_WhenNotFound_Returns404()
    {
        // Act
        var response = await _client.GetAsync($"/api/v1/{feature}/{Guid.NewGuid()}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }
}
