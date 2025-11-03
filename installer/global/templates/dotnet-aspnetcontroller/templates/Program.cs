using System.Reflection;
using FluentValidation;
using FluentValidation.AspNetCore;
using Serilog;
using {ServiceName}.API.Application.Services.Implementations;
using {ServiceName}.API.Application.Services.Interfaces;
using {ServiceName}.API.Infrastructure.Extensions;
using {ServiceName}.API.Infrastructure.Repositories.Implementations;
using {ServiceName}.API.Infrastructure.Repositories.Interfaces;

var builder = WebApplication.CreateBuilder(args);

// Configure Serilog
builder.Host.UseSerilog((context, config) =>
{
    config.ReadFrom.Configuration(context.Configuration);
});

// Add controllers
builder.Services.AddControllers();

// Add FluentValidation
builder.Services.AddFluentValidationAutoValidation();
builder.Services.AddValidatorsFromAssemblyContaining<Program>();

// Add Swagger/OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new() 
    { 
        Title = "{ServiceName} API", 
        Version = "v1",
        Description = "ASP.NET Core Web API with Controllers"
    });

    // Enable XML comments
    var xmlFile = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    if (File.Exists(xmlPath))
    {
        c.IncludeXmlComments(xmlPath);
    }
});

// Add OpenTelemetry
builder.Services.AddOpenTelemetryServices(builder.Configuration);

// Add Health Checks
builder.Services.AddHealthChecks();

// Add CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

// Register application services
builder.Services.AddScoped<I{Feature}Service, {Feature}Service>();
builder.Services.AddScoped<I{Feature}Repository, {Feature}Repository>();

var app = builder.Build();

// Configure middleware pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "{ServiceName} API V1");
    });
}

app.UseHttpsRedirection();
app.UseCors("AllowAll");
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();
app.MapHealthChecks("/api/v1/health");

app.Run();

// Make the implicit Program class public so test projects can access it
public partial class Program { }
