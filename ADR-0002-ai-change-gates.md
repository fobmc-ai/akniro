# ADR-0002: AI Change Gates

- Status: accepted
- Date: 2026-09-08
- Scope: AI-SAFE-001

## Decision

AI follows Read → Suggest → Patch → Test → Apply → Deploy. Critical PLC, Motion, EtherCAT, Safety, and IO changes require explicit human approval before deployment.

## Consequences

AI remains useful for navigation, analysis, scaffolding, and review without becoming an unaccountable deployment authority.

