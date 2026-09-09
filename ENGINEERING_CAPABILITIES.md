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
- `POST /api/projects/{projectId}/builds/firmware`：确定性固件镜像构建，记录 source/image hash，并验证断电恢复和回滚路径；
- `POST /api/projects/{projectId}/simulate`：生成测试运行和验证证据；除通用检查外，HMI 标签集合、EDA IO/BOM、Motion 软限位、Vision 阈值、Firmware 哈希、Edge 幂等性也会输出结构化失败原因；
- 测试用例执行无论通过或失败都会留存 Evidence；通过结果转为 `VALIDATED`，失败结果保留 `DRAFT` 并关联测试用例，供问题定位与复测审计。
- PLC 与 Firmware 构建失败会自动创建 OPEN Issue，并以 `diagnosed_by` 关联失败 Evidence；构建能力 ID 与问题标题保持准确对应。
- `POST /api/projects/{projectId}/test-plans/execute` 批量执行计划内用例，汇总 Test Run/Evidence，并按全通过推进 `COMPLETED`，否则推进 `FAILED`。
- Release Gate 还必须具备 SBOM 和 `rollbackRevision`，与人工审批、验证证据及已测试资产共同满足发布条件。
- `POST /api/projects/{projectId}/releases/compose` 根据已测试 Artifact 生成确定性 SBOM 摘要、组件清单和回滚版本，并返回最新 Release Gate。
- 验证失败会自动创建 OPEN Issue，关联 `sourceTestRunId`、`evidenceId`、能力 ID 和错误列表，进入问题/CAPA 状态机；
- `POST /api/entities/{entityId}/payload`：以 Revision 乐观并发保护更新 CAPA 根因、修复版本、回归测试和关闭标准；Issue 页面提供对应录入入口；
- `POST /api/artifacts/{artifactId}/transition`：资产 TESTED→APPROVED 需要 Owner 人工批准，资产清单提供操作入口；
- `POST /api/entities/{entityId}/apply`：参数快照仅允许 APPROVED 对象携带人工 `approvalId` 进入 `PUSH_APPROVED` Edge 队列并转为 APPLIED；
- `POST /api/engineering/toolchain-matrix`：执行 PLC/HMI Golden Project 矩阵，比较工具链、编译、HMI Smoke 和期望/实际 Hash；
- `POST /api/projects/{projectId}/toolchain-matrix`：将矩阵结果持久化为 `tool_validation`，通过为 VALIDATED，失败为 FAILED，并保留审计记录；
- 模拟证据包含稳定 `traceHash`；Robot 握手顺序、FAT/SAT 清单、Edge 重放幂等性和生命周期指标均按确定性规则重放，便于回归比较；
- MOT-001 提供离散步进轴模拟，验证起点、目标、速度、软限位、轨迹和越界安全停机；
- VIS-001 支持样本期望/预测标签回放，输出 TP/TN/FP/FN 混淆矩阵、准确率和确定性回归结果；
- EDGE-001 支持事件 ID 离线重放，输出重复跳过数、实际应用数，并验证幂等/非幂等结果；
- EDA-001 输出 IO/BOM 缺失项、额外项和重复项明细，避免只返回一个一致性布尔值；
- HMI-001 支持画面 Smoke 序列回放，验证缺失页面、未知页面和导航顺序；
- LIFE-001 支持确定性 OEE 计算，输出 Availability、Performance、Quality、OEE，并拒绝非法停机/产量边界；
- `LIFE-001`：生产指标、质量指标和维护流程统一进入生命周期验证，缺项会阻止软件验收证据通过；
- `GET /api/projects/{projectId}/readiness`：按工作包依赖计算可开始项；
- `GET /api/projects/{projectId}/capability-readiness`：按能力 ID 汇总 VALIDATED Evidence 覆盖情况；验收报告同时返回该矩阵；
- 验收报告 summary 同时提供 `openIssues` / `closedIssues`，用于确认失败验证是否已经完成 CAPA 收敛；
- 工程资产、参数和现场写入仍必须经 Artifact/Edge owner API、审批、回读和审计。

真实工具插件接入时，只替换 capability adapter，不改变项目对象、测试证据、Release 和安全边界。
