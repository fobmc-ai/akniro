# 织能 Zhinen V0.1 基础平台

织能是面向工业自动化全生命周期的 AI-Native Industrial Engineering OS。当前仓库处于契约优先的 V0.1 基础阶段。

先读：[长期产品/技术总纲](MASTER_PLAN.md) · [项目索引](PROJECT_INDEX.md) · [总体架构](ARCHITECTURE.md) · [路线图](ROADMAP.md)

当前重点是 Machine Project、稳定 ID、能力/资源注册、版本化 API/事件、权限审计和 Schema 验证；实时 Runtime、完整 IDE、设备驱动和工业应用按路线逐步实现。

Phase 0 契约测试：

```bash
python -m unittest discover -s tests -v
python tools/validate_machine_project.py examples/machine-project.valid.json
```

启动 PM-0 开发服务并打开项目总览：

```bash
python tools/run_pm_server.py
```

访问 <http://127.0.0.1:8765>。当前页面支持创建项目、需求/任务/问题和推进基础状态；正式身份认证和生产部署尚未接入。

