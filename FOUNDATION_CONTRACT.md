# V0.1 Foundation Contract

## Purpose

V0.1 的目标是证明平台边界和数据协同方式，而不是提前实现完整 PLC IDE、Runtime、HMI 或云平台。任何后续实现必须先通过本契约定义的最小闭环。

## Scope

V0.1 只交付以下六个核心能力：

1. Machine Project 的加载、保存、版本识别和 Schema 校验；
2. 稳定 ID、对象所有权和引用关系；
3. Capability Registry 的注册、查询、版本和生命周期；
4. Resource Manager 的声明、租约、过期和冲突处理；
5. Audit Log 的统一记录和查询；
6. 版本兼容、迁移、错误、回滚和离线行为的契约测试。

PLC 编译器、实时调度、真实设备驱动、HMI 编辑器、云同步和 AI Agent 在本阶段只定义接口，不实现生产行为。

## Non-goals

- 不在 V0.1 选择并锁死全部最终技术栈；
- 不实现危险运动、Safety、Force、现场 Deployment；
- 不引入云端作为运行依赖；
- 不建立第二套 Tag、Device、Alarm 或 Recipe 数据库；
- 不用临时字符串协议替代正式版本化契约。

## Invariants

- 每个持久化对象只有一个 authoritative owner；其他模块只能通过 API、事件或共享 Schema 读取。
- Control Plane 的配置写入必须经过校验并产生版本；Data Plane 只保存运行事实，不能偷偷变成配置库。
- 命令表达意图，事件表达已经发生的事实；事件不得作为隐藏命令。
- 所有写操作必须携带身份、作用域、相关 ID、幂等键和审计信息。
- 所有跨模块消息必须有 schemaVersion、correlationId、causationId 和时间戳。
- 任何未知的必需版本必须 fail closed；未知的可选字段在安全的情况下保留。
- 关键失败必须可定位、可重试或可回滚；禁止静默吞错。

## Minimum acceptance criteria

| Area | Acceptance |
|---|---|
| Project | 合法项目可加载、保存、再次加载且语义等价；非法项目被拒绝并指出路径、错误码和 Schema 版本 |
| Identity | 重复、未知、越界或格式不合法的 ID 被拒绝；ID 永不复用 |
| Ownership | 每个对象的 owner 可查询；跨 owner 直接写入被拒绝 |
| Capability | 同一 capability 的版本和生命周期规则可验证；缺少 prerequisite 时不能激活 |
| Resource | 冲突租约、过期租约和关键资源不可用均有确定性结果；关键资源不可用时 fail closed |
| Audit | 每次创建、修改、批准、迁移、回滚和失败都产生不可变审计记录 |
| Compatibility | Schema/API/Event 的兼容性测试能区分 additive、deprecated 和 breaking change |
| Offline | 断云时本地核心能力继续工作；云恢复后按明确的冲突策略同步，不能覆盖本地事实 |
| Recovery | 失败的写入、迁移和部署不会产生半完成状态；支持重试或恢复到上一个稳定版本 |

## First vertical slice

```text
Machine Project
  -> validate schema
  -> resolve IDs and ownership
  -> register capabilities
  -> acquire/release resource leases
  -> append audit records
  -> persist revision
  -> reload and verify semantic equivalence
```

完成该闭环前，不开始 Phase 1 的 PLC 编译、下载和在线控制功能。

当前代码已实现该闭环的基础骨架：项目校验、消息信封、Capability Registry、Resource Lease、Audit Log，以及不可覆盖的 JSON revision 持久化。迁移、outbox 和正式 API 将在下一步按对应契约实现。

## Required evidence

每个实现任务必须提交：Requirement/Capability ID、变更前后契约、测试结果、失败案例、迁移/回滚影响、未解决风险和成本说明。没有证据的“应该可以”不视为完成。
