# ADR-0009: Platform Operations and Governance Contract

- Status: accepted
- Date: 2026-09-09
- Scope: PM-FOUNDATION-002

## Decision

工程项目管理软件采用 tenant/site/project/machine 分层隔离，RBAC 与 scope/risk policy 组合授权；对象状态由服务端状态机控制；版本必须按环境逐级晋级；备份和恢复是发布验收的一部分；搜索为带 freshness 的派生索引；通知由可去重事件驱动；平台自身必须具备审计、指标和恢复校验；数据按 retention class 管理，客户敏感数据默认留在 Edge。

## Consequences

管理软件具备长期运行、升级维护和多客户协作的基础治理能力。前期需要更多状态、权限和恢复测试，但能避免错误版本进入现场、数据串租户、索引过期误导 AI 以及无法恢复等高成本问题。
