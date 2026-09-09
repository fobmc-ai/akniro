# ADR-0014: Control-plane evidence APIs

- Status: accepted
- Date: 2026-09-10
- Scope: Project Control Center / PM Service

## Decision

The management center exposes project-scoped, read-only evidence views for `completion-audit`, `issue-preflight`, `export-manifest`, and `schema`. Each response includes checks, blocker reasons, stable object IDs, and deterministic hashes where applicable.

These endpoints read canonical owner data only. They cannot change status, approve Release, resolve sync conflicts, apply AI changes, or write to a controller. Export manifests are metadata-only and exclude secrets and controller runtime data.

## Consequences

One management-center page can prove software-scope readiness without treating progress percentages or placeholders as acceptance. Human approval, field driver certification, formal safety certification, and real-time hardware deployment remain explicit external gates.
