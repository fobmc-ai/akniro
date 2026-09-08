# 织能 V0.1 基础平台

English project identifier: `Zhinen Foundation Platform V0.1`.

## Authority

This repository is the architecture source of truth for 织能 Zhinen, an AI-native industrial automation platform. These rules apply to every change unless a more specific `AGENTS.md` exists in a deeper directory.

## Codex operating rules

1. Read this file, `docs/00-master/PROJECT_INDEX.md`, `docs/00-master/ARCHITECTURE_MAP.md`, and the relevant domain documents before changing anything.
2. Classify every request as A (implement now), B (define contract only), or C (roadmap). Do not implement B/C behavior without an explicit decision record.
3. Prefer the smallest context level and budget that can safely answer the task. Follow `docs/07-ai/AI_CONTEXT_POLICY.md`.
4. Preserve module ownership, API compatibility, deterministic behavior, and realtime isolation. Do not infer ownership from convenience.
5. Use the workflow: Read → Plan → Suggest → Patch → Test → Review → Apply. Deployment of PLC, Motion, EtherCAT, Safety, or IO changes always requires a human approval gate.
6. Update affected indexes, capability records, changelog, and ADR references in the same change.
7. Never silently change an architecture decision. Create or update an ADR first.

## Hard constraints

- MUST keep realtime/control-plane workloads isolated from non-realtime/data-plane workloads.
- MUST support offline edge operation for the minimum control function.
- MUST use stable IDs for requirements, capabilities, APIs, events, tags, and ADRs.
- MUST define one authoritative owner for every persistent domain object.
- MUST NOT allow AI to directly deploy safety-critical or motion/control changes.
- MUST NOT perform an unreasoned full-repository scan or duplicate reads.
- MUST NOT add a dependency without license, security, maintenance, and runtime-impact review.

## Change checklist

- [ ] Scope and A/B/C classification recorded.
- [ ] Relevant domain contract and data owner identified.
- [ ] Compatibility and migration impact assessed.
- [ ] Tests or validation plan added.
- [ ] `PROJECT_INDEX.md`, `ARCHITECTURE_MAP.md`, or changelog updated when applicable.
- [ ] ADR added for a new or changed cross-cutting decision.
