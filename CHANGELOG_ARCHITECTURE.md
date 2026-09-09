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
- Extended the repository contract workflow to cover all Web Management Center scripts through a dependency-free Node syntax gate.
- Backlog readiness now validates non-empty design and delivery contract fields instead of treating field presence alone as completion.
- Added a deterministic firmware OTA upgrade rehearsal with approval, signature, health-observation, power-loss, rollback, and evidence boundaries.
- Added a project-scoped lifecycle simulation pipeline for OEE, SPC, health, and product trace evidence.
- Updated the Web readiness view to expose contract completeness and missing delivery fields alongside dependency blockers.
- Added a human-gated AI suggestion Apply path with expected-revision conflict detection, forbidden-action filtering, and applied-to traceability.
- AI Apply now requires same-project VALIDATED test evidence before any non-controlled object patch can be applied.
