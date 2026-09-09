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
- 增加备份恢复校验接口，验证完整性、核心表、项目、审计/Outbox 和 revision 一致性。
- 审计页面接入“创建并校验备份”一键流程。
- 验证和构建失败接入项目 Owner 通知链，并以 Run ID 做幂等去重。
- Edge 同步冲突/失败接入 Owner 通知链，并以 Sync ID 做幂等去重。
- S0/S1 Issue 自动进入 Owner 升级通知链，并校验严重度范围。
