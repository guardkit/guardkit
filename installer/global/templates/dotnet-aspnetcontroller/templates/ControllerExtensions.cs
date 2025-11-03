using ErrorOr;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ModelBinding;

namespace {ServiceName}.API.Infrastructure.Extensions;

/// <summary>
/// Extension methods for converting ErrorOr results to ActionResults
/// </summary>
public static class ControllerExtensions
{
    /// <summary>
    /// Convert ErrorOr errors to ProblemDetails response
    /// </summary>
    public static IActionResult Problem(this ControllerBase controller, List<Error> errors)
    {
        if (errors.Count is 0)
        {
            return controller.Problem();
        }

        if (errors.All(error => error.Type == ErrorType.Validation))
        {
            return ValidationProblem(controller, errors);
        }

        return Problem(controller, errors[0]);
    }

    private static IActionResult Problem(ControllerBase controller, Error error)
    {
        var statusCode = error.Type switch
        {
            ErrorType.Conflict => StatusCodes.Status409Conflict,
            ErrorType.Validation => StatusCodes.Status400BadRequest,
            ErrorType.NotFound => StatusCodes.Status404NotFound,
            ErrorType.Unauthorized => StatusCodes.Status401Unauthorized,
            ErrorType.Forbidden => StatusCodes.Status403Forbidden,
            _ => StatusCodes.Status500InternalServerError,
        };

        return controller.Problem(
            statusCode: statusCode,
            title: GetTitle(error.Type),
            detail: error.Description,
            type: error.Code);
    }

    private static IActionResult ValidationProblem(
        ControllerBase controller,
        List<Error> errors)
    {
        var modelStateDictionary = new ModelStateDictionary();

        foreach (var error in errors)
        {
            modelStateDictionary.AddModelError(
                error.Code,
                error.Description);
        }

        return controller.ValidationProblem(modelStateDictionary);
    }

    private static string GetTitle(ErrorType errorType) => errorType switch
    {
        ErrorType.Conflict => "Conflict",
        ErrorType.Validation => "Validation Error",
        ErrorType.NotFound => "Not Found",
        ErrorType.Unauthorized => "Unauthorized",
        ErrorType.Forbidden => "Forbidden",
        _ => "Server Error"
    };
}
