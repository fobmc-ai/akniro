# Architecture Changelog

## 2026-09-08 — V0.1

- Formalized the project name as 织能 V0.1 基础平台, with English identifier `Zhinen Foundation Platform V0.1`.
- Added formal product-family naming rules and repository slug `zhinen-platform`.
- Started the V0.1 contract-first source skeleton with Machine Project, Capability, and Resource Lease schemas.
- Established platform layers, Control/Data Plane split, realtime isolation, offline edge requirement.
- Added A/B/C classification and stable ID rules.
- Added canonical object ownership, project index, architecture map, AI context governance, deployment and recovery contracts.

## 2026-09-10 — Engineering validation loop

- Added deterministic PLC runtime simulation with watchdog, communication-loss, safety-trip, and safe-stop outcomes.
- Added domain-specific simulation diagnostics for EDA, Motion, Vision, Firmware, and Edge validation.
- Exposed runtime simulation and evidence-oriented validation through the PM control-center API.
- Added set-level HMI tag consistency validation for missing and unknown bindings.
## 2026-09-10 — 测试失败证据闭环

- `execute_test_case` 对通过和失败结果均持久化 Evidence；失败证据保持 `DRAFT`，并通过 `produces` 关联测试用例，保证问题定位、复测和验收审计链不断裂。
- PLC/Firmware 构建失败自动创建问题并关联失败证据，修正 PLC 构建失败的错误领域标识。
- 增加测试计划批量执行入口，统一汇总用例运行、证据和计划状态。
- Release Gate 增加 SBOM 与 rollback revision 门禁，确保发布包可追溯且可恢复。
- Release Gate 增加签名门禁，未签名发布包不能进入部署链。
- 增加 Release 组合接口，自动生成确定性 SBOM 摘要与组件清单。
- Issue 关闭增加同项目 VALIDATED Evidence 校验，自动失败记录预填证据关联。
- Knowledge Article 增加来源、版本、验证、测试和失效条件门禁，并接入 Web 录入表单。
- Maintenance Record 增加现场机器、执行人、Release、结果、异常和回滚门禁，并接入 Web 录入表单。
- AI 上下文增加可信状态过滤，草稿/失败证据及未批准运营记录不进入上下文，并返回审计可见的省略原因。
- 增加 Deployment Request 状态机与 Web 入口，隔离发布批准和现场部署授权。
- AI 上下文过滤未确认部署请求，避免将待执行变更误作为现场事实。
- 增加 Machine Commit，绑定机器快照、已测试资产、分支、父提交和回滚提交。
- Artifact Manifest 增加 revision 迁移与并发状态迁移保护。
- 增加备份恢复校验接口，验证完整性、核心表、项目、审计/Outbox 和 revision 一致性。
- 审计页面接入“创建并校验备份”一键流程。
- 验证和构建失败接入项目 Owner 通知链，并以 Run ID 做幂等去重。
- Edge 同步冲突/失败接入 Owner 通知链，并以 Sync ID 做幂等去重。
- S0/S1 Issue 自动进入 Owner 升级通知链，并校验严重度范围。
- 普通测试用例失败自动进入 Issue/CAPA 链并关联失败证据，统一各测试入口行为。
## 2026-09-10

- 生命周期验收补齐确定性 SPC 控制带与设备 Health 信号检查；结果写入模拟证据并纳入全域 12 项验收套件，越界自动失败，不把未接入真实设备误报为现场验证。
- 管理中心增加项目作用域的控制平面健康快照 API，集中显示数据库容量、Outbox、通知、审计、搜索 freshness 和备份状态。
- 管理平面写入增加持久化 Event Outbox，带 schema/correlation/idempotency、发布/失败/重试状态，并纳入重启与备份校验。
- 增加独立 Review 对象与审批门禁，绑定 reviewer、revision、结论和意见，禁止评审 owner 自审通过。
- 增加项目级 Traceability Graph API 与 Web 页面，解析对象引用并显示未解析关系。
- 实体内容 revision、Machine Object revision、Artifact 状态和实体关联统一产生 Event Outbox 事件，补齐跨模块协同覆盖面。
- 实体关联事件和审计改为贯穿真实操作者，避免系统代写掩盖责任主体。
- Release Gate 增加来源 revision、Machine Project revision、Schema/API/Event 版本、已知问题和目标环境绑定，并同步发布页面录入。
# 2026-09-10

- 管理中心新增事件 Outbox 页面，展示事件类型、幂等键、Actor、尝试次数和发布状态；QUEUED/FAILED 事件可在项目权限范围内人工发布或重试，形成跨模块协同的可见运维闭环。
- 管理中心新增 PLC / 固件构建台，调用确定性模拟构建接口并自动登记 Artifact、Test Run、Evidence；失败构建自动进入 Issue/CAPA 处理链路，断电恢复验证保留回滚引用。
- Artifact 创建事件补齐稳定 `artifactId`、审计和 Event Outbox 同事务写入，失败构建的产物、问题、通知和事件可被下游一致追溯。
