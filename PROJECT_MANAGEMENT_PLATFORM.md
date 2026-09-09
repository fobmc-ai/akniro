# 织能工程项目管理平台

> 暂定产品名：Zhinen Engineering Control Center（织能工程控制中心）  
> 产品定位：管理工业自动化工程项目、机器项目和平台研发协作的 Control Plane
> 重要边界：它管理变更和证据，但不直接执行 PLC、Motion、Safety 或 EtherCAT 控制。

## 1. 为什么需要独立的管理软件

织能同时面对两类项目：

1. **平台研发项目**：需求、架构、ADR、代码、测试、发布、技术债和团队协作；
2. **机器工程项目**：客户需求、方案、BOM、EDA、PLC/HMI/Vision/Motion、FAT/SAT、现场变更、维护和版本。

两者需要共享 ID、版本、审计、权限和证据规则，但不能混成同一张任务表或同一套运行数据。管理软件负责组织它们之间的关系，并把每次决策和交付变成可追溯记录。

## 2. 产品目标

- 一个项目从需求到发布、验收和维护都有明确状态；
- 需求、对象、代码、Schema、测试、部署和问题可以互相追溯；
- 多人、多 Agent、多模块协作时拥有清晰 owner、权限和锁/并发规则；
- 所有重大变更都有 Diff、审批、测试证据和回滚路径；
- 断网时 Edge/本地工程仍可工作，云端只做同步和协作增强；
- Codex/AI 能获得当前任务的最小、正确、可审计上下文；
- 管理层能看到进度、风险、质量和交付状态，工程师不需要重复录入数据。
- 功能和算法在开发前已有设计目标、验收标准和测试计划；工具版本在进入生产前已完成验证。

## 3. 不负责的事情

- 不替代 PLC Runtime、Motion Runtime、Safety Runtime 或设备驱动；
- 不把任务状态当作机器实时状态；
- 不直接修改 PLC 运行变量、Force IO 或下发危险控制；
- 不复制 Machine Project、Tag、Alarm、Recipe 的 canonical 数据；
- 不强制云端在线，不把聊天记录当作正式需求或审批记录；
- 不在第一版实现完整 ERP、CRM、MES、3D 数字孪生或企业即时通讯。

## 4. 分层定位

```text
管理软件：需求 / 任务 / ADR / 评审 / 测试证据 / 发布 / 风险 / 知识
                         |
                         v
Machine Project Control Plane：对象 / 版本 / 配置 / 部署意图 / 审计
                         |
                         v
Edge Runtime Data Plane：PLC / IO / Motion / Vision / Robot 实时事实
```

管理软件可以提出 Project Change、Deployment Request 或 Diagnostic Request；真正的应用、批准和执行必须通过对应 owner 的正式服务契约。

## 5. 核心对象与唯一所有权

| 对象 | 管理软件职责 | canonical owner |
|---|---|---|
| Engineering Project | 生命周期、成员、范围、里程碑、风险 | Project Management Service |
| Requirement | 需求、验收条件、优先级、追溯关系 | Requirements Service |
| Work Item | 任务、依赖、负责人、状态、成本 | Work Service |
| ADR / Proposal | 架构决策、替代方案、影响和批准 | Governance Service |
| Issue / Incident | 现象、复现、证据、根因、修复、关闭 | Problem Service |
| Test Plan / Test Case / Run / Evidence | 测试定义、执行结果、附件、环境 | Quality Service |
| Release / Deployment Request | 发布候选、批准、目标和回滚 | Release Service |
| Machine Project | 机器工程内容和 revision | Machine Project Service |
| Tag / Device / Alarm / Recipe | 引用和追溯，不复制定义 | 各自 canonical service |
| Audit Record | 查询和展示，不修改 | Audit Service |
| Knowledge Article | 已验证的经验和适用范围 | Knowledge Service |
| Design Goal | 功能/算法/工具的设计目标和验收指标 | Quality Service |
| Problem / CAPA | 根因、修复、回归和预防措施 | Problem Service |
| Tool Validation | PLC/HMI/编译器/模拟器/驱动版本验证 | Quality Service |
| Release / Maintenance | 发布、补丁、升级、回滚和现场维护 | Release Service |

## 6. 工作流

### 需求到交付

```text
Capture Requirement
  -> Scope / A-B-C / Acceptance / Non-goals
  -> Design / ADR / Impact Map
  -> Work Breakdown / Owner / Dependencies
  -> Implement / Review / Test Evidence
  -> Release Candidate / Approval
  -> Deploy or Handoff
  -> Observe / FAT-SAT / Close
```

### 问题闭环

```text
Capture -> Reproduce -> Bound -> Severity -> Owner
        -> Smallest Fix -> Regression -> Review
        -> Apply -> Observe -> Close / Rollback
```

### AI 协作闭环

