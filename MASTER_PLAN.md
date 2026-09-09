# 织能 Zhinen：AI 原生工业自动化工程平台

> 文档性质：长期产品/技术总纲（Master Plan）  
> 使用对象：Codex、开发团队、架构评审、产品规划  
> 适用范围：全生命周期的 AI-Native Industrial Engineering OS

本文是产品方向和长期技术边界的总纲。后续功能规划不得与本文的核心原则冲突；重大架构变更必须先形成 ADR。V0.1 当前只建设基础契约和可验证的工程骨架，不以本文的长期目标为理由提前实现尚未成熟的功能。

## 1. 产品定义与核心理念

织能不是单独的 PLC IDE，也不是简单的 PLC+HMI+AI，而是一套 AI 原生工业自动化工程操作系统。统一的 Machine Model / Machine DNA 贯穿：

需求 → 方案 → 选型 → 报价 → EDA → PLC → HMI → Motion → EtherCAT → Vision → Robot → Simulation → Commissioning → FAT/SAT → Production → Quality → Maintenance → Remote Service → Engineering Change。

AI 负责理解、生成、检查、解释、诊断、优化和提出变更；PLC、Motion、Safety Runtime 负责确定性、实时、可验证执行。最终闭环是：需求 → 设计 → 程序 → 测试 → 调试 → 运行 → 故障 → 改进 → 下一台机器复用。

## 2. 不可破坏的架构原则

1. **Single Source of Truth**：Tag、设备、报警、参数、Recipe、版本只定义一次。
2. **Object First**：核心对象是 Machine、Station、Module、Device、Capability、Sequence，而不是孤立的 X/Y/M/D 地址。
3. **安全门禁**：AI 不得直接控制危险运动；变更必须经过建议、Diff、仿真、测试、人工批准、部署。
4. **实时隔离**：Realtime Runtime 与 AI、云端、浏览器及其他非实时工作严格分层。
5. **模块化与插件化**：核心模块化，设备通过 Device Package/SDK 扩展，禁止无限硬编码。
6. **版本与迁移**：Project Schema、Runtime、Device Package 必须版本化，支持迁移和 LTS。
7. **生成即测试**：AI 生成程序必须同时生成测试；公共库修改必须回归测试。
8. **全程可追溯**：需求、代码、参数、测试、部署和现场修改均可追溯、可审计。
9. **Edge First / Cloud Optional**：核心工业能力离线可用，云端不能成为机器运行的硬依赖。
10. **最小上下文**：Codex/AI 只读取完成任务所需的最小上下文，禁止无目的扫描整个项目。

## 3. 工程项目管理软件

织能配套建设独立的 Engineering Project Management Plane（暂定名 Zhinen Engineering Control Center），用于管理平台研发项目和客户机器工程项目的需求、任务、ADR、问题、测试证据、版本、审批、发布和交付。它属于上层 Control Plane，不直接执行 PLC、Motion、Safety、EtherCAT 或 IO 控制，也不复制 Machine Project、Tag、Device、Alarm、Recipe 和 Runtime Data 的 canonical 数据。

管理软件与机器平台通过 Query、Command、Event 和不可变 revision 引用协同；第一版先做对象、状态机、权限、审计、追溯和离线同步契约，再做 UI、发布和 AI 上下文。详细范围、对象 owner、MVP 和验收标准见 [`PROJECT_MANAGEMENT_PLATFORM.md`](PROJECT_MANAGEMENT_PLATFORM.md)。

测试库、问题库、知识库、PLC/HMI 工具验证和发布维护是管理软件的一级能力，不是售后补丁。每个算法、工具功能和工程能力必须先有 Design Goal、Acceptance Criteria 和 Test Plan，质量门禁见 [`QUALITY_LIFECYCLE_SYSTEM.md`](QUALITY_LIFECYCLE_SYSTEM.md)。

管理软件还必须在开发前冻结租户/项目隔离、状态机、环境晋级、备份恢复、搜索索引 freshness、通知升级、平台可观测性和数据保留规则，详见 [`PLATFORM_OPERATIONS_GOVERNANCE.md`](PLATFORM_OPERATIONS_GOVERNANCE.md)。

管理软件的 PM-0 领域对象、状态机、权限、API 和事件契约已单独冻结，见 [`PM0_CONTRACTS.md`](PM0_CONTRACTS.md)。

PLC、HMI、Firmware、设备包、开发进度和现场参数通过 Artifact/Control Metadata/Runtime Fact 三层同步，管理软件不直接写实时控制数据，详见 [`ENGINEERING_ASSET_SYNC.md`](ENGINEERING_ASSET_SYNC.md)。

