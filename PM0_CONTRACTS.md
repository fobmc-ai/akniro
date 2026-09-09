# PM-0 管理软件核心契约

## 1. 目标

PM-0 只冻结领域边界和交互契约，不绑定数据库、前端框架或部署方式。所有服务、页面、AI 工具和同步适配器都必须遵守本文。

## 2. 核心对象

所有对象都有：`id、type、schemaVersion、tenantId、siteId、projectId、status、ownerId、createdAt、updatedAt、revision、createdBy、updatedBy`。

### Engineering Project

管理一个平台研发或客户工程项目，包含 scope、成员、目标、里程碑、Machine Project 引用和当前 release。

### Requirement

必须包含 description、priority、acceptanceCriteria、nonGoals、owner、source 和 traceLinks。没有 acceptanceCriteria 不能进入 Ready。

### Design Goal

必须包含 purpose、inputs、outputs、constraints、metrics、failureBehavior、risk、testPlanId 和 acceptanceThresholds。算法和工具功能必须先创建它。

### Work Item

必须包含 kind、assignee、dependencies、affectedIds、estimate、acceptanceCriteria 和 evidenceLinks。没有证据不能进入 Done。

### Issue / Incident

必须包含 severity、detectedAt、environment、reproduction、impact、evidence、owner、rootCause、fixVersion、regressionTestIds 和 closureCriteria。

### ADR / Proposal

必须包含 context、decision、alternatives、consequences、affectedContracts、status 和 approvers。修改 Schema、ID、API、Event、Runtime 或安全边界必须关联 ADR。

### Test Case / Test Run / Evidence

Test Case 定义步骤、输入、预期结果和阈值；服务端在执行前校验四项定义。Test Run 记录版本、环境、执行人和结果；Evidence 保存日志、波形、截图、数据、校验值和来源。Evidence 不可原地覆盖。

### Release / Deployment Request

Release 绑定 source revision、Machine Project revision、Schema/API/Event 版本、依赖/SBOM、测试证据、已知问题、签名和 rollback revision。Deployment Request 还必须绑定目标机器、环境、批准人和观察窗口。

Deployment Request 只能由 Release 角色推进授权，状态按 `REQUESTED -> AUTHORIZED -> STAGED -> APPLIED -> OBSERVED -> CONFIRMED/ROLLED_BACK` 流转；授权、签名、健康检查和观察结果均由服务端校验。

Machine Commit 是机器工程的原子版本单元，必须绑定 Machine Snapshot、已测试 Artifact、branch、parent commit 和 rollback commit 引用。

### Review

Review 记录被评审的 revision、reviewer、结论和意见，状态为 `REQUESTED -> IN_REVIEW -> APPROVED | CHANGES_REQUESTED`。服务端要求 APPROVED 决策由具备 APPROVE 权限且不同于 Review owner 的人员完成。

### Knowledge Article / Maintenance Record

Knowledge Article 必须带来源、适用版本、验证状态、owner、关联测试和失效条件。Maintenance Record 记录现场机器、执行人、Release、结果、异常和回滚。

## 3. 状态机

状态只允许服务端按迁移规则修改，客户端只能提交 transition command。每次迁移必须验证权限、前置条件、expectedRevision 并产生 Audit/Event。

```text
Requirement: DRAFT -> READY -> IMPLEMENTING -> VERIFIED -> ACCEPTED -> CLOSED
Work Item: PLANNED -> IN_PROGRESS -> REVIEW -> TEST -> DONE
Issue: OPEN -> REPRODUCED -> ROOT_CAUSED -> FIXED -> REGRESSION -> CLOSED
ADR: PROPOSED -> REVIEW -> ACCEPTED -> SUPERSEDED
Test Run: QUEUED -> RUNNING -> PASSED | FAILED | BLOCKED
Release: DRAFT -> CANDIDATE -> VALIDATED -> APPROVED -> RELEASED -> ROLLED_BACK
Deployment: REQUESTED -> AUTHORIZED -> STAGED -> APPLIED -> OBSERVED -> CONFIRMED | ROLLED_BACK
Knowledge: DRAFT -> REVIEW -> VALIDATED -> APPROVED -> EXPIRED | DEPRECATED
```

