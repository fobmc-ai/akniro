# Project Index

## Entry point

`MASTER_PLAN.md` 是长期产品/技术总纲；它定义 Machine Model、工程能力、AI 安全边界、分阶段路线和 Codex 工作规则。具体实现仍以 ADR、Schema 和模块契约为准。

Phase 0 implementation gate: `FOUNDATION_CONTRACT.md`、`DATA_INTERACTION_CONTRACT.md`、`CHANGE_CONTROL_RULES.md`。

工程项目管理软件规划：`PROJECT_MANAGEMENT_PLATFORM.md`、`ADR-0007-project-management-plane.md`。

质量与生命周期规划：`QUALITY_LIFECYCLE_SYSTEM.md`、`ADR-0008-quality-lifecycle-first-class.md`。

平台运营治理规划：`PLATFORM_OPERATIONS_GOVERNANCE.md`、`ADR-0009-platform-operations-governance.md`。

PM-0 领域契约：`PM0_CONTRACTS.md`、`ADR-0010-pm0-domain-contracts.md`。

工程资产与现场同步：`ENGINEERING_ASSET_SYNC.md`、`ADR-0011-engineering-asset-parameter-sync.md`。

总纲实施追溯：`IMPLEMENTATION_BACKLOG.md`、`ADR-0012-master-plan-to-implementation-traceability.md`。

管理中心证据审计：`ADR-0014-control-plane-evidence-apis.md`、`ENGINEERING_CAPABILITIES.md`、`IMPLEMENTATION_STATUS.md`。

当前代码骨架：`src/zhinen_foundation/`；契约测试：`tests/`；示例和校验入口：`examples/`、`tools/`。

PM-0 管理软件骨架：`src/zhinen_pm/`；PM-0 测试：`tests/test_pm0.py`。

This file is the low-cost navigation index for Codex. Read the smallest relevant entries before opening full documents.

| ID | Area | Primary documents | Status |
|---|---|---|---|
| CORE | canonical platform | `CORE_PLATFORM.md`, `DOMAIN_MODEL.md` | A |
| RT | deterministic execution | `REALTIME_ARCHITECTURE.md`, `PLC_RUNTIME.md` | B |
| ENG | engineering tools | `MACHINE_PROJECT.md`, `ENGINEERING_CAPABILITIES.md` | A/B |
| PLAT | extension platform | `PLUGIN_SDK.md`, `DRIVER_SDK.md` | B |
| FACT | factory applications | `SCADA.md`, `MES.md`, `QMS.md` | B |
| CLOUD | edge/cloud | `CLOUD_ARCHITECTURE.md`, `EDGE_CLOUD_SYNC.md` | B |
| AI | governed AI | `AI_CONTEXT_POLICY.md`, `AI_SAFETY.md` | A/B |
| QUAL | quality attributes | `SECURITY.md`, `TESTING.md`, `QUALITY_LIFECYCLE_SYSTEM.md` | A |
| GOV | decisions and change | `ADR-*.md`, `DEFINITION_OF_DONE.md`, `CHANGE_CONTROL_RULES.md` | A |
| BRAND | product identity | `BRAND_NAMING.md` | A |
| BUILD | implementation skeleton | `examples/`, `src/`, `web/`, `tests/`, `tools/` | A |

## Retrieval rule

Start here, follow one primary document, then only referenced contracts required by the task. Record newly discovered dependencies in this index.
