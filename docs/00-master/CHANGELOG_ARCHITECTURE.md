# Architecture Changelog

## 2026-09-08 — V0.1

- Formalized the project name as 织能 V0.1 基础平台, with English identifier `Zhinen Foundation Platform V0.1`.
- Added formal product-family naming rules and repository slug `zhinen-platform`.
- Started the V0.1 contract-first source skeleton with Machine Project, Capability, and Resource Lease schemas.
- Established platform layers, Control/Data Plane split, realtime isolation, offline edge requirement.
- Added A/B/C classification and stable ID rules.
- Added canonical object ownership, project index, architecture map, AI context governance, deployment and recovery contracts.

## 2026-09-10 — Engineering validation loop

- Added deterministic PLC runtime simulation with watchdog, communication-loss, safety-trip, and safe-stop outcomes.
- Added domain-specific simulation diagnostics for EDA, Motion, Vision, Firmware, and Edge validation.
- Exposed runtime simulation and evidence-oriented validation through the PM control-center API.
- Added set-level HMI tag consistency validation for missing and unknown bindings.
## 2026-09-10 — 测试失败证据闭环

- `execute_test_case` 对通过和失败结果均持久化 Evidence；失败证据保持 `DRAFT`，并通过 `produces` 关联测试用例，保证问题定位、复测和验收审计链不断裂。
- PLC/Firmware 构建失败自动创建问题并关联失败证据，修正 PLC 构建失败的错误领域标识。
- 增加测试计划批量执行入口，统一汇总用例运行、证据和计划状态。
- Release Gate 增加 SBOM 与 rollback revision 门禁，确保发布包可追溯且可恢复。
- Release Gate 增加签名门禁，未签名发布包不能进入部署链。
- 增加 Release 组合接口，自动生成确定性 SBOM 摘要与组件清单。
- Issue 关闭增加同项目 VALIDATED Evidence 校验，自动失败记录预填证据关联。
- Knowledge Article 增加来源、版本、验证、测试和失效条件门禁，并接入 Web 录入表单。
- Maintenance Record 增加现场机器、执行人、Release、结果、异常和回滚门禁，并接入 Web 录入表单。
- AI 上下文增加可信状态过滤，草稿/失败证据及未批准运营记录不进入上下文，并返回审计可见的省略原因。
- 增加 Deployment Request 状态机与 Web 入口，隔离发布批准和现场部署授权。
- AI 上下文过滤未确认部署请求，避免将待执行变更误作为现场事实。
- 增加 Machine Commit，绑定机器快照、已测试资产、分支、父提交和回滚提交。
- Artifact Manifest 增加 revision 迁移与并发状态迁移保护。
- 增加备份恢复校验接口，验证完整性、核心表、项目、审计/Outbox 和 revision 一致性。
- 审计页面接入“创建并校验备份”一键流程。

## 2026-09-10 — 发布前预检闭环

- Web Gate 页面接入只读 Release Preflight，统一展示制品、Hash、门禁、机器提交、参数快照、SBOM、审批和回滚检查。
- 修正页面与 `artifactRevisions` 权威响应契约的字段对接，并增加 HTTP 回归测试，避免制品数量和 revision/hash 展示误报。
- 增加项目级只读数据完整性审计，提前检查对象 revision/owner、关系目标、Payload 引用和 Artifact Hash，并接入管理中心页面。
- Demo 数据审计发现 `ISSUE-RUN-CAPA-1788976796647` 引用了尚未登记的 `TC-HMI-001`；该项保留为真实数据阻塞，等待测试用例回填后再关闭。
- Release Preflight 纳入项目完整性审计，悬空引用、关系目标缺失或 Artifact Hash 异常会直接阻止预检通过。
- CI 增加管理中心全部内嵌 Web 脚本的 Node 语法门禁，并将 `web/**` 纳入工作流触发范围。
- Backlog Readiness 增加 Design Goal、Acceptance Criteria、Test Plan、Owner、目标版本和回滚计划内容校验，防止空契约被统计为完成。
- 验证和构建失败接入项目 Owner 通知链，并以 Run ID 做幂等去重。
- Edge 同步冲突/失败接入 Owner 通知链，并以 Sync ID 做幂等去重。
- S0/S1 Issue 自动进入 Owner 升级通知链，并校验严重度范围。
- 普通测试用例失败自动进入 Issue/CAPA 链并关联失败证据，统一各测试入口行为。
## 2026-09-10

- 生命周期验收补齐确定性 SPC 控制带与设备 Health 信号检查；结果写入模拟证据并纳入全域 12 项验收套件，越界自动失败，不把未接入真实设备误报为现场验证。
- 管理中心增加项目作用域的控制平面健康快照 API，集中显示数据库容量、Outbox、通知、审计、搜索 freshness 和备份状态。
- 管理平面写入增加持久化 Event Outbox，带 schema/correlation/idempotency、发布/失败/重试状态，并纳入重启与备份校验。
- 增加独立 Review 对象与审批门禁，绑定 reviewer、revision、结论和意见，禁止评审 owner 自审通过。
- 增加项目级 Traceability Graph API 与 Web 页面，解析对象引用并显示未解析关系。
- 实体内容 revision、Machine Object revision、Artifact 状态和实体关联统一产生 Event Outbox 事件，补齐跨模块协同覆盖面。
- 实体关联事件和审计改为贯穿真实操作者，避免系统代写掩盖责任主体。
- Release Gate 增加来源 revision、Machine Project revision、Schema/API/Event 版本、已知问题和目标环境绑定，并同步发布页面录入。
# 2026-09-10

