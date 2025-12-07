# Patterns and Best Practices

## Recommended Practices

- Standard project structure

## Language-Specific Best Practices

- Use strict TypeScript mode
- Prefer const over let
- Use async/await over callbacks
- Leverage type inference where appropriate
- Follow functional programming patterns


# Quality Standards

## Testing

- **Unit Test Coverage**: ≥80%
- **Branch Coverage**: ≥75%
- Test all business logic
- Test error cases and edge cases
- Use descriptive test names

## Code Quality

- **SOLID Compliance**: 70/100
- **DRY Compliance**: 70/100
- **YAGNI Compliance**: 70/100
- Write self-documenting code
- Keep methods small and focused
- Use meaningful names

## Areas for Improvement

- Run full architectural review for detailed insights

## TypeScript Specific

- Strict mode enabled
- No `any` types (use `unknown` if needed)
- ESLint passing with zero warnings
- Prettier formatting

## Template Validation Checklist

Before using this template, verify:

### CRUD Completeness
- [ ] Create operation (endpoint + handler + validator)
- [ ] Read operation (GetById + List + handlers)
- [ ] Update operation (endpoint + handler + validator)
- [ ] Delete operation (endpoint + handler + validator)

### Layer Symmetry
- [ ] All UseCases commands have Web endpoints
- [ ] All Web endpoints have UseCases handlers
- [ ] Repository interfaces exist for all operations

### Pattern Consistency
- [ ] All entities follow same operation structure
- [ ] Naming conventions consistent
- [ ] Placeholders consistently applied

See documentation for detailed validation checklist.
