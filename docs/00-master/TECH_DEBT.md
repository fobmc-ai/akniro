# Technical Debt Register

| ID | Debt | Impact | Trigger to address | Owner | Status |
|---|---|---|---|---|---|
| TD-001 | Runtime implementation not present | high | before first edge pilot | Runtime | open |
| TD-002 | Driver certification matrix absent | high | before production hardware | Platform | mitigated — DRV-001 offline matrix implemented; field certification remains open |
| TD-003 | Migration runner not implemented | high | before persistent schema release | Core | mitigated — PM schema ledger, user_version and idempotent artifact revision migration implemented |
| TD-004 | Formal safety boundary evidence absent | critical | before safety-related deployment | Quality | mitigated — SAFE-001 software boundary evidence implemented; formal certification remains open |

Debt items MUST have an owner, impact, and exit trigger. Do not hide debt in prose.

