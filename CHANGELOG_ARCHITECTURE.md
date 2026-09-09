# Architecture Changelog

## 2026-09-08 — V0.1

- Formalized the project name as 织能 V0.1 基础平台, with English identifier `Zhinen Foundation Platform V0.1`.
- Added formal product-family naming rules and repository slug `zhinen-platform`.
- Started the V0.1 contract-first source skeleton with Machine Project, Capability, and Resource Lease schemas.
- Established platform layers, Control/Data Plane split, realtime isolation, offline edge requirement.
- Added A/B/C classification and stable ID rules.
- Added canonical object ownership, project index, architecture map, AI context governance, deployment and recovery contracts.

## 2026-09-10 — Release preflight management-center closure

- Exposed read-only Release Preflight in the Web Gate view for artifact, hash, gate, machine-commit, parameter-snapshot, SBOM, approval, and rollback checks.
- Aligned the UI with the authoritative `artifactRevisions` response contract and added an HTTP regression test for revision/hash display data.
- Added a project-scoped read-only integrity audit for entity revisions/owners, link targets, payload references, and artifact hashes.
- Release preflight now consumes the integrity audit and blocks release readiness on unresolved control-plane consistency errors.
