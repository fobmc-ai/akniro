# 织能 Zhinen V0.1 基础平台

织能是面向工业自动化全生命周期的 AI-Native Industrial Engineering OS。当前仓库处于契约优先的 V0.1 基础阶段。

先读：[长期产品/技术总纲](MASTER_PLAN.md) · [项目索引](PROJECT_INDEX.md) · [总体架构](ARCHITECTURE.md) · [路线图](ROADMAP.md)

当前可运行的软件范围包括：Project Control Center、Machine Project 对象树、需求/任务/问题/CAPA/知识库、PLC/HMI/EDA/Motion/Vision/Robot/Firmware/Edge/FAT-SAT/生命周期/AI 的确定性验证、Artifact/Test Run/Evidence、工具链矩阵、Release/Deployment Gate、离线同步、审计、备份、迁移状态和总纲完成度审计。真实 PLC/驱动/运动控制器/固件刷写和正式安全认证仍由人工与现场适配器承接，软件模拟不会冒充现场能力。

Phase 0 契约测试：

```bash
python -m unittest discover -s tests -v
python tools/validate_machine_project.py examples/machine-project.valid.json
node tools/check_web_syntax.js
git diff --check
# 一次运行以上全部门禁
python tools/verify_all.py
```

启动 PM-0 开发服务并打开项目总览：

```bash
python tools/run_pm_server.py
```

访问 <http://127.0.0.1:8765>。管理中心通过项目范围 API 展示目录、进度、测试证据、问题、资产、参数、发布和运维状态。关键只读审计入口包括：

```text
GET /api/projects/{projectId}/completion-audit
GET /api/projects/{projectId}/issue-preflight?issueId=...
GET /api/projects/{projectId}/export-manifest
GET /api/projects/{projectId}/schema
```

所有控制器写入、现场部署、AI Apply、参数应用和冲突裁决都保留人工权限与专用门禁；正式身份认证和生产硬件接入尚未接入。

