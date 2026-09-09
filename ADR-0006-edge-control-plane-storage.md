# ADR-0006: Edge Control-Plane Storage

- Status: accepted
- Date: 2026-09-09
- Scope: CORE-STORAGE-001

## Context

织能需要在断网和重启后保留项目 revision、审计记录和待发布事件，但实时 IO、PLC scan、Motion/EtherCAT 状态不能被通用数据库的延迟、锁或资源竞争影响。

## Decision

Edge Control Plane V0.1 采用 SQLite 作为本地事务存储，范围仅包括 project metadata/revisions、audit records、outbox、migration metadata 和 control-plane indexes。所有 schema migration 必须显式版本化并可回滚或安全失败。

Realtime Runtime、IO image、实时调度状态和高频 historian 不得依赖 SQLite；它们使用独立的 realtime-safe memory/storage contract。云端同步只读取已提交的 Control Plane facts 和明确允许的摘要。

Outbox 与业务事实在同一事务边界内提交；事件发布采用 at-least-once，消费者按 messageId 去重。应用重启后未发布事件必须可以继续投递。

## Consequences

Edge 部署获得成熟的事务、恢复和离线能力，同时保留实时边界。未来如果更换数据库，只需替换 storage adapter，不改变 domain/API/event contract。
