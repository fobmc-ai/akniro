# 工程能力适配与验证契约

管理中心通过统一 capability 适配层承载 PLC、HMI、EDA、Motion、Vision、Robot、Firmware、Edge 和 FAT/SAT 工程能力。当前实现位于 `src/zhinen_pm/engineering.py`，提供稳定 ID、能力域、验证检查项和安全门禁。

## 运行模式

- `SIMULATED`：允许在无真实工具/设备时运行确定性模拟验证，结果只能作为开发证据；
- `CONTRACT_ONLY`：只验证接口、数据和安全约束，不模拟真实实时行为；
- 所有能力的 `safetyGate` 均为 `HUMAN_APPROVAL_REQUIRED`；
- 验证成功不等于可发布、可部署或可操作现场设备。

## API

- `GET /api/engineering/capabilities`：列出能力、检查项和门禁；
- `POST /api/engineering/validate`：提交 `{capabilityId, payload}`，返回 `PASSED`、`CONTRACT_PASSED` 或 `BLOCKED`；
- `POST /api/engineering/runtime-simulate`：运行确定性的 PLC 周期/看门狗/安全停机模拟，支持 `watchdog`、`communication_loss`、`safety_trip` 故障注入；
- `POST /api/projects/{projectId}/plc/download-simulate`：校验 APPROVED PLC Artifact、人工审批和回滚版本，生成确定性 Edge 下载清单；明确 `writesController=false`，不直接写控制器；
- PLC 下载模拟成功/阻塞都会生成对应 Test Run 与 Evidence；成功为 `PASSED/VALIDATED`，阻塞保留 `FAILED/DRAFT`，并返回稳定的操作结果，便于发布与部署前审计；
- `POST /api/projects/{projectId}/plc/monitor-simulate`：按稳定顺序返回 Tag 在线监视快照，支持通信丢失、看门狗和安全停机故障注入；
- `POST /api/projects/{projectId}/builds/firmware`：确定性固件镜像构建，记录 source/image hash，并验证断电恢复和回滚路径；
- `POST /api/projects/{projectId}/simulate`：生成测试运行和验证证据；除通用检查外，HMI 标签集合、EDA IO/BOM、Motion 软限位、Vision 阈值、Firmware 哈希、Edge 幂等性也会输出结构化失败原因；
- 测试用例执行无论通过或失败都会留存 Evidence；通过结果转为 `VALIDATED`，失败结果保留 `DRAFT` 并关联测试用例，供问题定位与复测审计。
- PLC 与 Firmware 构建失败会自动创建 OPEN Issue，并以 `diagnosed_by` 关联失败 Evidence；构建能力 ID 与问题标题保持准确对应。
- `POST /api/projects/{projectId}/test-plans/execute` 批量执行计划内用例，汇总 Test Run/Evidence，并按全通过推进 `COMPLETED`，否则推进 `FAILED`。
- Release Gate 还必须具备签名、SBOM 和 `rollbackRevision`，与人工审批、验证证据及已测试资产共同满足发布条件。
- Issue 进入 CLOSED 前必须绑定同项目且状态为 `VALIDATED` 的 Evidence；失败验证自动预填证据链接，防止无证据关单。
- Knowledge Article 进入 `APPROVED` 前必须具备来源、适用版本、`VALIDATED` 验证状态、关联测试和失效条件。
- Maintenance Record 进入 `COMPLETED/CLOSED` 前必须记录现场机器、执行人、Release、结果、异常和回滚信息。
- AI 上下文仅纳入当前项目内已批准知识、已验证证据、通过测试和已批准/发布资产等可信状态；被过滤对象会返回原因。
- Deployment Request 已纳入管理中心，服务端强制 Release 角色授权、目标机器/环境、签名、健康检查、观察窗口和回滚路径；AI 无部署权限。
- AI 上下文对 Deployment Request 仅允许 `CONFIRMED` 记录进入，待授权/执行/观察对象默认过滤。
- Machine Commit 将 Machine Snapshot、已测试 Artifact、branch、parent 和 rollback commit 绑定，并生成确定性 commit hash。
- Artifact Manifest 增加持久化 revision 与 expectedRevision 冲突保护，旧数据库自动补列。
- 备份提供恢复校验：完整性、核心表、项目、审计/Outbox/权限相关计数和 revision 一致性必须全部通过。
- Web 审计页支持创建备份后立即执行恢复校验并显示结果。
- 验证/PLC/Firmware 构建失败会向项目 Owner 发送可去重的通知，通知关联 Test Run/构建 Run correlation ID。
- Edge 同步队列进入 CONFLICT/FAILED 会自动通知项目 Owner，并以 Sync ID 幂等去重。
- Edge Sync 创建和每次状态迁移都会记录 `pm.sync.queued` / `pm.sync.transitioned` 事件及 Audit；重复幂等请求不会重复产生队列事件。
- Issue 支持 S0-S4 严重度；S0/S1 创建时自动向项目 Owner 升级通知，并以 Issue ID 幂等去重。
- 普通测试用例失败与工程验证失败统一：自动创建 OPEN Issue、关联 DRAFT Evidence，并通知项目 Owner。
- Test Case 执行前强制校验 steps、inputs、expected 和 thresholds 四项验收定义。
- `POST /api/projects/{projectId}/releases/compose` 根据已测试 Artifact 生成确定性 SBOM 摘要、组件清单和回滚版本，并返回最新 Release Gate。
- 验证失败会自动创建 OPEN Issue，关联 `sourceTestRunId`、`evidenceId`、能力 ID 和错误列表，进入问题/CAPA 状态机；
- `POST /api/entities/{entityId}/payload`：以 Revision 乐观并发保护更新 CAPA 根因、修复版本、回归测试和关闭标准；Issue 页面提供对应录入入口；
- `POST /api/artifacts/{artifactId}/transition`：资产 TESTED→APPROVED 需要 Owner 人工批准，资产清单提供操作入口；
- `POST /api/entities/{entityId}/apply`：参数快照仅允许 APPROVED 对象携带人工 `approvalId` 进入 `PUSH_APPROVED` Edge 队列并转为 APPLIED；
- `POST /api/engineering/toolchain-matrix`：执行 PLC/HMI Golden Project 矩阵，比较工具链、编译、HMI Smoke 和期望/实际 Hash；
- `POST /api/projects/{projectId}/toolchain-matrix`：将矩阵结果持久化为 `tool_validation`，通过为 VALIDATED，失败为 FAILED，并保留审计记录；
- 模拟证据包含稳定 `traceHash`；Robot 握手顺序、FAT/SAT 清单、Edge 重放幂等性和生命周期指标均按确定性规则重放，便于回归比较；
- 能力验证同时保留执行时间 `validatedAt` 与排除时间字段的完整结果 `validationHash`，相同输入可跨运行逐字段比较，避免时间戳破坏回归确定性；
- 基础 `POST /api/engineering/validate` 也返回非空稳定 `validationHash`；`validatedAt` 仅作为审计观测字段，不参与 Hash。
- MOT-001 提供离散步进轴模拟，验证起点、目标、速度、软限位、轨迹和越界安全停机；
- VIS-001 支持样本期望/预测标签回放，输出 TP/TN/FP/FN 混淆矩阵、准确率和确定性回归结果；
- EDGE-001 支持事件 ID 离线重放，输出重复跳过数、实际应用数，并验证幂等/非幂等结果；
- EDA-001 输出 IO/BOM 缺失项、额外项和重复项明细，避免只返回一个一致性布尔值；
- HMI-001 支持画面 Smoke 序列回放，验证缺失页面、未知页面和导航顺序；
- LIFE-001 支持确定性 OEE 计算，输出 Availability、Performance、Quality、OEE，并拒绝非法停机/产量边界；同时支持显式上下限的 SPC 样本控制带与设备健康信号检查，输出越界样本、均值/σ、逐信号检查和可追溯结果；
- `LIFE-001`：生产指标、质量指标和维护流程统一进入生命周期验证，缺项会阻止软件验收证据通过；
- `COMM-001` 支持固定 FAT/SAT 调试顺序 `24V → Network → EtherCAT → IO → Safety → Servo → Cylinder → Vision → Station → Auto Cycle → Burn-in`，缺阶段、乱序或未通过证据均阻塞验收；
- 生命周期模拟证据可选包含 `spc_values/spc_lower/spc_upper` 与 `health_signals/health_limits`，越界样本和健康信号会产生结构化失败原因并自动进入问题流程；
- LIFE-001 支持 `product_trace` 记录 Product、Machine、Recipe、PLC State、Measurement、Parameters 和 Timestamp，并生成稳定 genealogy `traceHash`；字段不完整时阻塞验收。
- Release Gate 还要求 source revision、Machine Project revision、Schema/API/Event 版本、已知问题清单和目标环境，发布页提供对应录入字段；
- `GET /api/projects/{projectId}/readiness`：按工作包依赖计算可开始项；
- `GET /api/projects/{projectId}/capability-readiness`：按能力 ID 汇总 VALIDATED Evidence 覆盖情况；验收报告同时返回该矩阵；
- 验收报告 summary 同时提供 `openIssues` / `closedIssues`，用于确认失败验证是否已经完成 CAPA 收敛；
- 工程资产、参数和现场写入仍必须经 Artifact/Edge owner API、审批、回读和审计。

真实工具插件接入时，只替换 capability adapter，不改变项目对象、测试证据、Release 和安全边界。
