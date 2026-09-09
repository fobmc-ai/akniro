# 织能总纲实施目录

## 1. 目的

将 [`MASTER_PLAN.md`](MASTER_PLAN.md) 的长期规划逐项落入管理软件，形成可执行、可验证、可回填的实施目录。总纲是方向；本目录是工程任务入口；代码、测试和现场数据是证据。

## 2. 工作包状态

```text
PLANNED -> CONTRACTED -> IMPLEMENTING -> TESTING -> VALIDATED -> RELEASED
    |          |             |             |
  DEFERRED  BLOCKED       FAILED       PLACEHOLDER
```

- `PLANNED`：已登记但尚未冻结契约；
- `CONTRACTED`：目标、owner、输入输出和验收标准已冻结；
- `IMPLEMENTING`：正在开发；
- `TESTING`：有实现但正在验证；
- `VALIDATED`：测试和证据通过；
- `RELEASED`：已纳入正式 Release；
- `PLACEHOLDER`：真实软件/硬件/现场数据尚不存在，只提供结构和待回填位置；
- `DEFERRED/BLOCKED/FAILED`：明确记录原因，不得被进度统计当作完成。

## 3. 总纲到软件的映射

| Work Package | 总纲主题 | 管理软件落点 | 当前状态 | 首个验证 |
|---|---|---|---|---|
| CORE-001 | Machine Model / Machine DNA | Machine Project、对象树、版本 | CONTRACTED | Schema + revision round-trip |
| CORE-002 | Tag/Device/Alarm/Recipe | 领域对象引用和 owner | PLACEHOLDER | ownership/ID contract |
| PLC-001 | PLC IDE 与 Compiler/IR | PLC 工程资产、构建记录 | PLACEHOLDER | golden project compile |
| PLC-002 | PLC Runtime | Runtime artifact、部署申请 | PLACEHOLDER | deterministic timing contract |
| HMI-001 | HMI Designer / shared tags | HMI artifact、Widget 验证 | PLACEHOLDER | PLC-HMI binding test |
| EDA-001 | EDA / 电气工程 | EDA artifact、BOM、IO 引用 | PLACEHOLDER | IO consistency check |
| MOT-001 | Motion / EtherCAT | Axis/Device Package、参数快照 | PLACEHOLDER | axis simulation |
| VIS-001 | Vision / Feeder | Vision artifact、样本和阈值 | PLACEHOLDER | algorithm acceptance set |
| ROB-001 | Robot capability layer | Capability、流程和测试 | PLACEHOLDER | handshake simulation |
| QUAL-001 | Digital Twin / tests | Test Plan、Run、Evidence | CONTRACTED | fault injection contract |
| QUAL-002 | Tool validation | PLC/HMI/driver 验证矩阵 | CONTRACTED | golden project matrix |
| PM-001 | 项目/需求/任务/问题 | Project Control Center | IMPLEMENTING | API + UI smoke test |
| PM-002 | 知识与问题闭环 | Problem/CAPA/Knowledge | CONTRACTED | traceability test |
| REL-001 | Machine Git / Release | Release、SBOM、rollback | CONTRACTED | release composition |
| EDGE-001 | Edge/remote/sync | Artifact、参数、同步队列 | CONTRACTED | offline/replay/conflict |
| COMM-001 | Commissioning / FAT/SAT | 调试清单、验收证据 | PLACEHOLDER | commissioning checklist |
| LIFE-001 | 生产/质量/维护 | OEE/SPC/health/maintenance | PLACEHOLDER | data model contract |
| ECO-001 | Marketplace / fleet learning | Device Package、模板、授权 | DEFERRED | privacy/consent contract |

## 4. 每个工作包的最小记录

```text
workPackageId
masterPlanRefs
owner
scope
nonGoals
inputs
outputs
dependencies
designGoalId
acceptanceCriteria
testPlanId
placeholderData
affectedContracts
risks
status
evidenceLinks
targetRelease
rollbackPlan
```

没有 owner、Design Goal、Acceptance Criteria、Test Plan 和 targetRelease 的工作包不能进入 `CONTRACTED`。

## 5. Placeholder 规则

占位数据必须显式带：`isPlaceholder=true`、`source=planned`、`createdBy`、`createdAt`、`expectedType`、`fillCriteria` 和 `expiresAt`。

占位数据可以用于：

- 展示目录和页面布局；
- 建立对象引用和依赖关系；
- 提前编写 API、Schema 和测试；
- 生成待办和缺口报告。

占位数据不能用于：

- 标记功能已完成；
- 通过 Release/Deployment 门禁；
- 作为 AI 的高可信知识；
- 代替真实测试证据；
- 覆盖现场真实参数。

## 6. 回填流程

```text
Placeholder
  -> Real Artifact/Data Arrives
  -> Hash/Source/Version Check
  -> Owner Review
  -> Validate Against Design Goal
  -> Replace or Link
  -> Regression Test
  -> Audit + Evidence
```

回填不覆盖占位记录，而是产生新 revision，并保留 placeholder 与真实数据的关联。回填失败时进入 Problem/Conflict，不删除原始记录。

## 7. 开发顺序

1. PM-001：管理软件项目、目录、需求、任务、问题和权限；
2. CORE-001：Machine Project 对象和版本关联；
3. QUAL-001/002：测试库、证据和 PLC/HMI 工具验证；
4. REL-001：Release、兼容矩阵和回滚；
5. EDGE-001：离线同步、参数快照和冲突队列；
6. PLC/HMI/Motion/Vision/EDA/Robot 按工作包逐一实现和验证；
7. Commissioning、生产质量、维护和生态功能最后接入真实数据。

每个工作包完成后，管理软件必须能看到其进度、版本、测试证据、问题和回滚信息。
