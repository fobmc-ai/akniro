# AI Context Policy

## Levels

- **L0:** task statement and direct target file.
- **L1:** target module and local contract.
- **L2:** dependency interfaces and tests.
- **L3:** bounded domain documents and project index.
- **L4:** architecture map, ADRs, compatibility and security constraints.
- **L5:** machine context, runtime telemetry, project graph, relevant history.
- **L6:** full repository or broad cross-domain investigation; exceptional only.

Start at the lowest level. Escalate only when evidence shows missing context. Every retrieval records reason, source, level, token/byte budget, and result. Prefer indexed summaries, symbols, dependency edges, diffs, and targeted search. Full scans require an explicit rationale in the work log and MUST NOT be repeated without new evidence.

## Context budget

Each task declares a context budget. When the budget is exhausted, stop retrieval, summarize known facts, and ask for a scope decision or continue with the bounded evidence. Context is not permission to read secrets or unrelated tenants.