## 4. 统一 Machine Model / Machine DNA

对象结构为 `Machine → Station → Module → Cylinder/Vacuum/Sensor/Axis/Vision`。每个工业对象可携带 Tag、IO、PLC 逻辑、HMI、参数、报警、Recipe、运动能力、电气连接、仿真、测试、诊断、维护、历史、文档和 AI 语义。

Machine DNA 记录某台真实设备在某个时间点的 Hardware、Firmware、PLC、HMI、Vision、Motion、EtherCAT、EDA、BOM、Recipe、Parameters、Calibration、AI Model 和 Version。一个对象应能贯穿 EDA、PLC、HMI、运行时和诊断，避免各模块各建一套变量。

长期目标是让 `PLC FB = HMI Widget = Alarm Template = Parameter Template = Diagnostic Template`。例如 `Motor01:ServoAxis` 可自动派生运行、停止、JOG、位置、速度、报警、复位、参数、趋势和诊断能力。

## 5. 工程能力路线

### PLC IDE 与编译链

长期支持 LD、ST、FB/FBD、SFC、类型系统、Library、Watch、Trace、Force、Online Monitor、Download/Upload、Online Change、Debug 和 Device Configuration。正式编译链为：

`Source → AST → Semantic → IR → Optimization → Runtime/Target`

正式架构不得长期依赖字符串解释执行。AI 可用于程序生成、解释、依赖分析、静态检查、状态机生成、重构、程序体检、Review、测试和跨品牌迁移辅助。

### MDL 机器描述语言

建立 Machine Description Language，描述机器对象而不只是 PLC 指令。一个 Cylinder、Axis 或 Station 定义，应能派生 PLC、HMI、IO、Alarm、Parameter、Simulation、Test、Documentation 和 Diagnostics。工程师逐步面对 `PickCylinder.Extend` 等语义对象，而不是只面对地址。

### Device Package / SDK

统一设备包包含 Device Definition、Driver、Communication、EtherCAT PDO、Parameters、Alarm Codes、PLC FB、HMI Widget、Simulator、Diagnostics、Documentation 和 AI Knowledge。新增伺服、IO、温控、扫码枪、相机或机器人不得修改平台核心。长期支持自动发现、自动组态和 Plug & Produce。

### EDA / 电气工程

EDA 与 Machine Model 共享数据，逐步覆盖 PLC/IO/电源/断路器/端子选型、IO 分配、BOM、端子表、线号和电气图初稿。增加 NPN/PNP、NO/NC、错线、电源余量、模块容量和器件兼容检查。

### Motion / EtherCAT

统一 Axis Object，支持 Servo、Stepper、Pulse、EtherCAT Axis；逐步支持定位、回零、JOG、插补、电子凸轮、飞剪/追剪。AI 可辅助伺服整定、加速度/Jerk 优化、机械误差补偿和精度漂移检测，但不得绕过确定性控制和人工批准。

### Vision / 柔性振动盘

视觉能力统一纳入平台，覆盖 Shape Model、Caliper、Blob、OCR、Measurement 和 Classification。基于 OK/NG 样本推荐 ROI、算法链并自动调参后验证；逐步扩展相机、镜头、光源选型、标定、手眼标定和自标定。

柔性振动盘通过视觉反馈散料率、重叠率和可抓取率，优化频率、振幅、方向、振动和停稳时间。

### Robot 与统一能力层

建立品牌无关的 `Pick / Place / Move / Inspect / Dispense` Capability，长期支持轨迹、避障、视觉抓取、自动握手、PLC/Robot 统一流程和数字孪生验证。

## 6. AI 原生工程与安全治理

输入需求文档、电气图、IO 表、动作流程和设备清单后，AI 可辅助生成变量、设备对象、PLC 框架、HMI、报警、参数、Recipe 和调试清单。自然语言或手动示教可生成 Sequence/State Machine，并自动补充 Timeout、Alarm、Pause、Recovery、Manual 和 Reset，再进入审核和确定性控制逻辑。

同时保留 Professional Mode（LD/ST/FB）与 Process Mode（流程/示教）。Agent 至少拆分为 Requirements、PLC、HMI、EDA、Vision、Reviewer、Test、Diagnostic、Documentation。Builder 负责生成，Reviewer 专门挑错，Test 独立验证，生成者不能自己宣布正确。

权限至少包含 `READ / SUGGEST / MODIFY / SIMULATE / DEPLOY / FORCE`。所有 AI 动作写入 Audit Log；涉及 PLC、Motion、EtherCAT、Safety 或 IO 的部署必须有人批准。AI 永远不能直接 Force IO 或部署危险控制逻辑。

