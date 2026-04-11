---
agent: keycloak-auth-observability-specialist
---

# Keycloak Auth Observability Specialist - Quick Reference

## Purpose

Configures Keycloak JWT Bearer authentication with MapInboundClaims = false and ProcessKeycloakRoles mapping realm_access.roles and resource_access roles to ClaimTypes.Role. Sets up OpenTelemetry tracing with OTLP export, Serilog structured logging, health checks, and DbUp database migrations running before traffic is accepted..

## When to Use

- Implementing features related to this agent's specialty
- Need expert guidance in this specific domain

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/keycloak-auth-observability-specialist.md`
- Extended: `agents/keycloak-auth-observability-specialist-ext.md`