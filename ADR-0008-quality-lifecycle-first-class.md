# ADR-0008: Quality and Lifecycle as First-Class Platform Capabilities

- Status: accepted
- Date: 2026-09-09
- Scope: QUAL-LIFECYCLE-001

## Context

工业软件和 PLC/HMI 工具的风险不能依靠上线后的人工排查来控制。若设计目标、验收标准、工具验证、问题根因、知识沉淀和发布维护相互分离，缺陷会重复发生且无法判断一个版本是否真正可交付。

## Decision

将 Design Goal、Test Plan/Case/Run/Evidence、Tool Validation、Problem/CAPA、Knowledge Article、Release 和 Maintenance Record 作为工程项目控制中心的一级对象。任何功能、算法、工具能力或设备能力必须先定义设计目标和验收标准，再进入实现；Release 必须有完整测试证据、审批和回滚版本。

质量系统与 Machine Project、Runtime 和设备服务通过稳定 ID、revision、API、Event 和 Audit 协同，不复制实时状态或领域对象。AI 只可将已验证且适用版本匹配的知识作为高可信上下文。

## Consequences

前期需要编写更多设计卡、测试用例和验证报告，但能把质量前移，支持大厂式版本维护和问题预防，并形成需求到现场问题的闭环追溯。
