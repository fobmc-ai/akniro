# Change and Problem Handling Rules

目标是让问题被正确定位、一次只改一个边界、每次消耗都有可复核的产出。

## Work classification

- **A — Implement now**：已有契约、owner、验收标准和测试路径。
- **B — Define contract**：方向确定但实现细节或技术选型未定，只写 Schema/API/ADR/测试计划。
- **C — Roadmap**：长期能力或依赖尚未成熟，只登记目标、前置条件和触发时机。

没有 A 类验收条件的任务不得直接进入实现。

## Problem loop

```text
Capture -> Reproduce -> Bound -> Identify owner -> Decide severity
        -> Propose smallest fix -> Test regression -> Review
        -> Apply with approval -> Observe -> Close or rollback
```

每个问题必须记录：Problem ID、现象、复现条件、影响范围、最后稳定版本、相关对象/消息/日志、假设、证据、修复、回归测试、残余风险和关闭条件。

## Stop conditions

遇到以下情况必须暂停扩大改动并先补契约或 ADR：

- 不确定哪个模块拥有数据；
- 需要修改公共 Schema、ID、API、Event 或 Runtime 协议；
- 需要引入依赖但没有 license/security/runtime 评估；
- 无法复现且没有观测证据；
- 修复会影响 realtime、offline、security、migration 或 rollback；
- 需求同时覆盖多个领域但没有明确边界和优先级。

## AI/Codex operating rules

1. 先读总纲、索引和目标模块的直接契约，默认最小上下文。
2. 开始前写 Scope、A/B/C、影响 IDs、验收条件和非目标。
3. 先给出方案和风险，再 Patch；不以“先跑起来”为理由破坏正式边界。
4. 一次变更保持单一主题；跨模块变更必须说明数据流和 owner。
5. 测试失败先判断是代码、契约、环境还是数据问题，不盲目重试。
6. 每次工作结束报告 Files Changed、Behavior Changed、Tests、Risks、Compatibility、Token/时间成本。
7. 同一问题连续两次没有新证据时停止重复操作，升级为诊断任务或请求范围决策。

## Definition of resolved

问题只有在根因有证据、修复已验证、回归测试已加入、文档/ADR/索引已同步、风险和回滚路径已记录时才可关闭。临时绕过必须登记 TECH_DEBT、owner 和移除条件。
