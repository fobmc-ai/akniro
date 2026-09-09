# ADR-0007: Engineering Project Management Plane

- Status: accepted
- Date: 2026-09-09
- Scope: PM-FOUNDATION-001

## Context

织能的长期平台同时需要管理平台研发项目和客户机器工程项目。若把任务、需求、版本、审批和机器运行状态混为一体，会导致实时边界破坏、数据重复和责任不清。

## Decision

建立独立的 Engineering Project Management Plane（暂定产品名 Zhinen Engineering Control Center）。它拥有 Engineering Project、Requirement、Work Item、Issue、ADR、Test Evidence、Release 和 Deployment Request 等管理对象；Machine Project、Tag、Device、Alarm、Recipe 和 Runtime Data 仍由各自领域服务拥有。

管理软件只通过 Query、Command、Event 和 revision 引用与机器平台交互，不直接写 Runtime，不复制 canonical 数据，不把云端作为 Edge 运行依赖。第一版先实现 PM-0 契约和 PM-1 管理闭环，再连接发布、部署和 AI。

## Consequences

项目协同、工程资产和实时执行可以独立演进；问题和交付证据可追溯到具体 revision。代价是需要额外的服务边界、引用关系和权限模型，但能显著减少跨模块返工。
