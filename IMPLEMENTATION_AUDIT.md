# 织能软件范围验收矩阵

本文件是当前 V0.1 软件范围的验收入口。`VALIDATED-SW` 只表示契约、确定性模拟器、管理对象、自动化证据和门禁已经在软件中验证；不表示现场硬件、实时认证或正式安全认证已经完成。

## 能力矩阵

| ID | 能力 | 软件证据 | 管理中心入口 | 状态 |
|---|---|---|---|---|
| PLC-001/002 | 编译、下载清单、在线监视、周期/看门狗/安全停机 | Artifact + Test Run + Evidence + fault injection | PLC / Runtime / 全域验收 | VALIDATED-SW / REALTIME-DEFERRED |
| HMI-001 | 标签/报警绑定、画面 Smoke、工程包 | deterministic package + regression evidence | 工程包构建 / 全域验收 | VALIDATED-SW |
| EDA-001 | IO/BOM 一致性、缺失/额外/重复项 | consistency evidence | 工程包构建 / 全域验收 | VALIDATED-SW |
| MOT-001 | 轴步进、速度、软限位、状态机 | deterministic trajectory + safe-stop evidence | 工程包构建 / 全域验收 | VALIDATED-SW / REALTIME-DEFERRED |
| VIS-001 | 数据集、阈值、标签回放、混淆矩阵 | regression evidence + trace hash | 工程包构建 / 全域验收 | VALIDATED-SW |
| ROB-001 | 握手、权限范围、故障恢复 | no-motion-command handshake evidence | 工程包构建 / 全域验收 | VALIDATED-SW |
| FW-001 | 镜像 Hash、构建、升级预演、断电和回滚 | Artifact + OTA Test Run/Evidence | 固件构建 / Firmware OTA | VALIDATED-SW / FLASH-DEFERRED |
| EDGE-001 | 离线队列、幂等重放、冲突裁决 | Sync Queue + Event/Audit + replay summary | 同步与通知 | VALIDATED-SW |
| COMM-001 | FAT/SAT 固定顺序和签核证据 | commissioning checklist evidence | 全域验收 | VALIDATED-SW / FIELD-DEFERRED |
| LIFE-001 | OEE、SPC、Health、Product Trace、维护 | lifecycle Test Run/Evidence | 生命周期 / 维护记录 | VALIDATED-SW / DATA-DEFERRED |
| AI-001 | 最小上下文、建议、人工 Apply、Revision 冲突 | governed suggestion + validated evidence gate | AI 治理上下文 / AI 协作 | VALIDATED-SW |
| DRV-001 | 协议连接、读回、故障恢复、Golden Hash | offline driver certification matrix | 工程能力 / 全域验收 | VALIDATED-SW / HARDWARE-DEFERRED |
| SAFE-001 | 实时隔离、禁止控制器写入、人工审批、AI 边界 | explicit software-boundary evidence | 工程能力 / 全域验收 | VALIDATED-SW / FORMAL-CERT-DEFERRED |
| PM/REL | 项目树、需求、任务、问题/CAPA、知识、资产、Release、部署 | revision/audit/integrity/preflight/manifest | 管理中心全部页面 | VALIDATED-SW |

## 一键验收与审计

```text
python tools/verify_all.py
POST /api/projects/{projectId}/acceptance-suite
GET  /api/projects/{projectId}/completion-audit
GET  /api/projects/{projectId}/acceptance-suites
GET  /api/projects/{projectId}/export-manifest
GET  /api/projects/{projectId}/issue-preflight?issueId=...
```

服务端验收套件统一执行 14 项能力；通过项生成 `PASSED/VALIDATED` Test Run/Evidence，可选绑定同项目 Release；失败项生成 `FAILED/DRAFT`、OPEN Issue、`diagnosed_by` 关系和 Owner 通知。`completion-audit` 汇总能力证据、工作包契约、完整性、同步、问题和 Release Preflight，不会把 Placeholder 或进度百分比当作完成。

## 当前验证证据

- Python 全量测试：`69` 项通过（以当前运行结果为准）；
- Web：`node tools/check_web_syntax.js`；
- Machine Project：`py -3 tools/validate_machine_project.py examples/machine-project.valid.json`；
- 统一门禁：`py -3 tools/verify_all.py` 输出 `verify-all-ok`；
- 运行态：`http://127.0.0.1:8765/`，一键验收成功路径 `14/14`。

## 明确的外部边界

软件已经提供现场接入所需的 Artifact、Evidence、审批、回滚、Edge owner API 和审计边界，但不会伪造以下证据：真实 PLC/驱动/运动控制器写入、固件刷写、实时性能认证、现场 FAT/SAT 签核和正式安全认证。接入真实数据后必须以新 revision、Hash、人工审核和回归 Evidence 回填。
