# System Architecture

## Layers

1. **Hardware and HAL:** CPU, memory, storage, network, fieldbus, IO, camera, GPU/NPU, safety interfaces.
2. **Realtime Runtime:** PLC scan, motion, robot coordination, safety boundary, deterministic IO and time.
3. **Core Platform:** object model, tags, device registry, alarms, recipes, event bus, historian, workflow, rules, resources, capabilities.
4. **Engineering Plane:** project editor, PLC IDE, HMI designer, vision/motion studios, simulation, validation, deployment.
5. **Engineering Project Management Plane:** requirements, work items, ADRs, issues, test evidence, release, approval, collaboration, and AI context scope.
6. **Operations Plane:** HMI, SCADA, reports, dashboards, MES/QMS/WMS/EAM/EMS/APS applications.
7. **AI Plane:** indexing, machine context, assistants, policy enforcement, model gateway, evaluation, audit.
8. **Cloud/Enterprise:** fleet, identity federation, sync, remote access, OTA, analytics, tenant administration.

## Control Plane and Data Plane

The Control Plane owns desired configuration, identity, policy, lifecycle, deployment intent, and metadata. The Data Plane owns live execution, device values, runtime state, local events, and time-series observations. Control Plane writes are validated and promoted; Data Plane never becomes an accidental configuration store.

## Connectivity

- Southbound adapters normalize PLC, EtherCAT, OPC UA, Modbus, CAN, serial, robot, camera, and vendor protocols behind HAL/driver contracts.
- Northbound APIs expose stable REST/gRPC/WebSocket/event contracts; clients must not reach into runtime internals.
- Cloud synchronization is asynchronous and conflict-policy driven. It never becomes a hidden realtime dependency.

## Required boundaries

- Realtime Runtime MUST NOT import AI, cloud, browser, or non-deterministic analytics libraries.
- Domain Core MUST NOT own UI state or vendor-specific transport details.
- Apps MUST consume capabilities and contracts, not inspect files or assume installed modules.
- Drivers MUST be replaceable and must not own canonical domain records.
- Project Management MUST manage references, approvals, and evidence; it MUST NOT own runtime facts or duplicate domain records.

