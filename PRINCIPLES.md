# Architecture Principles

1. **Safety before convenience.** A deterministic and safe machine behavior outranks UI speed, AI autonomy, and feature breadth.
2. **Edge autonomy.** A machine must perform its minimum control and local HMI functions without cloud connectivity.
3. **Realtime isolation.** Control workloads are deterministic and resource-reserved; AI, analytics, and collaboration cannot starve them.
4. **One platform model.** Tags, devices, alarms, recipes, events, workflows, and identities have one canonical model.
5. **Explicit ownership.** Every durable object has one writer of record; projections and caches are derived.
6. **Contract first.** APIs, events, schemas, capability IDs, and migrations are versioned before implementation.
7. **Least privilege.** Human, agent, app, driver, and runtime permissions are scoped and auditable.
8. **Reversible change.** Deployments are signed, staged, health-checked, and rollback-capable.
9. **Observable by design.** Critical actions emit structured audit and operational telemetry.
10. **Long-term compatibility.** Prefer additive evolution, explicit deprecation, and migration tooling over breaking changes.

