# ID Specification

IDs are immutable, uppercase, namespaced, and stable across releases. Format: `<DOMAIN>-<CAPABILITY>-<NNN>`, for example `PLC-LD-001`, `CORE-TAG-001`, `AI-CTX-003`.

## Domains

`CORE`, `PLC`, `HMI`, `VIS`, `MOT`, `ROB`, `SCADA`, `MES`, `QMS`, `WMS`, `WCS`, `EAM`, `EMS`, `APS`, `CLOUD`, `AI`, `QUAL`, `GOV`.

## Rules

- Requirement IDs, capability IDs, API IDs, event IDs, test IDs, and ADR IDs MUST be unique and never reused.
- Renames update labels, not IDs.
- Every implementation PR/change references at least one requirement or capability ID.
- Unknown IDs are a governance failure, not a reason to invent a new namespace.

