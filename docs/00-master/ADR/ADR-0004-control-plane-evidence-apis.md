# ADR-0004: 管理中心使用证据化只读审计接口

- 状态：Accepted
- 日期：2026-09-10
- 范围：Project Control Center / PM Service

## 背景

织能的工程对象、能力验证、问题 CAPA、Release、同步和备份由不同服务操作。仅展示当前状态不足以证明软件是否满足总纲，也容易把占位数据或未验证状态误认为完成。

## 决策

管理中心提供项目范围的只读证据接口：

- `completion-audit` 汇总能力 Evidence、工作包契约、完整性、同步、问题和 Release Preflight；
- `issue-preflight` 逐项返回 CAPA 关单缺项；
- `export-manifest` 生成脱敏对象/版本/资产/关系摘要和稳定 Hash；
- `schema` 返回持久化迁移版本和幂等迁移记录。

这些接口只能读取 canonical owner 数据，不能改变状态、批准发布、解决冲突或写入控制器。每个结论必须返回检查项、阻塞原因和可追溯对象 ID；时间戳不得进入稳定 Hash。

## 安全与边界

导出清单不包含凭据、Secrets 或控制器实时数据。AI 可以读取允许的审计结果，但不能通过审计接口获得 Apply、Release、Deploy 或 Safety Override 权限。真实硬件认证、正式安全认证和现场部署仍需要人工审批及现场证据。

## 影响

管理中心可以用一个项目级审计结论驱动验收，但 `ready=false` 时必须显示阻塞项，不能用进度百分比替代门禁。新增跨域审计字段时必须同时更新测试、索引和变更记录。
