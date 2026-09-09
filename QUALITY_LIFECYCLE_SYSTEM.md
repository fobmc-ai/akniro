# 工程质量与生命周期系统

## 1. 定位

质量系统是织能工程项目控制中心的核心子系统，负责把设计目标、实现、测试、问题、知识、发布和维护连接成可审计闭环。质量不等到软件出问题后才开始，而是在功能设计阶段建立验收标准。

## 2. 一级对象

| 对象 | 作用 | 必须关联 |
|---|---|---|
| Design Goal | 定义功能/算法/工具要达到什么目标 | Requirement、Acceptance Criteria |
| Test Plan | 定义验证范围、环境和测试策略 | Design Goal、Risk |
| Test Case | 可重复的测试步骤和预期结果 | Requirement、Design Goal |
| Test Run | 某次实际执行 | Test Case、Environment、Version |
| Test Evidence | 日志、波形、截图、数据和报告 | Test Run、Artifact |
| Tool Validation | 验证 PLC/HMI/编译器/模拟器/驱动工具 | Tool Version、Golden Project |
| Problem | 软件、机器、算法或流程问题 | Version、Evidence、Root Cause |
| CAPA | 纠正和预防措施 | Problem、Regression Test |
| Knowledge Article | 经验证、可复用的工程知识 | Evidence、Owner、适用版本 |
| Release | 可交付版本和发布包 | Tests、Approval、Rollback |
| Maintenance Record | 现场升级、补丁、维修和版本偏差 | Machine、Release、Problem |

## 3. 设计先行规则

任何功能、算法、工具能力、PLC 功能、HMI Widget 或设备能力，在进入实现前必须有 Design Goal：

- Goal ID、目的和非目标；
- 输入、输出和数据质量；
- 前置条件和适用范围；
- 正常、边界和异常行为；
- 性能、精度、延迟、资源和安全指标；
- 失败时的确定性行为；
- 测试数据、环境和通过阈值；
- 风险、降级策略和回滚方案。

没有 Design Goal 和 Acceptance Criteria 的任务只能处于 Proposed，不能进入 Implementing 或 Done。

## 4. 测试分层与门禁

```text
Design Goal
  -> Contract/Schema
  -> Unit / Algorithm
  -> Component
  -> PLC-HMI/Device Integration
  -> Simulation / Fault Injection
  -> Hardware-in-loop
  -> FAT/SAT
  -> Regression
  -> Release Acceptance
```

测试类型至少包括 Schema、API、Event、Unit、Property、Algorithm、PLC/HMI Integration、Simulation、Realtime Timing、Hardware-in-loop、Security、Migration、Deployment/Rollback 和 Disaster Recovery。

测试结果分为 Pass、Fail、Blocked、Not Applicable；Blocked 必须有原因和解除条件，不能伪装成 Pass。

## 5. PLC/HMI/工程工具验证

工具本身必须有验证矩阵，至少覆盖：

- LD/ST/FB 语义和编译错误；
- AST/IR/Target 一致性；
- Simulator 与 Runtime 行为一致性；
- Tag、HMI、Alarm、Trend、Recipe 绑定；
- Online Monitor、Download/Upload、Online Change；
- Driver、EtherCAT、通讯掉线和恢复；
- 断电、重启、版本兼容和回滚；
- Golden Project 的可重复构建和结果。

每个工具版本必须有 Supported、Validated、Known Limitations、Blocked 和 End-of-Support 状态。未通过 Tool Validation 的版本不得进入生产工程。

## 6. 问题、根因与预防

问题流程：

```text
Capture -> Reproduce -> Bound -> Severity -> Owner
        -> Root Cause -> Fix -> Regression
        -> Release -> Verify -> Close / Rollback
```

严重度：S0 安全风险；S1 生产停止或数据损坏；S2 核心功能异常；S3 一般缺陷；S4 文档/优化建议。

问题关闭必须具备根因证据、修复版本、回归测试、受影响范围、预防措施和批准人。重复问题必须关联原问题并生成 CAPA，而不是重复开一条孤立 Bug。

## 7. 知识生命周期

```text
Draft -> Review -> Validated -> Approved -> Expired/Deprecated
```

知识必须记录来源、owner、适用设备/版本、验证时间、失效条件、关联测试和关联问题。AI 默认只能将 Approved 且版本匹配的知识作为高可信建议；其他知识必须明确标为未验证。

## 8. Release 与维护

Release 必须绑定源代码、Machine Project revision、Schema/API/Event 版本、依赖/SBOM、测试证据、已知问题、审批、目标环境和回滚版本。

维护系统需要支持 LTS、Hotfix、Security Patch、Deprecation、Migration、End-of-Support、现场版本盘点、版本偏差检测和升级结果记录。任何现场修改必须回写为新的 revision，不能只存在设备本地。

## 9. 质量追溯矩阵

```text
Requirement
  ↔ Design Goal
  ↔ Implementation / Commit
  ↔ Test Case / Run / Evidence
  ↔ Release / Machine
  ↔ Problem / Root Cause / Knowledge
```

发布前必须检查关键需求是否有实现和测试证据；问题关闭前必须检查是否需要新增测试、更新知识或修改标准。
