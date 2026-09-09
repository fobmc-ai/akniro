# ADR-0011: Engineering Asset and Parameter Synchronization

- Status: accepted
- Date: 2026-09-09
- Scope: PM-FOUNDATION-004

## Decision

Project Control Center manages artifact metadata, revisions, content hashes, progress and release composition. PLC/HMI/Firmware files are engineering assets; live values and field parameters remain owned by Edge/Runtime domain services. Parameter synchronization is snapshot/diff/validate/approve/apply/read-back, never direct memory writes from the management UI.

All releases bind a compatible artifact set and rollback set. Edge is the synchronization boundary and must support offline queue, idempotent replay, conflict queue, audit and signed artifacts. Sensitive customer engineering data is Edge-only by default.

## Consequences

开发人员可以在管理软件中看到进度、工程版本和现场偏差，而实时控制仍保持隔离。实现需要 Artifact、Parameter Snapshot、Sync Queue 和 Compatibility Matrix，但可以支持 PLC、HMI、固件和设备包协同升级。
