# ADR-0013: Ecosystem Package Data Boundary

- Status: accepted
- Date: 2026-09-10
- Scope: ECO-001

## Decision

Marketplace、Device Package 和 Fleet Learning 的共享输入必须通过确定性契约校验：来源同意、数据范围、保留天数、签名和权限均需明确。生态包不得声明 `direct_deploy`、`force_io`、`safety_override`、`raw_customer_program` 或 `credentials` 权限；即使契约通过，`directControlAllowed` 仍为 false，并保留人工审批门禁。

## Consequences

没有真实生态数据时，平台仍可验证数据边界和授权逻辑。后续接入真实市场或车队数据时只需替换输入适配器，不改变核心对象、证据和安全边界；真实数据仍必须经过租户隔离、来源审计和回归验证。
