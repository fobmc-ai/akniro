# Project Index

## Entry point

[`../../MASTER_PLAN.md`](../../MASTER_PLAN.md) 是长期产品/技术总纲；它定义 Machine Model、工程能力、AI 安全边界、分阶段路线和 Codex 工作规则。具体实现仍以 ADR、Schema 和模块契约为准。

This file is the low-cost navigation index for Codex. Read the smallest relevant entries before opening full documents.

| ID | Area | Primary documents | Status |
|---|---|---|---|
| CORE | canonical platform | `docs/01-core/CORE_PLATFORM.md`, `DOMAIN_MODEL.md` | A |
| RT | deterministic execution | `docs/02-runtime/REALTIME_ARCHITECTURE.md` | B |
| ENG | engineering tools | `docs/03-engineering/MACHINE_PROJECT.md` | B |
| PLAT | extension platform | `docs/04-platform/PLUGIN_SDK.md` | B |
| FACT | factory applications | `docs/05-factory/SCADA.md`, `MES.md` | B |
| CLOUD | edge/cloud | `docs/06-cloud/CLOUD_ARCHITECTURE.md` | B |
| AI | governed AI | `docs/07-ai/AI_CONTEXT_POLICY.md`, `AI_SAFETY.md` | A/B |
| QUAL | quality attributes | `docs/08-quality/SECURITY.md`, `TESTING.md` | A |
| GOV | decisions and change | `docs/09-governance/ADR/`, `DEFINITION_OF_DONE.md` | A |
| BRAND | product identity | `docs/00-master/BRAND_NAMING.md` | A |
| BUILD | implementation skeleton | `schemas/`, `examples/`, `src/`, `docs/09-governance/ADR/ADR-0003-foundation-skeleton.md` | A |

## Retrieval rule

Start here, follow one primary document, then only referenced contracts required by the task. Record newly discovered dependencies in this index.
