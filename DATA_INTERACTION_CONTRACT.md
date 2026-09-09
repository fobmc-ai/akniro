# Data Interaction and Coordination Contract

本文规定模块之间如何交换数据，避免 PLC、HMI、EDA、Vision、Motion、AI 和 Cloud 形成互相复制、互相写入的孤岛。

## Canonical ownership

| Object | Authoritative owner | Read consumers | Write path |
|---|---|---|---|
| Machine Project / revision | Project Service | IDE、部署、备份、AI | Project API + approved revision |
| Machine / Station / Module | Machine Model Service | 所有工程和运行应用 | Model API |
| Tag definition | Tag Registry | Runtime、HMI、Alarm、Historian | Tag API |
| Live tag value | Runtime / Data Plane | HMI、Rule、Historian、诊断 | Runtime command with policy |
| Device identity/topology | Device Registry | Driver、Runtime、应用 | Device API / discovery proposal |
| Alarm definition/state | Alarm Service | HMI、报告、AI | Alarm API; state from runtime facts |
| Recipe / parameter | Recipe Service | Runtime、HMI、MES | validated revision + approval |
| Capability | Capability Registry | App、授权、UI、调度 | Registry API |
| Resource lease | Resource Manager | Runtime、scheduler、observability | lease API |
| Audit record | Audit Service | Security、报告、AI governance | append-only audit API |

## Interaction types

1. **Query**：读取当前状态或投影，不产生副作用；可缓存但必须标明 freshness。
2. **Command**：表达意图，必须有 commandId、幂等键、actor、scope、权限、超时和结果状态。
3. **Event**：记录已经发生的事实，不要求消费者执行另一个动作；采用 at-least-once 时消费者必须幂等。
4. **Projection**：由 canonical owner 派生的读模型，必须记录 source revision 和生成时间。

模块不得通过读取其他模块的数据库表、私有文件或进程内存来完成交互。

## Common envelope

所有 API command 和 event 至少包含：

`messageId, messageType, schemaVersion, actor, tenantId, siteId, machineId, correlationId, causationId, occurredAt, idempotencyKey, payload`

实时数据还必须包含 tag/device 来源、quality、sample timestamp 和 sequence。配置写入还必须包含 expectedRevision，防止并发覆盖。

## State and failure rules

- 写入采用 validate → authorize → reserve → persist → publish 的顺序；失败时不得发布“成功”事件。
- 事件发布失败不能回滚已经提交的事实；使用 outbox/retry，消费者按 messageId 去重。
- 重复 command 返回第一次处理结果，不重复执行副作用。
- 并发 revision 不匹配时返回 conflict，由调用方重新读取并生成 Diff；禁止静默覆盖。
- 断网时 Edge 本地事实和安全控制继续运行；同步只处理明确标记为可同步的 Control Plane 变更。
- 不同来源的事实发生冲突时保留双方、记录冲突和决策，不以最后写入者自动取胜。

## Coordination sequence

```text
Request -> Context/Scope -> Authorization -> Validation
        -> Resource Reservation -> Apply to owner
        -> Audit -> Event/Projection -> Observe -> Reconcile
```

AI 只能在 Context、Authorization 和 Validation 之后提出变更；任何危险控制变更还必须经过 Simulation、Human Approval、Signed Revision 和 Runtime Validation。

## Versioning rules

- API、event、schema、capability、device package 分别版本化。
- additive change 可在同一小版本演进；删除、改语义或改变必填字段必须走 breaking-change ADR 和迁移方案。
- stable contract 必须有兼容性测试、owner、弃用日期、迁移说明和观测指标。
- 数据保留、迁移和回滚策略必须在发布前定义，不把迁移责任留给消费者猜测。

## Storage boundary

Edge Control Plane 的 project metadata/revisions、audit、outbox、migration metadata 和索引使用事务存储；V0.1 的参考实现为 SQLite。Realtime Runtime、IO image、scan 状态、Motion/EtherCAT 状态和高频 historian 不得依赖该存储路径。
