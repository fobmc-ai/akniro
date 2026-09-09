# 工程资产与现场参数同步架构

## 1. 目标

工程项目控制中心必须能展示和管理 PLC 程序、HMI、固件、设备包、参数、测试证据和现场版本，同时让开发进度与实际工程状态保持一致。同步必须可追溯、可冲突检测、可回滚，不能用“最后写入者覆盖”解决问题。

## 2. 三类数据边界

| 数据类 | 例子 | canonical owner | 管理软件行为 |
|---|---|---|---|
| Engineering Artifact | PLC/HMI/Firmware/EDA/Vision/Robot 源码、工程包、二进制 | 工程项目/Artifact Service | 管理版本、校验值、关联任务和发布 |
| Control Metadata | 项目、进度、需求、任务、问题、测试、审批、Release | Project/Quality/Release Service | 直接管理和审计 |
| Runtime/Field Fact | Live Tag、IO、报警、Recipe 当前值、校准、设备健康 | Edge Runtime/Domain Service | 读取快照、提交受控参数变更，不复制实时状态 |

工程文件不是实时数据；现场参数不是普通任务附件；进度不能由运行状态自动臆测，必须通过明确的事件或人工确认更新。

## 3. 工程资产模型

每个资产至少包含：

`artifactId、artifactType、projectId、machineId、moduleId、sourceUri、contentHash、revision、toolchainVersion、targetEnvironment、license、sensitivity、ownerId、createdAt、status`

资产类型：PLC、HMI、Firmware、Device Package、Motion、Vision、Robot、EDA、Recipe、Parameter Set、Calibration、Documentation、Test Evidence。

资产 revision 不可覆盖。每个 Release 绑定一组兼容的 artifact revisions，形成完整 Software/Firmware Bill of Materials。

## 4. 开发进度同步

进度以 Project Management Service 的 Work Item、Test Run、Review、Release 和 Deployment 事件为准。工程工具可以上报：

```text
opened -> edited -> built -> tested -> reviewed -> approved -> released -> deployed
```

上报必须包含 artifactId、revision、toolchain、actor、machine/project scope 和 correlationId。构建成功不等于功能完成，只有满足验收标准并经过测试/评审才能推进任务。

## 5. 参数同步

参数分为：

- **Design Parameter**：工程默认值，属于 Machine Project revision；
- **Deployment Parameter**：发布到某台机器的已批准参数；
- **Runtime Observation**：现场当前值和历史变化，属于 Edge/Runtime；
- **Calibration**：校准结果，必须带设备、环境、工具和证据；
- **Temporary Override**：临时调整，必须有过期时间、原因、操作者和回退值。

同步流程：

```text
Read Snapshot
  -> Compare Project/Deployment/Runtime
  -> Show Diff and Source
  -> Validate Range/Mode/Permission
  -> Approval if required
  -> Apply through Runtime/Device owner
  -> Verify Read-back
  -> Audit + Parameter Event
```

管理软件不得直接写 PLC 内存、IO 或危险参数。所有参数写入必须经过目标服务的类型、范围、设备状态、运行模式和安全策略检查。

## 6. 同步拓扑

```text
Developer Tools / PLC IDE / Firmware IDE
                  |
                  v
        Project Control Center
          (metadata + artifact index)
                  |
       signed release / approved request
                  v
              Edge Agent
          (offline queue + verify)
                  |
                  v
      PLC / HMI / Firmware / Devices
```

云端同步是可选的。Edge 断网时可以继续保存允许离线的记录和参数快照，恢复后按 idempotencyKey 重放；冲突进入 Conflict Queue，由人决策。

## 7. 版本与兼容

Release 不是单个文件，而是兼容资产集合：

```text
Release
├── PLC artifact revision
├── HMI artifact revision
├── Firmware artifact revision
├── Device Package revisions
├── Schema/API/Event versions
├── Parameter/Calibration revisions
├── Test evidence
└── Rollback set
```

升级前检查 PLC/HMI/Firmware/Device Package/Parameter 的兼容矩阵；任何失败都停在 Staged，不进入 Applied。回滚必须恢复完整集合，不能只回滚 PLC 文件。

## 8. 安全与审计

- 源码、固件和客户工程可标记为 Edge-only，禁止默认上传；
- 二进制和工程包必须校验 contentHash，正式发布必须签名；
- 参数写入和现场升级记录 actor、原因、审批、目标设备、旧值、新值和验证结果；
- 固件升级必须有电源、通讯、版本和恢复策略；
- AI 只能读取被授权的资产和快照，不能直接执行部署或 Force；
- 同步失败、校验失败、版本漂移和冲突都必须产生 Problem/Event。

## 9. 首个实现边界

第一阶段只实现：Artifact Metadata、contentHash、revision 引用、进度事件、参数快照、Diff 展示、同步队列和审计。文件上传、PLC/HMI 工具插件、Edge Agent 和现场写入按后续 ADR 分阶段接入。

## 10. 验收标准

- 能看到每个 PLC/HMI/Firmware 资产的当前 revision 和 contentHash；
- 任一任务可以追溯到资产、构建、测试和 Release；
- 任一机器能显示 Design/Deployment/Runtime 参数差异；
- 参数变更有范围校验、权限、审批和 read-back 证据；
- 断网期间不丢失允许同步的记录；
- 冲突不被覆盖，而是进入队列；
- Release 可完整回滚 PLC、HMI、Firmware 和参数集合；
- 客户敏感工程默认留在 Edge。
