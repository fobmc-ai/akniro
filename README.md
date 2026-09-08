# 织能 V0.1 基础平台

织能（Zhinen）是一个面向中高端工业自动化的 AI-native Industrial OS 平台。

英文品牌建议使用 **Zhinen**，正式产品线为：`Zhinen OS`、`Zhinen Studio`、`Zhinen Edge`、`Zhinen Control`、`Zhinen AI`。

This project defines the architecture and engineering contract for 织能 Zhinen, a mid/high-end, AI-native industrial automation platform. The earlier name “Industrial Platform Architecture Pack” is retained only as the historical description of this V0.1 documentation baseline. Business runtime implementations are not included in V0.1.

## Product stance

Web-first, not Web-only. The platform supports a browser engineering experience while retaining native/edge runtimes for deterministic control, offline operation, device access, and industrial safety. PLC, HMI, Vision, Motion, Robot, SCADA, MES, QMS, WMS/WCS, EAM, EMS, APS, Cloud, Mobile/Tablet HMI, and AI are platform capabilities, not unrelated products.

## Read order

1. `AGENTS.md`
2. `docs/00-master/PRINCIPLES.md`
3. `docs/00-master/ARCHITECTURE.md`
4. `docs/00-master/ARCHITECTURE_MAP.md`
5. The domain contract for the requested change
6. `docs/07-ai/AI_CONTEXT_POLICY.md` for AI-assisted work

## Status vocabulary

- **A — Now:** implementable in the current foundation.
- **B — Contract:** define interfaces, schemas, extension points, and tests; do not implement the full feature.
- **C — Roadmap:** record intent, constraints, and acceptance direction only.

## Repository layout

The `docs/` tree is the architecture source of truth. `docs/09-governance/ADR/` stores immutable architecture decisions. Future source code must live in bounded modules that reference these contracts.

## V0.1 scope

V0.1 establishes vocabulary, boundaries, ownership, IDs, lifecycle rules, deployment/recovery contracts, AI governance, and a staged roadmap. It does not implement the PLC compiler, realtime runtime, driver fleet, MES workflows, or cloud service.
