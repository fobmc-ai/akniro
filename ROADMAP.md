# Roadmap

## Current position

The repository is currently at **Phase 0 — Foundation**. The complete long-term product and technology route is maintained in [`MASTER_PLAN.md`](MASTER_PLAN.md).

The Phase 0 gate is defined in [`FOUNDATION_CONTRACT.md`](FOUNDATION_CONTRACT.md), with cross-module coordination in [`DATA_INTERACTION_CONTRACT.md`](DATA_INTERACTION_CONTRACT.md) and problem/change handling in [`CHANGE_CONTROL_RULES.md`](CHANGE_CONTROL_RULES.md).

The separate engineering project management plane is defined in [`PROJECT_MANAGEMENT_PLATFORM.md`](PROJECT_MANAGEMENT_PLATFORM.md). Its PM-0 contract work must precede UI and full collaboration features.

PM-0 also includes organization isolation, state machines, environment promotion, backup/recovery, index freshness, notification escalation, platform observability, and data retention as defined in [`PLATFORM_OPERATIONS_GOVERNANCE.md`](PLATFORM_OPERATIONS_GOVERNANCE.md).

PM-0 domain objects, state machines, permissions, APIs and events are frozen in [`PM0_CONTRACTS.md`](PM0_CONTRACTS.md) before database, service or UI implementation.

Engineering artifact, progress, parameter and Edge synchronization follows [`ENGINEERING_ASSET_SYNC.md`](ENGINEERING_ASSET_SYNC.md); live control data remains outside the management plane.

## Delivery phases

| Phase | Focus | Classification |
|---|---|---|
| 0 | Project Schema, IDs, Machine Model, permissions, audit, storage | A — now |
| 1 | Minimal PLC compile/download/monitor loop | A — next |
| 2 | Industrial usability: alarm, recipe, commissioning, trace, standard FB | A — next |
| 3–4 | Platform extensions, Device Package, Motion/Vision, Edge, Logical Twin, CI | B — define interfaces first |
| 5–7 | AI engineering, lifecycle intelligence, ecosystem and migration | C — long-term route |

## A — foundation now

- Repository governance, IDs, object ownership, project manifest, capability registry, resource manager contract.
- Versioned API/event conventions, deployment package metadata, backup/recovery manifest, migration policy.
- AI context policy, project index, architecture map, machine context contract, agent permission model.
- Validation checklists, ADR workflow, technical debt register, architecture changelog.

## B — define interfaces, defer full implementation

- PLC compiler/runtime, HMI/Vision/Motion/Robot studios and simulators.
- Driver SDK and protocol adapters; SCADA/MES/QMS/WMS/WCS/EAM/EMS/APS application APIs.
- Cloud sync, fleet management, OTA, remote access, mobile clients, App Center marketplace.
- Historian scale-out, advanced reports, digital twin, virtual commissioning.

## C — long-term route

- Multi-site federated operations, autonomous optimization, cross-factory learning, advanced robotics orchestration.
- Certification-grade safety tooling, formal verification, model marketplace, full lifecycle carbon optimization.

