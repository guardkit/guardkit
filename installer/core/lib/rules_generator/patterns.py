"""Architecture pattern rules generator."""

from typing import Dict, Optional


def generate_pattern_rules(pattern: str) -> str:
    """
    Generate architecture pattern-specific rules.

    Args:
        pattern: Architecture pattern (e.g., "clean-architecture", "mvvm", "layered")

    Returns:
        Markdown content for pattern rule file
    """
    templates = {
        "clean-architecture": _clean_architecture_template,
        "clean": _clean_architecture_template,
        "mvvm": _mvvm_template,
        "model-view-viewmodel": _mvvm_template,
        "layered": _layered_template,
        "layers": _layered_template,
        "hexagonal": _hexagonal_template,
        "ports-and-adapters": _hexagonal_template,
        "microservices": _microservices_template,
        "monolith": _monolith_template,
    }

    template_func = templates.get(pattern.lower(), _generic_template)
    return template_func(pattern)


def _clean_architecture_template(pattern: str) -> str:
    """Clean Architecture pattern template."""
    return """# Clean Architecture

## Layers

### 1. Domain Layer (Core)
- Entities: Business objects with identity
- Value Objects: Immutable objects without identity
- Domain Services: Business logic that doesn't fit in entities
- Repository Interfaces: Data access contracts

### 2. Application Layer
- Use Cases: Application-specific business rules
- DTOs: Data transfer objects
- Application Services: Orchestrate use cases
- Interfaces for external services

### 3. Infrastructure Layer
- Repository Implementations
- External Service Adapters
- Database Access
- File System Access
- Framework-specific code

### 4. Presentation Layer
- Controllers/Handlers
- View Models
- UI Components
- API Endpoints

## Dependency Rules

- Dependencies point inward
- Domain layer has no dependencies
- Application layer depends only on Domain
- Infrastructure and Presentation depend on Application

## Directory Structure

```
src/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   ├── repositories/
│   └── services/
├── application/
│   ├── use_cases/
│   ├── dtos/
│   └── interfaces/
├── infrastructure/
│   ├── database/
│   ├── repositories/
│   └── external_services/
└── presentation/
    ├── api/
    └── web/
```

## Best Practices

- Keep domain layer pure (no framework dependencies)
- Use dependency injection for cross-layer dependencies
- Repository pattern for data access
- Use case per business operation
- DTOs for data transfer across boundaries
"""


def _mvvm_template(pattern: str) -> str:
    """MVVM pattern template."""
    return """# Model-View-ViewModel (MVVM)

## Components

### Model
- Business logic and data
- Data access layer
- Domain entities
- No UI knowledge

### View
- UI elements and layout
- Data binding to ViewModel
- User interaction events
- No business logic

### ViewModel
- Presentation logic
- Commands for user actions
- Observable properties
- Mediates between Model and View

## Data Binding

- View binds to ViewModel properties
- ViewModel notifies View of changes
- Commands handle user actions
- No direct View-Model communication

## Directory Structure

```
src/
├── models/
│   ├── entities/
│   ├── services/
│   └── repositories/
├── viewmodels/
│   ├── base_viewmodel.py
│   └── feature_viewmodel.py
└── views/
    ├── pages/
    └── components/
```

## Best Practices

- ViewModel should not reference View
- Use observable collections
- Implement INotifyPropertyChanged
- Commands for all user actions
- Keep Views thin (minimal code-behind)
- Unit test ViewModels
"""


def _layered_template(pattern: str) -> str:
    """Layered architecture pattern template."""
    return """# Layered Architecture

## Layers

### 1. Presentation Layer
- User interface
- API controllers
- Request/response handling
- Input validation

### 2. Business Logic Layer
- Business rules
- Domain services
- Workflow orchestration
- Business validation

### 3. Data Access Layer
- Database operations
- ORM/Query builders
- Repository implementations
- Data mapping

### 4. Cross-Cutting Concerns (Optional)
- Logging
- Authentication/Authorization
- Caching
- Error handling

## Dependency Rules

- Each layer depends only on layers below it
- No circular dependencies
- Lower layers should not know about upper layers

## Directory Structure

```
src/
├── presentation/
│   ├── api/
│   └── web/
├── business/
│   ├── services/
│   └── validators/
├── data/
│   ├── repositories/
│   └── models/
└── common/
    ├── logging/
    └── auth/
```

## Best Practices

- Keep layers loosely coupled
- Use interfaces between layers
- DTOs for data transfer
- Avoid bypassing layers
- Test each layer independently
"""


def _hexagonal_template(pattern: str) -> str:
    """Hexagonal architecture (Ports and Adapters) template."""
    return """# Hexagonal Architecture (Ports and Adapters)

## Core Concepts

### Core Domain
- Business logic
- Domain models
- Independent of external concerns

### Ports
- Interfaces defining how to interact with core
- Input ports (driven by application)
- Output ports (driven by infrastructure)

### Adapters
- Implementations of ports
- Primary adapters (UI, API)
- Secondary adapters (Database, External services)

## Directory Structure

```
src/
├── domain/
│   ├── models/
│   └── services/
├── ports/
│   ├── input/
│   └── output/
└── adapters/
    ├── primary/
    │   ├── rest_api/
    │   └── cli/
    └── secondary/
        ├── database/
        └── messaging/
```

## Best Practices

- Core domain has no external dependencies
- All external interactions through ports
- Adapters are interchangeable
- Test core without adapters
- Use dependency injection
"""


def _microservices_template(pattern: str) -> str:
    """Microservices architecture pattern template."""
    return """# Microservices Architecture

## Service Design

- Single responsibility per service
- Bounded contexts
- Independent deployment
- Decentralized data management

## Communication

- REST APIs or gRPC
- Message queues for async
- Event-driven architecture
- API gateway pattern

## Service Structure

```
service/
├── api/
│   └── endpoints/
├── domain/
│   └── models/
├── infrastructure/
│   ├── database/
│   └── messaging/
└── config/
```

## Best Practices

- Service autonomy
- Failure isolation
- Distributed tracing
- API versioning
- Circuit breakers
- Service discovery
"""


def _monolith_template(pattern: str) -> str:
    """Monolithic architecture pattern template."""
    return """# Monolithic Architecture

## Structure

- Single deployable unit
- Shared database
- Internal module boundaries
- Feature-based organization

## Directory Structure

```
src/
├── features/
│   ├── auth/
│   ├── users/
│   └── products/
├── shared/
│   ├── database/
│   └── utilities/
└── config/
```

## Best Practices

- Clear module boundaries
- Avoid circular dependencies
- Shared infrastructure code
- Feature folders
- Modular design for future extraction
"""


def _generic_template(pattern: str) -> str:
    """Generic pattern template for unknown patterns."""
    return f"""# {pattern.replace('-', ' ').title()} Architecture

## Overview

Follow established patterns and principles for {pattern} architecture.

## Structure

Organize code according to pattern principles:
- Clear separation of concerns
- Appropriate layer boundaries
- Consistent file organization

## Best Practices

- Follow SOLID principles
- Keep code maintainable
- Document architectural decisions
- Write tests at appropriate levels
- Use dependency injection where appropriate
"""