## 7. 仿真、测试与质量门禁

第一阶段优先建设 Logical Digital Twin，不急于复杂 3D。模拟气缸、传感器、轴、真空、产品和相机。标准对象/FB 必须有 Unit Test，机器必须有 Integration Test；故障注入覆盖传感器不到位、伺服报警、EtherCAT 掉线、相机超时、急停、断电和通讯异常。

目标 CI/CD 流程：

`Commit → Compile → Static Analysis → Unit Test → Simulation → Safety Rules → Regression → Review → Release`

## 8. 调试、运行与生命周期

Commissioning 自动通电流程为：`24V → Network → EtherCAT → IO → Safety → Servo → Cylinder → Vision → Station → Auto Cycle → Burn-in`。支持自动 IO 点检、错线检测和调试报告。

Runtime 保存故障前后的 Tag、IO、轴、报警和状态机信息，后续加入视频、PLC、Vision、Motion 同步回放。“为什么不能启动”由确定性依赖图找出阻塞条件，再由 AI 负责解释。Alarm 升级为 Cause、Severity、Diagnosis、Recovery、Test，并建立 Root Cause/Derived Alarm 关系。

生产阶段记录步骤耗时，识别瓶颈、等待和并行机会，支持 OEE、Micro-stop 和停机损失。监测气缸动作、真空建立、伺服定位、视觉分数、网络错误和 Cycle Time，形成可解释的设备健康分析。

Product ID 关联 Recipe、Machine、PLC State、Vision、Measurement、Image、Process Parameters 和 Timestamp，支持 SPC、漂移分析和 NG 关联。一个 Product Recipe 统一 PLC、HMI、Motion、Vision、Feeder 和 Robot，实现一次换型。

## 9. Machine Git、Edge 与企业知识

一次 Machine Commit 包含 PLC、HMI、Vision、Servo、EtherCAT、Recipe、EDA、BOM 和 Firmware，支持 Diff、Rollback、Branch 和 Release。Golden Machine 用于比较同型设备，Machine Diff 用于解释“同样两台机器为什么表现不同”。

客户程序管理纳入 Machine Lifecycle，每台设备保存工程、BOM、图纸、参数、版本、维修记录、报警和备件。可先用工业 Linux/RK3576 Edge Box 接入现有 PLC、仪表、相机和串口设备，提供统一数据、Web 监控、历史、报警、远程维护、黑匣子和 AI 诊断。

平台逐步自动发现 PLC/HMI/Camera/Robot/Switch/EtherCAT 拓扑，检查 IP 冲突、掉线、延迟和网络基线变化。每次故障沉淀“现象 → 检查 → 原因 → 解决 → 验证”，形成企业 AI 老师傅；自动发现重复的 PLC/HMI/Alarm/工艺，建议抽象 Standard Module、Machine Template 和标准产品。

正常状态低频或摘要保存，异常时提高采样率并保存故障前后的高频窗口。实时数据留在本地，历史数据保存在 Edge，需要的摘要再上 Cloud；敏感程序可以永不离开现场。通过 Machine Graph/Dependency Graph（如 `Y20 → KM3 → Servo Enable → Axis → Station`）为 AI 提供问题相关对象，降低 Token、延迟和误判。

## 10. 方案、报价、验收与优化

方案链覆盖需求 → 选型 → BOM → 成本 → 毛利 → 报价 → 技术方案 → 交期，并纳入新工艺、超高良率和短交期等风险价格。Requirement ID 关联设计、PLC 逻辑、IO、Test Case 和 FAT Result。

自动生成 FAT/SAT 流程，保存 PLC 数据、图片、参数、测试结果和时间戳，形成验收证据。

根据负载、行程、速度、精度和节拍辅助选择电机、减速机、丝杆、导轨和气缸，并做扭矩、惯量、临界速度和安全系数计算。支持 DFM 自动化可行性、BOM 查错、替代料兼容、备件预测和高配/标准/低成本 Value Engineering；支持自标定、误差地图、机械漂移、工艺参数与良率关联、历史相似产品 Recipe 初值。

旧设备方向包括老程序分析、IO 还原、逻辑重构和旧 PLC/HMI 工程迁移。长期支持跨品牌迁移：能等价转换的自动转换，不能等价的生成 Migration Report；更换 PLC、驱动器或相机后可恢复最后稳定的程序、参数、ROI、模板和 Calibration。

## 11. 商业与生态路线

短期可销售：AI 工业工程工具箱、自动选型报价、程序分析、IO 调试、黑匣子、Machine Diff、自动备份、设备体检、Edge 盒子和远程维护。

