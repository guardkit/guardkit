using FluentValidation;
using {ServiceName}.API.Application.DTOs.Requests;

namespace {ServiceName}.API.Application.Validators;

public class Create{Feature}Validator : AbstractValidator<Create{Feature}Request>
{
    public Create{Feature}Validator()
    {
        RuleFor(x => x.Name)
            .NotEmpty().WithMessage("Name is required")
            .MaximumLength(100).WithMessage("Name must not exceed 100 characters");
    }
}

public class Update{Feature}Validator : AbstractValidator<Update{Feature}Request>
{
    public Update{Feature}Validator()
    {
        RuleFor(x => x.Name)
            .NotEmpty().WithMessage("Name is required")
            .MaximumLength(100).WithMessage("Name must not exceed 100 characters");
    }
}
