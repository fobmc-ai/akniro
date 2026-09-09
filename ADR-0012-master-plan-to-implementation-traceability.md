# ADR-0012: Master Plan Implementation Traceability

- Status: accepted
- Date: 2026-09-09
- Scope: GOV-IMPLEMENTATION-001

## Decision

MASTER_PLAN 的每个可交付主题都必须登记为带稳定 ID 的 Work Package，并进入 Project Control Center。工作包必须有 owner、Design Goal、Acceptance Criteria、Test Plan、依赖、风险、目标 Release 和回滚计划。

当真实软件、硬件或现场数据尚不存在时，允许使用显式 Placeholder；Placeholder 只能支持结构、接口和页面开发，不能通过测试、发布或 AI 高可信上下文门禁。真实数据到达后通过新 revision 回填，并保留来源、校验、审核和回归证据。

## Consequences

长期规划不会停留在文档里，开发进度和验证证据都能在管理软件中看到。代价是每个工作包需要维护追溯信息，但可以减少重复开发、虚假完成和后期数据补录风险。