中期建设统一 HMI/视觉/EDA/设备模型、Device Package、Commissioning 和 Simulation。长期护城河是自有 PLC Runtime、Motion/EtherCAT、完整 PLC IDE、Robot、Digital Twin 和 Industrial Engineering OS 生态。不要等 3–5 年 PLC 全部完成才第一次卖产品。

未来生态包括 Device Package、Servo Module、Vision 算法、Machine Template 和行业模板市场，以及在客户明确授权和隐私隔离前提下的 Fleet Learning。不得默认上传客户敏感程序。

## 12. 分阶段交付路线

| 阶段 | 目标 | 主要交付 |
|---|---|---|
| Phase 0 地基 | 建立可演进的基础契约 | Project Schema、Object ID、Tag/Type、Machine Model、Device Package 接口、Version、Dependency、Permission、Audit、Project Storage |
| Phase 1 最小闭环 | PLC 可编译、下载、监控 | PLC IDE 基础、Runtime、LD/ST、Compile/Download、Online Monitor、Tag、HMI 共享变量 |
| Phase 2 工业可用 | 形成可交付机器能力 | Alarm、Parameter、Recipe、Device Object、Commissioning、Trace、Version/Diff、标准 FB 库 |
| Phase 3 平台化 | 扩展工程和设备生态 | HMI Designer、Device Package、EtherCAT/Motion、Vision、Edge/Remote、Machine Git |
| Phase 4 验证 | 建立可重复质量门禁 | Logical Twin、Unit/Integration Test、Fault Injection、CI/CD、Regression |
| Phase 5 AI 工程 | 让 AI 成为受控工程协作者 | Requirements/PLC/HMI/Reviewer/Test/Diagnostic Agents、自然语言工程、自动文档 |
| Phase 6 生命周期 | 连接生产、质量、维护 | Black Box、OEE/SPC、Traceability、Health、FAT/SAT、Machine Diff、Golden Machine |
| Phase 7 生态 | 形成平台网络效应 | Robot、3D Twin、Marketplace、Fleet Learning、Machine Template、跨品牌迁移 |

与 V0.1 Roadmap 的对应关系：当前处于 Phase 0；Phase 1–2 属于后续 A 类实现；Phase 3–7 先定义契约并作为 B/C 类路线，不得无 ADR 直接实现。

## 13. 当前阶段禁止事项

- 不要一开始做完整 3D 数字孪生或同时支持大量 PLC 品牌。
- 不要先做漂亮 UI 再补数据模型。
- 不要让 PLC/HMI/EDA/Vision 各建一套变量。
- 不要把设备驱动硬编码进核心。
- 不要让 AI 直接 Force IO 或部署到现场。
- 不要为了 Demo 绕过 Compiler/IR/Runtime 正式架构。
- 不要无测试修改公共 FB、Schema 或 Runtime 协议。
- 不要把 AI 做成没有权限边界的万能 Agent。
- 不要把云端作为机器运行的硬依赖。
- 不要把客户程序云、远程维护、视觉等发展成互不相干的孤岛。

## 14. Codex 与团队工作规则

1. 开始任务前先读本总纲及当前模块 README、ADR、API 契约。
2. 明确任务边界、影响模块和验收条件后再修改。
3. 默认只读取当前模块和直接依赖；扩大范围必须说明原因。
4. 不得擅自改变核心 Schema、Object ID、公共 API、Runtime 协议和版本格式。
5. 架构变更先写 ADR/Proposal，不得直接改实现。
6. 每次修改列出 Files Changed、Behavior Changed、Tests、Risks、Compatibility。
7. 新功能优先扩展现有对象模型，不复制第二套数据源。
8. 新设备优先使用 Device Package，不写入核心特例。
9. AI 功能必须有权限、审计、Diff 和可撤销路径。
10. 控制安全结论必须由确定性规则、测试或仿真验证。
11. 临时代码必须标注 TECH_DEBT 和移除条件。
12. 每个里程碑保持项目可编译、可测试、可回滚。

## 15. 与现有架构决策的关系

- [ADR-0001](ADR-0001-platform-foundation.md) 固化分层、Edge Autonomous、Contract First、Machine Project 和 Control/Data Plane。
- [ADR-0002](ADR-0002-ai-change-gates.md) 固化 AI 的 Read → Suggest → Patch → Test → Apply → Deploy 门禁。
- [ADR-0003](ADR-0003-foundation-skeleton.md) 固化 V0.1 先做 Schema 和源码骨架、不引入外部 Runtime 依赖的决定。

若本总纲与具体 ADR 发生冲突，应先更新 ADR 和本总纲，再实施变更。
