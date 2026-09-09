# ADR-0005: Migration, Outbox and Service Boundary

- Status: accepted
- Date: 2026-09-09
- Scope: CORE-FOUNDATION-003

## Decision

V0.1 uses explicit, ordered migrations for persisted project revisions; migrations are pure, idempotent, version-paired functions and unknown required versions fail closed. Domain facts are first appended to an Outbox before publication; publishing is at-least-once and consumers deduplicate by message ID. Core services expose transport-neutral methods and typed errors; HTTP, gRPC and WebSocket adapters are separate layers.

## Consequences

Persistence, event delivery and API transport can evolve independently. A failed publisher can retry without losing the committed fact, while a failed migration cannot silently reinterpret data. The first implementation remains standard-library-only and does not prematurely select a web framework.