```text
Task Context -> Read -> Suggest -> Human Review
             -> Patch -> Test -> Approval -> Apply
```

AI 生成的每个结果必须绑定任务、输入上下文、模型/Agent、权限、Diff、测试和操作者；生成者不能兼任最终 Reviewer。

## 7. 数据协同规则

- 管理软件只保存项目管理事实和引用，不保存实时 Tag 值或设备私有状态；
- 引用 Machine Project 时使用 `projectId + revision`，禁止引用可变工作目录；
- 任务、需求、测试、ADR、问题和发布都使用稳定 ID，并支持双向 traceability；
- 读数据优先使用 Query/Projection；变更使用 Command；事实使用 Event；
- 跨服务写入必须经过 owner API，禁止直接写其他服务数据库；
- 每个变更记录 `expectedRevision`，冲突时生成 Diff，不静默覆盖；
- 附件采用内容寻址和校验值，敏感文件按策略只保存在现场；
- 外部同步必须有 source、同步时间、冲突状态和人工决策记录。

## 8. 权限与角色

最小角色集合：Owner、Architect、Engineer、Reviewer、QA、Commissioning、Maintenance、Viewer、AI Agent。权限按 tenant/site/machine/project、对象类型、动作和环境细分。

至少区分：`READ / COMMENT / SUGGEST / MODIFY / APPROVE / RELEASE / DEPLOY / FORCE`。`DEPLOY` 和 `FORCE` 不因拥有项目编辑权限而自动获得；Safety、Motion、EtherCAT、IO 的高风险操作必须追加人工批准和运行时策略校验。

## 9. 第一版 MVP

第一版只做平台研发项目和 Machine Project 的通用管理闭环：

1. 项目、成员、角色、范围和状态；
2. Requirement、Work Item、Issue、ADR；
3. ID、依赖、关联和追溯图；
4. Revision、Branch、Diff、Review、Approval；
5. Design Goal、Test Case、执行记录和证据附件；
6. Release Candidate、部署申请、回滚引用；
7. Audit、活动流、搜索和最小仪表盘；
8. Problem/CAPA 和 Knowledge Article 基础闭环；
9. PLC/HMI/工程工具版本验证矩阵；
10. Codex/AI 的受限上下文接口。

第一版不做复杂甘特图、社交聊天、计费、完整 ERP、完整 MES、在线 PLC 控制和复杂云端分析。

## 10. 阶段路线

| 阶段 | 内容 | 门禁 |
|---|---|---|
| PM-0 | 对象、状态机、ID、权限、审计、事件和追溯契约 | Schema/contract tests |
| PM-1 | 项目、需求、任务、问题、ADR 的 CRUD 和状态流 | owner、并发、审计、权限 |
| PM-2 | Revision、Diff、Review、Approval、测试证据 | 签名/不可变 revision |
| PM-3 | Release、Deployment Request、Rollback、Machine Project 引用 | 人工批准和回滚测试 |
| PM-4 | Edge/Cloud 同步、离线队列、冲突解决 | 断网/恢复/冲突测试 |
| PM-5 | AI/Codex 上下文、知识沉淀和跨项目复用 | 最小上下文、审计、评估 |

PM-0 必须先完成，PM-1 才能开始；PM-3 之前不接现场部署；PM-5 之前不允许 AI 读取无关项目。

质量门禁由 [`QUALITY_LIFECYCLE_SYSTEM.md`](QUALITY_LIFECYCLE_SYSTEM.md) 定义。任何功能若没有 Design Goal 和 Acceptance Criteria，不得进入 Implementing 或 Done。

## 11. 验收标准

- 任一需求可以找到关联任务、代码变更、测试证据和发布结果；
- 任一发布可以找到来源 revision、审批人、测试结果和回滚 revision；
- 任一问题可以找到复现条件、证据、owner、修复和回归测试；
- 无权限用户不能读取或改变超出 scope 的对象；
- 并发修改不会静默覆盖；
- 断网期间本地可继续创建允许离线的工程记录，恢复后可重放或进入冲突队列；
- AI 上下文可解释：能显示读取了哪些对象、为什么读取、使用了什么权限；
- 所有关键状态迁移和失败都有 Audit Record。

## 12. 与主平台的关系

管理软件是上层协作和治理产品，Machine Project 是其管理的工业工程资产之一。两者共享 ID、权限、版本、审计和事件规范，但保持独立服务边界。任何新功能都必须先回答：它管理的是项目事实、机器工程事实，还是实时运行事实；只有确定 owner 后才能落库。

组织隔离、状态机、环境晋级、备份恢复、搜索 freshness、通知升级、平台可观测性和数据保留规则见 [`PLATFORM_OPERATIONS_GOVERNANCE.md`](PLATFORM_OPERATIONS_GOVERNANCE.md)。这些规则属于 PM-0 门禁，不得等 UI 完成后补充。
