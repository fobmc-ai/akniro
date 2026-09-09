# 平台运营与治理契约

本文补齐工程项目管理软件在进入开发前必须冻结的组织、状态、环境、恢复和运营规则。

## 1. 组织与数据隔离

```text
Organization
  -> Department / Team
  -> Customer / Tenant
  -> Site / Factory
  -> Engineering Project
  -> Machine Project
```

每条记录至少带 `tenantId`、`siteId`、`projectId` 和 owner。跨租户读取默认禁止；跨项目引用必须显式授权并记录原因。公司通用知识与客户敏感知识分区存储，未经脱敏和批准不得跨租户复用。

### 权限模型

采用 RBAC + scope + risk policy：

`subject + tenant/site/project/machine scope + object + action + environment + risk`

角色只是默认权限集合，最终权限必须经过 scope 和风险策略计算。`DEPLOY`、`FORCE`、修改安全/运动/IO 的权限不能由普通项目编辑权限隐式获得。

## 2. 状态机

状态迁移由服务端规则执行，客户端只能请求迁移。每次迁移需要 actor、原因、前置条件结果、expectedRevision 和 audit record。

### 通用状态

```text
PROPOSED -> ACTIVE -> REVIEW -> APPROVED -> RELEASED -> ARCHIVED
    |          |         |          |
  REJECTED  BLOCKED   CHANGES    ROLLED_BACK
```

### 关键对象规则

- Requirement：Draft → Ready → Implementing → Verified → Accepted → Closed；没有验收条件不能 Ready。
- Work Item：Planned → In Progress → Review → Test → Done；没有证据不能 Done。
- Issue：Open → Reproduced → Root Caused → Fixed → Regression → Closed；S0/S1 需升级和批准。
- Test Run：Queued → Running → Passed/Failed/Blocked；失败不能自动发布。
- Release：Draft → Candidate → Validated → Approved → Released → Superseded/Rolled Back。
- Deployment：Requested → Authorized → Staged → Applied → Observed → Confirmed/Rolled Back。

## 3. 环境晋级

```text
Local
  -> CI
  -> Test
  -> Simulation
  -> HIL
  -> FAT
  -> SAT
  -> Production
```

每一级环境都有 entry gate、exit gate、责任人和证据。版本只能向前晋级，不能绕级；生产部署必须引用已签名 Release、目标 Machine、测试证据、批准记录和回滚版本。Runtime 的安全策略仍是最终执行门禁。

## 4. 备份、恢复与灾难演练

备份对象包括项目元数据、Machine Project revision、Audit、Outbox、附件索引、Schema/迁移版本和权限配置。备份必须有内容校验、来源版本、创建时间、保留策略和加密状态。

恢复等级：

1. 单个 revision 恢复；
2. 单项目恢复；
3. 单站点恢复；
4. Edge 完整恢复；
5. 灾难环境恢复。

备份成功不等于可恢复。每个 Release 周期至少执行一次自动恢复校验，并定期进行完整恢复演练。恢复后必须验证 Schema、Audit 连续性、Outbox 重放、权限隔离和 revision 一致性。

## 5. 搜索、索引和追溯

搜索索引是派生投影，不是 canonical 数据库。每个索引项保存 source type、source ID、source revision、tenant scope、updatedAt 和 freshness。索引落后时必须显示状态，不能让 AI 将索引结果当作最新事实。

核心查询：

- Requirement → Work → Commit → Test → Release；
- Release → Machine → Deployment → Problem；
- Problem → Root Cause → Regression → Knowledge；
- Object/Tag/Device → Owner → Consumers → History；
- 任意变更的影响范围和待审批事项。

## 6. 通知与升级

通知由事件驱动并按严重度、scope、角色和工作时间策略路由。至少支持任务逾期、测试失败、S0/S1 问题、审批等待、发布失败、同步冲突、备份失败、版本偏差和知识过期。

通知记录发送状态、接收策略、升级次数和最终处理结果；通知失败不能丢失原始事件。重复通知使用 correlationId 或 deduplication key 合并。

## 7. 平台自身可观测性

管理软件必须监控自身：API 延迟/错误、数据库容量、Outbox 堆积、同步失败、权限拒绝、审计写入失败、索引延迟、CI 失败率、备份状态、恢复校验和服务版本。

每个关键操作带 correlationId；日志分为业务审计、技术日志和指标，不能用普通日志替代 Audit。监控数据不得绕过租户隔离。

## 8. 数据保留、归档和隐私

每类数据定义 retentionClass、owner、归档条件、删除策略和法律/客户约束。默认：Audit、Release、FAT/SAT 和安全证据不可随意删除；工作草稿和临时索引可按策略清理；客户程序、图像、视频和 AI 上下文按项目策略决定是否离开 Edge。

删除、脱敏和跨项目复用都是受审计的变更。归档不等于删除；归档项目仍需可按权限恢复和追溯。

## 9. PM-0 必须通过的治理验收

管理中心通过 `GET /api/projects/{projectId}/ops` 提供项目作用域的控制平面健康快照，覆盖数据库容量、同步/事件 Outbox 队列、通知、审计写入失败计数、搜索 freshness 和备份可用性；事件通过 `GET /api/projects/{projectId}/events` 查询并可重试/发布。权限拒绝也会写入 `authorization.denied` Audit。该快照只反映管理平面事实，不冒充实时运行状态。

项目专属 Query 和实体 Query 必须携带 `X-Tenant-Id` 与 `X-Actor-Id`，由服务端执行 READ scope 校验；项目列表仅用于登录后的租户发现，后续项目数据不得依赖客户端隐藏字段实现隔离。

- 跨租户访问被拒绝并有审计；
- 非法状态迁移被拒绝；
- 未通过测试的 Release 不能批准；
- 未签名或无回滚版本的 Deployment 不能授权；
- 重启/恢复后 Outbox 可继续投递；
- 索引落后时显示 freshness；
- S0/S1 问题自动进入升级链；
- 备份恢复后 revision、Audit、权限和事件一致；
- 客户敏感数据不会被默认上传或跨项目检索。
