# Minimal Architecture Specification

This is a minimal architecture specification fixture for seam tests.

## System Context

**Name:** Test System
**Purpose:** Minimal system for testing
**Methodology:** modular

### Bounded Contexts

- Core: Main application logic
- Infrastructure: Support services

### External Systems

- Payment Gateway: Third-party payment processing

## Components

### Core Module

**Description:** Core business logic module
**Responsibilities:**
- Handle business rules
- Process requests

**Dependencies:** None

### Infrastructure Module

**Description:** Infrastructure support
**Responsibilities:**
- Logging
- Configuration

**Dependencies:**
- Core Module

## Crosscutting Concerns

### Observability

**Description:** Logging and metrics
**Applies To:** All modules

## Architecture Decisions

### ADR-001: Use Modular Architecture

**Status:** Accepted
**Context:** Need simple, maintainable structure
**Decision:** Use modular monolith architecture
**Consequences:**
- Simple deployment
- Clear module boundaries
