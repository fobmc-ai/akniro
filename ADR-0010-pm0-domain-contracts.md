# ADR-0010: PM-0 Domain and Interaction Contracts

- Status: accepted
- Date: 2026-09-09
- Scope: PM-FOUNDATION-003

## Decision

工程项目管理软件先冻结 PM-0 对象、状态机、权限、API envelope、错误模型和事件目录，再实现数据库、服务和 UI。核心对象使用稳定 ID、租户/站点/项目/机器 scope、revision 和 owner；写操作必须经过授权、校验、并发检查、持久化、审计和 Outbox。

## Consequences

不同页面和服务不能各自定义状态和数据含义，AI/同步/报表可以消费同一契约。前期需要维护 Schema 和契约测试，但后续可以替换数据库、HTTP 框架和前端实现而不破坏领域边界。
