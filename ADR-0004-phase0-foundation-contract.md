# ADR-0004: Phase 0 Foundation Contract

- Status: accepted
- Date: 2026-09-09
- Scope: CORE-FOUNDATION-002

## Context

长期平台会同时承载实时控制、工程配置、设备驱动、AI、质量和云同步。若没有统一的数据所有权、消息语义、失败处理和验收边界，后续每个模块都可能建立自己的对象和状态，最终导致重复数据、不可追溯和高成本返工。

## Decision

Phase 0 以 Machine Project、稳定 ID、canonical ownership、版本化消息、Capability Registry、Resource Lease、Audit Log 和兼容性/恢复测试为唯一基础闭环。跨模块交互只允许使用 Query、Command、Event 和明确标记的 Projection；禁止跨模块直接读表、私有文件或运行时内存。

所有变更按 A/B/C 分类；问题按 Capture → Reproduce → Bound → Fix → Regression → Review → Apply → Observe → Close/rollback 流程处理。没有 owner、验收条件、测试路径和回滚说明的工作不得进入实现。

Phase 1 PLC 编译、下载和在线控制必须等 Phase 0 的契约测试与数据闭环通过后开始。

## Consequences

前期会增加 Schema、ADR、测试和审计工作，但能保证 PLC/HMI/EDA/Vision/Motion/AI/Cloud 使用同一机器模型，限制数据孤岛，减少无证据重复排查，并为离线运行、迁移和回滚保留边界。

## Rejected shortcuts

- 以最后写入者覆盖并发配置；
- 用事件隐藏命令；
- 让 AI 直接修改 Runtime 或 Safety 数据；
- 为 Demo 建立第二套 Tag/Device/Alarm 模型；
- 在没有迁移和回滚策略时发布持久化 Schema。