通用退回状态为 `BLOCKED`，必须填写 reason、owner 和 unblockCriteria。非法迁移返回 `PM-STATE-001`。

## 4. 权限矩阵

| 动作 | Viewer | Engineer | Reviewer | QA | Owner | Release | AI |
|---|---:|---:|---:|---:|---:|---:|---:|
| READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | scope 内 |
| COMMENT | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SUGGEST | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MODIFY | - | scope 内 | scope 内 | 测试域 | 全项目 | 发布域 | 仅授权工具 |
| APPROVE | - | - | ✓ | 测试 | ✓ | 发布 | - |
| RELEASE | - | - | - | - | ✓ | ✓ | - |
| DEPLOY | - | - | - | - | 申请 | 授权 | - |
| FORCE | - | - | - | - | 受安全策略约束 | 受安全策略约束 | 禁止 |

权限计算为 subject + tenant/site/project/machine scope + object + action + environment + risk。AI 默认没有 APPROVE、DEPLOY、FORCE 权限。

## 5. API 契约

API 使用 transport-neutral envelope：

```json
{
  "messageId": "uuid",
  "messageType": "pm.requirement.create",
  "schemaVersion": "0.1",
  "actor": "user-or-agent-id",
  "tenantId": "TENANT-001",
  "siteId": "SITE-001",
  "projectId": "PROJECT-001",
  "correlationId": "uuid",
  "causationId": "uuid-or-null",
  "idempotencyKey": "stable-key",
  "expectedRevision": 3,
  "payload": {}
}
```

管理平面写入必须在同一事务中产生 Audit 与 Event Outbox 记录。项目/实体创建、实体内容 revision、状态迁移、实体关联、Machine Object revision 和 Artifact 状态变化都属于事件源。Event Outbox 至少保存 `messageType、schemaVersion、actor、tenantId、projectId、correlationId、causationId、idempotencyKey、payload、status、attempts`；发布失败进入 `FAILED`，只能通过重试回到 `QUEUED`，不得丢弃原始事件。

Query 不产生副作用；Command 必须幂等；写入顺序为 authorize → validate → concurrency check → persist → audit → outbox event。错误必须返回稳定 `code、message、path、retryable、correlationId`。

首批服务边界：Project、Requirement、Work、Problem、Governance、Quality、Release、Knowledge、Identity/Authorization、Audit、Search/Projection、Notification。

项目必须提供 Traceability Graph 查询：节点来自项目对象，边来自 canonical entity links 和已登记 payload 引用；未解析引用必须显式返回，不能静默丢失。所有关联写入还必须记录真实 actor，并产生 Audit/Event。

## 6. 事件目录

首批事件：

`pm.project.created`、`pm.requirement.accepted`、`pm.work.completed`、`pm.issue.opened`、`pm.issue.closed`、`pm.adr.accepted`、`pm.test.passed`、`pm.test.failed`、`pm.release.approved`、`pm.deployment.confirmed`、`pm.knowledge.approved`、`pm.backup.failed`、`pm.sync.conflict`。

事件是不可变事实，采用 at-least-once；消费者按 messageId 去重。事件不能代替命令，不能隐式触发危险控制。

## 7. PM-0 验收门禁

- 核心对象有稳定 Schema、owner、scope 和 revision；
- 每个状态机的非法迁移都有测试；
- 权限矩阵覆盖跨租户、跨项目和高风险动作；
- Command 幂等、并发冲突和错误模型有测试；
- 事件经过 Outbox，重启后可继续投递；
- Requirement → Design Goal → Work → Test → Release 可追溯；
- 没有测试证据的 Work/Release 不能完成/发布；
- AI 无法批准、部署或 Force；
- API/Event 版本和迁移路径已记录。
