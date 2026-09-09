# 总纲实施验收状态

本清单用于验收当前可落地的软件范围。`VALIDATED-SW` 表示管理中心、契约、模拟器和自动化测试已通过；不表示真实 PLC、HMI、驱动或现场设备已经接入。实施 backlog 的 `VALIDATED` 与此含义一致。

| 工作包 | 软件证据 | 状态 |
|---|---|---|
| CORE-001 | Machine Model、对象树、Revision、Snapshot、Diff | VALIDATED-SW |
| CORE-002 | Tag/Device/Alarm/Recipe 对象模型和 owner 约束 | VALIDATED-SW |
| PLC-001/002 | PLC 能力适配器、契约检查、模拟 Test Run/Evidence | VALIDATED-SW / CONTRACT_ONLY |
| HMI-001 | HMI 能力、标签/报警绑定检查接口 | VALIDATED-SW |
| EDA-001 | IO/BOM 一致性检查接口 | VALIDATED-SW |
| MOT-001 | 轴仿真、限位、状态机检查和人工门禁 | VALIDATED-SW / CONTRACT_ONLY |
| VIS-001 | 数据集 Hash、阈值、回归集检查接口 | VALIDATED-SW |
| ROB-001 | 握手、权限范围、故障恢复检查接口 | VALIDATED-SW |
| QUAL-001/002 | Test Run、Evidence、工具验证矩阵、Release Gate | VALIDATED-SW |
| PM-001/002 | 项目、成员、实体、Review、追溯图、事件 Outbox、审计和租户隔离 | VALIDATED-SW |
| REL-001 | Release 状态机、证据/审批门禁、备份 | VALIDATED-SW |
| EDGE-001 | 离线同步队列、幂等、冲突状态和人工审批 | VALIDATED-SW |
| COMM-001/LIFE-001 | FAT/SAT、维护、生命周期对象和模拟验证入口；生产/质量/维护三类指标检查 | VALIDATED-SW |
| AI-001 | 最小上下文、跨项目隔离、禁止批准/部署/Force | VALIDATED-SW |
| ECO-001 | Device Package/Fleet Learning 隐私、授权、保留期、签名和越权权限确定性验证；真实生态数据仍延后 | VALIDATED-SW / DEFERRED-DATA |

验收命令：`py -3 -m unittest discover -s tests -v`。真实硬件接入必须通过对应 capability adapter、Artifact Manifest、Evidence、人工审批和 Edge owner API，管理中心不会直接写 PLC 内存或下发危险动作。