- 管理中心新增事件 Outbox 页面，展示事件类型、幂等键、Actor、尝试次数和发布状态；QUEUED/FAILED 事件可在项目权限范围内人工发布或重试，形成跨模块协同的可见运维闭环。
- 管理中心新增 PLC / 固件构建台，调用确定性模拟构建接口并自动登记 Artifact、Test Run、Evidence；失败构建自动进入 Issue/CAPA 处理链路，断电恢复验证保留回滚引用。
- Artifact 创建事件补齐稳定 `artifactId`、审计和 Event Outbox 同事务写入，失败构建的产物、问题、通知和事件可被下游一致追溯。
- PLC Phase 1 最小闭环补齐下载清单和在线监视模拟：下载必须绑定 APPROVED Artifact、人工审批和回滚版本，监视输出稳定 Tag 快照与故障安全状态，二者均禁止直接写入真实控制器。
- Machine Object 创建补齐同事务 Audit 与 `pm.machine_object.created` Event Outbox，Machine Model 的创建与 revision 现在拥有一致的跨模块追踪入口。
- PLC 下载清单模拟现在自动落 Test Run/Evidence：成功进入 `PASSED/VALIDATED`，门禁阻塞保留 `FAILED/DRAFT`，为 Edge/Release/Deployment 提供可追溯操作证据。
- Edge Sync 队列补齐创建与状态迁移的 Audit/Event Outbox 事件，按 Sync ID 和幂等键保证跨设备重放时不重复制造业务事件。
- LIFE-001 新增 Product Trace 模拟与确定性 genealogy hash，将产品、机器、Recipe、PLC 状态、测量、参数和时间统一纳入生命周期验证证据。
- COMM-001 新增 FAT/SAT 固定调试顺序和逐阶段证据校验，乱序、缺项或失败项统一进入阻塞结果。
- 能力验证结果区分观测时间与确定性内容，新增不含时间字段的完整 `validationHash`，支持跨运行回归和发布审计比较。
- 修正基础能力验证接口漏返回稳定 Hash 的问题，并用非空回归断言锁定契约。
- Web 管理中心新增项目选择器；项目目录树、进度、测试、资产、审计和运维视图按选中项目刷新，避免多项目环境误读第一个项目。
- 实施 backlog 按当前软件证据回填 CORE/PLC/HMI/EDA/Motion/Vision/Robot/Quality/PM/Release/Edge/COMM/LIFE/AI 为 `VALIDATED`，并明确该状态仅代表软件验证，不代表真实硬件接入。
- 新增 backlog reconcile API 与 seed 流程，将规划源状态安全同步到既有项目并记录 Audit/Event Outbox，避免仓库规划和管理中心展示脱节。

## 2026-09-10

- 新增管理中心服务端受控 Backlog 源同步入口，统一从 `examples/implementation-backlog.json` 回填状态、占位标记和证据链接，并产生审计与事件记录。
- ECO-001 补齐 Device Package/Fleet Learning 隐私授权契约、越权权限拒绝和确定性 contract hash，并以 ADR-0013 固化数据边界。
- ROB-001 补齐握手状态、启动权限范围和故障安全停机的确定性回放证据，明确模拟器不发出运动命令。
- QUAL-001 新增 Logical Digital Twin 组件状态回放、故障注入和 Test Run/Evidence 持久化入口，覆盖气缸、传感器、轴、真空、产品和相机。
- AI-001 新增项目范围内受控建议接口，建议绑定最小上下文并持久化为 `ai_suggestion`，禁止自动批准、发布、部署或 Force。
- Runtime/Alarm 诊断新增有界依赖图回放，输出阻塞链、循环依赖、启动许可和稳定 hash，支持管理中心解释“为什么不能启动”。
- PLC-002 在线监视快照支持可选 Test Run/Evidence 自动留存，正常和故障结果分别进入验证或问题追踪链。
- HMI/EDA/Motion/Vision/Robot/Edge 新增统一确定性工程包构建接口，构建资产、测试证据、失败问题和通知进入同一闭环。
- 验收报告新增 `softwareReady`/`releaseReady` 双状态，清晰区分软件范围完成与 Release 安全门禁完成。
- 验收报告进一步拆分 `softwareReady`、`dataReady`、`releaseReady`，避免真实生态数据 Placeholder 影响软件契约完成度判断。
- 新增 Release Preflight，一致性核对 Artifact、证据、SBOM、版本元数据及可选 Machine Commit/参数快照绑定后，才把结果交给人工 Release 门禁。
